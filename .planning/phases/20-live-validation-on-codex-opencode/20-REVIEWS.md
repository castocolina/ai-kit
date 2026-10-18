---
phase: 20
cycle: 2
reviewers: [opencode-plan-review]
reviewed_at: 2026-10-18T03:12:35Z
plans_reviewed: [20-01-PLAN.md, 20-02-PLAN.md, 20-03-PLAN.md, 20-04-PLAN.md, 20-05-PLAN.md, 20-06-PLAN.md, 20-07-PLAN.md]
models:
  opencode-plan-review: "router-env/my-plan-review"
model_sources:
  opencode-plan-review: "pinned"
---

# Cross-AI Plan Review — Phase 20

<!-- gsd:plan-revision-conflicts:begin -->
## Plan-Revision Conflicts
<!-- gsd:plan-revision-conflicts:end -->

Convergence cycle 2, against the replan at 7a87de3 (commits 4181b02, c09fdc4, a81e5ce, 7a87de3).
Cycle 1 (6 plans, commit 47d6b7c) is summarized in "Cycle 1 dispositions" at the end; its full
text is at `git show 47d6b7c:.planning/phases/20-live-validation-on-codex-opencode/20-REVIEWS.md`.

Reviewer lane: `review.default_reviewers = ["opencode-plan-review"]` (reviewer instance on the
opencode adapter, model `router-env/my-plan-review`, no effort flag: `review.effort.opencode` is
`inherit` on purpose because gsd-core renders `--variant`, which opencode v2 removed). The lane ran
once with `opencode run --standalone`, exit 0, empty stderr, about 8 minutes. Plan coverage: 7/7
ids. No evidence-quality discount marker.

## OpenCode Review (opencode-plan-review)

### Document type
GSD · implementation plans · convergence cycle 2 · read-only, source-grounded review

All seven current plans and `20-REVIEWS.md` were read from disk and checked against relevant source. Plan citations below use **`P/` = `.planning/phases/20-live-validation-on-codex-opencode/`**.

## 20-01

### Summary
The runner migration is substantially improved: the version bump now distributes `--standalone` to existing installations, and the repository render is repaired before later plans dispatch. The remaining material issue is rollback ownership: detecting changed bytes does not establish that those bytes belong to this task.

### Strengths
- **Uses the existing migration mechanism correctly.** `P/20-01-PLAN.md:195-225` updates the template, version constant, pins and golden artifacts together. This matches the older-version upgrade branch in `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cross_ai_script.py:242-265`.
- **Covers resume through the shared argv builders.** Opencode resume derives from exec/review builders, so adding the flag there covers resumed calls too (`skills/ai-kit-spec-review/references/cross-ai.mjs:276-281`).
- **Adds tests at both existing lane-policy enforcement points**, rather than introducing another policy implementation (`P/20-01-PLAN.md:287-303`).

### Concerns
- **MEDIUM — Rollback can still discard concurrent or pre-existing work.** `P/20-01-PLAN.md:227-248` records a checksum, then prescribes `git checkout` whenever the checksum changes. A concurrent edit also changes that checksum; checkout restores the index version, not the saved starting bytes. This undermines the generator’s explicit concurrent-change preservation (`skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cross_ai_script.py:381-391`). Likewise, “`.new` did not exist initially” does not prove a subsequently appearing file is task-owned.
- **MEDIUM — The acceptance grep rejects an intentionally retained compatibility comment.** `P/20-01-PLAN.md:267` requires no `template 3` text anywhere under the skill, while `:208-209` deliberately retains the readiness floor. Its existing explanation contains exactly that text (`skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cross_ai_script.py:29-31`).

### Suggestions
- Save initial bytes and restore them only when the current file matches a known task-produced output; preserve unexpected concurrent content.
- Restrict current-version checks to current-version pins, excluding the valid template-3 readiness-floor explanation.

### Cycle-1 disposition
- **Version bump:** resolved by `P/20-01-PLAN.md:195-225`.
- **Unsafe bootstrap:** explicitly accepted, not eliminated, at `:98-108,250-253,339`. This is a recorded residual risk, not a completed mitigation.
- **Destructive cleanup:** partially resolved; pre-existing `.new` is protected, but concurrent ownership remains unresolved.

### Risk assessment
**MEDIUM.** The migration design is sound, but its failure recovery can still destroy unrelated work.

## 20-02

### Summary
The four-case tier rule resolves the earlier Claude regression, and the non-Claude negative control preserves independent expectations. Two oracle boundaries remain incomplete: subprocess success is not validated, and a missing runtime-tier mapping is incorrectly equated with inheritance.

### Strengths
- **Correctly preserves Claude override behavior.** The explicit cases at `P/20-02-PLAN.md:187-196` match gsd-core’s alias/concrete-override behavior (`.claude/gsd-core/bin/lib/model-resolver.cjs:438-451`).
- **Keeps the negative control independent.** The altered config is compared against the original plan’s promise (`P/20-02-PLAN.md:197-207`).
- **Separates unavailable tables from loaded-but-empty maps** (`P/20-02-PLAN.md:162-178`).

### Concerns
- **HIGH — Failed resolver execution can still supply passing evidence.** The plan changes comparison semantics without fixing `_resolve_model`. That helper uses `check=False`, never checks `returncode`, and accepts parsed stdout (`tests/gsd_curated_eval.py:632-648`). A nonzero resolver exit carrying otherwise matching model/tier JSON therefore passes. `live_tables` has the same missing exit-status check (`:444-467`).
- **MEDIUM — Missing runtime-tier data does not necessarily mean an empty model.** `P/20-02-PLAN.md:172-178,212-215` promises `""` whenever no applicable map entry exists. In gsd-core, failed runtime-tier resolution returns `""` only when the omission gate applies; otherwise resolution continues to a tier/profile fallback (`.claude/gsd-core/bin/lib/model-resolver.cjs:600-618,652-669`).

### Suggestions
- Require successful subprocess completion and valid result fields before treating output as resolution evidence; add nonzero-with-valid-JSON regression cases.
- Include omission policy in the empty-promise rule, or explicitly refuse unsupported missing-map configurations. Test missing entries both with and without omit.

### Cycle-1 disposition
- **Claude override-tier regression:** resolved by `P/20-02-PLAN.md:187-223`.
- **Unavailable/malformed runtime map becomes inheritance:** resolved for absent/non-dict top-level maps at `:162-178`; execution-failure and missing-entry semantics still need the corrections above.

### Risk assessment
**HIGH.** An acceptance oracle must not report successful resolution from an unsuccessful subprocess.

## 20-03

### Summary
The revised smoke design addresses the principal false-positive installation risk. Exact-root assertions, project-scoped environments and retained artifacts are strong improvements. The remaining guard issue is semantic normalization: removing a scratch trust entry can still change the serialized TOML representation, and outer snapshot checks do not share the smoke’s exemption.

### Strengths
- **Proves the selected installation, not merely a matching version.** `P/20-03-PLAN.md:212-241` removes `RUNTIME_DIR` and asserts the exact scratch root. This addresses the real precedence mechanism in `skills/ai-kit-spec-review/ai_kit_spec/gsd_tools.py:33-47` and `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/host.py:126-136`.
- **Contains inherited XDG paths at the installer boundary** (`P/20-03-PLAN.md:219-233`). This matters because gsd-core’s data-directory fallback reads `XDG_DATA_HOME` (`.claude/gsd-core/bin/lib/opencode-version.cjs:409-435`).
- **Exports the required analysis inputs before cleanup** (`P/20-03-PLAN.md:385-397`), fixing the prior artifact-loss design.
- **Improves directory protection honestly:** agent/command tree hashes versus explicitly names-only skills/plugins (`:319-345`).

### Concerns
- **MEDIUM — Removing the first scratch trust table can still alter the semantic hash.** `P/20-03-PLAN.md:310-318` drops scratch project keys but does not specify normalization of the now-empty `projects` container. Starting with `model = "x"` and then adding/removing the only scratch trust entry can leave `{"model":"x","projects":{}}`, which hashes differently from `{"model":"x"}`. A read-only Python check reproduced this representation difference. The proposed regression at `:337-339` should explicitly cover a baseline with no `projects` table.
- **MEDIUM — The outer snapshot command rejects the scratch trust writes that the smoke permits.** The smoke passes `(work,)`, but snapshot CLI calls pass no exemptions (`P/20-03-PLAN.md:316-318`). Later procedures require the external baseline check to print `snapshot ok`, including the interactive check (`P/20-07-PLAN.md:218-223`). An allowed trust write can therefore pass the smoke and fail its required outer guard.

### Suggestions
- Normalize absent/empty `projects` consistently while preserving unrelated tables.
- Define a run-owned scratch-root manifest or equivalent explicit exemption for outer checks. Do not broaden it to every temporary project.

### Cycle-1 disposition
- **Wrong scratch installation selected:** resolved by `P/20-03-PLAN.md:212-241`.
- **Installer probes omitted from isolation/threat model:** addressed by `:95-101,219-233,449`; actual CLI behavior remains a live verification.
- **Overbroad temp-prefix exception:** resolved by path-aware run-owned roots at `:310-318`.
- **Names-only guard overclaims byte identity:** resolved by `:319-345`.
- **Deleted return artifacts:** resolved in design by `:385-397`.
- The earlier empty-promise/`None` concern remains **not counted as a separate blocker**: Task 3 explicitly requires omission for empty Opencode promises (`:369-374`).

### Risk assessment
**MEDIUM.** The central smoke architecture is improved, but legitimate trust persistence can still produce contradictory guard outcomes.

## 20-04

### Summary
Evidence-only success now matches the runner’s `no_change` semantics, and controlled PATH enumeration addresses the unrelated Cursor write. The signal probe remains deterministically misdirected, however, and some promised timeout protection never reaches executable commands or the delegated prompt.

### Strengths
- **Correct success semantics:** `P/20-04-PLAN.md:220-227` accepts healthy `no_change` and independently requires smoke success.
- **Enumeration is genuinely host-scoped.** The controlled PATH at `:318-323` matches PATH-based discovery (`skills/ai-kit-spec-review/ai_kit_spec/detection.py:183-188,1003-1010`).
- **Uses child-PGID recording and a run-owned TMPDIR**, correcting the previous process-group and temp-prefix mistakes (`P/20-04-PLAN.md:366-381`).

### Concerns
- **HIGH — Readiness watches the first Git child, not the Codex execution child.** `P/20-04-PLAN.md:369-370` selects the first `spawn` record forever. The runner executes `treeState` before host execution (`skills/ai-kit-spec-review/references/cross-ai.mjs:2853-2859`); that starts Git children (`:716-740`), and every child is recorded (`:580-588`). The selected PID normally belongs to an already-exited Git process. The following fixed 15-second wait also does not prove the requested `sleep` tool operation began.
- **HIGH — Timeout containment remains incomplete.** The direct event command at `P/20-04-PLAN.md:308` and inventory commands at `:318-325` lack the promised timeout wrapper. The remaining-budget instruction at `:163-174` sits outside `<objective>`/`<tasks>`, while GSD constructs the delegated prompt from those sections (`.claude/gsd-core/workflows/execute-phase/detail/elaboration.md:84-87`). A parent deadline must not terminate unfinished detached probes.
- **MEDIUM — “Signals clean” checks only a filtered subset.** The dump at `P/20-04-PLAN.md:209-210` excludes `PI_CODING_AGENT`, `CURSOR_AGENT` and `GROK_AGENT`, despite their presence in the scrub set (`skills/ai-kit-spec-review/references/cross-ai.mjs:77-88`). The assertion at `:247` cannot detect their leakage.
- **MEDIUM — The out-of-scratch trust exception contradicts the guard.** `P/20-04-PLAN.md:176-179` says such a write is not a guard failure; `:238-240,280-281` still requires unchanged snapshot output. Plan 03 explicitly gives snapshot CLI calls no exemption.

### Suggestions
- Identify a live target execution child, exclude Git/listing children, and observe the long-running tool operation before signalling.
- Put executable deadlines, remaining-budget checks and cleanup/continuation rules inside dispatched task instructions.
- Capture the complete names-only set for signal assertions.
- Give unexpected trust writes one consistent blocked/accepted outcome.

### Cycle-1 disposition
- **Impossible `ok` requirement:** resolved at `P/20-04-PLAN.md:220-227`.
- **Own generic marker rejected:** resolved at `:247-252`.
- **Unrelated runtime enumeration:** resolved at `:318-323`.
- **Signal cleanup proof:** partially resolved; readiness remains broken.
- **Parent/child timeout mismatch:** partially resolved by smaller deadlines and splitting; unwrapped probes remain.

### Risk assessment
**HIGH.** The planned signal evidence cannot reliably be gathered using the specified readiness command.

## 20-05

### Summary
The Opencode plan preserves appropriate uncertainty about effort application and loader precedence. It inherits the signal and supervision defects from 20-04. Its overall bounded work can also exceed the enclosing dispatch even without retries.

### Strengths
- **The `#high` probe reaches execution rather than being inherently blocked by preflight.** The runner strips the suffix for listing membership, then executes the original model string (`skills/ai-kit-spec-review/references/cross-ai.mjs:2860-2881`).
- **Acceptance is not overstated as effort application** (`P/20-05-PLAN.md:275-286`).
- **Required lane trials and loader proof are routed to interactive work**, without claiming headless acceptance (`:229-239`).

### Concerns
- **HIGH — Signal readiness inherits the first-spawn defect.** `P/20-05-PLAN.md:325-330` mirrors 20-04’s procedure; the first recorded child is normally Git, not Opencode.
- **HIGH — The allowed work exceeds the parent budget, and enumeration is unwrapped.** The advertised bounds total 930 + 150 + three 300-second probes = **1,980 seconds**, before overhead (`P/20-05-PLAN.md:79-83`). The inventory command at `:288-289` has no wrapper. The stop-before-budget-exhaustion paragraph at `:153-164` is outside the sections GSD dispatches.
- **MEDIUM — Signal and snapshot proof gaps also carry over.** The filtered dump/check (`P/20-05-PLAN.md:197-200,215-218`) misses several foreign signal names; the trust exception at `:166-169` contradicts the unchanged-snapshot gate at `:250-251`.
- **LOW — Enumeration is more than a shared-service listing.** The product also starts an owned private server for image-capability probing (`skills/ai-kit-spec-review/ai_kit_spec/detection.py:1011-1019,796-847`). The evidence should account for that process rather than describe enumeration solely as `opencode models` (`P/20-05-PLAN.md:287-294`).

### Suggestions
- Apply the corrected readiness and full names-only checks from 20-04.
- Bound each command and explicitly hand unfinished probes back to the orchestrator before starting work that cannot fit.
- Include the private capability-probe server in process accounting.

### Cycle-1 disposition
- **`no_change` semantics and own-marker allowance:** resolved at `P/20-05-PLAN.md:202-218,278-286`.
- **Unrelated CLI enumeration:** resolved by controlled PATH at `:287-294`.
- **Signal proof and timeout:** partially resolved, for the reasons above.
- **Mandatory trials:** restored as REQUIRED at `:230-239`; their executable procedure is reviewed under 20-07.

### Risk assessment
**HIGH.** Supervision and signal readiness remain blockers despite improved evidence semantics.

## 20-06

### Summary
The certainty updates are much better scoped, especially the distinction between cached-installer verification and the shipped registry launcher. Completion rules still conflict, and the replacement-signal branch does not synchronize additions across the derived scrub set and its mirrors.

### Strengths
- **Installer claims now match the exercised path** (`P/20-06-PLAN.md:320-325`), unlike the shipped `npx` follow-up and its disclosures (`skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/followups.py:181-188`).
- **PASS/KEPT branches permit honest uncertainty** (`P/20-06-PLAN.md:312-316,371-378`).
- **Headless absence no longer silently removes a TUI-unconfirmed signal** (`:224-238`).

### Concerns
- **HIGH — Judge completion rules conflict and waive baseline non-regression.** `P/20-06-PLAN.md:436-438` permits an unavailable pi judge under the phase rule, but `:447-450` requires a passing pi row for PASS. Separately, `:443-444` calls baseline scores “reference, not a floor,” while `AGENTS.md:45-47` requires no regression versus baseline. A score of 96 can satisfy this plan while falling below the recorded 109/114 scores.
- **MEDIUM — Replacement additions leave scrub mirrors inconsistent.** `P/20-06-PLAN.md:233-238` adds a replacement such as `CODEX_SESSION_ID` but says mirrors remain untouched because no name was dropped. `HOST_SIGNAL_ENV_VARS` derives from all host signals (`skills/ai-kit-spec-review/ai_kit_spec/detection.py:191-205`); additions therefore require synchronization too. The template remains literal (`skills/ai-kit-spec-review/references/cross-ai.mjs:77-89`).
- **MEDIUM — Per-attempt limits do not bound the permitted judge loop.** Retries and two fix rounds can exceed the parent’s 1,800 seconds (`P/20-06-PLAN.md:407-442`). Three 630-second attempts alone exceed it.

### Suggestions
- Define one PASS/BLOCKED/FAILED/PENDING decision table and retain the repository’s baseline non-regression rule.
- Synchronize every signal-set change, including additions; a missing new scrub entry is not a harmless superset.
- Place remaining-budget checks and orchestrator continuation inside Task 3 before retries or fix rounds.

### Cycle-1 disposition
- **Dropped-signal mirror drift:** resolved for the normal keep/drop design at `P/20-06-PLAN.md:249-263`; replacement additions introduce the new gap above.
- **Installer overclaim:** resolved at `:320-325`.
- **Conditional wording versus unconditional acceptance:** resolved by `:312-378`.
- **Judge timeout:** partially resolved; individual attempts fit, cumulative paths need supervision.
- **SC3 default-only branch:** conservatively pinned at `:270-274`; no unsupported native-selection capability is claimed.

### Risk assessment
**HIGH.** The plan currently admits incompatible interpretations of whether the skill gate has passed.

## 20-07

### Summary
The handoff now retains artifacts and restores required interactive work. However, the required loader commands fail at shell redirection, the review trials use the wrong phase syntax, and loader observation still depends on an unverified output contract. These prevent reliable closure of EVAL-05.

### Strengths
- **Returns the required analysis artifacts** through `--artifacts-out` (`P/20-07-PLAN.md:210-217,271-275`).
- **Makes lane trials and loader observation REQUIRED** (`:224-265`), matching D-11.
- **Reads counts from the actual output format.** The module summaries used by the plan are produced at `tools/run_unittest_parallel.py:213-224`.
- **Docker now has a persisted exit-status gate**, rather than merely a nonempty log (`P/20-07-PLAN.md:367-371`).

### Concerns
- **HIGH — Loader redirection targets nonexistent scratch-relative directories.** `P/20-07-PLAN.md:247-255` runs inside `<dir>/project-a` but redirects to `tmp/p20/interactive/...`, created only in the checkout. The scratch builder does not create that path (`tests/gsd_curated_eval.py:3915-3929`). Redirection fails before either loader command runs.
- **HIGH — Lane trials use the wrong phase argument and an underspecified fallback project.** The script uses `/gsd-review 20` (`P/20-07-PLAN.md:235-239`), but the installed command declares `--phase N` (`.claude/commands/gsd-review.md:4`), and its workflow extracts only `--phase` (`.claude/gsd-core/workflows/review.md:156-159`). The fallback “any GSD project” need not contain phase 20. A prerequisite failure must not count as a host-lane self-skip.
- **HIGH — Loader evidence is assumed rather than defined, and closure is insufficiently conditional.** `P/20-07-PLAN.md:247-265` assumes JSON events expose resolved model fields merely because `--agent` exists. The fallback reads a shared service whose association with the kept scratch project is not established. Only `gsd-planner` is observed, whereas D-07 specifies the chain per agent (`P/20-CONTEXT.md:116-119`). Nevertheless, `P/20-07-PLAN.md:274-277` proceeds to EVAL check-off without requiring satisfactory precedence evidence.
- **MEDIUM — The dry-run requires a raw artifact that is never exported.** `P/20-07-PLAN.md:293-298` expects a baked Markdown agent file in the headless artifact directory. Plan 03 exports only four JSON files (`P/20-03-PLAN.md:388-397`), and normal cleanup deletes the original agent file (`tests/gsd_curated_eval.py:4358-4359`).
- **MEDIUM — Aggregate gate verification still accepts incomplete logs.** Unlike Docker, `make test`, `make validate` and the verbose unittest command do not persist their exit status. The final verifier checks selected passing lines (`P/20-07-PLAN.md:405-409`), which can survive a later failure or terminated aggregate run.

### Suggestions
- Capture a durable checkout output path before changing directories, then syntax-check the complete command in its intended cwd.
- Use `--phase <actual-phase>` and prepare a complete reviewable scratch phase; distinguish self-skip from missing prerequisites.
- Define a first-observation branch that establishes loader fields and project/session association. Leave R5/EVAL-05 pending when that proof is unavailable.
- Use a synthetic frontmatter fixture for syntax checks, or explicitly export the required raw agent file.
- Persist and verify exit codes for all aggregate gates, keeping count/log checks as additional evidence.

### Cycle-1 disposition
- **Artifact loss:** resolved by export; the raw-Markdown dry-run mismatch is new.
- **Mandatory evidence demoted to optional:** restored at `P/20-07-PLAN.md:224-265`, but invocation and loader-proof defects remain.
- **Wrong test-count output assumptions:** resolved at `:346-361`.
- **Docker accepts any nonempty log:** resolved at `:367-371`.
- **D-07 singular command drift:** amendment supplied at `:299-306`; its replacement evidence contract still needs validation.

### Risk assessment
**HIGH.** The human procedure can fail before collecting evidence or produce observations insufficient to close acceptance.

## Overall assessment

### Status: Issues Found — revise before execution

**Coverage: 7/7 plans reviewed.**

The replan resolves most cycle-1 structural problems. The architecture can remain: extend the existing harness, use the external installer, retain independent expectations, and distinguish headless preparation from interactive acceptance.

Highest-priority corrections:

1. Fix signal readiness so it targets the live execution child.
2. Make deadlines and continuation rules executable within the delegated prompt.
3. Reject unsuccessful subprocess output as oracle evidence.
4. Repair interactive command paths and `/gsd-review --phase` syntax.
5. Require actual loader/project-associated evidence before closing EVAL-05.
6. Reconcile judge completion and baseline rules.
7. Make snapshot exemptions consistent across inner and outer guards.

Skipped: implementation, full test execution, live host/model calls and credential access; no repository files were modified.  
Residual risk: actual CLI behavior remains unverified, and the current procedures can still produce false failures or incomplete acceptance evidence.

---

## Consensus Summary

One reviewer ran this cycle, so there is no cross-reviewer consensus and the consensus gate is
skipped; a single reviewer's HIGH counts. The review cites `file:line` evidence throughout and
carries no evidence-quality discount marker. The orchestrator re-checked every claim below against
the current plan text and the source before counting it.

### Agreed Strengths
- The replan resolves 10 of the 12 cycle-1 HIGHs outright (see "Cycle 1 dispositions"): the
  four-case tier rule, the exact scratch-root assertion with `RUNTIME_DIR` dropped, XDG isolation
  of the installer probes, the template-4 bump, `no_change` as a healthy evidence-only status, the
  four-set env rule, controlled-PATH enumeration, `--artifacts-out`, and the required D-11/R5 steps.
- PASS/KEPT branches per note (20-06) and the narrowed installer wording keep labels at the
  certainty the evidence supports.

### Agreed Concerns (verified, counted)
HIGH, each re-verified against source:
1. 20-02: `_resolve_model` runs `check=False` and never reads `returncode`
   (`tests/gsd_curated_eval.py:632-648`); `live_tables` does the same (`:444-467`). A non-zero
   resolve-model exit that still prints matching JSON passes the oracle. The plan changes the
   comparison but not this seam.
2. 20-04 Task 3: readiness reads the FIRST `spawn` line (`20-04-PLAN.md:369-370`). `runChild`
   records every child (`cross-ai.mjs:588`), and the runner runs `treeState` (git) and the
   `listModels` preflight before the CLI (`cross-ai.mjs:2853-2863`, git via `runChild` at
   `:720-730`). The first pid is an exited git child, so `ps -o args=` never names codex and the
   60 s readiness loop has no defined outcome.
3. 20-04 (and the same `## Time budget (checker W2)` section in 20-03, 20-05, 20-07): GSD builds the
   delegated prompt from `<objective>` and `<tasks>` only (`execute-phase/detail/elaboration.md`
   step 1 "Extract `<objective>` and `<tasks>`"). The stop-and-hand-back rule sits outside both
   (`20-04-PLAN.md:163-179`, `20-03:171`, `20-05:153`, `20-07:162`), so the executor never sees it.
   20-04 Task 2's direct `codex exec` (`:308`) and both `inventory --refresh` runs (`:318-325`)
   have no timeout wrapper although the objective promises `run-with-timeout 300` per probe.
4. 20-05 Task 3 mirrors the 20-04 readiness rule (`20-05-PLAN.md:325-330`): same first-spawn defect.
5. 20-05: the objective's own bounds are 930 + 150 + 300 + 2 x 300 = 1,980 s
   (`20-05-PLAN.md:79-83`), over the 1,800 s `workflow.cross_ai_timeout` before any overhead; the
   C-W12 inventory (`:288-289`) is unwrapped.
6. 20-06 Task 3: `BASELINE ... (reference, not a floor)` (`20-06-PLAN.md:443-444`) with a pass rule
   of `CURRENT >= 96` contradicts AGENTS.md's skill rule ("no regression vs. baseline"); a 97
   against the Phase 19 109/114 passes. The phase rule (`:436-438`, pi `judge unavailable` is
   acceptable) and the verdict rule (`:447-450`, unavailable is BLOCKED) also need one decision
   table.
7. 20-07 step 7 (`20-07-PLAN.md:245-255`): the commands run inside `<dir>/project-a` but redirect to
   the checkout-relative `tmp/p20/interactive/...`, which does not exist there
   (`_scratch_project`, `tests/gsd_curated_eval.py:3915-3929`); the shell fails the redirection
   before the loader command runs.
8. 20-07 step 6 (`:235-239`): `/gsd-review 20` omits `--phase`. The command declares
   `argument-hint: "--phase N ..."` (`.claude/commands/gsd-review.md:4`) and the workflow extracts
   only `--phase` (`.claude/gsd-core/workflows/review.md:157`). The fallback "any GSD project"
   need not hold phase 20, and a prerequisite failure is not separated from a lane self-skip.
9. 20-07 step 7: "the JSON events carry the provider and model ids" is an untested assumption
   (no [VERIFIED] source in 20-RESEARCH.md; `parseOpencode` reads only `text`/`error` events,
   `cross-ai.mjs:367-380`). Only `gsd-planner` is observed while D-07 records the chain per agent
   (`20-CONTEXT.md:116-119`), and `## What happens next` checks EVAL-05 off without a branch for
   "no loader field found".

Actionable MEDIUM/LOW, verified:
- 20-01 (MEDIUM, orchestrator-found): `python3 skills/ai-kit-spec-review/ai-kit-spec-review.py
  detect-current-runtime` (`20-01-PLAN.md:251`) names a file that does not exist; the entrypoint is
  `skills/ai-kit-spec-review/ai-kit-spec.py` (live: prints `{"host": "claude"}`). The required
  `bootstrap dispatch host:` line depends on it.
- 20-01 (MEDIUM, reviewer and orchestrator): the acceptance grep for `template 3`
  (`20-01-PLAN.md:267`) matches the kept floor comment at `cross_ai_script.py:29`, a file not in
  `files_modified`.
- 20-01 (MEDIUM, partial cycle-1 carry-over): the failure path restores with `git checkout`
  (`:246-247`), the index version, not the bytes recorded at task start; save a copy and restore it.
- 20-02 (MEDIUM): the empty promise for a loaded map without the host/tier entry
  (`20-02-PLAN.md:176-178`, test at `:214-215`) ignores the omit gate: without an applicable
  `resolve_model_ids: "omit"` gsd-core falls through to the tier alias
  (`model-resolver.cjs:584-585,600-618,654-669`).
- 20-03 (MEDIUM): `_toml_semantic_sha` drops scratch keys but leaves an empty `projects` table, so a
  baseline without `projects` hashes differently after a scratch-only trust write
  (`20-03-PLAN.md:310-318`).
- 20-03/20-04/20-05/20-07 (MEDIUM): the snapshot CLI passes no scratch exemption (`20-03:316-318`),
  while 20-04/20-05's "Snapshot baseline note" calls an outside trust table "not a guard failure"
  (`20-04:176-179`, `20-05:166-169`) and every verify still requires `snapshot ok`. Pick one rule.
- 20-04/20-05 (MEDIUM): the env dump keeps only `^(CODEX|OPENCODE|AI_AGENT|AGENT|CLAUDE)`
  (`20-04:209`, `20-05:197-200`), so the four-set check cannot see `PI_CODING_AGENT`,
  `CURSOR_AGENT` or `GROK_AGENT`, the likeliest leak when pi is the executor.
- 20-05 (LOW): `build_runtimes_snapshot` also starts a private `opencode serve` image probe for
  opencode (`detection.py:1011-1019`, `:796-812`); the evidence and the ps diff should name it.
- 20-06 (MEDIUM): the replacement branch (`20-06-PLAN.md:233-238`) adds a name to
  `host_signals`, which grows `HOST_SIGNAL_ENV_VARS` (`detection.py:201-205`); the template
  `scrubEnv` literal, `tests/test_ai_kit_spec.py:11561` and the 11-name pin
  (`tests/test_ai_kit_spec_runtimes_table.py:83-85`) then fail, but the plan says the mirrors stay
  untouched.
- 20-06 (MEDIUM): three 630 s judge attempts, a quota retry and two fix rounds exceed the 1,800 s
  dispatch (`:407-442`); no in-task budget check.
- 20-07 (MEDIUM): the dry run greps `^model:` in "a baked agent file from the headless artifacts
  dir" (`:293-298`), but 20-03 exports four JSON files only (`20-03:388-397`).
- 20-07 (MEDIUM): `make test`, `make validate` and the verbose pre-commit run record no exit code
  (`:346-361`); the verify (`:405`) greps lines, which a partial log can satisfy.

### Not counted
- 20-01 bootstrap dispatch on the template-1 runner (reviewer: "recorded residual risk"): the plan
  disposes it explicitly as accepted (T-20-17, `20-01-PLAN.md:339`) with the host recorded; not
  re-raised as a concern.
- 20-03 empty opencode promise vs `None`: already handled (`20-03-PLAN.md:369-374`), as the
  reviewer itself notes.

### Divergent Views
None between reviewers (single reviewer). The orchestrator would rate HIGH 1 MEDIUM on impact (the
code is Phase 19's, and resolve-model printing a matching JSON then exiting non-zero is
implausible) and HIGH 7 MEDIUM (the user sees the shell error at once); both are counted HIGH under
the single-reviewer rule.

## Verification coverage

Source-grounding authority: `grep` (`drift-guard authority --raw`). Severity map
(`drift-guard severity --authority grep`): VERIFIED = none, MISSING = needs-acknowledgement,
AMBIGUOUS = MEDIUM, UNCHECKABLE = INFO; no `hardBlock`. Symbols in each plan's "Artifacts this
phase produces" list are excluded. Symbols already resolved in cycle 1 and unchanged are
re-checked at their current lines.

20-01
- "`RUNTIMES.opencode`: `exec`, `review`, `resume`" (20-01:187): VERIFIED `skills/ai-kit-spec-review/references/cross-ai.mjs:274-283`
- "self-test `argv-exec-<rt>` and `argv-review-<rt>` ... `must` and `never` lists" (20-01:187): VERIFIED `cross-ai.mjs:1566,1574-1577,1585,1593`
- "`listModels`: the `opencode models` preflight" (20-01:187): VERIFIED `cross-ai.mjs:672`
- "`TEMPLATE_VERSION = 3`" (20-01:188): VERIFIED `cross_ai.py:46`; "`_READY_TEMPLATE = 3`, documented as a floor": VERIFIED `cross_ai_script.py:29-31`
- "`_plan_rendered`, `plan_runner_upgrade`, `ensure_runner`, `write_script`" (20-01:188): VERIFIED `cross_ai_script.py:192,242,366,381`
- "`test_template_version_constants_match_the_shipped_template`" (20-01:189): VERIFIED `tests/test_curated_config_script.py:53`
- "every `template=3` literal ... (lines 108, 132, 233, 306, 325, 351) and ... (lines 899, 911)" (20-01:189): VERIFIED
- "`_v2_pristine`" (20-01:212): VERIFIED `tests/test_curated_config_script.py:319`
- "SKILL.md line 193 and references/runner.md line 1" (20-01:190), "`tooling_guidance.py` line 24" (20-01:215): VERIFIED
- "seven goldens ... pin `"version": 3`" (20-01:217-219): VERIFIED (7 files)
- "`UPDATE_GOLDEN=1 python3 -m unittest tests.test_curated_config_golden`" (20-01:220): VERIFIED `tests/test_curated_config_golden.py:7`
- "`.planning/scripts/cross-ai.mjs` ... header `template=1`" (20-01:191): VERIFIED line 2; `--print-argv` prints one line per CLI (live)
- "`python3 skills/ai-kit-gsd-curated-config/ai-kit-gsd-curated-config.py ensure-runner --cwd .`" (20-01:231): VERIFIED `cli.py:768,891`
- "`python3 skills/ai-kit-spec-review/ai-kit-spec-review.py detect-current-runtime`" (20-01:251): MISSING (file absent; `ai-kit-spec.py` is the entrypoint, `cli.py:146`) — needs-acknowledgement, counted as actionable MEDIUM
- "`eligible_lanes`", "`_host_reviewer_problem`" (20-01:281): VERIFIED `cross_ai.py:202`, `plan_io.py:542`
- "`make_inventory`, `entry_map`, `build`", "`_fixture_review_lanes`", "`_review_lane_accepted_keys`" (20-01:282): VERIFIED `tests/test_curated_config_recommend.py:256,327,331,1547,1565`
- "`test_host_slug_never_a_review_lane`; `_write_pair(tmp, host=...)`, `_run_plan_set`" (20-01:283): VERIFIED `tests/test_curated_config_plan_edit.py:397,55,37`
- "`workflows/review.md:126-149`, `SELF_CLI=auto`" (20-01:307): VERIFIED `.claude/gsd-core/workflows/review.md:126-150`

20-02
- "`_LIVE_TABLES_SCRIPT`, `live_tables`, `promised`, `_set_entries`, `compare`" (20-02:152): VERIFIED `tests/gsd_curated_eval.py:444,470,505`
- "`_mismatches`", "`_unoverridden`, `_write_control_plan`, `_control_one`", "`run_matrix`", "`_cmd_matrix`" (20-02:152): VERIFIED `:655,705,714,727,808,2237`
- "`resolveTierFromConfig`", "`CLAUDE_POLICY_ID_TO_ALIAS`" (20-02:153): VERIFIED `.claude/gsd-core/bin/lib/model-resolver.cjs:425,211`
- "`_seed_runtime_key`, `_informational_row`", "`_render_matrix`", "`render_smoke_evidence`", "`MESSAGE_NON_CLAUDE`" (20-02:249-257): VERIFIED `:782,2267,4281,114`
- "`refuse_repo_apply`", "`_row_for`", "`_TIERS`" (20-02:30,209,192): VERIFIED `:558,681,123`
- "`E2E_MODULES`" (20-02:273): VERIFIED `tools/run_unittest_parallel.py`, Makefile:11 e2e list
- Signature behavior "an unloaded map ... promises `""`" vs gsd-core omit gate (20-02:176-178): UNCHECKABLE under `grep` as a signature/behavior claim; traced by hand: AMBIGUOUS semantics, see actionable MEDIUM

20-03
- "`SmokeCtx`", "`_step`, `_scratch_project`", "`_inventory`", "`run_smoke`", "`_smoke_placeholders`, `render_smoke_evidence`, `_cmd_smoke`" (20-03:191): VERIFIED `tests/gsd_curated_eval.py:3653,3904,3915,3945,4223,4263,4281,4321`
- "`_real_apply_or_fail`, `_dry_run_unchanged` and `validate_applied`" (20-03:191): VERIFIED `:4026,3998,3873`
- "`project_root`: `RUNTIME_DIR` wins" (20-03:192): VERIFIED `skills/ai-kit-spec-review/ai_kit_spec/gsd_tools.py:33-47`; "`local_gsd_core_roots` order": VERIFIED `:85-93`
- "`_HOST_FIRST_ROOT`, `resolve_gsd_core`" (20-03:192): VERIFIED `host.py:21-25,118-140`
- "inventory.py lines 405-412 (`gsd_core: {path, scope, version}`)" (20-03:192): VERIFIED `inventory.py:407`
- "`resolveOpencodeDataDir`" (20-03:193): VERIFIED `.claude/gsd-core/bin/lib/opencode-version.cjs:409`
- "`_file_sha`, `_dir_names`, ... `_tree_sha`", "`CREDENTIALS_BASENAME`", "`_cmd_snapshot`" (20-03:305): VERIFIED `:177,183,251,98,316`
- "`gsd_tools.gsd_core_version` of `GSD_TOOLS_PATH`" (20-03:207): VERIFIED `:94`
- "`~/.npm/_npx/*/...` or `~/.cache/pnpm/dlx/*/*/...`" (20-03:90): VERIFIED in cycle 1 (names only); not re-listed
- "`writeNonClaudeDefaults`, `cleanupLegacyGsdCc`", "`generateCodexAgentToml`" (20-03:95-96,252): VERIFIED in cycle 1 (cached 1.17.0 `bin/install.js`)
- "`opencode debug paths`" (20-03:98): VERIFIED live (`opencode debug --help` lists `paths`, v2.0.31)

20-04
- "`STATUS_TABLE` ... `no_change` exit 1 action fallback" (20-04:189): VERIFIED `cross-ai.mjs:128-130`
- "lines 2895-2945 (the exec-mode rule ...)" (20-04:189): VERIFIED `:2906-2910,2936-2937`
- "`parse_status_line`", "`_runner_reason`" (20-04:191): VERIFIED `runner_dispatch.py:200,504`
- "`RUNTIMES["codex"]`: `host_signals`, `scrub_signals=("CODEX_SANDBOX",)`", "`_GENERIC_HOST_MARKERS = ("AI_AGENT",)`", "`HOST_SIGNAL_ENV_VARS`" (20-04:192): VERIFIED `detection.py:101-105,142,201`
- "`detect_installed_clis`", "`detect_cursor_agent_models`", "`build_runtimes_snapshot`" (20-04:300): VERIFIED `detection.py:183,304,986`
- "catalog_adapter.py lines 166-170 (`inventory --refresh` runs `detect-runtimes --save`)" (20-04:300): VERIFIED
- "`KILL_GRACE_MS`, `SIGNAL_BUDGET_MS` 2500, `SIGNAL_GRACE_MS` 1000, `SIGNAL_DRAIN_MS` 500" (20-04:357): VERIFIED `cross-ai.mjs:151,155-157`
- "`noteChildPgid`", "`makeTemp('cross-ai-')`", "`xai-idx-`", "`--child-pgid-file`" (20-04:357): VERIFIED `:498,837,725,36`
- "readiness ... `awk '/^spawn/{print $2; exit}'`" names the CLI (20-04:369-370): AMBIGUOUS (multiple `spawn` candidates: git, listing, CLI; `runChild` records all at `:588`) — HIGH 2
- "`codex debug models`" (20-04:206): VERIFIED in cycle 1 (live)
- "`node .claude/gsd-core/bin/gsd-tools.cjs run-with-timeout 300 --`" (20-04:367): VERIFIED in cycle 1 (live usage)

20-05
- "opencode's bash tool sets `AGENT`, `OPENCODE`, `AI_AGENT ||= "opencode"`, `OPENCODE_SESSION_ID`" (20-05:182): VERIFIED `20-RESEARCH.md:292-296` (source byte scan, research-tagged)
- "`opencode run --help` ... `--standalone`", "`--agent`" (20-05:19, 20-07:247): VERIFIED live (v2.0.31)
- "`OPENCODE_EFFORT_EFFECT`" (20-05:269): VERIFIED `cross_ai.py:181`
- "the runner strips the suffix for listing membership" (reviewer, 20-05:280): VERIFIED `cross-ai.mjs:2861`
- "pi `openai/gpt-6.1-sol:xhigh`" availability (20-06:409): UNCHECKABLE (live model; no model call made)

20-06
- "`_LABEL_*`, `Runtime`, `RUNTIMES`", "the Phase 18 scrub comment", "`SCRUB_ENV lacks`" (20-06:216): VERIFIED `detection.py:44,51,57,64-74,197-200`
- "tests/test_ai_kit_spec.py line 11561" (20-06:217): VERIFIED
- "`_SCRUB_NAMES`, `test_ids_follow_host_precedence_and_known_clis`, `test_scrub_set_keeps_the_same_eleven_names`, `test_precedence_pairs`" (20-06:218): VERIFIED `tests/test_ai_kit_spec_runtimes_table.py:22,70,83,87`
- "`host_can_select`" (20-06:220): VERIFIED `routing.py:44`
- "`installer_argv`", "`_disclosures`", "`_config_dir_note`, `_opencode_root_note`, `_codex_installer_note`", "`build_followups`" (20-06:304): VERIFIED `followups.py:49,181,223,227,239,360`
- KEPT-branch strings "inferred (unverified until Phase 20)", "`.opencode/gsd-core` install root **unverified**", "inferred from ... (unverified)" (20-06:371): VERIFIED `followups.py:229,240`, SKILL.md:247
- "`shortcut:` comment above `"opencode": ".opencode"`" (20-06:333): VERIFIED `host.py:23`
- "tests/test_curated_config_followups.py ... `config-dir` note ... line 262" (20-06:307): VERIFIED; "`TestSkillDocCommands` (lines 2321-2360)": VERIFIED `tests/test_curated_config_apply.py:2321`; "tests/test_curated_config_cross_ai.py lines 715-727": VERIFIED `:725`
- "19-08-SUMMARY.md lines 28-34 (`elapsed=134s`)" (20-06:391): VERIFIED `:31`
- "`$HOME/.agents/skills/skill-judge/SKILL.md`" (20-06:398): VERIFIED exists (existence only)
- "`_cmd_digest`" (20-06:393): VERIFIED `tests/gsd_curated_eval.py:421`

20-07
- "Makefile lines 60-75 and 128-140", "`neither docker nor podman found on PATH`", "line 11 (the e2e group lists `tests.test_ai_kit_gsd_curated_config_matrix`)" (20-07:181): VERIFIED `Makefile:11,64,74,128,133,135`
- "`=== <module>: ok in <s>s  Ran N tests`", "`N/N modules passed`" (20-07:182): VERIFIED `tools/run_unittest_parallel.py:207,213-224`
- "19-05-SUMMARY.md `## Leak check`" (20-07:183): VERIFIED `:47`
- "20-SPEC.md line 142 (R5 adjacency row) ... `✅ covered`" (20-07:150): VERIFIED
- "`/gsd-review 20 --opencode`" (20-07:235): MISSING as invocation form (`--phase N` required, `.claude/commands/gsd-review.md:4`) — HIGH 8
- "the JSON events carry the provider and model ids" (20-07:246-247): UNCHECKABLE (output contract; no model call made, no research source) — HIGH 9
- "`opencode debug agents`" (20-07:252): VERIFIED live (`opencode debug --help` lists `agents`)

Coverage: two MISSING rows (the 20-01 entrypoint path and the 20-07 `/gsd-review` form) are
counted as findings; one AMBIGUOUS row is HIGH 2; three UNCHECKABLE rows need a live model or an
output-contract spike. No `hardBlock` (authority `grep`).

## Fact-drift pass (advisory)

`drift-guard phase-status --phase 20`: `verdict: uncheckable`, `reason: phase_not_in_roadmap`
(STATE.md `Ready to execute`; the guard does not parse the ROADMAP `### Phase 20:` heading). This
axis is recorded as unchecked, not consistent. Judged by hand:

- SC1 (codex smoke, env signal "confirmed live") vs must_haves: 20-04 (headless), 20-06 labels
  "TUI confirmation pending", 20-07 interactive script as human_verification. No contradiction.
- SC2 (opencode smoke; lane usability "confirmed and reflected in the recommendation logic and
  SKILL.md"): 20-01 tests, 20-06 SKILL.md paragraph, 20-07 step 6 REQUIRED. Cycle-1 drift closed.
- SC3 ("verified live from the codex and opencode hosts ... or `host_can_select` keeps the
  session-default-only label"): 20-06 pins the default branch with a unit test and keeps the live
  probe optional because "the OR is already met" (`20-06-PLAN.md` must_haves). ROADMAP's "verified
  live" qualifier applies to the whole criterion. Advisory drift (same as cycle 1): amend SC3's
  wording or make the probe a required interactive step.
- Requirements: ROADMAP EVAL-04, EVAL-05; plan `requirements` are 20-01 [EVAL-05], 20-02/03/06/07
  [EVAL-04, EVAL-05], 20-04 [EVAL-04], 20-05 [EVAL-05]. No drift.
- CONTEXT ↔ plans: D-05 ("drop whichever signal does not appear") vs 20-06 keeping an absent name
  pending the TUI: 20-06 Task 1 adds a dated D-05 amendment; not drift. D-07 ("the chain recorded
  per agent ... `opencode debug agent <name>`") vs 20-07 step 7 (one agent, `debug agents` or
  `run --agent`): the 20-07 D-07 amendment covers the command, not the per-agent scope (see HIGH 9).
  D-10's file list vs 20-03's allowlist: the plan adds `opencode.json` and `hooks.json`; additions
  are not drift. D-11 "two trials each": 20-07 step 6 REQUIRED; consistent.

## Cycle 1 dispositions

Cycle-1 HIGHs (numbering from the cycle-1 Consensus Summary; plan numbers then were 20-01..20-06):
1. Claude override-tier regression: FULLY RESOLVED (20-02 Task 1 four cases, claude matrix in verify).
2. Scratch inventory resolved from ai-kit's root: FULLY RESOLVED (20-03 `_project_env`, exact-root assertion and grep).
3. Installer opencode probes outside isolation: FULLY RESOLVED (20-03 XDG_* under the throwaway home, T-20-18, hermetic env pin).
4. No template version bump: FULLY RESOLVED (20-01 template 4, `TEMPLATE_VERSION = 4`, goldens).
5. Bootstrap on the old runner: closed by explicit acceptance (T-20-17, host recorded); not counted.
6. `status=ok` impossible for a clean tree: FULLY RESOLVED (20-04/20-05 dispatch rule, verify regex).
7. Opencode's own `AI_AGENT` rejected: FULLY RESOLVED (four-set rule).
8. `inventory --refresh` enumerates every CLI: FULLY RESOLVED (controlled PATH, `installed_runtimes` proof).
9. Signal probes on the wrong group/temp prefix: PARTIALLY RESOLVED (pgid file and TMPDIR fixed; readiness is now HIGH 2 and 4).
10. Child timeouts above the 1,800 s parent: PARTIALLY RESOLVED (per-child bounds; the stop rule and the 20-05 total are HIGH 3 and 5).
11. D-01 artifacts not kept: FULLY RESOLVED (20-03 `--artifacts-out`).
12. D-11/R5 steps optional: FULLY RESOLVED as to required-ness (20-07 steps 6 and 7 REQUIRED); their mechanics are HIGH 8 and 9.

Cycle-1 MEDIUMs: runtime map refusal, temp-prefix exemption, `_dir_names` overclaim, dropped-name
mirrors, installer overclaim, conditional acceptance, `make test`/`validate.txt` counts and the
docker gate are FULLY RESOLVED in the cited tasks. The runner failure-path restore is PARTIALLY
RESOLVED (pre-existing `.new` protected; restore still uses `git checkout`, listed above).
