#!/usr/bin/env bash
# Run one skill-judge lane through pi and the project cross-AI runner, in review mode.
# usage: run_lane.sh <referee> <round>   e.g. run_lane.sh my-referee-one base
cd "$(dirname "$0")/../../../.." || exit 1
export AI_KIT_REFUSE_REAL_HOME=1
REF="${1:?usage: run_lane.sh <referee> <round>}"
ROUND="${2:?usage: run_lane.sh <referee> <round>}"
JUDGE_DIR=.planning/phases/29-logical-commit-folding-and-the-shared-jev-ladder/judge
OUT="tmp/p29/judge/$ROUND-$REF"

mkdir -p tmp/p29/judge
sed "s/@JUDGE@/$REF/g" "$JUDGE_DIR/prompt-$ROUND.txt" > "$OUT.prompt"

node .claude/gsd-core/bin/gsd-tools.cjs run-with-timeout 3600 -- \
  node .planning/scripts/cross-ai.mjs --runtime pi --model "router-env/$REF" --route-pi router \
  --mode review --outer-timeout 3600 < "$OUT.prompt" > "$OUT.out" 2> "$OUT.err"
RC=$?
echo "lane-exit=$RC" >> "$OUT.err"
exit "$RC"
