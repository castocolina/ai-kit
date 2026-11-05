#!/usr/bin/env python3
"""Parse one judge lane's verdicts into Markdown table rows (stdlib only).

usage: parse.py <round> <referee> <skill> [<skill> ...]

Reads tmp/p29/judge/<round>-<referee>.out and .err (repo root resolved from this file's
path). Prints one row per listed skill, a `meta` line with rubric_version and spec_sha,
and the lane's last AIKIT-XAI status line. Exits 1 when a listed skill has no valid verdict.
"""

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
REQUIRED = (
    "skill",
    "judge",
    "rubric_version",
    "spec_sha",
    "scores",
    "max",
    "total",
    "max_total",
    "percent",
    "grade",
    "findings",
)


def read_text(path):
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def is_valid(verdict):
    if not all(key in verdict for key in REQUIRED):
        return False
    return verdict["grade"] in ("A", "B", "C", "D", "F") and isinstance(verdict["findings"], list)


def count_severity(findings, severity):
    return sum(1 for finding in findings if finding.get("severity") == severity)


def main(argv):
    if len(argv) < 4:
        print("usage: parse.py <round> <referee> <skill> [<skill> ...]", file=sys.stderr)
        return 2
    rnd, referee, skills = argv[1], argv[2], argv[3:]
    lane = REPO / "tmp" / "p29" / "judge" / f"{rnd}-{referee}"
    out_text = read_text(Path(f"{lane}.out"))
    err_text = read_text(Path(f"{lane}.err"))

    status = "status: none (no AIKIT-XAI line)"
    for line in err_text.splitlines() + out_text.splitlines():
        if line.startswith("AIKIT-XAI "):
            status = f"status: {line}"

    verdicts = {}
    for line in out_text.splitlines():
        if not line.startswith('{"skill"'):
            continue
        try:
            verdict = json.loads(line)
        except json.JSONDecodeError as exc:
            print(f"parse: unreadable verdict line: {exc}", file=sys.stderr)
            continue
        if is_valid(verdict):
            verdicts[verdict["skill"]] = verdict

    missing = [skill for skill in skills if skill not in verdicts]
    for skill in skills:
        verdict = verdicts.get(skill)
        if verdict is None:
            continue
        findings = verdict["findings"]
        print(
            f"| {skill} | {verdict['judge']} | {verdict['total']}/{verdict['max_total']} "
            f"| {verdict['percent']} | {verdict['grade']} "
            f"| {count_severity(findings, 'critical')} | {count_severity(findings, 'high')} |"
        )
        print(
            f"meta {skill} rubric_version={verdict['rubric_version']} spec_sha={verdict['spec_sha']}"
        )
    print(status)
    for skill in missing:
        print(f"parse: no valid verdict for {skill}", file=sys.stderr)
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
