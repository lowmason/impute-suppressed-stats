# Deferred items

Unticked items are the deferred-work backlog; `/deferred` owns triage.
Live roadmap stages (`specs/*-roadmap.md`) are out of scope here — the
roadmap is its own backlog.

## logging-employment-spec-roadmap derivation — 2026-09-03

- [ ] **SRC-OTH-005 — BEA detailed state-industry employment bridge.**
      `specs/logging-employment-spec.md` §8.5 SRC-OTH-005 requires BEA detailed
      employment to be treated as optional historical input and bridged
      explicitly (§5.3, §11.11 BEA row). Deferred rather than staged because
      BEA discontinued the detailed state industry employment tables
      `SAEMP25` and `SAEMP27` on 2024-09-27, so there is no current table to
      bridge; the concept also differs from the estimand (BEA counts
      full- and part-time jobs including self-employment, against §3.2's
      private QCEW-covered wage-and-salary jobs), which §2.2's BEA row
      already forbids forcing into agreement. The spec ships
      `bea.enabled: false` in Appendix A and Rollout D6 records the scope
      decision. Revisit only if BEA republishes detailed state-industry
      employment, or if an archived vintage is wanted as a §13.9 sensitivity
      arm — in which case the bridge needs the §8.6 fields and explicit
      source-vintage metadata, not a column rename.

## 1-stage0-logging-employment-spec — 2026-09-04

Stage 0 shipped with 0 Critical findings and no wrong measured value. Everything
below is either a reviewer Minor triaged as defer, or a question whose answer
belongs to a later stage. `SRC-OTH-005`'s premise above was re-confirmed at this
gate: Stage 0 audited no BEA source and produced nothing that bears on the
`SAEMP25`/`SAEMP27` discontinuation, so the recorded reason still stands.

### Open questions routed to later stages

- [ ] **The no-retabulation premise is carried by no cited source.** All eight
      `naics_vintage_by_year` entries in `data/raw/audit/qcew_codes/summary.json`
      rest on it, and it is honestly marked as uncited rather than asserted. A
      real BLS citation would close it. Touches `scripts/audit/qcew_codes.py`.
- [ ] **Appendix A vs the forest-source verdicts.**
      `specs/logging-employment-spec.md` Appendix A ships `tpo.enabled: false` and
      `fia.enabled: false`; Stage 0 measured both `access.status: verified`. These
      are different predicates — a configuration default versus a reachability
      measurement — so Stage 0 juxtaposes them in `specs/findings/source-audit.md`
      and deliberately does not reconcile them. **Stage 7's call.**
- [ ] **Stage 3 needs a substitute allocation anchor.** `SRC-QCEW-006` came back
      `decline` for UNVERIFIABILITY, not geography: every one of the 96 testable
      months carries at least one suppressed states+DC cell, so the employment
      identity is untestable on a complete published state sum. Stage 3 must name
      a substitute anchor or accept a weaker assumption. Recorded in the plan's own
      `> Deviation` note at Task 5 Step 6.
- [ ] **`cbp_metadata.lfo_by_year` is null for all eight window years** — the one
      roadmap-named field that shipped no value. Human ruling at this gate: carry
      as a §1.2 row rather than re-run. The "why" is recorded in the summary's
      sibling `notes` key and in `specs/findings/source-audit-notes.md`, and the
      exit gate declares it in `LEGITIMATELY_EMPTY_FINDINGS` rather than passing it
      silently. **Stage 1 (parser) should issue a dedicated `LFO,LFO_LABEL` query.**
- [ ] **`cbp_regime.unknown_years = [2024]`.** CBP's 2024 disclosure regime is
      undetermined because the vintage is not published yet. Stage 1 fails closed on
      an unknown regime, which is the correct behaviour; revisit when 2024 CBP ships.

### Reviewer Minors triaged as defer

- [ ] **`scripts/audit/qcew_identity.py`: two sets named by predicates that
      over-collect.** `NO_OTHER_AREA` conflates "no such area" with "area exists but
      published nothing"; `states_dc_short_span_areas` is built by grouping present
      rows, so it is structurally incapable of reporting a zero-row area — which is
      why DC (96 absent months) does not appear in this summary even though
      `qcew_panel` records it. Neither is live today. Two-line fix: report
      `sorted(c.STATE_AREAS - set(present))` alongside `short_span`.
- [ ] **`scripts/audit/qcew_panel.py`: `emplvl_raw_nonzero_rows` uses
      `strict=False` + `fill_null(0)`,** so a non-numeric raw value on a suppressed
      row counts as "not nonzero" — the one case the counter exists to catch. Not
      live (every real value parses). Fix the comparison or narrow the docstring;
      do not ship the current pairing.
- [ ] **`scripts/audit/qcew_panel.py`: `build_panel` and `main` are two independent
      call sites** of the same `build_long` → `_conform` composition. They agree
      today; nothing enforces it. Having `build_panel` return `(panel, predicates)`
      removes the seam.
- [ ] **`scripts/audit/qcew_routes.py`: the multi-year bulk-disagreement branch is
      unexercised** — `bulk_years_required` is `[]`, so no real data reaches it.
      Correct by inspection; a synthetic dict through the reduction would make it
      demonstrated rather than reasoned.
- [ ] **`html_title` exists in three byte-identical copies**
      (`cbp_metadata.py`, `bds_detail.py`, `susb_layout.py`), justified as "audit
      scripts are standalone PEP 723 files with no import between them" — true of
      script-to-script imports, but every one of them imports `_common`, which is
      the natural home. The risk is a fix to one not propagating.
- [ ] **`scripts/audit/cbp_metadata.py`: three request sites remain unguarded by
      `fetch_json_or_none`** (the dataset re-fetch, `variables.json`, and
      `geography.json`), plus `vresp.json()["variables"]` which raises `KeyError` on
      an unexpected shape. A 404 or malformed body there still crashes mid-loop and
      produces the dangling-manifest state `cfe0c1f` was written to prevent.
- [ ] **`scripts/audit/verify_extracts.py`: `enabled.setdefault(current, False)`
      types a default.** All ten Appendix A sources carry an explicit `enabled:`
      line today, so nothing false ships — but a future spec source without one
      would render `false`, indistinguishable from a spec-declared false, **with a
      test affirming it**. Fix: `bool | None` and render "not declared".
- [ ] **`scripts/audit/verify_extracts.py`: `classification_block`'s `Raises:`
      paragraph names the error that is lost but not the return value that replaces
      it** — when a fence follows an unclosed §3.1 fence it returns lines spanning
      later sections, departing from its own summary line. Unreachable on today's
      spec.
- [ ] **`scripts/audit/verify_extracts.py`: `check_roadmap_fields`'s
      document-presence check matches a quoted key name anywhere in the document**
      rather than in the owning source's fence. Measured safe today (zero
      double-quoted `ROADMAP_FIELDS` keys appear in the hand-written notes).
- [ ] **`specs/findings/source-audit.md`'s seam signpost has a second, weaker
      exception:** the whitespace-collapsed `> **Recorded access reason:**`
      blockquote. The extract-count exception is now named; this one is not.
- [ ] **Two vocabularies now ship side by side in the `ces` findings.**
      `publication_level_by_sm_state_code` and `near_miss_sm_state_codes` were
      renamed at this gate, but the six `states_with_*` counts keep their
      plan-mandated names while carrying the identical over-collection (they are
      computed over all 55 codes). `series_by_state` has the same implication and no
      ruling. **Stage 7 consumers must read `states_dc_tally`, not the six counts.**
- [ ] **Two gate-work fixes ship without tests:** the `ces_levels` "sm.state codes"
      rewording (`tests/audit/test_ces_levels.py`'s `broader_code_note` tests never
      pinned that clause) and `cbp_regime`'s `max()` empty-list guard (no pure seam).
      Both are visible in the shipped artifacts, so regression would not be silent.
- [ ] **`published_start` / `published_end` have no defined semantics.** They mean
      three different things across sibling summaries — measured publication bounds
      in `qcew_routes`, the window restated in `qcew_codes` (whose titles files are
      not year-indexed at all) and in `qcew_size`. This is a plan defect, not
      implementer drift: the task briefs prescribe the typed values verbatim. The
      ambiguity is now documented beside `COVERAGE_KEYS` in `scripts/audit/_common.py`;
      **Stage 1 must not compare the key across sources without reading that note.**
- [ ] **`bds/naics_11.json` is not hash-reproducible** — three fetches gave three
      hashes; rows are equal as sets but their order varies. Any future re-run of
      `bds_detail.py` will churn that extract's hash in the manifest. Similarly,
      FIA's `evalidator.jsp` flaps 403↔500 between runs and `/fullreport` drifts a
      few bytes, so `forest_sources.py` re-runs are not byte-stable either.
- [ ] **Repo-wide pre-existing `ruff I001` import-order noise**, untouched by this
      stage.

## 2-stage1-logging-employment-spec — 2026-09-05

### Raised during Tasks 7–9

- [ ] **`probe_slice_boundary` probes every candidate year rather than stopping at
      the first one served.** Ascending sort makes `served[0]` and an early exit
      return the same value, so this is cost, not correctness — but Task 16's live
      run pays it as ~17 sequential `data.bls.gov` requests where ~5 would settle
      the boundary. Left as the plan specifies it; revisit if the live run is slow
      or if BLS rate-limits. The full sweep does buy one thing an early exit would
      not: a complete per-year record of what the route served that run.
- [ ] **`tests/audit/` also fails `black`, not just `ruff I001`.** The existing
      repo-wide I001 item above undercounts the debt: 14 files under `tests/audit/`
      would be reformatted. `src/logging_employment/` and `tests/unit/` are clean
      under both, so a `black`/`ruff` gate can be enforced on the package today and
      on `tests/audit/` only after a dedicated sweep.
- [ ] **The bulk-route branch is exercised only under a synthetic boundary.**
      Stage 0 measured `bulk_years_required = []`, so with the boundary where it
      sits today no window year routes to bulk and no live run will ever take that
      path. `route_for_year` is tested by passing `earliest_slice_year=2020`, and
      `read_bulk_zip` by a reduced fixture. Neither is a substitute for the branch
      having run end-to-end against a real bulk download; if the boundary ever moves
      past a window year, treat that path as unproven in production.
- [ ] **`source_row_hash` is computed with `map_elements`,** i.e. one Python call
      per output row. Fine at the 5,430 rows one quarter produces; the full D1
      window is 32 quarters across three sources, and Task 14 rebuilds all of it
      twice to prove byte-identity. If that run is slow, this is the first thing to
      look at — `pl.concat_str(...).hash()` is not a substitute (it is not sha256
      and not stable across Polars versions), so a native replacement needs care.
