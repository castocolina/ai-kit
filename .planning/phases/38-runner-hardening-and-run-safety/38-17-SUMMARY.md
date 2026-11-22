# 38-17 Summary: the pure execute check

Status: complete. One commit through one cross-AI lane (pi router-env/my-coding), status=ok on its first run: b7381ed
(`feat(38-17): the pure execute check: tasks, coverage, admissions, forbidden paths, findings, --forbid and --plan-id`, Tasks 1 to 3, 380 s).

## What changed

- skills/ai-kit-spec-review/references/cross-ai.mjs: `ADMISSION_PHRASES_SEED` (the 18 D-13 phrases, labeled judged, recall unverified),
  `FORBIDDEN_PATHS_SEED` (`.planning/STATE.md`, `.planning/ROADMAP.md`, `.planning/REQUIREMENTS.md`), `PLAN_ID_RE`; `pathCovers` (whole
  components, a trailing `/` covers its directory), `parseTasks` (one forward scan, every type except `checkpoint*` counts, an unclosed planned
  block counts unchecked), `planSubjectRe` (port of gsd-core's zero-padding subject rule, a plan half holding `-` matched literally),
  `coverageOf`, `stripCode` (CommonMark fences and inline spans), `admissionHits`, `forbiddenHits`, `planFindings` (findings in `FINDING_CODES`
  order, `contract_violation` beats `partial`, informational codes never block); `--forbid` (repeatable; refuses an absolute path, an empty, `.`
  or `..` segment or a control character without echoing the value) and `--plan-id` (must match `PLAN_ID_RE`) in `parseArgs`; the new names in
  the export list. Nothing calls the functions yet (plan 38-18 wires them).
- skills/ai-kit-spec-review/references/cross-ai-selftest.mjs: helpers `tag`, `PLAN3` (plus local `equal`, `task`, `defaults`, `refusal`); 29 logic
  cases: the 19 `pure-*` cases of Tasks 1 and 2, six usage rows plus the standalone `vocab-forbid-control`, `vocab-forbid-plan-id-ok` and
  `pure-plan-id-regex`.

## Verification (run by the chunk agent)

- Acceptance greps: every named function, constant, flag branch and message once, `label judged` present; `node --check` on both files.
- The 29 cases plus `vocab-session-empty` and `ok` print `self-test ok`; `--self-test-list` 720 lines, the 29 names all `logic`.
- `--print-argv` of six calls byte-equal to fe97b14; `tests.test_arch_hardcoded_models`, `tests.test_runner_describe`, `tests.test_arch` and
  `tests.test_cross_ai_render_sync` pass; detection.py and the model-literal baseline unchanged; runner and sibling diffs reviewed against the plan.

## Deviations

- `vocab-forbid-control` is a standalone case: the shared usage-row check only tests the message line, and the case must also prove that no
  stderr line carries U+009B.
- The `PLAN3` fixture and the `pure-tasks-empty-files` input omit the plan's cosmetic newlines between tags (same parse result).
- The seed comments are shorter than the plan's quoted text (the admission seed keeps `label judged` and `recall unverified`; the forbidden seed
  names GSD execute-phase and the 999.15 list without the exact document path and verification date): open for code review.
- The plan's `selftest.sh` (bare `node` under a scratch HOME, the Volta-shim fork hazard) was replaced by `tmp/run-2026-11-19/p38-17/selftest.py`.
- One commit for all three tasks (the chunk's lane prompt) instead of one per task.
