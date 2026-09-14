---
phase: 12-architecture-rules-checker-ai-kit-project-rules-arch
plan: 01
subsystem: testing
tags: [makefile, ast, arch-fitness, rules-checker, python]

# Dependency graph
requires:
  - phase: 11-pre-commit-rules-checker-ai-kit-project-rules-precommit
    provides: skills/_shared/ai_kit_rules_common/ (makefile_parse.py, remediation.py, criticality.py) and the sys.path-append/argparse-free CLI dispatch pattern this skill imitates
provides:
  - skills/ai-kit-project-rules-arch skill package (check/remediate CLI)
  - arch_checker.check_arch_rules(repo_root) aggregator -- extended by plan 12-02
  - D-A1 arch-test-shaped naming rule and D-A2 chaining-detection graph walk
  - "arch" added to shared STRUCTURAL_KINDS tuple
  - parse_makefile_targets_ordered added to shared makefile_parse.py
affects: [12-02, 12-03, 15-rules-orchestrator-ai-kit-project-rules-all]

# Tech tracking
tech-stack:
  added: []
  patterns: [shared-package sys.path append with named ImportError, argparse-free CLI dispatch, bounded BFS over untrusted Makefile prerequisite graph]

key-files:
  created:
    - skills/ai-kit-project-rules-arch/ai-kit-project-rules-arch.py
    - skills/ai-kit-project-rules-arch/ai_kit_project_rules_arch/__init__.py
    - skills/ai-kit-project-rules-arch/ai_kit_project_rules_arch/cli.py
    - skills/ai-kit-project-rules-arch/ai_kit_project_rules_arch/arch_checker.py
    - skills/ai-kit-project-rules-arch/ai_kit_project_rules_arch/remediation.py
    - tests/test_ai_kit_project_rules_arch.py
  modified:
    - skills/_shared/ai_kit_rules_common/makefile_parse.py
    - skills/_shared/ai_kit_rules_common/remediation.py
    - tests/test_ai_kit_rules_common.py
    - Makefile
    - .pre-commit-config.yaml
    - pyproject.toml

key-decisions:
  - "D-A1 anchoring mechanism: re.fullmatch with NO trailing $ (not re.match with ^...$)."
  - "D-A2 clause (ii) bounds: depth_bound=8, breadth_bound=512, both written first as guards, not later hardening."
  - "No cache surface, no third subcommand -- D-A6 held exactly as specified."

requirements-completed: [REQ-rules-arch]

# Metrics
duration: ~25min
completed: 2026-09-14

actuals:
  tokens: 15400
  tasks: 2
  commits: 2
  plan_head_before: 6fddd35dde9f0f8561749f62884c7cbce5f31d2

status: complete
---

# Phase 12 Plan 01: Architecture Rules Checker Tracer (ai-kit-project-rules-arch) Summary

**Wired `ai-kit-project-rules-arch`'s check/remediate CLI end-to-end for two distinct findings -- a missing arch-test-shaped Makefile target, and one that exists but is never chained into `test` -- proven against ai-kit's own `Makefile:61`/`Makefile:66` (this repo's real `arch-test`/`test` wiring) producing neither finding.**

**Backlog resolution (ROADMAP Phase 12 Success Criterion 5):** This phase promotes and resolves
`.planning/ROADMAP.md`'s Backlog entry "Phase 999.3: Architecture-layer test suite" at this
milestone's scoped-down, form/convention-only ambition -- `arch-test` Makefile target existence,
chaining into `test`, and (plan 12-02) AST-only-ness of the backing test file. The backlog note's
fuller dependency-direction/layering-boundary enforcement ambition across the whole
`tools/`/`skills/` tree remains an explicitly-flagged known gap, NOT built here. The backlog stub
itself is left unchanged in `ROADMAP.md`; this phase is its resolution, not a second, separate
item.

## Environment note (pre-execution)

The dispatched worktree was branched from `main` before Phases 9-11 landed (a known,
previously-encountered issue for this phase family). Confirmed the worktree HEAD (`b30c0b2`) was a
non-diverged ancestor of `main` (`git merge-base --is-ancestor HEAD main` succeeded) and
fast-forwarded losslessly: `git merge --ff-only main` -> `6fddd35dde9f0f8561749f62884c7cbce5f31d2`
(this plan's `plan_head_before`). All four of Task 1's precondition checks then passed on the
fast-forwarded tree. All `git` invocations throughout this run used the absolute path `/usr/bin/git`
per this host's known bare-`git` PreToolUse hook pattern-matching quirk.

## Performance

- **Duration:** ~25 min (including the fast-forward, full read_first pass, and verification)
- **Started:** 2026-09-14T09:2x (approx, Task 1 commit at 09:29:12-04:00)
- **Completed:** 2026-09-14T09:37:49-04:00 (Task 2 commit)
- **Tasks:** 2 / 2
- **Files modified:** 12 (6 created, 6 modified)

## Accomplishments
- New `ai-kit-project-rules-arch` skill: `check`/`remediate` CLI over a target repo's Makefile,
  detecting (a) whether an arch-test-shaped target exists (D-A1) and (b) whether it is chained
  into `test` (D-A2), as two DISTINCT findings that never stand in for each other (D-A3/D-A4).
- Two shared-package edits, both additive: `parse_makefile_targets_ordered` added to
  `skills/_shared/ai_kit_rules_common/makefile_parse.py` (D-A1's declaration-order tie-break now
  comes from the shared parser, never a private header scan), and `"arch"` appended to
  `STRUCTURAL_KINDS` in `skills/_shared/ai_kit_rules_common/remediation.py`.
- Full test suite: 43 tests in `tests/test_ai_kit_project_rules_arch.py` (Task 1's six tracer
  cases plus Task 2's paired existence/chaining/shape/mechanism/degradation/gate-registration
  coverage) and 12 new tests in `tests/test_ai_kit_rules_common.py` (grown from 80 to 92 tests).
- Registered in every quality gate its three siblings are in (`Makefile` test-unit + lint,
  `.pre-commit-config.yaml` ruff/py-compile/unittest, `pyproject.toml` pyright/vulture), proven
  by the suite's own `TestGateRegistration` class and by `make lint`/`make test-unit` exercising
  the real recipes.
- Confirmed against ai-kit's own repository root: `check(".")` returns `{"arch": []}` -- the
  positive fixture at `Makefile:61` (`arch-test:`) and `Makefile:66`
  (`test: test-unit test-integration e2e-test arch-test`) is recognised by the general rules,
  never special-cased.

## Task Commits

1. **Task 1: Wire the new skill end-to-end** - `6cbe38c` (feat, tdd tracer)
2. **Task 2: Fill out the new suite + pin grown structural-kind tuple** - `f2c68ec` (test)

**Plan metadata:** (this commit, docs: complete plan)

## Files Created/Modified
- `skills/ai-kit-project-rules-arch/ai-kit-project-rules-arch.py` - entrypoint, repoints at the package
- `skills/ai-kit-project-rules-arch/ai_kit_project_rules_arch/__init__.py` - shared-package sys.path append with named ImportError
- `skills/ai-kit-project-rules-arch/ai_kit_project_rules_arch/arch_checker.py` - D-A1/D-A2/D-A4 logic, the aggregator `check_arch_rules`
- `skills/ai-kit-project-rules-arch/ai_kit_project_rules_arch/cli.py` - argparse-free `check`/`remediate` dispatch, no third subcommand
- `skills/ai-kit-project-rules-arch/ai_kit_project_rules_arch/remediation.py` - thin re-export of the shared `build_remediation`
- `tests/test_ai_kit_project_rules_arch.py` - 43 tests: tracer + paired fixtures + gate registration
- `skills/_shared/ai_kit_rules_common/makefile_parse.py` - additive `parse_makefile_targets_ordered`; `parse_makefile_targets` redefined in terms of it
- `skills/_shared/ai_kit_rules_common/remediation.py` - `STRUCTURAL_KINDS` grown to `("makefile", "precommit", "arch")`
- `tests/test_ai_kit_rules_common.py` - `TestRemediationArchKind`, `TestParseMakefileTargetsOrdered` (80 -> 92 tests)
- `Makefile` - `test-unit`/`lint` recipes register the new module/package
- `.pre-commit-config.yaml` - `ruff`/`py-compile` `files:` regexes and `unittest` `entry:` list grown
- `pyproject.toml` - `[tool.pyright] include` and `[tool.vulture] paths` grown

## Decisions Made

### D-A1 shape rule, as implemented

Normalize (casefold, `_` -> `-`), then match EITHER pattern with `re.fullmatch` (no trailing `$`
in either pattern -- the single anchoring mechanism, per D-A1's prohibition on combining
`re.fullmatch` with a trailing `$`):

```
_ARCH_SHAPE_PATTERN_DIRECT   = r"(arch|architecture)(-(test|tests|check|checks|lint|fitness|rules))?"
_ARCH_SHAPE_PATTERN_PREFIXED = r"(test|check|lint)-(arch|architecture)(-(test|tests|check|checks))?"
```

`re.fullmatch(...)` over either pattern. This is the mechanism Task 2's non-vacuity mutation
targeted (`fullmatch` -> `match`).

### D-A2's three chaining clauses, as implemented

- Clauses (i) and (ii) share one bounded breadth-first walk from `test` over
  `parse_makefile_prerequisites`, in `_reachable_via_prerequisite_graph`: a `visited` set seeded
  with `{"test"}`, a **depth bound of 8** (a node is only explored -- its own prerequisites
  checked -- if its own depth is `< 8`, so a target up to 8 hops away is reachable), and a
  **breadth bound of 512** distinct visited targets (reaching it ends the walk immediately,
  returning `False`). Direct prerequisite (clause i) is the depth-0-exploration special case of
  the same walk -- no separate code path.
- Clause (iii) is a plain call to the shared `recipe_mentions_target(parse_makefile_recipe(path,
  "test"), target_name)`.
- `is_chained` ORs the BFS result with clause (iii)'s result, so reaching either bound before the
  target is found always falls through to checking clause (iii) -- exactly D-A2's "fall through,
  never conclude anything from the truncation" rule, satisfied structurally by evaluating clause
  (iii) unconditionally rather than only on a BFS miss reported as "genuinely absent."

### Non-vacuity mutation (D-A1, Task 2 acceptance criterion)

Applied the mutation matching the chosen mechanism: changed both `re.fullmatch(...)` calls in
`is_arch_test_shaped` to `re.match(...)`. Ran `tests.test_ai_kit_project_rules_arch` -- **failure
was OBSERVED**: exactly 4 tests failed (`test_archive_target_missing_flagged`,
`test_arch_docs_target_missing_flagged`, `test_architecture_diagrams_target_missing_flagged`,
`test_archive_is_not_arch_test_shaped`), all and only the negative-shape-alternative tests; every
other test (including all six positive-shape-alternative tests) continued to pass. Reverted
immediately to `re.fullmatch`; re-ran the suite -- 43/43 green again.

### Two shared-package edits, recorded separately

1. **`STRUCTURAL_KINDS` growth** (`skills/_shared/ai_kit_rules_common/remediation.py`): one name
   appended, tuple order preserved (`("makefile", "precommit", "arch")`). Proved
   behavior-preserving by: `REMEDIATION-BACKCOMPAT-OK` (a report carrying only the two
   pre-existing kinds produces the pre-change payload field-by-field, asserting the tuple's first
   two entries and their order); `CROSS-KIND-ORDER-OK` and the new
   `TestRemediationArchKind.test_all_three_kinds_order_as_one_list_disagreeing_with_insertion_order`
   (all three kinds fold into ONE criticality-sorted list, with insertion order deliberately
   disagreeing with criticality order so a per-kind implementation cannot pass); and running all
   three sibling suites (`test_ai_kit_project_rules_makefile`, `test_ai_kit_project_rules_precommit`,
   `test_ai_kit_project_rules_agents`) green.
2. **`parse_makefile_targets_ordered` addition** (`skills/_shared/ai_kit_rules_common/makefile_parse.py`):
   one additive public function over the same module-private `_TARGET_HEADER_RE`
   `parse_makefile_targets` already used; `parse_makefile_targets` redefined as
   `set(parse_makefile_targets_ordered(path))`. Proved behavior-preserving by
   `MAKEFILE-PARSE-BACKCOMPAT-OK` (declaration order on a fixture built so it differs from
   alphabetical order; first-occurrence de-duplication on a repeated target header; the `VAR :=`
   and `.PHONY:` exclusions both still apply; absent-file empty-list/empty-set behavior for both
   readers; `__all__` grew rather than changed; and the set reader is asserted to equal
   `set(ordered reader's output)`) and by the new
   `TestParseMakefileTargetsOrdered` class in the shared suite, placed beside the existing
   `parse_makefile_targets` coverage.

### No `target` key; the two remediate `id`s

Confirmed on both findings via `TestFindingSchema`: the missing-target and not-chained findings
each carry exactly `{category, issue, criticality, summary, recommendation, needs_research}` and
neither carries a `target` key. `TestFindingSchema.test_remediate_ids_equal_categories_and_are_distinct`
proves the property `remediation.py:86` makes load-bearing: `remediate`'s entry `id` for the
missing-target fixture equals `"arch-test-target"` (its finding's `category`), the not-chained
fixture's entry `id` equals `"arch-test-chaining"`, and the two are distinct.

### D-A6: no cache surface, no third subcommand

Confirmed as a deliberate difference from the Phase 10/Phase 11 siblings, not an omission.
`cli.py` dispatches exactly `check`/`remediate`; no `stack_cache.py`/`tooling_payload.py` file
exists in the package; no non-comment line in the package's source contains the word "cache" (the
`NO-CACHE-SURFACE-OK` acceptance criterion). Plan 12-03's `SKILL.md` should therefore document two
subcommands, not four.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `cli.py` module docstring's use of the literal word "cache" tripped `NO-CACHE-SURFACE-OK`**
- **Found during:** Task 1's `NO-CACHE-SURFACE-OK` acceptance-criteria run
- **Issue:** The docstring explaining D-A6 ("No `cache-update` and no third subcommand...")
  contained the literal substring "cache" in non-comment source text, which the acceptance
  criterion's `'cache' not in body.lower()` check (comment lines stripped) treats as a violation
  regardless of intent.
- **Fix:** Reworded the docstring to convey the same D-A6 rationale without the literal word
  "cache" (references "third subcommand" and "research dispatch" instead).
- **Files modified:** `skills/ai-kit-project-rules-arch/ai_kit_project_rules_arch/cli.py`
- **Verification:** Re-ran the `NO-CACHE-SURFACE-OK` command; passed.
- **Committed in:** `6cbe38c` (Task 1 commit)

**2. [Rule 1 - Bug] Fixed 3 ruff findings (RUF100 unused noqa, 2x E501) in this plan's own new test file during `make validate`**
- **Found during:** Task 2's `make validate` verification pass
- **Issue:** `make validate` (via `uv run pre-commit run ruff --all-files`) flagged an unused
  `# noqa: E402` (redundant since `tests/*` already ignores E402 via
  `[tool.ruff.lint.per-file-ignores]`) and two lines over the 100-char limit in
  `tests/test_ai_kit_project_rules_arch.py` -- a file this plan itself authored, so in scope per
  the plan's own instruction ("Any finding in a path this plan touched is in scope and must be
  fixed here").
- **Fix:** Removed the redundant `# noqa: E402`; wrapped the `_SCHEMA_FIELDS` set literal and the
  `with tempfile.TemporaryDirectory() as ..., tempfile.TemporaryDirectory() as ...:` line (switched
  to parenthesized multi-context-manager form) to fit the line-length limit.
- **Files modified:** `tests/test_ai_kit_project_rules_arch.py`
- **Verification:** `uv run ruff check tests/test_ai_kit_project_rules_arch.py
  skills/ai-kit-project-rules-arch/` returned `[]`; re-ran the full test suite (43/43 green).
- **Committed in:** `f2c68ec` (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (1 blocking, 1 bug -- both Rule 1/3, no architectural changes).
**Impact on plan:** Neither changed the checker's logic or the finding vocabulary; both are
lint-hygiene fixes to this plan's own new files. No scope creep.

### No divergence from D-A1 through D-A6

No target in ai-kit's own `Makefile` other than `arch-test` matched D-A1's shape rule -- confirmed
by the tracer's `isf` (ai-kit-self) result being empty (`[]`, i.e. neither finding fires, which
would not hold if a second, wrongly-declared-first target were shadowing `arch-test`) and by
manually enumerating `Makefile`'s declared targets against the shape patterns: `install`,
`reconfigure`, `uninstall`, `doctor`, `check`, `setup-env`, `dev`, `test-unit`, `test-integration`,
`e2e-test`, `arch-test`, `test`, `lint`, `py-compile`, `pylint`, `pyright`, `ruff`, `shellcheck`,
`vulture`, `unittest`, `unittest-wizard`, `format`, `security-scanner`, `duplicate-code`,
`validate`, `e2e-docker`. Only `arch-test` matches (`test-unit`/`test-integration` do not, since
neither alternative's prefix set includes `unit`/`integration`; `check`/`test` alone would match
the direct pattern's bare `arch`/`architecture` alternative only if they equalled `arch` or
`architecture`, which they do not). So plan 12-02's downstream checks run against `arch-test`, as
intended.

## Issues Encountered

**`make validate` fails on pre-existing, out-of-scope findings** -- confirmed via the same-shape
per-hook runs `make pylint`, `uv run pre-commit run pyright --all-files --hook-stage pre-push`,
`make shellcheck`, `make py-compile`, `uv run pre-commit run unittest[-wizard] --all-files
--hook-stage pre-push` (since `validate`'s prerequisite chain halts at the first failing
prerequisite, `ruff`, before reaching later ones):

- `ruff`/`pylint`: fail only on `tools/status-line.py`, `tools/wizard_app.py`,
  `tests/test_ai_kit_spec.py`, `tests/test_ai_kit_spec_superpowers.py` -- exactly the four files
  STATE.md already names as pre-existing and out-of-scope. None touched by this plan.
- `pyright`: fails on ONE finding not previously named in STATE.md's list --
  `skills/ai-kit-project-rules-precommit/ai_kit_project_rules_precommit/pair_checks.py:178:26`
  (`"object" is not iterable`). This file was last modified by the pre-existing Phase 11 commit
  `a01cac8` (part of this plan's fast-forward, landed before this plan started) and is untouched
  by this plan -- out of scope per the plan's own scope-boundary rule, but flagged here explicitly
  since it is a newly-surfaced discrepancy against STATE.md's named list, not previously recorded.
- `vulture`, `shellcheck`, `py-compile`, `unittest`, `unittest-wizard`: all pass clean, including
  against the newly-registered `skills/ai-kit-project-rules-arch` and
  `tests/test_ai_kit_project_rules_arch` paths.
- `make test` (the AGENTS.md four-tier pyramid, including `uv`-dependent tiers) passes fully --
  `uv` was available throughout this run, so no environment-gap deflection applies.

## Next Phase Readiness

- `arch_checker.check_arch_rules`'s branch structure is ready for plan 12-02 to extend by
  appending one call inside the target-FOUND branch (the AST-only check) and attaching text to the
  existing missing-target finding's `recommendation` in the target-ABSENT branch (the per-stack
  canonical-tool text) -- neither addition requires restructuring this function.
- `find_arch_test_shaped_target`/`is_arch_test_shaped`/`is_chained`/`normalize_target_name` are
  all exported from `arch_checker.__all__` alongside `check_arch_rules`, so plan 12-02 can reuse
  the same resolved target name without re-running D-A1.
- No blockers. The skill remains uninstallable (no `SKILL.md`) until plan 12-03, as intended.

---
*Phase: 12-architecture-rules-checker-ai-kit-project-rules-arch*
*Completed: 2026-09-14*

## Self-Check: PASSED

All 13 created/modified files verified present on disk; both task commits (`6cbe38c`, `f2c68ec`)
verified present in `git log --oneline --all`.
