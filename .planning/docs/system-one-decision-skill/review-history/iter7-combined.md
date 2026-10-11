## Reviewer cursor-sol
### Document Type
Superpowers · plan (both documents)

### HIGH
- **`screen()` implementation is incomplete and internally unordered** — Location: decision-skill plan, Tasks 3–4, lines 605–1007. Required: provide the complete `screen()` flow, including stdin parsing, kill-switch handling, provenance initialization, candidate selection, dispatch, hashing, and error returns; initialize `provenance` before its first use at line 909. Why: the supplied fragments cannot satisfy the Task 3 tests without inventing substantial order-sensitive code and currently reference `provenance` before any defined initialization.
- **Calibration corpus is not reproducible** — Location: decision-skill plan, Task 5, lines 1024–1048. Required: specify all 32 JSONL cases or provide a deterministic generator producing their exact text and labels. Why: the implementer must invent 26 cases whose contents directly determine measured accuracy and the production fallback threshold.

### MEDIUM
- **RAM-budget test is omitted from its commit** — Location: provisioning plan, Task 4, lines 575–588. Required: include the selected budget test file (`tests/test_budget.py` or `tests/test_cli.py`) in Task 4’s commit. Why: Step 3 requires this coverage, but Step 5 leaves it uncommitted.
- **Failed idle-CPU investigation has no rollback** — Location: provisioning plan, Task 8, lines 1163–1222. Required: if no candidate passes, restore `pylib/compose.py` and `tests/test_compose.py` to their pre-investigation state before stopping. Why: the current procedure leaves the final failed experiment in the working tree and can contaminate subsequent work.
- **Resource errors omit the newly reserved service** — Location: provisioning plan, Task 4, lines 552–568. Required: update and test `ResourceError` messages so thresholds that include System One identify its CPU/RAM reservation. Why: the proposed arithmetic increases the floors while existing diagnostics still attribute them only to the host, OmniRoute, remote-setup, and possibly llm-server.
- **Frontmatter example contradicts its required keywords** — Location: decision-skill plan, Task 6, lines 1258–1266. Required: make the example description include `needs_fallback` and consent, or remove it as a copyable example. Why: following the example violates the immediately preceding activation requirements.

### Cross-Document Consistency
- No additional inconsistency was found in the Task 11 dependency, Laya URL, model, or live-gate ordering shared by the plans.

### Status: Issues Found — fix and re-invoke

## Reviewer cursor-glm
### Document Type
superpowers · plan (both documents)

### Files Read
- /var/home/bazzite/git/llm-env/docs/superpowers/plans/2026-10-10-system-one-provisioning.md (1580 lines)
- /var/home/bazzite/git/llm-env/docs/superpowers/plans/2026-10-10-system-one-decision-skill.md (1530 lines)
- Grounding (read, not reviewed): pylib/config.py, pylib/compose.py, pylib/resources.py, pylib/budget.py, pylib/detect.py, llmenv.py, setup/setup.sh, setup/render-unit.sh, scripts/start.sh, scripts/gpu-status.sh, scripts/check-setup.sh, scripts/check-server.sh, scripts/help.sh, tools/lib.sh, models.yml.example, tests/test_shell.py, docker/laya-rocm/Dockerfile, ~/.claude/skills/jev-fast-decision/scripts/jev_review.py, ~/.claude/skills/jev-fast-decision/SKILL.md, ~/.claude/skills/jev-fast-decision/reference.md

### MEDIUM
- **`help.sh` uses `echo` instead of the file's `_help_line` helper** — Location: Plan A, Task 2, Step 3 (`scripts/help.sh` block). Required: the added line must be `_help_line "system-one-build" "Build the local ROCm System One (Laya) image"` to match the existing `printf 'make %-32s%s\n'` convention at [scripts/help.sh:5-7](scripts/help.sh). Why: `echo "make system-one-build Build …"` produces a misaligned entry that breaks the column alignment every other line in the file uses.

- **Task 6 "REPLACE THIS LINE" is not fully self-contained** — Location: Plan A, Task 6, Step 3 (`setup/setup.sh` restructure). Required: give the exact end line (or a unique closing anchor) for the existing Steps 3–7 block the engineer must cut, or inline the replacement body. Why: the plan tells a zero-context engineer to replace `true # REPLACE THIS LINE with the existing Steps 3–7 body` but never states where Step 7 ends; the engineer must grep and guess the boundary in a ~150-line region under `set -e`, where an off-by-one includes or drops a `fi`.

- **Stale line reference for `test_setup_fails_when_the_budget_is_infeasible`** — Location: Plan A, Task 6, Step 1. Required: update the "~line 936" reference to line 855 (actual location). Why: the function exists and is findable by name, but the line number is off by ~80, a minor cross-section inconsistency.

### Cross-Document Consistency
- Both plans agree on the paired-plan gate: Plan A Task 11 leaves `system_one.enabled: true` and a healthy `http://127.0.0.1:8010`; Plan B Tasks 5–8 require it. Plan A Task 11 Step 9 and Plan B's header "Execution order" are mutually consistent. The `system_one.port` default (8010) and `JEV_LAYA_URL` default (`http://127.0.0.1:8010`) match across both. No drift detected.

### Status: Issues Found — fix and re-invoke

What I skipped: I did not run `make validate`/`make test` (plan mode, read-only) and did not verify the external `laya 0.4.2` library's internal API (`DEFAULT_MODELS`, `resolve_revision`, `PINNED_REVISIONS`) — those are research claims, not codebase-grounding claims. Risk: the `LAYA_REVISION=reviewed` pin and `system-one-cache-check.py` imports assume laya 0.4.2 internals that I could not confirm from the codebase; if those names differ, Tasks 6/7 prefetch/verify will fail at runtime, not at plan time.

## Reviewer cursor-gemini
### Document Type
superpowers · plan
### HIGH
- **Wrong task checkbox format and non-actionable steps** — Location: `docs/superpowers/plans/2026-10-10-system-one-decision-skill.md` (Tasks 1, 6). Required: Format all checkboxes exactly as `- [ ] **Step N: ...**` (e.g., `- [ ] **Step 1: Do something**`), and remove non-step checkboxes like `N/A` or `writing-skills RED`. Why: The superpowers framework enforces a strict `task_checkbox_format` for plan tasks; deviations and non-actionable checklist items (which are just notes) violate this syntax and the requirement for actionable steps.
### Status: Issues Found — fix and re-invoke

