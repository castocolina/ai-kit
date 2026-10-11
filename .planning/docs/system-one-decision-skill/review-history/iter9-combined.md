## Reviewer cursor-sol
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

## Reviewer opencode-glm53
### Document Type
superpowers · plan (both documents)

### Files Read
- /var/home/bazzite/git/llm-env/docs/superpowers/plans/2026-10-10-system-one-provisioning.md (1594 lines)
- /var/home/bazzite/git/llm-env/docs/superpowers/plans/2026-10-10-system-one-decision-skill.md (1536 lines)
- Grounding: llm-env (scripts/{start,check-setup,check-server,gpu-status,clean,print-endpoints,help}.sh, setup/{setup,render-unit}.sh, tools/lib.sh, pylib/{config,compose,resources,budget,detect,gguf}.py, llmenv.py, Makefile, models.yml.example, .agents/architecture.md, docker/laya-rocm/Dockerfile, tests/{test_shell,test_config,test_compose,test_resources,test_budget,test_detect}.py) and the skill dir (~/.claude/skills/jev-fast-decision/{SKILL.md,reference.md,scripts/jev_review.py}, skill-judge/SKILL.md). Every line citation, helper signature, and existing-behavior claim in both plans was verified against these files and found accurate.

### MEDIUM

- **`system-one-build.sh` skips the repo's migrate-before-raw-yq convention** — Location: Plan A, Task 2 Step 3 (`scripts/system-one-build.sh`). Required: call `migrate_config_file` (or die on a null/empty image) before `image="$(yq -r '.system_one.image' …)"`. Why: the convention is documented in-repo at scripts/gpu-status.sh:14-25 and followed by every user-facing entrypoint; every other new reader in the plan is safe (start.sh migrates at line 12, render-unit.sh at 11, check-setup.sh at 174, clean.sh null-guards), but standalone `make system-one-build` on a config predating `system_one` gets `null` from yq and builds an ~18 GB image tagged `null`.

- **Task file/commit metadata not reconciled** — Location: Plan A, Task 4 (Files header vs Step 3 and Step 5) and Task 7 (Step 5 commit). Required: add `tests/test_cli.py` to Task 4's Files list (Step 3 modifies its `cmd_budget` tests and the commit stages it), and drop `scripts/system-one-cache-check.py` from Task 7's `git add` (created and committed in Task 6, unmodified in Task 7). Why: a zero-context engineer working from the Files headers misses the test_cli.py change; the stale staging entry misstates Task 7's blast radius.

- **Task 8 LIVE gate rests on an unverified logging assumption** — Location: Plan B, Task 8 Step 2 (`posts()` = `podman logs system-one | rg -c 'POST /v1/systemone'`, used by LIVE checks 1–9, delta assertions in 2/5/7/9). Required: pin evidence that laya-serve 0.4.2 emits access-log lines matching `POST /v1/systemone` (one observed `podman logs` line captured during Plan A Task 11 or Task 5's live run) into the plan, or specify what to do when the log is empty. Why: the measured-facts table and appendix capture health and a response body but never a log line; if laya-serve's access logging is off, LIVE check 2 (delta == 3) fails on every round for a cause the FIX prompt cannot repair (it only edits skill files), burning all 3 rounds and reporting a false skill failure.

### Cross-Document Consistency

- **Hand-off health checks hardcode the configurable port** — Location: Plan A Task 11 Step 9 (`curl … http://127.0.0.1:8010/health`) and Plan B Task 8 Step 1 (`curl -sf http://127.0.0.1:8010/health`) vs Plan A Task 1 (`system_one.port` configurable; Step 5 of Task 11 already reads it from config). Required: read the port from config in Task 11 Step 9, or state explicitly that both plans' gates assume the default port. Why: minor ambiguity with a safe default — triggers only if a user hand-edits `system_one.port` away from 8010, in which case the "leave it healthy" gate probes the wrong port. Otherwise the two plans are mutually consistent: paired-task gating (A:Task 11 ↔ B:Tasks 5–8), env names (`JEV_BACKEND`/`JEV_LAYA_URL` in A's print-endpoints match B's contract), default URL, `jev-1`/`laya-rl-agent` model ids, appendix JSON shapes, and the Task 5→6 eval-results dependency all agree.

### Status: Issues Found — fix and re-invoke

Not checked: live external claims (TypeSafe `jev-latest` response-model prefix, Zen 429/400 semantics, `opencode`/`cursor-agent` model ids) — established by the plans' own live research, not re-verifiable from the codebase; and no tests were executed. No CRITICAL/HIGH findings: both plans are executable by a zero-context engineer, with exact code, commands, and accurate file/line grounding throughout.

