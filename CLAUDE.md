Do not generate additional .md files unless asked to.

## Product Lines

Two independent product lines live side-by-side in this repo.

### MVP — General Opportunity Finder
Streamlit app: user fills form → Claude web_search → ranked opportunity cards.

```
mvp/
  main.py      # Streamlit app — user fills form, Claude web_search returns results in UI
  portal.py    # Streamlit profile builder — saves profile.json for CLI pipeline
  run.py       # CLI pipeline entry point — reads profile.json, DuckDuckGo search, HTML report
  search.py    # All Claude API calls live here (web_search tool)
  scraper.py   # DuckDuckGo search used by run.py
  queries.py   # Builds search query strings from profile fields
  report.py    # Renders HTML report from DuckDuckGo results
```

```bash
streamlit run mvp/main.py
```

### Law — Law School Matcher
User inputs academic profile → matching algorithm → ranked law school results.
**No LLM / generative AI in this product line** — the matcher is fully deterministic
(real ABA data + transparent scoring). The LLM-judge under eval/ is offline dev
tooling only, never part of the app.

```
law/
  main.py        # Streamlit app entry point
  matcher.py     # Core matching algorithm
  data_loader.py # Loads law school data
  data/
    law_schools.json  # Law school database
```

```bash
streamlit run law/main.py
```

## Shared
```
tests/
requirements.txt
.env.example   # Copy to .env and add ANTHROPIC_API_KEY
```

## Tech Stack
- Python 3.11+
- Streamlit (UI — runs in the browser, all Python)
- Anthropic Python SDK (Claude integration)
- python-dotenv (environment variable management)

## Setup
```bash
pip install -r requirements.txt
cp .env.example .env   # add ANTHROPIC_API_KEY
```

## Code Conventions
- Type hints on all function signatures.
- Keep functions small and single-purpose.
- Never commit `.env` or API keys.
