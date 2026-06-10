import json
from pathlib import Path
from typing import Optional


# Schema definition for law school entries
REQUIRED_FIELDS = {
    # Basic info
    "id": str,
    "name": str,
    "location": str,
    "state": str,
    "website_url": str,
    "usnwr_rank_2026": (int, float),
    "is_public": bool,
    # ABA 509 admissions data
    "lsat_25": (int, float),
    "lsat_50": (int, float),
    "lsat_75": (int, float),
    "gpa_25": (int, float),
    "gpa_50": (int, float),
    "gpa_75": (int, float),
    "acceptance_rate": (int, float),
    "scholarship_pct": (int, float),
    "median_scholarship": (int, float),
    # NALP / ABA employment data
    "biglaw_pct": (int, float),
    "federal_clerkship_pct": (int, float),
    "government_pct": (int, float),
    "public_interest_pct": (int, float),
    "solo_small_firm_pct": (int, float),
    "jd_required_pct": (int, float),
    "bar_pass_rate_first_time": (int, float),
    # NALP salary data
    "median_private_sector_salary": (int, float),
    "median_public_sector_salary": (int, float),
    # Programmatic strengths
    "practice_area_strengths": list,
    "lrap_quality": str,
    "target_states": list,
    # Cost
    "annual_tuition": (int, float),
    "annual_tuition_resident": (int, float),
    "annual_tuition_nonresident": (int, float),
    "cost_of_living_index": (int, float),
}


# Enrichment fields (ABA 509 + Employment Summary). Optional during rollout:
# validated only when present, so schools can be populated in batches without
# breaking the loader. Promote to REQUIRED_FIELDS once all 75 are populated.
OPTIONAL_FIELDS = {
    "class_size_1l": (int, float),
    "scholarship_full_pct": (int, float),
    "scholarship_half_to_full_pct": (int, float),
    "scholarship_less_than_half_pct": (int, float),
    "no_scholarship_pct": (int, float),
    "conditional_scholarship": bool,
    "conditional_reduction_rate": (int, float),  # share of conditional awards later cut (ABA)
    "employed_10mo_pct": (int, float),
    "school_funded_pct": (int, float),
    # Transfer mobility (ABA 2025 Transfers report) — for "transfer up after 1L" use case
    "transfers_in": (int, float),
    "transfers_out": (int, float),
    # Bar passage (ABA 2026 First-Time + Two-Year Ultimate reports), fractions 0-1
    "bar_pass_state_avg": (int, float),
    "bar_pass_vs_state": (int, float),   # school first-time minus state avg (signed)
    "bar_pass_ultimate": (int, float),
    # Quality signals (ABA Attrition / Faculty Resources / Curricular Offerings),
    # display-only — never scored
    "attrition_1l_pct": (int, float),
    "faculty_ft_total": (int, float),
    "student_faculty_ratio": (int, float),
    "clinic_seats_filled": (int, float),
    "field_placements_filled": (int, float),
    "simulation_seats_filled": (int, float),
    "hands_on_per_student": (int, float),
    # College Scorecard JD-program outcomes (real graduates, federal data),
    # display-only — never scored
    "scorecard_median_debt": (int, float),
    "scorecard_debt_monthly": (int, float),
    "scorecard_earn_1yr": (int, float),
    "scorecard_earn_4yr": (int, float),
}


class DataValidationError(Exception):
    """Raised when law school data fails validation."""
    pass


def _get_data_path() -> Path:
    """Get the path to law_schools.json relative to this module."""
    return Path(__file__).parent / "data" / "law_schools.json"


def _validate_entry(entry: dict) -> None:
    """
    Validate a single law school entry has all required fields and correct types.

    Args:
        entry: The law school entry to validate

    Raises:
        DataValidationError: If validation fails
    """
    school_id = entry.get("id", "<unknown>")

    # Check all required fields are present
    missing_fields = [field for field in REQUIRED_FIELDS if field not in entry]
    if missing_fields:
        raise DataValidationError(
            f"School '{school_id}': missing required fields: {', '.join(missing_fields)}"
        )

    # Validate each field type
    for field, expected_type in REQUIRED_FIELDS.items():
        value = entry[field]

        if isinstance(expected_type, tuple):
            # Allow multiple types (e.g., int or float)
            if not isinstance(value, expected_type):
                raise DataValidationError(
                    f"School '{school_id}': field '{field}' has type {type(value).__name__}, "
                    f"expected {' or '.join(t.__name__ for t in expected_type)}"
                )
        else:
            # Single type check
            if not isinstance(value, expected_type):
                raise DataValidationError(
                    f"School '{school_id}': field '{field}' has type {type(value).__name__}, "
                    f"expected {expected_type.__name__}"
                )

    # Validate optional enrichment fields only if present (None allowed = unverified)
    for field, expected_type in OPTIONAL_FIELDS.items():
        if field not in entry or entry[field] is None:
            continue
        value = entry[field]
        types = expected_type if isinstance(expected_type, tuple) else (expected_type,)
        # bool is a subclass of int — guard so a bool field can't be a stray int
        if expected_type is bool and not isinstance(value, bool):
            raise DataValidationError(
                f"School '{school_id}': field '{field}' must be bool, got {type(value).__name__}"
            )
        if not isinstance(value, types):
            raise DataValidationError(
                f"School '{school_id}': field '{field}' has type {type(value).__name__}, "
                f"expected {' or '.join(t.__name__ for t in types)}"
            )


def load_law_schools() -> list[dict]:
    """
    Load and validate law schools from law_schools.json.

    Returns:
        List of validated law school dictionaries

    Raises:
        DataValidationError: If any entry fails validation
        FileNotFoundError: If the data file doesn't exist
        json.JSONDecodeError: If the JSON is malformed
    """
    data_path = _get_data_path()

    if not data_path.exists():
        raise FileNotFoundError(f"Law schools data file not found at {data_path}")

    # Load JSON
    try:
        with open(data_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise json.JSONDecodeError(
            f"Invalid JSON in {data_path}: {e.msg}",
            e.doc,
            e.pos,
        )

    # Extract schools list
    if "schools" not in data:
        raise DataValidationError("Data file missing 'schools' key")

    schools = data["schools"]
    if not isinstance(schools, list):
        raise DataValidationError("'schools' must be a list")

    # Validate each school
    for school in schools:
        if not isinstance(school, dict):
            raise DataValidationError("Each school entry must be a dictionary")
        _validate_entry(school)

    return schools
