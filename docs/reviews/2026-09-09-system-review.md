# Spec-driven system review — `logging_employment` at `c4bbf4e` (2026-09-09), with a 2026-09-10 addendum at `c7abb05`

**Scope.** Four source documents, the master spec, the roadmap, twelve retired plans, three sub-project specs, the deferred-items register, the conventions hierarchy, the code, the tests and the run artifacts, at the point where Stages 0–4 of the roadmap are ticked and Stage 5 (the state-total Bayesian model) is next. Read-only; the only file written is this report. Method: orientation and every High-severity item read by me in the primary material; parallel subagent readers for the sources, spec slices, git history, tests, plans, each module family and every deferred item, with every "resolved" verdict checked against code and a test; the full suite, linter, formatter and docstring gate run with the project's own commands.

## 1. Executive summary

The system is in better shape than its documents. The code that exists is principled, deterministic, fail-closed where it was designed to be, and reproducible: the full suite is green here (1,356 tests, 7 minutes), the three gates pass, and every headline number in the stage stamps re-derives from the staged data. The architecture matches the spec's design and the invariants that would be expensive to get wrong — no national state-sum constraint can be built, the allocation anchor is admitted only by an establishment-closure gate, a pseudo-suppression mask lives in the frame so a leak is unconstructible — are enforced by types and tests rather than by prose. What is not in good shape is the *record*: the roadmap ticks Stage 4 complete against two exit criteria the harness does not enforce and one it re-read after shipping; it says REQ-022 is closed while the rolling-origin regime scores nothing; the spec's normative text still requires a "compatible national total" the project's own audit declined and never names the anchor that replaced it; the reference configuration in Appendix A does not load; the retirement scenario in Appendix B cannot be satisfied; one of the five source documents the synthesis cites was not in the repository at the reviewed commit (it arrived the next day; §10); and three fail-closed guarantees are latent rather than real (baseline estimates are never checked against per-cell bounds, a non-200 fetch is dropped silently, a clean install cannot import the package). The deferral register is honest and has no silent drops, but 22 of its 39 open items are overdue and unowned, nine of them against stages ticked complete. Process health is the real concern: the completion signal has failed twice in a row, plans are retired within minutes of being written, and the corrective effort has moved into roadmap stage blocks that are single 13 KB lines accreting dated corrections.

| Dimension | Rating |
|---|---|
| Spec integrity | Concern |
| Intent coverage | Watch |
| Architecture | Sound |
| Correctness and robustness | Watch |
| Test health | Watch |
| Code quality and conventions | Sound |
| Tooling and operability | Concern |
| Process health | Concern |

**Five things to know before Stage 5 starts.**
1. **Do not plan Stage 5 from the roadmap's Stage 4 block or the spec's §13.** Nine of thirteen regimes score, on one arm, primary-like only; §13.5–13.8's stratified and constraint metrics that §13.10's gate needs do not exist; the "rolling" intervals are cross-sectional; the comparand may be `None`; the harvest baseline and the "required" harvest factor arrive two stages later (F-001, F-002, F-003, F-019, F-028).
2. **Two latent fail-open paths will bite the moment the data or the stage changes**: baselines never see `deterministic_bounds`, so the first finite upper bound on a state cell is exceeded silently (F-006); `fetch` drops a failed quarter with no record (F-009). Both are hours to fix.
3. **A clean environment cannot run the system**: `python-dotenv` is dev-only and imported at module scope, and 42 tests fail without the gitignored `data/` (F-007, F-010). No CI exists to notice.
4. **The identification engine identifies nothing on the product's primary target** — every one of 1,227 suppressed state cells is `[0, +∞)` — and the §9.3 margins that could change that were never fetched, declined or owned; the release contract has no field to say the national anchor is a modelling assumption (F-004, F-005).
5. **The spec is no longer the source of truth and says it is.** Amend §12.2, §16.2, §10.7, Appendix A and Appendix B, extend the roadmap's gap table past the 76 ids of day one, change the stage-block format, and put the tick, the stamp and the plan retirement in one commit guarded by a test (§7.4). This is a day of record work that removes four of the ten register risks.

None of this is Critical: nothing found makes a shipped number wrong on the pilot window. §10 (added 2026-09-10) folds in the prompt, which arrived the next day and confirms that the dropped national-benchmark fallback and the unowned §9.3 margins were prompt requirements, and a fifth research review, which should be filed as a post-synthesis document: three of its load-bearing claims fail against the project's own data. The remaining roadmap is the right order; it needs a record-only precondition step before Stage 5, a split between fitting the model and applying the promotion gate, and Stage 6's Consumes block to inherit the bounds, size-arm and margin questions explicitly (§7.5).


## 2. Intent reconstruction (Phase 1)

### 2.0 Orientation (Phase 0)

**Repository shape (observed).** One installable package, `src/logging_employment/` (67 modules, 10,038 lines), a Typer CLI `logging-estimates` with 9 of §16.1's 15 commands, and a test tree of 1,356 collected tests in three families (`tests/unit` 580, `tests/integration` 93, `tests/audit` 683 at `--collect-only`; the audit family tests the Stage 0 PEP 723 scripts under `scripts/audit/`, 8,633 lines, not the package). No CI configuration exists (`ls .github Makefile justfile` → none). Tooling is `uv` + hatchling, Python 3.14.0, ruff 0.16.6 as the single formatter and linter, `interrogate` at `fail-under = 100`. `data/` (561 MB raw, 1.7 MB staged) and `runs/` are gitignored and present on this machine.

**Spec-like documents (observed, with paths).**

| Role | Path | Size | Notes |
|---|---|---|---|
| Source review | `specs/logging-employment-research-chatgpt.md` | 1,026 lines | single commit `8899b5f` |
| Source review | `specs/logging-employment-research-copilot.md` | 458 lines | single commit `8899b5f` |
| Source review | `specs/logging-employment-research-gemini.md` | 455 lines | 44 formula images embedded as base64 PNGs, not text |
| Source (literature) | `specs/suppressed-cell-estimation.md` | 869 lines | named by §2.1 as the governing identification framework |
| Source (prompt) | `specs/logging-prompt.md` | 584 lines | cited at spec §2 l.51, §2.1 l.57, Appendix C l.2292 as `logging-prompt.md` / `logging-prompt(1).md`; **absent at `c4bbf4e`**, added by `c7abb05` on 2026-09-10 (see §10) |
| Source review (post-synthesis) | `specs/logging-employment-research-fable.md` | 517 lines | dated 2026-09-10; added by `c7abb05`; not a synthesis input (see §10.3) |
| Master spec | `specs/logging-employment-spec.md` | 2,514 lines | 18 commits; Rollout + Stage stamps at l.2300–2514 |
| Roadmap | `specs/logging-employment-spec-roadmap.md` | 310 lines | 28 commits; stage blocks are single lines of 6.6–13.2 KB |
| Deferred tracking | `specs/deferred_items.md` | 1,569 lines | 38 commits; 84 checkboxes (45 ticked, 39 open) |
| Sub-project specs | `specs/completed/{estimator-composition,break-adjusted-share-refusal,stage4-harness-completion}.md` | 176–294 lines | each names the deferred items it closes |
| Plans | `specs/plans/completed/1..12-*.md` | 572–7,501 lines | 12 plans; 6 are non-stage sub-projects (5–10) |
| Findings | `specs/findings/{source-audit,source-audit-notes,stage3-plan-audit}.md`, `source-audit-extracts.csv` | 6,496 / 118 / 689 lines | Stage 0 output and a pre-execution plan audit |
| Conventions | `CLAUDE.md` + five submodule `CLAUDE.md` (baselines, constraints, ingest, reconcile, validate) | 145 + 109–200 lines | added 2026-09-09 (`6eb2050`) |

Deferred tracking is centralised in one file, which is good; but deferrals also live as `> Deviation` notes inside plans, as `SHIPPED`/`RE-VALIDATED` prose in roadmap stage blocks, and as `CORRECTED`/`SUPERSEDED` annotations in three places. The roadmap's own header rule excludes live stages from `deferred_items.md`, so the roadmap block is itself a second backlog. Scattered tracking is a finding (F-021).

**Stage history from git (observed; the git-history subagent's timeline, spot-checked against `git log --first-parent`).** The project is seven days old: 415 commits from 2026-09-03 to 2026-09-09, 96 on main's first-parent line. Stages 0–4 are ticked; the review prompt's "4 of 9" counts Stages 1–4 of 1–9 and omits Stage 0 and the optional Stage 9; by roadmap blocks it is 5 of 10 ticked, with one optional.

| Stage / plan | Plan added | Declared done | Merged | Stamp protocol |
|---|---|---|---|---|
| Stage 0 (plan 1) | `df12b13` 09-03 13:54 | `1defbf0` 09-04 20:25 | PR #1 `8b1388b` 09-05 | compliant (tick + suffix + spec stamp in one commit) |
| Stage 1 (plan 2) | `2393f0a` 09-05 08:52 | `5969bd9` 09-05 11:06 | PR #2 `24e280b` 09-05 11:46 | compliant |
| Stage 2 (plan 3) | `b53fdde` 09-05 12:44 | `cb37d02` 09-05 14:21 | PR #3 `c94f0d9`, PR #4 `de09c93` | compliant |
| Stage 3 (plan 4) | `d0cdc33` 09-05 16:05 | `5f747fa` 09-05 17:28 (tick only) | PR #5 `344bdf7` 09-05 18:49 | **late**: spec stamp and heading suffix added `be3e161` 09-07 after a deferred item flagged it |
| Plans 5–10 (sub-projects) | 09-05 20:10 → 09-07 12:55 | 10–40 min after add | fast-forward / local merges | n/a (no stage) |
| Stage 4 (plan 11) | `4e81b77` 09-07 15:48 | `771dabe` 09-07 17:34 (tick only) | PR #6 `23c4945` 09-07, then PRs #7–#18 | **late and unrecorded**: spec stamp only at `f8fa033` 09-09 16:02; roadmap heading still lacks the suffix at HEAD (`roadmap:219`) |
| Plan 12 (Stage 4 completion) | `5a3fe38` 09-08 18:34 | `f8fa033` 09-09 16:02 | fast-forward 09-09 18:55 | n/a |

All three coding stages (1–3) shipped on one calendar day (2026-09-05, 88 branch commits); the next two days were dominated by corrections: 14 "unregistered work" items found by a post-plan-9 audit (`21d1ce0`), and 12 PRs (#7–#18) in 21 hours after Stage 4, seven of which touch only `specs/` or `runs/`.

**Spec drift versus code drift (observed; classification of every post-stage-start edit to the spec and roadmap is in Appendix 9.3).** Of the spec edits after a stage began: three are spec-drift proper — §7.13 (`9a58a0e`, 2026-09-07) declares a table `contracts.py` had carried since `627c736` (09-05); §7.14/§7.15 (`297d657`, 09-09) declare two tables `cli.py` had persisted since `5d853fd` (09-07); Appendix A's `validation:` block (`cfc854d`, 09-09) documents switch semantics code had already fixed. One is a new requirement written after its stage closed: §10.9 and the §13.8 decline paragraph (`9a58a0e`) were added two days after Stage 3 was ticked, and no roadmap `Spec:` line lists §10.9. The remainder are corrections of false claims or clarifications. Code drift with docs left stale is the larger category and is catalogued in §3.3 (divergences): §9.2's atomic key, §9.6's MILP trigger, §12.2's compatible national total, §16.2's signatures, §6.1's layout, §6.2's storage, Appendix A itself.

### 2.1 Source specs (Phase 1a)

Four source documents are present; a fifth (`logging-prompt.md`) is cited as supplying "the requested scope and epistemic discipline" and is absent from the repository and its history. Everything below about the prompt is therefore inference from what the other documents say it asked for.

| | Problem framed | Requires (distinctive) | Excludes | Assumes |
|---|---|---|---|---|
| **ChatGPT report** (1,026 l.) | Monthly state private (`own_code=5`) QCEW-covered jobs at 113310 establishments by March-reference size class, with a `contemporaneous_modeled` alternative labelled separately | Five-way constraint label taxonomy on every constraint row (→ INV-004); softmax residual allocation making the national total exact per draw; Student-t AR(1) with concrete priors (Beta(8,2) on (ρ+1)/2, ν=5, β~N(0,0.5²)); logistic-normal (not Dirichlet) composition; interval-support intensity `m = L + (U−L)·logit⁻¹(ψ)` with a heavy-tailed open class; latent harvest factor with TPO/FIA as correlated measurements; `suppressed_variance_multipliers {1.0,1.5,2.0}`; joint draw retention; balanced rounding with a second class-margin balancing pass | Proprietors/nonemployers; total-ownership series (optional second series); interpolating annual proxies to months | CBP noise-infusion facts (G/H/J, <3-establishment drops) from a page it says is under revision; a compatible undisclosed national private 113310 monthly total exists; QCEW open-data serves five years |
| **Copilot report** (458 l.) | Same estimand; explicit classification-decision log with three verbatim field names for `1113310 → 113310`; nine QCEW size classes | Three restriction classes (public fact / definitional support / empirical measurement as intervals); 1,000+ class has no finite public upper bound unless a parent supplies one, paired with a Pareto/lognormal tail prior as a separate object; ten named baselines including two Bayesian ablations; eight non-random pseudo-suppression designs incl. NAICS boundaries and preliminary-vs-final; national-vs-state compatibility test quarter by quarter including residual areas; disclosure flags for "posterior dominated by a strong prior" and "public employer information could reveal a dominant establishment" | Persons (jobs count twice); government ownership; time range explicitly unspecified (l.452); DC/PR never mentioned | 18 of its 36 citation tokens resolve to no bibliography entry; CBP state×113310×EMPSZES exists (never exercised with a key) |
| **Gemini report** (455 l.) | Decomposition E = A·p·r (exposure × size share × intensity); staged Stan/CmdStanPy pipeline | TPO/FIA harvest removals with a POST recipe; complementary-industry bound 113310 ≤ 113 − disclosed siblings; propensity-score pseudo-suppression (logistic on establishments + volatility); per-class TruncatedNormal intensities; Dirichlet-multinomial March shares with a latent GP monthly; reconciliation inside the sampler; IPF to state margins | — | **Asserts an "80/3" QCEW rule** as an identification constraint; **recommends artificial variance injection** and regional aggregation before publication; disclosure threshold `U−L < 3`; `agglvl_code '54'` for state six-digit (repo measured `58`); "no crosswalk bridges needed" |
| **Literature review** (`suppressed-cell-estimation.md`, 869 l.) | Identification-first: assemble public identities from one coherent vintage, compute rank/null space and LP/MILP bounds, then model within bounds; QCEW is MNAR + deterministic censoring + design-induced missingness | Five-way identification status (exactly recoverable / partially identified / model-estimable / assumption-sensitive / fundamentally unidentified) with a prescribed reportable output per status; rounding as half-width intervals per documented convention; **weighted-L1 slack fallback for unavoidably incompatible vintages**; sparse QR/SVD exact-rank per component; MILP only where integrality can matter; hierarchy-matrix caching; explicit selection likelihood P(R \| x, …) with sensitivity models over selection effects; two-stage pseudo-suppression (surrogate primary, then independent complementary) scored separately; whole-slice holdouts; nine evaluation strata; full metric set incl. L1/L∞ violation norms; seven-member benchmark suite and a complexity gate against the seasonal historical-share baseline; structural-break sensitivity S_j with an "assumption-dominated" criterion | Adding privacy noise to outputs (remedies are widen/aggregate/suppress/restrict); publishing exact reconstructions of `N` cells | Externally justified bounds may enter the LP "only if bounds themselves are valid public facts"; the atomic key is area × industry × ownership × period (no size class) |

**Where they agree (the load-bearing consensus).** All four put deterministic identification (rank, LP/MILP bounds from public accounting identities on one vintage) before any model; keep the deterministic interval and any posterior interval separate; treat published QCEW values as exact for their vintage; require exact reconciliation of every draw to hard margins; require realistic (non-random) pseudo-suppression with leakage controls; require transparent baselines that a complex model must beat; and route exact or narrow reconstructions to disclosure review rather than publishing them. All three logging reports independently agree on March-reference establishment size, private ownership, and CBP as a noisy March-centred measurement rather than a QCEW identity.

**Where they conflict.** (1) Composition family: ChatGPT and the literature review favour logistic-normal; Gemini uses Dirichlet-multinomial as the latent March process. (2) Disclosure rule: Gemini asserts 80/3 and derives a hard MILP bound from it; Copilot and the literature review say the numerical rule is undisclosed. (3) Privacy mitigation: Gemini injects artificial variance; the literature review's remedies are widen/aggregate/suppress/restrict. (4) Reconciliation locus: Gemini reconciles inside the sampler with lognormal renormalisation; ChatGPT and Copilot reconcile draws after sampling. (5) Vintage incompatibility: the literature review offers a weighted-L1 slack fallback; ChatGPT/Copilot treat incompatible vintages as never stackable. (6) National total: ChatGPT presupposes a compatible national total for exact softmax allocation; Copilot requires the compatibility test first and explicitly flags residual areas. (7) Tooling: Gemini pins Stan/pandas/PuLP; ChatGPT prefers a JAX-capable backend. (8) Extra sources: all three reports name weather/permits/severance feeds and BEA; the literature review is silent.

**Requirements carried by one source only.** Copilot's classification-decision log with verbatim field names (adopted as §3.1/REQ-001); Copilot's "1,000+ class has no finite public upper bound" paired with a separate tail prior (adopted as §9.3 "arbitrary top-class caps" forbidden + §11.9's heavy tail); ChatGPT's five-way constraint label taxonomy (adopted as INV-004); ChatGPT's `suppressed_variance_multipliers` (adopted in Appendix A's `model:` block); the literature review's separate scoring of primary-like and complementary-like cells (adopted as §13.2 step 8); the literature review's L1/L∞ violation norms (adopted as §13.8); the literature review's structural-break sensitivity S_j (adopted as §13.9's envelope); Gemini's complementary-industry parent bound (adopted generically as §9.3 "compatible parent industry totals equal to children"); Gemini's propensity-score masking (adopted as §13.2 step 1). Carried by one source and **not** adopted: the literature review's five-way identification status with a reportable output per status (§9.8 has six labels and no per-status output rule); its weighted-L1 slack fallback (forbidden by INV-007's "never stacked silently" — a deliberate drop, unrecorded); its derived-statistics constraints (LQ to hundredths, percent change to tenths: absent); its explicit selection likelihood (absent; §11.13's variance multipliers are the nearest thing); Copilot's "posterior dominated by a strong prior" and "dominant establishment" flags (present only as §14.2 prose triggers with no field until §7.12); ChatGPT's optional total-ownership second series (absent; §3.2 fixes private).

### 2.2 Synthesis fidelity (Phase 1b)

This subsection reports what I confirmed by reading the master spec against the four extractions; the fidelity subagent's independent pass is reconciled in §2.2.1 below.

**Conflicts the synthesis resolved, and where.** §2.2's thirteen-row table resolves (1)–(3), (5), (7) above explicitly and cites the losing side in Appendix C ("Claims about exact current suppression thresholds and universally available size constraints were not adopted"). The roadmap goes further and converts three rejected Gemini recommendations into negative exit criteria on Stages 2, 6 and 8 — a good practice; Stage 2's is implemented (`tests/unit/test_constraint_rows.py::test_a_constraint_warranted_by_an_assumed_threshold_can_never_be_hard`, `tests/integration/test_d1_acceptance.py::test_no_hard_constraint_rests_on_an_assumed_threshold`). (4) reconciliation locus is resolved by §12.7/INV-012 (reconcile every draw after transformation). (6) is resolved by SRC-QCEW-006's three-branch rule and, empirically, by Stage 0's `decline` verdict.

**Conflicts papered over (both sides survive, inconsistent).** (a) §12.2 makes a national-residual fast path "required" for "a compatible national total N_t" while the spec's own Stage 0/2 stamps record that no such total is verifiable on the window; §12.2 was never amended and the substitute anchor is documented only in code and a roadmap paragraph (F-006). (b) §13.2 step 8 scores primary-like and complementary-like cells separately while §13.10 gates "on primary-like masks"; the spec never says the comparand is single-arm — the roadmap supplies that reading. (c) §9.1 forbids models in identification while §9.8 asks the same engine to label cells `model-estimable`/`model-only` (code never emits them; `contracts.py:186-188`). (d) §11.1 lists the latent harvest factor H as a "required component" of the Stage 5 model while Appendix A ships `include_harvest_factor: false` and Stage 7 owns it. (e) §11.3 calls published values "exact observations" and then attaches Student-t observation noise σ_y. (f) §3.4 says the system MUST support two modes and MAY implement one; `realtime_asof` validates, re-ids the run and is ignored (deferred item D-064). (g) §14.1's three statuses (`identification_status`, `estimation_status`, `release_status`) appear in no §7 contract (`grep` of `src/` empty). (h) SRC-QSIZE-003 grants hard-control eligibility to "first-quarter monthly fields" while §7.4, INV-011 and §2.2 speak only of March.

**Content the synthesis introduced that no source contains (confirmed by grep of the four sources).** The fifteen-command CLI of §16.1 and every §16.2 signature; the §7 field lists as such (sources name concepts, not columns — e.g. `employment_noise_range`, `is_published_numeric_zero`, `vintage_compatibility_status`); §13.10's numeric gates (5 % WAPE, 2 % stratum, 5-point coverage) — the spec itself says they "are not findings from the source reports"; Appendix A's values (`use_milp_when_lp_interval_width_below: 25`, seeds `[1024, 2048, 4096]`, `target_accept 0.9`); the `march_reference`/`contemporaneous_modeled` enum names; §6.1's 60-file layout; and, post-synthesis, §10.9's composition rules (plan 9) and §7.13–7.15 (plans 9, 12). None of these is wrong to introduce; the point is that they are engineering decisions carrying MUSTs whose authority is the synthesis alone.

**Silent drops (source requirement absent from the synthesis).** Confirmed: the literature review's weighted-L1 slack for incompatible vintages (deliberate by INV-007; unrecorded); its per-status reportable output rule (dropped; §9.8 keeps only the labels); its derived-statistics constraints (dropped; §9.4 keeps only rounding intervals); its explicit selection likelihood (dropped in favour of §11.13 multipliers — arguably deliberate, unrecorded); Copilot's total-ownership optional series (dropped; not mentioned in §3.6 non-goals); Gemini's regional aggregation before publication (kept only as a §14.4 remedy, which is the right reading); all three reports' weather/permit/severance feeds (kept as §5.3 "optional", deferred to Stage 9 — consistent).

**Spec-quality defects (the three spec-ledger subagents' lists, each item spot-checked).** The full lists are in Appendix 9.4; the ones that matter for the next stage:

- *Reference configuration does not load.* `Config.model_validate` over Appendix A's YAML raises 11 errors (seven `sources.*` extras, `model` extra, `baselines` missing, two `disclosure.*` keys missing). `CLAUDE.md` calls Appendix A "≈ `config.yaml`"; it is not, and `config.yaml`'s own header cites Appendix A by line numbers that are 142 lines stale (F-013).
- *Appendix B cannot be satisfied as written.* Step 6 "builds a national state-sum constraint" — SRC-QCEW-006 is `decline` and `rows.assert_no_national_employment_margin` refuses exactly that row; step 7 "LP bounds for suppressed states" is vacuous on the window (every state cell is `[0, null]`). The roadmap's Completion section makes an end-to-end Appendix B run the retirement gate (F-007).
- *Untestable MUSTs at the frontier.* §13.10: "improves WAPE by at least 5 %" (relative or points? config stores `0.05`), "major stratum", "catastrophically", "clearly superior calibrated uncertainty distribution"; §11.14: "adequate", "stable", "documented exception is approved" (approver unnamed); §14.2: seven triggers with undefined quantities; §14.3: R_i divides by a deterministic width that is null on 1,227 of 1,241 unknown cells.
- *Normative-keyword inconsistency.* §1.1 makes only capitalised MUST/SHOULD/MAY normative; at least 20 binding sentences use lowercase `must`/`required`/`never` (e.g. §14.5, §15.4, §16.2 l.1839, SRC-OTH-005). Their priority is formally unstated.
- *Terminology.* One concept under four names (`exactly_recoverable` / `exactly_identified` / "exact identification" / "exact-recovery rate"); "hard constraints/bounds/controls/restriction"; `disclosure_decision` vs `disclosure_decisions.parquet`; `validation_score` vs `validation_scores.parquet`; "preferred transparent structural baseline" (§10.4, by designation) vs "preferred transparent baseline" (§13.10, resolved by scoring).
- *Stale premises in binding text.* Rollout D5 still says the slice endpoint serves "only the most recent five reference years" (Stage 0 measured 2014); §6 says "Python 3.11 or later" against D4's 3.14; §5.4 seeds `qcew_quarterly` while the registry uses `qcew` and lists no `qcew_size` seed although §5.1 makes it mandatory.
- *Invented or infeasible fields.* §7.12 `dominant_employer_linkage_flag` needs employer identification that §3.6 excludes; §15.2 `qcew_disclosure_code` on a state×size cell, which QCEW never publishes; §7.5 `employment_noise_range` maps to `EMP_N`, literally `'0'` on every row, while the field that carries the noise band (`EMP_N_F`) has no column (D-026).
- *The spec depends on code symbols.* Appendix A's comments name `contracts.VALIDATION_SWITCH_KINDS`, `tests/unit/test_validation_switch_kinds.py` and `ValidationConfig._refuse_a_random_mask_only_design`; §7.14 carries a dated measurement ("measured 2026-09-09 … null on all 12,530 scored rows") in a contract.



#### 2.2.1 Reconciliation with the fidelity subagent

The independent fidelity pass (Appendix 9.5 has its raw lists) agrees with §2.1–§2.2 on the consensus, on the §2.2 resolutions, and on the introduced content, and adds five silent drops I had not found: (1) ChatGPT l.325's fallback for an unavailable national benchmark — *the* drop that made Stage 3 invent the anchor (folded into F-004); (2) ChatGPT l.609/613's separation of duties for disclosure approval (F-029); (3) ChatGPT l.495's `national_constraint_status` and `proxy_set` release fields (folded into F-004); (4) ChatGPT l.601's fail-closed conditions for an unknown NAICS vintage or ownership definition, absent from §18.3 (the code refuses pre-2017 years and closes ownership by constants, but no spec text requires either); (5) Copilot l.222's establishment-exposure ablation (the one assumption every §10 baseline shares — quarterly count as monthly — is never sensitivity-tested; §13.9 lists no such ablation). It also records that §2.2's thirteen rows cover only part of the conflicts actually resolved: NAICS-continuity verification (§3.1), ownership (§3.2), CBP-noise treatment (INV-006), national-total availability (SRC-QCEW-006), CES alignment (D6), the QCEW `agglvl` code (`58` vs Gemini's `54`) and the slice-route coverage (D5 vs Stage 0) are resolved outside the table that claims to record resolutions. I accept all of these; they are reflected in F-004, F-014, F-015 and F-029.

### 2.3 Roadmap fidelity (Phase 1c)

**Numbered coverage is complete.** Crossing every `Gap closed:` line against the spec's 76 numbered ids (30 REQ, 16 INV, 25 SRC, 5 CON) finds no id owned by no stage and 32 ids split across two or more stages (script output in Appendix 9.2). The roadmap's gap table also lists all 76. So the roadmap is complete against what the spec *numbered*.

**Unnumbered MUSTs are where ownership fails.** The spec has 85 lines containing `MUST`; most are not covered by a numbered id, and several are owned by no stage: §16.1's "every command MUST write a machine-readable manifest" (Stage 1 claimed it for four commands; two write nothing — D-057); §7's preamble "every table MUST include `run_id` … and a schema version" (no table does); the §7.8/§9.3 soft-constraint classes `empirical_measurement`, `modeling_assumption`, `sensitivity_assumption` (declared in `contracts.CONSTRAINT_CLASSES`, emitted by nothing; `bounds.py:75-76` cites Stage 3 as the producer, Stage 3 shipped none, and no later Produces line names one — D-061); §10.9 and the §13.8 decline paragraph (added by plan 9 after Stage 3 closed; no `Spec:` line lists §10.9); §17.2's ninth property ("every reconciled draw lies within bounds and satisfies margins") which plan 3 handed to Stage 3 and plan 4 never mentions; §13.6's `size-share absolute error` and rank accuracy, assigned to Stage 4 by range but infeasible until Stage 6 produces a size estimator.

**Exit criteria that are not testable as written.** Stage 0: "no unresolved direct-source dimensionality assumptions" (a negative universal; discharged by a finding file). Stage 5: "adequate effective sample size", "stable posterior summaries", "the simpler method is selected when not beaten" (a disjunction satisfied either way). Stage 7: "proxies demonstrate incremental value or are excluded" (same). Stage 8: "clean-room rebuild succeeds" (undefined), and the §14.2 triggers each "with a test" while five of the seven triggers name no quantity. Stage 4's exit clause "scores primary-like and complementary-like cells separately" was discharged by the *absence* of the second label (D-075's resolution says so), which is a re-reading rather than a test.

**Dependency-ordering problems.** (1) Stage 4 was built before Stage 5 exists, by design, so its scoreboard names a comparand for a gate nothing applies; the `promotion:` block's three keys are read by no code (grep). That is acceptable *if* Stage 5's plan treats `PromotionConfig` as inert until wired. (2) Stage 3's §10.5 harvest baseline depends on Stage 7's harvest factor and declines by design in all 1,227 rows; the roadmap says so. (3) Stage 6 consumes `reconcile_matrix`, which hardcodes `lower=0, upper=+inf` and takes no bounds (F-016), and `integerize`'s bounded arms, which no caller exercises; both are "shipped" per the Stage 3 block. (4) Stage 5's `reconcile_draws` takes `ReconciliationInputs`, not §16.2's `ConstraintSystem`; recorded in the roadmap, not in §16.2. (5) Stage 7's `SRC-OTH-001/004` guards were listed under Stage 1's "Gap closed" while being uncalled until Stage 7 — now recorded in a docstring (D-068). (6) The roadmap's Completion gate (Appendix B end-to-end) is unsatisfiable as written (F-007), so nothing currently defines what "done" means for the roadmap as a whole.

**Roadmap as a document.** The three completed-stage blocks (Stage 3 SHIPPED, Stage 4 RE-VALIDATED, Stage 4 SHIPPED) are single lines of 11,323, 6,661 and 13,199 bytes that grew 10× by in-place accretion of `CORRECTED`/`SUPERSEDED`/`UPDATED`/`AMENDED`/`RESOLVED`/`SETTLED` markers (8/4/2/1/2/1 at HEAD), with two same-day reversals and one "keep both" merge that duplicated the Stage 4 block on main for two hours (`be70360` → `3be0275`). Nothing states how the markers compose. The spec's Rollout says "Stage stamps below are authoritative", and the Stage 3 and Stage 4 stamps then defer their substance to those roadmap lines. In practice the source of truth for what a stage delivered is the latest marker in a 13 KB line, read by a human (F-021, F-022).

### 2.4 Intent ledger (Phase 1d)

One row per numbered id. `Sources` names the source documents that carry the requirement (C = ChatGPT, P = Copilot, G = Gemini, L = literature review; S = synthesis-only). `Priority` is the spec's own keyword. `Stage` is from the roadmap's gap table. `Status` is this review's verdict from §3 (implemented requires a test that would fail if the requirement broke). Unnumbered normative statements that matter are carried as `R-<section>` rows at the end.

| ID | Requirement (abridged) | Sources | Priority | Stage(s) | Status | Ambiguity / note |
|---|---|---|---|---|---|---|
| REQ-001 | Record supplied and corrected industry codes | P (verbatim fields), C | MUST (§3.1) | 1 | partial | `classification_memo` builder exists with tests, called from nowhere; no memo artifact (D-058) |
| REQ-002 | Private QCEW-covered jobs as core target | C, P, G, L | MUST | 1, 2 | implemented | `qcew.apply_universe_filter`; `target_cell` |
| REQ-003 | Default to March-reference size | C, P, G | MUST | 1, 6 | partial | config default only; enforcement is Stage 6 |
| REQ-004 | Freeze vintages and checksums | C, P, L | MUST | 1 | implemented | content-addressed store; `source_manifest.parquet` (47 rows) |
| REQ-005 | Parse QCEW disclosure before numeric values | C, P, L | MUST | 1 | implemented | `infer_schema_length=0`; `test_qcew_parser` |
| REQ-006 | Dynamically discover CBP dimensions and regime | C, P, G | MUST | 0, 1 | partial | official `EMPSZES` crosswalk route dead (`discover_empszes` no caller, D-060); regime registry typed from Stage 0 |
| REQ-007 | Preserve SUSB enterprise-size semantics | C, P | MUST | 1, 7 | stubbed | `reject_enterprise_size` uncalled, documented as reserved (D-068) |
| REQ-008 | Explicit compatibility bridges | C, G(contra) | MUST | 1 | implemented | `bridge.parquet` (2 rows); §8.6 fields |
| REQ-009 | Sparse public accounting constraints | L, C, P | MUST | 2 | implemented | `constraints/rows.py`; golden matrix |
| REQ-010 | Rank, nullity, connected components | L, C | MUST | 2 | implemented | CON-003 "structural and numerical" → one `rank` column plus `nullity`; both computed, one persisted |
| REQ-011 | LP/MILP sharp bounds | L, C, P, G | MUST | 2 | diverged | MILP gated on LP width `< 25`, not on "integer feasibility can change the result" (F-014) |
| REQ-012 | Feasible and posterior intervals separate | L, C, P | MUST | 2, 5 | partial | no posterior yet |
| REQ-013 | All transparent baselines | P (ten), C, L | MUST | 3, 4 | implemented | 10 estimators; §10.5 declines by design; §10.7 intervals in `validate/intervals.py` |
| REQ-014 | Robust hierarchical state-total model | C, P, G | MUST | 5 | missing | not started; no jax/numpyro in `uv.lock` (D4 wheel check done 2026-09-05) |
| REQ-015 | Latent TPO/FIA harvest factor | C, P, G | MUST | 7 | missing | |
| REQ-016 | Logistic-normal annual size composition | C, L | MUST | 6 | missing | §2.2 forbids fixed Dirichlet latent |
| REQ-017 | Class support only at valid periods | C, P | MUST | 2, 6 | implemented (Stage 2 half) | `size_support_rows` refuses non-March |
| REQ-018 | Reconcile every draw to all hard constraints | C, P, G, L | MUST | 3, 5 | partial | `reconcile_draws` ready, no caller; baseline path passes no bounds (F-015) |
| REQ-019 | Retain joint posterior draws | C, L | MUST | 5 | missing | `PosteriorDraws` type exists |
| REQ-020 | Balanced integerization | C, P, G | MUST | 3 | implemented | `integerize`; bounded arms unexercised |
| REQ-021 | Realistic pseudo-suppression | L, C, P, G | MUST | 4 | partial | 9/13 regimes score; steps 3, 6, 8 not on scoring arm (F-002, F-003) |
| REQ-022 | Separate rolling forecasts and retrospective smoothing | P, L | MUST | 4 | diverged | `rolling_origin` scores 0; `retrospective_smoothing` switched off; ticked as closed by Stage 4 (F-004) |
| REQ-023 | Point, probabilistic, constraint metrics | L, P, C | MUST | 4 | partial | 5 point, 3 bound, 4+3 probabilistic, 3 constraint of §13.5–13.8's ~25 (F-005) |
| REQ-024 | Complexity must outperform baselines | all | MUST | 4, 5 | partial | scoreboard yes; gate keys read by no code |
| REQ-025 | Sensitivity and ablation variants | L, P, C | MUST | 7 | missing | |
| REQ-026 | Disclosure flags and release actions | L, P | MUST | 2, 8 | partial | two flags; six release actions absent |
| REQ-027 | Never auto-release exact reconstructions | L, all | MUST | 8 | missing | nothing releases yet; 0 exact cells on D1 |
| REQ-028 | Full provenance and run manifests | C, L | MUST | 1, 8 | partial | four per-command manifests; no `run_manifest.json`; §18.1's code commit / lock hash / crosswalk version absent; two commands write none (D-057, F-011) |
| REQ-029 | Fail closed | all | MUST | 1, 2, 5, 8 | partial | schema/code/cross-tab/universe/infeasible yes; `SolverError` untested; model/governance later |
| REQ-030 | Rebuild from a clean environment | C, L | MUST | 8 | missing | suite itself not green in a clean clone (F-010) |
| INV-001 | Disclosed cell preserved exactly | L, C | invariant | 2 | implemented | `fix\|…` rows; golden |
| INV-002 | Hard constraints satisfied by every estimate and draw | all | invariant | 3, 8 | partial | residual half exact; per-cell bounds half unenforced on baseline path (F-015) |
| INV-003 | No suppression-coded zero as true zero | C, P, L | invariant | 1 | implemented | |
| INV-004 | Every restriction labelled (five classes) | C | invariant | 2 | partial | rows labelled; anchor labelled in prose only; three classes have no producer (D-061) |
| INV-005 | Only public facts enter the feasible set | L, C | invariant | 2 | implemented | `is_hard` chokepoint; complement currently empty |
| INV-006 | Rounded → intervals; noisy → measurement models | C, P, L | invariant | 2, 5–6 | partial | rounding row unreachable in production; measurement models later |
| INV-007 | Never stack incompatible vintages silently | C, P, L | invariant | 1, 2 | partial | four narrow guards; cross-period release vintage and size-file-vs-monthly vintage unguarded (D-031, F-017) |
| INV-008 | Feasible vs posterior never relabelled | L, C | invariant | 2, 5 | missing | untestable until a posterior exists |
| INV-009 | Real suppression type `unknown`; labels only synthetic | L, C | invariant | 1, 4 | implemented | `assert_declared_provenance`; every real row `unknown` |
| INV-010 | Firm size never relabelled establishment size | C, P | invariant | 1 | stubbed | guard uncalled until Stage 7 |
| INV-011 | March bound not imposed outside its period | C, P | invariant | 2, 6 | implemented (Stage 2 half) | |
| INV-012 | Every draw reconciled before summaries | C, P | invariant | 5 | missing | |
| INV-013 | Joint draws retained | C, L | invariant | 5 | missing | |
| INV-014 | Complex model not promoted unless it beats baselines | all | invariant | 4, 5 | partial | |
| INV-015 | Identification, estimation, permission separate | C, L | invariant | 8 | missing | §14.1 fields in no contract |
| INV-016 | Clean environment reproduces a release | C, L | invariant | 8 | missing | |
| SRC-QCEW-001–004 | Ingest raw, parse disclosure first, expand months, retain fields | C, P | MUST | 1 | implemented | |
| SRC-QCEW-005 | Distinguish preliminary and final | C, P | MUST | 1 | partial | `release_status` is a stamped literal, not parsed; all D1 quarters final |
| SRC-QCEW-006 | Verify state/national universe; residual cells or decline | P (explicit), C | MUST | 0, 1, 2 | implemented (`decline`) | anchor gate on establishments substitutes for the employment identity |
| SRC-QCEW-007 | Test definitional alignment before a constraint | C | MUST | 0, 1, 2 | implemented | `assert_definitional_alignment` |
| SRC-QSIZE-001 | Retain March classification definition | C, P | MUST | 1 | implemented | by prose/`reference_month`; no definition field |
| SRC-QSIZE-002 | Verify simultaneous dimensionality from contents | C, P | MUST | 0, 1 | implemented | `assert_no_state_industry_size`; Stage 0 `false` |
| SRC-QSIZE-003 | National size totals hard only for compatible Q1/March fields and vintage | C | MAY | 2, 6 | partial | release-vintage condition unchecked; Q1-vs-March ambiguity |
| SRC-QSIZE-004 | State-sector size never relabelled | C, P | MUST | 1 | implemented | |
| SRC-CBP-001 | Discover NAICS predicate and official EMPSZES from metadata | C, P, G | MUST | 0, 1 | partial | predicate yes; official crosswalk route unfetched (D-060) |
| SRC-CBP-002 | Preserve EMP, ESTAB, flags, noise ranges, LFO, dropped status | C, P | MUST | 1 | partial | `EMP_N_F` (the noise band) dropped at parse (D-026) |
| SRC-CBP-003 | Store regime by year; fail closed on unknown | C, P | MUST | 0, 1 | implemented | |
| SRC-CBP-004 | CBP as March-centred noisy measurement | C, P, G | MUST | 3, 6 | partial | intensity baseline yes; measurement model Stage 6 |
| SRC-CBP-005 | CBP size counts inform shares; universe difference in the model | C | MAY | 6 | missing | |
| SRC-FOR-001–004 | TPO/FIA fields, errors, vintages, no interpolation | C, P, G | MUST | 0, 7 | missing (Stage 0 verdicts done) | |
| SRC-OTH-001 / 004 | SUSB semantics; nonemployer excluded | C, P | MUST | 1, 7 | stubbed | guards uncalled |
| SRC-OTH-002 / 003 | BDS detail discovered; CES vintages retained | C, P, G | MUST | 0, 7 | missing (Stage 0 verdicts done) | |
| SRC-OTH-005 | BEA bridged explicitly | C, P | lowercase must | none | deferred (D-001) | out of scope per D6 |
| CON-001–005 | Graph, components, ranks, provenance, cache | L | unstated | 2 | implemented | CON-005 cache key precision brittle (D-034) |
| R-§7-pre | Every table includes `run_id` and a schema version | S | MUST | none | missing | no table carries either |
| R-§9.3 | No assumed disclosure threshold may be hard | L, P (contra G) | MUST NOT | 2 | implemented | negative exit criterion with tests |
| R-§10-pre | Baselines use the same bounds and reconciliation layer as the model | C, L | MUST | 3 | diverged | baseline path unbounded (F-015) |
| R-§10.9 | Composition visible per cell; one fallback construction; typed units | S (plan 9) | MUST | 3 (post hoc) | implemented | `EmployeeWeights`; manifest `weight_basis_counts` |
| R-§12.4 | Weighted quadratic must be versioned and validation-tested | C | MAY/must | 3 | stubbed | value accepted, refused by nothing (D-041) |
| R-§13.2 | Random masking alone prohibited | L, P | prohibition | 4 | implemented | `_refuse_a_random_mask_only_design` |
| R-§13.2-3/6/8 | Complementary-like partners; reject exactly recoverable; score labels separately | L | steps | 4 | partial | implemented as functions with no harness caller (F-002, F-003) |
| R-§13.8-decl | Decline counts by kind per method per regime with denominator | S (plan 9) | MUST | 4 | implemented | `decline_and_basis_report` |
| R-§16.1-man | Every command writes a manifest and is idempotent | S | MUST | 1, 8 | partial | 7 of 9 commands write one (D-057, D-059) |
| R-§18.3 | Eight fail-closed conditions | all | MUST | 1, 2, 5, 8 | partial | five have code and tests; `SolverError` untested; three belong to later stages |


## 3. Traceability matrix (Phase 2)

### 3.1 The frontier (Phase 2a)

**What is done (observed).** Stages 0–4 have shipped code that runs end to end on the pilot window: `fetch → build-harmonized → build-constraints → solve-bounds → run-baselines → reconcile → validate`. The harmonized layer (`data/staged`, 4 tables, 47 snapshots), the identification run (`runs/f03023ac9f3a`: 4,775 bounds rows, 3 constraint components per March, `constraint_set_hash 6856d99b…`), the baseline run (12,270 rows, 10 estimators, drift 4.5e-13) and the validation run (12,530 scored rows, 4,530 metric rows, a 270×13 scoreboard at `d4e1187b…`) all reproduce from `config.yaml` on this machine. I re-derived the headline counts from the staged layer rather than quoting them: 4,716 state cells, 1,227 suppressed (share 0.2602), 14 partially identified national size cells, 0 exact and 1 narrow flag — every figure the stamps cite matches.

**What is in progress or half-wired at the frontier (observed).** The `validate/` package is the frontier and it is internally coherent — one entry point, frame-level masking, typed leakage errors, schema-and-nullity gates on all three persisted tables — but it carries four *implemented-and-unwired* mechanisms that the roadmap and the stamp describe as delivered content of §13: `complementary_partners` (§13.2 step 3), `is_exactly_recoverable` and `mask_and_solve_size`/`apply_size_mask` (§13.2 steps 5–6 on the size arm), and `cbp_size_gap_keys`/`apply_cbp_gap` (§13.3's CBP-gap regime). Each has unit tests and zero production callers (`grep` of `src/` returns only definitions and docstrings). The harness's `rolling_origin` branch runs a guard that, by its own comment (`harness.py:137-141`), cannot fail on its composition, and scores nothing. Two of thirteen required regimes therefore score zero rows with an honest manifest reason, two are switched off, and nine score — all on one arm, all primary-like.

**Is it a clean place to continue from?** Mostly yes for code, no for the record. The package boundary is clean (nothing outside `validate/` imports its internals except `cli.py`), there is no scaffolding reachable from production paths, and the acceptance artifact is current in content (the only commit after its mtime, `c4bbf4e`, changed a write-time gate and docstrings; verified by diff). The problem is that a Stage 5 planner reading the roadmap's Stage 4 Exit line, the spec's §13, or the phrase "REQ-022 closed" would believe things the tree does not support (F-002 to F-005). The frontier is therefore clean to *build on* and unsafe to *plan from* until the record is corrected.

**Stage 5 readiness beyond the harness.** `reconcile_draws` and `PosteriorDraws` exist with unit tests and no caller; `scale_into_bounds` is reachable only through them; `Bounds` treats an absent `upper` key as +∞ and an absent `lower` key as a bare `KeyError` (F-018); `PromotionConfig`'s three thresholds are read by nothing; the `model:` block of Appendix A is rejected by `Config`; and `jax`/`numpyro`/`arviz` are absent from `pyproject.toml` and `uv.lock` (the D4 wheel check was done 2026-09-05 and recorded in plan 2, so adding them is a lock change, not a research question).

### 3.2 Requirement → implementation → tests (Phase 2b)

The per-family tables below carry every requirement row whose status is anything other than `implemented`; `implemented` rows (with the test that would fail if the requirement broke) are listed compactly at the end of each family. Full subagent traces, including the `implemented` rows' test names, are in Appendix 9.6. Status counts by family:

| Family | implemented | partial | diverged | stubbed | missing | deferred | not-this-stage |
|---|---|---|---|---|---|---|---|
| ingest / harmonize / build / fetching / store / registry | 19 | 13 | 5 | 0 | 0 | 2 | 3 |
| constraints + disclosure flags | 26 | 3 | 6 | 0 | 0 | 0 | 2 |
| reconcile | 12 | 4 | 4 | 1 | 0 | 0 | 4 |
| baselines | 14 | 7 | 1 | 0 | 0 | 1 | 1 |
| validate | 34 | 10 | 3 | 4 | 7 | 2 | 6 |
| cli / config / contracts / runs / errors | 22 | 16 | 5 | 0 | 3 | 0 | 10 |

**Ingest, harmonize, build, fetching, store, registry (Stage 1).**

| Requirement | Implementing | Tests | Status | Note |
|---|---|---|---|---|
| D5 / §5.4 dual-route QCEW | `fetching.py:103-118`, `qcew.py:74-125` | `test_qcew_routes.py` (5 tests incl. `test_every_window_year_still_routes_to_the_slice_endpoint`) | diverged | `probe_slice_boundary`'s candidate range ends at `min(window)`, so `route_for_year` returns `"slice"` for every window year by construction; `read_bulk_zip` has no caller; `build_harmonized` globs `*.csv` only. Roadmap Stage 1 Produces still says "both QCEW acquisition routes … selected by reference year" (D-049, F-008) |
| §7.2 `source_snapshot` ↔ harmonized `snapshot_id` | `store.py:84` (sha256) vs `build.py:177,192,220` (`path.stem`) | none joins the two | diverged | harmonized rows carry `'2017q1'`; the manifest carries the digest; no key joins them (F-019) |
| §7.2 `source_publication_date` | `fetching.py:133,154,184` write `""` | none | partial | never populated |
| §7 preamble: `run_id` + schema version on every table | — | — | missing | no table carries either; `BUILDER_VERSION` unstamped (D-059) |
| §8.6 nine versioned dimensions; §3.1 memo; `source_registry` table | `harmonize/dimensions.py:28`, `classification.py:46`, `registry/loader.py:21` | unit tests on each builder | partial | builders have zero callers and no artifact on disk (D-058); roadmap Stage 1 Produces claims all three |
| §3.1 mechanical crosswalk verification | `harmonize/naics.py:135-165` | 4 tests in `test_harmonize.py` | partial | runs only in tests; no build step or command calls it |
| SRC-CBP-001 official `EMPSZES` crosswalk | `cbp.py:92-111` `discover_empszes`, `EMPSZES_URL` | `test_cbp.py::test_2017_size_codes_come_from_the_official_values_crosswalk` | partial | route unfetched and uncalled in production; parser reads `EMPSZES_LABEL` from the response (D-060) |
| SRC-CBP-002 preserve noise ranges | `cbp.py:273` | schema tests | partial | `employment_noise_range ← EMP_N` is `'0'` on every row; `EMP_N_F` (the real band) dropped at parse (D-026) |
| SRC-QCEW-005 preliminary vs final | `fetching.py:150,180` literal `"final"`; `build.py:179` from config | `test_qcew_parser.py:253-255` (column presence) | partial | stamped, not parsed; never exercised on D1 |
| §16.1 manifest for `validate-config`, `registry verify`, `build-harmonized` | `cli.py:28-59, 77-92` | none | partial | three of four Stage 1 commands write nothing (D-057, D-059 — the tracking item misstates `build-harmonized`) |
| §18.3 source fetch failure | `fetching.py:119-120,140-141,162-163,170-171` `continue` | `test_fetching.py` serves 200 only | diverged | non-200 or empty body is dropped with no record, no error (F-020) |
| §6.2 layout and no-re-download rule | flat `data/staged/`, `runs/source_manifest.parquet` at root; `fetch_source` always GETs | — | diverged | undocumented |
| `HarmonizedData.load` | `contracts.py:679-690` | — | partial | loads four Parquets without `validate_frame`; raises builtin `FileNotFoundError` |
| INV-010 / SRC-OTH-001 / SRC-OTH-004 guards | `harmonize/concepts.py` | `test_harmonize.py` | stubbed | uncalled by design until Stage 7; now documented (D-068) |

Implemented with a discriminating test: SRC-QCEW-001–004 (`test_qcew_parser.py` incl. `N`-coded zero → null, three monthly rows, `area_fips` string), SRC-QCEW-006/007 (`test_universe.py`, `test_constraint_rows.py:57,77`), SRC-QSIZE-002/004 (`test_qcew_size.py:36,181`), SRC-CBP-003 (`test_disclosure_regime.py::test_2024_halts_the_run`), INV-003, INV-009 (every real row `unknown`), REQ-004 (`test_store.py`, `test_fetching.py::test_manifest_writing_is_deterministic`), REQ-008 (bridge fields), the offline byte-identical rebuild (`test_build_harmonized.py::test_rebuild_is_byte_identical`, `::test_rebuild_attempts_no_network_call` — on a three-file fixture, not the full window), D3 (no secret in any manifest, `test_store.py`).

**Constraints and disclosure flags (Stage 2).**

| Requirement | Implementing | Tests | Status | Note |
|---|---|---|---|---|
| §9.6 step 2 (MILP when integer feasibility can change the result) | `bounds.py:323-340` `_needs_milp` | `test_national_size_margin_golden.py:147` | diverged | re-solve only when some LP width `< 25`; a wide fractional LP interval on an integer cell ships as-is (F-014). Latent on D1 (all coefficients ±1) |
| §5.5 size-margin gate, employment concept | `compat.py:110-140` | `test_constraint_compat.py` | partial | `observed_employment` is aggregated and never compared; gate rests on establishments only; header says so but not that employment is never checked (F-017) |
| SRC-QSIZE-003 release-vintage clause | `compat.py:120` join on `reference_month` only | — | partial | by-size table carries no `release_vintage`; two snapshots merge into one row unguarded |
| §9.2 atomic key with `release_vintage` | `cells.py:3-15` omits it deliberately | — | diverged | recorded in the module docstring and D-031; §9.2/§7.7 unamended |
| §9.4 rounding interval | `rows.py:458-501` closed interval | one §17.2 property | diverged (benign) | conservative widening; no D1 field is rounded; unreachable in production |
| §9.7 quarantine | `bounds.py:344` `quarantined=()` | tests only | partial | no CLI path; unrecorded |
| §9.7 diagnostic tolerances | `diagnostics.py:62` accepts `config`, never reads it | — | partial | HiGHS defaults; coincide with 1e-7 today |
| §9.8 six classes | `bounds.py:291-297` emits four | `test_bound_status.py::test_stage_two_never_emits_a_model_dependent_status` | diverged (documented, correct) | |
| INV-004 closed-set refusal | `rows.py:129-134` | none passes an unknown value | implemented, unpinned | deleting three guards leaves 119 tests green |
| `BOUND_STATUSES` / `solver_status` closed sets | declared `contracts.py:188` | — | partial | not enforced by `assert_declared_provenance` |

Implemented with a discriminating test: §17.2's eight named properties (`test_constraint_properties.py:90-227`, fixed examples not generated tables — see F-024), CON-001–005 (`test_constraint_graph.py`, `test_constraint_rank.py`, `test_constraint_index.py` list-equality guard), INV-001 (`test_constraint_golden.py`, hand-derived `[400,530]`/`[250,380]`), INV-005 (`bounds._hard_rows` chokepoint tests), INV-011 (`test_constraint_rows.py` non-March refusal), §9.3 assumed-threshold refusal (`test_constraint_rows.py:103`, `test_d1_acceptance.py:700`), §9.7 halt (`test_constraint_diagnostics.py:132` — the IIS assertion is a disjunction), `constraint_set_hash` gate (`test_constraint_cli.py::test_solve_bounds_refuses_inputs_that_did_not_produce_the_constraint_tables`), §9.8 flags (`test_disclosure_flags.py`, `test_d1_acceptance.py:298-452`).

**Reconcile (Stage 3).**

| Requirement | Implementing | Tests | Status | Note |
|---|---|---|---|---|
| §12.2 "compatible national total" | `anchor.py:156-229` establishment-closure gate; `anchor_basis='declared_national_total'` | `test_anchor.py` (9) | diverged (documented in code + roadmap, not in §12.2) | the substitute anchor; the employment identity remains `decline` (F-006) |
| §10 preamble / INV-002 per-cell bounds | `runner.py:253` `allocate(anchor, outcome)`; `:277` `integerize(..., total=)` — no bounds | `test_d1_baselines.py:57-70` (sum + non-negative only) | partial | baseline path never reads `deterministic_bounds`; `scale_into_bounds` reachable only via uncalled `reconcile_draws` (F-015) |
| §12.5 with bounds | `matrix.py:75-76` hardcodes `lower=0, upper=+inf` | — | partial | no bounds parameter; roadmap lists §12.5 as shipped (F-016) |
| §12.4 weighted quadratic | `projection.py:41-53` guard; zero callers | `test_projection.py` calls the guard directly | stubbed | `general_method: weighted_quadratic` validates, re-ids the run, is refused by nothing (D-041) |
| `Bounds` key handling | `scaling.py:37-46` | — | partial | absent `upper` → +∞ silently; absent `lower` → bare `KeyError` (F-018) |
| §16.2 `reconcile_draws` signature | `draws.py:74-78` takes `ReconciliationInputs` | `test_reconcile_draws.py` | diverged (recorded in roadmap Stage 5 block; §16.2 unamended) | better choice |
| Appendix A reconciliation block | `config.py:111-135` 8 keys, 5 originated; 4 read by no code | — | diverged (partly recorded) | |
| INV-004 label on the anchor | prose only (`anchor.py:27`) | `test_anchor.py` asserts the basis string | partial | `anchor_basis` names the source, not the INV-004 class |

Implemented with a discriminating test: §17.3 properties 1–7 plus 3b/7b and a tolerance parametrisation (`test_reconcile_properties.py:85-281`, seeded generator, 200 trials); `allocate`'s domain refusal before the empty-set shortcut; `integerize` bounds and tie rule (`test_integerize.py`, 7 tests); `kl_project` violation never increases; `reconcile_matrix` pre- and post-checks; `reconcile_draws` never reduces the draw axis and refuses a negative draw. Four fail-closed arms in `anchor.py`/`allocate.py` survive mutation (the reconcile subagent's `/tmp` mutant runs, 160 tests green under each): negative-residual halt, exactly-one-national-row, the `anchored` term, and the missing-basis refusal (F-025).

**Baselines (Stage 3).**

| Requirement | Implementing | Tests | Status | Note |
|---|---|---|---|---|
| §10.4 robust intensity shrunk toward regional/national | `intensity.py:64-83` plain ratio, `n/(n+5)` to national | `test_baselines_intensity.py` (6) | partial | no regional tier, no robust estimator, no historical term; shrink form recorded, omissions recorded nowhere (F-026) |
| §10.8 rung 1 "with robust historical adjustment" | `FALLBACK_ORDER[0] = 'cbp_intensity'` | `test_baselines_runner.py:91-95` (membership only) | partial | reinterpreted by §10.9 as precedent for composition; the historical term is absent and unrecorded |
| §10.8 selection logic | `runner.py:353-387` | membership/truthiness tests only | implemented, unpinned | reversing `FALLBACK_ORDER` leaves the suite green; `preferred_estimator_by_month` read by no test |
| §10.3 classification-consistent periods | `historical.py:102-103` behind `historical_may_cross_naics_vintage` | 2 tests | diverged (recorded) | a config toggle can violate a MUST and re-ids the run |
| §10.5 harvest | `harvest.py:27-47` declines by design | 4 tests | deferred (Stage 7) | decline reason cites config keys `Config` cannot hold |
| §10.6 constrained regression | `regression.py` | 4 tests + T-4 | partial | `MINIMUM_TRAINING_ROWS=3` undocumented; model form originated and recorded |
| §7.13 `decline_kind` closed set | `interfaces.py:91-97`, `contracts.py:242` | none constructs an unknown kind | implemented, unpinned | |
| R-BREAK-5 tie rule | `historical.py:235-238` | no tied fixture | implemented, unpinned | |

Implemented with a discriminating test: all ten registry members and their §10 mapping (`test_baselines_runner.py::test_the_registry_carries_every_section_10_estimator`); five distinct §10.3 numbers on one history (`test_the_five_variants_compute_five_different_numbers_on_one_history`); R-COMP-1..9 typed composition (`test_baseline_interfaces.py`, `test_baselines_fallback.py` T-1..T-7); R-COMP-8 partition/anchor cross-check; R-COMP-10 decline-by-kind (`test_baseline_cli.py::test_declines_are_broken_down_by_kind_not_pooled`); the golden (`test_baseline_golden.py`, regenerated from code — a drift pin, F-024); provenance enum enforcement (`test_contracts_validation.py`).

**Validate (Stage 4, the frontier).**

| Requirement | Implementing | Tests | Status | Note |
|---|---|---|---|---|
| §13.2 step 1 configurable propensity | `propensity.py:22-79` weights `0.5/0.3/0.2` literal; `del config` | 5 tests (data-dependent, unguarded) | partial | nothing configurable; a weight change does not change `run_id` |
| §13.2 step 3 complementary-like | `propensity.py:109-135` | `test_validate_complementary.py` (2) | stubbed | no production caller |
| §13.2 step 6 reject exactly recoverable | `recover.py:67-77`; `mask_and_solve_size` | `test_validate_exact_recovery.py` (2, one D1 March, silent skip) | partial | no harness caller; Stage 4 Exit "the harness rejects…" not enforced (F-002) |
| §13.2 step 8 score labels separately | `scoreboard.py:181-214` refuses non-primary-like | `test_validate_scoreboard.py`, `test_d1_validation.py:118` | diverged (recorded as a precondition, D-075) | steps 3/6/8 have no live content on the scoring arm |
| §13.3 `rolling_origin` | `regimes.py:338-419`; `harness.py:131-148` guard only | 6 unit + 2 acceptance | partial | scores nothing; guard cannot fail by construction (F-004) |
| §13.3 `retrospective_smoothing` | disposition `vacuous_on_registry`; switched off | 2 tests | stubbed | Appendix A ships it `true` |
| §13.3 `preliminary_to_final_vintage` | `select_targets` raises | 3 tests | deferred | no second vintage on D1 |
| §13.3 `cbp_size_gaps` | `regimes.py:485-546` | `test_validate_cbp_gap.py` (3) | stubbed | no production caller; manifest reason reports a measured effect the run never applies |
| §13.4 bullets 4–5 | — | — | deferred / not-this-stage | recorded in `leakage.py:4-7` |
| §13.5 infeasible-component rate, LP-vs-MILP tightening, "truth outside bounds is a bug" rule | — | — | missing | `bound_metrics` emits three of five; no refusal path (F-003, F-005) |
| §13.6 median APE | `metrics.py:107-111` | none | partial | nulls the whole estimator if any truth is 0 rather than the safe subset |
| §13.6 state-share / size-share AE, rank accuracy | — | — | missing | |
| §13.7 calibration by stratum and by CBP-anchor distance | — | — | missing | emitters group by estimator only; §13.10's stratum gates have no data source |
| §13.7 "rolling" residual ensembles (§10.7) | `metrics.py:154-167` cross-sectional leave-one-out within a replicate | `test_validate_intervals.py` | diverged | labelled `rolling_residual_ensemble`; not time-ordered; unrecorded (F-027) |
| §13.8 ‖Ax−y‖₁/∞, row-sum, class-margin violations | `constraint_metrics` emits negatives, integerization, anchor residual | none behavioural | missing / partial | |
| §13.10 gates | `PromotionConfig` only | `test_config_validation_block.py:27-31` (defaults equal literals) | not-this-stage | three unread floats |
| §16.2 signature | `harness.py:64-79` takes `Config` | none pins the `None` refusal | diverged (recorded) | better choice |
| `minimum_missing_set_size` | `config.py:206` | — | dead config | read by nothing; cannot be removed (run-id policy) |

Implemented with a discriminating test: frame-level masking and truth capture (`test_validate_mask.py`, `test_validate_leakage.py::test_the_partition_the_runner_derives_carries_no_held_out_truth`); typed leakage errors surviving `python -O` (`test_validate_leakage_guards.py`, subprocess); `assert_no_retained_truth` on the live path; INV-009 labelling on every scored row; `assert_declared_provenance` on every scored frame; nine scoring regimes' selectors sort before sampling (cross-process pins in `test_validate_regimes.py:106-132`, `test_validate_cbp_gap.py`); the random-mask-only refusal; `REGIME_SPECS` import-time consistency (`test_validate_regime_mechanisms.py`); the four regime switches (`test_stage4_acceptance.py:103-127`); pooled-across-seeds `preferred_baseline` restricted to §10.8 rungs with the tie rule (`test_validate_scoreboard.py`, 477 lines); CRPS closed form vs pairwise; schema + nullity gates on all three tables; `--estimators` reaching the run id with the override omitted when unset (`test_runs.py`, `test_cli_paths.py`).

**CLI, config, contracts, runs, errors (cross-cutting).**

| Requirement | Implementing | Tests | Status | Note |
|---|---|---|---|---|
| §16.1 fifteen commands | 9 exist | — | partial | `fit-state-model`, `fit-size-model`, `disclosure-review`, `publish`, `run-all` absent (Stages 5–8) |
| §16.1 manifest per command | 5 of 9 write one (`schema_`, `baseline_`, `reconcile_`, `validation_manifest`; `fetch` → `source_manifest`) | key-presence tests | partial | `validate-config`, `registry verify`, `build-harmonized`, `solve-bounds` write none (D-057, D-059) |
| §16.1 idempotence | `runs.py` + deterministic writer | in-process double invocation for three commands; cross-process only for selectors | partial | JSON manifests never compared across runs; a `datetime.now()` in any manifest passes (F-028) |
| §18.1 manifest contents | per-command JSON | — | partial | present: resolved config (build-constraints only), snapshot hashes, parser versions, schema fingerprints, constraint-set hash, solver name/version, output hashes (not for solve-bounds), seeds (in scores, not manifest); absent: code commit, lock hash, NAICS crosswalk version, model version, tolerances (validate) (F-011) |
| INV-016 / REQ-030 clean environment | — | — | partial | `python-dotenv` is dev-only while `config.py:11` imports it at module scope: a `uv sync --no-dev` install cannot run any command (F-009, verified with `uv tree --frozen --no-dev`) |
| Appendix A ≈ `config.yaml` | `config.py` `_Strict` models | `test_config.py::test_appendix_a_config_parses` uses a trimmed literal | diverged | Appendix A verbatim raises 11 errors (F-013); the test proves nothing about Appendix A |
| §7 closed sets | `assert_declared_provenance` on 5 columns | `test_contracts_validation.py` | partial | `mask_arm`, `bound_status`, `solver_status`, `INTERVAL_SOURCES` not enforced (D-082) |
| Error hierarchy | `errors.py` 17 classes | no test references `LoggingEmploymentError` | partial | 18 bare `ValueError` sites in ingest, 5 in constraints, several `KeyError`/`TypeError`/`NotImplementedError` elsewhere |
| Config keys that govern nothing | `immutable_raw`, `composite_fallback`, `max_projection_iterations`, `analysis_mode=realtime_asof` (D-064) plus `sources.*.enabled` ×3, `fail_on_unknown_disclosure_regime`, `minimum_missing_set_size`, `single_margin_method`, `integerization_tiebreak`, `PromotionConfig` ×3 | — | partial | fourteen keys fold into `run_id` and `config.resolved.yaml` with no reader; the 2026-09-07 "44-key scan" found four |

### 3.3 Divergences (Phase 2c)

Every `diverged` row above, consolidated, with where the divergence is recorded and whether the code's choice is better.

| # | Spec | Code | Recorded where | Better? |
|---|---|---|---|---|
| 1 | §12.2/§10 allocate against a compatible national total | anchor = published national total admitted by an establishment-closure gate; labelled `modeling_assumption` in prose | roadmap Stage 3 (5) "recorded nowhere else"; `anchor.py` docstring; D-004 | Yes on substance; **§12.2 should say so** |
| 2 | §9.6 MILP when integer feasibility can change the result | MILP when LP width < 25 | `config.py:99-101` calls it a performance switch; not as a divergence | No; ceil/floor tightening would restore sharpness cheaply |
| 3 | §9.2 atomic key includes `release_vintage`; size universe is state×size | key omits it; size cells national only | `cells.py:3-15`; D-031; Stage 0 stamp | Partly (follows §7.7 over §9.2; correct on D1) |
| 4 | §9.8 six statuses incl. model-estimable/model-only | four emitted | `bounds.py:291-297`; `contracts.py:186-188`; test | Yes (§9.1 forbids a model here) |
| 5 | §9.7 explicit quarantine | parameter exists; no CLI path | nowhere | Acceptable on D1; unrecorded |
| 6 | §5.5 gate evaluates employment concept, revision status… | establishment sum only; employment aggregated and never compared | `compat.py:12-17` says "rests mostly on establishments" | No |
| 7 | §16.2 `reconcile_draws(…, feasible_set: ConstraintSystem, …)` | takes `ReconciliationInputs` (Anchor + Bounds) | roadmap Stage 5 block; `draws.py` docstring | Yes; §16.2 unamended |
| 8 | §16.2 `run_pseudo_suppression(…, config: ValidationConfig)` | takes whole `Config`, `None` refused | `harness.py:69-73`; `validate/CLAUDE.md` | Yes; §16.2 unamended |
| 9 | §10 preamble "same hard bounds and reconciliation layer as the model" | baselines allocate and integerize with no bounds; draws use `scale_into_bounds` | oblique only (`allocate.py:68-70`, roadmap Stage 3 (6)) | No — fail-open when a state cell gains a finite upper (F-015) |
| 10 | §12.5 "with bounds … general convex projection" | `reconcile_matrix` hardcodes `[0, +inf)` | nowhere; roadmap says shipped | n/a until Stage 6; the claim overstates |
| 11 | §12.4 weighted quadratic "must be versioned and validation-tested" | accepted by config, refused by nothing | D-041 (open, premise corrected) | No |
| 12 | §10.4 robust, regional/national shrinkage; §10.8 rung 1 "robust historical adjustment" | plain ratio, national shrink, no history | shrink form only (`intensity.py:30-34`) | Unclear; needs a ruling |
| 13 | §10.3 classification-consistent periods (MUST) | config toggle can cross the seam | `historical.py:16-21` | Defensible as ablation lever, but a MUST-violating config should refuse or be labelled sensitivity-only |
| 14 | §10.7 intervals from *rolling* residuals | cross-sectional leave-one-out within a replicate, labelled `rolling_residual_ensemble` | nowhere | Unclear; §13.10's coverage gate would read a distribution the spec did not describe (F-027) |
| 15 | §13.2 step 8 score both labels separately | refuse the second label on the scoring arm | D-075 resolution; roadmap Stage 4 (3) | Defensible on the state arm (SRC-QCEW-006); §13.2 unamended |
| 16 | §13.6 median APE "where denominators are safe" | null whole metric if any truth is 0 | nowhere | No |
| 17 | D5 dual-route QCEW | slice route only, by construction | D-049; `ingest/CLAUDE.md` (imprecise) | Roadmap Stage 1 Produces and D5 unamended (F-008) |
| 18 | §7.2 snapshot identity = immutable retrieval | harmonized `snapshot_id` = filename stem | `ingest/CLAUDE.md` (for `release_vintage` only) | No (F-019) |
| 19 | §6.2 layout, no-re-download rule, `run_manifest.json` | flat staged dir; manifest at root; per-command manifests; always GETs | nowhere | Neutral; undocumented |
| 20 | Appendix A as reference config | `Config` rejects seven sources and `model:`; requires `baselines:` and two disclosure widths | `config.yaml` header (stale) | Fail-closed typos are right; the reference document is wrong (F-013) |
| 21 | Appendix A `include_retrospective_smoothing/vintage_comparison: true` | both `false` | `config.py:190-193`; `config.yaml:81-83` | Yes (data cannot support them) |
| 22 | §16.1 `reconcile` as a pipeline stage | a drift verifier; allocation happens in `run-baselines` | `cli.py:330-336` | Reasonable for Stage 3 |
| 23 | §6 "Python 3.11 or later" | `>=3.14` | D4 | Yes; §6 unamended |

### 3.4 Hidden incompleteness (Phase 2d)

**Systematic grep (repo-wide, `src`/`tests`/`scripts`).** `TODO|FIXME|XXX|HACK`: none. `NotImplementedError`: three sites — an abstract method (`historical.py:140`), a deliberate refusal of an unimplemented config value (`projection.py:49`, dead code), and a regime refusal (`regimes.py:316`) — all benign as code, the second tracked (D-041). `pass`/`...` bodies: one Protocol body (benign). `type: ignore`: five, all on polars `.cast(SCHEMA)` (benign). `pragma: no cover`: one (`scaling.py:100`, documented). `noqa`: three `E402` in audit scripts (documented). `skip`/`skipif`/`xfail`: nine sites, all `skipif` on data presence or a data-content condition; two are silent skips that convert the only §13.2 step-6 witnesses into green (F-002). `slow`: six sites, never deselected. `network`: declared, applied nowhere.

**Declared-but-uncalled production code (observed by grep; each has unit tests).** `registry_frame`, `dimension_frame`, `classification_memo`, `state_universe_report`, `discover_empszes`, `read_bulk_zip`, `require_supported_method`, `reject_enterprise_size`, `reject_nonemployer_in_core_total`, `reconcile_draws`, `scale_into_bounds`, `reconcile_matrix`, `kl_project`, `rounding_interval_row`, `is_exactly_recoverable`, `mask_and_solve_size`, `apply_size_mask`, `complementary_partners`, `cbp_size_gap_keys`, `apply_cbp_gap`, `preferred_estimator_by_month` (written to a manifest, read by nothing). Tracked: 13 of 21 (D-041, D-049, D-058, D-060, D-063, D-068, D-071, roadmap Stage 5/6 blocks, `reconcile/CLAUDE.md`). Untracked: `preferred_estimator_by_month` (no consumer), the Stage 6 dependence on `reconcile_matrix` lacking bounds (F-016).

**Config keys with no reader (observed by grep).** Fourteen: `storage.immutable_raw`, `sources.qcew.enabled`, `sources.qcew_size.enabled`, `sources.cbp.enabled`, `sources.cbp.fail_on_unknown_disclosure_regime` (the build raises regardless), `reconciliation.single_margin_method`, `reconciliation.max_projection_iterations`, `reconciliation.integerization_tiebreak`, `baselines.composite_fallback`, `validation.minimum_missing_set_size`, `validation.include_random_mask_sanity_check`, `promotion.*` ×3; plus `project.analysis_mode=realtime_asof` which validates and is ignored. Every one folds into `run_id` and `config.resolved.yaml`. Tracked: four (D-064). Untracked: ten.

**Hardcoded values that belong in config or a declaration.** Propensity weights `0.5/0.3/0.2` (`propensity.py:75-77`; §13.2 says "configurable"); `DEFAULT_SHRINK_STRENGTH = 5.0` (documented as a decision); EWMA decay `0.5**(1/12)` applied per observation, not per month (contradicting the module's own argument); `MINIMUM_TRAINING_ROWS = 3` (no rationale); `_BRIDGE_ROWS` valid_start/end literals duplicating `project.start_month/end_month`; `DISCLOSED_STATUSES` retyped from `OBSERVATION_STATUSES`; CBP `naics_vintage` stamped from QCEW's era rule, "documented-not-measured" (`cbp.py:3-7`).

**Dated witnesses in code (the project's own risk category).** 27 `measured YYYY-MM-DD` notes in `src/`, ten `CORRECTED …` markers in `validate/CLAUDE.md`, 14 in `regimes.py` alone, two reason strings that ship into the run manifest carrying `2026-09-08`, and a test that pins that date (`test_stage4_acceptance.py:281`). Six D1 state enumerations survive as literals in `interfaces.py`, `historical.py`, `config.py` after the same pattern was removed from `intensity.py` (D-062). §7.14 of the *spec* now carries a dated measurement as the justification for a MAY.

**Fixture or test data reachable from production.** None found. Production never reads `tests/fixtures`; the one reverse coupling is that seven unit modules and two integration modules read the gitignored `data/staged` with a cwd-relative path and no guard (F-010).

### 3.5 Verification run (Phase 2e)

All commands are the project's own (`CLAUDE.md`, `pyproject.toml`); outputs are verbatim tails. Run from the repo root at `c4bbf4e` with `data/` and `runs/` present.

| Command | Result | Time |
|---|---|---|
| `uv run pytest -q -p no:cacheprovider` | **1356 passed, 0 failed, 0 skipped** | 7:00 wall, 665 % CPU (polars threads; no `pytest-xdist` installed) |
| `uv run ruff check src tests` | All checks passed (415 enabled rules; `pyproject.toml` declares no `select` — provenance of the rule set is an open question, Q-12) | <1 s |
| `uv run ruff format --check src tests` | 171 files already formatted | <1 s |
| `uv run interrogate src` | PASSED, 100.0 % (min 100.0 %) | <1 s |
| `logging-estimates validate-config --config config.yaml` | `OK: 113310 / private / states_dc / 2017-01..2024-12` | |
| `logging-estimates registry verify --config config.yaml` | `OK: registry verified` | |
| `uv lock --check` | Resolved 38 packages (lock current) | |
| Type checker | **none configured** (no mypy/pyright in `pyproject.toml` or `uv.lock`; §6 asks for static typing) | |
| Coverage | **not configured** (no `pytest-cov`, no `[tool.coverage]`) | |

Zero skips with `data/` present means the skip counts in `CLAUDE.md` ("26 skipped" without `data/`) describe a different environment; on a clean clone the suite is red by construction (F-010), so "green" is a property of this machine.

**Tests that pass for the wrong reason (verified by reading each).**
- `test_validate_leakage.py::test_every_estimator_is_invariant_to_the_held_out_value` — its own docstring concedes the two masked frames are byte-identical, so it cannot detect an estimator that reads the truth; it also runs `REGISTRY[:4]` of 10.
- `test_validate_exact_recovery.py` (both tests) — the only witnesses of §13.2 steps 3 and 6, resting on the single March with zero suppressed classes (2017-03); any revision converts them into a silent `pytest.skip`.
- `test_stage4_acceptance.py::test_the_rolling_origin_entry_records_the_origins_its_guard_checked` — asserts `origins_checked == []` on the fixture; the live guard is exercised only in a slow, skipif'd test and cannot fail by construction.
- `test_validate_cli.py::test_validate_is_idempotent_for_identical_inputs` and its two siblings — both invocations run in one process; the repo's own docstring (`test_validate_regimes.py:97-104`) says within-process repeats hide unordered-frame nondeterminism.
- `test_baseline_golden.py::test_the_golden_fixture_is_tracked_in_git_not_rebuilt_from_ignored_data` — uses `Path.exists()`, which a gitignored file satisfies.
- `test_identity_rule.py::test_branch_is_always_exactly_one_of_three` — parametrised with two of the three branches; `decline`, the branch that actually occurred, is never produced.
- Twelve prose-pin tests assert that sentences exist in docstrings or source text (list in Appendix 9.7); several say so themselves.
- Goldens for baselines and validation metrics were regenerated from the code under test (commits `a64eba5`, `0571e15`) with a documented reason but no independent oracle; only the constraint and national-size goldens carry hand-derived values.

**Coverage concentration.** Risk that is well covered: the SRC-QCEW-006 consequences (no state-sum row can be built), the anchor gate, the mask-lives-in-the-frame property, the retained-truth guard under `-O`, the selector determinism across processes, the provenance closed sets on the baseline path, the `constraint_set_hash` gate between stages. Risk that is not covered: `SolverError` (zero tests), the `reconcile` exit-1 branch, INV-002's per-cell-bounds half on the production path, any cross-process idempotence of a CLI command's outputs, every §13.5–13.9 metric the harness does not emit, §17.4 rows 5–8, §17.5 in its entirety, §18.2 in its entirety.


## 4. Deferred-item ledger (Phase 3)

### 4.1 Inventory (Phase 3a)

All 84 checkboxes in `specs/deferred_items.md` were extracted by script (line, section, tick state), dated by `git log -S` on the title (creation) and `git blame` (last change), and read in full by me. D-ids are assigned in file order. Three subagents produced independent inventories of the three line ranges; their per-item notes (hops, rewrites, stale pointers) agree with mine and are reconciled below. Twelve further subagents then verified every one of the 45 ticked items against code and tests; I re-checked by hand every item that bears on a High finding (D-004, D-040, D-071, D-073, D-074, D-075, D-076, D-077, D-079) and every item the verifiers flagged as narrowed.

**Verified-status totals.**

| Status | Count | D-ids |
|---|---|---|
| resolved (code + discriminating test located) | 39 | see table |
| resolved with scope shrinkage (resolution narrower than the original ask; recorded inline) | 4 | D-002, D-005, D-024, D-076 |
| superseded (mooted by a documented design change) | 2 | D-023 (black removed; D4 amended), D-045 (collapse pinned as intentional, then redesigned by plan 10 → D-050) |
| open, on schedule — target stage not reached | 7 | D-001 (retirement), D-003, D-017, D-020 (Stage 7), D-026, D-031, D-041 (Stage 6) |
| open, on schedule — trigger condition not met | 10 | D-022, D-025, D-027, D-028, D-029, D-033, D-034, D-072, D-083, D-084 |
| open, overdue — originating stage done and no target, or target stage done | 22 | D-019, D-030, D-032, D-036, D-048, D-049, D-055, D-056, D-057, D-058, D-059, D-060, D-061, D-063, D-064, D-065, D-066, D-071, D-078, D-080, D-081, D-082 |
| re-deferred | 1 (counted in overdue) | D-071 — named in plan 12's `Closes:` line and then explicitly not closed (one hop) |
| silently dropped | **0** | scripted title diff over all 38 commits: no title removed without same-commit replacement, no `[x]`→`[ ]` reversion; one title rewrite (`e34ef16`, "gate nothing" → "gate no regime selection") with the reason in the commit body |

The full 84-row table follows. `Verification evidence` for ticked items is the verifier's code and test pointer (abridged) and whether the resolution was written back into the spec or roadmap.

| D-id | Line | Title (abridged) | Origin | Created | Target / trigger | Affects | Status (verified) | Verification evidence / note |
|---|---|---|---|---|---|---|---|---|
| D-001 | 9 | SRC-OTH-005 — BEA detailed state-industry employment bridge. | -roadmap derivation | 2026-09-03 | roadmap retirement | SRC-OTH-005 | open, on schedule |  |
| D-002 | 35 | The no-retabulation premise is carried by no cited source. All eight | 1-stage0- | 2026-09-04 | — | INV-007/§3.1 | resolved-with-scope-shrinkage | OBSERVED: src/logging_employment/harmonize/naics.py:27-52 carries the BLS Q&A quotation (' / OBSERVED: no test asserts the citation text (a comment cannot be pinne — write-back: NOT written back. grep of specs/logging- |
| D-003 | 63 | Appendix A vs the forest-source verdicts. `specs/logging-employment-spec.md` A | 1-stage0- | 2026-09-04 | Stage 7 | Appendix A/§5.2 | open, on schedule |  |
| D-004 | 69 | Stage 3 needs a substitute allocation anchor. `SRC-QCEW-006` came back | 1-stage0- | 2026-09-04 | — | §12.2/SRC-QCEW-006 | resolved | OBSERVED: src/logging_employment/reconcile/anchor.py:52 DECLARED_NATIONAL_TOTAL = 'declare / OBSERVED: tests/unit/test_anchor.py::test_the_residual_is_the_national — write-back: Roadmap: YES — specs/logging-employment- |
| D-005 | 87 | `cbp_metadata.lfo_by_year` is null for all eight window years — the one | 1-stage0- | 2026-09-04 | — | SRC-CBP-002 | resolved-with-scope-shrinkage | OBSERVED: src/logging_employment/ingest/cbp.py:114-130 build_query selects 'LFO,LFO_LABEL' / OBSERVED: tests/unit/test_cbp.py::test_the_query_selects_lfo_label_as_ — write-back: NOT in spec or roadmap. specs/logging-em |
| D-006 | 100 | `cbp_regime.unknown_years = [2024]`. CBP's 2024 disclosure regime is | 1-stage0- | 2026-09-04 | — | SRC-CBP-003 | resolved | OBSERVED: src/logging_employment/harmonize/disclosure.py:23-31 CBP_REGIME_BY_YEAR records  / OBSERVED: tests/unit/test_disclosure_regime.py::test_2024_halts_the_ru — write-back: Spec: YES — the Stage 1 stamp at specs/l |
| D-007 | 118 | `scripts/audit/qcew_identity.py`: two sets named by predicates that | 1-stage0- | 2026-09-04 | — |  | resolved | OBSERVED. Half 1 (rename): scripts/audit/qcew_identity.py:98-105 defines `NO_DISCRIMINATIN / OBSERVED. tests/audit/test_identity_rule.py::test_a_withheld_non_state — write-back: NOT written to spec or roadmap. `grep -n |
| D-008 | 133 | `scripts/audit/qcew_panel.py`: `emplvl_raw_nonzero_rows` uses | 1-stage0- | 2026-09-04 | — |  | resolved | OBSERVED. scripts/audit/qcew_panel.py:285-288 now computes `emplvl_raw_nonzero_rows=(pl.co / OBSERVED. tests/audit/test_panel_flags.py::test_an_unparseable_raw_val — write-back: NOT written to spec or roadmap. `grep 'e |
| D-009 | 145 | `scripts/audit/qcew_panel.py`: `build_panel` and `main` are two independent | 1-stage0- | 2026-09-04 | — |  | resolved | OBSERVED. scripts/audit/qcew_panel.py:186-197 defines `class PanelBuild(NamedTuple)` with  / OBSERVED. tests/audit/test_panel_flags.py::test_the_panel_and_the_long — write-back: NOT written to spec or roadmap. `grep 'P |
| D-010 | 154 | `scripts/audit/qcew_routes.py`: the multi-year bulk-disagreement branch is | 1-stage0- | 2026-09-04 | — |  | resolved | OBSERVED. Commit c075e33 (2026-09-04 18:52:22 -0400) extracted `column_parity` from `main( / OBSERVED. tests/audit/test_qcew_routes.py::test_identical_is_false_whe — write-back: NOT written to spec or roadmap. `grep 'b |
| D-011 | 170 | `html_title` exists in three byte-identical copies (`cbp_metadata.py`, `bds_de…` | 1-stage0- | 2026-09-04 | — |  | resolved | OBSERVED: single definition at scripts/audit/_common.py:109 (`def html_title(body: bytes)  / OBSERVED: tests/audit/test_common.py::test_html_title_reads_the_title_ — write-back: NOT written to spec or roadmap: grep for |
| D-012 | 180 | `scripts/audit/cbp_metadata.py`: three request sites remain unguarded by | 1-stage0- | 2026-09-04 | — |  | resolved | OBSERVED: `fetch_json_or_none` at scripts/audit/cbp_metadata.py:278-314 — catches HTTPStat / OBSERVED, all pass under `-p no:cacheprovider -o addopts=""`: tests/au — write-back: NOT written to spec or roadmap: grep for |
| D-013 | 194 | `scripts/audit/verify_extracts.py`: `enabled.setdefault(current, False)` | 1-stage0- | 2026-09-04 | — |  | resolved | OBSERVED: scripts/audit/verify_extracts.py:572 `enabled: dict[str, bool \\| None] = {}`, :58 / OBSERVED, both pass: tests/audit/test_verify_extracts.py::test_parse_a — write-back: NOT written to spec or roadmap: grep for |
| D-014 | 203 | `scripts/audit/verify_extracts.py`: `classification_block`'s `Raises:` | 1-stage0- | 2026-09-04 | — |  | resolved | OBSERVED: scripts/audit/verify_extracts.py:466-497 docstring — :482-485 states the closing / OBSERVED, passes: tests/audit/test_verify_extracts.py::test_an_unclose — write-back: NOT written to spec or roadmap: grep for |
| D-015 | 215 | `scripts/audit/verify_extracts.py`: `check_roadmap_fields`'s | 1-stage0- | 2026-09-04 | — |  | resolved | OBSERVED: code commit is 6bdc9f5 ('fix(audit): scope the roadmap-field presence check to t / OBSERVED: tests/audit/test_verify_extracts.py::test_a_roadmap_key_in_a — write-back: Not in the spec or roadmap: `grep -n 'ch |
| D-016 | 224 | `specs/findings/source-audit.md`'s seam signpost has a second, weaker | 1-stage0- | 2026-09-04 | — |  | resolved | OBSERVED: code commit is 7128144 ('fix(audit): name the seam signpost's second exception', / OBSERVED: tests/audit/test_assemble_finding.py::test_the_shipped_signp — write-back: Not in spec or roadmap: `grep -n 'seam s |
| D-017 | 234 | Two vocabularies now ship side by side in the `ces` findings. | 1-stage0- | 2026-09-04 | Stage 7 | SRC-OTH-003 | open, on schedule |  |
| D-018 | 240 | Two gate-work fixes ship without tests: the `ces_levels` "sm.state codes" | 1-stage0- | 2026-09-04 | — |  | resolved | OBSERVED: code commits are fb0a12b ('test(audit): hold the ces_levels sm.state-codes claus / OBSERVED: (a) tests/audit/test_ces_levels.py::test_broader_code_note_c — write-back: Not in spec or roadmap: `grep -n 'broade |
| D-019 | 255 | `published_start` / `published_end` have no defined semantics. They mean | 1-stage0- | 2026-09-04 | none stated | Stage 0 artifact | open, overdue |  |
| D-020 | 262 | `bds/naics_11.json` is not hash-reproducible — three fetches gave three | 1-stage0- | 2026-09-04 | Stage 7 | SRC-OTH-002/REQ-004 | open, on schedule |  |
| D-021 | 267 | Repo-wide pre-existing `ruff I001` import-order noise, untouched by this | 1-stage0- | 2026-09-04 | — |  | resolved | OBSERVED: code commit is 549a830 ('style(audit): sweep ruff I001 and black over the audit  / No test exists or is claimed; this is a lint state. There is no CI wor — write-back: Not written to the roadmap; the spec's D |
| D-022 | 279 | `probe_slice_boundary` probes every candidate year rather than stopping at | 2-stage1- | 2026-09-05 | trigger condition | §5.4 | open, on schedule (trigger) |  |
| D-023 | 286 | `tests/audit/` also fails `black`, not just `ruff I001`. The existing | 2-stage1- | 2026-09-05 | — | D4 | superseded | OBSERVED: black is gone — pyproject.toml has no [tool.black] block and no black dependency / NONE. No test, CI workflow, pre-commit hook, Makefile or justfile runs — write-back: Spec: YES — specs/logging-employment-spe |
| D-024 | 309 | The bulk-route branch is exercised only under a synthetic boundary. | 2-stage1- | 2026-09-05 | — | D5 | resolved-with-scope-shrinkage | OBSERVED: src/logging_employment/ingest/qcew.py:74 probe_slice_boundary, :104 route_for_ye / tests/unit/test_qcew_routes.py — four tests added by 5a34f00: ::test_t — write-back: Spec: NO — specs/logging-employment-spec |
| D-025 | 337 | `source_row_hash` is computed with `map_elements`, i.e. one Python call | 2-stage1- | 2026-09-05 | trigger condition | REQ-004 | open, on schedule (trigger) |  |
| D-026 | 346 | `cbp_state_size` has no column for `EMP_N_F`, the only field that carries | 2-stage1- | 2026-09-05 | Stage 6 | SRC-CBP-002/§7.5 | open, on schedule |  |
| D-027 | 366 | Nothing re-derives `EMPFLAG_WITHHELD_CODES` against a post-2017 layout. | 2-stage1- | 2026-09-05 | trigger condition | SRC-CBP-003 | open, on schedule (trigger) |  |
| D-028 | 376 | CBP responses are not byte-reproducible, so the immutable store cannot | 2-stage1- | 2026-09-05 | trigger condition | §6.2/REQ-004 | open, on schedule (trigger) |  |
| D-029 | 393 | `qcew_national_size` carries every industry, not just 113310. 140,343 rows | 2-stage1- | 2026-09-05 | trigger condition | §7.4 | open, on schedule (trigger) |  |
| D-030 | 408 | `evidence_kind` has no column of its own. §7.8's field list has no place for t | 3-stage2- | 2026-09-05 | none stated | §7.8/INV-004 | open, overdue |  |
| D-031 | 418 | No check covers a hard row spanning two area-months with differing release vin | 3-stage2- | 2026-09-05 | Stage 6 | INV-007/§7.7 | open, on schedule |  |
| D-032 | 436 | `classify_bound_status` labels an integer interval containing no integer | 3-stage2- | 2026-09-05 | none stated | §7.10/§9.6 | open, overdue |  |
| D-033 | 454 | The §9.7 diagnostic degrades silently on a box-shaped infeasibility. | 3-stage2- | 2026-09-05 | trigger condition | §9.7 | open, on schedule (trigger) |  |
| D-034 | 463 | `rank._shape_key` formats the matrix at `precision=12`. Two equality matrices  | 3-stage2- | 2026-09-05 | trigger condition | CON-005 | open, on schedule (trigger) |  |
| D-035 | 472 | `solve_bounds` rescans the frames once per component and once per row. | 3-stage2- | 2026-09-05 | — | §9.6 | resolved | OBSERVED: src/logging_employment/constraints/index.py:39 `@dataclass(frozen=True) class Sy / tests/unit/test_constraint_index.py (added in 4e08f2d, 210 lines): ::t — write-back: Spec: NO. Roadmap: NO (grep -n 'SystemIn |
| D-036 | 494 | `exactly_identified` and `integer_exactly_identified` never disagree. | 3-stage2- | 2026-09-05 | none stated | §7.10 | open, overdue |  |
| D-037 | 500 | `cli._constraints_dir` derives §6.2's path instead of reading a config key. | 3-stage2- | 2026-09-05 | — | §6.2 | resolved | OBSERVED: src/logging_employment/config.py:49-64 StorageConfig has `constraints_uri: str = / tests/unit/test_cli_paths.py::test_the_constraints_directory_does_not_ — write-back: Spec: NO — Appendix A storage: block at  |
| D-038 | 515 | `MAX_SCALE_RATIO = 100.0` is an originated tripwire with no spec warrant. | 4-stage3- | 2026-09-05 | — | §10.9 | resolved | OBSERVED: `git show 6674277 -- src/logging_employment/baselines/interfaces.py` deletes `MA / `tests/unit/test_baseline_interfaces.py::test_a_raw_dict_cannot_be_pas — write-back: YES, spec: `specs/logging-employment-spe |
| D-039 | 533 | §10.3's fallback scales by the DISCLOSED intensity; §10.4's uses the NATIONAL  | 4-stage3- | 2026-09-05 | — | §10.9 | resolved | OBSERVED: `src/logging_employment/baselines/fallback.py` exists (195 lines) and owns the s / `tests/unit/test_baselines_fallback.py::test_the_two_families_declare_ — write-back: YES, spec: §10.9 `specs/logging-employme |
| D-040 | 552 | `disclosed_intensity` reads the partition from the context while the residual  | 4-stage3- | 2026-09-05 | — | §10.9/R-COMP-8 | resolved | OBSERVED, plan 9 half: `src/logging_employment/baselines/fallback.py::_assert_the_partitio / Plan 9 half: `tests/unit/test_baselines_fallback.py::test_the_disclose — write-back: YES, spec: §10.9 `specs/logging-employme |
| D-041 | 585 | The `general_method` guard lives at the CLI, not in the reconciliation layer. | 4-stage3- | 2026-09-05 | Stage 6 | §12.4 | open, on schedule |  |
| D-042 | 601 | `kl_project` returns silently on an infeasible bounded system. | 4-stage3- | 2026-09-05 | — | §12.4/§17.3 | resolved | OBSERVED: `src/logging_employment/reconcile/projection.py::kl_project` signature returns ` / `tests/unit/test_projection.py::test_an_infeasible_bounded_system_repo — write-back: NOT in the spec: `specs/logging-employme |
| D-043 | 616 | The three provenance enums are declared but never enforced. | 4-stage3- | 2026-09-05 | — | §7.13 | resolved | OBSERVED: src/logging_employment/contracts.py:229-253 `assert_declared_provenance(frame)`  / OBSERVED: tests/unit/test_baselines_runner.py::test_a_typo_in_a_proven — write-back: Roadmap: yes — specs/logging-employment- |
| D-044 | 628 | `integerize` has three bound-handling gaps, all latent on D1 and all live in S | 4-stage3- | 2026-09-05 | — | §12.6 | resolved | OBSERVED src/logging_employment/reconcile/integerize.py: (gap 1, lower<=upper) :55-63 loop / OBSERVED tests/unit/test_integerize.py::test_a_contradictory_bound_pai — write-back: Roadmap: yes — specs/logging-employment- |
| D-045 | 641 | `BreakAdjustedShare` collapses to `RollingMedianShare` below four shares. | 4-stage3- | 2026-09-05 | — | §10.3 | superseded | OBSERVED: the defect the item describes no longer exists. src/logging_employment/baselines / Plan 7's test `test_below_four_shares_the_break_adjusted_variant_is_th — write-back: Roadmap: yes — specs/logging-employment- |
| D-046 | 659 | `NoHarvestFactorError` is defined and never raised. `errors.py` declares it fo | 4-stage3- | 2026-09-05 | — | §10.5/§18.3 | resolved | OBSERVED src/logging_employment/errors.py:95-103: class docstring 'Reserved for Stage 7 an / NONE. `grep -rln 'NoHarvest\\\|Reserved for Stage 7' tests` returns noth — write-back: Neither amended by this fix. The roadmap |
| D-047 | 669 | Task 18's property tests and four of the five cross-cutting audit units never  | 4-stage3- | 2026-09-05 | — | §17.3 | resolved | OBSERVED. Tick commit 6d36982 ('complete plan 7 and tick its five deferred items'); test c / OBSERVED via read-only in-memory mutants (uv run python, source exec'd — write-back: NOT written back. specs/logging-employme |
| D-048 | 704 | `emplvl_raw_nonzero_rows` now means "not a published zero", but three things s | 6-stage0-audit-hardening | 2026-09-05 | none stated | Stage 0 artifact | open, overdue |  |
| D-049 | 720 | The QCEW bulk route has no build-side consumer, and its fetch arm is unreachab | 7-p3-test-coverage | 2026-09-06 | none stated | D5/§5.4 | open, overdue |  |
| D-050 | 736 | `BreakAdjustedShare`'s `<4` fallback is a design choice nobody chose. The audi | 7-p3-test-coverage | 2026-09-06 | — | §10.3 | resolved | OBSERVED. Commit e1be920 ('the break-adjusted share refuses a degenerate cut', 2026-09-07; / OBSERVED. tests/unit/test_baselines_historical.py: T-1 `test_a_one_poi — write-back: PARTIAL. Roadmap: specs/logging-employme |
| D-051 | 758 | `historical.py:227`'s `segment = shares[cut:] or shares` — the `or shares` arm | 7-p3-test-coverage | 2026-09-06 | — | §10.3 | resolved | OBSERVED. Commit 3fe611c (2026-09-06, 'delete an unreachable arm, and keep the seed floor  / By design none was added ('Do not budget a test'). The commit message  — write-back: NOT written back; grep for 'or shares' i |
| D-052 | 785 | `projection.py:98`'s zero-seed floor is redundant with the clip at `:118`. Del | 7-p3-test-coverage | 2026-09-06 | — | §12.4 | resolved | OBSERVED. Commit 3fe611c: no deletion; a nine-line comment added above the floor line and  / OBSERVED. tests/unit/test_projection.py::test_a_zero_seed_is_floored_r — write-back: NOT written back. specs/logging-employme |
| D-053 | 823 | Four anti-drift breaches in `tests/integration/test_d1_acceptance.py`. Found b | 7-p3-test-coverage | 2026-09-06 | — | §17.6/anti-drift | resolved | OBSERVED: `grep -nE '1227\\|4716\\|== 8\b\\|> 4000\\|>= 4716\\|EXPECTED_BOUNDS' tests/integration/te / OBSERVED: `uv run pytest tests/unit/test_anchor.py tests/unit/test_qce — write-back: Not written back. `grep -nE 'anti-drift\| |
| D-054 | 844 | `tests/audit/test_ces_levels.py`'s three artifact tests skip in a clean clone. | 7-p3-test-coverage | 2026-09-04 | — | tests/audit | resolved | OBSERVED: `tests/audit/test_ces_levels.py:539-551` `_ces_findings_from_the_shipped_documen / OBSERVED: the three tests are the test evidence — they now run uncondi — write-back: Not written back. `specs/findings/source |
| D-055 | 854 | `tests/audit/test_qcew_codes.py:378` reads a personal skill file outside the r | 8-test-assertion-integrity | 2026-09-06 | none stated | tests/audit | open, overdue |  |
| D-056 | 869 | The other five `1,227` sites, where the count scopes a claim rather than decor | 8-test-assertion-integrity | 2026-09-06 | none stated | docstrings | open, overdue |  |
| D-057 | 911 | §16.1's manifest MUST is unimplemented for `validate-config` and `registry ver | unregistered-work audit | 2026-09-07 | Stage 1 (done) | §16.1 | open, overdue |  |
| D-058 | 928 | Three Stage 1 deliverables have builders in `src/` that nothing calls and no a | unregistered-work audit | 2026-09-07 | Stage 1 (done) | §8.6/§3.1/§7.1 | open, overdue |  |
| D-059 | 942 | `build-harmonized` writes no machine-readable manifest, and `BUILDER_VERSION`  | unregistered-work audit | 2026-09-07 | Stage 1 (done) | §16.1/§18.1 | open, overdue |  |
| D-060 | 951 | The CBP `EMPSZES` values-crosswalk route is dead: `discover_empszes` has no ca | unregistered-work audit | 2026-09-07 | Stage 1 (done) | SRC-CBP-001 | open, overdue |  |
| D-061 | 963 | `bounds.py`'s soft-row filter cites a schedule that has expired: three of the  | unregistered-work audit | 2026-09-07 | none stated | §7.8/§9.3/INV-004 | open, overdue |  |
| D-062 | 978 | A `stage3-plan-audit` DEFECT was only half discharged: `intensity.py`'s "MEASU | unregistered-work audit | 2026-09-07 | — | §10.4 | resolved | OBSERVED: commit be3e161 (`fix(deferred): five quick fixes from the 2026-09-07 triage`) re / OBSERVED: `tests/unit/test_baselines_runner.py:129 test_weight_basis_c — write-back: Not written back. `grep -nE 'Hawaii\|Rhod |
| D-063 | 1004 | `state_universe_report` has no caller, and a live guard's docstring delegates  | unregistered-work audit | 2026-09-07 | Stage 1 (done) | SRC-QCEW-006 | open, overdue |  |
| D-064 | 1015 | Four config keys govern nothing, and none is recorded as inert. The repo's con | unregistered-work audit | 2026-09-07 | none stated | config/§3.4 | open, overdue |  |
| D-065 | 1035 | The `network` pytest marker is registered with a promise it does not keep, and | unregistered-work audit | 2026-09-07 | none stated | §17/CI | open, overdue |  |
| D-066 | 1046 | The 24 pre-existing `ruff` violations in `scripts/audit/` are scoped out twice | unregistered-work audit | 2026-09-07 | none stated | lint | open, overdue |  |
| D-067 | 1057 | Three QCEW code constants are declared and then bypassed by inline literals in | unregistered-work audit | 2026-09-07 | — | constants | resolved | OBSERVED: `src/logging_employment/ingest/qcew.py:25-26` imports `QCEW_NATIONAL_AGGLVL, QCE / OBSERVED: `tests/unit/test_qcew_size.py:54-83 test_a_state_row_at_the_ — write-back: Not written back. `grep -nE 'QCEW_ALL_SI |
| D-068 | 1075 | The two §5 concept guards are never called, and unlike the repo's other inert  | unregistered-work audit | 2026-09-07 | — | INV-010/SRC-OTH-001/004 | resolved | OBSERVED: src/logging_employment/harmonize/concepts.py:1-11 module docstring now opens 'NE / No test pins the docstring text. The guards' behaviour is pinned by te — write-back: Code/docstring only. grep for 'concept g |
| D-069 | 1093 | Stage 3 completed without the completion stamp the roadmap mandates in the spe | unregistered-work audit | 2026-09-07 | — | stamp protocol | resolved | OBSERVED: specs/logging-employment-spec.md:2478 '- Roadmap: specs/logging-employment-spec- / None. No test reads specs/logging-employment-spec.md's Stage stamps or — write-back: Yes — this item IS the spec/roadmap writ |
| D-070 | 1111 | Two retired plans' status headers misstate their own deferral disposition. Nei | unregistered-work audit | 2026-09-07 | — | plan records | resolved | (1) OBSERVED: specs/plans/completed/2-stage1-logging-employment-spec.md:3 now reads '**Sta / None. No test reads plan headers (grep 'specs/plans' in tests/ returns — write-back: Not applicable / not done — the item con |
| D-071 | 1137 | Wire `rolling_origin` and `cbp_size_gaps` into the harness scoring loop. | 11-stage4- | 2026-09-07 | none stated | §13.3/REQ-022 | open, overdue (re-deferred ×1) | named in plan 12's Closes line, then explicitly not closed |
| D-072 | 1172 | §13.7's CRPS is the harness's dominant cost, not `run_baselines`. | 11-stage4- | 2026-09-07 | trigger condition | §13.7 | open, on schedule (trigger) |  |
| D-073 | 1186 | `validation_scores` / `validation_metrics` are written without `validate_frame…` | 11-stage4- | 2026-09-07 | — | §7.14/§7.15 | resolved | OBSERVED src/logging_employment/cli.py:455-462 — `validate_command` loops over (result.sco / OBSERVED tests/unit/test_contracts_validation.py::test_a_null_in_a_req — write-back: YES, both. Spec: specs/logging-employmen |
| D-074 | 1199 | Preferred transparent baseline is undefined against §10.8's rung exclusion. | 11-stage4- | 2026-09-07 | — | §13.10/§10.8 | resolved | OBSERVED src/logging_employment/validate/scoreboard.py:134-151 `preferred_baseline` return / OBSERVED tests/unit/test_validate_scoreboard.py::test_a_10_3_share_var — write-back: ROADMAP yes, SPEC no. Roadmap L229: 'RES |
| D-075 | 1281 | §13.10's "on primary-like masks" scoping is unreachable from the scoreboard. | 11-stage4- | 2026-09-07 | — | §13.10/§13.2-8 | resolved | OBSERVED src/logging_employment/validate/scoreboard.py:168-213 `assert_scored_cells_are_pr / OBSERVED tests/unit/test_validate_scoreboard.py::test_a_complementary_ — write-back: ROADMAP yes, SPEC no. Roadmap L229: '... |
| D-076 | 1372 | Appendix A's `include_*` switches gate no regime selection. | 11-stage4- | 2026-09-07 | — | Appendix A/§13.3 | resolved-with-scope-shrinkage | OBSERVED src/logging_employment/contracts.py:407-425 `SWITCH_KINDS` closed set and `VALIDA / OBSERVED tests/unit/test_validation_switch_kinds.py::test_every_includ — write-back: YES, both. Spec Appendix A (:2233-2250): |
| D-077 | 1404 | The `validate` CLI runs the full REGISTRY with no estimator-subset option. | 11-stage4- | 2026-09-07 | — | §16.1 | resolved | OBSERVED. Commit 316ddd9 (2026-09-07, 'feat(validate): reach §16.2's estimator lever from  / OBSERVED: `uv run pytest -p no:cacheprovider tests/unit/test_harmonize — write-back: Roadmap: YES — specs/logging-employment- |
| D-078 | 1457 | The audit script's NAICS note still reads "uncited", now that the citation exi | /deferred triage | 2026-09-08 | none stated | Stage 0 artifact | open, overdue |  |
| D-079 | 1472 | `vintage_for_year` mislabels every reference year below 2017, against BLS's ow | /deferred triage | 2026-09-08 | — | INV-007 | resolved | OBSERVED. Commit 41e17cf (2026-09-08, 'fix(naics): refuse pre-2017 reference years instead / OBSERVED: `uv run pytest -p no:cacheprovider tests/unit/test_harmonize — write-back: Spec: NO — `grep -n 'vintage_for_year\\|U |
| D-080 | 1497 | `vintage_for_year`'s refusal message pins its year but not its vintage payload | /deferred triage | 2026-09-08 | none stated | test pin | open, overdue |  |
| D-081 | 1513 | Three of `vintage_for_year`'s six call sites raise after a side effect. | /deferred triage | 2026-09-08 | none stated | §18.3/REQ-004 | open, overdue |  |
| D-082 | 1529 | `assert_declared_provenance` does not check `mask_arm` against `MASK_ARMS`. | 12-stage4-harness-completion | 2026-09-09 | none stated | §7 closed sets | open, overdue |  |
| D-083 | 1543 | `metric_name` is NULL on every `declines` metrics row. Measured 2026-09-08 and | 12-stage4-harness-completion | 2026-09-09 | trigger condition | §7.14 | open, on schedule (trigger) |  |
| D-084 | 1558 | The CBP gap's effect is pooled, not confined to the holed state-year. | 12-stage4-harness-completion | 2026-09-09 | trigger condition | §13.3 | open, on schedule (trigger) |  |

**Scope-shrinkage cases, in detail.**
- **D-002** (no-retabulation premise uncited): the citation was placed in two `src/` sites; the audit script and the tracked finding document the item named still read "uncited" — the residue was re-filed as D-078 (open) and the tick is defensible only as "find the citation".
- **D-005** (`lfo_by_year` null): the query now *selects* `LFO,LFO_LABEL` but still filters `LFO=001`; the item asked for "a dedicated LFO query" and the closure note itself records the narrowing.
- **D-024** (bulk route under a synthetic boundary): the tick explicitly narrows — the premise ("a production bulk path exists to be under-exercised") is declared false and the structural deadness was re-filed as D-049 (open, overdue).
- **D-076** (`include_*` switches): four of seven flags wired to regimes; the original's "delete the flags that name nothing" branch was refused because removing a `ValidationConfig` field re-ids every run directory; two mask-label flags and one design-validity operand remain declared-but-inert and `config.yaml` still claims complementary masking the harness refuses.

**Write-back to the spec or roadmap.** Of the 45 ticked items, 12 were reflected into the spec (§10.9 for D-038/D-039/D-040; §7.14/§7.15 and Appendix A comments for D-073/D-076; the Stage 3 stamp for D-069; D4 for D-023) or the roadmap (Stage 3/4 blocks for D-004, D-043, D-044, D-074, D-075, D-077). Thirty-three live only in code, docstrings, plan files or the register itself. That is acceptable for audit-script items (D-007..D-016) and test-only items, but not for D-042 (`kl_project`'s return contract: §12.4/§17.3 unamended), D-074/D-075 (the §13.10 comparand definition and the primary-like precondition: §13.10 still carries the undefined phrase and says nothing about `None`), or D-079 (`vintage_for_year` refusal: nothing in the spec).

**Pointer rot inside the register (observed).** At least eight ticked items cite the docs-only tick commit instead of the code commit (`4d91eea`, `ec7bd03`, `283802b`); cross-references by line number are stale in six places (`:600` → 659, `:661` → 720, `:243` → 267, `:63`/`:76`); the D-057 text says `build-harmonized` "folds rows into `source_manifest.parquet`" when only `fetch` writes it (D-059's title says the opposite in the same section). None of this changes a verdict; all of it costs the next reader.

### 4.2 Untracked deferrals (Phase 3c)

Requirements that are `missing` or `partial` in §2.4/§3.2, whose owning stage is ticked complete, and for which no deferred item, `> Deviation` note or roadmap sentence exists. These are the gaps nobody is watching.

| Requirement | Owning stage (done) | Status | Where it should have been recorded |
|---|---|---|---|
| §10 preamble / INV-002: baselines use the same hard bounds as the model; per-cell bounds enforced on released point estimates | Stage 3 | partial — baseline path passes no bounds (F-006) | a deferred item naming the trigger (any finite `selected_upper` on a state cell) and the owner |
| §12.5 "with bounds … general convex projection" | Stage 3 | partial — `reconcile_matrix` has no bounds parameter (F-018) | roadmap Stage 3 Produces qualification; Stage 6 Consumes |
| §10.4 "robust" intensity shrunk toward "regional/national"; §10.8 rung 1 "with robust historical adjustment" | Stage 3 | partial (F-020) | a deferred item or a §10.4/§10.8 amendment |
| §5.5 employment-margin comparison in the size gate | Stage 2 | partial — computed, never compared (F-017) | `compat.py` header or a deferred item |
| §9.6 step 2 MILP trigger | Stage 2 | diverged (F-016) | `config.py` docstring records a "performance switch"; not as a divergence |
| §9.7 explicit quarantine path | Stage 2 | partial — no CLI path | nowhere |
| §9.3 region / parent-industry / ownership margins | Stage 2 ("§9 (all)") | missing — no such input is fetched (F-005) | a recorded decline with its reason |
| §7.2 `source_publication_date`; harmonized `snapshot_id` ↔ manifest join | Stage 1 | partial / diverged (F-010) | nowhere |
| §18.3 source fetch failure (silent `continue`) | Stage 1 | diverged (F-009) | nowhere; `ingest/CLAUDE.md` documents the CBP-2024 instance only |
| §6.2 layout, no-re-download rule, `run_manifest.json` | Stage 1 | diverged | nowhere |
| §7 preamble: `run_id` and a schema version on every table | Stage 1 (tables) | missing | nowhere (D-059 covers `BUILDER_VERSION` only) |
| §3.1 mechanical crosswalk verification "in the ETL" | Stage 1 | partial — runs only in tests | roadmap reframed it as "a crosswalk test" |
| §13.2 step 1 "configurable propensity" | Stage 4 | partial — literals, `config` discarded | nowhere |
| §13.5 "truth outside bounds is a bug" rule; infeasible-component rate; LP-vs-MILP tightening | Stage 4 | missing (F-002, F-003) | nowhere; `validate/CLAUDE.md`'s not-covered list omits §13.8's norms and §13.7's anchor-distance calibration too |
| §10.7 *rolling* residual ensembles | Stage 4 | diverged, mislabelled (F-019) | nowhere |
| §13.6 median APE over the safe subset | Stage 4 | partial | nowhere |
| `validation.minimum_missing_set_size`, `sources.*.enabled`, `fail_on_unknown_disclosure_regime`, `single_margin_method`, `integerization_tiebreak`, `include_random_mask_sanity_check`, `promotion.*` | Stages 1–4 | dead config keys folded into `run_id` (F-025) | D-064 covers four of fourteen |
| §17.2's ninth property (every reconciled draw within bounds and satisfying margins) | handed Stage 2 → Stage 3 | partially covered by §17.3 property 2 on a single-margin system; no bounds-and-margins-on-draws test | plan 4 never mentions it |
| `preferred_estimator_by_month` (written to `baseline_manifest.json`) | Stage 3 | no reader, no test | nowhere |
| `runs/_baseline_pre_stage4c/` | Stage 4 | a non-run-id directory under the output root; the roadmap says `runs/` holds exactly one directory | nowhere |

### 4.3 Deferral dynamics (Phase 3d)

**Conscious scoping or pressure valve?** Both, and the register is candid enough that the distinction can be read off it. The counts by plan (created / closed-by-this-plan / still open from those created):

| Plan | Created | Closed here | Still open | Character |
|---|---|---|---|---|
| 1 (Stage 0) | 20 (+1 from derivation) | 0 | 4 | reviewer Minors and questions routed forward; closures came from plans 6, 7 and quick fixes |
| 2 (Stage 1) | 8 | 2 | 6 | plus 6 later "unregistered" items against Stage 1, all open |
| 3 (Stage 2) | 8 | 0 | 6 | all design-level refinements; none blocks |
| 4 (Stage 3) | 10 | 1 | 1 | highest churn: 9 of 10 closed by plans 5, 7, 9, 10, 11 and a quick fix |
| 5–10 (sub-projects) | 9 | 21 | 4 | net closers |
| 11 (Stage 4) | 7 | 1 | 2 | one of the two open is the stage's hard half |
| 12 (Stage 4 completion) | 3 | 2 | 3 | explicitly declined its third target |
| unregistered-work audit (09-07) | 14 | — | 9 | found by a 30-agent sweep, not by any plan protocol |
| triage (09-08) | 4 | — | 3 | |

Net: the backlog grew from 1 to 39 open across twelve plans; stage plans are net creators, sub-project plans net closers, and the single largest source of open items (14) was an external audit rather than a plan's own completion protocol.

**Were hard parts deferred?** Stage 0: no. Stage 1: the hard parts shipped, but four Produces claims are unmet and surfaced only through the 2026-09-07 audit (F-008). Stage 2: no hard part deferred; the state-arm vacuity is a data fact honestly recorded, but the question of whether other margins could change it was never asked (F-005). Stage 3: the anchor — the one ACTION REQUIRED — was delivered; §12.4/§12.5 shipped without callers by design; the bounds half of INV-002 shipped without enforcement and without a record (F-006). Stage 4: the hard half *was* deferred — plan 11 built two mechanisms and never specified their wiring; plan 12 declared "deciding what each regime scores" out of scope and ticked the stage; two exit criteria were re-read rather than implemented (F-001, F-002).

**Clustering.** Open items cluster on Stage 1's provenance and command surface (D-049, D-057, D-058, D-059, D-060, D-063: six items), on Stage 4's harness (D-071, D-072, D-082, D-083, D-084), and on unowned spec questions (D-030, D-032, D-036, D-061). Nothing clusters on the constraints engine's numerics or on reconciliation's arithmetic — the parts that would be expensive to get wrong are the parts with the fewest open items.

**Items that block the frontier.** D-071 (what `rolling_origin` and `cbp_size_gaps` score) blocks any honest claim that REQ-022 is met and therefore blocks a Stage 5 gate design that compares real-time and retrospective accuracy. D-041/D-061 (where the `general_method` guard lives; who produces soft constraint rows) and F-018 block Stage 6's plan from being written against a true picture of `reconcile/`. D-026 (`EMP_N_F`) blocks Stage 6's measurement model from having the noise band it would weight by. **Items that compound**: the run-id/provenance gap (F-011) grows with every stage that adds artifacts; the fourteen dead config keys (F-025) can no longer be removed without re-iding every run directory, so each new stage inherits them; the roadmap block accretion (F-021) makes each later stage's Consumes block longer and less readable.

**Were resolved items tested and written back?** Tested: yes, in every case the verifiers checked — the project's habit of mutation-testing a fix before ticking it (recorded in D-035, D-047, D-051, D-052, D-067) is the strongest process signal in the repository. Written back: only where the resolution changed a contract a later stage reads (12 of 45); the spec's normative sections were not amended for the anchor (D-004), the `kl_project` return (D-042), the comparand definition (D-074) or the precondition (D-075).


## 5. Findings

Severity is set by consequence for the spec's goals (§1: state-month-size estimates with honest identification, validation and disclosure control), not by how easy the problem was to spot. **No finding is Critical**: nothing found makes a shipped number wrong on the pilot window, and the byte-identical reproductions hold. The High findings are all of one of two kinds — the record overstates what shipped at the frontier, or a fail-closed guarantee is latent rather than enforced and will bite when the data or the stage changes. Categories: spec / code / test / deferral / tooling / process.

### High

**F-001 · process · Stage 4 is ticked COMPLETE against two exit criteria the code does not enforce, and the stamp lapse that Stage 3's deferred item was written to prevent recurred unrecorded.**
Evidence: roadmap Stage 4 Exit (`specs/logging-employment-spec-roadmap.md:226`): "the harness rejects a mask whose target remains exactly recoverable; a pseudo-hidden truth falling outside the deterministic bounds fails the run as a constraint-data bug (§13.5)". `grep -rn is_exactly_recoverable src/` → definition only (`validate/recover.py:67`); `mask_and_solve_size` likewise; `validate/harness.py:150-190` masks, solves, runs baselines and emits `exact_recovery_rate` and `truth_in_bound_rate` as metric rows — it never rejects a target or fails a run (verified by reading the loop). The only witnesses are `tests/integration/test_validate_exact_recovery.py` (calls `mask_and_solve_size` directly; skips silently unless a March with zero suppressed classes exists — only 2017-03 does) and `bound_metrics`. The tick: `771dabe` (2026-09-07 17:34) changed `[ ]`→`[x]` with no spec stamp and no heading suffix; the spec stamp arrived at `f8fa033` (2026-09-09 16:02) and `roadmap:219` still lacks the suffix Stages 0–3 carry. The identical Stage 3 lapse had been filed (D-069) and fixed five hours earlier the same day (`be3e161` 12:15). Three completion dates now coexist (roadmap SHIPPED 09-07; plan 11 header 09-07; spec stamp 09-09).
Impact: the roadmap's completion signal is unreliable at exactly the stage Stage 5 must plan from; a Stage 5 planner following `CLAUDE.md` ("read the Stage stamps") found no Stage 4 stamp for 46 hours while the roadmap said it was done. Related: REQ-021, INV-014, D-071, D-069.

**F-002 · spec-coverage · REQ-022 and four of §13.3's thirteen regimes are claimed closed while producing no score; §13.2 steps 3, 6 and 8 have no live content on the scoring arm.**
Evidence: roadmap Stage 4 "Gap closed: … REQ-022" (`:222`); `runs/f03023ac9f3a/validation_manifest.json`: `rolling_origin feasible scored=0 reps=0`, `cbp_size_gaps feasible scored=0`, `retrospective_smoothing vacuous_on_registry`, `preliminary_to_final_vintage cannot_run_on_d1` (read with polars; nine regimes score). `harness.py:131-148` runs `assert_no_future_rows` at seven origins and, per its own comment (`:137-141`), "cannot fail on this composition". `complementary_partners`, `cbp_size_gap_keys`, `apply_cbp_gap` have no `src/` caller. `scoreboard.assert_scored_cells_are_primary_like` refuses the second label (D-075) so "scores primary-like and complementary-like cells separately" is met by absence. All 12,530 scored cells are `unbounded` (`value_counts` on `validation_scores.parquet`).
Impact: there is no rolling-origin (real-time) accuracy number anywhere; every §13.6/§13.7 figure is retrospective, on one arm, primary-like only; the harness cannot detect a constraint-data regression through pseudo-suppression; Stage 5's promotion comparand inherits all of this. The tracking is honest (D-071 open; manifest reasons per regime) but the roadmap's Gap-closed line and Exit line are not. Related: REQ-021, REQ-022, INV-014, D-071, D-084.

**F-003 · spec-coverage · Eleven of §13.5–13.8's required metrics are not emitted and not tracked, and §13.10's stratum gates have no data source.**
Evidence: `validate/metrics.py` emits exactly `truth_in_bound_rate`, `exact_recovery_rate`, `mean_feasible_width`; `mae`, `rmse`, `bias`, `wape`, `median_ape`; `coverage_{0.50,0.80,0.90,0.95}`, `mean_interval_width_0.90`, `crps`, `n_clipped_at_zero`; `negative_outputs`, `integerization_violations`, `anchor_adding_up_max_abs` (18 names; confirmed against the golden's `metric_name` set). Missing from §13.5: infeasible-component rate, LP-vs-MILP tightening; §13.6: state-share AE, size-share AE, rank accuracy; §13.7: calibration by state size, region, gap duration, propensity, and by CBP-anchor distance; §13.8: ‖Ax−y‖₁, ‖Ax−y‖∞, row-sum and class-margin violations. `validate/CLAUDE.md:184-189` lists some but not §13.8's norms or the anchor-distance calibration; no deferred item names any. `metrics.py:18` says "§13.5's five metrics" and emits three; `:258` says "§13.8's residual norms" and emits none.
Impact: §13.10's "does not fail catastrophically in any major stratum" and "no major stratum degrades by more than 2 %" cannot be evaluated by anything that exists; REQ-023 is ticked. Related: REQ-023, REQ-024, INV-014.

**F-004 · spec · The required national-residual reconciliation rests on an anchor the normative spec never names, because the sources' fallback was dropped in synthesis and §12.2 was never amended after Stage 0's `decline`.**
Evidence: §2.2 row 11 and §12.2 (l.1419-1433) require the fast path "for a compatible national total N_t"; the Stage 0 stamp (l.2334-2337) records SRC-QCEW-006 = `decline` ("every one of the 96 testable months carries at least one suppressed cell"); ChatGPT l.325 ("when a national benchmark is unavailable … use whatever compatible parent intervals exist") has no counterpart in the spec (grep). Stage 3 shipped `reconcile/anchor.py` — the published national employment total admitted by an establishment-count closure gate, stamped `anchor_basis='declared_national_total'` and called a `modeling_assumption` in a docstring and in roadmap Stage 3 point (5), which says "recorded nowhere else". §15.2's release fields carry no anchor status (ChatGPT's `national_constraint_status` field was also dropped). `Anchor.anchor_basis` is an unvalidated `str`; the INV-004 class is not machine-readable.
Impact: every baseline estimate and every planned Stage 5 draw allocates against a total whose identity with the state universe is unverifiable on the pilot window; a reader of §12.2 believes N_t is verified; the release row cannot say otherwise. The code's choice is sound and well-argued; the spec is silent. Related: REQ-018, INV-002, INV-004, D-004.

**F-005 · spec/roadmap ownership · The identification engine bounds no state cell, and the §9.3 margins that could change that were never fetched, declined, or owned.**
Evidence: `runs/f03023ac9f3a/deterministic_bounds.parquet`: 1,227 suppressed state cells, all `unbounded` `[0, null]` (re-derived); the 14 partially-identified cells are national size classes. §9.3 (l.953-963) admits "compatible region totals", "compatible parent industry totals equal to children", "compatible ownership totals" as hard constraints; the registry (`registry/sources.yaml:20-25`) fetches `industry/113310.csv` only; `data/raw/qcew` holds 32 slices of 113310 and nothing at 1133 or 113 (find); Stage 2's block says "§9 (all)" and the stamp records "the only margin this stage builds"; no deferred item and no roadmap sentence records a decision not to pursue parent, ownership or regional margins. (Inference, labelled: with 113310 the only six-digit child of 1133, a 1133 state margin is identical and adds nothing; a 113 margin minus disclosed siblings 113110/113210, or an all-ownership total minus government, might bound some cells — nobody measured it.)
Impact: the product's primary target has zero identifying content, so §9.1's "identification precedes imputation" is vacuous for state totals, §13.5 can never fire on target 1, REQ-026's flags are structurally silent on state cells, and every state estimate is model-only — a fact the release must state and the spec does not. Related: REQ-009, REQ-011, INV-005, REQ-026.

**F-006 · code (fail-open, latent) · INV-002's per-cell-bounds half is unenforced on the baseline production path; baselines and draws use different reconciliation entry points, against §10's preamble.**
Evidence: `baselines/runner.py:253` `allocate(anchor, outcome)` and `:277` `integerize(allocated, total=…)` pass no bounds (read); `scale_into_bounds` (`scaling.py:51`) is reached only from `reconcile_draws`, which has no `src/` caller; nothing in `baselines/` or `cli.py` reads `deterministic_bounds` (grep); `test_d1_baselines.py:57-70` checks sum-to-residual and non-negativity only. Recorded only obliquely (`allocate.py:68-70` cites the D1 measurement "every state cell is unbounded above"; roadmap Stage 3 (6) covers the `integerize` half).
Impact: the moment any state cell carries a finite `selected_upper` — a clean month that retires the anchor (the retirement condition `anchor.py` itself names), a Stage 6 state×size cell, or a mask on the size arm — every baseline can exceed a public upper bound with `reconciliation_status='anchored_and_reconciled'` and no test, verifier or halt. Related: INV-002, REQ-018, R-§10-pre.

**F-007 · tooling · A clean environment cannot run any command: `python-dotenv` is a dev-only dependency imported at module scope by `config.py`.**
Evidence: `pyproject.toml:9-19` runtime deps omit it; `:26-30` `[dependency-groups].dev` lists it; `uv tree --frozen --no-dev | grep dotenv` → nothing; `src/logging_employment/config.py:11` `from dotenv import dotenv_values`; `cli.py` imports `config` at start-up. Not executed (`uv sync --no-dev` would re-sync the venv), but the import chain is unconditional.
Impact: INV-016/REQ-030's "clean environment" and every reproducibility claim in the stamps were made from a dev-synced venv; no CI exists to notice. Trivial fix (R-01). Related: INV-016, REQ-030.

**F-008 · deferral / completion overclaim · Stage 1 is ticked COMPLETE with four Produces claims unmet, discovered only by a later external audit and still open.**
Evidence: roadmap Stage 1 Produces (`:196`): "both QCEW acquisition routes behind one ingest interface, selected by reference year"; tables `source_registry` and "harmonized versioned dimensions per §8.6"; "the §3.1 classification memo carrying all four fields"; four commands "each writing a machine-readable manifest". Observed: `route_for_year` returns `"slice"` for every window year by construction (`fetching.py:103-107` probe range ends at `min(window)`), `read_bulk_zip` has no caller, `build_harmonized` globs `*.csv`; `registry_frame`, `dimension_frame`, `classification_memo` have zero callers and `ls data/staged` shows four tables; `validate-config`, `registry verify`, `build-harmonized` write nothing. D-049, D-057, D-058, D-059, D-060, D-063 are all open with no target; D5 and the roadmap block are unamended.
Impact: D5 is a spec decision that is not implemented in the build path; the registry/dimension layer later stages "consume" does not exist on disk. Related: REQ-001, REQ-006, REQ-008, REQ-028, D5.

**F-009 · code (fail-open) · `fetch` silently drops any quarter or year whose response is non-200 or empty, recording nothing.**
Evidence: `fetching.py:119-120`, `:140-141`, `:162-163`, `:170-171` — `if fetched.http_status != 200 …: continue` (read); no manifest row, no error, no log; `tests/unit/test_fetching.py` serves 200 only. `ingest/CLAUDE.md` documents only the CBP-2024 instance ("simply absent from the store rather than an error").
Impact: a transient BLS 5xx on one quarter yields a harmonized panel missing three months, a different `run_id`, and every downstream stage proceeding on a narrower window — against §18.3 and §18.2 ("track source fetch failures"). Related: REQ-029, REQ-004.

**F-010 · code (provenance) · Harmonized `snapshot_id` is a filename stem, so no harmonized or constraint row joins to `source_snapshot` by its declared key.**
Evidence: `build.py:177,192,220` `snapshot_id=path.stem`; `store.py:84` `snapshot_id = stored.retrieval_id` (sha256); `data/staged/qcew_monthly.parquet` `snapshot_id` ∈ {`2017q1`, …}; `runs/source_manifest.parquet` `snapshot_id` ∈ {`195ec956…`, …} (read with polars); `constraints/cells.py:104` and `rows.py:260-312` propagate the stem into `target_cell.source_snapshot_id` and `constraint_row.source_snapshot_ids`; no `src/` join to the manifest exists. Only `release_vintage`'s stem-ness is recorded (`config.py:190-193`, `ingest/CLAUDE.md`).
Impact: §18.1/INV-016 traceability from a constraint row to a checksummed retrieval works by filename convention, not by key; two snapshots of one reference key (the CBP case) would share one stem. Related: REQ-004, REQ-028, SRC-QCEW-001.

**F-011 · tooling/provenance · `run_id` excludes source code and §18.1's code commit and lock hash are recorded nowhere, so a stale run directory is undetectable from its manifests.**
Evidence: `runs.py:41-46` payload = {config, inputs[, overrides]}; `grep -rnE 'git rev|commit_sha|uv.lock|lock_hash' src` → 0; `solve-bounds` writes three tables and records no output hash; `validate --estimators` subset runs have no `config.resolved.yaml` (`cli.py:475-477` says so). The project knows this (`CLAUDE.md` gotchas; roadmap Stage 4 (6) "a THIRD staleness mode … only the artifact mtimes against `git log` can") and spent PRs #9, #11, #13, #15, #17 on 2026-09-08 re-establishing which directory the roadmap's numbers came from. I verified the current artifacts are not stale in content (the one post-mtime commit changed a write-time gate and docstrings), but only by reading the diff.
Impact: every measured figure in the roadmap detaches silently from the artifact it cites; the only cross-stage check is `constraint_set_hash`. Related: REQ-028, INV-016, §18.1.

**F-012 · spec integrity · The reference configuration does not load, and `config.yaml`'s header describes a different Appendix A than the one in the file.**
Evidence: `Config.model_validate(<Appendix A YAML>)` → 11 errors (seven `sources.*` extra, `model` extra, `baselines` missing, two `disclosure.*` missing; run in-session); `CLAUDE.md` says Appendix A "≈ `config.yaml`"; `config.yaml:1-9` cites Appendix A at lines 2022–2049 (now §19) and says the validation/promotion blocks are omitted while `config.yaml:74-102` carries both; `tests/unit/test_config.py::test_appendix_a_config_parses` parses a trimmed literal labelled `APPENDIX_A`.
Impact: the document the spec calls its example cannot be used; the test that claims to check it proves nothing; five `baselines:` keys have no spec home. Related: Appendix A, R-§16.1.

**F-013 · spec integrity · Appendix B (the roadmap's retirement gate) cannot be satisfied as written.**
Evidence: Appendix B step 6 "builds a national state-sum constraint plus observed-cell constraints" — SRC-QCEW-006 is `decline` and `rows.assert_no_national_employment_margin` refuses that row by design (`constraints/system.py:98-99`); step 7 "computes LP bounds for suppressed states" is vacuous (all `[0, null]`); the roadmap's Completion section: "confirming the Appendix B scenario runs end-to-end from a clean environment".
Impact: nothing currently defines what "done" means for the roadmap as a whole. Related: INV-016, REQ-030.

**F-014 · spec integrity · (Severity revised to Low on 2026-09-10 — see §10.1.) The spec cited a binding source document that was not in the repository at `c4bbf4e`, and its source citations use file names that do not exist.**
Evidence: §2 l.51 and §2.1 l.57 attribute "target tensor, required source inventory, compatibility analysis, … pseudo-suppression validation, and disclosure review" to `logging-prompt.md`; Appendix C cites `logging-prompt(1).md` with line ranges; `ls specs/` and `git log --all --diff-filter=A --name-only | grep -i prompt` → nothing; Appendix C and the roadmap header cite `logging-research-*.md.md`; the files are `logging-employment-research-*.md`. Stage 0's finding cites the roadmap's "three research reviews" and the review prompt says "the four".
Impact: the source of the "requested scope and epistemic discipline" cannot be audited; §2.1's attribution table has an unverifiable row; fidelity analysis is necessarily incomplete. Related: §2.1, Appendix C.

### Medium

**F-015 · spec · Nine papered-over contradictions remain in the normative text** (both sides present, mutually inconsistent, resolved only in roadmap prose or code): §12.2 required fast path vs `decline` (F-004); §13.2 step 8 vs §13.10 "on primary-like masks" (resolved as a precondition in `scoreboard.py`; §13.2 unamended); §9.1 no models vs §9.8 `model_estimable`/`model_only`; §11.1 H "required" vs Appendix A `include_harvest_factor: false` vs Stage 7; §11.3 "exact observations" vs Student-t σ_y; §3.4 MUST two modes vs MAY one (and `realtime_asof` accepted-and-ignored, D-064); §14.1's three statuses in no contract; SRC-QSIZE-003 "first-quarter" vs March; D5 "five recent years" vs Stage 0's 2014; BEA "available optional source" in five places vs D6 out of scope; three definitions of "preferred baseline" (§10.4 by fiat, §10.8 rung 1 fused, §13.10 by score — resolved in roadmap Stage 4 (3), where `preferred_baseline` may return `None`, which §13.10 does not contemplate). Evidence: spec line cites in §2.2 above and Appendix 9.4. Impact: a Stage 5 planner reading the spec alone gets three different comparands and a required model component that does not exist.

**F-016 · code (latent) · §9.6 step 2's MILP trigger is a width heuristic, so an integer cell with a wide fractional LP interval ships non-sharp, non-integer bounds.** Evidence: `bounds.py:323-340` `_needs_milp` re-solves only when some integer cell's LP width `< use_milp_when_lp_interval_width_below` (25); a probe with `2x − y = 0`, `y ∈ [1,101]` gives `x ∈ [0.5, 50.5]`, `partially_identified`, `milp_*` null (constraints subagent, reproduced by reading the gate). §9.1 defines L/U over F including integrality; §9.6 says "if integer feasibility can change the result". Latent on D1 (every hard coefficient is ±1 with integer rhs). Recorded as a "performance switch" (`config.py:99-101`), not as a divergence. Impact: the first fractional coefficient (a share, a deflator — the same trigger D-034 names) publishes non-integer bounds for integer counts; reconciliation would clip to them. Fix is cheap (ceil/floor tightening when MILP is skipped).

**F-017 · code (fail-open, latent) · The §5.5 size-margin gate aggregates the employment sum and never compares it, even in the one year it says is checkable.** Evidence: `compat.py:110-140` computes `observed_employment` and `employment_value` on the joined frame; the only refusals test `estab_gap != 0` and `size_vintages > 1` (read); the header says the gate "rests mostly on establishments" and exposes `employment_checkable_years=[2017]`, not that employment is never compared. Impact: a BLS revision that moves the national all-sizes March employment without moving the classes in a fully-published year is a vintage conflict §5.5 exists to catch at build time; it would surface only as an LP infeasibility at solve time, and only if the operator runs `solve-bounds`.

**F-018 · code · Stage 6's inherited reconciliation surface is overstated: `reconcile_matrix` takes no bounds, `Bounds` treats an absent `upper` as +∞ and an absent `lower` as a bare `KeyError`, and the `general_method` guard is dead.** Evidence: `matrix.py:32-40, 75-76` (`lower=zeros`, `upper=inf` hardcoded; no parameter); `scaling.py:37-46` (`upper.get` vs `lower[cell]`); `projection.py:41-53` `require_supported_method` with zero callers (D-041, whose original premise — "lives at the CLI" — was itself false); roadmap Stage 3 lists "§12.5 row–column matrix reconciliation" under Produces without qualification. Impact: Stage 6's plan will be written against a `reconcile/` that cannot honour class bands through `reconcile_matrix`, and a cell dropped from `deterministic_bounds` (the "84 state-months publish no row" shape) becomes unbounded above silently. Related: REQ-016, REQ-018, INV-011.

**F-019 · code/spec · §10.7's predictive intervals are cross-sectional leave-one-out within a replicate, labelled `rolling_residual_ensemble`, and §13.10's coverage gate would read them.** Evidence: `metrics.py:154-167` pools the other scored cells of the same (regime, seed, estimator) replicate and deletes the target by position; no time ordering; `contracts.INTERVAL_SOURCES` and `metrics.py:180` label it "rolling"; `intervals.py:1` restates the spec's wording. Unrecorded. `whole_seasonal_blocks` supplies 8,690 of 12,530 scored rows, so most coverage numbers calibrate on contemporaneous same-month errors across years. Impact: "90 % coverage within 5 points" (§13.10) would be evaluated on a distribution the spec did not describe, under a label that says it is the one the spec described. Related: REQ-013 (§10.7), REQ-023.

**F-020 · code/spec · The rung-1 baseline the model will be gated against is narrower than §10.4/§10.8 specify, and the omissions are recorded nowhere.** Evidence: `intensity.py:64-83` is a plain employment/establishments ratio shrunk to the national published aggregate with `k=5.0`; §10.4 asks for a "robust" intensity shrunk toward "regional/national" values; §10.8 rung 1 adds "with robust historical adjustment"; §10.9 reinterprets that phrase as precedent for composition; `grep -i 'regional|robust' specs/deferred_items.md` → nothing relevant. §10.8 selection logic (`runner.py:353-387`) is pinned only by membership/truthiness tests; reversing `FALLBACK_ORDER` leaves the suite green; `preferred_estimator_by_month` is read by no test. Impact: §13.10's comparand may be a weaker estimator than the spec names, and the manifest cannot say so.

**F-021 · process · The roadmap's completed-stage blocks are single lines of 6.6–13.2 KB that accrete dated corrections in place; nothing states how the markers compose, and the spec's "authoritative" stamps defer to them.** Evidence: line sizes over time (Stage 3 SHIPPED 1,143 → 11,323 B; Stage 4 SHIPPED 2,276 → 13,199 B, 14 date mentions); markers at HEAD CORRECTED 8, SUPERSEDED 4, UPDATED 2, RESOLVED 2, SETTLED 1, RE-MEASURED 1, AMENDED 1; same-day reversals (`035d9f4` 10:53 → `726d487` 12:07; `190e192` 13:14 → `b50c544` 14:28); a "keep both" merge (`be70360`, PR #12) duplicated the Stage 4 block on main for two hours and revived two just-fixed false claims (`3be0275`'s message); spec Rollout l.2303 "Stage stamps below are authoritative" while the Stage 3/4 stamps say their substance "lives in the roadmap block". Impact: the inherited-contract text a later stage must read is a palimpsest whose correct current statement is whichever marker is latest, read by a human; the memory notes record that this is already costing review time.

**F-022 · spec/process · For three persisted tables and one config block the spec is a post-hoc description of code, and it now depends on code symbols and dated measurements.** Evidence: §7.13 (`9a58a0e` 09-07) trails `BASELINE_RESULT` in `contracts.py` (`627c736` 09-05); §7.14/§7.15 (`297d657` 09-09) trail `validation_scoreboard` persistence (`5d853fd` 09-07); §7.14's `constraint_set_hash` description was corrected 3 h 20 m after being written (`c4bbf4e`); Appendix A's comments name `contracts.VALIDATION_SWITCH_KINDS`, a test file, and a private validator; §7.14 l.781-784 carries "measured 2026-09-09 … null on all 12,530 scored rows" as the justification for a MAY. Impact: for these sections a reader cannot use the spec to detect code drift; renaming a symbol rots the spec.

**F-023 · spec/roadmap · Unnumbered MUSTs are owned by no stage.** §7 preamble (`run_id` + schema version on every table — no table has either); §7.8/§9.3's three soft constraint classes (declared, produced by nothing; `bounds.py:75-76` cites Stage 3 as the producer, which shipped none; D-061 open); §10.9 and §13.8's decline paragraph (added post hoc; in no `Spec:` line); §17.2's ninth property (handed Stage 2 → 3, implemented by neither); §16.1's manifest MUST (four of nine commands write none); §13.6's size-share and rank metrics (assigned to Stage 4 by range, infeasible before Stage 6). Evidence: script cross-check in Appendix 9.2; D-057, D-059, D-061. Impact: a `derive-roadmap` resume will not see these as gaps because the gap table has never been extended past the 76 ids of 2026-09-03.

**F-024 · test · Coverage is broad but several load-bearing witnesses cannot fail on a wrong answer.** (a) Baseline and validation goldens were regenerated from the code under test (`a64eba5`, `0571e15`) with no independent oracle — pure drift pins; only the constraint and national-size goldens carry hand-derived values. (b) §17.2 "generated toy tables" are nine fixed literal systems (`test_constraint_properties.py:1-90`, no generator; contrast `test_reconcile_properties.py`'s seeded 200 trials). (c) Twelve prose-pin tests assert sentences exist (Appendix 9.7); two pin the date `2026-09-08` inside manifest reason strings (`test_stage4_acceptance.py:281`), so re-measuring breaks the suite and a wrong measurement never does. (d) The only §13.2 step-3/6 witnesses rest on one March and skip silently. (e) All CLI idempotence tests run both invocations in one process and compare Parquet only — a `datetime.now()` in any JSON manifest passes. (f) `SolverError` (`bounds.py:216-223`) and `reconcile`'s exit-1 branch have zero tests. (g) Four fail-closed arms in `anchor.py`/`allocate.py` survive mutation with 160 tests green (reconcile subagent's `/tmp` mutants: negative-residual halt, exactly-one-national-row, `anchored` term, missing-basis refusal). (h) `test_identity_rule.py::test_branch_is_always_exactly_one_of_three` parametrises two of three branches; `decline` — the branch that occurred — is never produced. Impact: green means "unchanged", not "correct", for the goldens; the fail-closed surface is thinner than its docstrings claim.

**F-025 · code/config · Fourteen config keys govern nothing yet fold into `run_id` and `config.resolved.yaml`; `ValidationConfig` is frozen by the run-id policy; propensity weights are hardcoded despite §13.2's "configurable".** Evidence: `grep` finds no reader for `storage.immutable_raw`, `sources.{qcew,qcew_size,cbp}.enabled`, `sources.cbp.fail_on_unknown_disclosure_regime` (build raises regardless, `build.py:211-216`), `reconciliation.{single_margin_method,max_projection_iterations,integerization_tiebreak}`, `baselines.composite_fallback`, `validation.{minimum_missing_set_size,include_random_mask_sanity_check}`, `promotion.*`; `project.analysis_mode=realtime_asof` validates and is ignored; `propensity.py:31` `del config`, `:75-77` literals `0.5/0.3/0.2`. D-064 tracks four; the 2026-09-07 "44-key scan" missed the rest. `config.py:185-188`: "NO FIELD MAY BE ADDED OR REMOVED". Impact: a run's record claims settings no code backs; two runs with different masks can share an id; the config cannot evolve without orphaning every run directory, and no migration or config-versioning decision is recorded.

**F-026 · code · Fail-closed paths raise builtins outside the `LoggingEmploymentError` hierarchy the conventions prescribe, and no test references the base class.** Evidence: 18 `raise ValueError` sites in ingest/harmonize/store/base/classification; `rows.py:129-139`, `flags.py:46-49`, `system.py:134` (`FileNotFoundError`), `runner.py:368`, `regimes.py:316,328`, `recover.py:76,110`, `draws.py:82`, `anchor.py:175` (`TypeError`), `contracts.py:684` (`FileNotFoundError`, pinned by `test_cli_paths.py:102`); `grep -rn LoggingEmploymentError tests/` → 0. Impact: a CLI wrapper distinguishing spec failures from programming errors cannot; a subclass silently dropping the base passes the suite.

**F-027 · deferral/process · Deferral hygiene is honest but the backlog is unowned: 22 of 39 open items are overdue, nine of them against ticked Stages 1–3; tracking is split across five places; register pointers rot.** Evidence: §4.1 table and §4.2; the 14-item unregistered-work audit (`21d1ce0`) found more open work than any plan's completion protocol; eight ticked items cite a docs-only commit; six line cross-references are stale; the D-057/D-059 pair contradict each other about `build-harmonized`; `specs/completed/stage4-harness-completion.md`'s `Closes:` line names an item the same document says it did not close. Impact: the roadmap's Completion rule ("unmet rows exit via a new stage or a written deferral") is being met by writing, not by owning.

**F-028 · roadmap/dependency · A spec-required baseline and a "required" model component arrive after the gate that needs them, with no re-gate step; Stage 5's dependencies are absent.** Evidence: §10.5's harvest baseline declines in all 1,227 rows by design until Stage 7; §11.1 lists H under "Required components" while Appendix A ships `include_harvest_factor: false`; `PromotionConfig`'s three thresholds are read by nothing; `jax`/`numpyro`/`arviz` absent from `pyproject.toml`/`uv.lock`; `reconcile_draws` takes `ReconciliationInputs` (recorded in the roadmap only). Impact: the §13.10 decision would be taken against an incomplete comparand and a model missing a component the spec calls required; either the promotion record is re-run after Stage 7 or §11.1 is wrong — the roadmap says neither.

**F-029 · spec · Separation of duties for disclosure approval was dropped in synthesis.** Evidence: ChatGPT l.613 ("model developers should not be the sole approvers of disclosure-sensitive outputs"), l.609 (peer review, model cards, change logs); spec §7.12 carries a free-text `reviewer`, §14.1 three statuses, no approver constraint (grep). Impact: INV-015's "permission to publish is a separate decision" has no actor separation; Stage 8's `disclosure-review` can be run by the modeller and satisfy REQ-027 as written.

### Low

**F-030 · test · One regime supplies 69 % of all scored rows** (`whole_seasonal_blocks` 8,690 of 12,530; the next largest 600). Per-regime scoreboards are unaffected; any pooled comparison would be dominated by one design. Unrecorded.

**F-031 · docs · Submodule `CLAUDE.md` files and the root file carry claims already false at HEAD.** `baselines/CLAUDE.md` gotcha 5 warns about two `spec:NNN` citations that `c7200a5` had already replaced (the file was authored on a branch without that commit); `ingest/CLAUDE.md` cites the spec at four line numbers that all land on unrelated text; the `slow`-marker count differs between `CLAUDE.md` ("one unit test and four integration modules"), D-065 ("three sites") and the tree (six); `runs/_baseline_pre_stage4c/` exists while the roadmap says `runs/` holds exactly one directory.

**F-032 · code · §13.6's median APE is nulled for the whole estimator if any scored truth is zero** (`metrics.py:107-111`) rather than computed over the safe subset with its own denominator, which is what "where denominators are safe" asks.

**F-033 · test · `test_config.py::test_appendix_a_config_parses` parses a literal shaped by the code**, not Appendix A (seven sources and the `model:` block removed, `baselines:` and two disclosure keys added). See F-012.

**F-034 · tooling · No type checker, no coverage tooling, no `pytest-xdist` (the memory note "suite is parallel" is stale), and the 415-rule ruff set is declared nowhere in the repository** (`pyproject.toml` has no `select`; `ruff check --show-settings` resolves to `pyproject.toml` yet enables 415 rules — whether 0.16 changed defaults or a config exists outside the searched locations is open, Q-12). `slow`/`network` markers are declared and never deselected; `network` is applied to zero tests.

**F-035 · code · `qcew_national_size` has no ownership column and no ownership guard**; a by-size file carrying total-covered or government rows at a national aggregation level would double-count every industry×size key silently (measured: all 17,745 fixture rows are own_code 5). Downstream stamps ownership from `constants`.

**F-036 · code · CBP `naics_vintage` is stamped from QCEW's era rule** (`build.py:223`) and declared "documented-not-measured" (`cbp.py:3-7`); the registry says CBP's predicate is `NAICS2017` for 2017–2023. If CBP 2022/2023 are NAICS-2017-coded, the INV-007 label on those rows is wrong; no deferred item.


## 6. Health assessment and risk register (Phase 4)

Ratings: `Sound` / `Watch` / `Concern` / `Blocking`.

| Dimension | Rating | Anchored on |
|---|---|---|
| Spec integrity | **Concern** | F-004, F-012, F-013, F-014, F-015, F-022 |
| Intent coverage | **Watch** | §2.4 ledger; F-002, F-003, F-005, F-023 |
| Architecture | **Sound** | §3.1; F-018 as the one overstatement |
| Correctness and robustness | **Watch** | F-006, F-009, F-016, F-017; verified reproductions |
| Test health | **Watch** | F-010 (clean-clone red), F-024; 1,356 green here |
| Code quality and conventions | **Sound** | 100 % docstrings, zero bare asserts, deterministic writers; F-025, F-026 as debts |
| Tooling and operability | **Concern** | F-007, F-011, F-034; no CI |
| Process health | **Concern** | F-001, F-008, F-021, F-027; the self-correcting habits are real but the completion signal is not |

**Spec integrity — Concern.** In practice the source of truth is the tree plus the roadmap's stage blocks, not the spec. The spec is still a truthful description of the *design* for §3–§5, §9, §12–§14 in their intent, but it is not a truthful description of the *system* for §6.1/§6.2 (layout, storage), §7 (three tables written back late; preamble unmet), §12.2 (anchor), §13 (regimes, metrics, "rolling"), §16 (commands, signatures), Appendix A (does not load) or Appendix B (unsatisfiable). Its citation surface is rotting (missing prompt source, `.md.md` names, D5, §6 Python floor). The project's own rule that a measured claim is a dated witness has now reached the normative text (§7.14). None of this makes the spec useless — it is unusually explicit about invariants, which is why the code is as principled as it is — but "the spec is authoritative" (`CLAUDE.md`) is no longer literally true and the next stage's planner should be told which sections to trust.

**Intent coverage — Watch.** Of the 76 numbered ids, 40 are `implemented` with a discriminating test, 20 are `partial`, 4 `diverged`, 3 `stubbed`, 9 `missing`/not started (Stages 5–8). Of the MUST-level requirements owned by ticked stages, the material gaps are covered by a deferral in most cases (D-049, D-057–D-061, D-071) and by nothing in the cases listed in §4.2 — most importantly INV-002's bounds half, the §9.3 margins, §13.5–13.8's missing metrics, and the "rolling" residual label. High-priority coverage that matters for the product's first customer, Stage 5: the comparand exists and is reproducible; the gate's inputs for stratum degradation and calibration do not.

**Architecture — Sound.** The implemented structure matches the spec'd one where it matters: immutable content-addressed raw store → harmonized Parquet → estimator-free constraint engine → transparent baselines through one reconciliation entry point → harness that masks the frame and rebuilds the system per replicate. Boundaries are enforced by types and closed sets (`EmployeeWeights`, `assert_declared_provenance`, `constraint_set_hash` between stages) rather than by convention. Implementation runs *ahead* of design in `reconcile/` (draw reconciliation, KL projection, matrix IPF all built without callers) and *behind* it in `validate/` (four §13 mechanisms unwired) and `ingest/` (dual route dead). Coupling is low; the one awkward seam is that `validate/` reaches into `constraints/` and `baselines/` internals to rebuild per mask, which is deliberate and documented.

**Correctness and robustness — Watch.** Idempotence is real: every Parquet write is byte-reproducible and the acceptance artifacts reproduce from `config.yaml` (I re-derived every headline count). Fail-closed is real where it was designed (unknown disclosure code, absent cross-tab, universe closure, infeasible component, retained truth under `-O`). It is *not* real at three edges: fetch (F-009), the baseline path's bounds (F-006), and the size-margin gate's employment sum (F-017); and it is latent at one (F-016). Schema enforcement between modules is strong for dtypes and names and, since plan 12, for nullity on three tables; it does not extend to `HarmonizedData.load`, to `bound_status`/`solver_status`/`mask_arm` closed sets, or to any JSON manifest. Point-in-time correctness is by construction (one final vintage per quarter; `release_vintage` is a reference key, honestly labelled), which also means the vintage regime cannot be exercised. Numerical reproducibility: seeds are explicit, tie rules are stated, selectors sort before sampling (after three separate fixes), and cross-process determinism is tested for selectors but not for CLI outputs.

**Test health — Watch.** 1,356 tests, all green here; coverage of the spec's *risks* is uneven in the way §3.5 describes: the invariants that would be expensive to get wrong (no state-sum row, anchor gate, mask in the frame, provenance closed sets) are well pinned; the surfaces that would fail silently (bounds on baselines, fetch, `SolverError`, JSON manifests, four reconcile arms) are not. The suite is red by construction on a clean clone (42 tests), which trains reviewers to ignore a module. Goldens are drift pins. Fixtures are small and two of seven directories carry provenance READMEs. Brittleness is concentrated in dated literals and prose pins, both of which the project has recognised and partially cleaned.

**Code quality and conventions — Sound.** The docstrings-as-design-record convention is followed everywhere (`interrogate` 100 %) and is the reason this review could be done; every callable says why not the obvious alternative. Zero bare `assert` in `src/` after plan 12. Module sizes are reasonable (largest 688 lines, `contracts.py`). Duplication is low (`DISCLOSED_STATUSES` retyped; two rung structures by design). Debts: builtin exceptions off the named hierarchy (F-026), fourteen inert config keys (F-025), dated literals surviving where the same pattern was fixed elsewhere (six state enumerations), and submodule docs that went stale on the day they were added (F-031).

**Tooling and operability — Concern.** No CI, no type checker, no coverage, no dependency for Stage 5, a dev-only import in the runtime path (F-007), a lint rule set of unknown provenance (F-034), run manifests without code identity (F-011), and `slow`/`network` markers that gate nothing. Logging is by `typer.echo` and per-command JSON manifests; there is no §18.2 monitoring surface. Config handling is strict and well-typed, but the run-id design has frozen it (F-025).

**Process health — Concern, with real strengths.** The spec-driven process produced principled code, an honest register, and a habit of mutation-testing fixes and re-measuring before quoting — those are not paperwork. But the completion signal has failed twice in a row (Stage 3 late, Stage 4 late and unrecorded), stage exits are re-read after shipping rather than amended, plans are retired 10–40 minutes after being written, and the corrective load has moved into roadmap prose that grows by accretion. Twelve follow-up PRs in 21 hours after Stage 4, seven touching only `specs/` or `runs/`, is the signature of a process spending its effort on the record rather than the system. The deferral register is being used both consciously (Stage 3's anchor; plan 12's declined target) and as a pressure valve (Stage 4's hard half; Stage 1's four Produces).

### Risk register

| # | Risk | Likelihood | Consequence | From |
|---|---|---|---|---|
| R1 | Stage 5 is planned against the roadmap's Stage 4 text and the spec's §13 and builds a promotion gate whose stratum and calibration inputs do not exist, whose coverage number is mislabelled, and whose comparand may be `None` | High | The gate that INV-014 makes the model's acceptance test cannot be applied as written; rework after the model is fitted | F-001, F-002, F-003, F-019, F-015 |
| R2 | A state cell acquires a finite upper bound (retired anchor, Stage 6 state×size cell, a size-arm mask) and every baseline exceeds it with `anchored_and_reconciled` written | Medium (certain by Stage 6) | INV-002 violated silently on released point estimates | F-006 |
| R3 | A transient source failure drops a quarter; the run gets a new id and every stage proceeds on a narrower window with no record | Medium | Wrong window, undetectable from manifests | F-009, F-011 |
| R4 | Stage 6 is planned against `reconcile/` as the roadmap describes it (bounded `reconcile_matrix`, a `general_method` guard "at the CLI") | High | Plan rework mid-execution; the third plan in a row whose code blocks are defective | F-018, D-041 |
| R5 | A clean-clone or CI run is attempted; the suite is red (42 tests) and the CLI cannot import; reviewers learn to ignore red | High | The clean-environment invariant is unverifiable; regressions in the 42 tests are invisible | F-007, F-010 |
| R6 | The roadmap's Stage 4/5 blocks keep accreting; a future "keep both" merge revives a corrected false claim; a planner acts on it | Medium | Wrong inherited contract acted on; already happened once for two hours | F-021 |
| R7 | The state-total product ships with zero identifying content and a release contract that cannot say the national anchor is a modelling assumption | High (it is the current state) | Disclosure and interpretation risk: every state number is model-only and the record does not say so | F-004, F-005 |
| R8 | Config evolution is frozen by the run-id policy; Stage 5 must add a `model:` block and priors (§11.12 MUST), re-iding every run directory including the Stage 4 comparand | Certain | Either the comparand is orphaned or Stage 5 works around `Config` | F-025, F-028 |
| R9 | The spec's normative text and the tree keep diverging (§12.2, §16.2, §6, Appendix A/B) and the next `derive-roadmap` resume treats the spec as authoritative | Medium | Gaps re-derived from a document that no longer describes the system | F-012, F-013, F-022, F-023 |
| R10 | The 22 overdue open items are never re-triaged; Stage 1's unmet Produces (dead dual route, no registry/dimension artifacts) are inherited as if delivered | Medium | A BLS boundary change silently drops years; provenance tables Stage 8 will need do not exist | F-008, F-027 |


## 7. Recommendations (Phase 5)

Effort: hours / days / week+. Each item names what to do, what it addresses, the risk of doing it, and how to verify it is done. Diffs are given where the change is small enough to show.

### 7.1 Before the next stage begins

**R-01 · Move `python-dotenv` to runtime dependencies** (F-007). Effort: minutes. Risk: none (re-lock). Verify: `uv sync --no-dev && uv run logging-estimates validate-config --config config.yaml` prints `OK`.
```diff
--- a/pyproject.toml
+++ b/pyproject.toml
@@ dependencies = [
     "pydantic>=2.13",
+    "python-dotenv>=1.2",
     "pyyaml>=6.0",
@@ dev = [
     "pytest>=8.0",
-    "python-dotenv>=1.2",
     "ruff>=0.9",
```

**R-02 · Guard the 42 data-dependent tests and make the suite green on a clean clone** (F-010, R5). Effort: hours. Risk: the guarded tests stop running where `data/` is absent — which is the current de facto state, made explicit. Verify: `git stash -u; mv data data.bak; uv run pytest -q` → 0 failed, N skipped; restore. Put one guard in `tests/conftest.py` and use it in the nine modules:
```python
# tests/conftest.py
REPO = Path(__file__).resolve().parents[1]
STAGED = REPO / "data" / "staged"
needs_staged = pytest.mark.skipif(
    not (STAGED / "qcew_monthly.parquet").exists(), reason="needs the gitignored data/staged layer"
)
```
and replace `HarmonizedData.load(Path("data/staged"))` with `HarmonizedData.load(STAGED)` so the tests also stop being cwd-relative.

**R-03 · Record the Stage 4 completion truthfully: amend the Exit line to what shipped, add the heading suffix, and file the stamp lapse** (F-001, F-002, R1). Effort: hours. Risk: none. Verify: `roadmap:219` reads `- [x] Stage 4: … — COMPLETE 2026-09-09, plans 11+12`; the Exit line says "nine of thirteen regimes score on the state-total arm; `rolling_origin` and `cbp_size_gaps` are open in D-071; §13.2 steps 3/6 are witnessed on the national-size arm by tests, not enforced by the harness"; a deferred item records that the §13.2 step-6 rejection and the §13.5 out-of-bounds failure are unenforced and names Stage 6 (first size-class estimator) as the owner. This is a record change, not a code change; do not implement the rejection on the state arm, where it cannot fire.

**R-04 · Amend §12.2 and §15.2 to name the anchor** (F-004, R7). Effort: hours. Risk: none. Verify: §12.2 gains a paragraph stating that when SRC-QCEW-006 declines, R_t is computed against the published national total under an establishment-closure gate as a `modeling_assumption`, cites `anchor_basis`, and names the retirement condition; §15.2 gains `anchor_basis` (or `national_constraint_status`) so a release row can say it; `Anchor.anchor_basis` is validated against `ANCHOR_BASES` at construction (one `if` + one test).

**R-05 · Enforce INV-002's bounds half on the baseline path** (F-006, R2). Effort: hours. Risk: low on D1 (every upper is null, so behaviour is unchanged — assert that in the test). Verify: `run_baselines` joins `deterministic_bounds` and either passes `Bounds` into `allocate`/`scale_into_bounds` or asserts after allocation that every estimate lies within `[selected_lower, selected_upper]` with a named error; a unit test with one finite upper reddens without the change; `test_d1_baselines` gains a bounds join. Smallest form:
```python
# baselines/runner.py, after `allocated = allocate(anchor, outcome)`
violations = {c: v for c, v in allocated.items() if not bounds.contains(c, v, tolerance)}
if violations:
    raise BoundViolationError(reference_month, estimator.estimator_id, violations)
```
with `bounds` built once per run from `deterministic_bounds.parquet` (`Bounds.upper_of` already treats `None` as +∞).

**R-06 · Make `fetch` fail closed on a non-200 or empty body, and record fetch failures** (F-009, R3). Effort: hours. Risk: the CBP-2024 absence becomes an explicit skip that must be configured (an `expected_absent` list or a `--allow-missing` flag) rather than a silent `continue`. Verify: a `MockTransport` returning 500 for one quarter makes `fetch --source qcew` exit non-zero and write no manifest row; the 2024 CBP case passes only when declared.

**R-07 · Stamp code identity into every run manifest and record output hashes for `solve-bounds`** (F-011, R3). Effort: hours. Risk: none (manifests only; `run_id` unchanged). Verify: every `*_manifest.json` under `runs/<id>/` carries `code_commit` (`git rev-parse HEAD`, or "dirty:<sha>") and `uv_lock_sha256`; `solve_bounds_command` writes `bounds_manifest.json` with three output hashes; `test_constraint_cli.py` asserts the keys. Do not put the commit into `run_id` (that would re-id on every commit); put it beside it so staleness is *detectable*.

**R-08 · Fix Appendix A or stop calling it the reference: make it load** (F-012, F-033, R9). Effort: hours. Risk: none. Verify: a new test loads the Appendix A fence verbatim through `Config.model_validate` and passes; `config.yaml`'s header cites `§` not lines; `test_appendix_a_config_parses` is renamed or made to read the spec. Either add the `baselines:` block and the two disclosure widths to Appendix A and move the seven inactive sources and the `model:` block into a clearly-labelled "future blocks" fence, or make `SourcesConfig` accept the inactive sources with `enabled: false` (the second is the smaller code change and keeps the spec's picture).

**R-09 · Decide what `rolling_origin` scores before Stage 5, or re-scope REQ-022 explicitly** (F-002, D-071, R1). Effort: days (design + implementation) or hours (re-scope). Risk: design is a genuine open question; the cheap honest option is to declare in the roadmap that REQ-022 is *not* closed by Stage 4 and is a Stage 5 precondition. Verify: either `rolling_origin` produces `MaskTarget`s on the truncated frame and scores at least one estimator per origin with `assert_no_future_rows` binding (the guard can then fail), or the roadmap's Gap-closed line for Stage 4 drops REQ-022 and Stage 5's Consumes names it.

**R-10 · Re-label or re-implement §10.7's intervals** (F-019, R1). Effort: hours (relabel) / days (rolling). Risk: relabelling changes `INTERVAL_SOURCES` and the golden. Verify: `interval_source` reads `cross_sectional_loo_ensemble` and §10.7/§13.7 say which one the coverage gate reads; or, if rolling is implemented, the residual pool for a cell at origin t contains only residuals from t' < t.

**R-11 · Re-triage the 22 overdue items with an owner each** (F-027, R10). Effort: hours. Risk: none. Verify: every open item in `deferred_items.md` carries either a `Stage N` target or a named trigger and a "Size:" line; the six Stage 1 items (D-049, D-057–D-060, D-063) get a ruling — implement or amend the roadmap's Stage 1 Produces block; D-057 and D-059 stop contradicting each other.

### 7.2 During the next stage (Stage 5)

**R-12 · Add the metric families Stage 5's gate needs, or amend §13.10 to the metrics that exist** (F-003). Effort: days. Verify: `metrics.py` emits stratified coverage/WAPE by state size, region and gap duration (the strata exist as columns), ‖Ax−y‖₁/∞ over the masked component's hard rows, and an infeasible-component rate; or §13.10 loses the stratum clauses with a recorded reason. Fix the median-APE nulling (F-032) in the same pass.

**R-13 · Write Stage 5's plan against the tree, not the roadmap block** (R4, F-018, F-028). Verify: the plan's Consumes names `ReconciliationInputs`, `Bounds`'s key semantics, the absence of `jax`/`numpyro` in the lock, the inert `PromotionConfig`, the `None` comparand case, and the missing H component — and states whether the promotion record is re-run after Stage 7.

**R-14 · Decide the config-evolution policy before adding the `model:` block** (F-025, R8). Options: (a) accept a one-time re-id of every run directory and re-run the 24-second chain plus the 11-minute validate to regenerate the comparand under the new id; (b) version the config in `run_id` so that adding a block with all-default values leaves existing ids alone. (a) is simpler and honest; record it as a decision. Verify: the decision is in the Rollout block; `runs/` after Stage 5 holds directories whose ids the current `config.yaml` reproduces.

**R-15 · Pin the fail-closed surface that mutation showed unpinned** (F-024, F-026). Effort: hours. Verify: tests exist for `SolverError`, `reconcile`'s exit-1, the four reconcile arms, the `decline_kind` closed set, R-BREAK-5's tie, and INV-004's unknown-class refusal; each new test is shown to fail under the mutation it targets.

**R-16 · Measure, then record, the §9.3 margin decision** (F-005; strengthened by §10). Effort: hours to fetch and measure; days if a margin is then built. First step: fetch the D1 state slices for industries 113, 1133 and 11331 and for total ownership (own_code 0) at 113310, and count, month by month, how often each is disclosed where 113310 is `N` (regional totals need no measurement — QCEW publishes none for 113310). Verify: a deferred item or spec note states the measured disclosure pattern and either "no usable parent or ownership margin exists on D1" or a Stage 2 amendment (registry rows, new cell kinds, `size_margin_rows`-style builders, and §13.2 step-4 parent masking in `validate/recover.py`) scheduled before Stage 5 consumes `deterministic_bounds`. Note the disclosure consequence: with 1133 → 11331 → 113310 single-child (D6), a disclosed parent cell is an exact reconstruction of the suppressed value and a live REQ-027 case, not merely a bound.

### 7.3 Backlog

- Tighten LP endpoints for integer cells when the MILP is skipped (F-016): `ceil(lower − tol)`, `floor(upper + tol)` in `classify_bound_status`'s caller; one property test with a fractional coefficient.
- Compare the employment sum in `assert_size_margin_compatible` for years with no suppressed class (F-017); one test.
- Give `reconcile_matrix` a bounds parameter or say in its docstring and the roadmap that it is unbounded (F-018).
- Populate `source_publication_date` from the response headers (`Last-Modified`) and make harmonized `snapshot_id` the retrieval digest, or add a `retrieval_id` column (F-010).
- Enforce `mask_arm`, `bound_status`, `solver_status`, `interval_source` closed sets in `assert_declared_provenance` (D-082).
- Replace the twelve prose-pin tests with behavioural ones where a behaviour exists; delete the date pins (F-024).
- Regenerate the baseline and validation goldens only with a hand-derived oracle row beside the whole-frame `equals` (F-024).
- Add cross-process idempotence for one CLI command including its JSON manifest (F-024e).
- Route the eighteen bare `ValueError`s through named errors (F-026); add one test that every raised error in `src/` subclasses `LoggingEmploymentError`.
- Derive the six D1 state enumerations from the run manifest (D-062's rule) in `interfaces.py`, `historical.py`, `config.py`.
- Add `pytest-cov` and a type checker; declare ruff's `select` explicitly so the 415-rule set is reproducible (F-034).

### 7.4 Spec and process changes

1. **Amend the spec where the code's choice is better and undocumented** (§3.3 rows 1, 2, 7, 8, 12, 14, 17, 21, 23): §12.2 anchor; §9.6 MILP trigger as a width heuristic *plus* ceil/floor; §16.2 signatures; §10.4/§10.8 rung 1 as implemented (or a deferral); §10.7 "rolling" → what is computed; D5 to what Stage 0 measured; §6 Python floor; Appendix A as above; Appendix B step 6 → "verifies that no national employment margin can be enforced (SRC-QCEW-006) and builds the national size margins", step 7 → "computes LP bounds for every target cell and records that state cells are unbounded". Mark each amendment with the plan or commit that made the choice.
2. **Extend the roadmap gap table** for post-synthesis requirements (§10.9 R-COMP-1..11, §7.13, §13.8 decline paragraph, R-BREAK-1..5, R-S4C-1..20) and for the unnumbered MUSTs in F-023, each with an owning stage or a recorded decline.
3. **Change the roadmap's stage-block format**: freeze a completed stage's block to a short "what a later stage inherits" list, and move measurements and corrections to a dated `specs/findings/stage-N-log.md` (multi-line, mergeable). Add one rule: a marker (`CORRECTED`, `SUPERSEDED`) replaces the sentence it corrects; it does not append to it.
4. **Tighten the stamp protocol** so a tick and a stamp cannot be separated: one commit ticks the roadmap heading (with suffix), writes the spec stamp, and retires the plan, and a test under `tests/unit/test_specs.py` asserts that every `[x]` stage heading has a suffix and a matching `> Stage N: COMPLETE` stamp. That test would have failed on both lapses.
5. **Deferred items**: give every item a stable `D-nnn` id (the ledger in §4 is a starting point), a target or trigger, and an owner; require that a plan's `Closes:` line be reconciled at retirement (plan 12's was not).
6. **Re-scope the remaining roadmap** (view below).

### 7.5 Is the remaining roadmap still the right plan?

Mostly yes in *order*; no in *sizing and entry conditions*. The staging — model after harness, size model after state model, proxies and governance last — is still right, and the review-informed decision to score baselines before building the model has already paid for itself (the harness surfaced the anchor, the composition rules and the mask-in-the-frame property). Three changes:

- **Insert a short "Stage 4.5" (or a Stage 5 precondition list) that is record-only**: R-01 to R-11 above. Stage 5 should not start from a roadmap that says REQ-022 is closed, a spec that says N_t is compatible, and a suite that is red on a clean clone. This is a day of work and it removes R1, R5, R7 and R9.
- **Split Stage 5's promotion gate from Stage 5's model.** Fitting the state-total model and building the §13.10 gate are different deliverables with different inputs; the gate's inputs (stratified metrics, a defined comparand including the `None` case, a rolling-origin number, the harvest baseline) are not all Stage 5's to produce. Either make the gate a Stage 5b that runs after Stage 7 delivers §10.5 and H, or amend §11.1 and §13.10 to say the first promotion decision is provisional. The roadmap currently says neither, and Phase 3's acceptance ("required baselines are beaten or the simpler model is retained") is satisfied by either outcome anyway.
- **Move the §9.3 margin question and the size-arm harness wiring into Stage 6's Consumes explicitly**, since Stage 6 is the first stage with a size-class estimator (where §13.2 steps 3/6 and §13.5's gate can fire) and the first with state×size cells (where INV-002's bounds half matters). Stage 6's block already inherits the `integerize` bounds; it should inherit F-006, F-016, F-018 and D-071's `cbp_size_gaps` half too.

Stage 9 can stay optional. Stage 8's exit needs the same treatment as Stage 4's had to have: the Appendix B scenario must be rewritten before it can be the retirement gate.


## 8. Open questions

Things I could not resolve from the material. Each names what would settle it.

- **Q-01** *(Resolved 2026-09-10: `specs/logging-prompt.md` was added by `c7abb05`; Appendix C's line ranges for it hold — §10.1.)* Remaining: should §2.1 and Appendix C cite the tracked file names?
- **Q-02** Is the Stage 4 tick without a spec stamp (`771dabe`) a deliberate deferral pending plan 12, or the same omission as Stage 3? No commit message or deferred item says; which of the three completion dates is authoritative?
- **Q-03** What should `rolling_origin` and `cbp_size_gaps` score (D-071)? Until decided, REQ-022 is unmet in substance and the roadmap says it is closed.
- **Q-04** Is §10.7's "rolling" meant as time-ordered? If yes, the coverage/CRPS numbers need a redesign before §13.10's coverage gate reads them; if no, the label and the spec wording should change.
- **Q-05** Which "preferred transparent baseline" governs §13.10 — §10.4's designation, §10.8 rung 1's fused estimator, or `preferred_baseline` (which may return `None`)? Only the roadmap answers; the spec has three phrasings and no `None` case.
- **Q-06** Was the omission of "robust", "regional" and "historical adjustment" from the rung-1 baseline (F-020) a decision? Nothing records it.
- **Q-07** Is the §10 preamble's "same hard bounds" clause for baselines deliberately deferred to Stage 6 with the `integerize` bounds, or an unowned gap (F-006)? No item names it.
- **Q-08** Will the promotion record be re-run after Stage 7 delivers the live §10.5 baseline and the harvest factor §11.1 calls "required", or is §11.1 wrong to call it required (F-028)?
- **Q-09** Is a recorded decline the intended outcome for §9.3's parent-industry, ownership and region margins on D1 (F-005), or should someone fetch `113`/all-ownership state rows and measure whether any interval narrows?
- **Q-10** Is §7's preamble (every table carries `run_id` and a schema version) still intended? No contract carries either and no stage owns it.
- **Q-11** Which stage owns the §13.5–13.8 metrics the harness does not emit (F-003)? The roadmap assigns none; Stage 4 claims REQ-023.
- **Q-12** Where do ruff's 415 enabled rules come from? `pyproject.toml` declares no `select`, no user config was found in the usual locations, and ruff 0.16.6 is far above the declared floor of 0.9. "`ruff check src tests` is clean" may not reproduce on another binary.
- **Q-13** Is the Stage 4 comparand still byte-identical under HEAD? Its sha256 matches the stamp, and the one post-mtime commit changed a write-time gate and docstrings (I read the diff), but no recorded provenance can answer this without a re-run (F-011).
- **Q-14** Are CBP 2022/2023 rows NAICS-2017-coded or NAICS-2022-coded (F-036)? The registry's predicate is `NAICS2017` for every year; the harmonized `naics_vintage` is stamped from QCEW's era rule.
- **Q-15** Does the QCEW national size benchmark's lack of classes 8–9 for 113310 (`sources.yaml:48` lists codes 1–7) reach Stage 6's design, given §11.8/§12.5 reconcile first-quarter state-size draws to national class margins that do not exist for the top two classes?
- **Q-16** What numeric tolerances does Stage 5's Exit ("within stated tolerances") refer to? §17.5 states none; §11.14 leaves ESS and the monitored-parameter list undefined.
- **Q-17** Has the full-window offline byte-identical rebuild been re-run since 2026-09-05? `data/staged` mtimes are Sep 5; the automated test covers a three-file fixture and patches `httpx`, not the socket layer.
- **Q-18** Is "reviewer approval" for golden regenerations (§17.6) recorded anywhere outside the single-author commit bodies (`a64eba5`, `0571e15`)? No PR or review artifact was found.
- **Q-19** What is `runs/_baseline_pre_stage4c/`? It is not a run-id directory, is referenced by no code, and the roadmap says `runs/` holds exactly one directory.
- **Q-20** Should the `config.yaml` toggle that can violate §10.3's MUST (`historical_may_cross_naics_vintage`) refuse, or be labelled sensitivity-only?
- **Q-21** *(added 2026-09-10)* Are BEA `SAEMP25N`/`SAEMP27N`, which the fifth review presents as available (DOCUMENTED, not verified), the same tables as the `SAEMP25`/`SAEMP27` that Rollout D6 records as discontinued 2024-09-27 on the ChatGPT review's citation? Neither document executed a BEA call; SRC-OTH-005's deferral rests on an unmeasured premise.
- **Q-22** *(added 2026-09-10)* In the state-months where 113310 is `N`, how often does QCEW disclose the parent cells at 1133, 11331 or 113, or the total-ownership (own_code 0) 113310 cell? Unmeasured — the registry fetches `industry/113310.csv` at private ownership only. D6's single-child chain means a disclosed 1133 or 11331 state cell would exactly reconstruct the suppressed 113310 value (§10.3).


## 9. Appendix

### 9.1 Commands run and output

All from the repository root at `c4bbf4e` (clean tree; `data/` and `runs/` present).

```
$ uv run pytest -q -p no:cacheprovider
1356 passed in 420.81s (0:07:00)
uv run pytest -q -p no:cacheprovider 2>&1  933.49s user 1871.55s system 665% cpu 7:01.27 total
EXIT: 0

$ uv run ruff check src tests
All checks passed!
$ uv run ruff format --check src tests
171 files already formatted
$ uv run interrogate src
RESULT: PASSED (minimum: 100.0%, actual: 100.0%)
$ uv run logging-estimates validate-config --config config.yaml
OK: 113310 / private / states_dc / 2017-01..2024-12
$ uv run logging-estimates registry verify --config config.yaml
OK: registry verified
$ uv run logging-estimates --help          # 9 commands: validate-config fetch build-harmonized build-constraints solve-bounds run-baselines reconcile validate registry
$ uv lock --check
Resolved 38 packages in 3ms
$ uv run ruff --version                   # ruff 0.16.6
$ uv run python --version                 # Python 3.14.0
$ uv tree --frozen --no-dev | grep -i dotenv   # (nothing)  → python-dotenv is dev-only
$ uv pip list | grep -i xdist             # no xdist
$ uv run ruff check --show-settings src | grep -E 'Settings path|^linter.rules.enabled'   # pyproject.toml; 415 rules
```

Read-only measurements made in-session with polars/python (no artifact written):

```
qcew_monthly rows 4812 | state rows 4716 | months 96 | states 50
observation_status: observed 3462, suppressed 1227, true_zero 27; suppression share 0.2602
deterministic_bounds: 4775 rows; observed 3534, partially_identified 14, unbounded 1227
disclosure_flags: exact_reconstruction_flag 0, narrow_feasible_interval_flag 1
validation_manifest regimes: 9 score (600/600/360/600/120/600/600/8690/360 rows), rolling_origin & cbp_size_gaps scored=0 with reason,
  retrospective_smoothing vacuous_on_registry, preliminary_to_final_vintage cannot_run_on_d1
validation_scoreboard shape (270, 13); output hash d4e1187b… matches the stamp
Config.model_validate(<Appendix A YAML>) → 11 errors (7× sources.* extra_forbidden, model extra_forbidden,
  baselines missing, disclosure.narrow_interval_{absolute,relative}_width missing)
staged snapshot_id values: qcew_monthly {'2017q1',…} (32); qcew_national_size {'2017_q1_by_size',…} (8); cbp_state_size {'2017',…} (7)
runs/source_manifest.parquet snapshot_id: 64-hex digests (47 rows: qcew 32, qcew_size 8, cbp 7)
git: 415 commits 2026-09-03..09-09; first-parent 96; merges/PRs #1–#18; no force-push to origin/main
spec/roadmap/deferred edit counts: 18 / 28 / 38 commits
roadmap long lines: 217 (11,322 B), 224 (6,660 B), 229 (13,198 B)
annotation counts (roadmap): CORRECTED 8, SUPERSEDED 4, UPDATED 2, RESOLVED 2, SETTLED 1, RE-MEASURED 1, COMPLETED BY 1, AMENDED 1
deferred_items.md: 84 checkboxes (45 ticked, 39 open); removed-checkbox scan over all 38 commits: every removal is a same-commit tick or the one retitle (e34ef16)
commits touching validate/ after the validation artifacts' mtime (2026-09-09 18:28): c4bbf4e only — code change confined to contracts.assert_required_columns_present
```

### 9.2 Roadmap ownership cross-check (script output)

```
numbered ids in spec: 76
ids owned by no stage Gap-closed line: []
ids owned by 2+ stages: 32 (e.g. REQ-029: stages 1,2,5,8; SRC-QCEW-006: 0,1,2)
table ids: 76; missing from table: []
lines containing MUST in spec: 85
```

### 9.3 Spec and roadmap edits after each stage began (git-history subagent; classifications spot-checked by reading the hunks)

| Commit | Date | File | Classification | What changed |
|---|---|---|---|---|
| `41f4372` | 09-05 11:08 | spec Stage 1 stamp | correction-of-false-claim | "EMP = 0 … recorded as suppressed" → "withheld … employment null"; 1,227/4,812 → 1,227/4,716 |
| `adc52c2` | 09-05 14:44 | spec Stage 2 stamp | correction-of-false-claim | "fires exactly once" → dated measurement; non-rectangular panel; DC absent |
| `6eff915` | 09-05 14:53 | spec Stage 2 stamp | clarification | re-validation of Stages 4, 7, 8 |
| `5f747fa` | 09-05 17:28 | roadmap | clarification | Stage 3 ticked without suffix; SHIPPED block asserting a `MAX_SCALE_RATIO` contract |
| `9a58a0e` | 09-07 10:32 | spec §7.13, §10.9, §13.8 | **spec-drift + new-requirement** | §7.13 declares a table code carried since 09-05; §10.9 and the decline paragraph add MUSTs after Stage 3 closed |
| `5019764` | 09-07 10:48 | roadmap 217/224 | correction-of-false-claim | plan 9 SUPERSEDED the magnitude guard; Stage 4 pointers stale |
| `be3e161` | 09-07 12:15 | spec stamps, roadmap 209 | correction-of-false-claim | Stage 3 stamp written "after the fact" |
| `84a4031` | 09-07 13:57 | spec, roadmap 217/224/230/241 | correction-of-false-claim | "four contract changes" → "the contract changes"; the anchor "recorded nowhere else" |
| `771dabe` | 09-07 17:34 | roadmap 219/229 | clarification | Stage 4 ticked without suffix or spec stamp |
| `316ddd9`/`fdeb14f` | 09-07 19:50/20:19 | roadmap 224/229 | correction-of-false-claim | comparand definition RESOLVED; earlier sentence SUPERSEDED |
| `cdcb11a`…`56ddd63` (7 commits) | 09-08 08:22–15:37 | roadmap 217 | correction-of-false-claim | which run directory the numbers came from, corrected seven times |
| `035d9f4`/`726d487` | 09-08 10:53/12:07 | roadmap 229 | correction-of-false-claim | "single-arm BY ENFORCEMENT" asserted, then CORRECTED 74 minutes later |
| `be70360` → `3be0275` | 09-08 12:10 → 12:55 | roadmap 229–230 | merge duplication | "keep both" resolution duplicated the Stage 4 block; fixed by PR #14 |
| `e34ef16`/`8ed7ecd` | 09-08 16:10/17:48 | roadmap 229, deferred | correction-of-false-claim | "gate nothing" → "gate no regime selection"; orphaning claim corrected |
| `cfc854d` | 09-09 15:23 | spec Appendix A | spec-drift | switch kinds documented after code declared them |
| `297d657` | 09-09 15:35 | spec §7.14/§7.15 | spec-drift | field lists for tables persisted since 09-07 |
| `f8fa033` | 09-09 16:02 | spec stamp, roadmap 229 | clarification | Stage 4 stamp (multi-line, "implemented by plan 11 and completed by plan 12") |
| `c4bbf4e` | 09-09 18:55 | spec §7.14, D4; roadmap 229 | spec-drift | `constraint_set_hash` "MAY be null" after measurement; D4 amended for black removal |

### 9.4 Spec-quality defect lists (three spec-ledger subagents, condensed; each item spot-checked)

*Slice A (§1–§8):* §7 preamble vs every table (no `run_id`/schema version); §7.3 omits `suppression_type`; §7.5 `employment_noise_range` ← `EMP_N` is `'0'` everywhere; §6 "3.11 or later" vs D4; §6.1 layout vs tree (no `features/`, `models/`, `publish/`; different module names); §6.2 storage vs tree; `disclosure_decision` vs `disclosure_decisions.parquet`, `validation_score` vs `validation_scores.parquet`; `validation_metrics.parquet` has no §7 contract; missing prompt source; §7.1 `size_dimension` nullable-and-required; lowercase `must` in 14 binding sentences; "Suggested" vs "Allowed" value sets; closed sets defined only in code; §9.2 vs §7.7 key; §3.4/§5.5/§2.2/§8.6 intent-based MUSTs; §7.12 `dominant_employer_linkage_flag` vs §3.6; §2.2/§3.2 fast path vs `decline`; §7.14 dated measurement; §7.14 redundant key (seed + replicate); SRC-QSIZE-003 Q1 vs March; SRC-QCEW-005 weakly testable; §7.4 March definition has no field; §5.4 seed names vs registry; D5 stale; §1.2 points at §21 for decisions that accrue elsewhere; §8.6 compound bullets; BEA presented as available in four places.

*Slice B (§9–§13):* §9.1 vs §9.8 model labels; four names for "exactly recoverable"; five names for "hard constraint"; three for the feasible set; three "preferred" baselines; §10.8 rung 1 undefined; R_t/M_t used before definition; §12.2 infeasible under `decline`; §12.3 presumes finite U; §9.6 text vs Appendix A MILP key; undefined tolerances/floors/"unusually narrow"; §13.10 untestable terms; §11.14 untestable terms; §11.13/§11.8/§13.1 obligations on what the implementation "claims"; over-specification (warm starts, bisection, noncentered, "carried by the type"); §10.9/§13.8 owned by no `Spec:` line; roadmap Stage 2 cites "§9.4 provenance" (§9.4 is rounding); CON-003 two ranks vs one column; §9.2 divergence documented only in code; §13.3's vintage regime infeasible on D1; §13.5 gate vacuous on target 1; "configurable propensity" with nothing to configure; §13.2 step 8 vs §13.10; §11.1 H required vs disabled; §11.3 exact vs σ_y; §11.12 priors vs Appendix A; Appendix C file names; §13.6 size metrics infeasible for Stage 4; §10 intro untestable until §11; §9.4 strict inequality not LP-encodable; §9.7 quarantine undefined; three coinages for pseudo-suppression; A_{s,t} monthly vs quarterly; §11.13 vs §13.9 duplicate lists.

*Slice C (§14–Rollout):* §14.1 statuses in no contract; §14.2 seven undefined triggers; §14.3 R_i undefined on null widths; §14.5 lowercase must + "substantially"; §15.1 names vs §7 vs run dir; `run_manifest.json` absent; §15.2 twelve fields with no §7.11 counterpart incl. `qcew_disclosure_code` on a cell QCEW never publishes; §16.1 "suggested" vs MUST; §16.1 manifest MUST unmet; §16.2 signatures vs code; §16.2 lowercase must; §17.2 "generated" vs literal; §17.2 ninth property duplicates §17.3; §17.3 item 5 untested; §18.1 items absent; §18.2 untestable; §19 unfalsifiable acceptance (negative universals, disjunctions); §19 Phase 2 vacuous on real data; §13.10 escape clause vs INV-014; 5 % relative or points; §21 stale row; Appendix A does not load; Appendix A names code symbols; Appendix B step 6 vs `decline`; Appendix C names; `config.yaml` stale line cites; Stage 3 stamp cites a symbol the roadmap never carried; Stage 4 completion record inconsistent; "states_dc" universe with no DC row; D5 stale; "stamps authoritative" inverted.

### 9.5 Fidelity subagent: raw silent drops, papered-over conflicts and introductions

Silent drops (13): ChatGPT l.325 national-benchmark fallback (accidental; consequence F-004); ChatGPT l.609/613 governance separation (accidental; F-029); ChatGPT l.495 `national_constraint_status`/`proxy_set` (unrecorded simplification; now material); ChatGPT l.41/615-660 budget and schedule (deliberate); Copilot l.30 / ChatGPT l.33 pre-2017 SIC bridge (deliberate via D1); Copilot l.28 `correction_reason` → `classification_status` (deliberate rename, unrecorded); Copilot l.285 bounded-simplex/projection sampler → bisection + KL (mechanism swap, unrecorded); ChatGPT l.601 unknown NAICS vintage / ownership as fail-closed conditions (accidental partial drop); Copilot l.222 exposure ablation (accidental); Gemini l.6 TPO monthly seasonality (deliberate, correctly resolved, unrecorded); Gemini l.140/287 MWR distortion (deliberate; Stage 9); literature review l.761 protection-erosion catch-all (accidental, low); ChatGPT l.696-733 API partition/cache/pagination (partly deliberate). Papered-over (10): as in F-015. Introduced (15): §16.1 CLI; §13.10 numerics; Appendix A numerics; narrowness thresholds; §10.3 rolling-median and break-adjusted variants; §13.3 CBP-gap regime; §12.3 bisection, §12.4 KL, §12.6 not-cell-by-cell; §6 stack and §6.1 layout; §3.4 mode names; §7 enums and fields (`classification_status`, `vintage_compatibility_status`, `constraint_set_hash`, `model_sensitivity_*`, `disclosure_regime`, `employment_noise_range`, `model_dependence_level`…); §14.3 R_i; CON-001..005 numbering; §10.9/§7.13/§13.8 (post-synthesis); §7.1 `access_status` enum; §13.6 rank accuracy and §13.7 anchor-distance calibration.

### 9.6 Subagent scopes

One workflow, 32 agents, 4.37 M subagent tokens, 870 tool uses, 26 minutes wall; all read-only (no edits, no pipeline runs, no writes into `runs/`; verified `git status --porcelain` empty afterwards). Scopes: one reader per source document (4); three readers over the master spec (§1–8, §9–13, §14–end); six module-family traceability agents (constraints+disclosure, reconcile, baselines, validate, ingest/harmonize/build/fetching/store/registry, cli/config/contracts/runs/errors); one git-history agent; one test-suite auditor; one plans-and-exit-criteria auditor; three deferred-item inventory agents (lines 1–512, 513–1134, 1135–1569) feeding twelve verification agents (four ticked items each); one synthesis/roadmap-fidelity agent consuming the seven readers' output. Every High finding above was re-read in the primary material by me; every "resolved" verdict was checked by a verifier against code and a test, and the ones bearing on High findings re-checked by me. Subagent judgments that I did not adopt: none rejected outright; several severities were lowered (e.g. the constraints agent's Medium on `is_hard` closed sets → part of F-024/F-026) and one raised (the ingest agent's fetch `continue` finding → High, F-009).

### 9.7 Prose-pin and source-text-pin tests (tests subagent; each opened)

`tests/unit/test_baselines_historical.py::test_the_break_adjusted_docstring_declares_its_refusal`; `tests/unit/test_constants.py::test_the_allowlist_docstring_does_not_claim_a_titles_file_defines_it`; `tests/unit/test_harmonize.py::test_the_crosswalk_docstring_does_not_call_link_type_a_census_column`, `::test_the_vendored_crosswalk_keeps_its_provenance_header`; `tests/unit/test_cbp.py::test_no_naics2022_predicate_is_ever_constructed` (`"NAICS2022" not in source`); `tests/unit/test_qcew_routes.py::test_boundary_probe_does_not_hard_code_a_year` (`"2014" not in source`; a literal 2015 passes); `tests/audit/test_susb_layout.py:153-164`; `tests/audit/test_forest_sources.py:1628-1651, 1750-1763`; `tests/audit/test_cbp_metadata.py:713-742` (three); `tests/integration/test_stage4_acceptance.py::test_exactly_four_regimes_carry_a_changed_reason` (pins `"2026-09-08"`); `tests/unit/test_validate_regime_mechanisms.py:53-72` (substring pins on reason strings); `tests/unit/test_contracts_validation.py::test_metric_name_is_not_required_and_the_reason_is_recorded`.

### 9.8 Documents read in full by me

`CLAUDE.md` and the five submodule `CLAUDE.md`; `specs/logging-employment-spec-roadmap.md` (all); `specs/logging-employment-spec.md` §1.2, §2.1–2.2, §3.2–3.6, §4, §5, §6.1, §7.2–7.5, §7.13–7.15, §8.1–8.6, §9.3, §9.5–9.8, §10, §11 intro/§11.1–11.5/§11.14, §12, §13, §14, §15, §16, §17, §18, §19, §20, §21, Appendices A–C, Rollout and all stage stamps; `specs/deferred_items.md` (all 1,569 lines); `specs/completed/*` headers; plans 11 and 12 headers and stamps; `specs/findings/source-audit-notes.md`, `stage3-plan-audit.md` head, `source-audit.md` structure; `src/logging_employment/validate/{harness,scoreboard,metrics,recover,intervals}.py` in full, `regimes.py` foot, `mask.py` head; `config.py`, `runs.py`, `disclosure/flags.py`, `reconcile/anchor.py` head, `cli.py` (validate, reconcile, validate-config, registry), `constraints/compat.py` and `bounds.py` at the cited lines, `baselines/runner.py:235-285`, `build.py:170-232`, `fetching.py:100-195`, `contracts.py` schema and regime declarations; `pyproject.toml`, `config.yaml`, `README.md`, `.gitignore`; run manifests and the pre-stage4c digests; the test files named in §3.5. The four source documents were read by subagents; I read the literature review's opening and each source's distinctive and contested lists, and confirmed the specific lines cited in F-004, F-014 and F-029.

### 9.9 Deliberately not covered

- `scripts/audit/*.py` (8,633 lines) and `tests/audit/` (683 tests) beyond their deferred items: they are Stage 0 tooling, destructive-first by design (`cbp_metadata.py` deletes extracts), and not on any production path. Not run.
- `specs/findings/source-audit.md` (6,496 lines) beyond its structure, the SRC-QCEW-006 verdict and the fields other documents cite.
- Plans 1–10 beyond headers, deviation notes, deferral references and completion stamps (they total ~35,000 lines; the plans agent read those parts).
- Any network access, any `fetch`, any pipeline command that writes into `runs/` or `data/`, and any test invocation outside the one full suite run.
- The 29 nits in `stage3-plan-audit.md` (the project's own unregistered-work audit also excluded them).
- A `uv sync --no-dev` execution (would re-sync the venv); the dependency-group claim in F-007 is from the lock and the import chain.


## 10. Addendum (2026-09-10): the prompt and a fifth review

Two documents arrived in commit `c7abb05` (2026-09-10 09:44, "spec dev"), after this review's HEAD: `specs/logging-prompt.md` (584 lines) — the "common prompt" that §2.1 names as the source of "the requested scope and epistemic discipline" and that F-014 recorded as absent — and `specs/logging-employment-research-fable.md` (517 lines, access dates 2026-09-10), a fifth research review written after the master spec and after Stages 0–4 shipped. This section revises F-014, extends the fidelity analysis of §2.2 to the prompt, and assesses the new review against the spec and the measured system. Everything marked *measured* below was re-derived from `data/staged` or `runs/f03023ac9f3a` in this session; the rest is from reading the two files and the subagent passes recorded in §10.4.

### 10.1 F-014 revised

The prompt exists and is now tracked. Appendix C's five line ranges for it (6–59, 164–205, 255–419, 439–487, 531–585) land exactly on the sections its descriptions name (objective and target; Part C; Parts E–F; Part G–H; research standards) — checked by printing the boundary lines. What remains of F-014 is Low: Appendix C cites the file as `logging-prompt(1).md` and the reviews as `logging-research-*.md.md`; the roadmap header (`:7-11`) still says "the three research reviews (`…{chatgpt,copilot,gemini}.md.md`)" and now there are four reviews plus the prompt, none with those names. **Severity of F-014 drops from High to Low**; the recommendation is a citation fix.

### 10.2 The prompt against the spec (Phase 1b, extended)

The prompt is unusually prescriptive, and the spec adopted almost all of it — which resolves several of §2.2's "introduced by synthesis" questions in the spec's favour. Confirmed adoptions (prompt line → spec): the target identities with the "where a compatible national benchmark exists" qualifier (38–50 → §3.2 verbatim); establishment- not firm-size, "do not treat … as interchangeable" (52–55 → INV-010); verify simultaneous dimensionality (141–144 → SRC-QSIZE-002, Stage 0); the suppressed-cell rules — do not read a published zero as zero, separate observed/bounded/model-only, LP/MILP sharp bounds, integrality, rounded totals as intervals, no temporal smoothness as an identity (185–200 → §2.2 row 2, §9.1, §9.4, §9.6, §9.3); the latent harvest factor and harvest-origin over mill receipts (249–253 → §2.2 forestry row, §11.4, SRC-FOR-001); the (a)–(e) restriction labels (545–550 → INV-004, verbatim); the state-total model's component list including harvest activity (277–289 → §11.1's "Required components", which is why §11.1 calls H required — the papered-over conflict in F-015 is between a prompt-mandated component and Appendix A's default, not a synthesis invention); AR(1)/random-walk/change-point with justification (302–303 → §11.2); March bounds as reference-period information and no arbitrary cap called a public bound (338–343 → §9.3, §11.9, INV-011); per-draw normalized-weight reconciliation (372–382 → §12.2, INV-012); the not-MCAR sensitivities (393–401 → §11.13); joint draws, the output field list including threshold probabilities (405–415 → §7.11, §15.4 — so `probability_thresholds_json` is prompt-sourced, not synthesis-invented); balanced rounding (417–419 → §12.6); all ten baselines including two Bayesian ablations (423–434 → §10, §13.9); the nine validation designs (443–453 → §13.3, one for one) and the metric list (455–465 → §13.5–13.8); "require the sophisticated model to outperform" (467–468 → INV-014); the five disclosure flags (475–483 → §14.2) and remedies (485–487 → §14.4); the research standards on vintages and bridges (536–544 → §5.5, INV-007).

Three things the prompt asked for that the spec dropped or narrowed, each already surfaced as a finding and now with a stronger basis:

- **"If the national benchmark is unavailable or incompatible, explain what weaker constraints can be enforced" (384–385).** This is the origin of ChatGPT l.325's fallback. The spec has no such text; §12.2 presupposes a compatible N_t; Stage 0 declined the identity; Stage 3 invented the anchor. The drop was not a source's minority opinion — it was a prompt requirement. **F-004 is strengthened.**
- **Part C's constraint inventory: "broader-industry state totals; regional totals; ownership totals" (169–180).** §9.3 lists them as permitted hard constraints; the registry fetches industry 113310 only; no stage or item owns the question of whether any of them binds. **F-005 is strengthened**: the prompt required each to be evaluated "for each month and year".
- **Part G's metrics: "state-share error; size-class-share error; … calibration by state size and suppression duration; national, state, temporal, and size-class constraint violations" (455–465).** These are exactly the §13.6–13.8 metrics `metrics.py` does not emit (F-003). The gap traces to the prompt, not only to the spec.

The prompt-fidelity subagent's exhaustive pass (130 requirements: 79 adopted, 40 adopted-narrowed, 2 dropped, 4 deferred out of scope, 5 process-only) adds the following drops with no spec trace, none consequential for the shipped system but all relevant to §2.1's claim that the prompt's "required source inventory" was retained: QCEW *annual* files (l.68 — no annual-average benchmark exists anywhere); wages, payroll and receipts as proxies (l.230 — wages are ingested and unused); timberland, active primary mills and downstream wood-products demand (l.225–229); forest-type pooling (l.319); workers' compensation and licensing feeds (l.119–121); OEWS (one mention, no stage); the bibliography and access-date fields (l.507, l.516). It also measured two Part C constraint families the review and I both raised: QCEW publishes **no regional rows** for 113310 (aggregation levels 18, 48, 58, 78 only), so "regional totals" has no source; and QCEW carries ownership codes 3 and 5 on 113310 rows, so a **total-ownership state row may exist** from which a suppressed private cell could be recovered by subtraction — never fetched, never measured (Q-22).

One place the spec is *narrower* than the prompt by choice: the prompt allows "a hierarchical logistic-normal **or Dirichlet-based** model" for shares (307–308); §2.2 resolves to logistic-normal and forbids a fixed Dirichlet latent process. That is a legitimate synthesis decision, recorded in §2.2 — but it should be read as the spec's ruling, not the prompt's. Everything under "DELIVERABLE FORMAT" and "SOURCE-ACCESS REQUIREMENT" (489–585) is addressed to the researcher and has no system counterpart, which is correct.

### 10.3 The fifth review against the spec and the measured system

The new review is a competent restatement of the same architecture the other three reached (identification first, LP/MILP bounds, a monthly QCEW spine reconciled to a national benchmark by positive weights, logistic-normal size composition anchored to annual CBP, transparent baselines, non-random pseudo-suppression, coarsening as the disclosure remedy) with a JAX/NumPyro stack that matches §6. Where it goes beyond the others, it is wrong more often than right, because it was written without the measurements Stages 0–3 made:

| Review claim or design element | Relation to the spec / system | Evidence |
|---|---|---|
| The QCEW "80/3 rule" (l.29) and an upper bound derived from it (l.124) | **Forbidden.** §2.2 row 1; roadmap Stage 2 negative exit; `test_a_constraint_warranted_by_an_assumed_threshold_can_never_be_hard` | same Gemini recommendation the roadmap already guards against; source is secondary (IBRC 2008) |
| "Each establishment has ≥1 employee, so A[s,t] ≤ E[s,t]" as a definitional support restriction (l.124) | **Contradicted by data.** *Measured:* 20 of 3,462 observed D1 state cells have `employment_value < qtrly_establishments` | QCEW reporting units can carry zero employment in a month; §9.3 is right to admit only nonnegativity; adopting A ≤ E would make some feasible sets wrong |
| Intensity prior centred at ~2 jobs/establishment (l.143), from IBISWorld's "1.8 employees per business" (l.9) | **Contradicted by data.** *Measured:* pooled disclosed employees per establishment on D1 is 5.907 (monthly 5.44–6.38) | IBISWorld's "businesses" include nonemployers; a Stage 5 prior centred at log 2 starts ~1.1 log-units below the level |
| Establishment-count proportional allocation is "likely the strongest simple baseline" and the thing to ship if the model fails (l.190, l.200) | **Contradicted by the scoreboard.** *Measured:* on `runs/f03023ac9f3a` it is the worst of {`cbp_intensity`, `share_last_observed`, `establishment_proportional`} in all nine scoring regimes (pooled WAPE 0.19–0.67 vs `cbp_intensity` 0.03–0.23) | §10.8's rung order (CBP intensity first, establishment-proportional last) is confirmed; the review's ranking is not |
| CBP tabulates employment by size class at state × 6-digit (l.33) | **Consistent** with §5.1/§2.2 row 4 and with the staged layer: 1,294 of 1,298 `cbp_state_size` rows carry employment | confirmation, not correction |
| EMPSZES codes `212=1–4, 220, 230, 241, 242, 251, 252, 254` (l.35) | **Partly wrong for this slice.** *Measured:* the 113310 state slice exposes `001, 210, 220, 230, 241, 242, 251`; `212` does not appear; `252`/`254` never occur for logging | Stage 0 recorded the observed set and warned it "is not the official set"; the review's table is typed from documentation |
| BEA `SAEMP25N`/`SAEMP27N` available (l.44, DOCUMENTED) | **Conflicts with D6** (SAEMP25/27 discontinued 2024-09-27; SRC-OTH-005 deferred, D-001) | neither document verified the table live; the recorded decision stands; open question Q-21 |
| "Is the national 113310 private monthly cell always disclosed?" (l.505) | **Answered by Stage 0/1.** *Measured:* the national row is `observed` in all 96 months; the problem is the identity (every month has a suppressed state), not disclosure | SRC-QCEW-006 `decline` |
| Fallback when the benchmark is unavailable: regional adding-up, CES shape as a soft prior, and E_113310 ≤ E_113 where both disclosed (l.185) | **Two of three moot; the third is new and worth measuring — with a correction.** *Measured:* QCEW publishes no region or division rows for 113310 (aggregation levels 18, 48, 58, 78 only), so (i) has no source; the national row is disclosed in all 96 months, so (ii) answers a problem the project does not have (the anchor problem is the untestable identity, not a missing benchmark). (iii) is not stated in §9.3 as an inequality — §9.3 l.958 admits "parent industry totals **equal to** children" — but it is derivable from that equality plus §9.2's sibling cells (113 = 1131 + 1132 + 1133 with slack cells for the siblings); and D6's verified single-child chain 1133 → 11331 → 113310 makes a disclosed state cell at 1133 or 11331 an *exact* reconstruction of a suppressed 113310 cell, not just an upper bound. Nothing fetches those industries (the slice URL is `industry/{industry}.csv` with 113310 only); whether BLS discloses them where 113310 is `N` is unmeasured | verifier votes 1/3 on my original wording; corrected here; feeds R-16, F-005 and Q-22 |
| Default time span 1990–present, NAICS-2022 focus (l.13) | **Out of scope** by D1 (2017-01..2024-12); `vintage_for_year` refuses years < 2017 | |
| Logistic-normal shares with an LKJ state-correlation prior; Dirichlet-multinomial as the annual CBP *measurement* (l.147–153) | **Already in spec** (§2.2 composition row permits DM as an observation model; §11.6–11.7) | the LKJ cross-class prior is a useful concrete choice for Stage 6 |
| TruncatedNormal per-class intensity with a LogNormal open class (l.155) | **Narrower than spec**: §11.9 uses a logit-support form on closed classes and a heavy-tailed open class; INV-011 makes the bound March-only | equivalent intent; the review also states the reference-period caveat correctly |
| "Scaled-logit map of the simplex into the box" for bounds inside the sampler (l.181) | **Alternative mechanism** to §12.3's bisection / §12.4's KL; compatible with INV-012 only if applied per draw before summaries; the spec's mechanisms are post-sampling | Stage 5 decision; not a correction |
| Aitchison distance for size-share error; per-stratum win/loss reporting (l.206–208) | **Useful concrete forms** of §13.6's size-share error and §13.10's stratum gates, both of which F-003 records as unimplemented | |
| Dynamax for the linear-Gaussian spine, Blackjax kernels, OR-Tools/PuLP for MILP (l.133, l.216, l.127) | **Tooling.** §6 and D4 name NumPyro/JAX + HiGHS via `highspy`; the shipped engine already uses `highspy` directly for LP and MILP, so OR-Tools/PuLP adds nothing | |
| "Automated fetch … blocked by robots" (l.27) | Not the repository's experience: Stage 0/1 fetched every D1 quarter with a contact User-Agent per D3 | |
| A suppressed cell "had ≥3 units to be tabulated" (l.124) | **Contradicted by data.** *Measured:* 360 of 1,227 suppressed D1 state cells have `qtrly_establishments < 3` (195 with exactly one, 165 with two); the suppressed-cell establishment count runs 1–282, median 9 | the review's picture of the missingness mechanism is typed from the 80/3 description, not from the panel |
| `disclosure_code` is "blank or N" (l.26); pipeline code flags `suppressed = code == 'N'` (l.252) | **Contradicted by data.** *Measured:* three codes on 113310 rows — `''` 17,302, `'-'` 935, `'N'` 40,875 (Stage 0); 27 staged state cells are `true_zero` on `'-'` with zero establishments | the snippet would treat `'-'` rows as observed; `constants.QCEW_DISCLOSURE_CODES` closes the set and §18.3 halts on a fourth |
| Size-class reconciliation at Q1 to the national size margin (l.183); QCEW size files "Exact" (l.61) | **Overstated.** *Measured:* 14 of 51 national 113310 size rows are `N` (classes 6–7 most years) — the very cells the engine partially identifies at widths 130–894 | the margin the review would reconcile to is suppressed in its top classes every year |
| CBP release lag "14–18 months" (l.35) | **Contradicted by data.** The 2024 vintage returned 404 on 2026-09-04 and 2026-09-05, twenty months after the reference year; `regime_for_year(2024)` raises | any schedule assuming CBP covers the window is wrong by a year (the spec's stamps already say so) |
| CBP query selects `EMP_N` for the noise range (l.260, l.272) and σ_noise "from the G/H/J flag" (l.160) | **Cannot be populated from the review's own query.** *Measured:* `EMP_N` is the literal `'0'` on all 1,298 rows; the G/H/J band is `EMP_N_F`, which the review never requests and which the harmonized table also lacks (D-026) | |
| Monthly size shares `p[s,t,k]` with seasonal `c_month` and per-month TruncatedNormal class support (l.147–155) | **Belongs to the optional extension.** §3.5 fixes the core product to March-reference annual membership; §11.9 and INV-011 make class support March-only; Stage 6's exit criterion tests exactly that | the DM observation model and the LKJ cross-class prior are fine; the monthly membership process is `contemporaneous_modeled` |

**Net assessment.** The review's value to the project is three concrete leads — the parent-industry inequality as a fallback constraint (already the subject of R-16), the Aitchison form for share error, and per-stratum win/loss reporting — and one useful caution that the spec already carries (coarsen before publishing). Its factual layer should not be admitted to the record without the corrections above: two of its bounds are forbidden or false, its prior centring and scale context are off by a factor of three, its preferred fallback baseline is the worst performer on the pilot window, and its BEA and EMPSZES entries conflict with measurements. It should be filed beside the other three reviews with a note in §2.1 saying it postdates the synthesis and was not a source, so that a `derive-roadmap` resume does not treat it as one.

### 10.4 How this addendum was checked

One workflow, 21 read-only agents (2.0 M subagent tokens, 19 minutes): a prompt-fidelity reader (every prompt requirement dispositioned against the spec with line cites), a fact-checker (38 claims in the fifth review against Stage 0's findings, the registry, the staged data and the spec: 9 consistent, 17 partly consistent, 4 contradicted by measurement, 4 contradicted by the spec, 4 unverifiable here), a design assessor (29 elements: 10 already in the spec, 8 contradicting measured reality, 3 forbidden, 4 narrower than the spec, 2 tooling-only, 2 new and worth considering), and three-lens adversarial verification (data / binding spec / refutation) of six high-impact claims. Tallies: A ≤ E is not a public fact — 3/3; the intensity prior is off the measured level — 3/3; CBP employment-by-size at state level is confirmed and the code table is not — 3/3; the BEA conflict is an open premise, not a correction — 3/3; the 80/3 bound is forbidden — 3/3; my original wording of the parent-industry point — 1/3, corrected above (the spec states an equality; the inequality is derivable; the single-child chain makes it an exact reconstruction). I re-derived every *measured* figure in §10.3 myself before the agents ran; the agents added the 360-of-1,227, the three-code disclosure set, the suppressed top classes and the CBP-lag points, each of which I checked against the cited lines.

Two refinements the verifiers made to my own claims are carried: "would make some feasible sets infeasible" is overstated — A ≤ E would not make the shipped LP infeasible (state cells carry no other constraint) but would place a false lower bound on the ~0.6 % of cells where employment is below the establishment count, which §13.5 would then report as truth outside the bounds; and the ~1.1 log-unit offset is against the establishment-weighted pooled intensity (log 5.9 − log 2 = 1.08), which the D1 data would overwhelm with 3,462 disclosed cells — the harm is in the review's downstream "establishment ≈ firm" reasoning, not in the posterior.

### 10.5 What changes in this review

- F-014: High → Low (§10.1). F-004 and F-005 are strengthened (the dropped fallback and the unowned margins were prompt requirements, not one source's opinion). F-003's missing metrics trace to the prompt's Part G.
- R-16 gains a concrete first step: fetch the 113 / 1133 / 11331 and total-ownership (own_code 0) state slices for the D1 window and measure, month by month, how often they are disclosed where 113310 is `N`; if the single-child chain is disclosed anywhere, that is both the first finite bound on a state cell and a live REQ-027 exact-reconstruction case, and Stage 2's cell kinds and Stage 4's mask (step 4: retain only the margins that would remain public) both have to change before Stage 5 consumes `deterministic_bounds`.
- New open questions Q-21 and Q-22 (§8).
- The fifth review should be filed as a post-synthesis document, not a source: §2.1 and the roadmap header should say so, and none of its bounds, priors or baseline ranking should reach a Stage 5 plan without the corrections in §10.3.
