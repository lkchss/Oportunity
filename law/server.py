"""Flask backend for the Law School Matcher web app.

Serves the static frontend in ``law/web`` and exposes a single JSON endpoint
that runs the matching algorithm against a posted profile.
"""

import hmac
import math
import os
from pathlib import Path

from flask import Flask, Response, jsonify, request, send_from_directory

from law.data_loader import DataValidationError, load_law_schools
from law.matcher import rank_schools, transfer_up_plan, build_portfolio, _parse_user_weights

WEB_DIR = Path(__file__).parent / "web"

# Single shared password (HTTP Basic Auth). Set APP_PASSWORD in the deploy
# environment to gate the whole site; leave it unset for open local dev. The
# browser supplies a username we ignore — only the password is checked.
_APP_PASSWORD = os.environ.get("APP_PASSWORD")

# Radar axis order — must match SCORE_NAMES on the frontend.
_RADAR_KEYS = [
    "admissibility_score",
    "prestige_score",
    "career_fit_score",
    "location_fit_score",
    "scholarship_score",
    "financial_score",
]

app = Flask(__name__, static_folder=str(WEB_DIR), static_url_path="")

try:
    _SCHOOLS = load_law_schools()
except (FileNotFoundError, DataValidationError) as exc:  # pragma: no cover
    raise SystemExit(f"Failed to load law school data: {exc}")


@app.before_request
def _require_password() -> Response | None:
    """Gate every route behind a single shared password when one is configured."""
    if not _APP_PASSWORD:
        return None  # no password set — open (local dev)
    auth = request.authorization
    if auth is not None and auth.password is not None and hmac.compare_digest(
        auth.password, _APP_PASSWORD
    ):
        return None
    return Response(
        "Authentication required.",
        401,
        {"WWW-Authenticate": 'Basic realm="Law School Matcher"'},
    )


def _build_weighted_states(payload: dict) -> list[dict]:
    """Coerce posted location preferences into [{state, weight}, ...].

    Accepts the multi-state weighted form (``target_states_weighted``); falls
    back to the single ``target_state`` field. Keeps only non-blank states with
    a positive weight.
    """
    raw = payload.get("target_states_weighted")
    prefs: list[dict] = []
    if isinstance(raw, list):
        for item in raw:
            state = str((item or {}).get("state") or "").strip()
            try:
                weight = float((item or {}).get("weight", 0))
            except (TypeError, ValueError):
                weight = 0.0
            if state and weight > 0:
                prefs.append({"state": state, "weight": weight})
    if not prefs:
        single = (payload.get("target_state") or "").strip()
        if single:
            prefs.append({"state": single, "weight": 1.0})
    return prefs


def _build_weighted_goals(payload: dict) -> list[dict]:
    """Coerce posted career preferences into [{goal, weight}, ...].

    Accepts the multi-goal weighted form (``goals_weighted``); falls back to the
    single ``goal`` field. Keeps only non-blank goals with a positive weight.
    """
    raw = payload.get("goals_weighted")
    goals: list[dict] = []
    if isinstance(raw, list):
        for item in raw:
            goal = str((item or {}).get("goal") or "").strip()
            try:
                weight = float((item or {}).get("weight", 0))
            except (TypeError, ValueError):
                weight = 0.0
            if goal and weight > 0:
                goals.append({"goal": goal, "weight": weight})
    if not goals:
        single = (payload.get("goal") or "").strip()
        goals.append({"goal": single or "Unsure", "weight": 1.0})
    return goals


def _build_profile(payload: dict) -> dict:
    """Coerce the posted form payload into the shape rank_schools expects."""
    no_lsat = bool(payload.get("no_lsat"))
    lsat = payload.get("lsat")
    weighted = _build_weighted_states(payload)
    goals = _build_weighted_goals(payload)
    primary_goal = max(goals, key=lambda g: g["weight"])["goal"]
    return {
        "lsat": None if no_lsat or lsat in (None, "") else int(lsat),
        "gpa": float(payload.get("gpa") or 0),
        "goal": primary_goal,                 # top-weighted goal (salary + display + columns)
        "goals_weighted": goals,
        "target_state": (payload.get("target_state") or "").strip(),
        "target_states_weighted": weighted,
        "instate_states": [s for s in (payload.get("instate_states") or []) if str(s).strip()],
        "income_bracket": payload.get("income_bracket") or "prefer_not",
        # Optional financials — blank/absent means 0 (a no-op in the matcher).
        "dependents": int(float(payload.get("dependents") or 0)),
        "cash_available": float(payload.get("cash_available") or 0),
        "existing_debt": float(payload.get("existing_debt") or 0),
        "scholarship": int(payload.get("scholarship", 5)),
        "career_weight": int(payload.get("career_weight", 5)),
        "location_weight": int(payload.get("location_weight", 5)),
        "wants_transfer": bool(payload.get("wants_transfer")),
    }


@app.get("/")
def index():
    return send_from_directory(WEB_DIR, "index.html")


@app.get("/api/schools")
def schools():
    """Raw dataset for the rankings/browse view — no profile, no algorithm."""
    return jsonify({"schools": _SCHOOLS})


@app.post("/api/match")
def match():
    payload = request.get_json(silent=True) or {}

    # Coercion (int/float) can raise on malformed input posted directly to the
    # API (the UI guards most of this); turn it into a clean 400, not a 500.
    try:
        profile = _build_profile(payload)
    except (TypeError, ValueError, OverflowError):
        return jsonify({"error": "Invalid profile fields (check LSAT/GPA)."}), 400

    if not (profile["gpa"] > 0) or math.isnan(profile["gpa"]):
        return jsonify({"error": "A valid GPA is required."}), 400

    # Optional per-score weight multipliers from the TweaksPanel.
    # Absent / null / {} → None (exact default behavior, byte-identical output).
    # All-zero → 400.  Unknown keys are silently ignored.
    try:
        user_weights = _parse_user_weights(payload.get("weights"))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    try:
        ranked = rank_schools(profile, _SCHOOLS, top_n=len(_SCHOOLS),
                              user_weights=user_weights)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    for school in ranked:
        school["radar"] = [round(school[k]) for k in _RADAR_KEYS]

    transfer_plan = transfer_up_plan(profile, _SCHOOLS)
    portfolio = build_portfolio(ranked)

    return jsonify({
        "profile": profile,
        "schools": ranked,
        "transfer_plan": transfer_plan,
        "portfolio": portfolio,
    })


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
