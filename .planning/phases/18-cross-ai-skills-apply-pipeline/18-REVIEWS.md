---
phase: 18
cycle: 2
reviewers: [opencode-plan-review]
reviewed_at: 2026-10-15T19:28:49Z
plans_reviewed: [18-01-PLAN.md, 18-02-PLAN.md, 18-03-PLAN.md, 18-04-PLAN.md, 18-05-PLAN.md, 18-06-PLAN.md, 18-07-PLAN.md, 18-08-PLAN.md, 18-09-PLAN.md, 18-10-PLAN.md, 18-11-PLAN.md, 18-12-PLAN.md, 18-13-PLAN.md, 18-14-PLAN.md, 18-15-PLAN.md, 18-16-PLAN.md, 18-17-PLAN.md, 18-18-PLAN.md, 18-19-PLAN.md, 18-20-PLAN.md, 18-21-PLAN.md, 18-22-PLAN.md]
models:
  opencode-plan-review: "router-env/my-plan-review"
model_sources:
  opencode-plan-review: "pinned"
---

# Cross-AI Plan Review — Phase 18 (convergence cycle 2)

<!-- gsd:plan-revision-conflicts:begin -->
## Plan-Revision Conflicts
<!-- gsd:plan-revision-conflicts:end -->

Cycle 2 reviews the plans as revised in 7981bed, which folded in cycle 1's review (f371fbc).
The prompt carried PROJECT.md, the ROADMAP Phase 18 section, the Phase 18 requirement lines and
the plan coverage manifest. It pointed the reviewer at the 22 PLAN.md files, CONTEXT, SPEC,
RESEARCH and the cycle-1 REVIEWS.md on disk instead of inlining them (about 560 KB of plans).
The reviewer read them from the repo. Lane runtime was about 5 minutes; plan coverage was 22 of 22.

## OpenCode Review (opencode-plan-review)

# Phase 18 — Convergence Cycle 2 Review

**Document type:** GSD · implementation plans  
**Coverage:** All 22 plans reviewed from disk, with independent source-grounding passes over the runner and apply subsystems. Context, specification, research, prior review, and disposition ledgers were included. No repository files changed.

Citation prefixes below are repository-relative:
- **P/** = `.planning/phases/18-cross-ai-skills-apply-pipeline/`
- **C/** = `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/`
- **S/** = `skills/ai-kit-spec-review/ai_kit_spec/`
- **G/** = `.claude/gsd-core/bin/lib/`

“Resolved” below means the **revised plan specifies an adequate fix**, not that its future implementation has passed verification.

## 18-01

**Summary:** The shared groundwork now handles the two previously identified encoding/enumeration ambiguities explicitly.

**Strengths**
- Invalid RPC envelopes return `None`, while a valid empty listing returns `[]`; snapshot behavior and malformed-exit-zero tests preserve that distinction (`P/18-01-PLAN.md:194–207,250–254`).
- Container encoding uses `allow_nan=False` and normalizes serialization failures into key-naming refusals before spawning (`P/18-01-PLAN.md:285–305`). This appropriately extends the existing shared writer rather than changing v1’s argv (`S/gsd_tools.py:163–187`).

**Concerns**
- **LOW:** “Never holding a key” overstates the chosen implementation. `secret_is_set` calls `load_secret`, which reads and returns the value internally (`P/18-01-PLAN.md:306–309`; `S/local_secrets.py:11–25`). The relevant guarantee is that the value does not escape the helper or appear in output. Reusing the parser is a reasonable ledger decision; no new parser is needed.

**Suggestions**
- Narrow the wording to “returns presence only; never exposes or logs the value.”

**Risk Assessment:** **LOW** — clear boundary behavior and compatibility preservation.

## 18-02

**Summary:** Inventory schema expansion is now adequately specified at the file boundary.

**Strengths**
- All six lane fields and skill-root values receive explicit validation, with malformed-input cases (`P/18-02-PLAN.md:205–210,304–310`).
- Root-discovery failure now remains distinguishable from absent data and produces a warning (`P/18-02-PLAN.md:192–201`).
- Existing config identity is retained through the established inventory mechanism (`C/inventory.py:91–103`).

**Concerns**
- No new blocking concern found. The opencode local-root assumption is visibly marked unverified rather than presented as established behavior (`P/18-02-PLAN.md:156–162`).

**Suggestions**
- Preserve the distinction between normalization of live node output and rejection of malformed persisted inventory.

**Risk Assessment:** **LOW** — bounded schema work with explicit degradation behavior.

## 18-03

**Summary:** The revised scanner resolves the global `SKILL.md` symlink issue and establishes one unreadable-file policy.

**Strengths**
- Escape detection follows both the directory and resolved skill file, matching gsd-core’s global-file check (`P/18-03-PLAN.md:160–168`; `G/init.cjs:3691–3702`).
- Unreadable existing files consistently retain entries with empty descriptions (`P/18-03-PLAN.md:209–215,261–263`).
- Backend reachability includes DNS in the bounded wait and avoids printing URL credentials (`P/18-03-PLAN.md:178–185,294–299`).

**Concerns**
- No new blocker found. Plugin layering remains an acknowledged assumption, and the limited plugin scan is explicitly documented (`P/18-03-PLAN.md:83–95`).

**Suggestions**
- Keep these confidence labels in inventory output, not only comments.

**Risk Assessment:** **MEDIUM** — filesystem and plugin discovery remain externally dependent, but the identified correctness gaps are addressed.

## 18-04

**Summary:** The cycle-1 task-order blocker is fully resolved.

**Strengths**
- The purity allowlist and inspected-module tuple now change in Task 1, alongside the new import (`P/18-04-PLAN.md:215–225`).
- This directly addresses the existing AST guard, which rejects unlisted relative imports (`tests/test_curated_config_recommend.py:1720–1740`).
- Runner settings have one authoritative artifact representation (`P/18-04-PLAN.md:153–162`).

**Concerns**
- No remaining concern from the original HIGH.

**Suggestions**
- Keep the allowlist change and import in the same logical commit as specified.

**Risk Assessment:** **LOW** — the deterministic verification-order failure has been removed.

## 18-05

**Summary:** Selection-edge coverage now supports its interruption-safety claim rather than relying on determinism alone.

**Strengths**
- The injected replacement failure checks preserved old bytes and temporary-file cleanup (`P/18-05-PLAN.md:168–169`).
- That test exercises the actual shared writer’s replacement/error-cleanup mechanism (`S/cache.py:35–46`).
- Host exclusion, preference ordering, defaults, and router priority have explicit cases (`P/18-05-PLAN.md:158–167`).

**Concerns**
- No new blocking concern found.

**Suggestions**
- Keep the interruption case separate from the pure-selection assertions so failures identify the responsible boundary.

**Risk Assessment:** **LOW** — focused, useful tests without additional runtime machinery.

## 18-06

**Summary:** Registry-driven lane selection remains sound; the ledger’s rejection of the earlier host-binary concern is justified.

**Strengths**
- Eligibility requires candidates matching the lane binary and marked non-host (`P/18-06-PLAN.md:143–147`).
- Candidate construction defines `is_host` from runtime identity, so an alternative lane slug cannot bypass host exclusion (`C/catalog_adapter.py:380–390`).
- Registry keys, router precedence, second-lane reselection, and effort limitations are explicit (`P/18-06-PLAN.md:150–168`).

**Concerns**
- No new blocker. The opencode effort incompatibility is disclosed and reasonably deferred to live validation (`P/18-06-PLAN.md:138,168`).

**Suggestions**
- Retain the disclosure in generated entries until Phase 20 provides evidence.

**Risk Assessment:** **MEDIUM** — external lane invocation remains a known validation dependency, not a newly discovered planning gap.

## 18-07

**Summary:** The affinity layer has clear boundaries and reuses existing recommendation patterns appropriately.

**Strengths**
- The CLI loads curated data while recommendation stays pure (`P/18-07-PLAN.md:199–218`).
- Caps, gates, deduplication, missing-skill silence, and reference precedence have targeted cases (`P/18-07-PLAN.md:244–257`).
- The additional CLI read is narrowly added to the existing I/O guard rather than weakening it (`P/18-07-PLAN.md:212–218`).

**Concerns**
- No new blocking concern. Tuple membership makes the ledger’s rejection of the unhashable-`when` concern reasonable (`P/18-07-PLAN.md:158–164,354–357`).

**Suggestions**
- Preserve file-order resolution as policy; avoid introducing a second ranking mechanism.

**Risk Assessment:** **LOW** — small pure policy layer with explicit input validation.

## 18-08

**Summary:** Partial existing trust and escaping project copies now have defined handling.

**Strengths**
- Proposed approval text preserves existing roots and excludes covered descendants (`P/18-08-PLAN.md:121–153,202–205`).
- Escaping project copies no longer automatically outrank usable alternatives (`P/18-08-PLAN.md:137–145,206`).
- This is conservative relative to gsd-core’s project-containment gate (`G/init.cjs:3718–3721`).

**Concerns**
- **LOW:** Lexical trusted-root coverage can propose a duplicate when an existing root reaches the same location through a symlink. This is explicitly accepted and documented, not an unresolved safety hole (`P/18-08-PLAN.md:124–129`).

**Suggestions**
- Keep the limitation labelled; no additional filesystem access is needed in the pure layer.

**Risk Assessment:** **LOW** — approval preservation and conservative filtering reduce the previous risks.

## 18-09

**Summary:** The revised harness addresses case contamination and restores useful coverage removed with the prototype self-test.

**Strengths**
- Each case has independent HOME and call-log state (`P/18-09-PLAN.md:163–176`).
- Initial exec/review argv and output parsing are tested for all four runtime blocks (`P/18-09-PLAN.md:282–301`).
- Hermetic PATH prevents accidental model calls and real-config access (`P/18-09-PLAN.md:169–176,209–212`).

**Concerns**
- **MEDIUM:** Initial argv coverage does not cover resumed review argv. The preserved Codex resume formula omits the initial review’s explicit read-only sandbox (`.planning/scripts/cross-ai.mjs:188–190`). This becomes relevant when 18-11 preserves resume behavior.

**Suggestions**
- Extend black-box argv coverage to review retries, or explicitly avoid resume where review restrictions cannot be preserved.

**Risk Assessment:** **MEDIUM** — good harness foundations, with one permission-boundary coverage gap.

## 18-10

**Summary:** Exit-based cleanup, asynchronous Git snapshots, and unknown-state rejection substantially improve the supervision design. One terminal-path inconsistency remains.

**Strengths**
- Cleanup starts on `exit`, avoiding the prototype’s dependency on `close` after inherited pipes drain (`P/18-10-PLAN.md:141–149`; `.planning/scripts/cross-ai.mjs:305–310`).
- Git work receives shared-budget asynchronous supervision (`P/18-10-PLAN.md:134–155`).
- Unknown before-state prevents execution; unknown after-state prevents success/fallback (`P/18-10-PLAN.md:160–166`).

**Concerns**
- **HIGH — Timeout finalization is incomplete.** The exit path explicitly drains and destroys streams; timeout specifies SIGTERM, bounded waiting, SIGKILL, then resolution without equivalent stream teardown (`P/18-10-PLAN.md:143–148`). The prototype echoes child stderr directly from data callbacks (`.planning/scripts/cross-ai.mjs:291–292`). Late callbacks can therefore print after the supposedly final status line.

**Suggestions**
- Require one bounded finalizer for exit, timeout, spawn error, and signal: stop heartbeat/echo callbacks, close streams, kill the group, settle once, then emit final status.
- Add termination-time output to the elapsed-time case and assert no stderr follows `AIKIT-XAI`.

**Risk Assessment:** **HIGH** — the remaining ambiguity affects the runner’s stable machine-readable contract.

## 18-11

**Summary:** Model preflight is now bounded by the remaining lifecycle budget. Retry permission preservation still needs specification.

**Strengths**
- Listing uses asynchronous `runChild` with `min(15 seconds, remaining budget)` (`P/18-11-PLAN.md:109–115`).
- A hanging-listing test checks elapsed time and proves no execution starts after budget exhaustion (`P/18-11-PLAN.md:147`).
- Fake retry counters now live outside the snapshotted repository (`P/18-11-PLAN.md:125–128,175`).

**Concerns**
- **MEDIUM:** “The prototype’s resume logic stays” preserves the Codex review-resume ambiguity identified above (`P/18-11-PLAN.md:121–123,179–180`; `.planning/scripts/cross-ai.mjs:188–190`). Post-run write detection does not establish preventive read-only behavior.

**Suggestions**
- Specify mode-preserving resume restrictions and test the actual retry argv.
- Accept the ledger’s deliberate exec-resume policy; do not prohibit useful same-CLI continuation after partial execution work.

**Risk Assessment:** **MEDIUM** — lifecycle preflight is improved; review retry isolation remains unproven.

## 18-12

**Summary:** Unknown-state review outcomes and elapsed-time deadline proof are now explicitly covered.

**Strengths**
- Review writes override other outcomes, and transient failures are checked before retry (`P/18-12-PLAN.md:151–163`).
- `outer-race` combines preflight, resistant descendants, inherited pipes, and hanging after-run Git under a measured deadline (`P/18-12-PLAN.md:194`).
- The prototype’s synchronous Git operations explain why arithmetic-only checks were insufficient (`.planning/scripts/cross-ai.mjs:256–259`).

**Concerns**
- **MEDIUM:** The elapsed case checks the last status line but does not explicitly force output during shutdown, leaving 18-10’s timeout-finalization gap insufficiently exercised (`P/18-12-PLAN.md:137–139,194`).

**Suggestions**
- Make the resistant child emit stderr during termination and require all output callbacks to finish before status emission.

**Risk Assessment:** **MEDIUM** — the main cycle-1 requirements are addressed, subject to the shared-finalizer correction.

## 18-13

**Summary:** The requested renderer race mitigation is adequately specified, including its residual concurrency limitation.

**Strengths**
- Publication rechecks expected bytes and returns the operation actually performed (`P/18-13-PLAN.md:140–149`).
- Intervening edit/create tests exercise the previously missing window (`P/18-13-PLAN.md:217–218`).
- The design reuses atomic-write machinery consistent with the existing shared writer (`S/cache.py:27–46`).

**Concerns**
- **LOW:** A recheck followed by replacement is not an atomic compare-and-swap. The plan explicitly discloses that remaining race (`P/18-13-PLAN.md:147–149`), satisfying cycle 1’s request to document residual limitations.

**Suggestions**
- Avoid describing this as absolute protection against simultaneous external edits.

**Risk Assessment:** **LOW** within the documented concurrency limit.

## 18-14

**Summary:** Shared executable-plan validation is a major improvement, but its artifact completeness rule remains insufficient.

**Strengths**
- Entry uniqueness, supported hosts, pinned artifact paths, and shared validation address the original shallow-envelope problem (`P/18-14-PLAN.md:156–172`).
- Refusals occur before plan publication (`P/18-14-PLAN.md:223–231`).

**Concerns**
- **HIGH — Missing target coverage invariant.** Models and choices must reference preferred IDs and be disjoint, but the plan never requires their union to equal `prefer` (`P/18-14-PLAN.md:167–172`). Thus `prefer=["pi"]`, empty models/choices, and `status="ok"` can pass the specified rules and produce a runner with no model.
- **MEDIUM:** Command/timeout policy applies to `set`, while 18-15 treats `keep.value` as effective (`P/18-14-PLAN.md:161–166`; `P/18-15-PLAN.md:145–153`). A hand-edited keep entry can claim a value that apply will not write or retain live.

**Suggestions**
- Require exact model-or-choice coverage, nonempty model strings, and router-map IDs constrained to preferred targets.
- Define effective keep values consistently and validate relevant live dependencies before apply.
- Treat `forced: true` as an acknowledgement marker, not authenticated proof that the editor was used.

**Risk Assessment:** **HIGH** — executable input validation remains partially open.

## 18-15

**Summary:** Execution invariants improve generic unset safety, but Task 1 introduces a deterministic ordering failure.

**Strengths**
- Shared invariants now run at load and after every edit (`P/18-15-PLAN.md:145–155`).
- Command-unset and execution-unset cases directly address cycle 1’s consistency gap (`P/18-15-PLAN.md:208–210`).

**Concerns**
- **HIGH — Task 1 cannot pass its CLI unset case.** It requires `plan-unset script:cross-ai.model.pi` to succeed (`P/18-15-PLAN.md:173,180`), but 18-14 installs an unconditional refusal (`P/18-14-PLAN.md:229–231`). Removing that refusal is deferred to Task 2, and Task 1 does not list `cli.py` (`P/18-15-PLAN.md:162,214–217`).
- **MEDIUM:** Shared validation does not require artifact timeout and effective config timeout to agree (`P/18-15-PLAN.md:145–155`), although hand-edited plans are supported inputs.

**Suggestions**
- Move pseudo-key unset dispatch wiring into Task 1.
- Validate timeout synchronization, not only editor-side synchronization.

**Risk Assessment:** **HIGH** — immediate task-order blocker.

## 18-16

**Summary:** Exclusive marker acquisition fixes the original concurrent-apply race. Recovery instructions need one additional state distinction.

**Strengths**
- Exclusive marker acquisition precedes backup and writes, with a competing-acquirer test (`P/18-16-PLAN.md:121–138,213–214`).
- Backup reuse now considers mode as well as bytes, avoiding restoration of stale permissions.

**Concerns**
- **MEDIUM:** Markers support `runner.kind="add"` without a snapshot (`P/18-16-PLAN.md:133–138`), but stale-marker recovery describes restoring a snapshot (`P/18-18-PLAN.md:84–96`). Interrupted creation instead requires removing the added runner.

**Suggestions**
- Branch recovery instructions by runner operation and backup progress.
- Explicitly handle “backup not yet taken” and “runner may already have been published.”

**Risk Assessment:** **MEDIUM** — ownership is sound; manual recovery completeness needs tightening.

## 18-17

**Summary:** Destination binding fixes the wrong-project/workstream apply risk. One prescribed tracer assertion contradicts the required mechanism.

**Strengths**
- Canonical resolved config identity is checked against inventory identity (`P/18-17-PLAN.md:146–152`).
- Dry run and real apply share reference translation and live-config reading (`P/18-17-PLAN.md:157–165`).

**Concerns**
- **MEDIUM — Impossible node-call assertion.** The tracer says its only node call is the `-e` table query (`P/18-17-PLAN.md:193`), but target resolution must call node-backed `config-path` (`P/18-17-PLAN.md:146–149`; `S/gsd_tools.py:243–250`).

**Suggestions**
- Assert an explicit read-only allowlist: config-path plus table query, with no config-set or creation call.

**Risk Assessment:** **MEDIUM** — destination safety is improved, but the specified test would reject the correct implementation.

## 18-18

**Summary:** Ordinary write-failure rollback is much stronger. Finalization order can still destroy the assets rollback requires.

**Strengths**
- Replaced runners are snapshotted, rollback errors preserve recovery assets, and `.new` is reported inactive (`P/18-18-PLAN.md:180–183,208–218`).
- Real-gsd-tools application checks include skills, config writes, and absence of leftover transaction assets (`P/18-18-PLAN.md:204–205`).

**Concerns**
- **HIGH — No safe commit/cleanup boundary.** The sequence deletes the runner snapshot, then prunes backups, then clears the marker; every subsequent failure must still roll back (`P/18-18-PLAN.md:208–215`). If pruning or marker removal fails after snapshot deletion, restoring the original runner is impossible.
- **MEDIUM:** A crash between snapshot deletion and marker deletion leaves recovery instructions pointing to a missing snapshot.

**Suggestions**
- Define a durable transaction commit boundary.
- Retain restore assets until that boundary; afterward report cleanup failures without attempting rollback using deleted assets.
- Inject prune, snapshot-discard, and marker-clear failures.

**Risk Assessment:** **HIGH** — the central configuration-recovery guarantee remains incomplete.

## 18-19

**Summary:** The added real transaction variants are valuable, but do not cover the newly introduced finalization hazard.

**Strengths**
- Absent-config rollback and failed re-apply runner restoration extend coverage beyond existing-config writes (`P/18-19-PLAN.md:127–130,158–160`).
- Correct second/third-apply backup expectations preserve meaningful history.

**Concerns**
- **MEDIUM:** Config-write failure proofs do not establish recovery after pruning, snapshot deletion, or marker-clear failure. These are now explicit transaction steps in 18-18.

**Suggestions**
- Add focused unit-tier finalization tests in 18-18; another expensive real-node suite is unnecessary.

**Risk Assessment:** **MEDIUM** — strong write-path evidence, incomplete terminal-state evidence.

## 18-20

**Summary:** The workstream sync restriction is honest and appropriate. Follow-up destination and approval identity still need tightening.

**Strengths**
- Explicit effort sync and its preview are disabled for unsupported workstreams.
- This matches root-only effort lookup in current gsd-core (`G/commands.cjs:789–795`; `G/install-effort-resolver.cjs:130–168`).
- Actual-write trigger IDs are carried through `--require`, avoiding the original plan-time-only drift gap (`P/18-20-PLAN.md:93–101,195–219`).

**Concerns**
- **MEDIUM — Destination binding is not reused.** Follow-ups load through `apply.load_inputs` (`P/18-20-PLAN.md:227–232`), which checks digest and directory existence only; canonical destination binding lives in `resolve_target` (`P/18-17-PLAN.md:140–152`). A project-A pair can therefore drive follow-ups in project B.
- **MEDIUM:** `--require` preserves trigger IDs, not an identical approved command block. Environment, local-tool resolution, workstream selection, and preview counts can change before approval (`P/18-20-PLAN.md:195–219`).

**Suggestions**
- Reuse destination binding before follow-up execution and test A→B refusal.
- Re-display/reconfirm materially changed commands. Narrow “same block” claims to stable fields rather than adding a receipt file automatically.

**Risk Assessment:** **MEDIUM** — approval exists, but its destination/state binding is incomplete.

## 18-21

**Summary:** Documentation now explains inactive `.new` output and recovery states rather than implying automatic activation.

**Strengths**
- Manual merge and active-runner inspection are explicit (`P/18-21-PLAN.md:142–157`).
- Command examples are checked against the real parser (`P/18-21-PLAN.md:127–130`).
- Judge evidence is bound to the committed skill blob and distinguished from independent review (`P/18-21-PLAN.md:189–210`).

**Concerns**
- **LOW:** `--print-argv` establishes active argv/deadline configuration, not successful live model access. Its no-dispatch nature is correctly stated; avoid stronger activation claims.

**Suggestions**
- Update recovery wording after 18-18 defines its commit boundary.

**Risk Assessment:** **LOW** — operational clarity is substantially improved.

## 18-22

**Summary:** Closing-gate execution is more realistic, though one old absolute-success statement remains.

**Strengths**
- Container provisioning is explicitly authorized, and network-blocked Docker verification is not counted as a pass (`P/18-22-PLAN.md:73–77,136–145`).
- Gate-fix scope and negative-test diagnostic handling are clarified (`P/18-22-PLAN.md:66–72,157–158`).
- This matches the Makefile’s actual image-build behavior (`Makefile:133–138`).

**Concerns**
- **LOW:** The final verification still requires `make ... e2e-docker` to exit zero, and success text says every gate is green, despite the accepted blocked-network outcome (`P/18-22-PLAN.md:265–273`).

**Suggestions**
- Make final verification and completion wording use the same “passed versus explicitly blocked” distinction.
- Carry the additional validator, finalization, and follow-up binding corrections into source-of-truth amendments.

**Risk Assessment:** **LOW** — remaining issues concern consistent closure reporting.

## Cycle-1 HIGH Resolution

- **18-04 purity-guard task order — FULLY RESOLVES.** Allowlist and inspected-module changes now accompany the import in Task 1 (`P/18-04-PLAN.md:215–225`).

- **18-10 cleanup waiting on `close` — FULLY RESOLVES the original issue.** Cleanup starts on `exit`, with inherited-pipe and resistant-grandchild cases (`P/18-10-PLAN.md:141–149,241`). The separate timeout-finalization gap remains HIGH.

- **18-10 unbounded Git snapshots — FULLY RESOLVES.** Async Git commands use capped shared-budget supervision (`P/18-10-PLAN.md:134–155,244`).

- **18-11 fixed synchronous listing budget — FULLY RESOLVES.** Listings share the lifecycle deadline and have a hanging-listing elapsed test (`P/18-11-PLAN.md:109–115,147`).

- **18-11 retries before Git checks — FULLY RESOLVES the actionable review-mode concern; accepts the reasonable exec deferral.** Review retries stop on writes/unknown state (`P/18-12-PLAN.md:158–163`). The ledger reasonably preserves deliberate same-CLI exec resume (`P/18-11-PLAN.md:263–266`).

- **18-12 unknown Git state succeeding — FULLY RESOLVES.** Unknown states prevent spawn or successful review and produce `unverified` (`P/18-10-PLAN.md:160–166`; `P/18-12-PLAN.md:151–163`).

- **18-12 arithmetic-only deadline proof — FULLY RESOLVES the evidence gap.** `outer-race` measures actual completion under combined overhead (`P/18-12-PLAN.md:194`). Terminal stream handling still needs the separate correction above.

- **18-13 renderer plan/write race — FULLY RESOLVES the requested mitigation.** Expected-byte recheck, performed-operation reporting, intervening edit/create tests, and residual-race disclosure are specified (`P/18-13-PLAN.md:140–149,217–218`).

- **18-14 executable input validation — PARTIALLY RESOLVES.** Shared validation and path pinning are present, but exact target coverage and effective keep-value policy remain incomplete (`P/18-14-PLAN.md:156–172`; `P/18-15-PLAN.md:145–155`).

- **18-16 exclusive apply ownership — FULLY RESOLVES.** Exclusive acquisition precedes backup/writes and has a contention test (`P/18-16-PLAN.md:121–138,213–214`).

- **18-17 destination binding — FULLY RESOLVES for apply.** Canonical config identity and project/workstream refusal cases are specified (`P/18-17-PLAN.md:146–152,227`). Follow-up binding is a separate omission.

- **18-18 failed restoration terminal state — PARTIALLY RESOLVES.** Ordinary restore failures preserve assets and both errors, but cleanup ordering can delete assets before a later failure requests rollback (`P/18-18-PLAN.md:208–215`).

- **18-18 runner rollback — PARTIALLY RESOLVES.** Normal write-failure rollback is covered; cleanup failures and interrupted-add recovery remain incomplete (`P/18-18-PLAN.md:84–103,208–215`).

- **18-20 workstream effort sync — FULLY RESOLVES for explicit sync commands.** Unsupported workstream sync is skipped honestly rather than reported effective. Deferring actual workstream-aware sync is reasonable given current root-only implementation (`G/commands.cjs:789–795`; `G/install-effort-resolver.cjs:130–168`).

## Overall Assessment

### Status: Issues Found — revise before execution

Cycle 2 is materially stronger. Most cycle-1 HIGHs now have explicit mechanisms and useful tests rather than assurances. The remaining changes are concentrated and do not require redesigning the phase.

**Fix before execution:**
1. **18-15:** Move pseudo-key unset CLI wiring into Task 1.
2. **18-18:** Define the transaction commit/cleanup boundary and preserve recoverability across finalization failures.
3. **18-14:** Require every preferred target to have exactly one model or unresolved choice.
4. **18-10:** Unify terminal stream/process cleanup before final status emission.
5. **18-17:** Correct the contradictory node-call assertion.

Then tighten effective keep-value validation, review-resume permissions, and follow-up destination/approval binding.

**Overall risk: HIGH until those corrections land**, primarily because configuration recovery and unattended-runner finalization are load-bearing safety guarantees. The breadth of feature coverage and serial dependency structure are otherwise adequate.

Skipped implementation, live model calls, installer execution, and full test runs; this was read-only plan/source review. Remaining risk is accepting a plan that passes its stated tests while losing rollback assets or misreporting runner completion.

---

## Consensus Summary

One reviewer ran (`opencode-plan-review`, opencode adapter, pinned model
`router-env/my-plan-review`), so there is no cross-reviewer consensus. The review is
source-grounded: it gives `file:line` citations into the plans, the prototype
`.planning/scripts/cross-ai.mjs`, the curated-config and ai_kit_spec modules, and the
checkout-local gsd-core. Coverage is 22 of 22. The orchestrator checked every concern below
against the PLAN.md text and, where a concern cites source, against that source.

Reviewer verdict: overall risk HIGH, "revise before execution". It confirms that 11 of cycle
1's 14 HIGH items are fully resolved. Two are partly resolved (18-14 validation, and 18-18
restore/runner rollback). New issues are concentrated in runner finalization (18-10), the
apply commit boundary (18-18) and one task-order slip (18-15).

### Agreed Strengths

Single reviewer, so none are "agreed". Its main strengths: the cycle-1 fixes are real
mechanisms backed by tests, not assurances. These include the exit-driven `runChild`, async
git and listing under one lifecycle budget, the `unverified` status, the shared
`validate_plan`, the `O_EXCL`-style marker, `.new` reported as inactive, destination binding,
and the honest workstream effort-sync skip.

### Agreed Concerns

None (single reviewer). Orchestrator triage follows.

**Cycle-1 HIGH status (reviewer, confirmed by the orchestrator against plan text):**
- Fully resolved: 18-04 task order; 18-10 `close` vs `exit`; 18-10/11/12 lifecycle deadline;
  18-12 unknown tree state; 18-13 plan/write race (residual window disclosed as a `shortcut:`);
  18-16 exclusive marker; 18-17 destination binding for apply; 18-20 workstream effort sync;
  18-11 retry-before-check (review part, in 18-12).
- Partly resolved: 18-14/17 input validation. The remaining gaps are the MEDIUM items (a) and
  (b) below; they apply to hand-edited plans only and fail loudly. Also partly resolved: 18-18
  failed restore and runner rollback. The remaining gap is current HIGH 3.

**HIGH, verified and still open (3):**

1. **18-10 timeout path does not tear down the pipes** (judgment-class, text confirmed). In the
   `runChild` `<interfaces>` (`18-10-PLAN.md:141-149`), the `exit` path drains and destroys the
   pipes before SIGKILL. The budget-timer path only does SIGTERM, a bounded wait for `exit`,
   SIGKILL and resolve, so stream destruction and stopping the echo callbacks are not
   specified. The prototype echoes child stderr from a `data` callback
   (`.planning/scripts/cross-ai.mjs:291`) and ends through `process.exitCode`, not
   `process.exit` (`cross-ai.mjs:477`). A descendant that left the process group can therefore
   keep the runner alive past its deadline and write after the `AIKIT-XAI` line. Same-group
   descendants are covered, because the group SIGKILL closes their pipes. Fix: give every
   settle path (exit, timer, error, signal) one finalizer that stops the heartbeat and echo,
   destroys both pipes, kills the group and settles once. Extend `outer-race` (18-12) so that
   the resistant descendant writes stderr during shutdown, and assert that nothing follows the
   status line. This merges the reviewer's 18-12 MEDIUM.
2. **18-15 Task 1 plan-unset case vs the 18-14 placeholder** (existence-class, confirmed).
   Task 1's behavior requires `plan-unset script:cross-ai.model.pi` to work, and its action says
   the cases are "CLI-level for exit codes" (`18-15-PLAN.md:173,180`). But `_cmd_plan_unset`
   raises `plan-unset is not available in this build` until Task 2 removes the placeholder
   (`18-14-PLAN.md:229-231`, `18-15-PLAN.md:214-217`), and Task 1's `<files>` does not list
   cli.py. A CLI-level test of that case fails at Task 1's verify. Fix: drop the placeholder for
   the pseudo-key branch in Task 1 (add cli.py to its files), or state that Task 1 tests that
   case through `plan_edit.plan_unset` directly.
3. **18-18 apply has no commit boundary** (judgment-class, confirmed). `run_apply` runs
   `verify_skills`, then `discard_snapshot`, `prune_backups` and `clear_marker`, and "every
   failure after the marker is acquired goes through `_rollback`" (`18-18-PLAN.md:208-215`).
   An `OSError` in `prune_backups` or `clear_marker` therefore rolls back a fully written config
   and then fails to restore the runner, because its snapshot was already deleted. The config
   reverts while the new runner stays. A crash between `discard_snapshot` and `clear_marker`
   also leaves a marker whose recovery text names a missing snapshot. Fix: after the last config
   write and `verify_skills`, the apply is committed. From then on the cleanup steps (clear the
   marker first, or record `committed` in it, then discard the snapshot, then prune) report
   failures as warnings and never call `_rollback`. Add injected prune, discard and clear-marker
   failure cases in 18-18 Task 2. This merges the reviewer's 18-18 MEDIUM (crash window) and
   18-19 MEDIUM (finalization coverage); unit tier is enough.

**HIGH reconsidered on verification (counted as MEDIUM, below):**
- 18-14 "missing target coverage invariant". The gap is real: `validate_plan` requires `models`
  and `choices` ids to be in `prefer` and disjoint, but not that they cover `prefer`
  (`18-14-PLAN.md:167-172`). It is reachable only by hand-editing, since `plan-set prefer` adds
  `choices` rows for new ids and `plan-unset model` adds a choice (`18-15-PLAN.md:126-134`). It
  fails loudly: the runner ends `status=no_model action=stop` (18-09 `no_model` case), not
  silently. MEDIUM (a).

**MEDIUM/LOW, actionable (not yet in any PLAN.md):**
- (a) 18-14 M: `validate_plan` must require every `config.prefer` id to have exactly one of
  `models[id]` (a non-empty str) or `choices[id]`, and `router_backed` ids to be in `prefer`.
  Add one `TestPlanValidator` case.
- (b) 18-14/18-15 M: a `keep` entry's value counts as effective in the 18-15 invariants
  (`18-15-PLAN.md:145-153`), but apply skips `keep` and never writes it. A hand-edited `keep`
  whose `value` differs from its `existing` passes the command invariant while the live config
  lacks the command. Fix: `validate_plan` requires `keep` entries to have `value == existing`.
- (c) 18-12 M (raised on 18-09/18-11): review-mode retries keep the prototype resume. The codex
  `resume` argv drops the review argv's `--sandbox read-only`
  (`.planning/scripts/cross-ai.mjs:186-190`), and `codex exec resume` has no `--sandbox` flag
  (only `-c`). A review retry can therefore write; 18-12 detects that afterwards but does not
  prevent it. Fix: in review mode, retry with the fresh review argv rather than resume, or add
  `-c sandbox_mode="read-only"` to codex's review resume, and pin the retry argv in a
  `--print-argv` case.
- (d) 18-18 M (raised on 18-16): the held-marker recovery text always says "put the snapshot
  back over <runner>" (`18-18-PLAN.md:84-89`), but a planned `add` records snapshot None, and
  recovering it means deleting the added runner. Branch the text on `runner.kind` and on backup
  progress ("not taken yet").
- (e) 18-17 M: the tracer asserts "the only node call is the `-e` tables script"
  (`18-17-PLAN.md:193`), but `resolve_target` must call node-backed `config-path`
  (`18-17-PLAN.md:146-149`; `skills/ai-kit-spec-review/ai_kit_spec/gsd_tools.py:243-250`). The
  correct implementation would fail it. Assert that the node calls are exactly `config-path`
  plus the tables script, with no `config-set` or `config-new-project`.
- (f) 18-20 M: `followups` loads through `apply.load_inputs`, which checks the digest and that
  the directory exists, but not the destination binding that `resolve_target` adds
  (`18-20-PLAN.md:227-232`, `18-17-PLAN.md:140-152`). `followups --project-dir B` with project A's
  plan can run the installer or effort sync in B. Fix: reuse the binding check in
  `_cmd_followups` and add an A-to-B refusal case.
- (g) 18-22 L: `<verification>` still requires `make test validate e2e-test e2e-docker` to exit
  0, `<success_criteria>` says "every gate green", and T-18-SC says "no package installs"
  (`18-22-PLAN.md:262-273`). That contradicts the sanctioned image build and the
  `e2e-docker: blocked (network)` outcome. Align the three statements with the "passed or
  explicitly blocked" rule.

**Not actionable (verified as covered or as accepted design):**
- 18-15 M "artifact timeout vs config timeout not validated together": the runner reads
  `workflow.cross_ai_timeout` live, and the baked `outerTimeoutS` acts only as a cap and as the
  no-config fallback (18-12 behavior: 3600 gives 1770, 600 gives 570). A mismatch can only
  shorten the run, never outlive GSD's own timeout.
- 18-20 M "`--require` keeps ids, not an identical block": `followups` without `--approve`
  prints the recomputed block first, and the identity claim (`18-20-PLAN.md:99`) is about ids
  and argv from the same inputs. A receipt file was rejected in Round 3 with a reason.
- 18-01 L docstring wording ("must never hold a key"): the operative rule in the same step is
  "never return, print or log the value", which is what the tests pin. Cosmetic only.
- 18-08 L (lexical root coverage), 18-13 L (residual race), 18-21 L (`--print-argv` is not live
  access): each is already disclosed as a `shortcut:` or stated correctly. The reviewer agrees.

### Divergent Views

None (single reviewer).

## Verification coverage

Source-grounding pass (`plan_review.source_grounding` true; authority `grep` from
`drift-guard authority`):

- Method: the same classifier as cycle 1 was run over each plan body, excluding the Review
  Dispositions Ledger. 841 symbol and path references were checked against the repo
  (`skills/`, `tools/`, `tests/`, `Makefile`, config files and the checkout-local
  `.claude/gsd-core/`), up from 753 because of the cycle-1 additions. 3,027 tokens were skipped
  as non-symbols.
- MISSING after cross-plan resolution: 0 hallucinated references to existing code. The
  unresolved tokens are new symbols that a plan's own `<interfaces>`, actions or artifacts
  create. Examples are `validate_plan`, `acquire_marker`, `_claim_copy`, `snapshot_file`,
  `resolve_target`, `workstream_config`, `existing_roots`, `covered`, `runChild`,
  `finalizeBy`, `GIT_CAP_MS`, `Progress`, `_rollback` and `restore_error`, plus new test
  classes. The rest are scratch fixture paths (`skills/projskill/SKILL.md`,
  `.planning/workstreams/ws/config.json`) or external names (pi JSON fields, `enabledPlugins`,
  git env vars, stdlib).
- Every Round 3 ledger claim was spot-checked in the plan bodies, not just in the ledger. Each
  named mechanism appears outside the ledger: `ALLOWED_RELATIVE_IMPORTS` in 18-04 Task 1,
  `gcpipe`/`git-hang`/`git-before-fail` in 18-10, `list-hang` in 18-11,
  `review-gitfail`/`outer-race`/`review-flaky-edit` in 18-12, `validate_plan`/`forced` in
  18-14, `acquire_marker`/`S_IMODE`/`snapshot_file` in 18-16, `resolve_target` in 18-17,
  `restore_error`/`active` in 18-18, `workstream_config`/`--require` in 18-20, and
  `allow_nan` in 18-01.
- Reviewer citations spot-checked and confirmed:
  `tests/test_curated_config_recommend.py:1720`, `catalog_adapter.py:383`,
  `ai_kit_spec/cache.py:35-46`, `ai_kit_spec/local_secrets.py:11-25`,
  `ai_kit_spec/gsd_tools.py:235-256` (`config_path` spawns node),
  `.planning/scripts/cross-ai.mjs:186-190,256-259,285-292,477`, `commands.cjs:793-796`,
  `init.cjs:3697-3699,3718-3721`, `Makefile:133-138`.
- External check: `codex exec resume --help` on this machine lists no `--sandbox` option, only
  `-c` overrides and `--dangerously-bypass-approvals-and-sandbox`. This supports (c).
- UNCHECKABLE: function signatures and runtime behavior of not-yet-written modules, and live
  external CLI behavior (pi RPC, `opencode models`, `cursor-agent models`). None were run.

Cross-artifact fact-drift pass:

- Phase status: `drift-guard phase-status --phase 18` returned `uncheckable`
  (`phase_not_in_roadmap`; STATE.md says "Ready to execute"). Recorded, not read as consistent.
- Requirement IDs: the union of the 22 plans' `requirements` is APP-01 to APP-04, EVAL-06,
  SKL-01 to SKL-04, SPEC-05, XAI-01 and XAI-02, the same 12 IDs ROADMAP lists. No
  contradiction.
- CONTEXT.md glossary vs PLAN usage: not compared term by term (size). Partial coverage.
