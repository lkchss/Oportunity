"""
Base-record generator: add the ABA-accredited schools missing from our set.

The seven ABA bulk reports in raw/ cover all ~196 accredited schools, so every
school we add gets real admissibility (LSAT/GPA percentiles), career outcomes,
scholarships, tuition, bar passage, and transfer data — the same provenance as
the original 75. This script generates the BASE record (identity + admissibility
+ tuition + the soft estimated fields), appends it to law_schools.json, then
delegates to build_enrichment to fill the ABA enrichment fields uniformly.

Two inputs can't come from the ABA files and are supplied by the SCHOOL_META
table below:
  - state          (drives in-state tuition + location fit)
  - usnwr_rank_2026 (the ABA doesn't rank; US News does)

Rank policy: only the elite schools we were missing get a real US News 2026 rank
(prestige floors at ~0 past rank ~84, so a precise rank below that is immaterial
to the composite). Everything else gets RNP_RANK and renders as "Unranked".
All assigned ranks and the soft estimated fields should be verified before
production use.

Run:  python -m law.data.build_schools     (from repo root)
"""

import json
import re
from pathlib import Path
from typing import Optional

import pandas as pd

from law.data import build_enrichment as be

RAW = Path(__file__).parent / "raw"
JSON_PATH = Path(__file__).parent / "law_schools.json"

RNP_RANK = 999  # sentinel for unranked (Rank-Not-Published) schools

# State cost-of-living index (rough, estimated — verify). Default 100.
_STATE_COL = {
    "CA": 135, "NY": 130, "MA": 130, "DC": 145, "HI": 165, "CT": 125,
    "NJ": 120, "WA": 115, "MD": 115, "OR": 110, "CO": 110, "RI": 115,
    "NH": 110, "VA": 105, "IL": 105, "FL": 102, "MN": 102, "PR": 90,
}

# Conservative regional defaults for fields not in the ABA reports (estimated).
_DEFAULT_PRIVATE_SALARY = 90_000
_DEFAULT_PUBLIC_SALARY = 58_000
_DEFAULT_MEDIAN_SCHOLARSHIP = 12_000

# aba_name -> (state, usnwr_rank_2026 | None, display_name | None)
# state is required; rank None => RNP; display_name None => auto de-inverted.
SCHOOL_META: dict[str, tuple[str, Optional[int], Optional[str]]] = {
    "Akron, The University of": ("OH", None, None),
    "Albany Law School": ("NY", None, "Albany Law School"),
    "American University": ("DC", None, "American University Washington College of Law"),
    "Appalachian School of Law": ("VA", None, "Appalachian School of Law"),
    "Arkansas at Little Rock, University of": ("AR", None, "University of Arkansas at Little Rock School of Law"),
    "Arkansas, University of": ("AR", None, "University of Arkansas School of Law"),
    "Atlanta's John Marshall Law School": ("GA", None, "Atlanta's John Marshall Law School"),
    "Ave Maria School of Law": ("FL", None, "Ave Maria School of Law"),
    "Baltimore, University of": ("MD", None, "University of Baltimore School of Law"),
    "Barry University": ("FL", None, "Barry University School of Law"),
    "Belmont University": ("TN", None, "Belmont University College of Law"),
    "Brooklyn Law School": ("NY", None, "Brooklyn Law School"),
    "California Western School of Law": ("CA", None, "California Western School of Law"),
    "California-Berkeley, University of": ("CA", 10, "University of California, Berkeley School of Law"),
    "California-San Francisco, University of": ("CA", None, "UC Law San Francisco"),
    "Campbell University": ("NC", None, "Campbell University School of Law"),
    "Capital University Law School": ("OH", None, "Capital University Law School"),
    "Case Western Reserve University": ("OH", None, "Case Western Reserve University School of Law"),
    "Chapman University": ("CA", None, "Chapman University Fowler School of Law"),
    "Charleston School of Law": ("SC", None, "Charleston School of Law"),
    "Chicago-Kent, Illinois Institute of Technology": ("IL", None, "Chicago-Kent College of Law"),
    "City University of New York, University of": ("NY", None, "CUNY School of Law"),
    "Cleveland State University": ("OH", None, "Cleveland State University College of Law"),
    "Cooley Law School": ("MI", None, "Cooley Law School"),
    "Creighton University": ("NE", None, "Creighton University School of Law"),
    "Dayton, University of": ("OH", None, "University of Dayton School of Law"),
    "DePaul University": ("IL", None, "DePaul University College of Law"),
    "Denver, University of": ("CO", None, "University of Denver Sturm College of Law"),
    "Detroit Mercy, University of": ("MI", None, "University of Detroit Mercy School of Law"),
    "District of Columbia, University of": ("DC", None, "University of the District of Columbia David A. Clarke School of Law"),
    "Drake University": ("IA", None, "Drake University Law School"),
    "Duquesne University": ("PA", None, "Duquesne University School of Law"),
    "Elon University": ("NC", None, "Elon University School of Law"),
    "Faulkner University": ("AL", None, "Faulkner University Jones School of Law"),
    "Florida A&M University": ("FL", None, "Florida A&M University College of Law"),
    "Georgetown University": ("DC", 14, "Georgetown University Law Center"),
    "Gonzaga University": ("WA", None, "Gonzaga University School of Law"),
    "Hawaii, University of": ("HI", None, "University of Hawaii Richardson School of Law"),
    "Hofstra University": ("NY", None, "Hofstra University Maurice A. Deane School of Law"),
    "Howard University": ("DC", None, "Howard University School of Law"),
    "Idaho, University of": ("ID", None, "University of Idaho College of Law"),
    "Illinois-Chicago, University of": ("IL", None, "University of Illinois Chicago School of Law"),
    "Indiana University-Indianapolis": ("IN", None, "Indiana University Robert H. McKinney School of Law"),
    "Inter American University of Puerto Rico": ("PR", None, "Inter American University of Puerto Rico School of Law"),
    "Jacksonville University": ("FL", None, "Jacksonville University College of Law"),
    "Lewis & Clark Law School": ("OR", None, "Lewis & Clark Law School"),
    "Liberty University": ("VA", None, "Liberty University School of Law"),
    "Lincoln Memorial University": ("TN", None, "Lincoln Memorial University Duncan School of Law"),
    "Louisiana State University": ("LA", None, "LSU Paul M. Hebert Law Center"),
    "Louisville, University of": ("KY", None, "University of Louisville Brandeis School of Law"),
    "Loyola University-New Orleans": ("LA", None, "Loyola University New Orleans College of Law"),
    "Maine, University of": ("ME", None, "University of Maine School of Law"),
    "Marquette University": ("WI", None, "Marquette University Law School"),
    "Massachusetts/Dartmouth, University of": ("MA", None, "University of Massachusetts School of Law"),
    "Memphis, The University of": ("TN", None, "University of Memphis Cecil C. Humphreys School of Law"),
    "Mercer University": ("GA", None, "Mercer University School of Law"),
    "Michigan State University": ("MI", None, "Michigan State University College of Law"),
    "Mississippi College": ("MS", None, "Mississippi College School of Law"),
    "Mississippi, The University of": ("MS", None, "University of Mississippi School of Law"),
    "Missouri-Kansas City, University of": ("MO", None, "University of Missouri-Kansas City School of Law"),
    "Mitchell/Hamline School of Law": ("MN", None, "Mitchell Hamline School of Law"),
    "Montana, University of": ("MT", None, "University of Montana Blewett School of Law"),
    "Nebraska, University of": ("NE", None, "University of Nebraska College of Law"),
    "Nevada-Las Vegas, University of": ("NV", None, "UNLV William S. Boyd School of Law"),
    "New England Law/Boston": ("MA", None, "New England Law Boston"),
    "New Hampshire, University of": ("NH", None, "University of New Hampshire Franklin Pierce School of Law"),
    "New Mexico, The University of": ("NM", None, "University of New Mexico School of Law"),
    "New York Law School": ("NY", None, "New York Law School"),
    "North Carolina Central University": ("NC", None, "North Carolina Central University School of Law"),
    "North Carolina, University of": ("NC", 22, "University of North Carolina School of Law"),
    "North Dakota, University of": ("ND", None, "University of North Dakota School of Law"),
    "North Texas at Dallas, University of": ("TX", None, "UNT Dallas College of Law"),
    "Northern Illinois University": ("IL", None, "Northern Illinois University College of Law"),
    "Northern Kentucky University": ("KY", None, "Northern Kentucky University Chase College of Law"),
    "Nova Southeastern University": ("FL", None, "Nova Southeastern University Shepard Broad College of Law"),
    "Ohio Northern University": ("OH", None, "Ohio Northern University Pettit College of Law"),
    "Oklahoma City University": ("OK", None, "Oklahoma City University School of Law"),
    "Oklahoma, University of": ("OK", None, "University of Oklahoma College of Law"),
    "Oregon, University of": ("OR", None, "University of Oregon School of Law"),
    "Pace University": ("NY", None, "Pace University Elisabeth Haub School of Law"),
    "Pacific, University of the": ("CA", None, "University of the Pacific McGeorge School of Law"),
    "Penn State Dickinson Law": ("PA", None, "Penn State Dickinson Law"),
    "Pontifical Catholic University of Puerto Rico": ("PR", None, "Pontifical Catholic University of Puerto Rico School of Law"),
    "Puerto Rico, University of": ("PR", None, "University of Puerto Rico School of Law"),
    "Quinnipiac University": ("CT", None, "Quinnipiac University School of Law"),
    "Regent University": ("VA", None, "Regent University School of Law"),
    "Roger Williams University": ("RI", None, "Roger Williams University School of Law"),
    "Rutgers University": ("NJ", None, "Rutgers Law School"),
    "Saint Louis University": ("MO", None, "Saint Louis University School of Law"),
    "Samford University": ("AL", None, "Samford University Cumberland School of Law"),
    "San Francisco, University of": ("CA", None, "University of San Francisco School of Law"),
    "Santa Clara University": ("CA", None, "Santa Clara University School of Law"),
    "Seattle University": ("WA", None, "Seattle University School of Law"),
    "South Carolina, University of": ("SC", None, "University of South Carolina Joseph F. Rice School of Law"),
    "South Dakota, University of": ("SD", None, "University of South Dakota Knudson School of Law"),
    "South Texas College of Law Houston": ("TX", None, "South Texas College of Law Houston"),
    "Southern Illinois University": ("IL", None, "Southern Illinois University School of Law"),
    "Southern University": ("LA", None, "Southern University Law Center"),
    "Southwestern Law School": ("CA", None, "Southwestern Law School"),
    "St. Mary's University": ("TX", None, "St. Mary's University School of Law"),
    "St. Thomas University (Miami)": ("FL", None, "St. Thomas University College of Law"),
    "St. Thomas, (Minneapolis) University of": ("MN", None, "University of St. Thomas School of Law"),
    "Stetson University": ("FL", None, "Stetson University College of Law"),
    "Suffolk University": ("MA", None, "Suffolk University Law School"),
    "Syracuse University": ("NY", None, "Syracuse University College of Law"),
    "Texas Southern University": ("TX", None, "Texas Southern University Thurgood Marshall School of Law"),
    "Texas Tech University": ("TX", None, "Texas Tech University School of Law"),
    "Texas, University of": ("TX", 16, "University of Texas School of Law"),
    "Toledo, The University of": ("OH", None, "University of Toledo College of Law"),
    "Touro University": ("NY", None, "Touro University Jacob D. Fuchsberg Law Center"),
    "Tulsa, The University of": ("OK", None, "University of Tulsa College of Law"),
    "Vermont Law School": ("VT", None, "Vermont Law and Graduate School"),
    "Washburn University": ("KS", None, "Washburn University School of Law"),
    "West Virginia University": ("WV", None, "West Virginia University College of Law"),
    "Western New England University": ("MA", None, "Western New England University School of Law"),
    "Western State, Westcliff University": ("CA", None, "Western State College of Law at Westcliff University"),
    "Widener University Commonwealth Law School": ("PA", None, "Widener University Commonwealth Law School"),
    "Widener University Delaware Law School": ("DE", None, "Widener University Delaware Law School"),
    "Willamette University": ("OR", None, "Willamette University College of Law"),
    "Wilmington University School of Law": ("DE", None, "Wilmington University School of Law"),
    "Wyoming, University of": ("WY", None, "University of Wyoming College of Law"),
}


def _slug(name: str) -> str:
    s = name.lower()
    s = s.replace("&", "and").replace(".", "").replace(",", "")
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s


def _num(v) -> float:
    return be._num(v)


def _admissibility(fy_row) -> Optional[dict]:
    """LSAT/GPA percentiles from the First Year Class report; None if incomplete."""
    fields = {
        "lsat_25": "All25thPercentileLSAT",
        "lsat_50": "All50thPercentileLSAT",
        "lsat_75": "All75thPercentileLSAT",
        "gpa_25": "All25thPercentileUGPA",
        "gpa_50": "All50thPercentileUGPA",
        "gpa_75": "All75thPercentileUGPA",
    }
    out = {}
    for key, col in fields.items():
        val = _num(fy_row[col])
        if val <= 0:
            return None  # can't tier a school without full admissibility data
        out[key] = int(val) if key.startswith("lsat") else round(val, 2)
    acc = _num(fy_row["AcceptanceRate"])
    out["acceptance_rate"] = round(acc / 100, 4) if acc > 0 else 0.5
    return out


def build_base_record(aba: str, fy_row, tui_row, basics_row, grants_row, emp_row) -> Optional[dict]:
    state, rank, display = SCHOOL_META[aba]
    adm = _admissibility(fy_row)
    if adm is None:
        return None

    name = display or aba
    sid = _slug(name)

    # Tuition (ABA): resident vs non-resident; private schools report them equal.
    # Many schools leave the *Annual columns blank and bill per credit instead —
    # fall back to FT_*_Credit x a standard full-time JD load (~30 credits/year;
    # total required hours vary 87-90 and some report quarter-hours, so a flat 30
    # is the robust estimate).
    _CREDITS_PER_YEAR = 30
    res = nonres = 0.0
    if tui_row is not None:
        res = _num(tui_row["FT_Resident_Annual"])
        nonres = _num(tui_row["FT_NonResident_Annual"])
        if res <= 0:
            res = _num(tui_row["FT_Resident_Credit"]) * _CREDITS_PER_YEAR
        if nonres <= 0:
            nonres = _num(tui_row["FT_NonResident_Credit"]) * _CREDITS_PER_YEAR
    nonres = nonres or res
    res = res or nonres

    # is_public from The Basics SchoolType
    is_public = bool(basics_row is not None and str(basics_row["SchoolType"]).strip().lower() == "public")

    # scholarship_pct (share receiving any grant) from the Grants report
    scholarship_pct = 0.5
    if grants_row is not None:
        total = _num(grants_row["Total Number # of Students Total #"])
        recip = _num(grants_row["Total Number # of Recieving Grants Total #"])
        if total > 0:
            # ABA recipient counts can slightly exceed enrollment (mid-year
            # leavers still counted as recipients) — cap at 100%.
            scholarship_pct = min(round(recip / total, 4), 1.0)

    # jd_required_pct (FT long-term bar-required / grads) from Employment Summary;
    # not filled by build_enrichment, so compute it here.
    jd_required_pct = 0.7
    if emp_row is not None:
        grads = _num(emp_row["Total_GraduatesTotal"])
        if grads > 0:
            jd_required_pct = round(_num(emp_row["Employed_BarAdmissionRequiredFTLT"]) / grads, 4)

    record = {
        "id": sid,
        "name": name,
        "location": state,
        "state": state,
        "website_url": "",
        "usnwr_rank_2026": rank if rank is not None else RNP_RANK,
        "is_public": is_public,
        **adm,
        "scholarship_pct": scholarship_pct,
        "median_scholarship": _DEFAULT_MEDIAN_SCHOLARSHIP,
        # career fields are placeholders; build_enrichment overwrites with real ABA data
        "biglaw_pct": 0.0,
        "federal_clerkship_pct": 0.0,
        "government_pct": 0.0,
        "public_interest_pct": 0.0,
        "solo_small_firm_pct": 0.0,
        "jd_required_pct": jd_required_pct,
        "bar_pass_rate_first_time": 0.0,  # overwritten by build_enrichment
        "median_private_sector_salary": _DEFAULT_PRIVATE_SALARY,
        "median_public_sector_salary": _DEFAULT_PUBLIC_SALARY,
        "practice_area_strengths": [],
        "lrap_quality": "moderate",
        "target_states": [state],
        "annual_tuition": int(nonres),
        "annual_tuition_resident": int(res),
        "annual_tuition_nonresident": int(nonres),
        "cost_of_living_index": _STATE_COL.get(state, 100),
    }
    return record


def main(json_path: Optional[Path] = None) -> None:
    target = json_path if json_path is not None else JSON_PATH
    fy = be._index(pd.read_excel(RAW / "First_Year_Class_2025.xlsx"))
    tui = be._index(pd.read_excel(RAW / "Tuitions_and_Fees_Living_Expenses_Cond._Scholarships_2025.xlsx"))
    basics = be._index(pd.read_excel(RAW / "The_Basics_Academic_Calendar_2025.xlsx"))
    grants = be._index(pd.read_excel(RAW / "Grants_and_Scholarships_2025.xlsx"))
    emp = be._index(pd.read_excel(RAW / "Employment_Summary_2025.xlsx"))

    data = json.loads(target.read_text(encoding="utf-8"))
    schools = data["schools"]
    existing_ids = {s["id"] for s in schools}

    added, skipped, ranked = [], [], []
    new_mappings: dict[str, str] = {}

    for aba in SCHOOL_META:
        if aba not in fy:
            skipped.append(f"{aba}: not in First Year Class report")
            continue
        rec = build_base_record(
            aba, fy[aba], tui.get(aba), basics.get(aba), grants.get(aba), emp.get(aba)
        )
        if rec is None:
            skipped.append(f"{aba}: incomplete admissibility data")
            continue
        if rec["id"] in existing_ids:
            skipped.append(f"{aba}: id '{rec['id']}' already exists")
            continue
        schools.append(rec)
        existing_ids.add(rec["id"])
        new_mappings[rec["id"]] = aba
        added.append(rec["id"])
        if rec["usnwr_rank_2026"] != RNP_RANK:
            ranked.append(f"{rec['name']} -> #{rec['usnwr_rank_2026']}")

    data["_metadata"]["coverage"] = (
        f"USNWR 1-82 + ABA-accredited expansion ({len(schools)} schools; "
        f"non-T82 schools RNP unless noted)"
    )
    target.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    print(f"added {len(added)} base records (total now {len(schools)})")
    print(f"assigned real ranks ({len(ranked)}): " + "; ".join(ranked))
    if skipped:
        print(f"skipped {len(skipped)}:")
        for s in skipped:
            print("  -", s)

    # Enrich the new schools (and re-enrich existing) with real ABA data.
    be.ID_TO_ABA.update(new_mappings)
    print("\n--- running build_enrichment over expanded set ---")
    be.main(json_path=target)


if __name__ == "__main__":
    main()
