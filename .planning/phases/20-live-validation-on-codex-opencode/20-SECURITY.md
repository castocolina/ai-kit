---
phase: "20"
slug: "live-validation-on-codex-opencode"
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
block_on: high
created: "2026-10-18"
---

# Phase 20 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| smoke harness -> gsd-core installer | The cached 1.17.0 installer runs `--<host> --local --no-legacy-cleanup` under a throwaway HOME and XDG dirs, with an allowlisted env (`INSTALL_ENV_KEEP`); never npx | config files (high) |
| smoke harness -> scratch projects | Real applies only in `mkdtemp` work dirs, refused inside the repo (`_smoke_work_dir`) and behind `refuse_repo_apply` | config (high) |
| cross-AI runner -> codex / opencode | Headless dispatch with `--codex-sandbox workspace-write` or opencode `--standalone`; host-signal env scrubbed; process groups killed | prompts, scratch files (high) |
| harness -> real home | Read-only protected-set snapshot (hashes and labels only; credential files excluded) diffed around each run | config hashes (high) |
| evidence -> repo | Placeholders applied, names-only env lists, `secret-scan` and `$HOME` greps gate every evidence commit | tool output (medium) |

---

## Threat Register

Evidence column from the gsd-security-auditor run (line numbers as of that audit; `tests/gsd_curated_eval.py` lines shifted after 89144b2).

| Threat | Cat | Sev | Disp | Evidence |
|---|---|---|---|---|
| T-20-01 | T | high | mitigate | `refuse_repo_apply` at `tests/gsd_curated_eval.py:616-623`. It runs first on all three real apply paths: `:637`, `:4212`, `:4500`. Pinned by `test_repo_config_untouched` and `test_snapshot_strict_set_unchanged_across_the_run` (`tests/test_ai_kit_gsd_curated_config_matrix.py:94-99`), which all three host classes inherit (`:102-107`). Further tests: `test_refuses_repo_root` and `test_refuses_symlink_to_repo_root` |
| T-20-02 | I | med | mitigate | Matrix output uses labels only (`gsd_curated_eval.py:91-169`). `test_output_carries_no_absolute_path` (`matrix.py:82-92`) runs for each host |
| T-20-03 | T | high | mitigate | `_install_local` (`:4052-4110`): env built from the `INSTALL_ENV_KEEP` allowlist (`:4049`, `:4083-4090`), throwaway HOME and four XDG dirs, `--no-legacy-cleanup` (`:4097`). Strict `<home>/.gsd` entries at `:203` and `:221` |
| T-20-04 | I | high | mitigate | The snapshot (`:292-321`) never lists `service.json`, `auth.json`, `credentials.json`, `package.json` or `bun.lock` (credentials excluded at `:100` and `:234`). Tests at `tests/test_gsd_curated_eval.py:538-549` and `:580-584` |
| T-20-06 | T | low | mitigate | `_toml_semantic_sha` (`:262-282`) exempts only trust rows under the scratch dir, compared after realpath (`:271`). Tests: `test_codex_trust_row_under_resolved_root_is_exempt` and `test_codex_toml_non_scratch_change_is_strict` |
| T-20-07 | E | med | mitigate | `--standalone` on exec and review (`skills/ai-kit-spec-review/references/cross-ai.mjs:280-281`). Resume reuses them (`:282`). Pinned by the self-test (`:1578`, `:1598`), which passed. `TEMPLATE_VERSION = 4` (`cross_ai.py:46`). The repo's own runner was re-rendered with template 4 (`.planning/scripts/cross-ai.mjs:2`, `:288-289`). The read-only shared-service preflight is recorded at `20-SMOKE-OPENCODE.md:337` |
| T-20-08 | S | med | mitigate | `eligible_lanes` skips the host slug (`cross_ai.py:219`). `_host_reviewer_problem` (`plan_io.py:542-550`). `TestPlanSetRefusals.test_host_slug_never_a_review_lane` covers each host, with and without `--force` (passed) |
| T-20-09 | E | high | mitigate | `--codex-sandbox workspace-write` in the argv (`20-SMOKE-CODEX.md:9`, `:11`, `:18`). Every `AIKIT-XAI` line shows `tree=clean`. `refuse_repo_apply` as in T-20-01 |
| T-20-10 | I | high | mitigate | Env lists are names only (`20-SMOKE-CODEX.md:32`). Placeholders applied. `secret-scan` and `$HOME` scans clean (re-run by me) |
| T-20-11 | D | med | mitigate | `killGroup` (`cross-ai.mjs:511-513`) and `--child-pgid-file` (`:936`). Process proof at `20-04-SUMMARY.md:120-125` and `20-SMOKE-CODEX.md:306-316` |
| T-20-12 | T | high | mitigate | `<home>/.cursor/cli-config.json` is strict (`:210`). `snapshot ok` at `20-04-SUMMARY.md:138` and `20-SMOKE-CODEX.md:332` |
| T-20-13 | R | med | mitigate | `test_codex_labels_are_live_verified` (`tests/test_ai_kit_spec_runtimes_table.py:87`) and `test_phase_20_evidence_notes_claim_only_what_the_smoke_ran` (`tests/test_curated_config_followups.py:527`). Both passed |
| T-20-14 | I | med | mitigate | Redaction recorded (`20-06-SUMMARY.md:122`). `skill-judge/` scans clean (re-run) |
| T-20-15 | I | high | mitigate | One `env \|` per script, and it pipes into `cut -d= -f1` (`20-INTERACTIVE-CODEX.md:26`, `20-INTERACTIVE-OPENCODE.md:26`) |
| T-20-16 | T | high | mitigate | Steps use `--standalone` (`20-INTERACTIVE-OPENCODE.md:73`, `:100`). The listing is read-only (`:106-109`). The shadow-file step is the user's own opt-in edit (`:122`). The global path is explained, never given as a command (`:138`) |
| T-20-17 | E | med | accept | Acceptance recorded at `20-01-PLAN.md:348`. Bootstrap host `pi` recorded at `20-01-SUMMARY.md:87`. Goes into the accepted-risks log |
| T-20-18 | I | med | mitigate | The installer env sets XDG_DATA/CACHE/STATE under the throwaway home (`:4086-4089`). The test pins HOME and the four XDG values (`test_gsd_curated_eval.py:2905-2914`). Residual risk: the real `opencode` binary still runs the probe (already in the plan) |
| T-20-19 | I | med | mitigate | `_write_artifacts` sends everything through `_smoke_placeholders` (`:4341-4368`, `:4629-4647`). Kept artifacts: secret-scan and three path greps all clean (re-run) |
| T-20-20 | T | high | mitigate | `installed_runtimes == ['codex']` under the controlled PATH (`20-SMOKE-CODEX.md:304`). Strict cursor entry at `:210` |
| T-20-21 | T | med | mitigate | The `HOST_SIGNAL_ENV_VARS` list (`detection.py:197`) matches the template's `scrubEnv` (`cross-ai.mjs:77-89`) and the rendered runner. Equality pinned in `tests/test_ai_kit_spec.py:11571` and `tests/test_curated_config_script.py:73` |
| T-20-22 | E | high | mitigate | `--standalone` and `tree=clean` (`20-SMOKE-OPENCODE.md:8`, `:17`). `refuse_repo_apply` |
| T-20-23 | I | high | mitigate | Names only (`20-SMOKE-OPENCODE.md:31-52`, re-captured inside opencode). Scans clean |
| T-20-24 | D | med | mitigate | Process groups checked dead, including those of the run-1 dispatch that never printed a final status line (`20-SMOKE-OPENCODE.md:24`, `20-05-SUMMARY.md:129-135`). The shared opencode service was left untouched (`:337`) |
| T-20-25 | T | high | mitigate | `snapshot ok` (`20-05-SUMMARY.md:148`, `20-SMOKE-OPENCODE.md:372`) |
| T-20-26 | T | high | mitigate | `installed_runtimes == ['opencode']` (`20-SMOKE-OPENCODE.md:350`) |
| T-20-SC | T | high | mitigate | No dependency file changed across the 57 Phase 20 commits. `_install_local` refuses to run without a cached installer ("never npx", `:4055-4058`) and requires the version to match the pin (`:4063-4066`) |
| T-20-05 | T | med | mitigate | `_smoke_work_dir()` in `tests/gsd_curated_eval.py` refuses a work dir whose realpath is inside `REPO_ROOT` (`SMOKE_WORK_IN_REPO`); tests `test_smoke_work_dir_refused_inside_the_repo` and `test_smoke_work_dir_outside_the_repo_is_kept` (89144b2). The codex evidence was re-run with `TMPDIR` outside the repo (dca8e96). Also `refuse_repo_apply` and the dropped `RUNTIME_DIR` |

All 27 threats (T-20-01..T-20-26 plus T-20-SC) are closed.

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-20-01 | T-20-17 | The 20-01 bootstrap ran in a full-permission cross-AI executor (pi), the standing v1.3 cross-AI setup | 20-01 plan (plan review) | 2026-10-18 |

*Accepted risks do not resurface in future audit runs.*

---

### Unregistered flags
None of the seven SUMMARYs has a `## Threat Flags` section. These come from reading the SUMMARYs, the reviews and the code. None blocks shipping.
1. **v1 can pick the host CLI as its own reviewer.** `detect-review-candidate` in the v1 path has no host exclusion. Commit `c7089ff` only documents this (`SKILL.md`, `references/v1-path.md`). T-20-08 covers the v2 path only. Spoofing, low.
2. **Nested full-permission dispatch.** Plans 20-02 to 20-07 ran in a cross-AI pi executor, which then dispatched codex and opencode with full permissions. T-20-17 accepts only the 20-01 bootstrap dispatch. Elevation of privilege, low; it is the standing v1.3 cross-AI setup.
3. **Unguarded delete in the interactive script.** `rm -rf "$DIR"` (`20-INTERACTIVE-OPENCODE.md:127`) deletes whatever path the user typed into `DIR`, with no `${DIR:?}` guard. Related to T-20-16. Tampering, low.
4. **Matrix tests read more real host config.** The matrix e2e tier now hashes more of the real `~/.codex` and `~/.config/opencode` (review IN-07, skipped and recorded in `20-REVIEW-FIX.md`). Read-only, but it conflicts with the AGENTS.md rule against using real config in tests. Low.
5. **Opencode run 1 never printed a final status line.** Its process groups were confirmed dead. This maps to T-20-24 and is informational only.

Flag 3 is fixed: the script now uses `rm -rf "${DIR:?set DIR to the kept smoke work directory first}"` (89144b2). Flags 1 and 4 are owner-review items.

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-10-18 | 27 | 26 | 1 (T-20-05, medium, below threshold) | gsd-security-auditor (ASVS 1, block_on high) |
| 2026-10-18 | 27 | 27 | 0 | orchestrator: T-20-05 guard and tests (89144b2), codex evidence re-run outside the repo (dca8e96) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-10-18
