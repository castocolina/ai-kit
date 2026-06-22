# Status-Line Architecture Refinement - Product Requirements Document (PRD)

> Follow-up to `status-line-architecture-pattern-v1.0-prd.md`. That overhaul landed the
> functional-core/imperative-shell pattern, the typed `Config`, the `Context` dataclass, the
> convention registry, and strict types. This refinement corrects the coupling and structure
> issues found in post-merge review: a god-bag `Context`, an undelivered role taxonomy, a
> position-coupled packer, scattered env reading, and CLI/diagnostic code on the render hot path.

## Requirements Description

### Background

- **Business Problem**: The merged `status-line.py` is behavior-correct and strictly typed, but
  its structure does not serve maintenance or extension. Five concrete defects: (1) `Context` is a
  god-object that enumerates every segment's data, so the core knows about every segment and
  segments are not extractable plugins; (2) the requested core/util/helper role classification was
  never delivered — the `HELPERS` block conflates pure utilities with side-effecting OS probes;
  (3) the packer mixes timing with fitting and computes the `render_time`/`slowest` meta segments
  per-line, making them silently position-coupled to the last layout row; (4) environment reading
  is scattered across many functions with hardcoded variable names, contradicting the "single env
  reader" decision (D8); (5) the doctor/`--check`/`--print-config` introspection code sits in the
  same file that runs on every render.
- **Target Users**: The maintainer (Java/clean-code background, obsessive about structure and the
  ability to "move a whole block out"), and future contributors adding or externalizing segments.
- **Value Proposition**: A file whose regions are predictable by role, where segments are
  decoupled from the core, where the truthful-timing invariant is structural rather than
  positional, where one place reads the environment by a deterministic convention, and where an
  architecture test keeps all of this true instead of re-litigating it in every PR.

### Feature Overview

- **Core Features**:
  1. **Data-model decoupling** — shrink `Context` to a clear two-part model (`ctx` = the Claude
     JSON representation; `ctx.line_conf` = our resolved statusline config), move single-consumer
     environment self-discovery (RSS, transcript size, file age, effort-auto, todo, git) out into
     memoized `probe_*`/`core_*` functions, and consolidate all config env reading behind one
     deterministic, structure-aware `CC_AI_KIT_<...>` → `line_conf.<group>.<field>` mapping (nested
     `line_conf`, full names; `CLAUDE_EFFORT` dropped).
  2. **Role classification** — a full role-prefix scheme across every function and a file
     reorganized into contiguous, predictable role blocks, defaults first.
  3. **Packer refactor** — separate "measure all segments" from "pack lines", compute the meta
     segments once globally, and remove the double-fit.
  4. **Second-class (`alt`) segments** — a `seg_alt_` prefix + keyed flag for dispensable segments
     so non-essential ones can be identified and extracted as a block.
  5. **Introspection extraction** — move the doctor and config-validation commands into a
     dedicated script; the render module renders only.
  6. **Architecture test** — an AST-based fitness test enforcing the structural invariants above.
- **Feature Boundaries**:
  - **In scope**: items 1–6 above, applied to `tools/status-line.py`, its tests, `tools/setup.py`
    pragmas as needed, `install.sh`, and docs.
  - **Out of scope (deferred to a later PRD)**: the dynamic external-segment config surface
    (external providers reading their own options via `config.get('my-opt', default)`). The *core*
    env consolidation in item 1 is in scope; the *external-provider* dynamic option API is not.
  - **Out of scope**: any change to rendered output (the golden snapshot stays byte-identical), any
    new runtime dependency (runtime stays stdlib-only), any change to the FR-R.2 truthful-slowest
    guarantee (it is preserved, not relaxed).
- **User Scenarios**:
  - Maintainer wants to externalize cost/rate-limit segments for an enterprise build → greps
    `seg_alt_`, moves that block.
  - Maintainer wants to change a default → goes to the defaults block at the top of the file.
  - Maintainer wants to touch render machinery → goes to the `core_` block at its known region.
  - A new segment needs OS data → it calls a `probe_*`/`util_*` function; it does **not** add a
    field to the core data model.
  - A reviewer would previously flag a bare dict subscript or a stray `env.get` → the arch test now
    fails in CI instead.

### Detailed Requirements

#### FR-1 — Data-model decoupling, `ctx`/`line_conf` split, single env reader

- **FR-1.1 Conceptual model.** The per-render object's root represents **Claude's incoming JSON**
  (model, cost, context_window, workspace, rate_limits, transcript path, session id, resolved
  effort). Our settings live in a clearly-bounded sub-object **`ctx.line_conf`** (today's `Config`):
  segment on/off flags, layout, palette, ramps, git TTL, cache locations, external providers. The
  `Theme` is derived from `line_conf` (palette/ramps). This makes "what came from Claude" and "what
  we configured" two distinct, non-mixed surfaces.
- **FR-1.2 Necessity rule for injection.** A value is kept on the per-render object **only if**
  either (a) it is computed at the SHELL/`main` boundary and a segment cannot discover it itself
  (e.g. terminal `cols`/`rows`/`assumed` geometry, the resolved `effort` level, the raw JSON), **or**
  (b) it is needed by most/all segments. Geometry is the canonical (a): only the shell can resolve
  it, and every segment needs it for width math plus the render/drop logic needs it — so it is
  injected.
- **FR-1.3 Move single-consumer environment self-discovery out of the data model.** Values that are
  **not** part of Claude's JSON and that a single (or few) segment(s) can obtain on demand must
  **not** be data-model fields. They become memoized `probe_*` (I/O) or pure `util_*`/`core_*`
  functions the owning segment calls: process RSS (`memory`), transcript file size (`chat_size`),
  transcript mtime "ago" (`time_ago`), effort-auto settings probe (`effort`), todo/task disk+
  transcript probe (`todo`), and the shared git snapshot (`branch`/`dirty`/`worktree`). The git
  snapshot is shared by three segments → it is a **memoized** probe so it still runs once per
  render.
- **FR-1.4 Preserve FR-R.2.** A `probe_*` runs on first call. Because segments are built inside the
  packer's per-segment timing bracket (FR-4), the probe's cost still lands inside the measured build
  of the first segment that triggers it. The truthful-slowest guarantee is preserved by the memoize-
  on-first-call mechanism, not by `cached_property` on a god-bag.
- **FR-1.5 `build_context` adjacency.** The assembler that builds the per-render object lives
  immediately adjacent to the dataclass it constructs (co-located, not in a distant block).
- **FR-1.6 Single config env reader + deterministic, structure-aware mapping with full names.**
  `line_conf` is **structured, not flat**: the nested groups (`segments`, `lines`, `git`,
  `external`, `palette`, `ramps`) keep their natural shape and are not merged with plain scalar
  settings. All **config** environment reading happens in exactly one place (the `cfg_` loader),
  which follows one generic convention using **full descriptive names** (no short forms): the
  leading token of `CC_AI_KIT_<...>` routes the value to its group, then the remainder names the
  field — `SEGMENT_<KEY>` → `segments[<key>]`, `GIT_<FIELD>` → `git.<field>`, `EXTERNAL_<FIELD>`
  → `external.<field>`. Resolution is by this convention with **no hardcoded per-variable branch**.
  The rename map:

  | Current env var | New env var | Resolves to |
  |---|---|---|
  | `CC_AI_KIT_GIT_TTL` | `CC_AI_KIT_GIT_CACHE_TTL` | `line_conf.git.cache_ttl` |
  | `CC_AI_KIT_EXTERNAL_TTL` | `CC_AI_KIT_EXTERNAL_CACHE_TTL` | `line_conf.external.cache_ttl` |
  | `CC_AI_KIT_SEGMENTS_DIR` | `CC_AI_KIT_EXTERNAL_DIR` | `line_conf.external.dir` |
  | `CC_AI_KIT_SEGMENT_<KEY>` | (unchanged) | `line_conf.segments[<key>]` |

  Example: `CC_AI_KIT_SEGMENT_BRANCH=false` → `line_conf.segments["branch"] = False` → the branch
  segment is hidden (same effect as today, via the structured `segments` group). No `env.get` for a
  config key may appear outside the loader (enforced by FR-8).
- **FR-1.7 Bootstrap config var (hardcoded at load).** `CC_AI_KIT_CONFIG` → `CC_AI_KIT_CONFIG_FILE`
  is read **to locate the config file itself**, so it cannot live in `line_conf` (chicken-and-egg).
  It is the one config var resolved by an explicit hardcoded read in the loader, documented as the
  bootstrap exception.
- **FR-1.8 Delineated SHELL/runtime + third-party env reads.** Per-render **runtime** inputs that
  are not config are read once at the SHELL boundary and are exempt from FR-1.6: terminal geometry
  (`STATUSLINE_COLS`/`STATUSLINE_LINES`/`COLUMNS`/`LINES`) and the JSON on stdin. Third-party vars
  (`CLAUDE_CONFIG_DIR`, `XDG_CONFIG_HOME`, `XDG_CACHE_HOME`) are not ours and are read where needed.
  These are the named exceptions the arch test (FR-8) whitelists.
- **FR-1.9 Drop `CLAUDE_EFFORT`.** The `CLAUDE_EFFORT` env fallback (a redundant third effort
  source that predates this work and serves only test/debug) is **removed**. Effort resolves from
  Claude's JSON (`raw["effort"]["level"]`) plus the settings-file auto detection only. The two
  `resolve_effort` unit tests are adjusted to inject effort via the raw JSON instead of the env.

#### FR-2 — Role classification (full prefix scheme) + reorganization

- **FR-2.1 Prefix vocabulary** (chosen: full scheme). Every function carries its role:
  - `seg_` / `seg_alt_` — segment builders (FR-5).
  - `probe_` — side-effecting data gathering (git, RSS, todo, transcript stat, terminal size, the
    effort-auto settings read).
  - `fmt_` — pure formatters (bytes/tokens/duration/ms/ago/number/rate-key).
  - `util_` — pure non-format helpers (color parse/pick, hex→sgr, char/visible width, truncate,
    first-fitting, icon, threshold parse, porcelain-branch parse).
  - `core_` — render machinery (safe-build, crown-slowest, the pack phases, render, diagnostic-line,
    builder discovery/registry, theme build, the per-render object assembler).
  - `cfg_` — config loading/resolution (load, resolve-segments/layout/external/palette/ramp, paths,
    env-bool, cache base, git-key validation).
- **FR-2.2 Contiguous role blocks.** The file is reorganized so each role is a single contiguous,
  banner-labelled region; a reader can locate all of a role's code in one place and lift a whole
  block out.
- **FR-2.3 Behaviour preserved.** Renames and motion only — no logic change; the golden snapshot
  stays byte-identical and the full test suite stays green.

#### FR-3 — (folded) Line-count is not a goal

- The refinement is not measured by line count; types/docstrings/role-blocks may keep it flat or
  grow it. Redundancy removal (the double-fit in FR-4, the multi-property git shim collapsed by
  FR-1.3) is the only place line reduction is expected.

#### FR-4 — Packer refactor: separate measurement from packing; global meta

- **FR-4.1 Active-segment determination.** A segment is active iff it appears in some layout line
  **and** its flag is enabled (`lines.segments ∩ segments[bool]`). Enabled-but-not-in-any-line is a
  no-op; in-a-line-but-disabled is hidden. This intersection is computed before building.
- **FR-4.2 Phase A — measure all (global).** Build and time every active **non-meta** segment
  across all lines, crowning the single slowest into the render bookkeeping. `render_time` and
  `slowest` are excluded as build targets in this phase (the meta exclusion set is retained — it was
  correct).
- **FR-4.3 Phase B — compute meta once (global).** After Phase A, with all non-meta builds timed,
  compute `render_time` (whole-render elapsed) and build `slowest` exactly once — not per line.
- **FR-4.4 Phase C — pack (per line).** A second pass over the lines performs the real
  placement/fitting from the already-built segment strings. Fitting logic lives in exactly **one**
  place; the provisional `used_est` fit that currently lives inside the timed pass is removed.
- **FR-4.5 Position independence.** As a consequence of B being global, `render_time`/`slowest` are
  no longer correct only when placed on the last line; they may be relocated to any line/position
  without changing their measured values.

#### FR-5 — Second-class (`alt`) dispensable segments

- **FR-5.1 Prefix + key** (chosen: prefix in key). A dispensable segment is named `seg_alt_<name>`
  and registers under key `alt_<name>`; `SEGMENTS`, `LAYOUT`, and config spell `alt_<name>`. Where a
  segment is also renamed into the `time_` family (FR-5.2), the two stack: builder
  `seg_alt_time_clock` → key `alt_time_clock`. (`alt_` = dispensable tier; `time_` = domain family.
  They are orthogonal; if the stacked name proves unwieldy in the plan, `alt` may instead be carried
  as a registry flag while `time_` stays the name — but the default is the literal stacked form.)
- **FR-5.2 Membership (confirmed) + the `time_` family rename.** The time-related segments are
  regrouped under a `time_` family, and all of them are dispensable, so the family is entirely `alt`
  (an extractable block). Final v1.0 partition of all 20 segments:
  - **Core (11):** `path`, `branch`, `dirty`, `todo`, `model`, `effort`, `lines`, `render_time`,
    `slowest`, `context`, `chat_size`.
  - **Alt (9):** `alt_cost`, `alt_rate_limits`, `alt_dimensions`, `alt_worktree`, `alt_memory`, and
    the time family `alt_time_clock` (was `clock`), `alt_time_ago` (was `time_ago`),
    `alt_time_session` (was `total_time`), `alt_time_api` (was `api_time`).
- **FR-5.3 Migration / back-compat.** Renaming a segment key changes its TOML key and its
  `CC_AI_KIT_SEGMENT_<KEY>` env name (e.g. `CC_AI_KIT_SEGMENT_CLOCK` → `CC_AI_KIT_SEGMENT_ALT_TIME_CLOCK`).
  All renamed keys (`clock`, `total_time`, `api_time`, `cost`, `rate_limits`, `dimensions`,
  `worktree`, `memory`, `time_ago`) must keep loading from their old spelling — tolerated and mapped
  forward (mirroring the existing `[git] worktree` legacy handling), with at most a dim deprecation
  warning. **Rendered output is unaffected** — keys are internal identifiers, so the golden stays
  byte-identical.

#### FR-6 — Defaults first, config block immediately after

- **FR-6.1** A single DEFAULTS block at the top holds all default **data** only (segment flags,
  layout, palette/ramp/effort defaults, tuning scalars) and contains no resolution logic.
- **FR-6.2** The `cfg_` block (resolution logic) is placed immediately after the DEFAULTS block.
- **FR-6.3** Defaults are tunable during testing by editing one top region; the arch test asserts
  the ordering and the data-only constraint.

#### FR-7 — Extract introspection to a dedicated script

- **FR-7.1** A new dedicated script (working name `tools/statusline-doctor.py`) owns the
  introspection commands: `--doctor`, `--check`, `--print-config`, plus `validate_config_file`, the
  dry-render-failures logic, and the doctor sample input. (chosen: dedicated script only.)
- **FR-7.2** `tools/status-line.py` renders only — the introspection flags are removed from it.
- **FR-7.3** The doctor script imports the core render module and calls into it (one-way dependency:
  tooling → core). The hyphenated module filename that blocks a plain `import` is resolved with the
  same `importlib`/`sys.modules` mechanism the tests already use (or an equivalent import shim).
- **FR-7.4** `install.sh` installs the doctor script and is the documented trigger; a user runs the
  dedicated script (optionally surfaced via install.sh). Docs and any references to
  `status-line.py --doctor` are updated. The doctor tests move to target the new script.
- **FR-7.5** Whether the doctor sample input stays a literal in the doctor script or moves to an
  external fixture is an implementation choice for the plan; it is no longer carried by the render
  module either way.

#### FR-8 — Architecture (AST fitness) test

- **FR-8.1** A stdlib-only (`ast`) unittest that parses the module(s) and enforces, as failing
  assertions:
  - env reads for config occur only in the `cfg_` loader; the FR-1.7 SHELL exceptions are
    whitelisted (enforces FR-1.6 / D8).
  - no subscript-load on our typed models (the per-render object, `line_conf`, `GitSnapshot`) —
    attribute access only (enforces D4 and the recurring `fields["x"]` review nit class).
  - only `seg_render_time` / `seg_slowest` read the render bookkeeping (`slowest`, render-start).
  - every `seg_*` / `seg_alt_*` has the canonical `(ctx, avail, theme)` signature.
  - the DEFAULTS block precedes the `cfg_` block and contains only data (FR-6).
  - role-prefix integrity: a function's prefix matches the block it lives in; no cross-role naming.
  - the render module contains no introspection/doctor symbols (enforces FR-7).
- **FR-8.2** The test runs inside `make validate` / pre-commit, so violations fail before merge.
- **FR-8.3** Rules may be added incrementally as each invariant lands, but the full set is green by
  the end of the final phase.

### Data Requirements

- **Per-render object**: root = parsed Claude JSON fields (typed) + SHELL-injected runtime
  (geometry, resolved effort) + `line_conf` + `theme` + render bookkeeping (`failed`, `slowest`).
  No single-consumer probe fields.
- **`line_conf`**: today's `Config` content, populated by the loader; env overrides applied by the
  `CC_AI_KIT_<NAME>` → `line_conf.<name>` convention.
- **Golden fixture**: `tests/fixtures/golden/expected.txt` is the invariant; never regenerated.

### Edge Cases

- A renamed `alt_` key present in an old config → tolerated via back-compat mapping (FR-5.3).
- A `probe_*` that fails (no `/proc`, no git, missing transcript) → returns the same "absent"
  sentinel today's probes do; the owning segment hides; never blanks the bar.
- Geometry unresolved → the existing assumed-200×40 fallback path is unchanged.
- Disabled segment → its `probe_*` is never called (laziness is the compute gate, as today).

## Design Decisions

### Technical Approach

- **Architecture Choice**: Keep the functional-core/imperative-shell pattern; refine *within* it.
  The data model moves from a typed god-bag to a thin root (Claude JSON) + bounded `line_conf` +
  memoized external probes. The packer moves from per-line build+fit to global measure → global
  meta → per-line pack. Classification is expressed as a full role-prefix vocabulary plus contiguous
  blocks. Introspection is extracted to a sibling script that depends on the core.
- **Key Components**: the per-render root object + `line_conf`; `probe_*` memoized data gatherers;
  the three-phase `core_` packer; the `seg_alt_` registry convention; `tools/statusline-doctor.py`;
  the `ast`-based arch test.
- **Interface Design**: builder contract unchanged — `seg_x(ctx, avail, theme) -> str | None`.
  Env→config contract becomes the deterministic name convention. CLI contract changes: render module
  loses introspection flags; the doctor script gains them.

### Constraints

- **Behavior**: golden snapshot byte-identical at every task; full suite green at every task.
- **Performance**: render hot path no heavier than today; extraction of introspection removes (small)
  cold-start parse weight from the render module. No per-render regression in the packer.
- **Compatibility**: existing TOML configs keep loading (back-compat key mapping). The
  `status-line.py --doctor`/`--check`/`--print-config` CLI is **intentionally broken** and replaced;
  this is a documented migration.
- **Security**: unchanged — session-id path-traversal guard, provider sandboxing, and never-blank
  isolation all preserved.
- **Dependencies**: runtime stdlib-only; dev gate (ruff/pylint/pyright/vulture/pre-commit) unchanged.

### Risk Assessment

- **Technical Risk — breaking FR-R.2 during probe extraction.** Mitigation: a dedicated test
  (already exists, mutation-verified) asserts probe cost is counted in the triggering segment; it
  must stay green through Phase 2.
- **Technical Risk — the alt-key rename changes user-facing config.** Mitigation: back-compat
  mapping + explicit migration note + the table is confirmed before Phase 3.
- **Technical Risk — hyphenated-filename import for the doctor script.** Mitigation: reuse the
  tests' `importlib`/`sys.modules` loader; covered by FR-7.3.
- **Dependency Risk — install.sh / docs drift after the CLI move.** Mitigation: FR-7.4 makes
  install.sh + docs + tests part of the same phase.
- **Schedule Risk — scope is six interlocking changes.** Mitigation: phased, each phase
  golden-gated and independently revertible; structure-only motion (Phase 1) lands first to de-risk.

## Acceptance Criteria

### Functional Acceptance

- [ ] **FR-1**: the per-render object exposes Claude JSON at its root and our settings under
      `line_conf`; no single-consumer probe (RSS, chat size, ago, effort-auto, todo, git) remains a
      data-model field; each is a memoized `probe_*`/`util_*`/`core_*` call from its owning segment.
- [ ] **FR-1.6**: exactly one function reads config env vars, via the structure-aware
      `CC_AI_KIT_<...>` → `line_conf.<group>.<field>` convention (full names; `line_conf` stays
      nested, not flat); no config `env.get` exists elsewhere; the bootstrap `CONFIG_FILE` (FR-1.7)
      and SHELL/runtime exceptions (FR-1.8) are the only other env reads; `CLAUDE_EFFORT` is gone
      (FR-1.9).
- [ ] **FR-2**: every function carries its role prefix (`seg_`/`seg_alt_`/`probe_`/`fmt_`/`util_`/
      `core_`/`cfg_`); the file is reorganized into contiguous role blocks.
- [ ] **FR-4**: packing is three phases (measure-all → meta-once → pack-per-line); the meta segments
      compute identical values regardless of their layout position; no fit logic remains in the timed
      pass.
- [ ] **FR-5**: the confirmed partition is implemented — core (11) unchanged, alt (9) as
      `seg_alt_<name>` / key `alt_<name>` including the renamed `time_` family
      (`alt_time_clock`/`alt_time_ago`/`alt_time_session`/`alt_time_api`); every old key still loads.
- [ ] **FR-6**: a data-only DEFAULTS block is first; the `cfg_` block follows immediately.
- [ ] **FR-7**: `tools/statusline-doctor.py` owns `--doctor`/`--check`/`--print-config`;
      `status-line.py` renders only; install.sh + docs + tests updated.
- [ ] **FR-8**: the AST arch test enforces all FR-8.1 rules and runs in the gate.

### Quality Standards

- [ ] **Behavior**: `tests/fixtures/golden/expected.txt` byte-identical after every task (never
      regenerated).
- [ ] **Test Coverage**: full unittest + shell suite green; the FR-R.2 probe-timing test stays
      green; new arch test added.
- [ ] **Static gates**: `make validate` (ruff, pylint at defaults, pyright strict, vulture,
      shellcheck, py-compile) green on both modules.
- [ ] **No new runtime dependency**; runtime stays stdlib-only.

### User Acceptance

- [ ] **Predictability**: maintainer can name the file region for defaults, config, core machinery,
      and segments without searching.
- [ ] **Extractability**: `grep seg_alt_` yields the dispensable-segment block as a movable unit.
- [ ] **Documentation**: README / install docs reflect the doctor script and the env-name convention;
      the CLI migration is noted.

## Execution Phases

### Phase 1: Classification + reorganization (FR-2, FR-6)
**Goal**: Establish the structure with pure motion + renames; no logic change.
- [ ] Apply the full role-prefix vocabulary to every function.
- [ ] Reorganize into contiguous role blocks; DEFAULTS block first, `cfg_` block immediately after.
- [ ] Verify golden byte-identical and full gate green (motion/rename only).
- **Deliverables**: reorganized, role-prefixed `status-line.py`; golden + gate green.

### Phase 2: Data-model decoupling + env consolidation (FR-1)
**Goal**: Thin the per-render object to `ctx` (Claude JSON) + `line_conf`; move probes out; one env reader.
- [ ] Introduce the `ctx`/`line_conf` split; co-locate the assembler with the dataclass.
- [ ] Convert single-consumer probes to memoized `probe_*` calls; collapse the git multi-property shim.
- [ ] Consolidate config env reading behind the `CC_AI_KIT_<NAME>` → `line_conf.<name>` convention.
- [ ] Keep the FR-R.2 probe-timing test green; verify golden + gate.
- **Deliverables**: decoupled data model; single env reader; FR-R.2 preserved.

### Phase 3: Packer refactor + alt segments (FR-4, FR-5)
**Goal**: Three-phase packer; dispensable-segment convention.
- [ ] Lift measurement to a global Phase A; compute meta once in Phase B; pack per line in Phase C.
- [ ] Remove the double-fit; verify meta values are position-independent.
- [ ] Apply the confirmed core/alt table (FR-5.2): rename the `time_` family, prefix dispensables
      to `seg_alt_`/`alt_`, with back-compat mapping for every old key (FR-5.3).
- [ ] Verify golden + gate (rendered output unchanged).
- **Deliverables**: position-independent meta; `alt` block; back-compat config.

### Phase 4: Introspection extraction (FR-7)
**Goal**: Doctor/validation in a dedicated script; render module renders only.
- [ ] Create `tools/statusline-doctor.py` importing the core; move the commands + sample + validator.
- [ ] Remove the introspection flags from `status-line.py`.
- [ ] Update install.sh, docs, and retarget the doctor tests.
- [ ] Verify both modules pass the gate; render hot path no longer parses introspection code.
- **Deliverables**: dedicated doctor script; lean render module; updated install/docs/tests.

### Phase 5: Architecture test (FR-8)
**Goal**: Lock the invariants in the gate.
- [ ] Implement the `ast`-based arch test covering all FR-8.1 rules.
- [ ] Wire it into `make validate` / pre-commit.
- [ ] Confirm it fails on a deliberately-violating diff, then passes clean.
- **Deliverables**: green arch test in the gate; the invariants are now enforced, not reviewed.

### Phase 6: Commit compaction + merge
**Goal**: Land per the working agreements.
- [ ] Compact working history into per-logical-unit commits (one concern each).
- [ ] Final whole-implementation review; merge to local main `--no-ff`.
- **Deliverables**: clean history; merged refinement; memory updated.

---

**Document Version**: 1.0
**Created**: 2026-06-22
**Clarification Rounds**: 5 (post-merge analysis → directed answers → 4-question decision round + config-model note → env-map + effort + alt-table decisions → nested-config correction)
**Quality Score**: 100/100
