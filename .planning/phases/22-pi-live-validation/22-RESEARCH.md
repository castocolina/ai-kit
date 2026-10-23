# Phase 22: Pi Live Validation - Research

**Researched:** 2026-10-23
**Domain:** pi (pi.dev coding agent) host validation of the `ai-kit-gsd-curated-config` v2 skill: RPC model enumeration, GSD-on-pi steering semantics, honest pi plans, smoke, matrix, label lift
**Confidence:** HIGH for repo state and static/mock evidence; MEDIUM for anything that needs a live pi session (L2/L3, interactive smoke, `PI_CODING_AGENT` live confirmation)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** GSD on pi is a gsd-tools bridge plus one request-steering hook. It spawns no named agents and no `pi` subprocesses and installs no agents, commands or skills. (`pi/gsd.cjs:290-310` `runHook` spawns only `node hook.js`; `:318-380` `/gsd` and `gsd_invoke` call `dispatchGsdCommand`; a scratch `--pi --local` install under a temp HOME produced only `.pi/extensions/gsd.js`, `.pi/gsd-core/` (marker `pi`), `.pi/gsd-hooks/` and `.pi/scripts/`.)
- **D-02:** The verdict vocabulary gains "session-steer (sonnet key only)" with per-key labels. The hook registers with no tier argument (`gsd.cjs:386`), defaults to `sonnet` (`:233`), replaces the payload `model` verbatim (`:265-272`), and fails open unless `pi.sonnet` is set. `pi.opus` alone left the wire unchanged; without `--approve` the project extension did not load, silently.
- **D-03:** The spike climbs an evidence ladder and records the trust state of every run: L0 static source; L1 fake-ExtensionAPI handler probe; L2 localhost mock provider logging the wire `model`; L3 one tiny real run comparing `message.model` with `message.responseModel` with and without the override. Only L3 spends a model call and needs uz's approval. `resolve-model` is not an oracle on pi (under `resolve_model_ids: "omit"` it returns `model: ""` while the hook still steers).
- **D-04:** Enumeration source is pi's RPC `get_available_models` (`pi --mode rpc --offline --no-session --no-extensions --no-skills --no-context-files --no-mcp`), one JSON command on stdin, stdin closed after the response, with the 18.1 supervisor's timeout. Exact `contextWindow`/`maxTokens`, `input` (to `image_input`) and `thinkingLevelMap` (to `reasoning_modes`). Pure `parse_pi_models(stdout)` plus thin `detect_pi_models`, as for codex. Fixture is a trimmed capture with `baseUrl` values removed.
- **D-05:** A pi plan writes no `model_overrides.*`, no `pi.opus`, no `pi.haiku`. If the verdict is session-steer it offers one `model_profile_overrides.pi.sonnet` as an opt-in `needs_choice`, limited to bare model ids served by the session's active provider, labelled "steers every request in this project's pi session".
- **D-06:** `agent_skills.*` and other agent-bound keys are labelled `no effect on pi (no GSD agent files installed)`. The L3 run should confirm. GSD's `skills-root pi` returns only `~/.pi/agent/skills` while pi also loads `~/.agents/skills`: filed as an R7 finding against 18 D-31.
- **D-07:** The pi matrix asserts tier equality from the independent oracle (19 D-10), `model == ""` under `omit`, and five handler probes (one per combination) for the effect. The oracle is host-parameterized: `omit` is the installer's intended state on pi, not poison.
- **D-08:** The pi installer runs under a temp HOME; 19 D-14's sha256 guard on the real `~/.gsd/defaults.json` stays the assertion. Phase 17's host-first gsd-core resolver adds `<project>/.pi/gsd-core` and `$PI_CODING_AGENT_DIR|~/.pi/agent/gsd-core`.
- **D-09:** Phase 22 also live-verifies `PI_CODING_AGENT` (labelled source-inspected at `detection.py:83-86`) from the interactive session and updates the label, as 20 D-05 does for codex.
- **D-10:** The user script loads the skill with `pi --skill <path>` (no `~/.pi/agent` change), tells the user to pick a model first (the default `openai-codex` login is gone), and treats the project-trust prompt as the user's consent action.

### Claude's Discretion
- Probe script names; the order of L0-L2 within the spike.

### Deferred Ideas (OUT OF SCOPE)
- Writing GSD agent files for pi's own subagent extension stays out of scope (SPEC Boundaries).

Open for research (CONTEXT `<specifics>`): steering on a real provider and whether the router accepts `provider/model` as `model`; whether pi persists project trust under `~/.pi/agent`; the meaning of a null `thinkingLevelMap`; upstream gsd-core's hard-coded sonnet tier and the `omit` vs hook disagreement. The analyzer's scratch `rpc-real.json` holds router `baseUrl` values: never commit it.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SPEC-05 | `detect-runtimes` enumerates pi via RPC `get_available_models` with a fixture-backed parser | Parser, snapshot branch and 9 tests already exist (Phase 18). Remaining delta: real trimmed 85-entry capture, `maxTokens`, `reasoning_modes` semantics, structured-error shape (see R1 section) |
| EVAL-08 | Live smoke on the pi host; label lifted only after R4 and R5 pass | Smoke harness exists for 4 hosts, lacks pi (installer layout, baked-chain oracle, protected set). R4 interactive step is owner-only |
| APP-05 | After `apply`, `resolve-model` with `GSD_RUNTIME=<host>` returns the planned model for all 35 agents | Matrix harness needs a pi branch; currently crashes on pi (`no candidates for model_profile_overrides.pi.sonnet`), verified this session |
</phase_requirements>

## Summary

Most of what the SPEC calls "target" for R1 and R3 is already in the tree from Phases 18 and 18.1. R1: `parse_pi_models`, `detect_pi_models`, `PI_RPC_ARGS`, the snapshot branch and a `TestPiRpcModels` class exist and pass; what is missing is the real trimmed capture (the current fixture is a synthetic 3-model file), the `maxTokens` field, a correct `reasoning_modes` derivation, and a decision on "structured error" (the parser returns `None`). R3: pi plans already write no `model_overrides.*`, label model-layer entries `effect unverified on pi (gsd-core registry: namedDispatch false)`, label `agent_skills.*`, and emit `model_profile_overrides.pi.sonnet` as an opt-in `needs_choice` with `candidates: []`. What is missing is candidate generation, the session-steer wording, a verbatim text pin, and verdict-conditional behaviour.

The static/mock evidence for the verdict re-verifies on current versions (pi 1.3.0, gsd-core 1.17.0; the SPEC was written against 1.2.0 and 1.16): the registry still says `namedDispatch: false`, the hook source is byte-identical in two npx caches, and an L1 fake-ExtensionAPI probe run this session shows only `pi.sonnet` steers. Two upstream facts change the plan: (a) pi exports `PI_PROVIDER`/`PI_MODEL`/`PI_SESSION_FILE` to the shell tool's commands, so the skill can learn the session's active provider without asking, which resolves the "session provider unknown" blocker behind the empty candidate list; (b) the upstream hook itself flags as an unverified ASSUMPTION that the request payload's model field is named `model`, so L3 is the first real proof of any effect and a non-echoing provider can make L3 inconclusive rather than "inert".

Automatable without any model call: parser fixture and tests, plan/label/golden changes, harness pi branches, the pi matrix (real-node `resolve-model`, no model), L0/L1 evidence, local install layout. Owner-only: the interactive-session smoke (R4), L3 (approval plus a real call), the real 85-model capture (needs the real agent dir), `PI_CODING_AGENT` TUI confirmation, and the project-trust prompt.

**Primary recommendation:** Treat R1 and R3 as small deltas on existing code (one module each), unblock the pi matrix by giving `pi.sonnet` real candidates (active provider's bare ids from `PI_PROVIDER` plus the enumerated list), build the pi smoke/matrix branches in `tests/gsd_curated_eval.py`, and gate the label lift on the owner's interactive run exactly as Phases 20/21 gated theirs ("pending" wording until it lands).

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Model enumeration (`pi --mode rpc get_available_models`) | `ai_kit_spec/detection.py` (runtime detection) | `catalog_adapter.py` (candidates) | Single source of truth for runtimes; codex precedent |
| Session provider discovery (`PI_PROVIDER`/`PI_MODEL`) | inventory (host facts) | recommend (candidate filter) | Env is read once in inventory; the plan stays a pure function of the inventory (SPEC R3 concurrency edge) |
| Honest pi plan (labels, opt-in `pi.sonnet`) | `recommend.py` / `presets.py` | `plan_io.py` schema | Labels are plan data, pinned by golden and unit tests |
| Request steering on pi | gsd-core `pi/gsd.cjs` hook (upstream, read-only) | project `.planning/config.json` | ai-kit only writes the config key; it never owns the hook |
| Smoke / matrix harness | `tests/gsd_curated_eval.py` | `tests/test_curated_config_*_e2e.py` | Host-agnostic harness; pi needs host branches |
| Label text | `SKILL.md` Limits table, README row | `tests/test_curated_config_apply.py` pins | Label lift is a doc change with pinned tests that must change in the same commit |

## Standard Stack

No new external packages are installed by this phase. The stack is what the repo and the hosts already provide.

### Core
| Component | Version | Purpose | Why Standard |
|-----------|---------|---------|--------------|
| pi (`@earendil-works/pi-coding-agent`) | 1.3.0 on this machine [VERIFIED: `pi --version` output `1.3.0`]; SPEC captured 1.2.0 | Host under test | Target host |
| `@opengsd/gsd-core` | 1.17.0 local tree [VERIFIED: `.claude/gsd-core/VERSION` content `1.17.0`] and two npx caches at 1.17.0, one at 1.13.0 | GSD engine, pi extension, installer | Pinned per scratch project (19/20 R1) |
| Python stdlib `unittest` via `tools/run_unittest_parallel.py` | python 3.14.7 here (project target py312) | Test runner | Repo standard |
| node | v24.21.0 | Runs gsd-tools / installer / L1 probe | Required by gsd-core |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| RPC `get_available_models` | `pi --list-models` table | Lossy (`toFixed(1)`), exits 0 on every failure; rejected by D-04 |
| Session JSONL for L3 | `pi --mode json` event stream | JSON mode needs no session file and works with `--no-session`; JSONL needs `--session-dir <scratch>` and the real agent dir for auth. Either records `message.model`; see L3 pitfalls |

**Installation:** none. **Package Legitimacy Audit:** not applicable (no external package is added; `@opengsd/gsd-core` is already pinned by Phases 17-21 and `@earendil-works/pi-coding-agent` is the user's installed host).

## Architecture Patterns

### System Architecture Diagram

```
 owner interactive pi session                 headless / hermetic (agent-runnable)
 ---------------------------                  ------------------------------------
 pi --skill <path>  (trust prompt = consent)  python tests (unittest)
        |                                           |
        v                                           v
 SKILL.md flow --> ai-kit-gsd-curated-config  parse_pi_models(fixture) --> snapshot
   inventory --> detect_current_runtime (PI_CODING_AGENT)        ^
        |            + PI_PROVIDER / PI_MODEL (session facts)     |
        |            + detect_pi_models: pi --mode rpc ... ------+  (real: needs real agent dir)
        v
   recommend --> plan: tier labels (effect unverified on pi ...)
        |            + agent_skills.* (no effect on pi ...)
        |            + needs_choice model_profile_overrides.pi.sonnet (bare ids of active provider)
        v
   apply --dry-run --> apply (gsd-tools config-set only) --> project .planning/config.json
                                                                    |
   gsd-core pi extension (.pi/extensions/gsd.js, trust-gated)       v
     before_provider_request --> loadConfig(cwd) --> model_profile_overrides.pi.sonnet?
        set  --> payload.model replaced verbatim (every request, session-wide)
        unset/"" --> undefined (fail open, pi's own selection)
```

### Recommended Project Structure (touch points only)
```
skills/ai-kit-spec-review/ai_kit_spec/detection.py      # R1 deltas (maxTokens, reasoning_modes, error shape)
skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/
  recommend.py presets.py  inventory.py                 # R3 deltas (candidates, wording, session facts)
  apply.py                                              # _PI_SKILL_SKIP wording check only
skills/ai-kit-gsd-curated-config/SKILL.md               # label row, verdict statement (R6)
tests/fixtures/pi_rpc_get_available_models.json         # replaced by trimmed real capture (R1)
tests/fixtures/curated_config_v2/golden/pi-*.json       # 3 pi goldens (R3)
tests/gsd_curated_eval.py                               # pi smoke/matrix/snapshot branches
tests/test_ai_kit_gsd_curated_config_matrix.py          # new pi matrix class
.planning/phases/22-pi-live-validation/                 # 22-SPIKE-PI-AGENTS.md, 22-SMOKE-PI.md, 22-INTERACTIVE-PI.md, 22-SKILL-JUDGE.md
```

### Pattern 1: Pure parser plus thin detector (codex precedent), already applied to pi
**What:** `parse_pi_models(stdout)` is pure and never raises; `detect_pi_models` runs the argv through `run_fn` with a timeout.
**Current code** [VERIFIED: `detection.py:32-36, 477-565`, read this session], quoted verbatim:
```python
PI_RPC_ARGS = (
    "--mode", "rpc", "--offline", "--no-session", "--no-extensions",
    "--no-skills", "--no-context-files", "--no-mcp",
)
PI_RPC_REQUEST = '{"id":"1","type":"get_available_models"}\n'
```
`detect_pi_models` calls `run_fn([binary, *_list_argv("pi")], input=PI_RPC_REQUEST, capture_output=True, text=True, check=False, timeout=15)`; `subprocess.run` closes stdin after `input` and kills the child on timeout, which satisfies the SPEC "closing stdin ends it and the supervisor kills it on timeout" edge.

### Pattern 2: Evidence ladder (D-03) with a trust-state column
Each spike rung records: pi version, gsd-core version, trust state (`--approve` one-shot, saved `/trust`, or explicit `-e`), the override set, the wire `model`, `message.model`, `message.responseModel`. One run at a time, one mock provider per run, killed afterwards.

### Anti-Patterns to Avoid
- **Trusting `resolve-model` on pi:** with `resolve_model_ids: "omit"` it returns `""` for every agent even when `pi.sonnet` is set (verified, below); the hook, not `resolve-model`, decides the wire model.
- **Offering `provider/model` strings as `pi.sonnet`:** the hook writes the value verbatim into `payload.model` (verified by L1: `router-env/my-coding` is passed through unchanged); a provider-qualified string on the wire breaks every request.
- **Pointing the RPC enumeration at the real agent dir from an automated test:** pi creates files in its agent dir even in `--offline` (observed below).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Model enumeration on pi | A `--list-models` table scraper | The existing RPC parser | Table is lossy and exit 0 on failure |
| Supported thinking levels | A custom guess from `thinkingLevelMap` keys | Re-implement pi-ai's `getSupportedThinkingLevels` rule exactly (see R1) | Missing key means provider default, `null` means unsupported, `xhigh`/`max` need an explicit mapping [VERIFIED: pi-ai `dist/models.js:679-691`] |
| Config writes | Direct JSON edits of `.planning/config.json` | gsd-tools `config-set` / `config-new-project` via the existing apply pipeline | Existing contract (Phase 18) |
| Smoke/matrix harness | A pi-only script | Extend `tests/gsd_curated_eval.py` with host branches | 5034-line harness already carries snapshot, secret-scan, digest and matrix logic |
| Secrets handling | Ad-hoc redaction | `gsd_curated_eval.py secret-scan` plus the names-only env rule | Precedent in 19-21 |

## Runtime State Inventory

Not a rename/refactor phase; the section is limited to pi-side state that a validation run can touch.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | pi agent dir (`~/.pi/agent`) holds `auth.json`, `models.json`, `models-store.json`, `settings.json`, `sessions/`, `extensions/`, `agents/`, `skills/` [VERIFIED: directory listing by name only, contents not read]. Project trust persists in `~/.pi/agent/trust.json` via `/trust` [CITED: pi docs security.md "Use `/trust` to save a decision"] | Never write. Guard with name/hash snapshot, `auth.json` excluded (credential, never hashed or read) |
| Live service config | None | None |
| OS-registered state | None | None |
| Secrets/env vars | `PI_CODING_AGENT_DIR`, `PI_OFFLINE`, `PI_SKIP_VERSION_CHECK`, provider key env vars | Scrub host signals for children; names only in evidence |
| Build artifacts | Installer writes `~/.gsd/defaults.json` and `defaults-provenance.json` under HOME even for `--local` | Run installer under temp HOME (D-08); assert real file sha256 unchanged |

## Common Pitfalls

### Pitfall 1: Volta shim breaks `node` under a temp HOME
**What goes wrong:** running the installer with `HOME=<temp>` and a bare `node` fails with `Volta error: Node is not available.` [VERIFIED: reproduced this session]. **How to avoid:** resolve `process.execPath` once (`node -p process.execPath`) and call that absolute binary with an allowlisted env (PATH, HOME, XDG_*), as the Phase 21 smoke does.
**Warning signs:** a `.volta/` directory appearing inside the scratch HOME.

### Pitfall 2: pi writes into its agent dir even for an offline listing
**What goes wrong:** `PI_CODING_AGENT_DIR=<empty scratch> pi --mode rpc --offline ...` created `auth.json` and `models-store.json` (2 bytes each) in the scratch dir [VERIFIED: observed this session]. Against the real dir this could touch the user's files. **How to avoid:** never run it in an automated test against the real dir; the owner capture step records sha256 before/after of every pi file except `auth.json`.

### Pitfall 3: An empty agent dir lists zero models
**What goes wrong:** the RPC returns `{"models":[]}` with exit 0 when no provider has credentials [VERIFIED: scratch run returned `success:true` and an empty `models` array; `pi --list-models --offline` printed "No models available"]. So the real 85-model capture can only come from the real agent dir (credentials), and the "empty list" edge is proven live for free.

### Pitfall 4: `reasoning_modes` from `thinkingLevelMap` keys is wrong for maps that omit keys
**What goes wrong:** `_pi_reasoning_modes` returns only keys present with a truthy value. pi's rule is different: `reasoning:false` means only `off`; a `null` value marks a level unsupported; a missing key means the provider default (supported) except `xhigh`/`max`, which need an explicit non-undefined mapping [VERIFIED: pi-ai `dist/models.js:680-691`; type doc `types.d.ts:645-649`: "Missing keys use provider defaults. null marks a level as unsupported."]. A reasoning model with an absent or partial map is reported as having no modes. This also answers the CONTEXT question on a null `thinkingLevelMap` entry: unsupported level (the fixture's `"xhigh": null`). **How to avoid:** derive modes with the same rule, over `["minimal","low","medium","high","xhigh","max"]` (decide whether `off` is included; consumers use the list as effort pins, `cross_ai.py` already clamps and pi clamps to `off` itself). This is a one-module R7 fix with a regression test.

### Pitfall 5: Host-signal inheritance
**What goes wrong:** children inherit `PI_CODING_AGENT`, `AI_AGENT=pi`, `PI_MODEL`, `PI_PROVIDER`, `PI_SESSION_FILE`, `PI_SESSION_ID`, `PI_OFFLINE`, `PI_SKIP_VERSION_CHECK` [CITED: pi docs environment-variables.md]. The Phase 21 cursor run observed exactly these pi names in a child's env dump [VERIFIED: 21-SMOKE-CURSOR.md "Env names" list]. **How to avoid:** `HOST_SIGNAL_ENV_VARS` already covers `PI_CODING_AGENT` and `AI_AGENT` [VERIFIED: `detection.py:205-210` code plus `_GENERIC_HOST_MARKERS`]; evidence prints names only, never values. `detect_pi_models` passes no `env`, so it inherits the parent env (fine: pi sets its own markers).

### Pitfall 6: L3 can be inconclusive, not "inert"
`message.model` records the selection; the hook rewrites only the wire payload afterwards, so selection never changes. `responseModel` is recorded only "when it differs from the requested model" [CITED: pi docs message-types.md:143]. If the provider/router does not echo the served model, steering is unobservable from the transcript. The L3 verdict table needs a fourth outcome, `inconclusive (provider does not echo)`, and the mock (L2) is the only rung that sees the wire. Also, the upstream hook admits the payload field name is an unverified ASSUMPTION [VERIFIED: `pi/gsd.cjs` doc comment "ASSUMPTION (flagged — verify against a live pi host)"], so the first L3 success is also the first proof the hook works at all on a real provider.

### Pitfall 7: Trust gating is silent
Project `.pi/extensions` is a trust-gated resource; in print/JSON/RPC modes there is no prompt and the default `defaultProjectTrust: "ask"` skips it [CITED: pi docs security.md]. `--approve` is a one-shot override and `/trust` persists to `~/.pi/agent/trust.json`. An explicit `-e <path>` still loads under `--no-extensions` [CITED: pi docs cli.md:196], which bypasses trust and changes what the run proves; record which path each rung used.

### Pitfall 8: Test pins on the label text
`tests/test_curated_config_apply.py:2378` requires the phrase `"not live-validated"` in SKILL.md, and `:2445` pins the exact row `| pi hosts | **not live-validated** |` [VERIFIED: file read this session]. The label lift edits both tests in the same commit. README line 45 also says "pi not live-validated" [VERIFIED: grep].

## R1: Enumeration (pi enumeration, SPEC-05)

**Current state** [VERIFIED: `detection.py`, `tests/test_ai_kit_spec.py:2533-2700`, fixture file, all read this session]:
- Row `"pi": Runtime(("pi",), (("PI_CODING_AGENT", _LABEL_PI),), list_argv=PI_RPC_ARGS, model_suffix=r":(?:off|minimal|low|medium|high|xhigh|max)$)`.
- `_LABEL_PI` text: "source-inspected-only — confirmed in the installed `@earendil-works/pi-coding-agent` package's `dist/config.js`, not live-verified from a real pi session (16 D-03; live validation is Phase 22)."
- Parser output record: `{"id": "provider/id", "reasoning_modes": [...], "image_input": bool, "context_window": int|None}`. It does not return `maxTokens`, and `_listing_fields` stores only `models`, `reasoning_modes`, `image_input` in the snapshot, so `context_window` never reaches a candidate.
- Duplicates: first `provider/id` wins; blank id or provider and non-dict items are skipped.
- Failure shape: every failure returns `None`; an all-skipped list returns `[]`. The SPEC R1 amendment says "structured error". Decide: keep `None` (it is the established codex contract; the snapshot omits `models` and the diagnostics surface "listing failed") and state in the plan that `None` is the structured error, or add an error reason. Recommendation: keep `None` and pin it, because changing the shared contract is a two-module change (parser plus consumers).
- Fixture is synthetic: 3 valid models plus a duplicate, a blank-id row and a bare string; its comment says "Phase 22 replaces this with a trimmed real capture (22 D-04)".

**Gap list for the plan:**
1. Real capture: needs the real agent dir and credentials. Agent-run attempts with an empty agent dir return 0 models, so this is an owner step (or an open question for the owner: allow one RPC run against the real dir with the before/after hash guard). Post-process by a script: drop `baseUrl` (and any `headers`-like field), keep `api, id, name, provider, input, contextWindow, maxTokens, reasoning, thinkingLevelMap, cost, type`; assert `"baseUrl" not in text`; secret-scan; keep 85 entries, provider split anthropic 17, opencode-go 31, radius 29, router-env 4, xai 4 (SPEC, captured 2026-10-14; counts will drift, so the test pins the fixture, not the live set).
2. Add `max_tokens` (exact int) to the record; decide whether to carry `context_window`/`max_tokens` into the snapshot (would bump `RUNTIMES_SCHEMA_VERSION`, currently 5). SPEC R1 only requires exact integers at parser level.
3. Fix `reasoning_modes` per Pitfall 4.
4. Add the `api` field to the record if candidate filtering by api is adopted (R3).
5. Keep the live-shape evidence note: RPC doc shape [CITED: pi docs rpc-commands.md:252-270]; the empty-dir run confirmed the envelope on 1.3.0.
6. Labels: `_LABEL_PI` docstring in `detect_current_runtime` and `detection.py:83-86` stay "not live-verified" until the interactive step; pi documents `PI_CODING_AGENT=true` as the Pi-specific child marker [CITED: pi docs environment-variables.md:16], so the label can honestly become "documented by pi; live confirmation pending 22-INTERACTIVE-PI.md" immediately, the way `_LABEL_CURSOR` reads.

## R2: Per-agent model spike (static and mock evidence)

**L0 (static) re-verified on current versions:**
- Registry entry for pi in the local gsd-core 1.17.0: `"namedDispatch": false`, `"nested": false`, `"maxDepth": 0`, `"subagentToolkit": "undocumented"`, `"installSurface": "profile-marker-only"` [VERIFIED: `.claude/gsd-core/bin/lib/capability-registry.cjs:3167-3215`, quoted fields read this session; the `installSurface` line at 3198 region and dispatch block at 3210-3215].
- `pi/gsd.cjs` is byte-identical across the two 1.17.0 npx caches [VERIFIED: sha256 comparison printed `same-1.17-gsd.cjs`].
- Hook behaviour [VERIFIED: `pi/gsd.cjs` lines 217-262 read this session]: `buildBeforeProviderRequestHandler({ tier = 'sonnet' } = {})`; fail-open when `overrides.pi[tier]` is `undefined`, `null` or `''`; otherwise `return { ...basePayload, model: modelId }`.
- pi side [VERIFIED: pi `dist/core/extensions/runner.js:1068-1103`]: `emitBeforeProviderRequest` runs every handler, takes a non-`undefined` return as the new payload, and reports handler errors without aborting. `types.d.ts:694` declares `payload: unknown`.

**L1 (fake ExtensionAPI) re-run this session on gsd-core 1.17.0** [VERIFIED: `tmp/p22/l1-probe.cjs`, output]:
```
{} -> undefined
{"opus":"o1"} -> undefined
{"haiku":"h1"} -> undefined
{"sonnet":"s1"} -> {"model":"s1","x":1}
{"sonnet":""} -> undefined
{"sonnet":"router-env/my-coding"} -> {"model":"router-env/my-coding","x":1}
```
This is the handler probe for the matrix's five-combination effect check (D-07); keep the script as a repo test (node-gated, skipped when no installer cache) rather than only an evidence artifact.

**`resolve-model` on pi, 1.17.0, scratch config** [VERIFIED: ran `resolve-model` with `GSD_RUNTIME=pi`]: without `resolve_model_ids` it returns `model: "claude-opus-4-8", tier: "opus", effort: "xhigh"` for `gsd-planner`; with `resolve_model_ids: "omit"` and `pi.sonnet` set it returns `model: ""` for planner, executor and mapper. Installer behaviour confirms `omit` is the intended pi state: a local `--pi --local` install printed `Set resolve_model_ids: "omit" in ~/.gsd/defaults.json` and `Set runtime: "pi" in ~/.gsd/defaults.json` [VERIFIED: installer output this session, under a temp HOME]. This is the "omit vs hook" disagreement from CONTEXT: not a bug in the plan, but the matrix oracle for pi must not expect `claude-opus-4-8`.

**Install layout (1.17.0, `--pi --local --no-legacy-cleanup`, temp HOME)** [VERIFIED: `find` output]: `.pi/extensions`, `.pi/gsd-core`, `.pi/gsd-file-manifest.json`, `.pi/gsd-hooks`, `.pi/gsd-install-state.json`, `.pi/.gsd-profile`, `.pi/.gsd-staging`, `.pi/scripts`; the temp HOME got `.gsd/defaults.json` and `.gsd/defaults-provenance.json`. No `agents/`, `commands/` or `skills/` directory. `tests/gsd_curated_eval.py::_generated_paths` lists `gsd-core`, `plugins/gsd-core.js` (+ `hooks`, `hooks.json`, `scripts` for cursor only) and `agents/commands/skills` globs, so a pi branch must list `extensions/gsd.js`, `gsd-hooks`, `scripts`, `gsd-file-manifest.json`, `gsd-install-state.json`, `.gsd-profile`, `.gsd-staging`.

**L2 (localhost mock provider):** automatable in principle (scratch `PI_CODING_AGENT_DIR` with a `models.json` pointing at 127.0.0.1 and a literal dummy key, `pi --mode json -p --no-session --approve`, mock logs the wire `model`). It starts pi's agent loop but sends no real model call. The research hard rules for this session limit pi use to model-free introspection, so L2 was not re-run here; the analyzer ran it on 2026-10-14 (CONTEXT D-02). Open Question 1 asks whether L2 may be re-run in the execution phase by the agent (recommended: yes, localhost only, no credentials).

**L3 (owner, one real call):** spec'd in D-03. Practical design notes: run from the real agent dir (credentials) with `--session-dir <scratch>` or `--mode json` so the transcript lands under scratch; load only the project extension (`-ne -e .pi/extensions/gsd.js`) to keep the user's extensions out, and separately once via `--approve` or the interactive trust prompt; two runs differing only in `pi.sonnet`; record `message.model`, `message.responseModel` and pi version. The session file path is exposed to the shell tool as `PI_SESSION_FILE` [CITED: pi docs environment-variables.md:27].

**Verdict mapping** (extends SPEC R2 amendment): `session-steer (sonnet key only)` requires an observed served-model change at L3 (or L2 for the wire plus L3 echo); `inert` requires L2 wire unchanged with the override set; L3 without echo is `inconclusive`, and the R3 plan then stays at label-only.

## R3: Honest pi plans

**Current code** [VERIFIED: `presets.py:135`, `recommend.py:152-157, 296-345, 712, 1076`, `apply.py:313-314, 456-457`, read this session], verbatim:
- `PI_EFFECT = "effect unverified on pi (gsd-core registry: namedDispatch false)"` attached to `model_profile` and every `models.<phase>` entry on a pi host.
- `_PI_AGENT_SKILLS_EFFECT = "no effect on pi (no GSD agent files installed)"` attached to every `agent_skills.*` entry.
- `_specialist_layer` returns `[], []` on pi (no `model_overrides.*`).
- `_pi_slot` emits `model_profile_overrides.pi.sonnet` with `status="needs_choice"`, `candidates=[]`, `effect=presets.PI_EFFECT`, and a note whose text is: "pi: only an opt-in model_profile_overrides.pi.sonnet is offered; no per-agent model_overrides (effect unverified on pi, gsd-core registry: namedDispatch false)". Its `why` says "the session provider is unknown before Phase 22".
- `apply.py::verify_skills` returns `{"skipped": _PI_SKILL_SKIP}` for pi; `_PI_SKILL_SKIP` mentions "GSD_RUNTIME=pi is not canonicalized by gsd-core 1.16.0": version string will go stale at 1.17.0; re-check the sentence against 1.17.0 behaviour before keeping it.
- Existing tests: `test_pi_sonnet_needs_choice` (recommend:900-915), a golden assertion (`test_curated_config_golden.py:413-420` requires `candidates == []`), the agent_skills label test (skills:1330). The "label text pinned verbatim" requirement is only partly met: tests compare `entry["effect"]` to `presets.PI_EFFECT` (a constant), not to a literal string. Add `assertEqual(entry["effect"], "effect unverified on pi (gsd-core registry: namedDispatch false)")`.

**Deltas:**
1. **Session provider is discoverable.** pi exports `PI_PROVIDER`, `PI_MODEL`, `PI_REASONING_LEVEL`, `PI_SESSION_ID`, `PI_SESSION_FILE` to commands run by its bash tool, resolved at each command start [CITED: pi docs environment-variables.md:20-33]. Phase 21's cursor child saw those names [VERIFIED: 21-SMOKE-CURSOR.md Env names]. So `inventory` can record `session.provider`/`session.model` (values are provider and model ids, not secrets) when `host == "pi"`, and `recommend` can offer `needs_choice` candidates = the bare ids of that provider's enumerated models. If the variables are absent (non-interactive, older pi), candidates stay empty and the entry says why (ask via `plan-set`). Whether pi 1.2.0 already exported them is unknown: the doc is the 1.3.0 doc [ASSUMED for 1.2.0].
2. **Candidate filter:** bare ids of the active provider only (D-05). Additional filter by equal `api` value as the active model is advisable because payload shape depends on the api [ASSUMED: model-id substitution across different `api` values of the same provider is unsafe; the fixture shows one provider listing models with different `api` values]. Needs `api` in the parser record. `PI_MODEL` is a bare id; a router that picks models internally is out of scope (`PI_PROVIDER`/`PI_MODEL` identify the selected model, not an upstream choice [CITED: pi docs]).
3. **Wording (D-05):** add the session-wide label to the opt-in entry text: "steers every request in this project's pi session". Keep the `PI_EFFECT` string until a verdict lands; after `session-steer`, the opt-in entry's `effect` becomes the session-wide label, tier entries stay `effect unverified...` (they still have no proven effect), `agent_skills` keep `no effect on pi...`. After `inert`: drop the opt-in entry entirely, relabel to `no effect on pi`. After `per-agent effective` (not expected): out of scope per Boundaries.
4. **Matrix unblock:** `_decide_all_choices` raises `no candidates for model_profile_overrides.pi.sonnet` [VERIFIED: ran `run_matrix(..., host='pi')` this session]. Either the golden bundle supplies the inventory's session provider (preferred; exercises the real path) or the bundle decides the entry as unset. The three pi goldens (`pi-mvp-adaptive`, `pi-rigorous-adaptive`, `pi-standard-adaptive`) and `test_curated_config_golden.py:413-420` change accordingly.
5. **Out-of-phase finding to file (R7):** `skills-root pi` returns only `~/.pi/agent/skills` while pi also loads `~/.agents/skills` (D-06, against 18 D-31). Not a fix for this phase unless it is a one-module change.

## R4: Smoke (EVAL-08) - prior hosts and what is automatable

**Precedent** [VERIFIED: 21-SMOKE-CURSOR.md and 21-INTERACTIVE-CURSOR.md read this session]: a headless iteration through the repo's cross-AI runner (`--prefer <host>`, explicit `--model-<host>`, `--mode exec`, `--no-preamble`, `--child-pgid-file`) under a scratch HOME produced a 10-step smoke (ai-kit inventory/recommend/dry-run; project (a) local install, inventory, recommend, dry run, apply, second apply, forced-failure restore, post-apply install and resolve-model check; project (b); matrix; protected set unchanged). The interactive run, started by the owner as `command <cli> --model <id>`, is the acceptance evidence and uses `tmp/p21/interactive` paths, a names-only env list, a before/after `snapshot` and `--host-rewrite` for the one host-rewritten config file.

**Pi-specific harness gaps** (`tests/gsd_curated_eval.py`, read this session):
- `matrix --host` choices are `("claude","codex","opencode","cursor")` (`:4979-4982`): add `pi`.
- `_strict_files` protects `~/.gsd/defaults.json`, `~/.claude/*`, `~/.cursor/{cli-config,hooks}.json` and tree hashes; nothing under `~/.pi/agent`. Add: `settings.json`, `models.json`, `trust.json` (strict or `--host-rewrite`, because pi rewrites `settings.json` when the model changes), `extensions`/`agents`/`skills` listings or tree hashes. Exclude `auth.json` and `sessions/` (credential never hashed or read; sessions are rewritten by design), following the `CREDENTIALS_BASENAME` precedent. `models-store.json` is rewritten by pi (observed created in a scratch dir): treat as host-rewrite.
- `_baked_chain` has branches for codex and cursor; pi needs its own: no agent files exist, the expected `resolve-model` model is `""` under `omit`, tier still equals the oracle tier.
- `_generated_paths` pi layout (see R2).
- Real-HOME guard: the installer writes `defaults.json`/`defaults-provenance.json` under HOME (verified) and ignores `GSD_HOME` (CONTEXT D-08), so keep the temp-HOME install plus the sha256 guard on the real file.
- Installer discovery: `--installer-dir <dir>` or the npx cache; there are two 1.17.0 caches and a 1.13.0 one, so the pinned-version check matters.
- Interactive precondition: the owner picks a model first (the default `openai-codex` login is gone, CONTEXT D-10); load with `pi --skill <path>`; trust prompt is the consent action.

**Automatable vs owner-only:**

| Work | Who | Notes |
|------|-----|-------|
| Pi branches in harness, hermetic tests with injected `run_fn` | agent | Hermetic tests need no node/pi |
| Headless smoke iteration on pi through the template-6 runner (`--prefer pi --model-pi router-env/my-coding`) | agent in the execution phase, subject to quota and the run rules | Calls a model; this research session did not run it. Same shape as Phase 21's headless run; supervision per Phase 25 |
| Interactive smoke from the owner's pi TUI, names-only env, `PI_CODING_AGENT` confirmation, trust prompt | owner only | Acceptance for R4 and D-09 |
| Real 85-model RPC capture | owner (or explicit consent for one guarded agent run) | Needs the real agent dir |
| L3 real-call spike | owner approval, then agent or owner | One tiny call per arm |

## R5: Matrix (APP-05 on pi)

- The matrix is real-node and model-free (`run_matrix` shells `resolve-model`); the `TestResolveModelMatrix` family in `tests/test_ai_kit_gsd_curated_config_matrix.py` (class `HOST` attribute, subclasses per host) is the home for a pi class. 5 combos x 2 start paths x 35 agents plus two controls [VERIFIED: file read; cursor run reported 420 checks, 21-SMOKE-CURSOR.md].
- Oracle changes needed for pi (`promised`, `_host_model`, `_mismatches`, `_write_control_plan`, `_control_one`):
  - `_host_model` currently returns the `RUNTIME_PROFILE_MAP.pi` id (`claude-opus-4-8` etc.) before it considers `omit`; on pi the intended state is `omit`, so expected `model` is `""` and the tier comes from the independent oracle (19 D-10). `compare()` fails an empty model when `expected` is truthy and passes `""` only when `expected == ""` [VERIFIED: `gsd_curated_eval.py:601-613`].
  - Control 1 for non-claude hosts removes `model_overrides.*` entries and refuses when none exist (`control 1: no model_overrides entry to remove`); a pi plan has none by design. Redefine control 1 for pi: remove the `resolve_model_ids` omit (or use the `pi.sonnet` set entry) and require the previously-passing agents to start failing, so the oracle is shown to discriminate.
  - Effect assertions: five L1 handler probes, one per combination, asserting `pi.sonnet` set -> steers, others -> `undefined` (D-07).
  - Informational row is claude-only; keep it so.
- Hosts table of the 4 existing matrices lives in the same test file; keep `_ROW_COUNT` logic.

## R6: Label lift and skill-judge

**Gates before the lift** (SPEC R6, ROADMAP SC2): R4 and R5 pass. Because R4's acceptance is the owner's interactive session, the honest sequencing is the Phase 20/21 pattern: land the headless evidence and a "validated headless; interactive confirmation pending" row (`| cursor host | validated headless ... pending |` is the precedent in SKILL.md and a pinned test `test_cursor_label_lifted_with_evidence_pointer`), then remove "pending" when the owner's artifacts return. Do not remove the label on headless evidence alone: SPEC R6 empty edge says "the label stays when any of R4/R5 fails".
**Edits that move together** (all verified present): SKILL.md Limits row (`| pi hosts | **not live-validated** |`, line 253 region), the `required` phrase list in `test_required_statements` (`"not live-validated"` stays only while another host still carries it; check that the phrase still appears elsewhere or update the list), `test_cursor_label_lifted_with_evidence_pointer` (asserts the pi row keeps the label), README row 45, `_LABEL_PI` and the `detect_current_runtime` docstring, and `ai-kit-gsd-curated-config` SKILL.md must state the R2 verdict for pi.

**Skill-judge procedure** (AGENTS.md: no Critical/Important left or score >= 96/120, and no regression vs baseline):
- Baselines recorded in Phase 21: in-session 110/120, pi gpt-6.1-sol 114/120 (both 0 Critical/0 Important) at digest `85da5a6682d937c5` [VERIFIED: 21-SKILL-JUDGE.md header read this session]. The digest covers `SKILL.md` plus `references/`, computed by `python3 tests/gsd_curated_eval.py digest` (`skill_digest`, 16 hex chars) [VERIFIED: `gsd_curated_eval.py:420-440, 488-500`]; `digest --check` validates the judge tables.
- Owner decision 2026-10-23 (task brief): judges are one clean-context native Opus subagent plus opencode with `router-env/my-plan-review`. The repo already has that lane: `.planning/config.json` defines reviewer instance `opencode-plan-review` with `"model": "router-env/my-plan-review"` [VERIFIED: `.planning/config.json` lines 52-56]. Run through the template-6 runner as in Phase 21 (`--prefer opencode --model-opencode router-env/my-plan-review --mode review --no-preamble --timeout <n> --outer-timeout <n+30>`; the `--model-<runtime>` flag pattern is [VERIFIED: runner `cross-ai.mjs` arg examples `--model-pi`], the opencode instance of it is [ASSUMED]).
- No baseline exists for the new opencode judge. Procedure: judge the pre-change digest first (baseline row) and the post-change digest second, per judge; the native Opus subagent baseline is compared against Phase 21's in-session 110/120 as context, not as a floor (different judge instance). Fix rounds capped at 2 as in Phase 21; each report must carry its own `DIGEST` equal to the tree it judged; a pending marker blocks phase close (21-06 Task 2 precondition).
- Run constraints from precedent: no commit and no write outside `tmp/` while a judge runs; secret-scan and `$HOME` grep on reports before they move into `skill-judge/`.
- The memory note that names pi gpt-6.1-sol as the second judge is superseded for this phase by the owner decision above; a quota-blocked judge is recorded as "judge unavailable" with the status line verbatim, never as a pass.

## R7 and gates: verify commands proven in Phases 20-21.3

| Purpose | Command | Notes |
|---------|---------|-------|
| Pi parser + snapshot tests | `python3 -m unittest tests.test_ai_kit_spec.TestPiRpcModels` | Ran this session: green |
| Curated-config apply/label tests | `python3 -m unittest tests.test_curated_config_apply` | Ran this session: 98 tests OK |
| Recommend/golden | `python3 -m unittest tests.test_curated_config_recommend tests.test_curated_config_golden tests.test_curated_config_skills` | Existing modules |
| Matrix (real node, no model) | `python3 -m unittest tests.test_ai_kit_gsd_curated_config_matrix` and `python3 tests/gsd_curated_eval.py matrix --host <h> --home <scratch>` | Pi not accepted by `--host` yet |
| Harness unit tests | `python3 -m unittest tests.test_gsd_curated_eval` | 4500-line module |
| Group runner | `python3 tools/run_unittest_parallel.py --group unit` (also `integration`, `e2e`, `arch`) | CPU cap rule applies, do not hardcode workers |
| Full gates | `make test` then `make validate` | Required by R7; ~600 s full |
| Digest / secret scan | `python3 tests/gsd_curated_eval.py digest` / `secret-scan` | Pre-judge and pre-commit of evidence |
| Protected-set guard | `python3 tests/gsd_curated_eval.py snapshot --out <file>` then `snapshot --check <file>` | Needs the pi entries above |
| Skill rules checks | `make lint` (shellcheck + py_compile) | |

Fix threshold (20 D-04, SPEC R7): one Python module stays in-phase with a same-commit regression test; two modules or a changed CONTEXT decision becomes a decimal phase. Candidate fixes found by this research and their module counts: `reasoning_modes` rule (detection.py, 1 module; plus its consumers' goldens if values change, which may push it to 2 -> check), `max_tokens` field (1), `pi.sonnet` candidates (inventory.py + recommend.py = 2 modules; treat as part of R3, not R7, since R3 owns the pi plan), `_PI_SKILL_SKIP` stale version text (apply.py, 1).

## Code Examples

### L1 handler probe (agent-runnable, offline)
```javascript
// Source: tmp/p22/l1-probe.cjs (this session); engine root = installed gsd-core package dir
const ext = require(path.join(pkgRoot, 'pi', 'gsd.cjs'));
const h = {}; ext({ registerCommand() {}, registerTool() {}, on(e, f) { h[e] = f; } });
const r = await h.before_provider_request({ payload: { model: 'sel' } }, { cwd: projectWithConfig });
```

### Offline RPC enumeration command (R1)
```bash
# Source: detection.py PI_RPC_ARGS / PI_RPC_REQUEST; scratch agent dir only in tests
printf '{"id":"1","type":"get_available_models"}\n' | \
  PI_CODING_AGENT_DIR=<scratch> pi --mode rpc --offline --no-session --no-extensions \
  --no-skills --no-context-files --no-mcp
# empty scratch dir -> {"id":"1","type":"response","command":"get_available_models","success":true,"data":{"models":[]}}
```

### Fixture post-processing guard (R1)
```python
# strip transport fields before commit; fail closed
for m in models: m.pop("baseUrl", None); m.pop("headers", None)
assert "baseUrl" not in text and "apiKey" not in text.lower()
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `pi --list-models` table | RPC `get_available_models` | 22 D-04 / Phase 18 | Exact integers, `thinkingLevelMap`, failure visible |
| Assume per-agent `pi --model` wiring | Registry-checked: no named dispatch | 2026-10-14 amendment | Verdict vocabulary gains session-steer |
| Session provider unknown at plan time | `PI_PROVIDER`/`PI_MODEL` exported to the bash tool | documented in pi 1.3.0 docs | `pi.sonnet` candidates can be generated |
| pi 1.2.0 / gsd-core 1.16 | pi 1.3.0 / gsd-core 1.17.0 on this machine | by 2026-10-23 | Re-verified: registry, hook source and RPC envelope unchanged; `_PI_SKILL_SKIP` text mentions 1.16.0 |

**Deprecated/outdated:** the SPEC's "85 models on 2026-10-14" and "pi 1.2.0" are historical; fixtures pin themselves, tests must not depend on the live count.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | pi 1.2.0 also exported `PI_PROVIDER`/`PI_MODEL` to shell tool children (the doc read is 1.3.0's; the Phase 21 env dump shows the names were present in some pi-launched context) | R3 | Candidate generation silently empty on older pi; need a fallback ask |
| A2 | Substituting a model id across different `api` values of the same provider is unsafe, so candidates should match the active model's `api` | R3 | Offering too few (harmless) or too many (breaks session) candidates |
| A3 | The opencode judge flag is `--model-opencode router-env/my-plan-review` in the template-6 runner | R6 | Judge dispatch fails; fix flag name from `--help` before the run |
| A4 | Keeping `None` as the "structured error" for R1 satisfies SPEC R1 | R1 | Owner may want an explicit error reason; adds a second module |
| A5 | Including/excluding `off` in `reasoning_modes` does not change cross-AI effort pinning outcomes | Pitfall 4 | Goldens or `cross_ai.py` effort selection shift; needs a diff review |
| A6 | A provider echoing the served model is common for direct providers, rare for routers | Pitfall 6 | L3 more often inconclusive than expected |
| A7 | L2 (localhost mock, no credentials) is permitted for the agent in the execution phase | R2 | Falls back to the analyzer's 2026-10-14 evidence only |

## Open Questions

1. **May the agent re-run L2 (localhost mock provider) in the execution phase, and the headless pi smoke through the cross-AI runner?**
   - Known: both use pi's agent loop without or with a model call; the analyzer ran L2 before; Phase 21 ran a headless cursor smoke.
   - Unclear: whether this phase's run rules extend to them (this research session did not run either).
   - Recommendation: yes for L2 (no credentials, localhost), and yes for the headless smoke under the quota supervision contract; L3 stays owner-approved.
2. **Real 85-model capture:** is one RPC run against the real agent dir acceptable (with before/after hashes of every pi file but `auth.json`), or does the owner run it?
   - Known: an empty agent dir returns 0 models; pi writes into the agent dir.
   - Recommendation: owner runs it as the first step of 22-INTERACTIVE-PI.md and returns the stripped fixture.
3. **Does L3 get a router lane that echoes the served model?** Without `responseModel` the observation is `inconclusive`. Pick a direct provider (anthropic or xai) for the L3 arm, router-env only as a second arm.
4. **Does pi persist project trust under `~/.pi/agent` (CONTEXT specific)?** Answer: yes, `~/.pi/agent/trust.json` via `/trust`; `--approve` is one-shot [CITED: pi docs]. Remaining question: whether the interactive prompt's "yes" persists by default; the owner run should note it and the guard should allow `trust.json` to change only in that step.
5. **Does steering on a real provider work with `provider/model`?** Answer from the hook: it passes the value verbatim, so a qualified string reaches the provider (L1). Whether a router accepts it is unobserved; the plan offers bare ids only, so this stays a documented non-goal.
6. **Upstream "hard-coded sonnet tier" quirk:** the hook is registered without a tier argument and defaults to `sonnet`; GSD cannot steer opus/haiku until upstream passes a tier signal. Worth an upstream issue (outside this phase).
7. **`context_window`/`max_tokens` into the snapshot?** Changes `RUNTIMES_SCHEMA_VERSION` (currently 5) and the `catalog_adapter`; SPEC R1 acceptance does not require it. Recommendation: parser-level only unless a consumer needs it.
8. **`_PI_SKILL_SKIP` text cites gsd-core 1.16.0.** Re-run the pi canonicalization check on 1.17.0 before the text is kept or reworded.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| node | gsd-tools, installer, L1 | yes | v24.21.0 (Volta shim; use `process.execPath` under temp HOME) | none needed |
| pi | R1 live capture, L2/L3, interactive | yes | 1.3.0 | hermetic fixtures |
| `@opengsd/gsd-core` installer cache | R4 local install | yes | 1.17.0 (two caches), 1.13.0 (one) | `--installer-dir` |
| opencode | skill-judge lane | yes | v2.0.31 | in-session judge only, recorded as unavailable |
| uv | `make test` unit-uv, wizard tiers | yes | 0.11.28 | none |
| python3 | tests | yes | 3.14.7 | none |
| bun | pi host runtime | yes | 1.3.14 | none |
| Real pi credentials / login | L3, interactive smoke | owner-only; not probed | unknown (default `openai-codex` login is gone per CONTEXT) | none; owner picks a model first |

**Missing dependencies with no fallback:** the owner's interactive session and credentials for R4 acceptance and L3.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | stdlib `unittest` through `tools/run_unittest_parallel.py` (groups unit, unit-uv, integration, e2e, arch) |
| Config file | `Makefile`, `.pre-commit-config.yaml`; group lists pinned by `tests/test_gate_scope.py` |
| Quick run command | `python3 -m unittest <touched module>` |
| Full suite command | `make test && make validate` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SPEC-05 | Trimmed real RPC capture yields 85 entries, exact ints, provider split; empty/garbled/missing -> `None` | unit | `python3 -m unittest tests.test_ai_kit_spec.TestPiRpcModels` | class exists; fixture replacement and 85-count test are Wave 0 |
| SPEC-05 | `reasoning_modes` follows pi's rule; `max_tokens` exact | unit | same | Wave 0 |
| R3 | pi plans: no `model_overrides.*`, verbatim labels, opt-in `pi.sonnet` bare ids of session provider only | unit + golden | `python3 -m unittest tests.test_curated_config_recommend tests.test_curated_config_golden tests.test_curated_config_skills` | exists; assertions change |
| R2 | L1: only `pi.sonnet` steers; `""` fails open; qualified string passes verbatim | node-gated e2e | `python3 -m unittest tests.test_curated_config_e2e` (new case) | Wave 0 |
| APP-05 | Pi matrix: tier equals oracle, `model == ""` under omit, discriminating control 1 | e2e real node | `python3 -m unittest tests.test_ai_kit_gsd_curated_config_matrix` | Wave 0 (pi class + harness branches) |
| EVAL-08 | Smoke 10 steps incl. forced-failure restore and ai-kit byte-identical | harness e2e + evidence doc | `python3 tests/gsd_curated_eval.py smoke --host pi --evidence-out <file>` | Wave 0 (pi branches) |
| EVAL-08 | Interactive pi session run | manual (owner) | `22-INTERACTIVE-PI.md` steps | Wave 0 (document) |
| R6 | Label lifted only with evidence; pinned strings updated | unit | `python3 -m unittest tests.test_curated_config_apply` | exists; edit in lift commit |
| R6 | skill-judge no regression | judge runs | digest + two judges (see R6) | evidence doc |
| MUST NOT | No key or `baseUrl` in evidence/fixtures | scan | `python3 tests/gsd_curated_eval.py secret-scan` plus fixture assertion | exists |

### Sampling Rate
- **Per task commit:** the touched module's quick command (< 30 s).
- **Per wave merge:** `--group unit` and `--group arch`.
- **Phase gate:** `make test` and `make validate` green before `/gsd-verify-work`.

### Wave 0 Gaps
- [ ] Trimmed real RPC fixture plus 85-count/provider-split test (owner supplies the capture)
- [ ] pi branches in `tests/gsd_curated_eval.py` (matrix choices, oracle, control 1, `_generated_paths`, `_baked_chain`, protected set)
- [ ] pi class in the matrix test module
- [ ] Node-gated L1 probe test
- [ ] Verbatim label assertions
- [ ] `22-INTERACTIVE-PI.md` owner script (names-only env, `pi --skill`, `PI_CODING_AGENT` check, trust prompt, L3 arms)

## Security Domain

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | n/a (never touch pi auth) |
| V3 Session Management | no | n/a |
| V4 Access Control | yes | Protected-set snapshot of `~/.pi/agent`, `~/.gsd`, `~/.claude`, project trust is the owner's consent action |
| V5 Input Validation | yes | Parser treats subprocess stdout as untrusted JSON: no raise, skip malformed items, never `eval`; override value validated against enumerated bare ids |
| V6 Cryptography / secret handling | yes | No `auth.json` read or hashed, no key or `baseUrl` in fixtures/evidence, names-only env dumps, secret-scan before commit |

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Credential leak into fixture or evidence | Information disclosure | Strip `baseUrl`/headers, assertion + secret-scan, names-only env |
| Project extension runs arbitrary code once trusted | Elevation | Trust only a scratch project; owner-granted trust; `--approve` one-shot |
| Wrong `model` on every request (provider-qualified id) | Tampering/DoS of the session | Bare ids of the active provider only |
| Runner child mistaking itself for the host | Spoofing | `HOST_SIGNAL_ENV_VARS` scrub (covers `PI_CODING_AGENT`, `AI_AGENT`) |
| Installer writing real `~/.gsd/defaults.json` | Tampering | Temp HOME + sha256 guard |

## Project Constraints (from AGENTS.md)

- English only in all written artifacts; no machine-specific absolute paths in source, tests, plans or generated commands (use repo-relative or discovered paths).
- Runtime code stays stdlib-only; atomic config writes (`mkstemp` + `os.replace`); no result shown with more certainty than its sourcing (reverse-engineered or documented-only items are flagged).
- New or materially changed `SKILL.md` passes the skill-judge loop (no Critical/Important, or >= 96/120, no regression vs baseline).
- One coherent buildable logical commit with tests and docs; never `--no-verify`; never reset/clean user work; fix failing tests, no deflection.
- `tests/test_arch.py` structural rules extend, not bypass; do not use the user's real config files as fixtures; kill spawned processes after e2e; update READMEs and docs after significant changes; scratch files under `./tmp/`; fold commits before closing; plans must be cross-AI reviewable, cheap-model executable and path-agnostic.
- Live-verify claims against the installed tools; amend REQUIREMENTS/ROADMAP when a verified fact contradicts them (this phase's R1/R3 "target" text is partly already satisfied: record that in the plan rather than redoing it).
- Global: GSD is per-project only; never write GSD artifacts into `~/.claude`; use the project-local `.claude/gsd-core/bin/gsd-tools.cjs`.

## Sources

### Primary (HIGH confidence)
- Repo files read this session: `22-SPEC.md`, `22-CONTEXT.md`, `22-DISCUSSION-LOG.md`, `ROADMAP.md` (Phase 22), `REQUIREMENTS.md` rows, `detection.py`, `tests/test_ai_kit_spec.py` (pi class), `tests/fixtures/pi_rpc_get_available_models.json`, `presets.py`, `recommend.py`, `apply.py`, `tests/test_curated_config_*`, `tests/gsd_curated_eval.py`, `tests/test_ai_kit_gsd_curated_config_matrix.py`, `21-SMOKE-CURSOR.md`, `21-INTERACTIVE-CURSOR.md`, `21-SKILL-JUDGE.md`, `.planning/config.json`
- Live local runs: `pi --version`, scratch RPC (0 models), L1 probe, `resolve-model` under pi, `--pi --local` install under a temp HOME, pi matrix attempt (crash)
- gsd-core 1.17.0: `.claude/gsd-core/bin/lib/capability-registry.cjs:3167-3215`, npx-cache `pi/gsd.cjs`
- pi 1.3.0 package: `dist/core/extensions/runner.js:1068-1103`, `dist/core/extensions/types.d.ts:694`, `@earendil-works/pi-ai` `dist/models.js:679-691` and `dist/types.d.ts:645-649`

### Secondary (MEDIUM confidence)
- pi docs shipped with the package: `docs/rpc-commands.md` (get_available_models, Model object), `docs/environment-variables.md`, `docs/security.md` (project trust), `docs/cli.md` (`--approve`, `-ne`, `--skill`, `--mode`), `docs/message-types.md` (`responseModel`), `docs/virtual-models.md`, `docs/session-format.md`

### Tertiary (LOW confidence)
- None used for claims; all `[ASSUMED]` items are listed in the Assumptions Log.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH, nothing new is introduced and versions were read from the machine.
- Architecture: HIGH for R1/R3 repo state (read and run); MEDIUM for the pi smoke/matrix harness design (not yet built).
- Pitfalls: HIGH for those reproduced this session (Volta, agent-dir writes, empty list, matrix crash); MEDIUM for L3 echo behaviour.

**Research date:** 2026-10-23
**Valid until:** 2026-11-06 (pi and gsd-core both moved a minor version in nine days)
