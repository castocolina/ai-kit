# Start the plan's unit (Step 1)

MANDATORY: read this file in full before the first task and run its block once; do NOT load it at
any other point.

The block finds the fold skill's `scripts/fold.py`, runs `fold.py start --plan` (it creates the
plan's unit branch on the stack top and checks it out, or reuses it) and checks that the plan file
is still in the tree. superpowers' planning skills commit the spec and plan before this step;
`start` carries those local-only commits onto the unit branch, so they stay in its PR and below
`FOLD_BASE`. It carries each local-only commit that touches the plan file or the spec named on the
plan's `**Spec:**` line, even when the spec was committed on its own; other local-only commits
stay off the unit.

## The block

One `Bash` call, before the Task paths block (no scalar file exists yet).

```bash
SKILL_DIR="<Step 0 SKILL_DIR>"; CWD="<Step 1 CWD>"; PLAN_FILE="<Step 1 PLAN_FILE>"
for n in SKILL_DIR CWD PLAN_FILE; do case "${!n}" in ""|"<"*)
  printf 'ERROR: %s is empty or a placeholder -- fill it from Step 0/Step 1\n' "$n"; exit 1 ;; esac; done
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
  printf 'ERROR: ai-kit-commit-fold (scripts/fold.py) is not installed -- STOP and tell the user\n'; exit 1
fi
python3 "$FOLD_PY" start --plan "$PLAN_FILE" --repo "$CWD" || exit $?
python3 "$FOLD_PY" boundary --plan "$PLAN_FILE" --point wave --repo "$CWD" || true
cd "$CWD" && [ -f "$PLAN_FILE" ] || {
  printf 'ERROR: %s left the tree after start -- STOP and tell the user\n' "$PLAN_FILE"; exit 1; }
```

The second boundary line is the wave-point run before the first task: `start` already runs the boundary for the unit's start, and this second run is the one before the first task. That is why a boundary problem never stops the plan (`|| true`).

## Reading the result

- Exit 0: go on to the Task paths block and record `FOLD_BASE` (Step 1 of `SKILL.md`).
- `refused no_remote` or `refused no_trunk` (no remote, or no remote target to stack on): show the
  report and ask the user whether to run the plan on the current branch without the unit flow. On
  yes, record `UNIT_FLOW=0` with `FOLD_BASE`; Step 5 then folds with the plain form, with no push
  and no PR. On no, stop.
- Any other refusal (`dirty_tree`, `plan_not_carried`, `wrong_parent`, ...): show the report with
  the fold skill's next step for that reason (its `SKILL.md` tables) and stop before the first
  task. A refusal changes nothing; never move the branch by hand.
- `ERROR: ... left the tree after start`: an older fold skill is installed. Stop and tell the user.
