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
  rows carrying disclosure code `N` still publish `qtrly_estabs > 0`. The *employment* identity
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
| Optional state sources (disabled by default) | Keep disabled. | This audit probed no state portal, so it gathered no evidence either way; Appendix A's `enabled: false` stands unchallenged rather than confirmed. |

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
  (`qcew_panel.estabs_survive_suppression_share = 1.0`). That is why the establishment identity
  is testable while the employment one is not, and it is the strongest structural constraint
  this audit found.
- **CES counts have two denominators, and they differ.** `ces.publication_level_by_state` maps
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
