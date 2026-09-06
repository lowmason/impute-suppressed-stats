# Stage 0 source audit -- findings

**Assembled** by `scripts/audit/assemble_finding.py` from the 12 source summaries under `data/raw/audit/`. **Newest `generated_utc` among them:** 2026-09-05T00:20:03+00:00.
**Spec:** `specs/logging-employment-spec.md` · **Roadmap:** `specs/logging-employment-spec-roadmap.md`, Stage 0 · **Plan:** `specs/plans/1-stage0-logging-employment-spec.md`
**Window (D1):** 2017-01 → 2024-12 · **Industry:** 113310 (Logging) · **Ownership:** private · **Geography:** states + D.C.

**Classification (§3.1):** the source prompt supplied `1113310`, which is not a valid NAICS code. It is recorded, not silently replaced -- `industry_code_supplied = '1113310'`, `industry_code_used = '113310'`, `industry_title = 'Logging'`, `classification_status = 'corrected_invalid_supplied_code'`. These four values are read from the fenced block under the spec's own `### 3.1` heading -- anchored there, not first-match across the file -- and are not retyped here.

Every value below is rendered from `data/raw/audit/<source>/summary.json`. Extract hashes are recorded in `source-audit-extracts.csv` and re-verified, in both directions, by `scripts/audit/verify_extracts.py`, which is also this stage's exit gate: re-run it to re-check the five criteria the roadmap's Stage 0 `Exit:` line states, and the artifact integrity they rest on. How much that proves has limits; two are worth naming here. First, the first criterion's field-by-field half runs against a mapping from that line's prose onto findings keys, hand-authored inside the gate and marked there as a reading rather than a measurement -- and two of the fields it maps are empty, passing by exemptions the gate declares by name: `qcew_routes.bulk_years_required`, an empty list the plan calls a legitimate finding, and `cbp_metadata.lfo_by_year`, null for every window year, whose why is the §1.2 row below. Second, the criterion covering §1.2's final bullet and the three §21 rows is four substring matches plus one presence test per Appendix A source name: its pass says those sections are in this document, not that their verdict cells say anything, so read the verdicts rather than that PASS line. Raw bytes live under `data/raw/audit/`, which is gitignored -- so the manifest records each extract's path relative to the repository root, while the summaries record it absolutely, as `_common.AUDIT_ROOT` is absolute. Recorded values are otherwise reproduced verbatim -- the summaries are the evidence, and rewriting them here would make this document disagree with them. 1 source has at least one rendered value embedding an absolute path from the machine this audit ran on (`qcew_identity`).

## Sources audited

Recorded values, verbatim where they fit. `(empty)` and `null` are what the source summary recorded, not a reading of what they mean; a long value is replaced by a descriptor and rendered whole in its per-source section below.

| Source | Access | Route | Covers of D1 window | Not covered |
|---|---|---|---|---|
| `bds` | verified | https://api.census.gov/data/timeseries/bds | 2017-2023 | 2024 |
| `cbp_metadata` | verified | https://api.census.gov/data/{year}/cbp | 2017-2023 | 2024 |
| `cbp_regime` | verified | recorded value (587 chars) -- see the per-source section | 2017-2023 | 2024 |
| `ces` | verified | https://download.bls.gov/pub/time.series/sm/<file> | recorded value (583 chars) -- see the per-source section | recorded value (218 chars) -- see the per-source section |
| `fia` | verified | https://apps.fs.usda.gov/fiadb-api/fullreport | recorded value (110 chars) -- see the per-source section | recorded value (1545 chars) -- see the per-source section |
| `qcew_codes` | verified | https://data.bls.gov/cew/doc/titles/<dimension>/ | 2017-2024 | (empty) |
| `qcew_identity` | verified | recorded value (112 chars) -- see the per-source section | 2017-01..2024-12 (96 month(s)) | (empty) |
| `qcew_panel` | verified | derived from qcew_routes slice extracts | 2017-01..2024-12 | (empty) |
| `qcew_routes` | verified | recorded value (161 chars) -- see the per-source section | 2017-2024 | (empty) |
| `qcew_size` | verified | https://data.bls.gov/cew/data/files/{year}/csv/{year}_q1_by_size.zip | first quarter of each window year only | recorded value (131 chars) -- see the per-source section |
| `susb` | verified | https://www2.census.gov/programs-surveys/susb/tables/{year}/ | 2017-2022 | 2023,2024 |
| `tpo` | verified | recorded value (357 chars) -- see the per-source section | recorded value (502 chars) -- see the per-source section | recorded value (594 chars) -- see the per-source section |

## SRC-QCEW-006 branch verdict

**Branch:** `decline`. The sentence below is `qcew_identity`'s recorded `verdict_sentence`, rendered from its summary rather than retyped; the notes section that follows states what the branch means for later stages.

> decline: across the 32 quarter(s) and 96 month(s) the panel covers (2017-01 through 2024-12), the national establishment count for industry 113310 and own_code 5 ('Private') equals the states+DC published sum in 32 of 32 evaluable quarter(s), with 0 unevaluable and 0 states+DC establishment cell(s) unpublished; the panel carries 1 non-state area(s) (Puerto Rico -- Statewide) across 24 area-month(s), measured as outside_national_total on 8 discriminating quarter(s); each of the 96 testable month(s) carries between 9 and 15 suppressed states+DC cells and an employment gap after non-state areas of at least 696; every one of the 96 testable month(s) carries at least one suppressed state cell, so the employment identity is untestable on a complete published state sum.

## Appendix A `enabled` defaults beside what this audit measured

Appendix A ships an `enabled` default per source; this audit measured whether the source's bytes can be fetched. Those are two different predicates -- a configuration default about whether the pipeline uses a source, and a measurement of reachability -- so this table juxtaposes them and leaves the reconciliation to the stage that owns each decision. The §21 section in the notes below gives this audit's verdict on the row that is genuinely decided by an extraction audit.

| Appendix A source | `enabled` default | Audited as | Measured access |
|---|---|---|---|
| `qcew` | true | `qcew_codes`, `qcew_identity`, `qcew_panel`, `qcew_routes` | verified |
| `qcew_size` | true | `qcew_size` | verified |
| `cbp` | true | `cbp_metadata`, `cbp_regime` | verified |
| `tpo` | false | `tpo` | verified |
| `fia` | false | `fia` | verified |
| `ces` | false | `ces` | verified |
| `susb` | false | `susb` | verified |
| `bds` | false | `bds` | verified |
| `nonemployer` | false | not audited | not measured |
| `bea` | false | not audited | not measured |

## SRC-QCEW-006 branch verdict -- consequence

The verdict sentence itself is rendered above, under "SRC-QCEW-006 branch verdict", from
`qcew_identity`'s recorded `verdict_sentence`. It is not retyped here: a 700-character sentence
copied by hand into a tracked document is a transcription defect waiting to happen, and no test
compares prose to prose.

**Consequence.** The branch is `decline`. Stage 2 therefore MUST NOT create a national
employment margin constraint out of this identity, and Stage 3's plan MUST name a substitute
allocation anchor before any baseline is written -- every §10.1-10.6 baseline allocates a
residual against a national total, and this audit could not verify one for employment. Two
asymmetries decide how much the `decline` costs, and both are measured:

- **The `decline` is about employment, not establishments.** The quarterly *establishment*
  identity closes exactly: `qcew_identity.quarter_table` records `estab_gap = 0` in all 32
  quarters of the window, and `qcew_panel.disclosure_code_values` records that all 1251 monthly
  rows carrying disclosure code `N` still publish `qtrly_estabs > 0` -- 1227 of them `states_dc`
  (`states_dc_rows`), the other 24 Puerto Rico's, the panel's only non-`states_dc` state-level
  area (`qcew_panel.other_state_level_areas` lists `72000` alone). The *employment* identity
  is what cannot be evaluated: `qcew_identity.evidence` records `clean_months = 0` of
  `months_total = 96`, because every month carries between 9 and 15 suppressed `states_dc`
  cells (`qcew_identity.panel_structure.states_dc_suppressed_per_month`), so no month offers a
  complete published state sum to compare the national row against.
- **The published state universe is 50 areas, not 51.** The District of Columbia (`11000`)
  publishes no 113310 private row in any month of the window --
  `qcew_panel.state_month_cell_coverage` records it under `areas_with_no_rows`, with all 96
  months absent, and `states_covered` is 50. Delaware (`10000`) and North Dakota (`38000`)
  publish for part of the window only, 36 and 48 months absent respectively. Any later stage
  that writes "the 51 states_dc areas" about published QCEW rows is wrong by one area for the
  whole window and by two more for part of it.

## Requirements that cannot be implemented without further source verification (§1.2)

Every row below is a measured gap, not an unattempted fetch: all twelve sources returned
`access.status = verified`. Cited keys are `<source>.findings.<key>` unless named otherwise.

| Requirement | What is missing | Which stage must resolve it |
|---|---|---|
| `SRC-CBP-003` | No fetched documentation states CBP's disclosure regime for reference year 2024: `cbp_regime.unknown_years = [2024]`, and the API serves no 2024 CBP dataset at all (`cbp_metadata.dataset_probe_status_by_year["2024"] = 404`). | Stage 1 fails closed on the unknown regime; re-audit when Census publishes CBP 2024. |
| §5.4 `cbp.predicates_to_discover: LFO` | `cbp_metadata.lfo_by_year` is `null` for all eight window years. LFO was only ever sent as a filter (`LFO=001`), never selected as an output column, so no code list came back; `cbp_metadata.notes` records that reason. Nothing about the source blocks it. | Stage 1 (parser), with a dedicated `LFO,LFO_LABEL` query. |
| `SRC-CBP-004`, `REQ-016` | CBP publishes 2017-2023 only (`cbp_metadata.years_available`), so a CBP-based intensity measurement covers seven of D1's eight years. | Stages 3 and 6: the CBP measurement model must handle a window year with no CBP vintage. |
| `SRC-QCEW-006` | The national employment identity cannot be verified from published QCEW at any point in the window (`qcew_identity.evidence.clean_months = 0`). | Stage 2 (no national employment margin from this identity); Stage 3 (substitute anchor named before any baseline). |
| `SRC-OTH-001`, `INV-010` | SUSB's latest published year is 2022 (`susb.latest_year`), leaving 2023-2024 with no SUSB vintage, and its size dimension is enterprise, not establishment (`susb.size_concept.value = "enterprise"`, column `ENTRSIZE`). Its detailed-sizes file does not reach six-digit NAICS at the state level (`susb.detailed_sizes_reaches_six_digit_at_state = false`). | Stage 1 (concept guard); Stage 7 (ingest). |
| `SRC-OTH-002` | BDS publishes no six-digit Logging detail to ingest: `bds.six_digit_logging_available = false`, `bds.finest_naics_available = "11"`, and the 3-, 4-, 5- and 6-digit probes answered 204 with empty bodies. Its years also stop at 2023. | Stage 7: drop or substitute the BDS proxy; six-digit detail must not be invented. |
| `SRC-OTH-003` | Three of the 51 `states_dc` jurisdictions publish no qualifying statewide CES series overlapping the window, and none publishes at 113310: `ces.states_dc_tally` is `{113310: 0, 1133: 4, 113: 0, supersector: 44, none: 3, other: 0}`. | Stage 7. |
| `SRC-FOR-001`, `REQ-015` (TPO half) | Two gaps. TPO per-state completeness within a window year is not enumerated: only reference year 2024's folder was listed (13 files, matching Box's own `filesCount` of 13), and `tpo.coverage_span.uncovered` records that a state-by-state count needs Box's paginated listing API for every window year. And the harvest-origin/mill-receipt split that SRC-FOR-001 requires rests on the sheet names of the one workbook fetched this run: `tpo.access.reason` marks that reading as an inference, with no data-row cells read and no second workbook compared. | Stage 7. |
| `REQ-015` (FIA half) | FIA carries no industry concept to select 113310 with: `fia.industry_concept_scan` counts 0 word-boundary hits for NAICS, SIC, industry, employment and establishment across the five fetched pages, against 282 for species and 52 for product. `fia.district_of_columbia_has_fia_evaluation = false`, so `states_dc`'s 51st member has no forest inventory either. `SRC-FOR-002` and `SRC-FOR-003` are *not* blocked -- this audit found both the sampling-error field (`fia.sampling_error_field = "SE"`) and the evaluation-vintage field (`fia.evaluation_vintage_field = "evalGrps"`, over a 1138-row index) -- so what is missing is the industry selection any FIA proxy would need before either can be stored against 113310. | Stage 7: its plan must name the crosswalk from FIA's species/product/land-use taxonomy before an FIA proxy is built. |

`SRC-OTH-005` (BEA `SAEMP25`/`SAEMP27`) is not in the table: the roadmap already records it as
`out-of-scope-deferred` with the discontinuation as its reason, and this audit probed no BEA
endpoint, so it has nothing to add or subtract.

## Open §21 decisions this audit touches

| §21 row | Verdict from this audit | Evidence |
|---|---|---|
| Geography universe (50 states + D.C.) | Confirmed on the establishment margin, with no residual cell needed; untestable on the employment margin. Neither "confirmed" nor "cannot be reconciled" on its own is true of both margins. | `qcew_identity.quarter_table`: `estab_gap = 0` and `estab_gap_after_other = 0` in all 32 quarters. `qcew_identity.non_state_area_containment`: on the 8 quarters where a non-state area publishes a non-zero establishment count, the gap is 0 in 8 and equals that area's own count in 0, verdict `outside_national_total` -- the one non-state area in the panel (`72000`, Puerto Rico -- Statewide) sits outside the national total rather than inside it, so no residual cell is required to close the establishment identity. Against that, D.C. contributes no published row at all, and `qcew_identity.evidence.clean_months = 0` leaves the employment margin unevaluated. |
| TPO/FIA coverage (required only after extraction audit) | Defer to Stage 7. The extraction audit this row waits on is now done, and it splits the two sources rather than settling them together. | `tpo.access.status = verified` with `harvest_origin_available = true` -- reachable, and it carries the harvest-origin concept SRC-FOR-001 needs, but only through an undocumented Box legacy-download redirect (`tpo.chosen_route`) and with per-state completeness unverified. `fia.access.status = verified` with a recorded reason -- one report retrieved and parsed, but no industry concept to slice 113310 out of (`fia.industry_concept_scan`). |
| Optional state sources (disabled by default) | Keep disabled. | This audit probed no state portal, so it gathered no evidence either way; the §21 row's own recommended default -- "Disabled by default", on the stated ground that no standardized nationwide feed was verified -- stands unchallenged rather than confirmed. The decision lives in that row and nowhere else: Appendix A has no optional-state-sources entry to cite (its ten `sources:` keys are `qcew`, `qcew_size`, `cbp`, `tpo`, `fia`, `ces`, `susb`, `bds`, `nonemployer`, `bea`), and an earlier version of this cell attributed the default to an `enabled: false` there that does not exist. |

## Auditor's notes

- **The §5.4 slice endpoint served far more than five reference years in this run.** D5 states
  the seed endpoint serves only the most recent five, which would leave most of D1 to the bulk
  route. `qcew_routes.earliest_year_served = 2014` and `latest_year_served = 2026`, and
  `bulk_years_required = []` -- in this run's boundary walk the slice route covered all of
  2017-2024 on its own, and the walk fetched a bulk file for 2017 anyway
  (`bulk_years_fetched = [2017]`) to compare columns. This is a status measured in one run, not
  a property of the route: Stage 1 must still select by reference year from a re-measured
  boundary rather than hard-code 2014.
- **The two QCEW routes do not return the same columns.** `qcew_routes.column_parity.identical`
  is `false`: `qtrly_estabs` (slice) against `qtrly_estabs_count` (bulk), the three `oty_`/`lq_`
  establishment variants renamed to match, and nine bulk-only columns of which five are
  `*_title` fields. Stage 1's single ingest interface has to reconcile those names, not assume
  them.
- **Suppression, with its denominator.** `qcew_panel.suppression_share_overall` is 0.260 over
  the 4716 `states_dc` month cells actually present in the panel, not over the 4896 cells of a
  51-area x 96-month grid (`qcew_panel.notes` states the denominator; `state_month_cell_coverage`
  decomposes the difference). Four of the 50 areas that publish at all are suppressed in every
  month they publish (`02000`, `15000`, `32000`, `50000`), 28 are never suppressed, and
  `suppressed_run_lengths` counts 54 maximal runs, four of them the full 96 months. Stage 4's
  mask design is sized against those numbers.
- **Every suppressed cell still publishes an establishment count.** All 1227 suppressed
  `states_dc` monthly cells report `qtrly_estabs > 0`
  (`qcew_panel.estabs_survive_suppression_share = 1.0`); the same is true of all 1251 rows
  carrying disclosure code `N`, the 24-row difference being Puerto Rico's area-months, which are
  outside `states_dc`. That is why the establishment identity is testable while the employment
  one is not, and it is the strongest structural constraint this audit found.
- **CES counts have two denominators, and they differ.** `ces.publication_level_by_sm_state_code` maps
  all 55 codes in the fetched `sm.state` file, and the `ces.states_with_*` counts are over those
  55 -- of which four (`00` All States, `72` Puerto Rico, `78` Virgin Islands, `99` All
  Metropolitan Statistical Areas) are not `states_dc` jurisdictions. `ces.states_dc_tally` is the
  D1-scoped count. So `states_with_supersector_only = 45` and `states_dc_tally.supersector = 44`
  are both correct and are not the same claim; the same holds for `states_with_none = 6` against
  `states_dc_tally.none = 3`. Any D1-scoped statement must cite the tally.
- **QCEW by-size is first-quarter only, and no aggregation level carries state, 113310 and
  size at once.** That is the measured predicate, and it is narrower than "the file has no
  state rows": `qcew_size.agglvl_inventory` records four aggregation levels (`61`-`64`) whose
  area pattern is `mixed` rather than `national`, so non-national areas do appear in the file
  -- but 113310 appears at exactly one level, `28`, whose area pattern is `national`. Hence
  `simultaneous_state_industry_size = false` and `stage6_reroute_required = false`, so §2.2
  row 3's premise holds and Stage 6 keeps its planned routing. All 24 Q2-Q4 probes across the
  eight window years returned 404 (`qcew_size.quarter_probe`); the finest simultaneous
  combination observed for 113310 is national geography x 113310 x size codes 1-7
  (`qcew_size.what_the_file_does_carry`).
- **CBP kept the `NAICS2017` predicate name through reference year 2023.**
  `cbp_metadata.naics_predicate_by_year` records `NAICS2017` for every year 2017-2023, so a
  Stage 1 parser that derives the predicate name from the reference year's NAICS vintage would
  ask for a variable CBP does not serve. The predicate must come from fetched metadata.
- **Non-200 bodies were retained as evidence, by design.** `bds` records four 204 responses,
  `fia` a 500, and `tpo` a 404, each with its body hashed and stored; every one of those three
  summaries carries a `raw_retention_rule` key stating why. A later stage re-reading the
  manifest should expect `http_status` values other than 200 and must not treat them as
  fetch failures.
- **A recorded value that embeds an absolute path is rendered verbatim anyway**, because the
  summaries are the evidence; the generated header above names which source that is, counted
  at render time rather than asserted here. Only the tracked extract manifest's `path` column is
  rewritten to repo-root-relative, so it still resolves in a fresh clone.

## Per-source findings

Everything from here to the end of the document is the recorded evidence itself: for each source, its `access`, `coverage_span` and `findings` objects rendered whole from `data/raw/audit/<source>/summary.json`, unabridged and unedited. Nothing in this section is summarised, ranked or interpreted by this assembler, besides each source's extract count in the italic line closing its block -- the one number below that this assembler computes rather than reproduces, and it is computed because the `extracts` list is the one recorded object this section does not render at all. That is the exception to the disclaimer just made; a second, weaker one qualifies `unabridged and unedited`: where a source recorded a non-empty `access.reason`, this assembler renders that one field a second time, as a blockquote under the source's `access` fence, with any run of whitespace in it collapsed to a single space -- the one field this section lifts out of one of those three objects and renders on its own. It is the weaker exception because it reproduces rather than computes, and because the `access` fence directly above still carries the same value, so the blockquote duplicates that rendering rather than standing in for it. Where a recorded value contains a reading rather than a measurement, it is the source script that says so, inside the value.

### `bds`

**access**:

```json
{
  "reason": null,
  "route": "https://api.census.gov/data/timeseries/bds",
  "status": "verified"
}
```

**coverage_span**:

```json
{
  "covered": "2017-2023",
  "published_end": "2023",
  "published_start": "1978",
  "uncovered": "2024",
  "window_end": "2024-12",
  "window_start": "2017-01"
}
```

**findings**:

```json
{
  "finest_naics_available": "11",
  "naics_probe": [
    {
      "digits": 2,
      "http_status": 200,
      "naics": "11",
      "row_count": 2346,
      "years_returned": [
        1978,
        1979,
        1980,
        1981,
        1982,
        1983,
        1984,
        1985,
        1986,
        1987,
        1988,
        1989,
        1990,
        1991,
        1992,
        1993,
        1994,
        1995,
        1996,
        1997,
        1998,
        1999,
        2000,
        2001,
        2002,
        2003,
        2004,
        2005,
        2006,
        2007,
        2008,
        2009,
        2010,
        2011,
        2012,
        2013,
        2014,
        2015,
        2016,
        2017,
        2018,
        2019,
        2020,
        2021,
        2022,
        2023
      ]
    },
    {
      "digits": 3,
      "http_status": 204,
      "naics": "113",
      "row_count": 0,
      "years_returned": []
    },
    {
      "digits": 4,
      "http_status": 204,
      "naics": "1133",
      "row_count": 0,
      "years_returned": []
    },
    {
      "digits": 5,
      "http_status": 204,
      "naics": "11331",
      "row_count": 0,
      "years_returned": []
    },
    {
      "digits": 6,
      "http_status": 204,
      "naics": "113310",
      "row_count": 0,
      "years_returned": []
    }
  ],
  "probe_query_scope": {
    "for": "state:*",
    "get": "YEAR,ESTAB"
  },
  "raw_retention_rule": {
    "extracts_recorded": 6,
    "extracts_with_non_200_status": 4,
    "non_200_statuses_recorded": [
      204
    ],
    "rule": "This script performs two kinds of fetch and registers a body from both, so the counters below count both. From each of the five NAICS-detail probes it writes and registers a fetched body whenever the endpoint answered at all, whatever the HTTP status, and each extract's own http_status records which status it carried. It also fetches this dataset's variables.json once, before any probe, to read which of the wanted variables the dataset declares, and registers that body as an extract too -- the first one, since it is fetched first -- which is what brings the count below to six whenever all five probes answer. That fetch is NOT on the same any-status terms: it goes through the shared request helper, which raises on a non-2xx status instead of returning it, so a failed variables fetch aborts the run rather than registering a non-200 extract. On this access-verdict probe, http_status alone already separates a 204 with an empty body (matched no published cell) from either 200 outcome; retaining that empty body anyway, with its sha256 sidecar like every other extract, is what makes the 204 a recorded observation rather than an unrecorded absence. The two 200 outcomes -- a 200 auth-rejection HTML page and a 200 real tabular answer -- share that identical status, so only the retained bytes tell the two 200 outcomes apart. A transport failure produces no body and so registers no extract; its evidence is the probe record's http_status-0 entry instead. The counters below therefore say which statuses were retained and nothing more: a retained status 200 means the endpoint answered with a body that claimed to be data, not that the body parsed as the tabular shape. findings.naics_probe's row_count tells a status-200 parse failure apart from a status-200 real answer whenever the real answer carries at least one data row; the one shape this script cannot distinguish by row_count alone is a status-200 parse failure against a status-200 tabular answer with a header row and zero data rows -- for that case the retained body itself, not any derived count, is what a reader would need to open. Reader's caution: this rule is this script's, and the absence of a non-200 extract under another source in this audit is not evidence that no non-200 response occurred there."
  },
  "six_digit_logging_available": false,
  "variables_present": [
    "ESTAB",
    "FIRM",
    "JOB_CREATION",
    "JOB_DESTRUCTION",
    "ESTABS_ENTRY",
    "ESTABS_EXIT"
  ],
  "years_available": [
    1978,
    1979,
    1980,
    1981,
    1982,
    1983,
    1984,
    1985,
    1986,
    1987,
    1988,
    1989,
    1990,
    1991,
    1992,
    1993,
    1994,
    1995,
    1996,
    1997,
    1998,
    1999,
    2000,
    2001,
    2002,
    2003,
    2004,
    2005,
    2006,
    2007,
    2008,
    2009,
    2010,
    2011,
    2012,
    2013,
    2014,
    2015,
    2016,
    2017,
    2018,
    2019,
    2020,
    2021,
    2022,
    2023
  ]
}
```

_Extracts: 6; summary `generated_utc` 2026-09-04T23:26:52+00:00._

### `cbp_metadata`

**access**:

```json
{
  "reason": null,
  "route": "https://api.census.gov/data/{year}/cbp",
  "status": "verified"
}
```

**coverage_span**:

```json
{
  "covered": "2017-2023",
  "published_end": "2023",
  "published_start": "2017",
  "uncovered": "2024",
  "window_end": "2024-12",
  "window_start": "2017-01"
}
```

**findings**:

```json
{
  "dataset_probe_status_by_year": {
    "2017": 200,
    "2018": 200,
    "2019": 200,
    "2020": 200,
    "2021": 200,
    "2022": 200,
    "2023": 200,
    "2024": 404
  },
  "empszes_by_year": {
    "2017": {
      "pairs": [
        {
          "code": "001",
          "label": "All establishments"
        },
        {
          "code": "204",
          "label": "Establishments with no paid employees"
        },
        {
          "code": "205",
          "label": "Establishments with paid employees"
        },
        {
          "code": "207",
          "label": "Establishments with less than 10 employees"
        },
        {
          "code": "209",
          "label": "Establishments with less than 20 employees"
        },
        {
          "code": "210",
          "label": "Establishments with less than 5 employees"
        },
        {
          "code": "211",
          "label": "Establishments with less than 4 employees"
        },
        {
          "code": "212",
          "label": "Establishments with 1 to 4 employees"
        },
        {
          "code": "213",
          "label": "Establishments with 1 employee"
        },
        {
          "code": "214",
          "label": "Establishments with 2 employees"
        },
        {
          "code": "215",
          "label": "Establishments with 3 or 4 employees"
        },
        {
          "code": "219",
          "label": "Establishments with 0 to 4 employees"
        },
        {
          "code": "220",
          "label": "Establishments with 5 to 9 employees"
        },
        {
          "code": "221",
          "label": "Establishments with 5 or 6 employees"
        },
        {
          "code": "222",
          "label": "Establishments with 7 to 9 employees"
        },
        {
          "code": "223",
          "label": "Establishments with 10 to 14 employees"
        },
        {
          "code": "230",
          "label": "Establishments with 10 to 19 employees"
        },
        {
          "code": "231",
          "label": "Establishments with 10 to 14 employees"
        },
        {
          "code": "232",
          "label": "Establishments with 15 to 19 employees"
        },
        {
          "code": "235",
          "label": "Establishments with 20 or more employees"
        },
        {
          "code": "240",
          "label": "Establishments with 20 to 99 employees"
        },
        {
          "code": "241",
          "label": "Establishments with 20 to 49 employees"
        },
        {
          "code": "242",
          "label": "Establishments with 50 to 99 employees"
        },
        {
          "code": "243",
          "label": "Establishments with 50 employees or more"
        },
        {
          "code": "249",
          "label": "Establishments with 100 to 499 employees"
        },
        {
          "code": "250",
          "label": "Establishments with 100 or more employees"
        },
        {
          "code": "251",
          "label": "Establishments with 100 to 249 employees"
        },
        {
          "code": "252",
          "label": "Establishments with 250 to 499 employees"
        },
        {
          "code": "253",
          "label": "Establishments with 500 employees or more"
        },
        {
          "code": "254",
          "label": "Establishments with 500 to 999 employees"
        },
        {
          "code": "260",
          "label": "Establishments with 1,000 employees or more"
        },
        {
          "code": "261",
          "label": "Establishments with 1,000 to 2,499 employees"
        },
        {
          "code": "262",
          "label": "Establishments with 1,000 to 1,499 employees"
        },
        {
          "code": "263",
          "label": "Establishments with 1,500 to 2,499 employees"
        },
        {
          "code": "270",
          "label": "Establishments with 2,500 employees or more"
        },
        {
          "code": "271",
          "label": "Establishments with 2,500 to 4,999 employees"
        },
        {
          "code": "272",
          "label": "Establishments with 5,000 to 9,999 employees"
        },
        {
          "code": "273",
          "label": "Establishments with 5,000 employees or more"
        },
        {
          "code": "280",
          "label": "Establishments with 10,000 employees or more"
        },
        {
          "code": "281",
          "label": "Establishments with 10,000 to 24,999 employees"
        },
        {
          "code": "282",
          "label": "Establishments with 25,000 to 49,999 employees"
        },
        {
          "code": "283",
          "label": "Establishments with 50,000 to 99,999 employees"
        },
        {
          "code": "290",
          "label": "Establishments with 100,000 employees or more"
        },
        {
          "code": "298",
          "label": "Covered by administrative records"
        }
      ],
      "source": "official_metadata_crosswalk"
    },
    "2018": {
      "note": "NOT the official CBP metadata enumeration -- this vintage's metadata carries no EMPSZES values crosswalk (see empszes_metadata_crosswalk_probe_by_year). A size class with zero logging establishments in every state this year is silently absent from `pairs`.",
      "pairs": [
        {
          "code": "001",
          "label": "All establishments"
        },
        {
          "code": "210",
          "label": "Establishments with less than 5 employees"
        },
        {
          "code": "220",
          "label": "Establishments with 5 to 9 employees"
        },
        {
          "code": "230",
          "label": "Establishments with 10 to 19 employees"
        },
        {
          "code": "241",
          "label": "Establishments with 20 to 49 employees"
        },
        {
          "code": "242",
          "label": "Establishments with 50 to 99 employees"
        },
        {
          "code": "251",
          "label": "Establishments with 100 to 249 employees"
        }
      ],
      "source": "observed_in_113310_state_slice"
    },
    "2019": {
      "note": "NOT the official CBP metadata enumeration -- this vintage's metadata carries no EMPSZES values crosswalk (see empszes_metadata_crosswalk_probe_by_year). A size class with zero logging establishments in every state this year is silently absent from `pairs`.",
      "pairs": [
        {
          "code": "001",
          "label": "All establishments"
        },
        {
          "code": "210",
          "label": "Establishments with less than 5 employees"
        },
        {
          "code": "220",
          "label": "Establishments with 5 to 9 employees"
        },
        {
          "code": "230",
          "label": "Establishments with 10 to 19 employees"
        },
        {
          "code": "241",
          "label": "Establishments with 20 to 49 employees"
        },
        {
          "code": "242",
          "label": "Establishments with 50 to 99 employees"
        },
        {
          "code": "251",
          "label": "Establishments with 100 to 249 employees"
        }
      ],
      "source": "observed_in_113310_state_slice"
    },
    "2020": {
      "note": "NOT the official CBP metadata enumeration -- this vintage's metadata carries no EMPSZES values crosswalk (see empszes_metadata_crosswalk_probe_by_year). A size class with zero logging establishments in every state this year is silently absent from `pairs`.",
      "pairs": [
        {
          "code": "001",
          "label": "All establishments"
        },
        {
          "code": "210",
          "label": "Establishments with less than 5 employees"
        },
        {
          "code": "220",
          "label": "Establishments with 5 to 9 employees"
        },
        {
          "code": "230",
          "label": "Establishments with 10 to 19 employees"
        },
        {
          "code": "241",
          "label": "Establishments with 20 to 49 employees"
        },
        {
          "code": "242",
          "label": "Establishments with 50 to 99 employees"
        },
        {
          "code": "251",
          "label": "Establishments with 100 to 249 employees"
        }
      ],
      "source": "observed_in_113310_state_slice"
    },
    "2021": {
      "note": "NOT the official CBP metadata enumeration -- this vintage's metadata carries no EMPSZES values crosswalk (see empszes_metadata_crosswalk_probe_by_year). A size class with zero logging establishments in every state this year is silently absent from `pairs`.",
      "pairs": [
        {
          "code": "001",
          "label": "All establishments"
        },
        {
          "code": "210",
          "label": "Establishments with less than 5 employees"
        },
        {
          "code": "220",
          "label": "Establishments with 5 to 9 employees"
        },
        {
          "code": "230",
          "label": "Establishments with 10 to 19 employees"
        },
        {
          "code": "241",
          "label": "Establishments with 20 to 49 employees"
        },
        {
          "code": "242",
          "label": "Establishments with 50 to 99 employees"
        },
        {
          "code": "251",
          "label": "Establishments with 100 to 249 employees"
        }
      ],
      "source": "observed_in_113310_state_slice"
    },
    "2022": {
      "note": "NOT the official CBP metadata enumeration -- this vintage's metadata carries no EMPSZES values crosswalk (see empszes_metadata_crosswalk_probe_by_year). A size class with zero logging establishments in every state this year is silently absent from `pairs`.",
      "pairs": [
        {
          "code": "001",
          "label": "All establishments"
        },
        {
          "code": "210",
          "label": "Establishments with less than 5 employees"
        },
        {
          "code": "220",
          "label": "Establishments with 5 to 9 employees"
        },
        {
          "code": "230",
          "label": "Establishments with 10 to 19 employees"
        },
        {
          "code": "241",
          "label": "Establishments with 20 to 49 employees"
        },
        {
          "code": "242",
          "label": "Establishments with 50 to 99 employees"
        },
        {
          "code": "251",
          "label": "Establishments with 100 to 249 employees"
        }
      ],
      "source": "observed_in_113310_state_slice"
    },
    "2023": {
      "note": "NOT the official CBP metadata enumeration -- this vintage's metadata carries no EMPSZES values crosswalk (see empszes_metadata_crosswalk_probe_by_year). A size class with zero logging establishments in every state this year is silently absent from `pairs`.",
      "pairs": [
        {
          "code": "001",
          "label": "All establishments"
        },
        {
          "code": "210",
          "label": "Establishments with less than 5 employees"
        },
        {
          "code": "220",
          "label": "Establishments with 5 to 9 employees"
        },
        {
          "code": "230",
          "label": "Establishments with 10 to 19 employees"
        },
        {
          "code": "241",
          "label": "Establishments with 20 to 49 employees"
        },
        {
          "code": "242",
          "label": "Establishments with 50 to 99 employees"
        },
        {
          "code": "251",
          "label": "Establishments with 100 to 249 employees"
        }
      ],
      "source": "observed_in_113310_state_slice"
    },
    "2024": null
  },
  "empszes_metadata_crosswalk_probe_by_year": {
    "2017": [
      {
        "carries_values_crosswalk": true,
        "status": 200,
        "url": "https://api.census.gov/data/2017/cbp/variables/EMPSZES.json"
      },
      {
        "carries_values_crosswalk": false,
        "status": 200,
        "url": "https://api.census.gov/data/2017/cbp/groups.json"
      },
      {
        "carries_values_crosswalk": false,
        "status": 200,
        "url": "https://api.census.gov/data/2017/cbp/groups/CB1700CBP.json"
      }
    ],
    "2018": [
      {
        "carries_values_crosswalk": false,
        "status": 200,
        "url": "https://api.census.gov/data/2018/cbp/variables/EMPSZES.json"
      },
      {
        "carries_values_crosswalk": false,
        "status": 200,
        "url": "https://api.census.gov/data/2018/cbp/groups.json"
      },
      {
        "carries_values_crosswalk": false,
        "status": 200,
        "url": "https://api.census.gov/data/2018/cbp/groups/CB1800ZBP.json"
      },
      {
        "carries_values_crosswalk": false,
        "status": 200,
        "url": "https://api.census.gov/data/2018/cbp/groups/CB1800CBP.json"
      }
    ],
    "2019": [
      {
        "carries_values_crosswalk": false,
        "status": 200,
        "url": "https://api.census.gov/data/2019/cbp/variables/EMPSZES.json"
      },
      {
        "carries_values_crosswalk": false,
        "status": 200,
        "url": "https://api.census.gov/data/2019/cbp/groups.json"
      },
      {
        "carries_values_crosswalk": false,
        "status": 200,
        "url": "https://api.census.gov/data/2019/cbp/groups/CB1900CBP.json"
      }
    ],
    "2020": [
      {
        "carries_values_crosswalk": false,
        "status": 200,
        "url": "https://api.census.gov/data/2020/cbp/variables/EMPSZES.json"
      },
      {
        "carries_values_crosswalk": false,
        "status": 200,
        "url": "https://api.census.gov/data/2020/cbp/groups.json"
      },
      {
        "carries_values_crosswalk": false,
        "status": 200,
        "url": "https://api.census.gov/data/2020/cbp/groups/CB2000CBP.json"
      }
    ],
    "2021": [
      {
        "carries_values_crosswalk": false,
        "status": 200,
        "url": "https://api.census.gov/data/2021/cbp/variables/EMPSZES.json"
      },
      {
        "carries_values_crosswalk": false,
        "status": 200,
        "url": "https://api.census.gov/data/2021/cbp/groups.json"
      },
      {
        "carries_values_crosswalk": false,
        "status": 200,
        "url": "https://api.census.gov/data/2021/cbp/groups/CB2100CBP.json"
      }
    ],
    "2022": [
      {
        "carries_values_crosswalk": false,
        "status": 200,
        "url": "https://api.census.gov/data/2022/cbp/variables/EMPSZES.json"
      },
      {
        "carries_values_crosswalk": false,
        "status": 200,
        "url": "https://api.census.gov/data/2022/cbp/groups.json"
      },
      {
        "carries_values_crosswalk": false,
        "status": 200,
        "url": "https://api.census.gov/data/2022/cbp/groups/CB2200CBP.json"
      }
    ],
    "2023": [
      {
        "carries_values_crosswalk": false,
        "status": 200,
        "url": "https://api.census.gov/data/2023/cbp/variables/EMPSZES.json"
      },
      {
        "carries_values_crosswalk": false,
        "status": 200,
        "url": "https://api.census.gov/data/2023/cbp/groups.json"
      },
      {
        "carries_values_crosswalk": false,
        "status": 200,
        "url": "https://api.census.gov/data/2023/cbp/groups/CB2300CBP.json"
      }
    ],
    "2024": null
  },
  "flag_values_by_year": {
    "2017": {
      "EMP_F": [
        "",
        "a"
      ],
      "EMP_N": [
        "0"
      ]
    },
    "2018": {
      "EMP_F": [
        ""
      ],
      "EMP_N": [
        "0"
      ]
    },
    "2019": {
      "EMP_F": [
        ""
      ],
      "EMP_N": [
        "0"
      ]
    },
    "2020": {
      "EMP_F": [
        ""
      ],
      "EMP_N": [
        "0"
      ]
    },
    "2021": {
      "EMP_F": [
        ""
      ],
      "EMP_N": [
        "0"
      ]
    },
    "2022": {
      "EMP_F": [
        ""
      ],
      "EMP_N": [
        "0"
      ]
    },
    "2023": {
      "EMP_F": [
        ""
      ],
      "EMP_N": [
        "0"
      ]
    },
    "2024": null
  },
  "geography_levels_by_year": {
    "2017": [
      "combined statistical area",
      "congressional district",
      "county",
      "metropolitan statistical area/micropolitan statistical area",
      "state",
      "us"
    ],
    "2018": [
      "combined statistical area",
      "congressional district",
      "county",
      "metropolitan statistical area/micropolitan statistical area",
      "state",
      "us",
      "zip code"
    ],
    "2019": [
      "combined statistical area",
      "congressional district",
      "county",
      "metropolitan statistical area/micropolitan statistical area",
      "state",
      "us",
      "zip code"
    ],
    "2020": [
      "combined statistical area",
      "congressional district",
      "county",
      "metropolitan statistical area/micropolitan statistical area",
      "state",
      "us",
      "zip code"
    ],
    "2021": [
      "combined statistical area",
      "congressional district",
      "county",
      "metropolitan statistical area/micropolitan statistical area",
      "state",
      "us",
      "zip code"
    ],
    "2022": [
      "combined statistical area",
      "congressional district",
      "county",
      "metropolitan statistical area/micropolitan statistical area",
      "state",
      "us",
      "zip code"
    ],
    "2023": [
      "combined statistical area",
      "congressional district",
      "county",
      "metropolitan statistical area/micropolitan statistical area",
      "state",
      "us",
      "zip code"
    ],
    "2024": null
  },
  "lfo_by_year": {
    "2017": null,
    "2018": null,
    "2019": null,
    "2020": null,
    "2021": null,
    "2022": null,
    "2023": null,
    "2024": null
  },
  "naics_predicate_by_year": {
    "2017": "NAICS2017",
    "2018": "NAICS2017",
    "2019": "NAICS2017",
    "2020": "NAICS2017",
    "2021": "NAICS2017",
    "2022": "NAICS2017",
    "2023": "NAICS2017",
    "2024": null
  },
  "notes": [
    "2017: EMPSZES official crosswalk found in metadata (44 codes) -- see empszes_metadata_crosswalk_probe_by_year for which route carried it",
    "2017: LFO exists as a variable for this vintage, but no attempt below selects LFO/LFO_LABEL as output columns (LFO is only ever used as the filter ='001' or omitted) -- lfo_by_year cannot be derived from this pull's rows even when a pull succeeds. A genuine LFO crosswalk would need a dedicated unfiltered LFO,LFO_LABEL query, which this script does not attempt.",
    "2018: LFO exists as a variable for this vintage, but no attempt below selects LFO/LFO_LABEL as output columns (LFO is only ever used as the filter ='001' or omitted) -- lfo_by_year cannot be derived from this pull's rows even when a pull succeeds. A genuine LFO crosswalk would need a dedicated unfiltered LFO,LFO_LABEL query, which this script does not attempt.",
    "2019: LFO exists as a variable for this vintage, but no attempt below selects LFO/LFO_LABEL as output columns (LFO is only ever used as the filter ='001' or omitted) -- lfo_by_year cannot be derived from this pull's rows even when a pull succeeds. A genuine LFO crosswalk would need a dedicated unfiltered LFO,LFO_LABEL query, which this script does not attempt.",
    "2020: LFO exists as a variable for this vintage, but no attempt below selects LFO/LFO_LABEL as output columns (LFO is only ever used as the filter ='001' or omitted) -- lfo_by_year cannot be derived from this pull's rows even when a pull succeeds. A genuine LFO crosswalk would need a dedicated unfiltered LFO,LFO_LABEL query, which this script does not attempt.",
    "2021: LFO exists as a variable for this vintage, but no attempt below selects LFO/LFO_LABEL as output columns (LFO is only ever used as the filter ='001' or omitted) -- lfo_by_year cannot be derived from this pull's rows even when a pull succeeds. A genuine LFO crosswalk would need a dedicated unfiltered LFO,LFO_LABEL query, which this script does not attempt.",
    "2022: LFO exists as a variable for this vintage, but no attempt below selects LFO/LFO_LABEL as output columns (LFO is only ever used as the filter ='001' or omitted) -- lfo_by_year cannot be derived from this pull's rows even when a pull succeeds. A genuine LFO crosswalk would need a dedicated unfiltered LFO,LFO_LABEL query, which this script does not attempt.",
    "2023: LFO exists as a variable for this vintage, but no attempt below selects LFO/LFO_LABEL as output columns (LFO is only ever used as the filter ='001' or omitted) -- lfo_by_year cannot be derived from this pull's rows even when a pull succeeds. A genuine LFO crosswalk would need a dedicated unfiltered LFO,LFO_LABEL query, which this script does not attempt.",
    "2024: not in years_available -- cbp.json returned HTTP 404 for this year, not 200; every other finding for 2024 is null."
  ],
  "rows_113310_by_year": {
    "2017": 188,
    "2018": 190,
    "2019": 186,
    "2020": 182,
    "2021": 185,
    "2022": 179,
    "2023": 188,
    "2024": null
  },
  "working_query_by_year": {
    "2017": {
      "LFO": "001",
      "NAICS2017": "113310",
      "for": "state:*",
      "get": "NAME,NAICS2017_LABEL,EMPSZES,EMPSZES_LABEL,ESTAB,EMP,EMP_F,EMP_N",
      "size_crossing_available": true
    },
    "2018": {
      "LFO": "001",
      "NAICS2017": "113310",
      "for": "state:*",
      "get": "NAME,NAICS2017_LABEL,EMPSZES,EMPSZES_LABEL,ESTAB,EMP,EMP_F,EMP_N",
      "size_crossing_available": true
    },
    "2019": {
      "LFO": "001",
      "NAICS2017": "113310",
      "for": "state:*",
      "get": "NAME,NAICS2017_LABEL,EMPSZES,EMPSZES_LABEL,ESTAB,EMP,EMP_F,EMP_N",
      "size_crossing_available": true
    },
    "2020": {
      "LFO": "001",
      "NAICS2017": "113310",
      "for": "state:*",
      "get": "NAME,NAICS2017_LABEL,EMPSZES,EMPSZES_LABEL,ESTAB,EMP,EMP_F,EMP_N",
      "size_crossing_available": true
    },
    "2021": {
      "LFO": "001",
      "NAICS2017": "113310",
      "for": "state:*",
      "get": "NAME,NAICS2017_LABEL,EMPSZES,EMPSZES_LABEL,ESTAB,EMP,EMP_F,EMP_N",
      "size_crossing_available": true
    },
    "2022": {
      "LFO": "001",
      "NAICS2017": "113310",
      "for": "state:*",
      "get": "NAME,NAICS2017_LABEL,EMPSZES,EMPSZES_LABEL,ESTAB,EMP,EMP_F,EMP_N",
      "size_crossing_available": true
    },
    "2023": {
      "LFO": "001",
      "NAICS2017": "113310",
      "for": "state:*",
      "get": "NAME,NAICS2017_LABEL,EMPSZES,EMPSZES_LABEL,ESTAB,EMP,EMP_F,EMP_N",
      "size_crossing_available": true
    },
    "2024": null
  },
  "years_available": [
    2017,
    2018,
    2019,
    2020,
    2021,
    2022,
    2023
  ]
}
```

_Extracts: 64; summary `generated_utc` 2026-09-04T14:06:01+00:00._

### `cbp_regime`

**access**:

```json
{
  "reason": null,
  "route": "https://www.census.gov/programs-surveys/cbp/technical-documentation/methodology.html; https://www.census.gov/programs-surveys/cbp/technical-documentation.html; https://www.census.gov/programs-surveys/cbp/technical-documentation/records-layouts.html; https://www.census.gov/programs-surveys/cbp/technical-documentation/record-layouts.html; https://www2.census.gov/programs-surveys/cbp/technical-documentation/records-layouts/2017_record_layouts/state_layout_2017.txt; https://www2.census.gov/programs-surveys/cbp/technical-documentation/records-layouts/noise-layout/state_x_lfo_layout.txt",
  "status": "verified"
}
```

**coverage_span**:

```json
{
  "covered": "2017-2023",
  "published_end": "2023",
  "published_start": "2017",
  "uncovered": "2024",
  "window_end": "2024-12",
  "window_start": "2017-01"
}
```

**findings**:

```json
{
  "documentation_fetched": [
    {
      "http_status": 200,
      "url": "https://www.census.gov/programs-surveys/cbp/technical-documentation/methodology.html"
    },
    {
      "http_status": 200,
      "url": "https://www.census.gov/programs-surveys/cbp/technical-documentation.html"
    },
    {
      "http_status": 404,
      "url": "https://www.census.gov/programs-surveys/cbp/technical-documentation/records-layouts.html"
    },
    {
      "http_status": 200,
      "url": "https://www.census.gov/programs-surveys/cbp/technical-documentation/record-layouts.html"
    },
    {
      "http_status": 200,
      "url": "https://www2.census.gov/programs-surveys/cbp/technical-documentation/records-layouts/2017_record_layouts/state_layout_2017.txt"
    },
    {
      "http_status": 200,
      "url": "https://www2.census.gov/programs-surveys/cbp/technical-documentation/records-layouts/noise-layout/state_x_lfo_layout.txt"
    }
  ],
  "emp_flag_variable_definitions_by_year": {
    "2017": {
      "EMP": {
        "attribute_of": null,
        "attribute_type": null,
        "has_values_crosswalk": false,
        "label": "Number of employees"
      },
      "EMP_F": {
        "attribute_of": "EMP",
        "attribute_type": "FLAG",
        "has_values_crosswalk": false,
        "label": "Flag for number of employees"
      },
      "EMP_N": {
        "attribute_of": null,
        "attribute_type": null,
        "has_values_crosswalk": false,
        "label": "Noise range for number of paid employees for pay period including March 12"
      },
      "EMP_N_F": {
        "attribute_of": "EMP_N",
        "attribute_type": "FLAG",
        "has_values_crosswalk": false,
        "label": "Flag for Noise range for paid employees for pay period including March 12"
      }
    },
    "2018": {
      "EMP": {
        "attribute_of": null,
        "attribute_type": null,
        "has_values_crosswalk": false,
        "label": "Number of employees"
      },
      "EMP_F": {
        "attribute_of": "EMP",
        "attribute_type": "FLAG",
        "has_values_crosswalk": false,
        "label": "Flag for number of employees"
      },
      "EMP_N": {
        "attribute_of": null,
        "attribute_type": null,
        "has_values_crosswalk": false,
        "label": "Noise range for number of employees"
      },
      "EMP_N_F": {
        "attribute_of": "EMP_N",
        "attribute_type": "FLAG",
        "has_values_crosswalk": false,
        "label": "Flag for Noise range for number of employees"
      }
    },
    "2019": {
      "EMP": {
        "attribute_of": null,
        "attribute_type": null,
        "has_values_crosswalk": false,
        "label": "Number of employees"
      },
      "EMP_F": {
        "attribute_of": "EMP",
        "attribute_type": "FLAG",
        "has_values_crosswalk": false,
        "label": "Flag for number of employees"
      },
      "EMP_N": {
        "attribute_of": null,
        "attribute_type": null,
        "has_values_crosswalk": false,
        "label": "Noise range for number of employees"
      },
      "EMP_N_F": {
        "attribute_of": "EMP_N",
        "attribute_type": "FLAG",
        "has_values_crosswalk": false,
        "label": "Flag for Noise range for number of employees"
      }
    },
    "2020": {
      "EMP": {
        "attribute_of": null,
        "attribute_type": null,
        "has_values_crosswalk": false,
        "label": "Number of employees"
      },
      "EMP_F": {
        "attribute_of": "EMP",
        "attribute_type": "FLAG",
        "has_values_crosswalk": false,
        "label": "Flag for number of employees"
      },
      "EMP_N": {
        "attribute_of": null,
        "attribute_type": null,
        "has_values_crosswalk": false,
        "label": "Noise range for number of employees"
      },
      "EMP_N_F": {
        "attribute_of": "EMP_N",
        "attribute_type": "FLAG",
        "has_values_crosswalk": false,
        "label": "Flag for Noise range for number of employees"
      }
    },
    "2021": {
      "EMP": {
        "attribute_of": null,
        "attribute_type": null,
        "has_values_crosswalk": false,
        "label": "Number of employees"
      },
      "EMP_F": {
        "attribute_of": "EMP",
        "attribute_type": "FLAG",
        "has_values_crosswalk": false,
        "label": "Flag for number of employees"
      },
      "EMP_N": {
        "attribute_of": null,
        "attribute_type": null,
        "has_values_crosswalk": false,
        "label": "Noise range for number of employees"
      },
      "EMP_N_F": {
        "attribute_of": "EMP_N",
        "attribute_type": "FLAG",
        "has_values_crosswalk": false,
        "label": "Flag for Noise range for number of employees"
      }
    },
    "2022": {
      "EMP": {
        "attribute_of": null,
        "attribute_type": null,
        "has_values_crosswalk": false,
        "label": "Number of employees"
      },
      "EMP_F": {
        "attribute_of": "EMP",
        "attribute_type": "FLAG",
        "has_values_crosswalk": false,
        "label": "Flag for number of employees"
      },
      "EMP_N": {
        "attribute_of": null,
        "attribute_type": null,
        "has_values_crosswalk": false,
        "label": "Noise range for number of employees"
      },
      "EMP_N_F": {
        "attribute_of": "EMP_N",
        "attribute_type": "FLAG",
        "has_values_crosswalk": false,
        "label": "Flag for Noise range for number of employees"
      }
    },
    "2023": {
      "EMP": {
        "attribute_of": null,
        "attribute_type": null,
        "has_values_crosswalk": false,
        "label": "Number of employees"
      },
      "EMP_F": {
        "attribute_of": "EMP",
        "attribute_type": "FLAG",
        "has_values_crosswalk": false,
        "label": "Flag for number of employees"
      },
      "EMP_N": {
        "attribute_of": null,
        "attribute_type": null,
        "has_values_crosswalk": false,
        "label": "Noise range for number of employees"
      },
      "EMP_N_F": {
        "attribute_of": "EMP_N",
        "attribute_type": "FLAG",
        "has_values_crosswalk": false,
        "label": "Flag for Noise range for number of employees"
      }
    },
    "2024": null
  },
  "emp_n_f_caveat": "EMP_N_F (labelled 'Flag for Noise range for number of employees' in this run's fetched variable metadata) is CBP's actual per-cell noise-magnitude flag (documented in methodology.html's Noise Infusion section as low/moderate/high, G/H/J) -- distinct from EMP_N, which is labelled 'Noise range for number of employees' and is int-typed, not the flag itself. EMP_N_F does not appear in any year's 113310 x state response header this run (Task 7's query never selected it as an output column). Every observed EMP_N value in every year's extract this run is the literal string '0'. emp_n_present_and_nonzero_share in flag_evidence_by_year therefore measures only 'EMP_N present and not the string 0', not the published noise-flag distribution, and must not be read as evidence that no noise was applied in a year labelled noise_infusion above -- the regime label does not rest on this share.",
  "flag_evidence_by_year": {
    "2017": {
      "EMP_F": {
        "a": 4,
        "null": 184
      },
      "EMP_N": {
        "0": 188
      },
      "emp_n_f_in_response": false,
      "emp_n_present_and_nonzero_share": 0.0,
      "suppressed_share": 0.02127659574468085
    },
    "2018": {
      "EMP_F": {
        "null": 190
      },
      "EMP_N": {
        "0": 190
      },
      "emp_n_f_in_response": false,
      "emp_n_present_and_nonzero_share": 0.0,
      "suppressed_share": 0.0
    },
    "2019": {
      "EMP_F": {
        "null": 186
      },
      "EMP_N": {
        "0": 186
      },
      "emp_n_f_in_response": false,
      "emp_n_present_and_nonzero_share": 0.0,
      "suppressed_share": 0.0
    },
    "2020": {
      "EMP_F": {
        "null": 182
      },
      "EMP_N": {
        "0": 182
      },
      "emp_n_f_in_response": false,
      "emp_n_present_and_nonzero_share": 0.0,
      "suppressed_share": 0.0
    },
    "2021": {
      "EMP_F": {
        "null": 185
      },
      "EMP_N": {
        "0": 185
      },
      "emp_n_f_in_response": false,
      "emp_n_present_and_nonzero_share": 0.0,
      "suppressed_share": 0.0
    },
    "2022": {
      "EMP_F": {
        "null": 179
      },
      "EMP_N": {
        "0": 179
      },
      "emp_n_f_in_response": false,
      "emp_n_present_and_nonzero_share": 0.0,
      "suppressed_share": 0.0
    },
    "2023": {
      "EMP_F": {
        "null": 188
      },
      "EMP_N": {
        "0": 188
      },
      "emp_n_f_in_response": false,
      "emp_n_present_and_nonzero_share": 0.0,
      "suppressed_share": 0.0
    },
    "2024": null
  },
  "regime_by_year": {
    "2017": {
      "citation": "https://www.census.gov/programs-surveys/cbp/technical-documentation/methodology.html -- section 'Protecting Confidentiality > Noise Infusion'",
      "evidence": "2017: fetched methodology.html (section 'Protecting Confidentiality > Noise Infusion') states CBP has used noise infusion since reference year 2007, and separately that reference year 2017 was the last year the EMPFLAG employment-size-range suppression flag was used ('The use of EMPFLAG was discontinued beginning in reference year 2018') and the first year a cell with fewer than three establishments is dropped from the release rather than published with a flag ('Beginning with reference year 2017, a cell is only published if it contains three or more establishments'). Both a noise-infusion mechanism and an EMPFLAG-based suppression mechanism are therefore documented as active for 2017, distinguishing it from every later window year. Corroborated by the year-specific layout fetched this run at https://www2.census.gov/programs-surveys/cbp/technical-documentation/records-layouts/2017_record_layouts/state_layout_2017.txt, which documents both EMPFLAG (size-range suppression codes A-M, plus 'S' for below-publication-standard withholding) and per-cell noise flags (G/H/J/N/S) as live fields on the state-by-NAICS file for this year. The 2017 113310 x state extract carries a small minority of rows with EMP_F == 'a' and no flag on the rest (a lowercase employment-size-range code, consistent with the fetched noise-layout state_x_lfo record layout's a=0-19-employee scheme; exact counts are in flag_evidence_by_year['2017'], computed fresh this run, not restated here as a number that could go stale against this static entry) -- reported as corroborating detail only, not as the basis for this regime label; the label rests on the two Census documents named above, not on this count.",
      "regime": "noise_infusion_plus_suppression"
    },
    "2018": {
      "citation": "https://www.census.gov/programs-surveys/cbp/technical-documentation/methodology.html -- section 'Protecting Confidentiality > Noise Infusion'",
      "evidence": "2018: the same methodology.html passage cited for 2017 states 'The use of EMPFLAG was discontinued beginning in reference year 2018 and a noisy employment cell value is provided' -- naming 2018 explicitly as the year the EMPFLAG suppression flag stopped, leaving noise infusion (documented active continuously since reference year 2007) as the sole per-cell disclosure mechanism the page names for published cells from 2018 forward. The beginning-2017 rule dropping cells with fewer than three establishments from the release is not stated to have changed and remains documented as active. Every row of the 2018 113310 x state extract carries EMP_F == null (see flag_evidence_by_year['2018'], computed fresh this run), consistent with EMPFLAG's documented discontinuation -- reported as corroborating detail only, not as the basis for this label.",
      "regime": "noise_infusion"
    },
    "2019": {
      "citation": "https://www.census.gov/programs-surveys/cbp/technical-documentation/methodology.html -- section 'Protecting Confidentiality > Noise Infusion'",
      "evidence": "No CBP documentation specific to reference year 2019 was found among the routes this script's own DOC_URLS fetches (see documentation_fetched -- only 2017 has a year-specific record-layout URL in that list). Additional manual verification while authoring this entry (live GETs against the Census record-layouts naming pattern for every window year, outside this script's own fetch list) found that unlike 2017, no year-labeled record-layout file for 2019 is archived at the Census record-layouts index at all: only 2017, 2018 and 2020 have one, and the 2018 and 2020 files describe the state ALL-NAICS-totals product rather than the state-by-NAICS product this task's own extracts use, so neither would have corroborated a NAICS-level regime for its own year even if it had been in scope. This entry therefore rests entirely on methodology.html's continuing statements -- noise infusion 'since reference year 2007' and EMPFLAG discontinued 'beginning in reference year 2018' -- read forward through 2019 with no later documented reversal found. methodology.html itself carries a banner, current as of its own June 18, 2026 revision, stating its content 'is no longer current' pending a U.S. Department of Commerce administrative order prohibiting the use of noise infusion -- a fact that by itself already means 2019's label carries less independent corroboration than 2017's or 2018's and should be weighted accordingly, not read as equally certain, regardless of how the banner's own scope is read. INFERENCE MARKER, OPENING: what follows to the closing marker is this auditor's own reading of that banner's scope, not a distinction the banner's text itself draws -- it carries no extract hash and is re-checked by no later run. The banner is read here as concerning Census's prospective/current approach following the recent order, not as a retraction of the dated 2007-2018 historical statements this entry relies on; a different reading, under which the banner casts doubt on those historical statements too, would leave this entry with no documentary basis at all and 2019 would have to be unknown instead. INFERENCE MARKER, CLOSING.",
      "regime": "noise_infusion"
    },
    "2020": {
      "citation": "https://www.census.gov/programs-surveys/cbp/technical-documentation/methodology.html -- section 'Protecting Confidentiality > Noise Infusion'",
      "evidence": "No CBP documentation specific to reference year 2020 was found among the routes this script's own DOC_URLS fetches (see documentation_fetched -- only 2017 has a year-specific record-layout URL in that list). Additional manual verification while authoring this entry (live GETs against the Census record-layouts naming pattern for every window year, outside this script's own fetch list) found that a 2020-labeled record-layout file is archived at the Census record-layouts index, but it describes the state ALL-NAICS-totals product rather than the state-by-NAICS product this task's own extracts use, so it does not corroborate a NAICS-level regime for 2020. The same is true of 2018's year-labeled file; only 2017 has a year-specific file of the right product; and 2019, 2021, 2022 and 2023 have no year-labeled file of either product at all. This entry therefore rests entirely on methodology.html's continuing statements -- noise infusion 'since reference year 2007' and EMPFLAG discontinued 'beginning in reference year 2018' -- read forward through 2020 with no later documented reversal found. methodology.html itself carries a banner, current as of its own June 18, 2026 revision, stating its content 'is no longer current' pending a U.S. Department of Commerce administrative order prohibiting the use of noise infusion -- a fact that by itself already means 2020's label carries less independent corroboration than 2017's or 2018's and should be weighted accordingly, not read as equally certain, regardless of how the banner's own scope is read. INFERENCE MARKER, OPENING: what follows to the closing marker is this auditor's own reading of that banner's scope, not a distinction the banner's text itself draws -- it carries no extract hash and is re-checked by no later run. The banner is read here as concerning Census's prospective/current approach following the recent order, not as a retraction of the dated 2007-2018 historical statements this entry relies on; a different reading, under which the banner casts doubt on those historical statements too, would leave this entry with no documentary basis at all and 2020 would have to be unknown instead. INFERENCE MARKER, CLOSING.",
      "regime": "noise_infusion"
    },
    "2021": {
      "citation": "https://www.census.gov/programs-surveys/cbp/technical-documentation/methodology.html -- section 'Protecting Confidentiality > Noise Infusion'",
      "evidence": "No CBP documentation specific to reference year 2021 was found among the routes this script's own DOC_URLS fetches (see documentation_fetched -- only 2017 has a year-specific record-layout URL in that list). Additional manual verification while authoring this entry (live GETs against the Census record-layouts naming pattern for every window year, outside this script's own fetch list) found that unlike 2017, no year-labeled record-layout file for 2021 is archived at the Census record-layouts index at all: only 2017, 2018 and 2020 have one, and the 2018 and 2020 files describe the state ALL-NAICS-totals product rather than the state-by-NAICS product this task's own extracts use, so neither would have corroborated a NAICS-level regime for its own year even if it had been in scope. This entry therefore rests entirely on methodology.html's continuing statements -- noise infusion 'since reference year 2007' and EMPFLAG discontinued 'beginning in reference year 2018' -- read forward through 2021 with no later documented reversal found. methodology.html itself carries a banner, current as of its own June 18, 2026 revision, stating its content 'is no longer current' pending a U.S. Department of Commerce administrative order prohibiting the use of noise infusion -- a fact that by itself already means 2021's label carries less independent corroboration than 2017's or 2018's and should be weighted accordingly, not read as equally certain, regardless of how the banner's own scope is read. INFERENCE MARKER, OPENING: what follows to the closing marker is this auditor's own reading of that banner's scope, not a distinction the banner's text itself draws -- it carries no extract hash and is re-checked by no later run. The banner is read here as concerning Census's prospective/current approach following the recent order, not as a retraction of the dated 2007-2018 historical statements this entry relies on; a different reading, under which the banner casts doubt on those historical statements too, would leave this entry with no documentary basis at all and 2021 would have to be unknown instead. INFERENCE MARKER, CLOSING.",
      "regime": "noise_infusion"
    },
    "2022": {
      "citation": "https://www.census.gov/programs-surveys/cbp/technical-documentation/methodology.html -- section 'Protecting Confidentiality > Noise Infusion'",
      "evidence": "No CBP documentation specific to reference year 2022 was found among the routes this script's own DOC_URLS fetches (see documentation_fetched -- only 2017 has a year-specific record-layout URL in that list). Additional manual verification while authoring this entry (live GETs against the Census record-layouts naming pattern for every window year, outside this script's own fetch list) found that unlike 2017, no year-labeled record-layout file for 2022 is archived at the Census record-layouts index at all: only 2017, 2018 and 2020 have one, and the 2018 and 2020 files describe the state ALL-NAICS-totals product rather than the state-by-NAICS product this task's own extracts use, so neither would have corroborated a NAICS-level regime for its own year even if it had been in scope. This entry therefore rests entirely on methodology.html's continuing statements -- noise infusion 'since reference year 2007' and EMPFLAG discontinued 'beginning in reference year 2018' -- read forward through 2022 with no later documented reversal found. methodology.html itself carries a banner, current as of its own June 18, 2026 revision, stating its content 'is no longer current' pending a U.S. Department of Commerce administrative order prohibiting the use of noise infusion -- a fact that by itself already means 2022's label carries less independent corroboration than 2017's or 2018's and should be weighted accordingly, not read as equally certain, regardless of how the banner's own scope is read. INFERENCE MARKER, OPENING: what follows to the closing marker is this auditor's own reading of that banner's scope, not a distinction the banner's text itself draws -- it carries no extract hash and is re-checked by no later run. The banner is read here as concerning Census's prospective/current approach following the recent order, not as a retraction of the dated 2007-2018 historical statements this entry relies on; a different reading, under which the banner casts doubt on those historical statements too, would leave this entry with no documentary basis at all and 2022 would have to be unknown instead. INFERENCE MARKER, CLOSING.",
      "regime": "noise_infusion"
    },
    "2023": {
      "citation": "https://www.census.gov/programs-surveys/cbp/technical-documentation/methodology.html -- section 'Protecting Confidentiality > Noise Infusion'",
      "evidence": "No CBP documentation specific to reference year 2023 was found among the routes this script's own DOC_URLS fetches (see documentation_fetched -- only 2017 has a year-specific record-layout URL in that list). Additional manual verification while authoring this entry (live GETs against the Census record-layouts naming pattern for every window year, outside this script's own fetch list) found that unlike 2017, no year-labeled record-layout file for 2023 is archived at the Census record-layouts index at all: only 2017, 2018 and 2020 have one, and the 2018 and 2020 files describe the state ALL-NAICS-totals product rather than the state-by-NAICS product this task's own extracts use, so neither would have corroborated a NAICS-level regime for its own year even if it had been in scope. This entry therefore rests entirely on methodology.html's continuing statements -- noise infusion 'since reference year 2007' and EMPFLAG discontinued 'beginning in reference year 2018' -- read forward through 2023 with no later documented reversal found. methodology.html itself carries a banner, current as of its own June 18, 2026 revision, stating its content 'is no longer current' pending a U.S. Department of Commerce administrative order prohibiting the use of noise infusion -- a fact that by itself already means 2023's label carries less independent corroboration than 2017's or 2018's and should be weighted accordingly, not read as equally certain, regardless of how the banner's own scope is read. INFERENCE MARKER, OPENING: what follows to the closing marker is this auditor's own reading of that banner's scope, not a distinction the banner's text itself draws -- it carries no extract hash and is re-checked by no later run. The banner is read here as concerning Census's prospective/current approach following the recent order, not as a retraction of the dated 2007-2018 historical statements this entry relies on; a different reading, under which the banner casts doubt on those historical statements too, would leave this entry with no documentary basis at all and 2023 would have to be unknown instead. INFERENCE MARKER, CLOSING.",
      "regime": "noise_infusion"
    },
    "2024": {
      "citation": "",
      "evidence": "2024: not obtainable -- cbp_metadata's own dataset probe (dataset_probe_status_by_year) recorded a non-200 status for reference year 2024 and 2024 is absent from years_available; Task 7's report identifies this as a real HTTP 404 from cbp.json, not a transport blip. No 2024 CBP dataset exists to fetch a 2024-specific disclosure-methodology statement from, and the documentation fetched this run for 2017-2023 cannot be assumed to cover a year that postdates it: methodology.html's own banner (current as of its June 18, 2026 revision) states its regime description 'is no longer current' pending a U.S. Department of Commerce administrative order prohibiting the use of noise infusion, so even a hypothetical future 2024 release cannot be assumed to carry forward the 2018-2023 regime found above.",
      "regime": "unknown"
    }
  },
  "unknown_years": [
    2024
  ]
}
```

_Extracts: 33; summary `generated_utc` 2026-09-04T16:25:37+00:00._

### `ces`

**access**:

```json
{
  "reason": null,
  "route": "https://download.bls.gov/pub/time.series/sm/<file>",
  "status": "verified"
}
```

**coverage_span**:

```json
{
  "covered": "2017-01-2024-12 for states with a qualifying series — verified at month grain, not assumed, from every qualifying series' own begin_year/begin_period and end_year/end_period: every one of the 101 qualifying series begins at or before 2017-01 (latest start observed, at month grain via begin_year/begin_period: 2009-01) and ends at or after 2024-12 (earliest end observed, via end_year/end_period: 2026-07), so the full D1 window 2017-01-2024-12 is covered wherever a qualifying series exists, verified at month grain, not merely at the year-level overlap qualifying_series filters on",
  "published_end": "2026",
  "published_start": "1990",
  "uncovered": "6 sm.state code(s) publish no Logging-related statewide all-employees series overlapping the window, of which 3 are D1 'states_dc' jurisdictions (see states_dc_tally and non_state_codes for the rest of the denominator)",
  "window_end": "2024-12",
  "window_start": "2017-01"
}
```

**findings**:

```json
{
  "derived_codes": {
    "all_employees_data_type": "01",
    "statewide_area": "00000"
  },
  "excluded_broader_codes": [
    {
      "industry_code": "15000000",
      "industry_name": "Mining, Logging and Construction"
    }
  ],
  "logging_industry_codes": [
    {
      "embedded_naics": "",
      "industry_code": "10000000",
      "industry_name": "Mining and Logging",
      "level": "supersector"
    },
    {
      "embedded_naics": "1133",
      "industry_code": "10113300",
      "industry_name": "Logging",
      "level": "1133"
    }
  ],
  "near_miss_sm_state_codes": [
    {
      "industry_code": "15000000",
      "series_id": "SMS10000001500000001",
      "state_code": "10"
    },
    {
      "industry_code": "15000000",
      "series_id": "SMU10000001500000001",
      "state_code": "10"
    },
    {
      "industry_code": "15000000",
      "series_id": "SMS11000001500000001",
      "state_code": "11"
    },
    {
      "industry_code": "15000000",
      "series_id": "SMU11000001500000001",
      "state_code": "11"
    },
    {
      "industry_code": "15000000",
      "series_id": "SMS15000001500000001",
      "state_code": "15"
    },
    {
      "industry_code": "15000000",
      "series_id": "SMU15000001500000001",
      "state_code": "15"
    },
    {
      "industry_code": "15000000",
      "series_id": "SMS78000001500000001",
      "state_code": "78"
    },
    {
      "industry_code": "15000000",
      "series_id": "SMU78000001500000001",
      "state_code": "78"
    }
  ],
  "non_state_codes": [
    {
      "code": "00",
      "name": "All States"
    },
    {
      "code": "72",
      "name": "Puerto Rico"
    },
    {
      "code": "78",
      "name": "Virgin Islands"
    },
    {
      "code": "99",
      "name": "All Metropolitan Statistical Areas"
    }
  ],
  "notes": "The six states_with_* counts below sum to 55, the number of codes in the fetched sm.state file, not 51 — sm.state also carries 00 ('All States'); 72 ('Puerto Rico'); 78 ('Virgin Islands'); 99 ('All Metropolitan Statistical Areas'), none of which is a D1 'states_dc' jurisdiction. Restricted to D1's own geography_universe ('states_dc', the 51 codes in c.STATES_DC_FIPS, also recorded in the states_dc_tally finding): 113310: 0, 1133: 4, 113: 0, supersector: 44, other: 0, none: 3. Excluded from the target industry codes because their titles merely mention 'logging' without being embedded-NAICS-113-prefixed or exactly titled 'Mining and Logging': 15000000 ('Mining, Logging and Construction'). sm.state codes 10, 11, 15, 78 publish a D1-window-overlapping statewide all-employees series only at one of these excluded codes — an unanchored substring match on 'logging' would have promoted them from 'none' to 'supersector', which is not what the fetched sm.industry file actually supports for them. The fetched sm.industry file defines no SAE industry code at the NAICS 5- or 6-digit depth for Logging at all — the Logging-related code(s) it defines below the supersector, this run: 10113300 (1133) (see logging_industry_codes). states_with_113310 is 0 because CES/SAE itself stops short of 113310 for every state, not because some state declines to publish at a level that exists.",
  "publication_level_by_sm_state_code": {
    "00": "none",
    "01": "supersector",
    "02": "supersector",
    "04": "supersector",
    "05": "supersector",
    "06": "1133",
    "08": "supersector",
    "09": "supersector",
    "10": "none",
    "11": "none",
    "12": "supersector",
    "13": "supersector",
    "15": "none",
    "16": "supersector",
    "17": "supersector",
    "18": "supersector",
    "19": "supersector",
    "20": "supersector",
    "21": "supersector",
    "22": "supersector",
    "23": "1133",
    "24": "supersector",
    "25": "supersector",
    "26": "supersector",
    "27": "supersector",
    "28": "supersector",
    "29": "supersector",
    "30": "supersector",
    "31": "supersector",
    "32": "supersector",
    "33": "supersector",
    "34": "supersector",
    "35": "supersector",
    "36": "supersector",
    "37": "supersector",
    "38": "supersector",
    "39": "supersector",
    "40": "supersector",
    "41": "1133",
    "42": "supersector",
    "44": "supersector",
    "45": "supersector",
    "46": "supersector",
    "47": "supersector",
    "48": "supersector",
    "49": "supersector",
    "50": "supersector",
    "51": "supersector",
    "53": "1133",
    "54": "supersector",
    "55": "supersector",
    "56": "supersector",
    "72": "supersector",
    "78": "none",
    "99": "none"
  },
  "series_by_state": {
    "01": [
      {
        "begin_year": 1990,
        "end_year": 2026,
        "industry_code": "10000000",
        "level": "supersector",
        "series_id": "SMS01000001000000001"
      },
      {
        "begin_year": 1990,
        "end_year": 2026,
        "industry_code": "10000000",
        "level": "supersector",
        "series_id": "SMU01000001000000001"
      }
    ],
    "02": [
      {
        "begin_year": 1990,
        "end_year": 2026,
        "industry_code": "10000000",
        "level": "supersector",
        "series_id": "SMS02000001000000001"
      },
      {
        "begin_year": 1990,
        "end_year": 2026,
        "industry_code": "10000000",
        "level": "supersector",
        "series_id": "SMU02000001000000001"
      }
    ],
    "04": [
      {
        "begin_year": 1990,
        "end_year": 2026,
        "industry_code": "10000000",
        "level": "supersector",
        "series_id": "SMS04000001000000001"
      },
      {
        "begin_year": 1990,
        "end_year": 2026,
        "industry_code": "10000000",
        "level": "supersector",
        "series_id": "SMU04000001000000001"
      }
    ],
    "05": [
      {
        "begin_year": 1990,
        "end_year": 2026,
        "industry_code": "10000000",
        "level": "supersector",
        "series_id": "SMS05000001000000001"
      },
      {
        "begin_year": 1990,
        "end_year": 2026,
        "industry_code": "10000000",
        "level": "supersector",
        "series_id": "SMU05000001000000001"
      }
    ],
    "06": [
      {
        "begin_year": 1990,
        "end_year": 2026,
        "industry_code": "10000000",
        "level": "supersector",
        "series_id": "SMS06000001000000001"
      },
      {
        "begin_year": 1990,
        "end_year": 2026,
        "industry_code": "10000000",
        "level": "supersector",
        "series_id": "SMU06000001000000001"
      },
      {
        "begin_year": 1990,
        "end_year": 2026,
        "industry_code": "10113300",
        "level": "1133",
        "series_id": "SMU06000001011330001"
      }
    ],
    "08": [
      {
        "begin_year": 1990,
        "end_year": 2026,
        "industry_code": "10000000",
        "level": "supersector",
        "series_id": "SMS08000001000000001"
      },
      {
        "begin_year": 1990,
        "end_year": 2026,
        "industry_code": "10000000",
        "level": "supersector",
        "series_id": "SMU08000001000000001"
      }
    ],
    "09": [
      {
        "begin_year": 1990,
        "end_year": 2026,
        "industry_code": "10000000",
        "level": "supersector",
        "series_id": "SMS09000001000000001"
      },
      {
        "begin_year": 1990,
        "end_year": 2026,
        "industry_code": "10000000",
        "level": "supersector",
        "series_id": "SMU09000001000000001"
      }
    ],
    "12": [
      {
        "begin_year": 2002,
        "end_year": 2026,
        "industry_code": "10000000",
        "level": "supersector",
        "series_id": "SMU12000001000000001"
      }
    ],
    "13": [
      {
        "begin_year": 1990,
        "end_year": 2026,
        "industry_code": "10000000",
        "level": "supersector",
        "series_id": "SMS13000001000000001"
      },
      {
        "begin_year": 1990,
        "end_year": 2026,
        "industry_code": "10000000",
        "level": "supersector",
        "series_id": "SMU13000001000000001"
      }
    ],
    "16": [
      {
        "begin_year": 1990,
        "end_year": 2026,
        "industry_code": "10000000",
        "level": "supersector",
        "series_id": "SMS16000001000000001"
      },
      {
        "begin_year": 1990,
        "end_year": 2026,
        "industry_code": "10000000",
        "level": "supersector",
        "series_id": "SMU16000001000000001"
      }
    ],
    "17": [
      {
        "begin_year": 1990,
        "end_year": 2026,
        "industry_code": "10000000",
        "level": "supersector",
        "series_id": "SMS17000001000000001"
      },
      {
        "begin_year": 1990,
        "end_year": 2026,
        "industry_code": "10000000",
        "level": "supersector",
        "series_id": "SMU17000001000000001"
      }
    ],
    "18": [
      {
        "begin_year": 1990,
        "end_year": 2026,
        "industry_code": "10000000",
        "level": "supersector",
        "series_id": "SMS18000001000000001"
      },
      {
        "begin_year": 1990,
        "end_year": 2026,
        "industry_code": "10000000",
        "level": "supersector",
        "series_id": "SMU18000001000000001"
      }
    ],
    "19": [
      {
        "begin_year": 1990,
        "end_year": 2026,
        "industry_code": "10000000",
        "level": "supersector",
        "series_id": "SMS19000001000000001"
      },
      {
        "begin_year": 1990,
        "end_year": 2026,
        "industry_code": "10000000",
        "level": "supersector",
        "series_id": "SMU19000001000000001"
      }
    ],
    "20": [
      {
        "begin_year": 1990,
        "end_year": 2026,
        "industry_code": "10000000",
        "level": "supersector",
        "series_id": "SMS20000001000000001"
      },
      {
        "begin_year": 1990,
        "end_year": 2026,
        "industry_code": "10000000",
        "level": "supersector",
        "series_id": "SMU20000001000000001"
      }
    ],
    "21": [
      {
        "begin_year": 1990,
        "end_year": 2026,
        "industry_code": "10000000",
        "level": "supersector",
        "series_id": "SMS21000001000000001"
      },
      {
        "begin_year": 1990,
        "end_year": 2026,
        "industry_code": "10000000",
        "level": "supersector",
        "series_id": "SMU21000001000000001"
      }
    ],
    "22": [
      {
        "begin_year": 1990,
        "end_year": 2026,
        "industry_code": "10000000",
        "level": "supersector",
        "series_id": "SMS22000001000000001"
      },
      {
        "begin_year": 1990,
        "end_year": 2026,
        "industry_code": "10000000",
        "level": "supersector",
        "series_id": "SMU22000001000000001"
      }
    ],
    "23": [
      {
        "begin_year": 1990,
        "end_year": 2026,
        "industry_code": "10000000",
        "level": "supersector",
        "series_id": "SMS23000001000000001"
      },
      {
        "begin_year": 1990,
        "end_year": 2026,
        "industry_code": "10000000",
        "level": "supersector",
        "series_id": "SMU23000001000000001"
      },
      {
        "begin_year": 1990,
        "end_year": 2026,
        "industry_code": "10113300",
        "level": "1133",
        "series_id": "SMU23000001011330001"
      }
    ],
    "24": [
      {
        "begin_year": 1990,
        "end_year": 2026,
        "industry_code": "10000000",
        "level": "supersector",
        "series_id": "SMS24000001000000001"
      },
      {
        "begin_year": 1990,
        "end_year": 2026,
        "industry_code": "10000000",
        "level": "supersector",
        "series_id": "SMU24000001000000001"
      }
    ],
    "25": [
      {
        "begin_year": 1990,
        "end_year": 2026,
        "industry_code": "10000000",
        "level": "supersector",
        "series_id": "SMS25000001000000001"
      },
      {
        "begin_year": 1990,
        "end_year": 2026,
        "industry_code": "10000000",
        "level": "supersector",
        "series_id": "SMU25000001000000001"
      }
    ],
    "26": [
      {
        "begin_year": 1990,
        "end_year": 2026,
        "industry_code": "10000000",
        "level": "supersector",
        "series_id": "SMS26000001000000001"
      },
      {
        "begin_year": 1990,
        "end_year": 2026,
        "industry_code": "10000000",
        "level": "supersector",
        "series_id": "SMU26000001000000001"
      }
    ],
    "27": [
      {
        "begin_year": 1990,
        "end_year": 2026,
        "industry_code": "10000000",
        "level": "supersector",
        "series_id": "SMS27000001000000001"
      },
      {
        "begin_year": 1990,
        "end_year": 2026,
        "industry_code": "10000000",
        "level": "supersector",
        "series_id": "SMU27000001000000001"
      }
    ],
    "28": [
      {
        "begin_year": 1990,
        "end_year": 2026,
        "industry_code": "10000000",
        "level": "supersector",
        "series_id": "SMS28000001000000001"
      },
      {
        "begin_year": 1990,
        "end_year": 2026,
        "industry_code": "10000000",
        "level": "supersector",
        "series_id": "SMU28000001000000001"
      }
    ],
    "29": [
      {
        "begin_year": 1990,
        "end_year": 2026,
        "industry_code": "10000000",
        "level": "supersector",
        "series_id": "SMS29000001000000001"
      },
      {
        "begin_year": 1990,
        "end_year": 2026,
        "industry_code": "10000000",
        "level": "supersector",
        "series_id": "SMU29000001000000001"
      }
    ],
    "30": [
      {
        "begin_year": 1990,
        "end_year": 2026,
        "industry_code": "10000000",
        "level": "supersector",
        "series_id": "SMS30000001000000001"
      },
      {
        "begin_year": 1990,
        "end_year": 2026,
        "industry_code": "10000000",
        "level": "supersector",
        "series_id": "SMU30000001000000001"
      }
    ],
    "31": [
      {
        "begin_year": 1990,
        "end_year": 2026,
        "industry_code": "10000000",
        "level": "supersector",
        "series_id": "SMS31000001000000001"
      },
      {
        "begin_year": 1990,
        "end_year": 2026,
        "industry_code": "10000000",
        "level": "supersector",
        "series_id": "SMU31000001000000001"
      }
    ],
    "32": [
      {
        "begin_year": 1990,
        "end_year": 2026,
        "industry_code": "10000000",
        "level": "supersector",
        "series_id": "SMS32000001000000001"
      },
      {
        "begin_year": 1990,
        "end_year": 2026,
        "industry_code": "10000000",
        "level": "supersector",
        "series_id": "SMU32000001000000001"
      }
    ],
    "33": [
      {
        "begin_year": 1990,
        "end_year": 2026,
        "industry_code": "10000000",
        "level": "supersector",
        "series_id": "SMS33000001000000001"
      },
      {
        "begin_year": 1990,
        "end_year": 2026,
        "industry_code": "10000000",
        "level": "supersector",
        "series_id": "SMU33000001000000001"
      }
    ],
    "34": [
      {
        "begin_year": 1990,
        "end_year": 2026,
        "industry_code": "10000000",
        "level": "supersector",
        "series_id": "SMS34000001000000001"
      },
      {
        "begin_year": 1990,
        "end_year": 2026,
        "industry_code": "10000000",
        "level": "supersector",
        "series_id": "SMU34000001000000001"
      }
    ],
    "35": [
      {
        "begin_year": 1990,
        "end_year": 2026,
        "industry_code": "10000000",
        "level": "supersector",
        "series_id": "SMS35000001000000001"
      },
      {
        "begin_year": 1990,
        "end_year": 2026,
        "industry_code": "10000000",
        "level": "supersector",
        "series_id": "SMU35000001000000001"
      }
    ],
    "36": [
      {
        "begin_year": 1990,
        "end_year": 2026,
        "industry_code": "10000000",
        "level": "supersector",
        "series_id": "SMS36000001000000001"
      },
      {
        "begin_year": 1990,
        "end_year": 2026,
        "industry_code": "10000000",
        "level": "supersector",
        "series_id": "SMU36000001000000001"
      }
    ],
    "37": [
      {
        "begin_year": 1990,
        "end_year": 2026,
        "industry_code": "10000000",
        "level": "supersector",
        "series_id": "SMS37000001000000001"
      },
      {
        "begin_year": 1990,
        "end_year": 2026,
        "industry_code": "10000000",
        "level": "supersector",
        "series_id": "SMU37000001000000001"
      }
    ],
    "38": [
      {
        "begin_year": 1990,
        "end_year": 2026,
        "industry_code": "10000000",
        "level": "supersector",
        "series_id": "SMS38000001000000001"
      },
      {
        "begin_year": 1990,
        "end_year": 2026,
        "industry_code": "10000000",
        "level": "supersector",
        "series_id": "SMU38000001000000001"
      }
    ],
    "39": [
      {
        "begin_year": 1990,
        "end_year": 2026,
        "industry_code": "10000000",
        "level": "supersector",
        "series_id": "SMS39000001000000001"
      },
      {
        "begin_year": 1990,
        "end_year": 2026,
        "industry_code": "10000000",
        "level": "supersector",
        "series_id": "SMU39000001000000001"
      }
    ],
    "40": [
      {
        "begin_year": 1990,
        "end_year": 2026,
        "industry_code": "10000000",
        "level": "supersector",
        "series_id": "SMS40000001000000001"
      },
      {
        "begin_year": 1990,
        "end_year": 2026,
        "industry_code": "10000000",
        "level": "supersector",
        "series_id": "SMU40000001000000001"
      }
    ],
    "41": [
      {
        "begin_year": 1990,
        "end_year": 2026,
        "industry_code": "10000000",
        "level": "supersector",
        "series_id": "SMS41000001000000001"
      },
      {
        "begin_year": 1990,
        "end_year": 2026,
        "industry_code": "10000000",
        "level": "supersector",
        "series_id": "SMU41000001000000001"
      },
      {
        "begin_year": 1990,
        "end_year": 2026,
        "industry_code": "10113300",
        "level": "1133",
        "series_id": "SMU41000001011330001"
      }
    ],
    "42": [
      {
        "begin_year": 1990,
        "end_year": 2026,
        "industry_code": "10000000",
        "level": "supersector",
        "series_id": "SMS42000001000000001"
      },
      {
        "begin_year": 1990,
        "end_year": 2026,
        "industry_code": "10000000",
        "level": "supersector",
        "series_id": "SMU42000001000000001"
      }
    ],
    "44": [
      {
        "begin_year": 2009,
        "end_year": 2026,
        "industry_code": "10000000",
        "level": "supersector",
        "series_id": "SMS44000001000000001"
      },
      {
        "begin_year": 1990,
        "end_year": 2026,
        "industry_code": "10000000",
        "level": "supersector",
        "series_id": "SMU44000001000000001"
      }
    ],
    "45": [
      {
        "begin_year": 1990,
        "end_year": 2026,
        "industry_code": "10000000",
        "level": "supersector",
        "series_id": "SMS45000001000000001"
      },
      {
        "begin_year": 1990,
        "end_year": 2026,
        "industry_code": "10000000",
        "level": "supersector",
        "series_id": "SMU45000001000000001"
      }
    ],
    "46": [
      {
        "begin_year": 1990,
        "end_year": 2026,
        "industry_code": "10000000",
        "level": "supersector",
        "series_id": "SMS46000001000000001"
      },
      {
        "begin_year": 1990,
        "end_year": 2026,
        "industry_code": "10000000",
        "level": "supersector",
        "series_id": "SMU46000001000000001"
      }
    ],
    "47": [
      {
        "begin_year": 1990,
        "end_year": 2026,
        "industry_code": "10000000",
        "level": "supersector",
        "series_id": "SMS47000001000000001"
      },
      {
        "begin_year": 1990,
        "end_year": 2026,
        "industry_code": "10000000",
        "level": "supersector",
        "series_id": "SMU47000001000000001"
      }
    ],
    "48": [
      {
        "begin_year": 1990,
        "end_year": 2026,
        "industry_code": "10000000",
        "level": "supersector",
        "series_id": "SMS48000001000000001"
      },
      {
        "begin_year": 1990,
        "end_year": 2026,
        "industry_code": "10000000",
        "level": "supersector",
        "series_id": "SMU48000001000000001"
      }
    ],
    "49": [
      {
        "begin_year": 1990,
        "end_year": 2026,
        "industry_code": "10000000",
        "level": "supersector",
        "series_id": "SMS49000001000000001"
      },
      {
        "begin_year": 1990,
        "end_year": 2026,
        "industry_code": "10000000",
        "level": "supersector",
        "series_id": "SMU49000001000000001"
      }
    ],
    "50": [
      {
        "begin_year": 1990,
        "end_year": 2026,
        "industry_code": "10000000",
        "level": "supersector",
        "series_id": "SMS50000001000000001"
      },
      {
        "begin_year": 1990,
        "end_year": 2026,
        "industry_code": "10000000",
        "level": "supersector",
        "series_id": "SMU50000001000000001"
      }
    ],
    "51": [
      {
        "begin_year": 1990,
        "end_year": 2026,
        "industry_code": "10000000",
        "level": "supersector",
        "series_id": "SMS51000001000000001"
      },
      {
        "begin_year": 1990,
        "end_year": 2026,
        "industry_code": "10000000",
        "level": "supersector",
        "series_id": "SMU51000001000000001"
      }
    ],
    "53": [
      {
        "begin_year": 1990,
        "end_year": 2026,
        "industry_code": "10000000",
        "level": "supersector",
        "series_id": "SMS53000001000000001"
      },
      {
        "begin_year": 1990,
        "end_year": 2026,
        "industry_code": "10000000",
        "level": "supersector",
        "series_id": "SMU53000001000000001"
      },
      {
        "begin_year": 1990,
        "end_year": 2026,
        "industry_code": "10113300",
        "level": "1133",
        "series_id": "SMU53000001011330001"
      }
    ],
    "54": [
      {
        "begin_year": 1990,
        "end_year": 2026,
        "industry_code": "10000000",
        "level": "supersector",
        "series_id": "SMS54000001000000001"
      },
      {
        "begin_year": 1990,
        "end_year": 2026,
        "industry_code": "10000000",
        "level": "supersector",
        "series_id": "SMU54000001000000001"
      }
    ],
    "55": [
      {
        "begin_year": 1990,
        "end_year": 2026,
        "industry_code": "10000000",
        "level": "supersector",
        "series_id": "SMS55000001000000001"
      },
      {
        "begin_year": 1990,
        "end_year": 2026,
        "industry_code": "10000000",
        "level": "supersector",
        "series_id": "SMU55000001000000001"
      }
    ],
    "56": [
      {
        "begin_year": 1990,
        "end_year": 2026,
        "industry_code": "10000000",
        "level": "supersector",
        "series_id": "SMS56000001000000001"
      },
      {
        "begin_year": 1990,
        "end_year": 2026,
        "industry_code": "10000000",
        "level": "supersector",
        "series_id": "SMU56000001000000001"
      }
    ],
    "72": [
      {
        "begin_year": 2003,
        "end_year": 2026,
        "industry_code": "10000000",
        "level": "supersector",
        "series_id": "SMS72000001000000001"
      },
      {
        "begin_year": 2003,
        "end_year": 2026,
        "industry_code": "10000000",
        "level": "supersector",
        "series_id": "SMU72000001000000001"
      }
    ]
  },
  "states_dc_tally": {
    "113": 0,
    "1133": 4,
    "113310": 0,
    "none": 3,
    "other": 0,
    "supersector": 44
  },
  "states_with_1133": 4,
  "states_with_113310": 0,
  "states_with_113_only": 0,
  "states_with_none": 6,
  "states_with_other": 0,
  "states_with_supersector_only": 45
}
```

_Extracts: 5; summary `generated_utc` 2026-09-05T00:13:39+00:00._

### `fia`

**access**:

```json
{
  "reason": "Verified for retrieval of one report from this endpoint: the response's own metadata names what came back as attribute 79, \"0079 Area of sampled land and water, in acres\" -- \"Area estimate for land and water based on all sampled plots (hazardous and denied access plots are not included in the estimate).\". The /fullreport/parameters/snum catalog fetched this run enumerates 752 estimate attributes, of which 74 sit in harvest-removals estimate groups -- Annual harvest removals dry weight (38 attribute(s), lowest attribute number 403, EVAL_TYP EXPREMV); Annual harvest removals number (6 attribute(s), lowest attribute number 913, EVAL_TYP EXPREMV); Annual harvest removals total-stem volume (13 attribute(s), lowest attribute number 11093, EVAL_TYP EXPREMV); Annual harvest removals volume (17 attribute(s), lowest attribute number 238, EVAL_TYP EXPREMV) -- which that same catalog keeps distinct from its non-harvest removals groups (Annual other removals dry weight, Annual other removals number, Annual other removals total-stem volume, Annual other removals volume, Annual removals dry weight, Annual removals number, Annual removals total-stem volume, Annual removals volume). That attribute number is not one of those harvest-removals attributes: what this run proved end to end is retrieval of the one measure named above, while the harvest-removals capability rests on the fetched catalog listing those attributes and not on a harvest-removals report having been requested and returned. See findings.snum_estimate_attributes.",
  "route": "https://apps.fs.usda.gov/fiadb-api/fullreport",
  "status": "verified"
}
```

> **Recorded access reason:** Verified for retrieval of one report from this endpoint: the response's own metadata names what came back as attribute 79, "0079 Area of sampled land and water, in acres" -- "Area estimate for land and water based on all sampled plots (hazardous and denied access plots are not included in the estimate).". The /fullreport/parameters/snum catalog fetched this run enumerates 752 estimate attributes, of which 74 sit in harvest-removals estimate groups -- Annual harvest removals dry weight (38 attribute(s), lowest attribute number 403, EVAL_TYP EXPREMV); Annual harvest removals number (6 attribute(s), lowest attribute number 913, EVAL_TYP EXPREMV); Annual harvest removals total-stem volume (13 attribute(s), lowest attribute number 11093, EVAL_TYP EXPREMV); Annual harvest removals volume (17 attribute(s), lowest attribute number 238, EVAL_TYP EXPREMV) -- which that same catalog keeps distinct from its non-harvest removals groups (Annual other removals dry weight, Annual other removals number, Annual other removals total-stem volume, Annual other removals volume, Annual removals dry weight, Annual removals number, Annual removals total-stem volume, Annual removals volume). That attribute number is not one of those harvest-removals attributes: what this run proved end to end is retrieval of the one measure named above, while the harvest-removals capability rests on the fetched catalog listing those attributes and not on a harvest-removals report having been requested and returned. See findings.snum_estimate_attributes.

**coverage_span**:

```json
{
  "covered": "inventory evaluation cycles overlapping D1's reference years, not calendar months or a Logging-specific series",
  "published_end": "2026",
  "published_start": "1968",
  "uncovered": "no monthly resolution: SRC-FOR-004 forbids interpolating to months. Also measured, over the 5 FIA page(s) in this scan's corpus -- each of which answered with a status-200 body this run and is hashed as an extract (fiadb_api_doc.html, fullreport_naive_probe.html, fullreport_real_probe.json, snum_estimate_attributes.html, wc_evaluation_index.html): word-boundary hits for the classification codes and measures an industry-coded source would carry are NAICS=0, SIC=0, employment=0, establishment=0, industry=0, and hits for the species/product/land-use concepts FIA organises its own reporting by are land use=10, product=52, species=282. INFERENCE MARKER, OPENING: what follows to the closing marker is a reading of those counts, not a further measurement; it is supplied by hand, carries no extract hash and is re-checked by no later run. Zero industry-term hits across those pages is read here as FIA carrying no industry concept to join on at all, so a Logging (113310) slice cannot be selected out of FIA the way it is out of QCEW or CBP and Stage 7 would need its own crosswalk from FIA's species/product/land-use taxonomy instead; the competing reading -- that an industry concept exists elsewhere in the API and merely goes unmentioned on the pages this script happens to fetch -- is not excluded by a zero count over those pages. INFERENCE MARKER, CLOSING. Also measured: no FIA evaluation unit for the District of Columbia -- absent from the 1138-row evaluation index fetched this run (states_dc's 51st member has no forest inventory).",
  "window_end": "2024-12",
  "window_start": "2017-01"
}
```

**findings**:

```json
{
  "datamart_probes": [
    {
      "attempts": [
        {
          "attempt": 1,
          "bytes": 0,
          "http_status": 0,
          "outcome": "transport_failure"
        },
        {
          "attempt": 2,
          "bytes": 0,
          "http_status": 0,
          "outcome": "transport_failure"
        },
        {
          "attempt": 3,
          "bytes": 0,
          "http_status": 0,
          "outcome": "transport_failure"
        }
      ],
      "elapsed_seconds": 6.271,
      "url": "https://apps.fs.usda.gov/fia/datamart/CSV/"
    },
    {
      "attempts": [
        {
          "attempt": 1,
          "bytes": 0,
          "http_status": 0,
          "outcome": "transport_failure"
        },
        {
          "attempt": 2,
          "bytes": 0,
          "http_status": 0,
          "outcome": "transport_failure"
        },
        {
          "attempt": 3,
          "bytes": 0,
          "http_status": 0,
          "outcome": "transport_failure"
        }
      ],
      "elapsed_seconds": 6.37,
      "url": "https://apps.fs.usda.gov/fia/datamart/datamart.html"
    }
  ],
  "district_of_columbia_has_fia_evaluation": false,
  "doc_parameters": [
    {
      "description": "FOR CIRCULAR ESTIMATES ONLY * - Otherwise not required The latitude in decimal degrees for a circular estimate centroid",
      "parameter": "lat",
      "required": true
    },
    {
      "description": "FOR CIRCULAR ESTIMATES ONLY * - Otherwise not required The longitude in decimal degrees for a circular estimate centroid",
      "parameter": "lon",
      "required": true
    },
    {
      "description": "FOR CIRCULAR ESTIMATES ONLY * - Otherwise not required The radius in miles for a circular estimate",
      "parameter": "radius",
      "required": true
    },
    {
      "description": "Evaluation group code(s) for inventory(ies) of interest. Typically consists of the state FIPS code concatenated with the 4 digit inventory year. e.g. 102020 would indicate the Delaware 2020 inventory. Valid values can be found in the \"EVALID\" column here: /fullreport/parameters/wc",
      "parameter": "wc",
      "required": true
    },
    {
      "description": "The estimate attribute number or description of interest. Used as the numerator for ratio estimates. Users can use values either from the numeric \"ATTRIBUTE_NBR\", or the text \"ATTRIBUTE_DESCR\" found here: /fullreport/parameters/snum",
      "parameter": "snum",
      "required": true
    },
    {
      "description": "Row estimate grouping definition, translates to rows in traditional EVALIDator table format. Valid values can be found in the \"LABEL_VAR\" column here: /fullreport/parameters/rselected",
      "parameter": "rselected",
      "required": true
    },
    {
      "description": "Column estimate grouping definition, translates to columns in traditional EVALIDator table format. Valid values can be found in the \"LABEL_VAR\" column here: /fullreport/parameters/cselected",
      "parameter": "cselected",
      "required": true
    },
    {
      "description": "Page estimate grouping definition, translates to pages in traditional EVALIDator table format. Valid values can be found in the \"LABEL_VAR\" column here: /fullreport/parameters/pselected",
      "parameter": "pselected",
      "required": false
    },
    {
      "description": "Row grouping temporal basis Temporal basis for row grouping definition. Only used in area change, growth, removals, and mortality estimates as these are based on plot-revisits. Allows users to base groupings on relevant status either from the first or from the second plot visit. Valid options are: CURRENT (default) PREVIOUS CURRENT IF AVAILABLE ELSE PREVIOUS PREVIOUS IF AVAILABLE ELSE CURRENT ACCOUNTING",
      "parameter": "rtime",
      "required": false
    },
    {
      "description": "Column grouping temporal basis Temporal basis for row grouping definition. Only used in area change, growth, removals, and mortality estimates as these are based on plot-revisits. Allows users to base groupings on relevant status either from the first or from the second plot visit. Valid options are: CURRENT (default) PREVIOUS CURRENT IF AVAILABLE ELSE PREVIOUS PREVIOUS IF AVAILABLE ELSE CURRENT ACCOUNTING",
      "parameter": "ctime",
      "required": false
    },
    {
      "description": "Page grouping temporal basis Temporal basis for row grouping definition. Only used in area change, growth, removals, and mortality estimates as these are based on plot-revisits. Allows users to base groupings on relevant status either from the first or from the second plot visit. Valid options are: CURRENT (default) PREVIOUS CURRENT IF AVAILABLE ELSE PREVIOUS PREVIOUS IF AVAILABLE ELSE CURRENT ACCOUNTING",
      "parameter": "ptime",
      "required": false
    },
    {
      "description": "The ratio denominator estimate attribute number or description of interest. Users can use values either from the numeric \"ATTRIBUTE_NBR\", or the text \"ATTRIBUTE_DESCR\" found here: /fullreport/parameters/snum",
      "parameter": "sdenom",
      "required": false
    },
    {
      "description": "SQL filter string with or without leading 'and'. E.g. \"COND.OWNCD = 40\" or \"AND TREE.CCLCD in (1,2,3)\"",
      "parameter": "strFilter",
      "required": false
    },
    {
      "description": "SQL filter applied to non-ratio estimates - deprecated in favor of 'strFilter' but maintained for back-compatibility",
      "parameter": "wf",
      "required": false
    },
    {
      "description": "SQL filter applied to ratio estimate numerators only",
      "parameter": "wnum",
      "required": false
    },
    {
      "description": "SQL filter applied to ratio estimate numerators and denominators - deprecated in favor of 'strFilter' but maintained for back-compatibility",
      "parameter": "wnumdenom",
      "required": false
    },
    {
      "description": "A value of Y returns only the grouped estimates without totals or subtotals. Note the behavior of this parameter has changed from the previous version of the API. Error estimates are now reported for all estimates.",
      "parameter": "estOnly",
      "required": false
    },
    {
      "description": "Select between FIA or RPA definition of forest land. Valid options are: FIADEF* (default) RPADEF* More information on the RPA definition can be found here: /static/html/RPA_forest_filter.html",
      "parameter": "FIAorRPA",
      "required": false
    },
    {
      "description": "Desired output format for estimate returns. Valid options are: HTML* - legacy EVALIDator page/row/column cross-tabulated format - this is the default NHTML* - flat table of estimate values JSON* - legacy EVALIDator page/row/column JSON NJSON* - flat formatted JSON estimate values with metadata XML* - legacy EVALIDator page/row/column XML format NXML* - flat formatted XML estimate values with metadata",
      "parameter": "outputFormat",
      "required": false
    }
  ],
  "evaluation_vintage_field": "evalGrps",
  "evaluation_vintage_index": {
    "row_count": 1138,
    "states": [
      "Alabama",
      "Alaska",
      "Alaska Coastal",
      "Alaska Interior",
      "American Samoa",
      "Arizona",
      "Arkansas",
      "California",
      "Colorado",
      "Connecticut",
      "Delaware",
      "Federated States Of",
      "Florida",
      "Georgia",
      "Guam",
      "Hawaii",
      "Idaho",
      "Illinois",
      "Indiana",
      "Iowa",
      "Kansas",
      "Kentucky",
      "Louisiana",
      "Maine",
      "Marshall Islands",
      "Maryland",
      "Massachusetts",
      "Michigan",
      "Minnesota",
      "Mississippi",
      "Missouri",
      "Montana",
      "Nebraska",
      "Nevada",
      "New Hampshire",
      "New Jersey",
      "New Mexico",
      "New York",
      "North Carolina",
      "North Dakota",
      "Northern Mariana Isl",
      "Ohio",
      "Oklahoma",
      "Oklahoma(East)",
      "Oklahoma(West)",
      "Oregon",
      "Palau",
      "Pennsylvania",
      "Puerto Rico",
      "Puerto Rico (Mainland Only)",
      "Puerto Rico (Mainland Only))",
      "Puerto Rico (Mainland, Vieques, Culebra)",
      "Puerto Rico (Mona Island)",
      "Rhode Island",
      "South Carolina",
      "South Dakota",
      "Tennessee",
      "Texas",
      "Texas(East)",
      "Texas(West)",
      "Us Virgin Islands",
      "Utah",
      "Vermont",
      "Virginia",
      "Washington",
      "West Virginia",
      "Wisconsin",
      "Wyoming"
    ],
    "year_max": 2026,
    "year_min": 1968
  },
  "industry_concept_scan": {
    "bytes_scanned": 751299,
    "fia_taxonomy_terms": {
      "land use": 10,
      "product": 52,
      "species": 282
    },
    "industry_classification_terms": {
      "NAICS": 0,
      "SIC": 0,
      "employment": 0,
      "establishment": 0,
      "industry": 0
    },
    "pages_scanned": [
      "fiadb_api_doc.html",
      "fullreport_naive_probe.html",
      "fullreport_real_probe.json",
      "snum_estimate_attributes.html",
      "wc_evaluation_index.html"
    ]
  },
  "measure_proved_by_probe": {
    "attribute_nbr": "79",
    "est_meta": "Area estimate for land and water based on all sampled plots (hazardous and denied access plots are not included in the estimate).",
    "num_est_desc": "0079 Area of sampled land and water, in acres"
  },
  "other_routes_probed": [
    {
      "bytes": 662,
      "content_type": "text/html; charset=iso-8859-1",
      "http_status": 500,
      "machine_readable": false,
      "origin": "dispatch lead table",
      "outcome": "other_status",
      "url": "https://apps.fs.usda.gov/Evalidator/evalidator.jsp"
    },
    {
      "bytes": 67698,
      "content_type": "text/html; charset=utf-8",
      "http_status": 200,
      "machine_readable": false,
      "origin": "dispatch lead table",
      "outcome": "reachable",
      "url": "https://www.fs.usda.gov/research/programs/fia"
    }
  ],
  "probe": {
    "bytes": 34033,
    "content_type": "application/json",
    "has_sampling_error": true,
    "http_status": 200,
    "outcome": "reachable",
    "params_sent": {
      "cselected": "Land use",
      "outputFormat": "NJSON",
      "rselected": "Land Use - Major",
      "snum": "79",
      "wc": "102020"
    },
    "parsed_as_report_with_estimates_and_metadata": true,
    "url": "https://apps.fs.usda.gov/fiadb-api/fullreport"
  },
  "probe_naive_missing_required_params": {
    "bytes": 4530,
    "content_type": "text/html; charset=utf-8",
    "http_status": 200,
    "is_evalidator_error_page": true,
    "note": "the brief's illustrative probe -- omits every parameter the doc page marks required (wc*, snum*, rselected*, cselected*); returns HTTP 200 but an EVALIDator error page, not a report -- a '200 but no usable data' outcome, not a source outage",
    "outcome": "reachable",
    "params_sent": {
      "outputFormat": "JSON"
    },
    "url": "https://apps.fs.usda.gov/fiadb-api/fullreport"
  },
  "raw_retention_rule": {
    "extracts_recorded": 7,
    "extracts_with_non_200_status": 1,
    "non_200_statuses_recorded": [
      500
    ],
    "rule": "This script writes and registers a fetched body whenever a route it probes for bytes answered with a non-empty body, whatever the HTTP status, and each extract's own http_status records which status it carried. On an access-verdict probe the non-200 body IS the evidence: a 404 page and a 403 page are different verdicts and only the retained bytes tell them apart. Two cases register no extract, and they are not the same case. A transport failure produced no response at all, so there is no body to keep; its evidence is the probe record's outcome field instead. A response whose body is empty -- including an empty 200 -- has nothing to keep either, so it registers no extract as well, and what records it is its probe entry's status and its bytes count of zero, not retained bytes. Scope: this rule is about the routes probed for bytes. Where this script probes a route status-only, through a helper that discards the body by construction, that route registers no extract whatever it answers; which routes, if any, a run probed that way is recorded in this source's own probe findings, as entries carrying each attempt's status and byte count and no body. The counters below therefore say which statuses were retained and nothing more: a retained status 200 means the endpoint answered, not that the body is usable data -- an application error page can arrive with status 200, and which retained bodies are usable is recorded per probe in findings, never inferable from an extract's http_status. Reader's caution: this rule is this script's, and the absence of a non-200 extract under another source in this audit is not evidence that no non-200 response occurred there."
  },
  "sampling_error_field": "SE",
  "snum_estimate_attributes": {
    "eval_typs_present": [
      "EXPCHNG",
      "EXPCURR",
      "EXPDWM",
      "EXPGROW",
      "EXPMORT",
      "EXPREMV",
      "EXPVOL"
    ],
    "harvest_removals_attribute_count": 74,
    "harvest_removals_attribute_nbrs": [
      "238",
      "239",
      "240",
      "241",
      "242",
      "244",
      "245",
      "246",
      "247",
      "248",
      "403",
      "404",
      "405",
      "406",
      "407",
      "408",
      "409",
      "410",
      "411",
      "412",
      "413",
      "414",
      "913",
      "914",
      "915",
      "916",
      "917",
      "918",
      "2649",
      "2650",
      "2651",
      "2654",
      "11093",
      "11094",
      "11107",
      "11108",
      "11149",
      "11150",
      "11163",
      "11164",
      "11191",
      "11192",
      "11258",
      "11259",
      "11278",
      "11279",
      "11293",
      "11306",
      "574067",
      "574068",
      "574069",
      "574070",
      "574071",
      "574072",
      "574073",
      "574074",
      "574075",
      "574076",
      "574077",
      "574078",
      "574079",
      "574080",
      "574081",
      "574082",
      "574083",
      "574084",
      "574085",
      "574086",
      "574087",
      "574088",
      "574161",
      "574162",
      "574209",
      "574210"
    ],
    "harvest_removals_groups": [
      {
        "attribute_count": 38,
        "estimate_group": "Annual harvest removals dry weight",
        "eval_typs": [
          "EXPREMV"
        ],
        "lowest_attribute_nbr": "403"
      },
      {
        "attribute_count": 6,
        "estimate_group": "Annual harvest removals number",
        "eval_typs": [
          "EXPREMV"
        ],
        "lowest_attribute_nbr": "913"
      },
      {
        "attribute_count": 13,
        "estimate_group": "Annual harvest removals total-stem volume",
        "eval_typs": [
          "EXPREMV"
        ],
        "lowest_attribute_nbr": "11093"
      },
      {
        "attribute_count": 17,
        "estimate_group": "Annual harvest removals volume",
        "eval_typs": [
          "EXPREMV"
        ],
        "lowest_attribute_nbr": "238"
      }
    ],
    "non_harvest_removals_groups": [
      "Annual other removals dry weight",
      "Annual other removals number",
      "Annual other removals total-stem volume",
      "Annual other removals volume",
      "Annual removals dry weight",
      "Annual removals number",
      "Annual removals total-stem volume",
      "Annual removals volume"
    ],
    "row_count": 752
  },
  "tpo_mentions_on_fia_doc_page": 0
}
```

_Extracts: 7; summary `generated_utc` 2026-09-04T23:27:10+00:00._

### `qcew_codes`

**access**:

```json
{
  "reason": null,
  "route": "https://data.bls.gov/cew/doc/titles/<dimension>/",
  "status": "verified"
}
```

**coverage_span**:

```json
{
  "covered": "2017-2024",
  "published_end": "2024",
  "published_start": "2017",
  "uncovered": "",
  "window_end": "2024-12",
  "window_start": "2017-01"
}
```

**findings**:

```json
{
  "alignment_srcqcew007": {
    "aligned": true,
    "industry_code": "113310",
    "naics_vintage_by_year": {
      "2017": "NAICS 2017",
      "2018": "NAICS 2017",
      "2019": "NAICS 2017",
      "2020": "NAICS 2017",
      "2021": "NAICS 2017",
      "2022": "NAICS 2022",
      "2023": "NAICS 2022",
      "2024": "NAICS 2022"
    },
    "national_agglvl": [
      "18"
    ],
    "notes": "Filter predicates recorded verbatim, applied in this order: industry_code == '113310' is applied first, to the full concatenated slice frame of 32 distinct year-quarters as loaded from Task 2's recorded slice CSVs, before any other split; 32 of those 32 loaded quarters carry at least one 113310 row, and every per-quarter count quoted elsewhere in these notes names which of the two it means. own_code == '5' (title 'Private', from the fetched ownership titles file) is applied next, restricting to private ownership; the national/state-like geography split comes last, so both sides of it are sub-frames of the already industry- and ownership-filtered frame. National rows are area_fips == 'US000'; state-like rows are area_fips.str.ends_with('000') and area_fips != 'US000'. Title evidence for 'same industry detail': fetched agglvl_code titles give national code 18 = 'National, NAICS 6-digit -- by ownership sector' and state code 58 = 'State, NAICS 6-digit -- by ownership sector'; stripping the leading geography clause leaves an identical detail clause at both levels ('NAICS 6-digit -- by ownership sector'), so the same-industry-detail conjunct of aligned above is True (see _same_industry_detail). This defends against a titles-metadata inconsistency between the two geography levels' fetched titles; it is not independent discriminating power, because digit-depth and ownership breakout are already pinned upstream by the queried industry_code and the own_code filter. Scope of the fetched-title comparison, computed from the 4 agglvl codes observed on 113310 rows before the own_code filter: all of them strip to one detail clause -- 'NAICS 6-digit -- by ownership sector' at codes 18 (National), 48 (MSA), 58 (State), 78 (County). So the identical-clause property is established across exactly the geography levels present here, which is all this run shows; it is not a claim about every title in the fetched agglvl_code.csv, whose other codes were not examined. Geography-universe finding for SRC-QCEW-007 / Sec 3.2: across all 32 quarters in which 113310 rows appear, the state-like predicate above yields exactly 51 distinct area codes. 72000 ('Puerto Rico -- Statewide', 8 rows, in 2017, 2018) is present in state-like rows but absent from c.STATE_AREAS. District of Columbia (11000) carries zero private-ownership 113310 rows in any of the 32 quarters in which 113310 rows appear at all: it is entirely absent from this panel, not merely cell-suppressed within a published row. The US000 composition argument that follows is hand-authored in all three of its parts -- quotation, premise and conclusion. This script fetches none of them, so none carries an extract hash and no later run re-checks any of them. Quoted, hand-transcribed from BLS's QCEW Aggregation Level Codes page (https://www.bls.gov/cew/classifications/aggregation/agg-level-titles.htm, footnote b): 'National level aggregations exclude Puerto Rico and Virgin Islands from the totals'. Unquoted premise, supplied by hand and carried by neither that quotation nor any other source cited here: the jurisdictions QCEW aggregates into a national total are the 50 states, DC, Puerto Rico and the Virgin Islands, and nothing else. Conclusion, which needs both: read against the national agglvl code computed above (agglvl-18), the US000 national total is definitionally 50 states + DC, the same composition as geography_universe: 'states_dc'. The exclusion quotation on its own says only what is removed, never what remains -- the membership premise is what closes the argument, and it is the part a later task should re-source before relying on this. DC's complete row-level absence is a genuine states_dc coverage gap: a private-ownership Logging panel over this window will have no DC series at all, which a later task should expect rather than mistake for a bug. INFERENCE MARKER, OPENING: what follows to the closing marker is a reading of that absence against the hand-authored membership premise recorded above, not a further measurement. It is supplied by hand, carries no extract hash, and is re-checked by no later run. On that premise US000 includes DC, while no DC state row is published, so nothing at the state level observes whatever DC contributes to the national total: a potential national-vs-sum-of-states residual channel, distinct from and additional to cell-level suppression. That is a channel, not a quantity. Its magnitude is not measured here and no value is claimed for it -- not even that it is nonzero, which would need DC to carry private 113310 activity at all, and nothing this script fetched shows whether it does. Where the channel would show up, if it is open at all, is the national-minus-sum-of-states difference qcew_identity measures quarter by quarter: quarter_table's estab_gap and estab_gap_after_other on the establishment margin, and evidence's clean_months on the employment one. Read the two findings together rather than either alone. On a margin where qcew_identity finds that difference closing exactly, its own recorded reading -- that an area adding zero establishments to a quarterly total which closes exactly can add no employment in that quarter's months -- rules this channel out for that margin, and what is left open here is only the margin qcew_identity could not evaluate. INFERENCE MARKER, CLOSING. NAICS vintage sourcing (Step 3). One part of this is derived and the rest is hand-authored; both are labelled as such. Derived: the fetched industry titles file gives 113310 = 'NAICS 113310 Logging', confirming the code is valid in the vintage that file reflects. Either way that settles only the current vintage, never the per-year history: QCEW publishes no per-row NAICS-vintage column and the titles file reflects only the current vintage, so naics_vintage_by_year above cannot be computed from anything this script fetches. Everything from here to the end of this note is hand-authored -- the quotations, the premises drawn on alongside them, and the conclusions that need both, equally. This script fetches none of it, so none of it carries an extract hash and no later run re-checks any of it. Quoted verbatim from two BLS classification pages: https://www.bls.gov/cew/classifications/industry/naics-2017.htm: 'This revision will be introduced by the Bureau of Labor Statistics (BLS) with the release of first quarter 2017 Quarterly Census of Employment and Wages (QCEW) data.' https://www.bls.gov/cew/classifications/industry/naics-2022.htm: 'This revision will be introduced by the Bureau of Labor Statistics (BLS) on September 7, 2022, with the full data release of first quarter 2022 Quarterly Census of Employment and Wages (QCEW) data.' Unquoted premise, and the load-bearing one: QCEW does not retabulate prior reference years onto a new NAICS vintage. The two quotations establish only the quarter at which each vintage is introduced; without that premise they say nothing about what vintage 2017-2021 data carry today, and the entire per-year naics_vintage_by_year mapping rests on it. It is supplied by hand, is carried by neither quotation and by no other source cited in this note, and is the single claim here a later task should re-source first. Granting it, the switch is a hard boundary at reference year 2022, giving the clean per-year split recorded above. Also hand-checked out-of-band, against the local classification-codes skill's derived NAICS data rather than against anything fetched here, and reported with its two caveats. That skill's concordance CSVs pair 113310 to itself with the title 'Logging' unchanged in both the 2012-to-2017 and the 2017-to-2022 direction, and its NAICS structure CSVs carry an empty change_indicator on 113310 in all three of the 2012, 2017 and 2022 vintages, which that skill documents as meaning unchanged from the prior vintage at that level. Caveat one: the concordance link_type of 1:1 is not a Census column. Census ships four columns -- source code, source title, target code, target title -- flags partial flows by cell formatting the parse discards, and publishes no allocation weights; link_type is derived by that skill from code multiplicities after deduplication. Caveat two, following from the first: 1:1 establishes only that 113310 neither split nor merged in the six-digit code pairing, which is not a statement about the industry's definitional content. It is the unchanged title and the empty structure-file change_indicator, not the 1:1, that carry the continuity claim, and even they are titles and markers rather than a comparison of the two vintages' definitional text.",
    "own_code": "5",
    "period_basis": "Measured this run, from the header of the concatenated slice frame load_slices() returns -- pl.concat(how='vertical') raises on a schema mismatch, so that one header is the header every slice CSV qcew_routes recorded carries. Period-keying columns present, of 'year' and 'qtr': year, qtr. Monthly employment level columns present: 3 (month1_emplvl, month2_emplvl, month3_emplvl), matched on the anchored pattern ^month(\\d+)_emplvl$, which is what keeps the location-quotient (lq_) and over-the-year (oty_) columns built on those same names out of the count. That is the whole of what the header establishes here: which columns exist and what they are called. Documented, not measured: the reference period a monthly employment column counts over. Hand-transcribed from the local bls-data-context skill's QCEW reference (~/.claude/skills/bls-data-context/references/qcew.md, section 'Employment concept'), which reads: 'QCEW monthly employment counts covered workers who worked during, or received pay for, the pay period including the 12th day of the month.' That reference is itself hand-authored and carries no per-section citation -- its own 'Source pages reviewed' header lists the BLS Handbook of Methods QCEW pages it drew on without tying any one of them to this sentence -- so no single BLS page is named for it here. The quotation is not among this run's own fetches: this script's extracts are the code/title CSVs TITLES names, and none of them states a reference period. So the quotation carries no extract hash and no later run re-checks it. INFERENCE MARKER, OPENING: what follows to the closing marker is a reading of that general statement onto the columns measured above, not a further measurement; it is supplied by hand, carries no extract hash and is re-checked by no later run. The 3 column(s) named above are read here as the QCEW monthly employment counts that statement describes, so each is taken to count over the pay period including the 12th day of its own month. The fetched slice files do not say so: their header supplies column names and their rows supply counts, and neither records a reference period. INFERENCE MARKER, CLOSING.",
    "state_agglvl": [
      "58"
    ]
  },
  "codes_present": {
    "agglvl_code": [
      {
        "code": "18",
        "row_count": 64,
        "title": "National, NAICS 6-digit -- by ownership sector"
      },
      {
        "code": "48",
        "row_count": 8684,
        "title": "MSA, NAICS 6-digit -- by ownership sector"
      },
      {
        "code": "58",
        "row_count": 1652,
        "title": "State, NAICS 6-digit -- by ownership sector"
      },
      {
        "code": "78",
        "row_count": 48712,
        "title": "County, NAICS 6-digit -- by ownership sector"
      }
    ],
    "disclosure_code": [
      {
        "code": "",
        "row_count": 17302,
        "title": null
      },
      {
        "code": "-",
        "row_count": 935,
        "title": null
      },
      {
        "code": "N",
        "row_count": 40875,
        "title": null
      }
    ],
    "own_code": [
      {
        "code": "3",
        "row_count": 180,
        "title": "Local Government"
      },
      {
        "code": "5",
        "row_count": 58932,
        "title": "Private"
      }
    ],
    "size_code": [
      {
        "code": "0",
        "row_count": 59112,
        "title": "All establishment sizes"
      }
    ]
  },
  "national_agglvl": [
    {
      "code": "18",
      "title": "National, NAICS 6-digit -- by ownership sector"
    }
  ],
  "private_own_code": "5",
  "size_code_values": [
    {
      "code": "0",
      "row_count": 59112,
      "title": "All establishment sizes"
    }
  ],
  "state_agglvl": [
    {
      "code": "58",
      "title": "State, NAICS 6-digit -- by ownership sector"
    }
  ],
  "titles_available": {
    "agglvl_code": "https://data.bls.gov/cew/doc/titles/agglevel/agglevel_titles.csv",
    "area_fips": "https://data.bls.gov/cew/doc/titles/area/area_titles.csv",
    "disclosure_code": null,
    "industry_code": "https://data.bls.gov/cew/doc/titles/industry/industry_titles.csv",
    "own_code": "https://data.bls.gov/cew/doc/titles/ownership/ownership_titles.csv",
    "size_code": "https://data.bls.gov/cew/doc/titles/size/size_titles.csv"
  }
}
```

_Extracts: 5; summary `generated_utc` 2026-09-05T00:20:03+00:00._

### `qcew_identity`

**access**:

```json
{
  "reason": null,
  "route": "derived from qcew_panel (/Users/lowell/Projects/impute-suppressed-stats/data/raw/audit/qcew_panel/panel.parquet)",
  "status": "verified"
}
```

**coverage_span**:

```json
{
  "covered": "2017-01..2024-12 (96 month(s))",
  "published_end": "2024-12",
  "published_start": "2017-01",
  "uncovered": "",
  "window_end": "2024-12",
  "window_start": "2017-01"
}
```

**findings**:

```json
{
  "absent_state_months": "Absent states+DC area-months, measured: 84 of the 50 x 96 possible area-month cells carry no row at all, and each month carries between 48 and 50 of the 50 areas. The area(s) whose span is shorter than the panel's: Delaware -- Statewide (60 month(s)), North Dakota -- Statewide (48 month(s)). Also measured: the establishment gap after non-state areas is exactly zero in 32 of 32 evaluable quarter(s). INFERENCE MARKER, OPENING: what follows to the closing marker is a reading of those two measurements, not a third measurement, is supplied by hand, carries no extract hash and is re-checked by no later run. An area-month with no published row is read here as a true zero rather than as a hidden value, on the ground that an area adding zero establishments to a quarterly total that closes exactly can add no employment in that quarter's months; on that reading the varying per-month area count above does not undercut the state sum. INFERENCE MARKER, CLOSING.",
  "branch": "decline",
  "clean_months": 0,
  "decision_thresholds": "Decision thresholds for SRC-QCEW-006. SCOPE MARKER, OPENING: every sentence in this findings key, from here to the closing scope marker, is hand-authored. It records where this script's two thresholds come from; it states nothing this run measured, it is the only wholly hand-authored key in this summary, and its scope does not extend past its own closing marker to any neighbouring key. This script fetches nothing, so none of the text here carries an extract hash and no later run re-checks any of it. Threshold one, tolerance: 'equals' means exact integer equality, tolerance 0, on the stated ground that QCEW monthly employment and quarterly establishment counts are integer counts of jobs and of establishments; classify_identity therefore compares gaps to 0 and never to a band, and no numerical confidentiality threshold is encoded anywhere in this script. Threshold two, branch assignment: a gap that closes only after subtracting non-state areas present in the national universe is classified residual_cells rather than enforce. That rests on one quotation, reproduced verbatim from specs/logging-employment-spec.md section 3.2: 'A national control MUST NOT be imposed on a state universe that omits components included in the national total.' The step from that quotation to the residual_cells branch is an inference and is hand-authored: the quotation forbids imposing a national control on a universe missing national components, and the reading applied here is that a states+DC universe which excludes a non-state area the national total includes is exactly such a universe, so the area must enter as an explicit residual cell instead of being controlled away. The quotation does not name the branch, and no measurement in this run carries that step. The same reading is what makes containment worth measuring rather than assuming: the quotation is conditioned on components 'included in the national total', so an area measured to sit outside that total is not what it governs. Both thresholds were set as defaults by the Stage 0 plan's Global Constraints and confirmed at handoff before classify_identity was written. SCOPE MARKER, CLOSING: end of the hand-authored text; every other findings key in this summary is computed from the panel this run read, and the one inference among them carries its own inline marker.",
  "evidence": {
    "clean_months": 0,
    "clean_months_close": false,
    "clean_months_closing": 0,
    "employment_residual_never_negative": true,
    "estab_identity_closes_after_other_areas": true,
    "max_abs_clean_emp_gap": null,
    "max_estab_gap_after_other": 0,
    "min_emp_gap_after_other": 696,
    "months_total": 96,
    "negative_residual_months": 0,
    "other_areas_present": false,
    "quarters_closing": 32,
    "quarters_evaluable": 32,
    "quarters_total": 32,
    "quarters_unevaluable": 0,
    "testable_months": 96,
    "untestable_months": 0
  },
  "geography_universe_explains_gap": false,
  "geography_universe_explains_gap_reading": "Reading of geography_universe_explains_gap, whose value this run is False: the key is the conjunction of other_areas_present (False) with estab_identity_closes_after_other_areas (True), so a false value can mean either that geography leaves a gap unexplained or that no gap arose for geography to explain. Which of the two this run found, from the raw comparison rather than from the conjunction: national minus states+DC establishments takes the value(s) [0] across the 32 quarter(s) in the panel, and non-state containment was measured separately in non_state_area_containment.",
  "month_table": [
    {
      "emp_gap": 1466,
      "emp_gap_after_other": 1466,
      "month": 1,
      "n_states_suppressed": 14,
      "national_emp": 48611,
      "other_emp": 0,
      "other_emp_published": null,
      "states_dc_emp": 47145,
      "year": 2017
    },
    {
      "emp_gap": 1549,
      "emp_gap_after_other": 1549,
      "month": 2,
      "n_states_suppressed": 14,
      "national_emp": 48581,
      "other_emp": 0,
      "other_emp_published": null,
      "states_dc_emp": 47032,
      "year": 2017
    },
    {
      "emp_gap": 1532,
      "emp_gap_after_other": 1532,
      "month": 3,
      "n_states_suppressed": 14,
      "national_emp": 47418,
      "other_emp": 0,
      "other_emp_published": null,
      "states_dc_emp": 45886,
      "year": 2017
    },
    {
      "emp_gap": 1743,
      "emp_gap_after_other": 1743,
      "month": 4,
      "n_states_suppressed": 15,
      "national_emp": 45720,
      "other_emp": 0,
      "other_emp_published": null,
      "states_dc_emp": 43977,
      "year": 2017
    },
    {
      "emp_gap": 1770,
      "emp_gap_after_other": 1770,
      "month": 5,
      "n_states_suppressed": 15,
      "national_emp": 47091,
      "other_emp": 0,
      "other_emp_published": null,
      "states_dc_emp": 45321,
      "year": 2017
    },
    {
      "emp_gap": 1829,
      "emp_gap_after_other": 1829,
      "month": 6,
      "n_states_suppressed": 15,
      "national_emp": 49192,
      "other_emp": 0,
      "other_emp_published": null,
      "states_dc_emp": 47363,
      "year": 2017
    },
    {
      "emp_gap": 1559,
      "emp_gap_after_other": 1559,
      "month": 7,
      "n_states_suppressed": 12,
      "national_emp": 49919,
      "other_emp": 0,
      "other_emp_published": null,
      "states_dc_emp": 48360,
      "year": 2017
    },
    {
      "emp_gap": 1585,
      "emp_gap_after_other": 1585,
      "month": 8,
      "n_states_suppressed": 12,
      "national_emp": 50151,
      "other_emp": 0,
      "other_emp_published": null,
      "states_dc_emp": 48566,
      "year": 2017
    },
    {
      "emp_gap": 1615,
      "emp_gap_after_other": 1615,
      "month": 9,
      "n_states_suppressed": 12,
      "national_emp": 49928,
      "other_emp": 0,
      "other_emp_published": null,
      "states_dc_emp": 48313,
      "year": 2017
    },
    {
      "emp_gap": 1708,
      "emp_gap_after_other": 1708,
      "month": 10,
      "n_states_suppressed": 14,
      "national_emp": 49924,
      "other_emp": 0,
      "other_emp_published": null,
      "states_dc_emp": 48216,
      "year": 2017
    },
    {
      "emp_gap": 1620,
      "emp_gap_after_other": 1620,
      "month": 11,
      "n_states_suppressed": 14,
      "national_emp": 49316,
      "other_emp": 0,
      "other_emp_published": null,
      "states_dc_emp": 47696,
      "year": 2017
    },
    {
      "emp_gap": 1587,
      "emp_gap_after_other": 1587,
      "month": 12,
      "n_states_suppressed": 14,
      "national_emp": 49403,
      "other_emp": 0,
      "other_emp_published": null,
      "states_dc_emp": 47816,
      "year": 2017
    },
    {
      "emp_gap": 1808,
      "emp_gap_after_other": 1808,
      "month": 1,
      "n_states_suppressed": 13,
      "national_emp": 48629,
      "other_emp": 0,
      "other_emp_published": null,
      "states_dc_emp": 46821,
      "year": 2018
    },
    {
      "emp_gap": 1825,
      "emp_gap_after_other": 1825,
      "month": 2,
      "n_states_suppressed": 13,
      "national_emp": 48602,
      "other_emp": 0,
      "other_emp_published": null,
      "states_dc_emp": 46777,
      "year": 2018
    },
    {
      "emp_gap": 1805,
      "emp_gap_after_other": 1805,
      "month": 3,
      "n_states_suppressed": 13,
      "national_emp": 48139,
      "other_emp": 0,
      "other_emp_published": null,
      "states_dc_emp": 46334,
      "year": 2018
    },
    {
      "emp_gap": 1681,
      "emp_gap_after_other": 1681,
      "month": 4,
      "n_states_suppressed": 13,
      "national_emp": 46585,
      "other_emp": 0,
      "other_emp_published": null,
      "states_dc_emp": 44904,
      "year": 2018
    },
    {
      "emp_gap": 1745,
      "emp_gap_after_other": 1745,
      "month": 5,
      "n_states_suppressed": 13,
      "national_emp": 48067,
      "other_emp": 0,
      "other_emp_published": null,
      "states_dc_emp": 46322,
      "year": 2018
    },
    {
      "emp_gap": 1776,
      "emp_gap_after_other": 1776,
      "month": 6,
      "n_states_suppressed": 13,
      "national_emp": 49784,
      "other_emp": 0,
      "other_emp_published": null,
      "states_dc_emp": 48008,
      "year": 2018
    },
    {
      "emp_gap": 2537,
      "emp_gap_after_other": 2537,
      "month": 7,
      "n_states_suppressed": 15,
      "national_emp": 50060,
      "other_emp": 0,
      "other_emp_published": null,
      "states_dc_emp": 47523,
      "year": 2018
    },
    {
      "emp_gap": 2580,
      "emp_gap_after_other": 2580,
      "month": 8,
      "n_states_suppressed": 15,
      "national_emp": 50311,
      "other_emp": 0,
      "other_emp_published": null,
      "states_dc_emp": 47731,
      "year": 2018
    },
    {
      "emp_gap": 2525,
      "emp_gap_after_other": 2525,
      "month": 9,
      "n_states_suppressed": 15,
      "national_emp": 49801,
      "other_emp": 0,
      "other_emp_published": null,
      "states_dc_emp": 47276,
      "year": 2018
    },
    {
      "emp_gap": 2711,
      "emp_gap_after_other": 2711,
      "month": 10,
      "n_states_suppressed": 15,
      "national_emp": 49838,
      "other_emp": 0,
      "other_emp_published": null,
      "states_dc_emp": 47127,
      "year": 2018
    },
    {
      "emp_gap": 2679,
      "emp_gap_after_other": 2679,
      "month": 11,
      "n_states_suppressed": 15,
      "national_emp": 48955,
      "other_emp": 0,
      "other_emp_published": null,
      "states_dc_emp": 46276,
      "year": 2018
    },
    {
      "emp_gap": 2689,
      "emp_gap_after_other": 2689,
      "month": 12,
      "n_states_suppressed": 15,
      "national_emp": 48669,
      "other_emp": 0,
      "other_emp_published": null,
      "states_dc_emp": 45980,
      "year": 2018
    },
    {
      "emp_gap": 2557,
      "emp_gap_after_other": 2557,
      "month": 1,
      "n_states_suppressed": 14,
      "national_emp": 47737,
      "other_emp": 0,
      "other_emp_published": 0,
      "states_dc_emp": 45180,
      "year": 2019
    },
    {
      "emp_gap": 2551,
      "emp_gap_after_other": 2551,
      "month": 2,
      "n_states_suppressed": 14,
      "national_emp": 47430,
      "other_emp": 0,
      "other_emp_published": 0,
      "states_dc_emp": 44879,
      "year": 2019
    },
    {
      "emp_gap": 2617,
      "emp_gap_after_other": 2617,
      "month": 3,
      "n_states_suppressed": 14,
      "national_emp": 47066,
      "other_emp": 0,
      "other_emp_published": 0,
      "states_dc_emp": 44449,
      "year": 2019
    },
    {
      "emp_gap": 1696,
      "emp_gap_after_other": 1696,
      "month": 4,
      "n_states_suppressed": 13,
      "national_emp": 45836,
      "other_emp": 0,
      "other_emp_published": 0,
      "states_dc_emp": 44140,
      "year": 2019
    },
    {
      "emp_gap": 1741,
      "emp_gap_after_other": 1741,
      "month": 5,
      "n_states_suppressed": 13,
      "national_emp": 47129,
      "other_emp": 0,
      "other_emp_published": 0,
      "states_dc_emp": 45388,
      "year": 2019
    },
    {
      "emp_gap": 1870,
      "emp_gap_after_other": 1870,
      "month": 6,
      "n_states_suppressed": 13,
      "national_emp": 48816,
      "other_emp": 0,
      "other_emp_published": 0,
      "states_dc_emp": 46946,
      "year": 2019
    },
    {
      "emp_gap": 785,
      "emp_gap_after_other": 785,
      "month": 7,
      "n_states_suppressed": 9,
      "national_emp": 49605,
      "other_emp": 0,
      "other_emp_published": 0,
      "states_dc_emp": 48820,
      "year": 2019
    },
    {
      "emp_gap": 828,
      "emp_gap_after_other": 828,
      "month": 8,
      "n_states_suppressed": 9,
      "national_emp": 49886,
      "other_emp": 0,
      "other_emp_published": 0,
      "states_dc_emp": 49058,
      "year": 2019
    },
    {
      "emp_gap": 807,
      "emp_gap_after_other": 807,
      "month": 9,
      "n_states_suppressed": 9,
      "national_emp": 49510,
      "other_emp": 0,
      "other_emp_published": 0,
      "states_dc_emp": 48703,
      "year": 2019
    },
    {
      "emp_gap": 1627,
      "emp_gap_after_other": 1627,
      "month": 10,
      "n_states_suppressed": 13,
      "national_emp": 49246,
      "other_emp": 0,
      "other_emp_published": 0,
      "states_dc_emp": 47619,
      "year": 2019
    },
    {
      "emp_gap": 1639,
      "emp_gap_after_other": 1639,
      "month": 11,
      "n_states_suppressed": 13,
      "national_emp": 48861,
      "other_emp": 0,
      "other_emp_published": 0,
      "states_dc_emp": 47222,
      "year": 2019
    },
    {
      "emp_gap": 1518,
      "emp_gap_after_other": 1518,
      "month": 12,
      "n_states_suppressed": 13,
      "national_emp": 47981,
      "other_emp": 0,
      "other_emp_published": 0,
      "states_dc_emp": 46463,
      "year": 2019
    },
    {
      "emp_gap": 696,
      "emp_gap_after_other": 696,
      "month": 1,
      "n_states_suppressed": 11,
      "national_emp": 46891,
      "other_emp": 0,
      "other_emp_published": 0,
      "states_dc_emp": 46195,
      "year": 2020
    },
    {
      "emp_gap": 736,
      "emp_gap_after_other": 736,
      "month": 2,
      "n_states_suppressed": 11,
      "national_emp": 46549,
      "other_emp": 0,
      "other_emp_published": 0,
      "states_dc_emp": 45813,
      "year": 2020
    },
    {
      "emp_gap": 710,
      "emp_gap_after_other": 710,
      "month": 3,
      "n_states_suppressed": 11,
      "national_emp": 46073,
      "other_emp": 0,
      "other_emp_published": 0,
      "states_dc_emp": 45363,
      "year": 2020
    },
    {
      "emp_gap": 915,
      "emp_gap_after_other": 915,
      "month": 4,
      "n_states_suppressed": 10,
      "national_emp": 43563,
      "other_emp": 0,
      "other_emp_published": 0,
      "states_dc_emp": 42648,
      "year": 2020
    },
    {
      "emp_gap": 996,
      "emp_gap_after_other": 996,
      "month": 5,
      "n_states_suppressed": 10,
      "national_emp": 45867,
      "other_emp": 0,
      "other_emp_published": 0,
      "states_dc_emp": 44871,
      "year": 2020
    },
    {
      "emp_gap": 1049,
      "emp_gap_after_other": 1049,
      "month": 6,
      "n_states_suppressed": 10,
      "national_emp": 47231,
      "other_emp": 0,
      "other_emp_published": 0,
      "states_dc_emp": 46182,
      "year": 2020
    },
    {
      "emp_gap": 1198,
      "emp_gap_after_other": 1198,
      "month": 7,
      "n_states_suppressed": 13,
      "national_emp": 47722,
      "other_emp": 0,
      "other_emp_published": 0,
      "states_dc_emp": 46524,
      "year": 2020
    },
    {
      "emp_gap": 1223,
      "emp_gap_after_other": 1223,
      "month": 8,
      "n_states_suppressed": 13,
      "national_emp": 48161,
      "other_emp": 0,
      "other_emp_published": 0,
      "states_dc_emp": 46938,
      "year": 2020
    },
    {
      "emp_gap": 1195,
      "emp_gap_after_other": 1195,
      "month": 9,
      "n_states_suppressed": 13,
      "national_emp": 47702,
      "other_emp": 0,
      "other_emp_published": 0,
      "states_dc_emp": 46507,
      "year": 2020
    },
    {
      "emp_gap": 1302,
      "emp_gap_after_other": 1302,
      "month": 10,
      "n_states_suppressed": 15,
      "national_emp": 48159,
      "other_emp": 0,
      "other_emp_published": 0,
      "states_dc_emp": 46857,
      "year": 2020
    },
    {
      "emp_gap": 1282,
      "emp_gap_after_other": 1282,
      "month": 11,
      "n_states_suppressed": 15,
      "national_emp": 47784,
      "other_emp": 0,
      "other_emp_published": 0,
      "states_dc_emp": 46502,
      "year": 2020
    },
    {
      "emp_gap": 1248,
      "emp_gap_after_other": 1248,
      "month": 12,
      "n_states_suppressed": 15,
      "national_emp": 47525,
      "other_emp": 0,
      "other_emp_published": 0,
      "states_dc_emp": 46277,
      "year": 2020
    },
    {
      "emp_gap": 1048,
      "emp_gap_after_other": 1048,
      "month": 1,
      "n_states_suppressed": 14,
      "national_emp": 46415,
      "other_emp": 0,
      "other_emp_published": 0,
      "states_dc_emp": 45367,
      "year": 2021
    },
    {
      "emp_gap": 1079,
      "emp_gap_after_other": 1079,
      "month": 2,
      "n_states_suppressed": 14,
      "national_emp": 45893,
      "other_emp": 0,
      "other_emp_published": 0,
      "states_dc_emp": 44814,
      "year": 2021
    },
    {
      "emp_gap": 1055,
      "emp_gap_after_other": 1055,
      "month": 3,
      "n_states_suppressed": 14,
      "national_emp": 45817,
      "other_emp": 0,
      "other_emp_published": 0,
      "states_dc_emp": 44762,
      "year": 2021
    },
    {
      "emp_gap": 924,
      "emp_gap_after_other": 924,
      "month": 4,
      "n_states_suppressed": 12,
      "national_emp": 45027,
      "other_emp": 0,
      "other_emp_published": 0,
      "states_dc_emp": 44103,
      "year": 2021
    },
    {
      "emp_gap": 979,
      "emp_gap_after_other": 979,
      "month": 5,
      "n_states_suppressed": 12,
      "national_emp": 45884,
      "other_emp": 0,
      "other_emp_published": 0,
      "states_dc_emp": 44905,
      "year": 2021
    },
    {
      "emp_gap": 1029,
      "emp_gap_after_other": 1029,
      "month": 6,
      "n_states_suppressed": 12,
      "national_emp": 47171,
      "other_emp": 0,
      "other_emp_published": 0,
      "states_dc_emp": 46142,
      "year": 2021
    },
    {
      "emp_gap": 1257,
      "emp_gap_after_other": 1257,
      "month": 7,
      "n_states_suppressed": 14,
      "national_emp": 47823,
      "other_emp": 0,
      "other_emp_published": 0,
      "states_dc_emp": 46566,
      "year": 2021
    },
    {
      "emp_gap": 1239,
      "emp_gap_after_other": 1239,
      "month": 8,
      "n_states_suppressed": 14,
      "national_emp": 47532,
      "other_emp": 0,
      "other_emp_published": 0,
      "states_dc_emp": 46293,
      "year": 2021
    },
    {
      "emp_gap": 1205,
      "emp_gap_after_other": 1205,
      "month": 9,
      "n_states_suppressed": 14,
      "national_emp": 47147,
      "other_emp": 0,
      "other_emp_published": 0,
      "states_dc_emp": 45942,
      "year": 2021
    },
    {
      "emp_gap": 1591,
      "emp_gap_after_other": 1591,
      "month": 10,
      "n_states_suppressed": 12,
      "national_emp": 47286,
      "other_emp": 0,
      "other_emp_published": 0,
      "states_dc_emp": 45695,
      "year": 2021
    },
    {
      "emp_gap": 1475,
      "emp_gap_after_other": 1475,
      "month": 11,
      "n_states_suppressed": 12,
      "national_emp": 46547,
      "other_emp": 0,
      "other_emp_published": 0,
      "states_dc_emp": 45072,
      "year": 2021
    },
    {
      "emp_gap": 1459,
      "emp_gap_after_other": 1459,
      "month": 12,
      "n_states_suppressed": 12,
      "national_emp": 46321,
      "other_emp": 0,
      "other_emp_published": 0,
      "states_dc_emp": 44862,
      "year": 2021
    },
    {
      "emp_gap": 873,
      "emp_gap_after_other": 873,
      "month": 1,
      "n_states_suppressed": 13,
      "national_emp": 44998,
      "other_emp": 0,
      "other_emp_published": 0,
      "states_dc_emp": 44125,
      "year": 2022
    },
    {
      "emp_gap": 885,
      "emp_gap_after_other": 885,
      "month": 2,
      "n_states_suppressed": 13,
      "national_emp": 45570,
      "other_emp": 0,
      "other_emp_published": 0,
      "states_dc_emp": 44685,
      "year": 2022
    },
    {
      "emp_gap": 872,
      "emp_gap_after_other": 872,
      "month": 3,
      "n_states_suppressed": 13,
      "national_emp": 45097,
      "other_emp": 0,
      "other_emp_published": 0,
      "states_dc_emp": 44225,
      "year": 2022
    },
    {
      "emp_gap": 1139,
      "emp_gap_after_other": 1139,
      "month": 4,
      "n_states_suppressed": 13,
      "national_emp": 44183,
      "other_emp": 0,
      "other_emp_published": 0,
      "states_dc_emp": 43044,
      "year": 2022
    },
    {
      "emp_gap": 1240,
      "emp_gap_after_other": 1240,
      "month": 5,
      "n_states_suppressed": 13,
      "national_emp": 44873,
      "other_emp": 0,
      "other_emp_published": 0,
      "states_dc_emp": 43633,
      "year": 2022
    },
    {
      "emp_gap": 1335,
      "emp_gap_after_other": 1335,
      "month": 6,
      "n_states_suppressed": 13,
      "national_emp": 46150,
      "other_emp": 0,
      "other_emp_published": 0,
      "states_dc_emp": 44815,
      "year": 2022
    },
    {
      "emp_gap": 960,
      "emp_gap_after_other": 960,
      "month": 7,
      "n_states_suppressed": 13,
      "national_emp": 46632,
      "other_emp": 0,
      "other_emp_published": 0,
      "states_dc_emp": 45672,
      "year": 2022
    },
    {
      "emp_gap": 961,
      "emp_gap_after_other": 961,
      "month": 8,
      "n_states_suppressed": 13,
      "national_emp": 46557,
      "other_emp": 0,
      "other_emp_published": 0,
      "states_dc_emp": 45596,
      "year": 2022
    },
    {
      "emp_gap": 953,
      "emp_gap_after_other": 953,
      "month": 9,
      "n_states_suppressed": 13,
      "national_emp": 46504,
      "other_emp": 0,
      "other_emp_published": 0,
      "states_dc_emp": 45551,
      "year": 2022
    },
    {
      "emp_gap": 1431,
      "emp_gap_after_other": 1431,
      "month": 10,
      "n_states_suppressed": 14,
      "national_emp": 46051,
      "other_emp": 0,
      "other_emp_published": 0,
      "states_dc_emp": 44620,
      "year": 2022
    },
    {
      "emp_gap": 1370,
      "emp_gap_after_other": 1370,
      "month": 11,
      "n_states_suppressed": 14,
      "national_emp": 45109,
      "other_emp": 0,
      "other_emp_published": 0,
      "states_dc_emp": 43739,
      "year": 2022
    },
    {
      "emp_gap": 1338,
      "emp_gap_after_other": 1338,
      "month": 12,
      "n_states_suppressed": 14,
      "national_emp": 44817,
      "other_emp": 0,
      "other_emp_published": 0,
      "states_dc_emp": 43479,
      "year": 2022
    },
    {
      "emp_gap": 1491,
      "emp_gap_after_other": 1491,
      "month": 1,
      "n_states_suppressed": 13,
      "national_emp": 43628,
      "other_emp": 0,
      "other_emp_published": 0,
      "states_dc_emp": 42137,
      "year": 2023
    },
    {
      "emp_gap": 1530,
      "emp_gap_after_other": 1530,
      "month": 2,
      "n_states_suppressed": 13,
      "national_emp": 43822,
      "other_emp": 0,
      "other_emp_published": 0,
      "states_dc_emp": 42292,
      "year": 2023
    },
    {
      "emp_gap": 1474,
      "emp_gap_after_other": 1474,
      "month": 3,
      "n_states_suppressed": 13,
      "national_emp": 43398,
      "other_emp": 0,
      "other_emp_published": 0,
      "states_dc_emp": 41924,
      "year": 2023
    },
    {
      "emp_gap": 1349,
      "emp_gap_after_other": 1349,
      "month": 4,
      "n_states_suppressed": 11,
      "national_emp": 42167,
      "other_emp": 0,
      "other_emp_published": 0,
      "states_dc_emp": 40818,
      "year": 2023
    },
    {
      "emp_gap": 1388,
      "emp_gap_after_other": 1388,
      "month": 5,
      "n_states_suppressed": 11,
      "national_emp": 43129,
      "other_emp": 0,
      "other_emp_published": 0,
      "states_dc_emp": 41741,
      "year": 2023
    },
    {
      "emp_gap": 1453,
      "emp_gap_after_other": 1453,
      "month": 6,
      "n_states_suppressed": 11,
      "national_emp": 44519,
      "other_emp": 0,
      "other_emp_published": 0,
      "states_dc_emp": 43066,
      "year": 2023
    },
    {
      "emp_gap": 1451,
      "emp_gap_after_other": 1451,
      "month": 7,
      "n_states_suppressed": 11,
      "national_emp": 44791,
      "other_emp": 0,
      "other_emp_published": 0,
      "states_dc_emp": 43340,
      "year": 2023
    },
    {
      "emp_gap": 1449,
      "emp_gap_after_other": 1449,
      "month": 8,
      "n_states_suppressed": 11,
      "national_emp": 44971,
      "other_emp": 0,
      "other_emp_published": 0,
      "states_dc_emp": 43522,
      "year": 2023
    },
    {
      "emp_gap": 1451,
      "emp_gap_after_other": 1451,
      "month": 9,
      "n_states_suppressed": 11,
      "national_emp": 44858,
      "other_emp": 0,
      "other_emp_published": 0,
      "states_dc_emp": 43407,
      "year": 2023
    },
    {
      "emp_gap": 1539,
      "emp_gap_after_other": 1539,
      "month": 10,
      "n_states_suppressed": 11,
      "national_emp": 44536,
      "other_emp": 0,
      "other_emp_published": 0,
      "states_dc_emp": 42997,
      "year": 2023
    },
    {
      "emp_gap": 1541,
      "emp_gap_after_other": 1541,
      "month": 11,
      "n_states_suppressed": 11,
      "national_emp": 43954,
      "other_emp": 0,
      "other_emp_published": 0,
      "states_dc_emp": 42413,
      "year": 2023
    },
    {
      "emp_gap": 1544,
      "emp_gap_after_other": 1544,
      "month": 12,
      "n_states_suppressed": 11,
      "national_emp": 43727,
      "other_emp": 0,
      "other_emp_published": 0,
      "states_dc_emp": 42183,
      "year": 2023
    },
    {
      "emp_gap": 1580,
      "emp_gap_after_other": 1580,
      "month": 1,
      "n_states_suppressed": 13,
      "national_emp": 42540,
      "other_emp": 0,
      "other_emp_published": 0,
      "states_dc_emp": 40960,
      "year": 2024
    },
    {
      "emp_gap": 1620,
      "emp_gap_after_other": 1620,
      "month": 2,
      "n_states_suppressed": 13,
      "national_emp": 42438,
      "other_emp": 0,
      "other_emp_published": 0,
      "states_dc_emp": 40818,
      "year": 2024
    },
    {
      "emp_gap": 1589,
      "emp_gap_after_other": 1589,
      "month": 3,
      "n_states_suppressed": 13,
      "national_emp": 41668,
      "other_emp": 0,
      "other_emp_published": 0,
      "states_dc_emp": 40079,
      "year": 2024
    },
    {
      "emp_gap": 1453,
      "emp_gap_after_other": 1453,
      "month": 4,
      "n_states_suppressed": 12,
      "national_emp": 40945,
      "other_emp": 0,
      "other_emp_published": 0,
      "states_dc_emp": 39492,
      "year": 2024
    },
    {
      "emp_gap": 1463,
      "emp_gap_after_other": 1463,
      "month": 5,
      "n_states_suppressed": 12,
      "national_emp": 42078,
      "other_emp": 0,
      "other_emp_published": 0,
      "states_dc_emp": 40615,
      "year": 2024
    },
    {
      "emp_gap": 1550,
      "emp_gap_after_other": 1550,
      "month": 6,
      "n_states_suppressed": 12,
      "national_emp": 43004,
      "other_emp": 0,
      "other_emp_published": 0,
      "states_dc_emp": 41454,
      "year": 2024
    },
    {
      "emp_gap": 1634,
      "emp_gap_after_other": 1634,
      "month": 7,
      "n_states_suppressed": 13,
      "national_emp": 43200,
      "other_emp": 0,
      "other_emp_published": 0,
      "states_dc_emp": 41566,
      "year": 2024
    },
    {
      "emp_gap": 1633,
      "emp_gap_after_other": 1633,
      "month": 8,
      "n_states_suppressed": 13,
      "national_emp": 43535,
      "other_emp": 0,
      "other_emp_published": 0,
      "states_dc_emp": 41902,
      "year": 2024
    },
    {
      "emp_gap": 1603,
      "emp_gap_after_other": 1603,
      "month": 9,
      "n_states_suppressed": 13,
      "national_emp": 43140,
      "other_emp": 0,
      "other_emp_published": 0,
      "states_dc_emp": 41537,
      "year": 2024
    },
    {
      "emp_gap": 1492,
      "emp_gap_after_other": 1492,
      "month": 10,
      "n_states_suppressed": 11,
      "national_emp": 42939,
      "other_emp": 0,
      "other_emp_published": 0,
      "states_dc_emp": 41447,
      "year": 2024
    },
    {
      "emp_gap": 1489,
      "emp_gap_after_other": 1489,
      "month": 11,
      "n_states_suppressed": 11,
      "national_emp": 42248,
      "other_emp": 0,
      "other_emp_published": 0,
      "states_dc_emp": 40759,
      "year": 2024
    },
    {
      "emp_gap": 1485,
      "emp_gap_after_other": 1485,
      "month": 12,
      "n_states_suppressed": 11,
      "national_emp": 41737,
      "other_emp": 0,
      "other_emp_published": 0,
      "states_dc_emp": 40252,
      "year": 2024
    }
  ],
  "non_state_area_containment": {
    "basis": "measured on 8 quarter(s) in which a non-state area publishes a non-zero establishment count: national minus states+DC equals that area's own count in 0 of them and equals 0 in 8 of them, giving the verdict outside_national_total, on which the non-state amount is left out of both comparison tables' gap columns",
    "per_quarter": [
      {
        "estab_gap": 0,
        "national_estabs": 8236,
        "other_published": 1,
        "qtr": 1,
        "states_dc_estabs": 8236,
        "year": 2017
      },
      {
        "estab_gap": 0,
        "national_estabs": 8262,
        "other_published": 1,
        "qtr": 2,
        "states_dc_estabs": 8262,
        "year": 2017
      },
      {
        "estab_gap": 0,
        "national_estabs": 8289,
        "other_published": 1,
        "qtr": 3,
        "states_dc_estabs": 8289,
        "year": 2017
      },
      {
        "estab_gap": 0,
        "national_estabs": 8286,
        "other_published": 2,
        "qtr": 4,
        "states_dc_estabs": 8286,
        "year": 2017
      },
      {
        "estab_gap": 0,
        "national_estabs": 8207,
        "other_published": 1,
        "qtr": 1,
        "states_dc_estabs": 8207,
        "year": 2018
      },
      {
        "estab_gap": 0,
        "national_estabs": 8277,
        "other_published": 1,
        "qtr": 2,
        "states_dc_estabs": 8277,
        "year": 2018
      },
      {
        "estab_gap": 0,
        "national_estabs": 8303,
        "other_published": 1,
        "qtr": 3,
        "states_dc_estabs": 8303,
        "year": 2018
      },
      {
        "estab_gap": 0,
        "national_estabs": 8301,
        "other_published": 1,
        "qtr": 4,
        "states_dc_estabs": 8301,
        "year": 2018
      }
    ],
    "quarters_discriminating": 8,
    "quarters_gap_equals_non_state_amount": 0,
    "quarters_gap_is_zero": 8,
    "quarters_non_state_amount_unpublished": 0,
    "subtraction_applied": false,
    "verdict": "outside_national_total"
  },
  "panel_structure": {
    "months_covered": 96,
    "national_months_present": 96,
    "national_months_unpublished_emp": 0,
    "national_quarters_present": 32,
    "national_quarters_unpublished_estabs": 0,
    "other_months_unpublished_emp": 24,
    "other_quarters_unpublished_estabs": 0,
    "other_state_level_areas": [
      {
        "area_fips": "72000",
        "area_months": 24,
        "area_title": "Puerto Rico -- Statewide"
      }
    ],
    "panel_rows": 4836,
    "qtrly_estabs_constant_within_area_quarter": true,
    "quarters_covered": 32,
    "rows_by_area_class": {
      "national": 96,
      "other_state_level": 24,
      "states_dc": 4716
    },
    "states_dc_area_months_absent": 84,
    "states_dc_areas": 50,
    "states_dc_areas_per_month": {
      "constant": false,
      "max": 50,
      "min": 48
    },
    "states_dc_short_span_areas": [
      {
        "area_fips": "10000",
        "area_title": "Delaware -- Statewide",
        "months": 60
      },
      {
        "area_fips": "38000",
        "area_title": "North Dakota -- Statewide",
        "months": 48
      }
    ],
    "states_dc_suppressed_cells": 1227,
    "states_dc_suppressed_per_month": {
      "max": 15,
      "min": 9
    },
    "states_dc_unpublished_emp_cells": 1227,
    "states_dc_unpublished_emp_is_exactly_suppressed": true,
    "states_dc_unpublished_estab_cells": 0
  },
  "quarter_table": [
    {
      "estab_gap": 0,
      "estab_gap_after_other": 0,
      "national_estabs": 8236,
      "other_estabs": 0,
      "other_estabs_published": 1,
      "qtr": 1,
      "states_dc_estabs": 8236,
      "year": 2017
    },
    {
      "estab_gap": 0,
      "estab_gap_after_other": 0,
      "national_estabs": 8262,
      "other_estabs": 0,
      "other_estabs_published": 1,
      "qtr": 2,
      "states_dc_estabs": 8262,
      "year": 2017
    },
    {
      "estab_gap": 0,
      "estab_gap_after_other": 0,
      "national_estabs": 8289,
      "other_estabs": 0,
      "other_estabs_published": 1,
      "qtr": 3,
      "states_dc_estabs": 8289,
      "year": 2017
    },
    {
      "estab_gap": 0,
      "estab_gap_after_other": 0,
      "national_estabs": 8286,
      "other_estabs": 0,
      "other_estabs_published": 2,
      "qtr": 4,
      "states_dc_estabs": 8286,
      "year": 2017
    },
    {
      "estab_gap": 0,
      "estab_gap_after_other": 0,
      "national_estabs": 8207,
      "other_estabs": 0,
      "other_estabs_published": 1,
      "qtr": 1,
      "states_dc_estabs": 8207,
      "year": 2018
    },
    {
      "estab_gap": 0,
      "estab_gap_after_other": 0,
      "national_estabs": 8277,
      "other_estabs": 0,
      "other_estabs_published": 1,
      "qtr": 2,
      "states_dc_estabs": 8277,
      "year": 2018
    },
    {
      "estab_gap": 0,
      "estab_gap_after_other": 0,
      "national_estabs": 8303,
      "other_estabs": 0,
      "other_estabs_published": 1,
      "qtr": 3,
      "states_dc_estabs": 8303,
      "year": 2018
    },
    {
      "estab_gap": 0,
      "estab_gap_after_other": 0,
      "national_estabs": 8301,
      "other_estabs": 0,
      "other_estabs_published": 1,
      "qtr": 4,
      "states_dc_estabs": 8301,
      "year": 2018
    },
    {
      "estab_gap": 0,
      "estab_gap_after_other": 0,
      "national_estabs": 8119,
      "other_estabs": 0,
      "other_estabs_published": 0,
      "qtr": 1,
      "states_dc_estabs": 8119,
      "year": 2019
    },
    {
      "estab_gap": 0,
      "estab_gap_after_other": 0,
      "national_estabs": 8131,
      "other_estabs": 0,
      "other_estabs_published": 0,
      "qtr": 2,
      "states_dc_estabs": 8131,
      "year": 2019
    },
    {
      "estab_gap": 0,
      "estab_gap_after_other": 0,
      "national_estabs": 8181,
      "other_estabs": 0,
      "other_estabs_published": 0,
      "qtr": 3,
      "states_dc_estabs": 8181,
      "year": 2019
    },
    {
      "estab_gap": 0,
      "estab_gap_after_other": 0,
      "national_estabs": 8182,
      "other_estabs": 0,
      "other_estabs_published": 0,
      "qtr": 4,
      "states_dc_estabs": 8182,
      "year": 2019
    },
    {
      "estab_gap": 0,
      "estab_gap_after_other": 0,
      "national_estabs": 8037,
      "other_estabs": 0,
      "other_estabs_published": 0,
      "qtr": 1,
      "states_dc_estabs": 8037,
      "year": 2020
    },
    {
      "estab_gap": 0,
      "estab_gap_after_other": 0,
      "national_estabs": 8017,
      "other_estabs": 0,
      "other_estabs_published": 0,
      "qtr": 2,
      "states_dc_estabs": 8017,
      "year": 2020
    },
    {
      "estab_gap": 0,
      "estab_gap_after_other": 0,
      "national_estabs": 8070,
      "other_estabs": 0,
      "other_estabs_published": 0,
      "qtr": 3,
      "states_dc_estabs": 8070,
      "year": 2020
    },
    {
      "estab_gap": 0,
      "estab_gap_after_other": 0,
      "national_estabs": 8067,
      "other_estabs": 0,
      "other_estabs_published": 0,
      "qtr": 4,
      "states_dc_estabs": 8067,
      "year": 2020
    },
    {
      "estab_gap": 0,
      "estab_gap_after_other": 0,
      "national_estabs": 7976,
      "other_estabs": 0,
      "other_estabs_published": 0,
      "qtr": 1,
      "states_dc_estabs": 7976,
      "year": 2021
    },
    {
      "estab_gap": 0,
      "estab_gap_after_other": 0,
      "national_estabs": 7983,
      "other_estabs": 0,
      "other_estabs_published": 0,
      "qtr": 2,
      "states_dc_estabs": 7983,
      "year": 2021
    },
    {
      "estab_gap": 0,
      "estab_gap_after_other": 0,
      "national_estabs": 8011,
      "other_estabs": 0,
      "other_estabs_published": 0,
      "qtr": 3,
      "states_dc_estabs": 8011,
      "year": 2021
    },
    {
      "estab_gap": 0,
      "estab_gap_after_other": 0,
      "national_estabs": 8026,
      "other_estabs": 0,
      "other_estabs_published": 0,
      "qtr": 4,
      "states_dc_estabs": 8026,
      "year": 2021
    },
    {
      "estab_gap": 0,
      "estab_gap_after_other": 0,
      "national_estabs": 7996,
      "other_estabs": 0,
      "other_estabs_published": 0,
      "qtr": 1,
      "states_dc_estabs": 7996,
      "year": 2022
    },
    {
      "estab_gap": 0,
      "estab_gap_after_other": 0,
      "national_estabs": 7984,
      "other_estabs": 0,
      "other_estabs_published": 0,
      "qtr": 2,
      "states_dc_estabs": 7984,
      "year": 2022
    },
    {
      "estab_gap": 0,
      "estab_gap_after_other": 0,
      "national_estabs": 8037,
      "other_estabs": 0,
      "other_estabs_published": 0,
      "qtr": 3,
      "states_dc_estabs": 8037,
      "year": 2022
    },
    {
      "estab_gap": 0,
      "estab_gap_after_other": 0,
      "national_estabs": 8043,
      "other_estabs": 0,
      "other_estabs_published": 0,
      "qtr": 4,
      "states_dc_estabs": 8043,
      "year": 2022
    },
    {
      "estab_gap": 0,
      "estab_gap_after_other": 0,
      "national_estabs": 7990,
      "other_estabs": 0,
      "other_estabs_published": 0,
      "qtr": 1,
      "states_dc_estabs": 7990,
      "year": 2023
    },
    {
      "estab_gap": 0,
      "estab_gap_after_other": 0,
      "national_estabs": 7930,
      "other_estabs": 0,
      "other_estabs_published": 0,
      "qtr": 2,
      "states_dc_estabs": 7930,
      "year": 2023
    },
    {
      "estab_gap": 0,
      "estab_gap_after_other": 0,
      "national_estabs": 7915,
      "other_estabs": 0,
      "other_estabs_published": 0,
      "qtr": 3,
      "states_dc_estabs": 7915,
      "year": 2023
    },
    {
      "estab_gap": 0,
      "estab_gap_after_other": 0,
      "national_estabs": 7910,
      "other_estabs": 0,
      "other_estabs_published": 0,
      "qtr": 4,
      "states_dc_estabs": 7910,
      "year": 2023
    },
    {
      "estab_gap": 0,
      "estab_gap_after_other": 0,
      "national_estabs": 7713,
      "other_estabs": 0,
      "other_estabs_published": 0,
      "qtr": 1,
      "states_dc_estabs": 7713,
      "year": 2024
    },
    {
      "estab_gap": 0,
      "estab_gap_after_other": 0,
      "national_estabs": 7710,
      "other_estabs": 0,
      "other_estabs_published": 0,
      "qtr": 2,
      "states_dc_estabs": 7710,
      "year": 2024
    },
    {
      "estab_gap": 0,
      "estab_gap_after_other": 0,
      "national_estabs": 7713,
      "other_estabs": 0,
      "other_estabs_published": 0,
      "qtr": 3,
      "states_dc_estabs": 7713,
      "year": 2024
    },
    {
      "estab_gap": 0,
      "estab_gap_after_other": 0,
      "national_estabs": 7684,
      "other_estabs": 0,
      "other_estabs_published": 0,
      "qtr": 4,
      "states_dc_estabs": 7684,
      "year": 2024
    }
  ],
  "reason": "every one of the 96 testable month(s) carries at least one suppressed state cell, so the employment identity is untestable on a complete published state sum",
  "verdict_sentence": "decline: across the 32 quarter(s) and 96 month(s) the panel covers (2017-01 through 2024-12), the national establishment count for industry 113310 and own_code 5 ('Private') equals the states+DC published sum in 32 of 32 evaluable quarter(s), with 0 unevaluable and 0 states+DC establishment cell(s) unpublished; the panel carries 1 non-state area(s) (Puerto Rico -- Statewide) across 24 area-month(s), measured as outside_national_total on 8 discriminating quarter(s); each of the 96 testable month(s) carries between 9 and 15 suppressed states+DC cells and an employment gap after non-state areas of at least 696; every one of the 96 testable month(s) carries at least one suppressed state cell, so the employment identity is untestable on a complete published state sum."
}
```

_Extracts: 0; summary `generated_utc` 2026-09-04T23:13:56+00:00._

### `qcew_panel`

**access**:

```json
{
  "reason": null,
  "route": "derived from qcew_routes slice extracts",
  "status": "verified"
}
```

**coverage_span**:

```json
{
  "covered": "2017-01..2024-12",
  "published_end": "2024-12",
  "published_start": "2017-01",
  "uncovered": "",
  "window_end": "2024-12",
  "window_start": "2017-01"
}
```

**findings**:

```json
{
  "disclosure_code_values": [
    {
      "disclosure_code": "",
      "emplvl_published_nonzero_rows": 3558,
      "emplvl_published_rows": 3558,
      "emplvl_raw_nonzero_rows": 3558,
      "panel_rows": 3558,
      "qtrly_estabs_positive_rows": 3558,
      "states_dc_rows": 3462
    },
    {
      "disclosure_code": "-",
      "emplvl_published_nonzero_rows": 0,
      "emplvl_published_rows": 27,
      "emplvl_raw_nonzero_rows": 0,
      "panel_rows": 27,
      "qtrly_estabs_positive_rows": 0,
      "states_dc_rows": 27
    },
    {
      "disclosure_code": "N",
      "emplvl_published_nonzero_rows": 0,
      "emplvl_published_rows": 0,
      "emplvl_raw_nonzero_rows": 0,
      "panel_rows": 1251,
      "qtrly_estabs_positive_rows": 1251,
      "states_dc_rows": 1227
    }
  ],
  "estabs_survive_suppression_share": 1.0,
  "filter_predicates": [
    "industry_code == '113310'; retained 59112 of 59112 rows",
    "own_code == '5' (qcew_codes.findings.private_own_code); retained 58932 of 59112 rows",
    "area_fips.str.ends_with('000'); retained 1612 of 58932 rows"
  ],
  "months_covered": 96,
  "notes": "Panel construction. 32 recorded slice CSVs contribute the raw frame; the predicates in filter_predicates are applied to it in the order listed there, each one recording what it retained, and the surviving quarterly rows unpivot to 4836 monthly rows (96 national, 24 other_state_level, 4716 states_dc). Suppression flag. `suppressed` is true where the published disclosure_code strips to 'N', and false for every other value, including an empty one: the flag is the published code alone, and no cell-count or concentration threshold enters it (Global Constraints, §2.2 row 1). This audit fetched no titles file for this column: qcew_codes.findings.titles_available carries null for disclosure_code, which records that qcew_codes sent no titles request for it -- not that no such file is published, which no request in either script tests. The code values below therefore come from the retained rows alone. Values observed on the retained rows, with what each carries: '' on 3558 monthly rows (3462 states_dc, 3558 with qtrly_estabs > 0, 3558 with a nonzero employment level in the source month columns, 3558 with one published into the panel), '-' on 27 monthly rows (27 states_dc, 0 with qtrly_estabs > 0, 0 with a nonzero employment level in the source month columns, 0 with one published into the panel), 'N' on 1251 monthly rows (1227 states_dc, 1251 with qtrly_estabs > 0, 0 with a nonzero employment level in the source month columns, 0 with one published into the panel). Employment on a suppressed row is written null in the panel (INV-003), so of the two counts above, emplvl_raw_nonzero_rows is taken before that null-out and emplvl_published_nonzero_rows after it; the difference between those two per code is measured here, not assumed from what a suppressed row is expected to publish. Denominator. suppression_share_overall, _by_state and _by_month divide by the 4716 states_dc monthly cells present in the panel, not by the 4896 cells of a 51-area x 96-month grid; state_month_cell_coverage decomposes the difference. states_dc areas with no retained row in any quarter: 1 (11000). states_dc areas with rows for part of the window only: 2 (10000: 36 months absent; 38000: 48 months absent). A per-state share for any of those areas is over the months it publishes. Run lengths. suppressed_run_lengths counts maximal runs of consecutive suppressed months within one states_dc area, where a run ends at an unsuppressed month and equally at an absent one. Counted across the states_dc areas over the 96-month window, the number of interior month gaps falling inside an area's own span of published rows is 0 (state_month_cell_coverage.interior_month_gaps). Establishment survival. estabs_survive_suppression_share is measured over the 1227 suppressed states_dc monthly cells, of which 1227 report qtrly_estabs > 0. Geography. states_covered counts the distinct states_dc area codes present, 50 of the 51 in _common.STATE_AREAS; other_state_level_areas enumerates every non-national area ending '000' that is outside that set: 72000 (Puerto Rico -- Statewide). This script draws no conclusion from either count about the composition of the US000 national total.",
  "other_state_level_areas": [
    {
      "area_fips": "72000",
      "area_title": "Puerto Rico -- Statewide"
    }
  ],
  "panel_rows": 4836,
  "state_month_cell_coverage": {
    "absent_months_by_area": {
      "10000": 36,
      "11000": 96,
      "38000": 48
    },
    "areas_with_no_rows": [
      "11000"
    ],
    "cells_present": 4716,
    "grid_areas": 51,
    "grid_cells": 4896,
    "grid_months": 96,
    "interior_month_gaps": 0
  },
  "states_covered": 50,
  "suppressed_run_lengths": {
    "12": 4,
    "15": 2,
    "18": 1,
    "21": 1,
    "24": 1,
    "27": 2,
    "3": 16,
    "30": 2,
    "39": 1,
    "48": 1,
    "51": 1,
    "54": 1,
    "57": 2,
    "6": 7,
    "63": 1,
    "75": 1,
    "9": 6,
    "96": 4
  },
  "suppression_share_by_month": {
    "2017-01": 0.2857142857142857,
    "2017-02": 0.2857142857142857,
    "2017-03": 0.2857142857142857,
    "2017-04": 0.30612244897959184,
    "2017-05": 0.30612244897959184,
    "2017-06": 0.30612244897959184,
    "2017-07": 0.24489795918367346,
    "2017-08": 0.24489795918367346,
    "2017-09": 0.24489795918367346,
    "2017-10": 0.2857142857142857,
    "2017-11": 0.2857142857142857,
    "2017-12": 0.2857142857142857,
    "2018-01": 0.2653061224489796,
    "2018-02": 0.2653061224489796,
    "2018-03": 0.2653061224489796,
    "2018-04": 0.2653061224489796,
    "2018-05": 0.2653061224489796,
    "2018-06": 0.2653061224489796,
    "2018-07": 0.30612244897959184,
    "2018-08": 0.30612244897959184,
    "2018-09": 0.30612244897959184,
    "2018-10": 0.30612244897959184,
    "2018-11": 0.30612244897959184,
    "2018-12": 0.30612244897959184,
    "2019-01": 0.2857142857142857,
    "2019-02": 0.2857142857142857,
    "2019-03": 0.2857142857142857,
    "2019-04": 0.2653061224489796,
    "2019-05": 0.2653061224489796,
    "2019-06": 0.2653061224489796,
    "2019-07": 0.1836734693877551,
    "2019-08": 0.1836734693877551,
    "2019-09": 0.1836734693877551,
    "2019-10": 0.2653061224489796,
    "2019-11": 0.2653061224489796,
    "2019-12": 0.2653061224489796,
    "2020-01": 0.22,
    "2020-02": 0.22,
    "2020-03": 0.22,
    "2020-04": 0.2,
    "2020-05": 0.2,
    "2020-06": 0.2,
    "2020-07": 0.26,
    "2020-08": 0.26,
    "2020-09": 0.26,
    "2020-10": 0.3,
    "2020-11": 0.3,
    "2020-12": 0.3,
    "2021-01": 0.28,
    "2021-02": 0.28,
    "2021-03": 0.28,
    "2021-04": 0.24,
    "2021-05": 0.24,
    "2021-06": 0.24,
    "2021-07": 0.28,
    "2021-08": 0.28,
    "2021-09": 0.28,
    "2021-10": 0.24,
    "2021-11": 0.24,
    "2021-12": 0.24,
    "2022-01": 0.2653061224489796,
    "2022-02": 0.2653061224489796,
    "2022-03": 0.2653061224489796,
    "2022-04": 0.2653061224489796,
    "2022-05": 0.2653061224489796,
    "2022-06": 0.2653061224489796,
    "2022-07": 0.2653061224489796,
    "2022-08": 0.2653061224489796,
    "2022-09": 0.2653061224489796,
    "2022-10": 0.2857142857142857,
    "2022-11": 0.2857142857142857,
    "2022-12": 0.2857142857142857,
    "2023-01": 0.2653061224489796,
    "2023-02": 0.2653061224489796,
    "2023-03": 0.2653061224489796,
    "2023-04": 0.22448979591836735,
    "2023-05": 0.22448979591836735,
    "2023-06": 0.22448979591836735,
    "2023-07": 0.22448979591836735,
    "2023-08": 0.22448979591836735,
    "2023-09": 0.22448979591836735,
    "2023-10": 0.22448979591836735,
    "2023-11": 0.22448979591836735,
    "2023-12": 0.22448979591836735,
    "2024-01": 0.2708333333333333,
    "2024-02": 0.2708333333333333,
    "2024-03": 0.2708333333333333,
    "2024-04": 0.25,
    "2024-05": 0.25,
    "2024-06": 0.25,
    "2024-07": 0.2708333333333333,
    "2024-08": 0.2708333333333333,
    "2024-09": 0.2708333333333333,
    "2024-10": 0.22916666666666666,
    "2024-11": 0.22916666666666666,
    "2024-12": 0.22916666666666666
  },
  "suppression_share_by_state": {
    "01000": 0.0,
    "02000": 1.0,
    "04000": 0.21875,
    "05000": 0.0,
    "06000": 0.0,
    "08000": 0.90625,
    "09000": 0.6875,
    "10000": 0.85,
    "12000": 0.0,
    "13000": 0.0,
    "15000": 1.0,
    "16000": 0.0,
    "17000": 0.0,
    "18000": 0.0,
    "19000": 0.125,
    "20000": 0.1875,
    "21000": 0.09375,
    "22000": 0.0,
    "23000": 0.0,
    "24000": 0.0,
    "25000": 0.0,
    "26000": 0.0,
    "27000": 0.0,
    "28000": 0.0,
    "29000": 0.0,
    "30000": 0.09375,
    "31000": 0.0,
    "32000": 1.0,
    "33000": 0.71875,
    "34000": 0.84375,
    "35000": 0.71875,
    "36000": 0.0,
    "37000": 0.0,
    "38000": 0.625,
    "39000": 0.0,
    "40000": 0.0,
    "41000": 0.0,
    "42000": 0.0,
    "44000": 0.9375,
    "45000": 0.0,
    "46000": 0.53125,
    "47000": 0.0,
    "48000": 0.0,
    "49000": 0.84375,
    "50000": 1.0,
    "51000": 0.0,
    "53000": 0.0,
    "54000": 0.3125,
    "55000": 0.375,
    "56000": 0.34375
  },
  "suppression_share_overall": 0.26017811704834604
}
```

_Extracts: 1; summary `generated_utc` 2026-09-04T23:13:51+00:00._

### `qcew_routes`

**access**:

```json
{
  "reason": null,
  "route": "slice: https://data.bls.gov/cew/data/api/{year}/{qtr}/industry/{industry}.csv | bulk: https://data.bls.gov/cew/data/files/{year}/csv/{year}_qtrly_by_industry.zip",
  "status": "verified"
}
```

**coverage_span**:

```json
{
  "covered": "2017-2024",
  "published_end": "2026",
  "published_start": "2014",
  "uncovered": "",
  "window_end": "2024-12",
  "window_start": "2017-01"
}
```

**findings**:

```json
{
  "bulk_member_names": {
    "2017": "2017.q1-q4.by_industry/2017.q1-q4 113310 NAICS 113310 Logging.csv"
  },
  "bulk_years_fetched": [
    2017
  ],
  "bulk_years_required": [],
  "column_parity": {
    "bulk_header_disagreement": {},
    "bulk_only": [
      "agglvl_title",
      "area_title",
      "industry_title",
      "lq_qtrly_estabs_count",
      "oty_qtrly_estabs_count_chg",
      "oty_qtrly_estabs_count_pct_chg",
      "own_title",
      "qtrly_estabs_count",
      "size_title"
    ],
    "identical": false,
    "slice_header_disagreement": {},
    "slice_only": [
      "lq_qtrly_estabs",
      "oty_qtrly_estabs_chg",
      "oty_qtrly_estabs_pct_chg",
      "qtrly_estabs"
    ]
  },
  "earliest_year_served": 2014,
  "latest_year_served": 2026,
  "slice_probe": [
    {
      "bytes": 0,
      "content_type": "",
      "http_status": 404,
      "qtr": 1,
      "row_count": 0,
      "year": 2010
    },
    {
      "bytes": 0,
      "content_type": "",
      "http_status": 404,
      "qtr": 2,
      "row_count": 0,
      "year": 2010
    },
    {
      "bytes": 0,
      "content_type": "",
      "http_status": 404,
      "qtr": 3,
      "row_count": 0,
      "year": 2010
    },
    {
      "bytes": 0,
      "content_type": "",
      "http_status": 404,
      "qtr": 4,
      "row_count": 0,
      "year": 2010
    },
    {
      "bytes": 0,
      "content_type": "",
      "http_status": 404,
      "qtr": 1,
      "row_count": 0,
      "year": 2011
    },
    {
      "bytes": 0,
      "content_type": "",
      "http_status": 404,
      "qtr": 2,
      "row_count": 0,
      "year": 2011
    },
    {
      "bytes": 0,
      "content_type": "",
      "http_status": 404,
      "qtr": 3,
      "row_count": 0,
      "year": 2011
    },
    {
      "bytes": 0,
      "content_type": "",
      "http_status": 404,
      "qtr": 4,
      "row_count": 0,
      "year": 2011
    },
    {
      "bytes": 0,
      "content_type": "",
      "http_status": 404,
      "qtr": 1,
      "row_count": 0,
      "year": 2012
    },
    {
      "bytes": 0,
      "content_type": "",
      "http_status": 404,
      "qtr": 2,
      "row_count": 0,
      "year": 2012
    },
    {
      "bytes": 0,
      "content_type": "",
      "http_status": 404,
      "qtr": 3,
      "row_count": 0,
      "year": 2012
    },
    {
      "bytes": 0,
      "content_type": "",
      "http_status": 404,
      "qtr": 4,
      "row_count": 0,
      "year": 2012
    },
    {
      "bytes": 0,
      "content_type": "",
      "http_status": 404,
      "qtr": 1,
      "row_count": 0,
      "year": 2013
    },
    {
      "bytes": 0,
      "content_type": "",
      "http_status": 404,
      "qtr": 2,
      "row_count": 0,
      "year": 2013
    },
    {
      "bytes": 0,
      "content_type": "",
      "http_status": 404,
      "qtr": 3,
      "row_count": 0,
      "year": 2013
    },
    {
      "bytes": 0,
      "content_type": "",
      "http_status": 404,
      "qtr": 4,
      "row_count": 0,
      "year": 2013
    },
    {
      "bytes": 268790,
      "content_type": "text/csv",
      "http_status": 200,
      "qtr": 1,
      "row_count": 1846,
      "year": 2014
    },
    {
      "bytes": 268775,
      "content_type": "text/csv",
      "http_status": 200,
      "qtr": 2,
      "row_count": 1846,
      "year": 2014
    },
    {
      "bytes": 268283,
      "content_type": "text/csv",
      "http_status": 200,
      "qtr": 3,
      "row_count": 1846,
      "year": 2014
    },
    {
      "bytes": 265659,
      "content_type": "text/csv",
      "http_status": 200,
      "qtr": 4,
      "row_count": 1846,
      "year": 2014
    },
    {
      "bytes": 269033,
      "content_type": "text/csv",
      "http_status": 200,
      "qtr": 1,
      "row_count": 1853,
      "year": 2015
    },
    {
      "bytes": 269438,
      "content_type": "text/csv",
      "http_status": 200,
      "qtr": 2,
      "row_count": 1853,
      "year": 2015
    },
    {
      "bytes": 269083,
      "content_type": "text/csv",
      "http_status": 200,
      "qtr": 3,
      "row_count": 1853,
      "year": 2015
    },
    {
      "bytes": 266102,
      "content_type": "text/csv",
      "http_status": 200,
      "qtr": 4,
      "row_count": 1853,
      "year": 2015
    },
    {
      "bytes": 267857,
      "content_type": "text/csv",
      "http_status": 200,
      "qtr": 1,
      "row_count": 1833,
      "year": 2016
    },
    {
      "bytes": 268156,
      "content_type": "text/csv",
      "http_status": 200,
      "qtr": 2,
      "row_count": 1833,
      "year": 2016
    },
    {
      "bytes": 266973,
      "content_type": "text/csv",
      "http_status": 200,
      "qtr": 3,
      "row_count": 1833,
      "year": 2016
    },
    {
      "bytes": 264313,
      "content_type": "text/csv",
      "http_status": 200,
      "qtr": 4,
      "row_count": 1833,
      "year": 2016
    },
    {
      "bytes": 265459,
      "content_type": "text/csv",
      "http_status": 200,
      "qtr": 1,
      "row_count": 1810,
      "year": 2017
    },
    {
      "bytes": 266555,
      "content_type": "text/csv",
      "http_status": 200,
      "qtr": 2,
      "row_count": 1810,
      "year": 2017
    },
    {
      "bytes": 266361,
      "content_type": "text/csv",
      "http_status": 200,
      "qtr": 3,
      "row_count": 1810,
      "year": 2017
    },
    {
      "bytes": 261897,
      "content_type": "text/csv",
      "http_status": 200,
      "qtr": 4,
      "row_count": 1810,
      "year": 2017
    },
    {
      "bytes": 268135,
      "content_type": "text/csv",
      "http_status": 200,
      "qtr": 1,
      "row_count": 1825,
      "year": 2018
    },
    {
      "bytes": 267567,
      "content_type": "text/csv",
      "http_status": 200,
      "qtr": 2,
      "row_count": 1825,
      "year": 2018
    },
    {
      "bytes": 267477,
      "content_type": "text/csv",
      "http_status": 200,
      "qtr": 3,
      "row_count": 1825,
      "year": 2018
    },
    {
      "bytes": 264231,
      "content_type": "text/csv",
      "http_status": 200,
      "qtr": 4,
      "row_count": 1825,
      "year": 2018
    },
    {
      "bytes": 268857,
      "content_type": "text/csv",
      "http_status": 200,
      "qtr": 1,
      "row_count": 1834,
      "year": 2019
    },
    {
      "bytes": 267342,
      "content_type": "text/csv",
      "http_status": 200,
      "qtr": 2,
      "row_count": 1834,
      "year": 2019
    },
    {
      "bytes": 267444,
      "content_type": "text/csv",
      "http_status": 200,
      "qtr": 3,
      "row_count": 1834,
      "year": 2019
    },
    {
      "bytes": 263594,
      "content_type": "text/csv",
      "http_status": 200,
      "qtr": 4,
      "row_count": 1834,
      "year": 2019
    },
    {
      "bytes": 271063,
      "content_type": "text/csv",
      "http_status": 200,
      "qtr": 1,
      "row_count": 1854,
      "year": 2020
    },
    {
      "bytes": 270233,
      "content_type": "text/csv",
      "http_status": 200,
      "qtr": 2,
      "row_count": 1854,
      "year": 2020
    },
    {
      "bytes": 269772,
      "content_type": "text/csv",
      "http_status": 200,
      "qtr": 3,
      "row_count": 1854,
      "year": 2020
    },
    {
      "bytes": 267671,
      "content_type": "text/csv",
      "http_status": 200,
      "qtr": 4,
      "row_count": 1854,
      "year": 2020
    },
    {
      "bytes": 270676,
      "content_type": "text/csv",
      "http_status": 200,
      "qtr": 1,
      "row_count": 1847,
      "year": 2021
    },
    {
      "bytes": 270278,
      "content_type": "text/csv",
      "http_status": 200,
      "qtr": 2,
      "row_count": 1847,
      "year": 2021
    },
    {
      "bytes": 270475,
      "content_type": "text/csv",
      "http_status": 200,
      "qtr": 3,
      "row_count": 1847,
      "year": 2021
    },
    {
      "bytes": 267195,
      "content_type": "text/csv",
      "http_status": 200,
      "qtr": 4,
      "row_count": 1847,
      "year": 2021
    },
    {
      "bytes": 271033,
      "content_type": "text/csv",
      "http_status": 200,
      "qtr": 1,
      "row_count": 1864,
      "year": 2022
    },
    {
      "bytes": 271250,
      "content_type": "text/csv",
      "http_status": 200,
      "qtr": 2,
      "row_count": 1864,
      "year": 2022
    },
    {
      "bytes": 272096,
      "content_type": "text/csv",
      "http_status": 200,
      "qtr": 3,
      "row_count": 1864,
      "year": 2022
    },
    {
      "bytes": 268501,
      "content_type": "text/csv",
      "http_status": 200,
      "qtr": 4,
      "row_count": 1864,
      "year": 2022
    },
    {
      "bytes": 272252,
      "content_type": "text/csv",
      "http_status": 200,
      "qtr": 1,
      "row_count": 1880,
      "year": 2023
    },
    {
      "bytes": 273378,
      "content_type": "text/csv",
      "http_status": 200,
      "qtr": 2,
      "row_count": 1880,
      "year": 2023
    },
    {
      "bytes": 273363,
      "content_type": "text/csv",
      "http_status": 200,
      "qtr": 3,
      "row_count": 1880,
      "year": 2023
    },
    {
      "bytes": 268877,
      "content_type": "text/csv",
      "http_status": 200,
      "qtr": 4,
      "row_count": 1880,
      "year": 2023
    },
    {
      "bytes": 267123,
      "content_type": "text/csv",
      "http_status": 200,
      "qtr": 1,
      "row_count": 1864,
      "year": 2024
    },
    {
      "bytes": 267205,
      "content_type": "text/csv",
      "http_status": 200,
      "qtr": 2,
      "row_count": 1864,
      "year": 2024
    },
    {
      "bytes": 266977,
      "content_type": "text/csv",
      "http_status": 200,
      "qtr": 3,
      "row_count": 1864,
      "year": 2024
    },
    {
      "bytes": 263278,
      "content_type": "text/csv",
      "http_status": 200,
      "qtr": 4,
      "row_count": 1864,
      "year": 2024
    },
    {
      "bytes": 258475,
      "content_type": "text/csv",
      "http_status": 200,
      "qtr": 1,
      "row_count": 1838,
      "year": 2025
    },
    {
      "bytes": 258070,
      "content_type": "text/csv",
      "http_status": 200,
      "qtr": 2,
      "row_count": 1838,
      "year": 2025
    },
    {
      "bytes": 257253,
      "content_type": "text/csv",
      "http_status": 200,
      "qtr": 3,
      "row_count": 1838,
      "year": 2025
    },
    {
      "bytes": 256042,
      "content_type": "text/csv",
      "http_status": 200,
      "qtr": 4,
      "row_count": 1838,
      "year": 2025
    },
    {
      "bytes": 217501,
      "content_type": "text/csv",
      "http_status": 200,
      "qtr": 1,
      "row_count": 1536,
      "year": 2026
    },
    {
      "bytes": 0,
      "content_type": "",
      "http_status": 404,
      "qtr": 2,
      "row_count": 0,
      "year": 2026
    },
    {
      "bytes": 0,
      "content_type": "",
      "http_status": 404,
      "qtr": 3,
      "row_count": 0,
      "year": 2026
    },
    {
      "bytes": 0,
      "content_type": "",
      "http_status": 404,
      "qtr": 4,
      "row_count": 0,
      "year": 2026
    }
  ]
}
```

_Extracts: 33; summary `generated_utc` 2026-09-03T20:17:52+00:00._

### `qcew_size`

**access**:

```json
{
  "reason": null,
  "route": "https://data.bls.gov/cew/data/files/{year}/csv/{year}_q1_by_size.zip",
  "status": "verified"
}
```

**coverage_span**:

```json
{
  "covered": "first quarter of each window year only",
  "published_end": "2024-Q1",
  "published_start": "2017-Q1",
  "uncovered": "Q2-Q4 of every window year: probed (24 requests) and none returned a by-size file, so the product is Q1-only for every year checked",
  "window_end": "2024-12",
  "window_start": "2017-01"
}
```

**findings**:

```json
{
  "agglvl_inventory": [
    {
      "agglvl_code": "21",
      "area_pattern": "national",
      "has_113310": false,
      "row_count": 72,
      "size_codes": [
        "1",
        "2",
        "3",
        "4",
        "5",
        "6",
        "7",
        "8",
        "9"
      ]
    },
    {
      "agglvl_code": "22",
      "area_pattern": "national",
      "has_113310": false,
      "row_count": 144,
      "size_codes": [
        "1",
        "2",
        "3",
        "4",
        "5",
        "6",
        "7",
        "8",
        "9"
      ]
    },
    {
      "agglvl_code": "23",
      "area_pattern": "national",
      "has_113310": false,
      "row_count": 773,
      "size_codes": [
        "1",
        "2",
        "3",
        "4",
        "5",
        "6",
        "7",
        "8",
        "9"
      ]
    },
    {
      "agglvl_code": "24",
      "area_pattern": "national",
      "has_113310": false,
      "row_count": 1421,
      "size_codes": [
        "1",
        "2",
        "3",
        "4",
        "5",
        "6",
        "7",
        "8",
        "9"
      ]
    },
    {
      "agglvl_code": "25",
      "area_pattern": "national",
      "has_113310": false,
      "row_count": 6363,
      "size_codes": [
        "1",
        "2",
        "3",
        "4",
        "5",
        "6",
        "7",
        "8",
        "9"
      ]
    },
    {
      "agglvl_code": "26",
      "area_pattern": "national",
      "has_113310": false,
      "row_count": 20828,
      "size_codes": [
        "1",
        "2",
        "3",
        "4",
        "5",
        "6",
        "7",
        "8",
        "9"
      ]
    },
    {
      "agglvl_code": "27",
      "area_pattern": "national",
      "has_113310": false,
      "row_count": 44213,
      "size_codes": [
        "1",
        "2",
        "3",
        "4",
        "5",
        "6",
        "7",
        "8",
        "9"
      ]
    },
    {
      "agglvl_code": "28",
      "area_pattern": "national",
      "has_113310": true,
      "row_count": 66529,
      "size_codes": [
        "1",
        "2",
        "3",
        "4",
        "5",
        "6",
        "7",
        "8",
        "9"
      ]
    },
    {
      "agglvl_code": "61",
      "area_pattern": "mixed",
      "has_113310": false,
      "row_count": 3802,
      "size_codes": [
        "1",
        "2",
        "3",
        "4",
        "5",
        "6",
        "7",
        "8",
        "9"
      ]
    },
    {
      "agglvl_code": "62",
      "area_pattern": "mixed",
      "has_113310": false,
      "row_count": 7575,
      "size_codes": [
        "1",
        "2",
        "3",
        "4",
        "5",
        "6",
        "7",
        "8",
        "9"
      ]
    },
    {
      "agglvl_code": "63",
      "area_pattern": "mixed",
      "has_113310": false,
      "row_count": 36493,
      "size_codes": [
        "1",
        "2",
        "3",
        "4",
        "5",
        "6",
        "7",
        "8",
        "9"
      ]
    },
    {
      "agglvl_code": "64",
      "area_pattern": "mixed",
      "has_113310": false,
      "row_count": 66240,
      "size_codes": [
        "1",
        "2",
        "3",
        "4",
        "5",
        "6",
        "7",
        "8",
        "9"
      ]
    }
  ],
  "all_sizes_code": {
    "code": "0",
    "title": "All establishment sizes"
  },
  "quarter_probe": [
    {
      "bytes": 190,
      "http_status": 404,
      "qtr": 2,
      "year": 2017
    },
    {
      "bytes": 190,
      "http_status": 404,
      "qtr": 3,
      "year": 2017
    },
    {
      "bytes": 190,
      "http_status": 404,
      "qtr": 4,
      "year": 2017
    },
    {
      "bytes": 190,
      "http_status": 404,
      "qtr": 2,
      "year": 2018
    },
    {
      "bytes": 190,
      "http_status": 404,
      "qtr": 3,
      "year": 2018
    },
    {
      "bytes": 190,
      "http_status": 404,
      "qtr": 4,
      "year": 2018
    },
    {
      "bytes": 190,
      "http_status": 404,
      "qtr": 2,
      "year": 2019
    },
    {
      "bytes": 190,
      "http_status": 404,
      "qtr": 3,
      "year": 2019
    },
    {
      "bytes": 190,
      "http_status": 404,
      "qtr": 4,
      "year": 2019
    },
    {
      "bytes": 190,
      "http_status": 404,
      "qtr": 2,
      "year": 2020
    },
    {
      "bytes": 190,
      "http_status": 404,
      "qtr": 3,
      "year": 2020
    },
    {
      "bytes": 190,
      "http_status": 404,
      "qtr": 4,
      "year": 2020
    },
    {
      "bytes": 190,
      "http_status": 404,
      "qtr": 2,
      "year": 2021
    },
    {
      "bytes": 190,
      "http_status": 404,
      "qtr": 3,
      "year": 2021
    },
    {
      "bytes": 190,
      "http_status": 404,
      "qtr": 4,
      "year": 2021
    },
    {
      "bytes": 190,
      "http_status": 404,
      "qtr": 2,
      "year": 2022
    },
    {
      "bytes": 190,
      "http_status": 404,
      "qtr": 3,
      "year": 2022
    },
    {
      "bytes": 190,
      "http_status": 404,
      "qtr": 4,
      "year": 2022
    },
    {
      "bytes": 190,
      "http_status": 404,
      "qtr": 2,
      "year": 2023
    },
    {
      "bytes": 190,
      "http_status": 404,
      "qtr": 3,
      "year": 2023
    },
    {
      "bytes": 190,
      "http_status": 404,
      "qtr": 4,
      "year": 2023
    },
    {
      "bytes": 190,
      "http_status": 404,
      "qtr": 2,
      "year": 2024
    },
    {
      "bytes": 190,
      "http_status": 404,
      "qtr": 3,
      "year": 2024
    },
    {
      "bytes": 190,
      "http_status": 404,
      "qtr": 4,
      "year": 2024
    }
  ],
  "simultaneous_state_industry_size": false,
  "size_codes_with_titles": [
    {
      "code": "1",
      "title": "Fewer than 5 employees per establishment"
    },
    {
      "code": "2",
      "title": "5 to 9 employees per establishment"
    },
    {
      "code": "3",
      "title": "10 to 19 employees per establishment"
    },
    {
      "code": "4",
      "title": "20 to 49 employees per establishment"
    },
    {
      "code": "5",
      "title": "50 to 99 employees per establishment"
    },
    {
      "code": "6",
      "title": "100 to 249 employees per establishment"
    },
    {
      "code": "7",
      "title": "250 to 499 employees per establishment"
    }
  ],
  "stage6_reroute_required": false,
  "what_the_file_does_carry": "the finest simultaneous combination observed for 113310 is national geography x 113310 x size codes ['1', '2', '3', '4', '5', '6', '7']",
  "years_checked": [
    2017,
    2018,
    2019,
    2020,
    2021,
    2022,
    2023,
    2024
  ]
}
```

_Extracts: 8; summary `generated_utc` 2026-09-04T01:05:00+00:00._

### `susb`

**access**:

```json
{
  "reason": null,
  "route": "https://www2.census.gov/programs-surveys/susb/tables/{year}/",
  "status": "verified"
}
```

**coverage_span**:

```json
{
  "covered": "2017-2022",
  "published_end": "2022",
  "published_start": "1992",
  "uncovered": "2023,2024",
  "window_end": "2024-12",
  "window_start": "2017-01"
}
```

**findings**:

```json
{
  "detailed_sizes_layout": {
    "columns": [
      "STATE",
      "NAICS",
      "ENTRSIZE",
      "FIRM",
      "ESTB",
      "EMPL",
      "EMPLFL_N",
      "PAYR",
      "PAYRFL_N",
      "RCPT",
      "RCPTFL_N",
      "STATEDSCR",
      "NAICSDSCR",
      "ENTRSIZEDSCR"
    ],
    "filename": "us_state_naics_detailedsizes_2022.txt",
    "geography_levels": [
      "00",
      "01",
      "02",
      "04",
      "05",
      "06",
      "08",
      "09",
      "10",
      "11",
      "12",
      "13",
      "15",
      "16",
      "17",
      "18",
      "19",
      "20",
      "21",
      "22",
      "23",
      "24",
      "25",
      "26",
      "27",
      "28",
      "29",
      "30",
      "31",
      "32",
      "33",
      "34",
      "35",
      "36",
      "37",
      "38",
      "39",
      "40",
      "41",
      "42",
      "44",
      "45",
      "46",
      "47",
      "48",
      "49",
      "50",
      "51",
      "53",
      "54",
      "55",
      "56"
    ],
    "has_113310_at_state": false,
    "industry_code_lengths": [
      2,
      3,
      4,
      5,
      6
    ],
    "industry_code_lengths_at_state": [
      2,
      4
    ],
    "row_count": 67867,
    "size_column": "ENTRSIZE",
    "size_values": [
      "01",
      "02",
      "03",
      "04",
      "05",
      "06",
      "07",
      "08",
      "09",
      "10",
      "11",
      "12",
      "13",
      "14",
      "15",
      "16",
      "17",
      "18",
      "19",
      "22",
      "23",
      "24",
      "25",
      "31",
      "33",
      "37"
    ]
  },
  "detailed_sizes_reaches_six_digit_at_state": false,
  "files_found": [
    "OLD-msa_3digitnaics_2022.xlsx",
    "cd_naicssector_2022.xlsx",
    "county_3digitnaics_2022.xlsx",
    "msa_3digitnaics_2022.xlsx",
    "territory_naics_2022.xlsx",
    "us_6digitnaics_rcptsize_2022.xlsx",
    "us_naicssector_large_emplsize_2022.xlsx",
    "us_naicssector_large_rcptsize_2022.xlsx",
    "us_state_6digitnaics_2022.txt",
    "us_state_6digitnaics_2022.xlsx",
    "us_state_naics_detailedsizes_2022.txt",
    "us_state_naics_detailedsizes_2022.xlsx",
    "us_state_naicssector_lfo_2022.xlsx"
  ],
  "has_113310_at_state": {
    "detailed_sizes": false,
    "six_digit": true
  },
  "latest_year": 2022,
  "raw_retention_rule": {
    "extracts_recorded": 5,
    "extracts_with_non_200_status": 0,
    "non_200_statuses_recorded": [],
    "rule": "This script makes no repeated multi-candidate access-verdict probe (contrast bds_detail.py's five-candidate NAICS probe or qcew_routes.py's year x quarter boundary walk); every fetch here -- the tables root, the year directory, the record-layout document, and each chosen data file -- is a single GET for a resource whose presence a preceding fetch already established. _common.request and _common.download_extract raise rather than return on a non-retryable 4xx or an exhausted 5xx/429 retry budget, so a failure on any of those fetches aborts this run before write_summary is reached and registers no extract for the failed resource -- there is no partial summary and no non-200 body left to retain, matching bds_detail.py's own precedent for its single non-probed variables.json fetch. Every extract this script does register therefore carries http_status 200; the counters below describe only a completed, successful run, and their being zero is not evidence that a non-200 response is impossible here, only that this run's every fetch that reached write_summary answered 200."
  },
  "six_digit_state_layout": {
    "columns": [
      "STATE",
      "NAICS",
      "ENTRSIZE",
      "FIRM",
      "ESTB",
      "EMPL",
      "EMPLFL_N",
      "PAYR",
      "PAYRFL_N",
      "RCPT",
      "RCPTFL_N",
      "STATEDSCR",
      "NAICSDSCR",
      "ENTRSIZEDSCR"
    ],
    "filename": "us_state_6digitnaics_2022.txt",
    "geography_levels": [
      "00",
      "01",
      "02",
      "04",
      "05",
      "06",
      "08",
      "09",
      "10",
      "11",
      "12",
      "13",
      "15",
      "16",
      "17",
      "18",
      "19",
      "20",
      "21",
      "22",
      "23",
      "24",
      "25",
      "26",
      "27",
      "28",
      "29",
      "30",
      "31",
      "32",
      "33",
      "34",
      "35",
      "36",
      "37",
      "38",
      "39",
      "40",
      "41",
      "42",
      "44",
      "45",
      "46",
      "47",
      "48",
      "49",
      "50",
      "51",
      "53",
      "54",
      "55",
      "56"
    ],
    "has_113310_at_state": true,
    "industry_code_lengths": [
      2,
      3,
      4,
      5,
      6
    ],
    "industry_code_lengths_at_state": [
      2,
      3,
      4,
      5,
      6
    ],
    "row_count": 570105,
    "size_column": "ENTRSIZE",
    "size_values": [
      "01",
      "02",
      "03",
      "26",
      "33",
      "34",
      "35",
      "36",
      "37"
    ]
  },
  "size_concept": {
    "column": "ENTRSIZE",
    "note": "ENTRSIZE\tC\tEnterprise Employment Size Code\n\t\t\tEnterprise Receipt Size Code * years ending in 2 and 7 only",
    "value": "enterprise"
  }
}
```

_Extracts: 5; summary `generated_utc` 2026-09-04T19:58:36+00:00._

### `tpo`

**access**:

```json
{
  "reason": "Reachable and machine-readable, but only via an undocumented Box legacy-download redirect rather than the modern share URL; per-state coverage per year is not exhaustively verified (see coverage_span). Measured in the one workbook fetched this run (Alabama_2024.xlsx, from the 2024 subfolder): its 8 sheet names are ['County Production', 'State Production', 'Receipts', 'Wood Movement-IMPORTS', 'Wood Movement-EXPORTS', 'Mill Locations', 'Residue Use State', 'Regional Production'], of which ['County Production', 'State Production', 'Regional Production'] match this script's harvest-origin sheet-name pattern and ['Receipts', 'Mill Locations'] match its mill-receipt pattern. Its first sheet (County Production) carries a 22-column header row, ['REGION', 'STATECD', 'STATE_NAME', 'COUNTYCD', 'COUNTY_NAME', 'YEAR', 'OWNCD', 'OWNER_MEANING', 'SPGRPCD', 'SPGRP_NAME', 'REMCLASSCD', 'REMCLASSCD_MEANING', 'SOURCECD', 'SOURCECD_MEANING', 'PRODCD', 'PRODCD_MEANING', 'MCFVOL', 'RPA_STD_AMOUNT', 'RPA_STD_AMOUNT_UOM_CODE', 'RPA_STD_AMOUNT_UOM_MEANING', 'SAWREMVOL', 'GREEN_TONS'], of which ['COUNTYCD', 'COUNTY_NAME'] match this script's county-identifier pattern and ['MCFVOL', 'SAWREMVOL', 'GREEN_TONS'] match its volume/weight-measure pattern. A county identifier and volume measures therefore share that header row: the workbook carries county-resolved volume columns, read from the header row's own column names rather than off a sheet name. Which county those identifiers name -- the county a harvest came from, or the county a mill sits in -- is not settled by a column name. INFERENCE MARKER, OPENING: what follows to the closing marker is a reading of those sheet names, not a further measurement; it is supplied by hand, carries no extract hash and is re-checked by no later run. Sheets named that way are read here as meaning the workbook holds harvest volumes attributed to the county of harvest in fields distinct from its mill-receipt fields, which is what SRC-FOR-001 requires. No data-row cells were read or compared across sheets, so the origin/receipt split rests on the sheet names alone; and only this one state-year workbook was inspected, so whether every state-year workbook in the share shares this sheet structure was not checked either. INFERENCE MARKER, CLOSING. INFERENCE MARKER, OPENING: how this route was found comes from the investigation that shaped this script rather than from this run -- the legacy-download redirect was found by reading the share page's own JS bundle, and the share page's embedded authenticated_download_url was observed there to answer 401 without a browser session. No probe in this run requested that URL, so both statements carry no extract hash and are re-checked by no later run. INFERENCE MARKER, CLOSING.",
  "route": "https://research.fs.usda.gov/products/dataandtools/national-resource-use-monitoring-data-downloads -> https://usfs-public.app.box.com/s/y4ziirdb9v7zardus0cuajh7ziy9b2id -> https://usfs-public.app.box.com/s/y4ziirdb9v7zardus0cuajh7ziy9b2id/folder/<year-subfolder-id> -> https://usfs-public.app.box.com/index.php?rm=box_download_shared_file&...&file_id=f_<id>",
  "status": "verified"
}
```

> **Recorded access reason:** Reachable and machine-readable, but only via an undocumented Box legacy-download redirect rather than the modern share URL; per-state coverage per year is not exhaustively verified (see coverage_span). Measured in the one workbook fetched this run (Alabama_2024.xlsx, from the 2024 subfolder): its 8 sheet names are ['County Production', 'State Production', 'Receipts', 'Wood Movement-IMPORTS', 'Wood Movement-EXPORTS', 'Mill Locations', 'Residue Use State', 'Regional Production'], of which ['County Production', 'State Production', 'Regional Production'] match this script's harvest-origin sheet-name pattern and ['Receipts', 'Mill Locations'] match its mill-receipt pattern. Its first sheet (County Production) carries a 22-column header row, ['REGION', 'STATECD', 'STATE_NAME', 'COUNTYCD', 'COUNTY_NAME', 'YEAR', 'OWNCD', 'OWNER_MEANING', 'SPGRPCD', 'SPGRP_NAME', 'REMCLASSCD', 'REMCLASSCD_MEANING', 'SOURCECD', 'SOURCECD_MEANING', 'PRODCD', 'PRODCD_MEANING', 'MCFVOL', 'RPA_STD_AMOUNT', 'RPA_STD_AMOUNT_UOM_CODE', 'RPA_STD_AMOUNT_UOM_MEANING', 'SAWREMVOL', 'GREEN_TONS'], of which ['COUNTYCD', 'COUNTY_NAME'] match this script's county-identifier pattern and ['MCFVOL', 'SAWREMVOL', 'GREEN_TONS'] match its volume/weight-measure pattern. A county identifier and volume measures therefore share that header row: the workbook carries county-resolved volume columns, read from the header row's own column names rather than off a sheet name. Which county those identifiers name -- the county a harvest came from, or the county a mill sits in -- is not settled by a column name. INFERENCE MARKER, OPENING: what follows to the closing marker is a reading of those sheet names, not a further measurement; it is supplied by hand, carries no extract hash and is re-checked by no later run. Sheets named that way are read here as meaning the workbook holds harvest volumes attributed to the county of harvest in fields distinct from its mill-receipt fields, which is what SRC-FOR-001 requires. No data-row cells were read or compared across sheets, so the origin/receipt split rests on the sheet names alone; and only this one state-year workbook was inspected, so whether every state-year workbook in the share shares this sheet structure was not checked either. INFERENCE MARKER, CLOSING. INFERENCE MARKER, OPENING: how this route was found comes from the investigation that shaped this script rather than from this run -- the legacy-download redirect was found by reading the share page's own JS bundle, and the share page's embedded authenticated_download_url was observed there to answer 401 without a browser session. No probe in this run requested that URL, so both statements carry no extract hash and are re-checked by no later run. INFERENCE MARKER, CLOSING.

**coverage_span**:

```json
{
  "covered": "a per-state-year subfolder exists in the NRUM Data Box share for every D1 window year (verified this run: ['2017', '2018', '2019', '2020', '2021', '2022', '2023', '2024']); this directly contradicts a blanket 'TPO is biennial, not annual' claim for the D1 window specifically, though whether every individual state resurveys annually (as opposed to the release/folder cadence being annual) was not checked; pre-2017 subfolders found only for odd years back to 1997 (biennial cadence, verified this run)",
  "published_end": "2024",
  "published_start": "1997",
  "uncovered": "no monthly resolution: SRC-FOR-004 forbids interpolating to months; per-state completeness within a year (which of the 51 states_dc have a file) was not exhaustively enumerated this run -- for the probed year (2024), Box's rendered item list returned 13 files, matching that folder's filesCount metadata (13) exactly -- no truncation observed for this specific year, though only the one year named here was checked and a different year could still be page-capped -- so a full state-by-state count would need paginating Box's listing API for every window year, out of scope for an access verdict",
  "window_end": "2024-12",
  "window_start": "2017-01"
}
```

**findings**:

```json
{
  "box_navigation": {
    "files_listed_this_page": 13,
    "filescount_per_box_metadata": 13,
    "nrum_data_folder_id": 121486946349,
    "probed_year": "2024",
    "sample_file": "Alabama_2024.xlsx",
    "sample_file_first_sheet_headers": [
      "REGION",
      "STATECD",
      "STATE_NAME",
      "COUNTYCD",
      "COUNTY_NAME",
      "YEAR",
      "OWNCD",
      "OWNER_MEANING",
      "SPGRPCD",
      "SPGRP_NAME",
      "REMCLASSCD",
      "REMCLASSCD_MEANING",
      "SOURCECD",
      "SOURCECD_MEANING",
      "PRODCD",
      "PRODCD_MEANING",
      "MCFVOL",
      "RPA_STD_AMOUNT",
      "RPA_STD_AMOUNT_UOM_CODE",
      "RPA_STD_AMOUNT_UOM_MEANING",
      "SAWREMVOL",
      "GREEN_TONS"
    ],
    "sample_file_first_sheet_name": "County Production",
    "sample_file_first_sheet_unresolved": "",
    "sample_file_sheet_names": [
      "County Production",
      "State Production",
      "Receipts",
      "Wood Movement-IMPORTS",
      "Wood Movement-EXPORTS",
      "Mill Locations",
      "Residue Use State",
      "Regional Production"
    ],
    "share_url_discovered": "https://usfs-public.app.box.com/s/y4ziirdb9v7zardus0cuajh7ziy9b2id",
    "window_year_subfolders_found": [
      "2017",
      "2018",
      "2019",
      "2020",
      "2021",
      "2022",
      "2023",
      "2024"
    ],
    "year_subfolders_found": [
      "1997",
      "1999",
      "2001",
      "2003",
      "2005",
      "2007",
      "2009",
      "2011",
      "2013",
      "2015",
      "2017",
      "2018",
      "2019",
      "2020",
      "2021",
      "2022",
      "2023",
      "2024"
    ]
  },
  "chosen_route": "https://usfs-public.app.box.com/index.php?rm=box_download_shared_file&shared_name=y4ziirdb9v7zardus0cuajh7ziy9b2id&file_id=f_2095812033097",
  "harvest_origin_available": true,
  "raw_retention_rule": {
    "extracts_recorded": 8,
    "extracts_with_non_200_status": 1,
    "non_200_statuses_recorded": [
      404
    ],
    "rule": "This script writes and registers a fetched body whenever a route it probes for bytes answered with a non-empty body, whatever the HTTP status, and each extract's own http_status records which status it carried. On an access-verdict probe the non-200 body IS the evidence: a 404 page and a 403 page are different verdicts and only the retained bytes tell them apart. Two cases register no extract, and they are not the same case. A transport failure produced no response at all, so there is no body to keep; its evidence is the probe record's outcome field instead. A response whose body is empty -- including an empty 200 -- has nothing to keep either, so it registers no extract as well, and what records it is its probe entry's status and its bytes count of zero, not retained bytes. Scope: this rule is about the routes probed for bytes. Where this script probes a route status-only, through a helper that discards the body by construction, that route registers no extract whatever it answers; which routes, if any, a run probed that way is recorded in this source's own probe findings, as entries carrying each attempt's status and byte count and no body. The counters below therefore say which statuses were retained and nothing more: a retained status 200 means the endpoint answered, not that the body is usable data -- an application error page can arrive with status 200, and which retained bodies are usable is recorded per probe in findings, never inferable from an extract's http_status. Reader's caution: this rule is this script's, and the absence of a non-200 extract under another source in this audit is not evidence that no non-200 response occurred there."
  },
  "route_probes": [
    {
      "bytes": 106526,
      "content_type": "text/html; charset=utf-8",
      "http_status": 200,
      "machine_readable": false,
      "origin": "brief",
      "outcome": "reachable",
      "url": "https://research.fs.usda.gov/programs/nrum"
    },
    {
      "bytes": 81316,
      "content_type": "text/html; charset=utf-8",
      "http_status": 200,
      "machine_readable": false,
      "origin": "brief",
      "outcome": "reachable",
      "url": "https://research.fs.usda.gov/products/dataandtools/timber-products-output-tpo-interactive-reporting-tool"
    },
    {
      "bytes": 4208,
      "content_type": "text/html; charset=utf-8",
      "http_status": 404,
      "machine_readable": false,
      "origin": "brief",
      "outcome": "not_found",
      "url": "https://apps.fs.usda.gov/fiadb-api/tpo"
    },
    {
      "bytes": 6569,
      "content_type": "text/html;charset=utf-8",
      "http_status": 200,
      "machine_readable": false,
      "origin": "discovered (linked from a brief candidate page)",
      "outcome": "reachable",
      "url": "https://public.tableau.com/views/TPOREPORTINGTOOL/MakeSelection?%3AshowVizHome=no"
    },
    {
      "bytes": 67963,
      "content_type": "text/html; charset=utf-8",
      "http_status": 200,
      "machine_readable": false,
      "origin": "discovered (linked from a brief candidate page)",
      "outcome": "reachable",
      "url": "https://research.fs.usda.gov/products/dataandtools/national-resource-use-monitoring-data-downloads"
    },
    {
      "bytes": 59364,
      "content_type": "text/html; charset=utf-8",
      "http_status": 200,
      "machine_readable": false,
      "origin": "discovered (linked from the NRUM data-downloads page)",
      "outcome": "reachable",
      "url": "https://usfs-public.app.box.com/s/y4ziirdb9v7zardus0cuajh7ziy9b2id"
    },
    {
      "bytes": 51648,
      "content_type": "text/html; charset=utf-8",
      "http_status": 200,
      "machine_readable": false,
      "origin": "discovered (Box subfolder for 2024)",
      "outcome": "reachable",
      "url": "https://usfs-public.app.box.com/s/y4ziirdb9v7zardus0cuajh7ziy9b2id/folder/359625501534"
    },
    {
      "bytes": 3947983,
      "content_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      "http_status": 200,
      "machine_readable": true,
      "origin": "discovered (Box legacy download of Alabama_2024.xlsx)",
      "outcome": "reachable",
      "url": "https://usfs-public.app.box.com/index.php?rm=box_download_shared_file&shared_name=y4ziirdb9v7zardus0cuajh7ziy9b2id&file_id=f_2095812033097"
    }
  ]
}
```

_Extracts: 8; summary `generated_utc` 2026-09-04T23:27:14+00:00._

