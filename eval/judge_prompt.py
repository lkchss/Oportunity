"""
Renders the blind A/B prompt handed to each zero-context judge agent.

One agent judges one profile with no knowledge of the optimization, which ranking
is the incumbent, or what changed — it only sees the applicant and two rankings.
That isolation is the point: the verdict reflects ranking quality, not loop state.
"""

import json

# What "a good ranking" means for THIS product. The judge optimizes the applicant's
# real interest, not raw prestige. Deliberately multi-criteria so the loop can't win
# by collapsing to a single axis (e.g. "always rank by USNWR").
RUBRIC = """\
You are a seasoned pre-law admissions advisor. A real applicant will act on this
list. Judge which ranking better serves THIS specific applicant, weighing:

1. Admissibility realism — A useful list is mostly schools the applicant can
   actually get into (a healthy mix of target/safety with a few reaches). A list
   dominated by "hard reach" schools the applicant will likely be rejected from is
   a BAD list, however prestigious.
2. Career fit — Schools should feed the applicant's stated goal (e.g. BigLaw % for
   BigLaw, public-interest placement + LRAP for PI/government).
3. Location — If the applicant named a target state, schools that place graduates
   there should be favored; ignoring a stated geographic preference is a defect.
4. Cost / debt reality — For cost-sensitive applicants (low income, high scholarship
   slider), lower net debt and in-state options matter; burying them under expensive
   schools is a defect.
5. Prestige — A reasonable tiebreaker, NOT the dominant factor. Higher rank is
   better all else equal, but should not override 1–4.
6. List usefulness — The top of the list should be schools worth applying to, not
   a single category repeated.

Pick the ranking that a thoughtful advisor would actually hand this applicant.
If they are genuinely equivalent, answer TIE — do not invent small preferences.
"""

_OUTPUT_SPEC = """\
Respond with EXACTLY two lines and nothing else:
VERDICT: A   (or: VERDICT: B   or: VERDICT: TIE)
REASON: <one sentence, <=25 words>
"""


def _fmt_ranking(rows: list[dict]) -> str:
    lines = []
    for i, s in enumerate(rows, 1):
        debt = s.get("net_debt")
        debt_str = f"${debt:,}" if isinstance(debt, (int, float)) else "n/a"
        rank = s.get("usnwr_rank")
        rank_str = "Unranked" if (rank is None or rank >= 999) else f"USNWR #{rank}"
        lines.append(
            f"{i:>2}. {s['name']} ({rank_str}) "
            f"[{s['admissibility_tier']}] "
            f"composite={s['composite_score']} "
            f"admiss={s['admissibility_score']} career={s['career_fit_score']} "
            f"loc={s['location_fit_score']} schol={s['scholarship_score']} "
            f"fin={s['financial_score']} debt={debt_str}"
        )
    return "\n".join(lines)


def render_judge_prompt(packet: dict) -> str:
    """Build the full prompt for one zero-context judge agent."""
    return (
        f"{RUBRIC}\n"
        f"APPLICANT:\n  {packet['summary']}\n\n"
        f"RANKING A:\n{_fmt_ranking(packet['ranking_A'])}\n\n"
        f"RANKING B:\n{_fmt_ranking(packet['ranking_B'])}\n\n"
        f"{_OUTPUT_SPEC}"
    )


def load_packets(path: str = "eval/runs/packets.json") -> dict:
    with open(path) as f:
        return json.load(f)
