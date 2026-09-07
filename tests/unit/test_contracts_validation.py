import polars as pl
import pytest

from logging_employment import contracts
from logging_employment.errors import ConceptViolationError


def test_a_suppression_type_outside_the_declared_set_is_refused():
    frame = pl.DataFrame({"suppression_type": ["primary_like", "invented_kind"]})
    with pytest.raises(ConceptViolationError, match="suppression_type"):
        contracts.assert_declared_provenance(frame)


def test_the_declared_suppression_types_pass():
    frame = pl.DataFrame({"suppression_type": ["unknown", "primary_like", "complementary_like"]})
    contracts.assert_declared_provenance(frame)


def test_every_holdout_regime_carries_a_disposition():
    assert set(contracts.REGIME_DISPOSITIONS) == set(contracts.HOLDOUT_REGIMES)
    assert contracts.REGIME_DISPOSITIONS["preliminary_to_final_vintage"] == "cannot_run_on_d1"


def test_the_two_validation_schemas_are_distinct_and_fingerprinted():
    a = contracts.schema_fingerprint(contracts.VALIDATION_SCORE_SCHEMA)
    b = contracts.schema_fingerprint(contracts.VALIDATION_METRIC_SCHEMA)
    assert a != b
    # R-COMP-10: a metric row is unreadable without the base it was computed over.
    assert "denominator" in contracts.VALIDATION_METRIC_SCHEMA
    assert "denominator_basis" in contracts.VALIDATION_METRIC_SCHEMA
