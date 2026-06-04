"""Flask backend for the Law School Matcher web app.

Serves the static frontend in ``law/web`` and exposes a single JSON endpoint
that runs the matching algorithm against a posted profile.
"""

import hmac
import os
from pathlib import Path

from flask import Flask, Response, jsonify, request, send_from_directory

from law.data_loader import DataValidationError, load_law_schools
from law.matcher import rank_schools, transfer_up_plan

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


def _build_profile(payload: dict) -> dict:
    """Coerce the posted form payload into the shape rank_schools expects."""
    no_lsat = bool(payload.get("no_lsat"))
    lsat = payload.get("lsat")
    return {
        "lsat": None if no_lsat or lsat in (None, "") else int(lsat),
        "gpa": float(payload.get("gpa") or 0),
        "goal": payload.get("goal") or "Unsure",
        "target_state": (payload.get("target_state") or "").strip(),
        "instate_states": payload.get("instate_states") or [],
        "income_bracket": payload.get("income_bracket") or "prefer_not",
        "scholarship": int(payload.get("scholarship", 5)),
        "career_weight": int(payload.get("career_weight", 5)),
        "location_weight": int(payload.get("location_weight", 5)),
    }


@app.get("/")
def index():
    return send_from_directory(WEB_DIR, "index.html")


@app.post("/api/match")
def match():
    payload = request.get_json(silent=True) or {}
    profile = _build_profile(payload)

    if profile["gpa"] <= 0:
        return jsonify({"error": "A valid GPA is required."}), 400

    try:
        ranked = rank_schools(profile, _SCHOOLS, top_n=len(_SCHOOLS))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    for school in ranked:
        school["radar"] = [round(school[k]) for k in _RADAR_KEYS]

    transfer_plan = transfer_up_plan(profile, _SCHOOLS)

    return jsonify({
        "profile": profile,
        "schools": ranked,
        "transfer_plan": transfer_plan,
    })


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
