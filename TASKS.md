## Backlog
- [ ] Refine plain web styling into final visual design (placeholder style in law/web/)
- [ ] UI/UX streamlining pass (informed by stress test findings)
- [ ] Enable LLM narratives (law/llm_client.py is built, currently unused)
- [ ] Data enrichment EASY tier: collect ABA 509 + Employment Summary fields for all 75 schools —
      class_size_1l, scholarship grid (full/half-to-full/<half/none pct), conditional_scholarship,
      employed_10mo_pct, school_funded_pct
- [ ] Data enrichment MEDIUM tier (second pass): median_grad_debt, placement_by_state, bar_pass_ultimate + state avg
- [ ] Data enrichment HARD/predicted (later): selectivity trend (multi-year), NLJ250-by-market, part-time/transfer
- [ ] After enrichment: wire new fields into matcher (scholarship grid -> aid; class_size -> admit-prob; employment quality -> career), then resume LLM-judge loop
- [ ] Optimization loop: 3 iters run, all REVERT (weighting not the lever; ~40% judge-noise floor). Resume after data enrichment.

## In progress

## Done
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
