"""Deterministic assembly of the harmonized layer from frozen raw bytes."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import polars as pl

from .config import Config
from .constants import QCEW_PARENT_INDUSTRY, QCEW_PARENT_STATE_AGGLVL
from .errors import AmbiguousSnapshotError, ConceptViolationError, UnknownDisclosureRegimeError
from .harmonize import bridge, disclosure
from .harmonize.naics import assert_113310_survives_the_window, vintage_for_year
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
    ordered = deterministic_order(frame).rechunk()
    ordered.write_parquet(path, compression="uncompressed", statistics=False)
    return hashlib.sha256(path.read_bytes()).hexdigest()


def deterministic_order(frame: pl.DataFrame) -> pl.DataFrame:
    """The row order `write_parquet_deterministic` writes in.

    Natural key first, remaining columns as tiebreak: the same determinism as sorting on every
    column, but the file reads in a sensible order rather than a hash order.

    Public so a golden test can put an in-memory frame into the same order as the file it is
    compared against. A test that re-implemented this sort would pass until the two drifted, and
    then fail for a reason that has nothing to do with the values.
    """
    natural = [
        c for c in ("area_fips", "state_fips", "reference_month", "size_code") if c in frame.columns
    ]
    return frame.sort(by=natural + [c for c in frame.columns if c not in natural])


def _manifest_paths(manifest_path: Path, source_id: str) -> list[Path]:
    """Every `raw_path` the run manifest records for one source."""
    frame = pl.read_parquet(manifest_path).filter(pl.col("source_id") == source_id)
    return [Path(p) for p in frame["raw_path"].to_list()]


def _is_cbp_metadata(source_id: str, path: Path) -> bool:
    """Whether a stored file is CBP variables metadata, which is never a data snapshot."""
    return source_id == "cbp" and cbp.is_metadata_path(path)


def predicate_from_stored_metadata(
    cbp_raw_dir: Path, year: int, *, manifest_path: Path | None = None
) -> str:
    """The NAICS predicate for one reference year, read from that year's stored metadata.

    A literal here would contradict Task 11's own test: the predicate name is a property of the
    vintage CBP serves, not of QCEW's reference-year vintage rule, and the two disagree for 2022
    and 2023, where CBP still serves `NAICS2017`.

    ONE COPY, CHOSEN THE WAY `snapshot_paths` CHOOSES A DATA FILE (D-097). The predicate decides
    which rows Census returns, and CBP's bytes are not reproducible, so the store can hold two
    copies of one year's metadata. The manifest's copy wins when the manifest lists one. Otherwise
    more than one stored copy halts, where this used to take the lowest sha256 silently.
    """
    name = cbp.metadata_filename(year)
    listed: list[Path] = []
    if manifest_path is not None and manifest_path.exists():
        listed = [p for p in _manifest_paths(manifest_path, "cbp") if p.name == name]
    if listed:
        missing = sorted(str(p) for p in listed if not p.exists())
        if missing:
            raise FileNotFoundError(
                f"{manifest_path} lists CBP {year} metadata absent from the store, {missing[0]}; "
                "fetch again or build without a manifest"
            )
        candidates = sorted(listed)
    else:
        candidates = sorted(cbp_raw_dir.rglob(name))
    if not candidates:
        raise FileNotFoundError(
            f"no stored variables.json for CBP {year}; fetch stores it beside the data file so the "
            "offline rebuild can discover the predicate the same way the online fetch did"
        )
    if len(candidates) > 1:
        raise AmbiguousSnapshotError(
            f"CBP {year} has {len(candidates)} stored copies of {name}: "
            f"{[str(p) for p in candidates]}. The predicate each carries decides which rows Census "
            "returns, so none is picked by sort order. Build with the run manifest, which records "
            "the copy the run used."
        )
    return cbp.discover_naics_predicate(json.loads(candidates[0].read_text()))


def snapshot_paths(
    source_id: str,
    raw_root: Path,
    pattern: str,
    *,
    manifest_path: Path | None = None,
) -> list[Path]:
    """The stored files this build should read for one source, one per reference key.

    The content-addressed store keys objects by their sha256, so a source that answers the same
    request with different bytes lands a second object beside the first. CBP does exactly that:
    its responses are set-identical across fetches but arrive in a different row order, so every
    re-fetch stores another copy of the same year. A build that globbed the tree would then
    concatenate both, and INV-007 forbids that silent stacking. The filename carries the reference
    key (`2023.json`, `2017q1.csv`) while the hash is the directory, so grouping by name groups by
    key.

    `manifest_path` resolves the ambiguity when it can: the run manifest records the `raw_path` of
    each snapshot that belongs to the run, which is what makes "the bytes this run was built from"
    a recoverable fact rather than a guess. Without it, an ambiguous store halts rather than
    picking a copy by sort order.

    CBP METADATA IS NEVER A DATA SNAPSHOT, IN EITHER BRANCH. `fetch` records `{year}_variables.json`
    in the manifest as well as storing it (D-097), so the manifest branch applies the same name
    filter as the glob branch. `predicate_from_stored_metadata` is the one reader of those files.
    """
    if manifest_path is not None and manifest_path.exists():
        listed = [
            path
            for path in _manifest_paths(manifest_path, source_id)
            if not _is_cbp_metadata(source_id, path)
        ]
        if listed:
            missing = sorted(str(p) for p in listed if not p.exists())
            if missing:
                raise FileNotFoundError(
                    f"{manifest_path} lists {len(missing)} {source_id} snapshot(s) absent from the "
                    f"store, starting with {missing[0]}; fetch again or build without a manifest"
                )
            return sorted(listed)

    candidates = [
        p for p in (raw_root / source_id).rglob(pattern) if not _is_cbp_metadata(source_id, p)
    ]
    by_key: dict[str, list[Path]] = {}
    for path in candidates:
        by_key.setdefault(path.name, []).append(path)
    ambiguous = {k: sorted(str(p) for p in v) for k, v in by_key.items() if len(v) > 1}
    if ambiguous:
        key = min(ambiguous)
        raise AmbiguousSnapshotError(
            f"{source_id} has {len(ambiguous)} reference key(s) with more than one stored "
            f"snapshot, e.g. {key} -> {ambiguous[key]}; concatenating them would stack two "
            "vintages of the same cell (INV-007). Build with the run manifest, which records "
            "which snapshot the run used."
        )
    return [by_key[k][0] for k in sorted(by_key)]


def state_parent_rows(
    raw: bytes, *, snapshot_id: str, release_status: str, naics_vintage: str
) -> pl.DataFrame:
    """The private `113` state rows of one stored parent slice (R-PM-1).

    Parsed at `QCEW_PARENT_STATE_AGGLVL`, universe-filtered exactly as the `113310` table is
    (REQ-002), then kept to state rows of the parent industry: the slice also carries national, MSA
    and county rows, none of which bounds a state cell. AN EMPTY RESULT HALTS. The level is a
    measurement, not a documented constant, and a changed level would otherwise build a table with
    no rows -- a margin that silently vanished rather than one measured absent.
    """
    parsed = qcew.apply_universe_filter(
        qcew.parse_qcew_monthly(
            qcew.read_slice_csv(raw),
            snapshot_id=snapshot_id,
            release_vintage=snapshot_id,
            release_status=release_status,
            naics_vintage=naics_vintage,
            state_agglvl=QCEW_PARENT_STATE_AGGLVL,
        )
    )
    rows = parsed.filter(
        (pl.col("area_type") == "state") & (pl.col("industry_code") == QCEW_PARENT_INDUSTRY)
    )
    if rows.is_empty():
        raise ConceptViolationError(
            f"{snapshot_id}: the stored parent slice carries no private {QCEW_PARENT_INDUSTRY} "
            f"state row at agglvl {QCEW_PARENT_STATE_AGGLVL}; the level is measured, not "
            "documented, so a changed one halts rather than building an empty parent table (R-PM-1)"
        )
    return rows


def build_harmonized(
    cfg: Config,
    *,
    raw_root: Path,
    out_root: Path,
    allow_network: bool = False,
    manifest_path: Path | None = None,
) -> dict[str, str]:
    """Assemble every harmonized table from stored bytes and return their output hashes.

    Reads only from `raw_root`. No fetch happens here: acquisition is `fetch`'s job, and keeping
    the two apart is what makes an offline rebuild possible at all (§19 Phase 1).
    """
    if allow_network:
        raise ValueError("build_harmonized never fetches; use `fetch` to acquire bytes first")
    # §3.1: "The ETL MUST verify the 113310 mapping mechanically." Checked before the first table
    # is written, so a re-vendored crosswalk that no longer carries 113310 unchanged across the
    # window's two vintages halts the build, not only the unit test that exercises the guard
    # (D-102).
    assert_113310_survives_the_window()
    hashes: dict[str, str] = {}
    # Resolved BEFORE the first table is written. A raw store without the parent series would
    # otherwise leave a partial staged layer behind -- one whose digests re-id a run from inputs no
    # build ever completed.
    parent_paths = snapshot_paths("qcew_parent", raw_root, "*.csv", manifest_path=manifest_path)
    if not parent_paths:
        raise FileNotFoundError(
            f"no stored qcew_parent slice under {raw_root / 'qcew_parent'}; the §9.3 parent margin "
            "needs the private 113 state series -- run `logging-estimates fetch --source "
            "qcew_parent` first"
        )

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
        for path in snapshot_paths("qcew", raw_root, "*.csv", manifest_path=manifest_path)
    ]
    hashes["qcew_monthly"] = write_parquet_deterministic(
        pl.concat(qcew_frames), out_root / "qcew_monthly.parquet"
    )
    hashes["qcew_state_parent"] = write_parquet_deterministic(
        pl.concat(
            [
                state_parent_rows(
                    path.read_bytes(),
                    snapshot_id=path.stem,
                    release_status=cfg.sources.qcew.release_status,
                    naics_vintage=vintage_for_year(int(path.stem[:4])),
                )
                for path in parent_paths
            ]
        ),
        out_root / "qcew_state_parent.parquet",
    )

    size_frames = [
        qcew_size.parse_qcew_national_size(
            qcew_size.read_by_size_zip(path.read_bytes()),
            snapshot_id=path.stem,
            reference_year=int(path.stem[:4]),
            naics_vintage=vintage_for_year(int(path.stem[:4])),
        )
        for path in snapshot_paths("qcew_size", raw_root, "*.zip", manifest_path=manifest_path)
    ]
    hashes["qcew_national_size"] = write_parquet_deterministic(
        pl.concat(size_frames), out_root / "qcew_national_size.parquet"
    )

    cbp_frames = []
    # Metadata is skipped by name, not by luck: `fetch` writes `{year}_variables.json` into this
    # same tree, it matches `*.json`, and its stem's first four characters are the same reference
    # year as the data file's. Both `snapshot_paths` branches skip it, because the manifest records
    # the metadata retrieval too (D-097).
    for path in snapshot_paths("cbp", raw_root, "*.json", manifest_path=manifest_path):
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
        predicate = predicate_from_stored_metadata(
            raw_root / "cbp", year, manifest_path=manifest_path
        )
        cbp_frames.append(
            cbp.parse_cbp_state_size(
                json.loads(path.read_text()),
                snapshot_id=path.stem,
                reference_year=year,
                predicate=predicate,
                # READ OFF CBP'S OWN METADATA (D-114), not `vintage_for_year`, which is BLS's rule
                # for QCEW. The stored metadata serves `NAICS2017`, labelled "2017 NAICS code", for
                # every window year, so that rule stamped the 2022 and 2023 rows with a vintage
                # their own source contradicts. Nothing reads the column -- every CBP consumer keys
                # on `reference_year` -- which is why the correction waited for a rebuild that
                # re-ids the run anyway (plan 15).
                naics_vintage=cbp.vintage_for_predicate(predicate),
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
