"""
Wikipedia enrichment: notable alumni + faculty per law school.

For each school in law_schools.json this resolves the school's Wikipedia article,
locates the "Notable alumni / people / faculty" sections, and extracts the linked
people. Results are cached to a sidecar (notable.json) so the network scrape runs
once; a separate --merge pass folds the cache into law_schools.json under the
``notable_alumni`` and ``notable_faculty`` keys.

Usage (from repo root):
  python -m law.data.build_notable --school boston-college-law   # test one school
  python -m law.data.build_notable --limit 10                    # scrape first 10
  python -m law.data.build_notable                               # scrape all
  python -m law.data.build_notable --merge                       # cache -> law_schools.json

Network: hits en.wikipedia.org once per school for resolution + one call per
relevant section. Be a good citizen — a short delay sits between schools.
"""

import argparse
import json
import re
import time
from html.parser import HTMLParser
from pathlib import Path
from typing import Optional
from urllib.parse import unquote

import requests

HERE = Path(__file__).parent
JSON_PATH = HERE / "law_schools.json"
CACHE_PATH = HERE / "notable.json"

API = "https://en.wikipedia.org/w/api.php"
HEADERS = {"User-Agent": "LawSchoolMatcher/1.0 (educational project; contact via repo)"}

# Section headings we treat as alumni vs faculty sources.
_ALUMNI_RE = re.compile(r"notable (alumni|people|graduates)|alumni", re.I)
_FACULTY_RE = re.compile(r"notable faculty|faculty|professors", re.I)

# Article titles that are pages, not individual people.
_SKIP_SUBSTR = ("List of", "Lists of", "law school", "University", "College")
# Exact titles that slip into list sections via citations/footers but aren't people.
_SKIP_EXACT = {
    "Wayback Machine", "Internet Archive", "Doi (identifier)", "ISBN (identifier)",
    "ISSN (identifier)", "PMID (identifier)", "JSTOR", "Google Books",
    "The New York Times", "Associated Press",
}
_MAX_PER_LIST = 10


def _display_name(title: str) -> str:
    """Strip a disambiguation parenthetical: 'Kent Greenfield (law professor)'."""
    return re.sub(r"\s*\([^)]*\)\s*$", "", title).strip()


def _get(params: dict, retries: int = 4) -> dict:
    params = {"format": "json", "formatversion": "2", **params}
    backoff = 2.0
    for attempt in range(retries):
        resp = requests.get(API, params=params, headers=HEADERS, timeout=20)
        if resp.status_code == 429 and attempt < retries - 1:
            wait = float(resp.headers.get("Retry-After", backoff))
            time.sleep(wait)
            backoff *= 2
            continue
        resp.raise_for_status()
        return resp.json()
    resp.raise_for_status()
    return resp.json()


def resolve_title(school_name: str) -> Optional[str]:
    """Best-effort Wikipedia article title for a school name."""
    data = _get({
        "action": "query", "list": "search",
        "srsearch": school_name, "srlimit": 1, "srnamespace": 0,
    })
    hits = data.get("query", {}).get("search", [])
    return hits[0]["title"] if hits else None


def _section_indices(title: str) -> list[tuple[str, str]]:
    """Return (index, heading) for LEAF sections matching alumni/faculty.

    A parent section (e.g. "Notable people" with "Alumni"/"Faculty" subsections)
    fetched by index includes all its subsections' content — which double-counts
    faculty into alumni. Detect containers (the next section sits at a deeper
    toclevel) and skip them, keeping only the specific leaf sections.
    """
    sections = _get({"action": "parse", "page": title, "prop": "sections"}) \
        .get("parse", {}).get("sections", [])
    out = []
    for i, sec in enumerate(sections):
        line = sec.get("line", "")
        if not (_ALUMNI_RE.search(line) or _FACULTY_RE.search(line)):
            continue
        level = sec.get("toclevel", 1)
        nxt = sections[i + 1] if i + 1 < len(sections) else None
        is_container = bool(nxt and nxt.get("toclevel", 1) > level)
        if is_container:
            continue  # its leaf subsections carry the real lists
        out.append((sec["index"], line))
    return out


class _ListLinkParser(HTMLParser):
    """Capture the FIRST /wiki/ article link inside each <li> of a section.

    People in Wikipedia "Notable alumni/faculty" sections live in bulleted lists,
    one person per <li>, the person as the lead link. Taking only the first link
    per list item drops inline prose links, citations, and the description links
    that follow the name — far cleaner than grabbing every link in the section.
    """

    def __init__(self):
        super().__init__()
        self.li_depth = 0
        self.need_link = False
        self.slugs: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag == "li":
            self.li_depth += 1
            self.need_link = True
        elif tag == "a" and self.li_depth and self.need_link:
            href = dict(attrs).get("href", "")
            if href.startswith("/wiki/"):
                slug = href[len("/wiki/"):].split("#")[0]
                self.need_link = False
                self.slugs.append(slug)

    def handle_endtag(self, tag):
        if tag == "li" and self.li_depth:
            self.li_depth -= 1


def _extract_people(title: str, index: str) -> list[dict]:
    """Pull people from a section's <li> list items (first link each)."""
    data = _get({
        "action": "parse", "page": title, "section": index, "prop": "text",
    })
    html = data.get("parse", {}).get("text", "")
    if not html:
        return []
    parser = _ListLinkParser()
    parser.feed(html)

    people, seen = [], set()
    for slug in parser.slugs:
        if ":" in slug:                       # File:, Help:, Category:, etc.
            continue
        name = unquote(slug).replace("_", " ")
        if name in _SKIP_EXACT or any(sub in name for sub in _SKIP_SUBSTR):
            continue
        if name in seen:
            continue
        seen.add(name)
        people.append({
            "name": _display_name(name),
            "url": "https://en.wikipedia.org/wiki/" + slug,
        })
    return people


def scrape_school(school: dict) -> dict:
    """Return {alumni: [...], faculty: [...], wiki_title: str}."""
    title = resolve_title(school["name"])
    result = {"wiki_title": title, "notable_alumni": [], "notable_faculty": []}
    if not title:
        return result
    alumni, faculty = [], []
    for index, heading in _section_indices(title):
        people = _extract_people(title, index)
        if _FACULTY_RE.search(heading) and not _ALUMNI_RE.search(heading):
            faculty.extend(people)
        else:
            alumni.extend(people)
    # De-dup across sections, cap length.
    result["notable_alumni"] = _dedup(alumni)[:_MAX_PER_LIST]
    result["notable_faculty"] = _dedup(faculty)[:_MAX_PER_LIST]
    return result


def _dedup(people: list[dict]) -> list[dict]:
    seen, out = set(), []
    for p in people:
        if p["name"] not in seen:
            seen.add(p["name"])
            out.append(p)
    return out


def load_schools() -> list[dict]:
    with open(JSON_PATH, encoding="utf-8") as fh:
        return json.load(fh)["schools"]


def load_cache() -> dict:
    if CACHE_PATH.exists():
        with open(CACHE_PATH, encoding="utf-8") as fh:
            return json.load(fh)
    return {}


def save_cache(cache: dict) -> None:
    with open(CACHE_PATH, "w", encoding="utf-8") as fh:
        json.dump(cache, fh, indent=2, ensure_ascii=False)


def cmd_scrape(args) -> None:
    schools = load_schools()
    if args.school:
        schools = [s for s in schools if s["id"] == args.school]
        if not schools:
            raise SystemExit(f"no school with id {args.school!r}")
    if args.limit:
        schools = schools[: args.limit]

    cache = load_cache()
    for i, school in enumerate(schools, 1):
        if school["id"] in cache and not args.force:
            print(f"[{i}/{len(schools)}] skip {school['id']} (cached)")
            continue
        try:
            res = scrape_school(school)
            cache[school["id"]] = res
            print(f"[{i}/{len(schools)}] {school['id']}: "
                  f"{len(res['notable_alumni'])} alumni, "
                  f"{len(res['notable_faculty'])} faculty "
                  f"(via {res['wiki_title']!r})")
        except requests.RequestException as exc:
            print(f"[{i}/{len(schools)}] {school['id']}: ERROR {exc}")
        save_cache(cache)
        time.sleep(args.delay)
    print(f"cache -> {CACHE_PATH} ({len(cache)} schools)")


def cmd_merge(_args) -> None:
    with open(JSON_PATH, encoding="utf-8") as fh:
        doc = json.load(fh)
    cache = load_cache()
    merged = 0
    for school in doc["schools"]:
        entry = cache.get(school["id"])
        if not entry:
            continue
        school["notable_alumni"] = entry["notable_alumni"]
        school["notable_faculty"] = entry["notable_faculty"]
        merged += 1
    with open(JSON_PATH, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=2, ensure_ascii=False)
    print(f"merged notable people into {merged} schools -> {JSON_PATH}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--school", help="scrape a single school id (test)")
    ap.add_argument("--limit", type=int, help="scrape only the first N schools")
    ap.add_argument("--delay", type=float, default=1.0, help="seconds between schools")
    ap.add_argument("--force", action="store_true", help="re-scrape cached schools")
    ap.add_argument("--merge", action="store_true",
                    help="fold notable.json cache into law_schools.json")
    args = ap.parse_args()
    if args.merge:
        cmd_merge(args)
    else:
        cmd_scrape(args)


if __name__ == "__main__":
    main()
