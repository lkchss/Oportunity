# Opportunity v2 - Planned Issues

## V2 Issue #1: Integrate Background/Soft Factors into Matching

**What do you want?**
Factor work experience, achievements, and personal statement themes into the matching algorithm, not just collect them.

**Why is it needed?**
Currently these are collected but ignored. For competitive applicants, softs matter (work experience, publications, leadership, underrep status, etc.).

**Acceptance Criteria**
- [ ] Parse work_experience field for keywords (law firm, finance, nonprofit, etc.)
- [ ] Parse achievements field for signals (law review, moot court, leadership, etc.)
- [ ] Add "soft factors score" (0-100) to matcher output
- [ ] Integrate into composite score (suggest: 10-15% weight)
- [ ] Display in school cards
- [ ] Unit tests for soft factor parsing

---

## V2 Issue #2: Redesign Scholarship Scoring Logic

**What do you want?**
Fix the confusing/contradictory "likely merit aid" + "reach school" combination. Clarify what drives merit aid likelihood.

**Why is it needed?**
Current logic is hard to understand and potentially misleading. Splitters can be reaches, but this creates confusion.

**Acceptance Criteria**
- [ ] Separate "admissibility" (am I competitive?) from "scholarship likelihood" (will I get merit aid?)
- [ ] Document the exact criteria for merit aid scoring
- [ ] Update school cards to show both clearly (not confusingly)
- [ ] Test with real splitter scenarios
- [ ] Consider: should merit aid impact ranking, or just inform the user?

---

## V2 Issue #3: Data Quality - Audit and Fix School Statistics

**What do you want?**
Audit all 52 schools' stats against official ABA 509 reports and NALP data. Fix inaccuracies.

**Why is it needed?**
Data quality corrupts all downstream scores. Example: Columbia's 25th percentile LSAT is higher than currently listed.

**Acceptance Criteria**
- [ ] Cross-check each school against latest ABA 509 report
- [ ] Verify LSAT/GPA medians and percentiles
- [ ] Verify employment percentages against NALP
- [ ] Verify bar pass rates against official ABA data
- [ ] Update law_schools.json with corrected data
- [ ] Document sources for each school
- [ ] Add data freshness date to file

---

## V2 Issue #4: Improve Error Handling & Edge Cases

**What do you want?**
Handle edge cases better: no LSAT, unusual geographic preferences, extreme outliers, etc.

**Acceptance Criteria**
- [ ] Test splitter with 180 LSAT / 2.5 GPA scenario
- [ ] Test reverse splitter with 150 LSAT / 4.0 GPA
- [ ] Test with no LSAT yet (currently uses conservative estimate)
- [ ] Test with no practice area interests
- [ ] Test with "Anywhere" geography preference
- [ ] Better fallback text when LLM unavailable
- [ ] Rate limit retry logic with backoff

---

## V2 Issue #5: Expand School Dataset & Add Custom Schools

**What do you want?**
Expand beyond 52 schools and allow users to add custom schools.

**Acceptance Criteria**
- [ ] Add all ~200 ABA law schools to dataset
- [ ] Add "custom school" form fields (allow user to input stats)
- [ ] Rank custom schools against the algorithm
- [ ] Generate narratives for custom schools
- [ ] Validate custom school data

---

## V2 Issue #6: UI Polish & Additional Features

**What do you want?**
Polish the UI with favorites, comparison mode, export results, etc.

**Acceptance Criteria**
- [ ] "Save to favorites" button on school cards
- [ ] "Compare 2 schools" side-by-side view
- [ ] Export results as PDF or CSV
- [ ] Dark mode toggle
- [ ] Mobile-responsive layout
- [ ] Share results link (shareable recommendations)

---

## V2 Issue #7: Documentation & User Guide

**What do you want?**
Document how the algorithm works, data sources, and how to interpret results.

**Acceptance Criteria**
- [ ] Methodology doc: explain each scoring component
- [ ] Data sources doc: where stats come from
- [ ] FAQ: common questions about rankings
- [ ] In-app tooltips on scoring components
- [ ] README with setup instructions for v2

---

## V2 Issue #8: Performance & Caching Optimizations

**What do you want?**
Optimize for speed, especially LLM narrative generation.

**Acceptance Criteria**
- [ ] Cache LLM results (same profile = same narratives)
- [ ] Batch LLM calls instead of sequential
- [ ] Profile matching search (find similar profiles)
- [ ] Lazy load school data if dataset expands

---

## V1 Remaining Work

- [ ] Data audit/fix: Verify and correct school statistics (Columbia, etc.)
- [ ] Fix any critical bugs discovered during testing
