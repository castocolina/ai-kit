---
phase: 9
reviewers: [opencode]
reviewed_at: 2026-09-14T02:18:55Z
plans_reviewed: [09-01-PLAN.md, 09-02-PLAN.md]
models:
  opencode: "xai/grok-4.6 (reasoning=high)"
model_sources:
  opencode: "pinned"
---

# Cross-AI Plan Review — Phase 9

<!-- gsd:plan-revision-conflicts:begin -->
## Plan-Revision Conflicts

_None recorded._
<!-- gsd:plan-revision-conflicts:end -->

## OpenCode Review

I'll verify the plans against the live tree first, then write the structured review.
Using writing-clearly-and-concisely for the review. Next I’ll check the plan’s counts and a few load-bearing claims against the live tree.
Using writing-clearly-and-concisely for the review. Claims below are checked against the live tree, not the plan text.

## 09-01

### Summary

The rename-then-prune split matches the tree: 11 tracked skill files, 12 live old-name hits outside `.planning`/`docs`/`tmp`, `check()` still returns both keys at `cli.py:90-96`, and `rule_checker.py:14` already imports the shared engine. Task 1’s registration rewrite plus `TestGateRegistration` is the right non-vacuity guard. Task 2’s class-deletion map matches the 20 test classes, the three second-kind `TestRemediation` cases are the only coverage of `build_remediation`’s makefile loop, and `ALL_TOOLING_KEYS` is 12. One acceptance command is wrong against the AST of `rules.py`, and the Phase 10 recovery recipe never names the post-rename paths.

### Strengths

- D-01/D-02/D-03 are operational, not slogans. `git ls-files` is 11; live `git grep -l` of the old names (excluding `.planning`/`docs`/`tmp`) is 12. Bytecode is already on disk at `skills/ai-kit-agents-md-rules-checker/__pycache__/` and the inner package `__pycache__/`, so the D-03 halt-then-`rm -rf` is aimed at a real leftover this repo has hit before.
- The Task 1 tracer is a real entrypoint invocation, not an import smoke test. `check_rules` at `classification.py:155-157` drops only `status == "present"`, so `not_applicable` rules (R04–R08 when tools are absent) still count; `len(ids)==17` holds on empty filler text. Existing `TestCliCheck.test_check_combines_and_orders_by_criticality` (`tests/test_ai_kit_agents_md_rules_checker.py:821-831`) already uses that same fixture shape.
- `TestGateRegistration` (`:1133-1171`) pins Makefile / pre-commit / pyright / vulture literals in the same commit as the surface edits. That is the T-09-02 mitigation, and those four surfaces do currently name the old skill (`Makefile:46,70`, `.pre-commit-config.yaml:21,50,55`, `pyproject.toml:88,94`).
- Task 2’s keep/delete split is complete against the 20 classes. The three cases to re-home — `test_combined_cross_kind_criticality_ordering` (`:924`), `test_present_but_recommended_structural_finding_in_remediate` (`:968`), `test_blocked_preserves_stacks` (`:989`) — are the only tests that enter `build_remediation`’s makefile loop (`remediation.py:52-68`). `test_ai_kit_rules_common.py` has 26 tests today; +3 = 29 is correct.
- D-04 landing `validate_tooling_payload` unwired is right: `_validate_tooling_payload` at `cli.py:105-126` plus the schema at `stack_cache.py:19-45` are Makefile-cache-specific; `setup.py:586` ignores a `skills/` dir with no `SKILL.md`; keeping it off vulture/ruff paths avoids a dead-code fail on a public function nothing imports yet.
- Removing `cache-update` (`cli.py:203-212`) really does drop this skill’s only write path and the only caller-supplied JSON ingest. The validator is preserved, not deleted.

### Concerns

- **HIGH — `RULES-17-OK` acceptance command cannot pass against this file.** Task 2 runs:

  `isinstance(n,ast.Assign) and getattr(n.targets[0],'id','')=='RULES'`

  Live `rules.py:30` is `RULES: tuple[dict, ...] = (`, which is `ast.AnnAssign`, not `ast.Assign`. I reproduced the `IndexError`. The executor will treat a correct 17-rule file as a failed prune and either churn or strip the annotation.

- **MEDIUM — Phase 10 recovery paths are unspecified.** Task 2’s parent is the *rename* commit, so the files live at `skills/ai-kit-project-rules-agents/ai_kit_project_rules_agents/makefile_checker.py` (and the same for `stack_cache.py` / `stack_detect.py`). CONTEXT and ROADMAP still show the pre-rename paths. A cheap executor will record `git show <sha>:skills/ai-kit-agents-md-rules-checker/...`, which does not exist on that parent.

- **MEDIUM — D-03 does not cover the inner package rename.** After `git mv` of `ai_kit_agents_md_rules_checker` → `ai_kit_project_rules_agents`, ignored `__pycache__` can remain at `skills/ai-kit-project-rules-agents/ai_kit_agents_md_rules_checker/`. D-03 only `rm -rf`s the old *skill* directory. Same leftover class as D-03, one level down. Tests import the new name, so this is clutter/footgun, not a silent wrong-import of the renamed suite.

- **LOW — `cache-path` is not a CLI subcommand.** ROADMAP SC2 and this plan treat `cache-path`/`cache-update` as subcommands. `main()` at `cli.py:187-214` dispatches `check`, `remediate`, and `cache-update` only. `cache_path` is a function on `stack_cache.py:51-52` and dies with that module. The work is correct; the wording is not.

- **LOW — unused test fixtures are not on the prune list.** `_FIXTURE_MAKEFILE_BASIC` and `_FIXTURE_PRECOMMIT_BASIC` (`:82-130`) are only consumed by classes Task 2 deletes. Plan tells the executor to drop unused *imports* (needed: `functools`, `mock`, `json`, `datetime` — tests do not ignore F401). It does not mention these constants. They may not fail ruff (F841 is local), but they are dead Makefile-domain payload left in the pruned suite.

### Suggestions

- Change `RULES-17-OK` to accept `ast.AnnAssign` (`n.target.id`) or both node types. Do not “fix” `rules.py` by dropping the annotation.
- In Task 2’s SUMMARY instructions, paste the three post-rename `git show` paths, not the pre-rename ones.
- Extend D-03 (or add a one-liner after the inner `git mv`) to `rm -rf` a leftover `ai_kit_agents_md_rules_checker/` under the new skill dir, with the same tracked-file halt guard.
- Name `cache-update` as the only removed subcommand; say `cache_path` leaves with `stack_cache.py`.
- Delete the two `_FIXTURE_*` constants in the same commit as the class deletions.

### Risk Assessment

**MEDIUM.** The mechanical rename/prune is well grounded and the tracers will catch a botched `check()` shape. The broken `RULES-17-OK` command can stall or mis-edit `rules.py`, and an unstated recovery path can make Phase 10 re-derive modules this phase meant to hand off.

## 09-02

### Summary

This is the docs/gate half, and it is sequenced correctly: 09-01 already moved names, this plan drops scope language that would keep routing Makefile questions here. The banned-literal chain matches the live `SKILL.md` (Makefile/pre-commit in `description`/`## Scope`/`## Run the check`, Step D + `## Deciding` + `ALL_TOOLING_KEYS` + `cache-update` in the wrap). The skill-judge same-session measurement plus ROADMAP append-only amendment matches AGENTS.md and the 08.1 house style. Main residual risk is the wrap-section edit (must delete Step D refs without touching A/B/C substance) and a judge finding that can only be cleared by restoring banned words.

### Strengths

- Precondition is load-bearing: it checks `cache_update` is already gone from `cli` before rewriting docs. That blocks documenting a prune 09-01 did not land.
- `DOC-MATCHES-CODE-OK` derives documented keys from a real `check()` run, not from reading the JSON example. After 09-01, `check()` returns only `workflow` (`cli.py:90-96` today returns both; prune removes `makefile`). The current example at `SKILL.md:37-51` still shows `"makefile"` kinds and a non-empty `blocked` list — exactly the lie T-09-04 names.
- Hand-off preservation is concrete: `grep -c 'Step A|B|C'` and `agent-md-refactor >= 3`. Those strings exist today at `SKILL.md:58-66` and throughout the wrap. The KEEP list correctly leaves entrypoint resolution (`:12-28`), inline reporting (`:148-150`), and `rules.py` as source of truth (`:153-154`).
- Banned literals are the right ones. Live counts in current `SKILL.md`: `makefile` (case-insensitive) appears in the description (`:3`), Scope (`:10`), the `check` contract (`:37`), wrap intro (`:58`), Step D (`:68-95`), the R02 anti-pattern (`:123-130`), and `## Deciding` (`:132`). `cache-update` / `Step D` / `ALL_TOOLING_KEYS` are confined to sections the plan deletes. Remaining anti-patterns (`:99-119`) do not contain those words, so “leave them as they are” will not fail the chain.
- Honest `remediate` contract: `build_remediation` (`remediation.py:11-12`) still returns `{"remediate", "blocked"}`. After prune, `blocked` is always empty because the makefile loop sees no `"makefile"` key. Documenting that beats deleting the key and teaching a `KeyError`.
- Task 2’s baseline is a git blob (`git show <sha>:<old-path>/SKILL.md`), scored in the same session as the pruned file, with `git cat-file -e` on the recorded spec. That is the only comparison 09-CONTEXT.md will accept. ROADMAP SC5 still cites `98/120` (`ROADMAP.md:310`); Phase 6 recorded `104/120`. Task 3’s append-only sentence, opening `Baseline corrected by Phase 9`, matches 08.1’s `Superseded by Phase 8.1` pattern (`08.1-01-PLAN.md:320-321`).
- `cross_ai: false` is justified: `/skill-judge` is a host skill, not a scripted edit. Putting it on 09-01’s cheap-model wave would fail SC5.

### Concerns

- **MEDIUM — wrap KEEP vs Step D REMOVE is a narrow edit.** `SKILL.md:58` is “The hand-off is Steps A/B/C, plus an optional Step D…”. Task 1 says do not tidy A/B/C wording, and also says remove every Step D cross-reference from that paragraph. `grep -c 'Step D'` must become 0. A cheap editor will either leave `:58` (fail verify) or rewrite the whole wrap (fail the “unchanged in substance” bar / drop `agent-md-refactor` count).
- **MEDIUM — skill-judge vs banned literals.** Task 2 forbids reintroducing Makefile/pre-commit/Step D language to win points, and caps the loop at three. That conflict path is written down, which is good. The R02 anti-pattern (`SKILL.md:123-130`) currently names `makefile_checker.py` and Makefile-shape; the rewrite must keep the `signals`/`category` lesson without those words. If the judge demands a named structural owner, “another skill’s concern” may score as vague.
- **LOW — scratch-file acceptance is vacuous.** Step 1 writes the recovered `SKILL.md` under `./tmp/` (gitignored). “Gone from the working tree” is checked with `git status --porcelain`, which will not list it even if left behind. Harmless under project convention, not evidence of deletion.
- **LOW — `description` is the only runtime change in this plan**, and no automated check talks to the host router. The human-check pair (“does my build configuration have the right targets” vs “is my AGENTS.md missing any workflow rules”) is the real SC3 test; it only runs end-of-phase.

### Suggestions

- Give the wrap intro a one-line replacement: “The hand-off is Steps A/B/C.” Nothing else in `:54-67` needs to move.
- For the R02 anti-pattern, prescribe the replacement sentence in the plan (name R02, `signals`, `category`, “structural half is another skill’s concern”) so the executor does not invent Makefile wording to stay precise.
- Add `rm -f` of the `./tmp/` baseline copy as an explicit Step 5 line, not a porcelain check.
- Keep the human-check. Do not try to automate host routing.

### Risk Assessment

**LOW.** Docs-only, well gated, and the dangerous mismatch (SKILL.md advertising `makefile` / `cache-update` after 09-01 removed them) is exactly what this wave closes. Residual risk is editorial: a wrap-section over-edit or a judge/scope stalemate, both of which the plan already tells the executor to stop and report rather than trade.

---

**Cross-plan:** Execute 09-01 then 09-02 with no gap that ships the renamed skill’s `SKILL.md` still advertising Makefile checks. Fix the `RULES-17-OK` AST check and the Phase 10 `git show` paths before 09-01 runs; 09-02 can stay as written.

---

## Consensus Summary

Only one reviewer lane ran this cycle (`opencode`, `xai/grok-4.6` at high reasoning), so there is
no cross-reviewer consensus to synthesize. The review is source-grounded — it cites `file:line`
evidence throughout and carries neither the `[reviewed-without-repo-access]` nor the
`[reviewed-without-source-citations]` marker — and its single HIGH was independently confirmed
against the live tree during aggregation.

### Agreed Strengths

_Single-reviewer cycle — no 2+ reviewer corroboration available._ The reviewer's grounded
strengths: D-01/D-02/D-03 are verified against real counts (11 tracked files, 12 old-name hits);
the Task 1 tracer is a real entrypoint invocation rather than an import smoke test;
`TestGateRegistration` pins the four registration surfaces in the same commit that edits them;
Task 2's keep/delete split is complete against all 20 test classes; D-04 landing the tooling
validator unwired avoids a dead-code gate failure; 09-02's `DOC-MATCHES-CODE-OK` derives the
documented keys from a real `check()` run rather than from the JSON example.

### Agreed Concerns

_Single-reviewer cycle._ The one HIGH — the `RULES-17-OK` acceptance command in 09-01 filtering on
`ast.Assign` when `rules.py:29` is `RULES: tuple[dict, ...] = (` (an `ast.AnnAssign`) — was
verified directly against the repo during this cycle and is confirmed: the list comprehension
yields `[]` and the `[0]` subscript raises `IndexError`, so a correct 17-rule file reads as a
failed prune.

### Divergent Views

_None — single reviewer._
