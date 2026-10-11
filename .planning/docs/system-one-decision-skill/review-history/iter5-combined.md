- **Live evaluation commands resolve against the wrong repository** — Location: decision-skill plan, Task 5 Step 4 and Task 7 Step 2 (lines 974–976 and 1044–1047). Required: Use the authoritative absolute paths under `~/.claude/skills/jev-fast-decision/scripts/` (or add an explicit `cd` to that skill root) for both eval and calibration commands. Why: the review document lives in and is executed from `llm-env`; `python3 -B scripts/eval_cases.py` otherwise targets `llm-env/scripts/`, where that file does not exist.- **The “live Laya” evaluation does not pin Laya** — Location: decision-skill plan, Task 5 Step 4 (lines 974–976). Required: Run the live recording with an explicit `JEV_BACKEND=laya` and controlled Laya URL/selection environment, then assert the recorded backend before Task 6/7 consume it. Why: `screen()` intentionally honors ambient `JEV_BACKEND`; a session configured for TypeSafe or OpenCode can silently record and calibrate the wrong backend despite the step being labeled as the Laya evaluation.
## Review: 2026-10-10-system-one-provisioning.md, 2026-10-10-system-one-decision-skill.md
### Document Type
Superpowers · plan (both documents)

### CRITICAL
- **Ambiguous cases have contradictory scoring requirements** — Location: decision-skill Task 5, lines 787–790, 839–847, and 944–969. Required: Define and test one consistent rule for excluding or including ambiguous cases in `n`, accuracy, fallback metrics, recorded results, and calibration. Why: the plan says scoring ignores ambiguous cases, while the test expects `n == 32` and the implementation scores and records all five ambiguous cases.

### HIGH
- **Malformed responses escape `screen()`** — Location: decision-skill Task 4 Step 3, lines 739–768. Required: Catch validation and JSON errors from `checked_response()` and return or record `invalid_response`, with an end-to-end `screen()` test. Why: only `DispatchError` is caught, so malformed backend responses raise a stack trace.
- **Live evaluation commands use the wrong working directory** — Location: decision-skill Task 5 Step 4 and Task 7 Step 2, lines 974–976 and 1044–1047. Required: Use absolute paths under `~/.claude/skills/jev-fast-decision/scripts/` or explicitly change to that directory. Why: from the llm-env root, `scripts/eval_cases.py` does not exist.
- **The live Laya evaluation does not select Laya explicitly** — Location: decision-skill Task 5 Step 4, lines 974–976. Required: Set `JEV_BACKEND=laya`, control the Laya URL, and assert the recorded backend before calibration. Why: ambient backend configuration can silently evaluate and calibrate TypeSafe or OpenCode instead.
- **Baseline snapshot can silently remain stale on rerun** — Location: decision-skill Task 0 Step 1, lines 59–61. Required: Recreate the destination atomically or require it to be absent before copying. Why: `cp -r source existing-destination` nests the new copy while leaving the old `SKILL.md` at the path used by baseline agents.

### Cross-Document Consistency
- **CRITICAL — Plan A finishes by disabling Plan B’s prerequisite** — Location: provisioning Task 11, lines 1494–1496; decision-skill execution order and Task 8, lines 3–4 and 1052–1066. Required: Re-enable System One and verify port 8010 healthy after the disabled-mode test, or add that gate before Plan B’s live tasks. Why: Plan B requires a healthy Laya service, but Plan A’s final prescribed state has no System One container.

### Status: Issues Found — fix and re-invoke

## Review: /var/home/bazzite/git/llm-env/docs/superpowers/plans/2026-10-10-system-one-provisioning.md, /var/home/bazzite/git/llm-env/docs/superpowers/plans/2026-10-10-system-one-decision-skill.md
### Document Type
superpowers · plan
### HIGH
- **Framework Convention Violation** — Location: Provisioning Plan, Task 11. Required: Tasks must use the `- [ ] **Step N: ...**` format. Why: The tasks use plain checkboxes without the step prefix, violating the framework's strict tracking syntax encoded in the profile.
- **Non-Actionable Step** — Location: Decision Skill Plan, Task 5. Required: Provide the exact 32 JSONL cases in the plan. Why: The plan deliberately omits 26 cases and instructs the implementer to author them from a rule, violating the plan requirement to provide exact code that is executable by a zero-context engineer.
### Status: Issues Found — fix and re-invoke
