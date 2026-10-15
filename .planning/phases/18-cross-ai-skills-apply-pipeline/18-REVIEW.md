---
phase: 18
status: issues_found
depth: deep
reviewers: [gsd-code-reviewer x3 (A/B/C batches), ponytail-review, skill-judge (independent)]
date: 2026-10-15
findings: {A: {critical: 5, warning: 13, info: 12}, B: {critical: 1, warning: 8, info: 8}, C: {critical: 1, warning: 14, info: 11}, ponytail: {should_fix: 17, consider: 5}, skill_judge: {verdict: FAIL, score: 88, baseline: 104, important: 7}}
---
# Phase 18 Code Review (consolidated)

Batches: A = cross-AI runner (`references/cross-ai.mjs`), cross_ai.py, cross_ai_script.py, ai_kit_spec detection/gsd_tools/cache/local_secrets/tooling_guidance; B = apply.py, config_backup.py, followups.py, plan_io.py, plan_edit.py, cli.py, plan_schema.py, host.py; C = skills.py, skill_scan.py, recommend.py, inventory.py, gsd_catalog.py, roles.py, project_facts.py, presets.py, skill_affinity.json, SKILL.md, README, gates. Finding ids keep their batch prefix (A-CR-01, B-WR-03, C-W7, PT-01, SJ-I1...).

Duplicates / overlaps:
- B-WR-02 == C-W7 (plan-set JSONDecodeError traceback on a bare value).
- C-W14 ~ skill-judge Important findings (SKILL.md vs CLI: file locations, `--force` example, `--project-dir`).
- C-W8 ~ B (trusted-root approval can drop existing roots) — C owns the proposal side, B owns the validator side.
- A rigorous single-lane warning == PT-17 == C IN-09 (cross_ai.py, owned by batch A).
- A self-test cleanup-not-in-finally == RUN-60 orchestrator note.

Orchestrator notes:
- Four orphaned self-test fakes from earlier runs (pids 1587199, 1590014, 1602429, 1627304; cwd /tmp/xai-st-*) reported by batch A were killed by the orchestrator, and the /tmp/xai-st-* dirs removed.
- Fix order (serial; the pre-commit unittest hook runs the whole unit suite): B -> C (+ skill-judge + SKILL.md) -> A (+ runner ponytail items).


# Batch A


## Phase 18: Code Review Report (batch A: cross-AI runner)

**Reviewed:** 2026-10-15T23:35:06Z
**Depth:** deep
**Files Reviewed:** 12
**Status:** issues_found

### Summary

I reviewed the runner template (`cross-ai.mjs`, process lifecycle, classification, retry/resume,
git tree state, preflight, self-test), its Python generator and writer (`cross_ai.py`,
`cross_ai_script.py`), and the `ai_kit_spec` helpers changed in this diff. I traced the code paths
against gsd-core's `run-with-timeout` and `config-get` in the checkout-local `.claude/gsd-core`.

Every Critical finding and most Warnings were reproduced. I used throwaway fake CLIs in
`mkdtemp` directories under `/tmp`, a copy of the runner, and the real `gsd-tools.cjs
run-with-timeout`. No real model CLI was run. Each scratch process was killed and each
directory removed afterwards. The current `--self-test` passes (31 s) and left nothing behind.

Main concerns:

- **Classification.** A successful exec run can be reported as failed because of noise on
  stderr.
- **Tree-state safety.** `retry-later` is not demoted when the tree is dirty or unknown, and
  the signal path reports a stale `tree=clean`.
- **Process lifecycle.** On the signal path the runner loses the race against run-with-timeout's
  3 s SIGKILL, and a second signal skips cleanup. Both leave a full-permission CLI group
  orphaned. The transient backoff also sleeps past the deadline.
- **Self-test cleanup.** The known issue is confirmed: cleanup is still not guaranteed. The
  details are refined in WR-09 and WR-10.

`cross_ai_script.py` keeps a TOCTOU window between its re-read and `os.replace`, as its own
`shortcut:` comment says. Writes are atomic via `cache_write_bytes`, the code is stdlib-only,
and `secret_is_set` checks presence only. No new defect was found in those areas beyond the
items below.

### Narrative Findings (AI reviewer)

All findings below come from direct review. No structural (fallow) findings and no external
reviewer evidence were provided.

### Critical Issues

#### CR-01: A successful run is reclassified as a failure by stderr noise

**File:** `skills/ai-kit-spec-review/references/cross-ai.mjs:646-656` (patterns `:97-105`)

**Issue:** `runCli` classifies stderr before it checks for success. Any non-transient pattern
hit returns a failure, even when the CLI exited 0 with a parsed answer and no structured error.
The patterns are broad (`\b40[13]\b`, `\b402\b`, `\b503\b`, `permission denied`, `billing`,
`overloaded`, `usage limit`). A CLI's stderr can carry a notice about a retry it recovered from,
or forwarded tool output.

**Evidence:**
- A scratch fake pi edits `a.txt`, writes `provider returned 503 Service Unavailable; retrying`
  to stderr, prints `# Summary\nok` and exits 0. The runner exits 75 with 0 bytes of stdout and
  `AIKIT-XAI status=capacity cli=pi model=f/okwarn exit=75 cli_rc=0 ... tree=dirty action=retry-later`.
- Classifier spot checks: `wrote 401 lines` gives `auth`;
  `EACCES: permission denied, open ~/.cache/x.log` gives `permission_blocked`.

**Impact:**
- An exec run that finished and committed is reported as failed, and its SUMMARY is dropped.
- Combined with CR-02, a later re-dispatch repeats the work on top of the commits.
- Unverified: for codex, any JSONL `type:"error"` event sets `p.error`, including one codex
  recovered from.

**Fix:** classify only runs that failed:
```js
const failed = r.code !== 0 || Boolean(p.error);
if (!failed) {
  if (!p.text.trim()) return { ok: false, status: 'empty_answer', outBytes: r.outBytes, cli_rc: 0 };
  return { ok: true, text: normalize(p.text), outBytes: Buffer.byteLength(r.stdout, 'utf8'), cli_rc: 0 };
}
const hit = classify(r.stderr, p.error);
if (hit && hit !== 'transient') return { ok: false, status: hit, outBytes: r.outBytes, cli_rc: r.code ?? '-' };
```
Add a self-test fake that exits 0 with `503` on stderr and an edit, and expect `status=ok`.

#### CR-02: `retry-later` survives a dirty or unknown tree, and a git failure after the run is not `unverified`

**File:** `skills/ai-kit-spec-review/references/cross-ai.mjs:159-168`, `:1961-1972`

**Issue:**
- `finish()` demotes only `action=fallback` to `stop` when the tree is dirty or unknown
  (`:163`). `quota` and `capacity` keep `retry-later` on a dirty or unknown tree.
- The `routerBacked` override (`:165-168`) runs after the demotion and sets `retry-later`/75
  unconditionally.
- In the failure branch, `after === null` keeps the CLI's status (for example `quota` 75
  `retry-later`, or `auth` with exit 69 and `action=stop`). SPEC R5 requires `unverified`
  (exit 1, stop) when the tree cannot be read after a run.
- Audit section 4.6 (`.planning/research/2026-10-13-audit/18-runtime-detection-and-subprocess-supervision.md:243`)
  says: "Stop and surface: any class with tree=dirty".

**Evidence:**
- A fake that edits and then exits 1 with `quota exceeded` gives
  `status=quota ... exit=75 ... tree=dirty action=retry-later`.
- With `routerBacked: {pi: true}`, a fake that edits and then exits 1 with
  `402 payment required` gives `status=billing ... exit=75 ... tree=dirty action=retry-later`.

**Impact:**
- The orchestrator is told to retry later over partial, uncommitted edits from a failed run.
- Exit codes (69/75) contradict the `stop` action.

**Fix:**
```js
let action = fields.action ?? row.action;
let exit = fields.exit ?? row.exit;
if (status === 'billing' && fields.cli && CONFIG.routerBacked[fields.cli]) { action = 'retry-later'; exit = 75; }
if ((action === 'fallback' || action === 'retry-later') && (tree === 'dirty' || tree === 'unknown')) action = 'stop';
```
In `main`'s failure branch, return `finish('unverified', { ...liveFields, tree: 'unknown', exit: 1 })`
when `after === null`. Add self-test cases for dirty-quota and dirty-billing-router.

#### CR-03: The signal status line claims `tree=clean` after an interrupted run

**File:** `skills/ai-kit-spec-review/references/cross-ai.mjs:142`, `:599-606`, `:1846`, `:1936-1938`

**Issue:** `liveFields.tree` starts as `'clean'` and changes only after the snapshot that follows
the run. The signal handler reports `liveFields.tree`, so a signal at any of these points
reports the value from before the run:
- while a CLI is running;
- during the snapshot after the run;
- during the backoff sleep (CR-05).

Header line 6 defines `tree=clean` as "this CLI run left HEAD and the tree unchanged".

**Evidence:** a fake appends to `a.txt` and then hangs. SIGTERM to the runner gives
`AIKIT-XAI status=signal cli=pi model=f/edithang exit=143 ... tree=clean action=stop`, but
`a.txt` was modified.

**Impact:**
- Operators and the orchestrator read this field to decide whether falling back is safe. After
  a failure, GSD offers "skip -> normal executor".
- It breaks the AGENTS.md rule against claiming more certainty than was verified.

**Fix:** set `liveFields.tree = 'unknown'` right before each `runCli`/CLI spawn, and set a value
only from `treeState`. Alternatively, have the handler report `unknown` whenever a CLI was
spawned since the last verified snapshot.

#### CR-04: The signal path loses to run-with-timeout's 3 s SIGKILL and to a second signal, which orphans the CLI group with no status line

**File:** `skills/ai-kit-spec-review/references/cross-ai.mjs:393-395`, `:408-429`, `:599-606`

**Issue:**
- (a) `signalPath = aborting > 0` is computed when `runChild` is called, not when the signal
  arrives. The running CLI's finalize therefore always waits `KILL_GRACE_MS` 2000 plus
  `PIPE_DRAIN_MS` 2000, so `SIGNAL_GRACE_MS` is never used.
- gsd-core's `run-with-timeout` forwards SIGTERM/SIGINT to the runner's group and SIGKILLs it
  3 s later (`.claude/gsd-core/bin/gsd-tools.cjs` `runWithTimeout`, `armEscalation` 3000 ms).
- If the CLI does not exit within about 1 s of SIGTERM, or a grandchild holds its pipes, the
  runner is killed mid-finalize. That happens before the group SIGKILL (`:428`) and before
  `finish()`. The CLI runs in its own detached group, so nothing reaps it.
- (b) `finalize` clears `currentFinalize` (`:413`) before it awaits. A second signal finds it
  null and exits at once, which skips the SIGKILL.

**Evidence:** a fake pi ignores SIGTERM and SIGINT. All scratch PIDs were SIGKILLed afterwards.
- Under the real `gsd-tools.cjs run-with-timeout 3 -- node <runner> ...`: rc=124, wall 6.6 s,
  no `AIKIT-XAI` line, and the CLI PID is still alive.
- A direct SIGTERM: the runner exits 4014 ms after the signal, which is more than 3 s.
- SIGTERM, then SIGINT 200 ms later: rc=130, a status line is printed, and the CLI PID is still
  alive.

**Impact:** a Ctrl-C, a CI cancel, or an outer timeout winning the race (see WR-03) leaves an
unsupervised full-permission agent editing the repo, and GSD gets no status line.

**Fix:**
- Choose the grace inside `finalize` (`const sig = aborting > 0; grace = sig ? SIGNAL_GRACE_MS : KILL_GRACE_MS; drain = sig ? 500 : PIPE_DRAIN_MS`).
- SIGKILL the group right after the grace wait, before draining.
- Make the handler re-entrant: `if (aborting) { if (current) killGroup(current, 'SIGKILL'); return; }`.
- Keep the whole signal path under about 2.5 s.
- Add a spawn self-test case with a CLI that ignores SIGTERM. It should assert an exit within
  2.5 s of the signal and a dead CLI PID.

#### CR-05: The transient backoff sleeps past the inner deadline and the outer timeout

**File:** `skills/ai-kit-spec-review/references/cross-ai.mjs:657-661`, `:675`

**Issue:**
- `budgetMs(wait + 60000, runDeadline) <= 0` is true only once the deadline has passed, because
  `budgetMs` clamps to the time left. The `+ 60000` margin therefore never applies.
- `await sleep(wait)` has no bound.
- With the shipped `backoffS: [30, 60]`, a transient error late in the run can sleep up to 60 s
  past `runDeadline`. That is past `finalizeBy` (+10 s) and past the outer timeout (+30 s at
  1800).
- The overrun also leaves no budget for the snapshot after the run, so the tree becomes
  `unknown`.

**Evidence:** the template's CONFIG as shipped, a fake that exits 1 with `429 Too Many Requests`,
and `--timeout 3` give a wall time of 30 159 ms and
`AIKIT-XAI status=timeout ... exit=124 cli_rc=124 elapsed=30s ... tree=unknown`. Under GSD, the
60 s step gets the runner SIGTERMed by run-with-timeout, which yields `status=signal` with the
stale tree from CR-03.

**Fix:**
```js
const left = runDeadline - Date.now();
const exhausted = hit === 'transient' && (attempt >= (opts.retries ?? CONFIG.retries) || left < wait + 60000);
...
await sleep(Math.min(wait, Math.max(0, runDeadline - Date.now())));
```
Add a self-test case where the backoff exceeds `--timeout`. It should assert `status=capacity`
and an elapsed time under the timeout plus 2 s.

### Warnings

#### WR-01: `exitFlushed` does not flush pipes, so the stdout answer and the status line can be truncated

**File:** `skills/ai-kit-spec-review/references/cross-ai.mjs:178-186`, `:1958-1959`

**Issue:**
- `fsyncSync` fails on a pipe or socket (the error is caught), and `process.exit` drops Node's
  queued async writes.
- Writes to files are synchronous, so GSD's `> "$CANDIDATE_SUMMARY" 2>"$ERROR_LOG"` path is
  safe. A caller that captures through a pipe loses data while seeing exit 0 (Python
  dispatchers per D-30, `| tee`, test harnesses).
- An older copy of this runner (still in `/tmp/xai-st-JPo5SA/runner-*.mjs`) waited for
  `'drain'`. The fsync version is a regression.

**Evidence:**
- A 315 010-byte answer comes through a pipe as 146 176 bytes, with `status=ok exit=0`. The same
  answer redirected to a file is 315 010 bytes.
- `node -e "process.stderr.write(<300 KB>); process.stderr.write('AIKIT-XAI ...\n'); process.exit(0)"`
  loses its final line on a pipe.

**Fix:** set `process.exitCode = code`, let the event loop drain, and keep an unref'd safety
timer (`setTimeout(() => process.exit(code), 2000).unref()`). Alternatively, call
`process.exit` only from the callbacks of a final `write` on both streams.

#### WR-02: The runner crashes on EPIPE to stderr and orphans the CLI group

**File:** `skills/ai-kit-spec-review/references/cross-ai.mjs:154-157`, `:613-621`

**Issue:** `process.stderr` and `process.stdout` have no `'error'` listener, and there is no
`uncaughtException` hook. Once the stderr reader is gone, the next log or heartbeat write throws.
The runner exits 1 without running `finalize`, and the detached CLI group keeps running.

**Evidence:** with `heartbeatS: 1` and a fake CLI that hangs, closing the runner's stderr reader
after the CLI starts makes the runner exit with code 1 after 982 ms. The CLI PID is still alive
(the harness killed it).

**Impact:** if a caller that captures through a pipe dies, a full-permission agent keeps running
unsupervised. This also explains the orphaned fake CLIs in WR-09.

**Fix:**
- `process.stderr.on('error', () => { finished = true; })` and
  `process.stdout.on('error', () => {})`.
- Add an `uncaughtException` hook that SIGKILLs the current child's group before exiting.

#### WR-03: The live timeout lookup differs from gsd-core's `config-get`

**File:** `skills/ai-kit-spec-review/references/cross-ai.mjs:315-324`

**Issue:**
- With `GSD_WORKSTREAM` set, the runner reads only `.planning/workstreams/<ws>/config.json` and
  otherwise falls back to 300 s.
- gsd-core inherits the root key when the workstream file lacks it or is missing
  (`config.cjs` `cmdConfigGet` #2702, `planning-workspace.cjs` `readScopedConfigValue`).
- The runner also ignores `GSD_PROJECT` (`planningDir` adds `.planning/<project>`) and the
  stored active-workstream pointer that gsd-tools folds into its own env.

**Evidence:** with root `cross_ai_timeout: 1800`, `GSD_WORKSTREAM=ws`, and a workstream config
that lacks the key (or is missing), `gsd-tools query config-get workflow.cross_ai_timeout --raw`
prints `1800`. The runner's `--print-argv` prints `cross-ai: deadline 270s (outer 300s)`.

**Impact:**
- Workstream exec runs are killed at 270 s although GSD allows 1800 s (exit 124).
- In the opposite direction, the outer timeout wins the race and CR-04 applies. This happens
  when a `GSD_PROJECT` or pointer-selected config is lower than what the runner reads (from
  reading the code, not run).

**Fix:**
- Mirror gsd-core's lookup order: the scoped file's own key, then the root key under
  `GSD_WORKSTREAM`, then the default.
- Honour `GSD_PROJECT` with the same `[/\\]|\.\.` rejection.
- Alternatively, have GSD's resolved value reach the runner explicitly and use that as `live`.

#### WR-04: 403 spending-limit errors classify as `auth`, so router-backed billing never reaches retry-later

**File:** `skills/ai-kit-spec-review/references/cross-ai.mjs:97-105`, `:288-297`

**Issue:** `classify` returns the first key that matches, in insertion order, and `auth`
(`\b40[13]\b`) comes before `billing`. The `routerBacked` 75 rule (`finish` `:165`) fires only
for status `billing`. That defeats the QTA-01 amendment for the 403 spending-limit failure that
the project memory records for xai.

**Evidence:** `Error 403: spending limit reached for this team` gives `auth`.
`403: {"type":"FreeTierError"}`, a live pi capture (`15-pi-live-tests.md:92`), also gives `auth`.

**Fix:**
- Check `billing` (and `quota`) before `auth`, or stop treating a bare 403 as auth when a
  billing phrase appears on the same line.
- Add a self-test case with `403 spending limit` and `routerBacked`.

#### WR-05: Model preflight rejects valid model specs that carry a thinking or variant suffix

**File:** `skills/ai-kit-spec-review/references/cross-ai.mjs:1917-1926` (`:470-512`)

**Issue:**
- The preflight requires an exact `ids.includes(c.model)` match against bare `provider/id`
  (pi) and `provider/model` (opencode) ids.
- pi documents `--model provider/id[:thinking]` (`18-RESEARCH.md:622`), and
  `15-pi-live-tests.md:215` recommends the suffix for pinning effort.
- opencode uses `provider/model#variant` (`18-RESEARCH.md:403`).
- `plan-set script:cross-ai.model.<cli>` stores any string (`plan_edit.py:200`), so such specs
  reach `CONFIG.models`. They then end as `bad_model` without the CLI ever running.

**Fix:** before matching, strip only the documented suffixes:
- pi: `/:(off|minimal|low|medium|high|xhigh|max)$/`
- opencode: `/#[^#/]+$/`

Log that the suffix itself was not validated.

#### WR-06: The selected execution effort never reaches the runner, so pi thinking is not pinned

**File:** `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cross_ai.py:24`, `:59-62`, `:312-332`; `cross-ai.mjs:213-215`

**Issue:**
- Targets are scored for `EXEC_EFFORT_TARGET = "medium"`, but the artifact carries only the
  model id.
- The pi formulas have no `--thinking`, and CONFIG has no effort field. Codex effort exists only
  as a CLI flag, and D-44 keeps that out of `cross_ai_command`.
- The research notes that omitting the level runs the user's default, xhigh on this machine:
  "an executor command must pin `--model` and `--thinking`" (`06-pi-cross-ai-executor.md:134`, `:299`).

**Impact:** a catalog-score pi pick on a reasoning model runs at the user's default effort, not
the one the selection targeted. Router picks are clamped by pi and are not affected.

**Fix:**
- Carry a per-target thinking level in `config` (for example `"thinking": {"pi": "medium"}`
  when the candidate has `reasoning_modes`) and render `--thinking <level>` in the pi formulas.
- Bake `codexEffort` into CONFIG for codex.

#### WR-07: pi review retries reuse the first attempt's `--session-id`, which is a resume, not a fresh run

**File:** `skills/ai-kit-spec-review/references/cross-ai.mjs:214-215`, `:342-345`, `:633`

**Issue:**
- `ctx.sid` is created once per `runCli`, and the "fresh" review argv carries
  `--session-id ctx.sid`. pi reopens an existing id.
- SPEC R5 (amended in 18-12) says "review retries re-run the fresh review argv instead of
  resuming".
- The self-test's retry checks cover only codex and cursor (`:1629-1677`).

**Fix:** generate a new sid for each review attempt (`ctx.sid = crypto.randomUUID()` in
`retryArgv` when `mode === 'review'`), or use `--no-session` for review. Add an
`argv-retry-pi-review` case that asserts the sid differs.

#### WR-08: The codex resume argv drops `--codex-effort` and `--codex-service-tier`

**File:** `skills/ai-kit-spec-review/references/cross-ai.mjs:226-227` (compare `:223-225`)

**Issue:**
- The exec and review formulas go through `withCodexKnobs`; `resume` does not. An exec retry
  therefore runs at the default effort and service tier, so a `flex` tier silently reverts.
- `argv-retry-codex-exec` (`:1649-1662`) checks only for `resume` and the bypass flag.

**Fix:** wrap `resume` in `withCodexKnobs(..., c)` and assert that the knobs appear in the
retry argv.

#### WR-09: Self-test cleanup is still not guaranteed (known issue confirmed and refined)

**File:** `skills/ai-kit-spec-review/references/cross-ai.mjs:1051-1066`, `:1068-1099`, `:1357-1425`, `:1804-1823`, `:1827-1840`, `:599-606`; `tests/test_cross_ai_runner_e2e.py:88-96`, `:147-156`

**Issue:**
- **No per-case reaping.** No case has a `try`/`finally` that reaps its processes.
  - The grandchild checks for hang, gcpipe, gcterm and outer-race report "alive" and return
    without killing anything.
  - gcescape's SIGKILL comes after three early returns (`:1389-1394`).
  - When the exit code or status line mismatches, `runSelfTestCaseSync` returns before the
    check runs (`:1057-1059`), so that SIGKILL is never reached.
- **Spawn case.** The 30 s `hard` timer SIGKILLs only the runner (`:1079-1082`). The fake CLI's
  detached group is orphaned.
- **Interrupting the self-test.** The run-mode SIGTERM/SIGINT/SIGHUP handlers are also active in
  self-test mode. Interrupting the self-test prints an `AIKIT-XAI status=signal` line, and
  `process.exit` skips the `finally` that runs `rmSync` and the in-flight cases.
- **The Python e2e test.** Its `timeout=120` SIGKILLs only the self-test PID. The orphaned
  runner then crashes on EPIPE (WR-02), and its CLI group keeps running.
- **Refinement.** In the passing path, gcescape's escaped grandchild also dies of EPIPE once the
  fake CLI is killed. Its missing `finally` is therefore not the main leak. The vectors above
  are.

**Evidence:**
- Four orphans from self-test runs between 18:19 and 18:24 today are still running at about
  99 % CPU each, and six `/tmp/xai-st-*` directories remain:
  - PIDs 1587199, 1590014 and 1602429: `pi -p --model fake/hang`, cwd `.../r-sigterm-hang`,
    each with a zombie child;
  - PID 1627304: the fake `git write-tree`, cwd `.../r-git-hang`.
- Those runs used runner versions older than HEAD (between 6734da9 and 15b43e5). They do not
  prove the current code leaks, but they show the cleanup has no backstop.
- My run of the current self-test passed and left no processes or directories.
- Per the hard rules, I did not kill the pre-existing orphans.

**Fix:**
- Spawn each case's runner with `detached: true` and record every PID file the fakes write.
- In a per-case `finally`, SIGKILL the runner's group and each recorded PID's group.
- In self-test mode, install signal handlers that do this reaping and the `rmSync`.
- In the Python test, use `start_new_session=True` and kill the group on timeout.

#### WR-10: Lifecycle assertions can pass vacuously, and the group kill on the signal path is never asserted

**File:** `skills/ai-kit-spec-review/references/cross-ai.mjs:1362-1367`, `:1407-1424`, `:1376-1382`, `:1078`

**Issue:**
- The hang, gcpipe and gcterm checks `return null` when `gc.pid` is missing. Under load,
  preflight can use up the 2 s deadline before the fake runs, and the case still passes because
  the status regex accepts any `cli_rc` and tree.
- `sigterm-hang` has no check at all. It signals at a fixed 1000 ms whether or not the CLI has
  spawned, so it never verifies the group kill on the signal path. That is the gap CR-04
  slipped through.
- No case uses a CLI that ignores SIGTERM on the signal path.
- AGENTS.md requires checks that cannot pass vacuously.

**Fix:**
- Treat a missing PID file as a failure.
- Have `sigterm-hang` wait for `gc.pid` before signalling, then assert that both pi and gc are
  dead.
- Add a variant with a CLI that ignores SIGTERM and a 2.5 s bound.

#### WR-11: `encode_value_strict` lets through strings that config-set re-types

**File:** `skills/ai-kit-spec-review/ai_kit_spec/gsd_tools.py:154-197`

**Issue:** the refusal test uses Python's `float()`. gsd-core's config-set uses
`Number.isFinite(Number(val)) && val !== ''` (`.claude/gsd-core/bin/lib/config.cjs:787-790`).
JS `Number` accepts hex, octal and binary literals and whitespace-only strings; Python `float`
does not.

**Evidence:** `"0x10"`, `"0o17"`, `"0b11"`, `"   "` and `"\t"` all pass `encode_value_strict`.
config-set's rule coerces them to 16, 15, 3, 0 and 0. The docstring claims such values are
refused.

**Fix:** also refuse `re.fullmatch(r"\s*0[xXoObB][0-9a-fA-F]+\s*", value)` and non-empty
whitespace-only strings, and add these cases to `TestStrictEncoder`.

#### WR-12: The temp-index tree id does not see uncommitted edits inside submodules

**File:** `skills/ai-kit-spec-review/references/cross-ai.mjs:565-585`

**Issue:** `git add -A` records a submodule, or any embedded repo, as its gitlink (its HEAD).
Uncommitted edits inside it leave the tree id unchanged. As a result:
- An exec CLI that edits only submodule files is reported as `no_change` with `tree=clean`, and
  the next CLI runs over those edits.
- A review that edits a submodule passes the contract check.

**Evidence:** in a scratch superproject, the snapshot before and after `echo edit >> sub/f` gives
the same tree id (`45573410...`), while `git status --porcelain` shows ` M sub`.

**Fix:** fold `git status --porcelain=v2 --ignore-submodules=none` for submodule entries (or a
`git submodule foreach --recursive` snapshot) into `stateSig`, or report `unknown` when
submodules are dirty.

#### WR-13: Rigorous review silently gets one lane when the other lanes have no vendor-different pick

**File:** `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cross_ai.py:293-308`

**Issue:** the "only one eligible review lane; rigorous wanted 2" note fires only when exactly
one lane is eligible. When two or more are eligible but `_ranked_lanes(rest, ..., excl)` returns
`[]` (every remaining pool shares an excluded vendor or exceeds the ceiling), one lane is chosen
and no note is added.

**Fix:** add a `review_lane` note whenever `want >= 2 and len(chosen) < 2`, and name the reason.

### Info

#### IN-01: The attempt log always says `timeout=1s` or `0s`

**File:** `skills/ai-kit-spec-review/references/cross-ai.mjs:640`

**Issue:** `budgetMs(1000, runDeadline)` caps the value at 1000 ms. I observed `attempt=1 timeout=1s`
with a 270 s deadline.

**Fix:** use `budgetMs(Number.POSITIVE_INFINITY, runDeadline)`.

#### IN-02: A tautological assertion

**File:** `tests/test_cross_ai_runner_e2e.py:182`

**Issue:** `self.assertLess(1770, 1800)` compares two constants.

**Fix:** delete it, or compare the parsed deadline with the configured timeout.

#### IN-03: Detecting an unborn HEAD depends on English git messages

**File:** `skills/ai-kit-spec-review/references/cross-ai.mjs:572`

**Issue:** git child processes inherit the user's locale. On a fresh repo under `es_ES` or
`de_DE`, `/unborn|unknown revision|bad object/` does not match, so the run fails closed as
`unverified`. I verified both messages.

**Fix:** use `git rev-parse --verify -q HEAD` (exit 1, no message), or set `LC_ALL=C` for git
child processes.

#### IN-04: Object.prototype keys pass the CLI-name validation

**File:** `skills/ai-kit-spec-review/references/cross-ai.mjs:715`, `:1855-1857`

**Issue:** `--prefer constructor` passes the check `RUNTIMES[n]`, then crashes with
`status=crash exit=1` instead of `usage` exit 2. I verified this.

**Fix:** use `Object.hasOwn(RUNTIMES, n)`.

#### IN-05: Temp directories leak when the runner exits on a signal

**File:** `skills/ai-kit-spec-review/references/cross-ai.mjs:631`/`:682`, `:574`/`:583`

**Issue:** `process.exit` from the signal handler skips the `finally` blocks. `/tmp/cross-ai-*`
and `/tmp/xai-idx-*` stay behind; the latter is a full temp index of the repo.

**Fix:** track the directories and remove them in the handler before exiting.

#### IN-06: The flaky check is not hermetic

**File:** `skills/ai-kit-spec-review/references/cross-ai.mjs:1529`

**Issue:** this check runs `git status` with the self-test's real env, so the user's global git
config applies.

**Fix:** pass `hermeticEnv(...)`.

#### IN-07: `cli_rc` is invented when the CLI never ran

**File:** `skills/ai-kit-spec-review/references/cross-ai.mjs:1944`

**Issue:** `cli_rc: r.cli_rc ?? 124` reports 124 as the CLI's exit code even when the timed-out
attempt never spawned. I observed `cli_rc=124` in the CR-05 run.

**Fix:** use `'-'`.

#### IN-08: Dead code

**File:** `skills/ai-kit-spec-review/references/cross-ai.mjs:146`, `:430`, `:448`

**Issue:** `current` is written but never read. `SIGNAL_GRACE_MS` is effectively dead (see CR-04).

**Fix:** use `current` in the fix for CR-04, or remove it.

#### IN-09: The review-only check runs only after earlier candidates have already run

**File:** `skills/ai-kit-spec-review/references/cross-ai.mjs:1904-1907`

**Issue:** the exec-mode "review-only" check runs per candidate. A config error with claude in an
exec `prefer` list surfaces only after the earlier CLIs have already run.

**Fix:** validate every candidate's formula before the first spawn.

#### IN-10: `config_set_strict` errors can echo the value being written

**File:** `skills/ai-kit-spec-review/ai_kit_spec/gsd_tools.py:229-230`

**Issue:** `str(TimeoutExpired)` includes the full argv, and therefore the value. If this writer
is ever used on a secret key, the value lands in the report. gsd-core masks secrets in its own
output.

**Fix:** return a fixed message on `TimeoutExpired`.

#### IN-11: `_publish` briefly sets the process umask to 0

**File:** `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cross_ai_script.py:205-207`

**Issue:** `os.umask(0)` followed by a restore sets a process-wide umask of 0 for a moment.
That is fine for a single-threaded CLI, but a thread that creates files in that window gets
mode 0666/0777.

**Fix:** read the umask from `/proc/self/status` (`Umask:`), or chmod relative to a known mode.

#### IN-12: Each tree snapshot rehashes the whole tree

**File:** `skills/ai-kit-spec-review/references/cross-ai.mjs:574-581`

**Issue:** each snapshot hashes every tracked and untracked file into an empty index, which
writes loose objects into `.git/objects`, in review mode too. With the 10 s `GIT_CAP_MS`, a
large or LFS repo can turn every run into `unverified`. I did not measure this.

**Fix:** seed the temp index from a copy of `.git/index`, which keeps the stat cache.

---

_Reviewed: 2026-10-15T23:35:06Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: deep_

# Batch B


## Phase 18 (batch B): Code Review Report

**Reviewed:** 2026-10-15T23:26:28Z
**Depth:** deep
**Files Reviewed:** 12
**Status:** issues_found
**Diff base:** d164697..HEAD

### Summary

This batch covers plan editing (`plan-set`/`plan-unset`), the D-22 apply pipeline (marker, backup, `config-new-project`, runner render, `config-set` writes, commit point), backups, recovery text and follow-ups. I traced the call chains into `ai_kit_spec.gsd_tools`/`cache` and into the project-local gsd-core 1.16.0 (`config-set`, `config-path`, `--cwd`/`--project-dir` root resolution, `platformWriteSync`, `loadTrustedGlobalRoots`).

What holds up:
- Marker exclusivity (`os.link`).
- Atomic restore and backup bytes and mode.
- Prune pattern.
- Recovery-text agreement for every state the code records.
- The `config-set` failure rollback.
- Destination binding through `config-path`.

**The main defect:** the rollback contract only covers failures that come back as return values. Exceptions raised in the pre-commit window skip `_rollback` completely. Those are:
- a `config-new-project` timeout or spawn error;
- an `OSError` from the runner snapshot or the marker update.

When they happen, a fresh project keeps a config that `config-new-project` created and that was never reconciled. The marker stays held and the CLI dies with a traceback instead of printing the JSON report (CR-01).

The same missing `subprocess.SubprocessError` handling also breaks two later stages:
- the post-commit skill check;
- the follow-ups (WR-01).

**Trust-boundary gaps for hand-edited plans:**
- `validate_plan` and `check_plan_inventory` never bind `plan.host` to `inventory.host` (WR-03).
- The "~/-relative" trusted-root rule accepts `~/../..` (WR-04).
- `--force` lets the host's own slug become a review lane (WR-05).

Every finding below was confirmed by reading the code. Where marked, it was also proven by running the real functions through the existing test harness in temporary directories (no repo writes).

### Narrative Findings (AI reviewer)

### Critical Issues

#### CR-01: Exceptions in the pre-commit window bypass rollback (fresh project left with a created, unreconciled config, a held marker and a traceback)

**File:** `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/apply.py:541-557, 761-766, 857-858, 871, 879-913`

**Issue:** D-22 says "A failure in steps 4-6 restores (D-21)". SPEC R13 says "On failure before the apply commit point it restores the backup". But only failures that come back as return values are rolled back. These calls can raise, and no caller in the chain catches them (`_execute_apply` -> `run_apply` -> `cli._cmd_apply`):

- `_new_project` (541-557) calls `call.run_fn([... "config-new-project" ...], timeout=120)` with no `try`. `subprocess.TimeoutExpired` or an `OSError` propagates.
- `_apply_script_step` (761-766) calls `config_backup.snapshot_file(plan.path)` and `_record_runner_marker(...)`, which is `update_marker`. Both raise `OSError` (disk full, permission, sibling missing), and neither is guarded. The `try` only starts at line 767, around `write_script`.
- `_prepare_writes` line 871 calls `read_live_config(config_path)` a third time, unguarded. Lines 852 and 865 are guarded. A `ValueError` here also escapes.

**Proven at runtime** (existing harness `_setup_reapply_change` + `_write_apply`, config deleted to make it a fresh project):

```
P3 snapshot OSError on fresh project ESCAPED: OSError
  config left behind: True {"model_profile":"balanced","resolve_model_ids":"omit"}
  marker: {'backup': None, 'committed': False, 'config_existed': False, 'runner': None, ...}
P4 config-new-project timeout ESCAPED: TimeoutExpired
  config left behind: True {"model_profile":"balanced"}
  marker: {... 'config_existed': False ...}
```

**Impact:**
- **Fresh project:** the config that `config-new-project` created stays on disk. It still holds the copied global keys that R13's reconcile exists to remove, such as `resolve_model_ids: "omit"`. That is neither the before state nor the after state.
- **Marker:** it stays held, so every later `apply` refuses until the user cleans up by hand.
- **Directories:** the `.planning/` (and `scripts/`) the run created are not removed. This breaks the R13 amendment ("removes dirs a failed run created").
- **CLI output:** `_cmd_apply` never prints the JSON report. The agent sees a Python traceback, so the SKILL.md failure states (`restore_error`, exit 1) never apply.
- **Existing config:** it is not modified, but the marker is still left held.
- **Tests:** none cover these paths. A grep for `TimeoutExpired`/`SubprocessError` in the four test modules finds nothing.

**Fix:** guard the whole pre-commit window once, and make `_new_project` report failure instead of raising:

```python
## apply.py
import subprocess

def _new_project(call: Any) -> bool:
    try:
        proc = call.run_fn([...], capture_output=True, text=True, check=False,
                           timeout=120, env=None if call.env is None else dict(call.env))
    except (OSError, subprocess.SubprocessError):
        return False
    return proc.returncode == 0

def _execute_apply(ctx: ExecuteCtx) -> tuple[int, dict]:
    ...
    blocked = _take_backup(config_path, project_dir, progress, ctx.deps, ctx.report)
    if blocked is not None:
        return blocked
    try:
        prepared = _prepare_writes(prep)
        if isinstance(prepared, tuple):
            return prepared
        performed = _apply_script_step(script_ctx)
        if performed is None and ctx.report.get("error"):
            return 1, ctx.report
        if not _apply_config_writes(write_ctx):
            return 1, ctx.report
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        return _rollback_report(progress, config_path, ctx.report, str(exc))
    ctx.report["applied"] = True
    ...
```

`_rollback` already handles `progress.runner is None` and a recorded `progress.snapshot`, so a failure between the snapshot and the runner write is cleaned up correctly. Add unit tests that inject `OSError` from `snapshot_file`/`update_marker` and `TimeoutExpired` from `config-new-project`. Each must assert exit 1, no config file left, no marker and no created dirs.

### Warnings

#### WR-01: `subprocess.TimeoutExpired` escapes the post-commit skill check and both follow-up subprocess paths

**File:**
- `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/apply.py:500-531`
- `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/followups.py:121-142, 373-398`

**Issue:** All three sites run subprocesses with a `timeout=` but catch only `(OSError, ValueError)`. `subprocess.TimeoutExpired` is a `SubprocessError`, not an `OSError`. The shared `gsd_tools.config_set_strict` correctly catches `(OSError, subprocess.SubprocessError)`, so these three are inconsistent with it.
- `verify_skills` (518) runs after the commit point.
- `effort_dry_run_count` (131) runs inside `_attach_followups` after commit, and also on every `followups` listing.
- `_run_one` (387) runs `npx -y ...` with `timeout=600`, so a slow registry makes this a realistic case.

There is also a second escape path: `data.get("warnings")` (529) and `body.get("changes")` (139) raise `AttributeError` when the JSON is valid but is not an object.

**Proven at runtime** (agent-skills call raising `TimeoutExpired`):

```
P2 ESCAPED: TimeoutExpired
P2 marker: {'committed': True, 'runner': {'kind': 'change', ... 'snapshot': '.../cross-ai.mjs.ai-kit-apply-backup'}, ...}
P2 leftover snapshots: ['cross-ai.mjs.ai-kit-apply-backup']
```

**Impact:** SPEC R13 says that after the commit point, "the skill check, snapshot discard, pruning and marker removal only warn". Instead, a committed apply crashes. The report (backup path, writes, follow-ups) is never printed. The marker and the runner snapshot are left behind, and old backups are not pruned. `followups --approve` crashes with no `results` when `npx` exceeds 600 s.

**Fix:** catch `(OSError, ValueError, subprocess.SubprocessError)` at all three sites and check `isinstance(data, dict)` before calling `.get`. Then wrap the post-commit calls `_cleanup_committed`'s `verify_skills` and `_attach_followups` in a warn-only guard, so nothing after the commit point can raise:

```python
try:
    report["skill_check"] = verify_skills(...)
except Exception as exc:  # post-commit: warn only (SPEC R13)
    report["warnings"].append(f"skill check failed after commit: {exc}")
```

#### WR-02: `plan-set` crashes with a traceback on a malformed JSON value

**File:**
- `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/plan_edit.py:62-66, 85-89`
- `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cli.py:582-586`

**Issue:** `_parse_string_list` and `_parse_json_type` call `json.loads(raw)` with no guard. `json.JSONDecodeError` is a `ValueError`, not a `PlanEditError`, and `_cmd_plan_set` catches only `plan_edit.PlanEditError`.

This affects every list key (`review.default_reviewers`, `agent_skills.*`, `agent_skills_security.trusted_global_roots`), `script:cross-ai.prefer`, and object-typed keys.

**Proven at runtime:**

```
review.default_reviewers UNCAUGHT JSONDecodeError
agent_skills.gsd-planner UNCAUGHT JSONDecodeError
script:cross-ai.prefer UNCAUGHT JSONDecodeError
B ESCAPED from cli.main: JSONDecodeError   (plan-set review.default_reviewers codex)
```

**Impact:** the most natural typo for these keys is passing `codex` instead of `'["codex"]'`. It produces a Python traceback with exit 1 instead of the documented one-line refusal with exit 2. Agents that branch on exit 2 will misclassify it.

**Fix:**

```python
def _parse_string_list(key: str, raw: str) -> list[str]:
    try:
        parsed = json.loads(raw)
    except ValueError as exc:
        raise PlanEditError(f"{key}: expected a JSON list of strings (got {raw!r})") from exc
    ...
```

Do the same in `_parse_json_type`, and add a test for each key family.

#### WR-03: `plan.host` is never bound to `inventory.host`, so a hand-edited host passes every trust-boundary check

**File:**
- `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/plan_io.py:444-453, 480-491, 697-707`
- `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/apply.py:58-79, 238-247`
- `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cli.py:522-549`

**Issue:** The inventory digest binds the plan to the inventory, but the digest covers only the inventory, not the plan. Neither `validate_plan` (which checks only `host in HOSTS`) nor `check_plan_inventory` (which checks only trusted-roots `existing`) compares `plan["host"]` with `inv["host"]`.

Everything downstream then trusts `plan["host"]`:
- `resolve_target` -> `host.resolve_gsd_core(..., plan["host"])` picks the host-first local root;
- `_validate_prefer` forbids only the *plan* host as an execution target (705);
- `plan_edit._assert_runner_target` uses `call.plan.get("host")`;
- `verify_skills` sets `GSD_RUNTIME=<plan host>`;
- `build_followups` decides installer and effort-sync per plan host.

**Proven:** with inventory host `claude` and the plan's host edited to `codex`, both `validate_plan` and `check_plan_inventory` return `None`.

**Impact:**
- With an opencode inventory and a plan edited to `claude`, `prefer: ["opencode"]` validates. That makes the real host CLI an execution target, which is a SPEC must-not (R2/R3).
- The skill references, computed for the inventory host, are written while gsd-core is resolved and checked for another runtime.
- The opencode installer follow-up is silently not offered.

**Fix:** add the check once in `check_plan_inventory`. It is already called by `apply.load_inputs` (and so by `followups`) and by `cli._load_plan_inputs` (`plan-set`/`plan-unset`):

```python
if plan.get("host") != inv.get("host"):
    return (f"plan host {plan.get('host')!r} does not match the inventory host "
            f"{inv.get('host')!r}; rerun recommend")
```

#### WR-04: The "~/-relative" trusted-root rule accepts `~/..` traversal, even without `--force`

**File:**
- `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/plan_edit.py:484-490, 544-554`
- `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/plan_io.py:619-630`

**Issue:** Both validators accept any element for which `element.startswith("~/")` is true. gsd-core's `loadTrustedGlobalRoots` (`.claude/gsd-core/bin/lib/security.cjs:177-230`) expands `~/` with `path.join(homedir, rest)`, then runs `realpathSync`. It rejects only the filesystem root and the home dir itself. So `~/../..` resolves to the parent of the home's parent (`/var` on this machine) and is accepted as a trusted root.

**Proven:** once the trusted-roots choice was decided, `plan-set agent_skills_security.trusted_global_roots '["~/.agents/skills/react-dev","~/../.."]'` exited 0 without `--force`, and the plan stored `['~/.agents/skills/react-dev', '~/../..']`. A hand-edited plan passes `validate_plan` the same way.

**Impact:** the guard's stated purpose is "must be ~/-relative (only an already-configured root keeps another form)". It can be bypassed, which lets the plan widen gsd-core's symlink-escape allowlist outside `$HOME`. This setting is a security control (`agent_skills_security`).

**Fix:** normalize before accepting, with a shared helper used by both validators:

```python
import posixpath

def home_relative_root(root: str) -> bool:
    if not root.startswith("~/"):
        return False
    rest = posixpath.normpath(root[2:])
    return rest not in ("", ".") and rest != ".." and not rest.startswith("../")
```

#### WR-05: `--force` lets the host's own slug into `review.default_reviewers` (R2 must-not), while the execution side is force-immune

**File:**
- `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/plan_edit.py:443-452`
- `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/plan_io.py:480-491`

**Issue:** `_reviewers_refusal` refuses slugs outside `cross_ai.eligible_lanes(inv)`, and `eligible_lanes` excludes the host. But that refusal is skipped when `call.force` is set. Nothing else, neither in `plan_edit` nor in `validate_plan`, rejects the host slug.

By contrast, the execution half of the same prohibition holds even with `--force`:
- `_assert_runner_target` ignores `force`;
- `_validate_prefer` rejects the plan host at every load.

**Proven:** on a claude inventory, `plan-set review.default_reviewers '["claude"]' --force` exited 0 with `"warnings": []`.

**Impact:** SPEC prohibition "MUST NOT make the host CLI a review lane or an execution target (R2, R3)" is enforced for execution only. A single `--force`, used to pin some unrelated non-lane slug, silently also admits self-review. There is no warning.

**Fix:** refuse the host slug regardless of `force` in `_reviewers_refusal`. Also add `validate_plan` coverage, using the plan host, so hand edits are caught at every load:

```python
host = call.inv["host"]
if host in value:
    raise PlanEditError(f"{host!r} is the host CLI and cannot be a review lane")
```

#### WR-06: Dry run hides the reconcile removals apply performs on a fresh project (R12 "see everything")

**File:** `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/apply.py:154-171, 306-320, 869-874`

**Issue:** On an absent config, apply runs `config-new-project`, which copies `~/.gsd/defaults.json`. It then unsets every managed or conflict key from that copy that is not in the plan (`reconcile_writes`, 869). `dry_run_report` diffs only `plan["entries"]` against `live == {}`, so none of those removals appear. The e2e test `test_absent_config_reconciles` shows `resolve_model_ids` and `model_policy.*` being reconciled, and a dry run of the same plan shows no `remove` row for them.

**Impact:**
- R12 ("It prints an add / change / keep / remove diff ... see everything") is not met for the fresh-project path.
- The marker's recovery text tells the user to trust "if its diff holds only keep rows, that apply finished its writes". That check cannot see an interrupted reconcile.

**Fix:** when the config is absent, predict the reconcile from the inventory's recorded `global_defaults.values` and add rows marked as predicted:

```python
if not os.path.isfile(target.config_path):
    for key, _ in reconcile_writes(inputs.plan, inputs.inv["global_defaults"]["values"],
                                   inputs.plan["host"]):
        rows.append({"key": key, "kind": "remove", "from": "<copied global default>",
                     "to": None, "predicted": True})
```

Because `global_defaults.values` is allowlist-filtered, label these rows "predicted (unverified)", per the AGENTS.md certainty rule.

#### WR-07: Installer version is unvalidated: the VERSION-file text flows straight into the `npx` package spec

**File:** `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/followups.py:1-3, 42-43, 156-161`

**Issue:** The module docstring promises the installer argv pins `@opengsd/gsd-core` "to the inventory-resolved version (never an npm dist-tag name)". In practice, `_inventory_version` accepts any non-empty string other than `"unknown"`.

That string comes from `gsd_tools.gsd_core_version`, which is the raw text of the resolved gsd-core's `VERSION` file. That file can be project-local, inside the target checkout. `inventory._validate_gsd_core` checks only "str or null". So a `VERSION` of `latest`, `next`, `file:../x` or `git+https://...` becomes `npx -y @opengsd/gsd-core@<that> --opencode --local`.

**Impact:**
- The "pinned version" guarantee (SPEC R14) is not enforced.
- An untrusted checkout, or a hand-edited inventory, can turn the approved follow-up into an `npx` run of an arbitrary package spec under an `@opengsd/gsd-core@` prefix. Only the user's reading of the argv before approval stands in the way.

**Fix:**

```python
_SEMVER = re.compile(r"\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?")

def _inventory_version(inv: dict) -> str | None:
    version = (inv.get("gsd_core") or {}).get("version")
    if not isinstance(version, str) or not _SEMVER.fullmatch(version):
        return None   # -> existing "version is unknown" note
    return version
```

#### WR-08: `followups --approve` runs while an apply marker is held (including after a failed restore)

**File:** `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cli.py:654-684`

**Issue:** `_cmd_followups` binds the destination through `resolve_target`, but it never reads the apply marker. While a `.ai-kit-apply-marker` exists, `--approve` still runs the installer and `effort sync --apply`. That covers both cases: an apply still in progress, or one that ended with `restore_error`, where SKILL.md says the config may still hold a partial state.

**Impact:** `effort sync --apply` pushes effort settings from a config that may be half-written into agent frontmatter. This spreads a failed apply's partial state beyond the config, which the backup and restore cannot undo. SPEC R14 also says follow-ups run "after a successful apply".

**Fix:** refuse with the same recovery text apply uses:

```python
marker = config_backup.read_marker(target.config_path)
if marker is not None and args.approve:
    print("ai-kit-gsd-curated-config: "
          + config_backup.recovery_text(marker, target.config_path), file=sys.stderr)
    return 2
```

### Info

#### IN-01: The `forced` flag sticks to the canonical `workflow.cross_ai_command`, giving a false full-permissions warning

**File:**
- `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/plan_edit.py:564-567`
- `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/apply.py:298-303`

**Issue:** `_apply_entry` pops `forced` for every key except `workflow.cross_ai_command`. So `plan-set ... "node other.mjs" --force` followed by `plan-set ... "node .planning/scripts/cross-ai.mjs"` leaves `forced: true` on the canonical command.

**Proven:** `_apply_warnings` then returns `['workflow.cross_ai_command overrides the runner; gsd-core runs it with full permissions']` for the canonical runner. A warning that fires when nothing is overridden trains users to ignore the real one (D-44's control is disclosure).

**Fix:** drop the key exception, i.e. `elif "forced" in entry: entry.pop("forced")`. `validate_plan` already accepts the canonical command without `forced`.

#### IN-02: The marker records the backup as a bare basename, so the recovery text is not a usable path

**File:**
- `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/apply.py:838-840`
- `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/config_backup.py:227-230`

**Issue:** The recovery text reads "put config.json.bak-20261015T120000Z back over /abs/.planning/config.json", while the runner snapshot in the same text is absolute. An agent acting from another cwd will not find the file.

**Fix:** resolve the basename in `_recovery_config_step` with `os.path.join(os.path.dirname(config_path), backup)`. Keep the basename in the marker so it stays relocatable.

#### IN-03: `_clear_runner_marker` deletes the snapshot before updating the marker

**File:** `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/apply.py:610-613, 774-778`

**Issue:** In the `.new` divert path, the snapshot is discarded first. Then `update_marker(runner=None)` runs, and its `OSError` is suppressed (777). If that update fails and the process later dies, the held marker still says "put <snapshot> back over <runner>" for a snapshot that no longer exists.

**Fix:** update the marker first, then discard the snapshot.

#### IN-04: An inventory without `existing_config.path` crashes apply with `KeyError` instead of the clean message

**File:**
- `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/apply.py:225`
- `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/plan_io.py:251-256`

**Issue:** `_validate_config_section` does not require `path`. `_target_for_core` indexes `inputs.inv["existing_config"]["path"]`, but `_config_binding_error` already handles a non-str value with a clear "rerun inventory" message. The failure happens before any write.

**Fix:** use `.get("path")`, or validate `path` as str in `_validate_config_section`.

#### IN-05: A failed apply leaves its `cross-ai.mjs.new` behind, and a re-render silently overwrites an existing `.new`

**File:**
- `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/apply.py:616-639, 774-779`
- `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cross_ai_script.py:217-235` (cross-reference)

**Issue:**
- `_rollback` never removes a `.new` that this apply wrote, so a render for a plan that was rolled back stays next to the runner as "merge it by hand".
- `_publish(path + ".new")` replaces any existing `.new` with no check, including one the user is merging by hand.

**Fix:**
- Record a `.new` in `Progress` that this apply created, and remove it on rollback.
- Refuse, or pick a `-<n>` suffix, when a `.new` already exists.

#### IN-06: The failure stderr line does not name the failing key, and an empty error string is treated as "no error"

**File:** `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/apply.py:790-792, 902` and `cli.py:705-706`

**Issue:**
- `report["error"]` is set to gsd-tools' stderr. When that is empty, `_cmd_apply` prints no stderr line at all; `failed_key` appears only in the stdout JSON.
- `_execute_apply` decides whether the runner step failed from the truthiness of `report["error"]` (902). An empty exception message would let config writes continue after `_rollback` has already cleared the marker.

**Fix:**
- Set `report["error"] = f"config-set {key} failed: {output or 'no output'}"`.
- Have `_apply_script_step` return an explicit failure flag instead of signalling through `report["error"]`.

#### IN-07: Python `==` treats `0 == False` and `1 == True` when deciding "already applied"

**File:** `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/apply.py:148, 459, 576`

**Issue:** A live `0` for a planned `false`, or a live `1` for a planned `true`, is reported as `keep` and skipped. The config keeps a number where the plan wants a boolean, but JS `===` and gsd-core's schema treat those as different values.

**Fix:** compare with type, for example `type(a) is type(b) and a == b`, or use a `json.dumps(..., sort_keys=True)` equality helper.

#### IN-08: The approval is not bound to the block the user saw, and duplicated CLI helpers

**File:**
- `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/followups.py:313-342`
- `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cli.py:522-549, 560-569, 600-609`

**Issue:**
- `followups --approve` rebuilds the block from the current plan and environment, and `--require` only adds ids (`followup_ids(...) | set(force_ids)`). A `plan-set` or a newly installed local gsd-core between the listing and the approval changes what runs, with no fingerprint check.
- Quality: `_print_plan_set_ok`/`_print_plan_unset_ok` are identical, and `_load_plan_inputs` duplicates `apply.load_inputs`' digest and `check_plan_inventory` logic.

**Fix:**
- Put a short digest of the `required` argv rows in `approve_with` and refuse when the rebuilt block differs.
- Merge the duplicated helpers.

---

_Reviewed: 2026-10-15T23:26:28Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: deep_

# Batch C


## Phase 18 (batch C): Code Review Report

**Reviewed:** 2026-10-15T23:27:03Z
**Depth:** deep (cross-file: cli.py, plan_io.py, plan_edit.py, apply.py, cross_ai.py,
catalog_adapter.py, config_backup.py, ai_kit_spec/detection.py, ai_kit_spec/local_secrets.py,
and the installed gsd-core 1.16 `security.cjs` / `init.cjs` / `runtime-homes.cjs` /
`config-loader.cjs` were read to verify behavior at the module boundaries)
**Files Reviewed:** 21
**Status:** issues_found

### Summary

Batch C covers the skill inventory, skill affinity and the recommend layers that consume them.
The global-root escape check, the plugin `enabledPlugins` layering, the per-rigor caps, the
recommend purity import guard, the pi RPC parser's None/[] split and the 40 % CPU cap in the
parallel runner all behave as specified. But the project-skill escape check models the wrong
containment root, so it disagrees with gsd-core in both directions. Several other problems
sit at the trust and certainty boundaries:

- a dropped `connect_fn` seam makes a unit test do real network I/O;
- YAML block-scalar descriptions are misparsed (this repo's own `markdown-to-pdf` and
  `mermaid-audit` skills parse to `>-`);
- skills under an already-configured absolute trusted root are refused;
- the trusted-root approval can drop the user's existing roots;
- the "wire with plan-set" proposal crashes plan-set with a traceback;
- unverified facts (plugin layering, URL-only System One) reach the plan at full confidence.

Each finding below was verified against the current source. A finding marked "verified by
execution" was reproduced with a pure in-process call (`python3 -B`, no file writes).

### Narrative Findings (AI reviewer)

### Critical Issues

#### CR-01: Project-skill escape check uses `<project>/skills` as the containment root; gsd-core uses the project root

**File:** `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/skill_scan.py:106-114, 243-244`
(consumed by `skills.py:120-141, 216-225` and `apply.py` `skill_value`)

**Evidence:** `scan_skills` calls `scan_root(proj_root, "project", "skills", home)` with
`proj_root = <project>/skills`, and `_escapes_root(skill_dir, root_dir)` compares the realpath of
the skill directory and of its `SKILL.md` with `realpath(<project>/skills)`. gsd-core 1.16 resolves a
project reference `skills/<name>` with `tryWithinRoot(skillPath, projectRoot)` (`init.cjs`
`buildAgentSkillsBlock`). That call compares the realpath of the **skill directory** with
`realpath(projectRoot)` (`security.cjs` `validatePath`), not the `skills/` dir, and never
realpaths `SKILL.md`. The two models disagree in both directions:

- `<project>/skills -> ~/shared/skills` (a symlinked `skills/` root). ai-kit sees every skill
  inside its realpath root, so `escapes_root=False` and `locate()` wires `skills/<name>`.
  gsd-core then rejects it: "Skipping unsafe path ... not confined to the project directory".
- `<project>/skills/foo -> <project>/vendor/foo`, or `skills/foo/SKILL.md -> <project>/docs/foo.md`.
  ai-kit sets `escapes_root=True`, refuses to wire the skill, and emits
  `"not wired: foo (its project copy resolves outside the project)"`. That statement is
  false, and gsd-core would accept the skill. `plan-set` then also refuses it
  (`plan_edit._skill_installed`).

**Impact:**

- The first case violates SPEC R8's acceptance ("written values pass gsd-core's own reference
  check with no skip warning"). apply detects this only after the commit point (warning-only
  `verify_skills`).
- The second case drops a valid skill and states an unverified, false fact (AGENTS.md certainty
  rule).

**Fix:** Give project rows gsd-core's own containment rule, and leave the `SKILL.md`-realpath
rule (which does match gsd-core) on global rows only:
```python
def _escapes_project(skill_dir: str, project_dir: str) -> bool:
    proj_real, dir_real = _real(project_dir), _real(skill_dir)
    return proj_real is None or dir_real is None or not _inside(dir_real, proj_real)
```
Pass `project_dir` into `scan_root` for `root_kind == "project"`. Amend D-31 so project rows
use this rule. Add two tests: a symlinked `skills/` root pointing outside the project (expect
unwired), and `skills/foo -> <project>/vendor/foo` (expect wired as `skills/foo`).

### Warnings

#### WR-01: `inventory` drops the injected `connect_fn`, so a unit test makes a real TCP/DNS probe

**File:** `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cli.py:446-457`;
`tests/test_curated_config_skills.py:435-469`

**Evidence:** `main()` computes `probe` and passes it to `_cmd_inventory(..., connect_fn)`, but
`_cmd_inventory` builds `host.InventoryDeps(which_fn, run_fn, env_fn)` and never passes it on.
`InventoryDeps.connect_fn` therefore always defaults to `socket.create_connection`. The bug
dates from `656b30d` (18-03). pylint's globally disabled `unused-argument` hid it, and the
18-03 SUMMARY claims the opposite ("optional connect_fn on inventory CLI for injectable
connects in tests"). `test_key_value_never_in_output` sets
`JEV_API_URL=https://user:pw-SENTINEL@h:1/` and passes a fake `connect`. The fake is ignored
and the test does a real `getaddrinfo("h")` plus a connect to port 1. Its `_calls` result is
never asserted, so the drop goes unnoticed.

**Impact:** The unit tier does non-hermetic network I/O, which adds up to 1.5 s of latency and
behaves differently on a network where `h` resolves through a search domain. The test seam the
SUMMARY claims does not exist.

**Fix:**
```python
deps = host.InventoryDeps(which_fn, run_fn, env_fn, connect_fn)
```
Assert `calls` in `test_key_value_never_in_output`, so a future drop fails.

#### WR-02: `_parse_description` misreads YAML block scalars with chomping/indent indicators (`>-`, `|-`, `>+`, `|2`)

**File:** `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/skill_scan.py:83-88`

**Evidence:** Only the exact `rest in (">", "|")` starts a block. `description: >-` falls through
to the plain-scalar path, so the description becomes the literal `">-"`. Verified by execution:
this repo's own `skills/markdown-to-pdf/SKILL.md` and `skills/mermaid-audit/SKILL.md` both
parse to `'>-'`. `skills.proposals()` then emits
`"unknown skill markdown-to-pdf (project): >-; wire with plan-set agent_skills.<agent>"`.

**Impact:**

- SPEC R9 bases each proposal on the skill's description, so these proposals carry garbage.
- The "empty description is skipped" edge rule is bypassed, because `">-"` is non-empty.
- `>-` is a common SKILL.md frontmatter form, so this hits real skills, not just edge cases.

**Fix:** Treat any value matching `^[>|][-+]?[0-9]?$` (and `^[>|][0-9][-+]?$`) as a block
indicator:
```python
if re.fullmatch(r"[>|](?:[-+]?[1-9]?|[1-9][-+])", rest):
    in_desc = True
    continue
```
Add a test case for `>-` and `|-`.

#### WR-03: The outside-HOME rule refuses skills that an already-configured absolute trusted root covers

**File:** `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/skills.py:226-233`

**Evidence:** `_can_wire` returns False with the note "resolves outside the home directory" for
any escaping global row without `real_dir_home`. It never consults `covered()`, although
`covered()` (lines 195-206) explicitly supports absolute roots. gsd-core's
`loadTrustedGlobalRoots` accepts any absolute existing root, and the 18-22 amendment says
"an already-configured root is accepted in its recorded form". Take a user with
`trusted_global_roots: ["/opt/skills"]` and a global skill whose real dir is `/opt/skills/foo`.
gsd-core accepts that skill, but ai-kit never wires it and tells the user it cannot be wired.

**Impact:** The plan wrongly drops a usable skill, and the note misleads the user.

**Fix:** Check coverage before refusing:
```python
if (row.get("root_kind") == "global" and row.get("escapes_root")
        and not row.get("real_dir_home")
        and not covered("", row.get("real_dir") or "", existing_roots(ctx.inv))):
```
Keep the rule that recommend never *proposes* an absolute root.

#### WR-04: A dangling `SKILL.md` symlink is inventoried as an installed, addressable skill

**File:** `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/skill_scan.py:142`

**Evidence:** `if not os.path.isfile(skill_md) and not os.path.islink(skill_md): continue`.
`isfile` already follows valid links, so the `islink` clause admits only *dangling* links.
`_real_dir` still returns `dirname(realpath(target))`, and the row gets `addressable: True`.

**Impact:**

- D-32 requires that "its skill file exists". A plugin row is emitted as a `global:<p>:<s>`
  directive, which the Skill tool cannot load.
- For a global row, gsd-core warns "Global skill not found" and skips it (an R8 violation).
- Neither case is visible until after apply.

**Fix:** Drop the `islink` clause (`if not os.path.isfile(skill_md): continue`), or record
`addressable: False` for an unresolvable `SKILL.md`. Add a dangling-link test.

#### WR-05: The unknown-agent note names uninstalled skills, because family ids equal skill names

**File:** `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/skills.py:237-243`;
`skills/ai-kit-gsd-curated-config/skill_affinity.json:24, 35`

**Evidence:** `_wire_agent` emits `"dropped unknown agent {agent} from family {fam_id}"` before
checking whether any family skill is installed. The family ids `ponytail-review` and
`ponytail-debt` are identical to skill names. Verified by execution: on a codex inventory with
`skills: []` and an agent table that lacks `gsd-eval-auditor`/`gsd-security-auditor`, the plan
notes contain "... from family ponytail-review".

**Impact:** This breaks the SPEC R9 prohibition ("plan, report and notes never name an
uninstalled recommended skill") whenever the host gsd-core's `AGENT_TO_PHASE_TYPE` drifts.
The live 1.16 table holds every affinity agent, so the bug appears only on an older or newer
gsd-core. It also fills notes with drop messages for families that would wire nothing.

**Fix:** Emit the note only when at least one family skill passes `_can_wire`. Rename the
family ids so they cannot collide with skill names (for example `ponytail-review-set`), and
make `validate_affinity` reject an id that equals any skill name in the file.

#### WR-06: Proposals offer skills that cannot be wired, and list duplicates once per root

**File:** `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/skills.py:368-408`

**Evidence:** `proposals()` filters on `addressable` and on the description only. Each case
below still gets a "wire with plan-set agent_skills.<agent>" proposal:

- An escaping project-only copy. `plan_edit._skill_installed` (plan_edit.py:471-481) then
  refuses it ("not installed or not addressable").
- A global skill outside HOME. plan-set accepts it, apply writes `global:<name>`, and gsd-core
  skips it with no trusted-root option.

A name present in several roots (for example global and plugin) produces several proposals
with the same `key`, and each duplicate counts toward `PROPOSAL_CAP`.

**Impact:** The proposals lead to a refusal or a silent skip, and the cap is spent on
duplicates.

**Fix:** Build proposals from the distinct names for which `locate()` returns a row and
`_can_wire`'s rules pass (use a side-effect-free variant of `_can_wire`). Dedupe by name
before applying the cap.

#### WR-07: Following the proposal text ("wire with plan-set agent_skills.<agent>") crashes plan-set with a traceback

**File:** `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/plan_edit.py:62-66`
(the proposal text comes from `skills.py:396`)

**Evidence:** `_parse_string_list` calls `json.loads(raw)` without a guard. Verified by
execution: `parse_value("agent_skills.gsd-planner", "ponytail", None)` raises
`JSONDecodeError`. `_cmd_plan_set` catches only `PlanEditError`, so
`plan-set agent_skills.gsd-planner ponytail`, the natural reading of the proposal, exits with
an uncaught traceback. The proposal text never says that a JSON list is required.

**Impact:** The documented wiring path ends in a crash instead of a one-line exit-2 refusal.
The CLI elsewhere promises "never a traceback".

**Fix:**
```python
try:
    parsed = json.loads(raw)
except ValueError as exc:
    raise PlanEditError(f"{key}: expected a JSON list of strings, e.g. '[\"name\"]'") from exc
```
Change the proposal text to `wire with plan-set agent_skills.<agent> '["<name>"]'`.

#### WR-08: Approving a trusted root with the candidate value silently drops the user's existing trusted roots

**File:** `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/skills.py:312-349`;
`plan_edit.py:484-491, 544-554`

**Evidence:** The `needs_choice` entry's `candidates` carry only the *new* per-skill values.
The full approval list (existing plus new) appears only inside the `why` prose.
`_check_trusted_roots` accepts any list whose elements are existing, candidates or `~/`-prefixed.
It never requires `existing ⊆ value`. So
`plan-set agent_skills_security.trusted_global_roots '["~/.agents/skills/react-dev"]'`, built
from the candidate value, passes. apply then replaces `["~/vault", ...]` with the single root.

**Impact:** User config is lost. Skills trusted through the dropped roots start being skipped
by gsd-core. The change is recoverable only from the apply backup.

**Fix:** Do one of the following:

- have plan-set merge the existing roots into the value for this key (order-preserving union)
  and warn when the user's list omits an existing root;
- refuse a list that drops an existing root unless `--force` is given.

Also store the merged list as the single candidate `value`.

#### WR-09: The approval command in `why` is not shell-quoted

**File:** `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/skills.py:343-349`

**Evidence:** The `why` embeds `'{payload}'`, where `payload` is `json.dumps` of filesystem-derived
paths and of strings from the project config. `json.dumps` does not escape `'`, so a root such
as `~/Bob's skills/x`, or any existing root that contains `'`, produces a broken command.
A crafted directory name produces an injected shell fragment. SKILL.md tells the agent to run
the `plan-set` command shown.

**Impact:** The suggested command breaks or misbehaves when an agent copies and runs it
verbatim.

**Fix:** Use `shlex.quote(payload)`. Stdlib `shlex` does no I/O, so `skills.py` stays pure.
```python
f"approve with plan-set agent_skills_security.trusted_global_roots {shlex.quote(payload)} "
```

#### WR-10: Inventory `skills[]` validation skips fields that recommend and apply consume

**File:** `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/plan_io.py:98-120`

**Evidence:** `_skill_entry_problem` checks only `name`, `root_kind`, `escapes_root` and
`addressable`. Each unchecked field leaks downstream:

- `real_dir_home` is used verbatim as a trusted-root candidate (`skills.py:322-330`).
  plan-set's `_trusted_root_ok` accepts any candidate-pool member, so a non-`~/` value from a
  stale or edited inventory passes plan-set. Only apply's `validate_plan` refuses it.
- `plugin` is written verbatim by `apply.skill_value` -> `reference_for` as
  `global:<plugin>:<name>`. Nothing downstream re-validates it.
- `name` is not checked against `^[A-Za-z0-9_-]+$` when `addressable` is true, so recommend
  can write a plan that its own `validate_plan` rejects. "rerun recommend" then reproduces the
  same plan.
- `real_dir`, `root` and `description` types, and `root_kind` membership in
  {project, global, plugin}, are unchecked.

**Impact:** The trust-boundary validation is incomplete, and problems surface late (apply)
or post-commit (gsd-core skip warnings).

**Fix:** In `_skill_entry_problem`, require all of the following:

- `name` fullmatches the pattern when `addressable` is true;
- `plugin` is `None` or fullmatches it;
- `real_dir_home` is `None` or a string starting with `~/`;
- `real_dir`, `root` and `description` are strings;
- `root_kind` is in the allowed set.

#### WR-11: Unverified detection facts reach plan entries at full confidence

**File:** `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/recommend.py:1076-1119`;
`inventory.py:374-383`

**Evidence:** The plugin-layering caveat ("enabledPlugins layering assumed per key
(unverified)") exists only in the inventory's `info`. The System One caveat ("reachable, not
verified as System One") exists only in `inventory.system_one_backend.note`. `_skills_layer`
never reads either. The claude goldens show `agent_skills.gsd-planner: ["ponytail"]` with
`why: "family ponytail-core: ponytail"`, with no `effect` or flag, even though that wiring
depends on the unverified layering. A jev entry produced only by URL reachability carries no
caveat either.

**Impact:** This breaks the AGENTS.md rule that inferred classifications are visibly flagged.
The plan, which is the artifact the user reviews, shows these facts as certain.

**Fix:**

- Add `effect: "unverified: enabledPlugins per-key layering assumed (D-32)"` to each
  `agent_skills.*` entry whose wired skill resolves to a plugin row.
- When `via == ["url_reachable"]`, add `effect: "backend reachable, not verified as System One"`
  to the jev entries.

#### WR-12: A failed model enumeration and an empty one collapse into the same misattributed reason

**File:** `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/inventory.py:143-165`;
`recommend.py:751-761`; `cross_ai.py:59-66`; `catalog_adapter.py:291-296`

**Evidence:** `parse_pi_models` and `build_runtimes_snapshot` correctly keep None (listing
failed, so no `models` key) apart from `[]` (an empty listing). The curated-config boundary
erases the difference:

- `_runtime_candidates` returns `[]` for both cases.
- `_catalog_fields` records only `installed`.
- The pi target's `why` becomes "no execution model within ceiling". Verified by execution
  with pi installed and no candidates.

`_no_lane_reason` has a related problem. With `installed_runtimes == ["claude"]` on a claude
host, it reports "no enumerated models on an installed non-host lane", although no non-host
lane is installed at all.

**Impact:** The plan states the wrong cause. A broken pi RPC reads as a price-ceiling
outcome, which violates the certainty rule. The user cannot tell "fix pi" from
"plan-set a model".

**Fix:**

- In `_catalog_fields`, record a per-runtime status: `enumeration: "failed" | "empty" | "ok"`,
  where "failed" means the `models` key is absent.
- In `_pick_for_runner`, give an empty pool its own why: "no <cli> models enumerated
  (listing failed)" or "... (listing empty)".
- In `_no_lane_reason`, test for installed *non-host* lane binaries rather than for an empty
  `installed_runtimes`.

#### WR-13: The negative R11 jev tests are vacuous

**File:** `tests/test_curated_config_skills.py:808-819`

**Evidence:** `test_jev_without_backend_not_wired` and `test_jev_backend_without_skill_silent`
use `make_inventory()`, whose `agent_to_phase_type` lacks `gsd-advisor-researcher` and
`gsd-assumptions-analyzer` (verified). The system-one family is therefore always dropped
through the unknown-agent path, and that note names only agents and the family id. Both
`assertNotIn("jev-fast-decision", blob)` checks would pass even if the `when` gate or the
installed check were deleted. `test_missing_skill_never_named` has the same hole for
`systematic-debugging`: its agents are also unknown in `make_inventory`.

**Impact:** SPEC R11's acceptance fixtures "skill without backend (none)" and "backend without
skill (none)" do not actually test the gate.

**Fix:** Add the two agents to `agent_to_phase_type`, as `test_jev_once_with_backend` already
does. Assert that the remaining notes contain no `affinity_agent` note for them. Add a
non-vacuity assertion that the same inventory *with* the backend wires jev.

#### WR-14: SKILL.md does not match the CLI and overstates the write guarantee

**File:** `skills/ai-kit-gsd-curated-config/SKILL.md:3, 15-16, 50-51, 56-57, 70-72, 196-199`;
`README.md:45`

**Evidence:**

1. **Inventory output and the implicit inventory file (lines 56-57, 70-72, 196-199).**
   `inventory` writes JSON to stdout (`cli.py:463`). SKILL.md never says to save it, yet every
   later step needs `<inv.json>`. Lines 71-72 omit `--inventory`, so plan-set and plan-unset
   silently load `inventory.json` beside `plan.json` (`plan_io.sibling_inventory_path`).
   Neither that default nor the file name is documented, and the subcommand table lists only
   `key, value, --plan`. An agent that follows the steps literally gets
   "inventory .../inventory.json: cannot read".
2. **`--project-dir` (lines 50-51).** The text says every project-touching subcommand takes
   `--project-dir`, but `recommend`, `plan-set` and `plan-unset` reject it (argparse exit 2).
   The examples also use a bare `ai-kit-gsd-curated-config.py` instead of `"$ENTRYPOINT"`.
3. **Needless `--force` (line 71).** The example passes `--force` with the canonical
   `node .planning/scripts/cross-ai.mjs` value. `--force` is unnecessary there, and the example
   teaches agents to reach for `--force` on the one key that gsd-core runs with full
   permissions (D-44).
4. **Write guarantee (lines 3, 15-16; README row "all writes via gsd-tools").** The docs claim
   every write goes through the gsd-tools wrappers, "never a hand-edited JSON file". In fact
   `config_backup.restore_backup` (config_backup.py:139-150) writes the config bytes directly,
   or unlinks the config, and the runner and plan are written directly as well. SPEC R13 calls
   the restore "the one sanctioned write outside gsd-tools".

**Impact:** Following SKILL.md fails at the plan-edit step. The docs overstate a safety
guarantee.

**Fix:**

- Show `inventory ... > <dir>/inventory.json`, document the sibling-inventory default, and
  add `[--inventory]` to the table.
- Restrict the `--project-dir` sentence to inventory, apply and followups, and use
  `python3 "$ENTRYPOINT"` in every example.
- Drop `--force` from line 71.
- Reword lines 3 and 15-16 and the README row: "config keys are written only through
  gsd-tools; a failed apply restores the backup bytes directly (D-21)".

### Info

#### IN-01: `SKILL_NAME_RE.match` with `$` accepts a trailing newline

**File:** `skill_scan.py:18, 147-148`

Verified: `re.match(r"^[A-Za-z0-9_-]+$", "foo\n")` returns True, while `fullmatch` (used by
`plan_io`/`plan_edit`) and gsd-core's JS regex reject it. A plugin `plugin.json` `name` of
`"ponytail\n"` is recorded addressable, and apply writes `global:ponytail\n:<skill>`, which
gsd-core then skips. Use `SKILL_NAME_RE.fullmatch` (or `\Z`).

#### IN-02: Recommend's purity docs and its dynamic test omit the skills layer

**File:** `recommend.py:1-6`; `tests/test_curated_config_recommend.py:1811-1823`

The module docstring lists the allowed imports without `.skills`. `test_build_plan_pure_and_deterministic`
builds `RecommendOpts` without `affinity`, so `_skills_layer` never runs under the I/O raisers.
The static AST guard does cover `skills.py`. Pass `affinity=_shipped_affinity()` in the dynamic
test and update the docstring.

#### IN-03: `trusted_roots` always returns an empty `notes` list

**File:** `skills.py:312-340`

`notes` is never appended to, and the caller discards it (`recommend.py` `_root_notes`).
Return only `candidates`.

#### IN-04: `ponytail_visibility.claude` reads `[]` on hosts that wire ponytail from the plugin

**File:** `skill_scan.py:261-273`

On claude the ponytail skills come from the plugin cache, but the visibility record scans only
`~/.claude/skills`. The inventory therefore says "not visible on claude" while the claude plan
wires `global:ponytail:*`. The function also calls `scan_root(..., home="")`, which runs
`realpath("")` (the current working directory) and reads every `SKILL.md` description for
nothing. Either merge plugin rows into the claude entry or document the field as
"global-root only", and pass the real `home`.

#### IN-05: `_tcp_reachable` catches only `OSError`

**File:** `skill_scan.py:292-309`; `tests/test_curated_config_skills.py:398-412`

`socket.create_connection` raises `UnicodeError` (a `ValueError`) for IDNA-invalid hosts such as
`http://a..b/`. The worker thread then prints a traceback to stderr through
`threading.excepthook`. `test_slow_connect_times_out`'s fake returns `None`, so `None.close()`
raises `AttributeError` in the leaked thread at cleanup. Catch `Exception` in the worker and
return a closable fake in the test.

#### IN-06: `test_empty_agent_no_entry` asserts an impossible outcome

**File:** `tests/test_curated_config_skills.py:660-670`

The family targets only `gsd-planner`, yet the test asserts that `gsd-debugger` is absent,
which is always true. Assert that `"gsd-planner" not in resolved` instead.

#### IN-07: The node query hardcodes its runtime list, and a per-host null root is silent

**File:** `gsd_catalog.py:161-162`; `inventory.py:344-358`

The JS `rts` list duplicates `host.HOSTS`. When `getGlobalSkillsBase(<current host>)` throws,
that host's root is `null`. `scan_skills` then skips global skills with no warning, because only
a whole-`null` dict warns. Pass `host.HOSTS` in through argv, and warn when the current host's
root is `null`.

#### IN-08: `covered()` treats an existing root of `/` as covering everything

**File:** `skills.py:195-206`

`"/".rstrip("/")` is `""`, and `real_dir.startswith("" + "/")` is always true. gsd-core drops
`/` (and `~`) as too broad, so ai-kit would suppress a needed proposal. Skip filesystem-root
and home roots in `covered`.

#### IN-09: Rigorous review with two eligible lanes but no vendor-different second pick returns one lane and no note

**File:** `cross_ai.py` `select_lanes` (outside batch C; verified because recommend relies on it)

The "only one eligible review lane" note fires only when `len(eligible) == 1`. When
`second_ranked` comes back empty, there is no note, which contradicts SPEC R2 ("otherwise 1
lane plus a note"). Add the note in that branch as well.

#### IN-10: `inventory` is documented as read-only but makes a TCP connection

**File:** `inventory.py:447-449`; `SKILL.md:53`

When `JEV_API_URL` is set, inventory opens a TCP connection to it. SKILL.md step 1 says
"read-only" and never mentions the probe. Add one line about it.

#### IN-11: The presence-only key check reads a CWD-relative secrets file when `HOME` is unset

**File:** `skill_scan.py:312-316` -> `ai_kit_spec/local_secrets.py:8-9`

`secrets_env_path` joins `env.get("HOME", "")`, so with `HOME` unset it reads
`./.config/ai-kit/secrets.env` relative to the CWD. Inventory itself falls back to
`os.path.expanduser("~")`. Use the same fallback, or skip the file when `HOME` is missing.

---

_Reviewed: 2026-10-15T23:27:03Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: deep_

# Ponytail review

## Ponytail code review: Phase 18 (d164697..HEAD, skills/ tools/ tests/)

What this change does: Phase 18 adds the v2 curated-config pipeline (`plan-set`, `plan-unset`,
`apply` with dry run, backups, an apply marker and restore, and `followups`), cross-AI review-lane
and execution-target selection, a skills inventory and affinity wiring, a pi RPC model parser in
`ai_kit_spec`, and the 2001-line `cross-ai.mjs` runner template with its black-box `--self-test`.

Load assumed: one developer runs the CLI by hand on one project; the runner runs one cross-AI plan
at a time (SPEC R5 edge). Nothing here needs multi-process scale, so these findings are about
correctness of shared logic and lines that must be read, tested and kept in sync.

Out of scope for cuts (locked by SPEC or CONTEXT): the v1 CLI, the self-test inside the template
(R5), the apply marker and recovery text (D-40, R13), the strict encoder (D-16), backups and
reuse (D-19/D-20), the inventory schema validation at file load (trust boundary), and the pi
parser existing in both Python and Node (the template must be stdlib Node).

Severity: should-fix = duplication that must change in lockstep, dead code, or a helper that
already exists. consider = shorter form, lower payoff.

### Should fix

#### PT-01: apply re-implements an existing, tested gsd-tools wrapper (should-fix, about -15 lines)
- Where: `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/apply.py:541-557` (`_new_project`).
- What this is: when the config is absent, apply runs `config-new-project --cwd <dir> --raw`.
- Problem: `ai_kit_spec/gsd_tools.py:358` `ensure_config_exists` builds the same argv. It has
  tests (`tests/test_ai_kit_spec_gsd_tools.py:268`, `tests/test_ai_kit_spec_e2e.py:52`) but no
  production caller. The `gsd_tools.py` module docstring also says its wrappers are the only code
  that shells out to gsd-tools for a config write; `_new_project` breaks that rule.
- Fix: add `env=None, timeout=None` keyword arguments to `ensure_config_exists`, call it from
  `_prepare_writes`, and delete `_new_project`.

#### PT-02: three copies of the same "is this entry a no-op" rule in apply (should-fix, about -35 lines)
- Where: `apply.py:140-171` (`_diff_kind`, `diff_entries`), `apply.py:441-465` (`pending_writes`),
  `apply.py:560-578` (`_count_skipped`), `apply.py:871`.
- What this is: dry run shows add/change/keep/remove; the real apply sends the writes and
  reports how many entries it skipped.
- Problem: each function re-derives "keep, or unset of an absent key, or set to the live value"
  on its own. If one changes, the dry-run diff, the writes and the skipped count disagree. On top
  of that: `pending_writes` takes `host_name` only to `del` it (line 444); it sorts (462-464)
  and its only caller re-sorts the merged list (874); and line 871 re-reads the live config that
  lines 852/865 just read (outside the `try` that guards the same call).
- Fix: build writes as the `diff_entries` rows whose kind is not `keep` (`(row["key"], row["to"])`),
  set `skipped` to the count of `keep` rows, and delete `pending_writes`, `_count_skipped`, the
  dead parameter, the inner sort and line 871. `preflight` already proves `_planned_to` cannot
  raise by this point, so `_count_skipped`'s `ValueError` guard is not needed.

#### PT-03: apply copies inventory's gsd-core table probe (should-fix, about -25 lines)
- Where: `apply.py:24-27` and `inventory.py:16-19` (the same `_PROBE_UNAVAILABLE` text);
  `apply.py:228-234` and `apply.py:276-288` against `inventory.py:120-138` (`_probe_gsd_tables`).
- What this is: both resolve `model-catalog.cjs`/`config-schema.cjs`, build `GsdCorePaths`, call
  `query_gsd_tables`, and format the same three errors.
- Fix: make `inventory._probe_gsd_tables` public (or move it to `gsd_catalog`) and call it from
  `_target_for_core`/`preflight`. Delete the second message constant.

#### PT-04: plan and inventory loading is written twice (should-fix, about -15 lines)
- Where: `cli.py:522-549` (`_load_plan_inputs`) against `apply.py:58-79` (`load_inputs`).
- Problem: both run `load_plan`, `load_inventory`, the digest compare with a word-for-word copy of
  the error text, and `check_plan_inventory`. The digest rule (D-17, D-42) lives in two places.
- Fix: one `plan_io.load_plan_and_inventory(plan_path, inv_path) -> (plan, inv, error)`. The CLI
  keeps its `out_path_problem` check; apply keeps its `--project-dir` check.

#### PT-05: plan-set and plan-unset handlers are near-copies (should-fix, about -35 lines)
- Where: `cli.py:560-570` and `cli.py:600-610` (`_print_plan_set_ok` and `_print_plan_unset_ok` are
  byte-identical); `cli.py:572-597` and `cli.py:710-735` differ only in the edit call.
- Fix: one `_run_plan_edit(args, edit)` that loads, encodes, edits, runs `validate_plan`, writes
  and prints. Each handler becomes one line passing `plan_edit.plan_set`/`plan_unset`.

#### PT-06: dry run re-sequences apply's pre-flight (should-fix, about -15 lines)
- Where: `cli.py:612-640` (`_apply_dry_run_report`) against `apply.py:937-960` (`run_apply`).
- Problem: the needs_choice refusal text, `resolve_target`, `preflight` and `load_template` run in
  the same order in both, with the refusal message copied verbatim. The SPEC says one validator
  path serves dry run and apply (R12); today they can drift.
- Fix: one `apply.prepare(inputs, deps, encode) -> (target, template, error)` used by both
  `run_apply` and the dry run.

#### PT-07: the timeout >= 1800 rule exists five times (should-fix, about -15 lines)
- Where: `plan_edit.py:507-518` (`_check_timeout`, two identical raises), `plan_io.py:523-532`
  (`_validate_runner_timeout`), `plan_io.py:601-605` (inside `_validate_entry_value`),
  `plan_io.py:710-715` (`_validate_outer_timeout`), `cross_ai.py:102-105` (`timeout_value`).
- Problem: five spellings of "an int, not a bool, at least `MIN_TIMEOUT_S`". The trusted-root
  `~/` rule is also written twice (`plan_edit.py:484-490,544-554` and `plan_io.py:619-630`), and
  `cli.py:583` already runs `validate_plan` on every `plan-set` result.
- Fix: one `cross_ai.timeout_ok(value) -> bool` used by every site. Let `plan_edit` rely on
  `validate_plan` for the trusted-root shape. Tests that assert the exact message text need one
  edit.

#### PT-08: one skill-name regex in three modules, and a copy of skills.locate (should-fix, about -12 lines)
- Where: `skill_scan.py:18`, `plan_io.py:415`, `plan_edit.py:12`; `plan_edit.py:471-481`
  (`_skill_installed`) against `skills.py:144-161` (`locate`).
- Problem: `_skill_installed` re-filters rows exactly like `locate` (name, `addressable`, not an
  escaping project copy). The regex check in it adds nothing: `skill_scan` already sets
  `addressable: false` for any name that fails the regex. `apply.skill_value` already uses `locate`.
- Fix: `_skill_installed = skills.locate(name, inv) is not None`. Keep one exported regex in
  `skill_scan` and import it in `plan_io`.

#### PT-09: two different candidate lists for the same runner choice (should-fix, about -15 lines)
- Where: `plan_edit.py:102-118` (`runtime_candidates`, `_price_sort_key`), `plan_edit.py:343-350`
  (`_find_inventory_model`), against `roles.py:239-266` (`choice_candidates`) and
  `cross_ai.py:39-41` (`_runtime_cands`).
- Problem: `recommend` fills `artifacts[0].choices.<runner>.candidates` with
  `roles.choice_candidates` (routers and `-fast` twins excluded, ceiling first). `plan-set
  script:cross-ai.prefer` and `plan-unset script:cross-ai.model.<id>` fill the same field with
  `runtime_candidates` (plain price sort, routers and twins included). Example: the same runner
  can show a `-fast` twin as a top choice after `plan-unset`, but not after `recommend`.
- Fix: call `roles.choice_candidates(cross_ai._runtime_cands(inv, runner_id), "execution", None)`
  and delete `runtime_candidates` and `_price_sort_key`.

#### PT-10: the declared-router filter is written twice (should-fix, about -8 lines)
- Where: `cross_ai.py:46-55` (execute routers inside `_pick_for_runner`) and `cross_ai.py:210-220`
  (`_review_routers`).
- Fix: one `_declared_routers(pool, purpose)` returning the sorted list.

#### PT-11: the umask trick and the atomic file copy are repeated (should-fix, about -15 lines)
- Where: the umask read in `plan_io.py:409-410`, `config_backup.py:42-45` and
  `cross_ai_script.py:205-206`; the "read bytes, read mode, `cache_write_bytes`" sequence in
  `config_backup.py:139-150` (`restore_backup`) and `config_backup.py:153-164` (`snapshot_file`).
- Fix: put one `umask_file_mode()` beside `cache_write_bytes` in `ai_kit_spec/cache.py` and reuse
  it in all three places. `snapshot_file` becomes a call to one `_atomic_copy(src, dst)` that
  `restore_backup` also uses.

#### PT-12: JSON-file loading boilerplate copied three times, plus a fourth reader (should-fix, about -20 lines)
- Where: `plan_io.py:329-342` (`load_affinity`) and `plan_io.py:423-439` (`load_plan`) copy the
  try, open, `json.load`, OSError and ValueError branches of `load_inventory` (`plan_io.py:345-360`).
  `skill_scan.py:34-40` (`_read_json`) duplicates `plan_io.read_json_object`.
- Fix: one `_load_doc(path, label, suffix, validate)` for the three loaders. In `skill_scan`, use
  `plan_io.read_json_object(path)[0] or {}`.

#### PT-13: dead and redundant code in skills.py (should-fix, about -25 lines)
- `skills.py:312-340`: `trusted_roots` returns a `notes` list that is always empty. Its only
  production caller throws it away (`recommend.py:1098`, `_root_notes`). Return the candidates only.
- `skills.py:178-192`: `existing_roots` is a 15-line `isinstance` chain over an inventory that
  `load_inventory` already validated. Use `presets.get_dotted(inv["existing_config"]["values"], ...)`
  and keep only the list filter.
- `skills.py:127-141`: `_escaping_project_only` is called only when `locate` returned None. In
  that case every addressable row is an escaping project copy, so the function equals
  `bool(_addressable_rows(name, inv))`.

#### PT-14: recommend recomputes cross-AI targets up to five times per plan (should-fix, about -15 lines)
- Where: `recommend.py:111`, `728`, `912` and `1205` call `cross_ai.exec_targets`.
  `cross_ai_answers` runs at `recommend.py:909` and again at `1203`.
- Problem: `exec_targets` is pure, so the results match, but each call re-runs scoring, and a
  future change to one call site (for example a different rigor) would silently fork the answer.
- Fix: compute `answers` and `targets` once in `build_plan`, store them on `PlanCtx`, and read them
  everywhere. In `_cross_ai_review_entries` (`recommend.py:798-810`), the "planner vendor unknown"
  and "no lanes" branches build the same off-entry and note; merge them, because
  `_no_lane_reason` already handles `None`.

#### PT-15: dead branches in the runner template (should-fix, about -12 lines)
- Where: `skills/ai-kit-spec-review/references/cross-ai.mjs`.
- `1962-1964`: the second `review && dirty -> contract_violation` check can never run. The same
  check at `1946-1948` already returned, and nothing in between changes its inputs.
- `1921-1925`: `tryNextCli('bad_model', 'clean')` is always true (`bad_model` means fallback and
  the tree is clean), so `return finish('bad_model', ...)` at 1925 is unreachable.
- `1992-1995`: both branches of the `.then` call `exitFlushed`; `exitFlushed(code ?? 0)` is the
  same. `178-187`: `const go = () => process.exit(code); ... go()` is a one-use wrapper.
  `299-303`: `tryNextCli` is one boolean expression.
- Fix: delete them. Change only the shipped template; renders follow on the next `apply`.

#### PT-16: duplicated test helpers although the tests already import from each other (should-fix, about -30 lines)
- Where: `_strict_encode` in `tests/test_curated_config_apply.py:1105`,
  `test_curated_config_apply_e2e.py:102` and `test_curated_config_plan_edit.py:63`; `_scratch_env` in
  `test_curated_config_apply.py:435` and `test_curated_config_followups.py:37`; `_tables_fake` in
  `test_curated_config_apply.py:578` and `test_curated_config_apply_e2e.py:87`; `_config_set_keys`
  in `test_curated_config_apply.py:1236` and `test_curated_config_apply_e2e.py:108`.
- Fix: keep one copy of each and import it. `test_curated_config_apply.py:38-48` already imports
  helpers from the golden, inventory, plan_edit, recommend and skills test modules.

#### PT-17: SPEC R2 note missing in one Rigorous case (should-fix, a correctness side note, about +3 lines)
- Where: `cross_ai.py:293-308` (`select_lanes`).
- Problem: SPEC R2 says Rigorous uses 2 lanes, "otherwise 1 lane plus a note". The note is added
  only when exactly one lane is eligible. Case: two eligible lanes, and every candidate on the
  second lane has the planner's or the first reviewer's vendor. `second_ranked` is empty, the
  plan gets 1 lane, and there is no note. No test asserts the note text (`rg` finds it only in
  `cross_ai.py`).
- Fix: when `second_ranked` is empty, append the same `review_lane` note with a vendor reason, and
  add one fixture test.

### Consider

#### PT-18: five context NamedTuples in apply only to satisfy max-args (consider, about -40 lines)
- Where: `apply.py:338-382` (`CleanupCtx`, `ScriptStepCtx`, `ConfigWriteCtx`, `PrepareCtx`,
  `ExecuteCtx`), plus the unpacking boilerplate at `apply.py:648-651` and `738-741`.
- Problem: the five types hold overlapping subsets of the same seven values (inputs, target,
  deps, template, gsd module, progress, report). Each new step needs a new type. Also,
  `verify_skills` (`apply.py:494-496`) loads `gsd_tools` only for a None check whose result it
  never uses, because `target.tools` was built from that module. The module is loaded four times
  per apply.
- Fix: one `_Run` dataclass created in `run_apply` and passed to every step (one argument, still
  within pylint max-args=5). Delete the dead load in `verify_skills`.

#### PT-19: followups.py rebuilds what NamedTuple already gives (consider, about -35 lines)
- Where: `followups.py:145-153` (`_followup_dict` is `row._asdict()`); `followups.py:433-440`
  (`FollowUp(**raw)`); `followups.py:414-421` (`row._replace(argv=...)`); `followups.py:367-370`
  (`_tail` is `text[-limit:]`, which already handles short text); seven single-use functions that
  return a fixed string (`_disclosures`, `_no_effort_host_note`, `_config_dir_note`,
  `_unknown_version_note`, `_codex_installer_note`, and others at `164-221`), which can be module
  constants or inline f-strings.
- Also: `local_gsd_tools` (which spawns `git rev-parse` via `host.resolve_gsd_core`) runs twice on
  the effort path (`followups.py:266` and `followups.py:301`). Resolve it once and pass it down.

#### PT-20: small leftovers in cross_ai_script.py (consider, about -15 lines)
- `cross_ai_script.py:142-143`: `command_argv` is `shlex.split` and only a test calls it
  (`tests/test_curated_config_script.py:92`). The test can call `shlex.split` directly.
- `cross_ai_script.py:123`: `_stamp` takes `template` and never uses it.
- `cross_ai_script.py:165-180`: the three `_note_new` texts differ only in one phrase; use a dict.
- `cross_ai_script.py:210-214`: `_divert_to_new` has one caller; use `plan._replace(...)`.

#### PT-21: plan_edit.py small duplication (consider, about -20 lines)
- `plan_edit.py:13,18`: `_LIST_KEYS_PREFIXES` and `LIST_KEYS_PREFIXES` name one tuple; keep one.
- `plan_edit.py:287-292`: `_require_script_artifact` repeats `_script_artifact`'s check and
  message. Call `_script_artifact(call.plan)`.
- `plan_edit.py:529-531`: the forced-command warning copies `apply._FORCED_CMD_WARNING`
  (`apply.py:28-31`). Share one constant.
- `plan_edit.py:196-275`: the three script pseudo-key editors repeat the same tail (deepcopy,
  `_script_artifact`, `_finish_script_artifact`, `_sync_artifact_command`, sort entries) and the
  same runner-id parse and `in prefer` check. One `_edit_script(call, mutate)` helper covers them.

#### PT-22: runner template self-test and listing boilerplate (consider, about -45 lines)
- `cross-ai.mjs:922-1024`: each of the five `writeFake*` functions ends with the same
  `writeFileSync` + `chmodSync(0o755)` and repeats the `--model` argv loop and the `FAKE_CALLS`
  log. One `writeExe(binDir, name, body)` plus a shared prelude string removes about 25 lines.
- `cross-ai.mjs:1051-1099`: `runSelfTestCaseSync` and `runSelfTestCaseSpawn` repeat the
  result-check tail (exit, `statusLineOk`, read the calls log, `spec.check`). `cross-ai.mjs:1101-1107`
  builds the same git env three times.
- `cross-ai.mjs:531-555`: `parseListingIds` and the if/else argv chain in `listModels` can become
  one `list: {argv, input, parse}` field per entry in `RUNTIMES` (about -15 lines). This keeps
  each CLI's argv formulas in one place, which the header comment asks users to edit.
- The self-test itself is required by SPEC R5 and D-27; only the repetition is in scope.

### Counts

17 should-fix (PT-01..PT-17, including one SPEC R2 correctness side note), 5 consider (PT-18..PT-22).

Verdict: fix PT-01, PT-02, PT-09 and PT-17 first (a bypassed wrapper, drift-prone apply logic,
two candidate lists that disagree for the same slot, and a missing SPEC note). The rest is lean.

Lean: about -460 lines possible (about -310 should-fix, about -155 consider). No feature, v1 path,
or locked decision is removed.

Not checked: the test bodies beyond helper duplication (about 7k lines); golden fixture content;
whether test assertions pin the exact message text that PT-07 and PT-12 would change. No tests were
run, because the review is read-only.

# Independent skill-judge (SKILL.md)

## Independent skill-judge: ai-kit-gsd-curated-config SKILL.md

- Current: working-tree `skills/ai-kit-gsd-curated-config/SKILL.md`, blob bb81efde (230 lines, no references/ dir)
- Baseline: `d164697:skills/ai-kit-gsd-curated-config/SKILL.md` (194 lines, v1 only)
- Scored blind: 18-SKILL-JUDGE.md was read only after both scores were final.

### Command/flag verification (offline, scratch HOME, `--help` only)

All 17 subcommands named in SKILL.md exist in the argparse (`inventory recommend plan-set plan-unset apply followups` +
the 11 v1 ones). Every flag used in the examples exists: `inventory --host {claude,codex,opencode,cursor,pi} --refresh`;
`recommend --inventory --profile --rigor {mvp,standard,rigorous} --cross-ai-review {y,n} --cross-ai-exec {y,n} --out`;
`plan-set key value --plan [--inventory] [--force]`; `plan-unset key --plan [--inventory]`;
`apply --plan --inventory --project-dir [--dry-run]`; `followups --plan --inventory --project-dir [--approve] [--require]`.
v1 flags all match. The runner flag `--print-argv` and the `AIKIT-XAI status=...` line exist in
`skills/ai-kit-spec-review/references/cross-ai.mjs` (the template; `status=unverified` with `tree=unknown` also exists). Marker and
snapshot suffixes (`.ai-kit-apply-marker`, `.ai-kit-apply-backup`), `approve_with`, `restore_error`, `script.active`,
`GSD_PATH_JEV*` and `GSD_WORKSTREAM` all exist in code. No command in the skill is missing from the CLI.

Problems found during verification, not visible from `--help` alone:
1. `inventory` writes JSON to **stdout** only (it has no `--out`). The skill never says to redirect it to the file that later
   `--inventory <inv.json>` flags read. `plan-set`/`plan-unset` default `--inventory` to `inventory.json` next to `plan.json`
   (`plan_io.sibling_inventory_path`). The skill does not say that either.
2. `recommend --out` is refused inside the project's `.planning/` and over any input/config file (`plan_io.out_path_problem`).
   `.planning/plan.json` is the obvious place an agent would try, and the skill does not warn against it.
3. `plan-set workflow.cross_ai_command "node .planning/scripts/cross-ai.mjs" --force` uses `--force` for nothing: that value is
   the canonical one and passes without it (`plan_edit._check_cross_ai_command`). `--force` exists to bypass candidate checks and
   the full-permissions-command guard. The skill never explains this, and its only example teaches agents to add the flag by habit.
4. v2 exits `2` on refusals the agent can fix (bad `--out`, inventory-digest mismatch, `needs_choice` left open on apply,
   malformed inventory). The skill says exit 2 means an install problem and "do not retry". That is true for v1 only.
5. v1 `apply-execution` writes a direct `opencode run ...`/`cursor-agent ...` value into `workflow.cross_ai_command`
   (`cli._cmd_apply_execution`). Run after a v2 apply, it silently replaces the v2 `node .planning/scripts/cross-ai.mjs` runner wiring.
   The skill only says "never mix v1 writes with an in-progress v2 plan ... without intent".
6. `inventory` already reports `ponytail_visibility` live (`inventory.py:373`). The SKILL.md bullet "on this machine the six
   ponytail names are visible only through the Claude plugin cache" is a dated fact about the maintainer's machine, written as if it were general.

### Scores

#### Baseline (d164697) — 104/120 (B)

| Dim | Score | Justification |
|---|---|---|
| D1 Knowledge delta | 16/20 | Strong expert gotchas: `config-set` silently creates a sparse one-key config without `ensure-project`; pass detect output through unchanged; `apply-execution` no-candidate asymmetry; bare binary on PATH vs a venv path; absolute `--dir` breaks after a re-clone; `gsd-executor` excluded from the heavy-tier sweep. Some repeated prose (the ensure-project footgun is explained twice). |
| D2 Mindset + procedures | 13/15 | Has an explicit "before any apply-*, ask yourself" check plus a correctly ordered detect, then ask, then apply procedure. |
| D3 Anti-patterns | 13/15 | NEVER list with non-obvious reasons; a common-mistakes table with a Why column. |
| D4 Spec/description | 13/15 | Valid frontmatter. WHAT is very specific, WHEN is present. The description is long (~800 chars) and full of implementation detail (`AGENT_DEFAULT_TIERS`), and it has few phrases a user would actually type. |
| D5 Progressive disclosure | 12/15 | Self-contained, under 200 lines. Points to source files for the literal lists. Some redundancy. |
| D6 Freedom calibration | 14/15 | Low freedom where config writes are fragile; exact order; the one question is fixed. |
| D7 Pattern | 9/10 | Clean Process pattern with a Tool-style reference table. |
| D8 Usability | 14/15 | Required-flags table, exit codes, null/no-candidate edge cases. |

#### Current (bb81efde) — 88/120 (C)

| Dim | Score | Justification |
|---|---|---|
| D1 Knowledge delta | 15/20 | Much new expert content: trusted-checkout model, marker/`restore_error` semantics, "exit 0 with cleanup warnings = committed, never restore", `.new` runner not active, partial opencode bare profile, unverified plugin layering. Lost every v1 gotcha. Several lines are too compressed to act on ("System One reachability", "only `GSD_WORKSTREAM` is honored ...", "the next apply's refusal must agree after its `apply --dry-run` check"). Includes the machine-specific ponytail note. |
| D2 Mindset + procedures | 10/15 | The 6-step v2 procedure is domain-specific and correctly ordered. It never says which questions to ask the user to fill `--profile`/`--rigor`/`--cross-ai-review`/`--cross-ai-exec`, and gives no rule for choosing them. The baseline's "before apply, ask yourself" check is gone. |
| D3 Anti-patterns | 11/15 | Specific NEVER list and a mistakes table, but most reasons are terse and the Why column was dropped. Two traps are missing: `--force` used by habit, and v1 `apply-execution` overwriting the v2 runner command. |
| D4 Spec/description | 12/15 | Valid. WHAT and WHEN are both present and shorter than the baseline. It lacks trigger phrasing for the new v2 capabilities (wiring skills to GSD agents, setting up a cross-AI runner, "configure .planning/config.json"). The WHEN clause is unchanged from v1. |
| D5 Progressive disclosure | 11/15 | Sectioned and 230 lines, fine without references/. v1 is now a bare command dump. The phrase "v1 — same as prior skill" points to text that no longer exists in the installed file. |
| D6 Freedom calibration | 11/15 | Low freedom where it matters (`approve_with` unchanged, grouped yes/no, never hand-write). But the examples use literal values that agents will copy: `--profile quality --rigor mvp --cross-ai-review n --cross-ai-exec y`, `--force`, `--model x`, `--require installer`. Nothing marks them as placeholders, and they directly drive config writes. |
| D7 Pattern | 8/10 | Process pattern. Putting v1 and v2 side by side blurs it a little. |
| D8 Usability | 10/15 | Good failure-state coverage. Gaps: inventory output is never captured to a file; `--out` refusal under `.planning/` is not mentioned; exit-2 semantics are wrong for v2; code blocks use the bare `ai-kit-gsd-curated-config.py` instead of `"$ENTRYPOINT"`; the v1 edge cases (null `claude_md_path`, detect takes no `--project-dir`, apply-execution optional flags) are gone. |

### Findings (current file)

#### Critical
None.

#### Important
- **I1: The skill never says which questions to ask before `recommend`, or how to choose the values.** Fix: in step 2, add
  "Ask the user, in one message: `model_profile` (quality/balanced/budget/adaptive; adaptive recommended), rigor
  (mvp/standard/rigorous), cross-AI plan review (y/n), cross-AI execution (y/n). Omit `--cross-ai-*` to take the inventory-derived
  default. Ask nothing else." Then replace the example literals with `<profile> <rigor> <y|n>` placeholders.
- **I2: Exit-code semantics are wrong for v2.** Fix: "v1: exit 2 = install problem (surface verbatim, do not retry). v2: exit 2 is also
  a refusal you can fix (bad `--out`, inventory digest mismatch, open `needs_choice`, malformed inventory). Read the stderr line and fix
  the input, re-running `inventory`/`recommend` where it says so. Exit 1 = a gsd-tools read/write or restore failure."
- **I3: Inventory and plan file locations are undefined.** Fix: in step 1, `python3 "$ENTRYPOINT" inventory --project-dir <target> > "$WORK/inventory.json"`,
  where `$WORK` is a scratch dir outside `<target>/.planning/`. In step 2, add "`--out` must be an existing directory outside the project's
  `.planning/`; keeping `inventory.json` beside `plan.json` lets `plan-set`/`plan-unset` omit `--inventory`."
- **I4: The `--force` example teaches agents to add the flag by habit.** Fix: delete `--force` from the `workflow.cross_ai_command` example (or the whole line;
  apply already sets that value). Add a NEVER: "Never pass `--force` to `plan-set` unless the user explicitly chose a value outside the
  listed candidates. It bypasses the candidate check and the full-permissions command guard."
- **I5: v1 `apply-execution` silently replaces v2 runner wiring.** Fix: replace "never mix v1 writes ... without intent" with "Never run v1
  `apply-execution`/`apply-review` on a project configured by v2 `apply`. `apply-execution` overwrites `workflow.cross_ai_command` with a
  direct CLI command, so `.planning/scripts/cross-ai.mjs` stops being used."
- **I6: A machine-specific fact is written as general guidance (ponytail bullet).** Fix: replace it with "Inventory reports
  `ponytail_visibility` per host. Report what it says; do not assume plugin-cache-only visibility."
- **I7: The v1 path regressed compared with the baseline.** "Same as prior skill" points to nothing, and the baseline's v1 safeguards were dropped. Fix: restore
  three one-line rules under the v1 path: run `ensure-project` first (otherwise `config-set` silently writes a sparse config); pass the `detect-*` `{cli, model}`
  output through unchanged (`apply-execution` flags are optional, `apply-review` flags are required); skip `apply-claude-md-path` when the detected path
  is `null`. Replace `--model x` with `--model <detected model>`.

#### Minor
- M1: The code blocks use `python3 ai-kit-gsd-curated-config.py`, while the prose says `python3 "$ENTRYPOINT"`. Use `"$ENTRYPOINT"` in the blocks too.
- M2: Rewrite the "Live timeout" bullet: "The runner's live outer timeout comes from `workflow.cross_ai_timeout` in `.planning/config.json`, or
  `.planning/workstreams/$GSD_WORKSTREAM/config.json` when `GSD_WORKSTREAM` is set. The baked timeout caps it from below."
- M3: Simplify the cleanup-warnings sentence ("the next apply's refusal must agree after its `apply --dry-run` check") to "If a marker remains,
  run `apply --dry-run`; it prints the recorded recovery steps; follow them."
- M4: Define "System One" in a few words (the jev backend the inventory TCP-probes), or drop the term.
- M5: Document the `script:cross-ai.model.<runner>` / `script:cross-ai.prefer` plan-set keys. They are the only way to pick runner models, and
  agents meet them in `needs_choice` without context.
- M6: Description: add v2 trigger phrases ("configure .planning/config.json", "wire skills to GSD agents", "set up a cross-AI execution runner").
- M7: Restore a short Why column in the Common mistakes table. The baseline's reasons were its strongest anti-pattern content.

### Verdict: FAIL

- Current 88/120 (C), baseline 104/120 (B). That is a 16-point regression, below the 96 bar, with 7 Important findings open.
- The CLI surface is accurate. The failures are in guidance: missing question protocol, wrong exit semantics, undefined file locations,
  examples agents will copy, and the v1 regression.
- Fixing I1-I7 should bring it back to at least about 100 without restructuring.

### Comparison with the executor self-check (18-SKILL-JUDGE.md)

- The self-check judged the same blob (bb81efde). It scored baseline 100 and current 103 (PASS, one Minor finding, now fixed).
- This review: baseline 104, current 88 (FAIL).
- The baselines roughly agree (100 vs 104). The current scores diverge by 15. The biggest gaps are D2 (13 vs 10), D6 (13 vs 11) and D8 (13 vs 10).
- The self-check gave credit for the new v2 content. It did not test the instructions against the CLI's actual behavior:
  - inventory is stdout-only;
  - `--out` is refused under `.planning/`;
  - `--force` is unnecessary in its example;
  - v2 exit 2 can be fixed and retried;
  - v1 `apply-execution` clobbers the runner.
- It also did not register that the v1 safeguards were dropped. That loss is why this review finds a regression where the self-check found +3.
- Its only finding (internal decision IDs) was cosmetic.
