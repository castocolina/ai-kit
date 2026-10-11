## Fix Summary: /var/home/bazzite/git/llm-env/docs/superpowers/plans/2026-10-10-system-one-provisioning.md

### Document
/var/home/bazzite/git/llm-env/docs/superpowers/plans/2026-10-10-system-one-provisioning.md

### Findings addressed
- **`help.sh` uses `echo` instead of the file's `_help_line` helper** — Severity: MEDIUM. Status: addressed. Edit: The new help entry is `_help_line "system-one-build" "Build the local ROCm System One (Laya) image"`. Section: Task 2, Step 3.
- **Task 6 "REPLACE THIS LINE" is not fully self-contained** — Severity: MEDIUM. Status: addressed. Edit: The Steps 3–7 paste is `setup/setup.sh` lines 103–208, ending at the `fi` that closes `if llmenv … budget`, and not the outer `else` at line 210. Section: Task 6, Step 3.
- **Stale line reference for `test_setup_fails_when_the_budget_is_infeasible`** — Severity: MEDIUM. Status: addressed. Edit: The reference is `tests/test_shell.py:855`. `run_setup_no_gpu` is cited at line 682. Section: Task 6, Step 1.
- **RAM-budget test is omitted from its commit** — Severity: MEDIUM. Status: addressed. Edit: Task 4’s commit includes `tests/test_cli.py`, where the `cmd_budget` `ram_available_mib` comparison lives. Section: Task 4, Steps 3 and 5.
- **Resource errors omit the newly reserved service** — Severity: MEDIUM. Status: addressed. Edit: `_floor_words()` is used in all four `ResourceError` strings, and a test requires `System One's reservation (2 CPUs, 4608 MiB)` on each branch. Section: Task 4, Steps 1 and 3.
- **Failed idle-CPU investigation has no rollback** — Severity: MEDIUM. Status: addressed. Edit: If no row passes, `git checkout -- pylib/compose.py tests/test_compose.py` runs before the report and the stop. Section: Task 8 acceptance.

### Findings escalated
None.

### Findings skipped (with disagreement noted)
None in this document.

### Findings not yet addressed
None.

### Status: Edits Applied

## Fix Summary: /var/home/bazzite/git/llm-env/docs/superpowers/plans/2026-10-10-system-one-decision-skill.md

### Document
/var/home/bazzite/git/llm-env/docs/superpowers/plans/2026-10-10-system-one-decision-skill.md

### Findings addressed
- **`screen()` implementation is incomplete and internally unordered** — Severity: HIGH. Status: addressed. Edit: Task 3 now has the only `screen()`: stdin parse, kill switch, timeout, `invalid_input`, provenance init, then candidate selection, dispatch, hashing, and every error return. Task 4 points at that function and does not paste a second copy. Section: Task 3 Step 3 and Task 4 Step 3.
- **Wrong task checkbox format and non-actionable steps** — Severity: HIGH. Status: addressed. Edit: Every checkbox is `- [ ] **Step N: ...**`. The `writing-skills RED` and `N/A` checkboxes are gone; flowchart and git-commit skips are one sentence in the Task 6 content rules. Section: Tasks 0–8.
- **Frontmatter example contradicts its required keywords** — Severity: MEDIUM. Status: addressed. Edit: The copyable example is removed. The description must include Laya, TypeSafe, OpenCode Zen, `needs_fallback`, and consent. Section: Task 6 content requirements.

### Findings escalated
None.

### Findings skipped (with disagreement noted)
- **Calibration corpus is not reproducible** — Severity: HIGH. Reason: Owner ruling rejected “specify all 32 JSONL cases / deterministic generator” again. Composition rules, six exemplars, and the Step 1 authoring step stay. NOT addressed in this pass.

### Findings not yet addressed
None.

### Status: Edits Applied

Laya 0.4.2 pins in the prefetch comment were checked against the local image; the plans were not executed. Risk: `screen()` and the `ResourceError` floors are unrun, so a mismatch with `jev_review.py`’s timeout or input handling shows up only when Task 3’s tests run.
