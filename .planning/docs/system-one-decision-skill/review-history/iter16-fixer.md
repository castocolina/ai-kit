## Fix Summary: /var/home/bazzite/git/llm-env/docs/superpowers/plans/2026-10-10-system-one-provisioning.md

### Document
/var/home/bazzite/git/llm-env/docs/superpowers/plans/2026-10-10-system-one-provisioning.md

### Findings addressed
- **Task 2 help line breaks an existing vulkan-only help test** — Severity: CRITICAL. Status: addressed. Edit: Help text is now "Build the local System One (Laya) GPU image", which contains no "rocm". Section: Task 2 Step 3, `scripts/help.sh`.
- **Task 8's always-on System One SKIP block breaks the concise default output test** — Severity: CRITICAL. Status: addressed. Edit: The disabled branch is the one-line form (`log_warn` only), so a default run prints no Identity:/Command:/Expectation: blocks and `test_check_setup_prints_concise_pass_rows_by_default` stays green. Section: Task 8 Step 3.
- **Task 8 check-server test crashes in the fixture** — Severity: HIGH. Status: addressed. Edit: `test_check_server_system_one_passes_when_stubbed` passes `{"gemma4": "ok", "ornith": "ok"}` to `run_check_server`. Section: Task 8 Step 1.
- **system_one-only setup drops measured VRAM fields** — Severity: HIGH. Status: addressed. Edit: After Step 2, setup persists `gpu.vram_total_mib` and `gpu.vram_budget_ceiling_mib` (the same values Step 6 writes at `setup/setup.sh:170-177`), and the System-One-only test asserts `("16304", "15489")`. Section: Task 6 Step 3 and Step 1.
- **Task 3 import edit fails ruff isort** — Severity: MEDIUM. Status: addressed. Edit: The `llmenv.py:48` import is the ruff-formatted parenthesized form. Section: Task 3 Step 3.
- **`rocr_visible_index` can raise StopIteration** — Severity: MEDIUM. Status: addressed. Edit: A missing `drm_render_minor` uses `next(..., None)` and raises `ValueError`; one test covers that node. Section: Task 3 Steps 1 and 3.

### Findings escalated
- None.

### Findings skipped (with disagreement noted)
- None.

### Findings not yet addressed
- None.

### Status: Edits Applied

## Fix Summary: /var/home/bazzite/git/llm-env/docs/superpowers/plans/2026-10-10-system-one-decision-skill.md

### Document
/var/home/bazzite/git/llm-env/docs/superpowers/plans/2026-10-10-system-one-decision-skill.md

### Findings addressed
- **Task 8 LIVE check 6 accuracy reference is ambiguous** — Severity: MEDIUM. Status: addressed. Edit: Check 6 gates on `accuracy_when_not_fallback` >= 0.95 with Task 7's minimum count `n * (1 - fallback_rate)` >= max(10, ceil(0.3 * n)). Section: Task 8 Step 3 LIVE prompt, check 6.
- **Task 8 LIVE check 6 gates on ambiguous “accuracy”** — Severity: CRITICAL. Status: addressed. Edit: Same check-6 sentence; the >= 0.95 gate is `accuracy_when_not_fallback`, with Task 7's minimum count. Section: Task 8 Step 3 LIVE prompt, check 6.

### Findings escalated
- None.

### Findings skipped (with disagreement noted)
- None.

### Findings not yet addressed
- None.

### Status: Edits Applied

Plan A grew by 14 lines (1673 → 1687). Plan B stayed 1582 lines. Task 8 lanes and the 32-case corpus were left as written.

Did not re-run the suite or open the Laya image; those were not in this report. The ceiling `15489` is `round(16304 * 95 / 100)` from the setup stub’s detect payload — if Step 2 is pasted short of the ceiling math, that yq line has nothing to write.
