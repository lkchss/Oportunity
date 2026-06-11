"""
Merge three ABA 2025 quality reports into law_schools.json (all 196 schools):

  Attrition_2025.xlsx            -> attrition_1l_pct        (academic + other 1L attrition rate)
  Faculty_Resources_2025.xlsx    -> faculty_ft_total, student_faculty_ratio
  Curricular_Offerings_2025.xlsx -> clinic_seats_filled, field_placements_filled,
                                    simulation_seats_filled, hands_on_per_student

All fields are DISPLAY-ONLY (school-detail screen): nothing here feeds the
ranking, so the eval suite is unaffected by running this script.

Run:  python -m law.data.build_quality        (from repo root)
"""

import json
from pathlib import Path
from typing import Optional

import pandas as pd

from law.data import build_enrichment as be
from law.data import build_schools as bs

RAW = Path(__file__).parent / "raw"
JSON_PATH = Path(__file__).parent / "law_schools.json"


def _id_to_aba() -> dict[str, str]:
    """Full id -> ABA SchoolName map: the original 75 explicit mappings plus the
    expansion schools, whose ids are slugs of their SCHOOL_META display names."""
    mapping = dict(be.ID_TO_ABA)
    for aba, (_state, _rank, display) in bs.SCHOOL_META.items():
        mapping.setdefault(bs._slug(display or aba), aba)
    return mapping


def _ratio(num: float, den: float, dp: int = 4) -> Optional[float]:
    return round(num / den, dp) if den > 0 else None


def main(json_path: Optional[Path] = None) -> None:
    target = json_path if json_path is not None else JSON_PATH
    attr = be._index(pd.read_excel(RAW / "Attrition_2025.xlsx"))
    fac = be._index(pd.read_excel(RAW / "Faculty_Resources_2025.xlsx"))
    curr = be._index(pd.read_excel(RAW / "Curricular_Offerings_2025.xlsx"))
    enroll = be._index(pd.read_excel(RAW / "JD_Enrollment_and_Ethnicity_2025.xlsx"))

    data = json.loads(target.read_text(encoding="utf-8"))
    schools = data["schools"]
    mapping = _id_to_aba()

    covered, missing = [], []
    for school in schools:
        aba = mapping.get(school["id"])
        if aba is None:
            missing.append(school["id"])
            continue

        en = enroll.get(aba)
        jd1 = be._num(en["TotalJD1Total"]) if en is not None else 0.0
        total_jd = (
            sum(be._num(en[f"TotalJD{y}Total"]) for y in (1, 2, 3, 4))
            if en is not None else 0.0
        )

        # Attrition: academic (dismissed/failed out) + other (left for any other
        # non-transfer reason) among 1Ls, over the 1L class. The report's counts
        # refer to the prior academic year's entering class; current 1L enrollment
        # is the closest available denominator (ABA publishes no per-school base
        # in this file), so treat the rate as an estimate.
        a = attr.get(aba)
        if a is not None and jd1 > 0:
            lost = (be._num(a["AcademicAttrition_TotalJD1Total"])
                    + be._num(a["OtherAttrition_TotalJD1Total"]))
            school["attrition_1l_pct"] = _ratio(lost, jd1)
        else:
            school["attrition_1l_pct"] = None

        f = fac.get(aba)
        ft_faculty = be._num(f["FTTotal"]) if f is not None else 0.0
        school["faculty_ft_total"] = int(ft_faculty) if ft_faculty > 0 else None
        school["student_faculty_ratio"] = (
            _ratio(total_jd, ft_faculty, dp=1) if ft_faculty > 0 and total_jd > 0 else None
        )

        # Hands-on training: seats actually FILLED (not just offered) in clinics,
        # field placements (externships) and simulation courses, plus a combined
        # per-student rate so big and small schools compare fairly.
        c = curr.get(aba)
        if c is not None:
            clinics = be._num(c["LawClinicsFilled"])
            placements = be._num(c["FieldPlacementsFilled"])
            sims = be._num(c["SimulationCoursesFilled"])
            school["clinic_seats_filled"] = int(clinics)
            school["field_placements_filled"] = int(placements)
            school["simulation_seats_filled"] = int(sims)
            school["hands_on_per_student"] = _ratio(clinics + placements + sims, total_jd, dp=2)
        else:
            school["clinic_seats_filled"] = None
            school["field_placements_filled"] = None
            school["simulation_seats_filled"] = None
            school["hands_on_per_student"] = None

        covered.append(school["id"])

    target.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    print(f"covered {len(covered)}/{len(schools)} schools")
    if missing:
        print("MISSING (no ABA match):", ", ".join(missing))
    pops = {
        k: sum(1 for s in schools if s.get(k) is not None)
        for k in ("attrition_1l_pct", "student_faculty_ratio", "hands_on_per_student")
    }
    print("populated:", pops)


if __name__ == "__main__":
    main()
