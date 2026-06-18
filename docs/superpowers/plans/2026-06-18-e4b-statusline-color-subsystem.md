# E4b — Status-line Color Subsystem Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the status line's colors into one small, statically-analyzable system: a single `parse_color()` accepting palette names, raw SGR codes, and hex (all with `+bold/+dim/+italic/+underline` modifiers); a pure-hue named palette; user-configurable per-band ramps; and a resolved `Theme` threaded into builders — with **no module-level mutable color state** (kills the `globals()[...] =` Pyright noise).

**Architecture (Approach B — no module color globals):** Two types. `Config` is parsed *intent* — gains a `ramps` field beside `segments, layout, palette`. `Theme` is resolved *colors* derived from a `Config`: the merged palette (`NAME -> sgr params`), the three resolved ramps (`band -> [(ceil, escape)]`), and the effort ladder. `build_theme(cfg)` produces it once; `render`/`pack_line`/every builder take a `theme` and ask `theme.c("BLUE")` / `theme.c("CYAN+bold")` or `pick_color(value, theme.ramps["context"])`. `init_palette()`/`_build_ramps()` and all the color globals they wrote (`BLUE`, `CONTEXT_RAMP`, `_EFFORT_BARS`, …) are deleted. `RESET`/`BG_LIGHTGRAY` stay true module constants; a new fixed `_DIM` const colors stderr warnings (palette-independent). The cutover is split so each step is verifiable: **Task 3** builds the Theme system *alongside* the old one and pins it byte-identical to today's globals; **Task 4** threads `theme` everywhere and deletes the old system (appearance still identical); **Task 5** is the isolated visual refresh (pure hues + bold-on-danger + lighter blue).

**Tech Stack:** Python 3.11+ stdlib only (`re`, `tomllib`, `argparse`, `json`, `os`, `sys`), `unittest` for Python tests, bash + `shellcheck` for the installer, TOML for the config file.

**Spec:** `docs/superpowers/specs/2026-06-18-e4b-statusline-color-subsystem-design.md` (E4b, v1.0). PRD roadmap row: `docs/prds/000-ai-kit-overhaul-requirements.md` (E4b, before E5).

**Branch:** `feat/e4b-statusline-colors` (off `feat/e4a-statusline-config` / `main` with E4a present).

**Test commands:**
- Python: `python3 -m unittest tests.test_status_line -v`
- Installer: `bash tests/test_install.sh`
- Lint installer: `shellcheck tools/install.sh`

---

## File Structure

- `tools/status-line.py` — **modify**. Add `parse_color`, `_hex_to_sgr`, `_MOD_SGR`, `_parse_threshold`, `_RAMP_DEFAULTS`, `_EFFORT_DEFAULTS`, `_EFFORT_GLYPHS`, `_DIM`, `Theme`, `_resolve_palette`, `_resolve_ramp`, `_build_effort`, `build_theme`, `default_theme`. Extend `Config` with `ramps`; extend `load_config` (`[ramp.*]`), `cmd_print_config`, `validate_config_file`. Thread `theme` through `pack_line`, `render`, all 17 `seg_*` builders, and the `rate_color`/`_rate_str` helpers. Make `_PALETTE_DEFAULTS` pure-hue (add `LIGHTBLUE`/`MAGENTA_DARK`; drop `ORANGE_BOLD`/`MAGENTA_DARK_BOLD`). **Delete** `init_palette`, `_build_ramps`, the import-time `init_palette()` call, the fixed `LIGHTBLUE` module const, the `_MB` const, and `main()`'s `init_palette(cfg.palette)` call.
- `tests/test_status_line.py` — **modify**. New: `TestParseColor`, `TestParseThreshold`, `TestTheme`, `TestBuildTheme`, `TestThemeMatchesLegacy` (Task 3, removed/converted in Task 4), `TestRampFromConfig`. Rewrite every color-asserting class off module globals onto a `Theme`. Add a module-level `THEME = sl.default_theme()` and pass it to direct builder calls.
- `tools/statusline.toml.sample` — **modify**. Add the `[palette]` pure-hue defaults + `[ramp.context|rate|chat_size]` default blocks + a grammar comment (names / raw SGR / hex / `+modifiers`).
- `README.md` — **modify**. Document the color grammar, `[palette]` merge vs `[ramp.*]` replace, thresholds, and terminal caveats.

New top-level names, used consistently across tasks:
`parse_color(spec, palette=None)`, `_hex_to_sgr(spec)`, `_MOD_SGR`, `_parse_threshold(key)`, `_RAMP_DEFAULTS`, `_EFFORT_DEFAULTS`, `_EFFORT_GLYPHS`, `_DIM`, `Theme`, `Theme.c(spec)`, `_resolve_palette(overrides)`, `_resolve_ramp(pairs, palette, band, fallback)`, `_build_effort(palette)`, `build_theme(cfg)`, `default_theme()`, `Config(segments, layout, palette, ramps)`.

---

## Color model (reference for every task)

- **`parse_color(spec, palette=None) -> "\033[...m" | None`** — the single place SGR is produced. Base form by shape: palette name (letter-led, looked up in `palette`), raw SGR (`^[0-9;]+$`, passthrough), hex (`#`-led). `+bold/+dim/+italic/+underline` map to `1/2/3/4`, prepended in canonical ascending order. Invalid → `None`.
- **`theme.palette`**: `NAME -> bare SGR params` (e.g. `"38;5;208"`, no `\033[`/`m`, no leading modifier). Name lookups append their own modifiers on top of these params.
- **`theme.ramps[band]`**: `[(ceil_value, escape)]` already sorted ascending — `pick_color(value, ramp)` returns the escape directly (its signature/body are unchanged).
- **`theme.effort[level]`**: `(color_escape, bar_str)` — same shape the old `_EFFORT_BARS` had, so `seg_effort` changes only its lookup source.
- `RESET`, `BG_LIGHTGRAY` stay module constants. `_DIM = "\033[90m"` is a new fixed const for stderr warnings (replaces the now-removed `GREY` global in warning strings).

---

## Phase 1 — Color primitives (pure functions)

### Task 1: `parse_color` + `_hex_to_sgr`

The grammar engine. Pure, depends on nothing else, and nothing references it yet — so it lands green in isolation.

**Files:**
- Modify: `tools/status-line.py`, `tests/test_status_line.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_status_line.py` (end of file, before `if __name__`):

```python
class TestParseColor(unittest.TestCase):
    PAL = {"RED": "31", "BLUE": "38;5;39", "ORANGE": "38;5;208"}

    def test_palette_name(self):
        self.assertEqual(sl.parse_color("RED", self.PAL), "\033[31m")
        self.assertEqual(sl.parse_color("BLUE", self.PAL), "\033[38;5;39m")

    def test_raw_sgr_passthrough(self):
        self.assertEqual(sl.parse_color("38;5;33"), "\033[38;5;33m")
        self.assertEqual(sl.parse_color("1;31"), "\033[1;31m")

    def test_hex_six(self):
        self.assertEqual(sl.parse_color("#3399ff"), "\033[38;2;51;153;255m")

    def test_hex_short_expands(self):
        self.assertEqual(sl.parse_color("#39f"), "\033[38;2;51;153;255m")

    def test_hex_alpha_stripped(self):
        self.assertEqual(sl.parse_color("#3399ffcc"), "\033[38;2;51;153;255m")

    def test_modifier_bold_on_name(self):
        self.assertEqual(sl.parse_color("RED+bold", self.PAL), "\033[1;31m")

    def test_modifier_on_hex(self):
        self.assertEqual(sl.parse_color("#3399ff+bold"), "\033[1;38;2;51;153;255m")

    def test_modifiers_canonical_order(self):
        # underline(4)+bold(1) -> ascending 1;4 regardless of input order
        self.assertEqual(sl.parse_color("RED+underline+bold", self.PAL), "\033[1;4;31m")

    def test_all_modifiers(self):
        self.assertEqual(sl.parse_color("RED+bold+dim+italic+underline", self.PAL),
                         "\033[1;2;3;4;31m")

    def test_unknown_name_is_none(self):
        self.assertIsNone(sl.parse_color("NOTACOLOR", self.PAL))

    def test_name_without_palette_is_none(self):
        self.assertIsNone(sl.parse_color("RED"))

    def test_unknown_modifier_is_none(self):
        self.assertIsNone(sl.parse_color("RED+blink", self.PAL))

    def test_bad_hex_is_none(self):
        self.assertIsNone(sl.parse_color("#zzz"))
        self.assertIsNone(sl.parse_color("#12345"))   # 5 nibbles, not 3/6/8

    def test_empty_is_none(self):
        self.assertIsNone(sl.parse_color(""))
        self.assertIsNone(sl.parse_color(None))
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python3 -m unittest tests.test_status_line.TestParseColor -v`
Expected: FAIL with `AttributeError: module ... has no attribute 'parse_color'`.

- [ ] **Step 3: Implement `_MOD_SGR`, `_hex_to_sgr`, `parse_color`**

Add a new `# ═══ Color engine` section in `tools/status-line.py`. Place it **immediately after** `_first_fitting` (end of the "Display width" section, ~line 281) so it sits above the builders that will use it but below `INF`/`re`:

```python
# ═══ Color engine ════════════════════════════════════════════════════════════
# One parser produces every SGR escape. Base forms (by shape): palette NAME
# (letter-led, resolved against `palette`), raw SGR ("38;5;208" passthrough), or
# hex ("#rgb"/"#rrggbb"/"#rrggbbaa", alpha dropped). "+bold/+dim/+italic/
# +underline" modifiers prepend 1/2/3/4 in ascending order. Invalid -> None.
_MOD_SGR = {"bold": "1", "dim": "2", "italic": "3", "underline": "4"}


def _hex_to_sgr(spec):
    """'#rgb' / '#rgba' / '#rrggbb' / '#rrggbbaa' -> '38;2;r;g;b' (alpha
    dropped). None if not valid hex of a supported length."""
    h = spec[1:]
    if len(h) in (3, 4):                 # short form: expand each nibble, drop alpha
        h = "".join(c * 2 for c in h[:3])
    elif len(h) == 8:                    # long form with alpha: drop the alpha byte
        h = h[:6]
    if len(h) != 6 or re.fullmatch(r"[0-9a-fA-F]{6}", h) is None:
        return None
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"38;2;{r};{g};{b}"


def parse_color(spec, palette=None):
    """Resolve a colorspec to '\\033[...m', or None if invalid. See section
    header for the grammar. `palette` ({NAME: sgr params}) is required only for
    name lookups; raw-SGR and hex specs ignore it."""
    if not spec:
        return None
    base, *mod_names = str(spec).split("+")
    base = base.strip()
    mods = []
    for m in mod_names:
        code = _MOD_SGR.get(m.strip().lower())
        if code is None:
            return None
        mods.append(code)
    if base.startswith("#"):
        params = _hex_to_sgr(base)
    elif base[:1].isalpha():
        params = (palette or {}).get(base)
    elif re.fullmatch(r"[0-9;]+", base):
        params = base
    else:
        params = None
    if params is None:
        return None
    ordered = sorted(set(mods), key=int)
    return "\033[" + ";".join(ordered + [params]) + "m"
```

- [ ] **Step 4: Run the new test and the full suite**

Run: `python3 -m unittest tests.test_status_line.TestParseColor -v` → PASS.
Run: `python3 -m unittest tests.test_status_line -v` → all still green (nothing else touched).

- [ ] **Step 5: Commit**

`feat(status-line): add parse_color grammar (names/SGR/hex + modifiers) — E4b`

---

### Task 2: `_parse_threshold`

Ramp threshold keys → comparable numbers. Pure; ramps don't use it yet.

**Files:**
- Modify: `tools/status-line.py`, `tests/test_status_line.py`

- [ ] **Step 1: Write the failing tests**

```python
class TestParseThreshold(unittest.TestCase):
    def test_percent_int(self):
        self.assertEqual(sl._parse_threshold(10), 10)
        self.assertEqual(sl._parse_threshold("25"), 25)

    def test_inf(self):
        self.assertEqual(sl._parse_threshold("inf"), float("inf"))
        self.assertEqual(sl._parse_threshold(float("inf")), float("inf"))

    def test_byte_suffixes(self):
        self.assertEqual(sl._parse_threshold("512k"), 512 * 1024)
        self.assertEqual(sl._parse_threshold("5M"), 5 * 1024 * 1024)
        self.assertEqual(sl._parse_threshold("1G"), 1024 ** 3)

    def test_bad_key_raises(self):
        with self.assertRaises(ValueError):
            sl._parse_threshold("nonsense")
        with self.assertRaises(ValueError):
            sl._parse_threshold("5MB")   # only single-letter k/M/G suffix
```

- [ ] **Step 2: Run it** → FAIL (`no attribute '_parse_threshold'`).

- [ ] **Step 3: Implement**

Add to the Color-engine section, directly below `parse_color`:

```python
_THRESHOLD_MULT = {"k": 1024, "M": 1024 ** 2, "G": 1024 ** 3}


def _parse_threshold(key):
    """Ramp threshold -> comparable number. 'inf'/inf -> INF; '512k'/'5M'/'1G'
    -> bytes (1024-based); bare int / numeric string -> that int (a percent).
    Raises ValueError on anything else."""
    if isinstance(key, float):
        return key
    if isinstance(key, int):
        return key
    s = str(key).strip()
    if s.lower() == "inf":
        return INF
    m = re.fullmatch(r"(\d+)([kMG])", s)
    if m:
        return int(m.group(1)) * _THRESHOLD_MULT[m.group(2)]
    return int(s)   # ValueError on garbage
```

(`INF = float("inf")` already exists at the top of the Palette section; it stays.)

- [ ] **Step 4: Run** the new test + full suite → green.

- [ ] **Step 5: Commit**

`feat(status-line): add _parse_threshold for ramp keys (percent/bytes/inf) — E4b`

---

## Phase 2 — Theme system (built alongside, then cut over)

### Task 3: `Theme` + `build_theme`, pinned byte-identical to today

Introduce the full resolved-color system **without touching any builder yet**. The old `init_palette`/`_build_ramps`/globals stay live, so the suite stays green; a new equivalence test proves the Theme reproduces the legacy globals exactly. `Config` gains `ramps`, and `load_config`/`cmd_print_config` learn `[ramp.*]`.

**Files:**
- Modify: `tools/status-line.py`, `tests/test_status_line.py`

- [ ] **Step 1: Write the failing tests**

```python
class TestTheme(unittest.TestCase):
    def test_c_resolves_and_memoizes(self):
        t = sl.default_theme()
        first = t.c("RED")
        self.assertTrue(first.startswith("\033["))
        self.assertEqual(t.c("RED"), first)          # same object/value, cached
        self.assertIn("RED", t._cache)

    def test_c_modifier(self):
        t = sl.default_theme()
        self.assertEqual(t.c("RED+bold"), sl.parse_color("RED+bold", t.palette))

    def test_c_invalid_is_empty_string(self):
        t = sl.default_theme()
        self.assertEqual(t.c("NOTACOLOR"), "")        # never raises, no color


class TestBuildTheme(unittest.TestCase):
    def _cfg(self, palette=None, ramps=None):
        return sl.Config(segments=dict(sl.SEGMENTS), layout=list(sl.LAYOUT),
                         palette=palette or {}, ramps=ramps or {})

    def test_palette_merges_over_defaults(self):
        t = sl.build_theme(self._cfg(palette={"BLUE": "1;34"}))
        self.assertEqual(t.palette["BLUE"], "1;34")
        self.assertEqual(t.palette["RED"], sl._PALETTE_DEFAULTS["RED"])  # untouched

    def test_palette_hex_override_resolved_to_params(self):
        t = sl.build_theme(self._cfg(palette={"BLUE": "#3399ff"}))
        self.assertEqual(t.palette["BLUE"], "38;2;51;153;255")

    def test_bad_palette_value_keeps_default(self):
        t = sl.build_theme(self._cfg(palette={"BLUE": "#zzz"}))
        self.assertEqual(t.palette["BLUE"], sl._PALETTE_DEFAULTS["BLUE"])

    def test_ramp_replaced_whole(self):
        t = sl.build_theme(self._cfg(ramps={"rate": {"50": "GREEN", "inf": "RED"}}))
        self.assertEqual([c for _, c in t.ramps["rate"]],
                         [t.c("GREEN"), t.c("RED")])
        self.assertEqual([ceil for ceil, _ in t.ramps["rate"]], [50, float("inf")])

    def test_unspecified_ramp_keeps_default(self):
        t = sl.build_theme(self._cfg(ramps={"rate": {"inf": "RED"}}))
        self.assertEqual(len(t.ramps["context"]), len(sl._RAMP_DEFAULTS["context"]))

    def test_bad_band_color_falls_back_to_default_band(self):
        # context default band at ceil 10 is WHITE; a bad override color for that
        # band falls back to the default band's resolved color.
        bad = {"10": "NOPE", "inf": "RED"}
        t = sl.build_theme(self._cfg(ramps={"context": bad}))
        self.assertEqual(t.ramps["context"][0], (10, t.c("WHITE")))

    def test_bad_threshold_keeps_whole_default_ramp(self):
        t = sl.build_theme(self._cfg(ramps={"context": {"oops": "RED"}}))
        self.assertEqual(t.ramps["context"], sl.default_theme().ramps["context"])

    def test_effort_derives_from_palette(self):
        t = sl.default_theme()
        self.assertEqual(t.effort["low"][0], t.c("CYAN"))
        self.assertEqual(t.effort["max"][0], t.c("RED"))
        self.assertEqual(t.effort["low"][1].count("▁"), 1)
        # full ladder: every glyph present, no trailing grey segment for max
        self.assertTrue(t.effort["max"][1].startswith(t.c("RED")))


class TestThemeMatchesLegacy(unittest.TestCase):
    """Pins the new Theme byte-identical to the still-live legacy globals, so the
    Task-4 cutover provably changes nothing. Removed in Task 4 with the globals."""
    def test_palette_colors_match_globals(self):
        t = sl.default_theme()
        for name in ("WHITE", "CYAN", "GREEN", "RED", "YELLOW", "MAGENTA",
                     "ORANGE", "BLUE", "GREY"):
            self.assertEqual(t.c(name), getattr(sl, name), name)

    def test_ramps_match_globals(self):
        t = sl.default_theme()
        self.assertEqual(t.ramps["context"], sl.CONTEXT_RAMP)
        self.assertEqual(t.ramps["rate"], sl.RATE_RAMP)
        self.assertEqual(t.ramps["chat_size"], sl.CHAT_SIZE_RAMP)

    def test_effort_matches_globals(self):
        self.assertEqual(sl.default_theme().effort, sl._EFFORT_BARS)


class TestRampFromConfig(unittest.TestCase):
    def _write(self, body):
        f = tempfile.NamedTemporaryFile("w", suffix=".toml", delete=False)
        f.write(body); f.close()
        self.addCleanup(os.unlink, f.name)
        return f.name

    def test_ramp_parsed_into_config(self):
        path = self._write('[ramp.rate]\n50 = "GREEN"\ninf = "RED+bold"\n')
        cfg = sl.load_config({"CC_AI_KIT_CONFIG": path, "HOME": "/h"})
        self.assertEqual(cfg.ramps, {"rate": {"50": "GREEN", "inf": "RED+bold"}})

    def test_unknown_ramp_dropped(self):
        path = self._write('[ramp.bogus]\n10 = "RED"\n')
        cfg = sl.load_config({"CC_AI_KIT_CONFIG": path, "HOME": "/h"})
        self.assertEqual(cfg.ramps, {})

    def test_no_ramp_block_is_empty(self):
        cfg = sl.load_config({"CC_AI_KIT_CONFIG": "/no/such.toml", "HOME": "/h"})
        self.assertEqual(cfg.ramps, {})
```

- [ ] **Step 2: Run it** → FAIL (`no attribute 'build_theme'` / `Config` has no field `ramps`).

- [ ] **Step 3: Add the `_DIM` constant + `_RAMP_DEFAULTS` + `_EFFORT_DEFAULTS`**

In the Palette section, add `_DIM` next to the fixed constants (just below `BG_LIGHTGRAY`, ~line 172):

```python
_DIM = "\033[90m"             # fixed dim grey for stderr warnings (palette-independent)
```

Then, **directly below** the existing `_PALETTE_DEFAULTS` dict (keep `_PALETTE_DEFAULTS` and the legacy `INF`/`_MB` exactly as they are for now), add the data-driven ramp + effort tables. **For this task the colors are the current names so resolved values are identical to today** (the visual refresh is Task 5):

```python
# Ramps as data: band -> [(threshold, colorspec)]. Threshold keys go through
# _parse_threshold (percent / byte-suffix / inf); colorspecs through parse_color
# against the resolved palette. [ramp.X] in config REPLACES a band wholesale.
_RAMP_DEFAULTS = {
    "context": [(10, "WHITE"), (15, "CYAN"), (20, "BLUE"), (25, "GREEN"),
                (30, "YELLOW"), (40, "ORANGE_BOLD"), (50, "RED"),
                ("inf", "MAGENTA_DARK_BOLD")],
    "rate": [(50, "GREEN"), (80, "YELLOW"), ("inf", "RED")],
    "chat_size": [("512k", "WHITE"), ("1M", "CYAN"), ("2M", "LIGHTBLUE"),
                  ("3M", "GREEN"), ("4M", "YELLOW"), ("5M", "ORANGE"),
                  ("10M", "RED"), ("inf", "MAGENTA")],
}

# Effort ladder: level -> (palette name, fill count 1..5). Palette-derived but
# NOT user-configurable. `auto` is a setting and `ultracode` reports as xhigh —
# neither is a level here.
_EFFORT_DEFAULTS = {
    "low": ("CYAN", 1), "medium": ("BLUE", 2), "high": ("YELLOW", 3),
    "xhigh": ("ORANGE", 4), "max": ("RED", 5),
}
_EFFORT_GLYPHS = "▁▃▄▆█"
```

For `_RAMP_DEFAULTS` to resolve in this task, `LIGHTBLUE`, `ORANGE_BOLD`, and `MAGENTA_DARK_BOLD` must be lookup-able **names**. `ORANGE_BOLD`/`MAGENTA_DARK_BOLD` are already in `_PALETTE_DEFAULTS`; **add `LIGHTBLUE` to `_PALETTE_DEFAULTS`** so the chat_size ramp can name it (it currently lives only as a fixed module const):

```python
_PALETTE_DEFAULTS = {
    "GREY": "90", "WHITE": "1;97", "CYAN": "1;36", "GREEN": "1;32",
    "ORANGE": "38;5;208", "RED": "1;31", "YELLOW": "1;33", "MAGENTA": "1;35",
    "BLUE": "38;5;33",
    "LIGHTBLUE": "38;5;75",            # NEW palette entry (chat-size ramp band 3)
    "ORANGE_BOLD": "1;38;5;208",
    "MAGENTA_DARK_BOLD": "1;38;5;90",
}
```

Leave the fixed `LIGHTBLUE = "\033[38;5;75m"` module const (line 173) in place for now — `_build_ramps` still references it; both resolve to the same escape, so `TestThemeMatchesLegacy` passes. (It is deleted in Task 4.)

- [ ] **Step 4: Implement the Theme + resolvers + `build_theme`/`default_theme`**

Add a new `Theme` block in the Color-engine section, below `_parse_threshold`:

```python
class Theme:
    """Resolved colors for one render. `palette` maps NAME -> bare SGR params;
    `ramps` band -> [(ceil, escape)]; `effort` level -> (escape, bar). `c()`
    memoizes parse_color and never raises (invalid spec -> '')."""

    def __init__(self, palette, ramps, effort):
        self.palette = palette
        self.ramps = ramps
        self.effort = effort
        self._cache = {}

    def c(self, spec):
        if spec not in self._cache:
            self._cache[spec] = parse_color(spec, self.palette) or ""
        return self._cache[spec]


def _resolve_palette(overrides):
    """Merge _PALETTE_DEFAULTS with `overrides` ({NAME: spec}); each override
    value is parsed (hex / raw SGR / +mods — no name nesting) to bare params. A
    bad value warns and keeps the default."""
    palette = dict(_PALETTE_DEFAULTS)
    for name, value in (overrides or {}).items():
        if name not in _PALETTE_DEFAULTS:
            continue                       # unknown keys already warned in load_config
        esc = parse_color(value, palette=None)
        if esc is None:
            print(f"{_DIM}status-line: bad palette {name}={value!r} — keeping "
                  f"default{RESET}", file=sys.stderr)
            continue
        palette[name] = esc[2:-1]          # strip "\033[" .. "m" -> bare params
    return palette


def _resolve_ramp(pairs, palette, band, fallback):
    """Resolve [(threshold, colorspec)] -> [(ceil, escape)] sorted ascending.
    A bad band color falls back to that ceil's color in `fallback`; a bad
    threshold abandons the override and returns `fallback` whole. `fallback` is
    None only when resolving the built-in defaults (known-good)."""
    fb = dict(fallback) if fallback else {}
    out = []
    for thr, spec in pairs:
        try:
            ceil = _parse_threshold(thr)
        except ValueError:
            print(f"{_DIM}status-line: bad ramp [{band}] threshold {thr!r} — "
                  f"keeping default{RESET}", file=sys.stderr)
            return list(fallback) if fallback else out
        esc = parse_color(spec, palette)
        if esc is None:
            esc = fb.get(ceil, "")
            print(f"{_DIM}status-line: bad ramp [{band}] color {spec!r} — using "
                  f"default band{RESET}", file=sys.stderr)
        out.append((ceil, esc))
    out.sort(key=lambda ce: ce[0])
    return out


def _build_effort(palette):
    """level -> (color escape, bar string). Filled glyphs in the level's color,
    the rest in grey (matching the legacy _EFFORT_BARS layout)."""
    grey = parse_color("GREY", palette) or ""
    out = {}
    for level, (name, n) in _EFFORT_DEFAULTS.items():
        color = parse_color(name, palette) or ""
        rest = _EFFORT_GLYPHS[n:]
        bar = f"{color}{_EFFORT_GLYPHS[:n]}" + (f"{grey}{rest}" if rest else "")
        out[level] = (color, bar)
    return out


def build_theme(cfg):
    """Resolve a Config's palette + ramps + effort into a Theme."""
    palette = _resolve_palette(cfg.palette)
    ramps = {}
    for band, default_pairs in _RAMP_DEFAULTS.items():
        default_ramp = _resolve_ramp(default_pairs, palette, band, None)
        override = (cfg.ramps or {}).get(band)
        ramps[band] = (default_ramp if override is None
                       else _resolve_ramp(override.items(), palette, band, default_ramp))
    return Theme(palette, ramps, _build_effort(palette))


def default_theme():
    """Theme from default_config() (no overrides)."""
    return build_theme(default_config())
```

- [ ] **Step 5: Extend `Config` with `ramps`**

Update the namedtuple and `default_config` (lines 67–73):

```python
Config = namedtuple("Config", "segments layout palette ramps")


def default_config():
    """A Config snapshotting the current module-global defaults (SEGMENTS/LAYOUT,
    no palette/ramp overrides). Copies are returned so callers cannot mutate
    globals."""
    return Config(segments=dict(SEGMENTS), layout=list(LAYOUT), palette={}, ramps={})
```

Update the `Config` doc comment (lines 63–66) to mention `ramps` and keep the E4c note.

- [ ] **Step 6: Parse `[ramp.*]` in `load_config`; swap warning colors to `_DIM`**

In `load_config` (lines 152–166), after palette resolution and before the `return`, add ramp parsing, then return all four fields:

```python
    ramps = {}
    for band, table in (raw.get("ramp") or {}).items():
        if band not in _RAMP_DEFAULTS:
            print(f"{_DIM}status-line: unknown ramp '{band}'{RESET}", file=sys.stderr)
            continue
        if not isinstance(table, dict):
            print(f"{_DIM}status-line: ramp '{band}' must be a table — ignored{RESET}",
                  file=sys.stderr)
            continue
        ramps[band] = {str(k): str(v) for k, v in table.items()}
    return Config(segments=segments, layout=layout, palette=palette, ramps=ramps)
```

Also change the warning escapes from `{GREY}` to `{_DIM}` in `_load_toml`, `_resolve_segments`, and the unknown-palette-key branch of `load_config` (the `GREY` global is removed in Task 4; `_DIM` is independent of the palette and works now). Other `Config(...)` constructions in this file (none outside `default_config`/`load_config`) — leave; tests construct `Config` with all four fields (handled in Task 4 test rewrites).

- [ ] **Step 7: Add `ramps` to `cmd_print_config`**

In `cmd_print_config` (lines 1004–1011) add `"ramps": cfg.ramps,` to the JSON dict.

- [ ] **Step 8: Run the new tests, then the full suite**

Run: `python3 -m unittest tests.test_status_line.TestTheme tests.test_status_line.TestBuildTheme tests.test_status_line.TestThemeMatchesLegacy tests.test_status_line.TestRampFromConfig -v` → PASS.
Run: `python3 -m unittest tests.test_status_line -v` → all green. The old globals still drive rendering; the Theme is proven equivalent but unused by builders.

> Note: existing `TestPaletteFromConfig.test_palette_parsed_into_config` and `TestResolveSegments.test_defaults_when_no_file_no_env` etc. construct/compare `Config` only via `load_config`/`default_config`, which now carry `ramps` — they keep passing. `TestCLI.test_print_config_emits_resolved_json` and `TestRenderWithConfig` build `Config(...)` **positionally/with kwargs missing `ramps`** — these break here. Fix them now as part of this task: add `ramps={}` to those `sl.Config(...)` literals (Task 4 rewrites the color bodies; the field addition is mechanical and belongs with the field). Re-run to confirm green before committing.

- [ ] **Step 9: Commit**

`feat(status-line): resolved Theme + build_theme + [ramp.*] config (values unchanged) — E4b`

---

### Task 4: Thread `theme` through builders; delete the global color system

The cutover. Every `seg_*` builder, `pack_line`, `render`, and the `rate_color`/`_rate_str` helpers take a `theme`. `main()` builds it via `build_theme`. All `init_palette`/`_build_ramps`/import-time/global machinery is deleted. **Appearance is byte-identical** — only the source of the escapes changes.

**Files:**
- Modify: `tools/status-line.py`, `tests/test_status_line.py`

- [ ] **Step 1: Rewrite the color-asserting tests to use a `Theme` (these now fail)**

Add a module-level theme after `sl = load_module()` (line 23):

```python
THEME = sl.default_theme()
```

Then rewrite, class by class — assert against `THEME.c(name)` / `THEME.ramps[...]` rather than deleted globals, and pass `THEME` to every direct builder call. The intent of each test is preserved; only the color source moves. Apply all of:

- **`TestPickColor`** (52): `pick_color` still exists. Replace `sl.CONTEXT_RAMP`→`THEME.ramps["context"]`, `sl.RATE_RAMP`→`THEME.ramps["rate"]`, and each `sl.WHITE/.../sl.ORANGE_BOLD/sl.RED/sl.MAGENTA_DARK_BOLD` expectation with `THEME.c("WHITE")` … `THEME.c("ORANGE_BOLD")` … `THEME.c("MAGENTA_DARK_BOLD")`.
- **`TestVisibleWidth.test_ansi_is_zero_width`** (101): `f"{sl.RED}hi{sl.RESET}"` → `f'{THEME.c("RED")}hi{sl.RESET}'` (`RESET` stays a const).
- **`TestEffortTable`** (141): `sl._EFFORT_BARS`→`THEME.effort`; `sl.CYAN/BLUE/YELLOW/ORANGE/RED`→`THEME.c(...)`; the fill-count test splits on `THEME.c("GREY")` instead of `sl.GREY`.
- **`TestCooperativeBuilders`** (158): add `THEME` as the third arg to **every** direct builder call — `sl.seg_branch(_data(...), 50, THEME)`, and likewise `seg_effort`, `seg_context`, `seg_dimensions`, `seg_chat_size`, `seg_memory`, `seg_rate_limits`, `seg_model`, `seg_clock`, `seg_todo`, `seg_path`.
- **`TestPackLine`** (275): `pack_line` calls already work via its internal default theme; no color globals referenced — leave as is (the signature keeps `theme=None`).
- **`TestRenderLayout`** / **`TestRenderWithConfig`** / **`TestEndToEnd`**: `render` keeps `theme=None` default — leave the call sites; just ensure any `sl.Config(...)` literals include `ramps={}` (done in Task 3 Step 8).
- **`TestBlueFix`** (373): `sl.BLUE`→`THEME.c("BLUE")`, `sl.LIGHTBLUE`→`THEME.c("LIGHTBLUE")`. Keep the literal `"\033[38;5;33m"`/`"38;5;33"` expectations **for now** (value unchanged until Task 5). `seg_path(_data(), 80)` → `seg_path(_data(), 80, THEME)`.
- **`TestChatSizeRamp`** (387): `sl.CHAT_SIZE_RAMP`→`THEME.ramps["chat_size"]`; `sl.WHITE/.../sl.MAGENTA`→`THEME.c(...)`; `seg_chat_size(...)`→ add `THEME`.
- **`TestEffortAutoSetting`** (412): `sl.YELLOW`→`THEME.c("YELLOW")`; add `THEME` to the `seg_effort(...)` calls.
- **`TestPaletteInit`** (742): this class tests the deleted `init_palette`/globals. **Delete it** — `TestBuildTheme` (palette merge + ramp rebuild + effort rebuild) and `TestTheme` cover its intent.
- **`TestPaletteFromConfig`** (769): drop the `tearDown` calling `sl.init_palette()`. `test_palette_parsed_into_config` / `test_unknown_palette_key_dropped` stay (they exercise `load_config`). `test_main_applies_palette` stays valid — `main` now applies the palette via `build_theme`; it still emits `\033[1;34m` for `BLUE="1;34"`. Keep the assertion.
- **`TestThemeMatchesLegacy`** (added in Task 3): references the deleted `sl.CONTEXT_RAMP`/`sl.RED`/`sl._EFFORT_BARS`. **Delete it** — its job (prove equivalence across the cutover) is done.

Run: `python3 -m unittest tests.test_status_line -v` → FAIL (builders still take `(data, avail)`; some now get a third arg; globals referenced in still-unported spots).

- [ ] **Step 2: Thread `theme` into the packer and render**

`pack_line` (820) and `render` (845):

```python
def pack_line(keys, data, cols, cfg=None, theme=None):
    cfg = cfg or default_config()
    theme = theme or build_theme(cfg)
    ...
        s = BUILDERS[key](data, max(avail, 0), theme)
    ...


def render(data, cols, lines, cfg=None, theme=None):
    cfg = cfg or default_config()
    theme = theme or build_theme(cfg)
    out = []
    for ln in cfg.layout:
        if lines < ln.min_rows:
            continue
        packed = pack_line(ln.segments, data, cols, cfg, theme)
        ...
```

- [ ] **Step 3: Add `theme` to all 17 builders and the two rate helpers**

Change each signature to `def seg_x(data, avail, theme):` and replace every bare color global with a `theme` lookup. Exhaustive list:

```python
def seg_path(data, avail, theme):
    return f"{theme.c('BLUE')}{_display_dir(data['work_dir'], data['home'])}{RESET}"

def seg_branch(data, avail, theme):
    ...
    return _first_fitting([f"{theme.c('GREY')}[{icon} {branch}]{RESET}"], avail)

def seg_dirty(data, avail, theme):                # mark has no color; sig only
    ...

def seg_todo(data, avail, theme):
    ...
    if state == "in_progress":
        return f"📝 {theme.c('YELLOW')}{text}{RESET}"
    if state == "pending":
        return f"⏸  {theme.c('GREY')}{text}{RESET}"
    ...

def seg_model(data, avail, theme):
    ...
    return _first_fitting([f"{theme.c('CYAN')}{name}{RESET}"], avail)

def seg_time_ago(data, avail, theme):
    ...
    return _first_fitting([f"{theme.c('WHITE')}{ago}{RESET}"], avail)

def seg_clock(data, avail, theme):                # no color; sig only
    return _first_fitting([f"⏰{data['clock']}"], avail)

def seg_effort(data, avail, theme):
    ...
    color, bar = theme.effort.get(level.lower(), ("", f"{theme.c('GREY')}▁▃▄▆█"))
    word = f"{color}{level}{RESET}"
    ...   # [auto]/* variants use theme.c('GREY') in place of GREY

def seg_lines(data, avail, theme):
    s = (f"📃{BG_LIGHTGRAY}{theme.c('GREEN')}+{fmt_number(data['added'])}{RESET}"
         f"/{BG_LIGHTGRAY}{theme.c('RED')}-{fmt_number(data['removed'])}{RESET}")
    return _first_fitting([s], avail)

def seg_cost(data, avail, theme):                 # no color; sig only
def seg_total_time(data, avail, theme):           # no color; sig only
def seg_api_time(data, avail, theme):             # no color; sig only
def seg_dimensions(data, avail, theme):           # no color; sig only

def seg_context(data, avail, theme):
    pct = int(data["context_pct"])
    color = pick_color(pct, theme.ramps["context"])
    ...   # every inline {GREY} -> {theme.c('GREY')}; bar uses `color`

def seg_chat_size(data, avail, theme):
    ...
    color = pick_color(n, theme.ramps["chat_size"])
    return _first_fitting([f"💾 {color}{fmt_bytes(n)}{RESET}"], avail)

def seg_memory(data, avail, theme):               # no color; sig only

def seg_rate_limits(data, avail, theme):
    ...
    return _first_fitting([_rate_str(rate_limits, "long", theme),
                           _rate_str(rate_limits, "short", theme),
                           _rate_str(rate_limits, "none", theme)], avail)
```

And the helpers:

```python
def rate_color(pct, theme):
    return pick_color(float(pct), theme.ramps["rate"])

def _rate_str(rate_limits, detail, theme):
    ...
        color = rate_color(pct, theme)
    ...
```

(`seg_dirty`, `seg_clock`, `seg_cost`, `seg_total_time`, `seg_api_time`, `seg_dimensions`, `seg_memory` use no color — they only gain the unused `theme` parameter so the `BUILDERS[key](data, avail, theme)` call site is uniform.)

- [ ] **Step 4: Point `main()` at `build_theme`; delete the global system**

In `main()` (1072): replace `init_palette(cfg.palette)` with building the theme, and pass it to `render`:

```python
    cfg = load_config(os.environ)
    theme = build_theme(cfg)
    if args.print_config:
        print(cmd_print_config(cfg))
        return
    ...
    print("\n".join(render(data, cols, lines, cfg, theme)))
```

Then **delete**: `init_palette` (219–230), `_build_ramps` (191–216), the import-time `init_palette()` call (234), the fixed `LIGHTBLUE = "\033[38;5;75m"` module const (173, now a palette entry), and the now-unused `_MB` const (188). Keep `INF` (used by `_parse_threshold`, ramps, and `pick_color`). Keep `_PALETTE_DEFAULTS` (now consumed by `_resolve_palette`/`_build_effort`).

- [ ] **Step 5: Run the full suite**

Run: `python3 -m unittest tests.test_status_line -v` → all green. No behavior change: the equivalence the deleted `TestThemeMatchesLegacy` proved in Task 3 means every escape is identical to pre-E4b.

- [ ] **Step 6: Confirm no module color globals remain**

Run: `grep -nE '\b(globals\(\)|init_palette|_build_ramps|CONTEXT_RAMP|RATE_RAMP|CHAT_SIZE_RAMP|_EFFORT_BARS)\b' tools/status-line.py` → no matches. (This is the Pyright-noise fix the user asked for: no `globals()[...] =` writes anywhere.)

- [ ] **Step 7: Commit**

`refactor(status-line): thread Theme into builders; delete color globals — E4b`

---

## Phase 3 — Visual refresh

### Task 5: Pure-hue palette + bold-on-danger ramps + lighter blue

A deliberate appearance change, isolated from the refactor: base palette becomes pure hues, bold moves to a `+bold` modifier on the bands that earn emphasis (red bold in context/chat/rate, plus the top danger bands), and `BLUE` is lightened. Per the spec's `_PALETTE_DEFAULTS`/`_RAMP_DEFAULTS`.

**Files:**
- Modify: `tools/status-line.py`, `tests/test_status_line.py`

- [ ] **Step 1: Update the value-pinning tests to the new expectations (these now fail)**

Only tests that hardcode a literal escape or a specific named-color band need editing; tests that assert via `THEME.c(name)` already track the refresh automatically.

- **`TestBlueFix`**: change the literal expectations to the lightened blue —
  `test_blue_is_256color_true_blue` → assert `THEME.c("BLUE") == "\033[38;5;39m"` (rename the method to `test_blue_is_lightened_256color`); `test_path_emits_true_blue_not_bold_ansi` → assert `"38;5;39"` in output and still `"\033[1;34m"` absent. `test_lightblue_defined_for_chat_ramp` → `THEME.c("LIGHTBLUE") == "\033[38;5;75m"` (unchanged).
- **`TestPickColor`** (context ramp): the ORANGE/RED/top bands are now bold. Update expectations to the modifier names: ceil 40 → `THEME.c("ORANGE+bold")`, ceil 50 → `THEME.c("RED+bold")`, `inf` → `THEME.c("MAGENTA_DARK+bold")`. Lower bands (`WHITE/CYAN/BLUE/GREEN/YELLOW`) stay `THEME.c(name)`.
- **`TestChatSizeRamp`**: the `10M` band is now `RED+bold`, so the 5M–<10M range resolves to `THEME.c("RED+bold")`. Update `test_ramp_bands` rows `(5*MB, ...)`,`(5*MB+1, ...)`,`(9*MB, ...)` to `THEME.c("RED+bold")` and `test_seg_chat_size_colors_the_size` to assert `THEME.c("RED+bold")` in the 6 MB output. `10M`/`20M` stay `MAGENTA`.
- **`TestEffortTable`** / **`TestEffortAutoSetting`** / **`TestCooperativeBuilders`**: assert via `THEME.c(...)`/`THEME.effort` — no edits needed (CYAN etc. simply resolve to pure-hue escapes now).

Run the suite → FAIL on the updated literal pins.

- [ ] **Step 2: Make the palette pure-hue**

Replace `_PALETTE_DEFAULTS` (per spec):

```python
_PALETTE_DEFAULTS = {            # pure hues — no baked-in bold
    "GREY": "90", "WHITE": "97", "CYAN": "36", "GREEN": "32", "RED": "31",
    "YELLOW": "33", "MAGENTA": "35", "ORANGE": "38;5;208",
    "BLUE": "38;5;39",           # lightened (was 38;5;33); shade reviewed on-terminal
    "LIGHTBLUE": "38;5;75", "MAGENTA_DARK": "38;5;90",
}   # ORANGE_BOLD / MAGENTA_DARK_BOLD removed — bold now lives on the ramp band
```

- [ ] **Step 3: Move bold onto the ramp bands**

Replace `_RAMP_DEFAULTS` (per spec):

```python
_RAMP_DEFAULTS = {
    "context": [(10, "WHITE"), (15, "CYAN"), (20, "BLUE"), (25, "GREEN"),
                (30, "YELLOW"), (40, "ORANGE+bold"), (50, "RED+bold"),
                ("inf", "MAGENTA_DARK+bold")],
    "rate": [(50, "GREEN"), (80, "YELLOW"), ("inf", "RED+bold")],
    "chat_size": [("512k", "WHITE"), ("1M", "CYAN"), ("2M", "LIGHTBLUE"),
                  ("3M", "GREEN"), ("4M", "YELLOW"), ("5M", "ORANGE"),
                  ("10M", "RED+bold"), ("inf", "MAGENTA")],
}
```

Use-sites that read better bold but aren't ramp-driven hardcode the modifier at the call site so the *palette* stays pure (none required by default; e.g. `theme.c("CYAN+bold")` for the model name is optional and not part of this task unless the terminal review calls for it).

- [ ] **Step 4: Update the `_PALETTE_DEFAULTS` doc comment**

Reword the comment above `_PALETTE_DEFAULTS` to describe pure hues + `+modifiers` (drop the stale "init_palette() rebuilds the globals" sentence and the `BLUE is 38;5;33` note).

- [ ] **Step 5: Run the full suite**

Run: `python3 -m unittest tests.test_status_line -v` → green with the new colors.

- [ ] **Step 6: Commit**

`feat(status-line): pure-hue palette + bold-on-danger ramps + lighter blue — E4b`

---

## Phase 4 — Validation, recipe, docs

### Task 6: `--check` validates palette + ramp colorspecs

`validate_config_file` currently only checks unknown keys. Extend it to run every palette value and every ramp colorspec through `parse_color`, and every ramp threshold through `_parse_threshold`, reporting each failure (so `--check` is the authority the spec promises).

**Files:**
- Modify: `tools/status-line.py`, `tests/test_status_line.py`

- [ ] **Step 1: Write the failing tests**

Add to `TestCLI`:

```python
    def test_check_bad_palette_hex_returns_one(self):
        path = self._write('[palette]\nBLUE = "#zzz"\n')
        self.assertEqual(sl.cmd_check(path, {"HOME": "/h"}), 1)

    def test_check_unknown_modifier_returns_one(self):
        path = self._write('[palette]\nRED = "31+blink"\n')
        self.assertEqual(sl.cmd_check(path, {"HOME": "/h"}), 1)

    def test_check_bad_ramp_color_returns_one(self):
        path = self._write('[ramp.context]\n10 = "NOTACOLOR"\n')
        self.assertEqual(sl.cmd_check(path, {"HOME": "/h"}), 1)

    def test_check_bad_ramp_threshold_returns_one(self):
        path = self._write('[ramp.context]\noops = "RED"\n')
        self.assertEqual(sl.cmd_check(path, {"HOME": "/h"}), 1)

    def test_check_valid_palette_and_ramp_returns_zero(self):
        path = self._write('[palette]\nBLUE = "#3399ff"\n'
                           '[ramp.rate]\n50 = "GREEN"\ninf = "RED+bold"\n')
        self.assertEqual(sl.cmd_check(path, {"HOME": "/h"}), 0)
```

Run → FAIL (bad colorspecs currently pass validation).

- [ ] **Step 2: Extend `validate_config_file`**

After the existing unknown-palette-key loop (1032–1034), validate palette **values** against `parse_color` (with `palette=None`, mirroring `_resolve_palette`); after the `[[line]]` loop, validate the `[ramp.*]` blocks. Build a resolved palette to check ramp names:

```python
    resolved_palette = _resolve_palette(
        {k: str(v) for k, v in (raw.get("palette") or {}).items()
         if k in _PALETTE_DEFAULTS})
    for name, value in (raw.get("palette") or {}).items():
        if name in _PALETTE_DEFAULTS and parse_color(str(value), palette=None) is None:
            errors.append(f"bad palette color: {name} = {value!r}")
    for band, table in (raw.get("ramp") or {}).items():
        if band not in _RAMP_DEFAULTS:
            errors.append(f"unknown ramp: {band}")
            continue
        if not isinstance(table, dict):
            errors.append(f"ramp [{band}] must be a table")
            continue
        for thr, spec in table.items():
            try:
                _parse_threshold(thr)
            except ValueError:
                errors.append(f"ramp [{band}] bad threshold: {thr!r}")
            if parse_color(str(spec), resolved_palette) is None:
                errors.append(f"ramp [{band}] bad color: {spec!r}")
```

- [ ] **Step 3: Run** the new `TestCLI` cases + full suite → green.

- [ ] **Step 4: Commit**

`feat(status-line): --check validates palette + ramp colorspecs — E4b`

---

### Task 7: Sample recipe — palette + ramp defaults + grammar

The shipped recipe must document the new color grammar and carry the real defaults so the drift test pins it to the code.

**Files:**
- Modify: `tools/statusline.toml.sample`, `tests/test_status_line.py`

- [ ] **Step 1: Update the drift test to expect new palette + ramp blocks (fails)**

In `TestSampleRecipe.test_uncommented_matches_internal_defaults`, the `[palette]` assertion already compares to `dict(sl._PALETTE_DEFAULTS)` — it will pick up the pure-hue values automatically once the sample is updated. Add a ramp drift assertion:

```python
        # [ramp.*] blocks document the real default tables.
        want_ramps = {
            band: {str(thr): spec for thr, spec in pairs}
            for band, pairs in sl._RAMP_DEFAULTS.items()
        }
        self.assertEqual(parsed.get("ramp"), want_ramps)
```

Run `TestSampleRecipe` → FAIL (sample has no `[ramp.*]`; `[palette]` still lists the old bold values).

- [ ] **Step 2: Update the sample**

In `tools/statusline.toml.sample`: refresh the `[palette]` block to the pure-hue defaults (each line's value = the new default), and add a grammar comment block + the three `[ramp.*]` default blocks, all `# `-prefixed data lines (prose stays `## `). Follow the existing file's comment style. Sketch:

```toml
## ─── color grammar (used by [palette] and [ramp.*] values) ───────────────────
## A color value is one of:
##   * a palette NAME            e.g. RED, BLUE, ORANGE
##   * a raw SGR parameter list  e.g. 38;5;208   (advanced; "xy;x;ab" form)
##   * a hex color               e.g. #3399ff  (#rgb / #rrggbb / #rrggbbaa;
##                                              an accidental IDE alpha is dropped)
## Any of these may carry +bold / +dim / +italic / +underline modifiers, e.g.
## RED+bold, #3399ff+bold. Hex needs a truecolor terminal; italic/underline vary.
## [palette] MERGES over the defaults (override just the names you list);
## [ramp.X] REPLACES that whole ramp (list every band you want).

## ─── [palette] — named colors (each value below IS the default) ──────────────
# [palette]
# GREY = "90"
# WHITE = "97"
# CYAN = "36"
# GREEN = "32"
# RED = "31"
# YELLOW = "33"
# MAGENTA = "35"
# ORANGE = "38;5;208"
# BLUE = "38;5;39"
# LIGHTBLUE = "38;5;75"
# MAGENTA_DARK = "38;5;90"

## ─── [ramp.context] — context-window % -> color (whole-ramp replace) ─────────
# [ramp.context]
# 10 = "WHITE"
# 15 = "CYAN"
# 20 = "BLUE"
# 25 = "GREEN"
# 30 = "YELLOW"
# 40 = "ORANGE+bold"
# 50 = "RED+bold"
# inf = "MAGENTA_DARK+bold"

## ─── [ramp.rate] — rate-limit % -> color ────────────────────────────────────
# [ramp.rate]
# 50 = "GREEN"
# 80 = "YELLOW"
# inf = "RED+bold"

## ─── [ramp.chat_size] — transcript bytes -> color (k/M/G suffixes) ──────────
# [ramp.chat_size]
# "512k" = "WHITE"
# "1M" = "CYAN"
# "2M" = "LIGHTBLUE"
# "3M" = "GREEN"
# "4M" = "YELLOW"
# "5M" = "ORANGE"
# "10M" = "RED+bold"
# inf = "MAGENTA"
```

The drift test reconstructs config from `# `-prefixed lines, so quoting must parse: bare `10`/`inf` keys are fine; byte thresholds (`"512k"`) are quoted. `test_as_shipped_is_all_commented_noop` requires every non-blank line start with `#` — keep all data lines `# `-prefixed.

- [ ] **Step 3: Run** `TestSampleRecipe` + full suite → green. The reconstructed TOML's `palette` equals `_PALETTE_DEFAULTS` and `ramp` equals the `_RAMP_DEFAULTS` tables.

- [ ] **Step 4: Commit**

`docs(status-line): sample recipe documents color grammar + ramp defaults — E4b`

---

### Task 8: README — color grammar + config blocks

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Document the color system**

In the status-line config section of `README.md`, add: the color grammar (palette name / raw SGR / hex, all with `+bold/+dim/+italic/+underline`), `[palette]` **merges** vs `[ramp.*]` **replaces a band wholesale**, threshold keys (percent for context/rate, `k/M/G` bytes for chat_size, `inf`), the file-only precedence (no `CC_AI_KIT_*` color env), and the caveats (hex needs truecolor; italic/underline are terminal-dependent). Point to `--check` for validation and `--print-config` to see the resolved config.

- [ ] **Step 2: Sanity-check** any README-pinning test (`TestDocumentation` asserts only `status-line.py` source phrases, not the README — no test impact). Run the full suite to be safe → green.

- [ ] **Step 3: Commit**

`docs: document status-line color grammar + [palette]/[ramp.*] — E4b`

---

## Phase 5 — Wrap-up

### Task 9: Full verification + acceptance cross-check + commit compaction

**Files:**
- Verify only, then compact history.

- [ ] **Step 1: Full test + lint sweep**

Run all three and confirm green:
- `python3 -m unittest tests.test_status_line -v`
- `bash tests/test_install.sh`
- `shellcheck tools/install.sh`

- [ ] **Step 2: No-globals / Pyright-noise check**

Run `grep -nE '\b(globals\(\)|init_palette|_build_ramps|CONTEXT_RAMP|RATE_RAMP|CHAT_SIZE_RAMP|_EFFORT_BARS|_MB)\b' tools/status-line.py` → no matches. Optionally run `pyright tools/status-line.py` (if available) and confirm no undefined-color errors.

- [ ] **Step 3: Smoke-test the CLI end to end**

- `echo '{}' | python3 tools/status-line.py` → renders without error.
- `python3 tools/status-line.py --print-config` → JSON includes `segments`, `layout`, `palette`, `ramps`.
- Point `CC_AI_KIT_CONFIG` at a temp file with `[ramp.rate]` + `[palette]` overrides and `--check` it (exit 0); add a bad hex and confirm exit 1 with a message.

- [ ] **Step 4: Cross-check the spec acceptance criteria**

Walk the spec's Acceptance criteria list (parse_color forms; pure-hue palette + modifiers; `[ramp.*]` replace + threshold forms + unspecified-keep-default; no mutable color globals + Theme threaded; `--check` validates all colorspecs; sample + README; existing tests pass + new coverage) and confirm each is satisfied. Note any gap and fix before compaction.

- [ ] **Step 5: Compact commits to one-per-logical-unit**

Per the working agreement, before closing the phase squash the task-by-task history into coherent one-per-feature commits (e.g. `parse_color + thresholds`, `Theme system + config`, `cutover/refactor`, `visual refresh`, `--check validation`, `recipe + README`). Use `git commit-tree` chaining if `rebase -i` is unavailable in the environment; verify the final tree is byte-identical to the pre-compaction head and the full suite is still green afterward. Do **not** push or merge unless asked.

---

## Notes & risks

- **Two writes of `_RAMP_DEFAULTS`/`_PALETTE_DEFAULTS`** (Task 3 values-preserved → Task 5 refresh) is deliberate: it keeps the structural cutover (Task 4) provably behavior-neutral, isolating the visual change to one reviewable diff. `TestThemeMatchesLegacy` is the safety net that proves Task 3+4 change nothing; it is removed in Task 4 once its job is done.
- **`_DIM` vs `GREY`**: warning strings must not depend on the (now palette-resolved) `GREY`, since `GREY` is no longer a module global. `_DIM` is a fixed const introduced in Task 3 and used from then on.
- **`Config` field addition** ripples to every `sl.Config(...)` literal in the tests (`TestRenderWithConfig`, `TestCLI`); add `ramps={}`/`ramps=...` when the field is introduced (Task 3 Step 8) to avoid spurious failures.
- **Palette override values are hex/raw-SGR only** (no name nesting → no cycles), matching `parse_color(value, palette=None)` in `_resolve_palette`. Ramp colorspecs *do* resolve names (against the merged palette).
- **External drop-in segments stay out of scope** — that is E4c, after E5.
