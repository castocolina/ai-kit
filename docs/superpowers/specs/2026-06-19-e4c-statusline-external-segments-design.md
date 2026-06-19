# E4c — Status-line External Drop-in Segments — Design

> Epic **E4c** of the ai-kit status-line overhaul (was labeled "E4b" before the color
> subsystem took that slot — see the labeling note in `docs/prds/000-ai-kit-overhaul-requirements.md`).
> Builds on **E4a** (config engine: tiers, `[segments]`, `[[line]]`, `[palette]`, recipe,
> introspection — **merged to main**). **E5** (installer + setup wizard) has **already
> shipped**, so E4c integrates *into* the existing wizard rather than preceding it.

**Goal:** let a user add a *new* status-line segment by dropping an executable in a
directory — no patching `tools/status-line.py`. Each provider gets the **same contract a
built-in builder gets**: it receives the available column budget and the status JSON, and
returns the richest line that fits (or nothing, to self-drop). The core handles discovery,
placement, timeout, output sanitization, TTL caching, enable/disable, and safe degradation.

## Background & motivation

E4a made segment visibility, layout, palette, and ramps configurable — but there is still
no way to add a *datum ai-kit doesn't ship* (e.g. "AWS session expires in 4h44m") without
forking `status-line.py`. The author has already had to hand-patch a custom segment on
another machine. E4c closes that gap with a drop-in provider model.

Two refinements over the original PRD draft (`statusline-external-segments-v1.0-prd.md`),
decided in the 2026-06-19 brainstorm:

1. **Providers self-format to the column budget** — the original draft only truncated
   provider output after the fact. Instead the core passes the **available columns** into
   the provider (exactly as built-in builders receive `avail`), so a provider can pick a
   long/medium/short rendering or drop itself — then the core still truncates as a safety
   net and owns the final keep/skip by priority.
2. **Providers are first-class toggles** — discovered providers fold into E4a's
   `[segments]` model, **enabled by default**, disabled only explicitly; and the **E5
   wizard discovers them** and lists them with their current toml state.

## Scope

**In:** provider discovery + header grammar; the input contract (status JSON + `segment`
block on stdin, `AI_KIT_SEGMENT_*` env mirror, cwd = workspace dir); the columns/tier
contract; execution with timeout + output sanitization (SGR-only) + width truncation;
placement as a synthetic builder into E4a's resolved layout; per-`id` TTL caching;
enable/disable via `[segments]` (default-on); the `[external]` config block + env scalars;
E5 wizard integration (discovery + listing + opt-in copy of the sample); a shipped
cross-platform **system-available-memory** sample provider; README contract docs with a
worked AWS example; tests.

**Out:** the E4a config engine itself; the E4b color subsystem; a curated library of
ready-made providers; any auto-install of provider logic; sandboxing of provider
execution (trust model is "the segments dir is user-owned", documented).

## Architecture & data flow

External providers are modeled as **synthetic builders** inserted into E4a's resolved
layout, so the existing packing / overflow / priority logic in `pack_line` handles them
unchanged. This is the seam that keeps E4c near-zero-rework on top of E4a.

```
load_config(env) -> Config            # E4a: segments, layout, palette, ramps
discover_external(directory, default_ttl, env) -> [ExtSpec]   # parse headers in the segments dir
  -> fold each id into cfg.segments (default-on) + into the resolved layout
render(data, cols, lines, cfg, theme)
  -> pack_line(keys, data, cols, cfg, theme)
       -> builder(data, avail, theme)            # built-in OR synthetic external
            (external) run_external(spec, data, avail)  # TTL-cached, timeout-bounded
```

A built-in builder is `seg_x(data, avail, theme) -> str | None`. The synthetic external
builder has the **same shape**: given `avail`, it runs the provider (or returns cached
output), sanitizes the result, and returns the line or `None`. `pack_line` cannot tell the
difference, so `PINNED` priority, overflow, and keep/skip behave identically.

### Key components

- `discover_external(directory, default_ttl, env) -> list[ExtSpec]` — scan the segments dir,
  parse headers, return specs (path, id, line, position, timeout, ttl). Skips
  non-executables (dim warning).
- `ExtSpec` — resolved provider metadata.
- `make_external_builder(spec)` — returns a `seg_x`-shaped closure for `BUILDERS`.
- `run_external(spec, data, avail)` — TTL-cached, timeout-bounded execution +
  sanitization; the only place a subprocess is spawned.
- Layout integration — insert each spec's id into `cfg.layout` at its declared
  row/position; fold the id into `cfg.segments` with a default of `True`.

## Provider discovery + header grammar

- **Directory:** `${CC_AI_KIT_SEGMENTS_DIR:-${[external].dir:-${XDG_CONFIG_HOME:-~/.config}/ai-kit/segments}}`.
- **Each executable file** in that dir is a provider. Non-executable files are skipped with
  a dim stderr warning.
- **Metadata header** (first 10 lines), regex-matched:
  ```
  # ai-kit-segment: line=<N> (after=<key>|before=<key>|start|end) [id=<slug>] [timeout=<s>] [ttl=<s>]
  ```
  Defaults: `line` = last layout row, `position` = `end`, `id` = filename stem,
  `timeout` = 2s, `ttl` = `[external].ttl`. A file with no header still loads with all
  defaults (it just renders at the end of the last row).

## Input contract

A provider is invoked with:

- **stdin** — the **same status JSON Claude passes to `status-line.py`**, augmented with a
  namespaced `segment` block so the provider knows its budget and identity:
  ```json
  {
    "...": "all normal status-line fields (workspace, model, cost, context, …)",
    "segment": { "id": "sysmem", "avail_cols": 24, "line": 1, "position": "after:context" }
  }
  ```
- **env mirror** (so a one-line shell provider needs no JSON parser):
  `AI_KIT_SEGMENT_COLS`, `AI_KIT_SEGMENT_ID`, `AI_KIT_SEGMENT_LINE`, `AI_KIT_SEGMENT_POSITION`.
- **cwd** = `workspace.current_dir`, so a provider can be context-aware (e.g. pick an AWS
  profile by directory). The parent env is inherited.

## Columns / tier contract (identical to built-in builders)

This is the core behavioral contract. A built-in builder calls
`_first_fitting([long, mid, short], avail)` — returning the richest variant whose display
width fits `avail`, else `None` to self-deprioritize. **An external provider does the same**,
using `avail_cols`:

```bash
# AWS-session-expiry — DOCS SNIPPET (shell, env-mirror path; not a shipped file)
# ai-kit-segment: line=2 after=clock id=aws-session ttl=30
cols=${AI_KIT_SEGMENT_COLS:-80}
left="4h 44m 12s"                                   # from your `aws` lookup
if   [ "$cols" -ge 14 ]; then printf '\033[33m🔐 %s\033[0m\n' "$left"   # long
elif [ "$cols" -ge 8  ]; then printf '\033[33m🔐 4h44m\033[0m\n'        # medium
elif [ "$cols" -ge 4  ]; then printf '\033[33m🔐4h\033[0m\n'            # short
fi                                                  # else: print nothing → core drops it
```

- The core supplies `avail_cols` = the column budget for the provider's slot, computed the
  same way `pack_line` computes `avail` for a built-in at that position.
- The provider returns the richest line that fits, or **empty output to drop**.
- The core still **truncates to `avail` as a safety net**, and `pack_line` still **owns the
  final keep/skip by priority** (`PINNED` segments win), so a misbehaving provider can never
  push a pinned segment off the line.

## Execution + output sanitization

- Run the provider with its `timeout` (default 2s); capture stdout.
- Take the **first non-empty line**, strip the trailing newline.
- **Allowed inline escapes: SGR color only** (`\033[…m`). Any other control / CSI sequence
  (cursor moves, clears, OSC) is stripped — display text only, no shell-eval of output.
- Measure width with the same `visible_width` built-ins use; truncate to `avail`.
- **Non-zero exit, timeout, or empty output → segment omitted.** A bad/slow/failing
  provider never breaks rendering.

## Placement

- Insert each provider as a synthetic builder into E4a's resolved layout at its declared
  `line`/`position`.
- Target row gated out by `min_rows` → simply not shown.
- `line=<N>` out of range → clamp to the last existing row + a dim stderr warning.
- Multiple externals resolving to the same slot → deterministic order by **filename, then
  `id`**.

## Caching

- Per `id`, output is cached `ttl` seconds at
  `${XDG_CACHE_HOME:-~/.cache}/ai-kit/segments/<id>`; stale or missing → re-run.
- Cache dir unwritable → run without caching (best effort, never fatal).
- The cache stores the provider's raw first-line output; sanitization + truncation happen on
  read, so a width change between renders re-truncates without re-running the provider.
- **Known tradeoff:** the cache key is `id` (+ ttl), **not** `avail_cols`. A provider chooses
  its tier from the `avail_cols` of the render that populated the cache; if the column budget
  changes *within* the TTL, the cached line is re-truncated rather than re-tiered (a cached
  "long" variant may be hard-truncated instead of the provider's own "short" variant).
  Accepted because status-line width rarely changes mid-session and the TTL is short; a
  provider that needs exact per-width tiers can set `ttl=0` to re-run every render.

## Enable / disable (enabled by default)

- Every discovered provider is folded into E4a's `[segments]` toggle model under its `id`,
  **defaulting to enabled**.
- A user disables one **explicitly**: `[segments] sysmem = false` in the toml, or
  `CC_AI_KIT_SEGMENT_SYSMEM=0` in the env (E4a's existing segment-toggle grammar).
- Discovery never requires registration — dropping the file is enough; the toggle only
  exists to turn a discovered provider *off*.

## E5 wizard integration

E5 (installer + setup wizard) has already shipped, so E4c integrates into it:

- The wizard **runs `discover_external`** and lists each provider alongside the
  built-in segments, showing its **current enabled/disabled state** loaded from the toml
  (using the same `[x]/[ ]` + accent/dim affordance E5 already uses for built-ins).
- Toggling a provider writes its `[segments] <id>` value like any other segment.
- On a fresh setup the wizard **asks** whether to copy the shipped **system-available-memory**
  sample into the live segments dir (opt-in; default No). Yes → the file is copied and, being
  discovered, is enabled by default; No → the live dir stays empty.

## Config surface (added to E4a's schema)

```toml
[external]
ttl = 10                              # seconds (overridden by CC_AI_KIT_EXTERNAL_TTL)
dir = "~/.config/ai-kit/segments"     # overridden by CC_AI_KIT_SEGMENTS_DIR
```

- Env scalars: `CC_AI_KIT_SEGMENTS_DIR` (dir), `CC_AI_KIT_EXTERNAL_TTL` (int seconds). Env
  wins over the file (E4a precedence: default < file < env).
- The E4a shipped recipe (`tools/statusline.toml.sample`) gains a commented `[external]`
  block (no-op until edited).

## Shipped files + file homes

- **`examples/segments/sysmem`** — the shipped **system-available-memory** sample: a
  self-contained `python3` provider (python3 is guaranteed — `status-line.py` runs on it),
  cross-platform (Linux `/proc/meminfo` `MemAvailable`; macOS `vm_stat` + page size; generic
  fallback → drop). It reads `AI_KIT_SEGMENT_COLS` and renders long/medium/short tiers, and
  is the canonical copy-and-edit starting point. Distinct from the built-in `🧮` segment
  (which is the Claude *process* RSS); the sample reports *system available* RAM. Header
  defaults it near the context cluster (`line=1 after=context`), documented as movable.
- **Test fixture providers** — ephemeral per-test temp dirs (not committed); each test class
  creates its own `tempfile.mkdtemp()` dir and writes fixture scripts at runtime: valid-header,
  no-header, slow/timeout, failing (non-zero), columns-tier, multi-line/huge output,
  non-executable.
- **Runtime dir** `~/.config/ai-kit/segments/` — **empty by default**; populated only when
  the user copies a sample or adds their own.
- **AWS-session-expiry** — **docs snippet only** (shown above), not a shipped file; it is the
  realistic worked example for the README contract section.

## Error handling (summary)

| Condition | Behavior |
|---|---|
| Provider not executable | Skipped, dim warning |
| No header | Loads with all defaults (end of last row) |
| Non-zero exit / timeout / empty output | Segment omitted; line renders without it |
| Output has non-SGR control sequences | Those sequences stripped; SGR kept |
| Multi-line / huge output | First non-empty line only, truncated to `avail` |
| `line=N` out of range | Clamp to last row + dim warning |
| Row gated by `min_rows` | Provider not shown |
| Cache dir unwritable | Run without caching |

## Testing

- `discover_external`: valid header, missing header (defaults), bad header fields, non-executable skip.
- Header grammar parser: each field + defaults + malformed values.
- `run_external`: timeout kill, non-zero exit, empty output, first-non-empty-line selection.
- Sanitization: SGR preserved; cursor/clear/OSC stripped; width measured + truncated.
- Columns/tier: a fixture provider returns different tiers for different `avail_cols`,
  and empty (drop) below its minimum.
- Placement: position resolution (`after`/`before`/`start`/`end`), out-of-range clamp,
  same-slot deterministic ordering, `min_rows` gating.
- Caching: write-on-run, TTL hit, TTL expiry re-run, unwritable-dir best-effort.
- Enable/disable: discovered provider default-on; `[segments] id=false` and
  `CC_AI_KIT_SEGMENT_<ID>=0` turn it off; precedence (file < env).
- Wizard: discovery lists externals with toml state; opt-in copy of the sample.
- Sample provider: renders on Linux/macOS, drops cleanly on an unsupported platform.
- Full existing `status-line.py`, installer, and setup suites stay green.

## Acceptance criteria

- [ ] An executable in the segments dir with a valid header renders at the declared row/position.
- [ ] A provider receives the status JSON + `segment` block on stdin, the `AI_KIT_SEGMENT_*`
      env mirror, and runs with cwd = `workspace.current_dir`.
- [ ] A provider that reads `avail_cols` returns long/medium/short tiers and drops below its
      minimum; the core truncates as a safety net and never lets an external push out a `PINNED`.
- [ ] Output keeps SGR colors, strips other control sequences, and is width-truncated like a built-in.
- [ ] Non-zero exit / timeout / empty output omits the segment without breaking the line.
- [ ] Output is cached per `id` for `ttl` and re-runs after expiry; unwritable cache dir runs uncached.
- [ ] Out-of-range `line=N` clamps to the last row; same-slot externals order by filename then id.
- [ ] Discovered providers are enabled by default and disabled only by explicit
      `[segments] <id>=false` / `CC_AI_KIT_SEGMENT_<ID>=0`.
- [ ] `[external] ttl|dir` and `CC_AI_KIT_SEGMENTS_DIR` / `CC_AI_KIT_EXTERNAL_TTL` work with E4a precedence.
- [ ] The E5 wizard discovers external providers, lists them with their toml state, and offers
      the opt-in copy of the system-available-memory sample.
- [ ] The shipped `examples/segments/sysmem` sample renders cross-platform and is documented;
      README covers the header grammar, input JSON (worked AWS example), expected output, and
      columns-tier handling.
- [ ] All existing tests pass; new tests cover discovery, input contract, columns tiers,
      execution, sanitization, placement, caching, toggles, and wizard integration.

---

**Document Version**: 1.0 · **Created**: 2026-06-19 · **Depends on**: E4a (config engine +
resolved layout — **merged to main**). **Relates to**: E5 (wizard — **shipped**; E4c
integrates into it), E4b (color subsystem — independent). Supersedes the loose
`statusline-external-segments-v1.0-prd.md` draft for the parts it refines (columns contract,
enable/disable, wizard discovery, shipped sample).
