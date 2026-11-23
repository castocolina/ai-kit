# 37-21 Summary: ai-kit-cross-ai documents the call vocabulary, the settings report and the status group, locked to the runner

Status: complete in two per-task lanes (pi `router-env/my-coding`), verified by the orchestrator. The SKILL.md change waits for the plan 37-24 judge loop.

## Lanes

- fix-a (Task 1): `status=ok exit=0 elapsed=272s attempts=1`, commit f07924d (hook 13/13).
- fix-b (Tasks 2 and 3 in one lane): `status=ok exit=0 elapsed=613s attempts=1`, commit 6b9fee6 (hook 13/13; the lane also ran `make test`, green).
- Prompts were built from the plan's own task blocks plus anchor notes checked against HEAD (`tmp/run-2026-11-19/c9-notes-37-21.md`: wrapped sentences, `TEMPLATE_VERSION` at cross_ai.py line 60, runner lists at cross-ai.mjs lines 1569-1570).

## Commits

- f07924d `docs(37-21): settings report, status fields and real sample lines in ai-kit-cross-ai`
- 6b9fee6 `docs(37-21): call vocabulary, sessions, argv-file lane, hosting, skills, MCP and evals in ai-kit-cross-ai`

## What was done

- skills/ai-kit-cross-ai/SKILL.md: new description; section 1 `--role` sentence and `### Call settings` (eleven rows); section 2 floor `template=9`, `--role execute` launch block, `### A runtime the runner has no formula for`, `### Hosting in a herdr tab` (with the setsid, fish, nushell, prompt and macOS limits), `### Skills and MCP servers for a lane`; section 4 samples from a hermetic run, `### Settings report` (names, states, ten-row reason table), `### Status line fields`; section 5 session paragraph; section 6 sample; a Pitfalls bullet; trailing `## Evidence`.
- references/launch-and-wait.md: real ok and report lines, `--role execute` in both launch blocks.
- tests/test_cross_ai_settings_text.py (replaces the 37-02 stub): SettingsReportDocs (4), StatusGroupDocs (3), VocabularyDocs (8); the reason table, names sentence and vocabulary table are locked to `SETTING_REASONS` / `SETTING_NAMES` in the runner source and to `--describe`.
- skills/ai-kit-cross-ai/evals/: evals.json (6), trigger-queries.json (16, 8 positive), files/session-ok/lane.err and files/auth-stop/lane.err from the capture.
- Scratch capture (not committed): tmp/run-2026-11-19/p37-21/capture.py and capture.txt (five hermetic runs against the e2e fake opencode: ok 0, auth 69, capacity 75, effort 0 with `effort=low ignored reason=id_carries`, unknown runtime 2).

## Evidence

Orchestrator re-run, `tmp/run-2026-11-19/c9-verify-37-21.sh 402c803 3`:

- Every acceptance grep at its expected count (old sample references 0, `--mode exec[^|]` 0, `template=8` 0, recurring/hourly 0, grok 0; the four subsections and `## Evidence` present, `## Evidence` the last heading).
- Sample lines in SKILL.md and launch-and-wait.md are byte-equal to capture.txt (ISO times replaced by `<iso time>` in SKILL.md only); no machine path, no ISO date in SKILL.md.
- 15 test methods, no stub skip; the `--describe` legs ran (not skipped); evals 6, queries 16 / 8; session-ok holds `session=ses_1`, auth-stop holds `status=auth ... exit=69`.
- Modules: skill_evals_shape, cross_ai_settings_text, cross_ai_skill_text, quota_policy_text, skill_text_history, skill_frontmatter, arch_hardcoded_models 7/7.
- tests/test_cross_ai_skill_text.py, Makefile and .pre-commit-config.yaml untouched.

## Deviations

- The fix-a lane also rewrote the section 1 `--role` sentence (Task 2's step) in its own words; the fix-b lane replaced it with the plan's sentence, so the final text is the plan's.
- The sample lines come from hermetic runs of the template against the e2e fake opencode, not from `--self-test` output (the plan's recorded live fact).
- The fix-a lane wrapped the prescribed test docstring and the fix-b lane reordered imports and wrapped two test lines for ruff.
