"""SRC-QSIZE-001..004: March classification retained, dimensionality verified from contents."""

from __future__ import annotations

import io
import re
import zipfile
from pathlib import Path

import polars as pl
import pytest

from logging_employment import constants
from logging_employment.contracts import QCEW_NATIONAL_SIZE_SCHEMA, validate_frame
from logging_employment.errors import MissingCrossTabulationError, UnknownSizeCodeError
from logging_employment.ingest import qcew_size

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "qcew_size" / "2017_q1_by_size.zip"


def _frame() -> pl.DataFrame:
    return qcew_size.read_by_size_zip(FIXTURE.read_bytes())


def _parsed() -> pl.DataFrame:
    return qcew_size.parse_qcew_national_size(
        _frame(), snapshot_id="s", reference_year=2017, naics_vintage="NAICS 2017"
    )


def test_the_assertion_passes_on_the_real_file() -> None:
    # SRC-QSIZE-002: verified from file contents, not inferred from documentation.
    qcew_size.assert_no_state_industry_size(_frame(), constants.INDUSTRY_CODE)


def test_the_assertion_names_the_level_when_a_state_size_row_appears() -> None:
    doctored = pl.DataFrame(
        {
            "area_fips": ["01000"],
            "agglvl_code": ["68"],
            "industry_code": [constants.INDUSTRY_CODE],
            "size_code": ["3"],
            "qtrly_estabs": ["5"],
            "month1_emplvl": ["50"],
            "year": ["2017"],
            "qtr": ["1"],
            "disclosure_code": [""],
        }
    )
    with pytest.raises(MissingCrossTabulationError, match="68"):
        qcew_size.assert_no_state_industry_size(doctored, constants.INDUSTRY_CODE)


def test_parsed_output_matches_the_declared_schema() -> None:
    validate_frame(_parsed(), QCEW_NATIONAL_SIZE_SCHEMA, "qcew_national_size")


def test_size_bounds_come_from_the_published_titles() -> None:
    assert qcew_size.SIZE_CLASS_BOUNDS["1"] == (0, 4)
    assert qcew_size.SIZE_CLASS_BOUNDS["7"] == (250, 499)


def test_the_march_reference_is_recorded_on_every_row() -> None:
    # SRC-QSIZE-001: the parser must retain that size class is determined by March employment.
    out = _parsed()
    assert out["reference_month"].unique().to_list() == ["2017-03"]
    assert out["reference_quarter"].unique().to_list() == ["2017Q1"]


# --- what the file itself says, rather than what this module types about it -------------------


def _titles_from_the_fixture() -> dict[str, str]:
    """`size_code` -> `size_title`, read from the raw member before the reader drops titles."""
    with zipfile.ZipFile(io.BytesIO(FIXTURE.read_bytes())) as archive:
        member = next(n for n in archive.namelist() if n.endswith(".csv"))
        raw = pl.read_csv(archive.read(member), infer_schema_length=0)
    pairs = raw.select("size_code", "size_title").unique().sort("size_code")
    return dict(zip(pairs["size_code"], pairs["size_title"], strict=True))


def _bounds_from_title(title: str) -> tuple[int, int | None]:
    """Parse an employment range out of a published size title, or fail loudly.

    Three shapes occur: "Fewer than 5 ...", "5 to 9 ...", "1000 or more ...". Anything else is a
    title shape this derivation does not understand, and guessing at it is what the exercise is
    meant to avoid.
    """
    if match := re.match(r"^Fewer than (\d+) ", title):
        return (0, int(match.group(1)) - 1)
    if match := re.match(r"^(\d+) to (\d+) ", title):
        return (int(match.group(1)), int(match.group(2)))
    if match := re.match(r"^(\d+) or more ", title):
        return (int(match.group(1)), None)
    raise AssertionError(f"unrecognized size title shape: {title!r}")


def test_size_class_bounds_agree_with_the_titles_the_file_publishes() -> None:
    """The constant is checked against data in scope, not trusted as typed.

    `size_code` 0 is excluded deliberately: "All establishment sizes" is a total over the
    dimension, not a range within it, so it has no bounds to carry.
    """
    titles = _titles_from_the_fixture()
    derived = {code: _bounds_from_title(title) for code, title in titles.items() if code != "0"}
    assert derived == qcew_size.SIZE_CLASS_BOUNDS


def test_every_size_class_the_file_publishes_carries_bounds() -> None:
    """No emitted row may lose its bounds silently.

    The by-size file publishes codes 8 and 9 as well; with a bounds table stopping at 7 they were
    16.3% of this parser's output and would have carried null `size_lower` / `size_upper`.
    """
    out = _parsed()
    assert out["size_lower"].null_count() == 0
    assert out["size_upper"].null_count() == out.filter(pl.col("size_class") == "9").height


def test_an_unmapped_size_code_halts_rather_than_nulling_its_bounds() -> None:
    doctored = _frame().with_columns(
        pl.when(pl.col("size_code") == "1")
        .then(pl.lit("Z"))
        .otherwise(pl.col("size_code"))
        .alias("size_code")
    )
    with pytest.raises(UnknownSizeCodeError, match="Z"):
        qcew_size.parse_qcew_national_size(
            doctored, snapshot_id="s", reference_year=2017, naics_vintage="NAICS 2017"
        )


# --- the by-size file speaks the bulk vocabulary ----------------------------------------------


def test_the_reader_reconciles_the_bulk_column_vocabulary() -> None:
    """The by-size file ships `qtrly_estabs_count`, not `qtrly_estabs`.

    Same publisher, same disagreement Task 8 already reconciled for the bulk route, so the same
    mapping is reused rather than a second one written.
    """
    frame = _frame()
    assert "qtrly_estabs" in frame.columns
    assert "qtrly_estabs_count" not in frame.columns
    for title_column in ("agglvl_title", "area_title", "industry_title", "own_title", "size_title"):
        assert title_column not in frame.columns


# --- the dimensionality guarantee has to hold in the build, not only in this file --------------


def test_the_parser_itself_enforces_the_dimensionality_assertion() -> None:
    """SRC-QSIZE-002 binds the parser, so calling it must be unavoidable.

    Left as a standalone helper the check would fire only from this suite, and the build path
    would carry no such guarantee.
    """
    doctored = pl.concat(
        [
            _frame(),
            _frame()
            .filter(pl.col("industry_code") == constants.INDUSTRY_CODE)
            .head(1)
            .with_columns(area_fips=pl.lit("01000"), agglvl_code=pl.lit("68")),
        ]
    )
    with pytest.raises(MissingCrossTabulationError, match="68"):
        qcew_size.parse_qcew_national_size(
            doctored, snapshot_id="s", reference_year=2017, naics_vintage="NAICS 2017"
        )


def test_no_emitted_row_has_zero_establishments() -> None:
    """Why a binary observed/suppressed status is safe for this file.

    `qcew_monthly` needs a true-zero rule because suppressed and genuinely-zero cells both
    publish `0`. Here the measurement says the second case does not arise, so the binary status
    is not an omission. If a later file breaks that, this test says so rather than the table
    quietly mislabelling a zero as observed -- which is what INV-003 forbids.
    """
    assert _parsed().filter(pl.col("establishments") == 0).height == 0
