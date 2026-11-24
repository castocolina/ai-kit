# Loop 39.2 round 1 fixes: ai-kit-commit-fold

Decide row: `fix` (3 critical, important or high findings: referee-one 3, referee-two 0, referee-three 0). No further round (AGENTS.md fix rule); the skill's digest is stale by design until its next loop.

- referee-one D8-1 (SKILL.md:31): "A refusal changes nothing" now applies to the fold that refused; `fold.py gsd --phase N` may have folded earlier plans, each reported before the refusal; relay every report and never move the branch back. File: skills/ai-kit-commit-fold/SKILL.md (Read the report).
- referee-one D8-2 (SKILL.md:102): a flow refusal report shows only its `refused:` line (scripts/flow_unit.py `_run`), so completed catch-up pushes, folds or merges may be unlisted; check local tip, remote tip and PR state read-only before re-running. Files: skills/ai-kit-commit-fold/SKILL.md (Unit flow), references/unit-contract.md (exit code 1), references/adapter-guide.md (superpowers step 5).
- referee-one D8-3 (SKILL.md:139): split `bad_resolution`: file errors keep the stack paused (fix the named files, rerun `--continue`); a branch that moved after the saved resolution has already been restored and the paused state cleared (scripts/flow_stack.py `_check_resolved_tips` then `_abort_and_restore`): report it and ask before a new restack, never rerun `--continue`. File: skills/ai-kit-commit-fold/SKILL.md (Cascade conflicts).

Tests before commit (text-only change, no new test): `python3 tools/run_unittest_parallel.py tests.test_skill_evals_shape tests.test_skill_text_history tests.test_skill_frontmatter tests.test_flow_docs tests.test_ai_kit_gsd_spec_discuss tests.test_check_dogfood`: 6/6 modules passed.
