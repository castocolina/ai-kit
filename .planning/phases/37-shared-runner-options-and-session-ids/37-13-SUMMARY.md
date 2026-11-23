# 37-13 Summary: lane skills through the runner (name, path, prose forms)

Status: complete in three per-task lanes (pi `router-env/my-coding`), verified by the orchestrator.

## Lanes

- fix-a (Task 1): `status=ok exit=0 elapsed=563s attempts=1`, commit 9401c6d (hook 129/129).
- fix-b (Task 2): `status=ok exit=0 elapsed=219s attempts=1`, commit dd18fed (tests only; the runner from Task 1 passed every new case unchanged).
- fix-c (Task 3): `status=ok exit=0 elapsed=561s attempts=1`, commit 899d089 (hook 128/128).
- Prompts were built from the plan's own task blocks plus orchestrator anchor notes (the plan's anchors predate 37-06..37-12: `confirmReport` has a fourth `builtMode` argument, both paths build the call with `callOf`, the run path plans settings after the prompt is composed).

## Commits

- 9401c6d `feat(37-13): Tracer: --skill-path on pi reaches the argv as --skill and prints applied form=path`
- dd18fed `feat(37-13): skill forms and reasons on every row, the argv-file lane and named usage errors`
- 899d089 `feat(37-13): prose skill blocks reach the lane prompt, read once, under the copilot argv limit`

## What was done

- Rows carry `forms.skills` (`name`, `path`, `prose` with labels): pi path `--skill` verified and name `mode_forbids`; claude name `/<name>` and path `--add-dir` unverified; copilot path `--add-dir` (root `.github/skills`) unverified; cursor, codex, opencode unknown; prose verified everywhere; the argv-file row gives `no_slot` for a name. 37-SPIKE.md Q4 and Q5 are "not probed", so no label was flipped and `EXPECTED_SKILL_FORMS` stays as seeded.
- `parseArgs` keeps the ordered `o.skillArgs`; `loadSkills` reads each SKILL.md once through `readCallFile` (realpath, directory, SKILL.md present and non-empty, strict UTF-8, size cap, name from frontmatter or directory); `planSkills` applies the first verified form in the order name, path, prose; one setting line per skill plus a `cross-ai: skill-block` line for prose; `composePrompt` is the single prompt composition of `--print-argv` and the run path; both `confirmReport` call sites get the composed prompt.
- Formulas: `...(c.adds?.skills || [])` is the last spread of pi, claude and copilot (exec and review); pi `reviewExtras` unchanged.
- Fakes: claude records argv and stdin (`FAKE_CLAUDE_SEEN`), copilot can edit a file per call (`FAKE_SKILL_EDIT`); `hostFilesDigest(home)`; logic cases `skill-prose-claude-stdin`, `skill-prose-copilot-argv`, `pure-skill-forms-verified`.
- `tests/test_runner_skills_argv.py` (37-02 stub, replaced): 11 tests in `TestSkillForms`, `TestRunnerSource`, `TestSkillUsageErrors`.

## Evidence (orchestrator re-run, `tmp/run-2026-11-19/c5-verify-37-13.sh`)

- Acceptance greps: 8 functions, `SKILL_PROSE` 1, `skills:` 10, fakes and digest 6, the three case names 3, `const prompt = composePrompt(skillPlan.promptPrefix` 1, `confirmReport(plan.report, firstArgv, prompt, o.mode)` 1; tests 11, classes 3, grok 0 (template grok lines still 1, none added); router-env literals 2; baseline and detection.py unchanged; no file outside the plan's two.
- `--print-argv --runtime pi --model fake/placeholder-model-1 --skill-path skills/ai-kit-cross-ai` exits 0 with `cross-ai: setting skill=ai-kit-cross-ai applied form=path` and `skill:ai-kit-cross-ai` in the status group.
- Self-test list 605 (602 + 3, all `logic`); 15 named cases (the three new ones, vocab, prepend-file, argv-prompt guard, copilot retry, settings-run-lines, argv-file) print `self-test ok`.
- `--print-argv` argv byte-equal to the 37-12 fold (affca90) for 14 calls without skill flags.
- Modules 7/7 (skills_argv, cli_help_flags, arch_hardcoded_models, arch, settings_argv, status_group, runner_flags) and 10/10 (the eight self-test shards, runner_e2e, exec_formula); verbose: all 11 skills tests `ok`, none skipped. The static host-settings-path check passes. Lane-reported: `make ruff`, `make pyright`, `make vulture`, `make pylint` exit 0.
- Real-config audit (marker at wave start): Claude host-session files (including `~/.claude/.credentials.json`, the host's own token refresh; the lanes run pi), the codex daemon's logs and model cache; no opencode or pi config file changed.

## Deviations

- Task 3 acceptance grep reads `confirmReport(plan.report, firstArgv, prompt, o.mode)`: the fourth argument (`builtMode`, from 37-06) stays.
- `loadSkills` keeps its own control-character message, but the parser (37-03) already refuses a control character in `--skill-path` with `--skill-path must be a non-empty path without control characters`, so that is the line a caller sees; the usage-error test accepts any `cross-ai:` line naming the flag, as the plan says.
- No `.planning/scripts/cross-ai.mjs` change and no shard-time refresh (both 37-23's).
