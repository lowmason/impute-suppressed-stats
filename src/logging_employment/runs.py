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


def run_id(config: Config, input_digests: Mapping[str, str]) -> str:
    """A stable identifier for one run: the resolved config plus every input's digest."""
    payload = json.dumps(
        {"config": resolved_dict(config), "inputs": dict(sorted(input_digests.items()))},
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:RUN_ID_LENGTH]


def run_dir(config: Config, identifier: str) -> Path:
    """The directory this run's outputs belong in."""
    return Path(config.storage.output_uri) / identifier
