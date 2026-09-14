---
phase: 13
reviewers: [opencode]
reviewed_at: 2026-09-14T16:47:16Z
plans_reviewed: [13-01-PLAN.md, 13-02-PLAN.md, 13-03-PLAN.md, 13-04-PLAN.md]
models:
  opencode: "xai/grok-4.6 (reasoning=high)"
model_sources:
  opencode: "pinned"
---

# Cross-AI Plan Review — Phase 13

<!-- gsd:plan-revision-conflicts:begin -->
## Plan-Revision Conflicts
(none)
<!-- gsd:plan-revision-conflicts:end -->

## OpenCode Review

I'll review the four Phase 13 plans against the live tree, not the plan text. Loading the review skill and checking the referenced code first.
Using gsd-review as the external reviewer: I'll ground each plan against the live tree, not the plan prose. Checking the load-bearing interfaces next.
Checking gate-registration surfaces, arch CLI patterns, catalog structure, and the unreadable-file path the plans rely on.
Using gsd-review as the external reviewer. Claims below are grounded against the live tree (Phases 9–12 have landed; the docker skill does not exist yet).

## 13-01

### Summary
A tight tracer that stands up the skill on the two filesystem/Makefile criteria (SC1, SC5) plus the load-bearing applicability gate. Interfaces it names are real: `STRUCTURAL_KINDS` is still `("makefile", "precommit", "arch")` at `remediation.py:22`, identifier precedence is `finding.get("target", finding.get("category"))` at `:88`, and the arch sibling's `__init__.py` / argparse-free `cli.py` / 7-line entrypoint are copyable as written. The gate's two negative edges match this repo (`e2e-docker` at `Makefile:127`, nested `tests/e2e/docker/Dockerfile`). Main gap: the plan overclaims that shared Makefile parsers degrade on unreadable files.

### Strengths
- Gate design is the right load-bearing choice. Clause (iv) is a prefix on the D-D1-normalized name, not a substring — `e2e-docker` would trip a substring rule and this repo would false-positive on first run.
- Identifier discipline is pinned to the actual builder, not folklore. `build_remediation` at `remediation.py:88-94` really does let `target` win; arch's aggregator docstring (`arch_checker.py:18-24`) already documents the same trap from the other side.
- Family vs Makefile-sibling shape regex is a real boundary. `_DOCKER_UP_SHAPE_RE` at `makefile_checker.py:82` is `^docker(?:-[a-z0-9]+)*-up$` — a different question. Not importing it is correct.
- Registration surfaces match: `Makefile:46` unittest list, `Makefile:70` py_compile glob, `.pre-commit-config.yaml:21,50,55`, `pyproject.toml:88,94`. 13-02/13-03 can rely on the package glob.
- Leaving `SKILL.md` unwritten is the right install-boundary control (`README.md:51`: skills need `SKILL.md`).
- Normalization copies `normalize_target_name` at `arch_checker.py:62-64` (casefold, `_` → `-`).

### Concerns
- **MEDIUM — T-13-02 overclaims shared-parser degradation.** `parse_makefile_targets` (`makefile_parse.py:34-37`) returns `[]` only when `not os.path.isfile`; it then does `open(..., encoding="utf-8")` with no `try`. Binary/non-UTF-8 content raises `UnicodeDecodeError`. Task 2 still requires an unreadable Makefile to return a list. The checker must wrap the read; "rely on the shared parsers" will not discharge that. TDD will catch it if Task 2 is not weakened.
- **LOW — `makefile_checker.py:463` is a weak citation.** That line is `"target": "validate"` on the ordering heuristic, one of eleven `target` keys. Mechanism is right; pin is coincidental. Re-read as the plan already says.
- **LOW — CONTEXT still says Phases 9–12 have no plans** (`13-CONTEXT.md:21-25`). The precondition (`STRUCTURAL_KINDS` length 3, arch `SKILL.md` present) is the live gate; the CONTEXT status line is stale. Harmless if the executor trusts the precondition.

### Suggestions
- In `docker_checker.check_docker_rules`, wrap Makefile reads in `try/except (OSError, UnicodeDecodeError)` and treat failure as "no targets" — do not wait for the shared parser to grow that contract.
- Keep the aggregator as gate-then-extend so 13-02/13-03 only append inside the applicable branch.

### Risk Assessment
**LOW.** Prerequisites are on disk, the sibling pattern is copyable, and SC1/SC5 plus the gate are specified to the fixture. Residual risk is the unreadable-file wrap, which Task 2's degradation class should force.

## 13-02

### Summary
This is the phase's hard plan: an indentation-aware stdlib compose reader plus SC2/SC3. It correctly refuses a YAML library (D-01/D-02), generalizes the flat scan in `precommit_parse.iter_precommit_hook_blocks` (`precommit_parse.py:40-55`, next-`- id:` boundary, no indent tracking), and copies `criticality.py:9-15`'s deliberate non-repoint + drift-guard pattern for `strip_yaml_quotes`. Nesting-attribution fixtures with two differently-valued services actually test D-01. Gaps: flow-mapping forms are unspecified, and "declared values only" is a user-visible limit that must survive into 13-04.

### Strengths
- Repointing gate clause (i) at `BASE_COMPOSE_FILENAMES` + `LOCAL_DEV_COMPOSE_FILENAMES` is the right one-list fix. `ONE-FILENAME-LIST-OK` asserting both the import *and* the absence of leftover literals is the check that catches the silent compile-and-pass failure.
- Bounds are exclusive (`>` not `>=`); the 5s vs 5.001s pair makes an off-by-one fail in tests, not in production. Numbers match ROADMAP SC2.
- Unreadable duration → advisory naming the raw value, not `0`/silence, matches `PROJECT.md` and copies `_not_verifiable_finding` at `ast_only.py:341-355` (`advisory: True`, `reason`, "could not verify").
- `depends_on`: all three bare forms, `service_started` ≡ absent condition (Compose default), `service_completed_successfully` advisory, per-entry not whole-block. `PER-ENTRY-OK` is the fixture that makes a whole-block search fail.
- `auto_apply = not finding.get("advisory", False)` at `remediation.py:98` already carries advisories; no builder change needed.
- No gate-file edits: 13-01's `ai_kit_project_rules_docker/*.py` glob (`Makefile:70`) and `skills/_shared/.*` regex already cover new modules.
- Findings prohibited from carrying `target` — same rule arch already follows.

### Concerns
- **MEDIUM — flow-mapping bodies are outside D-D7.** Block end is "from the line *after* the key until indent ≤ i". `healthcheck: {interval: 30s, timeout: 10s}` and `depends_on: {db: {condition: service_healthy}}` then yield an empty sub-block and produce no finding — a false-negative on valid Compose. Flow *sequences* (`[db, cache]`) are specified; flow *mappings* are not. SC2/SC3 fixtures are block-form, so tests will not catch this.
- **MEDIUM — absent `interval` is Compose's 30s default and is not flagged (D-D9).** Correct vs ROADMAP, easy to "fix" as a bug. Must remain a stated 13-04 limit; a later executor who flags missing keys would expand SC2.
- **LOW — tab indentation** is a stated mis-attribution limit, not a crash. Degradation class must assert "does not raise", not "parses correctly".
- **LOW — `docker-compose.yml` literal ban in `docker_checker.py`.** `ONE-FILENAME-LIST-OK` greps comment-stripped source. A docstring example of that filename fails the criterion even if the gate is correctly repointed. Interpolate names from the tuples.

### Suggestions
- State in the module docstring (and 13-04 SKILL.md) that same-line flow-mapping `healthcheck:`/`depends_on:` bodies are unread, not conforming.
- Do not add a fourth bounds key or flag absent healthcheck keys.
- Drive duration/bounds tests from the module-level table so they cannot drift from `timeout` 2.0 / `start_period` 10.0 / `interval` 5.0.

### Risk Assessment
**MEDIUM.** Parser attribution is the defect D-01 exists to prevent, and the fixtures/mutations target it. Residual risk is silent false-negatives on flow-mapping compose, plus any "helpfulness" that flags undeclared healthcheck keys.

## 13-03

### Summary
This is D-04's expansion (bind-mount + override is not enough; the override must be a stack-appropriate dev server) with a third advisory outcome so a stale marker table never asserts "no hot reload". Catalog extension belongs in `tool_catalog.py` *beside* `BASELINE_STACKS`, not in it: `__all__` (`tool_catalog.py:566-577`) has no hot-reload names today; `_derive_tool_category_index` collision `ImportError` and `_validate_pairs_reachability` at `:552` must stay undisturbed. `detect_stacks` (`stack_detect.py:15-38`) returns exactly `{go, python, node, java, rust}` from root marker files — the key-set test that *derives* names from temp dirs is the right anti-drift control. Highest remaining traps: longest-match ties, `NO-LOCAL-COPIES-OK` vs recommendation text, and mixed unreadable-volume + missing-override.

### Strengths
- Three outcomes, five named `reason`s, advisory voice copied from `ast_only.py:341-355`. Collapsing outcome 3 into 2 would violate `PROJECT.md`; the `prodcmd` fixture (`node dist/server.js` + bind mount) is exactly the user case in `13-CONTEXT.md:166-172`.
- `HOT_RELOAD_TOOLS` kept out of `TAXONOMY_CATEGORIES` / `TOOL_CATEGORY_INDEX` is load-bearing. Feeding `vite` into the index would teach the precommit classifier that a dev server is a linter (`resolve_tool_category` at `tool_catalog.py:480-511`).
- Token-boundary matching in the spirit of `recipe_mentions_target` (`makefile_parse.py:128-143`, `(?<![-\w])...(?![-\w])`). `--reload` will not match inside `--reload-dir`; `air` will not match `airflow`. That is already a paid-for lesson in this family.
- Local-dev scope via `discover_local_dev_compose_files` only — evaluating base `docker-compose.yml` would flag production services for not hot-reloading (inverts D-03).
- `volumes_unreadable` vs "no bind mount" is the same honesty rule as unreadable durations.
- Bind-mount rule matches Compose: `src:/app` without `./` is a named volume, not a relative bind. D-D17's `.` / `..` / `/` / `~` prefixes are Compose's own rule.

### Concerns
- **MEDIUM — longest-match tie is unspecified.** `LONGEST-MATCH-OK` requires `nodemon --watch src` → `nodemon`. Both markers are length 7. `>=` while scanning later in the node tuple (`--watch` after `nodemon` in D-D16) would return `--watch` and fail the criterion. Need "longest, first in tuple on tie".
- **MEDIUM — `NO-LOCAL-COPIES-OK` vs D-D15 recommendation text.** Action says the advisory should name "the markers this skill knows". Verify greps `hot_reload.py` for `vite` / `nodemon` / `docker-compose.override` in comment-stripped source (docstrings count). Hardcoded examples fail; join markers from `HOT_RELOAD_TOOLS` at runtime.
- **MEDIUM — mixed unreadable volume + missing override is unspecified.** Outcome 3 requires clauses (i) and (ii) to hold; unreadable is a third bind-mount state. Interpolated volume and no `command:`/`entrypoint:` could emit confident "no bind mount" (wrong) or "no override" (partially right). Pin: unreadable volume never contributes to outcome 2.
- **LOW — `STACK-DETECT-ONCE-OK` only matches `detect_stacks(...)`** (`ast.Call` with `func.id`). `stack_detect.detect_stacks(...)` would fail the AST check. Import like `arch_checker.py:40`.
- **LOW — CONTEXT Integration Points (`13-CONTEXT.md:156`) still says D-05 "adds a new category".** 13-03 correctly does *not*. Anyone reading CONTEXT instead of D-D16 could merge into `BASELINE_STACKS` and trip the collision guard (loud) or corrupt the classifier (quiet).

### Suggestions
- Resolve ties by longest marker, then earlier position in that stack's tuple.
- Build recommendation marker lists with `", ".join(HOT_RELOAD_TOOLS[s] for s in stacks)` — no marker literals in `hot_reload.py`.
- Evaluation order: script-prefix → `no_stack_detected` / `stack_without_baseline` → `resolve_hot_reload`; do not fold empty stacks into `command_not_matched` (`resolve_hot_reload(..., set())` is `None` for both).
- Skip the `stack_without_baseline` test with a stated reason while `HOT_RELOAD_BASELINE_GAPS` is empty — do not let it pass vacuously.

### Risk Assessment
**MEDIUM.** The three-outcome split is the whole point of D-04 and is well-fixtured. Residual risk is catalog/taxonomy contamination (mitigated if Task 1's leaked-marker assertion is not weakened) and the longest-match / source-literal greps failing a correct implementation.

## 13-04

### Summary
Correct last plan: the skill becomes installable only here (`README.md:51`). Writing `SKILL.md` from committed code + the three SUMMARYs, not from this plan's table, is the right authority order. The six limits in D-D19 are the real deliverable; the skill-judge loop's realistic failure is softening them, and the verbatim-quote backstop in `13-04-SUMMARY.md` is the right defense. Naming freeze (D-D20) matches ROADMAP Phases 14–15 / Phase 15 SC1. The two CONTEXT corrections are the right facts (`detect_stacks` lives in `stack_detect.py:29`, not `stack_cache.py`; `tests/e2e/docker/Dockerfile` exists). Do not stop at those two — CONTEXT has other stale lines.

### Strengths
- Six limits map to earlier decisions: root gate (13-01 D-D4), text parser + tabs (13-02 D-D7), declared-values-only healthcheck (13-02 D-D9), repo-wide stacks (13-03 D-D16), staleable markers (13-03 D-D15), no local-dev file → no hot-reload finding (13-03 D-D13).
- No Python edits. A judge finding that needs a code change is reported, not implemented — otherwise three plans' verified behavior moves without their suites.
- `SKILL-SHAPE-OK` + `DOC-MATCHES-CODE-OK` + `TWO-SUBCOMMANDS-OK` (including a real `cache-update` probe expecting rc 2, matching `cli.py:43-44`) keep the document honest against the CLI.
- README: one added row, zero removed — sibling rows at `README.md:39-42` are the placement template; "Detects and reports only." is the shared closer.
- No-baseline rule (D-D21) with a recorded history search avoids a fake comparative bar.
- Name not changed even if naming-analyzer proposes one — `ai-kit-project-rules-docker` is already in REQ-rules-docker and Phase 15 SC1.

### Concerns
- **MEDIUM — CONTEXT corrections are incomplete vs live drift.** Specified pair is right (`13-CONTEXT.md:146-147` `stack_cache.py` / `detect_stacks`; `:15-16` "no Dockerfile"). Unaddressed: `:21-25` still says Phases 9–12 have no plans (false — arch skill is on disk); `:33-37` still cites `_iter_precommit_hook_blocks` in `makefile_checker.py` (it lives in `precommit_parse.py:39-55`); `:156` still says D-05 adds a catalog *category* (13-03 forbids that). Phase 14 will read this file.
- **MEDIUM — D-D19 does not include the 13-02 flow-mapping unreadability limit.** If 13-02 ships that gap, SKILL.md that omits it claims more than the parser does.
- **LOW — `SKILL-SHAPE-OK` limit keywords are greppable (`root`, `tab`, `declared`, `stale`, `local-dev compose`, `per-service`).** Softening into a clause still passes. The verbatim SUMMARY quote is the real control — do not replace it with "still present".
- **LOW — `HEAD~3` append-only check** is skipped on shallow/reordered history. The pinned-range added-lines-only diff is the one that matters; use it.

### Suggestions
- Quote all six limits as standalone sentences in SKILL.md before the judge runs, so iteration 1 does not start from buried clauses.
- Add a third append-only CONTEXT note for the "new category" Integration Points line, or at least record in the SUMMARY that 13-03 settled it as a separate mapping.
- Re-derive the category/issue table from the five check modules before writing; if code disagrees with this plan's table, the code wins (already stated — do it).
- If 13-02 left flow-mapping unread, add that as a seventh limit rather than implying the parser handles "compose files".

### Risk Assessment
**LOW** for code (this plan owns none). **MEDIUM** for shipped claims: installability plus a concision-optimizing judge is T-13-26. The dual-axis limits backstop is adequate if the executor actually quotes the section verbatim.

---

## Cross-plan

Wave order 13-01 → 13-02 → 13-03 → 13-04 matches the dependency graph. 13-01's glob registration is what lets 13-02/13-03 add modules without touching gate files. Applicability gate + one filename list + local-dev-only hot-reload scope compose correctly: a non-Docker repo stays silent; a base-only compose repo gets family/runbook/healthcheck/depends_on but not hot-reload; override files get SC4.

Shared-package edits stay additive (`STRUCTURAL_KINDS` append, new `yaml_text.py`, `tool_catalog.py` section after line 577). That matches "four siblings still import."

**Does not achieve the phase if:** the 13-01 gate walks the tree; 13-02 attributes nested blocks with a flat scan; 13-03 treats bind-mount + any override as conforming; 13-04 drops declared-values-only or the stale-baseline advisory. Each of those has a named non-vacuity mutation. Execute those mutations; do not skip them.

**Overall risk: MEDIUM.** Plans are unusually well grounded against this tree (Phase 12 is actually present; docker skill is actually absent; `e2e-docker` / nested Dockerfile / `STRUCTURAL_KINDS` / identifier precedence all check out). Remaining risk is executor traps (unreadable-file wrap, flow-mapping silence, longest-match ties, source-literal greps) and honesty-about-limits surviving the judge — not missing success criteria.

---

## Consensus Summary

Single-reviewer pass (opencode / xai/grok-4.6, reasoning=high). All four plans were reviewed with full source-grounded citations (`file:line` evidence throughout); no plan required a `[reviewed-without-repo-access]` or `[reviewed-without-source-citations]` downgrade. No HIGH-severity findings were raised against any plan. Eight MEDIUM and eight LOW concerns were raised across the four plans, concentrated on: (1) the shared Makefile parser's unhandled `UnicodeDecodeError` on unreadable files (13-01), (2) unspecified behavior for YAML flow-mapping forms and default-value handling in the compose parser (13-02), (3) unspecified tie-breaking and mixed-state handling in hot-reload detection (13-03), and (4) incomplete CONTEXT.md drift corrections and a limits-list gap (13-04). Overall risk assessed as MEDIUM, driven by executor-trap risk rather than missing success criteria — plans are described as "unusually well grounded" against the live tree.

### Agreed Strengths
(single reviewer — no cross-reviewer agreement to report)

### Agreed Concerns
(single reviewer — no cross-reviewer agreement to report)

### Divergent Views
(single reviewer — no divergent views to report)

---

CYCLE_SUMMARY: current_high=0 current_actionable=16

## Current HIGH Concerns
(none — no HIGH-severity findings were raised against any of the four plans)

## Current Actionable Non-HIGH Concerns
- **13-01 (MEDIUM)** — `parse_makefile_targets` (`makefile_parse.py:34-37`) has no try/except around `open(..., encoding="utf-8")`; a binary/non-UTF-8 Makefile raises `UnicodeDecodeError` instead of degrading. Plan needs: wrap the read in `docker_checker.check_docker_rules` with `try/except (OSError, UnicodeDecodeError)` treating failure as "no targets" — do not rely on the shared parser to grow this contract.
- **13-01 (LOW)** — `makefile_checker.py:463` citation (`"target": "validate"`) is a weak/coincidental pin, not evidence of the claimed ordering heuristic; should be re-read and re-cited.
- **13-01 (LOW)** — `13-CONTEXT.md:21-25` still says Phases 9-12 have no plans, which is stale (arch skill is on disk); should be corrected.
- **13-02 (MEDIUM)** — YAML flow-mapping bodies (e.g. `healthcheck: {interval: 30s, timeout: 10s}`) are outside the block-scan (D-D7) and yield false negatives; only flow *sequences* are specified, not flow *mappings*. Plan needs an explicit stated limit (and fixture) for this gap, or handling for it.
- **13-02 (MEDIUM)** — absent `interval` (Compose's implicit 30s default) is not flagged; correct behavior today but needs to be pinned as a stated 13-04 limit so a later executor doesn't "fix" it into scope creep.
- **13-02 (LOW)** — tab-indentation handling must be asserted as "does not raise" in the degradation-class tests, not "parses correctly".
- **13-02 (LOW)** — the `docker-compose.yml` literal-ban check (`ONE-FILENAME-LIST-OK`) greps comment-stripped source including docstrings; any docstring example containing that literal filename would fail the criterion even on a correctly repointed gate. Names should be interpolated from the tuples, not hardcoded in docs/comments.
- **13-03 (MEDIUM)** — longest-marker-match tie-breaking (`LONGEST-MATCH-OK`, e.g. `nodemon --watch src` → `nodemon`) is unspecified; plan needs a stated rule ("longest match, then earliest position in the stack's tuple on tie").
- **13-03 (MEDIUM)** — `NO-LOCAL-COPIES-OK` verification greps `hot_reload.py` for hardcoded marker literals (`vite`, `nodemon`, `docker-compose.override`) in comment-stripped source including docstrings; recommendation text must build marker lists via `HOT_RELOAD_TOOLS` at runtime, not hardcode examples.
- **13-03 (MEDIUM)** — mixed "unreadable volume + missing override" state is unspecified for the three-outcome hot-reload result; plan needs a pinned rule that an unreadable volume never contributes to outcome 2 ("no bind mount").
- **13-03 (LOW)** — `STACK-DETECT-ONCE-OK` AST check only matches a bare `detect_stacks(...)` call; a qualified `stack_detect.detect_stacks(...)` import style would fail the check and should be reconciled with the arch sibling's import style.
- **13-03 (LOW)** — `13-CONTEXT.md:156` Integration Points still says D-05 "adds a new category" to the tool catalog, which 13-03 correctly does not do; stale note should be corrected to avoid a future contributor merging into `BASELINE_STACKS`.
- **13-04 (MEDIUM)** — CONTEXT.md drift corrections in the plan are incomplete: beyond the two specified fixes, `:21-25` (stale Phase 9-12 status), `:33-37` (wrong module for `_iter_precommit_hook_blocks`, now in `precommit_parse.py:39-55`), and `:156` (stale D-05 catalog-category claim) remain uncorrected and should be added to the correction list.
- **13-04 (MEDIUM)** — the six stated limits (D-D19) omit the 13-02 flow-mapping unreadability gap; if 13-02 ships with that gap, SKILL.md should list it as a seventh limit rather than implying the parser fully handles compose files.
- **13-04 (LOW)** — `SKILL-SHAPE-OK` limit-keyword grep is easily satisfied by softened language; the verbatim-SUMMARY-quote backstop should remain the actual control (not weakened to "still present").
- **13-04 (LOW)** — the `HEAD~3` append-only CONTEXT check is skipped on shallow/reordered git history; the pinned-range added-lines-only diff should be used instead as the check that actually matters.
