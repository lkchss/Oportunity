"""Grade the JOBS list (concrete roles toward where Luke wants to go) by FIT.

Separate DB (jobs.db). Grades A+..C- = how well the role fits Luke's destination
(tech / VC / startup / founder track; analytical, prestige-preserving, forward).
HARD CONSTRAINT: Luke has only 1-2 years of experience - ONLY include roles that
want <= 3 YOE (skip anything asking for more). Every row is kind='job'.
Re-export sorted CSV + print distribution.
"""
import sqlite3, csv
from pathlib import Path

DB = Path(__file__).parent / "jobs.db"
CSV = Path(__file__).parent / "jobs.csv"

# title -> (fit_grade, deadline/timing). 9 sub-tiers: A+ A A- B+ B B- C+ C C-
DATA = {
    "Anthropic - Strategy & Operations (junior / associate, <=3 YOE)": ("A", "Rolling; frontier AI lab; junior S&O only"),
    "AI BizOps & Chief-of-Staff job board (bizops.careers + AI Operators)": ("A-", "Live board; weekly; filter to 1-3 YOE roles"),
    "Early-stage VC Analyst / Associate roles (VC Stack, Startup&VC, Wellfound)": ("A-", "Rolling; entry/pre-MBA; scarce + network-driven"),
    "Founding / early BizOps & Strategy at high-growth AI (e.g. EliseAI)": ("B+", "Rolling; target associate/founding-IC, not Manager"),
    "Experimentation / Causal-Inference Data roles - new-grad / early-career": ("B", "Rolling; filter to new-grad/<=3 YOE; many want PhD"),
}

ORDER = ["A+", "A", "A-", "B+", "B", "B-", "C+", "C", "C-"]


def main() -> None:
    conn = sqlite3.connect(DB)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(opportunities)")}
    if "fit_grade" not in cols:
        conn.execute("ALTER TABLE opportunities ADD COLUMN fit_grade TEXT")
    if "deadline" not in cols:
        conn.execute("ALTER TABLE opportunities ADD COLUMN deadline TEXT")
    if "kind" not in cols:
        conn.execute("ALTER TABLE opportunities ADD COLUMN kind TEXT DEFAULT 'job'")

    for title, (grade, dl) in DATA.items():
        conn.execute(
            "UPDATE opportunities SET fit_grade=?, deadline=?, kind='job' WHERE title=?",
            (grade, dl, title),
        )
    conn.commit()

    order = {g: i for i, g in enumerate(ORDER)}
    rows = conn.execute(
        "SELECT fit_grade, deadline, category, title, url, summary, why_match, found_at "
        "FROM opportunities"
    ).fetchall()
    rows.sort(key=lambda r: (order.get(r[0], 99), r[2] or "", r[3] or ""))

    with open(CSV, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["Fit", "Timing", "Category", "Title", "URL", "Summary", "Why it fits", "Found at"])
        w.writerows(rows)

    print(f"CSV rows: {len(rows)}")
    print(" / ".join(f"{g} {sum(1 for r in rows if r[0] == g)}" for g in ORDER))


if __name__ == "__main__":
    main()
