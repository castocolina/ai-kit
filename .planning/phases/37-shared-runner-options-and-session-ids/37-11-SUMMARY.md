# 37-11 Summary: rendered runner copy stays in sync with the template

Status: complete in one lane (plan as written; pi `router-env/my-coding`), verified by the orchestrator.

## Lanes

- Lane 1 (plan as written): `status=ok exit=0 elapsed=704s attempts=1`, three commits. The lane also ran `make test` (unit 177/177, unit-uv 3/3, integration 9/9, e2e 26/26, arch 2/2, installer 48 passed, per its report).

## Commits

- 252fd3b `test(37-11): a rendered runner copy matches the template byte for byte outside the config block`
- 16023dc `test(37-11): template and rendered copy give the same --print-argv matrix`
- cb7a754 `test(37-11): non-vacuity cases for the render sync test`

Each holds only `tests/test_cross_ai_render_sync.py` (plan 37-02's registered stub, replaced whole); Makefile, `.pre-commit-config.yaml` and generated listings untouched.

## What was done

- `sync_problems(template, copy)`: pristine state, same template version, bytes outside the config block equal through `tools/check_dogfood.py`'s `_outside_config` (loaded by path), the config block one canonical CONFIG assignment (`render(template, template_config(copy)) == copy`). `render_copy` renders through the installer's own `cross_ai_script.ensure_runner` into a scratch project at `cross_ai.SCRIPT_PATH`.
- `--print-argv` matrix: six runtimes by review and execute, plus codex `--effort high`, cursor `--session-id placeholder-session-1` and an `--argv-file` lane (`placeholder-cli-1`); template and copy run with the same cwd and `runner_env`; normalization limited to `elapsed=<n>s` and a runner-generated session UUID on a chosen host when the call names no id.
- Non-vacuity: one changed byte outside the block (restamped and not), code hidden before and after the CONFIG assignment, a config-only edit that passes, two renders in separate scratch directories with the template's sha256 unchanged, and a changed cursor formula caught by the matrix on the cursor cases only.

## Evidence (orchestrator re-run, `tmp/run-2026-11-19/c4-verify-37-11.sh`)

- Acceptance greps: `def sync_problems(`, `cross_ai_script.ensure_runner(`, `cross_ai.SCRIPT_PATH`, `class TestSyncNonVacuity(` and both problem texts present; stub class and test 0; planning-folder literal 0; eight `def test_`; grok 0; `"--print-argv"`, `"--argv-file"`, `"--session-id"`, `"--effort"` present.
- Modules 5/5 (render_sync 8 tests, arch, arch_hardcoded_models, gate_scope, check_dogfood); verbose run: all eight tests `ok`, none skipped (real node present). Lane-reported: `make ruff`, `make pyright`, `make vulture`, `make pylint` exit 0. Tree clean.
- Real-config audit (marker before plan 37-10's lane): Claude host-session files, the codex daemon's logs, state and model cache, the lanes' pi sessions, and `~/.config/opencode/opencode.jsonc`, `~/.pi/agent/models.json`, `~/.pi/agent/settings.json` written together at 12:25:13 (within 25 ms). This lane was running `make ruff` and its Task 1 tests then; its pi session holds no command naming those files, the tests run under the runner's temporary HOME, and no ai-kit code writes `~/.pi/agent/models.json`. The same three-file write happened at 10:56:44 during chunk C3 and was traced to another project's agent-client setup (llm-env, which had a pytest run active at this time as well). Not attributed to this plan; listed for the owner.

## Deviations

- None in behaviour. Executed as three task commits (the plan names three).
