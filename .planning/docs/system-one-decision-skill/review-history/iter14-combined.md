## Reviewer opus
### Document Type
superpowers · plan (both documents)
### Files Read
- /var/home/bazzite/git/llm-env/docs/superpowers/plans/2026-10-10-system-one-provisioning.md (1665 lines)
- /var/home/bazzite/git/llm-env/docs/superpowers/plans/2026-10-10-system-one-decision-skill.md (1581 lines)
### CRITICAL
- **Task 4 `test_cmd_budget_system_one_lowers_ram_available_mib` cannot pass with the specified implementation** — Location: Plan A Task 4, the `test_cmd_budget_…` block (~line 615) and Step 3 "Right after the floors are computed, add System One". Required: the test fixture (or the implementation) must make System One change `ram_available_mib`. One option is to set `cfg["resources"]["llm_server"]["memory_ceiling_pct"] = 100`, so the remainder is what limits the budget. The other is to say explicitly that the reservation also lowers the percentage ceiling. Why: `write_test_config` (tests/test_cli.py:28) has no `resources`, so `cmd_budget` uses the default `memory_ceiling_pct` 46 (llmenv.py:285). On a 32768 MiB host that ceiling is 15073 MiB. The remainder is 27616 MiB without System One and 23008 MiB with it, so `min(remainder, 15073)` is 15073 both times (pylib/resources.py:109-115). `assert … < off` therefore fails, and the plan's code can't make it pass without a design decision the plan doesn't make: should System One shrink llm-server RAM when the percentage ceiling is the limit?
### HIGH
- **Plan test code fails `make validate`, which each step expects to PASS** — Location: Plan A Task 5 Step 1, Task 4 cmd_budget test, Task 6 Step 1, Task 8 Step 1, Task 1 Step 1. Required: each snippet passes the repo's ruff 0.16.2 and pyright (basic). I checked with `ruff check --stdin-filename tests/…` and `uv run pyright`. Why, per snippet:
  - Task 5 `kwargs = dict(...)`: ruff → C408. pyright → 9 `reportArgumentType` errors on `compute_budget(**kwargs)`, because the `int | list` union is checked against every parameter.
  - Task 4 `import llmenv; cfg = …`: ruff → I001.
  - Unused `result` (ruff → RUF059) in `test_setup_prefetches_system_one_weights_when_enabled`, `test_setup_skips_system_one_build_and_prefetch_when_disabled` and `test_check_setup_checks_system_one_weights_cache_when_enabled`.
  - Task 1's header line `from pylib.config import migrate_config, validate_config` repeats tests/test_config.py:11-21: ruff → F811.
- **Task 3 tells the executor to call `render_compose.add_argument` before `render_compose` exists** — Location: Plan A Task 3 Step 3, the llmenv block line `rocr = sub.add_parser("rocr-index"); …; render_compose.add_argument("--system-one-rocr-index", default="")  # build_parser, after detect`. Required: put the `--system-one-rocr-index` argument after the `render-compose` parser is defined (llmenv.py:603-610). Keep it separate from the `rocr-index` parser, which goes after `detect` (llmenv.py:539). Why: `render_compose` is a local that `build_parser` assigns at line 603. Pasting this line after `detect`, as the comment says, raises UnboundLocalError in `build_parser()`, which breaks every `llmenv` invocation.
- **Task 7 fixture `gpu.pci_address` must be quoted** — Location: Plan A Task 7 preamble ("When `system_one_enabled`, set written `gpu.pci_address` to `0000:03:00.0`"). Required: the fixture writes `pci_address: '0000:03:00.0'` (quoted). Why: PyYAML reads the unquoted value as the base-60 float `180.0` (verified). `run_lifecycle_script` runs the real `migrate-config` through `REAL_UV` (tests/test_shell.py:4615), and that rewrites the file. render-unit's `yq -r '.gpu.pci_address'` then returns `180.0`, the detect select comes back empty, and Task 3's `die "…has no render node"` fires. That breaks `test_start_waits_for_system_one_health_when_image_present` (expects rc 0) and `test_start_exits_when_system_one_health_never_succeeds` (expects the health-timeout message).
### MEDIUM
- **Task 3 code block mixes two files with no labels** — Location: Plan A Task 3 Step 3, the block that starts `from pylib.detect import …`. Required: label which lines go in llmenv.py and which in pylib/compose.py. Why: `def write_compose(…)` lives in pylib/compose.py:255, but the block reads as llmenv.py content.
- **`rocr-index` failure gives a traceback, not an error message** — Location: Plan A Task 3, `cmd_rocr_index`. Required: when no KFD node matches, `rocr-index` reports a clean `fail(...)` error. Why: `rocr_visible_index` raises ValueError. `main()` catches only ConfigError, BudgetError, GgufError, DetectError, ResourceError, OmniRouteError and OSError (llmenv.py:668-673), so render-unit and check-setup get a Python traceback.
- **`--calibrate` failure is hidden by `tee`** — Location: Plan B Task 7 Step 4 bash block. Required: the block runs under `set -euo pipefail`, or checks `PIPESTATUS`, so a nonzero `--calibrate` stops it. Why: `eval_cases.py --calibrate | tee notes/calibration.json` returns tee's status. The step's claim that "`--calibrate` exits nonzero unless re.subn count is 1" therefore stops nothing, and the verifier and pytest still run.
### Cross-Document Consistency
- No contradictions found. Both plans agree on port 8010, the activation line `GSD_PATH_JEV=1 JEV_BACKEND=laya JEV_LAYA_URL=http://127.0.0.1:<port> GSD_PATH_JEV_TIMEOUT_SECONDS=20`, the Task 11 gate on decision-skill Tasks 5–8, and counting `POST /v1/systemone` as per-check deltas.
### Status: Issues Found — fix and re-invoke

## Reviewer cursor-auto
### Document Type
Superpowers · plan (both)
### Files Read
- /var/home/bazzite/git/llm-env/docs/superpowers/plans/2026-10-10-system-one-provisioning.md (1665 lines)
- /var/home/bazzite/git/llm-env/docs/superpowers/plans/2026-10-10-system-one-decision-skill.md (1581 lines)
- /home/bazzite/.claude/skills/ai-kit-spec-review-checklist/references/frameworks/superpowers.md (framework profile)
- /home/bazzite/.claude/skills/jev-fast-decision/scripts/jev_review.py (305 lines)
- /home/bazzite/.claude/skills/jev-fast-decision/SKILL.md (139 lines)
- /home/bazzite/.claude/skills/jev-fast-decision/reference.md (126 lines)
- /home/bazzite/.claude/skills/skill-judge/SKILL.md (752 lines)
- /var/home/bazzite/git/llm-env/pylib/config.py, compose.py, detect.py, resources.py, budget.py, llmenv.py, setup/setup.sh, setup/render-unit.sh, scripts/{start,check-setup,check-server,gpu-status,clean}.sh, tools/lib.sh, docker/laya-rocm/Dockerfile, models.yml.example, tests/test_{shell,compose,detect}.py (grounding slices)
### CRITICAL
### HIGH
- **Plan B live unlock ignores Task 11 idle-CPU failure** — Location: decision-skill Execution order (L5); Task 5 Step 4; Task 6 preamble; Task 8 Step 1 (L1417). Required: a concrete preflight before Task 5 live / Task 6 / Task 8 that fails when provisioning Task 11 did not pin a winning idle-CPU env (e.g. compose `system-one.environment` lacks a table var, or Task 11 aborted without commit)—not only `curl …/health` or `system_one.enabled`. Why: Plan A states healthy-on-8010 with no winning row must not unlock Plan B Tasks 5–8; Plan B restates that requirement in prose but Step 1 only checks health, which Task 10 already leaves true after a Task 11 abort.
### MEDIUM
- **Task 3 compose assembly paste omits the return** — Location: provisioning Task 3 Step 3 volumes assembly (L473–479). Required: after building `document`, still `return HEADER_COMMENT + yaml.safe_dump(...)` as in current `render_compose`. Why: the snippet ends at `document = {...}`; a literal replace drops the return and breaks every compose caller.
- **Task 1 validate_config line anchor is wrong** — Location: provisioning Task 1 Files (L53). Required: point at the end of the `llm_server` validate block (~393), not ~383. Why: line 383 is the start of that block; “after the llm_server block” prose is right, the line number is not.
### Cross-Document Consistency
- Unlock contract: Plan A (paired-plan banner) forbids starting decision-skill Tasks 5–8 without Task 11’s idle-CPU pin + 8010 re-verify; Plan B’s executable gates only enforce health/port—same defect as the HIGH finding (Plan B side).
- Port 8010, print-endpoints activation line, Laya URL default, and Task 10→11→Plan B sequencing otherwise agree; skill-judge D1–D8 maxima match `/home/bazzite/.claude/skills/skill-judge/SKILL.md`; `jev_review.py` line anchors (API_URL/MODEL/MIN_CONFIDENCE) match disk.
### Status: Issues Found — fix and re-invoke

Skipped: no TOOL_AVAILABILITY (no legacy-tool flags); did not re-run live Laya/Zen. Risk: executor can start Plan B live work after Task 11 aborts with no idle-CPU pin.

