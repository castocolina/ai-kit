# Status-line Config & Extensibility — Product Requirements Document (PRD)

> Epic **E4** of the ai-kit status-line overhaul. Scope: the **configuration and
> extensibility mechanism** only. The interactive wizard/setup lives in E5; the
> effort/memory/macOS fixes live in E3. E4 builds the layer those depend on.

## Requirements Description

### Background
- **Problem**: `tools/status-line.py` is configured only by editing Python
  constants (`SEGMENTS` dict, `LAYOUT`). There is no per-user config, no way to
  toggle segments without editing source, and no way to add a custom segment
  (e.g. "AWS session expires in 12m") without patching the file — which the user
  has already had to do on another machine.
- **Users**: the kit's author and anyone who installs ai-kit and wants to tune
  the status line to their terminal/workflow without forking it.
- **Value**: tune and extend the status line through config + drop-in scripts;
  changes apply on the next refresh without reloading Claude Code; the source
  file stays the upstream default.

### Feature Overview
- **Core**:
  1. Three-tier resolved config: **internal defaults < TOML file < env vars**.
  2. Per-segment visibility toggles via config file and `CC_AI_KIT_SEGMENT_*`.
  3. Layout (which segments on which row, order, `min_rows`) overridable from the file.
  4. **External segments**: drop-in executables discovered from a directory, placed
     via a metadata header, output cached with a TTL.
  5. Minimal `[palette]` color overrides (lets a user fix "blue looks purple"
     without code; default-palette work itself is E3).
  6. Refactor: move the **editable config surface (segment defaults + layout) to
     the top of the file**, immediately after imports/constants.
  7. A **shipped recipe**: a complete, fully-commented `statusline.toml.sample`
     in the repo, copied by the installer to the default path if none exists. It
     declares every `[segments]` toggle and the full `[[line]]` layout (identical
     to internal defaults) commented out — the user uncomments only what they
     want to change; internal defaults stay in force for everything else.
- **Boundaries (in)**: config loading/merging, env grammar, the TOML schema, the
  shipped recipe + installer copy-if-absent, external-segment
  discovery/execution/caching, palette override application, the top-of-file
  reorg, and tests for all of it.
- **Boundaries (out)**: the Python wizard and install opt-in flow (**E5**);
  `effort=auto` detection + per-letter coloring, memory-process fix, macOS
  size/memory fallbacks (**E3**); shipping a curated theme library.

### User Scenarios
- Hide the `cost` segment: set `CC_AI_KIT_SEGMENT_COST=0` or `cost = false`
  in the config file.
- Reorder/move a segment between rows by editing `[[line]]` in the config file.
- Add an AWS-session-expiry segment: drop an executable in `~/.config/ai-kit/segments/`
  with `# ai-kit-segment: line=2 after=clock` — it appears next refresh, cached 30s.
- Fix a purple-ish blue: `[palette] BLUE = "38;5;33"`.

### Detailed Requirements

**Config resolution (`load_config(env)` → resolved config)**
- Internal defaults = current `SEGMENTS` + `LAYOUT` (post-reorg, at top of file).
- File path: `${CC_AI_KIT_CONFIG:-${XDG_CONFIG_HOME:-~/.config}/ai-kit/statusline.toml}`.
- Parsed with `tomllib` (Python ≥ 3.11). Missing/empty/malformed file → defaults,
  no crash (a malformed file is tolerated; optionally a dim warning to stderr).
- Env overrides applied last, per key (merge, not whole-source replace).

**Boolean env grammar (`env_bool`)**
- True: `1 true t y yes on` (case-insensitive). False: `0 false f n no off`.
- Unset/unrecognized → fall through to file/default (no override).

**Env var surface (documented in README + `--help`)**
- `CC_AI_KIT_SEGMENT_<KEY>` — bool; `<KEY>` is the upper-cased segment name
  (`EFFORT`, `MEMORY`, `COST`, `CONTEXT`, …).
- `CC_AI_KIT_CONFIG` — path to the TOML file.
- `CC_AI_KIT_SEGMENTS_DIR` — external-segment directory.
- `CC_AI_KIT_EXTERNAL_TTL` — int seconds, external output cache TTL.

Scope note: **env only covers segment toggles and the scalars above.** Layout
(`[[line]]`) and `[palette]` are **file-only** — there is no env override for them
(they are structural, not quick per-session switches).

**TOML schema**
```toml
version = 1                # config schema version (for forward migration)

[segments]                 # override visibility defaults (subset allowed)
cost   = true
memory = false

[[line]]                   # full layout override when ANY [[line]] is present
min_rows = 0
segments = ["path", "branch", "dirty", "todo"]
[[line]]
min_rows = 20
segments = ["model", "clock", "effort", "lines", "total_time", "api_time"]

[palette]                  # optional ANSI SGR overrides for named colors
BLUE = "38;5;33"

[external]
ttl = 10                   # seconds (overridden by CC_AI_KIT_EXTERNAL_TTL)
dir = "~/.config/ai-kit/segments"
```
Rule: `[segments]` merges over defaults (partial allowed). `[[line]]` is
all-or-nothing — if present it **replaces** the default layout (so a partial
layout can't silently drop segments by omission).

**Shipped recipe (`statusline.toml.sample`)**
- A complete, **fully-commented** TOML living in the repo (e.g. `tools/statusline.toml.sample`).
- Contains every `[segments]` key set to its default, the full `[[line]]` layout
  (byte-identical to the internal default), and example `[palette]` / `[external]`
  blocks — all commented.
- Header comment explains the two uncomment modes:
  - `[segments]` — uncomment **individual** lines to flip just those (merge).
  - `[[line]]` — to take over layout, uncomment **all** `[[line]]` blocks and edit
    (all-or-nothing; partial layout is intentionally not supported).
- Delivery: the installer copies it to
  `${XDG_CONFIG_HOME:-~/.config}/ai-kit/statusline.toml` **only if that file does
  not already exist** — it never overwrites a user's config. With every line
  commented, the freshly-copied file is a no-op (internal defaults apply) until
  the user edits it. The sample stays the upstream canonical reference; E5's
  wizard can regenerate the real file from it.

**External segment contract**
- Discovery: each executable file in the segments dir is a provider.
- Metadata header (first 10 lines), regex-matched:
  `# ai-kit-segment: line=<N> (after=<key>|before=<key>|start|end) [id=<slug>] [timeout=<s>] [ttl=<s>]`
  - Defaults: `line` = last layout row, position = `end`, `id` = filename stem,
    `timeout` = 2s, `ttl` = `[external].ttl`.
- Input: the script receives the **same status JSON Claude passes to status-line**
  on **stdin**, and runs with **cwd = `workspace.current_dir`** — so it can be
  context-aware (e.g. pick an AWS profile by directory). Env is inherited.
- Execution: run with the timeout; capture stdout. Output handling:
  - take the **first non-empty line**, strip the trailing newline;
  - allowed inline escapes are **SGR color codes only** (`\033[…m`); any other
    control/CSI sequence is stripped (no cursor moves, no clears);
  - width is measured with the same `visible_width` used for built-in segments,
    and the line is truncated to the available budget like any other segment.
  - Non-zero exit, timeout, or empty output → segment omitted; never breaks rendering.
- Placement: insert into the resolved layout at the declared row/position.
  - Target row gated out by `min_rows` → simply not shown.
  - `line=<N>` out of range → clamp to the last existing row + a dim stderr warning.
  - Multiple externals resolving to the same slot → deterministic order by
    **filename, then `id`**.
- Caching: per `id`, output cached `ttl` seconds at
  `${XDG_CACHE_HOME:-~/.cache}/ai-kit/segments/<id>`; stale or missing → re-run.

**File reorg**
- Move `SEGMENTS` (defaults) and the `LAYOUT` template to the **top**, right after
  imports and tuning constants, ahead of the palette and the `seg_*` functions.
- `BUILDERS` (maps keys → functions) stays below the function defs; a comment at
  the top points to it. The *editable surface* is at the top; the *wiring* stays
  with the functions.

**CLI flags & introspection**
- The script keeps its default mode: **no args → read status JSON from stdin and
  render** (today's behavior, unchanged). Arg parsing coexists with stdin mode:
  - `--print-config` — resolve config (defaults < file < env) and print it as JSON;
    do not render. Does not require stdin.
  - `--check [FILE]` — validate a config file (default: the resolved path); report
    each error (unknown keys, bad layout refs, malformed TOML); exit non-zero if invalid.
  - `--help` — usage + the full env-var list.

### Edge Cases
- Python < 3.11 (no `tomllib`): degrade to defaults + env only; warn once. (Kit
  targets 3.11+; record as a known limitation.)
- Config references an unknown segment key → ignored with a dim warning.
- External script not executable → skipped with a warning.
- Cache dir unwritable → run without caching (best effort).
- A `[[line]]` references a segment that is toggled off → not rendered.

## Design Decisions

### Technical Approach
- **Single module, no new deps**: `tomllib` (stdlib ≥3.11), `subprocess` (already
  used), `os`/`time`. No third-party packages — preserves `curl | bash`-free,
  zero-install execution.
- **One resolution pass** in `main()`/`build_data()`: `cfg = load_config(env)`,
  then `render()` consumes `cfg.layout`, `cfg.segments`, `cfg.palette`, and the
  external providers. Keeps the render path pure and testable.
- **Palette overrides**: the overridable keys are the base named colors —
  `GREY WHITE CYAN GREEN ORANGE RED YELLOW MAGENTA BLUE` plus the two band colors
  `ORANGE_BOLD MAGENTA_DARK_BOLD`. Values are raw SGR parameters (e.g. `"38;5;33"`
  or `"1;34"`), wrapped to `\033[<v>m`. Overrides are applied **before** the ramps
  (`CONTEXT_RAMP`, `RATE_RAMP`, `_EFFORT_BARS`) are built, so the ramps inherit the
  new colors automatically; ramps are not individually overridable. Unknown palette
  keys → ignored with a dim warning.
- **External segments** modeled as synthetic builders inserted into the layout, so
  the existing packing/overflow logic handles them unchanged.

### Key Components
- `env_bool(env, name)` — tri-state bool parser.
- `load_config(env)` — returns a `Config` (segments, layout, palette, external).
- `discover_external(cfg)` — parse headers → list of external segment specs.
- `run_external(spec, cfg)` — TTL-cached execution with timeout.
- Reorg of `SEGMENTS`/`LAYOUT` to top; `BUILDERS` annotated.
- `tools/statusline.toml.sample` — the canonical commented recipe, generated to
  match the internal defaults (a test asserts they stay in sync).
- Installer step (in `install.sh`, later mirrored by the E5 Makefile/wizard):
  copy the sample to the default config path only when absent.

### Constraints
- **Performance**: config-file read every render (cheap); external scripts only
  re-run past their TTL. Per-render added cost ≈ one small file stat/read.
  **Budget: < ~15 ms added** versus today with a warm external cache (no script
  re-run). Cold external runs are bounded by each script's `timeout`.
- **Compatibility**: defaults unchanged when no file/env present — existing
  installs behave identically until they opt in.
- **Safety**: never crash on bad config/scripts; external output is treated as
  display text only (no shell-eval of config values).

### Risk Assessment
- **External-script latency/abuse**: bounded by per-script timeout + TTL cache;
  document that providers should be fast and print one line.
- **Schema drift**: the TOML schema is versioned in README; unknown keys ignored.
- **tomllib availability**: mitigated by env-only degradation + documented 3.11+.

## Acceptance Criteria

### Functional Acceptance
- [ ] `CC_AI_KIT_SEGMENT_COST=0` hides cost; `=1` shows it; precedence is default < file < env.
- [ ] A `statusline.toml` with `[segments]` and `[[line]]` changes visibility and layout accordingly.
- [ ] An executable in the segments dir with a valid header renders at the declared row/position.
- [ ] External output is cached for its TTL and re-runs after it expires.
- [ ] External timeout / non-zero exit / empty output omits the segment without breaking the line.
- [ ] An external script receives the status JSON on stdin and runs in `workspace.current_dir`.
- [ ] External output keeps SGR colors but has other control sequences stripped, and is width-measured/truncated like a built-in segment.
- [ ] Out-of-range `line=N` clamps to the last row; same-slot externals order deterministically by filename then id.
- [ ] `[palette] BLUE=...` changes the rendered blue (and any ramp using it); absent → current default; unknown palette key warns and is ignored.
- [ ] `--print-config` emits the resolved config without rendering; `--check` flags an invalid config with a non-zero exit; no-arg mode still renders from stdin.
- [ ] Missing/malformed config file falls back to defaults with no crash.
- [ ] `SEGMENTS` defaults and `LAYOUT` are at the top of the file; rendering is unchanged from today with no config.
- [ ] The shipped `statusline.toml.sample` is fully commented; with it copied verbatim, rendering equals the no-config default (it is a no-op until edited).
- [ ] The installer copies the sample to the default path only when absent, never overwriting an existing config.
- [ ] A test asserts the sample's declared defaults match the internal `SEGMENTS`/`LAYOUT` (they cannot drift).

### Quality Standards
- [ ] `shellcheck`-clean install path unaffected; `status-line.py` passes existing tests.
- [ ] New tests cover: `env_bool`, precedence merge, TOML parse + toggles + layout override, external discovery/placement/timeout/TTL, malformed-config tolerance, palette override.
- [ ] No new third-party dependencies.

### User Acceptance
- [ ] README documents the config file, env vars, the external-segment header, and precedence.
- [ ] `status-line.py --help` (or a `--print-config` mode) lists resolved config and env knobs.

## Execution Phases

### Phase 1: Config core
**Goal**: three-tier resolution with segment toggles.
- [ ] Move `SEGMENTS`/`LAYOUT` to top; annotate `BUILDERS`.
- [ ] Implement `env_bool` and `load_config(env)` (defaults < TOML < env).
- [ ] Wire toggles into render; tests for precedence + malformed tolerance.
- **Deliverables**: config-driven visibility; green tests.

### Phase 2: Layout + palette from config
**Goal**: file-driven layout and color overrides.
- [ ] `[[line]]` override (all-or-nothing) + validation/warnings.
- [ ] `[palette]` override application.
- [ ] Tests for layout override + palette override.
- **Deliverables**: full layout/theming via file.

### Phase 3: External segments
**Goal**: drop-in extensible segments.
- [ ] Header grammar parser + `discover_external`.
- [ ] `run_external` with timeout + TTL cache; placement into layout.
- [ ] Tests with fixture scripts (valid header, no header, slow/timeout, failing).
- **Deliverables**: AWS-session-style segment works as a drop-in.

### Phase 4: Recipe, install copy, docs & introspection
**Goal**: discoverability + zero-friction first config.
- [ ] Generate `tools/statusline.toml.sample` (fully commented, complete) + drift test vs internal defaults.
- [ ] `install.sh`: copy the sample to the default config path if absent (never overwrite).
- [ ] README section + sample external segment.
- [ ] `--print-config` resolved-config dump.
- **Deliverables**: shipped recipe in place on install; documented, inspectable config surface.

---

**Document Version**: 1.0
**Created**: 2026-06-14
**Clarification Rounds**: 4 (decomposition + E4 deep-dive + shipped-recipe + gap-closure)
**Quality Score**: 100/100 — no open items
**Depends on / feeds**: E5 (wizard consumes this config), E3 (effort/memory fixes use the toggles/palette).
