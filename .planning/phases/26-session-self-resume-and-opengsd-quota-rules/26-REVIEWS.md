---
phase: 26
cycle: 3
reviewers: [referee-one, referee-two]
reviewed_at: 2026-10-29T05:46:15Z
plans_reviewed: [26-01-PLAN.md, 26-02-PLAN.md, 26-03-PLAN.md, 26-04-PLAN.md, 26-05-PLAN.md, 26-06-PLAN.md, 26-07-PLAN.md, 26-08-PLAN.md, 26-09-PLAN.md, 26-10-PLAN.md, 26-11-PLAN.md, 26-12-PLAN.md]
models:
  referee-one: "router-env/my-referee-one"
  referee-two: "router-env/my-referee-two"
model_sources:
  referee-one: "pinned"
  referee-two: "pinned"
---

> Note: referee-one and referee-two share the opencode adapter; their consensus is cross-model, not cross-tool.

# Cross-AI Plan Review — Phase 26

<!-- gsd:plan-revision-conflicts:begin -->
## Plan-Revision Conflicts
<!-- gsd:plan-revision-conflicts:end -->

Convergence cycle 3 (the last), over the 12 plans as replanned in d07a5fd (cycle 2: 488db00).
Review prompt (70 KB): PROJECT.md (first 80 lines), the ROADMAP Phase 26 section, QTA-04/05/06,
26-CONTEXT.md and 26-SPEC.md inlined; the 12 plans, 26-RESEARCH.md, 26-PATTERNS.md,
26-VALIDATION.md, 26-SPIKE-REPORT.md and AGENTS.md referenced by repo path. The prompt listed the
cycle-2 findings as C2-H1..C2-H4 (cycle-2 current HIGHs 1-4) and C2-L1..C2-L3 (cycle-2 actionable
1-3) with their dispositions, pointed reviewers at `git show d07a5fd` and each ledger's
`### Round 2 — 488db00` rows, and asked for a compact review: new concerns only per plan, a
mandatory `## Cycle-2 finding status` table, the spec-review-checklist plan pass with a ponytail
lens and a real-HOME safety lens, locked CONTEXT/SPEC decisions not re-litigable, cheap-model
executability, path-agnostic commands and cross-AI reviewability. Both lanes were asked to stay
read-only.

referee-three is configured but has no quota, so it was not run. The two instances ran in
parallel through the `review-lane invoke --slug opencode --model <instance model> --as <instance>`
seam, effort `inherit`. No retry was needed.

- referee-one: lane 288 s, exit 0, 12/12 plan ids, 7/7 status rows.
- referee-two: lane 579 s, exit 0, 12/12 plan ids, 7/7 status rows, no router error.

Read-only breach (referee-two): its session shows it listed the real
`~/.local/share/systemd/timers` and `~/.local/state/systemd/timers` folders (names only) and ran
one live `systemd-analyze --user verify` under `env -i` on a stub unit in a scratch folder under
the system temp dir, which it removed in the same command (the orchestrator confirmed the folder is
gone). Nothing in the repo or in a real config was written. Its "live layout" and "live-checked"
evidence in 26-02 and 26-12 comes from those commands.

No model, provider or harness was changed. Both review texts below are verbatim.

## OpenCode Review (referee-one)

## 26-01

Ready; the shared contract includes `arm_id`.

No new concerns.

## 26-02

Revise: C2-H1’s pre-spawn fix is present, but the count mutation still has a stale-state window.

- HIGH — 26-02 Task 1: Step (3) checks `not_before` before step (4)’s serialized increment, but the increment does not revalidate either `arm_id` or `not_before`. A reset refresh landing between those steps can therefore be counted before its newly recorded reset. With `wake_count=23`, step (4) writes 24 and the live-host/finish path disarms the timer before that reset; the new checks at (7)/(9) are never reached. A disarm/re-arm in the same window similarly lets an old fire increment the replacement wake (evidence: .planning/phases/26-session-self-resume-and-opengsd-quota-rules/26-02-PLAN.md:291–315; the existing serialized mutation interface is defined at :142–146) — Fix: Inside the increment’s `update_state` callback, compare the current `arm_id` with the original and re-test the current `not_before` before changing the count. A replaced or deferred fire must return without incrementing or finalizing the replacement/deferred wake.

## 26-03

Ready; refresh explicitly preserves `arm_id`.

No new concerns.

## 26-04

Unchanged; no cycle-2 regression identified.

No new concerns.

## 26-05

Extend the interleaving coverage for the remaining C2-H1 window.

- HIGH — 26-05 Task 1: New cases (e)/(f) interleave at liveness and session probing, both **after** the count increment. They therefore miss the refresh/re-arm window between the initial `not_before` check and the increment described under 26-02 (evidence: .planning/phases/26-session-self-resume-and-opengsd-quota-rules/26-05-PLAN.md:140–157) — Fix: Add deterministic pre-increment interleavings: a same-arm reset refresh from count 23 must leave count 23 and every wake file intact; a disarm followed by a first arm must leave the replacement count at zero. Neither may resume or emit a give-up notice.

## 26-06

Unchanged; no cycle-2 regression identified.

No new concerns.

## 26-07

Unchanged; no cycle-2 regression identified.

No new concerns.

## 26-08

Ready; the cleared scratch environment addresses the inherited-environment defect.

No new concerns.

## 26-09

Unchanged; no cycle-2 regression identified.

No new concerns.

## 26-10

Unchanged; no cycle-2 regression identified.

No new concerns.

## 26-11

Ready; Task 2 now ends with `make test-unit` and its failure check.

No new concerns.

## 26-12

Ready; unit-lookup isolation, the R20 assertion, and step numbering are corrected.

No new concerns.

## Cycle-2 finding status

| Finding | Plan | Status | Evidence |
|---|---|---|---|
| C2-H1 | 26-01, 26-02, 26-03, 26-05 | PARTIAL | .planning/phases/26-session-self-resume-and-opengsd-quota-rules/26-02-PLAN.md:297–305 adds generation/reset checks before spawning, but :291–294 still increments without checking the current generation/reset inside the mutation. |
| C2-H2 | 26-02, 26-05 | FIXED | .planning/phases/26-session-self-resume-and-opengsd-quota-rules/26-02-PLAN.md:205–211 requires seven exact configured paths; .planning/phases/26-session-self-resume-and-opengsd-quota-rules/26-05-PLAN.md:234–236 tests foreign-folder collisions. |
| C2-H3 | 26-08 | FIXED | .planning/phases/26-session-self-resume-and-opengsd-quota-rules/26-08-PLAN.md:276–291 clears inherited variables, supplies scratch HOME/XDG/PATH, skips missing prerequisites, and asserts the checkout tools path. This addresses the inheritance in skills/ai-kit-project-rules-all/ai_kit_project_rules_all/dispatch.py:103–110 and resolver precedence in skills/ai-kit-spec-review/ai_kit_spec/gsd_tools.py:33–47. |
| C2-H4 | 26-12 | FIXED | .planning/phases/26-session-self-resume-and-opengsd-quota-rules/26-12-PLAN.md:123–132 specifies `env -i` and scratch HOME/XDG directories; :241–249 corrects the safety claims. |
| C2-L1 | 26-11 | FIXED | .planning/phases/26-session-self-resume-and-opengsd-quota-rules/26-11-PLAN.md:178 appends `make test-unit` and the `failed:` check. |
| C2-L2 | 26-12 | FIXED | .planning/phases/26-session-self-resume-and-opengsd-quota-rules/26-12-PLAN.md:145 asserts `s.get("R20") in ok`. |
| C2-L3 | 26-12 | FIXED | .planning/phases/26-session-self-resume-and-opengsd-quota-rules/26-12-PLAN.md:140–142 gives skill-judge verification its own numbered step. |

## Cross-plan assessment

- The GSD plan structure and serial 01→12 dependency chain remain consistent; no new ordering or interface gap was identified.
- QTA-04 and SPEC R4/R5 retain one correctness gap: counting is serialized, but its generation/reset eligibility check is not part of that serialized mutation.
- QTA-05/QTA-06 retain their implementation, remediation, test, and documentation coverage; settled cycle-1 findings were not reopened.
- The cycle-2 fixes are proportionate: one generation field, an exact-path predicate, and explicit verification environments. The remaining correction fits the already-planned `update_state` callback; it needs no additional lock or module.
- Overall risk: **HIGH** until the pre-increment interleaving is covered, because a newly deferred reset wake can be exhausted and removed prematurely.

## Remaining HIGH concerns

- **26-02 Task 1 / 26-05 Task 1:** Guard generation and reset eligibility inside the serialized count mutation, and test refresh/re-arm immediately before that mutation.

Not run: tests, model lanes, installers, timers, or user-config checks.  
Risk: this is a static plan review; runtime behavior remains unverified.

## OpenCode Review (referee-two)

Source confirms the C2-H3 premises (`dispatch.py:104-110` no `env`, `gsd_tools.py:38-47` RUNTIME_DIR→git toplevel). Now the changed plans in detail.
Verification complete. All fixes checked against repo source and live tool behavior.

## 26-01
Verdict: sound; the shared-list addition correctly propagates `arm_id` to every later plan. No new concerns.

## 26-02
Verdict: both C2 fixes landed correctly and completely (details in the status table). No new concerns.
- Verified consistent: `arm_id = secrets.token_hex(8)` → exactly the 16-lowercase-hex `validate_state` requires (26-02-PLAN.md:152,271); `ARM_WINDOW_S = 60` matches 26-05 case (e)'s "+60 s" (26-02-PLAN.md:137); the stamp path `${XDG_DATA_HOME:-…}/systemd/timers/stamp-<timer>` matches the layout of a live systemd 259 user manager, so the seventh `owned_path` derivation is factually right.

## 26-03
Verdict: sound; the refresh keeps `arm_id` so only a disarm + first re-arm changes it, exactly what `fire`'s step (7) compares. No new concerns.

## 26-04
Verdict (one line): unchanged by d07a5fd; consistent with the amended D-08/D-09/D-15/D-21/D-24 — no new concerns.

## 26-05
Verdict: cases (e)/(f) and the foreign-folder TestDisarm pin both C2-HIGHs precisely; acceptance updated to six cases. No new concerns.

## 26-06
Verdict (one line): unchanged; the reset re-arm rides 26-03's refresh (same `arm_id`, moved `not_before`), which is exactly the scenario 26-05 case (f) pins — consistent. No new concerns.

## 26-07
Verdict (one line): unchanged; `--only-if-armed` is a flag, so D-02's six-subcommand lock holds. No new concerns.

## 26-08
Verdict: the e2e real-HOME fix is correct and its premises verify at source. No new concerns.
- Source-verified: `dispatch.py:104-110` really passes no `env` (inherits `os.environ`), and `gsd_tools.py:38-47` really prefers `RUNTIME_DIR` then falls back to `git -C <start> rev-parse --show-toplevel` — so the rejected `RUNTIME_DIR`-pinning variant's justification ("with RUNTIME_DIR gone the resolver uses the git toplevel of the requested repo") is accurate, and the `git` symlink in the scratch PATH is exactly what that fallback needs. The moved `TestTracer` assertions are shape-level only (`tests/test_ai_kit_project_rules_all.py:76-102`: keys, no `failed`), so clearing PATH cannot flip them on presence data. `mock.patch.dict(os.environ, …, clear=True)` mutates the real process environ via putenv/unsetenv, so `subprocess.run(env=None)` children do inherit the scratch env.

## 26-09
Verdict (one line): unchanged; the Gradle rows match the locked 2026-10-28 D-27 amendment. No new concerns.

## 26-10
Verdict (one line): unchanged; executors call only `arm`/`done` (D-35) and single-plan runs arm nothing. No new concerns.

## 26-11
Verdict: C2-L1 fixed in the plan's last task. No new concerns.

## 26-12
Verdict: C2-H4, C2-L2, C2-L3 all fixed; live-checked that `systemd-analyze --user verify` actually runs under the prescribed `env -i` scratch HOME/XDG/runtime environment on this machine (systemd 259: it parsed a scratch unit file offline, no bus, no refusal — so the skip branch should not trigger here).
- LOW — 26-12 Task 1: the scratch-env `systemd-analyze --user verify` run exists only in the action text; the automated `<verify>` chain never re-runs it, so a tracer that drops the `env -i` wrapper or records a skip silently still passes the gate (evidence: the `<automated>` chain at 26-12-PLAN.md:142-144 contains no `systemd-analyze` invocation, while the action prescribes it at 26-12-PLAN.md:123-133) — Fix: append the invocation (redirecting output to `$D/verify.log`, with the recorded-skip path allowed) to the verify chain, or make the acceptance criteria require the SUMMARY to quote the verify log.

## Cycle-2 finding status

| Finding | Plan | Status | Evidence |
|---|---|---|---|
| C2-H1 | 26-02, 26-03, 26-05 | FIXED | `arm_id` minted at arm (26-02-PLAN.md:271), validated as 16-hex (26-02-PLAN.md:152), step (7) abandons on a different `arm_id` and re-tests `now < not_before`, step (9) repeats (26-02-PLAN.md:297-301); refresh keeps `arm_id` (26-03-PLAN.md:170-171); `TestFireInterleaving` cases (e) and (f), acceptance "six cases" (26-05-PLAN.md:154-161,170); shared list (26-01-PLAN.md:137-138) |
| C2-H2 | 26-02, 26-05 | FIXED | `owned_path(path, host, session_id, seams)` now requires one of the seven exact absolute paths derived from `seams.env` (26-02-PLAN.md:205-212); foreign-folder TestDisarm under `user`/`session-wake`/`timers`/`timers.target.wants` (26-05-PLAN.md:234-235); stamp path verified against the live systemd 259 layout |
| C2-H3 | 26-08 | FIXED | Task 2 step 3 (26-08-PLAN.md:269-292): `mock.patch.dict(os.environ, …, clear=True)` with scratch HOME/XDG and a PATH of `node`+`git` symlinks, skip without the checkout-local gsd-tools, `test_agents_probe_runs_the_checkout_gsd_tools` with realpath equality; verify gates `clear=True` and the test name; T-26-44 added. Premises confirmed at `dispatch.py:104-110` and `gsd_tools.py:38-47`; rejection of the `RUNTIME_DIR`-pinning variant is source-accurate |
| C2-H4 | 26-12 | FIXED | Task 1 step 2 runs `systemd-analyze --user verify` under `env -i` with scratch HOME and XDG config/data/runtime dirs (26-12-PLAN.md:123-133); T-26-38, trust boundary and ASVS lines corrected; live check confirms the command runs in that environment |
| C2-L1 | 26-11 | FIXED | Task 2's (the last task's) verify ends with `make test-unit` and `! grep -q '^failed: '` (26-11-PLAN.md:178-180) |
| C2-L2 | 26-12 | FIXED | Verify asserts `s.get("R20") in ok` beside R18/R19; truth says R20 must be evaluated (26-12-PLAN.md:26,142-144) |
| C2-L3 | 26-12 | FIXED | "3. Skill-judge at the tip" starts on its own numbered line (26-12-PLAN.md:137-139) |

## Cross-plan assessment
- Wave/depends_on order is unchanged and consistent: 01→02→03→04→05→06→07 and 08→09→10→11→12, with 26-05's tests pinning 26-02's fire order and 26-06's reset refresh riding 26-03's same-arm semantics.
- The `arm_id` contract is named consistently in every place that needs it: 26-01 shared list, 26-02 mint/validate/compare, 26-03 keep-on-refresh, 26-05 test cases, 26-06 reset re-arm (implicitly, by riding the refresh).
- All four cycle-2 HIGH fixes are proportionate under the ponytail lens — no fix grew beyond its defect (a field + two re-checks + two cases; seven exact paths; one env patch + one probe test; one `env -i` wrapper).
- QTA-04 covered by 26-01..07+10, QTA-05 by 26-08, QTA-06 by 26-09, evaluation/docs by 26-10/11/12; no SPEC R-item left uncovered.
- Real-HOME safety now holds everywhere it was questioned: 26-08's e2e tier is scratch-env'd and self-proving, 26-12's only live outside-scratch reads are read-only repo checks and a scratch-scoped `systemd-analyze`.
- Overall risk: **LOW**.

## Remaining HIGH concerns
None.

## Consensus Summary

Two prompt-fed reviewers ran with repo access and cited `file:line` evidence. Neither review opens
with a `[reviewed-without-source-citations]` or `[reviewed-without-repo-access]` marker, so both
count at full weight and the consensus gate applies. Each covered 12/12 plan ids and filled 7/7
status rows. The orchestrator re-checked the premise of every newly raised HIGH and every counted
actionable item against the plan text (see "Verification coverage").

Overall verdicts: referee-two says overall risk LOW, no HIGH, one LOW. referee-one says overall
risk HIGH with one remaining HIGH: the C2-H1 fix guards the pre-`Popen` re-checks but not the
step (4) count increment.

### Cycle-2 finding status

- referee-one: 6 FIXED, 1 PARTIAL (C2-H1), 0 NOT FIXED.
- referee-two: 7 FIXED, 0 PARTIAL, 0 NOT FIXED.
- Consensus (after the orchestrator's check of referee-one's PARTIAL row, premise confirmed):
  **6 FIXED, 1 PARTIAL (C2-H1), 0 NOT FIXED.** C2-H2, C2-H3, C2-H4 and C2-L1..C2-L3 are closed.

### Agreed Strengths

- `arm_id` is named consistently wherever it is needed: the 26-01 shared list, minted and
  validated in 26-02, kept by 26-03's refresh, and pinned by 26-05 cases (e) and (f).
- C2-H2 (seven exact absolute paths in `owned_path`), C2-H3 (the cleared scratch env in the e2e
  module, with the checkout-path probe test) and C2-H4 (`env -i` scratch HOME/XDG around
  `systemd-analyze`) are fixed, and both reviewers confirmed the 26-08 premises at
  `dispatch.py:104-110` and `gsd_tools.py:33-47`.
- Ponytail: the cycle-2 fixes are proportionate (one field and two re-checks, an exact-path
  predicate, one env patch, one `env -i` wrapper); the remaining HIGH fits the existing
  `update_state` callback with no new lock or module.

### Agreed Concerns

None raised by both reviewers this cycle.

### Divergent Views

- **C2-H1 (26-02 Task 1, 26-05 Task 1).** referee-two marks it FIXED; referee-one marks it PARTIAL.
  The orchestrator confirmed referee-one's premise at `26-02-PLAN.md:291-293`: step (3) tests
  `not_before` and step (4)'s `update_state` then increments `wake_count` with no `arm_id` or
  `not_before` check, while the new checks sit at (7) and (9) (`26-02-PLAN.md:297-305`). A refresh
  keeps `wake_count` (`26-03-PLAN.md:170-171`), so a reset refresh landing between (3) and (4) at
  count 23 is counted as wake 24 before its new `not_before`, and the alive-host `finish` then gives
  up a wake that was just deferred; a disarm plus first arm in the same window charges one wake to
  the new arm. 26-05 cases (e) and (f) interleave at (5) and inside `session_exists`, after the
  increment (`26-05-PLAN.md:150-161`). The window is short (file operations only between (1) and
  (4)), but this is a single-reviewer judgment-class HIGH with no discount marker, so it counts.

### Current HIGH Concerns (after the consensus gate)

Two reviewers ran with no discount marker, so the gate is engaged. The single HIGH comes from
referee-one alone; it is judgment-class, so it counts, and its premise is confirmed at source.
referee-one lists it under both 26-02 and 26-05; it is one concern. None is excluded.

1. **26-02 Task 1 / 26-05 Task 1 (C2-H1, PARTIAL): the step (4) count increment does not check
   `arm_id` or `not_before`.** Fix: inside step (4)'s `update_state` callback, compare the current
   `arm_id` with the one step (1) read and re-test `now < not_before` on the current state; on a
   different `arm_id` exit 0 without counting or finishing, and on a moved `not_before` log
   `fire before not_before <iso UTC>; not counted` and exit 0 without counting. Add two
   `TestFireInterleaving` cases that patch the step (4) `update_state` entry: (g) a same-arm reset
   refresh from count 23 leaves `wake_count` 23 and every wake file in place; (h) a disarm then a
   first arm leaves the new arm's `wake_count` 0; neither makes a host call or prints a give-up
   line. (referee-one; premise confirmed `26-02-PLAN.md:291-305`, `26-03-PLAN.md:170-171`,
   `26-05-PLAN.md:150-161`)

### Current Actionable Non-HIGH Concerns

1. LOW, 26-12 Task 1: the scratch-env `systemd-analyze --user verify` runs only in the action
   text (`26-12-PLAN.md:123-133`); none of the plan's three `<automated>` chains
   (`26-12-PLAN.md:145,188,218`) runs it, so dropping the `env -i` wrapper or recording a skip
   still passes. Fix: add the `env -i ... systemd-analyze --user verify` call to Task 1's verify
   chain, writing `$D/verify.log` and accepting either empty output with exit 0 or a recorded
   `skip:` line. (referee-two; confirmed)

### Verification coverage

Source-grounding pass (grep adapter), against the repo at d07a5fd:
`.planning/phases/26-session-self-resume-and-opengsd-quota-rules/26-02-PLAN.md:286-322`,
`26-03-PLAN.md:160-178`, `26-05-PLAN.md:138-162`, `26-12-PLAN.md:123-134,145,188,218`, and the
round-2 ledger rows of 26-01, 02, 03, 05, 08, 11 and 12. Verified: the counted HIGH premise and the
counted actionable item. Refuted: none. Not independently re-checked: referee-two's FIXED rows
beyond C2-H1, and its two live observations (the stamp path layout and `systemd-analyze` running
under `env -i`), which came from commands outside its read-only brief.
