## Fix Summary: /var/home/bazzite/git/llm-env/docs/superpowers/plans/2026-10-10-system-one-provisioning.md

### Document
/var/home/bazzite/git/llm-env/docs/superpowers/plans/2026-10-10-system-one-provisioning.md

### Findings addressed
- **The Task 4 test import block fails `make validate` if pasted as written** — Severity: HIGH. Status: addressed. Edit: Removed the duplicate `from pylib.resources import (...)` and told the step to add only `SYSTEM_ONE_CPUS` and `SYSTEM_ONE_MEMORY_MIB` to the existing import, after `ResourceError`. Section: Task 4 Step 1.
- **A failed `rocr-index` makes `make start` stop with no message** — Severity: MEDIUM. Status: addressed. Edit: `cmd_rocr_index` now catches `ValueError` and `OSError` and prints the message to stderr; `render-unit.sh` dies with `System One: cannot map ${render} to a ROCm device; see message above` when the substitution fails. Section: Task 3 Step 3.
- **Wrong claim about how setup prompts behave at end of input** — Severity: MEDIUM. Status: addressed. Edit: The Input parenthetical now says that at EOF `ask` returns its default, verified by running `setup.sh` with empty stdin. Section: Task 6 Step 1.
- **Task 3 compose assembly snippet is easy to mis-paste** — Severity: MEDIUM. Status: addressed. Edit: The services/volumes lead-in now says the snippet is added after the existing llm-server / omniroute / remote-setup population, not a replacement of that block. Section: Task 3 Step 3.

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
- **Unknown `JEV_BACKEND` reason string disagrees with Interfaces** — Severity: CRITICAL. Status: addressed. Edit: Interfaces, `main()` `--probe`, and `screen()` now use `backend_unavailable:<name>:<probe reason>` for every explicit unusable choice, including an unknown name (`backend_unavailable:zen:unknown_backend`). Added `test_unknown_backend_reason_names_the_choice` for probe and screen. Section: Task 2 Interfaces, Task 2 `main()`, Task 3 `screen()` and Step 1.
- **LIVE 4 assumes something nothing records** — Severity: MEDIUM. Status: addressed. Edit: Task 5 stores the first alone-`vague` top probability as `vague_alone_top` in `notes/eval-results.json`. Task 8 stops before round 1 when that value is not below the calibrated Laya `min_confidence`, with the message that this is a calibration problem, not a skill failure. Section: Task 5 Step 4, Task 8 Step 3, LIVE 4.
- **LIVE check 4 assumes vague top stays below calibrated T** — Severity: MEDIUM. Status: addressed. Edit: Same change as the LIVE 4 finding above. Section: Task 5 Step 4, Task 8 Step 3, LIVE 4.

### Findings escalated
None.

### Findings skipped (with disagreement noted)
None.

### Findings not yet addressed
None.

### Status: Edits Applied

Skipped a scratch re-apply of either plan. Risk: the round-1 gate reads `notes/calibration.json` and treats a null Laya winner as `0.7`; a non-JSON stdout from `--calibrate` would stop the round before any lane runs.
