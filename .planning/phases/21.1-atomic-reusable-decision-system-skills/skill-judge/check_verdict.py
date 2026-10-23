#!/usr/bin/env python3
"""Validate Phase 21.1 skill-judge rows against the committed skill trees."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

PHASE = Path(".planning/phases/21.1-atomic-reusable-decision-system-skills")
REPORTS = {
    "jev-fast-decision": {
        "in-session": PHASE / "skill-judge/in-session-jev-fast-decision.md",
        "pi": PHASE / "skill-judge/jev-fast-decision-pi-gpt-6.1-sol-xhigh.md",
        "threshold": 96,
        "activation": True,
    },
    "ai-kit-gsd-spec-discuss": {
        "in-session": PHASE / "skill-judge/in-session-ai-kit-gsd-spec-discuss.md",
        "pi": PHASE / "skill-judge/ai-kit-gsd-spec-discuss-pi-gpt-6.1-sol-xhigh.md",
        "threshold": 106,
        "activation": False,
    },
}
DIMENSIONS = {1: (20, 16), 2: (15, 12), 3: (15, 12), 4: (15, 12),
              5: (15, 12), 6: (15, 12), 7: (10, 8), 8: (15, 12)}
# The end lines a block holds once each (judge-prompt.md); a repeat fails the row (WR-09).
ONCE = {"CURRENT": r"^CURRENT (\d+)/120\s*$", "CRITICAL": r"^CRITICAL (\d+)\s*$",
        "IMPORTANT": r"^IMPORTANT (\d+)\s*$"}


def run(*argv: str) -> str:
    return subprocess.run(argv, check=True, capture_output=True, text=True).stdout.strip()


def current_tree(skill: str) -> tuple[str, str]:
    digest = run(sys.executable, "tests/gsd_curated_eval.py", "digest", "--skill-dir",
                 f"skills/{skill}")
    tree = run("git", "rev-parse", f"HEAD:skills/{skill}")
    return digest, tree


def split_blocks(text: str) -> list[str]:
    matches = list(re.finditer(r"(?m)^DIGEST ([0-9a-f]+)\s*$", text))
    return [text[m.start():matches[i + 1].start() if i + 1 < len(matches) else len(text)]
            for i, m in enumerate(matches)]


def line_values(block: str, pattern: str) -> list[str]:
    return re.findall(pattern, block, re.M)


def cite_ok(block: str, skill_text: str) -> bool:
    lines = skill_text.splitlines()
    for label, phrase in (("CITE_PROBE", "--probe"), ("CITE_BACKEND", "backends/")):
        values = line_values(block, rf"^{label} skills/jev-fast-decision/SKILL\.md:(\d+)\s*$")
        if len(values) != 1:
            return False
        number = int(values[0])
        if number < 1 or number > len(lines) or phrase not in lines[number - 1]:
            return False
    return True


def valid_block(block: str, digest: str, tree: str, threshold: int,
                require_activation: bool, skill_text: str) -> tuple[bool, str, int | None]:
    digests = line_values(block, r"^DIGEST ([0-9a-f]+)\s*$")
    trees = line_values(block, r"^TREE ([0-9a-f]+)\s*$")
    if digests != [digest] or trees != [tree]:
        return False, "digest/tree mismatch", None
    # An end line is the whole line (`D3 13/15`); a narrative `D3 13/15 — ...` is not one.
    dim_rows = re.findall(r"^D([1-8]) (\d+)/\d+\s*$", block, re.M)
    dims = {int(key): int(score) for key, score in dim_rows}
    once = {name: line_values(block, pattern) for name, pattern in ONCE.items()}
    if (len(dim_rows) != len(DIMENSIONS) or set(dims) != set(DIMENSIONS)
            or any(len(values) != 1 for values in once.values())
            or len(line_values(block, r"^VERDICT \S+\s*$")) > 1):
        return False, "missing or duplicate score/end lines", None
    if any(dims[k] < floor or dims[k] > maximum
           for k, (maximum, floor) in DIMENSIONS.items()):
        return False, "dimension below floor", None
    total = sum(dims.values())
    score = int(once["CURRENT"][0])
    if score != total:
        return False, "CURRENT differs from D1-D8 sum", score
    if once["CRITICAL"][0] != "0":
        return False, "Critical findings remain", score
    if "FLOORS ok" not in block:
        return False, "FLOORS not ok", score
    if require_activation:
        if "ACTIVATION ok" not in block or not cite_ok(block, skill_text):
            return False, "activation/cites invalid", score
    if score < threshold:
        return False, f"lowest score {score} below {threshold}", score
    return True, "ok", score


def row_result(skill: str, lane: str) -> tuple[str, str]:
    config = REPORTS[skill]
    path = config[lane]
    if not path.is_file():
        return "fail", "report missing"
    text = path.read_text(encoding="utf-8")
    if "pending (orchestrator)" in text:
        return "pending", "pending (orchestrator)"
    digest, tree = current_tree(skill)
    dirty = run("git", "status", "--porcelain", "--", f"skills/{skill}")
    if dirty:
        return "fail", "skill tree dirty"
    skill_text = Path(f"skills/{skill}/SKILL.md").read_text(encoding="utf-8")
    return judge_blocks(text, (digest, tree), config["threshold"], config["activation"],
                        skill_text)


def judge_blocks(text: str, current: tuple[str, str], threshold: int,
                 activation: bool, skill_text: str) -> tuple[str, str]:
    """(state, reason) over every block judged on the current (digest, tree)."""
    digest, tree = current
    scores = []
    reasons = []
    important_counts = []
    for block in split_blocks(text):
        headers = block.splitlines()[:4]
        if (f"DIGEST {digest}" not in headers
                or f"TREE {tree}" not in headers):
            continue
        ok, reason, score = valid_block(block, digest, tree, threshold, activation,
                                        skill_text)
        if score is None or not ok:
            reasons.append(reason)
        if score is not None:
            scores.append(score)
            important_counts.append(int(line_values(block, ONCE["IMPORTANT"])[0]))
    if not scores:
        return "fail", "no valid current-tree judged block"
    lowest = min(scores)
    if reasons:
        return "fail", f"{'; '.join(reasons)}; lowest={lowest}"
    if important_counts and max(important_counts) > 0:
        return "fail", f"Important findings remain ({max(important_counts)}); lowest={lowest}"
    return "pass", f"lowest={lowest} threshold={threshold}"


def live_result() -> str:
    path = PHASE / "21.1-LIVE-LAYA.md"
    text = path.read_text(encoding="utf-8") if path.is_file() else ""
    match = re.search(r"(?m)^LIVE VERDICT .*?$", text)
    return match.group(0) if match else "LIVE VERDICT missing"


def written_verdict() -> tuple[str, str]:
    path = PHASE / "21.1-SKILL-JUDGE.md"
    text = path.read_text(encoding="utf-8") if path.is_file() else ""
    verdicts = re.findall(r"(?m)^VERDICT: (.+)$", text)
    needed = re.findall(r"(?m)^HUMAN_NEEDED: (.+)$", text)
    return (verdicts[-1] if verdicts else "missing",
            needed[-1] if needed else "")


def self_test() -> bool:
    digest, tree = "a" * 16, "b" * 40
    floors = [floor for _, floor in DIMENSIONS.values()]
    def block(total: int, tree_id: str = tree, activation: str = "ok",
              important: int = 0, d7: int | None = None, cites: bool = True) -> str:
        values = floors[:]
        if d7 is not None:
            values[0] += values[6] - d7
            values[6] = d7
        difference = total - sum(values)
        for index, (maximum, _) in enumerate(DIMENSIONS.values()):
            add = min(maximum - values[index], max(difference, 0))
            values[index] += add
            difference -= add
        if difference:
            values[0] -= abs(difference)
        lines = [f"DIGEST {digest}", f"TREE {tree_id}"]
        lines += [f"D{k} {values[k-1]}/{maximum}" for k, (maximum, _) in DIMENSIONS.items()]
        lines += [f"CURRENT {sum(values)}/120", "CRITICAL 0", f"IMPORTANT {important}",
                  "FLOORS ok", f"ACTIVATION {activation}"]
        if cites:
            lines += ["CITE_PROBE skills/jev-fast-decision/SKILL.md:1",
                      "CITE_BACKEND skills/jev-fast-decision/SKILL.md:2"]
        return "\n".join(lines)
    skill = "run --probe before call\nread backends/ notes\nempty\n"
    def synthetic_row(text: str, require_activation: bool = True) -> bool:
        # The real row loop (row_result's), minus its file, git and dirty-tree reads.
        return judge_blocks(text, (digest, tree), 96, require_activation, skill)[0] == "pass"
    good = block(100)
    tests = [
        synthetic_row(block(96)),
        not synthetic_row(block(95)),
        not synthetic_row(block(95) + "\n" + block(110)),
        not synthetic_row(block(100, tree_id="c" * 40)),
        not synthetic_row(block(100, activation="fail")),
        not synthetic_row(block(100, cites=False)),
        not synthetic_row(block(100).replace("CITE_PROBE skills/jev-fast-decision/SKILL.md:1", "")),
        not synthetic_row(block(100).replace("CITE_PROBE skills/jev-fast-decision/SKILL.md:1",
                                            "CITE_PROBE skills/jev-fast-decision/SKILL.md:3")),
        not synthetic_row(block(100).replace("CITE_PROBE skills/jev-fast-decision/SKILL.md:1",
                                            "CITE_PROBE skills/jev-fast-decision/SKILL.md:99")),
        not synthetic_row(block(100).replace("CITE_BACKEND skills/jev-fast-decision/SKILL.md:2",
                                            "CITE_BACKEND skills/jev-fast-decision/SKILL.md:99")),
        not synthetic_row(block(100, d7=7)),
        not synthetic_row(block(100).replace("CURRENT 100/120", "CURRENT 99/120")),
        not synthetic_row(block(100, important=1)),
        synthetic_row(block(80, tree_id="c" * 40) + "\n" + block(100)),
        synthetic_row(block(96), False),
        not synthetic_row(block(95), False),
        # WR-09: a repeated end line fails the row, whichever value comes last.
        not synthetic_row(good.replace("CRITICAL 0", "CRITICAL 2\nCRITICAL 0")),
        not synthetic_row(good.replace("IMPORTANT 0", "IMPORTANT 1\nIMPORTANT 0")),
        not synthetic_row(good.replace("CURRENT 100/120", "CURRENT 90/120\nCURRENT 100/120")),
        not synthetic_row(good.replace("D3 ", "D3 15/15\nD3 ", 1)),
        not synthetic_row(good + "\nVERDICT fail\nVERDICT pass"),
        synthetic_row(good + "\nVERDICT pass"),
        synthetic_row(good.replace("D3 ", "D3 13/15 — narrative, not an end line\nD3 ", 1)),
    ]
    if not all(tests):
        print(f"self-test cases failed: {[i for i, passed in enumerate(tests, 1) if not passed]}")
    if all(tests):
        print("self-test ok")
        return True
    print("self-test failed")
    return False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--final", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        return 0 if self_test() else 1
    results = []
    for skill in REPORTS:
        for lane in ("in-session", "pi"):
            state, reason = row_result(skill, lane)
            print(f"ROW {skill} {lane} {state}" + (f": {reason}" if state == "fail" else ""))
            results.append(state)
    live = live_result()
    print("LIVE pass" if live == "LIVE VERDICT pass" else live)
    computed = "PASS" if all(result == "pass" for result in results) and live == "LIVE VERDICT pass" else "UNRESOLVED"
    print(f"COMPUTED {computed}")
    written, human = written_verdict()
    print(f"WRITTEN {written}")
    missing = any(not REPORTS[skill][lane].is_file()
                  for skill in REPORTS for lane in ("in-session", "pi"))
    pending = any(state == "pending" for state in results)
    failed = missing
    if written == "PASS" and computed != "PASS":
        failed = True
    if written != "PASS" and not human:
        failed = True
    if pending and written != "BLOCKED: in-session judge pending (orchestrator)":
        failed = True
    if args.final and (pending or (computed == "PASS" and written != "PASS")):
        failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
