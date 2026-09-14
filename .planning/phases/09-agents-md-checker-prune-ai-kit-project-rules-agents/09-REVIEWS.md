---
phase: 9
reviewers: [opencode]
reviewed_at: 2026-09-14T02:41:31Z
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

Using codegraph to verify plan claims against the live tree before writing the review.
Need the remaining test classes, RULES shape, SKILL.md, and registration surfaces.
Checking test-class inventory, SKILL.md, registration surfaces, and file counts against the plans.
Cycle-1 dispositions checked against the live tree. Remaining notes are new.

## 09-01

### Summary

The rename-then-prune split matches the tree: `main` at `cli.py:187-214` dispatches only `check` / `remediate` / `cache-update`; `check` at `cli.py:90-96` still returns `{"makefile", "workflow"}`; `RULES` is `ast.AnnAssign` at `rules.py:30`; `rule_checker.py:14` already imports `ai_kit_rules_common.classification`. Cycle-1 R1–R5 are reflected in the gates and match the files. This plan will hit REQ-rules-agents-prune’s code half if executed as written.

### Strengths

- Task 1 tracer is a real entrypoint run. `check_rules` at `classification.py:155-157` drops only `status == "present"`, so filler text still yields 17 ids (R04–R08 become `not_applicable`). Same shape as `TestCliCheck.test_check_combines_and_orders_by_criticality` (`tests/test_ai_kit_agents_md_rules_checker.py:821-831`).
- D-03 is aimed at leftovers that exist now: `skills/ai-kit-agents-md-rules-checker/__pycache__/` and `ai_kit_agents_md_rules_checker/__pycache__/`. The tracked-file / `!!`-only guard before `rm -rf` matches AGENTS.md’s no-`git-clean` rule.
- `TestGateRegistration` (`tests/test_ai_kit_agents_md_rules_checker.py:1133-1171`) pins Makefile:46/70, `.pre-commit-config.yaml:21,50,55`, `pyproject.toml:88,94` in the same commit as the path edits (T-09-02).
- Keep/delete split matches all 20 classes. Symlink-escape / dangling-link stay in `TestCliCheck` (`:858-891`) and actually exercise `os.path.realpath` at `cli.py:71-79` (T-09-01).
- D-04 copies `REQUIRED_STATIC_TARGETS` + `RESEARCH_CATEGORIES` (`stack_cache.py:19-45`, 7+5=12) with the process-category comment. `validate_entry` at `tools/setup.py:581-586` ignores a `skills/` dir with no `SKILL.md`.
- Phase 10 recovery is forced onto post-rename paths. `CLI-SURFACE-OK` uses `hasattr` so leaving `cache_update` as a dead function still fails.
- `functools` / `json` / `datetime` / `mock` are used only by classes Task 2 deletes (`:199`, `:222`, `:1019+`). The unused-import note is load-bearing for `make validate`.

### Concerns

- **LOW** — Surviving `TestRemediation` fixtures still carry `"makefile": []` (`:913`, `:961`, `:1010`). Harmless for `build_remediation` (`remediation.py:52` uses `.get`), but they are the only leftover Makefile-shaped payload in a suite whose point is that this skill no longer has that domain. Plan (d) drops the empty key only on the three *moved* cases.
- **LOW** — Task 2(e)’s “remaining three remediation cases from (d)” is easy to misread. The keep set is `test_missing_and_near_miss_auto_apply`, `test_matched_signals_carried_forward`, `test_returns_dict_never_bare_list` (`:895-922`, `:950-966`, `:1009-1012`). The move set is the other three (`:924-948`, `:968-987`, `:989-1007`). No name collision with `tests/test_ai_kit_rules_common.py:281-322`.

### Suggestions

- In Task 2(e), name the three keep methods and strip `"makefile": []` from those fixtures the same way (d) does for the moved ones.
- Record the 15 deleted class names in the SUMMARY template now so the executor cannot invent a shorter list.

### Risk Assessment

**LOW.** Cycle-1 holes (AnnAssign, inner `__pycache__`, post-rename `git show`, `cache-path` vs `cache-update`, dead fixtures) are gated against live source. Remaining nits are executor-clarity, not design.

## 09-02

### Summary

Docs/gate plan is correctly sequenced after 09-01 and aimed at the real SKILL.md: description/scope still advertise Makefile auditing (`SKILL.md:3,10`), wrap intro still names Step D (`:58`), `check` is still documented as `{"makefile", "workflow"}` (`:37`), and `## Deciding Step D` (`:132`) plus the unsourced-research anti-pattern (`:120-122`) are the right deletions. The A/B/C hand-off (`:60-66`) and remaining anti-patterns (`:99-119`) have no Makefile/pre-commit literals, so the KEEP bar and the `SCOPE-PRUNE-OK` chain do not collide. Two gaps remain: REQUIREMENTS.md still has the same false `cache-path` claim Task 3 only fixes in ROADMAP, and the skill-judge baseline is scored from a `./tmp/` path that is not a skill directory.

### Strengths

- Carve-out replacement `The hand-off is Steps A/B/C.` is the only wrap-section edit; `**Step A` / `**Step B` / `**Step C` (`SKILL.md:60,63,64`) still satisfy `grep -c 'Step A'` ≥ 1 (`Steps A/B/C` does *not* contain the substring `Step A`).
- Prescribed R02 bullet names `check_workflow_rules`, `signals`, `category`, and R02 without `makefile`/`pre-commit`, matching `classification.py:105-109` and `rules.py:44-50`.
- `DOC-MATCHES-CODE-OK` runs the pruned entrypoint; `FRONTMATTER-OK` requires `AGENTS.md` and `CLAUDE.md` in `description`. Together they close T-09-04’s routing lie if Task 1 is followed.
- `validate_entry` (`tools/setup.py:581-586`) and `cross_ai: false` (skill-judge is host-local) are the right constraints.
- Scratch deletion is `test ! -e ./tmp/09-skill-judge-baseline-SKILL.md`, not porcelain — `tmp/` is gitignored.
- Task 3’s append-only SC5/SC2 edits match ROADMAP `:307` and `:310` as they actually read, and the verify command pins the measured `BASELINE_SCORE` into the SC5 sentence.

### Concerns

- **MEDIUM** — AGENTS.md’s Workflow rule requires amending REQUIREMENTS.md *and* ROADMAP when a live-verified fact contradicts them. `REQ-rules-agents-prune` still says the `cache-path`/`cache-update` subcommands are removed (`.planning/REQUIREMENTS.md` v1.2). `main` at `cli.py:194-212` never dispatched `cache-path`; `cache_path` is `stack_cache.py:51`. Task 3 (`files_modified`: only `.planning/ROADMAP.md`) leaves the same false claim in the file downstream planners treat as requirement source of truth. Cycle-1 R11 widened Task 3 to SC2 but stopped at ROADMAP.
- **MEDIUM** — Baseline is `git show` into `./tmp/09-skill-judge-baseline-SKILL.md`. skill-judge scores packaging (frontmatter `name:` vs parent directory). The recovered blob’s `name: ai-kit-agents-md-rules-checker` (`SKILL.md:2`) sitting under `tmp/` can tank the baseline on location/name dimensions the pruned file (`skills/ai-kit-project-rules-agents/`) will win, making “no regression” easier to pass than a same-layout comparison. 09-CONTEXT.md asked for a controlled same-session comparison; path layout is an uncontrolled variable.
- **LOW** — Must-have says document `remediate`’s second key as always-empty (`build_remediation` at `remediation.py:77` still returns `blocked`). No acceptance check requires `"blocked"` in SKILL.md. A cheap edit that deletes that key from the docs still passes `DOC-MATCHES-CODE-OK` (it only runs `check`) and `SCOPE-PRUNE-OK`.

### Suggestions

- Add a second append-only sentence on `REQ-rules-agents-prune` in REQUIREMENTS.md, same house style as Task 3 (`Baseline corrected` / `Subcommand wording corrected`), or explicitly record in Task 3 why REQUIREMENTS.md is exempt.
- Recover the baseline blob into a scratch *directory named* `ai-kit-agents-md-rules-checker/` (still under `./tmp/`), run skill-judge on that `SKILL.md`, then delete the whole scratch dir by name.
- Add `grep -c '"blocked"'` (or equivalent) to Task 1’s chain so the always-empty second key cannot disappear from the docs.

### Risk Assessment

**LOW.** Docs/gate work is well specified against the live SKILL.md; the two MEDIUM items are amendment completeness and measurement fairness, not a likely wrong prune. They should be folded before execution so Phase 10 and later skill-judge comparisons do not inherit a stale REQUIREMENTS line or a vacuous baseline.

---

## Consensus Summary

Cycle 2. Only one reviewer lane ran (`opencode`, `xai/grok-4.6` at high reasoning), so there is no
cross-reviewer consensus to synthesize. The review is source-grounded — it cites `file:line`
evidence throughout and carries neither the `[reviewed-without-repo-access]` nor the
`[reviewed-without-source-citations]` marker. Both plan ids in the coverage manifest received their
own section.

**Cycle-1 carry-over: resolved.** Cycle 1's single HIGH (`RULES-17-OK` filtering on `ast.Assign`
against a `rules.py` `RULES` that is an `ast.AnnAssign`) is confirmed closed — this cycle's reviewer
re-checked the live tree (`rules.py:30`) and reports the gate now matches, along with cycle-1's four
MEDIUM/LOW items (post-rename Phase 10 `git show` paths, inner `__pycache__` in D-03,
`cache-path` vs `cache-update` wording, dead `_FIXTURE_*` constants). No HIGH concerns were raised
this cycle.

### Agreed Strengths

_Single-reviewer cycle — no 2+ reviewer corroboration available._ The reviewer's grounded strengths:
09-01's Task 1 tracer is a real entrypoint run whose 17-id expectation matches
`classification.py:155-157`; D-03's `rm -rf` is guarded by a tracked-file / `!!`-only check per
AGENTS.md's no-`git-clean` rule; `TestGateRegistration` pins all four registration surfaces in the
same commit as the path edits; the keep/delete split covers all 20 test classes; the Phase 10
recovery recipe is now forced onto post-rename paths and `CLI-SURFACE-OK` uses `hasattr` so a dead
`cache_update` function still fails. For 09-02: the wrap carve-out replacement is verified not to
break `grep -c 'Step A'`; `DOC-MATCHES-CODE-OK` derives documented keys from a real `check()` run;
Task 3's append-only SC5/SC2 edits match ROADMAP `:307`/`:310` as they actually read.

### Agreed Concerns

_Single-reviewer cycle._ Two MEDIUM items, both on 09-02 and both verified against live source:

1. **REQUIREMENTS.md amendment is incomplete.** AGENTS.md's Workflow rule requires amending
   REQUIREMENTS.md *and* ROADMAP.md when a live-verified fact contradicts them. `REQ-rules-agents-prune`
   still asserts `cache-path`/`cache-update` were removed CLI subcommands; `main` at `cli.py:194-212`
   never dispatched `cache-path` (`cache_path` is `stack_cache.py:51`). Task 3's `files_modified`
   names only `.planning/ROADMAP.md`, leaving the false claim in the requirements source of truth.
2. **skill-judge baseline layout is uncontrolled.** The baseline blob is recovered to
   `./tmp/09-skill-judge-baseline-SKILL.md`; skill-judge scores packaging (frontmatter `name:` vs
   parent directory), so a blob named `ai-kit-agents-md-rules-checker` sitting under `tmp/` can lose
   location/name points the pruned file under `skills/ai-kit-project-rules-agents/` will win —
   making "no regression" easier to pass than a same-layout comparison, contrary to 09-CONTEXT.md's
   controlled-comparison requirement.

Three LOW items: surviving `TestRemediation` fixtures still carry `"makefile": []`
(`:913`, `:961`, `:1010`); Task 2(e)'s "remaining three remediation cases" is ambiguous and should
name the three keep methods; and no acceptance check requires `"blocked"` to remain documented in
SKILL.md, so a cheap edit deleting that key still passes `DOC-MATCHES-CODE-OK` and `SCOPE-PRUNE-OK`.

### Divergent Views

_None — single reviewer._
