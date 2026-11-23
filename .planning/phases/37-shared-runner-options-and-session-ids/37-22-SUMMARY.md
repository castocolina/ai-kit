# 37-22 Summary: runner docs outside ai-kit-cross-ai match the runner

Status: complete in one lane for all three tasks (pi `router-env/my-coding`), verified by the orchestrator.

## Lane

- fix-a (Tasks 1, 2 and 3 in one lane, one commit): `status=ok exit=0 elapsed=570s attempts=1`, commit f9b995d (hook 149/149).
- The prompt was built from the plan's own task blocks plus anchor notes checked against 45aa34d (`tmp/run-2026-11-19/c10-notes-37-22.md`).

## Commit

- f9b995d `docs(37-22): runner docs name the call vocabulary, settings report, hosting and the shipped template; baseline and marked-region pins`

## What was done

- cross-ai-dispatch.md: the runner call names `--role review`, `--host auto` and the entry's settings (no `--session-id` for a reviewer); the **Hosting.** paragraph; the `transient` row reads "template 7 and later"; the status-token paragraph names the settings group and the `cross-ai: setting` lines (the following "What each means is in ..." sentence and its link kept; the custom-entry sentence naming grok left untouched).
- runner.md: H1 and floor text at template 9; the call vocabulary line and five bullets under "## Template flags"; the opt-in paragraph with the review allowlist read from the template (pi `--skill <path>`) and the MCP flags as formula flags; the `unknown` / `argument` line break kept.
- curated-config SKILL.md: template 9 at the four floor sentences (213, 222, 266, 353).
- README.md: the `ai-kit-cross-ai` and `ai-kit-gsd-curated-config` rows.
- cli-profiles/claude.md: plan 37-10 had already rewritten the paragraph, so the plan's second branch applied: only the stale routing sentence was replaced.
- ai-kit-spec-config/SKILL.md line 200: the effort parenthetical names the generic `--effort` flag.
- tests/test_cross_ai_docs_text.py: the 37-02 stub replaced by `DispatchAndRunnerDocs` (6), `ReadmeAndProfileDocs` (3), `MarkedRegionInRunner` (1).
- tests/test_cross_ai_skill_text.py: the two template pins renamed and pinned to `cross_ai.TEMPLATE_VERSION` (30 test methods kept).
- Baseline: `shrink.py` printed `shrink: nothing to remove` (the guard named no fixed or gone hit), so tests/fixtures/no_hardcoded_models_baseline.json is unchanged (1486 hits).

joins loop 37: ai-kit-gsd-curated-config (floor sentences)
joins loop 37: ai-kit-spec-config (line 200)

## Evidence

Orchestrator re-run, `tmp/run-2026-11-19/c10-verify-37-22.sh 880b3e7`:

- Every acceptance grep at its expected count: `--mode review` and the template 8 phrases gone from the dispatch reference; `AIKIT_HOST=none` in runner.md; "review allowlist", "template-7", "ensure-runner" and the `unknown` / `argument` break kept; no template 8 floor token in README.md, curated-config SKILL.md or runner.md; claude.md holds neither "an exec attempt exits 2" nor "until it reads the runner's own"; the codex-effort parenthetical gone.
- tests/test_cross_ai_docs_text.py 10 test methods, all ok, none skipped; tests/test_cross_ai_skill_text.py 30.
- Modules: cross_ai_docs_text, cross_ai_skill_text, ai_kit_spec_runtimes_table, spec_chain_text, spec_config_flow_text, skill_text_history, ai_kit_gsd_curated_config, curated_config_script, arch_hardcoded_models 9/9.
- No grok line added; no `native` + `_runtime` / `_claude` token; Makefile, .pre-commit-config.yaml, cross-ai.mjs, ai-kit-cross-ai files, tests/test_cross_ai_settings_text.py and tools/gen_test_groups.py untouched; baseline unchanged.

## Deviations

- The plan's three commits were made as one lane commit (the fold makes one commit per plan anyway).
- The test module docstring was shortened and two list constructions rewritten to satisfy ruff; the tests check what the plan names.
- The baseline was not committed: shrink.py found nothing to remove (the guard already passed at HEAD).
- The spec-config SKILL.md line 200 is now longer than its neighbours (not rewrapped).
