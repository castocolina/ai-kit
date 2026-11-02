"""Print the findings of both judges of one round: show_findings.py <round>."""

import json
import sys

ROOT = ".planning/phases/27-one-shot-goal-and-loop-prompt-skill/skill-judge"
for judge in ("my-referee-one", "my-referee-three"):
    path = f"{ROOT}/r{sys.argv[1]}/ai-kit-spec-goal-prompt-{judge}.md"
    verdict = json.loads(open(path, encoding="utf-8").read().splitlines()[-1])
    print("==", judge, verdict["total"], verdict["percent"], verdict["scores"])
    for f in verdict["findings"]:
        print(f["id"], f["severity"], f["file"], f["line"])
        print("   E:", f["evidence"][:420])
