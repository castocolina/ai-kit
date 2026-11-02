#!/bin/sh
# Build the round 7 reports and print the findings.
cd "$(dirname "$0")/../.." || exit 1
J=.planning/phases/27-one-shot-goal-and-loop-prompt-skill/skill-judge/r7
mkdir -p "$J"
SHA=$(cat tmp/p27/judge/r7-digest.txt)
for r in my-referee-one my-referee-three; do
  python3 tmp/p27/build_report.py "$r" "tmp/p27/judge/r7-$r.out" "tmp/p27/judge/r7-$r.err" \
    --sha "$SHA" --out "$J/ai-kit-spec-goal-prompt-$r.md" | sed -n 4,9p
done
python3 tmp/p27/show_findings.py 7
