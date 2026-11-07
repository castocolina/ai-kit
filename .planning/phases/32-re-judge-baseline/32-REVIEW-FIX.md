---
phase: 32
fixed_at: 2026-11-07T00:00:00Z
review_path: .planning/phases/32-re-judge-baseline/32-REVIEW.md
iteration: 3
findings_in_scope: 0
fixed: 0
skipped: 0
status: all_fixed
---

> Iterations 2 and 3 (critical_warning scope): neither re-review found a Critical or Warning
> finding, so the fixer had nothing in scope; the loop ended at its cap of three reviews. The orchestrator fixed the Info findings of both reviews and the
> ponytail-review findings itself; see "Orchestrator fixes" below. Iteration 1 follows unchanged.

# Phase 32: Code Review Fix Report

**Fixed at:** 2026-11-07
**Source review:** .planning/phases/32-re-judge-baseline/32-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 5 (the orchestrator accepted WR-05, a necessity finding, as fix-now)
- Fixed: 5
- Skipped: 0

**Verification:** run in the main checkout (`use_worktrees` is not set to false, but the
orchestrator asked for the main checkout and no other writer ran), on branch
`gsd/phase-32-re-judge-baseline`. Each fix ran `python3 -m unittest tests.test_judge_loop
tests.test_check_dogfood` (146 tests, OK) and the pre-commit hooks (ruff, pylint, py-compile,
staged tests: test_arch, test_check_dogfood, test_judge_loop). No file under `skills/` was touched.

## Fixed Issues

### WR-01: `check` crashes on a malformed record or loop file; `check-dogfood` loses its output

**Files modified:** `tools/judge_loop.py`, `tools/check_dogfood.py`, `tests/test_judge_loop.py`,
`tests/test_check_dogfood.py`
**Commit:** 1e4f96e
**Status:** fixed: requires human verification (logic change)
**Applied fix:**
- New `_load_json` wraps invalid JSON into `JudgeLoopError`; used by `read_loop_file`,
  `load_inputs` and `_load_record`.
- `_judged_state` ranks only records whose verdict validates (as `_check_latest` does).
- `check` skips the REJUDGE.md compare when problems exist and adds "REJUDGE.md was not compared:
  fix the record problems first". Side effect: the old "REJUDGE.md not checked: ..." line no longer
  appears next to other problems; `test_a_missing_count_record_is_reported_as_not_checked` now
  asserts the count problem plus the new line.
- `check_judge_records` also turns `OSError, ValueError, KeyError, TypeError` into a
  `judge records: <Type>: <msg>` problem.
- Tests: verdict without `findings`, finding without `severity`, corrupt `loops/32.json`
  (exit 1, named message, no traceback); check_dogfood returns a problem for a `KeyError`.
- Not changed (left as the orchestrator directed): `_judged_state` and `_check_latest` stay
  separate (IN-01). The `report` command on a record with an invalid verdict still reaches
  `_verdict_row`, which indexes the verdict keys directly; `check` never renders such a record, and
  `main` still does not catch `KeyError`/`TypeError`.

### WR-02: A retried ingest keeps the first attempt's manifest

**Files modified:** `tools/judge_loop.py`, `tests/test_judge_loop.py`
**Commit:** 59f5359
**Status:** fixed: requires human verification (logic change)
**Applied fix:** `_load_record` refuses when the existing record's `digest` or `prompt_sha256`
differs from the manifest ("a changed skill is judged in a new round"). Test: failed attempt, then a
manifest with another digest; ingest exits 1 and the record keeps one attempt and no verdict.

### WR-03: The verdict-line scan depends on JSON key order

**Files modified:** `tools/judge_loop.py`, `tests/test_judge_loop.py`
**Commit:** 42e3064
**Status:** fixed: requires human verification (logic change)
**Applied fix:** `verdict_lines` keeps a line that starts with `{"skill"` (so `_read_verdict` still
reports "not JSON" for one that does not parse) or any `{` line that parses to a dict holding both
`skill` and `judge`. Test: a verdict with `judge` first and one starting `{ "skill"` are both
recorded.

### WR-04: The jev call's outer timeout equals the ladder's own deadline

**Files modified:** `tools/judge_loop.py`, `tests/test_judge_loop.py`
**Commit:** 0a8051c
**Status:** fixed: requires human verification (logic change)
**Applied fix:** `JEV_CALL_TIMEOUT = 30 * (1 + 3) + 10 + 20` (150 s), with a comment that it must
exceed `jev_ladder`'s `CALL_TIMEOUT_SECONDS * (items + 3) + 10` (130 s for one item, verified at
`jev_ladder.py:448-451`). The ask_jev test asserts the timeout is above 130.

### WR-05: Two env values `ask_jev` sets are overwritten by the ladder (necessity)

**Files modified:** `tools/judge_loop.py`, `tests/test_judge_loop.py`
**Commit:** 3d39a5d
**Status:** fixed: requires human verification (removes code)
**Applied fix:** dropped `GSD_PATH_JEV_TIMEOUT_SECONDS` and `JEV_CALLER` from `ask_jev`'s env.
`GSD_PATH_JEV=1` stays: `jev_review.py` returns `disabled` without it before the ladder runs. The
test no longer pins the two dead values.

## Orchestrator fixes (Info findings and ponytail-review)

Triaged through the jev ladder (`tmp/auto/p32-close/jev-review-triage.json`, all "fix now",
laya 0.83-0.99); the one override is noted under "Deferred".

| Finding | Commit | Fix |
|---|---|---|
| Iter 1 IN-01 / ponytail: report and check duplicated the latest-round logic | 4fb8529 | one `_last_round` helper ranks only validated verdicts for both; `report` refuses an invalid verdict with a named error (the fixer's residual) |
| Iter 1 IN-02: records of one round were not checked for one digest | 4fb8529 | `_round_problems` flags a round whose records judged different skill text (live records: 0 mixed rounds) |
| Iter 1 IN-03: `count` numstat compared base..HEAD | 4fb8529 | numstat compares the base with the working tree, as the digest does |
| Iter 1 IN-04: REJUDGE.md written non-atomically | 4fb8529 | `atomic_write_text`, shared with `atomic_write_json` |
| ponytail: `inputs.json` entry without `last_v4`/`old_score` passed the shape check | 4fb8529 | `_entry_error` names the missing keys |
| ponytail: a judge listed twice filled both pool seats | 4fb8529 | `choose_pool` refuses a duplicate judge |
| ponytail: copied test helper, redundant test | 78f0efc | `agent_problems` removed; the test became a label-subset check |
| Iter 2 IN-01: a record field of the wrong type ended `check` in a traceback | 749be77 | `_load_record_file` checks field types and names them |
| Iter 2 IN-02: `check` skipped the REJUDGE.md compare on any problem (gate, stale) | 749be77 | the compare always runs; a render it cannot read is a problem line (this replaces WR-01's "was not compared" skip) |
| Iter 2 IN-03: `atomic_write_text` left its temp file on a non-OS error | 749be77 | the temp file is removed on any exception |
| Iter 3 IN-01: a non-object `attempts` item ended `check` and `report` in a traceback; a pool probe without a judge named no file | 3d51506 | the record loader refuses a non-object attempt; a pool probe or substitute without a judge raises a named error for its loop file |
| Iter 3 IN-02: ingest's `_load_record` let a partial record through to a crash or a partial write | 3d51506 | ingest loads the record through `_load_record_file` (keys and types checked) |

Each fix has a test; `tests.test_judge_loop`, `tests.test_check_dogfood` and
`tests.test_skill_frontmatter` pass (162 tests), ruff, pylint and pyright exit 0, and
`judge_loop.py check .planning/judge --require-current` reports all 15 skills current.

**Deferred:** `worked-examples.md` placeholders (iter 1 IN-05, iter 2 IN-04): any edit under
`skills/` makes the committed baseline digests stale (SPEC R7: every skill current at close); batch
phase 32.4 owns `ai-kit-gsd-spec-discuss`. **Skipped as taste:** ponytail's rule-helper constants
and the per-skill mapper index rebuild (a one-off of about 15 s per round).

## Pre-existing defect outside this phase (not fixed)

`skills/jev-fast-decision/scripts/jev_ladder.py::child_env` (l.418-424) hardcodes
`JEV_CALLER: "ai-kit-gsd-spec-discuss"`, so the answer log attributes the judge-count call to that
caller. Fixing it (keep an incoming `JEV_CALLER`) is a change under `skills/`, which would make the
committed baseline verdicts stale, so it was not touched.

---

_Fixed: 2026-11-07_
_Fixer: Claude (gsd-code-fixer), iteration 1; orchestrator, Info and ponytail fixes_
_Iteration: 3_
