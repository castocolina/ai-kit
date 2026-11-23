# 37-05 Summary: the settings planner, version 2 (context and session forms)

Status: complete in one lane (pi `router-env/my-coding`), verified by the orchestrator.

## Lane

- `AIKIT-XAI status=ok cli=pi model=router-env/my-coding exit=0 cli_rc=0 elapsed=886s attempts=1 cycles=0`.

## Commits

- 1b1f44a `feat(37-05): plan context and session forms` (one commit for the three tasks; the plan asked for one per task). Holds only `skills/ai-kit-spec-review/references/cross-ai.mjs` (+74/-11) and `tests/test_runner_settings_argv.py` (+143). The staged-tests hook passed (129/129 modules per the lane).

## What was done

- `contextTokens(label)` (decimal k and m, 1 to 1000000000); `SETTING_HANDLERS.context` (`no_form`, `unverified_form`, `bad_value`, `id_carries`, then flag, config or bracket feeding) and `SETTING_HANDLERS.session` (chosen create-or-continue, minted resume, `mode_forbids` for codex review and sandboxed codex, `no_form` for a minted row without a resume formula).
- `forms.context` and `forms.session` on all six rows with the plan's label sources. copilot `exec`/`review` spread `c.adds.context` and carry `'--session-id', c.sid`; `withCodexKnobs` pushes the context pair after effort.
- `newSessionArgv` mints a new id for every chosen row (`if (rt.forms?.session?.style === 'chosen') ctx.sid = crypto.randomUUID();`); `runCli`'s `sid: crypto.randomUUID()` and `(name === 'pi' ? ctx.sid : null)` untouched (37-06/37-07).
- `--print-argv` passes `context`, `sessionId`, `newSessionId: '<sid>'`, `sandbox`; ctx `sid: plan ? (plan.sessionId ?? '<sid>') : '<sid>',`; prints `rt.resume(...)` when `plan.resume`.
- Self-test cases `copilot-argv-exec` and `copilot-argv-review` gain `--session-id <sid>`; no case added (519).
- Tests: `TestContextForms` (5), `TestSessionForms` (5); `NO_SETTING_ARGV` copilot entries gain `--session-id <sid>`; 21 tests.

## Session labels from 37-SPIKE.md

- pi, opencode, claude: not flipped. 37-SPIKE.md "Label flips" records each `forms.session.label -> unverified, not probed (no ledger consent line)` and opencode `style -> minted`; every label keeps its unverified default, opencode stays `minted`.

## Evidence (orchestrator re-run, scratch HOME)

- Acceptance greps: `contextTokens` 1, `valueKind` 3, `style` 6, `noResume` 1, the pi-only sid line 0, the chosen-row line 1, print-argv ctx line 1, `'--session-id', c.sid` 4, `      session: {` 6, `      context: {` 6, 21 tests; no grok line added; Makefile and `.pre-commit-config.yaml` untouched.
- `--self-test-list`: 519. Twelve named cases (Task 1 and Task 2 verify lists plus `planner-confirm-report`, `planner-report-lines`): `self-test ok`.
- Spot checks: cursor `--effort high --context 1m` -> `fake-ok-cursor[effort=high,context=1m]`, effort line before context line; codex `--context 2000m` -> `bad_value`; codex exec `--context 200k --session-id s-1` -> `exec resume ... s-1 - -c model_context_window=200000`; codex review session -> `mode_forbids`; claude -> context `unverified_form`, session `no_form`; pi UUID session id printed unredacted.
- No-setting argv equals the bb43c3c template for pi, opencode, cursor, codex (both modes), claude review, codex `--codex-effort high`, pi `fake/ok:high`, cursor `--effort high`; copilot differs only by the new `--session-id <sid>` (by design, 0c).
- Task 3 module list 9/9; eight self-test shards plus `test_ai_kit_spec_exec_formula_e2e` 9/9. Lane-reported: `make ruff` (after line-length fixes), `make pyright`, `make vulture`, `make pylint` exit 0; `make test` exit 0. `tmp/p37-05` gone; tree clean.
- Real-config audit: the orchestrating Claude session's files, the codex app-server daemon's files and the lane's own pi session file; nothing else.

## Deviations

- Plan text vs the 37-02 main-help guard (lesson 9): the opencode session label drops the plan's `--session, -s string` prefix (a `run`-subcommand flag absent from opencode's main help) and quotes `"Session ID to continue, or to create if it does not exist"`.
- One commit instead of one per task.
