"""The §3.1 memo is read from the spec, not retyped."""

from __future__ import annotations

from pathlib import Path

import pytest

from logging_employment.classification import classification_memo

SPEC = Path(__file__).resolve().parents[2] / "specs" / "logging-employment-spec.md"


def test_memo_carries_all_four_fields_from_the_spec() -> None:
    memo = classification_memo(SPEC)
    assert set(memo) == {
        "industry_code_supplied",
        "industry_code_used",
        "industry_title",
        "classification_status",
    }
    assert memo["industry_code_used"] == "113310"


def test_memo_reads_the_section_31_fence_and_not_appendix_a(tmp_path: Path) -> None:
    # Appendix A carries three of the four names in YAML `key: value` form. A parser that scanned
    # the whole file could read them from there; an anchored one cannot reach them.
    doctored = tmp_path / "spec.md"
    doctored.write_text(
        "### 3.1 Classification decision\n\n```text\n"
        "industry_code_supplied = 'AAA'\nindustry_code_used = 'BBB'\n"
        "industry_title = 'Anchored'\nclassification_status = 'from_section_31'\n```\n\n"
        "## Appendix A\n\n```yaml\nindustry_code_used: 'WRONG'\nindustry_title: 'Wrong'\n```\n"
    )
    assert classification_memo(doctored)["industry_title"] == "Anchored"


def test_memo_raises_when_section_31_is_missing(tmp_path: Path) -> None:
    empty = tmp_path / "spec.md"
    empty.write_text("## 2. Something else\n\n```text\nindustry_code_used = '113310'\n```\n")
    with pytest.raises(ValueError, match="3.1"):
        classification_memo(empty)
