---
phase: 10
reviewers: [opencode]
reviewed_at: 2026-09-14T05:24:51Z
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

I'll verify each plan against the live repo and the prior review, then write a section per plan id.
The shared modules and payload validator are in place; next I’ll check Phase 9’s prune, the recovery commit, and the sibling skill’s real wiring.
Phase 9 is landed and the recovery commit exists. I’ll read the recovered checker, sibling wiring, and prior review next.
Prior HIGH items look addressed in the plans; I’ll now check remaining source claims and hunt for new gaps.
Checking one more load-bearing fixture interaction and the recovered `stack_cache` vs the schema-single-source rule.
## 10-01

### Summary

A re-home, not a rewrite: recover `makefile_checker.py` / `stack_detect.py` / the skill-local cache binding and the 15 deleted test classes from `9d672b9`, split parsers into `skills/_shared/ai_kit_rules_common/`, and stand up a `check`/`remediate`/`cache-update` skill that owns the `"makefile"` key Phase 9 dropped. The recovery commit, prune parent, unwired `tooling_payload.py`, and sibling import/CLI patterns all match the tree. Round 1’s Task 2 stub-test contradiction is resolved in this revision (splitter → shared suite, ordering stub → skill suite, 10-02 rewrites that half in place).

### Strengths

- Precondition is live-checkable. `makefile_checker.py` is absent from the agents package; `tooling_payload.py` exists and still says it is UNWIRED (`tooling_payload.py:5-9`); `9d672b9` and prune `e56316e` both resolve.
- Recovery paths are post-rename. Recovered `check_makefile_shape` still ends by appending `check_precommit_prepush_split`. ROADMAP SC1 lists three inherited checks; the design spec assigns the fourth to the pre-commit skill (`docs/superpowers/specs/2026-09-12-ai-kit-rules-skill-family-design.md:125-127`). `NO-PRECOMMIT-STAGE-FINDING-OK` uses a slow hook with no `stages:` — `SLOW_HOOK_KEYWORDS` includes `"unittest"`.
- Shared-package split matches D-01/D-02/D-05. Sibling `__init__.py:6-26` is realpath → skills root → named `ImportError` → `sys.path.append`. `build_remediation` already reads `report.get("makefile", [])` (`remediation.py:52-74`). `cache_path` raises on `../escape` before join (`stack_cache.py:35-46`); recovered `cache_update` already catches that `ValueError`.
- Tracer fixture matches recovered emission: missing statics with `present is False`, `target: "test-unit-alias"` for the pairing check, five `RESEARCH_CATEGORIES` findings (`tooling_payload.py:43-49`). The fixture’s `ruff` hook/target matches no `CATEGORY_KEYWORDS` substring.
- Test roster is exact. Recovered suite has 20 classes; these 15 are the Makefile-domain set. `TestWiredCheckWordBoundary` really splits: two methods go through `check_makefile_shape`, one calls `_recipe_mentions_target`. `TestStackCache` in `tests/test_ai_kit_rules_common.py:170-276` already covers the generic engine.
- `CRITICALITY_*` in `rules.py:26-28` are 1/2/3. `min_confidence = 80` (`pyproject.toml:87`) will not flag an unused shared function. Installer requires `SKILL.md` (`tools/setup.py:586`). Gate surfaces match (`Makefile:46,70`, `.pre-commit-config.yaml:21,50,55`, `pyproject.toml:88,94`).

### Concerns

- **MEDIUM** — Recovered skill-local `stack_cache.py` is **not** a verbatim copy target. At `9d672b9` it already wraps the shared engine **and** still declares `REQUIRED_STATIC_TARGETS` / `RESEARCH_CATEGORIES` / `ALL_TOOLING_KEYS` as tuple literals (recovered `stack_cache.py:19-45`). Task 1(a) says copy recovered sources verbatim; Task 1(b) and `SCHEMA-SINGLE-SOURCE-OK` forbid those literals. An executor who `git show`s that blob into the new tree fails the schema criterion. The recovered file is a wrapper to imitate (namespace `project-rules-makefile`, re-export from `tooling_payload.py`), not a blob to paste.
- **LOW** — Task 1 tracer still never fires `chain_incomplete` (fixture lists `ruff` as a `validate` prerequisite; recovered `_wired` treats a Make prerequisite as chained). Coverage depends on re-homed `TestValidateChainAndAlias` / `TestWiringViaPrerequisites`. Unresolved from round 1 (`L44@2cb6b3a`); structurally OK because Task 2 is not optional.
- **LOW** — Must-haves still say a `sys.path` **insert**; sibling `__init__.py:25-26` **appends**. Task 1(b) already says copy the sibling. Unresolved from round 1 (`L45@2cb6b3a`).

### Suggestions

- In the SUMMARY, state explicitly that recovered `stack_cache.py` was **adapted** (schema stripped, namespace renamed), not copied. Record `project-rules-makefile` as the namespace string.
- For the three cache classes, keep only namespace/wrapper/stale-through-checker cases. `TestCachePathValidation.test_invalid_identifiers_raise` is already `TestStackCache.test_invalid_stack_identifier_raises`.

### Risk Assessment

**LOW.** Costly extraction, but the recovery blob, split lines, and “home but no caller” rule are grounded. Round 1’s stub-test contradiction is gone. Main remaining execution trap is pasting the recovered cache-binding file verbatim.

---

## 10-02

### Summary

Adds the six new checks as paired-fixture TDD on the checker 10-01 re-homes, plus two additive edits to shared `build_remediation` (advisory → `auto_apply` off; carry `issue` forward). Round 1’s HIGH (`ADVISORY-NONBLOCKING-OK` unsatisfiable) and the docker/catch-all/walk-pruning MEDIUMs are addressed in this revision with pinned regexes and a third hook id. Two new matching gaps remain: the advisory proving fixture depends on classifying `unittest` as slower than `ruff`, which the spec’s concrete name list does not include; and a token-boundary `build` check will miss `docker compose up --build`.

### Strengths

- Round 1 HIGH is actually fixed. `remediation.py:52-64` routes a makefile finding to `remediate` only when `recommendation is not None`. Recovered checker sets that only for a missing target whose name is also a hook id. The revised fixture’s `extra` hook with no `extra:` target is that shape; `[e['id'] for e in auto] == ['extra']` names it. `.DEFAULT_GOAL := help` keeps Task 2’s reachability check silent; both chainable members are wired so the inherited chain check does not suppress the advisory.
- Annotation-key note is exact. `build_remediation` does `finding.get("target", finding.get("category"))` (`remediation.py:53`). Excluding names that start with `validate` is required: otherwise `validate-security` contains `"security"` and requires itself. Pinned aliases `validate-security` / `validate-duplicate` / `validate-dead` match the spec (`...design.md:91-96`).
- Help/fail cannot be detected from `parse_makefile_targets`. `_TARGET_HEADER_RE` is `^(?!\.)([A-Za-z0-9_.-]+)\s*:(?!=)` — `.DEFAULT_GOAL` is dropped by `(?!\.)`, `%:` is not in the character class. Stemless catch-all `^%[ \t]*:(?!=)` is the right narrowing: a suffix rule is not a help path.
- Docker pair is now pinned and matches the Phase 13 roster: every spec name carries the `docker-` prefix (`...design.md:106-108`). `docker-events-up` matches; prefix-less `events-up` does not.
- `WALK-PRUNES-DOTDIRS-OK` is the negative fixture `WALK-BOUNDED-OK` could not be. Advisory `auto_apply` derived in the shared builder, not only in the checker (`remediation.py:62` is unconditionally `True` today). `id` kept as `validate` with `issue` as discriminator is the additive option that does not break `test_present_but_recommended_structural_finding_in_remediate` (`tests/test_ai_kit_rules_common.py:356-374`).
- This repo’s Makefile has neither `.DEFAULT_GOAL` nor `%:`, and it defines `format` / `security-scanner` / `duplicate-code` (`Makefile:103,109,116`) with no `validate-*` aliases. Treating findings against it as true positives is correct.

### Concerns

- **MEDIUM** — `ADVISORY-NONBLOCKING-OK` still depends on a classification the plan does not pin. The fixture inverts `validate: unittest ruff`. Spec concrete names (`...design.md:308-311`) list `ruff` in the fast-linter tier and never mention `unittest`. Action text says “test suites last” but does not name `unittest`/`pytest` as keywords. A name matching nothing is skipped and cannot form an inversion — so a spec-literal table leaves `unittest` untiered, emits no advisory, and the criterion fails the same way round 1’s fixture did. Pin `unittest`/`pytest`/`test` in the slowest tier and `ruff` in the fast-linter tier in the plan (and SUMMARY).
- **MEDIUM** — Inline-build satisfaction via a token-boundary `build` miss the common Compose flag. Recovered `_recipe_mentions_target` requires the character before the match to be neither `-` nor `_` nor alnum. In `docker compose up --build`, the character before `build` is `-`, so the lookbehind fails. Spec wording is “or an inline `build` invocation” (`...design.md:107`). A `docker-up` recipe that only has `--build` and no `docker-build` prerequisite will be flagged. Treat `--build` as a standalone build token, or document that only a Make prerequisite / `$(MAKE) docker-build` counts.
- **LOW** — Catch-all recipe-cap exemption is vacuously true under the planned loop. `parse_makefile_targets` never returns `%:`, so “for each present target” never sees the catch-all body. A 6-line `%:` fixture produces no finding whether or not the exempt set includes it. Literal `help` and the DEFAULT_GOAL-named target are the only testable exemptions. Unresolved DEFAULT_GOAL breadth (`L83@2cb6b3a`) still stands.

### Suggestions

- Write the speed-tier table in the plan with the proving fixture’s names in it (`unittest` last, `ruff` second), not only the spec’s rust/go/python examples.
- For docker inline-build, accept `--build` as a token, or drop “standalone build token” and require a build-shaped Make prerequisite only (which is what ROADMAP SC5 actually states).
- 10-01’s `test_check_validate_order_never_adds_a_finding` calls `check_validate_order("ignored", False)` and will still pass after the stub is replaced (no Makefile → empty prereqs → no inversion). Rewrite it against a real inverted fixture so it does not go vacuous.

### Risk Assessment

**MEDIUM.** Paired-fixture discipline and the shared-builder edits are sound; round 1’s blocking fixture bug is gone. Residual execution risk is the advisory criterion silently failing if `unittest` is not a slow-tier keyword, and a `--build` false positive Phase 13 will inherit.

---

## 10-03

### Summary

Docs-only close-out: write `SKILL.md`, one README row, `/skill-judge` as the code-review gate with committed evidence, `/naming-analyzer` as confirmation (no rename), and append-only corrections to ROADMAP SC1 and `REQ-rules-makefile`. The over-broad inheritance claim is a live fact: recovered `check_makefile_shape` emitted a fourth finding via `check_precommit_prepush_split`. Routing, report-only boundary, and “fix the document to match the code, never the reverse” are the right controls.

### Strengths

- `cc922e4:skills/ai-kit-agents-md-rules-checker/SKILL.md` resolves and contains `cache-update`, `(source:`, “research now”, “defer”, and Step D — plus `agent-md-refactor`, which this plan correctly forbids in the new document. Decision-criteria sentences already exist there (research now when few stacks; defer when many; the third is the “ask rather than guess” instruction 10-03 must keep).
- Description-vs-body split matches host routing. Sibling `SKILL.md` description is the AGENTS.md/CLAUDE.md surface; `SKILL-SHAPE-OK` scopes the negative assertion to frontmatter so the body can still name the neighbor.
- Output-shape check is against a live `check` invocation. `auto_apply` off for advisory is the one fact a reader could otherwise get dangerously wrong (`remediation.py:62` today; 10-02 changes it).
- Judge gate is absolute (new skill, no baseline). Every judge fix must still pass Task 1’s verify chain — that blocks rubric-driven description broadening (T-10-12) and shape simplification (T-10-15).
- Naming: `ai-kit-project-rules-makefile` is locked by ROADMAP Phases 10–15. Recording a proposal without applying it is the only safe pipeline step.
- Amendment target is real. ROADMAP Phase 10 SC1 (`ROADMAP.md:326`) says “reproduces every check the old Makefile-checker performed” then lists three. `REQUIREMENTS.md:77` says “inherits the Makefile-specific logic dropped by REQ-rules-agents-prune”. `AMENDMENT-OK` requiring `9d672b9` on the same REQ bullet matches Phase 9’s house style (`REQUIREMENTS.md:76` already appends on one line). Traceability row left alone (`REQUIREMENTS.md` REQ-rules-makefile row).
- `cross_ai: false` is justified: `/skill-judge` and `/naming-analyzer` are host skills.

### Concerns

- **LOW** — Task 1 must copy alias map, docker shape, speed tiers, and the shellcheck CI-limit sentence from `10-02-SUMMARY.md`. If 10-02’s SUMMARY is thin — especially if the two unpinned aliases or the `unittest`/`ruff` tier keywords are missing — `SKILL.md` freezes a guess. Make that SUMMARY a hard precondition, not just a `read_first` bullet. Unresolved from round 1 (`L116@2cb6b3a`).
- **LOW** — Recovered research-dispatch still talks about lettered steps and `/agent-md-refactor`. `SKILL-SHAPE-OK` fails if that literal appears anywhere in the new document, including an anti-pattern that names it in order to forbid it. Strip the mechanism name entirely; name the sibling skill in the body if a boundary must be stated.
- **LOW** — Judge fix-loop cap of 3 with escalate-rather-than-lower-the-bar is correct. An executor without `skill-judge` installed must HALT; do not substitute a self-score.

### Suggestions

- Quote the three decision-criteria sentences in `10-03-SUMMARY.md` as the plan already requires.
- Restate the 180-vs-30 cache staleness discrepancy (`constraints.md:48` and design spec line 253 vs `stack_cache.py:22`) as an open question for Phase 11. If the re-homed research step mentions a day count, make it 30 (the live engine), not 180 — 10-03’s own rule is document follows code.
- Sibling structure is the right scaffold. Do not pull in Wrap mechanism / Steps A–C.

### Risk Assessment

**LOW.** No Python, no gates, no installer write until the user re-runs setup. Residual risk is documentation drift from 10-02’s recorded decisions, already mitigated in the verify chain.

---

## Cross-plan

Wave order is right: shared extraction (costly) → new checks + additive `build_remediation` (costly for the shared builder) → installable docs. 10-01’s “home but no caller” for `check_precommit_prepush_split` and 10-03’s SC1 amendment are the same fact, stated twice on purpose.

**Prior HIGH (`L78@2cb6b3a`) is resolved.** Independent re-check: `remediation.py:55-64` still auto-applies any makefile finding with a non-`None` `recommendation`; recovered `check_makefile_shape` still sets that only when the missing target is also a pre-commit hook id; the revised fixture’s `extra` hook is that finding. No other round-1 HIGH remains.

Highest remaining execution defect is 10-02’s advisory proving fixture depending on unpinned `unittest` speed-tier membership, plus `--build` vs token-boundary. Phase 10 can meet REQ-rules-makefile if those two matching rules are written down rather than left to taste.

**Overall phase risk: MEDIUM** (down from round 1 only because the blocking fixture bug is gone; not LOW while SC5’s non-blocking proof can still miss).

---

## Consensus Summary

One prompt-fed, source-grounded reviewer ran this cycle (OpenCode / `xai/grok-4.6`, reasoning=high).
Its findings carry `file:line` evidence throughout — recovered blobs at `9d672b9`, the live
`skills/_shared/ai_kit_rules_common/remediation.py`, `stack_cache.py`, `tooling_payload.py`, the
design spec, `ROADMAP.md` and `REQUIREMENTS.md` — so no evidence-quality discount applies. With a
single reviewer there is no cross-reviewer corroboration to report; the sections below record its
verdict rather than agreement between independent reviewers.

**Round 1's HIGH is resolved.** `L78@2cb6b3a` (`ADVISORY-NONBLOCKING-OK` unsatisfiable on its own
fixture) was independently re-checked against `remediation.py:52-64` and the recovered
`check_makefile_shape`: the revised fixture's `extra` pre-commit hook with no matching Makefile
target is the one finding shape that carries a non-`None` `recommendation`, so the auto-apply
contrast the criterion asserts is now real. No HIGH concern was raised this cycle and no prior HIGH
remains open.

### Agreed Strengths

- The re-home is grounded in a real recovery point: `9d672b9` and prune parent `e56316e` both
  resolve, `makefile_checker.py` is genuinely absent from the agents package, and
  `tooling_payload.py` still carries its UNWIRED marker — every precondition is live-checkable.
- The shared-package split matches the constraints: the sibling `__init__.py` realpath →
  skills-root → named `ImportError` pattern, `build_remediation` already reading
  `report.get("makefile", [])`, and `cache_path` rejecting `../` escape before join.
- Round 1's MEDIUMs landed with pinned artifacts rather than prose: the two Docker shape regexes,
  the stemless `^%[ \t]*:(?!=)` catch-all narrowing, the `WALK-PRUNES-DOTDIRS-OK` negative fixture,
  and the additive `issue` carry-forward that disambiguates two `validate`-keyed remediate rows.
- 10-03's "document follows code, never the reverse" posture and the absolute `/skill-judge` gate
  (no baseline to regress against, every judge fix re-running Task 1's verify chain) are the right
  controls for a docs-only close-out.

### Agreed Concerns

Highest-priority items this cycle, in the reviewer's own severity order:

- **MEDIUM (10-01)** — recovered `stack_cache.py` is not a verbatim copy target. At `9d672b9` it
  already wraps the shared engine *and* still declares `REQUIRED_STATIC_TARGETS` /
  `RESEARCH_CATEGORIES` / `ALL_TOOLING_KEYS` as tuple literals. Task 1(a)'s "copy verbatim" and
  Task 1(b) + `SCHEMA-SINGLE-SOURCE-OK` (and threat row T-10-02, which forbids a second literal
  schema copy) contradict each other for this one file.
- **MEDIUM (10-02)** — `ADVISORY-NONBLOCKING-OK` depends on `unittest` being classified slower than
  `ruff`, but the plan sources its tier table from the design spec's concrete name list, which
  names `ruff` and never mentions `unittest`. An untiered name is skipped by design, so a
  spec-literal table emits no advisory and the criterion fails.
- **MEDIUM (10-02)** — the inline-build escape hatch misses `docker compose up --build`: the
  recovered `_recipe_mentions_target` boundary rejects a preceding `-`, so a `docker-up` recipe
  whose only build is `--build` is flagged.
- **LOW (10-02)** — the catch-all exemption from the 3-line recipe cap is vacuous: `parse_makefile_targets`
  never returns `%:`, so the planned per-present-target loop never sees a catch-all body.
- **LOW (10-03)** — Task 1 must copy the alias map, Docker shape, speed tiers and shellcheck CI
  sentence out of `10-02-SUMMARY.md`, but that file is only a `read_first` bullet, not a
  precondition; a thin SUMMARY freezes a guess into `SKILL.md`.

### Divergent Views

None — a single reviewer ran this cycle. Two round-1 LOWs the reviewer re-flagged as "unresolved"
(the Task 1 tracer never firing `chain_incomplete`; must-haves saying `sys.path` *insert* where the
sibling *appends*) are in fact explicitly addressed and deferred in 10-01's own Round-1 conflict
table with stated rationale, so they are recorded here as a reviewer/plan disagreement about
whether a documented deferral counts as resolution, not as open work.
