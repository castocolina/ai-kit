# Status-Line Config Binding Layer - Product Requirements Document (PRD)

## Requirements Description

### Background

- **Business Problem**: The `cfg_` block of `tools/status-line.py` (18 functions) resolves
  configuration with two *different* validation regimes braided into per-section logic:
  the **env** layer parses strings via single-type helpers (`cfg_env_bool`, `cfg_env_int`,
  `cfg_to_int`) routed by a hand-written `if token == "SEGMENT" / GIT / EXTERNAL` dispatcher,
  while the **TOML** layer type-checks already-parsed values with `isinstance` branches
  scattered across `cfg_resolve_segments`, `cfg_resolve_external`, and the `[git]` loop. The
  env-name↔config-path mapping is therefore encoded **twice** — once in the typed `Config`
  model and once in the router — so the two can drift. That drift risk is real enough that
  the architecture-refinement effort had to add an AST test (FR-8 "single env reader") purely
  to police it. Validation warnings are *also* duplicated: emitted inline by `cfg_*` during
  render **and** re-implemented by `tools/statusline-doctor.py`.
- **Target Users**: The maintainer (clean-architecture / low-entropy bar) and end users who
  configure the status line via `statusline.toml` and `CC_AI_KIT_*` environment variables.
- **Value Proposition**: Collapse the two regimes into one **type-directed converter** shared
  by env, TOML, and the doctor; make the env↔structure mapping **mechanical** (the Spring Boot
  relaxed-binding insight: env name = upper-cased projection of the config path); make
  "single reader" **true by construction** rather than test-enforced; and centralize all
  validation/warnings in the doctor so the render path binds **silently**. Net: fewer functions,
  one validation locus, auto-extending to new fields with zero reader edits.

### Feature Overview

- **Core Features**:
  1. A **ConversionService** (`cfg_convert`): one type-directed converter (bool + int) that
     turns a raw value (env string or already-typed TOML value) into a typed value **or** a
     structured *problem*, with the dispatch open to extend.
  2. An **access layer** (`cfg_source_get`): fetch the raw value for a config path from a
     source — env (via mechanical `CC_AI_KIT_<PATH>` name projection) or a TOML dict (nested).
  3. A **bind layer** (`cfg_bind`): a generic walk over the typed `Config` that, per field,
     does access → convert → apply the section's merge policy; segments bound as the one
     map-rule. Eliminates the current **two-pass** env invocation.
  4. **Silent render / doctor-owned validation**: the render path binds leniently (problems →
     fall back to default, no stderr output); the doctor consumes the same problems and is the
     **sole** emitter of all config warnings, validating both the TOML file and the env.
  5. **FR-8 rule reduction**: trim the AST "single env reader" rule to the minimal guard now
     that the bind walk makes single-reader structural.
  6. **Extraction-seam block comments**: zero-code block-header notes on `probe_`/`util_`/`fmt_`
     recording the "shared by default; classify by nature; single-kind seam noted" rule.

- **Feature Boundaries**:
  - **In scope**: the env-binding refactor (access/convert/bind), the shared converter reused by
    the doctor, moving all validation/warnings to the doctor, the FR-8 rule reduction, and the
    seam comments.
  - **NOT in scope**:
    - The heterogeneous **TOML merge policies** are preserved as-is: `[segments]`/`[palette]`/
      `[git]` MERGE; `[[line]]`/`[ramp.X]` REPLACE. `cfg_resolve_layout`, ramp resolution, and
      external placement keep their structural handling — the bind layer does not attempt a
      universal deep-merge.
    - **float / list scalar** conversion (no such config field exists today — YAGNI; the
      dispatch is left open so adding one later is a one-line table entry).
    - **Dynamic external-segment config** (`config.get('opt', default)`) — that remains the
      separate deferred PRD `statusline-config-extensibility-v1.0-prd.md`.
    - Any **renaming by consumer or by sub-domain** (`probe_kind_`, `util_kind_`, `seg_util_`):
      explicitly rejected — see Design Decisions.

- **User Scenarios**:
  1. A user sets `CC_AI_KIT_GIT_CACHE_TTL=10` → bound to `config.git.cache_ttl` with no
     per-key code; render is unaffected by any warning noise.
  2. A user typos `CC_AI_KIT_SEGMENT_ALT_COST=banana` → render silently keeps the default;
     `statusline-doctor.py --check` reports "must be true/false".
  3. A user keeps a deprecated `CC_AI_KIT_GIT_TTL` → it still functions (forwarded silently at
     runtime); the doctor reports the deprecation.

### Detailed Requirements

- **Input/Output**:
  - Inputs: the typed default `Config`, the parsed TOML dict, and the `Env` mapping.
  - Output (render): a fully resolved `Config`, byte-identical in its effect on **stdout** to
    today; **no stderr** emitted by the render path.
  - Output (doctor): the resolved `Config` **plus** the ordered list of problems (deprecations,
    invalid values, unknown keys, malformed file, out-of-range clamps), formatted as the dim
    warnings the render path used to emit.

- **User Interaction**: unchanged CLI surface. `status-line.py` renders only (no flags). The
  doctor's existing flags (`--check`, `--doctor`, `--print-config`) gain the full validation
  responsibility.

- **Data Requirements**:
  - `cfg_convert(raw, kind) -> ConvertResult` where `ConvertResult` carries `value` and/or
    `problem`. Bool conversion is **tri-state-aware**: it must distinguish **absent** (no
    override → fall through), **present-and-valid**, and **present-but-invalid** (→ problem).
  - The env-name projection is deterministic: `config.<group>.<field>` ⇄
    `CC_AI_KIT_<GROUP>_<FIELD>` (upper-cased); `segments.<key>` ⇄ `CC_AI_KIT_SEGMENT_<KEY>`.
  - The deprecated-alias map and the legacy-segment-key map remain **data**; forwarding is
    applied during bind (silently); the deprecation is surfaced as a *problem* (doctor-only).

- **Edge Cases**:
  - Malformed TOML → render uses `{}` silently; doctor reports the parse error.
  - `CC_AI_KIT_CONFIG_FILE` bootstrap read stays the one explicit pre-bind env read (chicken/egg).
  - External provider ids are unknown until discovery → segments are bound **after** discovery
    (single pass), not via the current throwaway double call.
  - Unknown `[git]`/segment/palette/ramp keys → ignored at render; reported by doctor.
  - An env value for a key whose segment does not exist → ignored at render; reported by doctor.

### Success Metrics

Measurable targets (verified at implementation; ranges are estimates to confirm against the
actual diff, the invariants are firm):

- **Duplication eliminated (primary)**: the env-name↔config-path mapping exists in **exactly one
  place** (the structure walk), down from two (model + router); config validation rules exist in
  **exactly one place** (`cfg_convert`), down from two (render inline + doctor). This is the
  core win — measured by absence of the second encoding, not by line count.
- **`cfg_` function count**: **18 → ~12–13** (delete the config-env string parsers `cfg_env_bool`
  and `cfg_env_int`; collapse the per-token router; net of `cfg_convert` + `cfg_source_get` +
  `cfg_bind`). Separately, `cfg_to_int` is **reclassified to `util_to_int`** — call-site analysis
  shows it is a pure probe-support parser (parses `tput`/`ps` output, called only from `probe_*`),
  misfiled in the `cfg_` block; moving it removes a `probe_ → cfg_` layering smell and matches
  "classify by nature, not caller". It is **not** absorbed into `cfg_convert` (which is for config
  values, not subprocess output).
- **Line count (secondary signal — relocation, not deletion, for warnings)**:
  - `tools/status-line.py`: **strictly decreases** (firm invariant). Estimate ~80–150 lines down
    (helpers + router + inline warnings + two-pass removed).
  - `tools/statusline-doctor.py`: may *increase* as it absorbs the consolidated validation; this
    is dedup of logic it already partly carried, not new behavior.
  - **System total (both modules): no net increase** (firm invariant) — target flat-to-down.
- **Single reader, proven not asserted-in-prose**: a test adds a throwaway typed config field and
  confirms it binds from env + TOML with **zero edits** to the reader/bind code (auto-extending).
- **Silent render, proven**: a test asserts the render path writes **0 bytes to stderr** on a
  deliberately broken config (bad int, unknown key, deprecated alias) while still rendering the
  fallback line byte-identically.

## Design Decisions

### Technical Approach

- **Architecture Choice**: three thin layers, the Spring `PropertySource` → `ConversionService`
  → `Binder` split, in stdlib only:
  1. **access** (`cfg_source_get`) — "raw value at this path from this source"; the only place
    that knows the env-name projection and the nested-TOML lookup.
  2. **convert** (`cfg_convert`) — "raw → typed | problem"; the only place that knows bool/int
    rules and the warning text. One dispatch, open to extend.
  3. **bind** (`cfg_bind`) — walks the typed `Config`, per field calls access→convert and
    applies the section merge policy; binds `segments` as the single map-rule.
  - **One converter, two consumption modes**: render discards problems (lenient/silent); the
    doctor collects and formats them. This is what lets validation centralize without
    duplicating the rules.
- **Key Components**:
  - New: `cfg_convert`, `ConvertResult`, `cfg_source_get`, `cfg_bind` (names indicative).
  - Removed/absorbed: `cfg_env_bool`, `cfg_env_int`, `cfg_to_int`, the per-token router body of
    `cfg_env_apply_overrides`, the two-pass call in `cfg_load_config`, and the scattered
    `isinstance` validation branches.
  - `statusline-doctor.py`: imports `cfg_convert`/`cfg_bind` problem output; gains a single
    validation pass over file + env; becomes the sole warning emitter.
- **Data Storage**: none. Pure in-memory config resolution; runtime stays stdlib-only.
- **Interface Design**: `cfg_load_config(env) -> Config` keeps its signature; a sibling
  `cfg_load_config_verbose(env) -> (Config, list[Problem])` (or equivalent) feeds the doctor.
- **Bind-walk scope (boundary)**: the walk binds **only the `line_conf` groups** — `segments`,
  `git`, `external`, `palette`, `ramps`. It does **not** touch SHELL geometry reads (terminal
  size, COLUMNS/LINES), the JSON-derived `effort` level, or the `CC_AI_KIT_CONFIG_FILE` bootstrap
  read (which stays the one explicit pre-bind env read). An implementer must not sweep those into
  the walk.
- **Precedence (explicit per-field bind rule)**: for every bound field the order is
  **default < TOML < env** — env, when present-and-valid, wins; present-but-invalid falls back to
  the TOML/default value (and yields a problem); absent falls through. This is a per-field rule of
  the bind layer, not an artifact of call ordering.

### Validation & Warning Parity Contract

Moving warnings to the doctor must not silently change what users see when they *do* run the
doctor. The contract:

- **Problem taxonomy** (the complete set the converter/bind layer must surface, each tagged with a
  stable class): `deprecated-alias`, `deprecated-segment-key`, `invalid-value` (bad int / non-bool),
  `unknown-key` (segment / `[git]` / palette / ramp), `malformed-file` (TOML parse error),
  `out-of-range` (external segment line clamp).
- **Text parity**: for each class, the doctor emits the **byte-identical** dim message the render
  path emits today (same wording, same `_DIM`/`RESET` wrapping, same stream = stderr). The render
  path emits **none** of them.
- **Coverage parity**: the doctor validates **both** the TOML file **and** the live env (it already
  reads both for dry-render), so no problem class that render used to catch is lost.
- **Test**: a captured-stderr fixture (the exact strings, asserted in `tests/test_statusline_doctor.py`)
  is the parity oracle; the corresponding render-path stderr assertions are deleted (render is
  silent) — see Phase 3.

### Rationale (entropy analysis)

Grounded in `reducing-entropy` (data-over-abstractions + simplicity-vs-easy):
- The config **is** data; binding is a generic op over it — *"one bind over the `Config`
  structure beats N branches over N sections."* The mechanical env-name projection removes the
  duplicated mapping, so "single reader" becomes structural (not test-enforced).
- **Rejected alternatives** (kept here so they are not re-litigated): renaming helpers by
  *consumer* (`seg_util_`/`alt_util_`) or by *sub-domain* (`probe_kind_`/`util_kind_`). Both add
  a second classification axis to the prefix; the highest-fan-in helpers (`util_first_fitting` ×18,
  `util_icon` ×14) are cross-tier/cross-domain and would force duplication or a `_misc_` junk
  drawer — churn with zero deletion. The prefix carries the **tier**, the name carries the
  **domain**, the **block ordering** carries the grouping: one axis per mechanism.

### Constraints

- **Performance Requirements**: render is no slower (silent bind removes stderr writes);
  FR-R.2 probe-timing test stays green.
- **Compatibility**: deprecated `CC_AI_KIT_*` aliases and legacy segment keys keep working
  identically at runtime. Golden **stdout** stays byte-identical (never `UPDATE_GOLDEN=1`).
- **Security**: none new (no new I/O, no subprocess, no network).
- **Scalability**: a new typed config field needs **zero** reader edits — access/convert/bind
  pick it up from the structure (the auto-extending property).

### Risk Assessment

- **Technical Risks**:
  - *Behavior change — silent render*: users lose live stderr nags. **Mitigation**: the doctor
    becomes the complete validation surface (file + env); README and `statusline.toml.sample`
    document that `statusline-doctor.py --check`/`--doctor` is where config problems surface.
  - *Tri-state bool regression*: conflating "absent" with "invalid" would change precedence.
    **Mitigation**: `ConvertResult` models the three states explicitly; dedicated tests.
  - *Two-pass removal ordering*: segments must bind after provider discovery. **Mitigation**:
    bind scalars (git/external) first, discover, then bind the segment map once — tested.
- **Dependency Risks**: none (stdlib only).
- **Schedule Risks**: test-migration churn (stderr-warning assertions move from render tests to
  doctor tests). **Mitigation**: isolate the behavior change to its own phase so each phase
  stays green; migrate assertions mechanically.

## Acceptance Criteria

### Functional Acceptance

- [ ] **FR-1 ConversionService**: a single `cfg_convert` handles bool and int, returns a
      value-or-problem, is tri-state-aware for bool, and is the only place encoding those rules;
      `cfg_env_bool`/`cfg_env_int`/`cfg_to_int` are gone.
- [ ] **FR-2 Access**: one `cfg_source_get` resolves a config path from env (mechanical
      `CC_AI_KIT_<PATH>` projection) and from a TOML dict; the env-name mapping exists in exactly
      one place.
- [ ] **FR-3 Bind**: `cfg_load_config` resolves git/external/segments through access→convert→bind
      with the section merge policy preserved; the throwaway **two-pass** env call is eliminated
      (segments bound once, after discovery).
- [ ] **FR-4 Silent render / doctor validation**: the render path emits **no** stderr config
      warnings; `statusline-doctor.py` reports every problem class (deprecation, invalid value,
      unknown key, malformed file, out-of-range clamp) for both file and env.
- [ ] **FR-4a Parity contract**: for each problem class the doctor's message is byte-identical to
      the message render emitted before; verified by a captured-stderr fixture in
      `tests/test_statusline_doctor.py`; the render path writes 0 bytes to stderr on broken config.
- [ ] **FR-3a Bind boundary + precedence**: the walk binds only the `line_conf` groups (not SHELL
      geometry, JSON effort, or the bootstrap read); per-field precedence is default < TOML < env
      with present-but-invalid falling back (and yielding a problem).
- [ ] **FR-5 Back-compat**: deprecated env aliases and legacy segment keys still forward and
      function identically at runtime; the doctor reports them as deprecations.
- [ ] **FR-6 FR-8 rule reduced**: the AST "single env reader" rule is trimmed to the minimal
      still-meaningful guard, allowlist updated to the bind symbol; redundant clauses removed.
- [ ] **FR-7 Seam comments**: `probe_`/`util_`/`fmt_` block headers carry the "shared by default;
      classify by nature; single-kind seam noted" rule; no per-function census; no runtime code.

### Quality Standards

- [ ] **Golden**: `tests/fixtures/golden/expected.txt` byte-identical (stdout) after every task;
      never `UPDATE_GOLDEN=1`.
- [ ] **Gate**: `make validate` (ruff / pylint / pyright-strict / vulture / shellcheck /
      py-compile) green at every task.
- [ ] **Tests**: `make test` green at every task; stderr-warning assertions relocated to
      `tests/test_statusline_doctor.py`; new tests for `cfg_convert` tri-state + projection + bind;
      a zero-edit-new-field test (single-reader proof) and a 0-byte-stderr render test (silent-render
      proof).
- [ ] **FR-R.2**: probe-timing test green throughout.
- [ ] **Runtime**: `status-line.py` and `statusline-doctor.py` stay stdlib-only; one-way doctor→core
      import preserved.

### User Acceptance

- [ ] **User Experience**: configuring via TOML/env behaves identically for valid input; invalid
      input is silently defaulted at render and surfaced by the doctor.
- [ ] **Documentation**: `README.md` and `tools/statusline.toml.sample` updated to state that the
      doctor is the validation surface and that render is silent.
- [ ] **Training Materials**: none required.

## Execution Phases

### Phase 0: Branch Setup
**Goal**: isolated workspace + green baseline.
- [ ] Create branch `refactor/status-line-config-binding` off `main`.
- [ ] Confirm `make validate && make test` green before any change.
- **Deliverables**: branch + recorded baseline.
- **Time**: ~15 min.

### Phase 1: Conversion layer
**Goal**: introduce `cfg_convert` + `ConvertResult`; collapse the parse helpers behavior-preservingly.
- [ ] TDD `cfg_convert` (bool tri-state, int, problem reporting; open dispatch).
- [ ] Replace internal uses of `cfg_env_bool`/`cfg_env_int`/`cfg_to_int` and the scattered
      `isinstance` checks with `cfg_convert`; **warnings still emitted from current sites** so
      behavior is byte-identical.
- [ ] Delete the three obsolete helpers.
- **Deliverables**: one converter; identical render/warn behavior; golden + gate green.
- **Time**: ~half day.

### Phase 2: Access + Bind layer
**Goal**: mechanical env projection + generic structure walk; kill the two-pass.
- [ ] TDD `cfg_source_get` (env projection + nested TOML).
- [ ] TDD `cfg_bind`; rewire `cfg_load_config` to bind git/external/segments via access→convert;
      preserve each section's merge/replace policy; bind segments once after discovery.
- [ ] Problems flow through the bind layer but are **still printed inline** (behavior parity).
- **Deliverables**: single-reader structural; two-pass removed; golden + gate + FR-R.2 green.
- **Time**: ~1 day.

### Phase 3: Silent render / doctor-owned validation (atomic behavior change)
**Goal**: render binds silently; doctor becomes the sole warning emitter.
- [ ] Render consumes `cfg_load_config` in lenient mode (problems discarded, no stderr).
- [ ] `statusline-doctor.py` gains the full file + env validation pass via the shared problem
      output; formats every problem class with the prior dim text.
- [ ] Migrate stderr-warning assertions from `test_status_line`/`test_external_segments` to
      `test_statusline_doctor`; add coverage for env-class problems.
- [ ] Update `README.md` + `statusline.toml.sample` (doctor is the validation surface).
- **Deliverables**: silent render; complete doctor validation; golden + gate + tests green.
- **Time**: ~1 day.

### Phase 4: FR-8 rule reduction + seam comments
**Goal**: trim the now-redundant arch rule; document extraction seams.
- [ ] Reduce the `tests/test_arch.py` "single env reader" rule to the minimal guard; update the
      allowlist to the bind symbol; keep the non-vacuity counterpart meaningful.
- [ ] Add block-header rule comments to the `probe_`/`util_`/`fmt_` banners (and the probe
      raw-vs-ctx-accessor note). Zero runtime code; no per-function census.
- **Deliverables**: reduced arch rule; seam documentation; golden + gate green.
- **Time**: ~half day.

### Phase 5: Compaction + final review + merge
**Goal**: ship to local main.
- [ ] Compact WIP commits into per-logical-unit commits via path-disjoint `git cherry-pick -n`
      replay (`rebase -i` is blocked); verify tree byte-identical to the pre-compaction tip.
- [ ] Final whole-implementation review against FR-1..FR-7 + constraints.
- [ ] `git merge --no-ff` into **local** `main`; **do NOT push**. Update memory.
- **Deliverables**: merged refactor; green gate; byte-identical golden vs main.
- **Time**: ~half day.

---

**Document Version**: 1.0
**Created**: 2026-06-23
**Clarification Rounds**: 2
**Quality Score**: 100/100
