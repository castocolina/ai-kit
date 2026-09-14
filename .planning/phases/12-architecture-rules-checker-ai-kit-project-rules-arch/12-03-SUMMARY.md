---
phase: 12-architecture-rules-checker-ai-kit-project-rules-arch
plan: 03
subsystem: testing
tags: [skill-authoring, skill-judge, naming-analyzer, documentation, ast-arch-fitness]

# Dependency graph
requires:
  - phase: 12-01
    provides: arch_checker.check_arch_rules aggregator, D-A1 shape rule, D-A2 chaining, two structural finding categories, no-cache/two-subcommand D-A6
  - phase: 12-02
    provides: ast_only.build_ast_only_findings (arch-test-ast-only category, four pinned not-verifiable reason tokens), canonical_tools.canonical_tool_advice, D-01 re-verification evidence
provides:
  - skills/ai-kit-project-rules-arch/SKILL.md -- the installable, routable skill document
  - README.md registration row
  - .planning/phases/12-architecture-rules-checker-ai-kit-project-rules-arch/12-SKILL-JUDGE.md -- skill-judge + naming-analyzer + SC5 evidence
  - dated append-only correction to 12-CONTEXT.md's D-01 scouting claim
affects: [15-rules-orchestrator-ai-kit-project-rules-all]

actuals:
  tokens: 9285
  tasks: 3
  commits: 3
  plan_head_before: 811c531993c2fa6cfefd8b627082bcb3bd850314

tech-stack:
  added: []
  patterns: [skill-authoring pipeline (scaffold -> skill-judge gate -> naming-analyzer confirmation), append-only house-style correction of a planning-decision record]

key-files:
  created:
    - skills/ai-kit-project-rules-arch/SKILL.md
    - .planning/phases/12-architecture-rules-checker-ai-kit-project-rules-arch/12-SKILL-JUDGE.md
  modified:
    - README.md
    - .planning/phases/12-architecture-rules-checker-ai-kit-project-rules-arch/12-CONTEXT.md

key-decisions:
  - "SKILL.md documents exactly two subcommands (check/remediate), matching cli.py's real CLI surface (12-01 D-A6) -- no classify/cache-update subcommand promised."
  - "skill-judge scored 100/120, 0 Critical/0 Important -- no fix-loop iteration needed, no baseline exists."
  - "naming-analyzer confirmed the name as-is; no rename proposed or applied."
  - "D-01's scouting claim corrected append-only, inside its own block, citing tests/test_arch.py:374 and :605-611 as live evidence; the DECISION itself stands unchanged."

requirements-completed: [REQ-rules-arch]

duration: ~2h
completed: 2026-09-14
status: complete
---

# Phase 12 Plan 03: SKILL.md, skill-judge gate, naming-analyzer confirmation, SC5 traceability, D-01 correction Summary

**Wrote and gate-reviewed `ai-kit-project-rules-arch`'s SKILL.md (100/120, 0 Critical/Important, no fix loop needed), confirmed the family name via naming-analyzer, mechanically discharged ROADMAP Success Criterion 5, and appended a dated, evidence-cited correction to 12-CONTEXT.md's D-01 scouting claim.**

## Environment note (pre-execution)

The dispatched worktree was branched before Phases 12-01/12-02 landed on `main` (a known,
previously-encountered issue for this phase family) -- confirmed `git merge-base --is-ancestor HEAD
main` succeeded from worktree HEAD `b30c0b2`, and fast-forwarded losslessly: `git merge --ff-only
main` -> `811c531993c2fa6cfefd8b627082bcb3bd850314` (this plan's `plan_head_before`). Both of Task
1's precondition checks (the tests/tracer command, and the `SUMMARY-INPUTS-PRESENT-OK` gate over
both prior SUMMARYs) then passed cleanly -- the orchestrator's punctuation-only fix to
`12-02-SUMMARY.md`'s "Backlog resolution" heading (the missing trailing colon) was already present
on `main` at `811c531`. All `git` invocations throughout this run used the absolute path
`/usr/bin/git`, per this host's known bare-`git` PreToolUse hook pattern-matching quirk.

## Backlog resolution (ROADMAP Phase 12 Success Criterion 5):

> This phase promotes and resolves `.planning/ROADMAP.md`'s Backlog entry "Phase 999.3:
> Architecture-layer test suite" at this milestone's scoped-down, form/convention-only ambition --
> `arch-test` Makefile target existence, chaining into `test`, and AST-only-ness of the backing
> test file. The backlog note's fuller dependency-direction/layering-boundary enforcement ambition
> across the whole `tools/`/`skills/` tree remains an explicitly-flagged known gap, NOT built here.
> The backlog stub itself is left unchanged in `ROADMAP.md`; this phase is its resolution, not a
> second, separate item.

**Mechanical SC5 result:**
- The literal string `Backlog resolution (ROADMAP Phase 12 Success Criterion 5):` was found in
  all three PLANs (`12-01-PLAN.md`, `12-02-PLAN.md`, `12-03-PLAN.md`) and in both SUMMARYs written
  before this one (`12-01-SUMMARY.md`, `12-02-SUMMARY.md`; this SUMMARY itself, quoted above, is a
  third).
- The `### Phase 999.3: Architecture-layer test suite (BACKLOG)` section extracted from the live
  `.planning/ROADMAP.md` and from `.planning/ROADMAP.md` as it stood at base commit `42c8f8e`
  (this phase's base) is **byte-identical** -- 1571 bytes on both sides. The stub was not touched;
  the dated resolution note lives on Phase 12's own Goal paragraph (`ROADMAP.md:364`) instead.

## Performance

- **Duration:** ~2h (including the fast-forward, full read_first pass across both prior SUMMARYs
  and the design spec, and verification)
- **Started:** 2026-09-14T12:30:00Z (approx)
- **Completed:** 2026-09-14T14:38:19Z
- **Tasks:** 3 / 3
- **Files modified:** 4 (2 created, 2 modified)

## Accomplishments

- `skills/ai-kit-project-rules-arch/SKILL.md` written: frontmatter `name:` matches the directory
  basename; the description routes on this skill's own subject (`arch-test`, `architecture`)
  without naming sibling domains; the scope section states the report-only boundary and the three
  neighbouring sibling boundaries; the two real subcommands (`check`/`remediate`) are documented
  with their real output shapes copied from `cli.py`; the three finding categories
  (`arch-test-target`, `arch-test-chaining`, `arch-test-ast-only`) are named; the hardcoded
  canonical-tool baseline is presented with the Rust/Go known gap; and the three limits (the four
  pinned AST-only not-verifiable reason tokens, the baseline's no-staleness nature, the form-only
  wiring-vs-architecture scope) are stated in one scannable `## Limits` section.
- README.md carries exactly one new row for the skill, alongside its three siblings, with no other
  row disturbed.
- `/skill-judge` ran against the finished document at commit `405c502`: **100/120, 0 Critical, 0
  Important** -- clears the 96/120 alternative pass bar with room to spare. No baseline exists
  (verified by a full-history search, see below); no fix-loop iteration was needed.
- `/naming-analyzer` confirmed `ai-kit-project-rules-arch` as-is; no rename proposed or applied.
- ROADMAP Success Criterion 5 discharged mechanically (see above); `ROADMAP.md`/`REQUIREMENTS.md`
  otherwise untouched by this plan (`NO-ROADMAP-EDIT-OK` anchored on the plan-file's own last-write
  commit `6fddd35d`).
- `12-CONTEXT.md`'s D-01 carries a dated, append-only, house-style correction of its scouting claim,
  citing `tests/test_arch.py:374` and `:605-611` as live evidence; every original word of D-01
  preserved; the correction lands inside D-01's own block, before D-02.
- The finished skill was run against ai-kit's own repository root one final time: no
  target-existence or chaining finding (ROADMAP SC1 holds); the expected `arch-test-ast-only`
  finding surfaced and presented, not silenced (see below).

## Task Commits

1. **Task 1: Write SKILL.md and register it in README** - `405c502` (feat)
2. **Task 2: Run skill-judge as the code-review gate, commit evidence** - `890fe15` (docs)
3. **Task 3: naming-analyzer confirmation, SC5 discharge, D-01 correction** - `0bade3c` (docs)

**Plan metadata:** (this commit, docs: complete plan)

## Files Created/Modified

- `skills/ai-kit-project-rules-arch/SKILL.md` - the new skill's instructions (181 lines)
- `README.md` - one new registration row
- `.planning/phases/12-architecture-rules-checker-ai-kit-project-rules-arch/12-SKILL-JUDGE.md` -
  skill-judge evidence (Task 2), then extended with the naming-analyzer verdict and SC5
  discharge sections (Task 3)
- `.planning/phases/12-architecture-rules-checker-ai-kit-project-rules-arch/12-CONTEXT.md` - D-01's
  append-only correction

## `SKILL.md` frontmatter description, as committed, verbatim

> Use when a target repo's `arch-test`-shaped Makefile target needs auditing -- whether it exists,
> whether it is chained into `test` so it actually runs, and (where the backing test file is
> discoverable) whether that file is AST-only rather than importing or executing the module it
> architecturally checks -- or when asked "is my architecture-fitness test wired into test", "does
> my arch-test target actually run", or "does my architecture test file import what it should only
> parse". Detects and reports only; never edits the target repo.

## Limits section, quoted VERBATIM as it stands after the final skill-judge fix-loop iteration

No fix-loop iteration ran (0 Critical/0 Important findings, 100/120 already clears the bar), so the
text below is IDENTICAL to what Task 1 committed -- there is no before-text to quote beside it,
because nothing was reworded:

> Three places this skill knows less than it might appear to -- stated here rather than left to be
> discovered, in one scannable section, per the design spec's anti-patterns-live-in-one-place
> lesson.
>
> **1. The AST-only check is Python-only and statically scoped.** It reads one file, follows one
> level of local name resolution, and sees no cross-module dataflow and no computed/dynamic module
> names. Where it cannot see, it emits one of four PINNED advisory reasons rather than a guess or a
> silent skip -- a caller branches on these exact `reason` token strings, so a paraphrase here would
> document a surface the code does not emit:
>   - `not_discoverable` -- the arch-test target's own Makefile recipe formed a file-shaped
>     candidate, but it did not resolve to an existing regular file inside the repo root.
>   - `not_python` -- the backing file the recipe names is not a `.py` file, so this skill's
>     ast-based check does not apply to it.
>   - `unparseable` -- the backing file is a `.py` file that Python's own `ast.parse` refused to
>     parse (a syntax error).
>   - `no_parse_call` -- the backing file parsed, but contains no call reaching `ast.parse`
>     (directly, or through a helper function), so this skill could not identify what it
>     architecturally checks.
>
> **2. The canonical-tool baseline is hardcoded with no staleness mechanism.** For Rust and Go it
> states a known gap rather than naming a tool, because no equally canonical dedicated tool
> surfaced for those ecosystems, and asserting one would be a confident wrong answer.
>
> **3. This skill checks the FORM of architecture-fitness wiring only.** It does NOT enforce
> dependency-direction or layering-boundary rules, and it does not analyse the target repo's own
> import graph. That fuller ambition is an explicitly-flagged known gap recorded in this project's
> roadmap backlog, deliberately out of this skill's scope rather than unfinished work. A user who
> reads a clean report from this skill has learned that the wiring is present, not that the
> architecture is sound.

## Facts copied from prior SUMMARYs (Task 1's precondition-checked source material)

From `12-01-SUMMARY.md`: the `arch-test-target`/`arch-test-chaining` finding categories, the
D-A1 shape-rule concept (a naming rule, not a literal), the three chaining mechanisms (direct
prerequisite, transitive prerequisite via bounded graph walk, `test`'s own recipe invocation), the
no-cache/two-subcommand D-A6 statement, and the finding-schema fields (`category`, `issue`,
`criticality`, `summary`, `recommendation`, `needs_research`, never `target`).

From `12-02-SUMMARY.md`: the `arch-test-ast-only` category, the four pinned not-verifiable
`reason` tokens (`not_discoverable`, `not_python`, `unparseable`, `no_parse_call`) with their
meanings, the five canonical-tool-per-stack rows (python/node/java/rust/go) with their exact
wording, the Rust/Go known-gap phrasing, and the D-01 re-verification section's file/line evidence.

Both prior plans' `SUMMARY-INPUTS-PRESENT-OK` precondition check passed cleanly on the first
attempt -- no fact was missing at precondition time.

## History-search command verifying no prior SKILL.md existed for this domain

```
/usr/bin/git log --all --follow --oneline -- skills/ai-kit-project-rules-arch/SKILL.md
```
Output: exactly one line, `405c502 feat(12-03): write ai-kit-project-rules-arch SKILL.md and
register it in README` -- Task 1's own commit, nothing before it.

```
/usr/bin/git log --all --diff-filter=A --name-only --pretty=format:%H -- '**/SKILL.md'
```
(filtered for any added path containing "arch") -- output: exactly
`skills/ai-kit-project-rules-arch/SKILL.md`, added once, by commit `405c502`. No earlier name for
this domain ever carried a `SKILL.md`.

## `/skill-judge` rubric, score, and findings

Installed rubric read in full this session: 8-dimension, 120-point rubric -- D1 Knowledge Delta
(20), D2 Mindset + Appropriate Procedures (15), D3 Anti-Pattern Quality (15), D4 Specification
Compliance -- Especially Description (15), D5 Progressive Disclosure (15), D6 Freedom Calibration
(15), D7 Pattern Recognition (10), D8 Practical Usability (15). **Identical** to what Phases 9, 10,
and 11's evidence files recorded -- no difference to report.

**Score: 100/120 (83.3%, Grade B). 0 Critical, 0 Important. 0/3 fix iterations used.**

Per-dimension: D1=17/20, D2=9/15, D3=13/15, D4=14/15, D5=13/15, D6=13/15, D7=8/10, D8=13/15 (full
evidence and reasoning for each in `12-SKILL-JUDGE.md`). No Critical or Important finding was
raised. D2's lower score reflects an honest, real characteristic of this specific skill -- it has
no branch point requiring a decision framework, by design (D-A6: entirely hardcoded knowledge, no
research dispatch) -- not a hidden gap the document fails to guide; D8's 2-point deduction is a
real but Minor gap (no worked `check`-output JSON example, only `remediate`'s). Neither rises to
Critical/Important. No disagreement was recorded during a fix loop because no fix loop ran (the
score already clears the 96/120 alternative bar).

Baseline: **none** -- this is a brand-new skill, verified by the two history-search commands above,
run and re-run, both returning only Task 1's own commit.

## Naming-analyzer verdict, verbatim

**NAMING_VERDICT: confirmed -- "ai-kit-project-rules-arch" is kept as-is, no rename applied.**

The analysis found one real tension worth recording (a bare "arch" segment could, in isolation,
over-promise full architecture enforcement) but concluded it does not warrant a rename: the
family's own convention names skills by DOMAIN, not by scope depth (no sibling qualifies its own
narrower-than-the-domain-name scope in its directory name either), and the `description`
frontmatter field plus the `SKILL.md` body's own Limits section are the correct place for
scope-depth communication, which this document already does. No alternative name is proposed; no
phases would need updating since no rename is proposed. Full reasoning (vagueness, misleading-name,
abbreviation, family-convention-match, length checks) recorded in `12-SKILL-JUDGE.md`.

## D-01 correction, quoted as appended

> Scouting claim corrected by Phase 12: D-01's DECISION (target-aware correlation, not a blanket
> scan) stands and was implemented faithfully -- confirmed by plan 12-02's live re-verification.
> Live evidence: the file's architecture-fitness check calls `_parse("status-line.py")` at
> `tests/test_arch.py:374` (a parser-helper function reaching `ast.parse`), correctly parsing
> `tools/status-line.py` -- the real checked target -- exactly as this decision describes, and the
> unrelated `tools/setup.py` load this decision also names is correctly NOT flagged. But the SAME
> FILE additionally contains `TestSegmentInventory._sl` at `tests/test_arch.py:605-611`, which
> separately loads that SAME module (`tools/status-line.py`) via
> `importlib.util.spec_from_file_location` + `exec_module`, for unrelated segment-inventory test
> helpers. This decision's supporting claim that the file "never import[s]" its checked target is
> therefore not accurate against the live tree: the file's architecture-fitness METHODS are
> AST-only, but the FILE as a whole is not. Consequence, per plan 12-02's recorded re-verification:
> running the finished checker against this repository DOES produce one `arch-test-ast-only`
> finding (`backing_file_executes_checked_target`) -- a true, correctly-implemented result of the
> target-aware design this decision specified, not a checker defect. ROADMAP Success Criterion 1 is
> unaffected -- it is scoped to target-existence and chaining findings only, neither of which fires
> here.

Confirmed: the correction opens with the pinned house-style phrase `Scouting claim corrected by
Phase 12:` (the same `<what was wrong> corrected by Phase <N>:` form `ROADMAP.md:326` and
`REQUIREMENTS.md:76-77` already established, no fifth form invented); it landed inside D-01's own
block, immediately after the Reversibility sub-line and before `- **D-02:**` begins; every original
word of D-01 survives verbatim (`APPEND-ONLY-OK` -- 24 added lines, 0 removed); and it cites the
live file/line evidence `12-02-SUMMARY.md` recorded rather than restating this plan's own belief.

## Finished skill run against ai-kit's own repository root

`python3 skills/ai-kit-project-rules-arch/ai-kit-project-rules-arch.py check .`:

```json
{
  "arch": [
    {
      "category": "arch-test-ast-only",
      "issue": "backing_file_executes_checked_target",
      "criticality": 3,
      "summary": "'tests/test_arch.py' both parses and imports/executes 'status-line' -- an architecture-fitness check that imports or executes the module it is checking defeats the point of a static, ast-only check. Change 'tests/test_arch.py' to only 'ast.parse' 'status-line' and never import, exec, or spec-load it.",
      "recommendation": "'tests/test_arch.py' both parses and imports/executes 'status-line' -- an architecture-fitness check that imports or executes the module it is checking defeats the point of a static, ast-only check. Change 'tests/test_arch.py' to only 'ast.parse' 'status-line' and never import, exec, or spec-load it.",
      "needs_research": false
    }
  ]
}
```

`remediate .`: one entry, `kind: "arch"`, `id: "arch-test-ast-only"`, `auto_apply: true` (the real
finding carries no `advisory` key, so the default applies), `blocked: []`.

| Finding | Judgement |
|---|---|
| `arch-test-ast-only` / `backing_file_executes_checked_target` | **TRUE statement uz may want to act on, not a false positive.** `tests/test_arch.py`'s `TestSegmentInventory._sl` genuinely loads `tools/status-line.py` via `spec_from_file_location`/`exec_module`, the same module `_parse("status-line.py")` architecturally checks via pure `ast.parse`. This is exactly the disclosure plan 12-02 made and this plan's Task 3 human-check re-confirmed against the live tree. Not opened as a fix here -- this plan reports, per its `<files_modified>` boundary and its own instruction not to edit `tests/test_arch.py`. |

No `arch_test_target_missing` / `arch_test_not_chained` finding -- ROADMAP Success Criterion 1
holds, matching the positive fixture the whole phase family is built against.

## Decisions Made

- **Two-subcommand documentation, not four.** Followed 12-01 D-A6 exactly: `SKILL.md` documents
  `check`/`remediate` only, with explicit prose (outside the runnable command surface, per the
  Round-1 review's scoping fix) stating this skill has no `classify`/`cache-update` subcommand and
  why -- an architecture-fitness tool choice per ecosystem is stable, unlike a per-stack linter
  roster.
- **README row placed after the precommit sibling row**, keeping the four-skill family visually
  grouped together in the table, before the unrelated `ai-kit-gsd-curated-config` row.
- **No fix loop invoked**, since the first skill-judge pass already cleared 0 Critical/0 Important
  and 100/120 >= 96/120. Documented per Task 2's own instruction (the fix loop's constraints were
  never exercised, and this is stated rather than left implicit).
- **Naming-analyzer's one real observation (the "arch" segment's potential over-promise) recorded,
  not acted on** -- consistent with the plan's explicit instruction that a rename is the user's
  decision, not this task's.

## Deviations from Plan

None -- plan executed exactly as written. No architectural changes, no Rule 1-4 deviations were
needed at any task.

## Issues Encountered

None beyond the environment note above (stale worktree base, resolved by fast-forward before Task
1 began).

## `make test` (all four pyramid tiers)

`uv` was available (`uv 0.11.28`) throughout this run. `make test` exits 0: 349 tests across
`tests.test_ai_kit_project_rules_arch`/`test_ai_kit_rules_common`/`test_ai_kit_project_rules_precommit`/
`test_ai_kit_project_rules_makefile`/`test_ai_kit_project_rules_agents` (all `OK`), 6
framework-profile tests, 131 wizard/config-doctor tests, 13 e2e/system-memory tests, 16 shell
install tests, and 22 `tests.test_arch` tests (the file this plan's D-01 correction is grounded
against -- unedited) -- all `OK`.

## `make validate`

Reported honestly, not a bare pass/fail. `make validate` exits non-zero because `ruff` (its first
prerequisite) exits non-zero -- but every finding is pre-existing and out of scope for this plan,
confirmed by grepping the full output for every path this plan's `files_modified` touches (zero
matches):

- `ruff`: 25 pre-existing errors across `docs/wizard-redesign/prototypes/mockup-textual.py`,
  `skills/ai-kit-spec-review/ai_kit_spec/dispatch.py`,
  `skills/markdown-to-pdf/scripts/markdown_to_pdf.py`,
  `skills/mermaid-audit/scripts/{audit_mermaid,mermaid_style}.py`, `tests/test_ai_kit_spec.py`,
  `tests/test_ai_kit_spec_superpowers.py`, `tools/status-line.py`, `tools/wizard_app.py` -- the
  same count 12-02-SUMMARY.md recorded, none in this plan's `<files>`.
- `pylint`: fails with 6 pre-existing findings, all in `tools/status-line.py` (matching
  12-01/12-02's recorded findings).
- `pyright`: fails with 1 pre-existing error in
  `skills/ai-kit-project-rules-precommit/ai_kit_project_rules_precommit/pair_checks.py:178:26`
  (named in 12-01-SUMMARY.md as a newly-surfaced, pre-existing, out-of-scope discrepancy).
- `vulture`, `shellcheck`, `py-compile`: all pass individually (run directly since `make
  validate`'s composite target halts at the first failed prerequisite).

No finding in `skills/ai-kit-project-rules-arch/SKILL.md`, `README.md`, `12-SKILL-JUDGE.md`, or
`12-CONTEXT.md` -- none of these are Python/shell source subject to `ruff`/`pylint`/`pyright`/
`shellcheck` in the first place, and grepping confirmed no path under `skills/ai-kit-project-rules-
arch/` appears in any tool's output.

## Known Stubs

None.

## Threat Flags

None beyond what this plan's own `<threat_model>` already registers (T-12-15 through T-12-20, all
mitigated per the threat register: ordering for the installer-exposure risk, the two-axis
mechanical+record backstop for T-12-16/T-12-17, append-only/pinned-block constraints for T-12-18,
byte-comparison for T-12-19, confirmation-only naming for T-12-20).

## Next Phase Readiness

- The `ai-kit-project-rules-arch` skill is now installable (`SKILL.md` exists) and reviewed, ready
  for the milestone's next skills (Phases 13-15) to reference it by name.
- Phase 15's orchestrator (`ai-kit-project-rules-all`) can now name all four landed family members
  (`agents`, `makefile`, `precommit`, `arch`) plus the two still-pending (`docker`, `cicd`).
- No blockers.

---
*Phase: 12-architecture-rules-checker-ai-kit-project-rules-arch*
*Completed: 2026-09-14*

## Self-Check: PASSED

- `skills/ai-kit-project-rules-arch/SKILL.md` -- FOUND
- `README.md` -- FOUND (modified)
- `.planning/phases/12-architecture-rules-checker-ai-kit-project-rules-arch/12-SKILL-JUDGE.md` -- FOUND
- `.planning/phases/12-architecture-rules-checker-ai-kit-project-rules-arch/12-CONTEXT.md` -- FOUND (modified)
- Commit `405c502` (Task 1) -- FOUND in `git log`
- Commit `890fe15` (Task 2) -- FOUND in `git log`
- Commit `0bade3c` (Task 3) -- FOUND in `git log`
