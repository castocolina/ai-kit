---
phase: 12-architecture-rules-checker-ai-kit-project-rules-arch
plan: 02
subsystem: ai-kit-project-rules-arch
tags: [architecture-checker, ast-analysis, static-analysis, rules-checker]
dependency-graph:
  requires:
    - 12-01: arch_checker.check_arch_rules aggregator, D-A1 shape rule, D-A2 chaining, D-A3 schema, D-A4 evaluation gate, arch-test-target/arch-test-chaining categories
  provides:
    - ast_only.build_ast_only_findings: target-aware AST-only correlation (arch-test-ast-only category)
    - canonical_tools.canonical_tool_advice: per-stack canonical-tool baseline text
  affects:
    - skills/ai-kit-project-rules-arch/ai_kit_project_rules_arch/arch_checker.py (check_arch_rules)
tech-stack:
  added: []
  patterns:
    - "AST scope-tracking visitor (Module/FunctionDef-scoped Assign/Call mapping) for one-level local name resolution on both sides of a correlation"
    - "Candidate-formed vs candidate-resolved distinction in file discovery, to separate 'no evidence' (silent) from 'evidence found but unreachable' (advisory)"
key-files:
  created:
    - skills/ai-kit-project-rules-arch/ai_kit_project_rules_arch/ast_only.py
    - skills/ai-kit-project-rules-arch/ai_kit_project_rules_arch/canonical_tools.py
  modified:
    - skills/ai-kit-project-rules-arch/ai_kit_project_rules_arch/arch_checker.py
    - tests/test_ai_kit_project_rules_arch.py
decisions:
  - "not_discoverable fires only when the arch-test recipe formed at least one file-shaped candidate (matched D-A7's extension or dotted-identifier rule) that failed to resolve -- a recipe forming ZERO candidates (e.g. a bare 'echo' no-op) produces no finding at all, silently. This refinement was required empirically: nearly all of 12-01's own committed paired fixtures use an 'echo a' arch-test recipe and assert zero findings; a literal, unconditional not_discoverable would have broken 17 of them."
  - "D-01's scouting claim is corrected: tests/test_arch.py's architecture-fitness METHODS are AST-only, but the FILE is not -- TestSegmentInventory._sl (605-611) loads tools/status-line.py, the same module _parse('status-line.py') (374) checks. A faithful implementation correctly flags this. Disclosed below, not suppressed."
metrics:
  duration: "~2.5h"
  completed: "2026-09-14"
actuals:
  tokens: 11767
  tasks: 3
  commits: 3
  plan_head_before: 52a796e0f251ae3c60b957abd789d6b54e8eecdf
status: complete
---

# Phase 12 Plan 02: AST-Only Correlation + Canonical-Tool Baseline Summary

Target-aware AST-only-ness check for the arch-test backing file (parses vs.
imports/executes its subject), plus a hardcoded per-stack canonical-tool
recommendation with an explicit Rust/Go known-gap disclosure -- ROADMAP
Phase 12 Success Criteria 3 and 4.

## Backlog resolution (ROADMAP Phase 12 Success Criterion 5)

> This phase promotes and resolves `.planning/ROADMAP.md`'s Backlog entry
> "Phase 999.3: Architecture-layer test suite" at this milestone's
> scoped-down, form/convention-only ambition -- `arch-test` Makefile target
> existence, chaining into `test`, and AST-only-ness of the backing test
> file. The backlog note's fuller dependency-direction/layering-boundary
> enforcement ambition across the whole `tools/`/`skills/` tree remains an
> explicitly-flagged known gap, NOT built here. The backlog stub itself is
> left unchanged in `ROADMAP.md`; this phase is its resolution, not a
> second, separate item. This plan is where that boundary is most tempting
> to cross: it reads a backing test file's AST, which is one short step
> from trying to enforce dependency direction. Do not take that step.

## D-01 re-verification (live-verified correction to 12-CONTEXT)

**Command run:**

```
python3 skills/ai-kit-project-rules-arch/ai-kit-project-rules-arch.py check .
```

**Result:** ONE `arch-test-ast-only` finding was produced, `issue:
"backing_file_executes_checked_target"`, naming module `'status-line'`.

**Correlated locations:**
- Parse call: `tests/test_arch.py:374` -- `cls.render_tree, cls.render_src
  = _parse("status-line.py")` inside `TestArchitecture.setUpClass`
  (`_parse` at line 87 is a parser-helper function calling `ast.parse`
  directly, so this call site's literal `"status-line.py"` is a parsed
  subject via the fixed point).
- Load call: `tests/test_arch.py:605-611`, `TestSegmentInventory._sl` --
  `sl_path = os.path.join(_TOOLS, "status-line.py")` (606) then
  `spec = importlib.util.spec_from_file_location("status_line_inv",
  sl_path)` (607). `sl_path` is a bare `Name` argument resolved one level
  against its own function-scope assignment, contributing the literal
  `"status-line.py"` to the executed subjects.

Both normalize to `"status-line"` via the shared normalizer
(`_normalize_module_token`), and their intersection is non-empty, so the
finding fires.

**Does this confirm or contradict D-01's scouting claim?** It corrects it.
D-01 stated: *"`tests/test_arch.py` loads `tools/setup.py` ... for
incidental inventory-test helpers, while its actual architecture-fitness
checks ... parse `tools/status-line.py` -- the real checked target -- via
pure `ast.parse`, never importing it."* The first half (the `setup.py`
load being unrelated and correctly unflagged) is confirmed live: the
`CLEAN`-shaped correlation does NOT flag `tools/setup.py`. The second half
is contradicted: the architecture-fitness *methods* (`test_rule1_...`
etc.) are indeed AST-only, but the *file* also contains
`TestSegmentInventory._sl`, which loads the exact module those methods
parse, for unrelated segment-inventory tests. This is a TRUE statement
about this repo, discovered by live verification, not suppressed or
narrowed to make the repo come back clean. No edit was made to
`tests/test_arch.py` in this plan -- that file is out of this plan's
`<files>`, and changing a test to satisfy a checker written in the same
phase would be the reverse of verification.

**ROADMAP SC1 status:** unaffected. `check .` produces exactly one
finding, `arch-test-ast-only`, and no `arch_test_target_missing` /
`arch_test_not_chained` -- SC1 is scoped to those two categories only.

## D-A7 discovery heuristic as implemented

Function: `find_backing_test_file(repo_root, makefile_path, target_name)`
in `ast_only.py`, returning `(backing_file_path_or_None,
any_candidate_formed)`.

- Tokenizes the recipe (`parse_makefile_recipe`), skipping flag-shaped
  (`-...`) and assignment-shaped (`...=...`) tokens.
- Per remaining token, in recipe order: rule (i) source-extension suffix
  (`.py`/`.ts`/`.tsx`/`.js`/`.java`/`.kt`/`.go`/`.rs`), then rule (ii)
  dotted-identifier path (`tests.test_arch` -> `tests/test_arch.py`).
- Containment guard (`ast_only.py:136-140`, applied BEFORE `os.path.isfile`
  at line 141): `real_candidate = os.path.realpath(candidate)`, then
  accept only `real_candidate == real_repo_root or
  real_candidate.startswith(real_repo_root + os.sep)`. Copied verbatim
  from `skills/ai-kit-project-rules-agents/ai_kit_project_rules_agents/cli.py:65-69`
  (the same `if not (real_link == real_repo_root or
  real_link.startswith(real_repo_root + os.sep))` shape), per D-A7's
  explicit instruction to reuse this family's one containment idiom
  rather than inventing a second.

**Escape fixture results:**
- Parent-traversal (`python3 ../outside.py`, a real file one level above
  the repo root): rejected. Advisory `reason: "not_discoverable"`.
- Sibling-prefix (`<tmp>/repo-evil/leak.py`, absolute path, sibling of
  `<tmp>/repo`): rejected. Advisory `reason: "not_discoverable"`. This is
  the case a bare, unresolved `startswith(repo_root)` would wrongly
  ACCEPT (`<tmp>/repo-evil` textually starts with `<tmp>/repo`); the
  `os.sep`-bounded prefix test is what rejects it correctly.

Both leak files were shaped to produce a REAL (wrong) finding if actually
read, so a containment bypass would surface as a wrong finding rather than
silence -- confirmed by construction, not just by the `not_discoverable`
assertion.

**Refinement beyond the literal D-A9 text (see Deviations):** discovery
also reports `any_candidate_formed`, and `_find_ast_only_finding` returns
no finding at all (not even an advisory) when zero candidates were formed
across the whole recipe -- as opposed to firing `not_discoverable`
whenever the file simply doesn't resolve. See Deviations for why this was
necessary.

## D-A8 correlation as implemented

- **Fixed point:** `_build_parser_helpers` marks a function name as a
  "parser helper" when its body directly contains a call to `ast.parse`
  (or the `from ast import parse` alias); then iterates to a fixed point
  so a function calling a parser helper becomes one too (proven by the
  two-level fixture: `_a` calls `_b`, `_b` calls `ast.parse` -- `_a`
  becomes a helper on the second pass).
- **One-level local name resolution** is applied on BOTH sides through
  ONE shared helper, `_collect_call_literals(call, assignments)`
  (`ast_only.py`), which both the parsed-subjects loop and the
  executed-subjects loop in `_find_ast_only_finding` call. For a bare
  `Name` argument, it resolves against `_ScopeCollector.scope_assignments`
  (the nearest enclosing Module/FunctionDef scope's own `Assign`
  statements) -- one level only, no chase into another function's scope.
  This is what makes the EXECUTE side see through
  `sl_path = os.path.join(_TOOLS, "status-line.py")` /
  `spec_from_file_location("status_line_inv", sl_path)` and collect
  `"status-line.py"` rather than only the unrelated alias literal
  `"status_line_inv"`.
- **Shared normalizer:** `_normalize_module_token` (last path component,
  strip known source extension, last dotted component, casefold, fold `_`
  to `-`). Confirmed exactly one such function exists, called from >= 2
  sites (`ONE-NORMALIZER-OK` printed `['_normalize_module_token']`, 4
  call sites).
- **NAMED fixture result** (variable-then-pass load of the module that IS
  parsed, under an unrelated alias): flagged exactly once; the finding's
  `summary` names `target_mod`/`target-mod` and does NOT contain
  `target_alias_zz` / `target-alias-zz` -- the finding names the module,
  not the load alias.
- **Stated limits** (also in `ast_only.py`'s module docstring): no
  cross-module dataflow, no resolution of a name assigned in another
  function's scope, no dynamic/computed module names. Where the mechanism
  cannot see, it emits an advisory rather than a guess.

## The four not-verifiable reasons (pinned enum, as emitted)

Exactly these four literal `reason` field values, verified via the `got`
mapping in Task 1's verify command and via
`test_emitted_reason_is_always_a_member_of_the_pinned_four_value_set`:

- `not_discoverable`
- `not_python`
- `unparseable`
- `no_parse_call`

## Canonical-tool baseline

- `detect_stacks(repo_root)` is called ONCE, inside
  `_missing_target_finding(repo_root)` in `arch_checker.py` -- the only
  finding this text is ever attached to, since the tool choice is already
  made once an arch-test target exists.
- Five rows in `canonical_tools.py`'s `_CANONICAL_TOOLS` dict:
  - `python` -> `import-linter -- static, AST-only via Grimp, safe against untrusted target-repo code, and config-DSL 'contracts' ...`
  - `node` -> `dependency-cruiser -- the broadest static rule surface (circular dependencies, path-based layering, orphan detection) with no build or type-system dependency.`
  - `java` -> `ArchUnit -- runs as ordinary JUnit tests in the normal test suite rather than as a side lint pass, the most consistently recommended pattern across sources surveyed ...`
  - `rust` -> `known gap -- no equally canonical, dedicated architecture-fitness tool surfaced in research for Rust, and this skill declines to assert a false canonical choice for it.`
  - `go` -> `known gap -- no equally canonical, dedicated architecture-fitness tool surfaced in research for Go, and this skill declines to assert a false canonical choice for it.`

## Human check: findings against ai-kit's own repository root

**`check .`:**

| Category | Issue | Criticality | Judgement |
|---|---|---|---|
| `arch-test-ast-only` | `backing_file_executes_checked_target` | 3 (MEDIUM) | TRUE statement uz may want to act on -- `tests/test_arch.py`'s `TestSegmentInventory._sl` genuinely loads `tools/status-line.py` via `spec_from_file_location` + `exec_module`, the same module `_parse("status-line.py")` architecturally checks via pure `ast.parse`. Not a checker defect. A future, separately-decided fix would either (a) switch `_sl`'s segment-inventory tests to read the source text directly instead of executing the module, or (b) accept the load as an intentional, out-of-scope exception (the segment-inventory tests need real runtime values, not just AST shape) and leave this finding as a documented, permanent advisory-level observation about this repo. Neither decision is made here -- this plan discloses, it does not fix. |

No `arch_test_target_missing` / `arch_test_not_chained` finding -- ROADMAP
SC1 holds.

**`remediate .`:** one entry, `kind: "arch"`, `id: "arch-test-ast-only"`,
`auto_apply: true` (the real finding carries no `advisory` key, so
`build_remediation`'s default applies). `blocked: []`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug, discovered via empirical testing] `not_discoverable`
narrowed to require at least one recipe-formed candidate, not unconditional
firing on discovery failure**
- **Found during:** Task 1, after implementing D-A9 literally (fire
  `not_discoverable` whenever `find_backing_test_file` returns `None`) and
  running the full suite.
- **Issue:** A literal reading breaks 17 pre-existing tests in 12-01's own
  committed `tests/test_ai_kit_project_rules_arch.py` (e.g.
  `TestChainingMechanisms`, `TestShapeRulePositiveAlternatives`,
  `TestGraphSafety`) -- nearly all of which use `arch-test:\n\techo a\n`
  as their fixture's recipe and assert `_findings(repo) == []`. `"echo a"`
  forms literally zero file-shaped candidates (neither token matches
  D-A7's extension or dotted-identifier rule), so under a literal reading
  every one of these pre-existing "clean, chained" fixtures would newly
  acquire an `ast_only_not_verifiable` advisory.
- **Fix:** `find_backing_test_file` now also returns whether the recipe
  formed AT LEAST ONE file-shaped candidate (`any_candidate_formed`).
  `not_discoverable` fires only when a candidate WAS formed but failed to
  resolve (e.g. `lint-imports --config importlinter.ini`'s
  `"importlinter.ini"` token matches the dotted-identifier rule but
  doesn't exist as a file, or a candidate is rejected by containment). A
  recipe that forms ZERO candidates at all (e.g. `echo a`, a bare no-op)
  produces no finding, silently -- there is no evidence this target even
  points at a checkable file. This distinction is not explicit in D-A9's
  prose (which reads "no candidate ... resolved to an existing regular
  file" without separating "zero candidates attempted" from "a candidate
  attempted and failed"), but it is the only reading consistent with
  BOTH 12-01's already-committed fixtures AND this plan's own `nd`/`esc`/
  `sib` fixtures (which all form a real candidate that then fails).
- **Files modified:** `ast_only.py`
- **Commit:** `c8581e9`

### Discovered, Unresolved Tension (reported, not silently worked around)

**12-01-PLAN.md's own `<verify>` tracer command (already merged, out of
this plan's `<files>`) cannot be satisfied verbatim by a faithful D-A9
implementation, specifically for its fixture `a`.**

- **What was found:** Re-running 12-01's committed tracer one-liner
  verbatim (per this plan's Task 1 acceptance criterion) after
  implementing the refinement above still fails one assertion:
  `assert len({x['category'] for x in F})==2, F` (`F = ra['arch'] +
  rb['arch']`). Fixture `a`'s recipe is
  `"python3 -m unittest tests.test_arch"`, run inside a bare temp dir
  containing ONLY a `Makefile` (no `tests/` subdirectory at all). The
  token `"tests.test_arch"` DOES match D-A7's dotted-identifier rule
  (candidate ii) -- indeed, D-A7's own text names `"tests.test_arch"` as
  its canonical worked example -- and the resulting candidate
  `tests/test_arch.py` genuinely does not exist in that synthetic repo.
  A faithful implementation therefore emits an HONEST `not_discoverable`
  advisory for fixture `a`, adding a THIRD category
  (`arch-test-ast-only`) to `F` alongside the two 12-01 pinned
  (`arch-test-chaining`, `arch-test-target`), which `len(...)==2` cannot
  tolerate.
- **Why this is not fixed by narrowing further:** The `nd` fixture in
  THIS plan's own Task 1 verify command (`lint-imports --config
  importlinter.ini`) is structurally IDENTICAL to fixture `a` -- both
  form exactly one dotted-identifier candidate that does not resolve --
  and `nd` is REQUIRED to produce `not_discoverable`. There is no
  further narrowing of the discovery/advisory mechanism that
  distinguishes these two cases without inventing a rule nowhere stated
  in D-A7/D-A9 (e.g. treating a `python3 -m unittest` invocation
  specially), which would be exactly the kind of after-the-fact tuning
  this plan's correction section prohibits for the correlation, applied
  instead to discovery.
- **What was NOT done:** 12-01-PLAN.md was not edited (it is out of this
  plan's `<files_modified>` and already merged to `main`). The
  correlation and discovery mechanisms were not narrowed to make this
  synthetic, already-merged shell one-liner pass at the cost of D-A9's
  own mandate ("the skill never stays silent about a limit it has").
- **What DOES hold, fully:** Task 1's own authoritative verify command
  (`AST-ONLY-OK`, the load-bearing gate per the Round-1 cross-AI review
  that specifically targeted this exact class of failure mode) passes
  completely. All 65 tests in the actual committed test suite pass (the
  suite is what Task 3 grows permanently, not the historical shell
  one-liner). The real ai-kit repository correctly produces the D-01
  disclosure finding and no SC1 regression. `ig`/`ib`/`isf`/`ic`/`ie`
  (12-01's OTHER five tracer fixtures) all still hold under both their
  original and their membership-only assertions.
- **Recommended follow-up:** a small, separately-decided update to
  12-01-PLAN.md's own `<verify>` block (relaxing
  `len({categories})==2` to a membership check, matching the pattern
  already used for `ia`/`ib`/`isf` in the same command) would fully
  reconcile this. Not made here -- it is a change to another plan's
  already-merged content, outside this plan's authority and `<files>`.

**2. [Rule 3 - Blocking issue] Fixed 6 pre-existing ruff findings in
`ast_only.py`**
- **Found during:** Task 3's `make validate` run.
- **Issue:** `ruff` (SIM102/SIM103/E501) flagged nested-if / inline-return
  / line-length issues in `ast_only.py` as committed in Task 1 -- these
  directly blocked this task's own `make validate` requirement.
- **Fix:** Combined nested `if` statements, inlined a boolean return, and
  wrapped two long lines. No behavior change (confirmed: all 65
  `test_ai_kit_project_rules_arch` tests plus the `AST-ONLY-OK` command
  still pass identically after the fix).
- **Files modified:** `ast_only.py`
- **Commit:** `06b42f2`
- **Acceptance-criterion impact, named explicitly:** Task 3's acceptance
  criterion "`git show --stat --format= HEAD` lists only the one test
  file" is therefore NOT literally met -- the commit lists two files
  (`ast_only.py` and the test file). The alternatives considered were (a)
  amend Task 1's commit, prohibited by this workflow's git safety
  protocol, or (b) a fourth, plan-unlisted commit, which would misrepresent
  a lint fix as its own task. Folding it into Task 3's commit, discovered
  by and required for Task 3's own `make validate` step, was judged the
  most honest option; named here rather than silently claiming the
  criterion passed.

None other. No narrowing was applied to make ai-kit's own repository come
back clean on the CORRELATION itself; no edit was made to
`tests/test_arch.py`.

## Non-Vacuity Mutations (confirmed, then reverted)

All three required mutations were performed, observed to fail exactly the
expected method(s), and reverted. Each command below was re-run after
reverting to confirm the suite returned to `OK`.

1. **Clean/dirty pair:** temporarily replaced
   `intersection = parsed_subjects & executed_subjects; if not
   intersection: return None` with an unconditional non-empty
   intersection in `ast_only.py`. Result: exactly ONE failure --
   `test_ast_parse_clean_file_parsing_one_module_and_loading_unrelated_one_not_flagged`.
   Nothing else failed. Reverted; suite returned to 65/65 `OK`.
2. **Name-resolution coverage:** temporarily replaced the execute-side
   loop's `assignments = collector.scope_assignments.get(scope, {})`
   with `assignments = {}` (disabling name resolution on the EXECUTE
   side only). Result: exactly ONE failure --
   `test_named_variable_then_pass_load_of_the_parsed_module_is_flagged_by_name`.
   Every inline-shaped method (`test_inline_import_module_call_is_flagged`,
   `test_plain_import_statement_is_flagged`,
   `test_dotted_execute_side_normalizes_against_path_form_parse_side`,
   `test_two_level_parser_helper_fixed_point_is_flagged`) kept passing.
   Reverted; suite returned to 65/65 `OK`.
3. **Rust/go negative half:** temporarily inserted `"import-linter"` into
   the rust row's text in `canonical_tools.py`. Result: exactly ONE
   failure -- `test_rust_only_repo_states_known_gap_and_names_no_tool`.
   Reverted; suite returned to 65/65 `OK`.

## `make test` (all four pyramid tiers)

`uv` is available (`uv 0.11.28`). `make test` exits 0: 2019 unit tests
(`OK (skipped=19)`), 6 framework-profile tests, 131 wizard/config-doctor
tests, 13 e2e/system-memory tests, 16 shell install tests, and 22
`tests.test_arch` tests (the file this plan's central decision is
grounded against, unedited) -- all `OK`.

## `make validate`

Reported honestly, not a bare pass/fail. `make validate` exits non-zero
because `ruff` (its first prerequisite) exits non-zero -- but EVERY
remaining ruff finding is pre-existing and OUT OF SCOPE for this plan:

- `ruff`: 25 pre-existing errors, all in `tests/test_ai_kit_spec_superpowers.py`,
  `tools/status-line.py`, `tools/wizard_app.py` (none in this plan's
  `<files>`). Down from 31 before this plan's own 6 findings in
  `ast_only.py` were fixed (see Deviations #2).
- `pylint`: fails with 6 pre-existing findings, all in `tools/status-line.py`.
- `pyright`: fails with 1 pre-existing error, in
  `skills/ai-kit-project-rules-precommit/ai_kit_project_rules_precommit/pair_checks.py`.
- `vulture`, `shellcheck`, `py-compile`, `unittest`, `unittest-wizard`:
  all pass individually (run directly since `make validate`'s
  composite target halts at the first failed prerequisite).

No finding in `ast_only.py`, `canonical_tools.py`, `arch_checker.py`, or
`tests/test_ai_kit_project_rules_arch.py` -- confirmed by grepping the
full `ruff`/`pylint`/`pyright` output for these four paths (zero matches).

## Known Stubs

None.

## Threat Flags

None beyond what this plan's own `<threat_model>` already registers
(T-12-08 through T-12-15a, all mitigated per the threat register).

## Self-Check: PASSED

- `skills/ai-kit-project-rules-arch/ai_kit_project_rules_arch/ast_only.py` -- FOUND
- `skills/ai-kit-project-rules-arch/ai_kit_project_rules_arch/canonical_tools.py` -- FOUND
- `skills/ai-kit-project-rules-arch/ai_kit_project_rules_arch/arch_checker.py` -- FOUND (modified)
- `tests/test_ai_kit_project_rules_arch.py` -- FOUND (modified)
- Commit `c8581e9` (Task 1) -- FOUND in `git log`
- Commit `43cde85` (Task 2) -- FOUND in `git log`
- Commit `06b42f2` (Task 3) -- FOUND in `git log`
