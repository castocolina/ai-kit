# Fold the finished plan (Step 5)

MANDATORY: read this file in full before running its block; do NOT load it at any other point.

Folds the plan's commits (`FOLD_BASE..HEAD`) into one commit per logical feature, through the
fold skill's `superpowers` form. Run it once, after the final whole-branch review passes. The
folding policy is the fold skill's `references/folding-policy.md`.

## The block

One `Bash` call. `<SCALARS path printed by the task-paths block>` is the literal path the
task-paths block printed.

```bash
SCALARS="<SCALARS path printed by the task-paths block>"
while IFS== read -r k v; do [[ $k =~ ^[A-Z][A-Z0-9_]*$ ]] || continue; printf -v "$k" '%s' "$v"; done < "$SCALARS"
for n in SKILL_DIR PLAN_FILE FOLD_BASE CWD; do case "${!n}" in ""|"<"*)
  printf 'ERROR: %s is empty or a placeholder -- fill it from the scalar file\n' "$n"; exit 1 ;; esac; done
FOLD_PY=""
for d in "$(dirname "$SKILL_DIR")/ai-kit-commit-fold" \
         "${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills/ai-kit-commit-fold" \
         "$HOME/.agents/skills/ai-kit-commit-fold" \
         "${XDG_CONFIG_HOME:-$HOME/.config}/opencode/skills/ai-kit-commit-fold" \
         "${CURSOR_CONFIG_DIR:-$HOME/.cursor}/skills/ai-kit-commit-fold" \
         "${PI_CODING_AGENT_DIR:-$HOME/.pi/agent}/skills/ai-kit-commit-fold"; do
  [ -f "$d/scripts/fold.py" ] && { FOLD_PY="$d/scripts/fold.py"; break; }
done
if [ -z "$FOLD_PY" ]; then
  printf 'ERROR: ai-kit-commit-fold (scripts/fold.py) is not installed -- STOP and tell the user\n'
  exit 1
fi
python3 "$FOLD_PY" superpowers --plan "$PLAN_FILE" --base "$FOLD_BASE" --repo "$CWD" --mode "${FOLD_MODE:-inline}"
exit $?
```

## Running it

- Where the host has a subagent, dispatch the block to it with `FOLD_MODE=subagent` exported in
  that call, and relay the subagent's report verbatim. Otherwise run the block yourself, as
  written (`inline`). The report's last line says which mode ran.
- The report has five lines: the unit, the commit counts with the grouping source, the tree check,
  the backup tag and the outcome. The outcome is `folded`, `nothing to fold` or `refused <reason>`.
- A refusal changes nothing, so the branch stays where it was. Show the report, name the reason
  (the fold skill's `SKILL.md`, "Read the report", lists what to tell the user for each one) and
  stop the run. Never move the branch by hand.
- After `folded` or `nothing to fold`, superpowers' finishing step is not used to merge, push or
  open a PR for this unit. Tell the user the folded branch is ready for ai-kit's unit flow (push and
  stacked draft PR).
</content>
