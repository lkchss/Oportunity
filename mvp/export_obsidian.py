"""Export the opportunity store to Obsidian-friendly Markdown.

Writes one note per opportunity (YAML frontmatter + body) plus a dashboard
note with Dataview queries. Frontmatter fields (title, url, category,
fit_grade, priority, deadline) are queryable by the Dataview plugin.

Usage:
    python mvp/export_obsidian.py                       # preview -> mvp/obsidian_export/
    python mvp/export_obsidian.py --vault "C:/path/to/Vault"   # write into vault
    python mvp/export_obsidian.py --vault "..." --subfolder Opportunities
"""
from __future__ import annotations

import argparse
import re
import sqlite3
from pathlib import Path

ROOT = Path(__file__).parent
DB = ROOT / "opportunities.db"
PRIORITY = {"A+": 0, "A": 1, "A-": 2, "B+": 3, "B": 4, "B-": 5, "C+": 6, "C": 7, "C-": 8}
# priority -> grade subfolder (numeric prefix keeps the file tree sorted A+ -> C-)
GRADE_FOLDER = {
    0: "0 - A+ (read first)",
    1: "1 - A",
    2: "2 - A-minus",
    3: "3 - B+",
    4: "4 - B",
    5: "5 - B-minus",
    6: "6 - C+",
    7: "7 - C",
    8: "8 - C-minus",
    9: "9 - ungraded",
}
GRADE_TAG = {
    "A+": "A-plus", "A": "A", "A-": "A-minus",
    "B+": "B-plus", "B": "B", "B-": "B-minus",
    "C+": "C-plus", "C": "C", "C-": "C-minus",
}


def slug(text: str) -> str:
    """Filesystem-safe note filename (Obsidian-friendly)."""
    text = text.replace("->", "to").replace("/", "-").replace("&", "and")
    text = re.sub(r'[\\:*?"<>|#^\[\]]', "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:120]


def yaml_escape(value: str) -> str:
    return '"' + str(value).replace('"', "'") + '"'


def tag_safe(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "-", text).strip("-")


def note(title, grade, deadline, category, url, summary, why, kind="opportunity") -> str:
    prio = PRIORITY.get(grade, 9)
    cat_tag = tag_safe(category)
    grade_tag = GRADE_TAG.get(grade, "ungraded")
    fm = [
        "---",
        f"title: {yaml_escape(title)}",
        f"kind: {yaml_escape(kind)}",
        f"fit_grade: {yaml_escape(grade or '')}",
        f"priority: {prio}",
        f"deadline: {yaml_escape(deadline or '')}",
        f"category: {yaml_escape(category or '')}",
        f"url: {yaml_escape(url or '')}",
        f"tags: [{kind}, grade/{grade_tag}, category/{cat_tag}]",
        "---",
    ]
    body = [
        "",
        f"> [!info] {grade} · {category} · deadline: {deadline or 'n/a'}",
        f"> [Open application / page]({url})",
        "",
        "## Summary",
        summary or "",
        "",
        "## Why it matches",
        why or "",
        "",
    ]
    return "\n".join(fm + body)


def dashboard(tag: str, title: str) -> str:
    return f"""---
tags: [{tag}-dashboard]
---

# {title} Dashboard

> Requires the **Dataview** community plugin (Settings -> Community plugins).
> Each tier has `seen` / `review` subfolders. New finds arrive flat in the tier; drag a note
> into `seen` or `review` to triage it. These views index by tag, across all folders.

## Untriaged (not yet seen/review) - by priority
```dataview
TABLE fit_grade AS Grade, deadline AS Deadline, category AS Category
FROM #{tag}
WHERE !contains(file.folder, "/seen") AND !contains(file.folder, "/review")
SORT priority ASC, file.name ASC
```

## Flagged for review
```dataview
TABLE fit_grade AS Grade, deadline AS Deadline, category AS Category
FROM #{tag}
WHERE contains(file.folder, "/review")
SORT priority ASC, file.name ASC
```

## Read first (A+)
```dataview
TABLE deadline AS Deadline, category AS Category
FROM #{tag}
WHERE fit_grade = "A+"
SORT category ASC
```

## All - by priority
```dataview
TABLE fit_grade AS Grade, deadline AS Deadline, category AS Category
FROM #{tag}
SORT priority ASC, category ASC, file.name ASC
```
"""


def main() -> None:
    ap = argparse.ArgumentParser(description="Export opportunities to Obsidian Markdown.")
    ap.add_argument("--vault", help="path to the Obsidian vault root")
    ap.add_argument("--subfolder", default="Opportunities", help="folder inside the vault (or output dir)")
    ap.add_argument("--out", default=str(ROOT / "obsidian_export"), help="output dir when --vault is omitted")
    ap.add_argument("--by-grade", action="store_true", help="sort notes into grade subfolders")
    ap.add_argument("--add-only", action="store_true",
                    help="only create notes that don't exist yet; never overwrite existing notes")
    args = ap.parse_args()

    # Two parallel trees: opportunities (fellowships/grants/etc) and positions (jobs/roles).
    if args.vault:
        roots = {"opportunity": Path(args.vault) / args.subfolder,
                 "position": Path(args.vault) / "positions"}
    else:
        out = Path(args.out)
        roots = {"opportunity": out, "position": out.with_name(out.name + "-positions")}
    for r in roots.values():
        r.mkdir(parents=True, exist_ok=True)

    # In add-only mode, an existing note (in either tree, any subfolder) is left untouched.
    existing = set()
    if args.add_only:
        for r in roots.values():
            existing |= {p.name for p in r.rglob("*.md")}

    conn = sqlite3.connect(DB)
    rows = conn.execute(
        "SELECT title, url, summary, why_match, category, found_at, fit_grade, deadline, kind "
        "FROM opportunities"
    ).fetchall()

    written = skipped = 0
    for title, url, summary, why, category, found_at, grade, deadline, kind in rows:
        kind = kind if kind in roots else "opportunity"
        fname = f"{slug(title)}.md"
        if args.add_only and fname in existing:
            skipped += 1
            continue
        base = roots[kind]
        if args.by_grade:
            grade_dir = base / GRADE_FOLDER[PRIORITY.get(grade, 9)]
            # seen/ + review/ triage bins; new (untriaged) notes sit FLAT in the tier folder
            for sub in ("seen", "review"):
                (grade_dir / sub).mkdir(parents=True, exist_ok=True)
            target = grade_dir
        else:
            target = base
        target.mkdir(parents=True, exist_ok=True)
        (target / fname).write_text(note(title, grade, deadline, category, url, summary, why, kind), encoding="utf-8")
        written += 1

    # One dashboard per tree (Dataview filters by the kind tag, so subfolders don't matter).
    for kind, title in (("opportunity", "Opportunities"), ("position", "Positions")):
        dash = roots[kind] / f"_{title} Dashboard.md"
        if not (args.add_only and dash.exists()):
            dash.write_text(dashboard(kind, title), encoding="utf-8")
    print(f"Wrote {written} new note(s), skipped {skipped} existing")


if __name__ == "__main__":
    main()
