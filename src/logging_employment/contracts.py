"""Polars schemas for every table this stage persists, and their fingerprints.

Field order follows the spec's own listing in §7.1-§7.5 and §8.6. Order is load-bearing: the
schema fingerprint is computed over the ordered pairs, so a reordering is a schema change and is
meant to be detected as one.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

import polars as pl

from .errors import ConceptViolationError, SchemaMismatchError

# `observation_status` is named in §7.3, §7.4, §7.7 and §15.2 and enumerated in none of them, so
# these four values are this package's decision rather than the spec's text. `absent` is the one
# that is easy to miss and impossible to fold in: Stage 0 measured that DC (11000) publishes no
# private 113310 row in any of the window's 96 months, which is not a suppressed cell and not a
# zero. Collapsing it into either would state something about DC that no source published.
OBSERVATION_STATUSES: tuple[str, ...] = ("observed", "suppressed", "true_zero", "absent")

# INV-009: the real-world suppression type is unknown unless a public source identifies one, and
# QCEW identifies none. The two labelled values exist for Stage 4's synthetic masks and must never
# be written onto a real row.
SUPPRESSION_TYPES: tuple[str, ...] = ("unknown", "primary_like", "complementary_like")

SOURCE_REGISTRY_SCHEMA: dict[str, pl.DataType] = {
    "source_id": pl.String,
    "agency": pl.String,
    "dataset": pl.String,
    "landing_url": pl.String,
    "endpoint_pattern": pl.String,
    "access_status": pl.String,
    "frequency": pl.String,
    "reference_period": pl.String,
    "geography": pl.String,
    "industry_detail": pl.String,
    "ownership": pl.String,
    "statistical_unit": pl.String,
    "employment_concept": pl.String,
    "size_dimension": pl.String,
    "disclosure_regime": pl.String,
    "revision_policy": pl.String,
    "model_role": pl.String,
    "limitations": pl.String,
}

SOURCE_SNAPSHOT_SCHEMA: dict[str, pl.DataType] = {
    "snapshot_id": pl.String,
    "source_id": pl.String,
    "request_url_or_file": pl.String,
    "request_parameters_json": pl.String,
    "retrieved_at_utc": pl.String,
    "source_publication_date": pl.String,
    "reference_start": pl.String,
    "reference_end": pl.String,
    "release_status": pl.String,
    "naics_vintage": pl.String,
    "schema_fingerprint": pl.String,
    "content_sha256": pl.String,
    "byte_count": pl.Int64,
    "http_status": pl.Int64,
    "parser_version": pl.String,
    "raw_path": pl.String,
}

QCEW_MONTHLY_SCHEMA: dict[str, pl.DataType] = {
    "snapshot_id": pl.String,
    "release_vintage": pl.String,
    "release_status": pl.String,
    "reference_quarter": pl.String,
    "reference_month": pl.String,
    "area_fips": pl.String,
    "area_type": pl.String,
    "state_fips": pl.String,
    "industry_code": pl.String,
    "naics_vintage": pl.String,
    "ownership_code": pl.String,
    "aggregation_level": pl.String,
    "size_code": pl.String,
    "qtrly_establishments": pl.Int64,
    "employment_raw": pl.String,
    "employment_value": pl.Int64,
    "wages_raw": pl.String,
    "wages_value": pl.Int64,
    "disclosure_code": pl.String,
    "observation_status": pl.String,
    "is_published_numeric_zero": pl.Boolean,
    "is_true_zero": pl.Boolean,
    "source_row_hash": pl.String,
    # This package's addition, not a field §7.3 names: INV-009 requires the real-world suppression
    # type to be recorded as `unknown`, and a default that exists only in Stage 4 could not be
    # distinguished from a value Stage 4 chose.
    "suppression_type": pl.String,
}

QCEW_NATIONAL_SIZE_SCHEMA: dict[str, pl.DataType] = {
    "snapshot_id": pl.String,
    "reference_year": pl.Int64,
    "reference_quarter": pl.String,
    "reference_month": pl.String,
    "industry_code": pl.String,
    "naics_vintage": pl.String,
    "size_class": pl.String,
    "size_lower": pl.Int64,
    "size_upper": pl.Int64,
    "establishments": pl.Int64,
    "employment": pl.Int64,
    "disclosure_code": pl.String,
    "observation_status": pl.String,
}

CBP_STATE_SIZE_SCHEMA: dict[str, pl.DataType] = {
    "snapshot_id": pl.String,
    "reference_year": pl.Int64,
    "state_fips": pl.String,
    "industry_code": pl.String,
    "naics_vintage": pl.String,
    "legal_form_code": pl.String,
    "size_code": pl.String,
    "size_label": pl.String,
    "size_lower": pl.Int64,
    "size_upper": pl.Int64,
    "establishments": pl.Int64,
    "employment": pl.Int64,
    "employment_flag": pl.String,
    "employment_noise_range": pl.String,
    "disclosure_status": pl.String,
    "disclosure_regime": pl.String,
    "reference_period": pl.String,
}

BRIDGE_SCHEMA: dict[str, pl.DataType] = {
    "bridge_id": pl.String,
    "source_concept": pl.String,
    "target_concept": pl.String,
    "valid_start": pl.String,
    "valid_end": pl.String,
    "method": pl.String,
    "uncertainty_treatment": pl.String,
    "verification_status": pl.String,
}


def schema_fingerprint(schema: dict[str, pl.DataType]) -> str:
    """A sha256 over the schema's ordered (name, dtype) pairs."""
    payload = json.dumps([[name, str(dtype)] for name, dtype in schema.items()])
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def validate_frame(frame: pl.DataFrame, schema: dict[str, pl.DataType], name: str) -> None:
    """Raise SchemaMismatchError unless the frame's columns and dtypes match the schema exactly."""
    missing = [c for c in schema if c not in frame.columns]
    extra = [c for c in frame.columns if c not in schema]
    if missing or extra:
        raise SchemaMismatchError(f"{name}: missing={missing} extra={extra}")
    wrong = [
        (c, str(schema[c]), str(frame.schema[c])) for c in schema if frame.schema[c] != schema[c]
    ]
    if wrong:
        raise SchemaMismatchError(f"{name}: dtype mismatches {wrong}")


# §7.8's five constraint classes, in the spec's own order. The order is load-bearing: §7.8 says
# "Only the first two may have is_hard=true", so `HARD_ELIGIBLE_CLASSES` is a slice of this tuple
# rather than a second literal that could drift away from it.
CONSTRAINT_CLASSES: tuple[str, ...] = (
    "public_accounting_fact",
    "definitional_support",
    "empirical_measurement",
    "modeling_assumption",
    "sensitivity_assumption",
)
HARD_ELIGIBLE_CLASSES: tuple[str, ...] = CONSTRAINT_CLASSES[:2]

# §7.8 does not enumerate `relation`, so these five are this package's decision. `integrality` is
# not a relation in the algebraic sense; it is here because INV-004 requires *every* restriction to
# carry a label, and a restriction recorded only as a column attribute would carry none.
RELATIONS: tuple[str, ...] = ("eq", "le", "ge", "range", "integrality")

# §7.10's suggested `bound_status` values, verbatim. Stage 2 emits five of the seven: it never
# emits `model_estimable` or `model_only`, because deciding that a cell is estimable requires a
# model and §9.1 forbids one at this stage.
BOUND_STATUSES: tuple[str, ...] = (
    "observed",
    "exactly_recoverable",
    "partially_identified",
    "model_estimable",
    "model_only",
    "unbounded",
    "infeasible",
)

# §7.11 names no reconciliation status and enumerates none, unlike `release_action`'s eight
# values, so these five are this package's decision. The separation that matters is the last two:
# a cell reconciled to the declared anchor is NOT a cell satisfying a hard public accounting
# constraint. INV-002 binds only the latter; INV-008 forbids relabelling one as the other.
RECONCILIATION_STATUSES: tuple[str, ...] = (
    "observed",
    "anchored_and_reconciled",
    "reconciled_no_anchor",
    "declined",
    "infeasible",
)

# Per-cell provenance for the weight that produced an estimate. §10.8's rank-1 phrasing
# ("employee-per-establishment with robust historical adjustment") is the spec's own precedent
# that a composed estimator is legitimate; this column is what keeps the composition declared
# rather than silent.
WEIGHT_BASES: tuple[str, ...] = ("own_estimator", "establishment_fallback", "none")

# What licensed the allocation target. Only one value is reachable in this stage;
# `verified_identity` exists for the retirement condition in the anchor's docstring, when a future
# QCEW vintage publishes a month with no suppressed cell and SRC-QCEW-006 becomes testable.
ANCHOR_BASES: tuple[str, ...] = ("declared_national_total", "verified_identity", "none")

# Why a declining estimator declined, as three groupable values rather than prose. §13.5-13.8
# score estimates against truth and define no decline metric, so an estimator whose months drop
# out of the scored set drops out non-randomly -- and a data bug can make a baseline's WAPE look
# BETTER than a correct implementation's. `decline_reason` stays free text beside this; the kind
# is what a scoreboard groups on.
DECLINE_KINDS: tuple[str, ...] = ("by_design", "data_gap", "reconciliation_failure")


def assert_declared_provenance(frame: pl.DataFrame) -> None:
    """Refuse a provenance value outside its declared tuple.

    The three tuples above are the closed sets a baseline row's provenance may draw from, but
    `BASELINE_RESULT_SCHEMA` checks dtypes only -- `pl.String` accepts any string. `weight_basis`
    is the live exposure: `run_baselines` copies it from an estimator's own `outcome.basis`, so a
    third-party estimator's typo reached `baseline_results.parquet` and passed every test. Nulls
    are permitted: a declining row carries no estimate and no weight to describe.
    """
    for column, allowed in (
        ("reconciliation_status", RECONCILIATION_STATUSES),
        ("weight_basis", WEIGHT_BASES),
        ("anchor_basis", ANCHOR_BASES),
        ("decline_kind", DECLINE_KINDS),
        ("suppression_type", SUPPRESSION_TYPES),
    ):
        if column not in frame.columns:
            continue
        seen = set(frame[column].drop_nulls().to_list())
        undeclared = sorted(seen - set(allowed))
        if undeclared:
            raise ConceptViolationError(
                f"{column} carries undeclared value(s) {undeclared}; the declared set is "
                f"{list(allowed)}. A value outside it reaches baseline_results.parquet and every "
                f"downstream consumer reads it as provenance."
            )


# What licenses a constraint, as a closed set rather than free prose. §7.8 has no column for it, so
# the row factory writes it into `provenance_text` behind an `evidence_kind=` prefix. It exists so
# that §9.3's forbidden forms can be refused *by name*: a restriction whose warrant is an assumed
# disclosure threshold can never be hard, whatever class a caller asks for.
EVIDENCE_KINDS: tuple[str, ...] = (
    "published_value",
    "class_definition",
    "unit_definition",
    "rounding_documentation",
    "empirical_fit",
    "assumed_threshold",
)
EVIDENCE_PREFIX = "evidence_kind="

TARGET_CELL_SCHEMA: dict[str, pl.DataType] = {
    "cell_id": pl.String,
    "state_fips": pl.String,
    "reference_month": pl.String,
    "size_concept": pl.String,
    "size_class": pl.String,
    "ownership_code": pl.String,
    "industry_code": pl.String,
    "naics_vintage": pl.String,
    "observation_status": pl.String,
    "observed_value": pl.Int64,
    "source_snapshot_id": pl.String,
    "qcew_disclosure_code": pl.String,
}

CONSTRAINT_ROW_SCHEMA: dict[str, pl.DataType] = {
    "constraint_id": pl.String,
    "component_id": pl.String,
    "constraint_class": pl.String,
    "relation": pl.String,
    "rhs_lower": pl.Float64,
    "rhs_upper": pl.Float64,
    "is_hard": pl.Boolean,
    "period_scope": pl.String,
    "geography_scope": pl.String,
    "industry_scope": pl.String,
    "ownership_scope": pl.String,
    "source_snapshot_ids": pl.String,
    "provenance_text": pl.String,
    "vintage_compatibility_status": pl.String,
}

CONSTRAINT_COEFFICIENT_SCHEMA: dict[str, pl.DataType] = {
    "constraint_id": pl.String,
    "cell_id": pl.String,
    "coefficient": pl.Float64,
}

DETERMINISTIC_BOUNDS_SCHEMA: dict[str, pl.DataType] = {
    "cell_id": pl.String,
    "component_id": pl.String,
    "rank": pl.Int64,
    "nullity": pl.Int64,
    "lp_lower": pl.Float64,
    "lp_upper": pl.Float64,
    "milp_lower": pl.Float64,
    "milp_upper": pl.Float64,
    "selected_lower": pl.Float64,
    "selected_upper": pl.Float64,
    "bound_status": pl.String,
    "exactly_identified": pl.Boolean,
    "integer_exactly_identified": pl.Boolean,
    "solver_status": pl.String,
    "solver_tolerance": pl.Float64,
    "constraint_set_hash": pl.String,
}

# One row per (estimator, cell). A declined cell is a row with a null `estimate` and a populated
# `decline_reason`, never an absent row: absence is indistinguishable from a bug.
BASELINE_RESULT_SCHEMA: dict[str, pl.DataType] = {
    "estimator_id": pl.String,
    "cell_id": pl.String,
    "state_fips": pl.String,
    "reference_month": pl.String,
    "raw_weight": pl.Float64,
    "estimate": pl.Float64,
    "estimate_integer": pl.Int64,
    "weight_basis": pl.String,
    "anchor_basis": pl.String,
    "reconciliation_status": pl.String,
    "decline_reason": pl.String,
    "decline_kind": pl.String,
    "residual": pl.Float64,
    "missing_set_size": pl.Int64,
    "constraint_set_hash": pl.String,
}

# One row per reference month. This is the anchor as a diffable artifact rather than a docstring:
# every number the admission gate looked at, recorded whether it passed or not.
ANCHOR_AUDIT_SCHEMA: dict[str, pl.DataType] = {
    "reference_month": pl.String,
    "national_total": pl.Int64,
    "national_establishments": pl.Int64,
    "state_establishments_sum": pl.Int64,
    "establishment_gap": pl.Int64,
    "publishing_area_count": pl.Int64,
    "disclosed_sum": pl.Int64,
    "disclosed_count": pl.Int64,
    "residual": pl.Int64,
    "missing_set_size": pl.Int64,
    "anchored": pl.Boolean,
    "implied_intensity": pl.Float64,
}


HOLDOUT_REGIMES: tuple[str, ...] = (
    "small_cell_biased",
    "concentration_proxy",
    "clustered_states_within_month",
    "long_consecutive_runs",
    "whole_state_year_blocks",
    "regional_blocks",
    "whole_seasonal_blocks",
    "rolling_origin",
    "retrospective_smoothing",
    "structural_break",
    "naics_transition",
    "preliminary_to_final_vintage",
    "cbp_size_gaps",
)

# Why a regime may not produce scores. `cannot_run_on_d1` is a REFUSAL, not a skip: the harness
# raises rather than emitting an empty partition that reads as "scored, nothing wrong".
REGIME_DISPOSITIONS: dict[str, str] = {
    "small_cell_biased": "feasible",
    "concentration_proxy": "feasible",
    "clustered_states_within_month": "feasible",
    "long_consecutive_runs": "feasible",
    "whole_state_year_blocks": "feasible",
    "regional_blocks": "feasible",
    "whole_seasonal_blocks": "feasible",
    "rolling_origin": "feasible",
    # No smoothing estimator exists in the §10 registry to exercise; adding one is a new baseline
    # outside §10's set and outside this stage.
    "retrospective_smoothing": "vacuous_on_registry",
    "structural_break": "feasible",
    "naics_transition": "feasible",
    # Measured 2026-09-07: no period in any staged table carries a second snapshot.
    "preliminary_to_final_vintage": "cannot_run_on_d1",
    "cbp_size_gaps": "feasible",
}

# What KIND of thing each Appendix A `include_*` switch is. Measured 2026-09-08, the seven were
# never a regime partition and every restatement that treated them as one has been wrong in a
# different way: four name regimes, two name INV-009 mask LABELS, and one names a design with no
# implementation anywhere in the package. Nine of the thirteen regimes have no switch at all.
SWITCH_KINDS: tuple[str, ...] = (
    "regime_switch",
    "mask_label_switch",
    "design_validity_operand",
)

VALIDATION_SWITCH_KINDS: dict[str, str] = {
    "include_long_runs": "regime_switch",
    "include_rolling_origin": "regime_switch",
    "include_retrospective_smoothing": "regime_switch",
    "include_vintage_comparison": "regime_switch",
    # §13.2 steps 3 and 8, not regime selection. These name the INV-009 label a masked cell
    # carries; every selector in `validate/regimes.py` constructs `primary_like` targets and
    # `scoreboard.assert_scored_cells_are_primary_like` refuses anything else on the scoring arm,
    # so the complementary half binds on the national-size March margin instead.
    "include_primary_like": "mask_label_switch",
    "include_complementary_like": "mask_label_switch",
    # An operand of `ValidationConfig._refuse_a_random_mask_only_design`, and the ONLY flag not in
    # that validator's disjunction — it is the design the §13.2 rule exists to exclude, not one of
    # the designed regimes that satisfies it. It has no implementation and gates no selection.
    "include_random_mask_sanity_check": "design_validity_operand",
}

# The four regime switches, as regime -> switch. NO FIELD IS ADDED OR REMOVED to build this:
# `runs.run_id` hashes `config.resolved_dict`, which is the whole model, so either direction
# re-identifies every run directory on disk and orphans `runs/f03023ac9f3a`. Changing a DEFAULT is
# free, because `config.yaml` pins all fourteen keys and no default reaches the resolved config —
# which is the opposite of what both `specs/deferred_items.md` and the roadmap asserted until
# 8ed7ecd.
REGIME_SWITCHES: dict[str, str] = {
    "long_consecutive_runs": "include_long_runs",
    "rolling_origin": "include_rolling_origin",
    "retrospective_smoothing": "include_retrospective_smoothing",
    "preliminary_to_final_vintage": "include_vintage_comparison",
}

MASK_ARMS: tuple[str, ...] = ("state_total", "national_size")

INTERVAL_SOURCES: tuple[str, ...] = ("rolling_residual_ensemble", "none")

# One row per (regime, seed, replicate, estimator, cell): the raw scored observations, including
# the ones that were declined. Distinct in grain from VALIDATION_METRIC_SCHEMA below, and
# conflating the two is how R-COMP-10's denominator gets lost.
#
# `replicate` is the INDEX OF THE SEED in `config.validation.pseudo_suppression_seeds`, so it is
# 1:1 with `seed` on any single run and the two together are one key rather than two. It is carried
# anyway because `pseudo_suppression_seeds` is configurable and a reader comparing two runs needs
# the slot as well as the value. `replicates_per_regime` is a DIFFERENT number: it sizes the mask
# (`regimes.sample_targets`), not this loop's trip count.
#
# The last six are the PROVENANCE columns `run_baselines` already writes and this schema used to
# omit, which is what made a scored row auditable and the declaration wrong at the same time. They
# are declared rather than dropped (R-S4C-14). `constraint_set_hash` and
# `masked_constraint_set_hash` are BOTH here and are different columns: the first rides in from
# `run_baselines`, the second is the hash of the masked system this replicate solved. Neither is a
# rename of the other and neither may be dropped as a duplicate.
VALIDATION_SCORE_SCHEMA: dict[str, pl.DataType] = {
    "regime": pl.String,
    "seed": pl.Int64,
    "replicate": pl.Int64,
    "mask_arm": pl.String,
    "estimator_id": pl.String,
    "cell_id": pl.String,
    "state_fips": pl.String,
    "reference_month": pl.String,
    "suppression_type": pl.String,
    "truth": pl.Float64,
    "estimate": pl.Float64,
    "estimate_integer": pl.Int64,
    "weight_basis": pl.String,
    "decline_kind": pl.String,
    "bound_status": pl.String,
    "selected_lower": pl.Float64,
    "selected_upper": pl.Float64,
    "masked_constraint_set_hash": pl.String,
    "lookback_months_masked": pl.Int64,
    "missing_set_size": pl.Int64,
    "raw_weight": pl.Float64,
    "anchor_basis": pl.String,
    "reconciliation_status": pl.String,
    "decline_reason": pl.String,
    "residual": pl.Float64,
    "constraint_set_hash": pl.String,
}

# One row per (regime, seed, estimator, metric_family): the §13.5-13.8 aggregates, each carrying
# its own denominator.
VALIDATION_METRIC_SCHEMA: dict[str, pl.DataType] = {
    "regime": pl.String,
    "seed": pl.Int64,
    "mask_arm": pl.String,
    "estimator_id": pl.String,
    "metric_family": pl.String,
    "metric_name": pl.String,
    "value": pl.Float64,
    # R-COMP-10: every scored comparison states the base it was computed over.
    "denominator": pl.Float64,
    "denominator_basis": pl.String,
    "n_scored": pl.Int64,
    "n_declined_by_design": pl.Int64,
    "n_declined_data_gap": pl.Int64,
    "n_declined_reconciliation_failure": pl.Int64,
    # Plan 10's refusals COMPOSE rather than decline, so they never reach the counts above.
    "n_own_estimator": pl.Int64,
    "n_establishment_fallback": pl.Int64,
    "interval_source": pl.String,
    "calibration_sample_size": pl.Int64,
    "bound_cells_finite_upper": pl.Int64,
    "constraint_rows_scored": pl.Int64,
}


_HARMONIZED_TABLES = ("qcew_monthly", "qcew_national_size", "cbp_state_size", "bridge")


@dataclass(frozen=True)
class HarmonizedData:
    """The Stage 1 harmonized layer, as §16.2's `build_constraint_system` receives it.

    Every downstream stage reads only this layer, never a source endpoint. Loading is eager and
    fails on the first missing file rather than deferring to a Polars error at first use, so a run
    started before `build-harmonized` halts with the path it wanted.
    """

    qcew_monthly: pl.DataFrame
    qcew_national_size: pl.DataFrame
    cbp_state_size: pl.DataFrame
    bridge: pl.DataFrame

    @classmethod
    def load(cls, staged_root: Path) -> HarmonizedData:
        """Read the four Stage 1 tables from a `data/staged`-shaped directory."""
        frames = {}
        for name in _HARMONIZED_TABLES:
            path = staged_root / f"{name}.parquet"
            if not path.exists():
                raise FileNotFoundError(
                    f"{path} is missing; run `logging-estimates build-harmonized` first"
                )
            frames[name] = pl.read_parquet(path)
        return cls(**frames)
