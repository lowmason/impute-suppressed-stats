# /// script
# requires-python = ">=3.12"
# dependencies = ["httpx>=0.27"]   # _common imports httpx
# ///
"""Render every source summary plus the hand-written notes into specs/findings/source-audit.md.

Idempotent in the strong sense: the output is a pure function of the twelve summaries, the
notes file and the spec, so re-running without re-running an audit script rewrites the same
bytes. The hand-written notes file is inlined verbatim, so re-running never clobbers prose.

Deviations from the plan's illustrative code, each established against the twelve shipped
summaries rather than assumed:

1. **The illustrative renderer drops `access.reason` for every `verified` source.** It prints
   the reason only when the status is not `verified`, and all twelve sources measured
   `verified` -- so `fia`'s and `tpo`'s recorded reasons, the two longest pieces of prose
   evidence in the audit, would appear nowhere in the document. Printing it unconditionally
   instead would write the literal `None` for the ten sources whose reason is null. Here the
   whole `access` object is rendered as JSON (where `null` is the honest rendering), and a
   recorded reason is additionally quoted as prose only when there is one.

2. **`coverage_span` and `access` appeared only in the truncated glance table.** The
   illustrative per-source section fences `findings` alone, so the full recorded value of
   every coverage and access field existed nowhere in the document. Both are now fenced in
   full per source.

3. **The glance table truncated with `route[:67] + "..."`.** `coverage_span` values are
   heterogeneous -- a bare year, an empty string, a comma-joined pair, a month range, a
   hyphenated year range, and full prose paragraphs. `fia`'s `uncovered` runs past 1300
   characters and carries an `INFERENCE MARKER, OPENING`/`CLOSING` pair; a mid-string cut
   would ship half a marked span, which is precisely the scope violation the marker convention
   exists to prevent. `cell` prints short values verbatim and replaces long ones with a
   derived descriptor pointing at the per-source section, where the value is rendered whole.

4. **Only the `route` cell escaped `|`.** One recorded value carries a pipe today --
   `qcew_routes`'s route, "slice: ... | bulk: ..." -- and it happens to sit in the one column
   the illustrative code escaped. A stray pipe silently splits a markdown row and shifts every
   later column, and which field carries one is a property of the evidence, not of the column.
   Escaping is therefore done per cell, by the one `cell` function, which also collapses
   newlines.

5. **The §3.1 classification record was written as literals.** All four fields are published in
   the spec's own §3.1 block, so they are parsed from it (`verify_extracts.parse_classification
   _record`) rather than retyped into a tracked document that no test would contradict.

6. **The header stamped the wall-clock run date**, which made the tracked document change
   whenever it was regenerated, whether or not any evidence had. The header now reports the
   newest `generated_utc` among the summaries, labelled as that and not as a generation date.

`EXPECTED_SOURCES` and the spec parsers live in `verify_extracts`, and this module imports
them: the gate must not depend on the renderer, so the dependency runs the other way.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import _common as c  # noqa: E402
import verify_extracts as v  # noqa: E402

OUT = c.FINDINGS_DIR / "source-audit.md"
NOTES = c.FINDINGS_DIR / "source-audit-notes.md"

# A glance-table value longer than this many *characters of markdown* is replaced by a derived
# descriptor rather than cut. Named for characters rather than cells on purpose: "cell"
# everywhere else in this audit means a state-month data cell, and 80 is the number §2.2's
# binding decision forbids encoding as a confidentiality threshold. This constant is neither --
# it is a table-width limit, and the collision in the old name was gratuitous.
GLANCE_TABLE_CHAR_LIMIT = 80

# Which Appendix A `sources:` entry each audited source key belongs to. Declared, not inferred
# from the name: `qcew_size` is both an Appendix A key and a prefix-shaped sibling of the four
# `qcew_*` audit keys, so a longest-prefix rule would be a coincidence rather than a reason.
# `check_appendix_a_map` validates it against both the audited set and the parsed spec block.
APPENDIX_A_KEY_BY_SOURCE = {
    "bds": "bds",
    "cbp_metadata": "cbp",
    "cbp_regime": "cbp",
    "ces": "ces",
    "fia": "fia",
    "qcew_codes": "qcew",
    "qcew_identity": "qcew",
    "qcew_panel": "qcew",
    "qcew_routes": "qcew",
    "qcew_size": "qcew_size",
    "susb": "susb",
    "tpo": "tpo",
}


def fence(obj) -> str:
    return "```json\n" + json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + "\n```"


def cell(value) -> str:
    """One markdown table cell: verbatim when short, a derived descriptor when long.

    Never a mid-string cut -- see this module's docstring, point 3. `null` and an empty string
    are rendered as what they are, not as a reading of what they mean.
    """
    if value is None:
        return "null"
    collapsed = " ".join(str(value).split())
    if not collapsed:
        return "(empty)"
    if len(collapsed) > GLANCE_TABLE_CHAR_LIMIT:
        return f"recorded value ({len(str(value))} chars) -- see the per-source section"
    return collapsed.replace("|", "\\|")


def check_appendix_a_map(sources: list[str], appendix_a: dict[str, bool]) -> None:
    """Fail loudly on either drift: an audited source the map does not place, or a map entry
    naming an Appendix A source the spec no longer ships."""
    unmapped = sorted(set(sources) - set(APPENDIX_A_KEY_BY_SOURCE))
    if unmapped:
        raise SystemExit(f"audited source(s) {unmapped} have no Appendix A mapping")
    unknown = sorted({key for key in APPENDIX_A_KEY_BY_SOURCE.values() if key not in appendix_a})
    if unknown:
        raise SystemExit(f"APPENDIX_A_KEY_BY_SOURCE names {unknown}, absent from Appendix A")


def appendix_a_rows(
    summaries: dict[str, dict], appendix_a: dict[str, bool]
) -> list[tuple[str, str, str, str]]:
    """One row per Appendix A source, in the spec's own order: its shipped `enabled` default,
    the audit source keys that measured it, and what they measured."""
    rows = []
    for name, enabled in appendix_a.items():
        audited = sorted(s for s, key in APPENDIX_A_KEY_BY_SOURCE.items()
                         if key == name and s in summaries)
        statuses = sorted({summaries[s]["access"]["status"] for s in audited})
        rows.append((
            f"`{name}`",
            "true" if enabled else "false",
            ", ".join(f"`{s}`" for s in audited) if audited else "not audited",
            ", ".join(statuses) if statuses else "not measured",
        ))
    return rows


def machine_path_disclosure(summaries: dict[str, dict]) -> str:
    """Name the sources whose rendered values embed an absolute path from the machine the audit
    ran on, counted rather than asserted: an audit script rerun elsewhere changes the answer,
    and a typed count in a tracked document is what goes stale. Only the three objects this
    document renders are scanned -- every `extracts[].path` is absolute by construction, and
    those reach the document as a count, not as a value."""
    root = str(v.REPO_ROOT)
    named = sorted(name for name, payload in summaries.items()
                   if any(root in json.dumps(payload[section], ensure_ascii=False)
                          for section in ("coverage_span", "access", "findings")))
    if not named:
        return "No rendered value embeds an absolute path from the machine this audit ran on."
    listed = ", ".join(f"`{name}`" for name in named)
    verb = "value embeds" if len(named) == 1 else "values embed"
    return (f"{len(named)} rendered {verb} an absolute path from the machine this audit ran "
            f"on ({listed}).")


def render_document(
    summaries: dict[str, dict],
    notes_text: str,
    classification: dict[str, str],
    appendix_a: dict[str, bool],
) -> str:
    newest = max(payload["generated_utc"] for payload in summaries.values())
    identity = summaries["qcew_identity"]["findings"]
    lines = [
        "# Stage 0 source audit -- findings",
        "",
        f"**Assembled** by `scripts/audit/assemble_finding.py` from the {len(summaries)} source "
        f"summaries under `data/raw/audit/`. **Newest `generated_utc` among them:** {newest}.",
        "**Spec:** `specs/logging-employment-spec.md` · "
        "**Roadmap:** `specs/logging-employment-spec-roadmap.md`, Stage 0 · "
        "**Plan:** `specs/plans/1-stage0-logging-employment-spec.md`",
        f"**Window (D1):** {c.WINDOW_START} → {c.WINDOW_END} · "
        f"**Industry:** {c.INDUSTRY_CODE} ({classification['industry_title']}) · "
        "**Ownership:** private · **Geography:** states + D.C.",
        "",
        "**Classification (§3.1):** the source prompt supplied "
        f"`{classification['industry_code_supplied']}`, which is not a valid NAICS code. It is "
        "recorded, not silently replaced -- "
        + ", ".join(f"`{key} = '{value}'`" for key, value in classification.items())
        + ". These four values are read from the spec's own §3.1 block, not retyped here.",
        "",
        "Every value below is rendered from `data/raw/audit/<source>/summary.json`. Extract "
        "hashes are recorded in `source-audit-extracts.csv` and re-verified, in both "
        "directions, by `scripts/audit/verify_extracts.py`, which is also this stage's exit "
        "gate: re-run it to re-check the five criteria the roadmap's Stage 0 `Exit:` line "
        "states, and the artifact integrity they rest on. How much that proves has one limit "
        "worth naming: the first criterion's field-by-field half runs against a mapping from "
        "that line's prose onto findings keys, hand-authored inside the gate and marked there "
        "as a reading rather than a measurement. "
        "Raw bytes live under `data/raw/audit/`, which is gitignored -- so the "
        "manifest records each extract's path relative to the repository root, while the "
        "summaries record it absolutely, as `_common.AUDIT_ROOT` is absolute. Recorded values "
        "are otherwise reproduced verbatim -- the summaries are the evidence, and rewriting "
        "them here would make this document disagree with them. "
        + machine_path_disclosure(summaries),
        "",
        "## Sources audited",
        "",
        "Recorded values, verbatim where they fit. `(empty)` and `null` are what the source "
        "summary recorded, not a reading of what they mean; a long value is replaced by a "
        "descriptor and rendered whole in its per-source section below.",
        "",
        "| Source | Access | Route | Covers of D1 window | Not covered |",
        "|---|---|---|---|---|",
    ]
    for name, payload in summaries.items():
        coverage = payload["coverage_span"]
        lines.append(
            f"| `{name}` | {cell(payload['access']['status'])} | "
            f"{cell(payload['access']['route'])} | {cell(coverage['covered'])} | "
            f"{cell(coverage['uncovered'])} |")

    lines += [
        "",
        "## SRC-QCEW-006 branch verdict",
        "",
        f"**Branch:** `{identity['branch']}`. The sentence below is `qcew_identity`'s recorded "
        "`verdict_sentence`, rendered from its summary rather than retyped; the notes section "
        "that follows states what the branch means for later stages.",
        "",
        "> " + identity["verdict_sentence"],
        "",
        "## Appendix A `enabled` defaults beside what this audit measured",
        "",
        "Appendix A ships an `enabled` default per source; this audit measured whether the "
        "source's bytes can be fetched. Those are two different predicates -- a configuration "
        "default about whether the pipeline uses a source, and a measurement of reachability "
        "-- so this table juxtaposes them and leaves the reconciliation to the stage that owns "
        "each decision. The §21 section in the notes below gives this audit's verdict on the "
        "row that is genuinely decided by an extraction audit.",
        "",
        "| Appendix A source | `enabled` default | Audited as | Measured access |",
        "|---|---|---|---|",
    ]
    lines += ["| " + " | ".join(row) + " |" for row in appendix_a_rows(summaries, appendix_a)]

    lines += ["", notes_text.rstrip(), "", "## Per-source findings", ""]
    for name, payload in summaries.items():
        access = payload["access"]
        lines += [f"### `{name}`", "", "**access**:", "", fence(access), ""]
        if access.get("reason"):
            lines += ["> **Recorded access reason:** " + " ".join(access["reason"].split()), ""]
        lines += ["**coverage_span**:", "", fence(payload["coverage_span"]), "",
                  "**findings**:", "", fence(payload["findings"]), "",
                  f"_Extracts: {len(payload['extracts'])}; summary `generated_utc` "
                  f"{payload['generated_utc']}._", ""]
    return "\n".join(lines) + "\n"


def main() -> None:
    spec_text = v.SPEC.read_text(encoding="utf-8")
    classification = v.parse_classification_record(spec_text)
    appendix_a = v.parse_appendix_a_sources(spec_text)

    found = v.enumerate_sources(c.AUDIT_ROOT)
    mismatches = v.check_source_set(found)
    if mismatches:
        raise SystemExit("\n".join(f"FAIL {failure.detail}" for failure in mismatches))
    summaries, failures = v.load_summaries(c.AUDIT_ROOT, found)
    if failures:
        raise SystemExit("\n".join(f"FAIL {failure.detail}" for failure in failures))
    if not NOTES.exists():
        raise SystemExit(f"{NOTES} is required; write it before assembling")
    check_appendix_a_map(found, appendix_a)

    text = render_document(summaries, NOTES.read_text(encoding="utf-8"), classification,
                           appendix_a)
    # D3 §7.2: no key value may appear in any manifest. This document is tracked, and the scan
    # can only see a value that is in the environment -- source `.env` for it to mean anything.
    c.assert_no_secrets(text)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text, encoding="utf-8")
    print(f"wrote {OUT} from {len(summaries)} summaries")


if __name__ == "__main__":
    main()
