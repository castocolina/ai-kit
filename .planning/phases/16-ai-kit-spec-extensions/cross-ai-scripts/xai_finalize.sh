#!/usr/bin/env bash
# Finalize a cross-AI-executed plan: write SUMMARY.md (frontmatter + executor report +
# orchestrator verification note), update ROADMAP/STATE, commit docs.
# Usage: xai_finalize.sh <plan-id> <base-sha> "<orchestrator verification note>"
set -eu
PLAN_ID="$1"; BASE="$2"; NOTE="$3"
ROOT=/var/home/bazzite/git/personal/ai-kit
SP=/tmp/claude-1000/-var-home-bazzite-git-personal-ai-kit/e987e526-f205-4dcf-ab4a-5e2965c4dea2/scratchpad
G="$HOME/.claude/gsd-core/bin/gsd-tools.cjs"
PHASE_DIR="$ROOT/.planning/phases/16-ai-kit-spec-extensions"
OUT="$SP/xai-${PLAN_ID}"
PLAN_NUM="${PLAN_ID#16-}"
SUMMARY="$PHASE_DIR/${PLAN_ID}-SUMMARY.md"
cd "$ROOT"
[ -s "$OUT/summary-candidate.md" ] || { echo "ERROR: empty summary candidate" >&2; exit 1; }
grep -q '^# Phase 16 Plan' "$OUT/summary-candidate.md" || { echo "ERROR: summary has no heading" >&2; exit 1; }
CREATED=$(git diff --name-only --diff-filter=A "$BASE" HEAD | grep -v '^\.planning/' | sed 's/^/    - /')
MODIFIED=$(git diff --name-only --diff-filter=M "$BASE" HEAD | grep -v '^\.planning/' | sed 's/^/    - /')
NCOMMITS=$(git rev-list --count "$BASE..HEAD")
RESUMES=$(wc -l < "$OUT/resumes.log" 2>/dev/null || echo 0)
{
  echo "---"
  echo "phase: 16-ai-kit-spec-extensions"
  echo "plan: ${PLAN_NUM}"
  echo "subsystem: ai_kit_spec"
  echo "executor: cross-ai (opencode run --model router-env/my-coding)"
  echo "actuals:"
  echo "  commits: ${NCOMMITS}"
  echo "key-files:"
  echo "  created:"
  [ -n "$CREATED" ] && echo "$CREATED" || echo "    []"
  echo "  modified:"
  [ -n "$MODIFIED" ] && echo "$MODIFIED" || echo "    []"
  echo "completed: $(date +%Y-%m-%d)"
  echo "---"
  echo
  cat "$OUT/summary-candidate.md"
  echo
  echo "## Cross-AI execution (orchestrator record)"
  echo
  echo "- Executor: \`opencode run --model router-env/my-coding\` (cross_ai: true), prompt = plan <objective> + <tasks> via stdin."
  echo "- Automatic session resumes after transient provider errors: ${RESUMES}."
  echo "- Orchestrator verification: ${NOTE}"
} > "$SUMMARY"
node "$G" query roadmap.update-plan-progress 16 "$PLAN_ID" complete >/dev/null 2>&1 || true
node "$G" query state.advance-plan >/dev/null 2>&1 || true
node "$G" query state.update-progress >/dev/null 2>&1 || true
git add "$SUMMARY" .planning/STATE.md .planning/ROADMAP.md .planning/state.json 2>/dev/null || true
git commit -q -m "docs(${PLAN_ID}): complete plan via cross-AI execution

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01UKVtiJfV2FnhffQXFKQRL8"
git log --oneline -1
