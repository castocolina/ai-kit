#!/usr/bin/env bash
# Cross-AI delegation for one plan (execute-phase cross_ai_delegation step).
# Usage: xai_exec.sh <plan-id e.g. 16-01>
set -u
PLAN_ID="$1"
ROOT=/var/home/bazzite/git/personal/ai-kit
SP=/tmp/claude-1000/-var-home-bazzite-git-personal-ai-kit/e987e526-f205-4dcf-ab4a-5e2965c4dea2/scratchpad
PHASE_DIR="$ROOT/.planning/phases/16-ai-kit-spec-extensions"
PLAN="$PHASE_DIR/${PLAN_ID}-PLAN.md"
G="$HOME/.claude/gsd-core/bin/gsd-tools.cjs"
CMD=$(node "$G" query config-get workflow.cross_ai_command --raw 2>/dev/null)
TO=$(node "$G" query config-get workflow.cross_ai_timeout --raw 2>/dev/null || echo 300)
OUT="$SP/xai-${PLAN_ID}"
mkdir -p "$OUT"
cd "$ROOT" || exit 1

PROMPT="$OUT/prompt.md"
{
  echo "# Execution request — ai-kit Phase 16, plan ${PLAN_ID}"
  echo
  echo "You are executing one GSD plan in the git repository at ${ROOT} (your working directory)."
  echo "Project: ai-kit — personal agent skills, slash commands and a one-line installer; multi-CLI toolkit."
  echo "Tech: Python 3 stdlib-only runtime, unittest, Makefile gates (make test-unit / make test / make validate), pre-commit hooks."
  echo "Artifacts and code comments are English only."
  echo "Execute every task below in order, exactly as written, including each task's verify commands and its git commit."
  echo "Never push, never create branches, never install packages, never modify ~/.config/opencode, ~/.gsd or ~/.claude, never use git add -A, never use --no-verify."
  echo "Your FINAL output must be the SUMMARY-shaped markdown report the plan asks for (starting with the heading '# Phase 16 Plan ...')."
  echo
  awk '/^<objective>/{f=1} f{print} /^<\/objective>/{f=0}' "$PLAN"
  echo
  awk '/^<tasks>/{f=1} f{print} /^<\/tasks>/{f=0}' "$PLAN"
} > "$PROMPT"

if ! git diff --quiet HEAD 2>/dev/null; then
  echo "WARNING: dirty working tree detected before ${PLAN_ID}" | tee "$OUT/dirty-warning.txt"
fi
BASE=${BASE_OVERRIDE:-$(git rev-parse HEAD)}
echo "$BASE" > "$OUT/base.txt"
date -Is > "$OUT/start.txt"
RESUME_MSG="You were interrupted by a transient provider error. Continue executing the same plan from exactly where you stopped: first inspect git status, git diff and git log to see what is already done, do not redo completed steps, then finish every remaining task (including verify commands and commits) and end with the SUMMARY-shaped report starting with '# Phase 16 Plan'."
if [ "${RESUME_SID:-}" != "" ]; then
  # Resume an interrupted session instead of starting fresh.
  # shellcheck disable=SC2086
  env -u CLAUDECODE node "$G" run-with-timeout "$TO" -- $CMD -s "$RESUME_SID" "$RESUME_MSG" > "$OUT/stdout.raw" 2> "$OUT/stderr.log"
else
  # shellcheck disable=SC2086
  env -u CLAUDECODE node "$G" run-with-timeout "$TO" -- $CMD < "$PROMPT" > "$OUT/stdout.raw" 2> "$OUT/stderr.log"
fi
EXIT=$?
SID=${RESUME_SID:-$(opencode session list 2>/dev/null | sed -r 's/\x1B\[[0-9;]*[A-Za-z]//g' | awk '/^ses_/{print $1; exit}')}
echo "$SID" > "$OUT/session.txt"
ATTEMPT=0
while [ "$EXIT" -ne 0 ] && grep -q "temporarily unavailable\|cooling down\|is locked\|rate limit" "$OUT/stderr.log" && [ "$ATTEMPT" -lt 6 ]; do
  ATTEMPT=$((ATTEMPT + 1))
  echo "transient provider error; resume attempt $ATTEMPT in 90s (session $SID)" >> "$OUT/resumes.log"
  sleep 90
  cat "$OUT/stdout.raw" >> "$OUT/stdout.all.raw"; cat "$OUT/stderr.log" >> "$OUT/stderr.all.log"
  # shellcheck disable=SC2086
  env -u CLAUDECODE node "$G" run-with-timeout "$TO" -- $CMD -s "$SID" "$RESUME_MSG" > "$OUT/stdout.raw" 2> "$OUT/stderr.log"
  EXIT=$?
done
echo "$EXIT" > "$OUT/exit.txt"
date -Is > "$OUT/end.txt"
# Strip ANSI and keep the final report (last '# Phase 16 Plan' heading onward).
sed -r 's/\x1B\[[0-9;]*[A-Za-z]//g' "$OUT/stdout.raw" > "$OUT/stdout.txt"
LINE=$(grep -n '^# Phase 16 Plan' "$OUT/stdout.txt" | tail -1 | cut -d: -f1)
if [ -n "$LINE" ]; then tail -n +"$LINE" "$OUT/stdout.txt" > "$OUT/summary-candidate.md"; fi
git log --oneline "$BASE..HEAD" > "$OUT/commits.txt"
echo "DONE plan=${PLAN_ID} exit=${EXIT} commits=$(wc -l < "$OUT/commits.txt") summary=$([ -s "$OUT/summary-candidate.md" ] && echo yes || echo no)"
