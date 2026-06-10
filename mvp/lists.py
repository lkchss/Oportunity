"""Unified CLI for the four opportunity lists (opps / horizons / jobs / network).

Replaces the per-list one-off scripts (_grade*.py, export_{horizons,jobs,network}.py).
Each list is a SQLite DB with the same schema; this tool handles the whole loop:

    ingest   -> grade-at-ingest (fit_grade/deadline/status come in the JSON),
                URL-normalized dedupe, batch logged to search_log, file archived.
                Known URLs arriving with a CHANGED deadline/status are refreshed
                in place (new cycle of an annual program), not dropped.
    titles   -> dump known items to feed Claude BEFORE searching (no re-finds);
                --category filters the dump to the slice being searched
    stats    -> yield per bucket from search_log (where to search next)
    batches  -> recent batches with their query strings (spot stale phrasing)
    stale    -> passed-deadline items (re-search candidates next cycle)
    recheck  -> open/rolling items not verified in N days (annual-cycle blindspot)
    sources  -> low-SEO hub registry (aggregators / X / Reddit / LinkedIn) to
                browse directly each cycle; --checked URL bumps last_checked
    canary   -> ground-truth set: opportunities learned of out-of-band; -check
                reports which ones the search loop found (recall measure)
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
DRY_STREAK = 5  # consecutive zero-new batches before a bucket is called dry
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
            batch      TEXT,
            checked_at TEXT
        )
        """
    )
    cols = {r[1] for r in conn.execute("PRAGMA table_info(opportunities)")}
    for col in ("fit_grade", "deadline", "kind", "status", "triage", "batch",
                "checked_at"):
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
            n_new       INTEGER,
            queries     TEXT,
            n_refreshed INTEGER
        )
        """
    )
    slog_cols = {r[1] for r in conn.execute("PRAGMA table_info(search_log)")}
    if "queries" not in slog_cols:
        conn.execute("ALTER TABLE search_log ADD COLUMN queries TEXT")
    if "n_refreshed" not in slog_cols:
        conn.execute("ALTER TABLE search_log ADD COLUMN n_refreshed INTEGER")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS sources (
            url          TEXT PRIMARY KEY,
            label        TEXT,
            bucket       TEXT,
            kind         TEXT,
            note         TEXT,
            added_at     TEXT,
            last_checked TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS canaries (
            url      TEXT PRIMARY KEY,
            title    TEXT,
            via      TEXT,
            added_at TEXT,
            found_at TEXT
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


def known_state(conn: sqlite3.Connection) -> dict[str, tuple[str, str, str]]:
    """norm_url -> (stored url, deadline, status) for the refresh-on-reingest path."""
    return {norm_url(u): (u, d or "", s or "") for u, d, s in
            conn.execute("SELECT url, deadline, status FROM opportunities")}


# ---------------------------------------------------------------- ingest


def ingest(cfg: ListCfg, conn: sqlite3.Connection, path: Path,
           bucket: str = "", archive: bool = True, queries: str = "") -> None:
    if not path.exists():
        raise SystemExit(f"File not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise SystemExit("Results file must be a JSON array of opportunity objects.")

    now = dt.datetime.now().isoformat(timespec="seconds")
    known = known_state(conn)
    added: list[dict[str, Any]] = []
    refreshed: list[str] = []
    ungraded = 0
    for it in data:
        raw = str(it.get("url", "")).strip()
        if not raw:
            continue
        url = norm_url(raw)
        grade = str(it.get("fit_grade", "") or "").strip()
        if grade and grade not in GRADES:
            print(f"  ! bad grade {grade!r} on {it.get('title', '?')} — stored ungraded")
            grade = ""
        it["fit_grade"] = grade
        deadline = str(it.get("deadline", "") or "").strip()
        status = infer_status(deadline, it.get("status"))
        if url in known:
            stored_url, old_deadline, old_status = known[url]
            changed = (deadline and deadline != old_deadline) or \
                (it.get("status") and status != old_status)
            if changed:
                # same URL, new cycle: annual programs reuse their apply page.
                # Grades deliberately don't refresh on their own — curated
                # regrades shouldn't be clobbered by a search batch (--regrade
                # is the grade-correction path).
                conn.execute(
                    "UPDATE opportunities SET "
                    "deadline=COALESCE(NULLIF(?, ''), deadline), status=?, "
                    "checked_at=?, batch=?, "
                    "fit_grade=COALESCE(NULLIF(?, ''), fit_grade) WHERE url=?",
                    (deadline, status, now, path.name, grade, stored_url),
                )
                known[url] = (stored_url, deadline or old_deadline, status)
                refreshed.append(
                    f"{it.get('title', '(untitled)')}: "
                    f"'{old_deadline}' [{old_status}] -> "
                    f"'{deadline or old_deadline}' [{status}]")
            continue
        if not grade:
            ungraded += 1
        conn.execute(
            "INSERT INTO opportunities "
            "(url, title, summary, why_match, category, found_at, fit_grade, "
            " deadline, kind, status, batch, checked_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (url, str(it.get("title", "")), str(it.get("summary", "")),
             str(it.get("why_match", "")), str(it.get("category", "")), now,
             grade, deadline, str(it.get("kind", "") or cfg.default_kind),
             status, path.name, now),
        )
        known[url] = (url, deadline, status)
        added.append(it)

    conn.execute(
        "INSERT INTO search_log (ingested_at, batch_file, bucket, n_found, n_new, "
        "queries, n_refreshed) VALUES (?,?,?,?,?,?,?)",
        (now, path.name, bucket, len(data), len(added), queries, len(refreshed)),
    )
    conn.commit()

    total = conn.execute("SELECT COUNT(*) FROM opportunities").fetchone()[0]
    print(f"{len(data)} ingested, {len(added)} new, {len(refreshed)} refreshed "
          f"(DB now {total}).")
    for it in added:
        g = it.get("fit_grade", "") or "ungraded"
        print(f"  + [{g}] [{it.get('category', '')}] {it.get('title', '(untitled)')}")
    for entry in refreshed:
        print(f"  ~ refreshed: {entry}")
    if ungraded:
        print(f"  ! {ungraded} new item(s) arrived UNGRADED — "
              "include fit_grade + deadline in the search JSON next time.")
    if bucket and not added and not refreshed:
        streak = dry_streak(conn, bucket)
        if streak >= DRY_STREAK:
            print(f"  !! bucket '{bucket}' looks DRY: {streak} straight batches "
                  "with 0 new. Check --batches for repeated phrasing; rotate "
                  "queries or retire the bucket.")

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
    now = dt.datetime.now().isoformat(timespec="seconds")
    unmatched = []
    for title, grade, deadline, status in items:
        if title not in db_titles:
            unmatched.append(title)
            continue
        conn.execute(
            "UPDATE opportunities SET fit_grade=?, deadline=?, status=?, "
            "checked_at=? WHERE title=?",
            (grade, deadline, infer_status(deadline, status), now, title),
        )
    conn.commit()
    print(f"{len(items) - len(unmatched)} updated.")
    if unmatched:
        print("!! UNMATCHED (no DB row with this title):")
        for t in unmatched:
            print("   ", t)


# ---------------------------------------------------------------- reports


def dump_titles(conn: sqlite3.Connection, category: str = "") -> None:
    """Known-items dump to paste into Claude's context BEFORE searching.
    --category filters to the slice being searched (full dump bloats context
    as the DB grows)."""
    if category:
        rows = conn.execute(
            "SELECT category, title, url FROM opportunities "
            "WHERE category LIKE ? ORDER BY category, title",
            (f"%{category}%",),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT category, title, url FROM opportunities ORDER BY category, title"
        ).fetchall()
    scope = f" matching category '{category}'" if category else ""
    print(f"# {len(rows)} known items{scope}. Search rules:")
    print("# - Do NOT re-list these unchanged.")
    print("# - DO re-submit a known item if its cycle re-opened or its deadline")
    print("#   changed — ingest refreshes the stored row in place.")
    print("# - Include borderline finds as C-tier instead of dropping them;")
    print("#   never silently filter (triage feedback can't correct what it never sees).")
    print("# - Rotate query phrasing each cycle (fellowship/residency/open call/RFP/")
    print("#   cohort/'applications open'/'now accepting') and date-restrict for freshness.")
    for category_, title, url in rows:
        print(f"- [{category_}] {title} | {url}")


def dry_streak(conn: sqlite3.Connection, bucket: str) -> int:
    """Consecutive most-recent batches in this bucket that produced neither new
    nor refreshed items (refresh-only cycles are productive, not dry)."""
    streak = 0
    for (yield_,) in conn.execute(
            "SELECT n_new + COALESCE(n_refreshed, 0) FROM search_log "
            "WHERE bucket=? ORDER BY id DESC", (bucket,)):
        if yield_:
            break
        streak += 1
    return streak


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
    dry: list[str] = []
    for bucket, n, found, new, last in rows:
        pct = f"{100 * (new or 0) / found:.0f}%" if found else "-"
        flag = ""
        if bucket != "(no bucket)" and dry_streak(conn, bucket) >= DRY_STREAK:
            flag = "  DRY"
            dry.append(bucket)
        print(f"{bucket:30} {n:>7} {found or 0:>6} {new or 0:>5} {pct:>5}  {last}{flag}")
    if dry:
        print(f"\nDRY = {DRY_STREAK}+ straight zero-new batches. Before retiring, "
              "check --batches: same phrasing repeated means stale queries, "
              "not an empty bucket.")


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


def recheck(conn: sqlite3.Connection, age_days: int) -> None:
    """Open/rolling/unknown items not verified in age_days. Annual programs reuse
    the same URL, so without this they'd never resurface once ingested; --stale
    only catches status='passed'."""
    cutoff = (dt.datetime.now() - dt.timedelta(days=age_days)).isoformat(
        timespec="seconds")
    order = {g: i for i, g in enumerate(GRADES)}
    rows = conn.execute(
        "SELECT fit_grade, status, deadline, title, "
        "COALESCE(NULLIF(checked_at, ''), found_at) AS seen "
        "FROM opportunities WHERE COALESCE(status, '') != 'passed' AND seen < ?",
        (cutoff,),
    ).fetchall()
    rows.sort(key=lambda r: (order.get(r[0], 99), r[4]))
    if not rows:
        print(f"Nothing unverified for {age_days}+ days.")
        return
    print(f"{len(rows)} item(s) not verified in {age_days}+ days — re-check these "
          "(a re-ingest with a changed deadline, or --regrade, marks them verified):")
    for grade, status, deadline, title, seen in rows:
        print(f"  [{grade or '?'}] [{status or '?'}] {title} — {deadline or 'no deadline'}"
              f" (last verified {seen[:10]})")


def batches(conn: sqlite3.Connection, limit: int = 20) -> None:
    """Recent batches with their query strings. Low new% on REPEATED phrasing
    means stale queries, not an exhausted bucket — rotate before retiring."""
    rows = conn.execute(
        "SELECT ingested_at, bucket, n_found, n_new, queries FROM search_log "
        "ORDER BY id DESC LIMIT ?", (limit,),
    ).fetchall()
    if not rows:
        print("No search_log yet.")
        return
    for ingested_at, bucket, found, new, queries in rows:
        print(f"{ingested_at}  [{bucket or 'no bucket'}]  {new}/{found} new")
        if queries:
            for q in queries.split("|"):
                print(f"    ? {q.strip()}")
        else:
            print("    (no queries logged — pass --queries 'q1 | q2' on ingest)")


# ---------------------------------------------------------------- sources

# Low-SEO hubs to browse DIRECTLY each cycle — listings here often never rank
# in web search. kind drives the fetch hint:
#   aggregator -> fetch the page directly
#   x          -> WebSearch with allowed_domains [x.com, twitter.com, nitter.net]
#   reddit     -> fetch is blocked (400); WebSearch `site:reddit.com ...` instead
#   linkedin   -> login-walled; WebSearch `site:linkedin.com ...` instead
KIND_HINT = {
    "aggregator": "fetch directly",
    "x": "WebSearch allowed_domains [x.com, twitter.com, nitter.net]",
    "reddit": "fetch BLOCKED — WebSearch site:reddit.com instead",
    "linkedin": "login-walled — WebSearch site:linkedin.com instead",
}

SEED_SOURCES: dict[str, list[tuple[str, str, str, str]]] = {
    # (url, label, kind, note)
    "opps": [
        ("https://www.profellow.com/fellowships/", "ProFellow directory",
         "aggregator", "fellowship database; filter by field/deadline"),
        ("https://opportunitydesk.org/", "Opportunity Desk",
         "aggregator", "daily fellowship/grant/competition feed"),
        ("https://www.f6s.com/programs", "F6S programs",
         "aggregator", "accelerators, founder programs, startup grants"),
        ("https://www.gjopen.com/", "Good Judgment Open",
         "aggregator", "live forecasting challenges"),
        ("https://www.metaculus.com/tournaments/", "Metaculus tournaments",
         "aggregator", "forecasting tournaments with prizes"),
        ("https://x.com/search?q=%22applications%20are%20open%22%20fellowship&f=live",
         "X live: 'applications are open' fellowship", "x",
         "rotate the quoted phrase: 'now accepting', 'apply by', 'cohort'"),
        ("https://www.reddit.com/r/fellowships/", "r/fellowships",
         "reddit", "also try site:reddit.com 'fellowship' 'applications open'"),
        ("https://www.linkedin.com/jobs/search/?keywords=fellowship",
         "LinkedIn fellowship posts", "linkedin",
         "fellowships posted as jobs never rank in normal web search"),
    ],
    "horizons": [
        ("https://resartis.org/listings/", "Res Artis open calls",
         "aggregator", "global residency open calls"),
        ("https://www.transartists.org/en/calls", "TransArtists calls",
         "aggregator", "residency open calls + deadlines"),
        ("https://artistcommunities.org/residencies", "Artist Communities Alliance",
         "aggregator", "US residency directory"),
        ("https://x.com/search?q=%22open%20call%22%20residency&f=live",
         "X live: 'open call' residency", "x",
         "catches just-announced residencies/explorations before sites index them"),
    ],
    "jobs": [
        ("https://jobs.80000hours.org/", "80,000 Hours job board",
         "aggregator", "policy/AI/research-adjacent roles"),
        ("https://www.workatastartup.com/", "YC Work at a Startup",
         "aggregator", "YC startup roles, often unposted elsewhere"),
        ("https://wellfound.com/jobs", "Wellfound",
         "aggregator", "startup roles incl. founding/early ops"),
        ("https://www.linkedin.com/jobs/", "LinkedIn jobs",
         "linkedin", "chief-of-staff/BizOps roles often LinkedIn-only"),
    ],
    "network": [
        ("https://www.joinondeck.com/", "On Deck",
         "aggregator", "cohort communities, rolling admissions"),
        ("https://joininteract.com/", "Interact",
         "aggregator", "tech fellowship community, annual cohort"),
        ("https://www.southparkcommons.com/", "South Park Commons",
         "aggregator", "founder/-1 to 0 community"),
        ("https://www.kernel.community/", "Kernel",
         "aggregator", "peer-learning cohorts (web3-leaning but broad)"),
        ("https://x.com/search?q=retreat%20%22applications%20open%22&f=live",
         "X live: retreat 'applications open'", "x",
         "small retreats announce on X only"),
    ],
}


def seed_sources(cfg: ListCfg, conn: sqlite3.Connection) -> None:
    now = dt.datetime.now().isoformat(timespec="seconds")
    n = 0
    for url, label, kind, note in SEED_SOURCES.get(cfg.name, []):
        cur = conn.execute(
            "INSERT OR IGNORE INTO sources (url, label, bucket, kind, note, added_at) "
            "VALUES (?,?,?,?,?,?)", (url, label, "", kind, note, now),
        )
        n += cur.rowcount
    conn.commit()
    print(f"{n} seed source(s) added ({len(SEED_SOURCES.get(cfg.name, []))} defined).")


def add_source(conn: sqlite3.Connection, url: str, label: str, bucket: str,
               kind: str, note: str) -> None:
    now = dt.datetime.now().isoformat(timespec="seconds")
    conn.execute(
        "INSERT OR REPLACE INTO sources (url, label, bucket, kind, note, added_at, "
        "last_checked) VALUES (?,?,?,?,?,?, "
        "(SELECT last_checked FROM sources WHERE url=?))",
        (url, label or url, bucket, kind, note, now, url),
    )
    conn.commit()
    print(f"Source saved: [{kind}] {label or url}")


def list_sources(conn: sqlite3.Connection) -> None:
    """Hub checklist for Claude, oldest-checked first. Browse these each cycle —
    they hold the listings web search never surfaces."""
    rows = conn.execute(
        "SELECT url, label, bucket, kind, note, last_checked FROM sources "
        "ORDER BY last_checked IS NOT NULL, last_checked, label"
    ).fetchall()
    if not rows:
        print("No sources yet — run --seed-sources, then --add-source URL to grow it.")
        return
    print(f"# {len(rows)} source(s), least-recently-checked first. Browse each, then")
    print("# mark done: lists.py <list> --checked URL [URL ...]")
    for url, label, bucket, kind, note, last in rows:
        when = last[:10] if last else "NEVER"
        b = f" ({bucket})" if bucket else ""
        print(f"- [{kind}]{b} {label} — last checked {when}")
        print(f"    {url}")
        print(f"    how: {KIND_HINT.get(kind, 'fetch directly')}"
              + (f" | {note}" if note else ""))


def mark_checked(conn: sqlite3.Connection, urls: list[str]) -> None:
    now = dt.datetime.now().isoformat(timespec="seconds")
    n = 0
    for url in urls:
        cur = conn.execute("UPDATE sources SET last_checked=? WHERE url=?", (now, url))
        if not cur.rowcount:
            print(f"  ! no source with url {url}")
        n += cur.rowcount
    conn.commit()
    print(f"{n} source(s) marked checked.")


# ---------------------------------------------------------------- canaries


def canary_add(conn: sqlite3.Connection, url: str, title: str, via: str) -> None:
    """Register an opportunity learned of OUT-OF-BAND (newsletter, friend, feed).
    --canary-check later reports whether the search loop found it on its own."""
    now = dt.datetime.now().isoformat(timespec="seconds")
    conn.execute(
        "INSERT OR REPLACE INTO canaries (url, title, via, added_at, found_at) "
        "VALUES (?,?,?,?, (SELECT found_at FROM canaries WHERE url=?))",
        (norm_url(url), title, via, now, norm_url(url)),
    )
    conn.commit()
    print(f"Canary added: {title or url}")


def canary_check(conn: sqlite3.Connection) -> None:
    now = dt.datetime.now().isoformat(timespec="seconds")
    known = known_norm_urls(conn)
    rows = conn.execute(
        "SELECT url, title, via, found_at FROM canaries").fetchall()
    if not rows:
        print("No canaries yet — add out-of-band finds with "
              "--canary URL --title T --via 'newsletter X'.")
        return
    hits = 0
    misses: list[tuple[str, str, str]] = []
    for url, title, via, found_at in rows:
        if found_at:
            hits += 1
        elif norm_url(url) in known:
            conn.execute("UPDATE canaries SET found_at=? WHERE url=?", (now, url))
            hits += 1
        else:
            misses.append((url, title, via))
    conn.commit()
    print(f"Recall: {hits}/{len(rows)} canaries found by the loop.")
    if misses:
        print("MISSED — diagnose each (phrasing? unindexed hub? filtered at grading?):")
        for url, title, via in misses:
            print(f"  - {title or url} (via {via or '?'})\n    {url}")


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
    ap.add_argument("--queries", default="",
                    help="'|'-separated query strings used this batch (for --batches)")
    ap.add_argument("--no-archive", action="store_true",
                    help="don't move the ingested file to mvp/ingested/")
    ap.add_argument("--regrade", metavar="FILE", help="bulk grade update from JSON")
    ap.add_argument("--titles", action="store_true", help="dump known items (pre-search context)")
    ap.add_argument("--category", default="",
                    help="filter --titles to categories containing this substring")
    ap.add_argument("--stats", action="store_true", help="yield per bucket from search_log")
    ap.add_argument("--batches", action="store_true",
                    help="recent batches with their query strings")
    ap.add_argument("--stale", action="store_true", help="passed-deadline items")
    ap.add_argument("--recheck", action="store_true",
                    help="open items not verified in --age-days")
    ap.add_argument("--age-days", type=int, default=180,
                    help="staleness window for --recheck (default 180)")
    ap.add_argument("--sources", action="store_true",
                    help="hub checklist (aggregators/X/Reddit/LinkedIn), oldest first")
    ap.add_argument("--seed-sources", action="store_true",
                    help="insert the built-in starter hubs for this list")
    ap.add_argument("--add-source", metavar="URL", help="register a hub to browse")
    ap.add_argument("--label", default="", help="label for --add-source")
    ap.add_argument("--source-kind", default="aggregator",
                    choices=sorted(KIND_HINT),
                    help="hub kind for --add-source (drives the fetch hint)")
    ap.add_argument("--note", default="", help="note for --add-source")
    ap.add_argument("--checked", nargs="+", metavar="URL",
                    help="mark source URL(s) as checked now")
    ap.add_argument("--canary", metavar="URL",
                    help="register an out-of-band find (recall ground truth)")
    ap.add_argument("--title", default="", help="title for --canary")
    ap.add_argument("--via", default="", help="where the canary came from")
    ap.add_argument("--canary-check", action="store_true",
                    help="report which canaries the loop found (recall)")
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
        ingest(cfg, conn, Path(args.ingest), args.bucket,
               archive=not args.no_archive, queries=args.queries)
        ran = True
    if args.regrade:
        regrade(conn, Path(args.regrade))
        ran = True
    if args.titles:
        dump_titles(conn, args.category)
        ran = True
    if args.stats:
        stats(conn)
        ran = True
    if args.batches:
        batches(conn)
        ran = True
    if args.stale:
        stale(conn)
        ran = True
    if args.recheck:
        recheck(conn, args.age_days)
        ran = True
    if args.seed_sources:
        seed_sources(cfg, conn)
        ran = True
    if args.add_source:
        add_source(conn, args.add_source, args.label, args.bucket,
                   args.source_kind, args.note)
        ran = True
    if args.sources:
        list_sources(conn)
        ran = True
    if args.checked:
        mark_checked(conn, args.checked)
        ran = True
    if args.canary:
        canary_add(conn, args.canary, args.title, args.via)
        ran = True
    if args.canary_check:
        canary_check(conn)
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
