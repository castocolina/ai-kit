---
phase: 13-docker-rules-checker-ai-kit-project-rules-docker
plan: 04
subsystem: testing
tags: [skill-authoring, skill-judge, naming-analyzer, docker, documentation]

requires:
  - phase: 13-docker-rules-checker-ai-kit-project-rules-docker
    plan: 01
    provides: "check_docker_rules aggregator, the eight-target family, the applicability gate, the runbook check"
  - phase: 13-docker-rules-checker-ai-kit-project-rules-docker
    plan: 02
    provides: "compose_parse.py's D-D7 parser contract, healthcheck.py, depends_on.py, and the flow-mapping limit recorded as surviving into the shipped parser"
  - phase: 13-docker-rules-checker-ai-kit-project-rules-docker
    plan: 03
    provides: "hot_reload.py, the per-stack marker table in tool_catalog.py, and the mapping-style long-form volume descope"
provides:
  - "skills/ai-kit-project-rules-docker/SKILL.md -- the document that makes the skill installable for the first time in this phase"
  - "README.md's skill-table row for ai-kit-project-rules-docker"
  - "13-SKILL-JUDGE.md -- skill-judge evidence (103/120, 0 Critical, 0 Important) plus the naming-analyzer verdict and the ROADMAP Phase 13 SC discharge pointers"
  - "13-CONTEXT.md's 9 dated, append-only stale-line corrections"
affects: [14-ci-cd-rules-checker-ai-kit-project-rules-cicd, 15-rules-orchestrator-ai-kit-project-rules-all]

actuals:
  tokens: 13061
  tasks: 3
  commits: 3
  plan_head_before: 2d8f58d5b32efc5174f9a10d08226a8aa79ed8ca

tech-stack:
  added: []
  patterns:
    - "SKILL.md written FROM the committed code and the three preceding SUMMARYs, never from this plan's own pre-execution table -- the category/issue list, the two-subcommand shape, and the eighth (mapping-style) and conditional-seventh (flow-mapping) limits were all re-derived live rather than copied"
    - "Evidence-file shape reused from Phase 12's 12-SKILL-JUDGE.md: machine-parseable header lines (JUDGED_PATH/JUDGED_COMMIT/BASELINE/SCORE/CRITICAL/IMPORTANT/FIX_ITERATIONS_USED), per-dimension table, findings section, code-review byte-identity pointer"
    - "Append-only correction notes in AGENTS.md's own amendment style, pinned to an explicitly-resolved <sha>^..<sha> diff range rather than a relative HEAD~N anchor"

key-files:
  created:
    - skills/ai-kit-project-rules-docker/SKILL.md
    - .planning/phases/13-docker-rules-checker-ai-kit-project-rules-docker/13-SKILL-JUDGE.md
  modified:
    - README.md
    - .planning/phases/13-docker-rules-checker-ai-kit-project-rules-docker/13-CONTEXT.md

key-decisions:
  - "Limits reconciliation resolved to EIGHT total (seven required, 1-6 and 8, plus the conditional seventh): 13-02-SUMMARY.md explicitly records the flow-mapping gap as 'confirmed to have survived into the shipped parser' and states plainly 'Plan 13-04 needs a seventh SKILL.md limit for it,' using the required hyphenated token verbatim."
  - "Skill-judge gate cleared without any fix-loop iteration: 103/120, 0 Critical, 0 Important -- well past the 96/120 alternative bar, so all eight Limits statements and the two-subcommand statement needed no defense against a judge-driven softening pass."
  - "Naming-analyzer verdict: CONFIRMED, no rename. D-D20's downstream dependencies (REQ-rules-docker, ROADMAP Phases 13-15, Phase 15 SC1) were named explicitly rather than assumed."
  - "13-CONTEXT.md sweep found 4 additional stale statements beyond D-D22's floor of 5 (9 corrections total): a duplicate 'no Docker setup' scouting claim in Reusable Assets, a second stale precedent citation inside D-01's own rationale text, and an Established Patterns bullet pointing at the wrong module for .pre-commit-config.yaml parsing."

patterns-established:
  - "Skill-judge as a mandatory phase-closing code-review gate (not planning-time) for any phase that creates or substantially rewrites a SKILL.md, with committed, byte-identity-checkable evidence naming the exact judged commit."

requirements-completed: [REQ-rules-docker]

coverage:
  - id: D1
    description: "SKILL.md exists, frontmatter name matches directory basename, description routes apart from all four siblings including the Makefile sibling's overlapping docker-* target opinion, and states all five categories/ten issues/two real subcommands/hardcoded baseline/eight limits"
    requirement: "REQ-rules-docker"
    verification:
      - kind: command
        ref: "SKILL-SHAPE-OK, DOC-MATCHES-CODE-OK, TWO-SUBCOMMANDS-OK, LIMITS-RECONCILED-OK, README-ROW-OK"
        status: pass
    human_judgment: false
  - id: D2
    description: "/skill-judge run against the finished SKILL.md as this phase's code-review gate; zero Critical/Important findings or score >=96/120; no-baseline claim verified by history search; reproducible evidence committed"
    requirement: "REQ-rules-docker"
    verification:
      - kind: command
        ref: "JUDGE-GATE-OK, EVIDENCE-CURRENT-OK"
        status: pass
    human_judgment: false
  - id: D3
    description: "/naming-analyzer run as pipeline confirmation; name unchanged; downstream dependencies named explicitly; 13-CONTEXT.md carries at least five dated append-only corrections from a full re-read sweep"
    requirement: "REQ-rules-docker"
    verification:
      - kind: command
        ref: "CORRECTIONS-OK"
        status: pass
    human_judgment: false

duration: ~1h 10min
completed: 2026-09-14
status: complete
---

# Phase 13 Plan 04: SKILL.md, Registration, Skill-Judge Gate, Naming Confirmation, and Context Sweep Summary

**Wrote `skills/ai-kit-project-rules-docker/SKILL.md` (making the skill installable for the first time), registered it in README.md, cleared the `/skill-judge` code-review gate at 103/120 with zero Critical/Important findings and no fix-loop iterations needed, confirmed the skill's name via `/naming-analyzer`, and swept `13-CONTEXT.md` for stale claims, landing nine dated append-only corrections.**

## Performance

- **Duration:** ~1h 10min
- **Tasks:** 3
- **Commits:** 3 (measured: `git rev-list --count 2d8f58d..HEAD`)
- **Files modified:** 4 (2 created, 2 modified) across the three tasks

## Environment recovery before Task 1

This worktree's base (`b30c0b2`) predated plans 13-01/13-02/13-03's merge to `main` (`2d8f58d`) --
the docker skill directory did not exist yet in this worktree. Confirmed
`git merge-base --is-ancestor HEAD main` succeeded, then fast-forwarded
(`git merge --ff-only main`, `b30c0b2` -> `2d8f58d`). Recorded as `plan_head_before` in this
SUMMARY's frontmatter (also `actuals.plan_head_before`), the same recovery pattern 13-03 recorded
for the same reason.

## Accomplishments

- `skills/ai-kit-project-rules-docker/SKILL.md` (251 lines): all five finding categories and ten
  issue names re-derived from the committed checker modules, both real subcommands (`check`/
  `remediate`) with their real output shapes and the deliberate absence of a third, the hardcoded
  baseline (eight-target family, three healthcheck bounds, conforming `depends_on` condition,
  per-stack hot-reload marker table), and all eight honesty-about-limits statements -- the skill
  becomes installable for the first time in this phase.
- `README.md`: exactly one new row for the skill, worded and placed consistently with its four
  siblings.
- `.planning/phases/13-docker-rules-checker-ai-kit-project-rules-docker/13-SKILL-JUDGE.md`: the
  `/skill-judge` gate evidence (103/120, 0 Critical, 0 Important, 0/3 fix iterations used), the
  naming-analyzer verdict, and the five ROADMAP Phase 13 success-criteria discharge pointers.
- `.planning/phases/13-docker-rules-checker-ai-kit-project-rules-docker/13-CONTEXT.md`: 9 dated,
  append-only corrections from a full re-read sweep (the D-D22 floor of 5, plus 4 more this sweep
  surfaced), every original word preserved.

## Task Commits

1. **Task 1: Write SKILL.md and register in README** - `df6bbf0` (feat)
2. **Task 2: Run /skill-judge code-review gate, commit evidence** - `3be221a` (docs)
3. **Task 3: /naming-analyzer confirmation and 13-CONTEXT.md stale-line sweep** - `d76211c` (docs)

## Files Created/Modified

- `skills/ai-kit-project-rules-docker/SKILL.md` - the skill document (new)
- `README.md` - one new skill-table row
- `.planning/phases/13-docker-rules-checker-ai-kit-project-rules-docker/13-SKILL-JUDGE.md` - skill-judge evidence, naming-analyzer verdict, ROADMAP SC pointers (new)
- `.planning/phases/13-docker-rules-checker-ai-kit-project-rules-docker/13-CONTEXT.md` - 9 append-only corrections

## The LIMITS section, quoted VERBATIM from `SKILL.md` (final, unmodified -- no fix-loop iteration changed any wording)

> 1. **The applicability gate is root-scoped.** This skill evaluates a repo only when root-level
> Docker evidence exists, and reports nothing otherwise. A repo whose Docker assets live only
> below the root -- ai-kit's own CI-only `tests/e2e/docker/Dockerfile` is the live example -- is
> not evaluated at all.
> 2. **The compose reader is a text parser, not a YAML implementation.** Compose files are read
> with an indentation-aware stdlib scan, never a YAML library. A TAB-indented file (invalid YAML)
> may be mis-attributed to the wrong service rather than rejected outright.
> 3. **Healthcheck bounds cover DECLARED values only.** An absent `interval` inherits Compose's own
> 30s default, which exceeds this skill's 5s bound, and is NOT flagged; a service with no
> `healthcheck:` block at all is NOT flagged either. This is the limit most likely to read as a
> bug to a user who knows Compose's own defaults, so it is stated rather than left to be
> discovered.
> 4. **Hot-reload stack attribution is REPO-WIDE, not PER-SERVICE.** The override command is
> resolved against the union of every stack detected anywhere in the repo, because a compose
> service definition carries no per-service language signal of its own. In a polyglot repo, a
> Node dev server can therefore satisfy a Python service's command line.
> 5. **The hot-reload marker baseline is hardcoded and will go STALE.** The per-stack table above is
> knowledge that ages, which is exactly why an override this skill does not recognize produces an
> ADVISORY finding with a named reason rather than a confident defect claim -- an unrecognized
> tool is not an accusation.
> 6. **No local-dev compose file means no hot-reload finding at all.** The hot-reload check's
> subject is the local-dev service definition; a repo that does local development straight from
> its base compose file, with no `docker-compose.override.yml`/`docker-compose.local.yml`
> present, is not evaluated for the hot-reload convention.
> 7. **Same-line flow-mapping compose bodies are unread.** `healthcheck: {interval: 30s}` and
> `depends_on: {db: {condition: service_healthy}}` are valid Compose forms the block-indentation
> parser does not read, so a service written this way is neither flagged nor confirmed
> conforming for that block. This is a stated reader gap, not a silent mis-parse: the parser
> never lets a flow-mapping value swallow the block boundary of the service defined after it.
> 8. **Long-form (mapping-style) volume entries are unread.** A local-dev service that declares its
> mounts as a `volumes:` sequence of mappings (`- type: bind` / `source:` / `target:`), rather
> than the short form `./src:/app/src` this skill reads, is reported as NOT CONFIRMABLE -- an
> advisory naming the reason `volumes_unreadable` -- rather than flagged as missing the
> convention or confirmed conforming. This skill reads only the short-form entry.

No wording change occurred: Task 2's `/skill-judge` run scored 0 Critical and 0 Important findings
on the first pass (no fix-loop iteration ran), so there is no "before text" to quote beside any
limit -- the text above is identical to what Task 1 committed and what Task 2's evidence file
already quotes.

## Limits reconciliation

**Limit 7 (conditional, flow-mapping):** `13-02-SUMMARY.md`'s "The flow-mapping limit, in
`SKILL.md`-ready wording" section states: *"Same-line **flow-mapping** bodies (`healthcheck:
{interval: 30s}`, `depends_on: {db: {condition: service_healthy}}`) are NOT read by this
parser... **This limit is real and confirmed to have survived into the shipped parser** -- it did
NOT get closed. Plan 13-04 needs a seventh `SKILL.md` limit for it."* Resolved: the gap survived,
so `SKILL.md` states **eight** limits total (seven required + the conditional seventh), carrying
the exact hyphenated token `flow-mapping`. A silent seven would have been the document
overclaiming coverage against what the shipped parser actually does; that was avoided.
`LIMITS-RECONCILED-OK` prints `eight`.

**Limit 8 (required, mapping-style):** `13-03-SUMMARY.md`'s "The THREE limits this check carries"
section states: *"Long-form (mapping-style) volume entries are not read... reported as advisory,
not-confirmable (`volumes_unreadable`)... This is a descope decided in cycle-2 review finding 1,
not an unfinished edge."* This is REQUIRED rather than conditional per D-D19 clause 8 (13-03
descoped it deliberately at planning time, so there is nothing to reconcile at execution time --
only to confirm the wording matches). `SKILL.md`'s limit 8 matches this SUMMARY's own wording and
carries the required hyphenated token `mapping-style` verbatim. No divergence found.

## Skill-judge result

- **Rubric as installed** (read in full before scoring, `/home/bazzite/.claude/skills/skill-judge/SKILL.md`):
  8 dimensions, 120 points total -- D1 Knowledge Delta (20), D2 Mindset + Procedures (15), D3
  Anti-Pattern Quality (15), D4 Specification Compliance (15), D5 Progressive Disclosure (15), D6
  Freedom Calibration (15), D7 Pattern Recognition (10), D8 Practical Usability (15). Unchanged
  from Phases 9-12's own recorded rubric -- no difference to report.
- **Score:** 103/120 (85.8%, grade B). Per-dimension: D1 18/20, D2 9/15, D3 13/15, D4 14/15, D5
  13/15, D6 14/15, D7 9/10, D8 13/15. Full per-dimension evidence in `13-SKILL-JUDGE.md`.
- **Critical:** 0. **Important:** 0. **Fix iterations used:** 0/3 -- the score cleared the 96/120
  alternative bar with room to spare, so no fix-loop iteration was needed and none of the four
  binding fix-loop constraints (Task 1's verify chain, the documented output shapes, every limit,
  the two-subcommand statement) were ever exercised.
- **Judged commit:** `df6bbf0b3cb244fa969016ee81b386673f4b5cc5` (Task 1's own commit).
- **No disagreement recorded** -- no finding pressed against any limit or the two-subcommand
  statement, so there was nothing to defend or concede.
- **No-baseline claim, exact commands run and their output:**
  ```
  /usr/bin/git log --all --follow --oneline -- skills/ai-kit-project-rules-docker/SKILL.md
  ```
  Output: exactly one line, `df6bbf0 feat(13-04): write SKILL.md for ai-kit-project-rules-docker
  and register in README` -- Task 1's own commit, nothing before it.
  ```
  /usr/bin/git log --all --diff-filter=A --name-only --pretty=format:%H -- '**/SKILL.md'
  ```
  (filtered for any added path containing "docker") -- exactly one match:
  `skills/ai-kit-project-rules-docker/SKILL.md`, added once, by `df6bbf0`. No pre-split combined
  skill (traced across Phases 9-12's own evidence files) ever covered this domain either.

## Naming-analyzer verdict

**NAMING_VERDICT: confirmed** -- `ai-kit-project-rules-docker` is kept as-is, no rename applied.

`/naming-analyzer` was run against the directory name, given the four sibling names, this skill's
actual scope (local-dev Docker Compose conventions only -- never general Dockerfile linting,
image-security scanning, or running any container), and the fact that the family scheme is
user-decided. Applying the analyzer's own decision framework: NOT vague ("docker" is unambiguous
in this family position); a misleading-name tension NOTED but not severe enough to warrant a
rename (the skill's real scope is narrower than "docker" alone suggests -- the same shape of
tension the `arch` and `makefile` siblings' own evidence files already recorded, where the
description and Limits section carry scope-depth, not the name); NOT mis-abbreviated ("docker" is
the full, correct word); exact family-convention match; 27 characters, comfortably under the
64-character limit. Full analysis in `13-SKILL-JUDGE.md`'s "Naming-analyzer verdict" section.

**Per D-D20, the name is fixed and this task did not change it** even though the verdict is
"confirmed": `REQUIREMENTS.md`'s `REQ-rules-docker`, `.planning/ROADMAP.md` Phases 13, 14 and 15,
and Phase 15's own Success Criterion 1 (which enumerates the six checkers by this exact family
naming scheme) all name this domain literally. A rename here would be a multi-phase edit that
also changes an already-shipped installer entry (Task 1 already registered
`ai-kit-project-rules-docker` in README.md and made it installable).

## Category/issue table -- code agreement check

No disagreement found. The five categories (`docker-target-family`, `docker-local-runbook`,
`docker-healthcheck-bounds`, `docker-depends-on`, `docker-hot-reload`) and all ten issue names
were re-derived directly from `docker_checker.py`, `healthcheck.py`, `depends_on.py`, and
`hot_reload.py` before being written into `SKILL.md`, and `DOC-MATCHES-CODE-OK` confirms the
document's category set is a superset of what a live fixture run actually returns (`{'docker-
local-runbook', 'docker-target-family'}` for the smallest applicable fixture, both present in the
document).

## `13-CONTEXT.md` corrections -- full sweep, not two spot fixes

Re-read `13-CONTEXT.md` in full (all six top-level sections: Phase Boundary, Implementation
Decisions, Canonical References, Existing Code Insights, Specific Ideas, Deferred Ideas). Found
**9 stale statements** total -- D-D22's floor of 5, plus 4 more this full re-read surfaced:

1. **Reusable Assets -- `stack_cache.py`** (D-D22 known #1). `detect_stacks` landed in
   `stack_detect.py`; `stack_cache.py` is the unrelated generic per-skill cache helper this skill
   does not use.
2. **Phase Boundary -- "no `docker-compose.yml`/`Dockerfile` today"** (D-D22 known #2). True at
   the root and of the local-dev workflow, but the repo carries a CI-only
   `tests/e2e/docker/Dockerfile` behind `e2e-docker` -- exactly the pair of edges 13-01's
   root-scoped gate is shaped around.
3. **Header `**Status:**` line -- "BLOCKED on Phases 9-12"** (D-D22 known #3, part 1). Phases
   9-12 have all since landed.
4. **Phase Boundary -- "NONE of Phases 9-12 have a plan or execution yet"** (D-D22 known #3, part
   2). Same correction as #3, at its second location.
5. **Existing parsing precedent -- deleted path/underscore-prefixed names** (D-D22 known #4).
   Converged into `skills/_shared/ai_kit_rules_common/precommit_parse.py`, block reader now
   public (`iter_precommit_hook_blocks`).
6. **Integration Points -- "D-05 adds a new category"** (D-D22 known #5, the most dangerous one).
   Plan 13-03 deliberately did NOT; `HOT_RELOAD_TOOLS` sits beside the taxonomy and never reaches
   `TOOL_CATEGORY_INDEX`.
7. **(Additional, found by the full re-read) D-01's own rationale text** -- the SAME stale
   path/helper-name citation as correction 5 appears a second time, inside the D-01 decision's own
   rationale paragraph (not only in the "Existing parsing precedent" canonical-refs section).
8. **(Additional) Reusable Assets' own "no Docker setup" restatement** -- a second, independent
   occurrence of the same "ai-kit's own repo has no Docker setup" scouting claim (separate from
   the Phase Boundary paragraph), needing its own note for the same CI-only-Dockerfile reason.
9. **(Additional) Established Patterns -- `makefile_checker.py`'s `.pre-commit-config.yaml`
   handling.** Stale: the live `makefile_checker.py` (in `ai-kit-project-rules-makefile`) checks
   Makefile target shape and does not parse `.pre-commit-config.yaml` at all; that logic is in
   `precommit_parse.py` now.

Every correction's factual basis was re-verified live via this task's own precondition command
(`CORRECTION-BASIS-OK`) before being written -- none was copied from this plan's prose. No
additional stale statement beyond these 9 was found after the full re-read.

**Append-only diff proof** (pinned to this task's own commit `d76211c`, `<sha>^..<sha>` range,
never a relative anchor): **79 lines added, 0 lines removed.** `CORRECTIONS-OK` printed:
```
CORRECTIONS-OK 9 79 d76211cf
```

## ROADMAP Phase 13 success criteria -- discharge pointers

| SC | Description | Discharged by | Verify command |
|----|---|---|---|
| SC1 | `docker-*` target family flagged by name | 13-01-PLAN.md | `TestTargetFamilyDrivenFromTuple`; `APPLICABILITY-EDGES-OK 0 9` (re-run, passed) |
| SC2 | Healthcheck bounds 2s/10s/5s exceeded flagged, at-bound not | 13-02-PLAN.md | `HEALTHCHECK-OK 4 1` (re-run, passed) |
| SC3 | Bare-ordering `depends_on` flagged, `service_healthy` not, per-entry | 13-02-PLAN.md | `DEPENDS-ON-OK 7` (re-run, passed) |
| SC4 | Missing hot-reload convention flagged, bind-mount+override not | 13-03-PLAN.md | `HOT-RELOAD-OK ['anonvol', 'baked', 'mounted', 'namedonly', 'prodcmd', 'scripted'] 7` (re-run, passed) |
| SC5 | Absent `docker/local/README.md` flagged, present not | 13-01-PLAN.md | `TestRunbookPaired` (both methods, passing in the 536-test suite) |

## Decisions Made

See `key-decisions` in frontmatter. No architectural decisions were made in this plan -- it is
documentation-only, matching its own scope note (no Python source change of any kind, no rename,
no ROADMAP.md phase-entry edit beyond orchestrator bookkeeping).

## Deviations from Plan

None -- plan executed exactly as written. The environment-recovery fast-forward before Task 1
(documented above) matches the same explicit dispatch-prompt instruction 13-03 recorded, not a
plan deviation.

## Issues Encountered

`make validate` fails (exit 1), but ONLY on the same 25 findings across the same 4 pre-existing,
out-of-scope files STATE.md already names as deferred: `tools/status-line.py`, `tools/wizard_app.py`,
`tests/test_ai_kit_spec.py`, `tests/test_ai_kit_spec_superpowers.py`. None of these files were
touched by this plan -- confirmed by extracting every file path `ruff` cited across all three
task-boundary `make validate` runs.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- **This phase is CLOSED.** `skills/ai-kit-project-rules-docker/SKILL.md` exists and is
  installable; README.md carries its row; `13-SKILL-JUDGE.md` carries the skill-judge gate
  evidence, the naming-analyzer verdict, and the five ROADMAP SC discharge pointers;
  `13-CONTEXT.md` is fully swept.
- Plainly: this plan touched **no Python source, no test, and no gate-configuration file**. Only
  two Markdown documents were created, one Markdown table row was added, and one append-only
  sweep was made to a third Markdown document.
- The skill became installable for the first time in this plan -- the installer's skill-entry
  validator will symlink `skills/ai-kit-project-rules-docker/` into a user's real agent-CLI
  skills directory on their next install run.
- Phase 14 (`ai-kit-project-rules-cicd`) and Phase 15 (`ai-kit-project-rules-all`) both read
  `13-CONTEXT.md`; the corrected version no longer reads as blocked and no longer points either
  reader at a deleted path or an inverted catalog-integration claim.
- No blockers.

---
*Phase: 13-docker-rules-checker-ai-kit-project-rules-docker*
*Completed: 2026-09-14*

## Self-Check: PASSED

All created/modified files confirmed present on disk (4 files: 2 created, 2 modified, plus this
SUMMARY.md). All three commit hashes (`df6bbf0`, `3be221a`, `d76211c`) confirmed present in `git
log`.
