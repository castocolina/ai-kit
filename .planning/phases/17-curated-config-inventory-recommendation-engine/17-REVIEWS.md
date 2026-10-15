---
phase: 17
reviewers: [opencode-plan-review]
reviewed_at: 2026-10-15T08:53:43Z
plans_reviewed: [17-01-PLAN.md, 17-02-PLAN.md, 17-03-PLAN.md, 17-04-PLAN.md, 17-05-PLAN.md, 17-06-PLAN.md, 17-07-PLAN.md, 17-08-PLAN.md, 17-09-PLAN.md]
models:
  opencode-plan-review: "router-env/my-plan-review"
model_sources:
  opencode-plan-review: "pinned"
---

# Cross-AI Plan Review — Phase 17

<!-- gsd:plan-revision-conflicts:begin -->
## Plan-Revision Conflicts
<!-- gsd:plan-revision-conflicts:end -->

## OpenCode Review (opencode-plan-review)

I'll review these 9 plans against the actual repository. Let me start by verifying the phase artifacts and key source files.
Codegraph is available. Let me read the key source files to verify plan claims with exact line numbers.
Verified `detection.py` claims. Now the ranker, catalog_build, model_catalog, gsd_tools, and vendor modules.
Now the curated-config skill's existing modules.
Now let me check the SPEC file that 17-09 Task 3 proposes to amend.
Let me verify a key live claim — that gsd-core 1.16's `isValidConfigKey` accepts every key the plans will propose (`closed_key_set`), plus the Makefile targets.
Let me check the pylint config for unused-argument handling (17-02's `_cmd_recommend` won't use `run_fn`), and the RESEARCH doc's claims about test counts.
One last verification round — the main checkout's config claim and a couple of remaining plan claims.
I've completed verification against the repository. Here is my review.

---

# Phase 17 Plan Review — Curated-Config Inventory & Recommendation Engine

**Methodology:** Every load-bearing claim was checked against the actual checkout (`<repo root>`): the gsd-core 1.16 tables were queried live via `node`, `isValidConfigKey` was probed live with the plans' exact `closed_key_set` key list, and all cited file/line locations in `ai_kit_spec`, `ai_kit_gsd_curated_config`, `tests/`, and the phase docs were opened. All 9 plan files exist on disk and match the reviewed content.

**Key live verifications performed (not taken from the plans):**
- `RUNTIME_PROFILE_MAP` (live 1.16): codex = sol/terra/luna with efforts xhigh/medium/medium, opencode = `anthropic/*`, pi = claude ids, **no `cursor` key** — matches 17-02/17-04 fixtures exactly.
- `MODEL_PROFILES` for all 11 agents named in 17-02's `TABLES` and 17-06's interfaces match byte for byte; tier counts (22/13, 2/31/2, 12/23, 9/13/13) match CONTEXT.
- `isValidConfigKey` live probe over the 47-key `closed_key_set` union: **`rejected: []`** — including `workflow.cross_ai_command`, `review.default_reviewers`, `runtime`, `resolve_model_ids`. Also confirmed: the five `model_policy` leaves and `model_policy.runtime_tiers.<rt>.<tier>` are accepted, the whole `model_policy` object is **rejected** — exactly D-08's per-leaf amendment.
- `EFFORT_LADDER` at `.claude/gsd-core/bin/lib/model-catalog.cjs:134` matches `roles.EFFORT_LADDER`; `_MODEL_TIER_SUFFIXES` (`vendor.py:11`) indeed lacks `minimal`/`ultra`, making 17-04's `shortcut:` comment accurate.

---

## 17-01

**Summary.** A well-scoped shared-infrastructure plan: restores the opencode `image_input` source on 2.x via a private `opencode serve` + `GET /api/model` probe (D-24/D-32), adds the unrounded `score_exact` (D-15), and fixes the stale `cli-model-selection.md` reference. Every line-number claim checked out: `RUNTIMES_SCHEMA_VERSION = 2` at `skills/ai-kit-spec-review/ai_kit_spec/detection.py:16`, `detect_opencode_image_input` at `:325`, `build_runtimes_snapshot` calling it at `:439`, the hardcoded `image_input_source = "opencode"` at `skills/ai-kit-spec-review/ai_kit_spec/catalog_build.py:269`, `_VALID_IMAGE_INPUT_SOURCE` at `skills/ai-kit-spec-review/ai_kit_spec/model_catalog.py:49`, `return {**entry, "score": round(score, 1)}` at `skills/ai-kit-spec-review/ai_kit_spec/model_ranker.py:250` with the rounded sort at `:277`, the pinned `2` literals at `tests/test_ai_kit_spec.py:2220` and `:2265`, and the exact stale text at `skills/ai-kit-spec-config/references/cli-model-selection.md:159`.

**Strengths.**
- The probe design is defensive and correct against the spike (`17-SPIKE-opencode-image-input.md` confirms endpoint, basic auth, and the four-fixture sample matches the expected image booleans): `--port 0`, loopback bind, token never printed, `try/finally` terminate→wait→kill, daemon `threading.Timer` so a silent server can't block `readline`, `cwd=tempfile.gettempdir()` labeled as an unverified-effect precaution (T-17-33).
- Version gate uses `fullmatch` with a dotted-triple pattern, so model listings (`openai/gpt-5.6-sol`) can't false-match — the acceptance criterion tests exactly this.
- Test-seam discipline is unusually careful: probe-level tests inject fake `Popen`/`urlopen_fn`; snapshot-level 2.x tests patch `detection.probe_opencode_api_image_input` by module-level name (a real Python patching seam). No test spawns a real opencode.
- `score_exact` is additive; the existing sort stays on rounded `score` (`model_ranker.py:277`), so no existing caller changes behavior.
- Schema bump blast radius is correctly scoped: `catalog_schema_is_current` tests (`tests/test_ai_kit_spec.py:8540`) use the same `{"schema_version": 2}, {3}` tuple but belong to the *catalog* schema (unchanged), and the plan explicitly says not to touch them.

**Concerns.**
- **MEDIUM — test-churn risk in a 10,799-line file.** `tests/test_ai_kit_spec.py` contains 39 `schema_version.*2` occurrences mixing runtimes and catalog caches. The plan's mitigation ("run the suite, update only the runtimes snapshots of tests that now fail") is workable but error-prone for a cheap cross-AI executor; a wrong edit silently weakens a catalog-schema test. Naming the specific at-risk tests (`test_fresh_current_cache_is_skipped` at `:2267` seeds a hardcoded `2`) would remove the ambiguity.
- **MEDIUM — no automated live verification of the 2.x probe.** The real `opencode serve` path is only exercised manually (VALIDATION.md). An opencode point release that moves the password line or changes `/api/model` shape fails closed to `{}` (correct), but nothing in `make test` would notice the regression — the restored capability silently reverts. This is accepted by D-24's fail-closed rule, but worth stating in the SUMMARY.
- **LOW — pre-existing merge semantics cap the fix's reach.** `_apply_runtime_meta` (`catalog_build.py:266-269`) only lets runtime metadata win when the entry lacks a bool `image_input` (`runtime_wins_image_input=False` default), so models that models.dev already covers keep the models.dev value. The plan's own truth correctly scopes to "opencode-only models," so this is accurate — just easy to over-expect.
- **LOW — "daemon `threading.Timer`"** requires explicitly setting `.daemon = True` on the Timer object before `start()`; the plan doesn't spell it out. Since `finally` always cancels, the worst case is bounded, but the literal reading produces a non-daemon timer.

**Suggestions.**
- In Task 2 step 5, enumerate the specific tests that seed "current" runtimes caches with a literal `2` (at minimum `tests/test_ai_kit_spec.py:2267-2270`) instead of relying on failure-driven discovery.
- Spell out `timer.daemon = True` in the Task 1 action.
- Consider one assertion that the probe is skipped when the version call itself fails (`OSError → None → 1.x path`) — the behavior table covers the rc-1 case but not spawn failure of `--version`.

**Risk Assessment.** **MEDIUM.** Correct, live-verified design with excellent hygiene; the residual risk is concentrated in test-suite churn and the untestable-in-CI live probe, both bounded by fail-closed paths.

---

## 17-02

**Summary.** The foundational tracer for the pure `recommend` engine — `presets.py`/`plan_io.py`/`recommend.py`, the CLI subcommand, the plan.json contract, and the purity guarantee. This is the contract five later plans build on, and it is internally consistent with all of them: the `_LAYERS` ordering it establishes (`_preset_layer, _tier_layer`, then `_cross_ai_layer` appended) composes correctly with 17-04's "insert `_slot_layer` right after `_tier_layer`", 17-06's append, and 17-08's append-last. Verified anchors: `VALID_MODEL_PROFILES` at `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cli.py:23`, `_build_parser`/`_COMMAND_HANDLERS`/`main` at `:432-505` with the `handler(args, which_fn, run_fn, env_fn)` dispatch the new handler matches; `load_gsd_tools` shim at `gsd_catalog.py:21-35` generalizes cleanly to `load_ai_kit_spec_module`; `cache_write_text` (mkstemp + `os.replace`) at `skills/ai-kit-spec-review/ai_kit_spec/cache.py:27-43`. `pyproject.toml:85` disables pylint `unused-argument`, so `_cmd_recommend`'s unused `run_fn` is fine.

**Strengths.**
- The `flatten_config` stop rules (`model_profile_overrides.<rt>.<tier>` and `model_policy.runtime_tiers.<rt>.<tier>` as single leaves) are not guesses — I re-probed live: the runtime_tiers leaf is accepted and `.model`/`.reasoning_effort` below it would be rejected. The tracer behavior spells out both flattening cases exactly.
- Purity is enforced twice (AST import guard plus the patch test making `subprocess/socket/time/open` raise), and the scoring-in-inventory decision correctly follows from `load_ranking_weights` reading `references/ranking-weights.toml` (`model_ranker.py:13-14`).
- Fail-closed inventory loading (exact `schema_version` match, older *or* newer refused) is a deliberate, documented deviation from the `>=` cache convention — correctly reasoned in the research's OQ4.
- `python3 tools/gen_test_groups.py` + `test_gate_scope` registration handles Pitfall 8; `tests/test_gate_scope.py:351` (`test_generated_listings_name_every_discovered_module`) is real and would catch a miss.

**Concerns.**
- **MEDIUM — the inventory contract is only provably joinable at 17-07.** `load_inventory` requires `candidates`, `project`, `existing_config`, `global_defaults`, `conflicts`, but 17-03's inventory emits only host/gsd-core/warnings and 17-05 adds candidates/catalog — until 17-07 completes the document, every *real* inventory fails `load_inventory`. No intermediate plan runs the join, so a contract drift (e.g., a field renamed between 17-02's `<interfaces>` and 17-07's writer) would surface only in wave 7. The verbatim contract duplication across the plans mitigates this, and 17-07 Task 1 proves the join, but the late feedback point is real.
- **LOW — `_drop_rejected` interacts with `op: unset` entries.** 17-08 later relies on rejected *unset* keys being dropped with a note (Task 3 behavior). That works only because `_drop_rejected` filters all entries, which 17-02 states for set entries; an executor could narrowly implement it for `op: set`. One clause ("including unsets") would remove the ambiguity.
- **LOW — `write_plan` raising `OSError("ai-kit-spec-review sibling … not installed")`** overloads `OSError` for a non-OS condition. It routes to exit 2 correctly; a dedicated exception would be cleaner but this is cosmetic.

**Suggestions.**
- State explicitly that `_drop_rejected` applies to every entry regardless of `op`.
- Have Task 3's `TestInventoryValidation` include one inventory whose `conflicts` items are valid but whose `candidates`/`project` are only the contract minimum — pinning that the *real* 17-03 inventory (which lacks those keys) is expected to fail until 17-07, so a future reader isn't surprised.

**Risk Assessment.** **MEDIUM.** The plan itself is sound and unusually well-anchored; the risk is positional — it defines a contract whose full realization is proven five waves later.

---

## 17-03

**Summary.** The read-only inventory tracer: host detection, project-local-first gsd-core resolution with scope labeling (D-11 including the pi amendment), and the single node call for tables + `isValidConfigKey` probing (D-09/D-31). Verified: `gsd_core_roots` hand-lists exactly the three project-local roots at `skills/ai-kit-spec-review/ai_kit_spec/gsd_tools.py:86-87` (so the `local_gsd_core_roots` extraction preserves output), `gsd_tools_candidates` uses `which_fn("gsd_run", path=env["PATH"])` with a `path=` kwarg at `:99` (the plan's warning about not injecting a name-only `which_fn` is correct and shows real understanding), `config_path` at `:224-239`, `gsd_core_version` at `:242-251`, `isValidConfigKey(keyPath, cwd)` at `.claude/gsd-core/bin/lib/config-schema.cjs:65`, and `_AGENT_CATALOG_QUERY_SCRIPT`'s argv/catch→`null` convention at `gsd_catalog.py:73-78` is the stated template.

**Strengths.**
- The `real_gsd_run(child_env, node_bin, fallback=None)` allow-list is an excellent harness investment: `tests/test_ai_kit_gsd_curated_config.py:82-89` confirms `run_cli` really does send every argv to a real subprocess, so the plan's "never use `run_cli`" rule and the AssertionError-on-unexpected-argv design (T-17-32) preempt later plans (17-05) silently shelling out from `make test`. The non-vacuity test (fallback routing) is specified.
- Scope semantics match GSD's launcher order; the pi `.pi/gsd-core` deviation is labeled as a deliberate departure with its decision trail, and the worktree warning uses `--path-format=absolute --git-common-dir` (a git argv that `real_gsd_run` correctly allow-lists).
- Probe-failure handling (node prints `null` → exit 2 naming install path + version + `isValidConfigKey unavailable`) implements the research's OQ6 resolution exactly, and `_parse_tables_output` rejects partial shapes whole.
- The real-gsd acceptance (all five hosts, `valid_keys.rejected == []` on the checkout's 1.16.0) is runnable here — node v24.21.0 and gsd-core 1.16.0 are both present, and my independent probe confirms every `closed_key_set` key is accepted.

**Concerns.**
- **LOW — `make_gsd_install(install_root, …)` vs the existing `_make_fake_install(root)`** (`tests/test_ai_kit_gsd_curated_config.py:111`) take different conventions (install root vs parent). 17-09 calls `make_gsd_install(<project>/.claude/gsd-core)`, which pins the intent, but a one-line note in 17-03 would prevent an executor moment of confusion.
- **LOW — the tables query drops `CODEX_MODEL_EFFORT`/`VALID_PROFILES`** that the research's Pattern 1 script dumps. This is a defensible minimization (17-04 reads native efforts from `runtime_profile_map` entries directly, verified live: codex entries carry `reasoning_effort`), but the deviation from the research pattern is silent.
- **LOW — `--host` choices exclude `unknown`** and `detect_host` returns a helpful error; fine, but `host_source: "flag"` vs `"detected"` wording should also cover the flag value equal to a detected value — cosmetic.

**Suggestions.** None blocking. Document the `make_gsd_install` root convention inline; optionally note why the node dump is narrower than RESEARCH Pattern 1.

**Risk Assessment.** **MEDIUM** — new resolver semantics (worktree/pi edges) but every mechanism was verified live or against source, and failure paths fail closed.

---

## 17-04

**Summary.** The most algorithmically dense plan — the tier→model layer with native-keep, family-based price ceiling, effort-variant selection, deterministic ties, and the full INV-02 fallback ladder. The math checks out against the fixtures: for the CODEX fixture, family prices [0.2, 2, 2, 4, 10] give nearest-rank 4 at q=0.75 (gpt-5.6-sol at exactly the ceiling is kept — the R9 boundary) and 2 at q=0.40 (opus overridden). The opencode fixture's standard ceiling computes to 2 over families [0, 0.2, 2, 2, 4]. The tier tables and `agent_tier` semantics were verified live against gsd-core 1.16, including the budget-profile subtlety that gsd-planner resolves to sonnet (W2's counterpart-reference correctness depends on it).

**Strengths.**
- `tie_key` tests `price is None` explicitly (price 0 sorts first) and the full-precision `score_exact` separation (1e-9) closes the D-06 hole the rounded score would leave.
- `pick_variant`'s family+tier-effort rule directly neutralizes the live effort-variant economics problem (higher AA score at the same price for `-max`), and the golden assertion "no mechanical slot carries `-max`/`-xhigh`" plus the cursor-haiku `-low` test pin it.
- The `-fast` exclusion, cap-never-empties fallback with explicit `why`, mechanical-floor `needs_choice` ("no eligible mechanical candidate", distinct from "no scores"), codex enumeration-failure keep-with-label, and the pi opt-in slot together cover the R9/R4/INV-02 edge grid the SPEC demands — each traced to a locked decision (D-03/D-05/D-12/D-22/D-25).
- Updating 17-02's `TestCrossAi` MVP case when narrowing the cheap-candidate default is exactly the right cross-plan hygiene.
- The `shortcut:` comment on `pick_variant` (family grouping doesn't strip `minimal`/`ultra`) is verified true against `vendor.py:11-13` and honestly labeled per the house style.

**Concerns.**
- **MEDIUM — `purpose_scores` pool semantics are load-bearing and only implicit.** `score_candidates` normalizes price/speed/context *relative to the call's entries* (`model_ranker.py:260-262`). 17-05 fixes the pool (all scored candidate entries, A9), but 17-04's tests hand-set `purpose_scores`, so a pool-definition mistake in 17-05 would not be caught by 17-04's tests — only by 17-05 Task 3's direct `score_candidates` comparison. That backstop exists; the coupling is just worth flagging since 17-04 lands first.
- **LOW — the MVP exec-default narrowing** introduces `cheap_other_cli` with the MVP ceiling computed over *host* families only; a host with zero priced families returns None (no default) — correct per the acceptance (`cheap_other_cli([], 0.4)` → None) but means MVP exec defaults rarely fire on unpriced hosts. Intended per spec §5's "when a cheap candidate exists."
- **LOW — kept-slot `op: unset` when an existing override exists** (D-18) means "keep" sometimes produces an entry with `op: unset` and `source: native`. 17-06's `_slot_models` handles it, but this dual meaning of `source: native` (keep and unset) is the subtlest part of the entry schema; the truth text does state it.

**Suggestions.** Add one sentence in 17-04's interfaces noting that `purpose_scores` values are pool-relative and the pool is fixed by 17-05 (A9), so a 17-05 executor knows not to "fix" a 17-04 expectation.

**Risk Assessment.** **MEDIUM.** Dense decision logic, but every rule is pinned by a named test, the fixtures' arithmetic was independently recomputed, and the layer composes with 17-02's engine as specified.

---

## 17-05

**Summary.** The catalog adapter: refresh state machine through the real `ai-kit-spec.py` subprocesses, and the candidate join producing scored (runtime, model) pairs with `fast_twin_of`/family/strict vendor/router confirmation/`purpose_scores`. All cited CLI mechanics verified: `_cmd_detect_runtimes` prints `{}` on fresh+schema-current and has `--save` (`skills/ai-kit-spec-review/ai_kit_spec/cli.py:384-396`), `skip_fetch`/`models_dev_ok`/`artificial_analysis_ok` result keys at `:474-483`, the fetch argparse flags (`--runtimes-json`, `--catalog-path`, `--cwd`, `--if-stale`) at `:140-161`, and `_runtime_meta_from_snapshot` reading `clis.opencode.image_input` at `skills/ai-kit-spec-review/ai_kit_spec/catalog_build.py:240-248`.

**Strengths.**
- The state machine maps truthfully onto the actual subprocess contract: "fresh when `fetch_skipped` or a source ok" matches `cli.py:431-437` (a skip prints all-false ok flags), and the AA-failed/models.dev-ok warning matches `aa_ok = aa_fetch_ok and bool(api_key)` at `:441`.
- Scoring lives here for the right reason (REC-01 purity, `ranking-weights.toml` file read), one normalization pool documented, and the mechanical-floor drop is preserved by storing only what `score_candidates` returned.
- Router handling is exactly D-04/D-12/D-14: `vendor: null` for routers, `router_confirmed` requiring recorded user confirmation (`_VALID_NAME_DECLARED_PURPOSE` at `model_catalog.py:48` verified), and `CANDIDATE_HEURISTIC_FIELDS` labeling satisfies the AGENTS.md certainty rule.
- The update to 17-03's `TestRealGsdInventory` (fake `fallback` for the two ai-kit-spec.py calls, asserted recorded) keeps the no-real-CLI invariant from `make test` intact.

**Concerns.**
- **MEDIUM — `detect-runtimes` failure and `--refresh` interplay.** With `--refresh`, `detect-runtimes --save` writes a *new* snapshot; if that subprocess fails (rc≠0), the plan appends a warning and "the fetch still runs" — against the *cached* runtimes. Correct, but the plan doesn't state that `--refresh` with a failed detect silently refreshes the catalog from stale runtimes. A one-line `why`/warning in that case would honor the honesty rule.
- **LOW — prices-without-scores catalog**: `scored` false is computed from "any entry with a numeric score axis" over the *whole* catalog, but candidates' eligibility is per-candidate. The two are consistent for the D-25 path (candidates get `{}`), just easy to conflate in review.
- **LOW — duplicate-join determinism** ("first, smallest key wins") is pinned by a test; good, since live cursor data really has reseller duplicates.

**Suggestions.** Add the stale-runtimes-on-refresh warning case to `TestCatalogStates`.

**Risk Assessment.** **MEDIUM** — external-subprocess orchestration with many states, but every state transition was checked against the real CLI code paths and each has a fixture test.

---

## 17-06

**Summary.** The specialist layer: at most seven `model_overrides` written only when the agent's resolved slot fails its rule, with counterpart/vision/frontend/execution purposes, single-provider notes, claude aliases, and the pi prohibition. The `<interfaces>` tier table matches live `MODEL_PROFILES` for all seven specialists (verified individually), and the two marquee test fixtures are internally coherent — I hand-traced the purpose-pin fixture (glm wins all slots; plan-checker/code-reviewer → sol by `review`; vision trio → grok by `general`) and the W2 budget case (planner=sonnet=terra → counterpart=grok), and both produce exactly the asserted outcomes under the stated rules.

**Strengths.**
- The W2 fix is genuinely important and correctly implemented: comparing the plan-checker against `roles.agent_tier("gsd-planner", …)` (sonnet under budget) instead of "the opus slot" — live-verified (`gsd-planner` budget = sonnet) — with a test that would fail under the wrong reading.
- Purposes are pinned per specialist family (counterparts by `review`, vision/frontend by `general`, execution by `execution`) with a fixture where the best `review` and `general` candidates differ — this closes the most likely silent bug in this layer.
- Routers as `vendor: null` (never an automatic counterpart) plus the `router_unconfirmed` note (both live routers are unconfirmed, per the research) correctly keeps D-04's exception from firing on unverified data.
- The `CLAUDE_ALIASES` drift guard against `detection.CLAUDE_MODEL_ALIASES` (exists at `detection.py:26`) keeps the copy honest while `roles.py` stays import-pure.

**Concerns.**
- **MEDIUM — `_slot_models` couples 17-06 to 17-04's entry shapes.** Reading "keep/unset native → native model; set → value or value['model']; needs_choice → None; claude → alias" duplicates knowledge of every slot-entry variant in a second module. If 17-04's tracer changes an entry shape, 17-06 breaks visibly (tests cover it), but the coupling is the plan's main maintenance hazard.
- **LOW — codex `model_overrides` values are bare ids** while codex `model_profile_overrides` values are `{model, reasoning_effort}` objects. Whether gsd-core 1.16 accepts the richer form for per-agent overrides on codex isn't verified here (the research verified the tier-slot object form only). The bare id is the safe choice and effort goes through `effort.agent_overrides` anyway; just an untested surface.
- **LOW — `_facts` claude-alias aggregation** ("vendor only if exactly one") is sound; no issue, just noting the all/none image logic is tested only via the property tests.

**Suggestions.** If convenient, add a live probe (17-09-style, skipUnless) asserting `config-set model_overrides.gsd-executor <bare-codex-id>` round-trips on the real gsd-core, closing the codex-override-format question for Phase 18's apply.

**Risk Assessment.** **MEDIUM** — the rules are decision-dense but each has a dedicated fixture whose expected outcome I independently derived from the live tables; the residual risk is the cross-module coupling to slot-entry shapes.

---

## 17-07

**Summary.** Completes the inventory: project facts (reusing `frontend_detect`/`claude_md_detect` — `_CANDIDATE_FILENAMES` verified at `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/claude_md_detect.py:12`, and the `package_json_deps` extraction faithfully mirrors `_package_json_signals_frontend` at `frontend_detect.py:39-56`), allow-listed config reads, the D-10/D-21/D-31 conflict matrix, and the read-only proof (byte-identical tree under chmod 0555/0444, with fakes and the real gsd-core). The end-to-end inventory→`recommend` join is proven here, closing 17-02's contract loop.

**Strengths.**
- The conflict matrix is the phase's most safety-relevant logic and every row is live-verified in the research (Branch C/D, `config-new-project` copying `model_policy` + `resolve_model_ids` but not `runtime`); the plan's allow-lists (`PROJECT_CONFIG_KEYS`/`GLOBAL_CONFIG_KEYS`) directly neutralize T-17-24, and the fixture plants `secret_token`/`brave_api_key` to prove it.
- `_probe_keys` extending the `isValidConfigKey` set with existing-config leaves and global `model_policy` leaves is the detail that makes 17-08's unsets droppable-but-not-blindly — and my live probe confirms those leaf keys are all accepted on 1.16.
- The read-only test design (path+sha256 snapshot, chmod, cleanup) is the strongest possible in-unit proof of the phase's core value ("never corrupt uz's config").

**Concerns.**
- **LOW — `detect_db_present`'s heuristics are invented here** (schema.sql/migrations/db-migrate/dependency set) with `heuristic_fields: ["db", "frontend"]` labeling. Nothing consumes `db` in Phase 17 (INV-01 just wants it reported), so the risk is only a mislabeled fact; the labeling rule covers it.
- **LOW — research-doc staleness:** the CONTEXT/RESEARCH claim this repo's `.planning/config.json` holds `claude_md_path: ./CLAUDE.md` is true in the main checkout (`:86`) but this worktree already says `./AGENTS.md`. No plan dependency (fixtures are synthetic), but the docs' "current machine state" framing should not be trusted blindly at execution time.
- **LOW — `TestReadOnlyRealGsd` runs the real `config-path` node call against a read-only project dir** — `config-path` is read-only in practice (verified in the research); if a future gsd-core version wrote anything there, the test would catch it (good) rather than corrupt (also good).

**Suggestions.** None material. Optionally note in the SUMMARY that `db` detection is informational-only and unconsumed until Phase 18.

**Risk Assessment.** **LOW-MEDIUM.** Mostly I/O orchestration over live-verified behavior, with the read-only guarantee tested at the strongest practical level.

---

## 17-08

**Summary.** The reconcile layer: managed-family leftover unsets, per-leaf `model_policy` unsets (the whole-object rejection is real — I confirmed live that `isValidConfigKey("model_policy")` is false while every leaf is true), `runtime` per D-23/D-30, latent global conflicts per D-31, and malformed-conflicts fail-closed validation. It slots in as the last `_LAYERS` entry, and the duplicate-key `ValueError` from 17-02 makes any key collision with earlier layers loud rather than silent.

**Strengths.**
- `is_managed`'s exact/prefix/host-override decomposition, with `model_policy`/`runtime`/`resolve_model_ids` deliberately *excluded* (reconciled from conflicts instead), is precisely specified and each exclusion has a dedicated test (unmanaged keys, other hosts' `model_profile_overrides`, `workflow.live_dom_uat` never touched).
- The composition tests (Task 3) are the ones that matter — leftover-vs-slot single-entry guarantee, `review.default_reviewers` reserved-vs-unset depending on the cross-AI answer, pi stale-override unset — and reuse the 17-04/17-06 fixtures rather than inventing new ones.
- `make_inventory`'s additive change (accepting global model_policy leaves) keeps 17-02..17-06 tests green.

**Concerns.**
- **LOW — the latent-effect unset for a global `resolve_model_ids`/`model_policy`** proposes unsetting a *project* key that does not yet exist (`existing: null`). Phase 18's apply must interpret this as "unset after `config-new-project` copies it" — the `why` names the copy, and 18's reconcile (18 D-22) is cited, but the semantic weight on Phase 18 is real. Within Phase 17's read-only boundary this is correct.
- **LOW — `_runtime_entries` note text** interpolates `~/.gsd/defaults.json` literally even when `GSD_HOME` redirected the path; `global_defaults.path` is in the inventory, so the note could name the actual path. Cosmetic honesty nit given the allow-listed reads.

**Suggestions.** Use `global_defaults.path` in the `runtime_mismatch` note text instead of the hardcoded `~/.gsd/defaults.json` string.

**Risk Assessment.** **LOW-MEDIUM.** Pure logic over verified key-validity facts, with removal scope tightly fenced and tested.

---

## 17-09

**Summary.** The golden/property/phase-gate closer: 17 digest-masked golden plans built end-to-end from shared fixtures (D-20), cross-cutting property assertions, the real `classify_conflicts`→`recommend` join, a live re-check of `closed_key_set` against the real gsd-core, the four SPEC amendments (R4/R9/R11), and `make test`/`make validate`. The critical live premise holds — my independent probe over the exact 47-key union returned `rejected: []`, so `TestGoldenTables`' canary and the no-drop goldens are achievable on this checkout. Fixture arithmetic also checks out (codex standard ceiling = 4 → all native kept; opencode standard ceiling = 2; `router-env/my-coding` fixture-confirmed so the router-declared path is exercised). Anchors verified: `UPDATE_GOLDEN` convention at `tests/test_status_line.py:2754/2797`, `test_generated_listings_name_every_discovered_module` at `tests/test_gate_scope.py:351`, `make validate` at `Makefile:128`, `make e2e-docker` at `:133`, and every SPEC string Task 3 replaces exists verbatim (lines 48, 49, 77, 79, 97, 143 of 17-SPEC.md — the `grep -c` acceptance counts, including the two "keep. entries write nothing" occurrences, are correct).

**Strengths.**
- The digest-masking design is a genuinely good regression-hygiene idea: unrelated inventory text changes stop rewriting every golden while determinism stays pinned by 17-02's two-run test, and property tests read the *committed* goldens so a blind regeneration can't launder a property break.
- The "stop and report; never edit `skills/` to make a golden pass; never rewrite a golden to hide a property failure" executor rule is the right guardrail for a cheap cross-AI executor.
- Fixture hygiene (`/home/`, `/tmp/`, `/var/` rejection; `<scratch>` normalization; pi labeled synthetic) directly enforces the no-absolute-path and no-secret rules.
- The Task 3 SPEC amendments are surgical, each traced to a locked decision (D-17 note, D-18, D-22-amended, D-29), and the e2e-docker/skill-judge scoping claim is verifiable via the git-log check it prescribes.

**Concerns.**
- **MEDIUM — goldens amplify any earlier-plan defect.** A wrong pick in 17-04/17-06 doesn't fail those plans' targeted tests (which assert properties like "not anthropic/" rather than specific ids) but *does* change golden bytes here. That's the design (goldens are the phase's acceptance), but it means 17-09 may surface rework that points backward across four waves. The plan handles it correctly (stop and report); the cost is schedule, not correctness.
- **MEDIUM — `TestGoldenTables` hard-requires VERSION exactly 1.16.0** to write the tables fixture ("if it is skipped … stop and report"). Correct fail-closed behavior, but a gsd-core bump between now and execution stalls the phase until the fixture is re-captured (1.17 is already published with identical tier tables per the research — the plan could have allowed re-capture against 1.17 with a version note).
- **LOW — `build_golden_inventory` normalizes the scratch root via `str.replace` on canonical JSON text**; a temp-dir path that appears inside a fixture string would also be rewritten. Harmless in practice, worth a comment.
- **LOW — Task 3's `make test`/`make validate` gate** is the first full-tier run in the phase; earlier plans only ran `make test-unit` and lint. An integration/e2e-tier surprise (e.g., PTY suites sensitive to timing) would land here. The executor rules cover reporting it as pre-existing if unrelated.

**Suggestions.** Permit `TestGoldenTables` to capture from gsd-core ≥1.16 when the tier tables byte-match the pinned expectations, or at least name the re-capture procedure in Task 1's stop condition.

**Risk Assessment.** **MEDIUM.** Everything it asserts is achievable on this checkout today (independently verified), but it concentrates the phase's integration risk into the final wave by design.

---

## Cross-Plan Assessment

**Dependency ordering.** The wave chain (01→02→03→04→05→06→07→08→09) is sound. Each plan's `depends_on` matches its actual couplings: 17-04 needs 17-02's engine and re-runs 17-03's checks; 17-05 modifies 17-03's real-gsd test; 17-06 reads 17-04's slot entries; 17-08 consumes 17-07's conflict contract (duplicated verbatim in both plans, as instructed); 17-09 gates on all. The `_LAYERS` sequence evolving across four plans stays consistent at every step (preset, tier → +slot after tier → +specialist → +reconcile last), and 17-02's duplicate-key `ValueError` guarantees layer collisions fail loudly.

**Requirement coverage.** INV-01 (17-03/05/07), INV-02 (17-01/04/05), INV-03 (17-07/08), REC-01 (17-02/08), REC-02 (17-02/09), REC-03 (17-01/04), REC-04 (17-01/06), REC-05 (17-02), REC-06 (17-02/03) — complete, with the D-22 pi deviation from INV-02's "per-slot prompts" explicitly SPEC-amended in 17-09 rather than left contradictory.

**Biggest structural risk.** The inventory contract defined in 17-02 is only provably satisfiable by a real inventory at 17-07 (waves 3–6 emit partial documents that `load_inventory` would reject). No intermediate test exercises the join, so contract drift surfaces late. Mitigated by verbatim contract duplication and 17-07 Task 1's end-to-end test; the residual cost is late rework, not a broken design.

**Consistency of verified facts.** I found zero factual errors in the plans' claims about the repo: every line number, table value, flag name, test-class location, and live-behavior assertion I checked held (including the subtle ones — `model_policy` whole-object rejection, `RUNTIME_PROFILE_MAP` lacking `cursor`, the `which_fn(path=)` kwarg trap, tier counts, `EFFORT_LADDER:134`). The only staleness found was in the research/CONTEXT (this worktree's `claude_md_path` already fixed to `./AGENTS.md`), which no plan depends on.

**Security.** Threat models are concrete and mechanistic rather than boilerplate: argv-only subprocess calls (arch rule 8 enforced by `tests/test_arch.py`), token redaction with tests, allow-listed real-subprocess harness, allow-listed config reads with planted-secret tests, read-only proof, scratch HOME/XDG/GSD_HOME everywhere — matching the repo's AGENTS.md rules. The one accepted side effect (opencode's own XDG data dir writes from `serve`) is documented and decided (D-32).

**Over-engineering.** None found. Each mechanism traces to a locked decision or a live-verified pitfall; the notable restraint is dropping the research's wider node dump (17-03) and reusing every existing helper instead of duplicating (`gsd_tools`, `group_models_by_family`, `infer_vendor_from_model`, `cache_write_text`).

## Overall Risk Assessment

**MEDIUM.** This is a high-complexity phase (three model layers, five hosts, catalog states, conflict semantics) executed through nine interlocking plans, but the plans are exceptionally well-grounded: every checkable claim was checked and held, the live key-validity premise underlying REC-06 was independently re-verified, and the failure modes are systematically fail-closed with tests that prove the failure paths. The residual risks are (1) late integration feedback at 17-07/17-09, (2) 17-01's test-suite churn and the CI-untestable live opencode probe, and (3) executor burden — the plans assume careful, literate execution (self-assessed confidence "low" is honest), and a cheap cross-AI executor will need the explicit stop-and-report rules these plans do provide.

---

## Consensus Summary

One reviewer ran (`opencode-plan-review`, opencode adapter, pinned model
`router-env/my-plan-review`), so there is no cross-reviewer consensus; findings below are that
reviewer's, checked by the orchestrator against the plans and source. The review is
source-grounded (`file:line` citations, live `isValidConfigKey` and table probes) and covers all
9 plan ids. The repository path in its methodology line was replaced with `<repo root>`.

Verdict: no HIGH concern; overall risk MEDIUM, driven by phase size and late integration
(17-07 join, 17-09 goldens), not by a design defect. The reviewer found no factual error in any
plan claim it checked.

### Agreed Strengths

Single reviewer, so none are "agreed". Its main strengths: every line number, table value and
live-behavior claim it checked held; fail-closed paths throughout; the `real_gsd_run` allow-list
harness; the W2 gsd-planner reference fix in 17-06; digest-masked goldens with property tests
over committed files.

### Agreed Concerns

None (single reviewer). Orchestrator triage of its MEDIUM/LOW concerns against the plan text:

- Actionable: 17-08 LOW. The `runtime_mismatch` note text names `~/.gsd/defaults.json`
  literally, but 17-07 reads `$GSD_HOME/.gsd/defaults.json` when `GSD_HOME` is set, so the note
  can name the wrong file. Fix: build the note from `inventory.global_defaults.path` (or say
  why the literal is kept).
- Already in the plans, so not actionable:
  - 17-01 test churn. Task 2 step 5 names the exact `TestRuntimesSchemaVersion` tests and the
    literal `2`s to change.
  - 17-01 `OSError` on `--version`. Task 1 `<behavior>` already has `OSError -> None`.
  - 17-01 untested live probe. It has a manual-only VALIDATION.md check.
  - 17-05 `--refresh` with a failed detect. Task 2 already emits `detect-runtimes failed; using
    the cached runtimes snapshot`.
  - 17-09 1.16.0 pin. It has an explicit stop-and-report rule, and the test skips (not fails)
    on another version.
  - 17-02 `_drop_rejected` on unsets. Step 3 filters every entry; 17-08 Task 3 pins a rejected
    unset.
- Not actionable or factually wrong:
  - 17-06 codex `model_overrides` bare ids. gsd-core types `model_overrides` as
    `Record<string,string>` (`.claude/gsd-core/bin/lib/model-resolver.cjs:290`), so bare ids
    are the correct form.
  - 17-01 daemon Timer. The action already says "daemon".
  - The rest are design observations (late contract join, `_slot_models` coupling,
    pool-relative `purpose_scores` with a 17-05 backstop, golden amplification, informational
    `db` heuristics), cosmetic notes, or Phase 18 concerns.

### Divergent Views

None (single reviewer).

## Orchestrator disposition (cycle 1)

- 17-08 (LOW) `runtime_mismatch` note hardcoded `~/.gsd/defaults.json`: **incorporated**. The
  note now names `ctx.inv["global_defaults"]["path"]` (17-07 resolves `$GSD_HOME`), and a Task 2
  behavior case sets a `GSD_HOME`-style path. Done in the plan text, so no replan cycle was needed.
- All other MEDIUM/LOW concerns: already handled in the plans or not plan changes, as the review
  summary above records. No HIGH concerns. **Converged at cycle 1.**
