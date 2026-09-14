---
phase: 13
reviewers: [opencode]
reviewed_at: 2026-09-14T11:47:00Z
plans_reviewed: [13-01-PLAN.md, 13-02-PLAN.md, 13-03-PLAN.md, 13-04-PLAN.md]
models:
  opencode: "xai/grok-4.6 (reasoning=high)"
model_sources:
  opencode: "pinned"
---

# Cross-AI Plan Review — Phase 13 (Cycle 1)

<!-- gsd:plan-revision-conflicts:begin -->
## Plan-Revision Conflicts
(none)
<!-- gsd:plan-revision-conflicts:end -->

## OpenCode Review

Using gsd-review as the external reviewer: grounded each plan against the live tree, not plan prose (Phases 9-12 have landed; the docker skill does not exist yet).

## 13-01

**Summary.** A tight tracer that stands up the skill on the two filesystem/Makefile criteria (SC1, SC5) plus the load-bearing applicability gate. Interfaces it names are real and copyable from the arch sibling. Main gap: the plan overclaims that shared Makefile parsers degrade on unreadable files.

**Strengths**
- Gate design (clause iv, prefix not substring on `e2e-docker`) is the right load-bearing choice.
- Identifier discipline (`target` wins over `category`) matches the real `build_remediation` builder.
- Registration surfaces (Makefile:46,70; `.pre-commit-config.yaml`; `pyproject.toml`) match, so 13-02/13-03 can rely on the package glob.
- Leaving `SKILL.md` unwritten is the correct install-boundary control.

**Concerns**
- **MEDIUM — T-13-02 overclaims shared-parser degradation.** `parse_makefile_targets` (`makefile_parse.py:34-37`) returns `[]` only when the file doesn't exist; it opens with no `try`, so binary/non-UTF-8 content raises `UnicodeDecodeError`. Task 2 still requires an unreadable Makefile to return a list — the checker must wrap the read itself, not rely on the shared parser growing that contract.
- **LOW — `makefile_checker.py:463` is a weak citation** for the `target`-key ordering heuristic — mechanism is right, pin is coincidental.
- **LOW — CONTEXT still says Phases 9-12 have no plans** (`13-CONTEXT.md:21-25`) — stale status line; harmless since the executor trusts the live precondition, not the prose.

**Suggestions**
- In `docker_checker.check_docker_rules`, wrap Makefile reads in `try/except (OSError, UnicodeDecodeError)` and treat failure as "no targets" — do not wait for the shared parser to grow that contract.
- Keep the aggregator gate-then-extend so 13-02/13-03 only append inside the applicable branch.

**Risk Assessment.** **LOW.** Prerequisites are on disk, the sibling pattern is copyable, SC1/SC5 plus the gate are specified to the fixture. Residual risk is the unreadable-file wrap.

## 13-02

**Summary.** The phase's hard plan: an indentation-aware stdlib compose reader plus SC2/SC3. Correctly refuses a YAML library, generalizes the flat scan in `precommit_parse.iter_precommit_hook_blocks`, copies `criticality.py`'s drift-guard pattern. Gaps: flow-mapping forms are unspecified, and "declared values only" is a user-visible limit that must survive into 13-04.

**Strengths**
- Repointing gate clause (i) at `BASE_COMPOSE_FILENAMES` + `LOCAL_DEV_COMPOSE_FILENAMES` is the right one-list fix.
- Bounds are exclusive (`>` not `>=`) — an off-by-one fails in tests, not production. Numbers match ROADMAP SC2.
- Unreadable duration -> advisory naming the raw value, not silence, matches the `ast_only.py` advisory pattern.
- `depends_on`: all three bare forms, `service_started` treated as absent-condition default, per-entry not whole-block.
- No gate-file edits needed — 13-01's glob/regex already cover new modules.

**Concerns**
- **MEDIUM — flow-mapping bodies are outside D-D7.** `healthcheck: {interval: 30s, timeout: 10s}` and `depends_on: {db: {condition: service_healthy}}` yield an empty sub-block and produce no finding — a false-negative on valid Compose. SC2/SC3 fixtures are block-form only, so tests will not catch this.
- **MEDIUM — absent `interval` is Compose's 30s default and is not flagged (D-D9).** Correct vs ROADMAP, but must remain a stated 13-04 limit; a later executor who "fixes" this would silently expand SC2.
- **LOW — tab indentation** is a stated mis-attribution limit, not a crash — degradation class must assert "does not raise", not "parses correctly".
- **LOW — `docker-compose.yml` literal-ban check in `docker_checker.py`** greps comment-stripped source; a docstring example of that filename could fail the criterion even if the gate is correctly repointed. Interpolate names from the tuples instead.

**Suggestions**
- State in the module docstring (and 13-04 SKILL.md) that same-line flow-mapping bodies are unread, not conforming.
- Do not add a fourth bounds key or flag absent healthcheck keys.
- Drive duration/bounds tests from the module-level table so they cannot drift from timeout 2.0 / start_period 10.0 / interval 5.0.

**Risk Assessment.** **MEDIUM.** Parser attribution is the defect D-01 exists to prevent, and fixtures/mutations target it. Residual risk is silent false-negatives on flow-mapping compose.

## 13-03

**Summary.** D-04's expansion (bind-mount + override is not enough; the override must be a stack-appropriate dev server) with a third advisory outcome so a stale marker table never asserts "no hot reload". Catalog extension belongs beside `BASELINE_STACKS`, not in it. Highest remaining traps: longest-match ties, source-literal greps vs recommendation text, and mixed unreadable-volume + missing-override.

**Strengths**
- Three outcomes, five named `reason`s, advisory voice copied from the established pattern. Collapsing outcome 3 into 2 would violate the project's honesty rule.
- Keeping `HOT_RELOAD_TOOLS` out of `TAXONOMY_CATEGORIES`/`TOOL_CATEGORY_INDEX` is load-bearing — feeding a dev-server marker into the index would teach the precommit classifier that a dev server is a linter.
- Token-boundary matching (`--reload` will not match inside `--reload-dir`) is an already-paid-for lesson in this family.
- Local-dev scope via `discover_local_dev_compose_files` only — evaluating base compose would flag production services for not hot-reloading (inverts D-03).

**Concerns**
- **MEDIUM — longest-match tie is unspecified.** Both `nodemon` and `--watch` could match at equal length in some fixtures, and scan order could return the wrong one. Needs an explicit "longest match, then earlier position in that stack's tuple" tiebreak rule.
- **MEDIUM — advisory recommendation text vs source-literal greps.** The verify check greps `hot_reload.py` for marker names in comment-stripped source; hardcoded example marker literals in a docstring would fail the criterion even with correct behavior — join markers from `HOT_RELOAD_TOOLS` at runtime instead.
- **MEDIUM — mixed unreadable-volume + missing-override state is unspecified.** Outcome 3 requires both clauses to hold; an unreadable volume is a third bind-mount state that could wrongly emit a confident "no bind mount" or "no override" finding. Pin: an unreadable volume must never contribute to a confident outcome-2 finding.
- **LOW — an AST-only detection check for `detect_stacks(...)` calls could miss a qualified `stack_detect.detect_stacks(...)` import form** — import like the arch sibling does.
- **LOW — CONTEXT Integration Points still says D-05 "adds a new category"** — 13-03 correctly does not; a reader following stale CONTEXT prose instead of the decision text could corrupt the classifier.

**Suggestions**
- Resolve ties by longest marker, then earlier position in that stack's tuple.
- Build recommendation marker lists at runtime from `HOT_RELOAD_TOOLS` — no marker literals hardcoded in `hot_reload.py`.
- Evaluation order: script-prefix -> `no_stack_detected`/`stack_without_baseline` -> `resolve_hot_reload`; do not fold empty stacks into `command_not_matched`.

**Risk Assessment.** **MEDIUM.** The three-outcome split is the whole point of D-04 and is well-fixtured. Residual risk is catalog/taxonomy contamination and the longest-match/source-literal traps.

## 13-04

**Summary.** Correct last plan: the skill becomes installable only here. Writing SKILL.md from committed code + the three SUMMARYs, not from this plan's table, is the right authority order. The six limits are the real deliverable; the skill-judge loop's realistic failure mode is softening them. Do not stop at the two named CONTEXT corrections — CONTEXT has other stale lines.

**Strengths**
- Six limits map cleanly to earlier decisions (root gate, text parser + tabs, declared-values-only healthcheck, repo-wide stacks, staleable markers, no-local-dev-file-no-finding).
- No Python edits in this plan — a judge finding that needs a code change is reported, not implemented, so three prior plans' verified behavior never moves without their own test suites.
- README: one added row, zero removed, matching the sibling placement template.
- No-baseline rule with a recorded history search avoids a fake comparative bar; name-freeze is confirm-only.

**Concerns**
- **MEDIUM — CONTEXT corrections are incomplete vs live drift.** The two specified corrections are right, but other stale lines remain unaddressed (a stale Phases-9-12-have-no-plans status line, a stale helper-function citation, and the stale "D-05 adds a category" line 13-03 itself forbids). Phase 14 will read this file.
- **MEDIUM — the six stated limits do not yet include 13-02's flow-mapping unreadability gap.** If 13-02 ships that gap as a real limitation, SKILL.md must state it as a seventh limit, or it claims more coverage than the parser actually has.
- **LOW — limit-keyword checks in the shape verifier are greppable** (root/tab/declared/stale/etc.) — a softened clause could still pass; the verbatim-quote backstop in the SUMMARY is the real control and must not be replaced with a paraphrase.
- **LOW — an append-only history check anchored at a fixed offset (e.g. `HEAD~3`) is fragile** on shallow/reordered history — use a pinned-commit-range, added-lines-only diff instead.

**Suggestions**
- Quote all six (soon seven) limits as standalone sentences in SKILL.md before the judge runs, so iteration 1 does not start from buried clauses.
- Do a full stale-line sweep of 13-CONTEXT.md, not just the two named corrections — record any additional dated corrections found.
- If 13-02 ships the flow-mapping gap, add it as an explicit seventh limit.

**Risk Assessment.** **LOW** for code (this plan owns none). **MEDIUM** for shipped claims — installability plus a concision-optimizing judge loop is the real risk surface.

---

## Cross-plan

Wave order 13-01 -> 13-02 -> 13-03 -> 13-04 matches the dependency graph. 13-01's glob registration is what lets 13-02/13-03 add modules without touching gate files. Applicability gate + one filename list + local-dev-only hot-reload scope compose correctly: a non-Docker repo stays silent; a base-only compose repo gets family/runbook/healthcheck/depends_on but not hot-reload; override files get SC4.

Shared-package edits stay additive (`STRUCTURAL_KINDS` append, new `yaml_text.py`, `tool_catalog.py` section appended after the existing baseline). That matches "four siblings still import."

**Does not achieve the phase if:** the 13-01 gate walks the tree; 13-02 attributes nested blocks with a flat scan; 13-03 treats bind-mount + any override as conforming; 13-04 drops declared-values-only or the stale-baseline advisory. Each of those has a named non-vacuity mutation — execute those mutations, do not skip them.

**Overall risk: MEDIUM.** Plans are unusually well grounded against this tree (Phase 12 is actually present; docker skill is actually absent; the referenced interfaces all check out). Remaining risk is executor traps (unreadable-file wrap, flow-mapping silence, longest-match ties, source-literal greps) and honesty-about-limits surviving the judge — not missing success criteria.

## Current HIGH Concerns

(none)

## Current Actionable Non-HIGH Concerns

1. **MEDIUM (13-01)** — Task 2's checker must wrap Makefile reads in `try/except (OSError, UnicodeDecodeError)` itself rather than relying on `parse_makefile_targets` to degrade on unreadable/non-UTF-8 files.
2. **MEDIUM (13-02)** — Flow-mapping compose bodies (`healthcheck: {...}`, `depends_on: {...}`) are unhandled by the block-indent parser and must be explicitly documented as a stated limit, not silently mis-parsed as "no finding".
3. **MEDIUM (13-02)** — Absent `interval` (Compose's 30s implicit default) must remain explicitly un-flagged and documented as a stated limit, not "fixed" into a stricter check that would silently expand SC2.
4. **MEDIUM (13-03)** — Longest-marker-match ties (e.g. `nodemon` vs `--watch` at equal length) need an explicit tiebreak rule: longest match, then earliest position in that stack's tuple.
5. **MEDIUM (13-03)** — Recommendation/advisory text must build marker lists at runtime from `HOT_RELOAD_TOOLS`, never hardcode marker literals in `hot_reload.py` source, since the verify check greps comment-stripped source for exactly those markers.
6. **MEDIUM (13-03)** — An unreadable bind-mount volume must never contribute to a confident outcome-2 ("no bind mount"/"no override") finding — pin it to the advisory outcome-3 path explicitly.
7. **MEDIUM (13-04)** — CONTEXT.md correction task must do a full stale-line sweep (at minimum: the Phases-9-12-status line, the precommit helper citation, and the D-05-adds-a-category line), not stop at the two originally-named corrections.
8. **MEDIUM (13-04)** — The six stated SKILL.md limits must be reconciled with whatever 13-02 actually ships for flow-mapping unreadability — add a seventh limit if that gap survives into the shipped parser.
9. **LOW (13-01)** — `makefile_checker.py:463`'s `target` key citation is coincidental, not load-bearing — re-read/re-verify the actual ordering-heuristic anchor before relying on it.
10. **LOW (13-01)** — 13-CONTEXT.md's "Phases 9-12 have no plans" status line is stale; harmless since the executor trusts the live precondition, but worth noting.
11. **LOW (13-02)** — Tab-indentation degradation must be tested as "does not raise", not "parses correctly".
12. **LOW (13-02)** — The `docker-compose.yml` literal-ban verify check should interpolate filenames from the shared tuples rather than grep for the literal string, to avoid failing on a correct docstring example.
13. **LOW (13-03)** — An AST-only call-detection check for `detect_stacks(...)` should also match a qualified `stack_detect.detect_stacks(...)` import form.
14. **LOW (13-03)** — 13-CONTEXT.md's Integration Points section still says D-05 "adds a new category" — 13-03 correctly does not; flag for correction alongside the other stale CONTEXT lines.
15. **LOW (13-04)** — Limit-keyword shape checks are greppable and could pass a softened clause — the verbatim-quote SUMMARY backstop is the real control.
16. **LOW (13-04)** — Prefer a pinned-commit-range, added-lines-only diff for the append-only CONTEXT check over a fixed `HEAD~N` offset, which is fragile on shallow/reordered history.

## Consensus Summary

Single-reviewer cycle (opencode only) — no cross-reviewer consensus to synthesize. All findings above are from the single opencode (xai/grok-4.6, reasoning=high) pass, grounded against live source rather than plan prose.

### Agreed Strengths
N/A — single reviewer.

### Agreed Concerns
N/A — single reviewer.

### Divergent Views
N/A — single reviewer.

CYCLE_SUMMARY: current_high=0 current_actionable=16
