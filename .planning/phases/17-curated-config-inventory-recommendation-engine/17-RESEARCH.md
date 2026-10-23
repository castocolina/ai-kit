# Phase 17: Curated-Config Inventory & Recommendation Engine - Research

**Researched:** 2026-10-15
**Domain:** Python stdlib CLI (read-only host/project inventory + pure recommendation engine) over the host gsd-core 1.16 `.cjs` tables and ai-kit's shared `ai_kit_spec` catalog/ranker
**Confidence:** HIGH for gsd-core behavior and existing code (live-probed in scratch projects this session); MEDIUM for the opencode 2.x probe shape (spike plus one re-probe); open product questions are flagged below

## Summary

Phase 17 adds two new subcommands to `skills/ai-kit-gsd-curated-config/` and leaves the v1 CLI as it is. `inventory` does all the I/O. It resolves the project-local gsd-core, makes one `node` call that reads the tables and probes `isValidConfigKey`, refreshes the ai-kit catalog cache through the `ai-kit-spec.py` subprocesses, and reads project facts and existing config. `recommend` is a pure function from that JSON to a sorted, byte-stable `plan.json`. Everything it needs comes from existing modules: the shared resolver `ai_kit_spec/gsd_tools.py`, the ranker `model_ranker.score_candidates`, `detection.group_models_by_family`, `vendor.infer_vendor_from_model`, `cache.cache_write_text` (atomic since 16.1), and the v1 detectors `frontend_detect` and `claude_md_detect`. The phase adds no third-party package.

Live probes this session settled all six open SPEC edges (see "Open Questions Resolution") and turned up five facts the planner must design around:
1. **Effort variants.** Cursor's effort-variant ids are separate catalog entries with different Artificial Analysis scores at the same per-token price. A naive score pick therefore always chooses the `-max`/`-xhigh` variant, even for the haiku/mechanical slot.
2. **Unconfirmed routers.** Neither live router (`router-env/my-coding`, `router-env/my-plan-review`) is user-confirmed (`heuristic_confirmed` is absent), so D-04's router win does not fire on this machine until the user confirms them.
3. **`dynamic_routing` has no model effect.** With the spec §5 keys and no `tier_models`, `resolve-model --attempt 1` returned the same model as attempt 0 on every case probed (opencode with and without `tier_models`, claude with `tier_models`).
4. **Global `defaults.json` is read only with no `.planning/`.** gsd-core reads it only when the project has no `.planning/` at all (Branch D), and it honors `GSD_HOME`.
5. **Ranker reads a file.** `score_candidates` needs weights that `load_ranking_weights` reads from a TOML file. Scoring must therefore happen in `inventory`, not in `recommend`, to keep REC-01 purity.

**Primary recommendation:** Build `inventory` as one I/O orchestrator (`host.py`, extended `gsd_catalog.py`, `catalog_adapter.py`, `project_facts.py`). It emits pre-scored (runtime, model) candidates with `score_exact` per purpose, `fast_twin_of`, `family`, `vendor` and `router_confirmed`. Build `recommend` as pure functions over that JSON (`roles.py`, `presets.py`, `recommend.py`, `plan_io.py`) with a single canonical-JSON writer. Choose effort variants by family plus tier effort, never by raw score.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Host detection, gsd-core resolution, scope label | CLI I/O layer (`host.py`) | `ai_kit_spec` (`detect_current_runtime`, `gsd_tools.resolve_gsd_tools`) | Reuses the shared resolver (16.1 D-18); never a second copy |
| gsd-core tables + valid-key probe | Host gsd-core (node subprocess) | `gsd_catalog.py` (the caller) | Tables are read from the install the project uses, never copied (R2) |
| Catalog refresh (fresh/stale/none) | `ai_kit_spec` CLI subprocesses (own cache) | `catalog_adapter.py` | Only `ai-kit-spec.py` writes `~/.cache/ai-kit/spec`, atomically |
| opencode 2.x `image_input` | `ai_kit_spec/detection.py` (detect-runtimes) | — | Capability enumeration belongs to the runtimes snapshot, not the curated-config skill |
| Candidate pairs, `fast_twin_of`, family, vendor, purpose scores | `catalog_adapter.py` (inside inventory) | `model_ranker`, `vendor`, `detection.group_models_by_family` | Scoring reads a weights file, so it must stay out of pure `recommend` |
| Project facts, existing config, conflicts | CLI I/O layer (`project_facts.py`, inventory) | `gsd-tools config-path` | Read-only; workstream-aware config path |
| Plan construction (layers, ceiling, specialists, unsets, key drop) | Pure engine (`recommend.py`, `roles.py`, `presets.py`) | — | REC-01: no subprocess/network/clock/filesystem |
| Plan serialization + digest | `plan_io.py` | `cache.cache_write_text` pattern for `--out` | One canonical writer gives byte-identical output |

## Project Constraints (from AGENTS.md / CLAUDE.md)

- English only in every artifact. Runtime code is **stdlib-only**. Node is allowed only to read the host gsd-core `.cjs` tables (SPEC Constraints).
- Every config write is atomic (`tempfile.mkstemp()` + `os.replace()`). Phase 17 writes no runtime config at all. Its only writes are ai-kit's own cache (through `ai-kit-spec.py`) and the `recommend --out` file.
- Never present a detection result with more certainty than its source has. Inferred classifications (vendor, family, router purpose, frontend, db) are labelled.
- Never hardcode an absolute machine path in source, tests or fixtures. Golden fixtures use placeholder paths.
- A new or materially changed `SKILL.md` must pass `/skill-judge`. **Phase 18 owns the SKILL.md v2 flow and the README row (18-SPEC R15).** Phase 17 should not touch SKILL.md, which avoids that loop.
- Use logical commits with tests and docs together. Never use `--no-verify`. Never run destructive git commands.
- `make test` (four runner tiers) and `make validate` must be green. A new `tests/test_*.py` joins the `unit` group automatically, but the generated listings must be refreshed with `python3 tools/gen_test_groups.py` (`tests/test_gate_scope.py::test_generated_listings_name_every_discovered_module`).
- pylint limits: `max-args=5`, `max-locals=15`, `max-branches=12`, `max-returns=6`, `max-statements=50`. Bundle injected deps in a `NamedTuple` (as `ai_kit_spec.cli.CliDeps` does) and split `recommend` into small functions.
- `tests/test_arch.py` rule 8 forbids `shell=True` in `ai-kit-spec-*` skills, and rule 9 allows a broad-except suppression only in the listed backstops. Catch specific exceptions only.
- Never use the real `~/.claude`, `~/.cursor`, `~/.config/opencode`, `~/.codex`, `~/.pi` or `~/.gsd` as fixtures. Use a temp HOME/XDG/`GSD_HOME`.
- Kill any spawned process (the opencode 2.x probe server) in `finally`.
- Plans must be portable for cheap cross-AI execution: path-agnostic commands, no machine paths.
- v1 modules and subcommands stay intact (Phase 18 D-08). v2 tests go in new test modules, never the v1 test file (18 D-15 pattern).

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Carried forward (locked elsewhere — do not re-decide)
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

#### Layer 2: tier → model (`model_profile_overrides.<host>.<tier>`)
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

#### Price ceiling
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

#### Undecidable slots
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

#### Existing config
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

#### Added 2026-10-14 (assumptions-mode discuss, jev-screened)
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

- **D-24: Restore the opencode `image_input` source on opencode 2.x (added 2026-10-15, live
  finding at Phase 16 close-out).** Live on opencode v2.0.29: `opencode models --verbose` is gone
  (`opencode models [--standalone | --server <url>]`), and `opencode serve` now starts "the v2 API
  and web server". The 16-05 parser therefore gets no input and fails closed, so every
  opencode-only model reads as unknown, which means not vision-eligible. Before planning, run a
  spike (theory → hypothesis → spike):
  - run opencode under a scratch HOME/XDG, never the real `~/.config/opencode`;
  - find which 2.x surface (the v2 API behind `serve`/`--standalone`, or the `models` output)
    exposes per-model input modalities, and record the exact command or endpoint, the version, and
    a captured sample;
  - kill every server it starts.

  If a surface exists, Phase 17 adds a version-gated parser next to `parse_opencode_verbose_image_input`
  (keeping the 1.x path) with `image_input_source` provenance. If none does, models.dev
  `modalities.input` stays the only source and the gap is labelled `unverified on opencode 2.x`,
  never inferred. Either way, `skills/ai-kit-spec-config/references/cli-model-selection.md:159` stops
  citing `--verbose` as current. The carried-forward fail-closed rule means nothing waits on this.
  - *(spike done 2026-10-15, `17-SPIKE-opencode-image-input.md`)* First branch: `GET /api/model` on
    the v2 API (`opencode serve`, basic auth `opencode:<printed token>`) returns
    `capabilities.input`; `"image" in input` means vision-capable.

### Claude's Discretion
- The exact percentile per rigor level.
- The plan.json schema details: top-level `schema_version`, inventory digest, and the entry
  field names beyond `key`/`value`/`why`/`source`/`status`/`existing`/`op`/`candidates`.
- The inventory's skill-scan depth and caching.
- Where the host → role → tier mapping tables live (`presets.py` / `roles.py` per spec §3).

### Deferred Ideas (OUT OF SCOPE)
- Visibility of skills per host belongs to Phase 18 (SKL-*); this phase only lists the skill
  directories it finds.
- The margin-based upgrade of valid native slots was rejected (D-02), not deferred.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| INV-01 | `inventory --project-dir` emits one JSON: host, host gsd-core (path/version/valid keys), (runtime, model) candidates (scores, price, `image_input`, reasoning levels), skills, project facts (frontend, db, `AGENTS.md`/`CLAUDE.md`, intel index), existing config, conflicts | §Architecture "Inventory schema"; node query + probe (verified live); project facts sources; candidate pair join (runtimes.json ∪ catalog) |
| INV-02 | Catalog from `~/.cache/ai-kit/spec`, refreshed `--if-stale`; stale cache + warning on failed refresh; no cache → native maps (claude/codex) or per-slot asks (cursor/opencode/pi); prices-without-scores takes the same path | §"Catalog freshness state machine" (fetch-model-catalog's printed `models_dev_ok`/`artificial_analysis_ok`/`fetch_skipped`); R4 per-pick rule |
| INV-03 | Conflicts only when they change resolution | §"Conflict matrix" (live: global defaults read only with no `.planning/`; config-new-project copies `model_policy` + `resolve_model_ids`, not `runtime`) |
| REC-01 | Pure function; every entry has `key`, `value`, `why`, `source` | §"Purity boundary" (scoring moved to inventory; canonical JSON writer; purity test skeleton) |
| REC-02 | `model_profile` + `models.<phase>` only for rigor phase shifts | §"Presets table"; tier counts verified on 1.16 |
| REC-03 | `model_profile_overrides.<host>.<tier>` by role score under ceiling; claude skip; codex `{model, reasoning_effort}`; cursor effort-suffixed; `-fast` excluded | §"Slot filling algorithm", §"Effort-variant selection" (live pitfall), nearest-rank percentile over families |
| REC-04 | ≤7 specialist overrides with counterpart/vision/frontend/execution rules; single-provider note | §"Specialist rules" (all 7 agents verified in 1.16 tables) |
| REC-05 | MVP/Standard/Rigorous presets per spec §5 | §"Presets table" (keys verified valid via live `isValidConfigKey`; `code_quality.fallow.profile` enum verified) |
| REC-06 | Unknown keys dropped with a note | §"Valid-key probe" (per key with `cwd`; `intel.enabled` and `refactor.trigger_enabled` are capability-only keys) |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python stdlib (`json`, `hashlib`, `subprocess`, `os`, `math`, `urllib.request`, `base64`, `argparse`, `typing.NamedTuple`) | system python3 3.14.7 (unit tier); uv env pins `>=3.12,<3.13` | All runtime code | AGENTS.md: runtime is stdlib-only [VERIFIED: pyproject.toml:9 `requires-python = ">=3.12,<3.13"`] |
| node | v24.21.0 | Reads `model-catalog.cjs` / `config-schema.cjs` of the resolved gsd-core | The only way to read the host's own tables (SPEC Constraints) [VERIFIED: `node --version`] |
| gsd-core (project-local) | 1.16.0 (`.claude/gsd-core/VERSION`); 1.17.0 published with identical tier tables | Source of tables + `isValidConfigKey` | R2 [VERIFIED: VERSION file; `pnpm view @opengsd/gsd-core versions`; 1.16 vs 1.17 `runtimeTierDefaults` byte-equal, 35 agents both] |
| `ai_kit_spec` (sibling skill) | in-repo | `gsd_tools` resolver, `model_ranker`, `detection`, `vendor`, `cache`, `model_catalog` | Shared single sources of truth (16.1 D-18, AGENTS.md Architecture) |

### Supporting (in-repo reuse — do not re-implement)
| Module / symbol | Purpose | When to Use |
|---|---|---|
| `ai_kit_spec.gsd_tools.resolve_gsd_tools`, `gsd_core_roots`, `project_root`, `gsd_core_version`, `config_path` | project-local-first resolution, scope label, version, workstream-aware config path | host.py |
| `ai_kit_spec.detection.detect_current_runtime` | host label (`pi`/`opencode`/`cursor`/`codex`/`claude`/`unknown`) | host.py |
| `ai_kit_spec.detection.group_models_by_family` | family collapse (D-16, effort-variant choice) | catalog_adapter.py |
| `ai_kit_spec.vendor.infer_vendor_from_model` | vendor inference (D-14) | catalog_adapter.py |
| `ai_kit_spec.model_ranker.load_ranking_weights`, `score_candidates` | per-purpose scoring (+ new `score_exact`, D-15) | catalog_adapter.py **only** (never recommend) |
| `ai_kit_spec.model_catalog.split_catalog_meta`, `cache_catalog_path`; `detection.cache_runtimes_path`; `cache.cache_read_json` | read the ai-kit cache, skipping `_meta` | catalog_adapter.py |
| `ai_kit_spec.cache.cache_write_text` | atomic `--out` write pattern (mkstemp + `os.replace`) | plan_io.py |
| `gsd_catalog.load_gsd_tools`, `resolve_node_binary`, `resolve_model_catalog_cjs_path` | sibling import shim + node resolution | gsd_catalog.py extension |
| `frontend_detect.detect_frontend_present`, `claude_md_detect.detect_claude_md_path` | project facts | project_facts.py |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Scoring in `inventory` (stored `score_exact` per purpose) | Scoring inside `recommend` | `load_ranking_weights` opens `references/ranking-weights.toml`, which is a filesystem read inside `recommend` and breaks REC-01. Embedding the weights in the inventory would also work but couples the plan to ranker internals. **Use inventory-side scoring.** |
| Nearest-rank percentile (hand-written, about 3 lines) | `statistics.quantiles` | `quantiles` interpolates, so the ceiling may match no real price, and "a price exactly at the ceiling counts as within" (R9 edge) becomes fuzzy. Nearest-rank always returns an actual family price. |
| opencode 2.x `GET /api/model` via a temporary `opencode serve --port 0` | `opencode models --server <url>` against the user's running `serve --service` | Both were observed. `--server` prints bare ids only (spike), so it carries no capabilities. Use the temporary server. |

**Installation:** none. No third-party packages.

## Package Legitimacy Audit

Not applicable. This phase installs no external packages (stdlib, node and the in-repo `ai_kit_spec` only).

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### System Architecture Diagram

```
                ┌───────────────────── inventory --project-dir DIR [--refresh] ─────────────────────┐
 env (HOST signals, HOME/XDG/GSD_HOME)                                                                 │
   │                                                                                                    │
   ├─► host.py ── detect_current_runtime ──► host label ──(unknown → exit 2 unless --host)              │
   │        └── gsd_tools.resolve_gsd_tools(start=DIR) ──► gsd-tools.cjs path ──(none → exit 2 + paths)│
   │                 └── scope = local|global (+ worktree warning, D-11)                                │
   │                                                                                                    │
   ├─► gsd_catalog.query_gsd_tables(node, lib dir, cwd=DIR, keys=CLOSED_KEY_SET)  ── ONE node call ──►  │
   │        RUNTIME_PROFILE_MAP, MODEL_PROFILES, AGENT_TO_PHASE_TYPE, AGENT_DEFAULT_TIERS,              │
   │        VALID_PROFILES, VALID_PHASE_TYPES, CODEX_MODEL_EFFORT, valid_keys{accepted,rejected}        │
   │        (probe/require failure → exit 2, see OQ6)                                                  │
   │                                                                                                    │
   ├─► catalog_adapter: python ai-kit-spec.py detect-runtimes --if-stale <runtimes.json>                │
   │                    python ai-kit-spec.py fetch-model-catalog --if-stale ... --cwd DIR             │
   │        (writes ONLY ~/.cache/ai-kit/spec, atomically)                                              │
   │        ──► catalog state: fresh | stale(+warning) | none ; scored? (R4)                            │
   │        ──► candidates = enumerated (runtime, model) pairs ⋈ catalog entries                        │
   │              + is_host, vendor, family, fast_twin_of, router_confirmed, purpose_scores{score_exact} │
   │                                                                                                    │
   ├─► project_facts: frontend, db, instruction_files, intel_index_present, skills dirs                 │
   ├─► existing config: gsd-tools config-path --cwd DIR → read JSON (read-only)                         │
   │                    $GSD_HOME|~ /.gsd/defaults.json (read-only)                                     │
   └─► conflicts / info (D-10, D-21, live Branch C/D)                                                    │
                                    │                                                                   │
                                    ▼  inventory.json (schema_version, …)  stdout or --out              │
└───────────────────────────────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
 recommend --inventory F --profile P --rigor R [--cross-ai-review y|n] [--cross-ai-exec y|n] --out plan.json
   (pure: reads F once; refuses unsupported schema_version → exit 2)
   presets[R] ─► gate/workflow/effort/intel/dynamic_routing entries
   roles: profile + phase shifts ─► used tiers (D-17) ─► layer 1 entries (model_profile, models.*)
   layer 2: per used tier: claude→skip | native kept (op keep) | override (ceiling, -fast excluded,
            family+tier-effort variant, router-declared) | needs_choice (no scores / no eligible)
   layer 3: ≤7 specialists vs their resolved slot model (counterpart vendor, vision, frontend, execution)
   cross-AI answers ─► boolean keys + needs_choice placeholders (D-19)
   existing managed-family keys not set ─► op unset (model_policy per actual leaf)
   valid_keys.rejected ─► drop + notes
   ─► plan_io.dump_canonical ─► plan.json (sorted entries, schema_version, inventory_digest)
```

### Recommended Project Structure
```
skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/
├── cli.py               # + "inventory" and "recommend" handlers in _COMMAND_HANDLERS (v1 handlers untouched)
├── host.py              # NEW: host label, gsd-core resolution + scope label + worktree warning
├── gsd_catalog.py       # EXTEND: query_gsd_tables() (one node call: tables + isValidConfigKey probe)
├── catalog_adapter.py   # NEW: refresh state machine, candidate pairs, family/vendor/fast twin, purpose scores
├── project_facts.py     # NEW: instruction_files, db, intel_index_present, skills dirs (reuses v1 detectors)
├── inventory.py         # NEW: orchestrates the above, builds conflicts/info, inventory schema_version
├── roles.py             # NEW (data + pure): tier↔purpose map, specialist rules, effort ladder helpers
├── presets.py           # NEW (data only): rigor tables per spec §5, percentiles, closed key set
├── recommend.py         # NEW (pure): layers 1-3, ceiling, needs_choice, unsets, key drop, cross-AI slots
└── plan_io.py           # NEW: plan schema_version, canonical dump, inventory digest, atomic --out write
skills/ai-kit-spec-review/ai_kit_spec/
├── model_ranker.py      # EDIT: add score_exact (D-15)
├── detection.py         # EDIT: opencode 2.x /api/model image_input source (D-24); RUNTIMES_SCHEMA_VERSION 2→3
└── model_catalog.py     # (no change if "opencode" source label reused — see Pattern 6)
skills/ai-kit-spec-config/references/cli-model-selection.md   # EDIT line 159 (D-24)
tests/
├── test_curated_config_inventory.py   # NEW (unit): host, node query, catalog states, conflicts, facts, read-only
├── test_curated_config_recommend.py   # NEW (unit): purity, ties, ceiling, specialists, unsets, key drop, presets
├── test_curated_config_golden.py      # NEW (unit): 15 goldens + spot checks via the tables builder (D-20)
└── fixtures/curated_config_v2/        # NEW: gsd_tables_1_16.json, trimmed model lists, golden plans
```

### Pattern 1: One node call for tables and the key probe (R2, R12, D-09)
**What:** Extend `gsd_catalog` with a second `-e` script. It `require`s `model-catalog.cjs` and `config-schema.cjs` by argv path (never interpolated), serializes the `Set` exports explicitly, and probes each key with `isValidConfigKey(key, cwd)`.
**When to use:** Once per `inventory`.
**Verified facts:**
- `isValidConfigKey(keyPath, cwd)` exists in 1.12.0, 1.13.0, 1.16.0 and 1.17.0. [VERIFIED: grep of the published tarballs; installed 1.16 `config-schema.cjs` `function isValidConfigKey(keyPath, cwd)`]
- `cwd` matters: without it, `_capabilityConfigSchema` falls back to the first-party capability schema only, and project-installed capabilities are missed. [VERIFIED: `.claude/gsd-core/bin/lib/config-schema.cjs` `_capabilityConfigSchema(cwd)`]
- `intel.enabled` and `refactor.trigger_enabled` are not in `VALID_CONFIG_KEYS` (central) but are valid capability keys. A central-only dump would wrongly drop REC-05's intel key. [VERIFIED: live node probe, `central has: ... intel.enabled=false ... refactor.trigger_enabled=false`, while `isValidConfigKey` returned `true` for both]
- `model_policy` (the whole object) → `false`; each leaf `model_policy.provider|budget|high|medium|low` → `true`. `code_quality.fallow.mode` → `false`, `live_dom_uat` (top level) → `false`, `workflow.live_dom_uat` → `true`. [VERIFIED: live probe in a scratch project, project tree unchanged]
- The probe left the scratch project byte-identical (file list diff empty). [VERIFIED: before/after `find` diff]
- Shape traps: `VALID_PHASE_TYPES`, `VALID_AGENT_TIERS`, `VALID_TIERS` and the `CODEX_MODEL_EFFORT` values are `Set`s; `DYNAMIC_KEY_PATTERNS` items are objects `{topLevel, source, description, test}`. [VERIFIED: live dump]
- `VALID_PROFILES` in 1.16 is `[ 'quality', 'balanced', 'budget', 'adaptive', 'inherit' ]`. The `recommend --profile` choices must stay the 4 spec profiles (`VALID_MODEL_PROFILES = ("quality", "balanced", "budget", "adaptive")`, `cli.py:23`). [VERIFIED: live dump; cli.py:23]

```javascript
// Source: pattern of gsd_catalog._AGENT_CATALOG_QUERY_SCRIPT (argv paths, catch → 'null')
// argv: [1]=model-catalog.cjs path, [2]=config-schema.cjs path, [3]=project cwd, [4]=JSON array of keys
try {
  const m = require(process.argv[1]); const cs = require(process.argv[2]);
  const keys = JSON.parse(process.argv[4]); const cwd = process.argv[3];
  const setMap = (o) => Object.fromEntries(Object.entries(o).map(([k, v]) => [k, [...v]]));
  const accepted = keys.filter((k) => cs.isValidConfigKey(k, cwd));
  process.stdout.write(JSON.stringify({
    runtimeProfileMap: m.RUNTIME_PROFILE_MAP, modelProfiles: m.MODEL_PROFILES,
    agentToPhaseType: m.AGENT_TO_PHASE_TYPE, agentDefaultTiers: m.AGENT_DEFAULT_TIERS,
    validProfiles: m.VALID_PROFILES, validPhaseTypes: [...m.VALID_PHASE_TYPES],
    codexModelEffort: setMap(m.CODEX_MODEL_EFFORT),
    validKeys: { accepted, rejected: keys.filter((k) => !accepted.includes(k)) },
  }));
} catch (e) { process.stdout.write('null'); }
```
Pass the keys as one argv JSON string. Probe dynamic-family keys with concrete instances, for example `model_overrides.gsd-executor` and `model_profile_overrides.<host>.opus`. Build the closed key set in `presets.py` from the host, the 35 agents and the spec §5 tables.

### Pattern 2: Catalog freshness state machine (R3, INV-02)
- `detect-runtimes --if-stale PATH` prints `{}` and exits 0 when the cache is fresh. Otherwise it re-detects and saves to PATH. [VERIFIED: `ai_kit_spec/cli.py` `_cmd_detect_runtimes`]
- `fetch-model-catalog --runtimes-json R --catalog-path C [--if-stale] --cwd DIR` always rewrites C (atomically). It prints `{"models_dev_ok", "artificial_analysis_ok", "fetch_skipped", "entry_count", ...}`. [VERIFIED: `_write_fetch_catalog_result`]
- State rules:
  - `fresh` when `fetch_skipped` is true, or when either source is ok.
  - `stale` when a fetch was attempted, both sources failed, or the subprocess errored or timed out, AND the catalog file has at least one entry. Add a warning.
  - `none` when there is no file or no entries.
  - `scored` is true when at least one entry has an intelligence, coding or agentic score.
  - If `artificial_analysis_ok` is false while `models_dev_ok` is true, the state is still fresh, plus the warning "scores from cache".
- `--refresh`: run `detect-runtimes --save PATH` (not `--if-stale`) and `fetch-model-catalog` without `--if-stale`.
- Pass `env=` explicitly to every subprocess (the v1 `detect_runtimes_snapshot` inherits the env, which makes tests leak). Use `sys.executable` as the interpreter and a timeout (for example 120 s for the fetch).
- Concurrency: `cache_write_text` uses a per-writer `tempfile.mkstemp(dir=parent, suffix=".tmp")` then `os.replace(tmp, path)`. [VERIFIED: `ai_kit_spec/cache.py:34`, `:38`] This satisfies the R3 concurrency edge after 16.1.

### Pattern 3: Candidate pairs (INV-01)
- **Pairs = the union** of each installed CLI's enumerated `runtimes.json` `clis.<cli>.models` and catalog entries joined on `runtimes.<cli>.model_id`. Enumerated-but-unmatched ids (live: cursor 259 enumerated vs 143 catalog joins; `composer-2.5` unmatched) stay as candidates with no scores and no price. D-02's presence check uses the enumerated list, not the catalog. [VERIFIED: live cache `runtimes.json` / `model-catalog.json`]
- Host label to CLI name: `cursor` ↔ `cursor-agent`. `KNOWN_CLIS = ("claude", "codex", "opencode", "grok", "cursor-agent")` (`detection.py:20`). pi is not in `KNOWN_CLIS`, so a pi host has zero enumerated host candidates (pi enumeration is Phase 22; goldens use a synthetic pi list, D-20). The gsd-core key namespace uses `cursor` (`model_profile_overrides.cursor.*`). [VERIFIED: detection.py:20; live probe]
- `fast_twin_of`: the id ends with `-fast` and `id[:-5]` is enumerated in the **same** runtime list. -fast twins exist on cursor (79) **and opencode** (e.g. `openai/gpt-5.5-fast`). [VERIFIED: live runtimes.json]
- `family`: `group_models_by_family` strips the trailing tokens `("thinking", "low", "medium", "high", "xhigh", "max", "none", "fast")` [VERIFIED: `vendor.py:11` `_MODEL_TIER_SUFFIXES`]. Example: `claude-opus-5-thinking-high` and `claude-opus-5-high` share the family `claude-opus-5`.
- `vendor` (D-14): try `infer_vendor_from_model(full_id)`, then `infer_vendor_from_model(bare id after the last "/")`, then the catalog provider. **A router (`is_router: true`) gets `vendor: null`.** Its backends are unknown, so it must never count as a different vendor for the counterpart pick. This is a recommendation and is [ASSUMED] beyond D-14's text. The prefix table includes `("claude-", "anthropic")`, `("gpt-", "openai")`, `("glm-", "zhipu")`, `("kimi-", "moonshot")`, `("gemini-", "google")`, `("composer-", "cursor")`, `("opencode-go/kimi", "moonshot")` [VERIFIED: `vendor.py:20-32`]. There is no `openai/` or `anthropic/` prefix entry, so opencode `openai/...` ids reach the catalog provider. The bare-id step catches `opencode-go/glm-...`.
- `router_confirmed` = `is_router is True and "is_router" in heuristic_confirmed and name_declared_purpose in {"review", "execute"}` (`_VALID_NAME_DECLARED_PURPOSE = {"review", "execute"}`, `model_catalog.py:48`). **Live:** both routers lack `heuristic_confirmed`, so they read as unconfirmed (see Pitfall 2).
- `purpose_scores`: `{purpose: {"score_exact": float, "score": float}}` for each purpose in `CANONICAL_PURPOSES = ("planning", "general", "mechanical", "execution", "review")` (`model_ranker.py:18`). Compute once over all candidate catalog entries (one normalization pool, documented in the inventory). A candidate excluded by the mechanical floor (`"mechanical": {... "floor": {"coding_index": 35}}`, `model_ranker.py:32-34`) has no `mechanical` score, so it is not mechanical-eligible.
- `score_axes` = the count of non-null `scores.{intelligence_index, coding_index, agentic_index}`. Zero means `no scores` (D-12).
- Keep prices at catalog precision (R1 precision edge): `pricing.input_per_1m` is the price axis the ranker uses (`model_ranker.py:206`).

### Pattern 4: Slot filling (layer 2, REC-03) and the price ceiling (D-03, D-16)
1. Used tiers (D-17): for each agent, the tier is `models[phase]` (the preset shift) when set, else `MODEL_PROFILES[agent][profile]`. Used = the set of those tiers. Escalation adds nothing (see OQ-extra 3).
2. Claude host: emit no layer-2 entries (D-01).
3. For each used tier `t` on a non-claude host, with role `opus→planning`, `sonnet→general`, `haiku→mechanical`:
   - The **eligible** pool is host candidates with a score for the role, `score_axes > 0`, not a `-fast` twin whose base is enumerated, and not a router unless router-confirmed for that role.
   - Ceiling: take one price per family (the min input price among the family's priced members) over the eligible pool, then nearest-rank: `ceil = sorted_prices[max(0, math.ceil(q * n) - 1)]`. Use q = 0.40 for MVP, 0.75 for Standard, none for Rigorous. "At ceiling" counts as within.
   - **Native kept:** `RUNTIME_PROFILE_MAP[host][t].model` is in the host's enumerated list AND (price ≤ ceiling OR price unknown) → emit `op: keep`, `source: native`, with `why: "kept gsd default: present on host, within ceiling"`.
   - Else pick from the in-ceiling pool by tie key `(-score_exact, price, id)`. If the pool is empty, use the cheapest eligible model with that `why` (D-03). If nothing is eligible (or the catalog is none/unscored on cursor/opencode/pi) → `needs_choice`. On codex/claude without scores the native map is kept (R4).
   - Codex value `{"model": id, "reasoning_effort": e}`, where `e` is the native tier's effort (`codex.opus xhigh`, `sonnet medium`, `haiku medium` [VERIFIED: live `RUNTIME_PROFILE_MAP` dump]) clamped to the model's `reasoning_modes`. config-set accepted this object and resolve-model returned the model. [VERIFIED: live scratch `config-set model_profile_overrides.codex.opus '{"model":"gpt-6.1-sol","reasoning_effort":"high"}'` → `"updated": true`; `resolve-model gsd-planner` → `"model":"gpt-6.1-sol"`]
   - Codex entries also carry `effect: resolve-model only (codex bakes only explicit model_overrides)` (D-23). pi entries carry the D-22 label.
4. Live expectations:
   - codex: native `gpt-5.6-sol`/`terra`/`luna` are enumerated (codex also lists `gpt-6.1-sol`, `gpt-6-astra`, `gpt-6-sol`, `gpt-6-luna`), so a native slot is kept unless above the ceiling.
   - opencode: no `anthropic/*` id is enumerated (0 found), so all used slots are overridden or `needs_choice`.
   - cursor: `RUNTIME_PROFILE_MAP` has no `cursor` key (its tier entries are null and filtered out), so the slot is always an override or `needs_choice`. [VERIFIED: live dump, cache files]

### Pattern 5: Effort-variant selection (live finding, REC-03 "Cursor effort-suffixed ids")
The live catalog stores each cursor effort variant as its own entry, with a reseller provider and **its own AA score at the same per-token price**. Examples: `openai/gpt-5.6-sol-low` intelligence 33.5, `-high` 42.3, `-xhigh` 44, `-max` 47, all at `input_per_1m: 4`. `anthropic/claude-opus-5-5-low` 42.3 vs `-xhigh` 56, both at 4. [VERIFIED: live `model-catalog.json`] A raw `(-score_exact, price, id)` pick therefore always selects the highest-effort variant, mechanical slot included, which multiplies token spend. That is the same economics that made `-fast` twins excluded. **Recommendation:** rank **families**. For each family, take the variant whose effort token matches the tier's rigor effort (`effort.routing_tier_defaults`: heavy, standard or light from the preset; executor `medium`). Fall back to the nearest lower level on gsd's ladder `['minimal', 'low', 'medium', 'high', 'xhigh', 'max', 'ultra']` (`EFFORT_LADDER`, `.claude/gsd-core/bin/lib/model-catalog.cjs:134`), then nearest higher, then the bare id. Score the family by that chosen variant. The `why` names the effort rule. This is [ASSUMED]: a design choice that needs user confirmation (A3).

### Pattern 6: opencode 2.x `image_input` source (D-24)
- Version gate: `opencode --version` → `opencode v2.0.29` [VERIFIED]. Major ≥ 2 uses the API path; otherwise the existing 1.x `parse_opencode_verbose_image_input` path (`detection.py:266`, run by `detect_opencode_image_input` at `detection.py:325`) is unchanged.
- Start `[binary, "serve", "--hostname", "127.0.0.1", "--port", "0"]` with `stdout=PIPE`. **`--port 0` works and prints the chosen port.** Its stdout lines are `server listening on http://127.0.0.1:<port>` and `server password <token>`. [VERIFIED: live in a scratch HOME/XDG this session, token redacted]
- `GET /api/model` with HTTP basic auth `opencode:<token>` (Bearer → 401). It returns `{"location": ..., "data": [Model.Info]}`. `"image" in capabilities.input` means vision-capable. The key is `f"{providerID}/{id}"`. [CITED: 17-SPIKE-opencode-image-input.md]
- A `try/finally` must `terminate()`, then `wait(timeout)`, then `kill()`. Never log the token. Read stdout with a deadline (for example 15 s). Catch specific exceptions only (`OSError`, `subprocess.TimeoutExpired`, `urllib.error.URLError`, `TimeoutError`, `ValueError`). Arch rule 9 allows no broad except here.
- **Do not touch the user's running `opencode serve --service`** (a long-lived background process exists on this machine). Start your own server, kill only your own PID, and never `pkill opencode`.
- Side effect: `opencode serve` creates `opencode.db`, `log/` and `repos/` in opencode's XDG data dir, and `opencode models` (already run by detect-runtimes) creates `log/` and `repos/` too. [VERIFIED: scratch XDG listing] This is opencode's own data dir, not config. State it in the module docstring (Open Question 4).
- Provenance: reuse `image_input_source: "opencode"`. `_VALID_IMAGE_INPUT_SOURCE = {"models_dev", "opencode"}` (`model_catalog.py:49`) means CLI-reported, and the runtime-meta path already writes `"opencode"` (`catalog_build.py:269`). This avoids a schema change. Record the opencode version in the runtimes snapshot entry if you want finer provenance.
- Bump `RUNTIMES_SCHEMA_VERSION = 2` (`detection.py:16`) to 3. Without the bump, a cached 30-day `runtimes.json` (live: opencode entry has no `image_input`) is never re-detected. Update the tests that pin `2` (`tests/test_ai_kit_spec.py:2220`, `:2265`).
- Fix `skills/ai-kit-spec-config/references/cli-model-selection.md:159`, which still cites "image capability from `opencode models --verbose`" (D-24). Since that is a reference file, not SKILL.md, the skill-judge loop is not triggered (state this in the plan).

### Pattern 7: Purity boundary and canonical output (REC-01, R7)
```python
# plan_io.py — one writer for byte-stable output
import hashlib, json
PLAN_SCHEMA_VERSION = 1
SUPPORTED_INVENTORY_SCHEMA = 1

def canonical_json(obj) -> str:
    return json.dumps(obj, sort_keys=True, indent=2, ensure_ascii=False) + "\n"

def inventory_digest(inventory: dict) -> str:
    compact = json.dumps(inventory, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return "sha256:" + hashlib.sha256(compact.encode("utf-8")).hexdigest()
```
- Entries are sorted by `key`. `"model_profile"` sorts before `"models.research"` because `_` (0x5F) < `s` (0x73), which satisfies the R8 ordering backstop. Notes are sorted by `(kind, key, text)`.
- `recommend.build_plan(inventory: dict, opts: RecommendOpts) -> dict` must not import `model_ranker` or any I/O module. The CLI handler reads the file and writes `--out` atomically (mkstemp + `os.replace`, the `cache_write_text` pattern).
- Purity test: after loading the input, patch `subprocess.run`, `subprocess.Popen`, `socket.socket`, `time.time`, `time.monotonic`, `datetime.datetime` and `builtins.open` to raise, then call `build_plan` twice and compare `canonical_json` output byte for byte. The SPEC says "open (except the input)", so the patched `open` passes through only the inventory path, or the test calls the pure function directly.

### Pattern 8: Conflict matrix (R5, INV-03), live-verified
| Situation | Live behavior (gsd-core 1.16, scratch HOME) | Inventory entry |
|---|---|---|
| project `model_policy` | shadows layer 2 (spec §2) | conflict; plan unsets **each leaf actually present** |
| global `model_policy`, no project config | read at resolution when `.planning/` is absent (warning printed); copied by `config-new-project` | conflict (`scope: global`) |
| global `model_policy`, project config present | ignored, warning `#3532` | info (inert) |
| project `resolve_model_ids: "omit"`, claude host | `resolve-model` → `"model": ""` | conflict; plan unsets (D-21) |
| global `resolve_model_ids: "omit"`, no project config, claude host | **not** applied now (`"model": "opus"`), but **copied** by `config-new-project`, then `"model": ""` | conflict, `effect: latent (copied on config creation)`; see OQ3 |
| project `runtime` ≠ host | changes the tier map | conflict |
| global `runtime` | **not** copied by `config-new-project` (`runtime: None` after creation) | info |

[VERIFIED: live scratch runs this session. Copy check output: `{'resolve_model_ids': 'omit', 'runtime': None, 'model_policy': {...}}`]
- The global file path is `$GSD_HOME/.gsd/defaults.json`, else `~/.gsd/defaults.json`: `const home = process.env['GSD_HOME'] || node_os_1.default.homedir();` (`config-loader.cjs:1000-1001`). The inventory must honor `GSD_HOME`.
- gsd-core reads the global file at resolution **only when `.planning/` does not exist** (Branch D). With `.planning/` present but no `config.json` (Branch C), builtin defaults apply. [VERIFIED: `config-loader.cjs:986-1003`] The conflict classification (D-10) is the same in both cases, because Phase 18 `apply` runs `config-new-project`, which copies the file either way. Report `planning_dir_present` so the `why` text is accurate.
- `model_policy` leaves also include the dynamic pattern `^model_policy\.runtime_tiers\.[a-zA-Z0-9_-]+\.(opus|sonnet|haiku)$` [VERIFIED: live `DYNAMIC_KEY_PATTERNS` dump]. **Unset the leaves found in the existing object** (flatten it), not a fixed list of 5.

### Pattern 9: Presets table (spec §5, REC-05), key validity verified
| Key | MVP | Standard | Rigorous |
|---|---|---|---|
| `granularity` | coarse | standard | fine |
| `workflow.mvp_mode` | true | (unset) | (unset) |
| `models.research` / `models.verification` | haiku / haiku | — | — / sonnet |
| `models.planning` | — | — | opus |
| `effort.routing_tier_defaults.heavy/standard/light` | high / medium / minimal | xhigh / high / low | xhigh / high / low |
| `effort.agent_overrides.gsd-executor`, `.gsd-code-fixer` | medium | medium | medium |
| `effort.agent_overrides.gsd-code-reviewer` | — | — | xhigh |
| `workflow.research/plan_check/verifier/pattern_mapper` | true | true | true |
| `workflow.nyquist_validation` | false | true | true |
| `workflow.tdd_mode` | false | false | true |
| `workflow.code_review_depth` | quick | standard | deep |
| `workflow.security_asvs_level` / `security_block_on` | 1 / critical | 1 / high | 2 / medium |
| `workflow.ui_phase` | = frontend | = frontend | = frontend |
| `workflow.ui_review` | false | = frontend | true |
| `intel.enabled` | false | true | true |
| `plan_review.source_grounding_authority` | — | — | `intel` when the index exists |
| `workflow.plan_review_convergence` | false | from cross-AI answer | true |
| `code_quality.fallow.enabled` / `.profile` | false / — | — | true / standard |
| `refactor.trigger_enabled` | — | — | true |
| `dynamic_routing.enabled/escalate_on_failure/max_escalations` | — | — | true / true / 1 |

- Valid values: `code_quality.fallow.profile` accepts `['minimal', 'standard', 'strict']` (`VALID_FALLOW_PROFILES`, `config.cjs:997`), so §5's "(standard)" means `profile: standard`. `workflow.code_review_depth` takes `["quick","standard","deep"]` and `workflow.security_block_on` takes `["critical","high","medium","low","none"]`. [VERIFIED: live capability schema dump]
- gsd defaults: `effort.routing_tier_defaults` light `low`, standard `high`, heavy `xhigh` [VERIFIED: `config-defaults.manifest.json`]. Writing the Standard values explicitly keeps R11's table test simple and makes the managed-family authority unambiguous (discretion).
- Rigorous `workflow.live_dom_uat` requires "frontend and a browser MCP exist". The inventory has no browser-MCP detector, so see Open Question 2.

### Pattern 10: Specialist rules (layer 3, REC-04 / R10)
Specialist agents and their 1.16 adaptive tiers [VERIFIED: live dump]:
- `gsd-plan-checker`: haiku (verification, light)
- `gsd-code-reviewer`: sonnet
- `gsd-ui-auditor`: haiku
- `gsd-dom-verifier`: haiku
- `gsd-ui-researcher`: sonnet (research)
- `gsd-executor`: sonnet (execution)
- `gsd-code-fixer`: sonnet (execution)

Rules:
- Each specialist is compared against **its own resolved slot model** (layer 1 + 2 result). An override is emitted only when that slot fails the rule (spec §4 "only when the slot fails the rule"). This structurally caps overrides at 7.
- `gsd-plan-checker`: vendor ≠ the vendor of **gsd-planner's resolved model** (under the budget profile the planner is sonnet, not opus). Purpose `review`.
- `gsd-code-reviewer`: vendor ≠ the vendor of the resolved executor model (after its override). Purpose `review`.
- `gsd-ui-auditor`, `gsd-dom-verifier`: need `image_input is True`. Purpose `general`. If none qualifies, emit a warning note (D-07).
- `gsd-ui-researcher`: only when `project.frontend`. "Frontend-capable" is **undefined** (Open Question 1).
- `gsd-executor`, `gsd-code-fixer`: execution role under the ceiling. A confirmed router with `execute` wins (D-04). Effort `medium` goes through `effort.agent_overrides`.
- Claude host: `model_overrides` values are aliases (`opus`/`sonnet`/`haiku`/`fable`). gsd maps full Claude ids to aliases via `mapClaudeOverrideForRuntime` and falls through on unmappable ids [VERIFIED: `model-resolver.cjs:501-509`]. Writing aliases avoids the fall-through. [ASSUMED: the alias-by-family mapping (`claude-haiku-*` → haiku)]
- pi host: no `model_overrides` at all (D-22).
- Single-provider host (claude, codex, or a host whose vendor set has size 1) → counterpart note, no override.

### Anti-Patterns to Avoid
- **Hardcoding gsd-core tables or the valid-key set:** read them from the resolved install (R2, D-09). 1.17 is already published.
- **Scoring inside `recommend`:** `load_ranking_weights` opens a TOML file, which breaks purity.
- **Choosing among effort variants by raw score:** this always picks max effort (Pattern 5).
- **Comparing the catalog `provider` for counterparts:** the provider is reseller noise (`302ai/`, `requesty/`, `venice/` rows for the same models, live).
- **A fixed 5-leaf `model_policy` unset:** `runtime_tiers.*` leaves exist.
- **Inheriting the process env in subprocesses:** tests would hit the real cache and HOME.
- **Asserting live counts (196/254, 143/259, 81 models) in tests:** they drifted already (live today: 195 entries, 150 scored). Use the fixtures.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| gsd-tools location | a new candidate list | `ai_kit_spec.gsd_tools.resolve_gsd_tools` / `gsd_core_roots` | 16.1 D-18 single resolver; drift test pins it |
| Valid config keys | a key list or regex copy | host `isValidConfigKey(key, cwd)` probe | capability keys are federated per project (D-09) |
| Host detection | env parsing | `detection.detect_current_runtime` | fixed precedence + certainty labels live there |
| Model families | a suffix regex | `detection.group_models_by_family` | the same tokens as `_MODEL_TIER_SUFFIXES` |
| Vendor | a prefix table | `vendor.infer_vendor_from_model` | one table; unknown → `None` |
| Scoring | weighted sums | `model_ranker.score_candidates` + `score_exact` | 49-default and floor semantics (16 D-11) |
| Cache refresh / atomic writes | your own fetch or JSON writes | `ai-kit-spec.py detect-runtimes` / `fetch-model-catalog`; `cache_write_text` | TTL + `schema_version` + mkstemp rules |
| Frontend / instruction file | new scans | `frontend_detect`, `claude_md_detect` (`_CANDIDATE_FILENAMES = ("AGENTS.md", "CLAUDE.local.md", "AGENTS.local.md", "CLAUDE.md")`, `claude_md_detect.py:12`) | already tested; R6 only adds reporting of both files |
| JSON canonicalization | ad hoc ordering | `json.dumps(sort_keys=True, ...)` | byte-identical runs |

**Key insight:** almost every input already has a tested single source in `ai_kit_spec` or gsd-core. The new code is orchestration (inventory) and decision tables (recommend). Bugs will hide in duplicated logic, so don't duplicate any.

## Common Pitfalls

### Pitfall 1: Effort-variant explosion picks max effort everywhere
**What goes wrong:** the haiku/mechanical slot gets `gpt-5.6-luna-max` and the planning slot gets `claude-opus-5-5-max`.
**Why it happens:** each variant is a separate catalog entry with a higher AA score at the same per-token price (live data above).
**How to avoid:** use the family plus tier-effort variant rule (Pattern 5). Add golden assertions that no mechanical slot carries a `-max`/`-xhigh` suffix.
**Warning signs:** chosen cursor ids end in `-max`.

### Pitfall 2: The router exception never fires live
**What goes wrong:** the golden "cursor/opencode: the user's router chosen for its role" passes in fixtures, but on this machine `router-env/my-coding` is never chosen.
**Why it happens:** confirmation is recorded only in `heuristic_confirmed` (written by `apply-heuristic-correction`). Both live routers have none.
**How to avoid:** the inventory exposes `router_confirmed`. When a router has a declared purpose but is unconfirmed, the plan adds a note: "confirm via ai-kit-spec-config to let it win its slot".
**Warning signs:** `name_declared_purpose` is set and `heuristic_confirmed` is missing.

### Pitfall 3: The vendor of a router or reseller row
**What goes wrong:** `router-env` counts as a "different vendor", so the plan-checker counterpart lands on a router that may route back to the planner's vendor.
**How to avoid:** routers get `vendor: null`, which makes them ineligible for the automatic counterpart pick (strict D-14).

### Pitfall 4: Purity broken by imports
**What goes wrong:** `recommend` imports `model_ranker`, or reads `ranking-weights.toml`, a clock or the env. The purity test fails, or worse, passes because `open` was patched too late.
**How to avoid:** `recommend.py` imports only `json`-free pure helpers (`roles`, `presets`, `plan_io` pure functions). Add an arch-style unit test asserting by AST that `recommend.py`, `roles.py` and `presets.py` import none of `subprocess`, `socket`, `time`, `os`, `urllib` or `ai_kit_spec`.

### Pitfall 5: Leaking real HOME, cache or GSD_HOME into tests
**What goes wrong:** inventory tests read `~/.cache/ai-kit/spec` or `~/.gsd/defaults.json`. This machine's real global defaults set `runtime: codex` and `resolve_model_ids` (the gsd-tools warning printed during research).
**How to avoid:** every inventory entrypoint takes `env_fn`. Subprocesses get `env=`. Tests set temp `HOME`, `XDG_CACHE_HOME` and `GSD_HOME`, and use `RUNTIME_DIR` only for the resolver (the `_RealGsdTestCase` pattern).

### Pitfall 6: Golden fixtures with machine paths
**What goes wrong:** captured inventories embed the checkout's absolute `gsd_core.path`.
**How to avoid:** the tables builder (D-20) writes placeholder paths (for example `<project>/.claude/gsd-core`). The digest is computed on the fixture as stored.

### Pitfall 7: The opencode probe orphans a server or prints the token
**How to avoid:** use `try/finally` with terminate, wait and kill. Test with a fake `Popen` that records `terminate`/`kill` calls. Never include the token in errors. Never kill a PID you did not start (the user runs `opencode serve --service`).

### Pitfall 8: New test module not in the generated listings
**What goes wrong:** `test_gate_scope` fails with "stale listing".
**How to avoid:** run `python3 tools/gen_test_groups.py` after adding the `tests/test_curated_config_*.py` modules, and commit the Makefile and hook config changes it makes.

### Pitfall 9: Treating `dynamic_routing` as a slot user
**What goes wrong:** D-17's "Rigorous can escalate to the heavy tier" leads to filling or asking about extra slots, or to claiming escalation works.
**Live:** with `{enabled: true, escalate_on_failure: true, max_escalations: 1}`, `resolve-model gsd-executor --attempt 1` returned the same model and effort as attempt 0 on opencode (with and without `tier_models`). On claude with `tier_models` it was also unchanged, and `tier_models[standard]` replaced the tier alias even at attempt 0. Under Rigorous, `models.planning: opus` and `models.verification: sonnet` already make opus and sonnet used, so escalation adds no tier in any profile. [VERIFIED: live scratch runs; `model-resolver.cjs` `dynamicRoutingModel` returns `null` without `tier_models`]
**How to avoid:** compute used tiers from profile plus shifts only, and add a property test that "escalation adds no tier under Rigorous". The `why` on `dynamic_routing.*` must not claim a model escalation; label it "effect unverified (no tier_models; resolve-model --attempt unchanged in 1.16)". Never write `tier_models` in Phase 17.

### Pitfall 10: `recommend --out` inside the project
**What goes wrong:** the SPEC says "nothing written to the project", but `--out` is user-chosen.
**How to avoid:** write `--out` atomically. The SKILL flow (Phase 18) should default it outside `.planning/`. Phase 17 only documents this; the inventory read-only test covers `inventory`.

## Code Examples

### Nearest-rank ceiling over families (D-03, D-16, R9 boundary)
```python
import math

def price_ceiling(family_prices: list[float], q: float | None) -> float | None:
    """Nearest-rank percentile; None means uncapped (Rigorous) or no priced family."""
    if q is None or not family_prices:
        return None
    ordered = sorted(family_prices)
    return ordered[max(0, math.ceil(q * len(ordered)) - 1)]
# codex example family prices [0.2, 2, 4, 10] (17-CONTEXT specifics): q=0.40 -> 2, q=0.75 -> 4
```

### Deterministic tie key (D-06, R13)
```python
def tie_key(c: dict, purpose: str):
    price = c.get("price")
    return (-c["purpose_scores"][purpose]["score_exact"],
            price if price is not None else float("inf"),
            c["model"])
```

### Ranker `score_exact` (D-15), additive
```python
# model_ranker._score_one_entry (model_ranker.py:249-250 today: score = min(100.0, base + bonus);
# return {**entry, "score": round(score, 1)})
    score = min(100.0, base + bonus)
    return {**entry, "score": round(score, 1), "score_exact": score}
# leave score_candidates' sort (model_ranker.py:277, key=lambda e: e["score"]) unchanged for existing callers
```

### Plan entry shapes (D-05, D-18, R7)
```json
{"key": "model_profile_overrides.opencode.opus", "op": "set", "value": "<host id>",
 "source": "catalog-score", "why": "best planning score within ceiling (≤ $X/1M, 75th pct of N families)",
 "existing": null}
{"key": "model_profile_overrides.codex.sonnet", "op": "keep", "value": null, "source": "native",
 "why": "kept gsd default: present on host, within ceiling", "existing": null,
 "effect": "resolve-model only (codex bakes only explicit model_overrides)"}
{"key": "model_profile_overrides.cursor.haiku", "op": "set", "value": null, "status": "needs_choice",
 "source": "catalog-score", "why": "no scored candidate",
 "candidates": [{"model": "...", "score": null, "price": 0.5, "why": "no scores"}], "existing": null}
{"key": "model_policy.provider", "op": "unset", "value": null, "source": "preset",
 "why": "project model_policy shadows model_profile_overrides (resolver step 2.5)", "existing": "generic"}
```
In a `needs_choice` whose candidates are unscored, do **not** use `source: catalog-score`. Use `source: preset` or a dedicated `"no-catalog"` reason (the MUST NOT in the SPEC). Planner: pin the exact `source` for `needs_choice` within the enum `preset | catalog-score | curated-affinity | router-declared | user | native`. The recommendation is `preset`, with `why` carrying `no scores`.

## Open Questions Resolution (the six SPEC edges) (RESOLVED — see 17-CONTEXT D-25..D-31)

1. **R10 edge row "unclassified"**
   - Evidence: this is an edge-floor engine artifact ("No shape cue"). The R10 rules are concrete, so classify the edges from locked decisions:
     - boundary: the cap of 7 is structural (exactly 7 named specialists; Pattern 10);
     - empty: no eligible model → warning note, never a block (D-07);
     - adjacency: equal vendor or unknown vendor → ineligible (D-14), and single-provider → note (D-07);
     - ordering: picks follow the R13 tie key.
   - **Resolved, no product decision.** One genuine gap remains inside R10: "frontend-capable" (Open Question 1).
2. **R4 precision: ordering when no candidate has scores**
   - Evidence:
     - With zero score axes for everyone, the ranker maps intelligence/coding/agentic to `None` → 49.0 (`_MISSING_AXIS_DEFAULT = 49.0`, `model_ranker.py:49`). Order is then driven by the price, context-window, speed and tool-calling axes, which is a price-shaped "score" R4 forbids presenting.
     - For `mechanical`, the floor excludes every unscored candidate, so the ranker returns **nothing** and could not even fill 3 candidates.
   - **Product decision with a recommendation.** Options:
     - (A) price ascending, unpriced last, then model id;
     - (B) the ranker's 49-default order;
     - (C) model id only.
   - **Recommend (A).** It is deterministic, it makes no quality claim, and it works for every role including mechanical. Restrict to candidates within the rigor ceiling first, falling back to all. Show `score: null` and `why: "no scores; ordered by price, not quality"`. The SKILL agent can show the full list from the inventory.
3. **R5 empty: global `resolve_model_ids` — omit or emit?**
   - Evidence: with no project config, a global `"omit"` does **not** change claude resolution today (`"model": "opus"`). `config-new-project` copies it, and claude resolution then becomes `"model": ""`. Codex was unaffected in both cases (`gpt-5.6-sol`). [VERIFIED: live scratch run]
   - Phase 18 apply step 4 reconciles copied global keys against the plan (18-SPEC R13 / 18-CONTEXT D-22).
   - **Recommend: emit.** Report it as a conflict on a claude host only when no project config exists, mirroring the global `model_policy` rule, with `effect: "latent: copied into the project config by config-new-project"`. `recommend` emits the same `op: unset` entry as for a project omit (`existing: null`, `why` naming the copy), which gives Phase 18's reconcile its instruction.
   - With a project config present, the global value is `info` (inert). On non-claude hosts it is never a conflict (D-21).
4. **R7: inventory with an unsupported `schema_version`**
   - Evidence: the project precedent is that a missing or older cache `schema_version` counts as stale and is regenerated, never consumed (`runtimes_schema_is_current`, `catalog_schema_is_current`). `recommend` is pure and cannot regenerate. Phase 18 `plan-set` also consumes the inventory and checks its digest (18 D-17).
   - **Recommend: refuse with exit 2** for any `schema_version` other than the supported integer (older **or** newer). Print a one-line message: "inventory schema_version X unsupported (expected Y); rerun `inventory`". Use the same check in Phase 18's loaders. This is within Claude's discretion (plan/inventory schema details), not a product decision.
5. **R12 adjacency: "a notes entry naming it" (per key) vs "one note" (acceptance)**
   - Evidence: Rigorous proposes 3 `dynamic_routing.*` keys, so per-key notes give 3 and the two SPEC sentences contradict.
   - **Product wording decision.** Options:
     - (A) one note per rejected key; amend the acceptance to "3 notes";
     - (B) one note per rejected key family (first segment) that names every dropped key, sorted. This satisfies both sentences literally.
   - **Recommend (B)** and amend the SPEC R12 text to say so explicitly. It is less noisy and still names each key.
6. **R12 empty: the `isValidConfigKey` probe is missing on the installed gsd-core**
   - Evidence: `isValidConfigKey(keyPath, cwd)` exists in every version that matters (1.12.0, 1.13.0, 1.16.0, 1.17.0). [VERIFIED: tarball grep + installed source] A "missing probe" therefore means a pre-1.12 install, a broken install, or a node failure.
   - Without the probe, R12's guarantee ("never proposes a key the host gsd-core rejects") cannot hold. An empty accepted set would drop everything, and skipping the check would let rejected keys through. Phase 18 D-18 relies on the same probe.
   - **Recommend: exit 2**, like a missing gsd-core. Name the gsd-core path and version and say "isValidConfigKey unavailable (require failed or export missing)". The node script's `null` output (Pattern 1) is the single signal for both causes. Not a product decision.

### Additional open questions found during research (RESOLVED — frontend-capable: D-28; live_dom_uat: D-29; runtime mismatch: D-30, an info note only, not an unset; probe side effects: D-32; OQ5 note granularity: D-26, one note per key)

1. **"Frontend-capable" for `gsd-ui-researcher` (R10/REC-04) is undefined.** No catalog field exists, and spec §4 says only "best frontend-capable model".
   - Recommend `image_input is True` (reads mockups and screenshots) ranked by `general`, overriding only when the ui-researcher's slot model lacks `image_input`. [ASSUMED: needs user confirmation]
   - Alternative: skip the ui-researcher override until a curated affinity exists (Phase 18 skill affinity).
2. **`workflow.live_dom_uat` (Rigorous, "when frontend and a browser MCP exist")**
   - The inventory cannot detect a browser MCP without reading host MCP configs (`~/.claude.json` etc.), which is real-config parsing outside the phase.
   - Recommend: do not manage this key in Phase 17. Never set or unset it, and add a Rigorous+frontend note: "enable workflow.live_dom_uat via plan-set if a browser MCP is available". [ASSUMED]
3. **Project `runtime` mismatch on claude/cursor/pi hosts.**
   - D-23 makes `runtime` managed only on opencode/codex, and spec §8 says "offer migration".
   - Recommend: on opencode/codex, emit `set runtime: <host>`; on claude/cursor/pi with a mismatched project runtime, emit `op: unset` of `runtime` with a migration `why`. The effect on the cursor/pi installer bake is unverified, so label it. [ASSUMED]
4. **opencode probe side effects.** `opencode serve` writes opencode's own `opencode.db`/`log/` in its XDG data dir. That is not config, but it is another tool's state; `opencode models` already writes `log/`/`repos/`. Recommend accepting this and documenting it (precedent). Raise it only if uz wants strict zero side effects.
5. **`claude_md_path`.**
   - gsd-core 1.16 `config-new-project` writes `claude_md_path: "./.claude/CLAUDE.md"` [VERIFIED: scratch], and this repo holds a stale `./CLAUDE.md`.
   - It is not in the D-08 managed families, so Phase 17 reports the detected file and the configured value in the inventory, and adds an info note when the configured file is missing. No plan entry.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `opencode models --verbose` (1.x) for `image_input` | `opencode serve` v2 API `GET /api/model` `capabilities.input` | opencode 2.x (live v2.0.29) | needs a version-gated probe (Pattern 6) |
| global gsd-core only (`gsd_catalog` v1 era) | project-local-first shared resolver | Phase 16.1 D-18 | inventory must label scope (D-11) |
| `cache_write_json` with a fixed `<path>.tmp` | per-writer `mkstemp` + `os.replace` | Phase 16.1 (landed) | R3 concurrency edge satisfied |
| gsd-core 1.14 assumptions in the design spec | 1.16 installed; 1.17 published with the same tier tables | 2026-10 | read live; profiles now include `inherit` |

**Deprecated/outdated:**
- `cli-model-selection.md:159` citing `opencode models --verbose` (fix in this phase, D-24).
- Live counts in CONTEXT (196/254 scored) have drifted; today it is 195 entries, 150 scored.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Routers get `vendor: null` (ineligible for the automatic counterpart pick) | Pattern 3 | A router could become a "different vendor" counterpart that actually routes to the same vendor |
| A2 | `router_confirmed` requires `"is_router" in heuristic_confirmed` | Pattern 3 | Router wins (D-04) fire on unconfirmed name heuristics, or never fire |
| A3 | Effort-variant choice by family + tier effort (rigor `routing_tier_defaults`) | Pattern 5 | Over-spend (max effort everywhere) or under-powered slots |
| A4 | Claude host writes aliases in `model_overrides` | Pattern 10 | An unmappable pinned id falls through silently |
| A5 | "Frontend-capable" = `image_input` + `general` score | Open Q 1 | Wrong ui-researcher override |
| A6 | `live_dom_uat` not managed in 17 | Open Q 2 | A Rigorous+frontend plan lacks a key the spec lists |
| A7 | `runtime` unset on claude/cursor/pi mismatch | Open Q 3 | Migration semantics differ from the installer's |
| A8 | Unpriced native slot counts as within the ceiling | Pattern 4 | A pricey native model kept without evidence |
| A9 | One normalization pool (all candidates) for purpose scores | Pattern 3 | Relative order can shift vs per-host normalization |
| A10 | `needs_choice` without scores uses `source: preset` | Code Examples | Conflicts with how Phase 18 interprets `source` |

## Open Questions (RESOLVED — answers are locked in 17-CONTEXT D-25..D-32; where a recommendation here differs, the D-XX wins)

1. **Product: R4 no-scores ordering**: recommend price ascending then id (OQ2).
2. **Product: R12 note granularity**: recommend one note per family naming each key (OQ5), then amend the SPEC.
3. **A3 effort-variant rule and A5 frontend-capable** need uz's confirmation before the golden plans are frozen.
4. **SPEC/ROADMAP amendments** (per the AGENTS.md workflow): R12 wording; R5 edge (global omit = latent conflict); D-17's escalation clause (live: adds no tier); R11 `live_dom_uat` handling if A6 is accepted.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| python3 (system) | unit tier, runtime | ✓ | 3.14.7 | — |
| uv | integration/validate tiers | ✓ | 0.11.28 | — |
| node | gsd-core table read + probe | ✓ | v24.21.0 | inventory exits 2 (with message) |
| gsd-core (project-local) | R2 | ✓ | 1.16.0 | exit 2 with searched paths |
| opencode | D-24 probe, enumeration | ✓ | v2.0.29 | models.dev `image_input` only, labelled |
| codex / cursor-agent / claude | enumeration (via detect-runtimes) | ✓ | — | catalog `none` / native maps |
| pi | (enumeration deferred, Phase 22) | binary present, not in `KNOWN_CLIS` | — | synthetic goldens (D-20) |
| Artificial Analysis key | scored catalog | configured (checked by name only in discuss) | — | unscored path (R4) |
| network (models.dev/AA) | `fetch-model-catalog` | not probed this session | — | stale/none states |

**Missing dependencies with no fallback:** none.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | stdlib `unittest` via `tools/run_unittest_parallel.py` tiers (CPU-share-capped parallel, one subprocess per module) |
| Config file | `tools/run_unittest_parallel.py` (`EXPLICIT_GROUPS`); listings generated by `tools/gen_test_groups.py`; enforced by `tests/test_gate_scope.py` |
| Quick run command | `python3 -m unittest tests.test_curated_config_recommend tests.test_curated_config_inventory -v` |
| Full suite command | `make test` (plus `make validate` before close) |

New modules belong in the default `unit` group (system python3, stdlib only). Tests needing real node/gsd-core skip when they are absent, following the `_RealGsdTestCase` pattern. The opencode probe tests use fake `Popen`/`urlopen` (no real server in the suite).

### Phase Requirements → Test Map
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

### Sampling Rate
- **Per task commit:** the quick run command for the touched module(s).
- **Per wave merge:** `make test-unit && make arch-test`.
- **Phase gate:** `make test` and `make validate` green before `/gsd-verify-work`.

### Wave 0 Gaps
- [ ] `tests/fixtures/curated_config_v2/gsd_tables_1_16.json`: tables captured once from the installed 1.16 (D-20), placeholder paths only
- [ ] `tests/fixtures/curated_config_v2/` trimmed model lists (cursor, opencode, codex, claude) plus a synthetic pi list (labelled)
- [ ] `tests/fixtures/opencode_api_model.json`: the spike sample (4 entries)
- [ ] the three new test modules, then `python3 tools/gen_test_groups.py`
- [ ] golden regeneration flag (for example env `AI_KIT_REGEN_GOLDENS=1`), never on by default

## Security Domain

`security_enforcement: true`, ASVS level 1 (`.planning/config.json`).

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | partly | opencode probe uses the server's own one-time password over loopback only; never logged |
| V3 Session Management | no | — |
| V4 Access Control | no | — |
| V5 Input Validation | yes | argparse `choices` for profile/rigor/y-n; strict inventory schema check (`schema_version`, required keys, types) before use; node output parsed as JSON with shape checks |
| V6 Cryptography | minimal | `hashlib.sha256` for the inventory digest (integrity, not security) |
| V7 Errors/Logging | yes | no secrets in output: AA key never read into the inventory; opencode token redacted; structured exit-2 errors |
| V12 Files | yes | inventory is read-only on the project; `--out` atomic write; no path from inventory content is ever opened by `recommend` |

### Known Threat Patterns
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Command injection via project dir or key names into node/subprocess | Tampering | argv lists, never `shell=True` (arch rule 8); keys passed as one JSON argv element |
| Malicious or corrupted inventory JSON driving `recommend` | Tampering | schema/type validation, unsupported version → exit 2, digest recorded |
| Token leak from `opencode serve` | Information disclosure | redact; never echo stdout lines; loopback bind `127.0.0.1` |
| Orphaned local server | DoS / resource | `try/finally` terminate → wait → kill; test with a fake Popen |
| Writing into the user's project/config | Tampering | read-only inventory test (byte-identical, read-only dir) |
| Real-config fixtures | Information disclosure | temp HOME/XDG/GSD_HOME in all tests |

## Sources

### Primary (HIGH confidence)
- Installed gsd-core 1.16.0 (`.claude/gsd-core`): `bin/lib/model-catalog.cjs` (exports, `EFFORT_LADDER` :134, `nextTier`), `bin/lib/config-schema.cjs` (`isValidConfigKey`), `bin/lib/config-loader.cjs` (:925-1003, GSD_HOME, Branch C/D), `bin/lib/model-resolver.cjs` (`resolveModelInternal`, `dynamicRoutingModel`, `resolveModelForTier`), `bin/lib/config.cjs:994-999`, `bin/lib/intel.cjs:30-37`, `bin/shared/config-defaults.manifest.json`
- Live scratch probes (temp HOME/project, all cleaned): `isValidConfigKey` over 58 keys; `config-new-project` copy behavior; global/project `resolve_model_ids` resolution; `dynamic_routing --attempt`; codex object override; `opencode serve --port 0` output
- Published `@opengsd/gsd-core` 1.12.0/1.13.0/1.17.0 tarballs (grep only, deleted afterward); `pnpm view @opengsd/gsd-core versions`
- In-repo code: `ai_kit_spec/{gsd_tools,cache,model_ranker,model_catalog,detection,vendor,catalog_build,cli}.py`; `ai_kit_gsd_curated_config/{cli,gsd_catalog,model_detect,claude_md_detect,frontend_detect}.py`; `tools/run_unittest_parallel.py`; `tests/test_arch.py`; `tests/test_gate_scope.py`; `Makefile`
- Live ai-kit cache (read-only): `~/.cache/ai-kit/spec/{runtimes,model-catalog}.json`

### Secondary (MEDIUM confidence)
- `17-SPIKE-opencode-image-input.md` (2026-10-15): `/api/model` shape and basic auth (re-confirmed only the startup lines this session)

### Tertiary (LOW confidence)
- None used for decisions; all `[ASSUMED]` items are listed in the Assumptions Log.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH, all in-repo or installed, versions read live.
- Architecture: HIGH for data sources and purity boundary; MEDIUM for effort-variant and frontend-capable rules (assumptions A3/A5).
- Pitfalls: HIGH, each backed by a live probe or source read this session.

**Research date:** 2026-10-15
**Valid until:** 2026-11-14 for gsd-core facts (1.17 is already out; re-probe on upgrade); 7 days for live catalog counts.
