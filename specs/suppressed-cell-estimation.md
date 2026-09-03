# Estimating Suppressed Cells in Hierarchical and Longitudinal Public Statistics: A QCEW-Centered Literature Review and Methodological Assessment

## Executive summary and the QCEW suppression problem

The central methodological conclusion is that **suppressed-cell analysis should begin as an identification problem, not an imputation problem**. For any suppressed QCEW cell, the first task should be to assemble every valid public accounting constraint from a *single coherent data vintage*, determine the rank and null space of the resulting system, and calculate the cell's minimum and maximum feasible values subject to nonnegativity, integrality where appropriate, and documented rounding. Only after separating exactly recoverable cells from partially identified cells should historical shares, time-series models, Bayesian hierarchies, matrix completion, or other predictive methods be introduced. This is not merely a statistical preference: linear-programming disclosure audits were developed precisely because complementary suppression can fail when other published margins reduce a protected cell to an excessively narrow feasible interval. Federal statistical-disclosure guidance explicitly treats the maximum and minimum feasible values as the relevant protection diagnostic. [[1](#ref-1), [2](#ref-2), [3](#ref-3)]

For QCEW specifically, several common informal descriptions of suppression are too simple. Current BLS documentation says that a disclosure code `N` means the macro cell is suppressed; for 2004-forward files, **the establishment count is nevertheless published, while the other data items in the cell are zero-filled rather than publicly observed**. Location quotients and over-the-year-change fields have their own disclosure codes and become unavailable when required components are unavailable, although establishment-count derivatives can remain available. BLS also states that most suppressed QCEW data are provided by, or substantially attributable to, a single large employer and that additional otherwise-disclosable cells may be withheld to prevent derivation of sensitive information elsewhere. Higher-level totals include suppressed lower-level data. [[4](#ref-4)]

That current description should be distinguished sharply from **historical documentation of the internal rule**. A 2004 BLS research paper described QCEW primary nondisclosure tests involving employment dominance, wage dominance, thresholds for establishments, employment and employers, followed by secondary suppression across ownership-industry, geography, size, and time. The 2005 revision of FCSM Statistical Policy Working Paper 22 stated that, for calendar year 2002 onward, QCEW used a threshold rule plus a p-percent concentration rule, whereas earlier practice used an `(n,k)` concentration rule. It also recommended that agencies *not* reveal the numerical parameters of disclosure rules because doing so can itself improve estimates of suppressed values. Current BLS methodological documentation says details of the confidentiality methods are intentionally not shared so that protection retains its strength. Thus, historical rule descriptions are invaluable for understanding the mechanism but **must not be treated as a statement of the exact 2026 QCEW algorithm or thresholds**. [[1](#ref-1), [3](#ref-3), [5](#ref-5)]

QCEW is especially amenable to constraint-based analysis because most primary published quantities are aggregates of establishment records. BLS describes employment and wage totals for a subdomain as sums of establishments belonging to that domain. Current quarterly files contain establishment counts, three monthly employment levels, quarterly total and taxable wages, unemployment-insurance contributions, and average weekly wages; annual files include annual-average establishments and employment, sums of quarterly wages and contributions, and wage/pay measures derived from employment and wage levels. [[6](#ref-6), [7](#ref-7), [8](#ref-8)]

At the same time, QCEW is **not a clean stationary panel**. BLS explicitly says QCEW is not designed as a time series; establishment records can shift because of births and deaths, mergers and acquisitions, changes from single-unit to multi-establishment reporting, physical relocation, corrections of county or industry codes, and changes in predominant economic activity. Current-year observations are preliminary and subsequently finalized, while corrections can affect the current and previous year. Published news-release growth rates can use adjusted unpublished prior-year levels that differ from the unadjusted public downloadable series. NAICS vintages also change: current BLS documentation identifies different NAICS bases over successive periods, including 2022 NAICS from 2022 forward. [[6](#ref-6), [9](#ref-9), [10](#ref-10)]

Those features make the missingness mechanism important. Suppression is emphatically **not MCAR**. Primary suppression historically depended on confidential respondent composition, concentration and cell magnitude; complementary suppression depends on the surrounding table and other suppressed cells. In contemporary terminology, the public-data mechanism is best regarded as a mixture of **nonignorable/MNAR selection, deterministic disclosure-control censoring, and globally design-induced missingness**. The public suppression flag itself therefore carries information, but not enough to reverse-engineer BLS's confidential thresholds: an `N`, its published establishment count, the hierarchy around it, and the persistence of suppression over time can all be predictive, yet the public cannot reliably infer which `N` is primary versus complementary or what numerical confidentiality rule caused it. [[4](#ref-4), [1](#ref-1), [3](#ref-3)]

The strongest practical approach is consequently a **hybrid identified-set / probabilistic workflow**:

> public accounting identities → sparse rank analysis → deterministic LP/MILP bounds → suppression-aware predictive model inside those bounds → reconciliation to all valid margins → posterior draws or multiple imputations → rolling-origin backtests → sensitivity analysis → disclosure-risk review.

The deterministic interval is a statement about what the public constraints logically imply. A posterior or imputation distribution inside that interval is a statement about additional modeling assumptions. They should never be conflated.

A second major conclusion concerns confidentiality. Multiple independently legitimate releases can collectively disclose substantially more information than any individual release. FCSM guidance has long required consideration of publicly available auxiliary information, while modern composition-attack research formalizes this phenomenon. Census Bureau reconstruction research dramatically demonstrated that a relatively small collection of aggregate tables could, in a different statistical system, enable extensive reconstruction. A 2025 QCEW-specific research paper likewise identifies composition across BLS and state releases as a motivation for formal privacy methods for establishment data. [[3](#ref-3), [11](#ref-11), [12](#ref-12), [13](#ref-13)]

For legitimate research, therefore, **better statistical accuracy is not always a reason to publish the resulting cell estimate**. When public constraints exactly reconstruct an `N`-flagged QCEW value, or reduce it to a range narrow enough that a dominant establishment could plausibly be inferred using external knowledge, the defensible output is generally the disclosure-risk finding itself, a coarser aggregate, or a deliberately wider analytic interval—not the reconstructed sensitive number. BLS's confidentiality pledge and applicable federal statutes require the agency to prevent identifiable disclosure, and FCSM explicitly recognizes inferential as well as direct disclosure. [[14](#ref-14), [3](#ref-3)]

## Identification framework and recoverability

**The basic linear system.** Let $z\in\mathbb R^m$ denote the vector of the finest mutually exclusive cells relevant to a set of releases—for example, county × six-digit NAICS × ownership × quarter for one additive measure. Every valid published total is a linear functional of those atomic cells,

```math
y = A z,
```

where rows of $A$ describe parent totals, ownership totals, industry rollups, state/county totals, annual sums, or other published aggregations. QCEW's current aggregation-level documentation contains national, state, county, metropolitan, ownership, supersector and multiple NAICS detail levels, so the actual public constraint graph is substantially richer than a single parent-child tree. Historical BLS disclosure research likewise emphasized simultaneous ownership-industry, area, size, and time relationships. [[15](#ref-15), [1](#ref-1)]

Partition $z=(z_O,x)$, where $z_O$ is observed and $x\in\mathbb R^s$ contains suppressed atomic quantities. Moving observed contributions to the right-hand side produces

```math
B x=c.
```

For exactly reported additive margins, define

```math
\mathcal F_0=\{x:B x=c\}.
```

The affine dimension before inequalities is

```math
\dim(\mathcal F_0)=s-\operatorname{rank}(B),
```

assuming consistency. Equivalently, if $N$ spans the null space of $B$, every solution is

```math
x=x_0+Nv.
```

The coordinates of $v$ are precisely the directions in which suppressed cells can change without changing any of the public accounting identities. This rank/null-space formulation converts the intuitive question “can I subtract enough totals?” into a formal identification test.

If $\operatorname{rank}(B)=s$, the continuous system has at most one solution. Rank deficiency does **not** automatically imply nonidentification, however, because nonnegativity, bounds and integrality can eliminate all but one feasible point. Conversely, two suppressed values in every displayed row do **not** guarantee safety: FCSM Working Paper 22 specifically warns that merely having two suppressed cells per row, column or layer is insufficient because the entire multidimensional equation system can still determine a cell. [[3](#ref-3)]

**Partial identification.** Add defensible public restrictions,

```math
x\ge0,\qquad Gx\le h,
```

and, for genuine counts,

```math
x_j\in\mathbb Z.
```

Then the identified set becomes

```math
\mathcal F=
\{x:B x=c,\;Gx\le h,\;x\ge0,\;x_{\mathcal I}\in\mathbb Z\}.
```

For each suppressed coordinate $j$,

```math
L_j=\min_{x\in\mathcal F}x_j,\qquad
U_j=\max_{x\in\mathcal F}x_j.
```

With continuous variables these are linear programs; with integer constraints they are mixed-integer linear programs. The interval $[L_j,U_j]$ is not a confidence interval. It is the **sharp feasible range given the stated public information and constraints**. BLS's 2004 Disclosure Audit System used essentially this min/max logic, and FCSM describes suppression auditing in exactly these terms: equal minima and maxima imply exact disclosure; excessively close extrema imply insufficient protection. [[1](#ref-1), [3](#ref-3)]

This leads to a useful five-way classification:

| Status | Formal criterion | What may properly be reported |
|---|---|---|
| **Exactly recoverable** | $L_j=U_j$ | “Public identities imply $x_j=L_j$,” subject to disclosure review |
| **Partially identified** | $L_j\lt U_j\lt\infty$ | The feasible range, preferably before any point estimate |
| **Model-estimable** | Wide $[L_j,U_j]$, but predictive structure exists | Point/posterior estimate explicitly labeled model-based |
| **Assumption-sensitive** | Estimate changes materially across plausible models | Scenario ranges, model ensemble, or multiple imputations |
| **Fundamentally unidentified** | Public constraints and defensible models provide little concentration | No cell estimate; aggregate or use restricted data |

A useful discipline is to keep **identified-set width**

```math
W_j=U_j-L_j
```

separate from **posterior or predictive uncertainty**. A model cannot turn an unidentified value into a logically identified fact; it can only assign probabilities within an identified region under assumptions.

**Counts, wages and derived quantities require different constraint types.** QCEW establishment counts and monthly employment levels are nonnegative counts and naturally support integrality constraints. Wage and contribution totals are nonnegative magnitude variables. Their aggregates are additive across mutually exclusive categories, provided geography, industry, ownership, period and classification definitions align. Current annual QCEW files explicitly define total annual wages and contributions as sums of quarterly values and annual-average employment from the monthly levels. [[7](#ref-7), [8](#ref-8)]

Average weekly wages, annual average pay, location quotients and percentage changes are different: they are **derived, generally nonadditive statistics**. They can sometimes provide nonlinear or interval constraints on additive primitives, but should not be inserted into the same additive matrix as if they were totals. QCEW's annual documentation explicitly describes average weekly wage and average annual pay as being based on employment and wage levels, while the quarterly documentation identifies location quotients and over-year percentage changes as rounded derived fields. [[7](#ref-7), [8](#ref-8)]

Moreover, current suppression practice substantially limits the usefulness of these cross-measure relations for a suppressed macro cell: since employment and wage-related fields are suppressed together while the establishment count remains disclosed, a user generally does not receive an independent precise average-wage observation that can simply be inverted to recover suppressed wages. Derived LQ/OTY fields also become unavailable where required components are unavailable. [[4](#ref-4)]

**Rounding should be represented explicitly.** If an underlying aggregate $a_i^\top x$ is published after rounding to grid width $r_i$, the correct constraint is approximately

```math
\tilde y_i-r_i/2
\le
a_i^\top x
<
\tilde y_i+r_i/2,
```

with endpoint details determined by the documented rounding convention. Treating a rounded statistic as exact can create false recoverability. Conversely, several independently rounded overlapping margins can have intervals whose intersection is substantially narrower than any individual interval. Historical BLS disclosure-audit work explicitly incorporated rounding bounds around published values. Current QCEW file documentation expressly labels location quotients as rounded to hundredths and percentage changes to tenths; analysts should therefore model documented rounding **field by field rather than assuming a universal QCEW rounding rule**. [[1](#ref-1), [7](#ref-7), [8](#ref-8)]

**Time creates equations only when genuine accounting identities exist.** An annual wage total equal to the sum of its four quarters is a real identity. “Employment next quarter should be close to employment this quarter” is not. Previous and next observations, seasonal similarity, peer-industry growth and bounded growth rates become constraints only after introducing statistical assumptions. Maintaining that separation is crucial because BLS warns that QCEW longitudinal breaks can arise from births/deaths, relocation, mergers, recoding, reporting-basis changes and other administrative changes. [[6](#ref-6)]

The historical BLS disclosure paper already recognized time as part of the suppression problem: quarterly versus annual files and preliminary versus revised releases can create additional differencing relationships. The modern implication is broader: a constraint engine should simultaneously understand period aggregation **and data vintage**. [[1](#ref-1)]

**Never mix incompatible vintages silently.** Let

```math
B^{(v)}x^{(v)}=c^{(v)}
```

denote constraints from release vintage $v$. If a later revision changes establishments, classification, employment or wages, $x^{(v)}$ and $x^{(v+1)}$ are not necessarily the same latent vector. Stacking the equations as though they were can yield a unique but fictitious solution—or an empty feasible set. BLS's current methodology permits revisions and explicitly notes that adjusted news-release growth rates can be based on unpublished previous-year data not equal to the public download. [[6](#ref-6)]

When incompatibility is unavoidable, use a slack formulation,

```math
\min_{x,e}\sum_i w_i|e_i|
\quad
\text{s.t.}\quad
B_i x=c_i+e_i,
```

and interpret $e_i$ as revision/rounding inconsistency rather than estimation noise. Better still, retain separate vintage-specific latent quantities and model the revision process.

**Hierarchy construction is a graph problem, not merely a tree problem.** NAICS itself is hierarchical, but geography and ownership create cross-cutting partitions, while quarterly/annual releases add a temporal layer. The resulting incidence matrix is sparse and usually decomposes into connected components. Sparse QR/SVD or exact-rank methods can diagnose redundant versus independent equations before optimization. For simple tree aggregations with integer right-hand sides, linear structure can sometimes yield integral solutions without explicit MILP; once overlapping classifications and extra bounds enter, that property should not be assumed.

For large QCEW panels, the efficient architecture is therefore: construct atomic keys; build a sparse constraint matrix; decompose its bipartite constraint/cell graph; perform rank analysis by component; run LP bounds on continuous magnitudes; invoke MILP only where count integrality could materially change the answer; and cache reusable hierarchy matrices across periods. This directly generalizes the LP-audit approach documented by BLS and FCSM while separating disclosure auditing from subsequent predictive estimation. [[1](#ref-1), [3](#ref-3)]

## Literature review and methodological taxonomy

The literature naturally divides into two bodies that are often mistakenly blended. **Disclosure-control literature asks how to prevent a suppressed value from being learned too accurately. Estimation literature asks how to predict an unobserved value as accurately as possible.** Linear-programming bounds belong to both: an agency can use them to audit whether protection is adequate, while an outside researcher can use exactly the same mathematics to determine what is publicly identified. FCSM and BLS documents make this duality unusually explicit. [[2](#ref-2), [3](#ref-3), [1](#ref-1)]

**Annotated core literature**

| Source | Literature role | Relevance to suppressed-cell estimation |
|---|---|---|
| FCSM, *Statistical Policy Working Paper 22*, second version, 2005 | **Protection / federal guidance** | Defines primary/complementary suppression, linear sensitivity rules, LP auditing, CTA, and historical federal-agency practices; explicitly warns that suppression-rule parameters can leak information. [[3](#ref-3), [2](#ref-2)] |
| Powers & Cohen, BLS, 2004 | **Protection / QCEW-specific audit** | Direct QCEW case study of primary and complementary nondisclosure and an LP Disclosure Audit System that obtains tight feasible min/max values. |
| Cox, 1980; later cell-suppression literature | **Protection / optimization** | Established mathematical cell-suppression analysis and the need to consider systems of marginal equations; foundational to later LP and network-based suppression algorithms. FCSM reviews this development. [[2](#ref-2), [3](#ref-3)] |
| Cox, 2009, “Vulnerability of Complementary Cell Suppression to Intruder Attack” | **Protection / adversarial analysis** | Explicitly studies how complementary suppression can be vulnerable to inference; especially germane when many related tables or public releases exist. |
| Webb et al., 2025, arXiv:2509.01597 | **Protection / QCEW / formal privacy** | Proposes establishment-oriented formal privacy motivated by QCEW; emphasizes skewed business data, uncertainty semantics and composition across releases. |
| Abowd et al., 2017, arXiv:1701.00752 | **Protection / reconstruction theory** | Explains why many individually accurate aggregate releases can cumulatively compromise privacy—the “Fundamental Law of Information Recovery.” |
| Abowd et al., 2023, arXiv:2312.11283 | **Protection / empirical reconstruction** | Demonstrates large-scale reconstruction from published 2010 Census tables, showing why cross-release composition must be part of the threat model. |
| Abowd et al., 2022, arXiv:2204.08986 | **Protection + constrained postprocessing** | Describes the 2020 Census TopDown system: noisy hierarchical measurements followed by constrained postprocessing, useful as a contrast to suppression-based releases. |
| Ganta, Kasiviswanathan & Smith, 2008, arXiv:0803.0032 | **Protection / composition** | Shows how overlapping independently protected releases plus auxiliary information can undermine privacy methods lacking composition guarantees. |
| Pannekoek, Shlomo & de Waal, 2014, arXiv:1401.1663 | **Estimation / constrained imputation** | Develops calibrated numerical imputation under linear edits and known totals, directly relevant to generating plausible suppressed values while respecting margins. |
| Denton, 1971; Dagum & Cholette, 2006 | **Estimation / benchmarking** | Foundation for adjusting high-frequency series to lower-frequency benchmark totals while minimizing disruption to movements. |
| Fay & Herriot, 1979; Molina, Nandram & Rao, 2014 | **Estimation / small area** | Foundation for borrowing strength across related areas; hierarchical Bayes extensions demonstrate posterior small-area inference. |
| Steorts, 2014; Steorts & Ghosh, 2013 | **Estimation / constrained SAE** | Combines smoothing or small-area estimation with explicit benchmarking constraints and studies error from benchmarking. |
| Girolimetto & Di Fonzo, 2023, arXiv:2305.05330 | **Estimation / reconciliation** | Treats point and probabilistic forecast reconciliation under general linear constraints, a direct mathematical analogue of coherent hierarchical cell estimation. |
| Sugasawa, Kobayashi & Kawakubo, 2024, arXiv:2407.17848 | **Estimation / Bayesian benchmarking** | Uses entropic tilting to obtain benchmark-consistent posterior distributions rather than only benchmarked point estimates. |
| Okonek & Wakefield, 2022, arXiv:2203.12195 | **Estimation / Bayesian benchmarking** | Develops computational approaches for conditioning posterior draws on official-statistics benchmark constraints. |
| Yang & Reiter, 2024, arXiv:2406.04599; Akande & Reiter, 2020, arXiv:2011.05482 | **Estimation / MNAR multiple imputation** | Show how auxiliary known margins can inform multiple imputation under explicitly nonignorable missingness. |
| Capponi & Stojnic, 2024, arXiv:2401.00578 | **Estimation / MNAR matrix completion** | Studies low-rank completion with structured, nonrandomly missing blocks—more relevant to suppression than standard random-missing matrix theory. |
| Elliot & Domingo-Ferrer, 2018, arXiv:1812.09204 | **Protection / SDC review** | Places traditional SDC in the modern environment of large-scale linking, computation and proliferating auxiliary data. |
| UN privacy-preserving computation handbook, 2023 | **Protection / international guidance** | Broadens the disclosure discussion to formal privacy and privacy-preserving computation; useful for governance even though it is not specifically a cell-imputation manual. [[16](#ref-16)] |

European statistical-disclosure practice is also represented by the ESS/Eurostat-centered literature around τ-ARGUS and by Hundepool et al.'s *Statistical Disclosure Control* (2012), which systematizes tabular and microdata SDC methods. The underlying optimization tradition is closely aligned with the FCSM literature: primary-cell identification, complementary suppression, perturbation/controlled adjustment, and auditing of multidimensional tables. FCSM itself notes that LP-based automatic complementary-suppression and audit systems had long been used at the U.S. Census Bureau and Statistics Canada. [[2](#ref-2), [3](#ref-3)]

The methods relevant to the research objective can be organized as follows.

**Deterministic bounds and linear or mixed-integer programming.** This should be considered the baseline, not one competitor among many. Inputs are public margins, observed components, hierarchy relations, documented rounding, nonnegativity, genuine public bounds and—where relevant—integer count restrictions. No temporal stationarity or cross-area exchangeability is required. Aggregation identities are preserved exactly. LP scales well on sparse systems; adding unrestricted integrality can make optimization much more expensive, although it is often practical when individual connected components are small or LP bounds are already narrow. Its output is a feasible range, not a probability interval. BLS and FCSM provide unusually direct precedent for this methodology. [[1](#ref-1), [3](#ref-3)]

The main analytical danger is exactly the reason agencies use LP audits: a very narrow range can itself represent a disclosure problem. Researchers should therefore calculate bounds internally but subject their *publication* to a disclosure-risk gate.

**Historical-share allocation.** Let a group of jointly suppressed children have public subtotal

```math
S_t=P_t-\sum_{i\in O_t}x_{it}.
```

For child $j$,

```math
\hat x_{jt}=\hat s_{jt}S_t,
\qquad
\sum_{j\in S_t}\hat s_{jt}=1.
```

The share $\hat s_{jt}$ may be the last observed share, same-quarter seasonal share, rolling mean, median, exponentially weighted average, or a robust pre/post-break estimate. Its advantages are transparency, near-zero computational cost, and exact preservation of the jointly suppressed subtotal. It is attractive when cell composition is stable and only short gaps occur.

Its weakness is that the historical sample of visible cells is selected. Suppressed QCEW cells are systematically associated with confidentiality risk, concentration and—historically—cell-size tests, while complementary cells are chosen because of table geometry. A share estimated from periods when a cell was visible is therefore not automatically representative of periods when it was suppressed. Current QCEW documentation and historical disclosure documentation both make that selection issue explicit. [[4](#ref-4), [1](#ref-1)]

A defensible historical-share method should use only classification-consistent periods; prefer same-quarter seasonal comparisons when seasonality is material; downweight old periods; detect breaks; and derive predictive intervals from genuine pseudo-suppression backtests rather than from naïve sampling-error formulas.

**Growth-rate and interpolation models.** A missing value can be forecast from the previous visible value,

```math
\hat x_t=x_{t-1}(1+\hat g_t),
```

interpolated between $t-1$ and $t+1$, or estimated from peer-industry/geographic growth. Modeling log levels or shares often makes multiplicative growth more natural.

These models have low computational cost and excellent interpretability, but QCEW's administrative discontinuities are directly hostile to smooth interpolation. A sudden movement can be a genuine establishment opening, closure or relocation, a recoding event, a reporting-basis change, or a merger rather than sampling noise. BLS specifically documents each of these possibilities. [[6](#ref-6)]

Accordingly, temporal methods should incorporate change-point detection, robust innovations, opening/closing states or time-varying coefficients. Interpolation using $t+1$ is appropriate for retrospective completion but creates future-data leakage in real-time evaluation.

**Benchmarking and reconciliation.** Suppose an initial unconstrained estimate $\hat x$ is available. A general reconciliation estimator is

```math
x^\star
=
\arg\min_x
(x-\hat x)^\top W^{-1}(x-\hat x)
\quad
\text{s.t.}\quad
A x=y,\;x\ge0.
```

Depending on the objective, this encompasses generalized least squares, weighted quadratic adjustment and related constrained estimators. Proportional allocation and iterative proportional fitting are attractive for strictly positive tabular quantities; entropy minimization preserves relative structure; Denton-style benchmarking is especially appropriate when preserving period-to-period movement matters; generalized forecast-reconciliation methods provide covariance-weighted solutions for large systems. Probabilistic reconciliation extends the same principle to distributions rather than only means. [[17](#ref-17), [18](#ref-18), [19](#ref-19)]

Reconciliation is best viewed as an **output coherence layer**, not a substitute for a data-generating model. A poor base model reconciled perfectly remains a poor model. Conversely, separately fitting every cell without reconciliation can produce impossible totals even when each marginal prediction appears plausible.

**Time-series and state-space models.** A natural QCEW formulation is

```math
x_t = F_t x_{t-1}+u_t,
```

```math
y_t=A_t x_t+v_t,
```

where $x_t$ contains latent detailed cells and $y_t$ contains published totals or visible cells. Exact accounting equations can be represented as zero-variance observations or, often more stably, by reparameterizing the latent state so constraints hold identically. Rounded or revised measurements receive nonzero observation error.

The state may include local levels, slopes, quarter-seasonal effects, industry/area factors, opening/closing states and common macroeconomic shocks. Linear-Gaussian models permit Kalman filtering/smoothing; nonnegativity, integer counts, heavy tails and nonlinear wage/employment relations lead toward transformed Gaussian, truncated, particle-filter or Bayesian state-space implementations.

These models offer a principled distinction between *filtering*—what could have been inferred at time $t$—and *smoothing*—what is inferred retrospectively using later quarters. They naturally return uncertainty distributions. Their main weakness is structural-break sensitivity unless break states or robust innovations are explicit.

**Bayesian hierarchical models.** This is the most flexible general framework when the objective is posterior distributions rather than unsupported point estimates. One can model latent child shares by geography, industry and ownership; quarter effects; common industry cycles; spatial effects; and unit-specific random trends while conditioning on exact aggregation identities.

For example, if $S_{gt}$ is a known suppressed subtotal and $p_{jgt}$ latent shares,

```math
x_{jgt}=S_{gt}p_{jgt},
\qquad
p_{jgt}\ge0,\quad
\sum_j p_{jgt}=1,
```

with

```math
\operatorname{logit\!-\!ratio}(p_{jgt})
=
X_{jgt}\beta+
\alpha_j+\gamma_g+\delta_t+\eta_{jgt}.
```

This automatically preserves the subtotal, and posterior draws directly support multiple completed datasets. Spatial, industry and temporal hierarchies borrow strength where a cell has little direct history. Small-area hierarchical Bayes research provides substantial precedent for borrowing strength across sparsely measured domains, while modern Bayesian benchmarking work shows how to condition or tilt posteriors to satisfy aggregate benchmarks. [[20](#ref-20), [19](#ref-19), [21](#ref-21)]

The weaknesses are consequential: priors can dominate cells with little information; computation may become demanding for QCEW-scale panels; and credible intervals can be badly calibrated under misspecification. Suppression should ideally enter the likelihood or selection model rather than being treated as ignorable.

**Small-area and borrowing-strength methods.** Fay-Herriot-style reasoning is applicable even though a suppressed QCEW cell is not literally a conventional noisy direct survey estimate. The transferable idea is hierarchical shrinkage: model a cell's share, growth rate or log level using auxiliary area/industry variables plus random effects, then benchmark the resulting predictions. Small-area methodology is strongest when meaningful auxiliary predictors exist and weaker when the principal feature of a suppressed cell is idiosyncratic dominance by a particular large establishment. [[20](#ref-20), [22](#ref-22), [18](#ref-18)]

Spatial borrowing should therefore be substantively structured. “Nearby counties” are not necessarily economic peers; industry mix, metropolitan labor markets, establishment size, ownership and historical covariation can be more informative than raw geographic proximity.

**Matrix and tensor completion.** Arrange QCEW as a matrix or tensor across geography × industry × ownership × measure × time and posit approximate low rank,

```math
X \approx U_1\otimes U_2\otimes\cdots.
```

The attraction is obvious: a huge repeated panel provides substantial cross-sectional structure, and latent factors can capture common industries or regional cycles. Constraints such as $AX=y$ and $X\ge0$ can be added to nuclear-norm or factorized objectives.

But standard matrix completion is a particularly risky default for QCEW because classical guarantees depend on favorable observation patterns and low-rank/incoherence assumptions, whereas QCEW suppression is strongly structured and nonrandom. Research on MNAR matrix completion confirms that structured missing blocks substantially change the problem. [[23](#ref-23), [24](#ref-24)]

Low rank is also least convincing exactly where confidentiality is often difficult: a locality dominated by one unusual establishment is an outlier, not a generic low-rank combination of regional and industrial factors. Matrix/tensor completion is therefore better used as one ensemble component or as a source of covariates than as an unquestioned standalone estimator.

**Multiple imputation.** Multiple imputation is an output representation rather than a unique prediction model. Generate

```math
x_{\text{mis}}^{(1)},\ldots,x_{\text{mis}}^{(M)}
```

from a suppression-aware predictive distribution, with every draw satisfying deterministic constraints. Downstream analyses are repeated across completed datasets, allowing imputation uncertainty to propagate.

The attractive QCEW version is **constrained MI**: draw latent values from a historical/hierarchical/state-space model, reject or transform draws that violate $\mathcal F$, reconcile every draw to published margins, and preserve separate data-vintage variables. Research on nonignorable survey missingness with known auxiliary margins shows that external totals can materially improve MI while maintaining uncertainty. [[25](#ref-25), [26](#ref-26)]

Drawing uniformly over the deterministic feasible polytope is not “assumption free.” It implicitly places a particular distribution over unidentified values. It can be useful for sensitivity analysis, but should be labeled as such.

**Hybrid methods.** The strongest general solution is a combination:

```math
\boxed{
\text{identified set}
+
\text{suppression-aware predictive model}
+
\text{exact reconciliation}
+
\text{multiple draws}
}
```

For example, derive $[L,U]$ by LP/MILP; fit a hierarchical dynamic model to published cells; truncate/condition its predictions to the feasible set; reconcile to every valid margin; and publish multiple imputations or quantiles rather than one number. This preserves the distinction among logical information, modeling information and residual uncertainty.

## Method comparison and recommended methodology

The table rates methods for the *QCEW suppressed-cell use case*, not in the abstract. “Accuracy potential” is conditional on assumptions and cannot be established from genuinely suppressed values without validation. “Disclosure implication” means the method's capacity to narrow protected cells, not that use of the method is inherently improper.

| Method | Accuracy potential | Interpretability | Data requirements | Ease | Computational cost | Constraint preservation | Uncertainty quantification | Structural-break robustness | Repeated longitudinal use | Disclosure-risk implication |
|---|---|---|---|---|---|---|---|---|---|---|
| **LP/MILP feasible bounds** | Exact for identification, no predictive claim | Very high | Margins + hierarchy | Moderate | Moderate; MILP can be high | **Exact** | Identified ranges, not probabilities | High if same-vintage constraints | Excellent screening tool | **High when bounds become tight** |
| **Historical shares** | Moderate in stable cells | Very high | Modest history | Very easy | Very low | Subtotal exact; other margins need reconciliation | Weak-to-moderate empirical intervals | Low | Good | Moderate |
| **Growth/interpolation** | Moderate; high for smooth cells | High | Temporal neighbors/peers | Easy | Low | Requires reconciliation | Moderate | Low unless change points modeled | Good | Moderate |
| **Proportional/IPF/entropy reconciliation** | Depends on seed estimate | High | Seed + margins | Moderate | Low–moderate | **Excellent** | Limited unless inputs stochastic | Moderate | Excellent as final layer | Moderate–high |
| **Denton/GLS/quadratic reconciliation** | High with good base estimates | High | Base path + benchmarks + weights | Moderate | Moderate | **Exact or near-exact by design** | Can propagate covariance | Moderate–high | Excellent | Moderate–high |
| **State-space model** | High for dynamic cells | Moderate | Longitudinal data + structure | Moderate–hard | Moderate–high | Excellent if encoded | **Strong** | Moderate; high with break states | Excellent | High |
| **Bayesian hierarchical model** | Potentially very high | Moderate | Rich panel + covariates | Hard | High | **Excellent if built into model** | **Excellent** | Moderate–high with robust/change-point priors | Excellent | High |
| **Small-area/shrinkage model** | Moderate–high | High | Peer areas + auxiliaries | Moderate | Moderate | Needs benchmarking | Strong | Moderate | High | Moderate |
| **Matrix/tensor completion** | Variable; high under good latent structure | Low–moderate | Large dense panel | Moderate–hard | High | Must be added explicitly | Often weak without Bayesian extension | Low–moderate | High computational reuse | High if it reconstructs anomalous cells tightly |
| **Multiple imputation** | Depends on imputation model | High conceptually | Model + margins | Moderate | Moderate–high | Excellent if constrained | **Excellent for downstream analysis** | Model-dependent | Excellent | Moderate–high |
| **Hybrid bounds + dynamic hierarchy + MI** | **Highest defensible potential** | Moderate–high | Highest | Hard | High | **Exact** | **Excellent** | High with explicit breaks | **Excellent** | Governable because deterministic and model information remain separable |

The literature supports treating reconciliation, benchmarking and posterior conditioning as complements rather than rivals. Constrained imputation explicitly combines predictive models with linear edits and totals, while modern reconciliation work treats coherent point and probability distributions under general linear restrictions. [[27](#ref-27), [17](#ref-17), [19](#ref-19)]

**Recommended model architecture.** For a serious QCEW production-quality research system, I would use four nested layers.

First, an **identification layer** constructs sparse public accounting constraints and obtains exact rank, null-space structure and LP/MILP bounds. Second, a **dynamic predictive layer** estimates latent shares or levels using seasonal history, industry/geographic common factors and change-point-aware state dynamics. Third, a **constraint/reconciliation layer** conditions every point or posterior draw on the public feasible set. Fourth, an **output-risk layer** decides whether a cell-level result is sufficiently uncertain and analytically necessary to be disseminated.

For groups of suppressed children whose subtotal $S_t$ is known, modeling **shares** is usually preferable to modeling raw children separately, because

```math
x_{jt}=S_t p_{jt},\qquad \sum_j p_{jt}=1
```

automatically preserves the most important identity. Log-ratio or logistic-normal dynamic models are more flexible than a fixed Dirichlet when shares show correlation and time dependence. Where the number of jointly suppressed children is only two, the problem reduces to a one-dimensional latent share $p_t$:

```math
a_t=S_t p_t,\qquad
b_t=S_t(1-p_t).
```

This makes transparent how little a point estimate adds unless there is independent information about $p_t$.

**Suppression-aware likelihood.** Let $R_{jt}=1$ denote publication and $R_{jt}=0$ suppression. A naïve model implicitly assumes

```math
P(R_{jt}\mid x_{jt},\text{latent respondent composition},\ldots)
```

is ignorable. QCEW documentation makes that implausible. A better conceptual model is

```math
P(x,R)=P(x)\,P(R\mid x,H,C,\mathcal T),
```

where $H$ represents hierarchy/table geometry, $C$ confidential concentration or respondent-composition variables, and $\mathcal T$ the disclosure algorithm. Because exact modern $\mathcal T$ and $C$ are not public, the full selection model is not identified. That limitation should be stated rather than hidden. Historical BLS documentation establishes that magnitude/concentration and table structure were inputs to primary and secondary nondisclosure, while current BLS deliberately does not expose all operational details. [[1](#ref-1), [3](#ref-3), [5](#ref-5)]

In practice, fit sensitivity models spanning plausible selection effects rather than pretending MAR. For example, allow suppressed observations to have systematically higher latent variance, larger expected parent shares, or different tail behavior than comparable visible observations. Compare posterior results across these assumptions.

**A practical end-to-end workflow** is:

| Stage | Recommended action | Required output or decision |
|---|---|---|
| **Data vintage management** | Archive each QCEW release with download timestamp, quarter, preliminary/final status and source product. Never overwrite older vintages. | Immutable provenance table |
| **Classification harmonization** | Map NAICS vintages explicitly; preserve original codes; identify county/MSA/ownership changes rather than forcing all history into one taxonomy. | Harmonization/crosswalk version |
| **Hierarchy construction** | Build atomic area × industry × ownership × period keys and a sparse aggregation matrix for every valid additive release. | $A$ plus metadata for every row |
| **Solvability audit** | Remove observed components, compute rank/null space and connected components. | Exactly recoverable versus underidentified groups |
| **Deterministic bounds** | Solve min/max LPs; use MILP for genuine integer quantities when it can alter bounds. | $[L_j,U_j]$ for every suppressed cell |
| **Rounding/revision treatment** | Replace rounded equations by intervals and quarantine inconsistent vintages. | Audited feasible constraint set |
| **Model selection** | Choose historical-share, dynamic regression, state-space or Bayesian hierarchy based on backtests and structural context. | Pre-specified model family |
| **Reconciliation** | Condition/optimize estimates so every valid published additive margin is satisfied. | Coherent completed table |
| **Uncertainty production** | Produce posterior draws or multiple imputations within $\mathcal F$, not merely standard errors around an unconstrained point estimate. | Quantiles and/or completed datasets |
| **Pseudo-suppression backtesting** | Artificially mask published cells with realistic clustered/complementary patterns and evaluate rolling origins. | Out-of-sample diagnostics |
| **Sensitivity analysis** | Vary structural breaks, priors, peer definitions, suppression selection, bounds and revision assumptions. | Model-dependence envelope |
| **Documentation** | Record constraint provenance and label every restriction as “public fact” or “model assumption.” | Reproducible audit trail |
| **Disclosure review** | Test whether the proposed released estimate or interval materially defeats an `N` flag, especially when external employer knowledge could be linked. | Release, aggregate, widen, restrict access, or suppress |

QCEW's own data-processing documentation reinforces the first two stages: observations can be imputed before publication, revisions occur, establishments are linked longitudinally, and administrative changes can create breaks. A reconstructed value should therefore never be described as “the employer-reported truth”; even a published QCEW aggregate may contain BLS imputation for late or missing respondents. BLS changed its QCEW nonresponse-imputation approach beginning in 2020, which is another reason not to assume a temporally invariant measurement process. [[6](#ref-6), [28](#ref-28)]

## Validation and sensitivity analysis

Validation is unusually important here because the actual suppressed values are, by design, unavailable. The strongest design is therefore **pseudo-suppression on cells whose true published values are known**, supplemented by rolling temporal holdouts and group-level holdouts.

Simple random masking is inadequate. Real QCEW suppression is clustered by hierarchy and is not random with respect to disclosure risk. A proper simulation should create at least two stages: a surrogate “primary suppression” process associated with observable proxies for small counts, large shares, or concentration risk, followed by complementary suppression chosen so no protected parent-child group contains only one missing component. This does **not** recreate BLS's confidential rule—the relevant parameters and establishment-level dominance information are unavailable—but it gives a much more realistic stress test than uniformly blanking cells. [[4](#ref-4), [1](#ref-1), [3](#ref-3)]

A particularly informative design is to begin from complete groups where all children are published, designate one pseudo-primary cell according to a transparent research rule, then use an independent complementary-suppression algorithm to mask additional cells until subtraction no longer identifies the target. The same estimator can then be evaluated under two conditions: primary-like cells and merely complementary cells. That separation matters because the two missingness processes have different selection properties.

**Rolling-origin validation** should mimic the actual temporal information set:

```math
\{1,\ldots,t-1\}\to t,
\qquad
\{1,\ldots,t\}\to t+1,
```

rather than randomly allocating quarters to train and test data. Retrospective smoothers can be evaluated separately using both past and future observations. A random split lets a model train on quarters immediately adjacent to a held-out observation and can also leak information through parent totals or overlapping geographic/industry margins that contain the held-out value.

**Whole-group holdouts** are equally important. Hold out all suppressed candidates within selected parent-child groups, or whole county-industry slices, rather than individual cells. Otherwise neighboring margins may effectively reveal the test cell, making predictive performance look much better than it is.

Evaluation should be stratified by:

- stable versus volatile industries;
- cell size and parent share;
- one-quarter versus long suppression runs;
- simple versus heavily overlapping suppression patterns;
- county, state and national aggregation level;
- private versus government ownership where economically meaningful;
- recession/shock periods;
- establishment births/deaths and reporting changes where identifiable;
- NAICS or geographic classification transitions.

BLS's documentation on administrative changes and classification breaks provides strong justification for those strata. [[6](#ref-6), [9](#ref-9)]

For point predictions $e_i=\hat x_i-x_i$, use several complementary metrics:

```math
\mathrm{MAE}=\frac1n\sum_i|e_i|,
```

```math
\mathrm{RMSE}=
\sqrt{\frac1n\sum_i e_i^2},
```

```math
\mathrm{Bias}=\frac1n\sum_i e_i,
```

and, where true values are safely away from zero,

```math
\mathrm{MdAPE}
=
\operatorname{median}_i
\left(
\frac{|e_i|}{|x_i|}
\right).
```

For heterogeneous QCEW magnitude cells, weighted absolute percentage error,

```math
\mathrm{WAPE}
=
\frac{\sum_i|\hat x_i-x_i|}
{\sum_i|x_i|},
```

is often more stable than averaging cell-level percentages. MAPE-type measures are pathological at or near zero, so MAE/RMSE and size-stratified results should remain primary for tiny cells.

For groups in which the substantive target is allocation rather than level, report share errors,

```math
|\hat p_{jt}-p_{jt}|,
```

rank accuracy, top-child accuracy and—for larger groups—rank correlations.

For deterministic bounds, evaluate:

```math
\text{width}_i=U_i-L_i,
```

the proportion of pseudo-hidden true values inside $[L_i,U_i]$, and how often the range collapses to a point. With correctly constructed public constraints, a known test value should lie in the feasible set; failures usually signal coding, rounding or vintage errors rather than “bad prediction.”

For probabilistic methods, report empirical coverage of nominal 50%, 80%, 90% and 95% intervals, their average width, calibration by cell size, and proper scoring rules where useful. Wide well-calibrated intervals are preferable to narrow intervals with poor coverage.

For every method, report **constraint violations** separately:

```math
\|A\hat x-y\|_1,\qquad
\|A\hat x-y\|_\infty,
```

plus counts of negative or noninteger outputs where those are impermissible. A reconciled estimator should make violations zero, apart from explicitly modeled rounding/revision slack.

A strong benchmark suite should include at least: equal split of the suppressed subtotal, last observed share, same-quarter previous-year share, rolling/EW historical share, peer growth, a simple constrained regression, and the proposed sophisticated model. If a Bayesian tensor model cannot reliably outperform the seasonal historical-share baseline after pseudo-suppression and structural-break stratification, its additional complexity is not justified.

**Structural-break sensitivity should be an explicit experiment, not an anecdotal caveat.** Refit the model after excluding pre-break history, using robust/heavy-tailed innovations, allowing change points, altering peer definitions, and varying the half-life of historical weights. Report how much the suppressed-cell estimate moves. A useful diagnostic is

```math
S_j=
\max_m \hat x_j^{(m)}
-
\min_m \hat x_j^{(m)},
```

where $m$ ranges over plausible model specifications. If $S_j$ is of the same order as the feasible interval, the point estimate is assumption-dominated.

Similarly, conduct a **vintage sensitivity analysis**. Estimate using only the vintage available contemporaneously, then repeat with final data. Differences measure real-time revision uncertainty. This is particularly important because QCEW current and previous-year information can be corrected and some released growth rates use adjusted unpublished comparators. [[10](#ref-10), [6](#ref-6)]

Finally, validation must include a privacy-oriented metric: **how much does the estimator reduce uncertainty in protected cells?** For example,

```math
R_j=
1-
\frac{\text{model interval width}}
{\text{deterministic feasible width}}.
```

A high $R_j$ can be statistically impressive but ethically concerning. In establishment statistics, utility and confidentiality are two objectives, not one. The recent QCEW formal-privacy research is especially useful here because it frames confidentiality itself through intended uncertainty around establishment values rather than only through whether a literal cell is printed. [[13](#ref-13)]

## Worked numerical example and broader applicability

Consider a **completely synthetic** employment table. Nothing in this example represents an actual QCEW cell or unpublished BLS suppression threshold.

For quarter $t$, let

```math
P_t=1000,
```

and suppose the eight published children sum to

```math
\sum_{i=1}^{8}x_{it}=840.
```

There are two suppressed children $a_t$ and $b_t$. The one indisputable public accounting fact is therefore

```math
a_t+b_t
=
P_t-\sum_{i=1}^{8}x_{it}
=
160.
```

Everything below is labeled either **fact/identified restriction** or **modeling assumption**.

| Information added | Feasible implication | Epistemic status |
|---|---|---|
| Parent and eight published children | $a+b=160$ | **Public accounting fact** |
| Nonnegativity | $0\le a\le160,\ b=160-a$ | **Definitional/factual for counts** |
| Integrality | $`a\in\{0,\ldots,160\}`$, 161 feasible pairs | **Definitional for employment counts** |
| Publicly justified bounds $50\le a\le110,\ 60\le b\le125$ | $50\le a\le100,\ 60\le b\le110$ | **Identifying only if bounds themselves are valid public facts** |
| Observed $a_{t-1}=72,\ a_{t+1}=84$ | No further restriction by themselves | **Historical facts, but no cross-time identity** |
| Assume changes no larger than 10 | $74\le a_t\le82,\ 78\le b_t\le86$ | **Model/regularity assumption** |
| Historical same-quarter shares imply $\hat p_a=0.481$ | $\hat a=76.96,\hat b=83.04$, perhaps reconciled to $77,83$ | **Model-based point estimate** |
| Additional margin $a+c=210$, with public bound $128\le c\le134$ | $76\le a\le82,\ 78\le b\le84$ | **Additional public partial identification** |
| Assume $a_t$ grows 8% from $a_{t-1}$ | $\hat a=77.76$, approximately 78; $\hat b\approx82$ | **Growth-model assumption** |
| Dynamic predictive distributions + all bounds | Posterior over feasible $`a\in\{76,\ldots,82\}`$ | **Probabilistic model, not identification** |

The first three steps illustrate a subtle point. Before nonnegativity, $a+b=160$ defines an unbounded line. Nonnegativity turns it into a line segment. Integrality changes that segment into 161 discrete points but **does not narrow its extreme values**. Integrality becomes much more important once several overlapping equations and narrow intervals exist.

Now suppose a researcher has legitimately established the synthetic bounds

```math
50\le a\le110,\qquad
60\le b\le125.
```

Because $b=160-a$,

```math
60\le160-a\le125
```

implies

```math
35\le a\le100.
```

Intersecting with $50\le a\le110$ gives

```math
50\le a\le100,
```

and therefore

```math
60\le b\le110.
```

That interval narrowing is **identified**; it does not require a statistical model.

Next suppose $a_{t-1}=72$ and $a_{t+1}=84$ are known. They do **not** logically imply any value for $a_t$. An establishment can open, close, relocate or be reclassified between quarters. In QCEW those possibilities are real, documented causes of discontinuity. [[6](#ref-6)]

Only after adding the explicit assumption

```math
|a_t-a_{t-1}|\le10
```

and

```math
|a_{t+1}-a_t|\le10
```

do we obtain

```math
62\le a_t\le82
```

from the first inequality and

```math
74\le a_t\le94
```

from the second. Their intersection is

```math
74\le a_t\le82.
```

This interval is therefore **assumption-dependent**, unlike the parent-child subtotal.

For historical-share allocation, suppose same-quarter historical shares of the jointly suppressed subtotal for child $a$ were 47%, 49% and 48%, with exponentially recency-weighted weights 0.2, 0.3 and 0.5. Then

```math
\hat p_a
=
0.2(0.47)+0.3(0.49)+0.5(0.48)
=
0.481,
```

so

```math
\hat a=160(0.481)=76.96,
\qquad
\hat b=83.04.
```

For integer employment counts a chosen reconciliation rule might report the analytic imputation $77,83$. **Nothing about the public accounting identity proves that split.** It is a historical-share estimate.

Now add an overlapping public margin,

```math
a+c=210,
```

where another valid constraint establishes

```math
128\le c\le134.
```

Then

```math
76\le a\le82.
```

Combined with $a+b=160$,

```math
78\le b\le84.
```

That is a new identified range resulting from public cross-table information. If $c$ had instead been publicly known **exactly** as 132, then

```math
a=210-132=78,\qquad b=82.
```

At that point the two cells would be **exactly algebraically recoverable**. No historical-share model, growth model or Bayesian model would be needed to identify them. From a disclosure-control perspective, that exact recoverability would be the important result; publishing the reconstructed suppressed value might defeat the purpose of the suppression. This is precisely why federal guidance calls for audits of the whole system of marginal equations rather than checking one displayed table in isolation. [[3](#ref-3)]

A growth-rate assumption gives a different kind of information. If a peer model predicts 8% growth from 72,

```math
\hat a_t=72(1.08)=77.76.
```

Subject to integrality and $a+b=160$, one might use $a=78,b=82$. Again, the identified set remains $[76,82]$ for $a$; the growth assumption merely ranks points within it.

Finally consider a synthetic probabilistic state-space prediction before observing the subtotal:

```math
a_t\sim N(79,4^2),\qquad
b_t\sim N(81,4^2),
```

independently for illustration. Conditioning on the exact accounting equation $a+b=160$ gives, in the unconstrained Gaussian case,

```math
a_t\mid(a_t+b_t=160)
\sim
N(79,8),
```

with standard deviation approximately $2.83$.

Now also impose the deterministic public interval and integrality,

```math
a_t\in\{76,77,\ldots,82\}.
```

The resulting discrete posterior probabilities are approximately:

| $a_t$ | 76 | 77 | 78 | 79 | 80 | 81 | 82 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| Posterior probability | .102 | .140 | .168 | .179 | .168 | .140 | .102 |

The posterior mean is 79, and about 79.6% of posterior mass lies on $77$ through $81$. The deterministic identified set, however, remains $76$ through $82$. The probabilistic model has **not discovered an additional accounting fact**; it has imposed a distribution over the admissible possibilities.

That distinction—**identified set first, probability distribution second**—is the most important conceptual safeguard in the entire exercise.

The framework transfers unevenly across official-statistics systems.

| Program/data type | What transfers directly | What does not |
|---|---|---|
| **QCEW employment, establishment and wage totals** | Additive constraint matrices, LP bounds, reconciliation, temporal models, constrained MI | Average wages and percentage changes are not additive |
| **Other establishment magnitude/count tables** | Primary/complementary suppression analysis, dominance-aware MNAR models, LP/MILP bounds | Program-specific disclosure rules cannot be inferred from QCEW |
| **BLS workplace injury/illness counts** | Additive counts can use hierarchy/bounds concepts | Incidence rates are nonlinear; current program rules must be verified independently |
| **Occupational employment/wage statistics** | Borrowing strength, benchmarking and uncertainty methods | Survey estimates and wage averages are not necessarily exact accounting components |
| **Price indexes** | Time-series, state-space, hierarchical and reconciliation concepts | Index numbers generally cannot be reconstructed by summing published child indexes |
| **Productivity statistics** | State-space/benchmarking and accounting-aware modeling | Productivity ratios and chain indexes are not simple additive cells |
| **Census business/economic tables** | Magnitude-table SDC, complementary-suppression and constrained estimation are highly transferable | Disclosure rules/product perturbations may differ |
| **Decennial/demographic Census products using formal privacy** | Hierarchical constrained inference and probabilistic reconciliation | Published quantities may be noisy measurements rather than exact confidential totals, so they must not be treated as $Ax=y$ truth |
| **BEA economic accounts** | Benchmarking, reconciliation and accounting-identity methods | Many chain-type quantity/index measures are explicitly nonadditive; revisions are central |

FCSM's 2005 report documented then-current disclosure practices across BLS, Census, BEA and other federal agencies, and within BLS described program-specific rules for QCEW, the Survey of Occupational Injuries and Illnesses, National Compensation Survey, CPI and PPI. Those details are historically useful but should **not** be presented as current 2026 policy without program-specific verification. [[3](#ref-3)]

The Census experience also illustrates an important methodological distinction. The 2020 Census TopDown system adds privacy-protecting noise and postprocesses measurements to satisfy specified structural constraints. In such a system, the public figure is not generally an exact equation on the confidential underlying table. Treating it like a traditional unperturbed QCEW margin would overstate identification. [[29](#ref-29)]

For BEA and price/productivity systems, the lesson is equally important: the constraint approach applies only to genuine accounting identities. An index hierarchy is not automatically an additive hierarchy. The broad ideas—state-space estimation, benchmarking, coherent probabilistic inference and model-vintage management—transfer much farther than literal subtraction.

## Ethical boundaries and open research questions

The statistical objective should be **analytically useful aggregate estimation, not respondent discovery**. BLS's current confidentiality pledge states that information supplied under a pledge of confidentiality is used for statistical purposes and protected against identifiable disclosure; BLS cites CIPSEA and other legal protections governing such information. [[14](#ref-14)]

FCSM's disclosure framework is broader than direct naming. It recognizes identity disclosure, attribute disclosure and inferential disclosure, and specifically notes that confidential information can become disclosive through combination with publicly available or external data. It recommends that agencies keep disclosure risk very low after considering relevant public auxiliary information. [[3](#ref-3)]

The relevance to suppressed-cell research is direct. A model estimate with a 40% uncertainty band is qualitatively different from an algebraically reconstructed value. So is a posterior whose precision depends on a strong stationarity prior. Responsible documentation should always state whether a result is:

**observed**, **exactly implied by public accounting identities**, **bounded by public constraints**, **predicted by a model**, or **assumption-sensitive**.

A suppression flag should never disappear from the analytic metadata merely because a researcher imputes the field.

Modern reconstruction results also make clear that “every ingredient was public” is not, by itself, a sufficient confidentiality analysis. The 2010 Census reconstruction study used published aggregate tables and demonstrated that composition could reveal far more than individual tables suggested; composition-attack theory reaches the same general conclusion. QCEW-specific 2025 research explicitly discusses the possibility that BLS and state releases can interact in this manner. [[12](#ref-12), [11](#ref-11), [13](#ref-13)]

A conservative **no-release rule** should therefore apply when any of the following holds: public equations exactly reconstruct an `N`-flagged cell; the deterministic range is sufficiently narrow that combining it with publicly known employer information could identify a dominant respondent's contribution; a model's apparent precision comes almost entirely from assumptions that cannot be externally validated; the research question can be answered almost as well at a coarser aggregation; or dissemination of the estimate would materially reduce the confidentiality protection that the official release intentionally provides. In those cases, appropriate alternatives are a larger geographic/industry aggregate, a deliberately wider interval, a qualitative conclusion, or use of a restricted-access research environment.

There is an important legal nuance: the federal confidentiality obligations governing BLS and its authorized agents are not automatically equivalent to a blanket prohibition on all mathematical analysis of already-public statistics. Applicable contracts, restricted-data agreements and other laws can impose additional obligations. The methodological recommendation here is therefore a **research-ethics and disclosure-risk standard**, not a claim that every public-data reconstruction exercise is legally prohibited.

**Open research questions.** The literature still leaves several important problems unresolved.

The first is **suppression-aware inference when the selection rule is partly secret**. Standard MAR theory is implausible, but the exact QCEW selection likelihood cannot be constructed publicly because the concentration parameters and respondent-level composition are intentionally protected. Robust partial-identification methods that bound the consequences of plausible MNAR selection would be preferable to choosing one arbitrary selection model. Historical FCSM guidance explicitly explains why publicizing exact rule parameters can weaken disclosure protection. [[3](#ref-3)]

Second, there is a need for **dynamic constrained Bayesian models that preserve sharp deterministic bounds**. Many current hierarchical methods benchmark posterior means after estimation. For suppression problems, every posterior draw should ideally lie in the public feasible polytope, while still admitting revision error, rounding and classification changes. Recent probabilistic reconciliation and Bayesian benchmarking work provides pieces of this architecture but not yet a QCEW-scale complete solution. [[17](#ref-17), [19](#ref-19), [21](#ref-21)]

Third, **validation under realistic MNAR complementary-suppression patterns** deserves dedicated research. Random masking substantially understates the difficulty. A public benchmark with synthetic establishment microdata, realistic dominance patterns, classification breaks, multi-period hierarchies and known ground truth would allow methods to be evaluated consistently.

Fourth, the field needs a principled connection between **predictive uncertainty and disclosure uncertainty**. A 95% posterior credible interval describes uncertainty under a statistical model; an agency protection interval describes how closely respondent information may safely be inferred. Those are different objects. The 2025 QCEW-focused work on establishment-oriented formal privacy is particularly promising because it explicitly frames protection in terms of interpretable uncertainty about business values. [[13](#ref-13)]

Fifth, **revision-aware identification** is underdeveloped. Public statistical tables increasingly exist in many archived vintages. Treating each new vintage as “more equations” is wrong whenever the underlying records or classifications changed. A useful future framework would jointly model latent economic quantities, administrative revisions and the release process.

Sixth, **constrained low-rank models under endogenous suppression** remain an open opportunity. Matrix/tensor methods can use extraordinary amounts of QCEW cross-sectional structure, but standard low-rank assumptions are weakest around dominant unusual establishments and standard missingness theory does not match suppression. MNAR matrix-completion research is moving in the right direction. [[23](#ref-23)]

Seventh, the computational problem is large but structurally favorable. QCEW constraint matrices are sparse and repeated over time. Research combining graph decomposition, sparse exact rank analysis, LP warm starts, selected integrality and probabilistic inference could make national multi-decade analyses tractable without sacrificing explicit identification diagnostics.

## Bibliography

1. <a id="ref-1"></a>Powers, Randall, and Stephen Cohen. 2004. "Use of an Audit Program to Improve Confidentiality Protection of Tabular Data at the Bureau of Labor Statistics." BLS Office of Survey Methods Research. Direct QCEW application of linear-programming disclosure auditing and historical primary/secondary nondisclosure procedures.

2. <a id="ref-2"></a>Cox, Lawrence H. 1980. "Suppression Methodology and Statistical Disclosure Control." *Journal of the American Statistical Association* 75(370): 377-385. Foundational treatment of cell suppression and systems of tabular equations; extensively incorporated into later FCSM guidance.

3. <a id="ref-3"></a>Federal Committee on Statistical Methodology. 2005. *Statistical Policy Working Paper 22: Report on Statistical Disclosure Limitation Methodology*, second version. Originally prepared 1994, revised 2005. Core federal guidance on cell suppression, p-percent and `(n,k)` rules, complementary suppression, LP auditing, controlled tabular adjustment and federal-agency practice.

4. <a id="ref-4"></a>Bureau of Labor Statistics. *QCEW Questions and Answers*. Current documentation of disclosure codes, suppression, establishment-count publication, complementary suppression, higher-level totals and longitudinal caveats.

5. <a id="ref-5"></a>Bureau of Labor Statistics. *Quarterly Census of Employment and Wages: Presentation*, Handbook of Methods. Current documentation of confidentiality evaluation, longitudinal data and preliminary/final release status.

6. <a id="ref-6"></a>Bureau of Labor Statistics. *Quarterly Census of Employment and Wages: Calculation*, Handbook of Methods. Current page last modified January 2026. Describes aggregation, validation, imputation, establishment linking, longitudinal breaks, adjustments and confidentiality.

7. <a id="ref-7"></a>Bureau of Labor Statistics. *QCEW Field Layouts for NAICS-Based Quarterly CSV Files*. Current quarterly schema and documented rounding of derived statistics.

8. <a id="ref-8"></a>Bureau of Labor Statistics. *QCEW Field Layouts for NAICS-Based Annual CSV Files*. Current annual schema and annual aggregation relationships.

9. <a id="ref-9"></a>Bureau of Labor Statistics. *QCEW Industry Classification*. Current documentation of NAICS vintages and warning that classification changes create discontinuities.

10. <a id="ref-10"></a>Bureau of Labor Statistics. *QCEW Data Guide*. Current data-access/vintage documentation; current page last modified January 2026.

11. <a id="ref-11"></a>Ganta, Srivatsava Ranjit, Shiva Prasad Kasiviswanathan, and Adam Smith. 2008. "Composition Attacks and Auxiliary Information in Data Privacy." arXiv:0803.0032. Foundational analysis of privacy failure across overlapping releases.

12. <a id="ref-12"></a>Abowd, John M., Tamara Adams, Robert Ashmead, David Darais, Sourya Dey, Simson Garfinkel, Nathan Goldschlag, Daniel Kifer, Philip Leclerc, Ethan Lew, Scott Moore, Rolando Rodriguez, Ramy Tadros, and Lars Vilhuber. 2023. "The 2010 Census Confidentiality Protections Failed, Here's How and Why." arXiv:2312.11283. Empirical reconstruction study from published tables.

13. <a id="ref-13"></a>Webb, Kaitlyn, Prottay Protivash, John Durrell, Daniell Toth, Aleksandra Slavkovic, and Daniel Kifer. 2025. "Statistics-Friendly Confidentiality Protection for Establishment Data, with Applications to the QCEW." arXiv:2509.01597. Directly QCEW-focused formal-privacy research.

14. <a id="ref-14"></a>Bureau of Labor Statistics. *Confidentiality Pledge and Laws*. Current BLS confidentiality documentation, including CIPSEA and related protections.

15. <a id="ref-15"></a>Bureau of Labor Statistics. *QCEW Aggregation Level Codes* and *Ownership Codes*. Current hierarchy metadata for national, state, county, metropolitan, ownership and NAICS aggregations.

16. <a id="ref-16"></a>Archer, David W., Borja de Balle Pigem, Dan Bogdanov, et al. 2023. *UN Handbook on Privacy-Preserving Computation Techniques*. arXiv:2301.06167. International methodological guidance on privacy-preserving statistical computation.

17. <a id="ref-17"></a>Girolimetto, Davide, and Tommaso Di Fonzo. 2023. "Point and Probabilistic Forecast Reconciliation for General Linearly Constrained Multiple Time Series." arXiv:2305.05330. General constrained point and distributional reconciliation.

18. <a id="ref-18"></a>Steorts, Rebecca C. 2014. "Smoothing, Clustering, and Benchmarking for Small Area Estimation." arXiv:1410.7056. Constrained estimation combining smoothing and aggregate benchmarks.

19. <a id="ref-19"></a>Sugasawa, Shonosuke, Genya Kobayashi, and Yuki Kawakubo. 2024. "Bayesian Benchmarking Small Area Estimation via Entropic Tilting." arXiv:2407.17848. Benchmark-consistent posterior distributions and uncertainty quantification.

20. <a id="ref-20"></a>Molina, Isabel, Balgobin Nandram, and J. N. K. Rao. 2014. "Small Area Estimation of General Parameters with Application to Poverty Indicators: A Hierarchical Bayes Approach." arXiv:1407.8384. Hierarchical Bayesian borrowing of strength.

21. <a id="ref-21"></a>Okonek, Taylor, and Jon Wakefield. 2022. "A Computationally Efficient Approach to Fully Bayesian Benchmarking." arXiv:2203.12195. Posterior benchmarking through sampling-based methods.

22. <a id="ref-22"></a>Steorts, Rebecca C., and Malay Ghosh. 2013. "On Estimation of Mean Squared Errors of Benchmarked Empirical Bayes Estimators." arXiv:1304.1600. Studies uncertainty introduced by benchmarking.

23. <a id="ref-23"></a>Capponi, Agostino, and Mihailo Stojnic. 2024. "Exact Error in Matrix Completion: Approximately Low-Rank Structures and Missing Blocks." arXiv:2401.00578. Explicit treatment of approximately low-rank matrices with MNAR block missingness.

24. <a id="ref-24"></a>Li, Tianxi. 2016. "A Note on the Statistical View of Matrix Completion." arXiv:1605.03040. Connects matrix completion to missing-data assumptions.

25. <a id="ref-25"></a>Yang, Yanjiao, and Jerome P. Reiter. 2024. "Imputation of Nonignorable Missing Data in Surveys Using Auxiliary Margins Via Hot Deck and Sequential Imputation." arXiv:2406.04599. MNAR multiple imputation using known margins.

26. <a id="ref-26"></a>Akande, Olanrewaju, and Jerome P. Reiter. 2020. "Multiple Imputation for Nonignorable Item Nonresponse in Complex Surveys Using Auxiliary Margin." arXiv:2011.05482. Constraint-informed nonignorable imputation.

27. <a id="ref-27"></a>Pannekoek, Jeroen, Natalie Shlomo, and Ton de Waal. 2014. "Calibrated Imputation of Numerical Data under Linear Edit Restrictions." arXiv:1401.1663. Constrained official-statistics imputation using linear edits and known totals.

28. <a id="ref-28"></a>Bureau of Labor Statistics. *QCEW Imputation*. Current methodological documentation; notes the 2020 change in nonresponse imputation and treatment of late/missing respondents.

29. <a id="ref-29"></a>Abowd, John M., Robert Ashmead, Ryan Cumings-Menon, et al. 2022. "The 2020 Census Disclosure Avoidance System TopDown Algorithm." arXiv:2204.08986. Hierarchical noisy measurement and constrained postprocessing under formal privacy.

30. <a id="ref-30"></a>Federal Committee on Statistical Methodology. 1978. *Statistical Policy Working Paper 2: Report on Statistical Disclosure and Disclosure-Avoidance Techniques*. Early federal treatment of dominance rules, complementary suppression and cross-table derivation; predecessor to Working Paper 22.

31. <a id="ref-31"></a>Cox, Lawrence H. 2009. "Vulnerability of Complementary Cell Suppression to Intruder Attack." *Journal of Privacy and Confidentiality* 1(2): 235-251. Direct analysis of inference vulnerabilities in complementary suppression.

32. <a id="ref-32"></a>Fischetti, Matteo, and Juan Jose Salazar-Gonzalez. 2001. "Solving the Cell Suppression Problem on Tabular Data with Linear Constraints." *Management Science* 47(7): 1008-1026. Optimization treatment of complementary cell suppression.

33. <a id="ref-33"></a>Castro, Jordi. 2006. "Minimum-Distance Controlled Perturbation Methods for Large-Scale Tabular Data Protection." *European Journal of Operational Research* 171(1): 39-52. Optimization-based alternative to suppression for large tables.

34. <a id="ref-34"></a>Hundepool, Anco, Josep Domingo-Ferrer, Luisa Franconi, Sarah Giessing, Eric Schulte Nordholt, Keith Spicer, and Peter-Paul de Wolf. 2012. *Statistical Disclosure Control*. Wiley Series in Survey Methodology. Comprehensive European/NSI treatment of tabular and microdata disclosure control.

35. <a id="ref-35"></a>Abowd, John M., Lorenzo Alvisi, Cynthia Dwork, Sampath Kannan, Ashwin Machanavajjhala, and Jerome Reiter. 2017. "Privacy-Preserving Data Analysis for the Federal Statistical Agencies." arXiv:1701.00752. Federal-statistics perspective on cumulative information leakage and formal privacy.

36. <a id="ref-36"></a>Elliot, Mark, and Josep Domingo-Ferrer. 2018. "The Future of Statistical Disclosure Control." arXiv:1812.09204. Review of SDC in an environment of increasingly linkable and computationally exploitable data.

37. <a id="ref-37"></a>Rubin, Donald B. 1976. "Inference and Missing Data." *Biometrika* 63(3): 581-592. DOI: **10.1093/biomet/63.3.581**. Foundational MAR/nonignorable missing-data framework.

38. <a id="ref-38"></a>Rubin, Donald B. 1987. *Multiple Imputation for Nonresponse in Surveys*. Wiley. DOI: **10.1002/9780470316696**. Foundational multiple-imputation framework.

39. <a id="ref-39"></a>Denton, Frank T. 1971. "Adjustment of Monthly or Quarterly Series to Annual Totals: An Approach Based on Quadratic Minimization." *Journal of the American Statistical Association* 66(333): 99-102. DOI: **10.1080/01621459.1971.10482227**. Foundation for movement-preserving temporal benchmarking.

40. <a id="ref-40"></a>Dagum, Estela Bee, and Pierre A. Cholette. 2006. *Benchmarking, Temporal Distribution, and Reconciliation Methods for Time Series*. Springer. Comprehensive official-statistics treatment of temporal benchmarking and reconciliation.

41. <a id="ref-41"></a>Deming, W. Edwards, and Frederick F. Stephan. 1940. "On a Least Squares Adjustment of a Sampled Frequency Table When the Expected Marginal Totals Are Known." *Annals of Mathematical Statistics* 11(4): 427-444. DOI: **10.1214/aoms/1177731829**. Foundational marginal-adjustment literature.

42. <a id="ref-42"></a>Fay, Robert E., and Roger A. Herriot. 1979. "Estimates of Income for Small Places: An Application of James-Stein Procedures to Census Data." *Journal of the American Statistical Association* 74(366): 269-277. DOI: **10.1080/01621459.1979.10482505**. Foundational area-level small-area estimation.

43. <a id="ref-43"></a>Candes, Emmanuel J., and Benjamin Recht. 2009. "Exact Matrix Completion via Convex Optimization." *Foundations of Computational Mathematics* 9: 717-772. DOI: **10.1007/s10208-009-9045-5**. Foundational low-rank matrix-completion theory; its observation assumptions illustrate why nonrandom suppression needs special care.

44. <a id="ref-44"></a>Aitchison, John. 1982. "The Statistical Analysis of Compositional Data." *Journal of the Royal Statistical Society, Series B* 44(2): 139-177. Foundational framework for vectors of shares constrained to sum to one; useful when suppressed children are modeled as shares of a known subtotal.
