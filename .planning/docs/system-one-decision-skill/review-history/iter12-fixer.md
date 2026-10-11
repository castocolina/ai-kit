## Fix Summary: /var/home/bazzite/git/llm-env/docs/superpowers/plans/2026-10-10-system-one-provisioning.md

### Document
/var/home/bazzite/git/llm-env/docs/superpowers/plans/2026-10-10-system-one-provisioning.md

### Findings addressed
- **System One health-timeout behavior lacks a regression test** — Severity: MEDIUM. Status: addressed. Edit: Added `test_start_exits_when_system_one_health_never_succeeds` (`llm_server_enabled=False`, `CURL_HEALTH_FAIL=1`, 1s timeout) asserting nonzero exit, `System One did not become healthy within 1s`, and `podman compose -f … logs system-one`, and specified the `run_lifecycle_script` curl stub (`tests/test_shell.py` ~4624) that exits 1 only for `/health` when that env is set. Section: Task 7, Step 1.
- **Research cleanup is not resumable** — Severity: MEDIUM. Status: addressed. Edit: Task 10 Step 1 now removes the research container, image, and volume with `podman rm -f` / `rmi` / `volume rm` each followed by `|| true`, then asserts `podman container exists laya`, `podman image exists localhost/laya-rocm`, and `podman volume exists laya-cache` all exit nonzero. Section: Task 10, Step 1.
- **Printed skill configuration is not runnable as advertised** — Severity: cross-document. Status: addressed. Edit: `print-endpoints` now prints `GSD_PATH_JEV=1 JEV_BACKEND=laya JEV_LAYA_URL=http://127.0.0.1:${system_one_port} GSD_PATH_JEV_TIMEOUT_SECONDS=20`, and the enabled-path test asserts that full line. Section: Task 7, `print-endpoints`.

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
- **Required execution workflow cannot track the global skill changes** — Severity: HIGH. Status: addressed. Edit: Header requires `superpowers:executing-plans` (native) and forbids `subagent-driven-development`. Global Constraints and Task 0 snapshot `cp -a` to `/tmp/claude-1000/jev-fast-decision.base` with no `git init`. Tasks 0–8 checkpoints and the final review use `diff -ru` against that snapshot instead of commits or SHAs. Section: preamble, Global Constraints, Tasks 0–8.
- **Non-loopback Laya can bypass the consent boundary** — Severity: HIGH. Status: addressed. Edit: `_send` raises `PermissionError("non_loopback_url")` before any socket when the Laya host is not loopback. `test_direct_send_and_dispatch_transmit_nothing_when_gated` covers direct `_send` and `_dispatch` with `build_opener` patched to fail if a connection is attempted. Section: Global Constraints; Task 3.
- **Calibration is implemented but never run** — Severity: HIGH. Status: addressed. Edit: Task 7 Step 4 runs `eval_cases.py --calibrate`, checks each non-null winner replaced that backend’s `min_confidence` exactly once, reruns the skill suite, and records thresholds in `notes/calibration.json`. `test_needs_fallback_marks_low_confidence` pins `0.7` so the rerun does not follow the calibrated literal. Section: Task 7, Steps 4–5.
- **Evaluation fixes can regress untested backends** — Severity: HIGH. Status: addressed. Edit: After each Task 8 FIX, the full skill pytest suite runs; a failure exits 1 and does not start another evaluation. Section: Task 8, FIX workflow.
- **Laya fixture ordering is implicit** — Severity: MEDIUM. Status: addressed. Edit: `laya` takes `clean_env` so its `JEV_LAYA_URL` override runs after `clean_env`. Section: Task 2 fixtures.
- **Printed skill configuration is not runnable as advertised** — Severity: cross-document. Status: addressed. Edit: Global Constraints, Task 6 `## Call it`, and `backends/laya.md` use the same activation prefix as print-endpoints, including `GSD_PATH_JEV_TIMEOUT_SECONDS=20`. Section: Global Constraints; Task 6.

### Findings escalated
None.

### Findings skipped (with disagreement noted)
- **Most of the calibration corpus is unspecified** — Severity: HIGH. Reason: Owner rejected this required outcome again (no complete 32-case corpus and no deterministic source). The labeling rule and six exemplars stay; the other 26 lines are still authored during Task 5 Step 1. NOT addressed in this pass.

### Findings not yet addressed
None.

### Status: Edits Applied

Net growth: provisioning +10 lines, decision-skill +20 lines. Did not re-check the Laya image (this report had no prefetch placeholder finding) and did not execute either plan. The corpus finding will return if the next review does not treat the owner rejection as final.
