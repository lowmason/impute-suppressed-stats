> For agentic workers: REQUIRED SKILL: derive-roadmap — resume via its
> reconcile step; route each unticked stage per its ROUTING line; never plan
> this document wholesale.

# logging-employment-spec — roadmap

Source spec: `specs/logging-employment-spec.md` (v0.1). Derived 2026-09-03.
Decisions D1–D4 live in the spec's Rollout note; stages cite them and never
restate them. Stage 0's finding lands in `specs/findings/source-audit.md`.

## Gap analysis

Repository state at derivation: `git ls-files` at `479c757` returns
`README.md`, `specs/logging-employment-spec.md`,
`specs/suppressed-cell-estimation.md`. No source, tests, or configuration
exist anywhere in the tree, so every row is `missing` with evidence
`none found` (whole tree searched). There are no `in-code-but-not-in-spec`
rows and no `specs/deferred_items.md`. The Note column names the stage(s)
that close the row; a split note means the row has two halves.

| Req | Verdict | Evidence | Note |
|---|---|---|---|
| REQ-001 | missing | none found | Stage 1 |
| REQ-002 | missing | none found | Stage 1 |
| REQ-003 | missing | none found | Stage 1 (config default); Stage 6 (enforced) |
| REQ-004 | missing | none found | Stage 1 |
| REQ-005 | missing | none found | Stage 1 |
| REQ-006 | missing | none found | Stage 0 (audit); Stage 1 (parser) |
| REQ-007 | missing | none found | Stage 1 (concept guard); Stage 7 (SUSB ingest, if enabled) |
| REQ-008 | missing | none found | Stage 1 |
| REQ-009 | missing | none found | Stage 2 |
| REQ-010 | missing | none found | Stage 2 |
| REQ-011 | missing | none found | Stage 2 |
| REQ-012 | missing | none found | Stage 2 (bounds table); Stage 5 (posterior_summary carries both) |
| REQ-013 | missing | none found | Stage 3 (point estimates); Stage 4 (§10.7 intervals) |
| REQ-014 | missing | none found | Stage 5 |
| REQ-015 | missing | none found | Stage 7 |
| REQ-016 | missing | none found | Stage 6 |
| REQ-017 | missing | none found | Stage 2 (constraint scope); Stage 6 (model) |
| REQ-018 | missing | none found | Stage 3 (layer); Stage 5 (applied to every draw) |
| REQ-019 | missing | none found | Stage 5 |
| REQ-020 | missing | none found | Stage 3 |
| REQ-021 | missing | none found | Stage 4 |
| REQ-022 | missing | none found | Stage 4 |
| REQ-023 | missing | none found | Stage 4 |
| REQ-024 | missing | none found | Stage 4 (scoreboard); Stage 5 (gate applied) |
| REQ-025 | missing | none found | Stage 7 |
| REQ-026 | missing | none found | Stage 2 (flags); Stage 8 (release actions) |
| REQ-027 | missing | none found | Stage 8 |
| REQ-028 | missing | none found | Stage 1 (source/run manifests); Stage 8 (full §18.1) |
| REQ-029 | missing | none found | Stage 1 (schema/regime); Stage 2 (compat/solver); Stage 5 (model); Stage 8 (governance) |
| REQ-030 | missing | none found | Stage 8 |
| INV-001 | missing | none found | Stage 2 |
| INV-002 | missing | none found | Stage 3 (layer); Stage 8 (release check) |
| INV-003 | missing | none found | Stage 1 |
| INV-004 | missing | none found | Stage 2 |
| INV-005 | missing | none found | Stage 2 |
| INV-006 | missing | none found | Stage 2 (rounding intervals); Stages 5–6 (measurement models) |
| INV-007 | missing | none found | Stage 1 (vintage dimensions); Stage 2 (compatibility status) |
| INV-008 | missing | none found | Stage 2 (feasible); Stage 5 (posterior) |
| INV-009 | missing | none found | Stage 1 (unknown by default); Stage 4 (synthetic labels only) |
| INV-010 | missing | none found | Stage 1 |
| INV-011 | missing | none found | Stage 2 (constraint); Stage 6 (model) |
| INV-012 | missing | none found | Stage 5 |
| INV-013 | missing | none found | Stage 5 |
| INV-014 | missing | none found | Stage 4 (mechanism); Stage 5 (applied) |
| INV-015 | missing | none found | Stage 8 (records all three; sourced from Stages 2, 5, 8) |
| INV-016 | missing | none found | Stage 8 |
| SRC-QCEW-001 | missing | none found | Stage 1 |
| SRC-QCEW-002 | missing | none found | Stage 1 |
| SRC-QCEW-003 | missing | none found | Stage 1 |
| SRC-QCEW-004 | missing | none found | Stage 1 |
| SRC-QCEW-005 | missing | none found | Stage 1 |
| SRC-QCEW-006 | missing | none found | Stage 1 (universe check); Stage 2 (residual cells or decline) |
| SRC-QCEW-007 | missing | none found | Stage 1 (alignment test); Stage 2 (constraint creation) |
| SRC-QSIZE-001 | missing | none found | Stage 1 |
| SRC-QSIZE-002 | missing | none found | Stage 0 (audit); Stage 1 (parser assertion) |
| SRC-QSIZE-003 | missing | none found | Stage 2 (hard-control eligibility); Stage 6 (benchmark) |
| SRC-QSIZE-004 | missing | none found | Stage 1 |
| SRC-CBP-001 | missing | none found | Stage 0 (audit); Stage 1 (parser) |
| SRC-CBP-002 | missing | none found | Stage 1 |
| SRC-CBP-003 | missing | none found | Stage 1 |
| SRC-CBP-004 | missing | none found | Stage 3 (intensity baseline); Stage 6 (measurement model) |
| SRC-CBP-005 | missing | none found | Stage 6 |
| SRC-FOR-001 | missing | none found | Stage 7 |
| SRC-FOR-002 | missing | none found | Stage 7 |
| SRC-FOR-003 | missing | none found | Stage 7 |
| SRC-FOR-004 | missing | none found | Stage 7 |
| SRC-OTH-001 | missing | none found | Stage 1 (concept guard); Stage 7 (ingest) |
| SRC-OTH-002 | missing | none found | Stage 7 |
| SRC-OTH-003 | missing | none found | Stage 7 |
| SRC-OTH-004 | missing | none found | Stage 1 (concept guard); Stage 7 (ingest) |
| SRC-OTH-005 | missing | none found | Stage 7 |
| CON-001 | missing | none found | Stage 2 |
| CON-002 | missing | none found | Stage 2 |
| CON-003 | missing | none found | Stage 2 |
| CON-004 | missing | none found | Stage 2 |
| CON-005 | missing | none found | Stage 2 |

## Stages

Order follows the spec's Phase 0→5 dependency chain and diverges in four
places, each for dependency or information order rather than value:
(1) Phase 0's empirical source audit is pulled out as Stage 0, a written
finding, because its answer (§2.2) sets Stage 6's design space and Stage 1's
parser contracts. (2) Phase 2 is split into the identification engine
(Stage 2) and reconciliation + baselines (Stage 3): each is independently
testable software and §9.1 requires the engine to be estimator-free.
(3) The pseudo-suppression harness (§13) moves ahead of the Bayesian model
(Stage 4 before Stage 5) because INV-014/REQ-024 make "beats the baselines"
the model's acceptance test, and scoring the baselines first is cheap
information. (4) Phase 5 splits into proxies + sensitivity (Stage 7, open
design) and governance + release (Stage 8, spec-determined) because their
routing differs and §14.2/§15.2 need Stage 7's sensitivity envelope.
Phase 6 is Stage 9, optional.

- [ ] Stage 0: Source dimensionality and access audit (investigation)
      Objective: Verify from fetched files what each mandatory and recommended source actually publishes for NAICS 113310 and how it is reached, so no later stage rests on an assumed dimension.
      Spec: §1.2 (last bullet), §2.2 rows 3–4, §5.1, §5.4, §8.2 SRC-QSIZE-002, §8.3 SRC-CBP-001/003, §19 Phase 0 acceptance, §21 rows TPO/FIA + optional state sources; Rollout D1, D3.
      Gap closed: REQ-006 (audit half), SRC-QSIZE-002 (audit half), SRC-CBP-001 (audit half); de-risks REQ-016 and SRC-CBP-005.
      Consumes: Empty repository; `.env` keys per Rollout D3; pilot window per D1.
      Produces: `specs/findings/source-audit.md` — per source: verified or documented access route; exact column headers and code lists observed in a fetched extract (QCEW: `agglvl_code`, `own_code`, `size_code`, `disclosure_code` values present for 113310; CBP: `EMPSZES` and `LFO` code lists per vintage 2017–2023 and the NAICS predicate name); CBP disclosure regime per reference year; which 2017–2024 quarters the §5.4 QCEW endpoint serves versus need the annual downloadable files; state×month suppression share for 113310 private ownership; the §2.2 verdict (does any QCEW file carry state × 113310 × size simultaneously?); TPO/FIA/CES access verdicts. Fetched extracts with sha256 under `data/raw/audit/<source>/`. Repo-root `.gitignore` covering `.env`.
      Exit: the finding file exists with every field above filled or marked "not obtainable — why"; `git ls-files` shows no `.env`; each extract's sha256 in the finding matches the file on disk; the §2.2 verdict is one sentence citing the extract that proves it.
      ROUTING: writing-plans

- [ ] Stage 1: Foundation, ingestion, and harmonization (Phase 0 code + Phase 1)
      Objective: Stand up the uv-managed hatchling package and produce immutable, vintage-aware QCEW, QCEW-size, and CBP tables with harmonized dimensions and explicit bridges.
      Spec: §3.1, §3.4 (contracts only), §5.5, §6, §7.1–7.5, §8.1–8.3, §8.6, §16.1 (validate-config, registry verify, fetch, build-harmonized), §17.1 rows 1–6 and 11, §17.4 rows 1–2, §17.6 (source parsing), §19 Phases 0–1; Rollout D1–D4.
      Gap closed: REQ-001, 002, 004, 005, 006 (parser), 007 (guard), 008, 028 (partial), 029 (schema/regime); INV-003, 007 (partial), 009 (partial), 010; SRC-QCEW-001–007 (006/007 test halves); SRC-QSIZE-001, 002 (assertion), 004; SRC-CBP-001 (parser), 002, 003; SRC-OTH-001/004 (guards).
      Consumes: Stage 0 finding (headers, code lists, regimes, servable years) and its extracts as fixtures; Rollout D3 `.env` via python-dotenv; Rollout D4 toolchain.
      Produces: single package `src/logging_employment/` per §6.1 with `pyproject.toml` per D4; Parquet tables `source_registry`, `source_snapshot`, `qcew_monthly` (`employment_value` null when `disclosure_code='N'`; `area_fips` kept as string), `qcew_national_size`, `cbp_state_size`, each with a schema fingerprint; harmonized dimension tables and a `bridge` table with §8.6 fields; immutable `data/raw/<source>/<retrieval_id>/` store; `source_manifest.parquet`; classification memo carrying the four REQ-001 fields; NAICS 2017→2022 crosswalk check for 113310; disclosure-regime registry keyed by CBP reference year; CLI `validate-config`, `registry verify`, `fetch --source {qcew,qcew_size,cbp}`, `build-harmonized`, each writing a manifest.
      Exit: a frozen 2017–2024 QCEW + CBP pull rebuilds byte-identical harmonized Parquet from `data/raw/` with the network disabled (§19 Phase 1); tests prove N-coded zero → null, true zero preserved, three monthly columns → three rows, unknown CBP regime → hard failure, NAICS vintage retained, enterprise-size input rejected, manifest hashes deterministic; CBP size codes come from fetched metadata rather than literals; no key value appears in any manifest.
      ROUTING: writing-plans

- [ ] Stage 2: Deterministic identification engine (Phase 2a)
      Objective: Turn harmonized tables into a sparse public-accounting constraint system and compute sharp LP/MILP bounds, rank, components, and infeasibility diagnostics for every suppressed target cell.
      Spec: §7.7–7.10, §9 (all), §16.1 (build-constraints, solve-bounds), §16.2 (`ConstraintSystem`, `build_constraint_system`, `solve_bounds`), §17.1 row 7 (constraint side), §17.2, §17.4 row 3, §17.6 (constraint matrices, LP/MILP bounds), §19 Phase 2 (engine half); Appendix A `constraints:` block.
      Gap closed: REQ-009, 010, 011, 012 (bounds), 017 (scope), 026 (flags), 029 (compat/solver); INV-001, 004, 005, 006 (rounding), 007 (status), 008 (feasible half), 011 (constraint half); SRC-QCEW-006/007 (constraint halves); SRC-QSIZE-003 (eligibility); CON-001–005.
      Consumes: Stage 1 `qcew_monthly`, `qcew_national_size`, harmonized dimensions, `bridge`, `source_snapshot`.
      Produces: `target_cell`, `constraint_row`, `constraint_coefficient`, `deterministic_bounds` Parquet with §7.7–7.10 fields (`constraint_class` enum; `is_hard` only on `public_accounting_fact` and `definitional_support`); `ConstraintSystem` protocol; `build_constraint_system(data, config) -> ConstraintSystem`; `solve_bounds(system, config) -> BoundResult` on HiGHS; `bound_status` per §7.10; component, rank, nullity record; §9.7 infeasibility diagnostic; `disclosure/flags.py` emitting `exact_reconstruction_flag` and `narrow_feasible_interval_flag`; `constraint_set_hash`; CLI `build-constraints`, `solve-bounds`.
      Exit: §17.2 property tests pass on generated toy tables (one missing child exact; two missing partial; overlapping margins identify; rounding blocks false exactness; integrality tightens; mixed vintage detected; components solve independently); an injected infeasible component halts the run with the §9.7 diagnostic; on the 2017–2024 fixture every suppressed state-month has a `bound_status` and every exact or narrow cell carries a flag.
      ROUTING: writing-plans

- [ ] Stage 3: Exact reconciliation and transparent baselines (Phase 2b)
      Objective: Ship the reconciliation layer and every required transparent baseline, each emitting coherent point estimates inside the Stage 2 feasible set.
      Spec: §10.1–10.6, §10.8, §12 (all), §16.1 (run-baselines, reconcile), §16.2 (`reconcile_draws`), §17.1 rows 8–10, §17.3, §17.4 row 4, §17.6 (baseline predictions, reconciliation), §19 Phase 2 (baseline half); Appendix A `reconciliation:` block.
      Gap closed: REQ-013 (point), 018 (layer), 020; INV-002 (layer); SRC-CBP-004 (baseline half).
      Consumes: Stage 2 `ConstraintSystem`, `deterministic_bounds`, `constraint_set_hash`; Stage 1 `qcew_monthly`, `cbp_state_size`.
      Produces: `reconcile/` — normalized residual (§12.2), bounded proportional scaling by bisection with hard failure on an infeasible residual (§12.3), KL projection into the polytope (§12.4), RAS/IPF row–column reconciliation (§12.5), balanced integerization (§12.6); `reconcile_draws(raw_draws, feasible_set, config) -> PosteriorDraws`; `Estimator` protocol; baselines equal, establishment-proportional, the five historical-share variants, CBP intensity, harvest-proportional (declares "no factor available" until Stage 7), constrained regression; `runs/<run_id>/baseline_results/`; §10.8 fallback order; CLI `run-baselines`, `reconcile`.
      Exit: §17.3 property tests pass (no-bound sum exact; every bound respected; infeasible residual fails; projection never increases violation; row and column exact; integer totals preserved; ordering-invariant); every baseline output has zero hard-constraint violations within tolerance on the 2017–2024 fixture (§13.8); the harvest-proportional baseline refuses to run without a factor rather than fabricating one.
      ROUTING: writing-plans

- [ ] Stage 4: Pseudo-suppression validation harness and baseline scoreboard
      Objective: Build the realistic pseudo-suppression generator, holdout regimes, leakage controls, and metric suite, then score every Stage 3 baseline so later models have a number to beat.
      Spec: §10.7, §13.1–13.8, §13.10 (mechanism), §15.1 item 5, §16.1 (validate), §16.2 (`run_pseudo_suppression`), §17.4 row 7; Appendix A `validation:` and `promotion:` blocks.
      Gap closed: REQ-013 (§10.7 intervals), 021, 022, 023, 024 (scoreboard); INV-009 (synthetic labels), INV-014 (mechanism).
      Consumes: Stage 3 `Estimator` protocol, baselines, `reconcile_draws`; Stage 2 bounds and system.
      Produces: `validate/` — generator per §13.2 with propensity on public predictors only, primary-like and complementary-like masks, exact-recovery rejection; every §13.3 regime; §13.4 leakage controls; §13.5–13.8 metrics; `run_pseudo_suppression(data, estimators, config) -> ValidationResult`; `validation_metrics.parquet`; empirical predictive intervals for the historical-share, CBP-intensity, and regression baselines (§10.7); a scoreboard report naming the preferred transparent baseline with WAPE and coverage per regime; CLI `validate`.
      Exit: the harness rejects a mask whose target stays exactly recoverable; a pseudo-hidden truth outside deterministic bounds fails the run (§13.5); the scoreboard covers every §13.3 regime with primary-like and complementary-like cells scored separately; rolling-origin runs contain no future-period rows (test); a random-mask-only configuration is refused as the sole design.
      ROUTING: writing-plans

- [ ] Stage 5: State-total Bayesian model (Phase 3)
      Objective: Fit the robust hierarchical state-intensity model, reconcile every joint draw, and promote it only if it beats the Stage 4 scoreboard.
      Spec: §11 intro, §11.1–11.3, §11.5, §11.11 (QCEW rows), §11.12, §11.14, §12.7, §13.10 (gate applied), §15.4, §16.1 (fit-state-model), §16.2 (`fit_state_total_model`), §17.4 rows 5–6, §17.5 (state-total rows), §19 Phase 3; §21 PPL row; Appendix A `model:` block.
      Gap closed: REQ-012 (posterior half), 014, 018 (every draw), 019, 024 (gate), 029 (model); INV-006 (measurement), 008 (posterior half), 012, 013, 014 (applied).
      Consumes: Stage 4 harness and scoreboard; Stage 3 `reconcile_draws`; Stage 2 bounds; Stage 1 `qcew_monthly`.
      Produces: `models/interfaces.py` (`ModelData`, `PosteriorDraws`, `StateModelConfig`); `models/state_total.py` with NumPyro behind the interface and a CmdStanPy slot; `fit_state_total_model(data, config) -> PosteriorDraws`; reconciled joint draws in an ArviZ-compatible store under `runs/<run_id>/posterior/` indexed by draw, chain, state, month; `posterior_summary.parquet` (§7.11) carrying both intervals; a promotion record comparing the model to the preferred baseline per §13.10; CLI `fit-state-model`.
      Exit: the §17.5 synthetic recovery test passes for state, region, seasonal, AR, and heavy-tail parameters within stated tolerances; every retained draw satisfies hard constraints within tolerance (test); the §11.14 diagnostics gate is enforced in code; the promotion record states beat or not-beat against Stage 4 numbers and the simpler method is selected when not beaten.
      ROUTING: writing-plans

- [ ] Stage 6: Annual size-composition model (Phase 4)
      Objective: Allocate reconciled state totals to March-reference size classes through a logistic-normal composition with CBP and national-QCEW measurement models.
      Spec: §3.5, §11.6–11.10, §11.11 (CBP and QCEW-size rows), §12.5, §13.1 targets 2–3, §16.1 (fit-size-model), §16.2 (`fit_size_model`), §17.1 row 7 (model side), §17.5 (size rows), §19 Phase 4.
      Gap closed: REQ-003 (enforced), 016, 017 (model); INV-011 (model half); SRC-QSIZE-003 (benchmark); SRC-CBP-004 (measurement), 005.
      Consumes: Stage 5 `PosteriorDraws` of reconciled state totals; Stage 1 `cbp_state_size`, `qcew_national_size`; Stage 3 `reconcile/matrix.py`; Stage 0 §2.2 verdict — if a QCEW file with state × 113310 × size exists, re-route this stage to brainstorming before planning.
      Produces: `models/size_composition.py`, `SizeModelData`, `SizeModelConfig`, `fit_size_model(data, config) -> PosteriorDraws`; class-support model applied to March only; state-month-size joint draws whose rows sum to state totals and whose Q1 columns reconcile to national class margins; CBP holdout validation report; draft `state_month_size.parquet` with §15.2 fields populated except the release and sensitivity columns.
      Exit: a test proves no March class bound is applied to a non-March month; every draw's rows sum to the reconciled state total (test); Q1 national class margins reconcile or the run fails with a diagnostic; the CBP holdout report exists and states the §13.1 target-3 limitation.
      ROUTING: writing-plans

- [ ] Stage 7: Proxy sources, harvest factor, and sensitivity suite (Phase 5a)
      Objective: Add TPO/FIA as correlated measurements of a latent harvest factor plus optional CES/SUSB/BDS/NES/BEA inputs, then run the full ablation and suppression-sensitivity suite.
      Spec: §5.2, §5.3, §7.6, §8.4, §8.5, §11.4, §11.11 (proxy rows), §11.13, §13.9, §19 Phase 5 (proxy and sensitivity deliverables); §21 rows TPO/FIA and optional state sources.
      Gap closed: REQ-007 (ingest), 015, 025; SRC-FOR-001–004; SRC-OTH-001–005 (ingest halves).
      Consumes: Stage 0 TPO/FIA/CES access verdicts; Stage 5 and 6 models; Stage 4 harness; Stage 3 harvest-proportional stub.
      Produces: `ingest/{tpo,fia,ces,susb,bds,nonemployer,bea}.py` feeding `proxy_observation` (§7.6); `features/harvest_factor.py`; `models/measurement.py` (§11.4); `models/suppression_sensitivity.py` (§11.13 variants); `validate/ablation.py` covering the §13.9 list; per-cell `model_sensitivity_low` and `model_sensitivity_high`; an include-or-exclude verdict per proxy; a live harvest-proportional baseline.
      Exit: TPO harvest-origin and mill-receipt variables are distinct fields (test); FIA rows carry sampling error; no annual proxy is interpolated to monthly (test); the ablation report covers every §13.9 row; a sensitivity envelope exists for every release cell; each proxy's verdict cites the Stage 4 metric that justified it.
      ROUTING: brainstorming

- [ ] Stage 8: Disclosure governance, release package, and clean-room rebuild (Phase 5b)
      Objective: Gate every cell through disclosure review, emit the nine release tables under the required label, and prove a clean environment reproduces the release from its manifests.
      Spec: §7.11 (final form), §7.12, §14 (all), §15 (all), §16.1 (disclosure-review, publish, run-all), §17.4 row 8, §17.6 (release schemas), §18 (all), §19 Phase 5 (governance deliverables), Appendix B; §21 rows disclosure thresholds and promotion thresholds; Appendix A `disclosure:` block.
      Gap closed: REQ-026 (actions), 027, 028 (full), 029 (governance), 030; INV-002 (release), 015, 016.
      Consumes: Everything shipped through Stage 7; Stage 2 flags; Stage 7 sensitivity envelope; Stage 5–6 posterior summaries.
      Produces: `disclosure/{policy,review}.py`; `disclosure_decision` table (§7.12 with the `release_action` enum); §14.3 concentration metric; the three-status record of §14.1; `publish/` emitting all nine §15.1 artifacts with §15.2 fields and §15.3 levels; the §14.5 label on every modeled record; `run_manifest.json` per §18.1; §18.2 monitoring metrics; CLI `disclosure-review`, `publish`, `run-all`.
      Exit: an exactly-reconstructed N-flagged cell cannot reach `release_observed` or `release_model_estimate` without a recorded reviewer decision (test); every §14.2 trigger routes to review (tests); `run-all` on a fresh clone holding only `data/raw/` and the manifest reproduces the output hashes (Appendix B, REQ-030); all nine release files validate against their schemas.
      ROUTING: writing-plans

- [ ] Stage 9 (optional): Phase 6 extensions
      Objective: Choose and design any §19 Phase 6 extension the owner wants once the core system is released.
      Spec: §3.4 `realtime_asof`, §3.5 `contemporaneous_modeled`, §19 Phase 6.
      Gap closed: none — no numbered requirement mandates Phase 6.
      Consumes: A released Stage 8 system; the owner's choice of extension.
      Produces: One sub-project spec per chosen extension, each with its own validation and disclosure review.
      Exit: A spec exists for each chosen extension, or this stage is marked "declined" with a date.
      ROUTING: brainstorming

## Stage-spec stamp

All stages share `specs/logging-employment-spec.md`; its Rollout note carries
one stamp line per routed stage, which writing-plans copies verbatim into the
stage plan's header:

> Roadmap: specs/logging-employment-spec-roadmap.md, Stage N — on plan
> completion, tick the stage and re-validate later stages against what
> shipped.

On completion the stamp becomes authoritative:

> Stage N: COMPLETE (YYYY-MM-DD) — implemented by plan <id> (path).
> Next: resume the roadmap.

## Completion

Retire this roadmap only after re-running the gap rubric over the
accumulated system with evidence per row (implementing stage and plan,
`> Deviation:` notes, `specs/deferred_items.md` entries) and confirming the
Appendix B scenario runs end-to-end from a clean environment. Unmet rows
exit only as a new stage or a written deferral with its reason. Optional
independent check: describe-critique-methodology Describe mode on the shipped
system, diffed against §9–§14.
