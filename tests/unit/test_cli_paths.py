"""CLI helpers that resolve a path or an option before any table is read."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from logging_employment.cli import _constraints_dir, _estimator_override, app
from logging_employment.config import load_config
from logging_employment.errors import ConceptViolationError

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


def test_no_estimator_option_means_no_override_at_all() -> None:
    """`None`, not an empty mapping -- `run_id` then omits the key and hashes as it always did."""
    assert _estimator_override(None) is None


def test_the_estimator_option_is_canonicalised_so_two_orderings_are_one_run() -> None:
    """`a,b` and `b,a` name the same set, so they must name the same run directory.

    Surrounding whitespace is stripped for the same reason: `'a, b'` is the way a human types the
    list, and a stray space that survived into the id would silently open a second directory
    holding byte-identical outputs.
    """
    typed = _estimator_override("share_last_observed, establishment_proportional")
    reversed_ = _estimator_override("establishment_proportional,share_last_observed")
    assert (
        typed == reversed_ == {"estimators": ["establishment_proportional", "share_last_observed"]}
    )


def test_an_unknown_estimator_id_is_refused_by_the_helper() -> None:
    with pytest.raises(ConceptViolationError):
        _estimator_override("establishment_proportional,no_such_estimator")


def test_validate_refuses_an_unknown_estimator_before_it_reads_the_staged_layer(
    tmp_path: Path,
) -> None:
    """The refusal is a message, not a table load -- and this proves the ORDER, not just the exit.

    `staged_uri` points at a directory that does not exist, so a command that resolved the option
    after loading `HarmonizedData` would fail on the missing tables instead. Exiting on the
    estimator name is what shows the check runs first.
    """
    raw = yaml.safe_load((REPO / "config.yaml").read_text())
    raw["storage"]["staged_uri"] = str(tmp_path / "there-is-no-staged-layer-here")
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(raw))

    result = CliRunner().invoke(
        app, ["validate", "--config", str(path), "--estimators", "no_such_estimator"]
    )
    assert result.exit_code == 2, result.output
    assert "no_such_estimator" in result.output
    assert "establishment_proportional" in result.output


def test_validate_without_the_option_reaches_the_staged_layer_unchanged(tmp_path: Path) -> None:
    """The DEFAULT path, which no affordable end-to-end test covers: omitting `--estimators`.

    A full-registry `validate` is ~3.8 minutes, so the integration test always passes a subset and
    the production default would otherwise be exercised nowhere through the CLI. This gets at it
    without paying for a harness run: with `staged_uri` pointing nowhere, a command whose option
    layer handled the missing flag correctly gets as far as loading tables and fails THERE, while
    one that mishandled it would fail at the option instead. `--estimators` is absent from the
    message for the same reason it is absent from the run id.
    """
    raw = yaml.safe_load((REPO / "config.yaml").read_text())
    raw["storage"]["staged_uri"] = str(tmp_path / "there-is-no-staged-layer-here")
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(raw))

    result = CliRunner().invoke(app, ["validate", "--config", str(path)])
    # Exit 2 is typer's USAGE error -- what a mishandled option produces, and what the sibling
    # test above asserts for a bad id. Exit 1 with a FileNotFoundError is the command running far
    # enough to look for tables. Asserting the exception type rather than the absence of a word in
    # `result.output` matters: CliRunner leaves output empty on an uncaught exception, so a
    # "the message does not mention estimators" assertion would pass against nothing at all.
    assert result.exit_code == 1, result.output
    assert isinstance(result.exception, FileNotFoundError)
    assert "build-harmonized" in str(result.exception)
