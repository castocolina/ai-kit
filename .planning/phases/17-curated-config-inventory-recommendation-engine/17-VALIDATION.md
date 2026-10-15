---
phase: "17"
slug: "curated-config-inventory-recommendation-engine"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-10-15"
---

# Phase 17 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | stdlib `unittest` via `tools/run_unittest_parallel.py` tiers (CPU-share-capped, one subprocess per module) |
| **Config file** | `tools/run_unittest_parallel.py` (`EXPLICIT_GROUPS`); listings from `tools/gen_test_groups.py`; enforced by `tests/test_gate_scope.py` |
| **Quick run command** | `python3 -m unittest tests.test_curated_config_recommend tests.test_curated_config_inventory -v` |
| **Full suite command** | `make test` (plus `make validate` before close) |
| **Estimated runtime** | ~10 seconds quick, ~120 seconds full |

---

## Sampling Rate

- **After every task commit:** run the quick command for the touched module(s)
- **After every plan wave:** `make test-unit && make arch-test`
- **Before `/gsd-verify-work`:** `make test` and `make validate` must be green
- **Max feedback latency:** 120 seconds

---

## Per-Task Verification Map

### Requirement → Test Map (task IDs filled by the planner)

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| INV-01 | inventory shape validates; read-only project byte-identical (tree + bytes hash before/after, chmod read-only dir) | unit (+ real gsd when available) | `python3 -m unittest tests.test_curated_config_inventory -v` | ❌ Wave 0 |
| INV-01 / R2 | local fake gsd-core beats global; scope label; exit 2 + searched paths; probe `null` → exit 2 | unit | same | ❌ |
| INV-02 / R3 | fresh / stale+warning / none markers via fake `run_fn` outputs; `--refresh` argv | unit | same | ❌ |
| INV-03 / R5 | conflict matrix incl. GSD_HOME, Branch C/D, latent global omit | unit | same | ❌ |
| R6 | AGENTS-only / CLAUDE-only / both / neither; frontend; db | unit | same | ❌ |
| REC-01 / R7 | two runs byte-identical; purity patch test; AST import guard; unsupported schema → exit 2 | unit | `python3 -m unittest tests.test_curated_config_recommend -v` | ❌ |
| REC-02 / R8 | `models.*` only per rigor shifts (3 rigors × adaptive) | unit (golden) | `python3 -m unittest tests.test_curated_config_golden -v` | ❌ |
| REC-03 / R9 | native kept (codex), `anthropic/*` replaced (opencode), cursor no native map, `-fast` never chosen, router-declared wins, cap never empties, at-ceiling within, family percentile, effort-variant rule | unit + golden | both | ❌ |
| R4 | unscored catalog: claude/codex no `model_profile_overrides`; opencode/cursor `needs_choice` with `no scores`; no `catalog-score` source | unit | recommend | ❌ |
| REC-04 / R10 | ≤7 overrides in all goldens; counterpart vendor; vision warning; single-provider note; pi no overrides | golden | golden | ❌ |
| REC-05 / R11 | table-driven: every §5 key/value per rigor | unit | recommend | ❌ |
| REC-06 / R12 | `valid_keys` without `dynamic_routing.*` → keys dropped + note(s) per the OQ5 decision | unit | recommend | ❌ |
| R13 | tie order independent of input order (shuffled candidates); leftover `model_overrides.gsd-planner` → unset; `model_policy` per actual leaf incl. `runtime_tiers` | unit | recommend | ❌ |
| D-15 | `score_exact` present, unrounded; `score` unchanged | unit | `python3 -m unittest tests.test_ai_kit_spec -k score_exact` | extend existing |
| D-24 | 2.x parser on the spike sample; version gate; server killed on every path; token never in output; 1.x path unchanged; schema bump | unit | `python3 -m unittest tests.test_ai_kit_spec -k opencode` | extend existing |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/fixtures/curated_config_v2/gsd_tables_1_16.json`: tables captured once from the installed 1.16 (D-20), placeholder paths only
- [ ] `tests/fixtures/curated_config_v2/` trimmed model lists (cursor, opencode, codex, claude) plus a synthetic pi list (labelled)
- [ ] `tests/fixtures/opencode_api_model.json`: the spike sample (4 entries)
- [ ] the three new test modules, then `python3 tools/gen_test_groups.py`
- [ ] golden regeneration flag (for example env `AI_KIT_REGEN_GOLDENS=1`), never on by default

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| opencode 2.x probe against a real `opencode serve` (D-24/D-32) | INV-01 | the suite uses a fake server; a live run needs opencode 2.x | run `inventory` under a scratch HOME/XDG, then check that `image_input_source` is the 2.x API and that no probe server is still running (`pgrep`) |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 120s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
