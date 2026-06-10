"""Personal opportunity store.

SUPERSEDED by lists.py (unified CLI for all four lists: ingest w/ grade-at-ingest,
URL-normalized dedupe, search_log, stale report, vault feedback). Kept for
back-compat; prefer:  python mvp/lists.py opps --ingest results.json

Holds opportunities that Claude Code finds for you (via your Claude Pro account)
in a local SQLite database (``opportunities.db``), keyed on URL so the same
opportunity is never saved twice.

This file does NOT call the Anthropic API — the searching is done by Claude Code
during a session. Claude writes the results it finds to a JSON file and ingests
them here. You drive it by asking Claude (in a Claude Code session) to "find more
opportunities"; Claude reads ``profile.txt``, searches the web, and ingests.

Commands:
    python mvp/finder.py --ingest results.json   # save a JSON array of opportunities
    python mvp/finder.py --list                  # print everything saved so far
    python mvp/finder.py --count                 # print how many are saved

A results JSON file is an array of objects, each with keys:
    title, url, summary, why_match, category
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sqlite3
from pathlib import Path
from typing import Any

ROOT = Path(__file__).parent
PROFILE_PATH = ROOT / "profile.txt"
DB_PATH = ROOT / "opportunities.db"


def init_db(db_path: Path = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS opportunities (
            url        TEXT PRIMARY KEY,
            title      TEXT,
            summary    TEXT,
            why_match  TEXT,
            category   TEXT,
            found_at   TEXT
        )
        """
    )
    conn.commit()
    return conn


def known_urls(conn: sqlite3.Connection) -> set[str]:
    return {row[0] for row in conn.execute("SELECT url FROM opportunities")}


def save(conn: sqlite3.Connection, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Insert items, skipping URLs already stored. Returns the newly-added items."""
    now = dt.datetime.now().isoformat(timespec="seconds")
    added: list[dict[str, Any]] = []
    for it in items:
        url = str(it.get("url", "")).strip()
        if not url:
            continue
        cur = conn.execute(
            "INSERT OR IGNORE INTO opportunities "
            "(url, title, summary, why_match, category, found_at) VALUES (?, ?, ?, ?, ?, ?)",
            (
                url,
                str(it.get("title", "")),
                str(it.get("summary", "")),
                str(it.get("why_match", "")),
                str(it.get("category", "")),
                now,
            ),
        )
        if cur.rowcount:
            added.append(it)
    conn.commit()
    return added


def ingest(conn: sqlite3.Connection, path: Path) -> None:
    if not path.exists():
        raise SystemExit(f"File not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise SystemExit("Results file must be a JSON array of opportunity objects.")
    added = save(conn, data)
    total = conn.execute("SELECT COUNT(*) FROM opportunities").fetchone()[0]
    print(f"{len(data)} ingested, {len(added)} new (DB now {total}).")
    for it in added:
        print(f"  + [{it.get('category', '')}] {it.get('title', '(untitled)')}")
        print(f"    {it.get('url', '')}")


def list_saved(conn: sqlite3.Connection) -> None:
    rows = conn.execute(
        "SELECT found_at, category, title, url, why_match "
        "FROM opportunities ORDER BY found_at DESC"
    ).fetchall()
    if not rows:
        print("No opportunities saved yet.")
        return
    print(f"{len(rows)} saved opportunities:\n")
    for found_at, category, title, url, why in rows:
        print(f"[{found_at}] ({category}) {title}")
        print(f"  {url}")
        if why:
            print(f"  why: {why}")
        print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Personal opportunity store.")
    parser.add_argument("--ingest", metavar="FILE", help="save a JSON array of opportunities")
    parser.add_argument("--list", action="store_true", help="print saved opportunities")
    parser.add_argument("--count", action="store_true", help="print how many are saved")
    parser.add_argument("--db", help="path to the SQLite DB (default: opportunities.db)")
    args = parser.parse_args()

    conn = init_db(Path(args.db) if args.db else DB_PATH)

    if args.ingest:
        ingest(conn, Path(args.ingest))
    elif args.list:
        list_saved(conn)
    elif args.count:
        print(conn.execute("SELECT COUNT(*) FROM opportunities").fetchone()[0])
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
