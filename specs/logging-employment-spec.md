# Implementation Specification: Monthly State Logging Employment by Establishment Size Class

**Status:** implementation-ready synthesis, version 0.1  
**Primary use:** input to a coding agent that will first write an implementation plan and then build the system  
**Target industry:** NAICS 113310, Logging  
**Core target:** monthly private-sector QCEW-covered jobs by state and March-reference establishment-size class  
**Methodological posture:** identification first, probabilistic estimation second, release approval third

---

## 1. Purpose

This specification defines a reproducible system for estimating monthly U.S. state employment in Logging, both in total and by establishment employment-size class, when official cells are suppressed or the desired cross-tabulation is not directly published.

The system must combine:

1. immutable, vintage-aware official-source ingestion;
2. explicit compatibility checks across statistical concepts;
3. sparse public-accounting constraints;
4. rank analysis and LP/MILP feasible bounds;
5. transparent benchmark estimators;
6. a hierarchical dynamic Bayesian model;
7. exact reconciliation of every retained posterior draw;
8. pseudo-suppression validation and sensitivity analysis; and
9. a separate disclosure-risk release gate.

The coding agent must treat this document as a requirements contract. It must not silently change the estimand, substitute firm size for establishment size, convert suppression-coded zeroes into true zeroes, mix release vintages, or turn modeling assumptions into deterministic constraints.

### 1.1 Normative language

The terms **MUST**, **MUST NOT**, **SHOULD**, **SHOULD NOT**, and **MAY** are normative.

### 1.2 Required agent workflow

Before modifying code, the coding agent MUST produce a plan that:

- maps every requirement ID in this specification to one or more implementation tasks;
- identifies source, schema, solver, and modeling dependencies;
- proposes a package and storage layout;
- lists unit, integration, property, statistical, and end-to-end tests;
- separates the minimum viable vertical slice from later model extensions;
- records every unresolved decision in Section 21; and
- states which requirements cannot be implemented without additional source verification.

Implementation may begin only after that plan is internally coherent and testable.

---

## 2. Basis of synthesis and conflict resolution

The common prompt supplies the requested scope and epistemic discipline. `suppressed-cell-estimation.md` supplies the governing identification, validation, and disclosure framework. The three logging reports supply source findings and candidate implementations.

### 2.1 Elements retained from each document

| Document | Elements adopted in this specification |
|---|---|
| `logging-prompt.md` | Target tensor, required source inventory, compatibility analysis, distinction among public facts and assumptions, exact reconciliation, pseudo-suppression validation, and disclosure review. |
| `suppressed-cell-estimation.md` | Identification-first workflow; sparse constraint graph; rank/null-space analysis; LP/MILP sharp bounds; coherent-vintage rule; model-within-bounds; constrained multiple draws; realistic complementary-suppression validation; and no-release logic. |
| ChatGPT report | Most conservative source-dimensionality findings; March-reference size estimand; source-vintage and disclosure-regime governance; robust AR dynamics; logistic-normal size model; exact residual allocation; pipeline contracts; and explicit separation of identification, estimation, and publication. |
| Copilot report | Concise two-stage architecture; source compatibility; strong transparent baselines; Student-t AR(1); logistic-normal composition; bounded reconciliation; balanced rounding; and clear validation metrics. |
| Gemini report | Clear economic decomposition into establishment exposure, size shares, and employment intensity; emphasis on TPO/FIA physical activity; source-specific measurement models; and staged production pipeline. |

### 2.2 Conflicts resolved

The following decisions are binding unless later official-source verification changes them.

| Topic | Resolution |
|---|---|
| **Current QCEW suppression rule** | The implementation MUST NOT encode an asserted current “80/3” rule or any other numerical confidentiality threshold. The current public rule is not sufficiently disclosed. Use the published disclosure flag and public accounting structure. Numerical rules may appear only in synthetic validation scenarios and MUST be labeled assumptions. |
| **Meaning of a QCEW zero** | A zero paired with `disclosure_code='N'` is missing/suppressed, not a substantive zero. Establishment counts may remain available even when employment and wage fields are suppressed. |
| **QCEW size dimensionality** | The system MUST assume no direct public state × six-digit Logging × establishment-size table from QCEW unless a concrete file extract proves otherwise. QCEW size information is used as a national six-digit benchmark and, separately, broader state-sector information. |
| **CBP completeness and accuracy** | CBP is the best annual state × six-digit × establishment-size anchor, but its employment is March-centered and disclosure-protected. The parser MUST be vintage-specific and MUST retain flags, noise ranges, dropped-cell behavior, and any future disclosure-regime change. CBP values are measurements, not QCEW identities. |
| **SUSB size concept** | SUSB enterprise-size statistics MUST NOT be treated as establishment-size observations. They MAY enter a weak prior or sensitivity model with their concept preserved. |
| **BEA role** | Detailed BEA state-industry employment is optional historical context, not a required current production source. It MUST NOT be forced to equal QCEW because the universe and statistical concept differ. |
| **Size-class definition** | The core product uses a March-reference annual establishment class, denoted `k_y`. Monthly employment is attributed to that annual class. A contemporaneous monthly class is a separately labeled extension. |
| **Class support bounds** | Closed-class employee bounds are hard only for a compatible March-reference count/measurement. They MUST NOT be imposed mechanically on every month when class membership is March-defined. |
| **Composition family** | Use a logistic-normal latent composition for flexible covariance and dynamics. Multinomial or Dirichlet-multinomial distributions MAY be used as observation models for published class counts. A fixed Dirichlet allocation is not the default latent process. |
| **Forestry proxies** | TPO and FIA MUST be modeled as correlated measurements of a latent harvest factor, not as independent additive signals. Harvest-origin measures are preferred to mill-location receipts. |
| **Reconciliation** | A simple normalized residual is the required fast path. A general projection into the full feasible polytope is required when more than one valid margin or bound applies. Every retained draw must be coherent. |
| **Privacy mitigation** | The system MUST NOT add arbitrary “privacy variance” and then claim protection. Exact or narrow reconstructions must instead be withheld, aggregated, widened through an explicitly reported analytic policy, or restricted. |
| **Probabilistic backend** | The mathematical and data contracts are backend-neutral. The recommended first implementation is Python with a JAX-capable Bayesian backend; CmdStanPy remains an acceptable fallback. Domain logic MUST NOT be embedded irreversibly in one PPL. |

---

## 3. Scope, estimand, and non-goals

### 3.1 Classification decision

The source prompt supplied `1113310`. The system MUST record that value and the correction rather than silently replacing it.

```text
industry_code_supplied = '1113310'
industry_code_used     = '113310'
industry_title         = 'Logging'
classification_status = 'corrected_invalid_supplied_code'
```

The ETL MUST retain source-specific NAICS vintages and MUST verify the 113310 mapping mechanically against the applicable official concordances. Apparent code-string continuity is not a substitute for a versioned crosswalk test.

### 3.2 Core estimand

Let:

```math
E_{s,t,k_y}
```

be the number of **private-sector QCEW-covered wage-and-salary jobs** in state $s$, month $t$, at establishments classified into establishment-size class $k$ using the March reference for year $y$.

The required identities are:

```math
E_{s,t} = \sum_k E_{s,t,k_y},
```

and, when a definitionally compatible national QCEW control exists,

```math
N_t = \sum_{s\in\mathcal S} E_{s,t}.
```

The primary geography is the 50 states plus the District of Columbia. Territories or residual areas MAY be included, but only through an explicit geography-universe configuration. A national control MUST NOT be imposed on a state universe that omits components included in the national total.

### 3.3 Target interpretation

The target is the **QCEW-equivalent published value that would be present absent disclosure suppression**, not unedited respondent microdata and not a unique-person count. Published QCEW values may themselves incorporate agency imputation and revision.

### 3.4 Analysis modes

The system MUST support two distinct modes, with separate manifests and model evaluations:

1. `retrospective_final`: use coherent final vintages for historical completion and smoothing;
2. `realtime_asof`: use only data available as of a specified timestamp and retain preliminary/final distinctions.

The minimum viable product MAY implement only `retrospective_final`, but data contracts must not preclude `realtime_asof`.

### 3.5 Size concepts

The supported values are:

```text
march_reference        # required core product
contemporaneous_modeled # optional extension
```

For `march_reference`, class membership is annual. Monthly employment in a class may move outside the class's March endpoint because the endpoint defines March classification, not a hard monthly employment corridor.

### 3.6 Non-goals

The core implementation does not attempt to:

- identify individual establishments or employers;
- reproduce confidential BLS disclosure algorithms;
- estimate proprietors or nonemployer contractors as employees;
- treat CBP, SUSB, BEA, CES, TPO, or FIA as interchangeable with QCEW;
- infer monthly establishment class migration without an explicitly labeled extension;
- publish exactly reconstructed suppressed values automatically;
- use matrix/tensor completion as the primary estimator; or
- claim that a posterior interval is a public-data identified interval.

---

## 4. System invariants

| ID | Invariant |
|---|---|
| `INV-001` | A disclosed QCEW target cell is preserved exactly for its selected release vintage. |
| `INV-002` | Every hard public accounting constraint is satisfied by every released point estimate and every retained reconciled draw, within declared numerical tolerance. |
| `INV-003` | No value paired with a suppression code is interpreted as a true zero without a source-specific rule proving that interpretation. |
| `INV-004` | Every restriction is labeled as public accounting fact, definitional support, empirical measurement, modeling assumption, or sensitivity assumption. |
| `INV-005` | Only public accounting facts and valid definitional restrictions enter the deterministic feasible set. |
| `INV-006` | Rounded values enter as intervals; noise-infused, sampled, modeled, or bridged values enter measurement models, not exact equations. |
| `INV-007` | Constraints from incompatible release vintages, ownership universes, geographies, NAICS vintages, or statistical units are never stacked silently. |
| `INV-008` | The deterministic feasible interval and model-dependent posterior interval are both retained and are never relabeled as one another. |
| `INV-009` | The real-world suppression type is recorded as unknown unless a public source identifies it. Primary-like and complementary-like labels are allowed only for synthetic validation masks. |
| `INV-010` | Firm-size or enterprise-size data are never relabeled as establishment size. |
| `INV-011` | A March-reference class bound is not imposed as a hard restriction outside its valid reference period. |
| `INV-012` | Every model draw is reconciled before summaries are computed. Summarizing and then reconciling is insufficient. |
| `INV-013` | Joint draws are retained because exact totals induce dependence among cells. |
| `INV-014` | A complex model is not promoted unless it outperforms required transparent baselines under realistic pseudo-suppression. |
| `INV-015` | Public-data identification, statistical estimation, and permission to publish are separate decisions. |
| `INV-016` | A clean environment can reproduce a release from its frozen source and configuration manifest. |

---

## 5. Source hierarchy and compatibility policy

### 5.1 Mandatory sources

| Source | Required role | Hard-constraint eligibility |
|---|---|---|
| **QCEW quarterly industry data** | Monthly state and national Logging employment; quarterly establishment exposure; disclosure flags; ownership; release vintage | Yes, when geography, ownership, industry, period, and vintage are compatible |
| **QCEW establishment-size data** | National six-digit Logging size benchmark; March-defined size structure | Yes only for compatible published margins and reference periods |
| **County Business Patterns** | Annual/March state × six-digit × establishment-size counts and employment measurements | No for QCEW accounting; yes as empirical measurement with disclosure metadata |

### 5.2 Recommended sources

| Source | Role | Treatment |
|---|---|---|
| **TPO/NRUM** | Harvest-origin roundwood, residues, and related physical activity | Noisy measurement of latent annual harvest activity |
| **FIA/EVALIDator** | Harvest removals and sampling error | Noisy measurement of the same latent harvest factor |
| **National and available state CES** | Monthly movement and turning-point proxy | Predictor or bridge equation, never an exact QCEW identity |

### 5.3 Optional structural or sensitivity sources

| Source | Role | Guardrail |
|---|---|---|
| **BDS** | Broader-industry births, deaths, expansions, contractions, and transition volatility | Do not imply six-digit Logging detail that is not present |
| **SUSB** | Enterprise-size and corporate-consolidation prior | Preserve enterprise-size concept |
| **Nonemployer Statistics** | Proprietor/nonemployer activity proxy or separate expanded-universe output | Never add directly to QCEW payroll jobs |
| **BEA regional accounts or archives** | Historical broad-industry and proprietor context | Explicit bridge and source-vintage metadata required |
| **State permits, severance taxes, sales, weather, wildfire, road restrictions** | Optional monthly timing indicators | Add only after stable access and incremental validation gain are demonstrated |
| **OEWS** | Occupational or wage structure sensitivity | Low priority; not a state Logging total |

### 5.4 Seed access patterns

These are seed registry values from the research reports. The ingestion code MUST verify them and must not hard-code a “latest” year.

```yaml
qcew_quarterly:
  endpoint_pattern: 'https://data.bls.gov/cew/data/api/{year}/{quarter}/industry/113310.csv'
  response: csv
  authentication: none

cbp:
  base_endpoint_pattern: 'https://api.census.gov/data/{year}/cbp'
  response: json
  authentication: census_api_key
  predicates_to_discover: [naics_variable, EMPSZES, LFO]

bds:
  base_endpoint: 'https://api.census.gov/data/timeseries/bds'
  response: json
  authentication: census_api_key

nonemployer:
  base_endpoint_pattern: 'https://api.census.gov/data/{year}/nonemp'
  response: json
  authentication: census_api_key

fiadb:
  endpoint: 'https://apps.fs.usda.gov/fiadb-api/fullreport'
  response: source_specific
  authentication: source_specific
```

### 5.5 Compatibility gate

Before a source value can be used, the system MUST evaluate:

- reference period;
- geography universe;
- industry code and NAICS vintage;
- ownership coverage;
- employment concept;
- statistical unit;
- size concept;
- release vintage and revision status;
- disclosure/noise regime; and
- whether the value is exact, rounded, sampled, modeled, noise-infused, suppressed, or dropped.

A source difference may be bridged statistically only when the bridge is explicit and its uncertainty is estimated or sensitivity-tested. A difference in statistical unit or target universe cannot be repaired by renaming columns.

---

## 6. Recommended software and repository architecture

The methodological specification is language-independent. The recommended implementation stack is:

- Python 3.11 or later;
- `uv` for environment and lock management;
- `hatchling` for packaging;
- Polars and PyArrow for tabular processing;
- `httpx` for downloads;
- Pydantic or typed dataclasses for configuration and contracts;
- SciPy sparse matrices plus HiGHS/`highspy` for LP/MILP;
- NumPyro/JAX as the preferred Bayesian backend, with CmdStanPy as a supported alternative;
- ArviZ-compatible posterior diagnostics and storage;
- Pytest, Hypothesis, Ruff, and static type checking.

### 6.1 Package layout

```text
src/logging_employment/
  __init__.py
  cli.py
  config.py
  constants.py

  registry/
    models.py
    loader.py
    validation.py

  ingest/
    base.py
    qcew.py
    qcew_size.py
    cbp.py
    bds.py
    ces.py
    susb.py
    nonemployer.py
    bea.py
    tpo.py
    fia.py
    state_optional.py

  harmonize/
    geography.py
    naics.py
    ownership.py
    periods.py
    disclosure.py
    concepts.py

  constraints/
    cells.py
    rows.py
    graph.py
    rank.py
    bounds.py
    diagnostics.py

  features/
    state_total.py
    size_structure.py
    harvest_factor.py
    temporal.py

  baselines/
    equal.py
    establishments.py
    historical_share.py
    cbp_intensity.py
    harvest.py
    regression.py

  models/
    interfaces.py
    state_total.py
    size_composition.py
    measurement.py
    priors.py
    suppression_sensitivity.py

  reconcile/
    residual.py
    bounded_scaling.py
    projection.py
    matrix.py
    rounding.py

  validate/
    pseudo_suppression.py
    splits.py
    metrics.py
    calibration.py
    ablation.py
    reports.py

  disclosure/
    flags.py
    policy.py
    review.py

  publish/
    schemas.py
    summaries.py
    draws.py
    manifest.py
```

### 6.2 Storage layout

```text
data/
  raw/<source>/<retrieval_id>/...
  staged/<source>/...
  harmonized/...
  constraints/...
  features/...

runs/<run_id>/
  config.resolved.yaml
  source_manifest.parquet
  schema_manifest.json
  constraint_manifest.parquet
  deterministic_bounds.parquet
  baseline_results/
  posterior/
  validation/
  disclosure/
  release/
  run_manifest.json
```

Raw source objects MUST be immutable and content-addressed or checksum-verified. A rerun against the same manifest MUST NOT re-download mutable “latest” files unless explicitly requested.

---

## 7. Core data contracts

All persisted analytical tables SHOULD use Parquet with explicit schemas. Every table MUST include `run_id`, source/version provenance where applicable, and a schema version.

### 7.1 `source_registry`

One row per logical source product.

| Field | Type | Requirement |
|---|---|---|
| `source_id` | string | Stable internal identifier |
| `agency` | string | Required |
| `dataset` | string | Required |
| `landing_url` | string/null | Required when available |
| `endpoint_pattern` | string/null | Required when available |
| `access_status` | enum | `verified`, `documented`, `unverified`, `retired` |
| `frequency` | string | Required |
| `reference_period` | string | Required |
| `geography` | string | Required |
| `industry_detail` | string | Required |
| `ownership` | string | Required |
| `statistical_unit` | string | Required |
| `employment_concept` | string | Required |
| `size_dimension` | string/null | Required |
| `disclosure_regime` | string | Versioned, not free-floating prose only |
| `revision_policy` | string | Required |
| `model_role` | string | Required |
| `limitations` | string | Required |

### 7.2 `source_snapshot`

One row per immutable retrieval.

```text
snapshot_id
source_id
request_url_or_file
request_parameters_json
retrieved_at_utc
source_publication_date
reference_start
reference_end
release_status
naics_vintage
schema_fingerprint
content_sha256
byte_count
http_status
parser_version
raw_path
```

Secrets and API keys MUST NOT be written to manifests.

### 7.3 `qcew_monthly`

The QCEW parser expands the three monthly employment columns in each quarterly record to normalized monthly rows.

```text
snapshot_id
release_vintage
release_status
reference_quarter
reference_month
area_fips
area_type
state_fips
industry_code
naics_vintage
ownership_code
aggregation_level
size_code
qtrly_establishments
employment_raw
employment_value
wages_raw
wages_value
disclosure_code
observation_status
is_published_numeric_zero
is_true_zero
source_row_hash
```

`employment_value` MUST be null when the disclosure code indicates suppression, regardless of a zero-filled raw value.

### 7.4 `qcew_national_size`

```text
snapshot_id
reference_year
reference_quarter
reference_month
industry_code
naics_vintage
size_class
size_lower
size_upper
establishments
employment
disclosure_code
observation_status
```

The table MUST retain that size class is determined by March employment.

### 7.5 `cbp_state_size`

```text
snapshot_id
reference_year
state_fips
industry_code
naics_vintage
legal_form_code
size_code
size_label
size_lower
size_upper
establishments
employment
employment_flag
employment_noise_range
disclosure_status
disclosure_regime
reference_period = 'week_including_march_12'
```

The parser MUST enumerate official `EMPSZES` metadata for each vintage. It MUST NOT reuse codes from another Census product.

### 7.6 `proxy_observation`

A long-format table for TPO, FIA, CES, BDS, SUSB, NES, BEA, and optional state sources.

```text
snapshot_id
proxy_id
state_fips
reference_start
reference_end
value
standard_error
lower_bound
upper_bound
unit
coverage
industry_code
naics_vintage
statistical_unit
employment_concept
measurement_role
quality_flag
```

### 7.7 `target_cell`

One row per atomic target cell.

```text
cell_id
state_fips
reference_month
size_concept
size_class
ownership_code
industry_code
naics_vintage
observation_status
observed_value
source_snapshot_id
qcew_disclosure_code
```

For the state-total model, use a synthetic total size class such as `ALL`. Size cells and total cells MUST have distinct IDs.

### 7.8 `constraint_row`

```text
constraint_id
component_id
constraint_class
relation
rhs_lower
rhs_upper
is_hard
period_scope
geography_scope
industry_scope
ownership_scope
source_snapshot_ids
provenance_text
vintage_compatibility_status
```

Allowed `constraint_class` values:

```text
public_accounting_fact
definitional_support
empirical_measurement
modeling_assumption
sensitivity_assumption
```

Only the first two may have `is_hard=true`.

### 7.9 `constraint_coefficient`

Sparse long form:

```text
constraint_id
cell_id
coefficient
```

### 7.10 `deterministic_bounds`

```text
cell_id
component_id
rank
nullity
lp_lower
lp_upper
milp_lower
milp_upper
selected_lower
selected_upper
bound_status
exactly_identified
integer_exactly_identified
solver_status
solver_tolerance
constraint_set_hash
```

Suggested `bound_status` values:

```text
observed
exactly_recoverable
partially_identified
model_estimable
model_only
unbounded
infeasible
```

### 7.11 `posterior_summary`

```text
cell_id
model_id
model_version
run_id
posterior_mean
posterior_median
ci50_low
ci50_high
ci80_low
ci80_high
ci90_low
ci90_high
ci95_low
ci95_high
probability_thresholds_json
deterministic_lower
deterministic_upper
model_sensitivity_low
model_sensitivity_high
observed_or_imputed
reconciliation_status
constraint_set_hash
source_vintage_set
```

### 7.12 `disclosure_decision`

```text
cell_id
exact_reconstruction_flag
narrow_feasible_interval_flag
posterior_overconcentration_flag
dominant_employer_linkage_flag
coarser_output_sufficient_flag
review_status
release_action
reviewer
review_timestamp
rationale
```

Allowed `release_action` values:

```text
release_observed
release_model_estimate
release_interval_only
aggregate_geography
aggregate_time
aggregate_size
restricted_access
withhold
```

---

## 8. Ingestion and harmonization requirements

### 8.1 QCEW quarterly ingestion

`SRC-QCEW-001` The pipeline MUST ingest exact raw files and preserve their retrieval and release vintages.

`SRC-QCEW-002` It MUST parse disclosure metadata before deriving numeric values.

`SRC-QCEW-003` It MUST normalize `month1_emplvl`, `month2_emplvl`, and `month3_emplvl` to calendar months while preserving the parent quarter.

`SRC-QCEW-004` It MUST retain ownership, aggregation level, area code, size code, industry code, NAICS vintage, quarterly establishments, wages, and disclosure code.

`SRC-QCEW-005` It MUST distinguish preliminary and final observations. A final national control cannot be combined with preliminary state values in a hard equation unless revisions are explicitly modeled.

`SRC-QCEW-006` It MUST verify the state/national universe each month. If the national total includes areas outside the configured state universe, the system must add explicit residual cells or decline to enforce the national identity.

`SRC-QCEW-007` It MUST test whether the national Logging total, state Logging rows, ownership code, and aggregation level are definitionally aligned before creating a constraint.

### 8.2 QCEW size ingestion

`SRC-QSIZE-001` The parser MUST retain the March classification definition.

`SRC-QSIZE-002` The parser MUST verify actual simultaneous dimensionality from file contents, not infer it from adjacent documentation.

`SRC-QSIZE-003` National six-digit Logging size totals MAY be hard controls only for their compatible first-quarter monthly fields and release vintage.

`SRC-QSIZE-004` State-sector size data MUST NOT be relabeled state-Logging size data.

### 8.3 CBP ingestion

`SRC-CBP-001` The pipeline MUST discover the vintage-specific NAICS predicate and official `EMPSZES` values from metadata.

`SRC-CBP-002` It MUST preserve `EMP`, `ESTAB`, employment flags, noise ranges, legal form, and dropped/suppressed status.

`SRC-CBP-003` It MUST store the disclosure regime by reference year and fail closed on an unknown regime.

`SRC-CBP-004` CBP employment MUST enter as a March-centered noisy measurement, not an exact QCEW identity.

`SRC-CBP-005` CBP establishment-size counts MAY inform latent size shares, but their target-universe difference from QCEW must remain in the measurement model.

### 8.4 Forest-source ingestion

`SRC-FOR-001` TPO variables MUST distinguish harvest origin from mill receipts.

`SRC-FOR-002` FIA observations MUST retain sampling errors or confidence intervals when available.

`SRC-FOR-003` Evaluation vintages and survey cycles MUST be stored explicitly.

`SRC-FOR-004` Annual or periodic forest measures MUST NOT be mechanically interpolated and treated as observed monthly activity.

### 8.5 Other-source ingestion

`SRC-OTH-001` SUSB data MUST preserve enterprise-size semantics.

`SRC-OTH-002` BDS industry detail MUST be discovered; six-digit Logging detail must not be invented.

`SRC-OTH-003` CES series MUST retain their own industry definitions and revision vintages.

`SRC-OTH-004` Nonemployer observations MUST be excluded from the core employment total.

`SRC-OTH-005` BEA detailed employment must be treated as optional historical input and bridged explicitly.

### 8.6 Harmonization

The harmonization layer MUST create versioned dimensions for:

- state and area geography;
- NAICS code and vintage;
- ownership;
- source universe and employment concept;
- statistical unit;
- reference period;
- size concept and endpoints;
- release status and as-of timestamp; and
- disclosure regime.

Every bridge MUST have:

```text
bridge_id
source_concept
target_concept
valid_start
valid_end
method
uncertainty_treatment
verification_status
```

No bridge may be introduced solely to force totals to agree.

---

## 9. Deterministic identification engine

### 9.1 Identification precedes imputation

The engine MUST first determine what public information logically implies. Predictive history, spatial borrowing, harvest proxies, temporal smoothness, and prior distributions are not allowed in this stage.

For suppressed target vector $x$, construct:

```math
B x = c
```

or interval/equality constraints equivalent to:

```math
\mathcal F = \{x: Bx=c,\;Gx\le h,\;x\ge0,\;x_{\mathcal I}\in\mathbb Z\}.
```

For each target cell $j$, compute:

```math
L_j=\min_{x\in\mathcal F}x_j,
\qquad
U_j=\max_{x\in\mathcal F}x_j.
```

These are sharp feasible bounds under the encoded public information. They are not confidence or credible intervals.

### 9.2 Atomic cells

The state-total constraint universe is at minimum:

```text
state × month × ownership × NAICS × release_vintage
```

The size universe is:

```text
state × month × March-reference-size-class × ownership × NAICS × release_vintage
```

The engine MAY include geography, ownership, and industry sibling cells needed to exploit valid overlapping margins. Every atomic key must be mutually exclusive within a constraint system.

### 9.3 Constraint types

Hard constraints may include:

- disclosed target cells fixed to their published values;
- compatible national totals equal to state sums;
- compatible region totals equal to member states;
- compatible parent industry totals equal to children;
- compatible ownership totals equal to ownership components;
- nonnegativity;
- integrality for employment and establishment counts;
- documented size support at the valid reference period; and
- documented rounding intervals.

The engine MUST NOT encode as hard constraints:

- prior or adjacent-month similarity;
- growth-rate limits;
- seasonal patterns;
- CBP employment;
- CES estimates;
- TPO or FIA activity;
- SUSB enterprise-size values;
- assumed disclosure thresholds; or
- arbitrary top-class caps.

### 9.4 Rounding

If a source value $\tilde y$ is rounded to grid width $r$, encode:

```math
\tilde y-r/2 \le a^\top x < \tilde y+r/2,
```

with endpoint behavior taken from source documentation. Rounding rules MUST be field-specific.

### 9.5 Graph decomposition and rank

`CON-001` Build the sparse bipartite graph connecting constraint rows and target cells.

`CON-002` Decompose the graph into connected components.

`CON-003` Compute structural and numerical rank for each component and record nullity.

`CON-004` Store enough provenance to explain which public margins identify or narrow each target cell.

`CON-005` Cache reusable hierarchy matrices across periods when definitions are unchanged.

For small integer 0/1 components, an exact-rank check MAY be used to guard against numerical rank ambiguity.

### 9.6 LP/MILP procedure

1. Solve continuous LP bounds for every unknown cell.
2. If the cell is an integer count and integer feasibility can change the result, solve MILP bounds.
3. Use warm starts and component-level batching.
4. Stop and emit diagnostics on infeasibility; do not silently relax production constraints.
5. Use slack minimization only as a diagnostic to identify rounding, revision, or vintage conflicts.

For integer cells, exact identification occurs when:

```text
ceil(lower - tolerance) == floor(upper + tolerance)
```

For continuous cells, exact identification occurs when the width is within declared solver tolerance.

### 9.7 Infeasibility diagnostics

An infeasible component MUST produce:

- component ID;
- all source snapshots involved;
- candidate mixed-vintage or universe conflicts;
- an irreducible infeasible subsystem when supported; otherwise
- a minimum-slack diagnostic solution;
- the constraints with largest required slack; and
- a hard run failure unless the component is explicitly quarantined.

### 9.8 Identification output and privacy flag

Each suppressed cell is classified as:

- exactly recoverable;
- partially identified;
- model-estimable;
- model-only;
- unbounded; or
- infeasible.

Exactly recoverable and unusually narrow cells MUST be sent to disclosure review before any cell-level modeled output is published.

---

## 10. Required transparent baselines

All baselines MUST use the same source universe, training windows, pseudo-suppression masks, hard bounds, and reconciliation layer as the full model.

### 10.1 Equal residual allocation

For missing set $M_t$:

```math
\hat E_{s,t}=R_t/|M_t|.
```

Use only as a sanity check.

### 10.2 Establishment-count proportional allocation

```math
\hat E_{s,t}
=
R_t\frac{A_{s,t}}{\sum_{j\in M_t}A_{j,t}}.
```

This is the minimum fallback when only QCEW establishment exposure is available.

### 10.3 Historical state-share baselines

Implement:

- last observed state share;
- same-month previous-year share;
- rolling median share;
- exponentially weighted historical share; and
- a robust break-adjusted share.

Every estimate must be reconciled to the current residual. Historical shares must use classification-consistent periods.

### 10.4 CBP/QCEW employee-per-establishment baseline

For each state-year, estimate a robust March employee-per-establishment intensity from CBP, shrink it toward regional/national values, combine it with QCEW establishment exposure, and reconcile to the national residual.

This is the preferred transparent structural baseline.

### 10.5 Harvest proportional baseline

Allocate residual using harvest-origin volume or the estimated latent harvest factor. It is a benchmark, not a preferred standalone estimator.

### 10.6 Constrained regression baseline

Fit a regularized model for log employment intensity using only training-visible cells, produce positive predictions, then reconcile each prediction vector to the feasible set.

### 10.7 Baseline uncertainty

At least the historical-share, CBP-intensity, and constrained-regression baselines SHOULD produce empirical predictive intervals from rolling pseudo-suppression residuals. A point-only baseline cannot be compared fairly on probabilistic metrics.

### 10.8 Fallback hierarchy

If the full Bayesian model is not supported, use:

1. reconciled CBP/QCEW employee-per-establishment with robust historical adjustment;
2. reconciled constrained regression;
3. reconciled historical shares; then
4. establishment-count proportional allocation.

---

## 11. Bayesian model specification

The full model has two linked but separately testable components:

1. monthly state totals; and
2. monthly employment allocated to annual March-reference size classes.

The two components MUST have separable interfaces so the state-total model can be validated and deployed before the size model.

### 11.1 State-total exposure and response

Let $A_{s,q(t)}$ be QCEW quarterly establishment exposure applied to month $t$ in quarter $q$. Treating it as constant within quarter is a baseline modeling assumption, not a public identity.

For disclosed observations, define:

```math
y_{s,t}=\log\left(\frac{E_{s,t}}{A_{s,q(t)}+\epsilon_A}\right).
```

The latent mean is:

```math
\mu_{s,t}
=
\alpha
+u_s
+v_{r(s)}
+\gamma_{m(t)}
+\delta_{y(t)}
+X_{s,t}^\top\beta
+\lambda_H H_{s,y(t)}
+\eta_{s,t}.
```

Required components:

- state random effect $u_s$;
- region random effect $v_{r(s)}$;
- sum-to-zero month effects $\gamma_m$;
- year effects $\delta_y$;
- standardized, nonredundant predictors $X$;
- annual latent harvest activity $H$; and
- robust state dynamics $\eta$.

### 11.2 Robust temporal dynamics

The default process is:

```math
\eta_{s,t}=\rho_s\eta_{s,t-1}+\epsilon_{s,t},
\qquad
\epsilon_{s,t}\sim t_\nu(0,\sigma_{\eta,s}).
```

A Student-t AR(1) is preferred to an unrestricted random walk because Logging intensity is persistent but plausibly mean-reverting, while heavy tails allow openings, closures, disasters, recodes, relocations, and market shocks.

A sparse change-point component MAY be added only if validation shows material gains.

### 11.3 Observed-cell likelihood

Published QCEW values are exact observations of the selected QCEW-equivalent target for their release vintage. The model process may have residual variation, but there is no extra arbitrary measurement error added merely because the value is small.

A practical response model is:

```math
y_{s,t}\mid\mu_{s,t}
\sim t_{\nu_y}(\mu_{s,t},\sigma_y),
```

for disclosed training cells. Suppressed cells have no pseudo-observation.

### 11.4 Latent harvest factor

For annual or survey-cycle latent activity $H_{s,y}$:

```math
\log TPO_{s,y}
=
a_T+b_T H_{s,y}+\epsilon^T_{s,y},
```

```math
\log FIA_{s,y}
=
a_F+b_F H_{s,y}+\epsilon^F_{s,y}.
```

FIA variance should incorporate its published sampling error. TPO and FIA are not conditionally independent employment regressors after conditioning on $H$.

The MVP MAY hold $H_{s,y}$ constant within year. Monthly weather, permits, fire, or road-access indicators MAY explain deviations only after incremental out-of-sample value is established.

### 11.5 Raw predictions for suppressed state totals

For each suppressed state-month, construct a positive score:

```math
q_{s,t}
=
(A_{s,q(t)}+\epsilon_A)\exp(\mu_{s,t}).
```

These scores are not final estimates. They are inputs to the exact reconciliation layer in Section 12.

### 11.6 Annual establishment-size composition

For March-reference class $k$, define annual latent log-ratios:

```math
z_{s,y,k}
=
\mu_k
+a_{s,k}
+b_{r(s),k}
+c_{y,k}
+f_{s,y,k},
```

and:

```math
p_{s,y,k}
=
\frac{\exp(z_{s,y,k})}{\sum_j\exp(z_{s,y,j})}.
```

The core product treats $p_{s,y,k}$ as an annual March-reference structure. It does not invent large monthly movements in class membership.

### 11.7 CBP size measurement model

Where CBP state-year size counts are published, use a multinomial or overdispersed multinomial observation model:

```math
\mathbf C^{CBP}_{s,y}
\sim
\text{Multinomial}\left(C^{CBP}_{s,y,+},\mathbf p_{s,y}\right),
```

or a Dirichlet-multinomial variant when overdispersion is supported.

The model MUST account for dropped/suppressed cells and disclosure regime. CBP employment by size may separately inform employment per establishment with source-specific uncertainty.

### 11.8 National QCEW size benchmark

National QCEW Logging size data provide a compatible national benchmark for the first quarter. The model SHOULD either:

- condition annual size priors on those data; or
- reconcile first-quarter state-size draws to those national class margins when definitions and vintages match.

It MUST NOT describe those margins as contemporaneous monthly class membership beyond the documented March-based classification.

### 11.9 Employment per establishment by class

For March and each closed size class $[L_k,U_k]$:

```math
m_{s,Mar(y),k}
=
L_k+(U_k-L_k)\operatorname{logit}^{-1}(\psi_{s,y,k}).
```

For the open-ended class:

```math
m_{s,Mar(y),K}=L_K+\exp(\psi_{s,y,K}),
```

with a strongly regularized hierarchical tail prior calibrated to national QCEW size data. This is a probabilistic tail, not a public upper bound.

For non-March months, model employment intensity relative to March:

```math
\log m_{s,t,k}
=
\log m_{s,Mar(y),k}
+\theta_{m(t),k}
+\zeta_{s,t,k},
```

with strong shrinkage toward no class-specific seasonal deviation in the initial implementation. Hard class endpoints do not apply outside the valid reference period under the March-reference concept.

### 11.10 Size-class employment allocation

Construct raw class employment weights:

```math
g_{s,t,k}=p_{s,y(t),k}m_{s,t,k},
```

normalize them:

```math
\pi_{s,t,k}=\frac{g_{s,t,k}}{\sum_j g_{s,t,j}},
```

then allocate the reconciled state total:

```math
E_{s,t,k}=E_{s,t}\pi_{s,t,k}.
```

This guarantees:

```math
\sum_k E_{s,t,k}=E_{s,t}
```

for every draw before any additional national size reconciliation.

### 11.11 Source-specific measurement roles

| Evidence | Treatment |
|---|---|
| Disclosed final QCEW | Exact target observation for that final vintage |
| Preliminary QCEW | Separate as-of observation; do not mix with final hard controls |
| Suppressed QCEW | No pseudo-value; deterministic bounds plus model prediction |
| CBP employment | March-centered noisy structural measurement |
| CBP size counts | Annual state size-composition measurement with disclosure handling |
| QCEW national size | Compatible first-quarter benchmark |
| TPO/FIA | Measurements of latent harvest activity |
| CES | Monthly movement predictor or bridge, not identity |
| SUSB | Weak enterprise-structure prior only |
| BDS | Broader-industry transition/volatility prior |
| NES | Nonemployer predictor or separate universe only |
| BEA | Optional historical broad-concept bridge |

### 11.12 Starting priors

These are configurable modeling defaults, not facts:

- standardized regression coefficients: $\beta_j\sim N(0,0.5^2)$;
- state and region scales: half-normal or half-$`t_3`$;
- persistence: transformed Beta prior centered near 0.8;
- Student-t degrees of freedom: fixed near 5 for the first implementation or $4+\text{Exponential}(0.1)$;
- size-composition deviations: hierarchical normal with strong shrinkage;
- class-specific monthly effects: strong shrinkage toward zero;
- top-class tail: regularized using national QCEW size evidence.

Every prior must be exposed in resolved configuration and included in sensitivity runs.

### 11.13 Suppression sensitivity

The exact public selection model is not identified. The implementation MUST NOT claim otherwise.

Required sensitivity variants include:

- suppressed-cell process variance multipliers, such as 1.0, 1.5, and 2.0;
- heavier and lighter employment-intensity tails;
- alternative expected state shares;
- different state pooling strengths;
- primary-like versus complementary-like pseudo-suppression regimes;
- with and without forest proxies;
- with and without CES predictors; and
- alternative CBP disclosure/noise variance mappings.

### 11.14 Inference and diagnostics

The model interface MUST return joint draws and standard diagnostics. Promotion requires:

- no unresolved divergent transitions or equivalent backend failures;
- $\hat R$ at or below 1.01 for monitored parameters, unless a documented exception is approved;
- adequate effective sample size for all release-relevant summaries;
- stable posterior summaries across independent seeds/chains;
- posterior predictive checks on observed cells; and
- exact reconciliation checks after draw transformation.

The implementation SHOULD use noncentered parameterizations and vectorized state/time operations.

---

## 12. Exact reconciliation

### 12.1 General principle

The predictive model ranks feasible allocations. The reconciliation layer maps each draw into the deterministic feasible set. It is not optional post-hoc cosmetic adjustment.

### 12.2 Single national residual fast path

Let $D_t$ be disclosed states and $M_t$ states requiring imputation. For a compatible national total $N_t$:

```math
R_t=N_t-\sum_{s\in D_t}E^{obs}_{s,t}.
```

With positive raw weights $q_{s,t}$:

```math
E_{s,t}
=
R_t\frac{q_{s,t}}{\sum_{j\in M_t}q_{j,t}}.
```

This is the required no-bound fast path.

### 12.3 Bounded proportional scaling

When deterministic lower and upper bounds apply, solve:

```math
E_{s,t}=\operatorname{clip}(\lambda q_{s,t},L_{s,t},U_{s,t})
```

for $\lambda$ such that:

```math
\sum_{s\in M_t}E_{s,t}=R_t.
```

Because the summed clipped allocation is monotone in $\lambda$, use robust bisection. The function MUST fail if:

```math
\sum_s L_{s,t}>R_t
\quad\text{or}\quad
\sum_s U_{s,t}<R_t.
```

This algorithm is deterministic, fast, and exactly preserves the residual and cell bounds.

### 12.4 General feasible-polytope projection

When several overlapping margins apply, reconcile each raw draw $\tilde x^{(m)}$ by solving:

```math
x^{(m)}
=
\arg\min_{x\in\mathcal F}
\sum_i
\left[
 x_i\log\frac{x_i}{\tilde x_i^{(m)}}-x_i+\tilde x_i^{(m)}
\right],
```

with a small positive floor for zero raw seeds.

A weighted quadratic projection MAY be used when KL geometry is inappropriate, but the objective and weights must be versioned and validation-tested.

### 12.5 Size matrix reconciliation

For each state-month, row sums must equal reconciled state totals. Where compatible national class margins exist, column sums must equal those margins.

- Without bounds, use RAS/IPF or an equivalent entropy projection.
- With bounds or overlapping margins, use the general convex projection.
- If margins are inconsistent, fail and diagnose rather than forcing convergence.

### 12.6 Integerization

Continuous expected job draws are retained internally. For an integer release table:

1. floor each value;
2. compute remaining units for each required margin;
3. distribute units by largest fractional remainder or a controlled-rounding optimizer;
4. respect deterministic lower and upper integer bounds;
5. recheck every hard margin; and
6. store both continuous and integerized values.

Integerization MUST NOT be applied independently cell by cell.

### 12.7 Joint dependence

Posterior summaries must be computed from reconciled joint draws. Marginal intervals do not capture the negative dependence induced by national and class adding-up constraints; joint draws MUST remain available for downstream analysis.

---

## 13. Validation and model selection

### 13.1 Separate validation targets

The system has three validation problems:

1. **state totals:** directly pseudo-validated against disclosed QCEW state-month Logging cells;
2. **annual state size structure:** validated against published CBP state-year size information, subject to disclosure/noise treatment;
3. **monthly state-size employment:** validated indirectly through state-total accuracy, CBP March structure, national QCEW first-quarter size margins, coherence, and sensitivity.

The third target lacks direct public ground truth. Reports MUST state that limitation.

### 13.2 Pseudo-suppression generator

Random masking alone is prohibited as the only validation design.

For each selected fully observed public component:

1. choose a **primary-like** target using a configurable propensity based only on public predictors, such as establishment count, parent share, employment per establishment, historical volatility, and sparsity;
2. mask the target;
3. choose one or more **complementary-like** cells so the target is not trivially recovered by subtraction;
4. retain only the margins that would remain public under the synthetic pattern;
5. run rank and bound analysis on the masked component;
6. reject or separately label cases that remain exactly recoverable;
7. estimate all candidate methods; and
8. score primary-like and complementary-like cells separately.

The generator does not claim to reproduce BLS's confidential algorithm.

### 13.3 Required holdout regimes

- small-cell-biased masks;
- high employees-per-establishment or concentration-proxy masks;
- clustered states within a month;
- long consecutive missing runs;
- whole state-year blocks;
- regional blocks;
- whole seasonal blocks;
- rolling-origin forecasts using only past data;
- retrospective smoothing using past and future data;
- structural-break periods;
- NAICS transition windows;
- preliminary-to-final vintage comparisons; and
- missing CBP size classes or full state-year size rows.

### 13.4 Leakage controls

When a target cell is held out:

- no direct copy or derived feature may retain the held-out value;
- overlapping margins must reflect the intended synthetic suppression pattern;
- future periods are excluded from rolling-origin tests;
- final revisions are excluded from real-time tests; and
- feature normalization and hyperparameter selection are fit only on the training information set.

### 13.5 Deterministic-bound metrics

Report:

- feasible width $U_i-L_i$;
- truth-in-bound rate;
- exact-recovery rate;
- infeasible-component rate; and
- LP versus MILP tightening.

A known pseudo-hidden truth outside the deterministic bounds is a constraint-data bug until proven otherwise.

### 13.6 Point metrics

Report at minimum:

- MAE;
- RMSE;
- bias;
- WAPE;
- median absolute percentage error where denominators are safe;
- state-share absolute error;
- size-share absolute error; and
- top-size-class or rank accuracy where meaningful.

### 13.7 Probabilistic metrics

Report:

- empirical coverage at 50%, 80%, 90%, and 95%;
- average interval width;
- CRPS or log score;
- calibration by state size, region, gap duration, and suppression propensity; and
- calibration by distance from the nearest CBP anchor year.

### 13.8 Constraint metrics

For every method and draw set, report:

```math
\|Ax-y\|_1,
\qquad
\|Ax-y\|_\infty,
```

plus negative outputs, integerization violations, row-sum violations, and class-margin violations.

Reconciled production output requires zero hard-constraint violations within tolerance.

### 13.9 Sensitivity and ablation

Required ablations:

- no TPO/FIA;
- no CES;
- no temporal smoothing;
- Gaussian rather than Student-t innovations;
- alternative AR persistence priors;
- stronger and weaker state pooling;
- alternative CBP noise mappings;
- alternative top-class tail priors;
- alternative historical windows; and
- alternative suppression-selection scenarios.

For each release cell, compute a model sensitivity envelope:

```math
S_i=\max_m \hat E_i^{(m)}-\min_m \hat E_i^{(m)}.
```

### 13.10 Default promotion gates

These are initial configurable engineering gates, not findings from the source reports:

- all hard constraints pass;
- convergence diagnostics pass;
- 90% interval coverage is within 5 percentage points of nominal overall and does not fail catastrophically in any major stratum;
- the full model improves WAPE by at least 5% over the preferred transparent baseline on primary-like masks, or supplies a clearly superior calibrated uncertainty distribution;
- no major stratum degrades by more than 2% WAPE without documented substantive benefit; and
- disclosure review approves the release form.

If these gates are not met, deploy the simpler method.

---

## 14. Disclosure-risk governance

### 14.1 Separate decisions

The system MUST record three separate statuses:

```text
identification_status
estimation_status
release_status
```

A cell can be estimable but not releasable.

### 14.2 Automatic review triggers

A suppressed cell MUST be routed to review when any of the following holds:

- deterministic bounds collapse to a point;
- deterministic width is narrow in absolute or relative terms;
- a posterior interval is much narrower than the feasible interval because of strong priors;
- the cell has very few published establishments;
- public employer information could plausibly reveal a dominant establishment;
- the model is highly sensitive to prior or proxy choices; or
- a coarser output would answer the analytic question nearly as well.

### 14.3 Privacy-oriented concentration metric

Compute:

```math
R_i
=
1-
\frac{\text{model interval width}_i}
     {\text{deterministic feasible width}_i}.
```

A high value may represent predictive success and disclosure risk simultaneously. It is a review indicator, not an accuracy score.

### 14.4 Release policy

For high-risk cells, preferred remedies are:

1. release a broader interval with clear methodology;
2. combine size classes;
3. aggregate months to quarters or years;
4. aggregate states to regions;
5. use restricted analyst access; or
6. withhold the cell.

The system MUST NOT automatically publish an exactly reconstructed `N`-flagged value. It MUST NOT label any modeled output as an official BLS or Census value.

### 14.5 Required label

Every public modeled record or table must include substantially the following label:

> Modeled estimate derived from public data and explicit assumptions; not an official BLS, Census Bureau, or Forest Service published value.

---

## 15. Output products

### 15.1 Required release tables

1. `state_month_total.parquet`
2. `state_month_size.parquet`
3. `deterministic_bounds.parquet`
4. `posterior_summary.parquet`
5. `validation_metrics.parquet`
6. `disclosure_decisions.parquet`
7. `source_manifest.parquet`
8. `constraint_manifest.parquet`
9. `run_manifest.json`

### 15.2 Required fields in state-month-size output

```text
state_fips
state_name
reference_month
industry_code
industry_title
ownership_code
employment_concept
size_concept
size_class
size_lower
size_upper
estimate_continuous
estimate_integer
posterior_mean
posterior_median
ci50_low
ci50_high
ci80_low
ci80_high
ci90_low
ci90_high
ci95_low
ci95_high
deterministic_lower
deterministic_upper
observation_status
qcew_disclosure_code
model_dependence_level
model_sensitivity_low
model_sensitivity_high
reconciliation_status
release_status
source_vintage_set
model_version
run_id
```

### 15.3 Model-dependence levels

Suggested values:

```text
0_observed
1_exactly_implied_publicly
2_partially_identified_low_model_dependence
3_model_estimated_moderate
4_model_estimated_high
5_withheld
```

### 15.4 Posterior draws

Joint draws SHOULD be stored in an ArviZ-compatible format and MAY also be exported to partitioned Parquet. The storage must preserve draw, chain, state, month, and size indexes.

---

## 16. Command-line and programmatic interfaces

### 16.1 CLI

A suggested Typer interface is:

```text
logging-estimates validate-config --config config.yaml
logging-estimates registry verify --config config.yaml
logging-estimates fetch --source qcew --config config.yaml
logging-estimates fetch --source cbp --config config.yaml
logging-estimates build-harmonized --config config.yaml
logging-estimates build-constraints --config config.yaml
logging-estimates solve-bounds --config config.yaml
logging-estimates run-baselines --config config.yaml
logging-estimates fit-state-model --config config.yaml
logging-estimates fit-size-model --config config.yaml
logging-estimates reconcile --config config.yaml
logging-estimates validate --config config.yaml
logging-estimates disclosure-review --config config.yaml
logging-estimates publish --config config.yaml
logging-estimates run-all --config config.yaml
```

Every command MUST write a machine-readable manifest and MUST be idempotent for the same inputs.

### 16.2 Programmatic interfaces

```python
class ConstraintSystem(Protocol):
    cells: CellTable
    rows: ConstraintRowTable
    coefficients: SparseCoefficientTable


def build_constraint_system(data: HarmonizedData, config: Config) -> ConstraintSystem: ...

def solve_bounds(system: ConstraintSystem, config: BoundConfig) -> BoundResult: ...

def fit_state_total_model(data: ModelData, config: StateModelConfig) -> PosteriorDraws: ...

def fit_size_model(data: SizeModelData, config: SizeModelConfig) -> PosteriorDraws: ...

def reconcile_draws(
    raw_draws: PosteriorDraws,
    feasible_set: ConstraintSystem,
    config: ReconciliationConfig,
) -> PosteriorDraws: ...

def run_pseudo_suppression(
    data: HarmonizedData,
    estimators: Sequence[Estimator],
    config: ValidationConfig,
) -> ValidationResult: ...
```

PPL-specific objects must remain behind model interfaces.

---

## 17. Testing requirements

### 17.1 Unit tests

At minimum:

- parse suppression-coded QCEW zero as null;
- preserve a true published zero when its metadata supports that interpretation;
- expand quarterly monthly columns correctly;
- reject unknown CBP disclosure regimes;
- preserve source NAICS vintage;
- reject enterprise-size input as establishment-size measurement;
- apply March support only to the valid period;
- compute residual allocation exactly;
- solve bounded proportional scaling;
- balance integer rounding; and
- produce deterministic hashes for manifests.

### 17.2 Constraint property tests

Use generated toy tables to verify:

- parent equals children;
- one missing child is exactly recoverable;
- two missing children are only partially identified under nonnegativity;
- overlapping margins can identify a cell despite two suppressions per row;
- rounding intervals avoid false exact recovery;
- integrality can tighten bounds;
- mixed-vintage constraints create a detected conflict;
- graph components solve independently; and
- every reconciled draw lies within bounds and satisfies margins.

### 17.3 Reconciliation property tests

For random feasible inputs:

- no-bound scaling sums exactly to the residual;
- bounded scaling respects every lower and upper bound;
- bounded scaling fails on infeasible residuals;
- generalized projection never increases constraint violation;
- row and column reconciliation is exact;
- integerization preserves required totals; and
- ordering or solver tolerances do not create material instability.

### 17.4 Integration tests

- ingest one known QCEW quarter and produce normalized monthly rows;
- ingest one CBP state-year and enumerate size codes from metadata;
- build a constraint component and solve bounds;
- run every baseline on a small frozen fixture;
- fit a reduced Bayesian model on synthetic data;
- reconcile posterior draws;
- generate pseudo-suppression metrics; and
- publish a complete release package from frozen fixtures.

### 17.5 Statistical recovery tests

Create synthetic data with known:

- state effects;
- region effects;
- seasonality;
- AR persistence;
- heavy-tailed shocks;
- size compositions;
- top-class tails;
- correlated TPO/FIA measurements; and
- primary-like/complementary-like missingness.

Test parameter and predictive recovery within tolerances appropriate to sample size.

### 17.6 Golden tests

Maintain small audited fixtures for:

- source parsing;
- constraint matrices;
- LP/MILP bounds;
- baseline predictions;
- reconciliation; and
- release schemas.

Golden updates require a documented reason and reviewer approval.

---

## 18. Reproducibility, observability, and failure policy

### 18.1 Reproducibility

Every run manifest MUST include:

- resolved configuration;
- code commit;
- package lock hash;
- source snapshot hashes;
- source parser versions;
- source schema fingerprints;
- NAICS crosswalk version;
- constraint-set hash;
- model and prior version;
- random seeds;
- solver names and versions;
- numerical tolerances; and
- output hashes.

### 18.2 Monitoring

Track:

- source fetch failures;
- schema drift;
- new disclosure codes or regimes;
- missing expected dimensions;
- QCEW national/state compatibility failures;
- infeasible constraint components;
- percentage of exactly recoverable cells;
- deterministic bound widths;
- solver time and status;
- Bayesian convergence diagnostics;
- pseudo-suppression accuracy and coverage;
- reconciliation residuals; and
- disclosure-review backlog.

### 18.3 Fail closed

The pipeline MUST fail rather than guess when:

- the supplied source schema is unrecognized;
- a disclosure code is unknown;
- a requested simultaneous cross-tabulation is absent;
- source universes cannot be reconciled;
- a hard constraint system is infeasible;
- model diagnostics fail;
- reconciliation fails; or
- disclosure review is required but incomplete.

---

## 19. Phased implementation and acceptance criteria

### Phase 0: decision and source lock

**Deliverables**

- resolved estimand configuration;
- classification memo for `1113310` → `113310`;
- source registry;
- NAICS-vintage map;
- disclosure-regime registry; and
- chosen pilot period.

**Acceptance**

- no unresolved direct-source dimensionality assumptions;
- every required source has a verified or explicitly documented access route;
- core geography and ownership universe are fixed.

### Phase 1: QCEW and CBP vertical slice

**Deliverables**

- immutable QCEW and CBP ingestion;
- normalized QCEW monthly table;
- CBP size table;
- compatibility checks; and
- source manifests.

**Acceptance**

- suppressed zeroes handled correctly;
- one frozen year/quarter rebuilds byte-for-byte at the harmonized layer;
- CBP size codes are metadata-driven.

### Phase 2: deterministic engine and baselines

**Deliverables**

- target-cell index;
- sparse constraint database;
- connected components and rank diagnostics;
- LP/MILP bounds;
- all required baselines; and
- exact reconciliation.

**Acceptance**

- toy and fixture constraints pass;
- every baseline produces coherent outputs;
- infeasibility diagnostics are actionable;
- exact/narrow cells are flagged for disclosure review.

This phase is the minimum useful product and must exist before the full Bayesian model.

### Phase 3: state-total Bayesian model

**Deliverables**

- robust hierarchical state-intensity model;
- posterior draws for suppressed totals;
- bounded reconciliation; and
- state-total pseudo-suppression report.

**Acceptance**

- diagnostics pass;
- constraints pass on every draw;
- required baselines are beaten or the simpler model is retained.

### Phase 4: size-composition model

**Deliverables**

- annual logistic-normal state size structure;
- CBP measurement model;
- national QCEW size benchmark integration;
- March class support model;
- monthly within-class intensity model; and
- state-month-size draws.

**Acceptance**

- state rows sum exactly to state totals;
- compatible national first-quarter class margins reconcile;
- CBP holdout validation is reported;
- monthly state-size limitations are explicit.

### Phase 5: forest factor, sensitivity, and governance

**Deliverables**

- TPO/FIA latent harvest factor;
- optional CES predictors;
- full ablation suite;
- disclosure workflow; and
- production release package.

**Acceptance**

- proxies demonstrate incremental value or are excluded;
- sensitivity envelope is produced;
- release actions are complete for all flagged cells;
- clean-room rebuild succeeds.

### Phase 6: optional extensions

Possible extensions include:

- real-time as-of vintages;
- contemporaneous modeled size classes;
- state-specific administrative feeds;
- weather, fire, and road-access features;
- county-level estimates with explicit MWR/location limitations;
- probabilistic revision modeling; and
- restricted-access analytic products.

Each extension requires its own validation and disclosure review.

---

## 20. Requirement traceability checklist

A coding plan MUST map at least the following IDs.

| ID | Requirement |
|---|---|
| `REQ-001` | Record supplied and corrected industry codes. |
| `REQ-002` | Use private QCEW-covered jobs as the core target. |
| `REQ-003` | Default to March-reference establishment size. |
| `REQ-004` | Freeze source vintages and checksums. |
| `REQ-005` | Parse QCEW disclosure before numeric values. |
| `REQ-006` | Dynamically discover CBP dimensions and disclosure regime. |
| `REQ-007` | Preserve SUSB enterprise-size semantics. |
| `REQ-008` | Build explicit compatibility bridges. |
| `REQ-009` | Build sparse public accounting constraints. |
| `REQ-010` | Compute rank, nullity, and connected components. |
| `REQ-011` | Compute LP/MILP sharp bounds. |
| `REQ-012` | Keep feasible and posterior intervals separate. |
| `REQ-013` | Implement all transparent baselines. |
| `REQ-014` | Implement robust hierarchical state-total model. |
| `REQ-015` | Implement latent TPO/FIA harvest factor. |
| `REQ-016` | Implement logistic-normal annual size composition. |
| `REQ-017` | Apply class support only at valid reference periods. |
| `REQ-018` | Reconcile every draw to all hard constraints. |
| `REQ-019` | Retain joint posterior draws. |
| `REQ-020` | Implement balanced integerization. |
| `REQ-021` | Implement realistic pseudo-suppression. |
| `REQ-022` | Separate rolling forecasts and retrospective smoothing. |
| `REQ-023` | Report point, probabilistic, and constraint metrics. |
| `REQ-024` | Require complexity to outperform baselines. |
| `REQ-025` | Run required sensitivity and ablation variants. |
| `REQ-026` | Implement disclosure-risk flags and release actions. |
| `REQ-027` | Never auto-release exact reconstructions. |
| `REQ-028` | Produce full provenance and run manifests. |
| `REQ-029` | Fail closed on schema, compatibility, solver, model, or governance errors. |
| `REQ-030` | Rebuild a release from a clean environment. |

---

## 21. Decisions that remain open

The implementation may start with the defaults below, but the owner should confirm them.

| Decision | Recommended default | Why it remains open |
|---|---|---|
| Historical period | Pilot on 2017–2024, then expand | The source reports were not given a required time span; older periods add NAICS and disclosure-regime complexity. |
| Geography universe | 50 states + D.C. | National QCEW compatibility must be tested; territories/residual areas may need explicit cells. |
| Release mode | `retrospective_final` first | Real-time mode requires archived as-of vintages and a separate validation design. |
| Size concept | `march_reference` | Contemporaneous size requires unobserved class-transition modeling. |
| PPL backend | NumPyro/JAX | CmdStanPy is viable; benchmark compilation, diagnostics, and constrained transforms before final selection. |
| General reconciliation solver | Entropy projection with a production convex solver | Solver choice should be based on reliability, licensing, and performance tests. |
| TPO/FIA coverage | Required only after extraction audit | Nationwide annual completeness and vintage semantics must be tested. |
| Optional state sources | Disabled by default | No standardized nationwide feed was verified. |
| Disclosure thresholds | Configured by governance owner | Exact numerical release thresholds are policy choices, not supplied evidence. |
| Promotion thresholds | Defaults in Section 13.10 | They are engineering defaults and should be approved or adjusted. |

---

## Appendix A. Example configuration

```yaml
project:
  name: 'logging-state-employment'
  industry_code_supplied: '1113310'
  industry_code_used: '113310'
  industry_title: 'Logging'
  ownership: 'private'
  geography_universe: 'states_dc'
  start_month: '2017-01'
  end_month: '2024-12'
  analysis_mode: 'retrospective_final'
  size_concept: 'march_reference'

storage:
  raw_uri: 'data/raw'
  staged_uri: 'data/staged'
  output_uri: 'runs'
  immutable_raw: true

sources:
  qcew:
    enabled: true
    release_status: 'final'
  qcew_size:
    enabled: true
  cbp:
    enabled: true
    api_key_env: 'CENSUS_API_KEY'
    fail_on_unknown_disclosure_regime: true
  tpo:
    enabled: false
  fia:
    enabled: false
  ces:
    enabled: false
  susb:
    enabled: false
  bds:
    enabled: false
  nonemployer:
    enabled: false
  bea:
    enabled: false

constraints:
  enforce_integrality: true
  use_milp_when_lp_interval_width_below: 25
  solver: 'highs'
  feasibility_tolerance: 1.0e-7
  rank_tolerance: 1.0e-10

model:
  backend: 'numpyro'
  chains: 4
  warmup: 1000
  draws: 1000
  target_accept: 0.9
  state_dynamic: 'student_t_ar1'
  include_change_points: false
  include_harvest_factor: false
  include_ces: false
  standardized_beta_sd: 0.5
  suppressed_variance_multipliers: [1.0, 1.5, 2.0]

reconciliation:
  single_margin_method: 'bounded_proportional_scaling'
  general_method: 'kl_projection'
  integerize_release: true

validation:
  pseudo_suppression_seeds: [1024, 2048, 4096]
  include_random_mask_sanity_check: true
  include_primary_like: true
  include_complementary_like: true
  include_long_runs: true
  include_rolling_origin: true
  include_retrospective_smoothing: true
  include_vintage_comparison: true

promotion:
  minimum_wape_improvement: 0.05
  maximum_major_stratum_wape_degradation: 0.02
  nominal_coverage_tolerance: 0.05

disclosure:
  exact_reconstruction_action: 'withhold'
  narrow_interval_action: 'manual_review'
  publish_label_required: true
```

---

## Appendix B. Minimum end-to-end acceptance scenario

A coding agent must demonstrate one frozen vertical slice that:

1. downloads or loads a frozen QCEW quarter for 113310;
2. parses state and national private rows and disclosure codes;
3. expands the quarter to three monthly rows;
4. loads one CBP year and enumerates official establishment-size codes;
5. creates target cells for one month;
6. builds a national state-sum constraint plus observed-cell constraints;
7. computes LP bounds for suppressed states;
8. runs equal, establishment-count, historical-share, and CBP-intensity baselines;
9. reconciles each baseline exactly;
10. fits a reduced robust state-total model;
11. reconciles every posterior draw;
12. performs at least one primary-like/complementary-like pseudo-suppression test;
13. reports accuracy, coverage, and constraint metrics;
14. generates disclosure flags; and
15. emits a complete reproducible run manifest and release package.

The vertical slice is not complete if it produces only point estimates, omits deterministic bounds, or reconciles only posterior means.

---

## Appendix C. Evidence map to the supplied documents

This specification is a synthesis, not an independent source-verification report. The principal source locations used were:

- `logging-prompt(1).md`, especially the target and compatibility requirements (lines 6–59), identification requirements (lines 164–205), Bayesian and reconciliation requirements (lines 255–419), validation and disclosure requirements (lines 439–487), and research standards (lines 531–585).
- `suppressed-cell-estimation.md`, especially the identification-first conclusion and hybrid workflow (lines 5–25), rank and LP/MILP framework (lines 27–154), recommended four-layer architecture (lines 325–397), validation design (lines 400–523), and disclosure boundaries (lines 747–779).
- `logging-research-chatgpt.md.md`, especially the verified target and source-dimensionality findings (lines 3–27), deterministic strategy (lines 133–226), model and reconciliation design (lines 228–499), validation and disclosure design (lines 501–575), and production requirements (lines 576–680).
- `logging-research-copilot.md.md`, especially the core estimand and CBP finding (lines 7–17), deterministic bounds (lines 198–211), robust model and reconciliation (lines 213–287), and validation pipeline (lines 289–318).
- `logging-research-gemini.md.md`, especially the decomposition and source roles (lines 3–15 and 120–163), model components (lines 164–233), and staged pipeline (lines 244–283). Claims about exact current suppression thresholds and universally available size constraints were not adopted.

---

## Rollout

Roadmap: `specs/logging-employment-spec-roadmap.md` — every stage implements
this spec. Stage stamps below are authoritative (derive-roadmap §5).

### Decisions resolved at roadmap derivation (2026-09-03, review-informed)

This supersedes the decision block written during the earlier derivation, which
was made before the three research reviews were in the repository. These rows
resolve §21 entries. Every stage plan copies the ones it needs into its Global
Constraints verbatim.

- **D1 Historical period:** pilot `2017-01` → `2024-12` as in Appendix A. Every quarter in the window is final under QCEW's finalize-with-next-year-Q1 rule. Confirmed against the reviews: the window spans the 2017→2022 QCEW NAICS transition, which Stage 1's crosswalk test must exercise.
- **D2 Scope ceiling:** Phases 0–5 are in scope. Phase 6 is an optional, separately routed stage. All three reviews stage the work in this order, so the ceiling stands.
- **D3 Source access:** live fetch from `data.bls.gov` and `api.census.gov`. Credentials come from an untracked repo-root `.env` (keys present: `CENSUS_API_KEY`, `BLS_API_KEY`, `BEA_API_KEY`, `FRED_API_KEY`, `BLS_CONTACT_EMAIL`) loaded with python-dotenv. `.env` MUST be gitignored before the first commit that adds code, and no key value may appear in any manifest (§7.2). Note that `bls.gov` admits scripted clients only when the User-Agent carries a contact address; `BLS_CONTACT_EMAIL` exists for that purpose.
- **D4 Toolchain:** a single installable package — `src/logging_employment/` laid out per §6.1 — built with hatchling and managed by uv; `requires-python >= 3.14`; author `Lowell Mason <mason.lowell@mac.com>`, MIT license; ruff and black at line length 100, pytest markers `network` and `slow`, interrogate at 100%, python-dotenv in the `dev` dependency group. Tooling is modeled on the owner's `alt-nfp` `pyproject.toml` (supplied 2026-09-03) but NOT its workspace layout. Stage 1's plan verifies that jax/jaxlib, numpyro, highspy, polars, and pyarrow publish 3.14 wheels before locking and records any that do not as an open decision.
- **D5 QCEW acquisition is dual-route.** The §5.4 seed endpoint serves only the most recent five reference years, so it cannot cover all of D1's window. Stage 1 implements both the Open Data CSV slice route and the downloadable bulk-file route behind one ingest interface, selecting by reference year from the boundary Stage 0 measures. §5.4's instruction not to hard-code a "latest" year applies to both routes.
- **D6 BEA is out of scope; CES is industry-aligned where published at 1133.** BEA `SAEMP25`/`SAEMP27` were discontinued 2024-09-27, leaving no current detailed state-industry table to bridge, so SRC-OTH-005 is deferred with that reason rather than staged. CES stays in scope: NAICS `1133 → 11331 → 113310` verified against the official structure files for both the 2017 and 2022 vintages, so 113310 is the only six-digit industry under 1133 and a state CES series published at 1133 covers exactly the target industry. §5.2's "never an exact QCEW identity" continues to bind on the statistical concept — CES is an annually QCEW-benchmarked sample estimate, published in thousands and revised — not on industry mismatch. A series published only at 113 or at the Mining-and-Logging supersector is genuinely broader and keeps its proxy-only treatment.

Other §21 rows keep their Appendix A defaults until a stage's plan or finding changes them.

### Stage stamps

- Roadmap: specs/logging-employment-spec-roadmap.md, Stage 0 — on plan completion, tick the stage and re-validate later stages against what shipped.
> Stage 0: COMPLETE (2026-09-04) — implemented by plan 1 (specs/plans/completed/1-stage0-logging-employment-spec.md).
> Next: resume the roadmap.
>
> **Later stages re-validated against what Stage 0 actually measured:**
> - **Stage 1 (parser contracts, QCEW year boundary).** The slice route serves from reference
>   year **2014**, measured — not the "most recent five years" D5 assumed, so the dual-route
>   selection boundary is empirical and stated as a reference year, not an approximation.
>   Stage 1 must read `published_start`/`published_end` only with the semantics note beside
>   `COVERAGE_KEYS` in `scripts/audit/_common.py`: the key means measured publication bounds in
>   some summaries and the window restated in others.
> - **Stage 2 (available margins).** `SRC-QCEW-006` is **`decline`** — the national/state
>   employment identity is untestable, because every one of the 96 testable months carries at
>   least one suppressed states+DC cell. Establishment counts close exactly in 32 of 32
>   quarters. Stage 2 gets the establishment margin, not the employment identity.
> - **Stage 3 (allocation anchor) — ACTION REQUIRED.** Because the branch is `decline`, Stage 3
>   must name a substitute anchor or accept a weaker assumption **before any baseline is
>   written**. The decline is for unverifiability, not geography.
> - **Stage 4 (mask design).** Measured suppression share **0.2602** over 4716 states+DC
>   monthly cells, in 54 runs of which four span the full 96 months. A mask design assuming
>   short independent gaps does not match this; four areas are suppressed throughout.
> - **Stage 6 (routing) — NO re-route needed.** `simultaneous_state_industry_size` came back
>   **`false`**, so the roadmap's condition for re-routing Stage 6 to brainstorming is not met.
>   SUSB's `detailed_sizes_reaches_six_digit_at_state` is also `false`, and BDS cannot resolve
>   logging at all (`finest_naics_available: "11"`).
> - **Stages 2, 3 and 6 `Consumes` blocks — CBP coverage gap.** CBP publishes **2017-2023**;
>   **2024 is not available** (probe returned 404, vintage not yet published). Any Consumes
>   block assuming CBP covers the full D1 window is wrong by one year.


- Roadmap: specs/logging-employment-spec-roadmap.md, Stage 1 — on plan completion, tick the stage and re-validate later stages against what shipped.
> Stage 1: COMPLETE (2026-09-05) — implemented by plan 2 (specs/plans/completed/2-stage1-logging-employment-spec.md).
> Next: resume the roadmap.
>
> **§19 Phase 1 acceptance, verified over the real D1 window on 2026-09-05.** A frozen pull
> rebuilds byte-identical harmonized Parquet offline: two consecutive `build-harmonized` runs
> produce the same four hashes, and so does a run with the socket layer patched to raise. The
> harmonized layer is `qcew_monthly` (4,812 rows, 96 months, 2017-01 → 2024-12),
> `qcew_national_size` (140,343), `cbp_state_size` (1,298) and `bridge` (2), from 47 snapshots.
>
> **Later stages re-validated against what Stage 1 actually shipped:**
> - **Stage 2 (what the harmonized layer hands you).** `qcew_monthly` is already
>   universe-filtered — private ownership, states+DC and the national row only — so Stage 2 does
>   *not* re-apply REQ-002, and a Puerto Rico or county row appearing downstream is a bug, not
>   data. `harmonize.universe.state_universe_report` supplies the per-month facts: measured on
>   the window, the 4,812 rows are 4,716 states+DC cells plus 96 national ones; of the
>   states+DC cells 1,227 are `suppressed`, 27 `true_zero` and 3,462 `observed`.
>   **1,227 / 4,716 = 0.2602** reproduces Stage 0's independently measured suppression
>   share exactly, over the same denominator. Every suppressed cell is a state cell.
>   `assert_definitional_alignment` (SRC-QCEW-007) must be called before any constraint is
>   created; it is not called from the build path, by design, because it guards constraint
>   construction rather than ingestion.
> - **Stage 3 (allocation anchor) — ACTION STILL REQUIRED.** Unchanged by Stage 1. The
>   `SRC-QCEW-006` `decline` stands; Stage 1 shipped the in-code universe report, not a
>   substitute anchor.
> - **Stage 4 (mask design).** `qcew_monthly.suppression_type` exists and is `unknown` on every
>   real row, with `contracts.SUPPRESSION_TYPES = ("unknown", "primary_like",
>   "complementary_like")`. INV-009 binds: Stage 4 writes the labelled values only onto synthetic
>   masks it created, never onto an ingested row.
> - **Stage 6 (CBP measurement model) — two things to know.** First, **CBP suppression is real in
>   this window.** Reference year 2017 carries the EMPFLAG regime
>   (`noise_infusion_plus_suppression`), and four of its 188 rows are withheld. In the
>   harmonized table they carry `disclosure_status = 'suppressed'`, `employment` **null**,
>   `establishments` 3 and `employment_flag` `'a'` -- Delaware and North Dakota, size classes
>   `001` and `210`. The published `EMP = 0` those rows carried survives only in the raw
>   store: INV-003 is exactly why the harmonized value is null rather than a zero, so do not
>   look for zeros here. 2018–2023 are plain `noise_infusion` with no withheld row. Second,
>   **the noise magnitude is not in the harmonized table.** `employment_noise_range` carries
>   `EMP_N`, which is the literal `'0'` on every row of every year; the real per-cell flag is
>   `EMP_N_F` (measured `G: 103, H: 51, J: 34` on 2023), which §7.5 has no column for. `fetch`
>   selects it, so it is in the raw store — closing the gap means amending §7.5 and
>   re-fingerprinting `CBP_STATE_SIZE_SCHEMA`. Recorded in `specs/deferred_items.md`.
> - **Every stage that rebuilds from the raw store.** CBP responses are **not byte-reproducible**
>   — successive fetches return set-identical rows in a different order, so each fetch stores a
>   new content-addressed object. `build_harmonized` therefore selects one snapshot per reference
>   key via `runs/source_manifest.parquet` and raises `AmbiguousSnapshotError` when nothing
>   disambiguates. Build through the manifest, not by globbing `data/raw/`. QCEW is unaffected.
> - **CBP coverage gap confirmed live.** Stage 0's probe result held: the 2024 vintage returns a
>   non-200, the window pull produced 7 CBP snapshots rather than 8, and `regime_for_year(2024)`
>   raises. Any `Consumes` block assuming CBP covers the full D1 window is still wrong by one year.

- Roadmap: specs/logging-employment-spec-roadmap.md, Stage 2 — on plan completion, tick the stage and re-validate later stages against what shipped.
> Stage 2: COMPLETE (2026-09-05) — implemented by plan 3 (specs/plans/completed/3-stage2-logging-employment-spec.md).
> Next: resume the roadmap.
>
> **What the engine measured, for stages that consume it:**
> - **Every one of the 1,227 suppressed state-month employment cells is `unbounded`.** Measured,
>   not predicted: `selected_lower` is 0 and `selected_upper` is **null**. `SRC-QCEW-006`'s
>   `decline` leaves nonnegativity as the only public fact touching a state cell.
> - **The identifying content is 14 cells.** The suppressed national size classes come back
>   `partially_identified` at widths of 130–894 employees. No cell anywhere is
>   `exactly_recoverable`, and `exact_reconstruction_flag` fires nowhere on real data.
> - **`narrow_feasible_interval_flag` fired once on the 2026-09-05 run**, on 2023 class 6 (width
>   184, relative width 0.232 against the 0.25 threshold). Read that as a measurement with a date,
>   not an invariant: 2018 class 5 sits at **0.2589** and 2024 class 6 at **0.2796**, so a single
>   BLS revision moves either under the threshold and the count becomes two or three.
> - **The state panel is not rectangular.** 4,716 state cells, not 50 x 96 = 4,800: 84 state-months
>   publish no row at all, and Stage 1 records absence as a missing row rather than an `absent`
>   cell, so those months get no cell and no bound. Separately, "states+DC" is a universe name
>   inherited from Stage 0, not a description of the data -- `qcew_monthly` carries 50 distinct
>   `state_fips` and DC (`11`) publishes no row anywhere in the window. Any Stage 3 code that
>   indexes a complete state x month grid will not find one.
>
> **Later stages re-validated against what Stage 2 actually shipped:**
> - **Stage 3 (reconciliation) — a null upper bound is the normal case, not an edge case.** Any
>   reconciliation that clips a draw into `[selected_lower, selected_upper]` meets a null upper on
>   1,227 of the 1,241 unknown cells. Code that assumes two finite endpoints will fail or, worse,
>   coerce null to a number and invent the cap §9.3 forbids. The substitute anchor Stage 3 must
>   name is now confirmed by measurement rather than inferred from Stage 0's verdict.
> - **Stage 3 (CBP as `empirical_measurement`).** The INV-005 `is_hard` filter in
>   `constraints/bounds.py` is exercised today only by tests, because every row this stage builds
>   is hard. Stage 3 is where a soft row first reaches the model and where that filter starts
>   doing visible work; `column_specs` and `matrix_rows` both apply it and must stay in agreement.
> - **Stage 5 (INV-008).** `deterministic_bounds` carries no posterior column and its
>   `selected_*` values are solver output only. The other half of "kept separate" needs a
>   posterior to be separate from, so it remains untestable until Stage 5 exists.
> - **Stage 6 (model constraints reuse these builders).** `rows.size_support_rows` refuses a
>   non-March size row (INV-011) *and* a frame carrying more than one industry. The second refusal
>   is not in the plan: the builder matches a size row to a cell on `(reference_month,
>   size_class)` and never on industry, so an unfiltered `qcew_national_size` silently produced
>   3,857 support rows carrying 14 distinct `constraint_id`s.
> - **Stage 6 / any stage reading INV-007.** Neither vintage check is a general INV-007 guarantee.
>   `cells._assert_one_vintage_per_cell` catches one area-month published under two *release*
>   vintages; `rows.vintage_status` catches a row spanning two *NAICS* vintages. Neither sees a
>   hard row spanning two different area-months whose release vintages differ — which on this
>   window is correct, since `qcew_monthly` carries 32 release vintages, one per reference quarter.
