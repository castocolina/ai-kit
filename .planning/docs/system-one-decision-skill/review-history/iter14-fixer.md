## Fix Summary: /var/home/bazzite/git/llm-env/docs/superpowers/plans/2026-10-10-system-one-provisioning.md

### Document
/var/home/bazzite/git/llm-env/docs/superpowers/plans/2026-10-10-system-one-provisioning.md

### Findings addressed
- **Plan A's `valid_cfg` fixture instruction rests on a wrong claim about the existing tests** — Severity: CRITICAL. Status: addressed. Edit: Replaced the `models.yml.example` sentence with a `valid_cfg` fixture that returns `make_cfg(system_one={...})`. Section: Task 1, Step 1.
- **The `_print_endpoints` test helper fails before it runs anything** — Severity: HIGH. Status: addressed. Edit: `commands.mkdir()` is now `commands.mkdir(parents=True)`. Section: Task 7, Step 1.
- **The `make clean` test cannot pass through `run_lifecycle_script`** — Severity: HIGH. Status: addressed. Edit: The clean test passes `llm_server_enabled=False` so the systemctl stub's `daemon-reload` arm does not exit 66 before `podman rmi` and `podman volume rm`. Section: Task 9, Step 1.
- **The placement of the new `tools/lib.sh` constant is ambiguous** — Severity: MEDIUM. Status: addressed. Edit: The constant is inserted after the validation at `tools/lib.sh:231-232`, after `die` exists. Section: Task 7, Step 3.
- **The `run_lifecycle_script` changes in Task 7 are not stated as an exact diff** — Severity: MEDIUM. Status: addressed. Edit: Listed only the new podman, uv, and curl arms; `gpu.pci_address` changes only when `system_one_enabled` is set, and `gpu.backend` stays `cpu`. Section: Task 7, paragraph before Step 1.
- **Some code is described in prose instead of given exactly** — Severity: MEDIUM. Status: addressed. Edit: Replaced the Task 3 `rocr-index` / `write_compose` / `cmd_render_compose` prose, the Task 4 `test_cli.py` sentence, and the Task 8 `run_check_server` sentence with exact code, including the appendix JSON on `*/v1/systemone` and `HEALTH_BODY` on `*/health`. Section: Task 3 Step 3, Task 4 Step 3, Task 8 Step 1.
- **System One ROCR check validates a compose file setup never renders** — Severity: HIGH. Status: addressed. Edit: If `COMPOSE_FILE` is missing, check-setup records SKIP `compose not rendered yet (run make start)`; if it exists, it still compares `ROCR_VISIBLE_DEVICES` to the index from config. Section: Task 8, Step 3.
- **Paired gate understated on idle-CPU failure** — Severity: MEDIUM. Status: addressed. Edit: Decision-skill Tasks 5–8 start only after Task 11 pinned a winning idle-CPU env and finished Step 7's health re-verify. Section: Execution order.
- **Plan A's header refers to Plan B's tasks without saying so** — Severity: cross-document. Status: addressed. Edit: The header now says decision-skill Task 6 copies decision-skill Task 5's `notes/eval-results.json`. Section: Execution order.

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
- **Task 2 implement paste omits `import urllib.parse`** — Severity: HIGH. Status: addressed. Edit: The pasted change adds `import urllib.parse`. Section: Task 2, Step 3.
- **The old `MIN_CONFIDENCE` constant breaks the invalid-threshold test** — Severity: HIGH. Status: addressed. Edit: Step 3 deletes `MIN_CONFIDENCE` and its comments so import with `JEV_MIN_CONFIDENCE=not-a-number` succeeds; Task 4 Step 2 says an import `ValueError` is that leftover, not a `screen()` bug. Section: Task 2 Step 3 and Task 4 Step 2.
- **The `runpy` eval tests always fail on `SystemExit`** — Severity: HIGH. Status: addressed. Edit: Both eval tests call `_eval().main()` and assert it returns 0. Section: Task 5, Step 2.
- **The Task 8 round loop does not define `R` and depends on shell state the harness does not keep** — Severity: MEDIUM. Status: addressed. Edit: Each round is one Bash script that sets `R`, `PROMPT`, and `LIVE` itself; lanes stay owner-filled placeholders. Section: Task 8, Steps 2–3.

### Findings escalated
None.

### Findings skipped (with disagreement noted)
None.

### Findings not yet addressed
None.

### Status: Edits Applied

Line counts: provisioning 1640 → 1665 (+25); decision-skill 1586 → 1581. Did not run the Laya container or the test suite. The `write_compose` and `cmd_render_compose` snippets share one fence and must be pasted into those two functions, not as one body.
