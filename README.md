# impute-suppressed-stats

Monthly state Logging (NAICS 113310) employment by establishment
size class, with deterministic bounds on the suppressed cells.

## Usage

### Deterministic identification (Stage 2)

    logging-estimates build-constraints --config config.yaml
    logging-estimates solve-bounds --config config.yaml

`build-constraints` writes `data/constraints/` and a run directory under `runs/`;
`solve-bounds` writes `deterministic_bounds.parquet`, `component_rank.parquet` and
`disclosure_flags.parquet` beside it. Both are idempotent: the run id is derived from the
resolved configuration and the harmonized inputs, so re-running lands on the same directory.

On the pilot window the engine bounds 14 suppressed national size classes to intervals 130–894
employees wide, and reports every one of the 1,227 suppressed state-month cells as `unbounded`.
`SRC-QCEW-006` came back `decline`, so no national employment margin exists to constrain a state
cell. A disclosed private `113` parent publishes an upper bound on 756 of those 1,227 cells
(measured 2026-09-11, `specs/findings/qcew-parent-margins.md`) that is not yet a constraint row;
`specs/stage5-parent-margin.md` owns wiring it in.
Stages 3–5 are what narrow the rest.
