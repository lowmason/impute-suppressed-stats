"""Deterministic assembly of the harmonized layer from frozen raw bytes."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import polars as pl

from .config import Config
from .errors import UnknownDisclosureRegimeError
from .harmonize import bridge, disclosure
from .harmonize.naics import vintage_for_year
from .ingest import cbp, qcew, qcew_size

BUILDER_VERSION = "build_harmonized/1"

# The bridges this stage declares. Each maps a source concept onto the target concept, and none
# exists to force a total to agree (§8.6).
_BRIDGE_ROWS = [
    {
        "bridge_id": "cbp_march_week_to_qcew_month",
        "source_concept": "CBP employment, week including March 12",
        "target_concept": "QCEW monthly employment, pay period including the 12th",
        "valid_start": "2017-01",
        "valid_end": "2024-12",
        "method": "measurement_model",
        "uncertainty_treatment": "estimated in the Stage 6 measurement model",
        "verification_status": "declared_not_estimated",
    },
    {
        "bridge_id": "qcew_size_march_class",
        "source_concept": "QCEW national size class, first-quarter file",
        "target_concept": "March-reference establishment size class k_y",
        "valid_start": "2017-01",
        "valid_end": "2024-12",
        "method": "definitional",
        "uncertainty_treatment": "none -- both sides are March-referenced by construction",
        "verification_status": "verified_stage0",
    },
]


def write_parquet_deterministic(frame: pl.DataFrame, path: Path) -> str:
    """Write a frame to Parquet reproducibly and return the file's sha256.

    Row order is fixed by sorting on every column before writing: Parquet preserves input order, so
    two runs that assemble the same rows in different orders would produce different bytes and the
    §19 Phase 1 criterion would fail for a reason that has nothing to do with the data. Sorting on
    every column rather than a key subset is what makes the order total -- the only rows left tied
    are rows identical in all columns, which are interchangeable in the output bytes.

    `rechunk` because Parquet row-group boundaries follow the frame's chunk layout, and a frame
    assembled by `concat` chunks differently than the same rows read back in one pass.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    # Natural key first, remaining columns as tiebreak: the same determinism as sorting on every
    # column, but the file reads in a sensible order rather than a hash order.
    natural = [
        c for c in ("area_fips", "state_fips", "reference_month", "size_code") if c in frame.columns
    ]
    ordered = frame.sort(by=natural + [c for c in frame.columns if c not in natural]).rechunk()
    ordered.write_parquet(path, compression="uncompressed", statistics=False)
    return hashlib.sha256(path.read_bytes()).hexdigest()


def predicate_from_stored_metadata(cbp_raw_dir: Path, year: int) -> str:
    """The NAICS predicate for one reference year, read from that year's stored metadata.

    A literal here would contradict Task 11's own test: the predicate name is a property of the
    vintage CBP serves, not of the reference year's NAICS vintage, and Stage 0 measured the two
    disagreeing for 2022 and 2023.
    """
    candidates = sorted(cbp_raw_dir.rglob(f"*{year}{cbp.METADATA_SUFFIX}"))
    if not candidates:
        raise FileNotFoundError(
            f"no stored variables.json for CBP {year}; fetch stores it beside the data file so the "
            "offline rebuild can discover the predicate the same way the online fetch did"
        )
    return cbp.discover_naics_predicate(json.loads(candidates[0].read_text()))


def build_harmonized(
    cfg: Config, *, raw_root: Path, out_root: Path, allow_network: bool = False
) -> dict[str, str]:
    """Assemble every harmonized table from stored bytes and return their output hashes.

    Reads only from `raw_root`. No fetch happens here: acquisition is `fetch`'s job, and keeping
    the two apart is what makes an offline rebuild possible at all (§19 Phase 1).
    """
    if allow_network:
        raise ValueError("build_harmonized never fetches; use `fetch` to acquire bytes first")
    hashes: dict[str, str] = {}

    # REQ-002 binds the pipeline, not the parser: `parse_qcew_monthly` returns whatever rows it
    # is given, which is right for a parser, so the universe filter is applied here -- on the
    # build path -- rather than living as a function nothing calls.
    qcew_frames = [
        qcew.apply_universe_filter(
            qcew.parse_qcew_monthly(
                qcew.read_slice_csv(path.read_bytes()),
                snapshot_id=path.stem,
                release_vintage=path.stem,
                release_status=cfg.sources.qcew.release_status,
                naics_vintage=vintage_for_year(int(path.stem[:4])),
            )
        )
        for path in sorted((raw_root / "qcew").rglob("*.csv"))
    ]
    hashes["qcew_monthly"] = write_parquet_deterministic(
        pl.concat(qcew_frames), out_root / "qcew_monthly.parquet"
    )

    size_frames = [
        qcew_size.parse_qcew_national_size(
            qcew_size.read_by_size_zip(path.read_bytes()),
            snapshot_id=path.stem,
            reference_year=int(path.stem[:4]),
            naics_vintage=vintage_for_year(int(path.stem[:4])),
        )
        for path in sorted((raw_root / "qcew_size").rglob("*.zip"))
    ]
    hashes["qcew_national_size"] = write_parquet_deterministic(
        pl.concat(size_frames), out_root / "qcew_national_size.parquet"
    )

    cbp_frames = []
    # Metadata is skipped by name, not by luck: `fetch` writes `{year}_variables.json` into this
    # same tree, it matches `*.json`, and its stem's first four characters are the same reference
    # year as the data file's.
    for path in sorted(
        p for p in (raw_root / "cbp").rglob("*.json") if not cbp.is_metadata_path(p)
    ):
        year = int(path.stem[:4])
        regime = disclosure.regime_for_year(
            year, fail_on_unknown=cfg.sources.cbp.fail_on_unknown_disclosure_regime
        )
        if regime == disclosure.UNKNOWN_REGIME:
            raise UnknownDisclosureRegimeError(
                f"CBP {year} resolved to {regime!r}; a harmonized table may not record a regime "
                "no source establishes, whatever the config's fail_on_unknown flag permits a "
                "report to say (SRC-CBP-003)"
            )
        cbp_frames.append(
            cbp.parse_cbp_state_size(
                json.loads(path.read_text()),
                snapshot_id=path.stem,
                reference_year=year,
                predicate=predicate_from_stored_metadata(raw_root / "cbp", year),
                naics_vintage=vintage_for_year(year),
                regime=regime,
            )
        )
    hashes["cbp_state_size"] = write_parquet_deterministic(
        pl.concat(cbp_frames), out_root / "cbp_state_size.parquet"
    )

    hashes["bridge"] = write_parquet_deterministic(
        bridge.bridge_frame(_BRIDGE_ROWS), out_root / "bridge.parquet"
    )
    return hashes
