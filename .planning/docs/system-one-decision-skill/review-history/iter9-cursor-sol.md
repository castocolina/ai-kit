## Review: 2026-10-10-system-one-provisioning.md; 2026-10-10-system-one-decision-skill.md
### Document Type
Superpowers · plan (both documents)

### CRITICAL
- **`--probe` consent behavior has contradictory contracts** — Location: decision-skill Global Constraints line 32; Task 2 lines 141–143 and 386–401; Task 6 lines 1271–1274. Required: define and test one result for auto mode when Laya is unavailable, a remote key exists, and consent is absent. Why: the drafted implementation returns `no_backend_available`, while the constraints and skill guidance require `consent_required_for_remote` with `remote_available`.

### HIGH
- **Setup persists enabled state before provisioning succeeds** — Location: provisioning Task 6 lines 913–927. Required: persist `system_one.enabled: true` only after image build and weight prefetch succeed, or restore `false` on failure. Why: a failed build/download leaves a partially provisioned configuration marked enabled.
- **Setup tests run without migrated System One defaults** — Location: provisioning Task 6 lines 681–797. Required: make `run_setup_no_gpu` execute real migration or provide the complete migrated `system_one` section and assert its image/models values. Why: its current `uv` stub returns success for `migrate-config` without modifying the minimal fixture, allowing build and prefetch tests to operate on `null` values and false-pass.
- **The baseline control is not isolated from the installed skill** — Location: decision-skill Tasks 0–1 lines 60–126 and Task 6 Step 3. Required: prevent control agents from discovering/loading the live global `jev-fast-decision` skill. Why: omitting the snapshot path does not create a no-skill control, especially when prompts explicitly mention or trigger the skill.
- **Calibration CLI integration lacks executable implementation detail** — Location: decision-skill Task 5 lines 1202–1238; Task 7 lines 1296–1339. Required: specify the exact `--calibrate` branch, result-file loading, output, and threshold-update workflow. Why: the only complete `main()` handles normal evaluation and `--record`; adding `calibrate()` alone cannot execute the documented command.

### MEDIUM
- **Budget resource calls omit the llm-server flag** — Location: provisioning Task 4 lines 581–583. Required: pass both `system_one_enabled` and `llm_server_enabled` to both `compute_resource_limits` calls in `cmd_budget`. Why: System-One-only configurations otherwise reserve RAM as though llama.cpp were also enabled.
- **Endpoint-test helper instructions conflict** — Location: provisioning Task 7 lines 1037–1063. Required: either define `_print_endpoints` explicitly or inline both executions consistently. Why: the test calls that helper while its instructions say not to add one.
- **Body-only word limit is checked against the entire file** — Location: decision-skill Task 6 Step 2, line 1285. Required: count words after the closing YAML frontmatter delimiter. Why: `wc -w SKILL.md` includes frontmatter and does not verify the stated body-only limit.
- **Baseline output directory is never created** — Location: decision-skill Task 0 lines 55–58; Task 1 line 124. Required: create `notes/baseline/` before writing the 50 result files. Why: Task 0 creates only `notes/`.

### Cross-Document Consistency
- **Configured ports can violate the paired-plan handoff** — Location: provisioning Task 1 lines 75–80 and Task 11 lines 1528–1581; decision-skill execution order and live tasks. Required: either force `system_one.port: 8010` before the handoff or consistently derive and export the configured port as `JEV_LAYA_URL`. Why: migration preserves an existing custom port, but both plans later hard-code `127.0.0.1:8010`.

### Status: Issues Found — fix and re-invoke
