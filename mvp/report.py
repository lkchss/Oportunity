"""Generate HTML report from search results."""
from __future__ import annotations

import datetime
from pathlib import Path

from mvp.scraper import Result

STYLE = """
  body { font-family: system-ui, sans-serif; max-width: 900px; margin: 40px auto; padding: 0 20px; color: #1a1a1a; }
  h1 { font-size: 1.8rem; margin-bottom: 4px; }
  .meta { color: #666; font-size: 0.9rem; margin-bottom: 32px; }
  .card { border: 1px solid #e0e0e0; border-radius: 8px; padding: 18px 22px; margin-bottom: 16px; }
  .card:hover { border-color: #999; }
  .card h2 { margin: 0 0 6px; font-size: 1.1rem; }
  .card h2 a { color: #1a56db; text-decoration: none; }
  .card h2 a:hover { text-decoration: underline; }
  .url { font-size: 0.8rem; color: #666; margin-bottom: 8px; word-break: break-all; }
  .snippet { font-size: 0.95rem; line-height: 1.5; margin: 0; }
  .query-tag { display: inline-block; font-size: 0.75rem; background: #f0f4ff; color: #3451b2; border-radius: 4px; padding: 2px 8px; margin-top: 10px; }
  .section { font-size: 0.8rem; color: #888; margin: 28px 0 8px; text-transform: uppercase; letter-spacing: 0.05em; border-bottom: 1px solid #eee; padding-bottom: 4px; }
"""


def _card(r: Result) -> str:
    return f"""
    <div class="card">
      <h2><a href="{r.url}" target="_blank">{r.title}</a></h2>
      <div class="url">{r.url}</div>
      <p class="snippet">{r.snippet}</p>
      <span class="query-tag">via: {r.query}</span>
    </div>"""


def render(
    results: list[Result],
    category: str,
    context_summary: str,
    output_path: Path,
) -> Path:
    now = datetime.datetime.now().strftime("%B %d, %Y %H:%M")
    cards = "\n".join(_card(r) for r in results)
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Opportunity Results — {category}</title>
  <style>{STYLE}</style>
</head>
<body>
  <h1>Opportunity Results</h1>
  <div class="meta">
    <strong>Category:</strong> {category} &nbsp;·&nbsp;
    <strong>Generated:</strong> {now} &nbsp;·&nbsp;
    <strong>{len(results)} results</strong>
  </div>
  <div class="section">Context</div>
  <p style="font-size:0.95rem; color:#444; margin-bottom:24px;">{context_summary}</p>
  <div class="section">Results</div>
  {cards}
</body>
</html>"""
    output_path.write_text(html, encoding="utf-8")
    return output_path
