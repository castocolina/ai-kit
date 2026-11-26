---
phase: 40-resilient-review-sized-by-jev
plan: 07
subsystem: ai-kit-spec-review (review sizing from deterministic signals and jev)
tags: [review, jev, sizing, signals, advisory]
requires: [40-06]
provides:
  - "ai_kit_spec/review_signals.py: SIGNAL_NAMES, plan_paths (superpowers path lines and GSD files blocks), plan_signals (word-bounded security/data/irreversible patterns over text and paths; migrations/ and .sql paths raise data), plan_facts (tasks, files, steps, complexity bucket)"
  - "jev_review.py: SizeInput, Sizing, _confident (shared with route_for), _with_second_lane (the second entry of quota.resolve_reviewers on a forced-double config copy over routing.unroutable_quota), _label, sizing_items (numbers, fixed labels, opaque p1..p5 tokens; reviewer item only with two or more candidates), _apply_answers, size_review, cmd_size_review and the size-review subcommand"
affects: [40-09, 40-10, 40-11, 40-13]
key-files:
  created:
    - skills/ai-kit-spec-review/ai_kit_spec/review_signals.py
    - tests/test_review_signals.py
    - tests/fixtures/review_signals/security_plan.md
    - tests/fixtures/review_signals/plain_plan.md
    - tests/fixtures/review_signals/data_plan.md
    - tests/fixtures/review_signals/irreversible_plan.md
  modified:
    - skills/ai-kit-spec-review/ai_kit_spec/jev_review.py
    - tests/test_jev_review.py
    - Makefile
    - .pre-commit-config.yaml
decisions:
  - "The added lane is the resolver's own second entry (no second eligibility predicate); jev never sees a lane key, model, vendor, path or plan text; size-review writes reviewers.json only when the rows change and appends the round-0 sizing event after that write"
metrics:
  tasks: 3
  commits: 4
---

# Phase 40 Plan 07: review sizing Summary

`size-review` sizes a review before round 1. Deterministic signals over the plan text and its file paths (`security`, `data`,
`irreversible`, word-bounded, case-insensitive) force two lanes without asking jev; the second lane is the second entry that
`quota.resolve_reviewers` picks in forced double mode over the route-overlaid quota cache with the host's own `--source-vendor`
and `--cross-ai`, so a quota-excluded, undispatchable or execute-purpose lane is never added, and a missing second lane is said in
the reason. Without a signal, jev (when present) answers `lanes` (one or two) and, with two or more candidate rows, `reviewer`
over opaque tokens mapped back locally; only confident answers apply. No jev, a low or failed answer keeps reviewers.json as it is.
The command prints `sizing: <n> lane(s): <reason>` and appends one round-0 sizing event to the lane log.

## Commits

| Task | Commit | Subject |
|------|--------|---------|
| 1 | 1a8e8da | feat(40-07): size the review from deterministic signals and jev |
| 2 | 882a24a | test(40-07): pin the review signals and plan facts on held-out fixtures |
| 3 | 2dedcb3 | test(40-07): pin jev sizing, the floor of two and the roster rule |
| 3 fix | 32dd63f | test(40-07): anchor the sizing payload shape check |

Cross-AI lanes (pi, router-env/my-coding), one per task from the start, each AIKIT-XAI `status=ok attempts=1`: Task 1 467 s,
Task 2 185 s (its hook ran the full unit and arch groups, 202/202), Task 3 90 s, fix-up 29 s.

## Verification (chunk executor, own runs)

- Task 1 acceptance: the three `def` lines in review_signals.py 3, the seven in jev_review.py 7, `quota.resolve_reviewers(` 1,
  `routing.unroutable_quota(` 1, no `resolve_ladder_pick|def eligible_keys|role_orders` (exit 1), `--source-vendor` 1,
  `"size-review"` 2, `--quota-path` 1, `migrate=False` 1, no `usage_limited|SKILLS_ROOTS|JEV_ENTRY_REL` (exit 1), subject ok.
- Task 2 acceptance: `def test_` 7, `test_review_signals` in the Makefile 1 (pre-commit listing 2), subject ok; one TRIGGERS row
  per pattern alternative plus `drop database` and `SQL injection risk`.
- Task 3 acceptance: `def test_` 26, the two E10 tests 2, `class TestSizeReview` 1, `SIZE_CONFIG` 7, no `SizeInput(CONFIG`
  (exit 1), subject ok; every pinned key list and reason string matches the plan text.
- No added line names a phase, plan or decision id; no line over 100 characters; review_signals.py does no I/O.
- `tests.test_jev_review` 26, `tests.test_review_signals` 7, `tests.test_gate_scope` 62, `tests.test_ai_kit_spec` 703,
  `tests.test_lane_settings` 50, `tests.test_arch` 118, `tests.test_arch_hardcoded_models` 23: all ok.
- Gates after the plan (at 32dd63f): unit + arch groups under the watchdog `198/198 modules passed` (peak 8 runner processes,
  not killed); `make ruff`, `make pyright`, `make vulture`, `make pylint`, `make check-dogfood` exit 0 each; the commit-deferred
  `tests.test_ai_kit_gsd_curated_config_matrix` 35 tests ok (163.3 s, under the watchdog, peak 0).

## Deviations

- The plan's cli.py line numbers were stale (`resolve-reviewers` parser 307-311, `_cmd_resolve_reviewers` 985); the lanes got
  corrected anchors and a probe of the roster through `cfg_resolve` and the forced-double resolver.
- Task 1 (lane): a `_read_size_inputs` helper reads reviewers.json and the documents; `_apply_answers` keeps the rows for a
  choice other than one or two; the sizing-event append shares the write's `OSError` branch (exit 2).
- Task 2 (lane): the test module docstring drops the word "deterministic" (line length).
- Task 3 (lane) checked the payload shape with `assertRegex` (a search); the plan says fullmatch, so a fix-up lane anchored it
  (32dd63f). The same search-style check in the 40-06 payload test stays open for code review.
