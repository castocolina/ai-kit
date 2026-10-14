# Phase 17: Curated-Config Inventory & Recommendation Engine - Context

**Gathered:** 2026-09-23 (interactive); updated 2026-10-14 (assumptions mode, after `17-SPEC.md`)
**Status:** Ready for planning

<domain>
## Phase Boundary

The rewritten `skills/ai-kit-gsd-curated-config/` gains two parts that never write anything:
- `inventory --project-dir DIR [--refresh]` — a read-only JSON snapshot of the host, the host's
  gsd-core, models, skills, project facts, the existing config and conflicts;
- `recommend` — a pure function that turns that inventory plus profile, rigor and the two
  cross-AI answers into an explainable, minimal `plan.json`.

These are out of scope here and belong to Phase 18: plan adjustment (`plan-set`/`plan-unset`),
the cross-AI review/execution selection logic (XAI-*), skill-affinity mapping (SKL-02/03),
`apply`, and removing the old modules.

`recommend` may take the cross-AI answers as inputs and reserve the plan slots for them, but
Phase 18 owns the selection rules.

</domain>

<decisions>
## Implementation Decisions

### Carried forward (locked elsewhere — do not re-decide)
- **Approved spec:** `docs/superpowers/specs/2026-09-23-gsd-curated-config-v2-design.md` §3–§5
  and §8 set the architecture, the three model layers plus the execution override, the role
  profiles, the ≤7 specialist rules, and the rigor presets. Rigor also enables `intel.enabled`
  (Standard/Rigorous) and `dynamic_routing` (Rigorous).
- **Phase 16:**
  - host precedence pi > opencode > cursor > codex > claude;
  - `image_input` absent = unknown = not vision-eligible;
  - ranker purposes planning/general/mechanical/execution/review;
  - the mechanical purpose has a floor, and a missing floor axis means the model is excluded;
  - cache `schema_version` staleness;
  - the reasoning data lives in the existing `reasoning_modes` field;
  - cursor wrapper resolution and pi enumeration are deferred (Phases 21/22).
- **v1 (Phase 07):** D-01 — writes only through `gsd-tools`, which is Phase 18's concern.
  D-09 — merge mode: unmanaged keys are never touched. D-10 — coexists with `gsd-settings`.

### Layer 2: tier → model (`model_profile_overrides.<host>.<tier>`)
- **D-01:** **Claude host:** skip layer 2 unless the user pins a model, as the spec says.
  - gsd resolves claude tiers to aliases, which Claude Code maps to current models.
  - The stale `claude-opus-4-8` in gsd-core's `RUNTIME_PROFILE_MAP` never reaches the user.
- **D-02:** **Other hosts: keep the native slot only while it is valid.**
  - A native gsd-core `RUNTIME_PROFILE_MAP[host][tier]` slot is kept (no key written) when its
    model is in the host's enumerated model list **and** within the rigor price ceiling.
    `why` records: "kept gsd default: present on host, within ceiling".
  - Otherwise the slot gets an override with the best eligible model for that tier's role
    (opus = planning, sonnet = general, haiku = mechanical).
  - Expected results: codex's sol/terra/luna are mostly kept; opencode's `anthropic/*`
    defaults get overridden because they are not in the user's opencode model list.
  - There is no score-margin upgrade of valid native slots. The user can pin any slot via
    Phase 18's `plan-set`.
  - Read the native map from the **host's own** gsd-core (`model-catalog.cjs`
    `RUNTIME_PROFILE_MAP`), not a hardcoded copy.

### Price ceiling
- **D-03:** Rigor sets a **relative percentile cap** over the host's eligible models' prices.
  - The exact percentiles are Claude's discretion, around MVP ≈ 40th, Standard ≈ 75th,
    Rigorous uncapped.
  - A cap **never empties a slot**: when nothing passes, the cheapest eligible model is used
    and `why` says so.
  - The cap applies to slot filling (layer 2) and to the execution override, as spec §4 says.
- **D-04:** **User-curated router models are preferred for their declared role.**
  - A router (`is_router`) is typically unpriced (e.g. `router-env/*`). When its
    user-confirmed `name_declared_purpose` matches a slot's role, it **wins that slot**:
    `execute` → execution override; `review` → review/plan-checker counterpart slots in
    Phase 18.
  - Such routers are exempt from the price cap. `why` = "user-curated router (declared
    purpose: …)".
  - The user's own rationale: those models are already analyzed by the user.
  - Unpriced models that are **not** user-curated routers stay eligible and are scored with the
    ranker's missing-axis default; `why` notes "price unknown".

### Undecidable slots
- **D-05:** When `recommend` cannot decide a slot, it emits a **`needs_choice`** entry:
  `{key, value: null, status: "needs_choice", candidates: [top 3 with score + why], why}`.
  - Triggers: no catalog on cursor/opencode/pi (spec §4 per-slot fallback), or no eligible
    model for a required, non-specialist slot.
  - `apply` (Phase 18) must refuse while any `needs_choice` remains. The SKILL agent asks the
    user and resolves each one with `plan-set`.
- **D-06:** **Ties never need the user.** They are broken deterministically: score descending,
  then lower price, then model id ascending. This is required for REC-01's
  same-inputs-same-plan guarantee.
- **D-07:** **Specialists never block.** If no eligible model exists for a specialist (e.g. no
  `image_input` model for `gsd-ui-auditor`/`gsd-dom-verifier`), no override is written; a
  warning note records that the agent falls back to its tier.
  - The single-provider counterpart case (claude/codex, or one configured provider) gets the
    spec's explicit note pointing to cross-AI review, not a `needs_choice`.

### Existing config
- **D-08:** **Plan-managed key families are authoritative.**
  - The families are: `model_profile`, `models.*`, `model_overrides.*`,
    `model_profile_overrides.<host>.*`, `effort.*`, `dynamic_routing.*`, the rigor-preset
    workflow/gate keys, `review.*` and `agent_skills.*` (the last two are filled in Phase 18).
  - Existing entries inside those families that the plan does not set are proposed as
    `op: "unset"` entries with a `why` (e.g. a leftover v1 `model_overrides.gsd-planner` that
    would shadow the new tiers).
  - Keys outside the managed families are untouched (v1 D-09).
  - Every plan entry records the `existing` value, so the review pass shows an
    add/change/keep/remove diff. The user keeps anything via `plan-unset` in Phase 18.
  - A pre-existing `model_policy` (project config) is always proposed for removal, because it
    shadows layer 2 (spec §8).
  - One in `~/.gsd/defaults.json` is never edited. **Refined 2026-10-14 by live gsd-core 1.16
    behavior (D-10):** it is a conflict only when no project config exists; otherwise it is
    reported as inert `info`.
  - **Amended 2026-10-14:** the unset is emitted per leaf
    (`model_policy.provider|budget|high|medium|low`), because gsd-core 1.16 rejects
    `config-set model_policy null` on the whole object.
  - **Reversibility:** reversible — nothing is written in this phase; the removal only happens
    at Phase 18 `apply`, with a backup.

### Added 2026-10-14 (assumptions-mode discuss, jev-screened)
- **D-09: Valid keys are probed, not re-implemented.** `inventory` calls the host gsd-core's
  `isValidConfigKey` once per key in the closed set `recommend` can propose, and stores the
  accepted and rejected keys. The live check accepts 125 central keys, 16 dynamic patterns and
  86 capability-federated keys; dumping only the central set would reject valid capability
  keys. `recommend` reads the stored result (R12).
- **D-10: Conflicts follow verified gsd-tools behavior (R5, INV-03).**
  - With a project config present, gsd-tools ignores `~/.gsd/defaults.json` for resolution.
    Creating a project config copies the global `model_policy`, not `runtime`.
  - A project `model_policy` is a conflict. A global one is a conflict only when no project
    config exists; otherwise it is inert `info`.
  - A project `runtime` that differs from the host is a conflict. A global `runtime` is never
    one (an absent project runtime comes from env or an install marker), so it is `info`.
- **D-11: gsd-core scope is labelled.** Resolution follows GSD's own launcher order
  (`git rev-parse --show-toplevel`, then `.claude/gsd-core`, then global installs). The
  inventory records `scope: local|global`, and warns when it resolved global inside a worktree
  whose main checkout has a local install (they can differ in version).
- **D-12: Unscored is decided per pool and per pick (R4).** A candidate with zero score axes is
  never auto-picked; it appears only in `needs_choice` with a `no scores` tag. A partly scored
  candidate keeps the ranker's 49/100 missing-axis default. The only exception is a
  user-confirmed router winning by declared purpose (D-04). This refines D-04's last bullet:
  "price unknown" still applies to priced-unknown but scored models.
- **D-13: `fast_twin_of` lives in the catalog adapter.** It is computed once per inventory
  candidate and only read by `recommend`. Phase 18's `plan-set` reuses it to warn when the user
  pins a `-fast` twin.
- **D-14: Counterpart providers compare an inferred vendor, strictly.** The catalog provider is
  whichever reseller row matched (the same Claude model appears under anthropic, 302ai, venice
  and others), so it cannot be compared as-is. Vendor = id prefix, else catalog provider. A
  candidate whose vendor cannot be inferred is ineligible for the automatic plan-checker and
  code-reviewer counterpart pick; it can still be chosen with `plan-set`.
- **D-15: The ranker gains an unrounded `score_exact`.** The shared ranker rounds to 1 decimal
  and sorts by the rounded value, which breaks D-06's full-precision tie order. The field is
  additive and backward-compatible; existing callers keep the rounded `score`.
- **D-16: The price ceiling percentile is taken over model families.** Effort variants of one
  family share a price (cursor lists about 142 priced ids in about 37 families), so the sample
  collapses them. This keeps the cap tied to price spread, not to how many variants a vendor
  ships.
- **D-17: Only used tier slots are filled.** A tier slot is filled or asked about only when
  some agent resolves to it under the chosen profile, the rigor phase shifts and dynamic
  routing (Rigorous can escalate to the heavy tier). Budget never asks about opus; quality
  never asks about haiku.
- **D-18: Plan schema gains `op: keep` and `source: router-declared` (R7).**
  - `keep` writes nothing and carries the explanation of a kept gsd default (D-02), so Phase
    18's review diff can show it.
  - `router-declared` marks a D-04 router win.
  - Unsets of leftover keys use `source: preset`.
- **D-19: Cross-AI answers reserve placeholders.** When an answer is yes, the plan carries the
  boolean keys plus `needs_choice` placeholder entries for the reviewer list and the execution
  command, owned by Phase 18. `apply` therefore refuses until Phase 18 fills them. An omitted
  flag defaults from rigor and host and is recorded as `defaulted`.
- **D-20: Golden plans come from a shared tables builder.** One fixture file holds the gsd-core
  tables captured once; a small builder assembles each host inventory from trimmed real model
  lists (cursor, opencode, codex, claude). pi is synthetic and labelled so. The 15 golden plans
  regenerate with a flag; property tests (ordering, ties, purity) are separate.

- **D-21: `resolve_model_ids` is a managed key (added 2026-10-14 from the Phase 19 spec).**
  `config-new-project` copies `~/.gsd/defaults.json`, including the codex installer's
  `resolve_model_ids: "omit"`. A project-explicit `omit` on a claude host makes `resolve-model`
  return `model: ""` for every agent without a per-agent override, so the tier layer has no
  effect. On a claude host it is a conflict (R5) and is proposed for unset. On other hosts it is
  the installer's intended value and is left alone. jev: Laya manage_and_reconcile 0.49 (fb),
  TypeSafe 0.99.

- **D-22: pi-host plans claim no unverified effect (added 2026-10-14 from the Phase 22 spec).**
  gsd-core 1.16's registry gives pi no named dispatch (`namedDispatch: false`, `maxDepth: 0`,
  plugin-only install). Until Phase 22's spike proves an effect, a pi-host plan writes no
  per-agent `model_overrides`, and its model-layer entries carry
  `effect unverified on pi (gsd-core registry: namedDispatch false)`.
  - *(amended 2026-10-14, 22 D-02, D-05, D-06)* The expected verdict is session-steer, sonnet
    key only. `agent_skills.*` is labelled no-effect on pi too, and the only model write offered
    is an opt-in `model_profile_overrides.pi.sonnet` with a bare id of the session provider.

- **D-23: `runtime` is a managed key on opencode and codex (added 2026-10-14 from the Phase 20
  discussion).** The gsd-core installer bakes agent models from the project `runtime`, else
  `~/.gsd/defaults.json`'s, and ignores `GSD_RUNTIME`. With this machine's global
  `runtime: "codex"`, opencode agents would bake codex ids. `recommend` emits
  `runtime: <host>` (`source: preset`) on opencode and codex; codex tier entries carry
  `effect: resolve-model only (codex bakes only explicit model_overrides)`. Laya amend_both
  0.90.

### Claude's Discretion
- The exact percentile per rigor level.
- The plan.json schema details: top-level `schema_version`, inventory digest, and the entry
  field names beyond `key`/`value`/`why`/`source`/`status`/`existing`/`op`/`candidates`.
- The inventory's skill-scan depth and caching.
- Where the host → role → tier mapping tables live (`presets.py` / `roles.py` per spec §3).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Milestone spec and phase contracts
- `docs/superpowers/specs/2026-09-23-gsd-curated-config-v2-design.md`:
  - §2 — research facts: the resolver order and why `model_policy` shadows layer 2;
  - §3 — architecture and modules;
  - §4 — model assignment;
  - §5 — presets;
  - §8 — error handling.
- `.planning/REQUIREMENTS.md` — INV-01..03 and REC-01..06.
- `.planning/ROADMAP.md` — the Phase 17 success criteria.
- `.planning/phases/16-ai-kit-spec-extensions/16-CONTEXT.md` — detection, catalog fields,
  ranker purposes/floor and cache decisions this phase consumes.

### gsd-core (read from the host's own install; claude = `~/.claude/gsd-core`, v1.16.0 as of 2026-10-14)
- `bin/lib/model-catalog.cjs`:
  - `AGENT_TO_PHASE_TYPE` (35 agents / 6 phase types);
  - `MODEL_PROFILES` (per-agent tier per profile);
  - `RUNTIME_PROFILE_MAP` (native tier → model, used by D-02);
  - `CODEX_MODEL_EFFORT`;
  - `VALID_PROFILES` / `VALID_PHASE_TYPES`.
- `bin/lib/config-schema.cjs` — `isValidConfigKey` (1.16: 125 central keys, 16 dynamic
  patterns, 86 capability-federated keys). This is the source for REC-06 unknown-key dropping,
  probed per key (D-09).
- 1.16 shape traps found live: some exports are `Set`s and some plain objects, so the node
  query must serialize each explicitly. `RUNTIME_PROFILE_MAP.pi` is new in 1.16.
- `bin/lib/model-resolver.cjs` — `resolveModelInternal`, the resolution order.

### v1 decisions still in force
- `.planning/milestones/v1.1-phases/07-curated-gsd-config-skill/` (CONTEXT) — D-01, D-05, D-09,
  D-10.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/gsd_catalog.py`:
  - `GSD_CORE_ROOT_CANDIDATES` and `resolve_gsd_tools_path`, which must become host-first
    (spec §3 `host.py`);
  - `resolve_model_catalog_cjs_path`, `resolve_node_binary`;
  - `query_agent_catalog`, which already shells a node script against `model-catalog.cjs`.
    Extend it to pull `RUNTIME_PROFILE_MAP`, `MODEL_PROFILES` and `isValidConfigKey`.
- `frontend_detect.py` (`detect_frontend_present`) and `claude_md_detect.py` — project facts
  for INV-01.
- `model_detect.py` (`resolve_ai_kit_spec_path`, `detect_runtimes_snapshot`) — the bridge into
  `ai_kit_spec` for `catalog_adapter.py`.
- `ai_kit_spec` (after Phase 16): the `detect-current-runtime`, `detect-runtimes --if-stale` and
  `fetch-model-catalog --if-stale` CLIs; `score_candidates` with the new purposes and floor.
  It rounds scores to 1 decimal (D-15 adds `score_exact`).
- Phase 16.1 creates `ai_kit_spec/gsd_tools.py`, the shared gsd-tools resolver. It does not
  exist yet; Phase 17 consumes it rather than adding another copy.

### Established Patterns
- CLI subcommands emit JSON; subprocess calls take an injected `run_fn`; missing tools degrade
  to structured errors (exit 2 with the searched paths when no gsd-core exists).
- `recommend` purity (REC-01): no subprocess, network, clock or filesystem reads inside it.
  Everything it needs comes in through the inventory JSON, and `inventory` does all the I/O.

### Integration Points
- `gsd-core`'s `RUNTIME_PROFILE_MAP` has no `cursor` entry (`runtimeTierDefaults.cursor = null`).
  A cursor host with a catalog therefore always gets overrides; without one it gets
  `needs_choice` (D-05).
- The Phase 18 `apply` consumes `plan.json` (`needs_choice` gating, `op: unset`, `existing`
  diff).
- The Phase 19 `resolve-model` check for all 35 agents validates that D-02's "kept native slot"
  entries actually resolve as promised.

</code_context>

<specifics>
## Specific Ideas

- **Profile tier counts** in gsd-core 1.14 (35 agents):
  - quality: 22 opus / 13 sonnet;
  - balanced: 2 opus / 31 sonnet / 2 haiku;
  - budget: 12 sonnet / 23 haiku;
  - adaptive: 9 opus / 13 sonnet / 13 haiku.
  - Adaptive is the recommended default (spec §5).
- **The `execution` phase type** contains `debugger`, `doc-writer` and `debug-session-manager`
  next to `executor`/`code-fixer`. Never use `models.execution` for the execution role; use
  per-agent overrides (spec §4).
- **The user's opencode** lists 81 models (`opencode-go/*`, `router-env/*`). The routers
  `router-env/my-coding` and `router-env/my-plan-review` are the canonical D-04 examples.
- **Current machine state (2026-10-14):** an Artificial Analysis key is configured, and a
  live fetch scored 196 of 254 catalog entries. The real first run is scored but partial, so
  D-12's per-pick rule matters in practice. The no-catalog path (D-05) remains for other
  machines.
- **Live join coverage:** cursor 143 of 259 ids match the catalog; `composer-2.5` is
  unmatched. All 79 cursor `-fast` ids have a non-fast twin.
- **Live price percentiles** for codex: [0.2, 2, 4, 10] (per million tokens).
- **`claude_md_detect` already prefers `AGENTS.md`.** The stale value is this repo's
  `.planning/config.json` `claude_md_path: ./CLAUDE.md`; the inventory reports both the
  detected file and the stale config value.

</specifics>

<deferred>
## Deferred Ideas

- Visibility of skills per host belongs to Phase 18 (SKL-*); this phase only lists the skill
  directories it finds.
- The margin-based upgrade of valid native slots was rejected (D-02), not deferred.

</deferred>

---

*Phase: 17-curated-config-inventory-recommendation-engine*
*Context gathered: 2026-09-23; updated 2026-10-14*
