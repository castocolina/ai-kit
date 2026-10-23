---
phase: 18-cross-ai-skills-apply-pipeline
verified: 2026-10-16T00:00:00Z
status: passed
score: 7/7 must-haves verified
covered_files:
  - .planning/phases/18-cross-ai-skills-apply-pipeline/18-01-PLAN.md
  - .planning/phases/18-cross-ai-skills-apply-pipeline/18-01-SUMMARY.md
  - .planning/phases/18-cross-ai-skills-apply-pipeline/18-02-PLAN.md
  - .planning/phases/18-cross-ai-skills-apply-pipeline/18-02-SUMMARY.md
  - .planning/phases/18-cross-ai-skills-apply-pipeline/18-03-PLAN.md
  - .planning/phases/18-cross-ai-skills-apply-pipeline/18-03-SUMMARY.md
  - .planning/phases/18-cross-ai-skills-apply-pipeline/18-04-PLAN.md
  - .planning/phases/18-cross-ai-skills-apply-pipeline/18-04-SUMMARY.md
  - .planning/phases/18-cross-ai-skills-apply-pipeline/18-05-PLAN.md
  - .planning/phases/18-cross-ai-skills-apply-pipeline/18-05-SUMMARY.md
  - .planning/phases/18-cross-ai-skills-apply-pipeline/18-06-PLAN.md
  - .planning/phases/18-cross-ai-skills-apply-pipeline/18-06-SUMMARY.md
  - .planning/phases/18-cross-ai-skills-apply-pipeline/18-07-PLAN.md
  - .planning/phases/18-cross-ai-skills-apply-pipeline/18-07-SUMMARY.md
  - .planning/phases/18-cross-ai-skills-apply-pipeline/18-08-PLAN.md
  - .planning/phases/18-cross-ai-skills-apply-pipeline/18-08-SUMMARY.md
  - .planning/phases/18-cross-ai-skills-apply-pipeline/18-09-PLAN.md
  - .planning/phases/18-cross-ai-skills-apply-pipeline/18-09-SUMMARY.md
  - .planning/phases/18-cross-ai-skills-apply-pipeline/18-10-PLAN.md
  - .planning/phases/18-cross-ai-skills-apply-pipeline/18-10-SUMMARY.md
  - .planning/phases/18-cross-ai-skills-apply-pipeline/18-11-PLAN.md
  - .planning/phases/18-cross-ai-skills-apply-pipeline/18-11-SUMMARY.md
  - .planning/phases/18-cross-ai-skills-apply-pipeline/18-12-PLAN.md
  - .planning/phases/18-cross-ai-skills-apply-pipeline/18-12-SUMMARY.md
  - .planning/phases/18-cross-ai-skills-apply-pipeline/18-13-PLAN.md
  - .planning/phases/18-cross-ai-skills-apply-pipeline/18-13-SUMMARY.md
  - .planning/phases/18-cross-ai-skills-apply-pipeline/18-14-PLAN.md
  - .planning/phases/18-cross-ai-skills-apply-pipeline/18-14-SUMMARY.md
  - .planning/phases/18-cross-ai-skills-apply-pipeline/18-15-PLAN.md
  - .planning/phases/18-cross-ai-skills-apply-pipeline/18-15-SUMMARY.md
  - .planning/phases/18-cross-ai-skills-apply-pipeline/18-16-PLAN.md
  - .planning/phases/18-cross-ai-skills-apply-pipeline/18-16-SUMMARY.md
  - .planning/phases/18-cross-ai-skills-apply-pipeline/18-17-PLAN.md
  - .planning/phases/18-cross-ai-skills-apply-pipeline/18-17-SUMMARY.md
  - .planning/phases/18-cross-ai-skills-apply-pipeline/18-18-PLAN.md
  - .planning/phases/18-cross-ai-skills-apply-pipeline/18-18-SUMMARY.md
  - .planning/phases/18-cross-ai-skills-apply-pipeline/18-19-PLAN.md
  - .planning/phases/18-cross-ai-skills-apply-pipeline/18-19-SUMMARY.md
  - .planning/phases/18-cross-ai-skills-apply-pipeline/18-20-PLAN.md
  - .planning/phases/18-cross-ai-skills-apply-pipeline/18-20-SUMMARY.md
  - .planning/phases/18-cross-ai-skills-apply-pipeline/18-21-PLAN.md
  - .planning/phases/18-cross-ai-skills-apply-pipeline/18-21-SUMMARY.md
  - .planning/phases/18-cross-ai-skills-apply-pipeline/18-22-PLAN.md
  - .planning/phases/18-cross-ai-skills-apply-pipeline/18-22-SUMMARY.md
  - README.md
  - skills/ai-kit-gsd-curated-config/SKILL.md
  - skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/apply.py
  - skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cli.py
  - skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/config_backup.py
  - skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cross_ai.py
  - skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cross_ai_script.py
  - skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/followups.py
  - skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/inventory.py
  - skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/plan_edit.py
  - skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/plan_io.py
  - skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/recommend.py
  - skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/skill_scan.py
  - skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/skills.py
  - skills/ai-kit-gsd-curated-config/skill_affinity.json
  - skills/ai-kit-spec-review/ai_kit_spec/detection.py
  - skills/ai-kit-spec-review/references/cross-ai.mjs
covered_digest: "v3:sha256:a6531b8c716fc5af5c90e1d3b19efb7fa5ae7357ae72ef95bedf7fd3821a325c"
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: human_needed
  note: "RUN-73 (jev A, TypeSafe 1.0): RUN-10 pattern. 4 real-host items deferred to the live-validation phases; 11 design-acceptance items stay visible as non-blocking owner review (body and final report), not claimed verified."
deferred:
  - truth: "B-CR-01: a real apply on a scratch GSD project rolls back byte-identically when a config-set fails mid-apply"
    addressed_in: "Phase 19"
    evidence: "Phase 19 SC3: live smoke run inventory + recommend + apply (dry-run, then real on a scratch project) completes without corrupting the scratch project's config"
  - truth: "Codex stream-error parse assumption holds against a real codex CLI"
    addressed_in: "Phase 20"
    evidence: "Phase 20 goal: the skill is confirmed working from real codex and opencode host sessions"
  - truth: "CR-03/CR-04 signal handling (run-with-timeout kill, grandchild cleanup) holds on real codex/opencode, cursor and pi CLIs"
    addressed_in: "Phases 20, 21, 22"
    evidence: "Live-validation phases per host: 20 codex/opencode, 21 cursor, 22 pi"
  - truth: "C-W12: a failed (not empty) runner model listing is reported as failed on a real host"
    addressed_in: "Phase 20"
    evidence: "Phase 20 live codex/opencode validation exercises real model listings"
owner_review_nonblocking:
  - "WR-04 / C-W8 trusted-root refuse-not-merge policy"
  - "B-IN-07 JSON-encoding value equality"
  - "C-CR-1 project-skill escape rule"
  - "C-W3 absolute trusted root covering an outside-home skill"
  - "PT-08 plan-set refuses an uncovered outside-home skill"
  - "A-CR-02 exit mapping kept, action=stop on a dirty tree"
  - "WR-06 optional plan key artifacts[0].config.effort"
  - "WR-03 workstream with .. falls back to 300 s"
  - "WR-12 submodule edits"
  - "U-2 npm registry pin (not live-tested; npm banned on this machine)"
  - "U-3 ignored-directory blind spot acceptance"
---

# Phase 18: Cross-AI, Skills & Apply Pipeline Verification Report

**Phase Goal:** A user can adjust the recommended plan, have cross-AI review/execution and per-agent skills wired in, and safely apply the result to a target project's `.planning/config.json`, with the v2 flow living alongside the unchanged v1 CLI.
**Verified:** 2026-10-16 (HEAD 6aef143)
**Status:** passed (re-verified by the orchestrator, RUN-73: real-host items deferred, design acceptances listed as non-blocking owner review)
**Re-verification:** No (initial verification)

## Goal Achievement

### Observable Truths

| # | Truth (ROADMAP SC) | Status | Evidence |
|---|---|---|---|
| 1 | `plan-set`/`plan-unset` adjust the plan, each recorded `source: user` | VERIFIED | `cli.py:702,709` subparsers; `plan_edit.py:132,157,374,578` set `source="user"` on every edit path (plain keys, script pseudo-keys, unset); `tests.test_curated_config_plan_edit` OK (`test_plan_set_rewrites_with_source_user`) |
| 2 | Cross-AI review keys (lane != host, reviewer vendor != planner, best review score, models/effort per lane, GSD lane registry) and execution keys (`node .planning/scripts/cross-ai.mjs`, per-project script, pi > cursor > opencode, unattended flags, bare profile, timeout >= 1800, supervision contract, D-39 defaults, `--cross-ai` + `manager.flags.execute`) | VERIFIED | `cross_ai.py`: `CROSS_AI_COMMAND`, `DEFAULT_PREFER=("pi","cursor","opencode")` (no grok), `MIN_TIMEOUT_S=1800`, `EXEC_DEFAULT_HOSTS=("claude","codex")`, `eligible_lanes` reads `gsd_core.review_lanes` and skips the host slug, `_vendor_keep` excludes planner vendor; `recommend.py:822-909` emits `workflow.plan_review_convergence`, `review.default_reviewers`, `workflow.cross_ai_execution/command/timeout`, `manager.flags.execute` and the `--cross-ai` note; runner `cross-ai.mjs:118-135` status table with exits 0/1/2/69/75/124/127 (+128+n signal), one `AIKIT-XAI` line, `--no-skills --no-extensions` bare profile, inner deadline below outer (`:410-417`); renderer `cross_ai_script.py` sha256 header + `.new` diversion; `tests.test_curated_config_cross_ai`, `tests.test_curated_config_script` OK; runner self-test subset (dirty-quota, okwarn, submodule-edit, ignored-dir-write) `Self-test ok` |
| 3 | Skill inventory (host dirs, project `skills/`, Claude plugins); `skill_affinity.json` gated by TDD/frontend/db, capped per rigor, bare names in plan, reference form on write; missing skills silently omitted; unknown skills get proposals; escaping symlinks get a `trusted_global_roots` proposal | VERIFIED | `skill_scan.py` root kinds global/plugin/project, `plugin_skills` reads `installed_plugins.json` + layered `enabledPlugins`; `skill_affinity.json` families with `when` gates; `presets.SKILL_CAPS={mvp:2,standard:3,rigorous:5}`; plan holds bare names (`recommend._agent_skill_entries`), `apply.py:100` converts via `skills.reference_for` (`skills/<n>`, `global:<n>`, `global:<plugin>:<n>`); `skills.proposals` (cap 10), `skills.trusted_roots`; `tests.test_curated_config_skills` OK (`test_missing_skill_never_named`, `test_trusted_root_entry_on_escaping_global`, `test_proposal_shows_runnable_json_list`) |
| 4 | `apply --dry-run` validates keys and prints a diff without writing; real `apply` backs up to `config.json.bak-<ts>`, writes only through `config-new-project`/`config-set`, restores and names the failing key, keeps 3 backups; follow-ups (pinned local installer, `effort sync --apply`) only after one grouped approval; `/gsd-map-codebase` only recommended | VERIFIED | `apply.py:242-256` probes every write key through the host gsd-core and refuses rejected ones; `_apply_config_writes` (`config_set_strict` only) sets `failed_key` + `config-set <key> failed:` and calls `_rollback`; `_execute_apply` wraps pre-commit in try/rollback (B-CR-01); `config_backup.py` `BACKUP_PREFIX="config.json.bak-"`, `KEEP=3`; `followups.py` `installer_argv` = `npx -y --registry ... @opengsd/gsd-core@<v> --<host> --local`, `effort_sync_argv(... --apply)`, nothing runs without `--approve` (+ fingerprint), `map_codebase` is a text recommendation; `tests.test_curated_config_apply`, `tests.test_curated_config_followups` OK; real-gsd-tools e2e green in the provided `make test` gate |
| 5 | v1 CLI and modules unchanged next to v2; `make test`/`make validate` green; README row updated; SKILL.md labels cursor and pi not live-validated | VERIFIED | v1 subparsers still present (`cli.py:719-790`: ensure-project, apply-profile, apply-critical-agents, apply-execution, apply-review, ...); no curated-config module deleted by phase 18 (the only deletion in range, `gsd_write.py`, is commit a741ee8 from Phase 16.1); `tests.test_ai_kit_gsd_curated_config` (v1) 90 tests OK; `README.md:45` row updated; `SKILL.md:216` "cursor / pi hosts: not live-validated"; gate evidence on HEAD 6aef143: `make test` rc=0 (37/37 unit, 4/4 integration, 7/7 e2e, 1/1 arch), `make validate` rc=0, `make e2e-docker` rc=0 |
| 6 | Ponytail first-class in `skill_affinity.json` (core -> planner/executor/code-fixer; review/audit -> code-reviewer + auditors; debt -> verifier), within cap; non-Claude visibility checked and recorded; stale CONTEXT note corrected | VERIFIED | `skill_affinity.json` families `ponytail-core`, `ponytail-reviewers` (gsd-code-reviewer, security/nyquist/eval/ui auditors), `ponytail-verifier` (gsd-verifier); `skill_scan.ponytail_visibility` recorded live in inventory (`inventory.py:391,420`) and validated in `plan_io.py:163`; 18-CONTEXT D-35 (amended) and the 2026-10-13 superseded note at line 453 |
| 7 | `jev-fast-decision` recommended for `gsd-advisor-researcher`/`gsd-assumptions-analyzer` only when a System One backend is detected | VERIFIED | `skill_affinity.json` family `system-one` with `when: system_one_backend`; `skills.skill_facts` gates on `system_one_backend.detected`; `skill_scan.system_one_backend` = `JEV_API_URL` TCP reachability or `JEV_API_KEY` presence (D-36: no default URL probed, so a local Laya counts only via `JEV_API_URL`); tests `test_jev_once_with_backend`, `test_jev_without_backend_not_wired` (non-vacuous per C-W13) OK |

**Score:** 7/7 truths verified (0 present, behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
|---|---|---|---|
| `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/plan_edit.py` | plan-set/plan-unset | VERIFIED | 598 lines, wired from `cli._run_plan_edit` |
| `.../cross_ai.py`, `.../recommend.py` | lane + execution target selection, plan entries | VERIFIED | wired into recommend; goldens pass |
| `skills/ai-kit-spec-review/references/cross-ai.mjs` | runner template + hermetic self-test | VERIFIED | 2525 lines; rendered by `cross_ai_script.render` |
| `.../cross_ai_script.py` | sha256-stamped render, `.new` protection | VERIFIED | used by `apply._apply_script_step` |
| `.../skill_scan.py`, `.../skills.py`, `skill_affinity.json` | inventory + affinity resolution | VERIFIED | used by inventory and recommend |
| `.../apply.py`, `.../config_backup.py` | dry-run, backup/restore, marker, gsd-tools writes | VERIFIED | wired from `cli.py` `apply` |
| `.../followups.py` | grouped-approval follow-ups | VERIFIED | wired from `cli.py` `followups` |
| `skills/ai-kit-spec-review/ai_kit_spec/detection.py` | pi RPC `get_available_models` (SPEC-05) | VERIFIED | `PI_RPC_REQUEST`, fixture `pi_rpc_get_available_models.json`, `pi` in `KNOWN_CLIS` |
| `skills/ai-kit-gsd-curated-config/SKILL.md`, `README.md` | v2 flow docs | VERIFIED | skill-judge: Claude R2 107/120 (baseline 100), pi gpt-6.1-sol 104/120 (85), pi glm-5.3 115/120 (104) |

### Key Link Verification

| From | To | Via | Status |
|---|---|---|---|
| recommend plan `agent_skills.<agent>` (bare names) | `.planning/config.json` | `apply.py:100` `skills.reference_for` -> `config_set_strict` | WIRED |
| plan script artifact | `.planning/scripts/cross-ai.mjs` | `cross_ai_script.plan_script/write_script` in `apply._apply_script_step` | WIRED |
| `workflow.cross_ai_command` | runner | constant `node .planning/scripts/cross-ai.mjs` (`COMMAND_KEYS` guard in plan-set) | WIRED |
| apply failure | backup restore | `_apply_config_writes` / `_execute_apply` except -> `_rollback` | WIRED |
| followups | installer / effort sync | `run_followups --approve` with fingerprint check | WIRED |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|---|---|---|---|
| plan-edit, cross-AI, skills, apply, followups, script, golden modules | `python3 -m unittest tests.<module>` (7 modules, sequential) | all OK | PASS |
| v1 CLI unchanged | `python3 -m unittest tests.test_ai_kit_gsd_curated_config` | Ran 90, OK | PASS |
| Runner supervision cases | `AIKIT_XAI_SELFTEST_CASES=dirty-quota,okwarn,submodule-edit,ignored-dir-write node .../cross-ai.mjs --self-test` | `Self-test ok` | PASS |
| Full suite / validate / docker e2e | not re-run (provided gate evidence on HEAD 6aef143) | rc=0 each | PASS (provided) |

### Probe Execution

No `scripts/*/tests/probe-*.sh` declared by phase 18 plans. SKIPPED.

### Requirements Coverage

| Requirement | Status | Evidence |
|---|---|---|
| XAI-01 | SATISFIED | Truth 2 (review lanes) |
| XAI-02 | SATISFIED | Truth 2 (execution runner, supervision contract) |
| SKL-01 | SATISFIED | Truth 3 (three inventory roots) |
| SKL-02 | SATISFIED | Truth 3 (affinity, gates, caps, reference forms) |
| SKL-03 | SATISFIED | Truth 3 (silent omission, proposals, trusted roots) |
| SKL-04 | SATISFIED | Truth 7 |
| APP-01 | SATISFIED | Truth 1 |
| APP-02 | SATISFIED | Truth 4 (dry-run) |
| APP-03 | SATISFIED | Truth 4 (backup, gsd-tools writes, reconcile, marker, inventory digest) |
| APP-04 | SATISFIED | Truth 4 (follow-ups) |
| EVAL-06 | SATISFIED | Truth 5 |
| SPEC-05 | SATISFIED | `detection.py` pi RPC enumeration + fixture |

All 12 IDs mapped to Phase 18 in REQUIREMENTS.md appear in plan frontmatter; no orphans. APP-05 is mapped to Phase 19.

### Anti-Patterns Found

No unreferenced `TBD`/`FIXME`/`XXX` markers in phase-modified source (only test data strings such as `grep -r FIXME .`). Known, documented shortcuts (codex event shape, unread active-workstream pointer, plugin.json custom skill paths) are tracked as `shortcut:` comments and routed to human verification below.

Open, documented, non-blocking review items: A-IN-12 (tree snapshot rehash cost, unmeasured; skipped to avoid false `tree=clean`).

### Deferred Items and Owner Review (non-blocking)

Items 1, 11, 12 and 6 (C-W12) need real hosts and are deferred: 1 to Phase 19, 11 and 6 to Phase 20, 12 to Phases 20-22 (frontmatter `deferred`). The other 11 are owner design acceptances. They are listed in the final report and are not claimed verified. The details below are unchanged from the first pass.

### 1. B-CR-01 rollback on a real project

**Test:** On a scratch copy of a real GSD project, force a failure inside the pre-commit window of a real `apply` (e.g. make one `config-set` fail, or interrupt `config-new-project` on a fresh project).
**Expected:** Exit 1 with a JSON report naming the failing key; `.planning/config.json` byte-identical to `config.json.bak-<ts>` (or absent on a fresh project); no apply marker, no created `.planning/`, no leftover `cross-ai.mjs.new` created by this apply.
**Why human:** Unit/e2e tests inject the failures with fakes (18-REVIEW-FIX-B B-CR-01, flagged 'requires human verification'); real gsd-tools timing and filesystem behavior on a live project is not exercised.

### 2. WR-04 / C-W8 trusted-root policy

**Test:** Read `plan_io.home_relative_root`, `plan_edit._check_trusted_roots` and the merged-candidate text in `skills.merged_trusted_roots_why`; then on a project with an existing `agent_skills_security.trusted_global_roots`, run `plan-set` with a list that omits a configured root, with and without `--force`.
**Expected:** Without `--force`: exit 2 and a printed, shell-quoted merged command. With `--force`: the root is dropped, a warning is printed and the entry is marked `forced`; `validate_plan` rejects an un-forced dropping list. `~/..`, `~/`, `~//x` are always refused. The refuse-not-merge design is acceptable as a security control.
**Why human:** Design decision on a security control (refuse rather than silently merge) flagged 'requires human verification' in 18-REVIEW-FIX-B and -C; tests prove behavior, not that the policy is the right one.

### 3. B-IN-07 JSON-encoding value equality

**Test:** Review `plan_io.same_value` and its two callers (diff rule, plan-set keep decision).
**Expected:** `0` vs `false`, `1` vs `true`, and `1` vs `1.0` are treated as different values (a write happens), while semantically identical JSON is a no-op.
**Why human:** Logic change flagged 'requires human verification' in 18-REVIEW-FIX-B (IN-07); key-order or float-format edge cases are a judgment call.

### 4. C-CR-1 project-skill escape rule

**Test:** Create a project whose `skills/` is a symlink pointing outside the project, plus `skills/foo -> <project>/vendor/foo`, and run inventory + recommend on a real host.
**Expected:** The outside-pointing skills are not wired (a note explains why); `skills/foo` is wired as `skills/foo`; the rule matches gsd-core's own realpath-inside-project check on the installed version.
**Why human:** Mirrors gsd-core's private rule; parity with the live gsd-core version is not machine-checked (flagged in 18-REVIEW-FIX-C).

### 5. C-W3 absolute trusted root covering an outside-home skill

**Test:** Configure an absolute `trusted_global_roots` entry covering a global skill whose realpath is outside $HOME and run recommend/apply.
**Expected:** The skill is wired (the outside-home refusal consults `covered()` first); recommend still never proposes an absolute root; gsd-core loads the skill at runtime.
**Why human:** Whether real gsd-core honors the absolute root is runtime behavior of an external tool (flagged in 18-REVIEW-FIX-C).

### 6. C-W12 failed vs empty model listings

**Test:** On a machine where one installed runner's model listing fails (or returns nothing), run inventory + recommend.
**Expected:** Inventory records `runtime_enumeration.<runtime>` = `failed`/`empty`; the target's why reads `no <runtime> models enumerated (listing failed|empty)`, never a price-ceiling reason.
**Why human:** Real CLI listing failures cannot be produced deterministically without the live CLIs (flagged in 18-REVIEW-FIX-C).

### 7. PT-08 plan-set refuses an uncovered outside-home skill

**Test:** Install a global skill whose realpath is outside $HOME with no trusted root covering it, then `plan-set agent_skills.<agent> '["<that skill>"]'`.
**Expected:** plan-set refuses (exit 2) via `skills.unwired_reason()`, consistent with recommend never wiring it and gsd-core skipping it.
**Why human:** Admission now depends on the same predicate recommend uses; parity with gsd-core's skip behavior is flagged 'requires human verification' in 18-REVIEW-FIX-C.

### 8. A-CR-02 exit mapping kept, action=stop on a dirty tree

**Test:** Read the `finish()` override in `cross-ai.mjs` and confirm the contract with GSD's consumer: a quota/billing failure on a dirty or unknown tree prints `status=quota exit=75 action=stop`.
**Expected:** Exit code keeps naming the status class (75), `action=stop` is the instruction; GSD's execute-phase cross-AI consumer honors `action` and does not retry-later on exit 75 alone. An unreadable tree after a failure ends `status=unverified` exit 1 stop.
**Why human:** The status/exit table is a cross-tool contract (D-30); whether the GSD consumer keys on `action` rather than exit code is external behavior (flagged in 18-REVIEW-FIX-A).

### 9. WR-06 optional plan key artifacts[0].config.effort

**Test:** Run recommend on a host with pi or codex installed and a catalog model with reasoning modes; inspect the plan and the rendered `.planning/scripts/cross-ai.mjs`; then run the runner with `--print-argv`.
**Expected:** `artifacts[0].config.effort` appears only for catalog picks on pi/codex with reasoning modes (absent for routers, no-mode models, ids that already name an effort); `CONFIG.effort` is baked in; pi gets `--thinking <level>` (not when the id has a `:level` suffix), codex gets `model_reasoning_effort`; `--codex-effort` still wins.
**Why human:** New optional plan-schema key and design choice flagged 'requires human verification' in 18-REVIEW-FIX-A; real CLI acceptance of the effort flags is not live-tested.

### 10. WR-03 workstream with `..` falls back to 300 s

**Test:** Run the runner with `GSD_WORKSTREAM=../x` (and a normal workstream) against a project with `workflow.cross_ai_timeout` set; compare with `gsd-tools config-get workflow.cross_ai_timeout` under the same env.
**Expected:** A bad segment reads as absent and the live outer timeout falls back to 300 s, matching GSD's own fallback; a normal workstream reads the scoped key first, then the root key. The runner uses the smaller of live and baked timeouts.
**Why human:** Behavior change mirroring gsd-core's private `readScopedConfigValue` (flagged in 18-REVIEW-FIX-A); the stored active-workstream pointer is not read (shortcut).

### 11. Codex stream-error parse assumption

**Test:** Run `cross-ai.mjs` against a real codex CLI in a scratch repo, provoking a transient stream `error` that recovers, and separately a `turn.failed`.
**Expected:** A stream `error` event followed by `turn.completed` is classified `ok`; `turn.failed` always fails.
**Why human:** The codex JSON event shape is assumed, not live-verified (shortcut comment, 18-REVIEW-FIX-A A-CR-01).

### 12. CR-03 / CR-04 signal rework on real CLIs

**Test:** Run `gsd-tools run-with-timeout` around the runner with each real CLI (pi, cursor-agent, opencode, codex) in a scratch repo and send SIGTERM mid-run, then a second signal.
**Expected:** Exactly one `AIKIT-XAI status=signal ... tree=<real state>` line within ~2.9 s; the CLI process group is dead; no temp dirs left; a second signal SIGKILLs the group at once.
**Why human:** Self-test uses fake CLIs (`sigterm-stubborn`, `sigterm-twice`, `sigterm-backoff`); real CLI child-process trees and signal handling differ (flagged in 18-REVIEW-FIX-A).

### 13. WR-12 submodule edits

**Test:** In a scratch repo with a checked-out submodule, run the runner with a CLI that edits only a file inside the submodule.
**Expected:** The tree id changes (`tree=dirty`, counted as success for exec); an unreadable nested repo makes the state `unknown`.
**Why human:** Real submodule layouts (nested, uninitialized, worktree-based) vary; tests cover one synthetic layout (flagged in 18-REVIEW-FIX-A).

### 14. U-2 npm registry pin

**Test:** On a machine where npm is allowed, run the approved installer follow-up (`npx -y --registry=https://registry.npmjs.org/ --@opengsd:registry=https://registry.npmjs.org/ @opengsd/gsd-core@<v> --<host> --local`) with a project `.npmrc` that sets a different `@opengsd:registry`.
**Expected:** The package is fetched from registry.npmjs.org (the scoped flag outranks the `.npmrc` scope).
**Why human:** Not live-tested: npm is banned on the dev machine; precedence is taken from npm docs (18-SECURITY T-18-75).

### 15. U-3 ignored-directory blind spot acceptance

**Test:** Confirm the accepted risk: edits inside a fully gitignored directory are not part of the runner's tree id.
**Expected:** A CLI that writes only inside a fully ignored directory reads as `tree=clean` (no change, may fall back); ignored files outside fully ignored dirs are still stat-tracked. The user accepts this blind spot.
**Why human:** Deliberate narrowing per jev in 59d8a4e (18-SECURITY T-18-76); a risk-acceptance decision, not a test outcome.

### Gaps Summary

No gaps. Every roadmap success criterion and all 12 requirement IDs are backed by code that exists, is wired, and is exercised by passing tests. The first pass was `human_needed` on 15 items. RUN-73 deferred the 4 real-host ones to Phases 19-22 and kept the 11 design acceptances as non-blocking owner review.

---

_Verified: 2026-10-16_
_Verifier: Claude (gsd-verifier)_
