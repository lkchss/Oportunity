# Handoff: Opportunity: Law — Full UI/UX Redesign

## Overview

A ground-up redesign of the Opportunity: Law web app — a tool that ranks every
ABA-accredited law school against an applicant's profile (LSAT/GPA, career goal, target
markets, budget). The redesign covers all five screens: intake, results (three views),
school detail, compare, and the raw rankings browser.

The target codebase is the existing app at `web/` (React via Babel-standalone:
`index.html`, `styles.css`, `app.jsx`, `components.jsx`, with a Python backend serving
`/api/match`). This package's prototype mirrors that structure closely, so most files
map 1:1.

## About the Design Files

The files in `prototype/` are **design references created in HTML** — a fully working
prototype showing intended look and behavior, not production code to copy verbatim.
The task is to **recreate this design in the target codebase's existing environment**,
keeping its `/api/match` data flow. The prototype substitutes a client-side matcher over
24 sample schools (`data.jsx`) purely so the design is interactive; production scoring
stays on the backend. The Tweaks panel (`tweaks-panel.jsx`, the `<TweaksPanel>` block at
the bottom of `main.jsx`, and the `useTweaks` wiring) is a design-review tool — **do not
ship it**; bake the defaults below instead.

## Fidelity

**High-fidelity.** Colors, type, spacing, copy, and interactions are final and
user-approved through many review rounds. Recreate pixel-perfectly. Where the prototype
and this README disagree, the prototype wins.

## Design Tokens (final)

```css
/* surfaces & ink */
--paper: #fbf9f4;        /* page background (cream) */
--surface: #fffdf8;      /* cards, panels, inputs */
--ink: #1c1917;          /* primary text */
--soft: #7d7567;         /* secondary text */
--faint: #a39a89;        /* tertiary/captions */
--line: #e8e2d5;         /* hairline borders */
--line2: #d3cab7;        /* stronger borders */

/* THE brand color — one token, used for accent AND highlight */
--accent: #a3791a;       /* marigold */
--accent-deep: #7d5c12;  /* hover, link text, "you" markers */
--accent-soft: #f3ead0;  /* tints, selected rows */
--accent-contrast: #f5f1e6; /* text on accent buttons */
--amber: var(--accent);  /* legacy alias — same value, always */

/* tier vocabulary — FIXED, never restyled by brand color */
--safety: #3d6b50;  --safety-dot: #4e8a66;  --safety-bg: #e6efe7;
--target: #14532d;  --target-dot: #1f6b3d;  --target-bg: #dbe9dc;
--reach:  #92400e;  --reach-dot:  #b45309;  --reach-bg:  #f6e8d4;
--hard:   #8c3120;  --hard-dot:   #9a3324;  --hard-bg:   #f5e2dc;
```

- **Type**: Source Serif 4 (display/titles, 700), IBM Plex Sans (UI, 400–700),
  IBM Plex Mono (numerals, captions, table cells). Google Fonts.
- **Density**: compact is the production default (prototype: `body.compact`,
  row padding 9px, card padding 14px).
- **Radii**: buttons/inputs 7–8px, cards 12px, panels 10px, pills 999px.
- **Score grading** (`gradeColor()` in `ui.jsx`): ≥85 `#1f6b3d`, ≥70 `#4e8a66`,
  ≥55 `#b45309`, else `#9a3324`. Driven by score value, never by tier.

## Brand rules (user cares about these)

1. **One brand color.** Marigold drives buttons, links, rings/bars fill, selected
   states, the title colon, sort arrows, the "you" dot. There is no separate
   highlight color.
2. **The colon is the brand.** Every page title ends in a colon colored marigold
   (`<span class="colon">:</span>`): "Where should you go to law school:",
   "Your matches, ranked:", "Side by side:", "All schools:", and on detail pages
   the school name itself ("Fordham University:").
3. **Lowercase chrome**: nav is "your matches · all schools · methodology";
   buttons "save / share ▾", "ignore admissibility", "retake what-if".
4. **No em-dashes in UI copy or tooltips.** Use colons/semicolons. Keep tooltips
   to 1–2 short sentences; explanatory copy lives behind `?` info tips
   (`InfoTip`), never as on-screen paragraphs.
5. **Tier colors are a separate vocabulary** (admissibility only). Score rings/chips
   use `gradeColor`. Don't mix the two systems.

## Screens

### 1. Intake (`screen-profile.jsx`)
- Serif H1 + one-line intro ("…what it would really cost *you*.").
- Two-panel card grid (1.15fr / 0.85fr): **Who you are** (LSAT + "haven't taken it"
  checkbox, GPA, career-goal select, weighted practice states, collapsible
  **Financials**) and **What matters to you** (three weight sliders + transfer
  checkbox + full-width marigold CTA "Find my schools →"; no caption).
- **Financials** toggle: "▸ Financials" + small uppercase `OPTIONAL` pill badge —
  no explanatory sentence. Inside (in order): Household income ($, typable number),
  Savings / Existing debt (no helper captions), then In-state tuition eligibility.
- **Sliders**: custom-styled range inputs — marigold fill left of thumb, gray right,
  16px marigold thumb with surface ring; color must NOT change while dragging;
  step 0.1 for smooth motion but display rounded "7/10".

### 2. Results (`screen-results.jsx`)
- Header: "Your matches, ranked:" + subtitle "Every school scored for *your* numbers,
  goal, and budget" + **profile card** (LSAT · GPA · Goal · Practice cells + Edit).
- **Toolbar**: segmented control (Shortlist / Full table / Transfer path*) · spacer ·
  **retake what-if** (solid marigold sm button) · "ignore admissibility" checkbox + `?`
  (tight 5px gaps) · "save / share ▾" ghost menu (copy link / export CSV / print).
  *Transfer path only when the user checked the transfer intent.
- **Retake what-if**: button swaps into a compact spinner `[170 | +/− stacked | ×]`
  (~30px tall): mono value (soft gray at delta 0, marigold-deep when raised), vertical
  + over −, separate × tab that closes AND resets. Raising LSAT re-runs the match and
  re-tiers schools live. No other what-if UI (no strip, no payoff text).
- **ignore admissibility** ("pure fit"): re-ranks by fit alone, no admit-tier scaling;
  no banner/popup when toggled. Tooltip: "Re-ranks by fit alone, ignoring your odds of
  admission. Tiers still show."
- **Shortlist view** (default): tier-grouped sections — "Targets", "Safeties",
  "Reaches" — each: dot + H2 + count, one-line sub, school cards (4 shown,
  "Show all N ▾"). Hard reaches collapsed into a dashed box ("68 hard reaches hidden —
  long odds for your numbers." / "Show anyway ▾").
- **School card**: score ring (grade-colored) · serif name + "loc · USNWR #n" meta ·
  why-line ("Target. Strong BigLaw pipeline (38%) · likely merit aid") · three stats
  (goal placement % — see goal rule below — / bar pass / est. cost) all in ink ·
  "+ Compare" pill → "✓ Added" (marigold fill).
- **Full table view**: tier filter chips (All · Safety · Target · Reach · Hard reach,
  with counts) above a dense table: ☐ compare checkbox, School, Tier pill, USNWR,
  goal % , Bar, LSAT Δ (green +/amber −), Cost/aid, Score chip (top scores get solid
  fill). Sortable headers with marigold arrows; mono numerals; zebra rows; hover/
  selected tint `--accent-soft`; mono footer (row count, sort, hints).
- **Compare tray** (fixed bottom center, ink background): "N selected: names…" +
  marigold "Compare →" + clear.
- **Transfer path view**: two card sections in the standard school-card idiom —
  "Launchpads:" (realistic admits ranked by transfer-out rate; stats: move up /yr,
  est. cost, bar pass) and "Transfer-friendly targets:" (reaches ranked by transfer
  seats; stats: seats /yr, goal %, USNWR). No explainer paragraphs, no footer line.

### 3. School detail (`screen-detail.jsx`)
- Crumb "← Back to results". Header: serif school name + colon; sub
  "New York, NY · USNWR #35 · class of 380" (no acceptance here).
- **Match score, top right (treatment "C")**: tier pill + big serif number with
  faint "/100", a 6px scale bar filled to the score in `gradeColor`, mono labels
  "0 · match score · 100" (210px block). "More about the school ↗" link below.
- **Hero**: radar (6 axes: Admiss./Prestige/Career/Location/Schol./Financial) +
  stat row **LSAT 50 · GPA 50 · Acceptance · [goal placement] · Bar pass** + six
  labeled bars.
- **Three story columns** (cards, `?` tip on each heading):
  - *Will you get in?* — two **number lines** (LSAT, GPA): 2px track, ticks+mono
    labels at 25th/median/75th, marigold "you" dot with value above; tier pill
    verdict (no sentence); kv rows: 1L attrition, transfer out/in, conditional-
    scholarship flag (only when applicable, with `?`).
  - *Will you get the job?* — kv rows BigLaw/Fed. clerkship/Government/Public
    interest with the **goal row highlighted** marigold-deep; divider; bar pass
    (first · ultimate), employed @10 mo, feeder markets.
  - *Can you afford it?* — two big numbers (est. cost after aid / starting salary);
    kv rows: monthly payment, debt-to-income, tuition basis, real-grad debt ·
    earnings (`?` cites College Scorecard).
- **Notable alumni**: pill links (Wikipedia), "Source: Wikipedia" caption.
- **Financial detail**: no tabs — panels side by side (flex-wrap):
  1. *Standard repayment — 10-yr @ 7%* as a **balance sheet**: Tuition × 3 yrs,
     Living × 3 yrs, rule, **Gross cost**, −Est. aid, (−Savings applied if any),
     heavy rule, **Borrowed**; second block: starting salary, monthly payment,
     debt-to-income. Max width 480px.
  2. *Year-by-year — standard plan*: compact ledger table (years 1/3/5/8/10:
     balance start, paid, balance end), max width 420px.
  3. *PSLF / IDR path* panel (+ IDR year-by-year) only when goal is Government or
     Public Interest.

### 4. Compare (`screen-compare.jsx`)
- "Side by side:" + "Green cells mark the best value in each row."
- Overlay radar with per-school series colors `#1e4d35 #b45309 #1e3a5f #8c3120` +
  legend rows (swatch, serif name, meta, remove).
- Two tabs: **With your numbers** (tier, match score, career/location/scholarship,
  cost after aid, monthly payment, DTI, tuition basis) and **Raw school stats**
  (rank, acceptance, LSAT/GPA percentiles, outcomes, bar, tuition, Scorecard).
  Best-in-row cells tinted `--safety-bg`/green. Empty state if <2 selected.

### 5. All schools / rankings (`screen-rankings.jsx`)
- "All schools:" + mono prototype note; search box + state filter (right).
- Dense table, columns in order: **School, Rank**, LSAT 25/50/75, GPA 50, Accept,
  BigLaw (plain %, no bar), Employed, Bar, Tuition. Sortable.
- Clicking a row expands a **data sheet** (two kv columns): outcomes each annotated
  with percentile standing as faint "· 88%" (percent of schools below); costs/aid/
  transfers/Scorecard. Footer: just "About the school ↗". No prose.

## Critical implementation rules

1. **Featured job placement is goal-driven.** Anywhere a single placement stat is
   featured (detail hero stat row, detail "get the job" highlight, school-card hero
   stat, table goal column), it must be the outcome the applicant flagged as their
   career goal (BigLaw %, clerkship %, government %, public interest %) — never
   hardcoded BigLaw. See `goalKey`/`goalStat` (`screen-detail.jsx`) and `goalLabel`
   (`screen-results.jsx`).
2. **View state survives navigation**: results view (shortlist/table/transfers) is
   owned by the app shell, so opening a school and going back restores the view.
3. **Profile persists** to localStorage; results are recomputed from the submitted
   profile snapshot. What-if delta and compare selections reset on re-submit.
4. **Nothing saved server-side** message in the footer + feedback mailto.
5. Direct-edit/`data-comment-anchor` attributes in the prototype are review-tool
   artifacts; omit them.

## Interactions & states

- Buttons: hover darkens (`--accent-deep` on primary; `#f6f2e9` on default);
  1px translate on press. Links underline on hover.
- Cards: hover raises shadow + underlines name; whole card clickable; compare
  button stops propagation.
- Info tips: 16px circled `?`, open on hover AND click/focus (aria-expanded),
  ink-colored popover 250px, 12px text.
- Dense table rows: pointer cursor, hover/selected tint, click → detail; rankings
  rows toggle expansion (Enter/Space too).
- Save/share: dropdown with copy-link (clipboard), CSV export (BOM, quoted), print.
- Compare tray appears only with ≥1 selection; "Compare →" disabled until 2.
- Responsive: grids collapse to single column under 900px (desktop-first is fine).

## Files in this package

- `README.md` — this document
- `prototype/Opportunity Law.html` — entry point (open in a browser)
- `prototype/app/styles.css` — complete stylesheet (tokens + all components)
- `prototype/app/ui.jsx` — shared components: TierTag/TierPill, ScoreRing, Bar,
  CellBar, Radar, RadarOverlay, InfoTip, Stat, Seg, Modal, Methodology, Masthead,
  `gradeColor`
- `prototype/app/screen-profile.jsx` — intake
- `prototype/app/screen-results.jsx` — results (shortlist/table/transfers), what-if
  spinner, compare tray, save menu, CSV export
- `prototype/app/screen-detail.jsx` — school page incl. RangeLine + balance-sheet
  ledgers
- `prototype/app/screen-compare.jsx` — compare
- `prototype/app/screen-rankings.jsx` — raw browser incl. percentile annotations
- `prototype/app/main.jsx` — shell/routing/state (strip the TweaksPanel block)
- `prototype/app/data.jsx` — sample data + illustrative client-side matcher (replace
  with `/api/match`; keep the result-object shape: tier, composite, radar[6], why,
  netDebt, monthly, dti, salary, goalPct, …)
- `prototype/app/tweaks-panel.jsx` — review tool only; do not ship

## Assets

No image assets. Fonts from Google Fonts (Source Serif 4, IBM Plex Sans, IBM Plex
Mono). External links: Wikipedia (school/alumni), mailto for feedback.
