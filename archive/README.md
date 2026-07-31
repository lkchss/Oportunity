# archive/

Frozen artifacts from the April 2026 law-matcher prototype, moved out of the
repo root 2026-07-31 because they actively mislead anyone (or any agent)
orienting from the root: `ALGORITHM_FIXES_SUMMARY.md` describes a 52-school
dataset, 38 tests, a "Practice Area 15%" weight and a duplicate-Northwestern
bug — none of which survived into the current 196-school six-score matcher —
and `V2_ISSUES.md`'s acceptance criteria are long done or superseded.

Nothing here is load-bearing: no tracked file references these (verified via
`git grep` before the move), and the two `run_*_profiles.py` scripts target
the pre-rewrite matcher API. Kept for history rather than deleted; full
lineage is in git anyway.
