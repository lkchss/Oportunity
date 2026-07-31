# Opportunity: Law

Deterministic law-school matcher: profile in (LSAT/GPA/goals/finances), ranked
ABA-data-backed school list out — admissibility tiers, six-factor fit scoring,
financial model, apply-plan portfolio builder, scholarship-leverage and
what-if tools, plus server-rendered SEO pages for every school and state.

No LLM anywhere in the product: all 196 schools are scored from public ABA
509/employment/bar data (plus College Scorecard debt/earnings), merged by the
build scripts in `law/data/`. The LLM-judge lives only in `eval/`, as the
offline keep/revert gate for ranking changes.

## Run

```bash
pip install -r requirements-law.txt
python -m law.server
```

## Test

```bash
pip install pytest flask
python -m pytest tests/ -q
```

Playwright suites (`test_*_playwright.py`) skip themselves unless a local
server is reachable.

## Deploy

- **Vercel**: `vercel.json` + `api/index.py` (WSGI shim). Set `SITE_BASE_URL`
  and `APP_PASSWORD` env vars in the dashboard.
- **Render** (fallback): `render.yaml`, pinned to `--workers 1` so the /stats
  counters stay authoritative.

## Layout

- `law/` — matcher, Flask server, SEO pages, web UI (in-browser Babel JSX),
  `data/` build+refresh pipeline (`refresh.py` dry-runs the annual data drop)
- `eval/` — LLM-judge harness (profiles, judge prompt, snapshot, diff/tally)
- `tests/` — unit + Playwright suites
- `archive/` — April-2026 prototype docs, kept for provenance only

## Provenance

Extracted 2026-07-31 from the `Opportunity` monorepo (`Apps/Opportunity`)
with full history via `git filter-repo` — 57 commits of law-line history
carried over. The opportunity-finder product line continues in that repo;
this one is standalone.
