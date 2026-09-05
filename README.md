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
That is not a gap in the engine: `SRC-QCEW-006` came back `decline`, so no national employment
margin exists to constrain a state cell, and nonnegativity is the only public fact that touches
one. Stages 3–5 are what narrow them.
