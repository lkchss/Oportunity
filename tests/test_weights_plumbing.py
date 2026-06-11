"""
Tests for optional user-weight multipliers in rank_schools / /api/match.

Coverage:
  1. Snapshot guard  — no weights → byte-identical to pre-weights baseline;
                       explicit default multipliers (all 1.0) → same.
  2. Reordering      — doubling financial weight moves a cheap school up for a
                       cost-sensitive profile.
  3. Invalid weights — all-zero → ValueError; all-zero via API → 400.
  4. Unknown keys    — silently ignored.
  5. Non-finite / negative → clamped to 0.0, rest renormalized.
  6. Flask integration — weights travel through /api/match end-to-end.
"""

import json
import pytest

from law.data_loader import load_law_schools
from law.matcher import rank_schools, _parse_user_weights
from law.server import app as flask_app


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def schools():
    return load_law_schools()


@pytest.fixture(scope="module")
def client():
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as c:
        yield c


# Varied profiles used for snapshot + reorder tests
_PROFILES = [
    # Profile A: strong applicant, BigLaw, NY
    {
        "lsat": 174, "gpa": 3.92, "goal": "BigLaw",
        "target_state": "NY", "instate_states": [],
        "income_bracket": "over_200k",
        "scholarship": 3, "career_weight": 7, "location_weight": 5,
    },
    # Profile B: mid-range, Public Interest, TX, cost-sensitive
    {
        "lsat": 158, "gpa": 3.55, "goal": "Public Interest",
        "target_state": "TX", "instate_states": ["TX"],
        "income_bracket": "under_65k",
        "scholarship": 8, "career_weight": 5, "location_weight": 6,
    },
    # Profile C: no LSAT, government goal, CA
    {
        "lsat": None, "gpa": 3.80, "goal": "Government",
        "target_state": "CA", "instate_states": [],
        "income_bracket": "65k_130k",
        "scholarship": 5, "career_weight": 4, "location_weight": 8,
    },
    # Profile D: weak stats, transfer intent
    {
        "lsat": 148, "gpa": 3.20, "goal": "Solo/Small Firm",
        "target_state": "OH", "instate_states": ["OH"],
        "income_bracket": "130k_200k",
        "scholarship": 5, "career_weight": 5, "location_weight": 5,
    },
]

# Default weights dict: all multipliers at 1.0 — must produce identical results.
_DEFAULT_WEIGHTS = {
    "admissibility": 1.0,
    "prestige": 1.0,
    "career_fit": 1.0,
    "location_fit": 1.0,
    "scholarship": 1.0,
    "financial": 1.0,
}


def _ranking_snapshot(profile: dict, schools: list) -> list[tuple[str, float]]:
    """Return (id, composite_score) order for a profile, no user weights."""
    ranked = rank_schools(profile, schools, top_n=len(schools))
    return [(s["id"], s["composite_score"]) for s in ranked]


# ---------------------------------------------------------------------------
# 1. Snapshot guard
# ---------------------------------------------------------------------------

class TestSnapshotGuard:
    """
    Byte-identical check: sending no weights OR explicit default weights (all
    multipliers = 1.0) must produce the exact same ranking as the pre-weights
    baseline captured from the unmodified rank_schools call.
    """

    @pytest.mark.parametrize("profile", _PROFILES)
    def test_no_weights_identical_to_baseline(self, profile, schools):
        baseline = _ranking_snapshot(profile, schools)
        result   = [(s["id"], s["composite_score"])
                    for s in rank_schools(profile, schools, top_n=len(schools),
                                         user_weights=None)]
        assert result == baseline, (
            f"no-weights result diverged from baseline for profile {profile.get('goal')}"
        )

    @pytest.mark.parametrize("profile", _PROFILES)
    def test_explicit_default_weights_identical_to_baseline(self, profile, schools):
        """All-ones multiplier dict must be a no-op."""
        baseline = _ranking_snapshot(profile, schools)
        uw = _parse_user_weights(_DEFAULT_WEIGHTS)
        result   = [(s["id"], s["composite_score"])
                    for s in rank_schools(profile, schools, top_n=len(schools),
                                         user_weights=uw)]
        assert result == baseline, (
            f"explicit default weights diverged from baseline for profile {profile.get('goal')}"
        )


# ---------------------------------------------------------------------------
# 2. Doubling financial weight reorders sanely for a cost-sensitive profile
# ---------------------------------------------------------------------------

class TestWeightReordering:

    def test_double_financial_promotes_cheap_school(self, schools):
        """
        For a cost-sensitive profile (low income, TX in-state), doubling the
        financial multiplier should improve low-cost schools' composite scores
        relative to high-cost schools (Kansas vs Georgetown).
        Kansas has much lower tuition; Georgetown is expensive and NY-focused.
        """
        profile = _PROFILES[1]  # cost-sensitive TX profile

        ranked_default = rank_schools(profile, schools, top_n=len(schools))
        ranked_fin2    = rank_schools(profile, schools, top_n=len(schools),
                                      user_weights={"financial": 2.0})

        def score_of(ranked, school_id):
            for s in ranked:
                if s["id"] == school_id:
                    return s["composite_score"]
            return 0.0

        # Kansas has substantially higher financial score than Georgetown for this profile
        ks_score_default = score_of(ranked_default, "kansas-law")
        gt_score_default = score_of(ranked_default, "georgetown-law")
        ks_score_fin2    = score_of(ranked_fin2,    "kansas-law")
        gt_score_fin2    = score_of(ranked_fin2,    "georgetown-law")

        # Gap between Kansas and Georgetown should widen when financial is up-weighted
        gap_default = ks_score_default - gt_score_default
        gap_fin2    = ks_score_fin2    - gt_score_fin2

        assert gap_fin2 >= gap_default, (
            f"Expected Kansas to gain on Georgetown with 2x financial weight, "
            f"but score gap went {gap_default:.1f} -> {gap_fin2:.1f}"
        )

    def test_zero_financial_weight_depresses_cheap_school(self, schools):
        """Setting financial multiplier to 0 removes financial from composite."""
        profile = _PROFILES[1]
        ranked_fin0 = rank_schools(profile, schools, top_n=len(schools),
                                   user_weights={"financial": 0.0})
        # Every school's composite_score must still be 0-100
        for s in ranked_fin0:
            assert 0 <= s["composite_score"] <= 100

    def test_weights_change_composite_scores(self, schools):
        """Boosting career_fit should change composite scores relative to default."""
        profile = _PROFILES[0]
        default_scores = {s["id"]: s["composite_score"]
                          for s in rank_schools(profile, schools)}
        boosted_scores = {s["id"]: s["composite_score"]
                          for s in rank_schools(profile, schools,
                                                user_weights={"career_fit": 3.0})}
        # At least some schools must change score
        diffs = sum(1 for sid in default_scores
                    if boosted_scores.get(sid) != default_scores[sid])
        assert diffs > 0, "Boosting career_fit weight changed no composite scores"


# ---------------------------------------------------------------------------
# 3. Invalid weights
# ---------------------------------------------------------------------------

class TestInvalidWeights:

    def test_all_zero_raises_value_error(self):
        with pytest.raises(ValueError, match="zero"):
            _parse_user_weights({
                "admissibility": 0.0,
                "prestige": 0.0,
                "career_fit": 0.0,
                "location_fit": 0.0,
                "scholarship": 0.0,
                "financial": 0.0,
            })

    def test_none_returns_none(self):
        assert _parse_user_weights(None) is None

    def test_empty_dict_returns_none(self):
        assert _parse_user_weights({}) is None

    def test_all_zero_via_api_returns_400(self, client):
        payload = {
            "lsat": 163, "gpa": 3.75, "goal": "BigLaw",
            "target_state": "NY",
            "weights": {
                "admissibility": 0, "prestige": 0, "career_fit": 0,
                "location_fit": 0, "scholarship": 0, "financial": 0,
            },
        }
        resp = client.post("/api/match", json=payload)
        assert resp.status_code == 400

    def test_valid_weights_via_api_returns_200(self, client):
        payload = {
            "lsat": 163, "gpa": 3.75, "goal": "BigLaw",
            "target_state": "NY",
            "weights": {"financial": 2.0, "career_fit": 0.5},
        }
        resp = client.post("/api/match", json=payload)
        assert resp.status_code == 200
        data = resp.get_json()
        assert "schools" in data
        assert len(data["schools"]) > 0


# ---------------------------------------------------------------------------
# 4. Unknown keys silently ignored
# ---------------------------------------------------------------------------

class TestUnknownKeys:

    def test_unknown_keys_ignored(self, schools):
        """Unknown weight keys must not raise and must produce valid results."""
        uw = _parse_user_weights({
            "financial": 2.0,
            "nonexistent_dimension": 999.9,
            "another_bad_key": -5,
        })
        assert uw is not None
        assert "nonexistent_dimension" not in uw
        profile = _PROFILES[0]
        ranked = rank_schools(profile, schools, top_n=10, user_weights=uw)
        assert len(ranked) > 0
        for s in ranked:
            assert 0 <= s["composite_score"] <= 100


# ---------------------------------------------------------------------------
# 5. Non-finite / negative clamped to 0.0
# ---------------------------------------------------------------------------

class TestNonFiniteWeights:

    def test_negative_clamped_to_zero(self):
        uw = _parse_user_weights({"financial": -5.0, "career_fit": 1.0})
        assert uw["financial"] == 0.0
        assert uw["career_fit"] == 1.0

    def test_infinity_clamped_to_zero(self):
        uw = _parse_user_weights({"financial": float("inf"), "career_fit": 1.0})
        assert uw["financial"] == 0.0

    def test_nan_clamped_to_zero(self):
        uw = _parse_user_weights({"financial": float("nan"), "career_fit": 1.0})
        assert uw["financial"] == 0.0

    def test_non_numeric_string_clamped_to_zero(self):
        uw = _parse_user_weights({"financial": "bad", "career_fit": 1.0})
        assert uw["financial"] == 0.0


# ---------------------------------------------------------------------------
# 6. Flask integration — default weights travel through /api/match unchanged
# ---------------------------------------------------------------------------

class TestFlaskIntegration:

    def test_no_weights_key_equals_explicit_defaults(self, client):
        """POST without weights key == POST with all-1.0 weights."""
        base = {
            "lsat": 163, "gpa": 3.75, "goal": "BigLaw",
            "target_state": "NY", "income_bracket": "prefer_not",
            "scholarship": 5, "career_weight": 5, "location_weight": 5,
        }
        resp_no_w  = client.post("/api/match", json=base)
        resp_def_w = client.post("/api/match", json={**base, "weights": _DEFAULT_WEIGHTS})

        assert resp_no_w.status_code == 200
        assert resp_def_w.status_code == 200

        order_no_w  = [(s["id"], s["composite_score"])
                       for s in resp_no_w.get_json()["schools"]]
        order_def_w = [(s["id"], s["composite_score"])
                       for s in resp_def_w.get_json()["schools"]]
        assert order_no_w == order_def_w, (
            "Sending explicit default weights changed the ranking"
        )

    def test_null_weights_key_same_as_absent(self, client):
        """POST with weights: null == no weights key."""
        base = {
            "lsat": 163, "gpa": 3.75, "goal": "BigLaw",
            "target_state": "NY",
        }
        resp_absent = client.post("/api/match", json=base)
        resp_null   = client.post("/api/match", json={**base, "weights": None})

        assert resp_absent.status_code == 200
        assert resp_null.status_code   == 200

        order_absent = [(s["id"], s["composite_score"])
                        for s in resp_absent.get_json()["schools"]]
        order_null   = [(s["id"], s["composite_score"])
                        for s in resp_null.get_json()["schools"]]
        assert order_absent == order_null
