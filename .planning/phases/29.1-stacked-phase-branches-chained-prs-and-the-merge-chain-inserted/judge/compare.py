#!/usr/bin/env python3
"""Compare one judge round's verdicts with 29-JUDGE.md's native-opus-xhigh fallback verdicts (stdlib only).

usage: compare.py <round> <referee>:<skill> [<referee>:<skill> ...]
       compare.py selftest

The baseline is the `## Fallback verdicts (native-opus-xhigh, 2026-11-04)` table of 29-JUDGE.md, each
skill's last round (Round 2 when re-judged, else Round 1), never the old `## Baselines` table. A delta
is computed only when the verdict's judge is native-opus-xhigh, the judge of that table; any other
judge's row reads `no same-judge baseline`. Each lane row passes the bar on critical, high and grade
only; the regression check is one `pending` row per skill, run by the orchestrator.
"""

import importlib.util
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
JUDGE_MD = ".planning/phases/29-logical-commit-folding-and-the-shared-jev-ladder/29-JUDGE.md"
SECTION = "## Fallback verdicts (native-opus-xhigh, 2026-11-04)"
SAME_JUDGE = "native-opus-xhigh"
NO_BASELINE = "no same-judge baseline"
REGRESSION_LIMIT = -7.0


def load_parse():
    spec = importlib.util.spec_from_file_location("judge_parse", HERE / "parse.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


parse = load_parse()
REPO = parse.REPO


def fallback_baselines():
    """Skill -> percent of its last fallback round (Round 2 when re-judged, else Round 1)."""
    rows = {}
    in_table = False
    for line in parse.read_text(REPO / JUDGE_MD).splitlines():
        if line.startswith(SECTION):
            in_table = True
            continue
        if in_table and line.startswith("## "):
            break
        if not in_table or not line.startswith("| ") or line.startswith(("| Skill", "| ---")):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 3:
            continue
        last = cells[1] if cells[2].startswith("not re-judged") else cells[2]
        match = re.search(r",\s*([0-9.]+)\s+[A-F]\b", last)
        if match:
            rows[cells[0]] = float(match.group(1))
    return rows


def judge_row(verdict, referee, baseline):
    """Format one valid verdict as a table row with its delta and bar verdict."""
    findings = verdict["findings"]
    critical = parse.count_severity(findings, "critical")
    high = parse.count_severity(findings, "high")
    percent = float(verdict["percent"])
    grade = verdict["grade"]
    delta = None
    if verdict["judge"] == SAME_JUDGE and baseline is not None:
        delta = round(percent - baseline, 1)
    reasons = []
    if (critical or high) and grade not in ("A", "B"):
        reasons.append(f"{critical} critical, {high} high at grade {grade}")
    if delta is not None and delta < REGRESSION_LIMIT:
        reasons.append(f"delta {delta:+.1f} below {REGRESSION_LIMIT:g}")
    bar = "pass" if not reasons else "fail: " + "; ".join(reasons)
    delta_text = NO_BASELINE if delta is None else f"{delta:+.1f}"
    score = f"{verdict['total']}/{verdict['max_total']}"
    return (
        f"| {verdict['skill']} | {referee} | {score} | {verdict['percent']} | {grade} "
        f"| {critical} | {high} | {delta_text} | {bar} |"
    )


def regression_pending(skill):
    return (
        f"| {skill} | {SAME_JUDGE} (orchestrator) | - | - | - | - | - | - | "
        "pending: native-opus-xhigh same-judge comparison, run by the orchestrator |"
    )


def lane_status(rnd, referee):
    lane = REPO / "tmp" / "p29.1" / "judge" / f"{rnd}-{referee}"
    status = "status: none (no AIKIT-XAI line)"
    for text in (parse.read_text(Path(f"{lane}.err")), parse.read_text(Path(f"{lane}.out"))):
        for line in text.splitlines():
            if line.startswith("AIKIT-XAI "):
                status = line
    return status


def find_verdict(rnd, referee, skill):
    out = parse.read_text(REPO / "tmp" / "p29.1" / "judge" / f"{rnd}-{referee}.out")
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
    baselines = fallback_baselines()
    assert baselines.get("ai-kit-commit-fold") == 82.4, baselines
    assert baselines.get("ai-kit-gsd-spec-discuss") == 88.8, baselines
    assert baselines.get("ai-kit-spec-execute-superpowers") == 83.2, baselines
    base = {"skill": "s", "total": 112, "max_total": 125, "percent": "89.6", "grade": "B",
            "findings": []}
    same = judge_row(dict(base, judge=SAME_JUDGE), SAME_JUDGE, 89.6)
    assert same.endswith("| +0.0 | pass |"), same
    regress = judge_row(dict(base, judge=SAME_JUDGE, percent="80.0"), SAME_JUDGE, 89.6)
    assert "fail: delta -9.6 below -7" in regress, regress
    lane = judge_row(dict(base, judge="my-referee-one"), "my-referee-one", 89.6)
    assert lane.endswith(f"| {NO_BASELINE} | pass |"), lane
    blocked = judge_row(dict(base, judge="my-referee-one", percent="72.0", grade="C",
                             findings=[{"severity": "critical"}]), "my-referee-one", None)
    assert "fail: 1 critical, 0 high at grade C" in blocked, blocked
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
    baselines = fallback_baselines()
    print("| Skill | Judge | Score | Percent | Grade | Critical | High | Delta | Bar |")
    print("| --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    skills = []
    for pair in argv[2:]:
        referee, skill = pair.split(":", 1)
        if skill not in skills:
            skills.append(skill)
        verdict = find_verdict(rnd, referee, skill)
        if verdict is None:
            print(f"| {skill} | {referee} | missing | | | | | | pending: {lane_status(rnd, referee)} |")
            continue
        print(judge_row(verdict, referee, baselines.get(skill)))
    for skill in skills:
        print(regression_pending(skill))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
