# Reproducible Estimation of Monthly U.S. State Logging Employment (NAICS 113310), Total and by Establishment Employment-Size Class

## 1. Executive Summary

The supplied code "1113310" is invalid as written (seven digits). The intended industry is almost certainly **NAICS 113310, Logging**, a six-digit U.S. national industry under 11331/1133/113 (Forestry and Logging). I do not silently correct it: I flag it and proceed on the verified premise that the target is 113310. NAICS 113310 has been **stable in code, title, and scope across the 2002, 2007, 2012, 2017, and 2022 vintages** (verified against the BLS QCEW NAICS crosswalk and the Census 2017 NAICS restatement, whose definitional changes were confined to sectors 51/53/54).

**The central finding is that the target latent quantity — E[state, month, establishment-size-class] for logging — does not exist in any single published source, and cannot be assembled by simple joins.** The binding constraints are: (a) QCEW publishes monthly state × 6-digit employment but **no size detail at that intersection** — QCEW establishment-size data exist only for Q1, and only at *national × 6-digit* and *state × NAICS-sector* aggregations; (b) CBP publishes annual (March-reference) *state × 6-digit × size-class* data, and — contrary to a common assumption — **employment (EMP) is tabulated by size class at the state and national levels** (only county/MSA/CSA/ZIP are restricted to establishment counts by size), but it is annual, noise-infused, and subject to a ≥3-establishment publication cutoff; (c) size-class data everywhere are annual/March, never monthly. The problem is therefore a **data-fusion / small-area estimation problem**: a monthly state-total spine from QCEW, reconciled to a national monthly benchmark, cross-classified by a slowly-evolving size-class composition anchored to annual CBP/SUSB structural observations, with deterministic feasible bounds from public margins.

For scale context, U.S. logging (NAICS 11331) is a small, fragmented industry: IBISWorld estimates **77,612 people employed across 43,153 businesses in 2025** (a −2.0% five-year employment CAGR 2020–2025) generating $16.1bn revenue, with **an average of just 1.8 employees per business** (IBISWorld, NAICS 11331, updated December 2025). This fragmentation is exactly why small-state monthly cells are frequently suppressed and why size-class disclosure risk is acute.

**Recommendation (staged):** (1) Build the monthly state-total layer first from QCEW private (own_code 5) 6-digit files, treating disclosed cells as observed and suppressed cells as LP/MILP-bounded, reconciled to the QCEW national monthly total via a positive-weight reparameterization. (2) Layer the size-class composition as a hierarchical logistic-normal process whose annual marginal is measured by CBP establishment-count-by-size distributions (and SUSB for firm-size sensitivity), with support constraints from size-class endpoints. (3) Only publish size-class employment at coarsened geographies/size-groupings where disclosure risk is acceptable. If the full model does not beat establishment-count-proportional allocation in pseudo-suppression validation, ship the baseline.

**Default assumptions (stated for override):** time span = full NAICS-era QCEW history (1990–present for monthly employment; NAICS-basis size/CBP from 2002 forward), current modeling focus NAICS-2022 vintage; primary universe = private ownership (own_code 5); target size dimension = **establishment** employment size (not firm/enterprise size); employment concept = QCEW-covered wage-and-salary jobs (monthly, third-of-month pay period), with CBP mid-March employment and BEA/Nonemployer as bridge sources for the proprietor-inclusive concept.

## 2. Verified NAICS Code, Target Population, and Statistical Unit

- **Code/title (VERIFIED):** NAICS 113310 *Logging*. Definition: "establishments primarily engaged in one or more of the following: (1) cutting timber; (2) cutting and transporting timber; and (3) producing wood chips in the field." Parent chain: 11 → 113 → 1133 → 11331 → 113310. The SBA small-business size standard is 500 employees (a program threshold, not a statistical size class); note SBA stated in its 2012 rule (77 FR 55757, Sept 11 2012) that it "did not review the 500-employee based size standard for NAICS 113310, Logging, but will review it in the near future with other employee based size standards."
- **Vintage stability (VERIFIED):** identical across NAICS 2002/2007/2012/2017/2022. The BLS QCEW industry-titles/crosswalk file tags codes that changed at a revision (e.g., NAICS07/NAICS12/NAICS17 markers); 113/1133/11331/113310 carry no such marker. Census 2017 restatement changes were limited to sectors 51, 53, 54. **Implication:** no industry-bridge model is required for logging across the NAICS era — a rare simplification. (I still flag the SIC→NAICS break at 1990/pre-2001 SIC 241 Logging as a separate regime if the span is extended before NAICS.)
- **Employment concept being estimated:** primary target is **QCEW-covered wage-and-salary employment** (UI-covered jobs, monthly count for the pay period including the 12th). This differs from: CBP (mid-March employees of employer establishments), SUSB (March-12 employment tabulated by *enterprise* size), BEA SAEMP25N (wage-and-salary + proprietors), and Nonemployer Statistics (no paid employees at all). These are **not interchangeable universes** and each enters only through an explicit bridge/measurement equation.
- **Statistical unit:** QCEW = UI *reporting unit* ≈ establishment (worksite); CBP = establishment; SUSB size dimension = *enterprise* (firm); Nonemployer = nonemployer establishment (tax unit). **Establishment-size vs firm-size is a first-order distinction here**: with an average of ~1.8 employees per logging business (IBISWorld, Dec 2025), logging is dominated by very small single-establishment firms, so establishment-size ≈ firm-size in most cells — but this must be verified, not assumed, and SUSB firm-size data are used only as a firm-size sensitivity anchor, not as an establishment-size substitute.
- **Ownership (VERIFIED codes):** QCEW own_code 0=Total Covered, 5=Private, 1=Federal, 2=State, 3=Local, 8=Total Government, 9=Total UI Covered. Logging is overwhelmingly private; government-owned logging establishments are rare but the adding-up identity must use a single consistent ownership universe. Primary universe = own_code 5 (private); the national benchmark and all state cells must be pulled at own_code 5 to be definitionally compatible.

## 3. Direct-Source Findings

### 3.1 BLS QCEW (VERIFIED)
- **Monthly employment at state × 6-digit × ownership**: quarterly NAICS CSV files carry three monthly employment observations (`month1_emplvl`, `month2_emplvl`, `month3_emplvl`), `qtrly_estabs`, wages, a `disclosure_code` (blank or 'N'), and `agglvl_code`. NAICS-coded QCEW data exist 1990 forward. This is the monthly state-total spine.
- **Open-data slice URL pattern (VERIFIED structure):** industry slice `https://data.bls.gov/cew/data/api/{YEAR}/{QTR}/industry/113310.csv`; area slice `.../area/{AREAFIPS}.csv`; size slice `.../size/{SIZECODE}.csv`. The size slice contains **only Q1** records and — critically — **only national × 6-digit and state × NAICS-sector** aggregations (agglvl 21–28 are "National, Private, …, by establishment size class"; there is **no state × 6-digit × size** aggregation level). Automated fetch of the raw CSV was blocked by robots for me (ROBOTS_DISALLOWED on data.bls.gov via the fetch tool) but the slice pattern and layout are documented; mark the endpoint **DOCUMENTED**, the layout/size-availability **VERIFIED**.
- **Establishment size (VERIFIED, decisive):** QCEW size class is assigned by **March (Q1 third-month) employment**; "these size class data are available at the national level by 6-digit NAICS industry, and at the State level by NAICS sector." Each establishment of a multi-unit firm is tabulated separately (true establishment size). **Therefore QCEW cannot deliver state × 6-digit × size for logging.**
- **Disclosure:** `disclosure_code = 'N'` marks non-disclosed cells; employment/wages are withheld but `qtrly_estabs` (establishment counts) generally remain available. QCEW/UI primary suppression follows the **"80/3 rule"**: per the Indiana Business Research Center, "Primary suppression (dubbed the 80/3 rule) occurs when… (1) There are fewer than three establishments… (2) One firm constitutes more than 80 percent of area employment," with the 80% test applied at the account level combining a firm's establishments. Preliminary vs final vintages differ; files carry revision updates.
- **Ownership/agg codes (VERIFIED):** own_code and agglvl_code documented; state 6-digit by ownership sector = agglvl 58 (DOCUMENTED); national private 6-digit by size = agglvl 28 (VERIFIED).

### 3.2 Census County Business Patterns (VERIFIED, with subagent correction)
- **State × 6-digit × size-class EMPLOYMENT exists (VERIFIED via CBP methodology):** at **national and state** levels CBP tabulates establishments, employment (week of March 12), Q1 payroll, and annual payroll **by employment size of establishment**. Only **county/MSA/CSA/ZIP** are restricted to "the number of establishments (but not employment or payroll) … by employment size of the establishment." This means CBP provides an *annual* analog of the target size-class employment vector at state × 6-digit — the single most valuable structural source.
- **Disclosure/noise (VERIFIED):** per Census, "Beginning with reference year 2017, a cell is only published if it contains three or more establishments. In all other cases, the cell is not included in the release (i.e., it is dropped from publication)" — the cell is **dropped, not zero-filled**. Since 2007, magnitude data are **noise-infused**; published EMP carries flags G (<2%), H (2–<5%), J (≥5%); pre-2015 high-noise cells were suppressed 'D'. "The use of the EMPFLAG was discontinued beginning in reference year 2018 and a noisy employment cell value is provided" (Census, 2018 CBP notes); suppression flag 'D' was replaced by 'S' from 2017. **Currency caveat (VERIFIED):** the CBP methodology page carries a banner that noise infusion is being phased out under a Commerce administrative order (DRB CBDRB-FY25-0158); the geography-level content distinctions remain.
- **API (VERIFIED endpoint + key requirement):** base `https://api.census.gov/data/{year}/cbp`; predicates `NAICS2017=` (2022 vintage file uses NAICS2017 codes; watch this) `EMPSZES=`, `for=state:{fips}`, variables `EMP,ESTAB,PAYANN,EMP_N,EMP_F,ESTAB_F`. **API key required** — my un-keyed test returned "Missing Key." Release lag is 14–18 months after the reference year (Census CBP FAQ: "Data are published annually, with data for a reference year typically being released 14-18 months after the end of that reference year"; e.g., 2023 CBP was released in 2025). EMPSZES anchor codes: 001=all sizes, 212=1–4, 220=5–9, 230=10–19, 241=20–49, 242=50–99, 251=100–249, 252=250–499, 254=500–999 (plus rollup codes).

### 3.3 Census SUSB (VERIFIED)
- Annual; state × detailed NAICS × **enterprise employment size**; number of firms, establishments, March-12 employment, annual payroll (receipts only in years ending 2/7). Covers 113 (excludes only 111/112 in the ag space). **Size = firm/enterprise, not establishment** — usable only as a firm-size sensitivity anchor and for the firm-vs-establishment wedge. Downloadable CSV per year plus API.

### 3.4 Census Nonemployer Statistics (VERIFIED)
- Annual; state × NAICS (to 6-digit for many industries); **establishments and receipts only, no employment** (businesses with no paid employees). Relevant only for the proprietor/self-employed logging-contractor universe if the target concept is widened. API base `https://api.census.gov/data/{year}/nonemp`, key required; 2022+ methodology break flagged by Census.

### 3.5 BEA Regional (DOCUMENTED)
- SAEMP25N (state total full-time+part-time employment by industry; includes proprietors) / SAEMP27N (wage-and-salary). **Finest forestry detail at state level is "Forestry, fishing, and related activities" (NAICS 113–115), not 113 alone** in most state tables — a conflict to resolve against the specific table's LineCode list. BEA local-area methodology defines line 0101 "Forestry and logging" = 113, but state employment tables commonly publish only the 113–115 aggregate. API base `https://apps.bea.gov/api/data`, dataset `Regional`, params `TableName,LineCode,GeoFips,Year`, free key; rate limits 100 req/min. Role: indirect regularizer for the proprietor-inclusive concept and broad trend, **not** a logging-specific state series.

### 3.6 BLS CES / SAE / OEWS (DOCUMENTED)
- CES publishes national logging (NAICS 1133) monthly; state SAE generally does **not** break out logging separately (forestry/logging folded into higher aggregates or natural-resources supersector). OEWS publishes national NAICS 113310/113300 and state-level NAICS 113000 (Forestry and Logging) occupational employment — annual, survey-based. Role: national monthly shape (CES) and occupational/wage structure (OEWS), not a state logging spine.

### 3.7 USDA Forest Service TPO / NRUM and FIA (VERIFIED endpoints)
- **TPO** (Timber Product Output, part of FIA's NRUM): annual state/county roundwood products harvested, logging residue, other removals, mill receipts. Harvest-origin production is the labor-relevant measure; mill receipts are location-of-processing (interstate log movement misallocates). Portal: `https://research.fs.usda.gov/programs/nrum`; interactive TPO tool + Tableau factsheets.
- **FIA DataMart / EVALIDator**: population estimates of removals with sampling errors; API `https://apps.fs.usda.gov/fiadb-api` (`/fullreport` endpoint, params `wc`, `snum`, `rselected`, `cselected`; EVALID = state FIPS + inventory year). Role: latent harvest-activity factor (with TPO), a monthly-to-annual seasonal driver only via disaggregation.

### 3.8 Other administrative (DOCUMENTED/UNVERIFIED)
- State LMI QCEW tools (e.g., Maryland, Pennsylvania "Employment by Size Code") republish QCEW size data at state/county but still by size *for total*, not by 6-digit logging × size × month. State timber severance-tax, harvest-report, and timber-sale datasets (state-specific) are candidate monthly/quarterly activity proxies. BLS Business Employment Dynamics (firm-size dynamics, Q1-based from 1993) is a firm-size, national/state-by-sector source.

## 4. Source-Compatibility Matrix

| Source | Time res. | Geo | Industry | Unit | Employment concept | Ownership | Size dim. | Direct/Proxy | Value status |
|---|---|---|---|---|---|---|---|---|---|
| QCEW monthly (state×6-digit) | **Monthly** | State | **113310** | Estab (UI unit) | UI wage&salary jobs | Private (5) / Total | n/a at this cell | **Direct** | Exact or suppressed 'N' (estabs kept) |
| QCEW size files | Q1 only | Nat'l / State | 6-digit (nat'l) / **sector (state)** | Estab | Wage&salary | Private | **Establishment** | Direct (wrong cross) | Exact |
| CBP | Annual (Mar) | **State**×6-digit | 113310 | Estab | Mar-12 employees | Private (nonfarm employer) | **Establishment** (EMP by size at state!) | Direct (annual) | Noise-infused; <3 estab dropped |
| CBP sub-state | Annual (Mar) | County/MSA×6-digit | 113310 | Estab | — | Private | Establishment (estabs only, no EMP by size) | Direct | Estab counts only |
| SUSB | Annual (Mar) | State×6-digit | 113310 | **Enterprise** | Mar-12 employees | Private | **Firm/enterprise** | Proxy (firm-size) | Suppressed via noise/withhold |
| Nonemployer | Annual | State×6-digit | 113310 | Nonemployer estab | **None (no employees)** | Private | Receipts-size (US only) | Proxy (proprietors) | Estab+receipts |
| BEA SAEMP25N/27N | Annual | State | **113–115** (usually) | Job | W&S (+proprietors 25N) | All | none | Proxy (regularizer) | (D)/(NA) suppression |
| CES (national) | Monthly | National | 1133 | Estab (sample) | W&S | Private | none | Proxy (national shape) | Sampled |
| SAE (state) | Monthly | State | usually >113 | Estab (sample) | W&S | Private | none | Weak proxy | Sampled/modelled |
| OEWS | Annual | State | 113000 / nat'l 113310 | Estab (sample) | W&S | All | none | Proxy (structure) | Sampled, RSE |
| TPO/NRUM | Annual | State/County | harvest (not NAICS) | Mill/harvest | n/a (volume) | n/a | none | Proxy (harvest factor) | Estimate |
| FIA EVALIDator | ~Annual/cycle | State/County | removals | plot | n/a (volume) | ownership splits | none | Proxy (harvest factor, w/ SE) | Estimate + sampling error |

**Modelable vs invalid substitutions:** CBP↔QCEW employment differ by reference period (mid-March vs monthly), universe (employer nonfarm vs UI-covered), and noise — reconcilable via a measurement equation with a March-alignment offset and noise variance, **not** by direct substitution. SUSB firm-size ↔ establishment-size is **not** a valid direct substitution (different unit); usable only through a firm→establishment wedge. BEA 113–115 ↔ 113 is an aggregation mismatch (fishing/support activities contaminate) — regularizer only. TPO mill receipts ↔ harvest origin is invalid for labor allocation across state lines.

## 5. Data Gaps and Suppression Patterns

1. **No monthly size-class anywhere.** Size structure is annual/March (CBP establishment-count/employment-by-size; QCEW Q1 size at wrong cross; SUSB firm-size). Monthly size composition must be modeled as a latent smooth process anchored to annual marginals — a **modeling assumption (d)**, not a public fact.
2. **QCEW state × 6-digit suppression.** Logging is small (avg 1.8 employees/business); many low-population-state monthly cells are `disclosure_code='N'`. Establishment counts typically remain → these give **definitional support restrictions (b)** and feed LP/MILP bounds. Suppression is **not MCAR**: the 80/3 rule ties it to few establishments and high concentration (one dominant operator), so suppressed states skew toward small totals and volatile employment-per-establishment.
3. **CBP <3-establishment drop.** Size-class cells for logging in small states vanish entirely (not zero) → missing rows must be treated as "unobserved," and the residual (state total minus observed size cells) is bounded, not zero.
4. **Noise infusion (CBP) and its impending removal.** Published CBP EMP is perturbed (G/H/J); carry the implied noise variance into the likelihood. The pending Commerce order to drop noise infusion means vintage-consistent handling is required — do not mix noise-infused and future non-noise vintages without a bridge.
5. **Concept/period seams:** CBP mid-March vs QCEW monthly; SUSB enterprise vs establishment; BEA 113–115 vs 113. Each is an explicit bridge, never a silent join.
6. **Preliminary vs final QCEW** and NAICS non-economic reclassification spikes between Q4 and Q1 (BLS warns these are not economic change) → change-point handling at Q4→Q1 boundaries.

## 6. Ranked Proxy Inventory

**A. State total logging employment**
1. **Lagged/adjacent-month disclosed QCEW employment** (same state) — near-direct, tiny error, AR structure. Main model.
2. **QCEW `qtrly_estabs` (establishment counts), state × 6-digit** — available even when employment suppressed; strong level proxy via employment-per-establishment. Main model (denominator of decomposition).
3. **CBP state × 6-digit employment** (annual, March) — direct concept-bridged anchor. Measurement model.
4. **TPO/FIA latent harvest activity** (state, annual) — economic driver of labor demand; positive association; annual → monthly via seasonal disaggregation. Prior/covariate.
5. **BEA 113–115 state employment** — broad regularizer. Prior only.
6. **CES national 1133 monthly** — national temporal shape for reconciliation residual. Measurement/benchmark shape.

**B. State establishment-size composition**
1. **CBP establishment-counts-by-size, state × 6-digit** (annual) — the direct measurement of the size *distribution*. Measurement model for p[s,·].
2. **QCEW Q1 state × NAICS-sector size** — coarse-industry size shape for partial pooling. Prior.
3. **SUSB firm-size, state × 6-digit** — firm-size sensitivity + firm/establishment wedge. Sensitivity.
4. **National QCEW 6-digit Q1 size** — national logging size distribution for shrinkage target. Prior.

**C. Monthly movement and seasonality**
1. **QCEW month1/2/3 within-quarter pattern** (disclosed states) — direct seasonal signal. Main model month effects.
2. **CES national 1133 monthly** — national seasonal factor. Prior.
3. **Harvest-season / weather / snow / road-restriction / wildfire indicators** — mechanistic seasonal operating conditions; regionally specific; monthly. Covariates in measurement/activity layer, only where they demonstrably improve validation.
4. **TPO annual → seasonalized** — low temporal resolution; sensitivity only.

**D. Proprietor / nonemployer activity**
1. **Nonemployer establishments/receipts, state × 6-digit** (annual) — proprietor logging contractors; only if concept widened. Separate layer.
2. **BEA SAEMP25N proprietors' component** — proprietor magnitude regularizer. Prior.

**Avoid double-counting:** TPO and FIA both measure harvest → collapse to one **latent harvest-activity factor** H[s,t] with two noisy loadings. CES national and QCEW national are the same universe → use one as benchmark, the other as shape, not two independent signals.

For each proxy the model records: mechanism (harvest volume → crew-hours → jobs; establishment counts → jobs via r); expected sign (all positive except off-season weather); temporal/geo resolution; lag (harvest→employment near-contemporaneous to ~1 month); measurement error (survey RSE for OEWS/FIA; noise for CBP; near-zero for QCEW disclosed); bias (mill-receipt spatial misallocation; firm-vs-establishment); and target (level vs employees-per-establishment vs counts vs size shares).

## 7. Deterministic Identification and Feasible-Bound Strategy

Label every restriction (a) public accounting fact, (b) definitional support, (c) empirical measurement, (d) modeling assumption, (e) sensitivity assumption.

**Exactly observed (a):** QCEW state-month cells with blank disclosure_code (private, 6-digit). These are fixed, not estimated.

**Deterministically bounded (a+b):** For a suppressed state-month with known `qtrly_estabs = A[s,t]` and known national/parent margins, employment is bounded by an LP. Let observed states O and suppressed states U for month t, national total N[t] (own_code 5, agglvl national 6-digit, if disclosed):

- Adding-up (a): Σ_{s∈U} E[s,t] = N[t] − Σ_{s∈O} E[s,t] =: R[t].
- Nonnegativity/integrality (b): E[s,t] ∈ ℤ₊.
- Establishment-based support (b): since each establishment has ≥1 employee and the cell had ≥3 units to be tabulated but was suppressed, A[s,t] ≤ E[s,t]; upper bound from the "no unit ≥80%" (80/3) rule and any disclosed higher-geography (region/division) margins.
- Size-class endpoints (b): if size-class establishment counts C[s,t,k] are known, Σ_k L_k·C[s,t,k] ≤ E[s,t] ≤ Σ_k U_k·C[s,t,k], with L_k,U_k the class bounds (top class open-ended → external cap, labeled (e), never a strict public bound).

Sharp per-cell bounds are obtained by solving min/max E[s,t] subject to all of the above with **HiGHS via `scipy.optimize.linprog`** (LP relaxation) and, where integrality binds materially, **MILP via OR-Tools/PuLP**. Rounded published totals enter as **intervals** [N−0.5, N+0.5] scaled by rounding unit, not equalities. These feasible intervals are the **support** into which the Bayesian posterior is truncated; they are model-independent and must be reported separately from posterior intervals.

**Estimable only by model (d):** the split of R[t] across U, and all monthly size-class allocations, once bounds are exhausted.

## 8. Recommended Bayesian Model (JAX/NumPyro), with Equations and Priors

Stack (user): Python + NumPyro/JAX (NUTS), Blackjax for custom kernels, Dynamax for the linear-Gaussian state-space total layer, ArviZ for diagnostics. Decomposition, per assignment, with a reparameterization that makes size shares compositional and the national identity exact in every draw:

E[s,t,k] = A[s,t] · p[s,t,k] · r[s,t,k]

where A[s,t] = establishment count (observed from QCEW `qtrly_estabs`, treated as known/near-known with small measurement error), p[s,t,k] = share of establishments in size class k (compositional), r[s,t,k] = expected employment per establishment in class k. State total E[s,t] = A[s,t]·Σ_k p[s,t,k] r[s,t,k].

**(1) State-total intensity layer.** Model log employment-per-establishment r̄[s,t] = E[s,t]/A[s,t]:

log r̄[s,t] = α + u_state[s] + v_region[r(s)] + m_month[mon(t)] + y_year[yr(t)] + β·X[s,t] + φ_s·(log r̄[s,t−1] − μ_s) + ε[s,t]

- Priors: α ~ Normal(log(≈2), 1) — center at ~2 jobs/establishment, consistent with the observed U.S. average of 1.8 employees per logging business (IBISWorld, Dec 2025), rather than 3; u_state ~ Normal(0, σ_u), σ_u ~ HalfNormal(0.5); v_region ~ Normal(0, σ_v), σ_v ~ HalfNormal(0.5); m_month sum-to-zero via `ZeroSumNormal`-style reparam, σ_m ~ HalfNormal(0.3); y_year random walk: y_year[j] ~ Normal(y_year[j−1], σ_y), σ_y ~ HalfNormal(0.2).
- Dynamics: state-specific **stationary AR(1)** φ_s = 2·sigmoid(φ*_s)−1, φ*_s ~ Normal(1,0.5) (favoring persistence); innovation ε[s,t] ~ StudentT(ν, 0, σ_ε), ν ~ Gamma(2,0.1), σ_ε ~ HalfNormal(0.3) — **heavy tails absorb openings/closures/recoding/disaster shocks** without a full change-point layer. Justification: AR(1) + Student-t is the parsimonious choice given short per-state monthly series and the dominant risk being sporadic large jumps (single dominant operator entering/leaving), not smooth regime drift; a change-point (horseshoe on Δ) is offered as sensitivity (e).
- Covariates X[s,t]: latent harvest activity H[s,t] (see (4)), CES national 1133 monthly shape, seasonal weather/road indices. β ~ Normal(0, 0.3).

**(2) Establishment-size shares (compositional).** Hierarchical **logistic-normal**: for classes k=1..K with reference class K,

η[s,t,k] = a_k + b_state[s,k] + c_month[mon(t),k] + g·Ĥ[s,t] , k=1..K−1
p[s,t,·] = softmax(η[s,t,1..K−1], 0)

- Priors: a_k ~ Normal(national logit share, 1) with the national logging Q1 size distribution as the shrinkage target; b_state[s,·] ~ MultiNormal(0, Σ_b) with LKJ(2) correlation prior across classes (partial pooling by state, region, year); c_month small (seasonal size shifts allowed but shrunk), σ_c ~ HalfNormal(0.2).
- **Annual anchoring:** the CBP annual establishment-count-by-size vector for state s, year yr is a **multinomial/Dirichlet-multinomial measurement** of the *year-average* of p[s,t,·]: Ĉ[s,yr,·] ~ DirichletMultinomial(A_cbp, κ·mean_t∈yr p[s,t,·]), κ concentration ~ Gamma(2,0.1). Monthly p thus fluctuates smoothly around the annually-measured structure — annual is reference-period info (labeled b/c), not a monthly equality.

**(3) Size-class support and bounds.** r[s,t,k] is truncated to class endpoints: r[s,t,k] ~ TruncatedNormal(ρ_k, τ_k, low=L_k, high=U_k) with L_k,U_k the class limits (e.g., class 1–4 → [1,4]); top open class uses LogNormal with an externally-supported cap (OEWS/QCEW national max), labeled (e). If C[s,t,k] observed, enforce L_k·C ≤ E[s,t,k] ≤ U_k·C by construction. When size counts are only annual/March, these are reference-period bounds (b), applied to the annual marginal, not to every month.

**(4) Measurement models (separate observation equations).**
- QCEW disclosed monthly: y^QCEW[s,t] = E[s,t] (exact; degenerate likelihood / fixed) or Normal with tiny σ for numerical stability.
- QCEW suppressed: no likelihood term; only the LP/MILP truncation of §7 restricts support.
- CBP annual state×6-digit employment: y^CBP[s,yr] ~ Normal(δ_March·(1/|Mar|)Σ E[s,Mar,·], σ_CBP²+σ_noise²), δ_March a universe/reference-period offset (CBP employer nonfarm vs UI-covered), σ_noise from the G/H/J flag. <3-estab cells contribute no term.
- SUSB firm-size: enters only the firm-size sensitivity model via a firm→establishment wedge ω; not in the main establishment-size likelihood.
- TPO & FIA: two loadings on one latent H[s,t]: TPO[s,yr] ~ Normal(λ_1 H_annual, σ_TPO), FIA_removals[s,cycle] ~ Normal(λ_2 H_annual, σ_FIA(SE)) carrying FIA sampling error. H[s,t] monthly = H_annual · seasonal[mon,region].
- BEA 113–115: y^BEA[s,yr] ~ Normal(E_113[s,yr] + other_11315[s,yr], σ_BEA), other_* a nuisance offset — regularizer only.

**(5) Exact national reconciliation (see §9).**

**(6) Suppression mechanism (not MCAR).** No fully identified selection model (rule not public). Instead: suppressed cells get (e) heavier-tailed ε (larger ν⁻¹), (e) inflated σ_ε, and (e) alternative expected shares; run scenarios with primary-like vs complementary-like pseudo-suppression. Report sensitivity of estimates to these.

**(7) Output.** Joint posterior draws (NUTS, 4 chains); retain for each (s,t,k) and (s,t): mean/median; 50/80/90/95% CrIs; observed-vs-imputed flag; direct-source flag; deterministic feasible [lower,upper] from §7; P(E>threshold); vintage/NAICS metadata. **Balanced rounding:** retain continuous expected jobs; when integers required, use a largest-remainder (Hamilton) apportionment per month so Σ_s and Σ_k are preserved exactly.

## 9. Exact Reconciliation Strategy

Preserve disclosed QCEW state values exactly. For each month t define the imputation residual against the national private benchmark:

R[t] = N_private[t] − Σ_{s∈O} E_obs[s,t]

Allocate R[t] **only** across suppressed states U via a positive-weight reparameterization that satisfies the identity in every draw:

w[s,t] = softplus(θ[s,t]) > 0 ; E[s,t] = R[t] · w[s,t] / Σ_{s'∈U} w[s',t]

with θ[s,t] = θ_state[s] + AR(1) term + β·X[s,t] (same covariates as §8.1), θ_state ~ Normal(0,1). This is the Dirichlet-like normalized-weight scheme; it makes the national adding-up an **exact identity**, avoiding a tight artificial penalty. The feasible bounds of §7 enter as a **truncation** on E[s,t] (reject/reparameterize draws outside [L,U]); with HiGHS-precomputed per-cell [L,U], use a scaled-logit map of the simplex into the box so all constraints hold by construction where the box intersection is nonempty.

**Size-class reconciliation:** where a national (or regional) size-class employment margin exists (QCEW national 6-digit Q1 size, own_code 5), enforce Σ_s A[s,t]·p[s,t,k]·r[s,t,k] = NationalSize[t,k] for the Q1/March reference month via the same normalized-weight trick along the state index within each k; for non-reference months enforce only the softer within-state simplex (p sums to 1) and the annual anchor.

**If the national benchmark is unavailable/incompatible** (e.g., national cell also suppressed, or only Total-Covered not Private): fall back to (i) regional adding-up where regional totals disclosed, (ii) the QCEW national CES-shape as a soft prior on Σ_s E, (iii) monotone consistency with disclosed higher-industry (113) state totals: E_113310[s,t] ≤ E_113[s,t] (a public accounting fact when both disclosed).

## 10. Alternative Models and Baselines

Ordered by expected credibility when the full model is unsupportable:
1. **Establishment-count proportional allocation:** E[s,t] = R[t]·A[s,t]/Σ_U A — uses the most reliable auxiliary (counts rarely suppressed); likely the **strongest simple baseline**.
2. **CBP employment-per-establishment allocation:** weight A[s,t] by state CBP jobs/estab (concept-bridged).
3. **Same-month-previous-year state share** and **last-observed share** (persistence baselines).
4. **Rolling / EWMA historical shares.**
5. **Harvest-volume (TPO) proportional allocation.**
6. **Equal allocation of residual** (naïve floor).
7. **Constrained regression + raking** to national/regional margins.
8. **Bayesian model without forestry proxies** (tests proxy value).
9. **Bayesian model without temporal smoothing** (tests dynamics value).

**Recommendation:** require the full hierarchical model to beat baseline (1) on held-out disclosed cells (§11). If it does not, ship establishment-count proportional allocation with LP/MILP bounds — transparent, near-identity, and defensible.

## 11. Validation and Sensitivity Plan

**Pseudo-suppression design (not random-only):** mask disclosed state-month cells using patterns that mimic real suppression — (i) small/concentrated cells (low A, high HHI), (ii) clustered across neighboring states/quarters, (iii) whole-group holdouts (entire census region), (iv) long runs of consecutive missing months, (v) rolling-origin (expanding-window) real-time forecasts, (vi) retrospective smoothing evaluated **separately** from real-time, (vii) structural-break and NAICS-revision periods, (viii) preliminary-vs-final QCEW vintage comparison.

**Metrics:** MAE, RMSE, WAPE, MdAPE (where nonzero); **state-share error** and **size-class-share error** (Aitchison distance on compositions); interval **coverage** vs nominal (50/80/90/95) and mean interval width; **CRPS**/log-score for probabilistic calibration; constraint-violation rates (national, regional, size-class, nonnegativity/integrality); calibration stratified by state size and suppression-run length; sensitivity to priors (σ hyperpriors, ν), proxy inclusion (drop TPO/FIA; drop CBP anchor), and suppression-scenario (e).

**Decision rule:** full model must dominate baseline (1) on WAPE **and** achieve ≥nominal interval coverage without excessive width; otherwise recommend the baseline. Report the win/loss per stratum, not just pooled.

## 12. Privacy and Disclosure-Risk Assessment

Because logging is a small, concentrated industry (avg ~1.8 employees/business; ~43k businesses nationally), several risks are acute: (i) LP/MILP bounds can become **degenerate** (L≈U) for a suppressed cell when parent/child margins nearly pin it — this can **reconstruct an officially suppressed QCEW value**; (ii) narrow deterministic bounds combined with public employer lists (a single dominant logging firm in a state) risk identifying a dominant establishment; (iii) posterior precision may be driven by strong priors rather than data — flag when the posterior width ≪ feasible-bound width only because of the prior. **Mitigations:** publish size-class employment only at **coarsened geographies** (multi-state regions) or **collapsed size groups** (e.g., <20 / 20–99 / 100+) where reconstruction risk is acceptable; widen released intervals to the feasible bounds; route cell-level estimates through restricted access; never label a model estimate as an official BLS/Census value; suppress or aggregate any cell where the deterministic interval width falls below a disclosure threshold or where one establishment could be inferred. Prefer answering the research question at the coarsest geography/size grouping that suffices.

## 13. Recommended Production Data Pipeline (Python/Polars)

Design: reproducible, vintage-pinned, constraint-aware. Tabular handling in **Polars**; solves in HiGHS/OR-Tools; inference in NumPyro/JAX; diagnostics in ArviZ. Pin every source vintage (QCEW release date, CBP reference year, NAICS 2022).

**Ingestion.**

QCEW industry slice (cURL):
```
curl -s 'https://data.bls.gov/cew/data/api/2024/1/industry/113310.csv' -o qcew_113310_2024q1.csv
```

QCEW pull + filter (Python/Polars):
```python
import polars as pl
import urllib.request


def fetch_qcew_industry(year, qtr, naics='113310'):
    url = f'https://data.bls.gov/cew/data/api/{year}/{qtr}/industry/{naics}.csv'
    fn = f'qcew_{naics}_{year}q{qtr}.csv'
    urllib.request.urlretrieve(url, fn)
    return fn


def load_state_private_monthly(fn):
    lf = pl.scan_csv(fn, infer_schema_length=0)
    out = (
        lf.filter(pl.col('own_code').eq('5'))
          .filter(pl.col('agglvl_code').eq('58'))  # state x 6-digit x ownership
          .select([
              'area_fips', 'year', 'qtr', 'disclosure_code',
              'qtrly_estabs', 'month1_emplvl', 'month2_emplvl', 'month3_emplvl',
          ])
          .with_columns([
              pl.col('qtrly_estabs').cast(pl.Int64),
              pl.col('month1_emplvl').cast(pl.Int64),
              pl.col('month2_emplvl').cast(pl.Int64),
              pl.col('month3_emplvl').cast(pl.Int64),
              pl.col('disclosure_code').eq('N').alias('suppressed'),
          ])
    )
    return out.collect()
```

CBP size-class pull (cURL, key required):
```
curl -s 'https://api.census.gov/data/2022/cbp?get=NAME,ESTAB,EMP,EMP_F,EMP_N&for=state:*&NAICS2017=113310&EMPSZES=001&key=YOUR_KEY'
```

CBP by size class (Python/Polars):
```python
import polars as pl
import urllib.request
import json


def fetch_cbp_by_size(year, state='*', naics='113310', key='YOUR_KEY'):
    base = f'https://api.census.gov/data/{year}/cbp'
    q = (f'?get=NAME,ESTAB,EMP,EMP_F,EMP_N&for=state:{state}'
         f'&NAICS2017={naics}&EMPSZES=*&key={key}')
    with urllib.request.urlopen(base + q) as r:
        rows = json.loads(r.read().decode())
    df = pl.DataFrame(rows[1:], schema=rows[0])
    return df.with_columns([
        pl.col('ESTAB').cast(pl.Int64),
        pl.col('EMP').cast(pl.Int64, strict=False),
    ])
```

BEA regional (cURL):
```
curl -s 'https://apps.bea.gov/api/data/?UserID=YOUR_KEY&method=GetData&DataSetName=Regional&TableName=SAEMP25N&LineCode=100&GeoFips=STATE&Year=ALL&ResultFormat=JSON'
```

**Bound computation (HiGHS via SciPy):**
```python
import numpy as np
from scipy.optimize import linprog


def cell_bounds(residual, weights_lb, estab_counts, upper_caps):
    n = len(estab_counts)
    a_eq = np.ones((1, n))
    b_eq = np.array([residual])
    bounds = list(zip(estab_counts.tolist(), upper_caps.tolist()))
    lows, highs = [], []
    for i in range(n):
        c = np.zeros(n)
        c[i] = 1.0
        lo = linprog(c, A_eq=a_eq, b_eq=b_eq, bounds=bounds, method='highs')
        hi = linprog(-c, A_eq=a_eq, b_eq=b_eq, bounds=bounds, method='highs')
        lows.append(lo.x[i])
        highs.append(-hi.fun)
    return np.array(lows), np.array(highs)
```

**Pipeline stages:** (1) ingest + vintage-pin (QCEW monthly state 6-digit private; CBP annual state×6-digit×size; SUSB; Nonemployer; BEA; TPO/FIA); (2) harmonize NAICS-2022, FIPS, ownership=private, reference periods; (3) classify each cell observed/suppressed; (4) compute LP/MILP feasible bounds; (5) NumPyro model (Dynamax for the linear-Gaussian total spine as an optional fast pre-estimate → NUTS for full joint); (6) posterior post-processing (balanced rounding, credible intervals, ArviZ diagnostics — R̂, ESS, PPCs); (7) disclosure review + coarsening; (8) emit parquet of joint draws + metadata. Orchestrate with a DAG; cache raw pulls immutably keyed by release date.

## 14. Machine-Readable Source Inventory

```json
[
  {
    "agency": "BLS",
    "dataset": "QCEW quarterly NAICS files (monthly employment, state x 6-digit)",
    "table_or_endpoint": "industry slice CSV",
    "url": "https://data.bls.gov/cew/data/api/{year}/{qtr}/industry/113310.csv",
    "access_date": "2026-09-10",
    "years_available": "1990-present (NAICS)",
    "release_frequency": "quarterly (preliminary then final)",
    "reference_period": "monthly, pay period incl. 12th",
    "geography": "national/state/county/MSA",
    "industry_detail": "6-digit NAICS 113310",
    "ownership": "own_code 0/5/1/2/3/8/9",
    "statistical_unit": "UI reporting unit (establishment)",
    "employment_concept": "UI-covered wage & salary jobs",
    "size_dimension": "none at state x 6-digit",
    "suppression_or_noise": "disclosure_code 'N' (80/3 rule); estabs usually retained",
    "revision_status": "preliminary/final vintages",
    "proposed_model_role": "monthly state-total spine (direct/observed)",
    "important_limitations": "no size at state x 6-digit; small-state suppression"
  },
  {
    "agency": "BLS",
    "dataset": "QCEW establishment-size files",
    "table_or_endpoint": "size slice CSV / agglvl 21-28 (nat'l), state x sector",
    "url": "https://data.bls.gov/cew/data/api/{year}/1/size/{size_code}.csv",
    "access_date": "2026-09-10",
    "years_available": "NAICS era, Q1 only",
    "release_frequency": "annual (Q1 only)",
    "reference_period": "March (Q1 third month)",
    "geography": "national (6-digit) / state (NAICS sector only)",
    "industry_detail": "6-digit at national; sector at state",
    "ownership": "private",
    "statistical_unit": "establishment",
    "employment_concept": "wage & salary",
    "size_dimension": "establishment employment size",
    "suppression_or_noise": "disclosure_code",
    "revision_status": "final",
    "proposed_model_role": "national size distribution prior; NOT state x 6-digit",
    "important_limitations": "no state x 6-digit x size intersection"
  },
  {
    "agency": "Census",
    "dataset": "County Business Patterns",
    "table_or_endpoint": "cbp API (CB22..CBP)",
    "url": "https://api.census.gov/data/2022/cbp?get=EMP,ESTAB,EMP_N&for=state:*&NAICS2017=113310&EMPSZES=*",
    "access_date": "2026-09-10",
    "years_available": "annual, NAICS from 1998; ~14-18 mo lag",
    "release_frequency": "annual",
    "reference_period": "week of March 12",
    "geography": "state x 6-digit (EMP by size); county/MSA (estabs by size only)",
    "industry_detail": "6-digit NAICS 113310",
    "ownership": "private nonfarm employer",
    "statistical_unit": "establishment",
    "employment_concept": "mid-March employees",
    "size_dimension": "establishment employment size (EMPSZES)",
    "suppression_or_noise": "noise-infused (G/H/J); <3 estab cell dropped; 'S' withhold",
    "revision_status": "final; noise-infusion being phased out (Commerce order)",
    "proposed_model_role": "annual state x size measurement/anchor (direct)",
    "important_limitations": "annual/March; API key required; noise; small-cell drop"
  },
  {
    "agency": "Census",
    "dataset": "Statistics of U.S. Businesses (SUSB)",
    "table_or_endpoint": "SUSB annual datasets / API",
    "url": "https://www.census.gov/data/datasets/2021/econ/susb/2021-susb.html",
    "access_date": "2026-09-10",
    "years_available": "annual",
    "release_frequency": "annual",
    "reference_period": "week of March 12",
    "geography": "US/state x 6-digit",
    "industry_detail": "6-digit NAICS 113310",
    "ownership": "private (excl. 111/112, most govt)",
    "statistical_unit": "enterprise (firm) for size; establishment counts too",
    "employment_concept": "mid-March employees",
    "size_dimension": "ENTERPRISE employment size (firm size)",
    "suppression_or_noise": "noise/withhold",
    "revision_status": "final",
    "proposed_model_role": "firm-size sensitivity; firm->establishment wedge",
    "important_limitations": "firm size, not establishment size"
  },
  {
    "agency": "Census",
    "dataset": "Nonemployer Statistics",
    "table_or_endpoint": "nonemp API",
    "url": "https://api.census.gov/data/2022/nonemp?get=ESTAB,NRCPTOT&for=state:*&NAICS2017=113310",
    "access_date": "2026-09-10",
    "years_available": "1997-present",
    "release_frequency": "annual",
    "reference_period": "annual",
    "geography": "state x 6-digit",
    "industry_detail": "6-digit NAICS 113310",
    "ownership": "nonemployer (no paid employees)",
    "statistical_unit": "nonemployer establishment",
    "employment_concept": "none (proprietor activity via receipts)",
    "size_dimension": "receipts-size (US only)",
    "suppression_or_noise": "disclosure",
    "revision_status": "final; 2022 methodology break",
    "proposed_model_role": "proprietor/self-employed layer (if concept widened)",
    "important_limitations": "no employment counts"
  },
  {
    "agency": "BEA",
    "dataset": "Regional Economic Accounts (SAEMP25N/27N)",
    "table_or_endpoint": "Regional API",
    "url": "https://apps.bea.gov/api/data/?method=GetData&DataSetName=Regional&TableName=SAEMP25N&GeoFips=STATE&Year=ALL",
    "access_date": "2026-09-10",
    "years_available": "annual, long history",
    "release_frequency": "annual",
    "reference_period": "annual",
    "geography": "state",
    "industry_detail": "usually 113-115 (Forestry, fishing, related); 113 in local-area methodology",
    "ownership": "all",
    "statistical_unit": "job",
    "employment_concept": "W&S + proprietors (25N); W&S (27N)",
    "size_dimension": "none",
    "suppression_or_noise": "(D)/(NA)/(L)",
    "revision_status": "revised annually",
    "proposed_model_role": "broad regularizer; proprietor magnitude",
    "important_limitations": "industry too broad; not logging-specific"
  },
  {
    "agency": "BLS",
    "dataset": "CES (national) / SAE (state) / OEWS",
    "table_or_endpoint": "BLS series / OEWS tables",
    "url": "https://www.bls.gov/oes/2018/May/naics4_113300.htm",
    "access_date": "2026-09-10",
    "years_available": "CES monthly; OEWS annual",
    "release_frequency": "monthly (CES) / annual (OEWS)",
    "reference_period": "pay period incl. 12th (CES); May survey (OEWS)",
    "geography": "national (CES 1133; OEWS 113310); state OEWS 113000",
    "industry_detail": "1133 / 113310 / 113000",
    "ownership": "private (CES)",
    "statistical_unit": "establishment (sample)",
    "employment_concept": "wage & salary",
    "size_dimension": "none",
    "suppression_or_noise": "sampling error/RSE",
    "revision_status": "CES revised; OEWS point-in-time",
    "proposed_model_role": "national monthly shape (CES); occupational structure (OEWS)",
    "important_limitations": "no state logging monthly series"
  },
  {
    "agency": "USDA Forest Service",
    "dataset": "Timber Product Output / NRUM; FIA DataMart/EVALIDator",
    "table_or_endpoint": "NRUM portal; FIADB-API /fullreport",
    "url": "https://apps.fs.usda.gov/fiadb-api",
    "access_date": "2026-09-10",
    "years_available": "TPO periodic/annual; FIA continuous",
    "release_frequency": "annual/periodic",
    "reference_period": "annual harvest / inventory cycle",
    "geography": "state/county",
    "industry_detail": "roundwood/removals (not NAICS)",
    "ownership": "land-ownership splits",
    "statistical_unit": "mill / FIA plot",
    "employment_concept": "none (volume)",
    "size_dimension": "none",
    "suppression_or_noise": "estimate; FIA sampling error",
    "revision_status": "periodic",
    "proposed_model_role": "latent harvest-activity factor (with FIA)",
    "important_limitations": "annual; harvest-origin vs mill-receipt allocation"
  }
]
```

## 15. Bibliography

**Primary agency documentation (all accessed 2026-09-10):**
- BLS QCEW establishment size data: https://www.bls.gov/cew/classifications/size/size-data-info.htm
- BLS QCEW open data / CSV slices: https://www.bls.gov/cew/additional-resources/open-data/csv-data-slices.htm ; home: https://www.bls.gov/cew/additional-resources/open-data/home.htm
- BLS QCEW NAICS quarterly file layout: https://www.bls.gov/cew/about-data/downloadable-file-layouts/quarterly/naics-based-quarterly-layout.htm (txt: .../naics-based-quarterly-layout.txt)
- BLS QCEW aggregation-level codes: https://www.bls.gov/cew/classifications/aggregation/agg-level-titles.htm
- BLS QCEW ownership codes (NAICS): https://www.bls.gov/cew/classifications/ownerships/ownership-titles.htm
- BLS QCEW industry titles / NAICS crosswalk: https://www.bls.gov/cew/classifications/industry/industry-titles.htm ; 2017 hierarchy crosswalk: https://www.bls.gov/cew/classifications/industry/2017-naics-hierarchy-crosswalk.htm
- BLS OEWS logging (NAICS 113300/113000): https://www.bls.gov/oes/2018/May/naics4_113300.htm
- Census CBP methodology: https://www.census.gov/programs-surveys/cbp/technical-documentation/methodology.html
- Census CBP FAQ (release lag): https://www.census.gov/programs-surveys/cbp/about/faqs.html
- Census CBP API variables (2022): https://api.census.gov/data/2022/cbp/variables.html ; EMP: https://api.census.gov/data/2022/cbp/variables/EMP.html ; EMPSZES: https://api.census.gov/data/2022/cbp/variables/EMPSZES_LABEL.html ; group CB2300CBP: https://api.census.gov/data/2023/cbp/groups/CB2300CBP.html
- Census CBP 2017/2018 disclosure notes: https://www.census.gov/data/datasets/2017/econ/cbp/2017-cbp.html ; https://www.census.gov/data/datasets/2018/econ/cbp/2018-cbp.html
- Census SUSB about + datasets: https://www.census.gov/programs-surveys/susb/about.html ; https://www.census.gov/data/datasets/2021/econ/susb/2021-susb.html
- Census Nonemployer Statistics API: https://www.census.gov/data/developers/data-sets/nonemp-api.html
- Census 2017 NAICS restatement: https://www.census.gov/programs-surveys/sas/2017-naics-restatement.html
- BEA Regional API docs: https://apps.bea.gov/API/docs/ ; signup: https://apps.bea.gov/API/signup/
- USDA FS NRUM/TPO: https://research.fs.usda.gov/programs/nrum ; FIADB-API/EVALIDator: https://apps.fs.usda.gov/fiadb-api
- SBA size standards rule (NAICS 113310, 500-employee): https://www.govinfo.gov/link/fr/77/55757

**Secondary:** IBISWorld Logging in the US (NAICS 11331) — employment/business-size figures, Dec 2025 (https://www.ibisworld.com/united-states/employment/logging/78 ; https://www.ibisworld.com/classifications/naics/113310/logging/); Indiana Business Research Center on the QCEW/CBP "80/3" suppression rule (https://incontext.indiana.edu/2008/july-august/2.asp); state LMI size tools (Maryland https://labor.maryland.gov/lmi/emppay/ ; Pennsylvania https://workstats.dli.pa.gov/Products/EmploymentBySize); FRED mirrors of BEA regional series (e.g., N4206C0A173NBEA).

## 16. Unresolved Questions and Evidence Gaps

1. **Exact CBP state × 6-digit × size EMP behavior for logging** could not be executed (API key required; my un-keyed call returned "Missing Key"). Documentation confirms EMP *is* tabulated by size at the state level, but the realized suppression/noise pattern for 113310 in small states must be checked with a keyed pull — this determines how much of the size layer is direct vs modeled. **Resolves via:** keyed call to `.../2022/cbp?get=EMP,EMP_F,ESTAB&for=state:*&NAICS2017=113310&EMPSZES=*`.
2. **QCEW national 6-digit private employment benchmark disclosure**: is the national 113310 private monthly cell always disclosed (so R[t] is well-defined)? If sometimes suppressed, the reconciliation falls back to regional/soft benchmarks. **Resolves via:** inspecting the national industry slice `disclosure_code`.
3. **State 6-digit agglvl code** (58 assumed) and whether all states publish agglvl-58 logging — confirm against a live area slice. **Resolves via:** area slice for a state FIPS.
4. **BEA state industry granularity**: whether any state SAEMP tables expose 113 alone vs only 113–115. **Resolves via:** BEA `GetParameterValues` for SAEMP25N LineCodes.
5. **CBP NAICS predicate name** for the 2022-vintage file (NAICS2017 vs NAICS2022) — the 2022 CBP uses NAICS2017 codes per the variable metadata; confirm for the exact reference year used.
6. **Firm-vs-establishment wedge magnitude** for logging (how often multi-establishment firms occur) — needed to justify treating establishment-size ≈ firm-size (plausible given ~1.8 employees/business). **Resolves via:** SUSB firm-vs-establishment counts at 113310.
7. **Time-span decision** (NAICS-era only vs extend into SIC 241 pre-2001) — default is NAICS-era; extending requires an SIC→NAICS bridge model.
8. **Default overrides:** the user should confirm ownership universe (private vs total covered), size dimension (establishment vs firm), and concept (UI wage&salary vs proprietor-inclusive) before production.

---

### Source-access verification status (summary)
- **VERIFIED (opened/inspected):** QCEW size-data page; QCEW quarterly NAICS layout (fields incl. month1/2/3, disclosure_code); QCEW ownership-code and aggregation-level pages; CBP API variable/group metadata (EMP, EMPSZES, CB2300CBP) and the "Missing Key" behavior of an un-keyed CBP call; CBP 2017/2018 disclosure notes; SUSB about/datasets; Nonemployer API landing; NAICS 113310 definition and cross-vintage stability (via QCEW crosswalk + Census 2017 restatement, confirmed by subagent); FIADB-API landing.
- **DOCUMENTED (official docs, not executed live):** QCEW open-data CSV slice URLs (data.bls.gov fetch blocked by robots); CBP keyed data pull; BEA Regional API request; USDA TPO/NRUM interactive tools; state LMI size tools.
- **UNVERIFIED (leads):** exact agglvl-58 coverage per state for logging; BEA per-state 113-vs-113–115 line availability; state timber severance-tax / harvest-permit monthly feeds.