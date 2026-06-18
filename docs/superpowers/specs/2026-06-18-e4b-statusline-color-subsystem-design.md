# E4b — Status-line Color Subsystem — Design

> Epic **E4b** of the ai-kit status-line overhaul. Builds on **E4a** (config engine:
> tiers, `[segments]`, `[[line]]`, `[palette]`, recipe, introspection). Scheduled
> **before E5** so the setup wizard (E5) is built against the final palette/ramp schema.
> The external-drop-in-segments work that previously held the "E4b" name is renamed
> **E4c** and stays scheduled after E5.

**Goal:** make the status line's colors a small, well-defined system — one color parser
accepting palette names, raw SGR codes, and hex (with modifiers); a pure-hue named
palette; and user-configurable per-band ramps — with no module-level mutable color state.

## Background & motivation

E4a made segment visibility, layout, and named colors configurable, but:

- **Bold is tangled into color values.** Six base palette colors silently bake in `1;`
  (`WHITE=1;97`, `CYAN=1;36`, `GREEN=1;32`, `RED=1;31`, `YELLOW=1;33`, `MAGENTA=1;35`),
  while `ORANGE`/`BLUE` do not, and there are two single-use bold duplicates
  (`ORANGE_BOLD`, `MAGENTA_DARK_BOLD`). In ANSI SGR, bold is parameter `1`, orthogonal to
  color — like CSS `font-weight`. Bold should be a modifier, not a separate color.
- **Ramp thresholds and band colors are hardcoded** inside `_build_ramps()`; `[palette]`
  can change what `RED` is, but not *where* the context bar turns red or which color a
  band uses.
- **Ramps drifted to mid-file.** The E4a Task 8 refactor pushed `CONTEXT_RAMP`/`RATE_RAMP`
  from the top of the file into `_build_ramps()`, below the config machinery, and that
  function mutates module globals via `globals()[...] =` — the source of the Pyright
  "undefined variable" noise.

E4b resolves all three.

## Scope

**In:** unified `parse_color()`; pure-hue `_PALETTE_DEFAULTS`; data-driven `_RAMP_DEFAULTS`
for the three ramps (`context`, `rate`, `chat_size`); `[ramp.*]` config + validation; a
resolved `Theme` threaded into builders (no module color globals); file reorganization;
updated sample recipe + README; tests.

**Out:** external drop-in segments (**E4c**); the E5 wizard; making the effort ladder or
individual builder inline colors independently user-configurable (they keep deriving from
the palette); `CC_AI_KIT_*` env knobs for colors (env stays for segment toggles).

## Architecture & data flow

Two types, no mutable module color state:

- **`Config`** — parsed *intent*: `segments, layout, palette, ramps`. `palette` is the
  override dict; `ramps` the override tables; both empty when unset.
- **`Theme`** — resolved *colors* derived from `Config`: the merged palette
  (name → SGR params), the three resolved ramps (name → `[(ceil, escape)]`), and the
  effort ladder. Built once via `build_theme(cfg)`.

Flow:

```
load_config(env) -> Config
build_theme(cfg) -> Theme
render(data, cols, lines, cfg, theme)
  -> pack_line(keys, data, cols, cfg, theme)        # cfg.segments gates visibility
       -> builder(data, avail, theme)                # colors come from theme
```

Builders ask `theme.c("BLUE")` / `theme.c("CYAN+bold")` (memoized resolve through
`parse_color`) and `pick_color(value, theme.ramps["context"])`. `RESET` and
`BG_LIGHTGRAY` remain true module constants (immutable, not a smell). **No `globals()`
writes anywhere** — `Theme` is an explicit object, statically analyzable.

Back-compat: `render`/`pack_line` keep `cfg=None`/`theme=None` defaults resolving to
`default_config()` / `default_theme()`, so existing call sites and tests keep working.

## The color grammar + `parse_color()`

`parse_color(spec, palette=None) -> "\033[...m" | None` is the single place SGR is
produced. Three base forms, disambiguated by shape, plus `+` modifiers.

| Form | Detection | Example → params |
|---|---|---|
| palette name | starts with a letter | `RED` → looks up resolved palette → `31` |
| raw SGR code | matches `^[0-9;]+$` | `38;5;39` → passthrough |
| hex RGB/RGBA | starts with `#` | `#3399ffcc` → strip alpha → `38;2;51;153;255` |

- **Modifiers** (apply to any base): `+bold`/`+dim`/`+underline`/`+italic` →
  prepend `1`/`2`/`4`/`3` in canonical ascending order. `RED+bold` → `1;31`;
  `#3399ff+bold` → `1;38;2;51;153;255`.
- **Hex:** `#rgb` expands to `#rrggbb`; `#rrggbbaa` drops the trailing `aa` (accidental
  IDE alpha); produces `38;2;r;g;b` (truecolor). Invalid hex → `None`.
- **Name lookup** uses the resolved palette passed in; palette values themselves are
  parsed with `palette=None` (hex/SGR only — no name nesting, so no cycles).
- **Invalid input** (unknown name, unknown modifier, bad hex) → `None`; callers warn and
  fall back. `--check` surfaces every failure.

Documented caveats: hex → truecolor needs a truecolor terminal; `italic`/`underline`
support varies by terminal.

## Palette + ramps as data

A deliberate **visual refresh**, not a preserve-pixels refactor: base palette becomes
pure hues; bold is applied only where it earns emphasis.

```python
_PALETTE_DEFAULTS = {            # pure hues — no baked-in bold
    "GREY": "90", "WHITE": "97", "CYAN": "36", "GREEN": "32", "RED": "31",
    "YELLOW": "33", "MAGENTA": "35", "ORANGE": "38;5;208",
    "BLUE": "38;5;39",           # lightened (was 38;5;33); exact shade reviewed on-terminal
    "LIGHTBLUE": "38;5;75", "MAGENTA_DARK": "38;5;90",
}   # ORANGE_BOLD / MAGENTA_DARK_BOLD removed — bold now lives on the ramp band

_RAMP_DEFAULTS = {
    "context":   [(10, "WHITE"), (15, "CYAN"), (20, "BLUE"), (25, "GREEN"),
                  (30, "YELLOW"), (40, "ORANGE+bold"), (50, "RED+bold"),
                  ("inf", "MAGENTA_DARK+bold")],
    "rate":      [(50, "GREEN"), (80, "YELLOW"), ("inf", "RED+bold")],
    "chat_size": [("512k", "WHITE"), ("1M", "CYAN"), ("2M", "LIGHTBLUE"), ("3M", "GREEN"),
                  ("4M", "YELLOW"), ("5M", "ORANGE"), ("10M", "RED+bold"), ("inf", "MAGENTA")],
}
```

Red is bold in context / chat / rate (as required); the top "danger" bands also bold. The
effort ladder (`_EFFORT_DEFAULTS`) stays data-driven but **not** user-configurable; its
colors derive from palette names. Use-sites that read better bold (e.g. the model name)
hardcode the modifier at the call site (`theme.c("CYAN+bold")`) so the *palette* stays
pure and config overrides remain predictable.

Net visual effect: most segments render regular-weight; danger states pop. Exact
colors/bold are confirmed during a terminal review pass.

## Config schema, precedence, validation

```toml
[palette]                 # MERGES over defaults; values: name / raw SGR / hex (+modifiers)
BLUE = "#3399ff"
RED  = "1;31"

[ramp.context]            # REPLACES the whole ramp (all-or-nothing, like [[line]])
10  = "WHITE"
50  = "RED+bold"
inf = "MAGENTA_DARK+bold"

[ramp.chat_size]
"512k" = "WHITE"
"10M"  = "RED+bold"
inf    = "MAGENTA"
```

- **Threshold keys:** `inf` → ∞; `512k`/`5M`/`1G` → bytes (chat_size); bare integer →
  percent (context/rate).
- **`[palette]` merges**, **`[ramp.X]` replaces** that ramp entirely; ramps you don't
  mention keep their defaults. Bad single band → warn + fall back to that band's built-in
  color; an unparseable ramp → keep the built-in ramp.
- **Precedence:** built-in defaults < TOML file. Colors/ramps are **file-only** (no
  `CC_AI_KIT_*` env overrides; env stays for segment toggles).
- **`--check`** runs every palette value and every ramp colorspec through `parse_color`
  and reports each failure (unknown name/modifier, bad hex, unresolvable band).

## File reorganization

```
EDITABLE SURFACE (top):  SEGMENTS, PINNED, LAYOUT (+Line), _PALETTE_DEFAULTS,
                         _RAMP_DEFAULTS, _EFFORT_DEFAULTS, Config + default_config
COLOR ENGINE:            parse_color, _hex_to_sgr, _parse_threshold, pick_color,
                         Theme, build_theme, default_theme
CONFIG RESOLUTION:       config_path, _load_toml, _resolve_segments/layout/palette/ramps,
                         load_config                         (moved BELOW the defaults)
EXTRACTORS / BUILDERS:   seg_* (now take theme), BUILDERS
PACKER / RENDER:         pack_line, render                  (thread cfg + theme)
CLI / main:              parse_args, cmd_*, validate_config_file, main
```

## Error handling

- Any `parse_color` failure → `None` → warn (dim, stderr) + fall back (palette: keep
  default for that key; ramp band: keep default band; whole ramp: keep built-in).
- Malformed TOML / missing file → existing E4a behavior (ignored with a warning).
- `Theme.c` on an invalid spec returns a safe empty string (no color) rather than raising,
  so a bad hardcoded use-site can never break rendering.

## Testing

- `parse_color`: table tests over every form + every modifier + alpha-strip + short-hex
  expansion + invalid inputs.
- `_parse_threshold`: percent ints, byte suffixes (`k`/`M`/`G`), `inf`, bad keys.
- `build_theme`: palette merge, per-ramp replace, band fall-back, effort derivation.
- `Theme.c`: resolution + memoization; invalid spec → empty string.
- `--check`: valid config → 0; unknown palette key, unknown modifier, bad hex,
  unresolvable ramp band → non-zero with a message each.
- Sample drift test updated: pure-hue `[palette]` equals `_PALETTE_DEFAULTS`; the
  `[ramp.*]` blocks equal `_RAMP_DEFAULTS`.
- Full existing `status-line.py` + installer suites stay green.

## Acceptance criteria

- [ ] `parse_color` resolves names (`+mods`), raw SGR, and hex (`#rgb`/`#rrggbb`/`#rrggbbaa`,
      alpha stripped); invalid input returns `None`.
- [ ] Named palette is pure-hue; bold/dim/underline/italic apply via `+` modifiers.
- [ ] `[ramp.context|rate|chat_size]` replace their ramp; thresholds accept percent / byte
      suffix / `inf`; unspecified ramps keep defaults.
- [ ] No module-level mutable color globals; `Theme` is threaded into builders; Pyright
      reports no undefined-color errors.
- [ ] `--check` validates all palette + ramp colorspecs and reports each failure.
- [ ] Updated sample recipe documents the grammar (names, raw codes, hex, modifiers) and
      ships the `[ramp.*]` defaults; README updated.
- [ ] All existing tests pass; new tests cover the parser, thresholds, theme, and validation.

---

**Document Version**: 1.0 · **Created**: 2026-06-18 · **Depends on**: E4a (on branch
`feat/e4a-statusline-config`). **Scheduled**: before E5. External drop-in segments are
**E4c** (after E5).
