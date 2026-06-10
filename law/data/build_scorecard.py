"""
Merge College Scorecard JD-program debt + earnings into law_schools.json.

Source: law/data/raw/scorecard_law_2201.json — Scorecard API extract of every
institution with a CIP 22.01 (Law) program (fetch documented in TASKS.md).
We keep credential level 7 (First Professional Degree = JD) only.

Fields written (DISPLAY-ONLY, never scored):
    scorecard_median_debt     median Stafford+GradPLUS federal debt at graduation
    scorecard_debt_monthly    median monthly payment on that debt
    scorecard_earn_1yr        median earnings 1 year after completion
    scorecard_earn_4yr        median earnings 4 years after completion

Institutions are matched to our schools by state + token containment on
normalized names, with a manual map for the awkward ones. The script fails
loudly (prints) on every unmatched school so coverage gaps are visible.

Run:  python -m law.data.build_scorecard        (from repo root)
"""

import json
import re
from pathlib import Path
from typing import Optional

RAW = Path(__file__).parent / "raw" / "scorecard_law_2201.json"
JSON_PATH = Path(__file__).parent / "law_schools.json"

# Words that carry no identity: school-of-law boilerplate + generic glue.
# NOTE: "university"/"college" stay — they distinguish e.g. Boston University
# from Boston College and Mississippi College from University of Mississippi.
_NOISE = {
    "school", "of", "law", "the", "at", "in", "a", "center", "campus",
    "main", "and", "&", "for",
}

# our id -> Scorecard institution name (exact school.name), for schools the
# token matcher can't resolve (parent named differently, multi-campus systems,
# mergers, or a state mismatch like Widener's DE law school under its PA parent).
MANUAL: dict[str, str] = {
    "cardozo-law": "Yeshiva University",
    "nyu-law": "New York University",
    "ucla-law": "University of California-Los Angeles",
    "uc-davis-law": "University of California-Davis",
    "uc-law-san-francisco": "University of California College of the Law-San Francisco",
    "loyola-la-law": "Loyola Marymount University",
    "indiana-maurer-law": "Indiana University-Bloomington",
    "indiana-university-robert-h-mckinney-school-of-law": "Indiana University-Indianapolis",
    "maryland-carey-law": "University of Maryland Baltimore",
    "university-of-hawaii-richardson-school-of-law": "University of Hawaii at Manoa",
    "lsu-paul-m-hebert-law-center": "Louisiana State University and Agricultural & Mechanical College",
    "unlv-william-s-boyd-school-of-law": "University of Nevada-Las Vegas",
    # Penn State Law merged into Dickinson Law (2025); one Scorecard entry.
    "penn-state-dickinson-law": "Pennsylvania State University-Main Campus",
    "university-of-south-carolina-joseph-f-rice-school-of-law": "University of South Carolina-Columbia",
    # Widener University (PA parent) hosts Delaware Law; Commonwealth (Harrisburg)
    # has no separate Scorecard law entry and stays unmatched.
    "widener-university-delaware-law-school": "Widener University",
    "illinois-law": "University of Illinois Urbana-Champaign",
    "chicago-kent-college-of-law": "Illinois Institute of Technology",
    "arizona-state-law": "Arizona State University Campus Immersion",
    "texas-am-law": "Texas A&M University-College Station",
    "university-of-oklahoma-college-of-law": "University of Oklahoma-Norman Campus",
    "university-of-puerto-rico-school-of-law": "University of Puerto Rico-Rio Piedras",
    "michigan-law": "University of Michigan-Ann Arbor",
    "florida-aandm-university-college-of-law": "Florida Agricultural and Mechanical University",
    "unt-dallas-college-of-law": "University of North Texas at Dallas",
    "northwestern-pritzker-law": "Northwestern University",
    # No Scorecard JD entry (programs too new or folded into a parent we already
    # use): jacksonville-university-college-of-law, wilmington-university-school-
    # of-law, widener-university-commonwealth-law-school stay unmatched.
}


def _tokens(name: str) -> frozenset[str]:
    s = name.lower().replace("&", " and ")
    # Strip the law-school suffix as a PHRASE so its "college"/"school" words
    # don't block matching against the parent university's name.
    s = re.sub(r"\b(college of (the )?law|school of law|law school|law center)\b", " ", s)
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    toks = {t for t in s.split() if t not in _NOISE}
    return frozenset(toks)


def _score(school: dict, inst: dict) -> float:
    """Match quality between one of our schools and a Scorecard institution.
    0 = no match. Same state required; token containment required; subset of
    the institution name (ours <= theirs) preferred over the reverse; jaccard
    breaks ties (so 'University of Illinois' prefers the shorter campus name
    only when containment is equal)."""
    if (inst.get("school.state") or "").upper() != school["state"].upper():
        return 0.0
    ours, theirs = _tokens(school["name"]), _tokens(inst["school.name"])
    if not ours or not theirs:
        return 0.0
    if ours <= theirs:
        base = 2.0
    elif theirs <= ours:
        base = 1.0
    else:
        return 0.0
    return base + len(ours & theirs) / len(ours | theirs)


def _assign(schools: list[dict], insts: list[dict]) -> dict[str, dict]:
    """Greedy unique assignment: best-scoring (school, institution) pairs first,
    each institution used at most once. Manual mappings are applied first and
    their institutions removed from the pool."""
    by_name = {i["school.name"]: i for i in insts}
    assigned: dict[str, dict] = {}
    taken: set[str] = set()

    for sid, iname in MANUAL.items():
        inst = by_name.get(iname)
        if inst is None:
            print(f"!! MANUAL name not in extract: {iname} (for {sid})")
            continue
        assigned[sid] = inst
        taken.add(iname)

    pairs = []
    for school in schools:
        if school["id"] in assigned:
            continue
        for inst in insts:
            if inst["school.name"] in taken:
                continue
            sc = _score(school, inst)
            if sc > 0:
                pairs.append((sc, school["id"], inst["school.name"]))
    pairs.sort(reverse=True)
    for sc, sid, iname in pairs:
        if sid in assigned or iname in taken:
            continue
        assigned[sid] = by_name[iname]
        taken.add(iname)
    return assigned


def _jd_program(inst: dict) -> Optional[dict]:
    for p in inst.get("latest.programs.cip_4_digit", []):
        if p.get("credential", {}).get("level") == 7:
            return p
    return None


def main() -> None:
    insts = json.loads(RAW.read_text(encoding="utf-8"))

    data = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    schools = data["schools"]
    assigned = _assign(schools, insts)

    matched, unmatched, suppressed = [], [], []

    for school in schools:
        inst = assigned.get(school["id"])
        prog = _jd_program(inst) if inst else None
        if prog is None:
            unmatched.append(school["id"])
            for k in ("scorecard_median_debt", "scorecard_debt_monthly",
                      "scorecard_earn_1yr", "scorecard_earn_4yr"):
                school[k] = None
            continue

        debt = prog["debt"]["staff_grad_plus"]["all"]["eval_inst"]
        earn1 = prog["earnings"]["1_yr"]["overall_median_earnings"]
        earn4 = prog["earnings"]["4_yr"]["overall_median_earnings"]
        school["scorecard_median_debt"] = debt.get("median")
        school["scorecard_debt_monthly"] = debt.get("median_payment")
        school["scorecard_earn_1yr"] = earn1
        school["scorecard_earn_4yr"] = earn4
        matched.append(school["id"])
        if debt.get("median") is None and earn1 is None:
            suppressed.append(school["id"])

    JSON_PATH.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    print(f"matched {len(matched)}/{len(schools)} (privacy-suppressed values at {len(suppressed)})")
    if unmatched:
        print(f"UNMATCHED ({len(unmatched)}):")
        for u in unmatched:
            print("  -", u)
    dbt = sum(1 for s in schools if s.get("scorecard_median_debt") is not None)
    e4 = sum(1 for s in schools if s.get("scorecard_earn_4yr") is not None)
    print(f"populated: median_debt {dbt}, earn_4yr {e4}")


if __name__ == "__main__":
    main()
