"""The package installs and exposes a version."""

from __future__ import annotations


def test_package_exposes_a_version_string() -> None:
    import logging_employment

    assert isinstance(logging_employment.__version__, str)
    assert logging_employment.__version__.count(".") >= 1
