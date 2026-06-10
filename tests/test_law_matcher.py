"""
Stress tests for law/matcher.py — four angles:
  1. Edge cases (no LSAT, extreme splitters, boundary inputs)
  2. Score sanity (tiers, ordering, score ranges)
  3. Ranking stability (slider sensitivity, monotonicity)
  4. Financial math (debt, PSLF, DTI)
"""

import pytest
from law.data_loader import load_law_schools
from law.matcher import (
    rank_schools,
    transfer_up_plan,
    _compute_admissibility,
    _compute_career_fit,
    _compute_location_fit,
    _compute_scholarship,
    _compute_financial,
    _transfer_metrics,
    _precompute_career_scalars,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def schools():
    return load_law_schools()


@pytest.fixture(scope="module")
def scalars(schools):
    return _precompute_career_scalars(schools)


def _school(schools, id_):
    return next(s for s in schools if s["id"] == id_)


def _profile(**kwargs):
    base = {
        "lsat": 163,
        "gpa": 3.75,
        "goal": "BigLaw",
        "target_state": "NY",
        "instate_states": [],
        "income_bracket": "prefer_not",
        "scholarship": 5,
    }
    base.update(kwargs)
    return base


# ---------------------------------------------------------------------------
# 1. Edge Cases
# ---------------------------------------------------------------------------

class TestEdgeCases:

    def test_no_lsat_runs_without_error(self, schools):
        profile = _profile(lsat=None)
        ranked = rank_schools(profile, schools, top_n=10)
        assert len(ranked) > 0

    def test_no_lsat_capped_below_full_lsat(self, schools):
        """No-LSAT candidate should never score above the same candidate with LSAT."""
        s = _school(schools, "iowa-law")
        score_with, _ = _compute_admissibility(163, 3.75, s)
        score_without, _ = _compute_admissibility(None, 3.75, s)
        assert score_without <= score_with

    def test_no_lsat_score_stays_in_tier_band(self, schools):
        """No-LSAT path must keep the score inside its tier band (no score↔tier
        contradiction from the GPA-only penalty)."""
        bands = {"hard reach": (0, 38), "reach": (38, 60),
                 "target": (60, 82), "safety": (82, 100)}
        for gpa in (4.0, 3.7, 3.4, 3.0, 2.6):
            for s in schools:
                score, tier = _compute_admissibility(None, gpa, s)
                lo, hi = bands[tier]
                assert lo - 0.01 <= score <= hi + 0.01, (s["id"], gpa, score, tier)

    def test_extreme_splitter_high_lsat_low_gpa(self, schools, scalars):
        """165 LSAT / 2.8 GPA — should not crash, scholarship score should be elevated."""
        profile = _profile(lsat=165, gpa=2.8)
        ranked = rank_schools(profile, schools, top_n=32)
        assert len(ranked) > 0
        # All scores in range
        for s in ranked:
            assert 0 <= s["admissibility_score"] <= 100
            assert 0 <= s["scholarship_score"] <= 100

    def test_extreme_splitter_low_lsat_high_gpa(self, schools):
        """155 LSAT / 4.0 GPA — reverse splitter should not crash."""
        profile = _profile(lsat=155, gpa=4.0)
        ranked = rank_schools(profile, schools, top_n=32)
        assert len(ranked) > 0

    def test_perfect_stats(self, schools):
        """180 LSAT / 4.0 GPA — safety everywhere EXCEPT ultra-selective schools,
        which are capped by acceptance rate (no school is a guaranteed admit)."""
        profile = _profile(lsat=180, gpa=4.0)
        ranked = rank_schools(profile, schools)
        for s in ranked:
            rate = s.get("acceptance_rate")
            if rate is None or rate >= 0.12:
                assert s["admissibility_tier"] == "safety"
            elif rate < 0.05:
                assert s["admissibility_tier"] == "reach"      # ceiling
            else:
                assert s["admissibility_tier"] == "target"     # ceiling
            # Score must stay consistent with the (possibly capped) tier band.
            assert s["admissibility_score"] >= 38

    def test_very_weak_stats(self, schools):
        """130 LSAT / 2.5 GPA — every school should be hard reach."""
        profile = _profile(lsat=130, gpa=2.5)
        ranked = rank_schools(profile, schools)
        for s in ranked:
            assert s["admissibility_tier"] == "hard reach"

    def test_no_target_state_returns_neutral_location(self, schools):
        """Empty target_state gives every school a neutral location score (50)."""
        profile = _profile(target_state="")
        ranked = rank_schools(profile, schools)
        for s in ranked:
            assert s["location_fit_score"] == 50.0

    def test_instate_tuition_applied(self, schools):
        """In-state resident should see lower tuition in breakdown than out-of-state."""
        ohio = _school(schools, "ohio-state-moritz-law")
        profile_in  = _profile(instate_states=["OH"])
        profile_out = _profile(instate_states=[])
        _, bd_in  = _compute_financial(profile_in,  ohio, 60.0)
        _, bd_out = _compute_financial(profile_out, ohio, 60.0)
        assert bd_in["annual_tuition_effective"] < bd_out["annual_tuition_effective"]
        assert bd_in["qualifies_instate"] is True
        assert bd_out["qualifies_instate"] is False

    def test_all_income_brackets_run(self, schools):
        """Every income_bracket option completes without error."""
        for bracket in ("under_65k", "65k_130k", "130k_200k", "over_200k", "prefer_not"):
            profile = _profile(income_bracket=bracket)
            ranked = rank_schools(profile, schools, top_n=5)
            assert len(ranked) > 0

    def test_scholarship_slider_extremes(self, schools):
        """Slider at 0 and 10 both produce valid results."""
        for slider in (0, 10):
            profile = _profile(scholarship=slider)
            ranked = rank_schools(profile, schools, top_n=5)
            assert all(0 <= s["composite_score"] <= 100 for s in ranked)

    def test_all_goal_types_run(self, schools):
        """Every goal option completes without error."""
        goals = ["BigLaw", "Federal Clerkship", "Government", "Public Interest",
                 "Solo/Small Firm", "In-house", "Academia", "Unsure"]
        for goal in goals:
            profile = _profile(goal=goal)
            ranked = rank_schools(profile, schools, top_n=5)
            assert len(ranked) > 0


# ---------------------------------------------------------------------------
# 2. Score Sanity
# ---------------------------------------------------------------------------

class TestScoreSanity:

    def test_all_scores_in_range(self, schools):
        """Every score field must be 0–100 for a typical profile."""
        profile = _profile()
        ranked = rank_schools(profile, schools)
        fields = ["admissibility_score", "career_fit_score", "location_fit_score",
                  "scholarship_score", "financial_score", "composite_score"]
        for s in ranked:
            for f in fields:
                assert 0 <= s[f] <= 100, f"{s['name']} {f}={s[f]}"

    def test_tier_matches_score_direction(self, schools):
        """Safety tier schools should have higher admissibility scores than hard reach."""
        profile = _profile(lsat=170, gpa=3.90)
        ranked = rank_schools(profile, schools)
        safeties    = [s["admissibility_score"] for s in ranked if s["admissibility_tier"] == "safety"]
        hard_reaches = [s["admissibility_score"] for s in ranked if s["admissibility_tier"] == "hard reach"]
        if safeties and hard_reaches:
            assert min(safeties) > max(hard_reaches)

    def test_valid_tier_labels(self, schools):
        """All tier labels must be one of the four valid values."""
        profile = _profile()
        ranked = rank_schools(profile, schools)
        valid = {"safety", "target", "reach", "hard reach"}
        for s in ranked:
            assert s["admissibility_tier"] in valid

    def test_biglaw_school_scores_higher_for_biglaw_goal(self, schools, scalars):
        """For BigLaw goal, USC Gould (67% biglaw) should outscore Kansas (7%)."""
        profile = _profile(goal="BigLaw", target_state="")
        usc    = _school(schools, "usc-gould-law")
        kansas = _school(schools, "kansas-law")
        usc_score    = _compute_career_fit(profile, usc,    scalars)
        kansas_score = _compute_career_fit(profile, kansas, scalars)
        assert usc_score > kansas_score

    def test_pi_school_scores_higher_for_pi_goal(self, schools, scalars):
        """For Public Interest goal, Wisconsin (25.5% PI) should outscore SMU (5%)."""
        profile = _profile(goal="Public Interest", target_state="")
        wisc = _school(schools, "wisconsin-law")
        smu  = _school(schools, "smu-dedman-law")
        wisc_score = _compute_career_fit(profile, wisc, scalars)
        smu_score  = _compute_career_fit(profile, smu,  scalars)
        assert wisc_score > smu_score

    def test_career_weighted_blend_between_goals(self, schools, scalars):
        """A BigLaw/PI weighted blend lands between the two single-goal fits."""
        usc = _school(schools, "usc-gould-law")
        big = _compute_career_fit(
            _profile(goals_weighted=[{"goal": "BigLaw", "weight": 1}]), usc, scalars)
        pi = _compute_career_fit(
            _profile(goals_weighted=[{"goal": "Public Interest", "weight": 1}]), usc, scalars)
        blend = _compute_career_fit(
            _profile(goals_weighted=[{"goal": "BigLaw", "weight": 50},
                                     {"goal": "Public Interest", "weight": 50}]), usc, scalars)
        assert big != pi
        assert min(big, pi) - 0.01 <= blend <= max(big, pi) + 0.01

    def test_career_weighted_overrides_single_goal(self, schools, scalars):
        """When goals_weighted is present, the legacy single goal is ignored."""
        usc = _school(schools, "usc-gould-law")
        a = _compute_career_fit(
            _profile(goal="BigLaw", goals_weighted=[{"goal": "Public Interest", "weight": 1}]),
            usc, scalars)
        b = _compute_career_fit(
            _profile(goal="Academia", goals_weighted=[{"goal": "Public Interest", "weight": 1}]),
            usc, scalars)
        assert a == b

    def test_location_score_primary_state_beats_unlisted(self, schools):
        """School placing grads primarily in TX scores higher for TX target than an unlisted one."""
        profile = _profile(target_state="TX")
        baylor = _school(schools, "baylor-law")        # target_states[0] = TX
        fordham = _school(schools, "fordham-law")      # TX not in target_states
        baylor_loc  = _compute_location_fit(profile, baylor)
        fordham_loc = _compute_location_fit(profile, fordham)
        assert baylor_loc > fordham_loc

    def test_location_score_primary_beats_secondary(self, schools):
        """Position 0 in target_states should score higher than position 1."""
        profile = _profile(target_state="NY")
        fordham = _school(schools, "fordham-law")  # NY is position 0
        # find a school with NY at position > 0
        bc = _school(schools, "boston-college-law")  # NY is position 1
        fordham_loc = _compute_location_fit(profile, fordham)
        bc_loc      = _compute_location_fit(profile, bc)
        assert fordham_loc > bc_loc

    def test_weighted_states_blend_between_extremes(self, schools):
        """A weighted CA/NY blend sits between the single-state fits, leaning by weight."""
        fordham = _school(schools, "fordham-law")  # NY position 0, CA unlisted
        ny = _compute_location_fit(
            _profile(target_state="", target_states_weighted=[{"state": "NY", "weight": 1}]), fordham)
        ca = _compute_location_fit(
            _profile(target_state="", target_states_weighted=[{"state": "CA", "weight": 1}]), fordham)
        blend = _compute_location_fit(
            _profile(target_state="",
                     target_states_weighted=[{"state": "NY", "weight": 30},
                                             {"state": "CA", "weight": 70}]), fordham)
        assert ny > ca
        assert ca < blend < ny            # blend lands between, weighted toward CA

    def test_weighted_states_override_legacy_single(self, schools):
        """When both are present, the weighted form takes precedence over target_state."""
        fordham = _school(schools, "fordham-law")
        weighted_only = _compute_location_fit(
            _profile(target_state="", target_states_weighted=[{"state": "NY", "weight": 1}]), fordham)
        legacy_conflict = _compute_location_fit(
            _profile(target_state="CA", target_states_weighted=[{"state": "NY", "weight": 1}]), fordham)
        assert weighted_only == legacy_conflict

    def test_high_need_boosts_scholarship_score(self, schools):
        """Under $65k income bracket should give higher scholarship than over $200k."""
        school = _school(schools, "iowa-law")
        low  = _profile(income_bracket="under_65k")
        high = _profile(income_bracket="over_200k")
        s_low  = _compute_scholarship(low,  school, 163, 3.75)
        s_high = _compute_scholarship(high, school, 163, 3.75)
        assert s_low > s_high

    def test_instate_improves_financial_score(self, schools):
        """In-state tuition reduces debt and should improve financial score."""
        ohio = _school(schools, "ohio-state-moritz-law")
        scholarship_score = 60.0
        score_in,  _ = _compute_financial(_profile(instate_states=["OH"]), ohio, scholarship_score)
        score_out, _ = _compute_financial(_profile(instate_states=[]),     ohio, scholarship_score)
        assert score_in > score_out

    def test_cheap_school_better_financial_than_expensive(self, schools):
        """Kansas (low COL, low tuition) should outscore USC Gould on financial for same profile."""
        profile = _profile(goal="Government", instate_states=[], income_bracket="prefer_not")
        kansas = _school(schools, "kansas-law")
        usc    = _school(schools, "usc-gould-law")
        schol = 50.0
        f_kansas, _ = _compute_financial(profile, kansas, schol)
        f_usc,    _ = _compute_financial(profile, usc,    schol)
        assert f_kansas > f_usc


# ---------------------------------------------------------------------------
# 3. Ranking Stability
# ---------------------------------------------------------------------------

class TestRankingStability:

    def test_sorted_descending_by_composite(self, schools):
        """Results must always be sorted descending by composite_score."""
        profile = _profile()
        ranked = rank_schools(profile, schools)
        scores = [s["composite_score"] for s in ranked]
        assert scores == sorted(scores, reverse=True)

    def test_top_n_respected(self, schools):
        """rank_schools(top_n=5) returns at most 5 schools."""
        profile = _profile()
        ranked = rank_schools(profile, schools, top_n=5)
        assert len(ranked) <= 5

    def test_scholarship_slider_monotonicity(self, schools):
        """A highly generous school should rank higher as scholarship slider increases."""
        # Washington & Lee: 97% scholarship, generous — should climb vs a stingy school
        wl     = _school(schools, "washington-lee-law")
        fordham = _school(schools, "fordham-law")  # 57% scholarship

        def rank_of(school_id, slider):
            profile = _profile(target_state="", scholarship=slider)
            ranked = rank_schools(profile, schools)
            ids = [s["id"] for s in ranked]
            return ids.index(school_id) if school_id in ids else 999

        # W&L rank should be better (lower index) at slider=10 vs slider=0
        wl_rank_low    = rank_of("washington-lee-law", 0)
        wl_rank_high   = rank_of("washington-lee-law", 10)
        ford_rank_low  = rank_of("fordham-law", 0)
        ford_rank_high = rank_of("fordham-law", 10)

        # Gap between W&L and Fordham should grow as slider increases
        gap_low  = ford_rank_low  - wl_rank_low
        gap_high = ford_rank_high - wl_rank_high
        assert gap_high >= gap_low

    def test_target_state_changes_ranking(self, schools):
        """Changing target state should change the top-ranked school."""
        profile_tx = _profile(target_state="TX")
        profile_ny = _profile(target_state="NY")
        top_tx = rank_schools(profile_tx, schools, top_n=1)[0]["id"]
        top_ny = rank_schools(profile_ny, schools, top_n=1)[0]["id"]
        assert top_tx != top_ny

    def test_instate_improves_composite_score(self, schools):
        """Being in-state at a public school should raise its composite score."""
        profile_in  = _profile(target_state="", instate_states=["OH"])
        profile_out = _profile(target_state="", instate_states=[])
        ranked_in  = rank_schools(profile_in,  schools, top_n=75)
        ranked_out = rank_schools(profile_out, schools, top_n=75)
        ohio_in  = next(s for s in ranked_in  if s["id"] == "ohio-state-moritz-law")
        ohio_out = next(s for s in ranked_out if s["id"] == "ohio-state-moritz-law")
        assert ohio_in["composite_score"] > ohio_out["composite_score"]

    def test_deterministic(self, schools):
        """Same profile always returns same ranking."""
        profile = _profile()
        r1 = [s["id"] for s in rank_schools(profile, schools)]
        r2 = [s["id"] for s in rank_schools(profile, schools)]
        assert r1 == r2


# ---------------------------------------------------------------------------
# 4. Financial Math
# ---------------------------------------------------------------------------

class TestFinancialMath:

    def test_net_debt_non_negative(self, schools):
        """Net debt must never go negative."""
        profile = _profile(income_bracket="under_65k", scholarship=10)
        for school in schools:
            _, bd = _compute_financial(profile, school, 90.0)
            assert bd["net_debt"] >= 0

    def test_gross_cost_components_add_up(self, schools):
        """gross_cost == tuition_3yr + living_3yr."""
        profile = _profile()
        for school in schools:
            _, bd = _compute_financial(profile, school, 50.0)
            assert bd["gross_cost"] == bd["tuition_3yr"] + bd["living_3yr"]

    def test_dti_ratio_matches_net_debt_and_salary(self, schools):
        """debt_to_income_ratio == net_debt / starting_salary (rounded)."""
        profile = _profile(goal="BigLaw")
        for school in schools:
            _, bd = _compute_financial(profile, school, 50.0)
            expected = round(bd["net_debt"] / max(bd["starting_salary"], 1), 2)
            assert abs(bd["debt_to_income_ratio"] - expected) < 0.01

    def test_pslf_only_shown_for_eligible_goals(self, schools):
        """PSLF breakdown appears for PI/Government, not for BigLaw."""
        school = _school(schools, "wisconsin-law")
        _, bd_pi  = _compute_financial(_profile(goal="Public Interest"), school, 50.0)
        _, bd_gov = _compute_financial(_profile(goal="Government"),      school, 50.0)
        _, bd_big = _compute_financial(_profile(goal="BigLaw"),          school, 50.0)
        assert bd_pi["pslf_eligible"]  is True
        assert bd_gov["pslf_eligible"] is True
        assert bd_big["pslf_eligible"] is False

    def test_pslf_forgiven_plus_paid_equals_debt(self, schools):
        """pslf_forgiven + pslf_total_paid should approximately equal net_debt."""
        profile = _profile(goal="Public Interest")
        for school in schools:
            _, bd = _compute_financial(profile, school, 50.0)
            if bd["pslf_eligible"]:
                total = bd["pslf_forgiven"] + bd["pslf_total_paid"]
                # Allow $1 rounding tolerance
                assert abs(total - bd["net_debt"]) <= 1

    def test_strong_lrap_reduces_idr_payment(self, schools):
        """School with strong LRAP should have lower idr_monthly_net than weak LRAP."""
        profile = _profile(goal="Public Interest")
        wisc   = _school(schools, "wisconsin-law")   # lrap_quality: strong
        baylor = _school(schools, "baylor-law")      # lrap_quality: weak
        _, bd_wisc  = _compute_financial(profile, wisc,   50.0)
        _, bd_baylor = _compute_financial(profile, baylor, 50.0)
        assert bd_wisc["idr_monthly_net"] < bd_baylor["idr_monthly_net"]

    def test_grid_aid_increases_with_competitiveness(self, schools):
        """With real award-grid data, a stronger applicant gets more expected aid."""
        school = _school(schools, "iowa-law")  # has scholarship_full_pct grid
        _, bd_strong = _compute_financial(_profile(), school, 80.0)
        _, bd_weak   = _compute_financial(_profile(), school, 20.0)
        assert bd_strong["expected_aid"] > bd_weak["expected_aid"]

    def test_grid_aid_bounded_by_full_tuition(self, schools):
        """Expected aid can never exceed three years of effective tuition."""
        school = _school(schools, "boston-college-law")
        _, bd = _compute_financial(_profile(), school, 100.0)
        assert bd["expected_aid"] <= bd["annual_tuition_effective"] * 3 + 1

    def test_aid_heuristic_fallback_when_no_grid(self, schools):
        """Schools lacking grid data fall back to the median-scholarship heuristic."""
        school = dict(_school(schools, "iowa-law"))
        school.pop("scholarship_full_pct", None)  # force fallback path
        _, bd_high = _compute_financial(_profile(), school, 70.0)  # >= 65
        _, bd_low  = _compute_financial(_profile(), school, 30.0)  # < 45
        assert bd_high["expected_aid"] == school["median_scholarship"] * 3
        assert bd_low["expected_aid"] == 0.0

    def test_private_goal_uses_private_salary(self, schools):
        """BigLaw goal uses median_private_sector_salary."""
        school = _school(schools, "fordham-law")
        _, bd = _compute_financial(_profile(goal="BigLaw"), school, 50.0)
        assert bd["starting_salary"] == school["median_private_sector_salary"]

    def test_public_goal_uses_public_salary(self, schools):
        """Government goal uses median_public_sector_salary."""
        school = _school(schools, "fordham-law")
        _, bd = _compute_financial(_profile(goal="Government"), school, 50.0)
        assert bd["starting_salary"] == school["median_public_sector_salary"]


# ---------------------------------------------------------------------------
# 5. Transfer-up feature
# ---------------------------------------------------------------------------

class TestTransferUp:

    def test_metrics_present_on_ranked_schools(self, schools):
        """Ranked entries expose transfer_out_rate / transfer_in_rate."""
        ranked = rank_schools(_profile(), schools, top_n=5)
        for s in ranked:
            assert "transfer_out_rate" in s and "transfer_in_rate" in s

    def test_metrics_rate_definition(self, schools):
        """Rate equals count / class size."""
        s = _school(schools, "suny-buffalo-law")
        m = _transfer_metrics(s)
        assert m["transfer_out_rate"] == round(s["transfers_out"] / s["class_size_1l"], 3)

    def test_metrics_none_without_class_size(self):
        """Missing class size yields None rates, no crash."""
        m = _transfer_metrics({"transfers_out": 5, "transfers_in": 3})
        assert m == {"transfer_out_rate": None, "transfer_in_rate": None}

    def test_plan_shape(self, schools):
        """Plan returns launchpad and target lists."""
        plan = transfer_up_plan(_profile(lsat=158, gpa=3.4), schools)
        assert set(plan) == {"launchpads", "targets"}
        assert isinstance(plan["launchpads"], list)
        assert isinstance(plan["targets"], list)

    def test_targets_are_reaches_that_take_transfers(self, schools):
        """Every transfer target is a reach for the applicant AND admits transfers."""
        profile = _profile(lsat=156, gpa=3.3)  # not T14-competitive
        plan = transfer_up_plan(profile, schools)
        by_id = {s["id"]: s for s in schools}
        for t in plan["targets"]:
            assert _compute_admissibility(
                profile["lsat"], profile["gpa"], by_id[t["id"]])[1] == "reach"
            assert t["transfers_in"]  # > 0

    def test_launchpads_are_realistic_admits_by_score(self, schools):
        """Launchpads are safety/target tier, ordered by composite score descending."""
        plan = transfer_up_plan(_profile(lsat=157, gpa=3.4), schools)
        by_id = {s["id"]: s for s in schools}
        for lp in plan["launchpads"]:
            assert _compute_admissibility(157, 3.4, by_id[lp["id"]])[1] in ("safety", "target")
        scores = [lp["composite_score"] for lp in plan["launchpads"]]
        assert scores == sorted(scores, reverse=True)

    def test_transfer_plan_responds_to_profile(self, schools):
        """Changing the target state should change the transfer-up recommendations
        (the plan must be profile-aware, not the same schools for everyone)."""
        tx = transfer_up_plan(_profile(lsat=156, gpa=3.3, target_state="TX"), schools)
        ny = transfer_up_plan(_profile(lsat=156, gpa=3.3, target_state="NY"), schools)
        tx_ids = [lp["id"] for lp in tx["launchpads"]] + [t["id"] for t in tx["targets"]]
        ny_ids = [lp["id"] for lp in ny["launchpads"]] + [t["id"] for t in ny["targets"]]
        assert tx_ids != ny_ids
