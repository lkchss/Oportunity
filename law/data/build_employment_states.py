"""
Parse per-school ABA Employment Summary Reports to extract placement-by-state data.

Source: ABA Required Disclosures backend API
  https://backend.abarequireddisclosures.org/api/EmploymentOutcomes/
  GenerateIndividualEQSummaryReport?schoolId=<N>&year=2024

Each report (PDF) includes an "Employment Location" section:
  State/U.S. Territory - Largest Employment    <STATE NAME>  <N>
  State/U.S. Territory - 2nd Largest Employment ...
  State/U.S. Territory - 3rd Largest Employment ...
  Employed in Foreign Countries                             <N>

Workflow:
  a) Download phase  — fetch all valid ABA school IDs (probe 1-250), save PDFs
     to law/data/raw/employment_states/<id>.pdf. Skip already-downloaded files
     so re-runs are cheap.  1.75s polite delay between requests.
  b) Parse phase     — extract school name + location counts from each PDF;
     write intermediate law/data/raw/employment_states.json.
  c) Match phase     — match ABA school names to our law_schools.json IDs using
     the existing ID_TO_ABA + SCHOOL_META mappings (same logic as build_quality).
  d) Merge phase     — write placement_states + placement_year to law_schools.json;
     print coverage report.

Run:
  python -m law.data.build_employment_states            # full pipeline
  python -m law.data.build_employment_states --skip-download  # parse+merge only
  python -m law.data.build_employment_states --merge-only     # merge from existing extract
"""

import argparse
import io
import json
import re
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Optional

# ---- optional pdfplumber import (graceful failure) ----
try:
    import pdfplumber  # type: ignore
    _HAS_PDFPLUMBER = True
except ImportError:
    _HAS_PDFPLUMBER = False

RAW_DIR = Path(__file__).parent / "raw" / "employment_states"
EXTRACT_JSON = Path(__file__).parent / "raw" / "employment_states.json"
JSON_PATH = Path(__file__).parent / "law_schools.json"

YEAR = 2024
BASE_URL = (
    "https://backend.abarequireddisclosures.org/api/EmploymentOutcomes/"
    "GenerateIndividualEQSummaryReport?schoolId={school_id}&year={year}"
)

# Probe range: IDs observed up to 226, leave headroom.
PROBE_MAX = 250
POLITE_DELAY = 1.75  # seconds between downloads

# Full state-name → 2-letter code mapping (US territories included).
STATE_NAMES: dict[str, str] = {
    "ALABAMA": "AL", "ALASKA": "AK", "ARIZONA": "AZ", "ARKANSAS": "AR",
    "CALIFORNIA": "CA", "COLORADO": "CO", "CONNECTICUT": "CT",
    "DELAWARE": "DE", "DISTRICT OF COLUMBIA": "DC", "FLORIDA": "FL",
    "GEORGIA": "GA", "HAWAII": "HI", "IDAHO": "ID", "ILLINOIS": "IL",
    "INDIANA": "IN", "IOWA": "IA", "KANSAS": "KS", "KENTUCKY": "KY",
    "LOUISIANA": "LA", "MAINE": "ME", "MARYLAND": "MD",
    "MASSACHUSETTS": "MA", "MICHIGAN": "MI", "MINNESOTA": "MN",
    "MISSISSIPPI": "MS", "MISSOURI": "MO", "MONTANA": "MT",
    "NEBRASKA": "NE", "NEVADA": "NV", "NEW HAMPSHIRE": "NH",
    "NEW JERSEY": "NJ", "NEW MEXICO": "NM", "NEW YORK": "NY",
    "NORTH CAROLINA": "NC", "NORTH DAKOTA": "ND", "OHIO": "OH",
    "OKLAHOMA": "OK", "OREGON": "OR", "PENNSYLVANIA": "PA",
    "RHODE ISLAND": "RI", "SOUTH CAROLINA": "SC", "SOUTH DAKOTA": "SD",
    "TENNESSEE": "TN", "TEXAS": "TX", "UTAH": "UT", "VERMONT": "VT",
    "VIRGINIA": "VA", "WASHINGTON": "WA", "WEST VIRGINIA": "WV",
    "WISCONSIN": "WI", "WYOMING": "WY",
    "PUERTO RICO": "PR", "GUAM": "GU", "VIRGIN ISLANDS": "VI",
    "NORTHERN MARIANA ISLANDS": "MP", "AMERICAN SAMOA": "AS",
}


# ---------------------------------------------------------------------------
# Name-normalisation helpers (mirror build_quality / build_enrichment logic)
# ---------------------------------------------------------------------------

def _build_name_to_id(schools: list[dict]) -> dict[str, str]:
    """Build ABA-name → our-id lookup using existing mapping tables.

    Priority order:
      1. ID_TO_ABA (75 explicit reverse-mapped entries)
      2. SCHOOL_META display names (slug match)
      3. SCHOOL_META raw ABA keys
    All keys are upper-cased for comparison against PDF headers.
    """
    from law.data import build_enrichment as be
    from law.data import build_schools as bs

    name_to_id: dict[str, str] = {}

    # 1) Invert ID_TO_ABA: aba_name.upper() -> our id
    for our_id, aba_name in be.ID_TO_ABA.items():
        name_to_id[aba_name.upper()] = our_id

    # 2) SCHOOL_META: aba_key.upper() -> slug(display_name) if known
    for aba_key, (_state, _rank, display) in bs.SCHOOL_META.items():
        slug = bs._slug(display or aba_key)
        name_to_id[aba_key.upper()] = slug

    # 3) Also map display names (upper) -> slug, for direct PDF header matches
    for aba_key, (_state, _rank, display) in bs.SCHOOL_META.items():
        if display:
            slug = bs._slug(display or aba_key)
            name_to_id[display.upper()] = slug

    # Verify slugs are real school IDs (drop phantoms)
    valid_ids = {s["id"] for s in schools}
    return {k: v for k, v in name_to_id.items() if v in valid_ids}


def _normalise_pdf_name(raw: str) -> str:
    """Normalise the PDF school-name header for lookup."""
    return raw.strip().upper()


# ---------------------------------------------------------------------------
# Download phase
# ---------------------------------------------------------------------------

def _is_valid_pdf(data: bytes) -> bool:
    return data[:4] == b"%PDF"


def _fetch_pdf(school_id: int) -> Optional[bytes]:
    url = BASE_URL.format(school_id=school_id, year=YEAR)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = resp.read()
        return data if _is_valid_pdf(data) else None
    except (urllib.error.HTTPError, urllib.error.URLError, OSError):
        return None


def download_phase(skip_existing: bool = True) -> list[int]:
    """Probe IDs 1-PROBE_MAX, download valid PDFs, return list of saved IDs."""
    if not _HAS_PDFPLUMBER:
        raise RuntimeError("pdfplumber is not installed — run: pip install pdfplumber")

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    saved_ids: list[int] = []

    for sid in range(1, PROBE_MAX + 1):
        dest = RAW_DIR / f"{sid}.pdf"
        if skip_existing and dest.exists() and dest.stat().st_size > 10_000:
            saved_ids.append(sid)
            continue

        data = _fetch_pdf(sid)
        if data is not None:
            dest.write_bytes(data)
            saved_ids.append(sid)
            print(f"  downloaded ID {sid:4d} ({len(data):,} bytes)")
        else:
            # 400/404 = invalid ID; no message needed
            pass

        time.sleep(POLITE_DELAY)

    print(f"[download] {len(saved_ids)} PDFs in {RAW_DIR}")
    return saved_ids


# ---------------------------------------------------------------------------
# Parse phase
# ---------------------------------------------------------------------------

def _parse_pdf_bytes(data: bytes) -> Optional[dict]:
    """Extract school name + employment location from a PDF's bytes.
    Returns None if parsing fails or the location section is absent."""
    if not _HAS_PDFPLUMBER:
        return None
    try:
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            text = pdf.pages[0].extract_text() or ""
    except Exception:
        return None

    lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
    if not lines:
        return None
    school_name = lines[0]

    # Total graduates
    m = re.search(r"Total Graduates\s+(\d+)", text)
    total_grads = int(m.group(1)) if m else None

    # Employment location section
    loc_re = re.compile(
        r"State/U\.S\. Territory - (?:Largest|2nd Largest|3rd Largest) Employment"
        r"\s+([A-Z][A-Z ]+[A-Z])\s+(\d+)"
    )
    locations = []
    for lm in loc_re.finditer(text):
        state_full = lm.group(1).strip().upper()
        count = int(lm.group(2))
        # Skip "UNKNOWN" — ABA uses it when location data is not reported
        if state_full == "UNKNOWN":
            continue
        code = STATE_NAMES.get(state_full, state_full[:2] if len(state_full) >= 2 else state_full)
        locations.append({"state": code, "count": count})

    if not locations:
        return None  # Report exists but no usable state data

    fm = re.search(r"Employed in Foreign Countries\s+(\d+)", text)
    foreign = int(fm.group(1)) if fm else 0

    return {
        "school_name": school_name,
        "total_grads": total_grads,
        "locations": locations,
        "foreign": foreign,
    }


def parse_phase(saved_ids: list[int]) -> dict[int, dict]:
    """Parse all downloaded PDFs; return id -> parsed-data dict."""
    results: dict[int, dict] = {}
    failed: list[int] = []

    for sid in saved_ids:
        pdf_path = RAW_DIR / f"{sid}.pdf"
        if not pdf_path.exists():
            continue
        parsed = _parse_pdf_bytes(pdf_path.read_bytes())
        if parsed is None:
            failed.append(sid)
        else:
            results[sid] = parsed

    if failed:
        print(f"[parse] FAILED to parse {len(failed)} PDFs: {failed}")
    print(f"[parse] successfully parsed {len(results)} / {len(saved_ids)} PDFs")
    return results


# ---------------------------------------------------------------------------
# Match + merge phase
# ---------------------------------------------------------------------------

def _compute_pct(count: int, total: int) -> float:
    """Round percentage to one decimal place."""
    if total <= 0:
        return 0.0
    return round(count / total * 100, 1)


def merge_phase(
    parsed: dict[int, dict],
    json_path: Optional[Path] = None,
) -> None:
    """Match parsed data to law_schools.json entries; write placement fields."""
    target = json_path if json_path is not None else JSON_PATH
    data = json.loads(target.read_text(encoding="utf-8"))
    schools = data["schools"]

    name_to_id = _build_name_to_id(schools)
    by_id = {s["id"]: s for s in schools}

    matched_aba: dict[str, dict] = {}  # our_id -> parsed data (best match)
    unmatched_pdfs: list[str] = []

    for aba_id, parsed_data in parsed.items():
        pdf_name = _normalise_pdf_name(parsed_data["school_name"])
        our_id = name_to_id.get(pdf_name)

        if our_id is None:
            # Attempt partial match: strip trailing words until a match is found
            parts = pdf_name.split()
            for end in range(len(parts), 0, -1):
                candidate = " ".join(parts[:end])
                if candidate in name_to_id:
                    our_id = name_to_id[candidate]
                    break

        if our_id is None:
            unmatched_pdfs.append(f"ABA_ID={aba_id}: {pdf_name!r}")
            continue

        # Prefer the match with more grads (should be the same school; skip dupes)
        existing = matched_aba.get(our_id)
        if existing is None or (parsed_data["total_grads"] or 0) > (existing["total_grads"] or 0):
            matched_aba[our_id] = parsed_data

    # Write placement fields
    matched_schools, missing_schools, zero_grads = [], [], []

    for school in schools:
        sid = school["id"]
        pdata = matched_aba.get(sid)

        if pdata is None:
            # Clear stale fields
            school["placement_states"] = None
            school["placement_year"] = None
            missing_schools.append(sid)
            continue

        total = pdata.get("total_grads") or 0
        locs = pdata.get("locations", [])

        if total == 0 or not locs:
            school["placement_states"] = None
            school["placement_year"] = None
            zero_grads.append(sid)
            continue

        placement = [
            {"state": loc["state"], "pct": _compute_pct(loc["count"], total)}
            for loc in locs
        ]
        school["placement_states"] = placement
        school["placement_year"] = YEAR
        matched_schools.append(sid)

    # Save the extract for reproducibility
    extract = {str(k): v for k, v in parsed.items()}
    EXTRACT_JSON.write_text(json.dumps(extract, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"[merge] wrote intermediate extract to {EXTRACT_JSON}")

    target.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    print("\n=== Coverage report ===")
    print(f"Parsed PDFs:          {len(parsed)}")
    print(f"Matched to schools:   {len(matched_schools)}/{len(schools)}")
    print(f"No grad data:         {len(zero_grads)}")
    print(f"No match in JSON:     {len(missing_schools)}")
    if unmatched_pdfs:
        print(f"Unmatched ABA PDFs ({len(unmatched_pdfs)}):")
        for u in unmatched_pdfs:
            print(f"  {u}")
    if missing_schools:
        print(f"Missing schools ({len(missing_schools)}):")
        for s in missing_schools[:20]:
            print(f"  {s}")
        if len(missing_schools) > 20:
            print(f"  ... and {len(missing_schools) - 20} more")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main(json_path: Optional[Path] = None, skip_download: bool = False, merge_only: bool = False) -> None:
    if not _HAS_PDFPLUMBER:
        print("ERROR: pdfplumber not installed.  Run:  pip install pdfplumber")
        return

    if merge_only:
        # Load previously saved extract
        if not EXTRACT_JSON.exists():
            print(f"ERROR: {EXTRACT_JSON} not found — run without --merge-only first")
            return
        raw = json.loads(EXTRACT_JSON.read_text(encoding="utf-8"))
        parsed = {int(k): v for k, v in raw.items()}
        print(f"[merge-only] loaded {len(parsed)} records from {EXTRACT_JSON}")
    else:
        if skip_download:
            # Use already-downloaded PDFs
            existing = sorted(
                int(p.stem) for p in RAW_DIR.glob("*.pdf")
                if p.stat().st_size > 10_000
            )
            print(f"[skip-download] using {len(existing)} existing PDFs")
            saved_ids = existing
        else:
            saved_ids = download_phase(skip_existing=True)

        parsed = parse_phase(saved_ids)

    merge_phase(parsed, json_path=json_path)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--skip-download", action="store_true",
                    help="skip download phase; parse already-downloaded PDFs")
    ap.add_argument("--merge-only", action="store_true",
                    help="merge from existing employment_states.json extract only")
    args = ap.parse_args()
    main(skip_download=args.skip_download, merge_only=args.merge_only)
