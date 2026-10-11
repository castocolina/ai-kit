## Review: docs/superpowers/plans/2026-10-10-system-one-provisioning.md, docs/superpowers/plans/2026-10-10-system-one-decision-skill.md
### Document Type
superpowers · plan (both documents)
### Files Read
- /var/home/bazzite/git/llm-env/docs/superpowers/plans/2026-10-10-system-one-provisioning.md (1687 lines). I applied Plan A Tasks 1–9 to a scratch copy of the repo at `scratchpad/v3/repo`.
  - Baseline: `make validate` PASS, `make test` 1244 passed / 0 failed.
  - After each task, `make validate` passed every time. `make test` results were T1 1248, T2 1250, T3 1256, T4 1261, T5 1262, T6 1272, T7 1281, T8 1287, T9 1288. Every run had 0 failed.
  - **Final: `make validate` PASS, `make test` 1288 passed / 0 failed.**
- /var/home/bazzite/git/llm-env/docs/superpowers/plans/2026-10-10-system-one-decision-skill.md (1582 lines). I applied Plan B Tasks 0, 2–5 and 7 (code parts) to a scratch copy of the skill at `scratchpad/v3/skill`, running `uv run --no-project --with pytest pytest tests -q` after each.
  - T0: 0 collected.
  - T2: 10 passed. T3: 14 passed. T4: 36 passed. T5: 41 passed.
  - T7 RED: 42 passed / 3 failed, as the plan expects (`calibrate` missing).
  - **T7 GREEN: 45 passed / 0 failed.**
  - I also ran the T7 Step 4 script, unchanged, against a synthetic `notes/eval-results.json` with HOME pointed at the copy. It wrote `laya: 0.6` once, the check passed, it exited 0, and the suite stayed at 45 passed.
- Grounding: I read the code each plan cites (all line references match within a few lines) and the laya 0.4.2 sources:
  - `router.DEFAULT_MODELS`, `_ALIASES` (they match `LAYA_MODEL_ALIASES`) and `normalise_name`
  - `revisions.resolve_revision`
  - the `Agent.__init__` `allow_patterns`
  - `serve._apply_thread_limit` and `_resolve_idle_unload_seconds`
  - the score/choice/noul answer shapes, which the checkers accept
  - huggingface_hub 2.2.0 `local_files_only` checks completeness per pattern, so `verify` is sound.
- The real repo and the real skill directory are unchanged. No containers were started and the GPU was not touched.

### HIGH
- **The Task 4 test import block fails `make validate` if pasted as written** — Location: Plan A Task 4 Step 1, the `# tests/test_resources.py` block (~lines 556–565).
  - **Required:** the step says to add only `SYSTEM_ONE_CPUS` and `SYSTEM_ONE_MEMORY_MIB` to the existing `from pylib.resources import (...)` at the top of `tests/test_resources.py`, and not to import the other names again. Tasks 1 and 3 already carry this kind of note.
  - **Why:** the block repeats names the file already imports at lines 8–21. I pasted it literally above the new tests and `ruff check` reported 3 errors: `F811 Redefinition of unused ResourceError`, `F811 … compute_resource_limits`, and `I001 Import block is un-sorted`. So Step 4's expected PASS fails. The other reading, replacing the existing import with this block, removes `HOST_CPU_FLOOR`, `OMNIROUTE_CPU_MAX`, `REMOTE_SETUP_CPU_MAX` and others that existing tests use. Only merging the two names passes, and that is what I did.

### MEDIUM
- **A failed `rocr-index` makes `make start` stop with no message** — Location: Plan A Task 3 Step 3, the `cmd_rocr_index` code and the `setup/render-unit.sh` snippet (~lines 496–499 and 513–526).
  - **Required:** when no KFD node matches the render node or the KFD topology is missing, `render-unit.sh` stops with a readable message.
  - **Why:** `fail()` prints its `{"error": …}` JSON to stdout. Inside `system_one_rocr_index="$(llmenv rocr-index …)"`, under `set -e`, the script exits 1 and never shows that message. A missing `/sys/class/kfd/kfd/topology/nodes` raises `FileNotFoundError`, which `except ValueError` does not catch, so the user gets a traceback.
- **Wrong claim about how setup prompts behave at end of input** — Location: Plan A Task 6 Step 1, "Input" bullet (~line 754), the parenthetical "(`read` at EOF also fails under `set -e`)".
  - **Required:** the parenthetical says what the code actually does. At end of input, `ask` returns its default.
  - **Why:** bash outside POSIX mode turns off `-e` inside `$(…)`, and `ask` ends with `printf`. I ran the real `setup/setup.sh` from the scratch copy with empty stdin and it finished with "Setup complete". A short test stdin therefore takes defaults silently instead of failing. The prescribed inputs are still correct.
- **LIVE 4 assumes something nothing records** — Location: Plan B Task 8, LIVE 4 (~lines 1487–1489), compared with Task 7 Step 3, where thresholds can go as low as 0.50.
  - **Required:** Task 5 records the top probability of the alone `vague` answer, the same way it records `repeat_max_prob_diff`. LIVE 4 then fails clearly before the round starts if that value is not below the calibrated `min_confidence`.
  - **Why:** LIVE 4 needs alone `vague` to come back with `needs_fallback: true`. The only measured value is "billing 0.46", which is not the answer's top probability across three options. If calibration picks 0.50 or 0.55, LIVE 4 can fail no matter how good the skill is.

### Cross-Document Consistency
- Both plans agree on:
  - port 8010
  - the activation line `GSD_PATH_JEV=1 JEV_BACKEND=laya JEV_LAYA_URL=http://127.0.0.1:<port> GSD_PATH_JEV_TIMEOUT_SECONDS=20`, which Plan A's print-endpoints test pins
  - `POST /v1/systemone` counted as per-check differences only
  - Task 11 not being the gate for Plan B Tasks 5–8
  - Plan B Task 6 copying Plan B Task 5's `notes/eval-results.json`

  I found no contradictions between the two plans.

### Status: Issues Found — fix and re-invoke
