"""Gate-logic tests for `verify_extracts` (the Stage 0 exit gate).

Nothing here reads `data/raw/audit/`. That tree is gitignored, so it does not exist in a fresh
clone, and a test that depended on it would pass on this machine and fail on any other. The
summaries are synthetic, built by `summary()` below; the only real files these tests read are
tracked ones -- `specs/logging-employment-spec.md`, whose §3.1 and Appendix A blocks the gate
parses, and the two shipped `specs/findings/` artifacts.

What is pinned here is the behaviour that made this gate different from the plan's illustrative
version, defect by defect:

1. the orphan direction (`find_orphans`), which the illustrative verifier had no equivalent of
   -- including that a `.part` from an interrupted download is an orphan and not whitelisted;
2. source enumeration by directory, so a source that wrote extracts but no summary is a
   failure rather than one fewer glob hit;
3. `check_env_untracked` anchored at the repository root and matched on basename, exercised
   against a real throwaway git index rather than a stub;
4. the manifest's repo-root-relative `path` column and its LF line endings;
5. `is_empty`, which must keep accepting `0` and `False` as filled findings while rejecting a
   mapping whose every value is null -- and must keep accepting one with a lone null year;
6. `check_document(None, ...)` failing E1, E2 and C together, so no criterion whose checks did
   not run can print PASS;
7. `parse_classification_record` anchored to the `### 3.1` heading and the fence under it, so
   `=`-form assignments for these names elsewhere in the file cannot stand in for a §3.1 that
   moved. The real spec carries no such assignments outside §3.1: where three of the four names
   appear again, they are YAML or a bare word, so the specs below construct the case;
8. `classification_block` bounding the block by the fence it locates rather than by a heading
   scan over raw lines, so a `#`-prefixed line inside the fence is block content rather than a
   heading that truncates the section and makes the block look unclosed.

`verify_extracts` is imported bare, like `_common`, per `tests/conftest.py`. Importing it is
inert: the module's only side effects sit behind `if __name__ == "__main__"`.
"""

from __future__ import annotations

import csv
import json
import subprocess

import pytest

import verify_extracts as m

SPEC_TEXT = m.SPEC.read_text(encoding="utf-8")

# The verdict sentence shape criterion E2 accepts, in miniature: one sentence, one line, citing
# quarters and non-state areas. Not the real recorded sentence -- that lives under data/.
GOOD_VERDICT = ("decline: the national count equals the states+DC sum in 32 of 32 quarter(s), "
                "and the panel carries 1 non-state area(s).")


def summary(source: str, *, findings=None, access=None, coverage=None, extracts=()) -> dict:
    """A schema-valid summary payload, so `load_summaries` and `render`-side helpers see the
    same shape the twelve real scripts write."""
    return {
        "source": source,
        "generated_utc": "2026-09-04T00:00:00+00:00",
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


def extract(source: str, path, *, sha256="0" * 64, status=200) -> dict:
    return {"source": source, "url": "https://example.invalid/f", "path": str(path),
            "sha256": sha256, "bytes": 3, "retrieved_utc": "2026-09-04T00:00:00+00:00",
            "http_status": status}


def write_extract(root, source: str, name: str, body: bytes, *, sidecar=True):
    """A stored extract the way `_common.record_extract` leaves it: the file plus its sidecar."""
    import hashlib

    directory = root / source
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / name
    target.write_bytes(body)
    digest = hashlib.sha256(body).hexdigest()
    if sidecar:
        (directory / f"{name}.sha256").write_text(f"{digest}  {name}\n")
    return target, digest


# --- is_empty: wrong in both obvious directions, so it is neither ---------------------------


@pytest.mark.parametrize("value", [None, "", [], {}])
def test_is_empty_true_for_null_and_empty_containers(value):
    assert m.is_empty(value) is True


@pytest.mark.parametrize("value", [0, 0.0, False, "0", [0], {"a": 0}, 1.0])
def test_is_empty_false_for_measured_zeroes_and_falses(value):
    """`qcew_identity.clean_months` is `0`, `qcew_size.simultaneous_state_industry_size` is
    `false`, and both are findings that decide a later stage. A gate that read them as unfilled
    would demand a fabricated value. `[0]` and `{"a": 0}` are here for the recursion too: a
    container of measured zeroes is filled, because each entry is."""
    assert m.is_empty(value) is False


def test_is_empty_true_for_a_mapping_whose_every_value_is_null():
    """The hole this closes. `cbp_metadata.lfo_by_year` is eight window years mapped to eight
    nulls; testing the container and never its contents read it as filled, and E1 printed PASS
    for a roadmap-named field that was neither filled nor declared."""
    assert m.is_empty({str(year): None for year in range(2017, 2025)}) is True


def test_is_empty_false_for_a_mapping_with_a_lone_null_year():
    """`naics_predicate_by_year` and `empszes_by_year` each carry `"2024": null` against seven
    filled years. That is a measured absence for one year, not an unfilled field, and it must
    keep passing -- deepening the check must not fail a partial mapping."""
    partial = {str(year): "NAICS2017" for year in range(2017, 2024)} | {"2024": None}
    assert m.is_empty(partial) is False


def test_is_empty_recurses_through_nested_containers():
    assert m.is_empty({"a": {"b": [None, ""]}, "c": []}) is True
    assert m.is_empty({"a": {"b": [None, ""]}, "c": [False]}) is False


def test_the_two_declared_empty_shapes_are_accepted_by_e1():
    """Both shapes the deepened check flags in the shipped summaries are declared, so
    `check_findings_filled` accepts them and E1 still passes.

    What this does *not* check: that they are the only two. Nothing here reads `data/`, which is
    gitignored, so a thirteenth all-null mapping appearing in a real summary tomorrow would
    leave this test green. "Exactly two across the twelve summaries" was measured out-of-band
    and is recorded in `verify_extracts`'s module docstring, point 7 -- not guarded here.
    """
    assert ("cbp_metadata", "lfo_by_year") in m.LEGITIMATELY_EMPTY_FINDINGS
    assert ("qcew_routes", "bulk_years_required") in m.LEGITIMATELY_EMPTY_FINDINGS
    summaries = {
        "cbp_metadata": summary("cbp_metadata", findings={
            "lfo_by_year": {str(year): None for year in range(2017, 2025)},
            "naics_predicate_by_year": {"2023": "NAICS2017", "2024": None}}),
        "qcew_routes": summary("qcew_routes", findings={"bulk_years_required": [],
                                                        "bulk_years_fetched": [2017]}),
    }
    assert m.check_findings_filled(summaries) == []


def test_an_undeclared_all_null_mapping_is_a_failure():
    """The latent hole, for the next one: the same shape under a source with no declaration
    fails E1 instead of passing on container shape."""
    summaries = {"bds": summary("bds", findings={"lfo_by_year": {"2017": None, "2018": None}})}
    failures = m.check_findings_filled(summaries)
    assert [f.criterion for f in failures] == ["E1"]
    assert "lfo_by_year" in failures[0].detail


# --- source enumeration, both directions ----------------------------------------------------


def test_enumerate_sources_lists_a_directory_that_has_no_summary(tmp_path):
    """A script that died between its last fetch and `write_summary` leaves exactly this: a
    directory with extracts and no summary. Globbing `*/summary.json` would not see it."""
    (tmp_path / "bds").mkdir()
    (tmp_path / "ces").mkdir()
    (tmp_path / "ces" / "summary.json").write_text("{}")
    assert m.enumerate_sources(tmp_path) == ["bds", "ces"]


def test_main_reports_a_missing_audit_root_instead_of_raising(tmp_path, monkeypatch, capsys):
    """`data/` is gitignored, so a fresh clone has no audit root. A later stage re-running the
    gate there must get the reason, not a `FileNotFoundError` traceback."""
    monkeypatch.setattr(m.c, "AUDIT_ROOT", tmp_path / "absent")
    assert m.main() == 1
    assert "no audit root" in capsys.readouterr().out


def test_enumerate_sources_ignores_files_beside_the_source_directories(tmp_path):
    (tmp_path / "bds").mkdir()
    (tmp_path / "stray.json").write_text("{}")
    assert m.enumerate_sources(tmp_path) == ["bds"]


def test_check_source_set_is_clean_for_exactly_the_expected_twelve():
    assert m.check_source_set(sorted(m.EXPECTED_SOURCES)) == []


def test_check_source_set_reports_a_missing_source():
    found = sorted(m.EXPECTED_SOURCES - {"tpo"})
    failures = m.check_source_set(found)
    assert [f.criterion for f in failures] == ["S"]
    assert "'tpo'" in failures[0].detail


def test_check_source_set_reports_an_unexpected_source():
    failures = m.check_source_set(sorted(m.EXPECTED_SOURCES) + ["qcew_extra"])
    assert len(failures) == 1
    assert "qcew_extra" in failures[0].detail


def test_expected_sources_holds_twelve_keys_from_eleven_scripts():
    """`forest_sources.py` writes both `fia` and `tpo`, so the count is not the script count."""
    assert len(m.EXPECTED_SOURCES) == 12
    assert {"fia", "tpo"} <= m.EXPECTED_SOURCES


# --- load_summaries -------------------------------------------------------------------------


def test_load_summaries_reports_a_source_directory_with_no_summary(tmp_path):
    (tmp_path / "bds").mkdir()
    summaries, failures = m.load_summaries(tmp_path, ["bds"])
    assert summaries == {}
    assert "no summary.json" in failures[0].detail


def test_load_summaries_reports_unreadable_json(tmp_path):
    (tmp_path / "bds").mkdir()
    (tmp_path / "bds" / "summary.json").write_text("{not json")
    summaries, failures = m.load_summaries(tmp_path, ["bds"])
    assert summaries == {}
    assert "unreadable" in failures[0].detail


def test_load_summaries_reports_a_schema_violation(tmp_path):
    (tmp_path / "bds").mkdir()
    payload = summary("bds")
    del payload["findings"]
    (tmp_path / "bds" / "summary.json").write_text(json.dumps(payload))
    summaries, failures = m.load_summaries(tmp_path, ["bds"])
    assert summaries == {}
    assert "findings" in failures[0].detail


def test_load_summaries_reports_a_summary_whose_source_is_not_its_directory(tmp_path):
    """The summary is still loaded -- it is schema-valid -- but the mismatch is a failure, so a
    copy/paste between two audit scripts cannot pass silently."""
    (tmp_path / "bds").mkdir()
    (tmp_path / "bds" / "summary.json").write_text(json.dumps(summary("ces")))
    summaries, failures = m.load_summaries(tmp_path, ["bds"])
    assert set(summaries) == {"bds"}
    assert "not its own directory name" in failures[0].detail


# --- direction one: dangling entries --------------------------------------------------------


def test_verify_recorded_extracts_accepts_a_stored_extract_and_returns_a_relative_path(tmp_path):
    target, digest = write_extract(tmp_path, "bds", "a.json", b"abc")
    summaries = {"bds": summary("bds", extracts=[extract("bds", target, sha256=digest)])}
    rows, failures = m.verify_recorded_extracts(summaries, tmp_path)
    assert failures == []
    assert rows[0]["path"] == "bds/a.json"
    assert rows[0]["sha256"] == digest


def test_verify_recorded_extracts_reports_a_dangling_entry(tmp_path):
    summaries = {"bds": summary("bds", extracts=[extract("bds", tmp_path / "bds" / "gone.json")])}
    rows, failures = m.verify_recorded_extracts(summaries, tmp_path)
    assert rows == []
    assert [f.criterion for f in failures] == ["E5"]
    assert "dangling" in failures[0].detail


def test_verify_recorded_extracts_reports_a_hash_mismatch(tmp_path):
    target, _ = write_extract(tmp_path, "bds", "a.json", b"abc")
    summaries = {"bds": summary("bds", extracts=[extract("bds", target, sha256="f" * 64)])}
    rows, failures = m.verify_recorded_extracts(summaries, tmp_path)
    assert rows == []
    assert "sha256 mismatch" in failures[0].detail


def test_verify_recorded_extracts_reports_a_missing_sidecar(tmp_path):
    target, digest = write_extract(tmp_path, "bds", "a.json", b"abc", sidecar=False)
    summaries = {"bds": summary("bds", extracts=[extract("bds", target, sha256=digest)])}
    rows, failures = m.verify_recorded_extracts(summaries, tmp_path)
    assert rows == []
    assert "missing sidecar" in failures[0].detail


def test_verify_recorded_extracts_reports_a_record_claiming_another_source(tmp_path):
    target, digest = write_extract(tmp_path, "bds", "a.json", b"abc")
    summaries = {"bds": summary("bds", extracts=[extract("ces", target, sha256=digest)])}
    _, failures = m.verify_recorded_extracts(summaries, tmp_path)
    assert "claims source 'ces'" in failures[0].detail


def test_manifest_relative_path_returns_none_outside_the_repository(tmp_path):
    assert m.manifest_relative_path("/somewhere/else/f.json", tmp_path) is None
    assert m.manifest_relative_path(str(tmp_path / "a" / "b.json"), tmp_path) == "a/b.json"


# --- direction two: orphans -----------------------------------------------------------------


def test_find_orphans_accepts_registered_extracts_their_sidecars_and_summaries(tmp_path):
    target, digest = write_extract(tmp_path, "bds", "a.json", b"abc")
    (tmp_path / "bds" / "summary.json").write_text("{}")
    summaries = {"bds": summary("bds", extracts=[extract("bds", target, sha256=digest)])}
    assert m.find_orphans(tmp_path, summaries) == []


def test_find_orphans_reports_a_file_no_summary_registers(tmp_path):
    write_extract(tmp_path, "bds", "a.json", b"abc")
    (tmp_path / "bds" / "summary.json").write_text("{}")
    (tmp_path / "bds" / "unregistered.json").write_text("{}")
    summaries = {"bds": summary("bds")}
    orphans = m.find_orphans(tmp_path, summaries)
    assert [p.name for p in orphans] == ["a.json", "a.json.sha256", "unregistered.json"]


def test_find_orphans_reports_a_part_file_from_an_interrupted_download(tmp_path):
    """`_common.download_extract` streams to `<name>.part` and renames on completion, so a
    surviving `.part` means a fetch did not finish. Whitelisting it would hide that."""
    target, digest = write_extract(tmp_path, "bds", "big.zip", b"abc")
    (tmp_path / "bds" / "summary.json").write_text("{}")
    (tmp_path / "bds" / "big.zip.part").write_bytes(b"trunc")
    summaries = {"bds": summary("bds", extracts=[extract("bds", target, sha256=digest)])}
    assert [p.name for p in m.find_orphans(tmp_path, summaries)] == ["big.zip.part"]


# --- E4: .env, against a real git index -----------------------------------------------------


def git_repo(tmp_path):
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True, capture_output=True)
    return tmp_path


def test_check_env_untracked_passes_when_git_tracks_no_dotenv(tmp_path):
    repo = git_repo(tmp_path)
    (repo / "README.md").write_text("hi\n")
    (repo / ".env.example").write_text("KEY=\n")
    subprocess.run(["git", "add", "README.md", ".env.example"], cwd=repo, check=True,
                   capture_output=True)
    assert m.check_env_untracked(repo) == []


def test_check_env_untracked_catches_a_dotenv_tracked_below_the_root(tmp_path):
    """The illustrative check compared against the literal string ".env", which only ever
    matches a repo-root entry; the criterion is that `git ls-files` shows no `.env` at all."""
    repo = git_repo(tmp_path)
    (repo / "nested").mkdir()
    (repo / "nested" / ".env").write_text("CENSUS_API_KEY=x\n")
    subprocess.run(["git", "add", "-f", "nested/.env"], cwd=repo, check=True, capture_output=True)
    failures = m.check_env_untracked(repo)
    assert [f.criterion for f in failures] == ["E4"]
    assert "nested/.env" in failures[0].detail


def test_check_env_untracked_reports_rather_than_raises_outside_a_repository(tmp_path):
    """A gate that dies on `CalledProcessError` reports nothing at all, including the checks
    that would have passed."""
    failures = m.check_env_untracked(tmp_path / "not-a-repo")
    assert [f.criterion for f in failures] == ["E4"]


def test_check_gitignore_requires_a_dotenv_entry():
    assert m.check_gitignore("# comment\n.env\ndata/\n") == []
    assert m.check_gitignore("/.env\n") == []
    assert m.check_gitignore("data/\n")[0].criterion == "E4"
    assert m.check_gitignore(None)[0].criterion == "E4"


def test_the_repositorys_own_gitignore_covers_dotenv():
    assert m.check_gitignore(m.GITIGNORE.read_text(encoding="utf-8")) == []


# --- spec parsing ---------------------------------------------------------------------------


def test_parse_classification_record_reads_all_four_fields_from_the_real_spec():
    record = m.parse_classification_record(SPEC_TEXT)
    assert record == {"industry_code_supplied": "1113310", "industry_code_used": "113310",
                      "industry_title": "Logging",
                      "classification_status": "corrected_invalid_supplied_code"}


def test_parse_classification_record_raises_when_the_block_is_absent():
    """The easy case: nothing anywhere in the file. The two tests below cover the cases an
    unanchored first-match scan would have parsed rather than rejected."""
    with pytest.raises(ValueError, match="§3.1"):
        m.parse_classification_record("# a spec with no classification block\n")


# The four names as the spec's §3.1 fence publishes them, reused by the anchoring tests below.
CLASSIFICATION_ASSIGNMENTS = ("industry_code_supplied = '1113310'\n"
                              "industry_code_used     = '113310'\n"
                              "industry_title         = 'Logging'\n"
                              "classification_status = 'corrected_invalid_supplied_code'\n")


def test_parse_classification_record_raises_when_the_names_sit_outside_the_section_31_fence():
    """The real gap, constructed rather than observed: the spec's own second copies of these
    names -- three of the four have one -- are YAML `key: value` and a bare column name, which
    a `key = value` scan skips, so the real spec never presented this gap at all. Here
    §3.1 has lost its fence and `=`-form assignments survive in §3.2, which an unanchored scan
    would read from that wrong section instead of failing. Appendix A is included in the form
    the spec ships it -- YAML, and invisible to either scan."""
    spec = ("## 3. Scope\n\n"
            "### 3.1 Classification decision\n\n"
            "The classification block moved.\n\n"
            "### 3.2 Core estimand\n\n"
            "```text\n" + CLASSIFICATION_ASSIGNMENTS + "```\n\n"
            "## Appendix A. Example configuration\n\n"
            "```yaml\nproject:\n  industry_code_supplied: '1113310'\n"
            "  industry_code_used: '113310'\n  industry_title: 'Logging'\n```\n")
    with pytest.raises(ValueError, match="§3.1"):
        m.parse_classification_record(spec)


def test_parse_classification_record_raises_when_one_name_left_the_31_fence():
    """Field granularity, same defect: a name that moved out of §3.1's fence but still exists
    later in the file must be reported missing, not picked up from where it moved to."""
    kept = "".join(line + "\n" for line in CLASSIFICATION_ASSIGNMENTS.splitlines()[:3])
    spec = ("### 3.1 Classification decision\n\n```text\n" + kept + "```\n\n"
            "### 3.2 Core estimand\n\n"
            "```text\nclassification_status = 'corrected_invalid_supplied_code'\n```\n")
    with pytest.raises(ValueError, match="classification_status"):
        m.parse_classification_record(spec)


def test_parse_classification_record_raises_on_an_unclosed_31_fence():
    """An unclosed fence is a broken spec, not a block running to the next heading: reading it
    that way would silently take whatever prose followed as assignments."""
    spec = ("### 3.1 Classification decision\n\n```text\n" + CLASSIFICATION_ASSIGNMENTS
            + "\n### 3.2 Core estimand\n")
    with pytest.raises(ValueError, match="never closed"):
        m.parse_classification_record(spec)


def test_classification_block_keeps_a_hash_prefixed_line_inside_the_fence():
    """A `# `-prefixed line inside §3.1's fence is block content, not a heading. Scanning raw
    lines for the section end *before* locating the fences read it as one: the section was cut
    between the opening and closing fence, and the block was reported "never closed" -- an
    error naming a defect the spec does not have. Today's spec carries no such line, so this
    constructs one."""
    spec = ("### 3.1 Classification decision\n\n```text\n"
            "# the supplied code and the correction, both recorded\n"
            + CLASSIFICATION_ASSIGNMENTS + "```\n\n### 3.2 Core estimand\n")
    assert m.classification_block(spec) == [
        "# the supplied code and the correction, both recorded",
        *CLASSIFICATION_ASSIGNMENTS.splitlines()]
    assert m.parse_classification_record(spec)["industry_title"] == "Logging"


def test_classification_block_returns_only_the_fenced_lines():
    spec = ("### 3.1 Classification decision\n\nProse before the fence.\n\n"
            "```text\n" + CLASSIFICATION_ASSIGNMENTS + "```\n\nProse after it.\n\n"
            "### 3.2 Core estimand\n")
    assert m.classification_block(spec) == CLASSIFICATION_ASSIGNMENTS.splitlines()


def test_parse_appendix_a_sources_reads_the_real_spec_block():
    sources = m.parse_appendix_a_sources(SPEC_TEXT)
    assert sources["qcew"] is True
    assert sources["cbp"] is True
    assert sources["tpo"] is False
    assert sources["fia"] is False


def test_parse_appendix_a_sources_does_not_let_enabled_drift_onto_a_sibling_key():
    """`release_status`, `api_key_env` and `fail_on_unknown_disclosure_regime` sit at the same
    indent as `enabled` in the real block; only an exact `enabled` match may set the flag."""
    block = ("sources:\n"
             "  qcew:\n    enabled: true\n    release_status: 'final'\n"
             "  cbp:\n    api_key_env: 'CENSUS_API_KEY'\n    enabled: false\n"
             "    fail_on_unknown_disclosure_regime: true\n"
             "  mystery:\n    release_status: 'final'\n"
             "\nconstraints:\n  enforce_integrality: true\n")
    assert m.parse_appendix_a_sources(block) == {"qcew": True, "cbp": False, "mystery": False}


def test_parse_appendix_a_sources_raises_when_there_is_no_block():
    with pytest.raises(ValueError, match="Appendix A"):
        m.parse_appendix_a_sources("# no yaml here\n")


# --- E1: findings filled --------------------------------------------------------------------


def test_check_findings_filled_accepts_a_measured_zero_and_false():
    summaries = {"qcew_size": summary("qcew_size", findings={"simultaneous": False, "n": 0})}
    assert m.check_findings_filled(summaries) == []


def test_check_findings_filled_reports_an_empty_key():
    summaries = {"bds": summary("bds", findings={"finest_naics_available": ""})}
    failures = m.check_findings_filled(summaries)
    assert [f.criterion for f in failures] == ["E1"]
    assert "finest_naics_available" in failures[0].detail


def test_check_findings_filled_allows_the_declared_empty_key_for_its_own_source():
    summaries = {"qcew_routes": summary("qcew_routes", findings={"bulk_years_required": []})}
    assert m.check_findings_filled(summaries) == []


def test_the_empty_allowance_is_granted_per_source_not_per_key_name():
    """The allowance belongs to the script the plan granted it to. The same key name empty
    under another source is still a failure."""
    summaries = {"bds": summary("bds", findings={"bulk_years_required": []})}
    assert len(m.check_findings_filled(summaries)) == 1


def test_check_findings_filled_reports_an_empty_access_route():
    summaries = {"bds": summary("bds", access={"route": ""})}
    assert any("access.route" in f.detail for f in m.check_findings_filled(summaries))


# --- E1: the roadmap's own field list -------------------------------------------------------


def test_check_roadmap_fields_reports_a_field_absent_from_the_document():
    """Present and filled in the summary is not enough: criterion E1 is about the finding
    file, so a field that never reaches the document is a failure."""
    summaries = {source: summary(source, findings={key: "x" for _, s, key in m.ROADMAP_FIELDS
                                                   if s == source})
                 for source in {s for _, s, _ in m.ROADMAP_FIELDS}}
    complete_doc = " ".join(f'"{key}"' for _, _, key in m.ROADMAP_FIELDS)
    assert m.check_roadmap_fields(summaries, complete_doc) == []
    failures = m.check_roadmap_fields(summaries, complete_doc.replace('"branch"', ""))
    assert [f.criterion for f in failures] == ["E1"]
    assert "does not appear in the finding document" in failures[0].detail


def test_check_roadmap_fields_reports_a_source_with_no_summary():
    failures = m.check_roadmap_fields({}, "")
    assert {f.criterion for f in failures} == {"E1"}
    assert all("no valid summary" in f.detail for f in failures)


def test_every_roadmap_field_names_an_expected_source():
    assert {source for _, source, _ in m.ROADMAP_FIELDS} <= m.EXPECTED_SOURCES


# --- E2 and E3 ------------------------------------------------------------------------------


def test_check_verdict_sentence_accepts_a_one_sentence_verdict():
    assert m.check_verdict_sentence(GOOD_VERDICT) == []


def test_check_verdict_sentence_tolerates_an_interior_abbreviation():
    """"U.S. TOTAL" and "D.C." are area titles, not sentence ends."""
    sentence = GOOD_VERDICT[:-1] + " for U.S. TOTAL and the D.C. area."
    assert m.check_verdict_sentence(sentence) == []


def test_check_verdict_sentence_tolerates_a_verdict_ending_in_an_abbreviation():
    """The illustrative check counted periods after normalising abbreviations away, so a
    sentence ending in one had none left to count and was rejected -- forcing a measured
    sentence to be reworded to satisfy the gate."""
    sentence = GOOD_VERDICT[:-1] + " for D.C."
    assert m.check_verdict_sentence(sentence) == []


def test_check_verdict_sentence_requires_a_terminal_period():
    assert any("period" in f.detail for f in m.check_verdict_sentence(GOOD_VERDICT[:-1]))


def test_check_verdict_sentence_rejects_two_sentences():
    failures = m.check_verdict_sentence(GOOD_VERDICT + " It also carries quarter(s).")
    assert any("exactly one sentence" in f.detail for f in failures)


def test_check_verdict_sentence_requires_the_quarter_comparison():
    sentence = GOOD_VERDICT.replace("quarter(s)", "period(s)")
    assert any("per-quarter" in f.detail for f in m.check_verdict_sentence(sentence))


def test_check_verdict_sentence_requires_the_geography_universe_statement():
    sentence = GOOD_VERDICT.replace("non-state area(s)", "other area(s)")
    assert any("geography universe" in f.detail for f in m.check_verdict_sentence(sentence))


def test_check_verdict_reports_a_verdict_sentence_missing_from_the_document():
    summaries = {"qcew_identity": summary("qcew_identity",
                                          findings={"branch": "decline",
                                                    "verdict_sentence": GOOD_VERDICT}),
                 "qcew_routes": summary("qcew_routes", findings={"earliest_year_served": 2014})}
    assert m.check_verdict(summaries, GOOD_VERDICT) == []
    failures = m.check_verdict(summaries, "a document without it")
    assert [f.criterion for f in failures] == ["E2"]


def test_check_verdict_rejects_a_branch_outside_the_three():
    summaries = {"qcew_identity": summary("qcew_identity",
                                          findings={"branch": "maybe",
                                                    "verdict_sentence": GOOD_VERDICT}),
                 "qcew_routes": summary("qcew_routes", findings={"earliest_year_served": 2014})}
    failures = m.check_verdict(summaries, GOOD_VERDICT)
    assert any("enforce/residual_cells/decline" in f.detail for f in failures)


@pytest.mark.parametrize("year", ["2014", 2014.0, True, None])
def test_check_verdict_rejects_a_year_boundary_that_is_not_an_integer(year):
    """E3: a reference year, not an approximation -- and `True` is an `int` subclass, which is
    why the check tests for `bool` first."""
    summaries = {"qcew_identity": summary("qcew_identity",
                                          findings={"branch": "decline",
                                                    "verdict_sentence": GOOD_VERDICT}),
                 "qcew_routes": summary("qcew_routes", findings={"earliest_year_served": year})}
    failures = m.check_verdict(summaries, GOOD_VERDICT)
    assert [f.criterion for f in failures] == ["E3"]


# --- the document checks --------------------------------------------------------------------


def test_check_document_fails_e1_e2_and_c_together_when_the_document_is_absent():
    """`main` prints one PASS/FAIL line per criterion. A criterion whose checks could not run
    must not appear there as passing, so an absent document fails every criterion that reads
    it -- not E1 alone."""
    failures = m.check_document(None, {"industry_code_used": "113310"}, {"qcew": True})
    assert {f.criterion for f in failures} == {"E1", "E2", "C"}


def test_check_document_reports_a_missing_classification_value():
    doc = "# findings\ncannot be implemented without\nGeography universe\nTPO/FIA coverage\n" \
          "Optional state sources\n`qcew`\n"
    failures = m.check_document(doc, {"industry_code_supplied": "1113310"}, {"qcew": True})
    assert [f.criterion for f in failures] == ["E1"]
    assert "1113310" in failures[0].detail


def test_check_document_requires_the_appendix_a_sources_and_the_section_headings():
    doc = "# findings\n113310\n"
    failures = m.check_document(doc, {"industry_code_used": "113310"},
                                {"qcew": True, "bea": False})
    assert {f.criterion for f in failures} == {"C"}
    details = " ".join(f.detail for f in failures)
    assert "'qcew'" in details and "'bea'" in details
    assert "§1.2" in details and "§21" in details


# --- the manifest -----------------------------------------------------------------------------


def test_write_manifest_writes_lf_line_endings_and_sorted_rows(tmp_path):
    """`csv.DictWriter` defaults to CRLF; this file is tracked text in an LF repository."""
    path = tmp_path / "manifest.csv"
    rows = [{**extract("ces", "x"), "path": "ces/b.json"},
            {**extract("bds", "x"), "path": "bds/z.json"},
            {**extract("bds", "x"), "path": "bds/a.json"}]
    m.write_manifest(path, rows)
    raw = path.read_bytes()
    assert b"\r\n" not in raw
    lines = raw.decode().splitlines()
    assert lines[0] == ",".join(m.FIELDS)
    assert [line.split(",")[2] for line in lines[1:]] == ["bds/a.json", "bds/z.json",
                                                          "ces/b.json"]


# --- the shipped artifacts (tracked files only) ------------------------------------------------


def test_the_shipped_manifest_has_the_declared_header_and_repo_relative_paths():
    with m.MANIFEST.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        assert tuple(reader.fieldnames) == m.FIELDS
        rows = list(reader)
    assert rows, "the shipped manifest has no rows"
    assert all(not row["path"].startswith("/") for row in rows)
    assert all(row["path"].startswith("data/raw/audit/") for row in rows)
    assert all(len(row["sha256"]) == 64 for row in rows)
    assert {row["source"] for row in rows} <= m.EXPECTED_SOURCES


def test_the_shipped_manifest_has_no_crlf():
    assert b"\r\n" not in m.MANIFEST.read_bytes()
