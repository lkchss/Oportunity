"""
Fixed, deterministic suite of synthetic applicants for the optimization eval.

Stratified across the input space the algorithm actually keys on:
  stats tier (LSAT/GPA) x career goal x target state x in-state x income x sliders.

The suite is intentionally hand-built (not random) so it is stable across runs and
git revisions — the eval compares algorithm versions, so the profiles must not move.
Scale by adding archetypes; the diff-only judging keeps cost flat regardless of size.
"""

from typing import Optional


def _p(
    pid: str,
    lsat: Optional[int],
    gpa: float,
    goal: str,
    target_state: str,
    instate_states: list[str],
    income_bracket: str,
    scholarship: int = 5,
    career_weight: int = 5,
    location_weight: int = 5,
) -> dict:
    return {
        "id": pid,
        "lsat": lsat,
        "gpa": gpa,
        "goal": goal,
        "target_state": target_state,
        "instate_states": instate_states,
        "income_bracket": income_bracket,
        "scholarship": scholarship,
        "career_weight": career_weight,
        "location_weight": location_weight,
    }


# Each archetype is a realistic applicant. Comment = the human story the judge
# should be able to reconstruct from the fields alone.
_PROFILES: list[dict] = [
    # --- median applicants, varied goals/geo ---
    _p("p01", 163, 3.75, "BigLaw",            "NY", [],     "65k_130k"),
    _p("p02", 165, 3.80, "BigLaw",            "CA", ["CA"], "130k_200k", location_weight=8),
    _p("p03", 161, 3.65, "Public Interest",   "NY", ["NY"], "under_65k", scholarship=9),
    _p("p04", 159, 3.55, "Government",        "DC", [],     "65k_130k"),
    _p("p05", 167, 3.85, "Federal Clerkship", "",   [],     "over_200k", career_weight=9),

    # --- strong applicants ---
    _p("p06", 172, 3.90, "BigLaw",            "NY", [],     "over_200k"),
    _p("p07", 170, 3.88, "Federal Clerkship", "IL", ["IL"], "130k_200k"),
    _p("p08", 174, 3.95, "Academia",          "",   [],     "prefer_not", career_weight=10),

    # --- weak / regional applicants ---
    _p("p09", 156, 3.40, "Solo/Small Firm",   "TX", ["TX"], "under_65k", scholarship=10, location_weight=9),
    _p("p10", 154, 3.30, "Government",        "OH", ["OH"], "65k_130k"),
    _p("p11", 158, 3.50, "Public Interest",   "CA", ["CA"], "under_65k", scholarship=8),

    # --- splitters (algo has explicit splitter logic) ---
    _p("p12", 172, 3.25, "BigLaw",            "TX", ["TX"], "65k_130k", scholarship=9),   # high LSAT, low GPA
    _p("p13", 158, 3.96, "BigLaw",            "NY", [],     "130k_200k"),                  # reverse splitter

    # --- no-LSAT path ---
    _p("p14", None, 3.85, "Unsure",           "MA", ["MA"], "65k_130k"),
    _p("p15", None, 3.60, "Government",       "WA", ["WA"], "under_65k", scholarship=9),

    # --- cost-sensitive, in-state public-school seekers ---
    _p("p16", 162, 3.70, "Government",        "MI", ["MI"], "under_65k", scholarship=10, location_weight=8),
    _p("p17", 160, 3.60, "Solo/Small Firm",   "WI", ["WI"], "65k_130k",  scholarship=9),

    # --- unsure / undirected ---
    _p("p18", 166, 3.78, "Unsure",            "",   [],     "prefer_not"),
    _p("p19", 168, 3.82, "In-house",          "CA", ["CA"], "130k_200k"),

    # --- T14-chasing high performers, geo-flexible ---
    _p("p20", 175, 3.92, "BigLaw",            "",   [],     "over_200k", career_weight=8),
    _p("p21", 169, 3.72, "Federal Clerkship", "VA", ["VA"], "65k_130k"),

    # --- max-aid / scholarship-driven ---
    _p("p22", 164, 3.55, "BigLaw",            "",   [],     "under_65k", scholarship=10),
    _p("p23", 160, 3.45, "Public Interest",   "MN", ["MN"], "under_65k", scholarship=10, location_weight=7),

    # --- location-anchored ---
    _p("p24", 163, 3.68, "BigLaw",            "GA", ["GA"], "65k_130k",  location_weight=10),
]


def build_profiles() -> list[dict]:
    """Return the fixed evaluation suite (deterministic, order-stable)."""
    return [dict(p) for p in _PROFILES]


def profile_summary(p: dict) -> str:
    """One-line human description of an applicant, for judge prompts."""
    lsat = p["lsat"] if p["lsat"] is not None else "no-LSAT"
    instate = ",".join(p["instate_states"]) or "none"
    target = p["target_state"] or "no preference"
    return (
        f"LSAT {lsat} / GPA {p['gpa']:.2f} | goal: {p['goal']} | "
        f"target state: {target} | in-state: {instate} | "
        f"income: {p['income_bracket']} | "
        f"sliders[scholarship={p['scholarship']}, career={p['career_weight']}, "
        f"location={p['location_weight']}]"
    )
