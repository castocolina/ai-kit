---
phase: 25-quota-aware-cross-ai-subprocess-supervision
reviewed: 2026-10-25T05:08:46Z
depth: standard
files_reviewed: 33
files_reviewed_list:
  - Makefile
  - .pre-commit-config.yaml
  - README.md
  - skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cross_ai_script.py
  - skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/plan_edit.py
  - skills/ai-kit-gsd-curated-config/references/runner.md
  - skills/ai-kit-gsd-curated-config/SKILL.md
  - skills/ai-kit-spec-execute-gsd/ai_kit_spec_gsd/adapter.py
  - skills/ai-kit-spec-execute-gsd/ai_kit_spec_gsd/cli.py
  - skills/ai-kit-spec-execute-gsd/ai_kit_spec_gsd/gsd_config.py
  - skills/ai-kit-spec-execute-gsd/ai_kit_spec_gsd/gsd_cross_ai.py
  - skills/ai-kit-spec-execute-gsd/references/dispatch-notes.md
  - skills/ai-kit-spec-execute-gsd/SKILL.md
  - skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers/dispatch_injection.py
  - skills/ai-kit-spec-execute-superpowers/references/design-notes.md
  - skills/ai-kit-spec-execute-superpowers/references/escalation.md
  - skills/ai-kit-spec-execute-superpowers/references/state-management.md
  - skills/ai-kit-spec-execute-superpowers/SKILL.md
  - skills/ai-kit-spec-review/ai_kit_spec/error_classifier.py
  - skills/ai-kit-spec-review/ai_kit_spec/runner_dispatch.py
  - skills/ai-kit-spec-review/references/cross-ai-dispatch.md
  - skills/ai-kit-spec-review/references/cross-ai.mjs
  - skills/ai-kit-spec-review/references/subprocess-quota-policy.md
  - skills/ai-kit-spec-review/SKILL.md
  - tests/test_ai_kit_spec_gsd.py
  - tests/test_ai_kit_spec.py
  - tests/test_ai_kit_spec_runner_dispatch.py
  - tests/test_ai_kit_spec_runtimes_table.py
  - tests/test_ai_kit_spec_superpowers.py
  - tests/test_cross_ai_runner_e2e.py
  - tests/test_curated_config_plan_edit.py
  - tests/test_curated_config_script.py
  - tests/test_quota_policy_text.py
findings:
  critical: 2
  warning: 6
  info: 7
  total: 15
status: issues_found
---

# Phase 25: Code Review Report

**Reviewed:** 2026-10-25T05:08:46Z
**Depth:** standard
**Files Reviewed:** 33
**Status:** issues_found

## Summary

Scope: the 33 listed files. The given `diff_base` (19ca10a) is 1385 commits back, so the review
looked at the Phase 25 range (`a063759^..HEAD`, 60 `(25-NN)` commits). Most attention went to the
runtime code that changed: `cross-ai.mjs` (runCli, ladderNext, attemptCapMs, cycle state, live
detection, main), `runner_dispatch.py`, `cli.py` `--min`, `gsd_cross_ai.py`, `plan_edit.py` and
`cross_ai_script.py`. The SKILL/reference docs were checked only for claims the code contradicts.
`node cross-ai.mjs --self-test` passes (`self-test ok`).

Five findings were reproduced in hermetic runs: CR-01 and WR-04 with a fake `pi` on a scratch
PATH/HOME, WR-01 with an unwritable `XDG_STATE_HOME`, WR-06 with `--classify-only`, and CR-02 with
a Python call against a scratch project. No real CLI ran. How often real CLIs print the stderr
text behind CR-01 and WR-06 was not checked.

Main concerns: a live stderr match overrides a run that actually succeeded (CR-01), and a pristine
runner from a newer template is silently downgraded (CR-02). The rest of the ladder holds up, but
it has edge-case gaps: a timed-out attempt can never reach a rung under the shipped CONFIG, there
is a budget cliff, a state write can crash the run, and the bare-code rows misclassify stack
traces.

## Narrative Findings (AI reviewer)

## Critical Issues

### CR-01: A live terminal stderr match discards a successful run (exit 0, answer, edits)

**File:** `skills/ai-kit-spec-review/references/cross-ai.mjs:2268-2276, 2518-2521, 2566-2575`
**Issue:** `armLimit` records `state.liveHit` on the first stderr line that matches any
`terminal: true` row (`permission denied`, `unauthori[sz]ed`, `not logged in`, `usage limit`,
`\bbilling\b`, `invalid model`, ...). In `runCli`, `if (r.liveHit)` takes priority over everything
else, and the success check (`!failed && p.text.trim()`, line 2541) exists only in the
`else` branch. A child that prints such a line and then exits 0 with a valid answer inside the
1.5 s grace is therefore classified as a failure. `runChild` does compute `limited` (whether the
limit timer actually killed the child), but nothing reads it.
Reproduced: a fake `pi` writes `tool bash: cat /root/x: Permission denied` to stderr, edits
`a.txt`, prints `# Summary\nok` and exits 0. Result:
`AIKIT-XAI status=permission_blocked ... exit=69 cli_rc=0 ... tree=dirty`, runner stdout empty.
GSD loses the SUMMARY, the plan reads as failed while its edits and commits are in the tree, and
an owner re-run redoes the work. On a confirmed router lane, a `usage limit`/`billing` notice
turns the same success into exit 75 and a cycle. Unverified: how often real pi/codex/opencode/cursor
print such lines on stderr during a healthy run.
**Fix:** let a live hit win only when it actually ended the child:
```js
const p = rt.parse(r.stdout, ctx);
const succeeded = !r.timedOut && r.code === 0 && !p.error && p.text.trim();
if (r.liveHit && !r.limited && succeeded) r.liveHit = null; // the child finished on its own
```
(or check success before the `r.liveHit` branch), plus a self-test case "terminal stderr line,
then exit 0 with an answer -> ok".

### CR-02: A pristine runner from a newer template is silently downgraded

**File:** `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cross_ai_script.py:256-262`
**Issue:** The new pristine branch re-renders with the installed template and returns `"change"`
whenever `older or data != existing`. A pristine runner stamped `template=8`, written by a newer
ai-kit (another checkout or worktree, which this owner routinely runs ahead of the installed
copy), differs from the template-7 render, so `ensure-runner` overwrites it with the older body.
Before this change it was `keep-pristine`. Reproduced: a pristine v8 render planned against the
shipped template gives `plan.kind == "change"`, and the new file has version 7. `runner.md`
("a pristine current-template runner takes a same-version body fix ... otherwise kept byte for
byte") does not describe this downgrade, and no test covers it.
**Fix:**
```python
try:
    existing_v, template_v = template_version(existing), template_version(template)
except ValueError:
    existing_v, template_v = -1, template_version(template)
if state == "pristine":
    if existing_v > template_v:
        return ScriptPlan("keep-pristine", path, None, existing, state, "", existing)
    data = render(template, _upgrade_config(template, existing, scrub_env))
    ...
```
Add a test: a pristine runner from a newer template is kept.

## Warnings

### WR-01: A cycle-state write failure crashes a router-quota stop

**File:** `skills/ai-kit-spec-review/references/cross-ai.mjs:1868-1880, 2450-2457, 2589`
**Issue:** `writeCycleState` (`mkdirSync`, `openSync(tmp, 'wx')`, `renameSync`) has no error
handling, and `saveCycle` runs on every router-lane quota failure. A read-only or wrong
`XDG_STATE_HOME`/`~/.local/state`, or a leftover `.<file>.<pid>.tmp` from a killed run with a
reused pid (`'wx'` -> EEXIST), throws out of `runCli`. Reproduced with `XDG_STATE_HOME` pointing at
a file: `AIKIT-XAI status=crash exit=1 ... attempts=0`, and the quota class, rule and evidence are
lost. With a writable dir, the same run ends `status=quota exit=75 retry_after_s=600`.
**Fix:** wrap the write. On failure, log `cross-ai: cycle state unwritable: <path>` and stop with
the quota status but no `retry_after_s` (a bare 75, since no cycle can be tracked). Use a unique
tmp name (`${pid}.${randomUUID()}`) instead of only the pid.

### WR-02: `attemptCapMs` has a budget cliff just above 60 s

**File:** `skills/ai-kit-spec-review/references/cross-ai.mjs:2323-2334`
**Issue:** `budget = remaining - 60000 > 0 ? remaining - 60000 : remaining`. With 60 s left an
attempt gets 60 s, but with 61 s left it gets 1 s. `ladderNext` admits a rung once
`now + wait + 60 s <= deadline`, so an admitted rung usually starts with 60-120 s left and gets
only 0-60 s of child time. In exec mode that means a resumed session killed after a few seconds,
which can leave partial edits behind, and the rung is wasted.
**Fix:** reserve only when enough is left for both parts, and never return less than the
admission guarantee:
```js
const budget = remaining >= 120000 ? remaining - 60000 : remaining;
```
Or move the reserve entirely into `ladderNext` admission.

### WR-03: Under the shipped CONFIG a timed-out attempt can never reach a rung

**File:** `skills/ai-kit-spec-review/references/cross-ai.mjs:1796, 2325, 2591`;
`skills/ai-kit-spec-review/references/subprocess-quota-policy.md` ("Classes": "a timeout with no
quota match" is `transient`)
**Issue:** With `attemptTimeoutS: 0` (the shipped default) the child timer ends at
`deadline - 60 s`. Admission then needs `now + backoff + 60 s <= deadline`. `now` is already past
`deadline - 60 s` by the finalize time, and `backoffS[0]` is 30 s (0 in self-test copies, still
`> 0` ms late). So every plain timeout stops with `why=deadline`, which is `status=timeout`/124
through `ladderStop`. The "timeout -> transient rung" path in the policy, and the "keeps 60 s in
hand for the next rung" comment, only hold when the owner sets `attemptTimeoutS`. The self-tests
exercise timeout rungs only with `attemptTimeoutS: 8/10` (lines 4760, 4773).
**Fix:** either reserve `60 s + max(backoffS)` plus finalize slack in `attemptCapMs`, or state in
the policy and in `runner.md` that a timeout is rung-eligible only with `attemptTimeoutS > 0`.
Add a self-test under the default CONFIG that pins whichever is chosen.

### WR-04: Class stops report `first_failure=- last_failure=-`

**File:** `skills/ai-kit-spec-review/references/cross-ai.mjs:2549-2558, 2566-2575`
**Issue:** Both immediate class-stop returns increment `attempts` and log the attempt, but never
set `firstFailureMs`/`lastFailureMs` (only the ladder path at 2580-2581 does). The mandatory
`cross-ai: report` line, which the skills relay verbatim, then says no failure happened. Seen in
the CR-01 reproduction: `report status=permission_blocked ... attempts=1 ... first_failure=-
last_failure=-`.
**Fix:** before each class-stop return:
```js
lastFailureMs = Date.now();
if (!firstFailureMs) firstFailureMs = startedMs;
```

### WR-05: `--min` plus `clear-workflow-keys` deletes a user's own lower timeout; the SKILL claims it never does

**File:** `skills/ai-kit-spec-execute-gsd/ai_kit_spec_gsd/cli.py:763-773`;
`skills/ai-kit-spec-execute-gsd/SKILL.md:295-299` vs `:337`
**Issue:** A user-set `workflow.cross_ai_timeout` below 1800 (or a non-int such as `1800.0`) is
overwritten with 1800 and recorded as adapter-owned. The next mode-transition cleanup then sets it
to `None` (`apply_changes` with value `None`), so the user's value is gone and GSD falls back to
its 300 s default, not the user's number. Lines 295-299 admit this ("a lower one is raised and
owned, so a later cleanup removes it (the per-run backup holds the original)"). Line 337 still
says the cleanup "Never touches a value the user set by hand", which this flow contradicts.
**Fix:** record the prior value from `config-set`'s `previousValue` in the ownership sidecar and
have `clear-workflow-keys` restore it instead of unsetting. At minimum, reword line 337 to exempt
the raised `cross_ai_timeout`.

### WR-06: The bare-code and `billing` rows misclassify crash stack traces and paths

**File:** `skills/ai-kit-spec-review/references/cross-ai.mjs:1156-1173` (rows `code-401-403`,
`code-5xx`, `text-billing`)
**Issue:** Post-hoc classification scans up to 64 KiB of stderr with unanchored `\b401\b`,
`\b50[0234]\b` and `\bbilling\b`. Verified with `--classify-only`:
- `at run (/app/dist/cli.js:401:17)` -> `auth` (exit 69, cycle state deleted)
- `at f (/app/index.js:500:3)` -> `transient` (up to 6 retry rungs of a real crash)
- on a router lane, `ENOENT ... 'src/billing/x.ts'` -> `quota`, so 600 s cooldown cycles for up
  to 4 h on a project that has a `billing` module

The Python classifier already guards against this by scanning only the stderr tail
(`_STDERR_TAIL_CHARS`, "a task ABOUT rate limiting must not read as a quota event").
**Fix:** anchor the code rows to HTTP context, e.g.
`(?:status|code|http|error)[^\n]{0,12}\b401\b`, and `billing` to error wording (e.g.
`billing (?:error|issue|required|limit)|check your billing`). Scan only the tail, as Python does.
Add `--classify-only` fixtures for stack-trace line numbers and path segments.

## Info

### IN-01: Dead state and parameters in live detection

**File:** `skills/ai-kit-spec-review/references/cross-ai.mjs:1943, 1958, 1974, 2257`
**Issue:** `runChild` returns `limited`, but nothing reads it (CR-01 needs it).
`watchChunk(cli, source, relay, state, chunk)` uses only `relay` and `chunk`.
**Fix:** use `limited` (CR-01). Drop the unused parameters.

### IN-02: `waitMs` compares a duration with an epoch timestamp

**File:** `skills/ai-kit-spec-review/references/cross-ai.mjs:2596`
**Issue:** `Math.min(wait, quotaEnd() || wait)` always yields `wait`, because `quotaEnd()` is an
absolute ms timestamp. The apparent intent was `quotaEnd() - Date.now()`, which line 2643 does
compute.
**Fix:** `waitMs: quotaEnd() ? Math.min(wait, Math.max(0, quotaEnd() - Date.now())) : wait`.

### IN-03: Unreachable and redundant code

**File:** `cross-ai.mjs:2375` (`stoppedWhy`: `step.next === 'cooldown'` is returned earlier at
2600), `cross-ai.mjs:2446` (`STATE_DELETE.has(s) || (s !== 'quota' && !QUOTA_KEEP.has(s))`
equals `!QUOTA_KEEP.has(s)`), `cross-ai.mjs:2416` (stray blank line inside the returned object),
`runner_dispatch.py:230-238` (`argv = [...]; return argv` adds nothing)
**Fix:** simplify or delete.

### IN-04: "Refused without spawning a child" is not quite true

**File:** `skills/ai-kit-spec-review/references/subprocess-quota-policy.md` ("A re-entry before
the state file's due time is refused without spawning a child");
`skills/ai-kit-spec-execute-gsd/SKILL.md:26-28` ("refused by the runner without starting the CLI")
**Issue:** `main` runs `treeState` (git children) and `listModels` (the CLI binary itself:
`pi --mode rpc`, `opencode models`, `agent models`, `codex debug models`) before
`runCli` checks `due_at` (`cross-ai.mjs:6111-6135` vs `2418`). The model call is skipped, but the
CLI is started.
**Fix:** check the due time before preflight, or reword to "without a model call".

### IN-05: Every answer line is also copied to stderr

**File:** `skills/ai-kit-spec-review/references/cross-ai.mjs:1111-1114, 2281`
**Issue:** `outRelay` is a `makeLineRelay`, whose `emit` calls `log()` for every stdout line, so
the whole answer (redacted) also lands in GSD's stderr log. This was visible in the CR-01
reproduction. Likely unintended, since only the stdout hook is needed for live events.
**Fix:** give the stdout relay a non-logging `emit`, or a `quiet` option.

### IN-06: A unit test reads the developer's real catalog cache

**File:** `tests/test_ai_kit_spec_runner_dispatch.py:634-645` (`test_wedged_runner_recorded_group_killed`)
**Issue:** `RunnerSeams` keeps the default `route_fn=resolve_route` and `env_fn=os.environ`, so
`run_runner` reads `~/.cache/ai-kit/spec/model-catalog.json` and the argv depends on it. The file
is not asserted on today, but this goes against the AGENTS.md rule on real user files in tests.
`test_ai_kit_spec_env_scrub.py` already pins `route_fn=lambda *_a: None` for exactly this reason.
**Fix:** pass `route_fn=lambda *_a: None` there, and in the other default-seam `run_runner` calls.

### IN-07: The wake-line text pin is easy to evade

**File:** `tests/test_quota_policy_text.py:38-50`
**Issue:** A line passes whenever it contains both `one-shot` and `retry_after_s`, even if it also
says `hourly`. Fixed intervals such as "every 10 minutes" are never flagged.
**Fix:** exempt only lines without `WAKE_RE` hits after the exemption tokens are removed, and add
`every \d+ ?(?:s|sec|min|minutes?)` to `WAKE_RE`, with a non-vacuity case.

---

_Reviewed: 2026-10-25T05:08:46Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_

## Fix status (2026-10-25, orchestrator)

- **Fixed in code, with tests:**
  - in 8c3dbfa: CR-01, WR-01, WR-02, WR-04, WR-06, IN-02 and IN-06, with five new runner
    self-test cases;
  - in 5b28f21: CR-02.
- **Fixed in docs** (8c3dbfa): WR-03 and IN-04.
  - WR-03: the policy and runner.md now say a timeout reaches a rung only with
    `attemptTimeoutS` set.
  - IN-04: "without a model call".
- **WR-05, partly fixed:** the SKILL now names the exception. Restoring the user's lower value
  on cleanup would need a prior-value record in the ownership sidecar; until then the per-run
  config backup holds it.
- **Open, low impact:**
  - IN-01: unused `watchChunk` parameters.
  - IN-03: redundant code.
  - IN-05: stdout lines are relayed to stderr.
  - IN-07: the wake-line pin can be evaded.

Gates after the fixes: the runner self-test (template and dogfood copy), ruff, pyright, vulture,
`make test` and `make validate` all pass.

## Ponytail review (2026-10-25, read-only subagent, `a063759^..HEAD`)

- **Fixed in the ponytail commit:**
  1. **High:** `routerBacked` applied to every model on its CLI, so a direct model got router
     cycles. `routeOf` now honors it only for the CLI's pinned `models[cli]`. The self-test case
     `billing-unpinned-model-on-router-cli` is red on the old rule.
  2. IN-05: the stdout relay no longer copies answer lines into stderr.
  3. The duplicated class-stop block is now one closure.
- **Deferred, worth doing:**
  - 4. superpowers: a `quota_cycle` class from `classify_dispatch_failure`, instead of three
    shell JSON parses in the SKILL.
  - 5. `plan_io.py`: replace the re-implemented gsd-core skill-resolution rules with gsd-core's
    `buildAgentSkillsBlock` (about -100 lines).
  - The second "confirmed router" rule (Python `fallback_quota` against curated-config's
    `is_router`/`router_confirmed`/execute) should become one rule.
- **Deferred cleanup** (about -65 lines):
  - 6: dead `runCli` state;
  - 7: live-detection plumbing;
  - 8: clamp helpers;
  - 9: trivia.
- **Backlog:**
  - 10: move the runner's embedded self-test harness (about 3,300 lines) to a sibling file;
  - IN-07: skip.
