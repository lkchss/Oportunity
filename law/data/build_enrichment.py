"""
One-shot enrichment parser: merge ABA 2025 bulk reports into law_schools.json.

Reads the five 2025 ABA compilation spreadsheets in law/data/raw/, computes the
enrichment fields for each of our 75 schools (mapped by explicit name table to
avoid fuzzy mis-matches), and writes them back into law_schools.json.

Run:  python -m law.data.build_enrichment        (from repo root)
   or python law/data/build_enrichment.py
"""

import json
from pathlib import Path

import pandas as pd

RAW = Path(__file__).parent / "raw"
JSON_PATH = Path(__file__).parent / "law_schools.json"

# our id -> exact ABA SchoolName string (verified against all 5 reports)
ID_TO_ABA: dict[str, str] = {
    "boston-college-law": "Boston College",
    "notre-dame-law": "Notre Dame, University of",
    "texas-am-law": "Texas A&M University",
    "minnesota-law": "Minnesota, University of",
    "boston-university-law": "Boston University",
    "byu-clark-law": "Brigham Young University",
    "george-washington-law": "George Washington University, The",
    "georgia-law": "Georgia, University of",
    "usc-gould-law": "Southern California, University of",
    "wisconsin-law": "Wisconsin, University of",
    "ohio-state-moritz-law": "The Ohio State University",
    "wake-forest-law": "Wake Forest University",
    "george-mason-scalia-law": "George Mason University",
    "iowa-law": "Iowa, University of",
    "baylor-law": "Baylor University",
    "florida-state-law": "Florida State University",
    "uc-irvine-law": "California-Irvine, University of",
    "florida-levin-law": "Florida, University of",
    "washington-lee-law": "Washington and Lee University",
    "william-mary-law": "William & Mary",
    "emory-law": "Emory University",
    "alabama-law": "Alabama, The University of",
    "fordham-law": "Fordham University",
    "smu-dedman-law": "Southern Methodist University",
    "arizona-state-law": "Arizona State University",
    "utah-quinney-law": "Utah, The University of",
    "illinois-law": "Illinois, University of",
    "kansas-law": "Kansas, The University of",
    "pepperdine-law": "Pepperdine University",
    "indiana-maurer-law": "Indiana University-Bloomington",
    "temple-beasley-law": "Temple University",
    "villanova-law": "Villanova University",
    "washington-law": "Washington, University of",
    "uc-davis-law": "California-Davis, University of",
    "university-san-diego-law": "San Diego, University of",
    "houston-law": "Houston, University of",
    "colorado-law": "Colorado, University of",
    "tennessee-law": "Tennessee, University of",
    "uconn-law": "Connecticut, University of",
    "cardozo-law": "Cardozo, Yeshiva University",
    "missouri-law": "Missouri, University of",
    "maryland-carey-law": "Maryland, University of",
    "richmond-law": "Richmond, University of",
    "st-johns-law": "St. John's University",
    "wayne-state-law": "Wayne State University",
    "tulane-law": "Tulane University",
    "arizona-rogers-law": "Arizona, The University of",
    "loyola-la-law": "Loyola Marymount University-Los Angeles",
    "miami-law": "Miami, University of",
    "catholic-columbus-law": "Catholic University of America, The",
    "stanford-law": "Stanford University",
    "uchicago-law": "Chicago, The University of",
    "yale-law": "Yale University",
    "penn-carey-law": "Pennsylvania, University of",
    "uva-law": "Virginia, University of",
    "harvard-law": "Harvard University",
    "duke-law": "Duke University",
    "nyu-law": "New York University",
    "columbia-law": "Columbia University",
    "northwestern-pritzker-law": "Northwestern University",
    "michigan-law": "Michigan, University of",
    "vanderbilt-law": "Vanderbilt University",
    "cornell-law": "Cornell University",
    "ucla-law": "California-Los Angeles, University of",
    "washu-law": "Washington University (St. Louis)",
    "kentucky-rosenberg-law": "Kentucky, University of",
    "seton-hall-law": "Seton Hall University",
    "georgia-state-law": "Georgia State University",
    "loyola-chicago-law": "Loyola University-Chicago",
    "northeastern-law": "Northeastern University",
    "pittsburgh-law": "Pittsburgh, University of",
    "fiu-law": "Florida International University",
    "cincinnati-law": "Cincinnati, University of",
    "drexel-kline-law": "Drexel University",
    "suny-buffalo-law": "Buffalo, University at",
}


def _num(v) -> float:
    """Coerce an ABA cell to a number; blanks/dashes -> 0."""
    if pd.isna(v):
        return 0.0
    s = str(v).replace("$", "").replace(",", "").strip()
    if s in ("", "-", "N/A", "nan"):
        return 0.0
    return float(s)


def _index(df: pd.DataFrame) -> dict[str, pd.Series]:
    return {str(r["SchoolName"]).strip(): r for _, r in df.iterrows()}


def main() -> None:
    grants = _index(pd.read_excel(RAW / "Grants_and_Scholarships_2025.xlsx"))
    enroll = _index(pd.read_excel(RAW / "JD_Enrollment_and_Ethnicity_2025.xlsx"))
    emp = _index(pd.read_excel(RAW / "Employment_Summary_2025.xlsx"))
    tuition = _index(pd.read_excel(RAW / "Tuitions_and_Fees_Living_Expenses_Cond._Scholarships_2025.xlsx"))
    transfers = _index(pd.read_excel(RAW / "Transfers_2025.xlsx"))

    data = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    schools = data["schools"]

    covered, missing = [], []
    warnings = []

    for school in schools:
        sid = school["id"]
        aba = ID_TO_ABA.get(sid)
        if aba is None or aba not in grants:
            missing.append(sid)
            continue

        g = grants[aba]
        total = _num(g["Total Number # of Students Total #"])
        recip = _num(g["Total Number # of Recieving Grants Total #"])
        less_half = _num(g["Less than half tuition Total Number #"])
        half_full = _num(g["Half to full tuition total Number #"])
        full = _num(g["Full tuition total Number #"])
        more_full = _num(g["More than full tuition total Number #"])

        if total <= 0:
            warnings.append(f"{sid}: grants total=0, skipped scholarship grid")
            full_pct = half_to_full_pct = less_than_half_pct = no_pct = None
        else:
            full_pct = round((full + more_full) / total, 4)
            half_to_full_pct = round(half_full / total, 4)
            less_than_half_pct = round(less_half / total, 4)
            no_pct = round((total - recip) / total, 4)
            grid_sum = (full_pct or 0) + half_to_full_pct + less_than_half_pct + no_pct
            if not (0.95 <= grid_sum <= 1.05):
                warnings.append(f"{sid}: scholarship grid sums to {grid_sum:.3f}")

        class_1l = enroll.get(aba)
        class_size_1l = int(_num(class_1l["TotalJD1Total"])) if class_1l is not None else None

        e = emp.get(aba)
        if e is not None and _num(e["Total_GraduatesTotal"]) > 0:
            grads = _num(e["Total_GraduatesTotal"])
            ftlt_bar = _num(e["Employed_BarAdmissionRequiredFTLT"])
            ftlt_jd = _num(e["Employed_JDAdvantageFTLT"])
            employed_10mo_pct = round((ftlt_bar + ftlt_jd) / grads, 4)
            school_funded_pct = round(_num(e["Funded_TotTotalEmployed"]) / grads, 4)
        else:
            employed_10mo_pct = school_funded_pct = None
            warnings.append(f"{sid}: no employment row / 0 grads")

        t = tuition.get(aba)
        conditional = bool(t is not None and str(t["OfferScholorships"]).strip().upper() == "Y")

        tr = transfers.get(aba)
        transfers_in = int(_num(tr["TransferIn"])) if tr is not None else None
        transfers_out = int(_num(tr["JD1 Transfers Out"])) if tr is not None else None

        school["class_size_1l"] = class_size_1l
        school["scholarship_full_pct"] = full_pct
        school["scholarship_half_to_full_pct"] = half_to_full_pct
        school["scholarship_less_than_half_pct"] = less_than_half_pct
        school["no_scholarship_pct"] = no_pct
        school["conditional_scholarship"] = conditional
        school["employed_10mo_pct"] = employed_10mo_pct
        school["school_funded_pct"] = school_funded_pct
        school["transfers_in"] = transfers_in
        school["transfers_out"] = transfers_out
        covered.append(sid)

    JSON_PATH.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    print(f"covered {len(covered)}/{len(schools)} schools")
    if missing:
        print("MISSING (no ABA match):", ", ".join(missing))
    if warnings:
        print("WARNINGS:")
        for w in warnings:
            print("  -", w)


if __name__ == "__main__":
    main()
