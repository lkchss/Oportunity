"""Unified CLI for the four opportunity lists (opps / horizons / jobs / network).

Replaces the per-list one-off scripts (_grade*.py, export_{horizons,jobs,network}.py).
Each list is a SQLite DB with the same schema; this tool handles the whole loop:

    ingest   -> grade-at-ingest (fit_grade/deadline/status come in the JSON),
                URL-normalized dedupe, batch logged to search_log, file archived
    titles   -> dump known items to feed Claude BEFORE searching (no re-finds)
    stats    -> yield per bucket from search_log (where to search next)
    stale    -> passed-deadline items (re-search candidates next cycle)
    feedback -> read your seen/review triage out of the Obsidian vault back
                into the DB + report which grades/categories you actually pursue
    csv      -> sorted CSV export (Sheets)
    obsidian -> vault export (grade subfolders + seen/review bins, add-only safe)
    regrade  -> bulk grade update from a JSON file, warns on unmatched titles

Ingest JSON: array of objects with keys
    title, url, summary, why_match, category            (required-ish)
    fit_grade, deadline, status, kind                    (optional, grade at search time)

Usage examples:
    python mvp/lists.py opps --ingest results.json --bucket "ai-policy"
    python mvp/lists.py horizons --titles
    python mvp/lists.py jobs --csv
    python mvp/lists.py opps --obsidian --vault "C:/.../Vault" --add-only
    python mvp/lists.py opps --feedback --vault "C:/.../Vault"
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

try:
    from .export_obsidian import GRADE_FOLDER, PRIORITY, dashboard, note, slug
except ImportError:  # run as a script: python mvp/lists.py
    from export_obsidian import GRADE_FOLDER, PRIORITY, dashboard, note, slug

ROOT = Path(__file__).parent
INGESTED_DIR = ROOT / "ingested"
GRADES = ["A+", "A", "A-", "B+", "B", "B-", "C+", "C", "C-"]
TRACKING_KEYS = {"ref", "source", "fbclid", "gclid", "mc_cid", "mc_eid", "igshid"}


@dataclass(frozen=True)
class ListCfg:
    name: str
    db: Path
    csv: Path
    default_kind: str
    subfolder: str          # default vault subfolder
    dashboard_title: str
    csv_header: tuple[str, ...]
    two_trees: bool = False  # opps splits opportunity/position into two vault trees


LISTS: dict[str, ListCfg] = {
    "opps": ListCfg(
        "opps", ROOT / "opportunities.db", ROOT / "opportunities.csv",
        "opportunity", "Opportunities", "Opportunities",
        ("Fit grade", "Est. deadline", "Category", "Title", "URL", "Summary",
         "Why it matches", "Found at", "Status"),
        two_trees=True,
    ),
    "horizons": ListCfg(
        "horizons", ROOT / "horizons.db", ROOT / "horizons.csv",
        "horizon", "horizons", "Horizons",
        ("Springboard", "Timing", "Category", "Title", "URL", "Summary",
         "Why it's worth it", "Found at", "Status"),
    ),
    "jobs": ListCfg(
        "jobs", ROOT / "jobs.db", ROOT / "jobs.csv",
        "job", "jobs", "Jobs",
        ("Fit", "Timing", "Category", "Title", "URL", "Summary",
         "Why it fits", "Found at", "Status"),
    ),
    "network": ListCfg(
        "network", ROOT / "network.db", ROOT / "network.csv",
        "network", "network", "Network",
        ("Network value", "Access", "Category", "Title", "URL", "Summary",
         "Why it's worth it", "Found at", "Status"),
    ),
}


# ---------------------------------------------------------------- schema


def connect(cfg: ListCfg) -> sqlite3.Connection:
    conn = sqlite3.connect(cfg.db)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS opportunities (
            url        TEXT PRIMARY KEY,
            title      TEXT,
            summary    TEXT,
            why_match  TEXT,
            category   TEXT,
            found_at   TEXT,
            fit_grade  TEXT,
            deadline   TEXT,
            kind       TEXT,
            status     TEXT,
            triage     TEXT,
            batch      TEXT
        )
        """
    )
    cols = {r[1] for r in conn.execute("PRAGMA table_info(opportunities)")}
    for col in ("fit_grade", "deadline", "kind", "status", "triage", "batch"):
        if col not in cols:
            conn.execute(f"ALTER TABLE opportunities ADD COLUMN {col} TEXT")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS search_log (
            id          INTEGER PRIMARY KEY,
            ingested_at TEXT,
            batch_file  TEXT,
            bucket      TEXT,
            n_found     INTEGER,
            n_new       INTEGER
        )
        """
    )
    if "status" not in cols:  # column just added: backfill from deadline text
        for url, deadline in conn.execute("SELECT url, deadline FROM opportunities"):
            conn.execute("UPDATE opportunities SET status=? WHERE url=?",
                         (infer_status(deadline), url))
    conn.commit()
    return conn


def infer_status(deadline: str | None, explicit: str | None = None) -> str:
    if explicit:
        return explicit.strip().lower()
    d = (deadline or "").lower()
    if "passed" in d:
        return "passed"
    if "rolling" in d:
        return "rolling"
    return "open" if d else "unknown"


def norm_url(url: str) -> str:
    """Canonical URL for dedupe: lowercase scheme/host, no tracking params,
    no fragment, no trailing slash."""
    p = urlsplit(url.strip())
    query = [(k, v) for k, v in parse_qsl(p.query, keep_blank_values=True)
             if not k.lower().startswith("utm_") and k.lower() not in TRACKING_KEYS]
    path = p.path.rstrip("/")
    return urlunsplit((p.scheme.lower(), p.netloc.lower(), path,
                       urlencode(query), ""))


def known_norm_urls(conn: sqlite3.Connection) -> set[str]:
    return {norm_url(r[0]) for r in conn.execute("SELECT url FROM opportunities")}


# ---------------------------------------------------------------- ingest


def ingest(cfg: ListCfg, conn: sqlite3.Connection, path: Path,
           bucket: str = "", archive: bool = True) -> None:
    if not path.exists():
        raise SystemExit(f"File not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise SystemExit("Results file must be a JSON array of opportunity objects.")

    now = dt.datetime.now().isoformat(timespec="seconds")
    known = known_norm_urls(conn)
    added: list[dict[str, Any]] = []
    ungraded = 0
    for it in data:
        raw = str(it.get("url", "")).strip()
        if not raw:
            continue
        url = norm_url(raw)
        if url in known:
            continue
        grade = str(it.get("fit_grade", "") or "").strip()
        if grade and grade not in GRADES:
            print(f"  ! bad grade {grade!r} on {it.get('title', '?')} — stored ungraded")
            grade = ""
        it["fit_grade"] = grade
        if not grade:
            ungraded += 1
        deadline = str(it.get("deadline", "") or "").strip()
        conn.execute(
            "INSERT INTO opportunities "
            "(url, title, summary, why_match, category, found_at, fit_grade, "
            " deadline, kind, status, batch) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (url, str(it.get("title", "")), str(it.get("summary", "")),
             str(it.get("why_match", "")), str(it.get("category", "")), now,
             grade, deadline, str(it.get("kind", "") or cfg.default_kind),
             infer_status(deadline, it.get("status")), path.name),
        )
        known.add(url)
        added.append(it)

    conn.execute(
        "INSERT INTO search_log (ingested_at, batch_file, bucket, n_found, n_new) "
        "VALUES (?,?,?,?,?)", (now, path.name, bucket, len(data), len(added)),
    )
    conn.commit()

    total = conn.execute("SELECT COUNT(*) FROM opportunities").fetchone()[0]
    print(f"{len(data)} ingested, {len(added)} new (DB now {total}).")
    for it in added:
        g = it.get("fit_grade", "") or "ungraded"
        print(f"  + [{g}] [{it.get('category', '')}] {it.get('title', '(untitled)')}")
    if ungraded:
        print(f"  ! {ungraded} new item(s) arrived UNGRADED — "
              "include fit_grade + deadline in the search JSON next time.")

    if archive:
        INGESTED_DIR.mkdir(exist_ok=True)
        dest = INGESTED_DIR / path.name
        if dest.exists():
            dest = INGESTED_DIR / f"{path.stem}_{now.replace(':', '')}{path.suffix}"
        path.rename(dest)
        print(f"  archived -> {dest}")


def regrade(conn: sqlite3.Connection, path: Path) -> None:
    """Bulk grade update. JSON: {title: [grade, deadline]} or
    [{title, fit_grade, deadline, status?}]. Warns on every unmatched title."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    items: list[tuple[str, str, str, str | None]] = []
    if isinstance(raw, dict):
        items = [(t, g, d, None) for t, (g, d) in raw.items()]
    else:
        items = [(it["title"], it.get("fit_grade", ""), it.get("deadline", ""),
                  it.get("status")) for it in raw]

    db_titles = {r[0] for r in conn.execute("SELECT title FROM opportunities")}
    unmatched = []
    for title, grade, deadline, status in items:
        if title not in db_titles:
            unmatched.append(title)
            continue
        conn.execute(
            "UPDATE opportunities SET fit_grade=?, deadline=?, status=? WHERE title=?",
            (grade, deadline, infer_status(deadline, status), title),
        )
    conn.commit()
    print(f"{len(items) - len(unmatched)} updated.")
    if unmatched:
        print("!! UNMATCHED (no DB row with this title):")
        for t in unmatched:
            print("   ", t)


# ---------------------------------------------------------------- reports


def dump_titles(conn: sqlite3.Connection) -> None:
    """Known-items dump to paste into Claude's context BEFORE searching."""
    rows = conn.execute(
        "SELECT category, title, url FROM opportunities ORDER BY category, title"
    ).fetchall()
    print(f"# {len(rows)} known items — do NOT re-find these:")
    for category, title, url in rows:
        print(f"- [{category}] {title} | {url}")


def stats(conn: sqlite3.Connection) -> None:
    rows = conn.execute(
        "SELECT COALESCE(NULLIF(bucket, ''), '(no bucket)'), COUNT(*), "
        "SUM(n_found), SUM(n_new), MAX(ingested_at) "
        "FROM search_log GROUP BY 1 ORDER BY SUM(n_new) DESC"
    ).fetchall()
    if not rows:
        print("No search_log yet — pass --bucket on ingest to start tracking yield.")
        return
    print(f"{'bucket':30} {'batches':>7} {'found':>6} {'new':>5} {'new%':>5}  last")
    for bucket, n, found, new, last in rows:
        pct = f"{100 * (new or 0) / found:.0f}%" if found else "-"
        print(f"{bucket:30} {n:>7} {found or 0:>6} {new or 0:>5} {pct:>5}  {last}")


def stale(conn: sqlite3.Connection) -> None:
    """Passed-deadline items, best grades first — re-search these next cycle."""
    order = {g: i for i, g in enumerate(GRADES)}
    rows = conn.execute(
        "SELECT fit_grade, deadline, title FROM opportunities WHERE status='passed'"
    ).fetchall()
    rows.sort(key=lambda r: order.get(r[0], 99))
    if not rows:
        print("Nothing stale.")
        return
    print(f"{len(rows)} passed-deadline item(s) — candidates to re-check for next cycle:")
    for grade, deadline, title in rows:
        print(f"  [{grade or '?'}] {title} — {deadline}")


# ---------------------------------------------------------------- exports


def export_csv(cfg: ListCfg, conn: sqlite3.Connection) -> None:
    import csv as csv_mod
    order = {g: i for i, g in enumerate(GRADES)}
    rows = conn.execute(
        "SELECT fit_grade, deadline, category, title, url, summary, why_match, "
        "found_at, status FROM opportunities"
    ).fetchall()
    rows.sort(key=lambda r: (order.get(r[0], 99), r[2] or "", r[3] or ""))
    with open(cfg.csv, "w", newline="", encoding="utf-8-sig") as f:
        w = csv_mod.writer(f)
        w.writerow(cfg.csv_header)
        w.writerows(rows)
    print(f"CSV rows: {len(rows)} -> {cfg.csv.name}")
    print(" / ".join(f"{g} {sum(1 for r in rows if r[0] == g)}" for g in GRADES))


def _vault_roots(cfg: ListCfg, vault: str | None, subfolder: str | None,
                 out: str | None) -> dict[str, Path]:
    sub = subfolder or cfg.subfolder
    if vault:
        base = Path(vault) / sub
    else:
        base = Path(out) if out else ROOT / f"{cfg.name}_export"
    if cfg.two_trees:
        pos = Path(vault) / "positions" if vault else base.with_name(base.name + "-positions")
        return {"opportunity": base, "position": pos}
    return {cfg.default_kind: base}


def export_vault(cfg: ListCfg, conn: sqlite3.Connection, vault: str | None,
                 subfolder: str | None, out: str | None, by_grade: bool,
                 add_only: bool) -> None:
    roots = _vault_roots(cfg, vault, subfolder, out)
    for r in roots.values():
        r.mkdir(parents=True, exist_ok=True)

    existing: set[str] = set()
    if add_only:
        for r in roots.values():
            existing |= {p.name for p in r.rglob("*.md")}

    rows = conn.execute(
        "SELECT title, url, summary, why_match, category, fit_grade, deadline, kind "
        "FROM opportunities"
    ).fetchall()

    written = skipped = 0
    for title, url, summary, why, category, grade, deadline, kind in rows:
        kind = kind if kind in roots else cfg.default_kind
        fname = f"{slug(title)}.md"
        if add_only and fname in existing:
            skipped += 1
            continue
        target = roots[kind]
        if by_grade:
            target = target / GRADE_FOLDER[PRIORITY.get(grade, 9)]
            for sub in ("seen", "review"):
                (target / sub).mkdir(parents=True, exist_ok=True)
        target.mkdir(parents=True, exist_ok=True)
        (target / fname).write_text(
            note(title, grade, deadline, category, url, summary, why, kind),
            encoding="utf-8",
        )
        written += 1

    for kind, root in roots.items():
        title = cfg.dashboard_title if kind == cfg.default_kind else "Positions"
        dash = root / f"_{title} Dashboard.md"
        if not (add_only and dash.exists()):
            dash.write_text(dashboard(kind, title), encoding="utf-8")
    print(f"Wrote {written} new note(s), skipped {skipped} existing")


# ---------------------------------------------------------------- feedback


def feedback(cfg: ListCfg, conn: sqlite3.Connection, vault: str | None,
             subfolder: str | None, out: str | None) -> None:
    """Read seen/review triage out of the vault back into the DB, then report
    which grades/categories actually get pursued — recalibration signal for
    both the grading rubric and where to point the next searches."""
    roots = _vault_roots(cfg, vault, subfolder, out)
    by_fname = {f"{slug(t)}.md": u for u, t in
                conn.execute("SELECT url, title FROM opportunities")}

    n_matched = 0
    for root in roots.values():
        if not root.exists():
            continue
        for p in root.rglob("*.md"):
            if p.name.startswith("_"):
                continue
            url = by_fname.get(p.name)
            if not url:
                continue
            parent = p.parent.name
            triage = parent if parent in ("seen", "review") else "untriaged"
            conn.execute("UPDATE opportunities SET triage=? WHERE url=?", (triage, url))
            n_matched += 1
    conn.commit()

    counts = dict(conn.execute(
        "SELECT COALESCE(triage, 'unexported'), COUNT(*) FROM opportunities GROUP BY 1"
    ).fetchall())
    print(f"Synced triage for {n_matched} note(s).")
    print("  " + " / ".join(f"{k}: {v}" for k, v in sorted(counts.items())))

    def rates(col: str) -> list[tuple[str, int, int, int]]:
        return conn.execute(
            f"SELECT COALESCE(NULLIF({col}, ''), '?'), "
            "SUM(triage='review'), SUM(triage='seen'), COUNT(*) "
            "FROM opportunities WHERE triage IS NOT NULL "
            f"GROUP BY 1 ORDER BY SUM(triage='review') DESC"
        ).fetchall()

    if counts.get("review") or counts.get("seen"):
        gorder = {g: i for i, g in enumerate(GRADES)}
        print("\nReview-rate by grade (what your triage says the grades should be):")
        for grade, rev, seen, n in sorted(rates("fit_grade"),
                                          key=lambda r: gorder.get(r[0], 99)):
            print(f"  {grade:4} review {rev}/{n}, seen {seen}/{n}")
        print("\nReview-rate by category (where to point the next searches):")
        for cat, rev, seen, n in rates("category"):
            print(f"  {cat:35} review {rev}/{n}, seen {seen}/{n}")
    else:
        print("No seen/review triage found in the vault yet — sort some notes first.")


# ---------------------------------------------------------------- main


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("list", choices=sorted(LISTS), help="which list to operate on")
    ap.add_argument("--ingest", metavar="FILE", help="ingest a JSON array of results")
    ap.add_argument("--bucket", default="", help="search bucket label for search_log")
    ap.add_argument("--no-archive", action="store_true",
                    help="don't move the ingested file to mvp/ingested/")
    ap.add_argument("--regrade", metavar="FILE", help="bulk grade update from JSON")
    ap.add_argument("--titles", action="store_true", help="dump known items (pre-search context)")
    ap.add_argument("--stats", action="store_true", help="yield per bucket from search_log")
    ap.add_argument("--stale", action="store_true", help="passed-deadline items")
    ap.add_argument("--csv", action="store_true", help="export sorted CSV")
    ap.add_argument("--obsidian", action="store_true", help="export to Obsidian vault")
    ap.add_argument("--feedback", action="store_true",
                    help="sync vault triage back into the DB + report")
    ap.add_argument("--vault", help="Obsidian vault root (for --obsidian/--feedback)")
    ap.add_argument("--subfolder", help="vault subfolder (default per list)")
    ap.add_argument("--out", help="output dir when --vault omitted")
    ap.add_argument("--flat", action="store_true",
                    help="obsidian: no grade subfolders (default is by-grade)")
    ap.add_argument("--overwrite", action="store_true",
                    help="obsidian: overwrite existing notes (default is add-only)")
    ap.add_argument("--count", action="store_true", help="print row count")
    args = ap.parse_args()

    cfg = LISTS[args.list]
    conn = connect(cfg)

    ran = False
    if args.ingest:
        ingest(cfg, conn, Path(args.ingest), args.bucket, archive=not args.no_archive)
        ran = True
    if args.regrade:
        regrade(conn, Path(args.regrade))
        ran = True
    if args.titles:
        dump_titles(conn)
        ran = True
    if args.stats:
        stats(conn)
        ran = True
    if args.stale:
        stale(conn)
        ran = True
    if args.csv:
        export_csv(cfg, conn)
        ran = True
    if args.obsidian:
        export_vault(cfg, conn, args.vault, args.subfolder, args.out,
                     by_grade=not args.flat, add_only=not args.overwrite)
        ran = True
    if args.feedback:
        feedback(cfg, conn, args.vault, args.subfolder, args.out)
        ran = True
    if args.count:
        print(conn.execute("SELECT COUNT(*) FROM opportunities").fetchone()[0])
        ran = True
    if not ran:
        ap.print_help()


if __name__ == "__main__":
    main()
