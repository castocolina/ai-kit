---
phase: 21-cursor-live-validation
plan: 06
subsystem: validation
tags: [cursor, interactive-gate, host-rewrite, phase-gates, skill-judge, leak-proof]

# Dependencies for planning/execution (what this plan requires from what shipped before)
requires:
  # The harness this plan extends: a host rewrite on ~/.cursor/cli-config.json must be reportable
  # without demoting any other protected entry from strict to ignored.
  - "tests/gsd_curated_eval.py snapshot/smoke strict-vs-host-managed reporting (18-03/19-06, 21-04)"
  # The plan's exit criterion is "the gates pass on the final tree", so it needs 21-05's product work
  # (SKILL.md + tests) landed and digest-stable before the gates can be citable.
  - "skills/ai-kit-gsd-curated-config SKILL.md/tests amended by 21-05 (digest 85da5a6682d937c5)"
  # The interactive script re-runs exactly what 21-04 ran headlessly, so the run-script shape (spawn
  # pid, protected set, installer write scope) must already be proven.
  - ".planning/phases/21-cursor-live-validation/21-SMOKE-CURSOR.md ## Headless run (21-04)"
  # SPEC R1's "live run from the cursor host" sentence is the gate this plan writes for uz.
  - "SPEC R1 (interactive Cursor run) / R3 (host rewrite) + ROADMAP SC1, SC2, SC5"
# What this layer declares for downstream code/plans
provides:
  - "snapshot/smoke --host-rewrite <label> — an explicit, per-run exemption with `changed (host-rewrite)` reporting in the snapshot line, the smoke detail and the evidence template; strict-vs-exempt behaviour pinned by six new tests"
  - ".planning/phases/21-cursor-live-validation/21-INTERACTIVE-CURSOR.md — the user-run Cursor TUI gate (four REQUIRED steps: login in the real TUI, read-only baseline + user-keys digest, the paste-able smoke command, post-run protected-set check; one OPTIONAL step: the ROADMAP SC5 per-call model probe)"
  - ".planning/phases/21-cursor-live-validation/21-SMOKE-CURSOR.md ## Interactive run — a pointer to that script plus the SPEC R1/SC5 split, replacing `pending: 21-INTERACTIVE-CURSOR.md`"
  - ".planning/phases/21-cursor-live-validation/21-SMOKE-CURSOR.md ## Phase gates — `test`, `validate`, `gate_scope`, `skill-judge`, `snapshot`, `secret scan`, `leak check` and `scratch home` lines with exit codes and durations, and the full gate logs under tmp/p21/gates/"
  - "the in-phase pyright correction (`promised_map` annotation) that makes `make validate` exit 0 on this tree"
# Collections this plan introduces or changes (empty = no new runtime id, skill name, category, etc.)
affects: [tests/gsd_curated_eval.py, tests/test_gsd_curated_eval.py, .planning/phases/21-cursor-live-validation]

# Key decisions carried forward for later phases in this subsystem
key_decisions:
  - "SPEC R1's live run from the cursor host is a human verification gate, not an executor step: this plan wrote and verified the script and stopped. No executor run can log in through a TUI, and running `cursor-agent` here would repeat the unauthorized-execution defect 21-04 recorded."
  - "`--host-rewrite` exempts one label for one invocation only. `_strict_files()` still protects `<home>/.cursor/cli-config.json` strictly for every run without the flag — a host rewrite is never allowed to become invisible by changing the protection."
  - "The skill-judge gate is recorded as NOT PASSED and the phase ends `human_needed`: the independent pi lane scores 114/120 strict against the floor Phase 20's final sets for this lane (in-session 109, pi 116), with 0 Critical/0 Important and both reports' `DIGEST` equal to the current digest. Whether that is variance (pi scored 114 on this skill in Phase 19 too) or regression is uz's call, not the executor's."
  - "The pyright failure this plan's `make validate` found is pre-existing (21-03's `_baked_chain` cursor branch, reproduced at `HEAD~1`) and was fixed in-phase rather than deflected: one dev-harness module, no product module, so no decimal phase under R8."
  - "No kill command appears in 21-INTERACTIVE-CURSOR.md — including its optional probe. The probe only lists newly appeared `worker-server` processes and labels each `probe-owned` or `unidentified` from its own `/proc/<pid>/environ`, leaving disposal to uz. Killing by name would hit the user's own Cursor IDE servers, which 21-04's kill audit already ruled out."
  - "Every gate line in `## Phase gates` cites this plan's own run (`tmp/p21/gates/*.txt`), never an earlier plan's number: plan04's `make test` and plan05's digest are cross-checked but re-run here because 'a gate passes only with the current run's exit code and duration' is the phase's standing rule."
  - "The user's real `~/.cursor/cli-config.json`, `~/.cursor/mcp.json` and `~/.codex/config.toml` were read only through the harness digest path (names/digests, values never printed), and no cursor/opencode/pi binary version was probed outside this plan's actions."

# Metrics
duration: 85min
completed: 2026-10-19
# Interfaces created/modified by this plan (functions, commands, files, CLI flags)
interfaces:
  created:
    - ".planning/phases/21-cursor-live-validation/21-INTERACTIVE-CURSOR.md"
    - "tests/gsd_curated_eval.py:snapshot --host-rewrite / smoke --host-rewrite (choices: <home>/.cursor/cli-config.json, value <label>)"
    - "tests/gsd_curated_eval.py:_split_host_rewrite / CURSOR_CLI_CONFIG_LABEL"
    - "changed (host-rewrite) <label> — snapshot line, smoke step detail and evidence-template wording"
  modified:
    - "tests/gsd_curated_eval.py:_snapshot_report/_cmd_snapshot/run_smoke/render_smoke_evidence/_cmd_smoke/main"
    - "tests/gsd_curated_eval.py:_baked_chain (promised_map type annotation — pyright gate fix)"
    - "tests/test_gsd_curated_eval.py (six new cases: four snapshot, two smoke)"
    - ".planning/phases/21-cursor-live-validation/21-SMOKE-CURSOR.md (## Interactive run filled, ## Phase gates appended)"
---

# Phase 21 Plan 06 Summary: Cursor interactive gate and phase gates

**Phase 21's gates all ran and are recorded with this run's exit codes — and the Cursor interactive gate is now an executable script for uz, with a `--host-rewrite` exemption so the host rewrite SPEC R3 actually produces stops being reported as a harness failure.**

## Objective

Plan 06's goal was Phase 21's end-to-end gate set plus the interactive Cursor run script SPEC R1 and
ROADMAP SC2 ask for: prove that the curated cursor config works live from the cursor host, that the
label wording is honest, and that no gate passed with weaker evidence than its own run. Two
obstacles drove the shape of this plan, and the plan text itself predicted both: a host rewrite of
`~/.cursor/cli-config.json` landing mid-phase would trip the protected-set gate, and the skill-judge
gate might not accept.

Tasks, in the order the plan fixed:

1. Implement: `tests/gsd_curated_eval.py` `--host-rewrite`, its tests, `21-INTERACTIVE-CURSOR.md`, and
   `21-SMOKE-CURSOR.md`'s `## Interactive run` pointer; verify; commit.
2. Verification: run the phase gates, append `## Phase gates` to `21-SMOKE-CURSOR.md`, and commit the
   plan's SUMMARY with it.

## Performance

- **Duration:** ~85 min (started 2026-10-19T00:18 +08; last gate log 01:43)
- **Started:** 2026-10-19T00:18:36+08:00 (`tmp/p21/plan06.start`, epoch 1792379916)
- **Completed:** 2026-10-19T01:43:00+08:00 (`tmp/p21/gates/validate.final.txt`, the last gate run on the final tree)
- **Tasks:** 2 of 2 (4 committed work items: harness + script, gate record, gate fix)
- **Files modified:** 4 (`tests/gsd_curated_eval.py`, `tests/test_gsd_curated_eval.py`,
  `21-SMOKE-CURSOR.md`, plus `21-INTERACTIVE-CURSOR.md` and this SUMMARY created)

## Accomplishments

| # | Work | Result | Commit |
|---|------|--------|--------|
| 1 | `--host-rewrite` exemption: `CURSOR_CLI_CONFIG_LABEL`, `_split_host_rewrite`, `changed (host-rewrite)` wording through the snapshot line, the smoke step detail and the evidence template, the `snapshot ok` gate, the flag on both subparsers (value `<label>`, `choices` that reject everything else) | implemented; **six** cases (`test_run_smoke_host_rewrite_filters_only_that_label`, `test_host_rewrite_flag_rejects_other_labels`, two snapshot-class strict cases, the reported-not-failed case and the host-managed-only-omits-`snapshot ok` case) pin reported-not-failed, strict-for-everything-else, exit `2` on any other label, and that `snapshot ok` never prints for a host-managed-only change. Targeted run: 97 tests OK; full module: 302 tests OK. `tests/gsd_curated_eval.py` is dev/test scaffolding, so no product-module rule applies and `test_gate_scope` stays green | `c4dba7f feat(21-06): snapshot/smoke --host-rewrite exemption; interactive cursor run script` |
| 2 | `21-INTERACTIVE-CURSOR.md` + `21-SMOKE-CURSOR.md ## Interactive run` | the script is phase-owned (matching 20-INTERACTIVE-CODEX.md's shape), four REQUIRED steps plus one OPTIONAL SC5 probe, with the digest one-liner, the `CURSOR_CONFIG_DIR` guard, the post-run protected-set check and the `--host-rewrite` form; every shell step is parseable (`bash -n`), the digest one-liner runs and prints only 64 hex, the flag was exercised on a synthetic home (exit `0` with `changed (host-rewrite)` + `snapshot ok`, exit `1` without it), and `21-SMOKE-CURSOR.md` now points at it instead of `pending: 21-INTERACTIVE-CURSOR.md` | `c4dba7f` (same logical change) |
| 3 | Phase gates: `make test`, the matrix loader-count equality, `make validate`, `tests.test_gate_scope`, `make e2e-docker`, the skill-judge acceptance check, the post-gate snapshot, secret scan and leak/scratch-home proofs | all recorded in `21-SMOKE-CURSOR.md ## Phase gates` with exit codes and durations and full logs under `tmp/p21/gates/`. Six of the eight recorded lines passed outright (`test`, matrix single-run, `validate`, `gate_scope`, `docker`, and the snapshot/secret/leak/scratch-home proofs); the skill-judge gate did not, and is recorded as such rather than smoothed over | `docs(21-06): phase gates` (this commit) |
| 4 | In-phase gate defect: pyright rejected `_baked_chain`'s `promised_map` | reproduced at `HEAD~1` (21-03's cursor branch), fixed by annotating `promised_map: dict[str, str \| None]`; `uv run pyright` now reports `0 errors, 0 warnings`, and the pyright hook is `Passed` in the gate log | `a3fab6d fix(21-06): annotate promised_map so the cursor None branch type-checks (gate fix)` |

## Execution notes

- The plan's `<verify><command>` for task 2 requires `make validate` to exit `0` with no `Failed` hook
  line, and the tree as handed to this plan could not produce that: five attempts stopped at
  `pylint ... Failed — files were modified by this hook` while pylint reported `10.00/10` with zero
  messages, because a **concurrent session** was rewriting its own Phase 21.1 plan files inside this
  same worktree while pre-commit hashed the tree (proved with an md5 manifest of every tracked file
  around a single hook run: `21.1-07-PLAN.md` was the only difference —
  `tmp/p21/gates/manifest-before-pylint.txt`, `manifest-after-pylint.txt`, `pylint-hook-output.txt`).
  The sixth attempt cleared
  pylint and exposed a real pyright defect; the seventh attempt was fully green (`exit=0`, eight
  `Passed` hook lines). Both causes are written into `## Phase gates` rather than presented as a
  clean first-run pass.
- **No deviation from the plan.** Nothing was reordered, no step was skipped, and no finding was
  reclassified as out of scope. The skill-judge gate's failure is reported as a failure, with the
  fix path spelled out — not as a pass, and not as an out-of-scope note.
- `cursor-agent` was not run by this executor at any point. Plan 21-04's finding stands, and its
  reason is in the script: the only thing a non-interactive executor attempt can produce is a
  "could not determine a Claude session ID" failure, while the host-side login state it would touch
  is the user's. Steps 1-4 of `21-INTERACTIVE-CURSOR.md` are uz's; step 5 is optional and
  non-destructive.
- No credential, no auth file and no token was read, listed, hashed, copied, printed or
  pattern-matched — the only `auth.json` handling in the script is `test -L`/`test ! -e`, and the
  only digest this plan printed is a hash of three user-owned config *keys*.

## Task Commits

Each task was committed atomically, with pre-commit hooks running on every one:

1. **Task 1: `--host-rewrite` exemption + tests + interactive script + evidence pointer** — `c4dba7f`
   (feat; the script and its harness are one logical change, as the plan sequences them)
2. **Task 2 gate fix: pyright `promised_map` annotation** — `a3fab6d` (fix; found by this plan's own
   `make validate` run, see `## Fixes`)
3. **Task 2: `## Phase gates` + this SUMMARY** — `docs(21-06): phase gates` (this commit)

## Files Created/Modified

- `.planning/phases/21-cursor-live-validation/21-INTERACTIVE-CURSOR.md` — created: the user-run
  SPEC R1 gate (four REQUIRED steps) plus the optional ROADMAP SC5 probe
- `.planning/phases/21-cursor-live-validation/21-SMOKE-CURSOR.md` — modified: `## Interactive run`
  pointer, and the appended `## Phase gates` record
- `.planning/phases/21-cursor-live-validation/21-06-SUMMARY.md` — created (this file)
- `tests/gsd_curated_eval.py` — modified: `CURSOR_CLI_CONFIG_LABEL`, `_split_host_rewrite`,
  `changed (host-rewrite)` reporting through `_snapshot_report`/`_cmd_snapshot`/`run_smoke`/
  `render_smoke_evidence`, the `--host-rewrite` flag on both subparsers, and the `promised_map`
  annotation in `_baked_chain`
- `tests/test_gsd_curated_eval.py` — modified: six cases pinning the exemption's semantics
- `tmp/p21/gates/*` — created (gitignored scratch): the gate logs this SUMMARY quotes

## Artifacts by task

### Task 1

- `tests/gsd_curated_eval.py` (flag + split + report + smoke + renderer + parser),
  `tests/test_gsd_curated_eval.py` (six cases),
  `.planning/phases/21-cursor-live-validation/21-INTERACTIVE-CURSOR.md`,
  `.planning/phases/21-cursor-live-validation/21-SMOKE-CURSOR.md`.

### Task 2

- `.planning/phases/21-cursor-live-validation/21-SMOKE-CURSOR.md` — `## Phase gates` (eight lines:
  `test`, `validate`, `gate_scope`, `skill-judge`, `snapshot`, `secret scan`, `leak check`,
  `scratch home`).
- `tmp/p21/gates/` — `test.txt`, `validate.txt` (plus `validate.attempt1/2/6.txt` kept as the record
  of why it took seven attempts), `matrix-loader.txt`, `docker.txt`, `digest-now.txt`,
  `skill-judge.txt`, `snapshot-plan06.txt`, `snapshot-plan04.txt`, `ps-final.txt`, and the
  contention proof: `manifest-before-pylint.txt` / `manifest-after-pylint.txt` (md5 of all 1,302
  tracked files around one pylint hook run — one line differs, another session's
  `21.1-07-PLAN.md`) plus `pylint-hook-output.txt` (the hook's own `10.00/10` output).

## Decisions Made

- The interactive Cursor run is a human verification gate: the script was written and verified, then
  handed to uz. Running `cursor-agent` here would repeat 21-04's unauthorized-execution defect and
  could only produce a session-ID failure.
- `--host-rewrite` is a per-run exemption printed as `changed (host-rewrite)`, never a downgrade of
  the strict entry: every run without the flag behaves exactly as 21-03/21-04 recorded.
- The skill-judge gate is recorded not-passed rather than talked around; see `## Issues Encountered`.
- The pyright defect found by this plan's gates was fixed in this plan (one dev-harness module), not
  deferred.

### Decisions Affected

**From SUMMARY-04 (headless run shipped, interactive run owned by uz):**

- `21-SMOKE-CURSOR.md ## Interactive run` → the placeholder is gone; the section now names the script
  and states the split: steps 1-4 are SPEC R1's acceptance, step 5 is the optional ROADMAP SC5 probe.
  Evidence: `c4dba7f`; the pointer text is the last lines of that section.

**From SUMMARY-05 (product amended; skill-judge unresolved by the orchestrator's own run):**

- `21-SMOKE-CURSOR.md ## Phase gates` → the `skill-judge` line is the phase's gate record and it says
  `gate not passed — UNRESOLVED (owner review)` with both rows' scores, both `DIGEST` lines equal to
  the current digest, the floor's provenance (Phase 20's finals — in-session 109, pi 116 — are this
  lane's floors), what uz must decide
  and the exact re-judge command. Evidence: `02375c0` for the rows, `tmp/p21/gates/digest-now.txt` +
  `tmp/p21/gates/skill-judge.txt` for the verification.
- Nothing in this plan's gates passed on weaker evidence than its own run: the earlier `gate_scope`
  number quoted in `## Headless run` was already corrected by 21-04's own addendum, and this plan
  cites `Ran 34 tests ... OK` from its own command.

**No gate passed with weaker evidence than its own run, and no finding was reclassified to make a
gate pass.** The one judgement call — treating the concurrent 21.1 writes as contention rather than
treating a pre-existing typing error as "out of scope" — went the other way: the typing error was
fixed here, and the contention was proved with a manifest diff instead of asserted.

## Gate outcomes

| Gate | Result | This run's evidence |
|------|--------|---------------------|
| `make test` | `exit=0` | `tmp/p21/gates/test.final.txt` on the final tree (and `test.txt` before the fix): 57 module `ok` lines, 4,396 tests, `43/43`+`1/1`+`4/4`+`8/8`+`1/1`, installer `45 passed, 0 failed`, no `FAILED` line |
| Matrix single-run | equal | `=== tests.test_ai_kit_gsd_curated_config_matrix: ok ... Ran 36 tests` (the only such line) == `module 36` in `tmp/p21/gates/matrix-loader.txt`; per-class `9/9/9/9` |
| `make validate` | `exit=0` | `tmp/p21/gates/validate.txt` (after 7 attempts): ruff, pylint, pyright, vulture, shellcheck, py-compile, `unittest (core)`, `unittest (wizard — uv)` all `Passed`; `tmp/p21/gates/validate.attempt*.txt` record the two causes; `tmp/p21/gates/validate.final.txt` re-runs it green on the final tree |
| `tests.test_gate_scope` | `OK` (34 tests) | this plan added no test module, so registration is unchanged |
| `make e2e-docker` | `exit=0` | `tmp/p21/gates/docker.txt`: podman clean-room, `matrix ran: 420 checks`, `protected set unchanged`, `e2e ok`, `==> ai-kit clean-room E2E: PASS` |
| skill-judge | **not passed** | verifier `exit=1` (`tmp/p21/gates/skill-judge.txt`): pi `CURRENT 114/120` < floor 116; in-session `110/120` ≥ 109; both `DIGEST 85da5a6682d937c5` == current, so not stale |
| Protected set | `snapshot ok` | `snapshot --check tmp/p21/plan06.before.json`; plan04 and plan05 baselines also `snapshot ok` |
| Secret scan / leak / scratch home | clean | `secret-scan` `exit=0`, `$HOME` grep `exit=1`; no process this phase started remains (the one match is in 21-04's pre-dispatch capture); all twelve `spawn <pid>` groups dead; scratch home `/tmp/p21-cursor-home.SysiYq` gone |

## Deviations from Plan

No task was skipped, reworded or reordered, and no scope was added. One issue was auto-fixed under
the plan's own gate rule:

**1. [Rule D-04/R8 — gate defect fixable in-phase] `make validate` failed on pyright**
- **Found during:** Task 2 (phase gates, `make validate` attempt 6)
- **Issue:** `tests/gsd_curated_eval.py` `_baked_chain` passed a `dict[str, None]`-inferred
  `promised_map` into `_baked_mismatches(..., promised_map: dict[str, str | None])`; pyright rejects
  it because `dict` is invariant in its value type. Reproduced at `HEAD~1`, so it is pre-existing
  (introduced by 21-03's cursor branch) — and it is reported as pre-existing rather than used as a
  reason to skip the gate.
- **Fix:** annotate `promised_map: dict[str, str | None]` once above the three branches (4 added
  lines, one comment block).
- **Files modified:** `tests/gsd_curated_eval.py` only — one dev-harness module, zero shipped product
  modules, so R8 keeps it in-phase instead of opening a decimal phase.
- **Verification:** `uv run pyright` → `0 errors, 0 warnings, 0 informations`; the pyright hook is
  `Passed` in `tmp/p21/gates/validate.txt` (`exit=0`); `tests.test_gsd_curated_eval` still `OK`
  (302 tests).
- **Committed in:** `a3fab6d` (its own fix commit, so the gate fix is separable from the feature).

The other gate-blocking condition was **not** auto-fixed because fixing it is outside this plan's
authority: the `UNRESOLVED` skill-judge verdict needs both judges re-run (an AI CLI this plan may not
run) — see `## Issues Encountered` and criterion 8 above.

No probe was dispatched (no unexplained `cursor-agent` process existed), so no
`cursor-probe*.pgid`/`cursor-probe*.md` artifact was created; the plan makes that conditional and
`21-SMOKE-CURSOR.md ## Phase gates` records it.

## Assessment

### Plan-level criteria

| # | Criterion | Status | Evidence |
|---|-----------|--------|----------|
| 1 | The `--host-rewrite` flag exists, and the tests prove the exempted label is reported not failed, everything else stays strict, `snapshot ok` still means every strict entry is unchanged, and a host-managed-only change still exits 1 | VERIFIED | six new cases in `tests/test_gsd_curated_eval.py`; `tests.test_gsd_curated_eval` 302 tests OK; `--help` greps for both subcommands; the flag was exercised on a synthetic home (exit `0` with `changed (host-rewrite)` + `snapshot ok`, exit `1` without) and rejects any other label with exit `2` |
| 2 | `21-INTERACTIVE-CURSOR.md` and the `## Interactive run` pointer exist and every shell step parses | VERIFIED | `bash -n` on all four extracted blocks; the digest one-liner runs exactly as written in the script (default dir, no `HOME` override) and prints a 64-hex digest — only its pattern match was counted here, never its value; the run/exit pairing, the `TMPDIR=/tmp` form, the post-run protected-set check and the optional probe are present; `secret-scan` `exit=0` on the phase dir |
| 3 | Task 1's `<verify>` block passes, including the `test`/`validate`-free harness greps | VERIFIED | run end-to-end at commit time and re-run after; `snapshot --help`/`smoke --help` contain `--host-rewrite`, the `host_rewrite`-class tests and `cursor_config_change_is_strict` are `ok`, the phase dir is secret-clean and carries no `$HOME` literal |
| 4 | `make test` exit 0, the matrix loader-count equality, and `make validate` exit 0 with no `Failed` hook, all logged under `tmp/p21/gates/` | VERIFIED | both re-run on the final tree, after the pyright fix and all doc edits: `tmp/p21/gates/test.final.txt` (`exit=0`, 57 module `ok` lines, 4,396 tests, single `Ran 36` matrix line equal to `matrix-loader.txt`'s `module 36`) and `tmp/p21/gates/validate.final.txt` (`exit=0`, all eight hooks `Passed`, 0 `Failed`); `test.txt`/`validate.txt` keep the earlier runs of the same gates |
| 5 | `make e2e-docker` exit `0` or `1` for a documented real-path failure, `tests.test_gate_scope` `OK`, the skill-judge gate evaluated at the current digest | PARTIAL | `docker.txt` `exit=0` (`==> ai-kit clean-room E2E: PASS`); `gate_scope` `Ran 34 tests ... OK`; the skill-judge gate was evaluated correctly (verifier `exit=1`, both rows' `DIGEST` == `85da5a6682d937c5`) but **did not pass** — recorded as `UNRESOLVED (owner review)`, pi 114 below the 116 floor |
| 6 | Post-gate snapshot `snapshot ok`; older baselines information-only; `secret-scan` over the phase directory clean and no phase artifact carries a home path or digest value; no `cursor-agent`/`worker-server`/`cross-ai`/`gsd_curated_eval` process or `spawn` process group started by the phase survives; the recorded scratch home gone or its failure state recorded | VERIFIED | `snapshot-plan06.txt`/`snapshot-plan04.txt` both `snapshot ok`; `secret-scan` `exit=0` and `$HOME` grep `exit=1` on the phase dir; `ps-final.txt`'s single line is also in `tmp/p21/headless/ps-before.txt`; all twelve recorded `spawn` groups empty; `/tmp/p21-cursor-home.SysiYq` gone and no `/tmp/p21-cursor-home.*` exists |
| 7 | No unexplained uncommitted change remains from this plan | VERIFIED | `git log` shows `c4dba7f`, `a3fab6d` and `docs(21-06): phase gates`; the only paths this plan touched are in those commits. The dirty `21.1-*` files belong to the concurrent session and were neither staged nor altered — see Environment findings |
| 8 | Task 2's `<verify><automated>` block exits 0 | **NOT MET — and bisected, not asserted** | run verbatim from the plan's `<automated>` (extracted into `tmp/p21/gates/verify-task2.sh`, `bash -x` trace in `tmp/p21/gates/verify-trace.txt`): it aborts at `! grep -rq 'pending (orchestrator)' …`, which matches one narrative line of the orchestrator's own `21-SKILL-JUDGE.md:39` quoting that rule, not a score row; behind it the verdict alternation offers only PASS+verifier, STALE or `BLOCKED: pi judge unavailable`, none of which is this state; and the final `test -z "$(git status --porcelain)"` reflects only other sessions' untracked
  `21.2`/`21.3` RESEARCH files after this plan's three commits land (`c4dba7f`, `a3fab6d`, and the
  docs commit this SUMMARY is in). Proof that the rest is genuinely green: with exactly those two judge clauses removed (`tmp/p21/gates/verify-task2-rest.sh` → `verify-trace-rest.txt`) the chain reaches the end and exits 0, and with the clean-tree clause also removed it exits `0` on this tree — so nothing was hidden behind a short-circuit |

### Goal-achievement (goal check)

Partially achieved. Every gate ran with its own exit code and duration, the protected set is proven
unchanged across the whole phase, and the artifact that gates Phase 21's ROADMAP SC1/SC2 claim is
written and verified — but Phase 21's end-to-end goal has two open items, neither of which an
executor can close: the interactive TUI run is uz's (the plan says so explicitly, and 21-04 proved
why an executor attempt cannot produce anything but a session-ID failure), and the skill-judge gate
did not pass (pi 114 against the 116 floor). The plan anticipated exactly this pair, which is why
its own exit criterion is "all gates pass or are recorded with the reason they cannot pass on
executor authority".

### Requirement fulfillment (Phase 21 requirements + phase completion)

- EVAL-07 (validate the curated cursor config live, headless **and** interactive): PARTIAL —
  headless proven by 21-04 and re-proved at the gate level here (matrix single-run, clean-room
  `e2e-docker` PASS, protected set unchanged); the interactive half is gated on uz's run of
  `21-INTERACTIVE-CURSOR.md`.
- SPEC-06 (the `session default — pending` wording): met at 21-05 (the description is the exact
  lifted wording) and pinned in the matrix test; the second half — removing the `pending` note from
  `21-CURATED-MODELS.md`'s cursor entry — happens only after uz's interactive run.
- AGT-01 (ship `cursor-agents/`): shipped at 21.1-02 with 21-03's live proof and 21-05's tests; the
  host-side linking + live delegation proof remains deferred to backlog 999.7 (AGT-02), unchanged.
- Phase 21 completion: **not complete.** `phase status: human_needed` — see the final line and
  Human verification below.

### Phase 31 cursor-entry completion

Not applicable to this plan. No `model-catalog.json` or `ai_kit/config_paths.json` entry gained,
lost or changed a `cursor` key here: this plan touches only the eval harness and Phase 21 planning
artifacts. The catalog's 295 entries and their cursor keys are unchanged from 21-05's state, and
the `python3 tests/gsd_curated_eval.py catalog-entries` gate (Phase 31's rule) stays green inside
`make test`.

### ROADMAP success criteria (phase-level)

| SC | Status | Evidence |
|----|--------|----------|
| SC1 — "live smoke run completes successfully from the cursor host on a scratch project" | PARTIAL — headless proven, interactive awaiting uz | headless: `21-SMOKE-CURSOR.md ## Headless run` (attempt 2 `exit=0`, `all 12 steps passed`, `matrix ran: 420 checks`, protected set unchanged, real-path installer). Gates here: `make test`/`make e2e-docker`/`snapshot ok`. Interactive half: `21-INTERACTIVE-CURSOR.md` steps 1-4, uz's run, `smoke exit=0` |
| SC2 — "cursor-agents label replaced by qualified wording; pending removed only with the interactive run" | PARTIAL — qualified wording shipped, `pending` removal awaiting uz | 21-05's `LIFT` branch is live in `21-CURATED-MODELS.md` (description `validated headless via cursor-agent in phase 21, pending session default + model catalog confirmation`; selector `not supported by the runtime`; note keeps `pending`); removal is gated on `21-INTERACTIVE-CURSOR.md` steps 1-4 |
| SC3 — "cursor-agent detected and enumerated even behind the shell wrapper" | MET | 21-01's resolver `sh -c '<node> …/index.js "$@"'` decoding (self-test `cursor wrapper alias resolves to the bare call`, `exec form stays inert`, `malformed exec value returns None`) plus 21-07's runner-template `resolveBin()` cases, which run through the template's `--self-test` under `tests.test_cross_ai_runner_e2e` (`ok in 108.3s  Ran 13 tests`) and the Python dispatch under `tests.test_ai_kit_spec_runner_dispatch` (`ok in 13.2s  Ran 59 tests`) in this plan's `make test` log |
| SC4 — "cursor-agents files shipped, pinned and tested" | MET | `skills/ai-kit-gsd-curated-config/cursor-agents/` (21-02), `TestCursorAgentsNaming` (21-03), `TestCursorAgentsParity` (21-05, 4 subTests) — all in `make test` above; the host-side linking + live delegation proof stays in backlog 999.7 (AGT-02) |
| SC5 — "native per-call model override verified live, or session-default-only label kept" | session-default-only branch pinned; per-call awaiting uz's optional probe | `native_selectors == ()` for cursor + `test_runtime_table_marks_cursor_installed_and_review_only` (pinned); `21-INTERACTIVE-CURSOR.md` step 5 is the optional per-call read-only probe — a pass there lets 21-05's `LIFT` branch replace the current wording with `validated live via cursor-agent`, `native per-call model override` and `cursor` in `enum_values`, with the same three-way `phase status: complete` / `requirement: REQ-02 pending decision` / `phase status: blocked` shape; a fail or an unfinished probe keeps the current wording |

## Issues Encountered

- **The skill-judge gate could not be closed by this executor, and that makes this plan's
  `<verify><automated>` block unable to exit 0.** The pi lane's strict score (114) sits two points
  under the floor Phase 20's final sets for this lane (116; in-session 109, met at 110), while both
  judges report 0 Critical/0 Important and both reports' `DIGEST` equals the current digest — so the
  state is real, current and `UNRESOLVED`, which this plan's own text says "fails the gate outright
  (a defect to fix in SKILL.md by the 21-05 fix loop, then the judge re-run)". That fix loop is not
  executable inside this plan: its task-2 action forbids running an AI CLI here (the pi re-judge is a
  `pi` dispatch), and editing `SKILL.md` first would re-key the digest and turn two byte-exact reports
  into `skill-judge: STALE (digest … != …) — gate not passed`, i.e. weaker evidence, not stronger —
  and AGENTS.md's skill rule will not let a materially updated `SKILL.md` be called complete without
  the very loop that cannot be run here. Under the same rule's other branch, work that needs both
  judges re-run is "a decimal phase recorded in the SUMMARY and inserted through the orchestrator".
  So the three ways to force the verify green were all rejected on purpose: write
  `## Verdict: BLOCKED: pi judge unavailable` (false — the judge ran, three rounds), write
  `skill-judge: PASS` (false — 114 < 116), or edit `SKILL.md` blind and re-judge later. Every other
  clause of that verify block is green in this run, each with its own line in `## Phase gates`. What
  uz must do: decide variance vs regression (`21-SKILL-JUDGE.md` states the same open question), and
  if regression, apply pi's §Findings items 1-4 and §Top 3 improvements to
  `skills/ai-kit-gsd-curated-config/SKILL.md`, then re-run both judges on the new digest — the exact
  command is in `21-SMOKE-CURSOR.md ## Phase gates`.
- **`make validate` cannot be trusted to run cleanly while another session holds this worktree.** A
  concurrent Phase 21.1 replan was writing and committing its own plan files in the same checkout for
  most of this plan (`dd741bd`, `5848872` on this branch; `git status` still shows `21.1-0N-PLAN.md`
  modified). pre-commit's modified-files check hashes the whole tree, so its long pylint hook reported
  `Failed — files were modified by this hook` on those writes even though pylint itself was clean. The
  mitigation used here was to retry until the other session's writes settled (attempt 7) and to prove
  the cause with a manifest diff rather than assert it. Future plans that gate on `make validate` in a
  shared worktree should expect the same and should not read it as a lint defect — or should run in an
  isolated worktree.

## Fixes

- `a3fab6d fix(21-06): annotate promised_map so the cursor None branch type-checks (gate fix)` —
  `tests/gsd_curated_eval.py` `_baked_chain` computed `promised_map` in three branches and passed it to
  `_baked_mismatches(baked: dict[str, str | None], promised_map: dict[str, str | None])`; the cursor
  branch (`{agent: None for agent in agents}`, added by 21-03) infers `dict[str, None]`, which pyright
  rejects because `dict` is invariant in its value type. Reproduced at `HEAD~1` before this plan
  touched the file, so it is pre-existing — and fixed here rather than deflected, because the plan's
  gate requires `make validate` `exit=0`. Scope: one dev-harness module, zero shipped product modules,
  so no decimal phase under R8. The regression check is the pyright hook itself (`Passed` in
  `tmp/p21/gates/validate.txt`, `0 errors` from a direct `uv run pyright`), which runs in every future
  `make validate`; no unit test is added for a pure type annotation.
- No other fix was needed. Nothing in `skills/` or `tools/` changed in this plan.

## Human verification

One gate and one deferred item, both belonging to uz:

- **`21-INTERACTIVE-CURSOR.md` steps 1-4 (REQUIRED) — SPEC R1 / ROADMAP SC1-SC2.** Run it in the real
  Cursor TUI: sign in (`command cursor-agent --model auto`), read-only baseline + user-keys digest,
  the paste-able `TMPDIR=/tmp python3 tests/gsd_curated_eval.py smoke … --host-rewrite
  '<home>/.cursor/cli-config.json'` with `smoke exit=$rc` printed, then the post-run protected-set
  check and digest comparison. **What to look at:** `smoke exit=0` with `all 12 steps passed` and a
  `plan` line naming a `cursor/*` model; the `protected set (unchanged)` line reading
  `changed (host-rewrite): <home>/.cursor/cli-config.json` if the host rewrote the config (that is
  SPEC R3's proof, not a failure); the post-run line `snapshot ok`; and the two digest lines matching
  (an earlier 21-05 attempt's rewrite would otherwise be invisible to every later gate). Then paste the
  transcript and both exit codes into `21-SMOKE-CURSOR.md ## Interactive run`. On a `1` or `2` stop —
  that is the phase's gate failing, and the evidence files under `tmp/p21/interactive/` are what to
  bring back.
  **What it triggers:** a green run is what lets the cursor env-signal label lose its
  `TUI confirmation pending` note and the SKILL.md cursor row lose its `pending` interactive note in
  the same commit that records the run (`21-INTERACTIVE-CURSOR.md` step 4, 21-05's two-step-lift rule)
  — no interactive transcript, no label change.
- **`21-INTERACTIVE-CURSOR.md` step 5 (OPTIONAL) — ROADMAP SC5.** Only if uz wants the per-call claim:
  the probe prints `cursor exit=$?` and, for each assistant object that carries a non-null
  `subagentType`, `subagent=<type> model=<model>` and nothing else; a model that differs from the
  session default lets 21-05's `LIFT` branch replace the current wording. It ends by listing new
  `worker-server` processes as `probe-owned` or `unidentified` and killing nothing — uz decides
  disposal, because a name-based kill would take the IDE's own servers too.
- **Skill-judge decision (see Issues Encountered).** uz decides whether pi's 114/120 against the 116
  floor is accepted variance (then `21-SKILL-JUDGE.md`'s `UNRESOLVED (owner review)` becomes the
  recorded decision and Phase 21 can be marked complete once the interactive run also lands) or a real
  regression (then 21-05's fix loop and both re-judges, command in `## Phase gates`).

## Process proof

- **Plan04's spawn-pid capture is what the leak check is measured against**
  (`bash tmp/p21/gates/leak-check.sh tmp/p21/gates/ps-final.txt`, which also diffs every surviving
  line against 21-04's baseline and prints `PRE-EXISTING` / `NEW-LINE`). `cursor-run1.pgid`
  carries twelve `spawn <pid>` entries (the dispatch's descendants: `cross-ai.mjs`, its `claude`
  child, `gsd-tools.cjs run-with-timeout`, the `node -e while` idle probe, the `worker-server`
  processes); every one now reports an empty process group, and 21-04's own kill audit had already
  cleared them before this plan started. There is no `cursor-probe*.pgid` file because no probe was
  dispatched. So: **no process started by Phase 21 survives this plan**, and the single line matching
  the leak pattern in `tmp/p21/gates/ps-final.txt` is also present in `tmp/p21/headless/ps-before.txt`
  — a two-day-old shell whose command string merely names those binaries, not ours.
- **Scratch home: removed, and the D-19 late-teardown clause was never needed.**
  `test -e "$(cat tmp/p21/headless/scratch-home.txt)"` is false: `/tmp/p21-cursor-home.SysiYq` is gone
  and no `/tmp/p21-cursor-home.*` exists. 21-04's own teardown ran before this plan, so this plan ran
  none of that clause's steps (b)-(d); no `/tmp/claude-*/scratch-home.txt` stray exists either, and no
  scratch home was ever inside the repo. The `auth.json` symlink into the user's real login was
  removed with the scratch home and was only ever `test -L`/`test ! -e`'d.
- **Cleanup rule honoured.** `ps -eo pid,args | grep -E 'gc-late|node -e while' | grep -v grep`
  returned nothing, so no `kill` was issued. Nothing under `/tmp` created by this plan is unrecorded:
  the paths it wrote are `tmp/p21/gates/*` (including the three manifest/hook-output proof files),
  `tmp/p21/plan06.start` and `tmp/p21/plan06.before.json`, and the throwaway copies it used under
  `./tmp/` during the pyright investigation (`plan06.prev.py`, `plan06.new.py`, `plan06.newtest.py`)
  were deleted right after that experiment.

## Environment findings

- **`secret-scan` is scoped by this plan to the phase directory** (`21-06-PLAN.md`'s truth and Task 2
  action) and that scan is clean (`exit=0`). Running it over all of `tmp/p21` is **not** clean and was
  never required: every hit is inside `tmp/p21/inst/proj/…`, an earlier plan's scratch install of
  gsd-core, i.e. third-party reference docs that merely contain secret-shaped strings. No credential
  value of any kind lives under `tmp/p21`.
- The `$HOME` grep over the phase directory is a real check here, not a formality: this worktree's
  own path has the home path as a substring (`/var<home>/…` contains `<home>`), so any absolute
  worktree path baked into a phase artifact would trip it too — and it did, once, in the sentence
  above, before this commit removed it. It now returns `exit=1`. Three of this plan's
  own gate logs did carry absolute paths from tool output (`validate.attempt6.txt`, `ps-final.txt`,
  `verify-trace-rest.txt`) and were rewritten to `<home>` after the runs they record — the logs are
  gitignored scratch under `./tmp/`, but they no longer name the machine.

- **A concurrent session is using this same worktree.** During this plan it committed
  `dd741bd docs(21.1): replan after cross-AI review cycle 2` and `5848872 docs(21.1): cross-AI review
  cycle 3` onto `gsd/v1.3-curated-config-v2` (between this plan's two commits) and kept
  `.planning/phases/21.1-*/21.1-0N-PLAN.md` / `21.1-VALIDATION.md` modified. Those files are not this
  plan's, were never staged, edited, stashed or reverted. They are why five `make validate` attempts
  could not finish, and — together with the two untracked `21.2-RESEARCH.md` / `21.3-RESEARCH.md` files
  that appeared later — why `git status --porcelain` is not empty at the end of this plan even though
  every path this plan touched is committed. Nothing was done to any of them beyond observing the
  mtime/hash churn that broke the validate attempts.
- **plan04's baseline protected-set check: `snapshot ok`** (`tmp/p21/gates/snapshot-plan04.txt`) —
  information only, as the plan requires the current gate to be plan06's own baseline
  (`tmp/p21/gates/snapshot-plan06.txt`, also `snapshot ok`), and plan05's baseline is `snapshot ok`
  too. Across 21-04 → 21-06 nothing wrote to `~/.cursor/cli-config.json` or any other protected path,
  so **the `--host-rewrite` exemption was not needed and not used** for this plan's snapshot. It is
  shipped because the plan predicts the host will rewrite that file during uz's interactive run, where
  using it is then mandatory — and because a label that can only be exempted by editing `_strict_files`
  is a label that gets deleted under gate pressure instead.
- The task-1 scratch verification used a synthetic home only (`--home <tmp>` with a seeded
  `cli-config.json`); the user's real `~/.cursor/cli-config.json` was touched only through the
  harness's protected-set hash (`snapshot --check`, which prints label names and a `changed` verdict,
  never values), never opened, never read with `jq`; `python3 tests/gsd_curated_eval.py digest` hashes
  the skill's own bytes, not any user config. No cursor/opencode/pi binary was version-probed or
  executed outside this plan's named actions.
- `python3 tests/gsd_curated_eval.py digest` → `85da5a6682d937c5`
  (`tmp/p21/gates/digest-now.txt`), unchanged from 21-05's stored value and equal to both skill-judge
  reports' `DIGEST`, which is what makes the skill-judge verdict current rather than stale.
- `tmp/p21/headless/ps-before.txt`, `cursor-run1.pgid`, `cursor-smoke.md`, `run-smoke.sh` and
  `scratch-home.txt` survived 21-04 intact and are the files cited above. `plan04-make-test.log` had
  already been rotated from `tmp/p21/headless/` to `tmp/p21/` before this plan's gate check (by
  21-05's scratch reorganisation), so plan04's gate is cited from `21-04-SUMMARY.md`'s recorded
  `rc=0` and from that surviving log, and in every case that matters from this plan's own fresh
  `make test` runs — `tmp/p21/gates/test.txt` and, after the pyright fix,
  `tmp/p21/gates/test.final.txt` (`exit=0`, 4,396 tests). `make validate` was likewise re-run on the
  final tree (`tmp/p21/gates/validate.final.txt`, `exit=0`, all eight hooks `Passed`).
- Phase 21.1 is executing in parallel with Phase 21's close-out (that session's commits above). No
  conflict was observed in any path this plan owns; the only interference was the shared-worktree
  pre-commit hashing effect recorded under Issues Encountered.

## Next Phase Readiness

- Phase 22 (Pi Live Validation) is unaffected by this plan: no product module changed, and the only
  harness surface added is an opt-in flag whose `choices` accept exactly one label.
- Phase 21 is **not** ready to close. Two items gate it, both outside an executor's authority: uz's
  run of `21-INTERACTIVE-CURSOR.md` steps 1-4 (SPEC R1, ROADMAP SC1-SC2, and the label change it
  triggers), and the `UNRESOLVED` skill-judge verdict (pi 114 under the 116 floor), which needs uz's
  variance-vs-regression decision and, if it is a regression, the 21-05 fix loop plus both judges
  re-run on the new digest — work that needs an AI CLI and therefore a phase of its own, not a step
  an executor can improvise inside 21-06.
- Whatever closes Phase 21 should re-run `python3 tests/gsd_curated_eval.py snapshot --check
  tmp/p21/plan06.before.json` and the digest one-liner from `21-INTERACTIVE-CURSOR.md` step 2: the
  protected set has been unchanged across 21-04 → 21-06, and that continuity is the evidence the
  cursor label rests on.

## Dependencies

No new runtime, tool or dev dependency. The harness change is stdlib-only (`argparse`, `os.path`), and
the interactive script uses only `cursor-agent`, `python3`, `jq`, `ps`, `wc`, `cmp` and `stat`.

## Sources

- `.planning/phases/21-cursor-live-validation/21-06-PLAN.md` (tasks, must_haves, verification truths)
- `.planning/phases/21-cursor-live-validation/21-SMOKE-CURSOR.md` (`## Headless run`,
  `## Label decision`, and this plan's `## Interactive run` + `## Phase gates`)
- `.planning/phases/21-cursor-live-validation/21-INTERACTIVE-CURSOR.md` (the user-run gate)
- `.planning/phases/21-cursor-live-validation/21-SKILL-JUDGE.md` + `skill-judge/in-session.md` +
  `skill-judge/ai-kit-gsd-curated-config-pi-gpt-6.1-sol-xhigh.md` (the gate's inputs)
- `.planning/phases/21-cursor-live-validation/21-04-SUMMARY.md`, `21-05-SUMMARY.md` and
  `.planning/phases/20-live-validation-on-codex-opencode/20-07-SUMMARY.md` (the lane's gate rules:
  `TMPDIR=/tmp`, the floors, the scratch-home and process-group proofs, the `phase status` form)
- `tmp/p21/gates/*` (this plan's own gate logs), `tmp/p21/headless/*` (21-04's dispatch capture)
- `.claude/gsd-core/workflows/execute-plan.md` §7 (SUMMARY discipline; the in-session skill-judge row
  is the orchestrator's and keeps its own pending marker)

---
*Phase: 21-cursor-live-validation*
*Completed: 2026-10-19*

phase status: human_needed
