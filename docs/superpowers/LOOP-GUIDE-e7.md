# E7 Loop — launch guide & one-shot driver prompt

This is everything needed to run the whole of E7 (FR-7.2 worktree, FR-7.3 slowest-segment,
FR-7.4 hybrid wizard, FR-7.5 sysmem bootstrap) as a single hands-off `/loop`.

## What `/loop` does here

`/loop <prompt>` **with no interval** runs in **dynamic / self-paced** mode: the same prompt is
re-fed to the agent each iteration, and the agent schedules its own next wake-up
(`ScheduleWakeup`) to continue — or **stops** by ending its turn without scheduling one. That
makes the prompt below a *driver*: every iteration it re-orients from disk (the PLAN ledger +
git), does exactly one task, verifies it with a fresh subagent, commits, and loops. Because all
state lives on disk, the loop survives context compaction and finishes in one session.

## Pre-flight (already done for you in the planning session)

- ✅ Branch `feat/e7-loop` created off `main`.
- ✅ FR-7.1 cherry-picked (`97f8cee`); `TestAdoptPredecessorLinks` green (8/8).
- ✅ Committed on this branch: the spec, this guide, and the PLAN ledger.

If you're starting cold, just confirm:

```
git switch feat/e7-loop
git log --oneline -4          # expect: planning-docs commit, then 97f8cee, then f99dc83
make test                     # green baseline
```

## Launch

Type `/loop` (no interval), then paste the **driver prompt** below as the one-shot.

> Monitoring: watch commits land (`git log --oneline`) and boxes flip in
> `docs/superpowers/plans/2026-06-20-e7-loop-PLAN.md`. To stop early, cancel the loop; to
> resume, just relaunch with the same prompt — it re-orients from the ledger and continues.

---

## THE ONE-SHOT DRIVER PROMPT  (copy everything in the block)

```
Execute the E7 build as a self-paced loop. You are on branch feat/e7-loop. You MAY have compacted
since the previous iteration — trust ONLY on-disk state (the PLAN ledger + git), NEVER your memory.
The ledger at docs/superpowers/plans/2026-06-20-e7-loop-PLAN.md is the single source of truth for
progress; the design is docs/superpowers/specs/2026-06-20-e7-execution-design.md.

Do EXACTLY these steps, in order, every iteration:

1. ORIENT. Read the full PLAN ledger. Run `git log --oneline -8` and `git status --porcelain`.
   Confirm you are on feat/e7-loop (else `git switch feat/e7-loop`). If the working tree has
   uncommitted changes from a half-done iteration, reconcile them against the ledger before
   continuing (finish-and-commit if the task's verify passes, else revert them).

2. CHECK DONE. If EVERY `- [ ]` box in the ledger (tasks, FR-GATES, CLOSEOUT) is checked, run the
   full COMPLETION PROMISE verification (make test; make lint; python3 tools/status-line.py
   --doctor; re-run the T2.6 / T4.5 / T5.4 E2E suites; confirm the final review is clean). If and
   ONLY if every clause is literally true, output a line starting `E7-LOOP-COMPLETE:` with a
   one-line summary and END YOUR TURN WITHOUT SCHEDULING A WAKEUP (this stops the loop). If any
   clause is false, uncheck the offending box, append a fix task under the relevant section, and
   go to step 3.

3. PICK ONE. Select the FIRST unchecked `- [ ]` item, reading top-to-bottom (tasks, then that
   FR's gate, then CLOSEOUT). Do ONLY that single item this iteration. Never batch.

4. IMPLEMENT with TDD: write or extend the failing test FIRST (red), implement to green, then
   refactor. Follow the task's `files:`/`spec:`/`tdd:` notes and the design doc. Tests are
   `python3 -m unittest` — NOT pytest. For a task marked 🎨 (UI), FIRST dispatch the
   ui-ux-designer agent for a plan-time review of your approach and fold in its guidance.

5. VERIFY with a FRESH subagent — never self-certify. Dispatch a NEW general-purpose subagent
   (clean context) to run the task's `verify:` command(s); it must return PASS/FAIL WITH the raw
   command output. For 🎨 tasks ALSO dispatch ui-ux-designer for an exec/e2e review. On FAIL: fix
   and re-verify; do NOT check the box.

6. COMMIT + CHECK — only on PASS. Edit the ledger to check the task's box, then make ONE atomic
   commit containing the code + the ledger edit (message: feat(e7)/test(e7)/refactor(e7)/docs(e7):
   <concise>). One logical concern per commit.

7. FR GATE. If the item you just completed was the LAST unchecked TASK of an FR, the next unchecked
   item will be that FR's gate (G2/G3/G4/G5): run /requesting-code-review via a clean subagent
   (scoped to that FR's changes) and /simplify (or /reducing-entropy). Append any HIGH/CRITICAL
   findings as new `- [ ]` tasks under that FR BEFORE moving on; check the gate box only once clean.

8. CONTINUE. End the iteration by scheduling the next wake-up (ScheduleWakeup, delaySeconds ~60,
   re-firing THIS same prompt) so the loop proceeds. Only step 2's true completion promise ends
   the loop by omitting the wake-up.

HARD RULES (non-negotiable):
- One task per iteration. The ledger wins over your memory if they ever disagree.
- NEVER check a box or output E7-LOOP-COMPLETE without PASS evidence from a fresh subagent. Do not
  emit the completion promise to escape a hard task — only when it is literally, fully true.
- Respect the ledger's RUNAWAY BACKSTOP (max 40 iterations): if reached before the promise is true,
  STOP (omit the wake-up) and report the remaining unchecked tasks + the last failing evidence.
  Never report false completion.
- Keep main untouched; all work stays on feat/e7-loop until CLOSEOUT C5.
```

---

## After it finishes

When you see `E7-LOOP-COMPLETE:` the branch is built, verified, and compacted into per-FR
commits, awaiting your merge/PR decision (CLOSEOUT C5 uses `finishing-a-development-branch`,
which asks you how to integrate). If instead it stops on the runaway backstop, it will list
exactly what's left and why — fix or refine, then relaunch the same prompt to resume.
