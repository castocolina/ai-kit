## Fix Summary: /var/home/bazzite/git/llm-env/docs/superpowers/plans/2026-10-10-system-one-provisioning.md

### Document
/var/home/bazzite/git/llm-env/docs/superpowers/plans/2026-10-10-system-one-provisioning.md

### Findings addressed
- **Plan A finishes by disabling Plan B’s prerequisite** — Severity: CRITICAL. Status: addressed. Edit: Task 11 Step 8 still checks disabled mode, then Step 9 sets `system_one.enabled: true`, runs `make restart`, and requires `curl` health on `http://127.0.0.1:8010`. The paired execution-order paragraph now says live decision-skill steps wait for that ending state. Section: execution order; Task 11 Steps 8–9.
- **Framework Convention Violation** — Severity: HIGH. Status: addressed. Edit: Task 11 checkboxes now use `- [ ] **Step N: ...**`. Section: Task 11.

### Findings escalated
None.

### Findings skipped (with disagreement noted)
None in this document.

### Findings not yet addressed
None.

### Status: Edits Applied

## Fix Summary: /var/home/bazzite/git/llm-env/docs/superpowers/plans/2026-10-10-system-one-decision-skill.md

### Document
/var/home/bazzite/git/llm-env/docs/superpowers/plans/2026-10-10-system-one-decision-skill.md

### Findings addressed
- **Ambiguous cases have contradictory scoring requirements** — Severity: CRITICAL. Status: addressed. Edit: Ambiguous cases stay in `n`, in recorded cases, and in `fallback_rate`. `accuracy`, `accuracy_when_not_fallback`, and `calibrate`’s accuracy omit them. `summarize`, the Task 5 test, the Task 7 rule and test, and the Task 8 live pass line match that. Section: Task 5 interfaces, labeling rule, `summarize`/`main`, Task 7 Step 2, Task 8 check 6.
- **Malformed responses escape `screen()`** — Severity: HIGH. Status: addressed. Edit: `screen()` records `invalid_response` for `checked_response` `ValueError` and for `JSONDecodeError` wrapped by `DispatchError`, and re-raises `invalid_input`. Two end-to-end `screen()` tests cover a bad model and a JSON decode error. Section: Task 4 Steps 1 and 3.
- **Live evaluation commands use the wrong working directory** — Severity: HIGH. Status: addressed. Edit: The live eval and `--calibrate` commands use `python3 -B ~/.claude/skills/jev-fast-decision/scripts/eval_cases.py`. Section: Task 5 Step 4; Task 7 Step 2.
- **The live Laya evaluation does not select Laya explicitly** — Severity: HIGH. Status: addressed. Edit: The live command sets `JEV_BACKEND=laya` and `JEV_LAYA_URL=http://127.0.0.1:8010`, then asserts the printed report and `notes/eval-results.json` both record backend `laya` before Task 6 or 7. Section: Task 5 Step 4.
- **Baseline snapshot can silently remain stale on rerun** — Severity: HIGH. Status: addressed. Edit: Task 0 copies into a staging directory, moves the old snapshot aside, then replaces it, and checks `SKILL.md` is at the snapshot root. Section: Task 0 Step 1.
- **Plan A finishes by disabling Plan B’s prerequisite** — Severity: CRITICAL. Status: addressed. Edit: The execution order, the worker banner, and Task 8 now require provisioning Task 11 to have finished with System One healthy on `http://127.0.0.1:8010`, and they say to stop if that health check fails. Section: header; Task 8.
- **OpenCode free/paid model ladder (owner ruling, not a report finding)** — Severity: n/a. Status: addressed. Edit: `opencode` tries `jev-1.13-free`, then `jev-1.13`, only after 429, 5xx, network error, or 400 `Model is unavailable`. Other 400s and 401/403 do not call the paid id. Attempts record the free failure and `model`. `response_prefix` stays `jev-`. Consent covers both ids. Four tests and `backends/opencode.md` state the sources and that the reset window is undocumented. Section: spec table, global constraints, Tasks 2–4 and 6.

### Findings escalated
None.

### Findings skipped (with disagreement noted)
- **Non-Actionable Step** — Severity: HIGH. Reason: The owner rejected Gemini’s demand for all 32 JSONL lines. The composition rule, six exemplars, and the Step 1 authoring instruction stay as written. NOT addressed in this pass.

### Findings not yet addressed
None.

### Status: Edits Applied

Did not re-open the Laya image or re-score skill-judge; those sections were already concrete and this report did not flag them. Did not execute the plans. Risk: a confident ambiguous case still counts toward calibration’s coverage floor while staying out of the accuracy fraction, which is the rule you set.
