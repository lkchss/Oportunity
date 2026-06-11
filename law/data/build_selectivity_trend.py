"""
Multi-year 509 selectivity trend: merge LSAT_50, GPA_50, and acceptance rate
per school per year (2023, 2024, 2025) into law_schools.json.

Reads the ABA "First Year Class" bulk xlsx files for all available cycles from
law/data/raw/.  Missing files are skipped gracefully (future-proofs against
running before a new cycle is downloaded).  The builder uses the same
ID_TO_ABA + SCHOOL_META name mapping that all other builders use.

Field written (DISPLAY-ONLY, never scored):
    selectivity_trend: {
        "years":       [2023, 2024, 2025],
        "lsat_50":     [165, 166, 167],
        "gpa_50":      [3.70, 3.72, 3.75],
        "accept_rate": [0.28, 0.24, 0.21],   # fraction 0-1
    }
    Only years actually parsed are included.  Schools absent from an older
    file simply get fewer data points.  Schools with only one data point get
    selectivity_trend = None (not enough for a trend).

Run:  python -m law.data.build_selectivity_trend   (from repo root)
"""

import json
from pathlib import Path
from typing import Optional

import pandas as pd

from law.data import build_enrichment as be
from law.data import build_schools as bs

RAW = Path(__file__).parent / "raw"
JSON_PATH = Path(__file__).parent / "law_schools.json"

# Cycles to load, in chronological order.
CYCLES = [2023, 2024, 2025]

# File name pattern for the raw xlsx files.
def _fy_path(year: int) -> Path:
    return RAW / f"First_Year_Class_{year}.xlsx"


def _id_to_aba() -> dict[str, str]:
    """Full school-id -> ABA SchoolName map (75 explicit + expansion schools)."""
    mapping = dict(be.ID_TO_ABA)
    for aba_key, (_state, _rank, display) in bs.SCHOOL_META.items():
        mapping.setdefault(bs._slug(display or aba_key), aba_key)
    return mapping


def _load_cycle(year: int) -> Optional[dict[str, pd.Series]]:
    """Load one First Year Class xlsx; return SchoolName -> row dict, or None."""
    path = _fy_path(year)
    if not path.exists():
        return None
    df = pd.read_excel(path)
    return {str(r["SchoolName"]).strip(): r for _, r in df.iterrows()}


def _parse_row(row: pd.Series) -> Optional[dict]:
    """Extract LSAT_50, GPA_50, accept_rate from a row; None if data missing."""
    lsat = be._num(row["All50thPercentileLSAT"])
    gpa = be._num(row["All50thPercentileUGPA"])
    if lsat <= 0 or gpa <= 0:
        return None

    # AcceptanceRate in the ABA file is a percentage (e.g. 9.58 means 9.58%).
    # Convert to fraction.
    acc_pct = be._num(row["AcceptanceRate"])
    if acc_pct > 0:
        accept_rate = round(acc_pct / 100, 4)
    else:
        # Fall back to offers/applications if AcceptanceRate cell is blank.
        apps = be._num(row["Applications"])
        offers = be._num(row["Offers"])
        accept_rate = round(offers / apps, 4) if apps > 0 else None

    return {
        "lsat_50": int(lsat),
        "gpa_50": round(gpa, 2),
        "accept_rate": accept_rate,
    }


def main(json_path: Optional[Path] = None) -> None:
    target = json_path if json_path is not None else JSON_PATH
    # Load each available cycle.
    cycles: dict[int, dict[str, pd.Series]] = {}
    for year in CYCLES:
        idx = _load_cycle(year)
        if idx is None:
            print(f"[selectivity_trend] {year}: file not found, skipping")
        else:
            print(f"[selectivity_trend] {year}: loaded {len(idx)} schools")
            cycles[year] = idx

    if not cycles:
        print("[selectivity_trend] no cycle files found — nothing to do")
        return

    mapping = _id_to_aba()  # school-id -> ABA SchoolName

    data = json.loads(target.read_text(encoding="utf-8"))
    schools = data["schools"]

    covered, missing, single_year = [], [], []

    for school in schools:
        sid = school["id"]
        aba = mapping.get(sid)
        if aba is None:
            school["selectivity_trend"] = None
            missing.append(sid)
            continue

        years_out, lsat_out, gpa_out, acc_out = [], [], [], []
        for year in CYCLES:
            idx = cycles.get(year)
            if idx is None:
                continue  # file not downloaded yet
            row = idx.get(aba)
            if row is None:
                continue  # school not in this cycle's file
            parsed = _parse_row(row)
            if parsed is None:
                continue  # data missing for this school/year
            years_out.append(year)
            lsat_out.append(parsed["lsat_50"])
            gpa_out.append(parsed["gpa_50"])
            acc_out.append(parsed["accept_rate"])

        if len(years_out) < 2:
            # Fewer than 2 data points — no displayable trend.
            school["selectivity_trend"] = None
            if len(years_out) == 1:
                single_year.append(sid)
            else:
                missing.append(sid)
            continue

        school["selectivity_trend"] = {
            "years": years_out,
            "lsat_50": lsat_out,
            "gpa_50": gpa_out,
            "accept_rate": acc_out,
        }
        covered.append(sid)

    target.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    # Coverage report
    print(f"\n=== Selectivity trend coverage report ===")
    print(f"Schools with trend (>=2 years): {len(covered)}/{len(schools)}")
    print(f"Schools with only 1 year:       {len(single_year)}")
    print(f"Schools with no ABA match:      {len(missing)}")

    # Per-year coverage
    for year in CYCLES:
        if year not in cycles:
            continue
        idx = cycles[year]
        n = sum(1 for s in schools
                for aba in [mapping.get(s["id"])]
                if aba and aba in idx)
        print(f"  {year}: {n}/{len(schools)} schools have data in file")


if __name__ == "__main__":
    main()
