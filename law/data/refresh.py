"""
Annual data-refresh pipeline for law/data/law_schools.json.

Orchestrates the build scripts in correct dependency order:
  1. build_schools  — base records from ABA bulk xlsx (also calls build_enrichment)
  2. build_quality  — attrition / faculty / curricular ABA fields
  3. build_scorecard — College Scorecard JD debt + earnings

DEFAULT (dry run): runs the full pipeline against a TEMP COPY of law_schools.json,
then prints a diff report (schools added/removed, changed-field counts, example
before→after values). The real law_schools.json is NEVER touched without --write.

  python law/data/refresh.py                      # dry run (safe, read-only)
  python law/data/refresh.py --write              # apply to the real file + validate
  python law/data/refresh.py --include-notable    # also run build_notable --merge
                                                  # (WARNING: hits Wikipedia network)

Run from the repo root.
"""

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_DATA_DIR = Path(__file__).parent
_REAL_JSON = _DATA_DIR / "law_schools.json"


# ---------------------------------------------------------------------------
# Pipeline steps
# ---------------------------------------------------------------------------

def _run_build_schools(json_path: Path) -> None:
    """Step 1: add missing ABA base records (also calls build_enrichment internally)."""
    from law.data import build_schools as bs
    print("[refresh] step 1/3: build_schools (+ build_enrichment)")
    bs.main(json_path=json_path)


def _run_build_quality(json_path: Path) -> None:
    """Step 2: merge ABA attrition / faculty / curricular fields."""
    from law.data import build_quality as bq
    print("[refresh] step 2/3: build_quality")
    bq.main(json_path=json_path)


def _run_build_scorecard(json_path: Path) -> None:
    """Step 3: merge College Scorecard JD debt + earnings."""
    from law.data import build_scorecard as bsc
    print("[refresh] step 3/3: build_scorecard")
    bsc.main(json_path=json_path)


def _run_build_employment_states(json_path: Path) -> None:
    """Step 4: merge per-school ABA placement-by-state data (skipped if extract absent)."""
    from law.data import build_employment_states as bes
    extract = bes.EXTRACT_JSON
    if not extract.exists():
        print(
            "[refresh] step 4/4: build_employment_states — SKIPPED "
            f"(extract not found: {extract}; run build_employment_states to populate)"
        )
        return
    print("[refresh] step 4/4: build_employment_states (--merge-only)")
    bes.main(json_path=json_path, merge_only=True)


def _run_build_notable(json_path: Path) -> None:
    """Optional step: merge notable alumni/faculty from Wikipedia cache."""
    from law.data import build_notable as bn
    import argparse as _ap
    print("[refresh] optional: build_notable --merge")
    # Reuse cmd_merge with a fake args namespace; it reads JSON_PATH directly,
    # so we temporarily monkey-patch it.
    original = bn.JSON_PATH
    bn.JSON_PATH = json_path
    try:
        bn.cmd_merge(_ap.Namespace())
    finally:
        bn.JSON_PATH = original


def run_pipeline(json_path: Path, include_notable: bool = False) -> None:
    """Run all pipeline steps against *json_path* in dependency order."""
    _run_build_schools(json_path)
    _run_build_quality(json_path)
    _run_build_scorecard(json_path)
    _run_build_employment_states(json_path)
    if include_notable:
        _run_build_notable(json_path)


# ---------------------------------------------------------------------------
# Diff report logic (pure — easy to unit-test)
# ---------------------------------------------------------------------------

def compute_diff(
    before: dict[str, Any],
    after: dict[str, Any],
    notable_fields: frozenset[str] = frozenset(
        {"notable_alumni", "notable_faculty", "wiki_title",
         "placement_states", "placement_year"}
    ),
    max_examples: int = 3,
) -> dict[str, Any]:
    """Compute a structured diff between two dataset dicts (each has a 'schools' list).

    Fields in *notable_fields* are excluded from the diff — they are produced by
    optional build steps (build_notable, build_employment_states) that are excluded
    by default; reporting them as removed would be misleading.

    Returns a dict with:
        schools_added   – list of school ids present in after but not before
        schools_removed – list of school ids present in before but not after
        field_change_counts – {field_name: count_of_schools_where_value_changed}
        field_examples  – {field_name: [{id, before, after}, ...]} (up to max_examples)
    """
    before_by_id: dict[str, dict] = {s["id"]: s for s in before.get("schools", [])}
    after_by_id: dict[str, dict] = {s["id"]: s for s in after.get("schools", [])}

    before_ids = set(before_by_id)
    after_ids = set(after_by_id)

    schools_added = sorted(after_ids - before_ids)
    schools_removed = sorted(before_ids - after_ids)

    field_change_counts: dict[str, int] = {}
    field_examples: dict[str, list[dict]] = {}

    common_ids = before_ids & after_ids
    for sid in common_ids:
        old = before_by_id[sid]
        new = after_by_id[sid]
        all_keys = set(old) | set(new)
        for key in all_keys:
            if key in notable_fields:
                continue
            old_val = old.get(key)
            new_val = new.get(key)
            if old_val != new_val:
                field_change_counts[key] = field_change_counts.get(key, 0) + 1
                examples = field_examples.setdefault(key, [])
                if len(examples) < max_examples:
                    examples.append({"id": sid, "before": old_val, "after": new_val})

    return {
        "schools_added": schools_added,
        "schools_removed": schools_removed,
        "field_change_counts": field_change_counts,
        "field_examples": field_examples,
    }


def print_diff_report(diff: dict[str, Any]) -> None:
    """Print a human-readable diff report to stdout."""
    added = diff["schools_added"]
    removed = diff["schools_removed"]
    changes = diff["field_change_counts"]
    examples = diff["field_examples"]

    print("\n" + "=" * 60)
    print("REFRESH DRY-RUN DIFF REPORT")
    print("=" * 60)

    if added:
        print(f"\nSchools ADDED ({len(added)}):")
        for sid in added:
            print(f"  + {sid}")
    else:
        print("\nSchools added: none")

    if removed:
        print(f"\nSchools REMOVED ({len(removed)}):")
        for sid in removed:
            print(f"  - {sid}")
    else:
        print("Schools removed: none")

    if changes:
        print(f"\nChanged fields ({len(changes)} fields across dataset):")
        for field, count in sorted(changes.items(), key=lambda x: -x[1]):
            print(f"  {field}: {count} school(s) changed")
            for ex in examples.get(field, []):
                print(f"      [{ex['id']}] {ex['before']!r} -> {ex['after']!r}")
    else:
        print("\nField changes: none (dataset is already up to date)")

    total_field_changes = sum(changes.values())
    print(f"\nSummary: {len(added)} added, {len(removed)} removed, "
          f"{total_field_changes} total field-level changes across "
          f"{len(changes)} distinct field(s).")
    print("=" * 60)


# ---------------------------------------------------------------------------
# Validation helper
# ---------------------------------------------------------------------------

def _validate(json_path: Path) -> None:
    """Run data_loader validation against *json_path*. Raises on failure."""
    import json as _json
    import law.data_loader as dl
    original = dl._get_data_path
    dl._get_data_path = lambda: json_path
    try:
        dl.load_law_schools()
    finally:
        dl._get_data_path = original


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument(
        "--write",
        action="store_true",
        help="apply the refreshed dataset to the real law_schools.json "
             "(runs data_loader validation first)",
    )
    ap.add_argument(
        "--include-notable",
        action="store_true",
        dest="include_notable",
        help=(
            "WARNING: hits en.wikipedia.org for every school. "
            "Folds notable.json cache into the refreshed dataset using "
            "build_notable --merge."
        ),
    )
    args = ap.parse_args()

    if not _REAL_JSON.exists():
        sys.exit(f"error: {_REAL_JSON} not found — run from the repo root")

    if args.include_notable:
        print(
            "WARNING: --include-notable will make network requests to "
            "en.wikipedia.org.\n"
        )

    # Snapshot the current dataset for diffing.
    before = json.loads(_REAL_JSON.read_text(encoding="utf-8"))

    # Work on a temp copy so the real file is never touched by the pipeline.
    with tempfile.TemporaryDirectory(prefix="law_refresh_") as tmp_dir:
        tmp_json = Path(tmp_dir) / "law_schools.json"
        shutil.copy2(_REAL_JSON, tmp_json)

        print(f"[refresh] working on temp copy: {tmp_json}")
        run_pipeline(tmp_json, include_notable=args.include_notable)

        after = json.loads(tmp_json.read_text(encoding="utf-8"))
        diff = compute_diff(before, after)
        print_diff_report(diff)

        if args.write:
            print("\n[refresh] --write requested: validating before applying...")
            _validate(tmp_json)
            shutil.copy2(tmp_json, _REAL_JSON)
            print(f"[refresh] wrote refreshed dataset to {_REAL_JSON}")
        else:
            print("\n(dry run — real law_schools.json unchanged; pass --write to apply)")


if __name__ == "__main__":
    main()
