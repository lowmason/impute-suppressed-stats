"""`_constraints_dir` reads §6.2's location from config instead of inferring it from a sibling."""

from __future__ import annotations

from pathlib import Path

import yaml

from logging_employment.cli import _constraints_dir
from logging_employment.config import load_config

REPO = Path(__file__).resolve().parents[2]


def test_the_constraints_directory_does_not_move_when_the_staged_root_does(
    tmp_path: Path,
) -> None:
    """§6.2's `data/constraints/` is configured, not derived from `staged_uri`'s parent.

    Deriving it silently relocated the constraint tables whenever `staged_uri` was pointed
    outside `data/` -- into a sibling of a directory nobody chose.
    """
    raw = yaml.safe_load((REPO / "config.yaml").read_text())
    raw["storage"]["staged_uri"] = str(tmp_path / "elsewhere" / "staged")
    raw["storage"]["constraints_uri"] = str(tmp_path / "chosen")
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(raw))
    assert _constraints_dir(load_config(path)) == tmp_path / "chosen"
