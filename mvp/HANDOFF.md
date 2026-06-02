# MVP Handoff

Context for the next coding agent (Sonnet) picking up this MVP.

## Project pivot

Repo started as a law school matcher (`lawschool_v1/`). User pivoted to a **general opportunity finder MVP**. The law school version is preserved untouched in `lawschool_v1/` — do not modify it. Build the new app in `mvp/`.

## MVP scope (agreed with user)

A Streamlit app where:

1. User selects a **category** of opportunity from a fixed list (dropdown).
2. User provides **freeform text**: background + goals (two textareas).
3. App calls Claude with the **web search tool** to find concrete, currently-open opportunities matching the user.
4. Results render as cards: title (link), summary, why-it-matches.

### Decisions already made
- **Input shape**: freeform text (background + goals). No resume upload, no questionnaire for MVP.
- **Category selection**: user picks one category per query (not "all in one pipeline").
- **Scraper**: use Claude's built-in `web_search_20250305` tool. No custom scrapers, no Google API, no site-specific crawlers. Reason: zero infra, no ToS risk, LLM filters inline. Revisit only if result quality is poor.
- **Stash strategy**: lawschool code moved into `lawschool_v1/` folder on `main` (not a separate branch). New code lives in `mvp/`.

### Categories (in `mvp/main.py`)
Jobs, Internships, Graduate school, Fellowships / Scholarships, Gap year programs, Travel / Volunteer.

## Current state

Committed: nothing new yet. Working tree has the reorg + partial MVP scaffold.

Files created so far in `mvp/`:
- `__init__.py` — empty, written.
- `main.py` — **NOT written** (user rejected the write before handoff). See "Resume here" below for the intended contents.
- `search.py` — **NOT written** (user rejected). See below.

Files moved:
- All previous `app/*.py` + `app/data/` → `lawschool_v1/`.
- Old `app/` directory removed.

`requirements.txt`, `.env.example`, `CLAUDE.md`, `README.md` untouched. Tests under `tests/` still reference the old `app.*` import paths and **will break** — fix or skip when convenient.

## Resume here

### 1. Confirm with user before writing the two rejected files
The previous agent (Opus) had drafted `mvp/main.py` and `mvp/search.py` and the user rejected the writes without saying why. Ask the user whether to:
- proceed with the drafts as-described below,
- change the approach (different model, different tool, different UI layout),
- or start the MVP differently entirely.

### 2. Intended `mvp/main.py` (draft to confirm)
Streamlit app:
- Page config + title.
- `st.selectbox` for category (list above).
- Two `st.text_area`s: background, goals.
- Button disabled until both textareas non-empty.
- On click → spinner → call `mvp.search.find_opportunities(category, background, goals)` → cache in `st.session_state["results"]`.
- Render each result inside `st.container(border=True)` with markdown title link, summary, why_match.

### 3. Intended `mvp/search.py` (draft to confirm)
- Single function: `find_opportunities(category, background, goals) -> list[dict]`.
- Lazy `Anthropic()` client init, reads `ANTHROPIC_API_KEY` from env (already loaded via `dotenv` in `main.py`).
- Model: `claude-opus-4-7` (switch to `claude-sonnet-4-6` if user wants cheaper).
- System prompt instructs: prefer official sources, return JSON array only, fields `{title, url, summary, why_match}`.
- Tools: `[{"type": "web_search_20250305", "name": "web_search", "max_uses": 5}]`.
- `max_tokens=4096`.
- Parse: concat text blocks from `response.content`, slice from first `[` to last `]`, `json.loads`. Return `[]` on parse failure (no exceptions to the UI for MVP).

### 4. Dependencies to verify in `requirements.txt`
Need at minimum: `streamlit`, `anthropic`, `python-dotenv`. `requirements.txt` was not read in this session — check it and add any missing.

### 5. Smoke test
After files exist:
```bash
pip install -r requirements.txt
streamlit run mvp/main.py
```
User runs locally; you cannot. Ask them to paste any errors.

## Open questions / known gaps

- **No tests yet** for `mvp/`. The `tests/` folder still targets `app.*` (now `lawschool_v1.*`) — those imports are broken. Either rewrite imports or leave alone until user asks.
- **No result ranking / dedup** — web_search may return duplicates or irrelevant items. MVP just trusts the model. Add a ranking pass only if quality is bad.
- **No caching** of search results. Each click hits the API. Consider `@st.cache_data` keyed on (category, background, goals) hash later.
- **No eval harness**. README explicitly flags this as an unsolved problem ("how do we even begin to measure what the 'best' results are?"). Out of MVP scope.
- **Cost**: web_search tool calls add real cost per query. User has not set a budget cap. Flag if they want token/spend limits.

## Conventions to follow

From `CLAUDE.md`:
- Python 3.11+, type hints on function signatures, small single-purpose functions.
- All Claude API calls in one client module (here: `mvp/search.py`).
- Streamlit UI in `mvp/main.py`.
- **Do not create additional `.md` files unless asked.** (This handoff was explicitly requested.)
- Never commit `.env`.

## User preferences observed this session

- Ultra-terse "caveman" response mode currently active. Sonnet should keep responses short while in this mode unless user toggles off.
- User pivoted scope mid-session and prefers tight MVP scope over breadth.
- User did not want a branch — wanted both versions side-by-side in folders on `main`.
