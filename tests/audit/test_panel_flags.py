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

from qcew_panel import PANEL_SCHEMA, build_panel, run_lengths


def write_fixture(tmp_path, monkeypatch):
    """Two states over one quarter: one clean row, one suppressed row, one county row."""
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
    ]
    slice_csv = tmp_path / "qcew_routes" / "slices" / "2017q1.csv"
    slice_csv.parent.mkdir(parents=True, exist_ok=True)
    slice_csv.write_text(header + "\n" + "\n".join(rows) + "\n")
    titles = tmp_path / "qcew_codes" / "titles" / "area_fips.csv"
    titles.parent.mkdir(parents=True, exist_ok=True)
    titles.write_text('area_fips,area_title\nUS000,U.S. TOTAL\n01000,Alabama\n41000,Oregon\n')

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
