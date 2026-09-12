"""Tests for `render_parent_margins` (R-S5G-6): what the renderer REFUSES, not its prose.

Offline. The renderer is the only thing between a revised audit summary and a false committed
finding, so what is pinned here is what it refuses -- an extract whose bytes changed, a summary or
extract that no longer supports a sentence the template writes -- plus the predicate it duplicates
from the measurement script, which its own docstring says must agree.
"""

from __future__ import annotations

import copy
import hashlib

import polars as pl
import pytest
import qcew_parent_margins as measure
import render_parent_margins as r

CLEAN = {
    "slice_outcomes": {
        i: {"ok": 32, "not_found": 0, "unparseable": 0} for i in ("113310", "113", "1133", "11331")
    },
    "parents": {
        "113": {
            "fetched": True,
            "agglvl_codes_present": ["55"],
            "disclosed_where_child_suppressed": 252,
        },
        "1133": {
            "fetched": True,
            "agglvl_codes_present": ["56"],
            "disclosed_where_child_suppressed": 0,
        },
        "11331": {
            "fetched": True,
            "agglvl_codes_present": ["57"],
            "disclosed_where_child_suppressed": 0,
        },
    },
    "total_ownership_113310": {
        "own_code_0_rows": 0,
        "sibling_own_3_disclosed_where_child_suppressed": 0,
    },
    "identification": {"exact": 0},
}


def _broken(mutate):
    findings = copy.deepcopy(CLEAN)
    mutate(findings)
    return r.summary_premises(findings, expected_slices=32)


def test_the_measured_summary_supports_every_guarded_sentence():
    assert r.summary_premises(copy.deepcopy(CLEAN), expected_slices=32) == []


@pytest.mark.parametrize(
    ("mutate", "names"),
    [
        (lambda f: f["parents"]["1133"].update(disclosed_where_child_suppressed=3), "1133"),
        (lambda f: f["parents"]["11331"].update(disclosed_where_child_suppressed=1), "11331"),
        (lambda f: f["parents"]["113"].update(disclosed_where_child_suppressed=0), "grandchild"),
        (lambda f: f["parents"]["113"].update(fetched=False), "113 was fetched"),
        (lambda f: f["parents"]["1133"].update(agglvl_codes_present=["58"]), "agglvl"),
        (lambda f: f["parents"]["113"].update(agglvl_codes_present=["55", "54"]), "agglvl"),
        (lambda f: f["total_ownership_113310"].update(own_code_0_rows=5), "own_code 0"),
        (
            lambda f: f["total_ownership_113310"].update(
                sibling_own_3_disclosed_where_child_suppressed=2
            ),
            "both ends",
        ),
        (lambda f: f["identification"].update(exact=1), "exact reconstruction"),
        (lambda f: f["slice_outcomes"]["113"].update(ok=31), "parsable"),
    ],
)
def test_each_broken_summary_premise_halts_by_naming_its_sentence(mutate, names):
    broken = _broken(mutate)
    assert broken and any(names in b for b in broken), broken


def test_an_unfetched_parent_halts_by_name_before_any_extract_is_indexed():
    """A uniform 404 on 113 leaves no 113 extracts; the premise must fire, not a KeyError later."""
    broken = _broken(lambda f: f["parents"].update({"113": {"fetched": False}}))
    assert any("113 was fetched" in b for b in broken)


def _extract_premises(**over):
    kwargs = {"dash_hit": 0, "median_ratio": 0.9, "n_under": 107, "n_values": 756} | over
    return r.extract_premises(**kwargs)


def test_extract_premises_hold_on_the_measured_extracts():
    assert _extract_premises() == []


@pytest.mark.parametrize(
    ("over", "names"),
    [
        ({"dash_hit": 1}, "true-zero"),
        ({"median_ratio": 0.3}, "dwarf"),
        ({"median_ratio": None}, "no disclosed pair"),
        ({"n_under": 0}, "subset"),
        ({"n_under": 756}, "subset"),
    ],
)
def test_each_broken_extract_premise_halts_by_naming_its_sentence(over, names):
    assert any(names in b for b in _extract_premises(**over))


def test_main_halts_on_the_summary_before_it_touches_an_extract(monkeypatch):
    """The ORDER inside `main`: a parent never fetched must halt by name before `load_extracts`."""
    findings = copy.deepcopy(CLEAN)
    findings["parents"]["113"] = {"fetched": False}
    summary = {
        "findings": findings,
        "coverage_span": {"covered": [str(y) for y in range(2017, 2025)]},
    }
    monkeypatch.setattr(r.c, "load_summary", lambda _source: summary)

    def unreachable(_summary):
        raise AssertionError("load_extracts ran before the summary premises halted")

    monkeypatch.setattr(r, "load_extracts", unreachable)
    with pytest.raises(SystemExit, match="113 was fetched"):
        r.main()


def _extract(tmp_path, monkeypatch, content: bytes, recorded_sha: str):
    monkeypatch.setattr(r.c, "AUDIT_ROOT", tmp_path)
    dest = tmp_path / r.SOURCE / "113" / "2017q1.csv"
    dest.parent.mkdir(parents=True)
    dest.write_bytes(content)
    # Recorded under a DIFFERENT root: the renderer must rebuild the path under this checkout.
    return {
        "extracts": [
            {"path": f"/elsewhere/data/raw/audit/{r.SOURCE}/113/2017q1.csv", "sha256": recorded_sha}
        ]
    }


def test_extracts_load_from_a_relocated_root_and_pin_a_reproducible_digest(tmp_path, monkeypatch):
    content = b'"area_fips","own_code"\n"06000","5"\n'
    sha = hashlib.sha256(content).hexdigest()
    frames, digest, n = r.load_extracts(_extract(tmp_path, monkeypatch, content, sha))
    assert n == 1 and frames["113"].height == 1
    assert digest == hashlib.sha256(f"{sha}  113/2017q1.csv\n".encode()).hexdigest()


def test_an_extract_whose_bytes_changed_halts(tmp_path, monkeypatch):
    summary = _extract(tmp_path, monkeypatch, b"a\n1\n", "0" * 64)
    with pytest.raises(SystemExit, match="no longer hashes"):
        r.load_extracts(summary)


def test_a_path_that_escapes_the_audit_directory_halts(monkeypatch, tmp_path):
    monkeypatch.setattr(r.c, "AUDIT_ROOT", tmp_path)
    escaping = f"/x/data/raw/audit/{r.SOURCE}/../secrets/a.csv"
    with pytest.raises(SystemExit, match="escapes"):
        r.load_extracts({"extracts": [{"path": escaping, "sha256": "0" * 64}]})


def test_a_path_outside_the_audit_directory_halts(monkeypatch, tmp_path):
    monkeypatch.setattr(r.c, "AUDIT_ROOT", tmp_path)
    with pytest.raises(SystemExit, match="not under"):
        r.load_extracts(
            {"extracts": [{"path": "/somewhere/else/113/2017q1.csv", "sha256": "0" * 64}]}
        )


def test_the_renderer_predicate_agrees_with_the_measurement_script():
    frame = pl.DataFrame(
        {
            # The last row is a DIFFERENT industry, so the industry clause is exercised too.
            "industry_code": ["113"] * 7 + ["113310"],
            "area_fips": ["06000", "11000", "72000", "US000", "C1010", "06001", "41000", "53000"],
            "own_code": ["5", "5", "5", "5", "5", "5", "3", "5"],
        }
    )
    expected = measure.state_rows(frame, "113").filter(pl.col("own_code") == "5")
    assert r.private_state_rows(frame, "113").equals(expected)


def test_bound_widths_are_the_disclosed_parent_values_on_suppressed_quarters_only():
    parent = pl.DataFrame(
        {
            "area_fips": ["06000", "41000", "53000"],
            "year": ["2019"] * 3,
            "qtr": ["1"] * 3,
            "disclosure_code": ["", "N", ""],
            "month1_emplvl": ["10", "99", "7"],
            "month2_emplvl": ["30", "99", "7"],
            "month3_emplvl": ["40", "99", "7"],
        }
    )
    suppressed = {("06000", "2019", "1"), ("41000", "2019", "1")}
    widths = r.bound_widths(parent, suppressed)
    assert widths["area_fips"].to_list() == ["06000"]
    assert widths.select(r.MONTHS).row(0) == (10.0, 30.0, 40.0)
