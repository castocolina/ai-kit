---
phase: 42-code-review-after-execution-and-jev-picked-executors
reviewed: 2026-11-27T19:24:59Z
depth: deep
files_reviewed: 27
files_reviewed_list:
  - skills/ai-kit-spec-review/ai_kit_spec/code_review.py
  - skills/ai-kit-spec-review/ai_kit_spec/lane_transport.py
  - skills/ai-kit-spec-review/ai_kit_spec/herdr_pane.py
  - skills/ai-kit-spec-review/ai_kit_spec/executor_pick.py
  - skills/ai-kit-spec-review/ai_kit_spec/jev_review.py
  - skills/ai-kit-spec-review/ai_kit_spec/cli.py
  - skills/ai-kit-spec-review/ai_kit_spec/runner_dispatch.py
  - skills/ai-kit-spec-review/ai_kit_spec/reviewer_dispatch.py
  - skills/ai-kit-spec-review/ai_kit_spec/execute_dispatch.py
  - skills/ai-kit-spec-review/ai_kit_spec/lane_settings.py
  - skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers/cli.py
  - skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers/dispatch_injection.py
  - skills/ai-kit-spec-execute-superpowers/SKILL.md
  - skills/ai-kit-spec-execute-superpowers/references/code-review.md
  - skills/ai-kit-spec-execute-superpowers/references/lite-block.md
  - skills/ai-kit-spec-execute-superpowers/references/dispatch-external-cli.md
  - skills/ai-kit-spec-execute-superpowers/references/fold-step.md
  - skills/ai-kit-spec-execute-superpowers/references/resolution-stops.md
  - skills/ai-kit-spec-execute-superpowers/evals/files/executor-pick/project/aikit/config.toml
  - skills/ai-kit-spec-execute-superpowers/evals/files/lite-small/model-catalog.json
  - skills/ai-kit-spec-config/references/config-file.md
  - skills/ai-kit-spec-config/references/wizard-flow.md
  - AGENTS.md
  - skills/_shared/ai_kit_rules_common/code_exploration.py
  - tools/run_unittest_parallel.py
  - tests/test_arch.py
  - tests/test_lane_transport.py
findings:
  critical: 1
  warning: 6
  info: 14
  total: 21
  necessity: 1
status: issues_found
---

# Phase 42: Code Review Report

**Reviewed:** 2026-11-27T19:24:59Z
**Depth:** deep
**Files Reviewed:** 27
**Status:** issues_found

## Summary

I reviewed the phase 42 range `7af5a8a..HEAD` with `.planning/` left out. The review covered the new modules (code_review, lane_transport, herdr_pane, executor_pick, the jev_review additions), the CLI wiring in both packages, the adapter references, the spec-config docs, the gate-runner change and the arch rule. I traced call chains across modules: dispatch-reviewer and dispatch-task through begin_round, end_round and pane_runner into run_runner; code-review-normalize, merge-reports and code-review-verdict; resolve-injection through the executor pick and the ladder walk. Three scratch scripts, since removed, reproduced CR-01, WR-02, WR-04, IN-01 and IN-03. WR-01, WR-03, WR-05, WR-06, IN-05 and IN-09 rest on code reading only. The scripts ran against the real modules and real `merge-reports` output, with a scratch HOME, and never called a host CLI or herdr.

Main concern: the code-review pass rule can fail open. `normalize_report` trusts whatever `review_reports.parse_findings` returns. A lane that writes its HIGH heading slightly off (`### High`, `### HIGH (1)`, `## HIGH`), or writes `### Status: Issues Found` with no bullet in the exact shape, is normalized to MEDIUM or to `### Status: Approved`, and the round passes. That breaks the SPEC prohibition "MUST NOT pass a review with one [CRITICAL or HIGH] open" (CR-01).

Other real defects:
- The execute-result classifier is wired with the status token only (WR-01).
- Superpowers-shaped reports lose each finding's fix text, or stop the run on common "no issues" wording (WR-02).
- The lite block never fires without jev; plan 42-03 chose this, so it is an owner decision (WR-03).
- `begin_round` overwrites a corrupt or foreign record (WR-04).
- After a cap stop, the run is stuck if HEAD moves (WR-05).
- A latent cluster of pane-lifecycle defects (WR-06). It is latent because `PANE_LABEL` is unverified and amendment 13 keeps every resume label unverified, so neither the pane path nor the resume path runs with the shipped labels. With those labels every lane runs as a fresh subprocess.

Executor leads: confirmed 2, 3 (narrowed), 4, 5, 7, 8, 9, 10, 11, 13 and 14. Lead 6 is refuted as a state leak. Lead 1 is not a defect (Info, necessity). Lead 12 has a likely root cause found by code reading (not reproduced); it is pre-existing and outside the phase diff. Each lead's outcome is in the finding that cites it.

Not reviewed in depth: `README.md`, `evals.json`, the `Makefile` and `.pre-commit-config.yaml` header-comment changes, and most of the 7,000 added test lines. For the tests I only grepped phase-42 test files for absolute paths and vacuous assertions, and the eval fixtures for real model names; the fixtures use placeholders only. No test was run through the parallel runner. The repros used direct module imports in a scratch directory.

Necessity rubric (`.claude/gsd-core/references/necessity-review.md`) was read and applied.

## Narrative Findings (AI reviewer)

## Critical Issues

### CR-01: Code-review normalization fails open: a HIGH finding under a non-exact heading, or an "Issues Found" report with no parsed bullet, passes the round

**File:** `skills/ai-kit-spec-review/ai_kit_spec/code_review.py:177-197` (with `render_report` at `:200-223` and `_sections` at `:95-112`; root parser `skills/ai-kit-spec-review/ai_kit_spec/review_reports.py:62-72`)
**Issue:** `normalize_report` checks gaps only for sections whose heading matches the exact `^### (CRITICAL|HIGH)\s*$` (`_AIKIT_HEAD_RE`, line 21). Every other shape slips through. Reproduced (scratch repro, removed after the review):
- `### High` + one well-formed bullet + `### Status: Issues Found`: `parse_findings` gives the bullet severity `None`, `render_report` files it under `### MEDIUM` (line 206-207), and `review_verdict` returns `pass`.
- `### HIGH (1)` and `## HIGH` headings: same, verdict `pass`.
- `### Findings` with the HIGH issue written as prose, plus `### Status: Issues Found`: zero findings, `render_report` writes `### Status: Approved` (line 221-222), verdict `pass`. The report's own status said issues, and nothing checks that.
- A superpowers report with an unindented `#` line between Critical item 1 and item 2: `_sections` ends the body at any line starting with `#` (line 105), so item 2 is dropped silently (`[('CRITICAL', 'First')]`).
- A `### HIGH` section with one parsed bullet and one malformed bullet: `_blocking_gap` only asks whether *any* bullet parsed (line 172), so the malformed HIGH is dropped from the normalized report and never reaches the fix prompt.

The lane report is untrusted model output, so a drifted heading is a realistic input. Through `code-review-normalize`, then `merge-reports`, then `code-review-verdict`, a round with an open HIGH or CRITICAL ends in `state: pass`. Then `fold-step.md` folds and readies the PR. This breaks SPEC R1 and the Prohibition "MUST NOT pass a review with one open". Real `merge-reports` output itself normalizes correctly (verified with a partial merge: `Judged by:` and `(Reviewers: a)` survive and the verdict is `fix`), so the hole is at the lane-report normalization step.
**Fix:** Fail closed in `normalize_report`:
```python
findings = review_reports.parse_findings(text)
if any(f["severity"] not in (*SEVERITIES, "CROSS-DOC") for f in findings):
    raise IncompleteReport("a finding sits under no recognised severity heading")
if status == "issues" and not findings:
    raise IncompleteReport("the status says Issues Found but no finding parsed")
# every bullet-shaped line under a blocking heading must parse
for heading, body in _sections(text, _AIKIT_HEAD_RE):
    bullets = [l for l in body if l.lstrip().startswith(("- **", "* **"))]
    if len(bullets) != len(_aikit_items(body)):
        raise IncompleteReport(f"{heading.strip()} has a bullet that does not parse")
```
Also make `_sections` end a body only at a heading of the same or a higher level (`re.match(r"^#{1,4} ", line)` for the superpowers `####` sections), not at any line starting with `#`. Then do the same `len(_top_items(body))` against bullet count check. Add tests for each shape above.

## Warnings

### WR-01: classify-execute-result gets only the status token, so jev never sees the runner's status, findings or coverage (lead 2, confirmed)

**File:** `skills/ai-kit-spec-execute-superpowers/references/dispatch-external-cli.md:150` and `:159-171`; `skills/ai-kit-spec-execute-superpowers/SKILL.md:247`; `skills/ai-kit-spec-review/ai_kit_spec/jev_review.py:489-501` (`execute_item`), `:504-518`, `:521-532`
**Issue:** `ExecuteFacts` and `execute_item` allowlist runner status, runner finding codes (`no_commit`, `task_uncovered`, `forbidden_path`, ...) and coverage. But both call sites pass only `--status "$STATUS"`, and the reference even says "from the status token alone". In practice jev always gets `Runner status: none. Runner findings: none. Coverage: none.` For an `external_cli` DONE run whose runner reported `no_commit` or `task_uncovered`, jev cannot flag it, which is the case R7 targets. With no evidence, jev answering `another_round` on a bare `DONE` downgrades the handover at random. Second defect: jev is also asked for `DONE_WITH_CONCERNS`, `NEEDS_CONTEXT` and `BLOCKED`, where `handover_status` cannot change anything. That is a wasted jev call on every such report. Plan 42-06 (task 5) left the flags out because "the Classify step holds no runner-status, finding or coverage scalar". But the dispatch result JSON already carries them: its `status` dict is the parsed `AIKIT-XAI` line, and the runner prints `coverage=... findings=...` on it (`skills/ai-kit-spec-review/references/cross-ai.mjs:1654`).
**Fix:** In the `ok` branch, take the runner facts out of `$DISPATCH_RESULT_JSON` (status `status`, its finding codes and coverage) with a small shim subcommand, not inline JSON, and pass `--runner-status`, `--findings`, `--coverage`. In `classify_execute_result`, return the default without asking jev when `facts.status != "DONE"`. Update the reference sentence "from the status token alone". The native branch can keep `--status` only, since a native dispatch has no runner.

### WR-02: Superpowers-shaped reports lose each finding's fix text, and common "no issues" wording stops the run as incomplete

**File:** `skills/ai-kit-spec-review/ai_kit_spec/code_review.py:146-160`, `:115-138`, `:24`
**Issue:** Session-model mode (and any lane that answers in superpowers' template) goes through `_superpowers_findings`. Two defects, reproduced with superpowers 7.0.2's own example shape (scratch repro, removed after the review):
1. `required` and `why` are both set to the item's title line. The `- Issue:` and `- Fix:` sub-bullets are discarded, and only `File:` is kept. The normalized and merged report, which `code-review.md` uses to build `iter$N-fix-prompt.md`, reads `Required: Date validation missing. Why: Date validation missing.` The fix implementer gets a title with no fix.
2. `_EMPTY_RE` accepts only `none`, `none.` and `- none`. A Critical section reading `None found.`, `No critical issues.` or `_None_` raises `IncompleteReport` (exit 4). That is an owner stop every round, although the report is clean. superpowers' template does not tell the reviewer to write exactly `None`.

**Fix:** Collect the indented sub-bullets of each item: `Issue:`/`Impact:` go into `why`, `Fix:` into `required`, falling back to the title. Widen the empty marker to a short closed set, `^(?:[-*]\s*)?_?(none|no (critical|important|minor) issues?)( found)?\.?_?$`, and add tests with the template's own example text.

### WR-03: lite-block writes no file unless jev answers confidently, even when the executor that will run is a lite model (owner decision: plan 42-03 chose this)

**File:** `skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers/cli.py:386-402`; `skills/ai-kit-spec-execute-superpowers/references/lite-block.md:21`
**Issue:** `lite = picked is not None and is_lite(...)`, and `picked` is found only from `pick.key`. `pick_executor` returns `key=None` for one candidate, jev absent, jev low and jev error. In all those cases the dispatch order (R3: "without jev ... the existing order decides") makes the first ranked candidate the executor. Scenario: an execute roster with one lane whose catalog class is `small`. Every task runs on that lite model, but `lite-block` prints `"lite": false` and the plan writer never gets the block. Same with two lanes, jev not installed, and a lite lane first. R4 and D-05 tie the block to "the picked executor". Without jev, that executor is the default-order head. The reference documents the gap ("with no jev, a low answer or one lane there is no pick and no file"), Plan 42-03 wrote that sentence and `test_no_pick_writes_nothing` pins it, and SPEC's R4 "empty" edge row reads "no executor picked adds nothing to the brief". So this is a recorded choice, not an executor slip. It still conflicts with R3's "without jev ... the existing order decides": without jev an executor is still picked, by the default order. And it removes the feature's value for every owner without jev. Raised for the owner to decide, not as a fix the fixer may apply alone.
**Fix (only on the owner's yes):** Fall back to the default-order head when there is no jev pick: `picked = next((c for c in ranked if c["key"] == pick.key), ranked[0] if ranked else None)`. Keep `decided_by` from the pick so the JSON still says `default`, and update `lite-block.md` and `test_no_pick_writes_nothing` to match. The feature is kept; only the fallback is added.

### WR-04: begin_round overwrites a corrupt or foreign transport record with an empty record, which close_record refuses to touch (lead 5, confirmed)

**File:** `skills/ai-kit-spec-review/ai_kit_spec/lane_transport.py:189-207` (`_locked_update`), `:216-230` (`begin_round`), `:144-151` (`read_record`)
**Issue:** `read_record` maps any unreadable or other-shape file to `{"version": 1, "lanes": {}}`. `_locked_update` then always calls `write_record` with the update's result. `begin_round`'s update returns the record unchanged, so every round start rewrites the file. Reproduced: a file holding `{"some": "other tool data"}` becomes `{"version": 1, "lanes": {}}` after one `begin_round`. A record truncated by a crash loses every recorded pane and session in the same way. Those herdr tabs are then orphaned from `close-transports`, so only the runner sweep can find them. Meanwhile `close_record` and `_load_raw_record` (line 396-405) treat the same file as foreign and refuse it. The two code paths disagree about one file. On spec review's default path (`transport.json` beside `--lane-log`), every non-native dispatch now also does a needless locked write.
**Fix:** Let `begin_round` read under the lock without writing: return `None` from its update and treat `None` as "no write" (move the remove-file case to an explicit sentinel). In `_locked_update`, refuse a file that exists but fails `_foreign_record`, raising `ValueError` the way `_load_raw_record` does. The CLI callers then degrade to a plain subprocess round with one stderr line.

### WR-05: After a cap stop the plan is stuck when HEAD moves; accept records the old head and the fold step refuses forever

**File:** `skills/ai-kit-spec-execute-superpowers/references/code-review.md:31-34`, `:146-148`; `skills/ai-kit-spec-execute-superpowers/references/fold-step.md:24-29`
**Issue:** At `cap_stop`, the start block prints only `CODE_REVIEW_NEXT=cap_stop` whatever HEAD is. The cap-stop answer offers accept (writes `owner_accepted` with `reviewed_head` = `iter<R>-head`) or stop. Scenario: the owner answers stop at the cap, fixes the open HIGH by hand, and re-invokes. The start block still prints `cap_stop`; a stop answer keeps it there on every re-invoke. An accept answer writes `owner_accepted` at the old head. The fold gate then compares that head's tree with the current `HEAD^{tree}`, they differ, and it prints "the code review has not passed for HEAD -- STOP". The next re-invoke hits the start block's `pass|owner_accepted` arm (line 31-33) and prints "HEAD moved after the code review ended -- STOP". No documented path re-runs a review round or resets `state.json`. The plan can only move on if someone deletes `superpowers-run-<key>-code-review/` by hand, and the skill text never mentions that.
**Fix:** In both the `cap_stop` and the `owner_accepted` arms of the start block, compare `ST_TREE` with `HEAD_TREE`. When they differ, print `CODE_REVIEW_NEXT=cap_stop_moved <R>` and offer a third owner answer, "review the new head". It writes `{"round": 0, "state": "none"}` (a fresh 3-round budget for the owner's own change) or one extra capped round. Document it in `resolution-stops.md`.

### WR-06: Pane lifecycle (latent): a pane that is already gone makes close-transports fail on every run, and an idled-out launcher fails the next round instead of reopening (lead 8, confirmed, plus two siblings)

**File:** `skills/ai-kit-spec-review/ai_kit_spec/lane_transport.py:298-308`, `:342-359`, `:447-458`; `skills/ai-kit-spec-review/ai_kit_spec/herdr_pane.py:56`, `:582-602`, `:622-629`
**Issue:** Latent: reachable only once `PANE_LABEL` flips to verified. `interactive` does reach a review row's `extra`, because `quota.to_resolved` copies every unknown field, so the path is live as soon as the label flips.
- A pane that is already gone (its run dir swept by the runner, or its tab closed by hand): `close_pane` returns `False` because `_owned_record` cannot `lstat` the run dir. `_close_one_pane` lists it as `failed` and keeps the entry, so `_close_under_lock` rewrites the record instead of removing it. `close-transports` exits 1 on this and every later close of the plan.
- Idle-out: the launcher loop exits after `PANE_IDLE_S` = 1800 s idle, which is common between two tasks of one execute lane. `run_record.runner_pid` is the per-round dispatch process, already dead, so the next runner start sweeps the run dir. `_prepare_pane` then reuses the recorded pane without checking it (`_pane_needs_renewal` looks only at `closed`, the renewal and the transport). `run_round` hits "launcher gone", `pane_spawn` raises `OSError`, and `run_runner` returns `_unavailable`. The round fails, an execute lane stops for the owner, and a review lane is lost for that round, all instead of reopening.
- Lead 8: after a renewal close, a failed `open_pane` only clears the busy mark (line 454-456). The closed pane dict stays in the entry and later counts as a failed close.

**Fix:** In `_close_for_renewal`, treat a pane whose run record is missing or whose launcher pid is not alive (`herdr_pane._read_run_record` and `pid_alive`) as needing renewal, and drop it from the entry before opening. Have `_close_one_pane` treat a pane whose run dir no longer exists as closed (nothing left to close; the sweep owns the tab). On a failed open after a renewal close, set the entry's `pane` to `None` under the lock.

## Info

### IN-01: Cargo-culted pattern: the jev redaction is applied to the reviewer prompt's description (lead 1, not a defect)

**File:** `skills/ai-kit-spec-review/ai_kit_spec/code_review.py:355-360`
**Category:** necessity
**Issue:** `_summary_text` exists for jev's summaries-only rule (SPEC Constraints). The reviewer prompt goes to review lanes, which are told to run `git diff` and read the changed files, and the same prompt carries `{plan}`, `{base}` and `{head}` unredacted. So that prerequisite does not hold here. The effect is lost context: "Adds the `--sweep` flag to tools/setup.py ..." becomes "Adds the [omitted] flag to [omitted] and fixes the [omitted] gauge colors for us". It is documented in `code-review.md:9` and harmless. Judgment call, so Info.
**Fix:** Keep the control-character strip and `secret_shapes.redact` (defense in depth). Drop the path/quote omission and the 80-character cut for the lane prompt, or raise the cap.

### IN-02: dispatch-reviewer starts the transport round before reading its inputs (lead 6, refuted as a state leak)

**File:** `skills/ai-kit-spec-review/ai_kit_spec/cli.py:1483-1489`
**Issue:** `begin_round` claims nothing; the busy mark is set only inside `pane_runner`. An input-read failure after it costs only a misleading `transport ...` stderr line and the needless record rewrite of WR-04. The same holds for the `LaneRefused` and `ValueError` returns, which skip `end_round`, so the round is simply not counted.
**Fix:** Call `_reviewer_round_start` after `_read_dispatch_inputs` succeeds.

### IN-03: A Labels tail with trailing text or a doubled period reads its last label as unknown (lead 3, narrowed)

**File:** `skills/ai-kit-spec-review/ai_kit_spec/code_review.py:73-80`
**Issue:** A single final period is stripped by `_BULLET_RE`, so the normal case works. `stage=mvp..` or `stage=mvp. See a.py.` gives `stage: unknown`, and `kind = logic` (spaces around `=`) gives `kind: unknown`. jev then gets less context for the fit (scratch repro, removed after the review). It never touches the severity rule.
**Fix:** `pairs = {k.strip(): v.strip().rstrip(".") ...}` and stop the value at the first whitespace.

### IN-04: Unused re-imports kept alive by suppression pragmas (lead 4, confirmed)

**File:** `skills/ai-kit-spec-review/ai_kit_spec/jev_review.py:27-29`
**Issue:** `_SPAN_RE` and `OMITTED` are not used in `jev_review`. `_UNSAFE_TOKEN_RE` is read only by `tests/test_jev_review.py:389`. Only `_summary_text` is used.
**Fix:** Import `_summary_text` alone. Point the test at `code_review._UNSAFE_TOKEN_RE` and drop both pragmas.

### IN-05: Pane path reads the record outside the lock after claiming, and a fallback round rewrites the holder's entry (lead 7, confirmed, latent)

**File:** `skills/ai-kit-spec-review/ai_kit_spec/lane_transport.py:447-450`, `:233-252`
**Issue:** Between `_claim_pane` and `read_record`, a concurrent round of the same lane id that fell back to a subprocess can run `end_round`. That rewrites the entry to `transport: "subprocess"`, `rounds: 1`. The holder then sees `_pane_needs_renewal` true and closes a healthy pane. This needs two overlapping dispatches of one lane id, which subagent-driven-development does not do today.
**Fix:** Return the entry from `_claim_pane`'s locked update and use it. In `end_round`, leave an entry alone when another live pid holds it.

### IN-06: The record lock is implemented twice (lead 9, confirmed)

**File:** `skills/ai-kit-spec-review/ai_kit_spec/lane_transport.py:189-206` and `:385-393`
**Issue:** `_locked_update` and `_under_record_lock` repeat the same makedirs, open, flock and unlock code. The `.lock` file also stays beside the plan's quota folder after a clean `close-transports`, by design.
**Fix:** Build `_locked_update` on `_under_record_lock`.

### IN-07: Vacuous last assertion in the lane-log pane test (lead 10, confirmed)

**File:** `tests/test_lane_transport.py:1384-1385`
**Issue:** `assertIs(f.__func__ if hasattr(f, "__func__") else None, None)` passes for any plain function, the pane runner closure included. The test still holds through `self.assertEqual(opened, [])`.
**Fix:** Assert `seen[0].runner_tiers_fn is <the deps runner_tiers_fn passed in>`, or drop the line.

### IN-08: `tests.test_herdr_pane_sweep_e2e` has no recorded time (lead 11, confirmed)

**File:** `tools/run_unittest_parallel.py:157` (listed in the e2e set) and `:169-199` (`E2E_RECORDED_SECS`, no entry)
**Issue:** A module missing from the table counts as over budget. So every commit that covers herdr_pane or lane_transport prints `staged: deferred to push` for it, and it runs only in pre-push `deferred-e2e`. Its runtime was not measured here.
**Fix:** Add its rounded `=== ... ok in <s>` time from one `make e2e-test` run.

### IN-09: Likely root cause of the `test_cursor_status_line` Errno 39 flake: a detached refresher writes into the temp dir during cleanup (lead 12; by code reading, not reproduced; pre-existing, outside the phase diff)

**File:** `tests/test_cursor_status_line.py:1224-1239` (`test_empty_cache_shows_no_quota_and_no_percent`); `tools/cursor_quota.py:296-303`, `:449-463`, `:421-446`
**Issue:** The test runs the entry with an empty cache. `core_needs_refresh` returns true when there is no `data_fetched_at` and no `last_attempt_at`, so `probe_read_quota` calls `probe_spawn_refresher`. That starts a detached `cursor_quota.py --refresh` in its own session, with `XDG_CACHE_HOME` inside the test's `TemporaryDirectory`. The entry returns at once and the `with` block's `rmtree` runs while the child is still creating `empty-cache/ai-kit/cursor/` and its lock and cache files. Under load 5.5 the child starts late, rmtree's final `rmdir` sees a new entry and raises `ENOTEMPTY`. The file is unchanged in this phase. The other entry-run tests (from line 139) seed a fresh synthetic cache through `_environment`, but whether `core_synthetic_cache` sets `data_fetched_at` was not checked, so other tests may race too.
**Fix:** Seed the empty-cache case with a recent `last_attempt_at` and `last_error_kind` (negative cache), so no refresher spawns. Or point that run at a cache base the test leaves behind its own wait.

### IN-10: A 124-character signature with lint suppressions to satisfy a plan grep (lead 13, confirmed)

**File:** `skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers/dispatch_injection.py:408-409`
**Issue:** `# pylint: disable-next=line-too-long` and `# noqa: E501` exist only so a plan-time grep matches one line.
**Fix:** Wrap the signature and loosen the plan check to a multi-line regex.

### IN-11: The adapter SKILL.md is at 297 of its 300-line budget (lead 14, confirmed)

**File:** `skills/ai-kit-spec-execute-superpowers/SKILL.md` (297 lines)
**Issue:** Any later fix to the code-review step (CR-01 or WR-05 wording) has three lines of room.
**Fix:** Move the native-dispatch paragraph's classify-execute-result sentence (line 247) into `dispatch-external-cli.md` or a reference.

### IN-12: Duplicate scalar check in the fold block

**File:** `skills/ai-kit-spec-execute-superpowers/references/fold-step.md:20-23`
**Issue:** `QUOTA_PATH` and `PROJECT_KEY` are checked by the first loop (line 20) and again by an identical second loop (line 22-23).
**Fix:** Delete the second loop.

### IN-13: A pane choice that falls back still logs "pane"; classify-execute-result has no jev error guard

**File:** `skills/ai-kit-spec-review/ai_kit_spec/lane_transport.py:224-225`, `:465-471`; `skills/ai-kit-spec-review/ai_kit_spec/jev_review.py:514-515`
**Issue:** `begin_round` prints `transport ...: pane` before `pane_runner` may fall back to a subprocess (busy, or failed to open), so the log names a transport that did not run. Separately, `classify_execute_result` lets an undecodable jev reply raise (`UnicodeDecodeError`, which the shared client does not catch). `executor_pick.pick_executor` guards against that. The reference's "nonzero, hand over unchanged" rule absorbs it, but the run prints a traceback.
**Fix:** Print one `transport ...: subprocess (pane fallback: <why>)` line on fallback. Wrap the `ask_items` call the way `pick_executor` does.

### IN-14: The wizard's interactive question promises a pane for any lane, but spec-review lanes never get one

**File:** `skills/ai-kit-spec-config/references/wizard-flow.md:79`
**Issue:** "a lane marked interactive may run in a herdr pane" holds for execute and code-review lanes only. `cli.py:1456-1457` forces `interactive=False` on spec review's default record (amendment 12(2)).
**Fix:** Add "(execute and code-review lanes; spec review never uses a pane)".

---

_Reviewed: 2026-11-27T19:24:59Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: deep_
