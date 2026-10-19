---
phase: 21-cursor-live-validation
plan: 04
subsystem: testing
tags: [cursor, cursor-agent, headless-smoke, runner, env-signal, detection]
requires:
  - phase: 21-01
    provides: Guarded cursor binary resolution (PATH scan for `agent`) that the runner mirrors
  - phase: 21-03
    provides: Cursor project-local gsd-core root, the cursor matrix host and the green local cursor smoke
  - phase: 21-07
    provides: Template-5 runner render whose `resolveBin` agrees with the Python resolver
provides:
  - Headless cursor smoke evidence on a real cursor host (21-SMOKE-CURSOR.md) with the one-attempt verdict line
  - A live-verified cursor env-signal label (`CURSOR_AGENT`) with its docstring bullet and test pin
  - The R1 input 21-05's label lift keys on
affects: [21-05, 21-06, 22-01]
actuals:
  tokens: 8415
  tasks: 2
  commits: 2
tech-stack:
  added: []
  patterns:
    - "One-attempt headless verdict: exactly one `headless verdict: green|red (attempt N: ...)` line, re-derivable from that attempt's status line, pgid spawn record, smoke log last line and ten passing steps"
    - "Path guard before every `rm -rf` of a recorded scratch path (anchored `/tmp` regex, directory, not a symlink, owned by the current user); a failed guard deletes nothing"
    - "Environ-matched reap: no `cursor-agent`/`worker-server` pid whose `/proc/<pid>/environ` names the scratch HOME survives the dispatch"
key-files:
  created:
    - .planning/phases/21-cursor-live-validation/21-SMOKE-CURSOR.md
    - .planning/phases/21-cursor-live-validation/21-04-SUMMARY.md
  modified:
    - skills/ai-kit-spec-review/ai_kit_spec/detection.py
    - tests/test_ai_kit_spec_runtimes_table.py
key-decisions:
  - "Take branch (A) of Task 2: `CURSOR_AGENT` was in the names-only list and the signals check read `signals clean`, so `_LABEL_CURSOR` became live-verified (Phase 21) headless, with TUI confirmation explicitly still pending."
  - "Keep the label's certainty at what a names-only headless dump supports: it names the env-dump source and the pending TUI step, and never claims a live subprocess inspection of the bundle."
  - "Use the install-directory version string (`2026.10.14-941492e`) in the label because that is the exact version string recorded in `## Session`; the version came from the directory name, never from invoking the CLI."
requirements-completed: [EVAL-07]
coverage:
  - id: D1
    description: A real cursor host session completed inventory, recommend, dry run and real apply on scratch projects through this repo's template-5 runner, with the protected real `~/.cursor` set unchanged.
    requirement: EVAL-07
    verification:
      - kind: other
        ref: "node .planning/scripts/cross-ai.mjs --prefer cursor --model-cursor composer-2.5 --mode exec --timeout 900 --outer-timeout 930 --no-preamble --child-pgid-file tmp/p21/headless/cursor-run1.pgid (see 21-SMOKE-CURSOR.md `## Headless runs`)"
        status: pass
      - kind: e2e
        ref: "python3 tests/gsd_curated_eval.py smoke --evidence-out tmp/p21/headless/cursor-smoke.md --artifacts-out tmp/p21/headless/cursor-artifacts (10/10 steps, `smoke exit=0`)"
        status: pass
      - kind: other
        ref: "python3 tests/gsd_curated_eval.py snapshot --check tmp/p21/plan04.before.json --scratch-root <work dir> -> snapshot ok"
        status: pass
    human_judgment: false
  - id: D2
    description: "`CURSOR_AGENT` detection is labelled live-verified (Phase 21) from the headless env dump, mirrored in the `detect_current_runtime` docstring and pinned by a test."
    requirement: EVAL-07
    verification:
      - kind: unit
        ref: tests/test_ai_kit_spec_runtimes_table.py#test_cursor_label_is_live_verified_headless
        status: pass
      - kind: unit
        ref: "python3 tools/run_unittest_parallel.py --group unit (43/43 modules)"
        status: pass
    human_judgment: false
  - id: D3
    description: SPEC R1's acceptance surface — the same flow driven by uz in the cursor TUI, including the TUI env-name listing that confirms the label beyond the headless dump.
    verification: []
    human_judgment: true
    rationale: "The interactive TUI run is uz's acceptance step (`21-INTERACTIVE-CURSOR.md`); the headless dump proves the pipeline and the signal's presence in cursor's own shell tool, not the TUI's own environment."
duration: 105min
completed: 2026-10-19
status: complete
---

# Phase 21 Plan 04: Cursor live validation Summary

**Headless cursor smoke green on a real cursor-agent host through the template-5 runner, and the `CURSOR_AGENT` detection signal upgraded from source-inspected-only to live-verified (Phase 21) with its docstring bullet and test pin.**

## Performance

- **Duration:** 105 min
- **Started:** 2026-10-18T22:42:46Z
- **Completed:** 2026-10-19T00:28:00Z
- **Tasks:** 2
- **Files modified:** 4 (2 created: the evidence file and this summary; 2 edited: `detection.py`, its table test)

## Accomplishments

- `.planning/phases/21-cursor-live-validation/21-SMOKE-CURSOR.md` records the headless iteration: session and runner argv, the runs table with the dispatch rule, exactly one `headless verdict: green (attempt 1: ...)` line, the names-only env section, the isolation-scope limit, process proof over every pgid file, the ten-step smoke body, planned-vs-baked and generated paths, the artifacts note, and the chain/runner notes.
- The dispatch ran `cursor-agent 2026.10.14-941492e` under a guarded scratch HOME (`CURSOR_CONFIG_DIR`, `XDG_CONFIG_HOME`, `XDG_CACHE_HOME`, `XDG_STATE_HOME` redirected; `XDG_DATA_HOME` deliberately not, because the CLI locates its own install there), reached the login only through a symlink, and tore the scratch home down after the path guard. `snapshot --check` proved the protected allowlist unchanged, including the strict `~/.cursor/cli-config.json` and `hooks.json` entries and the `agents`/`skills` name listings.
- Inside the host, the smoke passed all ten steps: host detected as `cursor`, both scratch projects installed gsd-core 1.17.0 locally at `<scratch-a>/.cursor/gsd-core` and `<scratch-b>/.cursor/gsd-core`, real apply plus second apply (0 writes, byte-identical, backups +1), forced-failure restore, the resolve-model-only chain (35 agents, no `-fast` models, baked files verified model-free), the 420-check matrix on the cursor host, and the protected set unchanged.
- `_LABEL_CURSOR` and its `detect_current_runtime` docstring bullet now read live-verified (Phase 21) via the headless env dump, names only, with TUI confirmation pending `21-INTERACTIVE-CURSOR.md` step 2; `test_cursor_label_is_live_verified_headless` pins the signal set, the label's wording, the absence of `source-inspected-only`, and the docstring/constant agreement.

## Task Commits

Each task was committed atomically:

1. **Task 1: Headless cursor smoke through this repo's runner, scratch-HOME isolation, evidence** — `cb05866` (docs: headless cursor smoke evidence)
2. **Task 2: Cursor env-signal label from the live names, with its docstring bullet, test pin and this SUMMARY** — this commit (`feat(21-04): cursor env signal live-verified from the headless cursor session`; resolve it with `git log --format=%h -1 --grep 'feat(21-04)'`)

_Note: the Phase 21 override commits this SUMMARY with the plan's last task instead of a separate "complete plan" commit, and a commit cannot contain its own sha, so both the evidence file and this summary point at the `git log --grep` lookup rather than a literal hash. Folding the summary into Task 2's commit was done with `git commit --amend --no-edit` on this dispatch's own unpushed commit, with the hooks running; the result is exactly the two commits the plan names. No orchestrator-owned planning file (`STATE.md`, `ROADMAP.md`, `REQUIREMENTS.md`) was edited._

## Files Created/Modified

- `.planning/phases/21-cursor-live-validation/21-SMOKE-CURSOR.md` — headless cursor evidence (created in Task 1; `## Label` filled in Task 2).
- `skills/ai-kit-spec-review/ai_kit_spec/detection.py` — `_LABEL_CURSOR` and the cursor bullet of `detect_current_runtime`.
- `tests/test_ai_kit_spec_runtimes_table.py` — `test_cursor_label_is_live_verified_headless` in `TestRuntimeTable`.
- `.planning/phases/21-cursor-live-validation/21-04-SUMMARY.md` — this summary.

## Verification

- Task 1 `<verify>`: all gates passed — evidence sections present, one verdict line re-derivable from attempt 1's own files (`status=no_change cli=cursor model=composer-2.5 exit=1 cli_rc=0` + `spawn` record + `smoke exit=0` + 10 `pass` steps), host detected, both scratch roots, resolve-model-only, `signals clean`, `XDG_STATE_HOME`, `template=5`, scratch-home path absent from the evidence, `cursor-agent invoked only by the runner`, eight artifacts with 35 non-fast resolved models and all-null baked map, `secret-scan` clean, no `$HOME` hit, `snapshot ok`, no scratch-HOME-matched process, every pgid empty.
- Task 2 `<verify>`, clause by clause after the commit: `pending Task 2` gone (pass); `## Label` present (pass); the branch/label/docstring consistency script printed `label consistent: UPGRADED` (pass); `secret-scan` clean over the evidence and this summary (pass); the `$HOME` grep found no real home path (pass); `git status --porcelain` is empty, so the tree is clean after the commit (pass). The one clause that does not pass is the plan's unittest gate shape — see Issues Encountered.
- Product/test runs: `python3 -m unittest tests.test_ai_kit_spec_runtimes_table tests.test_ai_kit_spec -k label -k docstring -k Runtime` (61 tests, OK); the two modules together end `Ran 755 tests … OK` with exit 0; `python3 tools/run_unittest_parallel.py --group unit` (43/43 modules); `make test` (unit 43/43, integration 4/4 and 8/8, e2e 45 passed/0 failed, arch 1/1, `rc=0`) — log kept at `tmp/p21/plan04-make-test.log`. The pi and codex docstring pins (`test_docstring_confidence_labels_for_pi_and_codex_thread_id`) pass untouched.

## Decisions Made

- Branch (A) of the label decision, because `tmp/p21/headless/cursor-env-names.txt` holds `CURSOR_AGENT` and `tmp/p21/headless/signals.txt` reads `signals clean`; the conditional stayed evidence-driven rather than upgrading on the bundle's source inspection alone.
- One product module (`detection.py`) plus its test in the Task 2 commit, per the plan's R8/D-04 routing: this was a planned certainty update, not a behavior fix, so no decimal phase was needed.
- Runner exit 1 on `status=no_change cli_rc=0` is recorded as healthy runner semantics for an evidence-only dispatch (the smoke writes only under gitignored `tmp/` and `/tmp`), with the host-written `smoke exit=0` as the independent proof.

## Deviations from Plan

None — both tasks ran as written. No auto-fixed product behavior, no re-scope, no second scratch attempt (attempt 1 was green).

**Total deviations:** 0. **Impact on plan:** none.

## Issues Encountered

- A first grep of the evidence candidates for the scratch-home path found a real `/tmp/p21-cursor-home.XXXXXX` path inside the runner's stderr; that stderr was redacted in the temporary evidence file before any commit, and the required `secret-scan`, `$HOME` and `p21-cursor-home` greps were then re-run against the committed file only (the committed evidence never carried it). Task 1's verify re-runs the scratch-path-absent gate for exactly this reason.
- Task 2's verify gates the two test modules with `python3 -m unittest … 2>&1 | tail -3 | grep -Eq '^OK( \(skipped=[0-9]+\))?$'`. That pipe cannot pass in this repo, and not because of a test failure: `tests/test_ai_kit_spec.py` writes to stdout (rendered policy TOML and cache paths), so the merged stream's last three lines are that output, not unittest's stderr summary. Reproduced identically in a detached worktree at `HEAD~1` (`e61bcfa`, i.e. the tree before this plan's label edit) — pre-existing, not introduced here. The underlying condition holds: the same two modules exit 0 and their stderr ends `Ran 755 tests / OK`. The plan's own parallel-group runs (which capture exit status, not a `tail` of merged output) are green, and the SUMMARY records the literal clause as the one non-passing gate rather than quietly substituting the corrected one.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- 21-05's label lift has its R1 input: the single `headless verdict: green (attempt 1: ...)` line, re-derivable from attempt 1's status line, spawn record, smoke log and ten steps.
- 21-06 can reuse the scratch-HOME layout, the pgid/environ reap proof and the archived-entry convention; 21-07's late teardown must re-apply the same path guard.
- Open, not a blocker for this plan: whether cursor-side GSD workflows pass the resolve-model result into a Task call is unverified (the chain note says so explicitly), and SPEC R1's interactive acceptance is uz's `21-INTERACTIVE-CURSOR.md` run.
- For 21-05: the label lift input is the single verdict line in `21-SMOKE-CURSOR.md`; the in-session skill-judge row stays the orchestrator's, and the `BLOCKED: in-session judge pending (orchestrator)` marker is the expected end state for an executor without the Skill tool.

---
*Phase: 21-cursor-live-validation*
*Completed: 2026-10-19*
