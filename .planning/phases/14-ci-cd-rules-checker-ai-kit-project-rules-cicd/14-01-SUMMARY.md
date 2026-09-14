---
phase: 14-ci-cd-rules-checker-ai-kit-project-rules-cicd
plan: 01
subsystem: infra
tags: [python, stdlib-only, ci-cd, gitlab-ci, static-analysis, ai-kit-rules-checker]

requires:
  - phase: 09-agents-md-checker-prune-ai-kit-project-rules-agents
    provides: shared ai_kit_rules_common package convergence (criticality, makefile_parse)
  - phase: 11-pre-commit-rules-checker-ai-kit-project-rules-precommit
    provides: tool_catalog (resolve_tool_category, OUT_OF_TAXONOMY_GROUPS), parity_checker precedent
  - phase: 13-docker-rules-checker-ai-kit-project-rules-docker
    provides: compose_parse.py's indentation-aware text-scan pattern, yaml_text.py's first three primitives, sibling skill package shape
provides:
  - ai-kit-project-rules-cicd skill (check/remediate CLI) with a working GitLab CI reader, Makefile reuse-source inventory, and command-key matcher
  - skills/_shared/ai_kit_rules_common/command_text.py (new shared module: shell-command-line grammar)
  - skills/_shared/ai_kit_rules_common/yaml_text.py grown to six generic indentation-aware block primitives
  - STRUCTURAL_KINDS grown to five kinds ("cicd" appended)
affects: [14-02-github-actions-reader, 14-03-other-reuse-surfaces, 14-04-skill-md-and-installer, 15-rules-orchestrator]

actuals:
  tokens: 29754
  tasks: 2
  commits: 3
  plan_head_before: da78d3b47c4595be1ce099be09c3dfe3301b7762

tech-stack:
  added: []
  patterns:
    - "Indentation-aware stdlib-only YAML text reader (no PyYAML dependency), generalizing compose_parse.py's private helpers into shared yaml_text.py primitives"
    - "Shell-command-line grammar (segment splitting, runner-prefix stripping, token normalization) factored into a policy-free shared module, with reuse-table policy kept in the consuming skill"
    - "Deliberately un-repointed duplication + drift guard (yaml_text vs compose_parse, command_text vs parity_checker) rather than importing a closed sibling file"

key-files:
  created:
    - skills/ai-kit-project-rules-cicd/ai-kit-project-rules-cicd.py
    - skills/ai-kit-project-rules-cicd/ai_kit_project_rules_cicd/__init__.py
    - skills/ai-kit-project-rules-cicd/ai_kit_project_rules_cicd/cli.py
    - skills/ai-kit-project-rules-cicd/ai_kit_project_rules_cicd/ci_parse.py
    - skills/ai-kit-project-rules-cicd/ai_kit_project_rules_cicd/reuse_sources.py
    - skills/ai-kit-project-rules-cicd/ai_kit_project_rules_cicd/cicd_checker.py
    - skills/ai-kit-project-rules-cicd/ai_kit_project_rules_cicd/remediation.py
    - skills/_shared/ai_kit_rules_common/command_text.py
    - tests/test_ai_kit_project_rules_cicd.py
  modified:
    - skills/_shared/ai_kit_rules_common/remediation.py
    - skills/_shared/ai_kit_rules_common/yaml_text.py
    - tests/test_ai_kit_rules_common.py
    - Makefile
    - pyproject.toml
    - .pre-commit-config.yaml

key-decisions:
  - "D-C1 through D-C13 and D-C28 implemented exactly as the plan specified (applicability gate, catalog-grounded identity/match rules, complete reuse-invocation table, determinism, never-follow-include disclosure) -- no deviation from the planner's locked decisions."
  - "Rule 1 auto-fix: the GitLab reader's block-end lookup needed a same-indent-aware boundary helper for top-level sequences, and the sequence scanner needed to stop at a sibling key instead of skipping over it -- GitLab commonly indents list items at the SAME level as their key (ai-kit's own .gitlab-ci.yml uses this for stages:), which the compose-parse-derived helpers (written for compose's deeper-indent convention) mis-read as an empty block or bled across sibling boundaries."
  - "Rule 1 auto-fix: command_text.strip_leading_noise gained an optional stop_check callback so the skill can halt prefix-stripping the moment a reuse-invocation shape (pre-commit run <id>) appears -- the pinned, byte-identical RUNNER_PREFIX_RE is generic enough to also match 'pre-commit run', which would otherwise be silently consumed as noise before the reuse table ever saw it. The callback itself carries no policy inside command_text.py; the skill supplies it."
  - "Rule 1 auto-fix: the bare 'pnpm <script>'/'yarn <script>' reuse-table rows exclude 'exec'/'dlx' as the immediate next token, closing a second collision where 'pnpm exec eslint .' would otherwise match the bare-script row before its dedicated two-token runner-prefix strip ran."

patterns-established:
  - "A skill package with no SKILL.md is intentionally invisible to the installer -- confirmed live via the installer's skill-entry validator requiring SKILL.md."
  - "Task-split commit discipline: when test-writing (Task 2) surfaces real implementation bugs in Task 1's already-committed code, the fix lands as its own separate commit before the test-only commit, keeping each task's own diff matching its stated <files> list."

requirements-completed: [REQ-rules-cicd]

coverage:
  - id: D1
    description: "A GitLab CI job running a tool directly when an equivalent single-tool Makefile target already exists is flagged, naming both sides of the duplication (ROADMAP SC1 GitLab half)"
    requirement: "REQ-rules-cicd"
    verification:
      - kind: unit
        ref: "tests/test_ai_kit_project_rules_cicd.py#TestTracerDirectInvocationFlagged.test_direct_invocation_produces_one_finding_naming_both_sides"
        status: pass
    human_judgment: false
  - id: D2
    description: "A CI file whose every command is a reuse invocation (make/pre-commit run/npm/pnpm/yarn/gradle forms) produces zero findings (ROADMAP SC2), with the reuse-invocation table complete across all four families"
    requirement: "REQ-rules-cicd"
    verification:
      - kind: unit
        ref: "tests/test_ai_kit_project_rules_cicd.py#TestSegmentationAndReuseTable.test_classify_reuse_invocation_matches_each_table_row_directly"
        status: pass
    human_judgment: false
  - id: D3
    description: "The Makefile reuse surface is covered by paired triggering/non-triggering fixtures, including D-C3's identity clauses and D-C4's tool-shaped gate with its Route 3 qualifier"
    requirement: "REQ-rules-cicd"
    verification:
      - kind: unit
        ref: "tests/test_ai_kit_project_rules_cicd.py#TestIdentityExtractionClauses"
        status: pass
      - kind: unit
        ref: "tests/test_ai_kit_project_rules_cicd.py#TestIdentityGateNegatives"
        status: pass
    human_judgment: false
  - id: D4
    description: "Every parsing primitive this skill needs that another family skill already owns is imported from skills/_shared/ai_kit_rules_common/ rather than re-implemented (ROADMAP SC4)"
    requirement: "REQ-rules-cicd"
    verification:
      - kind: unit
        ref: "SHARED-REUSE-OK acceptance script (Task 1 <acceptance_criteria>)"
        status: pass
    human_judgment: false
  - id: D5
    description: "GitLab include: (all forms, both local and remote) is never followed, disclosed in the reader's docstring, and pinned by a fixture asserting both zero findings and that the included file was never opened (D-C28)"
    requirement: "REQ-rules-cicd"
    verification:
      - kind: unit
        ref: "tests/test_ai_kit_project_rules_cicd.py#TestReaderStatedLimits.test_include_local_is_a_disclosed_limit_and_produces_no_findings"
        status: pass
    human_judgment: false

duration: 105min
completed: 2026-09-14
status: complete
---

# Phase 14 Plan 1: CI/CD Rules Checker Tracer Summary

**GitLab CI reuse-duplication checker (ai-kit-project-rules-cicd) end-to-end: a stdlib-only indentation-aware `.gitlab-ci.yml` reader, a Makefile reuse-source inventory with a catalog-grounded identity gate and match rule, and a check/remediate CLI wired into every quality gate its four siblings share.**

## Performance

- **Duration:** ~105 min
- **Started:** 2026-09-14 (worktree fresh-start, no prior partial state)
- **Completed:** 2026-09-14T23:08:19Z
- **Tasks:** 2 (Task 1 tracer + Task 2 suite fill-out), plus one Rule-1 fix commit discovered while executing Task 2
- **Files modified:** 15 (9 created, 6 modified)

## Accomplishments

- `ai-kit-project-rules-cicd` stands up end-to-end: `check(repo_root)` returns `{"cicd": [...]}`, `remediate(repo_root)` returns the family's two-key payload, and a real GitLab CI job running `ruff check .` beside a matching `ruff` Makefile target is flagged with a recommendation naming both `ruff check .` and `make ruff`.
- `skills/_shared/ai_kit_rules_common/yaml_text.py` grows from 3 to 9 public functions (six new generic indentation-aware block primitives), pinned against `compose_parse.py`'s six private counterparts by a non-vacuous drift guard.
- New shared module `skills/_shared/ai_kit_rules_common/command_text.py`: shell-command-line grammar (segment splitting honoring quotes/pipes, D-C6's bounded 3-round prefix stripping, token normalization). Its `RUNNER_PREFIX_RE` constant is pinned byte-identical to `parity_checker._RUNNER_PREFIX_RE` by a non-vacuous, narrowly-scoped drift guard.
- `STRUCTURAL_KINDS` grows to `("makefile", "precommit", "arch", "docker", "cicd")`, additively -- proven byte-identical for pre-existing 4-kind reports and correctly cross-kind-ordered for all 5.
- 92 test methods in `tests/test_ai_kit_project_rules_cicd.py` (40 matching the negative/non-triggering naming pattern) covering the applicability gate, every reader shape and stated limit, D-C3's identity clauses, D-C4's gate with Route 3's qualifier, D-C5's `ruff` triad match rule, D-C6's segmentation/reuse table, D-C13's determinism, degradation, D-C7's identifier discipline, the CLI surface, and gate registration.
- Six required non-vacuity mutations (match rule, whole identity gate, Route 3 qualifier alone, D-C3 clause b2, D-C28's include-following, applicability gate negatives) each manually applied, observed failing on exactly the predicted method(s), and confirmed reverted -- see "Non-vacuity mutations" below.
- The skill is registered in every quality gate its four siblings are in (`Makefile` test-unit + lint, `.pre-commit-config.yaml` ruff/py-compile/unittest, `pyproject.toml` pyright/vulture) while remaining uninstallable (`test ! -e skills/ai-kit-project-rules-cicd/SKILL.md` still succeeds) until plan 14-04.

## Task Commits

1. **Task 1: Wire the new skill end-to-end (tracer)** - `ecb2801` (feat)
2. **[Rule 1 auto-fix, discovered writing Task 2] GitLab reader same-indent sequences + reuse-table ordering** - `6d9426a` (fix)
3. **Task 2: Fill out the suite, grow the shared suite** - `820798e` (test)

_No separate plan-metadata commit was made in this session; this SUMMARY and STATE.md updates are committed by the standard final-commit step._

## Files Created/Modified

- `skills/ai-kit-project-rules-cicd/ai-kit-project-rules-cicd.py` - 7-line entrypoint, matches sibling shape exactly
- `skills/ai-kit-project-rules-cicd/ai_kit_project_rules_cicd/__init__.py` - shared-path append with named ImportError
- `skills/ai-kit-project-rules-cicd/ai_kit_project_rules_cicd/ci_parse.py` - GitLab CI reader: applicability gate, discovery, command-site iteration
- `skills/ai-kit-project-rules-cicd/ai_kit_project_rules_cicd/reuse_sources.py` - D-C3 identity extraction, D-C4 gate, D-C5 match rule, D-C6 reuse table, inventory builder
- `skills/ai-kit-project-rules-cicd/ai_kit_project_rules_cicd/cicd_checker.py` - aggregator: gate-first, one commit-site/segment loop, D-C12 finding shape
- `skills/ai-kit-project-rules-cicd/ai_kit_project_rules_cicd/cli.py` - argparse-free check/remediate dispatch
- `skills/ai-kit-project-rules-cicd/ai_kit_project_rules_cicd/remediation.py` - thin re-export of the shared builder
- `skills/_shared/ai_kit_rules_common/command_text.py` - new shared shell-command-line grammar module
- `skills/_shared/ai_kit_rules_common/yaml_text.py` - +6 public functions, additive
- `skills/_shared/ai_kit_rules_common/remediation.py` - `STRUCTURAL_KINDS` +1 name, additive
- `tests/test_ai_kit_project_rules_cicd.py` - the new skill's full suite (92 test methods)
- `tests/test_ai_kit_rules_common.py` - +5-kind coverage, +yaml_text primitive tests, +command_text tests, +2 drift guards
- `Makefile`, `.pre-commit-config.yaml`, `pyproject.toml` - registration surfaces extended

## Decisions Made

### The five catalog facts the `<precondition>` re-verified

Verified live before implementing (all held, matching the plan's citations):
- `resolve_tool_category("ruff") == "linting"`
- `resolve_tool_category("ruff check") == "linting"`
- `resolve_tool_category("ruff format") == "formatting"`
- `resolve_tool_category("pytest") is None` (lives in `OUT_OF_TAXONOMY_GROUPS`)
- `resolve_tool_category("tsc") is None`, but `resolve_tool_category("tsc --noEmit") == "type-checking"`

D-C2, D-C4, and D-C5 all rest on these; plans 14-02/14-03 inherit the same matcher unchanged.

### D-C1's applicability gate exactly as implemented

Both clauses evaluated first and short-circuiting, root-scoped only: (i) `os.path.isfile` for `.gitlab-ci.yml`/`.gitlab-ci.yaml`; (ii) `os.path.isdir` on `.github/workflows/` plus ONE non-recursive `os.listdir` checking for any `.yml`/`.yaml` entry. Clause (ii) is implemented even though this plan reads no workflow file, so plan 14-02 does not change the gate's answer. Negative edges pinned: an empty `.github/workflows/` directory, a `.github/workflows/README.md`-only directory, and a nested `sub/.gitlab-ci.yml` all correctly do NOT satisfy the gate.

### D-C3's identity-extraction clauses as they landed

Implemented in `reuse_sources.makefile_target_identity(name, recipe_text, prerequisites) -> (identity, derived_from_command_body)`, in the plan's exact order: cap (>2 real lines, or 0 real lines + prerequisites, -> no identity) evaluated first; clause (a) delegate (`pre-commit run <id>`, searched across ALL real lines, checked before the 1-line/2-line split); clause (b) single real line -> `compute_command_key`; clause (b2) two real lines -> identity only if both lines' keys match, else no identity; clause (c) zero real lines + no prerequisites -> the target's own bare name, `derived_from_command_body=False`. No clause's behavior differed from the plan text.

### D-C4's tool-shaped gate as implemented

`reuse_sources.is_tool_shaped_identity(identity: str, source_name: str, derived_from_command_body: bool) -> bool`. The third parameter is passed EXPLICITLY by `makefile_target_identity`'s two-value return (never inferred from `identity == source_name`), exactly as the plan requires. Route 1 (`resolve_tool_category`), Route 2 (out-of-taxonomy, casefolded exact match against a flattened frozenset built once from `OUT_OF_TAXONOMY_GROUPS`), Route 3 (`normalize_token(identity) == normalize_token(source_name)` AND `derived_from_command_body`).

Negative fixtures and which route rejected them:
- `clean: rm -rf dist` -> identity `"rm"`, all three routes fail (no catalog hit, not out-of-taxonomy, `"rm" != "clean"`)
- `greet: echo hello` -> identity `"echo"`, all three routes fail
- `enter: cd sub`, `tag: git tag v1`, `run-script: bash script.sh` -> same pattern, all rejected
- Route 3 pair: `myformatter: myformatter --fix` (one real line) -> identity `"myformatter"`, `derived=True`, `normalize("myformatter")==normalize("myformatter")` -> ADMITTED. `myformatter:` (empty recipe, no prerequisites) -> clause (c), `derived=False` -> Route 3 unavailable, Routes 1/2 don't know it -> REJECTED.
- Positive: `test: pytest` -> identity `"pytest"`, admitted via Route 2 (`OUT_OF_TAXONOMY_GROUPS`'s test-runner markers) -- the case a catalog-gated design would silently miss (D-C2's rationale).

Both mutations required by the plan were applied and observed:
- Whole-gate mutation (`is_tool_shaped_identity` always returns `True`): exactly `rm`/`echo`/`cd`/`git`/`bash` and the Route-3-empty-recipe negative failed (6 of 8 methods in `TestIdentityGateNegatives`); `pytest` and the Route-3-admits-with-body positive stayed green. Observed, then reverted (the mutation lived only inside an isolated `python3 -c` subprocess; the source file was never edited).
- Route-3-qualifier-only mutation (drop `derived_from_command_body`, Route 3 becomes plain name equality): exactly 2 methods failed across two classes -- `test_route3_rejects_the_same_name_with_no_command_body` and `test_clause_c_non_catalog_bare_name_yields_no_findings` (the `my-house-style` clause-(c) fixture, also a name-only identity) -- and nothing else. This is the precise pair the plan's acceptance criterion names.

### D-C3's clause (b2) as it landed

Two-real-line targets: `ruff:` with lines `ruff check .` / `ruff format .` -> keys `"ruff check"` vs `"ruff format"` differ -> `(None, False)`, no identity, zero findings against a matching CI `ruff check .` line. Paired: `ruff:` with lines `ruff check .` / `ruff check --fix .` -> `compute_command_key` only inspects the first TWO tokens of each line, so both lines compute `"ruff check"` -> SAME key -> `("ruff check", True)`, admitted, and `make ruff` is recommended for a CI `ruff check .` line.

Non-vacuity: restoring the old "identity = target's own name" fallback for any two-line recipe made exactly `test_clause_b2_different_key_pair_yields_no_findings` (and its Task-1-tracer duplicate `test_different_key_two_line_target_has_no_identity`) fail; the same-key pair method stayed green. Observed, reverted.

### D-C28 as it landed

The reader's module docstring states (verbatim, so plan 14-04 can quote it unparaphrased):

> `include:` is skipped as a reserved non-job key and NONE of its forms is ever resolved or opened (D-C28): a pipeline composed from included files can run a tool this reader never sees, so a zero-finding result on such a repo is not evidence its CI is clean.

Mechanism proving the included file is never opened: `ci_parse.read_ci_text` is monkeypatched in the test to record every path it is asked to read; the assertion checks the included path never appears in that record, not merely that the finding count is zero. Both the `include: local:` fixture and a second fixture over ai-kit's own real shape (`include: - template: Security/Secret-Detection.gitlab-ci.yml`) are pinned. All forms are skipped uniformly -- `local:`, `template:`, `project:`, `remote:`, `component:` are all reserved-key children never resolved.

Non-vacuity: monkeypatching `discover_ci_files` to also follow `local:` references made exactly `test_include_local_is_a_disclosed_limit_and_produces_no_findings` and `test_include_local_is_never_followed` fail; the `template:` method and every other `TestReaderStatedLimits` method stayed green. Observed, reverted.

### D-C5's match rule measured

The `ruff` triad as the implementation really produces it:
- bare `ruff` identity (Route 1 via `AMBIGUOUS_TOOL_DEFAULTS`) MATCHES CI `ruff check .` -> flagged
- `ruff` identity does NOT match CI `ruff format .` -> zero findings (first tokens equal, categories `linting` vs `formatting` differ)
- `ruff check` identity (exact) MATCHES CI `ruff check --fix .` -> flagged (exact-key equality on the two-token form; `--fix` is the third token, outside `compute_command_key`'s two-token window)
- an unknown-key CI line with no matching reuse source -> zero findings

Mutation: temporarily changing `keys_match` to first-token-equality-only made exactly `test_ruff_format_matches_neither_ruff_nor_ruff_check` fail; the other 5 methods in `TestMatchRuleRuffTriad` stayed green. Observed, reverted.

### Shared-package growth, proven behavior-preserving

- `STRUCTURAL_KINDS`: one name appended (`"cicd"`), tuple order `("makefile", "precommit", "arch", "docker", "cicd")` unchanged for the first four. `TestRemediationCicdKind` in the shared suite pins a 4-kind report byte-identical to pre-change output and a 5-kind report ordering as one criticality-sorted list.
- `yaml_text.py`: six names appended -- `is_document_separator`, `is_effective_structural`, `strip_inline_comment`, `match_key_header`, `find_block_end`, `own_level_lines`. The three pre-existing functions (`strip_yaml_quotes`, `line_indent`, `is_structural_line`) are byte-identical (unedited). `TestYamlTextComposeParseDriftGuard` loads `compose_parse.py` by file path (`importlib.util.spec_from_file_location`) and pins each new primitive against its private counterpart over a shared input table, with its own non-vacuity method.
- `command_text.py` public surface: `RUNNER_PREFIX_RE`, `split_top_level_segments`, `truncate_at_unquoted_pipe`, `has_heredoc`, `strip_leading_noise` (now with an optional `stop_check` parameter added during the Task-2 bug fix), `normalize_token`.
- All five sibling suites (`test_ai_kit_project_rules_docker/arch/precommit/makefile/agents`) plus the shared suite pass unchanged: 686 tests combined, `OK (skipped=1)`.

### Both drift guards as they landed

- **D-C8 (yaml_text vs compose_parse):** `TestYamlTextComposeParseDriftGuard` compares all six primitives over paired input tables, skips with a stated reason if `compose_parse.py` is absent, and its `test_drift_guard_is_non_vacuous` method monkeypatches `is_document_separator`'s answer and confirms the comparison catches the divergence.
- **D-C9 (command_text.RUNNER_PREFIX_RE vs parity_checker._RUNNER_PREFIX_RE):** `TestCommandTextRunnerPrefixDriftGuard` reads the sibling literal via `ast` (never importing `parity_checker`), asserts equality on `RUNNER_PREFIX_RE.pattern` alone, mutates that ONE constant and observes the guard fail (`test_drift_guard_is_non_vacuous_on_the_pinned_constant`), then mutates an UNPINNED constant (`_ONE_TOKEN_RUNNER_RE`) and confirms the guard does NOT fail (`test_mutating_an_unpinned_constant_does_not_fail_the_guard`) -- proving the guard is scoped to the one named literal, not a whole-module equivalence check.

### D-C10 as it landed

The `try/except (OSError, UnicodeDecodeError)` wrap sits in `reuse_sources.build_reuse_inventory`, around both the `parse_makefile_targets_ordered` call (returns `[]` on failure) and the per-target `parse_makefile_recipe`/`parse_makefile_prerequisites` calls (skip that target on failure). The CI-file reader's own degradation lives in `ci_parse.read_ci_text`, returning `""` on the same two exception types. `test_shared_parser_really_raises_on_the_binary_fixture` calls `parse_makefile_targets` directly on the same binary fixture and asserts it RAISES `(OSError, UnicodeDecodeError)` -- proving the wrap is non-vacuous, since an empty result can only come from a wrap this skill owns.

### The GitLab reader's stated limits, quoted verbatim from its module docstring

> it is a text reader, not a YAML implementation; tab indentation may mis-attribute a block rather than raise; anchors, aliases, merge keys and GitLab's `!reference` are not resolved and a site using them may be read incompletely; a line containing a heredoc is skipped rather than mis-parsed; and `include:` is skipped as a reserved non-job key and NONE of its forms is ever resolved or opened, `local:` included.

### `NO-CACHE-SURFACE-OK`, rewritten AST-based form

Reserved-key tuple length: **7** (`stages`, `variables`, `include`, `workflow`, `image`, `services`, `cache`), written as plain string literals with no computed or concatenated spelling anywhere in the skill. Both non-vacuity probes confirmed and reverted: a throwaway `_cache_dir = None` identifier trips the identifier-scan assertion; a second string literal containing `"cache"` outside the tuple trips the stray-literal assertion. Grep confirms `"cache"` appears exactly once in `ci_parse.py` (the tuple element) across the whole package.

### Scope discipline confirmed

This plan added NO GitHub Actions reading, NO pre-commit/`package.json`/Gradle reuse SOURCE (only the reuse-invocation-table recognition for all four, per D-C6), NO cache surface, and NO third subcommand -- `check`/`remediate` only, matching D-C11.

## Deviations from Plan

### Auto-fixed Issues (all Rule 1 -- bugs, found while writing Task 2's test coverage)

**1. [Rule 1 - Bug] GitLab reader mis-read same-indent-as-key sequences**
- **Found during:** Task 2 (writing `TestReaderShapes`)
- **Issue:** `find_block_end`/`own_level_lines` (generalized from `compose_parse.py`, which assumes Docker Compose's deeper-indent convention) mis-computed a block boundary when a top-level key's list items shared the key's own indent (`before_script:\n- a\n- b\n`) or when multiple sibling list-valued keys within one job shared indent with their own items (`after_script:`/`script:`/`before_script:` all at the job's child indent, ai-kit's own `.gitlab-ci.yml` uses exactly this style for `stages:`). Result: an empty block for the top-level case, and cross-sibling item bleed for the nested case.
- **Fix:** Added `_top_level_block_end` (peeks at the next line; if it's a same-indent dash item, scans forward stopping at the first non-dash indent-0 line rather than the first indent<=0 line) and changed `_sequence_command_lines` to `break` (not skip) on the first non-dash own-level line.
- **Files modified:** `skills/ai-kit-project-rules-cicd/ai_kit_project_rules_cicd/ci_parse.py`
- **Verification:** `TestReaderShapes` (6 paired methods), full suite green
- **Committed in:** `6d9426a`

**2. [Rule 1 - Bug] Generic runner-prefix stripping swallowed `pre-commit run <id>`**
- **Found during:** Task 2 (writing `TestSegmentationAndReuseTable`)
- **Issue:** The pinned, byte-identical `RUNNER_PREFIX_RE` (`<name> run <rest>`) also matches `pre-commit run <id>` (any identifier + `run` satisfies it), so `strip_leading_noise` consumed `"pre-commit run "` as if it were a generic runner wrapper before the reuse-invocation table ever saw the intact shape -- turning a legitimate reuse invocation into a false-positive direct-invocation finding.
- **Fix:** `strip_leading_noise` gained an optional `stop_check` callback (checked before stripping and after every round); `cicd_checker.py` passes `lambda s: reuse_sources.classify_reuse_invocation(s) is not None`, halting stripping the instant a reuse shape appears. `command_text.py` itself gained no policy knowledge -- the callback is opaque to it, per D-C9.
- **Files modified:** `skills/_shared/ai_kit_rules_common/command_text.py`, `skills/ai-kit-project-rules-cicd/ai_kit_project_rules_cicd/cicd_checker.py`
- **Verification:** `TestSegmentationAndReuseTable.test_pre_commit_run_row_is_reuse_and_never_a_finding`
- **Committed in:** `6d9426a`

**3. [Rule 1 - Bug] Bare `pnpm`/`yarn` reuse-table rows collided with their own `exec`/`dlx` runner forms**
- **Found during:** Task 2, same investigation as #2 (checking `classify_reuse_invocation` before any stripping, needed for fix #2, exposed this)
- **Issue:** `^pnpm\s+\S+` (bare-script row) also matched `pnpm exec eslint .`, misreading it as if `exec` were a package.json script name -- exactly the false classification D-C6's ordering proof exists to prevent.
- **Fix:** Added negative lookaheads excluding `exec`/`dlx` as the immediate next token on the bare `pnpm`/`yarn` table rows.
- **Files modified:** `skills/ai-kit-project-rules-cicd/ai_kit_project_rules_cicd/reuse_sources.py`
- **Verification:** `TestSegmentationAndReuseTable.test_pnpm_exec_direct_invocation_is_flagged_not_reuse`
- **Committed in:** `6d9426a`

---

**Total deviations:** 3 auto-fixed (all Rule 1 -- bugs)
**Impact on plan:** All three were genuine correctness bugs in Task 1's tracer, surfaced by Task 2's deliberately adversarial fixture coverage (same-indent YAML, `pre-commit run` reuse, `pnpm exec` ordering) -- exactly the kind of defect the plan's paired-fixture requirement exists to catch. No scope creep: no new capability was added, and the fixes are committed separately (`6d9426a`) from the test-only Task 2 commit (`820798e`) so each commit's diff matches what its own task's `<files>`/acceptance criteria expect.

## Issues Encountered

None beyond the deviations above. The worktree required a fast-forward merge to `main` (`b30c0b2..da78d3b`) before starting, since it was created before Phase 14's planning docs landed -- this is worktree setup, not plan execution, and is noted for the orchestrator's awareness rather than as a plan deviation.

One pre-existing environment gap, unrelated to this plan: `make test-unit`'s aggregate run fails on `tests.test_markdown_to_pdf.TestRenderRealMmdc.test_real_render_produces_image` (missing `@mermaid-js/mermaid-cli` module in this sandbox's pnpm global store). This is outside every file this plan touched; the scoped combined suite this plan is responsible for (`tests.test_ai_kit_project_rules_cicd` + the five siblings + the shared suite, 686 tests) passes cleanly. `make validate` fails ONLY on the four pre-existing, STATE.md-documented out-of-scope files (`tools/status-line.py`, `tools/wizard_app.py`, `tests/test_ai_kit_spec.py`, `tests/test_ai_kit_spec_superpowers.py`) -- confirmed by listing every `-->` path in ruff's failure output; zero findings in any path this plan touched. `pyright` (whole configured include list) reports one pre-existing error in `ai-kit-project-rules-precommit/pair_checks.py`, a file this plan never opened. `vulture` over the whole configured path list reports nothing.

## User Setup Required

None - no external service configuration required. This skill makes no network call, adds no dependency, and writes no file anywhere.

## Next Phase Readiness

- Plan 14-02 (GitHub Actions reader) can extend `ci_parse.py`'s discovery list and `cicd_checker.py`'s aggregator by appending, per the plan's stated extension seam -- no rework needed on this plan's output.
- Plan 14-03 (pre-commit/`package.json`/Gradle reuse SOURCES) extends `reuse_sources.build_reuse_inventory` by appending a surface; the reuse-invocation TABLE is already complete for all four surfaces, so no false positives are inherited.
- Plan 14-04 can write `SKILL.md` immediately; the skill remains fully uninstallable until then (`test ! -e skills/ai-kit-project-rules-cicd/SKILL.md` still succeeds after this plan).
- No blockers.

---
*Phase: 14-ci-cd-rules-checker-ai-kit-project-rules-cicd*
*Completed: 2026-09-14*

## Self-Check: PASSED

All 10 claimed created/modified files verified present on disk (entrypoint, `__init__.py`, `cli.py`, `ci_parse.py`, `reuse_sources.py`, `cicd_checker.py`, `remediation.py`, `command_text.py`, `tests/test_ai_kit_project_rules_cicd.py`, this SUMMARY.md). All 3 claimed commit hashes (`ecb2801`, `6d9426a`, `820798e`) verified present in `git log`. HEAD confirmed on the agent-namespace branch `worktree-agent-a98b8a89c0d1b51a3` at `820798e3d7d0bc7f0e9cba03f7777eb59c29ed92` — no drift onto a protected branch.
