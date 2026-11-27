# Fold the finished plan (Step 5)

MANDATORY: read this file in full before running its block; do NOT load it at any other point.

Closes the plan's unit: `fold.py checkpoint --plan "$PLAN_FILE" --base "$FOLD_BASE" --final` folds
the plan's commits (`FOLD_BASE..HEAD`) into one commit per logical feature and marks the unit
finished, then `fold.py ready --plan "$PLAN_FILE"` marks its PR ready. Run it once, after the code
review step (`code-review.md`) passes; the block refuses unless that review passed for the tree of
the current HEAD. The folding policy is the fold skill's `references/folding-policy.md`;
the unit flow is its `references/adapter-guide.md`.

## The block

One `Bash` call. `<SCALARS path printed by the task-paths block>` is the literal path the
task-paths block printed.

```bash
SCALARS="<SCALARS path printed by the task-paths block>"
while IFS== read -r k v; do [[ $k =~ ^[A-Z][A-Z0-9_]*$ ]] || continue; printf -v "$k" '%s' "$v"; done < "$SCALARS"
for n in SKILL_DIR PLAN_FILE FOLD_BASE CWD SHIM QUOTA_PATH PROJECT_KEY; do case "${!n}" in ""|"<"*)
  printf 'ERROR: %s is empty or a placeholder -- fill it from the scalar file\n' "$n"; exit 1 ;; esac; done
CR_STATE="$(dirname "$QUOTA_PATH")/superpowers-run-${PROJECT_KEY}-code-review/state.json"
CR_HEAD="$(python3 -c 'import json,sys; s=json.load(open(sys.argv[1])); print(s["reviewed_head"] if s.get("state") in ("pass", "owner_accepted") else "")' "$CR_STATE" 2>/dev/null)"
CR_TREE="$(git -C "$CWD" rev-parse -q --verify "${CR_HEAD:-none}^{tree}" 2>/dev/null)"
if [ -z "$CR_TREE" ] || [ "$CR_TREE" != "$(git -C "$CWD" rev-parse 'HEAD^{tree}')" ]; then
  printf 'ERROR: the code review has not passed for HEAD (%s) -- STOP and tell the user\n' "$CR_STATE"; exit 1
fi
python3 "$SHIM" close-transports --transport-record "$(dirname "$QUOTA_PATH")/superpowers-run-${PROJECT_KEY}-transport.json" > "$(dirname "$QUOTA_PATH")/superpowers-run-${PROJECT_KEY}-close-transports.json" 2>&1 || printf 'WARNING: close-transports exited %s; the runner sweep closes leftovers at its next start\n' "$?" >&2
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
if [ "${UNIT_FLOW:-1}" = 0 ]; then  # Step 1 ran without the unit flow: fold only, no push, no PR
  python3 "$FOLD_PY" superpowers --plan "$PLAN_FILE" --base "$FOLD_BASE" --repo "$CWD"; exit $?
fi
python3 "$FOLD_PY" checkpoint --plan "$PLAN_FILE" --base "$FOLD_BASE" --final --repo "$CWD" || exit $?
python3 "$FOLD_PY" ready --plan "$PLAN_FILE" --repo "$CWD"
exit $?
```

## Running it

- Where the host has a subagent, dispatch the block to it and relay both flow reports verbatim.
  Otherwise run the block yourself, as written.
- Before folding, the block closes the plan's recorded lane transports (`close-transports`, see `dispatch-external-cli.md` "Lane transport"); its JSON goes to `superpowers-run-<key>-close-transports.json` and a failure is a warning, never a stop.
- The block runs `fold.py checkpoint --plan "$PLAN_FILE" --base "$FOLD_BASE" --final`, then
  `fold.py ready --plan "$PLAN_FILE"`. The checkpoint's report is the flow report: its first line is
  `flow checkpoint <unit>:`. Each report's last line is `outcome: <unit> <done | nothing to do |
  skipped (no consent) | refused <reason>>`. A `skipped (no consent)` outcome means no push ran: the
  owner has not granted push consent yet.
- A refusal does not undo the steps before it: a catch-up push, the checkpoint's fold or its push
  can already be done when a later stage refuses, and the refusal report shows only its `refused:`
  line. Show the report, name the failed stage (`checkpoint` or `ready`) and the reason (the fold
  skill's `SKILL.md`, "Read the report", lists what to tell the user for each one, and
  `references/unit-contract.md` lists the flow's reason codes). Before telling the owner what
  completed, check read-only: the local tip (`git -C "$CWD" rev-parse HEAD`), the recorded unit
  state and PR number (`fold.py show --plan "$PLAN_FILE" --repo "$CWD"`, the `fold.py` the block found;
  it makes no remote call) and, when a push or `ready` may have run, the remote branch tip and the
  PR's state on the remote host. Then stop the run. Never move
  the branch by hand. A refused `ready` leaves the PR a draft.
- With `UNIT_FLOW=0` (Step 1's start was refused `no_remote` or `no_trunk` and the user chose to
  go on), the block folds with `fold.py superpowers --plan` and runs no `ready`; nothing is pushed.
  Its report's last line is `outcome: <unit> <folded | nothing to fold | refused <reason>>`:
  `folded` and `nothing to fold` (exit 0) are its successful outcomes, so they clear the run's
  start scalars exactly as `done` and `nothing to do` do (`SKILL.md` Step 5); a refusal keeps them.
- superpowers' finishing step is not used to merge, push or open a PR for this unit. A plan run
  inline, without this skill, follows the same three commands: `fold.py start --plan`, then
  `fold.py checkpoint --plan` with `--base` and `--final`, then `fold.py ready --plan`.
