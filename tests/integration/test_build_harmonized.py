"""§19 Phase 1 acceptance: an offline rebuild is byte-identical."""

from __future__ import annotations

import shutil
from pathlib import Path

import httpx
import polars as pl
import pytest

from logging_employment.build import build_harmonized, write_parquet_deterministic
from logging_employment.config import load_config
from logging_employment.errors import UnknownDisclosureRegimeError

REPO = Path(__file__).resolve().parents[2]
FIXTURES = REPO / "tests" / "fixtures"


@pytest.fixture()
def frozen_raw(tmp_path: Path) -> Path:
    """A `data/raw`-shaped tree holding the audited fixture bytes.

    The CBP branch stores that year's `variables.json` beside its data response, because that is
    what `fetch` does and what `predicate_from_stored_metadata` reads. A tree without it cannot
    exercise the rebuild at all, and a build that globs `*.json` indiscriminately would try to
    parse it as a data response.
    """
    raw = tmp_path / "raw"
    (raw / "qcew" / "frozen").mkdir(parents=True)
    shutil.copy(FIXTURES / "qcew" / "slice_2017q1.csv", raw / "qcew" / "frozen" / "2017q1.csv")
    (raw / "qcew_size" / "frozen").mkdir(parents=True)
    shutil.copy(
        FIXTURES / "qcew_size" / "2017_q1_by_size.zip",
        raw / "qcew_size" / "frozen" / "2017_q1_by_size.zip",
    )
    (raw / "cbp" / "frozen").mkdir(parents=True)
    shutil.copy(FIXTURES / "cbp" / "data_113310_2023.json", raw / "cbp" / "frozen" / "2023.json")
    shutil.copy(
        FIXTURES / "cbp" / "variables_2023.json", raw / "cbp" / "frozen" / "2023_variables.json"
    )
    return raw


def _cfg():
    return load_config(REPO / "config.yaml")


def test_rebuild_is_byte_identical(frozen_raw: Path, tmp_path: Path) -> None:
    first = build_harmonized(_cfg(), raw_root=frozen_raw, out_root=tmp_path / "a")
    second = build_harmonized(_cfg(), raw_root=frozen_raw, out_root=tmp_path / "b")
    assert first == second
    assert set(first) == {"qcew_monthly", "qcew_national_size", "cbp_state_size", "bridge"}


def test_the_rebuild_compares_two_runs_rather_than_a_pinned_hash(
    frozen_raw: Path, tmp_path: Path
) -> None:
    # The exit criterion is reproducibility, not a particular byte string. Pinning a literal here
    # would make every later task that changes a schema look like a determinism regression.
    first = build_harmonized(_cfg(), raw_root=frozen_raw, out_root=tmp_path / "a")
    assert all(len(digest) == 64 for digest in first.values())


def test_rebuild_attempts_no_network_call(
    frozen_raw: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def explode(*args: object, **kwargs: object) -> None:
        raise AssertionError("build-harmonized attempted a network call")

    monkeypatch.setattr(httpx.Client, "send", explode)
    monkeypatch.setattr(httpx, "get", explode)
    monkeypatch.setattr(httpx.Client, "request", explode)
    build_harmonized(_cfg(), raw_root=frozen_raw, out_root=tmp_path / "offline")


def test_no_harmonized_table_carries_a_retrieval_timestamp(
    frozen_raw: Path, tmp_path: Path
) -> None:
    out = tmp_path / "c"
    build_harmonized(_cfg(), raw_root=frozen_raw, out_root=out)
    for path in out.glob("*.parquet"):
        assert "retrieved_at_utc" not in pl.read_parquet_schema(path)


def test_stored_metadata_is_not_parsed_as_a_data_response(frozen_raw: Path, tmp_path: Path) -> None:
    # `fetch` stores `{year}_variables.json` beside `{year}.json`. A build that globs `*.json`
    # picks up both, and `2023_variables` even yields the same reference year under `stem[:4]`.
    out = tmp_path / "d"
    build_harmonized(_cfg(), raw_root=frozen_raw, out_root=out)
    frame = pl.read_parquet(out / "cbp_state_size.parquet")
    assert frame.height == 188
    assert frame["reference_year"].unique().to_list() == [2023]


def test_the_cbp_predicate_is_read_from_the_stored_metadata(
    frozen_raw: Path, tmp_path: Path
) -> None:
    # SRC-CBP-001 offline: the rebuild discovers the predicate the same way the fetch did.
    from logging_employment.build import predicate_from_stored_metadata

    assert predicate_from_stored_metadata(frozen_raw / "cbp", 2023) == "NAICS2017"


def test_a_missing_metadata_file_halts_rather_than_assuming_a_predicate(
    frozen_raw: Path, tmp_path: Path
) -> None:
    from logging_employment.build import predicate_from_stored_metadata

    with pytest.raises(FileNotFoundError, match="2019"):
        predicate_from_stored_metadata(frozen_raw / "cbp", 2019)


def test_the_build_never_persists_an_unknown_disclosure_regime(
    frozen_raw: Path, tmp_path: Path
) -> None:
    # `regime_for_year(..., fail_on_unknown=False)` returns "unknown", and config can set that
    # flag. The flag exists so a *report* can record the gap; a harmonized table recording a
    # regime no source establishes is a different thing, and the build refuses it either way.
    shutil.copy(
        frozen_raw / "cbp" / "frozen" / "2023.json", frozen_raw / "cbp" / "frozen" / "2024.json"
    )
    shutil.copy(
        frozen_raw / "cbp" / "frozen" / "2023_variables.json",
        frozen_raw / "cbp" / "frozen" / "2024_variables.json",
    )
    permissive = _cfg().model_copy(deep=True)
    permissive.sources.cbp.__dict__["fail_on_unknown_disclosure_regime"] = False
    with pytest.raises(UnknownDisclosureRegimeError, match="2024"):
        build_harmonized(permissive, raw_root=frozen_raw, out_root=tmp_path / "e")


def test_a_shuffled_frame_writes_the_same_bytes(tmp_path: Path) -> None:
    # The determinism guarantee lives in `write_parquet_deterministic`, so test it directly:
    # Parquet preserves input order, and two runs that assemble the same rows in different orders
    # must still produce one file.
    frame = pl.DataFrame(
        {"state_fips": ["02", "01", "01"], "size_code": ["001", "210", "001"], "v": [3, 2, 1]}
    )
    shuffled = frame.sample(fraction=1.0, shuffle=True, seed=7)
    a = write_parquet_deterministic(frame, tmp_path / "a.parquet")
    b = write_parquet_deterministic(shuffled, tmp_path / "b.parquet")
    assert a == b
    assert pl.read_parquet(tmp_path / "a.parquet")["v"].to_list() == [1, 2, 3]


def test_build_harmonized_refuses_to_fetch(frozen_raw: Path, tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="never fetches"):
        build_harmonized(_cfg(), raw_root=frozen_raw, out_root=tmp_path / "f", allow_network=True)


def test_the_persisted_qcew_table_is_the_estimand_universe(
    frozen_raw: Path, tmp_path: Path
) -> None:
    # REQ-002. `apply_universe_filter` exists in `ingest.qcew`; what makes it a pipeline guarantee
    # rather than an available helper is that the build path calls it. The fixture quarter carries
    # public-ownership rows, county rows and Puerto Rico, so this can fail.
    from logging_employment import constants

    out = tmp_path / "g"
    build_harmonized(_cfg(), raw_root=frozen_raw, out_root=out)
    frame = pl.read_parquet(out / "qcew_monthly.parquet")
    assert frame["ownership_code"].unique().to_list() == [constants.PRIVATE_OWN_CODE]
    assert set(frame["area_fips"].unique().to_list()) <= (
        constants.STATE_AREAS | {constants.NATIONAL_AREA}
    )
    assert frame["suppression_type"].unique().to_list() == ["unknown"]
