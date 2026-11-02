#!/bin/sh
# One sanctioned read-only copy of the installed skill-judge files into tmp/ (9 files).
cd "$(dirname "$0")/../.." || exit 1
SRC="$HOME/.claude/skills/skill-judge"
DST="tmp/p27/judge/skills/skill-judge"
mkdir -p "$DST/references/agentskills"
cp "$SRC/SKILL.md" "$DST/SKILL.md"
cp "$SRC/references/rubric.md" "$SRC/references/verdict.schema.json" "$DST/references/"
for f in best-practices.md specification.md optimizing-descriptions.md evaluating-skills.md \
         using-scripts.md skills-ref-validator.py.txt; do
  cp "$SRC/references/agentskills/$f" "$DST/references/agentskills/$f"
done
chmod -R a-w "$DST"
find "$DST" -type f | sort
