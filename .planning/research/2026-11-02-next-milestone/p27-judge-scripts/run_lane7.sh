#!/bin/sh
# Run one skill-judge lane through pi/router in review mode; usage: run_lane.sh my-referee-one
cd "$(dirname "$0")/../.." || exit 1
export AI_KIT_REFUSE_REAL_HOME=1
REF="$1"
OUT="tmp/p27/judge/r7-$REF"
sed "s/@JUDGE@/$REF/g" tmp/p27/judge/prompt-template-r7.txt > "$OUT.prompt"
node .claude/gsd-core/bin/gsd-tools.cjs run-with-timeout 3600 -- \
  node .planning/scripts/cross-ai.mjs --runtime pi --model "router-env/$REF" --route-pi router \
  --mode review --outer-timeout 3600 < "$OUT.prompt" > "$OUT.out" 2> "$OUT.err"
echo "lane-exit=$?" >> "$OUT.err"
