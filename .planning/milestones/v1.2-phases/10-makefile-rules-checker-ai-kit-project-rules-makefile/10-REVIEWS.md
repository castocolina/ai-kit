---
phase: 10
reviewers: [opencode]
reviewed_at: 2026-09-14T05:51:43Z
plans_reviewed: [10-01-PLAN.md, 10-02-PLAN.md, 10-03-PLAN.md]
models:
  opencode: "xai/grok-4.6 (reasoning=high)"
model_sources:
  opencode: "pinned"
---

# Cross-AI Plan Review — Phase 10

<!-- gsd:plan-revision-conflicts:begin -->
## Plan-Revision Conflicts

_None recorded._
<!-- gsd:plan-revision-conflicts:end -->

## OpenCode Review

I'll review the three Phase 10 plans against the live source and the cycle-2 review record.
Using writing-clearly-and-concisely for the review. Next I’ll verify cycle-2 concerns against live source and the recovery commit.
Cycle-2 concerns are in the plans; I’ll verify recovered checker shape, pylint limits, and remaining source claims.
Cycle-2 MEDIUMs are in the plan text. Checking one fixture interaction that could still break re-homed tests.
# Cross-AI Plan Review — Phase 10 (cycle 3)

Verified against the live tree and `9d672b9`. Cycle-2 MEDIUMs are in the current plan text (Round 2 ledgers). No new HIGH/MEDIUM.

## 10-01

### Summary

Re-home, not a rewrite: recover the checker, stack detector, cache binding, and 15 deleted test classes from `9d672b9`, split parsers into `skills/_shared/ai_kit_rules_common/`, and stand up a `check`/`remediate`/`cache-update` skill that owns the `"makefile"` key Phase 9 dropped. Preconditions hold. Cycle 2’s MEDIUM (verbatim paste of recovered `stack_cache.py` vs single-source schema) is closed in this revision.

### Cycle-2 dispositions

| Concern | Status | Evidence |
|---|---|---|
| MEDIUM — recovered `stack_cache.py` is not a verbatim copy | **FULLY RESOLVED** | Recovered file still declares the three schema names (`REQUIRED_STATIC_TARGETS` / `RESEARCH_CATEGORIES` as tuples, `ALL_TOOLING_KEYS = REQUIRED_STATIC_TARGETS + RESEARCH_CATEGORIES`) and `_NAMESPACE = "agents-md-rules-checker"`. Plan now names it the one adapted file, lists the three edits, and `SCHEMA-SINGLE-SOURCE-OK` rejects any module-level assignment to those names plus object identity with `tooling_payload.py`. |
| LOW — Task 1 tracer never fires `chain_incomplete` | **STILL OPEN** (documented deferral) | Tracer fixture lists `ruff` as a `validate` prerequisite; recovered `_wired` treats a Make prerequisite as chained (`makefile_checker.py` at `9d672b9`, `_wired` / `member in validate_prereqs`). Coverage stays on Task 2’s `TestValidateChainAndAlias`. |
| LOW — must_haves say `sys.path` insert; sibling appends | **STILL OPEN** (documented deferral) | Sibling `__init__.py:25-26` appends. Task 1(b) still says copy the sibling exactly. |

### Strengths

- Preconditions are live. `makefile_checker.py` is absent from the agents package; `tooling_payload.py:5-9` still says UNWIRED; `9d672b9` resolves; recovered checker is 418 lines and still ends by appending `check_precommit_prepush_split`.
- Dropping that caller matches the design spec (`docs/superpowers/specs/2026-09-12-ai-kit-rules-skill-family-design.md:125-127`) and ROADMAP SC1’s three inherited checks (`ROADMAP.md:326`). `NO-PRECOMMIT-STAGE-FINDING-OK` uses hook id `unittest`, which is in recovered `SLOW_HOOK_KEYWORDS`.
- Shared split matches D-01/D-02/D-05. Sibling `__init__.py:6-26` is realpath → skills root → named `ImportError` → `sys.path.append`. `build_remediation` already reads `report.get("makefile", [])` (`remediation.py:52-74`). `cache_path` raises on `../escape` before join (`stack_cache.py:35-46`); recovered `cache_update` already catches that `ValueError`.
- Tracer fixture matches recovered emission: missing statics with `present is False`, `target: "test-unit-alias"` for the pairing check (`makefile_checker.py` recovered ~381-409), five `RESEARCH_CATEGORIES` (`tooling_payload.py:43-49`).
- Test roster is exact: recovered suite has 20 classes; these 15 are the Makefile-domain set. `TestWiredCheckWordBoundary` splits as the plan says (two methods through `check_makefile_shape`, one calls `_recipe_mentions_target`). `TestStackCache` in `tests/test_ai_kit_rules_common.py:170-276` already covers the generic engine.
- `CRITICALITY_*` in `rules.py:26-28` are 1/2/3. `min_confidence = 80` (`pyproject.toml:87`) will not flag an unused shared function. Installer requires `SKILL.md` (`tools/setup.py:586`). Gate surfaces match (`Makefile:46,70`, `.pre-commit-config.yaml:21,50,55`, `pyproject.toml:88,94`).

### Concerns

- **LOW** — `TestValidateOrderAndPrecommitPrepushSplit` has a fifth method the 2-way split does not name. Recovered class (`9d672b9` tests, lines 614-669): stub (`test_check_validate_order_never_adds_a_finding`), three splitter methods, and `test_categories_never_contain_removed_entries` (asserts `RESEARCH_CATEGORIES` does not contain `validate-order` / `precommit-vs-prepush-split`, via `stack_cache.RESEARCH_CATEGORIES`). The plan splits only splitter vs stub. That fifth method can be dropped while the class name still satisfies `RECOVERED-CLASSES`. It belongs in the skill suite next to the `tooling_payload.py` re-export.

### Suggestions

- Record that fifth method’s destination in the SUMMARY (skill suite, beside the schema re-export). Do not treat “the class was split” as covering every method.
- For the three cache classes: keep wrapper defaulting / namespace / stale-through-`check_makefile_shape` (`TestStaleCacheNotTrusted` is skill-binding). Drop `TestCachePathValidation.test_invalid_identifiers_raise` — it duplicates `TestStackCache.test_invalid_stack_identifier_raises` (`tests/test_ai_kit_rules_common.py:201-203`).
- Pin the promoted recipe-helper’s public name (recovered `_recipe_mentions_target`). Phase 11/14 will import it.

### Risk Assessment

**LOW.** Costly extraction, but the recovery blob, split lines, “home but no caller” rule, and schema-adaptation trap are grounded. Cycle 2’s paste-the-blob MEDIUM is gone.

---

## 10-02

### Summary

Adds the six new checks as paired-fixture TDD on the checker 10-01 re-homes, plus two additive edits to shared `build_remediation` (advisory → `auto_apply` off; carry `issue` forward). Cycle 2’s two MEDIUMs (untiered `unittest`, `--build` vs token-boundary) and the vacuous catch-all exemption are closed with pinned artifacts.

### Cycle-2 dispositions

| Concern | Status | Evidence |
|---|---|---|
| MEDIUM — `ADVISORY-NONBLOCKING-OK` depends on unpinned `unittest` vs `ruff` | **FULLY RESOLVED** | Spec concrete list (`design.md:308-311`) names `ruff`, no test runner. Task 3(c) now pins `test`/`unittest`/`pytest` in tier 4 and `ruff` in tier 2, exposes `speed_tier(name)`, and `SPEED-TIER-PINNED-OK` asserts `speed_tier('unittest') > speed_tier('ruff')`. |
| MEDIUM — `--build` fails the token-boundary helper | **FULLY RESOLVED** | Recovered helper is `(?<![-\w])NAME(?![-\w])` (`makefile_checker.py` at `9d672b9` ~168). Satisfaction is now exactly two mechanisms; `DOCKER-SATISFACTION-OK` flags the `--build`-only fixture; summary must name what was checked. |
| LOW — `%:` recipe-cap exemption is vacuous | **FULLY RESOLVED** | Header pattern `^(?!\.)([A-Za-z0-9_.-]+)\s*:(?!=)` has no `%`. Exempt set is now two members: default-goal-named target and literal `help`. |
| LOW — DEFAULT_GOAL exemption broader than spec (`L83`) | **STILL OPEN** (deferred, unchanged rationale) | Exempting the target a bare `make` runs vs false-positive on `usage`/`targets`/`list`. |

### Strengths

- Round 1 HIGH stays fixed. `remediation.py:52-64` routes a makefile finding to `remediate` only when `recommendation is not None`. Recovered checker sets that only for a missing target whose name is also a hook id. The `extra` hook with no `extra:` target is that shape; `[e['id'] for e in auto] == ['extra']` names it.
- Annotation-key note is exact. `build_remediation` does `finding.get("target", finding.get("category"))` (`remediation.py:53`). Excluding names that start with `validate` is required: otherwise `validate-security` contains `"security"` (`CATEGORY_KEYWORDS` recovered ~28-34) and requires itself. Pinned aliases match the spec (`design.md:91-96`).
- Help/fail cannot be detected from `parse_makefile_targets`. `_TARGET_HEADER_RE` drops `.DEFAULT_GOAL` via `(?!\.)` and drops `%:` (no `%` in the class). Stemless catch-all `^%[ \t]*:(?!=)` is the right narrowing.
- Docker pair is pinned and matches the Phase 13 roster (`design.md:106-108`): every spec name carries the `docker-` prefix. `docker-events-up` matches; prefix-less `events-up` does not.
- `WALK-PRUNES-DOTDIRS-OK` is the negative fixture `WALK-BOUNDED-OK` could not be. `id` kept as `validate` with `issue` as discriminator does not break `test_present_but_recommended_structural_finding_in_remediate` (`tests/test_ai_kit_rules_common.py:356-374`).
- This repo’s Makefile has neither `.DEFAULT_GOAL` nor `%:`, and it defines `format` / `security-scanner` / `duplicate-code` (`Makefile:103,109,116`) with no `validate-*` aliases. Treating findings against it as true positives is correct.
- Re-homed tests should survive the new checks: they index by `target`/`issue` rather than asserting exact finding-list length. `_FIXTURE_MAKEFILE_BASIC` has a `lint:` target, so the alias family will emit an extra missing-alias finding after Task 1; that does not collide with `arch-test` / `vulture` / `chain_incomplete` assertions.

### Concerns

None new at MEDIUM or above.

- **LOW** (carry-forward) — DEFAULT_GOAL-named target remains a broader recipe-cap exemption than the spec’s “help/fail-printing target”. Left as planned; re-raise with a concrete failing repo if it matters.

### Suggestions

- In the SUMMARY, copy the two Docker regex source strings from `DOCKER-SHAPE-OK` output; do not retype them.
- Rewrite `test_check_validate_order_never_adds_a_finding` against a real inverted fixture when Task 3 replaces the stub. Calling `check_validate_order("ignored", False)` still returns `None` on a missing Makefile (empty prereqs, no inversion), so the recovered assertion stays green and becomes vacuous.
- Record the two non-roadmap alias names (`formatter` / `code-smell-detector`) once, in code and in the SUMMARY.

### Risk Assessment

**LOW.** Paired-fixture discipline and the shared-builder edits are sound. Cycle 2’s two matching gaps that could make SC5 silently fail are now pinned and asserted.

---

## 10-03

### Summary

Docs-only close-out: write `SKILL.md`, one README row, `/skill-judge` as the code-review gate with committed evidence, `/naming-analyzer` as confirmation (no rename), and append-only corrections to ROADMAP SC1 and `REQ-rules-makefile`. Cycle 2’s LOW (thin `10-02-SUMMARY.md` frozen into `SKILL.md`) is now a hard Task 1 precondition.

### Cycle-2 dispositions

| Concern | Status | Evidence |
|---|---|---|
| LOW — four 10-02 facts only in `read_first` | **FULLY RESOLVED** | Task 1 `<precondition>` now requires `SUMMARY-INPUTS-PRESENT-OK` before any of `SKILL.md` is written, HALTs on missing/empty items, and forbids reconstructing them from plan prose or checker source. |
| LOW — recovered research-dispatch names `/agent-md-refactor` | **STILL OPEN** as already-controlled | `SKILL-SHAPE-OK` fails if that literal appears anywhere in the new document. Action already drops the hand-off and lettered steps. |
| LOW — no `skill-judge` → HALT, no self-score | **STILL OPEN** as already required | Task 2 `<precondition>` already says this verbatim. |

### Strengths

- `cc922e4:skills/ai-kit-agents-md-rules-checker/SKILL.md` resolves and contains `cache-update`, `(source:`, “research now”, “defer”, and Step D — plus `agent-md-refactor`, which this plan correctly forbids in the new document. Decision-criteria sentences already exist there (research now when few stacks; defer when many; ask rather than guess).
- Description-vs-body split matches host routing. Sibling `SKILL.md:3` description is the AGENTS.md/CLAUDE.md surface; `SKILL-SHAPE-OK` scopes the negative assertion to frontmatter so the body can still name the neighbor.
- Output-shape check is against a live `check` invocation. `auto_apply` off for advisory is the one fact a reader could otherwise get wrong (`remediation.py:62` today; 10-02 changes it).
- Judge gate is absolute (new skill, no baseline). Every judge fix must still pass Task 1’s verify chain — that blocks rubric-driven description broadening (T-10-12) and shape simplification (T-10-15). Phase 9’s evidence file (`09-SKILL-JUDGE.md:29-38`) already recorded that the installed rubric has no packaging/naming dimension; 10-03 tells the executor to re-confirm, not copy that forward.
- Naming: `ai-kit-project-rules-makefile` is locked by ROADMAP Phases 10–15. Recording a proposal without applying it is the only safe pipeline step.
- Amendment target is real. ROADMAP Phase 10 SC1 (`ROADMAP.md:326`) says “reproduces every check the old Makefile-checker performed” then lists three. Recovered `check_makefile_shape` appends a fourth via `check_precommit_prepush_split`. `REQUIREMENTS.md:77` says “inherits the Makefile-specific logic dropped by REQ-rules-agents-prune”. `AMENDMENT-OK` requiring `9d672b9` on the same REQ bullet matches Phase 9’s house style (`REQUIREMENTS.md:76`). Traceability row left alone.
- `cross_ai: false` is justified: `/skill-judge` and `/naming-analyzer` are host skills.
- Installer boundary is real: `tools/setup.py:586` requires `SKILL.md`. Plans 10-01/10-02 stay uninstallable; this plan is the one that crosses it.

### Concerns

None new.

### Suggestions

- Quote the three decision-criteria sentences in `10-03-SUMMARY.md` as the plan already requires.
- Restate the 180-vs-30 cache staleness discrepancy (`constraints.md:48` and `design.md:253` vs `stack_cache.py:22`) as an open question for Phase 11. If the re-homed research step names a day count, use 30 (the live engine). This plan’s own rule is document follows code.
- Sibling structure is the right scaffold. Do not pull in Wrap mechanism / Steps A–C.
- `AMENDMENT-OK` requires `9d672b9` on the same REQUIREMENTS line as `REQ-rules-makefile**`. Put the correction sentence on that bullet, not in a following paragraph.

### Risk Assessment

**LOW.** No Python, no gates, no installer write until the user re-runs setup. Residual risk is documentation drift from 10-02’s recorded decisions, now gated by `SUMMARY-INPUTS-PRESENT-OK`.

---

## Cross-plan

Wave order is right: shared extraction (costly) → new checks + additive `build_remediation` (costly for the shared builder) → installable docs. 10-01’s “home but no caller” for `check_precommit_prepush_split` and 10-03’s SC1 amendment are the same fact, stated twice on purpose.

**All cycle-2 MEDIUMs are FULLY RESOLVED** in the current plan text, independently re-checked against recovered `stack_cache.py:19-45`, `design.md:308-311`, and recovered `_recipe_mentions_target` at `9d672b9`. No HIGH remains from round 1 (`L78@2cb6b3a` was already closed in cycle 2).

The only new finding this cycle is 10-01’s unassigned fifth method on `TestValidateOrderAndPrecommitPrepushSplit` (LOW). Two round-1 LOWs remain documented deferrals (tracer vs `chain_incomplete`; `sys.path` insert vs append), not open work.

**Overall phase risk: LOW** (down from cycle 2’s MEDIUM). Phase 10 can meet REQ-rules-makefile as written.

---

## Consensus Summary

One prompt-fed, source-grounded reviewer ran this cycle (OpenCode / `xai/grok-4.6`,
reasoning=high). Its findings carry `file:line` evidence throughout — the recovery blob at
`9d672b9`, the live `skills/_shared/ai_kit_rules_common/` modules, the design spec, `ROADMAP.md`
and `REQUIREMENTS.md` — so no evidence-quality discount applies. With a single reviewer there is
no cross-reviewer corroboration to report; the sections below record its verdict rather than
agreement between independent reviewers.

**Every cycle-2 MEDIUM is FULLY RESOLVED, and no HIGH is open.** Independently re-verified
against source during this cycle's grounding pass:

- 10-01's "recovered `stack_cache.py` is not a verbatim copy target" — the plan now names it the
  one *adapted* file, and `SCHEMA-SINGLE-SOURCE-OK` (`10-01-PLAN.md:82` and its criterion) rejects
  any module-level re-declaration of the three schema names.
- 10-02's untiered-`unittest` MEDIUM — Task 3(c) pins `test`/`unittest`/`pytest` to tier 4 and
  `ruff` to tier 2, with a new `SPEED-TIER-PINNED-OK` criterion (`10-02-PLAN.md:628`) asserting
  `speed_tier('unittest') > speed_tier('ruff')` and that an unrecognized name still returns `None`.
- 10-02's `docker compose up --build` MEDIUM — satisfaction is now pinned to exactly two
  mechanisms with `DOCKER-SATISFACTION-OK` (`10-02-PLAN.md:627`) proving all three fixture
  outcomes, and the `--build`-only flag is documented as deliberate rather than a defect.
- 10-02's vacuous `%:` recipe-cap exemption — the exempt set is narrowed to two real members
  (default-goal-named target, literal `help`).
- 10-03's thin-`10-02-SUMMARY.md` LOW — promoted from a `read_first` bullet to a hard Task 1
  `<precondition>` with a mechanical `SUMMARY-INPUTS-PRESENT-OK` gate (`10-03-PLAN.md:127`) that
  HALTs and names the missing item.

### Agreed Strengths

- Preconditions remain live-checkable: `makefile_checker.py` is absent from the agents package,
  `tooling_payload.py:5-9` still carries its UNWIRED marker, and `9d672b9` resolves with the
  recovered checker still appending `check_precommit_prepush_split`.
- The shared-package split matches the constraints — sibling `__init__.py:6-26`'s realpath →
  skills-root → named `ImportError` → `sys.path.append` pattern, `build_remediation` already
  reading `report.get("makefile", [])` (`remediation.py:52-74`), and `cache_path` rejecting `../`
  escape before join (`stack_cache.py:35-46`).
- Cycle-2's concerns landed as pinned, directly-assertable artifacts (`SPEED-TIER-PINNED-OK`,
  `DOCKER-SATISFACTION-OK`, `SUMMARY-INPUTS-PRESENT-OK`) rather than prose — each one fails loudly
  and attributably instead of going silently inert.
- 10-03's "document follows code, never the reverse" posture and the absolute `/skill-judge` gate
  (no baseline to regress against, every judge fix re-running Task 1's verify chain) remain the
  right controls for a docs-only close-out.

### Agreed Concerns

Only one new finding this cycle:

- **LOW (10-01)** — the recovered `TestValidateOrderAndPrecommitPrepushSplit` class has **five**
  methods, but plan 10-01's two-way split (`10-01-PLAN.md:464` splitter half → shared suite;
  `10-01-PLAN.md:500` ordering-stub half → skill suite) names only four of them. Confirmed against
  `9d672b9:tests/test_ai_kit_project_rules_agents.py:614-669`: the fifth,
  `test_categories_never_contain_removed_entries`, asserts `RESEARCH_CATEGORIES` contains neither
  `validate-order` nor `precommit-vs-prepush-split` — a schema assertion that is neither a splitter
  case nor a stub case, so neither bullet claims it. `RECOVERED-CLASSES` (`10-01-PLAN.md:553`)
  grades class *names* only, so the method can be dropped while the criterion still passes.

Carry-forward LOWs re-flagged but already recorded as explicit, rationale-bearing deferrals in the
plans' own conflict tables (not open work):

- 10-01 — the Task 1 tracer never fires `chain_incomplete` (`L44@2cb6b3a`).
- 10-01 — must_haves say `sys.path` *insert* where the sibling *appends* (`L45@2cb6b3a`).
- 10-02 — the DEFAULT_GOAL-named-target recipe-cap exemption is broader than the spec's
  "help/fail-printing target" (`L83@2cb6b3a`).
- 10-03 — `SKILL-SHAPE-OK` already bans the `/agent-md-refactor` literal, and Task 2's
  `<precondition>` already requires a HALT when `skill-judge` is absent.

### Divergent Views

None — a single reviewer ran this cycle.
