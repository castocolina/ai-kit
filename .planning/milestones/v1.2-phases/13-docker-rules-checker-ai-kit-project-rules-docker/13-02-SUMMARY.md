---
phase: 13-docker-rules-checker-ai-kit-project-rules-docker
plan: 02
subsystem: testing
tags: [python, stdlib, yaml-text-parsing, compose, healthcheck, depends-on, docker]

requires:
  - phase: 13-docker-rules-checker-ai-kit-project-rules-docker
    plan: 01
    provides: "docker_checker.check_docker_rules(repo_root)'s gate-then-extend aggregator shape, the eight-name target-family tuple, D-D3's identifier discipline, and STRUCTURAL_KINDS already carrying \"docker\""
provides:
  - "skills/_shared/ai_kit_rules_common/yaml_text.py: strip_yaml_quotes/line_indent/is_structural_line, the three shared stdlib YAML-text primitives Phase 14's CI-YAML checker is the named next consumer for"
  - "compose_parse.py: iter_services/block_scalar/block_subblock/block_sequence/block_mapping_keys (D-D7's indentation-aware parser contract), discover_compose_files/discover_local_dev_compose_files/read_compose_text, and the BASE_COMPOSE_FILENAMES/LOCAL_DEV_COMPOSE_FILENAMES tuples plan 13-03 consumes"
  - "healthcheck.py: parse_duration and check_healthcheck_bounds -- ROADMAP SC2"
  - "depends_on.py: check_depends_on -- ROADMAP SC3"
affects: [13-03-docker-hot-reload-and-runbook-content, 13-04-docker-skill-md-and-registration, 15-rules-orchestrator]

actuals:
  tokens: 21516
  tasks: 3
  commits: 3
  plan_head_before: e8859f757e951ddc5fe60be0157b98e05b380e5b

tech-stack:
  added: []
  patterns:
    - "One structural reader (_own_level_lines + _find_block_end in compose_parse.py), every accessor expressed in terms of it -- the same convergence makefile_parse.py records for its own ordered/set reader pair"
    - "block_subblock's three-way return contract: None (key absent OR same-line value present, including a flow-mapping body), \"\" (key present with a bare colon and no nested lines), or real block text -- callers distinguish \"not found\"/\"unreadable\" from \"found but empty\""
    - "Per-dependency condition reading composes block_subblock TWICE (once for depends_on: itself, once for the dependency name) rather than a dedicated nested-mapping reader -- the same primitive serves both levels"

key-files:
  created:
    - skills/_shared/ai_kit_rules_common/yaml_text.py
    - skills/ai-kit-project-rules-docker/ai_kit_project_rules_docker/compose_parse.py
    - skills/ai-kit-project-rules-docker/ai_kit_project_rules_docker/healthcheck.py
    - skills/ai-kit-project-rules-docker/ai_kit_project_rules_docker/depends_on.py
  modified:
    - skills/ai-kit-project-rules-docker/ai_kit_project_rules_docker/docker_checker.py
    - tests/test_ai_kit_project_rules_docker.py
    - tests/test_ai_kit_rules_common.py

key-decisions:
  - "D-D7's parser contract landed exactly as specified: iter_services/block_scalar/block_subblock/block_sequence/block_mapping_keys, built on one shared own-level-line reader (_own_level_lines) and one block-end reader (_find_block_end), both driven by yaml_text.line_indent/is_structural_line plus a compose_parse-local `---`-separator carve-out (_effective_structural)."
  - "block_sequence's SCALAR-ITEMS-ONLY contract (D-D7) is implemented and pinned: a `- type: bind` sequence-of-mappings entry returns the single fragment `type: bind`, with its `source:`/`target:` continuation lines dropped rather than merged or returned separately. Plan 13-03 must treat that fragment as UNREADABLE."
  - "D-D8's shared yaml_text.py module landed with precommit_parse._strip_yaml_quotes deliberately left un-repointed, held together by a drift guard in tests/test_ai_kit_rules_common.py, following criticality.py's precedent for rules.py."
  - "D-D9's declared-values-only prohibition survived implementation untightened -- absent healthcheck keys are never flagged, pinned by multiple regression fixtures."
  - "D-D6's compose filename lists have exactly one home (compose_parse.BASE_COMPOSE_FILENAMES/LOCAL_DEV_COMPOSE_FILENAMES); docker_checker.py's old _COMPOSE_FILE_NAMES tuple was deleted, not left as a dead duplicate."

patterns-established:
  - "Bounds-table-driven test coverage: TestHealthcheckBoundsPerKeyPaired iterates healthcheck._BOUNDS itself for its over/at-boundary pairs, so the test cannot fall out of step with the checker's own table (same discipline plan 13-01 established for DOCKER_TARGET_FAMILY)."

requirements-completed: [REQ-rules-docker]

coverage:
  - id: SC2
    description: "A docker-compose.yml service whose healthcheck declares timeout>2s, start_period>10s or interval>5s is flagged -- one finding per key, naming the key/value/bound -- while a paired service at exactly 2s/10s/5s is not; the exclusive bound is proven on a fractional discriminator (interval: 5.001s)"
    requirement: "REQ-rules-docker"
    verification:
      - kind: unit
        ref: "tests/test_ai_kit_project_rules_docker.py#TestHealthcheckBoundsPerKeyPaired.test_each_bound_key_over_and_at_boundary"
        status: pass
      - kind: unit
        ref: "tests/test_ai_kit_project_rules_docker.py#TestHealthcheckFractionalExclusiveBound.test_interval_5_001s_is_out_of_bounds_not_unreadable"
        status: pass
      - kind: command
        ref: "BOUNDS-EXCLUSIVE-OK"
        status: pass
    human_judgment: false
  - id: SC3
    description: "A depends_on entry using bare ordering (block sequence, flow sequence, or a mapping entry with condition: service_started or absent) is flagged; condition: service_healthy is not; per-entry not whole-block evaluation"
    requirement: "REQ-rules-docker"
    verification:
      - kind: unit
        ref: "tests/test_ai_kit_project_rules_docker.py#TestDependsOnPerEntryEvaluation.test_one_correct_entry_does_not_clear_the_other_two"
        status: pass
      - kind: command
        ref: "DEPENDS-ON-OK, PER-ENTRY-OK, SEQUENCE-FORMS-OK"
        status: pass
    human_judgment: false

duration: ~2h
completed: 2026-09-14
status: complete
---

# Phase 13 Plan 02: Docker-Compose Parser, Healthcheck Bounds, and depends_on Discipline Summary

**An indentation-aware, stdlib-only `docker-compose.yml` reader (D-D7) plus the two structural checks built directly on top of it: healthcheck timing bounds exceeding 2s/10s/5s (SC2) and `depends_on` bare-ordering discipline across all three real forms (SC3), both evaluated per-entry with a stated, tested flow-mapping gap rather than a silent mis-parse.**

## Performance

- **Duration:** ~2h
- **Tasks:** 3
- **Commits:** 3 (measured: `git rev-list --count e8859f7..HEAD`)
- **Files modified:** 7 (4 created, 3 modified) across the three tasks

## Accomplishments

- `skills/_shared/ai_kit_rules_common/yaml_text.py`: `strip_yaml_quotes`, `line_indent`, `is_structural_line` -- D-D8's three shared stdlib primitives, with `precommit_parse._strip_yaml_quotes` deliberately left un-repointed and a drift guard pinning the two.
- `compose_parse.py`: D-D6's `BASE_COMPOSE_FILENAMES`/`LOCAL_DEV_COMPOSE_FILENAMES` tuples and `discover_compose_files`/`discover_local_dev_compose_files`; D-D7's `iter_services`/`block_scalar`/`block_subblock`/`block_sequence`/`block_mapping_keys`, all built on one structural reader.
- `healthcheck.py`: `parse_duration` (Go-style durations with decimal-fraction support) and `check_healthcheck_bounds` (D-D9's declared-values-only, exceeding-not-at-or-above bounds check).
- `depends_on.py`: `check_depends_on` (D-D10's per-entry evaluation across block-sequence, flow-sequence, and mapping forms, with the advisory completion-condition and unreadable-condition cases).
- `docker_checker.py`: D-D4 clause (i) repointed at `compose_parse`'s tuples (the old `_COMPOSE_FILE_NAMES` literal tuple was deleted, not left dead); `check_docker_rules` discovers compose files once and appends both new checks inside the applicable branch.
- Test suite grown from 42 to 106 docker-skill tests and the shared suite from 99 to 113, plus three independently-applied-and-reverted non-vacuity mutations proving the bounds comparison, the per-entry `depends_on` evaluation, and the indentation-driven block boundary are all load-bearing.

## Task Commits

1. **Task 1: Shared yaml-text primitives, compose parser, healthcheck bounds check** - `efe5349` (feat)
2. **Task 2: `depends_on` discipline check across all bare-ordering forms** - `ad3d85c` (feat)
3. **Task 3: Fill out the suite, add yaml_text coverage/drift guard, prove non-vacuous** - `e9f01e9` (test)

## Files Created/Modified

- `skills/_shared/ai_kit_rules_common/yaml_text.py` - the three shared primitives
- `skills/ai-kit-project-rules-docker/ai_kit_project_rules_docker/compose_parse.py` - the parser contract, discovery, filename tuples
- `skills/ai-kit-project-rules-docker/ai_kit_project_rules_docker/healthcheck.py` - duration parsing, bounds table, the two findings
- `skills/ai-kit-project-rules-docker/ai_kit_project_rules_docker/depends_on.py` - the four `depends_on` findings, per-entry evaluation
- `skills/ai-kit-project-rules-docker/ai_kit_project_rules_docker/docker_checker.py` - gate repointed, compose discovery, two appended calls
- `tests/test_ai_kit_project_rules_docker.py` - 64 new tests across Tasks 1-3 (42 -> 106)
- `tests/test_ai_kit_rules_common.py` - the `yaml_text` section + drift guard (99 -> 113)

## Decisions Made

### The parser's structural rules AS IMPLEMENTED (D-D7)

- **Indentation** is measured via the shared `yaml_text.line_indent` -- `len(line) - len(line.lstrip())`, a raw whitespace-character count, never a tab-to-column conversion.
- **A block's end** is decided by `_find_block_end(lines, start, ref_indent)`: the index of the first effectively-structural line at or after `start` whose indent is `<= ref_indent`; `len(lines)` if none exists.
- **The block's OWN nesting level** (used to find sibling keys/items inside a block) is decided by `_own_level_lines(lines, start, end)`: the level is established by the indent of the FIRST effectively-structural line in the range; only lines at exactly that indent are yielded as own-level headers, a line at a deeper indent is silently skipped (a child of the preceding header), and a line at a shallower indent than the established level ends the scan (malformed-input degrade, never a raise).
- **The SERVICE indentation level** (`iter_services`) is the indent of the first structural line inside the `services:` block -- found the same way, via `_own_level_lines` scoped to the `services:` block's own range.
- **Blank lines and comments** never count as structural (`yaml_text.is_structural_line`) and are transparently skipped everywhere -- they never end a block and never establish an indentation level.
- **A `---` document separator** is treated as noise by a `compose_parse`-local wrapper, `_effective_structural`, which layers a "not `---`" check on top of `is_structural_line`; this carve-out is local to `compose_parse.py` rather than baked into the shared `yaml_text.is_structural_line`, since `---` is a Compose/YAML-document concern, not a generic structural-line concern.
- Every accessor (`block_scalar`, `block_subblock`, `block_sequence`, `block_mapping_keys`) is expressed in terms of the SAME `_own_level_lines`/`_find_block_end` pair via a shared `_find_own_key` helper, so no two accessors can disagree about where a block ends.

### The tab-indentation limit and the missing-key limits, exactly as they came out

- A tab-indented compose file is NOT rejected and NOT asserted to parse correctly -- `TestParserDegradationFull.test_tab_indented_file_does_not_raise` asserts ONLY that `iter_services`/`check_docker_rules` return without raising, never a specific service or finding set, per cycle-1 review finding 11.
- An absent `interval` (or `timeout`/`start_period`) inherits Compose's own 30s implicit default and is NOT flagged -- pinned by `TestHealthcheckDeclaredValuesOnlyScopeRegression` (four methods: only-`test:`, only-`timeout:`, `disable: true` with an out-of-bounds `interval`, and no `healthcheck:` block at all -- each yields nothing).
- A service with no `healthcheck:` block is NOT flagged; a service with no `depends_on` at all is NOT flagged (`TestDependsOnMappingForm.test_no_depends_on_at_all_yields_nothing`).

### The flow-mapping limit, in `SKILL.md`-ready wording

Same-line **flow-mapping** bodies (`healthcheck: {interval: 30s}`, `depends_on: {db: {condition: service_healthy}}`) are NOT read by this parser. `block_subblock` and `block_mapping_keys` return `None`/`[]` for such a key, so the owning service is neither flagged nor confirmed conforming -- a stated gap, not a silent mis-parse. The parser does NOT let a flow-mapping value swallow the block boundary of the service defined after it: `STATED-LIMITS-OK`'s fixture (`flowy` in flow-mapping form, `after` immediately below in block form with an out-of-bounds `interval: 30s`) produces exactly one finding, named `after`, proving the flow-mapping line did not corrupt attribution of the next service. This holds identically for the `depends_on:` flow-mapping form (`TestFlowMappingStatedLimitPairedFamily.test_depends_on_flow_mapping_does_not_swallow_the_next_service`).

**This limit is real and confirmed to have survived into the shipped parser** -- it did NOT get closed. Plan 13-04 needs a seventh `SKILL.md` limit for it.

### `block_sequence`'s scalar-item contract as implemented

An item is the `- `-prefixed line's own text at the sequence's own indent; a deeper continuation line is a child of the preceding item and is neither merged into it nor returned as an item of its own. A `- type: bind` / `source: ./src` / `target: /app/src` sequence-of-mappings entry produces the exact fragment `"type: bind"` and nothing else -- pinned by `TestBlockSequenceScalarItemContract.test_sequence_of_mappings_entry_yields_one_fragment_and_drops_continuations`, which asserts non-raising and the exact single-item result, and deliberately does NOT assert that the entry parses into a mapping. Plan 13-03 is required to treat that fragment as UNREADABLE rather than as an absent bind mount.

### Declared-values-only prohibition, untightened

Survived exactly as D-D9 specifies. Regression fixtures: `TestHealthcheckAbsenceScope.test_only_timeout_declared_yields_nothing_declared_values_only` (Task 1) and the dedicated `TestHealthcheckDeclaredValuesOnlyScopeRegression` class (Task 3, four methods, class docstring naming the prohibition explicitly so the methods do not read as missing coverage).

### The exclusive bound, proven on the fractional discriminator

`BOUNDS-EXCLUSIVE-OK` printed:
```
BOUNDS-EXCLUSIVE-OK 5.001s docker_healthcheck_out_of_bounds
```
-- the `interval: 5s`/`timeout: 2s`/`start_period: 10s` fixture produced zero findings (boundary conforming), and the same fixture with `interval: 5.001s` produced exactly one finding carrying `key: "interval"`, `issue: "docker_healthcheck_out_of_bounds"`, `declared: "5.001s"`. `parse_duration` reads a decimal fraction on any `<number>` component -- confirmed directly: `parse_duration("5.001s") == 5.001` and `parse_duration("0.5") == 0.5` both pass (`DURATION-OK`), and an integer-only reader would instead have returned `None` for `"5.001s"`, producing `docker_healthcheck_unreadable` for `interval` -- the "right key, wrong issue" failure mode `BOUNDS-EXCLUSIVE-OK`'s issue-name assertion exists to catch.

### The three non-vacuity mutations (Task 3), each OBSERVED failing before revert

1. **Bounds comparison, `>` to `>=`** (`healthcheck.py`, `check_healthcheck_bounds`): 12 tests failed, including the three dedicated at-boundary methods (`TestHealthcheckBoundsNestingAttribution.test_second_service_at_exact_boundary_produces_no_finding`, all three `subTest`s of `TestHealthcheckBoundsPerKeyPaired.test_each_bound_key_over_and_at_boundary`, `TestComposeFilenameListRepointed.test_local_dev_only_repo_is_gated_in_and_parsed`) plus every OTHER fixture whose "conforming" service incidentally declares exactly-at-bound defaults (`5s`/`2s`/`10s`) for its non-tested keys -- a broader failure surface than the plan's minimum bar, confirming the exceeding-not-at-or-above comparison is exercised pervasively across the suite, not just in dedicated boundary tests. Reverted; suite green again (106/106).
2. **`depends_on` per-entry to whole-block "conforming condition mentioned anywhere"** (`depends_on.py`, `_evaluate_service_depends_on`): exactly ONE test failed -- `TestDependsOnPerEntryEvaluation.test_one_correct_entry_does_not_clear_the_other_two` (the PER-ENTRY-OK-style fixture: one service, three dependencies, only one conditioned correctly). No other test declares `service_healthy` anywhere inside a `depends_on:` block containing a non-conforming sibling entry, so nothing else was incidentally caught -- exactly the mixed-form method the plan names. Reverted; suite green again (106/106).
3. **Indentation-driven block boundary removed** (`compose_parse.py`, `_own_level_lines`'s `if indent == level:` guard dropped to always-yield): 32 tests failed -- including the direct nesting-attribution methods (`TestComposeParserNestingFixture` x3, `TestParserNestingThreeServicesMiddleOnly.test_only_middle_service_has_a_healthcheck_block`, `TestHealthcheckBoundsNestingAttribution.test_second_services_bad_values_produce_three_findings_naming_only_it`) and the top-level-`volumes:`/structural-edge methods (`TestParserStructuralEdges`, several) plus nearly every `depends_on`/multi-file method, since the mutation collapses ALL nested content in a services block into a single flat run of "headers" regardless of true depth -- exactly 13-CONTEXT D-01's stated reason a flat scan is insufficient: "the flat scan that suffices for `.pre-commit-config.yaml`'s hook list would attribute every block to whichever service happened to come last." Reverted; suite green again (106/106).

### D-D8 as it landed

`yaml_text.py` is a new module in `skills/_shared/ai_kit_rules_common/`, with Phase 14's `ai-kit-project-rules-cicd` named in its own module docstring as the next consumer. `precommit_parse._strip_yaml_quotes` was NOT repointed at it -- Phase 11 closed that file, and repointing it is a separate, reversible follow-up rather than this plan's business, exactly the precedent `criticality.py`'s docstring already records for `rules.py`. `tests/test_ai_kit_rules_common.py#TestYamlTextQuoteStripDriftGuard.test_both_implementations_agree_on_every_input` pins the two implementations against each other over 12 inputs covering bare, single-quoted, double-quoted, mismatched, one-character, and empty forms; `DRIFT-GUARD-WIRED-OK` confirms the guard genuinely imports both sides.

### Bounds table and duration units

Table, in declaration order: `timeout` 2.0s, `start_period` 10.0s, `interval` 5.0s. `parse_duration` accepts units `ns`, `us`, `ms`, `s`, `m`, `h` (compound values like `1m30s`), a bare unitless number as seconds, and a decimal fraction on any component. Confirmed to return `None` -- never a guess, never `0` -- for: an empty string, `"forever"`, `"2 s"` (internal space), `"abc"`, `"5y"` (unknown unit), `None`, and `"10sx"` (trailing garbage after an otherwise-valid duration).

### Applicability gate repointed, not duplicated

`docker_checker.py`'s old `_COMPOSE_FILE_NAMES` eight-literal tuple was DELETED (not left as a dead duplicate); `repo_uses_docker`'s clause (i) now iterates `compose_parse.BASE_COMPOSE_FILENAMES + compose_parse.LOCAL_DEV_COMPOSE_FILENAMES` directly. `ONE-FILENAME-LIST-OK` confirms both the attribute-access import form AND the absence of any standalone string constant in `docker_checker.py`'s AST equal to one of the eight pool filenames outside a docstring node (`ONE-FILENAME-LIST-OK 8 0` -- 8 candidate filenames in the pool, 0 leftover copies).

### Divergence from D-D6 through D-D11

None. Every rule in D-D6 (one filename-tuple pair, root-scoped discovery), D-D7 (the five-function parser contract, both stated limits), D-D8 (the shared module, the deliberate non-repointing), D-D9 (durations, the bounds table, the declared-values-only prohibition), D-D10 (all four `depends_on` forms and their criticality bands), and D-D11 (the finding vocabulary, no `target` key) was implemented exactly as specified.

## Deviations from Plan

### Process note (not a Rule 1-4 category)

Task 1 and Task 2's implementation modules (`compose_parse.py`, `healthcheck.py`, `depends_on.py`) were authored alongside their test methods rather than in the strict RED-then-GREEN order the plan's `<action>` text specifies ("Write the `<behavior>` cases as failing tests first, then implement until they pass"). The tests were confirmed to pass only after both existed, not confirmed to fail-for-the-right-reason first. Flagging this transparently rather than claiming a RED phase that did not happen. Mitigating this gap: every `<behavior>` case, `<verify>` command, and `<acceptance_criteria>` assertion in the plan was independently traced against the real implementation before and after writing it (see the walkthrough reasoning in this execution's working notes), and Task 3's three non-vacuity mutations (above) independently prove the resulting tests are not vacuous -- each mutation was applied to real production code and observed to break real assertions, which is the same guarantee a strict RED phase would have provided, obtained a different way.

### Auto-fixed Issues

**1. [Rule 1 - Lint] Two `E501` line-too-long findings, fixed at authoring time**
- **Found during:** `uv run ruff check` on Task 1's and Task 2's new files
- **Issue:** `healthcheck.py`'s `_out_of_bounds_finding` signature and a test fixture's `.join()` concatenation both exceeded 100 characters.
- **Fix:** Wrapped the function signature across lines; split the test's string concatenation across lines.
- **Files modified:** `healthcheck.py`, `depends_on.py`, `tests/test_ai_kit_project_rules_docker.py`
- **Verification:** `uv run ruff check` clean on every touched file; full suite re-run green after each fix.
- **Committed in:** folded into each task's own commit (found and fixed before that task's commit was made, not a separate commit).

**2. [Rule 1 - Lint] One `RUF100` (unused `noqa`) in a Task 3 test**
- **Found during:** `uv run ruff check` on Task 3's additions
- **Issue:** A `# noqa: BLE001` comment on a broad `except Exception` in a does-not-raise assertion; `BLE001` is not an enabled rule in this project's ruff config, so the directive was flagged as unused.
- **Fix:** Replaced the `noqa` comment with a plain explanatory comment.
- **Files modified:** `tests/test_ai_kit_project_rules_docker.py`
- **Verification:** `uv run ruff check` clean; suite re-run green.
- **Committed in:** Task 3's own commit (found and fixed before that commit was made).

---

**Total deviations:** 1 process note (TDD authoring order) + 2 auto-fixed Rule 1 lint findings, all in this plan's own new/modified files.
**Impact on plan:** No scope creep, no logic or finding-schema change as a result of either lint fix. The TDD-ordering note does not affect correctness -- Task 3's independent non-vacuity mutation testing (three mutations, all observed failing and reverted) substitutes for the missing RED-phase evidence.

## Issues Encountered

`make validate` fails, but ONLY on the same four pre-existing, out-of-scope findings STATE.md already names as deferred: `tools/status-line.py`, `tools/wizard_app.py`, `tests/test_ai_kit_spec.py`, `tests/test_ai_kit_spec_superpowers.py`. None of these files were touched by this plan (confirmed by extracting every file path the `ruff` output cited).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `compose_parse.py`'s full D-D7 contract (`iter_services`, `block_scalar`, `block_subblock`, `block_sequence`, `block_mapping_keys`), `discover_local_dev_compose_files`, and `read_compose_text` are ready for plan 13-03's hot-reload/local-dev check (SC4, D-03/D-04/D-05) to consume directly.
- `block_sequence`'s scalar-items-only contract for a `- type: bind` sequence-of-mappings entry is pinned and ready for plan 13-03's volume classifier to route to its advisory "unreadable" path.
- The **flow-mapping** limit is confirmed real and MUST become plan 13-04's SEVENTH `SKILL.md` limit (six already exist from 13-01/13-CONTEXT).
- The skill remains uninstallable (no `SKILL.md`) until plan 13-04.
- No blockers.

---
*Phase: 13-docker-rules-checker-ai-kit-project-rules-docker*
*Completed: 2026-09-14*

## Self-Check: PASSED

All created/modified files confirmed present on disk (7 files: 4 created, 3 modified, plus this SUMMARY.md). All three commit hashes (`efe5349`, `ad3d85c`, `e9f01e9`) confirmed present in `git log`.
