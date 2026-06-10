"""DuckDuckGo-based opportunity scraper."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from duckduckgo_search import DDGS

# page-1-only (5) missed everything below the fold; 25 reaches lower-SEO hits
MAX_RESULTS_PER_QUERY = 25


@dataclass
class Result:
    title: str
    url: str
    snippet: str
    query: str


def search(queries: list[str]) -> list[Result]:
    results: list[Result] = []
    seen: set[str] = set()
    with DDGS() as ddgs:
        for query in queries:
            hits: list[dict[str, Any]] = list(
                ddgs.text(query, max_results=MAX_RESULTS_PER_QUERY)
            )
            for h in hits:
                url = h.get("href", "")
                if url and url not in seen:
                    seen.add(url)
                    results.append(
                        Result(
                            title=h.get("title", ""),
                            url=url,
                            snippet=h.get("body", ""),
                            query=query,
                        )
                    )
    return results
