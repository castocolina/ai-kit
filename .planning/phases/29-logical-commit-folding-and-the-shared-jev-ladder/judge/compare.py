#!/usr/bin/env python3
"""Compare one judge round's verdicts with the 29-JUDGE.md baselines (stdlib only).

usage: compare.py <round> <referee>:<skill> [<referee>:<skill> ...]
       compare.py selftest

Reads tmp/p29/judge/<round>-<referee>.out (verdict lines) and the `## Baselines` table of
29-JUDGE.md, and prints one Markdown row per pair: score, percent, grade, critical and high
counts, the delta in percentage points to the same judge's baseline (`none` when that judge
has no baseline for the skill, e.g. ai-kit-commit-fold), and the bar verdict.

Bar: `pass` when (no critical and no high finding, or grade A or B) and the delta is not
below -7; else `fail` with the reason. A pair with no valid verdict prints a `pending` row
that names the lane status line.
"""

import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
JUDGE_MD = ".planning/phases/29-logical-commit-folding-and-the-shared-jev-ladder/29-JUDGE.md"
REGRESSION_LIMIT = -7.0


def load_parse():
    spec = importlib.util.spec_from_file_location("judge_parse", HERE / "parse.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


parse = load_parse()
REPO = parse.REPO


def baselines():
    rows = {}
    in_table = False
    for line in parse.read_text(REPO / JUDGE_MD).splitlines():
        if line.startswith("## Baselines"):
            in_table = True
            continue
        if in_table and line.startswith("## "):
            break
        if not in_table or not line.startswith("| ") or line.startswith(("| Skill", "| ---")):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) >= 4:
            rows[(cells[0], cells[1])] = float(cells[3])
    return rows


def judge_row(verdict, referee, baseline):
    """Format one valid verdict as a table row with its delta and bar verdict."""
    findings = verdict["findings"]
    critical = parse.count_severity(findings, "critical")
    high = parse.count_severity(findings, "high")
    percent = float(verdict["percent"])
    grade = verdict["grade"]
    delta = None if baseline is None else round(percent - baseline, 1)
    reasons = []
    if (critical or high) and grade not in ("A", "B"):
        reasons.append(f"{critical} critical, {high} high at grade {grade}")
    if delta is not None and delta < REGRESSION_LIMIT:
        reasons.append(f"delta {delta:+.1f} below {REGRESSION_LIMIT:g}")
    bar = "pass" if not reasons else "fail: " + "; ".join(reasons)
    delta_text = "none" if delta is None else f"{delta:+.1f}"
    score = f"{verdict['total']}/{verdict['max_total']}"
    return (
        f"| {verdict['skill']} | {referee} | {score} | {verdict['percent']} | {grade} "
        f"| {critical} | {high} | {delta_text} | {bar} |"
    )


def lane_status(rnd, referee):
    lane = REPO / "tmp" / "p29" / "judge" / f"{rnd}-{referee}"
    status = "status: none (no AIKIT-XAI line)"
    for text in (parse.read_text(Path(f"{lane}.err")), parse.read_text(Path(f"{lane}.out"))):
        for line in text.splitlines():
            if line.startswith("AIKIT-XAI "):
                status = line
    return status


def find_verdict(rnd, referee, skill):
    out = parse.read_text(REPO / "tmp" / "p29" / "judge" / f"{rnd}-{referee}.out")
    for line in out.splitlines():
        if not line.startswith('{"skill"'):
            continue
        try:
            verdict = json.loads(line)
        except json.JSONDecodeError:
            continue
        if parse.is_valid(verdict) and verdict["skill"] == skill:
            return verdict
    return None


def selftest():
    base = 89.6
    ok = judge_row(
        {"skill": "s", "total": 112, "max_total": 125, "percent": "89.6", "grade": "B",
         "findings": []}, "r", base)
    assert ok.endswith("| +0.0 | pass |"), ok
    regress = judge_row(
        {"skill": "s", "total": 100, "max_total": 125, "percent": "80.0", "grade": "B",
         "findings": []}, "r", base)
    assert "fail: delta -9.6 below -7" in regress, regress
    blocked = judge_row(
        {"skill": "s", "total": 90, "max_total": 125, "percent": "72.0", "grade": "C",
         "findings": [{"severity": "critical"}]}, "r", None)
    assert "| 1 | 0 | none | fail: 1 critical, 0 high at grade C |" in blocked, blocked
    lenient = judge_row(
        {"skill": "s", "total": 115, "max_total": 125, "percent": "92.0", "grade": "A",
         "findings": [{"severity": "high"}]}, "r", None)
    assert lenient.endswith("| none | pass |"), lenient
    print("selftest ok")
    return 0


def main(argv):
    if len(argv) == 2 and argv[1] == "selftest":
        return selftest()
    if len(argv) < 3:
        print("usage: compare.py <round> <referee>:<skill> [...] | compare.py selftest",
              file=sys.stderr)
        return 2
    rnd = argv[1]
    base = baselines()
    print("| Skill | Judge | Score | Percent | Grade | Critical | High | Delta | Bar |")
    print("| --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for pair in argv[2:]:
        referee, skill = pair.split(":", 1)
        verdict = find_verdict(rnd, referee, skill)
        if verdict is None:
            print(f"| {skill} | {referee} | missing | | | | | | pending: {lane_status(rnd, referee)} |")
            continue
        print(judge_row(verdict, referee, base.get((skill, referee))))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
