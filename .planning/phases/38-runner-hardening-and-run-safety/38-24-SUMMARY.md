# 38-24 Summary: the runner docs outside the cross-ai skill name the new statuses, flags, checks and sweep

Status: complete. One commit: b879e6e (`docs(38-24): runner statuses, supervision flags, the sweep and the watchdog in
cross-ai-dispatch.md, runner.md, README and curated-config SKILL.md`, Tasks 1 and 2 in one cross-AI lane, pi router-env/my-coding,
status=ok, 301 s).

## What changed

- skills/ai-kit-spec-review/references/cross-ai-dispatch.md: the `real_error` row gains `partial` and `locked`; the status-line paragraph
  names the check group `coverage`/`findings` and the `cross-ai: finding` lines; a `**Run safety.**` paragraph (review lanes take no lock,
  the review note, the opt-in watchdog, the sweep and its complete-label rule).
- skills/ai-kit-gsd-curated-config/references/runner.md: the `--describe` wording, the sweep sentence in the host bullet, a supervision-flags
  bullet (`locked`, `partial`, `coverage=`, `findings=`), the CONFIG keys sentence with `idleTimeoutS`, `forbiddenPaths`,
  `admissionPhrases`, the watchdog sentence after the live timeout.
- README.md: the ai-kit-cross-ai row names the watchdog, the run lock (`locked`), the execute checks (`partial`) and `--sweep`; the
  curated-config row names the run lock and the execute checks (`template-9` unchanged; plan 38-25 bumps it).
- skills/ai-kit-gsd-curated-config/SKILL.md: the runner exit sentence (`partial` under 1, `locked` under 75, the idle watchdog under 124);
  step 3 gains the timeout sentence and the `router_confirmed` sentence; the `**Refusals `--force` cannot bypass:**` bullet describes the
  gsd-core check at apply.
- tests/test_cross_ai_docs_text.py: `ERROR_CLASSIFIER_DIR`, `CURATED_SKILL`, `SUPERVISION_FLAGS`, `dispatch_status_names`,
  `runner_status_names`; the README test extended; class `SupervisionDocsText` with seven tests (the dispatch table covers every
  `STATUS_TABLE` name, `partial`/`locked` map to `real_error` in the doc and in `STATUS_TO_REASON`, check group and sweep texts, runner.md
  flags and CONFIG keys, a non-vacuity case, the curated step-3 and refusal texts, the curated exit sentence).

## Verification (run by the chunk agent)

- Acceptance greps: the dispatch row and `**Run safety.**` once each; runner.md holds `idleTimeoutS`, `--sweep`, `--plan-id <id>`; README's
  cross-ai row holds `the run lock (`locked`)` once; the curated SKILL.md diff touches only the exit paragraph, the step-3 paragraph and the
  refusals bullet.
- Every doc sentence was checked against the code before the lane ran: `STATUS_TABLE` exits, `STATUS_TO_REASON` (error_classifier.py),
  `sweepRuns`, the review note, `planIdle`, `--sweep` (no spawn, no lock, exit 0), `cross_ai.timeout_why`/`timeout_ok` and recommend's
  `existing` field, `model_heuristics.router_statement`, apply's `prepare`/`_skill_check` and `plan_io.gsd_skipped_skill_problem`, 38-27's
  plan-edit note.
- `tests.test_cross_ai_docs_text` (17), `tests.test_cross_ai_skill_text`, `tests.test_cross_ai_settings_text`, `tests.test_skill_text_history`,
  `tests.test_arch_hardcoded_models`, `tests.test_ai_kit_gsd_curated_config`, `tests.test_quota_policy_text` pass; `make ruff`, `make pyright`,
  `make vulture`, `make pylint` passed in the lane; the commit hook ran 149/149 modules (the curated-config matrix deferred to push; the chunk
  agent runs it before the fold).

## Deviations

- One commit for both tasks (the plan names one per task).
- Refusals bullet: the plan said to keep its first sentence, but since 38-27 `plan-set` and `plan-unset` no longer refuse (they print
  `the skipped-skill check runs at apply (plan-set has no project root)`), so the first sentence now says `apply` and `apply --dry-run`
  refuse and plan edit only notes; the four sub-bullets became one sentence on gsd-core's `buildAgentSkillsBlock`, with the skip cases the
  code names (no project-local gsd-core, pi, gsd-core cannot answer). No sub-bullet was kept: 38-06 and 38-27 leave no local check.
- Timeout sentence: the code replaces any value that is not an integer of at least 1800 (booleans, floats and text included) and the
  entry's reason says why, so the sentence says that instead of the plan's "below 1800 ... shown as invalid".
- runner.md `--describe` part: the bullet's real text was replaced in place (the plan's anchor omitted the `--argv-file` part before it).
- The curated SKILL.md sentences keep the paragraph's existing line breaks, so three lines run past the file's usual wrap.
