"""§16.1 idempotence for the CBP gap selector, which had no test and no caller until now."""

import subprocess
import sys
import textwrap
from pathlib import Path

from logging_employment.config import load_config
from logging_employment.contracts import HarmonizedData
from logging_employment.validate.regimes import apply_cbp_gap, cbp_size_gap_keys

FIXTURE = Path("tests/fixtures/baselines")

_DRAW = """
from pathlib import Path
from logging_employment.config import load_config
from logging_employment.contracts import HarmonizedData
from logging_employment.validate.regimes import cbp_size_gap_keys

data = HarmonizedData.load(Path("tests/fixtures/baselines"))
cfg = load_config(Path("config.yaml"))
print(cbp_size_gap_keys(data, seed=1024, config=cfg))
"""


def test_the_same_seed_gives_the_same_keys_in_separate_processes():
    """V6/M6: `unique()` gives no order guarantee, so a seeded sample over it is not reproducible.

    PER CALL — not merely per process. Re-measured 2026-09-09: six consecutive calls in ONE
    process, on the same `HarmonizedData` object at the same seed, returned six distinct key sets
    (symmetric difference 26 of 40 between the first two). Measured 2026-09-08 before the fix,
    three runs of this exact program produced three different 20-key sets — which is why the
    sibling defect at `_clustered` and `_state_year` was caught twice and this one never was.

    The subprocess shape is a DELIBERATE CHOICE, not a necessity: it matches how the harness is
    actually invoked, and it is the form that pins the property a caller depends on. Do not weaken
    it to an in-process loop on the grounds that one would witness the defect too.
    """
    drawn = {
        subprocess.run(
            [sys.executable, "-c", textwrap.dedent(_DRAW)],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        for _ in range(3)
    }
    assert len(drawn) == 1, f"three processes drew {len(drawn)} different key sets"


def test_the_gap_removes_the_whole_state_year_across_every_size_code():
    """M3: this is a state-YEAR gap, not a size gap, whatever the identifier says."""
    data = HarmonizedData.load(FIXTURE)
    keys = cbp_size_gap_keys(data, seed=1024, config=load_config(Path("config.yaml")))
    gapped = apply_cbp_gap(data, keys[:1])
    state, year = keys[0]
    before = data.cbp_state_size.filter(
        (data.cbp_state_size["state_fips"] == state)
        & (data.cbp_state_size["reference_year"] == year)
    )
    after = gapped.cbp_state_size.filter(
        (gapped.cbp_state_size["state_fips"] == state)
        & (gapped.cbp_state_size["reference_year"] == year)
    )
    assert before.height > 1, "the fixture must carry more than one size row for this state-year"
    assert after.height == 0
    assert gapped.cbp_state_size.height == data.cbp_state_size.height - before.height


def test_an_empty_key_list_returns_the_data_untouched():
    data = HarmonizedData.load(FIXTURE)
    assert apply_cbp_gap(data, []) is data
