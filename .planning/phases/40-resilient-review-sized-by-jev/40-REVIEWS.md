---
phase: 40
cycle: 1
reviewers: [referee-one]
reviewed_at: 2026-11-25T03:39:46-03:00
plans_reviewed: [40-01-PLAN.md, 40-02-PLAN.md, 40-03-PLAN.md, 40-04-PLAN.md, 40-05-PLAN.md, 40-06-PLAN.md, 40-07-PLAN.md, 40-08-PLAN.md, 40-09-PLAN.md, 40-10-PLAN.md, 40-11-PLAN.md, 40-12-PLAN.md, 40-13-PLAN.md]
models:
  referee-one: "router-env/my-referee-one"
model_sources:
  referee-one: "pinned"
---

# Cross-AI Plan Review — Phase 40

<!-- gsd:plan-revision-conflicts:begin -->
## Plan-Revision Conflicts
<!-- gsd:plan-revision-conflicts:end -->

> Note: one reviewer lane only (referee-one, `.planning/config.json` `review.default_reviewers`); its findings are single-reviewer.

## Cycle 1 (referee-one)

### Review conditions (cycle 1)

Reviewer referee-one (`router-env/my-referee-one`, opencode, through `query review-lane invoke --as referee-one`), probed
01:02 (READY in 14 s). Four batches in parallel (A = 40-01..03, B = 40-04..07, C = 40-08..09, D = 40-10..13), prompts 193-214 KB
built by the phase-40 copy of the phase-39 review drivers (verify-against-source, ponytail lens, executor reality for pi
router-env/my-coding, same-wave overlap check, the local shell rules verbatim, the orchestrator planning rules and locked
decisions inlined). All four lanes exited 0 (470-693 s) and every review was read in full; findings are path:line grounded.
The plan checker (sonnet) ran in parallel on the same plans: 0 blockers, 4 warnings, 1 info (folded into the fix pass).

Fix pass (one targeted pass, time rule): the orchestrator's decisions D1-D14 (`tmp/p40-review/c1/fix-brief.md`) were applied
by five opus fix planners to all 13 plans; each plan ends with a `## Review dispositions (cycle 1)` section (rejections carry
path:line evidence: the five-file budget for fixtures and generated listings, the ai-kit-cross-ai section 4 pointer, the root
README row, distinct eval vendors, the duplicate pure-function switch cases, dropping the REASONS non-vacuity case). The plan
checker re-checked the revised plans: 0 blockers, 0 warnings (40-05 checked separately after its own fix). Contract change
accepted by the orchestrator: before round 1 every chosen non-native lane is probed (the 120-second cache reuse applies only to
probes this review ran itself). The decision-coverage gate passes (10 of 10 CONTEXT decisions cited). Review cycle 2 was NOT
run (time box): the fixes themselves are unreviewed by referee-one. The review drivers are ready
(`tmp/p40-review/prep_cycle.py 2 ...`, `run_all.sh 2`, `assemble.py 2`); the inlined planner rules carry a CORRECTIONS section
pointing to the fix brief.

Open concerns after the fix pass (with severity):
- **HIGH — resume supersede (plan 40-03, owner of `dispatch-reviewer --lane-log`) — FIXED 2026-11-25 in commit 73421b3
  (40-03 Task 2 red-then-green test, `_record_dispatch_success`):** a lane logged `failed` by its first
  dispatch (for example an exit-75 pending lane) that succeeds on its one-shot resume logs nothing, so `record_merge` keeps it
  `failed` and drops its report (the D4 precedence rule). Fix before wave 3: a successful `dispatch-reviewer --lane-log`
  appends a `chosen` event that supersedes the earlier `failed` of the same round, with a test of failed-then-resumed.
- **MEDIUM — fixture assumptions the planners did not verify at HEAD:** that `cfg_resolve` keeps `usage_limited` and `pool`
  on a custom-command lane (40-03, 40-05 fixtures); `route_all` for custom lanes under the fake `which_fn` (40-05);
  `resolve-reviewers` under 40-07's fakes; the synthetic runtime cache shape of 40-13's layout check.
- **LOW — lane size:** 40-02 Task 1 stages seven files and 40-06 Task 1 six (two of them generated listings); split at run
  time if a lane exceeds its cap (the plans say how).

### referee-one

#### Batch A (40-01, 40-02, 40-03)

#### 40-01

**Summary.** The plan makes the right compatibility split for REV-07: a merge with a round log keeps surviving reports and can return `Approved (partial)`; a merge without a log keeps the existing fail-closed contract. The main gap is that the new merge still trusts a readable report more than the dispatch outcome, so it can turn a recorded failure into a clean approval.

**Strengths**

- Extends the existing reason vocabulary and updates its exact-set test in the same task. The runtime-table test checks that mapped values are *members* of `REASONS`, not that there are nine keys; the quota-policy test checks for prohibited wake wording, not tuple size. The proposed extension does not require changing either assertion. `tests/test_ai_kit_spec.py:3483–3490`; `tests/test_ai_kit_spec_runtimes_table.py:774–780`; `tests/test_quota_policy_text.py:150–153`.
- Preserves the existing renderer and its protection against turning unparsed findings into an approval. The status parser already recognizes `Approved (partial)` as an approval, so no second parser is needed. `skills/ai-kit-spec-review/ai_kit_spec/review_reports.py:22–42,104–145`; `.planning/phases/40-resilient-review-sized-by-jev/40-01-PLAN.md:125–126`.

**Concerns**

- **HIGH — A failed lane can become `judged` just by leaving a readable report.** Task 1 puts any non-`Failure` status file in `reports`, then appends `judged` for all those keys. A `failed` or `replaced` log entry can therefore be overwritten by a stale or unsuccessful attempt’s `Approved` output. Conversely, a same-round remerge can rely on an old `judged` event for a key omitted from the new merge. Real dispatch writes stdout and returns its exit code separately; the pending-lane path deliberately keeps its report file. The planned tests only pair recorded failures with missing or invalid files. `.planning/phases/40-resilient-review-sized-by-jev/40-01-PLAN.md:120–126,204–211`; `skills/ai-kit-spec-review/ai_kit_spec/cli.py:1384–1388`; `skills/ai-kit-spec-review/references/cross-ai-dispatch.md:301–314`.
- **MEDIUM — The ordering backstop verifies argument order, not the owner’s roster order.** Task 1 builds `roster` from `key=path` arguments. Those can be reordered by sizing, and an in-place replacement can put a later roster key first. Task 2 then uses that mutated order as the expected result. This does not verify the locked rule that known keys follow the configured order and only unknown keys follow log order. `.planning/phases/40-resilient-review-sized-by-jev/40-01-PLAN.md:31,122–126,168–171`; `.planning/phases/40-resilient-review-sized-by-jev/40-07-PLAN.md:125–127`; `skills/ai-kit-spec-review/ai_kit_spec/role_orders.py:85–89`.
- **MEDIUM — The log reader accepts objects downstream code cannot use.** A valid JSON object with `round` and `key` but no `state` passes `round_states` and raises `KeyError` in `review_outcome`. An unknown nonempty `reason` is printed as-is, despite the R3 default requirement. The malformed-line test covers invalid JSON and arrays, not incomplete lane objects. `.planning/phases/40-resilient-review-sized-by-jev/40-01-PLAN.md:119–124,161–164`; `skills/ai-kit-spec-review/ai_kit_spec/error_classifier.py:16–26,128–135`.
- **LOW — Two task checks need to be made executable as written.** Task 2 specifies six parameters for `ev`, above the locked five-argument design cap, although repo pylint excludes tests; simplify it rather than claiming pylint will catch it. Task 3 compares against `HEAD_TASK1` without giving the isolated executor a command to resolve and count that baseline. The existing module/class anchors and fixture are otherwise usable. `.planning/phases/40-resilient-review-sized-by-jev/40-01-PLAN.md:160,194,220`; `pyproject.toml:75–80`; `.pre-commit-config.yaml:26–32`; `tests/test_ai_kit_spec.py:3552–3560,3643–3662`.

**Suggestions**

- Make the current attempt’s successful completion, not just a parseable file, the condition for recording `judged`. Specify how a confirmed successful resume supersedes the prior attempt. Add cases for a failed lane leaving a readable `Approved`, a stale report for a replaced lane, and a successful same-round resume.
- Pass or persist the original review order for the logged merge. Test with report arguments reversed and a replacement occupying the first slot. Validate lane events and positive round numbers before using them; an unusable log must not silently make a review look clean.
- Give the executor an exact baseline lookup for Task 3. Give the orchestrator an explicit route to amend Task 1 if the later tests expose a production bug, rather than leaving a committed tracer that cannot pass the plan.

**Risk assessment: HIGH.** The legacy path is well isolated, but the new path can make an incorrect approval claim. Fix the state/report precedence before downstream plans depend on it.

##### Ponytail findings

- **HIGH — Task 1:** Required for D-01/D-03. Keep the append-only log and reuse `merge_findings` / `render_merged_report`; neither needs a replacement framework. Fix the evidence check at the logged merge boundary shared by the normal loop and resume. `skills/ai-kit-spec-review/ai_kit_spec/review_reports.py:72–145`; `skills/ai-kit-spec-review/references/cross-ai-dispatch.md:355–376`.
- **MEDIUM — Task 2:** A focused log test module is justified. Reuse the existing test-group generator; spend a test on a malformed lane object or genuinely concurrent appends before adding more tests that only echo hand-built reason values. `.planning/phases/40-resilient-review-sized-by-jev/40-01-PLAN.md:160–175`; `tools/gen_test_groups.py:72–100`; `tests/test_gate_scope.py:570–583`.
- **LOW — Task 3:** Keep the no-log assertions and reuse `_REPORT_A` for survivor coverage. Prefer the real reason-table mutation planned in 40-09 to maintaining another handwritten 13-key set solely to show that adding or removing a key changes a set. `tests/test_ai_kit_spec.py:3483–3490,3552–3560`; `.planning/phases/40-resilient-review-sized-by-jev/40-01-PLAN.md:201–210`; `.planning/phases/40-resilient-review-sized-by-jev/40-09-PLAN.md:136`.

#### 40-02

**Summary.** The plan puts the ping behind a usable CLI and shares fallback policy with the next plan. It is not executable as written: the first commit trips an existing lane-reader guard, and the proposed worker loop does not enforce the deadline it promises. The cache and error paths also need tests that exercise more than the successful two-lane case.

**Strengths**

- Builds on `selectable_lanes`, `role_order`, `lane_fallback`, and the existing routing skip vocabulary. This is the right place to keep owner-order selection shared rather than writing two fallback policies. `skills/ai-kit-spec-review/ai_kit_spec/lane_settings.py:116–154`; `skills/ai-kit-spec-review/ai_kit_spec/role_orders.py:85–89`; `skills/ai-kit-spec-review/ai_kit_spec/routing.py:36–41`.
- A trailing `ProbeSeams.timeout_s` preserves the existing positional constructor and defaults while reaching both the runner and custom launcher. The planned two-second fake-probe case gives the concurrency claim a measurable check. `skills/ai-kit-spec-review/ai_kit_spec/quota.py:208–214,250–256`; `skills/ai-kit-spec-review/ai_kit_spec/cli.py:188–190`; `.planning/phases/40-resilient-review-sized-by-jev/40-02-PLAN.md:172–177`.

**Concerns**

- **HIGH — The first commit is blocked by an existing test.** `next_lane` must call `lane_fallback`, but `TestNoFlagSetter.test_no_module_calls_a_lane_reader` scans every package module and rejects that reference. Neither the task’s staged allowlist nor its focused verification includes `tests/test_lane_settings.py`. The commit touches generated listings, which trigger the full unit and arch groups, so deferring this to 40-03 cannot work. `.planning/phases/40-resilient-review-sized-by-jev/40-02-PLAN.md:124,141–146`; `tests/test_lane_settings.py:232–260,453–477`; `tools/run_unittest_parallel.py:226–232`.
- **HIGH — The deadline is a wait limit, not a probe limit.** `_probe_all` waits for `timeout + 5`, then uses `future.done()`, which can accept a result that finished after the wait expired. Running threads are not cancelled by `shutdown(wait=False)`, and the process still waits for executor threads at exit. The real runner has a separate outer margin and kill grace; fallback candidates bypass `_probe_all` entirely. The proposed test releases its blocked worker in cleanup and sets grace to zero, so it does not prove that the CLI exits on time or that a result completing at the deadline is rejected. `.planning/phases/40-resilient-review-sized-by-jev/40-02-PLAN.md:132–133,172–177`; `skills/ai-kit-spec-review/ai_kit_spec/runner_dispatch.py:42–45,275–282,645–670`.
- **HIGH — A single probe exception aborts the round; some failures are not logged.** An expected I/O error can escape the existing probe, which only catches `ValueError`; the plan does not handle exceptions from `future.result()` or the direct fallback probe. It also puts a rejected fallback candidate in the cache/exclusion set without a `failed` event, and `entry_reason` accepts an arbitrary non-null reason. These are gaps in the one-lane isolation and closed-reason claims. `.planning/phases/40-resilient-review-sized-by-jev/40-02-PLAN.md:132–134,218`; `skills/ai-kit-spec-review/ai_kit_spec/quota.py:196–205,259–287`.
- **HIGH — Empty input can exit 0.** With `reviewers.json` equal to `[]`, the stop description built from failed entries is empty; `if outcome.stop` is false, so the command returns success on zero lanes. The planned all-blocked test starts with a nonempty list and misses it. `.planning/phases/40-resilient-review-sized-by-jev/40-02-PLAN.md:131–139`; `.planning/phases/40-resilient-review-sized-by-jev/40-SPEC.md:84–90,249–250`.
- **MEDIUM — Recent cache success can mask a failure or refer to the wrong lane.** `_skip_status` falls through to the 120-second hit even when the previous round recorded `failed`. The cadence test has no fresh success entry for that failed key. Also, the shared quota file is user-global and keyed by lane key, while project configuration can override a user lane under the same key. A recent success can certify a different invocation unless reuse checks identity. This also affects the PROVISIONAL handoff: 40-05’s expiry fixture supplies an empty cache. `.planning/phases/40-resilient-review-sized-by-jev/40-02-PLAN.md:132,211–213`; `.planning/phases/40-resilient-review-sized-by-jev/40-05-PLAN.md:100–104`; `skills/ai-kit-spec-review/ai_kit_spec/quota.py:31–32,290–306`; `skills/ai-kit-spec-review/ai_kit_spec/config_io.py:694–709`.
- **MEDIUM — “Read-only routing” still performs discovery and can migrate configuration.** `persist=False` prevents writing the runtime snapshot, not running discovery. The unconditional `review_routes` call happens even for native-only or judge-file inputs, and `cfg_resolve` defaults to migration. The installed-layout handoff runs a native-only ping in a scratch home and asserts no host stub was called; a cold runtime snapshot can call the stubs for inventory or version checks before any lane ping. `.planning/phases/40-resilient-review-sized-by-jev/40-02-PLAN.md:127,134`; `.planning/phases/40-resilient-review-sized-by-jev/40-13-PLAN.md:89–96`; `skills/ai-kit-spec-review/ai_kit_spec/routing.py:265–280,353–369`; `skills/ai-kit-spec-review/ai_kit_spec/detection.py:1293–1321`; `skills/ai-kit-spec-review/ai_kit_spec/config_io.py:671–691`.
- **MEDIUM — Task 1 is oversized and leaves implementation choices to the lane.** It touches six files, introduces two modules, and asks the executor to split a multi-stage function under pylint caps without naming the split or the exception policy. `_probe_all` also refers to `now` without defining or passing it. Task 2 accepts nonpositive `--timeout` even though the real runner rejects it; its zero-match `rg -c` check produces no count and exits 1. Task 3’s out-of-order fake gives both results the same reason, so swapping those results would still pass. `.planning/phases/40-resilient-review-sized-by-jev/40-02-PLAN.md:109,123–141,173,187,215`; `pyproject.toml:75–80`; `skills/ai-kit-spec-review/references/cross-ai.mjs:6724–6727`.

**Suggestions**

- Put a narrowly scoped update to the lane-reader guard in the **first** commit that needs it. Pin allowed reader names by module and keep the planted-violation test. Update the file manifest and run `tests.test_lane_settings` in that task.
- Use one bounded probe path for originals and candidates. Specify monotonic deadline handling, process cleanup, and the named exceptions that become lane failures. Test exact-deadline behavior, one raising probe plus a healthy sibling, rejected-candidate logging, and `[]` returning exit 3.
- Bypass cached success after a recorded failure; verify that reused entries refer to the same lane invocation. Delay route discovery until fallback selection actually needs it, and use non-migrating config resolution for an already-started review.
- Split setup/selection from orchestration with exact helper signatures and stage lists. Make the ordering fixture produce distinct results that cannot be swapped undetected.

**Risk assessment: HIGH.** The unmodified guard blocks the first commit, and fixing only the guard would still leave timeout, failure isolation, and zero-lane behavior unproven.

##### Ponytail findings

- **MEDIUM — Task 1:** D-02 needs the scheduler and shared selection, not a second atomic file writer. Keep `write_rows` as the shared entry point if callers need it, but delegate to the existing cache atomic-write primitives with an explicit private mode. Lazy routing also avoids unnecessary host discovery. `.planning/phases/40-resilient-review-sized-by-jev/40-02-PLAN.md:123–134`; `skills/ai-kit-spec-review/ai_kit_spec/cache.py:23–46,83–85`.
- **HIGH — Task 2:** The timeout seam is needed; a second, weaker timeout for fallback candidates is not. Reuse the supervised runner and custom launcher for child lifetime and have the ping code classify outcomes consistently. `skills/ai-kit-spec-review/ai_kit_spec/runner_dispatch.py:566–592,645–719`; `.planning/phases/40-resilient-review-sized-by-jev/40-02-PLAN.md:132–133,172–177`.
- **MEDIUM — Task 3:** Cadence, dedup and the judge-file edge are required. Keep the existing fake/temporary-config pattern, but add a **CLI** judge-file case and combine failures with fresh cache data in the cadence case. Pure calls alone do not cover the routing and cache setup that 40-12 invokes. `.planning/phases/40-resilient-review-sized-by-jev/40-02-PLAN.md:210–218`; `.planning/phases/40-resilient-review-sized-by-jev/40-12-PLAN.md:112`; `tests/test_role_orders.py:22–43,273–288`.

#### 40-03

**Summary.** The switch predicate matches D-04: quota on an owner-flagged lane can switch, while other reasons cannot. The tracer proves that a manually invoked switch rewrites a row, but it bypasses the production exit-code branch and never dispatches the replacement. The shared row update also needs an explicit one-writer rule.

**Strengths**

- Uses the existing boolean reader on the config lane and reuses ordered fallback selection, rather than guessing from an exit code or stderr. The runner maps permission, auth, billing and transient outcomes separately, so the negative cases target real classifications. `skills/ai-kit-spec-review/ai_kit_spec/lane_settings.py:96–107,133–154`; `skills/ai-kit-spec-review/ai_kit_spec/error_classifier.py:30–60`; `.planning/phases/40-resilient-review-sized-by-jev/40-03-PLAN.md:109–110,149–155`.
- Keeps the existing refusal exit and provides a plan to record it as `configuration` without allowing a switch. The separate JSON-result and `--stdout-only` contracts can remain intact. `skills/ai-kit-spec-review/ai_kit_spec/cli.py:1373–1388`; `.planning/phases/40-resilient-review-sized-by-jev/40-03-PLAN.md:113,159`.

**Concerns**

- **HIGH — The tracer does not exercise the trigger or dispatch the replacement.** Task 1 asserts exit **0** in JSON-result mode, calls `switch-lane` unconditionally, then manufactures the fallback report. Production uses `--stdout-only`, and 40-09 switches only after a nonzero exit, before hard-tier handling. Neither the tracer nor the unflagged tests proves that sequence. `.planning/phases/40-resilient-review-sized-by-jev/40-03-PLAN.md:114,157–159`; `.planning/phases/40-resilient-review-sized-by-jev/40-09-PLAN.md:167–171`; `skills/ai-kit-spec-review/ai_kit_spec/cli.py:1384–1388`; `skills/ai-kit-spec-review/SKILL.md:377–385`.
- **HIGH — Atomic replacement does not serialize two switches.** Two flagged lanes can fail in one round. Two `switch-lane` calls can read the same rows and log, choose the same fallback, and both report success. The last whole-file write wins, but both replacement events survive. Dispatching by index can then run or attribute the wrong row. The plan neither locks the read/select/write/log operation nor requires the orchestrator to run switches one at a time and re-read the rows. `.planning/phases/40-resilient-review-sized-by-jev/40-03-PLAN.md:111,191–194`; `.planning/phases/40-resilient-review-sized-by-jev/40-09-PLAN.md:168`; `skills/ai-kit-spec-review/ai_kit_spec/cli.py:1340–1346,1359–1369`.
- **HIGH — The same lane-reader guard blocks this commit too.** Even after allowing the specific 40-02 `lane_fallback` reference, adding `lane_usage_limit` needs a second permitted use in the same commit. Task 2 explicitly runs the rejecting module but does not let the executor edit it. Extend the permitted-use table again in 40-04 for its provisional reader and runner call. `.planning/phases/40-resilient-review-sized-by-jev/40-03-PLAN.md:99,110,134,163–167`; `.planning/phases/40-resilient-review-sized-by-jev/40-04-PLAN.md:103,138`; `tests/test_lane_settings.py:250–260,453–477`.
- **MEDIUM — Run identity and failure validation are incomplete.** The CLI accepts `--round 0` or a negative round even though those are not lane-event rounds. The switch re-reads config by key without checking that the flag still applies to the runtime/model/command that actually failed. A config edit can change the pair or flag behind the same key; existing configuration code treats flags as pair-bound. Task 2’s reason-membership test also depends on unspecified events “after the dispatch cases above,” but each test has a fresh setup. `.planning/phases/40-resilient-review-sized-by-jev/40-03-PLAN.md:110–114,157–163`; `skills/ai-kit-spec-review/ai_kit_spec/lane_settings.py:11–14`; `skills/ai-kit-spec-review/ai_kit_spec/quota.py:42–52`.
- **LOW — Flag the provisional pool behavior without flagging the owner’s settled quota rule.** The same-pool backstop and pool fixture in 40-03 are presented without the required `PROVISIONAL` label. The core flag-and-quota switch is settled; the free-pool comparison and blocked-until behavior carry the provisional label. `.planning/phases/40-resilient-review-sized-by-jev/40-03-PLAN.md:19–22,114,149–153`; `.planning/phases/40-resilient-review-sized-by-jev/40-SPEC.md:171–178`.

**Suggestions**

- Have the tracer use `--stdout-only` with a fake quota exit 75, run the switch at the production branch point, dispatch the new index with a successful fake that records the actual key, and merge that output. Add an unflagged exit-69 case that keeps the sibling’s report.
- Keep the simplest one-writer contract: require the orchestrator to serialize switches, reload the rows after each change, and bind dispatch to the resulting key/index. Test two failed slots competing for one fallback. If the CLI must support concurrent switch writers, serialize the entire operation, not just the rename.
- Specify paired flags, positive round and index semantics, and how a changed lane identity is refused. Make the reason-membership test seed and collect its own events. State the lint-sized helper split in Task 1 rather than asking the executor to infer it.

**Risk assessment: HIGH.** The core predicate is sound on paper, but the current tracer misses the shipping path, and two simultaneous failures can make the slot and the audit log disagree.

##### Ponytail findings

- **HIGH — Task 1:** Needed for REV-01/REV-07. Reuse the existing `--stdout-only` exit contract and Task 1 of 40-02’s row writer; do not add another dispatch or selection mechanism. The missing caller work is at 40-09’s switch-first branch and in the existing resume reference, whose saved argv and failure instructions are not updated by the sizing-only reference edit. `.planning/phases/40-resilient-review-sized-by-jev/40-09-PLAN.md:168,208`; `skills/ai-kit-spec-review/references/cross-ai-dispatch.md:315–336,355–376`.
- **MEDIUM — Task 2:** Keep policy-edge tests that the existing fallback tests cannot cover: the dispatch refusal, failed log event, no switch, and surviving report. Reuse existing index/error patterns and avoid duplicating pure fallback cases unless the new wrapper changes their result. The refusal fixture should use the real `prompt_over_window` reason, not `window_exceeded`. `tests/test_lane_settings.py:320–362`; `tests/test_ai_kit_spec.py:5805–5831`; `skills/ai-kit-spec-review/ai_kit_spec/prompt_guard.py:22–32`; `.planning/phases/40-resilient-review-sized-by-jev/40-03-PLAN.md:149–162`.

#### Cross-plan checks

- **Waves and dependencies:** Waves 1, 2 and 3 each have one plan. No same-wave file overlap exists. The 40-01 → 40-02 → 40-03 → 40-04 dependency chain supplies the log, selection and switch helpers in order; the later consumers are transitively downstream. The lane-reader guard is a **missing file change**, not a scheduling conflict. Add it to the serial plans that first introduce each permitted reference. `.planning/phases/40-resilient-review-sized-by-jev/40-01-PLAN.md:5–6`; `.planning/phases/40-resilient-review-sized-by-jev/40-02-PLAN.md:5–6`; `.planning/phases/40-resilient-review-sized-by-jev/40-03-PLAN.md:5–6`; `.planning/phases/40-resilient-review-sized-by-jev/40-04-PLAN.md:5–6`.
- **Requirement and prohibition coverage:** R1–R4 are assigned across this batch and the 40-04/05/09/10/12 handoffs. R5 is assigned to 40-06/09/10; R6 to 40-07/09; R7 to 40-08/09/10; R8 to 40-11/12/13. All five prohibition statements have a plan home, but the **R2 exact-deadline** and **R4 owner-order** backstops are not actually demonstrated, as noted above. Two handoff gaps remain: 40-12 reuses the same quota cache across judge rounds, so a second round begun within 120 seconds can log a cached `ok` rather than run its required probe; and 40-09 only routes `Escalation Required`, `No Edits`, or cap stops to classification, missing an `Edits Applied` summary that also lists a skipped finding. The current fixer explicitly permits that combination. `.planning/phases/40-resilient-review-sized-by-jev/40-SPEC.md:182–253`; `.planning/phases/40-resilient-review-sized-by-jev/40-12-PLAN.md:112`; `.planning/phases/40-resilient-review-sized-by-jev/40-09-PLAN.md:203`; `skills/ai-kit-spec-review-fixer/SKILL.md:82–91`.
- **Gate checks:** The unittest runner accepts the proposed module arguments and emits the reported `=== <module>: FAILED (rc=…)` signal. The main verification commands and generated-listings tool exist. However, `make check-dogfood` is **not** a W031 check: dogfood’s check list does not include it, and GSD health emits W031 separately as a warning. With `STATE.md` at 294 lines, give the orchestrator an explicit line-count check after each summary/state update, and explicitly assign the plan summary and its commit to the orchestrator rather than the task-only executor. `tools/run_unittest_parallel.py:884–913,935–945`; `tools/check_dogfood.py:622–648`; `.claude/gsd-core/bin/lib/health-diagnostic-rules/state-consistency.cjs:391–406`; `.planning/STATE.md:286–294`; `.claude/gsd-core/workflows/execute-plan.md:12–18`.

**Verdict: revise all three plans before dispatch.** Fix the first-green-commit blocker, then pin the report/dispatch evidence and ping deadline contracts before wiring the skill loop.

Read-only review: no files changed, and no tests, Make targets, or live reviewer lanes were run. Findings are based on source and plan inspection, not runtime verification.

#### Batch B (40-04, 40-05, 40-06, 40-07)

#### 40-04

**Summary.** The reader belongs on top of the existing runner interface, and adding a trailing `RunnerSpec.pool` field is a small, compatible way to pass the flag. The plan is not yet execution-ready: the shared probe constructor also serves execute-role probes, and the reader’s fail-open behavior is narrower than claimed.

**Strengths**
- The status reader reuses the runner’s validated output rather than parsing its state file in Python. The existing command emits one status line, and `bounded_run` puts the real child in a process group with timeout cleanup. `skills/ai-kit-spec-review/references/cross-ai.mjs:4072–4081,4140–4143,7000`; `skills/ai-kit-spec-review/ai_kit_spec/detection.py:955–982`.
- The field and flag placement preserve existing callers when the field is unset. The plan puts `--pool` after `--mcp-config` in the **settings flags**, without disturbing the timeout suffix in the actual argv. `.planning/phases/40-resilient-review-sized-by-jev/40-04-PLAN.md:138–142`; `skills/ai-kit-spec-review/ai_kit_spec/runner_dispatch.py:238–243,275–282`.

**Concerns**
1. **HIGH — Task 2 changes execute-role quota probes despite the review-only promise.** `probe-quota --role execute` selects execute entries but refreshes them through the same `_probe_call`, which constructs a `review_spec` for any runtime-backed lane. After this change, an execute-only flagged lane can pass `--pool` on its availability probe and write or clear the pool record. The proposed negative test only checks `spec_with_effort(..., "exec", ...)`; 40-05 uses a custom command for its execute case, bypassing the affected constructor. `.planning/phases/40-resilient-review-sized-by-jev/40-04-PLAN.md:134–143`; `.planning/phases/40-resilient-review-sized-by-jev/40-05-PLAN.md:136–140`; `skills/ai-kit-spec-review/ai_kit_spec/cli.py:903–931`; `skills/ai-kit-spec-review/ai_kit_spec/quota.py:250–256,290–306`; `skills/ai-kit-spec-review/references/cross-ai.mjs:7313–7314`.
2. **MEDIUM — Task 1 can throw instead of treating malformed output as no record.** The child uses `text=True`; undecodable output can raise `UnicodeDecodeError` during the subprocess call, before the regex or date parser. The prescribed spawn catch does not cover it. The existing runner-description reader catches `ValueError`, which includes decoding errors. `.planning/phases/40-resilient-review-sized-by-jev/40-04-PLAN.md:104`; `skills/ai-kit-spec-review/ai_kit_spec/detection.py:955–971`; `skills/ai-kit-spec-review/ai_kit_spec/runner_facts.py:30–44`.
3. **MEDIUM — The executor checks are not fully self-contained or hermetic.** Task 1 defines the recorder inside `_read` but then refers to `run_fn` from the test without saying how it is exposed. Task 2’s byte-equality assertion compares default `None` with explicit `None`, not against the old argv. Its verify list also runs existing real-Node cases in **both** named modules, contrary to the task’s blanket fake-only claim. `.planning/phases/40-resilient-review-sized-by-jev/40-04-PLAN.md:70,107,142,147`; `tests/test_runner_flags.py:44–55,117–137`; `tests/test_runner_describe.py:247–266,305–329`.

**Suggestions**
- Specify how the originating role reaches the probe constructor, and pin `--pool` on actual fake runner argv for review while asserting its absence for an execute-role **runtime** probe. State which other `review_spec` consumers are intended to inherit the flag, including the effort probe (`skills/ai-kit-spec-review/ai_kit_spec/effort_probe.py:58–86`).
- Catch decoding errors at the status-read boundary, give `_read` an exact return shape including recorded calls, and use the existing argv golden pattern. Select fake-only test cases for the task gate, or explicitly distinguish existing real-Node contract checks from the new unit tests.
- Mark the D-04 pool-flag must-have itself **PROVISIONAL**, not only the surrounding objective and code comment. `.planning/phases/40-resilient-review-sized-by-jev/40-04-PLAN.md:18–21,138`.

**Risk Assessment: HIGH.** As written, a review-only feature can change execute-side state, and the new reader can abort selection on input it promises to ignore.

##### Ponytail findings
- **MEDIUM — Task 1:** Needed for D-05. Keep the thin wrapper and existing `RunnerSeams`/bounded child pattern (`runner_dispatch.py:294–328`); no second record reader is needed. Finish the decode and timeout cases through that seam.
- **HIGH — Task 2:** Needed for D-04. Reuse `lane_usage_limit` and the argv builder, but test the shared probe caller, not just the two constructors (`lane_settings.py:96–107`; `quota.py:250–256`).
- **MEDIUM — Task 3:** The equality boundary and cache tests are needed. Keep the cache policy small; prove expiry through 40-05’s real call chain rather than treating a helper-only deletion test as evidence of one retry (`quota.py:290–307`).

#### 40-05

**Summary.** This covers both intended entry points and correctly puts the pool record ahead of a fresh cached success. The plan leaves the crucial integration step underspecified, and its exact fake causes both CLI tracers to fail before they reach the pool status reader.

**Strengths**
- The Step 0.7 insertion point is correct: a fresh synthetic `quota` entry prevents `refresh_quota_cache` from probing, and `resolve-reviewers` consumes the same cache. The review-only check is explicit at this call site. `.planning/phases/40-resilient-review-sized-by-jev/40-05-PLAN.md:124–140`; `skills/ai-kit-spec-review/ai_kit_spec/cli.py:922–934,962–973`; `skills/ai-kit-spec-review/ai_kit_spec/quota.py:290–307`.
- Reusing `next_lane` preserves the existing owner-order and different-pool fallback rule. The plan does not introduce another selector. `.planning/phases/40-resilient-review-sized-by-jev/40-05-PLAN.md:100–102`; `.planning/phases/40-resilient-review-sized-by-jev/40-02-PLAN.md:123–127`; `skills/ai-kit-spec-review/ai_kit_spec/lane_settings.py:139–154`.

**Concerns**
1. **HIGH — Both CLI tracers fail before reaching `--blocked-status`.** Their injected `which_fn` advertises Node, but `fake_run` returns `None` for `--describe`. Routing refreshes the runner fact before either command reaches the block check; the fact reader accesses `proc.returncode` and does not catch `AttributeError`. `.planning/phases/40-resilient-review-sized-by-jev/40-05-PLAN.md:104,136`; `skills/ai-kit-spec-review/ai_kit_spec/routing.py:265–279,353–357`; `skills/ai-kit-spec-review/ai_kit_spec/runner_facts.py:30–44,54–60`.
2. **HIGH — The block check is not wired to the existing result shape or timeout.** In 40-02, `_skip_status` returns `ok`, `fresh`, or `None`; unavailable results and their reasons come from probe entries. “The row is blocked with reason `quota`” leaves the executor to invent how that value reaches replacement and logging. Putting the status subprocess in `_skip_status` also puts it **before** the worker pool: two slow status reads can serialize and add up to 60 seconds before either model probe starts, regardless of `--timeout`. `.planning/phases/40-resilient-review-sized-by-jev/40-05-PLAN.md:100`; `.planning/phases/40-resilient-review-sized-by-jev/40-02-PLAN.md:128–134,172–177`; `skills/ai-kit-spec-review/ai_kit_spec/runner_dispatch.py:51`.
3. **HIGH — Two lanes in one expired pool can both be retried.** The pre-pass reads all records and drops cached failures before the sequential refresh starts. If that pool has two ordered lanes, a quota failure from the first can renew the record, but the second still probes from the pre-pass snapshot. The ping test only injects `False` for “passed,” and the Step 0.7 test uses `blocked_until=-`, not an expired record that gets renewed. The claimed “try once, then honor renewal” is not established even within one invocation. `.planning/phases/40-resilient-review-sized-by-jev/40-04-PLAN.md:173`; `.planning/phases/40-resilient-review-sized-by-jev/40-05-PLAN.md:103,137–140`; `skills/ai-kit-spec-review/ai_kit_spec/quota.py:298–306`; `skills/ai-kit-spec-review/references/cross-ai.mjs:4053–4059,4118–4125`.
4. **MEDIUM — Task 1’s test recipe names the wrong helper and assumes thread order.** `_ping` is a CLI helper; the pure `run()` helper hardwires `CONFIG`. The task does not say how to inject the modified roster, or give complete CLI argv/setup. The test also requires `["lane-a", "lane-b"]` in an order the worker pool does not promise. `.planning/phases/40-resilient-review-sized-by-jev/40-05-PLAN.md:95–104`; `.planning/phases/40-resilient-review-sized-by-jev/40-02-PLAN.md:132–137,174–176`.

**Suggestions**
- Give both fakes exact responses for `--describe` and `--blocked-status`; fail on unexpected calls. Specify the `PingRun` construction and assert one call per key without asserting worker order.
- Specify the existing unavailable-entry shape for a pool block and how it enters the replacement path. Put the status read and model probe under one per-lane time budget, without serializing unrelated pools. Add the blocked-path case to the concurrency test.
- Add a fake-clock case with two lanes in an expired pool and a fake runner that renews the record on the first retry. Verify the second lane is not probed. Keep the writer in the runner. Add `REV-07` and the D-02 handoff to this plan’s traceability: Task 1 changes the ping path, not just REV-01 selection. `.planning/phases/40-resilient-review-sized-by-jev/40-05-PLAN.md:14–21,99–104`.

**Risk Assessment: HIGH.** The verification fails as prescribed, and a literal implementation can violate both the ping deadline and the once-after-expiry rule.

##### Ponytail findings
- **HIGH — Task 1:** Needed for D-05 and D-02. Reuse the worker and the existing quota-entry contract (`quota.py:217–223`). Don’t create a second ping-result protocol just for pool blocks.
- **HIGH — Task 2:** Needed for Step 0.7. Reuse the existing refresh path (`quota.py:290–307`), but keep the decision close enough to the next probe to observe a renewal. One stateful fake is more valuable than additional isolated cache-entry assertions.

#### 40-06

**Summary.** The adapter uses the right shared client and confidence threshold. Its tests prove routing for hand-built items, not for the merged report and fixer summary the loop will actually hand it. The resulting gaps affect both severe-finding preservation and what leaves the process.

**Strengths**
- `find_jev` and `ask_items(strict=True)` already handle absence, invalid choices, failed calls and `needs_fallback`. Importing `STABLE_TOP` avoids a second threshold. `.planning/phases/40-resilient-review-sized-by-jev/40-06-PLAN.md:110–117`; `skills/ai-kit-spec-review/ai_kit_spec/jev_names.py:121–174`; `skills/ai-kit-spec-review/ai_kit_spec/lane_order.py:14`.
- The payload-recording fake is an appropriate way to verify the actual client input without using a backend. Excluding the report’s `Location`, `Required`, and `Why` fields by construction is useful. `.planning/phases/40-resilient-review-sized-by-jev/40-06-PLAN.md:114–121,164`; `tests/test_catalog_jev_names.py:132–146`.

**Concerns**
1. **HIGH — Cap-open findings disappear on the normal merged-report path.** Task 1 feeds `EFFECTIVE_REPORT_PATH` to `parse_findings`. The parser requires `Why: ….` at end of line; the renderer appends ` (Reviewers: …)` after the period. Every such bullet is missed, including the deterministic HIGH fold finding. The test uses an unmerged report, so it passes without exercising the 40-09 handoff. `.planning/phases/40-resilient-review-sized-by-jev/40-06-PLAN.md:113,121,163`; `.planning/phases/40-resilient-review-sized-by-jev/40-09-PLAN.md:171,203`; `skills/ai-kit-spec-review/ai_kit_spec/review_reports.py:11–13,57–69,138–141`.
2. **HIGH — The fixer can accidentally downgrade a finding before the hard rule sees it.** The plan trusts severity from the fixer summary, then uses title alone to omit matching report findings. A summary that calls a HIGH finding MEDIUM can route it to `skipped`; two distinct findings with the same title can also collapse. In addition, the action’s final `reviewer_wrong` branch is not explicitly limited to MEDIUM/LOW, despite the stated contract; the report parser can emit `CROSS-DOC` or no severity. `.planning/phases/40-resilient-review-sized-by-jev/40-06-PLAN.md:112–116,159–163`; `skills/ai-kit-spec-review/ai_kit_spec/review_reports.py:44–69,72–93`; `skills/ai-kit-spec-review-fixer/SKILL.md:42–49`.
3. **HIGH — The payload test does not enforce “summaries only.”** Titles and reasons still come from free-form model output. Length limits, single-backtick removal and known secret patterns do not exclude a copied config value, unmarked code, or a literal path inside those fields. The proposed test puts sensitive material in fields already omitted and uses only a known token shape in the transmitted title. Its straddle case also needs an explicit separator: several secret patterns require a non-word character before the token. `.planning/phases/40-resilient-review-sized-by-jev/40-06-PLAN.md:114–115,164,193`; `skills/ai-kit-spec-review/ai_kit_spec/secret_shapes.py:48–102`; `.planning/phases/40-resilient-review-sized-by-jev/40-SPEC.md:249–253`.
4. **MEDIUM — The caller can miss a genuine skip or use the wrong project’s jev settings.** The 40-09 handoff invokes classification on `No Edits`, `Escalation Required`, or cap; the fixer can emit `Edits Applied` with a skipped MEDIUM finding and no escalation. Also, neither the command nor its handoff sets the reviewed worktree as jev’s child cwd. Jev reads its project layer from `os.getcwd()`, and the existing classification command already uses `functools.partial(run, cwd=cwd)` to avoid this mismatch. `.planning/phases/40-resilient-review-sized-by-jev/40-06-PLAN.md:117–119`; `.planning/phases/40-resilient-review-sized-by-jev/40-09-PLAN.md:134,203`; `skills/ai-kit-spec-review-fixer/SKILL.md:79–91`; `skills/jev-fast-decision/scripts/jev_review.py:78–85`; `skills/ai-kit-spec-review/ai_kit_spec/skill_classify.py:121–128`.

**Suggestions**
- Add a CLI test that runs the actual merge and then classifies its output at the cap. Reuse the shared report parser, with an explicitly supported reviewer suffix. Take severity from a uniquely matched report finding; ambiguous, unknown, or unparseable items stay on the owner path. Test a summary/report severity mismatch and duplicate titles.
- Define a conservative rule for sending a summary. When a title or reason cannot safely be reduced to a value-free summary, keep that item local. Test prohibited material **inside the transmitted fields**. Pass the reviewed root through both the command and the docs handoff; cover a skip on `Edits Applied`.
- Make the task checks literal: specify the payload test imports and fixture string, and use a no-match assertion for `STABLE_TOP = ` (`rg -c` does not print `0` on no match). `.planning/phases/40-resilient-review-sized-by-jev/40-06-PLAN.md:130–131,155–164`.

**Risk Assessment: HIGH.** The main production input can yield no classifications at the cap, while malformed or conflicting summary text can bypass the severe-finding rule.

##### Ponytail findings
- **HIGH — Task 1:** Needed for REV-02. Keep one adapter and the existing CLI registration pattern (`skill_classify.py:197–220`). Reuse the parser after fixing the producer/consumer mismatch; resolve jev presence once so `"asked"` cannot disagree with the call actually made.
- **HIGH — Task 2:** Needed for R5’s boundary, empty, encoding and precision checks. Use the same fake client, but feed it one real merged-report fixture. More fabricated `Finding` tuples will not catch the handoff or severity bugs. `.planning/phases/40-resilient-review-sized-by-jev/40-06-PLAN.md:155–164`.

#### 40-07

**Summary.** Local signal detection, one advisory sizing adapter, and one sizing event are a good division of work. The selection step must respect quota results, and the jev request must not expose raw configuration strings. The task split also needs tighter instructions for an unattended executor.

**Strengths**
- The signal branch runs before jev, and the no-jev test pins `reviewers.json` byte-for-byte. This is the right distinction between a deterministic floor and advice. `.planning/phases/40-resilient-review-sized-by-jev/40-07-PLAN.md:126–134`; `.planning/phases/40-resilient-review-sized-by-jev/40-SPEC.md:126–135`.
- The plan reuses the row builder, atomic writer, and append-only log rather than adding a second CLI or persistence format. `.planning/phases/40-resilient-review-sized-by-jev/40-07-PLAN.md:125–128`; `.planning/phases/40-resilient-review-sized-by-jev/40-02-PLAN.md:125–127`; `.planning/phases/40-resilient-review-sized-by-jev/40-01-PLAN.md:117–120`.

**Concerns**
1. **HIGH — Sizing can undo Step 0.7’s quota selection.** `_with_second_lane` checks route, not quota. With ordered lanes A/B/C, if A is blocked and `resolve-reviewers` returns B, a security signal adds A back ahead of eligible C. The ping must then replace A again, marks the review partial, and can no longer truthfully describe the sizing decision as two available lanes. The proposed CLI test starts from a hand-written one-lane row and never exercises that sequence. `.planning/phases/40-resilient-review-sized-by-jev/40-07-PLAN.md:125–134`; `skills/ai-kit-spec-review/ai_kit_spec/cli.py:962–973`; `skills/ai-kit-spec-review/ai_kit_spec/quota.py:64–101,180–193`; `.planning/phases/40-resilient-review-sized-by-jev/40-09-PLAN.md:165–166`.
2. **HIGH — The sizing payload violates the no-config-values prohibition.** It sends raw review-order keys as criteria. The order reader accepts string keys, not a safe vocabulary. Clipping and redacting arbitrary `--archetype`/`--framework` values does not make them validated labels either. The proposed test pins the raw-key leak by requiring those exact keys. A one-lane roster also sends a one-option choice that the real ladder rejects; the fake does not enforce that minimum. `.planning/phases/40-resilient-review-sized-by-jev/40-07-PLAN.md:126,213`; `skills/ai-kit-spec-review/ai_kit_spec/role_orders.py:12–28`; `skills/jev-fast-decision/scripts/jev_ladder.py:218–221,583–591`.
3. **MEDIUM — Task 3’s fixtures do not match the supplied helper.** The task calls `SizeInput(CONFIG, ...)` but declares `SIZE_CONFIG`. More importantly, the inherited `answers_run` indexes every requested ID, but the low and invalid-pick cases do not consistently supply both answers. A missing entry raises `KeyError` in the fake instead of taking jev’s missing-answer path. The outside-roster test also starts with two rows and asks for two, so it cannot prove that an unusable reviewer pick leaves count **and** order unchanged. `.planning/phases/40-resilient-review-sized-by-jev/40-07-PLAN.md:206–213`; `.planning/phases/40-resilient-review-sized-by-jev/40-06-PLAN.md:121`; `skills/ai-kit-spec-review/ai_kit_spec/jev_names.py:164–174`.
4. **MEDIUM — Task 1 leaves design work to the executor.** The direct `size_review` recipe is likely to exceed the 15-local pylint cap; it gives one function input handling, signal policy, item construction and answer application. It also does not specify whether adding/reordering rows mutates the original list. An in-place append can make `sizing.reviewers != reviewers` false, leaving the log and JSON file inconsistent. Task 2 samples trigger families, but does not pin each promised expression; e.g. deleting `rm\s+-rf` or `rotate\s+key` leaves the listed tests green. `.planning/phases/40-resilient-review-sized-by-jev/40-07-PLAN.md:120–127,168–176`; `pyproject.toml:70–80`.

**Suggestions**
- Carry the same selection evidence into sizing, so the second candidate comes from the ordered, routable, quota-eligible lanes. Preserve the locked one-lane explanation when there is no eligible second lane. Test `probe-quota → resolve-reviewers → size-review → ping-lanes` with fakes.
- Use opaque position tokens in the jev choice and map them back locally. Send only known category labels, and omit the reviewer item when fewer than two eligible choices exist. Bind the client cwd to `--cwd`, following `skill_classify.py:128`. Make the fake enforce the real request shape.
- Give Task 1 explicit helper boundaries and require result rows to be a new list when changed. Specify malformed-input handling and write the sizing event only for the selection actually persisted. In Task 3, pin low reviewer and low count cases independently and use a count-changing answer in the invalid-pick case.

**Risk Assessment: HIGH.** The proposed sizing can bypass quota selection and transmit configuration values. The current tests can miss both.

##### Ponytail findings
- **HIGH — Task 1:** Needed for REV-06. Reuse ordered-lane selection (`role_orders.py:85–101`) and the shared row writer. Don’t walk the roster a second time with weaker eligibility rules. Ten files across the plan is above the rough five-file target; the three tasks each touch at most five, but split the tracer by behavior if the repaired implementation plus gates no longer fits the lane budget. `.planning/phases/40-resilient-review-sized-by-jev/40-07-PLAN.md:7–17,110–136`.
- **MEDIUM — Task 2:** Needed for the R6 backstop. Keep the four fixtures and reuse the listing generator (`tools/gen_test_groups.py:96–104`). A table of every trigger is enough; no framework parser is needed.
- **HIGH — Task 3:** Needed for the roster, no-jev and payload prohibitions. Reuse the fake response seam, but test opaque criteria and the actual ladder constraints, not just payload context. `skills/jev-fast-decision/scripts/jev_ladder.py:198–222`; `.planning/phases/40-resilient-review-sized-by-jev/40-07-PLAN.md:205–214`.

#### Batch assessment

- **Dependencies and waves:** No same-wave file overlap. Waves 4–7 each have one plan; the artifacts from 40-01 through 40-03 are available transitively. The material problems are incompatible handoffs, not missing dependency edges.
- **Coverage:** The phase assigns all eleven acceptance lines, the covered/backstop edges, and the five prohibitions to plans or closing evidence (`.planning/phases/40-resilient-review-sized-by-jev/40-VALIDATION.md:39–54`; `.planning/phases/40-resilient-review-sized-by-jev/40-13-PLAN.md:127`). Assignment is not proof. The uncovered cases that matter here are **R1 retry after expiry with renewal**, **R5 classification of a real merged cap report and every skip**, and **R6 sizing without undoing quota selection or sending config values**. R6’s roster reordering also exposes an R4 backstop mismatch: 40-01 derives “roster order” from merge argv, but 40-07 may reorder those rows. Preserve the owner’s order separately for report rendering. `.planning/phases/40-resilient-review-sized-by-jev/40-SPEC.md:223`; `.planning/phases/40-resilient-review-sized-by-jev/40-01-PLAN.md:126`; `.planning/phases/40-resilient-review-sized-by-jev/40-07-PLAN.md:126`.
- **Verification and handoff:** The unittest runner accepts the named module form and really emits `=== <module>: FAILED (rc=…)` with a nonzero aggregate exit. The recorded gate timings do not establish the 1,800-second executor budget for these tasks. Plans 40-06 and 40-07 correctly regenerate listings, which triggers the full unit/arch commit hook. The downstream pooled eval fixture still needs a **PROVISIONAL** label; 40-09 labels the reference, but 40-11’s fixture recipe does not. `tools/run_unittest_parallel.py:226–232,895–913,935–945`; `AGENTS.md:221–228`; `.planning/phases/40-resilient-review-sized-by-jev/40-09-PLAN.md:130`; `.planning/phases/40-resilient-review-sized-by-jev/40-11-PLAN.md:94–98`.

**Verdict: Revise all four before dispatch.** Fix the pool-role and timeout handoffs first, then make classification consume real merged reports and make sizing preserve quota eligibility and payload privacy.

Not checked: live runner or jev behavior, suite results, or executor timings. This was a read-only review; no files changed and no tests or make targets ran.

#### Batch C (40-08, 40-09)

#### 40-08

##### Summary

The deterministic fold check is the right shape for REV-08: a small stdlib command, a positive/negative fixture pair, and an optional input to the existing report merge. The single-document path is well specified. The plan is not ready to execute, though: a heading outside the last task can suppress the finding, and the finding loses the document identity needed to route fixes in a mixed review.

##### Strengths

- **Reuses the report contract.** The proposed bullet matches the existing parser, and the existing renderer turns a parsed HIGH into `Issues Found`. Adding the finding after lane validation keeps `fold-check` out of the lane count and preserves the old no-log failure path. (`.planning/phases/40-resilient-review-sized-by-jev/40-08-PLAN.md:110–118`; `skills/ai-kit-spec-review/ai_kit_spec/review_reports.py:9–13,125–144`; `skills/ai-kit-spec-review/ai_kit_spec/cli.py:976–1001`)
- **Keeps the fixtures and runtime dependency small.** Both reviewed demo files end at Task 2; the execute-only fixture stops at setup and does not need changing. The adapter wording can be pinned from a test without a runtime cross-skill import. (`.planning/phases/40-resilient-review-sized-by-jev/40-08-PLAN.md:181–195`; `skills/ai-kit-spec-review/evals/files/active/project/docs/superpowers/plans/demo.md:14–19`; `skills/ai-kit-spec-review/evals/files/no-config/project/docs/superpowers/plans/demo.md:14–19`; `skills/ai-kit-spec-review/evals/evals.json:123–129`; `tests/test_arch.py:1547–1561`)

##### Concerns

1. **HIGH — The check can mistake an example or trailing section for a real fold task.** Task 1 scans from the last raw `### Task ` match through EOF and accepts any heading or checkbox in that slice. A fold mention in a fenced Markdown example or under a later `## Self-Review Notes` section suppresses the required HIGH. Trailing self-review sections exist in this repo; Task 2 tests prose and earlier tasks, but neither boundary. (`.planning/phases/40-resilient-review-sized-by-jev/40-08-PLAN.md:110–111,155–158`; `docs/superpowers/plans/2026-09-02-ai-kit-model-discovery-consumers.md:680–689`)
2. **HIGH — Multiple documents can lose the finding or send it to the wrong revise handler.** Each finding has the same `Location: last ### Task`, and 40-09 appends all blocks to one file. The existing merge deduplicates across reports by severity and location, and uses the title to disambiguate repeats within a report. Two identical findings lose document identity; three with the same title and location collapse to at most two. A reviewer HIGH at the same location can also absorb the deterministic finding, keeping the reviewer’s `Required:` text. The revise router requires a document and archetype per finding and surfaces ambiguous findings instead of dispatching them. 40-10’s fold note does not change that rule. (`.planning/phases/40-resilient-review-sized-by-jev/40-08-PLAN.md:110–117`; `.planning/phases/40-resilient-review-sized-by-jev/40-09-PLAN.md:170`; `.planning/phases/40-resilient-review-sized-by-jev/40-10-PLAN.md:142–143`; `skills/ai-kit-spec-review/ai_kit_spec/review_reports.py:72–101`; `skills/ai-kit-spec-review/references/apply-findings.md:7–22`)
3. **MEDIUM — The tests do not prove the full merge contract at this wave.** The positive tracer uses one lane without a log. The two-lane test uses the old fail-closed path and expects the fold finding to disappear. 40-13 does exercise the logged merge later, but only with one surviving report. Neither test catches loss of the fold `Required:` text when another report flags the same location. (`.planning/phases/40-resilient-review-sized-by-jev/40-08-PLAN.md:118,160–166,234`; `.planning/phases/40-resilient-review-sized-by-jev/40-13-PLAN.md:90–91`; `skills/ai-kit-spec-review/ai_kit_spec/review_reports.py:87–100`)
4. **LOW — A few task details invite fixes the executor should not have to infer.** Task 2 uses `contextlib.redirect_stderr` without adding the import to Task 1’s documented imports and offers to adapt the failure assertion even though 40-01 explicitly preserves it. Task 3’s unit assertion also passes if all task headings are removed: `fold_finding` returns `None` for that input. The separate `rg` check is stronger than the permanent test. (`.planning/phases/40-resilient-review-sized-by-jev/40-08-PLAN.md:111,118,163–167,193–203`; `.planning/phases/40-resilient-review-sized-by-jev/40-01-PLAN.md:201`; `tests/test_ai_kit_spec.py:3664–3673`)

##### Suggestions

- Bound recognition to the last real task, excluding fenced examples and later peer or parent sections. Add one negative fixture for each boundary; keep the locked wording and case-insensitive heading/checkbox behavior.
- Preserve the locked standalone finding text, but carry the document identity into the merge and revise handoff. Test two missing-fold plans in a mixed document set and one reviewer finding at the same location. Assert that each affected plan reaches `superpowers:writing-plans` with the deterministic `Required:` text intact.
- Add the logged two-lane case to this wave, then pin Task 3’s actual final heading in the permanent test. Spell out the stderr import and keep the no-log failure expectation exact.

##### Risk Assessment

**HIGH for REV-08 correctness; low for runtime cost.** For this solo-developer workflow, reading and scanning a plan once per round does not justify a new parser dependency. The risk is a wrong verdict or an unrouteable fix, not throughput. Both locked R7 backstops are assigned; the gap is the real Markdown boundary and multi-document handoff. No phase prohibition is specific to this slice, so the empty `must_haves.prohibitions` is reasonable.

##### Ponytail findings

- **Task 1 — HIGH:** Required by D-08. Keep `register_parsers`/`COMMANDS` and the existing report merger; do not add a second report format. The small change still needs to carry identity to the revise caller. (`skills/ai-kit-spec-review/ai_kit_spec/skill_classify.py:197–220`; `skills/ai-kit-spec-review/ai_kit_spec/review_reports.py:72–101`; `.planning/phases/40-resilient-review-sized-by-jev/40-08-PLAN.md:110–119`)
- **Task 2 — MEDIUM:** Required for the R7 edges. Reuse the existing in-process `main`/captured-stdout test pattern; spend the tests on the logged merge and Markdown boundaries, not duplicate scope assertions or method counts. (`tests/test_ai_kit_spec.py:3646–3662`; `.planning/phases/40-resilient-review-sized-by-jev/40-08-PLAN.md:153–175`)
- **Task 3 — LOW:** Both fixture edits are needed; no adapter edit or third fixture update is needed. Pin the actual final task using the wording already documented by the adapter. (`skills/ai-kit-spec-execute-superpowers/SKILL.md:108`; `skills/ai-kit-spec-review/evals/evals.json:123–129,153–159`; `.planning/phases/40-resilient-review-sized-by-jev/40-08-PLAN.md:185–203`)

#### 40-09

##### Summary

This is not just documentation: `SKILL.md` is the executable control flow the host agent follows. The plan connects the right commands in the common path and preserves important text contracts, but leaves contradictory instructions at the failure, resume, and fixer branches. The proposed text tests can pass while those branches still skip required behavior.

##### Strengths

- **The reason lock checks the runtime source of truth.** The table is scoped to `## Reasons`, compared against `REASONS`, and checked for duplicates. Adding or removing a synthetic row demonstrates that the comparison can detect drift. The pattern already exists in the repository. (`.planning/phases/40-resilient-review-sized-by-jev/40-09-PLAN.md:132–137`; `skills/ai-kit-spec-review/ai_kit_spec/error_classifier.py:14–26`; `tests/test_cross_ai_settings_text.py:59–60`)
- **The normal-round wiring preserves compatibility where it matters.** The plan adds the dispatch log flags, runs the logged merge with one survivor, and checks partial approval before plain approval. It keeps the existing three status-row spellings and the owner-only edit-lens path. The current status parser already recognizes the approval prefix. (`.planning/phases/40-resilient-review-sized-by-jev/40-09-PLAN.md:166–172,204–206`; `tests/test_ai_kit_spec_review_checklist.py:25–29`; `skills/ai-kit-spec-review/ai_kit_spec/review_reports.py:22–28`; `skills/ai-kit-spec-review/SKILL.md:282–295`)

##### Concerns

1. **HIGH — The mandatory exit and resume instructions still contradict switch-first and partial merge.** Task 2 inserts switch-first, but leaves “Every nonzero exit … so Step 1.5 fails closed.” The mandatory dispatch reference likewise still says a terminal failure makes the whole merge fail. Its resume argv omits `--lane-log`/`--round`, and resumed exits bypass the new switch branch. For example, an unflagged lane that first waits and later stops with auth can retain its earlier quota reason; a flagged lane that reaches quota on resume has no switch-first instruction. Also require an explicit reread of the replacement row and serialize `switch-lane` calls: 40-03 rewrites the full JSON array, so two concurrent switches can pick the same fallback or overwrite each other. (`.planning/phases/40-resilient-review-sized-by-jev/40-09-PLAN.md:167–171,208–209`; `.planning/phases/40-resilient-review-sized-by-jev/40-03-PLAN.md:111–113`; `skills/ai-kit-spec-review/SKILL.md:405–419,445–459`; `skills/ai-kit-spec-review/references/cross-ai-dispatch.md:254–272,315–337,355–376`)
2. **HIGH — Disagreements can bypass jev, including at the cap.** Task 3 only inserts prose after the fixer table. `Edits Applied` can include skipped findings and still jumps straight to the next round; Step 2’s cap row jumps straight to Surface. Even if the host runs the cap command, 40-06 parses `EFFECTIVE_REPORT_PATH` with `parse_findings`, but the merged renderer adds `(Reviewers: …)` after the final period and `_BULLET_RE` ends at the period. A normal logged cap report can therefore yield zero cap-open items. Finally, the unchanged Step 5 templates still ask the owner to decide on unfiltered findings, even if jev routed some to `skipped`. (`.planning/phases/40-resilient-review-sized-by-jev/40-09-PLAN.md:134,203–204,210`; `.planning/phases/40-resilient-review-sized-by-jev/40-06-PLAN.md:112–118`; `skills/ai-kit-spec-review-fixer/SKILL.md:79–91`; `skills/ai-kit-spec-review/SKILL.md:459–461,488–497,508–513`; `skills/ai-kit-spec-review/ai_kit_spec/review_reports.py:11–13,137–144`)
3. **HIGH — The summaries-only promise is stronger than the payload control.** The doc test proves a sentence exists. The adapter sends clipped fixer reasons and titles derived from untrusted reports. Removing backtick spans and redacting known token shapes does not keep an unquoted config value or verbatim file fragment out of those fields. The planned payload test puts raw content mainly in fields the adapter already ignores; it does not prove the prohibition for the fields actually transmitted. (`.planning/phases/40-resilient-review-sized-by-jev/40-09-PLAN.md:133,136,241–242`; `.planning/phases/40-resilient-review-sized-by-jev/40-06-PLAN.md:112–115,164`; `skills/ai-kit-spec-review/ai_kit_spec/secret_shapes.py:91–103`; `skills/ai-kit-spec-review/ai_kit_spec/jev_names.py:140–153`)
4. **HIGH — Ping and fold command failures lack a safe branch.** Step 1 stops explicitly on ping exit 3 only. A config error returns 2, and `ping-lanes` can fail before rewriting `reviewers.json`; the next instruction rereads that stale file and proceeds. Similarly, `check-fold-step` returns 2 on unreadable input, but the runbook checks only whether the appended output file is nonempty. An empty file can mean “no finding” **or** “not checked,” and the latter can lead to a clean approval. The opening claim that nothing in the new reference runs without a log also conflicts with the intentional native-only fold path and leaves no explicit missing-helper fallback for classification. (`.planning/phases/40-resilient-review-sized-by-jev/40-09-PLAN.md:128,134,166,170–171,203`; `.planning/phases/40-resilient-review-sized-by-jev/40-08-PLAN.md:114`; `skills/ai-kit-spec-review/ai_kit_spec/cli.py:1474–1481`; `skills/ai-kit-spec-review/references/cross-ai-dispatch.md:109–123`)
5. **MEDIUM — The reference promises evidence the implementation does not produce.** A rejected replacement candidate is excluded but not logged, so its ping failure has no review-log reason. The later-round cache check can reuse a recent successful probe **after** a lane failed dispatch, and the planned failed-lane test supplies no such cache entry. Finally, the documented owner-roster ordering is not the same as order after sizing or replacement: 40-01 derives its roster from merge arguments, and 40-09 takes those from the mutable reviewer list. (`.planning/phases/40-resilient-review-sized-by-jev/40-09-PLAN.md:129–132,166,171`; `.planning/phases/40-resilient-review-sized-by-jev/40-02-PLAN.md:132–133,211–218`; `.planning/phases/40-resilient-review-sized-by-jev/40-01-PLAN.md:122–126,168–171`; `.planning/phases/40-resilient-review-sized-by-jev/40-SPEC.md:100–101,223`)
6. **MEDIUM — The prescribed commands leave unresolved choices for the executor and host.** Sizing is an imperative in two places, and the reference is written before either caller knows which one owns the call. The new commands also need the existing first-document-root rule for labeled cross-repo reviews. The fold append needs a defined reset/re-entry rule, and Task 1 says to prefer SUMMARY output over the locked strings without saying to stop on a contract mismatch. The same task describes ping replacement as the next dispatchable lane, omitting `lane_fallback`’s unflagged and different-pool filters. (`.planning/phases/40-resilient-review-sized-by-jev/40-09-PLAN.md:124,129–134,165,170,208`; `skills/ai-kit-spec-review/references/cross-ai-dispatch.md:138–142,176–196`; `skills/ai-kit-spec-review/ai_kit_spec/lane_settings.py:129–154`)
7. **LOW — Some caller-facing prose needs a bounded consistency pass.** The locked §8 sentence correctly preserves the exception, but §1 and §4 still state the blanket stop; add pointers so readers of those sections do not have to infer precedence. Qualify pool writes and clears as attempts—the runner can report failure to write or clear. The root README’s review row still says it loops until approved, with no mention of partial or not-reviewed output. Keep the existing runner-wide no-automatic-fallback wording intact. (`.planning/phases/40-resilient-review-sized-by-jev/40-09-PLAN.md:130,207–209`; `skills/ai-kit-cross-ai/SKILL.md:37–39,193–207,373–377`; `skills/ai-kit-spec-review/references/cross-ai.mjs:4126–4137`; `README.md:34`; `AGENTS.md:353–355`)

##### Suggestions

- Give each action one owner: point 5 sizes once, Step 1 pings once per new round, and the shared fresh/resume exit procedure handles switch-first, pending lanes, and failures. Preserve the existing no-log and one-shot behavior explicitly.
- Replace the relevant Step 2 and Step 4 **actions**, not their pinned status spellings. Classify skipped findings even after edits, make cap-open parsing round-trip the real merged report, and specify exactly what Step 5 shows for `owner`, `fixer`, and `skipped`. With no helper, failed classification, or unusable advice, keep the old path. Preserve revision authorization and the per-archetype revise route.
- Add fake behavioral checks for terminal sibling failure, pending-to-terminal resume, two simultaneous quota stops, a failed dispatch with a fresh cached ping, and a merged HIGH at the cap. Keep the literal text checks for wording; do not use them as evidence that branches work.

##### Risk Assessment

**HIGH.** The key risks are false clean approval, loss of a surviving report, and failure to route open findings. The fork between pending waits and terminal stops is especially important because it crosses invocations. The direct quota exit claim itself is grounded: the supervised off-router quota stop is a bare 75 with `stopped=class`; that is not a rule for interpreting every bare 75. (`skills/ai-kit-cross-ai/SKILL.md:193–207`)

##### Ponytail findings

- **Task 1 — MEDIUM:** D-09 needs the reference and D-01 needs the lock. Reuse the reason-table pattern and the canonical command reference; do not duplicate fallback rules in a form that omits conditions. (`tests/test_cross_ai_settings_text.py:59–60`; `skills/ai-kit-spec-review/references/cross-ai-dispatch.md:138–196`; `.planning/phases/40-resilient-review-sized-by-jev/40-09-PLAN.md:127–137`)
- **Task 2 — HIGH:** The wiring is required, but adding paragraphs beside superseded instructions makes the host choose which rule wins. Edit the existing exit and merge branches and their mandatory resume reference together. No new state file or runner template change is needed. (`skills/ai-kit-spec-review/SKILL.md:399–449`; `skills/ai-kit-spec-review/references/cross-ai-dispatch.md:301–376`; `.planning/phases/40-resilient-review-sized-by-jev/40-09-PLAN.md:164–175`)
- **Task 3 — HIGH:** Classification, partial retention, and the caller exception are all needed. Reuse the existing Step 2/4 route tables and authorization check; the added paragraph and command-name assertions are not substitutes for wiring those routes. Keep 40-10’s prompt handoff synchronized. (`skills/ai-kit-spec-review/SKILL.md:453–497,547–551`; `.planning/phases/40-resilient-review-sized-by-jev/40-09-PLAN.md:203–211`; `.planning/phases/40-resilient-review-sized-by-jev/40-10-PLAN.md:137–143`)

#### Batch coverage and execution checks

- **Waves and dependencies:** No same-wave overlap. Waves 8 and 9 each contain one plan. The serial chain gives 40-08 the 40-01 merge helper and gives 40-09 the earlier CLI commands. 40-10, 40-11, and 40-13 consume the planned docs, fixtures, and CLI outputs after those waves. The problem is what crosses the handoffs, not their order. (`.planning/phases/40-resilient-review-sized-by-jev/40-08-PLAN.md:5–6,117`; `.planning/phases/40-resilient-review-sized-by-jev/40-09-PLAN.md:5–6`; `.planning/phases/40-resilient-review-sized-by-jev/40-10-PLAN.md:5–6,99–101`; `.planning/phases/40-resilient-review-sized-by-jev/40-11-PLAN.md:88–95`; `.planning/phases/40-resilient-review-sized-by-jev/40-13-PLAN.md:83–91`)
- **SPEC traceability:** R1 is assigned to 40-03–05 plus the 40-09 doc contract; R2 to 40-02/09/12; R3–R4 to 40-01/02/09/10; R5 to 40-06/09/10; R6 to 40-07/09; R7 to 40-08/09/10; and R8 to 40-11/12. The five prohibitions have planned assertions across 40-01/02/03/06/07/09. Assignment is not proof: the uncovered behaviors are the R2 failed-lane/cache combination, individual ping-failure reasons and true roster ordering in R3–R4, the R5 skip/cap and payload paths, and R7’s mixed-document repair. The roster-order backstop in particular tests a supplied list, not that the caller passes the owner’s order. (`.planning/phases/40-resilient-review-sized-by-jev/40-SPEC.md:180–253`; `.planning/phases/40-resilient-review-sized-by-jev/40-VALIDATION.md:39–53`; `.planning/phases/40-resilient-review-sized-by-jev/40-01-PLAN.md:126,171`)
- **MEDIUM — Make the verification handoff explicit in both plans.** The unittest commands and `FAILED` markers match the runner. Both plans name `make check-dogfood`, but neither assigns it in its per-wave steps; it is a live-project check that reads the GSD consent state, not another hermetic lane test. Assign it to the orchestrator and specify who writes and commits the SUMMARY, since `<output>` is not in the one-task prompt. Both plans exceed the approximate five-file plan budget (nine and seven files); the two Task 1 commits trigger the full unit/arch hook through generated listings. That is a scheduling risk, not evidence that either hits 1,800 seconds. The new tests need no real host, jev, or Node; the existing `tests.test_ai_kit_spec` module does have a real-Node parity test, so scope the no-real-Node rule explicitly to new tests or name the sanctioned existing gate. (`.planning/phases/40-resilient-review-sized-by-jev/40-08-PLAN.md:7–16,119,229–251`; `.planning/phases/40-resilient-review-sized-by-jev/40-09-PLAN.md:7–14,137,246–256`; `tools/run_unittest_parallel.py:225–232,884–913,939–945`; `tools/check_dogfood.py:334–369`; `tests/test_ai_kit_spec.py:1634–1653`)

**Verdict: revise both plans before dispatch.** Fix the fold finding’s document identity and the fresh/resumed exit and cap paths first; they can change the result the owner sees.

Static, read-only review. No files changed, no suites or live lanes run, and no executor timing measured.

#### Batch D (40-10, 40-11, 40-12, 40-13)

### Phase 40 plan review

**What this change does:** Plans 40-10 through 40-13 document the resilient review loop, add scenario evals, judge the changed skills, and verify the installed commands before marking the phase complete. I reviewed these as plans for a solo-maintainer project. The main risks are incorrect routing at the handoffs and closing evidence that can look green without exercising the promised behavior.

#### 40-10

**Summary:** The plan keeps the generic fixer change small and correctly assigns the superpowers fold edit to `writing-plans`. It does not yet make the disagreement routes agree across the main skill, reference, and diagram.

**Strengths**

- Task 3 adds one editing rule alongside the existing CRITICAL/HIGH rule and reuses the fixer’s section-scoped test pattern; it does not create a second fixer protocol (`.planning/phases/40-resilient-review-sized-by-jev/40-10-PLAN.md:163–169`; `skills/ai-kit-spec-review-fixer/SKILL.md:38–51`; `tests/test_ai_kit_spec_review_fixer.py:78–100`).
- Task 2 correctly keeps the fold edit out of the generic fixer. The framework profile already routes plans to `superpowers:writing-plans`, whose revise prompt consumes the review report (`.planning/phases/40-resilient-review-sized-by-jev/40-10-PLAN.md:142`; `skills/ai-kit-spec-review-checklist/references/frameworks/superpowers.md:29–37`; `skills/ai-kit-spec-review/references/apply-findings.md:70–83`).

**Concerns**

1. **HIGH — A fixer can skip a finding without ever reaching jev.** A summary with one edit and one skip legitimately returns `Edits Applied` (`skills/ai-kit-spec-review-fixer/SKILL.md:76–91`). Task 1 preserves the direct `Edits Applied` → next-round edge, and 40-09’s classifier hook only runs on `Escalation Required`, `No Edits`, or the cap. Task 2 says to classify skips but never resolves that contradiction. Its string tests also pass if the guard against a second mechanical re-pass is missing from the actual routing (`.planning/phases/40-resilient-review-sized-by-jev/40-10-PLAN.md:110–113,139–143`; `.planning/phases/40-resilient-review-sized-by-jev/40-09-PLAN.md:203`).
2. **HIGH — The fold handoff loses the document in a multi-document run.** The existing reference assigns findings to handlers by `Location` and surfaces any finding whose document cannot be identified. The producer emits the same `Location: last ### Task` for every document and appends the output into one file. Two plans missing the step therefore yield findings that Task 2 cannot reliably route to the right plan; the test only verifies that two phrases share a section (`.planning/phases/40-resilient-review-sized-by-jev/40-10-PLAN.md:142–143`; `skills/ai-kit-spec-review/references/apply-findings.md:7–22`; `.planning/phases/40-resilient-review-sized-by-jev/40-08-PLAN.md:110–117`; `.planning/phases/40-resilient-review-sized-by-jev/40-09-PLAN.md:170`).
3. **MEDIUM — The diagram makes conditional steps unconditional.** Task 1 sends every start through sizing and ping and every round through logged merge, although 40-09 explicitly skips sizing and the round log for native-only runs. The existing pending-lane contract also forbids merging the pending lane and running a fixer while it waits. The prescribed edge counts reward keeping the misleading graph unchanged (`.planning/phases/40-resilient-review-sized-by-jev/40-10-PLAN.md:107–123`; `.planning/phases/40-resilient-review-sized-by-jev/40-09-PLAN.md:165–172`; `skills/ai-kit-spec-review/references/cross-ai-dispatch.md:301–314`).
4. **MEDIUM — Task 2 has an acceptance command that exits 2 regardless of the edit.** `rg -c -F "- Mechanical re-pass: …"` treats the leading hyphen as an option; I confirmed the exact command returns `unrecognized flag`. Task 3’s test also accepts a row that drops the “only when impossible, with a reason” clause because it checks just the opening text (`.planning/phases/40-resilient-review-sized-by-jev/40-10-PLAN.md:151,167–168`).

**Suggestions**

- Make the classifier trigger depend on the summary’s contents, not just its status. Pin the mixed edit-plus-skip case, the one-re-pass limit, and the cap call without a Fix Summary. Scope the re-pass to the applicable direct-edit report and documents already used by Step 3a.
- Preserve the originating document at the fold-check handoff. Test two plans in one review, including a case where only one lacks the step.
- Use `rg -c -F -e "- Mechanical re-pass: <MECHANICAL_TITLES>" …`; replace line-count checks for the diagram with checks of the branches that matter.

**Risk assessment: HIGH.** The edit count fits the cross-AI task budget, but the docs are executable instructions for the review agent. The current gaps can silently skip an advisory classification or route a required fold edit to the wrong document.

##### Ponytail findings

- **MEDIUM — Task 1:** D-09 needs the diagram update, not a new diagram system. Keep the existing DOT companion and show the logged path as conditional (`skills/ai-kit-spec-review/references/loop-diagram.md:3–9,30–38`).
- **HIGH — Task 2:** R5/R7 need the template changes. Reuse the existing per-route report split rather than introducing another fixer or copying the classifier rules into a third authority (`skills/ai-kit-spec-review/references/apply-findings.md:22,35–59`).
- **LOW — Task 3:** One row and one section-scoped test are enough; assert the safety clause as well as the row’s prefix. Plan 40-11 supplies the semantically relevant eval (`tests/test_ai_kit_spec_review_fixer.py:78–91`; `.planning/phases/40-resilient-review-sized-by-jev/40-11-PLAN.md:126`).

#### 40-11

**Summary:** The two tasks are small and provide the requested four review evals plus a fixer eval. The fixtures need to establish the claimed starting state, and one expected report contradicts the round-log contract.

**Strengths**

- The proposed eval fields and paths follow the actual shape and fixture-listing checks. Task 2 reuses a report that contains both the named MEDIUM finding and a separate HIGH finding (`.planning/phases/40-resilient-review-sized-by-jev/40-11-PLAN.md:94–100,120–126`; `tests/test_skill_evals_shape.py:41–65,71–93`; `tests/test_spec_chain_text.py:492–497`; `skills/ai-kit-spec-review-fixer/evals/files/plan-bad-review.md:9–17`).
- Copying the fixture after 40-08 adds its fold task keeps an unrelated HIGH finding out of the lane scenarios. The refusal eval is left intact (`.planning/phases/40-resilient-review-sized-by-jev/40-08-PLAN.md:185–192`; `.planning/phases/40-resilient-review-sized-by-jev/40-11-PLAN.md:89,95,111`; `skills/ai-kit-spec-review/evals/evals.json:142–150`).

**Concerns**

5. **HIGH — The blocked-ping eval expects the wrong reason in the report.** Task 1 correctly expects stdout `ping review-second: replaced by review-third (auth)`, then requires `auth` as the report reason. The event stores `reason=replaced`, `cause=auth`, and `by=review-third`. The renderer prints `reason` and `by`, not `cause`. A correct result fails the proposed assertion (`.planning/phases/40-resilient-review-sized-by-jev/40-11-PLAN.md:98`; `.planning/phases/40-resilient-review-sized-by-jev/40-02-PLAN.md:133`; `.planning/phases/40-resilient-review-sized-by-jev/40-01-PLAN.md:122–123,168`).
6. **MEDIUM — The scenarios don’t pin the state before the simulated failure.** The prompts say to copy the project and run from it, but do not pin the output of the prior quota walk, the rows after sizing, or the cache age. A fresh Step 0.7 verdict can satisfy the first ping without a new probe; a blocked lane in that walk can be excluded before the ping begins. `double` also does not by itself guarantee the named pair: secondary resolution applies a vendor filter, and sizing can change the pair. The JSON shape checks cannot catch an unreachable scenario (`.planning/phases/40-resilient-review-sized-by-jev/40-11-PLAN.md:94–100`; `skills/ai-kit-spec-review/ai_kit_spec/quota.py:87–95,180–191`; `.planning/phases/40-resilient-review-sized-by-jev/40-07-PLAN.md:124–127`; `.planning/phases/40-resilient-review-sized-by-jev/40-09-PLAN.md:129,165–166`).
7. **MEDIUM — The executor/judge boundary is implicit.** These are transcript-assessed evals, but their imperative prompts describe running placeholder lanes and a jev client without explicitly saying those results are simulated. The same plan omits the required post-wave unit/arch gate, and its free-pool fixture is not labelled PROVISIONAL (`.planning/phases/40-resilient-review-sized-by-jev/40-11-PLAN.md:94–100,158–168`; `.planning/phases/40-resilient-review-sized-by-jev/40-13-PLAN.md:127`; `.planning/phases/40-resilient-review-sized-by-jev/40-SPEC.md:174–178`).
8. **LOW — The fixer eval doesn’t assert its claimed HIGH outcome.** It promises the HIGH is addressed, but the explicit assertions check only the Goal edit, MEDIUM routing, and status. The missing assertion matters because the fixture carries a real second edit at `Modify: TBD` (`.planning/phases/40-resilient-review-sized-by-jev/40-11-PLAN.md:126`; `skills/ai-kit-spec-review-fixer/evals/files/plan-bad-review.md:9–15`).

**Suggestions**

- Assert three separate facts in the ping eval: stdout reports `auth`, the log stores `cause=auth`, and the report renders `review-second (replaced, by review-third)`.
- Say explicitly that the evals use simulated tool responses. Pin the initial pair, no sizing override, and stale or absent cache for the probe case. Give the fixtures explicit distinct placeholder vendors where independence matters.
- Add one assertion for the actual HIGH edit in Task 2. Restore the post-wave unit/arch gate before code review.

**Risk assessment: MEDIUM.** The work is mechanically small and fits the executor budget. The danger is that shape-valid evals can penalize correct behavior or award credit for a path the supplied setup does not establish.

##### Ponytail findings

- **MEDIUM — Task 1:** D-10 needs four scenarios, not four fixture trees. Keep the shared fixture and existing setup convention; specify the fake pre-round state once and vary the failure (`tests/test_spec_chain_text.py:492–501`).
- **LOW — Task 2:** The existing two-finding report is enough. Add the missing HIGH assertion rather than authoring another fixture or evaluator (`skills/ai-kit-spec-review-fixer/evals/files/plan-bad-review.md:9–15`).

#### 40-12

**Summary:** The plan uses the existing judge tool, preserves its count authority, and separates advisory evidence from the scored result. The live preflight and the reused driver checks need correction before paid lanes start.

**Strengths**

- The Git-derived skill set and frozen-tree validation are stronger than trusting a hardcoded list: the inherited helper checks changed paths against the registry, and the judge checker rejects mixed digests within a round (`.planning/phases/40-resilient-review-sized-by-jev/40-12-PLAN.md:105–114`; `tmp/judge-39.2/judged.py:34–62`; `tools/judge_loop.py:1311–1319`).
- The native substitute uses the existing manifest and ingest path. The recorded comparison baselines match the checked-in report, and the proposed gate keeps the tool’s regression calculation (`.planning/phases/40-resilient-review-sized-by-jev/40-12-PLAN.md:28–33,113`; `tools/judge_loop.py:648–674,1619–1636`; `.planning/judge/REJUDGE.md:27,34–36`).

**Concerns**

9. **HIGH — The real-HOME ping is not read-only.** Step 5 calls the ping with real HOME against the main checkout. The 40-02 handler calls `cfg_resolve` with migration enabled, which can migrate both the project and user rosters. The inherited legacy preflight deals with runner retry config, not `review-spec.toml` migration. Auditing afterwards detects some changes; it does not authorize or prevent the write (`.planning/phases/40-resilient-review-sized-by-jev/40-12-PLAN.md:112–114`; `.planning/phases/40-resilient-review-sized-by-jev/40-02-PLAN.md:134`; `skills/ai-kit-spec-review/ai_kit_spec/config_io.py:521–534,671–691,721–729`; `.planning/phases/39.2-spec-discuss-branch-strategy-for-stacked-units/39.2-09-PLAN.md:116`).
10. **HIGH — The runbook can stop before judging, or during a valid later round.** The collision scan includes `copy_drivers.py`, whose existing `OLD.sub("39.2", …)` is a known transformation hit not enumerated by the scan rule, and `verdict_facts.py` uses a split `"tmp" / "judge-39.2"` path. More importantly, `publish.py` refuses a differing destination loop JSON, while Step 5, if repeated literally, recounts the surviving skills with `--no-jev` before re-counting them. A changed advisory count or regenerated pool probe can therefore trip the publish guard. The plan must distinguish a per-round ping from round-1 pool/count initialization (`.planning/phases/40-resilient-review-sized-by-jev/40-12-PLAN.md:107–112,139`; `tmp/judge-39.2/copy_drivers.py:23–35`; `tmp/judge-39.2/verdict_facts.py:15–16`; `tmp/judge-39.2/publish.py:20–31,51–72`; `tmp/judge-39.2/lanes.py:379–398`).
11. **HIGH — “Closing judge check” does not enforce the bar.** The inherited `closing.sh` runs plain `judge_loop.py check`; the checker only makes an unmet bar fatal with `--gate`. Task 2 can meet its automated acceptance criteria with an unmet score, leaving 40-13 dependent on a manually transcribed summary to stop. A no-rejudge fix must not turn a failing score into a passing one (`.planning/phases/40-resilient-review-sized-by-jev/40-12-PLAN.md:139–152`; `tmp/judge-39.2/closing.sh:1–2`; `tools/judge_loop.py:1376–1396`; `AGENTS.md:65–79`).
12. **MEDIUM — The count-one path handles only one skill and does not establish an exactly-once verdict check.** The copied driver hardcodes a singleton `SKILLS` and one judge, and Task 1 names a single destination script. If multiple skills take that branch, it can overwrite a driver or leave a skill without its advisory verdict. `findings.py` counts findings, not the required presence of exactly one valid third-lane verdict: two non-null zero-finding verdicts would give the same finding count as one (`.planning/phases/40-resilient-review-sized-by-jev/40-12-PLAN.md:112–113,139`; `tmp/judge-39.2/advisory_extra.py:46–57`; `tmp/judge-39.2/findings.py:43–69`).

**Suggestions**

- Use the existing non-migrating roster path for the referee ping, and preflight both legacy roster and runner retry files before any live probe. Put the ping’s temporary work and state under the run folder; audit after a failed ping as well as a successful one.
- Specify the exact reuse exceptions and rehearse the copy/compile, count-one, and round-transition branches with fixtures before launching judges. Retain the recorded pool/count across rounds; re-ping and reassign only the round’s surviving skills.
- Make the existing gated check authoritative. Require exactly one non-null referee-three or labelled substitute record per skill/round, and keep an unmet result explicitly blocked even after a no-rejudge fix. Add `REV-07` to the frontmatter because this plan owns the live judge-round ping.

**Risk assessment: HIGH.** A failure here can affect real configuration, consume paid calls before a procedural stop, or produce locally valid records without proving JDG-04.

##### Ponytail findings

- **HIGH — Task 1:** The judge set, ping, and native substitute are required. Reuse `judge_loop.py` and the existing drivers, but enumerate the small Phase 40 differences instead of inheriting another phase’s full procedure by substitution (`tools/judge_loop.py:383–415,648–674`; `tmp/judge-39.2/lanes.py:379–398`).
- **HIGH — Task 2:** Reuse `bar_table.py`’s existing `--gate` call and `decide.py`’s decision table; add an explicit coverage check, not a parallel scoring tool. The handoff must distinguish “bar met,” “bar met, then fixed,” and “unmet: owner decision” (`tmp/judge-39.2/bar_table.py:77–92,110–123`; `tmp/judge-39.2/decide.py:10–15`).

#### 40-13

**Summary:** The closeout order is sound: linked-layout smoke test, full suites, dry run, narrow live check, then the ROADMAP tick. The scratch check is not hermetic as specified, and retries can mix evidence from different candidates.

**Strengths**

- The plan reuses the actual aggregate test target and the runner’s per-module `ran`, `rc`, and `skips` evidence. It distinguishes judged eval text from executed tests (`.planning/phases/40-resilient-review-sized-by-jev/40-13-PLAN.md:122–127`; `Makefile:75–89`; `tools/run_unittest_parallel.py:482–503`).
- The narrow link-only install is appropriate. The inherited helper inspects all requested destinations before changing any and never replaces an existing destination that points elsewhere. The final checkbox has a unique existing anchor (`.planning/phases/40-resilient-review-sized-by-jev/40-13-PLAN.md:146–157,192`; `tmp/run-2026-11-23/p39.2-10/live_links.py:14–41`; `.planning/ROADMAP.md:132`).

**Concerns**

13. **HIGH — The scratch smoke test can invoke a real CLI or fail on its own tripwire.** `KNOWN_CLIS` contains runtime IDs, not executable aliases: the `cursor` row looks up `cursor-agent` or `agent`, neither stubbed by Task 1. Even with no configured lanes, the planned size/ping handlers call `review_routes`; cold routing builds an inventory and invokes the available CLIs for model listings. Thus some commands can hit real binaries on the inherited PATH, while others hit the stubs and make the required empty-log assertion fail. The copied environment also retains host overrides stripped by the normal test runner (`.planning/phases/40-resilient-review-sized-by-jev/40-13-PLAN.md:89–96`; `.planning/phases/40-resilient-review-sized-by-jev/40-02-PLAN.md:127,134`; `.planning/phases/40-resilient-review-sized-by-jev/40-07-PLAN.md:127`; `skills/ai-kit-spec-review/ai_kit_spec/routing.py:265–281,353–365`; `skills/ai-kit-spec-review/ai_kit_spec/detection.py:112–136,1293–1321`; `tools/run_unittest_parallel.py:438–461`).
14. **HIGH — The prescribed restart reuses the old suite reports.** Task 2 always writes into the same directory. The runner preserves existing reports and writes numbered duplicates; the inherited evidence reader fails on duplicates. After the first `fix(40)` restart, a green run can fail evidence collection or be confused with prior reports unless the directory is made candidate-specific (`.planning/phases/40-resilient-review-sized-by-jev/40-13-PLAN.md:122–126`; `tools/run_unittest_parallel.py:494–503`; `tmp/run-2026-11-23/p39.2-10/evidence.py:21–28`).
15. **MEDIUM — The “real tools covered on the host” claim only checks exit codes.** Task 2b requires `rc == 0` for the named E2E and PTY modules but allows all their skips. Missing Node or checkout-local GSD tools can skip the real code path while the runner still prints `ok`. The predecessor gate checked the specific prerequisite skips; the new gate needs the equivalent for the cases it claims covered (`.planning/phases/40-resilient-review-sized-by-jev/40-13-PLAN.md:122–129`; `.planning/phases/39.2-spec-discuss-branch-strategy-for-stacked-units/39.2-10-PLAN.md:118`; `tests/test_ai_kit_spec_e2e.py:39–50,129–135`; `tests/test_cross_ai_runner_e2e.py:166–176`; `tests/test_wizard_pty.py:63–66`; `tools/run_unittest_parallel.py:939–945`).
16. **MEDIUM — The acceptance proof and live-install preconditions need to be executable.** Task 1 instructs the script to print only `layout: ok` on success but requires the captured command lines in the summary; it also does not assert merge exit codes or the exact `never_resolved` reason. Task 3 asks for same-SHA evidence, but the live step changes or selects the checkout tip before writing success without an explicit recheck against `candidate.txt` before the real-HOME write (`.planning/phases/40-resilient-review-sized-by-jev/40-13-PLAN.md:91–105,146,191–192`; `AGENTS.md:347–352`).

**Suggestions**

- Reuse `baseline_env` and `write_tripwire` and supply a fresh synthetic runtime cache with a current runner fact, or provide a deliberately restricted PATH with no real host executables or Node. Check the exact merge status, reason, and exit code; print the successful evidence lines before `layout: ok`.
- Write reports to a fresh candidate-SHA directory. Require the intended real-tool cases to have run on the host before using the clean-room exception.
- Compare `HEAD`, unit-branch tip, and `candidate.txt` immediately before live linking. If they differ, return to the candidate gate before writing anything to the real HOME.

**Risk assessment: HIGH.** A closing gate must neither reach real host tooling from its scratch test nor certify a candidate using evidence from a different run.

##### Ponytail findings

- **HIGH — Task 1:** The symlinked entrypoint smoke test is needed; a second homemade host-isolation mechanism is not. Reuse the test runner’s environment and tripwire helpers (`tools/run_unittest_parallel.py:370–387,438–461`).
- **MEDIUM — Task 2:** Keep the existing watchdog and module reports. Fix evidence provenance and skip checks rather than adding another full run (`tmp/run-2026-11-23/orch-guard.py:47–70`; `tools/run_unittest_parallel.py:482–503`).
- **LOW — Task 3:** The one-line tick is right-sized. Keep the same-SHA gate before the install and before the tick; no new closeout tool is needed (`.planning/phases/40-resilient-review-sized-by-jev/40-13-PLAN.md:143–157,190–193`).

#### Cross-plan coverage and sequencing

- **Wave check:** No same-wave overlap. Waves 10–13 each have one plan; the serial `40-09 → 40-10 → 40-11 → 40-12 → 40-13` chain also covers the transitive fixture and CLI dependencies. The code-review handoff is named by both 40-11 and 40-12 (`.planning/phases/40-resilient-review-sized-by-jev/40-10-PLAN.md:5–6`; `.planning/phases/40-resilient-review-sized-by-jev/40-11-PLAN.md:5–6,166–169`; `.planning/phases/40-resilient-review-sized-by-jev/40-12-PLAN.md:5–6,97–101`; `.planning/phases/40-resilient-review-sized-by-jev/40-13-PLAN.md:5–6`).
- **Coverage on paper:** All 11 acceptance lines are assigned in the closeout checklist. The five prohibitions are allocated across 40-01/02/03/06/07/09; dismissed edges do not need new tests. That is a coverage map, not proof that the intended behavior follows (`.planning/phases/40-resilient-review-sized-by-jev/40-SPEC.md:180–253`; `.planning/phases/40-resilient-review-sized-by-jev/40-13-PLAN.md:127`).
- **Coverage not yet earned:** The **R2 deadline boundary** test holds the fake beyond the deadline; it does not test a result arriving *at* the deadline. The **R4 owner-roster ordering** test uses the supplied report order as its roster, so it does not cover a replacement or jev reorder of `reviewers.json`. **R3** also has no round-log event for a failed fallback candidate: the ping only caches and excludes it. Extend the existing tests rather than adding a new framework (`.planning/phases/40-resilient-review-sized-by-jev/40-SPEC.md:211–226`; `.planning/phases/40-resilient-review-sized-by-jev/40-02-PLAN.md:132–133,173–178`; `.planning/phases/40-resilient-review-sized-by-jev/40-01-PLAN.md:122–126,168–171`).
- **Two prohibitions need stronger boundary tests.** R5’s payload test proves redaction of known secret shapes and backtick spans, not that verbatim titles/reasons cannot carry arbitrary config values or raw excerpts. And the parser trusts the summary’s severity rather than reconciling it to the report: a HIGH finding restated as MEDIUM could take the `reviewer_wrong` skip route. Test those two cases with the existing fake jev seam (`.planning/phases/40-resilient-review-sized-by-jev/40-06-PLAN.md:110–118,157–164`; `skills/ai-kit-spec-review/ai_kit_spec/secret_shapes.py:94–117`; `.planning/phases/40-resilient-review-sized-by-jev/40-SPEC.md:249–253`).
- **Owner confirmations:** Keep pool selection **PROVISIONAL** in the fixture and closeout, and record the outstanding confirmation explicitly. The caller tests cover skip/retry selection; the existing runner self-test covers renewal arithmetic. Neither is a live confirmation of pool scope (`.planning/phases/40-resilient-review-sized-by-jev/40-SPEC.md:65–77,174–178`; `.planning/phases/40-resilient-review-sized-by-jev/40-05-PLAN.md:135–140`; `skills/ai-kit-spec-review/references/cross-ai-selftest.mjs:1089–1095`).

**Verdict: Revise before execution.** Prioritize the disagreement and fold handoffs, the judge preflight and bar enforcement, and the closing gate’s isolation and evidence provenance.

**Not checked:** I did not run suites, paid lanes, or installers, and made no file changes. Live host behavior and execution timings remain unverified.

### Triage of cycle 1 (planner fix pass after the cycle)

#### Batch A (40-01, 40-02, 40-03)

40-01: HIGH failed-lane-judged-by-readable-report incorporated (D4: record_merge readable/failed/replaced rule returning judged keys, merge only judged keys, Task 2+3 tests, T-40-03 extended); MEDIUM roster-order incorporated (D3: --cwd required, role_order(cfg_resolve(migrate=False)), reversed/first-slot twins); MEDIUM unusable log objects incorporated (LANE_STATES, round_states validation, _shown_reason, --round<1 exit 2); LOW ev-6-params + HEAD_TASK1 incorporated (5 params, step-0 baseline N+14, fix(40) route); ponytail HIGH T1 incorporated; ponytail MEDIUM T2 incorporated; ponytail LOW T3 rejected (40-R3 needs a REASONS non-vacuity case, tests/test_ai_kit_spec.py:3483-3490); D14 incorporated.
40-02: HIGH guard blocks first commit incorporated (D1: ALLOWED_READERS in Task 1, test_lane_settings staged and run); HIGH deadline incorporated (D5: one _ping_one/_probe_all path, monotonic clock_fn, exact-deadline test); HIGH probe exception / rejected candidate incorporated (D5: named tuple -> real_error, candidate failed event, tests); HIGH empty input incorporated (exit 3, test); MEDIUM cache reuse incorporated (D5: no reuse after failed/replaced, checked_at newer than log's first event, empty log no reuse, tests; consequence: round 1 after Step 0.7 probes again); MEDIUM routing/migration incorporated (migrate=False, _lazy_routes, CLI judge-file test); MEDIUM Task 1 size/now/--timeout/rg-zero/ordering fixture incorporated (helper split, _positive_int, rg -q, distinct reasons, orchestrator split rule); ponytail T1 MEDIUM, T2 HIGH, T3 MEDIUM incorporated; D14 incorporated.
40-03: HIGH tracer incorporated (Task 1: --stdout-only fake quota exit 75, switch-lane at the branch point, replacement index dispatched with a key-recording fake, merge with --cwd --lane-log --round; record before the --stdout-only branch; unflagged exit-69 twin keeps the sibling report); HIGH two concurrent switches incorporated (D10: one-writer contract, test_two_failed_slots_switch_one_at_a_time, T-40-11); HIGH lane-reader guard incorporated (D1: ALLOWED_READERS["lane_switch.py"] = {"lane_fallback", "lane_usage_limit"} + planted case, test_lane_settings staged/run, six-path commit); MEDIUM round/index validation incorporated (exit 2 for round<1, index<0); MEDIUM changed lane identity incorporated (_refusal "lane changed"); MEDIUM reason-membership test incorporated (own events); MEDIUM helper split incorporated (_refusal); LOW PROVISIONAL label incorporated; ponytail T1 HIGH incorporated; ponytail T2 MEDIUM incorporated for prompt_over_window, duplicate-pure-cases part rejected (flagged_replacement adds the flag+quota gate over next_lane); config migrate=False; test count 17; D14 incorporated.

#### Batch B (40-04, 40-05, 40-06, 40-07)

40-04: HIGH --pool reaches execute-role probes incorporated (D2: review_spec(..., pool=None) keyword; ProbeSeams.role trailing after timeout_s; _probe_call passes lane_pool only for role review; _cmd_probe_quota _replace(role=args.role); dispatch_reviewer passes lane_pool(extra); Task 2 fake-runner argv tests for review dispatch/review probe and absence for execute probe and spec_with_effort exec; T-40-15); D1 lane_pool reader incorporated (lane_settings.lane_pool + TestLanePool, READERS + ALLOWED_READERS for lane_switch.py/reviewer_dispatch.py/quota.py in Task 1, replaces _flagged_pool); MEDIUM UnicodeDecodeError incorporated (ValueError catch + test); MEDIUM _read shape/golden/real-Node scope incorporated ((value, calls), literal golden list, no-real-node rule scoped to new tests); effort probe keeps no pool; D-04 truth PROVISIONAL; ponytail T1/T2 incorporated, T3 handed to 40-05 (D6); D14 incorporated.
40-05: incorporated (A4 fix pass) - HIGH CLI tracer fakes: exact --describe ({"runtimes": {}}) and --blocked-status answers, any other call recorded and raised, unexpected == [] asserted (Task 1 test_cli_reads_the_runner_line, Task 2 probe helper); HIGH placement and shape: status read inside _ping_one under the per-lane deadline via PingSeams.status_fn, result lane_switch.quota_entry (existing unavailable quota shape) through the normal replacement path, pooled rows never skipped by fresh/120 s reuse; HIGH one retry per expired pool: lane_switch.pool_status (blocked/expired/none), pool_keys, PingSeams.retry_keys = first key per pool from row order before submit (config only), stateful fake test_second_lane_of_a_renewed_pool_is_not_probed (set of probed lanes), Step 0.7 blocked_cache_entries walks the ladder with one retry per expired pool and functools.cache(reader), test_expired_pool_is_retried_by_one_lane; MEDIUM helper/order: run(...)._replace(config=...), sets/sorted only; REV-07 added; D1 guards: no reader or usage_limited literal in lane_ping.py/cli.py (rg -q acceptance), ALLOWED_READERS extension rule stated, tests.test_lane_settings in both verifies; D14 orchestrator steps; T-40-18..20 reused. Section: 40-05-PLAN.md ## Review dispositions (cycle 1).
40-06: incorporated (A3 fix pass) - HIGH merged-report bullets: D7a regex in Task 1 step 1 + test_merged_report_round_trips_through_the_parser, tracer and Task 2 run on render_merged_report output; HIGH fixer severity: D7b _match (title, then location), unmatched to owner unsent, cap-open identity by report position, SKIPPABLE, test_severity_comes_from_the_report + test_duplicate_or_unknown_titles_go_to_the_owner; HIGH payload: D7e _summary_text drop rules, payload test with path, key=value, quoted value and hex token inside the transmitted title/reason, straddle case with a space; MEDIUM Edits Applied + cwd: D7c contract truth (Status never read, tracer on Edits Applied), D7d --cwd + functools.partial(deps.run_fn, cwd=args.cwd); jev presence resolved once (Classified.jev asked/absent/not needed); rg -q no-match checks; D14 orchestrator steps; Task 1 touches six files (two are generated listings, one a one-line regex). Section: 40-06-PLAN.md ## Review dispositions (cycle 1).
40-07: incorporated (A3 fix pass) - HIGH quota selection: D8 eligible_keys (quota.resolve_ladder_pick predicate + SKIP_ROUTES), --quota-path, test_quota_excluded_lane_is_never_re_added (probe-quota cache -> real resolve-reviewers -> size-review), test_no_eligible_second_lane_says_so; HIGH payload: opaque p1..p5 tokens, reviewer item omitted below two eligible lanes, ARCHETYPES/FRAMEWORKS else other, strict_run enforces two or more criteria; MEDIUM Task 3 fixtures: SIZE_CONFIG everywhere (acceptance check), both answers supplied, count-changing invalid-pick case; MEDIUM Task 1 design: named helpers, new lists only (test_inputs_are_never_mutated), event only after the write, one trigger table row per alternative; cwd bound with functools.partial; cfg_resolve(..., migrate=False); D14 orchestrator steps; test count 23. Section: 40-07-PLAN.md ## Review dispositions (cycle 1).

#### Batch C (40-08, 40-09)

# Cycle 1 dispositions, batch C (40-08, 40-09), fix planner B

- 40-08 #1 HIGH fenced example / trailing section suppresses the finding: incorporated (Task 1 `_real_lines` + `_STOP_RE` bound; Task 2 fixtures fold_in_fence.md, fold_under_self_review.md and their test; boundary truth) per brief D9.
- 40-08 #2 HIGH multi-document identity lost: incorporated (Location `<doc path as given>, last ### Task`; `fold_finding(text, doc)`; `test_two_plans_keep_two_findings` with a reviewer HIGH at another location; T-40-43) per brief D9.
- 40-08 #3 MEDIUM logged two-lane merge untested in this wave: incorporated (Task 2 `test_logged_two_lane_merge_keeps_the_fold_finding`, with `--cwd` per brief D3).
- 40-08 #4 LOW stderr import, adapt-assertion wording, weak Task 3 pin: incorporated (import named; no-log failure line asserted exactly with stop-and-report; Task 3 pins the actual final `### Task` heading).
- 40-08 ponytail Task 1/2/3: incorporated (no second report format; tests spent on boundaries and logged merge; no adapter edit).
- C batch MEDIUM check-dogfood/SUMMARY ownership and real-Node scope: incorporated in 40-08 and 40-09 orchestrator steps per brief D14.
- C batch MEDIUM five-file budget: rejected (extra files are fixtures and generated listings; each task stays one lane).
- 40-09 #1 HIGH exit/resume branches contradict switch-first and partial merge; serialize switch-lane: incorporated (Task 2 step 5b edits the "Every nonzero exit" sentence in place; Task 2 step 5 serializes switch-lane with a re-read; Task 3 steps 1/1b edit the dispatch reference exit paragraph, resume argv `--lane-log/--round`, resume branch) per brief D10.
- 40-09 #2 HIGH disagreements bypass jev, cap, Step 5 templates: incorporated (trigger per brief D7c in lane-failure.md; SKILL.md Step 2 cap row, Step 4, Step 5 owner/fixer/skipped moved to 40-10 Task 2 for lane size; cap parse is 40-06 Task 1 per brief D7a).
- 40-09 #3 HIGH summaries-only stronger than the payload control: incorporated on the doc side (dropped token classes named); payload construction and test owned by 40-06 per brief D7e.
- 40-09 #4 HIGH ping exit 2 / fold exit 2 lack a safe branch, native-only fold, no-helper fallback: incorporated (Task 1 ping (c), Commands (4)/(5), intro; Task 2 steps 3 and 7) per brief D5, D9, D10.
- 40-09 #5 MEDIUM rejected candidate not logged, cache after failure, roster order: incorporated on the doc side; behaviour owned by 40-02 (brief D5) and 40-01 (brief D3, D4).
- 40-09 #6 MEDIUM sizing owner, cross-repo root, fold reset, contract mismatch, fallback filters: incorporated (sizing once at point 5; first-document root in intro; fold reset rule; contract-mismatch stop; unflagged and different-pool filters per lane_settings.py:133-136).
- 40-09 #7 LOW section 1/4 pointers, write-attempt wording, README: section 1 pointer incorporated (Task 3 step 7); section 4 rejected (skills/ai-kit-cross-ai/SKILL.md:203-207 stays true for the runner's caller); README rejected (README.md:34 stays true under Approved (partial)); pool write/clear wording owned by 40-04/40-05.
- Checker W1 exit-code claims: incorporated (per-route quote of skills/ai-kit-cross-ai/SKILL.md:193-207 and subprocess-quota-policy.md:66-67; switch on any nonzero exit) per brief D10.
- Checker W2 roster order: incorporated (Partial status sentence, Step 1.5 `--cwd`) per brief D3.
- Checker W3 ping drops an unreplaceable lane: incorporated (ping (b), Task 2 step 3) per brief D10.
- Checker W4 classification trigger: incorporated (lane-failure.md jev paragraph and Commands (5); SKILL.md wiring in 40-10 Task 2) per brief D7c.
- Planner A contract note (round 1 always probes; 120 s reuse only for probes this review ran): incorporated in 40-09 ping (a) and 40-11 setup.

#### Batch D (40-10, 40-11, 40-12, 40-13)

# Cycle 1 dispositions, batch D (40-10 .. 40-13), fix planner B

- 40-10 #1 HIGH a fixer skip never reaches jev: incorporated (Task 2 step B Step 4 "Classify first" on any listed skip/escalation, Edits Applied row edited in place; step A cap row with --cap-reached; TestSkillClassifyWiring) per brief D7c.
- 40-10 #2 HIGH fold handoff loses the document: incorporated (40-08 Location carries the doc path; Task 2 step 5 binds it to that plan; test checks `last ### Task`) per brief D9.
- 40-10 #3 MEDIUM diagram makes conditional steps unconditional: incorporated (Task 1 `--no-cross-ai` and `round log exists` edges, pending-lane edges kept, test_logged_path_is_conditional; edge counts replaced by branch greps).
- 40-10 #4 MEDIUM `rg -c -F "- Mechanical ..."` exits 2; fixer test misses the safety clause: incorporated (`-e` per brief D14; Task 3 test asserts both safety sentences).
- 40-10 ponytail Task 1/2/3: incorporated (no new diagram system; no third classifier authority; one row and one test).
- 40-11 #5 HIGH blocked-ping eval expects the wrong report reason: incorporated (three assertions: stdout auth, log cause=auth, report `review-second (replaced, by review-third)`) per brief D13.
- 40-11 #6 MEDIUM scenarios do not pin pre-round state: incorporated (pair, no sizing change, round-1 probe); distinct vendors rejected (the scenario names the pair directly, no vendor filter decides it).
- 40-11 #7 MEDIUM simulated responses, post-wave gate, PROVISIONAL fixture: incorporated (simulated sentences, PROVISIONAL comment in config.toml, unit/arch gate in verification and orchestrator steps) per brief D13, D14.
- 40-11 #8 LOW fixer eval misses the HIGH assertion: incorporated (Modify: skills/commit-message/SKILL.md, from plan-bad-review.md:11).
- 40-12 #9 HIGH real-HOME ping not read-only: incorporated (--cwd tmp/judge-40/ping/project with no config, quota and lane log under tmp/judge-40/ping/, real-HOME exception limited to the runner's lane probe, audit after every ping) per brief D11.
- 40-12 #10 HIGH collision scan / per-round recount: incorporated (copy_drivers.py substitution and verdict_facts.py split path enumerated and hand-edited; pool and count in round 1 only; survivors re-pinged and reassigned) per brief D11.
- 40-12 #11 HIGH closing check does not enforce the bar: incorporated (closing.sh rewritten with --gate; unmet is fatal; no-rejudge fix never turns unmet into met) per brief D11.
- 40-12 #12 MEDIUM count-one for one skill only; exactly-once third lane: incorporated (advisory_extra_<skill>.py per skill with its own ADV folder; third_lane_once.py) per brief D11.
- 40-12 REV-07 in frontmatter: incorporated.
- 40-13 #13 HIGH scratch check can hit a real CLI or its own stubs: incorporated (write_tripwire + baseline_env from tools/run_unittest_parallel.py, PATH = stubs + python3, synthetic runtime cache asserted fresh) per brief D12.
- 40-13 #14 HIGH restart reuses old reports: incorporated (reports-<candidate SHA>/, must not pre-exist) per brief D12.
- 40-13 #15 MEDIUM real-tools claim checks exit codes only: incorporated (ran >= 1 and no skip for the three real-tool modules) per brief D12.
- 40-13 #16 MEDIUM evidence printing, exact statuses, same-SHA before the live write: incorporated (evidence lines before layout: ok, exact Judged by line and exit codes 0/1/2/3, --cwd on merge-reports; HEAD == tip == candidate before the live link and before the tick) per brief D3, D12.
- D cross-plan R4 roster-order and R3 failed-candidate event coverage: owned by 40-01/40-02 per brief D3, D5 (not in this range).
- D cross-plan R5 payload and severity reconciliation: owned by 40-06 per brief D7b, D7e.

## Cycle 2 (referee-one)

### Review conditions (cycle 2)

Cycle 2 (referee-one, same drivers and batches, all 13 plans changed since cycle 1, the cycle-1 triage and the orchestrator
decisions of 2026-11-25 inlined through `c2/triage.md`): four lanes exit 0 (497-667 s), every review read in full, findings
path:line grounded. The cycle-1 fixes held in the main; the remaining HIGHs sat at handoffs (resume branch order and payload,
same-round remerge, replacement route for a lane with no route result, deadline wording, shared quota-cache reuse, check-reviewer
pool side effect, pool-status race and expired-pool retry, routing of CROSS-DOC/unheaded findings and owner items after Edits
Applied, sizing selection against the resolver, fold fence nesting and merge order, the Judged-by line on every outcome,
judge-ping isolation and later-round launch, clean-room preflight evidence).

Targeted fix pass (one, no cycle 3): orchestrator decisions E1-E14 (`tmp/p40-review/c2/fix-brief.md`) applied by five opus fix
planners; every touched plan ends with a `## Review dispositions (cycle 2)` section; the orchestrator added three handoff
edits (40-09 `size-review` gets `--source-vendor ... --cross-ai` and a nonzero-exit branch, the sizing paragraph names the
resolver's double-mode pick; 40-08 quotes the five-argument `_merge_with_lane_log`; VALIDATION row updated after the cache
reuse was deleted). Deviation recorded: 40-04 passes the pool with `review_spec(...)._replace(pool=...)` instead of a sixth
`review_spec` parameter (pylint max-args 5); D2's intent (review role only) is kept.

Open after the fix pass (severity; not fixed, owner or execution-time items):
- MEDIUM — summaries-only residual risk (E9, rejected as a plan change): reviewer and fixer titles and reasons are free-text
  model summaries; the filter drops recognizable code, path, assignment, quoted and long-hex forms, but an unquoted copied value
  inside such a summary would still reach jev. Owner decision.
- MEDIUM — 40-06/40-07: an undecodable jev reply can still escape the shared client (`jev_names.ask_items`); a change to the
  shared client is outside the SPEC's scope.
- MEDIUM — 40-07: no CLI test yet that a confident jev "one" rewrites reviewers.json and logs the reason, and the log does not
  say why the first reviewer moved; E10 edge: when the single existing row is already the resolver's second entry, a risky plan
  can stay on one lane.
- MEDIUM — 40-03: a refused switch can still run read-only route discovery; a dispatch that fails before it runs (unreadable
  prompt, bad `--timeout-tiers`) logs nothing, so the previous attempt's reason stands.
- MEDIUM — 40-10: the loop diagram still draws unconditional edges into the ping step; 40-11: the jev eval does not prove that
  a CRITICAL or HIGH finding reaches the owner; 40-12: no failure branch for an extra advisory lane; 40-13: the requirement
  checklist does not separate CLI evidence from skill behaviour.
- LOW — lane size: 40-02 Task 1 and 40-05 Task 1 are large; each plan states its split rule if a lane overruns.
- PROVISIONAL — everything about the blocked-until record (D-05), owner asked by the orchestrator.

### referee-one

#### Batch A (40-01, 40-02, 40-03)

#### 40-01

**Summary.** The first slice has the right boundary: extend one reason vocabulary, keep the legacy no-log merge unchanged, and make the logged merge preserve surviving reports. Cycle 1’s roster-order and stale-file fixes are present. The remaining blocker is that the logged merge can still approve a report that does not contain the findings of every lane it claims judged.

**Strengths**
- Reuses the existing parser and renderer. In particular, it preserves `any_source_issues`, which prevents an unparseable finding from silently turning an Issues report into an approval. This also keeps the no-log behavior separate. `.planning/phases/40-resilient-review-sized-by-jev/40-01-PLAN.md:127–131`; `skills/ai-kit-spec-review/ai_kit_spec/review_reports.py:119–145`; `skills/ai-kit-spec-review/ai_kit_spec/cli.py:976–1001`.
- The reversed-argument and first-slot replacement tests now exercise the actual config order, not a test-supplied surrogate. The 13-key lock changes in the same commit as `REASONS`; the runtime-table test checks membership, not the old count. `.planning/phases/40-resilient-review-sized-by-jev/40-01-PLAN.md:118,220–221`; `skills/ai-kit-spec-review/ai_kit_spec/role_orders.py:85–89`; `tests/test_ai_kit_spec_runtimes_table.py:774–780`.

**Concerns**
- **HIGH — A same-round remerge can drop findings but still say the lane judged.** `record_merge` correctly preserves the prior state of an omitted key. But the CLI takes the verdict’s `judged` and `none_judged` from the **whole log**, while findings come only from the **current arguments**. If lane A previously judged with a HIGH finding and a remerge supplies only lane B’s Approved report, the prescribed code can print `Judged by: lane-a, lane-b` and plain `Approved`. The new tests cover stale *files* for failed and replaced lanes, not a previously judged lane omitted from the current merge. `.planning/phases/40-resilient-review-sized-by-jev/40-01-PLAN.md:125–129,213–221`; `skills/ai-kit-spec-review/ai_kit_spec/cli.py:979–1001`. This matters at the resume handoff, where one-report and two-report merges are both possible: `skills/ai-kit-spec-review/references/cross-ai-dispatch.md:308–314,365–376`.
- **MEDIUM — The log validator still admits records the ping consumer cannot read.** A `judged` event with a valid round, key and state but no `at`, or a nonnumeric `at`, passes `round_states`. The next plan indexes and subtracts `event["at"]` before entering the protected probe worker, so one bad record can abort the whole ping. The malformed-record test never exercises that field. `.planning/phases/40-resilient-review-sized-by-jev/40-01-PLAN.md:121–125,167`; `.planning/phases/40-resilient-review-sized-by-jev/40-02-PLAN.md:137–139`.

**Suggestions**
- Preserve historical lane states, but derive the rendered current-round judged set from the reports actually admitted to this merge. Add a regression with a previously judged HIGH report omitted from a remerge; it must not produce a clean approval. Make the normal and resume callers pass every completed report. Also resolve the Task 1 call/signature mismatch: the inline call omits `deps`, while the signature requires it and 40-08 quotes the stale four-argument form. `.planning/phases/40-resilient-review-sized-by-jev/40-01-PLAN.md:129,277`; `.planning/phases/40-resilient-review-sized-by-jev/40-08-PLAN.md:121`.
- Treat an invalid timestamp as **not fresh**, without discarding otherwise useful failure evidence. Pin this with a single malformed-log-to-ping case.

**Risk assessment: HIGH.** The remerge can overstate review coverage and lose a blocking finding while returning success.

##### Ponytail findings
- **HIGH — Task 1:** The log and merge change are needed for R3/R4. Keep the existing `merge_findings` and renderer; fix the mismatch at their caller, not with a second report parser. `skills/ai-kit-spec-review/ai_kit_spec/review_reports.py:72–145`.
- **MEDIUM — Task 2:** The separate log module tests and generated registration are justified. Spend the reason-membership case on events actually emitted by `record_merge`, rather than checking hand-built fixtures that also include a deliberately invalid reason. `.planning/phases/40-resilient-review-sized-by-jev/40-01-PLAN.md:176–179`; `tools/gen_test_groups.py:72–103`; `tests/test_gate_scope.py:570–583`.
- **LOW — Task 3:** Keep the legacy twins and `_REPORT_A` pattern. Reuse one expected set and one assertion for the actual lock and its add/remove mutation checks; a second set plus independent inequality assertions does not exercise the same check. `tests/test_ai_kit_spec.py:3483–3490,3552–3560`; `.planning/phases/40-resilient-review-sized-by-jev/40-01-PLAN.md:205–215`.

#### 40-02

**Summary.** The concurrent ping slice correctly reuses the existing probe, ordered fallback policy and atomic writer. The revised plan fixes the empty-list case and gives original lanes and candidates the same worker. It is not ready to execute: the replacement builder conflicts with the prescribed row type, and the timeout and cache rules still do not provide the guarantees claimed.

**Strengths**
- The reader guard changes in the first commit that needs it, retaining a planted violation outside the allowlist. Reusing `cache_write_bytes` also avoids a second atomic writer. `.planning/phases/40-resilient-review-sized-by-jev/40-02-PLAN.md:127–132`; `tests/test_lane_settings.py:239–260,453–477`; `skills/ai-kit-spec-review/ai_kit_spec/cache.py:27–46`.
- A trailing `ProbeSeams.timeout_s` preserves current callers and reaches both launch paths. Distinct failure reasons in the out-of-order test check attribution rather than just elapsed time. `.planning/phases/40-resilient-review-sized-by-jev/40-02-PLAN.md:180–188,230`; `skills/ai-kit-spec-review/ai_kit_spec/cli.py:188–190`; `skills/ai-kit-spec-review/ai_kit_spec/quota.py:250–256`.

**Concerns**
- **HIGH — The replacement builder sets the route incorrectly in the prescribed pure tests.** `replacement_row` falls back to `"native"` when `route_fn` returns `None`, which is the default seam. `_native` then skips the candidate probe even for a custom-command row. The rejected-candidate test expects lane C to be probed and rejected, but the specified code keeps it as native. In production, the existing router classifies that shape as `custom`; lack of a route result is not evidence that the current host can run the lane natively. `.planning/phases/40-resilient-review-sized-by-jev/40-02-PLAN.md:129–138,189`; `skills/ai-kit-spec-review/ai_kit_spec/routing.py:134–150`. There is a second fixture mismatch: the exact-deadline test starts with **only** lane A, so owner order selects B, not the asserted C. `.planning/phases/40-resilient-review-sized-by-jev/40-02-PLAN.md:182,187`; `skills/ai-kit-spec-review/ai_kit_spec/lane_settings.py:133–154`.
- **HIGH — The deadline classifies a late answer but does not bound CLI exit.** `shutdown(wait=False, cancel_futures=True)` does not stop running threads, and Python waits for them at interpreter exit. The real runner’s outer deadline adds 30 seconds and its Python backstop adds another 10 before cleanup. The planned test releases its held thread in cleanup, so it proves classification, not that the CLI returns within its stated bound. `.planning/phases/40-resilient-review-sized-by-jev/40-02-PLAN.md:181,185–187,265`; `skills/ai-kit-spec-review/ai_kit_spec/runner_dispatch.py:42–43,275–282,645–670`. The provisional handoff compounds this: 40-05 puts the status read inside the worker but still gives the subsequent probe its full budget. `.planning/phases/40-resilient-review-sized-by-jev/40-04-PLAN.md:111–113`; `.planning/phases/40-resilient-review-sized-by-jev/40-05-PLAN.md:114`.
- **HIGH — A newer global cache entry does not prove this review ran the probe.** The cache is shared and keyed by lane key; another project can write the same key after this review’s sizing event. The proposed reuse check can then skip a mandatory round-1 probe. Task 3’s positive reuse test does not specify a later round, while the shared helper defaults to round 1. `.planning/phases/40-resilient-review-sized-by-jev/40-02-PLAN.md:137,182,223–228`; `skills/ai-kit-spec-review/ai_kit_spec/quota.py:31–32,290–306`; `skills/ai-kit-spec-review/ai_kit_spec/config_io.py:384–399`.
- **MEDIUM — The CLI leaves gaps in input and failure handling.** `--round 0` is accepted and can return success while emitting lane events 40-01 will discard. `_reason` also passes through any nonempty reason from `entry_reason`; the planned test checks known reasons only. And the two-blocked fixture does not say whether `_stop_text` should list the rejected candidate it just logged. `.planning/phases/40-resilient-review-sized-by-jev/40-02-PLAN.md:137–144,234`; `.planning/phases/40-resilient-review-sized-by-jev/40-01-PLAN.md:123`; `skills/ai-kit-spec-review/ai_kit_spec/quota.py:196–205`.
- **MEDIUM — Task 1 is still oversized for the unattended lane.** It stages seven files, introduces both runtime modules, and takes the full unit/arch hook for generated files. The suggested split only happens after an overrun; as written, the helper-only first commit would also need a caller or direct test to satisfy the plan’s vulture rule. `.planning/phases/40-resilient-review-sized-by-jev/40-02-PLAN.md:109–111,127–147,280–284`; `tools/run_unittest_parallel.py:226–232`; `pyproject.toml:97–102`.

**Suggestions**
- Give the pure tests explicit `custom` routes and explicit occupied slots. In production, require a real dispatchable route; do not infer `native` from a missing route. Specify the first green split before execution, with a direct selection test in the helper commit.
- Enforce the deadline at the existing supervised child boundary, with a remaining-time budget for each substep. Test **CLI completion** with a supervised fake child as well as exact result classification. Preserve the later-round no-reprobe rule when 40-05 adds pool status: its current “pooled rows always reach the worker” recipe otherwise probes a fresh judged lane when the status is `none`. `.planning/phases/40-resilient-review-sized-by-jev/40-05-PLAN.md:114`.
- Disable round-1 reuse explicitly. For later reuse, require evidence from this review’s own log; a timestamp in someone else’s cache is not that evidence. Validate the round before I/O and normalize unrecognized probe reasons to `real_error` before logging.

**Risk assessment: HIGH.** The plan as written can fail its own tests, skip a required probe, or leave a round waiting beyond the advertised timeout.

##### Ponytail findings
- **HIGH — Task 1:** Shared selection and atomic row replacement are needed. Keep `selectable_lanes` plus `lane_fallback`; don’t add a fallback routing rule that treats unknown as native. `skills/ai-kit-spec-review/ai_kit_spec/lane_settings.py:133–154`; `skills/ai-kit-spec-review/ai_kit_spec/cache.py:27–46`.
- **HIGH — Task 2:** The deadline seam is needed. Reuse the existing supervisor for child lifetime rather than asking the thread pool to enforce it. `skills/ai-kit-spec-review/ai_kit_spec/runner_dispatch.py:566–592,645–719`.
- **MEDIUM — Task 3:** Keep the judge-file CLI case, but add a conflicting global roster to that fixture. The current test empties **both** config layers; the actual judge handoff supplies a scratch `--cwd` but does not isolate the global config lookup. `.planning/phases/40-resilient-review-sized-by-jev/40-02-PLAN.md:231–232`; `.planning/phases/40-resilient-review-sized-by-jev/40-12-PLAN.md:114`; `skills/ai-kit-spec-review/ai_kit_spec/config_io.py:721–732,821–832`.

#### 40-03

**Summary.** The plan now tests the real `--stdout-only` branch, dispatches the replacement rather than manufacturing its report, and adds the required failed-then-successful resume regression. The policy tests are useful. The remaining blockers are at the CLI and caller boundaries: an expected non-switch can still run discovery, and a resumed quota stop can still bypass switch-first.

**Strengths**
- The tracer checks the real return-code contract and records which row was dispatched after the slot rewrite. The negative cases distinguish quota, capacity, crashes and the real pre-spawn refusal. `.planning/phases/40-resilient-review-sized-by-jev/40-03-PLAN.md:123–126,172–175`; `skills/ai-kit-spec-review/ai_kit_spec/cli.py:1373–1388`; `skills/ai-kit-spec-review/ai_kit_spec/prompt_guard.py:22–32`.
- The one-writer rule is written into both the CLI contract and the downstream caller. The two-slot test checks that the second switch sees the first rewrite rather than claiming the same fallback. `.planning/phases/40-resilient-review-sized-by-jev/40-03-PLAN.md:121,179`; `.planning/phases/40-resilient-review-sized-by-jev/40-09-PLAN.md:171`.

**Concerns**
- **HIGH — A resumed lane can enter another quota wait before `switch-lane` runs.** 40-09 adds the check only to the final “anything else” bullet and leaves the earlier exit-75-with-hint branch unchanged. A flagged lane can first be pending on `capacity`, then resume and return `quota` with a hint. The earlier branch schedules again, contrary to the locked “switch first on any nonzero exit” contract. 40-03’s new test exercises only a successful resume. `.planning/phases/40-resilient-review-sized-by-jev/40-03-PLAN.md:181`; `.planning/phases/40-resilient-review-sized-by-jev/40-09-PLAN.md:31,211`; `skills/ai-kit-spec-review/references/cross-ai-dispatch.md:365–376`.
- **MEDIUM — Non-switch cases still run route discovery.** Task 1 resolves all routes before `flagged_replacement` checks the reason and flag. Thus a flagged auth or configuration refusal can wait on live discovery even though the only permitted result is `not switched`. `persist=False` suppresses the cache write, not runtime inventory or subprocess calls. `.planning/phases/40-resilient-review-sized-by-jev/40-03-PLAN.md:119–123`; `skills/ai-kit-spec-review/ai_kit_spec/routing.py:265–281,353–369`.
- **MEDIUM — Some dispatch failures bypass the new logging boundary.** The plan records exceptions inside the dispatch `try`, but reading the prompt and parsing `--timeout-tiers` are above it. An unreadable prompt or bad tier token exits without the promised typed event; a resumed lane can retain the previous attempt’s reason. `.planning/phases/40-resilient-review-sized-by-jev/40-03-PLAN.md:123,175–181`; `skills/ai-kit-spec-review/ai_kit_spec/cli.py:1340–1360,1373–1388`.
- **LOW — The provisional label is only partly applied.** The adjacency backstop is labelled, but the main truth still states the different-pool rule without qualification, and other pool fixtures lack the marker. Keep the owner’s flag-and-quota decision settled and label the pool-dependent parts specifically. `.planning/phases/40-resilient-review-sized-by-jev/40-03-PLAN.md:20–23,124,165–169,179`; `.planning/phases/40-resilient-review-sized-by-jev/40-SPEC.md:65–70`.

**Suggestions**
- Put switch-first above **all** resumed nonzero-exit branches, preserving the sibling and merge-lock rules. Add one transient-to-quota resume case: replacement runs immediately, no new wait is scheduled, and the merged outcome stays partial.
- Invoke the route lookup lazily, only after the quota, flag and row-identity checks pass. Give the executor one ordered `cmd_switch_lane` recipe instead of an inline sequence plus instructions to replace part of it. Add a fake that fails the test if a refused switch reaches discovery.
- Move prompt and tier validation into the logged error path once a lane is identified. For the red-then-green proof, require the **named resume test** to fail on the expected old state, not merely a module-level `FAILED` line. `.planning/phases/40-resilient-review-sized-by-jev/40-03-PLAN.md:181,189–192`; `tools/run_unittest_parallel.py:938–945`.

**Risk assessment: HIGH.** The ordinary fake-switch path is well specified, but the real resume caller can still wait instead of switching, and the reason log can misdescribe a failed re-invocation.

##### Ponytail findings
- **MEDIUM — Task 1:** The shared row writer and production CLI tracer are needed. Reuse the lazy route lookup from 40-02 rather than discovering routes on a known refusal. Supply one complete `switch` test helper with the required flags so the isolated executor need not reconstruct shorthand invocations. `.planning/phases/40-resilient-review-sized-by-jev/40-02-PLAN.md:139`; `.planning/phases/40-resilient-review-sized-by-jev/40-03-PLAN.md:121–126,172–180`.
- **HIGH — Task 2:** Keep the successful-resume test and the flag/quota policy cases. Add the missing nonzero resume branch at the existing caller; no new scheduler or retry policy is needed. `skills/ai-kit-spec-review/references/cross-ai-dispatch.md:355–376`; `.planning/phases/40-resilient-review-sized-by-jev/40-03-PLAN.md:181`.

##### Batch coverage and sequencing

- **3 of 3 plans reviewed.** Waves 1, 2 and 3 each contain one plan. There is no same-wave overlap; the serial dependencies supply the log, selection and switch in order. The problems above are handoff **contracts**, not missing dependency edges. `.planning/phases/40-resilient-review-sized-by-jev/40-01-PLAN.md:5–6`; `.planning/phases/40-resilient-review-sized-by-jev/40-02-PLAN.md:5–6`; `.planning/phases/40-resilient-review-sized-by-jev/40-03-PLAN.md:5–6`; `.planning/phases/40-resilient-review-sized-by-jev/40-04-PLAN.md:5–6`.
- All 11 acceptance lines have a plan assignment. The non-dismissed R1–R4 edges are assigned across 40-01–05, with doc and judge handoffs in 40-09/10/12; the later plans assign the R5–R8 edges and the remaining prohibitions. I found no unassigned SPEC row in that map. Assignment is not proof: the remerge, deadline, cache provenance, pooled cadence and resumed-quota cases above still need coverage. `.planning/phases/40-resilient-review-sized-by-jev/40-VALIDATION.md:39–54`; `.planning/phases/40-resilient-review-sized-by-jev/40-SPEC.md:205–255`; `.planning/phases/40-resilient-review-sized-by-jev/40-13-PLAN.md:129`.

**Verdict: revise before execution.** This was a read-only source review. No files were changed, and no tests, make targets, or live lanes were run.

#### Batch B (40-04, 40-05, 40-06, 40-07)

#### 40-04

**Summary.** The plan adds the PROVISIONAL pool-status reader and passes `--pool` to the runner. Using the runner’s existing reader is the right boundary. The revised plan fixes the original execute-role leak in `probe-quota`, but a diagnostic caller still inherits the flag, and several task checks cannot pass as written.

**Strengths**
- Task 1 uses the runner’s validated record reader rather than parsing the state file again. It also handles undecodable child output and uses the existing process-group timeout path. `.planning/phases/40-resilient-review-sized-by-jev/40-04-PLAN.md:109–113`; `skills/ai-kit-spec-review/references/cross-ai.mjs:4072–4082,4140–4143`; `skills/ai-kit-spec-review/ai_kit_spec/detection.py:955–982`.
- Task 2 preserves the no-pool flags, makes the live review callers opt in explicitly, and pins the execute-role negative case through `probe_reviewer_quota`, not just through an execute spec constructor. `.planning/phases/40-resilient-review-sized-by-jev/40-04-PLAN.md:148–154`; `skills/ai-kit-spec-review/ai_kit_spec/quota.py:250–256`; `tests/test_runner_flags.py:44–55`.

**Concerns**
1. **HIGH — `check-reviewer` can gain pool-record side effects.** Task 2 gives `ProbeSeams` a default role of `"review"` and overrides it only in `_cmd_probe_quota`. `check-reviewer` accepts `extra` and calls the same quota probe both directly and through `probe_effort`. The effort preview stays pool-free, but its subsequent live probe does not. A diagnostic with flagged pooled `extra` can now explicitly clear the pool record on success. `.planning/phases/40-resilient-review-sized-by-jev/40-04-PLAN.md:148–154`; `skills/ai-kit-spec-review/ai_kit_spec/cli.py:1402–1418`; `skills/ai-kit-spec-review/ai_kit_spec/effort_probe.py:58–61,75–88`; `skills/ai-kit-spec-review/references/cross-ai.mjs:4133–4137,7314`.
2. **MEDIUM — The “last on argv” test checks only an intermediate flag list.** The proposed tests call `runner_flags` on a recorded spec. `build_runner_argv` appends timeouts and `--no-preamble`, and `run_runner` adds the child-PGID argument at spawn. The action implements “after the existing settings flags”; it does not implement the advertised “last on the argv.” Also, omitting `--pool` prevents *explicit* pool selection and clearing, not every record write: the runner can infer a pool from a matched row. `.planning/phases/40-resilient-review-sized-by-jev/40-04-PLAN.md:142–154,170,220`; `skills/ai-kit-spec-review/ai_kit_spec/runner_dispatch.py:275–282,645–665`; `skills/ai-kit-spec-review/references/cross-ai.mjs:4061–4067,4112–4124`.
3. **MEDIUM — The executor is left to repair the test recipe and lint contract.** Task 1 still passes `run_fn` from outside the helper where it is defined. Its literal reader recipe has seven return sites against a cap of six, while Task 2’s `review_spec` gains a sixth parameter against a cap of five. Task 1 requires four `PROVISIONAL` matches in `lane_switch.py` but prescribes only three there. Task 3’s count is also stale: 40-03 now specifies 18 tests, so the additions yield **23**, not 22. `.planning/phases/40-resilient-review-sized-by-jev/40-04-PLAN.md:109–127,148,188–201`; `.planning/phases/40-resilient-review-sized-by-jev/40-03-PLAN.md:181–189`; `pyproject.toml:70–80`.

**Suggestions**
- Make pool participation explicit at the actual review callers; add a fake-runner `check-reviewer` regression for both normal and effort checks. Assert the pool’s placement relative to existing settings and timeout flags on constructed argv, without starting Node.
- Give the missing-Node test its own fail-if-called fake. Specify the parser/spawn helper split and resolve the `review_spec` lint signature in the plan, not in the executor prompt. Replace inherited total-test counts with checks for the named new cases.

**Risk assessment: HIGH.** The process boundary is sound, but the unintended state change and the intermediate gate conflicts should be fixed before wave 4 runs.

##### Ponytail findings
- **MEDIUM — Task 1:** The thin reader is needed for D-05. Keep `bounded_run` and the `RunnerSeams` pattern; split parsing from spawning rather than adding another reader or a lint waiver. `skills/ai-kit-spec-review/ai_kit_spec/runner_dispatch.py:294–328`; `.planning/phases/40-resilient-review-sized-by-jev/40-04-PLAN.md:109–114`.
- **HIGH — Task 2:** The trailing field is sufficient for D-04; the missing work is at the existing diagnostic callers, not another flag abstraction. `skills/ai-kit-spec-review/ai_kit_spec/cli.py:1402–1418`; `skills/ai-kit-spec-review/ai_kit_spec/reviewer_dispatch.py:108–121`.
- **LOW — Task 3:** The equality boundary is needed; keep that named test and the no-record cases. The cache helper alone is not evidence of a retry—the actual consumer decides whether to probe. `.planning/phases/40-resilient-review-sized-by-jev/40-04-PLAN.md:187–201`; `skills/ai-kit-spec-review/ai_kit_spec/quota.py:290–307`.

#### 40-05

**Summary.** The plan connects the PROVISIONAL status reader to both selection paths. It correctly moves the status read into the ping worker and uses the existing unavailable-entry shape. The remaining defects are in the transitions between expired, cleared and fresh states: the implementation can spend zero or two retries where the plan promises one.

**Strengths**
- The CLI fakes now answer both `--describe` and `--blocked-status`. This reaches the intended integration path without a real node or host process. The synthetic `quota` entry also reaches the existing fallback and logging path without a second selector. `.planning/phases/40-resilient-review-sized-by-jev/40-05-PLAN.md:110–120,155–158`; `skills/ai-kit-spec-review/ai_kit_spec/runner_facts.py:30–44,54–60`; `.planning/phases/40-resilient-review-sized-by-jev/40-02-PLAN.md:128–139`.

**Concerns**
1. **HIGH — An expired pool can get no retry.** Task 2 drops only a cached *unavailable quota* entry for the first key. A fresh cached success or fresh `auth` failure survives, and `refresh_quota_cache` skips any fresh entry. Meanwhile later keys are stamped unavailable. The test seeds only cached quota failures, so it misses the case where expiry suppresses the whole pool without trying it. The same recipe sends unflagged lanes down the `none` branch, which says to delete cached quota failures; its own unflagged-cache test requires the opposite. `.planning/phases/40-resilient-review-sized-by-jev/40-05-PLAN.md:148–161`; `skills/ai-kit-spec-review/ai_kit_spec/quota.py:290–307`.
2. **HIGH — The ping retry test starts with a blocked pool, and a successful retry can release a second worker.** Task 1 uses epoch `1000.0` for `now`, but the “expired” timestamp is in 2000. Both workers therefore see a future block; the first lane cannot make the expected retry. After the clock is fixed, there is still a race: each worker reads separately, and the `retry_keys` check only applies to `expired`. If the first probe succeeds and clears the record before the second worker reads it, the second sees `none` and probes too. The renewal-only fake does not cover this. `.planning/phases/40-resilient-review-sized-by-jev/40-05-PLAN.md:114–119`; `skills/ai-kit-spec-review/references/cross-ai.mjs:4133–4137,7314`.
3. **HIGH — The pool path breaks the cadence and does not bound the work by the ping deadline.** Task 1 bypasses both fresh checks for every pooled non-native row, even if it judged last round and has no blocked record. It also checks elapsed time only after a status subprocess with its own fixed 30-second timeout and a probe with its original full budget. With `--timeout 1`, the worker can still be in the status read when the caller declares a timeout, and can then start a probe. Cancelling pending futures does not stop work already running. `.planning/phases/40-resilient-review-sized-by-jev/40-05-PLAN.md:114,193`; `.planning/phases/40-resilient-review-sized-by-jev/40-04-PLAN.md:111`; `.planning/phases/40-resilient-review-sized-by-jev/40-02-PLAN.md:179–187,224–228`; `skills/ai-kit-spec-review/ai_kit_spec/runner_dispatch.py:645–665`.
4. **MEDIUM — Two handoff checks are not executable as specified.** The execute-role fake accepts and returns a valid answer for `--blocked-status`, but its helper returns only probe keys and cache contents, so it cannot assert that no read took place. Task 1 also expects 23 total tests in `test_lane_switch.py`; the preceding plans and its own addition specify **24**. `.planning/phases/40-resilient-review-sized-by-jev/40-05-PLAN.md:133,157–162`; `.planning/phases/40-resilient-review-sized-by-jev/40-04-PLAN.md:114,188–201`; `.planning/phases/40-resilient-review-sized-by-jev/40-03-PLAN.md:189`.

**Suggestions**
- Keep one status decision per pool for a `ping-lanes` call, obtained inside the workers. Test both renewal and clearing with a fixed clock and assert exact call multiplicity, not just sets.
- Specify an early bypass for non-pooled rows, how the first expired lane bypasses the quota TTL, and how the remaining monotonic budget reaches both child calls. Add a pooled round-2 freshness test and a test proving an exhausted status read starts no probe. Make the execute fake reject any status read.

**Risk assessment: HIGH.** The current fixtures can fail before exercising the intended behavior, and the remaining defects can either hide a pool after expiry or spend quota the plan says it will not spend.

##### Ponytail findings
- **HIGH — Task 1:** The in-worker check is required by D6. Reuse `_ping_one` and `_probe_all`; give them a shared pool decision and remaining budget rather than introducing a second probe path. `.planning/phases/40-resilient-review-sized-by-jev/40-02-PLAN.md:137–139,179–187`; `.planning/phases/40-resilient-review-sized-by-jev/40-05-PLAN.md:110–120`.
- **HIGH — Task 2:** The pre-pass belongs at the existing quota-refresh boundary. Reuse the existing cache-entry shape, but pin the actual expired-pool retry against `refresh_quota_cache`, including both a fresh success and a non-quota failure. `skills/ai-kit-spec-review/ai_kit_spec/cli.py:922–934`; `skills/ai-kit-spec-review/ai_kit_spec/quota.py:217–223,290–307`.

#### 40-06

**Summary.** The merged-report tracer, report-sourced severity and reviewed-root `cwd` fix the main cycle-1 integration gaps. The plan still treats scrubbed free text as safe by construction, misses a locked severity restriction, and can lose owner items in the handoff to the fixer loop.

**Strengths**
- The tracer uses the actual merged-report renderer and an `Edits Applied` summary with a skip. The optional reviewer tag fixes the real parser/renderer mismatch, and the fake checks the subprocess working directory. `.planning/phases/40-resilient-review-sized-by-jev/40-06-PLAN.md:123–136`; `skills/ai-kit-spec-review/ai_kit_spec/review_reports.py:11–13,138–141`; `skills/ai-kit-spec-review/ai_kit_spec/skill_classify.py:121–128`.
- The plan reuses `ask_items(strict=True)` and the existing confidence threshold. Its cases for out-of-criteria choices, `needs_fallback`, failed exit and no matching report finding exercise meaningful advisory boundaries. `.planning/phases/40-resilient-review-sized-by-jev/40-06-PLAN.md:127–132,181–185`; `skills/ai-kit-spec-review/ai_kit_spec/jev_names.py:121–174`.

**Concerns**
1. **HIGH — The payload filter still forwards unmarked source or values.** The new test fixes the old placement problem, but tests only the forms the filter knows how to remove. A fixer reason containing an unquoted copied setting value such as `The access phrase is Violet Harbor` or an unmarked source fragment such as `return 7` survives. `secret_shapes.redact` preserves text outside known matches; clipping does not establish provenance. This leaves the R5 prohibition unproved and the claimed boundary false. `.planning/phases/40-resilient-review-sized-by-jev/40-06-PLAN.md:124,129–130,186`; `skills/ai-kit-spec-review/ai_kit_spec/secret_shapes.py:91–117`; `.planning/phases/40-resilient-review-sized-by-jev/40-SPEC.md:249–255`.
2. **HIGH — Routing is incomplete at the severity and Surface boundaries.** `route_for` restricts `reviewer_wrong` to MEDIUM/LOW but sends a confident `mechanical` CROSS-DOC or unheaded finding to the fixer below the cap. Amended R5 restricts the extra pass to MEDIUM/LOW as well. Separately, the actual handoff is 40-10, not 40-09: its `Edits Applied` row advances the iteration after classification, but its Surface edits only cover escalation and cap. An owner item from a skip on `Edits Applied` can disappear when the next review approves; the plan never says to surface or carry that item forward. `.planning/phases/40-resilient-review-sized-by-jev/40-06-PLAN.md:21,131,178–180`; `.planning/phases/40-resilient-review-sized-by-jev/40-SPEC.md:114–124`; `.planning/phases/40-resilient-review-sized-by-jev/40-10-PLAN.md:144–151`.
3. **MEDIUM — One jev failure still escapes both adapters.** The shared client uses `text=True` but catches only `OSError` and `SubprocessError` around the spawn. A decoding error occurs during the call, before the separate JSON parse handler. Both this adapter and 40-07 can therefore raise instead of taking the old path. The nonzero-exit test does not exercise it. `.planning/phases/40-resilient-review-sized-by-jev/40-06-PLAN.md:132–133,183`; `.planning/phases/40-resilient-review-sized-by-jev/40-07-PLAN.md:132`; `skills/ai-kit-spec-review/ai_kit_spec/jev_names.py:140–167`.
4. **MEDIUM — Task 1 is oversized for the lane and describes a non-green intermediate commit.** It asks for the full parser, adapter, CLI, fixtures and six staged paths including both generated listings. It also explicitly adds `re` and `secret_shapes` to the test module in Task 1, although the described tests first use them in Task 2. Ruff’s `F` checks cover this module before the first commit. `.planning/phases/40-resilient-review-sized-by-jev/40-06-PLAN.md:108–137,186`; `.pre-commit-config.yaml:20–25,71`; `pyproject.toml:29–48`.

**Suggestions**
- Keep D7e’s scrubbing as a backstop, not as proof a field is safe. Define what makes a summary safe to send, and keep a finding on the owner path when no safe summary can be formed. Add a recorded-payload case with unmarked copied text.
- Apply the same MEDIUM/LOW guard to both non-owner routes. Specify how 40-10 preserves owner items from mixed outcomes through a re-pass or later approval. Add a fake sequence for `Edits Applied` + owner item → next-round approval.
- Handle the decoding failure once at the shared client boundary, without adding a second client, and pin it for both callers. Keep Task 1 to the smallest complete CLI tracer, moving Task 2-only imports and coverage to the backstop commit.

**Risk assessment: HIGH.** The open issues affect what can leave the process and whether the owner learns about an unresolved disagreement. Passing the current route tests would not establish either guarantee.

##### Ponytail findings
- **HIGH — Task 1:** The adapter and merged-report round trip are needed for R5. Reuse `parse_findings` and the shared client as planned; enforce the safe-payload and fallback boundaries there rather than asking the host to infer them later. `skills/ai-kit-spec-review/ai_kit_spec/review_reports.py:44–69`; `skills/ai-kit-spec-review/ai_kit_spec/jev_names.py:140–174`; `.planning/phases/40-resilient-review-sized-by-jev/40-06-PLAN.md:123–136`.
- **MEDIUM — Task 2:** The fake is useful and already records the real request shape. Spend the next cases on decoding failure, non-MEDIUM/LOW mechanical answers, and the mixed-outcome handoff rather than more copies of happy-path `Finding` tuples. `.planning/phases/40-resilient-review-sized-by-jev/40-06-PLAN.md:176–186`; `tests/test_catalog_jev_names.py:132–146`.

#### 40-07

**Summary.** The plan keeps signal detection local and now sends counts, fixed labels and opaque tokens instead of roster data. It also fixes the quota-excluded-lane case from cycle 1. The remaining selection logic still does not match the resolver it claims to reuse, and the test for jev selecting one lane does not reach the required log.

**Strengths**
- The signal branch bypasses jev, and the request is built from local counts and allowlisted labels. The test also enforces the real ladder’s two-option minimum and checks that keys, models, commands and plan text stay out of the recorded payload. `.planning/phases/40-resilient-review-sized-by-jev/40-07-PLAN.md:126–132,224–225`; `skills/jev-fast-decision/scripts/jev_ladder.py:218–221,583–591`.
- The CLI tracer starts from real `resolve-reviewers` output and demonstrates that an unavailable quota entry is not re-added in the supplied case. Reusing the atomic rows writer and the existing append-only log avoids another persistence format. `.planning/phases/40-resilient-review-sized-by-jev/40-07-PLAN.md:133,139–141`; `.planning/phases/40-resilient-review-sized-by-jev/40-02-PLAN.md:130–132`; `skills/ai-kit-spec-review/ai_kit_spec/cache.py:27–46`.

**Concerns**
1. **HIGH — The added lane is not necessarily one `resolve-reviewers` would select.** `eligible_keys` calls the low-level picker with an empty vendor filter and the raw quota cache. The actual resolver first narrows by review purpose, uses a cross-vendor secondary when selecting a pair, and overlays routes on the quota cache so a stale failure cannot hide a native lane. A dispatchable lane tagged `purpose="execute"` can be added ahead of a valid review lane; a native second lane with a stale cache failure can be missed. The current tracer has neither case. `.planning/phases/40-resilient-review-sized-by-jev/40-07-PLAN.md:26,127–128,141`; `skills/ai-kit-spec-review/ai_kit_spec/quota.py:104–119,168–193`; `skills/ai-kit-spec-review/ai_kit_spec/cli.py:962–973`; `skills/ai-kit-spec-review/ai_kit_spec/routing.py:192–204`; `tests/test_ai_kit_spec.py:3042–3065,3090–3099`.
2. **MEDIUM — A bad sizing input can prevent the mandatory ping without a defined outcome.** `cmd_size_review` specifies an `OSError` handler, not handling for malformed reviewers JSON or undecodable plan text. The common CLI catches only `ConfigError`. The 40-09 handoff predicates ping on the sizing event’s file existing but gives no branch for `size-review` failure. A failed sizing step that creates no log can therefore fall through to dispatch without the ping, or stop without the specified review outcome. `.planning/phases/40-resilient-review-sized-by-jev/40-07-PLAN.md:133–134`; `skills/ai-kit-spec-review/ai_kit_spec/cli.py:1474–1481`; `.planning/phases/40-resilient-review-sized-by-jev/40-09-PLAN.md:168–169`.
3. **MEDIUM — The jev-one log acceptance is not exercised.** Task 1’s CLI cases cover a signal, absent jev and quota exclusion; Task 3’s confident-one case checks a returned reason, not `reviewers.json` or the round-0 event. No planned test would catch the CLI failing to write or log the jev-one decision. A confident reorder also records the final keys but not why the first key moved: the reason contains only the count answer and its confidence. `.planning/phases/40-resilient-review-sized-by-jev/40-07-PLAN.md:131–141,219–220`; `.planning/phases/40-resilient-review-sized-by-jev/40-SPEC.md:126–137`.
4. **MEDIUM — The first task still leaves boundary work for the lite executor.** It references `_clip`, which 40-06 does not create, and tells the executor to unpack `{t}`, `{f}`, `{s}`, `{c}` from an unnamed mapping step. The task combines the scanner, selector, CLI I/O, two fixtures and three CLI tests before the first commit. Task 3 then needs a temporary jev-root fixture defined as `jev_root(self)` in the prior plan but does not state where to put it so both test classes can reuse it. `.planning/phases/40-resilient-review-sized-by-jev/40-07-PLAN.md:109–145,214–217`; `.planning/phases/40-resilient-review-sized-by-jev/40-06-PLAN.md:124–134,175–177`.

**Suggestions**
- Use the resolver’s purpose narrowing and route-to-quota overlay for sizing. Make the vendor eligibility of a synthesized second slot explicit and test it against the existing resolver contract instead of silently using `skip_vendor=""`.
- Specify exact CLI outcomes for invalid inputs and sizing-log failure, and a 40-09 branch that never dispatches without the required ping. Add one confident-je v CLI tracer that checks the rewritten rows, the event and the reason for any applied reviewer pick.
- Name `_summary_text` correctly, specify the fact bindings and shared temp-fixture scope, and use the token map returned by `sizing_items` rather than rebuilding it. Keep the first task to one complete CLI tracer and move the remaining fixtures and branch tests to the later tasks.

**Risk assessment: HIGH.** The privacy shape is much stronger than in cycle 1. The selection mismatch can still admit the wrong second lane or report that none exists, and the failed-sizing handoff can bypass the next required step.

##### Ponytail findings
- **HIGH — Task 1:** The signal-plus-sizing slice is needed. The atomic writer and log are good reuse; the sizing eligibility path should also reuse the resolver’s existing policy rather than a near-copy. `skills/ai-kit-spec-review/ai_kit_spec/quota.py:104–119,168–193`; `skills/ai-kit-spec-review/ai_kit_spec/routing.py:192–204`; `.planning/phases/40-resilient-review-sized-by-jev/40-07-PLAN.md:127–133`.
- **LOW — Task 2:** The held-out fixtures and generated listings are justified. Keep the existing generator and gate; do not add mutation machinery just to prove the trigger table, and do not overstate overlap-prone regex examples as independent mutation tests. `.planning/phases/40-resilient-review-sized-by-jev/40-07-PLAN.md:180–186`; `tests/test_gate_scope.py:570–583`.
- **MEDIUM — Task 3:** The pure tests are useful for the floor and payload. Reuse `answers_run` in a CLI-level confident-one case, and test a failed shared-client call that actually reaches the error branch. `.planning/phases/40-resilient-review-sized-by-jev/40-07-PLAN.md:217–226`; `.planning/phases/40-resilient-review-sized-by-jev/40-06-PLAN.md:136`; `skills/ai-kit-spec-review/ai_kit_spec/jev_names.py:140–167`.

##### Coverage and overall verdict

- **Waves and handoffs:** Waves 4–7 each contain one plan. I found no same-wave file overlap or missing dependency edge: the serial chain supplies the earlier log, ping and switch helpers before 40-04/05, and classification before 40-07. The inaccurate 40-09 classification ownership in 40-06 is a handoff citation, not a scheduling conflict. `.planning/phases/40-resilient-review-sized-by-jev/40-04-PLAN.md:5–6`; `.planning/phases/40-resilient-review-sized-by-jev/40-05-PLAN.md:5–6`; `.planning/phases/40-resilient-review-sized-by-jev/40-06-PLAN.md:5–6,21`; `.planning/phases/40-resilient-review-sized-by-jev/40-07-PLAN.md:5–6`; `.planning/phases/40-resilient-review-sized-by-jev/40-10-PLAN.md:144–151`.
- **SPEC coverage:** The acceptance lines and non-dismissed edges have plan homes: R1 in 40-03/04/05/09; R2 in 40-02/05/09/12; R3–R4 in 40-01/02/03/09/10; R5 in 40-06/10; R6 in 40-07/09; R7 in 40-08/09/10; and R8 in 40-11/12/13. The five prohibitions are assigned, but assignment is not proof: the expiry and freshness backstops, summaries-only and advisory-fallback prohibitions, and the jev-one logged result still have the gaps above. The plan-level `<verification>` blocks in 40-05/06/07 also omit `make check-dogfood`; it is present in their orchestrator steps, so this is a gate-list mismatch, not missing execution. `.planning/phases/40-resilient-review-sized-by-jev/40-VALIDATION.md:39–54`; `.planning/phases/40-resilient-review-sized-by-jev/40-05-PLAN.md:200–212`; `.planning/phases/40-resilient-review-sized-by-jev/40-06-PLAN.md:224–236`; `.planning/phases/40-resilient-review-sized-by-jev/40-07-PLAN.md:263–275`.
- **Verification:** The unittest runner’s `=== <module>: FAILED (rc=...)` prefix is real. The concerns above are static findings about the prescribed implementations and assertions, not reports of executed failures. `tools/run_unittest_parallel.py:935–945`.

**Verdict: Revise before execution.** Prioritize the pool retry and deadline contract, the jev payload and owner-routing boundaries, and resolver parity. Keep the pool behavior **PROVISIONAL** pending owner confirmation.

No files were changed or created; no tests, make targets, live lanes or jev calls were run. Runtime timing and judge outcomes remain unverified.

#### Batch C (40-08, 40-09)

#### 40-08

##### Summary

The plan is well scoped for REV-08: a deterministic check produces a HIGH finding, the existing merger carries it into the report, and the execute adapter remains unchanged. Cycle 2 fixes ordinary fenced examples, trailing self-review sections, and document identity for distinct filenames. Three issues still block dispatch: the prescribed multi-document test cannot pass, valid nested fences can fool the checker, and the merge can discard the required fold edit while keeping its `fold-check` tag.

##### Strengths

- The CLI follows the existing `register_parsers` / `COMMANDS` pattern and feeds the existing report parser and renderer. The extra file stays out of lane validation, so it cannot turn a failed no-log review into a success. (`.planning/phases/40-resilient-review-sized-by-jev/40-08-PLAN.md:113–122`; `skills/ai-kit-spec-review/ai_kit_spec/skill_classify.py:197–220`; `skills/ai-kit-spec-review/ai_kit_spec/cli.py:976–1001`)
- Task 3 updates both demo fixtures that can reach review and leaves the execute-only fixture alone: its eval stops at the setup question. The permanent test pins the actual final heading and checks the adapter wording without a runtime cross-skill import. (`.planning/phases/40-resilient-review-sized-by-jev/40-08-PLAN.md:194–204`; `skills/ai-kit-spec-review/evals/evals.json:123–129,153–159`; `skills/ai-kit-spec-execute-superpowers/SKILL.md:108`)

##### Concerns

1. **HIGH — Task 2’s exact multi-document command cannot pass.** `--doc-paths` takes **one string**, not multiple arguments. In the prescribed call, `p2.md` and `p3.md` are treated as positional lane reports. Neither contains `=`, so the handler tries to open an empty path and returns Failure instead of the expected three findings. This blocks the unattended executor even if the implementation is correct. (`.planning/phases/40-resilient-review-sized-by-jev/40-08-PLAN.md:170`; `skills/ai-kit-spec-review/ai_kit_spec/cli.py:315–318,976–997`)
2. **HIGH — Fence toggling still lets examples count as real tasks.** `_real_lines` flips state on any triple-backtick or triple-tilde prefix. A three-backtick line inside a four-backtick Markdown fence therefore ends the fence early for the checker. A fold heading or checkbox later in that example can suppress the HIGH finding. This is not a hypothetical Markdown style: the repo already has plans with four-backtick fences containing triple-backtick code blocks. The new fixture checks only a single, matching triple-backtick pair. (`.planning/phases/40-resilient-review-sized-by-jev/40-08-PLAN.md:113–115,158–161`; `docs/superpowers/plans/2026-06-14-e1-review-spec-skill.md:119–138`)
3. **HIGH — A reviewer finding at the same location can erase the deterministic edit.** The plan appends the extra report *after* the reviewer reports. The merger keys across reports by `(severity, location)`, keeps the first finding’s text, and only adds the later reviewer tag. If a reviewer raises a different HIGH at `<doc>, last ### Task`, the output can carry `fold-check` without `Plan has no fold step` or its exact `Required:` edit. Task 2 tests a reviewer HIGH at a deliberately different location, while 40-10’s repair handoff assumes the fold text survives. (`.planning/phases/40-resilient-review-sized-by-jev/40-08-PLAN.md:121,170,268–269`; `skills/ai-kit-spec-review/ai_kit_spec/review_reports.py:87–101`; `.planning/phases/40-resilient-review-sized-by-jev/40-10-PLAN.md:152–153`)
4. **MEDIUM — A generated but unparseable finding is treated as an empty result.** `--doc` is interpolated verbatim into a single-line report field. A valid filename containing a line break can make that bullet unparseable, and `read_extra_findings` then returns `[]` even though the file is nonempty. A clean lane can consequently yield Approved. The existing subprocess path guard rejects control characters, but this check also runs on the native-only path. (`.planning/phases/40-resilient-review-sized-by-jev/40-08-PLAN.md:113–118`; `skills/ai-kit-spec-review/ai_kit_spec/review_reports.py:9–13,57–69`; `skills/ai-kit-spec-review/ai_kit_spec/prompt_guard.py:82–88`; `.planning/phases/40-resilient-review-sized-by-jev/40-09-PLAN.md:174–175`)
5. **MEDIUM — The logged test does not isolate the config it reads.** A temporary `--cwd` does not make the user layer empty. `_run` inherits the process environment, and the 40-01 logged handler resolves the global roster even with `migrate=False`. The prescribed parallel runner supplies a scratch HOME, so the named verification is isolated; the new test itself is not when run directly. Task 1 also stages six paths and triggers the full unit/arch hook. That is a scheduling risk, not evidence that it exceeds 1,800 seconds. (`.planning/phases/40-resilient-review-sized-by-jev/40-08-PLAN.md:122–123,171`; `.planning/phases/40-resilient-review-sized-by-jev/40-01-PLAN.md:129–130`; `skills/ai-kit-spec-review/ai_kit_spec/config_io.py:821–832`; `tools/run_unittest_parallel.py:226–232,438–460`)

##### Suggestions

- Pass the document set as one `--doc-paths` argument, matching the shipped caller. Add a same-location regression asserting that **both** the reviewer’s finding and the deterministic `Required:` text survive, then check that the latter reaches the correct `writing-plans` handler report. (`skills/ai-kit-spec-review/SKILL.md:426–432`; `skills/ai-kit-spec-review/references/apply-findings.md:7–22`)
- Track fence marker and opening length, and close only on a matching fence of sufficient length. Reuse the existing scanner pattern without importing the other skill. Reject report-breaking path characters before rendering, and distinguish an empty extra file from a nonempty file that fails to parse. (`skills/ai-kit-project-rules-agents/ai_kit_project_rules_agents/cli.py:23,51–64`; `skills/ai-kit-spec-review/ai_kit_spec/prompt_guard.py:82–96`)
- Give the logged test an explicit scratch `env_fn`, as 40-01 does. Keep the existing generated-listing and lint gates; put the most important parser and merge cases in the task that first ships the behavior. (`.planning/phases/40-resilient-review-sized-by-jev/40-01-PLAN.md:130`; `tests/test_gate_scope.py:570–583`)

##### Risk Assessment

**HIGH for correctness; low for runtime cost.** Both R7 backstops are assigned, and no phase prohibition is directly owned by this slice. The problem is not throughput in a solo-maintainer workflow; it is a false approval or a HIGH finding that reaches the fixer without the required edit. The named unittest command and failure marker match the runner, but the specified multi-document test would fail under that command. (`.planning/phases/40-resilient-review-sized-by-jev/40-08-PLAN.md:29–41,177–182`; `tools/run_unittest_parallel.py:884–913,939–945`)

##### Ponytail findings

- **Task 1 — HIGH:** Required by D-08. Keep the small stdlib command and existing report format. Fix the collision at the existing merge boundary; do not add a second report format or a new Markdown dependency. (`.planning/phases/40-resilient-review-sized-by-jev/40-08-PLAN.md:101–121`; `skills/ai-kit-spec-review/ai_kit_spec/review_reports.py:72–101`)
- **Task 2 — HIGH:** The edge tests are needed. Reuse the in-process `main` pattern, but spend the tests on nested fences, same-location findings, and real CLI argument shape rather than counting test methods. The current task proves distinct document locations, not the full repair handoff. (`.planning/phases/40-resilient-review-sized-by-jev/40-08-PLAN.md:158–185`; `tests/test_ai_kit_spec.py:3646–3662`)
- **Task 3 — LOW:** Both fixture edits and the wording pin are needed; an adapter edit or third fixture update is not. The downstream flagged fixture copies the active plan after this wave, so it inherits the fold task. (`.planning/phases/40-resilient-review-sized-by-jev/40-08-PLAN.md:194–204`; `.planning/phases/40-resilient-review-sized-by-jev/40-11-PLAN.md:89–95`)

#### 40-09

##### Summary

This is the host agent’s runbook, not just explanatory documentation. Cycle 2 improves the fresh-dispatch path: it keeps the existing no-log branch, stops on the documented ping and fold errors, threads log flags into resume argv, and puts partial approval before plain approval. It does not yet make the resumed path obey those same rules. Related gaps can skip the fold check, lose partial evidence, or claim that a live probe cannot migrate configuration.

##### Strengths

- The reason-table lock uses the runtime `REASONS` tuple, checks duplicates, and demonstrates drift with both an added and a removed row. It follows an existing section-scoped test pattern. (`.planning/phases/40-resilient-review-sized-by-jev/40-09-PLAN.md:133–139`; `skills/ai-kit-spec-review/ai_kit_spec/error_classifier.py:14–26`; `tests/test_cross_ai_settings_text.py:59–60`)
- The fresh path correctly adds `--cwd` to logged merge, preserves the three pinned status cells and the refusal rule, and retains evidence for partial approvals. Those are real compatibility checks, not just wording preferences. (`.planning/phases/40-resilient-review-sized-by-jev/40-09-PLAN.md:170–179,212–214`; `tests/test_ai_kit_spec_review_checklist.py:25–29`; `tests/test_quota_policy_text.py:97–107`; `skills/ai-kit-spec-review/ai_kit_spec/review_reports.py:22–28`)

##### Concerns

6. **HIGH — Resume still schedules a wait before checking for a flagged quota switch, and can skip the fold check.** Task 3 changes only the final “anything else” bullet. A resumed exit 75 with `retry_after_s=` still hits the *first* bullet and reschedules, before `switch-lane` can run. A successful final resume still goes straight to Step 1.5; the new fold check sits before that heading in Step 1. Task 1’s instruction to reset the fold file on resume has no effect if the resumed path never runs the check. The new test checks only that the pending section contains `switch-lane`, so it passes with this ordering. (`.planning/phases/40-resilient-review-sized-by-jev/40-09-PLAN.md:135,174–175,211,218`; `skills/ai-kit-spec-review/SKILL.md:308–313`; `skills/ai-kit-spec-review/references/cross-ai-dispatch.md:355–376`)
7. **HIGH — The resume payload does not restore the inputs Phase 40 adds.** Resume skips Step 0.7. The saved inputs have the old `archetype` and `framework_profile_path`, but not `QUOTA_JSON` or the per-document fold-check arguments. If a resumed round is fixed and starts another round, `ping-lanes` needs the original quota path. If the last resume is made to run the fold check as intended, it also needs those document-specific arguments. The saved `sibling_key` is likewise not refreshed by the switch instructions; a sibling replaced after that pointer was captured can be mistaken for the current slot. The successful-resume event added by 40-03 fixes log precedence, not this caller state. (`.planning/phases/40-resilient-review-sized-by-jev/40-09-PLAN.md:169–174,211`; `skills/ai-kit-spec-review/references/cross-ai-dispatch.md:315–337,355–373`; `.planning/phases/40-resilient-review-sized-by-jev/40-03-PLAN.md:181`)
8. **HIGH — Partial evidence is not required on every final outcome.** Task 3 quotes `Judged by:` only for partial approval. Its general Step 5 addition appends sizing and ping output, not the full round evidence. A mid-dispatch replacement or failed lane followed by an Issues Found handoff can be invisible to the owner; it is not a ping event. The unchanged “Single reviewer” row also says approval removes the run folder, which conflicts with the new partial outcome when only one lane survives. R4 requires Step 5 to name the lanes that judged and the reasons for the others, not only on approval. (`.planning/phases/40-resilient-review-sized-by-jev/40-09-PLAN.md:212–214,218`; `skills/ai-kit-spec-review/SKILL.md:508–525,547–551`; `.planning/phases/40-resilient-review-sized-by-jev/40-SPEC.md:103–112`)
9. **HIGH — The blanket “never migrates” promise is false for a live ping.** `migrate=False` covers Python’s roster resolution. The reused probe starts the normal runner in a scratch working directory; that avoids scanning the caller’s Git tree, but the runner still checks the caller’s user config and can migrate legacy retry settings into `config.toml`. The judge plan has a legacy preflight; this user-facing path has no equivalent. A scratch cwd alone is not a read-only guarantee. (`.planning/phases/40-resilient-review-sized-by-jev/40-09-PLAN.md:129–130`; `skills/ai-kit-spec-review/ai_kit_spec/quota.py:231–265`; `skills/ai-kit-spec-review/references/cross-ai.mjs:3769–3805,7077–7081`; `.planning/phases/40-resilient-review-sized-by-jev/40-12-PLAN.md:114`)
10. **HIGH — The summaries-only prohibition still is not enforced by construction.** The revised payload test does put forbidden *shapes* inside transmitted fields, which is an improvement. It still cannot catch ordinary, unquoted words copied verbatim from a file or a config value into a title or reason. The adapter keeps text outside its matching spans and the existing client serializes that text to jev. The doc test only proves the promise exists. This is a remaining 40-06 handoff issue, not a request to change the owner’s prohibition or add another client. (`.planning/phases/40-resilient-review-sized-by-jev/40-09-PLAN.md:134,138,285`; `.planning/phases/40-resilient-review-sized-by-jev/40-06-PLAN.md:129–132,186`; `skills/ai-kit-spec-review/ai_kit_spec/secret_shapes.py:99–114`; `skills/ai-kit-spec-review/ai_kit_spec/jev_names.py:140–153`)
11. **MEDIUM — Sizing still has two owners and no defined failure branch.** Step 0.7 says to run `size-review`, and mandatory reference point 5 also says to run it. Neither says its text is only a pointer to the other. Running both can ask jev twice and mutate an already-sized list. Conversely, a sizing error that leaves no log silently disables the ping, because the next step checks only whether the log exists. The earlier handler explicitly returns 2 on some failures before appending the event. (`.planning/phases/40-resilient-review-sized-by-jev/40-09-PLAN.md:168–169,216,288`; `skills/ai-kit-spec-review/SKILL.md:153–161`; `.planning/phases/40-resilient-review-sized-by-jev/40-07-PLAN.md:133–134`)
12. **MEDIUM — The exact-command reference cannot satisfy its own mismatch rule.** Task 1 says both “use the line the code prints” and “stop” on a mismatch. There are already concrete mismatches in the plans: `check-fold-step` does not accept `--cwd`, and the empty ping input has its own stderr line, `ai-kit-spec: no lane left: (empty reviewers file)`. The same task omits the **PROVISIONAL** label from the different-pool eligibility sentence and promises that a successful run clears the record, although the runner can report a failed clear. It also does not make the D6 once-per-pool rule explicit across Step 0.7 and later pings. (`.planning/phases/40-resilient-review-sized-by-jev/40-09-PLAN.md:125,129–137`; `.planning/phases/40-resilient-review-sized-by-jev/40-08-PLAN.md:119`; `.planning/phases/40-resilient-review-sized-by-jev/40-02-PLAN.md:143–145`; `tmp/p40-review/c1/fix-brief.md:58–64`; `skills/ai-kit-spec-review/references/cross-ai.mjs:4124–4137`)
13. **MEDIUM — The one-task prompts still leave execution choices unresolved.** Both objectives tell a blocked executor to write in the SUMMARY, but the orchestrator alone owns that file. The tasks also name bare lint targets and `git commit`; the scratch-HOME guarantee they cite applies to unittest children, not to the outer `uv run` hooks. With a cold dev environment, the lane has no prescribed offline setup or stop condition. In 40-09 specifically, Task 3 must distinguish **copying** the existing inline Python and redirections as shipped Markdown from **executing** them, which its shell rules forbid. (`.planning/phases/40-resilient-review-sized-by-jev/40-08-PLAN.md:80–82,247–251`; `.planning/phases/40-resilient-review-sized-by-jev/40-09-PLAN.md:92–94,211,267`; `Makefile:98–113`; `.pre-commit-config.yaml:20–44`; `tools/run_unittest_parallel.py:438–460`)

##### Suggestions

- Give fresh and resumed dispatches one switch-first exit procedure. On a resume, apply it **before** the hinted-75 branch, serialize the roster rewrite across wakes, and use the resulting current roster when deciding who merges. From the final-resume merge lock, run the fold check exactly once before Step 1.5. Pin these with a saved-resume case, not a command-name assertion. (`skills/ai-kit-spec-review/references/cross-ai-dispatch.md:355–376`)
- Make reference point 5 the sole sizing call. Specify what to do on every nonzero result, including how to preserve mandatory pings when advisory sizing is unavailable. Save or rederive the quota path and per-document fold inputs on resume. Add a mixed-archetype example so one document’s labels cannot be applied to every document. (`skills/ai-kit-spec-review/references/cross-ai-dispatch.md:148–196`; `skills/ai-kit-spec-review/SKILL.md:103–128`)
- Require the `Judged by:` line for **every final logged outcome** that has a merged report. Keep the existing pending notice separate. Add a fake case where a sibling fails and the surviving report contains an open finding; the handoff must show both the finding and the partial evidence. (`skills/ai-kit-spec-review/SKILL.md:500–525`; `.planning/phases/40-resilient-review-sized-by-jev/40-11-PLAN.md:97–100`)
- Distinguish a read-only Python config lookup from a live probe, and reuse the runner guide’s preflight before the first call that can migrate retry settings. For jev, add a fail-closed check or owner path for summaries whose content cannot be safely sent; do not treat the wording pin as proof of payload safety. (`skills/ai-kit-cross-ai/SKILL.md:106–117`; `.planning/phases/40-resilient-review-sized-by-jev/40-SPEC.md:251–255`)
- Resolve command mismatches in the plan rather than asking the executor to reconcile them. Have the executor report blockers in its final response, and make the orchestrator provide the pre-provisioned offline lint/hook environment. (`tmp/p40-review/c1/fix-brief.md:94–107,130–133`)

##### Risk Assessment

**HIGH.** The normal path is substantially clearer, but a real resume can still wait instead of switching, or approve without the fold check. The text tests can pass while both behaviors remain broken. The three tasks are serial and have quoted anchors; the seven-file plan exceeds the rough five-file target, but its generated files and full-hook cost are execution risks, not proof of a timeout. (`.planning/phases/40-resilient-review-sized-by-jev/40-09-PLAN.md:7–14,159–179,210–222`; `tools/run_unittest_parallel.py:226–232`)

##### Ponytail findings

- **Task 1 — MEDIUM:** D-01 and D-09 require the reference and lock. Reuse the existing reason-table test pattern; keep one authoritative command example per operation. The test should verify the table it claims to lock, not independently hardcode the count in addition to equality and duplicate checks. (`tests/test_cross_ai_settings_text.py:59–60`; `.planning/phases/40-resilient-review-sized-by-jev/40-09-PLAN.md:129–139`)
- **Task 2 — HIGH:** The dispatch wiring is necessary. Reuse the existing Step 1.5 report binding and Step 2 table, but keep one owner for sizing and one shared route into fold-check-and-merge. An extra pointer that leaves a second imperative is not a shortcut. (`skills/ai-kit-spec-review/SKILL.md:423–464`; `.planning/phases/40-resilient-review-sized-by-jev/40-09-PLAN.md:168–176,216`)
- **Task 3 — HIGH:** The resume changes, partial evidence, and caller exception are necessary. Extend the existing resume JSON, running marker, and merge lock rather than adding a new state file or editing the runner template. The current edits reach the saved argv but not the earlier wait branch, the final-resume fold check, or all Step 5 outcomes. (`skills/ai-kit-spec-review/references/cross-ai-dispatch.md:315–337,355–376`; `.planning/phases/40-resilient-review-sized-by-jev/40-09-PLAN.md:210–218`)

##### Batch coverage and dependencies

**No same-wave overlaps or missing dependency edges.** Waves 8 and 9 each contain one plan. The serial chain supplies 40-08 with 40-01’s merge helper and 40-06’s tagged-bullet parser, and supplies 40-09 with the earlier CLI commands. The 40-10 docs, 40-11 evals, and 40-13 layout check consume those outputs later. The remaining problems are in the contracts passed between waves, not the wave order. (`.planning/phases/40-resilient-review-sized-by-jev/40-08-PLAN.md:5–6,121`; `.planning/phases/40-resilient-review-sized-by-jev/40-09-PLAN.md:5–6`; `.planning/phases/40-resilient-review-sized-by-jev/40-10-PLAN.md:5–6,148–153`; `.planning/phases/40-resilient-review-sized-by-jev/40-11-PLAN.md:89–100`; `.planning/phases/40-resilient-review-sized-by-jev/40-13-PLAN.md:82–97`)

**The SPEC rows are assigned, but some assigned checks do not prove the user-visible behavior.** The phase verification map assigns R1–R8, the resolved edges have plan homes, and all five prohibitions have named checks. I found no unassigned row in this batch. I would not count the resumed switch-first and fold-repair paths, the partial Issues Found handoff, or the summaries-only prohibition as covered by the planned evidence. Also keep the 40-10 diagram aligned with 40-09: its revised start distinguishes native-only review, but its next-iteration edges unconditionally route that same review through ping. (`.planning/phases/40-resilient-review-sized-by-jev/40-VALIDATION.md:39–53`; `.planning/phases/40-resilient-review-sized-by-jev/40-SPEC.md:205–255`; `.planning/phases/40-resilient-review-sized-by-jev/40-10-PLAN.md:110–116`)

**Verdict: revise both plans before dispatch.** Fix the fold parser and merge test first, then make fresh and resumed reviews follow the same exit, fold, and reporting rules.

Static, read-only review: no files changed, no suites or live lanes ran, and executor timing was not measured.

#### Batch D (40-10, 40-11, 40-12, 40-13)

#### 40-10

**Summary.** This plan is where the REV-02 classifier becomes part of the actual review loop. The cycle-1 revision now invokes it on mixed edit-and-skip summaries and at the cap. But it specifies when to call the classifier more clearly than what to do with its answer. A valid Fix Summary can still lead to a lost owner decision, an unintended second edit, or an unnecessary escalation.

**Strengths**
- Task 2 edits the existing Step 2 action cell and preserves the status spelling the checklist test pins. The `rg -e` fix for the leading-hyphen pattern is also correct. (`.planning/phases/40-resilient-review-sized-by-jev/40-10-PLAN.md:144,161`; `tests/test_ai_kit_spec_review_checklist.py:25–29,162–168`)
- The fold note now carries document identity into the existing `writing-plans` route rather than adding an unrelated rule to the generic fixer. The profile and handler already support this handoff. (`.planning/phases/40-resilient-review-sized-by-jev/40-10-PLAN.md:152`; `skills/ai-kit-spec-review/references/apply-findings.md:17–22,69–83`; `skills/ai-kit-spec-review-checklist/references/frameworks/superpowers.md:33–38`)

**Concerns**
1. **HIGH — Calling jev does not reliably change the next action.** A fixer can legitimately return `Edits Applied` with a skipped MEDIUM finding. If classification returns `owner`, the planned row still increments the iteration; only the Escalation and Cap rows know how to surface that item. A clean next review can discard it. Conversely, if `No Edits` contains only a confident `reviewer_wrong` skip, the unchanged escalation row still asks the owner to decide. The cap row also retains an unconditional `Decide manually.` (`.planning/phases/40-resilient-review-sized-by-jev/40-10-PLAN.md:144–151`; `skills/ai-kit-spec-review/SKILL.md:493–519`; `skills/ai-kit-spec-review-fixer/SKILL.md:79–91`)
2. **HIGH — The mechanical re-pass exposes findings that were not routed to it.** Task 2 passes the same direct-edit report and adds a list of titles. Task 3 says to edit those titles but never says to process *only* those findings. The fixer builds its checklist from the whole report and must address its HIGH and CRITICAL findings. A fresh fixer can therefore revisit an already addressed HIGH or edit a MEDIUM item reserved for the owner. “Only when the edit is impossible” also leaves it unclear whether an existing escalation condition still takes precedence over jev’s advice. (`.planning/phases/40-resilient-review-sized-by-jev/40-10-PLAN.md:149–151,179–180`; `skills/ai-kit-spec-review-fixer/SKILL.md:31–48,53–64`)
3. **MEDIUM — The diagram still contradicts the loop.** The native-only bypass works at Start, but all four next-iteration edges lead unconditionally to ping. `Edits Applied` still bypasses classification in the graph, and the instruction to preserve pending-lane nodes preserves none: the existing DOT file has no pending branch. The proposed tests pin the unconditional edges and check labels, not the missing paths. (`.planning/phases/40-resilient-review-sized-by-jev/40-10-PLAN.md:110–116`; `skills/ai-kit-spec-review/references/loop-diagram.md:30–67`; `skills/ai-kit-spec-review/SKILL.md:457–464`; `.planning/phases/40-resilient-review-sized-by-jev/40-09-PLAN.md:168–169`)
4. **MEDIUM — The fold handoff still has a same-location collision.** The document path fixes collisions *between plans*. It does not fix a reviewer HIGH at the exact same location as the fold HIGH. The dependency appends the fold report after the reviewer reports, and the existing merge keeps the first finding’s `Required:` text for the same severity and location. The new doc test cannot verify the promised edit survives that merge. (`.planning/phases/40-resilient-review-sized-by-jev/40-10-PLAN.md:152–153`; `.planning/phases/40-resilient-review-sized-by-jev/40-08-PLAN.md:121,170–171`; `skills/ai-kit-spec-review/ai_kit_spec/review_reports.py:87–101`)

**Suggestions**
- Specify one Step 4 action table that combines the fixer status and classification result. Say what happens to first-pass `owner` and `skipped` items after a re-pass or re-review; only unresolved owner items should ask for a decision. Pin mixed `Edits Applied` plus skip, skipped-only, and a mixed owner/mechanical re-pass.
- Reuse the existing handler-report split to pass only the eligible mechanical findings to the fresh fixer. Leave the existing escalation rules in force. Add a branch-level check rather than more substring checks.
- Put the round-log condition on the diagram’s shared dispatch path, draw the pending wait explicitly, and test that the fold `Required:` text survives a same-location merge.

**Risk assessment: HIGH.** These Markdown instructions are executable control flow for the host agent. The current plan can lose an owner decision or cause an edit that the advisory classifier did not authorize.

##### Ponytail findings
- **MEDIUM — Task 1:** D-09 needs the existing DOT companion, not a second account of the loop. Reuse its shared return to Step 1 and put the log check there once. (`skills/ai-kit-spec-review/references/loop-diagram.md:3–9,45–61`)
- **HIGH — Task 2:** The classifier hook is needed; a new classifier or report format is not. Reuse the command contract from 40-09 and the existing per-handler report. The six planned files are slightly over the sizing guideline, but Task 2’s incomplete branching instructions are the bigger risk for the unattended executor. (`.planning/phases/40-resilient-review-sized-by-jev/40-10-PLAN.md:7–13,134–157`; `.planning/phases/40-resilient-review-sized-by-jev/40-09-PLAN.md:135`; `skills/ai-kit-spec-review/references/apply-findings.md:22`)
- **MEDIUM — Task 3:** One row and one test are enough if the caller supplies the scoped report and the row explicitly preserves the existing escalation rules. Reuse `TestRules` and keep the Fix Summary contract unchanged. (`tests/test_ai_kit_spec_review_fixer.py:78–98`; `skills/ai-kit-spec-review-fixer/SKILL.md:53–91`)

#### 40-11

**Summary.** The plan budgets two small tasks for the four required reviewer evals and one fixer eval. The revised ping case distinguishes stdout, log cause and rendered reason correctly. The remaining gap is in the simulated inputs: several expected outcomes still depend on facts the prompt never supplies.

**Strengths**
- The blocked-ping eval now distinguishes `auth` on stdout and in the event’s `cause` from `replaced` in the report. The fixture marks its pooled behavior PROVISIONAL and uses placeholder models. (`.planning/phases/40-resilient-review-sized-by-jev/40-11-PLAN.md:94,98`; `.planning/phases/40-resilient-review-sized-by-jev/40-01-PLAN.md:125–126`)
- The fixer eval reuses inputs with a real MEDIUM edit and a separate HIGH edit. The latter’s expected replacement matches the fixture exactly. (`.planning/phases/40-resilient-review-sized-by-jev/40-11-PLAN.md:126`; `skills/ai-kit-spec-review-fixer/evals/files/plan-bad-review.md:9–17`)

**Concerns**
1. **MEDIUM — The lane evals pin the chosen pair, not the outcomes needed to reach their assertions.** The quota-switch and partial-approval cases do not say that both pings pass. The blocked-ping case does not say that the replacement’s own ping passes. The shared setup also never says that the PROVISIONAL pool has no active block; the planned worker can bypass the probe if it does. All three scenarios can follow the skill correctly and miss the expected branch. (`.planning/phases/40-resilient-review-sized-by-jev/40-11-PLAN.md:96–99`; `.planning/phases/40-resilient-review-sized-by-jev/40-02-PLAN.md:137–138`; `.planning/phases/40-resilient-review-sized-by-jev/40-05-PLAN.md:112–119`)
2. **MEDIUM — The jev eval does not prove serious findings reach the owner or that the re-pass terminates correctly.** The prompt supplies only MEDIUM and LOW, with no iteration number, matching report titles, or second-pass result. The assertion about CRITICAL/HIGH can pass without exercising that rule. In the real classifier contract, an unmatched summary item goes straight to the owner, and `mechanical` routes to the fixer only with an explicit iteration below the cap. The shape checks cannot catch any of this. (`.planning/phases/40-resilient-review-sized-by-jev/40-11-PLAN.md:100,104–105`; `.planning/phases/40-resilient-review-sized-by-jev/40-06-PLAN.md:127–134`; `tests/test_skill_evals_shape.py:1–5,41–67`)

**Suggestions**
- Make each simulation a complete short sequence: no pool block, exact ping outcomes including the candidate, dispatch outcome, and clean surviving report where approval is expected.
- Set the disagreement case below the cap, name the findings and their exact matching summary titles, and give the re-pass a result. Include a HIGH sent to `owner` despite a confident contrary answer, or remove that assertion from this eval and cite the dedicated fake-jev test. Put the fixer’s `Mechanical re-pass:` input on its own literal line.

**Risk assessment: MEDIUM.** These defects weaken the judge’s evidence, not the runtime directly. The two tasks fit the stated executor size, and their checks are appropriate for shape, not behavior.

##### Ponytail findings
- **MEDIUM — Task 1:** The four evals are required by R8. Reuse the current `Setup: copy …` pattern and fixture-shape checks; tighten the inputs rather than adding an eval harness or changing vendors merely to satisfy a simulated case. (`skills/ai-kit-spec-review/evals/evals.json:29–36`; `tests/test_spec_chain_text.py:492–501`)
- **LOW — Task 2:** The extra eval is justified by the one new fixer rule. Keep the existing two inputs and the HIGH assertion; no new fixture or parser is needed. (`skills/ai-kit-spec-review-fixer/evals/files/plan-bad-review.md:9–17`; `tests/test_skill_evals_shape.py:53–65`)

#### 40-12

**Summary.** The judge plan correctly keeps paid dispatch and live-host access with the orchestrator. It now makes an unmet bar fatal, separates the third verdict from any count-one advisory verdict, and keeps pool and count records stable across rounds. The live ping boundary and later-round handoff still need correction before spending quota.

**Strengths**
- The judged set is based on the actual `SKILL.md` diff, and the inherited driver stops on unexpected or unregistered skills. An unchanged checklist does not get a new verdict. (`.planning/phases/40-resilient-review-sized-by-jev/40-12-PLAN.md:112–113`; `tmp/judge-39.2/judged.py:34–62,95–114`)
- `--gate` really does make an unmet bar fail, and the new exactly-one check tests verdict presence rather than inferring it from a finding count. The plan also distinguishes transcript-assessed evals from executed tests. (`.planning/phases/40-resilient-review-sized-by-jev/40-12-PLAN.md:111,141,148–155`; `tools/judge_loop.py:1376–1389,1957–1962`; `tmp/judge-39.2/findings.py:43–69`)

**Concerns**
1. **HIGH — A config-less cwd does not isolate the referee ping from the real roster.** The plan invokes `ping-lanes` with the caller’s real HOME. `cfg_resolve(..., migrate=False)` still combines an empty project layer with the user layer; that setting suppresses migration, not reading. A user config with a matching referee key can enter the normal replacement path. A malformed user config can stop the ping entirely. The mtime audit does not detect either read. The runner also inherits the XDG state directory, so the quota JSON and lane log are not the only possible writes. (`.planning/phases/40-resilient-review-sized-by-jev/40-12-PLAN.md:77,114,176–177`; `.planning/phases/40-resilient-review-sized-by-jev/40-02-PLAN.md:129,139`; `skills/ai-kit-spec-review/ai_kit_spec/config_io.py:721–732,821–838`; `skills/ai-kit-spec-review/references/cross-ai.mjs:3985–3989,4009–4012`)
2. **HIGH — Later rounds log ping failures, then launch from the unchanged pool anyway.** Even if ping removes `referee-two` from `referees-r2.json`, `lanes.py assign` reads only the saved pool and counts. The round-1 tool probe can adjudicate a failed ping; the plan explicitly skips that probe in later rounds without giving a new rule for a failed ping. The earlier round’s recent success can also satisfy ping from the shared 120-second cache. The ledger proves the command was invoked, not that the actual round’s lanes were freshly checked or admitted by it. (`.planning/phases/40-resilient-review-sized-by-jev/40-12-PLAN.md:114–116,141`; `tmp/judge-39.2/lanes.py:391–415`; `.planning/phases/40-resilient-review-sized-by-jev/40-02-PLAN.md:137–139`)
3. **MEDIUM — The extra-advisory driver is scoped per skill, but not to surviving skills.** Step 6 says to launch every copy created in step 5. Those copies hardcode a singleton `SKILLS` and use round-keyed done files. If a count-one skill was fixed and retired in round 1 while another skill continues, its extra driver can judge it again in round 2. Also, `wait` prints `advisory ended` when the process stops, whether it emitted a valid verdict or failed; there is no explicit failure branch before including its findings count. (`.planning/phases/40-resilient-review-sized-by-jev/40-12-PLAN.md:114–116,141`; `tmp/judge-39.2/advisory_extra.py:46–57,194–226,230–256`)
4. **LOW — The copy recipe contains a check whose premise is false.** The `39.2` substitution matches the string in `"tmp" / "judge-39.2"`; splitting the Python path does not split the text `39.2`. The expected old text will already be gone if the driver was copied as instructed. The runbook says to stop rather than improvise if an exact edit cannot be made. (`.planning/phases/40-resilient-review-sized-by-jev/40-12-PLAN.md:110–111`; `tmp/judge-39.2/copy_drivers.py:23–35`; `tmp/judge-39.2/verdict_facts.py:13–16`)

**Suggestions**
- Give the referee ping an explicit config and state boundary. Verify both the Python resolver and runner environment against it; do not cite an empty cwd or mtime checks as proof that config cannot be read. Keep the authorized host access separate and explicit.
- Keep the committed pool/count frozen, but state how each new ping governs launch. For a failed selected pool referee, stop with the named owner decision rather than dispatching from stale evidence; apply the locked third-lane rule separately. Select extra-advisory drivers from the round’s `skills.txt` and check for a validated verdict or a recorded failure before counting.
- Check the resulting split path, not the presence of the old text. Rehearse round 2 and a failed extra advisory with fake records before any paid call. Scope the closing `--gate` to `skills.r1.txt`: without `--skills`, the tool gates the entire registry, not just Phase 40 (`tools/judge_loop.py:1461–1475`).

**Risk assessment: HIGH.** The plan can consult unintended real configuration and then dispatch a judge that failed its pre-round check. Both faults can survive a green record-shape check.

##### Ponytail findings
- **HIGH — Task 1:** REV-07 needs the ping and JDG-04 needs the frozen-tree judge run. Keep `lanes.py assign` and the supported judge commands; fix the boundary and the launch decision, not `tools/judge_loop.py`. (`tmp/judge-39.2/lanes.py:379–426`; `tools/judge_loop.py:1974–1998`)
- **MEDIUM — Task 2:** Reuse `publish.py`, `check.py` and `decide.py`. Pass the validated-plus-extra count to the existing decision function and check only the phase’s bar at the final gate. No new record scheme or count override is needed. (`tmp/judge-39.2/publish.py:20–32,51–76`; `tmp/judge-39.2/check.py:34–52`; `tmp/judge-39.2/decide.py:10–15`)

#### 40-13

**Summary.** The closeout sequence is sound: linked-layout smoke check, suites, dry run, live link check, then ROADMAP. Candidate-specific module reports and the same-SHA check before live writes address the major cycle-1 concerns. The plan still overstates two pieces of evidence: what the layout test prints and which host test backs the clean-room exception.

**Strengths**
- The scratch check reuses the test runner’s tripwire and baseline environment, and then narrows PATH further. It checks actual command output and exit codes for both a partial merge and the empty-lane refusal. (`.planning/phases/40-resilient-review-sized-by-jev/40-13-PLAN.md:89–97`; `tools/run_unittest_parallel.py:363–388,438–462`)
- The pre-write SHA comparison and the link-only helper preserve the ship order. The helper inspects all target entries before adding any link and refuses unexpected destinations. (`.planning/phases/40-resilient-review-sized-by-jev/40-13-PLAN.md:148–161,193–194`; `tmp/run-2026-11-23/p39.2-10/live_links.py:14–42`; `AGENTS.md:347–352`)

**Concerns**
1. **HIGH — The clean-room preflight exception is not backed by evidence for the preflight it inherits.** The 39.2 exception names `tests.test_ai_kit_gsd_spec_discuss_e2e.TestRealBranchPreflight`. This plan requires no skips in three *other* modules and records every other skip as allowed. If the branch-preflight module skips, the gate can still claim the skipped clean-room case ran on the host. The image does not install Node, so this is a real evidence gap, not just a wording problem. (`.planning/phases/40-resilient-review-sized-by-jev/40-13-PLAN.md:124–129`; `.planning/phases/39.2-spec-discuss-branch-strategy-for-stacked-units/39.2-10-PLAN.md:117–118`; `tests/test_ai_kit_gsd_spec_discuss_e2e.py:78–84`; `tests/e2e/docker/Dockerfile:10–14`)
2. **MEDIUM — The layout check can pass its assertions but fail its own evidence contract.** Task 1 asks for each command’s first stdout line. `merge-reports` starts with `## Review: …`, not the status, and the empty-list ping’s reason is on stderr. Some successful checks deliberately have no stdout. The plan also requires evidence of an empty tripwire log, but tells the script only to assert emptiness before deleting the layout. Unless the implementer adds unspecified output, the saved evidence cannot prove all the stated acceptance conditions. (`.planning/phases/40-resilient-review-sized-by-jev/40-13-PLAN.md:90–106`; `skills/ai-kit-spec-review/ai_kit_spec/review_reports.py:129–145`; `tools/run_unittest_parallel.py:370–377`)
3. **MEDIUM — The requirement checklist gives isolated CLI tests credit for end-to-end behavior.** Task 2 cites 40-06 for jev classification, but that adapter test cannot prove the owner saw a mixed `Edits Applied` result or that the re-pass stayed in scope. Likewise, 40-08 proves the fold finding enters a merge but not that its exact `Required:` reaches `writing-plans` when a reviewer flags the same location. The proposed layout check cannot close either gap: it classifies an empty report and merges a fold finding against an approval. (`.planning/phases/40-resilient-review-sized-by-jev/40-13-PLAN.md:91,95,129`; `.planning/phases/40-resilient-review-sized-by-jev/40-06-PLAN.md:130–136`; `.planning/phases/40-resilient-review-sized-by-jev/40-08-PLAN.md:170–171`)

**Suggestions**
- Keep the single candidate `make test` run. Require host execution evidence for `TestRealBranchPreflight` as well, using the inherited skip check against the candidate-specific reports. Record each clean-room skip as a skip.
- Pin the precise evidence rows: matched report status and `Judged by:` line, stderr reason for exit 3, an explicit marker for empty stdout, and `tripwire calls: 0` before cleanup. Use the snapshot shape in `tests/test_ai_kit_spec_routing.py:47–50,71–76` rather than making the orchestrator hunt for a working cache fixture.
- Separate CLI, skill-routing, and judge evidence in the checklist. Keep the RDG/JDG bar and the PROVISIONAL pool caveat visible; do not promote transcript predictions to executed proof.

**Risk assessment: HIGH.** The principal risk is closing the phase with a claim the evidence does not establish. The same-SHA and link-only safeguards materially reduce the real-HOME write risk.

##### Ponytail findings
- **LOW — Task 1:** The installed-entry-point check is justified. Reuse `baseline_env` and `write_tripwire`; keep this a smoke check, not another suite. The existing runner already proves what a non-empty tripwire log means. (`tools/run_unittest_parallel.py:370–409,438–462`)
- **MEDIUM — Task 2:** The aggregate suite and one installer dry run are needed. Reuse the existing evidence reader, including its real-preflight skip check, instead of adding another run or accepting an unrelated green module as proof. (`Makefile:67–89`; `tmp/run-2026-11-23/p39.2-10/evidence.py:7–9,21–49`; `tmp/run-2026-11-23/p39.2-10/dryrun.py:28–64`)
- **LOW — Task 3:** The roadmap-only commit is the right scope. Keep it behind the digest and live-check gates; no new installer path or workflow hook is needed. (`.planning/ROADMAP.md:132`; `AGENTS.md:347–352`; `.planning/phases/40-resilient-review-sized-by-jev/40-13-PLAN.md:145–161`)

##### Cross-plan coverage and verdict

- **Coverage:** Reviewed **4/4** manifest plans. No same-wave file overlap: waves 10–13 each contain one plan. The serial chain `40-09 → 40-10 → 40-11 → 40-12 → 40-13` covers the named handoffs, including the fold fixture from 40-08 and the classifier contract from 40-06. (`.planning/phases/40-resilient-review-sized-by-jev/40-08-PLAN.md:200–203`; `.planning/phases/40-resilient-review-sized-by-jev/40-10-PLAN.md:5–6`; `.planning/phases/40-resilient-review-sized-by-jev/40-11-PLAN.md:5–6,95,170`; `.planning/phases/40-resilient-review-sized-by-jev/40-12-PLAN.md:5–6,100`; `.planning/phases/40-resilient-review-sized-by-jev/40-13-PLAN.md:5–6`)
- **Acceptance and prohibitions:** The earlier plans assign the non-dismissed SPEC edge rows and all five prohibitions to checks; 40-13 maps all eleven acceptance lines to evidence. The gaps are in what that evidence proves: actual judge admission after a failed ping (R2), owner-visible classification and a scoped re-pass (R5), and the fold handoff when findings collide (R7). The cycle-1 resume-supersede item is no longer missing from the plan: 40-03 now specifies the `chosen` event and a red-then-green check. (`.planning/phases/40-resilient-review-sized-by-jev/40-SPEC.md:184–199,205–255`; `.planning/phases/40-resilient-review-sized-by-jev/40-13-PLAN.md:129`; `.planning/phases/40-resilient-review-sized-by-jev/40-03-PLAN.md:181`)
- **Verdict: revise before dispatch.** Fix 40-10’s owner and fixer routing first, make 40-12’s ping boundary and launch decision explicit, then make 40-13 certify only evidence it actually captures.

Read-only review: no files changed, and no suites, live judges, or installer steps were run. The blocked-until pool behavior remains **PROVISIONAL**.

### Triage of cycle 2 (planner fix pass after the cycle)

#### Batch A (40-01, 40-02, 40-03)

# Cycle-2 dispositions, Batch A (40-01, 40-02, 40-03)

- 40-01 HIGH same-round remerge lists a judged lane whose report is omitted: incorporated (E1) Task 1 step 4 exit 2 `merge-reports: lane <key> judged in round <N> but its report is not given` before any write; truth, record_merge text, T-40-03, artifacts; Task 3 `test_remerge_without_a_judged_lanes_report_exits_2` (N + 15).
- 40-01 MEDIUM call omits `deps`: incorporated (one-line) `_merge_with_lane_log(args, reports, failing, missing, deps)`.
- 40-01 MEDIUM judged event without numeric `at` aborts the ping: incorporated in 40-02 `_skip_status` (not fresh), pinned in `test_ttl_edges`.
- 40-01 MEDIUM ponytail Task 2 reason-membership on record_merge events: rejected, `TestRecordMerge` already asserts the exact reasons record_merge appends; not one line.
- 40-01 LOW ponytail Task 3 one expected set: rejected, SPEC 40-R3 asks for a non-vacuity case of the lock.
- 40-01 HIGH ponytail Task 1 fix at the caller: incorporated, guard in the CLI caller, merge_findings and renderer reused.
- 40-01 LOW (clarity) shared log across subTests in `test_missing_lane_reads_never_resolved_in_either_order`: incorporated, fresh log per subTest.
- 40-02 HIGH `replacement_row` reads a missing route as native; fixtures wrong: incorporated (E2) `lane_switch._route` (None -> `custom` for a command lane, else not dispatchable and excluded); rows stated; exact deadline asserts `replaced by lane-b`.
- 40-02 HIGH deadline does not bound CLI exit: incorporated (E3) truth, `_probe_all` docstring, `--timeout` help, T-40-06 (per-ping timeout to the runner plus `RUNNER_OUTER_MARGIN_S`/`_KILL_GRACE_S`/`_TERM_GRACE_S`; pool only classifies).
- 40-02 HIGH global cache entry does not prove this review probed: incorporated (E4) reuse window, its constant and `_review_start` deleted; round 1 probes all non-native lanes; later rounds skip only a lane judged in round N-1 within `QUOTA_TTL_SECONDS`; probes still written to quota.json; three reuse tests -> `test_round_one_probes_despite_a_fresh_cache_success`; count 20; negative grep.
- 40-02 HIGH ponytail Task 1 (unknown is not native) and Task 2 (supervisor owns child lifetime): incorporated with E2 and E3.
- 40-02 MEDIUM `--round 0` accepted: incorporated (one-line) `--round` type `_positive_int`.
- 40-02 MEDIUM `_reason` passes unknown reasons: incorporated (one-line) mapped to `real_error`.
- 40-02 MEDIUM `_stop_text` and the rejected candidate: incorporated (one-line) original rows only.
- 40-02 MEDIUM Task 1 oversized: open, not one line; three-task cap; orchestrator split rule stands.
- 40-02 MEDIUM ponytail Task 3 conflicting global roster in the judge-file CLI case: incorporated (one-line).
- 40-03 HIGH resumed lane can enter another quota wait before switch-lane: incorporated (E5, 40-03 part) truth "Resumed failure"; Task 2 `test_resumed_flagged_lane_failing_with_quota_switches` (capacity, then resumed quota, flagged lane switches); count 19. Doc order and order test: 40-09.
- 40-03 HIGH ponytail Task 2 resume branch at the caller: incorporated, CLI already records the resumed reason; caller text 40-09.
- 40-03 MEDIUM non-switch cases run route discovery: open, not one line (lazy lookup would move 40-02's `_lazy_routes` into lane_switch.py); read-only (`persist=False`).
- 40-03 MEDIUM prompt read and tier parse fail before the logged path: open, not one line; that exit carries no event, so the log keeps the earlier reason.
- 40-03 LOW provisional label partly applied: incorporated (one-line) main D-04 truth labels the different-pool part PROVISIONAL.
- 40-03 LOW red proof accepts any FAILED line: incorporated (one-line) acceptance requires `FAIL: test_resumed_lane_after_a_failed_attempt_is_judged`.
- 40-03 MEDIUM ponytail Task 1 lazy lookup and one switch helper: open for the lazy lookup; E2's `_route` also governs switch-lane's replacement row.

## Handoffs to other planners (not edited here)

- 40-08 quotes the stale four-argument `_merge_with_lane_log`; the signature is `(args, reports, failing, missing, deps)`.
- 40-09 callers of `merge-reports --lane-log` must pass every report already judged in the round, or handle exit 2 with `merge-reports: lane <key> judged in round <N> but its report is not given`.
- 40-09 and 40-12 text that mentions the 120-second cache reuse must drop it (E4): round 1 always probes; later rounds skip only a lane judged in round N-1 within `QUOTA_TTL_SECONDS`.
- 40-05: each worker's probe gets `min(timeout_s, remaining)` (E3), on top of 40-02's `ProbeSeams.timeout_s`.
- Checked at fix time: 40-05, 40-09 and 40-12 already drop the reuse (E4); SPEC and CONTEXT do not require it. `40-VALIDATION.md` line 45 (REV-07 R2 row) still lists `quota-cache reuse`; the orchestrator should change it to `round 1 probes despite a fresh cache entry` (outside the plan scope).

#### Batch B (40-04, 40-05, 40-06, 40-07)

# Cycle-2 dispositions, Batch B first half (40-04, 40-05)

- 40-04 HIGH check-reviewer (plain and effort) can clear a pool record: incorporated (E6) Task 2: `ProbeSeams.role` default `""`; only `probe-quota --role review` and `ping-lanes` (40-05 Task 1, `role="review"`) opt in; `test_check_reviewer_never_passes_the_pool` (CLI plain leg plus direct `probe_effort` leg); T-40-15.
- 40-04 HIGH ponytail Task 2 (fix at the diagnostic callers): incorporated (E6), same field with the default flipped.
- 40-04 MEDIUM "last on the argv" / runner pool inference: incorporated: "after every existing `runner_flags` flag"; the D-04 truth says the runner may still infer a pool from a matched row.
- 40-04 MEDIUM `run_fn` used outside `_read`: incorporated: its own fail-if-called `never` fake.
- 40-04 MEDIUM seven returns in `blocked_until`: incorporated: `_parse_status` parser helper (PROVISIONAL, gate).
- 40-04 MEDIUM `review_spec` sixth parameter vs `max-args = 5`: incorporated as a deviation from c1 D2's literal signature (intent kept): `review_spec` unchanged; the two review callers use `review_spec(...)._replace(pool=...)`; evidence pyproject.toml:75-76 and runner_dispatch.py:114-115; no other plan quotes the keyword.
- 40-04 MEDIUM PROVISIONAL count / stale 22 total: incorporated: four named docstrings; named-test gate instead of a total.
- 40-04 LOW ponytail Task 3: incorporated by 40-05 (E7 decisions, pre-pass pinned against `refresh_quota_cache`).
- 40-05 HIGH expired pool gets no retry; unflagged lanes hit `none`: incorporated (E7) Task 2: `blocked_cache_entries` on `pool_decisions`; the retry key pops ANY cached entry; only flagged pooled keys are touched; subTests for a cached quota failure, fresh success, fresh `auth`; unflagged test with cleared and expired lines.
- 40-05 HIGH fake clock epoch and second-worker race: incorporated (E7) Task 1: one epoch (`POOL_NOW`, `PAST`, `FUTURE`); one concurrent read per pool before the workers (`_read_pools`), decisions passed in as data, no read in a worker; renewal and clearing subTests with exact read and probe counts and read-before-probe order; two-pool test; prohibition reworded.
- 40-05 HIGH cadence and deadline bound: incorporated (E3, E4, E7) Task 1: decision `none` keeps `_skip_status` (no cache reuse); shared monotonic budget from before the reads; probe gets `min(timeout_s, int(remaining))`, under 1 s is `ping_timeout` with no probe; reads killed at `timeout_s` (`blocked_until`/`blocked_reader` gain `timeout_s`); bound stated as E3 words it (truth, `_ping_one` docstring, T-40-18); round-2 fresh and budget tests.
- 40-05 HIGH ponytail Task 1/Task 2: incorporated: same `_ping_one`/`_probe_all`; pre-pass pinned through `probe-quota` against `refresh_quota_cache`.
- 40-05 MEDIUM execute fake cannot show no read: incorporated: helper returns the read count, a status read with `line=None` is unexpected; execute test asserts reads 0.
- 40-05 MEDIUM stale 23 total: incorporated: named-test gates.
- 40-05 MEDIUM `<verification>` lacks `make check-dogfood`: incorporated.
- 40-05 E4 (no 120-second reuse): incorporated: no reliance on reuse; `rg -q "PING_REUSE_S"` exits 1 gate; cycle-1 row marked superseded.
- 40-05 40-02 names quoted in read_first: incorporated: the revised 40-02-PLAN.md has `_skip_status(run, row, now)`, `PING_GRACE_S = 5`, `clock_fn`, `_ping_one(row, run, seams)` and no `PING_REUSE_S`.
- 40-05 native rows reaching the worker / retry slot: incorporated: decisions built from non-native rows only.
- 40-05 two-pool concurrency proof: incorporated: `threading.Barrier(2)` in `test_two_pools_are_read_once_each_before_any_probe`.
- 40-05 Task 1 size (tracer plus eight named cases): open: explicit overrun rule (five named cases to a Task 3 with only tests/test_lane_ping.py, both gate counts stated).

# Cycle-2 dispositions, Batch B second half (40-06, 40-07)

- B/40-06 #1 payload filter forwards unmarked text | HIGH -> MEDIUM residual risk | rejected (E9): summaries only by construction (CONTEXT D-06); filter drops every recognizable code, path, assignment, quoted and long-hex form; adapter reads no file content, diff or config value; no new filter. Recorded for the owner.
- B/40-06 #2a mechanical CROSS-DOC/unheaded reaches the fixer | HIGH | incorporated (E8): one SKIPPABLE guard before the class in `route_for`; `SERIOUS` removed; CROSS-DOC/none mechanical cases in Task 2.
- B/40-06 #2b owner items lost after an Edits Applied skip | HIGH | incorporated (E8, 40-06 part): `classify-disagreements --owner-out <path>` appends each owner entry as one JSON line via `review_log.append_event`; OSError -> exit 2, empty stdout; `test_owner_items_are_appended_to_the_owner_file`. Final-Surface carry stays with 40-10.
- B/40-06 #3 decoding error escapes the shared jev client | MEDIUM | open: fix belongs in `jev_names.ask_items` (outside both plans' files) plus a test.
- B/40-06 #4 Task 1 test imports before use; Task 1 size | MEDIUM | incorporated: `re`/`secret_shapes` moved to Task 2; size kept.
- B/40-06 ponytail Task 2 | MEDIUM | incorporated except decoding (open).
- B/40-07 #1 added lane differs from the resolver's choice | HIGH | incorporated (E10): forced-double `quota.resolve_reviewers` over `routing.unroutable_quota`, same `--source-vendor`/`--cross-ai`, second entry when not already chosen; `eligible_keys` deleted; distinct test vendors; execute-purpose and native stale-cache tests.
- B/40-07 ponytail Task 1 | HIGH | incorporated: no second eligibility predicate; reviewer tokens index the candidate rows (D8 tokens and omission kept).
- E10 residual (existing row = resolver's second entry) | n/a | open for the owner: literal E10 keeps one lane.
- B/40-07 #2 bad sizing input | MEDIUM | incorporated (40-07 part: OSError/ValueError -> exit 2, no write, no event); 40-09 failure branch open.
- B/40-07 #3 jev-one CLI log, reorder reason | MEDIUM | open (new CLI test; reason text that 40-09 quotes).
- B/40-07 #4 `_clip`, fact bindings, token map, `jev_root` scope | MEDIUM | incorporated.
- B/40-07 ponytail Task 2 | LOW | no change needed.

## Cross-plan handoffs (orchestrator: relay to the owners of 40-09 and 40-10)

- 40-09 `## Commands` (1) must add `--source-vendor "<the value passed to resolve-reviewers>" --cross-ai` to the `size-review` line. Without `--cross-ai` the resolver returns only the session default and no second lane is ever added, so the signal floor never fires in the real flow.
- 40-09 `## jev classes and sizing` sizing paragraph: replace "the next lane of the review order that resolve-reviewers could also have chosen (its route dispatches and the quota file marks it available)" with "the second lane resolve-reviewers picks in double mode (same source vendor, quota and routes)", and "the reviewer among the first five keys of the review order" with "the reviewer among the candidate lanes (the current lanes, then that second lane)".
- 40-09: give a `size-review` exit 2 its own branch (stop with the stderr line; never dispatch without the ping).
- 40-10: the flag is `classify-disagreements --owner-out "$RUN_TMP_DIR/owner-items.json"`; each call appends its owner entries as JSON lines `{"title", "severity", "source", "class", "confidence"}` plus `"reason"` on noted entries; a nonzero exit means nothing was printed (today's path).

#### Batch C (40-08, 40-09)

# Cycle-2 dispositions, Batch C (40-08, 40-09)

- 40-08 #1 HIGH --doc-paths as three arguments: incorporated (E11), Task 2 test passes "p1.md p2.md p3.md" as one argument.
- 40-08 #2 HIGH fence toggle ends a four-backtick fence: incorporated (E11), Task 1 CommonMark rule (same char, run >= opening, no info string); Task 2 fixture fold_in_long_fence.md (fold lines inside the inner block, so HEAD's toggle fails it) and a tilde-in-backtick text case.
- 40-08 #3 HIGH same-location reviewer HIGH erases the fold edit: incorporated (E11), merge_findings((args.extra_findings or []) + reports) in both calls; test_same_location_reviewer_high_keeps_the_fold_edit; the reviewer's text at that one key is dropped, its tag kept.
- 40-08 #4 MEDIUM unparseable non-empty extra file reads as empty: incorporated (one-line), read_extra_findings raises ArgumentTypeError (exit 2), pinned.
- 40-08 #5 MEDIUM logged test config isolation: rejected, the named verify runs under tools/run_unittest_parallel.py with a temporary HOME and AI_KIT_REFUSE_REAL_HOME=1 (tools/run_unittest_parallel.py:438-460).
- 40-08 ponytail Task 1/2 HIGH: incorporated with #1-#3; Task 3 LOW: no change.
- 40-09 #6 HIGH resume waits before the flagged switch; final resume skips fold check: incorporated (E5), Task 3 point 5 switch-first bullet before the hinted exit-75 bullet, fold check before Step 1.5 (exit 0 and failed-lane merge), ORDER doc test with non-vacuity.
- 40-09 #7 HIGH resume payload lacks QUOTA_JSON/fold inputs; stale sibling_key: incorporated (E5), quota_json, lane_log, framework_id, doc_archetypes saved and restored; sibling re-read from current reviewers.json; failed-lane merge passes the sibling's key=path again.
- 40-09 #8 HIGH Judged by only on partial approval; Single reviewer cleanup: incorporated (E12), every Step 5 outcome quotes Judged by when a merged report exists; Single reviewer row cleans up only on clean Approved.
- 40-09 #9 HIGH "never migrates" false for live probe: incorporated (E12), sentence now "Python's config resolution in these commands never migrates; the runner's own legacy check runs as on every dispatch."
- 40-09 #10 summaries-only residual risk: rejected as a plan change, severity MEDIUM (E9): summaries by construction (CONTEXT D-06), 40-06 filter drops code/path/assignment/quoted/long-hex forms, no file content, diff or config value read.
- 40-09 #11 MEDIUM sizing failure branch: open (not a one-line edit); sizing owner already single since cycle 1.
- 40-09 #12 MEDIUM command mismatches: incorporated in part (check-fold-step excluded from --cwd sentence; empty reviewers stderr line quoted); open: PROVISIONAL label on different-pool sentence, failed-clear wording (40-04/40-05 own it).
- 40-09 #13 MEDIUM one-task prompt choices: incorporated in part (python3 -c lines are Markdown to edit, never to run); open: blocker reporting and cold lint env are orchestrator-wide (D14).
- 40-09 E4 120-second cache reuse: incorporated, removed from Task 1 ping (a) and Task 2 step 3; round 1 always probes; later rounds skip only a lane judged last round within the TTL.
- 40-09 lane-failure.md chosen supersede and --owner-out: incorporated (Partial status, Commands final paragraph, jev paragraph, Commands (5), COMMANDS pin includes --owner-out).
- 40-09 ponytail Task 1 MEDIUM count hardcode: open (kept as a drift alarm); Task 2/3 HIGH: incorporated with #6-#8.

#### Batch D (40-10, 40-11, 40-12, 40-13)

# Cycle 2 dispositions, Batch D (40-10..40-13)

- 40-10 #1 jev answer does not change the next action | HIGH | incorporated (E8): `--owner-out $RUN_TMP_DIR/owner-items.json` in Step 2 cap cell and Step 4; Step 4 branch on lists; all-`reviewer_wrong` surfaces as skipped, no Decide manually; cap asks only with owner items; every outcome lists the file; tests in TestSkillClassifyWiring
- 40-10 #2 re-pass exposes unrouted findings | HIGH | incorporated (E8): template parenthetical, apply-findings, Step 4 and fixer row say process only the listed findings, escalation conditions take precedence; Task 3 test, grep, truth, prohibition, T-40-35 changed together
- 40-10 ponytail Task 2 branching | HIGH | incorporated: Step 4 branch sentence
- 40-10 #3 diagram edges | MEDIUM | open (not one-line)
- 40-10 #4 fold same-location collision | MEDIUM | open here, owned by 40-08 (E11)
- 40-11 E8 ripple: fixer eval required a HIGH edit on a MEDIUM-only re-pass | HIGH (consistency) | incorporated: Task 2 prompt line on its own line; assertion 3 checks `Modify: TBD` stays
- 40-11 #1 ping/pool outcomes missing | MEDIUM | incorporated (one-line setup sentence)
- 40-11 #2 jev eval CRITICAL/HIGH and re-pass result | MEDIUM | open (not one-line; covered by 40-06 and 40-10 tests)
- 40-12 #1 ping not isolated from the real roster; XDG writes | HIGH | incorporated (E13): `judge-referee-*` keys, user-layer read stated as accepted, exit 2 failed ping + owner question, `state_audit.py` lists runner state writes after every ping
- 40-12 #2 later rounds launch from the unchanged pool; 120 s cache | HIGH | incorporated (E13, E4): failed later-round pool referee skips assign/launch with owner question; failed referee-three skips advisory launch and takes the substitute; every round probes all three (no judged events in the ping log, no cache reuse)
- 40-12 #3 extra advisory scope / failure branch | MEDIUM | partly incorporated (round `skills.txt` scope); failure branch open
- 40-12 #4 split-path hand edit false premise | LOW | incorporated: check instead of edit
- 40-12 closing --gate covers whole registry | MEDIUM | incorporated: `--skills` from skills.r1.txt
- 40-13 #1 clean-room exception lacks preflight host evidence | HIGH | incorporated (E14): `tests.test_ai_kit_gsd_spec_discuss_e2e` rc 0, ran >= 1, no REAL_CASE_SKIPS skip, reports from `reports-<SHA>`
- 40-13 #2 layout evidence lines | MEDIUM | incorporated (one-line)
- 40-13 #3 checklist credits CLI tests for skill behaviour | MEDIUM | open (not one-line)
