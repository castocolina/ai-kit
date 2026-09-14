---
phase: 10
reviewers: [opencode]
reviewed_at: 2026-09-14T04:54:59Z
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

I'll verify each plan against the live repo rather than the plan text, starting with the recovery commit, shared package, and Phase 9 prune state.
Phase 9 landed: `makefile_checker.py` is gone and `tooling_payload.py` sits unwired. Next I’ll check the recovery commit, sibling CLI, and the claims the plans treat as load-bearing.
Recovery commit and prune both resolve. Next I’ll inspect the recovered checker, test roster, gate surfaces, and a few claims that look load-bearing.
## 10-01

### Summary

A re-home, not a rewrite: recover `makefile_checker.py` / `stack_detect.py` / skill-local `stack_cache.py` and the 15 deleted test classes from `9d672b9`, split parsers into `skills/_shared/ai_kit_rules_common/`, and stand up a `check`/`remediate`/`cache-update` skill that owns the `"makefile"` key Phase 9 dropped. The recovery commit, prune parent, unwired `tooling_payload.py`, and sibling import/CLI patterns all match the tree. The one ownership trap the plan names is real: recovered `check_makefile_shape` still appends `check_precommit_prepush_split`. Dropping that caller while still moving the function is the right Phase 11 boundary.

### Strengths

- Precondition is live-checkable. `makefile_checker.py` is absent from the agents package; `tooling_payload.py` exists and still says it is UNWIRED (`tooling_payload.py:5-9`); `9d672b9` and prune `e56316e` both resolve. Re-deriving the checker from the spec would reopen the gap Phase 9 just created.
- Recovery paths are post-rename, as claimed. `git show 9d672b9:.../makefile_checker.py` is the 418-line file whose last act is `split_finding = check_precommit_prepush_split(...)` then `findings.append`. ROADMAP SC1 lists three inherited checks; the design spec assigns the fourth to the pre-commit skill (`docs/superpowers/specs/2026-09-12-ai-kit-rules-skill-family-design.md:125-127`). `NO-PRECOMMIT-STAGE-FINDING-OK` uses a slow hook with no `stages:` — the exact input the moved splitter fires on (`SLOW_HOOK_KEYWORDS` includes `"unittest"`).
- Shared-package split matches D-01/D-02/D-05 and the import convention. Sibling `__init__.py:6-26` is the realpath → skills root → named `ImportError` → `sys.path.append` pattern. `build_remediation` already reads `report.get("makefile", [])` (`remediation.py:52-74`). `cache_path` raises on `../escape` before join (`stack_cache.py:24-46`); recovered `cache_update` already catches that `ValueError`.
- Finding shape the tracer asks for is what the recovered checker actually emits: missing static targets with `present is False`, `target: "test-unit-alias"` for the pairing check, and one finding per `RESEARCH_CATEGORIES` entry (`tooling_payload.py:43-49`). The tracer fixture’s `ruff` hook/target does not match any `CATEGORY_KEYWORDS` substring, so all five category findings fire.
- Test roster is exact. Recovered `tests/test_ai_kit_project_rules_agents.py` has 20 classes; Phase 9’s SUMMARY deleted 15; the 15 names in Task 2 match. `TestWiredCheckWordBoundary` really does split: two methods go through `check_makefile_shape` (chain membership), one calls `makefile_checker._recipe_mentions_target` (the helper to promote). `TestStackCache` in `tests/test_ai_kit_rules_common.py:170-276` already covers the generic engine, so the “keep binding, drop engine” instruction is load-bearing.
- `CRITICALITY_*` literals in `rules.py:26-28` are 1/2/3. Drift guard via `ast` (not a runtime import of the sibling package) matches `.planning/intel/constraints.md`. `min_confidence = 80` in `pyproject.toml:87` really will not flag an unused shared function (vulture reports those at 60).
- Installer boundary is real: `tools/setup.py:586` requires `SKILL.md`. Gate surfaces match the cited lines (`Makefile:46,70`, `.pre-commit-config.yaml:21,50,55`, `pyproject.toml:88,94`). T-10-01 through T-10-05 map to those mechanisms.

### Concerns

- **MEDIUM** — Task 2(a) and 2(b) contradict on the ordering-stub half of `TestValidateOrderAndPrecommitPrepushSplit`. (a) says leave it out of this commit (10-02 will replace the stub). (b) says port `test_check_validate_order_never_adds_a_finding` into the skill suite. Follow (b): the recovered method asserts `check_validate_order(...) is None` for both `True`/`False`, which is the post-Task-1 behavior. 10-02 then rewrites those tests.
- **LOW** — The Task 1 tracer never fires `chain_incomplete`. The fixture lists `ruff` as a `validate` prerequisite, and recovered wiring treats a Make prerequisite as chained. Coverage depends on re-homed `TestValidateChainAndAlias` / `TestWiringViaPrerequisites` / `TestWiredCheckWordBoundary`. If Task 2 is deferred or split, SC1’s second inherited check has no end-to-end proof.
- **LOW** — Must-haves say a `sys.path` **insert**; sibling `__init__.py:25-26` **appends**. Copy the sibling. Insert vs append only matters if something else already put a different `ai_kit_rules_common` on `sys.path`.
- **LOW** — “Sibling class’s five checks, retargeted” lists Makefile / ruff+py-compile / unittest / pyright / vulture. The sibling’s fifth method is `test_validate_covers_every_precommit_hook` (`tests/test_ai_kit_project_rules_agents.py:394-425`), a this-repo hook-parity check that is Phase 11’s job. Do not copy that method.

### Suggestions

- In the SUMMARY, resolve the stub-test contradiction explicitly: skill suite in 10-01, rewritten in 10-02.
- For the three cache classes, keep only namespace/wrapper/stale-through-checker cases. `TestCachePathValidation.test_invalid_identifiers_raise` is already `TestStackCache.test_invalid_stack_identifier_raises`.
- Namespace `project-rules-makefile` is a new choice. Recovered binding used `agents-md-rules-checker`; `default_cache_root`’s docstring still examples `"makefile-rules-checker"`. Record the string so Phase 11 does not invent a third.

### Risk Assessment

**LOW.** Costly extraction, but the recovery blob, split lines, and “home but no caller” rule are grounded in source. Main execution risk is the Task 2 stub-test contradiction, not the production split.

---

## 10-02

### Summary

Adds the six new checks as paired-fixture TDD on the checker 10-01 re-homed, plus one additive `auto_apply` change in shared `build_remediation`. SC2–SC5, the `category`-vs-identifier trap, alias/chain double-report rule, ordered-prereq reader, and “do not silence this repo’s Makefile” note are all right. The Task 3 CLI criterion `ADVISORY-NONBLOCKING-OK` will fail as written: its fixture produces no non-advisory makefile finding with a `recommendation`, so `any(auto_apply is True)` is false.

### Strengths

- Annotation-key note is exact. `build_remediation` does `identifier = finding.get("target", finding.get("category"))` (`remediation.py:53`). A new finding that stuffed the tooling category into `category` while also setting `target` would still identify as the target, but a category-only finding would steal the identifier. Inherited tooling findings are the ones keyed by `category` (`remediation.py:20-21`, `test_blocked_preserves_stacks` at `tests/test_ai_kit_rules_common.py:376-393`).
- Alias family reuses `CATEGORY_KEYWORDS` and the recovered `_wired` rule (recipe token-boundary **or** Make prerequisite). Excluding names that start with `validate` is required: otherwise `validate-security` contains `"security"` and requires itself. Roadmap-pinned names `validate-security` / `validate-duplicate` / `validate-dead` match the design spec (`...design.md:91-96`).
- Help/fail cannot be detected from `parse_makefile_targets`. `_TARGET_HEADER_RE` is `^(?!\.)([A-Za-z0-9_.-]+)\s*:(?!=)` — `.DEFAULT_GOAL` is dropped by `(?!\.)`, `%:` is not in the character class. Own patterns against raw text are mandatory.
- Recipe-cap quadratic warning is real: recovered `parse_makefile_recipe` re-reads the file per target. Not changing that shared signature is the right Phase 11/14 constraint.
- Advisory path is the only place a suggestion must survive `remediate`. Today the makefile branch hard-codes `"auto_apply": True` (`remediation.py:55-63` and the docstring at 22-24). `test_present_but_recommended_structural_finding_in_remediate` (`tests/test_ai_kit_rules_common.py:356-374`) pins that. Deriving `auto_apply` from absence of an advisory flag is the minimum additive change. Slowest-tier-first matching matches the spec’s substring hazard (`ruff` vs slower names that contain fast tokens).
- Shellcheck CI half stated as unconfirmed matches PROJECT.md’s certainty rule and the spec (`...design.md:109-113`). Not stubbing a pass is correct.
- This repo’s Makefile has neither `.DEFAULT_GOAL` nor `%:` (`Makefile:45-70` is a normal `test-unit` recipe). Treating findings against it as true positives, and not editing it, prevents the checker from being tested against a silenced subject.

### Concerns

- **HIGH** — `ADVISORY-NONBLOCKING-OK` is unsatisfiable on its own fixture. The Makefile defines `help`/`unittest`/`ruff`/`validate: unittest ruff`, with matching hook ids. Recovered checker then: missing static targets have no stack markers → `needs_research True`, `recommendation None` → **blocked**; both hook ids exist as targets → no hook-gap recommendation; categories likewise blocked; help/recipe/docker/shellcheck silent; advisory is the only `remediate` entry, with `auto_apply False`. `assert any(e['auto_apply'] is True for e in r['remediate'])` fails. Fix: add one finding that still auto-applies, e.g. a hook id with no Makefile target (`id: extra` and no `extra:` target), or a 4-line non-help recipe.
- **MEDIUM** — Docker shape rule disagrees with itself. Action: “start with the docker prefix and end with the respective verb” (covers `docker-up`, not `events-up`). Same paragraph: Phase 13’s family includes `events-up`. Spec says `docker-up`-shaped / `docker-build`-shaped (`...design.md:106-108`). Pick one pattern and write it in the SUMMARY; Phase 13 will copy it.
- **MEDIUM** — Catch-all detection that is only “`%` at start of line” treats `%.o: %.c` as a help path. SC3 wants a catch-all `%:` so unknown targets print something. A suffix rule is not that. Require `%:` with no stem (optional empty prereqs), not any `%` pattern rule.
- **MEDIUM** — `WALK-BOUNDED-OK` only bounds runtime. The fixture has 60 visible `dN/s.sh` files (already ≥5) plus `ignored.sh` under `.hidden`. Pruning the dot-dir cannot change the finding. Add a 4-visible-scripts + scripts-only-under `.git`/`node_modules` fixture that must **not** flag.
- **LOW** — Alias-unchained and inherited `chain_incomplete` can both key `target: "validate"`. `build_remediation` then emits two `remediate` rows with `id: "validate"`. Distinct `issue` values keep `check` honest; `remediate` consumers that key on `id` will collide. Either qualify the remediate id (`validate:alias_unchained`) or document the collision.
- **LOW** — Exempting “the target named by `.DEFAULT_GOAL`” from the recipe cap is broader than the spec’s “help/fail-printing target”. A repo with `.DEFAULT_GOAL := test` and a 6-line `test` recipe would be exempt. Prefer literal `help` + catch-all body; treat DEFAULT_GOAL as exempt only when it names `help`.

### Suggestions

- Repair `ADVISORY-NONBLOCKING-OK` before execution; it is the SC5 non-blocking proof.
- Pin the two unpinned aliases in code and SUMMARY (`formatter` → `validate-format`, `code-smell-detector` → `validate-lint` is the short-name convention the pinned three already use).
- For docker, record the regex itself in the SUMMARY (e.g. `(?i)^docker(-[a-z0-9]+)*-up$` / `-build$`) so Phase 13 does not guess.
- Keep `check_validate_order`’s `chain_incomplete_found` argument load-bearing, as written; otherwise inverted-and-incomplete `validate` lists get noisy advisories.

### Risk Assessment

**MEDIUM.** Checks and paired-fixture discipline are sound; the shared `auto_apply` change is correctly additive. The Task 3 CLI assertion will fail without a fixture fix, and the docker/catch-all matching rules are under-specified for later phases.

---

## 10-03

### Summary

Docs-only close-out: write `SKILL.md`, one README row, `/skill-judge` as the code-review gate with committed evidence, `/naming-analyzer` as confirmation (no rename), and append-only corrections to ROADMAP SC1 and `REQ-rules-makefile`. The over-broad inheritance claim is a live fact: recovered `check_makefile_shape` emitted a fourth finding via `check_precommit_prepush_split`. Routing, report-only boundary, and “fix the document to match the code, never the reverse” are the right controls now that 10-01/10-02 will have made the skill real but uninstallable.

### Strengths

- `cc922e4:skills/ai-kit-agents-md-rules-checker/SKILL.md` resolves and actually contains `cache-update`, `(source:`, “research now”, “defer”, and Step D — plus `agent-md-refactor`, which this plan correctly forbids in the new document. Re-home, do not invent.
- Description-vs-body split matches how hosts route. Sibling `SKILL.md:2-3` is the AGENTS.md/CLAUDE.md surface; putting those tokens in this skill’s `description` would reopen the two-owner bug Phase 9 closed. Verify scopes the negative assertion to frontmatter and still lets the body name the neighbor.
- Output-shape check is against a live `check` invocation, not the plan’s prose. `auto_apply` off for advisory is the one fact a reader could otherwise get dangerously wrong (`remediation.py:55-63` today; 10-02 changes it).
- Judge gate is absolute (new skill, no baseline), evidence names `JUDGED_COMMIT`, and every judge fix must still pass Task 1’s verify chain. That blocks rubric-driven description broadening (T-10-12) and shape simplification (T-10-15).
- Naming: `ai-kit-project-rules-makefile` is locked by ROADMAP Phases 10–15. Recording a proposal without applying it is the only safe pipeline step.
- Amendment target is real. ROADMAP Phase 10 SC1 (`ROADMAP.md:326`) says “reproduces every check the old Makefile-checker performed” then lists three. `REQUIREMENTS.md:77` says “inherits the Makefile-specific logic dropped by REQ-rules-agents-prune”. Recovered checker’s last statements append the pre-push finding. Append-only, same wording, cite `9d672b9`, leave the traceability row alone (`REQUIREMENTS.md:138`) — matches the Phase 9 house style and AGENTS.md’s both-files rule.
- `cross_ai: false` is justified: `/skill-judge` and `/naming-analyzer` are host skills, not mechanical edits.

### Concerns

- **LOW** — Task 1 must copy alias map, docker shape, speed tiers, and the shellcheck CI-limit sentence from `10-02-SUMMARY.md`. If 10-02’s SUMMARY is thin, `SKILL.md` will freeze a guess. Make that SUMMARY a hard precondition, not just a read_first bullet.
- **LOW** — Recovered research-dispatch still talks about lettered steps and the refactor hand-off. Stripping those while keeping decision criteria is easy to get directionally right and still fail `agent-md-refactor not in t.lower()`. Re-run that assertion after the first draft, not only at the end.
- **LOW** — Judge fix-loop cap of 3 with escalate-rather-than-lower-the-bar is correct, but this plan cannot run the judge itself in a cross-AI setting (`cross_ai: false`). An executor without `skill-judge` installed must HALT as written; do not substitute a self-score.

### Suggestions

- Quote the three decision-criteria sentences in `10-03-SUMMARY.md` as the plan already requires; that is what later phases will copy.
- Restate the 180-vs-30 cache staleness discrepancy (`constraints.md:48` and design spec line 253 vs `stack_cache.py:22`) as an open question for Phase 11, so phase close does not drop it.
- Sibling structure is the right scaffold (`## Scope`, entrypoint candidate list, `## Run the check`, anti-patterns). Do not pull in Wrap mechanism / Steps A–C (`SKILL.md:51-63`).

### Risk Assessment

**LOW.** No Python, no gates, no installer write until the user re-runs setup. Residual risk is documentation drift from 10-02’s recorded decisions, and the judge loop optimizing the rubric at the expense of routing/output-shape constraints — both already mitigated in the verify chain.

---

## Cross-plan

Wave order is right: shared extraction (costly) → new checks + additive `auto_apply` (costly for the shared builder) → installable docs. 10-01’s “home but no caller” for `check_precommit_prepush_split` and 10-03’s SC1 amendment are the same fact, stated twice on purpose. Highest execution defect is 10-02’s `ADVISORY-NONBLOCKING-OK` fixture, not architecture. Phase 10 as a whole can meet REQ-rules-makefile if that criterion is fixed and the docker/catch-all matchers are written down rather than left to taste.

---

## Consensus Summary

Only one reviewer lane ran this cycle (OpenCode / `xai/grok-4.6`, reasoning=high), so there is
no cross-reviewer consensus to synthesize. The review is source-grounded: it carries no
`[reviewed-without-repo-access]` or `[reviewed-without-source-citations]` marker and cites
concrete `path:line` evidence throughout (`remediation.py:52-74`, `stack_cache.py:24-46`,
`rules.py:26-28`, `tools/setup.py:586`, `ROADMAP.md:326`, `REQUIREMENTS.md:77`, the `9d672b9`
recovery blob). Plan coverage is complete — all three plan ids (10-01, 10-02, 10-03) received
their own section.

An independent source-grounding pass confirmed the single HIGH finding against real project
source: `skills/_shared/ai_kit_rules_common/remediation.py:52-74` routes a makefile finding to
`remediate` **only** when `recommendation is not None`, otherwise to `blocked`. The recovered
checker (`git show 9d672b9:skills/ai-kit-project-rules-agents/ai_kit_project_rules_agents/makefile_checker.py:275-303`)
sets `recommendation` for a missing static target only when that target's name is also a
pre-commit hook id; the `ADVISORY-NONBLOCKING-OK` fixture in `10-02-PLAN.md:429` gives both of
its hook ids (`unittest`, `ruff`) a matching Makefile target, so neither produces a finding at
all, and every remaining missing-target/category finding resolves through the stack path with
`recommendation = None`. The advisory is therefore the only `remediate` entry and carries
`auto_apply is False`, so the criterion's final assertion
`any(e['auto_apply'] is True for e in r['remediate'])` cannot pass on that fixture. The finding
is real and not an artifact of reading plan text alone.

### Agreed Strengths

Single reviewer — no 2+ reviewer agreement available. Strengths it recorded, in priority order:

- The re-home-not-rewrite strategy is live-checkable: the `9d672b9` recovery blob, the
  `e56316e` prune parent, and the UNWIRED `tooling_payload.py` all resolve as the plans claim.
- The shared-package split (D-01/D-02/D-05) matches the sibling's existing import convention
  (`__init__.py:6-26`) and `build_remediation` already reads `report.get("makefile", [])`.
- The `auto_apply` change in `build_remediation` is correctly scoped as strictly additive, with
  `ADDITIVE-REMEDIATION-OK` and the sibling's full suite as the guards.
- 10-03's ROADMAP SC1 / `REQ-rules-makefile` amendment is factually warranted: the recovered
  `check_makefile_shape` really did emit a fourth finding via `check_precommit_prepush_split`,
  so "reproduces every check" overstates the three-check inheritance.
- Wave ordering (shared extraction → new checks → installable docs) is sound.

### Agreed Concerns

Single reviewer — no 2+ reviewer agreement available. See "Current HIGH Concerns" and the
per-plan Concerns sections above; the one blocking item is 10-02's `ADVISORY-NONBLOCKING-OK`
fixture.

### Divergent Views

None — only one reviewer lane ran.
