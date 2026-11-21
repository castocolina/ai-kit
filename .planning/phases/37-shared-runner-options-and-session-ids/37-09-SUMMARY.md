# 37-09 Summary: argv-file lane for a runtime with no formula

Status: complete after one no-change lane, two focused fix-up lanes (pi `router-env/my-coding`, same CLI and model throughout) and one orchestrator fix commit, verified by the orchestrator.

## Lanes

- Lane 1 (plan as written): `status=no_change exit=1 elapsed=70s tree=clean`, no edit.
- Fix-up a (XAI_FIXUP, the plan's Task 1 block verbatim plus framing and checked anchor corrections): `status=ok exit=0 elapsed=471s attempts=1`, commit 414f5fe.
- Fix-up b (XAI_FIXUP, the plan's Task 2 and 3 blocks verbatim plus framing): `status=ok exit=0 elapsed=571s attempts=1`, commit 0dac382.

## Commits

- 414f5fe `feat(37-09): a runtime with no formula runs a command declared by --argv-file`
- 0dac382 `feat(37-09): argv-file refusals, review role, read-once and the flag doc`
- 4559cfa `fix(37-09): an argv-file retry keeps its explicit session id without the pin` (orchestrator)

Each holds only `skills/ai-kit-spec-review/references/cross-ai.mjs`; the staged-tests hooks passed (128/128 modules each).

## What was done

- `ARGV_FILE_PLACEHOLDERS`, `ARGV_FILE_NO_FORM`, `loadArgvFile` (plan 37-03's `readCallFile` with `cwdOnly`, `strictJson`, content-free strict-JSON error, array, empty, non-string, NUL, unknown-placeholder and command-placeholder refusals), `fillArgvFile` (function replacers), `argvFileAllowed`, `argvFileRow` (never added to `RUNTIMES`; `errorsUnverified: true`, no listing, resume, profiles or seed shape), `planArgvFile` (slot settings `applied` with the exact substituted element as proof, absent slots and context `ignored no_slot`, provider `- unknown`, `{effort}` or `{session}` without the setting a usage error); first statement of `planSettings`; usage finish after both `planSettings(` call sites.
- `main`: `--argv-file` with a row that has the selected role's formula is refused (`cross-ai: --argv-file needs a runtime with no <execute|review> formula in the runner; <id> has one`); otherwise the file is read once and the declared row runs through `runCli`; plan 37-08's named refusal stays for an id with no row and no file. `liveSettings.sessionId` reads `plan.sessionId` for a declared row (a file without `{session}` shows `session=-`); `pinSession` is off for a declared row; `attemptSid` keeps the explicit id on the first attempt and on every `new`/`reset` rung.
- Fake `placeholder-cli-1` (`writeFakeDeclared`, `FAKE_DECLARED_SEEN`, `fake-crash`, `fake-edit-then-ok`, `fake-review`); 29 self-test cases, all `logic`; `--self-test-list` 599. Flag doc lines for `--runtime` and `--argv-file`.

## Evidence (orchestrator re-run, scratch HOME, `tmp/run-2026-11-19/c4-verify-37-09.sh`, then the fix)

- Acceptance greps: every function and edit line of Task 1 present; `viaSlot` 0; `argvFile: true` 1; the known-runtime refusal 1; `argv-file-refuse-` 1; the unknown-placeholder and NUL texts present; the `--runtime` doc text 1; grok lines in the template 1 (none added); `router-env/` literals 2; baseline JSON unchanged. Before the fix `pinSession: !rt.argvFile &&` was 0 (see Deviations); after it, 1.
- All 29 names listed as `logic`; the 29 plus `gate-runtime-no-formula`, `gate-runtime-case-sensitive`, `ok`, `model-flag-each-claude`, `settings-run-lines`, `session-roundtrip-cursor`, `session-pinned-copilot-retry`: `self-test ok`. After the fix, the ten behaviour cases of Tasks 1 and 3, `pure-argv-file-slot-proof` and eight session and ladder cases (`session-pinned-copilot-retry`, `session-roundtrip-cursor`, `session-rejected-no-fresh`, `session-rejected-transient-no-fresh`, `session-chosen-pi`, `session-chosen-copilot`, `ladder-codex-exec-resume`, `hard-tier-other-task-fresh-session`): `self-test ok`.
- A declared file under `--print-argv` prints `placeholder-cli-1<TAB>MISSING<TAB>["--model","fake-ok","--effort=high"]`, `setting effort=high applied` and `rung1 placeholder-cli-1 unavailable`.
- `--print-argv` stdout equals the da373a3 template for fourteen calls (eleven runtime and mode entries, pi `--effort high`, cursor and pi `--session-id s-1`).
- Modules 6/6 (cli_help_flags, runner_status_group, arch_hardcoded_models, runner_settings_argv, runner_dispatch, arch); eight shards plus `test_cross_ai_runner_e2e` and `test_ai_kit_spec_exec_formula_e2e` 10/10; the fix commit's hook 128/128. Lane-reported: `make ruff`, `make pyright`, `make vulture`, `make pylint` exit 0. Tree clean; scratch folder removed.
- Real-config audit (marker before lane 1): Claude host-session files, the codex app-server daemon's auto-update and logs, the lanes' pi sessions; none attributable to this plan.

## Deviations

- Plan gap: step 7(c) kept the explicit id only for the first attempt; a transient retry of a declared row goes to the `new` rung, which reset `attemptSid` from `argv.includes(ctx.sid)`, false for an embedded `--session=<id>`, so `argv-file-read-once` failed on `session=`. Fix-up b turned the pin on for declared rows and marked them `chosen`, which broke Task 1's acceptance line `pinSession: !rt.argvFile &&` and the must-have that the pin is off (a pinned row also refuses the `new` and `reset` rungs and gets no resets). The orchestrator fix restores the plan's pin line and `chosen` and keeps `opts.sessionId` as `attemptSid` on the `new` and `reset` rungs of a declared row; both the acceptance line and the case hold.
- Anchors absent from the code (`function piThinkingArgs(`, `function refuseReview(` as a declaration) were corrected in the fix-up prompt; no `planSettings(` call sits in `runCli`, so step 6's runCli branch had no site.
- Executed as two fix-up lanes plus one fix commit instead of the plan's single commit (folded at the wave checkpoint).
