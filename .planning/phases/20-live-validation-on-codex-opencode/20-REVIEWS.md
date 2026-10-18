---
phase: 20
reviewers: [opencode-plan-review]
reviewed_at: 2026-10-18T01:52:52Z
plans_reviewed: [20-01-PLAN.md, 20-02-PLAN.md, 20-03-PLAN.md, 20-04-PLAN.md, 20-05-PLAN.md, 20-06-PLAN.md]
models:
  opencode-plan-review: "router-env/my-plan-review"
model_sources:
  opencode-plan-review: "pinned"
---

# Cross-AI Plan Review — Phase 20

<!-- gsd:plan-revision-conflicts:begin -->
## Plan-Revision Conflicts
<!-- gsd:plan-revision-conflicts:end -->

Reviewer lane: `review.default_reviewers = ["opencode-plan-review"]` (reviewer instance on the
opencode adapter, model `router-env/my-plan-review`, no effort flag: `review.effort.opencode` is
`inherit` on purpose because gsd-core renders `--variant`, which opencode v2 removed). The lane ran
once with `opencode run --standalone`, exit 0, no stderr. Plan coverage: 6/6 ids.

## OpenCode Review (opencode-plan-review)

I'll review these six Phase 20 plans against the actual repository. Let me start by verifying the referenced files, functions, and claims.
### Document type
GSD · implementation plans · read-only, source-grounded review

Plan references below are relative to `.planning/phases/20-live-validation-on-codex-opencode/`. All six plans were read from disk and checked against relevant source, tests, specification, context, and research.

## 20-01

### Summary
The approach is sound: extend the existing oracle, preserve independent plan-derived expectations, and add non-Claude controls. However, the specified tier-comparison rule would reject correct Claude overrides, violating the required unchanged-Claude baseline.

### Strengths
- **Reuses the right source of truth.** `.claude/gsd-core/bin/lib/model-catalog.cjs:13` exports all three required tables, including `RUNTIME_PROFILE_MAP`; loading them together avoids hardcoded host mappings.
- **Preserves meaningful negative controls.** The existing `_control_one` requires nonempty expected failures and checks that each expected agent fails (`tests/gsd_curated_eval.py:732-747`). Removing non-Claude overrides while comparing against the original promise preserves that discrimination.
- **Retains existing safety assertions.** The matrix suite checks both repository config/runner bytes and the protected snapshot (`tests/test_ai_kit_gsd_curated_config_matrix.py:115-124`).

### Concerns
- **HIGH — The new tier rule regresses Claude overrides.** `20-01-PLAN.md:169-175` says to use `_tier_for(...)` for Claude override agents, then claims this preserves existing behavior. Currently, `compare` checks a tier-alias override against the **promised alias**, not the underlying profile tier (`tests/gsd_curated_eval.py:505-515`). gsd-core likewise reports the override alias as its tier (`.claude/gsd-core/bin/lib/model-resolver.cjs:438-451`). An override to `haiku` over a `sonnet` profile would therefore fail despite resolving correctly. Concrete Claude overrides would also acquire an inappropriate profile-tier check.
- **MEDIUM — Missing runtime-table evidence becomes an inheritance promise.** `20-01-PLAN.md:153-163` normalizes unavailable/malformed `runtime_profiles` to `{}` and interprets missing entries as intentional inheritance. This conflates “the loaded map genuinely lacks this tier” with “the map was not available.” The resolver wrapper also converts subprocess/parsing failures into empty fields (`tests/gsd_curated_eval.py:632-648`), so these states need explicit separation.

### Suggestions
- Specify four comparison cases:
  1. Claude alias override: tier equals the promised alias.
  2. Claude concrete override: no inferred profile-tier assertion.
  3. Non-Claude override: model check without inferred tier.
  4. No override: model and `_tier_for(...)`.
- Add regression cases where the override alias differs from the profile tier.
- Refuse unavailable/malformed runtime maps on non-Claude hosts; permit inheritance only after successfully loading the map.

### Risk assessment
**HIGH.** The proposed rule is likely to block the required Claude regression matrix immediately. The correction is small and localized.

## 20-02

### Summary
This plan correctly separates model resolution from installer baking and introduces valuable isolation and idempotency checks. Its main weakness is that the proposed inventory assertions can validate the wrong installation, while the installer boundary has transitive host-CLI activity that the threat model does not account for.

### Strengths
- **Separates resolve-only configuration from baked output.** The installer explicitly treats an unresolved model as omission, not an empty frontmatter value (`.claude/gsd-core/bin/lib/install-model-override-resolver.cjs:251-272`).
- **Uses existing orchestration and hashing mechanisms.** `_step` records failures so later snapshot checks can execute (`tests/gsd_curated_eval.py:3904-3912`); reusing it is preferable to another smoke framework.
- **Addresses a real shadowing problem.** The current scratch builder always creates the Claude symlink (`tests/gsd_curated_eval.py:3915-3928`), so host-specific scratch setup is necessary.

### Concerns
- **HIGH — Scratch inventory still resolves from ai-kit’s root.** `_cmd_smoke` sets `RUNTIME_DIR=REPO_ROOT` (`tests/gsd_curated_eval.py:4337-4343`), and `_inventory` passes that environment unchanged (`:3955-3959`). `project_root` prioritizes `RUNTIME_DIR` over the supplied project (`skills/ai-kit-spec-review/ai_kit_spec/gsd_tools.py:33-40`). `host.resolve_gsd_core` then uses that root for candidate selection **and** its local-scope classification (`skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/host.py:126-136`). Consequently, the checkout’s Claude installation can satisfy both proposed assertions—`scope == local` and matching version—without selecting the scratch-host installation.
- **HIGH — Empty Opencode promises conflict with the baked comparison.** `20-02-PLAN.md:199-202` uses `promised(...)` directly and requires exact equality, but that oracle returns `""` for inheritance. The baked reader returns `None` for an absent line (`:297-302`). Correct omission therefore fails. gsd-core explicitly requires omission rather than `null` or `""` (`.claude/gsd-core/bin/lib/install-model-override-resolver.cjs:256-272`).
- **HIGH — The installer’s transitive probes are not contained.** The cached installer’s finish path invokes generation/data-directory probes. The installed helper executes `opencode debug paths` without `--standalone` and honors inherited `XDG_DATA_HOME` (`.claude/gsd-core/bin/lib/opencode-version.cjs:409-435`). Replacing only HOME and XDG_CONFIG_HOME does not substantiate the plan’s claim that installation never reaches the managed-service/data boundary.
- **MEDIUM — The TOML exception is broader than D-10.** `20-02-PLAN.md:249-254` ignores every project whose string starts with the system temp directory. D-10 permits scratch-project trust exceptions (`20-CONTEXT.md:134-140`), not arbitrary temporary projects or prefix neighbors such as `/tmp-backup`.
- **MEDIUM — Directory listings cannot prove byte-identical configuration.** The proposed guards use `_dir_names`, which captures only immediate entry names (`tests/gsd_curated_eval.py:183-188`). Overwriting an existing agent, plugin, or nested skill file is invisible. This is narrower than the byte-identical claim at `20-02-PLAN.md:234`.

### Suggestions
- Give scratch inventory a project-scoped environment and assert the exact resolved root is `<scratch>/.<host>/gsd-core`.
- Normalize empty oracle promises to `None` for baked-file expectations, while still rejecting an explicitly present empty `model:` line.
- Source-trace and contain installer subprocesses and inherited data-directory overrides; add a controlled-PATH test.
- Exempt only run-owned scratch trust entries using path-aware containment.
- Either strengthen directory protection or consistently describe the guard as file hashes plus name listings—not byte identity.

### Risk assessment
**HIGH.** The current plan can produce false-positive installation evidence and makes stronger isolation claims than the source supports.

## 20-03

### Summary
The generator-based runner update and policy tests are appropriate. Two delivery issues remain: the repair is bootstrapped through the runner it intends to repair, and keeping the same template version prevents the fix from reaching existing template-3 installations.

### Strengths
- **Uses the established safe-upgrade mechanism.** `plan_runner_upgrade` preserves older edited runners by generating `.new`, and `_upgrade_config` carries forward CONFIG while refreshing the scrub list (`skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cross_ai_script.py:227-264`).
- **Tests real enforcement points.** Lane recommendation excludes the host slug (`skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cross_ai.py:202-230`), and plan validation independently rejects it (`skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/plan_io.py:542-550`).
- **Covers resume indirectly.** Opencode resume builds from the exec/review argv builders (`skills/ai-kit-spec-review/references/cross-ai.mjs:277-279`), so placing the flag there covers resumed calls too.

### Concerns
- **HIGH — Existing template-3 runners will not receive the fix through `ensure-runner`.** `20-03-PLAN.md:171-172` forbids a version bump. However, `plan_runner_upgrade` returns pristine current-version runners unchanged (`skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cross_ai_script.py:250-265`), explicitly pinned by `tests/test_curated_config_script.py:412-422`. This checkout’s template-1 runner upgrades; existing template-3 users can retain the unsafe argv.
- **HIGH — Bootstrap precedes the safety repair.** This plan is itself `cross_ai: true`. The repository enables delegation through the old runner (`.planning/config.json:45-47`), and GSD invokes that configured command before the executor starts its tasks (`.claude/gsd-core/workflows/execute-phase/detail/elaboration.md:82-99`). The same-wave coordination note does not protect the initial dispatch of 20-03—or an earlier 20-01 dispatch—from the old fallback.
- **MEDIUM — Failure cleanup can destroy pre-existing or concurrent work.** `20-03-PLAN.md:189-192` unconditionally restores the tracked runner and deletes `.new`. This defeats the generator’s explicit concurrent-change preservation (`skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cross_ai_script.py:381-391`).

### Suggestions
- Bootstrap the runner repair natively before any delegated Phase 20 dispatch.
- Use the existing template-version migration mechanism if installed runners must receive this safety fix.
- Save and compare the initial runner/`.new` state; restore only task-owned changes and preserve unexpected contents.

### Risk assessment
**HIGH.** The local edit is small, but its bootstrap and upgrade behavior leave the unsafe path reachable.

## 20-04

### Summary
The evidence structure and distinction between headless preparation and interactive acceptance are strong. Execution is blocked by a fundamental mismatch with runner success semantics, compounded by unsafe enumeration scope, incomplete process proofs, and an insufficient enclosing timeout.

### Strengths
- **Honest evidence classification.** `20-04-PLAN.md:76-78` explicitly refuses to count headless runs as EVAL acceptance, matching `20-SPEC.md:105`.
- **Reuses the supervision contract.** The runner already supplies signal cleanup, status lines, and detached child handling (`skills/ai-kit-spec-review/references/cross-ai.mjs:548-582`).
- **Correctly limits the effort claim.** Acceptance without rejection is distinguished from proof that effort was applied (`20-04-PLAN.md:271-286`).

### Concerns
- **HIGH — Healthy smoke runs cannot normally produce the required `status=ok`.** The plan forbids tracked edits while dispatching with `--mode exec` and requiring `ok` (`20-04-PLAN.md:181-185`). The runner deliberately classifies successful unchanged-tree execution as `no_change` (`skills/ai-kit-spec-review/references/cross-ai.mjs:2903-2910,2936-2937`). Outputs go into ignored `tmp/` (`.gitignore:17`) or external scratch projects; fully ignored directory contents are excluded from tree-change detection (`cross-ai.mjs:736-739`). The word-only liveness and `#high` probes have the same problem.
- **HIGH — The Opencode signal-cleanliness rule rejects its own marker.** The plan permits only `OPENCODE` from the scrub set. Yet the research records that Opencode’s tool shell sets `AI_AGENT` itself (`20-RESEARCH.md:292-297`), and that name belongs to `HOST_SIGNAL_ENV_VARS` (`skills/ai-kit-spec-review/ai_kit_spec/detection.py:196-205`). A child may legitimately recreate its own marker after inherited signals were scrubbed.
- **HIGH — “Per-host” fresh inventory enumerates other installed runtimes.** `inventory --refresh` invokes `detect-runtimes` (`skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/catalog_adapter.py:166-170`), which loops over all installed CLIs (`skills/ai-kit-spec-review/ai_kit_spec/detection.py:1003-1010`). The Cursor listing explicitly rewrites its global privacy cache (`:304-311`). Thus a Codex/Opencode probe can cause a known unrelated protected-config write.
- **HIGH — Signal probes do not prove owned-child cleanup or accelerated escalation.** CLI children have separate process groups (`cross-ai.mjs:580-582`), so checking the runner’s group is insufficient. The temp search misses the runner’s `cross-ai-*` directory (`:837`). Sending the second signal at one second also overlaps normal escalation (`:556-560`), making the result ambiguous.
- **HIGH — The enclosing delegated plan can expire before a permitted child run.** The configured plan timeout is 1,800 seconds (`.planning/config.json:47`), enforced around the entire executor (`.claude/gsd-core/workflows/execute-phase/detail/elaboration.md:99`). This plan allows one smoke alone 2,400 seconds, followed by another host and several probes.

### Suggestions
- Define an evidence-only dispatch success rule that accepts a healthy `no_change` result with `cli_rc=0` and independently validates smoke exit/artifacts. Do not manufacture repository edits to obtain `ok`.
- Distinguish foreign inherited signals from target-generated generic markers.
- Scope live enumeration to the selected runtime without invoking unrelated CLIs.
- Capture child PGIDs through `--child-pgid-file`, wait for actual readiness, and inspect a run-owned TMPDIR.
- Run long-lived orchestration natively or split it into separately supervised bounded units.

### Risk assessment
**HIGH.** As written, successful runs can fail acceptance, while enumeration and cleanup procedures can violate their own safety claims.

## 20-05

### Summary
Evidence-driven labels, explicit uncertainty, and digest-bound judging are good choices. This plan needs tighter handling of conditional evidence outcomes and a clearer distinction between an installer-layout validation and validation of the actual shipped follow-up command.

### Strengths
- **Keeps capability claims conservative.** `host_can_select` only accepts models listed in verified native selectors (`skills/ai-kit-spec-review/ai_kit_spec/routing.py:44-56`); pinning empty selectors avoids an unsupported native-selection claim.
- **Binds reviews to actual skill content.** The digest covers SKILL.md plus sorted references, and the checker rejects mismatching live evidence rows (`tests/gsd_curated_eval.py:353-409`).
- **Updates existing note-producing paths.** Installer and effort notes are already assembled centrally by `build_followups` (`skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/followups.py:360-386`).

### Concerns
- **MEDIUM — A dropped/replacement signal can desynchronize runner scrub lists.** Task 1 conditionally changes `HOST_SIGNAL_ENV_VARS`, while claiming runner lists remain equal (`20-05-PLAN.md:203-225`). The template contains a literal scrub array (`skills/ai-kit-spec-review/references/cross-ai.mjs:77-89`), and 20-03 has already generated the project runner. Neither runner appears in this plan’s changed-file list. The common “keep both” outcome avoids this, but the advertised alternative branches are incomplete.
- **MEDIUM — “Installer follow-up verified” overstates the exercised path.** The smoke runs cached `node install.js` with an isolated HOME and `--no-legacy-cleanup`. The shipped follow-up uses `npx`, registry flags, real execution environment, and omits that cleanup flag (`skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/followups.py:49-59,181-188`). The smoke validates installation behavior/layout, not the complete follow-up invocation.
- **MEDIUM — Conditional evidence handling conflicts with unconditional acceptance.** Task 2 says to retain uncertain wording when a probe is not reached or does not establish the root (`20-05-PLAN.md:267-290`), but its acceptance criteria require all relevant uncertainty strings and the local-root limit to disappear (`:319-320`). An executor cannot satisfy both honestly in those branches.

### Suggestions
- Make runner synchronization explicit for every detection-table change, or retain a deliberate scrub superset and describe that contract accurately.
- Label the cached-installer result narrowly: verified local layout and host flags; registry launcher and global side effects not exercised.
- Define separate passing, blocked, and unresolved acceptance outcomes instead of unconditional string-removal gates.

### Risk assessment
**MEDIUM.** The expected evidence path is manageable, but alternative outcomes currently encourage stale configuration or overconfident labels.

## 20-06

### Summary
The fresh interactive baseline and explicit user handoff are useful. However, the scripts do not preserve the artifacts they promise to return, and they make mandatory phase evidence optional. Several final gate checks also contradict the actual test-runner output.

### Strengths
- **Correct aggregate test entry point.** `make test` already includes unit, integration, e2e, and architecture tiers (`Makefile:50-74`), so avoiding a separate full e2e invocation is sensible.
- **Fresh baseline avoids unrelated historical changes.** Taking the interactive snapshot after starting the TUI is explicitly described at `20-06-PLAN.md:163-178`.
- **Keeps acceptance visibly pending.** The scripts state that headless runs are not EVAL evidence (`20-06-PLAN.md:216-218`).

### Concerns
- **HIGH — The requested return artifacts are deleted and are not embedded in smoke evidence.** The script claims plan/config/resolve output “live inside the smoke evidence” (`20-06-PLAN.md:199-202`). The renderer currently emits step summaries, matrix counts, controls, protected-set status, and key paths—not those artifacts (`tests/gsd_curated_eval.py:4281-4318`). Plan 20-02 adds summary sections, not full plan/config/per-agent resolved records. The default command then deletes the work directory (`:4358-4359`). This prevents the promised post-run analysis required by D-01 (`20-CONTEXT.md:39-41`).
- **HIGH — Required lane mechanics and loader evidence become optional.** D-11 explicitly retains two trials per route (`20-CONTEXT.md:143-151`), and the specification requires project-agent precedence evidence (`20-SPEC.md:59-71`). The script makes both optional (`20-06-PLAN.md:181-194`). Asking the model which model an agent uses is also not a loader observation; it can answer by reading the same baked file being tested.
- **MEDIUM — Final acceptance asks for output the gates deliberately suppress.** The parallel runner prints module summaries and only emits full output on failure (`tools/run_unittest_parallel.py:213-224`), so passing `make test` does not name the three matrix classes. The plan also acknowledges pre-commit hides passing output, then requires `Ran N tests` inside `validate.txt` (`20-06-PLAN.md:259-262,302`). Those checks contradict the separate verbose files it creates.
- **MEDIUM — Container failure is not enforced by the automated verification.** The intended rule is container success or the exact missing-engine finding, but the verification checks only that `docker.txt` is nonempty (`20-06-PLAN.md:298`). A genuine failed container run can satisfy that check.

### Suggestions
- Export sanitized plan, resulting config, and per-agent resolve/baked records before cleanup; include their paths in the send-back list.
- Keep EVAL-05 pending until mandatory mechanics and precedence evidence exists, or formally amend the governing requirements before making those checks optional.
- Use observable loader/tool/session metadata rather than model self-report for precedence.
- Read class names from `matrix.txt` and verbose hook counts from `validate-unittest.txt`; preserve command exit codes.
- Explicitly verify container success or the allowed missing-engine outcome.

### Risk assessment
**HIGH.** The proposed handoff can complete without the evidence needed to close the phase, even when all generated documents look finished.

## Overall assessment

### Status: Issues Found — revise before execution

**Coverage: 6/6 plans reviewed.**

The core architecture does not need replacing. The highest-priority corrections are:

1. Fix Claude override-tier comparisons.
2. Prove scratch inventory selects the scratch installation.
3. Bootstrap and version the runner repair correctly.
4. Align evidence-only runs with runner `no_change` semantics.
5. Contain enumeration and installer subprocess side effects.
6. Preserve return artifacts and retain mandatory EVAL evidence gates.

Skipped: execution, live host sessions, provider/model availability checks, and credential access; no repository files were changed.  
Residual risk: runtime behavior remains unverified, and the current plans can report either false failures or incomplete validation as successful preparation.

---

## Consensus Summary

One reviewer ran this cycle, so there is no cross-reviewer consensus and the consensus gate is
skipped; a single reviewer's HIGH counts. The review cites `file:line` evidence throughout and
carries no evidence-quality discount marker. Every claim below was re-checked by the orchestrator
against the plan text and the source before counting.

### Agreed Strengths
- The oracle extension reuses gsd-core's live `RUNTIME_PROFILE_MAP` instead of hardcoded host
  tables, and the non-claude Control 1 keeps the discriminating-control shape.
- Headless runs are never counted as EVAL evidence; the effort-suffix probe is labelled as
  acceptance only.
- The runner sync goes through the product's own `ensure-runner`/`.new` path.

### Agreed Concerns (verified, counted)
HIGH, each re-verified against source:
1. 20-01: the tier rule (`20-01-PLAN.md:172-175`) says "otherwise `_tier_for(...)`" for claude
   override agents while claiming the old rule stays. gsd-core reports an override alias as the
   tier (`.claude/gsd-core/bin/lib/model-resolver.cjs:438-450`), and the current `compare` checks
   the tier only against the promised alias (`tests/gsd_curated_eval.py:505-515`). Taken
   literally, the rule regresses the claude matrix for any alias override that differs from the
   profile tier.
2. 20-02: the scratch inventory resolves gsd-core from ai-kit's root. `_cmd_smoke` sets
   `RUNTIME_DIR=REPO_ROOT` (`tests/gsd_curated_eval.py:4337-4343`, `RUNTIME_DIR` at `:4339`), `project_root` prefers
   `RUNTIME_DIR` (`skills/ai-kit-spec-review/ai_kit_spec/gsd_tools.py:38-39`), and
   `resolve_gsd_core` uses that root for both selection and the scope label
   (`skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/host.py:127-135`). So
   `scope == local` and `version == 1.17.0` pass on the checkout's own `.claude/gsd-core`, not the
   scratch install.
3. 20-02: the threat model leaves out the installer's opencode probes. A `--opencode --local`
   install without `GSD_TEST_MODE` runs `detectOpencodeGeneration`, `opencode debug paths` (no
   `--standalone`) and a read-only sqlite read of the data dir's `opencode.db` (cached 1.17.0
   `bin/install.js:13868-13893`, `.claude/gsd-core/bin/lib/opencode-version.cjs:409-435`). An
   inherited `XDG_DATA_HOME` points that read at the real data dir. T-20-03 names only
   `writeNonClaudeDefaults` and `cleanupLegacyGsdCc`.
4. 20-03: there is no template version bump, so `ensure-runner` keeps every existing pristine or
   edited template-3 runner as it is (`cross_ai_script.py:250-265`). Only this repo's template-1
   runner gets `--standalone`.
5. 20-03: this plan is `cross_ai: true` and is dispatched through the old runner
   (`.planning/config.json:46`). That runner falls back pi > cursor > opencode with no
   `--standalone`, so the dispatch that applies the fix itself still runs on the unsafe path.
6. 20-04: an exec run that leaves the tree clean finishes `no_change`, not `ok`
   (`skills/ai-kit-spec-review/references/cross-ai.mjs:2906-2910,2936-2937`). Writes under the
   gitignored `tmp/` count as no change (`cross-ai.mjs:736-739`). The required
   `AIKIT-XAI status=ok cli=codex|opencode` lines (Task 1/2 verify) cannot appear for a healthy
   smoke or for the `#high` probe.
7. 20-04: the opencode signal check rejects opencode's own marker. opencode's bash tool sets
   `AI_AGENT ||= "opencode"` (`20-RESEARCH.md:292-296`), and `AI_AGENT` is in
   `HOST_SIGNAL_ENV_VARS` (`detection.py:201-205`, 11 names verified live). The acceptance check
   allows only `OPENCODE`. The orchestrator found this independently as well.
8. 20-04 Task 3(c): `inventory --refresh` runs `detect-runtimes` over every installed CLI
   (`catalog_adapter.py:166-170`, `detection.py:1003-1010`). `cursor-agent models` rewrites
   `~/.cursor/cli-config.json` privacyCache (`detection.py:304-308`), which breaks the plan's
   own "nothing under ~/.cursor" rule.
9. 20-04 Task 3(b): CLI children are spawned `detached: true` in their own group
   (`cross-ai.mjs:579-582`), so the "no process of the recorded pgid" check misses them. The
   runner's temp dir prefix is `cross-ai-` (`cross-ai.mjs:837`), but the `find` looks for
   `aikit-*`/`xai-*`. `--child-pgid-file` exists (`cross-ai.mjs:36,933`) and is not used.
10. 20-04 (also 20-05 Task 3): every plan is `cross_ai: true`, and GSD wraps the whole executor in
    `run-with-timeout ${CROSS_AI_TIMEOUT}` = 1800 s (`.planning/config.json:47`,
    `.claude/gsd-core/workflows/execute-phase/detail/elaboration.md:99`). Child runs set
    `--timeout 2400 --outer-timeout 2430` (20-04) and `--timeout 1800 --outer-timeout 1830`
    (20-05 pi judge), so they can outlive their parent.
11. 20-06: D-01 needs plan.json, the resulting config.json and the resolve-model output analyzed
    after the run. `render_smoke_evidence` emits none of them
    (`tests/gsd_curated_eval.py:4281-4318`), and `_cmd_smoke` deletes the work dir
    (`:4358-4359`). Only `--keep-scratch` keeps it, and the main step-3 smoke does not pass it.
12. 20-06: the D-11 two-trials-per-route mechanics (`20-CONTEXT.md:150-151`) and the SPEC R5
    precedence evidence ("The run shows that opencode loads the project agents over any global
    ones", `20-SPEC.md:64-66`) are demoted to optional steps without an amendment. The
    precedence step also relies on the model's self-report.

Actionable MEDIUM, verified:
- 20-01: a missing or malformed `runtime_profiles` becomes `{}`, then `""` (an inheritance
  promise) without a refusal (`20-01-PLAN.md:153-163`).
- 20-02: `startswith(tempfile.gettempdir())` also exempts sibling prefixes and every temp
  project, not only this run's scratch dirs (`20-02-PLAN.md:249-254`).
- 20-02: `_dir_names` (`tests/gsd_curated_eval.py:183`) lists names only, so the
  "byte-identical" acceptance (`20-02-PLAN.md:234`) overclaims for agents, commands, skills and
  plugins.
- 20-03: the failure path restores the tracked runner and deletes `.new` without checking
  whether that state was task-owned (`20-03-PLAN.md:189-192`).
- 20-05: if `CODEX_VERSION` is dropped, `HOST_SIGNAL_ENV_VARS` changes, but the template's
  literal `scrubEnv` (`cross-ai.mjs:77-89`) and the project runner are not in files_modified.
  `tests/test_ai_kit_spec.py:11561` pins template `scrubEnv == sorted(HOST_SIGNAL_ENV_VARS)` and
  Task 1's `-k` verify does not run it.
- 20-05: `_codex_installer_note` "verified" overstates the evidence. The smoke ran a cached
  `node install.js --no-legacy-cleanup` under a throwaway HOME, not the shipped
  `npx --registry ...` argv (`followups.py:49-59`).
- 20-05: Task 2 keeps the wording "else unchanged" when the evidence does not support a change,
  but its acceptance requires `unverified until Phase 20` and the `local gsd root` row to
  disappear unconditionally (`20-05-PLAN.md:319-320`).
- 20-06: the acceptance criteria ask `test.txt` to name the three matrix classes and
  `validate.txt` to hold `Ran N tests`. Neither runner prints these on success
  (`tools/run_unittest_parallel.py:218-224`; pre-commit hides passing output). The verify reads
  `matrix.txt`/`validate-unittest.txt` instead, and the must_have says the classes come from
  `make test`'s own output.
- 20-06: the verify checks only `test -s tmp/p20/gates/docker.txt`, so a failed container run
  passes. podman is on PATH on this machine, so the container run will happen.

### Not counted (claim already handled by the plan)
- 20-02 "empty opencode promise vs None in the baked comparison" (reviewer HIGH): 20-02 Task 3
  already says "an agent with the empty promise must have no `model:` line (SPEC R5 empty)"
  (`20-02-PLAN.md:300-302`). Task 3 owns the opencode reader and rule.

### Divergent Views
None (single reviewer). The orchestrator would rate items 3 and 4 MEDIUM on impact: item 3 is a
read-only probe and the D-10 guard still catches config writes; item 4 is out of this repo's
scope. They are counted HIGH under the single-reviewer rule.

## Verification coverage

Source-grounding authority: `grep` (`drift-guard authority --raw`). Severity map
(`drift-guard severity --authority grep`): VERIFIED = none, MISSING = needs-acknowledgement,
AMBIGUOUS = MEDIUM, UNCHECKABLE = INFO. Symbols in each plan's "Artifacts this phase produces"
list are excluded.

20-01
- "`_LIVE_TABLES_SCRIPT`, `live_tables`, `promised`, `_set_entries`, `compare`" (20-01:141): VERIFIED `tests/gsd_curated_eval.py:436,444,470,495,505`
- "`_mismatches`", "`_unoverridden`, `_write_control_plan`, `_control_one`", "`run_matrix`", "`_cmd_matrix`" (20-01:141): VERIFIED `:655,705,714,727,808,2237`
- "`_seed_runtime_key`, `_informational_row`", "`_render_matrix`", "`render_smoke_evidence`" (20-01:222): VERIFIED `:768,782,2267,4281`
- "Delete `MESSAGE_NON_CLAUDE`" (20-01:230): VERIFIED exists `:114`; `WHY_INFORMATIONAL` `:118`
- "Delete the `inheritance_promised` keyword" (20-01:166-168): VERIFIED `:470,505,661`
- "`live_tables` points ... at `bin/lib/model-catalog.cjs` ... `model-profiles.cjs` only re-exports it" (20-01:150-152): VERIFIED `.claude/gsd-core/bin/lib/model-catalog.cjs:13,85`; `model-profiles.cjs:10-24` re-exports without `RUNTIME_PROFILE_MAP`
- "`RUNTIME_PROFILE_MAP[host][tier]` ... a dict with a `model` key or a bare string" (20-01:62,161): VERIFIED live: codex/opencode entries are `{model: ...}` dicts
- "35 agents", "matrix ok (420 checks)" (20-01:21,210): VERIFIED live `MODEL_PROFILES`/`AGENT_TO_PHASE_TYPE` both 35 keys
- "keeps the old `expected in _TIERS` rule" (20-01:175): VERIFIED `_TIERS` `:123`; see HIGH 1 (the plan text contradicts it)
- "`refuse_repo_apply`" (20-01:29): VERIFIED `:558`; "`_refusal` style" (20-01:201): VERIFIED class `:72`
- "`_row_for`" (20-01:189): VERIFIED `:681`
- "`TestOracle` (lines 87-206), `TestMatrixEnv` (403-461)" (20-01:142): VERIFIED `tests/test_gsd_curated_eval.py:87,403`
- "`test_matrix_refuses_non_claude_host`", "`test_matrix_cli_host_refusal_is_exit_2`", "`test_inheritance_promised_accepts_empty`", "`_StopRun`" (20-01:197,223,233-236): VERIFIED `:446,686,117,57`
- "`TestResolveModelMatrix`", "`test_repo_config_untouched`", "`test_output_carries_no_absolute_path`", "whole file, 128 lines" (20-01:224,238-243): VERIFIED `tests/test_ai_kit_gsd_curated_config_matrix.py:33,115,106`, 128 lines
- "The module stays in `E2E_MODULES`" (20-01:246): VERIFIED `tools/run_unittest_parallel.py:53-58`
- "`GSD_CORE_LABEL`" (20-01:277): VERIFIED `:92`

20-02
- "`SmokeCtx`", "`_step`, `_scratch_project`", "`_inventory`", "`_smoke_ai_kit`, `_smoke_project_a`, `_smoke_project_b`", "`run_smoke`", "`_smoke_placeholders`, `render_smoke_evidence`, `_cmd_smoke`", "`_build_parser`" (20-02:151): VERIFIED `tests/gsd_curated_eval.py:3653,3904,3915,3945,4056,4075,4183,4223,4263,4281,4321,4362`
- "`local_gsd_core_roots` order" (20-02:152): VERIFIED `skills/ai-kit-spec-review/ai_kit_spec/gsd_tools.py:85-93`
- "`_HOST_FIRST_ROOT`, scope label" (20-02:152): VERIFIED `host.py:21-25,135`
- "`gsd_tools.gsd_core_version` of `GSD_TOOLS_PATH`" (20-02:165): VERIFIED `gsd_tools.py:358`, `tests/gsd_curated_eval.py:94`
- "`- version: 1.17.0` (the value of `.claude/gsd-core/VERSION`)" (20-02:231): VERIFIED `1.17.0`
- "`node <installer>/bin/install.js --<host> --local --no-legacy-cleanup`" (20-02:20): VERIFIED cached 1.17.0 `bin/install.js:901,968,971,1215-1220`
- "cached ... `~/.npm/_npx/*/...` or `~/.cache/pnpm/dlx/*/*/...`" (20-02:80-81): VERIFIED live: 1.17.0 copies exist under both layouts (names only)
- "`writeNonClaudeDefaults`, `cleanupLegacyGsdCc`" (20-02:359): VERIFIED cached `bin/install.js:7087,14663`; `generateCodexAgentToml` (20-02:198): VERIFIED `:4116`
- "`_strict_files`, `_strict_listings`, `_host_managed_files`, `_tree_sha`, `snapshot`, `snapshot_diff`, `_snapshot_report`" and "`CREDENTIALS_BASENAME`" (20-02:244): VERIFIED `:191,219,231,251,274,293,301,98`
- "`_file_sha`", "`_dir_names`", "`HOME_LABEL`" (20-02:255-260): VERIFIED `:177,183,90`
- "`_ScratchPaths.seed`, `TestSnapshot`, `test_credentials_file_is_never_snapshot`, `test_report_lines_name_labels_only`" (20-02:245): VERIFIED `tests/test_gsd_curated_eval.py:207,242,292,262`; `TestSmoke` `:2466`
- "the `finally: shutil.rmtree(work, ignore_errors=True)`" (20-02:292): VERIFIED `:4359`
- "`snapshot --out`/`--check`", "`secret-scan`" (20-02:276,339): VERIFIED parser `:4370-4373,4390`; `snapshot ok` `:331`
- "`tempfile.mkdtemp()` under the system temp dir" (20-02:31): VERIFIED `_cmd_smoke` `mkdtemp(prefix="smoke-")` `:4335`
- "`opencode debug agents` has no `--standalone`" (20-02:293): VERIFIED live: `opencode debug --help` lists `agents`; `opencode run --help` lists `--standalone` (v2.0.31)

20-03
- "`RUNTIMES.opencode`: `exec`, `review`, `resume`" (20-03:156): VERIFIED `skills/ai-kit-spec-review/references/cross-ai.mjs:276-285` (plan cites 270-285)
- "self-test `argv-exec-<rt>` and `argv-review-<rt>` ... `must` and `never` lists" (20-03:156): VERIFIED `:1566-1597`
- "`childEnv`, `withExtra`" (20-03:156), "`listModels`" (20-03:156): VERIFIED `:775,782,672`
- "header `template=3 sha256=UNSTAMPED`" (20-03:204): VERIFIED `:2`
- "`.planning/scripts/cross-ai.mjs` lines 1-2 (header `template=1`)" (20-03:159): VERIFIED; `script_state` = `edited` (live)
- "`_plan_rendered`, `plan_runner_upgrade`, `_upgrade_config`", "`ensure_runner`", "`_READY_TEMPLATE` stays 3", "`template_config`, `script_state`, `template_version`" (20-03:158,172,205): VERIFIED `cross_ai_script.py:192,242,227,366,31,83,57,72`
- "`ensure-runner --cwd .` ... exit 0 ready, 1 not ready, 2 error" (20-03:158,174): VERIFIED `cli.py:225-242,767-769`; SKILL.md `:259`
- "upgrade ... keeps `prefer` and the five `models` entries" (20-03:178): VERIFIED live: an in-memory upgrade render of the current runner keeps them and passes `--self-test` (`self-test ok`); it also carries the legacy keys `timeoutMarginS`/`defaultOuterTimeoutS` (harmless)
- "`eligible_lanes`: the `slug in (host, "pi")` skip" (20-03:216): VERIFIED `cross_ai.py:202,217`
- "`_host_reviewer_problem`" (20-03:216): VERIFIED `plan_io.py:542-550`
- "`make_inventory`, `entry_map`, `build`" (20-03:217): VERIFIED `tests/test_curated_config_recommend.py:256,327,331`
- "`_fixture_review_lanes`, `_review_lane_accepted_keys` ... 1705-1740" (20-03:217): AMBIGUOUS (line drift): the symbols are at `:1547,1565`; the names resolve
- "`test_host_slug_never_a_review_lane`; `_write_pair(tmp, host=...)`, `_run_plan_set`" (20-03:218): VERIFIED `tests/test_curated_config_plan_edit.py:397,55,37`
- "`tests.test_cross_ai_runner_e2e tests.test_curated_config_script`" (20-03:198): VERIFIED files exist
- "`workflows/review.md:126-149`, `SELF_CLI=auto`" (20-03:242): VERIFIED `.claude/gsd-core/workflows/review.md:126-150`

20-04
- "`--no-preamble`", "`--codex-sandbox workspace-write`", "`--timeout`/`--outer-timeout`", "`--print-argv`" (20-04:184): VERIFIED `cross-ai.mjs:27-33,920-931`
- "`CONFIG.scrubEnv`" (20-04:160): VERIFIED `:77-89`; "`codexExecArgv` (line 353)" VERIFIED `:353`; "`parseOpencode`" VERIFIED `:367`
- "signal handling (786-800)", "`sigterm-*` self-test cases" (20-04:328): VERIFIED `:786-800,1822-1849`
- "`parse_status_line`", "`_runner_reason`" (20-04:161): VERIFIED `runner_dispatch.py:200,504`
- "`HOST_SIGNAL_ENV_VARS`, the 11 names" (20-04:329): VERIFIED `detection.py:201`, 11 names live
- "`node .claude/gsd-core/bin/gsd-tools.cjs run-with-timeout 600 --`" (20-04:346): VERIFIED live usage line
- "`codex exec --ephemeral --ignore-user-config --skip-git-repo-check --sandbox read-only -C ... --json -o`" (20-04:337): VERIFIED live `codex exec --help` (codex-cli 0.162.1)
- "`codex debug models`" (20-04:171): VERIFIED live
- "`inventory --project-dir . --host opencode`", "`recommend --inventory ... --profile adaptive --rigor standard --out`", "`--refresh`" (20-04:250-253,364): VERIFIED `cli.py:845-866`
- "`runtime_enumeration`" (20-04:365): VERIFIED `inventory.py:167,423`, `cross_ai.py:144`
- "`OPENCODE_EFFORT_EFFECT`" (20-04:246): VERIFIED `cross_ai.py:181`
- "18-VERIFICATION.md items 6, 11, 12 (lines 220-262)" (20-04:327): VERIFIED `.planning/phases/18-cross-ai-skills-apply-pipeline/18-VERIFICATION.md:220,250,256`
- "19-SMOKE.md", "19-05-SUMMARY.md `## Leak check`" (20-04:162): VERIFIED files exist
- "the template appends `--standalone`" (20-04:264): MISSING today (produced by 20-03; listed in the artifacts list, so excluded)
- "`aikit-*` ... `xai-*`" temp dirs (20-04:355-356): MISSING as the runner's prefix: the runner uses `cross-ai-` (`cross-ai.mjs:837`); `xai-st-` is self-test only (`:1506`) — see HIGH 9

20-05
- "`_LABEL_*`, `Runtime`, `RUNTIMES`" (20-05:191): VERIFIED `detection.py:39-128`
- "the Phase 18 scrub comment", "`SCRUB_ENV lacks`", "`not yet live-verified from a codex host`" (20-05:191,246): VERIFIED `detection.py:197-200,55-56`
- "`_LABEL_OPENCODE`" (20-05:208): VERIFIED `:44`
- "`host_signals`", "`scrub_signals`", "`native_selectors`" (20-05:203-229): VERIFIED `Runtime` `:64-74`; codex/opencode `native_selectors == ()` live
- "`_SCRUB_NAMES`, `test_ids_follow_host_precedence_and_known_clis`, `test_scrub_set_keeps_the_same_eleven_names`, `test_precedence_pairs`" (20-05:192): VERIFIED `tests/test_ai_kit_spec_runtimes_table.py:22,70,83,87`
- "`TestDetectCurrentRuntime`, `TestRuntimePrecedenceMatrix`, `TestChildEnv`, `TestDispatchReviewerRealChild`" (20-05:193): VERIFIED `tests/test_ai_kit_spec.py:1148,1248,11279,11322` (10 `CODEX_VERSION` hits)
- "`routing.host_can_select("codex", "gpt-5.6-sol", "codex") is False`" (20-05:230): VERIFIED signature `(runtime, model, host)` `routing.py:44`
- "REQUIREMENTS.md line 17 ... `expected to be dropped by Phase 20 D-05`" (20-05:195,249): VERIFIED
- "20-SPEC.md line 24 (host CLI versions)" (20-05:195): VERIFIED (says 0.153.4 / 1.18.35; live is 0.162.1 / v2.0.31)
- "`installer_argv`", "`_disclosures`", "`_config_dir_note`, `_opencode_root_note`, `_codex_installer_note`" (20-05:259): VERIFIED `followups.py:49,181,223,227,239`
- "`unverified until Phase 20`" (20-05:319): VERIFIED `followups.py:229`, `host.py:23-24`; not in SKILL.md
- "`## Limits (as of 2026-10-15)`", "`local gsd root`" row (20-05:261,320): VERIFIED SKILL.md `:240,247`
- "`TestSkillDocCommands`" (20-05:262): VERIFIED `tests/test_curated_config_apply.py:2321`
- "`_cmd_digest`", "`digest --check`" (20-05:336): VERIFIED `tests/gsd_curated_eval.py:421,4376`
- "`$HOME/.agents/skills/skill-judge/SKILL.md`" (20-05:341): VERIFIED exists (existence only)
- "19-SKILL-JUDGE.md", "19-08-PLAN.md", "18.1-21-PLAN.md", "18.1-VERIFICATION.md" (20-05:194,334-335): VERIFIED files exist
- "pi `openai/gpt-6.1-sol:xhigh` through the runner" (20-05:350): UNCHECKABLE (live model availability; no model call made)

20-06
- "`test`, `validate`, `e2e-test`, `e2e-docker` and its CONTAINER_ENGINE check" (20-06:239): VERIFIED `Makefile:21,64,74,128,133-138`
- "`neither docker nor podman found on PATH`" (20-06:269): VERIFIED `Makefile:135` (prefixed `err: `); podman is on PATH here
- "`=== <module>: ok in <s>s  Ran N tests`, `N/N modules passed`" (20-06:251-252): VERIFIED `tools/run_unittest_parallel.py:207,221`
- "`uv run pre-commit run unittest --all-files --hook-stage pre-push`" (20-06:261): VERIFIED `.pre-commit-config.yaml:57-63` (`stages: [pre-push]`)
- "`--evidence-out`, ... `--home`, `--keep-scratch`" (20-06:146): VERIFIED `--evidence-out`/`--home` `:4414-4415`; `--keep-scratch` is a 20-02 artifact (excluded)
- "19-05-SUMMARY.md `## Leak check`", "19-08-PLAN.md" (20-06:241): VERIFIED files exist

Coverage: no MISSING symbol blocks a plan (the two MISSING rows are HIGH 9 and an
artifact-produced flag). One AMBIGUOUS row is a stale line range. One UNCHECKABLE row needs a
live model.

## Fact-drift pass (advisory)

`drift-guard phase-status --phase 20`: `verdict: uncheckable`, `reason: phase_not_in_roadmap`
(the guard did not parse the ROADMAP `### Phase 20:` heading; STATE.md says "Ready to execute").
Judged by hand:

- SC1 (codex live smoke + live env signal) vs must_haves: covered by 20-04 headless runs and the
  20-06 interactive script. EVAL acceptance stays human_verification per D-01. No drift.
- SC2 ("whether the opencode review lane is usable ... is confirmed and reflected in the
  recommendation logic and SKILL.md"): the policy half is pinned (20-03, 20-05). The mechanics
  trials D-11 retains are optional in 20-06 (HIGH 12). Drift.
- SC3 ("verified live from the codex and opencode hosts"): the plans pin the default branch
  (`native_selectors == ()`, already true in source) with a unit test, and leave the live probe
  optional (20-06 step 8). No plan observes either host live. Advisory drift: either make the
  probe a required interactive item or amend SC3's "verified live" wording.
- Requirements: ROADMAP EVAL-04, EVAL-05 match the plans' `requirements` (20-03 lists only
  EVAL-05, as intended). No drift.
- CONTEXT ↔ plans:
  - D-01 through D-05, D-08, D-09, D-10 and D-12 are each used by a plan. D-08's
    `runtime: <host>` entry already exists (`recommend.py:1042`).
  - D-07 still names `opencode debug agent <name>`. The research found that it does not exist
    in v2.0.31 (`20-RESEARCH.md:97`), and the plans drop the headless loader check. D-07 is not
    amended, which the AGENTS.md amendment rule asks for.
  - D-11's "two trials each" is demoted without an amendment (HIGH 12).
