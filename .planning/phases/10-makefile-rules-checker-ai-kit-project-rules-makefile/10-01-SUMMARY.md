---
phase: 10-makefile-rules-checker-ai-kit-project-rules-makefile
plan: 01
subsystem: testing
tags: [python, makefile, pre-commit, skill-checker, ai-kit-project-rules-makefile, ai-kit-rules-common]

# Dependency graph
requires:
  - phase: 09-agents-md-checker-prune-ai-kit-project-rules-agents
    provides: the pruned ai-kit-project-rules-agents skill (makefile_checker.py physically
      absent), tooling_payload.py already relocated to this skill's tree, and the recovery
      point commit 9d672b9 (Phase 9's rename commit, parent of its prune commit e56316e)
provides:
  - "ai-kit-project-rules-makefile skill: check/remediate/cache-update CLI reproducing the
    three inherited Makefile checks (REQUIRED_STATIC_TARGETS shape, validate chain_incomplete,
    test/test-unit pairing) with pre-prune finding shape"
  - "skills/_shared/ai_kit_rules_common/{criticality,makefile_parse,precommit_parse,
    stack_detect}.py -- shared parsing primitives and criticality bands for Phase 11 and
    Phase 14 to import"
  - "check_precommit_prepush_split: homed in shared package, no caller yet (Phase 11's)"
affects: [11-pre-commit-rules-checker-ai-kit-project-rules-precommit,
  13-docker-rules-checker-ai-kit-project-rules-docker,
  14-ci-cd-rules-checker-ai-kit-project-rules-cicd,
  15-rules-orchestrator-ai-kit-project-rules-all,
  10-makefile-rules-checker-ai-kit-project-rules-makefile]

actuals:
  tokens: 20471
  tasks: 2
  commits: 2

tech-stack:
  added: []
  patterns:
    - "Skill-local namespace binding of a shared generic engine (stack_cache.py wrapper
      pattern): re-export re-exported constants from a single-source-of-truth module
      (tooling_payload.py) rather than declaring them, proven by AST + object-identity checks"
    - "Ordered-reader-is-the-source-of-truth: a set-returning parser defined in terms of an
      ordered list-returning one, so the two can never disagree about tokenization"

key-files:
  created:
    - skills/_shared/ai_kit_rules_common/criticality.py
    - skills/_shared/ai_kit_rules_common/makefile_parse.py
    - skills/_shared/ai_kit_rules_common/precommit_parse.py
    - skills/_shared/ai_kit_rules_common/stack_detect.py
    - skills/ai-kit-project-rules-makefile/ai-kit-project-rules-makefile.py
    - skills/ai-kit-project-rules-makefile/ai_kit_project_rules_makefile/__init__.py
    - skills/ai-kit-project-rules-makefile/ai_kit_project_rules_makefile/cli.py
    - skills/ai-kit-project-rules-makefile/ai_kit_project_rules_makefile/makefile_checker.py
    - skills/ai-kit-project-rules-makefile/ai_kit_project_rules_makefile/remediation.py
    - skills/ai-kit-project-rules-makefile/ai_kit_project_rules_makefile/stack_cache.py
    - tests/test_ai_kit_project_rules_makefile.py
  modified:
    - skills/ai-kit-project-rules-makefile/ai_kit_project_rules_makefile/tooling_payload.py
    - tests/test_ai_kit_rules_common.py
    - Makefile
    - pyproject.toml
    - .pre-commit-config.yaml

key-decisions:
  - "stack_cache.py is the ONE adapted recovery artifact (all others copied verbatim); its
    three schema tuple declarations are stripped in favor of importing them from
    tooling_payload.py, per the plan's SCHEMA-SINGLE-SOURCE-OK gate."
  - "check_precommit_prepush_split moved to the shared package but is called by nobody in this
    phase -- Phase 11 owns the check, this phase only gives the function a home."
  - "TestWiredCheckWordBoundary and TestValidateOrderAndPrecommitPrepushSplit both split across
    the shared and skill suites (two-way and three-way respectively) rather than being recovered
    into a single file, following code ownership."

patterns-established:
  - "Recovery-then-split protocol for future skill extractions: git show a pre-prune commit,
    copy verbatim except where a later commit already relocated a dependency, and adapt only
    that one file with the adaptation enumerated in the SUMMARY."

requirements-completed: [REQ-rules-makefile]

coverage:
  - id: D1
    description: "New skill's check command reproduces the three inherited Makefile checks
      (static-target shape unioned with pre-commit hook ids, validate chain_incomplete,
      test/test-unit pairing) with pre-prune finding shape"
    requirement: "REQ-rules-makefile"
    verification:
      - kind: unit
        ref: "tests/test_ai_kit_project_rules_makefile.py#TestCheckMakefileShapeTracer,
          TestValidateChainAndAlias, TestWiringViaPrerequisites, TestNoCrashAndNoStack"
        status: pass
      - kind: other
        ref: "Task 1 tracer <verify> command (python3 -c ... TRACER-OK)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Shared parsing primitives (makefile_parse, precommit_parse, stack_detect,
      criticality) extracted to skills/_shared/ai_kit_rules_common/ for Phase 11/14 reuse"
    requirement: "REQ-rules-makefile"
    verification:
      - kind: unit
        ref: "tests/test_ai_kit_rules_common.py#TestParseMakefileTargets,
          TestParsePrecommitHooks, TestRecipeMentionsTargetWordBoundary,
          TestPrecommitPrepushSplit"
        status: pass
      - kind: other
        ref: "Task 1 SHARED-EXTRACT-OK / ORDERED-PREREQ-OK acceptance criteria"
        status: pass
    human_judgment: false
  - id: D3
    description: "cache-update subcommand validates through the relocated tooling_payload
      validator and writes under this skill's own project-rules-makefile cache namespace,
      rejecting a path-traversal-shaped stack argument cleanly"
    requirement: "REQ-rules-makefile"
    verification:
      - kind: unit
        ref: "tests/test_ai_kit_project_rules_makefile.py#TestCacheUpdateCLI,
          TestCacheUpdateValidation"
        status: pass
      - kind: other
        ref: "Task 1 CACHE-UPDATE-OK acceptance criterion"
        status: pass
    human_judgment: false
  - id: D4
    description: "Criticality band vocabulary shared and pinned against
      ai-kit-project-rules-agents's rules.py literals by a non-vacuous drift guard"
    requirement: "REQ-rules-makefile"
    verification:
      - kind: unit
        ref: "tests/test_ai_kit_rules_common.py#TestCriticalityDriftGuard.test_shared_bands_match_agents_skill_literals"
        status: pass
    human_judgment: false
  - id: D5
    description: "All 15 Makefile-domain test classes Phase 9 deleted are recovered from
      9d672b9 and re-homed with a recorded destination; skill registered in every quality
      gate the sibling is in"
    requirement: "REQ-rules-makefile"
    verification:
      - kind: unit
        ref: "tests/test_ai_kit_project_rules_makefile.py#TestGateRegistration"
        status: pass
      - kind: other
        ref: "Task 2 RECOVERED-CLASSES / GATES-OK acceptance criteria"
        status: pass
    human_judgment: false

duration: 55min
completed: 2026-09-14
status: complete
---

# Phase 10 Plan 01: Re-home Makefile checker into ai-kit-project-rules-makefile Summary

**Recovered `makefile_checker.py`/`stack_detect.py` verbatim from commit `9d672b9`, extracted
three shared parsing modules (`makefile_parse`, `precommit_parse`, `stack_detect`) plus a
shared `criticality` module into `skills/_shared/ai_kit_rules_common/`, and re-homed all 15
deleted test classes across two suites -- the new skill's `check` command reproduces the three
inherited Makefile checks end-to-end.**

## Performance

- **Duration:** 55 min
- **Tasks:** 2
- **Files modified:** 16 (11 created, 5 modified)

## Accomplishments
- New skill `ai-kit-project-rules-makefile` with a working `check`/`remediate`/`cache-update`
  CLI, reproducing the three checks ROADMAP Phase 10 SC1 names, with the exact pre-prune
  finding shape (`target`/`category`, `present`, `issue`, `recommendation`, `needs_research`,
  `stacks`, `criticality`, `summary`)
- `skills/_shared/ai_kit_rules_common/` grew by four modules (`criticality.py`,
  `makefile_parse.py`, `precommit_parse.py`, `stack_detect.py`) that Phase 11 and Phase 14 will
  import instead of re-deriving (10-CONTEXT D-01/D-02/D-05)
- All 15 Makefile-domain test classes Phase 9 deleted are back, recovered verbatim from
  `9d672b9` and re-homed by code ownership across the shared and skill suites
- Suite totals: shared 29 -> 38 (+9), skill 0 -> 33 (new file), agents unchanged at 21
  (91 total across the three suites, up from 50 before this plan)
- New skill registered in every quality gate the sibling is in (`Makefile` test-unit + lint,
  `.pre-commit-config.yaml` ruff/py-compile/unittest, `pyproject.toml` pyright/vulture), proven
  by its own `TestGateRegistration` class

## Task Commits

1. **Task 1: Extract the shared parsing primitives, then wire the new skill end-to-end** -
   `64355db` (feat)
2. **Task 2: Recover the 15 deleted Makefile-domain test classes, re-home each, plus drift
   guard and gate registration** - `4b992f3` (test)

**Plan metadata:** (this commit, once made)

## Files Created/Modified

- `skills/_shared/ai_kit_rules_common/criticality.py` - shared `CRITICALITY_CRITICAL=1`/
  `_HIGH=2`/`_MEDIUM=3` (matching `ai-kit-project-rules-agents/rules.py` verbatim) plus
  `CRITICALITY_ADVISORY=4` for plan 10-02
- `skills/_shared/ai_kit_rules_common/makefile_parse.py` - `parse_makefile_targets`,
  `parse_makefile_recipe`, `parse_makefile_prerequisites` (set), the new
  `parse_makefile_prerequisites_ordered` (list, single source of truth), and the promoted
  `recipe_mentions_target` word-boundary helper
- `skills/_shared/ai_kit_rules_common/precommit_parse.py` - `parse_precommit_hooks`, the
  promoted `iter_precommit_hook_blocks`, `check_precommit_prepush_split`, `SLOW_HOOK_KEYWORDS`
- `skills/_shared/ai_kit_rules_common/stack_detect.py` - `detect_stacks`, verbatim
- `skills/ai-kit-project-rules-makefile/ai_kit_project_rules_makefile/__init__.py` - sibling's
  `sys.path`-insert pattern, retargeted
- `skills/ai-kit-project-rules-makefile/ai_kit_project_rules_makefile/stack_cache.py` - THE ONE
  ADAPTED recovery artifact (see Deviations)
- `skills/ai-kit-project-rules-makefile/ai_kit_project_rules_makefile/makefile_checker.py` -
  recovered checker minus the split-away pre-commit-stage splitter call
- `skills/ai-kit-project-rules-makefile/ai_kit_project_rules_makefile/remediation.py` - thin
  re-export of the shared `build_remediation`
- `skills/ai-kit-project-rules-makefile/ai_kit_project_rules_makefile/cli.py` -
  `check`/`remediate`/`cache-update`, argparse-free
- `skills/ai-kit-project-rules-makefile/ai-kit-project-rules-makefile.py` - 6-line entrypoint
- `skills/ai-kit-project-rules-makefile/ai_kit_project_rules_makefile/tooling_payload.py` -
  docstring updated; no longer claims to be unwired
- `tests/test_ai_kit_project_rules_makefile.py` - new skill's suite (33 tests)
- `tests/test_ai_kit_rules_common.py` - grown by 9 tests (shared-package re-homed coverage +
  criticality drift guard)
- `Makefile`, `.pre-commit-config.yaml`, `pyproject.toml` - registration surfaces extended

## Recovery Record

All recovery reads were run against the same commit,
`9d672b9ef233baf496a48d50e6dba921316d107c` (Phase 9's rename commit, parent of its prune commit
`e56316e`), verified to resolve at planning time and re-verified before any edit (Task 1's
precondition):

```
git show 9d672b9ef233baf496a48d50e6dba921316d107c:skills/ai-kit-project-rules-agents/ai_kit_project_rules_agents/makefile_checker.py   -> VERBATIM (split across makefile_checker.py + the three new shared modules)
git show 9d672b9ef233baf496a48d50e6dba921316d107c:skills/ai-kit-project-rules-agents/ai_kit_project_rules_agents/stack_detect.py         -> VERBATIM -> skills/_shared/ai_kit_rules_common/stack_detect.py
git show 9d672b9ef233baf496a48d50e6dba921316d107c:skills/ai-kit-project-rules-agents/ai_kit_project_rules_agents/stack_cache.py          -> ADAPTED (the one exception; see below) -> skills/ai-kit-project-rules-makefile/ai_kit_project_rules_makefile/stack_cache.py
git show 9d672b9ef233baf496a48d50e6dba921316d107c:skills/ai-kit-project-rules-agents/ai_kit_project_rules_agents/cli.py                  -> VERBATIM (cache-update handler only: _split_cache_root, cache_update, the cache-update branch of main) -> skills/ai-kit-project-rules-makefile/ai_kit_project_rules_makefile/cli.py
git show 9d672b9ef233baf496a48d50e6dba921316d107c:tests/test_ai_kit_project_rules_agents.py                                              -> VERBATIM per-class (15 Makefile-domain classes; see Test Recovery Ledger below)
```

**Every recovered artifact was VERBATIM except one.** `ai_kit_project_rules_makefile/stack_cache.py`
is the ONE ADAPTED file, with exactly three adaptations, all recorded in its own docstring and
in Task 1(b)'s plan text:

1. **STRIPPED** the three schema declarations (`REQUIRED_STATIC_TARGETS`, `RESEARCH_CATEGORIES`
   tuple literals, and the `ALL_TOOLING_KEYS = REQUIRED_STATIC_TARGETS + RESEARCH_CATEGORIES`
   re-derivation). Replaced with `from .tooling_payload import ALL_TOOLING_KEYS,
   REQUIRED_STATIC_TARGETS, RESEARCH_CATEGORIES` -- the single definition site Phase 9 already
   relocated them to.
2. **REPOINTED** the namespace: `_NAMESPACE = "agents-md-rules-checker"` (recovered) ->
   `_NAMESPACE = "project-rules-makefile"` (this skill). Both sides recorded here for a later
   reader: the recovered file's cache namespace was `agents-md-rules-checker`; this skill's is
   `project-rules-makefile` (the skill name minus the `ai-kit-` prefix, mirroring the sibling's
   own convention of `agents-md-rules-checker` for `ai-kit-project-rules-agents`).
3. **REPLACED** the docstring: the recovered text describes the schema staying in that file
   because `makefile_checker.py` "still lives in the old skill" and points at a "follow-up plan"
   that relocates both together -- that follow-up plan is this one, so both halves of the
   recovered sentence were false. Replaced with a statement of what the module now is (this
   skill's namespace binding of the shared generic cache engine) and where the schema now lives.

**Why this file, and only this file, needed adaptation:** at `9d672b9`, `stack_cache.py` was
already a thin wrapper around the shared generic cache engine (`ai_kit_rules_common.stack_cache`)
-- that wrapper SHAPE (the `_shared` import, `STALE_AFTER_DAYS` re-export, namespaced
`CACHE_ROOT`, the four `cache_root`-defaulting wrappers, `__all__`) is identical between the
recovered file and this skill's copy, and all of that travels verbatim. But the recovered file
ALSO still declared the tooling key schema as tuple literals, because at that commit those
tuples had nowhere else to live. Phase 9 gave them a home (`tooling_payload.py`, already present
in this skill's tree, unwired) specifically so this plan would not re-create a second definition
site. Pasting the recovered blob in verbatim would have created exactly that second copy, failing
this plan's own `SCHEMA-SINGLE-SOURCE-OK` acceptance criterion (which forbids ANY module-level
assignment to those three names, not just a tuple literal -- it also catches the recovered file's
`ALL_TOOLING_KEYS` `BinOp` re-derivation) and re-opening threat row T-10-02 (the payload validator
and the checker disagreeing about what a valid tooling key is).

### Per-module shared-extraction ledger (what moved, from where)

| Shared module | Functions/constants | Recovered from |
|---|---|---|
| `criticality.py` | `CRITICALITY_CRITICAL`/`_HIGH`/`_MEDIUM` (values only, not names -- recovered file imported these from `.rules`); `CRITICALITY_ADVISORY` new | values matched against `skills/ai-kit-project-rules-agents/ai_kit_project_rules_agents/rules.py` lines 26-28 |
| `makefile_parse.py` | `_TARGET_HEADER_RE`, `parse_makefile_targets`, `parse_makefile_prerequisites`, `parse_makefile_recipe`, `_recipe_mentions_target` (promoted to `recipe_mentions_target`) | `9d672b9`'s `makefile_checker.py` |
| `makefile_parse.py` (new) | `parse_makefile_prerequisites_ordered` | new, per D-05's ordering requirement; `parse_makefile_prerequisites` now delegates to it |
| `precommit_parse.py` | `_ID_LINE_RE`/`_ENTRY_LINE_RE`/`_STAGES_LINE_RE`, `_strip_yaml_quotes`, `_iter_precommit_hook_blocks` (promoted to `iter_precommit_hook_blocks`), `parse_precommit_hooks`, `check_precommit_prepush_split`, `SLOW_HOOK_KEYWORDS` | `9d672b9`'s `makefile_checker.py` |
| `stack_detect.py` | `_MARKERS`, `detect_stacks` | `9d672b9`'s `stack_detect.py`, verbatim |

**`check_precommit_prepush_split` lands in shared with NO caller in this phase.** The design
spec assigns the precommit-vs-prepush-split CHECK to `ai-kit-project-rules-precommit` (Phase
11), not to this skill; D-01 only requires the pre-commit-hook parsing FAMILY to travel as one
unit so Phase 11 can import it without reaching into another skill. `makefile_checker.py`'s
`check_makefile_shape` therefore does NOT call it, and does not append its finding. Verified by
the `NO-PRECOMMIT-STAGE-FINDING-OK` acceptance criterion: a fixture with a slow hook (`unittest`,
no `stages:`) that would trip the pre-prune checker's split-finding branch produces zero findings
containing the substring `"push"` from this skill's `check` -- confirming the caller really was
dropped, not that the fixture was uninteresting.

### Cache namespace

Chosen: `project-rules-makefile` (the skill directory name minus the `ai-kit-` prefix), following
the sibling's own convention (`agents-md-rules-checker` for `ai-kit-project-rules-agents`). Cache
root resolves to `~/.cache/ai-kit/project-rules-makefile/stack-refs/` via the shared engine's
`default_cache_root(namespace)`.

### Cache-staleness discrepancy (observed, deliberately unfixed)

`.planning/intel/constraints.md` and the design spec both state the cache staleness threshold as
**180 days**. The already-merged shared `skills/_shared/ai_kit_rules_common/stack_cache.py`
ships **30** (`STALE_AFTER_DAYS = 30`). This skill inherits the shared engine's shipped value
verbatim and changes neither side -- the shared engine's own value is out of this phase's scope,
and the two documents naming 180 are a SPEC-extract, not `REQUIREMENTS.md` or `ROADMAP.md`.
Recorded here so plan 10-03 and Phase 11 inherit it as a known open question rather than
re-discovering it.

## Test Recovery Ledger

All 15 test classes Phase 9 deleted, recovered verbatim from `9d672b9`'s
`tests/test_ai_kit_project_rules_agents.py`, with a recorded destination for each:

| Recovered class | Destination | Notes |
|---|---|---|
| `TestParseMakefileTargets` | shared suite (verbatim) | |
| `TestParsePrecommitHooks` | shared suite (verbatim) | |
| `TestCheckMakefileShapeTracer` | skill suite (verbatim) | |
| `TestStackCacheStates` | skill suite (trimmed) | only the two skill-binding-specific methods kept (default cache root under `project-rules-makefile` namespace; wrappers thread the default root through when `cache_root` is omitted). `test_absent_fresh_stale`, `test_corrupted_cache_file_never_crashes`, `test_non_object_cache_payload_never_crashes` dropped as already-covered by `tests/test_ai_kit_rules_common.py`'s `TestStackCache.{test_absent_fresh_stale, test_corrupted_json_is_absent, test_non_dict_payload_is_absent}` (they exercise the generic engine directly, not this skill's binding) |
| `TestCachePathValidation` | skill suite (trimmed) | kept `test_valid_identifiers_succeed` (renamed `..._via_default_namespace`) as it exercises the skill wrapper's default-root resolution; dropped `test_invalid_identifiers_raise` as already-covered by `tests/test_ai_kit_rules_common.py`'s `TestStackCache.test_invalid_stack_identifier_raises` (generic engine's `ValueError` behavior, already proven against the shared `cache_path` directly) |
| `TestStaleCacheNotTrusted` | skill suite (verbatim) | genuinely skill-specific: exercises `check_makefile_shape` together with this skill's `stack_cache` |
| `TestMultiStackResolution` | skill suite (verbatim) | |
| `TestToolingCategoryGaps` | skill suite (verbatim) | |
| `TestValidateChainAndAlias` | skill suite (verbatim) | |
| `TestWiringViaPrerequisites` | skill suite (verbatim) | |
| `TestWiredCheckWordBoundary` | **split** | word-boundary-semantics case (`test_hyphenated_name_never_matches_inside_a_longer_hyphenated_token`, calls `recipe_mentions_target` directly) -> shared suite's `TestRecipeMentionsTargetWordBoundary`. The two cases that assert through `check_makefile_shape` (`test_raw_substring_never_satisfies_membership`, `test_standalone_token_satisfies_membership`) -> skill suite, kept under the original class name `TestWiredCheckWordBoundary` |
| `TestNoCrashAndNoStack` | skill suite (verbatim) | |
| `TestValidateOrderAndPrecommitPrepushSplit` | **THREE-WAY split** | (1) pre-commit-stage splitter cases (`test_slow_hook_missing_own_push_stage_is_flagged`, `test_slow_hook_with_own_push_stage_not_flagged`, `test_no_slow_hook_nothing_to_verify`) -> shared suite's `TestPrecommitPrepushSplit`, exercising `precommit_parse.check_precommit_prepush_split`; (2) the ordering-stub case (`test_check_validate_order_never_adds_a_finding`) -> skill suite, kept under the original class name `TestValidateOrderAndPrecommitPrepushSplit` -- this is the checker's real post-Task-1 behavior (a permanent no-op); plan 10-02 rewrites this coverage in place once the stub becomes the advisory heuristic; (3) `test_categories_never_contain_removed_entries` -> ALSO skill suite, same class -- an independent schema-shape assertion (`RESEARCH_CATEGORIES` contains neither `validate-order` nor `precommit-vs-prepush-split`) that cycle-3 review caught going unassigned by the original two-way split |
| `TestCacheUpdateCLI` | skill suite (verbatim) | |
| `TestCacheUpdateValidation` | skill suite (verbatim) | |

**New, not recovered:** `TestRecipeMentionsTargetWordBoundary` and `TestPrecommitPrepushSplit`
(shared suite; carry the split-off cases above), `TestCriticalityDriftGuard` (shared suite),
`TestGateRegistration` (skill suite, mirrors the sibling's five checks retargeted at this skill --
Makefile module+package, `ruff`/`py-compile` `files:` regex, `unittest` `entry:`, pyright
`include`, vulture `paths` -- deliberately excluding `test_validate_covers_every_precommit_hook`,
which is Phase 11's hook-parity check, not this plan's).

**Criticality drift guard non-vacuity confirmed by hand:** temporarily edited
`skills/_shared/ai_kit_rules_common/criticality.py`'s `CRITICALITY_CRITICAL` from `1` to `99`,
re-ran `TestCriticalityDriftGuard` alone, observed it FAIL with an `AssertionError` diffing
`(1, 2, 3)` against `(99, 2, 3)`, then reverted the file and confirmed the diff against the
pre-edit copy was empty (byte-identical) before re-running the test to confirm it passes again.

**Registration-surface insertions (five checks, seven physical insertions across three files):**
- `Makefile` (test-unit list line 46; lint `py_compile` list line 70)
- `.pre-commit-config.yaml` (`ruff` hook `files:` regex line 21; `py-compile` hook `files:`
  regex line 50; `unittest` hook `entry:` list line 55)
- `pyproject.toml` (`[tool.vulture] paths` line 88; `[tool.pyright] include` line 94)

**`make validate` result:** fails on `ruff` (SIM117/E501/RUF059/I001 findings), all of them
confined to `tools/status-line.py`, `tools/wizard_app.py`, `tests/test_ai_kit_spec.py`, and
`tests/test_ai_kit_spec_superpowers.py` -- exactly the four pre-existing, out-of-scope files
`STATE.md`/Phase 9's SUMMARY already name. Confirmed by running every remaining pre-commit hook
individually since `make validate`'s prerequisite chain stops at the first failure: `pylint`
(fails only on `tools/status-line.py`, also pre-existing/out-of-scope), `pyright`, `vulture`,
`shellcheck`, `py-compile`, `unittest`, `unittest-wizard` all PASS. One finding did land in a
file this plan touched (a `ruff` `SIM117` nested-`with` finding in
`tests/test_ai_kit_project_rules_makefile.py`) -- fixed in-scope before the Task 2 commit (see
Deviations).

## Decisions Made
- Named the cache namespace `project-rules-makefile`, mirroring the sibling's
  `agents-md-rules-checker` convention (skill name minus `ai-kit-` prefix).
- Named the new ordered-prerequisite reader `parse_makefile_prerequisites_ordered` and kept
  `parse_makefile_prerequisites` as the set-returning name, delegating to the ordered reader --
  satisfies the acceptance criterion's `dir(mp)` substring-match discovery (both names contain
  `prereq`) without inventing an unrelated naming scheme.
- Split `TestWiredCheckWordBoundary` and `TestValidateOrderAndPrecommitPrepushSplit` by putting
  the ORIGINAL class name wherever the majority/most-structurally-significant share of methods
  landed (skill suite in both cases), and a newly-named class in the shared suite for the
  split-off piece -- satisfies the `RECOVERED-CLASSES` acceptance criterion (which only checks
  class-NAME presence across the two files) while keeping each method beside the code it tests.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed a `ruff` SIM117 finding in this plan's own new test file**
- **Found during:** Task 2, `make validate` run
- **Issue:** `TestStackCacheStates.test_wrappers_thread_default_root_when_cache_root_omitted`
  used two nested `with` statements (`tempfile.TemporaryDirectory()` then
  `mock.patch.object(...)`), which `ruff`'s SIM117 flags as combinable.
- **Fix:** Combined into a single `with (tempfile.TemporaryDirectory() as cache_root,
  mock.patch.object(stack_cache, "CACHE_ROOT", cache_root)):` using Python 3.10+ parenthesized
  context-manager syntax.
- **Files modified:** `tests/test_ai_kit_project_rules_makefile.py`
- **Verification:** `uv run ruff check tests/test_ai_kit_project_rules_makefile.py` -> "All
  checks passed!"; suite still 33/33 passing after the fix.
- **Committed in:** `4b992f3` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug fix, Rule 1)
**Impact on plan:** Necessary for `make validate`'s ruff hook to stay clean on this plan's own
files, per the plan's own instruction that any finding in a path this plan touched is in scope.
No scope creep.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `skills/_shared/ai_kit_rules_common/{makefile_parse,precommit_parse,stack_detect}.py` and
  `criticality.py` are ready for Phase 11 (`ai-kit-project-rules-precommit`) and Phase 14
  (`ai-kit-project-rules-cicd`) to import.
- `check_precommit_prepush_split` is homed but uncalled -- Phase 11 is expected to wire it.
- The skill remains uninstallable (no `SKILL.md`) until plan 10-03, which also owns the README
  row and the `/skill-judge` pass.
- Plan 10-02 (the five new checks) can now build on a proven, tested inherited-check foundation;
  its ordering heuristic will rewrite `TestValidateOrderAndPrecommitPrepushSplit`'s
  ordering-stub-half coverage in place.
- Cache-staleness discrepancy (180 days per docs vs. 30 days shipped) remains open for the
  shared engine's owner to resolve, out of this phase's scope.

---
*Phase: 10-makefile-rules-checker-ai-kit-project-rules-makefile*
*Completed: 2026-09-14*

## Self-Check: PASSED

All 11 created files (4 shared modules, 6 skill-package files, 1 new test file) and the
SUMMARY.md itself found on disk. Both task commits (`64355db`, `4b992f3`) found in `git log`.
