# Fold the finished plan (Step 5)

MANDATORY: read this file in full before running its block; do NOT load it at any other point.

Closes the plan's unit: `fold.py checkpoint --plan "$PLAN_FILE" --base "$FOLD_BASE" --final` folds
the plan's commits (`FOLD_BASE..HEAD`) into one commit per logical feature and marks the unit
finished, then `fold.py ready --plan "$PLAN_FILE"` marks its PR ready. Run it once, after the final
whole-branch review passes. The folding policy is the fold skill's `references/folding-policy.md`;
the unit flow is its `references/adapter-guide.md`.

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
python3 "$FOLD_PY" checkpoint --plan "$PLAN_FILE" --base "$FOLD_BASE" --final --repo "$CWD" || exit $?
python3 "$FOLD_PY" ready --plan "$PLAN_FILE" --repo "$CWD"
exit $?
```

## Running it

- Where the host has a subagent, dispatch the block to it and relay both flow reports verbatim.
  Otherwise run the block yourself, as written.
- The block runs `fold.py checkpoint --plan "$PLAN_FILE" --base "$FOLD_BASE" --final`, then
  `fold.py ready --plan "$PLAN_FILE"`. The checkpoint's report is the flow report: its first line is
  `flow checkpoint <unit>:`. Each report's last line is `outcome: <unit> <done | nothing to do |
  skipped (no consent) | refused <reason>>`. A `skipped (no consent)` outcome means no push ran: the
  owner has not granted push consent yet.
- A refusal changes nothing, so the branch stays where it was. Show the report, name the reason (the
  fold skill's `SKILL.md`, "Read the report", lists what to tell the user for each one, and
  `references/unit-contract.md` lists the flow's reason codes) and stop the run. Never move the
  branch by hand. A refused `ready` leaves the PR a draft.
- superpowers' finishing step is not used to merge, push or open a PR for this unit. A plan run
  inline, without this skill, follows the same three commands: `fold.py start --plan`, then
  `fold.py checkpoint --plan` with `--base` and `--final`, then `fold.py ready --plan`.
</content>
