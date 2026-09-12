"""Judgment-logic tests for `qcew_parent_margins` (R-S5G-5).

Nothing here touches the network or `data/raw/audit/`. The script makes TWO judgments and both are
tested here: which margin identifies a suppressed cell and how strongly (`identification`), and
whether a walk's slice outcomes are a measurement at all (`fetch_verdict`). The row predicates those
judgments stand on (`state_rows`, `disclosed_keys`) are pinned too. `_common`'s retry and backoff are tested
there; `fetch_slice`'s one departure from them -- a 404 is answered, not raised -- is pinned here,
with `parse_slice`'s content check. `qcew_parent_margins` is imported bare, like `_common`, per
`tests/conftest.py`; importing it is inert because its side effects sit behind
`if __name__ == "__main__"`.
"""

from __future__ import annotations

import httpx
import polars as pl
import pytest
import qcew_parent_margins as m

NOTHING = {
    "parent_113_disclosed": False,
    "parent_1133_disclosed": False,
    "parent_11331_disclosed": False,
    "ownership_total_disclosed": False,
    "ownership_siblings_disclosed": False,
}


def test_no_disclosed_margin_is_the_status_quo():
    """Today's measured state: every one of the 1,227 suppressed cells is `[0, +inf)`."""
    assert m.identification(NOTHING) == m.NONE


def test_a_disclosed_single_child_parent_is_exact_not_a_bound():
    """D6: `1133 -> 11331 -> 113310` is single-child in both vintages, so the parent IS the cell."""
    for level in ("parent_1133_disclosed", "parent_11331_disclosed"):
        assert m.identification({**NOTHING, level: True}) == m.EXACT


def test_a_disclosed_113_bounds_rather_than_identifies():
    """`113` aggregates 1131, 1132 and 1133; nonnegativity of the siblings gives an upper bound."""
    assert m.identification({**NOTHING, "parent_113_disclosed": True}) == m.UPPER_BOUND


def test_total_ownership_is_exact_only_when_the_sibling_is_disclosed_too():
    total = {**NOTHING, "ownership_total_disclosed": True}
    assert m.identification(total) == m.UPPER_BOUND
    assert m.identification({**total, "ownership_siblings_disclosed": True}) == m.EXACT


def test_exact_outranks_a_bound_when_both_are_available():
    """The strongest margin wins: a cell with both is a REQ-027 case, not a bounded one."""
    both = {**NOTHING, "parent_113_disclosed": True, "parent_1133_disclosed": True}
    assert m.identification(both) == m.EXACT


EXPECTED = 32


def _outcomes(**overrides):
    base = {i: {"ok": EXPECTED, "not_found": 0, "unparseable": 0} for i in m.INDUSTRIES}
    base.update(overrides)
    return base


def test_a_complete_fetch_is_a_measurement():
    m.fetch_verdict(_outcomes(), EXPECTED)


def test_a_parent_the_route_never_serves_is_a_measured_absence():
    """Every quarter 404s: that is an answer to R-S5G-5, recorded as `fetched: false`."""
    absent = {"ok": 0, "not_found": EXPECTED, "unparseable": 0}
    m.fetch_verdict(_outcomes(**{"113": absent}), EXPECTED)


def test_a_parent_answering_200_without_the_csv_halts_rather_than_reading_as_absent():
    """Classify on content: a 200 error body is a failure, never an absence (plan Task 2 property 2).

    Before this verdict was extracted, an industry whose every slice came back unparseable had
    `ok == 0`, slipped past the `0 < ok < expected` partial guard, and was recorded as a measured
    absence -- scored as "not disclosed" on every suppressed quarter.
    """
    garbled = {"ok": 0, "not_found": 0, "unparseable": EXPECTED}
    with pytest.raises(SystemExit, match="unparseable"):
        m.fetch_verdict(_outcomes(**{"113": garbled}), EXPECTED)


def test_a_partial_fetch_halts():
    with pytest.raises(SystemExit, match="partial"):
        m.fetch_verdict(
            _outcomes(**{"1133": {"ok": 31, "not_found": 1, "unparseable": 0}}), EXPECTED
        )


def test_the_child_is_the_denominator_and_may_not_be_absent_even_uniformly():
    absent = {"ok": 0, "not_found": EXPECTED, "unparseable": 0}
    with pytest.raises(SystemExit, match="113310"):
        m.fetch_verdict(_outcomes(**{"113310": absent}), EXPECTED)


def test_a_published_value_and_a_true_zero_are_disclosed_and_n_is_not():
    """`''` and `'-'` both publish a value; `'-'` publishes ZERO, which forces the child to zero."""
    rows = pl.DataFrame(
        {
            "area_fips": ["06000", "41000", "53000", "23000"],
            "own_code": ["5", "5", "5", "3"],
            "disclosure_code": ["", "-", "N", ""],
            "year": ["2019"] * 4,
            "qtr": ["1"] * 4,
        }
    )
    assert m.disclosed_keys(rows, "5") == {("06000", "2019", "1"), ("41000", "2019", "1")}


def test_state_rows_keeps_states_and_dc_and_nothing_else():
    frame = pl.DataFrame(
        {
            "industry_code": ["113"] * 6 + ["1133"],
            "area_fips": ["06000", "11000", "72000", "US000", "C1010", "06001", "06000"],
        }
    )
    assert m.state_rows(frame, "113")["area_fips"].to_list() == ["06000", "11000"]


def _client(status: int, body: bytes = b"") -> httpx.Client:
    return httpx.Client(
        transport=httpx.MockTransport(lambda _request: httpx.Response(status, content=body))
    )


def test_a_404_slice_is_an_answer_not_a_crash():
    assert m.fetch_slice(_client(404), "https://example.test/x.csv") is None


def test_any_other_client_error_still_halts():
    with pytest.raises(httpx.HTTPStatusError):
        m.fetch_slice(_client(403), "https://example.test/x.csv")


def test_a_served_slice_returns_its_bytes():
    assert m.fetch_slice(_client(200, b"a,b\n1,2\n"), "https://example.test/x.csv") == b"a,b\n1,2\n"


def test_a_200_error_body_does_not_parse_as_a_slice():
    """Classify on content: a 200 carrying an HTML error page is not a slice."""
    assert m.parse_slice("u", b"<html><title>Access Denied</title></html>") is None


def test_a_body_with_the_columns_parses():
    body = b'"area_fips","own_code","industry_code","agglvl_code","disclosure_code"\n"06000","5","113310","58",""\n'
    frame = m.parse_slice("u", body)
    assert frame is not None and frame.height == 1
