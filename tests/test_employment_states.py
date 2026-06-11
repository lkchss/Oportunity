"""
Tests for law/data/build_employment_states.py — parse, match, and merge logic.

Uses committed fixture text (synthetic ABA report text) rather than live PDFs
or actual downloaded files, so tests are fast, offline, and deterministic.
"""

import io
import json
import re
import tempfile
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Inline fixtures: representative ABA Employment Summary text blocks
# (mirroring exact pdfplumber output format)
# ---------------------------------------------------------------------------

# Synthetic Yale-like report
FIXTURE_YALE_TEXT = """\
YALE UNIVERSITY
ABA EMPLOYMENT SUMMARY FOR 2024 GRADUATES
EMPLOYMENT STATUS FULL TIME FULL TIME PART TIME PART TIME NUMBER
LONG TERM SHORT TERM LONG TERM SHORT TERM
Employed - Bar Admission Required/Anticipated 172 0 0 0 172
Employed - J.D. Advantage 11 0 0 1 12
Employed - Law School/University Funded 14 3 0 0 17
Total Graduates 215
EMPLOYMENT TYPE FULL TIME FULL TIME PART TIME PART TIME NUMBER
LONG TERM SHORT TERM LONG TERM SHORT TERM
501 + 66 0 0 0 66
Total 200 3 0 2 205
EMPLOYMENT LOCATION LOCATION NUMBER
State/U.S. Territory - Largest Employment NEW YORK 68
State/U.S. Territory - 2nd Largest Employment DISTRICT OF COLUMBIA 44
State/U.S. Territory - 3rd Largest Employment CALIFORNIA 21
Employed in Foreign Countries 4
"""

# Synthetic school with only 2 state locations
FIXTURE_TWO_STATES_TEXT = """\
NORTHWESTERN UNIVERSITY
ABA EMPLOYMENT SUMMARY FOR 2024 GRADUATES
Total Graduates 100
EMPLOYMENT LOCATION LOCATION NUMBER
State/U.S. Territory - Largest Employment ILLINOIS 60
State/U.S. Territory - 2nd Largest Employment NEW YORK 20
Employed in Foreign Countries 1
"""

# Synthetic report with no location section (edge case)
FIXTURE_NO_LOCATION_TEXT = """\
SOME LAW SCHOOL
ABA EMPLOYMENT SUMMARY FOR 2024 GRADUATES
Total Graduates 50
EMPLOYMENT TYPE FULL TIME NUMBER
Total 45 45
"""

# Synthetic report with territory (Puerto Rico)
FIXTURE_TERRITORY_TEXT = """\
UNIVERSITY OF PUERTO RICO
ABA EMPLOYMENT SUMMARY FOR 2024 GRADUATES
Total Graduates 120
EMPLOYMENT LOCATION LOCATION NUMBER
State/U.S. Territory - Largest Employment PUERTO RICO 95
State/U.S. Territory - 2nd Largest Employment FLORIDA 12
State/U.S. Territory - 3rd Largest Employment NEW YORK 8
Employed in Foreign Countries 0
"""


# ---------------------------------------------------------------------------
# Import the module under test (parse helpers only)
# ---------------------------------------------------------------------------

from law.data.build_employment_states import (
    STATE_NAMES,
    _compute_pct,
    _normalise_pdf_name,
    merge_phase,
)


# Re-implement _parse_pdf_bytes on text so we don't need a real PDF binary.
# This tests the parsing logic that sits between the PDF layer and the merge.
def _parse_text(text: str):
    """Same logic as _parse_pdf_bytes but operating on already-extracted text."""
    lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
    if not lines:
        return None
    school_name = lines[0]

    m = re.search(r"Total Graduates\s+(\d+)", text)
    total_grads = int(m.group(1)) if m else None

    loc_re = re.compile(
        r"State/U\.S\. Territory - (?:Largest|2nd Largest|3rd Largest) Employment"
        r"\s+([A-Z][A-Z ]+[A-Z])\s+(\d+)"
    )
    locations = []
    for lm in loc_re.finditer(text):
        state_full = lm.group(1).strip().upper()
        count = int(lm.group(2))
        code = STATE_NAMES.get(state_full, state_full[:2] if len(state_full) >= 2 else state_full)
        locations.append({"state": code, "count": count})

    if not locations:
        return None

    fm = re.search(r"Employed in Foreign Countries\s+(\d+)", text)
    foreign = int(fm.group(1)) if fm else 0

    return {
        "school_name": school_name,
        "total_grads": total_grads,
        "locations": locations,
        "foreign": foreign,
    }


# ---------------------------------------------------------------------------
# Parse tests
# ---------------------------------------------------------------------------

class TestParseText:
    def test_yale_school_name(self):
        result = _parse_text(FIXTURE_YALE_TEXT)
        assert result is not None
        assert result["school_name"] == "YALE UNIVERSITY"

    def test_yale_total_grads(self):
        result = _parse_text(FIXTURE_YALE_TEXT)
        assert result["total_grads"] == 215

    def test_yale_three_locations(self):
        result = _parse_text(FIXTURE_YALE_TEXT)
        locs = result["locations"]
        assert len(locs) == 3
        assert locs[0] == {"state": "NY", "count": 68}
        assert locs[1] == {"state": "DC", "count": 44}
        assert locs[2] == {"state": "CA", "count": 21}

    def test_yale_foreign(self):
        result = _parse_text(FIXTURE_YALE_TEXT)
        assert result["foreign"] == 4

    def test_two_state_report(self):
        result = _parse_text(FIXTURE_TWO_STATES_TEXT)
        assert result is not None
        assert len(result["locations"]) == 2
        assert result["locations"][0]["state"] == "IL"
        assert result["locations"][1]["state"] == "NY"

    def test_no_location_returns_none(self):
        result = _parse_text(FIXTURE_NO_LOCATION_TEXT)
        assert result is None

    def test_territory_state_code(self):
        result = _parse_text(FIXTURE_TERRITORY_TEXT)
        assert result is not None
        assert result["locations"][0]["state"] == "PR"

    def test_all_three_states_present(self):
        result = _parse_text(FIXTURE_TERRITORY_TEXT)
        assert len(result["locations"]) == 3


# ---------------------------------------------------------------------------
# _compute_pct tests
# ---------------------------------------------------------------------------

class TestComputePct:
    def test_basic_percentage(self):
        assert _compute_pct(68, 215) == pytest.approx(31.6, abs=0.1)

    def test_zero_total(self):
        assert _compute_pct(10, 0) == 0.0

    def test_full_pct(self):
        assert _compute_pct(100, 100) == 100.0

    def test_rounds_to_one_decimal(self):
        # 1/3 = 33.333... should round to 33.3
        result = _compute_pct(1, 3)
        assert result == pytest.approx(33.3, abs=0.05)


# ---------------------------------------------------------------------------
# _normalise_pdf_name tests
# ---------------------------------------------------------------------------

class TestNormalisePdfName:
    def test_uppercase(self):
        assert _normalise_pdf_name("Yale University") == "YALE UNIVERSITY"

    def test_strips_whitespace(self):
        assert _normalise_pdf_name("  DUKE UNIVERSITY  ") == "DUKE UNIVERSITY"


# ---------------------------------------------------------------------------
# Merge phase tests (with a synthetic law_schools.json)
# ---------------------------------------------------------------------------

# Minimal valid school record matching what _validate_entry expects
_BASE_SCHOOL = {
    "id": "yale-law",
    "name": "Yale Law School",
    "location": "New Haven, CT",
    "state": "CT",
    "website_url": "https://law.yale.edu",
    "usnwr_rank_2026": 1,
    "is_public": False,
    "lsat_25": 173, "lsat_50": 176, "lsat_75": 178,
    "gpa_25": 3.82, "gpa_50": 3.93, "gpa_75": 3.98,
    "acceptance_rate": 0.06,
    "scholarship_pct": 0.55,
    "median_scholarship": 30000,
    "biglaw_pct": 0.30,
    "federal_clerkship_pct": 0.26,
    "government_pct": 0.04,
    "public_interest_pct": 0.16,
    "solo_small_firm_pct": 0.01,
    "jd_required_pct": 0.85,
    "bar_pass_rate_first_time": 0.95,
    "median_private_sector_salary": 190000,
    "median_public_sector_salary": 62000,
    "practice_area_strengths": ["public_interest"],
    "lrap_quality": "excellent",
    "target_states": ["CT", "NY"],
    "annual_tuition": 70000,
    "annual_tuition_resident": 70000,
    "annual_tuition_nonresident": 70000,
    "cost_of_living_index": 125,
}


class TestMergePhase:
    def _make_json(self, tmp_path: Path, schools: list) -> Path:
        p = tmp_path / "law_schools.json"
        p.write_text(json.dumps({"schools": schools}), encoding="utf-8")
        return p

    def test_writes_placement_states(self, tmp_path):
        school = dict(_BASE_SCHOOL)
        json_path = self._make_json(tmp_path, [school])

        parsed = {
            25: {
                "school_name": "YALE UNIVERSITY",
                "total_grads": 215,
                "locations": [
                    {"state": "NY", "count": 68},
                    {"state": "DC", "count": 44},
                    {"state": "CA", "count": 21},
                ],
                "foreign": 4,
            }
        }

        merge_phase(parsed, json_path=json_path)

        result = json.loads(json_path.read_text(encoding="utf-8"))
        yale = result["schools"][0]
        assert yale["placement_year"] == 2024
        states = yale["placement_states"]
        assert len(states) == 3
        assert states[0]["state"] == "NY"
        assert states[0]["pct"] == pytest.approx(31.6, abs=0.1)

    def test_unmatched_school_gets_null(self, tmp_path):
        school = dict(_BASE_SCHOOL)
        json_path = self._make_json(tmp_path, [school])

        # Parsed data with a name that won't match yale-law
        parsed = {
            99: {
                "school_name": "SOME UNKNOWN SCHOOL",
                "total_grads": 100,
                "locations": [{"state": "TX", "count": 50}],
                "foreign": 0,
            }
        }

        merge_phase(parsed, json_path=json_path)

        result = json.loads(json_path.read_text(encoding="utf-8"))
        yale = result["schools"][0]
        assert yale["placement_states"] is None
        assert yale["placement_year"] is None

    def test_zero_grads_gets_null(self, tmp_path):
        school = dict(_BASE_SCHOOL)
        json_path = self._make_json(tmp_path, [school])

        parsed = {
            25: {
                "school_name": "YALE UNIVERSITY",
                "total_grads": 0,
                "locations": [{"state": "NY", "count": 0}],
                "foreign": 0,
            }
        }

        merge_phase(parsed, json_path=json_path)

        result = json.loads(json_path.read_text(encoding="utf-8"))
        yale = result["schools"][0]
        assert yale["placement_states"] is None

    def test_extract_json_written(self, tmp_path, monkeypatch):
        """merge_phase writes an intermediate employment_states.json extract."""
        import law.data.build_employment_states as bes
        original = bes.EXTRACT_JSON
        monkeypatch.setattr(bes, "EXTRACT_JSON", tmp_path / "employment_states.json")

        school = dict(_BASE_SCHOOL)
        json_path = self._make_json(tmp_path, [school])

        parsed = {
            25: {
                "school_name": "YALE UNIVERSITY",
                "total_grads": 215,
                "locations": [{"state": "NY", "count": 68}],
                "foreign": 4,
            }
        }
        merge_phase(parsed, json_path=json_path)

        extract_path = tmp_path / "employment_states.json"
        assert extract_path.exists()
        extract = json.loads(extract_path.read_text(encoding="utf-8"))
        assert "25" in extract
