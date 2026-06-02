"""
Compare two snapshots (baseline vs candidate) and emit blind judge packets only
for profiles whose top-N ranking actually changed.

Most single-parameter tweaks move few rankings, so this keeps the number of
judge spawns small per iteration. For each changed profile we randomly assign
the two rankings to labels A and B (so the judge can't tell which is the
incumbent), and store the decode key separately.

Usage:
    python -m eval.diff                 # uses runs/baseline.json + runs/candidate.json
Outputs:
    runs/packets.json   # what the judge sees: profile + ranking A + ranking B
    runs/key.json       # decode: for each profile, which label is 'candidate'
Prints a one-line summary (how many changed, how many identical).
"""

import json
import random
from pathlib import Path

_RUNS_DIR = Path(__file__).parent / "runs"
_SEED = 1729  # fixed: A/B assignment stable across reruns of the same diff


def _ordered_ids(entry: dict) -> list[str]:
    return [s["id"] for s in entry["top"]]


def _render(entry: dict) -> list[dict]:
    """The ranking rows shown to the judge (drop ids->names handled in prompt)."""
    return entry["top"]


def build_packets() -> dict:
    baseline = json.loads((_RUNS_DIR / "baseline.json").read_text())
    candidate = json.loads((_RUNS_DIR / "candidate.json").read_text())
    rng = random.Random(_SEED)

    packets = {}
    key = {}
    changed = identical = 0

    for pid in baseline:
        b, c = baseline[pid], candidate[pid]
        if _ordered_ids(b) == _ordered_ids(c):
            identical += 1
            continue
        changed += 1
        # Blind A/B assignment
        if rng.random() < 0.5:
            a_label, b_label = "baseline", "candidate"
            rank_a, rank_b = _render(b), _render(c)
        else:
            a_label, b_label = "candidate", "baseline"
            rank_a, rank_b = _render(c), _render(b)
        packets[pid] = {
            "summary": b["summary"],
            "ranking_A": rank_a,
            "ranking_B": rank_b,
        }
        key[pid] = {"A": a_label, "B": b_label}

    (_RUNS_DIR / "packets.json").write_text(json.dumps(packets, indent=2))
    (_RUNS_DIR / "key.json").write_text(json.dumps(key, indent=2))
    return {"changed": changed, "identical": identical, "ids": list(packets)}


def tally(verdicts: dict) -> dict:
    """
    verdicts: {pid: 'A'|'B'|'TIE'}  (judge output, blind labels)
    Returns win/loss/tie for the CANDIDATE after decoding via key.json.
    """
    key = json.loads((_RUNS_DIR / "key.json").read_text())
    wins = losses = ties = 0
    detail = {}
    for pid, choice in verdicts.items():
        if choice == "TIE":
            ties += 1
            detail[pid] = "tie"
            continue
        picked = key[pid][choice]  # 'baseline' or 'candidate'
        if picked == "candidate":
            wins += 1
            detail[pid] = "candidate"
        else:
            losses += 1
            detail[pid] = "baseline"
    judged = wins + losses  # ties excluded from win-rate denominator
    win_rate = (wins / judged) if judged else None
    return {
        "wins": wins, "losses": losses, "ties": ties,
        "win_rate": win_rate, "detail": detail,
    }


if __name__ == "__main__":
    summary = build_packets()
    print(f"changed={summary['changed']} identical={summary['identical']}")
    if summary["ids"]:
        print("judge these:", " ".join(summary["ids"]))
    else:
        print("no ranking changes — nothing to judge (candidate == baseline)")
