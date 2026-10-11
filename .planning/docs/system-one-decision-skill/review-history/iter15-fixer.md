## Fix Summary: /var/home/bazzite/git/llm-env/docs/superpowers/plans/2026-10-10-system-one-provisioning.md

### Document
/var/home/bazzite/git/llm-env/docs/superpowers/plans/2026-10-10-system-one-provisioning.md

### Findings addressed
- **Task 4 `test_cmd_budget_system_one_lowers_ram_available_mib` cannot pass with the specified implementation** — Severity: CRITICAL. Status: addressed. Edit: The fixture sets `resources.llm_server.memory_ceiling_pct = 100` before either `cmd_budget` call so the remainder binds, and Step 3 states that the reservation lowers llm-server RAM only when the remainder is the binding limit. Section: Task 4 Step 3.
- **Plan test code fails `make validate`** — Severity: HIGH. Status: addressed. Edit: `compute_budget` is called with explicit keywords; `import llmenv` is on its own line; unused `result` bindings are `_result`; the Task 1 block no longer repeats the existing `pylib.config` import. Section: Task 1 Step 1, Task 4 Step 3, Task 5 Step 1, Task 6 Step 1, Task 8 Step 1.
- **Task 3 tells the executor to call `render_compose.add_argument` before `render_compose` exists** — Severity: HIGH. Status: addressed. Edit: The `rocr-index` parser stays after `detect`; `--system-one-rocr-index` is added only after the render-compose parser (lines 603–610). Section: Task 3 Step 3.
- **Task 7 fixture `gpu.pci_address` must be quoted** — Severity: HIGH. Status: addressed. Edit: The written value is `pci_address: '0000:03:00.0'`. Section: Task 7 preamble.
- **Task 3 code block mixes two files with no labels** — Severity: MEDIUM. Status: addressed. Edit: Comments mark `llmenv.py` versus `pylib/compose.py`, including extending the existing detect import instead of adding a second one. Section: Task 3 Step 3.
- **`rocr-index` failure gives a traceback, not an error message** — Severity: MEDIUM. Status: addressed. Edit: `cmd_rocr_index` catches `ValueError` and returns `fail(str(error))`. Section: Task 3 Step 3.
- **Task 3 compose assembly paste omits the return** — Severity: MEDIUM. Status: addressed. Edit: The volumes assembly still returns `HEADER_COMMENT + yaml.safe_dump(...)`. Section: Task 3 Step 3.
- **Task 1 validate_config line anchor is wrong** — Severity: MEDIUM. Status: addressed. Edit: The Files line points at the end of the `llm_server` validate block, ~line 393. Section: Task 1 Files.
- **Unlock contract (paired-plan banner)** — Severity: HIGH (cross-document, owner-overruled). Status: addressed. Edit: Decision-skill Tasks 5–8 start once System One is enabled and healthy on 8010. Task 11 still reports its own idle-CPU pass/fail and is not that gate. The reviewer’s Required (fail Plan B when no winning idle-CPU row was pinned) was not applied. Section: Execution order.

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
- **Plan B live unlock ignores Task 11 idle-CPU failure** — Severity: HIGH. Status: addressed. Edit: Per the owner ruling, the idle-CPU condition is removed from the execution order and from the Task 5 Step 4, Task 6, and Task 8 preconditions. Those tasks need System One enabled and healthy on 8010. Task 11 still reports its own pass/fail and is not the gate. The reviewer’s Required (a preflight that fails when no winning idle-CPU env was pinned) was not applied. Section: Execution order; Task 5 Step 4; Task 6 preamble; Task 8 preamble and Step 1.
- **`--calibrate` failure is hidden by `tee`** — Severity: MEDIUM. Status: addressed. Edit: The Task 7 Step 4 block starts with `set -euo pipefail`, so a nonzero `--calibrate` stops the pipeline. Section: Task 7 Step 4.
- **Unlock contract** — Severity: cross-document. Status: addressed. Edit: Plan B now matches Plan A: health on 8010 is the gate; idle-CPU is not. Section: Execution order and Task 5/6/8 preconditions.

### Findings escalated
None.

### Findings skipped (with disagreement noted)
None.

### Findings not yet addressed
None.

### Status: Edits Applied

Ruff on each touched snippet joined to its destination module (`ruff check --stdin-filename tests/<file>.py -`) passed. Pyright on the explicit `compute_budget` call, against the planned signature, reported 0 errors. Net growth: provisioning +8 lines (1665→1673), decision skill +1 (1581→1582). Task 8 lanes stay empty placeholders.

Skipped the Laya image, skill-judge, and writing-skills reads; this report did not flag them. Risk: a reviewer that still treats idle-CPU as a Plan B gate will reopen that HIGH, and Task 11 can fail while Plan B starts on a healthy port 8010.
