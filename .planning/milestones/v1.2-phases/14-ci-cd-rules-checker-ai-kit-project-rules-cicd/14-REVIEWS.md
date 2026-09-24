---
phase: 14
reviewers: [opencode]
reviewed_at: 2026-09-14T15:55:00Z
plans_reviewed: [14-01-PLAN.md, 14-02-PLAN.md, 14-03-PLAN.md, 14-04-PLAN.md]
models:
  opencode: "xai/grok-4.6 (reasoning=high)"
model_sources:
  opencode: "pinned"
---

# Cross-AI Plan Review — Phase 14 (Cycle 1)

<!-- gsd:plan-revision-conflicts:begin -->
## Plan-Revision Conflicts
(none)
<!-- gsd:plan-revision-conflicts:end -->

## OpenCode Review

Verified against the live tree at `0b4a504` (plans grounded at `672aab4`). Catalog facts, `STRUCTURAL_KINDS`, sibling CLI/gate patterns, and `precommit_parse`/`makefile_parse` degradation all checked on disk.

## 14-01

**Summary.** A strong tracer: it stands up the skill end-to-end on GitLab `script:` plus the Makefile reuse surface, with additive shared-package growth and a match rule that is actually pinned to live catalog behavior. Two issues will bite the executor: the GitLab `include:` blind spot is not treated as a stated limit, and D-C9's drift-guard "same pattern" wording fights D-C6's richer prefix table.

**Strengths.** Catalog facts (ruff -> linting/formatting, pytest/tsc -> None) are live-true. `STRUCTURAL_KINDS`/`build_remediation` precedence correctly read. Docker sibling correctly cloned. Makefile parsers still raise on binary UTF-8 — D-C10's wrap is correctly placed. `yaml_text.py`'s drift-guard pattern correctly reused. Applicability/identity/match-rule design is the right false-positive profile. Registration counts all verified on disk.

**Concerns**
- **HIGH — GitLab `include:` is not followed and not named as a limit.** Live `.gitlab-ci.yml:15-16` is `include: - template: Security/Secret-Detection.gitlab-ci.yml`. The reserved-key handling skips `include:` as a job and never opens the included file. A repo using `include: local: ci/lint.yml` with `ruff check .` inside would be a silent pass. 14-04's ten limits inherit this hole from 14-01's reader docstring, which lists tabs/anchors/`!reference`/heredocs but not include/extends.
- **MEDIUM — `NO-CACHE-SURFACE-OK` vs GitLab's reserved key `cache`.** The reserved-key tuple in `ci_parse.py` will literally contain the word "cache" unless encoded as a computed literal — already flagged in-plan but still an easy executor trap.
- **MEDIUM — D-C9 drift-guard equality vs D-C6's richer prefix table.** Pinning "the shared pattern literal" equal to `_RUNNER_PREFIX_RE` either shrinks `command_text` (breaking `npx`/`pnpm exec` tests) or the guard isn't actually equality. Needs explicit clarification that the module can hold the old regex plus extra strippers.
- **MEDIUM — D-C3(c) + D-C4 name-equality admits every 2-real-line non-delegate target.** A 2-line `ruff:` target that both checks and formats could become a linter reuse source via `AMBIGUOUS_TOOL_DEFAULTS`, under-tested relative to the 1-line negative fixtures.
- **LOW — "those shapes exist in ai-kit's own Makefile" is factually false** (no `clean` target; `validate:` is prerequisites-only). Fixtures still required regardless.
- **LOW — `.gitlab-ci.yml` is 16 lines, not 17** (minor citation error; the substantive claim is correct).

**Risk Assessment.** **MEDIUM.** The include: silence and the D-C9 pattern-pin are the two ways this tracer ships a checker that looks green and misses or mis-parses real CI.

## 14-02

**Summary.** The right second slice: GitHub `steps:` is a sequence of mappings, which `compose_parse.block_sequence` explicitly will not read, and the pre-commit surface correctly reuses `parse_precommit_hooks`. Main risks are discovery/aggregator double-append and unquoted-vs-quoted hook `entry:` values.

**Strengths.** D-C14/D-C15/D-C16/D-C17 all consistent with live interfaces and the family's convergence rules. `uses:` never fetched correctly controlled. Quote-stripping precedent correctly identified as missing for `entry:`.

**Concerns**
- **MEDIUM — discovery "extend" vs aggregator "append" can double-scan** GitHub workflow files if both paths independently visit them — needs an explicit single-list-single-loop statement.
- **MEDIUM — hook `entry:` is not quote-stripped**, unlike the id. `entry: "ruff check"` would feed the match rule a quoted string that fixtures (using bare `ruff check`) wouldn't catch.
- **MEDIUM — GitLab tests must stay green under the step-reader mutation** — the mapping-item iterator must be strictly GitHub-only, not shared incorrectly with `_own_level_lines`.
- **LOW — `defaults.run` implicit prefix contribution is unstated** as a limit (reusable-workflow and `run`+`working-directory` are stated; this one isn't).

**Risk Assessment.** **MEDIUM.** The capability split is correct; double-discovery and quoted entries are the realistic wrong-green paths.

## 14-03

**Summary.** This is the plan that makes SC3 true, and most of it is well-constrained. One behavior fixture is unsatisfiable under 14-01's match rule and will fail Task 2 until rewritten.

**Strengths.** Plugin-table catalog facts (spotless/checkstyle/PMD/SpotBugs -> real categories; ktlint/detekt/dependency-check -> None) all live-true. Lockfile-runner ordering, plugin-id-as-prerequisite, lifecycle exclusion, and the exception-narrowing all correctly designed.

**Concerns**
- **HIGH — `tasks.register("jscpdReport")` covering CI `jscpd .` contradicts D-C5.** D-C5 matches exact keys or same-first-token-same-category with no substring/suffix stripping — `jscpdReport` cannot match `jscpd` under that rule. Task 2's first behavior case is unsatisfiable as written; needs either the task name to literally be the tool name, or a documented identity-mapping mechanism like the plugin table already provides for Route 2.
- **MEDIUM — D-C19b (plugin-table admission) must not leak into the other three gate routes.** A plugin-table membership check without a Gradle-only flag would wrongly admit Makefile/hook identities that happen to equal a plugin-table tool name. Re-running the other three surfaces' own OK-checks after this change is the mitigation.
- **MEDIUM — Route 1 declared-task identity is a name, not a command key**, which may be fine in general but makes the SC3 pair fragile if not seeded with task names that are already catalog keys.
- **LOW — plugin-id mentioned only in a comment still admits the identity** — stated as a known limit, correctly deferred to SKILL.md.

**Risk Assessment.** **MEDIUM (HIGH until the `jscpdReport` fixture is rewritten).** The rest of the surface design is sound and SC3-complete once Route 1 identity and D-C5 agree.

## 14-04

**Summary.** Correct last plan: installability, sibling-shaped SKILL.md, skill-judge gate, naming confirmation, append-only CONTEXT sweep. It will document whatever 14-01–03 actually shipped, so the include: hole and any 14-03 identity divergence become user-facing lies if not fixed upstream first.

**Strengths.** D-C22 (code wins over SUMMARY) correct. Two-axis limits survival with hyphenated distinctive tokens correctly designed against judge-loop concision pressure. No-baseline claim correctly structured. D-C24 name-freeze correctly justified against 4 separate downstream references. Append-only CONTEXT sweep floor of 4 matches live stale lines.

**Concerns**
- **HIGH if 14-01 is unfixed — the limits set is missing GitLab `include:`.** Same root cause as 14-01's HIGH, not an independent defect — but the consequence lands here: a zero-finding run against this repo's own composed CI would read as "CI is clean" when it silently never opened the included file.
- **MEDIUM — `autonomous: true` vs the naming-analyzer SURFACE-and-STOP rule.** An autonomous executor could be tempted to record "declined" and continue past a proposed rename rather than actually halting — Task 3 must genuinely stop if a rename is proposed.
- **MEDIUM — skill-judge concision vs ten limits.** This is denser than Phase 13's 103/120 pass (four surfaces, two platforms, plugin table); a judge pass wanting shorter prose must not be satisfied by dropping a limit — stop and report instead.
- **LOW — description-length routing-quality proxy is not a substitute for the makefile/precommit disambiguation clause**, which must survive any judge-driven shortening.

**Risk Assessment.** **MEDIUM as a docs plan; HIGH as a user-facing honesty plan** if the upstream include:/identity defects are papered over here rather than fixed at the source.

---

## Cross-plan

Plans 14-01->04 are a coherent tracer-then-platforms-then-surfaces-then-docs sequence, matching Phase 13's successful split. Phase 14 SC1-SC4 are covered IF 14-03's Route 1 fixture is rewritten to obey D-C5 AND GitLab `include:` becomes a stated limit (or is handled). Without both fixes, SC1 is true on synthetic root-file fixtures and false on the include-composed CI this repo itself actually uses.

**Overall risk: MEDIUM.** Do not start 14-01 execution until D-C9's drift-guard contract is explicit; do not start 14-03 Task 2 until `jscpdReport`/`jscpd` is replaced with a D-C5-legal pair.

## Current HIGH Concerns

1. **HIGH (14-01, inherited by 14-04)** — GitLab `include:` (both `local:` and `template:` forms) is never followed; the reader treats it as a skipped reserved key rather than opening the included file. This is a real, live blind spot: ai-kit's own `.gitlab-ci.yml` uses `include: - template: ...`, and a repo using `include: local: ci/lint.yml` with a duplicated tool invocation inside would produce a silent false-clean result. Must be either handled (open and scan included local files) or explicitly documented as a stated limit surfaced all the way through to SKILL.md.
2. **HIGH (14-03)** — The plan's Task 2 behavior fixture pairs `tasks.register("jscpdReport")` (Gradle task) with CI `jscpd .`, but D-C5's match rule (exact keys or same-first-token-same-catalog-category, no substring/suffix stripping) cannot match `jscpdReport` to `jscpd`. This fixture is unsatisfiable as written. Fix by either using a task name that literally equals the tool name (e.g. `tasks.register("jscpd")`), or introducing an explicit, documented identity-mapping mechanism analogous to the plugin table already used for Route 2.

## Current Actionable Non-HIGH Concerns

1. **MEDIUM (14-01)** — The GitLab reserved-key tuple must encode the literal word "cache" as a computed/concatenated literal, not a bare string, to stay honest under the skill's own `NO-CACHE-SURFACE-OK` self-scan.
2. **MEDIUM (14-01)** — D-C9's drift-guard "same pattern" wording must be clarified: does it require byte-identical equality to `_RUNNER_PREFIX_RE`, or can `command_text` hold that regex plus additional stripping helpers for `npx`/`pnpm exec`/etc.? As written it's ambiguous and risks either breaking real-world prefix handling or making the guard vacuous.
3. **MEDIUM (14-01)** — D-C3(c) + D-C4's name-equality clause could admit any 2-real-line non-delegate Makefile target as a reuse source via `AMBIGUOUS_TOOL_DEFAULTS`; needs tighter gating (e.g. require `resolve_tool_category` or `OUT_OF_TAXONOMY` to actually admit the name) and more negative-fixture coverage.
4. **LOW (14-01)** — The plan's claim that certain Makefile target shapes "exist in ai-kit's own Makefile" is factually false (no `clean` target; `validate:` has an empty prerequisites-only recipe) — synthetic fixtures are still required regardless, but the citation should be corrected.
5. **MEDIUM (14-02)** — Discovery's "extend" and the aggregator's "append" must be reconciled into a single file list visited once per loop, or GitHub workflow files risk being double-scanned and producing duplicate findings.
6. **MEDIUM (14-02)** — Pre-commit hook `entry:` values are not quote-stripped before being fed into the match rule (unlike the hook id, which is), so a real `entry: "ruff check"` would be missed by fixtures using bare `ruff check`. Strip via the shared `yaml_text.strip_yaml_quotes` helper and add a quoted-entry fixture.
7. **LOW (14-02)** — `defaults.run`'s implicit command-prefix contribution (at workflow or job level) should be explicitly stated as an ignored/degraded case in the reader's docstring, alongside the already-stated reusable-workflow and `run`+`working-directory` limits.
8. **MEDIUM (14-03)** — D-C19b's plugin-table admission check must carry an explicit Gradle-only flag or scoping mechanism so it cannot leak into and wrongly admit identities on the other three (Makefile/pre-commit/package.json) surfaces — re-run those three surfaces' own acceptance checks after this change lands.
9. **LOW (14-03)** — A plugin id mentioned only inside a comment (not real usage) still satisfies the containment-prerequisite check — already correctly flagged as a stated, deferred limit; keep it documented through to SKILL.md.
10. **MEDIUM (14-04)** — Task 3's naming-analyzer step must genuinely SURFACE-and-STOP if a rename is proposed, not record "declined" and silently continue — this must be enforced as an actual halt behavior, not just a documented intention, since the plan is marked `autonomous: true`.
11. **MEDIUM (14-04)** — If the skill-judge fix loop pushes toward shorter SKILL.md prose to satisfy a length/concision-flavored finding, no limit statement may be dropped to comply — stop and report the tension instead, per D-C26.
12. **LOW (14-04)** — The description-length routing-quality proxy in the shape-verification check is not a substitute for the makefile/precommit disambiguation clause, which must survive any judge-driven shortening intact.

## Consensus Summary

Single-reviewer cycle (opencode only) — no cross-reviewer consensus to synthesize. All findings above are from the single opencode (xai/grok-4.6, reasoning=high) pass, grounded against live source rather than plan prose.

### Agreed Strengths
N/A — single reviewer.

### Agreed Concerns
N/A — single reviewer.

### Divergent Views
N/A — single reviewer.

CYCLE_SUMMARY: current_high=2 current_actionable=12

<!-- gsd:cycle-2:begin -->
## Cross-AI Plan Review — Phase 14 (Cycle 2)

**Reviewer-lane route (documented for continuity):** the project's configured default reviewer (`opencode`, pinned to `xai/grok-4.6`) failed immediately with `APIError 403 personal-team-blocked:spending-limit` — confirmed via a direct `opencode run --model xai/grok-4.6` sanity check as a genuine account-level billing block, not a transient host issue. Fallback to `codex` also failed genuinely: stored OAuth refresh token already consumed server-side (`refresh_token_reused`, 401), requiring an interactive `codex logout && codex login` no agent can perform. `gemini` CLI's install was separately found broken (`MODULE_NOT_FOUND`). The **`claude` CLI lane succeeded** (separate auth path, independent of the xai/OpenAI account issues) and produced this cycle's review. Both failures are recorded in persistent memory (`project_opencode_xai_billing_block.md`) for future sessions. This outage is logged as a `human_verification` item for the end-of-run report: opencode needs account credits/subscription, codex needs interactive re-login.

reviewer: claude (separate Claude Code CLI session)
reviewed_at: 2026-09-14T~20:30Z (approx, background dispatch)

### Cross-Plan Assessment

**Overall Risk: LOW.** Every one of cycle-1's fixes was independently re-verified against live source and found genuinely correct (not merely plausible) — including D-C28's GitLab `include:` disclosure, D-C9's byte-identical regex pin to `_RUNNER_PREFIX_RE`, D-C3(b2)/D-C4's Route-3 tightening, D-C15's quote-stripping fix (grounded in a real verified bug: `_ENTRY_LINE_RE`'s match was never passed through `_strip_yaml_quotes`, unlike the id), D-C19b's gate-leak parameter design (grounded in real unresolvable catalog names: `ktlint`/`detekt`/`dependency-check` all resolve to `None`), and all of 14-04's sibling-pattern citations (verified byte-accurate line counts: docker=251, arch=181, makefile=231, precommit=245).

### New Findings (minor, all self-limiting)

1. **MEDIUM (14-01)** — `NO-CACHE-SURFACE-OK`'s AST rewrite has an unexamined false-positive path: honest docstring prose naming "cache" could trip the self-scan check, costing an iteration but not correctness.
2. **LOW (14-01)** — D-C3 clause (b2)'s "compute the SAME key" is ambiguous between literal-string and D-C5-widened equality — a latent spec gap not exercised by any required fixture.
3. **LOW (14-02)** — The `entry:` regex captures greedily to end-of-line, so a trailing YAML `# comment` isn't stripped — narrow, not blocking.
4. **LOW (14-03)** — The plugin table's text-containment evidence check is an honestly-disclosed limit, not a defect.
5. **LOW (14-03)** — D-C18b's lockfile-runner precedence is unverifiable against this repo (no `package.json` here) but is not a flaw in the plan.
6. **LOW-MEDIUM (14-04)** — Task 3's `/naming-analyzer` step lacks the explicit reachability precondition Task 2 gives `/skill-judge` — asymmetric gating, easy one-line fix.
7. **LOW (14-04)** — The concision-tension rule (D-C26) creates an anticipated-and-correctly-handled risk that this plan finishes "incomplete by design" — a scheduling note, not a plan-quality defect.

Reviewer's own verdict, verbatim: "Neither rises above LOW-MEDIUM severity, and both are easy one-line fixes if the team wants to close them before execution. The plans are ready to execute as converged."

### Consensus Summary

Single-reviewer cycle (claude lane only, after opencode/codex both failed for genuine external account reasons — see route notes above). All cycle-1 fixes independently re-verified as correct; no HIGH findings surfaced; remaining findings are minor and self-limiting per the reviewer's own explicit "ready to execute as converged" assessment.

**Orchestrator ruling:** given 0 HIGH findings, all findings independently described as minor/self-limiting/non-blocking, and the reviewer's own explicit convergence verdict, declaring convergence now rather than spending a third cycle — consistent with established precedent (Phases 10-13) of not spending an extra cycle on trivial findings. Item 6 (asymmetric reachability gating for `/naming-analyzer`) is genuinely a one-line fix; will be applied directly by the executor/orchestrator during code review of 14-04 if not already covered by the plan text, rather than triggering a further replan cycle.

CYCLE_SUMMARY: current_high=0 current_actionable=7
<!-- gsd:cycle-2:end -->
