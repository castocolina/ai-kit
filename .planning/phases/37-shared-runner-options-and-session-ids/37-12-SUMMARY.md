# 37-12 Summary: one Python call vocabulary for the runner (table-driven flags, version 9)

Status: complete in two per-task lanes (pi `router-env/my-coding`), verified by the orchestrator.

## Lanes

- fix-a (Task 1, prompt built from the plan's own task block plus anchor notes): `status=ok exit=0 elapsed=984s attempts=1`, commit c867398. The first commit attempt failed its hook (131/133) on golden fixtures and the lane-settings literal guard; the lane fixed both and recommitted (hook 133/133).
- fix-b (Tasks 2 and 3): `status=ok exit=0 elapsed=570s attempts=1`, commit bfaab43 (hook 129/129).
- No plan-as-written lane: the plan is flagged heavy, so the tasks were split up front.

## Commits

- c867398 `feat(37-12): Tracer: table-driven runner_flags with the new settings and template version 9`
- bfaab43 `feat(37-12): escalation through lane_escalation, build-command --role and builder parity`

## What was done

- `RunnerSpec` gains `context`, `session_id`, `escalate_runtime`, `escalate_model`, `host` (default `"auto"`, D-23) and the `role` property; `_SETTING_FLAGS` drives `runner_flags` in one fixed order (`--runtime --model --role`, route, `--effort --context --session-id --escalate-runtime --escalate-model --host`, then codex service tier and sandbox, cursor mode). `--mode` and `--codex-effort` are gone.
- `spec_with_effort` reads escalation only through `lane_settings.lane_escalation` and passes `context=None, session_id=None`; `review_spec` and `execute_dispatch._runner_spec` pass the whole entry or candidate as knobs.
- `build-command --role review|execute` (default review); its flags equal the GSD hook builder's for one lane.
- `TEMPLATE_VERSION = 9`, `_READY_TEMPLATE = 9`, template header lines 2 and 4 (2 insertions, 2 deletions in the template).
- `tests/test_runner_flags.py` (37-02 stub, replaced): 14 tests in five classes, including the tracer that runs the shipped template with every flag Python emits.

## Evidence (orchestrator re-run, `tmp/run-2026-11-19/c5-verify-37-12.sh`)

- Acceptance greps: `codex-effort` 0 and `"--mode"` 0 in runner_dispatch.py; `_SETTING_FLAGS = (` and `def role(self) -> str:` present; both version constants 9; template diff 2/2; `lane_escalation(` 1; `escalate_` 0 in execute_dispatch.py; 14 tests; grok 0; the `--role` parser line present.
- Modules 11/11 (runner_flags, runner_dispatch, ai_kit_spec, trust, curated_config, curated_config_script, lane_settings, arch_hardcoded_models, superpowers, render_sync, cli_help_flags); verbose: all 14 runner_flags tests `ok`, none skipped. `build-command --runtime codex --role execute` prints `--role execute --host auto --codex-sandbox workspace-write`. Self-test list still 602 cases. detection.py unchanged. Lane-reported: `make ruff`, `make pyright`, `make vulture`, `make pylint` exit 0.
- Real-config audit (marker at chunk start): Claude host-session files and the codex daemon's auto-update and logs only; no opencode or pi config file changed.

## Deviations

- Seven golden fixtures under `tests/fixtures/curated_config_v2/golden/` (outside the file list) pinned runner `version: 8`; updated to 9 (lesson 4: they asserted the old version this plan replaces).
- `tests/test_lane_settings.py` (outside the file list): phase 36's guards banned lane-flag string literals and every lane reader in ai_kit_spec modules. The locked phase-37 rules need both in runner_dispatch.py, so the guards now exempt only the `_SETTING_FLAGS` assignment and only the name `lane_escalation` in runner_dispatch.py; two new non-vacuity asserts prove other setters and readers are still caught.
- Baseline: one hit removed (`cross_ai_script.py` "flag and", fixed by the rewritten floor comment).
- `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cross_ai.py` line 53 still names `--codex-effort` in a comment (not in this plan's scope); left for code review.
