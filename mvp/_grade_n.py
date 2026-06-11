"""Grade the NETWORK-RETREATS list (retreats/communities for ambitious young adults,
focused on NETWORK DEVELOPMENT) by NETWORK VALUE.

Separate DB (network.db). Grades A+..C- = density/quality of the people + access it gives
Luke as an ambitious pre-founder (tech/VC/founder track), NOT generic fit. Every row is
kind='network'. Re-export sorted CSV + print distribution.
"""
import sqlite3, csv
from pathlib import Path

DB = Path(__file__).parent / "network.db"
CSV = Path(__file__).parent / "network.csv"

# title -> (network_value_grade, timing/access). 9 sub-tiers: A+ A A- B+ B B- C+ C C-
DATA = {
    "Interact Fellowship (community of young technologists, 18-23)": ("B+", "~Feb 15 deadline; ages 18-23; fully-sponsored retreats; <10% accept"),
    "Summit Series (invite-only entrepreneur/creative community)": ("B", "Invite/apply; festivals + events; can be pricey"),
    "Launch House (founder/builder social club + residencies)": ("B", "Competitive rolling; LA/NYC houses + digital"),
    "On Deck (builder network - co-founders, mentors, investors)": ("B-", "Cohorts; mostly virtual; broad builder network"),
    "Foster (collective of writers & editors)": ("B", "Rolling; writers/editors collective + feedback; YC-backed"),
    "Socratica (build-in-public makers collective + Symposium)": ("B-", "Annual Symposium (Waterloo) + study sessions"),
    "AGI House (AI founders & researchers community)": ("B+", "Merit-based, free events; SF + expanding; non-tech welcome"),
    "BizOps Network (peer community for BizOps / operators)": ("B", "Membership; welcomes early-career; BizOps/CoS peers"),
    "GoingVC (aspiring-investor fellowship + alumni network)": ("B", "~16-wk; no accreditation needed; paid; on your VC aim"),
    "Neo (community of young technologists + residency)": ("B-", "Residency $40k/3-mo SF (2026 closed) + community; eng-leaning"),
    "Reboot (publication + community for technologists who write)": ("B", "Rolling; Discord + meetups; tech + writing culture fit"),
    "Tech Week by a16z (decentralized founder/investor events)": ("B", "NYC Jun 1-7, SF Oct 5-11, LA, Boston 2026; mostly free"),
    "Asterisk AI Blogging Fellowship (write-in-public cohort)": ("B+", "Cohort + $1k + mentorship; needs an AI-topic angle"),
    "Confluence.VC (emerging-VC community + intel)": ("B-", "Newsletter + firm intel; on your VC track"),
    "The Residency (live-in houses for young builders)": ("B-", "Rolling cohorts; live together months; verify current cities"),
    "Sandbox (global community of under-30 doers)": ("B-", "Apply to a hub; verify current activity"),
    "Kairos Society (young entrepreneurs network)": ("B-", "Fellowship + global summit; skews college/early"),
    "GenZ VCs (community for young people in / into VC)": ("B-", "Free-ish community + events; directly on your VC aim"),
    "Cerebral Valley (AI builder community + summits)": ("B-", "Summits/events; AI-builder network; SF-centric"),
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
        conn.execute("ALTER TABLE opportunities ADD COLUMN kind TEXT DEFAULT 'network'")

    for title, (grade, dl) in DATA.items():
        conn.execute(
            "UPDATE opportunities SET fit_grade=?, deadline=?, kind='network' WHERE title=?",
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
        w.writerow(["Network value", "Access", "Category", "Title", "URL", "Summary", "Why it's worth it", "Found at"])
        w.writerows(rows)

    print(f"CSV rows: {len(rows)}")
    print(" / ".join(f"{g} {sum(1 for r in rows if r[0] == g)}" for g in ORDER))


if __name__ == "__main__":
    main()
