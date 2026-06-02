"""Entry point: reads profile.json and produces an HTML report.

Typical usage — tell Claude Code "run" and it executes:
    python mvp/run.py
"""
from __future__ import annotations

import datetime
import json
import sys
import webbrowser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from mvp.queries import build_queries
from mvp.report import render
from mvp.scraper import search

PROFILE_PATH = Path(__file__).parent.parent / "profile.json"


def load_profile() -> dict:
    if not PROFILE_PATH.exists():
        raise FileNotFoundError(
            "profile.json not found. Open the portal (python -m streamlit run mvp/portal.py) and save your profile first."
        )
    return json.loads(PROFILE_PATH.read_text(encoding="utf-8"))


def run(profile: dict | None = None, open_browser: bool = True) -> Path:
    if profile is None:
        profile = load_profile()

    category = profile.get("category", "Jobs")
    role = profile.get("role", "")
    field = profile.get("field", "")
    location = profile.get("location", "")
    background = profile.get("background", "")
    goals = profile.get("goals", "")

    queries = build_queries(
        category=category,
        role=role,
        field=field,
        location=location,
        background=background,
        year=datetime.date.today().year,
    )

    print(f"Category: {category}")
    print(f"Searching {len(queries)} queries:")
    for q in queries:
        print(f"  → {q}")
    print()

    results = search(queries)
    print(f"Found {len(results)} results.\n")

    context_summary = f"{background} | Goals: {goals}" if background else goals
    out_dir = Path(__file__).parent.parent / "output"
    out_dir.mkdir(exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = out_dir / f"results_{timestamp}.html"

    render(results, category, context_summary, out_path)
    print(f"Report saved: {out_path}")

    if open_browser:
        webbrowser.open(out_path.as_uri())

    return out_path


if __name__ == "__main__":
    run()
