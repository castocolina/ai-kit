---
phase: 32-re-judge-baseline
reviewed: 2026-11-07T00:00:00Z
depth: standard
files_reviewed: 32
files_reviewed_list:
  - .pre-commit-config.yaml
  - AGENTS.md
  - Makefile
  - README.md
  - agents/ai-kit-judge.md
  - skills/ai-kit-cross-ai/SKILL.md
  - skills/ai-kit-gsd-curated-config/SKILL.md
  - skills/ai-kit-gsd-spec-discuss/SKILL.md
  - skills/ai-kit-gsd-spec-discuss/references/decision-table.md
  - skills/ai-kit-gsd-spec-discuss/references/log-formats.md
  - skills/ai-kit-gsd-spec-discuss/references/worked-examples.md
  - skills/ai-kit-spec-config/SKILL.md
  - skills/ai-kit-spec-execute-superpowers/SKILL.md
  - skills/ai-kit-spec-review-checklist/SKILL.md
  - skills/ai-kit-spec-review/SKILL.md
  - skills/ai-kit-usage-metrics/SKILL.md
  - skills/jev-fast-decision/SKILL.md
  - skills/jev-fast-decision/backends/laya.md
  - skills/jev-fast-decision/backends/typesafe.md
  - tests/test_arch.py
  - tests/test_check_dogfood.py
  - tests/test_curated_config_apply.py
  - tests/test_gate_scope.py
  - tests/test_judge_loop.py
  - tests/test_rules_docs.py
  - tests/test_setup.py
  - tests/test_skill_frontmatter.py
  - tests/test_skill_frontmatter_pyyaml.py
  - tests/test_skill_text_history.py
  - tools/check_dogfood.py
  - tools/judge_loop.py
  - tools/run_unittest_parallel.py
findings:
  critical: 0
  warning: 0
  info: 2
  total: 2
  necessity: 0
status: issues_found
---

# Phase 32: Code Review Report

**Reviewed:** 2026-11-07
**Depth:** standard
**Files Reviewed:** 32
**Status:** issues_found

## Summary

This is iteration 3, the last re-review. The 32 files were all reviewed in iterations 1 and 2.
Since then only `tools/judge_loop.py` and `tests/test_judge_loop.py` changed, in commit `749be77`.
This pass focuses on that commit. Locked decisions D-01 to D-22 were not flagged.

Evidence gathered (scripts `tmp/auto/p32-close/rereview_iter3.py` and
`tmp/auto/p32-close/rereview_iter3_tests.sh`, run with `AI_KIT_REFUSE_REAL_HOME=1`; every probe
ran on a throwaway copy of `.planning/judge`, and each copy was removed afterwards):
- `tests.test_judge_loop`, `tests.test_check_dogfood` and `tests.test_skill_frontmatter`: 161
  tests passed. ruff is clean, and pylint gives `tools/judge_loop.py` 10.00/10.
- On the live records, `check` exits 0. `check --gate --require-current` prints the four
  `bar not met` lines and exits 1. It prints no REJUDGE.md line, so the report was compared and
  matches.
- A record with `"judge": 5` now gives `not a judge record (wrong type: judge)`, with no traceback,
  under both `check` and `report`.
- A record whose `attempts` list holds a string still ends `check` and `report` in an
  `AttributeError` traceback (IN-01).
- A pool probe without `"judge"` in `loops/32.json` makes `check` print
  `REJUDGE.md not checked: KeyError: 'judge'`, which names no file. `report` ends in a `KeyError`
  traceback (IN-01).

Status of iteration 2's findings:
- **IN-01: partly resolved.** `_load_record_file` now refuses a wrong-typed
  `skill`/`judge`/`digest`/`round`/`prompt_sha256`/`attempts`, and a non-dict
  `verdict`/`substitute`, with a named `JudgeLoopError`. A test covers it. Two gaps remain: the
  contents of `attempts` and the pool probes. Iteration 2's `_pool_lines` fix was not applied. The
  ingest path is IN-02.
- **IN-02: resolved.** `check` always calls `_report_problems`. The two old test assertions now
  expect the `REJUDGE.md not checked: ...` line. A new test proves that the comparison still runs
  next to another problem. The live `--gate --require-current` run confirms it.
- **IN-03: resolved.** `atomic_write_text` catches `BaseException`, removes the temp file and
  re-raises. The new test writes a lone surrogate and checks that the folder is left empty.
- **IN-04 (`worked-examples.md` placeholders)** and the hardcoded `JEV_CALLER` in
  `jev_ladder.py` are deferred on purpose. They are not counted here, as the brief directs: phase
  32.4 owns that skill, and any `skills/` edit would make the baseline digests stale.

The commit introduced no regression. No Critical or Warning finding remains. In every case below
the gate still exits non-zero, so nothing gets through. What is left is the message the user sees.

## Narrative Findings (AI reviewer)

## Info

### IN-01: Two record shapes still end `check`/`report` in a traceback or an unnamed problem line

**File:** `tools/judge_loop.py:613-615, 894-897, 944, 1177-1180`; `tools/check_dogfood.py:601-603`
**Issue:**
1. `RECORD_TYPES` checks that `attempts` is a list, but not that its items are dicts.
   `_verdict_row` (l.896-897) calls `last.get(...)` on the last item. With `"attempts": ["x"]`,
   `check` and `report` both end in `AttributeError: 'str' object has no attribute 'get'`
   (reproduced). The new `except (KeyError, TypeError, ValueError)` in `_report_problems` does not
   catch `AttributeError`, and neither does `main` (l.1704). `check_dogfood.check_judge_records`
   (l.601) does not catch it either, so the pre-push `check-dogfood` hook also prints a traceback.
2. `_pool_lines` (l.944) still reads `p["judge"]` and `p["usable"]`. Under `check`, a probe without
   `judge` becomes `REJUDGE.md not checked: KeyError: 'judge'`, which names neither the file nor
   the probe. Under `report` it is a traceback (reproduced). The new comment at l.1178 says "the
   record checks above already named it". That is not true here: no check reads the pool probes.
**Fix:** Keep the fix at load, as the commit does. In `_load_record_file`, add
`attempts` items that are not dicts to `wrong`:
```python
if isinstance(record["attempts"], list) and not all(isinstance(a, dict) for a in record["attempts"]):
    wrong.append("attempts")
```
In `_pool_lines`, use `p.get("judge")` and `p.get("usable")` (the `_cell` renderer already shows
`None` as `-`). Then reword the l.1178 comment to "a loop or record field the render cannot read".

### IN-02: Ingest's `_load_record` still crashes on a partial record, though the brief says those are refused

**File:** `tools/judge_loop.py:555-570, 590`
**Issue:** The brief says ingest keeps `_load_json` "because a partial record in ingest is refused
by those checks" (the judge, verdict and digest checks). That holds only when one of those fields
differs. Four cases get past them:
- An existing record with the right `judge`, `digest` and `prompt_sha256`, `verdict: null`, and no
  `attempts` key passes all three checks. It then hits `record["attempts"].append` at l.590 and
  raises `KeyError`. `main` does not catch `KeyError`, so the user gets a traceback.
- The same record with `attempts` set to a string raises `AttributeError` at the same line.
- A record file that holds a JSON list raises `AttributeError` at `record.get` (l.560).
- A record that is missing only, say, `schema` passes the checks. Ingest appends the attempt and
  writes the record back, still partial. `check` refuses it later as `not a judge record`.

No data is lost, because every crash happens before `atomic_write_json`. The cost is a traceback
in place of a named error, plus a partial record that check then rejects.
**Fix:** One line: in `_load_record`, call `_load_record_file(path)` in place of `_load_json(path)`.
Every record that ingest writes has all `RECORD_KEYS` (`_new_record` adds the three that the
manifest lacks), so valid records still load. The judge, verdict and digest checks stay as they
are.

---

_Reviewed: 2026-11-07_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
