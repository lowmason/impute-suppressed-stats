# /// script
# requires-python = ">=3.12"
# dependencies = ["httpx>=0.27"]   # _common imports httpx
# ///
"""Stage 0 exit gate: enumerate the audited sources, validate every summary against the Task 1
schema, re-verify the extract manifest in both directions, check the five criteria the
roadmap's Stage 0 `Exit:` line states, prove no `.env` is tracked, and emit the committed
extract manifest.

What that last claim is worth: E2 to E5 are checked against the values themselves. E1's
"every field above" half is checked against `ROADMAP_FIELDS`, a hand-authored reading of the
roadmap's `Produces:` prose onto the findings keys the eleven scripts shipped, marked there
with the inference-marker convention. A field the roadmap names that nobody mapped would pass
this gate silently, so the mapping is the thing to review, not the PASS line. Criterion C is
weaker still: four substring matches plus one presence test per Appendix A source name, which
proves the deliverable carries those sections and says nothing about what they contain -- see
the comment on `REQUIRED_DOC_TEXT`.

Deviations from the plan's illustrative code, each established against the twelve shipped
summaries and this repository rather than assumed:

1. **The illustrative verifier checks the manifest in one direction only.** It walks each
   summary's `extracts` and reports a recorded path missing from disk (a *dangling* entry). A
   file sitting under `data/raw/audit/` that no summary registers (an *orphan*) passes it
   silently -- including a `.part` file left by an interrupted `_common.download_extract`,
   which is exactly the artifact whose presence means a fetch did not finish. `find_orphans`
   adds the second direction, and `main` reports both counts whether or not either is zero.

2. **`glob("*/summary.json")` enumerates summaries, so it cannot report a missing source.** A
   source directory carrying extracts but no summary -- a script that died between its last
   fetch and `write_summary` -- yields one fewer glob hit and no complaint. `enumerate_sources`
   lists directories instead and `check_source_set` compares them against `EXPECTED_SOURCES`
   in both directions, so a missing source and an unexpected one are both failures.

3. **`git ls-files` is resolved against the process CWD, not the repository root.** Run from
   `scripts/audit/`, it lists paths relative to that directory, so a tracked repo-root `.env`
   never appears as the literal string `".env"` and the criterion passes while being violated.
   `check_env_untracked` runs `git -C <repo root> ls-files` and matches on each tracked path's
   *basename*, so a `.env` tracked at any depth is caught. Its `check=True` is also caught:
   an unrunnable `git` became an uncaught `CalledProcessError`, i.e. a gate that reports
   nothing at all, and is now a named failure like any other.

4. **The illustrative verifier writes the manifest even when the run failed**, from whichever
   extracts happened to pass -- so a failing gate overwrites the committed manifest with a
   short one. Here the manifest is written only on a clean run, and a failing run says on
   stdout that it was not written.

5. **`csv.DictWriter` on a file opened with `newline=""` emits CRLF line endings** (RFC 4180 is
   the module default). The manifest is a tracked text file in a repository whose other tracked
   text is LF, so `lineterminator="\n"` is set explicitly.

6. **The manifest recorded absolute paths.** `_common.AUDIT_ROOT` is absolute, so every
   summary's `extracts[].path` is absolute -- correct for the summaries, which stay under
   gitignored `data/`. The manifest does not: it is one of three artifacts that survive into a
   fresh clone, where `/Users/<name>/...` names nothing. `manifest_relative_path` rewrites the
   `path` column to repo-root-relative and reports a path outside the repository as a failure
   rather than raising. Hashing still runs against the recorded absolute path.

7. **The empty-value test is wrong in both of the obvious directions, so it is neither.** The
   natural tidy-up to `if not value:` would reject `qcew_identity.clean_months` (`0`),
   `qcew_size.simultaneous_state_industry_size` (`false`), `bds.six_digit_logging_available`
   (`false`), `fia.tpo_mentions_on_fia_doc_page` (`0`) and several more -- every one a measured
   finding, and several of them the answer that decides a later stage's routing. The opposite
   error is testing the container and never its contents: `cbp_metadata.lfo_by_year` is a dict
   of eight window years whose every value is `null`, and a shape test read it as filled, so
   E1 printed PASS for a roadmap-named field that was neither filled nor declared. `is_empty`
   therefore also calls a container empty when every entry in it is. Across the twelve shipped
   summaries that flags exactly two findings values -- `qcew_routes.bulk_years_required` (`[]`)
   and `cbp_metadata.lfo_by_year` -- and both are declared in `LEGITIMATELY_EMPTY_FINDINGS`,
   so the deepening creates no new failure today and closes the hole for the next all-null
   mapping. A *lone* `null` per year stays filled: `cbp_metadata.naics_predicate_by_year` and
   `empszes_by_year` each carry `"2024": null` against seven filled years, which is a measured
   absence for one year, not an unfilled field.

The gate is a pure-function core (`check_*`/`find_*`/`verify_*`, each taking what it inspects
as an argument) with `main` as the wiring that supplies the real paths, so the tests exercise
the checks themselves rather than a monkeypatched module constant.
"""

from __future__ import annotations

import csv
import io
import json
import re
import subprocess
import sys
from pathlib import Path, PurePosixPath
from typing import Any, NamedTuple

sys.path.insert(0, str(Path(__file__).parent))
import _common as c  # noqa: E402

REPO_ROOT = c.AUDIT_ROOT.parents[2]
SPEC = REPO_ROOT / "specs" / "logging-employment-spec.md"
FINDING_DOC = c.FINDINGS_DIR / "source-audit.md"
MANIFEST = c.FINDINGS_DIR / "source-audit-extracts.csv"
GITIGNORE = REPO_ROOT / ".gitignore"
FIELDS = ("source", "url", "path", "sha256", "bytes", "retrieved_utc", "http_status")

# Twelve source keys from eleven scripts: `forest_sources.py` writes both `fia` and `tpo`, so a
# one-script-per-source assumption drops a source. Declared here rather than scanned from disk
# so that a missing source and an unexpected one are both errors (see `check_source_set`).
EXPECTED_SOURCES = frozenset({
    "bds", "cbp_metadata", "cbp_regime", "ces", "fia", "qcew_codes", "qcew_identity",
    "qcew_panel", "qcew_routes", "qcew_size", "susb", "tpo",
})

# Findings keys whose empty value is a recorded finding, not a missing one. A gate that
# rejected these would push someone to fabricate a value -- the exact failure this stage exists
# to prevent. Keyed by (source, key), not by key alone: the allowance is granted to the script
# that earned it. The first four are declared by the plan; the fifth is declared here so that
# E1's pass names the field rather than passing it by accident of container shape.
LEGITIMATELY_EMPTY_FINDINGS = frozenset({
    ("qcew_routes", "bulk_years_required"),  # plan: "[] is a legitimate finding, not a failure"
    ("cbp_regime", "unknown_years"),         # plan: list of years whose regime is `unknown`
    ("fia", "sampling_error_field"),         # plan: the field name, or null
    ("tpo", "chosen_route"),                 # plan: the URL, or `null`
    # `null` for all eight window years, because LFO was only ever sent as a filter (`LFO=001`)
    # and never selected as an output column, so no code list came back. The field is marked
    # "not obtainable -- why" in two places, neither of them the value: `cbp_metadata.findings
    # .notes` records the reason year by year, and the §1.2 table in
    # `specs/findings/source-audit-notes.md` carries it as the row routing the fix to Stage 1
    # with a dedicated `LFO,LFO_LABEL` query. Declared rather than left to `is_empty`'s shape
    # test, which passed it before this entry existed.
    ("cbp_metadata", "lfo_by_year"),
})

# The roadmap's Stage 0 `Exit:` line, split into its five criteria and quoted from it. `main`
# prints one PASS/FAIL line per entry, so the gate reports which criterion failed rather than
# only that something did.
CRITERIA: dict[str, str] = {
    "E1": 'the finding file exists with every field above either filled or marked '
          '"not obtainable - why"',
    "E2": "the SRC-QCEW-006 branch verdict names exactly one of enforce, residual-cells, or "
          "decline, in one sentence, citing the per-quarter comparison that produced it and "
          "stating whether the geography universe accounts for any gap",
    "E3": "the QCEW year boundary is stated as a reference year, not an approximation",
    "E4": "`git ls-files` shows no `.env`",
    "E5": "every extract's recorded sha256 matches the file on disk",
    # Not from the `Exit:` line: the plan's Task 13 `Closes:` line, which also names the §1.2
    # bullet and the three §21 rows this stage gives a verdict on.
    "C": "the stage deliverable also discharges §1.2's final required-plan bullet and gives a "
         "verdict on the three §21 rows the stage cites",
    # Not a roadmap criterion either: the artifact integrity E1 and E5 are read off.
    "S": "artifact integrity: the audited source set, the summary schema, and the extract "
         "manifest in both directions",
}

# INFERENCE MARKER, OPENING: the mapping below, to the closing marker, is a reading of the
# roadmap's Stage 0 `Produces:` line -- prose written before the audit ran -- onto the findings
# keys the eleven scripts actually shipped. It is hand-authored, measures nothing, and is how
# this gate supports criterion E1's "every field above". The plan's own per-task `Produces:`
# blocks are deliberately NOT the reference: two sources ship keys those blocks never named
# (`bds.probe_query_scope`, `bds.raw_retention_rule`, `susb.raw_retention_rule`), reviewed and
# accepted as dispatch-mandated, so checking against them would reject correct work. Each entry
# is (roadmap phrase, source, findings key).
ROADMAP_FIELDS: tuple[tuple[str, str, str], ...] = (
    ("the earliest reference year the §5.4 slice endpoint serves",
     "qcew_routes", "earliest_year_served"),
    ("the bulk-file route covering the remainder of the D1 window",
     "qcew_routes", "bulk_years_required"),
    ("the bulk-file route covering the remainder of the D1 window",
     "qcew_routes", "bulk_years_fetched"),
    ("the code/title lists actually present for agglvl_code, own_code, size_code and "
     "disclosure_code on 113310 rows", "qcew_codes", "codes_present"),
    ("the own_code for private ownership, derived from the fetched titles file",
     "qcew_codes", "private_own_code"),
    ("whether any QCEW size file carries state x 113310 x size simultaneously",
     "qcew_size", "simultaneous_state_industry_size"),
    ("the CBP EMPSZES code list per vintage", "cbp_metadata", "empszes_by_year"),
    ("the CBP LFO code list per vintage", "cbp_metadata", "lfo_by_year"),
    ("the CBP NAICS predicate name per vintage", "cbp_metadata", "naics_predicate_by_year"),
    ("the CBP disclosure regime per reference year", "cbp_regime", "regime_by_year"),
    ("the state x month suppression share for 113310 private ownership",
     "qcew_panel", "suppression_share_overall"),
    ("the state x month suppression share for 113310 private ownership",
     "qcew_panel", "suppression_share_by_month"),
    ("per-state CES publication level (1133, 113, or supersector)",
     "ces", "publication_level_by_state"),
    ("BDS finest industry detail", "bds", "finest_naics_available"),
    ("SUSB detailed-sizes file layout", "susb", "detailed_sizes_layout"),
    ("FIA /fullreport parameters", "fia", "doc_parameters"),
    ("the SRC-QCEW-006 branch verdict", "qcew_identity", "branch"),
    ("the SRC-QCEW-006 branch verdict, in one sentence",
     "qcew_identity", "verdict_sentence"),
    ("quarter by quarter, whether national 113310 private employment equals the sum of state "
     "rows", "qcew_identity", "quarter_table"),
    ("the geography-universe explanation, tested before suppression is blamed",
     "qcew_identity", "geography_universe_explains_gap"),
)
# INFERENCE MARKER, CLOSING.

# Headings and row labels the finding document must carry for criterion C. The §21 row labels
# are quoted from the spec's §21 table; the §1.2 heading from the spec's §1.2 bullet.
#
# What C's PASS is worth, stated because rule 7 requires it. These four are substring matches,
# and `check_document` adds one presence test per Appendix A source name. Together they prove
# the deliverable carries the sections the plan's Task 13 `Closes:` line names, and nothing
# whatever about what those sections say: a notes file carrying these four headings with
# entirely empty verdict cells passes C. Deliberately not strengthened. The only check that
# would catch that without inventing a semantic judgement the gate cannot make is a non-empty
# test on the cells of a markdown table row, and that would fail on correct work the day
# someone writes the §21 verdicts as prose instead of a table. Disclosing the limit is the
# honest fix; the verdicts themselves are what a reviewer reads, not this criterion's PASS
# line. The shipped document says the same thing to a fresh-clone reader.
REQUIRED_DOC_TEXT: tuple[tuple[str, str], ...] = (
    ("the §1.2 table of requirements needing further source verification",
     "cannot be implemented without"),
    ("the §21 geography-universe row", "Geography universe"),
    ("the §21 TPO/FIA coverage row", "TPO/FIA coverage"),
    ("the §21 optional-state-sources row", "Optional state sources"),
)


class Failure(NamedTuple):
    """One unmet check, tagged with the criterion in `CRITERIA` it belongs to."""

    criterion: str
    detail: str


def is_empty(value: Any) -> bool:
    """A findings value counts as unfilled when it is null, an empty container, or a container
    whose every entry is itself unfilled.

    Two rules correcting opposite errors, both set out in this module's docstring, point 7.
    Deliberately not `not value`: `0`, `0.0` and `False` are measurements this audit shipped,
    and every one of them is a filled field. And deliberately not the container test alone: a
    mapping of eight years to eight nulls is an unfilled field wearing a filled field's shape.

    The recursion covers lists as well as mappings. The ruling that prompted it named mappings;
    "a container whose entries are all empty" is the same rule without the special case, and no
    list in the twelve shipped summaries is affected either way (checked).
    """
    if value in (None, "", [], {}):
        return True
    if isinstance(value, dict):
        return all(is_empty(entry) for entry in value.values())
    if isinstance(value, list):
        return all(is_empty(entry) for entry in value)
    return False


def enumerate_sources(audit_root: Path) -> list[str]:
    """Source keys as they exist on disk: one directory each, whether or not it holds a
    summary. Listing directories rather than `summary.json` files is what lets a source that
    died before writing its summary be reported as missing instead of silently skipped."""
    return sorted(p.name for p in audit_root.iterdir() if p.is_dir())


def check_source_set(found: list[str],
                     expected: frozenset[str] = EXPECTED_SOURCES) -> list[Failure]:
    """Both directions: an expected source with no directory, and a directory nobody expects."""
    failures = [Failure("S", f"expected source {name!r} has no directory under the audit root")
                for name in sorted(expected - set(found))]
    failures += [Failure("S", f"unexpected source directory {name!r} under the audit root; it "
                              "is registered by no task in this plan")
                 for name in sorted(set(found) - expected)]
    return failures


def load_summaries(audit_root: Path, names: list[str]) -> tuple[dict[str, dict], list[Failure]]:
    """Read and schema-validate one summary per source directory."""
    summaries: dict[str, dict] = {}
    failures: list[Failure] = []
    for name in names:
        path = audit_root / name / "summary.json"
        if not path.exists():
            failures.append(Failure("S", f"{name}: no summary.json (the source directory "
                                         "exists, so a script wrote extracts but no summary)"))
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            failures.append(Failure("S", f"{name}: summary.json is unreadable: {exc}"))
            continue
        try:
            c.validate_summary(payload)
        except ValueError as exc:
            failures.append(Failure("S", f"{name}: {exc}"))
            continue
        if payload["source"] != name:
            failures.append(Failure("S", f"{name}: summary records source "
                                         f"{payload['source']!r}, not its own directory name"))
        summaries[name] = payload
    return summaries, failures


def registered_paths(summaries: dict[str, dict]) -> set[Path]:
    return {Path(rec["path"]) for payload in summaries.values() for rec in payload["extracts"]}


def manifest_relative_path(recorded: str, repo_root: Path) -> str | None:
    """The tracked manifest's `path` column: repo-root-relative, or None when the recorded path
    lies outside the repository (reported by the caller, never raised)."""
    try:
        return Path(recorded).relative_to(repo_root).as_posix()
    except ValueError:
        return None


def verify_recorded_extracts(
    summaries: dict[str, dict], repo_root: Path
) -> tuple[list[dict], list[Failure]]:
    """Direction one: every extract a summary registers exists, hashes to its recorded sha256,
    and carries its `.sha256` sidecar. Returns the manifest rows for the ones that pass."""
    rows: list[dict] = []
    failures: list[Failure] = []
    for name, payload in summaries.items():
        for rec in payload["extracts"]:
            if rec["source"] != name:
                failures.append(Failure("S", f"{name}: extract record claims source "
                                             f"{rec['source']!r}"))
            target = Path(rec["path"])
            if not target.exists():
                failures.append(Failure("E5", f"{name}: dangling manifest entry -- no file at "
                                              f"{rec['path']}"))
                continue
            actual = c.sha256_file(target)
            if actual != rec["sha256"]:
                failures.append(Failure(
                    "E5", f"{name}: sha256 mismatch for {rec['path']}\n"
                          f"  recorded {rec['sha256']}\n  on disk  {actual}"))
                continue
            sidecar = target.parent / f"{target.name}.sha256"
            if not sidecar.exists():
                failures.append(Failure("E5", f"{name}: missing sidecar {sidecar}"))
                continue
            relative = manifest_relative_path(rec["path"], repo_root)
            if relative is None:
                failures.append(Failure("S", f"{name}: recorded extract path {rec['path']} is "
                                             "outside the repository"))
                continue
            row = {k: rec[k] for k in FIELDS}
            row["path"] = relative
            rows.append(row)
    return rows, failures


def expected_files(audit_root: Path, summaries: dict[str, dict]) -> set[Path]:
    """Described from the inside out: a file under the audit root is expected iff it is a
    registered extract, a source's `summary.json`, or the `.sha256` sidecar of a registered
    extract. Nothing else -- a `.part` from an interrupted download is an orphan, and saying so
    is the point."""
    files = {audit_root / name / "summary.json" for name in summaries}
    for path in registered_paths(summaries):
        files.add(path)
        files.add(path.parent / f"{path.name}.sha256")
    return {p.resolve() for p in files}


def find_orphans(audit_root: Path, summaries: dict[str, dict]) -> list[Path]:
    """Direction two: files on disk that no summary accounts for."""
    expected = expected_files(audit_root, summaries)
    return sorted(p for p in audit_root.rglob("*") if p.is_file() and p.resolve() not in expected)


def check_env_untracked(repo_root: Path) -> list[Failure]:
    """E4. Anchored at the repository root, and matched on basename so a `.env` tracked at any
    depth counts; `.env.example` and friends do not."""
    try:
        completed = subprocess.run(["git", "-C", str(repo_root), "ls-files"],
                                   capture_output=True, text=True, check=True)
    except (OSError, subprocess.CalledProcessError) as exc:
        return [Failure("E4", f"could not list tracked files with git: {exc}")]
    return [Failure("E4", f"git tracks {tracked}")
            for tracked in completed.stdout.splitlines()
            if PurePosixPath(tracked).name == ".env"]


def check_gitignore(gitignore_text: str | None) -> list[Failure]:
    """The roadmap's Stage 0 `Produces:` line also names the repo-root `.gitignore` covering
    `.env`; E4's `git ls-files` check is the outcome, this is the mechanism."""
    if gitignore_text is None:
        return [Failure("E4", "no repo-root .gitignore")]
    entries = {line.strip() for line in gitignore_text.splitlines()}
    if not entries & {".env", "/.env"}:
        return [Failure("E4", "the repo-root .gitignore has no `.env` entry")]
    return []


def classification_block(spec_text: str) -> list[str]:
    """The lines inside the fenced block under the spec's own `### 3.1` heading.

    Anchored, not merely first-match -- for the general case, not for anything today's spec
    presents. Three of the four names do appear again (Appendix A's example configuration, plus
    `industry_title` in a column list), but always as YAML `key: value` or a bare word, never
    the `key = value` form the parser splits on, and `classification_status` appears only in
    §3.1. Nowhere outside §3.1 does this spec carry these names in `=` form, so an unanchored
    scan of it would read §3.1's block or find nothing at all and raise -- it could not reach
    Appendix A. What anchoring guards is the case the spec does not present: a §3.1 that moved
    or was renamed while `=`-form assignments for these names survive in some other fenced
    block, which
    `test_parse_classification_record_raises_when_the_names_sit_outside_the_section_31_fence`
    constructs directly. The scan therefore starts at the `### 3.1` heading, takes the first
    fence to open before the next heading of the same level or higher -- a §3.1 that lost its
    fence cannot borrow §3.2's -- and reads only what that fence encloses.

    Raises when the heading is absent, when the section carries no fence, and when no later
    fence closes the one it opens. That closing fence is the next fence line in the file rather
    than the next one inside the section, so an unclosed §3.1 fence is reported as unclosed
    only when no fence follows it anywhere.
    """
    lines = spec_text.splitlines()
    start = next((i for i, line in enumerate(lines) if re.match(r"###\s+3\.1(\s|$)", line)), None)
    if start is None:
        raise ValueError("the spec has no §3.1 heading (`### 3.1 ...`) to anchor the "
                         "classification block to")
    # One pass, and whichever comes first after the heading decides: a fence opens the block
    # and no later heading is consulted, while a heading reached before any fence ends the
    # section with no block in it. Scanning raw lines for the section end *before* locating the
    # fences cannot make that distinction -- a `#`-prefixed line inside the fence was read as a
    # heading, cutting the section between the opening and closing fence and reporting the
    # block unclosed, an error naming a defect the spec does not have.
    opening = None
    for i in range(start + 1, len(lines)):
        if lines[i].lstrip().startswith("```"):
            opening = i
            break
        if re.match(r"#{1,3}\s", lines[i]):
            break
    if opening is None:
        raise ValueError("the spec's §3.1 section carries no fenced classification block")
    closing = next((i for i in range(opening + 1, len(lines))
                    if lines[i].lstrip().startswith("```")), None)
    if closing is None:
        raise ValueError("the spec's §3.1 fenced classification block is never closed")
    return lines[opening + 1:closing]


def parse_classification_record(spec_text: str) -> dict[str, str]:
    """The four §3.1 classification fields, read from the fenced block under the spec's own
    `### 3.1` heading rather than retyped. Raises when that heading or its fence is absent, or
    when the fence does not carry all four names, so a spec edit fails loudly here instead of
    quietly dropping the record from the finding document or reading it from somewhere else
    (see `classification_block`)."""
    wanted = ("industry_code_supplied", "industry_code_used", "industry_title",
              "classification_status")
    record: dict[str, str] = {}
    for line in classification_block(spec_text):
        stripped = line.strip()
        if "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        key, value = key.strip(), value.strip()
        if key in wanted and key not in record:
            record[key] = value.strip("'\"")
    missing = [k for k in wanted if k not in record]
    if missing:
        raise ValueError(f"the spec's §3.1 fenced classification block is missing {missing}")
    return record


def parse_appendix_a_sources(spec_text: str) -> dict[str, bool]:
    """Appendix A's `sources:` block as {source key: enabled}, in the spec's own order.

    A five-line indentation reader, not a YAML parser: `sources:` at column 0, source keys at
    two spaces, their settings at four. Siblings of `enabled` (`release_status`, `api_key_env`,
    `fail_on_unknown_disclosure_regime`) are skipped by name-matching `enabled` exactly, so an
    `enabled` lookup cannot drift onto a neighbour.
    """
    lines = spec_text.splitlines()
    try:
        start = next(i for i, line in enumerate(lines) if line == "sources:")
    except StopIteration:
        raise ValueError("the spec has no Appendix A `sources:` block") from None
    enabled: dict[str, bool] = {}
    current: str | None = None
    for line in lines[start + 1:]:
        if not line.strip():
            continue
        if not line.startswith("  "):
            break
        if not line.startswith("    "):
            current = line.strip().rstrip(":")
            enabled.setdefault(current, False)
            continue
        key, _, value = line.strip().partition(":")
        if key == "enabled" and current is not None:
            enabled[current] = value.strip() == "true"
    if not enabled:
        raise ValueError("Appendix A's `sources:` block lists no sources")
    return enabled


def check_findings_filled(summaries: dict[str, dict]) -> list[Failure]:
    """E1, over what shipped: every findings value is filled, or is one of the five declared in
    `LEGITIMATELY_EMPTY_FINDINGS` whose emptiness is itself the recorded finding."""
    failures: list[Failure] = []
    for name, payload in summaries.items():
        for key, value in sorted(payload["findings"].items()):
            if (name, key) in LEGITIMATELY_EMPTY_FINDINGS or not is_empty(value):
                continue
            failures.append(Failure("E1", f"{name}: findings[{key!r}] is empty -- fill it or "
                                          "mark it 'not obtainable -- why'"))
        access = payload["access"]
        if not access.get("route"):
            failures.append(Failure("E1", f"{name}: access.route is empty"))
    return failures


def check_roadmap_fields(summaries: dict[str, dict], doc_text: str) -> list[Failure]:
    """E1, over what the roadmap asked for: every field its Stage 0 `Produces:` line names is
    present and filled in the summary that owns it, and reaches the finding document."""
    failures: list[Failure] = []
    for phrase, source, key in ROADMAP_FIELDS:
        payload = summaries.get(source)
        if payload is None:
            failures.append(Failure("E1", f"{phrase}: source {source!r} has no valid summary"))
            continue
        findings = payload["findings"]
        if key not in findings:
            failures.append(Failure("E1", f"{phrase}: {source}.findings has no {key!r}"))
            continue
        if is_empty(findings[key]) and (source, key) not in LEGITIMATELY_EMPTY_FINDINGS:
            failures.append(Failure("E1", f"{phrase}: {source}.findings[{key!r}] is empty"))
        if f'"{key}"' not in doc_text:
            failures.append(Failure("E1", f"{phrase}: {source}.findings[{key!r}] does not "
                                          "appear in the finding document"))
    return failures


def check_year_boundary(summaries: dict[str, dict]) -> list[Failure]:
    """E3, on `qcew_routes`'s year boundary. Separate from `check_verdict`, and called
    unconditionally, because it reads no document: while it lived inside `check_verdict` it
    sat behind `main`'s `if doc_text is not None` guard, so an absent finding document made
    the gate print `PASS E3` with `earliest_year_served` never looked at -- the exact "a
    criterion whose checks never ran must not appear as passing" rule `check_document`'s
    absent-document branch exists to honour."""
    routes = summaries.get("qcew_routes")
    if routes is None:
        return [Failure("E3", "qcew_routes has no valid summary")]
    earliest = routes["findings"].get("earliest_year_served")
    if isinstance(earliest, bool) or not isinstance(earliest, int):
        return [Failure("E3", "earliest_year_served must be an integer reference "
                              f"year; it is {earliest!r}")]
    return []


def check_verdict(summaries: dict[str, dict], doc_text: str) -> list[Failure]:
    """E2, on `qcew_identity`'s recorded verdict. E3 is `check_year_boundary`'s, which runs
    whether or not the document exists."""
    failures: list[Failure] = []
    identity = summaries.get("qcew_identity")
    if identity is None:
        failures.append(Failure("E2", "qcew_identity has no valid summary"))
    else:
        findings = identity["findings"]
        if findings.get("branch") not in ("enforce", "residual_cells", "decline"):
            failures.append(Failure("E2", "branch verdict is not one of "
                                          "enforce/residual_cells/decline"))
        sentence = str(findings.get("verdict_sentence", "")).strip()
        failures += check_verdict_sentence(sentence)
        if sentence and sentence not in doc_text:
            failures.append(Failure("E2", "the verdict sentence is not present in the finding "
                                          "document"))
    return failures


def check_verdict_sentence(sentence: str) -> list[Failure]:
    """E2's shape rules. Abbreviation periods ("U.S.", "D.C.") and decimal points in section
    references are normalised away before sentence breaks are looked for, so a legitimate
    verdict is not rejected for carrying one.

    The illustrative check counted periods in the normalised sentence and required exactly one,
    at the end. That rejects a one-sentence verdict *ending* in an abbreviation -- "... outside
    the national total for D.C." normalises to a string ending in `ABBR`, with no period left
    to count -- so the audit would have had to reword a measured sentence to satisfy the gate.
    A sentence break is a period followed by whitespace, which is what is looked for here; the
    terminal period is checked on the sentence as recorded.
    """
    if not sentence:
        return [Failure("E2", "the verdict sentence is empty")]
    failures: list[Failure] = []
    normalized = re.sub(r"\b(?:[A-Za-z]\.){2,}", "ABBR", sentence)
    normalized = re.sub(r"(?<=\d)\.(?=\d)", "", normalized)
    if not sentence.endswith("."):
        failures.append(Failure("E2", "the verdict must end in a period"))
    if re.search(r"\.\s", normalized):
        failures.append(Failure("E2", "the verdict must be exactly one sentence"))
    if "\n" in sentence:
        failures.append(Failure("E2", "the verdict must be a single line"))
    if not re.search(r"\bquarters?\b", sentence):
        failures.append(Failure("E2", "the verdict must cite the per-quarter comparison"))
    if "non-state area" not in sentence:
        failures.append(Failure("E2", "the verdict must state whether the geography universe "
                                      "accounts for any gap"))
    return failures


def check_document(
    doc_text: str | None, classification: dict[str, str], appendix_a: dict[str, bool]
) -> list[Failure]:
    """E1's "the finding file exists", the §3.1 record it must carry, and criterion C's
    headings. The Appendix A check is what makes the `enabled`-default juxtaposition a
    verifiable part of the deliverable rather than a paragraph someone may drop."""
    if doc_text is None:
        # One failure per criterion whose checks read the document, rather than one for E1
        # alone: `main` prints a PASS line per criterion, and a criterion whose checks never
        # ran must not appear there as passing.
        absent = f"{FINDING_DOC} does not exist (run assemble_finding.py), so the checks that "
        return [Failure("E1", absent + "read it did not run"),
                Failure("E2", absent + "look for the verdict sentence in it did not run"),
                Failure("C", absent + "look for the §1.2 and §21 sections in it did not run")]
    if not doc_text.strip():
        # Same criterion set as the absent branch above, but NOT the same reason, and the
        # details must not be copied from it. `read_optional` returns `""` for a file that
        # exists and is empty, and `None` only for a path that does not exist -- so `main`'s
        # `if doc_text is not None` guard is TRUE here, and `check_roadmap_fields` and
        # `check_verdict` both run and both read this document; `check_verdict` prints its own
        # E2 line right beside these. What did not run is the rest of THIS function: the §3.1,
        # REQUIRED_DOC_TEXT and Appendix A checks below, the last two of which are criterion
        # C's only source of failures -- so early-returning E1 alone printed `PASS C` for a
        # deliverable with no §1.2 or §21 sections in it at all. The details below therefore
        # say what the empty file does not carry, which is true of the file itself and claims
        # nothing about which checks ran. They stay specific to emptiness either way: an empty
        # file and a file missing four sections are different things to fix.
        empty = "the finding file is empty, so it carries no "
        return [Failure("E1", empty + "§3.1 classification record"),
                Failure("E2", empty + "verdict sentence"),
                Failure("C", empty + "§1.2 or §21 section, and names no Appendix A source")]
    failures = [Failure("E1", f"the §3.1 classification record is missing {key}={value!r} from "
                              "the finding document")
                for key, value in classification.items() if value not in doc_text]
    failures += [Failure("C", f"the finding document is missing {label}")
                 for label, needle in REQUIRED_DOC_TEXT if needle not in doc_text]
    failures += [Failure("C", f"the finding document does not name Appendix A's {name!r} source")
                 for name in appendix_a if f"`{name}`" not in doc_text]
    return failures


def write_manifest(path: Path, rows: list[dict]) -> None:
    """Rendered first, secret-scanned, then written -- D3 §7.2 forbids a key value in any
    manifest, and this one is tracked. The scan can only see a value that is in the
    environment, so run this script with `.env` sourced for it to mean anything."""
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=FIELDS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(sorted(rows, key=lambda r: (r["source"], r["path"])))
    text = buffer.getvalue()
    c.assert_no_secrets(text)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def read_optional(path: Path) -> str | None:
    return path.read_text(encoding="utf-8") if path.exists() else None


def main() -> int:
    spec_text = SPEC.read_text(encoding="utf-8")
    classification = parse_classification_record(spec_text)
    appendix_a = parse_appendix_a_sources(spec_text)
    doc_text = read_optional(FINDING_DOC)

    if not c.AUDIT_ROOT.is_dir():
        # A fresh clone has no data/ tree at all -- it is gitignored. A later stage re-running
        # this gate there should be told that, not handed a FileNotFoundError traceback.
        print(f"FAIL [S] no audit root at {c.AUDIT_ROOT}; the raw tree is gitignored, so run "
              "the eleven source scripts before re-checking the stage")
        return 1

    found = enumerate_sources(c.AUDIT_ROOT)
    failures = check_source_set(found)
    summaries, load_failures = load_summaries(c.AUDIT_ROOT, found)
    failures += load_failures
    if not summaries:
        failures.append(Failure("S", "no source summaries found under data/raw/audit/"))

    rows, extract_failures = verify_recorded_extracts(summaries, REPO_ROOT)
    failures += extract_failures
    orphans = find_orphans(c.AUDIT_ROOT, summaries)
    failures += [Failure("S", f"orphan file under the audit root, registered by no summary: "
                              f"{path}") for path in orphans]
    failures += check_env_untracked(REPO_ROOT)
    failures += check_gitignore(read_optional(GITIGNORE))
    failures += check_findings_filled(summaries)
    failures += check_document(doc_text, classification, appendix_a)
    # Unguarded: E3 reads only `qcew_routes.earliest_year_served`, so putting it behind the
    # document guard would print PASS for a check that never ran.
    failures += check_year_boundary(summaries)
    if doc_text is not None:
        failures += check_roadmap_fields(summaries, doc_text)
        failures += check_verdict(summaries, doc_text)

    registered = len(registered_paths(summaries))
    print(f"sources: {len(EXPECTED_SOURCES)} expected, {len(found)} on disk, "
          f"{len(summaries)} with a valid summary")
    print(f"summaries validated: {len(summaries)}; extracts verified: {len(rows)} of "
          f"{registered} registered")
    print(f"manifest, dangling direction: {registered - len(rows)} recorded extract(s) not "
          "verifiable on disk")
    print(f"manifest, orphan direction: {len(orphans)} file(s) under the audit root that no "
          "summary registers")
    if failures:
        print(f"manifest NOT written (this run failed): {MANIFEST}")
    else:
        write_manifest(MANIFEST, rows)
        print(f"manifest written: {MANIFEST} ({len(rows)} rows)")

    for failure in failures:
        print(f"FAIL [{failure.criterion}] {failure.detail}")
    failed = {failure.criterion for failure in failures}
    for criterion, text in CRITERIA.items():
        print(f"{'FAIL' if criterion in failed else 'PASS'} {criterion}: {text}")
    print("EXIT CRITERIA:", "PASS" if not failures else f"{len(failures)} FAILURE(S)")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
