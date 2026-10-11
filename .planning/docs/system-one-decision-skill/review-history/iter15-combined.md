## Reviewer opus
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

## Reviewer cursor-auto
### Document Type
superpowers · plan (both)
### Files Read
- `/var/home/bazzite/git/llm-env/docs/superpowers/plans/2026-10-10-system-one-provisioning.md` (1673 lines)
- `/var/home/bazzite/git/llm-env/docs/superpowers/plans/2026-10-10-system-one-decision-skill.md` (1582 lines)
- `/home/bazzite/.claude/skills/ai-kit-spec-review-checklist/references/frameworks/superpowers.md` (52 lines)
- `/home/bazzite/.claude/skills/jev-fast-decision/scripts/jev_review.py` (305 lines)
- `/var/home/bazzite/git/llm-env/setup/setup.sh` (269 lines)
- `/var/home/bazzite/git/llm-env/pylib/resources.py` (159 lines)
- `/var/home/bazzite/git/llm-env/pylib/compose.py` (297 lines)
- `/var/home/bazzite/git/llm-env/pylib/config.py` (migrate/validate sections)
- `/var/home/bazzite/git/llm-env/pylib/detect.py` (list_gpus / processes_on_render_node)
- `/var/home/bazzite/git/llm-env/tools/lib.sh` (331 lines)
- `/var/home/bazzite/git/llm-env/scripts/check-setup.sh` (293 lines)
- `/var/home/bazzite/git/llm-env/scripts/check-server.sh` (request_record / REQUEST_BODY_FILE)
- `/var/home/bazzite/git/llm-env/scripts/start.sh`, `scripts/gpu-status.sh` (200 lines)
- `/var/home/bazzite/git/llm-env/docker/laya-rocm/Dockerfile` (21 lines)
- `/var/home/bazzite/git/llm-env/llmenv.py` (cmd_budget / cmd_resources)
- `/var/home/bazzite/git/llm-env/tests/test_shell.py` (helper line anchors)
- `/home/bazzite/.claude/skills/jev-fast-decision/SKILL.md` (frontmatter + NEVER)
### CRITICAL
- **Task 8 LIVE check 6 gates on ambiguous “accuracy”** — Location: Plan B Task 8 Step 3 LIVE prompt, check 6 (~line 1494). Required: the pass rule names the metric field `accuracy_when_not_fallback` (Task 7’s calibrate rule) and does not treat the separate report field `accuracy` as the ≥ 0.95 gate. Why: check 6 records both `accuracy` and `accuracy_when_not_fallback`, then says “Task 7’s rule holds: that accuracy >= 0.95”; Task 5 defines `accuracy` as clear-case correctness and Task 7’s rule as `accuracy_when_not_fallback >= 0.95` with `len(not_fallback) >= max(10, ceil(0.3*n))`. Those two readings pass/fail opposite live corpora.
### HIGH
- **system_one-only setup drops measured VRAM fields** — Location: Plan A Task 6 Step 3 layout (~lines 951–992), early `PCI_ADDRESS` write vs skipped Step 6. Required: whenever Step 2 selects a GPU for System One (including `llm_server.enabled: false`), persist the Step 2-measured `gpu.vram_total_mib` and `gpu.vram_budget_ceiling_mib` (same values Step 6 writes today at `setup/setup.sh:170-177`), not only `gpu.pci_address`. Why: today those fields are written only in Step 6 (Vulkan); the plan skips Step 6 when llm-server is off, so Review Focus mode leaves template `vram_total_mib: 0` / ceiling derived from that zero despite a successful detect.
### MEDIUM
- **`rocr_visible_index` can raise StopIteration** — Location: Plan A Task 3 Step 3 `rocr_visible_index` snippet. Required: a missing `drm_render_minor` in a KFD node’s `properties` becomes `ValueError` (same family as “no KFD GPU node…”), not an uncaught `StopIteration`. Why: `next(...)` over an empty generator is not converted; zero-context implementers will ship the paste as-is.
### Cross-Document Consistency
- Paired gates agree: Plan B Tasks 5–8 need System One enabled and healthy on 8010; Plan A Task 11 idle-CPU is not that gate; both assume port 8010 and stop when it is not.
- Activation line agrees: Plan A `print-endpoints` and Plan B Task 6 / Global Constraints use `GSD_PATH_JEV=1 JEV_BACKEND=laya JEV_LAYA_URL=http://127.0.0.1:<port> GSD_PATH_JEV_TIMEOUT_SECONDS=20`.
- Plan B LIVE check 6’s metric ambiguity is internal to Plan B but is the gate that consumes Plan A’s live System One — fix Plan B before relying on paired E2E.
### Status: Issues Found — fix and re-invoke

Skipped: full live Laya/Zen re-probe; did not re-simulate Task 8 lanes. Risk: if check 6 is “fixed” by requiring overall `accuracy >= 0.95`, a corpus that only meets Task 7’s `accuracy_when_not_fallback` rule will still fail LIVE.

