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
- **The catalog has prices but no scores.** There is no Artificial Analysis key on this machine, so the ranking is price-only and the mechanical purpose returns nothing by design (Phase 16 D-11).
- **Phase 18.1 will turn every model candidate into a (runtime, model) pair** and remove `native_runtime`.
- **The user measured Cursor's `-fast` twins at about 5× the token spend** and wants the non-fast variants (2026-10-13 todo, AGT-01).
- **`claude_md_detect.py` targets `./CLAUDE.md`.** This repo's instruction file is `AGENTS.md`, and the audit found `claude_md_path` pointing at a missing file.
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
   - Target: a catalog with no score axes counts as no catalog for slot filling.
     - Claude and Codex keep their native tier maps.
     - Cursor, opencode and pi get `needs_choice` entries whose candidates show prices and a `no scores` note.
   - Acceptance: with an unscored fixture catalog, the Claude and Codex plans contain no `model_profile_overrides`, and the opencode plan has a `needs_choice` per non-native slot with that note.

5. **Conflicts**: reported only when they change resolution.
   - Current: none.
   - Target:
     - `model_policy` in the project config, or in `~/.gsd/defaults.json`, is a conflict.
     - An effective runtime (project config first, then global defaults) that differs from the host is a conflict.
     - A global `runtime` that the project config overrides is listed under `info`, not `conflicts`.
   - Acceptance: fixtures for policy-in-project, policy-in-global, a project runtime mismatch, and a global runtime overridden by the project each yield the expected entry.

6. **Project facts**: the instruction file is found by its real name.
   - Current: `claude_md_detect` assumes `CLAUDE.md`.
   - Target: `project` reports `frontend`, `db`, `instruction_files` (which of `AGENTS.md` / `CLAUDE.md` exist) and `intel_index_present`.
   - Acceptance: fixtures with only `AGENTS.md`, only `CLAUDE.md`, both and neither report correctly. A frontend fixture and a DB fixture are detected.

7. **Pure, deterministic recommend**: same inputs, same bytes.
   - Current: none.
   - Target: `recommend --inventory --profile --rigor [--cross-ai-review y|n] [--cross-ai-exec y|n] --out plan.json` performs no subprocess, network, clock or filesystem read beyond its input file. Every entry carries `key`, `value`, `why`, `source` (`preset | catalog-score | curated-affinity | user | native`) and `existing`. The plan carries `schema_version` and the inventory digest.
   - Acceptance: two runs on the same inputs are byte-identical. A test patches `subprocess`, `socket`, `time` and `open` (except the input) to raise, and `recommend` still succeeds.

8. **Tier layer**: `model_profile` plus phase shifts only.
   - Current: v1 heavy sweep.
   - Target: `model_profile` is set (adaptive recommended). `models.<phase_type>` is set only where the rigor preset shifts a whole phase (MVP research/verification → haiku; Rigorous planning → opus, verification → sonnet).
   - Acceptance: golden plans for 3 rigors × adaptive show exactly those `models.*` keys.

9. **Tier → model layer**: overrides only where the native slot fails.
   - Current: none.
   - Target: `model_profile_overrides.<host>.<tier>` is written only when the native slot's model is missing from the host's candidates or is above the rigor price ceiling. Claude is skipped unless pinned. A router with a user-confirmed declared purpose wins its slot and is exempt from the ceiling. A `-fast` twin is excluded from automatic filling whenever its non-fast model exists.
   - Acceptance:
     - Golden plans for codex (native kept), opencode (`anthropic/*` replaced), and cursor (no native map, `-fast` never chosen, the user's router chosen for its role).
     - A cap test shows a slot is never emptied: when nothing passes, the cheapest eligible model is used with that `why`.

10. **Specialists**: at most 7 `model_overrides`.
    - Current: v1 critical agents.
    - Target:
      - `gsd-plan-checker` uses a provider other than the planning slot's;
      - `gsd-code-reviewer` uses a provider other than the execution model's;
      - `gsd-ui-auditor` and `gsd-dom-verifier` require `image_input`;
      - `gsd-ui-researcher` is frontend-capable, only when a frontend exists;
      - `gsd-executor` and `gsd-code-fixer` take the execution role with effort `medium`.

      A single-provider host gets the explicit "no in-runtime counterpart → use cross-AI review" note instead of an override. A specialist with no eligible model gets a warning, never a block.
    - Acceptance: golden plans never exceed 7 `model_overrides`. Single-provider fixtures (claude, codex) carry the note. A host with no `image_input` model carries the vision warning.

11. **Rigor presets**: data-only tables per spec §5.
    - Current: v1 fixed bundle.
    - Target: MVP, Standard and Rigorous set granularity, effort tiers, gates (nyquist, TDD, code-review depth, ASVS, UI review), `intel.enabled` (Standard, Rigorous), `dynamic_routing` (Rigorous) and `workflow.mvp_mode` (MVP), exactly as spec §5 lists.
    - Acceptance: a table-driven test asserts every §5 key and value per rigor.

12. **Unknown keys dropped**: the plan never proposes a key the host's gsd-core rejects.
    - Current: none.
    - Target: every candidate key is checked with the host gsd-core's `isValidConfigKey`. A rejected key is removed and a `notes` entry names it.
    - Acceptance: a fixture `valid_keys` without `dynamic_routing.*` gives a Rigorous plan with no such keys and one note.

13. **Undecidable slots and existing keys**: explicit, never silent.
    - Current: none.
    - Target:
      - An undecidable required slot becomes `{status: "needs_choice", value: null, candidates: top 3 with score/price/why}`.
      - Ties break by score descending, then price ascending, then model id ascending.
      - An existing key in a managed family that the plan does not set becomes `op: "unset"` with a `why`.
      - A project `model_policy` is always proposed for unset.
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
- Without an Artificial Analysis key the real first run is the unscored path (R4). It must be useful there, not only in fixtures.

## Acceptance Criteria

- [ ] `inventory` on a read-only fixture project succeeds and leaves the project byte-identical
- [ ] The inventory reports the project-local gsd-core over a global one, and exits 2 with the searched paths when none exists
- [ ] The fresh, stale-with-warning and no-catalog states each appear in the inventory
- [ ] With an unscored catalog, the Claude/Codex plans have no `model_profile_overrides`, and the opencode/cursor plans carry `needs_choice` with a `no scores` note
- [ ] Policy-in-project, policy-in-global and an effective-runtime mismatch are conflicts; a global runtime overridden by the project is info only
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

**Coverage:** 19/25 applicable edges resolved · 6 unresolved

| Category | Requirement | Status | Resolution / Reason |
|----------|-------------|--------|---------------------|
| boundary | R1 | ✅ covered | The read-only project directory test |
| precision | R1 | 🧪 backstop | Prices keep catalog precision (no rounding before `recommend`) |
| unclassified | R2 | ⚠ UNRESOLVED | No shape cue; planner treats local-vs-global version skew as an assumption |
| unclassified | R3 | ⚠ UNRESOLVED | No shape cue; the three states are specified in Acceptance |
| unclassified | R4 | ⚠ UNRESOLVED | No shape cue; unscored behavior is specified in Acceptance |
| unclassified | R5 | ⚠ UNRESOLVED | No shape cue; the four conflict fixtures are specified |
| concurrency | R6 | 🧪 backstop | Detection is read-only; concurrent inventories do not interfere |
| adjacency | R7 | ✅ covered | Reordered input candidates give an identical plan (tie test) |
| empty | R7 | ✅ covered | An inventory with zero candidates yields `needs_choice` entries, never a crash |
| ordering | R7 | ✅ covered | Plan entries are sorted by key for byte-stable output |
| adjacency | R8 | ✅ covered | Standard sets no `models.*` |
| empty | R8 | 🧪 backstop | Unknown profile name rejected with exit 2 |
| ordering | R8 | 🧪 backstop | `models.*` written after `model_profile` in plan order |
| boundary | R9 | ✅ covered | A price exactly at the ceiling counts as within |
| precision | R9 | 🧪 backstop | The percentile ceiling is computed over eligible prices only (unpriced excluded) |
| unclassified | R10 | ⚠ UNRESOLVED | No shape cue; the specialist rules are specified in Acceptance |
| adjacency | R11 | ✅ covered | MVP ↔ Standard ↔ Rigorous tables differ only where §5 says |
| empty | R11 | 🧪 backstop | Unknown rigor rejected with exit 2 |
| ordering | R11 | 🧪 backstop | Preset keys merge before catalog-driven keys |
| unclassified | R12 | ⚠ UNRESOLVED | No shape cue; the drop-with-note behavior is specified |
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
| 1 | Researcher | What changed since the 2026-09-23 discussion? | – | – | gsd-core 1.16, GSD per repo, no AA key, `runtime: codex` in global defaults, 18.1 pairs, `AGENTS.md` (Background) |
| 1 | Failure Analyst | Catalog with prices but no scores? | no_scores_fallback p=0.83 | – | R4: treat as no catalog; never fake a ranking |
| 1 | Simplifier | Cursor `-fast` twins? | exclude_fast 0.55 (fb) | exclude_fast 1.00 | R9: excluded from auto-fill when the non-fast model exists |
| 1 | Boundary Keeper | Candidate shape, given 18.1? | pairs_now 0.68 (fb) | pairs_now 0.98 | R1: (runtime, model) pairs now |
| 1 | Boundary Keeper | Per-skill host visibility in the inventory? | defer p=0.79 | – | Deferred to Phase 18 (SKL-01 owns skill discovery) |
| 1 | Failure Analyst | Global `runtime: codex` vs the Claude host? | always_conflict p=0.84 | – | **Laya overridden:** gsd-tools ignores global keys when a project config exists, so a conflict there would overstate certainty (core value). R5: conflict only on effective mismatch, otherwise info |

---

*Phase: 17-curated-config-inventory-recommendation-engine*
*Spec created: 2026-10-14*
*Next step: /gsd-discuss-phase 17 — implementation decisions (how to build what's specified above)*
