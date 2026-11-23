# 37-07 Summary: session ids at run time

Status: complete after one no-change lane and two focused fix-up lanes (pi `router-env/my-coding`, same CLI and model throughout), verified by the orchestrator.

## Lanes

- Lane 1 (plan as written): `status=no_change exit=1 elapsed=68s tree=clean`; read the SPEC, summaries, CONTEXT and RESEARCH, ended "not implemented", no edit.
- Fix-up a (XAI_FIXUP, the plan's Task 1 block verbatim plus framing): `status=ok exit=0 elapsed=534s attempts=1`, commit 145fa2f.
- Fix-up b (XAI_FIXUP, the plan's Task 2 and 3 blocks verbatim plus framing): `status=ok exit=0 elapsed=1125s attempts=1`, commits dc8956c and d25f5eb.

## Commits

- 145fa2f `feat(37-07): explicit session id resumes first, prints session=, never falls to a fresh rung`
- dc8956c `test(37-07): chosen, opencode and codex sessions, mode_forbids and last_sid precedence`
- d25f5eb `test(37-07): unshown host and record ids print session=- and are never passed back`

Each holds only `skills/ai-kit-spec-review/references/cross-ai.mjs`; the staged-tests hooks passed (128/128 modules each, per the lanes).

## What was done

- `sessionShown(id)` (37-03's `SESSION_ID_RE` plus `redactKeyShapes`); `main` sets `liveSettings.sessionId` from an explicit shown id on the run and print-argv paths and passes `pinSession` when the planner applied it.
- `runCli`: `pinned`, `chosen`, `attemptSid`, `hostSid`, `usedSid`, `unshownNoted`, `sameArgv` (a pinned chosen row continues through `newSessionArgv(..., keepSid = true)`); `sessionResets: pinned ? 0 : ...`; a pinned `new` or `reset` step is refused with `cross-ai: --session-id was given; no fresh session is started (next=<step> refused)`; `classStop`, `saveCycle` and the attempt lines use the id actually used; a persisted `last_sid` outside the charset or key-shaped is never reused (note printed); a host id outside the charset prints `session=-` with one note; `reviewProblem` falls back to the review formula for a row without `resume`.
- Fakes: `recordSession` in `FAKE_PRELUDE`, `FAKE_SESSIONS` harness env and `sessionRows`; cursor fake `--resume`, `rejected-*`, `rejected503-*`, `FAKE_SESSION_MODE=badsid-503`; opencode `--session`, codex `exec resume <id> -`, copilot `--session-id`, claude `--resume` and `FAKE_SESSION_MODE=nosid`.
- Thirteen self-test cases, all `logic`; `--self-test-list` 542.

## Evidence (orchestrator re-run, scratch HOME)

- Acceptance greps: `function sessionShown(id)`, `sessionResets: pinned ? 0 : retryCfg.session_resets`, `no fresh session is started (next=`, `FAKE_SESSIONS: path.join(tmp,`, the three `recordSession` calls of Task 2, both notes, `badsid-503` present; the old `p.sessionId || (name === 'pi'` line 0; `recordSession('` 5 (cursor, opencode, codex, copilot, plus claude from Task 3); one `SESSION_ID_RE`; grok lines in the template 1 (unchanged), none added; Makefile and `.pre-commit-config.yaml` untouched.
- All thirteen cases listed as `logic`; the thirteen plus `ladder-codex-exec-resume`, `hard-tier-other-task-fresh-session`, `settings-run-lines`, `settings-session-first-argv`, `ladder-codex-review-fresh`, `copilot-dash-prompt`, `claude-review-ok`, `claude-exec-usage`: `self-test ok`.
- `--session-id ''` exits 2. `--print-argv` stdout argv equals the 46b4720 template for fourteen calls (eleven runtime/mode entries plus cursor, codex and pi with `--session-id s-1`).
- Modules 5/5 (runner_status_group, cross_ai_skill_text, arch_hardcoded_models, runner_settings_argv, runner_dispatch); eight shards plus `test_cross_ai_runner_e2e` and `test_ai_kit_spec_exec_formula_e2e` 10/10. Lane-reported: `make ruff`, `make pyright`, `make vulture`, `make pylint` exit 0. Tree clean.
- Real-config audit: Claude host-session files, the codex app-server daemon, the lanes' pi sessions, and `~/.config/opencode/opencode.jsonc`, `~/.pi/agent/models.json`, `~/.pi/agent/settings.json` written together at 10:56:44 (13:56:44 UTC). At that moment fix-up b was inside its Task 3 `git commit` hook (modules run under a temporary HOME); its pi session shows no command touching those files, and no ai-kit code writes `~/.pi/agent/models.json`. A concurrent llm-env onboard-local-model run (another agent, `router-env/llama-cpp/...`) was active, and llm-env's agent-client setup writes those files. Not attributed to this plan; listed for the owner.

## Deviations

- `session-host-id-unshown` passes `--no-preamble` on both cursor calls: the plan's `taskDigest('prompt\n')` record matches the runner's digest only without the preamble, so the persisted-invalid-id path is exercised only that way.
- Executed as two fix-up lanes carrying the plan's task blocks verbatim, after the plan-as-written lane stopped without an edit.
