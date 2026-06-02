## Backlog
- [ ] Refine plain web styling into final visual design (placeholder style in law/web/)
- [ ] UI/UX streamlining pass (informed by stress test findings)
- [ ] Enable LLM narratives (law/llm_client.py is built, currently unused)

## In progress
- [~] Commit current working tree (all law/ changes since session start)

## Done
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
