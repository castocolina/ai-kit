---
phase: 26-session-self-resume-and-opengsd-quota-rules
plan: 08
subsystem: rules-checker
tags: [agents-md, opengsd, identity-probe, notices, e2e-tier, quota-policy]

# Dependency graph
requires:
  - phase: 26-session-self-resume-and-opengsd-quota-rules plan 07
    provides: the session-wake hook and state, whose wording R18 names
provides:
  - gsd_identity.probe: strict `@opengsd/gsd-core` identity check (ok | absent | unverified)
  - R18 (session wake) and R19 (subprocess quota pointer), both gated on the opengsd condition
  - notices key in build_remediation and the rules-all aggregate, carrying unverified findings
affects: [26-09, 26-10, 26-12]

actuals:
  tokens: 15310
  tasks: 3
  commits: 2

tech-stack:
  added: []
  patterns:
    - "tri-state condition (met | unmet | unverified); unverified becomes a not_applicable finding with unverified: true and a reason"
    - "identity probe runs with an env of only PATH and HOME and a 5 s timeout"
    - "e2e-tier module clears os.environ to a scratch HOME/XDG and a PATH of node and git symlinks"

key-files:
  created:
    - skills/_shared/ai_kit_rules_common/gsd_identity.py
    - tests/test_ai_kit_project_rules_all_e2e.py
  modified:
    - skills/_shared/ai_kit_rules_common/classification.py
    - skills/_shared/ai_kit_rules_common/remediation.py
    - skills/ai-kit-project-rules-agents/ai_kit_project_rules_agents/rules.py
    - skills/ai-kit-project-rules-agents/ai_kit_project_rules_agents/cli.py
    - skills/ai-kit-project-rules-all/ai_kit_project_rules_all/aggregate.py
    - tests/test_ai_kit_project_rules_agents.py
    - tests/test_ai_kit_project_rules_all.py
    - tests/test_ai_kit_rules_common.py
    - tests/test_ai_kit_project_rules_arch.py
    - tests/test_ai_kit_project_rules_cicd.py
    - tests/test_ai_kit_project_rules_docker.py
    - tests/test_ai_kit_project_rules_precommit.py
    - tools/run_unittest_parallel.py
    - Makefile
    - .pre-commit-config.yaml

requirements-completed: [QTA-05]

coverage:
  - id: D1
    description: "R18 and R19 apply only when `.planning/` exists and the probe proves `@opengsd/gsd-core`; each is checked and remediated separately"
    requirement: "QTA-05"
    verification:
      - kind: unit
        ref: "tests/test_ai_kit_project_rules_agents.py#TestOpenGsdRules"
        status: pass
    human_judgment: false
  - id: D2
    description: "An unprovable identity surfaces as an unverified notice in remediate and the rules-all aggregate; other valid names are plain not_applicable"
    requirement: "QTA-05"
    verification:
      - kind: unit
        ref: "tests/test_ai_kit_project_rules_agents.py#TestOpenGsdRules.test_unverified_identity_is_notice_in_remediate"
        status: pass
      - kind: unit
        ref: "tests/test_ai_kit_project_rules_agents.py#TestOpenGsdRules.test_unverified_notice_reaches_rules_all_aggregate"
        status: pass
    human_judgment: false
  - id: D3
    description: "Identity is exact: only `@opengsd/gsd-core` is ok; lookalikes are absent; unprovable shapes are unverified; the probe env holds only PATH and HOME"
    requirement: "QTA-05"
    verification:
      - kind: unit
        ref: "tests/test_ai_kit_rules_common.py#TestGsdIdentity"
        status: pass
    human_judgment: false
  - id: D4
    description: "R19's summary equals the policy reference's pointer block verbatim, and its groups match that pointer"
    requirement: "QTA-05"
    verification:
      - kind: unit
        ref: "tests/test_ai_kit_project_rules_agents.py#TestOpenGsdRuleText.test_r19_summary_is_the_policy_pointer_verbatim"
        status: pass
    human_judgment: false
  - id: D5
    description: "The real six-checker dispatch and the checkout-gsd-tools probe run only in the e2e tier, under a cleared scratch env"
    requirement: "QTA-05"
    verification:
      - kind: e2e
        ref: "tests/test_ai_kit_project_rules_all_e2e.py"
        status: pass
    human_judgment: false
orchestrator_verify: "VERIFY 26-08: 3/3 passed"
---

# Phase 26 Plan 08: OpenGSD-only R18 and R19 Summary

**R18 (session wake) and R19 (subprocess quota pointer) now apply only to a project whose gsd-core strictly proves `@opengsd/gsd-core`; an unprovable identity is reported as a notice in remediate and the rules-all aggregate.**

## Performance

- **Tasks:** 3 (Tasks 1 and 2 share one commit, as the plan requires)
- **Files changed:** 17 across both commits (`git diff --name-only f7fc889 HEAD`); the Task 3 commit touches 2 of them

## Accomplishments
- `gsd_identity.probe` reuses `ai_kit_spec.gsd_tools.resolve_gsd_tools`, `GsdTools` and `ai_kit_gsd_curated_config.gsd_catalog.resolve_node_binary`. `_shared` holds no second resolver, node lookup or run wrapper.
- The condition is tri-state. `unverified` yields a `not_applicable` finding with `unverified: true`, a reason, and a notice that reaches `remediate` and the rules-all aggregate.
- R18 and R19 are appended after R17 with `verbatim: true`. R19's summary is the policy reference's pointer block, pinned by a repo-only test.
- `notices` is present in every `build_remediation` payload and in the aggregate. Six shape pins were re-pinned to name it.
- The real-dispatch tests moved from the unit tier to `tests/test_ai_kit_project_rules_all_e2e.py`, listed in `E2E_MODULES`. That module clears `os.environ` to a scratch HOME/XDG and a PATH of `node` and `git` symlinks, skips without the checkout-local gsd-tools, and proves the agents probe ran that file.
- `make test-unit` green (61/61 plus the uv module); the e2e module green under uv; pyright 0 errors.

## Task Commits

1. **Tasks 1 and 2: OpenGSD-only R18 and R19 with an identity probe and notices** - `30dfd75` (feat)
2. **Task 3: pin the OpenGSD identity, the rule edges and the pointer sync** - `39387ba` (test)

**Plan metadata:** committed with this SUMMARY as the plan's last commit.

## Files Created/Modified
- `skills/_shared/ai_kit_rules_common/gsd_identity.py` - new probe (`OPENGSD_PACKAGE`, `probe`)
- `skills/_shared/ai_kit_rules_common/classification.py` - `condition_state`, `CONDITION_OPENGSD`, the unverified finding
- `skills/_shared/ai_kit_rules_common/remediation.py` - `notices` key, carried `verbatim` and per-stack flags
- `skills/ai-kit-project-rules-agents/ai_kit_project_rules_agents/rules.py` - R18, R19, `R19_POINTER`
- `skills/ai-kit-project-rules-agents/ai_kit_project_rules_agents/cli.py` - opengsd presence, keyword-only `env`/`run_fn`/`include_present`
- `skills/ai-kit-project-rules-all/ai_kit_project_rules_all/aggregate.py` - `notices` aggregation
- `tests/test_ai_kit_project_rules_all_e2e.py` - new e2e module (real dispatch, probe path proof)
- `tests/test_ai_kit_project_rules_all.py` - real-dispatch tests moved out; unit tier keeps fakes
- `tests/test_ai_kit_project_rules_agents.py` - `TestOpenGsdRules`, `TestOpenGsdRuleText`, re-pin
- `tests/test_ai_kit_rules_common.py` - `TestGsdIdentity`, re-pin
- `tests/test_ai_kit_project_rules_{arch,cicd,docker,precommit}.py` - `notices` re-pins
- `tools/run_unittest_parallel.py`, `Makefile`, `.pre-commit-config.yaml` - e2e listing and regenerated groups

## Decisions Made
- `probe()` returns the located gsd-tools path even when the identity command then does not run (no node, timeout). The docstring was corrected to say so; the earlier wording said `None` in that case.
- R18's flat signals need two of three matches to be `present`, per the classifier's existing `ceil(n/2)` rule. The Task 3 expectations were written against that rule, not against a guess.
- The `_shared` package now imports two sibling skills (`ai-kit-gsd-curated-config`, `ai-kit-spec-review`). No arch rule forbids it today. This is flagged for backlog 999.3 (the whole-tree layering suite) to decide.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Probe returned a bogus gsd-tools path in the test fake**
- **Found during:** Task 3 (TestGsdIdentity)
- **Issue:** The fake `run_fn` answered the resolver's `git rev-parse` call with identity JSON, so the project root resolved to junk and every identity case read as `unverified`.
- **Fix:** The fake routes by argv: `git` exits 128 as in a non-git scratch dir; only the identity call is recorded.
- **Files modified:** tests/test_ai_kit_rules_common.py
- **Verification:** `TestGsdIdentity` passes (7 tests).
- **Committed in:** 39387ba

**2. [Rule 1 - Bug] Test expectations for R18 near_miss and missing were wrong**
- **Found during:** Task 2 (`make`-tier unit run)
- **Issue:** I expected one matched signal to read as `missing`; the flat rule classifies one of three as `near_miss`.
- **Fix:** The expectations now follow the classifier's rule: 0 matches missing, 1 near_miss, 2 present.
- **Files modified:** tests/test_ai_kit_project_rules_agents.py
- **Committed in:** 30dfd75

**3. [Rule 3 - Blocking] Pre-commit hooks rejected the first commit attempt**
- **Found during:** Task 2 commit
- **Issue:** ruff flagged two unused imports; pylint flagged `probe()` for too many locals and returns.
- **Fix:** Removed the imports; split the run and classification into `_run_identity`. No suppression.
- **Committed in:** 30dfd75 (the hooks passed on the second attempt; no `--no-verify`)

**4. [Rule 3 - Blocking] Pyright errors in the new code**
- **Found during:** Tasks 1 and 3
- **Issue:** Optional narrowing for `load_gsd_tools`/`resolve_node_binary`, a `dict[str, str]` update into `dict[str, bool]`, and Optional subscripts in tests.
- **Fix:** Narrowed in source; the test helper now fails explicitly when a rule is absent.
- **Committed in:** 30dfd75, 39387ba

**Total deviations:** 4 auto-fixed (2 bugs, 2 blocking). **Impact on plan:** None on scope; each fix is within the plan's own acceptance criteria.

## Issues Encountered
- **Real dispatch in unit tier**: resolved by the e2e move. The e2e module's `node` runs use the checkout-local gsd-tools under a scrubbed env.
- **Pre-existing, not this plan**: `pyright` prints "a new pyright version is available" (1.1.410 to 1.1.414). It is an informational banner, not a failure.
- **Not run by this executor**: the `skill-judge` gate does not apply here (only plans 18.1-21 and 18.1-22). No SKILL.md was rewritten.
- **Not in this plan**: the agents SKILL.md Step C wording, the rule-count strings (17 to 20), and the README updates. They land in 26-09 by design (the plan's objective says so).
- **Live processes**: two `node ... cross-ai.mjs` processes (pids 978927 and 978929) belong to the orchestrator's supervisor for this plan, started before this executor's first command. They were not killed, per the rule to kill only processes this executor started. No `gc-late` or `node -e while` fake grandchildren were found.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- 26-09 can now edit the agents SKILL.md and the rule-count strings to 20, on the `verbatim` and `notices` contract this plan defines.
- Backlog 999.3 must decide whether `_shared` may import sibling skills (see Decisions Made).

---
*Phase: 26-session-self-resume-and-opengsd-quota-rules*
*Completed: 2026-10-30*
