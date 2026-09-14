---
phase: 11
reviewers: [opencode]
reviewed_at: 2026-09-14T08:30:00Z
cycle_2_reviewed_at: 2026-09-14T08:30:00Z
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

I'll review the four Phase 11 plans against the live tree, not the plan text. Loading the review skill and grounding claims in the actual shared package and sibling skills.
The plans are on disk; I'll ground each claim against the live shared package, sibling skills, and design spec rather than treating the plan text as fact.
Phase 10 is in the tree; the precommit skill is not. Next I’ll check the shared modules and sibling patterns the plans claim to extend.
I need the sibling `__init__`, gate surfaces, design-spec tables, and a few load-bearing Makefile/pre-commit details before scoring the plans.
Checked the live tree at `561741f`. Phase 10’s shared package is present; `skills/ai-kit-project-rules-precommit/` does not exist yet. Registration line numbers in 11-01 match the files on disk.

## 11-01

### Summary
This plan can stand the skill up. Phase 10’s shared parsers, the sibling CLI/`__init__.py` pattern, and the gate surfaces it names are all in the tree and match the cited lines. The tracer fixture is a real SC1 discriminator. The main risks are D-P2’s tool-shape rule vs this repo’s actual recipes, and Task 1 shipping a shared `remediation.py` change whose unittest coverage waits until Task 3.

### Strengths
- Preconditions match the tree: `precommit_parse.py` and `makefile_parse.py` exist; `check_precommit_prepush_split` has no production caller (`makefile_checker.py:16` says so; only `tests/test_ai_kit_rules_common.py` calls it).
- Gate line numbers are exact: `Makefile:46` and `:70`, `.pre-commit-config.yaml:21`, `:50`, `:55`, `pyproject.toml:88`, `:94`.
- Sibling patterns to copy are real: `__init__.py` uses `realpath` + `sys.path.append` (`skills/ai-kit-project-rules-makefile/ai_kit_project_rules_makefile/__init__.py:6-26`); `cli.py` is argparse-free with a hand-scanned `--cache-root` (`cli.py:32-48`, `:51-87`).
- `build_remediation` is still a single `"makefile"` loop (`remediation.py:69-92`). Generalizing it to a kind tuple is the right additive edit; the back-compat one-liner asserts the live field set (`issue`, `auto_apply`, `stacks`).
- Tracer fixture hits both parity directions plus the splitter: `mypy` is in `SLOW_HOOK_KEYWORDS` (`precommit_parse.py:20`); `validate-dead` is a `CATEGORY_ALIAS_MAP` value (`makefile_checker.py:73`); `validate`/`test` are aggregates with empty recipes.
- D-P3 is the right ownership call. The sibling already unions hook ids into required targets (`makefile_checker.py:502-509`).
- Cache-staleness 180 vs 30 is correctly left as an open question (`stack_cache.py:22` is `30`).

### Concerns
- **MEDIUM — D-P2 clause (i) vs this repo’s recipes.** The plan says it copies “the delegation convention this repository itself uses.” This repo’s recipes are `uv run pre-commit run ruff --all-files` (`Makefile:85-86`), not bare `pre-commit run`. The tracer omits `uv run`. A first-token parse will miss every real delegate here; a substring check for `pre-commit run` will not.
- **MEDIUM — D-P2 clause (ii) will flag this repo’s `format` target.** `format` is in the pinned short-name list and has a one-line recipe (`Makefile:103-104`) with no matching hook. The dual recommendation (add a hook **or** state it is non-gating) is necessary, not optional. `security-scanner` and `duplicate-code` (`Makefile:109-117`) do not match those short names until 11-02 extends the predicate.
- **MEDIUM — Task 1 changes shared `remediation.py` with no unittest growth until Task 3.** Acceptance is one-liners. A later Task 1 amend can break the kind tuple while `tests.test_ai_kit_rules_common` still passes. The `<files>` list also omits `tests/test_ai_kit_rules_common.py`, so Task 1 cannot land those tests without failing `git show --stat`.
- **LOW — must_haves say `sys.path` insert; the sibling and the action say `append`.** Copy the sibling (`__init__.py:25-26`).

### Suggestions
- Pin clause (i) as: the recipe contains the token sequence `pre-commit run <id>`, anywhere on a real line, so `uv run pre-commit run ruff` counts.
- In the SUMMARY, record how `format` / `security-scanner` / `duplicate-code` on this repo classify under D-P2 as implemented.
- Keep Task 1’s shared-suite proof as the one-liners; do not silently edit `tests/test_ai_kit_rules_common.py` in that commit.

### Risk Assessment
**LOW.** Interfaces exist, ownership is clean, and the tracer is a real end-to-end probe. Residual risk is the tool-shape predicate, which 11-02 extends in one place — pin the `uv run` case now so that extension does not fight it.

## 11-02

### Summary
This is the phase’s knowledge plan, and it is mostly right: one catalog, derived index, alias table with an ast drift guard, absence computed from classification. Two transcription/matching gaps can make ROADMAP SC2/SC4 look green while 11-03’s Go pair fixture is dead on arrival.

### Strengths
- D-T1 (derive the index, raise on two-category collision) is the correct encoding of 11-CONTEXT D-01. `jscpd` in several stacks is the same category; `ruff format` vs `ruff check` are different strings — that matches the spec table (`design.md:282-286`).
- Alias target is the live tuple: `RESEARCH_CATEGORIES` in `tooling_payload.py:43-49` is five names. `type-checking → None` is the honest D-02 reading; `REQUIRED_STATIC_TARGETS` (`tooling_payload.py:25-33`) has no type-check slot.
- Drift guard via `ast` (not import) matches the sibling criticality pattern and the shared-package import rule.
- `detect_stacks` returns exactly `{go, python, node, java, rust}` (`stack_detect.py:15-26`). The catalog’s five rows line up.
- CLASSIFY-OK / DISAMBIGUATION-OK / ABSENCE-OK are real entrypoint probes for SC2 and SC4. Computing absence from classification (D-T5) is the right invariant.
- Not repointing the sibling’s `CATEGORY_KEYWORDS` / `_SPEED_TIERS` (`makefile_checker.py:49-55`, `:120-137`) is the same reversible follow-up `criticality.py` already records.
- Extending the one D-P2 predicate, rather than forking it, is the 11-01 contract.

### Concerns
- **HIGH — pairs-table tools may never classify, so 11-03 SC5 cannot fire.** Index is derived only from baseline cells. Bare `staticcheck` is not a cell entry; Go linting is `golangci-lint`, dead-code is `staticcheck unused` (`design.md:286`). Token-bounded longest match will not map hook `staticcheck` / `staticcheck ./...` onto `staticcheck unused`. 11-03 then evaluates “unordered pairs of detected tools **sharing a taxonomy category**.” Unclassified `staticcheck` shares nothing, and `PAIR-CHECKS-OK` fails. Same hole for `ts-prune` and `cargo-audit` (pairs table `design.md:295,298`; both are “don’t use” notes, not baseline entries).
- **MEDIUM — `+` / slash cells can be transcribed as one string.** `eslint`+`typescript-eslint` (`design.md:283`) as a single index key will miss CLASSIFY-OK’s `eslint` hook. The plan says to split slash-alternatives; it does not say to split `+` combinations. `spotless`+`google-java-format` is the same shape.
- **MEDIUM — cache-confidence fixture will never hit if the tool is already in the table.** Resolve order is index → out-of-taxonomy → cache → defaults (`D-T3`). A cache entry for `vulture` classifies as `baseline`. The cache test needs a name **absent** from the index.
- **MEDIUM — “stale” is a fourth outcome D-T3 does not name.** `read_stack_cache` returns `state: stale` with data still populated (`stack_cache.py:50-78`). The plan says “reported as stale rather than as fresh fact” but the confidence enum is only `baseline|cache|inferred|unclassified`.
- **MEDIUM — catalog-name clause vs the 2-line cap.** 11-02 adds “name or recipe token is in the index ⇒ tool-shaped.” If that ORs past the 2-line cap, a long recipe named `eslint` becomes parity-relevant and can break 11-01’s “multi-line non-tool is never flagged” fixture. The plan says both “do not loosen any existing clause” and “a catalog-named target with no hook IS now flagged.”

### Suggestions
- After deriving the index from the baseline table, also index every tool name that appears in the pairs table (still one category each; collision still raises). That is data, not a second handwritten map, and it makes 11-03’s Go/supersession rows reachable.
- Pin: `a + b` in a cell becomes two entries; parentheticals stay comments.
- Pin the cache fixture tool as a name not in the index (e.g. `deadcode-foo`).
- Pin confidence for a stale cache hit: `cache` plus `stale: true`, or `unclassified` with `needs_research`. Do not invent a fourth undocumented label.
- Pin the catalog-name clause as a third OR, still under the 2-line cap — or say the cap does not apply to catalog names, and require 11-01’s multi-line fixture **not** to use a catalog name.

### Risk Assessment
**MEDIUM.** SC2/SC4 can pass on the named fixtures while the catalog cannot support 11-03’s locked Go pair. Fix the index membership rule in this plan, not as a surprise in 11-03.

## 11-03

### Summary
The anti-pattern plan is the right shape: one degrade-not-crash reader, data-driven enable-everything table, type-safety answered by the classifier, pins as three concrete sources, D-04 as empty lookup. Two executable contradictions will fail the verify commands if implemented as written: the YAML subset cannot see the golangci `disable:` block list, and pair evaluation cannot see `staticcheck` unless 11-02 indexes it.

### Strengths
- D-C4 is grounded: this repo selects no `ANN`/`TC` (`pyproject.toml:34`) and has a `pyright` hook (`/.pre-commit-config.yaml:29-34`). A hooks-only type-safety check would still be wrong in general; the Makefile-target evidence source is the half that saves other repos.
- Preview pin via whole-file `rev:` is the right warning. `iter_precommit_hook_blocks` starts at `- id:` (`precommit_parse.py:43-52`), so a block-scoped scan cannot see `repo:` / `rev:` above the hook. The `RUFF-CHECKS-OK` fixture puts `rev: v0.14.0` on the repo line on purpose.
- Child-config prune set is copy-pasteable: `_PRUNED_DIR_NAMES` at `makefile_checker.py:92-94`, walk at `:348-351`. Copy it; do not invent a second set.
- D-04 encoded as `lookup(...) is None ⇒ do not flag` is the PROJECT.md rule. `mypy`+`pyright` is a live same-category pair with no pairs-table row (`design.md:282` vs `:288-301`).
- `advisory: True` → `auto_apply: False` is already in `build_remediation` (`remediation.py:80`). Asserting it on `remediate` output is the right probe.
- No XML parser / stdlib-only is the right T-11-14 control. This repo has no YAML parser today; do not add one.
- SELF-CLEAN-RUFF-OK should pass on this tree (curated select, pyright hook, `uv.lock` + `ruff~=0.14` in `pyproject.toml:19`).

### Concerns
- **HIGH — YAML subset vs the golangci disable fixture.** `config_read.py` is specified to read “simple scalar and inline-list values” and not block folding. `PAIR-CHECKS-OK`’s non-trigger is a **block sequence**:
  ```
  linters:
    disable:
      - staticcheck
  ```
  If the scanner cannot read that, the finding still fires and the assertion `assert not b` fails. ENABLE-EVERYTHING’s `enable-all: true` is a scalar and would still work, hiding the gap.
- **HIGH — pair evaluation depends on 11-02 classifying `staticcheck`.** See 11-02. If the executor follows 11-02 as written, `PAIR-CHECKS-OK` is unreachable no matter how correct `pair_checks.py` is.
- **MEDIUM — PMD discovery is underspecified.** D-C1 says “a PMD ruleset XML referenced from the repo.” No filename list, no walk bound. An unbounded XML hunt is a smaller T-11-15. Contrast ruff/go/node, which have named candidates.
- **MEDIUM — `ruff S` vs `bandit` cannot fire from hook classification.** That pairs row (`design.md:292`) is a rule-family vs a tool. Generic pair evaluation over classified hooks will never see it. Not an SC miss (SC5 is the Go row), but the “evaluate the ten-row table” claim overstates what hooks can prove.
- **LOW — ENABLE-EVERYTHING-OK / RUFF-CHECKS-OK / ABSENCE-OK run full `check`.** Extra parity/absence/stage-split issues in the payload are fine because assertions filter by `category`/`issue`. Do not tighten those probes to `len(findings)==1`.

### Suggestions
- State that the YAML subset **must** read golangci `linters.enable-all`, `linters.enable` (block or inline), and `linters.disable` (block or inline). The disable fixture is the contract, not an illustration.
- In 11-02 or here, say pair members are resolved by token-matching hook haystacks against the pairs table’s tool names, **or** require those names in the index. Do not leave both plans assuming the other did it.
- Name PMD candidates (`pmd.xml`, `rulesets/*.xml`, or a path in `pom.xml`) and reuse the pruned walk.
- For the ruff-S/bandit row, either skip it in this plan (config-family, not a hook pair) or fold it into the ruff checks. Do not pretend hook-pair evaluation covers it.

### Risk Assessment
**MEDIUM.** SC3’s ruff/go scalar markers will work. SC5’s Go clause and the disable half of its pair will not, unless YAML block lists and `staticcheck` classification are pinned before execution.

## 11-04

### Summary
The close-out plan is the right wave-4 job: document the code, judge it, confirm the name, append the SC1 correction. It correctly forbids code edits. The amendment verify command demands the word `amend`, which Phase 10’s house style never used — that will fail a faithful copy of 10-03.

### Strengths
- Sibling `SKILL.md` is a real template: report-only first, neighbouring boundaries, five-path entrypoint, honest copy-install `ImportError`, `check`/`remediate` shapes, no `--cache-root` (`skills/ai-kit-project-rules-makefile/SKILL.md:1-72`).
- `DOC-MATCHES-CODE-OK` against live JSON keys is the right T-11-20 control. `check` is `{"makefile": ...}` today (`cli.py:23`); this skill will be `{"precommit": ...}`.
- Amendment basis is live: sibling `check` unions hook ids and emits `present: False` for missing targets (`makefile_checker.py:502-509`). The 11-04 precondition one-liner (`target==mypy`, `present is False`) matches that code.
- No-baseline + history search, judge as code review, naming-analyzer confirmation-only, and “fix the document to match the code” are the standing AGENTS.md rules applied correctly.
- Human-check against this repo is necessary. This tree will produce real findings: `format`/`security-scanner`/`duplicate-code` have no hooks (`Makefile:100-117`); no duplicate-code **hook** (pylint R0801 is Makefile-only); `vulture` **is** a dead-code hook (`/.pre-commit-config.yaml:35-40`). Do not suppress those.

### Concerns
- **HIGH — `AMENDMENT-OK` requires the word `amend` in both files.** The verify does `re.findall(r'(?im)^.*amend.*$', sc1)` and `re.search(r'(?i)amend', req)`. Phase 10’s append used “Inherited-check scope **corrected** by Phase 10” (`ROADMAP.md:326`, `REQUIREMENTS.md:77`) — no `amend`. An executor copying that style fails the probe. The action never says to use that word.
- **MEDIUM — `AMENDMENT-OK` also requires `'both directions' in req` on the REQ-rules-precommit **line**.** That phrase is already there (`REQUIREMENTS.md:78`). Good. The same regex then requires `amend` on that same bullet. If the correction is a following paragraph, `req` is only the first matching `-` line and the probe fails.
- **MEDIUM — Task 1 `SUMMARY-INPUTS-PRESENT-OK` is a floor.** If a prior SUMMARY has the tokens but empty sections, the action says HALT. Cheap models will reconstruct from this plan anyway; the halt rule has to be treated as real.
- **LOW — `STATE.md` still says “Total Plans in Phase: 3”** (`STATE.md:34`). There are four plans. Not this plan’s job, but 11-04’s ROADMAP plan list is already the four-plan list (`ROADMAP.md:353-360`).

### Suggestions
- Either put `amend`/`Amended` in the correction sentence both files share, or change the verify to look for the dated correction the way 10-03 did (`9d672b9` / “Inherited-check scope”). Do not leave action and verify disagreeing.
- Append the correction to the existing REQ bullet (same line or same list item), not as a new paragraph, so `req=[... startswith('-')][0]` still sees it.
- Quote the three limits and the frontmatter description in `11-04-SUMMARY.md` as the plan already requires — that is what later phases copy.

### Risk Assessment
**MEDIUM.** Documentation and the judge loop are well specified. The amendment verify as written is a self-trap against this repo’s own append-only style.

---

## Cross-plan

Wave order 11-01 → 11-02 → 11-03 → 11-04 matches the code that exists. 11-01’s preconditions are satisfied today. The load-bearing cross-plan break is **catalog membership for pairs-table tools** (11-02) plus **golangci block-list YAML** (11-03): together they decide whether ROADMAP SC5’s last clause is actually executable. Fix those two before execution; do not leave them to executor discretion.

**Overall: MEDIUM.** The phase can hit all five success criteria if those two pins land. Without them, SC1–SC4 still ship and SC5’s Go clause does not.

---

## Consensus Summary

Only one reviewer lane (OpenCode, `xai/grok-4.6`, reasoning=high) ran this cycle — no other configured CLI (`--opencode` was the only explicit flag) participated, so there is no cross-reviewer corroboration available. The findings below are OpenCode's own, source-grounded against the live tree at commit `561741f` with concrete `file:line` citations throughout.

### Agreed Strengths
Not applicable — single-reviewer cycle, no corroboration possible.

### Agreed Concerns
Not applicable — single-reviewer cycle, no corroboration possible.

### Divergent Views
Not applicable — single-reviewer cycle.

### Single-Reviewer HIGH Findings (unconfirmed by a second reviewer)
- **11-02 — pairs-table tools may never classify, breaking 11-03 SC5.** The tool catalog's index is derived only from baseline-table cells; `staticcheck`, `ts-prune`, `cargo-audit` appear only in the pairs table (`design.md:286,295,298`) and would remain unclassified, so `PAIR-CHECKS-OK` in 11-03 cannot fire for the locked Go pair.
- **11-03 — YAML subset cannot read the golangci `disable:` block-sequence fixture.** `config_read.py` is specified to read only scalar/inline-list values; `PAIR-CHECKS-OK`'s non-trigger fixture uses a block sequence (`linters: \n  disable: \n    - staticcheck`), which the reader as specified cannot see, so the assertion that the finding does NOT fire would fail.
- **11-03 — pair evaluation depends on 11-02 classifying `staticcheck`.** Same root cause as the 11-02 HIGH above; restated because it independently breaks 11-03's own verify command regardless of which plan's task list "owns" the fix.
- **11-04 — `AMENDMENT-OK` verify requires the literal word "amend" in both files, but Phase 10's own precedent ("Inherited-check scope corrected by Phase 10") never used that word.** A faithful copy of the established house style fails the probe as specified.

---

## Cycle 2 — OpenCode Review (`xai/grok-4.6`, reasoning=high)

Reviewed against commit `a97d2f2` (cycle-1 replan) and the live tree. Verifies whether cycle 1's 4 HIGH fixes actually landed, and surfaces anything newly wrong.

### 11-01

**Summary:** The wiring plan still matches the tree: shared parsers exist, the stage-splitter has no production caller, gate line numbers are unchanged, and the cycle-1 tool-shape holes are closed in the tracer. Residual risk is small.

**Strengths:** Preconditions hold (`precommit_parse.py`/`makefile_parse.py` exist; `check_precommit_prepush_split` has no production caller). Gate surfaces match cited lines. Tracer now uses `uv run pre-commit run` on every delegate and requires `len(b)==2` including `shellcheck` (`11-01-PLAN.md:399`) — a first-token matcher fails that probe, closing cycle 1's D-P2 clause (i) gap. D-P2b is a named decision addressing the `format` target. `STALE_AFTER_DAYS` still 30 — the 180-vs-30 discrepancy correctly left open.

**Concerns (LOW):** "Seven" prefixed delegates is wrong — `Makefile` has eight `uv run pre-commit run` recipes (`py-compile` through `unittest-wizard`, `:74-98`); the plan's count and line range include `format`, which is not a delegate. The matcher itself does not depend on the count.

**Risk:** LOW. Cycle-1 MEDIUMs on clause (i), D-P2b, and the Task-1 shared-suite gap are fully addressed.

**Cycle-1 HIGHs:** none applicable to 11-01.

### 11-02

**Summary:** D-T7 closes the cycle-1 catalog hole for `staticcheck`/`ts-prune`/`cargo-audit`. The new `PAIRS-REACHABLE-OK` probe then overreaches: it demands every pairs tool-token live in the derived index, including bare `ruff`, which D-T3 forbids. That probe cannot pass without breaking inferred confidence.

**Strengths:** D-T1 (derive index, raise on collision) still matches the spec table. D-T7 + `CATALOG-OK` (`11-02-PLAN.md:425`) pin the three cycle-1 tools and require each to share its partner's category — refusing partner-derivation is correct (indexing `ruff` from the vulture row would mark every bare ruff hook as dead-code). `+` split is now its own transcription rule. Stale cache is `confidence: "cache"` plus `stale: true`.

**Concerns:**
- **HIGH — `PAIRS-REACHABLE-OK` vs D-T3 bare `ruff` (NEW, unsatisfiable as written).** The probe (`11-02-PLAN.md:433`) asserts every pairs-row tool-token resolves in the derived index. The "ruff vs vulture" spec row (`design.md:293`) is a bare tool token; baseline cells are `ruff format`/`ruff check`, not bare `ruff`. D-T3 keeps bare `ruff` OUT of the index (so a hook with no entry is `inferred` linting, not `baseline`) — putting it in breaks the inferred-confidence fixture; leaving it out breaks this new probe. Deriving a first-token `ruff` from both cells collides formatting vs linting and trips the import guard. Genuinely unsatisfiable as specified.
- **MEDIUM — D-T7 names three supplements; the guard requires every pairs tool-token.** Node security is `eslint-plugin-security` (+`semgrep` in CI) — `semgrep` is a pairs tool-token not covered by D-T7's three cited entries; the import guard raises until a fourth entry exists.
- **MEDIUM — clause (iii) "single recipe tool token" repeats the runner-prefix hole clause (i) already fixed.** `security-scanner` is `uv run bandit -r tools skills` — a first-token matcher yields `uv`, not in the catalog. Cycle 1's clause (i) fix (skip the runner prefix) was not carried to clause (iii).
- **MEDIUM — `duplicate-code` will not become tool-shaped via `pylint`.** Recipe is `uv run pylint --enable=duplicate-code`; catalog duplicate-code is `jscpd`/pylint `R0801`. Indexing bare `pylint` as duplicate-code would misclassify this repo's actual pylint lint hook.
- **LOW — `key_links` still says pairs-only names are "indexed into the category its partner resolves to."** D-T7 forbids that rule; the `key_links` prose was not updated to match action (b2).

**Suggestions:** Change `PAIRS-REACHABLE-OK` to resolve through the index OR the D-T3 defaults map, and/or only require index membership for redundancy/supersession rows (the rows 11-03 actually flags) — never put bare `ruff` in the index. Add `semgrep` as a fourth cited D-T7 entry. Pin clause (iii) the same way as clause (i): skip the runner prefix, then token-bound match against the index; do not expect `duplicate-code` to match via `pylint`.

**Risk:** MEDIUM. SC2/SC4 probes sound; cycle-1 Go-pair hole closed; Task 1 can still fail on the new `PAIRS-REACHABLE-OK` probe.

**Cycle-1 HIGH (staticcheck/ts-prune/cargo-audit unclassified): FULLY RESOLVED** for those three tools.

### 11-03

**Summary:** The anti-pattern plan now makes the golangci `disable:` block sequence a reader contract with a positive probe, and refuses to start Task 3 unless `classify` puts both Go tools in the same category. Both cycle-1 HIGHs closed. Remaining risk is 11-02's new catalog self-trap leaking in through the precondition.

**Strengths:** YAML contract is scalar + inline list + block sequence with indentation-based termination; `YAML-BLOCK-SEQ-OK` (`:301`) proves the reader against `linters.disable` as a positive assertion (the cycle-1 failure mode). Task 3 precondition (`:415`) runs live `classify` on both Go tools and HALTs against 11-02 rather than adding a private map. PMD discovery is now a named candidate list. Rule-family row is skipped by reading the mark, not a failed name match — nine-of-ten is the honest claim.

**Concerns (MEDIUM):** Task 3's `PAIR-PRECONDITION-OK` inherits 11-02's catalog — if 11-02 lands `staticcheck` correctly the Go fixture is fine; if the executor weakens D-T7 to force `PAIRS-REACHABLE-OK` to pass, this precondition is the backstop and must be kept as-is (no workaround should be added here).

**Risk:** LOW given 11-02's D-T7 actually landing; MEDIUM if 11-02 Task 1 is forced to compromise the index to satisfy `PAIRS-REACHABLE-OK`.

**Cycle-1 HIGH (YAML disable: block sequence): FULLY RESOLVED.**
**Cycle-1 HIGH (pair eval needs classified staticcheck): FULLY RESOLVED** — Task 3 precondition, halt-and-report, no private tool map.

### 11-04

**Summary:** The close-out plan now matches this repo's append-only correction style. The "amend" self-trap is gone. `STATE.md` already says 4 plans.

**Strengths:** `AMENDMENT-OK` (`11-04-PLAN.md:401`) now pins the opening phrase to the live Phase 9/10 house-style form ("...corrected by Phase 11:") rather than requiring the literal word "amend." REQ correction is on the same bullet line. No-baseline history search, judge-as-code-review, naming-confirmation-only, and "fix the document to match the code" all remain correct.

**Concerns (LOW):** `SUMMARY-INPUTS-PRESENT-OK` is still only a token floor — the halt-on-empty-section rule is written, but not new; still the real enforcement gate per the plan text.

**Risk:** LOW.

**Cycle-1 HIGH (AMENDMENT-OK required "amend"): FULLY RESOLVED** — opening phrase pinned to the Phase 9/10 form, confirmed against `ROADMAP.md:326`.

### Cross-plan (Cycle 2)

Wave order 11-01 → 11-02 → 11-03 → 11-04 still matches the tree. All 4 cycle-1 HIGHs are closed in the plan text with live probes (`CATALOG-OK`/D-T7 for `staticcheck`; `YAML-BLOCK-SEQ-OK` + Task 3 `PAIR-PRECONDITION-OK`). One NEW HIGH surfaced inside 11-02's own fix: `PAIRS-REACHABLE-OK` (`11-02-PLAN.md:433`) is unsatisfiable against D-T3's bare-`ruff` defaults map — must be fixed before execution, without indexing `ruff`. Clause (iii) still needs the same runner-prefix pin clause (i) already received.

**Overall: MEDIUM** — down from cycle 1's 4 HIGHs to 1 new HIGH, all 5 non-HIGH findings actionable and narrowly scoped.

### Cycle 2 HIGH/Actionable Ledger

| ID | Severity | Finding | Status |
|----|----------|---------|--------|
| 11-02 | HIGH (new) | `PAIRS-REACHABLE-OK` unsatisfiable against D-T3 bare-`ruff` defaults | UNRESOLVED |
| 11-02 | MEDIUM | D-T7 names 3 supplements, guard requires `semgrep` as 4th | UNRESOLVED |
| 11-02 | MEDIUM | clause (iii) needs the same runner-prefix pin as clause (i) | UNRESOLVED |
| 11-02 | MEDIUM | `duplicate-code` will not become tool-shaped via bare `pylint` | UNRESOLVED |
| 11-02 | LOW | `key_links` prose contradicts D-T7's no-partner-derivation rule | UNRESOLVED |
| 11-01 | LOW | "seven" delegates should be "eight" | UNRESOLVED |
| 11-02/11-03/11-04 | — | all 4 cycle-1 HIGHs | FULLY RESOLVED |

CYCLE_SUMMARY: current_high=1 current_actionable=5
