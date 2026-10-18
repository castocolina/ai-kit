---
phase: 21
reviewers: [opencode-plan-review]
reviewed_at: 2026-10-18T13:42:40Z
plans_reviewed: [21-01-PLAN.md, 21-02-PLAN.md, 21-03-PLAN.md, 21-04-PLAN.md, 21-05-PLAN.md, 21-06-PLAN.md]
models:
  opencode-plan-review: "router-env/my-plan-review"
model_sources:
  opencode-plan-review: "pinned"
---

# Cross-AI Plan Review — Phase 21

<!-- gsd:plan-revision-conflicts:begin -->
## Plan-Revision Conflicts
<!-- gsd:plan-revision-conflicts:end -->

Cycle 1, against the plan set at 42fa790. Reviewer lane: `review.default_reviewers =
["opencode-plan-review"]` (reviewer instance on the opencode adapter, model
`router-env/my-plan-review`, no effort flag because `review.effort.opencode` is `inherit`). The
lane ran once, exit 0, empty stderr, about 5 minutes. Plan coverage: 6/6 ids. No
evidence-quality discount marker. No prompt trimming.

## OpenCode Review (opencode-plan-review)

## 21-01

**Summary:** The detection work is grounded in the existing resolver and parser, but its `real_path` guarantee and wrapper-proof behavior do not yet cover every path that consumes them.

**Strengths**
- Preserves the resolver’s positional arguments and tests PATH lookup without a shell; the current resolver is a first-hit lookup ([`detection.py:167–185`](skills/ai-kit-spec-review/ai_kit_spec/detection.py#L167-L185)).
- Uses a captured listing while retaining the existing no-header model-line behavior.

**Concerns**
- **HIGH:** Adding `real_path` only in `build_runtimes_snapshot` leaves refreshed rows inconsistent: `_refresh_runtime` copies an old row and replaces `path` without replacing `real_path` ([`detection.py:999–1006`](skills/ai-kit-spec-review/ai_kit_spec/detection.py#L999-L1006), [`routing.py:269–299`](skills/ai-kit-spec-review/ai_kit_spec/routing.py#L269-L299)).
- **HIGH:** The runner’s `resolveBin` still rejects a grok `agent` at the first PATH hit without scanning later entries. Detection can therefore report Cursor installed while dispatch cannot launch it ([`references/cross-ai.mjs:404–429`](skills/ai-kit-spec-review/references/cross-ai.mjs#L404-L429)). Plan 01 explicitly leaves this unchanged.
- **MEDIUM:** The proposed parser checks ASCII IDs in the capture, but its “non-space token” rule does not enforce that alphabet on other CLI output (21-01, Task 2).

**Suggestions**
- Update and test the refresh path when a binary changes, or limit the documented `real_path` guarantee to newly built snapshots.
- Mirror guarded scan-all resolution in the runner and its rendered copy, or state the remaining dispatch limitation prominently.
- Validate arbitrary parsed IDs against the intended alphabet.

**Risk Assessment: HIGH** — snapshot metadata can become stale, and the advertised wrapper-proof detection may not lead to a usable dispatch.

## 21-02

**Summary:** The two-file deliverable is well bounded. Explicit pins, bundle-style parsing and test registration are appropriate for files that will not be linked until Phase 21.1.

**Strengths**
- Keeps Cursor pins out of Claude’s `agents/` and checks them against the captured listing.
- Registers the new unit module with the generated test listings, consistent with [`run_unittest_parallel.py:76–97`](tools/run_unittest_parallel.py#L76-L97) and [`gen_test_groups.py:72–103`](tools/gen_test_groups.py#L72-L103).

**Concerns**
- **MEDIUM:** The optional catalog test skips when `query_agent_catalog` returns `None`, including when an available catalog query fails. That permits the “no GSD collision” check to pass without a successful query ([`gsd_catalog.py:112–146`](skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/gsd_catalog.py#L112-L146); 21-02, Task 1).
- **LOW:** The Node parity oracle compares selected fields on two valid files, not every parsed field or rejection case. Its stated scope should remain “these shipped files,” not full parser equivalence (21-02, Task 1).

**Suggestions**
- Skip only when Node or gsd-core is unavailable; fail on a query error when both are present.
- Compare the complete field map if full parity matters.

**Risk Assessment: MEDIUM** — the static pins are well tested, but one collision check can silently become a skip.

## 21-03

**Summary:** Cursor-first gsd-core discovery and a resolve-model-only chain address concrete harness gaps. The rehearsal’s success evidence needs a stronger attempt boundary.

**Strengths**
- The proposed `.cursor` root fills the current host-specific omission ([`host.py:20–26,61–75`](skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/host.py#L20-L75)).
- Reuses the matrix oracle and correctly avoids claiming Cursor’s model-free agent files have baked model pins ([`gsd_curated_eval.py:4315–4356`](tests/gsd_curated_eval.py#L4315-L4356)).

**Concerns**
- **HIGH:** Task 2 runs the smoke followed by `echo "smoke exit=$?"`; the command then exits with `echo`’s status. Verification searches a potentially reused log for *any* `smoke exit=0`, so a failed rerun can inherit an earlier success ([`gsd_curated_eval.py:4826–4848`](tests/gsd_curated_eval.py#L4826-L4848); 21-03, Task 2).
- **MEDIUM:** Artifact checks cover cursor tier slots and resolved models but not every specialist `model_overrides.*` entry, despite the plan-wide no-`-fast` claim (21-03, Task 2; [`gsd_curated_eval.py:792–830`](tests/gsd_curated_eval.py#L792-L830)).

**Suggestions**
- Use fresh per-attempt outputs, preserve the smoke’s actual exit code and require that attempt’s ten passing steps.
- Check specialist overrides as well as tier slots.

**Risk Assessment: HIGH** — stale evidence could mark a failed rehearsal green before the live dispatch.

## 21-04

**Summary:** Runner-based launch, an explicit model and post-run protection checks are sound. Scratch-home teardown is the plan’s most consequential safety boundary.

**Strengths**
- Launches via the runner’s PATH resolution and argv rather than the user’s shell function ([`cross-ai.mjs:412–437`](.planning/scripts/cross-ai.mjs#L412-L437)).
- Requires both a runner status and host-written smoke evidence, rather than accepting `no_change` alone.

**Concerns**
- **HIGH:** Re-entry teardown trusts `tmp/p21/headless/scratch-home.txt` before validating it as this run’s scratch directory; normal teardown uses its contents in `rm -rf`. The inside-repo check is insufficient as a deletion guard (21-04, Task 1, scratch-home and teardown steps).
- **HIGH:** `run-smoke.sh` ends with `echo "smoke exit=$?"`, so it can report shell success when the smoke fails. Reused log and evidence paths compound the attempt-mixing risk (21-04, Task 1; [`gsd_curated_eval.py:4634,4842–4848`](tests/gsd_curated_eval.py#L4634-L4848)).
- **HIGH:** Setting `HOME`, `CURSOR_CONFIG_DIR` and `XDG_CONFIG_HOME` does not prove all inherited configuration/cache destinations are isolated. The runner scrubs host signals, not arbitrary path variables ([`cross-ai.mjs:84–96`](.planning/scripts/cross-ai.mjs#L84-L96)).
- **MEDIUM:** The stated reason for group cleanup is inaccurate: `runChild` calls group termination during normal finalization too ([`cross-ai.mjs:560–579`](.planning/scripts/cross-ai.mjs#L560-L579)). Checks for escaped workers remain worthwhile.

**Suggestions**
- Validate the recorded directory’s canonical location, type and ownership **before every deletion**; fail closed on uncertainty.
- Propagate the smoke exit status and isolate logs, evidence and PGID records per attempt.
- Audit inherited path variables and check every attempted child’s processes, not only `cursor-run1.pgid`.

**Risk Assessment: HIGH** — an unsafe teardown path or incomplete isolation threatens user data; misleading exit status threatens the live result.

## 21-05

**Summary:** The conditional label lift is appropriately tied to evidence, and pi’s warning remains. The evidence and judge gates are weaker than the claims they authorize.

**Strengths**
- Keeps the label edit, README wording, test pin and evidence section together (21-05, Task 1).
- Uses the existing skill digest mechanism ([`gsd_curated_eval.py:384–459`](tests/gsd_curated_eval.py#L384-L459)).

**Concerns**
- **HIGH:** The LIFT condition finds success strings anywhere in the evidence and matrix log; it does not establish one current passing run with no failing rows. That is weaker than R3’s explicit failure rule ([`21-SPEC.md:143–144`](.planning/phases/21-cursor-live-validation/21-SPEC.md#L143-L144); 21-05, Task 1).
- **HIGH:** The automated `PASS` check enforces score floors but not `CRITICAL 0`, `IMPORTANT 0`, or each report’s judged digest (21-05, Task 2).
- **MEDIUM:** Plan 05 can finish with the in-session judge pending, while Plan 06 forbids that marker. The orchestrator replacement is not an explicit dependency gate between them (21-05, Task 2; 21-06, Task 2).

**Suggestions**
- Bind the lift to one identified attempt’s runner status, smoke exit, ten steps and matrix result.
- Verify every judge criterion and digest from both reports before declaring `PASS`; require the orchestrator’s completed report before Plan 06.

**Risk Assessment: HIGH** — the shipped certainty label or review verdict could advance on incomplete evidence.

## 21-06

**Summary:** An opt-in, single-label exemption is a practical way to handle Cursor’s own config rewrite, but its assurance must be stated narrowly and the optional probe must not kill unrelated processes.

**Strengths**
- Leaves the existing cursor config entry strict for unflagged runs ([`gsd_curated_eval.py:324–363`](tests/gsd_curated_eval.py#L324-L363)).
- Calls for separate snapshot and smoke tests, including preservation of host-managed-only output (21-06, Task 1).

**Concerns**
- **HIGH:** Equal hashes of three selected config keys show only that those values match before and after. They cannot prove “ai-kit did not write your config” once all other bytes are exempted; the script claims more than its check establishes (21-06, Task 1, steps 2–4).
- **HIGH:** The optional probe kills newly observed `pgrep -f 'index.js worker-server'` PIDs. A concurrent, unrelated Cursor worker can enter that set and be killed (21-06, Task 1, step 5).
- **MEDIUM:** Plan 06 accepts a `BLOCKED: pi judge unavailable` state as a phase gate with a note, despite the required review loop and its own closure language (21-06, Task 2).
- **MEDIUM:** Several snapshot gates pipe into `grep` without requiring the checker’s exit status; the checker deliberately returns nonzero for strict changes ([`gsd_curated_eval.py:347–363`](tests/gsd_curated_eval.py#L347-L363); 21-06, Task 2).

**Suggestions**
- Describe the digest as limited key-integrity evidence; report other byte changes without attributing their writer.
- Reap only a verified process group belonging to the probe, or omit automatic killing and surface leftovers.
- Keep an unavailable judge explicitly blocking completion, and capture snapshot exit codes independently of output matching.

**Risk Assessment: HIGH** — the optional process cleanup can harm another session, and the config-integrity claim exceeds what is measured.

### Cross-plan assessment

All six plans were reviewed against this worktree’s source; no files were changed and no live AI CLI or tests were run. The most important revisions before execution are **attempt-specific success evidence** (21-03 through 21-05), **safe scratch-home teardown** (21-04) and **process ownership for the optional probe** (21-06). The user’s interactive Cursor run remains pending in these plans, so the phase must not be reported as interactively confirmed until its results arrive.

---

## Consensus Summary

One reviewer ran, so there is no cross-reviewer consensus and the convergence consensus gate
does not apply: every HIGH below counts. The reviewer raised 10 HIGH and 8 MEDIUM/LOW concerns.

Orchestrator spot-checks against source (verification only, no disposition):

- Confirmed, 21-01 refresh drops `real_path`: `_refresh_runtime` rebuilds the row with only
  `installed` and `path` (`skills/ai-kit-spec-review/ai_kit_spec/routing.py:278-284`), and no
  Phase 21 plan mentions `_refresh_runtime`.
- Confirmed, 21-04 group-cleanup rationale: `finalize` calls `killGroup(child, 'SIGTERM')` and
  `killGroup(child, 'SIGKILL')` on every path, including `reason === 'exit'`
  (`skills/ai-kit-spec-review/references/cross-ai.mjs:553-571`). 21-04's read_first note
  ("the finalize kill only on timeout/signal") is wrong; the surviving worker-server must be
  explained another way (for example a re-parented process outside the group).
- Partly inaccurate, 21-03/21-04 `echo "smoke exit=$?"`: the smoke log is opened with `>`
  (truncate), so a rerun cannot inherit an earlier `smoke exit=0` from the same log, and the
  echoed value is the smoke's own exit status. The real gap is narrower: the shell command's
  own exit is echo's, and evidence/artifact paths are not attempt-scoped.
- Deliberate, 21-01 runner `resolveBin` first-hit: 21-01 and 21-04 record this as an
  orchestrator decision (D-09). The replan must either change the runner and its rendered copy
  or state the detection/dispatch mismatch as an explicit, visible limitation.

### Agreed Strengths
- Single reviewer; see its per-plan strengths. Notably the evidence-tied label lift, the
  `cursor-agents/` separation from Claude's `agents/`, and launching cursor-agent only through
  the runner.

### Agreed Concerns
- Not applicable with one reviewer. Highest-priority single-reviewer concerns: attempt-specific
  success evidence (21-03 to 21-05), scratch-home deletion guard before `rm -rf` (21-04),
  process ownership for the optional probe's `kill` (21-06), and judge `PASS` checks that
  skip `CRITICAL 0`/`IMPORTANT 0` and digests (21-05).

### Divergent Views
- None (one reviewer).
