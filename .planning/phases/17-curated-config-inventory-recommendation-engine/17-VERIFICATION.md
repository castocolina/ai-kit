---
phase: 17-curated-config-inventory-recommendation-engine
verified: 2026-10-15T13:10:00Z
status: passed
score: 4/4 roadmap success criteria verified (9/9 requirements, 3/3 prohibitions)
covered_files:
  - .planning/phases/17-curated-config-inventory-recommendation-engine/17-01-PLAN.md
  - .planning/phases/17-curated-config-inventory-recommendation-engine/17-01-SUMMARY.md
  - .planning/phases/17-curated-config-inventory-recommendation-engine/17-02-PLAN.md
  - .planning/phases/17-curated-config-inventory-recommendation-engine/17-02-SUMMARY.md
  - .planning/phases/17-curated-config-inventory-recommendation-engine/17-03-PLAN.md
  - .planning/phases/17-curated-config-inventory-recommendation-engine/17-03-SUMMARY.md
  - .planning/phases/17-curated-config-inventory-recommendation-engine/17-04-PLAN.md
  - .planning/phases/17-curated-config-inventory-recommendation-engine/17-04-SUMMARY.md
  - .planning/phases/17-curated-config-inventory-recommendation-engine/17-05-PLAN.md
  - .planning/phases/17-curated-config-inventory-recommendation-engine/17-05-SUMMARY.md
  - .planning/phases/17-curated-config-inventory-recommendation-engine/17-06-PLAN.md
  - .planning/phases/17-curated-config-inventory-recommendation-engine/17-06-SUMMARY.md
  - .planning/phases/17-curated-config-inventory-recommendation-engine/17-07-PLAN.md
  - .planning/phases/17-curated-config-inventory-recommendation-engine/17-07-SUMMARY.md
  - .planning/phases/17-curated-config-inventory-recommendation-engine/17-08-PLAN.md
  - .planning/phases/17-curated-config-inventory-recommendation-engine/17-08-SUMMARY.md
  - .planning/phases/17-curated-config-inventory-recommendation-engine/17-09-PLAN.md
  - .planning/phases/17-curated-config-inventory-recommendation-engine/17-09-SUMMARY.md
  - skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/catalog_adapter.py
  - skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cli.py
  - skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/gsd_catalog.py
  - skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/host.py
  - skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/inventory.py
  - skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/plan_io.py
  - skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/plan_schema.py
  - skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/presets.py
  - skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/project_facts.py
  - skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/recommend.py
  - skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/roles.py
  - skills/ai-kit-spec-review/ai_kit_spec/detection.py
  - skills/ai-kit-spec-review/ai_kit_spec/model_ranker.py
  - tests/test_ai_kit_spec.py
  - tests/test_curated_config_e2e.py
  - tests/test_curated_config_golden.py
  - tests/test_curated_config_inventory.py
  - tests/test_curated_config_recommend.py
covered_digest: "v3:sha256:09da35e7bb8ce1a8548a4589e9688e9f583fde59d250b5a6928e2f539086e5d5"
behavior_unverified: 0
overrides_applied: 0
warnings:
  - finding: "First-ever offline run mislabels the catalog as stale"
    severity: warning
    detail: >-
      With no catalog cache, a failed fetch-model-catalog (models.dev and Artificial Analysis both
      unreachable) still exits 0 and writes a router-only catalog (the opencode router-env/* ids).
      catalog_adapter._catalog_state then sees non-empty entries and reports state "stale" with
      "catalog refresh failed; using the stale cache", though no cache existed. SPEC R3 expects
      "none". Slot filling is unaffected: the catalog is unscored, so the plans fall back exactly
      like "none" (codex keeps native slots, cursor/opencode get needs_choice). It only happens
      when opencode lists router ids; without them the state is "none".
    fix: >-
      Treat a catalog with no models_dev or artificial_analysis sourced entry as "none" (or pass
      "had a cache before the refresh" into _catalog_state), plus one fixture test.
    resolved: "28ba056: rows whose source flags are all false classify as none (test_failed_fetch_with_router_only_rows_is_none)"
---

# Phase 17: Curated-Config Inventory & Recommendation Engine Verification Report

**Phase Goal:** The rewritten `ai-kit-gsd-curated-config` can inventory a target project/host and
turn that inventory plus a profile/rigor choice into a pure, explainable, minimal recommendation
plan, without writing anything.
**Verified:** 2026-10-15
**Status:** passed (one warning, no blocker)
**Re-verification:** No (initial verification)

## How this was verified

- The code was read: `inventory.py`, `catalog_adapter.py`, `host.py`, `recommend.py`, `presets.py`
  and `cli.py`.
- A live end-to-end run used the real CLI, with no mocks:
  - a scratch HOME, and a scratch project holding a copy of this checkout's `.claude/gsd-core`
    (1.16.0), a `package.json` with react and an `AGENTS.md`;
  - fake `opencode`/`cursor-agent`/`codex`/`claude` executables first on PATH (models from the
    phase fixtures), and real `node` through volta;
  - every run inside `unshare -rn`, so there was no network.
- `make test` was run once at HEAD 4e28c43, along with the named phase test modules.

## Goal Achievement

### Observable Truths (roadmap success criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `inventory --project-dir` emits one JSON document covering host, the host's own gsd-core (path/version/valid keys), (runtime, model) candidates (scores, price, `image_input`, reasoning levels), skills, project facts, existing config and conflicts; it reads the catalog from `~/.cache/ai-kit/spec`, refreshes `--if-stale`, falls back to a stale-cache warning when refresh fails, and to native tier maps (Claude/Codex) or per-slot prompts (Cursor/opencode/pi) when no cache exists | VERIFIED | **Shape.** A live inventory on 4 hosts exits 0. Top-level keys: `schema_version, host, host_source, gsd_core{path, scope, version, valid_keys, runtime_profile_map, model_profiles, agent_to_phase_type}, candidates, candidate_heuristic_fields, catalog, existing_config, global_defaults, project, skills, conflicts, info, warnings`. Candidates carry runtime, model, is_host, provider, vendor, price, scores, score_axes, image_input, reasoning_modes and fast_twin_of.<br>**gsd-core.** `scope: local, version 1.16.0`, read from the project copy; a planted global 9.9.9 does not override it, and is used only for a project without a local install. A missing gsd-core exits 2 and lists 25 searched paths. `valid_keys` comes from a live `isValidConfigKey` probe (47 accepted).<br>**Catalog states.** Live runs give `fresh` (seeded, skip), `stale` plus "catalog refresh failed; using the stale cache" (60-day-old cache, offline), and `none` (no cache, offline).<br>**Fallbacks.** With no or an unscored catalog: codex plans `keep` the native `gpt-5.6-*` slots; claude plans have no `model_profile_overrides`; cursor/opencode slots are `needs_choice` with 3 candidates and "no scores".<br>**Read-only.** The project tree hash is identical before and after every inventory and recommend run.<br>**Caveat.** See the warning on the first offline run. |
| 2 | `recommend` is a pure function of inventory + profile + rigor + cross-AI answers; the same inputs give the same `plan.json`; every entry carries `key`, `value`, `why`, `source` | VERIFIED | `build_plan` imports only `typing`, `presets`, `roles` and `plan_schema`. `TestPurity` patches subprocess.run/Popen, socket, time.time/monotonic and builtins.open to raise and still passes, and an AST import guard has a non-vacuity test. Live: 24 plans (8 inventories: 4 fresh, 3 unscored, 1 no-catalog; x 3 rigors) each ran twice and were byte-identical with `cmp`. Every entry has key/op/value/source/why/existing (0 missing). `--out` inside the project `.planning/` is refused with exit 2. |
| 3 | The three model layers are set per rigor/profile: `model_profile` plus `models.<phase>` only on whole-phase shifts; `model_profile_overrides.<host>.{opus,sonnet,haiku}` by role score under the rigor price ceiling with host formatting (Claude skipped unless pinned, Codex ids with `reasoning_effort`, Cursor effort-suffixed); at most 7 specialist `model_overrides`; a "no in-runtime counterpart" note on single-provider hosts | VERIFIED | Live plans:<br>- `models.*` appear only as MVP research/verification=haiku and Rigorous planning=opus, verification=sonnet; Standard has none.<br>- Claude never gets `model_profile_overrides`.<br>- Codex values are `{model, reasoning_effort}`. In MVP, opus is replaced by `gpt-5.6-terra/high` because "gsd default gpt-5.6-sol above ceiling (40th pct)"; in Standard/Rigorous the natives are kept.<br>- Cursor values are effort-suffixed ids (`gemini-3.8-flash-low`, `claude-opus-5-5-xhigh`), and no `-fast` id is ever chosen.<br>- On opencode, the `anthropic/*` defaults are replaced ("not on host"), and the confirmed router `router-env/my-coding` wins the executor slot with `source: router-declared`.<br>- At most 6 `model_overrides` were seen; `SPECIALISTS` holds 7 agents, so the cap is structural.<br>- Claude and codex carry the counterpart note.<br>- None-catalog plans carry the vision note.<br>17 goldens (5 hosts x 3 rigors plus quality and budget spot checks) match in `tests.test_curated_config_golden`. |
| 4 | Keys unknown to the host gsd-core are dropped with a visible note | VERIFIED | Live: the 3 `dynamic_routing.*` keys were moved to `valid_keys.rejected` in a real inventory. The Rigorous plan then has 0 `dynamic_routing` entries and 3 `dropped_key` notes ("not accepted by the host gsd-core 1.16.0 isValidConfigKey"). A key in neither list fails closed with exit 2 (`TestUnprobedKeys`). |

**Score:** 4/4 truths verified (0 present-but-behavior-unverified)

### Prohibitions (SPEC must-NOT, test tier)

| Prohibition | Status | Evidence |
|---|---|---|
| No write to the project, its `.planning/` or any tool config during inventory/recommend | VERIFIED | `TestReadOnly` and e2e `TestReadOnlyRealGsd`. Live: the hashes of all 3 scratch projects are unchanged, and `--out` into `.planning/` is refused. |
| No `catalog-score` source without scores | VERIFIED | Live: there are 0 `catalog-score` entries in all 12 unscored or no-catalog plans. Unit: `TestSlotEdges`. |
| No auto-selected `-fast` twin when its non-fast model exists | VERIFIED | Live: no plan value ends in `-fast`, across the cursor and opencode plans. `fast_twin_of` is computed in `catalog_adapter`. |

### Required Artifacts

| Artifact | Status | Details |
|---|---|---|
| `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/inventory.py` | VERIFIED | Real config reads, conflict classifier, live gsd-core probe; wired via `cli._cmd_inventory` |
| `.../catalog_adapter.py` | VERIFIED | detect-runtimes then fetch-model-catalog (`--if-stale`), state classification, candidate join |
| `.../host.py` | VERIFIED | Project-local-first resolution through the shared `ai_kit_spec.gsd_tools` |
| `.../recommend.py`, `presets.py`, `roles.py`, `plan_schema.py`, `plan_io.py` | VERIFIED | 6 ordered layers, per-layer key drop, canonical JSON, atomic `--out` |
| `skills/ai-kit-spec-review/ai_kit_spec/detection.py` (opencode 2.x probe), `model_ranker.py` (`score_exact`) | VERIFIED | 30/30 `TestOpencodeApiImageInput` tests pass |

### Key Link Verification

| From | To | Via | Status |
|---|---|---|---|
| `cli inventory` | `inventory.build_inventory` -> `host.resolve_gsd_core` -> `gsd_catalog.query_gsd_tables` (node) | subcommand dispatch | WIRED (live run reads 1.16.0 tables) |
| `inventory` | `catalog_adapter.refresh_catalog` -> `ai-kit-spec.py detect-runtimes / fetch-model-catalog` | subprocess argv | WIRED (fake CLIs were enumerated, so runtimes.json was produced) |
| `cli recommend` | `plan_io.load_inventory` -> `recommend.build_plan` -> `plan_io.write_plan` | subcommand dispatch | WIRED |

### Behavioral Spot-Checks

| Behavior | Result | Status |
|---|---|---|
| inventory x 4 hosts (fresh, stale, none) | rc 0; markers as expected | PASS |
| recommend x 24 inventory/rigor pairs, run twice | byte-identical | PASS |
| conflict matrix (project policy/omit/runtime mismatch; global policy with and without a project config; global runtime) | conflicts: project model_policy, resolve_model_ids omit, runtime cursor!=claude; latent global model_policy without a project config. info: inert global model_policy, global runtime, stale `claude_md_path`. Plan: per-leaf `model_policy.*` unsets, `resolve_model_ids` unset, leftover `model_overrides.gsd-planner` unset, runtime_mismatch note | PASS |
| missing gsd-core | exit 2 with the searched paths | PASS |
| `python3 -m unittest tests.test_curated_config_golden tests.test_curated_config_recommend` | 132 tests OK | PASS |
| `python3 -m unittest tests.test_ai_kit_spec -k TestOpencodeApiImageInput` | 30 tests OK | PASS |
| `make test` (PATH with `~/.local/bin`, `UV_NO_SYNC=1 UV_OFFLINE=1`, runner capped at 40% of CPUs) | exit 0. unit 31/31 + 1/1 modules, integration 4/4, e2e 5/5 modules, arch 1/1: 3396 tests in total, plus 45/45 `test_install.sh` checks | PASS |

### Requirements Coverage

| Requirement | Status | Evidence |
|---|---|---|
| INV-01 | SATISFIED | Truth 1 (shape, gsd-core, candidates, project facts: AGENTS.md-only detected, frontend true, db false) |
| INV-02 | SATISFIED | Truth 1 (fresh, stale and none plus the fallbacks); see the warning |
| INV-03 | SATISFIED | Conflict-matrix spot-check |
| REC-01 | SATISFIED | Truth 2 |
| REC-02 | SATISFIED | Truth 3 (`models.*` only on phase shifts) |
| REC-03 | SATISFIED | Truth 3 (ceiling, native keep, codex/cursor formatting, no `-fast`) |
| REC-04 | SATISFIED | Truth 3 (structural cap of 7, counterpart, vision and router rules) |
| REC-05 | SATISFIED | `presets.PRESETS` checked against design spec section 5 (granularity, effort, gates, `intel.enabled` on Standard and Rigorous, `dynamic_routing` on Rigorous, `mvp_mode` on MVP); `TestPresets` |
| REC-06 | SATISFIED | Truth 4 |

No orphaned requirements: REQUIREMENTS.md maps exactly these 9 ids to Phase 17.

### Anti-Patterns Found

| File | Pattern | Severity | Impact |
|---|---|---|---|
| `catalog_adapter.py` `_catalog_state` | A non-empty catalog written by a failed first fetch (router entries only) is classified `stale` | Warning | Wrong marker and warning text on the first offline run; plan output is unchanged (see the frontmatter `warnings`) |

The debt-marker scan (TBD/FIXME/XXX/TODO/HACK/PLACEHOLDER) over all phase modules and tests found nothing.

### Human Verification Required

None. The live `opencode serve` 2.x `image_input` probe (17-VALIDATION manual-only row) is
**optional**, not a gate:
- 30 unit tests cover the 2.x parser, the version gate, server stop on every path, the password
  never being output, and the 1.x path unchanged. Their response shape comes from a sample
  captured from a real opencode v2.0.29 during the spike.
- A failed probe is never silent: it becomes `image_input_probe: failed` plus an inventory
  warning.
- `image_input` also comes from the models.dev catalog.

Run it once when opencode 2.x is next live on a host:
1. Run `inventory` under a scratch HOME/XDG.
2. Check that the opencode candidates show `image_input_source` as the 2.x API.
3. Check with `pgrep` that no probe server is left running.

### Gaps Summary

No blocking gaps:
- All 4 roadmap success criteria, all 9 requirements and all 3 prohibitions hold in code and in
  live runs.
- One warning, a cosmetic misclassification with no effect on the plan: on a first-ever run
  with no network, a router-only catalog written by the failed fetch is reported as `stale`
  instead of `none`. It is worth a `/gsd-quick` fix before Phase 18 shows `catalog.state` to
  users.

---

_Verified: 2026-10-15_
_Verifier: Claude (gsd-verifier)_
