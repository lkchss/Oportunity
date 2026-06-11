import json
import pytest
import tempfile
from pathlib import Path

from law.data_loader import (
    load_law_schools,
    DataValidationError,
    _validate_entry,
    _get_data_path,
)


# Valid school entry for testing
VALID_SCHOOL = {
    "id": "test-law",
    "name": "Test Law School",
    "location": "Test City, TS",
    "website_url": "https://test.edu",
    "lsat_25": 150,
    "lsat_50": 160,
    "lsat_75": 170,
    "gpa_25": 3.0,
    "gpa_50": 3.5,
    "gpa_75": 4.0,
    "acceptance_rate": 0.25,
    "scholarship_pct": 0.80,
    "median_scholarship": 25000,
    "biglaw_pct": 0.15,
    "federal_clerkship_pct": 0.05,
    "public_interest_pct": 0.10,
    "government_pct": 0.08,
    "bar_pass_rate_first_time": 0.85,
    "practice_area_strengths": ["corporate", "litigation"],
    "lrap_quality": "basic",
    "annual_tuition": 50000,
    "cost_of_living_index": 3,
    # Fields added when the schema gained state/rank/public-private, NALP
    # salary + solo/JD-required outcomes, target states, and resident vs
    # nonresident tuition. Kept in sync with REQUIRED_FIELDS in law/data_loader.py.
    "state": "TS",
    "usnwr_rank_2026": 50,
    "is_public": False,
    "solo_small_firm_pct": 0.10,
    "jd_required_pct": 0.85,
    "median_private_sector_salary": 90000,
    "median_public_sector_salary": 58000,
    "target_states": ["TS"],
    "annual_tuition_resident": 45000,
    "annual_tuition_nonresident": 50000,
}


class TestValidateEntry:
    """Test the _validate_entry function."""

    def test_valid_entry(self):
        """Valid entry should not raise."""
        _validate_entry(VALID_SCHOOL)

    def test_missing_required_field(self):
        """Entry missing a required field should raise DataValidationError."""
        school = VALID_SCHOOL.copy()
        del school["lsat_50"]
        with pytest.raises(DataValidationError, match="missing required fields"):
            _validate_entry(school)

    def test_missing_field_error_includes_school_id(self):
        """Error message should include the school's id."""
        school = VALID_SCHOOL.copy()
        school["id"] = "problem-school"
        del school["name"]
        with pytest.raises(DataValidationError, match="problem-school"):
            _validate_entry(school)

    def test_wrong_type_numeric_field(self):
        """Numeric field with wrong type should raise."""
        school = VALID_SCHOOL.copy()
        school["lsat_50"] = "160"  # Should be int or float
        with pytest.raises(DataValidationError, match="field 'lsat_50'"):
            _validate_entry(school)

    def test_wrong_type_string_field(self):
        """String field with wrong type should raise."""
        school = VALID_SCHOOL.copy()
        school["name"] = 123  # Should be str
        with pytest.raises(DataValidationError, match="field 'name'"):
            _validate_entry(school)

    def test_wrong_type_list_field(self):
        """List field with wrong type should raise."""
        school = VALID_SCHOOL.copy()
        school["practice_area_strengths"] = "corporate"  # Should be list
        with pytest.raises(DataValidationError, match="field 'practice_area_strengths'"):
            _validate_entry(school)

    def test_accepts_float_for_numeric_fields(self):
        """Numeric fields should accept both int and float."""
        school = VALID_SCHOOL.copy()
        school["lsat_50"] = 160.5  # float instead of int
        school["annual_tuition"] = 50000.0
        _validate_entry(school)  # Should not raise


class TestLoadLawSchools:
    """Test the load_law_schools function."""

    def test_happy_path(self, tmp_path):
        """Valid data should load successfully."""
        # Create a temporary JSON file
        data = {"schools": [VALID_SCHOOL]}
        json_file = tmp_path / "law_schools.json"
        json_file.write_text(json.dumps(data))

        # Mock _get_data_path to return our temp file
        import law.data_loader as dl
        original_get_data_path = dl._get_data_path
        dl._get_data_path = lambda: json_file

        try:
            schools = load_law_schools()
            assert len(schools) == 1
            assert schools[0]["id"] == "test-law"
            assert schools[0]["name"] == "Test Law School"
        finally:
            dl._get_data_path = original_get_data_path

    def test_invalid_json(self, tmp_path):
        """Invalid JSON should raise json.JSONDecodeError."""
        json_file = tmp_path / "law_schools.json"
        json_file.write_text("{invalid json")

        import law.data_loader as dl
        original_get_data_path = dl._get_data_path
        dl._get_data_path = lambda: json_file

        try:
            with pytest.raises(json.JSONDecodeError):
                load_law_schools()
        finally:
            dl._get_data_path = original_get_data_path

    def test_missing_file(self, tmp_path):
        """Missing data file should raise FileNotFoundError."""
        json_file = tmp_path / "missing.json"

        import law.data_loader as dl
        original_get_data_path = dl._get_data_path
        dl._get_data_path = lambda: json_file

        try:
            with pytest.raises(FileNotFoundError):
                load_law_schools()
        finally:
            dl._get_data_path = original_get_data_path

    def test_missing_schools_key(self, tmp_path):
        """JSON missing 'schools' key should raise DataValidationError."""
        json_file = tmp_path / "law_schools.json"
        json_file.write_text(json.dumps({"data": []}))

        import law.data_loader as dl
        original_get_data_path = dl._get_data_path
        dl._get_data_path = lambda: json_file

        try:
            with pytest.raises(DataValidationError, match="missing 'schools' key"):
                load_law_schools()
        finally:
            dl._get_data_path = original_get_data_path

    def test_schools_not_list(self, tmp_path):
        """'schools' value that's not a list should raise DataValidationError."""
        json_file = tmp_path / "law_schools.json"
        json_file.write_text(json.dumps({"schools": "not a list"}))

        import law.data_loader as dl
        original_get_data_path = dl._get_data_path
        dl._get_data_path = lambda: json_file

        try:
            with pytest.raises(DataValidationError, match="'schools' must be a list"):
                load_law_schools()
        finally:
            dl._get_data_path = original_get_data_path

    def test_invalid_school_entry(self, tmp_path):
        """Invalid school entry should raise DataValidationError."""
        invalid_school = VALID_SCHOOL.copy()
        del invalid_school["lsat_50"]

        json_file = tmp_path / "law_schools.json"
        json_file.write_text(json.dumps({"schools": [invalid_school]}))

        import law.data_loader as dl
        original_get_data_path = dl._get_data_path
        dl._get_data_path = lambda: json_file

        try:
            with pytest.raises(DataValidationError, match="missing required fields"):
                load_law_schools()
        finally:
            dl._get_data_path = original_get_data_path

    def test_multiple_schools(self, tmp_path):
        """Multiple valid schools should all load."""
        school1 = VALID_SCHOOL.copy()
        school1["id"] = "school-1"

        school2 = VALID_SCHOOL.copy()
        school2["id"] = "school-2"

        data = {"schools": [school1, school2]}
        json_file = tmp_path / "law_schools.json"
        json_file.write_text(json.dumps(data))

        import law.data_loader as dl
        original_get_data_path = dl._get_data_path
        dl._get_data_path = lambda: json_file

        try:
            schools = load_law_schools()
            assert len(schools) == 2
            assert schools[0]["id"] == "school-1"
            assert schools[1]["id"] == "school-2"
        finally:
            dl._get_data_path = original_get_data_path

    def test_actual_data_file_loads(self):
        """The actual law_schools.json file should load successfully."""
        schools = load_law_schools()
        assert len(schools) > 0
        assert all(isinstance(s, dict) for s in schools)
        assert all("id" in s for s in schools)


class TestIntegration:
    """Integration tests."""

    def test_data_path_exists(self):
        """The data path should point to an existing file."""
        path = _get_data_path()
        assert path.exists(), f"Expected {path} to exist"

    def test_real_data_is_valid(self):
        """The real law_schools.json file should pass validation."""
        schools = load_law_schools()
        assert len(schools) >= 50, "Expected at least 50 schools"
        # Check a few T14 schools are present
        school_ids = {s["id"] for s in schools}
        assert "harvard-law" in school_ids
        assert "yale-law" in school_ids
        assert "stanford-law" in school_ids

    def test_quality_fields_populated_and_in_range(self):
        """ABA quality signals (attrition / faculty / curricular) should cover
        nearly all schools and sit in sane ranges."""
        schools = load_law_schools()
        attr = [s["attrition_1l_pct"] for s in schools if s.get("attrition_1l_pct") is not None]
        assert len(attr) >= 190
        assert all(0 <= a <= 0.5 for a in attr)
        ratios = [s["student_faculty_ratio"] for s in schools if s.get("student_faculty_ratio") is not None]
        assert len(ratios) >= 190
        assert all(2 <= r <= 50 for r in ratios)
        hands = [s["hands_on_per_student"] for s in schools if s.get("hands_on_per_student") is not None]
        assert len(hands) >= 190
        assert all(0 <= h <= 10 for h in hands)

    def test_scorecard_fields_populated_and_in_range(self):
        """College Scorecard JD debt/earnings should cover most schools (some
        are privacy-suppressed or too new) and sit in sane dollar ranges."""
        schools = load_law_schools()
        debt = [s["scorecard_median_debt"] for s in schools
                if s.get("scorecard_median_debt") is not None]
        assert len(debt) >= 150
        assert all(20_000 <= v <= 350_000 for v in debt)
        earn = [s["scorecard_earn_4yr"] for s in schools
                if s.get("scorecard_earn_4yr") is not None]
        assert len(earn) >= 150
        assert all(25_000 <= v <= 400_000 for v in earn)

    def test_placement_states_valid_when_present(self):
        """When placement_states is populated, all entries must be valid."""
        schools = load_law_schools()
        with_placement = [s for s in schools if s.get("placement_states") is not None]
        # If data has been merged, validate it; otherwise just confirm no exceptions
        for school in with_placement:
            ps = school["placement_states"]
            assert isinstance(ps, list)
            assert 1 <= len(ps) <= 3
            for entry in ps:
                assert isinstance(entry, dict)
                assert isinstance(entry.get("state"), str)
                assert len(entry["state"]) == 2
                pct = entry.get("pct")
                assert isinstance(pct, (int, float))
                assert 0 <= pct <= 100
            py = school.get("placement_year")
            assert py is not None
            assert isinstance(py, int)
            assert 2020 <= py <= 2030


class TestPlacementStatesValidation:
    """Unit tests for placement_states field validation in _validate_entry."""

    def test_valid_placement_states_passes(self):
        school = VALID_SCHOOL.copy()
        school["placement_states"] = [
            {"state": "NY", "pct": 62.1},
            {"state": "NJ", "pct": 9.0},
            {"state": "CT", "pct": 5.0},
        ]
        school["placement_year"] = 2024
        _validate_entry(school)  # should not raise

    def test_placement_states_none_passes(self):
        school = VALID_SCHOOL.copy()
        school["placement_states"] = None
        school["placement_year"] = None
        _validate_entry(school)  # should not raise

    def test_placement_states_too_many_entries(self):
        school = VALID_SCHOOL.copy()
        school["placement_states"] = [
            {"state": "NY", "pct": 40.0},
            {"state": "NJ", "pct": 20.0},
            {"state": "CT", "pct": 10.0},
            {"state": "CA", "pct": 5.0},  # 4th entry — too many
        ]
        with pytest.raises(DataValidationError, match="max 3"):
            _validate_entry(school)

    def test_placement_states_invalid_state_code(self):
        school = VALID_SCHOOL.copy()
        school["placement_states"] = [{"state": "XX", "pct": 50.0}]
        with pytest.raises(DataValidationError, match="valid 2-letter"):
            _validate_entry(school)

    def test_placement_states_pct_out_of_range(self):
        school = VALID_SCHOOL.copy()
        school["placement_states"] = [{"state": "NY", "pct": 150.0}]
        with pytest.raises(DataValidationError, match="0, 100"):
            _validate_entry(school)

    def test_placement_states_not_a_list(self):
        school = VALID_SCHOOL.copy()
        school["placement_states"] = {"state": "NY", "pct": 50.0}
        with pytest.raises(DataValidationError):
            _validate_entry(school)
