#!/usr/bin/env bash
# Copy the installed skill-judge read-only into tmp/p29.1/judge/skills/ (gitignored run space).
# The judged text is the working tree, so no base extraction is needed (unlike Phase 29's prepare.sh).
cd "$(dirname "$0")/../../../.." || exit 1
set -euo pipefail
export AI_KIT_REFUSE_REAL_HOME=1

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

mkdir -p tmp/p29.1/judge/skills
rm -rf tmp/p29.1/judge/skills/skill-judge
cp -rL "$SJ" tmp/p29.1/judge/skills/skill-judge
echo "prepare: skill-judge copied from $SJ"
