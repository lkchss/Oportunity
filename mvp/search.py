"""Opportunity search via Claude web search tool."""
from __future__ import annotations

import json
import os
from typing import Any

from anthropic import Anthropic

MODEL = "claude-sonnet-4-6"
MAX_RESULTS = 8

_client: Anthropic | None = None


def _get_client() -> Anthropic:
    global _client
    if _client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY missing. Copy .env.example to .env.")
        _client = Anthropic(api_key=api_key)
    return _client


SYSTEM = (
    "You are an opportunity-matching assistant. Given a user's background, goals, and category, "
    "use web search to find concrete, currently-open opportunities that fit them. "
    "Prefer official sources (employer career pages, university admissions, program sites) over aggregators. "
    "Return ONLY a JSON array. Each item: {\"title\": str, \"url\": str, \"summary\": str, \"why_match\": str}. "
    "No prose outside JSON."
)


def _build_prompt(category: str, background: str, goals: str, resume_text: str) -> str:
    parts = [f"Category: {category}"]
    if resume_text:
        parts.append(f"Resume:\n{resume_text}")
    if background:
        parts.append(f"Additional background:\n{background}")
    parts.append(f"Goals:\n{goals}")
    parts.append(f"Find up to {MAX_RESULTS} opportunities. Return JSON array only.")
    return "\n\n".join(parts)


def _extract_json(text: str) -> list[dict[str, Any]]:
    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end == -1:
        return []
    try:
        data = json.loads(text[start : end + 1])
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        return []


def find_opportunities(
    category: str, background: str, goals: str, resume_text: str = ""
) -> list[dict[str, Any]]:
    client = _get_client()
    response = client.messages.create(
        model=MODEL,
        max_tokens=4096,
        system=SYSTEM,
        tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 5}],
        messages=[{"role": "user", "content": _build_prompt(category, background, goals, resume_text)}],
    )

    text_parts: list[str] = []
    for block in response.content:
        if getattr(block, "type", None) == "text":
            text_parts.append(block.text)
    return _extract_json("\n".join(text_parts))
