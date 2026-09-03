"""Judgment-logic tests for the 113310 private panel.

Three hazards live here, all of them silent rather than loud:

1. `pl.col("disclosure_code").str.strip_chars() == "N"` yields **null**, not `False`, wherever
   the column is empty, and a null `suppressed` is dropped from every `.mean()` denominator --
   reporting a suppression share of `1.0` for any state that has any suppression at all.
2. A suppressed row publishes `0` in the employment columns. Read as a true zero it becomes a
   real observation of no logging jobs (INV-003).
3. A run of suppressed months is only a run if the months are adjacent. A state whose rows stop
   partway through the window and resume later would otherwise have two runs merged into one,
   overstating the "long runs" regime Stage 4 is sized from.

`qcew_panel` is imported bare, like `_common`, per `tests/conftest.py`. Importing it is inert:
the module's only side effects sit behind `if __name__ == "__main__"`.
"""

from __future__ import annotations

import polars as pl

import pytest

from qcew_panel import (
    PANEL_SCHEMA,
    _conform,
    build_long,
    build_panel,
    disclosure_code_values,
    estabs_survival,
    run_lengths,
)


def write_fixture(tmp_path, monkeypatch, extra_rows=()):
    """Two states over one quarter: one clean row, one suppressed row, one county row.

    `extra_rows` appends slice rows without disturbing those four, so the tests below that
    came from the task brief keep asserting on the fixture the brief described.
    """
    import json

    import _common as c

    monkeypatch.setattr(c, "AUDIT_ROOT", tmp_path)
    header = ("area_fips,own_code,industry_code,agglvl_code,size_code,year,qtr,"
              "disclosure_code,qtrly_estabs,month1_emplvl,month2_emplvl,month3_emplvl")
    rows = [
        'US000,5,113310,18,0,2017,1,,100,1000,1000,1000',
        '01000,5,113310,58,0,2017,1,,40,400,400,400',
        '41000,5,113310,58,0,2017,1,N,50,0,0,0',
        '01001,5,113310,78,0,2017,1,N,3,0,0,0',
        *extra_rows,
    ]
    slice_csv = tmp_path / "qcew_routes" / "slices" / "2017q1.csv"
    slice_csv.parent.mkdir(parents=True, exist_ok=True)
    slice_csv.write_text(header + "\n" + "\n".join(rows) + "\n")
    titles = tmp_path / "qcew_codes" / "titles" / "area_fips.csv"
    titles.parent.mkdir(parents=True, exist_ok=True)
    titles.write_text('area_fips,area_title\nUS000,U.S. TOTAL\n01000,Alabama\n'
                      '41000,Oregon\n38000,North Dakota\n72000,Puerto Rico -- Statewide\n')

    def summary(name, extract_path, findings):
        payload = {
            "source": name, "generated_utc": "x",
            "coverage_span": {k: "" for k in c.COVERAGE_KEYS},
            "access": {"route": "r", "status": "verified", "reason": None},
            "extracts": [{"source": name, "url": "u", "path": str(extract_path),
                          "sha256": "0", "bytes": 1, "retrieved_utc": "x",
                          "http_status": 200}],
            "findings": findings,
        }
        (tmp_path / name / "summary.json").write_text(json.dumps(payload))

    summary("qcew_routes", slice_csv, {})
    summary("qcew_codes", titles, {"private_own_code": "5"})


def test_suppressed_is_boolean_never_null(tmp_path, monkeypatch):
    write_fixture(tmp_path, monkeypatch)
    panel = build_panel("5")
    assert panel["suppressed"].null_count() == 0, \
        "a null `suppressed` is dropped from every .mean() denominator"
    assert panel["suppressed"].dtype == pl.Boolean


def test_suppression_share_uses_the_full_denominator(tmp_path, monkeypatch):
    write_fixture(tmp_path, monkeypatch)
    states = build_panel("5").filter(pl.col("area_class") == "states_dc")
    assert states.height == 6  # two states x three months
    assert float(states["suppressed"].mean()) == 0.5


def test_suppressed_employment_is_null_not_zero(tmp_path, monkeypatch):
    """INV-003: a value paired with a suppression code is never a true zero."""
    write_fixture(tmp_path, monkeypatch)
    panel = build_panel("5")
    assert panel.filter(pl.col("area_fips") == "41000")["emplvl"].null_count() == 3
    assert panel.filter(pl.col("area_fips") == "01000")["emplvl"].to_list() == [400, 400, 400]


def test_sub_state_rows_are_excluded(tmp_path, monkeypatch):
    write_fixture(tmp_path, monkeypatch)
    assert build_panel("5").filter(pl.col("area_fips") == "01001").height == 0


def test_panel_matches_the_documented_schema(tmp_path, monkeypatch):
    """Task 5 reads this parquet by column name and dtype; a silent rename breaks it there."""
    write_fixture(tmp_path, monkeypatch)
    panel = build_panel("5")
    assert list(panel.schema.items()) == list(PANEL_SCHEMA.items())


# --- run_lengths: pure function over a month index and its flags -------------------------


def test_run_lengths_counts_maximal_runs_between_unsuppressed_months():
    assert run_lengths([1, 2, 3, 4, 5], [True, True, False, True, True]) == [2, 2]


def test_run_lengths_counts_a_run_that_reaches_the_end_of_the_series():
    assert run_lengths([1, 2, 3], [False, True, True]) == [2]


def test_run_lengths_breaks_a_run_at_an_absent_month():
    """Suppressed months either side of an absence are two runs, not one twice as long."""
    assert run_lengths([1, 2, 5, 6], [True, True, True, True]) == [2, 2]


def test_run_lengths_of_no_suppression_is_empty():
    assert run_lengths([1, 2, 3], [False, False, False]) == []


# --- estabs_survival: a measured 0.0 and an unmeasurable one are not the same ------------


def test_estabs_survival_is_none_when_nothing_is_suppressed():
    """0.0 would read as 'no suppressed cell keeps its establishment count' -- a measurement
    that was never taken. suppression_share_overall already returns None on an empty
    denominator; this field is what Task 5's universe test reads."""
    empty = pl.DataFrame({"qtrly_estabs": []}, schema={"qtrly_estabs": pl.Int64})
    assert estabs_survival(empty) is None


def test_estabs_survival_counts_a_null_establishment_count_as_not_surviving():
    rows = pl.DataFrame({"qtrly_estabs": [3, None, 0]}, schema={"qtrly_estabs": pl.Int64})
    assert estabs_survival(rows) == 1 / 3


# --- area_class and the disclosure codes that are not `N` --------------------------------

# A state-level area (agglvl 58, area_fips ending '000') that is outside _common.STATE_AREAS.
OTHER_STATE_LEVEL_ROW = '72000,5,113310,58,0,2017,1,N,7,0,0,0'
# A states_dc area publishing a disclosure_code that is neither empty nor the suppression code.
NON_SUPPRESSION_CODE_ROW = '38000,5,113310,58,0,2017,1,-,0,0,0,0'


def test_a_state_level_area_outside_states_dc_is_classed_other(tmp_path, monkeypatch):
    """The branch Task 5's question turns on: a `*000` area that is not in STATES_DC_FIPS is
    neither national nor states_dc, and must stay out of the suppression denominator."""
    write_fixture(tmp_path, monkeypatch, extra_rows=[OTHER_STATE_LEVEL_ROW])
    panel = build_panel("5")
    other = panel.filter(pl.col("area_fips") == "72000")
    assert other["area_class"].to_list() == ["other_state_level"] * 3
    assert other["area_title"].to_list() == ["Puerto Rico -- Statewide"] * 3
    assert panel.filter(pl.col("area_class") == "states_dc").height == 6


def test_a_disclosure_code_other_than_the_suppression_code_is_not_suppressed(
    tmp_path, monkeypatch
):
    """`suppressed` is the published code alone. A row carrying some other code keeps its
    published employment level rather than being nulled out as if it were suppressed."""
    write_fixture(tmp_path, monkeypatch, extra_rows=[NON_SUPPRESSION_CODE_ROW])
    rows = build_panel("5").filter(pl.col("area_fips") == "38000")
    assert rows["suppressed"].to_list() == [False] * 3
    assert rows["emplvl"].to_list() == [0, 0, 0]


# --- _conform: the panel contract, including its key ------------------------------------


def test_a_duplicated_state_quarter_is_rejected(tmp_path, monkeypatch):
    """One row per (area_fips, year, month) is the panel's defining shape. A duplicate would
    inflate the suppression share's denominator with every derived sentence still reading as
    self-consistent, so it fails here instead."""
    duplicate = '01000,5,113310,58,0,2017,1,,40,400,400,400'
    write_fixture(tmp_path, monkeypatch, extra_rows=[duplicate])
    with pytest.raises(RuntimeError, match="not unique"):
        build_panel("5")


def test_conform_rejects_a_dtype_that_drifted():
    """The happy-path schema assertion is half-guaranteed by `select(*PANEL_SCHEMA)`, which
    imposes column order; this is the half that is not."""
    drifted = pl.DataFrame(
        {name: [] for name in PANEL_SCHEMA},
        schema={**PANEL_SCHEMA, "year": pl.Int64},
    )
    with pytest.raises(RuntimeError, match="schema"):
        _conform(drifted)


# --- disclosure_code_values: measured before INV-003 nulls the employment out ------------

# A suppressed row that publishes a nonzero employment level -- the anomaly the source-column
# count exists to surface. No real row in the current window looks like this.
SUPPRESSED_WITH_EMPLOYMENT_ROW = '56000,5,113310,58,0,2017,1,N,9,5,5,5'


def test_disclosure_code_values_counts_source_employment_before_the_null_out(
    tmp_path, monkeypatch
):
    write_fixture(tmp_path, monkeypatch,
                  extra_rows=[NON_SUPPRESSION_CODE_ROW, SUPPRESSED_WITH_EMPLOYMENT_ROW])
    long, _predicates = build_long("5")
    by_code = {row["disclosure_code"]: row for row in disclosure_code_values(long)}
    assert set(by_code) == {"", "-", "N"}

    suppressed = by_code["N"]
    assert suppressed["panel_rows"] == 6  # 41000 and 56000, three months each
    assert suppressed["emplvl_published_rows"] == 0  # INV-003 nulls every one of them
    assert suppressed["emplvl_raw_nonzero_rows"] == 3  # ... and 56000 published 5 anyway
    assert suppressed["qtrly_estabs_positive_rows"] == 6

    assert by_code["-"]["emplvl_raw_nonzero_rows"] == 0
    assert by_code["-"]["emplvl_published_rows"] == 3  # not suppressed, so a published zero
    assert by_code["-"]["qtrly_estabs_positive_rows"] == 0
    assert by_code[""]["emplvl_raw_nonzero_rows"] == 6
