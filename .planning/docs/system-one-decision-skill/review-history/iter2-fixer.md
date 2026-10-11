## Fix Summary: /var/home/bazzite/git/llm-env/docs/superpowers/plans/2026-10-10-system-one-provisioning.md

### Document
/var/home/bazzite/git/llm-env/docs/superpowers/plans/2026-10-10-system-one-provisioning.md

### Findings addressed
- **Decision plan assumes unavailable Git history** — Severity: CRITICAL. Status: addressed (paired decision plan; no provisioning text referenced git recovery). Edit: N/A in this file. Section: (cross-doc).
- **Configured GPU is not proven ROCm-capable** — Severity: HIGH. Status: addressed. Edit: Added `vendor` to `list_gpus`, AMD `0x1002` + render-node checks after GPU selection in Task 6, and matching `check-setup` probes plus hybrid render-node failure test in Task 9. Section: Task 6 Step 3, Task 9.
- **Incomplete cache can pass startup validation** — Severity: HIGH. Status: addressed. Edit: Introduced `scripts/system-one-cache-check.py` with shared `ALLOW_SUFFIXES` manifest; setup prefetch, `start` verify, and `check-setup` all call `prefetch`/`verify`. Section: Task 6–7, Task 9.
- **Task 1's duplicate-models test cannot pass** — Severity: HIGH. Status: addressed. Edit: Assertion now expects `"more than once"` to match `validate_config` message. Section: Task 1 Step 1.
- **Baseline repetition count is contradictory** — Severity: MEDIUM. Status: addressed (in decision plan). Section: (cross-doc).
- **VRAM gate does not calculate aggregate usage** — Severity: MEDIUM. Status: addressed. Edit: Task 11 uses deduplicated DRM VRAM summation script vs `vram_reserve_mib`. Section: Task 11.
- **Live Laya dependency has no declared execution order** — Severity: Cross-document. Status: addressed. Edit: Header **Execution order** paragraph. Section: top of plan.

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
- **Decision plan assumes unavailable Git history** / **Skill directory has no git history** — Severity: CRITICAL. Status: addressed. Edit: Task 0 copies current on-disk skill to `/tmp/claude-1000/jev-current-skill-snapshot`; removed git/zen-only recovery; Task 1 is 25 no-skill + 25 current-skill runs. Section: Task 0–1.
- **Probe failures disappear from backend reports** — Severity: HIGH. Status: addressed. Edit: `screen()` always includes `unavailable`; new test for Laya unreachable + TypeSafe 429; Review Focus 2 updated. Section: Task 4, Review Focus.
- **Laya test stub violates the response contract** — Severity: HIGH. Status: addressed. Edit: `LayaStub` normalizes choice probabilities for any option count; score answers include `legend` and `probabilities`. Section: Task 2 Step 1.
- **Per-backend confidence selection lacks an executable contract** — Severity: HIGH. Status: addressed. Edit: `BACKENDS[*].min_confidence`, `_parse_jev_min_confidence` / `min_confidence_for`, `invalid_min_confidence` path, and tests. Section: Global Constraints, Task 2 Step 3, Task 4.
- **TypeSafe model string contradicts itself** — Severity: MEDIUM. Status: addressed. Edit: Removed `jev-1.13.0` comment; `jev-latest` request; `backends/typesafe.md` notes unverified returned model; stub uses `jev-latest`. Section: Task 2, Task 6.
- **`clean_env` leaves `JEV_MIN_CONFIDENCE` un-isolated** — Severity: MEDIUM. Status: addressed. Edit: `clean_env` clears `JEV_MIN_CONFIDENCE` and legacy `JEV_API_*`. Section: Task 2.
- **Baseline repetition count** — Severity: MEDIUM. Status: addressed. Edit: 25 + 25 runs documented. Section: Task 1.
- **Live Laya dependency has no declared execution order** — Severity: Cross-document. Status: addressed. Edit: Header **Execution order**; Task 5 live note. Section: top, Task 5.

### Findings escalated
(none)

### Findings skipped (with disagreement noted)
(none)

### Findings not yet addressed
(none)

### Status: Edits Applied

---

Skipped: live run of `check-setup` `bad()` helper naming and whether `run_check_setup_with_stubs` can simulate missing `/dev/dri/renderD999` without root-only device nodes — plan assumes the render-node readability check is enough for the new test.

Risk: `check-setup.sh` snippet mixes `llmenv` and `uv run llmenv.py detect` in `record_command` display vs execution; implementers should match existing `check-setup` conventions so recorded commands match what actually runs.
