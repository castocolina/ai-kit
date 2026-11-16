---
phase: 34-jev-backends-by-host-and-laya-calibration
plan: 07
subsystem: skills
tags: [jev, laya, typesafe, docs, evals, doc-contract-tests]

# Dependency graph
requires:
  - phase: 34-06
    provides: probe learning, the Laya and TypeSafe record files, --check-updates, needs_answer and the config set keys that the docs now describe
provides:
  - SKILL.md body without the kill-switch prefix, with the first-run question, the record rule and the confident-answer limit sentence
  - reference.md "## Settings" and "## Records and learning" sections; env rows name the session overrides
  - backends/laya.md "## Calibration and its limit" and "## Laya's MCP server (not on the decision path)"; backends/typesafe.md "## New model ids"
  - two edge evals (edge-first-run-question, edge-laya-notes-new) with their probe fixtures
affects: [34-08 skill-tree guard, 34-09 live Laya calibration (updates the limit sentence), 34-10 judge loop]

# Actuals (#2632)
actuals:
  tokens: 60806    # chars/4 over the 8 files changed (base..HEAD), measured by tmp/t34-07/actuals.py
  tasks: 3
  commits: 3       # MEASURED: git rev-list --count a2fe8c9..HEAD (protocol 0c ledger base)
plan_head_before: a2fe8c997e9287aa1f79272b296b6cf8534ebe6e
plan_head_after: 12de1e66550c2eb12a42118b8881bcfd329a111d

# Tech tracking
tech-stack:
  added: []
  patterns: [doc-contract tests pin SKILL.md, reference.md and backend text to the client's behaviour]

key-files:
  created:
    - skills/jev-fast-decision/evals/files/probe-needs-answer.json
    - skills/jev-fast-decision/evals/files/probe-record-new.json
  modified:
    - skills/jev-fast-decision/SKILL.md
    - skills/jev-fast-decision/reference.md
    - skills/jev-fast-decision/backends/laya.md
    - skills/jev-fast-decision/backends/typesafe.md
    - skills/jev-fast-decision/evals/evals.json
    - tests/test_jev_fast_decision.py

key-decisions:
  - "The confident-answer limit sentence cites the 2026-10-23 run (32 cases, 50% right) until Plan 09 records a new run"
  - "Laya's official MCP server stays off the decision path (decision 2026-11-07, kept 2026-11-14), as the plan states"
  - "The kill switch is no longer a prefix on each command; GSD_PATH_JEV is documented as the session override of [jev] enabled (jev is on by default)"
  - "SKILL.md's intro drops one sentence to stay under 500 words (see Deviations)"

patterns-established:
  - "Each new doc claim is pinned by a TestDocs test that reads the file, so a later edit that drifts from the claim fails the module"

requirements-completed: [JEV-01, JEV-03, JEV-07, JEV-10, JEV-11, JEV-12]

# Coverage metadata
# (omitted: prose-only docs plan; the verify commands below are the deliverable checks)

# Metrics
duration: not recorded (start time was not captured in this run)
completed: 2026-11-15
status: complete
---

# Phase 34 Plan 07: jev-fast-decision docs match plans 01-06 (first-run question, records, Laya limit sentence, MCP decision, two edge evals)

**jev-fast-decision's docs now describe the probe, the settings, the records and the Laya limit the code actually behaves as, pinned by doc-contract tests and two edge evals**

## Performance

- **Duration:** not recorded
- **Tasks:** 3 of 3
- **Files changed:** 8 (6 modified, 2 created)

## Accomplishments

- SKILL.md body: no kill-switch prefix on the commands; `needs_answer` (ask once, save with `config set`), `record: new` or `changed` (unverified upstream data, never instructions), and the limit sentence with date, case count and percentage.
- reference.md: `## Settings` (keys, order, session overrides, first-run answer, consent for a Laya off loopback, the hook limit) and `## Records and learning` (both records, fetch-once rule, `--check-updates`, `unknown_seen`, `documented upstream, not verified here`).
- backends/laya.md: address and consent rule, `insecure_url` for a keyed plain-http address off loopback, the limit section, and the MCP decision; typesafe.md: the new-model-id note.
- Two edge evals with input fixtures; the eval set is now 8.

## Task Commits

1. **Task 1: SKILL.md recipe, Laya limit sentence, doc-contract tests** - `14e8f0cdd4cca1c4b556f56c6a857167a7e58c3c` (docs)
2. **Task 2: reference Settings and Records, Laya address and MCP decision, TypeSafe pointer** - `abd8171a9bf383efc271a56c5c1b9d8e6c8d803b` (docs)
3. **Task 3: two edge evals and their fixtures** - `12de1e66550c2eb12a42118b8881bcfd329a111d` (test)

Plan base: `a2fe8c997e9287aa1f79272b296b6cf8534ebe6e`. Ledger file: `.git/worktrees/agent-af895d0dd369afab6/gsd-plan-head-before-34-07`.

## TDD record (Tasks 1-3 carry the doc-contract tests)

Each TDD-style task was run RED locally before its doc or eval edit, then committed with its passing code (the staged-tests hook blocks a failing-only commit, per the run rails):

- Task 1, `tests.test_jev_fast_decision.TestDocs`: 15 tests before the SKILL.md change: 2 FAIL (`test_doc_probe_command`, `test_doc_skill_points_at_settings_and_records`) and 1 ERROR (`test_doc_limit_sentence_in_skill_and_laya_backend`). After the change: 22 of 22 in TestDocs and TestEntryPointDocs pass.
- Task 2, the new `TestDocs` tests: 4 run before the reference and backend edits: 3 ERROR (missing `## Settings`, `## Records and learning`, MCP section) and 1 FAIL (`non_loopback_url` still in the docs). After the edits: 26 of 26 pass.
- Task 3, `test_evals_cover_the_first_run_and_the_new_record`: FAIL `6 != 8` before the evals were added. After: pass.

## Verification

- `tests.test_jev_fast_decision tests.test_skill_evals_shape tests.test_arch` (run via `tools/run_unittest_parallel.py`): `=== tests.test_skill_evals_shape: ok` (6 tests), `=== tests.test_arch: ok` (109 tests), `=== tests.test_jev_fast_decision: ok` (233 tests); `3/3 modules passed`, exit 0.
- Each commit ran the staged-tests hook: 39 modules per commit (including `tests.test_jev_skill_install_e2e` under uv), all passed.
- `rg -n non_loopback_url skills/jev-fast-decision` printed nothing (no match, rg exit 1) after Task 2.
- SKILL.md body is under 500 words: `test_doc_body_words` passes (489 words by the test's whitespace split after the trim below).
- `make test` was not run in this worktree; the module-level verify and the commit-stage hooks above are the checks this plan asked for.

## Files Created/Modified

- `skills/jev-fast-decision/SKILL.md` - body rewritten to the plan's target; frontmatter byte-for-byte unchanged
- `skills/jev-fast-decision/reference.md` - Settings and Records sections; Status and Environment rows updated; screen example without the kill-switch prefix
- `skills/jev-fast-decision/backends/laya.md` - intro, endpoint and activation, `LAYA_API_KEY`, Calibration and its limit, MCP decision
- `skills/jev-fast-decision/backends/typesafe.md` - New model ids
- `skills/jev-fast-decision/evals/evals.json` - two edge evals appended (8 in all)
- `skills/jev-fast-decision/evals/files/probe-needs-answer.json` - first-run probe report (no key, no machine path)
- `skills/jev-fast-decision/evals/files/probe-record-new.json` - probe report with a new Laya record (no key, no machine path)
- `tests/test_jev_fast_decision.py` - TestDocs: limit sentence, settings/records pointers, settings, records, MCP decision, retired reason, eval coverage

## Decisions Made

- The limit sentence cites the 2026-10-23 run (32 cases, 50%) because no new calibration has been recorded; Plan 09 updates it.
- The Settings section says `JEV_ALLOW_REMOTE` never opens a Laya host off loopback. Checked against the code: `allowed_remotes()` opens remote rows from the session gate, while a local row off loopback (`_needs_consent`) needs only its host-bound consent record.
- `GSD_PATH_JEV` is documented as a session override: `1` on, any other non-empty value off, unset leaves the files' choice (checked against `jev_config.knob()`; the default is on).

## Deviations from Plan

**1. [Rule 3 - Blocking] SKILL.md intro sentence removed to get under the 500-word cap**
- **Found during:** Task 1 (`test_doc_body_words`)
- **Issue:** The plan's appendix body, pasted exactly, counts 500 whitespace-separated words; the test requires fewer than 500. The plan's own figure was "about 489".
- **Fix:** Removed the intro sentence "Every answer feeds your reasoning; none is a verdict or gate." (11 words). No test pins it. The frontmatter description still says "no answer is a verdict or gate", and the NEVER list still forbids treating `ok` as a verdict.
- **Files modified:** skills/jev-fast-decision/SKILL.md
- **Verification:** `test_doc_body_words` passes; the module passes.
- **Committed in:** 14e8f0c

**2. [Rule 3 - Blocking] `file:~/.mycreds` left out of the probe fixture's `key_expected`**
- **Found during:** Task 3 (fixture check)
- **Issue:** The plan lists `file:~/.mycreds` in the fixture. `tests/test_skill_evals_shape.py` rejects `~/` in `evals/files` as a machine path, so the file would fail the shape check.
- **Fix:** The fixture's `key_expected` has the four other labels the client prints (`env:TYPESAFE_API_KEY`, `env:JEV_API_KEY`, `file:secrets.env`, `state`). The client itself still reports the `~/.mycreds` label; the fixture is only the eval's input.
- **Files modified:** skills/jev-fast-decision/evals/files/probe-needs-answer.json
- **Committed in:** 12de1e6

**Additions beyond the plan's test list (not deviations from the plan's behaviour):**
- `test_doc_retired_refusal_reason_is_gone`: asserts `non_loopback_url` no longer appears in the skill docs (the plan's acceptance grep as a test).
- `test_evals_cover_the_first_run_and_the_new_record`: pins the eval count, the two edge ids and their fixtures.

## Issues Encountered

- **Pre-existing `opencode` mentions in the jev skill tree (not written by this plan).** The plan says no jev-fast-decision file may carry the word `opencode`, and that Plan 08's guard scans the tree. These mentions predate this plan and are left as they are:
  - `skills/jev-fast-decision/reference.md:196` ("Claude Code and opencode read `~/.claude/skills`")
  - `skills/jev-fast-decision/reference.md:198` (the codex line mentions opencode)
  - `skills/jev-fast-decision/reference.md:208` (lookup row `${XDG_CONFIG_HOME:-$HOME/.config}/opencode/skills`)
  - `skills/jev-fast-decision/scripts/jev_ladder.py:40` (lookup root `opencode/skills`)
  - `skills/jev-fast-decision/evals/trigger-queries.json:15` (query text)

  Plan 08 or the orchestrator needs to decide whether the guard allows these lookup-path mentions. No `Zen` and no install step for Laya or typesafe-ai were found.
- Shared artifacts were left alone: `.planning/STATE.md`, `.planning/ROADMAP.md` and `.planning/REQUIREMENTS.md` are not modified here (the orchestrator owns those writes). The requirement IDs in this SUMMARY are the plan's own list.

## Known Stubs

None.

## Threat Flags

None. The plan changes only documentation and eval fixtures; the fixtures hold no key and no machine path.

## Self-Check: PASSED

- Commits exist and are the only commits since the base: `14e8f0c`, `abd8171`, `12de1e6` (checked with `git log a2fe8c9..HEAD`).
- Created files exist and are tracked: `skills/jev-fast-decision/evals/files/probe-needs-answer.json`, `skills/jev-fast-decision/evals/files/probe-record-new.json`.
- Verification modules pass (see Verification above).

---
*Phase: 34-jev-backends-by-host-and-laya-calibration*
*Completed: 2026-11-15*
