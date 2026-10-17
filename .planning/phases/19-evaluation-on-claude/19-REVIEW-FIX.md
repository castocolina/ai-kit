---
phase: 19-evaluation-on-claude
review: 19-REVIEW.md (gsd-code-reviewer) and the ponytail code review (H/M/L ids)
fixed_in: tests/gsd_curated_eval.py, tests/test_gsd_curated_eval.py, evals 01/03/04, three e2e/unit test modules
red_green: TestReviewFixes, 25 tests; all 25 fail on the pre-fix grader and pass after
---

# Phase 19: Code Review Fixes

## Fixed

- CR-01: a dry run counts only when its rows reached the user in an earlier turn than the apply: the dry run itself, or an earlier-turn dry run with the same diff rows. Row-shown checks (`remove_rows_shown`, `full_diff_shown`, `nothing_dropped_silently`, `review_pass_shown`) read only text from earlier turns.
- CR-02: the record stores only product reports (`dry_run`/`applied`/`results`/`required`). The agent env is an allowlist (`CELL_ENV_KEEP` plus the fixture env and HOME), not `os.environ`. `SECRET_RX` now covers `apiKey`/`token`/`secret` JSON keys in any case, `*_TOKEN=`, `*_SECRET=`, and the `ghp_`, `glpat-`, `xai-` and `AIza` prefixes. The self-check plants one canary per shape. All committed evidence scans clean under the wider pattern.
- CR-03: `_run_one_turn` kills the child's process group in a `finally`, so an interrupt kills it too.
- WR-01 / H1: verbs are read per command segment by `calls()`, which needs an interpreter or script word. `grep config-set` is no write, and a chained `apply --dry-run && apply` is a write and a real apply.
- WR-02: evals 01, 03 and 04 gained a fourth scripted answer that approves the follow-ups. Eval 03's turn-2 answer now also answers the open trusted-roots choice; opus D never applied without it (19-09 owner-review item).
- WR-03: smoke placeholders run longest-first (projects, work dir, worktree, resolved home, home).
- WR-04: the transcript key is the cwd that init reports, with every non-alphanumeric character mapped to `-`. A live probe confirmed this through `memory_paths.auto`. All candidate forms are deleted, and if the reported key is missing the run records a harness failure. `.claude.json` is checked in both path forms.
- WR-05: the reaper matches the run dir only as a whole path word.
- WR-06: `snapshot` checks its mode before reading the home.
- WR-07 / M1 / M2: the keep-count rule is gone; SKILL.md never asked for keep rows. A follow-up row is named by its id, full purpose or full argv. One ask pattern: a word-final `?` (not `$?`, not inside a URL), `please` only before a request verb, plus the offered-choice rule (`_asks`) in C and E. `router_wins_execution` reads the first preferred runner's model.
- WR-08 / L1: history rows are found by cell (`context`, or a status ending in `superseded (...)`); `_status` is deleted.
- H2 / L6 / L7: the smoke matrix step fails on a failing matrix. Evidence prints each control's `ok`/`FAILED`, the renderer names control-2 mismatches, and `_cmd_matrix` computes the verdict once.
- M3: one `_PREDICATES` table replaces the six dispatch functions; a test pins it to `CHECKS`.
- IN-01, IN-03: corrected the stale docstring and the 1.16/1.17 claims (checked once, key parity re-checked).
- IN-02 / L12, L13: dropped the unused matrix scratch dir; `TestRealApply` uses `_gsd16_or_skip`.
- IN-04: `RunSeams.version_fn`.
- IN-05 / M8: project (b) records reconciled key paths only; the test drives `_smoke_project_b`.
- IN-06 / M7: a redirected report is read only from inside the run dir.
- IN-08: the shadow check uses `commonpath`.
- IN-09: `run --snapshot F` adds a strict protected-set change to the harness failures.
- IN-10: every turn's init is gated: only `builtin` plugins, and no memory beyond `auto`.
- L2, L3, L8, L11, L14: dead `None` checks, the version alias, router literals and the `KEEP_LIMIT` alias are removed; SKILL.md's family list is pinned to `MANAGED_PREFIXES`.

## Not fixed

- IN-07 (SKILL.md wording): a product change re-binds the digest, every GREEN cell and both judges. It is listed for owner review with the next SKILL.md revision.
- M4, M5 (duplicate helpers), L5 (pylint comments), L9 (shadow tokenizer), L10: refactors of the dev-only harness with no behavior change, deferred. The two tree hashers treat symlinks differently, so merging them first needs a decision on which behavior is right.
- M6: the root cause is in `tests/test_ai_kit_gsd_curated_config.py`, which Run rule 8 forbids editing. `product_module` stays.
- L4 (`inheritance_promised`): kept for Phase 20, where non-claude hosts can promise an empty model.

## Effect on committed evidence

The grader and the scripted answers changed, and the run dirs of the committed GREEN records were deleted in 19-10. So every GREEN cell (B-E, sonnet and opus) is re-run on the unchanged digest; see `19-PRESSURE-TESTS.md`.
