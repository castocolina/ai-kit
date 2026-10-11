## Fix Summary: /var/home/bazzite/git/llm-env/docs/superpowers/plans/2026-10-10-system-one-provisioning.md

### Document
/var/home/bazzite/git/llm-env/docs/superpowers/plans/2026-10-10-system-one-provisioning.md

### Findings addressed
- **Idle-CPU task requires a service that has not been provisioned** — Severity: CRITICAL. Status: addressed. Edit: Moved the idle-CPU investigation to Task 11, after live E2E (now Task 10); check-setup is Task 8 and clean/docs is Task 9. Task 11 starts from Task 10’s running container, and its last step re-verifies health on port 8010. Section: Tasks 8–11 and the execution-order paragraph.
- **Single-render-node ROCm passthrough is implemented before it is verified** — Severity: HIGH. Status: addressed. Edit: Recorded the 2026-10-11 live result (a lone `renderD128` device yields torch “No CUDA GPUs are available”) and replaced the pin with `/dev/kfd` plus `/dev/dri:/dev/dri` and `ROCR_VISIBLE_DEVICES` from `rocr_visible_index` (fake sysfs test; this host renderD128 → 0, renderD129 → 1). check-setup compares that index, not a single render-node device. Section: measured facts, Task 3, Task 8 check-setup, Task 9 docs.
- **GPU status can classify System One as an external offender** — Severity: MEDIUM. Status: addressed. Edit: `processes_on_render_node` gains `cmdline`; the offender filter drops a cmdline containing `laya-serve`, and a System-One-only test asserts no “Move these” prompt. Section: Task 7.
- **Provisioning’s final restart erases the POST log required by the decision-skill precondition** — Severity: cross-document. Status: addressed. Edit: Task 10’s final restart no longer claims its access log survives; Task 11’s last step sends one fresh decision POST after the winning restart and requires a new `POST /v1/systemone` line. Section: Task 10 Step 8, Task 11 Step 7.

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
- **Task 4 cannot produce its prescribed RED result** — Severity: CRITICAL. Status: addressed. Edit: Task 4’s tests are regression tests expected to pass against Task 3’s `screen()`; a failure means fix `screen()`. Section: Task 4 Steps 1–2.
- **Task 7 omits the mandatory RED phase** — Severity: HIGH. Status: addressed. Edit: Step 2 writes the calibration and override tests, runs them, and records the expected `calibrate` failure before Step 3 implements `calibrate()` and the `--calibrate` rewrite. Section: Task 7 Steps 2–5.
- **Explicit remote consent lacks the positive result-handling branch** — Severity: MEDIUM. Status: addressed. Edit: `backend_unavailable:<name>:consent_required_for_remote` on an explicit-backend run uses the same ask-consent-and-retry recipe as top-level `consent_required_for_remote`. Section: Task 6, Pick the backend and Read the result.
- **Provisioning’s final restart erases the POST log required by the decision-skill precondition** — Severity: cross-document. Status: addressed. Edit: Tasks 5–8 wait for provisioning Task 11 (idle-CPU fix done, health re-verified on 8010). Live POST counts are per-check deltas only; an empty log before a check is not a failure. Section: execution order, Tasks 6 and 8.

### Findings escalated
None.

### Findings skipped (with disagreement noted)
None.

### Findings not yet addressed
None.

### Status: Edits Applied

Did not re-inspect the Laya image: this report had no prefetch-placeholder finding, and the cache-check script in the plan was already concrete. Line growth is about +15 on the provisioning plan and 0 on the decision-skill plan against the pre-edit files.
