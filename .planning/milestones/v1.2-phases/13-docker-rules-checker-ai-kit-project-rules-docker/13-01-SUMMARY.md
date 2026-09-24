---
phase: 13-docker-rules-checker-ai-kit-project-rules-docker
plan: 01
subsystem: testing
tags: [python, stdlib, makefile-parsing, remediation, docker]

requires:
  - phase: 12-architecture-rules-checker-ai-kit-project-rules-arch
    provides: skills/_shared/ai_kit_rules_common (makefile_parse, remediation, criticality) and the sys.path-append package-init pattern this skill copies
provides:
  - "ai-kit-project-rules-docker skill: check_docker_rules(repo_root) aggregator answering SC1 (eight-target docker-* Makefile family) and SC5 (docker/local/README.md runbook), gated on D-D4's root-scoped Docker applicability check"
  - "STRUCTURAL_KINDS grown to 4 entries (+\"docker\") in the shared remediation.py, additive only"
  - "extensible aggregator shape (gate-then-extend) plans 13-02/13-03 append to"
affects: [13-02-docker-compose-parsing, 13-03-docker-hot-reload-and-runbook-content, 13-04-docker-skill-md-and-registration, 15-rules-orchestrator]

actuals:
  tokens: 14789
  tasks: 2
  commits: 3

tech-stack:
  added: []
  patterns:
    - "D-D4 applicability gate evaluated FIRST, short-circuiting to an empty finding list -- the pattern plans 13-02/13-03 extend by appending calls inside the applicable branch"
    - "D-D23: the unreadable-Makefile wrap lives in the CONSUMING skill (docker_checker.py), not the shared parser -- try/except (OSError, UnicodeDecodeError) around every parse_makefile_targets_ordered call only"

key-files:
  created:
    - skills/ai-kit-project-rules-docker/ai-kit-project-rules-docker.py
    - skills/ai-kit-project-rules-docker/ai_kit_project_rules_docker/__init__.py
    - skills/ai-kit-project-rules-docker/ai_kit_project_rules_docker/cli.py
    - skills/ai-kit-project-rules-docker/ai_kit_project_rules_docker/docker_checker.py
    - skills/ai-kit-project-rules-docker/ai_kit_project_rules_docker/remediation.py
    - tests/test_ai_kit_project_rules_docker.py
  modified:
    - skills/_shared/ai_kit_rules_common/remediation.py
    - tests/test_ai_kit_rules_common.py
    - Makefile
    - .pre-commit-config.yaml
    - pyproject.toml

key-decisions:
  - "D-D4's applicability gate reads root-level evidence only via os.path.isfile/isdir against explicitly-joined paths plus one non-recursive os.listdir(repo_root) (needed only to catch the variable-suffix Dockerfile.* filename shape); clause (iv) over Makefile targets is a PREFIX rule over the D-D1-normalized name."
  - "D-D1's eight-target family is matched by exact equality after normalization (casefold + `_`->`-`), never a shape/regex rule -- deliberately different from the Makefile sibling's _DOCKER_UP_SHAPE_RE."
  - "D-D23's unreadable-Makefile wrap (try/except (OSError, UnicodeDecodeError)) lives entirely inside docker_checker.py's _normalized_targets_present helper, used by both the gate and the target-family check, so the wrap sits at one call site rather than duplicated."

patterns-established:
  - "Family-tuple-driven test coverage: iterate the checker's own DOCKER_TARGET_FAMILY tuple in test methods rather than hand-writing eight near-identical methods, so tests cannot fall out of step with the checker's literal list."

requirements-completed: [REQ-rules-docker]

coverage:
  - id: D1
    description: "SC1 -- a fixture Makefile missing one or more of the eight docker-* targets is flagged by name for each missing target; a fixture with the full family produces none"
    requirement: "REQ-rules-docker"
    verification:
      - kind: unit
        ref: "tests/test_ai_kit_project_rules_docker.py#TestTargetFamilyDrivenFromTuple.test_missing_one_target_at_a_time_produces_one_finding_naming_it"
        status: pass
      - kind: unit
        ref: "tests/test_ai_kit_project_rules_docker.py#TestTargetFamilyDrivenFromTuple.test_all_eight_targets_present_yields_no_findings"
        status: pass
    human_judgment: false
  - id: D2
    description: "SC5 -- absence of docker/local/README.md is flagged as a missing runbook requirement, and its presence is not, with a recommendation naming the required content"
    requirement: "REQ-rules-docker"
    verification:
      - kind: unit
        ref: "tests/test_ai_kit_project_rules_docker.py#TestRunbookPaired.test_runbook_missing_produces_one_finding"
        status: pass
      - kind: unit
        ref: "tests/test_ai_kit_project_rules_docker.py#TestRunbookPaired.test_runbook_present_produces_no_finding"
        status: pass
      - kind: unit
        ref: "tests/test_ai_kit_project_rules_docker.py#TestRunbookPaired.test_runbook_recommendation_names_required_content"
        status: pass
    human_judgment: false
  - id: D3
    description: "D-D4 applicability gate -- a repo with no root-level Docker evidence, including ai-kit's own repository root and a repo whose only image is a nested CI Dockerfile beside a docker-suffixed Makefile target, produces zero findings"
    requirement: "REQ-rules-docker"
    verification:
      - kind: unit
        ref: "tests/test_ai_kit_project_rules_docker.py#TestTracerAiKitOwnRepo.test_ai_kit_own_repo_yields_no_findings"
        status: pass
      - kind: unit
        ref: "tests/test_ai_kit_project_rules_docker.py#TestApplicabilityGateEvidenceClauses (9 methods, 4 evidence clauses + 4 negatives + suffix edge)"
        status: pass
    human_judgment: false
  - id: D4
    description: "Shared remediation.py STRUCTURAL_KINDS grown additively; existing three-kind payloads stay byte-identical and all four sibling test suites still pass"
    verification:
      - kind: unit
        ref: "tests/test_ai_kit_rules_common.py#TestRemediationDockerKind.test_backcompat_report_carrying_only_three_pre_existing_kinds_is_byte_identical"
        status: pass
      - kind: unit
        ref: "python3 -m unittest tests.test_ai_kit_project_rules_arch tests.test_ai_kit_project_rules_precommit tests.test_ai_kit_project_rules_makefile tests.test_ai_kit_project_rules_agents"
        status: pass
    human_judgment: false

duration: 45min
completed: 2026-09-14
status: complete
---

# Phase 13 Plan 01: ai-kit-project-rules-docker tracer Summary

**Wired `ai-kit-project-rules-docker` end-to-end: an 8-target `docker-*` Makefile family check plus a `docker/local/README.md` runbook check, both gated on a root-scoped Docker-applicability check that keeps every non-Docker repo (including ai-kit's own) at zero findings.**

## Performance

- **Duration:** ~45 min
- **Tasks:** 2
- **Files modified:** 11 (6 created, 5 modified) across the two tasks, plus one lint-fix commit touching 1 file

## Accomplishments
- `docker_checker.check_docker_rules(repo_root)`: the aggregator plans 13-02/13-03 extend, gate-first, flat-list, Makefile path resolved once.
- D-D4 applicability gate: 4 evidence clauses (root compose file, root `Dockerfile`/`Dockerfile.*`, root `docker/` dir, `docker`/`docker-*` Makefile target), root-scoped and stat-based. Both of ai-kit's own repo's edges pinned as negatives: the nested `tests/e2e/docker/Dockerfile` and the docker-SUFFIXED `e2e-docker` target neither trip it.
- D-D1 family match: exact equality after normalization (casefold + `_`->`-`) against the fixed 8-name tuple, never a shape rule.
- D-D2 ordering: missing-target findings emitted in family-tuple declaration order (proven to differ from alphabetical order), deterministic across repeated runs.
- D-D3 identifier discipline: target-family findings carry `target` (the missing name); the runbook finding carries no `target` key.
- D-D23: the unreadable-Makefile wrap (`try/except (OSError, UnicodeDecodeError)`) lives in `docker_checker.py`'s `_normalized_targets_present` helper, the single call site both the gate and the family check route through.
- `STRUCTURAL_KINDS` grown to `("makefile", "precommit", "arch", "docker")`, additive-only, proven byte-identical for the pre-existing three-kind payload shape.
- New skill registered in `Makefile` (`test-unit`, `lint`), `.pre-commit-config.yaml` (`ruff`, `py-compile` file regexes; `unittest` entry), and `pyproject.toml` (`[tool.pyright] include`, `[tool.vulture] paths`) -- same surfaces the three siblings are in.
- No `SKILL.md` written (plan 13-04's job) -- skill stays uninstallable by the installer's skill-entry validator.

## Task Commits

Each task was committed atomically:

1. **Task 1: Wire the new skill end-to-end (tracer)** - `d42917b` (feat)
2. **[Deviation] Rule 1 lint fix: combine nested `if` into one condition (ruff SIM102)** - `1450f7d` (fix)
3. **Task 2: Fill out the new suite; pin grown STRUCTURAL_KINDS** - `86991b9` (test)

_Note: the fix commit (Rule 1) sits between Task 1 and Task 2 so Task 2's own commit stays scoped to exactly its two declared files (`tests/test_ai_kit_project_rules_docker.py`, `tests/test_ai_kit_rules_common.py`), per that task's own acceptance criterion._

## Files Created/Modified
- `skills/ai-kit-project-rules-docker/ai-kit-project-rules-docker.py` - 7-line entrypoint, siblings' pattern
- `skills/ai-kit-project-rules-docker/ai_kit_project_rules_docker/__init__.py` - shared-path sys.path append with named ImportError
- `skills/ai-kit-project-rules-docker/ai_kit_project_rules_docker/cli.py` - argparse-free `check`/`remediate`, no third subcommand
- `skills/ai-kit-project-rules-docker/ai_kit_project_rules_docker/docker_checker.py` - the aggregator: gate, family tuple, normalization, target/runbook findings, D-D23 wrap
- `skills/ai-kit-project-rules-docker/ai_kit_project_rules_docker/remediation.py` - thin re-export of the shared `build_remediation`
- `tests/test_ai_kit_project_rules_docker.py` - 42 tests: 6 tracer classes + 9 Task 2 classes (applicability gate, family-tuple-driven, normalization, ordering, runbook, identifiers, degradation, CLI, gate registration)
- `skills/_shared/ai_kit_rules_common/remediation.py` - `STRUCTURAL_KINDS` grown by one name (`"docker"`), comment extended
- `tests/test_ai_kit_rules_common.py` - `TestRemediationDockerKind` appended (7 methods): 4-kind tuple pin, byte-identical 3-kind backcompat, cross-kind ordering, advisory/needs_research paths, identifier precedence for both docker finding shapes
- `Makefile` - `test-unit`'s unittest list + `lint`'s `py_compile` list extended
- `.pre-commit-config.yaml` - `ruff`/`py-compile` `files:` regexes + `unittest` `entry:` list extended
- `pyproject.toml` - `[tool.pyright] include` + `[tool.vulture] paths` extended

## Decisions Made

**D-D4's applicability-gate rule as implemented:** root-level evidence only, checked with a bounded, constant number of operations -- `os.path.isfile`/`os.path.isdir` against explicitly-joined root paths for clauses (i)-(iii), plus one non-recursive `os.listdir(repo_root)` for clause (ii)'s `Dockerfile.*` variable-suffix matching (a single directory read, never a walk that descends into subdirectories), and `parse_makefile_targets_ordered` + D-D1 normalization + a PREFIX test for clause (iv). The two edges pinned: ai-kit's own nested `tests/e2e/docker/Dockerfile` (does not trip clause (ii) because the gate never descends past repo_root) and its `e2e-docker` Makefile target (does not trip clause (iv) because the normalized name `e2e-docker` fails the `startswith("docker-")` prefix test).

**Non-vacuity mutations, both applied and OBSERVED failing before revert:**
1. D-D1 equality->prefix: changed `_target_family_findings`'s `if name in present:` to `if any(p.startswith(name) for p in present):`. Ran the full docker suite -- exactly `TestNormalizationRule.test_docker_upload_and_docker_start_are_not_flagged_as_docker_up` failed (1 failure, 41 still passing), because under the mutation `docker-upload` now satisfies the `docker-up` slot. Reverted; suite green again (42/42).
2. D-D4 root-only->recursive-walk-plus-substring: changed `repo_uses_docker`'s root-only stat checks to an `os.walk(repo_root)` traversal for compose/Dockerfile/docker-dir evidence, and clause (iv)'s prefix test to a substring test (`"docker" in name`). Ran the full docker suite -- exactly 6 methods failed: the 4 `TestApplicabilityGateEvidenceClauses` negative-edge methods (`test_gate_not_satisfied_by_nested_compose_file`, `_nested_dockerfile`, `_nested_docker_directory`, `_e2e_docker_suffixed_target`) plus `TestTracerAiKitOwnRepo.test_ai_kit_own_repo_yields_no_findings` and `TestTracerApplicabilityEdges.test_nested_dockerfile_and_suffixed_target_yield_no_findings` (both encode the same nested/suffixed shape against this repo's own layout). 36 tests still passed. Reverted; suite green again (42/42).

**The family tuple as implemented, in declaration order** (plans 13-02, 13-03, and 13-04's `SKILL.md` all read this tuple rather than re-deriving it):
`docker-up`, `docker-health`, `docker-stop`, `docker-clean`, `docker-prune`, `docker-events-up`, `docker-events-monitor`, `docker-events-test`.
Normalization applied (D-D1): casefold, then fold `_` to `-`.

**D-D3's identifier outcome, measured from the Task 1 tracer fixture** (a Makefile carrying only `docker-up`/`docker-stop`, plus a compose file, missing the runbook): `remediate`'s 7 ids were
`['docker-health', 'docker-clean', 'docker-prune', 'docker-events-up', 'docker-events-monitor', 'docker-events-test', 'docker-local-runbook']` -- the first six are the missing target names (distinct, matching `finding["target"]`), and the seventh (`docker-local-runbook`) is the runbook finding's own `category`, since it carries no `target` key and `build_remediation` falls through to `finding.get("category")`.

**`STRUCTURAL_KINDS` growth:** appended `"docker"` as the fourth entry: `("makefile", "precommit", "arch", "docker")`. Proved behavior-preserving for the three existing consumers by: (a) a test asserting the first three entries keep their exact positions and the tuple has no duplicates; (b) a test rebuilding the EXACT pre-Phase-13 three-kind report and asserting the `remediate` list is byte-identical field-by-field to what it produced before this plan; (c) a test with all four kinds present, criticality order deliberately disagreeing with insertion order, asserting one merged criticality-sorted list; (d) running all four sibling test modules (`test_ai_kit_project_rules_arch`, `_precommit`, `_makefile`, `_agents`) after the edit -- all 398 combined tests plus the shared suite's own 99 pass.

**D-D23 as it landed:** the `try/except (OSError, UnicodeDecodeError)` wrap sits in `docker_checker.py`'s `_normalized_targets_present(makefile_path)` helper -- the ONE call site both `repo_uses_docker` (the gate's clause (iv)) and `_target_family_findings` route their `parse_makefile_targets_ordered` call through, so the wrap covers every shared-parser call this module makes without duplicating it. On catching either exception, the helper returns an empty set, which both callers treat identically to "Makefile declares no docker-shaped targets." Direct-call assertion (`test_shared_parser_raises_directly_on_binary_makefile_fixture`, plus the Task 1 acceptance criterion's `UNREADABLE-MAKEFILE-WRAP-OK` command) confirms `ai_kit_rules_common.makefile_parse.parse_makefile_targets` still raises `(OSError, UnicodeDecodeError)` on the same binary fixture -- so the checker's 9-finding, no-traceback result can only come from this skill's own wrap, not a shared-module behavior change.

**`makefile_checker.py` site read for D-D3's identifier anchor:** line 506 at planning time (confirmed live at the same line number during this execution) -- `finding = {"target": name, "present": False, "criticality": CRITICALITY_CRITICAL}` inside `for name in sorted(required):`, the missing-required-target loop: one finding PER missing name, each carrying that name, structurally the same one-finding-per-missing-name shape D-D2 requires here. This is the anchor relied on, NOT `makefile_checker.py:463`'s `{"target": "validate", ...}`, which is a hardcoded literal that happens to be a target name and demonstrates the convention only coincidentally.

**No divergence from D-D1 through D-D5 or D-D12.** One implementation note worth flagging explicitly rather than silently absorbing: D-D4's clause (ii) (`Dockerfile`/`Dockerfile.*`) needs to enumerate root-level filenames because the suffix varies, so `repo_uses_docker` calls `os.listdir(repo_root)` once (a single, non-recursive directory read) rather than a pure `os.path.isfile` stat per candidate name. This stays within the "never a directory walk, never a glob that descends" boundary the plan states (it reads exactly one directory, never descends into subdirectories, and costs the same order of syscalls as N `isfile` stats), but it is a `listdir` rather than a bare `isfile`/`isdir` call, so it is named here rather than left implicit.

**Plainly:** this plan added NO `docker-compose.yml` parsing of any kind, NO cache surface (`stack_cache.py`/`tooling_payload.py` absent; the word "cache" does not appear in the skill's own source outside comments -- confirmed by the `NO-CACHE-SURFACE-OK` acceptance criterion), and NO third subcommand (`check`/`remediate` only, unknown subcommand returns 2). No new runtime dependency was introduced anywhere (13-CONTEXT D-02) -- everything here is stdlib plus the shared `ai_kit_rules_common` package. Plan 13-02 starts from a clean seam, and plan 13-04's `SKILL.md` documents exactly two subcommands.

**ai-kit's own Makefile:** no target in this repo's own `Makefile` matched a family name or tripped clause (iv) -- the only docker-related target is `e2e-docker`, which is docker-SUFFIXED and correctly does not satisfy the D-D1-normalized prefix rule. Combined with the absence of a root compose file, root `Dockerfile`, or root `docker/` directory, ai-kit's own repository root produces zero findings, confirmed live by `TestTracerAiKitOwnRepo` and the `APPLICABILITY-EDGES-OK`/tracer commands. If this repo ever gains a root compose file, `Dockerfile`, or `docker/` directory, that test failing is the correct signal, not a nuisance -- its docstring states this explicitly.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug/lint] Combined nested `if` into one condition in the Dockerfile-evidence loop**
- **Found during:** Task 2's `make validate` run (ruff SIM102: "Use a single `if` statement instead of nested `if` statements")
- **Issue:** `repo_uses_docker`'s Dockerfile-detection loop had `if entry == "Dockerfile" or entry.startswith("Dockerfile."): if os.path.isfile(...): return True` -- a nested `if` ruff's SIM102 rule flags.
- **Fix:** Combined into one `and`-joined boolean condition. No behavior change -- the full docker test suite (42 tests) and the Task 1 tracer/`APPLICABILITY-EDGES-OK` commands were re-run and stayed green before and after.
- **Files modified:** `skills/ai-kit-project-rules-docker/ai_kit_project_rules_docker/docker_checker.py`
- **Verification:** `python3 -m unittest tests.test_ai_kit_project_rules_docker` (42/42 pass), `make validate`'s ruff pass no longer flags this file.
- **Committed in:** `1450f7d` (separate commit, kept out of Task 1's and Task 2's commits so both stayed scoped to their declared `<files>` lists)

**2. [Rule 1 - Bug/lint] Two `RUF005` list-concatenation findings in the new test file, fixed at authoring time**
- **Found during:** Task 2's `make validate` run, same pass as above
- **Issue:** `["DOCKER_UP"] + rest` and `["docker-upload", "docker-start", "up"] + rest` triggered ruff's RUF005 ("prefer unpacking over concatenation").
- **Fix:** Rewrote both as `["DOCKER_UP", *rest]` and `["docker-upload", "docker-start", "up", *rest]`.
- **Files modified:** `tests/test_ai_kit_project_rules_docker.py`
- **Verification:** `make validate`'s ruff pass no longer flags this file; docker suite stayed green (42/42).
- **Committed in:** `86991b9` (part of Task 2's own commit -- both fixes predate that commit's creation, so no separate commit was needed for these two)

---

**Total deviations:** 2 auto-fixed (both Rule 1 -- ruff lint findings in this plan's own new/modified files, caught by `make validate`).
**Impact on plan:** No scope creep. Both are mechanical lint conformance in files this plan already owns; no logic, finding schema, or test assertion changed as a result.

## Issues Encountered

`make validate` fails, but ONLY on four pre-existing, out-of-scope findings STATE.md already names as deferred to a later phase: `tools/status-line.py`, `tools/wizard_app.py`, `tests/test_ai_kit_spec.py`, `tests/test_ai_kit_spec_superpowers.py`. None of these files were touched by this plan. Confirmed by extracting every file path `ruff`/`pylint` cited in the `make validate` output after this plan's own two lint findings were fixed -- only those four remained.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `check_docker_rules(repo_root)`'s gate-then-extend shape is ready for plan 13-02 (compose parsing, D-01/D-02, SC2/SC3) and plan 13-03 (hot-reload/local-dev identification, D-03/D-04/D-05, SC4) to extend by appending calls inside the applicable branch, using the same `makefile_path` this plan already resolves once.
- `STRUCTURAL_KINDS` now carries `"docker"`, so Phase 15's cross-domain orchestrator will already see docker findings ordered beside `makefile`/`precommit`/`arch` ones once plans 13-02/13-03 add more.
- The skill remains uninstallable (no `SKILL.md`) until plan 13-04, which also owns the README.md row and the stale-status-line correction in `13-CONTEXT.md`.
- No blockers.

---
*Phase: 13-docker-rules-checker-ai-kit-project-rules-docker*
*Completed: 2026-09-14*

## Self-Check: PASSED

All created/modified files confirmed present on disk (11 files: 6 created, 5 modified, plus this SUMMARY.md). All three commit hashes (`d42917b`, `1450f7d`, `86991b9`) confirmed present in `git log`.
