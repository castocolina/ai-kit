---
phase: 11
reviewers: [opencode]
reviewed_at: 2026-09-14T08:56:07Z
cycle_3_reviewed_at: 2026-09-14T08:56:07Z
plans_reviewed: [11-01-PLAN.md, 11-02-PLAN.md, 11-03-PLAN.md, 11-04-PLAN.md]
models:
  opencode: "xai/grok-4.6 (reasoning=high)"
model_sources:
  opencode: "pinned"
---

# Cross-AI Plan Review — Phase 11

<!-- gsd:plan-revision-conflicts:begin -->
## Plan-Revision Conflicts
(none)
<!-- gsd:plan-revision-conflicts:end -->

## OpenCode Review

I'll review the four plans against the live tree, starting with the prior cycle-2 findings and the files they claim to have fixed.
Phase-11 plan files weren't where I expected. I'll locate them and check the live shared-package interfaces the plans depend on.
Plan files didn't show up in glob. I'll list the planning tree and read the shared modules the plans claim to depend on.
I'll verify the cycle-2 HIGH fix against the design spec, the live Makefile, and the plan probes.
Cycle-2 HIGH is closed against the live spec table. Checking one last transcription collision, then writing the review.
Using writing-clearly-and-concisely. Grounded against HEAD `756a6f9` and the live tree (Phase 10 shared package present; `skills/ai-kit-project-rules-precommit/` does not exist yet).

## 11-01

### Summary
The wiring plan still matches the tree. Shared parsers exist, the stage-splitter has no production caller, gate line numbers are unchanged, and both cycle-1/cycle-2 tool-shape fixes are in the live plan text and in the tracer. Residual risk is execution, not design.

### Strengths
- Preconditions hold: `precommit_parse.py` and `makefile_parse.py` exist; `check_precommit_prepush_split` has no production caller (`makefile_checker.py:16-20`).
- Gate surfaces still match the cited lines: `Makefile:46` and `:70`, `.pre-commit-config.yaml:21`, `:50`, `:55`, `pyproject.toml:88`, `:94`.
- Sibling patterns to copy are real: `sys.path.append` at `__init__.py:25-26`; argparse-free `--cache-root` at `cli.py:32-48`.
- Tracer still requires `len(b)==2` including `shellcheck` with `uv run pre-commit run` on every delegate. A first-token matcher fails that probe.
- D-P2b now splits "deliberately non-gating" (all three targets) from "becomes tool-shaped under clause (iii)" (`security-scanner` only). That matches `Makefile:100-117`: `format` is a one-line short-name; `security-scanner` is `uv run bandit`; `duplicate-code` is `uv run pylint --enable=duplicate-code`.
- Eight prefixed delegates is now correct: `Makefile:75,78,83,86,89,92,95,98`.

### Concerns
None new. Cycle-2 LOW ("seven" vs "eight") is **FULLY RESOLVED**.

### Suggestions
None. Execute as written.

### Risk Assessment
**LOW.** Interfaces exist, ownership is clean, the tracer is a real SC1 probe, and the cycle-2 count/range error is gone.

## 11-02

### Summary
The cycle-2 HIGH is closed in the assertion, not by weakening D-T3. `PAIRS-REACHABLE-OK` now calls `resolve_tool_category` (index, then defaults). Independently counting the ten spec rows at `design.md:292-301` under that chain produces exactly `7 2 1 ['complementary']` — the dry-run number is the unique count this table yields, not an invented mock. The five non-HIGH cycle-2 items landed in plan text and in probes.

### Strengths
- `resolve_tool_category` is pinned as the single definition of "resolve" (`11-02-PLAN.md` D-T7, action (b2), `CATALOG-OK`, `PAIRS-REACHABLE-OK`, clause (iii)). An index-only guard is the cycle-2 self-trap; this chain is the reviewer's own first option.
- `CATALOG-OK` now asserts `R('ruff') in cats and 'ruff' not in L` and `R(fictional) is None`. Forcing bare `ruff` into the index, or answering every name, fails the probe.
- Four cited supplements are in the probe tuple: `staticcheck`, `ts-prune`, `cargo-audit`, `semgrep`, each required to share its partner's category. That matches `design.md:286,283,285,294`.
- Independent row count against the live spec:
  - same-category (7): eslint-plugin-security/semgrep, knip/ts-prune, checkstyle/PMD, cargo-audit/cargo-deny, cargo-machete/cargo-udeps, staticcheck/golangci-lint, gosec/govulncheck
  - cross-category (2), both complementary: ruff/vulture (linting vs dead-code), PMD/SpotBugs (linting vs security)
  - rule-family (1): ruff `S` vs bandit
- `CLAUSE-III-REAL-REPO-OK` runs `check` against this repo's root. `Makefile:109-110` is `uv run bandit`; a first-token matcher reads `uv` and fails. The second assertion forbids indexing bare `pylint` as duplicate-code. Python linting in the spec is `ruff check` only (`design.md:282`); bare `pylint` is not a baseline entry.
- `key_links` now names the two permitted mechanisms and forbids partner-derivation.
- Alias target is still the live 5-tuple (`tooling_payload.py:43-49`). `type-checking → None` remains the honest D-02 reading.

### Concerns
- **LOW — Java dead-code cell vs `SpotBugs`.** `design.md:284` security is `SpotBugs`+`find-sec-bugs`; dead-code is `PMD unused-code rules / SpotBugs UC_*`. Transcribing the second as bare `SpotBugs` collides with the security cell and trips D-T1 at import. Keep `SpotBugs UC_*` as a distinct string (or a comment). The collision guard is the safety net; this is a transcription footgun, not a missing guard.
- **LOW — this repo's `pylint` and `shellcheck` hooks will classify as unclassified.** Neither is a matchable baseline entry (`design.md:282`; shellcheck is absent from the table). That is honest `needs_research`, not a false positive. Do not index `pylint` to silence it — that is the change `CLAUSE-III-REAL-REPO-OK` is built to catch.

### Suggestions
- In the SUMMARY, record the four `PAIRS-REACHABLE-OK` values as measured (`7 2 1 ['complementary']`) and name the two cross-category rows (ruff/vulture, PMD/SpotBugs). The plan already requires this.
- When transcribing `design.md:284` dead-code, do not shorten `SpotBugs UC_*` to `SpotBugs`.

### Risk Assessment
**LOW.** Cycle-2 HIGH is **FULLY RESOLVED** in the probe, and the dry-run count matches the spec table. Remaining risk is transcription of two messy Java/Rust cells, caught at import if done wrong.

**Cycle-2 HIGH (`PAIRS-REACHABLE-OK` unsatisfiable vs bare `ruff`): FULLY RESOLVED.**
**Cycle-2 MEDIUM (`semgrep` 4th supplement): FULLY RESOLVED.**
**Cycle-2 MEDIUM (clause (iii) runner prefix): FULLY RESOLVED.**
**Cycle-2 MEDIUM (`duplicate-code` via bare `pylint`): FULLY RESOLVED.**
**Cycle-2 LOW (`key_links` partner-derivation): FULLY RESOLVED.**

## 11-03

### Summary
Both cycle-1 HIGHs stay closed. Cycle-2's MEDIUM ("keep the Task 3 precondition as-is") was correctly left unchanged: 11-02's chain fix removed the pressure to weaken D-T7, so the live `classify` gate remains a backstop rather than a load-bearing workaround.

### Strengths
- YAML contract is still scalar + inline list + block sequence; `YAML-BLOCK-SEQ-OK` asserts `linters.disable` as a positive read. `PAIR-CHECKS-OK`'s non-trigger is that same block sequence.
- Task 3 precondition still runs live `classify` on `golangci-lint` + `staticcheck` and HALTs against 11-02 with an explicit ban on a private tool map (`pair_checks.py` must not grow one).
- PMD discovery is a named candidate list. Rule-family coverage is nine-of-ten, skipped by the mark.
- D-C4 is grounded: this repo selects no `ANN`/`TC` (`pyproject.toml:34`) and has a `pyright` hook (`.pre-commit-config.yaml:29-34`). `pyright` is a slash-alternative in `design.md:282`, so the classifier will fill type-checking and `SELF-CLEAN-RUFF-OK` should hold.
- `advisory: True` → `auto_apply: False` is already in `build_remediation` (`remediation.py:80`). Asserting it on `remediate` output is the right probe.
- Child-config prune set is copy-pasteable: `_PRUNED_DIR_NAMES` at `makefile_checker.py:92-94`.

### Concerns
- **LOW — golangci `enable:` is additive, not a replacement.** The action says "replaces the default set with one that omits it." In golangci-lint, `enable:` adds to defaults; replacement is `disable-all` / `default: none` plus an enable list. The ROADMAP SC5 fixture is `disable: - staticcheck`, which is the correct form and is what `PAIR-CHECKS-OK` tests. Implement the disable path as specified; do not treat a mere `enable:` list as "staticcheck is off."
- **LOW — the ruff+bandit skip fixture is non-diagnostic by itself.** `ruff` classifies as linting, `bandit` as security (`design.md:282`), so same-category pair evaluation never considers them. "No `tool-pair` finding" would pass without reading `rule_family_members`. The plan already requires the skip path to read the mark; that assertion is the one that matters.

### Suggestions
- Pin the golangci "replacement" case as `disable-all`/`default: none`, not as `enable:` present-and-omitting.
- Prove the rule-family skip with a unit assertion on `rule_family_members`, not only with a ruff+bandit repo fixture.

### Risk Assessment
**LOW.** Cycle-1 HIGHs remain **FULLY RESOLVED**. Cycle-2 MEDIUM is **FULLY RESOLVED** by leaving the precondition untouched, which is what that finding asked for.

## 11-04

### Summary
The close-out plan still matches this repo's append-only correction style. The cycle-1 "amend" self-trap stays gone. `STATE.md:34` already reads 4. Nothing new is wrong.

### Strengths
- `AMENDMENT-OK` pins `Parity-check ownership corrected by Phase 11:` and asserts the first four words. Live precedent is `ROADMAP.md:326` / `REQUIREMENTS.md:77` ("Inherited-check scope corrected by Phase 10"). SC1 still contains "both directions, not just one" (`ROADMAP.md:347`); REQ-rules-precommit still contains "both directions" (`REQUIREMENTS.md:78`).
- `REQ-SAME-LINE-OK` and `APPEND-ONLY-OK` still encode the house style. Amendment basis is live: sibling unions hook ids at `makefile_checker.py:502-509`.
- `DOC-MATCHES-CODE-OK` against live JSON keys is the right T-11-20 control.
- Naming-analyzer is confirmation-only. Four later phases name this skill literally.
- Human-check against this repo is necessary. True findings to present, not suppress: `format` (clause (ii) from 11-01), `security-scanner` (clause (iii) from 11-02), `duplicate_code_absent` (no jscpd hook; pylint R0801 is Makefile-only), plus unclassified `pylint`/`shellcheck` if D-T4 does not mark them out-of-taxonomy. `vulture` is a dead-code hook (`.pre-commit-config.yaml:35-40`); do not expect `dead_code_absent`. `duplicate-code` the target must not appear in `target_without_hook`.

### Concerns
- **LOW — `SUMMARY-INPUTS-PRESENT-OK` is still a token floor.** Cycle 2 restated this and asked for no further hardening. The halt-on-empty-section rule in the action is the real gate. Leave it.

### Suggestions
None. Quote the three limits and the frontmatter description in `11-04-SUMMARY.md` as the plan already requires.

### Risk Assessment
**LOW.** Cycle-1 HIGH remains **FULLY RESOLVED**.

## Cross-plan

Wave order 11-01 → 11-02 → 11-03 → 11-04 still matches the tree. 11-01's preconditions are satisfied today.

Cycle 2's load-bearing break — `PAIRS-REACHABLE-OK` unsatisfiable against D-T3's bare `ruff` — is closed by one public `resolve_tool_category` chain that the import guard, the catalog test, 11-02's probes, and 11-03's `PAIR-PRECONDITION-OK` all call. The claimed dry-run `7 2 1 ['complementary']` is the count the live ten-row table produces under that chain. The three regressions the planner named (dropped supplement, bare name forced into the index, index-only resolution) each have a probe that fails them.

All four cycle-1 HIGHs remain closed. All six cycle-2 ledger rows are closed. No new HIGH. No new MEDIUM.

**Overall: LOW.**

### Cycle 3 ledger

| ID | Severity | Finding | Status |
|----|----------|---------|--------|
| 11-02 | HIGH (cycle 2) | `PAIRS-REACHABLE-OK` unsatisfiable vs D-T3 bare `ruff` | **FULLY RESOLVED** — probe calls `resolve_tool_category`; dry-run `7 2 1 ['complementary']` matches `design.md:292-301` |
| 11-02 | MEDIUM | D-T7 missing `semgrep` | **FULLY RESOLVED** |
| 11-02 | MEDIUM | clause (iii) runner prefix | **FULLY RESOLVED** — `CLAUSE-III-REAL-REPO-OK` against `Makefile:109-110` |
| 11-02 | MEDIUM | `duplicate-code` via bare `pylint` | **FULLY RESOLVED** — D-P2b + `CLAUSE-III-REAL-REPO-OK` second assertion |
| 11-02 | LOW | `key_links` partner-derivation | **FULLY RESOLVED** |
| 11-01 | LOW | "seven" delegates | **FULLY RESOLVED** — eight recipes, `Makefile:74-98` |
| 11-03 | MEDIUM | keep Task 3 precondition as-is | **FULLY RESOLVED** — no edit, by design |
| 11-01/11-03/11-04 | — | all 4 cycle-1 HIGHs | **FULLY RESOLVED** (unchanged) |
| 11-02 | LOW (new) | Java `SpotBugs UC_*` vs security `SpotBugs` | open, caught by D-T1 if transcribed wrong |
| 11-02/11-04 | LOW (new) | this repo's `pylint`/`shellcheck` hooks unclassified | open, true findings — do not index `pylint` |
| 11-03 | LOW (new) | golangci `enable:` is additive | open, SC5 fixture uses `disable:` |

---

## Consensus Summary

Single-reviewer cycle (opencode only, `xai/grok-4.6`, reasoning=high). The reviewer independently re-derived the `PAIRS-REACHABLE-OK` dry-run count (`7 2 1 ['complementary']`) against the live `design.md:292-301` ten-row table rather than accepting the plan's own claim, and confirmed cycle 2's HIGH is closed by the new `resolve_tool_category()` chain (index lookup → D-T3 defaults) that the import guard, catalog test, 11-02's probes, and 11-03's `PAIR-PRECONDITION-OK` all now call. All 6 cycle-2 ledger rows (1 HIGH, 4 MEDIUM, 1 LOW) and all 4 cycle-1 HIGHs are confirmed FULLY RESOLVED against the live tree at HEAD `756a6f9`.

Three new LOW-severity findings surfaced this cycle, none blocking:
1. A transcription footgun in 11-02 — the Java dead-code cell (`PMD unused-code rules / SpotBugs UC_*`) must not be shortened to bare `SpotBugs`, which would collide with the security cell and trip the D-T1 import guard.
2. This repo's own `pylint`/`shellcheck` pre-commit hooks are legitimately unclassified under the current baseline table — a true `needs_research` finding, not a bug, but flagged so 11-02/11-04 don't quietly index `pylint` to make it go away.
3. In 11-03, the plan text describes golangci-lint's `enable:` key as "replacing" the default lint set, but `enable:` is additive in golangci-lint — the correct replacement form is `disable-all`/`default: none`. The ROADMAP SC5 fixture already uses the correct `disable:` form, so this is a plan-prose correction, not a fixture/test change.

### Agreed Strengths
N/A — single reviewer this cycle.

### Agreed Concerns
N/A — single reviewer this cycle.

### Divergent Views
N/A — single reviewer this cycle.
