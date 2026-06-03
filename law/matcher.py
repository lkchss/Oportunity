"""
Law school matching algorithm — v3.

Produces six independent, transparent scores per school:
  1. Admissibility  — LSAT/GPA fit vs school percentiles → tier label
  2. Prestige       — USNWR rank-based institutional standing
  3. Career Fit     — employment outcome alignment with target career
  4. Location Fit   — placement strength in user's target state
  5. Scholarship    — merit likelihood + need-based aid signal
  6. Financial      — net debt vs expected starting salary

All scores are 0–100. Composite rank = weighted average of the six.
"""

import math
from typing import Optional


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sigmoid(x: float, midpoint: float = 0, scale: float = 1) -> float:
    try:
        return 1 / (1 + math.exp(-scale * (x - midpoint)))
    except OverflowError:
        return 1.0 if x > midpoint else 0.0


def _clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, value))


# ---------------------------------------------------------------------------
# 1. Admissibility
# ---------------------------------------------------------------------------

def _compute_admissibility(
    lsat: Optional[int],
    gpa: float,
    school: dict,
) -> tuple[float, str]:
    """
    Score LSAT/GPA fit against school percentiles.

    Returns (score 0-100, tier label).
    LSAT weighted 70%, GPA 30% (mirrors law school median-protection priorities).
    """
    # No-LSAT path: GPA-only, capped at target
    if lsat is None:
        if gpa >= school["gpa_75"]:
            return 65.0, "target"
        elif gpa >= school["gpa_50"]:
            return 50.0, "target"
        elif gpa >= school["gpa_25"]:
            return 35.0, "reach"
        else:
            return 15.0, "hard reach"

    def _percentile_score(value, p25, p50, p75, floor=120):
        if value >= p75:
            overage = (value - p75) / max(p75 - p50, 1)
            return min(85 + overage * 15, 100)
        elif value >= p50:
            progress = (value - p50) / max(p75 - p50, 1)
            return 60 + progress * 25
        elif value >= p25:
            progress = (value - p25) / max(p50 - p25, 1)
            return 40 + progress * 20
        elif value < p25 - 10:
            return 0.0
        else:
            deficit = (p25 - value) / max(p25 - floor, 1)
            return max(40 - deficit * 40, 0)

    lsat_score = _percentile_score(
        lsat,
        school["lsat_25"], school["lsat_50"], school["lsat_75"],
    )
    gpa_score = _percentile_score(
        gpa,
        school["gpa_25"], school["gpa_50"], school["gpa_75"],
        floor=2.0,
    )
    composite = lsat_score * 0.70 + gpa_score * 0.30

    # Tier: both axes must be healthy (schools protect both medians)
    at_75_lsat = lsat >= school["lsat_75"]
    at_50_lsat = lsat >= school["lsat_50"]
    at_25_lsat = lsat >= school["lsat_25"]
    at_75_gpa  = gpa  >= school["gpa_75"]
    at_50_gpa  = gpa  >= school["gpa_50"]
    at_25_gpa  = gpa  >= school["gpa_25"]

    if at_75_lsat and at_50_gpa:
        tier = "safety"
    elif at_50_lsat and at_50_gpa:
        tier = "target"
    elif (at_50_lsat and at_25_gpa) or (at_25_lsat and at_50_gpa):
        tier = "target"
    elif at_25_lsat and at_25_gpa:
        tier = "reach"
    elif at_75_lsat or at_75_gpa:
        tier = "reach"   # extreme splitter — one axis strong, other weak
    elif at_50_lsat or at_50_gpa:
        tier = "reach"
    else:
        tier = "hard reach"

    return _clamp(composite), tier


# ---------------------------------------------------------------------------
# 2. Career Fit
# ---------------------------------------------------------------------------

_GOAL_FIELDS = {
    "biglaw":        ["biglaw_pct"],
    "federal clerkship": ["federal_clerkship_pct"],
    "government":    ["government_pct"],
    "public interest": ["public_interest_pct"],
    "solo/small firm": ["solo_small_firm_pct"],
    "in-house":      ["biglaw_pct"],        # BigLaw is primary pipeline
    "academia":      ["federal_clerkship_pct", "biglaw_pct"],  # prestige proxies
    "unsure":        ["biglaw_pct", "federal_clerkship_pct", "government_pct",
                      "public_interest_pct", "solo_small_firm_pct"],
}

_GOAL_WEIGHTS = {
    "academia": [0.60, 0.40],
    "unsure":   [0.25, 0.20, 0.20, 0.20, 0.15],
}

_LRAP_MULTIPLIERS = {"excellent": 1.25, "strong": 1.10, "moderate": 1.00, "weak": 0.85}


def _precompute_career_scalars(schools: list[dict]) -> dict:
    """Max value across all schools per outcome field, for normalization."""
    fields = {
        "biglaw_pct", "federal_clerkship_pct", "government_pct",
        "public_interest_pct", "solo_small_firm_pct",
    }
    return {
        f: max((s.get(f, 0) for s in schools), default=1) or 1
        for f in fields
    }


def _compute_career_fit(profile: dict, school: dict, scalars: dict) -> float:
    """
    Normalize the school's outcome percentage against the best in the dataset,
    then apply goal-specific logic.
    """
    goal_key = profile.get("goal", "Unsure").lower()

    # Fuzzy-match goal key
    matched = "unsure"
    for key in _GOAL_FIELDS:
        if key in goal_key:
            matched = key
            break

    fields   = _GOAL_FIELDS[matched]
    weights  = _GOAL_WEIGHTS.get(matched, [1.0])

    # Normalize each field against dataset max
    normed = []
    for f in fields:
        raw = school.get(f, 0)
        mx  = scalars.get(f, 1) or 1
        normed.append(_clamp((raw / mx) * 100))

    # Weighted average across fields
    if len(normed) == 1:
        score = normed[0]
    else:
        w = weights[:len(normed)]
        total_w = sum(w)
        score = sum(n * (wi / total_w) for n, wi in zip(normed, w))

    # LRAP multiplier for loan-sensitive careers
    if matched in ("public interest", "government"):
        lrap = school.get("lrap_quality", "moderate").lower()
        score *= _LRAP_MULTIPLIERS.get(lrap, 1.0)

    # Real-outcome quality adjustment (ABA Employment Summary, when available).
    # employed_10mo_pct (FTLT bar-required + JD-advantage / grads) is the
    # gold-standard placement metric; school_funded_pct flags employment-stat
    # gaming (schools hiring their own grads into short-term funded roles) and is
    # netted out. Blend 70% goal-specific fit, 30% real discounted placement.
    employed = school.get("employed_10mo_pct")
    if employed is not None:
        funded = school.get("school_funded_pct") or 0.0
        real_placement = max(employed - funded, 0.0)
        score = score * 0.70 + (real_placement * 100) * 0.30

    # Bar-passage value-add (ABA 2026): a school that beats its state's first-time
    # pass rate adds outcome value beyond the students it admits; one that lags is
    # a risk. bar_pass_vs_state is school-minus-state; nudge career ±10% (capped).
    vs_state = school.get("bar_pass_vs_state")
    if vs_state is not None:
        score *= 1 + max(-0.10, min(0.10, vs_state))

    return _clamp(score)


# ---------------------------------------------------------------------------
# 2. Prestige
# ---------------------------------------------------------------------------

def _compute_prestige(school: dict) -> float:
    """
    Rank-based institutional prestige score (0-100).

    Rank 1 → 100, rank 82 → ~2. Ensures that for otherwise-equal profiles,
    higher-ranked schools sort above lower-ranked ones.
    """
    rank = school.get("usnwr_rank_2026", 100)
    return _clamp(100 - (rank - 1) * 1.2)


# ---------------------------------------------------------------------------
# 3. Location Fit
# ---------------------------------------------------------------------------

def _compute_location_fit(profile: dict, school: dict) -> float:
    """
    Score how strongly the school places graduates into the user's target state.

    Uses the school's target_states list (ordered: first = strongest placement).
    Bonus if the school is physically in the target state.
    """
    target = (profile.get("target_state") or "").strip().upper()
    if not target:
        return 50.0  # neutral if no preference stated

    school_state   = (school.get("state") or "").upper()
    target_states  = [s.upper() for s in school.get("target_states", [])]

    if not target_states:
        return 20.0

    # Position in the ordered target_states list
    try:
        position = target_states.index(target)
    except ValueError:
        position = -1

    if position == -1:
        base = 15.0  # not listed — possible but unlikely
    elif position == 0:
        base = 100.0
    elif position == 1:
        base = 85.0
    elif position <= 3:
        base = 70.0
    else:
        base = 55.0

    # Physical proximity bonus: school is in the target state
    if school_state == target and position != 0:
        base = min(base + 15.0, 100.0)

    return _clamp(base)


# ---------------------------------------------------------------------------
# 4. Scholarship
# ---------------------------------------------------------------------------

_NEED_FACTORS = {
    "under_65k":   1.00,
    "65k_130k":    0.60,
    "130k_200k":   0.20,
    "over_200k":   0.00,
    "prefer_not":  0.30,
}

_NEED_BOOST_MAX = 15.0   # max points added to scholarship score for high-need


def _grid_generosity(school: dict) -> Optional[float]:
    """Award-size-weighted generosity from the ABA 509 grid (None if absent)."""
    full = school.get("scholarship_full_pct")
    if full is None:
        return None
    htf = school.get("scholarship_half_to_full_pct") or 0.0
    lth = school.get("scholarship_less_than_half_pct") or 0.0
    return full * 1.0 + htf * 0.7 + lth * 0.3


def _precompute_scholarship_scalar(schools: list[dict]) -> float:
    """Max grid generosity across the dataset, for normalizing to 0-100."""
    vals = [g for s in schools if (g := _grid_generosity(s)) is not None]
    return max(vals, default=0.70) or 0.70


def _compute_scholarship(
    profile: dict,
    school: dict,
    lsat: Optional[int],
    gpa: float,
    generosity_max: float = 0.70,
) -> float:
    """
    Combined merit + need-based scholarship likelihood.

    Merit: splitter detection + school generosity.
    Need:  income-bracket signal scales a flat boost across all schools.
    """
    # --- Merit component ---
    if lsat is None:
        lsat = 160  # conservative placeholder

    lsat_vs_75  = lsat - school["lsat_75"]
    gpa_vs_75   = gpa  - school["gpa_75"]
    gpa_vs_25   = gpa  - school["gpa_25"]
    gpa_below_25 = school["gpa_25"] - gpa

    # Splitter: high LSAT, low-ish GPA
    if lsat_vs_75 > 5 and gpa_below_25 <= 0.30:
        merit_base = 85.0
    elif lsat_vs_75 > 5 and gpa_below_25 > 0.30:
        merit_base = 35.0   # GPA drags school median too far
    elif gpa_vs_75 > 0.5 and lsat < school["lsat_50"]:
        merit_base = 60.0   # reverse splitter
    else:
        merit_base = 50.0

    # Generosity: prefer the real ABA 509 award grid (weights award SIZE, not just
    # receipt) — full band counts most, then half-to-full, then <half — normalized
    # against the most generous school so it occupies the full 0-100 range. Fall
    # back to the flat "any grant" rate when grid data is absent.
    grid_g = _grid_generosity(school)
    if grid_g is not None:
        school_generosity = _clamp((grid_g / generosity_max) * 100)
    else:
        school_generosity = school.get("scholarship_pct", 0.75) * 100
    median_scholarship_bonus = min(school.get("median_scholarship", 20000) / 50000, 1.0) * 10

    lsat_pct = _clamp(
        (lsat - school["lsat_25"]) / max(school["lsat_75"] - school["lsat_25"], 1) * 100
    )
    gpa_pct = _clamp(
        (gpa  - school["gpa_25"])  / max(school["gpa_75"]  - school["gpa_25"],  0.01) * 100
    )
    percentile_fit = (lsat_pct + gpa_pct) / 2 * 0.30

    merit_score = (
        merit_base                * 0.40
        + school_generosity       * 0.30
        + percentile_fit
        + median_scholarship_bonus
    )

    # Conditional scholarships (ABA reported) can be revoked after 1L if the
    # student misses a GPA stipulation. Penalize by the school's ACTUAL reduction
    # rate (share of conditional awards historically cut) when known — a school
    # that rarely cuts is low-risk, one that guts a quarter of them is not — and
    # fall back to a flat penalty when the rate is unavailable.
    if school.get("conditional_scholarship"):
        reduction_rate = school.get("conditional_reduction_rate")
        merit_score -= reduction_rate * 40.0 if reduction_rate is not None else 5.0

    # --- Need component ---
    income_bracket = profile.get("income_bracket", "prefer_not")
    need_factor    = _NEED_FACTORS.get(income_bracket, 0.30)
    need_boost     = need_factor * _NEED_BOOST_MAX

    return _clamp(merit_score + need_boost)


# ---------------------------------------------------------------------------
# 5. Financial Reality
# ---------------------------------------------------------------------------

_LIVING_EXPENSE_BASE = 22_000   # annual baseline (NALP estimate), scaled by COL index

_GOAL_USES_PRIVATE_SALARY = {
    "biglaw", "in-house", "academia",
}

_MONTHLY_PAYMENT_FACTOR = 0.01161   # 10-yr repayment at 7% interest

# PSLF / IDR constants
_PSLF_ELIGIBLE_GOALS  = {"public interest", "government"}
_IDR_POVERTY_LINE     = 22_590   # 150% of 2024 federal poverty line (1 person)
_IDR_INCOME_PCT       = 0.10     # PAYE/IBR: 10% of discretionary income
_PSLF_MONTHS          = 120      # 10 years of qualifying payments

# LRAP monthly reductions by school quality tier (dollars)
_LRAP_MONTHLY_REDUCTION = {
    "excellent": 700,
    "strong":    400,
    "moderate":  150,
    "weak":        0,
}


def _expected_tuition_discount(school: dict, scholarship_score: float) -> Optional[float]:
    """
    Fraction of annual tuition the applicant can expect covered, derived from the
    school's real ABA 509 award grid scaled by the applicant's competitiveness.

    Returns None when grid data is absent (caller falls back to the heuristic).

    avg_award_frac = dollar-weighted average award SIZE among recipients
                     (full≈1.0, half-to-full≈0.75, <half≈0.25 of tuition).
    award_rate     = share of the class receiving any grant, scaled by a
                     competitiveness factor (scholarship_score 50 ≈ neutral).
    discount       = avg_award_frac × min(award_rate × comp, 1.0)   ∈ [0, 1]
    """
    full = school.get("scholarship_full_pct")
    if full is None:
        return None
    htf = school.get("scholarship_half_to_full_pct") or 0.0
    lth = school.get("scholarship_less_than_half_pct") or 0.0
    awarded = full + htf + lth
    if awarded <= 0:
        return 0.0
    avg_award_frac = (full * 1.0 + htf * 0.75 + lth * 0.25) / awarded
    comp = 0.4 + (scholarship_score / 100) * 1.0          # [0.4, 1.4]
    return min(avg_award_frac * min(awarded * comp, 1.0), 1.0)


def _compute_financial(
    profile: dict,
    school: dict,
    scholarship_score: float,
) -> tuple[float, dict]:
    """
    Estimate net debt and score debt-to-income ratio (standard repayment).

    Also computes an optional PSLF/IDR path for Public Interest and Government
    goals — returned in the breakdown dict for display, but does NOT affect the
    score (the score stays on standard repayment so it remains a conservative
    baseline regardless of career commitment length).

    Returns (score 0-100, breakdown dict with raw numbers for display).
    """
    # Determine tuition: resident if user qualifies, else nonresident
    instate_states = [s.upper() for s in profile.get("instate_states", [])]
    school_state   = (school.get("state") or "").upper()
    qualifies_instate = school_state in instate_states

    if qualifies_instate:
        annual_tuition = school.get("annual_tuition_resident", school.get("annual_tuition", 0))
    else:
        annual_tuition = school.get("annual_tuition_nonresident", school.get("annual_tuition", 0))

    tuition_3yr = annual_tuition * 3

    col_index = school.get("cost_of_living_index", 100)
    living_3yr = (_LIVING_EXPENSE_BASE * (col_index / 100)) * 3

    gross_cost = tuition_3yr + living_3yr

    # Estimated aid: prefer the school's real award grid (ABA 509) gated by the
    # applicant's competitiveness; fall back to the median-scholarship heuristic
    # when grid data is absent.
    median_scholarship = school.get("median_scholarship", 0)
    discount = _expected_tuition_discount(school, scholarship_score)
    if discount is not None:
        expected_aid = annual_tuition * discount * 3
    elif scholarship_score >= 65:
        expected_aid = median_scholarship * 3
    elif scholarship_score >= 45:
        expected_aid = median_scholarship * 1.5
    else:
        expected_aid = 0.0

    net_debt = max(gross_cost - expected_aid, 0)

    # Starting salary based on career goal
    goal_key = (profile.get("goal") or "Unsure").lower()
    use_private = any(g in goal_key for g in _GOAL_USES_PRIVATE_SALARY)
    starting_salary = (
        school.get("median_private_sector_salary", 75000) if use_private
        else school.get("median_public_sector_salary", 60000)
    )

    # Primary score: standard 10-yr repayment DTI (conservative baseline)
    dti            = net_debt / max(starting_salary, 1)
    score          = _clamp(100 - (dti * 25))
    monthly_payment = net_debt * _MONTHLY_PAYMENT_FACTOR

    breakdown = {
        "annual_tuition_effective":  annual_tuition,
        "qualifies_instate":         qualifies_instate,
        "tuition_3yr":               round(tuition_3yr),
        "living_3yr":                round(living_3yr),
        "gross_cost":                round(gross_cost),
        "expected_aid":              round(expected_aid),
        "net_debt":                  round(net_debt),
        "starting_salary":           starting_salary,
        "monthly_payment_estimate":  round(monthly_payment),
        "debt_to_income_ratio":      round(dti, 2),
        "pslf_eligible":             False,
    }

    # PSLF / IDR alternate path — only for PI and Government goals
    matched_goal = "unsure"
    for g in _PSLF_ELIGIBLE_GOALS:
        if g in goal_key:
            matched_goal = g
            break

    if matched_goal != "unsure":
        # IDR monthly payment (PAYE/IBR: 10% of income above 150% poverty line)
        discretionary_income = max(starting_salary - _IDR_POVERTY_LINE, 0)
        idr_monthly_gross    = round(discretionary_income * _IDR_INCOME_PCT / 12)

        # LRAP reduces your out-of-pocket IDR payment
        lrap_quality     = school.get("lrap_quality", "moderate").lower()
        lrap_reduction   = _LRAP_MONTHLY_REDUCTION.get(lrap_quality, 0)
        idr_monthly_net  = max(idr_monthly_gross - lrap_reduction, 0)

        # Total paid over 10 years, capped at net_debt (can't overpay)
        pslf_total_paid  = min(idr_monthly_net * _PSLF_MONTHS, net_debt)
        pslf_forgiven    = max(round(net_debt - pslf_total_paid), 0)

        breakdown.update({
            "pslf_eligible":       True,
            "idr_monthly_gross":   idr_monthly_gross,
            "lrap_monthly":        lrap_reduction,
            "idr_monthly_net":     idr_monthly_net,
            "pslf_total_paid":     round(pslf_total_paid),
            "pslf_forgiven":       pslf_forgiven,
        })

    return _clamp(score), breakdown


# ---------------------------------------------------------------------------
# Composite + ranking
# ---------------------------------------------------------------------------

# Multipliers applied to composite score by admissibility tier.
# Individual scores stay transparent — only the ranking priority shifts.
_TIER_COMPOSITE_MULTIPLIER = {
    "safety":     1.00,
    "target":     1.00,
    "reach":      0.92,
    "hard reach": 0.80,
}


def _composite(
    scores: dict,
    career_slider: float,
    location_slider: float,
    scholarship_slider: float,
    tier: str,
) -> float:
    """
    Weighted average of six scores, scaled by admissibility tier.

    Fixed weights:  admissibility 0.15, prestige 0.05  (total 0.20 fixed)
    User-adjustable (sliders 0-10 each, financial absorbs the remainder):
      career_w     = 0.25 + (career_slider/10)*0.12     → [0.25, 0.37]
      location_w   = 0.17 + (location_slider/10)*0.10   → [0.17, 0.27]
      scholarship_w = 0.05 + (scholarship_slider/10)*0.10 → [0.05, 0.15]
      financial_w  = 0.80 − career_w − location_w − scholarship_w

    At all defaults (slider=5): career 31%, location 22%, scholarship 10%, financial 17%.
    Tier multiplier suppresses hard-reach schools in the composite ranking.
    """
    career_w      = 0.25 + (career_slider      / 10) * 0.12
    location_w    = 0.17 + (location_slider    / 10) * 0.10
    scholarship_w = 0.05 + (scholarship_slider / 10) * 0.10
    financial_w   = 0.80 - career_w - location_w - scholarship_w

    raw = (
        scores["admissibility"] * 0.12
        + scores["prestige"]    * 0.08
        + scores["career_fit"]  * career_w
        + scores["location_fit"]* location_w
        + scores["scholarship"] * scholarship_w
        + scores["financial"]   * financial_w
    )
    multiplier = _TIER_COMPOSITE_MULTIPLIER.get(tier, 1.00)
    return _clamp(raw * multiplier)


# ---------------------------------------------------------------------------
# Transfer-up planning (for applicants not competitive at their target tier
# who intend to transfer to a higher-ranked school after 1L)
# ---------------------------------------------------------------------------

def _transfer_metrics(school: dict) -> dict:
    """
    Per-school transfer mobility from ABA Transfers data, normalized by 1L class
    size. Returns rates rounded to 3 dp; values are None when data is missing.

      transfer_out_rate — share of the 1L class that transferred out (a proxy for
                          "viable launchpad": students here successfully move up).
      transfer_in_rate  — transfers admitted relative to class size (how open the
                          school is to taking transfers).
    """
    class_1l = school.get("class_size_1l")
    t_out = school.get("transfers_out")
    t_in = school.get("transfers_in")
    out_rate = round(t_out / class_1l, 3) if class_1l and t_out is not None else None
    in_rate = round(t_in / class_1l, 3) if class_1l and t_in is not None else None
    return {"transfer_out_rate": out_rate, "transfer_in_rate": in_rate}


def transfer_up_plan(
    profile: dict,
    schools: list[dict],
    top_n: int = 5,
) -> dict:
    """
    Build a two-sided transfer-up plan for an applicant who may not be competitive
    at their desired tier and wants to transfer after 1L.

      launchpads — schools the applicant can realistically get into (safety/target)
                   that have the strongest transfer-out mobility: good places to
                   enroll, perform, and transfer up from.
      targets    — higher-ranked schools (better USNWR rank than the applicant's
                   best realistic admit) that admit the most transfers: realistic
                   destinations to aim for after 1L.

    Returns {"launchpads": [...], "targets": [...]} where each item carries name,
    usnwr_rank_2026, and the relevant transfer metric. Empty lists when data or
    eligible schools are absent.
    """
    lsat = profile.get("lsat")
    gpa = profile.get("gpa")
    if not gpa:
        raise ValueError("profile must include a valid GPA")

    realistic_ranks = []
    launchpad_pool = []
    for school in schools:
        _, tier = _compute_admissibility(lsat, gpa, school)
        if tier in ("safety", "target"):
            rank = school.get("usnwr_rank_2026")
            if rank is not None:
                realistic_ranks.append(rank)
            metrics = _transfer_metrics(school)
            if metrics["transfer_out_rate"] is not None:
                launchpad_pool.append((school, metrics["transfer_out_rate"]))

    launchpad_pool.sort(key=lambda pair: pair[1], reverse=True)
    launchpads = [
        {
            "id": s.get("id"),
            "name": s.get("name"),
            "usnwr_rank_2026": s.get("usnwr_rank_2026"),
            "transfer_out_rate": rate,
        }
        for s, rate in launchpad_pool[:top_n]
    ]

    # Best realistic admit = lowest (best) rank among safety/target schools.
    best_realistic = min(realistic_ranks) if realistic_ranks else None
    targets = []
    if best_realistic is not None:
        eligible = [
            s for s in schools
            if (s.get("usnwr_rank_2026") is not None
                and s["usnwr_rank_2026"] < best_realistic
                and s.get("transfers_in"))
        ]
        eligible.sort(key=lambda s: s["transfers_in"], reverse=True)
        targets = [
            {
                "id": s.get("id"),
                "name": s.get("name"),
                "usnwr_rank_2026": s.get("usnwr_rank_2026"),
                "transfers_in": s.get("transfers_in"),
            }
            for s in eligible[:top_n]
        ]

    return {"launchpads": launchpads, "targets": targets}


def rank_schools(
    profile: dict,
    schools: list[dict],
    top_n: int = 20,
) -> list[dict]:
    """
    Rank law schools by profile fit. Returns top N with all scores attached.

    Profile keys expected:
      lsat (int|None), gpa (float), goal (str),
      target_state (str),           e.g. "TX"
      instate_states (list[str]),   e.g. ["TX"]
      income_bracket (str),         "under_65k"|"65k_130k"|"130k_200k"|"over_200k"|"prefer_not"
      scholarship (int 0-10),       scholarship importance slider
      career_weight (int 0-10),     career fit importance slider
      location_weight (int 0-10),   location fit importance slider

    Each returned school dict has extra keys:
      admissibility_score, admissibility_tier,
      prestige_score,
      career_fit_score, location_fit_score,
      scholarship_score, financial_score,
      financial_breakdown (dict),
      composite_score
    """
    if not profile:
        raise ValueError("profile cannot be empty")
    if not schools:
        raise ValueError("schools cannot be empty")
    if top_n < 1:
        raise ValueError("top_n must be at least 1")

    lsat = profile.get("lsat")
    gpa  = profile.get("gpa")
    if not gpa:
        raise ValueError("profile must include a valid GPA")

    scholarship_slider = profile.get("scholarship", 5)
    career_slider      = profile.get("career_weight", 5)
    location_slider    = profile.get("location_weight", 5)
    scalars = _precompute_career_scalars(schools)
    generosity_max = _precompute_scholarship_scalar(schools)

    scored = []
    for school in schools:
        admissibility, tier = _compute_admissibility(lsat, gpa, school)
        prestige            = _compute_prestige(school)
        career_fit          = _compute_career_fit(profile, school, scalars)
        location_fit        = _compute_location_fit(profile, school)
        scholarship         = _compute_scholarship(profile, school, lsat, gpa, generosity_max)
        financial, breakdown = _compute_financial(profile, school, scholarship)

        scores = {
            "admissibility": admissibility,
            "prestige":      prestige,
            "career_fit":    career_fit,
            "location_fit":  location_fit,
            "scholarship":   scholarship,
            "financial":     financial,
        }

        entry = school.copy()
        entry["admissibility_score"]   = round(admissibility, 1)
        entry["admissibility_tier"]    = tier
        entry["prestige_score"]        = round(prestige, 1)
        entry["career_fit_score"]      = round(career_fit, 1)
        entry["location_fit_score"]    = round(location_fit, 1)
        entry["scholarship_score"]     = round(scholarship, 1)
        entry["financial_score"]       = round(financial, 1)
        entry["financial_breakdown"]   = breakdown
        entry.update(_transfer_metrics(school))
        entry["composite_score"]       = round(
            _composite(scores, career_slider, location_slider, scholarship_slider, tier), 1
        )
        scored.append(entry)

    scored.sort(key=lambda s: s["composite_score"], reverse=True)
    return scored[:top_n]
