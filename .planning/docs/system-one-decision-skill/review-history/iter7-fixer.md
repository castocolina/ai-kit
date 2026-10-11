## Fix Summary: /var/home/bazzite/git/llm-env/docs/superpowers/plans/2026-10-10-system-one-provisioning.md

### Document
/var/home/bazzite/git/llm-env/docs/superpowers/plans/2026-10-10-system-one-provisioning.md

### Findings addressed
- **New setup prompt breaks existing interactive fixtures** — Severity: CRITICAL. Status: addressed. Edit: Task 6 now inserts a System One answer before GPU/model lines in `run_setup_with_numbered_selection` (`"\nn\n" + selection`), `run_setup_no_gpu` (`"\n\n"` or `"n\ny\n1\n"`), and `test_setup_fails_when_the_budget_is_infeasible` (`"1\nn\n1\n1\n"`); the assume-yes rerun and the prerequisites-failure test do not read that prompt. Section: Task 6 Step 1 and Step 4.
- **GPU status becomes factually wrong in System-One-only mode** — Severity: HIGH. Status: addressed. Edit: Architecture and Review Focus 3 include `gpu-status`; Task 7 changes the early exit so “no GPU is in use” happens only when both `llm_server` and `system_one` are off, and adds `test_gpu_status_reports_the_gpu_when_only_system_one_is_enabled` on `run_gpu_status_with_stubs`. Section: Architecture, Review Focus 3, Task 7.
- **The live VRAM gate does not guarantee config restoration** — Severity: MEDIUM. Status: addressed. Edit: Task 11 installs `trap restore_and_restart EXIT` immediately after the backup; the trap restores `models.yml` and runs `make restart`, including on a nonzero exit. Section: Task 11 Step 5.
- **VRAM gate config restore not robust to early failure** — Severity: MEDIUM. Status: addressed. Edit: same trap as above. Section: Task 11 Step 5.
- **Missing Rollback** — Severity: MEDIUM. Status: addressed. Edit: same trap as above. Section: Task 11 Step 5.
- **No test for `print-endpoints.sh` System One output** — Severity: MEDIUM. Status: addressed. Edit: Task 7 adds `test_print_endpoints_system_one_follows_the_flag`, using the existing print-endpoints stub setup, asserting the `8010/v1/systemone` line and `JEV_BACKEND` / `JEV_LAYA_URL` when enabled and their absence when disabled. Section: Task 7 Step 1.
- **Execution Order Synchronization** — Severity: MEDIUM. Status: addressed. Edit: The paired-plan header now says decision-skill Task 6 needs this plan’s Task 11, because it copies Task 5’s eval file and its green scenarios need Laya. Section: Execution order.

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
- **Successful-response fixtures violate the retained response contract** — Severity: CRITICAL. Status: addressed. Edit: none. Every mocked success answer at Task 4 (`_ok_noul`, the 0.75 and 0.6 fixtures) and Task 7 (the 0.8 fixture) already includes `"type": "noul"`, which `_check_noul_answer` requires. Section: Task 4 Step 1, Task 7 Step 2.
- **Kill switch and consent can be bypassed through published interfaces** — Severity: CRITICAL. Status: addressed. Edit: `send`/`dispatch` are `_send`/`_dispatch`. `_send` raises `PermissionError` before any socket when `GSD_PATH_JEV != "1"`, or when the backend is remote and `JEV_ALLOW_REMOTE != "1"`. `test_direct_send_and_dispatch_transmit_nothing_when_gated` calls both directly and fails if `build_opener` runs. Section: Global Constraints, Task 3.
- **Parallel evaluation lanes share non-isolated log counters** — Severity: CRITICAL. Status: addressed. Edit: Parts 1–2 stay in the parallel `$PROMPT`. Part 3 is `$LIVE` and runs glm, then gemini, with no `&`. Section: Task 8.
- **The required writing-skills workflow is incomplete** — Severity: HIGH. Status: addressed. Edit: Header requires test-driven-development. Task 1 tracks the RED items. Task 6 names the Pick-the-backend table as the quick reference, adds Red Flags and Common Mistakes, and micro-tests only the behavior-shaping sentences. Flowchart, git publish, and micro-tests of the reference files are marked N/A with a one-line reason. Task 7 adds new discipline rationalizations to Red Flags. Section: header, Tasks 1, 6, and 7.
- **OpenCode retry branches lack coverage** — Severity: MEDIUM. Status: addressed. Edit: Task 4 tests 500/503 and `OSError` fallthrough to `jev-1.13`, and 401/403 stopping on the free id. Section: Task 4 Step 1.
- **Execution Order Contradiction** — Severity: CRITICAL. Status: addressed. Edit: Tasks 0–4 run without Laya. Task 6 requires Task 11 and Task 5’s `notes/eval-results.json`. Section: Execution order and Task 6 header.

### Findings escalated
None.

### Findings skipped (with disagreement noted)
- **Twenty-six calibration cases are delegated rather than specified** — Severity: HIGH. Reason: owner rejected this again. Composition counts, labeling rules, and the six exemplars stay the level of detail. NOT addressed in this pass.
- **Non-actionable Steps (Documentation)** — Severity: HIGH. Reason: owner rejected this again. Task 10 and Task 6 documentation stay content bullet lists, not full markdown dumps. NOT addressed in this pass.

### Findings not yet addressed
None.

### Status: Edits Applied

Did not re-check the Laya image or re-score skill-judge; this report did not flag those, and Task 8 already uses skill-judge’s eight dimensions and the 96–107 grade B band. The VRAM block must be run with `bash`, not sourced, because the trap calls `exit`.
