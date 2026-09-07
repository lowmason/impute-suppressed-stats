> For agentic workers: REQUIRED SKILL: derive-roadmap — resume via its
> reconcile step; route each unticked stage per its ROUTING line; never plan
> this document wholesale.

# logging-employment-spec — roadmap

Source spec: `specs/logging-employment-spec.md` (v0.1). Derived 2026-09-03 from
the spec **and** the three research reviews
(`specs/logging-employment-research-{chatgpt,copilot,gemini}.md.md`), which the
spec synthesizes. Supersedes the roadmap committed at `211bc03`, which was
derived at `479c757` before the reviews were in the repository.

Decisions D1–D6 live in the spec's Rollout note; stages cite them and never
restate them. Stage 0's finding lands in `specs/findings/source-audit.md`.

## Gap analysis

Repository state at derivation: `git ls-files` returns `README.md`,
`.gitignore`, the four spec/review documents, and the superseded roadmap. No
source, tests, configuration, or data exist anywhere in the tree. Every one of
the 76 numbered requirements is therefore `missing` with evidence `none found`
(whole tree searched). There are **no `in-code-but-not-in-spec` rows**, and
`specs/deferred_items.md` did not exist at derivation — this derivation created
it carrying the single deferral below. One row is `out-of-scope-deferred`
rather than staged: see SRC-OTH-005.

The Note column carries the whole value of this table: it maps each row to the
stage that discharges it. A split note means the row has two or more halves.

| Req | Verdict | Evidence | Note |
|---|---|---|---|
| REQ-001 | missing | none found | Stage 1 |
| REQ-002 | missing | none found | Stage 1 (universe filter); Stage 2 (`target_cell`) |
| REQ-003 | missing | none found | Stage 1 (config default); Stage 6 (enforced) |
| REQ-004 | missing | none found | Stage 1 |
| REQ-005 | missing | none found | Stage 1 |
| REQ-006 | missing | none found | Stage 0 (audit); Stage 1 (parser) |
| REQ-007 | missing | none found | Stage 1 (concept guard); Stage 7 (SUSB ingest) |
| REQ-008 | missing | none found | Stage 1 |
| REQ-009 | missing | none found | Stage 2 |
| REQ-010 | missing | none found | Stage 2 |
| REQ-011 | missing | none found | Stage 2 |
| REQ-012 | missing | none found | Stage 2 (bounds table); Stage 5 (`posterior_summary` carries both) |
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
| SRC-QCEW-006 | missing | none found | **Stage 0 (branch verdict)**; Stage 1 (universe check); Stage 2 (residual cells or decline) |
| SRC-QCEW-007 | missing | none found | **Stage 0 (alignment test)**; Stage 1 (test in code); Stage 2 (constraint creation) |
| SRC-QSIZE-001 | missing | none found | Stage 1 |
| SRC-QSIZE-002 | missing | none found | Stage 0 (confirm on extract); Stage 1 (parser assertion) |
| SRC-QSIZE-003 | missing | none found | Stage 2 (hard-control eligibility); Stage 6 (benchmark) |
| SRC-QSIZE-004 | missing | none found | Stage 1 |
| SRC-CBP-001 | missing | none found | Stage 0 (keyed enumeration); Stage 1 (parser) |
| SRC-CBP-002 | missing | none found | Stage 1 |
| SRC-CBP-003 | missing | none found | Stage 0 (regime per year); Stage 1 (fail closed) |
| SRC-CBP-004 | missing | none found | Stage 3 (intensity baseline); Stage 6 (measurement model) |
| SRC-CBP-005 | missing | none found | Stage 6 |
| SRC-FOR-001 | missing | none found | Stage 0 (access verdict); Stage 7 |
| SRC-FOR-002 | missing | none found | Stage 0 (access verdict); Stage 7 |
| SRC-FOR-003 | missing | none found | Stage 0 (access verdict); Stage 7 |
| SRC-FOR-004 | missing | none found | Stage 7 |
| SRC-OTH-001 | missing | none found | Stage 1 (concept guard); Stage 7 (ingest) |
| SRC-OTH-002 | missing | none found | Stage 0 (BDS detail discovery); Stage 7 |
| SRC-OTH-003 | missing | none found | Stage 0 (per-state publication level); Stage 7 |
| SRC-OTH-004 | missing | none found | Stage 1 (concept guard); Stage 7 (ingest) |
| SRC-OTH-005 | out-of-scope-deferred | none found | **No stage.** BEA `SAEMP25`/`SAEMP27` were discontinued 2024-09-27 (ChatGPT review), so no current detailed state-industry BEA table exists to bridge. Deferred per §6 with that reason; §5.3 already marks BEA optional and Appendix A ships `bea.enabled: false`. |
| CON-001 | missing | none found | Stage 2 |
| CON-002 | missing | none found | Stage 2 |
| CON-003 | missing | none found | Stage 2 |
| CON-004 | missing | none found | Stage 2 |
| CON-005 | missing | none found | Stage 2 |

### What the reviews changed

The reviews **confirm** the spec's §19 Phase 0→5 dependency chain rather than
redrawing it. All three independently place the deterministic feasibility
engine and the transparent baselines *before* the Bayesian model, and the
ChatGPT review states the rationale directly: an early finding that public
constraints or the CBP/QCEW intensity baseline are already adequate removes the
need for the complex model. Agreement across three independent reviews and the
spec's own phasing is the strongest available signal that the partition is
right, so the stage boundaries below track §19.

Sequencing diverges from §19 in four places, each for dependency or
information order and never for the reviews' or the spec's value ranking:

1. Phase 0's empirical source work becomes **Stage 0**, an investigation whose
   exit is a written finding. Its answers set Stage 1's parser contracts,
   Stage 2's available margins, and Stage 6's design space.
2. Phase 2 splits into the identification engine (**Stage 2**) and
   reconciliation plus baselines (**Stage 3**). §9.1 requires the engine to be
   estimator-free, and each half is independently testable software.
3. The pseudo-suppression harness (§13) moves **ahead** of the Bayesian model
   (Stage 4 before Stage 5). INV-014/REQ-024 make "beats the transparent
   baselines" the model's acceptance test, so scoring the baselines first is
   cheap information that can end the roadmap early.
4. Phase 5 splits into proxies plus sensitivity (**Stage 7**, open design) and
   governance plus release (**Stage 8**, spec-determined), because their
   ROUTING differs and §14.2/§15.2 consume Stage 7's sensitivity envelope.

Content changes the reviews forced, relative to the spec read alone:

- **QCEW access is two routes, not one.** §5.4's seed endpoint serves only the
  most recent five reference years, so the D1 window needs the downloadable
  bulk files for its early years. Stage 0 measures the boundary; Stage 1 builds
  both routes (D5).
- **Stage 0's audit shrinks in two places and grows in six.** Two reviews
  independently document QCEW-size dimensionality (national × six-digit *or*
  state × sector) and CBP's simultaneous state × six-digit × `EMPSZES`, so
  those move from open verdicts to extract-confirmations. Newly added, because
  every review flags them unresolved: the QCEW year boundary above; a keyed CBP
  execution enumerating `EMPSZES`/`LFO` per vintage; the CBP disclosure regime
  per reference year after the Commerce order; the QCEW code/title files for
  aggregation level, ownership, size, and disclosure; the national-identity
  branch verdict below; and the SUSB, TPO, FIA, and CES access verdicts.
- **The national-identity verdict is promoted to a partition dependency.**
  SRC-QCEW-006 pre-specifies three branches — enforce, add residual cells, or
  decline — and §3.2 forbids imposing a national control on a state universe
  missing national components while D1 fixes that universe at states + D.C.
  Stage 3's entire baseline family allocates a residual against a national
  total (§10.1–10.6, §12.2), so the branch is named in Stage 3's `Consumes`.
- **CES is an industry-aligned predictor, not a broader-industry proxy.**
  NAICS `1133 → 11331 → 113310` verified against the local code tables: 113310
  is the only six-digit industry under 1133 in both the 2017 and 2022 vintages,
  and both concordances mark it `1:1` with no content change. A state CES series
  published at 1133 therefore covers exactly the target industry. §5.2's
  "never an exact QCEW identity" still binds — but on the statistical concept
  (annually QCEW-benchmarked sample estimate, in thousands, revised), not on
  industry mismatch. A series published only at 113 or at the Mining-and-Logging
  supersector *is* broader; 113 has two other children.
- **Three review recommendations contradict binding spec resolutions and are
  now guarded by negative exit criteria**, because the reviews sit in `specs/`
  where a later implementer will read them. The Gemini review derives a hard
  MILP bound from an asserted "80/3" disclosure threshold (its §7 item 5) and
  recommends injecting artificial privacy variance (its §12); §9.3 and §2.2
  forbid both. The same review makes Dirichlet-multinomial the latent
  composition process; §2.2 resolves the latent process to logistic-normal with
  multinomial or Dirichlet-multinomial permitted only as observation models.
  Stages 2, 6, and 8 each carry an exit criterion that fails if the forbidden
  form is reachable.
- **BEA drops out** (SRC-OTH-005 above). REQ-007's SUSB half and §13.9's CES
  ablation stay in Stage 7.

## Stages

- [x] Stage 0: Source access, dimensionality, and national-identity audit (investigation) — COMPLETE 2026-09-04, plan 1
      Objective: Establish from fetched files what each source actually publishes for 113310 over the D1 window, by which route, and which SRC-QCEW-006 branch the national identity takes — so no later stage rests on an assumed dimension or an unavailable margin.
      Spec: §1.2 (final bullet), §2.2 rows 1–4, §5.1–5.4, §8.1 SRC-QCEW-006/007, §8.2 SRC-QSIZE-002, §8.3 SRC-CBP-001/003, §8.5 SRC-OTH-002/003, §19 Phase 0 acceptance, §21 rows (geography universe, TPO/FIA coverage, optional state sources); Rollout D1, D3, D5.
      Gap closed: audit halves of REQ-006, SRC-QSIZE-002, SRC-CBP-001, SRC-CBP-003, SRC-OTH-002, SRC-OTH-003, SRC-FOR-001/002/003; the branch verdict for SRC-QCEW-006 and SRC-QCEW-007. De-risks REQ-015, REQ-016, SRC-CBP-005.
      Consumes: Empty repository; `.env` credentials per D3; pilot window per D1; dual-route mandate per D5.
      Produces: `specs/findings/source-audit.md` recording, per source, a `verified` or `documented` access route plus the observed contents of a fetched extract — for QCEW, the earliest reference year the §5.4 slice endpoint serves and the bulk-file route covering the remainder of the D1 window, together with the code/title lists actually present for `agglvl_code`, `own_code`, `size_code`, and `disclosure_code` on 113310 rows; for QCEW size, whether any file carries state × 113310 × size simultaneously; for CBP, the `EMPSZES` and `LFO` code lists and the NAICS predicate name per vintage across the window, and the disclosure regime per reference year; the state × month suppression share for 113310 private ownership; per-state CES publication level (1133, 113, or supersector); BDS finest industry detail; SUSB detailed-sizes file layout; and TPO and FIA access verdicts including FIA `/fullreport` parameters. Separately, the SRC-QCEW-006 branch verdict: quarter by quarter over the window, whether national 113310 private employment equals the sum of state rows, with the geography-universe explanation (national coverage beyond states + D.C.) tested before suppression is blamed. Fetched extracts stored with sha256 under `data/raw/audit/<source>/`. Repo-root `.gitignore` covering `.env`.
      Exit: the finding file exists with every field above either filled or marked "not obtainable — why"; the SRC-QCEW-006 branch verdict names exactly one of enforce, residual-cells, or decline, in one sentence, citing the per-quarter comparison that produced it and stating whether the geography universe accounts for any gap; the QCEW year boundary is stated as a reference year, not an approximation; `git ls-files` shows no `.env`; every extract's recorded sha256 matches the file on disk.
      ROUTING: writing-plans

- [x] Stage 1: Foundation, ingestion, and harmonization (Phase 0 code + Phase 1) — COMPLETE 2026-09-05, plan 2
      Objective: Stand up the uv-managed hatchling package and produce immutable, vintage-aware QCEW, QCEW-size, and CBP tables with harmonized dimensions and explicit bridges.
      Spec: §3.1, §3.4 (contracts only), §5.5, §6, §7.1–7.5, §8.1–8.3, §8.6, §16.1 (`validate-config`, `registry verify`, `fetch`, `build-harmonized`), §17.1 rows 1–6 and 11, §17.4 rows 1–2, §17.6 (source parsing), §19 Phases 0–1; Rollout D1–D5.
      Gap closed: REQ-001, REQ-002 (universe filter), REQ-003 (config default), REQ-004, REQ-005, REQ-006 (parser), REQ-007 (guard), REQ-008, REQ-028 (source/run manifests), REQ-029 (schema/regime); INV-003, INV-007 (dimensions), INV-009 (default unknown), INV-010; SRC-QCEW-001–005, SRC-QCEW-006/007 (in-code tests); SRC-QSIZE-001, SRC-QSIZE-002 (assertion), SRC-QSIZE-004; SRC-CBP-001 (parser), SRC-CBP-002, SRC-CBP-003 (fail closed); SRC-OTH-001/004 (guards).
      Consumes: Stage 0's finding — access routes, year boundary, code/title lists, CBP predicate names and regimes — and its extracts as test fixtures; `.env` via python-dotenv per D3; toolchain per D4; dual-route mandate per D5.
      Produces: one installable package `src/logging_employment/` laid out per §6.1 with a `pyproject.toml` per D4; Parquet tables `source_registry`, `source_snapshot`, `qcew_monthly`, `qcew_national_size`, and `cbp_state_size` with the §7.1–7.5 fields and a schema fingerprint each; both QCEW acquisition routes behind one ingest interface, selected by reference year from Stage 0's boundary; harmonized versioned dimensions per §8.6 and a `bridge` table carrying the §8.6 fields; an immutable content-addressed `data/raw/<source>/<retrieval_id>/` store; `source_manifest.parquet`; the §3.1 classification memo carrying all four fields; a mechanical NAICS crosswalk test for 113310 across the window's vintages; a disclosure-regime registry keyed by CBP reference year; CLI `validate-config`, `registry verify`, `fetch --source {qcew,qcew_size,cbp}`, and `build-harmonized`, each writing a machine-readable manifest and idempotent for identical inputs. Later stages may assume every downstream stage reads only harmonized Parquet, never a source endpoint.
      Exit: a frozen pull covering the full D1 window rebuilds byte-identical harmonized Parquet from `data/raw/` with the network disabled (§19 Phase 1); tests prove an `N`-coded zero parses to null, a metadata-supported true zero is preserved, three monthly employment columns expand to three rows, an unknown CBP disclosure regime halts the run, source NAICS vintage survives ingestion, enterprise-size input is rejected as an establishment-size measurement, and manifest hashes are deterministic; CBP size codes come from fetched metadata rather than literals; `area_fips` round-trips as a string with leading zeros intact; no credential value appears in any manifest.
      ROUTING: writing-plans

- [x] Stage 2: Deterministic identification engine (Phase 2a) — COMPLETE 2026-09-05, plan 3
      Objective: Turn harmonized tables into a sparse public-accounting constraint system and compute sharp LP/MILP bounds, rank, components, and infeasibility diagnostics for every suppressed target cell.
      Spec: §7.7–7.10, §9 (all), §16.1 (`build-constraints`, `solve-bounds`), §16.2 (`ConstraintSystem`, `build_constraint_system`, `solve_bounds`), §17.1 row 7 (constraint side), §17.2, §17.4 row 3, §17.6 (constraint matrices, LP/MILP bounds), §19 Phase 2 (engine half); Appendix A `constraints:` block.
      Gap closed: REQ-002 (`target_cell`), REQ-009, REQ-010, REQ-011, REQ-012 (bounds table), REQ-017 (constraint scope), REQ-026 (flags), REQ-029 (compat/solver); INV-001, INV-004, INV-005, INV-006 (rounding intervals), INV-007 (compatibility status), INV-008 (feasible half), INV-011 (constraint half); SRC-QCEW-006/007 (constraint halves); SRC-QSIZE-003 (hard-control eligibility); CON-001–005.
      Consumes: Stage 1's `qcew_monthly`, `qcew_national_size`, harmonized dimensions, `bridge`, `source_snapshot`; Stage 0's SRC-QCEW-006 branch verdict, which determines whether a national margin, residual cells, or neither enters the system.
      Produces: `target_cell`, `constraint_row`, `constraint_coefficient`, and `deterministic_bounds` Parquet with the §7.7–7.10 fields, the §7.8 `constraint_class` enum, and `is_hard=true` reachable only from `public_accounting_fact` and `definitional_support`; the `ConstraintSystem` protocol and `build_constraint_system`/`solve_bounds` signatures of §16.2 on HiGHS; a `bound_status` per §7.10 for every cell; component, rank, and nullity records with the §9.4 provenance; the §9.7 infeasibility diagnostic; `disclosure/flags.py` emitting `exact_reconstruction_flag` and `narrow_feasible_interval_flag`; a `constraint_set_hash`; CLI `build-constraints` and `solve-bounds`.
      Exit: the §17.2 property tests pass on generated toy tables — parent equals children, one missing child exactly recoverable, two only partially identified under nonnegativity, overlapping margins identifying despite two suppressions per row, rounding intervals blocking false exact recovery, integrality tightening bounds, mixed-vintage conflict detected, components solving independently; an injected infeasible component halts the run with the §9.7 diagnostic rather than silently relaxing; on the D1 fixture every suppressed state-month carries a `bound_status` and every exact or narrow cell carries a flag; **and a test proves no constraint derived from an assumed disclosure threshold can be admitted with `is_hard=true`** (§9.3 final bullets — the Gemini review's §7 item 5 is the concrete form to reject).
      ROUTING: writing-plans

- [x] Stage 3: Exact reconciliation and transparent baselines (Phase 2b) — COMPLETE 2026-09-05, plan 4
      Objective: Ship the reconciliation layer and every required transparent baseline, each emitting coherent point estimates inside the Stage 2 feasible set.
      Spec: §10.1–10.6, §10.8, §12 (all), §16.1 (`run-baselines`, `reconcile`), §16.2 (`reconcile_draws`), §17.1 rows 8–10, §17.3, §17.4 row 4, §17.6 (baseline predictions, reconciliation), §19 Phase 2 (baseline half); Appendix A `reconciliation:` block.
      Gap closed: REQ-013 (point estimates), REQ-018 (layer), REQ-020; INV-002 (layer); SRC-CBP-004 (intensity baseline).
      Consumes: Stage 2's `ConstraintSystem`, `deterministic_bounds`, and `constraint_set_hash`; Stage 1's `qcew_monthly` and `cbp_state_size`; **Stage 0's SRC-QCEW-006 branch verdict — every §10.1–10.6 baseline allocates a residual against a national total, so a `decline` verdict changes this stage's allocation target and its plan must state the substitute anchor before any baseline is written.**
      Produces: `reconcile/` implementing the §12.2 normalized-residual fast path, §12.3 bounded proportional scaling by bisection with hard failure when summed bounds exclude the residual, §12.4 KL projection into the polytope, §12.5 row–column matrix reconciliation, and §12.6 balanced integerization; `reconcile_draws` per §16.2; an `Estimator` protocol; the baselines of §10.1, §10.2, all five §10.3 historical-share variants, §10.4 CBP intensity, §10.5 harvest-proportional, and §10.6 constrained regression; `runs/<run_id>/baseline_results/`; the §10.8 fallback ordering. Later stages may assume a single reconciliation entry point every model draw passes through, and a named preferred transparent baseline slot that Stage 4 fills with numbers.
      Exit: the §17.3 property tests pass on random feasible inputs — no-bound scaling sums exactly to the residual, bounded scaling respects every bound, an infeasible residual fails rather than approximating, generalized projection never increases constraint violation, row and column reconciliation is exact, integerization preserves required totals, and solver tolerance or cell ordering does not shift results materially; every baseline output has zero hard-constraint violations within tolerance on the D1 fixture (§13.8); integerization is never applied cell-by-cell independently (§12.6); the harvest-proportional baseline declines to run without a harvest factor rather than fabricating one.
      ROUTING: writing-plans
      SHIPPED (2026-09-05, plan 4 retired): all of the above, with four contract changes later stages inherit. (1) Both arms of a composite MUST be in employees — `baselines.interfaces.compose` raises `WeightDomainError` when the two arms' medians differ by more than 100x, because `allocate` normalizes the union and the larger-scaled arm otherwise absorbs the residual. SUPERSEDED by plan 9 (2026-09-07), and a later stage inherits the REPLACEMENT, not this: the employees rule stands but is now carried by the TYPE — both arms are `baselines.interfaces.EmployeeWeights`, a frozen wrapper `compose` refuses to accept a plain dict in place of, raising `ConceptViolationError`. The magnitude guard is deleted, and no threshold replaces it: measured on D1 the honest arm-ratio range is 0.947-4.996 while substituting a raw establishment count for the scaled fallback gives 0.182-0.811 for the share family and 0.160-0.316 for §10.4 — the bug sits INSIDE the honest range, so a caller wraps its arms rather than sizing them. See §10.9 and `specs/completed/estimator-composition.md` R-COMP-1 to R-COMP-3. (2) `kl_project` refuses non-0/1 margin rows and `reconcile_matrix` raises rather than returning non-converged margins, so a caller must build indicator rows and handle the raise. (3) `require_supported_method` is NOT called inside the reconciliation layer — `reconcile_matrix` takes no config, so whoever wires the §12.4/§12.5 path owns the `general_method` guard. (4) `weight_basis_counts` in `baseline_manifest.json` is nested per estimator, and `preferred_estimator_by_month` exists alongside the window scalar, which is a summary only. Measured on D1: 12,270 baseline rows over 10 estimators and 96 months, 1,374 declines (§10.5 in all 96 months, §10.4 in the 12 months of 2024), max residual drift 4.5e-13, and every `cell_id` joins `deterministic_bounds`.

- [ ] Stage 4: Pseudo-suppression validation harness and baseline scoreboard
      Objective: Build the realistic pseudo-suppression generator, holdout regimes, leakage controls, and metric suite, then score every Stage 3 baseline so the Bayesian model has a published number to beat.
      Spec: §10.7, §13.1–13.8, §13.10 (mechanism), §15.1 item 5, §16.1 (`validate`), §16.2 (`run_pseudo_suppression`), §17.4 row 7; Appendix A `validation:` and `promotion:` blocks.
      Gap closed: REQ-013 (§10.7 intervals), REQ-021, REQ-022, REQ-023, REQ-024 (scoreboard); INV-009 (synthetic labels only), INV-014 (mechanism).
      Consumes: Stage 3's `Estimator` protocol, baselines, and `reconcile_draws`; Stage 2's bounds and constraint system; Stage 0's suppression-share measurement, which sizes the mask design.
      RE-VALIDATED against Stage 3 as shipped: still routes to writing-plans, with four additions (the fourth added by plan 9). A mask that changes the partition MUST rebuild `EstimatorContext.partitions` from the same mask it hands the anchor. UPDATED by plan 9 (2026-09-07) — the two pointers this sentence used to carry are both stale: `disclosed_intensity` now lives in `baselines/fallback.py`, not `baselines.simple`, and the disagreement is no longer unenforced. It recomputes `national_residual` from the context's partition and raises `ConceptViolationError` when that disagrees with `anchor.residual` (R-COMP-8, spec §10.9). So a harness that hands an estimator a partition the anchor did not come from now FAILS CLOSED on every composing baseline instead of silently scaling the fallback off the wrong disclosed set — which makes this a Stage 4 obligation rather than a Stage 4 risk. The check witnesses the DISCLOSED side only, so `specs/deferred_items.md` keeps the item open for the harness half Stage 4 owns. Scoring must read `weight_basis_counts` per estimator, not pooled, or a composite's score is reported as a pure estimator's. And the preferred-baseline slot Stage 4 fills should use `preferred_estimator_by_month`: the window scalar names `cbp_intensity` even for the 12 months of 2024 in which it produced nothing. Added by plan 9: every declined row now carries a `decline_kind` from the closed set `by_design | data_gap | reconciliation_failure` (`contracts.DECLINE_KINDS`, in `baseline_results.parquet` beside `decline_reason` and broken out per estimator in `baseline_manifest.json`), and spec §13.8 now REQUIRES every scored comparison in §13.5-13.8 to report decline counts by kind, per method and per holdout regime, with its denominator stated — R-COMP-10, which lands on this stage and nowhere else. Grouping on `decline_reason` instead would group on a sentence that names a state fips.
      Produces: `validate/` implementing the §13.2 generator with propensity built only from public predictors, primary-like and complementary-like masking, retention of only the margins that would remain public, and rejection or separate labelling of masks whose target stays exactly recoverable; every §13.3 holdout regime; the §13.4 leakage controls; the §13.5–13.8 metric families; `run_pseudo_suppression` per §16.2; `validation_metrics.parquet`; empirical predictive intervals for at least the historical-share, CBP-intensity, and constrained-regression baselines (§10.7); and a scoreboard naming the preferred transparent baseline with its WAPE and coverage per regime. Later stages may assume the number Stage 5's promotion gate compares against, and the harness Stage 7 reuses for its ablations.
      Exit: the harness rejects a mask whose target remains exactly recoverable; a pseudo-hidden truth falling outside the deterministic bounds fails the run as a constraint-data bug (§13.5); the scoreboard covers every §13.3 regime and scores primary-like and complementary-like cells separately; a rolling-origin run provably contains no future-period rows; a random-mask-only configuration is refused as the sole validation design (§13.2); every real-world suppression retains type `unknown` while only synthetic masks carry primary-like or complementary-like labels (INV-009).
      ROUTING: writing-plans

- [ ] Stage 5: State-total Bayesian model (Phase 3)
      Objective: Fit the robust hierarchical state-intensity model, reconcile every joint draw, and promote it only if it beats the Stage 4 scoreboard.
      Spec: §11 intro, §11.1–11.3, §11.5, §11.11 (QCEW rows), §11.12, §11.14, §12.7, §13.10 (gate applied), §15.4, §16.1 (`fit-state-model`), §16.2 (`fit_state_total_model`), §17.4 rows 5–6, §17.5 (state-total rows), §19 Phase 3; §21 PPL row; Appendix A `model:` block.
      Gap closed: REQ-012 (posterior half), REQ-014, REQ-018 (every draw), REQ-019, REQ-024 (gate applied), REQ-029 (model diagnostics); INV-006 (measurement models), INV-008 (posterior half), INV-012, INV-013, INV-014 (applied).
      Consumes: Stage 4's harness and scoreboard; Stage 3's `reconcile_draws`; Stage 2's `deterministic_bounds`; Stage 1's `qcew_monthly`.
      RE-VALIDATED against Stage 3 as shipped: `reconcile_draws(raw_draws, feasible_set, config)` takes `ReconciliationInputs` (an `Anchor` plus per-cell `Bounds`), NOT the `ConstraintSystem` §16.2 types — Stage 5 constructs one from `deterministic_bounds` plus the anchor. It refuses a negative draw rather than flooring it, so a model that can emit negatives must be constrained upstream or the run halts.
      Produces: `models/interfaces.py` defining `ModelData`, `PosteriorDraws`, and `StateModelConfig`; `models/state_total.py` with the NumPyro implementation behind that interface and a CmdStanPy slot per §2.2's backend row; `fit_state_total_model` per §16.2; reconciled joint draws in an ArviZ-compatible store under `runs/<run_id>/posterior/` preserving draw, chain, state, and month indexes; `posterior_summary.parquet` per §7.11 carrying deterministic and posterior intervals in distinct columns; a promotion record comparing the model against the Stage 4 preferred baseline on the §13.10 gates. Later stages may assume reconciled state totals as the row margin Stage 6 allocates, and a PPL-agnostic model interface.
      Exit: the §17.5 synthetic recovery test passes for state effects, region effects, seasonality, AR persistence, and heavy-tailed shocks within stated tolerances; every retained draw satisfies all hard constraints within tolerance, verified after draw transformation rather than on summaries (INV-012); the §11.14 diagnostic gate is enforced in code, not documented; suppressed cells receive no pseudo-observation (§11.3); the promotion record states beat or not-beaten against Stage 4's numbers and the simpler method is selected when not beaten (§13.10 final line).
      ROUTING: writing-plans

- [ ] Stage 6: Annual size-composition model (Phase 4)
      Objective: Allocate reconciled state totals to March-reference size classes through a logistic-normal composition with CBP and national-QCEW measurement models.
      Spec: §3.5, §11.6–11.10, §11.11 (CBP and QCEW-size rows), §12.5, §13.1 targets 2–3, §16.1 (`fit-size-model`), §16.2 (`fit_size_model`), §17.1 row 7 (model side), §17.5 (size rows), §19 Phase 4.
      Gap closed: REQ-003 (enforced), REQ-016, REQ-017 (model half); INV-011 (model half); SRC-QSIZE-003 (benchmark); SRC-CBP-004 (measurement model), SRC-CBP-005.
      Consumes: Stage 5's reconciled state-total `PosteriorDraws`; Stage 1's `cbp_state_size` and `qcew_national_size`; Stage 3's matrix reconciliation; **Stage 0's QCEW-size dimensionality verdict — if an extract proves a state × 113310 × size table exists, re-route this stage to brainstorming before planning, because §2.2 row 3's premise would no longer hold.**
      Produces: `models/size_composition.py` with `SizeModelData`, `SizeModelConfig`, and `fit_size_model` per §16.2; the §11.9 class-support transform applied at March only; state-month-size joint draws whose rows sum to reconciled state totals and whose compatible first-quarter columns reconcile to national class margins; a CBP holdout validation report; and a draft `state_month_size.parquet` with the §15.2 fields populated except the release and sensitivity columns. Later stages may assume the cell grain of the release table, and per-cell size-class estimates for Stage 7's sensitivity envelope and Stage 8's disclosure review.
      Exit: a test proves no March class bound is applied to a non-March month (INV-011, §11.9 final paragraph); every draw's class values sum to the reconciled state total before any national size reconciliation (§11.10); compatible first-quarter national class margins reconcile or the run fails with a diagnostic rather than forcing convergence (§12.5); the CBP holdout report exists and states the §13.1 target-3 limitation that monthly state-size employment has no direct public ground truth; **and the latent composition process is logistic-normal, with a test or interface constraint preventing a fixed Dirichlet or Dirichlet-multinomial from occupying the latent-process slot** (§2.2 composition-family row — the Gemini review's §8 item 2 is the concrete form to reject; multinomial and Dirichlet-multinomial remain permitted as observation models per §11.7).
      ROUTING: writing-plans

- [ ] Stage 7: Proxy sources, harvest factor, and sensitivity suite (Phase 5a)
      Objective: Add TPO and FIA as correlated measurements of a latent harvest factor plus the remaining optional inputs, then run the full ablation and suppression-sensitivity suite.
      Spec: §5.2, §5.3, §7.6, §8.4, §8.5, §11.4, §11.11 (proxy rows), §11.13, §13.9, §19 Phase 5 (proxy and sensitivity deliverables); §21 rows TPO/FIA coverage and optional state sources.
      Gap closed: REQ-007 (SUSB ingest), REQ-015, REQ-025; SRC-FOR-001–004; SRC-OTH-001–004 (ingest halves). SRC-OTH-005 is explicitly out of scope per the gap table.
      Consumes: Stage 0's TPO, FIA, CES, BDS, and SUSB access verdicts and its per-state CES publication level; Stage 5 and Stage 6 models; Stage 4's harness for scoring each proxy's incremental value; Stage 3's harvest-proportional baseline slot.
      Produces: `ingest/{tpo,fia,ces,susb,bds,nonemployer}.py` feeding the §7.6 `proxy_observation` table; `features/harvest_factor.py`; `models/measurement.py` implementing §11.4 with TPO and FIA as correlated measurements of one latent factor rather than independent regressors; `models/suppression_sensitivity.py` covering the §11.13 variants; `validate/ablation.py` covering every §13.9 row; the per-cell §13.9 sensitivity envelope; an include-or-exclude verdict per proxy citing the metric that justified it; and a live harvest-proportional baseline replacing Stage 3's declining stub. Later stages may assume `model_sensitivity_low` and `model_sensitivity_high` for every release cell, which §14.2 and §15.2 both require.
      Exit: TPO harvest-origin and mill-receipt variables occupy distinct fields and the harvest-origin measure is the one used (§8.4 SRC-FOR-001, §2.2 forestry row); FIA rows carry sampling error or a recorded reason they cannot; a test proves no annual or survey-cycle proxy is interpolated and then treated as observed monthly activity (SRC-FOR-004); each CES series is labelled with the industry level actually published for its state, and only a 1133 series is treated as industry-aligned; the ablation report covers every §13.9 row; a sensitivity envelope exists for every release cell; and each proxy's include-or-exclude verdict cites the Stage 4 metric that decided it (§19 Phase 5 acceptance: proxies demonstrate incremental value or are excluded).
      ROUTING: brainstorming

- [ ] Stage 8: Disclosure governance, release package, and clean-room rebuild (Phase 5b)
      Objective: Gate every cell through disclosure review, emit the nine release tables under the required label, and prove a clean environment reproduces the release from its manifests.
      Spec: §7.11 (final form), §7.12, §14 (all), §15 (all), §16.1 (`disclosure-review`, `publish`, `run-all`), §17.4 row 8, §17.6 (release schemas), §18 (all), §19 Phase 5 (governance deliverables), Appendix B; §21 rows disclosure thresholds and promotion thresholds; Appendix A `disclosure:` block.
      Gap closed: REQ-026 (release actions), REQ-027, REQ-028 (full §18.1), REQ-029 (governance), REQ-030; INV-002 (release check), INV-015, INV-016.
      Consumes: everything shipped through Stage 7; Stage 2's exactness and narrowness flags; Stage 7's sensitivity envelope; Stage 5 and Stage 6 posterior summaries.
      Produces: `disclosure/{policy,review}.py`; the §7.12 `disclosure_decision` table with its `release_action` enum; the §14.3 concentration metric recorded as a review indicator and not an accuracy score; the three separate statuses of §14.1; `publish/` emitting all nine §15.1 artifacts with the §15.2 fields and §15.3 model-dependence levels; the §14.5 label on every modeled record; `run_manifest.json` per §18.1; the §18.2 monitoring metrics; CLI `disclosure-review`, `publish`, and `run-all`.
      Exit: an exactly-reconstructed `N`-flagged cell cannot reach `release_observed` or `release_model_estimate` without a recorded reviewer decision (REQ-027, §14.4); every §14.2 trigger routes to review, each with a test; `run-all` on a fresh clone holding only `data/raw/` and the manifests reproduces the recorded output hashes (Appendix B, REQ-030, INV-016); all nine release files validate against their schemas and every modeled record carries the §14.5 label; the §18.3 fail-closed conditions each halt the pipeline, with a test per condition; **and a test proves no code path can widen a posterior by injecting variance and then mark the cell releasable — high-risk cells exit only through the §14.4 remedies** (§2.2 privacy-mitigation row; the Gemini review's §12 is the concrete form to reject).
      ROUTING: writing-plans

- [ ] Stage 9 (optional): Phase 6 extensions
      Objective: Choose and design any §19 Phase 6 extension the owner wants once the core system is released.
      Spec: §3.4 `realtime_asof`, §3.5 `contemporaneous_modeled`, §19 Phase 6.
      Gap closed: none — no numbered requirement mandates Phase 6, and D2 places it outside the core scope.
      Consumes: a released Stage 8 system; the owner's choice of extension. County-level work additionally consumes the MWR limitation the Gemini review raises in its §5 and §15, which §19 Phase 6 already names.
      Produces: one sub-project spec per chosen extension, each carrying its own validation and disclosure review per §19 Phase 6's closing line.
      Exit: a spec exists for each chosen extension, or this stage is marked "declined" with a date.
      ROUTING: brainstorming

## Stage-spec stamp

All stages implement `specs/logging-employment-spec.md`. Its Rollout note
carries one stamp line per routed stage, which writing-plans copies verbatim
into the stage plan's header:

> Roadmap: specs/logging-employment-spec-roadmap.md, Stage N — on plan
> completion, tick the stage and re-validate later stages against what
> shipped.

On completion the stamp becomes authoritative:

> Stage N: COMPLETE (YYYY-MM-DD) — implemented by plan <id> (path).
> Next: resume the roadmap.

## Completion

Retire this roadmap only after re-running the gap rubric over the accumulated
system with evidence per row — the implementing stage and plan, any
`> Deviation:` notes, and any `specs/deferred_items.md` entries — and
confirming the Appendix B scenario runs end-to-end from a clean environment.
This is a conformance audit of the accumulated system, not a whole-roadmap code
diff: stages merged separately and code quality was reviewed per stage.

Unmet rows exit exactly two ways: a new stage, leaving the roadmap live, or a
conscious deferral with a written reason. SRC-OTH-005 is already in the second
category, recorded in `specs/deferred_items.md` with the BEA discontinuation as
its reason; confirm at retirement that its premise still holds.

Optional independent check: re-run describe-critique-methodology's Describe
mode on the shipped system and diff the fresh description against §9–§14. That
is a re-derivation rather than a self-assessment, and it is the natural input
to the next critique round. Where the remaining improvement directions are
diffuse, route to creative-thinking.
