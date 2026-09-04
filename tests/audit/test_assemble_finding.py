"""Rendering tests for `assemble_finding` (the Stage 0 finding document).

Nothing here reads `data/raw/audit/`; that tree is gitignored and absent from a fresh clone.
The summaries are synthetic. The tracked artifacts the tests do read -- the spec and the
shipped `specs/findings/source-audit.md` -- are in the repository.

The document is the only Stage 0 artifact that survives into a clone, and no test in this repo
compares its prose to the data behind it, so what is pinned here is the rendering behaviour
whose failure would put a false or missing value into it:

1. a `verified` source's null `access.reason` never renders as the string `None`, and a
   `verified` source that recorded a reason anyway (`fia`, `tpo`) still has it rendered;
2. a long `coverage_span` value is never cut mid-string -- a cut would ship half of an
   `INFERENCE MARKER, OPENING`/`CLOSING` span -- and its full text appears in the document;
3. every table cell escapes `|` (a real recorded route contains one) and collapses newlines;
4. the header carries the newest summary `generated_utc`, not a wall-clock date, so
   regenerating the document without new evidence rewrites the same bytes;
5. the Appendix A `enabled` defaults are juxtaposed with the measured access status for every
   source Appendix A ships, including the ones this audit never touched;
6. `machine_path_disclosure` counts what it names, and is not fooled by `extracts[].path`,
   which is absolute for every source by construction;
7. the shipped disclosure paragraph names two of the criteria's limits -- E1's hand-authored
   field mapping and criterion C's substring matches -- and no longer closes the list after
   naming only the first. E2 to E5 and S get no worth-statement there, and the test below
   asserts two clauses of criterion C's limit plus the absence of the phrase that closed the
   list, not one claim per criterion.

`assemble_finding` is imported bare, like `_common`, per `tests/conftest.py`. Importing it is
inert: the module's only side effects sit behind `if __name__ == "__main__"`.
"""

from __future__ import annotations

import json

import pytest

import assemble_finding as m
import verify_extracts as v

CLASSIFICATION = {"industry_code_supplied": "1113310", "industry_code_used": "113310",
                  "industry_title": "Logging",
                  "classification_status": "corrected_invalid_supplied_code"}
APPENDIX_A = {"qcew": True, "tpo": False, "bea": False}
VERDICT = ("decline: the national count equals the states+DC sum in 32 of 32 quarter(s), and "
           "the panel carries 1 non-state area(s).")


def summary(source: str, *, findings=None, access=None, coverage=None, extracts=(),
            generated="2026-09-04T00:00:00+00:00") -> dict:
    return {
        "source": source,
        "generated_utc": generated,
        "coverage_span": {
            "published_start": "2017", "published_end": "2024",
            "window_start": "2017-01", "window_end": "2024-12",
            "covered": "2017-2024", "uncovered": "",
            **(coverage or {}),
        },
        "access": {"status": "verified", "route": "https://example.invalid/", "reason": None,
                   **(access or {})},
        "extracts": list(extracts),
        "findings": {"measured": 1} if findings is None else findings,
    }


def identity_summary(**kwargs) -> dict:
    return summary("qcew_identity",
                   findings={"branch": "decline", "verdict_sentence": VERDICT}, **kwargs)


def render(summaries, notes="## notes\n", appendix_a=None) -> str:
    return m.render_document(summaries, notes, CLASSIFICATION, appendix_a or APPENDIX_A)


# --- cell ------------------------------------------------------------------------------------


def test_cell_renders_null_and_empty_as_what_they_are():
    """Rendering `''` as "none" would be a reading of an empty string, not the value; ten of the
    twelve summaries record a null `access.reason` and four record an empty `uncovered`."""
    assert m.cell(None) == "null"
    assert m.cell("") == "(empty)"
    assert m.cell("   ") == "(empty)"


def test_cell_escapes_a_pipe():
    """`qcew_routes`'s recorded route is "slice: ... | bulk: ...". An unescaped pipe silently
    splits the markdown row and shifts every later column."""
    assert m.cell("slice: a | bulk: b") == "slice: a \\| bulk: b"


def test_cell_collapses_newlines_and_runs_of_whitespace():
    assert m.cell("a\nb  c\td") == "a b c d"


def test_cell_renders_a_short_value_verbatim():
    assert m.cell("2017-01..2024-12 (96 month(s))") == "2017-01..2024-12 (96 month(s))"


def test_cell_replaces_a_long_value_with_a_descriptor_rather_than_cutting_it():
    """`fia.coverage_span.uncovered` runs past 1300 characters and carries an INFERENCE MARKER
    span; `[:67] + "..."` would ship the opening marker without its close."""
    value = "INFERENCE MARKER, OPENING: " + "x" * 200 + " INFERENCE MARKER, CLOSING."
    rendered = m.cell(value)
    assert rendered == f"recorded value ({len(value)} chars) -- see the per-source section"
    assert "INFERENCE MARKER" not in rendered


def test_cell_reports_the_recorded_length_not_the_collapsed_one():
    value = "word\n\n" + "y" * 120
    assert f"({len(value)} chars)" in m.cell(value)


# --- fence -----------------------------------------------------------------------------------


def test_fence_sorts_keys_and_keeps_non_ascii_literal():
    fenced = m.fence({"b": 1, "a": "§3.2 -- 96 month(s)"})
    assert fenced.startswith("```json\n") and fenced.endswith("\n```")
    assert fenced.index('"a"') < fenced.index('"b"')
    assert "§3.2" in fenced and "\\u" not in fenced


def test_fence_renders_a_null_as_json_null_not_python_none():
    assert '"reason": null' in m.fence({"reason": None})


# --- machine_path_disclosure -------------------------------------------------------------------


def test_machine_path_disclosure_names_the_source_whose_rendered_value_embeds_a_local_path():
    route = f"derived from a panel ({v.REPO_ROOT}/data/raw/audit/qcew_panel/panel.parquet)"
    summaries = {"bds": summary("bds"),
                 "qcew_identity": identity_summary(access={"route": route})}
    disclosure = m.machine_path_disclosure(summaries)
    assert disclosure.startswith("1 rendered value embeds")
    assert "`qcew_identity`" in disclosure and "`bds`" not in disclosure


def test_machine_path_disclosure_ignores_extract_paths(tmp_path):
    """Every `extracts[].path` is absolute by construction, since `_common.AUDIT_ROOT` is; they
    reach the document as a count, not as a value, so counting them would name all twelve."""
    record = {"source": "bds", "url": "https://example.invalid/f",
              "path": f"{v.REPO_ROOT}/data/raw/audit/bds/a.json", "sha256": "0" * 64,
              "bytes": 1, "retrieved_utc": "2026-09-04T00:00:00+00:00", "http_status": 200}
    summaries = {"bds": summary("bds", extracts=[record])}
    assert m.machine_path_disclosure(summaries).startswith("No rendered value")


# --- the Appendix A juxtaposition ---------------------------------------------------------------


def test_appendix_a_map_covers_exactly_the_expected_sources():
    assert set(m.APPENDIX_A_KEY_BY_SOURCE) == set(v.EXPECTED_SOURCES)


def test_appendix_a_map_names_only_sources_the_spec_still_ships():
    shipped = v.parse_appendix_a_sources(v.SPEC.read_text(encoding="utf-8"))
    assert set(m.APPENDIX_A_KEY_BY_SOURCE.values()) <= set(shipped)


def test_check_appendix_a_map_rejects_an_audited_source_it_does_not_place():
    with pytest.raises(SystemExit, match="qcew_new"):
        m.check_appendix_a_map(["qcew_new"], {"qcew": True})


def test_check_appendix_a_map_rejects_a_mapping_to_an_absent_appendix_entry():
    with pytest.raises(SystemExit, match="Appendix A"):
        m.check_appendix_a_map(sorted(v.EXPECTED_SOURCES), {"qcew": True})


def test_appendix_a_rows_keep_the_specs_order_and_group_the_audit_keys():
    summaries = {"qcew_codes": summary("qcew_codes"), "qcew_panel": summary("qcew_panel"),
                 "tpo": summary("tpo")}
    rows = m.appendix_a_rows(summaries, {"qcew": True, "tpo": False, "bea": False})
    assert [row[0] for row in rows] == ["`qcew`", "`tpo`", "`bea`"]
    assert rows[0][1] == "true" and rows[1][1] == "false"
    assert rows[0][2] == "`qcew_codes`, `qcew_panel`"
    assert rows[0][3] == "verified"


def test_appendix_a_rows_mark_a_source_this_audit_never_touched():
    rows = m.appendix_a_rows({"tpo": summary("tpo")}, {"bea": False})
    assert rows[0][2] == "not audited"
    assert rows[0][3] == "not measured"


def test_appendix_a_rows_report_a_status_the_audit_actually_measured():
    summaries = {"tpo": summary("tpo", access={"status": "documented", "reason": "why"})}
    assert m.appendix_a_rows(summaries, {"tpo": False})[0][3] == "documented"


# --- render_document ---------------------------------------------------------------------------


def test_a_verified_source_with_a_null_reason_never_renders_the_string_none():
    """The illustrative renderer printed the reason only for a non-`verified` status; printing
    it unconditionally instead writes `None` for the ten sources whose reason is null."""
    document = render({"qcew_identity": identity_summary(), "bds": summary("bds")})
    assert "None" not in document
    assert "Recorded access reason" not in document
    assert '"reason": null' in document


def test_a_verified_source_that_recorded_a_reason_still_has_it_rendered():
    """All twelve sources measured `verified`, and two of them (`fia`, `tpo`) recorded a reason
    anyway -- the two longest pieces of prose evidence in the audit."""
    reason = "Reachable, but only via an undocumented redirect."
    document = render({"qcew_identity": identity_summary(),
                       "tpo": summary("tpo", access={"reason": reason})})
    assert f"> **Recorded access reason:** {reason}" in document


def test_a_long_coverage_value_is_summarised_in_the_table_and_rendered_whole_below():
    value = "INFERENCE MARKER, OPENING: " + "x" * 400 + " INFERENCE MARKER, CLOSING."
    document = render({"qcew_identity": identity_summary(),
                       "fia": summary("fia", coverage={"uncovered": value})})
    assert f"recorded value ({len(value)} chars) -- see the per-source section" in document
    assert json.dumps(value)[1:-1] in document
    assert document.count("INFERENCE MARKER, OPENING") == document.count(
        "INFERENCE MARKER, CLOSING")


def test_the_glance_row_escapes_a_pipe_in_a_recorded_route():
    document = render({"qcew_identity": identity_summary(),
                       "qcew_routes": summary("qcew_routes",
                                              access={"route": "slice: a | bulk: b"})})
    assert "| `qcew_routes` | verified | slice: a \\| bulk: b |" in document


def test_the_verdict_sentence_is_rendered_outside_the_json_fence():
    """The gate checks `verdict_sentence in doc`. Satisfying that only through the findings
    fence would make the check an accident of JSON escaping -- a verdict containing a double
    quote would escape it there and the check would fail on correct work."""
    document = render({"qcew_identity": identity_summary()})
    assert f"\n> {VERDICT}\n" in document
    assert "**Branch:** `decline`" in document


def test_the_header_reports_the_newest_summary_timestamp_not_a_run_date():
    """A wall-clock stamp made the tracked document change whenever it was regenerated, whether
    or not any evidence had."""
    summaries = {"qcew_identity": identity_summary(generated="2026-09-03T00:00:00+00:00"),
                 "susb": summary("susb", generated="2026-09-04T19:58:36+00:00")}
    document = render(summaries)
    assert "**Newest `generated_utc` among them:** 2026-09-04T19:58:36+00:00." in document
    assert "2026-09-03T00:00:00+00:00" in document  # still shown in its own per-source section


def test_rendering_is_a_pure_function_of_its_inputs():
    summaries = {"qcew_identity": identity_summary(), "bds": summary("bds")}
    assert render(summaries) == render(summaries)


def test_the_notes_are_inlined_verbatim():
    notes = "## Auditor's notes\n\n- a claim with `backticks` and a | pipe\n"
    assert notes.rstrip() in render({"qcew_identity": identity_summary()}, notes=notes)


def test_the_classification_record_is_rendered_from_the_parsed_spec_values():
    document = render({"qcew_identity": identity_summary()})
    for value in CLASSIFICATION.values():
        assert value in document


def test_every_source_gets_its_coverage_span_and_access_rendered_in_full():
    """The illustrative per-source section fenced `findings` alone, so the full recorded value
    of every coverage and access field existed nowhere in the document."""
    document = render({"qcew_identity": identity_summary(),
                       "bds": summary("bds", coverage={"published_start": "1978"})})
    assert '"published_start": "1978"' in document
    assert document.count("**coverage_span**:") == 2
    assert document.count("**access**:") == 2
    assert document.count("**findings**:") == 2


# --- the shipped document (a tracked file) -------------------------------------------------------


def test_the_shipped_document_carries_every_appendix_a_source_and_the_required_sections():
    document = m.OUT.read_text(encoding="utf-8")
    shipped = v.parse_appendix_a_sources(v.SPEC.read_text(encoding="utf-8"))
    for name in shipped:
        assert f"`{name}`" in document
    for heading in ("## Sources audited", "## SRC-QCEW-006 branch verdict",
                    "## Appendix A `enabled` defaults", "## Per-source findings",
                    "## Auditor's notes"):
        assert heading in document


def test_the_shipped_document_has_one_section_per_audited_source():
    document = m.OUT.read_text(encoding="utf-8")
    for name in v.EXPECTED_SOURCES:
        assert f"### `{name}`" in document


def test_the_shipped_disclosure_names_criterion_cs_limit_and_not_only_e1s():
    """Rule 7 in the artifact that reaches a fresh clone. The disclosure named E1's limit and
    called it "one limit worth naming", which reads as exhaustive to a reader who has only this
    file; criterion C's PASS rests on four substring matches plus one presence test per
    Appendix A source name and asserted far more than that. Both limits are named now, and the
    phrasing that closed the list is gone."""
    document = m.OUT.read_text(encoding="utf-8")
    assert "one limit worth naming" not in document
    assert "four substring matches" in document
    assert "not that their verdict cells say anything" in document


def test_the_shipped_document_names_the_two_fields_e1_passes_by_declared_exemption():
    """Two of the roadmap-mapped fields are empty and pass E1 because the gate declares them.
    A reader of this document alone should be told which, rather than reading the PASS line as
    "every mapped field carries a value"."""
    document = m.OUT.read_text(encoding="utf-8")
    for source, key in (("qcew_routes", "bulk_years_required"),
                        ("cbp_metadata", "lfo_by_year")):
        assert (source, key) in v.LEGITIMATELY_EMPTY_FINDINGS
        assert f"`{source}.{key}`" in document
