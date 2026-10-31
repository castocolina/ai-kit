# Step 3 reference: the quota wake prompt

MANDATORY read before scheduling or printing the one-shot quota wake (Step 3, the Schedule-or-stop
step of the `"quota"` branch in `references/dispatch-external-cli.md`). The scheduler and the print path use the same prompt.

## The prompt

```text
Quota wake for this one task. For this re-dispatch only: do not resolve a candidate, do not
read the plan, do not re-run the session-wake arm block and do not enter Step 2. Load the
ai-kit-spec-execute-superpowers skill, then:
1. Bind SKILL_DIR=<SKILL_DIR>, SHIM=<SHIM>, TOOLS_PY=<TOOLS_PY>, CWD=<CWD>, QUOTA_PATH=<QUOTA_PATH>,
   DISPATCH_BASE=<DISPATCH_BASE>, PROMPT_FILE=<PROMPT_FILE>, FORMAT_BLOCK_FILE=<FORMAT_BLOCK_FILE>,
   REPORT_FILE=<REPORT_FILE>, RESUME_STATE_PATH=<RESUME_STATE_PATH>, WAKE_SHIM=<WAKE_SHIM>,
   WAKE_OWNED=<WAKE_OWNED>, WAKE_HOST=<WAKE_HOST>, WAKE_ID=<WAKE_ID> and REPORT_MODE=append.
2. In this order: read that state file (JSON, at RESUME_STATE_PATH from step 1) and bind PLAN_FILE (its plan_path) and TASK_N (its
   task_index): they are not among the substituted values. Run SKILL.md's task-paths block, filling
   its six placeholder lines from the step 1 and step 2 values of the same names. This run never
   executes Step 2 or the Seed block: if RESUME_FOUND is not 1 (the state file exists), stop and
   report (Seed would wipe the pin). Record the printed SCALARS path as the loader's literal. Then run
   the "Restore" script in references/state-management.md (never its Step 2 re-entry): it writes
   RUN_DIR's JSON files, INJECTION_JSON.json among them, and prints FIX_ROUND, LAST_DISPATCHED_KEY,
   ESCALATION_ANCHOR_KEY and INJECTION_KEY. Never paste the injection JSON into a command.
3. If PROMPT_FILE still says WRITE the report, replace only that sentence with the APPEND
   sentence; leave the <objective> block byte-identical.
4. Read references/dispatch-external-cli.md, then run its Dispatch step (both blocks, the
   dispatch backgrounded) and its Classify step as written. Every Bash call starts a fresh
   shell: open each with the scalar loader (SCALARS literal from step 2); step 1's values and the
   task-paths block's PLAN_FILE and TASK_N are then in the file too.
5. On "ok", load superpowers:subagent-driven-development, restore its ledger for PLAN_FILE and
   continue at "2. Handle the report" for task TASK_N. Before any later fix round or task, redo
   the ai-kit-spec-execute-superpowers Step 0 and take BRIEF_FILE from the restored ledger; from there a later fix round of
   this task starts at Step 3 with the restored pin, and Step 2 runs only for a later task or an
   owner-named pair.
6. When the job ends, run the skill's "Close the session wake" step with the WAKE_* values above.
```

Substitute all fourteen placeholders (the `<NAME>` tokens inside the block above: SKILL_DIR, SHIM, TOOLS_PY, CWD, QUOTA_PATH, DISPATCH_BASE, PROMPT_FILE, FORMAT_BLOCK_FILE, REPORT_FILE, RESUME_STATE_PATH, WAKE_SHIM, WAKE_OWNED, WAKE_HOST, WAKE_ID; `REPORT_MODE=append` is a literal) with the literal values recorded earlier. `<SKILL_DIR>`, `<SHIM>`
and `<TOOLS_PY>` are the Step 0 lines (the task-paths guard stops the woken run on an empty or `<...>`
value), `<DISPATCH_BASE>` is the one Step 3 printed, and the four `WAKE_*` values are the ones the arm
block printed (an empty `<WAKE_HOST>`/`<WAKE_ID>` with `WAKE_OWNED=0` is correct). Without the `WAKE_*`
values the woken run skips the re-arm on a second quota stop and never closes the wake when the job ends.

The objective block stays byte-identical to the dispatch that just stopped: the runner reuses its
session only when the task digest matches, and rewriting the objective would start a different
task on the same lane. The report sentence sits outside it, so switching WRITE to APPEND never
overwrites the partial report.

## Resume of that wake

Restoring `$RESUME_STATE_PATH` for this re-invoke keeps `injection_json` pinned and does not enter
Step 2. An owner's plain resume keeps it pinned too; Step 2 re-resolves only when the owner names a
replacement pair (`references/state-management.md`). A stop on the re-dispatched run re-enters the
same quota branch; it does not pick another candidate.
