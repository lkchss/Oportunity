"""
Decode blind judge verdicts into a candidate win-rate.

Write the collected verdicts to runs/verdicts.json as {pid: "A"|"B"|"TIE"},
then run:  python -m eval.tally

win_rate = candidate_wins / (wins + losses)   # ties excluded
Decision rule for the loop: keep the candidate only if win_rate > 0.55 AND
losses are not concentrated (no single profile regressing hard). 0.55 is the
floor that beats judge noise on a ~handful of changed profiles.
"""

import json
from pathlib import Path

from eval.diff import tally

_RUNS_DIR = Path(__file__).parent / "runs"


def main() -> None:
    verdicts_path = _RUNS_DIR / "verdicts.json"
    if not verdicts_path.exists():
        print("no runs/verdicts.json — write {pid: 'A'|'B'|'TIE'} there first")
        return
    verdicts = json.loads(verdicts_path.read_text())
    result = tally(verdicts)
    wr = result["win_rate"]
    wr_str = f"{wr:.0%}" if wr is not None else "n/a (all ties)"
    print(f"candidate wins={result['wins']} losses={result['losses']} "
          f"ties={result['ties']}  win_rate={wr_str}")
    regressions = [pid for pid, who in result["detail"].items() if who == "baseline"]
    if regressions:
        print("regressed profiles:", " ".join(regressions))
    verdict = "KEEP" if (wr is not None and wr > 0.55) else "REVERT"
    print(f"decision: {verdict}")


if __name__ == "__main__":
    main()
