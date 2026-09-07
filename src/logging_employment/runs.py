"""The `runs/<run_id>/` layout of §6.2, with a run id derived from inputs rather than a clock.

§16.1 requires every command to be idempotent for the same inputs. A timestamp or a UUID would
make each invocation land in a new directory, so "idempotent" could only ever mean "wrote the same
bytes somewhere else". Deriving the id from the resolved configuration and the input digests makes
a repeated run land on its own previous output, where byte-identity is checkable.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path

from .config import Config, resolved_dict

RUN_ID_LENGTH = 12


def run_id(
    config: Config,
    input_digests: Mapping[str, str],
    *,
    overrides: Mapping[str, object] | None = None,
) -> str:
    """A stable identifier for one run: the resolved config, every input's digest, and overrides.

    `overrides` carries a command-line choice that changes WHAT the run computes but that no
    config file declared -- today, `validate --estimators`. It must reach the id: a subset that
    stopped at `argv` would hash to the same directory as a full pass and overwrite its outputs
    with different bytes under one identifier, which is precisely the byte-identity this scheme
    exists to make checkable.

    The key is OMITTED, not emitted as null, when there is no override. That keeps the payload of
    an un-overridden run byte-identical to the payload used before this parameter existed, so
    adding the option renumbered no existing run directory -- `runs/f03023ac9f3a` still resolves
    from `config.yaml`. Emitting `"overrides": null` would have re-identified every run on disk
    and orphaned Stage 4's acceptance artifact for a key that says nothing.
    """
    payload: dict[str, object] = {
        "config": resolved_dict(config),
        "inputs": dict(sorted(input_digests.items())),
    }
    if overrides:
        payload["overrides"] = dict(sorted(overrides.items()))
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()[
        :RUN_ID_LENGTH
    ]


def run_dir(config: Config, identifier: str) -> Path:
    """The directory this run's outputs belong in."""
    return Path(config.storage.output_uri) / identifier
