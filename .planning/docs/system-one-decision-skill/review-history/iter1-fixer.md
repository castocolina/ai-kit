## Fix Summary: /var/home/bazzite/git/llm-env/docs/superpowers/plans/2026-10-10-system-one-provisioning.md

### Document
/var/home/bazzite/git/llm-env/docs/superpowers/plans/2026-10-10-system-one-provisioning.md

### Findings addressed
- **Undefined resource-floor constant / `MEMORY_FLOOR_MIB` referenced but never defined** — Severity: CRITICAL. Status: addressed. Edit: Task 4 test imports `HOST_MEMORY_FLOOR_MIB` + OmniRoute/remote-setup mins, asserts exact `llm_server` shrinkage, drops `MEMORY_FLOOR_MIB`. Section: Task 4 Step 1.
- **Start does not detect missing weights** — Severity: CRITICAL. Status: addressed. Edit: Task 7 adds volume + `local_files_only` weight checks before start, new tests for missing/incomplete cache. Section: Task 7 Steps 1 and 3; Review Focus 1.
- **Weight provisioning remains placeholder code** — Severity: HIGH. Status: addressed. Edit: Task 6/9 replace placeholders with `LAYA_REVISION=reviewed` + `snapshot_download` using `DEFAULT_MODELS`/`resolve_revision` (laya 0.4.2). Section: Task 6 Step 3, Task 9 Step 3.
- **RAM feasibility ignores System One reservation** — Severity: HIGH. Status: addressed. Edit: Task 4 Step 3 threads `system_one_enabled` through both `cmd_budget` `compute_resource_limits` calls + test note. Section: Task 4 Step 3.
- **Model selection accepts arbitrary strings** — Severity: HIGH. Status: addressed. Edit: Task 1 adds `canonical_laya_model_name`, validation, and tests for unknown/empty/duplicate tokens. Section: Task 1.
- **Setup tests call an unspecified helper interface** — Severity: HIGH. Status: addressed. Edit: Task 6 documents `env_overrides`, recording `bash`, podman hooks, detect stub, and three-line stdin. Section: Task 6 Step 1.
- **Task 6 input budget: three prompts, two lines** — Severity: HIGH. Status: addressed. Edit: Same Task 6 harness note (three `\n` when `system_one_env` set). Section: Task 6 Step 1/4.
- **`"scripts/system-one-build.sh" in calls` is unrecordable** — Severity: HIGH. Status: addressed. Edit: Recording `bash` stub + assert on `system-one-build.sh` in `$CALLS`. Section: Task 6 Step 1.
- **Task 7's health-wait test dies inside render-unit.sh** — Severity: HIGH. Status: addressed. Edit: `run_lifecycle_script` extension (detect stub, `gpu.pci_address`, system_one config). Section: Task 7 intro + Step 1.
- **Task 9's check-server test mechanism contradicts harness** — Severity: HIGH. Status: addressed. Edit: Extend `run_check_server` curl stub + `system_one` config; concrete test. Section: Task 9 Step 1.
- **Health-wait test accepts failure** — Severity: MEDIUM. Status: addressed. Edit: Stricter assertions (`returncode == 0`, health poll evidence). Section: Task 7 Step 1.
- **Decision-check fixture uses the wrong answer ID** — Severity: MEDIUM. Status: addressed. Edit: Appendix JSON uses `answers.team`. Section: Appendix.
- **Confirmed legacy tools / Legacy tool usage** — Severity: MEDIUM. Status: addressed. Edit: `fd` and `rg` in Task 8 measure_idle and Task 11 VRAM gate. Section: Tasks 8 and 11.
- **`LLM_ENV_SYSTEM_ONE_HEALTH_TIMEOUT_SECONDS` bypasses validation** — Severity: MEDIUM. Status: addressed. Edit: Positive-integer validation in `tools/lib.sh`. Section: Task 7 Step 3.
- **check-setup's `/dev/kfd` check is host-dependent** — Severity: MEDIUM. Status: addressed. Edit: `LLM_ENV_KFD_PATH` in check-setup + harness note. Section: Task 9 Step 3/1.

### Findings escalated
(none)

### Findings skipped (with disagreement noted)
(none)

### Findings not yet addressed
(none)

### Status: Edits Applied

---

## Fix Summary: /var/home/bazzite/git/llm-env/docs/superpowers/plans/2026-10-10-system-one-decision-skill.md

### Document
/var/home/bazzite/git/llm-env/docs/superpowers/plans/2026-10-10-system-one-decision-skill.md

### Findings addressed
- **The RED baseline already contains the target guidance** — Severity: CRITICAL. Status: addressed. Edit: Task 0/1 require zen-only snapshot + mandatory no-skill control (5 reps); pre-plan skill optional. Section: Tasks 0–1.
- **Explicit-backend error contract is contradicted** — Severity: CRITICAL. Status: addressed. Edit: `screen()` emits `backend_unavailable:typesafe:missing_api_key`; tests in Tasks 2 and 4. Section: Task 4 Step 3, Review Focus 3.
- **Task 8 assumes a nonexistent skill-judge contract** — Severity: CRITICAL. Status: addressed. Edit: Acceptance uses skill-judge D1–D8, 120-point total ≥96, per-dimension floors. Section: Task 8 Step 1.
- **Writing-skills test-count requirements are not met** — Severity: HIGH. Status: addressed. Edit: 5 reps in Tasks 1, 6, 7; no-skill control per writing-skills RED. Section: Tasks 1, 6, 7.
- **The evaluation stub cannot answer the required case mix** — Severity: HIGH. Status: addressed. Edit: `LayaStub` branches on `choice`/`score`/`noul`. Section: Task 2 Step 1.
- **Custom Laya URLs bypass remote-consent rules** — Severity: HIGH. Status: addressed. Edit: `_laya_loopback_ok`, `non_loopback_url` probe, global constraint, test. Section: Global Constraints, Task 2.
- **Threshold calibration can succeed vacuously** — Severity: HIGH. Status: addressed. Edit: Task 7 Step 2 defines candidates, min coverage, tie-break, no-qualifier behavior. Section: Task 7.
- **`BACKENDS["laya"]` has no `url` key** — Severity: MEDIUM. Status: addressed. Edit: Interfaces clarify `url` is remote-only. Section: Task 2 Interfaces.
- **Review Focus #3's promised reason string** — Severity: MEDIUM. Status: addressed. Edit: Aligned Review Focus 3 with composite `reason` + `unavailable` map. Section: Review Focus 3.

### Findings escalated
(none)

### Findings skipped (with disagreement noted)
(none)

### Findings not yet addressed
(none)

### Status: Edits Applied

---

Skipped: full end-to-end run of updated shell tests; zen-only snapshot commit hash is left for the implementer to pick from `jev-fast-decision` git history. Risk: bundled-repo `snapshot_download` + `local_files_only` must match what Laya 0.4.2 actually caches on disk—verify once against a real `make setup` prefetch.
