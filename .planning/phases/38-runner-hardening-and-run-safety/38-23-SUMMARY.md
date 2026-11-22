# 38-23 Summary: ai-kit-cross-ai documents the supervision flags, the run lock, the watchdog and the execute checks

Status: complete. One commit: c946bf5 (`docs(38-23): supervision flags, run lock, watchdog, execute checks and caller rules in
ai-kit-cross-ai, locked to --describe`, Tasks 1 to 3 in one cross-AI lane, pi router-env/my-coding, status=ok, 288 s).

## What changed

- skills/ai-kit-cross-ai/SKILL.md: the description clause `ends locked or partial, prints retry_after_s= or a finding`; the `--describe`
  sentence names `statuses`, `findings` and `supervision_flags`; new subsections `### Supervision flags` (five rows, the three CONFIG keys
  and the seed rule), `### Run lock`, `### A hosted lane's run safety`, `### Idle watchdog`, `### Execute result checks` (the numbered
  nine-row finding table and the precedence paragraph); the exit table with backticked statuses plus `partial` (1) and `locked` (75); the
  bare-75 paragraph names the run lock; the `coverage=` and `findings=` bullets; the `partial`/`locked` caller paragraph and the helpers
  paragraph in section 5; three Pitfalls bullets replace the watchdog denial; five Evidence lines. Structure and heading order unchanged,
  `## Evidence` last.
- skills/ai-kit-cross-ai/references/launch-and-wait.md and the two SKILL.md sample lines: ` coverage=- findings=-` after `escalate=-`.
- skills/ai-kit-cross-ai/evals/evals.json: `edge-locked-is-a-bare-75`, `edge-partial-resume-with-missing-list` (8 cases).
- tests/test_cross_ai_settings_text.py: `STATUS_HEADING`, `FINDINGS_HEADING`, `FLAGS_HEADING`, `status_rows`, `finding_rows`,
  `flag_rows`, `runner_statuses`, `runner_flags`; `group_problem` requires the check group and a valid `coverage`; class `SupervisionDocs`
  with the eight tests the plan names (status, finding and flag sets equal the runner source and `--describe`, drift cases, rule texts,
  figures once, no watchdog denial, dates only under Evidence).

## Verification (run by the chunk agent)

- Acceptance greps: the five subsections, the row `| 9. | `coverage_unchecked` | info |` and `` `quota`, `transient`, `locked` `` once each;
  `coverage=- findings=-` twice in SKILL.md and once in launch-and-wait.md; `250 ms` and `twice the capture cap` once each; last heading
  `## Evidence`; evals.json 8 cases.
- The texts the plan quotes were checked against the runner at 083317b before the lane ran (idle, lock, stale, orphan, sweep, finding,
  no-tree-change and heartbeat messages; `STATUS_TABLE`, `FINDING_CODES`, `SUPERVISION_FLAGS`; `--baseline`, `--idle-timeout`, `--plan-id`
  parsing; lock path and modes; re-read 2 s; poll 250 ms; check interval; the status-line group order; `parseTasks`, `stripCode`,
  `executeFindings`, the run record fields and label).
- `tests.test_cross_ai_settings_text` (23, the `SupervisionDocs` describe legs ran, none skipped), `tests.test_cross_ai_skill_text`,
  `tests.test_skill_text_history`, `tests.test_quota_policy_text`, `tests.test_arch_hardcoded_models`, `tests.test_skill_frontmatter`,
  `tests.test_skill_evals_shape` pass; `make ruff`, `make pyright`, `make vulture` passed in the lane; the commit hook ran 14/14 modules.
  No runner, sibling, detection.py or baseline change. No docs outside this plan still deny the watchdog or show an `AIKIT-XAI` sample
  without the check group.

## Deviations

- One commit for the three tasks (the plan names one per task).
- Planned tasks: the runner's `parseTasks` counts every task type that is not a checkpoint type and treats a task whose files are all glob
  patterns as unchecked, so the sentence says `whose type is absent or not a checkpoint type` and `a task with no files, or only glob
  patterns, is unchecked` instead of the plan's `auto`, `tdd` or absent.
- No host output timing was measured (38-SPIKE.md records claude, opencode, pi text and pi json as not probed), so the watchdog text ends
  `Output timing per host is unverified: ... were not measured (see Evidence).` and the Evidence line uses the plan's not-measured form.
- `test_supervision_text_names_each_rule` checks `never in a loop` case-insensitively (the sentence starts with a capital).
