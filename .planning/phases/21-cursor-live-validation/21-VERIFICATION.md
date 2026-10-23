---
phase: 21-cursor-live-validation
verified: 2026-10-19T12:00:00Z
status: human_needed
score: 5/5 must-haves verified
covered_files:
  - ".planning/phases/21-cursor-live-validation/21-01-PLAN.md"
  - ".planning/phases/21-cursor-live-validation/21-01-SUMMARY.md"
  - ".planning/phases/21-cursor-live-validation/21-02-PLAN.md"
  - ".planning/phases/21-cursor-live-validation/21-02-SUMMARY.md"
  - ".planning/phases/21-cursor-live-validation/21-03-PLAN.md"
  - ".planning/phases/21-cursor-live-validation/21-03-SUMMARY.md"
  - ".planning/phases/21-cursor-live-validation/21-04-PLAN.md"
  - ".planning/phases/21-cursor-live-validation/21-04-SUMMARY.md"
  - ".planning/phases/21-cursor-live-validation/21-05-PLAN.md"
  - ".planning/phases/21-cursor-live-validation/21-05-SUMMARY.md"
  - ".planning/phases/21-cursor-live-validation/21-06-PLAN.md"
  - ".planning/phases/21-cursor-live-validation/21-06-SUMMARY.md"
  - ".planning/phases/21-cursor-live-validation/21-07-PLAN.md"
  - ".planning/phases/21-cursor-live-validation/21-07-SUMMARY.md"
  - ".planning/scripts/cross-ai.mjs"
  - "README.md"
  - "cursor-agents/composer-worker.md"
  - "cursor-agents/grok-worker.md"
  - "skills/ai-kit-gsd-curated-config/SKILL.md"
  - "skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cross_ai.py"
  - "skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/host.py"
  - "skills/ai-kit-gsd-curated-config/references/runner.md"
  - "skills/ai-kit-spec-review/ai_kit_spec/detection.py"
  - "skills/ai-kit-spec-review/ai_kit_spec/routing.py"
  - "skills/ai-kit-spec-review/references/cross-ai.mjs"
  - "tests/gsd_curated_eval.py"
  - "tests/test_ai_kit_spec_runtimes_table.py"
  - "tests/test_curated_config_apply.py"
  - "tests/test_cursor_agents.py"
  - "tests/test_gsd_curated_eval.py"
covered_digest: "v3:sha256:dcf785282aaba24685cb63a23fbc04ed88692c9d7d4dab7f4cffefdaf4169d61"
behavior_unverified: 0
overrides_applied: 0
human_verification:
  - test: "Run 21-INTERACTIVE-CURSOR.md steps 1-4 from your own interactive cursor-agent TUI session at the checkout root (SPEC R1 acceptance)"
    expected: "Smoke ends with all steps passing on both scratch projects, ai-kit byte-identical, snapshot --check with --host-rewrite on cli-config.json passes; then the `pending` note in SKILL.md's `cursor host` row and the README skill row is removed in the commit that records the run"
    why_human: "SPEC R1 (amended) makes the user's interactive session the acceptance; the headless run only lifts the label to `validated headless ... pending`"
  - test: "Optional: 21-INTERACTIVE-CURSOR.md step 5, the ROADMAP SC5 per-call model probe"
    expected: "Task call's `model` field read from stream-json; only if it proves native per-call selection would host_can_select change for cursor"
    why_human: "Live AI-CLI run; SC5 is already satisfied by its OR branch (cursor stays session-default-only), so this is informational"
  - test: "Cursor usage-dashboard non-fast confirmation"
    expected: "Not part of Phase 21: moved with AGT-02 to backlog 999.7 (ROADMAP 999.7 criterion 2; REQUIREMENTS AGT-02 row `999.7 (backlog) | Deferred`)"
    why_human: "Dashboard is an external UI; recorded here only so the deferral is visible"
  - test: "Skill-judge gate for skills/ai-kit-gsd-curated-config/SKILL.md (pending orchestrator step)"
    expected: "Both judges re-run on the current digest f0c43a5da52a587d (python3 tests/gsd_curated_eval.py digest); 21-SKILL-JUDGE.md updated; owner decides whether pi 114/120 (0 Critical / 0 Important) vs the 116 baseline is variance or regression"
    why_human: "Recorded verdict is UNRESOLVED on digest 85da5a6682d937c5, which is stale after the 21-REVIEW-FIX template-6 edits to SKILL.md and references/runner.md; re-judging is in flight (pi waiting on its subscription limit), not a gap"
owner_review_nonblocking:
  - item: "21-REVIEW-FIX logic changes flagged `fixed: requires human verification`: CR-01 (runner parseCursorListingIds ported to parse_cursor_models rules, template 6), WR-01 (resolve_runtime_binary returns os.path.abspath), WR-02 (cached_binary_usable re-checks the agent guard), WR-06 (bare/flagged token counts only after the `Available models` header)"
    note: "Regression tests exist and pass (67 tests in tests.test_cursor_agents + tests.test_ai_kit_spec_runtimes_table ran OK here); intent of the header rule and absolute-path cache semantics is the owner's call"
  - item: "Headless smoke evidence predates the review fixes"
    note: "21-SMOKE-CURSOR.md ran at product_commit 9129390 through the template-5 runner; the tracked runner is now template 6 and detection.py changed (WR-01/02/05/06). HEAD gates (make test, make validate, make e2e-docker with its 420-check matrix) are green, but no cursor-hosted run exercised the post-fix tree; the interactive run will"
  - item: "Predecessor/cursor scope notes"
    note: "SPEC R6/R7 (setup category, wizard row, headless flag, live delegation proof) moved to backlog 999.7 by the D-01 spike; the cursor installer bakes no model line, so the verified chain is plan -> resolve-model only and whether cursor workflows pass that into a Task call is unverified (21-SMOKE-CURSOR.md Chain note)"
  - item: "IN-05 empty-PATH limit"
    note: "An empty PATH entry resolves as the cwd in both resolvers, so an untrusted checkout can supply its own `agent`; documented in references/runner.md only, not guarded"
  - item: "Stale docstring"
    note: "skills/ai-kit-spec-review/ai_kit_spec/routing.py:49 says other hosts are session-default-only `until Phases 20-22`; Phase 21 kept cursor session-default-only, so the wording is outdated (info)"
---

# Phase 21: Cursor Live Validation Verification Report

**Phase Goal:** The skill is confirmed working from a real cursor host session; cursor's "not live-validated" label is lifted.
**Verified:** 2026-10-19
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | SC1: live cursor-host smoke (inventory + recommend + apply, dry-run then real) completes on a scratch project | VERIFIED (headless) | `21-SMOKE-CURSOR.md`: one dispatch through the runner, `--print-argv` shows `cursor-agent ... --model composer-2.5`; steps 1-10 pass (ai-kit dry run wrote nothing, local install 1.17.0, dry run + apply + validation, second apply 0 writes, forced-failure restore, project (b) apply, 420-check matrix, protected set unchanged); `headless verdict: green`; process reap and scratch-home teardown recorded. Interactive acceptance (SPEC R1) is a human item |
| 2 | SC2: label replaced by `validated headless (interactive confirmation pending)` | VERIFIED | `SKILL.md:253-254` splits into `pi hosts` (keeps **not live-validated**) and `cursor host` (validated headless, interactive confirmation **pending**); `README.md:45` "cursor validated headless (interactive confirmation pending)"; pinned by `test_cursor_label_lifted_with_evidence_pointer` (ran OK); lift landed with the evidence and SPEC/ROADMAP amendment in one commit `3a36abd` |
| 3 | SC3: cursor-agent detected and enumerated when wrapped by a shell function/alias (SPEC-06) | VERIFIED | `detection.py:167-187` scans PATH via `which(path=dir)`, accepts `agent` only when realpath basename is `cursor-agent`, never spawns a shell; `detection.py:311-357` parses `models` with explicit argv; `real_path` recorded at `detection.py:1053`. Tests `test_shell_function_is_invisible_to_the_lookup`, `test_cursor_listing_never_spawns_a_shell`, `test_grok_agent_first_then_cursor_agent_later_resolves`, `test_both_names_one_real_file_reported_once`, `test_agent_symlink_to_grok_does_not_resolve` ran OK. Runner `resolveBin` mirrors it (21-07, self-test case `agent-grok-first-then-cursor`) |
| 4 | SC4 (amended): `cursor-agents/composer-worker` and `grok-worker` pinned to explicit non-fast ids, tested against the bundle parser and captured `models` output | VERIFIED | Files carry `model: composer-2.5` / `model: grok-4.7-medium`, short task-execution bodies; `tests/test_cursor_agents.py` (bundle-rule parse, only bundle fields, non-fast ids from `tests/fixtures/cursor_models.txt`, no `gsd-` prefix, node regex parity) ran OK. Linking and live delegation are AGT-02 / backlog 999.7 per the amendment; README:60 documents manual linking |
| 5 | SC5: native per-call selection verified live, or `host_can_select` keeps cursor session-default-only | VERIFIED (OR branch) | `RUNTIMES["cursor"].native_selectors == ()`, `host_can_select("cursor","composer-2.5","cursor")` is False, pinned in `test_non_claude_hosts_have_no_native_selectors`; live probe optional (step 5 of the interactive script) |

**Score:** 5/5 truths verified (0 present, behavior-unverified)

Phase gates (SPEC R8), from the orchestrator on HEAD aa17ee7: `make test` exit 0 (4400 tests), `make validate` exit 0 (8 hooks), `make e2e-docker` exit 0; not re-run here per instruction.

### Prohibitions

| Prohibition | Tier | Enforcement | Status |
|---|---|---|---|
| Never execute the user's shell wrapper / an interactive shell during detection | test | `test_cursor_listing_never_spawns_a_shell`, `test_shell_function_is_invisible_to_the_lookup` | resolved |
| Never ship a `-fast` or config-dependent bare pin | test | `test_pins_are_non_fast_ids_from_the_captured_listing` | resolved |
| No write to `~/.cursor/cli-config.json` or other `~/.cursor` files | test | `snapshot --check` (strict cli-config.json/hooks.json, tree-hashed agents/skills since WR-04) reported `snapshot ok` for plans 04-06 baselines; `test_cursor_agents_skills_hooks_are_protected` | resolved |

### Deferred Items

| # | Item | Addressed In | Evidence |
|---|------|-------------|----------|
| 1 | Per-file linking into `.cursor/agents`, live delegation proof, usage-dashboard non-fast check (SPEC R6/R7) | Backlog 999.7 (AGT-02) | ROADMAP 999.7 criteria 1-2; REQUIREMENTS AGT-02 "Deferred (secondary runtime)" |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|---|---|---|---|
| Wrapper-proof detection + cursor agent bundle tests | `python3 -m unittest tests.test_cursor_agents tests.test_ai_kit_spec_runtimes_table` | Ran 67 tests, OK | PASS |
| Label pin | `python3 -m unittest tests.test_curated_config_apply -k cursor_label` | OK | PASS |
| Judge digest currency | `python3 tests/gsd_curated_eval.py digest` | `f0c43a5da52a587d` (recorded verdict `85da5a6682d937c5`) | stale, pending orchestrator re-judge |

### Requirements Coverage

| Requirement | Description | Status | Evidence |
|---|---|---|---|
| EVAL-07 | Live smoke on the cursor host | SATISFIED headless; interactive pending | Truths 1-2; human item 1 |
| SPEC-06 | cursor-agent detected through wrappers | SATISFIED | Truth 3 |
| AGT-01 | Pinned composer-worker / grok-worker files, tested | SATISFIED | Truth 4 |

No orphaned requirement: AGT-02 maps to 999.7, not Phase 21.

### Anti-Patterns Found

No `TBD`/`FIXME`/`XXX` markers in the phase's changed non-planning files. Only the info-level stale docstring at `routing.py:49` (owner list).

### Human Verification Required

1. **Interactive cursor run** — `21-INTERACTIVE-CURSOR.md` steps 1-4; remove the `pending` note in the commit that records it.
2. **Optional SC5 probe** — step 5; informational, SC5 already holds.
3. **Usage-dashboard check** — confirmed moved with AGT-02 to backlog 999.7; nothing to do in Phase 21.
4. **Skill-judge gate** — pending orchestrator step: re-run both judges on digest `f0c43a5da52a587d`; owner decides on pi 114 vs 116.

### Gaps Summary

No automated gap. Every roadmap criterion holds in code and committed evidence; the phase is `human_needed` on the interactive run and the in-flight skill-judge re-run.

---

_Verified: 2026-10-19_
_Verifier: Claude (gsd-verifier)_
