---
phase: 21
reviewers: [opencode-plan-review]
reviewed_at: 2026-10-18T18:16:13Z
plans_reviewed: [21-01-PLAN.md, 21-02-PLAN.md, 21-03-PLAN.md, 21-04-PLAN.md, 21-05-PLAN.md, 21-06-PLAN.md, 21-07-PLAN.md]
models:
  opencode-plan-review: "router-env/my-plan-review"
model_sources:
  opencode-plan-review: "pinned"
---

# Cross-AI Plan Review — Phase 21

<!-- gsd:plan-revision-conflicts:begin -->
## Plan-Revision Conflicts
<!-- gsd:plan-revision-conflicts:end -->

Cycle 2, against the plan set at 71695d9 (replanned from cycle 1's review at 1354f43; seven
plans). Reviewer lane: `review.default_reviewers = ["opencode-plan-review"]` (reviewer instance
on the opencode adapter, model `router-env/my-plan-review`, no effort flag because
`review.effort.opencode` is `inherit`). The lane ran once, exit 0, empty stderr, about 7
minutes. Plan coverage: 7/7 ids. No evidence-quality discount marker. No prompt trimming.

## OpenCode Review (opencode-plan-review)

**Framework:** GSD · implementation plans  
**Review:** Convergence cycle 2, grounded in this worktree’s source and all seven current plans. Plan-file references below are relative to `.planning/phases/21-cursor-live-validation/`.

## 21-01

**Summary:** The main round-1 findings are addressed: `real_path` now covers refresh as well as initial construction, ASCII validation is explicit, and Plan 07 supplies the runner fix. One PATH edge still makes Python detection disagree with JavaScript dispatch.

**Strengths**
- The planned refresh change correctly targets the cached-row reconstruction in `skills/ai-kit-spec-review/ai_kit_spec/routing.py:269–299`.
- Preserves positional resolver callers and existing parser behavior while adding captured-output, ANSI and nameless-model cases.

**Concerns**
- **NEW · MEDIUM — Empty PATH segments have different semantics in detection and dispatch.** `21-01-PLAN.md:240–247` explicitly skips empty segments during the guarded scan. The runner preserves them as cwd through `dir || '.'` (`skills/ai-kit-spec-review/references/cross-ai.mjs:404–409`; retained by Plan 07). With `PATH=/grok/bin:` and a Cursor `agent` symlink in cwd, Python rejects the first Grok hit and skips cwd, while the runner finds Cursor.

**Suggestions**
- Preserve cwd semantics in the Python scan using `directory or os.curdir`, and add matching Python/runner tests for the trailing-empty-segment case.

**Risk Assessment: MEDIUM** — the common grok-first case is covered, but the claimed detection/dispatch agreement still has an executable exception.

## 21-02

**Summary:** Static file placement, explicit pins, bundle-style parsing and test-tier separation are well scoped. The live collision check, however, uses a discovery helper with a stronger version restriction than the plan recognizes.

**Strengths**
- Keeps Cursor model pins outside Claude’s `agents/` directory.
- The round-1 `query_agent_catalog(...) is None` issue is fixed by failing rather than skipping after discovery.
- The parity oracle’s limited scope is now stated accurately.

**Concerns**
- **NEW · MEDIUM — The catalog cross-check skips the installed 1.17.0 catalog.** `21-02-PLAN.md:287–306` treats any string from `real_gsd_paths()` as unavailable Node/gsd-core. That helper also returns a string whenever gsd-core is not **1.16.0**, and when config-schema support is missing (`tests/test_curated_config_e2e.py:94–110`). This phase uses 1.17.0, so the proposed test skips before querying its available catalog. The new `assertIsNotNone` does not cover this earlier exit.

**Suggestions**
- Discover only what this test needs: a working Node executable and the checkout-local model catalog. Do not reuse the golden-table 1.16.0 restriction.
- Require the cross-check to execute—not skip—in this phase’s recorded gate.

**Risk Assessment: MEDIUM** — the files and static checks are sound, but the advertised live collision proof currently does not run here.

## 21-03

**Summary:** The Cursor-first root and resolve-model-only chain address real harness gaps. Round-1 smoke exit propagation and specialist-override checks are addressed. One proposed baked-file assertion is broader than the helper actually enforces.

**Strengths**
- The one-entry host fix follows the existing insertion points in `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/host.py:61–75`.
- Avoids claiming that model-free Cursor files contain baked pins; the current comparison and rendering points are correctly identified in `tests/gsd_curated_eval.py:4315–4356,4739–4758`.
- The revised rehearsal command preserves the smoke’s exit status, and retry archiving keeps prior evidence.

**Concerns**
- **NEW · MEDIUM — “Every baked file is model-free” is not enforced by the proposed comparison.** `21-03-PLAN.md:317–337` builds `promised_map` from canonical catalog agents and says `_baked_mismatches` rejects any baked model. The helper iterates only `promised_map.items()` (`tests/gsd_curated_eval.py:4288–4298`), while `_baked_models` also returns compact files (`:4274–4285`). A compact or additional file carrying `model:` is ignored by that comparison; `_baked_lines` currently reports compact models as “not compared” (`:4751–4754`). A synthetic probe confirmed that a compact pin produces no mismatch. The later rehearsal artifact check catches this locally, but the reusable smoke assertion and “baked files verified model-free” wording remain incorrect.

**Suggestions**
- Keep the canonical-agent existence check, then separately reject every non-`None` value in the complete Cursor baked map.
- Include a negative test with a compact file carrying a model—not only another canonical agent.

**Risk Assessment: MEDIUM** — rehearsal artifacts provide a backstop, but future headless/interactive smoke runs could overstate the model-free result.

## 21-04

**Summary:** The plan substantially improves wrapper avoidance, isolation qualification and deletion guards. The remaining risks concern interrupted-run recovery and the actual lifetime of the credential-bearing scratch HOME.

**Strengths**
- The round-1 deletion guard, smoke exit propagation and qualified isolation statement are addressed.
- The corrected cleanup explanation matches runner `finalize`, which terminates child groups on normal exits too (`skills/ai-kit-spec-review/references/cross-ai.mjs:553–571`).
- The selected-attempt verdict is stronger than searching arbitrary evidence for success strings.

**Concerns**
- **NEW · HIGH — Scratch-HOME cleanup has no executable lifetime, and its timing conflicts with retries.** `21-04-PLAN.md:279–286` creates the HOME through separate commands; `:363–398` promises teardown on every exit and “immediately after the runner returns.” No enclosing trap/supervisor is specified. Setup errors or executor interruption can bypass cleanup. Conversely, immediate teardown removes the HOME needed by the subsequent probe/retry described at `:355–362`, with no recreation step. The runner cleans its child groups, not this externally created directory (`skills/ai-kit-spec-review/references/cross-ai.mjs:553–579`).

- **CARRIED-OVER · HIGH — Re-entry can still combine a new healthy runner result with old successful smoke outputs.** Archiving is specified only before attempt **N+1** (`21-04-PLAN.md:331–337`). Re-entry cleans the old HOME but restarts at attempt 1 without invalidating fixed smoke outputs; it also overwrites the original protection snapshot first (`:249–250,270–279`). A new healthy `no_change` invocation that never runs the wrapper can therefore reuse the old smoke log/evidence. The runner explicitly permits `no_change` without proving any requested command ran (`skills/ai-kit-spec-review/references/cross-ai.mjs:2907–2914,2940–2941`). This is distinct from the correctly rejected claim that `>` fails to truncate: **no truncation occurs if the wrapper is never invoked**.

- **NEW · MEDIUM — Process-proof verification can pass without process records.** The final loop skips missing PGID files. Runner bookkeeping failures are deliberately nonfatal (`skills/ai-kit-spec-review/references/cross-ai.mjs:499–508`). Thus the loop can pass vacuously, and it does not machine-check the separate escaped-worker absence promised by `21-04-PLAN.md:374–380`.

**Suggestions**
- Define one supervising script with cleanup for ordinary failures and catchable signals, plus durable recovery for forced termination.
- Choose an explicit HOME lifetime: recreate per dispatch, or retain until the final retry/probe finishes.
- Archive/invalidate outputs before the first dispatch on **every entry**, retain unique attempt identities, and check the interrupted run’s original snapshot before replacing it.
- Require spawn records for the selected attempt and a final scratch-HOME-matched worker absence check.

**Risk Assessment: HIGH** — stale evidence can authorize a false green result, and interruption/retry behavior can leave sensitive scratch state behind.

## 21-05

**Summary:** The round-1 attempt-binding, judge criteria and pending-orchestrator gate are addressed. The remaining blocker is a mismatch between what the plan calls R1 green and what the locked specification requires.

**Strengths**
- The PASS verifier now checks findings, score floors and each report’s digest.
- Uses the existing byte-bound digest mechanism in `tests/gsd_curated_eval.py:384–402,452–459`.
- Shipped wording honestly distinguishes headless validation from pending interactive confirmation.

**Concerns**
- **NEW · HIGH — LIFT substitutes headless preparation for the required interactive R1 acceptance.** `21-05-PLAN.md:227–234` selects LIFT solely from headless evidence and the matrix. But `21-SPEC.md:45–48` requires the smoke from the **user’s interactive Cursor session**, and `:55–58` permits lifting only after R1 and R2 pass. Plan 06 itself says the headless run only prepared R1 (`21-06-PLAN.md:294–297`). Narrower documentation wording does not amend that prerequisite.

**Suggestions**
- Either defer LIFT until interactive steps 1–4 pass, or obtain and record a formal SPEC amendment separating headless label eligibility from interactive acceptance.

**Risk Assessment: HIGH** — the plan can authorize the label transition before its stated prerequisite has occurred.

## 21-06

**Summary:** The exemption design and narrowed digest claims are much improved. Final closure still needs stronger acceptance and current-tree gates, and the optional probe retains an unsafe ownership inference.

**Strengths**
- Round-1 digest overclaim is resolved: the selected-key hash is described as limited integrity evidence.
- An unavailable pi judge now explicitly prevents completion.
- The snapshot-pipeline rejection is justified: current `_cmd_snapshot` cannot print `snapshot ok` on a strict failure (`tests/gsd_curated_eval.py:347–363`), and the planned change preserves that invariant.

**Concerns**
- **NEW · HIGH — Required interactive acceptance does not block phase completion.** `21-06-PLAN.md:496–512` records interactive acceptance as pending but requires `phase status: human_needed` **only** when the judge gate fails. With judge PASS and automated gates green, the phase can close while the required R1 run remains outstanding (`21-SPEC.md:45–48`). Listing it under Human verification is not a completion gate.

- **NEW · HIGH — Cursor agents, hooks and skills are absent from the claimed protection.** The plan adds the config exemption, but not the Cursor entries identified in research. `_strict_files` protects only `.cursor/cli-config.json`; `_strict_listings` and `snapshot` add no Cursor agents/hooks/skills coverage (`tests/gsd_curated_eval.py:189–226,292–321`). A synthetic mutation of Cursor agents and `hooks.json` produced no snapshot difference. Consequently, `snapshot ok` cannot substantiate the broader no-write assurance in `21-06-PLAN.md:301–315`.

- **NEW · HIGH — The final judge gate accepts a stale PASS after later skill fixes.** `21-06-PLAN.md:447–458` accepts the stored verdict while permitting gate-driven fixes. Its final verifier does not recheck the current digest or report criteria. A later change to `SKILL.md` or `references/` invalidates the judged bytes (`tests/gsd_curated_eval.py:384–402`), but the old PASS string remains sufficient.

- **CARRIED-OVER · HIGH — Manual probe cleanup still mistakes age for ownership.** Automatic killing is removed, but `21-06-PLAN.md:358–367` calls newly appearing, younger workers “the probe’s leftovers” and instructs the user to kill them. A concurrent session’s new worker satisfies the same criterion. The plan acknowledges that ambiguity; the actual ownership precedent used a scratch-HOME environment check (`21-SPIKE-D01.md:25–27`).

- **NEW · MEDIUM — The optional model probe extracts arbitrary model fields, not the Task call.** The `grep` at `21-06-PLAN.md:358` discards event/tool context and can match a model elsewhere in the stream. Subsequent cleanup also obscures the CLI exit status. That is insufficient evidence for the per-call-selection conclusion at `:364–370`.

- **NEW · MEDIUM — Digest and snapshot may protect different config files.** The digest honors `CURSOR_CONFIG_DIR` (`21-06-PLAN.md:118–120`), whereas the snapshot always protects `<home>/.cursor/cli-config.json` (`tests/gsd_curated_eval.py:210,298–301`). No default-directory precondition or consistent custom-path handling is specified.

**Suggestions**
- Keep the phase `human_needed` until required interactive acceptance passes, independently of judge status.
- Add explicitly scoped Cursor protected entries with synthetic mutation tests; state whether directory checks cover names or contents.
- Reuse Plan 05’s complete digest/report validation at final closure, rejudging changed bytes.
- Label probe workers as **unidentified candidates** unless ownership is established; never recommend termination by age alone.
- Parse the actual Task-call event and preserve command status.
- Either support one consistently resolved config path or reject non-default `CURSOR_CONFIG_DIR` for this validation run.

**Risk Assessment: HIGH** — phase completion, protection claims and probe evidence can exceed what the executable checks establish.

## 21-07

**Summary:** Adding the runner mirror and tracked render resolves the central round-1 dispatch mismatch. Two verification instructions nevertheless reject a correct upgrade.

**Strengths**
- Correctly follows the newer-template rule in `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cross_ai_script.py:242–265`.
- Preserves CONFIG through the existing upgrade path and includes pins, goldens and the tracked render.
- Covers the grok-first PATH case hermetically.

**Concerns**
- **NEW · HIGH — The final snapshot necessarily rejects the authorized runner rewrite.** The baseline is captured before Task 1 (`21-07-PLAN.md:238`), then Task 2 upgrades `.planning/scripts/cross-ai.mjs` and requires the original snapshot to remain unchanged (`:327–350,356`). That exact runner is strict (`tests/gsd_curated_eval.py:198`); changed bytes produce a failed snapshot (`:332–363`). A synthetic probe confirmed the expected failure.

- **NEW · HIGH — CONFIG preservation compares against the wrong revision before commit.** `21-07-PLAN.md:333–336,355` selects the older of the last two runner commits. Before the planned commit, those are `4e53b3e` and `ef2daf6`, so it selects `ef2daf6`, not the actual pre-upgrade runner. That older CONFIG lacks keys preserved by `_upgrade_config` (`skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cross_ai_script.py:227–235`). The comparison therefore fails before commit even when preservation is correct.

**Suggestions**
- Save the actual pre-upgrade runner bytes under `tmp/p21/` and compare CONFIG against those, independent of commit timing.
- Verify that the protected-set delta is **exactly the authorized runner change**, require every other entry unchanged, and only then establish the next baseline.

**Risk Assessment: HIGH** — otherwise-correct execution is blocked by deterministic verification failures.

## Overall assessment

**Coverage: 7/7 plans. Status: Issues Found — revise before execution.**

The round-1 revisions resolve most original findings. The highest-priority remaining changes are:

1. Fix Plan 07’s two deterministic upgrade gates.
2. Make Plan 04’s cleanup/re-entry lifetime executable and invalidate stale evidence on every entry.
3. Reconcile interactive acceptance with label lifting and phase completion.
4. Complete Cursor protection and validate the final judge verdict against the final bytes.

No repository files were changed. No live AI CLI or full test/build suite was run; verification used source tracing and small synthetic probes.

---

## Consensus Summary

One reviewer ran, so there is no cross-reviewer consensus and the convergence consensus gate
does not apply: every HIGH counts unless the orchestrator spot-check shows it inaccurate. The
reviewer raised 9 HIGH (2 carried over from cycle 1, 7 new) and 6 MEDIUM concerns, and judged
every other cycle-1 finding resolved by the Round 1 ledgers.

Orchestrator spot-checks against source (verification only, no disposition):

- Confirmed, 21-07 snapshot gate: Task 1 captures `tmp/p21/plan07.before.json` before the
  rewrite (`21-07-PLAN.md:238`), Task 2 re-renders `.planning/scripts/cross-ai.mjs` and its
  verify requires `snapshot --check tmp/p21/plan07.before.json` to print `snapshot ok`; that
  file is a strict entry (`tests/gsd_curated_eval.py:198`), so the gate fails on a correct run.
- Confirmed, 21-07 CONFIG revision: the action's pre-commit check takes the older of
  `git log -2 -- .planning/scripts/cross-ai.mjs`, which today is `ef2daf6`, not `4e53b3e` as
  the plan states. `template_config` of `ef2daf6` lacks `effort`, `extraArgs`,
  `outerTimeoutS` and `routerBacked` compared with `4e53b3e` (checked), so the pre-commit
  comparison fails. The post-commit `<verify>` picks the right revision.
- Confirmed, 21-05/21-06 interactive acceptance: `21-SPEC.md:45-48` makes R1 the user's
  interactive session and `:55-58` lifts the label only after R1 and R2 pass. 21-05 selects
  LIFT from headless evidence; 21-06 writes `phase status: human_needed` only when the judge
  gate fails. Phase 20 lifted the codex label on headless evidence, but its SPEC had no
  label requirement; Phase 21's does.
- Confirmed, 21-06 Cursor protection: the snapshot's only Cursor entry is
  `<home>/.cursor/cli-config.json` (`tests/gsd_curated_eval.py:207-210,292-321`).
  `21-RESEARCH.md:364` (T-21-02) proposed listings for `agents/`, `skills/` and `hooks.json`;
  no plan adds them, yet 21-04's `## Session` and 21-06's script say the `~/.cursor`
  allowlist is proven unchanged.
- Confirmed, 21-06 stale judge PASS: Task 2 checks only the stored verdict line and the
  pending-marker precondition, not the current `digest`.
- Confirmed, 21-06 probe ownership: step 5 tells the user that new workers younger than the
  probe are its leftovers to kill; a concurrent session's new worker meets the same test.
- Confirmed, 21-04 re-entry stale outputs: outputs are archived only before attempt N+1; a
  re-entry restarts at attempt 1, re-captures `plan04.before.json` and leaves the old
  `cursor-smoke.log`/`.md` in place. A `no_change` run that never invokes the wrapper would
  then derive its verdict from the old files.
- Mostly inaccurate, 21-04 scratch-HOME lifetime: the teardown list already runs after the
  probe and the retries, a setup-guard failure runs the teardown, and interruption is covered
  by the re-entry teardown and 21-06's late teardown. What remains is the wording "it runs
  immediately after the runner returns", which contradicts that order. Counted as a MEDIUM.
- Confirmed MEDIUMs: 21-02 `real_gsd_paths()` returns a reason string unless gsd-core is
  1.16.0 (`tests/test_curated_config_e2e.py:94-110`) and this checkout has 1.17.0, so the new
  catalog test skips here. 21-03 `_baked_mismatches` iterates only `promised_map`
  (`tests/gsd_curated_eval.py:4288-4298`). 21-01 skips empty PATH segments while the runner
  maps them to `.`. 21-04 vacuous pgid loop, 21-06 probe `grep` and the `CURSOR_CONFIG_DIR`
  mismatch: plan text matches the reviewer's reading; not re-traced further.

### Agreed Strengths
- Single reviewer. It judged most cycle-1 findings resolved: `real_path` on refresh, ASCII ids,
  the runner scan-all mirror (21-07), the catalog `None` failure, smoke exit capture,
  specialist-override checks, the path guard, the qualified isolation wording, the attempt-bound
  verdict line, the judge `CRITICAL`/`IMPORTANT`/digest checks, the narrowed digest claim and
  the BLOCKED-judge handling. It accepted the snapshot-pipe rejection.

### Agreed Concerns
- Not applicable with one reviewer. Highest priority: the two deterministic 21-07 gate
  failures; stale smoke evidence on 21-04 re-entry; reconciling the headless LIFT and phase
  completion with SPEC R1/R3 (21-05, 21-06); Cursor protection and the final judge digest
  (21-06).

### Divergent Views
- None (one reviewer).
