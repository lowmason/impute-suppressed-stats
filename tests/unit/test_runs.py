"""`run_id`'s payload: what goes into it, and what deliberately stays out of it."""

from __future__ import annotations

import hashlib
import json

from logging_employment.config import Config, resolved_dict
from logging_employment.runs import RUN_ID_LENGTH, run_id

DIGESTS = {"qcew_monthly": "aa" * 32, "bridge": "bb" * 32}


def _payload_before_overrides_existed(cfg: Config) -> str:
    """The id as it was computed before `run_id` grew an `overrides` parameter.

    Re-derived from `resolved_dict` rather than pinned as a literal: a literal would encode
    today's `config.yaml` and would have to be re-typed on every unrelated config change, which
    is exactly how a compatibility pin stops checking compatibility and starts checking nothing.
    """
    payload = json.dumps(
        {"config": resolved_dict(cfg), "inputs": dict(sorted(DIGESTS.items()))}, sort_keys=True
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:RUN_ID_LENGTH]


def test_a_run_with_no_override_hashes_exactly_as_it_did_before_the_parameter_existed(
    appendix_a_config: Config,
) -> None:
    """The whole reason `overrides` is omitted rather than emitted as null.

    Emitting `"overrides": null` would have re-identified every directory under `runs/` for a key
    that says nothing -- orphaning Stage 4's acceptance artifact, and making `solve-bounds` and
    `run-baselines` refuse until a full rebuild. This is the test that keeps that from happening
    by accident later.
    """
    assert run_id(appendix_a_config, DIGESTS) == _payload_before_overrides_existed(
        appendix_a_config
    )


def test_an_empty_override_mapping_is_the_same_as_none(appendix_a_config: Config) -> None:
    """`{}` means "nothing was overridden", so it must not fork the id either."""
    assert run_id(appendix_a_config, DIGESTS, overrides={}) == run_id(appendix_a_config, DIGESTS)


def test_an_estimator_subset_gets_its_own_run_id(appendix_a_config: Config) -> None:
    """The point of routing the subset through the id: it cannot land on a full pass's outputs.

    Same config, same inputs, different estimators -- if these collided, the two runs would write
    different bytes to one `runs/<id>/validation_metrics.parquet` under a single identifier.
    """
    full = run_id(appendix_a_config, DIGESTS)
    subset = run_id(appendix_a_config, DIGESTS, overrides={"estimators": ["equal_residual"]})
    other = run_id(
        appendix_a_config, DIGESTS, overrides={"estimators": ["establishment_proportional"]}
    )
    assert len({full, subset, other}) == 3
