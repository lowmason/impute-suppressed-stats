# Deferred items

Unticked items are the deferred-work backlog; `/deferred` owns triage.
Live roadmap stages (`specs/*-roadmap.md`) are out of scope here — the
roadmap is its own backlog.

**Every item carries a stable `D-nnn` id.** D-001..D-084 were assigned in file
order on 2026-09-10 and cross-checked row-by-row against the 84-row ledger in
`docs/reviews/2026-09-09-system-review.md` §4.1, so that review's D-citations
resolve here. **Ids are permanent and are never renumbered**: a new item takes
the next unused number regardless of where it is inserted, and a closed item
keeps its id so a citation to it never dangles. Cite an item by id, never by
title — titles have been rewritten in place before (`e34ef16`).

## logging-employment-spec-roadmap derivation — 2026-09-03

- [ ] `D-001` **SRC-OTH-005 — BEA detailed state-industry employment bridge.**
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

- [x] `D-002` **The no-retabulation premise is carried by no cited source.** All eight
      `naics_vintage_by_year` entries in `data/raw/audit/qcew_codes/summary.json`
      rest on it, and it is honestly marked as uncited rather than asserted. A
      real BLS citation would close it. Touches `scripts/audit/qcew_codes.py`.
      → done 2026-09-08 (/deferred quick fix): BLS publishes the reference-year-to-vintage
      mapping and still places 2017-2021 on NAICS 2017 four years after NAICS 2022 arrived
      (`https://www.bls.gov/cew/questions-and-answers.htm`, Q "What versions of NAICS and SIC
      does the QCEW program use?", last modified 2026-02-13; the same mapping appears at
      `https://www.bls.gov/cew/classifications/industry/home.htm`, last modified 2026-01-28), so
      all eight entries are validated by direct observation rather than by inference from an
      introduction quarter. Applied to the two live `src/` sites — `harmonize/naics.py`'s
      `_VINTAGE_BOUNDARY_YEAR` comment carries the quotation and the source, and
      `baselines/historical.py`'s docstring records that the citation CONFIRMS its
      stop-at-the-break default rather than flipping it.
      TWO THINGS THE CITATION CHANGED that the item did not anticipate. (1) The premise AS WORDED
      here is false: the same BLS answer records that 1990-2000 "had been reclassified under the
      NAICS 2002" as a one-time reconstruction across classification SYSTEMS, so QCEW has
      retabulated history once. The operative claim — no NAICS-vintage-to-vintage recode — is what
      is cited, and both `src/` sites now say so. (2) The item's "Touches
      `scripts/audit/qcew_codes.py`" understated the blast radius by an order of magnitude: four
      live prose sites, two generated artifacts, six `vintage_for_year` call sites and
      `config.py:151`. Two follow-ons are recorded under the /deferred triage section at the end
      of this file.
      SEARCH SCOPE, so a re-check knows what was covered: bls.gov only, read through the live
      browser DOM. `curl` is WAF-blocked on www.bls.gov (HTTP 403) and a WebSearch snippet drifted
      the key sentence's tense, so neither was used for a quotation; every quoted string was read
      character-for-character out of the rendered page, including collapsed accordion content that
      `innerText` hides.
- [ ] `D-003` **Appendix A vs the forest-source verdicts.**
      `specs/logging-employment-spec.md` Appendix A ships `tpo.enabled: false` and
      `fia.enabled: false`; Stage 0 measured both `access.status: verified`. These
      are different predicates — a configuration default versus a reachability
      measurement — so Stage 0 juxtaposes them in `specs/findings/source-audit.md`
      and deliberately does not reconcile them. **Stage 7's call.**
- [x] `D-004` **Stage 3 needs a substitute allocation anchor.** `SRC-QCEW-006` came back
      `decline` for UNVERIFIABILITY, not geography: every one of the 96 testable
      months carries at least one suppressed states+DC cell, so the employment
      identity is untestable on a complete published state sum. Stage 3 must name
      a substitute anchor or accept a weaker assumption. Recorded in the plan's own
      `> Deviation` note at Task 5 Step 6.
      **Confirmed by measurement 2026-09-05 at the Stage 2 gate, still open.** The engine
      reports all 1,227 suppressed state-month cells as `bound_status = 'unbounded'` with a
      null `selected_upper`; nonnegativity is the only public fact that touches one. The item
      is no longer an inference from Stage 0's verdict, and Stage 3's anchor must also cope
      with a null upper endpoint rather than two finite ones.
      **→ retired 2026-09-05: Stage 3 named the anchor — `reconcile/anchor.py` stamps
      `anchor_basis = 'declared_national_total'`, and `scaling.py` reads a null upper as
      infinite.** Admission is `closure_audit`'s gap-0 test on `qtrly_establishments` — the
      universe, not the employment identity, so `SRC-QCEW-006`'s `decline` still stands and
      `anchor.py`'s docstring says so. The stamped value is pinned by
      `tests/unit/test_anchor.py`, not by `ANCHOR_BASES`, which an open item below records as
      constraining nothing.
- [x] `D-005` **`cbp_metadata.lfo_by_year` is null for all eight window years** — the one
      roadmap-named field that shipped no value. Human ruling at this gate: carry
      as a §1.2 row rather than re-run. The "why" is recorded in the summary's
      sibling `notes` key and in `specs/findings/source-audit-notes.md`, and the
      exit gate declares it in `LEGITIMATELY_EMPTY_FINDINGS` rather than passing it
      silently. **Stage 1 (parser) should issue a dedicated `LFO,LFO_LABEL` query.**
      **Closed 2026-09-05 by Stage 1 Task 11 Step 6.** `ingest.cbp.build_query`
      selects `LFO,LFO_LABEL` as output columns rather than sending `LFO=001` only
      as a filter. The live 2023 query returned 200 with `LFO_LABEL` present and
      equal to `"All establishments"` on all 188 rows — the label for the `001`
      code the window queries filter on. The response is shipped as
      `tests/fixtures/cbp/data_113310_2023_live.json` and pinned by
      `test_the_live_response_serves_the_lfo_label_the_query_asks_for`.
- [x] `D-006` **`cbp_regime.unknown_years = [2024]`.** CBP's 2024 disclosure regime is
      undetermined because the vintage is not published yet. Stage 1 fails closed on
      an unknown regime, which is the correct behaviour; revisit when 2024 CBP ships.
      **Closed 2026-09-05 by Stage 1 Tasks 12 and 16.** `harmonize.disclosure`
      records 2017–2023 and omits 2024, so `regime_for_year(2024)` raises
      `UnknownDisclosureRegimeError`; `build_harmonized` additionally refuses to
      persist the `"unknown"` label even when config permits a report to carry it.
      Confirmed against the live API: `variables.json` for 2024 returns 404, the
      fetch skipped the year on a bare non-200 `continue`, and the window pull
      produced 7 CBP snapshot rows rather than 8. **Note what that does and does not
      show.** No 2024 bytes entered the store, so `regime_for_year` — whose only
      non-test call site is `build.py`, on the build path — was never reached. The
      fail-closed guard is proven by an injected-snapshot test, not by this run; the
      run demonstrates only that the year is absent upstream. Re-open when a 2024
      vintage ships, at which point the guard becomes reachable for real.

### Reviewer Minors triaged as defer

- [x] `D-007` **`scripts/audit/qcew_identity.py`: two sets named by predicates that
      over-collect.** `NO_OTHER_AREA` conflates "no such area" with "area exists but
      published nothing"; `states_dc_short_span_areas` is built by grouping present
      rows, so it is structurally incapable of reporting a zero-row area — which is
      why DC (96 absent months) does not appear in this summary even though
      `qcew_panel` records it. Neither is live today. Two-line fix: report
      `sorted(c.STATE_AREAS - set(present))` alongside `short_span`.
      **→ done in plan 6.** Both halves. `NO_OTHER_AREA` is renamed `NO_DISCRIMINATING_QUARTER`:
      it was reached by a panel whose non-state amount is WITHHELD as well as by one with no such
      area, so the verdict contradicted its own sibling counter inside one returned dict.
      `states_dc_areas_with_no_rows` closes the second half — DC carries no row in any of the 96
      months and appeared in neither this key nor `short_span`, while `qcew_panel`'s own summary
      recorded it. The derived note names the 51-code universe too, because `states_dc_areas`
      (50) and `states_dc_area_months_absent` (84) are both denominated against PRESENT areas.
      Artifact regenerated offline; the rename touched no artifact.
- [x] `D-008` **`scripts/audit/qcew_panel.py`: `emplvl_raw_nonzero_rows` uses
      `strict=False` + `fill_null(0)`,** so a non-numeric raw value on a suppressed
      row counts as "not nonzero" — the one case the counter exists to catch. Not
      live (every real value parses). Fix the comparison or narrow the docstring;
      do not ship the current pairing.
      **→ done in plan 6: fixed the comparison, not the docstring.** The counter feeds a note
      into the committed source-audit.md, so the defect landed in a published artifact. Neither
      offered fix was quite right: moving `fill_null` after the comparison and filling True
      corrects the unparseable case but then counts a row that published NOTHING as nonzero, so
      an explicit `is_not_null()` keeps all three cases apart. Measured on
      `["-", "0", "5", None]`: old 1, naive fix 3, shipped 2. Artifact-neutral — the live panel
      has 0 nulls and 0 unparseable, so the count stays 3558.
- [x] `D-009` **`scripts/audit/qcew_panel.py`: `build_panel` and `main` are two independent
      call sites** of the same `build_long` → `_conform` composition. They agree
      today; nothing enforces it. Having `build_panel` return `(panel, predicates)`
      removes the seam.
      **→ done in plan 6, but not by the remedy this item proposed.** `(panel, predicates)` is
      insufficient: `main` also needs the pre-`_conform` `long` frame, because `emplvl_raw`
      exists only there and `disclosure_code_values` reads it. A `PanelBuild` NamedTuple returns
      all three and `build()` is the single composition site; `build_panel` survives as
      `build(own).panel`, so all eight existing test call sites are untouched.
- [x] `D-010` **`scripts/audit/qcew_routes.py`: the multi-year bulk-disagreement branch is
      unexercised** — `bulk_years_required` is `[]`, so no real data reaches it.
      Correct by inspection; a synthetic dict through the reduction would make it
      demonstrated rather than reasoned.
      **→ already closed by `c075e33` (2026-09-04 18:52), 93 minutes BEFORE `1defbf0` (20:25)
      recorded this item; confirmed during plan 7's recon, which carried no task for it.**
      `column_parity` was extracted from `main()` in that same commit specifically so the branch
      could be tested, and it shipped with the synthetic dict this item asks for:
      `test_identical_is_false_when_the_bulk_years_disagree_with_each_other`
      (`tests/audit/test_qcew_routes.py:45`) passes two bulk years whose headers differ while the
      reference year matches the slice exactly, so bulk non-uniformity is the only conjunct
      driving `identical` False; `:61` pins the recorded content. A `sys.settrace` line trace over
      the six tests reaches every executable line of `column_parity` (`qcew_routes.py:61-86`),
      including `:79`, this branch's else arm. The item's *premise* stands — `bulk_years_required`
      is still `[]` — and is pinned separately at `verify_extracts.py:125-128`, whose
      `LEGITIMATELY_EMPTY_FINDINGS` lists `("qcew_routes", "bulk_years_required")` first.
- [x] `D-011` **`html_title` exists in three byte-identical copies**
      (`cbp_metadata.py`, `bds_detail.py`, `susb_layout.py`), justified as "audit
      scripts are standalone PEP 723 files with no import between them" — true of
      script-to-script imports, but every one of them imports `_common`, which is
      the natural home. The risk is a fix to one not propagating.
      **→ done in plan 6, and the risk had already materialised.** The four executable lines are
      identical; the DOCSTRINGS are not — `susb_layout`'s had already lost the "including when
      `body` isn't HTML at all" clause the other two carry. So this repaired existing drift
      rather than preventing hypothetical drift. Now `_common.html_title`, with the corrected
      rationale recorded rather than dropped. 13 test assertions repointed.
- [x] `D-012` **`scripts/audit/cbp_metadata.py`: three request sites remain unguarded by
      `fetch_json_or_none`** (the dataset re-fetch, `variables.json`, and
      `geography.json`), plus `vresp.json()["variables"]` which raises `KeyError` on
      an unexpected shape. A 404 or malformed body there still crashes mid-loop and
      produces the dangling-manifest state `cfe0c1f` was written to prevent.
      **→ done in plan 6, after fixing the guard itself first.** Two corrections to the item:
      `fetch_json_or_none` is in `cbp_metadata.py`, not `_common.py`; and it was ITSELF reaching
      the orphan state — `record_extract` ran before `resp.json()` and only `HTTPStatusError`
      was caught, so a 200 carrying Census's HTML error page was written and registered, then
      raised. Routing the three sites through the OLD helper would have made one failure mode
      worse. A silent-wrong path the item does not name is closed too: `.get("fips", [])` on a
      malformed geography body reached `zero_pull_cause` as `state_available=False` and
      persisted "geography_unavailable" — a fetch failure recorded as a fact about CBP.
      Verified by unit tests on extracted pure helpers; the script was NOT run.
- [x] `D-013` **`scripts/audit/verify_extracts.py`: `enabled.setdefault(current, False)`
      types a default.** All ten Appendix A sources carry an explicit `enabled:`
      line today, so nothing false ships — but a future spec source without one
      would render `false`, indistinguishable from a spec-declared false, **with a
      test affirming it**. Fix: `bool | None` and render "not declared".
      **→ done in plan 6.** `bool | None`, and the one renderer is three-way. The affirming test
      was flipped rather than deleted — its assertion WAS the defect. Artifact-neutral, proven
      by regeneration: all ten sources declare `enabled:`, so no cell becomes "not declared".
      That left the new branch dead on today's spec, so it is pinned by its own unit test.
- [x] `D-014` **`scripts/audit/verify_extracts.py`: `classification_block`'s `Raises:`
      paragraph names the error that is lost but not the return value that replaces
      it** — when a fence follows an unclosed §3.1 fence it returns lines spanning
      later sections, departing from its own summary line. Unreachable on today's
      spec.
      **→ done in plan 6: documented, deliberately not refused.** Two committed constraints rule
      refusal out — stopping the closing scan at the next heading reintroduces the
      `#`-inside-a-fence defect already pinned, and a new raise would be an uncaught traceback
      rather than a FAIL line, because `main` calls this before any check runs and outside any
      handler. Worth recording: the bad return reaches `assemble_finding`, which writes it into
      the tracked document's Classification paragraph, so the consequence was a wrong value in a
      deliverable, not just a confused gate. A characterization test pins it.
- [x] `D-015` **`scripts/audit/verify_extracts.py`: `check_roadmap_fields`'s
      document-presence check matches a quoted key name anywhere in the document**
      rather than in the owning source's fence. Measured safe today (zero
      double-quoted `ROADMAP_FIELDS` keys appear in the hand-written notes).
      **→ done in plan 6.** Scoped to the owning source's `**findings**:` fence. The "measured
      safe" is a QUOTING CONVENTION, not a structural guarantee: zero keys appear double-quoted
      in the notes, but twelve of twenty appear there backticked. The cost is recorded in the
      code — the gate now depends on three literals the assembler emits, so renaming any of them
      breaks the gate on correct work. Verified: EXIT CRITERIA still PASS over all 20 entries.
- [x] `D-016` **`specs/findings/source-audit.md`'s seam signpost has a second, weaker
      exception:** the whitespace-collapsed `> **Recorded access reason:**`
      blockquote. The extract-count exception is now named; this one is not.
      **→ done 2026-09-05 (/deferred quick fix).** Named in `assemble_finding.py`'s
      `seam_signpost` and the document regenerated — the artifact is generated, so editing the
      `.md` alone would have been reverted by the next run. The item's "whitespace-collapsed"
      premise was corrected before writing: the collapse is a no-op on both recorded reasons
      (`fia`, `tpo` carry no newline, tab or double space), so the sentence states the
      transform without asserting it changes anything. Two tests — one pins the sentence, one
      pins that it is true of the artifact.
- [ ] `D-017` **Two vocabularies now ship side by side in the `ces` findings.**
      `publication_level_by_sm_state_code` and `near_miss_sm_state_codes` were
      renamed at this gate, but the six `states_with_*` counts keep their
      plan-mandated names while carrying the identical over-collection (they are
      computed over all 55 codes). `series_by_state` has the same implication and no
      ruling. **Stage 7 consumers must read `states_dc_tally`, not the six counts.**
- [x] `D-018` **Two gate-work fixes ship without tests:** the `ces_levels` "sm.state codes"
      rewording (`tests/audit/test_ces_levels.py`'s `broader_code_note` tests never
      pinned that clause) and `cbp_regime`'s `max()` empty-list guard (no pure seam).
      Both are visible in the shipped artifacts, so regression would not be silent.
      **→ done in plan 7** (Tasks 1 and 2). The only one of the five P3 items accurate as worded.
      Both gaps were mutation-proven before the fix: reverting `ces_levels.py:180` to
      `"States {states} publish"` left the file at 37 passed / 3 skipped / 0 failed, and stripping
      all three `if years_available else ""` guards left all 37 `cbp_regime` tests passing.
      **The item's last sentence is wrong for B2.** With today's `years_available = [2017..2023]`
      the guard's empty branch leaves no trace in any artifact, so removing it is entirely silent;
      it goes loud only on the one run where it would have mattered, and on that run the script
      dies instead of writing the summary that records that outcome. "no pure seam" is literally
      true and a helper was deliberately NOT extracted — `main()` is drivable offline with
      `AUDIT_ROOT` and `build_client` monkeypatched, which buys the coverage without touching a
      script that renders into `specs/findings/source-audit.md:1167-1168`.
- [ ] `D-019` **`published_start` / `published_end` have no defined semantics.** They mean
      three different things across sibling summaries — measured publication bounds
      in `qcew_routes`, the window restated in `qcew_codes` (whose titles files are
      not year-indexed at all) and in `qcew_size`. This is a plan defect, not
      implementer drift: the task briefs prescribe the typed values verbatim. The
      ambiguity is now documented beside `COVERAGE_KEYS` in `scripts/audit/_common.py`;
      **Stage 1 must not compare the key across sources without reading that note.**
- [ ] `D-020` **`bds/naics_11.json` is not hash-reproducible** — three fetches gave three
      hashes; rows are equal as sets but their order varies. Any future re-run of
      `bds_detail.py` will churn that extract's hash in the manifest. Similarly,
      FIA's `evalidator.jsp` flaps 403↔500 between runs and `/fullreport` drifts a
      few bytes, so `forest_sources.py` re-runs are not byte-stable either.
- [x] `D-021` **Repo-wide pre-existing `ruff I001` import-order noise**, untouched by this
      stage.
      **→ done 2026-09-05 (/deferred quick fix).** `ruff check --select I --fix` over
      `scripts/audit` and `tests/audit`: all 22 I001 gone, 46 → 24 total violations with every
      other category byte-identical. `--select I` was required — a bare `--fix` also deletes
      three deliberate `# noqa: E402` markers guarding `sys.path` late imports. The remaining
      24 (ISC004, TRY004, UP037, RUF100, RET501, UP047) are pre-existing and outside this item.

## 2-stage1-logging-employment-spec — 2026-09-05

### Raised during Tasks 7–11

- [ ] `D-022` **`probe_slice_boundary` probes every candidate year rather than stopping at
      the first one served.** Ascending sort makes `served[0]` and an early exit
      return the same value, so this is cost, not correctness — but Task 16's live
      run pays it as ~17 sequential `data.bls.gov` requests where ~5 would settle
      the boundary. Left as the plan specifies it; revisit if the live run is slow
      or if BLS rate-limits. The full sweep does buy one thing an early exit would
      not: a complete per-year record of what the route served that run.
- [x] `D-023` **`tests/audit/` also fails `black`, not just `ruff I001`.** The existing
      repo-wide I001 item above undercounts the debt: 14 files under `tests/audit/`
      would be reformatted. `src/logging_employment/` and `tests/unit/` are clean
      under both, so a `black`/`ruff` gate can be enforced on the package today and
      on `tests/audit/` only after a dedicated sweep.
      **→ done 2026-09-05 (/deferred quick fix), with a trap the item did not name.** All 28
      black-dirty files (14 + 14) are formatted. Black takes its target from the project's
      `requires-python = ">=3.14"`, and at that target it rewrites `except (A, B):` into PEP 758
      form in `qcew_routes.py` and `forest_sources.py` — PEP 723 scripts whose own headers
      promise `>=3.12`, where the result does not parse. No test catches it: the suite runs on
      3.14. `[tool.black] target-version = ["py312"]` was pinned in `pyproject.toml`.
      **SUPERSEDED 2026-09-09 by plan 12's Task 0: black is gone from this repo** — it and
      `ruff format` disagreed on eight files and `pyproject.toml` declared both, so "is the tree
      formatted?" depended on which command you ran. THE TRAP THIS ITEM FOUND SURVIVES THE
      SWITCH, and is the reason the removal was not a straight deletion: `ruff` takes its target
      from the same `requires-python` and rewrites the same `except (A, B):` in the same PEP 723
      scripts (re-measured 2026-09-09: TWO files, `forest_sources.py` and `qcew_routes.py`, not the
      three first written here). A global `target-version = "py312"` would silently retarget every
      pyupgrade rule for `src/`; ruff has no per-file target-version WITHIN one config, though it
      does resolve a nearest-ancestor config per file, so a `scripts/audit/ruff.toml` is a real
      alternative that was not taken. The guard is instead SCOPE — format `src tests`, never `ruff format .` — recorded beside
      `[tool.ruff]` and in `CLAUDE.md`. Read this item's last sentence as history, not as
      configuration that exists.
- [x] `D-024` **The bulk-route branch is exercised only under a synthetic boundary.**
      Stage 0 measured `bulk_years_required = []`, so with the boundary where it
      sits today no window year routes to bulk and no live run will ever take that
      path. `route_for_year` is tested by passing `earliest_slice_year=2020`, and
      `read_bulk_zip` by a reduced fixture. Neither is a substitute for the branch
      having run end-to-end against a real bulk download; if the boundary ever moves
      past a window year, treat that path as unproven in production.
      **→ done in plan 7** (Task 3), but the item is wrong in BOTH directions and the tick is
      narrowed accordingly.
      *Its premise is false:* there is no production bulk path to be under-exercised.
      `read_bulk_zip` has zero callers in `src/`, and `fetch_source`'s bulk arm
      (`fetching.py:117-118`) is structurally dead for **every** input, not merely at today's
      boundary — `probe_slice_boundary` draws from `range(min(window_years) - 5,
      min(window_years) + 1)` and returns its earliest served element, so
      `boundary <= min(window_years) <= y` always and `route_for_year` returns `"slice"` for every
      window year. Filed below as its own source-side item.
      *Its literal obligation was satisfiable after all:* the audited archive is on disk at
      `data/raw/audit/qcew_routes/bulk/2017_qtrly_by_industry.zip` (460,476,363 bytes) with its
      sha256 tracked at `specs/findings/source-audit-extracts.csv:123`, so "a real bulk download"
      needed no network. Task 3 runs against it skip-if-absent and gets what the four-member
      fixture cannot give: against the real 2,232 members, `113310` matches exactly 1 and `11331`
      exactly 3.
      *What the four new tests do NOT prove:* that any production caller composes these functions,
      because `read_bulk_zip` has no caller in `src/` and `build_harmonized` reads only `*.csv`
      through `read_slice_csv`. The item's trailing condition is now self-monitoring rather than
      prose — `test_every_window_year_still_routes_to_the_slice_endpoint` derives the boundary and
      the window from the tracked findings document at runtime and reddens if a re-audit moves
      it.
- [ ] `D-025` **`source_row_hash` is computed with `map_elements`,** i.e. one Python call
      per output row. Fine at the 5,430 rows one quarter produces; the full D1
      window is 32 quarters across three sources, and Task 14 rebuilds all of it
      twice to prove byte-identity. If that run is slow, this is the first thing to
      look at — `pl.concat_str(...).hash()` is not a substitute (it is not sha256
      and not stable across Polars versions), so a native replacement needs care.

### Raised during Tasks 11-16

- [ ] `D-026` **`cbp_state_size` has no column for `EMP_N_F`, the only field that carries
      CBP's per-cell noise magnitude.** §7.5's field list was written against the
      columns Stage 0's query selected, and Stage 0 never selected `EMP_N_F`
      (`emp_n_f_in_response: false` for all eight years), so the omission is a spec
      gap this stage's live run discovered rather than a parser defect.
      `employment_noise_range` ← `EMP_N` is the correct mapping by Census's own
      naming ("Noise range for number of employees"), and `EMP_N` is the literal
      string `'0'` on every row of every window year — so the shipped column
      preserves a field that carries no information while the one that does is
      dropped at the parse layer. Measured on the live 2023 response this run
      (188 rows, `113310` × state × `LFO=001`): `EMP_N_F` is present on every row,
      distributed `G: 103, H: 51, J: 34` — methodology.html's low / moderate / high
      noise bands. Not urgent and not a data loss: `ingest.cbp.build_query` already
      selects `EMP_N_F`, so the immutable raw store captures it at rest and a later
      stage can re-parse the stored bytes without re-fetching. Closing it means
      amending §7.5 and `CBP_STATE_SIZE_SCHEMA` (a fingerprint change), which is a
      spec decision rather than an implementation one. **Stage 6's measurement
      model is the consumer that needs it** (SRC-CBP-004 enters CBP employment as a
      noisy measurement; noise magnitude is what that model would weight by).

- [ ] `D-027` **Nothing re-derives `EMPFLAG_WITHHELD_CODES` against a post-2017 layout.**
      The table is derived from the 2017 state record layout, which is the last year
      EMPFLAG was used, so it is correct for the D1 window. A test re-derives it from
      the shipped copy of that document. If CBP is ever read outside 2017–2023, the
      derivation has no later layout to check against and an unrecognized flag will
      halt the run — the intended §18.3 behaviour, but worth knowing before the run
      halts.

### Raised during Task 16's live run

- [ ] `D-028` **CBP responses are not byte-reproducible, so the immutable store cannot
      deduplicate them.** Measured this run: two fetches of `2023/cbp` minutes apart
      returned rows that are *identical as sets* (188 each, zero rows in one and not
      the other) in a **different order**, so the content sha256 differs and
      `RawStore.put` writes a second object. Five of the seven window years now carry
      two snapshots. This is the same phenomenon Stage 0 recorded for
      `bds/naics_11.json` ("three fetches gave three hashes; rows are equal as sets
      but their order varies"), now confirmed for CBP. The build no longer stacks
      them — `build.snapshot_paths` selects one file per reference key, preferring the
      run manifest and halting with `AmbiguousSnapshotError` when nothing disambiguates
      — so the INV-007 exposure is closed. What is *not* closed is the store growing a
      copy per fetch. Options if that becomes a problem: canonicalize CBP JSON (sort
      rows) before hashing, which would break "bytes verbatim"; or record a
      content-independent identity alongside the hash. Neither is obviously right, so
      neither is done. **QCEW is unaffected** — all 32 quarters re-fetched to identical
      bytes.

- [ ] `D-029` **`qcew_national_size` carries every industry, not just 113310.** 140,343 rows
      over the eight window years, against 1,298 for `cbp_state_size`. Task 10's parser
      filters to national geography and to size codes other than "all sizes", and uses
      its `industry` argument only for the dimensionality assertion, never as a row
      filter. §7.4's schema has an `industry_code` column, so a multi-industry table is
      consistent with the contract and this is not a defect — but it is ~99% of the
      harmonized layer's row count and every `build-harmonized` run pays for it twice
      under the byte-identity check. Revisit if the rebuild gets slow, together with the
      `map_elements` item above.

## 3-stage2-logging-employment-spec — 2026-09-05

Stage 2 shipped every task and every roadmap `Exit:` clause, verified on the real D1 window.
Nothing was descoped. The three items below are the ones the stage deliberately did not close.

- [ ] `D-030` **`evidence_kind` has no column of its own.** §7.8's field list has no place for the warrant
      behind a restriction, so `constraints/rows.py` writes it into `provenance_text` behind a
      fixed `EVIDENCE_PREFIX` (`evidence_kind=`). That keeps it queryable in the persisted
      `constraint_row` table and lets §9.3's forbidden warrants be refused by name, but it is
      stringly typed: a query for assumed-threshold rows is a substring match, not a column
      predicate. Promoting it to a real column is a spec amendment to §7.8, which this plan
      deliberately did not make. Deferred by the plan itself ("Record it as a deferred item at
      completion"). Closing it means amending §7.8, adding the column to `CONSTRAINT_ROW_SCHEMA`
      in `src/logging_employment/contracts.py`, and dropping the prefix from the factory.

- [ ] `D-031` **No check covers a hard row spanning two area-months with differing release vintages.**
      `constraints/cells.py::_assert_one_vintage_per_cell` groups by `(area_fips,
      reference_month)` and catches one area-month published under two release vintages.
      `constraints/rows.py::vintage_status` reads `naics_vintage`, which is the only vintage
      `TARGET_CELL_SCHEMA` carries. Neither sees a row whose cells span two area-months published
      under different release vintages. On the D1 window this silence is correct rather than a
      hole — `qcew_monthly` carries 32 release vintages, one per reference quarter, so
      period-to-period variation is the ordinary state of a retrospective panel. The stronger
      statement, established at the review gate by enumerating every builder: it is unreachable
      **without a new builder**, not merely unreached by today's data. `observed_value_rows`,
      `nonnegativity_rows`, `integrality_rows`, `size_support_rows` and `rounding_interval_row`
      are single-cell by construction; `size_margin_rows` is the only multi-cell builder and it
      groups by `reference_month` and looks up its national total under that same key, so every
      coefficient in the row shares one month by construction. It becomes reachable the moment a
      builder couples two periods (a Stage 6 model constraint, or any across-period margin). Closing it
      means carrying `release_vintage` onto `target_cell` — a §7.7 amendment — and feeding it to
      `vintage_status` alongside `naics_vintage`.

- [ ] `D-032` **`classify_bound_status` labels an integer interval containing no integer
      `partially_identified`.** `constraints/bounds.py` applies §9.6's `ceil(L) == floor(U)` rule;
      for an interval like `[41.2, 41.9]` that is false, so the cell is reported as partially
      identified even though an integer-valued cell cannot lie anywhere in it. Unreachable while
      `constraints.enforce_integrality` is `true`, because an interval that narrow triggers the
      MILP re-solve, which reports the component infeasible first. It becomes reachable if that
      config key is flipped to `false`. Pinned by
      `tests/unit/test_bound_status.py::test_an_integer_interval_containing_no_integer_is_not_called_exactly_recoverable`
      so the behaviour is recorded rather than assumed. Closing it means deciding whether an
      empty integer interval is an infeasibility (raising) or a distinct `bound_status`, which is
      a §7.10 question.

### Review-gate items (whole-branch review, 2026-09-05)

The review returned no Critical findings. All six Important findings were fixed on the branch
before merge and pinned by tests. The items below are the Minor findings judged not worth fixing
now; each is unreachable at Stage 2's scale or coefficients, and each names what makes it reachable.

- [ ] `D-033` **The §9.7 diagnostic degrades silently on a box-shaped infeasibility.**
      `constraints/diagnostics.py` adds slack to coupling rows only, so a component made
      infeasible by its column bounds alone (a malformed class band with `n*lower > n*upper`)
      reports `minimum slack: 0`, `irreducible infeasible subsystem: unavailable` and `candidate
      conflicts: none detected` -- a report that reads "nothing is wrong" as the final message of
      a halted run. Unreachable through the shipped builders, which derive both endpoints from
      the same published establishment count. Closing it means giving the minimum-slack model
      slack variables on the column bounds too, and adding a diagnostics test for the box shape.

- [ ] `D-034` **`rank._shape_key` formats the matrix at `precision=12`.** Two equality matrices differing
      past the twelfth decimal share a CON-005 cache key, so the second component reports the
      first's rank. Every hard coefficient this stage emits is +/-1, so it cannot bite today. It
      becomes reachable if a later stage introduces fractional hard coefficients (a share, a
      deflator). Fix is `matrix.tobytes()` plus shape rather than `np.array2string`. Related:
      `rank.numerical_rank_of` passes `rank_tolerance` to `np.linalg.matrix_rank` as an
      *absolute* singular-value threshold, which is equally fine at +/-1 and equally brittle if
      magnitudes grow.

- [x] `D-035` **`solve_bounds` rescans the frames once per component and once per row.**
      `constraints/bounds.py` runs a full `built.rows.filter(...)` per component and a full
      `built.coefficients.filter(...)` per row, and `column_specs` is computed twice per component
      (once in `solve_bounds`, again inside `solve_component`) -- roughly 28,000 full scans for
      the 15.7s D1 run. Fine at 4,775 cells; name it before Stage 3 adds cells and soft rows.
      Pre-grouping the coefficients into a dict keyed by `constraint_id` once would collapse it.
      → done 2026-09-06 (commit `4e08f2d`): triaged by `/deferred` as a quick fix, then
      re-scoped to plan breadth once measurement disproved the item's own prescription, and
      executed directly in-session under confirmed scope rather than through `writing-plans` —
      so no plan file exists and no completion protocol ticked this; the disposition it was
      finally done under is not the one it was ticked by. One frozen `SystemIndex` built per
      solve, threaded through `column_specs`, `matrix_rows`, `equality_matrix` and
      `solve_component`. Measured 59,389 scans → 2 and 11.833s → 0.354s on `data/constraints`
      (median of five warm reps). Two corrections to this item, both measured rather than
      argued: the count was 59,389, not ~28,000, and the prescribed coefficient dict alone
      removes 36% of the calls but only 17% of the scan time — 14,172 of the scans are in
      `rank.py`'s `equality_matrix`, reached from `solve_bounds` via `rank_table`, so the fix
      covers that file too. Gated on an old-vs-new differential over `data/constraints`,
      `data/staged` and both tracked fixtures (9,856 records, list-order comparisons plus
      parquet hashes, zero differing), with the dormant integer re-solve forced and diffed
      separately, because the test suite provably cannot see a permuted coefficient order.

- [ ] `D-036` **`exactly_identified` and `integer_exactly_identified` never disagree.**
      `classify_bound_status` assigns both the same value on the integer branch, so two columns of
      `deterministic_bounds` carry one column's information. §7.10 gives field names without
      definitions, and the agreement is *correct* when the MILP ran (`selected_*` are then the
      integer optima) -- but if the two are meant to differ, §7.10 has to say how first.

- [x] `D-037` **`cli._constraints_dir` derives §6.2's path instead of reading a config key.**
      `Path(cfg.storage.staged_uri).parent / "constraints"` silently relocates the constraint
      tables if `staged_uri` is ever pointed outside `data/`. A `StorageConfig.constraints_uri`
      would make the location configured rather than inferred.
      **→ done 2026-09-05 (/deferred quick fix).** `StorageConfig.constraints_uri` is an
      originated key defaulting to `data/constraints`, the exact path the derivation resolved
      to, so configs written before it stay valid under `extra="forbid"`. Appendix A needed no
      amendment — no conformance gate reads the `storage:` block — but `config.yaml`'s
      byte-for-byte header claim did: it now names the originated key, and the narrowed claim
      was re-derived against the spec rather than retyped. Both integration fixtures redirect
      `constraints_uri` into `tmp_path`; without that the suite writes the real
      `data/constraints/` and still passes.

## 4-stage3-logging-employment-spec — 2026-09-05

- [x] `D-038` **`MAX_SCALE_RATIO = 100.0` is an originated tripwire with no spec warrant.**
      `baselines/interfaces.py` refuses a composite whose two arms' medians differ by more than
      100x. The factor is this package's decision, chosen to sit far above any honest
      employees-vs-employees ratio and far below the ~1e4 units mismatch it was written to catch.
      Nothing in §10 or §12 speaks to it. If a future baseline legitimately produces arms an order
      of magnitude apart, the number needs re-deriving rather than nudging.
      **→ done in plan 9: deleted, not re-derived.** The item's own remedy assumed a better
      threshold exists. Measured on the D1 window, it does not: substituting a raw establishment
      count for the scaled fallback — the exact bug the guard was written to catch — produces
      arm-median ratios of 0.182-0.811 for the share family and 0.160-0.316 for §10.4, entirely
      inside the honest 0.947-4.996 range, and reintroducing it tripped the guard zero times while
      shipping own-cell estimates up to 6.12x too large. The honest range and the bug's range
      overlap, so the unit is now carried structurally by `baselines/interfaces.py::EmployeeWeights`
      — a frozen wrapper `compose` refuses to accept a bare dict in place of (R-COMP-1 to R-COMP-3).
      `tests/integration/test_baseline_golden.py` inherits the guard's remaining job and says so in
      its module docstring: a corrupt column or a moved CBP vintage changes the NUMBERS while every
      arm stays honestly typed, and the golden is now the only check that reddens on either.

- [x] `D-039` **§10.3's fallback scales by the DISCLOSED intensity; §10.4's uses the NATIONAL one.**
      Both put the fallback arm in employees, and each is defensible on its own terms — §10.4's is
      exactly its own n->0 shrinkage limit, §10.3 has no such limit to appeal to and uses a
      published ratio of two published sums. But two baselines answering "how many employees does
      an establishment carry" differently is a divergence no section asked for. See
      `baselines/simple.py:establishment_fallback_in_employees` and
      `baselines/intensity.py:national_march_intensity`.
      **→ done in plan 9: declared, deliberately not standardised.** The divergence is kept
      (R-COMP-7) — §10.4's national value is exactly its own shrinkage limit as the CBP cell count
      goes to zero, a derivation §10.3 and §10.6 have nothing equivalent to appeal to, so collapsing
      the two would have made one of them arbitrary. What was actually wrong was that the choice was
      unstated and duplicated: each composing baseline built and scaled its own arm. Both functions
      this item names have moved into a new `baselines/fallback.py`, which owns the ONLY construction
      that turns §10.2 exposure into employees and takes the intensity as an argument; each estimator
      declares its choice as `fallback_intensity`, and `baseline_manifest.json` reports it per
      estimator, so an arm can be checked against its name without reading source. Measured on D1 the
      two values were never far apart (disclosed 5.442-6.380, national 5.914-6.139) — this was an
      unexplained divergence in a layer Stage 4 is about to score, not a numerical error.

- [x] `D-040` **`disclosed_intensity` reads the partition from the context while the residual comes from
      the anchor.** `baselines/simple.py` looks up `context.partitions[anchor.reference_month]`,
      but `national_residual` was handed a `Partition` argument directly. Under a Stage 4
      pseudo-suppression mask the two agree only if the harness rebuilds
      `EstimatorContext.partitions` from the same mask it passed to the anchor — nothing enforces
      that, and a mismatch would scale the fallback off the unmasked partition without any signal.
      This is the mask-parameterisation rule one level above where the plan stated it. Stage 4
      should either thread the partition through the estimator call or assert the two agree.
      **→ STILL OPEN, and re-scoped by plan 9.** Plan 9 took the second option INSIDE the
      estimator layer and left the harness half for Stage 4, which is why this box stays unticked.
      Two corrections to the pointers above, since the code moved under them: `disclosed_intensity`
      now lives in `baselines/fallback.py`, not `baselines/simple.py`; and it no longer merely
      reads the context's partition — `_assert_the_partition_is_the_anchors` recomputes
      `national_residual` from that partition and raises `ConceptViolationError` when it disagrees
      with `anchor.residual` (R-COMP-8, pinned by T-5 in `tests/unit/test_baselines_fallback.py`).
      The check witnesses the DISCLOSED side only, deliberately. What remains for Stage 4 is the
      obligation this creates on the harness: it must rebuild `EstimatorContext.partitions` from
      the same mask it hands the anchor, or every composing estimator now fails closed on it.
      §10.9 of `specs/logging-employment-spec.md` states that requirement; Stage 4's plan closes
      this item and should record that plan 9 supplied it.
      **→ done in plan 11 (2026-09-07).** Closed STRUCTURALLY rather than by assertion, which is
      stronger than the option this item asked for. Plan 11's harness never builds an
      `EstimatorContext` or a `Partition` at all: `validate/mask.py::apply_mask` masks the FRAME
      and returns a new `HarmonizedData`, and `run_baselines` derives both the partition and the
      anchor from that single object (`baselines/runner.py:110-119`). There is no second object to
      disagree with, so the mismatch is unconstructible rather than merely checked. Plan 11's
      evidence §3 measured why the alternative fails: a Partition-only mask leaves the constraint
      system fixing the answer (`bound_status='observed'`, an `eq` row at the held-out value) AND
      leaves the truth in `context.partitions[m].missing["employment_value"]`, one column read from
      any estimator — latent today only because none of the ten happens to read it. Pinned by
      `tests/integration/test_validate_leakage.py::test_the_partition_the_runner_derives_carries_no_held_out_truth`,
      which fails the moment anything reintroduces a partition built from unmasked data.

- [ ] `D-041` **The `general_method` guard lives at the CLI, not in the reconciliation layer.**
      `require_supported_method` is exported from `reconcile.projection` but is called only where
      config is read. `reconcile_matrix` takes no config argument, so Stage 6 must call the guard
      itself when it wires the matrix path — nothing in the layer forces it to.
      **Correction 2026-09-07 (unregistered-work audit): the premise above is false, and the work
      is larger than it says.** `require_supported_method` is called from NOWHERE — not the CLI,
      not anywhere. `rg 'require_supported_method' src/` returns the definition
      (`reconcile/projection.py:41`), two docstring mentions (`projection.py:26`, `draws.py:19`)
      and the re-export (`reconcile/__init__.py:22,43`), and no call site. Plan 4 created the guard
      (its deviation note at `specs/plans/completed/4-stage3-logging-employment-spec.md:1611`) and
      then removed its only caller from `reconcile_draws` (:2139, "The `general_method` guard is
      removed — this path is §12.3"); a CLI call was never added. `git log -S` over `src/` shows
      two commits, both in `reconcile/`. So a Stage 6 implementer following this item will search
      the CLI for a call site that has never existed. The guard is currently dead code, and the
      ruling needed is where to call it, not where to move it from.

- [x] `D-042` **`kl_project` returns silently on an infeasible bounded system.**
      Its loop breaks on step size, not on violation, so a fully-clipped update exits on iteration
      one: `kl_project(seed=[1,1], margins=[[1,1]], targets=[10], upper=[1,1])` returns `[1., 1.]`
      with violation 8.0 and no exception. `reconcile_matrix` compensates with its own post-check,
      and a 5,417-case feasible sweep showed violation never increases — but `kl_project` is
      exported and Stage 5/6 can call it directly. It should return the achieved violation or
      raise. (Whole-branch review, Important.)
      **→ done in plan 5.** It returns `(x, violation)` and deliberately does NOT raise. The item
      offered either; measurement chose. `projection.py`'s own contract is "violation must never
      increase -- rather than a convergence proof", and §17.3's property tests feed jointly
      infeasible two-margin systems on purpose: achieved violation exceeds `tolerance` in 3 of 25
      existing cases, worst 16.15. A raise would have broken a spec-mandated test. Not a half-done
      fix — the branch not taken is recorded so it is not re-opened as one. `reconcile_matrix`
      formats the returned value rather than recomputing it.

- [x] `D-043` **The three provenance enums are declared but never enforced.**
      `RECONCILIATION_STATUSES`, `WEIGHT_BASES` and `ANCHOR_BASES` in `contracts.py` constrain
      nothing: `run_baselines` writes string literals and only `BASELINE_RESULT_SCHEMA`'s dtypes
      are checked, so a typo reaches `baseline_results.parquet` and passes every test. Validate
      the three columns before returning. (Whole-branch review, Important.)
      **→ done in plan 5.** `contracts.assert_declared_provenance` sits beside the tuples, since the
      defect was that declaration and enforcement lived apart; `run_baselines` calls it before
      returning. That one call covers the whole write path: `runner.py` is the only constructor of a
      `BASELINE_RESULT_SCHEMA` frame in `src/`, and the `reconcile` command reads the parquet rather
      than building one. Nulls stay legal and are pinned, so declines remain representable. The
      shipped D1 run's 12,270 rows already conform — this guards drift, it did not fix live data.

- [x] `D-044` **`integerize` has three bound-handling gaps, all latent on D1 and all live in Stage 6.**
      No `lower <= upper` check (a contradictory pair silently violates the lower bound); the cap
      loop iterates `upper` rather than `values`, so a cap for an absent cell injects a phantom
      entry; and the ordering key is the raw fractional part, which is no longer largest-remainder
      once `floors` has been raised by `lower` or lowered by `upper`. D1 has `lower=0, upper=None`
      throughout. (Whole-branch review, Minor.)
      **→ done in plan 5, with one premise narrowed.** The phantom entry needs a NEGATIVE cap: with
      `cap=0` the guard is `0 > 0` and no entry appears, so the reachable case is the one now tested.
      All three closed and each reproduced against the shipped code first. Behaviour is unchanged
      where it should be: over 4,000 random D1-shaped inputs old and new agree on every case; over
      4,000 bounded inputs they differ in 118, all from the ordering fix, with no bound violation and
      no sum error. Every pre-existing test passes unchanged.

- [x] `D-045` **`BreakAdjustedShare` collapses to `RollingMedianShare` below four shares.**
      The pre-execution audit measured 111 of 360 cells taking that branch, and
      `test_section_10_3_ships_exactly_five_variants` only checks that five distinct estimator ids
      exist — nothing detects two variants computing the same number. (Whole-branch review, Minor.)
      **→ done in plan 7** (Task 4), with two of its own claims corrected.
      *The headline is right and bitwise:* `historical.py:223-224` is character-identical to
      `RollingMedianShare._reduce`, and at n=2/n=3 both return the same `float.hex()`.
      *"111 of 360 cells taking that branch" conflates two numbers from its own source.*
      `specs/findings/stage3-plan-audit.md:451` says **108** of 360 take the branch and **111**
      produce an identical value. Neither reproduces against shipped code, and `data/` is
      gitignored so the audit's snapshot is unrecoverable — no count was restated or pinned.
      *"(Whole-branch review, Minor.)" is the wrong provenance:* the only source in the repo is
      `stage3-plan-audit.md:449-455`, tagged **[NIT]** in the pre-execution plan audit.
      *The branch was never unreached* — `tests/unit/test_baselines_historical.py:78` already
      drove it at three shares while asserting only `> 0.0` and `== OWN`. The gap was assertions.
      Scope held to test-only plus one docstring reword that the new tests would otherwise have
      contradicted; the threshold itself is deferred below.

- [x] `D-046` **`NoHarvestFactorError` is defined and never raised.**
      `errors.py` declares it for §10.5, but `HarvestProportional` returns a `Decline` instead,
      which is the correct behaviour. Either remove the class or document it as reserved for the
      Stage 7 path that will raise it.
      **→ done 2026-09-05 (/deferred quick fix): documented as reserved, not removed.** The
      roadmap settles it — Stage 7 produces "a live harvest-proportional baseline replacing
      Stage 3's declining stub". The docstring deliberately claims no §18.3 warrant: those
      eight bullets carry no missing-harvest-factor condition, so it names Stage 7 as owning
      the halt-vs-decline decision instead.

- [x] `D-047` **Task 18's property tests and four of the five cross-cutting audit units never ran.**
      The plan audit was stopped early after its subagents wrote into the working tree (see
      specs/findings/stage3-plan-audit.md). The four cross-cutting checks were re-run inline by
      hand and came back clean — mask-signature, call-site arity, anti-drift in test blocks, and
      §17.3 vacuity — but Task 18 was never machine-audited. Its twelve properties pass against
      the shipped implementation, which is evidence but not the same thing.
      **→ done in plan 7** (Task 5). Both halves of the item were discharged as machine audits.
      *Task 18's unit* ran as 24 source mutations over the twelve shipped tests, judged against
      `spec:1714-1716` and `spec:1737-1743`, with a full-suite run for each mutant surviving the
      unit file. Three holes, all closed: §12.3's `Σ U < R_t` refusal could be deleted with all
      1123 tests still green (the bracket-exhaustion `for...else` raises the same exception type
      and both candidate tests asserted only the type); property 4 passed under an identity
      `kl_project`; property 5 asserted `rel=1e-4` while `reconcile_matrix` itself refuses above
      `rtol=1e-6`. A fourth, found by the adversarial pass, was closed alongside:
      `test_integer_lower_and_upper_bounds_are_respected` passes no `lower=` at all, leaving the
      seat floor at `integerize.py:67` unpinned. The tolerance half of §17.3's last bullet, which
      no test in the repo varied, is now covered.
      *The cross-cutting units* — `mask-signature` was settled by the whole-branch review and
      `65c4480`; `§17.3 vacuity` is the above. The remaining two, which had only ever been
      hand-checked, were machine-run during plan 7's recon: **call-site arity CLEAN** (943 call
      sites bound with `inspect.Signature.bind()` against 262 definitions across the whole
      package — deliberately not scoped to `reconcile/`, since that narrowing is what made the
      mask-signature hand-verdict wrong — plus return arity, all 84 dataclass construction sites,
      the registry against the `Estimator` Protocol, the Typer surface, and the plan's own
      fences; a positive control caught 5/5 planted mismatches). **anti-drift in test blocks
      returned 6 findings**, none in plan 7's path and all filed below; the plan's own 46 python
      and 23 bash fences are clean.
      *Scope not covered, because a negative result without its scope overclaims:* the
      correctness of the reconcile implementations beyond what these mutants probe;
      `reconcile_draws`, the CLI and the manifest; other plans' code blocks; `tests/audit/`'s ~136
      numeric assert sites (swept, not individually classified); and `src/` docstrings beyond a
      targeted regex.

## 6-stage0-audit-hardening — 2026-09-05

- [ ] `D-048` **`emplvl_raw_nonzero_rows` now means "not a published zero", but three things still say
      "nonzero".** The comparison was fixed in plan 6 so an unparseable raw value is counted; the
      key name in `scripts/audit/qcew_panel.py`, the interpolated note at `qcew_panel.py:369` and
      its restatement at `:390` all still read "with a nonzero employment level in the source
      month columns". That sentence would be false for exactly the case the fix added.
      Deliberately not bundled: renaming the key changes a shipped `summary.json` key, so it
      carries the offline regeneration chain (`qcew_panel` → `qcew_identity` → `assemble_finding`
      → `verify_extracts`) plus a one-cell change to `source-audit-extracts.csv` from
      `panel.parquet`'s restamped `retrieved_utc` — a different kind of change from the
      comparison fix it would have ridden on.

## 7-p3-test-coverage — 2026-09-06

Raised during plan 7's recon and its adversarial verification pass. None is test-coverage work,
which is why none was folded into the batch. See specs/plans/completed/7-p3-test-coverage.md.

- [ ] `D-049` **The QCEW bulk route has no build-side consumer, and its fetch arm is unreachable.**
      `fetch_source` can acquire and store a bulk zip (`src/logging_employment/fetching.py:117-121`),
      but `build_harmonized` reads only `*.csv` through `read_slice_csv` (`build.py:174-183`) and
      `read_bulk_zip` has no caller in `src/` at all. The arm is unreachable for **any** probe
      outcome, not merely at today's measured boundary: `probe_slice_boundary` draws candidates from
      `range(min(window_years) - 5, min(window_years) + 1)` (`fetching.py:106`) and returns the
      earliest served one, so `boundary <= min(window_years) <= y` for every window year and
      `route_for_year` returns `"slice"` unconditionally. Were it reachable, three defects would be
      live, all measured: without a run manifest a bulk-routed year is silently dropped from
      `qcew_monthly.parquet`; with one, `snapshot_paths` ignores its `pattern` argument
      (`build.py:116-134`), returns the zip path, and `read_slice_csv` raises
      `ComputeError: invalid utf-8 sequence`; and the quarter loop fetches the year-level zip four
      times, producing four manifest rows against one content-addressed `raw_path` that
      `sorted(listed)` returns four times (INV-007 stacking). This is a delete-or-fix decision on
      dead code, not a condition to wait on. Touches `build.py` and `fetching.py`.

- [x] `D-050` **`BreakAdjustedShare`'s `<4` fallback is a design choice nobody chose.** The audit's own two
      options (`specs/findings/stage3-plan-audit.md:451`): scope the docstring — done in plan 7
      Task 4 — or return `None` below a minimum segment length so the cell takes the declared §10.2
      fallback. Whoever takes it needs a new fixture: `tests/fixtures/baselines/` has only three
      cells with a history, all length 6 and all one state-08 series, so the frozen golden contains
      no `<4` cell and cannot validate the change, while a D1 run would move roughly a third of the
      own-weight cells from `OWN` to `FALLBACK`. Plan 7's
      `test_below_four_shares_the_break_adjusted_variant_is_the_rolling_median` is deliberately
      silent on intent and is the test that must change.
      **→ done in plan 10, and the new fixture this item asked for was not needed.** The second
      option shipped: `_reduce` returns `None` unless the selected cut leaves at least two points
      in the recent segment. Two corrections to the item. First, the threshold is NOT a minimum
      segment length applied below a history length — it reads the CUT, so a length-3 history cut
      in the middle is kept and a length-12 history cut at its end is refused, a case `<4` cannot
      see and which this item did not know about (28 D1 cells, six of them length 12). Second, the
      frozen golden needed no new cell and was not re-pinned: all three of its cells with a history
      are length 6 with the cut at position 3, so every one is kept and
      `baseline_results_golden.parquet` is byte-identical. The rule is pinned directly on `_reduce`
      over bare share lists (T-1…T-6) instead, with T-7 driving the full `weights` path to hold
      that a refused cell is COMPOSED onto the §10.2 fallback rather than declined. The item's
      "roughly a third" was right: 101 of 342 own-weight cells, 29.5%.

- [x] `D-051` **`historical.py:227`'s `segment = shares[cut:] or shares` — the `or shares` arm is
      unreachable.** For n ≥ 4, `steps` has n−1 entries so `cut ∈ [1, n-1]` and the slice always has
      at least one element; below 4 the early return fires first. Verified exhaustively for
      n = 4..40. Delete the arm or record why it stands. Do not budget a test for it.
      **→ done 2026-09-06 (/deferred quick fix): arm deleted.** The conclusion was right; four of
      its supporting claims were not, and the line is 228, not 227.
      *The bound is stronger and cheaper than the item states.* It holds for every n ≥ 2, not just
      n ≥ 4, and is value-independent: `steps` has exactly n−1 entries, so `cut ∈ [1, n-1]` and
      `len(shares[cut:]) ≥ 1`; `list` defines no `__bool__` (`"__bool__" in vars(list)` is False),
      so list truthiness routes through `__len__` alone and a length-≥1 slice is always truthy.
      That is a proof, which makes "verified exhaustively for n = 4..40" both a misdescription —
      no sweep over float-valued lists is exhaustive — and unnecessary. It also means the arm is
      dead independently of the `<4` guard, so this closure does **not** constrain the open item
      above it, which proposes changing that guard.
      *"Unreachable" is exact only for `list`.* A `numpy` array fires the arm (a single-zero array
      is falsy) or raises on a multi-element one; `polars.Series` raises. Unreachable here because
      the sole call site feeds `history["share"].to_list()`, which is `list` for Float64,
      null-bearing and empty columns alike.
      *"Or record why it stands" was not a live option.* The arm contradicts its own class
      docstring — "At four or more shares this is not a plain median over the whole lookback" — and
      firing at n ≥ 4 would return exactly that plain median. It arrived verbatim from the Stage 3
      plan code block with no rationale recorded anywhere.
      *Why green means equivalence here, not absent coverage:* the control mutant `segment = shares`
      fails `test_the_five_variants_compute_five_different_numbers_on_one_history` and
      `test_the_baseline_output_matches_its_golden_fixture`, so the expression is discriminated.
      The item's one instruction that was exactly right: no test was added.

- [x] `D-052` **`projection.py:98`'s zero-seed floor is redundant with the clip at `:118`.** Deleting
      `x = np.maximum(np.asarray(seed, dtype=float), floor)` leaves all 1123 tests passing — and
      that is the correct answer, **not** a hole. `:118` is
      `x = np.clip(x, np.maximum(lower, floor), upper)` and runs on the full vector after every
      margin row, so §12.4's floor is re-imposed each iteration by a second line. Verified directly:
      on all-zero, one-zero and two-zero seeds the shipped and floor-deleted versions return
      identical output and identical violations. No test can kill this mutant and none should try.
      Remedy: delete one of the two lines, or document why both stand. Recorded because plan 7's
      recon proposed filing it as "a real MUST-level hole", which the adversarial pass disproved —
      the aged-claim pattern this file exists to prevent.
      **→ done 2026-09-06 (/deferred quick fix): both lines documented and pinned. The item is
      wrong — the recon was right and the adversarial pass that overturned it was the aged claim.**
      Deleting `:98` is not behaviour-preserving. Measured on an ordinary feasible system with no
      degeneracy — seed `[0, 2]`, margins `[[1,1],[0,1]]`, targets `[50, 1]`, config defaults:
      shipped returns `[49., 1.]` at violation 3.2e-12, floor-deleted returns `[5e-11, 1.]` at
      violation **49.0**.
      *Mechanism:* `current = float(row @ x)` is read BEFORE the clip, so `:98` sets the scale
      factor the first margin row applies to every cell and no later clip undoes an applied one.
      The two lines are also different quantities — the clip bounds the ITERATE to
      `np.maximum(lower, floor)`, `:98` floors the SEED to `floor` — and "runs on the full vector
      after every margin row" is false three ways: the `touched.any()` guard `continue`s past it
      for an all-zero row, and it never runs at all for empty margins or `max_iterations=0`.
      *`:98` is also the function's only copy of `seed`.* `np.asarray` hands a float64 caller its
      own array straight back, so under the deletion the in-place scaling rewrites the caller's
      array: `[0., 1., 1.]` comes back `[0., 15., 15.]`.
      *"No test can kill this mutant and none should try" is false, and inverts the finding.*
      `tests/unit/test_projection.py` already fed a distinguishing input — `out[0]/FLOOR` is 15.0
      shipped against 1.0 deleted — and passed both only because `assert out[0] > 0.0` admits
      either. That is a coverage hole, not a redundancy. It is now closed by a pin whose expected
      value is derived from the test's own inputs rather than frozen.
      *The obvious form of that pin does not work,* and this is the part worth carrying: reading
      `seed.sum()` AFTER the call derives the expectation from the very corruption it exists to
      catch, so it passes under the mutant at relative error 0.0. Hoisting it above the call is
      what makes it discriminate. Both mutants now die: the item's deletion and the
      copy-preserving `np.array` rewrite.
      *"All 1123 tests" is stale* — 1137 today, and they pass with the deletion in place, which is
      exactly why the item read as settled.

- [x] `D-053` **Four anti-drift breaches in `tests/integration/test_d1_acceptance.py`.** Found by plan 7's
      machine run of the `anti-drift in test blocks` cross-cutting unit. The Stage 3 plan's Global
      Constraint says every count in it is a measurement dated 2026-09-05 — compute at run time,
      assert on structure, never on the literal. These assert literals against the gitignored
      `data/staged/` tree: `suppressed.height == 1227` and `joined.height == 1227` (`:67`, `:69`);
      a data-derived tally encoded in a test's own NAME plus the identity of the single narrow cell
      (`:84`, `:91-93`); `>= 4716`, `== 8` and `> 4000` on consecutive lines (`:100-102`); and
      `assert produced == EXPECTED_BOUNDS` (`:81`) against 14 hand-typed pairs. The last is the
      arguable one and should be argued rather than assumed — `EXPECTED_BOUNDS` is described in the
      file as derived analytically from the published margin before this engine existed, which is
      an independent oracle and the strongest form of golden, but a golden freezes its **input** and
      this one reads live gitignored data, so its cardinality-14 assertion still moves with a
      revision. Two NITs alongside: `tests/unit/test_anchor.py:174` ships the plan-level NIT
      recorded at `stage3-plan-audit.md:191-195` verbatim, and
      `src/logging_employment/reconcile/anchor.py:9` types "1,227" into a docstring where it is
      load-bearing on nothing. Not test-coverage work — these are over-tight assertions, and each
      needs a ruling on what its structural form is. Related:
      `tests/integration/test_d1_baselines.py` is plan-authored (`038c3af`) and carries one breach
      of the same family, so the fix is not confined to inherited Stage 2 code.
      → done in plan 8.

- [x] `D-054` **`tests/audit/test_ces_levels.py`'s three artifact tests skip in a clean clone.** `:534`,
      `:544` and `:556` read `data/raw/audit/ces/summary.json` through `_ces_summary()`, and `data/`
      is gitignored in its entirety, so none runs on a fresh checkout or in CI. Plan 7 Task 1
      deliberately reads the tracked `specs/findings/source-audit.md` instead, which is why its
      truth pin never skips; converting the three existing tests to the same source is the residual.
      Check the sibling audit test files for the same pattern before fixing only this one.
      → done in plan 8; the sibling sweep is plan 8 Task 7.

## 8-test-assertion-integrity — 2026-09-06

- [ ] `D-055` **`tests/audit/test_qcew_codes.py:378` reads a personal skill file outside the repo.**
      `test_period_basis_quotes_the_reference_verbatim_where_the_reference_is_readable` opens
      `~/.claude/skills/bls-data-context/references/qcew.md` and skips when it is absent, so it
      passes on this machine and would skip on every other one — CI included. Inventoried during
      plan 8 Task 7 and deliberately not fixed there: unlike its sibling at `:399`, this is not a
      gitignored-`data/` problem, and it has no tracked equivalent to convert to. The shipped
      `period_basis` sentence quotes that file, so the choice is a real one — vendor the quoted
      sentence into the repo (with its provenance, the way `tests/fixtures/qcew/README.md` records
      an extract's SHA-256), or drop the test and accept that the quotation is checked nowhere.
      Vendoring is the better default but it duplicates text whose upstream nothing re-checks, so
      it needs a ruling rather than a patch. Scope of the sweep that found it: every skip in
      `tests/audit/` was enumerated in a fresh `git clone`, not grepped; after plan 8 that
      directory has none left, and this is the site that would return if the skill file were
      removed from this machine.

- [ ] `D-056` **The other five `1,227` sites, where the count scopes a claim rather than decorating one.**
      Plan 8's R11 fixed `src/logging_employment/reconcile/anchor.py:9` only, where the number was
      load-bearing on nothing — the §5.5 dimension-matching argument reads identically with "many".
      The remaining five are not the same edit and were left rather than swept:
      `src/logging_employment/reconcile/scaling.py:11` ("`selected_upper` is null on 1,227 of 1,241
      unknown cells"), `src/logging_employment/baselines/simple.py:4`,
      `tests/unit/test_scaling.py:32` ("1,227 of 1,241 D1 cells have this shape, so this is the
      production path"), `tests/unit/test_baselines_runner.py:146` and
      `tests/unit/test_reconcile_properties.py:4`. Each uses the count to say how much of the
      window a code path covers, which is what justifies calling that path the production one — so
      deleting the number deletes the justification, and "many" is not a substitute. Inventory
      derived by `grep -rn "1,227" src/ tests/` at plan 8's completion, so it is current as of
      2026-09-06 and excludes `tests/integration/test_d1_acceptance.py`, whose two occurrences are
      historical ("the 1,227 this test used to assert"). What each needs is a ruling on whether the
      claim survives as a derived statement (recompute the share at run time) or as a dated one
      explicitly marked as measured-on-D1 — five decisions, not one rule.
      **Pointer refresh 2026-09-07:** re-running that grep after plan 9 merged, four of the five
      are still byte-exact; `tests/unit/test_baselines_runner.py:146` is now `:150`, shifted by
      plan 9's addition of the required `kind=` argument at that file's `Decline(` sites. The
      substance is unchanged — all five still carry the raw, undated count, and none acquired
      either resolution — so the item stays open with five decisions outstanding.


## unregistered-work audit — 2026-09-07

Found by a 30-agent read-only sweep run after plan 9 merged, asking two questions the per-plan
completion protocols do not: is every open item above still true of the tree, and is there
unimplemented work that reached neither this register nor a plan? All 25 then-open items were
verified individually and **none was already fixed** — no box should be ticked on that pass. The
items below are the second question's answer: work that is real, outstanding, and was recorded
nowhere.

**Sweep scope, so a later re-check knows what was and was not covered.** Covered: all nine retired
plans (status headers, deviation and skip annotations, descoping prose, checkbox state), `git log
--all` for follow-up promises, every live spec under `specs/*.md` against `src/`, the roadmap's
stage blocks, `specs/findings/stage3-plan-audit.md` reconciled finding-by-finding (35 distinct
non-nit findings; exactly one unaccounted for, recorded below), an AST call-graph over
`src/logging_employment/` for declared-but-uncalled symbols, and a per-key scan of all 44 config
keys for consumers. NOT covered: `specs/findings/` beyond a deferral-promise grep, retired specs
under `specs/completed/`, the 29 nits in the Stage 3 plan audit, and anything requiring network
access. Live roadmap stages remain out of scope per this file's header rule.

- [ ] `D-057` **§16.1's manifest MUST is unimplemented for `validate-config` and `registry verify`.**
      §16.1 says "Every command MUST write a machine-readable manifest and MUST be idempotent for
      the same inputs", and the roadmap's Stage 1 Produces line names all four Stage 1 commands as
      "each writing a machine-readable manifest". Two of the four write nothing: `validate_config`
      (`cli.py:28-38`) is `load_config` plus one `typer.echo`; `registry_verify` (`cli.py:45-59`)
      is `load_registry`/`verify` plus echoes and an exit code. Neither touches the filesystem.
      `fetch` and `build-harmonized` both fold rows into `source_manifest.parquet`. This is not a
      future stage: Stage 1 is ticked COMPLETE (2026-09-05, plan 2), plan 2 records no deviation or
      exemption for these two commands, and the repo's own reading of the MUST already convicted
      the same shape elsewhere — `specs/findings/stage3-plan-audit.md` lists "`reconcile` wrote no
      manifest, against §16.1's MUST" as a confirmed-and-fixed defect, and `cli.py:361` now quotes
      the sentence verbatim as the justification. Needs either two small writers or an explicitly
      recorded exemption for read-only check commands — but the roadmap's "each" forecloses
      assuming the latter. Related and deliberately excluded: `solve-bounds` also writes no
      manifest of its own, a weaker case because it runs inside a run directory whose
      `schema_manifest.json` is its own precondition gate.

- [ ] `D-058` **Three Stage 1 deliverables have builders in `src/` that nothing calls and no artifact on
      disk.** The roadmap marks Stage 1 COMPLETE and its Produces block names the `source_registry`
      table, "harmonized versioned dimensions per §8.6", and "the §3.1 classification memo carrying
      all four fields". All three builders exist and are unit-tested; all three are called from
      nowhere in `src/`: `registry/loader.py:21 registry_frame`, `harmonize/dimensions.py:28
      dimension_frame` (with its nine-member `DIMENSIONS` dict), and `classification.py:46
      classification_memo`. `build_harmonized` (`build.py:154-260`) writes exactly four tables —
      `qcew_monthly`, `qcew_national_size`, `cbp_state_size`, `bridge` — and
      `contracts.HarmonizedData` declares those same four, so there is no dimensions table for any
      downstream stage to read (`ls data/staged/` confirms four files). Plan 2 specified each
      function and its tests and never specified a wiring step. Needs a ruling per deliverable:
      wire it into `build_harmonized` and add it to `HarmonizedData`, or amend the roadmap's Stage
      1 Produces block to stop claiming it.

- [ ] `D-059` **`build-harmonized` writes no machine-readable manifest, and `BUILDER_VERSION` is stamped
      nowhere.** `build.py:17` defines `BUILDER_VERSION = "build_harmonized/1"` and nothing in
      `src/`, `tests/` or `scripts/` references it. The three parser versions beside it
      (`qcew.PARSER_VERSION`, `qcew_size.PARSER_VERSION`, `cbp.PARSER_VERSION`) are all stamped
      into `source_snapshot` rows via `fetching.py:132,153,183`, so the omission is specific to the
      builder. `build_harmonized_command` (`cli.py:77-92`) computes output hashes and only echoes
      them. Distinct from the item above: that one is about two commands writing nothing at all,
      this one is about a version constant that exists for stamping and stamps nothing.

- [ ] `D-060` **The CBP `EMPSZES` values-crosswalk route is dead: `discover_empszes` has no caller and
      `EMPSZES_URL` is never fetched.** `ingest/cbp.py:92 discover_empszes` implements the two
      metadata routes SRC-CBP-001 requires — the official `variables/EMPSZES.json` values
      crosswalk, falling through to the response's `EMPSZES_LABEL` column — and its docstring
      insists "The second is a different metadata route, not a fallback to hard-coded values."
      Nothing in `src/` calls it, and `EMPSZES_URL` (`cbp.py:21`) is referenced nowhere at all;
      `fetching.py:161-172` fetches `VARIABLES_URL` and `CBP_URL` only. `parse_cbp_state_size`
      reads `frame["EMPSZES_LABEL"]` directly (`cbp.py:243`), so a run only ever exercises the
      second route, and the official 44-code 2017 crosswalk Stage 0 measured — shipped as
      `tests/fixtures/cbp/empszes_2017.json` — is never consulted. Same dead-but-declared shape as
      the recorded `read_bulk_zip` item at `:661`, and unrecorded until now.

- [ ] `D-061` **`bounds.py`'s soft-row filter cites a schedule that has expired: three of the five
      `constraint_class` values have no producer.** `constraints/bounds.py:75-76` justifies
      `_hard_rows` with "Stage 3 adds CBP as `empirical_measurement`, which is when this filter
      starts doing visible work." Stage 3 shipped and added no such row — and `baselines/
      intensity.py:17-19`, written by Stage 3, states the opposite intent: "Nothing here builds a
      constraint row." Every `constraint_class=` literal in `constraints/rows.py` is one of two
      values (`public_accounting_fact` at :253,:354; `definitional_support` at :282,:305,:438,:484),
      so `empirical_measurement`, `modeling_assumption` and `sensitivity_assumption` in
      `contracts.CONSTRAINT_CLASSES` are emitted by nothing, the `is_hard` filter has never
      discriminated between two populations, and INV-005 is enforced against an empty complement.
      No remaining roadmap stage Produces a CBP `empirical_measurement` row — Stage 6 owns
      SRC-CBP-004's measurement *model*, not a constraint row — so the soft-constraint arm of
      §7.8/§9.3 currently has no home. Needs a ruling on which stage owns it, or the bounds
      docstring corrected to stop naming a stage that has passed.

- [x] `D-062` **A `stage3-plan-audit` DEFECT was only half discharged: `intensity.py`'s "MEASURED" coverage
      enumeration names two states where five take the fallback.** Task 13 `[DEFECT] plan:3235,
      plan:3366` makes two claims; the Disposition table discharges only (a), the magnitude
      figures. Claim (b) — "HI and RI are not the only states without a CBP row" — appears in no
      fixed-table row, no "Not acted on" bullet, and no item here. `baselines/intensity.py:7-15`
      still carries the header "WHAT CBP DOES AND DOES NOT COVER ON THIS WINDOW, MEASURED." and
      under it one fallback bullet naming Hawaii ('15') and Rhode Island ('44') only. The sentence
      is true in isolation and false by omission under that header: measured on `data/staged/
      cbp_state_size.parquet` at `size_code='001'`, 45-47 states publish per year, never 51, and
      the absent-and-therefore-fallback set after dropping CBP-suppressed nulls is 2017
      {10,15,32,38,44}, 2018 {15,32,38,44}, 2019-2022 {10,15,32,38,44}, 2023 {10,15,38,44}. ND
      ('38') never has a usable row at all — its only appearance, 2017, carries null employment —
      so it belongs in the never-usable class the docstring reserves for HI and RI. This is
      load-bearing: §10.8 ranks this estimator first and the roadmap names it the preferred-baseline
      slot Stage 4 fills with numbers. The fix is a derived statement — report the own/fallback
      split from the run manifest, as `historical.py:28-32` already does — not a corrected literal.
      Why it survived is recorded in this file already: the ticked plan-7 Task 18 item states its
      uncovered scope as including "`src/` docstrings beyond a targeted regex".
      **→ done 2026-09-07 (/deferred quick fix).** Took the remedy the item names rather than
      correcting the literal: the bullet no longer enumerates a state set at all. It now says
      coverage is per state-YEAR, that the missing set moves between years, that HI/RI (and ND in
      effect, via its null-employment row) are the only never-usable states, and that the
      own/fallback split is reported in `baseline_manifest.json`'s `weight_basis_counts` — the same
      rule `historical.py` follows. A docstring that names no measurement cannot go stale against
      a CBP vintage.

- [ ] `D-063` **`state_universe_report` has no caller, and a live guard's docstring delegates an obligation
      to it.** `harmonize/universe.py:18 state_universe_report` is called from nowhere in `src/`
      (five references in `tests/`). That matters more than an ordinary unused helper: its sibling
      `assert_definitional_alignment`, which IS on the build path, documents at :61-63 that it
      deliberately returns without complaint when one geography level is missing, because "the
      caller that needs a national control is the one that must notice its absence --
      `state_universe_report` reports it per month." The referral points at a function no caller
      runs, so the missing-national-row case is noticed by nobody. `identity_evaluable_months` and
      `months_with_a_complete_state_sum` — the SRC-QCEW-006 per-month facts the module says "Stage
      2 needs in order to build constraints at all" — are computed only inside tests.

- [ ] `D-064` **Four config keys govern nothing, and none is recorded as inert.** The repo's convention is
      to write inertness into the code (`matrix.py:3` "NO REAL INPUT UNTIL STAGE 6"; `rows.py:479`
      "nothing in the D1 run calls this"; `errors.py:84` "Reserved for Stage 7 and deliberately
      unraised today"). These four carry no such note, and each lands in
      `runs/*/config.resolved.yaml` and folds into the run id, so each is a claim in a run's record
      that no code backs. (1) `baselines.composite_fallback` (`config.yaml:61`, `config.py:148`) —
      `fallback.py:158 declared_fallback` always builds via `establishment_fallback`, so the key
      selects nothing; its sibling `allow_declared_composite` IS read, which makes the asymmetry a
      slip rather than a convention. This is plan-9-era code that merged after the 2026-09-06
      triage and has never been triaged. (2) `storage.immutable_raw` (`config.py:63`) —
      `store.py`'s `RawStore` gets immutability from content-addressing alone and never consults
      the flag; setting it false changes nothing. (3) `reconciliation.max_projection_iterations`
      (`config.py:130`) — unwired because its only consumers would be `kl_project` and
      `reconcile_matrix`, neither called from `src/`; both siblings ARE wired via `draws.py:91,94`.
      (4) `project.analysis_mode`'s `realtime_asof` (`config.py:37`) — validates, changes the run
      id, and every stage behaves as if `retrospective_final` were set. Stage 9 owns the *mode* as
      a future extension; what is missing is the refusal. Compare `reconciliation.general_method`,
      whose unsupported value at least has a written refusal, and `size_concept`, whose second
      value is at least read.

- [ ] `D-065` **The `network` pytest marker is registered with a promise it does not keep, and there is no
      CI at all.** `pyproject.toml:73` registers "network: hits a live source endpoint; excluded
      from the default run". No test carries `@pytest.mark.network` anywhere — the marker is
      applied zero times — and `addopts` (`pyproject.toml:71`) contains no `-m 'not network'`, so
      nothing would deselect it if one did. There is no `.github/` and no workflow file in the
      repo, so "the default run" is a bare `pytest` that excludes nothing. The `slow` marker beside
      it is applied at three sites and likewise not deselected, so `tests/integration/
      test_d1_acceptance.py` and `test_d1_baselines.py` run by default whenever `data/staged/` is
      populated. Needs a ruling on whether the marker is aspirational (delete it) or load-bearing
      (apply it and wire the deselection), and a separate one on whether this repo wants CI.

- [ ] `D-066` **The 24 pre-existing `ruff` violations in `scripts/audit/` are scoped out twice and tracked
      by no item.** The ticked `ruff I001` item at `:243` closes with "The remaining 24 (ISC004,
      TRY004, UP037, RUF100, RET501, UP047) are pre-existing and outside this item" — implying a
      home that does not exist, since no unticked item names any of those six rule codes. Plan 5
      then made the same scope-out a standing obligation ("those are out of scope for this plan and
      must be unchanged, not fixed. Confirm the count is still 24") while its own status header
      says "nothing deferred". So the count-24 invariant is held only by a retired plan file. No
      gate enforces it: `[tool.ruff]` declares no `exclude`, so `ruff check .` does cover
      `scripts/audit/`, but with no CI it runs only when a human or a plan step invokes it, and
      `interrogate` is explicitly scoped to `src/`.

- [x] `D-067` **Three QCEW code constants are declared and then bypassed by inline literals in the
      parser.** `constants.py:22-24` declares `QCEW_NATIONAL_AGGLVL = "18"`, `QCEW_STATE_AGGLVL =
      "58"` and `QCEW_ALL_SIZES_CODE = "0"`, each with its BLS title in a trailing comment. None is
      imported anywhere. The values are typed as bare literals at the two sites that need them:
      `ingest/qcew.py:271,273` for the area-type derivation, and `ingest/qcew_size.py:74` inside
      `assert_no_state_industry_size`. Every other measured code set in the same module IS imported
      (`INDUSTRY_CODE`, `QCEW_DISCLOSURE_CODES`, `STATE_AREAS`, `NATIONAL_AREA`), so this is three
      constants that lost their single source of truth rather than a deliberate style. Plan 2 lists
      all three among the constants Stage 1 was to define.
      **→ done 2026-09-07 (/deferred quick fix), and it was not purely mechanical.** Before
      substituting, each literal was mutation-tested to confirm the line was guarded. Two were:
      `qcew.py`'s `"18"` and `"58"` each kill two tests in `test_universe.py`. The third was NOT —
      changing `qcew_size.py`'s `!= "0"` to any other code left all 491 tests green, because the
      only test using a state row picks `size_code = "3"`, which is offending under the original
      AND the mutant. So the `!= "0"` EXEMPTION — the case the predicate exists to allow — was
      unpinned. `test_a_state_row_at_the_all_sizes_code_is_not_a_cross_tabulation` was added first,
      confirmed to die under the mutation, and only then were all three literals replaced.

- [x] `D-068` **The two §5 concept guards are never called, and unlike the repo's other inert seams nothing
      says so.** `harmonize/concepts.py` defines `reject_enterprise_size` (INV-010, SRC-OTH-001)
      and `reject_nonemployer_in_core_total` (SRC-OTH-004); neither is called anywhere in `src/`,
      both are exercised only by unit tests. The substance is defensible — Stage 7 owns
      "SRC-OTH-001–004 (ingest halves)" and `ingest/{susb,nonemployer}.py` do not exist, so there
      is no site to call them from. What is missing is the note: the module docstring reads
      "Concept guards that halt a run before a statistical unit is silently relabeled", describing
      behaviour no run can currently exhibit, and the roadmap's Stage 1 lists INV-010 and
      "SRC-OTH-001/004 (guards)" under "Gap closed", which reads as wired. Compare
      `errors.py:81-89`'s `NoHarvestFactorError` — same Stage-7 shape, carries the note, and is
      recorded at `:600`. One-line docstring fix, filed so it is not re-found as a live defect.
      **→ done 2026-09-07 (/deferred quick fix).** `harmonize/concepts.py`'s module docstring now
      states that neither guard is called today and that this is correct rather than a gap: both
      refuse an input from a source with no ingest module yet, Stage 7 owns those halves and is
      where the call sites appear, and until then they are reserved. Written in the same form as
      `errors.NoHarvestFactorError`, and for the reason the item gives — an uncalled guard reads as
      a gap unless it says it is waiting.

- [x] `D-069` **Stage 3 completed without the completion stamp the roadmap mandates in the spec's
      Rollout.** The roadmap's "Stage-spec stamp" section requires that on completion the stamp
      becomes authoritative: "Stage N: COMPLETE (YYYY-MM-DD) — implemented by plan <id> (path)."
      The spec's Rollout "Stage stamps" section carries exactly three pairs — Stage 0 (plan 1),
      Stage 1 (plan 2), Stage 2 (plan 3) — and then ends. Stage 3 has neither the pre-plan
      `- Roadmap: ... Stage 3` line nor the `> Stage 3: COMPLETE` stamp, though it is ticked and
      shipped 2026-09-05 via plan 4. The roadmap's Stage 3 heading also lacks the "— COMPLETE
      YYYY-MM-DD, plan N" suffix Stages 0-2 carry. Stages 4-9 having no stamp is correct — theirs
      are added at planning time. Ranked last here because the substance is not lost, only filed in
      the wrong place: the roadmap's Stage 3 block carries a SHIPPED paragraph with the date, the
      retired plan and the inherited contract changes. Remediation is a stamp, not code.
      **→ done 2026-09-07 (/deferred quick fix).** Both halves: the `- Roadmap: ... Stage 3` /
      `> Stage 3: COMPLETE (2026-09-05) — implemented by plan 4` pair now closes the spec's Rollout
      "Stage stamps" section, and the roadmap's Stage 3 heading carries the "— COMPLETE 2026-09-05,
      plan 4" suffix Stages 0-2 have. The stamp deliberately does NOT restate what Stage 3 shipped:
      that lives in the roadmap's Stage 3 block, which plan 9 has already amended once, and a
      second copy is precisely how the two would drift.

- [x] `D-070` **Two retired plans' status headers misstate their own deferral disposition.** Neither is
      missing work; both are record defects in the field this kind of audit reads first.
      (1) `specs/plans/completed/2-stage1-logging-employment-spec.md` is the only one of the nine
      with no `**Status: COMPLETE (...)**` line at all, so it is the one plan where a reader cannot
      tell from the file whether anything was deferred. It is complete — 131/131 steps ticked, exit
      criteria ticked with named witness tests, "All sixteen tasks complete, 2026-09-05", and both
      items its completion protocol assigned it are ticked here at `:63` and `:76`. Its retirement
      commit `5969bd9` narrates every exit criterion and simply never adds the header. One caveat
      that cannot be resolved from the record: the plan's deviation convention began at Task 7
      ("Deviations from Task 8 on are annotated inline"), so for Tasks 1-6 the record cannot
      distinguish "nothing raised" from "no convention to raise it under" — no commit touched this
      file between plan 1's completion and `8836ca9`, and the Tasks 1-6 commits fixed their two
      issues rather than deferring them. (2) `7-p3-test-coverage.md:3` says "five new items
      deferred"; its own completion section is titled "**Six new deferred items to append**" and
      all six landed in the `## 7-p3-test-coverage` section. The "five" is the count of SOURCE
      items plan 7 was assigned to close, collapsed into the wrong sentence.
      **→ done 2026-09-07 (/deferred quick fix).** Plan 2 now carries a status header naming the
      completion date and its deferral disposition, with a note that the header was added after
      the fact. Which execution skill ran is recorded in neither the file nor its retirement
      commit `5969bd9`, so the header does not name one rather than guessing — and the note keeps
      the caveat that the plan's deviation convention began at Task 7, so Tasks 1-6 cannot be
      distinguished between "nothing raised" and "no convention to raise it under". Plan 7's
      header now reads six with the miscount explained inline.

## 11-stage4-logging-employment-spec — 2026-09-07

- [ ] `D-071` **Wire `rolling_origin` and `cbp_size_gaps` into the harness scoring loop.**
      Both regimes are declared `feasible` in `contracts.REGIME_DISPOSITIONS` and both are
      implemented — `validate/regimes.py` ships `rolling_origin_frames` (frame truncation) and
      `cbp_size_gap_keys` / `apply_cbp_gap` (CBP state-year removal). Neither produces a
      `MaskTarget`, so `validate/harness.py::run_pseudo_suppression` never reaches them: the D1
      acceptance run reports `feasible / scored=0` for both.
      **CORRECTED 2026-09-08, twice.** (a) This used to say the two mechanisms ship "each with unit
      tests". `rolling_origin_frames` is tested (`tests/unit/test_validate_temporal_regimes.py:11`);
      the CBP pair is not. `cbp_size_gap_keys` and `apply_cbp_gap` have no test AND no caller
      anywhere in `src/`, `tests/` or `scripts/` — both halves are dead, so "implemented" means
      "defined" for that regime and wiring it is the larger of the two jobs.
      **PARTLY OVERTAKEN by plan 12 (2026-09-09); the item stays open because neither regime
      scores, which is what closes it.** Three of its premises are now stale. (i) The CBP pair has
      a test — `tests/unit/test_validate_cbp_gap.py` — and `cbp_size_gap_keys` was NONDETERMINISTIC
      when this was written, drawing a different key set on every CALL, so any wiring built on the
      old behaviour would not have reproduced. It sorts before sampling now. (ii) `rolling_origin`
      is no longer inert on the live path: `run_pseudo_suppression` runs `assert_no_future_rows` at
      each panel-derived origin and records them in the manifest as `origins_checked` (seven on
      D1). It still scores nothing. (iii) The `reason` this item credits is no longer a `{name}`
      template — each regime declares its own, and the CBP one no longer claims an entry point
      nothing calls. What remains to close is unchanged and is the hard half: decide what each
      regime SCORES. (b) This used to say
      `select_targets` returns `[]` for them. It is never called: `run_pseudo_suppression`
      short-circuits on `spec.select is None` BEFORE its `select_targets` call, because neither
      name is in `regimes._SELECTORS`. (Line pins dropped 2026-09-09 — plan 12 moved this code
      while editing this very bullet, which is how they went stale.) `select_targets`' own `return []` is latent, reachable only by a direct
      caller — so a fix aimed at `select_targets` alone would never run. The plan specified the two mechanisms (Tasks 11 and
      12) but never specified their wiring into Task 18's loop, and inventing a design during
      execution was out of scope. The harness now records an explicit `reason` on each so the
      manifest cannot read as "scored, nothing wrong", and
      `tests/integration/test_d1_validation.py::test_no_regime_reports_zero_scores_without_saying_why`
      pins that. To close: decide what each regime scores. `rolling_origin` needs a target
      selector applied to the TRUNCATED frame (the `assert_no_future_rows` guard already exists);
      `cbp_size_gaps` needs the CBP gap composed with a QCEW mask, since dropping CBP alone changes
      only `cbp_intensity`'s availability and produces no scored cell on its own.
- [ ] `D-072` **§13.7's CRPS is the harness's dominant cost, not `run_baselines`.**
      The plan's cost model (evidence §4) attributes ~30 s of a ~30.4 s replicate to
      `run_baselines`. Measured 2026-09-07 during execution, that is wrong once §13.7 is wired:
      `crps` is evaluated once per scored cell over an ensemble of the other cells' residuals, so
      it is O(n^2) per cell and O(n^3) per estimator, and `whole_seasonal_blocks` masks 291 cells.
      `validate/intervals.py::crps` was changed to the exact sorted-ensemble identity
      (`sum_i sum_j |x_i - x_j| = 2 * sum_i (2i - n + 1) * x_(i)`), which is O(n log n) and is
      pinned against the pairwise definition by
      `tests/unit/test_validate_intervals.py::test_the_closed_form_matches_the_pairwise_matrix`.
      A full three-seed run is 11:03 after that change. Still open: the per-cell leave-one-out
      rebuilds the whole ensemble each time, and the pairwise term is shift-invariant except for
      the zero clip, so an incremental form would remove another factor of n. Revisit if
      `replicates_per_regime` is raised from 3 seeds toward Appendix A's 20 replicates, where the
      plan's ~2.2 h estimate applies.
- [x] `D-073` **`validation_scores` / `validation_metrics` are written without `validate_frame`.**
      → done in plan 12 (2026-09-09). `cli.py::validate_command` now gates all THREE persisted
      validation tables — `validation_scoreboard` was ungated too, and undeclared — on both
      `validate_frame` and a new `assert_required_columns_present`.
      **The "superset" premise was FALSE and is the reason this took a schema change rather than a
      one-line gate.** Measured: 23 columns produced against 20 declared, 17 in common — so three
      DECLARED columns were produced by nothing and six produced ones were declared nowhere.
      Neither disposition offered here ("widen the loop", "narrow the frame") was correct: the
      frame gained `mask_arm`, `replicate` and `lookback_months_masked`, the schema gained the six
      provenance columns `run_baselines` already wrote, and both sets are now 26. The nullity gate
      is separate because `validate_frame` compares columns and dtypes and
      `dict[str, pl.DataType]` has no nullability slot — which is how a NULL `mask_arm` on every
      `declines` row (270 of 270 on D1) passed the schema gate it was already subject to.
- [x] `D-074` **"Preferred transparent baseline" is undefined against §10.8's rung exclusion.**
      `validate/scoreboard.py::preferred_baseline` returns the lowest-WAPE estimator that scored
      anything. On the D1 acceptance run (`runs/f03023ac9f3a`, 2026-09-07) that named
      `equal_residual` for `long_consecutive_runs` — and §10.8 deliberately leaves equal allocation
      OUT of its four-rung ordering, calling it a sanity check, because it ignores the
      establishment counts QCEW publishes for suppressed cells (`baselines/runner.py` module
      docstring, `FALLBACK_ORDER`). So Stage 4's scoreboard can name as "preferred" an estimator
      Stage 3 refuses to rank. The plan (Task 17) specifies "the best-scoring estimator that
      actually scored something" and never addresses the collision. Stage 5's §13.10 promotion gate
      compares the model against this number, so the ambiguity has to be resolved before the gate
      is applied: either restrict `preferred_baseline` to `FALLBACK_ORDER`'s members, or state
      explicitly that scoring and the production fallback ordering answer different questions and
      let the scoreboard report both. Do not resolve it silently in Stage 5.

      **→ retired 2026-09-07: `preferred_baseline` ranks §10.8's hierarchy members only, and
      `best_scoring_baseline` reports the unrestricted best beside it.** The register named two
      options; the resolution takes both, because they answer different halves of one question.
      §13.10's failure branch is "deploy the simpler method" — §10.8's hierarchy — so the gate's
      comparand MUST be an estimator that would actually ship, or the gate can block a model in
      favour of something no one would deploy. That decides which number Stage 5 reads. But §10.1
      out-scoring every rung is a finding about the DATA — it says the establishment counts QCEW
      publishes for suppressed cells are not earning their place on that regime, which is the use
      §10.1 puts equal allocation to — so it is reported rather than discarded.
      `best_scoring_baseline` gates nothing and its docstring says so.

      THE TEXTUAL BASIS IS CONVERGENCE, NOT A DEFINITION. §10.4 line 1015 calls `cbp_intensity`
      "the preferred transparent STRUCTURAL baseline" and §13.10 line 1572 says "the preferred
      transparent baseline"; the qualifier differs and §10.1 does sit under §10's "Required
      transparent baselines", so §10.4 is not a definition of §13.10's term and is not cited as
      one. What settles it is that every §10 passage bearing on eligibility disqualifies the same
      two estimators: §10.1 "Use only as a sanity check", §10.5 "a benchmark, not a preferred
      standalone estimator", §10.8's ordering, and `baselines/runner.py`'s own "it is just never
      preferred" — which was aspirational prose until this change gave it an enforcer.

      NOT `FALLBACK_ORDER`, WHICH IS THE OBVIOUS IMPLEMENTATION AND IS WRONG. Eligibility is rung
      MEMBERSHIP (`baselines/runner.py::FALLBACK_RUNGS`, with `PREFERRABLE` its union), because
      §10.8 rung 3 is "reconciled historical shares" — all five §10.3 variants — and
      `FALLBACK_ORDER` names one representative of it. Restricting to the literal four-tuple would
      rank `share_last_observed` above its own siblings, which §10.8 does not do: on D1's
      `whole_state_year_blocks`, `share_rolling_median` pools to 0.1342 against
      `share_last_observed`'s 0.1403, so the four-tuple would have named the worse of two
      estimators the hierarchy ranks equally.
      `test_a_10_3_share_variant_outside_the_four_rungs_can_still_be_preferred` is the guard
      against re-introducing that fix, and `test_every_registry_estimator_is_classified_against_10_8s_hierarchy`
      pins the whole set so a `REGISTRY` addition fails until someone places it.

      THE WITNESS THE REGISTER RECORDED WAS CONTAMINATED, and the contamination was a second
      defect. The scoreboard is one row per (regime, seed, estimator), and `preferred_baseline`
      filtered on regime alone and sorted rows — an argmin over seeds × estimators, an order
      statistic that rewards VARIANCE rather than accuracy. `equal_residual` on
      `long_consecutive_runs` scores 0.1106 / 2.0258 / 2.0452 across the three seeds: it holds
      both the best single row in the regime and the two worst. Ranking rows crowned it on one
      lucky seed. `_best` now pools across seeds weighted by `denominator` (masked cell-rows)
      before ranking, and pooled it is last of nine at 1.3939 against `cbp_intensity`'s 0.2308.
      Ties are broken by rung, because the tie is real and bit-exact rather than hypothetical:
      `establishment_proportional` and `share_same_month_prior_year` both pool to
      0.4228995374421378 on that regime, and `group_by` order would otherwise decide it.

      MEASURED, AND THE RESULT IS THAT ELIGIBILITY CHANGED NO D1 NUMBER. `run_id(cfg,
      _input_digests(cfg))` re-derives `f03023ac9f3a`, so these are current. After pooling,
      `preferred_baseline` and `best_scoring_baseline` name the SAME estimator in 9 of 9 scored
      regimes and `None` occurs in 0 of 9 — every regime has hierarchy members scoring. The
      collision the register recorded was produced entirely by the argmin. The restriction is
      therefore a coherence guarantee for §13.10 rather than a correction to this run's numbers,
      and it is still the right resolution because equal allocation's disqualification is
      STRUCTURAL, not seed-dependent: at Appendix A's 20 replicates or on a different seed set
      nothing prevents a pooled `equal_residual` from winning a regime again. Pooling did move two
      regimes on its own — `concentration_proxy` from `cbp_intensity` to `share_last_observed`,
      and `whole_state_year_blocks` from `cbp_intensity` to `share_rolling_median`.

      The cost of the choice, stated. (1) `preferred_baseline` can now return `None` where no
      hierarchy member scored; §13.10 must read that as "no comparand" rather than falling through
      to a sanity check. Reachable, but 0 of 9 on D1. (2) Stage 5 reads two functions where it read
      one, and must not gate on the wrong one — the docstrings carry that, nothing enforces it.
      (3) The pooling weight is the masked cell-row count, NOT WAPE's own denominator: WAPE is
      `sum|err| / sum|truth|` (`validate/metrics.py`) and the scoreboard does not carry
      `sum|truth|`, so this is cell-weighted pooling and not an exact pooled WAPE. Measured, the
      approximation does not bind — unweighted, cell-weighted and `n_scored`-weighted pooling pick
      the same estimator in 9 of 9 regimes, and only the row-argmin differs from all three — but an
      exact form would need `VALIDATION_METRIC_SCHEMA` to carry the truth mass. (4) §13.10 scopes
      its comparison to "primary-like masks" and `preferred_baseline` takes a REGIME; that gap is
      separate and is filed below rather than absorbed here.
- [x] `D-075` **§13.10's "on primary-like masks" scoping is unreachable from the scoreboard.**
      §13.10 gates on WAPE improvement "over the preferred transparent baseline ON PRIMARY-LIKE
      MASKS", and neither `validate/scoreboard.py::preferred_baseline` nor `best_scoring_baseline`
      takes a mask label — both take a REGIME. The label exists upstream and is dropped: INV-009's
      `suppression_type` rides every row of `validation_scores` (`harness.py::_join_truth`), and
      both metric emitters group by estimator without it, so it is absent from
      `VALIDATION_METRIC_SCHEMA`, from `validation_metrics.parquet`, and from the scoreboard. There
      is no way to ask the shipped scoreboard for a primary-like-only number.
      Today this is VACUOUSLY satisfied rather than wrong, which is why it was not caught: all
      12,530 scored rows on D1 (`runs/f03023ac9f3a`, run id re-derived 2026-09-07) carry
      `suppression_type = primary_like`, because every regime selector in `validate/regimes.py`
      emits `primary_like` targets and the sole producer of `complementary_like` —
      `validate/propensity.py::complementary_partners` — has unit tests
      (`tests/unit/test_validate_complementary.py`) and NO caller in `src/`. It is implemented and
      unwired, the same shape as the `rolling_origin` / `cbp_size_gaps` item above. The roadmap's
      Stage 4 Exit criterion "scores primary-like and complementary-like cells separately" is
      therefore met by the absence of the second label, not by the scoreboard separating anything.
      The failure is latent and silent: the first regime to emit complementary-like targets pools
      both labels into one WAPE per estimator, and §13.10 reads a mixed number while still
      reporting itself as a primary-like comparison. Nothing would raise.
      To close, decide which of two things §13.10's clause is. Either it is a REAL SPLIT — carry
      `suppression_type` into the emitters' grouping and out to the scoreboard, widening
      `VALIDATION_METRIC_SCHEMA` and giving `preferred_baseline` a mask-label argument — or it is a
      STANDING PRECONDITION, in which case the harness must assert that every scored row is
      primary-like and fail closed when one is not, rather than leaving the guarantee resting on
      which selectors happen to be wired. Do not leave it resting on that.

      **→ retired 2026-09-08: the clause is a STANDING PRECONDITION, and the harness now refuses a
      run that violates it.** `validate/scoreboard.py::assert_scored_cells_are_primary_like` runs
      on every scored frame beside `assert_declared_provenance` (`harness.py`), and `_best` refuses
      a regime whose rows span more than one `mask_arm`. Neither the metrics schema nor the
      scoreboard gained a column. (This sentence read "scored rows" until 2026-09-08, and the
      word was load-bearing: the check ran after the scoring and eligibility filters, so it did
      not fire for `preferred_baseline` — see the `CORRECTED 2026-09-08` note on the arm guard
      below.)

      WHY A PRECONDITION AND NOT §13.2 STEP 8'S SPLIT, which is the reading the item leaned toward.
      Step 3's complementary cells exist to defeat recovery by subtraction, and ON THE ARM THAT
      PRODUCES WAPE THERE IS NO SUBTRACTION TO DEFEAT: every one of the 4,716 state cells is a
      single-cell component, so a masked state total is `unbounded` with and without partners —
      already pinned by
      `tests/unit/test_validate_complementary.py::test_a_complementary_mask_changes_nothing_about_state_total_identification`,
      and a consequence of Stage 0's SRC-QCEW-006 `decline`. The arm where steps 3 and 6 do bind is
      the national-size March margin (`recover.mask_and_solve_size`), and it produces NO WAPE at
      all: the §10 baselines estimate state totals, not size classes, so its content is §13.5
      bound metrics and the exactly-recoverable rejection, not a scoring comparand. A
      complementary-like cell admitted to the scoring arm would therefore be, for scoring purposes,
      the same kind of thing as a primary-like one — it would dilute §13.10's comparand rather than
      sharpen it. The split is a real spec obligation on the national-size arm; it is not the
      question §13.10's clause asks.

      THE FAILURE IT REPLACES IS MEASURED, not argued. A frame carrying one perfect primary-like
      estimate and one doubled complementary-like estimate emits ONE wape row with no
      `suppression_type` column and a value of 0.5, where the primary-like number alone is 0.0.
      §13.10 would have read 0.5 and still reported itself as a primary-like comparison. Against
      the shipped D1 scores (`runs/f03023ac9f3a`, 12,530 rows) the guard passes; doctoring a single
      row of those 12,530 to `complementary_like` makes it refuse.

      ALSO CLOSED: the sibling silent-pooling path one level up. `mask_arm` was already a
      scoreboard column and `_best` pooled across it, so a second scoring arm would have averaged a
      state-total WAPE with a national-size one under one number — the same shape as the seed
      argmin retired above. It now raises. CORRECTED 2026-09-08 — as shipped it raised only for
      `best_scoring_baseline`. The check sat after the `PREFERRABLE` narrowing and after `n_scored
      > 0`, so `preferred_baseline` — the GATING wrapper — returned a name off a two-arm board
      whenever the second arm carried no hierarchy member, and a second arm that scored nothing
      was invisible to both. It now runs on the regime's rows before any narrowing; see Stage 4
      SHIPPED point (3) for the measurement. This path is more remote than the label path (a second
      scoring arm needs size-class baselines, which are Stage 6's), which is why it is a guard and
      not a parameter.

      The cost of the choice, stated. (1) §13.2 step 8's split remains unimplemented for the WAPE
      path. It already was; this makes the gap loud instead of silent, and the refusal message
      names the work — carry `suppression_type` into the emitters' grouping and
      `VALIDATION_METRIC_SCHEMA`, add it to the scoreboard, give `preferred_baseline` a label
      argument. (2) If complementary masking is ever wired onto the scoring arm, Stage 5's call
      gains a label argument at that point rather than being final today. (3)
      `include_complementary_like` still defaults to `true` and still gates no regime
      selection — it is an operand of the random-mask-only refusal, not inert; see the item
      below — so `config.yaml` continues to claim complementary masking that the harness
      does not perform.
      That flag is NOT touched here on purpose — but CORRECTED 2026-09-08, because the reason
      first recorded is false. This used to read "`runs.run_id` hashes the resolved config, so
      changing a `ValidationConfig` default would renumber every `runs/<id>/` and orphan
      `runs/f03023ac9f3a`". Measured: `config.yaml:74-97` pins all fourteen `ValidationConfig`
      keys, so NO default participates in the resolved config and changing one re-hashes to the
      SAME run id. What does orphan the run is REMOVING a field. The flag stays untouched because
      it names a decided question, not because touching it is expensive — which inverts the cost
      of the "delete the flags that name nothing" option below. It stays with the `include_*`
      item below, which now inherits a decided
      question rather than an open one — on the scoring arm the flag names something the harness
      must refuse, not something it should start doing.
- [x] `D-076` **Appendix A's `include_*` switches gate no regime selection.**
      → done in plan 12 (2026-09-09). The mapping was DECIDED, not guessed at: the seven flags are
      three different kinds of thing, declared in `contracts.VALIDATION_SWITCH_KINDS` and
      classified by `tests/unit/test_validation_switch_kinds.py`, which derives the switch set from
      `ValidationConfig.model_fields` so a new flag fails until it is classified. Four are regime
      switches, mapped in `contracts.REGIME_SWITCHES` and read by `run_pseudo_suppression`; two
      name INV-009 mask LABELS, exactly as this item suspected; one names a design with no
      implementation and is an operand of `_refuse_a_random_mask_only_design`, which is why that
      validator "refuses a configuration that would in fact have run every regime" — it is
      excluding the random-mask-only DESIGN, not selecting regimes. Nine of the thirteen regimes
      have no switch, so the set was never a partition and no flag was deleted. An excluded regime
      stays in the manifest with a reason naming its switch (R-S4C-12), and the switch is checked
      BEFORE the fail-closed refusal so that turning `include_vintage_comparison` ON still raises.
      Appendix A now states all three kinds. NOTE the constraint that shaped this: no field could
      be added or removed, because `runs.run_id` hashes `resolved_dict` over the whole model —
      "delete the flags that name nothing" would have orphaned every run directory.

      `ValidationConfig` declares `include_random_mask_sanity_check`, `include_primary_like`,
      `include_complementary_like`, `include_long_runs`, `include_rolling_origin`,
      `include_retrospective_smoothing` and `include_vintage_comparison` (plan Task 1), and
      `validate/harness.py::run_pseudo_suppression` iterates `contracts.REGIME_DISPOSITIONS`
      without reading any of them. Turning `include_long_runs` off still runs
      `long_consecutive_runs`. Only `include_vintage_comparison` is wired, and only in the
      fail-closed direction the plan specified: asking for regime 12 now raises rather than
      recording a disposition and continuing
      (`tests/unit/test_validate_declared_regimes.py::test_asking_for_the_vintage_regime_makes_the_harness_refuse`).
      The rest were left alone because the flag-to-regime mapping is a design decision the plan
      never made — six flags do not partition thirteen regimes, and `include_primary_like` /
      `include_complementary_like` describe MASK LABELS (INV-009) rather than regimes at all. The
      model validator that refuses a random-mask-only design reads the same flags, so today it
      refuses a configuration that would in fact have run every regime. Decide the mapping, then
      either wire it or delete the flags that name nothing.
- [x] `D-077` **The `validate` CLI runs the full REGISTRY with no estimator-subset option.**
      Task 4 added `estimators` to `run_baselines` and the plan calls it "a 5x lever"; §16.2's
      `run_pseudo_suppression` takes the sequence and `cli.py::validate_command` hardcodes
      `REGISTRY`. One CLI pass over one seed is ~3.7 minutes and the shipped three-seed run is
      11:03 (`runs/f03023ac9f3a`, 2026-09-07), so `tests/integration/test_validate_cli.py` has to
      share a single invocation across its two tests to stay affordable. An `--estimators` option,
      or a per-regime declared subset as the plan's Task 18 note suggests ("regimes declare the
      estimators they need"), would let the CLI test cover the wiring in seconds instead of
      minutes. Nothing is wrong today; the lever is simply not reachable from the command line.
      **→ retired 2026-09-07: `validate --estimators a,b` ships, and the run id carries it.**
      `baselines.runner.resolve_estimators` maps ids to `REGISTRY` members IN REGISTRY ORDER and
      refuses an unknown, repeated, or empty subset rather than narrowing silently — a filtered-out
      typo would leave a smaller subset, or an empty one whose manifest reads `scored=0`, which is
      the empty-partition-as-success this stage refuses everywhere else. The refusal runs BEFORE
      `HarmonizedData.load`, so a mistyped id costs a message and not a table load;
      `test_validate_refuses_an_unknown_estimator_before_it_reads_the_staged_layer` points
      `staged_uri` at a directory that does not exist and so pins the ORDER, not just the exit code.

      THE DESIGN DECISION, since the obvious implementation is wrong. `runs.run_id` hashes the
      resolved config, so an option that stopped at `argv` would send a one-estimator pass and a
      full one to the SAME `runs/<id>/` and overwrite one's metrics with the other's bytes under a
      single identifier — destroying exactly the byte-identity §16.1 makes checkable. The subset
      therefore reaches the id. It does so through a new keyword-only `overrides` parameter whose
      key is OMITTED when absent, rather than through a `validation.estimators` config field:
      measured, adding a field to `ValidationConfig` moved the shipped config from `f03023ac9f3a`
      to `c07d8e7d58b0` and orphaned all five directories under `runs/`, including Stage 4's
      acceptance artifact and the Stage 3 run that `solve-bounds` / `run-baselines` / `reconcile`
      gate on. `tests/unit/test_runs.py` pins the compatibility by re-deriving the pre-parameter
      payload, so a later `"overrides": null` cannot renumber the run directories by accident.
      The cost of the choice, stated: the subset is reachable only from the command line, not
      declarable in `config.yaml`. Task 18's other suggestion — "regimes declare the estimators
      they need" — is untouched and remains available.

      WHAT IT BOUGHT, measured 2026-09-07 on the D1 staged layer at one seed (9 scoring regimes,
      9 passes): 226.6 s for the full ten-estimator registry, 49.6 s for `share_last_observed`
      alone, 6.2 s for `establishment_proportional` alone, 50.2 s for the pair. Those last two
      single-estimator numbers are the controlled comparison that names the cost — identical
      `run_baselines` work, and the 43 s between them is §13.7's CRPS, which runs only for
      `metrics._INTERVAL_FAMILIES`. `tests/integration/test_validate_cli.py` now runs the pair, so
      one invocation still crosses BOTH branches of `probabilistic_metrics` and the idempotence
      test keeps covering the metric path that dominates the run. Measured back-to-back on this
      machine 2026-09-07, that module went from 7:31 to 1:38, and the whole suite now runs in
      6:41 over 1,282 tests with `slow` included. `validate/harness.py`'s module docstring
      carried the pre-CRPS cost model
      ("~30 s per replicate, essentially all of it `run_baselines`") and read
      `replicates_per_regime` as the loop's trip count when it sizes the MASK; both are corrected
      there against these measurements.

## /deferred triage — 2026-09-08

Residue of the `/deferred` pass that closed the NAICS-vintage citation item above. Not plan work
that was skipped — work the close itself uncovered.

- [ ] `D-078` **The audit script's NAICS note still reads "uncited", now that the citation exists.**
      `scripts/audit/qcew_codes.py:543-544` states "Unquoted premise, and the load-bearing one:
      QCEW does not retabulate prior reference years onto a new NAICS vintage", and that string is
      serialized into `data/raw/audit/qcew_codes/summary.json` and from there into the TRACKED
      `specs/findings/source-audit.md:3042`. Verified 2026-09-08: all three are byte-identical, so
      editing the source string alone breaks a property that currently holds. Deliberately left
      when the citation landed rather than half-done. Closing it means re-running `qcew_codes.py`
      → `assemble_finding` → `verify_extracts`, and unlike the `qcew_panel` chain the register
      calls "offline", this one is NOT: `main()` unconditionally fetches five BLS titles URLs with
      no `--offline` flag or env switch, and `record_extract` / `write_summary` both call
      `_utcnow()`, so even a no-op re-run churns `retrieved_utc` on five rows of the tracked
      `specs/findings/source-audit-extracts.csv`.
      Size: plan. Done when: the note carries the BLS citation (the quotation lives at
      `harmonize/naics.py`) and the three copies are byte-identical again — or the chain gains an
      offline path that leaves `retrieved_utc` untouched, and the note is updated through it.
- [x] `D-079` **`vintage_for_year` mislabels every reference year below 2017, against BLS's own table.**
      `harmonize/naics.py:34-36` is `return "NAICS 2022" if year >= 2022 else "NAICS 2017"`, so
      `vintage_for_year(2016)` returns "NAICS 2017" where the BLS table cited at
      `_VINTAGE_BOUNDARY_YEAR` says NAICS 2012 (and 2007-2010 says NAICS 2007). Found 2026-09-08
      by the citation search — the source that closed the premise is the same source that refutes
      the rule's tail. LATENT, not live — but **CORRECTED 2026-09-08: the reason first recorded
      here was wrong.** This used to read "`constants.py:5` pins `WINDOW_START = "2017-01"`, so no
      current input reaches the wrong branch". `WINDOW_START` is never consulted on the fetch or
      build path — it appears in `src/` only at its own definition, and `fetching.py:98` builds
      its years from `cfg.project.start_month`, which `ProjectConfig` validates for `YYYY-MM` shape
      only. The gate is a `config.yaml` value, not a code constant, so the defect was one YAML edit
      from live rather than one code change away. Note the emitted strings for 2017-2024 must not
      change: `constraints/cells.py:67` composes `naics_vintage` into `cell_id`, and five
      `contracts.py` schemas declare the column.
      Size: quick-fix. Done when: a year outside the range the repo can justify either classifies
      per BLS's published table or raises, rather than silently returning "NAICS 2017", with the
      pins at `tests/unit/test_harmonize.py:86-90` updated deliberately.
      → done 2026-09-08 (commit `41e17cf`): refuses below 2017 with
      `UnsupportedReferenceYearError` rather than classifying per BLS's table, because this
      package can NAME a pre-2017 vintage but
      cannot CONSUME one — `baselines/historical.py:103` filters the lookback on `naics_vintage`
      equality, so a third string would silently shrink every baseline window rather than fail.
      BLS's table is recorded as `_BLS_VINTAGE_ERAS` and wired only to the refusal message. Emitted
      values for 2017-2024 are unchanged and the `:86-90` pins are byte-identical, so no `cell_id`
      and no persisted fingerprint moves.
- [ ] `D-080` **`vintage_for_year`'s refusal message pins its year but not its vintage payload.**
      `tests/unit/test_harmonize.py::test_a_reference_year_below_the_naics_2017_era_fails_closed`
      asserts with `pytest.raises(UnsupportedReferenceYearError, match=str(year))`, which matches
      only the interpolated year. Demonstrated by mutation 2026-09-08: replacing
      `bls_vintage_for_year(year)` with `bls_vintage_for_year(year - 6)` at the message site makes
      2011's refusal read "NAICS 2002" where BLS says NAICS 2012, and the suite still reports
      21 passed / exit 0. The era-start assertions added in `41df95b` do NOT close this — they
      exercise `bls_vintage_for_year` in isolation and never the composed message. Found by the
      code review of `41e17cf`; triaged Minor independently by the reviewer, by the authoring
      session, and here, because the string is inert — raised, never emitted, never persisted, and
      no handler reads it (`grep "except "` over `src/`, `tests/` and `scripts/` finds no handler
      for `UnsupportedReferenceYearError`, and the CLI has no top-level
      `LoggingEmploymentError` catch). Recorded rather than fixed so the mutation is not lost.
      Size: quick-fix. Done when: an assertion inside the `pytest.raises` block pins the vintage
      alongside the year (e.g. `match=r"2011.*NAICS 2012"`), and the `year - 6` mutation reddens
      the suite.
- [ ] `D-081` **Three of `vintage_for_year`'s six call sites raise after a side effect.**
      Found by the code review of `41e17cf`, which made the function raise. In `fetching.py` the
      order per year is fetch → status check → `store.put` → `snapshot_row(...,
      vintage_for_year(year), ...)` (`:130`, `:151`, `:181`). A pre-2017 `cfg.project.start_month`
      therefore writes one blob to the immutable raw store and then raises before
      `merge_source_manifest` runs, so NO manifest rows are recorded for any year in that fetch. A
      later `build-harmonized` globs the manifest-less orphan (`build.py:133-137` fallback) and
      raises again, persistently, until someone hand-deletes from a store the design calls
      immutable. Not reachable on the shipped config, and not a defect in `41e17cf` — the raise is
      correct, the ordering predates it. Validating `window_years` once before the loop makes the
      refusal cost a message instead of an orphan.
      Size: quick-fix. Done when: `fetch_source` refuses an out-of-range window before its first
      `store.put`, with a test that asserts the store is untouched after the refusal.

## 12-stage4-harness-completion — 2026-09-09

- [ ] `D-082` **`assert_declared_provenance` does not check `mask_arm` against `MASK_ARMS`.**
      `contracts.MASK_ARMS` is the declared pair `('state_total', 'national_size')`, and
      `contracts.assert_declared_provenance` loops over five provenance columns without including
      `mask_arm` — so an invented arm string reaches `validation_scores` and `validation_metrics`
      without the fail-closed refusal every other closed set gets. Plan 12 made this reachable
      rather than theoretical: `mask_arm` is now PRODUCED on the scores frame from
      `MaskTarget.arm` (`validate/harness.py::_join_truth`) instead of being a literal at the emit
      sites, so its value now comes from data. Not deferred for difficulty — it is roughly a
      one-line addition to that loop plus a test — but because R-S4C-14 does not require it and
      plan 12's V1/V2 assert that the plan moved no number, so an unrequired widening of the
      fail-closed surface belonged outside that diff. Touches
      `src/logging_employment/contracts.py` and `tests/unit/test_contracts_validation.py`.
      Size: quick-fix. Done when: `assert_declared_provenance` refuses a `mask_arm` outside
      `MASK_ARMS`, with a test in the shape of the existing `suppression_type` refusal.
- [ ] `D-083` **`metric_name` is NULL on every `declines` metrics row.**
      Measured 2026-09-08 and still true: 70 of 70 rows on the committed golden, 270 of 270 on D1.
      Structurally identical to the `mask_arm` defect plan 12 closed — a null persisted in
      `validation_metrics` that `validate_frame` cannot see — and it was consciously RECORDED
      rather than fixed (decision 2026-09-08, in that plan's Global Constraints): the family emits
      counts rather than one named metric, and naming it would move a second column of the golden
      beyond what V3 authorised. `contracts.VALIDATION_REQUIRED_NON_NULL["validation_metrics"]`
      excludes it with that reason written down, and
      `tests/unit/test_contracts_validation.py::test_metric_name_is_not_required_and_the_reason_is_recorded`
      pins the exclusion. Touches `src/logging_employment/validate/metrics.py`,
      `src/logging_employment/contracts.py`, and regenerates
      `tests/fixtures/validation/validation_metrics_golden.parquet`.
      Size: quick-fix. Revisit if: a consumer needs to group `validation_metrics` on
      `metric_name` without special-casing the `declines` family — at which point delete that test
      and give the family names for its six counts.
- [ ] `D-084` **The CBP gap's effect is pooled, not confined to the holed state-year.**
      `apply_cbp_gap` removes one state-year, but `national_march_intensity` is a pooled ratio over
      surviving rows, so every state's shrunk intensity in that year moves. Re-measured 2026-09-09
      at `seed=1024` on D1 with the determinism fix in place: all 1,080 non-declined
      `cbp_intensity` estimates across 2017-2023 move, max |delta| 459.5 employees, identical
      across three processes. Recorded in `validate/regimes.py::cbp_size_gap_keys`'s docstring and
      deliberately not fixed — confining the effect would require handing the estimator an
      ungapped national value, which `baselines/fallback.py::resolve_intensity` does not permit.
      This matters to whoever closes the wiring item above: a regime that scores `cbp_size_gaps`
      will be scoring a perturbation of every state, not of the holed one.
      Size: design. Revisit if: `cbp_size_gaps` is wired to score, or `resolve_intensity` gains a
      way to take a caller-supplied national intensity.

## 2026-09-09 system review — 2026-09-10

Filed while amending the roadmap to what shipped. Both items are gaps the review
names but no existing item owns; the Stage 4 `Exit:` line cites them.

- [ ] `D-085` **§13.2 step 6 and §13.5's out-of-bounds rule are witnessed by tests, never enforced by the harness.**
      Stage 4's `Exit:` claimed the harness "rejects a mask whose target remains exactly
      recoverable" and that a truth outside the deterministic bounds "fails the run as a
      constraint-data bug (§13.5)". Neither happens. `is_exactly_recoverable`
      (`validate/recover.py:67`) and `mask_and_solve_size` (`:80`) have no caller anywhere in
      `src/`; `validate/harness.py` raises only `ConceptViolationError` (`:76`, `:296`), never on
      recoverability or on a bound violation. What ships instead is measurement:
      `validate/metrics.py:45,52` emit `truth_in_bound_rate` and `exact_recovery_rate` as metric
      rows, both present in `runs/f03023ac9f3a/validation_metrics.parquet`. The only executable
      witnesses are `tests/integration/test_validate_exact_recovery.py`, which calls
      `mask_and_solve_size` directly and skips unless a March with zero suppressed classes exists.
      This is not a wrong number on D1: every state cell is `unbounded` with a null
      `selected_upper`, so the bounds rule cannot fire on the state-total arm at all.
      Target: Stage 6 — the first stage with a size-class estimator and state x size cells, which
      is where both rules can first bind. Size: implementation.
      Done when: a mask whose target stays exactly recoverable is rejected (or separately
      labelled) by the harness rather than by a test, and a pseudo-hidden truth outside
      `deterministic_bounds` fails the run with a named error.

- [ ] `D-086` **Two of the four non-scoring regimes are owned by nothing.**
      Nine of the thirteen §13.3 regimes score in the D1 acceptance run (measured from
      `runs/f03023ac9f3a/validation_scoreboard.parquet`: `clustered_states_within_month`,
      `concentration_proxy`, `long_consecutive_runs`, `naics_transition`, `regional_blocks`,
      `small_cell_biased`, `structural_break`, `whole_seasonal_blocks`,
      `whole_state_year_blocks`). Four do not. `D-071` owns two of them — `rolling_origin` and
      `cbp_size_gaps` — and its closure condition is "decide what each regime scores".
      `retrospective_smoothing` and `preliminary_to_final_vintage` are the other two and are named
      by no open item: `D-076` mentions their `include_*` switches but is closed and is about the
      switches gating no selection, not about the regimes scoring nothing.
      Size: design. Revisit if: `D-071` is closed (the same "what does it score" question applies
      to these two and should be answered in the same pass), or REQ-022 is re-scoped — the review
      records that REQ-022 cannot honestly be called closed by Stage 4 while four regimes score
      nothing.

