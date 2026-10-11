## Review: docs/superpowers/plans/2026-10-10-system-one-provisioning.md, docs/superpowers/plans/2026-10-10-system-one-decision-skill.md
### Document Type
superpowers · plan (both documents)
### Files Read
- /var/home/bazzite/git/llm-env/docs/superpowers/plans/2026-10-10-system-one-provisioning.md (1673 lines)
- /var/home/bazzite/git/llm-env/docs/superpowers/plans/2026-10-10-system-one-decision-skill.md (1582 lines)

**How this was checked:** I applied the plan code to scratch copies of the repo and the skill, then ran the real gates there. The baseline repo copy was green: 1244 passed, `make validate` clean.

**Provisioning plan (Plan A):** I applied Tasks 1–9 as written, filling the prose-described helper edits by their text. Result: `tools/validate.sh` passes (shellcheck, ruff, pyright 0 errors), and the suite gives **1284 passed, 3 failed**. The three failures are the CRITICAL/HIGH items below.

**Decision-skill plan (Plan B):** I assembled Tasks 2–5 into `jev_review.py`, `eval_cases.py` and a 32-row `cases.jsonl` that follows the rules. All 41 tests pass. The Task 7 `--calibrate` regex replaces each backend's `min_confidence` exactly once.

**Laya claims:** I checked them against the `laya==0.4.2` wheel and all match: `DEFAULT_MODELS`, `normalise_name`, `resolve_revision`/`PINNED_REVISIONS` SHAs, `Agent.__init__` `allow_patterns`, the alias table, `LAYA_THREADS`/`LAYA_IDLE_UNLOAD_SECONDS`, `/health`, and the uvicorn access log.

### CRITICAL
- **Task 2 help line breaks an existing vulkan-only help test** — Location: Plan A Task 2 Step 3, `scripts/help.sh` line `_help_line "system-one-build" "Build the local ROCm System One (Laya) image"`. Required: `make help` output contains no "rocm" (any case), so `tests/test_shell.py::test_make_help_describes_a_vulkan_only_benchmark` (it asserts `"rocm" not in result.stdout.lower()`) still passes. Why: confirmed failing in the scratch run. Task 2 Step 4's `make test` fails, and so does every later task's gate.
- **Task 8's always-on System One SKIP block breaks the concise default output test** — Location: Plan A Task 8 Step 3. In `check-setup.sh`, the `else record_section_skip "system-one" ...` branch runs on every default run, because System One defaults to off. Required: a default run (llm-server enabled, System One disabled) prints no `Identity:`/`Command:`/`Expectation:` blocks to stdout. Either the disabled branch stays one-line in non-verbose mode, or the plan names `test_check_setup_prints_concise_pass_rows_by_default` (`tests/test_shell.py` ~4385) and states its new expectation. Why: confirmed failing. `record_section_skip` always prints `Identity: system-one` / `Command: not run: system-one is disabled` to stdout, and that test asserts `"Identity:" not in result.stdout`.
### HIGH
- **Task 8 check-server test crashes in the fixture** — Location: Plan A Task 8 Step 1, `test_check_server_system_one_passes_when_stubbed` calls `run_check_server(tmp_path, {"gemma4": "ok"}, ...)`. Required: the call supplies a completion body for every key the helper reads, so the test reaches the System One assertions. Why: `run_check_server` reads `completion_body["ornith"]` unconditionally (`tests/test_shell.py` ~6957), which raises `KeyError: 'ornith'`. The RED test can never go GREEN as written. With `{"gemma4": "ok", "ornith": "ok"}` it passes against the plan's `check-server.sh` code (verified).
### MEDIUM
- **Task 3 import edit fails ruff isort** — Location: Plan A Task 3, "add rocr_visible_index to the existing import (line 48)". Required: the extended `from pylib.detect import ...` is wrapped the way ruff formats it. Why: putting the name on the existing single line exceeds the line length, so `make validate` fails with I001 until `ruff check --fix` runs. Tooling catches it, but it stops the first `make validate`.
- **Task 8 LIVE check 6 accuracy reference is ambiguous** — Location: Plan B Task 8 LIVE prompt, check 6: "Task 7's rule holds: that accuracy >= 0.95". Required: the prompt names the metric explicitly (`accuracy_when_not_fallback`). Why: an external judge that reads it as `accuracy` (all clear cases, including fallback ones) can fail check 6 against the same data. That fails the round and triggers an unneeded FIX loop.
### Cross-Document Consistency
- No contradictions found. Both plans agree on:
  - port 8010
  - container name `system-one`, used by `podman logs system-one`
  - the activation line `GSD_PATH_JEV=1 JEV_BACKEND=laya JEV_LAYA_URL=http://127.0.0.1:<port> GSD_PATH_JEV_TIMEOUT_SECONDS=20`
  - the `/health` probe
  - the `POST /v1/systemone` per-check-delta counting
  - the gate: Plan B Tasks 5–8 need only System One enabled and healthy on 8010; Plan A Task 11 is not a gate
### Status: Issues Found — fix and re-invoke

I did not check the live-only steps (Plan A Tasks 10–11, Plan B Tasks 1, 6 Step 3 and 8). I also did not check the docs prose of Plan A Task 9 beyond `tests/test_docs.py`'s constraints. Scratch copies are under the session scratchpad; nothing in the repo or the skill directory was modified.
