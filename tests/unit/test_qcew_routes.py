"""Slice-route URL construction, the boundary probe, and CSV reading."""

from __future__ import annotations

import hashlib
import io
import json
import re
import zipfile
from pathlib import Path

import httpx
import polars as pl
import pytest

from logging_employment import constants
from logging_employment.ingest import qcew
from logging_employment.ingest.base import HttpFetcher

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "qcew" / "slice_2017q1.csv"
BULK = Path(__file__).resolve().parents[1] / "fixtures" / "qcew" / "bulk_2017.zip"
TARGET_MEMBER = "2017.q1-q4.by_industry/2017.q1-q4 113310 NAICS 113310 Logging.csv"


def _fetcher(handler) -> HttpFetcher:
    fetcher = HttpFetcher(contact_email="who@example.invalid")
    fetcher._client = httpx.Client(transport=httpx.MockTransport(handler))
    return fetcher


def test_slice_url_interpolates_year_quarter_and_industry() -> None:
    assert qcew.slice_url(2017, 1, "113310") == (
        "https://data.bls.gov/cew/data/api/2017/1/industry/113310.csv"
    )


def test_boundary_probe_returns_the_earliest_year_that_answers() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        year = int(str(request.url).split("/api/")[1].split("/")[0])
        if year < 2015:
            return httpx.Response(404, content=b"")
        return httpx.Response(200, content=FIXTURE.read_bytes())

    assert qcew.probe_slice_boundary(_fetcher(handler), "113310", range(2010, 2020)) == 2015


def test_boundary_probe_does_not_hard_code_a_year() -> None:
    # D5 and Stage 0's auditor note both forbid it: the earliest year served was "a status
    # measured in one run, not a property of the route".
    source = Path(qcew.__file__).read_text()
    assert "2014" not in source


def test_every_slice_column_is_read_as_a_string() -> None:
    frame = qcew.read_slice_csv(FIXTURE.read_bytes())
    assert set(frame.schema.values()) == {pl.String}
    assert frame["area_fips"].str.len_chars().min() == 5  # leading zeros survive


def test_the_fixture_carries_the_columns_the_parser_needs() -> None:
    frame = qcew.read_slice_csv(FIXTURE.read_bytes())
    for column in (
        "area_fips",
        "own_code",
        "industry_code",
        "agglvl_code",
        "size_code",
        "year",
        "qtr",
        "disclosure_code",
        "qtrly_estabs",
        "month1_emplvl",
        "month2_emplvl",
        "month3_emplvl",
        "total_qtrly_wages",
    ):
        assert column in frame.columns


def test_route_selection_uses_the_measured_boundary() -> None:
    assert qcew.route_for_year(2017, earliest_slice_year=2014) == "slice"
    # Forced: today's measured boundary makes this unreachable in production, so the bulk branch
    # would otherwise never execute.
    assert qcew.route_for_year(2017, earliest_slice_year=2020) == "bulk"


def test_the_bulk_fixture_carries_the_audited_member_bytes() -> None:
    """`bulk_2017.zip` is reduced, so pin the member the reduction was supposed to preserve.

    The fixture is not the archive Stage 0 fetched -- that one is 439 MB across 2,232 members and
    untrackable -- but the target member inside it must still be byte-identical to the audited
    archive's. This asserts that, rather than asserting that `tests/fixtures/qcew/README.md`
    says so.
    """
    with zipfile.ZipFile(io.BytesIO(BULK.read_bytes())) as archive:
        members = archive.namelist()
        digest = hashlib.sha256(archive.read(TARGET_MEMBER)).hexdigest()
    assert digest == "47bfbef888054477d4fc4fcf4c2a04e70b72610ec4125eeb279c613a14c48caa"
    # More than one member, or the filter below narrows one name to one name and proves nothing.
    assert len(members) == 4


def test_bulk_columns_are_renamed_to_the_slice_vocabulary() -> None:
    frame = qcew.read_bulk_zip(BULK.read_bytes(), constants.INDUSTRY_CODE)
    assert "qtrly_estabs" in frame.columns
    assert "qtrly_estabs_count" not in frame.columns
    for bulk_name in qcew.BULK_TO_SLICE_COLUMNS:
        assert bulk_name not in frame.columns


def test_both_routes_agree_on_the_columns_the_parser_reads() -> None:
    slice_frame = qcew.read_slice_csv(FIXTURE.read_bytes())
    bulk_frame = qcew.read_bulk_zip(BULK.read_bytes(), constants.INDUSTRY_CODE)
    needed = {
        "area_fips",
        "own_code",
        "industry_code",
        "agglvl_code",
        "size_code",
        "year",
        "qtr",
        "disclosure_code",
        "qtrly_estabs",
        "month1_emplvl",
        "month2_emplvl",
        "month3_emplvl",
        "total_qtrly_wages",
    }
    assert needed <= set(slice_frame.columns)
    assert needed <= set(bulk_frame.columns)


def test_bulk_only_title_columns_are_dropped() -> None:
    frame = qcew.read_bulk_zip(BULK.read_bytes(), constants.INDUSTRY_CODE)
    for title_column in qcew.BULK_ONLY_TITLE_COLUMNS:
        assert title_column not in frame.columns


def test_the_member_filter_picks_the_target_among_near_misses() -> None:
    """The fixture carries decoys, so the filter narrows many names to one, as in production.

    Against a single-member fixture this function is indistinguishable from one with no filter
    at all -- deleting the comprehension leaves every other test here green.
    """
    frame = qcew.read_bulk_zip(BULK.read_bytes(), constants.INDUSTRY_CODE)
    assert frame["industry_code"].unique().to_list() == [constants.INDUSTRY_CODE]


def test_an_ambiguous_industry_substring_fails_closed() -> None:
    """Matching is unanchored, so a shorter code can hit several members (§18.3: raise).

    `11331` is `113310`'s parent and publishes under the same "Logging" title; the digits also
    fall inside `111331 Apple orchards`. That is a property of the real archive, not of a
    constructed one, so the fixture's own members demonstrate it.
    """
    with pytest.raises(ValueError, match="expected one member for industry 11331"):
        qcew.read_bulk_zip(BULK.read_bytes(), "11331")


# --- the bulk route, composed ------------------------------------------------------------------


def _parsed(raw_frame: pl.DataFrame) -> pl.DataFrame:
    """Both routes through the same normalization, so the comparison is of data and not of call
    arguments."""
    return qcew.apply_universe_filter(
        qcew.parse_qcew_monthly(
            raw_frame,
            snapshot_id="fixture",
            release_vintage="2026-09-05",
            release_status="final",
            naics_vintage="2017",
        )
    )


def test_the_bulk_route_yields_the_same_rows_as_the_slice_route() -> None:
    """The two routes are alternatives for the same data, and nothing composed them end to end
    until now: route_for_year and read_bulk_zip were each tested alone, and read_bulk_zip's output
    had never been fed to parse_qcew_monthly anywhere in the suite. Asserts the rows agree, not
    merely that the chain ran -- a smoke chain would pass without testing what its name claims.

    This does not prove any production caller composes them: read_bulk_zip has no caller in src/,
    and build_harmonized reads only *.csv through read_slice_csv."""
    assert qcew.route_for_year(2017, earliest_slice_year=2020) == "bulk"

    bulk = _parsed(qcew.read_bulk_zip(BULK.read_bytes(), constants.INDUSTRY_CODE))
    slice_ = _parsed(qcew.read_slice_csv(FIXTURE.read_bytes()))

    # The bulk member carries q1-q4 in one file; the slice fixture is one quarter.
    bulk_q1 = bulk.filter(pl.col("reference_month") <= "2017-03")
    assert bulk_q1.height == slice_.height

    joined = bulk_q1.join(slice_, on=["area_fips", "reference_month"], how="inner", suffix="_s")
    assert joined.height == slice_.height
    for column in ("employment_value", "observation_status", "source_row_hash"):
        assert joined.filter(pl.col(column) != pl.col(f"{column}_s")).height == 0


def test_bulk_url_interpolates_the_reference_year() -> None:
    """The third function of the bulk trio, and the only one no test called: route_for_year's bulk
    outcome and read_bulk_zip were both asserted, bulk_url never was."""
    assert (
        qcew.bulk_url(2017)
        == "https://data.bls.gov/cew/data/files/2017/csv/2017_qtrly_by_industry.zip"
    )


def _qcew_routes_findings() -> tuple[dict, dict]:
    """The tracked findings document, not data/raw/audit/: data/ is gitignored in its entirety, so
    a boundary pin written against the summary is a silent skip in a clean clone."""
    document = (
        Path(__file__).resolve().parents[2] / "specs" / "findings" / "source-audit.md"
    ).read_text(encoding="utf-8")
    (block,) = [
        b
        for b in re.split(r"^### `", document, flags=re.MULTILINE)[1:]
        if b.startswith("qcew_routes`")
    ]

    def fenced(label: str) -> dict:
        return json.loads(block.split(f"**{label}**:\n\n```json\n", 1)[1].split("\n```", 1)[0])

    return fenced("findings"), fenced("coverage_span")


def test_every_window_year_still_routes_to_the_slice_endpoint() -> None:
    """Derived, not typed: the measured boundary and the window both come out of the tracked
    findings document at runtime, so a re-audit that moves the boundary past a window year turns
    this red instead of leaving a prose condition nobody re-reads. What production would then do is
    not take the bulk route -- probe_slice_boundary would face an all-404 candidate range and raise
    ValueError -- which is why this is a monitor and not a coverage claim."""
    findings, span = _qcew_routes_findings()
    earliest = int(findings["earliest_year_served"])
    window = range(int(span["window_start"][:4]), int(span["window_end"][:4]) + 1)

    assert findings["bulk_years_required"] == []
    assert {qcew.route_for_year(year, earliest) for year in window} == {"slice"}


REAL_BULK = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "raw"
    / "audit"
    / "qcew_routes"
    / "bulk"
    / "2017_qtrly_by_industry.zip"
)


def _recorded_digest() -> str:
    """From the tracked extracts manifest, never hard-coded: a typed digest is a transcription
    defect, and this one is 64 characters of it."""
    rows = (
        (Path(__file__).resolve().parents[2] / "specs" / "findings" / "source-audit-extracts.csv")
        .read_text(encoding="utf-8")
        .splitlines()
    )
    (row,) = [
        r for r in rows if r.startswith("qcew_routes,") and "bulk/2017_qtrly_by_industry.zip," in r
    ]
    return row.split(",")[3]


@pytest.mark.slow
def test_the_member_selector_is_unique_in_the_real_archive_not_just_the_fixture() -> None:
    """tests/fixtures/qcew/README.md concedes of the unanchored substring selector that the target
    "really is unique here -- but that is a fact about this data, not a guarantee from the code."
    A four-member fixture cannot establish otherwise; the 2,232-member archive can. Skips where the
    gitignored archive is absent, per the tests/audit/test_qcew_codes.py:389 idiom.

    The final equality is the fidelity statement the other tests rest on: only the CONTAINER was
    reduced, not the data."""
    if not REAL_BULK.exists():
        pytest.skip(f"{REAL_BULK} not present; run scripts/audit/qcew_routes.py first")

    raw = REAL_BULK.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == _recorded_digest()

    names = zipfile.ZipFile(io.BytesIO(raw)).namelist()
    assert len(names) == 2232
    assert len([n for n in names if constants.INDUSTRY_CODE in n]) == 1
    assert len([n for n in names if "11331" in n]) == 3

    real = qcew.read_bulk_zip(raw, constants.INDUSTRY_CODE)
    assert real.equals(qcew.read_bulk_zip(BULK.read_bytes(), constants.INDUSTRY_CODE))

    with pytest.raises(ValueError, match="expected one member for industry 11331"):
        qcew.read_bulk_zip(raw, "11331")
