"""
Run the CURRENT working-tree algorithm over the eval suite and snapshot the
top-N ranking per profile to JSON.

Usage:
    python -m eval.snapshot baseline    # before editing matcher.py
    python -m eval.snapshot candidate   # after editing matcher.py

The two snapshots are then compared by eval.diff. Keeping rankings in files
(not memory) means a snapshot is just "run the code as it exists on disk right
now" — so baseline = git HEAD checkout, candidate = your edited tree.
"""

import json
import sys
from pathlib import Path

from law.data_loader import load_law_schools
from law.matcher import rank_schools
from eval.profiles import build_profiles, profile_summary

_RUNS_DIR = Path(__file__).parent / "runs"
TOP_N = 10

# Component fields surfaced to the judge so it can reason about WHY a school ranks.
_SCORE_FIELDS = [
    "composite_score", "admissibility_score", "admissibility_tier",
    "prestige_score", "career_fit_score", "location_fit_score",
    "scholarship_score", "financial_score",
]


def _compact_school(s: dict) -> dict:
    out = {
        "id": s["id"],
        "name": s["name"],
        "usnwr_rank": s.get("usnwr_rank_2026"),
        "net_debt": s.get("financial_breakdown", {}).get("net_debt"),
    }
    for f in _SCORE_FIELDS:
        out[f] = s.get(f)
    return out


def snapshot(label: str) -> Path:
    schools = load_law_schools()
    profiles = build_profiles()
    result = {}
    for p in profiles:
        ranked = rank_schools(p, schools, top_n=TOP_N)
        result[p["id"]] = {
            "summary": profile_summary(p),
            "top": [_compact_school(s) for s in ranked],
        }
    _RUNS_DIR.mkdir(exist_ok=True)
    out_path = _RUNS_DIR / f"{label}.json"
    out_path.write_text(json.dumps(result, indent=2))
    return out_path


if __name__ == "__main__":
    label = sys.argv[1] if len(sys.argv) > 1 else "candidate"
    path = snapshot(label)
    print(f"wrote {path}")
