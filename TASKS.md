## Backlog
- [ ] (TRIED & REVERTED) over-qualification dampener: composite multiplier (1-min((overshoot-3)/30, .45)) on schools far above the applicant's reach. Cleanly fixed p18 (Jacksonville off #1) but LLM-judge 7-11 (39%) -> REVERT. Regressions spanned high-stats non-cost-sensitive profiles (p07/p08/p12/p20), so it's not a calibration miss: the judge WANTS affordable safeties in lists, and any dampener strong enough to move Jacksonville off #1 also pushes down safeties it likes. Don't retry a global dampener; the Jacksonville-style intrusion is apparently tolerated by the judge. The matcher is now plateaued (data-blocked + judge rewards no further re-weighting).
- [ ] (still verify, low priority) 4 assigned elite ranks (Berkeley 10/Georgetown 14/UT 16/UNC 22) + soft estimated defaults (salary $90k/$58k, COL, lrap=moderate, target_states=[home]) are mine-from-memory/heuristic. Known minor data: wilmington (brand-new, no employment/bar outcomes -> honest zeros), ohio-northern (scholarship grid sums to 1.78 but no_scholarship_pct isn't scored, cosmetic), marquette bar=0 (WI diploma privilege).
- [ ] Optionally merge a real US News 2026 rank list for the 83-150 band (currently RNP-sentinel 999; prestige floors at ~0 past rank 84 so low impact).
- [ ] Refine plain web styling into final visual design (placeholder style in law/web/); render usnwr_rank_2026==999 as "Unranked" in web/server like the judge prompt now does.
- [ ] UI/UX streamlining pass (informed by stress test findings)
- [ ] p14 (no-LSAT/MA/65k-130k): UMass (in-state MA, affordable) now IS in the dataset, but expansion still regressed p14 — cheap out-of-state schools pushed MA schools down (the over-qualification/intrusion artifact above). Fixing the dampener should also fix p14.
- [ ] Add class_size_1l -> admissibility softener (transfers now done as a feature)
- [ ] Tier-3 STILL BLOCKED ON DATA: median_grad_debt (LST blocked, not in ABA) + placement_by_state (per-school PDFs).
      Real debt $ remains the #1 judge ask. Bar passage + conditional-retention DONE.
- [ ] Open PR for algo-optimization (pushed to origin; URL: github.com/lkchss/Opportunity/pull/new/algo-optimization)
- [ ] Render transfer-up plan styling in the final UI pass (TransferPanel is placeholder-styled)
- [ ] Add lower-ranked schools (ranks 83+) so the transfer-up launchpad list works for genuinely-not-T14 profiles (157/3.4 currently has 0 safety/target)
- [ ] Data enrichment HARD/predicted (later): selectivity trend (multi-year), NLJ250-by-market, part-time/transfer

## In progress

## Done
- [x] Verify the 121 new schools + fix tuition bug: audit found 27 schools with annual_tuition=$0 (they bill per-credit; *Annual cols blank). Fixed build_schools to fall back to FT_*_Credit x 30 credits/yr. Now all 196 have valid tuition, unique ids, valid states, monotonic LSAT/GPA percentiles, real career data. Bonus: correct tuition knocked the p18 Jacksonville intrusion from #1 to #4.
- [x] Expand coverage 75 -> 196 schools: add all 121 missing ABA schools via law/data/build_schools.py (base record from First_Year_Class admissibility + Tuitions + The_Basics; enrichment fills real career/scholarship/bar/transfers). Fixes the coverage cliff (was 0 schools with median LSAT <=155; sub-156 applicants now get real safety/target lists). Includes elite gaps Berkeley/Georgetown/UT-Austin/UNC + UMass. LLM-judge 12-9 (57%) -> KEEP (marginal; depressed by the over-qualification artifact now queued as next lever). Also: dti computed from rounded net_debt (test invariant); judge prompt renders RNP.
- [x] Remove unused LLM narrative generator (law/llm_client.py + dead app-import test). Not wired into server/matcher.
- [x] Fix p03 regression: cost-sensitivity financial-weight floor in _composite (scholarship slider no longer starves financial weight). LLM-judge 10-5 (67%) -> KEEP. Fixed p03/p09/p16/p23; losses spread (p01/p02/p08/p15/p17), not concentrated.
- [x] Push algo-optimization branch to origin (17 commits).
- [x] Conditional-scholarship penalty scaled by real reduction_rate (data + matcher). LLM-judge 5-4 (56%, marginal) -> KEEP.
- [x] Wire bar_pass_vs_state into career fit (±10% value-add). LLM-judge 17-7 (71%) -> KEEP, commit 35e6f49.
- [x] Add ABA 2026 bar passage data (first-time, state avg, vs-state, ultimate) for all 75. Commit + detail-screen surfacing.
- [x] Finish transfer feature: surface mobility + bar passage on school detail screen.
- [x] Transfer-up feature: _transfer_metrics + transfer_up_plan (launchpads/targets) in matcher, /api/match transfer_plan, TransferPanel UI, 6 tests. Commit daa4697.
- [x] Tier-3 available part: recompute 5 real career outcome rates from ABA Employment Summary. LLM-judge 17-7 (71%) -> KEEP, commit 5adb764.
- [x] Normalize grid scholarship generosity to dataset max. LLM-judge 13-2 (87%) over iter-1 -> KEEP, committed d9f90f3.
      Recovered 5 of 6 prior regressions; regressions now 2 (p03, p14).
- [x] Wire ABA enrichment into matcher (real aid grid, grid generosity + conditional penalty, real placement net of school-funded).
      LLM-judge: 18-6 (75% win) over baseline -> KEEP, committed 971bb9c. Real data beats re-weighting (earlier weighting iters ~40%).
- [x] Data enrichment EASY tier: all 75 schools populated from ABA 2025 bulk reports via law/data/build_enrichment.py
      (class_size_1l, scholarship grid, conditional_scholarship, employed_10mo_pct, school_funded_pct) + transfers_in/out
- [x] Build LLM-judge optimization harness (eval/): seeded profiles, blind pairwise diff-only judging via zero-context agents, win-rate gate
- [x] Commit current working tree (all law/ changes since session start) — baseline commit 64f859a on branch algo-optimization
- [x] Build Flask web app (law/server.py + law/web/) from the mock-up: Profile form -> Results table -> School detail, wired to rank_schools (plain placeholder styling)
- [x] Restructure repo into two product lines: mvp/ and law/
- [x] Design and implement five-score matching algorithm (admissibility, career fit, location fit, scholarship, financial)
- [x] Add PSLF/IDR path as display-only financial breakdown (not part of score)
- [x] Build Streamlit UI with new form inputs (target state, in-state residency, income bracket, scholarship slider)
- [x] Verify and patch all 22 schools in law/data/law_schools.json with ABA 509 data (7sage.com 2025-26 cycle)
- [x] Add ranks 42-49 (10 schools) — 32 schools total
- [x] Add ranks 52-70 (18 schools) — 50 schools total
- [x] Write 37-test stress suite covering edge cases, score sanity, ranking stability, financial math (37/37 passing)
- [x] Add T14 (15 schools, ranks 1-13) + ranks 70-82 (10 schools) — 75 schools total (ranks 1-82)
