# Phase 17: Curated-Config Inventory & Recommendation Engine — Specification

**Created:** 2026-10-14
**Ambiguity score:** 0.14 (gate: ≤ 0.20)
**Requirements:** 13 locked

## Goal

`ai-kit-gsd-curated-config` gains `inventory --project-dir` (one read-only JSON snapshot of
host, gsd-core, model candidates, skills, project facts, existing config and conflicts) and a pure
`recommend` that turns it plus profile, rigor and the two cross-AI answers into a deterministic,
explainable, minimal `plan.json`, with nothing written to the project.

## Background

- **v1 is the only flow.** `skills/ai-kit-gsd-curated-config/` today ships the v1 CLI: `cli.py`, `preference_match.py`, `critical_agents.py`, `workflow_defaults.py`, `cross_ai_build.py` and the detectors `frontend_detect.py`, `claude_md_detect.py` and `model_detect.py`. There is no `inventory`, no `recommend` and no `plan.json`. v1 stays unchanged (Phase 18 D-08).
- **`gsd_catalog.py` looks only for a global gsd-core.** Phase 16.1 D-18 moves the resolver into a shared `ai_kit_spec/gsd_tools.py` with project-local-first order. Since then the facts changed:
  - gsd-core is 1.16.0 (the spec assumed 1.14);
  - GSD is installed per repo;
  - `~/.gsd/defaults.json` sets `runtime: codex`.
- **The catalog is partly scored.** An Artificial Analysis key is configured, and a live fetch scored 196 of 254 entries (intelligence ~77%, coding ~47%, agentic ~44%). The shared ranker scores a missing axis as 49/100 and rounds scores to 1 decimal.
- **Phase 18.1 will turn every model candidate into a (runtime, model) pair** and remove `native_runtime`.
- **The user measured Cursor's `-fast` twins at about 5× the token spend** and wants the non-fast variants (2026-10-13 todo, AGT-01).
- **`claude_md_path` is stale.** `claude_md_detect.py` already prefers `AGENTS.md`, but this repo's `.planning/config.json` still holds the v1 literal `claude_md_path: ./CLAUDE.md`, which points at a missing file.
- **Phase 17's CONTEXT (2026-09-23) already locks D-01..D-08:** the Claude layer-2 skip, keeping native slots, the percentile price ceiling, router preference, `needs_choice`, deterministic ties, non-blocking specialists, and authoritative managed families. This SPEC keeps all of them.

## Requirements

1. **Inventory snapshot**: one JSON document, read-only for the project.
   - Current: none.
   - Target: `inventory --project-dir DIR [--refresh]` prints `schema_version`, `host`, `gsd_core`, `candidates` (one entry per (runtime, model) pair with `is_host`, provider, scores, price, `image_input`, `reasoning_modes`), `skills`, `project`, `existing_config` and `conflicts`. It writes only inside ai-kit's own cache (`~/.cache/ai-kit/spec`), never in the project or another tool's config.
   - Acceptance: a fixture run produces a document that validates against the documented shape, and a test with a read-only project directory succeeds and leaves it byte-identical.

2. **Host gsd-core**: read from the install the project actually uses.
   - Current: global candidates only.
   - Target: resolution goes through the shared project-local-first resolver (16.1 D-18). `gsd_core` reports `path`, `version`, `valid_keys`, `RUNTIME_PROFILE_MAP` and `MODEL_PROFILES`, all read from that install, never from a hardcoded copy.
   - Acceptance: with a project-local fake gsd-core and a global one, the inventory reports the local path and version. Valid keys come from its `isValidConfigKey`. A missing gsd-core exits 2 and lists the searched paths.

3. **Catalog freshness**: refresh, stale and none are distinct.
   - Current: no adapter.
   - Target: the inventory runs `detect-runtimes --if-stale` then `fetch-model-catalog --if-stale`. When the refresh fails it uses the stale cache and adds a warning. When no catalog exists it marks `catalog: none`.
   - Acceptance: the three states are covered by fixture tests, and each produces its marker in the inventory.

4. **Unscored catalog**: prices without scores never fake a ranking.
   - Current: undefined.
   - Target: a catalog with no score axes counts as no catalog for slot filling. Unscored is also decided per pick: a candidate with zero score axes is never auto-picked; it appears only in `needs_choice` tagged `no scores`. The one exception is a user-confirmed router winning a slot by its declared purpose.
     - Claude and Codex keep their native tier maps.
     - Cursor and opencode get `needs_choice` entries whose candidates show prices and a `no scores` note; pi gets an opt-in `model_profile_overrides.pi.sonnet` `needs_choice` entry with `candidates: []` (amended 2026-10-15: D-22 as amended by 22 D-05).
   - Acceptance: with an unscored fixture catalog, the Claude and Codex plans set no `model_profile_overrides` value (amended 2026-10-15, D-18: Codex `op: keep` entries write nothing), and the opencode plan has a `needs_choice` per non-native slot with that note.

5. **Conflicts**: reported only when they change resolution.
   - Current: none.
   - Target:
     - `model_policy` in the project config is a conflict.
     - `model_policy` in `~/.gsd/defaults.json` is a conflict only when no project config exists (creating one copies it). With a project config present, gsd-tools ignores the global file, so it is listed under `info` as inert.
     - A project `resolve_model_ids: "omit"` on a claude host is a conflict: every agent without a per-agent override then resolves to `model: ""` and inherits the session model (verified 2026-10-14; `config-new-project` copies it from global defaults).
     - A project `runtime` that differs from the host is a conflict. A global `runtime` is never a `resolve-model` conflict: gsd-tools fills an absent project runtime from env or an install marker, never from global defaults. It is listed under `info`. *(amended 2026-10-14, 20 D-08: the installer's model bake does read the global `runtime` when the project has none, so `recommend` writes project `runtime: <host>` as a managed key on opencode and codex — 17 D-23.)*
   - Acceptance: fixtures for policy-in-project, policy-in-global with and without a project config, a project runtime mismatch, and a global runtime each yield the expected entry.

6. **Project facts**: the instruction file is found by its real name.
   - Current: `claude_md_detect` assumes `CLAUDE.md`.
   - Target: `project` reports `frontend`, `db`, `instruction_files` (which of `AGENTS.md` / `CLAUDE.md` exist) and `intel_index_present`.
   - Acceptance: fixtures with only `AGENTS.md`, only `CLAUDE.md`, both and neither report correctly. A frontend fixture and a DB fixture are detected.

7. **Pure, deterministic recommend**: same inputs, same bytes.
   - Current: none.
   - Target: `recommend --inventory --profile --rigor [--cross-ai-review y|n] [--cross-ai-exec y|n] --out plan.json` performs no subprocess, network, clock or filesystem read beyond its input file. Every entry carries `key`, `value`, `why`, `op` (`set | unset | keep`), `source` (`preset | catalog-score | curated-affinity | router-declared | user | native`) and `existing`. `keep` writes nothing and explains a kept gsd default; `router-declared` marks a user-confirmed router winning by declared purpose. The plan carries `schema_version` and the inventory digest.
   - Acceptance: two runs on the same inputs are byte-identical. A test patches `subprocess`, `socket`, `time` and `open` (except the input) to raise, and `recommend` still succeeds.

8. **Tier layer**: `model_profile` plus phase shifts only.
   - Current: v1 heavy sweep.
   - Target: `model_profile` is set (adaptive recommended). `models.<phase_type>` is set only where the rigor preset shifts a whole phase (MVP research/verification → haiku; Rigorous planning → opus, verification → sonnet).
   - Acceptance: golden plans for 3 rigors × adaptive show exactly those `models.*` keys.

9. **Tier → model layer**: overrides only where the native slot fails.
   - Current: none.
   - Target: `model_profile_overrides.<host>.<tier>` is written only when the native slot's model is missing from the host's candidates or is above the rigor price ceiling. Claude is skipped unless pinned. A router with a user-confirmed declared purpose wins its slot and is exempt from the ceiling. A `-fast` twin is excluded from automatic filling whenever its non-fast model exists. The twin link is computed once in the catalog adapter (`fast_twin_of` on each inventory candidate). The ceiling percentile is taken over distinct model families (effort variants collapsed), and only tier slots some agent resolves to under the profile, phase shifts and dynamic routing are filled or asked about. (Amended 2026-10-15, D-17 note: live gsd-core 1.16 showed no model escalation from Rigorous dynamic routing, so dynamic routing adds no tier slot unless a later gsd-core proves an effect.)
   - Acceptance:
     - Golden plans for codex (native kept), opencode (`anthropic/*` replaced, the user's confirmed router chosen for its role), and cursor (no native map, `-fast` never chosen). (Amended 2026-10-15: live `cursor-agent` enumerates no router ids, so the router case is asserted on the opencode golden.)
     - A cap test shows a slot is never emptied: when nothing passes, the cheapest eligible model is used with that `why`.

10. **Specialists**: at most 7 `model_overrides`.
    - Current: v1 critical agents.
    - Target:
      - `gsd-plan-checker` uses a provider other than the planning slot's (provider = inferred vendor: id prefix, else catalog provider; a candidate whose vendor cannot be inferred is not eligible for the automatic counterpart pick);
      - `gsd-code-reviewer` uses a provider other than the execution model's;
      - `gsd-ui-auditor` and `gsd-dom-verifier` require `image_input`;
      - `gsd-ui-researcher` is frontend-capable, only when a frontend exists;
      - `gsd-executor` and `gsd-code-fixer` take the execution role with effort `medium`.

      A single-provider host gets the explicit "no in-runtime counterpart → use cross-AI review" note instead of an override. A specialist with no eligible model gets a warning, never a block.
    - Acceptance: golden plans never exceed 7 `model_overrides`. Single-provider fixtures (claude, codex) carry the note. A host with no `image_input` model carries the vision warning.

11. **Rigor presets**: data-only tables per spec §5.
    - Current: v1 fixed bundle.
    - Target: MVP, Standard and Rigorous set granularity, effort tiers, gates (nyquist, TDD, code-review depth, ASVS, UI review), `intel.enabled` (Standard, Rigorous), `dynamic_routing` (Rigorous) and `workflow.mvp_mode` (MVP), exactly as spec §5 lists. (Amended 2026-10-15, D-29: `workflow.live_dom_uat` is not managed in Phase 17; Rigorous with a frontend adds a note pointing to `plan-set` instead.)
    - Acceptance: a table-driven test asserts every §5 key and value per rigor, except `workflow.live_dom_uat` (D-29).

12. **Unknown keys dropped**: the plan never proposes a key the host's gsd-core rejects.
    - Current: none.
    - Target: `inventory` calls the host gsd-core's `isValidConfigKey` once per key in the closed set `recommend` can propose (central keys, dynamic patterns and capability keys all apply) and stores accepted and rejected keys. `recommend` drops a rejected key and adds a `notes` entry naming it.
    - Acceptance: a fixture `valid_keys` without `dynamic_routing.*` gives a Rigorous plan with no such keys and one note per dropped key (3 notes; amended 2026-10-15, RUN-39b).

13. **Undecidable slots and existing keys**: explicit, never silent.
    - Current: none.
    - Target:
      - An undecidable required slot becomes `{status: "needs_choice", value: null, candidates: top 3 with score/price/why}`.
      - Ties break by score descending (the ranker's unrounded `score_exact`), then price ascending, then model id ascending.
      - An existing key in a managed family that the plan does not set becomes `op: "unset"` with a `why`.
      - On a claude host, a project `resolve_model_ids: "omit"` is proposed for unset.
      - A project `model_policy` is always proposed for unset, one entry per leaf (`model_policy.provider|budget|high|medium|low`): gsd-core 1.16 rejects `config-set model_policy null` on the whole object.
    - Acceptance: tie fixtures resolve identically on reordered input. A leftover v1 `model_overrides.gsd-planner` becomes an unset entry. A no-catalog cursor plan lists `needs_choice` slots with 3 candidates each.

## Boundaries

**In scope:**
- `inventory` and `recommend` subcommands, plus the new modules: `host`, `catalog_adapter`, `roles`, `presets`, `plan_io`, `recommend`
- The plan.json schema and the inventory schema (both versioned)
- Rigor preset tables and role scoring
- Golden-plan fixtures (5 hosts × 3 rigors × adaptive, plus quality and budget spot checks)
- Instruction-file detection for `AGENTS.md` and `CLAUDE.md`

**Out of scope:**
- `plan-set`, `plan-unset` and `apply` — Phase 18 (APP-*)
- Cross-AI review lane and execution command selection — Phase 18 (XAI-01/02); `recommend` only reserves their slots from the two answers
- Skill-affinity mapping, plugin-skill discovery and per-skill host visibility — Phase 18 (SKL-01..04); Phase 17 lists the skill directories it finds
- The (runtime, model) schema change inside `ai_kit_spec` and `native_runtime` removal — Phase 18.1; Phase 17 derives pairs from the current catalog
- pi model enumeration (Phase 22) and the cursor wrapper (Phase 21)
- Removing v1 modules — kept by Phase 18 D-08

## Constraints

- Runtime code stays stdlib-only. Node is used only to read the host gsd-core's `.cjs` tables, as `gsd_catalog.query_agent_catalog` does today.
- All I/O lives in `inventory`; `recommend` has none (REC-01).
- The gsd-core tables are read from the resolved install, never copied into ai-kit.
- The real first run here is scored, but partly: R4's per-pick rule must keep unscored candidates out of automatic picks, and the fully unscored path must stay useful for machines without a key.

## Acceptance Criteria

- [ ] `inventory` on a read-only fixture project succeeds and leaves the project byte-identical
- [ ] The inventory reports the project-local gsd-core over a global one, and exits 2 with the searched paths when none exists
- [ ] The fresh, stale-with-warning and no-catalog states each appear in the inventory
- [ ] With an unscored catalog, the Claude/Codex plans set no `model_profile_overrides` value (Codex `op: keep` entries write nothing, D-18), and the opencode/cursor plans carry `needs_choice` with a `no scores` note
- [ ] Policy-in-project, policy-in-global without a project config, and a project-runtime mismatch are conflicts; an inert global policy and any global runtime are info only
- [ ] `AGENTS.md`-only, `CLAUDE.md`-only, both and neither are reported correctly
- [ ] Two `recommend` runs on the same inputs are byte-identical, and `recommend` succeeds with subprocess, socket, clock and extra file reads patched to raise
- [ ] `models.*` keys appear only where the rigor preset shifts a whole phase
- [ ] Native slots are kept when present and within the ceiling; `-fast` twins are never auto-chosen when the non-fast model exists; a declared-purpose router wins its slot
- [ ] No golden plan has more than 7 `model_overrides`; single-provider hosts carry the counterpart note
- [ ] Every spec §5 preset key and value matches per rigor
- [ ] A key unknown to the host gsd-core is dropped with a note
- [ ] Ties are order-independent; leftover managed keys become `op: unset`; `model_policy` is always proposed for unset
- [ ] MUST NOT: `recommend` performs no I/O beyond reading its input file
- [ ] MUST NOT: no plan entry claims a score-based choice (`source: catalog-score`) when the catalog has no scores

## Edge Coverage

**Coverage:** 40/46 applicable edges resolved · 6 unresolved (engine floor recomputed 2026-10-14 after the requirement amendments)

| Category | Requirement | Status | Resolution / Reason |
|----------|-------------|--------|---------------------|
| boundary | R1 | ✅ covered | The read-only project directory test |
| precision | R1 | 🧪 backstop | Prices keep catalog precision (no rounding before `recommend`) |
| adjacency | R2 | ✅ covered | A local and a global install never merge: the local one wins, with its `scope` recorded (R2 acceptance, D-11) |
| empty | R2 | ✅ covered | A missing gsd-core exits 2 and lists the searched paths (R2 acceptance) |
| ordering | R2 | ✅ covered | Installs are searched in GSD's launcher order, project-local first (16.1 D-18, D-11) |
| adjacency | R3 | ✅ covered | The three states never merge: each yields its own marker (R3 acceptance) |
| empty | R3 | ✅ covered | No catalog marks `catalog: none` (R3), and an empty or unscored catalog fills slots as none (R4) |
| ordering | R3 | ✅ covered | The refresh order is fixed: `detect-runtimes` before `fetch-model-catalog` (R3 target) |
| concurrency | R3 | ✅ covered | A failed refresh keeps the stale cache plus a warning (R3), and concurrent cache writes stay valid (16.1 R15) |
| boundary | R4 | ✅ covered | Zero score axes is never auto-picked except as a declared-purpose router, and one axis or more ranks with the 49/100 missing-axis default (R4, D-12) |
| precision | R4 | ✅ covered | With no scores anywhere, candidates are ordered by price ascending (unpriced last), then model id, within the rigor ceiling first, with `score: null` and `why: "no scores; ordered by price, not quality"` (17 D-25) |
| adjacency | R5 | ✅ covered | A project runtime equal to the host is no conflict, and a project and a global value never merge into one entry (R5) |
| empty | R5 | ✅ covered | With no project config on a claude host, a global `resolve_model_ids: "omit"` is a conflict with `effect: latent (copied into the project config by config-new-project)`, and `recommend` emits `op: unset` (17 D-31; verified live) |
| ordering | R5 | ✅ covered | Project config takes precedence: beside it, a global `model_policy` or `runtime` is inert `info` (R5) |
| concurrency | R5 | ✅ covered | Conflict detection only reads configs, and `inventory` writes nothing outside ai-kit's cache (R1) |
| empty | R6 | ✅ covered | The neither, `AGENTS.md`-only and `CLAUDE.md`-only fixtures pin the empty and single cases (R6 acceptance) |
| encoding | R6 | 🧪 backstop | Exact file names are checked with `isfile`, as `claude_md_detect` does today, so the filesystem decides case |
| concurrency | R6 | 🧪 backstop | Detection is read-only; concurrent inventories do not interfere |
| boundary | R7 | ✅ covered | `recommend` exits 2 on any inventory `schema_version` other than the supported one, older or newer, and tells the user to rerun `inventory` (17 D-31) |
| adjacency | R7 | ✅ covered | Reordered input candidates give an identical plan (tie test) |
| empty | R7 | ✅ covered | An inventory with zero candidates yields `needs_choice` entries, never a crash |
| ordering | R7 | ✅ covered | Plan entries are sorted by key for byte-stable output |
| precision | R7 | 🧪 backstop | The two-run byte-identical test pins number output, and comparisons use the unrounded `score_exact` (R13) |
| concurrency | R7 | ✅ covered | Pure runs share no state (R7), and a partial `plan.json` fails to load in `apply` (18 D-22) |
| adjacency | R8 | ✅ covered | Standard sets no `models.*` |
| empty | R8 | 🧪 backstop | Unknown profile name rejected with exit 2 |
| ordering | R8 | 🧪 backstop | `models.*` written after `model_profile` in plan order |
| boundary | R9 | ✅ covered | A price exactly at the ceiling counts as within |
| adjacency | R9 | ✅ covered | Effort variants collapse into one family for the percentile, and a `-fast` twin yields to its non-fast model (R9) |
| empty | R9 | ✅ covered | A cap that passes nothing uses the cheapest eligible model, and no eligible model gives `needs_choice` (R9, R13) |
| ordering | R9 | ✅ covered | Equal candidates for a slot follow R13's tie order: `score_exact`, then price, then model id |
| precision | R9 | 🧪 backstop | The percentile ceiling is computed over eligible prices only (unpriced excluded) |
| unclassified | R10 | ✅ covered | Classified from locked decisions: the cap of 7 is structural, no eligible model gives a note and never blocks (D-07), equal or unknown vendor is ineligible (D-14), picks follow the R13 tie key, and frontend-capable is defined in 17 D-28 |
| adjacency | R11 | ✅ covered | MVP ↔ Standard ↔ Rigorous tables differ only where §5 says |
| empty | R11 | 🧪 backstop | Unknown rigor rejected with exit 2 |
| ordering | R11 | 🧪 backstop | Preset keys merge before catalog-driven keys |
| adjacency | R12 | ✅ covered | One note per rejected key; the R12 acceptance was amended to 3 notes for Rigorous (17 D-26) |
| empty | R12 | ✅ covered | A failed `isValidConfigKey` probe (export missing or require failed) exits 2 like a missing gsd-core, naming the gsd-core path and version (17 D-31); the export exists in 1.12, 1.13, 1.16 and 1.17 |
| ordering | R12 | 🧪 backstop | The two-run byte-identical test (R7) pins the order of the drop notes |
| idempotency | R12 | ✅ covered | A rerun on the same inventory drops the same keys with the same notes (R7 byte-identical) |
| concurrency | R12 | ✅ covered | The key probe only reads the host gsd-core, and `inventory` writes nothing outside ai-kit's cache (R1) |
| boundary | R13 | ✅ covered | Exactly 3 candidates (fewer when fewer exist) |
| adjacency | R13 | ✅ covered | Equal score and price → model id decides |
| empty | R13 | ✅ covered | No existing config → no unset entries |
| ordering | R13 | ✅ covered | Tie order is independent of input order |
| precision | R13 | 🧪 backstop | Scores are compared at full precision, never rounded |

## Prohibitions (must-NOT)

**Coverage:** 3/3 applicable prohibitions resolved · 0 unresolved

| Prohibition (must-NOT statement) | Requirement | Status | Verification / Reason |
|----------------------------------|-------------|--------|------------------------|
| MUST NOT write to the project, its `.planning/` or any tool config during `inventory` or `recommend` | R1, R7 | resolved | test |
| MUST NOT present a price-only pick as a score-based recommendation (no `catalog-score` source without scores) | R4 | resolved | test |
| MUST NOT auto-select a `-fast` twin when its non-fast model exists | R9 | resolved | test |

## Ambiguity Report

| Dimension          | Score | Min  | Status | Notes |
|--------------------|-------|------|--------|-------|
| Goal Clarity       | 0.90  | 0.75 | ✓      | Two subcommands, one pure |
| Boundary Clarity   | 0.88  | 0.70 | ✓      | 18, 18.1, 21, 22 boundaries named |
| Constraint Clarity | 0.80  | 0.65 | ✓      | Purity, stdlib, unscored first run |
| Acceptance Criteria| 0.82  | 0.70 | ✓      | 15 pass/fail criteria |
| **Ambiguity**      | 0.14  | ≤0.20| ✓      | Initial 0.21; one auto round |

## Interview Log

`--auto`: the initial ambiguity was 0.21 (constraint and acceptance clarity were low after the facts changed since 2026-09-23), so one auto round ran. The open decisions went to jev-fast-decision: local Laya first, one item per call; `needs_fallback` items went to TypeSafe direct (`jev-latest` → `jev-1.13.0`). Summaries only, advisory. The existing 17-CONTEXT D-01..D-08 are kept as locked. Rule: best design over the smallest diff (`workflow.mvp_mode` unset).

| Round | Perspective | Question summary | Laya (advisory) | TypeSafe (advisory) | Decision locked |
|-------|-------------|------------------|-----------------|---------------------|-----------------|
| 1 | Researcher | What changed since the 2026-09-23 discussion? | – | – | gsd-core 1.16, GSD per repo, no AA key (corrected in discuss: a key is configured), `runtime: codex` in global defaults, 18.1 pairs, `AGENTS.md` (Background) |
| 1 | Failure Analyst | Catalog with prices but no scores? | no_scores_fallback p=0.83 | – | R4: treat as no catalog; never fake a ranking |
| 1 | Simplifier | Cursor `-fast` twins? | exclude_fast 0.55 (fb) | exclude_fast 1.00 | R9: excluded from auto-fill when the non-fast model exists |
| 1 | Boundary Keeper | Candidate shape, given 18.1? | pairs_now 0.68 (fb) | pairs_now 0.98 | R1: (runtime, model) pairs now |
| 1 | Boundary Keeper | Per-skill host visibility in the inventory? | defer p=0.79 | – | Deferred to Phase 18 (SKL-01 owns skill discovery) |
| 1 | Failure Analyst | Global `runtime: codex` vs the Claude host? | always_conflict p=0.84 | – | **Laya overridden:** gsd-tools ignores global keys when a project config exists, so a conflict there would overstate certainty (core value). R5: conflict only on effective mismatch, otherwise info |

---

*Phase: 17-curated-config-inventory-recommendation-engine*
*Spec created: 2026-10-14*
*Next step: /gsd-discuss-phase 17 — implementation decisions (how to build what's specified above)*
