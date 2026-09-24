---
phase: 9
reviewers: [opencode]
reviewed_at: 2026-09-14T03:08:27Z
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

Using the review instructions to verify both plans against the live tree and prior REVIEWS.md. Gathering source evidence first.
Cycle-2 dispositions are in the plan ledgers. Verifying them against the live tree and hunting anything the prior cycles missed.
## 09-01

### Summary

Rename-then-prune still matches the tree: `main` at `cli.py:187-214` dispatches only `check` / `remediate` / `cache-update`; `check` at `cli.py:90-96` still returns `{"makefile", "workflow"}`; `RULES` is `ast.AnnAssign` at `rules.py:30` (17 entries); `rule_checker.py:14` already imports `ai_kit_rules_common.classification`. Cycle-1 R1–R5 and cycle-2 R12–R13 are in the gates and match the live files. Executed as written, this plan hits the code half of REQ-rules-agents-prune.

### Strengths

- Task 1 tracer is a real entrypoint run. `check_rules` at `classification.py:155-157` drops only `status == "present"`, so filler text still yields 17 ids. Same shape as `TestCliCheck.test_check_combines_and_orders_by_criticality` (`tests/test_ai_kit_agents_md_rules_checker.py:821-831`), which already reads only `result["workflow"]`.
- D-03 targets leftovers that exist now: `skills/ai-kit-agents-md-rules-checker/__pycache__/` and `ai_kit_agents_md_rules_checker/__pycache__/`. The tracked-file / `!!`-only guard before `rm -rf` matches AGENTS.md’s no-`git-clean` rule. Inner stale path is named.
- `TestGateRegistration` (`:1133-1171`) pins Makefile:46/70, `.pre-commit-config.yaml:21,50,55`, `pyproject.toml:88,94` in the same commit as the path edits (T-09-02). Fifth method `test_validate_covers_every_precommit_hook` (`:1173-1204`) does not name the skill and correctly stays.
- Keep/delete split matches all 20 classes and the live 63-test count. Symlink-escape / dangling-link stay in `TestCliCheck` (`:858-891`) and exercise `os.path.realpath` at `cli.py:71-79` (T-09-01).
- Move set (`:924-948`, `:968-987`, `:989-1007`) and keep set (`:895-922`, `:950-966`, `:1009-1012`) are named against the file. No collision with `tests/test_ai_kit_rules_common.py:281-322` (`test_unknown_kind_keys_ignored_safely` is the extra method there). Shared import already sits at `test_ai_kit_rules_common.py:278`.
- D-04 copies `REQUIRED_STATIC_TARGETS` + `RESEARCH_CATEGORIES` (`stack_cache.py:19-45`, 7+5=12) with the process-category comment. `validate_entry` at `tools/setup.py:581-586` ignores a `skills/` dir with no `SKILL.md`.
- `CLI-SURFACE-OK` uses `hasattr` so a leftover `cache_update` still fails. `NO-SECOND-KIND-PAYLOAD-OK` is AST dict-key/subscript scoped, so `_MAKEFILE_PATH` (`:28`) and `test_makefile_registers_module_and_package` (`:1134`) cannot false-fail it.
- Live D-02 grep is exactly the 12 files the plan names (Makefile, pyproject.toml, `.pre-commit-config.yaml`, README.md, `classification.py` docstring, test file, plus six files under the skill). `git ls-files` of the skill dir is 11. `test_ai_kit_rules_common` is 26 tests. AGENTS.md and `tools/install.sh` are clean.

### Concerns

None remaining. Cycle-2 R12/R13 are in Task 2(e) and the SUMMARY roster.

### Suggestions

None. Execute as written.

### Risk Assessment

**LOW.** Cycle-1 holes (AnnAssign, inner `__pycache__`, post-rename `git show`, `cache-path` vs `cache-update`, dead fixtures) and cycle-2 nits (empty `"makefile": []` at `:913`/`:961`/`:1010`, unnamed keep set) are gated against live source. Remaining work is mechanical.

### Prior concerns (09-01)

| # | Sev | Status |
|---|-----|--------|
| R1 AnnAssign `RULES-17-OK` | HIGH | **Resolved** — gate matches `ast.AnnAssign`; live `rules.py:30` is `RULES: tuple[dict, ...] = (` with 17 elts. |
| R2 Phase 10 recovery paths pre-rename | MED | **Resolved** — four post-rename `git show` invocations; parent is the rename commit. |
| R3 Inner `__pycache__` | MED | **Resolved** — both stale paths named; both `__pycache__/` dirs exist on disk now. |
| R4 `cache-path` not a subcommand | LOW | **Resolved** — `cli.py:194-212` dispatches `check`/`remediate`/`cache-update`; `cache_path` is `stack_cache.py:51`. 09-02 Task 3 amends ROADMAP SC2 + REQUIREMENTS. |
| R5 Dead `_FIXTURE_*` | LOW | **Resolved** — three module-level names present; `DEAD-FIXTURES-GONE-OK` keeps `_REPO`/`_MAKEFILE_PATH`/`_PRECOMMIT_PATH`/`_PYPROJECT_PATH`/`_CLI_PY_CANDIDATE`. |
| R12 Empty `"makefile": []` in keep fixtures | LOW | **Resolved** — Task 2(e) strips keep-set keys; `NO-SECOND-KIND-PAYLOAD-OK` added. Live keys at `:913`, `:961`, `:1010`. |
| R13 Unnamed keep set / 15-class roster | LOW | **Resolved** — both sets named; DELETE list is the live 15 Makefile/cache classes. |

---

## 09-02

### Summary

Docs/gate plan is correctly sequenced after 09-01 and aimed at the live SKILL.md: description/scope still advertise Makefile auditing (`SKILL.md:3,10`), wrap intro still names Step D (`:58`), `check` is still documented as `{"makefile", "workflow"}` (`:37`), and `## Deciding Step D` (`:132`) plus the unsourced-research anti-pattern (`:120-122`) are the right deletions. A/B/C (`:60-66`) and remaining anti-patterns (`:99-119`) have no Makefile/pre-commit literals, so KEEP and `SCOPE-PRUNE-OK` do not collide. Cycle-2 R14–R16 are in the tasks (REQUIREMENTS.md amendment, directory-scoped baseline, `"blocked"` floor). One new nit: the installed skill-judge rubric does not actually score parent-directory vs `name:`.

### Strengths

- Carve-out replacement `The hand-off is Steps A/B/C.` is the only wrap-section edit; line 58 is the only `makefile` hit in `:54-66`. `**Step A` / `**Step B` / `**Step C` (`:60,63,64`) still satisfy `grep -c 'Step A'` ≥ 1 (`Steps A/B/C` does not contain the substring `Step A`).
- Prescribed R02 bullet names `check_workflow_rules`, `signals`, `category`, and R02 without `makefile`/`pre-commit`, matching `classification.py:105-109` and `rules.py:44-50`. Current R02 anti-pattern (`SKILL.md:123-130`) is the rewrite target; `:99-119` has neither banned literal.
- Pre-task negative counts still match: makefile 11, pre-commit 3 (only `:3`, `:10`, `:77`), cache-update 6, Step D 8, ALL_TOOLING_KEYS 2. `"blocked"` count is 2 (`:37` shape sentence, `:47` example). README row check is 1 (`README.md:39`).
- `DOC-MATCHES-CODE-OK` runs the pruned entrypoint; `FRONTMATTER-OK` requires `AGENTS.md` and `CLAUDE.md` in `description`. Together they close T-09-04 if Task 1 is followed. `"blocked"` floor now gates the always-empty `remediate` key (`build_remediation` at `remediation.py:77`).
- `validate_entry` (`tools/setup.py:581-586`) and `cross_ai: false` are the right constraints. `tmp/` still has exactly the three entries Task 2 Step 6 must preserve (`agents-md-rules-research-python.json`, `ingest-manifest.yaml`, `scripts-linux-tmp-prune/`).
- Task 3 now amends both files AGENTS.md’s Workflow rule names. Live `REQ-rules-agents-prune` is `.planning/REQUIREMENTS.md:76` (still claims `cache-path`/`cache-update` subcommands). ROADMAP SC2/SC5 are `:307`/`:310`. Phase 10 neighbour at `:319` is the regex bound. Traceability row `:137` stays Pending. 08.1-01 house style is append-only.

### Concerns

- **LOW** — Task 2 `read_first` tells the executor to confirm a skill-judge dimension that scores frontmatter `name:` against the parent directory, and to report both runs’ score on it. The installed rubric does not have that dimension. D4 (`~/.agents/skills/skill-judge/SKILL.md:209-221`) scores `name` as lowercase / hyphens / ≤64 and description WHAT/WHEN/KEYWORDS — not directory match. D5 (`:293-317`) scores `references/` layering, which this skill does not have. Do not HALT looking for it. R15’s directory-scoped scratch path (`./tmp/ai-kit-agents-md-rules-checker/SKILL.md`) is still good same-layout hygiene, and the plan’s own `dirn==nm` gate checks it; just record that D4 does not weight directory match and move on. The “If the judge reported a packaging/naming dimension” clause in Step 5 already allows this.

### Suggestions

- In Task 2 Step 2, if no packaging/naming dimension exists, write `PACKAGING_DIMENSION: none (D4 name-format only)` in `09-SKILL-JUDGE.md` and continue. Do not treat a missing dimension as a HALT.

### Risk Assessment

**LOW.** Docs/gate work is specified against the live SKILL.md. Cycle-2 MEDIUMs (REQUIREMENTS.md amendment, baseline layout, `"blocked"` floor) are incorporated. The new LOW is executor-clarity on a rubric the plan slightly over-claimed; it does not reopen R15.

### Prior concerns (09-02)

| # | Sev | Status |
|---|-----|--------|
| R6 Wrap KEEP vs Step D in one sentence | MED | **Resolved** — exact replacement text; only wrap line that may change is `:58`. |
| R7 R02 anti-pattern wording | MED | **Resolved** — full replacement body prescribed. |
| R8 Porcelain scratch check | LOW | **Resolved**, form superseded by R15 — existence check, not porcelain. `tmp/` is gitignored. |
| R9 Description routing un-automatable | LOW | **Accepted** — `<human-check>` pair unchanged. |
| R10 skill-judge as code-review gate | n/a | **Resolved** — `<verification>` item 8 + T-09-06. |
| R11 ROADMAP SC2 `cache-path` | LOW | **Resolved**, then widened by R14. |
| R14 REQUIREMENTS.md unamended | MED | **Resolved** — Amendment 3 on `:76`, same opener as ROADMAP SC2, checkbox/traceability/Coverage untouched. |
| R15 Flat baseline path | MED | **Resolved** — `./tmp/<old-skill-dir-name>/SKILL.md` + `BASELINE_JUDGED_PATH` gate. Premise that skill-judge scores directory match is not in the installed rubric (new LOW above); the layout control still stands. |
| R16 `"blocked"` ungated | LOW | **Resolved** — `grep -c '"blocked"'` ≥ 1 in Task 1 chain; live count 2. |

---

## Consensus Summary

Cycle 3. Single reviewer lane (`opencode`, `xai/grok-4.6`). Source-grounded; no `[reviewed-without-repo-access]` / `[reviewed-without-source-citations]`. Both plan ids covered.

**Cycle-1 and cycle-2 carry-over: resolved.** All 16 ledger rows (R1–R16) are in the current plan text and still match the live tree. No HIGH this cycle. No cycle-2 MEDIUM left open.

**Agreed strengths.** 09-01 tracer is a real entrypoint run (`classification.py:155-157`); D-03 guards both stale `__pycache__/` dirs that exist on disk; `TestGateRegistration` pins the four registration surfaces; keep/delete covers all 20 classes / 63 tests; Phase 10 recovery is post-rename; D-04 lands 12 keys unwired (`tools/setup.py:581-586`). 09-02 wrap carve-out does not break `grep -c 'Step A'`; `DOC-MATCHES-CODE-OK` derives keys from a real `check()`; Task 3 now amends both ROADMAP.md `:307`/`:310` and REQUIREMENTS.md `:76`.

**Agreed concerns.** One new LOW on 09-02: installed skill-judge D4 does not score parent-directory vs `name:`. Not a reopen of R15. No MEDIUM. No HIGH.

**Divergent views.** None — single reviewer.

**Ready to execute.** Both plans.

---

## Consensus Summary

Cycle 3. One reviewer lane ran (`opencode`, `xai/grok-4.6` at high reasoning), so there is no
cross-reviewer consensus to synthesize. The review is source-grounded — it cites `file:line`
evidence throughout and carries neither the `[reviewed-without-repo-access]` nor the
`[reviewed-without-source-citations]` marker. Both plan ids in the coverage manifest received their
own section.

**Cycle-1 and cycle-2 carry-over: fully resolved.** All 16 prior ledger rows (R1–R16) are confirmed
incorporated in the current plan text and re-verified against the live tree. Cycle 1's single HIGH
(`RULES-17-OK` filtering on `ast.Assign` against an `ast.AnnAssign` `RULES`) remains closed. Cycle 2's
two MEDIUMs are closed: Task 3 of 09-02 now amends `.planning/REQUIREMENTS.md:76` alongside
ROADMAP `:307`/`:310` (R14), and the skill-judge baseline is recovered into a directory named for
the blob's own frontmatter `name:` with a `BASELINE_JUDGED_PATH` gate that re-derives that name out
of git (R15). Cycle 2's three LOWs are closed as well (empty `"makefile": []` keep fixtures,
unnamed keep set / 15-class roster, ungated `"blocked"` key).

No HIGH concerns were raised this cycle.

### Agreed Strengths

_Single-reviewer cycle — no 2+ reviewer corroboration available._ The reviewer's grounded strengths:
09-01's Task 1 tracer is a real entrypoint run whose 17-id expectation matches
`classification.py:155-157`; D-03 names both stale `__pycache__/` dirs that exist on disk and guards
`rm -rf` behind a tracked-file / `!!`-only check per AGENTS.md's no-`git-clean` rule;
`TestGateRegistration` (`tests/test_ai_kit_agents_md_rules_checker.py:1133-1171`) pins all four
registration surfaces in the same commit as the path edits; the keep/delete split covers all 20 test
classes and the live 63-test count; `NO-SECOND-KIND-PAYLOAD-OK` is AST dict-key/subscript scoped so
`_MAKEFILE_PATH` cannot false-fail it; D-04 lands 12 cache keys unwired (`tools/setup.py:581-586`).
For 09-02: the wrap carve-out replacement is verified not to break `grep -c 'Step A'`;
`DOC-MATCHES-CODE-OK` derives documented keys from a real `check()` run; Task 3's append-only edits
match ROADMAP `:307`/`:310` and REQUIREMENTS `:76` as they actually read.

### Agreed Concerns

_Single-reviewer cycle._ One new LOW, on 09-02, and it is an over-claim in the plan rather than a
design flaw:

1. **LOW — 09-02 Task 2 `read_first` asserts a skill-judge rubric dimension that does not exist.**
   The plan (`09-02-PLAN.md:262`) instructs the executor to confirm "whichever dimension scores
   packaging / naming consistency (frontmatter `name:` against the containing directory)" exists and
   how it is weighted BEFORE Step 2, and the `<done>`/SUMMARY text (`:670`) requires recording both
   runs' score on it unconditionally. The installed rubric has no such dimension: D4
   (`~/.agents/skills/skill-judge/SKILL.md:209-221`) scores `name` only as lowercase / hyphens /
   ≤64 chars plus description WHAT/WHEN/KEYWORDS — directory match is not scored anywhere in the
   file (independently confirmed by this workflow's source-grounding pass: no
   "parent director"/"containing directory" hit in the skill). An executor reading `read_first`
   literally could HALT hunting for a dimension that is not there. Step 5's conditional clause
   (`:336`, "If the judge reported a packaging/naming dimension") already tolerates absence, so the
   fix is to make `read_first` and the SUMMARY requirement conditional too. R15's directory-scoped
   layout control is still correct hygiene and is NOT reopened — the plan's own `dirname == name`
   gate is independent of the rubric.

No MEDIUM and no HIGH concerns this cycle. The reviewer's verdict on both plans is **ready to
execute**.

### Divergent Views

_None — single reviewer._
