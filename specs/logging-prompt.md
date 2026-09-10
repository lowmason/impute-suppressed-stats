You are an expert researcher in U.S. labor statistics, establishment data,
forestry economics, small-area estimation, and Bayesian data integration.

RESEARCH OBJECTIVE

Research and propose a reproducible method for estimating monthly U.S. state
employment in Logging, total and by establishment employment-size class.

The industry code supplied for this assignment is "1113310." First verify the
intended code and classification. It is likely NAICS 113310, Logging, but do
not silently correct it. Report:

1. The valid NAICS code and title.
2. The applicable NAICS vintage or vintages.
3. Whether any historical code changes or crosswalks affect the requested
   time period.
4. The employment concept being estimated, such as QCEW-covered
   wage-and-salary jobs, all payroll employment, persons employed, or jobs
   including proprietors.

Do not assume that a single direct source exists. The likely problem is that:

- state-by-month logging employment may be suppressed in some states;
- establishment-size-class employment may not be published at the required
  state, month, and six-digit industry intersection;
- annual or March-reference-period size distributions may exist, but not
  monthly size-class employment;
- national, regional, annual, quarterly, or higher-industry totals may provide
  valid constraints;
- sources may measure different universes, reference periods, statistical
  units, and ownership categories.

Treat the task as a data-identification and data-integration problem, not merely
a search for one table.

TARGET OUTPUT

The desired latent quantity is:

    E[state, month, establishment_size_class]

with:

    E[state, month, total] =
        sum over establishment_size_class E[state, month, size_class]

and, where a compatible national benchmark exists:

    sum over states E[state, month, total] =
        national logging employment for that month.

Clarify whether "size class" means establishment employment size, firm
employment size, enterprise size, or another definition. Prefer establishment
employment size unless the evidence or assignment specifies otherwise. Do not
treat firm-size and establishment-size classifications as interchangeable.

Use official government sources wherever possible. Clearly distinguish direct
measurements, accounting constraints, structural proxies, and modeling
assumptions.

PART A: DIRECT-SOURCE INVENTORY

Search for all potentially relevant sources, including at minimum:

1. Bureau of Labor Statistics Quarterly Census of Employment and Wages
   (QCEW), particularly:
   - quarterly files containing the three monthly employment observations;
   - annual files;
   - state, national, ownership, and six-digit NAICS aggregation levels;
   - establishment counts;
   - disclosure codes;
   - size-class products, if any;
   - preliminary versus final vintages;
   - documentation of suppression, zero-filled fields, revisions, and
     classification changes.

2. Census Bureau County Business Patterns (CBP), including:
   - state-by-six-digit-industry employment and establishments;
   - employment-size-class tables;
   - March reference-period employment;
   - suppression flags, employment noise ranges, and other uncertainty fields;
   - whether size-class counts are actually available at the simultaneous
     state-by-six-digit-industry level.

3. Census Bureau Statistics of U.S. Businesses (SUSB), including:
   - establishment-size and firm-size distributions;
   - state and detailed-industry availability;
   - employment, establishments, payroll, and receipts;
   - differences between firm size and establishment size.

4. Census Bureau Business Dynamics Statistics or related longitudinal business
   data, if useful for establishment births, deaths, expansions, contractions,
   or size-class transitions.

5. Bureau of Labor Statistics Current Employment Statistics, Occupational
   Employment and Wage Statistics, or other BLS products, but only where their
   geography, industry detail, universe, and sampling properties make them
   informative.

6. USDA Forest Service sources:
   - Timber Products Output or National Resource Use Monitoring;
   - Forest Inventory and Analysis and EVALIDator;
   - harvest removals, roundwood output, timberland, logging residue,
     retained production, mill activity, and interstate wood movements.

7. Census Nonemployer Statistics, if the target might include proprietors or
   nonemployer logging contractors.

8. Bureau of Economic Analysis sources:
   - state employment;
   - wage-and-salary employment;
   - proprietors' employment;
   - compensation, earnings, or GDP for the closest available forestry and
     logging industry.

9. Other official state or federal administrative sources, such as:
   - state unemployment-insurance publications;
   - state labor-market-information QCEW tools;
   - workers' compensation records;
   - logging permits, timber severance taxes, harvest reports, timber-sale
     records, or occupational licensing;
   - federal and state timber-sale, harvest, and land-management data.

For every source, report:

- agency and dataset;
- exact URL, API endpoint, downloadable file, or table identifier;
- years and update frequency;
- reference period;
- geography;
- industry detail;
- ownership coverage;
- employment concept;
- statistical unit;
- establishment-size or firm-size definition;
- suppression, noise infusion, or disclosure treatment;
- whether establishment counts remain available when employment is suppressed;
- preliminary/final or revision status;
- strengths and limitations for this exact problem.

Do not state that a variable or cross-tabulation exists merely because adjoining
dimensions exist separately. Verify its simultaneous dimensionality by
examining the API predicates, data dictionary, table layout, or an actual
download.

PART B: SOURCE-COMPATIBILITY MATRIX

Construct a source-compatibility matrix comparing each source with the target
along these dimensions:

- monthly versus quarterly, annual average, or March snapshot;
- state versus regional or national;
- six-digit logging versus broader forestry industry;
- establishments versus firms versus enterprises;
- wage-and-salary jobs versus persons versus proprietors;
- private ownership versus total ownership;
- establishment-size versus firm-size classification;
- direct observation versus proxy;
- exact value versus suppressed, bounded, sampled, or noise-infused value.

Explain which source differences can be modeled and which make direct
substitution invalid.

PART C: IDENTIFICATION AND PUBLIC CONSTRAINTS

Before proposing an imputation model, identify all valid public accounting
constraints.

For each month and year, determine whether the following are available and
definitionally compatible:

- national logging employment;
- disclosed state logging employment;
- state establishment counts;
- broader-industry state totals;
- regional totals;
- ownership totals;
- quarterly or annual benchmarks;
- establishment-size-class establishment counts;
- size-class employment totals at a broader geographic or industry level.

Use only compatible data from a coherent release vintage unless revisions are
modeled explicitly.

For suppressed cells:

1. Do not interpret a published zero as a true zero without checking the
   disclosure code.
2. Separate:
   - exactly observed cells;
   - suppressed but deterministically bounded cells;
   - cells estimable only through a statistical model.
3. If compatible parent and child margins exist, formulate the public
   accounting system and derive sharp lower and upper bounds using linear
   programming or mixed-integer linear programming.
4. Treat employment and establishment counts as nonnegative integers where
   appropriate.
5. Represent rounded totals as intervals rather than exact equations.
6. Do not treat temporal smoothness or historical growth as an accounting
   identity.

Explicitly distinguish:

- an identified or feasible interval derived from public information;
- a posterior interval that depends on a statistical model.

PART D: PROXY ASSESSMENT

Rank candidate proxies separately for:

A. State total logging employment.
B. State establishment-size composition.
C. Monthly movement and seasonality.
D. Proprietor or nonemployer activity, if relevant.

At minimum, evaluate:

- QCEW establishment counts;
- lagged or adjacent-month disclosed QCEW employment;
- CBP employment and employment per establishment;
- CBP establishment counts by employment-size class, if verified;
- SUSB establishment-size or firm-size structure;
- TPO harvest-origin roundwood production;
- FIA harvest-removals volume and its sampling error;
- private or commercially available timberland;
- timber sales and harvest permits;
- logging residue;
- active primary mills;
- downstream wood-products demand;
- payroll, wages, receipts, or compensation;
- broader forestry-and-logging employment;
- nonemployer establishment counts and receipts;
- weather, wildfire, snow, road restrictions, and other seasonal operating
  conditions, if demonstrably useful.

For each proxy, explain:

- the economic mechanism connecting it to logging labor demand;
- expected direction of association;
- temporal and geographic resolution;
- lag structure;
- measurement error;
- likely bias;
- whether it predicts employment levels, employees per establishment,
  establishment counts, or size-class shares;
- whether it belongs in the main model, a measurement model, a prior, or a
  sensitivity analysis.

Avoid double-counting correlated proxies. For example, if TPO and FIA both
measure harvest activity, consider a latent harvest-activity factor rather
than treating them as independent signals. Distinguish harvest-origin
production from mill-location receipts because interstate log movements can
misallocate logging activity.

PART E: BAYESIAN MODEL

Propose a hierarchical Bayesian model that estimates monthly state employment
both in total and by establishment-size class.

Use a coherent decomposition such as:

    E[s,t,k] = A[s,t] * p[s,t,k] * r[s,t,k]

where:

- s indexes state;
- t indexes month;
- k indexes establishment employment-size class;
- A[s,t] is the number of logging establishments;
- p[s,t,k] is the share of establishments in size class k;
- r[s,t,k] is expected employment per establishment in class k.

Modify this decomposition if the available data support a better formulation.

The model should include the following components.

1. STATE TOTALS

Model employees per establishment or state employment intensity using:

- state and regional random effects;
- month or seasonal effects;
- year effects;
- state-specific temporal dynamics;
- harvest activity;
- broader-industry conditions;
- establishment counts;
- robust innovations or change points for openings, closures, recoding,
  relocations, disasters, and major market changes.

For example:

    log r[s,t] =
        alpha
        + state_effect[s]
        + region_effect[region[s]]
        + month_effect[month[t]]
        + year_effect[year[t]]
        + beta' X[s,t]
        + dynamic_error[s,t]

Consider an AR(1), random-walk, dynamic-factor, or change-point-aware process.
Justify the choice.

2. ESTABLISHMENT-SIZE SHARES

Model p[s,t,k] as a compositional vector whose elements are nonnegative and sum
to one. Consider a hierarchical logistic-normal or Dirichlet-based model.

Use observed CBP or SUSB size distributions as noisy, annual, or March-centered
measurements of the latent size structure rather than automatically treating
them as monthly truth.

Allow partial pooling by:

- state;
- region;
- year;
- forest type or logging system;
- historical state size structure;
- national logging size distribution.

If only annual size-class information exists, model monthly size shares as a
smooth latent process around an annual structural distribution, while allowing
seasonal size-class differences if supported by data.

3. SIZE-CLASS SUPPORT AND BOUNDS

Respect the mathematical support of each employment-size class. If a class
contains establishments with 1-4 employees, for example, employment attributed
to that class must be consistent with its establishment count and class
endpoints.

If size-class establishment counts C[s,t,k] are observed:

    lower_k * C[s,t,k] <= E[s,t,k] <= upper_k * C[s,t,k].

Handle open-ended top classes through a justified probabilistic tail model or
externally supported cap. Do not call an arbitrary cap a strict public bound.

If size classes are observed only annually or for a March reference period,
treat these bounds as reference-period information, not as exact restrictions
on every month.

4. MEASUREMENT MODELS

Specify separate observation equations for sources with different concepts.
Examples include:

- QCEW monthly employment as a direct observation when disclosed;
- CBP employment as a March-reference-period observation;
- SUSB size structure as an annual structural observation;
- TPO and FIA as noisy measurements of latent harvest activity;
- broader-industry BEA employment as an indirect regularizer;
- weather or harvest-permit measures as monthly activity indicators.

Carry published sampling errors, noise ranges, or interval information into
the likelihood where possible.

5. EXACT RECONCILIATION

Preserve disclosed QCEW state values.

For each month, define:

    R[t] =
        NationalEmployment[t]
        - sum of disclosed compatible state employment[t].

Allocate R[t] only across states requiring imputation.

Prefer a parameterization that satisfies the national adding-up constraint in
every posterior draw, such as normalized positive weights:

    w[s,t] = positive latent employment weight

    E[s,t] =
        R[t] * w[s,t] / sum_over_suppressed_states w[s,t].

Extend this reconciliation to size classes where compatible national or state
size-class margins exist. Avoid relying solely on a very tight artificial
likelihood penalty if exact reparameterization is feasible.

If the national benchmark is unavailable or incompatible, explain what weaker
constraints can be enforced.

6. SUPPRESSION MECHANISM

Recognize that official suppression is not missing completely at random.
Discuss why suppressed cells may differ systematically in establishment
concentration, cell size, volatility, or industry structure.

Because the exact disclosure rule may not be public, do not claim to estimate a
fully identified selection model. Instead propose sensitivity analyses, such
as:

- suppressed cells having different residual variance;
- heavier-tailed employment-per-establishment priors;
- different expected state shares;
- alternative concentration-risk scenarios;
- primary-like versus complementary-like pseudo-suppression patterns.

7. UNCERTAINTY AND OUTPUT

Produce joint posterior draws, not only marginal point estimates.

For each state-month-size-class observation, retain:

- posterior mean or median;
- 50%, 80%, 90%, and 95% credible intervals;
- observed versus imputed status;
- direct-source flags;
- deterministic feasible lower and upper bounds, when available;
- posterior probability of economically meaningful thresholds;
- source vintage and classification metadata.

Ensure that rounding posterior means to integers does not destroy total
constraints. Describe an integerization or balanced-rounding procedure, or
retain posterior draws as continuous expected job counts if appropriate.

PART F: ALTERNATIVE MODELS AND BASELINES

Compare the proposed Bayesian model with at least:

- establishment-count proportional allocation;
- equal allocation of the residual;
- last observed state share;
- same-month previous-year share;
- rolling or exponentially weighted historical shares;
- CBP employment-per-establishment allocation;
- harvest-volume proportional allocation;
- constrained regression followed by reconciliation;
- a Bayesian model without forestry proxies;
- a Bayesian model without temporal smoothing.

Explain which baseline is likely to be most credible if the full model cannot
be supported by available data.

PART G: VALIDATION

Design pseudo-suppression validation using disclosed state-month cells.

Do not rely only on random masking. Include:

- masking patterns resembling small or concentrated cells;
- clustered suppression across related states or periods;
- whole-group holdouts;
- long runs of missing months;
- rolling-origin forecasts;
- retrospective smoothing evaluated separately from real-time estimation;
- structural-break periods;
- NAICS revision periods;
- preliminary-versus-final vintage comparisons.

Evaluate:

- MAE and RMSE;
- WAPE and median absolute percentage error where meaningful;
- state-share error;
- size-class-share error;
- interval coverage and interval width;
- proper probabilistic scores;
- national, state, temporal, and size-class constraint violations;
- calibration by state size and suppression duration;
- sensitivity to priors and proxy inclusion.

Require the sophisticated model to outperform transparent baselines. If it
does not, recommend the simpler method.

PART H: PRIVACY AND DISCLOSURE REVIEW

The purpose is aggregate economic analysis, not identifying individual
businesses.

Flag situations where:

- public constraints exactly reconstruct an officially suppressed cell;
- deterministic bounds become unusually narrow;
- a result could be combined with public employer information to infer a
  dominant establishment;
- posterior precision is driven mostly by strong assumptions;
- a coarser geography, time period, or size grouping would answer the research
  question adequately.

Recommend aggregation, interval widening, restricted access, or nonpublication
where appropriate. Do not present a model estimate as an officially published
value.

DELIVERABLE FORMAT

Return the research in this order:

1. Executive summary.
2. Verified NAICS code, target population, and statistical unit.
3. Direct-source findings.
4. Source-compatibility matrix.
5. Data gaps and suppression patterns.
6. Ranked proxy inventory.
7. Deterministic identification and feasible-bound strategy.
8. Recommended Bayesian model, with equations and clearly stated priors.
9. Exact reconciliation strategy.
10. Alternative models and baselines.
11. Validation and sensitivity plan.
12. Privacy and disclosure-risk assessment.
13. Recommended production data pipeline.
14. Machine-readable source inventory.
15. Bibliography with working links and access dates.
16. Unresolved questions and evidence gaps.

For the machine-readable source inventory, provide one record per source with:

    agency
    dataset
    table_or_endpoint
    url
    access_date
    years_available
    release_frequency
    reference_period
    geography
    industry_detail
    ownership
    statistical_unit
    employment_concept
    size_dimension
    suppression_or_noise
    revision_status
    proposed_model_role
    important_limitations

RESEARCH STANDARDS

- Prefer primary agency documentation and actual data files over summaries.
- Cite every factual claim with a direct source.
- Record the publication or update date and access date.
- Test API endpoints or inspect actual tables when possible.
- Separate verified facts from tentative leads.
- Explicitly say when a desired cross-tabulation does not exist or could not
  be verified.
- Do not invent data, endpoints, size classes, suppression rules, or source
  availability.
- Do not assume that similarly named variables have compatible definitions.
- Do not mix preliminary and final data, NAICS vintages, ownership categories,
  or statistical units without an explicit bridge model.
- Label every restriction as one of:
    (a) public accounting fact,
    (b) definitional support restriction,
    (c) empirical measurement,
    (d) modeling assumption,
    (e) sensitivity assumption.
- If agents reach conflicting findings, report the conflict and identify the
  agency documentation or data extract needed to resolve it.
 
SOURCE-ACCESS REQUIREMENT

For every source identified, provide at least one directly usable access method:

1. A stable landing-page URL; and
2. Where available, one of:
   - a complete API request URL,
   - an API endpoint plus all required query parameters,
   - a direct-download URL,
   - a file path and file-naming pattern, or
   - a table identifier with exact navigation instructions.

For APIs, provide:

- base endpoint;
- complete example request for NAICS 113310 and one sample state/year;
- required predicates and parameter definitions;
- expected response format;
- authentication or API-key requirements;
- pagination, rate-limit, and revision notes;
- a short reproducible request example using cURL, Python, or both.

Do not provide a generic agency homepage when a dataset page, API endpoint,
download file, or table URL is available. Verify each access method by opening
the URL or executing the request when tools permit. Mark each item as:

- VERIFIED: opened or executed successfully;
- DOCUMENTED: supported by official documentation but not executed;
- UNVERIFIED: plausible lead requiring follow-up.

If no public API exists, state that explicitly and provide the best available
download or manual-access procedure.