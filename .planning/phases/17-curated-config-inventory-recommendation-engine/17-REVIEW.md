---
phase: 17
status: issues_found
depth: deep
reviewers: [gsd-code-reviewer x3 (A/B/C batches), ponytail-review]
date: 2026-10-15
---
# Phase 17 Code Review (consolidated)

Batches: A = recommend.py, roles.py, presets.py; B = inventory.py, host.py, project_facts.py, plan_io.py, cli.py, catalog_adapter.py, frontend_detect.py, gsd_catalog.py; C = ai_kit_spec changes, gates, golden tests. Finding ids keep their batch prefix (A-CR-01, B-WR-03, C-IN-08, PT-1...).

Duplicates: A-CR-01 == B-CR-01 (MODEL_PROFILES orientation); A-WR-01 ~ B-WR (plan_io under-validation); B-WR (worktree warning braces) == C note; C-IN (detect_opencode_image_input test-only) == PT-3.

## Gray-area decisions (jev ladder, RUN-42)
- A-WR-04 Claude alias ranking: own reasoning (Laya B 0.35 fallback, TypeSafe C 0.53 fallback) -> collapse to one row per alias using the highest-version id as representative; `why` names the representative and an `effect` says the alias mapping is inferred.
- A-IN-09 D-08 families: A (TypeSafe 0.95) -> narrow managed families to the prefixes the plan can write (review.default_reviewers, review.models., review.effort., effort.routing_tier_defaults., effort.agent_overrides.); other user knobs are kept.
- C-IN-08 AA fixture data: A (Laya 0.88) -> replace real Artificial Analysis values with synthetic scores keeping the same ordering, regenerate goldens, mark the fixture synthetic.


# Batch A

## Phase 17: Code Review Report (batch A)

**Reviewed:** 2026-10-15T11:06:52Z
**Depth:** deep (call paths traced into plan_io.py, cli.py, inventory.py, catalog_adapter.py, gsd_catalog.py and the worktree's real gsd-core 1.16.0)
**Files Reviewed:** 4
**Status:** issues_found

### Summary

The recommend engine is pure. It uses only stdlib imports and never touches the clock, environment or network. Output is byte-stable for every reachable input I tried. Tie order, `-fast` exclusion, the ceiling cap fallback and the D-19 reservations all match SPEC/CONTEXT on the synthetic fixtures, and the 97 tests pass.

The blocker is in the shape of the input data. The real `inventory` command emits gsd-core's `MODEL_PROFILES` as `agent -> profile -> tier`, the order gsd-core itself uses. `roles.agent_tier`/`roles.used_tiers` index it as `profile -> agent -> tier`. So `inventory | recommend` raises `KeyError: 'adaptive'` on every host. I reproduced this by running the real node query against `.claude/gsd-core` (see CR-01). The unit fixtures use the wrong orientation, and the golden test transposes the real table before feeding it in, so CI never sees the real shape.

The warnings fall into three groups:
- **Fail-closed gaps:** some inputs crash with a traceback instead of exit 2, and same-layer duplicate keys pass the guard.
- **Wrong or overstated claims in plan output:**
  - codex `keep` values that are not the gsd default;
  - Claude alias picks justified by a stale model's score;
  - a router note promising behavior that does not exist;
  - a wrong vision note;
  - an unprobed key reported as "rejected by gsd-core".
- **Layering:** specialists are computed against slot entries that are later dropped.

### Critical Issues

### CR-01: `model_profiles` orientation mismatch: recommend crashes on every real inventory

**File:** `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/roles.py:262-281` (consumed via `recommend.py:352, 365, 425, 509, 588, 615, 669`)

**Issue:** `agent_tier` reads `gsd_core["model_profiles"][profile].get(agent)` and `used_tiers` iterates `gsd_core["model_profiles"][profile]`. gsd-core 1.16 exports `MODEL_PROFILES` agent-first (`{"gsd-planner": {"quality": "opus", "balanced": "opus", ...}}`). The inventory stores that object verbatim:
- `gsd_catalog._GSD_TABLES_QUERY_SCRIPT` writes `model_profiles: m.MODEL_PROFILES`;
- `tests/test_curated_config_inventory.py:288` even asserts `"gsd-planner" in parsed["gsd_core"]["model_profiles"]`.

Reproduced against the worktree's real gsd-core:

```
tables = gsd_catalog.query_gsd_tables(<real node + .claude/gsd-core lib paths>, proj, presets.closed_key_set("codex"))
## tables["model_profiles"] keys: ['gsd-planner', 'gsd-roadmapper', 'gsd-executor', ...]
recommend.build_plan(inv_with_those_tables, RecommendOpts("adaptive", "standard"))
## -> roles.py:276 used_tiers: KeyError: 'adaptive'   (same for claude/opencode hosts via agent_tier)
```

`plan_io._validate_gsd_core` (plan_io.py:108) only checks that the value is a dict. So `cli._cmd_recommend` (cli.py:466) dies with a traceback (exit 1) instead of producing a plan, for every host, profile and rigor.

The bug is masked twice:
- `TABLES["model_profiles"]` in `tests/test_curated_config_recommend.py:55-100` is profile-first, which is not gsd-core's shape;
- `tests/test_curated_config_golden.py:85-103` (`_profile_first_model_profiles`) transposes the real fixture before the fake node returns it.

The 17 golden plans therefore never exercise the shape the real node query emits.

Separately, gsd-core's `computeProfileTier` (model-resolver.cjs:376-404) falls back to `agentModels['balanced']` when a profile column is missing. `agent_tier` has no such fallback.

**Fix:** Read the native gsd-core orientation in roles (single source of truth), mirror the gsd-core fallback, and stop transposing in tests:

```python
def agent_tier(agent: str, gsd_core: dict, profile: str, shifts: dict) -> str | None:
    phase = gsd_core["agent_to_phase_type"].get(agent)
    if phase is not None and phase in shifts:
        tier = shifts[phase]
    else:
        cols = gsd_core["model_profiles"].get(agent) or {}
        tier = cols.get(profile) or cols.get("balanced")   # computeProfileTier fallback
    return tier if tier in presets.TIERS else None


def used_tiers(gsd_core: dict, profile: str, shifts: dict) -> tuple[str, ...]:
    seen = {agent_tier(a, gsd_core, profile, shifts) for a in gsd_core["model_profiles"]}
    return tuple(t for t in presets.TIERS if t in seen)
```

Then rewrite `TABLES["model_profiles"]` agent-first and delete `_profile_first_model_profiles` from the golden builder. Add one test that feeds `gsd_tables_1_16.json`'s `model_profiles` unmodified into `build_plan`. Also validate the orientation in `plan_io._validate_gsd_core`: every value is a dict of profile -> str.

### Warnings

### WR-01: `build_plan` dereferences fields the validator never checks, so it crashes with a traceback instead of the D-31 exit 2

**File:** `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/recommend.py:769-770, 791`; `roles.py:74-75, 91-97, 153-155, 165`

**Issue:** `plan_io._validate_candidates` (plan_io.py:161) only checks `runtime`/`model`/`is_host`, and `_conflict_item_problem` only checks `kind`/`key`/`scope`. The engine indexes the following directly:
- `c["score_axes"]`, `c["fast_twin_of"]`, `c["is_router"]`, `c["purpose_scores"]`, `c["price"]` and `c["family"]`;
- `item["why"]` and `item["value"]` on conflicts;
- `gsd_core["model_profiles"][profile]`.

Verified:
- a candidate `{"runtime","model","is_host"}` raises `KeyError: 'score_axes'`;
- a `resolve_model_ids` conflict without `why` raises `KeyError: 'why'`.

`_cmd_recommend` does not catch exceptions, so the user gets a traceback (exit 1). D-31 and the `_cmd_recommend` docstring promise a one-line message and exit 2 with "rerun inventory". CR-01 surfaces the same way.

**Fix:** Extend `_validate_candidates`/`_conflict_item_problem` to cover every field recommend reads:
- the candidate fields above, with their types;
- `why: str` on conflicts;
- `value: dict` when `kind == "model_policy"`;
- a `profile` column present for at least one agent.

As a backstop, wrap `recommend.build_plan` in `_cmd_recommend` with `except (KeyError, TypeError, ValueError) as exc:`, print `inventory <path>: malformed ({exc}); rerun inventory` and return 2.

### WR-02: The duplicate-key guard misses duplicates within a layer, so the plan can carry the same key twice

**File:** `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/recommend.py:887-893`

**Issue:** Each new entry is compared only against `all_entries` from previous layers, and `all_entries` is extended after the loop. Two entries with the same key from one layer pass silently.

Verified: two `model_policy` conflicts (project + global, which the validator accepts) yield two `model_policy.provider` unset entries in `plan["entries"]`. Their relative order comes from the conflict list order, so a reordered inventory changes the bytes. Phase 18 `apply`, which keys by `key`, would see an ambiguous plan.

The cross-layer case the guard does check cannot actually occur, because reconcile filters leftovers by `planned`. In practice the guard is dead, and the case that can occur is unguarded. It also raises a bare `ValueError` that the CLI does not catch.

**Fix:**

```python
seen: set[str] = set()
for layer in _LAYERS:
    entries, notes = layer(ctx, all_entries)
    for entry in entries:
        if entry["key"] in seen:
            raise ValueError(f"duplicate plan key {entry['key']}")
        seen.add(entry["key"])
    ...
```

Also dedupe conflicts by kind in `_conflict_unsets`: project scope wins over global. Map the `ValueError` to exit 2 (WR-01).

### WR-03: Codex `keep` entries show a `reasoning_effort` that is not the gsd default they claim to keep

**File:** `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/recommend.py:244-254, 188-195, 292-299`

**Issue:** For a kept native slot, `value` is built by `_slot_value(..., meta.target)`, which sets `reasoning_effort` to the rigor's tier target, not the native slot's effort. The committed golden `codex-standard-adaptive.json` shows:
- `model_profile_overrides.codex.sonnet keep {"model":"gpt-5.6-terra","reasoning_effort":"high"}`, why "kept gsd default", while gsd-core 1.16's `RUNTIME_PROFILE_MAP.codex.sonnet` is `{"model":"gpt-5.6-terra","reasoning_effort":"medium"}`;
- `haiku` shows `"low"` against a native `"medium"`.

`keep` writes nothing, so the effort that actually takes effect is not the one displayed. The plan presents an invented value as the gsd default, which breaks the "never more certainty than sourcing" rule.

`_codex_empty_slots` also reads `slot.get("reasoning_modes")` from a `RUNTIME_PROFILE_MAP` slot. Real slots only carry `model`/`reasoning_effort`, so `modes` is always `[]` and the value is again the raw rigor target.

**Fix:** For `op: keep` and keep-turned-`unset`, emit the native slot verbatim:

```python
native_slot = ctx.inv["gsd_core"]["runtime_profile_map"][ctx.host][tier]
value = dict(native_slot) if ctx.host == "codex" else native_slot["model"]
```

Use the same in `_codex_empty_slots` and delete the `reasoning_modes` lookup.

### WR-04: On a Claude host, a stale model's score justifies an alias that resolves to a different model

**File:** `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/recommend.py:415-420, 513-521, 435-436` (also `_vision_keep` 634-640, `_facts` 387-400)

**Issue:** The Claude runtime lists several ids per alias. The shared fixture lists `claude-opus-4-8` and `claude-opus-5-5`, and `claude-haiku-4-5` and `claude-haiku-5-5`. `best_pick` ranks each id separately and `_value_for` collapses the winner to its alias.

Verified:
- `claude-opus-4-8` has execution 9, `claude-opus-5-5` 4 and `claude-sonnet-5` 6;
- the result is `model_overrides.gsd-executor = "opus"`, `source: catalog-score`, why "... inferred family claude-opus-4-8 ...".

Claude Code maps `opus` to its current model (D-01: the stale id "never reaches the user"). The run would use a model that scores worse than the sonnet slot, while the plan claims a score-based win. The ceiling check also uses the stale id's price.

**Fix:** On the claude host, collapse candidates to one row per alias before ranking. Use a deterministic representative, such as the highest-version id per alias, or the minimum score across the alias group to stay conservative. Say so in `why`, e.g. "alias opus (Claude Code maps it to its current model; scored as claude-opus-5-5)". Without a verified alias-to-id map, mark the entry with an `effect` such as "alias mapping unverified".

### WR-05: The `router_unconfirmed` note promises that review routers can win a slot, but no code path lets them

**File:** `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/recommend.py:439-454`

**Issue:** The note fires for any router whose purpose is declared but unconfirmed, and it says "confirm it via ai-kit-spec-config to let it win its slot". Only `name_declared_purpose == "execute"` routers are ever used (lines 528-539). `_eligible_pool` (roles.py:155) excludes every router from tier, counterpart and vision picks. A confirmed `review` router wins nothing in Phase 17 (D-04 defers review routers to Phase 18).

The committed golden `opencode-*-adaptive.json` already carries this false promise for `router-env/my-plan-review`.

**Fix:** Emit the "let it win its slot" text only for `execute` routers. For `review` routers, either skip the note or word it "used by Phase 18 cross-AI review selection once confirmed".

### WR-06: The vision fallback note claims "no image_input model" when image-capable models exist

**File:** `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/recommend.py:666-678, 626-631`

**Issue:** Both branches emit `no image_input model on {host}`:
- the `any(...)` pre-check (which counts unscored models, routers and `-fast` twins);
- the `best_pick is None` branch.

Verified: opencode with `b/y` (`image_input: True`, unscored) yields "no image_input model on opencode; gsd-ui-auditor falls back to its tier". The user is told to look for a capability they already have; the real reason is that no image-capable model has a `general` score.

**Fix:** Keep the current text only when no host candidate has `image_input is True`. Otherwise emit e.g. `"image_input models on {host} have no general score (unscored, router or -fast twin); {agent} falls back to its tier; choose with plan-set"`.

### WR-07: `_drop_rejected` reports keys that were never probed as "not accepted by gsd-core"

**File:** `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/recommend.py:862-878`

**Issue:** Any planned key missing from `valid_keys.accepted` is dropped with the text "not accepted by the host gsd-core X isValidConfigKey". `valid_keys.rejected` is never consulted. A key that is in neither list was never probed. Two ways that happens:
- the inventory was produced by an ai-kit whose `closed_key_set` predates a key added later (Phase 18 will add keys while `schema_version` stays 1);
- a conflict value diverges from the probed existing/global config.

Such a key is silently dropped with a false provenance claim instead of failing closed.

**Fix:**

```python
accepted = set(vk["accepted"]); rejected = set(vk["rejected"])
unprobed = sorted(e["key"] for e in entries if e["key"] not in accepted | rejected)
if unprobed:
    raise ValueError(f"keys not probed by this inventory: {', '.join(unprobed)}")  # -> exit 2 "rerun inventory"
```

Keep the existing note text for `rejected` keys only.

### WR-08: Specialists are computed against slot entries that `_drop_rejected` removes later

**File:** `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/recommend.py:881-894, 917-918` (readers: `_slot_models` 363-381, `_write_exec_overrides` 482, `_append_counterpart_override` 561-565, `_append_vision_override` 647)

**Issue:** `_merge_layers` hands every later layer the unfiltered `all_entries`, and rejected keys are dropped only afterwards. If the host gsd-core rejects `model_profile_overrides.<host>.<tier>`, the specialist layer still treats that slot's planned model as the agent's effective model. It then skips executor, counterpart or vision overrides because `pick_val == slot_model`. The final plan has neither the slot nor the specialist override, even though spec §5 anticipates older gsd-cores (e.g. cursor 1.12) lacking keys.

The code-reviewer counterpart is also computed against a dropped executor override.

**Fix:** Apply the key filter per layer inside `_merge_layers`: `entries, drop_notes = _drop_rejected(ctx, entries)` before extending `all_entries`. Later layers then see only entries that will actually be written.

### WR-09: Explicit cross-AI answers are labelled `source: "preset"` instead of `"user"`

**File:** `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/recommend.py:729-737`

**Issue:** R7 defines `source ∈ {preset, catalog-score, curated-affinity, router-declared, user, native}`. When `--cross-ai-review y|n` / `--cross-ai-exec y|n` is passed explicitly (`defaulted: False`), the `workflow.plan_review_convergence` / `workflow.cross_ai_execution` entries still carry `source: "preset"`. `user` is never emitted anywhere, so Phase 18's review diff cannot tell a user decision from a rigor default.

**Fix:** `source = "preset" if answer["defaulted"] else "user"` for the boolean entry.

### WR-10: The purity guard whitelists an I/O module, so the AST check cannot enforce the R7 MUST-NOT

**File:** `tests/test_curated_config_recommend.py:1548-1575` (`ALLOWED_RELATIVE_IMPORTS`); `recommend.py:4-5, 9`

**Issue:** The recommend docstring says purity is "guarded by the tests' AST import check". That check allows `from . import plan_io`, and `plan_io` imports `gsd_catalog` (subprocess, os, shutil) and defines `load_inventory` (`open`) and `write_plan` (atomic write). A future `plan_io.load_inventory(...)` or `plan_io.gsd_catalog.subprocess.run(...)` call inside recommend passes the AST guard. Only the runtime mock test (lines 1581-1593) would catch it, and only on paths its single fixture executes. The structural guard for "MUST NOT: recommend performs no I/O" is therefore not structural.

**Fix:** Move `PLAN_SCHEMA_VERSION`, `canonical_json` and `inventory_digest` into a pure module (e.g. `plan_schema.py` with only `hashlib`/`json`), have `plan_io` re-export them, and drop `plan_io` from `ALLOWED_RELATIVE_IMPORTS`. Alternatively, let the AST guard recurse into each allowed sibling's imports.

### Info

### IN-01: The scored branch of `choice_candidates` is unreachable

**File:** `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/roles.py:225-238`
**Issue:** The only caller (`recommend._tier_slot`, line 272) reaches it after `best_pick` returned `None`, which means no candidate passes `purpose in purpose_scores and not fast and not router`. `scored` applies exactly that predicate, so it is always empty. That is 13 dead lines, including the `round(score, 1)` output path.
**Fix:** Delete the scored branch, or document and test the scenario it is meant for.

### IN-02: The final fallback in `pick_variant` is unreachable, order-dependent and mislabelled

**File:** `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/roles.py:144-146`
**Issue:** `effort_token` only returns ladder tokens and every preset target is on the ladder, so exact, lower, higher or bare always matches first. If the fallback were reached, `next(iter(groups))` would depend on input order (breaking R7) and would label a suffixed variant `"bare"`.
**Fix:** Replace it with `raise AssertionError("unreachable")`, or pick `min(groups, key=_ladder_index)` with rule `"nearest available"`.

### IN-03: Specialist functions skip silently when the agent has no tier

**File:** `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/recommend.py:509-511, 588-590, 669-673`
**Issue:** These branches cannot be reached with gsd-core 1.16 (all 7 specialists are in `MODEL_PROFILES`). If a later gsd-core drops an agent, the specialist disappears without the D-07 warning note.
**Fix:** Emit a `specialist` note ("{agent} unknown to gsd-core {version}"), or remove the branches.

### IN-04: Duplicated literals and logic

**File:** `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/recommend.py:308-316 vs 334-342`; `presets.py:141-148 vs 181-191`
**Issue:**
- `_pi_slot` repeats the same note dict verbatim in both branches.
- `_managed_key_set` and `closed_key_set` build the same union of PRESETS, CONDITIONAL_KEYS, CROSS_AI_KEYS and `model_profile` separately.
**Fix:** Hoist a `_PI_NOTE` constant, and build `closed_key_set` on top of a shared `_preset_key_union()`.

### IN-05: Parameter-object sprawl to satisfy pylint `max-args`

**File:** `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/recommend.py:27-76`
**Issue:** Seven private NamedTuples (`_SlotMeta`, `_PickRequest`, `_SpecialistRun`, `_SpecialistOut`, `_CounterpartReq`, `_CounterpartPick`, `_VisionPick`) exist mainly to bundle arguments, and several are built only to be unpacked again one line later (e.g. 558, 644). This is over-engineering that hurts readability. Several layers also take `prior_entries` only to `del` it.
**Fix:** Pass `ctx`/`run` plus one or two explicit values. Let layers that do not need prior entries accept `_prior` instead of `del`.

### IN-06: `op: "unset"` entries with a non-null `value`

**File:** `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/recommend.py:198-204, 245-254`
**Issue:** A kept native slot with an existing override becomes `op: unset` but keeps the native value in `value`. Every other unset (lines 773, 787, 804) uses `value: None`. A Phase 18 consumer could read it as "set to X".
**Fix:** Use `value: None` for unsets, or document that `value` on a keep-unset is the default that will apply.

### IN-07: A zero-candidate `needs_choice` says "no scores" instead of "no models enumerated"

**File:** `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/recommend.py:259-264`
**Issue:** `not any(...)` over an empty list is `True`, so an empty host list reads "no scores: no opencode candidate has a catalog score". The real cause is failed enumeration.
**Fix:** Branch on `not cands` first: `"no {host} models enumerated; choose with plan-set"`.

### IN-08: Digest normalization lives outside `plan_io.inventory_digest`

**File:** `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/recommend.py:897-904`
**Issue:** The candidate sort that makes the digest order-independent is a private recommend helper. Any other consumer (e.g. Phase 18 checking a plan against its inventory) that calls the public `plan_io.inventory_digest` gets a different digest whenever candidates are not pre-sorted.
**Fix:** Move the normalization into `plan_io.inventory_digest`.

### IN-09: The `review.*` and `effort.*` family prefixes unset user tuning knobs that no layer ever sets

**File:** `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/presets.py:131-138, 156-166`
**Issue:** gsd-core 1.16 accepts the following, and every existing one becomes `op: unset` with "managed by the curated plan":
- `review.max_prompt_tokens`, `review.max_prompt_tokens_per_reviewer`, `review.parallel_lanes`;
- `review.reviewer_instances.<id>.*`, `effort.default`.

This follows D-08 literally, but neither Phase 17 nor the Phase 18 scope in spec §6 writes these keys. Applying the plan loses user configuration (recoverable only via backup or `plan-unset`).
**Fix:** Confirm the intent with uz. If these knobs should survive, narrow the families to the keys the plan can write (e.g. `review.default_reviewers`, `review.models.`, `review.effort.`, `effort.routing_tier_defaults.`, `effort.agent_overrides.`).

### IN-10: `effort_token` treats product-name suffixes as effort variants

**File:** `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/roles.py:49-55, 120-143`
**Issue:**
- `gpt-5.1-codex-max` (a distinct model) is read as the `max` effort variant of family `gpt-5.1-codex`. The `vendor._MODEL_TIER_SUFFIXES` grouping strips `max`, so both land in one family.
- Under D-27's order (exact, lower, higher, then bare), a `medium` target picks `codex-max` over the bare `codex`.
- The family's ceiling price also becomes the minimum of two different models.

The existing `shortcut:` comment covers `minimal`/`ultra` only.
**Fix:** Extend the shortcut comment to `max`, or only treat a suffix as an effort token when the family also has at least one other ladder-suffixed sibling.

### IN-11: `clamp_effort` can return an effort level the model does not list

**File:** `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/roles.py:58-70`
**Issue:** When `modes` is empty or shares no level with the ladder, the raw target is returned. On codex this writes e.g. `reasoning_effort: "minimal"` (MVP light) for a model whose supported levels are unknown, with no `why` marker.
**Fix:** Add `"; effort unverified (no reasoning modes enumerated)"` to the slot `why` when `modes` is empty.

### IN-12: Test-file nits

**File:** `tests/test_curated_config_recommend.py:18-19, 1657, 1675`
**Issue:**
- `unittest.mock` is imported twice (`import unittest.mock` and `from unittest import mock`).
- `base` is built and then only `del`'d in `test_each_removed_required_key_named`.
**Fix:** Drop `import unittest.mock` and the unused `base`.

---

_Reviewed: 2026-10-15T11:06:52Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: deep_

# Batch B

## Phase 17: Code Review Report (batch B)

**Reviewed:** 2026-10-15T11:07:39Z
**Depth:** deep
**Files Reviewed:** 9
**Status:** issues_found

### Narrative Findings (AI reviewer)

### Summary

Batch B covers the inventory I/O side: host and gsd-core resolution, the node probe of the
gsd-core tables, catalog refresh and candidate building, project facts, the plan/inventory I/O
and the two new CLI handlers. I traced call chains into `ai_kit_spec` (`gsd_tools`, `cache`,
`detection`, `model_ranker`, `vendor`) and into `roles.py`/`recommend.py`, the consumers of the
inventory. I also ran the real chain in scratch dirs (temp HOME, a copy of the checkout's
gsd-core 1.16.0, catalog subprocesses faked, no network, real project and config files never
touched).

Main result: **a real `inventory` cannot be fed to `recommend`.** gsd-core exports
`MODEL_PROFILES` keyed by agent, the inventory passes that through unchanged, and `roles.py`
indexes it by profile. `recommend` dies with `KeyError: 'adaptive'` on every host. All 74 tests
in `tests/test_curated_config_inventory.py` pass anyway, because every test that reaches
`recommend` uses a hand-transposed fixture. The golden builder even documents the transpose as
"recommend expects profile -> {agent: tier}".

Two more confirmed defects:
- `recommend --out plan.json`, the SPEC R7 invocation word for word, exits 2: a bare filename
  makes `os.makedirs("")` fail.
- A project whose README.md is not UTF-8 crashes `inventory` with a traceback.

Verified sound:
- Live, the inventory leaves the project tree and the scratch HOME untouched.
- `config-path` returns an absolute path.
- The node `-e` argv indexing is correct.
- gsd-core runtime names match `HOSTS`.
- `PROJECT_CONFIG_KEYS` covers every managed key family.
- No secrets reach the inventory output.
- Runtime code is stdlib-only.
- No source file hardcodes a machine path.

### Critical Issues

### CR-01: Real inventory crashes recommend: `model_profiles` orientation mismatch (agent-first vs profile-first)

**File:** `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/gsd_catalog.py:146-147, 159-188`; `inventory.py:332-337`; consumer `roles.py:267, 276`
**Issue:** gsd-core 1.16's `MODEL_PROFILES` is `{agent: {quality, balanced, budget, adaptive}}`
(`.claude/gsd-core/bin/lib/model-catalog.cjs:76-81`). `_GSD_TABLES_QUERY_SCRIPT` serializes it
as-is. `_parse_tables_output` only checks that it is a non-empty dict, and `_assemble_inventory`
spreads it into `gsd_core` unchanged. `roles.agent_tier`/`roles.used_tiers` then read
`gsd_core["model_profiles"][profile]`, which is profile-first.

Reproduced end to end with the checkout's real gsd-core:
`inventory --host {claude,opencode,codex}` exits 0, then `recommend --profile adaptive` raises
`KeyError: 'adaptive'` (traceback, not exit 2). With an in-process transpose, `recommend`
succeeds on all 5 hosts, so this is the only break on that path.

Why the tests miss it:
- `tests/test_curated_config_golden.py:85-103` transposes the faked node output
  (`_profile_first_model_profiles`).
- `tests/test_curated_config_inventory.py:1273-1285` hand-writes a profile-first fixture.
- `_default_tables_from_argv` (line 85-94) uses the real agent-first shape but never reaches
  `recommend`.
- `TestRealGsdInventory` runs the real tables but never calls `recommend`.

The SPEC's core flow (`inventory` → `recommend`) is broken for every real user.
**Fix:** Normalize once at the inventory boundary and delete the test-side adapter so goldens run the production path:
```python
## gsd_catalog._parse_tables_output, inside the tables_ok branch
by_profile: dict[str, dict[str, str]] = {}
for agent, per_profile in profiles.items():
    if isinstance(per_profile, dict):
        for prof, tier in per_profile.items():
            if isinstance(tier, str):
                by_profile.setdefault(prof, {})[agent] = tier
out["model_profiles"] = by_profile
```
Then:
- Remove `_profile_first_model_profiles` from `tests/test_curated_config_golden.py` (feed the
  raw fixture).
- Add `plan_io._validate_gsd_core` checks so a wrong shape exits 2: every value is a dict of
  str, and the requested profile is a key.
- Extend `TestRealGsdInventory` to write the real inventory and run `recommend` on it for each
  host.

### CR-02: `recommend --out plan.json` (bare filename, the SPEC R7 invocation) always fails

**File:** `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/plan_io.py:194-201` (via `skills/ai-kit-spec-review/ai_kit_spec/cache.py:31-32`)
**Issue:** `write_plan` passes the user path straight to `cache.cache_write_text`, which does
`os.makedirs(os.path.dirname(path))`. For `plan.json`, `dirname` is `""` and
`os.makedirs("")` raises `FileNotFoundError`.

Reproduced: `recommend --inventory inv.json ... --out plan-rel.json` printed
`cannot write plan-rel.json: [Errno 2] No such file or directory: ''`, returned exit 2 and wrote
no file. SPEC R7's target literally reads `--out plan.json`. Every test passes an absolute
`os.path.join(tmp, ...)`, so nothing covers it.
**Fix:**
```python
def write_plan(path: str, plan: dict) -> None:
    ...
    cache.cache_write_text(os.path.abspath(path), canonical_json(plan))
```
Add a test that runs `recommend` with a relative bare `--out` from a temp cwd.

### CR-03: `inventory` crashes (traceback) on a non-UTF-8 README.md or package.json

**File:** `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/frontend_detect.py:27-29, 44-47, 69-72`; reached from `project_facts.py:41, 76`
**Issue:** `_read_text` opens with `encoding="utf-8"`, and the callers catch only `OSError` /
`json.JSONDecodeError`. `UnicodeDecodeError` is a `ValueError`, so neither handler catches it.

The docstring promises "Never raises", and this phase newly routes it through `inventory`
(`project_facts.project_facts` → `detect_frontend_present`, and the new public
`package_json_deps` → `detect_db_present`). Reproduced: a README.md containing Latin-1
`Caf\xe9 React app` makes `project_facts()` raise `UnicodeDecodeError`. `inventory` therefore
dies with a traceback and exit 1 instead of a degraded "no signal" fact.

The same class of crash applies to the unguarded `os.listdir` in `project_facts.py:49`
(`detect_intel_index`) and `:61` (`list_skills`) on an unreadable dir.
**Fix:**
```python
def _read_text(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()
```
Alternatively, catch `(OSError, ValueError)` at lines 46 and 71. Wrap the two `os.listdir`
calls with `except OSError: return False` / `continue`. Add a Latin-1 README fixture test.

### Warnings

### WR-01: Inventory validation is too shallow, so malformed inventories traceback instead of exiting 2 ("rerun inventory")

**File:** `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/plan_io.py:108-123, 161-191`
**Issue:** `_cmd_recommend`'s docstring promises "Any load or write failure is a one-line stderr
message and exit 2" (D-31 fail-closed). However:
- `_validate_candidates` checks only `runtime`/`model`/`is_host`.
- `_validate_gsd_core` checks only that `model_profiles` is a dict.

Reproduced crashes, each a traceback:
- A candidate missing `score_axes`: `KeyError: 'score_axes'`.
- A candidate with `price: "4"`: `ValueError: Unknown format code 'g'`.
- The CR-01 shape: `KeyError: 'adaptive'`.

Also, `load_inventory` catches `json.JSONDecodeError` but not `UnicodeDecodeError`. Reproduced:
an inventory file starting with `\xff\xfe` raises a traceback.
**Fix:**
- Validate every candidate field `recommend` reads: `score_axes` int; `price` number or null;
  `purpose_scores` dict of number; `family` str; `is_router`/`router_confirmed` bool;
  `image_input` bool or null; `reasoning_modes` list; `vendor`/`fast_twin_of` str or null.
- Validate the `model_profiles` profile→agent→tier shape.
- Change line 183 to `except (json.JSONDecodeError, UnicodeDecodeError):` (or `ValueError`).

### WR-02: `inventory` reports a nonexistent `--project-dir` as a valid empty project (exit 0)

**File:** `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cli.py:437-448`
**Issue:** `_cmd_inventory` takes `os.path.abspath(args.project_dir)` without checking that it
exists. Reproduced: with a global gsd-core and `--project-dir <home>/does-not-exist-typo`,
inventory exits 0 with `scope: global`, `existing_config.exists: false`, no conflicts and all
facts false. A typo yields a plausible "fresh project" plan that silently drops every existing
key and conflict.
**Fix:**
```python
project_dir = os.path.abspath(args.project_dir)
if not os.path.isdir(project_dir):
    print(f"ai-kit-gsd-curated-config: --project-dir {project_dir} is not a directory", file=sys.stderr)
    return 2
```

### WR-03: The `config-path` call has no timeout and no exception handling: the only untimed subprocess in inventory

**File:** `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/inventory.py:85-96` (wrapper `ai_kit_spec/gsd_tools.py:232-247`)
**Issue:** Every other inventory subprocess has a timeout and catches `OSError`: git 10s, node
query 30s, ai-kit-spec 120s. `gsd.config_path(...)` boots the full gsd-tools CLI with neither.
A hung gsd-tools (or a project-local one, see WR-07) blocks `inventory` forever, and a spawn
failure raises out of `build_inventory` as a traceback.
**Fix:** In the shared wrapper, pass `timeout=10` and catch
`(OSError, subprocess.SubprocessError)`, returning `None`. Then
`_existing_config` falls back to `<project>/.planning/config.json` as it already does on
failure.

### WR-04: A failed models.dev refresh is labelled `fresh` with no warning when AA succeeds

**File:** `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/catalog_adapter.py:215-228`
**Issue:** `if skipped or models_ok or aa_ok:` returns `"fresh"` and warns only for
`models_ok and not aa_ok`. With models.dev down and AA up (`models_ok=False, aa_ok=True`), the
inventory claims a fresh catalog with no warning. Prices, `image_input` and provider rows
then all come from the old cache.

This breaks R3 ("when the refresh fails ... adds a warning") and the AGENTS.md rule never to
present a result with more certainty than its sourcing.
**Fix:**
```python
if not skipped and not models_ok:
    warns.append("models.dev refresh failed; prices and capabilities from cache")
```
Add a fixture test for `{"models_dev_ok": false, "artificial_analysis_ok": true}`.

### WR-05: The outer 120s SIGKILL on `detect-runtimes` can orphan the D-32 private `opencode serve`

**File:** `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/catalog_adapter.py:179-191` (spawned in `ai_kit_spec/detection.py:440`)
**Issue:** `subprocess.run(..., timeout=120)` sends SIGKILL only to the direct child
(`ai-kit-spec.py detect-runtimes`). The probe's cleanup lives in that child's `finally`
(detection.py:462-468) and in its daemon `threading.Timer`. Both die with the child, while the
grandchild `opencode serve` (no `start_new_session`, own stdout pipe) survives as an orphan.

This defeats D-32's "kills only its own PID / guaranteed kill". This is reasoning-based, not
reproduced. Likelihood is low: the inner timeouts sum to about 80s, so it needs a stall past
120s. Whether opencode exits when its stdout reader dies is unverified.
**Fix:** Run the refresh subprocess in its own session and kill the group on timeout, e.g.:
- call `run_fn(..., start_new_session=True)`;
- on `TimeoutExpired`, `os.killpg(proc.pid, SIGKILL)` through a small Popen helper.

Alternatively, have the probe register `atexit`/signal handlers. Either keeps the guarantee
end to end.

### WR-06: A `{` or `}` in the main-checkout path crashes inventory (str.format injection)

**File:** `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/host.py:100-121`
**Issue:** `_worktree_warning` interpolates `main` into an f-string that still contains
`{root}`, and `_global_worktree_warnings` then calls `.format(root=install_root)` on it. A
legal path such as `/tmp/repo{x}` turns into a format field. Reproduced: `KeyError: 'x'`, an
uncaught crash of `inventory`. It triggers on a global-scope resolution inside a worktree whose
main checkout has a local install.
**Fix:** Drop the two-stage templating:
```python
def _worktree_warning(main: str, host: str, install_root: str) -> str | None:
    ...
            return (f"gsd-core resolved globally at {install_root}, but the main checkout "
                    f"{main} has a project-local install; versions can differ (D-11)")
```

### WR-07: The "read-only" inventory executes project-controlled code (security, undocumented)

**File:** `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/inventory.py:88-92, 123-137`; `host.py:124-147`
**Issue:** With project-local-first resolution (D-11), `inventory --project-dir <repo>` runs two
pieces of code from the repo:
- `node <repo>/.claude/gsd-core/bin/gsd-tools.cjs config-path`;
- `require()` of `<repo>/.claude/gsd-core/bin/lib/{model-catalog,config-schema}.cjs`.

It also honors `RUNTIME_DIR` from the env. Run against an untrusted checkout, a command
advertised as a read-only snapshot gives that checkout arbitrary code execution. GSD itself
behaves the same way, so this is by design, but neither the CLI help nor the module docstrings
say so. A user may reasonably run "inventory" to inspect an unfamiliar repo.
**Fix:** State it in the `inventory` subparser help and in SKILL.md, e.g. "runs the project's
own gsd-core (node); only use on trusted checkouts". The inventory already reports
`gsd_core.scope: local`; also surface `path` in that note.

### WR-08: A missing `vendor` sibling module silently yields zero candidates

**File:** `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/catalog_adapter.py:122-129, 237-241`
**Issue:** `_load_spec_stack` checks detection, model_catalog, cache and model_ranker, but not
`vendor`. `build_candidates` returns `[]` with no warning when any of the three modules it
loads is missing. An older installed `ai-kit-spec-review` (resolved via
`~/.claude/skills`/`CLAUDE_PLUGIN_ROOT`) then produces an inventory with
`catalog.state: fresh`, no candidates and no warning. `recommend` turns that into
`needs_choice` everywhere, and nothing explains why.
**Fix:** Add `vendor` to `_load_spec_stack` so `refresh_catalog` returns `_SIBLING_ERR`, and
make `build_candidates` raise or return an error instead of `[]` when its modules are absent.

### WR-09: The SPEC must-NOT "never write to the project's .planning/" is enforced only by help text

**File:** `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cli.py:541-545, 466-471`
**Issue:** `--out` is written unconditionally. `--out .planning/config.json` (or
`existing_config.path`, `global_defaults.path`, or the `--inventory` file itself) atomically
replaces the GSD config, or the input, with plan JSON. The inventory already carries both
config paths, so a guard is cheap.
**Fix:** Before `write_plan`, refuse (exit 2) when `os.path.realpath(args.out)` equals the
realpath of `loaded["existing_config"]["path"]`, `loaded["global_defaults"]["path"]` or
`args.inventory`, or lies under `os.path.dirname(existing_config.path)`.

### WR-10: Tests mask CR-01; the "feeds recommend" test uses a shape gsd-core never emits

**File:** `tests/test_curated_config_inventory.py:1263-1340, 260-300`
**Issue:**
- `test_complete_inventory_feeds_recommend` fakes `model_profiles` as
  `{"adaptive": {agent: tier}}`, the opposite of the real export (and of this file's own
  `_default_tables_from_argv` at line 85-94). It then asserts only `plan["schema_version"] == 1`.
- `TestRealGsdInventory` asserts `"gsd-planner" in model_profiles`, which holds only for the
  agent-first shape, yet never runs `recommend`.

So the suite pins both shapes and passes (74/74) while the real chain crashes.
**Fix:**
- Use the agent-first shape (or the shared `gsd_tables_1_16.json` fixture) in the
  feeds-recommend test, and assert real plan content (e.g. a `model_profile` entry).
- Add a real-gsd inventory→recommend round trip per host.

### Info

### IN-01: `plan_io._ill` has dead branches and a hardcoded version in its message

**File:** `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/plan_io.py:50-62, 69-71`
**Issue:** `_ill` is only called with `"str"`, `"dict"` and `"list"`, so the `"int"` and
`"str-or-null"` branches are dead. `_schema_version_problem` hardcodes "expected 1" instead of
`INVENTORY_SCHEMA_VERSION`, which will go stale on the next bump. `_validate_conflicts` runs
outside `_validate_inventory` for no clear reason.
**Fix:** Drop the unused branches, use `f"... (expected {INVENTORY_SCHEMA_VERSION})"`, and fold
`_validate_conflicts` into `_validate_inventory`.

### IN-02: Unused parameter and duplicate node resolution in inventory

**File:** `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/inventory.py:123, 124, 352`
**Issue:** `_probe_gsd_tables(core, host_name, ...)` never uses `host_name`.
`resolve_node_binary` runs twice per inventory (lines 124 and 352).
**Fix:** Remove the parameter, and resolve node once in `_load_configs` and pass it down.

### IN-03: A global `resolve_model_ids: omit` with no `.planning/` is active, not just latent

**File:** `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/inventory.py:234-243`
**Issue:** With `.planning/` absent, gsd-core reads `~/.gsd/defaults.json` at resolution
(config-loader Branch D, `config-loader.cjs:998-1001`), so the omit already applies.
`_global_model_policy` appends "read at resolution while .planning/ is absent" for this case,
but `_resolve_model_ids` does not. The D-31 `effect: latent` label stays, but the `why`
understates.
**Fix:** Mirror the `planning_dir_present` suffix: pass `facts` into `_resolve_model_ids`.

### IN-04: Two warning texts overclaim what is cached

**File:** `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/catalog_adapter.py:18, 20, 135-136, 225-226`
**Issue:**
- `_DETECT_WARN` ("using the cached runtimes snapshot") is emitted even when no snapshot exists.
  The result is zero candidates with a warning that implies a fallback.
- `_AA_WARN` ("scores from cache") fires on every non-skipped refresh on a machine without an
  AA key, where no scores ever existed.

**Fix:**
- Use "...; no cached snapshot" when `runtimes` is empty.
- Say "Artificial Analysis unavailable (no key or fetch failed)" and drop "from cache" when the
  catalog is unscored.

### IN-05: The env/which DI seam is leaky

**File:** `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/host.py:76`; `inventory.py:90`; `gsd_catalog.py:196-209`
**Issue:**
- The git and node subprocesses (`project_root`, `_main_checkout`, `config_path`,
  `query_gsd_tables`) inherit the process env instead of `deps.env_fn()`, while the ai-kit-spec
  calls pass `env=env`.
- `gsd_tools_candidates` uses the real `shutil.which` instead of `deps.which_fn`.

Production is unaffected. Under an injected env, though, Python-side `GSD_HOME`/`HOME` (used by
`_global_defaults`) and node-side `GSD_HOME` (used by `isValidConfigKey` capability lookups) can
diverge.
**Fix:** Pass `env=deps.env_fn()` to those `run_fn` calls and thread `which_fn` into
`gsd_tools_candidates`.

### IN-06: The legacy `depth` key is not captured, so `existing` for `granularity` is misreported

**File:** `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/inventory.py:18-37`
**Issue:** gsd-core hoists a top-level `depth` into `granularity` when the latter is absent
(`configuration.cjs` normalization 4). Older configs therefore have an effective granularity
that the inventory reports as absent, and the plan shows "add" instead of "change".
**Fix:** Include `depth` in `PROJECT_CONFIG_KEYS` and surface it as an `info` item, or map it,
when `granularity` is absent.

### IN-07: Absolute literal paths in tests

**File:** `tests/test_curated_config_inventory.py:231-232, 239-240, 1357`
**Issue:** `"/tmp/proj"`, `"/tmp/h"`, `"/tmp/x"`, `"/usr/bin/node"` and `"/p"` are synthetic
and never touched on disk (pure functions and mocks), but AGENTS.md bans hardcoded absolute
paths in tests.
**Fix:** Use `tempfile.mkdtemp()` or `os.path.join(os.sep, "proj")`-style synthetic roots.

### IN-08: Inconsistent error prefix, and `--out` side effects

**File:** `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cli.py:457-459`; `plan_io.py:194-201`
**Issue:**
- `_cmd_recommend` prints the load error without the `ai-kit-gsd-curated-config:` prefix that
  every other error path uses.
- `write_plan` (through `cache_write_text`) silently creates missing parent directories for
  `--out`, and leaves plan.json at mkstemp's mode 0600.

**Fix:**
- Prefix the message.
- Decide whether `--out` into a nonexistent directory should be an error; if 0600 is intended,
  document it.

---

_Reviewed: 2026-10-15T11:07:39Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: deep_

# Batch C

## Phase 17: Code Review Report (batch C)

**Reviewed:** 2026-10-15T11:05:44Z
**Depth:** deep
**Files Reviewed:** 30
**Status:** issues_found

### Summary

Scope: the Phase 17 hunks in the shared `ai_kit_spec` modules (opencode 2.x image probe, runtimes
schema 3, `score_exact`, `local_gsd_core_roots`, the `opencode-api` provenance label), gate
registration, the reference doc, and the golden-plan test and fixtures.

What holds up:
- The ranker, catalog-validator and gsd_tools changes are additive. The only production consumer
  of `score_exact` is `catalog_adapter._purpose_scores_by_key`.
- Runtime code stays stdlib-only.
- The new test modules are in the generated `unit` group and the pre-commit `unittest` entry.
  `test_gate_scope` passes. ruff, pylint (10.00), pyright (0 errors) and vulture are clean on the
  scoped files.
- `tests.test_ai_kit_spec` and `tests.test_ai_kit_spec_gsd_tools` pass (701 tests).
- The golden tests stay byte-stable under different `PYTHONHASHSEED`, a symlinked `TMPDIR`,
  `LC_ALL=C` and a different `TZ`. The fixtures contain no absolute machine paths and no secrets.

The defects are concentrated in the new `probe_opencode_api_image_input`. I ran it live against
the installed opencode v2.0.29, cleaning up every server I started.
- **Security blocker:** the server runs in the shared temp dir, and opencode loads (and executes)
  project config from there and from every parent directory.
- **Silent failures:** the probe quietly returns `{}` under `http_proxy`, and stalls 15 s and
  returns `{}` when `OPENCODE_SERVER_PASSWORD` is set.
- **Process cleanup:** only the direct PID is signalled.

### Narrative Findings (AI reviewer)

### Critical Issues

### CR-01: The opencode probe executes untrusted config from the world-writable temp dir

**File:** `skills/ai-kit-spec-review/ai_kit_spec/detection.py:439-442` (docstring claim at 434)

**Issue:** `probe_opencode_api_image_input` starts `opencode serve` with
`cwd=tempfile.gettempdir()` (normally `/tmp`). The docstring calls this a "precaution (serve's
cwd effect is unverified)". It is verified now, and it is the opposite of a precaution: opencode
loads project config from its cwd and from every ancestor directory.

Live checks on opencode v2.0.29, each in a scratch `TMPDIR`:
1. An `opencode.json` containing `{"disabled_providers": ["openai"]}` placed in the probe's cwd
   changed the probe result from 45 models to 29 (no `openai/*`).
2. The same file placed in the cwd's **parent** also took effect. opencode walks up the tree, so a
   private `mkdtemp()` under `/tmp` would still pick up `/tmp/opencode.json`.
3. An `opencode.json` declaring `"mcp": {"x": {"type": "local", "command": ["touch", ".../mcp-ran"]}}`
   **ran the command** during the probe.

How it gets exploited:
- Any local user, or any sandboxed process allowed to write `/tmp` (codex's workspace-write
  sandbox allows `/tmp`), can create `/tmp/opencode.json`.
- The next `detect-runtimes` re-detect then runs the attacker's command outside any sandbox, as
  the user. Re-detects happen in ai-kit-spec-review cross-AI dispatch step 0.7, ai-kit-spec-config
  and the curated-config `inventory`; the schema bump to 3 forces one on every machine.

So the probe both executes code from the shared temp dir and lets another party change the
detection result.

**Fix:** Disable project config for the probe child and run it from a user-owned directory.
Verified live: with `OPENCODE_DISABLE_PROJECT_CONFIG=1` the planted `disabled_providers` file was
ignored (45 models, `openai/*` present) and the planted MCP command did **not** run.
```python
probe_env = {k: v for k, v in os.environ.items() if k != "OPENCODE_SERVER_PASSWORD"}  # WR-02
probe_env["OPENCODE_DISABLE_PROJECT_CONFIG"] = "1"  # never load opencode.json/.opencode from cwd or ancestors
probe_dir = os.path.join(cache_base(os.environ), "opencode-probe")  # user-owned ancestors only
os.makedirs(probe_dir, mode=0o700, exist_ok=True)
proc = popen_fn([binary, "serve", "--hostname", "127.0.0.1", "--port", "0"],
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
                cwd=probe_dir, env=probe_env, start_new_session=True)  # WR-03
```
Also correct the docstring and comment at lines 434/439. Add a unit test asserting the `env` flag
and that `cwd` is not `tempfile.gettempdir()`.

### Warnings

### WR-01: The loopback API call honours `http_proxy` and sends the Basic-auth password to the proxy

**File:** `skills/ai-kit-spec-review/ai_kit_spec/detection.py:453-457`

**Issue:** `urllib.request.urlopen` uses the default opener, whose `ProxyHandler` reads
`http_proxy`. With `no_proxy` unset, `proxy_bypass("127.0.0.1")` is `False`.

Verified live: with `http_proxy` pointed at a local listener, the listener received
`GET http://127.0.0.1:<port>/api/model` **with** an `Authorization: Basic ...` header, and the
probe returned `{}`.

On any machine with a proxy configured and no `no_proxy=127.0.0.1`:
- opencode 2.x image detection fails silently, so every opencode-only model reads as
  not vision-eligible (spurious vision warnings in `recommend`);
- the one-time server password goes to a third-party proxy. That contradicts T-17-01's
  "never leaves this process" intent.

**Fix:** Bypass proxies for this request:
```python
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
default_urlopen = opener.open  # use as urlopen_fn's default
```
Alternatively, use `http.client.HTTPConnection("127.0.0.1", int(port), timeout=10)` directly. Add
a test that sets `http_proxy` in the environment and asserts the request never reaches it.

### WR-02: `OPENCODE_SERVER_PASSWORD` in the environment makes every probe stall 15 s and fail silently

**File:** `skills/ai-kit-spec-review/ai_kit_spec/detection.py:397-415, 444-452`

**Issue:** When the user (or a host) exports `OPENCODE_SERVER_PASSWORD`, `opencode serve` prints
only `server listening on ...`, with no `server password` line (verified live).

`_read_opencode_banner` then keeps calling `readline()` on an idle server until the 15 s timer
kills it, and the probe returns `{}`. Measured: 0 entries after 15.0 s.

The snapshot records nothing about the failure: no `image_input`, no marker. Downstream code
therefore cannot tell "probe failed" from "no data". D-24 requires the 2.x gap to be labelled
(`unverified on opencode 2.x`), never silently absent.

**Fix:**
- Drop `OPENCODE_SERVER_PASSWORD` from the child env (see the CR-01 snippet), so opencode always
  prints a one-time password.
- Optionally return as soon as the port line arrives when no password line follows.
- When the 2.x probe yields `{}`, record a marker in the snapshot (for example
  `entry["image_input_probe"] = "failed"`) so the inventory can surface a warning instead of
  silently treating every opencode model as not vision-capable.

### WR-03: Only the direct child PID is signalled; grandchildren and wrapper launchers escape cleanup

**File:** `skills/ai-kit-spec-review/ai_kit_spec/detection.py:446, 463-469`

**Issue:** `opencode serve` spawns children: CR-01's live test showed it starting a local MCP
process. The 15 s timer and the `kill` fallback send SIGKILL to the direct PID only, which orphans
any child.

If `opencode` on PATH is a launcher that spawns the real binary rather than `exec`-ing it (for
example a Node shim from a package-manager install), two things go wrong:
- `terminate()` kills only the shim, and the real server keeps listening with no owner;
- in the timer path the surviving server still holds the stdout pipe, so `readline()` never sees
  EOF. That breaks the docstring's "readline cannot block forever" guarantee and hangs
  `detect-runtimes`.

This is not verified here: the local install is a native ELF, and the normal SIGTERM path left no
survivors in a live before/after process diff. The SIGKILL paths are untested: `FakePopen.stdout`
is a `StringIO` that hits EOF at once, so the timer branch is never exercised.

**Fix:** Start the server in its own process group and signal the group:
```python
proc = popen_fn([...], ..., start_new_session=True)
timer = threading.Timer(_OPENCODE_PROBE_DEADLINE_S, lambda: _killpg(proc, signal.SIGKILL))
## finally: _killpg(proc, signal.SIGTERM); wait(5); _killpg(proc, signal.SIGKILL)
def _killpg(proc, sig):
    with contextlib.suppress(OSError):
        os.killpg(proc.pid, sig)
```
Add a test whose fake stdout blocks (for example `os.pipe()` with the write end held open) to
prove the deadline path returns `{}` and kills the process.

### Info

### IN-01: The injection seam stops at `run_fn`, so stubbed callers can still spawn a real server

**File:** `skills/ai-kit-spec-review/ai_kit_spec/detection.py:618-619`, `skills/ai-kit-spec-review/ai_kit_spec/cli.py:391`

**Issue:** `build_runtimes_snapshot` and `_cmd_detect_runtimes` pass only `run_fn`.
`opencode_image_input_with_source` then falls back to the real `subprocess.Popen` and `urlopen`.
Any caller or test that stubs `run_fn` and answers `--version` with 2.x starts the real binary.
Tests work around this by patching the module global (`test_snapshot_records_image_input_source`).

**Fix:** Thread `popen_fn`/`urlopen_fn` through `build_runtimes_snapshot` and `CliDeps`, the same
way `run_fn` already is.

### IN-02: An unknown `image_input_source` is relabelled `opencode` instead of being dropped

**File:** `skills/ai-kit-spec-review/ai_kit_spec/catalog_build.py:253-254`

**Issue:** `source if source in ("opencode", "opencode-api") else "opencode"`:
- labels an unrecognized provenance as the 1.x `models --verbose` path, which claims more
  certainty than the data has (AGENTS.md certainty rule);
- re-hardcodes the valid-label set already in `model_catalog._VALID_IMAGE_INPUT_SOURCE` and
  `detection.OPENCODE_API_IMAGE_SOURCE`.

A missing source (schema-2 snapshots) correctly means `opencode`. An unknown one should skip the
value.

**Fix:** Default only when the key is absent, skip unknown labels, and reuse the shared constants.

### IN-03: Dead production wrapper and a stale snapshot docstring

**File:** `skills/ai-kit-spec-review/ai_kit_spec/detection.py:509-520, 596-599`

**Issue:**
- `detect_opencode_image_input` no longer has a production caller (only tests). The snapshot uses
  `opencode_image_input_with_source`.
- The `build_runtimes_snapshot` docstring's shape omits the `image_input` and
  `image_input_source` keys it now writes.

**Fix:** Remove the wrapper (point its tests at `opencode_image_input_with_source`), or note that
it is a test and back-compat seam. Add both keys to the docstring shape.

### IN-04: Leaked handles and a typo in the new probe code and tests

**File:** `skills/ai-kit-spec-review/ai_kit_spec/detection.py:446, 457`; `tests/test_ai_kit_spec.py:131, 10178`

**Issue:**
- The `urlopen` response and `proc.stdout` are never closed.
- `open(OPENDCODE_API_FIXTURE_PATH, "rb").read()` leaks a file handle. A `ResourceWarning` is
  confirmed under `python3 -X dev`.
- `OPENDCODE_API_FIXTURE_PATH` is a typo for `OPENCODE_...`.

**Fix:** Use `with urlopen_fn(...) as resp: body = resp.read()`, close `proc.stdout` in `finally`,
read the fixture with `Path(...).read_bytes()`, and rename the constant.

### IN-05: The `local_gsd_core_roots` single-source claim is contradicted twice

**File:** `skills/ai-kit-spec-review/ai_kit_spec/gsd_tools.py:83-89`

**Issue:** The docstring says "never duplicate this list elsewhere", but:
- the module docstring (lines 10-12) sanctions a drift-tested copy in `edge_floor.py`;
- `host.py:_local_roots` adds `<root>/.pi/gsd-core` outside the shared list.

As a result, on a pi host the inventory (`host.py`) and the v1 write path
(`gsd_catalog.resolve_gsd_tools_path` → `resolve_gsd_tools`) can resolve different gsd-core
installs. Valid keys would then be probed against one install and written through another.

**Fix:** Make the shared resolver host-aware (`.pi/gsd-core` first when `host == "pi"`) so both
paths agree, and reword the docstring to name the sanctioned `edge_floor.py` copy.

### IN-06: The fixture behind every golden plan is only re-validated on a machine-local gsd-core

**File:** `tests/test_curated_config_golden.py:171-186, 213-218`

**Issue:** `TestGoldenTables` runs only when the untracked, checkout-local `.claude/gsd-core` is
exactly `1.16.0`; otherwise it skips. In a fresh clone, or after the local gsd-core moves to
1.17, `gsd_tables_1_16.json` (the source of all 17 golden plans) is never checked against a real
gsd-core again, and only a skip message shows it. The class also spawns real `node` from the
`unit` tier.

**Fix:** Keep the pin, but make the version mismatch an explicit `skipTest` that names the found
version. Consider moving the class to the `e2e` group.

### IN-07: `mask_digest` drops coverage it does not need to; `UPDATE_GOLDEN` silently disables assertions

**File:** `tests/test_curated_config_golden.py:153-156, 164-167, 251`

**Issue:**
- The inventory handed to `recommend` is already canonical. Paths are replaced with `<scratch>`,
  and the inventories were byte-identical across hash seeds and `TMPDIR`. So
  `inventory_digest` is deterministic, and masking it removes the plan's only check of the
  inventory→digest link (R7).
- Separately, an `UPDATE_GOLDEN` left exported in a shell turns every golden assertion into a
  rewrite, including under `make validate`.

**Fix:** Pin the real digest, or document why it is masked. Have `check_golden` fail (or warn
loudly) when `UPDATE_GOLDEN` is set outside an explicit regeneration run.

### IN-08: Narrow path-hygiene check; real Artificial Analysis data committed as a fixture

**File:** `tests/test_curated_config_golden.py:501`; `tests/fixtures/curated_config_v2/model-catalog.json`

**Issue:**
- `BAD_FRAGMENTS` misses `/opt/`, `/usr/`, `/root/`, `/private/`, `/mnt/`, `/run/` and Windows
  drive paths. The fixtures are currently clean (spot-checked).
- The catalog fixture is a trimmed live catalog: real Artificial Analysis `scores` and
  `tokens_per_sec`, with no attribution. I have not verified whether AA's API terms permit
  redistributing that data in a committed fixture. The project already treats AA attribution as
  a hard requirement.

**Fix:** Use a generic absolute-path regex (`r'"/(?!/)[^"]*"'` or similar) instead of a
fragment list. Either replace the AA numbers with synthetic values or add attribution, after
checking AA's terms.

---

_Reviewed: 2026-10-15T11:05:44Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: deep_

# Ponytail review
## Ponytail review: Phase 17 (curated-config inventory + recommend)

Scope: `git diff e824d1a~1..HEAD -- skills/ Makefile .pre-commit-config.yaml` (3157+ / 33-).
Read-only. Required behavior from 17-SPEC R1-R13 and 17-CONTEXT D-01..D-32 is not flagged.
Load assumed: one person runs a CLI on one machine; no concurrency or scale concerns apply.

What this change does: It adds two subcommands to `ai-kit-gsd-curated-config`. `inventory`
reads the host, the project's gsd-core tables, the model catalog and the project config into a
single JSON snapshot. `recommend` is a pure function that turns that snapshot into a sorted,
explained `plan.json`. Small shared changes support them: `score_exact` in the ranker, the
opencode 2.x image probe, and `local_gsd_core_roots`.

No correctness, security or data-loss bugs found. Every finding is about lean code. Many
helpers and private NamedTuples exist only to satisfy pylint `max-args=5` / `max-locals=15`,
so each fix below has to stay inside those limits.

### Should fix

1. **Dead list in `used_tiers`** (`roles.py:273-281`)
   - What this is: It collects the tiers that some agent resolves to.
   - Problem: `ordered` is filled but never read. The return value uses `presets.TIERS` filtered
     by `seen`.
   - Fix: delete `ordered` and its `append`. Use
     `return tuple(t for t in presets.TIERS if t in seen)`, or build `seen` with a set
     comprehension.
   - Lines saved: ~3. Risk: none.

2. **Unused `host_name` parameter** (`inventory.py:123`, caller `inventory.py:360-362`)
   - What this is: `_probe_gsd_tables(core, host_name, project_dir, probe_keys, deps)`.
   - Problem: the body never reads `host_name`. pylint's `unused-argument` is disabled
     repo-wide, so no check catches it.
   - Fix: drop the parameter and the argument. The same fix also removes the second
     `resolve_node_binary` call: `_load_configs` already resolved `node_bin` (line 352), so
     pass it in instead of calling `which` again on line 124.
   - Lines saved: ~3. Risk: none (two test call sites may need the argument removed).

3. **`detect_opencode_image_input` has no production caller left** (`ai_kit_spec/detection.py:509-520`)
   - What this is: an old-name wrapper around `opencode_image_input_with_source` that drops the
     source.
   - Problem: `build_runtimes_snapshot` now calls `opencode_image_input_with_source`. Only
     tests (`tests/test_ai_kit_spec.py:9702-10197`) call the wrapper.
   - Fix: delete it and point those 5 tests at `opencode_image_input_with_source(...)[0]`, or at
     `detect_opencode_verbose_image_input` for the 1.x cases.
   - Lines saved: ~14. Risk: low; test-only callers.

4. **Duplicated pi note text** (`recommend.py:306-343`)
   - What this is: `_pi_slot` builds the same `{"kind": "pi", ...}` note in both branches,
     word for word.
   - Fix: build `note` once at the top. Return `[], [note]` or `[entry], [note]`.
   - Lines saved: ~9. Risk: none (the golden files pin the text).

5. **`_codex_empty_slots` re-derives `_slot_meta` and `_keep_why`** (`recommend.py:277-303`)
   - What this is: the codex "enumeration failed" path.
   - Problem: it recomputes `band`/`target` (the same as `_slot_meta`). It calls `_keep_why`,
     throws away its `why`, then rebuilds the same "; removes the existing override" suffix by
     hand.
   - Fix: use `meta = _slot_meta(ctx, tier)` for key and target. Give `_keep_why` a `why`
     prefix argument (or return only `op` plus a suffix) so the suffix logic lives in one place.
   - Lines saved: ~8. Risk: low (codex golden plans pin the output).

6. **Same sibling-missing message defined three times** (`host.py:18-20`, `catalog_adapter.py:21-23`, `cli.py:~55`)
   - Fix: define one `SIBLING_MISSING` constant next to `gsd_catalog.load_ai_kit_spec_module`
     and import it in all three files.
   - Lines saved: ~6. Risk: none.

7. **`_KNOWN_VENDORS` copies the vendor table** (`catalog_adapter.py:30-32`)
   - What this is: the allow-list for the catalog-provider fallback (D-14).
   - Problem: it is exactly the set of vendor values in
     `ai_kit_spec/vendor.py:_MODEL_VENDOR_PREFIXES`. If a vendor is added there, this copy goes
     stale without any error.
   - Fix: export `KNOWN_VENDORS = frozenset(v for _, v in _MODEL_VENDOR_PREFIXES)` from
     `vendor.py` and read it through the already-loaded `vendor_mod`.
   - Lines saved: ~2, plus no drift. Risk: low.

8. **Two copies of the subprocess call** (`catalog_adapter.py:179-212`)
   - What this is: `_run_subprocess` and `_run_fetch_json` repeat the same `run_fn(...)` call,
     kwargs and `except`.
   - Fix: keep one `_run(run_fn, argv, env)` that returns the result, or `None` on
     OSError/timeout. `detect` checks `returncode == 0` and `fetch` parses the JSON.
   - Lines saved: ~10. Risk: none.

9. **Hand-rolled `type().__name__` and dead schema branches** (`plan_io.py:36-62`, `108-158`)
   - `_type_of` (12 lines) returns exactly `type(value).__name__` for every type JSON can
     produce. Delete it.
   - In `_ill`, the `"str-or-null"` branch and the bool-vs-int guard are never reached: callers
     only pass `str`, `dict` and `list`. Delete both (~5 lines).
   - `_conflict_item_problem` has four checks that return the same string. Collapse them into one
     boolean expression (~5 lines).
   - `_validate_gsd_core` checks `version` in a separate block that matches the `path`/`scope`
     loop. Add it to the loop (~3 lines).
   - `_validate_conflicts` runs separately in `load_inventory`. Add it to the problem list in
     `_validate_inventory` (~4 lines).
   - Lines saved: ~29 in total. Risk: low. This is validation at a trust boundary, so keep every
     check; only duplicate code goes.

### Nice to have

10. **Same "nearest effort" walk written twice** (`roles.py:58-70` `clamp_effort`, `roles.py:120-146` `pick_variant`)
    - Both do: exact match, else nearest lower on `EFFORT_LADDER`, else nearest higher.
    - Fix: one `_nearest_effort(target, tokens) -> (token, rule) | None` used by both. Also,
      `_ladder_index` (4 lines) can be
      `EFFORT_LADDER.index(t) if t in EFFORT_LADDER else -1`.
    - Also: `pick_variant`'s last fallback (lines 144-146) only runs when the target is not on
      the ladder, which no preset produces. If it ever runs, it labels a non-bare variant as
      `"bare"`.
    - Lines saved: ~12. Risk: low (effort tests cover both paths).

11. **Two copies of the managed-key union** (`presets.py:141-151` vs `181-198`)
    - `closed_key_set` rebuilds the same union of `PRESETS`, `CONDITIONAL_KEYS` and
      `CROSS_AI_KEYS` that `MANAGED_KEYS` already holds.
    - Fix: start with `keys = set(MANAGED_KEYS) | {"runtime", "resolve_model_ids"}`.
    - Lines saved: ~4. Risk: none.

12. **Score-axis count and score dict computed separately** (`catalog_adapter.py:372-387`)
    - `_score_axes(e)` always equals `len(_entry_scores(e))`. Keep `_entry_scores` and use
      `len(...)` for the count.
    - The `seen` set in `_scoring_pool` (lines 319-327) is also redundant: the loop already runs
      over `sorted(set(...))`.
    - `_candidate_vendor`'s `is_router` check (lines 413-414) repeats the guard its only caller
      already applies (line 347).
    - Lines saved: ~10. Risk: none.

13. **Refresh-path plumbing: four hops and three single-use NamedTuples** (`catalog_adapter.py:44-152`)
    - The chain `refresh_catalog → _refresh_with_stack → _catalog_state_from_cache →
      _read_cache` exists only to pass arguments along, through `_RefreshJob` and `_CacheRead`.
    - Fix: split by job into two functions: (a) run the two refresh subprocesses, (b) read the
      cache and classify the state. Keep `_RefreshPaths`. This drops `_RefreshJob`, `_CacheRead`
      and two hops.
    - Lines saved: ~25. Risk: medium. It must stay within pylint `max-locals=15`, so check it
      with `make pylint`.

14. **Inventory plumbing: a 10-field snapshot tuple** (`inventory.py:49-66`, `351-407`)
    - `_ResolvedHost`, `_InventorySnapshot` and `_load_configs` (which returns a 6-tuple) only
      move values from one function to the next.
    - Fix: have `_load_configs` return a partial inventory dict plus a warnings list. Have
      `_assemble_inventory` merge the dicts. Both NamedTuples go away.
    - Lines saved: ~25. Risk: medium (pylint locals limit; many tests patch these internals).

15. **`gsd_tools` module re-loaded and None-checked four times** (`host.py:58-147`)
    - `_local_roots`, `_gsd_tools_candidates`, `_worktree_warning` and `resolve_gsd_core` each
      call `load_ai_kit_spec_module("gsd_tools")` and check for `None`. `resolve_gsd_core`
      already guarantees it is loaded, so pass the module down.
    - `_worktree_warning` returns a `{root}` template that its caller then formats. Pass
      `install_root` in and return the final string.
    - Lines saved: ~12. Risk: low.

16. **`_item(kind, scope, key, ...)`: `key` always equals `kind`** (`inventory.py:155-288`)
    - All 7 call sites pass the same string twice.
    - Fix: drop the parameter and set `"key": kind` inside. The emitted shape is unchanged.
    - Lines saved: ~7. The "inert: gsd-tools ignores ... (#3532)" string is also duplicated
      (lines 196, 229); make it one constant.
    - Risk: none.

17. **`claude_md_path_configured` has no reader** (`project_facts.py:72,82`, `inventory.py:314-316`)
    - The field only repeats whether `existing_config.values.claude_md_path` is a string. No code
      or test reads it.
    - Fix: drop the field and the `configured_claude_md_path` parameter. 17-07-PLAN listed it,
      so confirm with uz first.
    - Lines saved: ~4. Risk: low.

18. **Layer pipeline with 4× `del prior_entries`** (`recommend.py:126-150,346-348,717-720,852-894`)
    - Only `_specialist_layer` and `_reconcile_layer` use `prior_entries`. The uniform signature
      exists only so `_LAYERS` can loop, and the duplicate-key check is O(n²).
    - Fix: either keep the pipeline and drop the `del` lines by giving the parameter a leading
      underscore, or call the 6 layers in order in `build_plan` and run one `Counter` duplicate
      check at the end.
    - Lines saved: ~8. Risk: low.

19. **Small repeats in `recommend.py`**
    - `_slot_layer` (line 355) inlines the exact `_host_cands` comprehension. Call
      `_host_cands(ctx)`.
    - `_parse_tables_output` (`gsd_catalog.py:152-189`) re-checks `isinstance(accepted, list)`
      after `key_lists_ok` (it only narrows types for pyright). Early returns would remove the
      nested `if` and that re-check.
    - Lines saved: ~8. Risk: none.

Not flagged, on purpose:
- The private NamedTuples in `recommend.py` (`_PickRequest`, `_CounterpartPick`, `_VisionPick`,
  and so on) exist to meet the repo-wide pylint max-args/max-locals rules. Inlining them would
  break those rules.
- `_merge_layers`' duplicate-key raise is the R11 ordering backstop.
- Review-purpose routers not winning a slot is D-04 (deferred to Phase 18).
- Tests: about 4.3k lines plus fixtures for 13 requirements and 15 golden plans. That is large,
  but not grossly over-built.

Verdict: Ship. No bug blocks it. Do 1-9 in one cleanup commit when convenient.
Lean: about -200 lines possible (about -90 from 1-9, which carry no risk to behavior).
Not checked: I did not run `make test`/`make validate` after the proposed cuts, so the
pylint-limit risk on 13-14 is estimated, not measured. I did not re-derive the golden-plan
values against live gsd-core.
