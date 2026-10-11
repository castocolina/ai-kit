## Fix Summary: /var/home/bazzite/git/llm-env/docs/superpowers/plans/2026-10-10-system-one-provisioning.md

### Document
/var/home/bazzite/git/llm-env/docs/superpowers/plans/2026-10-10-system-one-provisioning.md

### Findings addressed
- **Setup persists enabled state before provisioning succeeds** — Severity: HIGH. Status: addressed. Edit: `system_one.enabled: true` is written only after image build and weight prefetch both succeed; either failure writes `false` and dies, and a failing-build test covers that path. Section: Task 6.
- **Setup tests run without migrated System One defaults** — Severity: HIGH. Status: addressed. Edit: `run_setup_no_gpu`’s written `models.yml` now includes the full migrated `system_one` block, and the build/prefetch tests assert the image tag and `LAYA_MODELS=english`. Section: Task 6.
- **Budget resource calls omit the llm-server flag** — Severity: MEDIUM. Status: addressed. Edit: Both `cmd_budget` `compute_resource_limits` calls pass `system_one_enabled` and `llm_server_enabled`. Section: Task 4.
- **Endpoint-test helper instructions conflict** — Severity: MEDIUM. Status: addressed. Edit: `_print_endpoints` is defined once from the existing print-endpoints stubs and config; the “do not add a helper” sentence is gone. Section: Task 7.
- **`system-one-build.sh` skips the repo's migrate-before-raw-yq convention** — Severity: MEDIUM. Status: addressed. Edit: The script calls `migrate_config_file` before reading `.system_one.image` and dies when that value is null or empty. Section: Task 2.
- **Task file/commit metadata not reconciled** — Severity: MEDIUM. Status: addressed. Edit: Task 4’s Files list includes `tests/test_cli.py`; Task 7’s `git add` no longer stages `scripts/system-one-cache-check.py`. Section: Tasks 4 and 7.
- **Task 8 LIVE gate rests on an unverified logging assumption** — Severity: MEDIUM. Status: addressed. Edit: Task 11’s decision request captures one `podman logs system-one` line matching `POST /v1/systemone` and fails the plan if none (laya-serve 0.4.2 keeps uvicorn’s default access log). Section: Task 11.
- **Configured ports can violate the paired-plan handoff** — Severity: cross-document. Status: addressed. Edit: The execution-order note says both plans assume port 8010; Task 11 reads `system_one.port` and stops with a clear message when it is not. Section: Execution order and Task 11.

### Findings escalated
None.

### Findings skipped (with disagreement noted)
None.

### Findings not yet addressed
None.

### Status: Edits Applied

## Fix Summary: /var/home/bazzite/git/llm-env/docs/superpowers/plans/2026-10-10-system-one-decision-skill.md

### Document
/var/home/bazzite/git/llm-env/docs/superpowers/plans/2026-10-10-system-one-decision-skill.md

### Findings addressed
- **`--probe` consent behavior has contradictory contracts** — Severity: CRITICAL. Status: addressed. Edit: In auto mode with Laya unavailable, a remote key present, and `JEV_ALLOW_REMOTE` unset, both `screen()` and `--probe` return `status: consent_required_for_remote` and `remote_available`; Global Constraints, Task 6 guidance, the probe branch, and a new test all say that. Section: Global Constraints, Tasks 2, 3, 4, and 6.
- **The baseline control is not isolated from the installed skill** — Severity: HIGH. Status: addressed. Edit: Control runs are fresh `claude -p` processes while `~/.claude/skills/jev-fast-decision` is moved aside and restored by `trap` on EXIT; control prompts never name the skill, and the current-skill arm runs after the restore. Task 6’s no-guidance control uses the same move-aside. Section: Tasks 1 and 6.
- **Calibration CLI integration lacks executable implementation detail** — Severity: HIGH. Status: addressed. Edit: One `--calibrate` branch at the top of `main()` loads `notes/eval-results.json`, prints `JEV_MIN_CONFIDENCE`, and writes each non-null winner over that backend’s `min_confidence` in `scripts/jev_review.py`. Section: Task 7.
- **Body-only word limit is checked against the entire file** — Severity: MEDIUM. Status: addressed. Edit: Step 2 counts words after the closing frontmatter `---` with the specified `awk` pipeline. Section: Task 6 Step 2.
- **Baseline output directory is never created** — Severity: MEDIUM. Status: addressed. Edit: Task 0 creates `notes/baseline/` before the 50 result files are written. Section: Task 0.
- **Task 8 LIVE gate rests on an unverified logging assumption** — Severity: MEDIUM. Status: addressed. Edit: The live prompt says Plan A Task 11 already captured a matching access-log line and failed if none, and an empty log here stops rather than becoming a skill-file fix. Section: Task 8.
- **Hand-off health checks hardcode the configurable port** — Severity: cross-document. Status: addressed. Edit: The execution-order note says both plans assume port 8010 and that Tasks 5–8 must not start if Task 11 stopped because `system_one.port` is not 8010. Section: Execution order.

### Findings escalated
None.

### Findings skipped (with disagreement noted)
None.

### Findings not yet addressed
None.

### Status: Edits Applied

Each plan grew by 20 lines. I did not re-run the suites, and I left the prefetch script as written because it already matches laya 0.4.2’s `DEFAULT_MODELS`, `allow_patterns`, and reviewed SHAs. The `--calibrate` write depends on `min_confidence` staying inside that backend’s dict literal.
