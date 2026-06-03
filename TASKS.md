## Backlog
- [ ] Refine plain web styling into final visual design (placeholder style in law/web/)
- [ ] UI/UX streamlining pass (informed by stress test findings)
- [ ] Enable LLM narratives (law/llm_client.py is built, currently unused)
- [ ] Next loop iter: 2 residual regressions (p03, p14) — both mid/low-income MA/NY profiles where judge still wants a stronger aid story
- [ ] Add class_size_1l -> admissibility softener (transfers now done as a feature)
- [ ] Tier-3 STILL BLOCKED ON DATA: median_grad_debt (LST blocked, not in ABA) + placement_by_state (per-school PDFs).
      Real debt $ remains the #1 judge ask. Bar passage + conditional-retention DONE.
- [ ] Open PR for algo-optimization (pushed to origin; URL: github.com/lkchss/Opportunity/pull/new/algo-optimization)
- [ ] Render transfer-up plan styling in the final UI pass (TransferPanel is placeholder-styled)
- [ ] Add lower-ranked schools (ranks 83+) so the transfer-up launchpad list works for genuinely-not-T14 profiles (157/3.4 currently has 0 safety/target)
- [ ] Data enrichment HARD/predicted (later): selectivity trend (multi-year), NLJ250-by-market, part-time/transfer

## In progress

## Done
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
