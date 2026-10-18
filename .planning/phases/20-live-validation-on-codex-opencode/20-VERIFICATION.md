---
phase: 20-live-validation-on-codex-opencode
verified: 2026-10-18T14:00:00Z
status: human_needed
score: 8/9 must-haves verified
covered_files:
  - ".planning/phases/20-live-validation-on-codex-opencode/20-01-PLAN.md"
  - ".planning/phases/20-live-validation-on-codex-opencode/20-01-SUMMARY.md"
  - ".planning/phases/20-live-validation-on-codex-opencode/20-02-PLAN.md"
  - ".planning/phases/20-live-validation-on-codex-opencode/20-02-SUMMARY.md"
  - ".planning/phases/20-live-validation-on-codex-opencode/20-03-PLAN.md"
  - ".planning/phases/20-live-validation-on-codex-opencode/20-03-SUMMARY.md"
  - ".planning/phases/20-live-validation-on-codex-opencode/20-04-PLAN.md"
  - ".planning/phases/20-live-validation-on-codex-opencode/20-04-SUMMARY.md"
  - ".planning/phases/20-live-validation-on-codex-opencode/20-05-PLAN.md"
  - ".planning/phases/20-live-validation-on-codex-opencode/20-05-SUMMARY.md"
  - ".planning/phases/20-live-validation-on-codex-opencode/20-06-PLAN.md"
  - ".planning/phases/20-live-validation-on-codex-opencode/20-06-SUMMARY.md"
  - ".planning/phases/20-live-validation-on-codex-opencode/20-07-PLAN.md"
  - ".planning/phases/20-live-validation-on-codex-opencode/20-07-SUMMARY.md"
  - ".planning/scripts/cross-ai.mjs"
  - "skills/ai-kit-gsd-curated-config/SKILL.md"
  - "skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cross_ai.py"
  - "skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/followups.py"
  - "skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/host.py"
  - "skills/ai-kit-spec-review/ai_kit_spec/detection.py"
  - "skills/ai-kit-spec-review/references/cross-ai.mjs"
  - "tests/gsd_curated_eval.py"
  - "tests/test_ai_kit_gsd_curated_config_matrix.py"
  - "tests/test_ai_kit_spec_runtimes_table.py"
  - "tests/test_curated_config_plan_edit.py"
  - "tests/test_curated_config_recommend.py"
  - "tests/test_gsd_curated_eval.py"
covered_digest: "v3:sha256:8da239292e26cdf22c47936efa20de3ce0b758576a14794dfc1d18e8442544a4"
behavior_unverified: 0
overrides_applied: 0
human_verification:
  - test: "Run 20-INTERACTIVE-CODEX.md required steps 1-5 from the user's own codex TUI session"
    expected: "Names-only env list shows CODEX_THREAD_ID/CODEX_VERSION; smoke exit 0 with all 10 steps pass; snapshot check ok; artifacts returned; trust-prompt note recorded"
    why_human: "SPEC constraint: only the user's interactive session counts as EVAL-04 evidence; the committed evidence is headless codex exec. EVAL-04 stays Pending in REQUIREMENTS.md until then."
  - test: "Run 20-INTERACTIVE-OPENCODE.md required steps 1-4, 6 and 7 from the user's own opencode TUI session"
    expected: "Smoke exit 0; four unblocked lane-trial outcomes (step 6, --opencode and default_reviewers, two trials each); loader output proving project agents load over global ones (step 7, smoke --keep-scratch)"
    why_human: "SPEC constraint for EVAL-05; the lane mechanics trials need a GSD project with plans and are LLM-judged; loader precedence has no headless listing path. EVAL-05 stays Pending until then."
  - test: "Optional native per-call model selection probe (codex script step 6, opencode script step 5; ROADMAP SC3 calls it 'step 8')"
    expected: "Either the host takes the requested model natively (label could be upgraded) or nothing changes"
    why_human: "SC3's session-default branch is already satisfied by native_selectors == () and its unit test; the probe is an optional upgrade only and needs a live TUI."
  - test: "Owner decision on WR-12: 29 opencode *.compact.md agents carry no model: line"
    expected: "Decide upstream gsd-core report vs a documented SKILL.md limit"
    why_human: "Product decision; both smokes report it explicitly and do not fail on it (20-REVIEW-FIX.md Owner review)."
  - test: "Owner decision on the skill-judge fix-cap accounting (20-SKILL-JUDGE.md: 2 of 2 rounds plus one voluntary edit)"
    expected: "Accept or reject the accounting"
    why_human: "Process judgment; both final rows pass (109/120, 116/120, 0/0) on digest ea3200ce9624de80."
  - test: "Owner review of RUN-106: commit e40ced6 changes the v1 test-suite template pin '3' -> '4' in tests/test_ai_kit_spec.py"
    expected: "Accept the two-literal v1-suite edit (v1 kept intact per Phase 18 D-08)"
    why_human: "Touches the v1 path the owner chose to keep untouched pending evidence."
  - test: "Owner review of the codex gpt-5.6-luna smoke-skip finding (20-SMOKE-CODEX.md 'Smoke evidence' preamble)"
    expected: "Decide whether 4 of 6 no_change dispatches without running the command need a follow-up"
    why_human: "Cause not established; non-deterministic model behavior."
  - test: "Owner review of IN-07: the matrix e2e tier reads more real host config (read-only)"
    expected: "Accept as the Phase 19 D-08 real-HOME design or tighten"
    why_human: "Trade-off against the AGENTS.md real-config rule; recorded, not fixed (20-REVIEW-FIX.md)."
---

# Phase 20: Live Validation on Codex + Opencode Verification Report

**Phase Goal:** The skill is confirmed working from real codex and opencode host sessions, resolving the two open verifications the spec left pending.
**Verified:** 2026-10-18
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | SC1: codex host smoke (inventory + recommend + apply) completes; codex env signal confirmed live | ✓ VERIFIED (headless) | 20-SMOKE-CODEX.md: runner dispatch `smoke exit=0`, steps 1-10 pass, host codex (detected); env names list shows CODEX_THREAD_ID and CODEX_VERSION. `detection.py:52-57` `_LABEL_CODEX` "live-verified (Phase 20) ... TUI confirmation pending"; table `detection.py:100`; pinned by `test_codex_labels_are_live_verified` (tests/test_ai_kit_spec_runtimes_table.py:87) and the docstring test (tests/test_ai_kit_spec.py:1349-1355). Interactive TUI confirmation is a human item. |
| 2 | SC2: opencode host smoke completes; opencode-lane finding reflected in recommend and SKILL.md with a test | ✓ VERIFIED (headless; lane trials human) | 20-SMOKE-OPENCODE.md: `smoke exit=0`, steps 1-10 pass, `--standalone` argv, no managed-port clash. Policy default (host never a lane): SKILL.md:216-220 and :254; `test_host_slug_never_a_review_lane_on_codex_and_opencode` (tests/test_curated_config_recommend.py:1608) and `test_host_slug_never_a_review_lane` (tests/test_curated_config_plan_edit.py:397) — both run and pass. Whether an intentional same-CLI lane is usable is the required interactive step 6. |
| 3 | SC3: native per-call selection — host takes requested model, or host_can_select keeps session-default-only | ✓ VERIFIED | `routing.py:44-55` requires `model in RUNTIMES[runtime].native_selectors`; `test_non_claude_hosts_have_no_native_selectors` (tests/test_ai_kit_spec_runtimes_table.py:96-100) pins codex/opencode to `()`. Module run: 48 tests OK. |
| 4 | R1: each scratch project shows a local, pinned gsd-core | ✓ VERIFIED | Both smokes: `scope local`, version 1.17.0 for project-a and project-b, installed into `.codex/gsd-core` / `.opencode/gsd-core`. |
| 5 | R4/R7: codex and opencode matrices pass (5 x 35, model and tier) | ✓ VERIFIED | Smoke step 9 `matrix ran: 420 checks`, controls ok, on each host; `TestResolveModelMatrixCodex`/`TestResolveModelMatrixOpencode` (tests/test_ai_kit_gsd_curated_config_matrix.py:102-107) run inside `make test` (exit 0). |
| 6 | R5: opencode baked models equal plan, and project agents win over global ones | ? UNCERTAIN (human) | planned == baked == resolve-model for 35 agents on both projects (verified). Loader precedence was not observable headless (20-SMOKE-OPENCODE.md "Local install and precedence"); required interactive step 7. |
| 7 | R8: headless runs and environment findings recorded | ✓ VERIFIED | Run tables with verbatim AIKIT-XAI lines, signal probes, not-provoked items labeled as such, in both smoke files. |
| 8 | R9: fixes carry regression tests; `make test` and `make validate` green | ✓ VERIFIED | Orchestrator gates on HEAD 2026-10-18: make test exit 0 (4348 tests), make validate exit 0, make e2e-docker PASS. 20-REVIEW-FIX.md: 28/31 fixed with linked tests; 3 skipped with stated reasons. |
| 9 | MUST NOT: no global opencode/codex config modified; no secret or env value in evidence | ✓ VERIFIED (judgment) | Env sections are names-only; installs ran under a throwaway HOME/XDG; protected set `unchanged` on both hosts; 20-SECURITY.md threats_open 0. |

**Score:** 8/9 truths verified (0 present, behavior-unverified; 1 uncertain, routed to human)

### Required Artifacts

| Artifact | Status | Details |
|----------|--------|---------|
| `skills/ai-kit-spec-review/ai_kit_spec/detection.py` | ✓ VERIFIED | Codex labels live-verified, opencode label updated |
| `skills/ai-kit-spec-review/references/cross-ai.mjs` + `.planning/scripts/cross-ai.mjs` | ✓ VERIFIED | template 4, `--standalone` in opencode argv (20-SMOKE-OPENCODE.md --print-argv) |
| `skills/ai-kit-gsd-curated-config/SKILL.md` | ✓ VERIFIED | Host-never-a-lane text; skill-judge 109/116, 0/0 |
| `tests/gsd_curated_eval.py` (host-aware oracle, smoke harness) | ✓ VERIFIED | Exercised by both smokes and the matrix classes |
| `20-SMOKE-CODEX.md`, `20-SMOKE-OPENCODE.md` | ✓ VERIFIED | Regenerated after review fixes |
| `20-INTERACTIVE-CODEX.md`, `20-INTERACTIVE-OPENCODE.md` | ✓ VERIFIED | Required/optional steps labeled |
| `tmp/p20/headless/*-artifacts/` | ✓ present | Untracked scratch (gitignored), as stated |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Detection table + native selectors | `python3 -m unittest tests.test_ai_kit_spec_runtimes_table` | 48 tests OK | ✓ PASS |
| Host never a lane | `python3 -m unittest -k test_host_slug_never_a_review_lane tests.test_curated_config_recommend tests.test_curated_config_plan_edit` | 2 tests OK | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Status | Evidence |
|-------------|-------------|--------|----------|
| EVAL-04 | 20-02, 20-04, 20-06, 20-07 | ? NEEDS HUMAN | Headless evidence complete; interactive codex run pending; REQUIREMENTS.md:171 Pending (correct) |
| EVAL-05 | 20-01, 20-02, 20-05, 20-06, 20-07 | ? NEEDS HUMAN | Headless evidence complete; interactive steps 6 and 7 pending; REQUIREMENTS.md:172 Pending (correct) |

No orphaned requirement IDs for Phase 20.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| changed source files | — | no TBD/FIXME/XXX | — | — |
| `.planning/ROADMAP.md` | Phase 20 SC3 | refers to "20-07 step 8"; the optional probe is codex step 6 / opencode step 5 | ℹ️ Info | Stale cross-reference |
| `20-SMOKE-CODEX.md` / `20-SMOKE-OPENCODE.md` | Phase gates | "Ran 36 tests" / "4,343 tests"; superseded by 27 (TestMatrixModuleCollection, tests/test_gsd_curated_eval.py:3833) and 4348 | ℹ️ Info | Stale gate counts; REVIEW-FIX notes the supersession |
| `20-SMOKE-CODEX.md` | Local install | `root /var<scratch-a>` keeps a `/var` prefix outside the label | ℹ️ Info | Cosmetic redaction gap, no secret |

### Human Verification Required

See the `human_verification` frontmatter list: two interactive TUI runs (EVAL-04, EVAL-05), the optional native-selection probe, and five owner-review items (WR-12, skill-judge fix-cap accounting, RUN-106 / e40ced6, the gpt-5.6-luna smoke-skip finding, IN-07).

### Gaps Summary

No automated gap. Every automated success criterion holds in code, tests and committed headless evidence. What remains is the SPEC-mandated interactive evidence (EVAL-04/EVAL-05 stay Pending until the user's TUI runs) and owner decisions.

---

_Verified: 2026-10-18_
_Verifier: Claude (gsd-verifier)_

## Resolved after verification (orchestrator, 2026-10-18)

- ROADMAP SC3's optional-probe reference now names `20-INTERACTIVE-CODEX.md` step 6 and `20-INTERACTIVE-OPENCODE.md` step 5.
- Both smoke files' "Phase gates" lines carry a superseded note (27 matrix tests, 4,348 total).
- The `/var<scratch-*>` redaction gap was a harness bug: `_smoke_placeholders` now also replaces realpath forms (regression test `test_smoke_placeholders_cover_the_realpath_form`); the two evidence lines were corrected.
- Skill-judge digest checked: `python3 tests/gsd_curated_eval.py digest` prints `ea3200ce9624de80`, equal to `20-SKILL-JUDGE.md`.
