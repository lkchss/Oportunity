"""Export the NETWORK-RETREATS list to a single Obsidian tree (projects/lists/network-retreats).

Reuses note/dashboard/slug machinery from export_obsidian.py. Notes tagged #network so the
Network Retreats dashboard's Dataview queries never mix with the other lists. Same grade
subfolders + seen/review triage bins; add-only never overwrites your sorting.

Usage:
    python mvp/export_network.py --vault "C:/.../projects/lists" --subfolder network-retreats --by-grade --add-only
"""
from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

from export_obsidian import slug, note, dashboard, PRIORITY, GRADE_FOLDER

ROOT = Path(__file__).parent
DB = ROOT / "network.db"


def main() -> None:
    ap = argparse.ArgumentParser(description="Export the network-retreats list to Obsidian Markdown.")
    ap.add_argument("--vault", help="path to the Obsidian vault root")
    ap.add_argument("--subfolder", default="network-retreats", help="folder inside the vault (or output dir)")
    ap.add_argument("--out", default=str(ROOT / "network_export"), help="output dir when --vault is omitted")
    ap.add_argument("--by-grade", action="store_true", help="sort notes into grade subfolders")
    ap.add_argument("--add-only", action="store_true",
                    help="only create notes that don't exist yet; never overwrite existing notes")
    args = ap.parse_args()

    base = Path(args.vault) / args.subfolder if args.vault else Path(args.out)
    base.mkdir(parents=True, exist_ok=True)

    existing = {p.name for p in base.rglob("*.md")} if args.add_only else set()

    conn = sqlite3.connect(DB)
    rows = conn.execute(
        "SELECT title, url, summary, why_match, category, found_at, fit_grade, deadline "
        "FROM opportunities"
    ).fetchall()

    written = skipped = 0
    for title, url, summary, why, category, found_at, grade, deadline in rows:
        fname = f"{slug(title)}.md"
        if args.add_only and fname in existing:
            skipped += 1
            continue
        if args.by_grade:
            grade_dir = base / GRADE_FOLDER[PRIORITY.get(grade, 9)]
            for sub in ("seen", "review"):
                (grade_dir / sub).mkdir(parents=True, exist_ok=True)
            target = grade_dir
        else:
            target = base
        target.mkdir(parents=True, exist_ok=True)
        (target / fname).write_text(
            note(title, grade, deadline, category, url, summary, why, kind="network"),
            encoding="utf-8",
        )
        written += 1

    dash = base / "_Network Retreats Dashboard.md"
    if not (args.add_only and dash.exists()):
        dash.write_text(dashboard("network", "Network Retreats"), encoding="utf-8")
    print(f"Wrote {written} new note(s), skipped {skipped} existing")


if __name__ == "__main__":
    main()
