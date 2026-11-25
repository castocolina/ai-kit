---
phase: 40-resilient-review-sized-by-jev
reviewed: 2026-11-25T19:13:24Z
reviewed_head: e7dbfa2
diff_range: "7106efb..e7dbfa2 (excluding .planning)"
depth: standard (call chains traced for ping, switch, logged merge, sizing and classification)
files_reviewed: 49
files_reviewed_list:
  - .pre-commit-config.yaml
  - Makefile
  - skills/ai-kit-cross-ai/SKILL.md
  - skills/ai-kit-spec-review-fixer/SKILL.md
  - skills/ai-kit-spec-review-fixer/evals/evals.json
  - skills/ai-kit-spec-review/SKILL.md
  - skills/ai-kit-spec-review/ai_kit_spec/cli.py
  - skills/ai-kit-spec-review/ai_kit_spec/error_classifier.py
  - skills/ai-kit-spec-review/ai_kit_spec/fold_check.py
  - skills/ai-kit-spec-review/ai_kit_spec/jev_review.py
  - skills/ai-kit-spec-review/ai_kit_spec/lane_ping.py
  - skills/ai-kit-spec-review/ai_kit_spec/lane_settings.py
  - skills/ai-kit-spec-review/ai_kit_spec/lane_switch.py
  - skills/ai-kit-spec-review/ai_kit_spec/quota.py
  - skills/ai-kit-spec-review/ai_kit_spec/review_log.py
  - skills/ai-kit-spec-review/ai_kit_spec/review_reports.py
  - skills/ai-kit-spec-review/ai_kit_spec/review_signals.py
  - skills/ai-kit-spec-review/ai_kit_spec/reviewer_dispatch.py
  - skills/ai-kit-spec-review/ai_kit_spec/runner_dispatch.py
  - skills/ai-kit-spec-review/evals/evals.json
  - skills/ai-kit-spec-review/evals/files/active/project/docs/superpowers/plans/demo.md
  - skills/ai-kit-spec-review/evals/files/flagged/project/aikit/config.toml
  - skills/ai-kit-spec-review/evals/files/flagged/project/docs/superpowers/plans/demo.md
  - skills/ai-kit-spec-review/evals/files/project/docs/superpowers/plans/demo.md
  - skills/ai-kit-spec-review/references/apply-findings.md
  - skills/ai-kit-spec-review/references/cross-ai-dispatch.md
  - skills/ai-kit-spec-review/references/lane-failure.md
  - skills/ai-kit-spec-review/references/loop-diagram.md
  - tests/fixtures/fold_step/fold_in_fence.md
  - tests/fixtures/fold_step/fold_in_long_fence.md
  - tests/fixtures/fold_step/fold_under_self_review.md
  - tests/fixtures/fold_step/with_fold.md
  - tests/fixtures/fold_step/without_fold.md
  - tests/fixtures/review_signals/data_plan.md
  - tests/fixtures/review_signals/irreversible_plan.md
  - tests/fixtures/review_signals/plain_plan.md
  - tests/fixtures/review_signals/security_plan.md
  - tests/test_ai_kit_spec.py
  - tests/test_ai_kit_spec_review_fixer.py
  - tests/test_fold_check.py
  - tests/test_jev_review.py
  - tests/test_lane_failure_text.py
  - tests/test_lane_ping.py
  - tests/test_lane_settings.py
  - tests/test_lane_switch.py
  - tests/test_review_log.py
  - tests/test_review_signals.py
  - tests/test_role_orders.py
  - tests/test_runner_flags.py
findings:
  critical: 2
  warning: 5
  info: 11
  total: 18
  necessity: 1
status: issues_found
---

# Phase 40: Code Review Report

**Reviewed:** 2026-11-25T19:13:24Z
**Depth:** standard, with call chains traced for ping, switch, logged merge, sizing and classification
**Files Reviewed:** 49 (range 7106efb..e7dbfa2, `.planning/` excluded; see "Not read in full" for what was only skimmed)
**Status:** issues_found

## Summary

Phase 40 adds the round log (`review_log.py`), the pre-round ping (`lane_ping.py`), the flagged-lane
switch and blocked-until reader (`lane_switch.py`), jev classification and sizing (`jev_review.py`),
deterministic signals (`review_signals.py`), the fold-step check (`fold_check.py`), the logged merge in
`cli.py`, and the matching SKILL.md and reference text.

What holds: the new runtime modules import only the stdlib and `ai_kit_spec` (stdlib-only rule kept).
`reviewers.json` is rewritten through `cache.cache_write_bytes` (mkstemp, fsync, `os.replace`), so the
rewrite is atomic. This phase writes no runtime config file (opencode.jsonc, Codex TOML, Claude JSON,
`settings.json`). The runner's `--blocked-status` printer (`cross-ai.mjs:4048,4140-4142,7000`) emits
`blocked_until=YYYY-MM-DDTHH:MM:SSZ failures=N` as one stdout line, which matches `_STATUS_RE`
(`lane_switch.py:26-27`). A readable report from a failed or replaced lane no longer becomes `judged`.
The fixer cannot lower a severity, because severity comes from the matched report finding. The fold
check follows the CommonMark fence rule. The four R8 evals are present in `evals/evals.json`.

Two defects are blockers. (1) The deterministic two-lane floor fails in a common roster shape: the
review log then says no second lane is eligible when one is. Plan review cycle 2 left this case open
for the owner, but the false log reason is new. (2) A slow `--blocked-status` read uses up the probe
budget of every original lane. Unflagged lanes are then recorded `ping_timeout` without a probe,
replaced, and cached unavailable for an hour in the user-global quota cache. That contradicts D-05.

The warnings cover a security-signal regex that misses "authentication" and "authorization", a jev
reviewer pick that cannot do what the docs say, contradictory docs on the size-review failure path,
a cap-stop row that can drop the owner decision when classification did not run, and a hole in the
lane-reader guard. Two of these (WR-02, WR-03) are plan-review handoffs (40-REVIEWS.md:1068-1069) that
were not applied. All ten executor items are confirmed or refuted in their own section below. Every
confirmed item also has a finding ID.

Known open items from plan review cycle 2 that are not raised again here: the summaries-only residual
risk (E9, owner decision), and an undecodable jev reply escaping the shared client `jev_names.ask_items`
(outside this phase's files).

Verification: CR-01, CR-02, WR-01, WR-05 and IN-01 were reproduced with scratch scripts under
`tmp/p40-code-review/`; their outputs are quoted below. The scripts were removed after the run, so
re-running needs a new copy. No repo file other than this report was changed, and no unit-test module
was run. The necessity rubric (`.claude/gsd-core/references/necessity-review.md`) was read.

## Narrative Findings (AI reviewer)

All findings below come from direct code review. No structural pre-pass and no external reviewer
evidence was provided.

## Critical Issues

### CR-01: size-review cannot add the second lane when the single-mode pick is the double-mode secondary, and logs a false reason

**File:** `skills/ai-kit-spec-review/ai_kit_spec/jev_review.py:282-295` (used by `size_review` 344-352 and by `_apply_answers` for a jev `two`)
**Issue:** `_with_second_lane` re-runs `resolve_reviewers` in double mode, then adds only `picked[1]`, and
only when that key is not already in the rows. Single mode picks the first lane whose vendor differs
from `--source-vendor`. Double mode takes the first lane with quota as primary, then the first lane of
another vendor as secondary. When the first ladder lane shares the source vendor (a plan written on
Claude, reviewed with a Claude-first ladder), the single-mode pick is the double-mode secondary.
`picked[1]` is then already present, nothing is added, and sizing logs "signal security wants two
lanes; the roster has no second eligible lane". The double-mode primary (`lane-x`) is eligible and has
quota. SPEC R6 ("a plan with a security signal gets two lanes whatever jev says") fails. The logged
reason is also a false claim, which breaks the AGENTS.md rule that no diagnostic claims more than it
verified. A jev `two` answer hits the same path. Reproduced (scratch `verify.py`):

```
single-mode resolve: ['lane-a']
sizing: ['lane-a'] | signal security wants two lanes; the roster has no second eligible lane
```

The roster was `lane-x` (vendor-src) then `lane-a` (vendor-other), with `--source-vendor vendor-src`.
The tests (`tests/test_jev_review.py:457-501`, `TestSizeReview`) always pass `source_vendor=""`, so they
never hit this case. Plan review cycle 2 recorded the case as "E10 residual ... open for the owner:
literal E10 keeps one lane" (40-REVIEWS.md:585-586, 1059). It still ships against R6, and the log line
now states it as a fact about the roster.
**Fix:** Add the first resolver pick that is not already a row, not only `picked[1]`:
```python
present = {r["key"] for r in inputs.reviewers}
extra = next((p for p in picked if p.key not in present
              and p.key != quota.NO_CONFIG_FALLBACK.key), None)
if extra is not None:
    row = extra._asdict()
    row["route"] = inputs.routes.get(row["key"], "native")
    return [*inputs.reviewers, row]
```
Add a CLI test with `--source-vendor` equal to the first lane's vendor and a security plan. If the
owner keeps the literal E10 rule, at least change the reason to say the resolver's second lane is
already chosen, not that the roster has none.

### CR-02: A slow blocked-status read times out every original lane, unflagged ones included, and caches them unavailable for an hour

**File:** `skills/ai-kit-spec-review/ai_kit_spec/lane_ping.py:166-171` (shared `started`), `106-108` (`_budget_s`), `122-124` (`remaining < 1`), `269` (cache write)
**Issue:** When any chosen lane is flagged and pooled, `_statuses` takes `started` before
`_read_pools` and hands that one start time to every lane's `_ping_one`. Each lane's probe budget is
`timeout_s - (now - started)`. The pool read is a runner child bounded at `--timeout`
(`blocked_reader(deps, timeout_s=args.timeout)`, line 265). If the read takes close to the whole
timeout, every original lane, unflagged ones included, gets `remaining < 1` and is recorded
`ping_timeout` without a probe. It is then replaced from the order, or the review stops with exit 3
when no lane is left. `cmd_ping_lanes` then writes those unprobed `ping_timeout` entries, with a fresh
`checked_at`, into the quota cache (line 269). That cache is user-global
(`quota.py:33`, `cache_base(env)/quota.json`; `cross-ai-dispatch.md:29` takes `QUOTA_JSON` from
`cache-path --kind quota`). For the one-hour `QUOTA_TTL_SECONDS`, `refresh_quota_cache` and
`resolve-reviewers` treat the healthy lanes as unavailable in later reviews as well.

Trigger: nothing in the runner between `parseArgs` and the status print can stall
(`cross-ai.mjs:6982-7000`; the line is a synchronous state-file read). The full-timeout case therefore
needs a stalled node start or a stalled state-directory read (a heavily loaded host, a slow network or
FUSE home), which is rare. But any read delay comes off every lane's budget, and with a small
`--timeout` (1 or 2 s) an ordinary node start-up delay already times all lanes out. D-05
(owner-confirmed 2026-11-25) says a missing runner or a bad record never blocks a lane; here a slow
runner blocks every lane, including lanes that have no pool. Reproduced (scratch `verify_ping.py`;
lane-a flagged and pooled, lane-b unflagged, the read advances the clock by the 30 s timeout and
returns no record):

```
lines: ['ping lane-a: replaced by lane-c (ping_timeout)', 'ping lane-b: replaced by lane-d (ping_timeout)']
probed: [('lane-c', 30), ('lane-d', 30)]
cache: {'lane-b': (False, 'ping_timeout'), 'lane-a': (False, 'ping_timeout'), ...}
```

`test_status_read_time_comes_off_the_probe_budget` (`tests/test_lane_ping.py:494-516`) has only the
pooled lane, so nothing tests the unflagged sibling (executor item 5).
**Fix:** Take the read time off the budget only for lanes that carry a decision. Unpooled lanes keep a
budget measured from their own start, and a lane that timed out without being probed is not written
to the quota cache:
```python
# _ping_one / _budget_s: the shared start applies to pooled keys only
pooled = row["key"] in (seams.decisions or {})
begin = seams.started if (pooled and seams.started is not None) else started
```
Also skip `state["cache"]` updates for entries that report "ping deadline reached" without a probe
having run. Add a test: one pooled lane plus one unflagged lane, the read uses the whole timeout, and
the unflagged lane is probed with its full budget.

## Warnings

### WR-01: The security signal misses "authentication", "authorization", "authorize" and "OAuth2"

**File:** `skills/ai-kit-spec-review/ai_kit_spec/review_signals.py:10-13`
**Issue:** `_words` wraps the alternatives in `\b(?:...)\b`. The bare alternatives `auth` and `oauth`
then match only as whole words, so the most common security words never trigger: "authentication",
"authorization", "authorize", "OAuth2". `encrypt\w*` and `credential\w*` show that suffixes were
meant to be covered. Reproduced (scratch `verify.py`):
```
'Add OAuth2 authentication and authorization to the login flow' []
'Implement user authentication' []
'Authorize admin endpoints' []
```
For such a plan, without jev or with a confident jev `one`, the review runs on one lane. The
deterministic floor of SPEC R6 / D-07 fails, and the jev payload says "Signals: none".
`test_common_words_never_trigger` (`tests/test_review_signals.py:108-121`) excludes "author" and
"authority", which explains the bare `auth` but does not justify losing the real words.
**Fix:** Use `auth(?:n|z|entic\w*|ori[sz]\w*)?|oauth\d*` in place of `auth|authn|authz|oauth`. Add
"authentication", "authorization", "authorize" and "OAuth2" to `TRIGGERS` in
`tests/test_review_signals.py`, and keep "author" and "authority" in the negative list.

### WR-02: jev's reviewer pick cannot choose the reviewer; the docs still say "among the first five keys of the review order"

**File:** `skills/ai-kit-spec-review/ai_kit_spec/jev_review.py:311-317, 329-337`; `skills/ai-kit-spec-review/references/lane-failure.md:70`
**Issue:** The reviewer tokens come from `candidates[:5]`. `candidates` holds the configured rows plus
at most one resolver lane (`_with_second_lane`), so at most two tokens exist. The doc's "among the
first five keys of the review order" is false. Plan review asked for exactly this phrase to be
replaced with "the reviewer among the candidate lanes (the current lanes, then that second lane)"
(40-REVIEWS.md:1068), and the change was not made. The criteria text "lane position N of the owner's
review order" is also false: p2 is the second candidate, not the second key of the order. On a
confident `one`, `rows = inputs.reviewers[:1]` and the pick is looked up only in those rows, so a
confident `p2` is silently dropped. `test_unusable_pick_with_a_count_changing_answer`
(`tests/test_jev_review.py:619-621`) pins that drop. jev therefore never chooses which lane reviews
alone. It can only reorder two lanes that both run. SPEC R6 says "jev picks the reviewer from the
owner's order and one or two lanes".
**Fix:** On `one`, take the picked candidate as the single row (`rows = [first or inputs.reviewers[0]]`).
Apply the 40-REVIEWS.md:1068 wording to lane-failure.md:70 and the `REVIEWER_QUESTION`/criteria text
("candidate N", not "lane position N of the owner's review order"). Then flip the pinned test.

### WR-03: The size-review failure path contradicts itself: the ping is said to run but the SKILL gate skips it, and "unchanged" files can be changed

**File:** `skills/ai-kit-spec-review/references/lane-failure.md:85`; `skills/ai-kit-spec-review/SKILL.md:192,343`; `skills/ai-kit-spec-review/references/cross-ai-dispatch.md:191`; `skills/ai-kit-spec-review/ai_kit_spec/jev_review.py:375-396`
**Issue:** lane-failure.md:85 says that on a nonzero `size-review` exit, "reviewers.json and the round
log [stay] unchanged ... the ping still runs before round 1". But the round log is created only by
size-review's round-0 event (cross-ai-dispatch.md:191, "the round log every later step looks for"),
and SKILL.md:343 runs the ping only "whenever `$RUN_TMP_DIR/lanes.jsonl` exists". An unreadable or
non-UTF-8 `--doc` makes size-review exit 2 before any write (`_read_size_inputs`, lines 375-379).
lanes.jsonl then never exists, so there is no ping, no `--lane-log` dispatch, no partial status and no
flagged switch. The whole R1-R4 path is off for that review, against the doc's promise. Plan review
asked for the opposite branch: "give a `size-review` exit 2 its own branch (stop with the stderr line;
never dispatch without the ping)" (40-REVIEWS.md:1069); the shipped doc continues instead. Separately,
when `write_rows` succeeds and `append_event` then raises, the shared `except OSError` returns 2 with
reviewers.json already rewritten, so "unchanged" is false (executor item 7).
**Fix:** Pick one rule and state it in all three documents. Either stop on exit 2 as the handoff says,
or make the SKILL.md ping gate "active cross-AI path" rather than "lanes.jsonl exists" (ping creates the
log through `O_CREAT`). Split the two `OSError` branches, or append the event first and write the rows
second, so the exit-2 promise holds.

### WR-04: The cap-stop row drops "Decide manually" whenever owner-items.json is empty, including when classification never ran

**File:** `skills/ai-kit-spec-review/SKILL.md:527`; `skills/ai-kit-spec-review/references/lane-failure.md:113`
**Issue:** The Cap reached row says: "Ask the owner to decide only when `owner-items.json` holds an
item ... with none, drop `Decide manually.`". owner-items.json is filled only by a successful
`classify-disagreements --owner-out`. With no `TOOLS_PY`, or a nonzero exit from classify (exit 2 on
an unreadable report, `jev_review.py:253-262`), the file is empty. The cap stop then reports open
findings without asking the owner. lane-failure.md:113 says the opposite: "Without `TOOLS_PY`, or on a
nonzero exit, keep today's path: every finding goes to the owner." That is a fail-open on the owner
decision, and the two documents disagree.
**Fix:** In the Cap reached row, drop `Decide manually.` only when `classify-disagreements` exited 0
and every open finding landed in `skipped`. Otherwise keep today's message. Pin both cases in
`tests/test_lane_failure_text.py`.

### WR-05: The lane-reader guard exempts `lane_pool` by file name, so lane_order.py and propose_cmds.py may call the reader unseen

**File:** `tests/test_lane_settings.py:236-246`
**Issue:** The reader `lane_settings.lane_pool` has the same name as the module `ai_kit_spec.lane_pool`.
To stop false hits, `ALLOWED_READERS` exempts `lane_pool` entirely for lane_order.py and
propose_cmds.py. A real `lane_settings.lane_pool(...)` call added to either file now passes the guard.
Reproduced (scratch `verify_misc.py`): `_reader_lines(planted, allowed=ALLOWED_READERS["lane_order.py"])`
gives `[]`, while a plain module gives `[2]`. The comment "the one reader each module may call" is
also wrong: lane_switch.py is allowed three. The allowance is keyed by base name across both scanned
packages, so a same-named file in the superpowers package inherits it (executor item 2).
**Fix:** Rename the reader (for example `lane_free_pool`), or make the scan call-aware: count an
`Attribute` only when its `value` is `Name("lane_settings")`, and count a `Name` only when it was
imported from `lane_settings`. Then delete the two allowances and add a planted
`lane_settings.lane_pool(...)` case for lane_order.py to `test_scanners_catch_a_planted_setter_and_reader`.

## Info

### IN-01: record_merge leaves a never_resolved lane's readable report out, and a re-merge rewrites never_resolved to failed/real_error

**File:** `skills/ai-kit-spec-review/ai_kit_spec/review_log.py:100-113`
**Issue:** Item 1 is confirmed. A readable report whose last state is `never_resolved` is skipped
(line 112). That is the conservative direction, but lane-failure.md:25 names only failed and replaced.
Line 102 also omits `never_resolved`, so a second merge of the same round (the pending-lane resume
re-merge) appends `failed`/`real_error` over it. Reproduced (scratch `verify_misc.py`): after merge 1
the state is `never_resolved`, after merge 2 it is `failed` with `real_error`. The Judged-by line then
shows a wrong reason.
**Fix:** Treat `never_resolved` like failed and replaced at line 102 (`in ("failed", "replaced",
"never_resolved")`), and name `never_resolved` in lane-failure.md's Partial status paragraph.

### IN-02: switch-lane runs route discovery for every non-quota or unflagged refusal

**File:** `skills/ai-kit-spec-review/ai_kit_spec/lane_switch.py:243-250`
**Issue:** Item 3 is confirmed in part. Refusals from `_refusal` (no record, a state other than failed,
lane changed) return before discovery. A lane whose recorded reason is not `quota`, or that is not
flagged, still reaches `review_routes(config, deps)` (line 244, which runs `route_all` and may spawn
inventory or describe children) before `flagged_replacement` returns None. SKILL.md Step 1 runs
switch-lane on any nonzero exit of a flagged lane, so every transient, auth or refused exit pays for a
discovery it never uses.
**Fix:** Move `lane_ping._lazy_routes` into lane_switch and pass the lazy lookup, or check
`reason == "quota"` and the flag before building the routes.

### IN-03: A prompt-file or --timeout-tiers failure in dispatch-reviewer exits before the log write

**File:** `skills/ai-kit-spec-review/ai_kit_spec/cli.py:1428-1433`
**Issue:** Item 4 is confirmed. `open(args.prompt_file)` and `int(t)` run outside the try block. A
missing prompt file or a bad tier raises a traceback (exit 1) and appends nothing. On a resume, the
log keeps the earlier attempt's reason (for example `quota`), so the merge shows that stale reason and
a later switch-lane decides on it. On a first attempt the lane reads `never_resolved`.
**Fix:** Read the prompt and parse the tiers inside a `try` that calls
`_record_dispatch_failure(args, key, "configuration")` on `OSError`/`ValueError` and returns 1.

### IN-04: The 40-06 payload test checks the context shape with a search, not a full match

**File:** `tests/test_jev_review.py:349-359`
**Issue:** Item 6 is confirmed. `assertRegex` searches, so a context with extra text before or after
`Severity: ... Source: escalated.` still passes. The banned-needle list catches only the fixture's own
strings. The 40-07 sizing test was anchored with `fullmatch` (line 669); this one was not.
**Fix:** `self.assertIsNotNone(re.fullmatch(shape, item["context"]), item["context"])`.

### IN-05: Exit codes of the new commands that no doc branch covers

**File:** `skills/ai-kit-spec-review/ai_kit_spec/lane_switch.py:228-235`; `skills/ai-kit-spec-review/ai_kit_spec/lane_ping.py:257-279`; `skills/ai-kit-spec-review/references/lane-failure.md:15`; `skills/ai-kit-spec-review/SKILL.md:343`
**Issue:** Item 8 is confirmed and wider than reported. switch-lane exits 2 on `--round < 1` or
`--index < 0`, and exits 1 with only a stderr line ("no reviewer at index") and no `not switched`
stdout line. A missing reviewers.json or a row without `key` raises a traceback (exit 1). The docs
know only `switched ...` (0) and `not switched ...` (1). ping-lanes documents 0, 2 and 3, but an
unreadable or malformed reviewers.json, a row without `key`, or an `OSError` while appending to the
log or writing the quota cache raises a traceback (exit 1), which SKILL.md:343 has no branch for.
**Fix:** Catch `OSError`/`ValueError`/`KeyError` at the top of both commands, print one
`ai-kit-spec: ...` stderr line and return 2. Document "any other nonzero exit: stop before dispatch and
surface stderr" for ping-lanes, and "anything but `switched`: handle the exit as an unflagged lane"
for switch-lane.

### IN-06: The loop diagram has no pending-lane node and sends Edits Applied past the classify step

**File:** `skills/ai-kit-spec-review/references/loop-diagram.md:70-80`
**Issue:** Item 10 is confirmed. The gap predates this phase (the diagram had no hard-tier node before
40-10). In addition, "Parse fixer Status" -> "Ping lanes" on Edits Applied skips the Step 4 rule
"Classify first ... whatever its Status line" (SKILL.md Step 4). Every "next iter" edge now goes
through "Ping lanes", including on the `--no-cross-ai` path, which keeps no round log and runs no
ping. Plan review left the unconditional ping edges open (40-REVIEWS.md:589, 1101).
**Fix:** Add a "Lane pending (hard tier)" node from the dispatch with an edge to Surface. Route Edits
Applied through a "listed skip or escalation?" diamond into Classify. Label the next-iter edges "ping
when the round log exists".

### IN-07: The waiting lane of an expired pool is replaced with reason `quota` even after the retrying lane cleared the pool

**File:** `skills/ai-kit-spec-review/ai_kit_spec/lane_ping.py:119-121`; pinned by `tests/test_lane_ping.py:442-443`
**Issue:** With two chosen lanes in one expired pool, the second one (`expired-wait`) gets a `quota`
entry before the first one's retry result is known. When that retry succeeds and clears the record,
the second lane is still replaced and logged `quota` ("ping lane-b: replaced by lane-c (quota)"), and
the review turns partial. The stored reason is not what happened.
**Fix:** Resolve `expired-wait` lanes after their pool's `expired-retry` probe: probe them when the retry
succeeded, and mark them `quota` only when it failed.

### IN-08: Stale PROVISIONAL labels in the switch tests

**File:** `tests/test_lane_switch.py:56,216`
**Issue:** "PROVISIONAL: the free-pool comparison awaits owner confirmation." The SPEC's 2026-11-25
amendment says the owner confirmed and "the artifacts drop the PROVISIONAL label". lane-failure.md is
pinned free of the word (`test_blocked_until_reader`); these two test comments are not.
**Fix:** Drop both labels.

### IN-09: `pool_blocked` has no production caller

**File:** `skills/ai-kit-spec-review/ai_kit_spec/lane_switch.py:117-119`
**Issue:** Only `tests/test_lane_switch.py` calls it. Production uses `pool_status` and `pool_decisions`.
**Fix:** Delete it and point the tests at `pool_status(...)[0] == "blocked"`.

### IN-10: Already-defended-elsewhere: the dict check in round_states

**File:** `skills/ai-kit-spec-review/ai_kit_spec/review_log.py:44-45`
**Category:** necessity
**Issue:** `round_states` drops non-dict events, but every production caller passes `read_events(...)`
output (`lane_ping.py:261`, `lane_switch.py:237`, `cli.py` `_merge_with_lane_log`), and `read_events`
already keeps only dicts (`review_log.py:36-37`). The file read is the trust boundary, and that guard
stays. This second check defends against nothing.
**Fix:** Optional: drop lines 44-45, or note that `read_events` is the one validator.

### IN-11: The REASONS non-vacuity test cannot fail

**File:** `tests/test_ai_kit_spec.py:3493-3500`
**Issue:** `test_reason_lock_is_not_vacuous` asserts `set(REASONS) | {"zzz_added"} != expected` and
`set(REASONS) - {"quota"} != expected`. These are set-arithmetic facts that hold whatever `REASONS`
holds, so the test never runs the lock assertion against a changed list and cannot fail. The real
non-vacuity case is the doc-table mutation in `tests/test_lane_failure_text.py:88-92`.
**Fix:** Delete it, or make it patch `error_classifier.REASONS` (`mock.patch.object`) with an added key
and assert that the lock check raises `AssertionError`.

## Executor items: confirmed or refuted

1. **record_merge and a never_resolved lane with a readable report: confirmed.** `review_log.py:112`
   skips it (not judged, no new event). This fails closed, but it is undocumented, and line 102 lets a
   re-merge rewrite `never_resolved` to `failed`/`real_error` (reproduced). See IN-01.
2. **lane_pool name clash and the two allowances: confirmed.** `ai_kit_spec/lane_pool.py` exists and is
   imported by `lane_order.py:8` and `propose_cmds.py:10`. The allowances make a real reader call in
   those files invisible (reproduced). See WR-05.
3. **A refused switch-lane may still run route discovery: confirmed in part.** Not for `_refusal`
   outcomes (they return at line 242). Yes for non-quota reasons and unflagged lanes (line 244 runs
   before 247). See IN-02.
4. **A prompt-read failure exits before the log write: confirmed.** The same holds for a bad
   `--timeout-tiers` (`cli.py:1428-1433`). See IN-03.
5. **A slow status read shortens every original lane's budget, with no test for the unflagged case:
   confirmed, and worse than stated.** At the extreme, unflagged lanes are marked `ping_timeout`
   without a probe, replaced, and cached unavailable for an hour in the user-global quota cache
   (reproduced). See CR-02.
6. **The 40-06 payload test uses assertRegex: confirmed** (`tests/test_jev_review.py:359`). See IN-04.
7. **The sizing-event append shares the write's error branch: confirmed** (`jev_review.py:386-396`).
   It makes lane-failure.md:85's "leaves reviewers.json ... unchanged" false. See WR-03, which also
   covers the larger contradiction on the same path.
8. **switch-lane exits 2 on a bad --round or --index, with no doc branch: confirmed**
   (`lane_switch.py:228-230`). There are also undocumented stderr-only exits and traceback exits in
   switch-lane and ping-lanes. See IN-05.
9. **SKILL.md Step 1 paragraphs inside the numbered list without blank lines: refuted as a defect.**
   SKILL.md:391 and :410 are indented to the list item's content column and continue item 3 lazily.
   That is the same pattern the item already uses for "**Check the `--files` set ...**" (398) and
   "**Two hard rules ...**" (404). They render inside item 3, where they belong. No finding.
10. **The loop diagram has no pending-lane node: confirmed, and it predates this phase.** The new
    Edits Applied edge also skips the classify-first rule. See IN-06.

## Not read in full

- `tests/test_role_orders.py`: only the added test names and the probe-quota pool cases were read.
- `tests/test_fold_check.py` lines 140-275, and `tests/test_lane_switch.py` lines 1-247 (the pure
  helper cases): skimmed by test name.
- The eval fixture plans (`evals/files/*/demo.md`) and the `tests/fixtures/` plan files: checked only
  where a test or eval named them.
- `40-REVIEWS.md`: cycle 1 batch A, the cycle 2 review conditions and both triage sections were read,
  but not the full cycle 2 reviewer text. `40-*-PLAN.md` files were not read.

## Resolution

Fixed in chunk c7 on 2026-11-25, one `fix(40):` commit per group. Every behaviour fix got a test that failed before it; the red
output is kept in the run's lane folders. "Ponytail n" is finding n of the ponytail review of the same range.

- CR-01: fixed, 06c882a (size-review adds the first lane of the resolver's double-mode pick that is not already a row).
- CR-02 (executor item 5): fixed, d87643e (the blocked-status read has its own bound; every probe gets its whole timeout, so an
  unprobed lane is never `ping_timeout`, replaced or cached for it).
- WR-01 and ponytail 1: fixed, dcecb76 and 70f35c7 (security matches authentication, authorization, authorize and OAuth2;
  irreversible skips a hit that `never`, `do not`, `don't` or `must not` precedes on its line, or that `no` directly precedes,
  a hit on a `trap` line, and an `rm -rf` of a temp path; 70f35c7 narrowed the first rule, which also hid real work such as
  `rm -rf templates/` and "Without a backup, drop table users.").
- WR-02 and ponytail 3: fixed, 67e1751 (a confident `one` keeps jev's pick; tokens name candidate lanes; lane-failure.md says so).
  A confident `one` may pick the lane the resolver adds, which after CR-01 can share the plan author's vendor; the SPEC sets no
  vendor rule for the pick, and a test pins the behaviour.
- WR-03, ponytail 2 and executor item 7: fixed, 5a4203b (the sizing event is written before `reviewers.json`; the ping runs on the
  active path whatever size-review exited and starts the round log; SKILL.md and lane-failure.md agree).
- WR-04: fixed, ff12f38 (the cap stop drops `Decide manually.` only when classification exited 0 and left no owner item).
- WR-05 and executor item 2: fixed, 5317d6b (the reader is `lane_settings.lane_free_pool`; the two allowances are gone and a planted
  call is caught).
- IN-01, IN-02, IN-03, IN-05, ponytail 9 and executor items 1, 3, 4 and 8: fixed, ad61b3e.
- IN-04, IN-08, IN-09, ponytail 10, IN-10 and IN-11 (executor item 6): fixed, 451d6dc.
- IN-07: fixed, 29a59e9, with the text corrected in db07102 (only the ping waits on the retrying lane).
- IN-06 (executor item 10): fixed in chunk c8, a9854fd (a hard-tier pending-lane node from the Status parse, a "listed skip or
  escalation?" diamond that sends the fixer's summary to the classify step first, and an edge that skips the ping off the active
  cross-AI path; the four next-iteration edges into the ping stay, as the diagram test pins them).
- Ponytail 5: fixed, c0c7c0d (`review_log.lane_event` builds every lane event; the two dispatch recorders are one).
- Ponytail 6: fixed, 455e659 (`lane_switch.review_lane`; a key missing from the configuration now raises `KeyError`, which
  switch-lane reports as its exit-2 line, instead of a bare `StopIteration`).
- Ponytail 7: fixed, 0f31057 (`reviewer_dispatch.row_is_native` and `row_resolved`, used by the dispatch and the ping).
- Ponytail 11: fixed, f1aa6d6 (`lane_switch.unavailable_entry`). Ponytail 12: fixed, 124476f (one bounded thread-pool helper).
  Ponytail 13: fixed, d689a76 (one merged-report renderer).
- Ponytail 4 and 8: fixed, fcbf033 (SKILL.md passages that repeated lane-failure.md became pointers or were cut, body 7722 -> 7553
  words; the classify paragraph of apply-findings.md and the sizing text of cross-ai-dispatch.md point to lane-failure.md). The
  SKILL.md edit makes the skill's judge digest stale until its next judge loop.
- Security signal on rule text (orchestrator item after c7): fixed, f359721 (the security signal skips a hit that a rule word
  negates on its line, the same rule as the irreversible signal; a real security plan that also carries such rule lines still
  fires, pinned by a fixture).
- switch-lane write order (orchestrator item after c7, same shape as WR-03): fixed, 1087c6c (both round-log events go out in one
  write before `reviewers.json` is rewritten, so a failed log write changes neither file).
- Executor item 9: not taken, refuted above (same list style as the item's other paragraphs).
- Ponytail 14 to 17 (`id()` keys, per-run state in the seams tuple, serial replacement probes of about 140 s worst case, size-review
  routing every lane): not taken; low, no defect at this load.

Signal re-measure after 70f35c7, over this repo's own plans with the shipped `plan_signals`:

- GSD plans, `.planning/phases/*/*-PLAN.md` (303 plans; `.planning/milestones/*/*-PLAN.md` matches none): irreversible 278 -> 11,
  any signal 286 -> 235, security 209 -> 210, data 80 -> 80.
- Superpowers plans, `docs/superpowers/plans/*.md` (38 plans): irreversible 8 -> 8, any signal 24 -> 24, security 16 -> 17,
  data 15 -> 15.
- For reference, the archived plans one level deeper, `.planning/milestones/**/*-PLAN.md` (269 plans): irreversible 143 -> 30,
  any signal 256 -> 232.

Re-measure after f359721 (security skips negated rule lines), same sets:

- GSD plans (303): security 210 -> 157, any signal 235 -> 195, irreversible 11 -> 11, data 80 -> 80.
- Superpowers plans (38): security 17 -> 17, any signal 24 -> 24, irreversible 8 -> 8, data 15 -> 15.
- Archived plans, `.planning/milestones/**/*-PLAN.md` (269, reference): security 212 -> 199, any signal 232 -> 227.

Most of the remaining security hits are this repo's real vocabulary (auth status, permission and sandbox flags, secret redaction,
"injection" as in dependency injection). 18 GSD plans still fire only through the owner's bypass-permissions preamble ("runs with
bypass permissions", "ask for permission"); a phrase rule for it would also hide real permission work, so it was not added. A
clause-scoped negation was tried (GSD security 158) and not taken: it also moved the irreversible count of the archived plans.

---

_Reviewed: 2026-11-25T19:13:24Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
