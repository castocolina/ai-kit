---
phase: 33-one-config-design
plan: 10
subsystem: config
tags: [config-toml, spec-config, skill-text, evals, migration, trust, lanes]

# Dependency graph
requires:
  - phase: 33-07
    provides: roster readers over config.toml [lanes] with the migration and the D-11 trust rule
  - phase: 33-09
    provides: render-toml guard, its refusal and migration lines, and the [lanes] writer this text describes
provides:
  - "ai-kit-spec-config SKILL.md describes config.toml, the migration, the replacement gate and the render-toml messages"
  - "references/config-file.md: layers, tables, roles, trust and the migration in one reference"
  - "evals in the seven-case shape; the stale-opencode fixture in the [[lanes.review]] shape"
affects: [33-11 (creates docs/config/design.md and the README section this text links to), 33-12 (loop 33 judges the changed SKILL.md)]

# Actuals (#2632): chars/4 over the realized diff (base c4a9096 .. HEAD before this SUMMARY)
actuals:
  tokens: 9130
  tasks: 3
  commits: 3

plan_head_before: c4a909602db4791c411634fb5687d24771d3f364
plan_head_after: 0f7cc93edf9b8dd9aa18c9c93c5287e173d5f357

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Every physical line of the skill folder that names review-spec.toml also says the file migrates (scope scan, zero unmarked hits)"

key-files:
  created:
    - skills/ai-kit-spec-config/references/config-file.md
  modified:
    - skills/ai-kit-spec-config/SKILL.md
    - skills/ai-kit-spec-config/references/check-only.md
    - skills/ai-kit-spec-config/references/cli-model-selection.md
    - skills/ai-kit-spec-config/evals/evals.json
    - skills/ai-kit-spec-config/evals/trigger-queries.json
    - skills/ai-kit-spec-config/evals/files/stale-opencode/config.toml
    - tests/test_ai_kit_spec_check_providers.py

key-decisions:
  - "The SKILL description is a double-quoted YAML scalar of 666 characters, so the ': ' inside it passes the strict frontmatter parser"
  - "config-file.md holds no decision ids and no dates, so tests/test_skill_text_history.py passes on the shipped reference"
  - "Step 4's local-write sentence says a file with no command-bearing lane needs no trust, matching the trust sentence the plan requires in the same step"

requirements-completed: []  # Orchestrator decides. The plan lists CFG-01, CFG-02, CFG-05, JDG-04. This plan writes the text for CFG-02 and CFG-05; CFG-01 needs the record (33-11); JDG-04 is loop 33 (33-12). Not marked here.

# Metrics
duration: unknown (the plan start time was not recorded in this run)
completed: 2026-11-15
status: complete
---

# Phase 33 Plan 10: spec-config text describes config.toml, roles, trust and the migration Summary

**ai-kit-spec-config's SKILL.md, its check-only and model-selection references and its evals now describe config.toml with role-keyed lanes, the D-11 trust rule and the review-spec.toml migration, backed by a new config-file reference and a seven-case evals file**

## Performance

- **Duration:** unknown (the plan start time was not recorded in this run)
- **Tasks:** 3
- **Commits:** 3 task commits; this SUMMARY commit follows

## Accomplishments

- SKILL.md: the description (quoted YAML, 666 characters) names `config.toml` and the migration; a pointer to `references/config-file.md` sits after the task paragraph.
- SKILL.md Step 2.1: an old `review-spec.toml` beside the target counts as an existing roster; the replacement gate names the migration and the recoverable `review-spec.toml.migrated` copy; only an explicit "replace" passes `--replace`.
- SKILL.md Steps 2.8, 3 and 4: `[lanes]` and `strategy`, the `lanes` JSON key, `render-toml` in place of `cfg_render_toml`, the lane-entry wording for timeouts and warnings, the meaning of the refusal and `migrated ... to ...` lines, and the trust sentence the plan requires.
- New `references/config-file.md` (67 lines): Layers, Tables, Roles, Trust, Migration from review-spec.toml, Files kept apart.
- `references/check-only.md`: reads `[[lanes.review]]` and `[[lanes.execute]]`, reports a pending old roster, probes with `--no-migrate`, and states the untrusted-file edge case as the plan requires.
- `references/cli-model-selection.md`: the three old-name mentions now name the `config.toml` roster or describe a migrated entry.
- Evals: the stale-opencode fixture is `git mv`'d to `config.toml` in the `[[lanes.review]]` shape; the seventh eval `edge-old-roster-migration-pending` is added; two prompts name `config.toml`; the trigger queries gain a migration query and name `config.toml`.
- `tests/test_ai_kit_spec_check_providers.py`: `test_skill_evals_have_six_cases` is now `test_skill_evals_have_the_seven_cases` and asserts the seven ids in order (C2-5).

## Task Commits

1. **Task 1: config-file reference and the SKILL.md write path** - `22ccedb` (docs; the staged-tests hook ran 4 modules, 4/4 passed)
2. **Task 2: check-only and model-selection references** - `4e5c9eb` (docs; the hook ran 4 modules, 4/4 passed)
3. **Task 3: evals in the new shape, fixture rename, renamed test** - `0f7cc93` (test; the hook ran 5 modules, 5/5 passed)

**Plan metadata:** this SUMMARY commit follows `0f7cc93`.

## Files Created/Modified

- `skills/ai-kit-spec-config/references/config-file.md` - new; the one reference for the config file.
- `skills/ai-kit-spec-config/SKILL.md` - description, pointer, Steps 2.1, 2.4-2.8, 3 and 4, and the NEVER trust bullet.
- `skills/ai-kit-spec-config/references/check-only.md` - raw read of `config.toml` lanes, `--no-migrate` probe, edge case (3).
- `skills/ai-kit-spec-config/references/cli-model-selection.md` - three old-name mentions.
- `skills/ai-kit-spec-config/evals/evals.json` - seven evals; prompts and assertions name `config.toml`.
- `skills/ai-kit-spec-config/evals/trigger-queries.json` - nine positive and eight negative queries.
- `skills/ai-kit-spec-config/evals/files/stale-opencode/config.toml` - renamed from `review-spec.toml` (git mv); content `[[lanes.review]]`.
- `tests/test_ai_kit_spec_check_providers.py` - the renamed eval-count test.

## Decisions Made

- The description is a double-quoted scalar with no `"` or `\` inside, so `tests/test_skill_frontmatter.py` accepts the `: ` in it.
- The reference states the trust rule and the migration in plain words, with no decision ids, dates or version numbers, so the skill-history test passes.
- The `[runner]` row in `config-file.md` names the table only. The `migrated_from` marker is not documented because no code in this tree writes it yet.

## Deviations from Plan

**1. [Forward reference - not changed] `docs/config/design.md` does not exist in this tree**
- **Found during:** Task 1 (before writing `config-file.md`)
- **Issue:** The plan has `references/config-file.md` say the design record `docs/config/design.md` lists each non-migrated file with its reason. `git ls-files docs/config` is empty in this worktree: Plan 33-11 creates that file, in a later wave.
- **Fix:** The sentence is written exactly as the plan states. It points at a file that appears when 33-11 merges. No test checks that the path exists.
- **Files modified:** `skills/ai-kit-spec-config/references/config-file.md`
- **Commit:** `22ccedb`

**2. [Plan anchor differs] Eval-count test line**
- **Found during:** Task 3
- **Issue:** The plan gives the test's HEAD lines as 322-325. In this tree `test_skill_evals_have_six_cases` is the method at line 353 of `TestSpecConfigStep`.
- **Fix:** Renamed and reasserted as the plan states; the only change in that module is the method body and name.
- **Commit:** `0f7cc93`

**3. [Wording beyond the plan's literal text] Step 4 local-write sentence**
- **Found during:** Task 1
- **Issue:** The plan's Step 4 trust sentence says a file with no command-bearing entry needs no trust, but the paragraph that says the local file "stays inactive until trusted" did not carry that qualifier.
- **Fix:** Added "(a file with no command-bearing lane needs no trust)" to that paragraph so the two sentences agree.
- **Commit:** `22ccedb`

**Total deviations:** 3 (1 forward reference left as the plan states, 1 anchor difference, 1 wording alignment). **Impact:** none on the tests. Deviation 1 resolves when 33-11 merges.

## Issues Encountered

- None blocking. The scope scan baseline was 19 unmarked lines; after Task 2 it was 3 (all in the evals, which Task 3 rewrites); after Task 3 it is 0.
- No test outside the plan's six pinned modules needed a change. The unit and arch groups (120 modules) pass on the final tree.

## Verification (run in this worktree)

Every test run went through `tools/run_unittest_parallel.py` with `AI_KIT_REFUSE_REAL_HOME=1` (through `tmp/p33/10/scope.py test` and `tmp/run-groups.sh`). No ai-kit-spec CLI, runner, roster read or live eval was run. The main checkout was not used as cwd.

| Command | Exit | Count line |
| --- | --- | --- |
| `python3 tmp/p33/10/scope.py test` (baseline, before any edit) | 0 | `6/6 modules passed`, `tests rc: 0` |
| `python3 tmp/p33/10/scope.py scan` (baseline) | 1 | `unmarked hits: 19` |
| `python3 tmp/p33/10/scope.py test` (after Task 1) | 0 | `6/6 modules passed`, `tests rc: 0` |
| `python3 tmp/p33/10/scope.py test` (after Task 2) | 0 | `6/6 modules passed`, `tests rc: 0` |
| `python3 tmp/p33/10/scope.py scan` (after Task 2) | 1 | `unmarked hits: 3` (the evals lines Task 3 rewrites) |
| `python3 tmp/p33/10/scope.py test` (after Task 3) | 0 | `6/6 modules passed`, `tests rc: 0` |
| `python3 tmp/p33/10/scope.py scan` (final) | 0 | `unmarked hits: 0` |
| `python3 tmp/p33/10/scope.py test` (final) | 0 | `6/6 modules passed`, `tests rc: 0` |
| `bash tmp/run-groups.sh` (unit and arch groups) | 0 | `120/120 modules passed`, `groups rc: 0` |
| `rg -n "cfg_render_toml" skills tests` | 1 | no match |
| `git ls-files skills/ai-kit-spec-config/evals/files/stale-opencode` | 0 | `skills/ai-kit-spec-config/evals/files/stale-opencode/config.toml` only |
| `rg -c "def test_skill_evals_have_" tests/test_ai_kit_spec_check_providers.py` | 0 | `1` |

Size checks (`tmp/p33/10/actuals.py`): description value 666 characters (limit 1024), quoted at both ends; `config-file.md` 67 lines (minimum 40).

The plan's `skill-judge` run is not part of this plan (Plan 12's loop 33). Not run here.

## Known Stubs

None.

## Threat Flags

None beyond the plan's threat model. T-33-27 is mitigated by the trust sentence in SKILL.md Step 4, the NEVER bullet about `trust-local` (kept), and the Trust section of `config-file.md`, which states exactly which edits drop trust.

## Self-Check

- Created files exist: `skills/ai-kit-spec-config/references/config-file.md`, `.planning/phases/33-one-config-design/33-10-SUMMARY.md`.
- Task commits are ancestors of HEAD: `22ccedb`, `4e5c9eb`, `0f7cc93`.
- Ledger base `c4a9096` is the parent of `22ccedb`; `commits: 3` was measured with `git rev-list --count c4a9096..HEAD` before this SUMMARY commit.

## Self-Check: PASSED

---
*Phase: 33-one-config-design*
*Completed: 2026-11-15*
