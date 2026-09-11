---
phase: 06-agents-md-rules-checker-skill
verified: 2026-09-11T00:00:00Z
status: passed
score: 4/4 ROADMAP truths verified; 1 plan-level must-have (quality-gate cleanliness) now passes
covered_files:
  - ".planning/REQUIREMENTS.md"
  - ".planning/phases/06-agents-md-rules-checker-skill/06-01-PLAN.md"
  - ".planning/phases/06-agents-md-rules-checker-skill/06-01-SUMMARY.md"
  - ".planning/phases/06-agents-md-rules-checker-skill/06-02-PLAN.md"
  - ".planning/phases/06-agents-md-rules-checker-skill/06-02-SUMMARY.md"
  - ".planning/phases/06-agents-md-rules-checker-skill/06-03-PLAN.md"
  - ".planning/phases/06-agents-md-rules-checker-skill/06-03-SUMMARY.md"
  - ".planning/phases/06-agents-md-rules-checker-skill/06-CONTEXT.md"
  - ".planning/phases/06-agents-md-rules-checker-skill/06-REVIEW.md"
  - ".planning/phases/06-agents-md-rules-checker-skill/deferred-items.md"
  - ".pre-commit-config.yaml"
  - "Makefile"
  - "README.md"
  - "pyproject.toml"
  - "skills/ai-kit-agents-md-rules-checker/SKILL.md"
  - "skills/ai-kit-agents-md-rules-checker/ai-kit-agents-md-rules-checker.py"
  - "skills/ai-kit-agents-md-rules-checker/ai_kit_agents_md_rules_checker/__init__.py"
  - "skills/ai-kit-agents-md-rules-checker/ai_kit_agents_md_rules_checker/cli.py"
  - "skills/ai-kit-agents-md-rules-checker/ai_kit_agents_md_rules_checker/makefile_checker.py"
  - "skills/ai-kit-agents-md-rules-checker/ai_kit_agents_md_rules_checker/remediation.py"
  - "skills/ai-kit-agents-md-rules-checker/ai_kit_agents_md_rules_checker/rule_checker.py"
  - "skills/ai-kit-agents-md-rules-checker/ai_kit_agents_md_rules_checker/rules.py"
  - "skills/ai-kit-agents-md-rules-checker/ai_kit_agents_md_rules_checker/stack_cache.py"
  - "skills/ai-kit-agents-md-rules-checker/ai_kit_agents_md_rules_checker/stack_detect.py"
  - "skills/ai-kit-agents-md-rules-checker/ai_kit_agents_md_rules_checker/tool_presence.py"
  - "tests/test_ai_kit_agents_md_rules_checker.py"
covered_digest: "v1:sha256:d838ded58aa19eb23a5ebe383c6ef227a84ccfeef31483e4cbfb3ec8cd2fa230"
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: gaps_found
  previous_score: "4/4 ROADMAP truths verified; 1 plan-level must-have failed"
  gaps_closed:
    - "make validate's failures are limited to the pre-existing, documented, out-of-phase files — Phase 6's own code (stack_cache.py) no longer introduces a new pyright failure. Fix commit 6271a5d added an explicit isinstance(cached_at, str) guard before the fromisoformat() call, which pyright now type-checks cleanly (0 errors), while preserving identical runtime behavior (a non-str cached_at previously fell through to the try/except TypeError branch and returned 'stale'; it now returns 'stale' directly via the new isinstance guard — same outcome, same data payload, no branch reordering that changes observable behavior)."
  gaps_remaining: []
  regressions: []
advisory:
  - finding: "make validate's ruff hook also fails on tests/test_ai_kit_spec.py (E501/RUF059, unrelated to Phase 6), a fourth file not listed in deferred-items.md alongside the three documented ones (tools/status-line.py, tools/wizard_app.py, tests/test_ai_kit_spec_superpowers.py)."
    category: other
    reason: "Confirmed via git log that test_ai_kit_spec.py was never touched by any Phase 6 commit (b99eee7..6271a5d) and is unmodified in the working tree (git diff/status clean) — its lint failures are genuinely pre-existing and unrelated to this phase's own files (opencode custom-provider / model-catalog work). This is a documentation-staleness gap in deferred-items.md (written before this file accumulated its own lint debt), not a Phase 6 code regression. Recommend deferred-items.md be updated to include this fourth file in a future unrelated cleanup pass; it does not block Phase 6."
    evidence_status: "confirmed via git log/diff — genuinely pre-existing, out of Phase 6 scope"
---

# Phase 6: AGENTS.md Rules Checker Skill Verification Report

**Phase Goal:** Agents working against any repo's AGENTS.md/CLAUDE.md-style instruction file get an automated check against ai-kit's accumulated house ruleset, not just a generic progressive-disclosure refactor.
**Verified:** 2026-09-11
**Status:** passed
**Re-verification:** Yes — after gap closure (commit `6271a5d`)

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria)

Truths 1-4 were fully re-verified in the initial pass (2026-09-11T00:00:00Z, same-day prior report) and are carried forward here with a quick regression check (Step 0 re-verification optimization — full detail preserved below); truth 5 is the item that failed previously and receives full re-verification.

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | SC-1: Missing Makefile targets flagged by name with per-language tool recommendation | ✓ VERIFIED (regression check) | Re-ran `python3 skills/ai-kit-agents-md-rules-checker/ai-kit-agents-md-rules-checker.py check .` — still returns 17 `makefile` findings, identical count to the prior verification pass; `makefile_checker.py`/`stack_cache.py` are the only two Phase 6 files touched by the fix commits, and neither changes the findings shape. |
| 2 | SC-2: Missing workflow rules flagged individually | ✓ VERIFIED (regression check) | Same run returns 15 `workflow` findings, identical to prior pass — `rule_checker.py` untouched by either fix commit. |
| 3 | SC-3: Invocation observably distinct from plain `/agent-md-refactor` | ✓ VERIFIED (regression check) | No change to `SKILL.md` or `agent-md-refactor/SKILL.md` since the prior pass; wrap structure intact. |
| 4 | SC-4: Scaffolded via `/superpowers:writing-skills`, `/skill-judge`-cleared, `/naming-analyzer`-named | ✓ VERIFIED (regression check) | No change to naming/registration surfaces since the prior pass. |
| 5 | (Plan-level, non-ROADMAP) `make validate`'s only failures are pre-existing and out-of-phase | ✓ VERIFIED | Full re-verification, see below. |

**Score:** 4/4 ROADMAP success criteria verified. The additional plan-level must-have (asserted explicitly and repeatedly in 06-02-PLAN.md/06-03-PLAN.md frontmatter) now also passes.

### Gap Closure — Full Re-Verification

**Previous gap:** fix commit `2359e43` (CR-01 corrupted-cache-crash fix) added an `isinstance(payload, dict)` narrowing check in `stack_cache.py`, which caused `pyright` to newly report `reportArgumentType` at line 100 (`datetime.fromisoformat(cached_at)` — `cached_at`'s type narrowed from `Any` to `Unknown | None`, which `fromisoformat`'s `str` parameter rejects).

**Fix applied:** commit `6271a5d` adds an explicit `isinstance(cached_at, str)` guard immediately before the `try`/`fromisoformat` call, returning `{"state": "stale", "data": data}` directly when `cached_at` is not a `str`. The `except` clause was narrowed from `(TypeError, ValueError)` to `ValueError` only, since the `TypeError` case (a non-str/None `cached_at` passed to `fromisoformat`) is now intercepted before the `try` block by the new `isinstance` check.

**Verification performed directly against current source and tool output (not the commit message):**

1. **Read the current file** (`stack_cache.py` lines 96–104) — confirmed the new `isinstance(cached_at, str)` guard precedes the `try`/`except ValueError` block exactly as described.
2. **Ran `uv run pyright skills/ai-kit-agents-md-rules-checker/ai_kit_agents_md_rules_checker/stack_cache.py` in isolation** → `0 errors, 0 warnings, 0 informations`. The previously-reported line-100 `reportArgumentType` error is gone.
3. **Ran `make validate`** (the full `pre-commit run --all-files` gate) → the `pyright` hook reports `Passed`. The only failing hooks are `ruff` and `pylint`, and every failing file confirmed by `-->` path extraction is: `tools/status-line.py`, `tools/wizard_app.py`, `tests/test_ai_kit_spec_superpowers.py` (all three documented in `deferred-items.md`) plus one additional file, `tests/test_ai_kit_spec.py` (see Advisory below — confirmed genuinely pre-existing and unrelated to Phase 6, not a new regression from this phase's commits). **Zero Phase 6 package files** (`skills/ai-kit-agents-md-rules-checker/**`) appear anywhere in the `make validate` failure output — grep for `ai-kit-agents-md-rules-checker`/`ai_kit_agents_md_rules_checker` across the full validate output returns 0 matches.
4. **Semantic-equivalence check (runtime behavior preserved):** Before the fix, a non-`str` `cached_at` (e.g. `None` from a payload missing the key, or malformed JSON where `cached_at` is a number) triggered `datetime.fromisoformat(cached_at)` to raise `TypeError`, caught by `except (TypeError, ValueError)`, returning `{"state": "stale", "data": data}`. After the fix, the same non-`str` `cached_at` is caught by the new `isinstance` guard *before* the `try` block and returns the identical `{"state": "stale", "data": data}`. The observable behavior for every input is unchanged — confirmed by re-running the full existing regression suite (see below), which required no test changes to stay green.

**Full regression run (never filtered/re-run per-truth, run once):**
- `python3 -m unittest tests.test_ai_kit_agents_md_rules_checker -v` → `Ran 62 tests in 0.012s — OK`, including `test_corrupted_cache_file_never_crashes`, `test_non_object_cache_payload_never_crashes` (CR-01 regressions) and `test_hyphenated_name_never_matches_inside_a_longer_hyphenated_token` (CR-02 regression) — all `ok`.
- `make test` → workspace-wide `python3 -m unittest discover` reports `Ran 1595 tests in 21.189s — OK (skipped=25)`, plus `tests/test_install.sh` reports `16 passed, 0 failed`. Exit code `0`.

**Conclusion:** The gap is closed. `make validate`'s only Phase-6-attributable outcome is a clean `pyright` pass; the remaining `ruff`/`pylint` failures are entirely in files never touched by any Phase 6 commit.

### Code Review Critical Fixes — Re-Confirmed Stable

| Review Finding | File | Verification Method | Result |
|---|---|---|---|
| CR-01: corrupted/malformed stack-cache JSON crashes every future `check`/`remediate` call | `stack_cache.py` `read_stack_cache()` | Re-ran `test_corrupted_cache_file_never_crashes`, `test_non_object_cache_payload_never_crashes` within the full suite run above — both `ok`. Read current function body: the crash-safety `try/except (json.JSONDecodeError, OSError, UnicodeDecodeError)` and `isinstance(payload, dict)` guard are unchanged by the pyright fix. | ✓ Still fixed, no regression |
| CR-02: word-boundary check false-positives on hyphenated target names | `makefile_checker.py` `_recipe_mentions_target()` | Re-ran `test_hyphenated_name_never_matches_inside_a_longer_hyphenated_token` within the full suite run above — `ok`. File untouched by commit `6271a5d`. | ✓ Still fixed, no regression |

### Required Artifacts

| Artifact | Expected | Status | Details |
|---|---|---|---|
| `skills/ai-kit-agents-md-rules-checker/SKILL.md` | Final-name skill definition, full wrap narrative | ✓ VERIFIED (unchanged) | Not touched by either fix commit. |
| `ai_kit_agents_md_rules_checker/rules.py` | 17-rule structured ruleset | ✓ VERIFIED (unchanged) | Not touched by either fix commit; `check .` confirms all 17 still classified. |
| `ai_kit_agents_md_rules_checker/makefile_checker.py` | Makefile target-shape + chain/alias/category checks | ✓ VERIFIED (unchanged since CR-02 fix) | CR-02 regression test passes; not touched by `6271a5d`. |
| `ai_kit_agents_md_rules_checker/rule_checker.py` | Workflow-rule prose classifier | ✓ VERIFIED (unchanged) | Not touched by either fix commit. |
| `ai_kit_agents_md_rules_checker/stack_cache.py` | Staleness-gated per-stack cache | ✓ VERIFIED — regression fully resolved | 151 lines; `isinstance(cached_at, str)` guard added; `pyright` clean (0 errors); crash-safety tests still pass. |
| `ai_kit_agents_md_rules_checker/remediation.py` | `build_remediation()` payload builder | ✓ VERIFIED (unchanged) | Not touched by either fix commit. |
| `ai_kit_agents_md_rules_checker/cli.py` | `check`/`remediate`/`cache-update` CLI | ✓ VERIFIED (unchanged) | `check .` re-run produced correct JSON output. |
| `tests/test_ai_kit_agents_md_rules_checker.py` | Full test suite | ✓ VERIFIED | 62 tests, all pass. |
| `README.md` Contents row | Final-name row added | ✓ VERIFIED (unchanged) | Not touched by either fix commit. |

### Key Link Verification

No key links changed by the fix commit (`stack_cache.py`'s public interface — `read_stack_cache`, `write_stack_cache`, `cache_path`, `get_stack_tooling` — is untouched; only the internal staleness-check body changed). Prior verification's WIRED findings for `cli.py check()` → `makefile_checker`/`rule_checker`, `makefile_checker.py` → `stack_cache.get_stack_tooling()`, and the `/agent-md-refactor` handoff all stand unchanged.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|---|---|---|---|
| `check` subcommand produces real, non-empty findings against this repo's own Makefile/AGENTS.md | `python3 skills/ai-kit-agents-md-rules-checker/ai-kit-agents-md-rules-checker.py check .` | 17 makefile findings + 15 workflow findings, valid JSON — unchanged from prior pass | ✓ PASS |
| `pyright` clean on the fixed file (isolated) | `uv run pyright skills/ai-kit-agents-md-rules-checker/ai_kit_agents_md_rules_checker/stack_cache.py` | `0 errors, 0 warnings, 0 informations` | ✓ PASS |
| Full unit test suite passes | `python3 -m unittest tests.test_ai_kit_agents_md_rules_checker -v` | `Ran 62 tests in 0.012s — OK` | ✓ PASS |
| `make test` passes (full workspace) | `make test` | `Ran 1595 tests in 21.189s — OK (skipped=25)`; `tests/test_install.sh`: `16 passed, 0 failed`; exit code 0 | ✓ PASS |
| `make validate` — `pyright` hook | `make validate` | `pyright..................................................................Passed` | ✓ PASS |
| `make validate` — overall gate | `make validate` | Still fails overall, but only on `ruff`/`pylint` in 4 files, none of which are Phase 6's own package (0 grep matches for the skill's package name in the failure output) | ✓ PASS (Phase-6-scoped) |
| CR-01 regression tests | within the full suite run above | `test_corrupted_cache_file_never_crashes`, `test_non_object_cache_payload_never_crashes` both `ok` | ✓ PASS |
| CR-02 regression test | within the full suite run above | `test_hyphenated_name_never_matches_inside_a_longer_hyphenated_token` `ok` | ✓ PASS |

### Requirements Coverage

Unchanged from the prior verification pass — REQ-agtmd-wrapper, REQ-agtmd-makefile-rules, REQ-agtmd-workflow-rules, REQ-agtmd-skill-pipeline all ✓ SATISFIED (see prior evidence; no Phase 6 requirement-relevant code changed by the fix commit). No orphaned requirements found.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|---|---|---|---|---|
| — | — | Previous 🛑 Blocker (`stack_cache.py:100` pyright `reportArgumentType`) — resolved | — | `pyright` now clean; no Phase 6 anti-patterns remain |
| — | — | No `TBD`/`FIXME`/`XXX` debt markers found in any Phase 6 file | — | N/A, clean |
| — | — | No stub returns, no empty-implementation patterns found in the package | — | N/A, clean |

### Advisory (New Scope, Unevidenced)

| # | Finding | Category | Why Advisory |
|---|---------|----------|--------------|
| 1 | `make validate`'s `ruff` hook also fails on `tests/test_ai_kit_spec.py` (E501/RUF059), a fourth pre-existing failing file not listed in `deferred-items.md` alongside the three documented ones | other | Confirmed via `git log`/`git diff`/`git status` that this file was never touched by any Phase 6 commit and is unmodified in the working tree — genuinely pre-existing and unrelated to this phase (opencode/model-catalog work). Documentation-staleness in `deferred-items.md`, not a Phase 6 regression; does not block this phase. |

### Human Verification Required

None. The prior human-verification item (end-to-end SKILL.md wrap invocation) was structural/human-only in the initial pass and is unaffected by the pyright fix commit (no change to `SKILL.md` or the wrap mechanism) — it remains outside the scope of this re-verification, which targeted only the previously identified `gaps_found` item.

### Gaps Summary

The single gap from the prior verification pass — a new `pyright` regression in `stack_cache.py:100` introduced by the CR-01 fix commit (`2359e43`) — is closed by commit `6271a5d`. Verified directly: `pyright` reports 0 errors on the isolated file and `Passed` inside the full `make validate` run; the full 62-test package suite and the full 1595-test workspace suite both pass with no changes required; the CR-01/CR-02 regression tests specifically remain green; and the fix preserves identical runtime behavior for every `cached_at` input shape (confirmed by code inspection of the guard placement, not just test-passing). `make validate`'s only remaining failures are `ruff`/`pylint` findings in files with zero Phase 6 commits touching them — three of which are documented in `deferred-items.md`, plus one (`tests/test_ai_kit_spec.py`) confirmed pre-existing and unrelated but not yet added to that document (flagged as an advisory, not a blocker). Phase 6's goal is fully achieved: all 4 ROADMAP success criteria hold, both code-review Criticals are genuinely fixed and regression-tested, and the phase's own quality-gate contract (`make validate` introduces no new Phase-6-attributable failures) now holds as well.

---

*Verified: 2026-09-11*
*Verifier: Claude (gsd-verifier)*
