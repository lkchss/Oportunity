"""
Unit tests for the selectivity trend feature.

Covers:
  1. build_selectivity_trend.py — parse logic and merge
  2. data_loader.py — _validate_selectivity_trend validation
  3. Integration — real law_schools.json field coverage and value ranges
"""

import io
import json
import tempfile
from pathlib import Path
from typing import Optional
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from law.data_loader import DataValidationError, _validate_entry, load_law_schools
from law.data.build_selectivity_trend import _parse_row, main as trend_main


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

def _make_fy_row(lsat_50=165, gpa_50=3.70, accept_rate=25.0,
                  apps=1000, offers=250) -> pd.Series:
    """Build a minimal First Year Class row for testing."""
    return pd.Series({
        "SchoolName": "Test Law School",
        "SchoolYear": 2023,
        "All50thPercentileLSAT": lsat_50,
        "All50thPercentileUGPA": gpa_50,
        "AcceptanceRate": accept_rate,  # percentage (e.g. 25.0 = 25%)
        "Applications": apps,
        "Offers": offers,
    })


VALID_SCHOOL = {
    "id": "test-law",
    "name": "Test Law School",
    "location": "Test City, TS",
    "website_url": "https://test.edu",
    "lsat_25": 150, "lsat_50": 165, "lsat_75": 170,
    "gpa_25": 3.0, "gpa_50": 3.5, "gpa_75": 4.0,
    "acceptance_rate": 0.25,
    "scholarship_pct": 0.80,
    "median_scholarship": 25000,
    "biglaw_pct": 0.15,
    "federal_clerkship_pct": 0.05,
    "public_interest_pct": 0.10,
    "government_pct": 0.08,
    "solo_small_firm_pct": 0.10,
    "jd_required_pct": 0.85,
    "bar_pass_rate_first_time": 0.85,
    "practice_area_strengths": [],
    "lrap_quality": "basic",
    "annual_tuition": 50000,
    "annual_tuition_resident": 45000,
    "annual_tuition_nonresident": 50000,
    "cost_of_living_index": 100,
    "state": "TS",
    "usnwr_rank_2026": 50,
    "is_public": False,
    "median_private_sector_salary": 90000,
    "median_public_sector_salary": 58000,
    "target_states": ["TS"],
}


# ---------------------------------------------------------------------------
# 1. _parse_row tests
# ---------------------------------------------------------------------------

class TestParseRow:
    def test_normal_row(self):
        row = _make_fy_row(lsat_50=170, gpa_50=3.92, accept_rate=9.58)
        result = _parse_row(row)
        assert result is not None
        assert result["lsat_50"] == 170
        assert result["gpa_50"] == 3.92
        # 9.58% -> 0.0958
        assert abs(result["accept_rate"] - 0.0958) < 0.001

    def test_accept_rate_converts_pct_to_fraction(self):
        row = _make_fy_row(accept_rate=25.0)
        result = _parse_row(row)
        assert result is not None
        assert result["accept_rate"] == pytest.approx(0.25, abs=0.001)

    def test_missing_lsat_returns_none(self):
        row = _make_fy_row(lsat_50=0)
        result = _parse_row(row)
        assert result is None

    def test_missing_gpa_returns_none(self):
        row = _make_fy_row(gpa_50=0)
        result = _parse_row(row)
        assert result is None

    def test_fallback_to_offers_over_apps_when_no_accept_rate(self):
        row = _make_fy_row(accept_rate=0, apps=400, offers=100)
        result = _parse_row(row)
        assert result is not None
        assert result["accept_rate"] == pytest.approx(0.25, abs=0.001)

    def test_lsat_50_is_int(self):
        row = _make_fy_row(lsat_50=165.0)  # xlsx sometimes returns float
        result = _parse_row(row)
        assert result is not None
        assert isinstance(result["lsat_50"], int)

    def test_gpa_50_is_rounded_to_2dp(self):
        row = _make_fy_row(gpa_50=3.7777)
        result = _parse_row(row)
        assert result is not None
        assert result["gpa_50"] == 3.78


# ---------------------------------------------------------------------------
# 2. _validate_selectivity_trend (via _validate_entry) tests
# ---------------------------------------------------------------------------

class TestValidateSelectivityTrend:
    def _school_with_trend(self, trend):
        s = VALID_SCHOOL.copy()
        s["selectivity_trend"] = trend
        return s

    def test_valid_three_year_trend(self):
        school = self._school_with_trend({
            "years": [2023, 2024, 2025],
            "lsat_50": [165, 166, 167],
            "gpa_50": [3.70, 3.72, 3.75],
            "accept_rate": [0.28, 0.24, 0.21],
        })
        _validate_entry(school)  # must not raise

    def test_valid_two_year_trend(self):
        school = self._school_with_trend({
            "years": [2024, 2025],
            "lsat_50": [165, 166],
            "gpa_50": [3.70, 3.72],
            "accept_rate": [0.28, 0.24],
        })
        _validate_entry(school)  # must not raise

    def test_none_trend_is_accepted(self):
        school = VALID_SCHOOL.copy()
        school["selectivity_trend"] = None
        _validate_entry(school)  # None means "not computed yet" — OK

    def test_missing_key_raises(self):
        school = self._school_with_trend({
            "years": [2023, 2024],
            "lsat_50": [165, 166],
            # gpa_50 missing
            "accept_rate": [0.28, 0.24],
        })
        with pytest.raises(DataValidationError, match="gpa_50"):
            _validate_entry(school)

    def test_parallel_array_length_mismatch_raises(self):
        school = self._school_with_trend({
            "years": [2023, 2024, 2025],
            "lsat_50": [165, 166],          # only 2 values for 3 years
            "gpa_50": [3.70, 3.72, 3.75],
            "accept_rate": [0.28, 0.24, 0.21],
        })
        with pytest.raises(DataValidationError, match="lsat_50"):
            _validate_entry(school)

    def test_single_year_raises(self):
        school = self._school_with_trend({
            "years": [2025],
            "lsat_50": [165],
            "gpa_50": [3.70],
            "accept_rate": [0.28],
        })
        with pytest.raises(DataValidationError, match=">=2 years"):
            _validate_entry(school)

    def test_lsat_out_of_range_raises(self):
        school = self._school_with_trend({
            "years": [2024, 2025],
            "lsat_50": [99, 165],   # 99 < 100
            "gpa_50": [3.70, 3.72],
            "accept_rate": [0.28, 0.24],
        })
        with pytest.raises(DataValidationError, match="lsat_50"):
            _validate_entry(school)

    def test_gpa_out_of_range_raises(self):
        school = self._school_with_trend({
            "years": [2024, 2025],
            "lsat_50": [165, 166],
            "gpa_50": [5.0, 3.72],  # 5.0 > 4.33
            "accept_rate": [0.28, 0.24],
        })
        with pytest.raises(DataValidationError, match="gpa_50"):
            _validate_entry(school)

    def test_accept_rate_out_of_range_raises(self):
        school = self._school_with_trend({
            "years": [2024, 2025],
            "lsat_50": [165, 166],
            "gpa_50": [3.70, 3.72],
            "accept_rate": [1.5, 0.24],  # 1.5 > 1.0
        })
        with pytest.raises(DataValidationError, match="accept_rate"):
            _validate_entry(school)

    def test_not_a_dict_raises(self):
        school = self._school_with_trend([2023, 2024])  # wrong type
        with pytest.raises(DataValidationError, match="must be a dict"):
            _validate_entry(school)


# ---------------------------------------------------------------------------
# 3. Integration — real data
# ---------------------------------------------------------------------------

class TestSelectivityTrendIntegration:
    """Validate the selectivity_trend field against the live law_schools.json."""

    @pytest.fixture(scope="class")
    def schools(self):
        return load_law_schools()

    def test_most_schools_have_trend(self, schools):
        """At least 190/196 schools should have a 3-year trend (all files present)."""
        with_trend = [s for s in schools if s.get("selectivity_trend") is not None]
        assert len(with_trend) >= 190, (
            f"Expected >=190 schools with selectivity_trend, got {len(with_trend)}"
        )

    def test_trend_has_all_three_years(self, schools):
        """Schools with a trend should include 2023, 2024, and 2025."""
        for s in schools:
            t = s.get("selectivity_trend")
            if t is None:
                continue
            assert 2025 in t["years"], f"{s['id']}: missing 2025 in trend"
            assert len(t["years"]) >= 2

    def test_lsat_values_in_range(self, schools):
        for s in schools:
            t = s.get("selectivity_trend")
            if t is None:
                continue
            for v in t["lsat_50"]:
                if v is not None:
                    assert 100 <= v <= 180, f"{s['id']}: lsat {v} out of range"

    def test_gpa_values_in_range(self, schools):
        for s in schools:
            t = s.get("selectivity_trend")
            if t is None:
                continue
            for v in t["gpa_50"]:
                if v is not None:
                    assert 0.0 <= v <= 4.33, f"{s['id']}: gpa {v} out of range"

    def test_accept_rate_in_range(self, schools):
        for s in schools:
            t = s.get("selectivity_trend")
            if t is None:
                continue
            for v in t["accept_rate"]:
                if v is not None:
                    assert 0.0 <= v <= 1.0, f"{s['id']}: accept_rate {v} out of range"

    def test_parallel_arrays_same_length(self, schools):
        for s in schools:
            t = s.get("selectivity_trend")
            if t is None:
                continue
            n = len(t["years"])
            assert len(t["lsat_50"]) == n
            assert len(t["gpa_50"]) == n
            assert len(t["accept_rate"]) == n

    def test_known_schools_plausible(self, schools):
        """Spot-check Yale and Harvard for plausible values."""
        by_id = {s["id"]: s for s in schools}

        yale = by_id["yale-law"]["selectivity_trend"]
        assert yale is not None
        assert all(v >= 173 for v in yale["lsat_50"])  # Yale never dips below 173
        assert all(v <= 0.12 for v in yale["accept_rate"])  # Yale always <12%

        harvard = by_id["harvard-law"]["selectivity_trend"]
        assert harvard is not None
        assert all(v >= 172 for v in harvard["lsat_50"])
