## Reviewer opus
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

## Reviewer cursor-auto
### Document Type
Superpowers · plan (both)
### Files Read
- `/var/home/bazzite/git/llm-env/docs/superpowers/plans/2026-10-10-system-one-provisioning.md` (1687 lines)
- `/var/home/bazzite/git/llm-env/docs/superpowers/plans/2026-10-10-system-one-decision-skill.md` (1582 lines)
- Grounding (not reviewed): `pylib/compose.py`, `pylib/resources.py`, `pylib/budget.py`, `pylib/config.py`, `pylib/detect.py`, `llmenv.py`, `scripts/start.sh`, `scripts/check-setup.sh`, `scripts/check-server.sh`, `scripts/gpu-status.sh`, `scripts/print-endpoints.sh`, `setup/setup.sh`, `setup/render-unit.sh`, `tools/lib.sh`, `docker/laya-rocm/Dockerfile`, `tests/test_shell.py`, `tests/test_compose.py`, `tests/test_cli.py`, `~/.claude/skills/jev-fast-decision/scripts/jev_review.py`, `SKILL.md`, `reference.md`, `~/.claude/skills/skill-judge/SKILL.md`
### CRITICAL
- **Unknown `JEV_BACKEND` reason string disagrees with Interfaces** — Location: Plan B Task 2 Interfaces (~L139) vs Task 2 `main()` `--probe` branch (~L402–408) and Task 3 `screen()` empty-usable branch (~L679–680). Required: one rule for explicit unknown names (e.g. `JEV_BACKEND=zen`): either `reason` is always `backend_unavailable:<name>:<probe reason>` (including `unknown_backend`), or Interfaces explicitly limit that shape to names in `BACKENDS` and document `no_backend_available` for unknowns — and `main()` / `screen()` match that rule. Why: Interfaces say every explicit unusable backend gets `backend_unavailable:<name>:<probe reason>`; the pasted code only builds that when `choice in BACKENDS`, so unknown names get `no_backend_available` instead — two opposite reason strings for the same env.
### HIGH
### MEDIUM
- **Task 3 compose assembly snippet is easy to mis-paste** — Location: Plan A Task 3 services/volumes assembly (~L475–485). Required: the snippet is clearly an addition after the existing `llm-server` / `omniroute` / `remote-setup` population, not a replacement of that block. Why: taken alone it rebuilds `document` from `services` without showing those assignments; existing compose tests would catch a wipe, but a zero-context paste can still drop them first.
- **LIVE check 4 assumes vague top stays below calibrated T** — Location: Plan B Task 8 Part 3 check 4 (~L1487–1489) vs Spec table (~L22) and Task 7 calibrate (lowest qualifying T, often 0.50). Required: pass criterion remains true under the measured alone-vague distribution (or the check pins a threshold relationship that cannot flip when calibrate returns 0.50). Why: alone pricing was measured at billing 0.46; if live top lands ≥ calibrated T, `needs_fallback` is false and the round fails despite correct dispatch.
### Cross-Document Consistency
- Port 8010 gate, activation env line, idle-CPU non-gate for Plan B Tasks 5–8, and Task 5→6 `notes/eval-results.json` handoff agree across both plans; no cross-doc contradiction found.
### Status: Issues Found — fix and re-invoke

Skipped: full live ROCm/KFD topology re-measure; risk: unknown-backend reason mismatch alone blocks clean execution of Plan B’s probe/`screen` contract.

