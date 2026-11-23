# 38-05 Summary: the quota_cycle class and the one classifier object

Status: complete. Commits 4dd1574 (`feat(38-05): the classifier object with quota_cycle; locked and partial map to real_error`, Tasks 1 and 2) and af2b6fe (`feat(38-05): quota_cycle class, classifier object and its one caller`, Task 3: class, CLI output and every caller text in one commit). Executed through two cross-AI lanes (pi router-env/my-coding), each status=ok on its first run (275 s, 266 s).

## What changed

- `dispatch_injection.py`: `RUNNER_ONLY_STATUSES = ("locked", "partial")`, `_whole_token` (non-negative ints or 1 to 15 digit strings), `dispatch_classification` returning `{"class", "retry_after_s", "cycle"}` (`locked`/`partial` real_error by name first; exit 0 ok; exit 75 with both whole tokens quota_cycle; 69/75 transient-or-quota with no malformed token, or reason quota, is quota; else real_error); `classify_dispatch_failure` is now its class projection.
- `cli.py`: `classify-dispatch-failure` prints the JSON object.
- `error_classifier.py`: `STATUS_TO_REASON` maps `locked` and `partial` to `real_error`.
- `dispatch-external-cli.md`: one classifier call, its `CLASSIFICATION` appended to `$SCALARS`; the three token `python3 -c` parses and their printf are gone; branch, Write state, Schedule-or-stop and the wake time read `$CLASSIFICATION`. `escalation.md`, `state-management.md` and `SKILL.md` name `quota_cycle` beside `quota` (class names only).
- Tests: `TestDispatchClassificationTable` (22 rows, purity, projection), renamed and replaced methods in `TestClassifyDispatchFailure` and `TestCliClassifyDispatchFailure` (every row through the CLI), `test_reference_classifies_once`, updated text pins; two rows in `test_reason_for_status_maps_named_statuses`.

## Verification (run by the chunk agent)

- Acceptance greps all at their expected counts (one `classify-dispatch-failure`, no token parse, no `RETURNCODE=` line, seven `python3 -c` left in the out-of-scope fold blocks, `quota_cycle` twice in SKILL.md); no grok text; baseline and detection.py untouched.
- tests.test_ai_kit_spec_superpowers (173), tests.test_ai_kit_spec_runtimes_table (59), tests.test_quota_policy_text (19): all pass. Lanes ran make ruff, pyright, vulture, pylint (exit 0); hooks passed (134/134 and 17/17 covering modules).

## Deviations

- The two `quota` branches of `dispatch_classification` are one `elif` joined by `or` (ruff SIM114); order and outcome are the plan's.
- The edited SKILL.md line 263 and some reference lines run past 100 columns (not rewrapped); cosmetic, left for code review.
- Handoff: SKILL.md of ai-kit-spec-execute-superpowers changed (class names), so 38-26's materiality check decides its judge loop; 38-13 and 38-18 rely on the `locked`/`partial` rows.
