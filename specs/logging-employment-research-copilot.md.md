# Estimating Monthly State Employment in U.S. Logging, Total and by Establishment Size Class

**Research date:** 2026-09-03  
**Target industry:** NAICS 113310, Logging  
**Recommended target concept:** private-sector, QCEW-covered jobs at establishments, measured monthly, with establishment size defined by March employment

## Executive summary

The supplied code `1113310` is not a valid six-digit NAICS code. The intended code is almost certainly **113310, Logging**, but this correction must be recorded as a classification decision rather than made silently. The official 2022 NAICS definition covers establishments primarily cutting timber, cutting and transporting timber, or producing wood chips in the field. The code and scope are unchanged across the 2007, 2012, 2017, and 2022 NAICS vintages, so no within-NAICS content crosswalk is needed over those vintages. Pre-NAICS history requires a bridge to SIC 2411 and should not be pooled without explicit treatment. citeturn1search52turn1search53

The best estimand is **monthly private QCEW-covered wage-and-salary jobs at logging establishments**, not persons employed and not employment including proprietors. QCEW is the anchor because it publishes establishment counts and three monthly employment observations per quarter for state-by-six-digit-industry cells when disclosure permits. It covers workers reported under state unemployment-insurance laws and federal workers under UCFE, and overall covers more than 95 percent of U.S. jobs. Logging should normally be extracted as private ownership because the complementary Census employer datasets are private-sector products. citeturn1search7turn1search63

No public source appears to publish the complete target cross-tabulation of **state × month × six-digit logging × establishment-size class**. QCEW size files are first-quarter products whose size class is determined by March employment; they provide six-digit industry detail nationally but only NAICS-sector detail at state level. Consequently, national six-digit logging size distributions are direct structural measurements, while state logging size composition is latent and must be estimated. citeturn1search44turn1search5

A crucial finding is that **CBP does expose state × six-digit NAICS × establishment employment-size simultaneously** through the 2023 API/table structure, with March 12-week employment, establishments, payroll, disclosure flags, and employment noise ranges. This is the strongest annual state-specific size-structure measurement, but it is a March snapshot in a Census employer universe and must not be treated as monthly QCEW truth. All Census Data API calls now require a key. citeturn1search8turn1search10turn1search64

The recommended production method has two stages. First, construct deterministic feasible intervals from disclosed QCEW values, compatible parent margins, establishment counts, and size-class support. Second, fit a hierarchical dynamic Bayesian model for employment per establishment, annual-to-monthly size composition, and class-specific employment intensity. Preserve every disclosed QCEW value exactly and allocate only the compatible national residual across suppressed states using normalized positive weights. Posterior draws should be reconciled in every draw, not merely on average.

## 1. Verified NAICS code, target population, and statistical unit

### 1.1 Classification decision

- **Supplied value:** `1113310`.
- **Status:** invalid as a standard six-digit NAICS code.
- **Corrected value:** `113310`.
- **Official title:** **Logging**.
- **Official scope:** cutting timber; cutting and transporting timber; and producing wood chips in the field. Trucking timber without cutting belongs in 484220, while wood chips produced in sawmills belong in 321113. citeturn1search52turn1search53
- **Decision log:** retain both `industry_code_supplied="1113310"` and `industry_code_used="113310"`, plus `correction_reason="invalid seven-digit code; intended six-digit Logging code verified"`.

The published code remains 113310 in the 2007, 2012, 2017, and 2022 NAICS structures. Thus, for a study beginning in 2007 or later, vintage changes need metadata controls but not a content bridge for this industry. For earlier data, QCEW’s reconstructed NAICS series for 1990–2000 was converted from SIC and should be flagged as reconstructed; QCEW also supplies SIC-based files through 2000. citeturn1search2turn1search53

### 1.2 Recommended estimand

Let

\[
E_{s,t,k}=\text{QCEW-covered jobs in state }s\text{, month }t\text{, at logging establishments in size class }k.
\]

Define the total as \(E_{s,t}=\sum_k E_{s,t,k}\). This is a **job count** on employer payrolls during the QCEW reference period, not a count of unique individuals. A person holding two covered jobs can contribute twice. The statistical unit for industry and size assignment is the **establishment/worksite**, not the firm or enterprise. QCEW confirms that multi-establishment firms are tabulated establishment by establishment and that March employment determines first-quarter size class. citeturn1search44turn1search63

Use private ownership as the production default. If total ownership is required, model ownership layers separately because Census CBP/SUSB do not provide a directly interchangeable government-employer universe.

### 1.3 Size classes

Use the QCEW classes: fewer than 5; 5–9; 10–19; 20–49; 50–99; 100–249; 250–499; 500–999; and 1,000 or more employees per establishment. These are establishment-size classes, not firm-size classes. citeturn1search45turn1search44

## 2. Direct-source findings

### 2.1 BLS Quarterly Census of Employment and Wages

**Role:** primary monthly state-total observation and accounting anchor.

QCEW quarterly CSV records contain quarterly establishments, three separate monthly employment fields, quarterly wages, ownership, geography, industry, aggregation level, size code, and disclosure code. `disclosure_code="N"` means the value is not disclosed. Therefore, a numeric zero in a suppressed record must not be interpreted as a true zero. citeturn1search63turn1search62

**Access:**

- Open-data pattern: `https://data.bls.gov/cew/data/api/{year}/{quarter}/industry/{industry}.csv`
- Verified documented example: `https://data.bls.gov/cew/data/api/2024/1/industry/10.csv`
- Logging adaptation: `https://data.bls.gov/cew/data/api/2024/1/industry/113310.csv`
- Historical downloads: `https://www.bls.gov/cew/downloadable-data-files.htm`
- Quarterly layout: `https://www.bls.gov/cew/about-data/downloadable-file-layouts/quarterly/naics-based-quarterly-layout.htm`

The open-data service covers the most recent five years; zipped downloadable files provide the longer history. BLS updates current and prior-year records, so a production system must archive release vintage and distinguish preliminary from final data. citeturn1search2turn1search3turn1search56

**Size limitation:** QCEW first-quarter size products are available at six-digit NAICS nationally and at NAICS-sector level by state. They do not directly supply state × 113310 × size class. This is a verified dimensionality limitation, not an inference from missing search results. citeturn1search44

### 2.2 Census County Business Patterns

**Role:** strongest annual/March state-specific logging size measurement.

CBP is annual and reports establishments, employment during the week of March 12, first-quarter payroll, and annual payroll for employer establishments. Its API dimensions include geography, two- through six-digit NAICS, legal form, and establishment employment-size class. Variables include `EMP`, `ESTAB`, `EMPSZES`, `EMP_F`, and `EMP_N`, making suppression/noise information available for measurement modeling. citeturn1search8turn1search10turn1search65

**Example request, Alabama, 2023, Logging:**

```bash
curl 'https://api.census.gov/data/2023/cbp?get=NAME,NAICS2017_LABEL,EMPSZES,EMPSZES_LABEL,ESTAB,EMP,EMP_F,EMP_N&for=state:01&NAICS2017=113310&LFO=001&key=YOUR_KEY'
```

The API requires a Census key. `LFO=001` is the all-legal-forms setting used in the official examples; retrieve all returned `EMPSZES` rows rather than inventing class codes. The downloadable 2023 State File is an alternative when reproducibility or bulk throughput matters. citeturn1search64turn1search67

**Compatibility judgment:** treat CBP size-class establishment counts and employment as an annual, noisy March-centered observation on latent state size structure. Do not substitute CBP employment for QCEW monthly employment without an explicit bridge for universe, processing, and disclosure differences.

### 2.3 Census Statistics of U.S. Businesses

**Role:** annual structural prior, especially enterprise-size context and national/state six-digit totals.

SUSB provides employer-establishment data by establishment industry and **enterprise size**, including firms, establishments, March 12-week employment, and annual payroll. The 2022 directory includes `us_state_6digitnaics_2022` and `us_state_naics_detailedsizes_2022`; the latter is not evidence of state × six-digit × detailed size until its layout is inspected. The published description emphasizes enterprise employment size, so it cannot be relabeled establishment size. citeturn1search15turn1search18turn1search19

**Access:** `https://www2.census.gov/programs-surveys/susb/tables/2022/` and `https://www.census.gov/programs-surveys/susb/data/tables.html`. No public SUSB API was verified in this research; use official spreadsheets/text files and archive hashes.

### 2.4 Census Business Dynamics Statistics

**Role:** annual prior for births, deaths, expansions, contractions, and transition volatility.

BDS provides annual measures of establishment openings/closings, firm startups/shutdowns, and job creation/destruction. Public data reach 3- and 4-digit NAICS, not six-digit Logging, so BDS is a broader-industry dynamic proxy rather than a direct measurement. citeturn1search75turn1search77

**Access:** `https://api.census.gov/data/timeseries/bds` and `https://bds.explorer.ces.census.gov/`.

### 2.5 BLS Current Employment Statistics

**Role:** monthly seasonality and turning-point proxy only.

CES is a monthly establishment survey of nonfarm payroll employment. The state program publishes a Logging aggregate mapped to NAICS 1133, but only four state series are published, and CES industry codes need not map one-to-one to NAICS due to sample-size limitations. Therefore CES cannot fill the national state panel at NAICS 113310, but available state series can validate monthly movement. citeturn1search32turn1search34turn1search36

### 2.6 Census Nonemployer Statistics

**Role:** proprietor/nonemployer sensitivity layer, not part of the core QCEW job estimand.

NES reports annual counts and receipts for businesses with no paid employees, at detailed industries and subnational geographies. It contains no employee measure. The 2022 release introduced methodological changes affecting historical comparability. citeturn1search38turn1search39

**Example:**

```bash
curl 'https://api.census.gov/data/2023/nonemp?get=NAME,NESTAB,NRCPTOT&for=state:01&NAICS2022=113310&key=YOUR_KEY'
```

### 2.7 BEA regional accounts

**Role:** broader forestry-and-logging regularizer and proprietor bridge.

BEA’s Regional dataset can provide state employment, wage-and-salary employment, proprietors’ employment, compensation, earnings, and GDP at available industry detail. The API supports JSON or XML and requires a registered 36-character key. Because BEA’s industry aggregation may be broader than NAICS 113310, these series are indirect constraints, not replacements for QCEW logging employment. citeturn1search26turn1search27turn1search30

**Endpoint:** `https://apps.bea.gov/api/data`. Discover current Regional tables and line codes through `GetParameterValuesFiltered` before production; do not hard-code an unverified line code.

### 2.8 USDA Forest Service TPO/NRUM and FIA

**Role:** harvest-activity measurement model.

NRUM/TPO collects annual mill-survey information on roundwood volume, product, species, and geographic origin, plus mill residue; estimates are aggregated to county and state. Geographic origin is more relevant to logging labor than mill location because interstate wood movements can otherwise misallocate activity. TPO also reports logging residue and active primary mills. citeturn1search20turn1search21

FIA EVALIDator/FIADB-API produces population estimates and sampling errors, including annual harvest-removals measures. Its `/fullreport` endpoint requires evaluation (`wc`), attribute (`snum`), and grouping parameters; evaluation vintages must not be mixed casually. citeturn1search69turn1search70turn1search72

**Access:** `https://apps.fs.usda.gov/fiadb-api/`, `https://apps.fs.usda.gov/fiadb-api/evalidator`, and `https://research.fs.usda.gov/products/dataandtools/timber-products-output-tpo-interactive-reporting-tool`.

### 2.9 State administrative and land-management sources

State UI/QCEW tools may reproduce federal QCEW with different interfaces and can help diagnose recodes, but they do not override federal disclosure restrictions. Timber severance taxes, harvest permits, road restrictions, wildfire closures, and state/federal timber sales can add monthly timing information. Forest Service cut-and-sold reports provide quarterly/annual National Forest System volumes and values, but cover only federal lands and are therefore partial-coverage proxies. citeturn1search25turn1search47

## 3. Source-compatibility matrix

| Source | Time | Geography × industry | Unit / size | Employment concept | Disclosure | Use |
|---|---|---|---|---|---|---|
| QCEW quarterly | Monthly employment, quarterly establishments | State × 6-digit | Establishment; no state-6-digit size detail | UI/UCFE-covered jobs | Suppression code N | Direct totals and constraints |
| QCEW size | Q1, March-determined class | U.S. × 6-digit; state × sector | Establishment size | Covered jobs | Suppressed as needed | National logging size benchmark |
| CBP | Annual, March 12 week | State × 6-digit × size verified | Establishment size | Private employer employees | Flags and noise ranges | State size-structure measurement |
| SUSB | Annual, March 12 week | State × industry, detail varies | Primarily enterprise size | Private employer employees | Disclosure protection | Structural prior; firm context |
| CES state | Monthly | Few states × NAICS 1133 | Establishment survey | Nonfarm payroll jobs | Sampling error/revisions | Seasonality proxy |
| BDS | Annual | State × up to 4-digit | Firm and establishment characteristics | Employment dynamics | Protected aggregates | Transition prior |
| NES | Annual | State × detailed NAICS | Nonemployer business | No employees; receipts only | Protected aggregates | Proprietor sensitivity |
| BEA Regional | Annual | State × available industry | Persons/jobs by table | Wage jobs and proprietors available separately | Published aggregates | Broader regularizer |
| TPO/NRUM | Annual, survey cycle | State/county, forest product | Mill/origin activity | No employment | Sampling/model uncertainty | Harvest signal |
| FIA | Multi-year/annualized | State and custom areas | Forest plot | No employment | Sampling errors | Harvest-removals signal |

Direct substitution is invalid when the universe, reference period, statistical unit, size concept, or industry level differs. Differences in timing and measurement error can be modeled. A firm-size series cannot be converted to establishment size without a multi-establishment ownership model.

## 4. Data gaps and suppression patterns

1. **Core gap:** suppressed state-month QCEW logging employment.
2. **Structural gap:** no direct public monthly state-six-digit establishment-size employment.
3. **Reference-period gap:** QCEW size and CBP are March-centered; they do not identify monthly class migration.
4. **Universe gap:** QCEW covered jobs, Census employer employees, BEA persons/jobs, and nonemployers differ.
5. **Selection gap:** suppression is not plausibly missing completely at random because it is related to cell concentration and disclosure risk.
6. **Vintage gap:** current/prior-year QCEW records can be revised, and Census products arrive later.

Classify each target cell as observed, suppressed but deterministically bounded, or model-only. Never infer a true zero from a field paired with nondisclosure code `N`. citeturn1search63

## 5. Ranked proxy inventory

### State total logging employment

1. Adjacent disclosed QCEW employment and establishment counts: same universe and exact industry; strongest.
2. Compatible QCEW national residual and broader-industry state margins: accounting anchor.
3. CBP state logging employment per establishment: strong annual level signal, March-centered.
4. Latent harvest activity from TPO and FIA: causal production signal but annual/noisy.
5. Available CES state Logging: monthly movement, broader 1133 and sparse states.
6. BEA broader forestry/logging wages or employment: indirect regularizer.
7. Timber permits/sales, weather, wildfire, snow, and road restrictions: monthly timing only.

### State establishment-size composition

1. CBP state × 113310 × establishment size: direct annual structural measurement.
2. QCEW national × 113310 size distribution: national benchmark.
3. Historical CBP state logging distributions: persistence prior.
4. SUSB: useful only with size concept explicitly retained as enterprise size.
5. BDS broader-industry establishment-size transitions: transition prior.

### Monthly movement and seasonality

Rank adjacent QCEW months, same-month prior year, available CES, monthly permits/timber sales, and weather/operating restrictions. TPO and FIA should not be interpolated into false monthly precision.

### Proprietor activity

NES counts/receipts and BEA proprietors’ employment are the leading sources. Keep them outside the core covered-job estimand unless the assignment explicitly changes the population.

To avoid double counting, combine TPO origin volume, FIA harvest removals, residue, and mill indicators in a latent harvest factor with source-specific measurement errors.

## 6. Deterministic identification and feasible-bound strategy

For each month, create integer variables \(E_{s,t}\ge0\). Add only verified compatible restrictions:

- **(a) Public accounting fact:** disclosed QCEW cells equal published values.
- **(a):** compatible national total equals the sum of state cells.
- **(a):** compatible region/ownership/industry children sum to parent intervals.
- **(b) Definitional support:** if \(C_{s,t,k}\) establishments are known in class \([L_k,U_k]\), then \(L_kC_{s,t,k}\le E_{s,t,k}\le U_kC_{s,t,k}\).
- **(b):** classes and states sum to totals.
- **(c) Empirical measurement:** rounded or noise-infused values enter as intervals, not identities.

Compute sharp lower and upper bounds by solving two MILPs per target cell. Treat the 1,000-plus class with no finite strict upper bound unless a compatible public parent total supplies one. Annual or March counts constrain only their reference period.

LP/MILP results are **identified feasible intervals**. Bayesian credible intervals are **model-dependent posterior intervals**. Report both.

## 7. Recommended Bayesian model

### 7.1 Decomposition

\[
E_{s,t,k}=A_{s,t}\,p_{s,t,k}\,r_{s,t,k},\qquad
E_{s,t}=\sum_k E_{s,t,k}.
\]

Here \(A_{s,t}\) is the number of active logging establishments, \(p_{s,t,k}\) is the share in class \(k\), and \(r_{s,t,k}\) is expected jobs per establishment. If quarterly QCEW establishment counts are observed, model monthly \(A_{s,t}\) as piecewise constant within quarter in the baseline and test a latent monthly alternative.

### 7.2 State employment intensity

\[
\log(E^*_{s,t}/A_{s,t})=\alpha+u_s+u_{r[s]}+\gamma_{m(t)}+\delta_{y(t)}+x_{s,t}'\beta+h_{s,t}+z_{s,t}.
\]

Use \(u_s\sim N(0,\sigma_s^2)\), regional effects \(u_r\), sum-to-zero monthly seasonality, and regularized coefficients. Let

\[
z_{s,t}=\phi_s z_{s,t-1}+\epsilon_{s,t},\quad
\epsilon_{s,t}\sim t_\nu(0,\sigma_{z,s}).
\]

A Student-t AR(1) is preferred to a random walk because logging intensity is persistent but plausibly mean-reverting, while heavy tails accommodate closures, disasters, recodes, and abrupt market changes. Add a sparse change-point component \(J_{s,t}d_{s,t}\), with \(J_{s,t}\sim\text{Bernoulli}(\pi_J)\), only if validation supports it.

Suggested priors: \(\phi_s\) hierarchically centered near 0.8 after transformation; standardized \(\beta_j\sim N(0,0.5^2)\); \(\nu=4+\text{Exponential}(1/10)\); half-normal scale priors. These are modeling assumptions and must be stress-tested.

### 7.3 Size shares

Use a logistic-normal composition:

\[
\eta_{s,t,k}=\mu_k+a_{s,k}+b_{r[s],k}+c_{y,k}+f_{s,t,k},\qquad
p_{s,t,k}=\frac{e^{\eta_{s,t,k}}}{\sum_j e^{\eta_{s,t,j}}}.
\]

Let \(f_{s,t,k}\) evolve as a low-variance AR(1) around the annual March distribution. CBP size counts enter as multinomial or overdispersed multinomial measurements of \(p_{s,March,k}\). QCEW national logging size shares provide a compatible annual national observation. Permit seasonal size effects only if pseudo-suppression testing improves out-of-sample performance.

### 7.4 Within-class employment intensity

For bounded classes, transform a beta-distributed mean into support:

\[
r_{s,t,k}=L_k+(U_k-L_k)\operatorname{logit}^{-1}(q_{s,t,k}).
\]

For the top class, use \(r_{s,t,K}=1000+\exp(q_{s,t,K})\) with a strongly regularized lognormal or Pareto-tail prior calibrated to national QCEW size data. This is a probabilistic tail model, not a public upper bound.

### 7.5 Measurement equations

- QCEW disclosed: exact conditioning, \(Y^Q_{s,t}=E_{s,t}\).
- QCEW suppressed: interval/censoring likelihood if public bounds exist.
- CBP March employment and size: source-specific lognormal/count likelihood, including flags/noise ranges.
- TPO/FIA: noisy indicators of latent harvest \(H_{s,y}\), with FIA sampling error carried into its likelihood.
- BEA/CES/broader QCEW: bridge equations with explicit aggregation bias and source variance.
- Weather/permits: regression covariates or monthly indicators, never accounting constraints.

## 8. Exact reconciliation strategy

Let \(D_t\) be disclosed states and \(M_t\) states needing imputation. If a compatible national QCEW benchmark \(N_t\) exists,

\[
R_t=N_t-\sum_{s\in D_t}Y_{s,t}.
\]

Generate unconstrained positive weights \(w_{s,t}=\exp(\theta_{s,t})\) and set

\[
E_{s,t}=R_t\frac{w_{s,t}}{\sum_{j\in M_t}w_{j,t}},\quad s\in M_t.
\]

This preserves disclosed state values and national adding-up in every posterior draw. If state lower bounds \(L_{s,t}\) exist, first allocate the mandatory mass and normalize over the residual capacity. For upper bounds, use a bounded-simplex transform or projection sampler. Apply the same approach to size classes where compatible margins exist.

For publication integers, use balanced controlled rounding: floor each model estimate, then distribute the remaining units to cells with largest fractional parts while respecting bounds and margins. Retain continuous draws internally.

## 9. Alternative models and baselines

Benchmark against: establishment-count proportional allocation; equal residual allocation; last observed state share; same-month prior-year share; exponentially weighted shares; CBP employment-per-establishment allocation; harvest-volume allocation; constrained regression plus reconciliation; Bayesian model without forestry proxies; and Bayesian model without temporal smoothing.

The most credible fallback is **reconciled historical state shares with establishment-count and CBP intensity adjustment**. It is transparent, uses close-universe evidence, and avoids false precision from weak forestry proxies. Adopt the full model only if it materially improves masked-cell accuracy and probabilistic calibration.

## 10. Validation and sensitivity plan

Create pseudo-suppression tests from disclosed QCEW cells using nonrandom designs: small/concentrated-cell masks, clustered state-period masks, regional holdouts, long missing runs, rolling-origin forecasts, structural-break periods, NAICS-vintage boundaries, and preliminary-versus-final comparisons. Separate retrospective smoothing from real-time nowcasting.

Report MAE, RMSE, WAPE, median APE where denominators are stable, state-share error, size-share error, CRPS/log score, interval coverage and width, calibration by state size and suppression duration, and all constraint violations. Require the complex model to beat transparent baselines. If it does not, use the simpler model.

Sensitivity analyses should vary suppression-selection scenarios, state-share priors, residual variance for suppressed cells, heavy-tail strength, harvest-factor inclusion, top-class tail, temporal dynamics, and source bridge variances.

## 11. Privacy and disclosure-risk assessment

Do not publish a reconstruction as an official value. Flag cells whose public constraints exactly reconstruct a suppressed value, whose deterministic interval is unusually narrow, or whose posterior is dominated by a strong prior. Also flag cases where public employer information could reveal a dominant establishment. Where risk is high, aggregate states, months, or size classes; widen intervals; suppress cell-level estimates; or use restricted access. The purpose is aggregate analysis, not business identification.

## 12. Recommended production data pipeline

1. Ingest QCEW quarterly industry slices and archive raw files, timestamps, hashes, release status, and NAICS vintage.
2. Validate `industry_code=113310`, private ownership, state aggregation, and disclosure codes.
3. Ingest CBP API/bulk state files and verify all `EMPSZES` rows for 113310.
4. Ingest QCEW national size slices, SUSB files, BDS, NES, BEA, TPO, FIA, and selected monthly administrative/weather signals.
5. Harmonize geography, month, ownership, universe, unit, industry vintage, and source reference period in a metadata-first staging layer.
6. Build public accounting matrices and MILP bounds.
7. Fit baselines, then the Bayesian model.
8. Reconcile every draw; run deterministic consistency checks.
9. Validate using designed pseudo-suppression and frozen historical vintages.
10. Produce estimates with observed/imputed flags, bounds, posterior intervals, source lineage, and disclosure-risk flags.

## 13. Machine-readable source inventory

```yaml
- source_id: qcew_quarterly
  agency: BLS
  dataset: Quarterly Census of Employment and Wages
  access_status: VERIFIED_DOCUMENTATION
  landing_url: https://www.bls.gov/cew/downloadable-data-files.htm
  endpoint_pattern: https://data.bls.gov/cew/data/api/{year}/{quarter}/industry/113310.csv
  frequency: quarterly_release_with_three_monthly_employment_fields
  geography: state_and_national
  industry: six_digit_NAICS
  ownership: private_and_government_codes
  unit: establishment
  employment_concept: UI_UCFE_covered_jobs
  size_definition: establishment_March_employment
  disclosure: disclosure_code_N
  role: direct_total_and_accounting_anchor

- source_id: qcew_size
  agency: BLS
  dataset: QCEW establishment size data
  access_status: VERIFIED_DOCUMENTATION
  landing_url: https://www.bls.gov/cew/classifications/size/size-data-info.htm
  frequency: first_quarter_annual
  simultaneous_detail: national_x_6digit_or_state_x_sector
  role: national_logging_size_benchmark

- source_id: cbp
  agency: Census_Bureau
  dataset: County Business Patterns
  access_status: VERIFIED_DOCUMENTATION
  base_endpoint: https://api.census.gov/data/2023/cbp
  example: https://api.census.gov/data/2023/cbp?get=NAME,NAICS2017_LABEL,EMPSZES,EMPSZES_LABEL,ESTAB,EMP,EMP_F,EMP_N&for=state:01&NAICS2017=113310&LFO=001&key=YOUR_KEY
  api_key_required: true
  frequency: annual
  reference_period: week_of_March_12
  simultaneous_detail: state_x_6digit_x_establishment_size
  disclosure: flags_and_EMP_noise_range
  role: annual_state_size_structure_measurement

- source_id: susb
  agency: Census_Bureau
  dataset: Statistics_of_US_Businesses
  access_status: DOCUMENTED_NOT_EXECUTED
  landing_url: https://www.census.gov/programs-surveys/susb/data/tables.html
  download_directory: https://www2.census.gov/programs-surveys/susb/tables/2022/
  frequency: annual
  size_definition: enterprise_employment_size_in_core_products
  role: structural_prior_not_establishment_size_substitute

- source_id: bds
  agency: Census_Bureau
  dataset: Business_Dynamics_Statistics
  access_status: VERIFIED_DOCUMENTATION
  endpoint: https://api.census.gov/data/timeseries/bds
  frequency: annual
  industry_detail: up_to_4_digit_NAICS
  role: broader_industry_transition_prior

- source_id: ces_state
  agency: BLS
  dataset: Current_Employment_Statistics_State_and_Area
  access_status: VERIFIED_DOCUMENTATION
  landing_url: https://www.bls.gov/sae/
  frequency: monthly
  industry: NAICS_1133_logging_for_four_states
  role: seasonality_and_turning_point_proxy

- source_id: nonemployer
  agency: Census_Bureau
  dataset: Nonemployer_Statistics
  access_status: VERIFIED_DOCUMENTATION
  base_endpoint: https://api.census.gov/data/2023/nonemp
  api_key_required: true
  frequency: annual
  employment_concept: no_paid_employees
  role: proprietor_sensitivity

- source_id: bea_regional
  agency: BEA
  dataset: Regional
  access_status: DOCUMENTED_REQUIRES_METADATA_DISCOVERY
  endpoint: https://apps.bea.gov/api/data
  api_key_required: true
  frequency: annual
  role: broader_employment_proprietor_compensation_regularizer

- source_id: tpo_nrum
  agency: USDA_Forest_Service
  dataset: Timber_Products_Output_National_Resource_Use_Monitoring
  access_status: VERIFIED_DOCUMENTATION
  landing_url: https://research.fs.usda.gov/programs/nrum
  frequency: annual_or_survey_cycle
  role: latent_harvest_activity_measurement

- source_id: fia
  agency: USDA_Forest_Service
  dataset: FIADB_API_EVALIDator
  access_status: VERIFIED_DOCUMENTATION
  endpoint: https://apps.fs.usda.gov/fiadb-api/fullreport
  documentation: https://apps.fs.usda.gov/fiadb-api/
  frequency: inventory_evaluation
  uncertainty: sampling_errors_available
  role: harvest_removals_measurement
```

## 14. Bibliography

All links accessed 2026-09-03.

1. BLS, QCEW Overview: https://www.bls.gov/cew/overview.htm citeturn1search7
2. BLS, QCEW Data Files: https://www.bls.gov/cew/downloadable-data-files.htm citeturn1search2
3. BLS, QCEW CSV Data Slices: https://www.bls.gov/cew/additional-resources/open-data/csv-data-slices.htm citeturn1search56
4. BLS, QCEW Quarterly File Layout: https://www.bls.gov/cew/about-data/downloadable-file-layouts/quarterly/naics-based-quarterly-layout.htm citeturn1search63
5. BLS, QCEW Size Data: https://www.bls.gov/cew/classifications/size/size-data-info.htm citeturn1search44
6. BLS, QCEW Size Classes: https://www.bls.gov/cew/classifications/size/size-titles.htm citeturn1search45
7. Census Bureau, NAICS 113310: https://www.census.gov/naics/?input=logging&year=2022&details=113310 citeturn1search52
8. Census Bureau, CBP API: https://www.census.gov/data/developers/data-sets/cbp-zbp/cbp-api.html citeturn1search8
9. Census Bureau, 2023 CBP Variables: https://api.census.gov/data/2023/cbp/variables.html citeturn1search10
10. Census Bureau, 2023 CBP Downloads: https://www.census.gov/data/datasets/2023/econ/cbp/2023-cbp.html citeturn1search67
11. Census Bureau, SUSB: https://www.census.gov/programs-surveys/susb.html citeturn1search15
12. Census Bureau, BDS: https://www.census.gov/programs-surveys/bds.html citeturn1search75
13. Census Bureau, Nonemployer API: https://www.census.gov/data/developers/data-sets/nonemp-api.html citeturn1search38
14. BLS, CES State Series Structure: https://www.bls.gov/sae/additional-resources/state-and-area-ces-series-code-structure-under-naics.htm citeturn1search36
15. BEA, API User Guide: https://apps.bea.gov/api/_pdf/bea_web_service_api_user_guide.pdf citeturn1search30
16. USDA Forest Service, NRUM: https://research.fs.usda.gov/programs/nrum citeturn1search21
17. USDA Forest Service, FIADB-API Documentation: https://apps.fs.usda.gov/fiadb-api/ citeturn1search69
18. USDA Forest Service, Cut and Sold Reports: https://www.fs.usda.gov/managing-land/forest-management/reports citeturn1search25

## 15. Unresolved questions and evidence gaps

- The assignment does not specify its time range. This determines which NAICS vintage, reconstructed QCEW history, and source availability are relevant.
- An actual keyed CBP query should be executed to enumerate 2023 `EMPSZES` codes and inspect logging-specific flags for every state.
- SUSB file layouts should be inspected before claiming any detailed state-industry-size cross-tab beyond the published enterprise-size description.
- BEA Regional table and line codes for the closest forestry/logging series should be discovered dynamically and frozen by vintage.
- TPO downloadable-tool endpoints and state-year coverage require extraction testing; the interactive landing page alone does not establish nationwide annual completeness.
- The compatibility of national QCEW logging totals with the sum of state private-ownership records should be tested quarter by quarter, including residual areas and disclosure patterns.
- Public QCEW disclosure rules do not fully identify the selection process. Suppression modeling must remain a sensitivity exercise, not a claim of identified missingness.
