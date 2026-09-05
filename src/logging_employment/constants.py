"""Fixed values for the D1 window, the target industry, and the measured QCEW code sets."""

from __future__ import annotations

WINDOW_START = "2017-01"
WINDOW_END = "2024-12"

INDUSTRY_CODE = "113310"
PRIVATE_OWN_CODE = "5"

NATIONAL_AREA = "US000"
STATES_DC_FIPS: tuple[str, ...] = (
    "01", "02", "04", "05", "06", "08", "09", "10", "11", "12", "13", "15", "16", "17",
    "18", "19", "20", "21", "22", "23", "24", "25", "26", "27", "28", "29", "30", "31",
    "32", "33", "34", "35", "36", "37", "38", "39", "40", "41", "42", "44", "45", "46",
    "47", "48", "49", "50", "51", "53", "54", "55", "56",
)
STATE_AREAS = frozenset(f"{fips}000" for fips in STATES_DC_FIPS)

QCEW_NATIONAL_AGGLVL = "18"  # "National, NAICS 6-digit -- by ownership sector"
QCEW_STATE_AGGLVL = "58"  # "State, NAICS 6-digit -- by ownership sector"
QCEW_ALL_SIZES_CODE = "0"  # "All establishment sizes"

# QCEW_DISCLOSURE_CODES holds the three disclosure codes measured on 113310 rows across the
# whole D1 window by the Stage 0 audit (`qcew_codes.findings.codes_present.disclosure_code`):
# '' 17302 rows, '-' 935, 'N' 40875. BLS publishes no titles file for this dimension -- Stage 0
# recorded `titles_available.disclosure_code = null` -- so this set is measured, not documented,
# and nothing here defines what a code means. A fourth code halting the run (§18.3) is the
# correct response to a set that was only ever observed.
QCEW_DISCLOSURE_CODES = frozenset({"", "N", "-"})
