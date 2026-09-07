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
- [x] **Stage 3 needs a substitute allocation anchor.** `SRC-QCEW-006` came back
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
- [x] **`cbp_metadata.lfo_by_year` is null for all eight window years** — the one
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
- [x] **`cbp_regime.unknown_years = [2024]`.** CBP's 2024 disclosure regime is
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

- [x] **`scripts/audit/qcew_identity.py`: two sets named by predicates that
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
- [x] **`scripts/audit/qcew_panel.py`: `emplvl_raw_nonzero_rows` uses
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
- [x] **`scripts/audit/qcew_panel.py`: `build_panel` and `main` are two independent
      call sites** of the same `build_long` → `_conform` composition. They agree
      today; nothing enforces it. Having `build_panel` return `(panel, predicates)`
      removes the seam.
      **→ done in plan 6, but not by the remedy this item proposed.** `(panel, predicates)` is
      insufficient: `main` also needs the pre-`_conform` `long` frame, because `emplvl_raw`
      exists only there and `disclosure_code_values` reads it. A `PanelBuild` NamedTuple returns
      all three and `build()` is the single composition site; `build_panel` survives as
      `build(own).panel`, so all eight existing test call sites are untouched.
- [x] **`scripts/audit/qcew_routes.py`: the multi-year bulk-disagreement branch is
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
- [x] **`html_title` exists in three byte-identical copies**
      (`cbp_metadata.py`, `bds_detail.py`, `susb_layout.py`), justified as "audit
      scripts are standalone PEP 723 files with no import between them" — true of
      script-to-script imports, but every one of them imports `_common`, which is
      the natural home. The risk is a fix to one not propagating.
      **→ done in plan 6, and the risk had already materialised.** The four executable lines are
      identical; the DOCSTRINGS are not — `susb_layout`'s had already lost the "including when
      `body` isn't HTML at all" clause the other two carry. So this repaired existing drift
      rather than preventing hypothetical drift. Now `_common.html_title`, with the corrected
      rationale recorded rather than dropped. 13 test assertions repointed.
- [x] **`scripts/audit/cbp_metadata.py`: three request sites remain unguarded by
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
- [x] **`scripts/audit/verify_extracts.py`: `enabled.setdefault(current, False)`
      types a default.** All ten Appendix A sources carry an explicit `enabled:`
      line today, so nothing false ships — but a future spec source without one
      would render `false`, indistinguishable from a spec-declared false, **with a
      test affirming it**. Fix: `bool | None` and render "not declared".
      **→ done in plan 6.** `bool | None`, and the one renderer is three-way. The affirming test
      was flipped rather than deleted — its assertion WAS the defect. Artifact-neutral, proven
      by regeneration: all ten sources declare `enabled:`, so no cell becomes "not declared".
      That left the new branch dead on today's spec, so it is pinned by its own unit test.
- [x] **`scripts/audit/verify_extracts.py`: `classification_block`'s `Raises:`
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
- [x] **`scripts/audit/verify_extracts.py`: `check_roadmap_fields`'s
      document-presence check matches a quoted key name anywhere in the document**
      rather than in the owning source's fence. Measured safe today (zero
      double-quoted `ROADMAP_FIELDS` keys appear in the hand-written notes).
      **→ done in plan 6.** Scoped to the owning source's `**findings**:` fence. The "measured
      safe" is a QUOTING CONVENTION, not a structural guarantee: zero keys appear double-quoted
      in the notes, but twelve of twenty appear there backticked. The cost is recorded in the
      code — the gate now depends on three literals the assembler emits, so renaming any of them
      breaks the gate on correct work. Verified: EXIT CRITERIA still PASS over all 20 entries.
- [x] **`specs/findings/source-audit.md`'s seam signpost has a second, weaker
      exception:** the whitespace-collapsed `> **Recorded access reason:**`
      blockquote. The extract-count exception is now named; this one is not.
      **→ done 2026-09-05 (/deferred quick fix).** Named in `assemble_finding.py`'s
      `seam_signpost` and the document regenerated — the artifact is generated, so editing the
      `.md` alone would have been reverted by the next run. The item's "whitespace-collapsed"
      premise was corrected before writing: the collapse is a no-op on both recorded reasons
      (`fia`, `tpo` carry no newline, tab or double space), so the sentence states the
      transform without asserting it changes anything. Two tests — one pins the sentence, one
      pins that it is true of the artifact.
- [ ] **Two vocabularies now ship side by side in the `ces` findings.**
      `publication_level_by_sm_state_code` and `near_miss_sm_state_codes` were
      renamed at this gate, but the six `states_with_*` counts keep their
      plan-mandated names while carrying the identical over-collection (they are
      computed over all 55 codes). `series_by_state` has the same implication and no
      ruling. **Stage 7 consumers must read `states_dc_tally`, not the six counts.**
- [x] **Two gate-work fixes ship without tests:** the `ces_levels` "sm.state codes"
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
- [x] **Repo-wide pre-existing `ruff I001` import-order noise**, untouched by this
      stage.
      **→ done 2026-09-05 (/deferred quick fix).** `ruff check --select I --fix` over
      `scripts/audit` and `tests/audit`: all 22 I001 gone, 46 → 24 total violations with every
      other category byte-identical. `--select I` was required — a bare `--fix` also deletes
      three deliberate `# noqa: E402` markers guarding `sys.path` late imports. The remaining
      24 (ISC004, TRY004, UP037, RUF100, RET501, UP047) are pre-existing and outside this item.

## 2-stage1-logging-employment-spec — 2026-09-05

### Raised during Tasks 7–11

- [ ] **`probe_slice_boundary` probes every candidate year rather than stopping at
      the first one served.** Ascending sort makes `served[0]` and an early exit
      return the same value, so this is cost, not correctness — but Task 16's live
      run pays it as ~17 sequential `data.bls.gov` requests where ~5 would settle
      the boundary. Left as the plan specifies it; revisit if the live run is slow
      or if BLS rate-limits. The full sweep does buy one thing an early exit would
      not: a complete per-year record of what the route served that run.
- [x] **`tests/audit/` also fails `black`, not just `ruff I001`.** The existing
      repo-wide I001 item above undercounts the debt: 14 files under `tests/audit/`
      would be reformatted. `src/logging_employment/` and `tests/unit/` are clean
      under both, so a `black`/`ruff` gate can be enforced on the package today and
      on `tests/audit/` only after a dedicated sweep.
      **→ done 2026-09-05 (/deferred quick fix), with a trap the item did not name.** All 28
      black-dirty files (14 + 14) are formatted. Black takes its target from the project's
      `requires-python = ">=3.14"`, and at that target it rewrites `except (A, B):` into PEP 758
      form in `qcew_routes.py` and `forest_sources.py` — PEP 723 scripts whose own headers
      promise `>=3.12`, where the result does not parse. No test catches it: the suite runs on
      3.14. `[tool.black] target-version = ["py312"]` is now pinned in `pyproject.toml`.
- [x] **The bulk-route branch is exercised only under a synthetic boundary.**
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
- [ ] **`source_row_hash` is computed with `map_elements`,** i.e. one Python call
      per output row. Fine at the 5,430 rows one quarter produces; the full D1
      window is 32 quarters across three sources, and Task 14 rebuilds all of it
      twice to prove byte-identity. If that run is slow, this is the first thing to
      look at — `pl.concat_str(...).hash()` is not a substitute (it is not sha256
      and not stable across Polars versions), so a native replacement needs care.

### Raised during Tasks 11-16

- [ ] **`cbp_state_size` has no column for `EMP_N_F`, the only field that carries
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

- [ ] **Nothing re-derives `EMPFLAG_WITHHELD_CODES` against a post-2017 layout.**
      The table is derived from the 2017 state record layout, which is the last year
      EMPFLAG was used, so it is correct for the D1 window. A test re-derives it from
      the shipped copy of that document. If CBP is ever read outside 2017–2023, the
      derivation has no later layout to check against and an unrecognized flag will
      halt the run — the intended §18.3 behaviour, but worth knowing before the run
      halts.

### Raised during Task 16's live run

- [ ] **CBP responses are not byte-reproducible, so the immutable store cannot
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

- [ ] **`qcew_national_size` carries every industry, not just 113310.** 140,343 rows
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

- [ ] **`evidence_kind` has no column of its own.** §7.8's field list has no place for the warrant
      behind a restriction, so `constraints/rows.py` writes it into `provenance_text` behind a
      fixed `EVIDENCE_PREFIX` (`evidence_kind=`). That keeps it queryable in the persisted
      `constraint_row` table and lets §9.3's forbidden warrants be refused by name, but it is
      stringly typed: a query for assumed-threshold rows is a substring match, not a column
      predicate. Promoting it to a real column is a spec amendment to §7.8, which this plan
      deliberately did not make. Deferred by the plan itself ("Record it as a deferred item at
      completion"). Closing it means amending §7.8, adding the column to `CONSTRAINT_ROW_SCHEMA`
      in `src/logging_employment/contracts.py`, and dropping the prefix from the factory.

- [ ] **No check covers a hard row spanning two area-months with differing release vintages.**
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

- [ ] **`classify_bound_status` labels an integer interval containing no integer
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

- [ ] **The §9.7 diagnostic degrades silently on a box-shaped infeasibility.**
      `constraints/diagnostics.py` adds slack to coupling rows only, so a component made
      infeasible by its column bounds alone (a malformed class band with `n*lower > n*upper`)
      reports `minimum slack: 0`, `irreducible infeasible subsystem: unavailable` and `candidate
      conflicts: none detected` -- a report that reads "nothing is wrong" as the final message of
      a halted run. Unreachable through the shipped builders, which derive both endpoints from
      the same published establishment count. Closing it means giving the minimum-slack model
      slack variables on the column bounds too, and adding a diagnostics test for the box shape.

- [ ] **`rank._shape_key` formats the matrix at `precision=12`.** Two equality matrices differing
      past the twelfth decimal share a CON-005 cache key, so the second component reports the
      first's rank. Every hard coefficient this stage emits is +/-1, so it cannot bite today. It
      becomes reachable if a later stage introduces fractional hard coefficients (a share, a
      deflator). Fix is `matrix.tobytes()` plus shape rather than `np.array2string`. Related:
      `rank.numerical_rank_of` passes `rank_tolerance` to `np.linalg.matrix_rank` as an
      *absolute* singular-value threshold, which is equally fine at +/-1 and equally brittle if
      magnitudes grow.

- [x] **`solve_bounds` rescans the frames once per component and once per row.**
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

- [ ] **`exactly_identified` and `integer_exactly_identified` never disagree.**
      `classify_bound_status` assigns both the same value on the integer branch, so two columns of
      `deterministic_bounds` carry one column's information. §7.10 gives field names without
      definitions, and the agreement is *correct* when the MILP ran (`selected_*` are then the
      integer optima) -- but if the two are meant to differ, §7.10 has to say how first.

- [x] **`cli._constraints_dir` derives §6.2's path instead of reading a config key.**
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

- [x] **`MAX_SCALE_RATIO = 100.0` is an originated tripwire with no spec warrant.**
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

- [x] **§10.3's fallback scales by the DISCLOSED intensity; §10.4's uses the NATIONAL one.**
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

- [ ] **`disclosed_intensity` reads the partition from the context while the residual comes from
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

- [ ] **The `general_method` guard lives at the CLI, not in the reconciliation layer.**
      `require_supported_method` is exported from `reconcile.projection` but is called only where
      config is read. `reconcile_matrix` takes no config argument, so Stage 6 must call the guard
      itself when it wires the matrix path — nothing in the layer forces it to.

- [x] **`kl_project` returns silently on an infeasible bounded system.**
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

- [x] **The three provenance enums are declared but never enforced.**
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

- [x] **`integerize` has three bound-handling gaps, all latent on D1 and all live in Stage 6.**
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

- [x] **`BreakAdjustedShare` collapses to `RollingMedianShare` below four shares.**
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

- [x] **`NoHarvestFactorError` is defined and never raised.**
      `errors.py` declares it for §10.5, but `HarvestProportional` returns a `Decline` instead,
      which is the correct behaviour. Either remove the class or document it as reserved for the
      Stage 7 path that will raise it.
      **→ done 2026-09-05 (/deferred quick fix): documented as reserved, not removed.** The
      roadmap settles it — Stage 7 produces "a live harvest-proportional baseline replacing
      Stage 3's declining stub". The docstring deliberately claims no §18.3 warrant: those
      eight bullets carry no missing-harvest-factor condition, so it names Stage 7 as owning
      the halt-vs-decline decision instead.

- [x] **Task 18's property tests and four of the five cross-cutting audit units never ran.**
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

- [ ] **`emplvl_raw_nonzero_rows` now means "not a published zero", but three things still say
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

- [ ] **The QCEW bulk route has no build-side consumer, and its fetch arm is unreachable.**
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

- [ ] **`BreakAdjustedShare`'s `<4` fallback is a design choice nobody chose.** The audit's own two
      options (`specs/findings/stage3-plan-audit.md:451`): scope the docstring — done in plan 7
      Task 4 — or return `None` below a minimum segment length so the cell takes the declared §10.2
      fallback. Whoever takes it needs a new fixture: `tests/fixtures/baselines/` has only three
      cells with a history, all length 6 and all one state-08 series, so the frozen golden contains
      no `<4` cell and cannot validate the change, while a D1 run would move roughly a third of the
      own-weight cells from `OWN` to `FALLBACK`. Plan 7's
      `test_below_four_shares_the_break_adjusted_variant_is_the_rolling_median` is deliberately
      silent on intent and is the test that must change.

- [x] **`historical.py:227`'s `segment = shares[cut:] or shares` — the `or shares` arm is
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

- [x] **`projection.py:98`'s zero-seed floor is redundant with the clip at `:118`.** Deleting
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

- [x] **Four anti-drift breaches in `tests/integration/test_d1_acceptance.py`.** Found by plan 7's
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

- [x] **`tests/audit/test_ces_levels.py`'s three artifact tests skip in a clean clone.** `:534`,
      `:544` and `:556` read `data/raw/audit/ces/summary.json` through `_ces_summary()`, and `data/`
      is gitignored in its entirety, so none runs on a fresh checkout or in CI. Plan 7 Task 1
      deliberately reads the tracked `specs/findings/source-audit.md` instead, which is why its
      truth pin never skips; converting the three existing tests to the same source is the residual.
      Check the sibling audit test files for the same pattern before fixing only this one.
      → done in plan 8; the sibling sweep is plan 8 Task 7.

## 8-test-assertion-integrity — 2026-09-06

- [ ] **`tests/audit/test_qcew_codes.py:378` reads a personal skill file outside the repo.**
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

- [ ] **The other five `1,227` sites, where the count scopes a claim rather than decorating one.**
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
