#!/usr/bin/env bash
# Extract the unchanged base text of the four skills this phase changes, and copy the
# installed skill-judge read-only, into tmp/p29/judge/ (gitignored run space).
cd "$(dirname "$0")/../../../.." || exit 1
set -euo pipefail
export AI_KIT_REFUSE_REAL_HOME=1

BASE=$(git log --diff-filter=A --format=%H -1 -- .planning/phases/29-logical-commit-folding-and-the-shared-jev-ladder/29-01-PLAN.md)
if [ -z "$BASE" ]; then
  echo "prepare: no base commit found for 29-01-PLAN.md" >&2
  exit 1
fi

mkdir -p tmp/p29/judge/base
printf '%s\n' "$BASE" > tmp/p29/judge/base.sha

BASE_PATHS="skills/jev-fast-decision skills/ai-kit-gsd-spec-discuss skills/ai-kit-spec-execute-superpowers skills/ai-kit-spec-goal-prompt tests/test_jev_fast_decision.py tests/test_jev_skill_install_e2e.py tests/test_ai_kit_gsd_spec_discuss.py tests/test_ai_kit_gsd_spec_discuss_e2e.py tests/test_ai_kit_spec_superpowers.py"
GOAL_TESTS=$(git ls-tree --name-only "$BASE" tests/ | grep -E '^tests/test_ai_kit_spec_goal_prompt_.*\.py$' | tr '\n' ' ')
# shellcheck disable=SC2086 # word splitting is the point: these repo paths contain no spaces
git archive "$BASE" $BASE_PATHS $GOAL_TESTS | tar -x -C tmp/p29/judge/base

SJ=""
for d in "${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills/skill-judge" \
         "$HOME/.agents/skills/skill-judge" \
         "${PI_CODING_AGENT_DIR:-$HOME/.pi/agent}/skills/skill-judge"; do
  if [ -d "$d" ]; then
    SJ="$d"
    break
  fi
done
if [ -z "$SJ" ]; then
  echo "prepare: no installed skill-judge directory found" >&2
  exit 1
fi

mkdir -p tmp/p29/judge/skills
rm -rf tmp/p29/judge/skills/skill-judge
cp -rL "$SJ" tmp/p29/judge/skills/skill-judge
echo "prepare: base $BASE, skill-judge copied from $SJ"
