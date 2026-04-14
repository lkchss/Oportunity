"""
Law school matching and ranking algorithm.

Deterministic, explainable scoring based on:
- Admissibility (LSAT/GPA fit)
- Goal fit (employment outcomes alignment)
- Practice area fit (interest overlap)
- Scholarship likelihood
- Geographic preference
"""

import math
from typing import Optional


def _sigmoid(x: float, midpoint: float = 0, scale: float = 1) -> float:
    """
    Sigmoid function for smooth scoring curves.

    Args:
        x: Input value
        midpoint: Center of curve (default 0)
        scale: Steepness of curve (default 1)

    Returns:
        Value between 0 and 1
    """
    try:
        return 1 / (1 + math.exp(-scale * (x - midpoint)))
    except OverflowError:
        return 1.0 if x > midpoint else 0.0


def _compute_admissibility_score(
    lsat: Optional[int],
    gpa: float,
    school: dict,
) -> tuple[float, str]:
    """
    Compute admissibility score and tier based on LSAT/GPA vs. school medians.

    Uses sigmoid curves centered on school medians:
    - High LSAT/GPA → score near 100 (safety)
    - Median LSAT/GPA → score around 50 (target)
    - Low LSAT/GPA → score near 0 (hard reach)

    Tier assignment:
    - Safety: both metrics at/above 75th percentile
    - Target: both metrics at/above median
    - Reach: both metrics at/above 25th percentile
    - Hard Reach: below 25th percentile on either

    Args:
        lsat: User's LSAT score (or None if not taken)
        gpa: User's GPA
        school: School data dict with lsat_25/50/75, gpa_25/50/75

    Returns:
        (admissibility_score, tier_label) tuple
    """
    # If no LSAT, lower admissibility significantly
    if lsat is None:
        lsat_score = 30
        lsat_factor = 0.7  # Weight LSAT as 70% if missing
    else:
        # Sigmoid centered on median, steeper slope
        lsat_score = _sigmoid(lsat, midpoint=school["lsat_50"], scale=0.15) * 100
        lsat_factor = 1.0

    # GPA scoring
    gpa_score = _sigmoid(gpa, midpoint=school["gpa_50"], scale=2.0) * 100

    # Weighted average
    composite = (lsat_score * lsat_factor + gpa_score) / (lsat_factor + 1)

    # Determine tier
    lsat_ok = lsat is not None and lsat >= school["lsat_50"]
    gpa_ok = gpa >= school["gpa_50"]
    lsat_strong = lsat is not None and lsat >= school["lsat_75"]
    gpa_strong = gpa >= school["gpa_75"]
    lsat_weak = lsat is None or lsat < school["lsat_25"]
    gpa_weak = gpa < school["gpa_25"]

    if lsat_strong and gpa_strong:
        tier = "safety"
    elif lsat_ok and gpa_ok:
        tier = "target"
    elif (lsat is not None and lsat >= school["lsat_25"]) and gpa >= school["gpa_25"]:
        tier = "reach"
    else:
        tier = "hard reach"

    return composite, tier


def _compute_goal_fit_score(profile: dict, school: dict) -> float:
    """
    Compute goal fit score based on primary career goal.

    Maps user's primary goal to relevant employment outcome percentages:
    - BigLaw → biglaw_pct
    - Federal Clerkship → federal_clerkship_pct
    - Public Interest → public_interest_pct
    - Government → government_pct
    - Unsure → balanced average of all outcomes

    Args:
        profile: User profile dict with 'goal' field
        school: School data dict with employment outcome percentages

    Returns:
        Score 0-100
    """
    goal = profile.get("goal", "Unsure").lower()

    if "biglaw" in goal:
        return school.get("biglaw_pct", 0) * 100
    elif "clerkship" in goal:
        return school.get("federal_clerkship_pct", 0) * 100
    elif "interest" in goal:  # public interest
        return school.get("public_interest_pct", 0) * 100
    elif "government" in goal:
        return school.get("government_pct", 0) * 100
    else:  # Unsure or other: balanced average
        outcomes = [
            school.get("biglaw_pct", 0),
            school.get("federal_clerkship_pct", 0),
            school.get("public_interest_pct", 0),
            school.get("government_pct", 0),
        ]
        return (sum(outcomes) / len(outcomes)) * 100


def _compute_practice_area_fit(profile: dict, school: dict) -> float:
    """
    Compute practice area fit based on overlap between user interests and school strengths.

    Calculates: (# matching areas / # user interests) * 100
    Returns 100 if user has no stated interests (neutral).

    Args:
        profile: User profile dict with 'practice_areas' field (list)
        school: School data dict with 'practice_area_strengths' field (list)

    Returns:
        Score 0-100
    """
    user_areas = [area.lower() for area in profile.get("practice_areas", [])]
    school_areas = [area.lower() for area in school.get("practice_area_strengths", [])]

    if not user_areas:
        return 100  # Neutral if no preferences stated

    matches = sum(1 for area in user_areas if area in school_areas)
    return (matches / len(user_areas)) * 100


def _compute_scholarship_likelihood(profile: dict, school: dict, lsat: Optional[int], gpa: float) -> float:
    """
    Compute scholarship likelihood based on profile fit and school generosity.

    Logic:
    - Splitter (high LSAT, low GPA): high merit aid likelihood (75+ threshold)
    - Reverse splitter (high GPA, low LSAT): moderate merit aid likelihood
    - Otherwise: based on school's scholarship_pct and percentile fit
    - Consider median_scholarship as indicator of school's generosity

    Args:
        profile: User profile dict
        school: School data dict with scholarship_pct, median_scholarship, LSAT/GPA percentiles
        lsat: User's LSAT score (or None)
        gpa: User's GPA

    Returns:
        Score 0-100
    """
    if lsat is None:
        lsat = 160  # Default conservative estimate

    # Percentile calculation (rough)
    lsat_vs_75 = lsat - school["lsat_75"]  # Positive = above 75th
    gpa_vs_25 = gpa - school["gpa_25"]  # Positive = above 25th

    # Splitter: high LSAT, low GPA → schools offer merit aid for LSAT boost
    if lsat_vs_75 > 5 and gpa_vs_25 < 0.5:
        splitter_boost = 85
    # Reverse splitter: high GPA, low LSAT → more modest boost
    elif gpa - school["gpa_75"] > 0.5 and lsat < school["lsat_50"]:
        splitter_boost = 60
    else:
        splitter_boost = 50

    # Base on school's scholarship percentage and median
    school_generosity = school.get("scholarship_pct", 0.75) * 100
    median_scholarship_bonus = min(school.get("median_scholarship", 20000) / 50000, 1.0) * 10

    # Percentile fit bonus
    lsat_percentile = min(max((lsat - school["lsat_25"]) / (school["lsat_75"] - school["lsat_25"]) * 100, 0), 100)
    gpa_percentile = min(max((gpa - school["gpa_25"]) / (school["gpa_75"] - school["gpa_25"]) * 100, 0), 100)
    percentile_fit = (lsat_percentile + gpa_percentile) / 2 * 0.3

    scholarship_score = (splitter_boost * 0.4 + school_generosity * 0.3 + percentile_fit + median_scholarship_bonus)
    return min(scholarship_score, 100)


def _compute_geographic_fit(profile: dict, school: dict) -> float:
    """
    Compute geographic fit score.

    Returns 100 if user has no geographic preferences (flexible).
    Returns 100 if school is in a preferred region.
    Returns 50 if school is outside preferences but not explicitly excluded.

    Args:
        profile: User profile dict with 'geography' field (list of regions)
        school: School data dict with 'location' field (city, state)

    Returns:
        Score 0-100
    """
    user_regions = [r.lower() for r in profile.get("geography", [])]

    if not user_regions or "Anywhere" in profile.get("geography", []):
        return 100  # Flexible

    location = school.get("location", "").lower()
    school_state = location.split(",")[-1].strip().lower() if "," in location else ""

    # Map regions to states
    region_map = {
        "northeast": ["ma", "ct", "ny", "nj", "pa", "vt", "nh", "me", "ri"],
        "southeast": ["nc", "sc", "va", "ga", "fl", "al", "tn", "tx"],
        "midwest": ["oh", "il", "mi", "in", "wi", "mn", "ia", "mo"],
        "southwest": ["tx", "az", "nm"],
        "west coast": ["ca", "wa", "or"],
    }

    matched_region = False
    for region in user_regions:
        states = region_map.get(region, [])
        if school_state in states:
            matched_region = True
            break

    return 100 if matched_region else 50


def _apply_filters(schools_with_scores: list[dict], profile: dict) -> list[dict]:
    """
    Apply user preference filters to remove schools that don't meet criteria.

    Filters:
    - Reach preference: "Only schools where I'm a strong candidate" → remove reaches
    - Scholarship: "Must have significant scholarship" → remove low scholarship likelihood

    Args:
        schools_with_scores: List of school dicts with computed scores
        profile: User profile dict with reach preference and scholarship importance

    Returns:
        Filtered list of schools
    """
    filtered = schools_with_scores

    # Reach filter
    reach_pref = profile.get("reach_preference", "Want a balanced list")
    if "Only schools where I'm a strong candidate" in reach_pref:
        # Remove reach and hard reach tiers
        filtered = [s for s in filtered if s["admissibility_tier"] in ["safety", "target"]]

    # Scholarship filter
    scholarship_pref = profile.get("scholarship", "Prefer but not required")
    if "Must have significant scholarship" in scholarship_pref:
        # Remove schools with low scholarship likelihood
        filtered = [s for s in filtered if s["scholarship_likelihood_score"] >= 50]

    return filtered


def rank_schools(
    profile: dict,
    schools: list[dict],
    top_n: int = 20,
) -> list[dict]:
    """
    Rank law schools based on user profile and return top N matches.

    Scoring logic:

    1. **Admissibility (30%)**: LSAT/GPA fit using sigmoid curves
       - Compares user stats to school medians and percentiles
       - Assigns tier: safety, target, reach, hard reach

    2. **Goal Fit (30%)**: Employment outcome alignment
       - Matches primary career goal to relevant outcome percentage
       - E.g., BigLaw goal → weighted by school's biglaw_pct

    3. **Practice Area Fit (20%)**: Interest-strength overlap
       - Counts matching practice areas between user interests and school strengths

    4. **Scholarship Likelihood (10%)**: Merit aid probability
       - Splitters (high LSAT, low GPA) score highly
       - Based on school's scholarship percentage and median

    5. **Geographic Fit (10%)**: Location preference alignment
       - 100 if in preferred region, 50 if flexible, 0 if excluded

    **Composite Score**: Weighted average of above (default weights shown)

    **Filtering**:
    - Respects "Only strong candidates" preference (removes reaches)
    - Respects "Must have scholarship" preference

    Args:
        profile: User profile dict with:
            - lsat (int or None)
            - gpa (float)
            - goal (str)
            - practice_areas (list[str])
            - geography (list[str])
            - reach_preference (str)
            - scholarship (str)
        schools: List of school dicts (from data_loader)
        top_n: Number of top schools to return (default 20)

    Returns:
        List of top N schools sorted by composite score (desc), each with:
            - All original school fields
            - admissibility_score (0-100)
            - admissibility_tier (safety/target/reach/hard reach)
            - goal_fit_score (0-100)
            - practice_area_fit_score (0-100)
            - scholarship_likelihood_score (0-100)
            - geographic_fit_score (0-100)
            - composite_score (0-100)

    Raises:
        ValueError: If profile or schools data is invalid
    """
    # Validate inputs
    if not profile:
        raise ValueError("profile cannot be empty")
    if not schools:
        raise ValueError("schools cannot be empty")
    if top_n < 1:
        raise ValueError("top_n must be at least 1")

    lsat = profile.get("lsat")
    gpa = profile.get("gpa", 0)

    if gpa == 0 or gpa is None:
        raise ValueError("profile must include a valid GPA")

    # Score each school
    scored_schools = []
    for school in schools:
        # Compute component scores
        admissibility_score, tier = _compute_admissibility_score(lsat, gpa, school)
        goal_fit_score = _compute_goal_fit_score(profile, school)
        practice_area_score = _compute_practice_area_fit(profile, school)
        scholarship_score = _compute_scholarship_likelihood(profile, school, lsat, gpa)
        geographic_score = _compute_geographic_fit(profile, school)

        # Composite score (default weights)
        composite_score = (
            admissibility_score * 0.30
            + goal_fit_score * 0.30
            + practice_area_score * 0.20
            + scholarship_score * 0.10
            + geographic_score * 0.10
        )

        # Augment school with scores
        school_with_scores = school.copy()
        school_with_scores["admissibility_score"] = round(admissibility_score, 1)
        school_with_scores["admissibility_tier"] = tier
        school_with_scores["goal_fit_score"] = round(goal_fit_score, 1)
        school_with_scores["practice_area_fit_score"] = round(practice_area_score, 1)
        school_with_scores["scholarship_likelihood_score"] = round(scholarship_score, 1)
        school_with_scores["geographic_fit_score"] = round(geographic_score, 1)
        school_with_scores["composite_score"] = round(composite_score, 1)

        scored_schools.append(school_with_scores)

    # Apply user preference filters
    filtered_schools = _apply_filters(scored_schools, profile)

    # Sort by composite score descending
    filtered_schools.sort(key=lambda s: s["composite_score"], reverse=True)

    # Return top N
    return filtered_schools[:top_n]
