# E4a — Status-line Config Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `tools/status-line.py` configurable through a three-tier resolution (internal defaults < `~/.config/ai-kit/statusline.toml` < `CC_AI_KIT_*` env) covering segment toggles, layout, and palette — without changing default behavior when no config is present.

**Architecture:** A `Config` namedtuple `(segments, layout, palette)` is resolved once in `main()` via `load_config(env)` and threaded into `render`/`pack_line` (both keep a `cfg=None` default that falls back to a snapshot of the module globals, so existing call sites and tests stay green). Colors move behind a `_PALETTE_DEFAULTS` table + `init_palette()` so palette overrides rebuild the ramps that derive from them. A fully-commented `statusline.toml.sample` ships in the repo, is copied by `install.sh` only when absent, and a drift test pins it to the internal defaults. `--print-config` / `--check` / `--help` add introspection. External drop-in segments are **out of scope** (E4b).

**Tech Stack:** Python 3.11+ stdlib only (`tomllib`, `argparse`, `json`, `os`, `sys`), `unittest` for Python tests, bash + `shellcheck` for the installer, TOML for the config file.

**Spec:** `docs/prds/statusline-config-extensibility-v1.0-prd.md` (E4a, v1.1).

**Branch:** `feat/e4a-statusline-config` (off clean `main`; E3 already merged).

**Test commands:**
- Python: `python3 -m unittest tests.test_status_line -v`
- Installer: `bash tests/test_install.sh`
- Lint installer: `shellcheck tools/install.sh`

---

## File Structure

- `tools/status-line.py` — **modify**. Add `Config`, `default_config`, `env_bool`, `config_path`, `_load_toml`, `_resolve_segments`, `_resolve_layout`, `load_config`, `_PALETTE_DEFAULTS`, `init_palette`, `_build_ramps`, `validate_config_file`, `cmd_print_config`, `cmd_check`, `parse_args`; thread `cfg` into `pack_line`/`render`; move `Line`/`LAYOUT`/`PINNED` to the top editable surface.
- `tools/statusline.toml.sample` — **create**. The canonical fully-commented recipe (a no-op until edited).
- `tools/install.sh` — **modify**. Add `install_statusline_config()` (copy sample to the config path if absent) and call it from `main()`.
- `tests/test_status_line.py` — **modify**. New test classes for env_bool, config resolution, layout/palette overrides, the sample drift check, and the CLI flags.
- `tests/test_install.sh` — **modify**. Assert the sample is copied when absent and never overwrites an existing config.
- `README.md` — **modify**. Document the config file, env vars, and precedence.

All new top-level names introduced and used consistently across tasks:
`Config(segments, layout, palette)`, `default_config()`, `env_bool(env, name)`, `config_path(env)`, `_load_toml(path)`, `_resolve_segments(defaults, file_seg, env)`, `_resolve_layout(default_layout, raw_lines)`, `load_config(env)`, `_PALETTE_DEFAULTS`, `init_palette(overrides=None)`, `_build_ramps()`, `validate_config_file(path, env)`, `cmd_print_config(cfg)`, `cmd_check(path, env)`, `parse_args(argv)`, `_NO_CHECK`.

---

## Phase 1 — Config core

### Task 1: Editable-surface reorg + `Config` scaffold

Move the layout template to the top with `SEGMENTS`, and add the `Config` type plus a `default_config()` that snapshots the current module globals. This is the seam every later task plugs into. No behavior change.

**Files:**
- Modify: `tools/status-line.py`

- [ ] **Step 1: Add a baseline test that pins current default render output**

Add to `tests/test_status_line.py` (near `TestRenderLayout`, end of file):

```python
class TestConfigScaffold(unittest.TestCase):
    def test_default_config_matches_globals(self):
        cfg = sl.default_config()
        self.assertEqual(cfg.segments, dict(sl.SEGMENTS))
        self.assertEqual(cfg.layout, list(sl.LAYOUT))
        self.assertEqual(cfg.palette, {})

    def test_default_config_is_a_snapshot(self):
        cfg = sl.default_config()
        cfg.segments["clock"] = not cfg.segments["clock"]
        self.assertNotEqual(cfg.segments["clock"], sl.SEGMENTS["clock"])  # snapshot, not alias
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python3 -m unittest tests.test_status_line.TestConfigScaffold -v`
Expected: FAIL with `AttributeError: module ... has no attribute 'default_config'`

- [ ] **Step 3: Move `Line`/`LAYOUT`/`PINNED` to the top editable surface**

In `tools/status-line.py`, **delete** this block from its current location (just above `# ═══ Extractors`):

```python
# ═══ Layout template — edit to reorder / move / re-line segments ═════════════
# One Line per row. `segments` lists keys LEFT->RIGHT; leftmost = highest
# priority (kept first when space is tight). `min_rows` gates the whole row by
# terminal height. Reorder = move a key within a list; move between rows = cut
# and paste a key; hide = flip its SEGMENTS flag.
Line = namedtuple("Line", "min_rows segments")
LAYOUT = [
    Line(0,  ["path", "branch", "dirty", "todo"]),
    Line(20, ["model", "time_ago", "clock", "effort", "lines",
              "cost", "total_time", "api_time"]),
    Line(30, ["dimensions", "context", "chat_size", "memory", "rate_limits"]),
]
PINNED = {"path", "context"}   # always rendered even if they overflow the budget
```

Then **insert** it immediately after the `SEGMENTS = { ... }` dict and its identity-line tuning constants (`PATH_MAX_LEN`, `CONTEXT_BAR_CELLS`, `RIGHT_MARGIN`, `SEP`), i.e. right before the `# ═══ Palette` banner. `Line`/`LAYOUT`/`PINNED` reference only segment-key strings, so they are safe to define before the builder functions. `BUILDERS` (key→function) stays where it is, below the builders.

- [ ] **Step 4: Annotate where `BUILDERS` lives**

Add this comment directly above the existing `BUILDERS = {` definition:

```python
# Editable surface (SEGMENTS + LAYOUT) is at the top of the file; this registry
# (key -> builder function) stays next to the builders it wires up.
```

- [ ] **Step 5: Add the `Config` type and `default_config()`**

Add directly below the relocated `PINNED = {...}` line:

```python
# Resolved configuration: the result of merging internal defaults < TOML file <
# env. `segments` is a {key: bool} dict, `layout` a list[Line], `palette` a
# {NAME: "sgr;params"} dict of overrides (empty = no override). External drop-in
# segments are E4b and are intentionally not part of this type yet.
Config = namedtuple("Config", "segments layout palette")


def default_config():
    """A Config snapshotting the current module-global defaults (SEGMENTS/LAYOUT,
    no palette overrides). Copies are returned so callers cannot mutate globals."""
    return Config(segments=dict(SEGMENTS), layout=list(LAYOUT), palette={})
```

- [ ] **Step 6: Run the new test and the full suite**

Run: `python3 -m unittest tests.test_status_line -v`
Expected: PASS (all prior tests still green; `TestConfigScaffold` passes). The reorg changed nothing observable.

- [ ] **Step 7: Commit**

```bash
git add tools/status-line.py tests/test_status_line.py
git commit -m "refactor(status-line): hoist LAYOUT to editable surface, add Config + default_config (E4a)"
```

---

### Task 2: `env_bool` tri-state parser

**Files:**
- Modify: `tools/status-line.py`
- Test: `tests/test_status_line.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_status_line.py`:

```python
class TestEnvBool(unittest.TestCase):
    def test_true_tokens(self):
        for v in ("1", "true", "T", "y", "Yes", "on", "ON"):
            self.assertIs(sl.env_bool({"X": v}, "X"), True, v)

    def test_false_tokens(self):
        for v in ("0", "false", "F", "n", "No", "off", "OFF"):
            self.assertIs(sl.env_bool({"X": v}, "X"), False, v)

    def test_unset_is_none(self):
        self.assertIsNone(sl.env_bool({}, "X"))

    def test_unrecognized_is_none(self):
        self.assertIsNone(sl.env_bool({"X": "maybe"}, "X"))
        self.assertIsNone(sl.env_bool({"X": ""}, "X"))
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python3 -m unittest tests.test_status_line.TestEnvBool -v`
Expected: FAIL with `AttributeError: ... has no attribute 'env_bool'`

- [ ] **Step 3: Implement `env_bool`**

Add to `tools/status-line.py` in a new section just below the `default_config()` definition:

```python
# ═══ Config resolution (defaults < TOML file < env) ══════════════════════════
_ENV_TRUE = {"1", "true", "t", "y", "yes", "on"}
_ENV_FALSE = {"0", "false", "f", "n", "no", "off"}


def env_bool(env, name):
    """Tri-state bool from env[name]: True / False / None (unset or unrecognized).
    None means 'no override' so callers fall through to file/default."""
    v = env.get(name)
    if v is None:
        return None
    v = v.strip().lower()
    if v in _ENV_TRUE:
        return True
    if v in _ENV_FALSE:
        return False
    return None
```

- [ ] **Step 4: Run to verify it passes**

Run: `python3 -m unittest tests.test_status_line.TestEnvBool -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tools/status-line.py tests/test_status_line.py
git commit -m "feat(status-line): add env_bool tri-state parser (E4a)"
```

---

### Task 3: Config path + TOML loader (malformed-tolerant)

**Files:**
- Modify: `tools/status-line.py`
- Test: `tests/test_status_line.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_status_line.py`:

```python
class TestConfigPathAndLoad(unittest.TestCase):
    def test_explicit_path_wins(self):
        env = {"CC_AI_KIT_CONFIG": "/tmp/x.toml", "HOME": "/home/u"}
        self.assertEqual(sl.config_path(env), "/tmp/x.toml")

    def test_xdg_path(self):
        env = {"XDG_CONFIG_HOME": "/cfg", "HOME": "/home/u"}
        self.assertEqual(sl.config_path(env), "/cfg/ai-kit/statusline.toml")

    def test_home_default_path(self):
        env = {"HOME": "/home/u"}
        self.assertEqual(sl.config_path(env), "/home/u/.config/ai-kit/statusline.toml")

    def test_missing_file_is_empty(self):
        self.assertEqual(sl._load_toml("/no/such/file.toml"), {})

    def test_malformed_file_is_empty_no_crash(self):
        with tempfile.NamedTemporaryFile("w", suffix=".toml", delete=False) as f:
            f.write("this is = = not toml")
            path = f.name
        try:
            self.assertEqual(sl._load_toml(path), {})
        finally:
            os.unlink(path)

    def test_valid_file_parses(self):
        with tempfile.NamedTemporaryFile("w", suffix=".toml", delete=False) as f:
            f.write("[segments]\ncost = true\n")
            path = f.name
        try:
            self.assertEqual(sl._load_toml(path), {"segments": {"cost": True}})
        finally:
            os.unlink(path)
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python3 -m unittest tests.test_status_line.TestConfigPathAndLoad -v`
Expected: FAIL with `AttributeError: ... has no attribute 'config_path'`

- [ ] **Step 3: Add the `tomllib` import**

At the top of `tools/status-line.py`, in the import block (after `import time`), add:

```python
try:
    import tomllib
except ModuleNotFoundError:        # Python < 3.11 — degrade to env-only config.
    tomllib = None
```

- [ ] **Step 4: Implement `config_path` and `_load_toml`**

Add below `env_bool` in the config-resolution section:

```python
def config_path(env):
    """Resolved TOML path: CC_AI_KIT_CONFIG, else
    ${XDG_CONFIG_HOME:-$HOME/.config}/ai-kit/statusline.toml."""
    explicit = env.get("CC_AI_KIT_CONFIG")
    if explicit:
        return os.path.expanduser(explicit)
    base = env.get("XDG_CONFIG_HOME") or os.path.join(env.get("HOME", ""), ".config")
    return os.path.join(base, "ai-kit", "statusline.toml")


def _load_toml(path):
    """Parse the TOML at path. Missing/empty/malformed/no-tomllib → {} (a dim
    warning to stderr on a malformed file). Never raises."""
    if tomllib is None:
        return {}
    try:
        with open(path, "rb") as f:
            return tomllib.load(f)
    except FileNotFoundError:
        return {}
    except (OSError, tomllib.TOMLDecodeError) as e:
        print(f"{GREY}status-line: ignoring config {path}: {e}{RESET}", file=sys.stderr)
        return {}
```

- [ ] **Step 5: Run to verify it passes**

Run: `python3 -m unittest tests.test_status_line.TestConfigPathAndLoad -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add tools/status-line.py tests/test_status_line.py
git commit -m "feat(status-line): config_path + malformed-tolerant TOML loader (E4a)"
```

---

### Task 4: Segment resolution (`load_config` part 1)

Resolve segment visibility as defaults < file `[segments]` < `CC_AI_KIT_SEGMENT_*` env. Layout/palette are added in Phase 2 but `load_config` returns a full `Config` now (layout = defaults, palette = {}).

**Files:**
- Modify: `tools/status-line.py`
- Test: `tests/test_status_line.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_status_line.py`:

```python
class TestResolveSegments(unittest.TestCase):
    def _write(self, body):
        f = tempfile.NamedTemporaryFile("w", suffix=".toml", delete=False)
        f.write(body)
        f.close()
        self.addCleanup(os.unlink, f.name)
        return f.name

    def test_defaults_when_no_file_no_env(self):
        env = {"CC_AI_KIT_CONFIG": "/no/such.toml", "HOME": "/h"}
        cfg = sl.load_config(env)
        self.assertEqual(cfg.segments, dict(sl.SEGMENTS))
        self.assertEqual(cfg.layout, list(sl.LAYOUT))
        self.assertEqual(cfg.palette, {})

    def test_file_overrides_default(self):
        path = self._write("[segments]\ncost = true\nmemory = false\n")
        cfg = sl.load_config({"CC_AI_KIT_CONFIG": path, "HOME": "/h"})
        self.assertTrue(cfg.segments["cost"])      # default False -> True
        self.assertFalse(cfg.segments["memory"])   # default True  -> False
        self.assertTrue(cfg.segments["clock"])     # untouched default

    def test_env_overrides_file(self):
        path = self._write("[segments]\ncost = true\n")
        env = {"CC_AI_KIT_CONFIG": path, "HOME": "/h", "CC_AI_KIT_SEGMENT_COST": "0"}
        cfg = sl.load_config(env)
        self.assertFalse(cfg.segments["cost"])     # env beats file

    def test_unknown_segment_key_ignored(self):
        path = self._write("[segments]\nbogus = true\n")
        cfg = sl.load_config({"CC_AI_KIT_CONFIG": path, "HOME": "/h"})
        self.assertNotIn("bogus", cfg.segments)

    def test_wrong_type_value_ignored(self):
        # `cost = "true"` (string, not bool) is a known key but a bad value:
        # it must be dropped (keeping the default), not silently coerced.
        path = self._write('[segments]\ncost = "true"\n')
        cfg = sl.load_config({"CC_AI_KIT_CONFIG": path, "HOME": "/h"})
        self.assertEqual(cfg.segments["cost"], sl.SEGMENTS["cost"])  # default kept
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python3 -m unittest tests.test_status_line.TestResolveSegments -v`
Expected: FAIL with `AttributeError: ... has no attribute 'load_config'`

- [ ] **Step 3: Implement `_resolve_segments` and `load_config`**

Add below `_load_toml`:

```python
def _resolve_segments(defaults, file_seg, env):
    """defaults < file [segments] < CC_AI_KIT_SEGMENT_<KEY> env. Each file entry
    is dropped with a dim warning if its key is unknown OR its value is not a
    bool (e.g. `cost = "true"` instead of `cost = true`); only bool file values
    for known keys are honored. Env always overrides whatever the file resolved."""
    seg = dict(defaults)
    for k, v in (file_seg or {}).items():
        if k not in seg:
            print(f"{GREY}status-line: unknown segment '{k}' in config{RESET}",
                  file=sys.stderr)
        elif not isinstance(v, bool):
            print(f"{GREY}status-line: segment '{k}' must be true/false, "
                  f"got {v!r} — ignored{RESET}", file=sys.stderr)
        else:
            seg[k] = v
    for k in seg:
        ov = env_bool(env, f"CC_AI_KIT_SEGMENT_{k.upper()}")
        if ov is not None:
            seg[k] = ov
    return seg


def load_config(env):
    """Resolve the full Config: internal defaults < TOML file < env.
    Layout and palette resolution are added in Phase 2; for now they are the
    defaults / empty so callers get a complete Config from day one."""
    base = default_config()
    raw = _load_toml(config_path(env))
    segments = _resolve_segments(base.segments, raw.get("segments"), env)
    return Config(segments=segments, layout=base.layout, palette={})
```

- [ ] **Step 4: Run to verify it passes**

Run: `python3 -m unittest tests.test_status_line.TestResolveSegments -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tools/status-line.py tests/test_status_line.py
git commit -m "feat(status-line): load_config segment resolution (defaults<file<env) (E4a)"
```

---

### Task 5: Thread `cfg` into `pack_line` and `render`

Make the render path consume a `Config` while keeping the old signatures working (`cfg=None` → `default_config()`), so all existing tests and the `sl.SEGMENTS` global-mutation tests stay green.

**Files:**
- Modify: `tools/status-line.py`
- Test: `tests/test_status_line.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_status_line.py`:

```python
class TestRenderWithConfig(unittest.TestCase):
    def test_pack_line_honors_cfg_segments(self):
        cfg = sl.Config(segments={**sl.SEGMENTS, "clock": False},
                        layout=list(sl.LAYOUT), palette={})
        out = strip(sl.pack_line(["model", "clock"], _data(), 200, cfg))
        self.assertNotIn("⏰", out)
        self.assertIn("Opus 4.8", out)

    def test_render_honors_cfg_layout(self):
        cfg = sl.Config(segments=dict(sl.SEGMENTS),
                        layout=[sl.Line(0, ["model"])], palette={})
        lines = sl.render(_data(), 200, 50, cfg)
        self.assertEqual(len(lines), 1)
        self.assertIn("Opus 4.8", strip(lines[0]))

    def test_render_default_cfg_unchanged(self):
        # No cfg arg -> same as today (three rows when tall+wide).
        self.assertEqual(len(sl.render(_data(), 200, 50)), 3)
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python3 -m unittest tests.test_status_line.TestRenderWithConfig -v`
Expected: FAIL — `test_pack_line_honors_cfg_segments` / `test_render_honors_cfg_layout` raise `TypeError: pack_line() takes 3 positional arguments but 4 were given`.

- [ ] **Step 3: Add `cfg` to `pack_line`**

In `tools/status-line.py`, change the `pack_line` signature and the two global reads. Replace:

```python
def pack_line(keys, data, cols):
```
with:
```python
def pack_line(keys, data, cols, cfg=None):
```

Immediately after the docstring inside `pack_line`, add:

```python
    cfg = cfg or default_config()
```

Replace `if not SEGMENTS.get(key, False):` with:

```python
        if not cfg.segments.get(key, False):       # flag gate: not built => no compute
```

(`PINNED` stays a module global — it is not user-configurable in E4a.)

- [ ] **Step 4: Add `cfg` to `render`**

Replace:

```python
def render(data, cols, lines):
    """Render up to len(LAYOUT) lines, gated by terminal height and width."""
    out = []
    for ln in LAYOUT:
        if lines < ln.min_rows:
            continue
        packed = pack_line(ln.segments, data, cols)
        if packed:
            out.append(packed)
    return out
```
with:
```python
def render(data, cols, lines, cfg=None):
    """Render up to len(cfg.layout) lines, gated by terminal height and width."""
    cfg = cfg or default_config()
    out = []
    for ln in cfg.layout:
        if lines < ln.min_rows:
            continue
        packed = pack_line(ln.segments, data, cols, cfg)
        if packed:
            out.append(packed)
    return out
```

- [ ] **Step 5: Run the new tests and the full suite**

Run: `python3 -m unittest tests.test_status_line -v`
Expected: PASS. `TestPackLine.test_flag_off_segment_not_built` still passes because it mutates `sl.SEGMENTS` and calls `pack_line` without a `cfg`, so `default_config()` snapshots the mutated global.

- [ ] **Step 6: Commit**

```bash
git add tools/status-line.py tests/test_status_line.py
git commit -m "refactor(status-line): thread Config through pack_line/render (back-compatible) (E4a)"
```

---

### Task 6: Wire `load_config` into `main()`

Resolve config once at startup and pass it to `render`. With no file and no env, output is byte-for-byte identical to today.

**Files:**
- Modify: `tools/status-line.py`
- Test: `tests/test_status_line.py`

- [ ] **Step 1: Add `import sys` to the test file (test scaffolding, not a TDD step)**

The `TestMainUsesConfig` test in Step 2 patches `sys.stdin`, so the test module needs `sys`. This is test infrastructure, not production code, so there is no failing test to assert here yet — the write-FAIL → implement → PASS cycle for this task begins in Step 2.

At the top of `tests/test_status_line.py`, in the import block (after `import re`), add:

```python
import sys
```

Run: `python3 -m unittest tests.test_status_line -v`
Expected: PASS — adding an import is inert; all prior tests stay green. (This is a sanity check that the import did not break collection, NOT a TDD PASS — the real failing test lands in Step 2.)

- [ ] **Step 2: Write the failing test**

Add to `tests/test_status_line.py`:

```python
class TestMainUsesConfig(unittest.TestCase):
    def _run_main(self, raw, env):
        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with mock.patch.object(sys, "stdin", io.StringIO(json.dumps(raw))), \
             mock.patch.dict(os.environ, env, clear=True), \
             redirect_stdout(buf):
            sl.main()
        return buf.getvalue()

    def test_segment_hidden_via_env(self):
        raw = {"workspace": {"current_dir": "/tmp"}, "model": {"display_name": "Opus"},
               "context_window": {"used_percentage": 10}}
        # PATH is preserved: build_data shells out to `git` (unguarded), and
        # clear=True would otherwise strip it and crash main().
        env = {"HOME": "/tmp", "STATUSLINE_COLS": "200", "STATUSLINE_LINES": "50",
               "PATH": os.environ.get("PATH", ""),
               "CC_AI_KIT_SEGMENT_CLOCK": "0", "CC_AI_KIT_CONFIG": "/no/such.toml"}
        out = strip(self._run_main(raw, env))
        self.assertNotIn("⏰", out)
        self.assertIn("Opus", out)
```

- [ ] **Step 3: Run it to verify it fails**

Run: `python3 -m unittest tests.test_status_line.TestMainUsesConfig -v`
Expected: FAIL — `⏰` still present because `main()` ignores config.

- [ ] **Step 4: Wire config into `main()`**

Replace the body of `main()`:

```python
def main():
    try:
        raw = json.load(sys.stdin)
    except (ValueError, OSError):
        raw = {}
    data, cols, lines = build_data(raw, os.environ)
    print("\n".join(render(data, cols, lines)))
```
with:
```python
def main():
    cfg = load_config(os.environ)
    try:
        raw = json.load(sys.stdin)
    except (ValueError, OSError):
        raw = {}
    data, cols, lines = build_data(raw, os.environ)
    print("\n".join(render(data, cols, lines, cfg)))
```

- [ ] **Step 5: Run to verify it passes**

Run: `python3 -m unittest tests.test_status_line -v`
Expected: PASS (full suite).

- [ ] **Step 6: Commit**

```bash
git add tools/status-line.py tests/test_status_line.py
git commit -m "feat(status-line): main() resolves and applies config (E4a)"
```

---

## Phase 2 — Layout + palette from config

### Task 7: Layout override via `[[line]]` (all-or-nothing)

**Files:**
- Modify: `tools/status-line.py`
- Test: `tests/test_status_line.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_status_line.py`:

```python
class TestResolveLayout(unittest.TestCase):
    def _write(self, body):
        f = tempfile.NamedTemporaryFile("w", suffix=".toml", delete=False)
        f.write(body)
        f.close()
        self.addCleanup(os.unlink, f.name)
        return f.name

    def test_no_line_keeps_default_layout(self):
        cfg = sl.load_config({"CC_AI_KIT_CONFIG": "/no/such.toml", "HOME": "/h"})
        self.assertEqual(cfg.layout, list(sl.LAYOUT))

    def test_line_replaces_layout(self):
        path = self._write(
            '[[line]]\nmin_rows = 0\nsegments = ["path", "model"]\n'
            '[[line]]\nmin_rows = 25\nsegments = ["context"]\n')
        cfg = sl.load_config({"CC_AI_KIT_CONFIG": path, "HOME": "/h"})
        self.assertEqual(cfg.layout,
                         [sl.Line(0, ["path", "model"]), sl.Line(25, ["context"])])

    def test_line_missing_min_rows_defaults_zero(self):
        path = self._write('[[line]]\nsegments = ["path"]\n')
        cfg = sl.load_config({"CC_AI_KIT_CONFIG": path, "HOME": "/h"})
        self.assertEqual(cfg.layout, [sl.Line(0, ["path"])])
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python3 -m unittest tests.test_status_line.TestResolveLayout -v`
Expected: FAIL — `test_line_replaces_layout` fails (layout still default; `load_config` ignores `[[line]]`).

- [ ] **Step 3: Implement `_resolve_layout` and wire it in**

Add below `_resolve_segments`:

```python
def _resolve_layout(default_layout, raw_lines):
    """If the file has ANY [[line]] block, it REPLACES the whole layout
    (all-or-nothing — a partial layout can't silently drop segments). Otherwise
    keep the default. Each block: min_rows (default 0) + segments list."""
    if not raw_lines:
        return list(default_layout)
    return [Line(int(item.get("min_rows", 0)), list(item.get("segments", [])))
            for item in raw_lines]
```

In `load_config`, replace the return line:

```python
    return Config(segments=segments, layout=base.layout, palette={})
```
with:
```python
    layout = _resolve_layout(base.layout, raw.get("line"))
    return Config(segments=segments, layout=layout, palette={})
```

- [ ] **Step 4: Run to verify it passes**

Run: `python3 -m unittest tests.test_status_line.TestResolveLayout -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tools/status-line.py tests/test_status_line.py
git commit -m "feat(status-line): [[line]] layout override (all-or-nothing) (E4a)"
```

---

### Task 8: Palette refactor — `_PALETTE_DEFAULTS` + `init_palette` + `_build_ramps`

Move the overridable colors behind a defaults table and a (re)builder so palette overrides can rebuild the ramps that derive from them. Default behavior at import is unchanged.

**Files:**
- Modify: `tools/status-line.py`
- Test: `tests/test_status_line.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_status_line.py`:

```python
class TestPaletteInit(unittest.TestCase):
    def tearDown(self):
        sl.init_palette()   # always restore defaults after a palette test

    def test_defaults_unchanged_at_import(self):
        self.assertEqual(sl.BLUE, "\033[38;5;33m")
        self.assertEqual(sl.RED, "\033[1;31m")
        # A ramp entry derives from the color globals.
        self.assertIn(sl.BLUE, [c for _, c in sl.CONTEXT_RAMP])

    def test_override_changes_color_and_ramp(self):
        sl.init_palette({"BLUE": "1;34"})
        self.assertEqual(sl.BLUE, "\033[1;34m")
        self.assertIn("\033[1;34m", [c for _, c in sl.CONTEXT_RAMP])  # ramp rebuilt
        self.assertEqual(sl._EFFORT_BARS["medium"][0], "\033[1;34m")  # effort bar rebuilt

    def test_unknown_override_ignored(self):
        before = sl.BLUE
        sl.init_palette({"NOTACOLOR": "1;34"})
        self.assertEqual(sl.BLUE, before)

    def test_restore_via_no_arg(self):
        sl.init_palette({"BLUE": "1;34"})
        sl.init_palette()
        self.assertEqual(sl.BLUE, "\033[38;5;33m")
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python3 -m unittest tests.test_status_line.TestPaletteInit -v`
Expected: FAIL with `AttributeError: ... has no attribute 'init_palette'`

- [ ] **Step 3: Replace the palette + ramp + effort-bar definitions**

In `tools/status-line.py`, **replace** the entire `# ═══ Palette` block and the `# ═══ Color ramps` block (the constants `RESET`…`MAGENTA_DARK_BOLD`, `INF`, `CONTEXT_RAMP`, `RATE_RAMP`, `_MB`, `CHAT_SIZE_RAMP`) with:

```python
# ═══ Palette ════════════════════════════════════════════════════════════════
# Fixed (non-overridable) colors.
RESET = "\033[0m"
BG_LIGHTGRAY = "\033[47m"
LIGHTBLUE = "\033[38;5;75m"   # cornflower — chat-size ramp band 3 (distinct from BLUE)

# Overridable palette: NAME -> default SGR params (no "\033[" / "m" wrapper).
# [palette] overrides replace a value here; init_palette() rebuilds the globals
# and every ramp that derives from them. BLUE is 38;5;33 (true blue) because the
# bold-ANSI 1;34 reads purple on many terminals.
_PALETTE_DEFAULTS = {
    "GREY": "90", "WHITE": "1;97", "CYAN": "1;36", "GREEN": "1;32",
    "ORANGE": "38;5;208", "RED": "1;31", "YELLOW": "1;33", "MAGENTA": "1;35",
    "BLUE": "38;5;33",
    "ORANGE_BOLD": "1;38;5;208",      # high-severity context band
    "MAGENTA_DARK_BOLD": "1;38;5;90",  # dark/gothic — top context band (>=50%)
}

INF = float("inf")
_MB = 1024 * 1024


def _build_ramps():
    """(Re)build the color ramps + effort bars from the current color globals.
    Called by init_palette after the color globals are (re)assigned."""
    g = globals()
    g["CONTEXT_RAMP"] = [
        (10, WHITE), (15, CYAN), (20, BLUE), (25, GREEN),
        (30, YELLOW), (40, ORANGE_BOLD), (50, RED), (INF, MAGENTA_DARK_BOLD),
    ]
    g["RATE_RAMP"] = [(50, GREEN), (80, YELLOW), (INF, RED)]
    # Chat-transcript size bands (bytes). Mirrors the context bar's progression;
    # top two bands pinned: >=5 MB red, >=10 MB purple. Same "first ceil the value
    # is strictly below wins" rule as CONTEXT_RAMP.
    g["CHAT_SIZE_RAMP"] = [
        (512 * 1024, WHITE), (1 * _MB, CYAN), (2 * _MB, LIGHTBLUE), (3 * _MB, GREEN),
        (4 * _MB, YELLOW), (5 * _MB, ORANGE), (10 * _MB, RED), (INF, MAGENTA),
    ]
    # API-resolved effort levels, lowest -> highest; fill count = intensity (1..5),
    # each with a clear fixed color. `ultracode` is NOT a level (reports as xhigh)
    # and `auto` is a *setting*, not a level — neither belongs here.
    g["_EFFORT_BARS"] = {
        "low":    (CYAN,   f"{CYAN}▁{GREY}▃▄▆█"),
        "medium": (BLUE,   f"{BLUE}▁▃{GREY}▄▆█"),
        "high":   (YELLOW, f"{YELLOW}▁▃▄{GREY}▆█"),
        "xhigh":  (ORANGE, f"{ORANGE}▁▃▄▆{GREY}█"),
        "max":    (RED,    f"{RED}▁▃▄▆█"),
    }


def init_palette(overrides=None):
    """(Re)assign the overridable color globals from _PALETTE_DEFAULTS merged with
    `overrides` ({NAME: "sgr;params"}; unknown names ignored), then rebuild ramps.
    Call with no args to restore defaults. Idempotent."""
    merged = dict(_PALETTE_DEFAULTS)
    for name, val in (overrides or {}).items():
        if name in _PALETTE_DEFAULTS:
            merged[name] = str(val)
    g = globals()
    for name, params in merged.items():
        g[name] = f"\033[{params}m"
    _build_ramps()


# Build the colors + ramps once at import so module-level defaults are in force.
init_palette()
```

Note: the `_EFFORT_BARS` literal that currently lives lower in the file (in the "Segment builders" section) is now created by `_build_ramps()`. **Delete** the old standalone `_EFFORT_BARS = { ... }` definition (and keep the explanatory comment above it, trimmed, if desired). The `pick_color` function definition stays where it is — it only reads ramps at call time.

- [ ] **Step 4: Run the new tests and the full suite**

Run: `python3 -m unittest tests.test_status_line -v`
Expected: PASS. `TestEffortTable` and `TestPickColor` still pass because the rebuilt ramps/bars hold identical default values.

- [ ] **Step 5: Commit**

```bash
git add tools/status-line.py tests/test_status_line.py
git commit -m "refactor(status-line): palette behind init_palette() so overrides rebuild ramps (E4a)"
```

---

### Task 9: Apply `[palette]` overrides through config

**Files:**
- Modify: `tools/status-line.py`
- Test: `tests/test_status_line.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_status_line.py`:

```python
class TestPaletteFromConfig(unittest.TestCase):
    def tearDown(self):
        sl.init_palette()

    def _write(self, body):
        f = tempfile.NamedTemporaryFile("w", suffix=".toml", delete=False)
        f.write(body)
        f.close()
        self.addCleanup(os.unlink, f.name)
        return f.name

    def test_palette_parsed_into_config(self):
        path = self._write('[palette]\nBLUE = "1;34"\n')
        cfg = sl.load_config({"CC_AI_KIT_CONFIG": path, "HOME": "/h"})
        self.assertEqual(cfg.palette, {"BLUE": "1;34"})

    def test_unknown_palette_key_dropped(self):
        path = self._write('[palette]\nNOTACOLOR = "1;34"\n')
        cfg = sl.load_config({"CC_AI_KIT_CONFIG": path, "HOME": "/h"})
        self.assertEqual(cfg.palette, {})

    def test_main_applies_palette(self):
        import io
        from contextlib import redirect_stdout
        path = self._write('[palette]\nBLUE = "1;34"\n')
        raw = {"workspace": {"current_dir": "/tmp"}, "model": {"display_name": "Opus"},
               "context_window": {"used_percentage": 10}}
        env = {"HOME": "/tmp", "STATUSLINE_COLS": "200", "STATUSLINE_LINES": "50",
               "PATH": os.environ.get("PATH", ""),  # keep PATH so git in build_data resolves
               "CC_AI_KIT_CONFIG": path}
        buf = io.StringIO()
        with mock.patch.object(sys, "stdin", io.StringIO(json.dumps(raw))), \
             mock.patch.dict(os.environ, env, clear=True), redirect_stdout(buf):
            sl.main()
        # path segment is BLUE; overridden blue (1;34) must appear in the raw output.
        self.assertIn("\033[1;34m", buf.getvalue())
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python3 -m unittest tests.test_status_line.TestPaletteFromConfig -v`
Expected: FAIL — `cfg.palette` is `{}` (load_config does not read `[palette]` yet).

- [ ] **Step 3: Parse `[palette]` in `load_config`**

In `load_config`, replace:

```python
    layout = _resolve_layout(base.layout, raw.get("line"))
    return Config(segments=segments, layout=layout, palette={})
```
with:
```python
    layout = _resolve_layout(base.layout, raw.get("line"))
    palette = {}
    for k, v in (raw.get("palette") or {}).items():
        if k in _PALETTE_DEFAULTS:
            palette[k] = str(v)
        else:
            print(f"{GREY}status-line: unknown palette key '{k}'{RESET}", file=sys.stderr)
    return Config(segments=segments, layout=layout, palette=palette)
```

- [ ] **Step 4: Apply the palette in `main()`**

In `main()`, add the `init_palette` call right after resolving config:

```python
def main():
    cfg = load_config(os.environ)
    init_palette(cfg.palette)        # apply overrides + rebuild ramps before render
    try:
        raw = json.load(sys.stdin)
    except (ValueError, OSError):
        raw = {}
    data, cols, lines = build_data(raw, os.environ)
    print("\n".join(render(data, cols, lines, cfg)))
```

- [ ] **Step 5: Run the new tests and the full suite**

Run: `python3 -m unittest tests.test_status_line -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add tools/status-line.py tests/test_status_line.py
git commit -m "feat(status-line): apply [palette] overrides from config (E4a)"
```

---

## Phase 3 — Recipe, install copy, docs & introspection

### Task 10: Ship `statusline.toml.sample` + drift test

**Files:**
- Create: `tools/statusline.toml.sample`
- Test: `tests/test_status_line.py`

- [ ] **Step 1: Write the failing drift test**

Add to `tests/test_status_line.py`:

```python
class TestSampleRecipe(unittest.TestCase):
    SAMPLE = os.path.join(_HERE, "..", "tools", "statusline.toml.sample")

    def _uncomment(self):
        # Data lines are "# " prefixed; prose is "## " prefixed. Reconstruct the
        # intended config by taking the single-hash data lines, stripping "# ".
        with open(self.SAMPLE) as f:
            lines = f.read().splitlines()
        return "\n".join(ln[2:] for ln in lines if ln.startswith("# "))

    def test_file_exists(self):
        self.assertTrue(os.path.isfile(self.SAMPLE))

    def test_as_shipped_is_all_commented_noop(self):
        # No active (uncommented) TOML keys: every non-blank line is a comment.
        with open(self.SAMPLE) as f:
            for ln in f:
                s = ln.strip()
                if s:
                    self.assertTrue(s.startswith("#"), f"active line in sample: {ln!r}")

    def test_uncommented_matches_internal_defaults(self):
        parsed = tomllib.loads(self._uncomment())
        self.assertEqual(parsed.get("version"), 1)
        self.assertEqual(parsed.get("segments"), dict(sl.SEGMENTS))
        want = [{"min_rows": ln.min_rows, "segments": ln.segments} for ln in sl.LAYOUT]
        self.assertEqual(parsed.get("line"), want)
```

- [ ] **Step 2: Add `import tomllib` to the test file**

At the top of `tests/test_status_line.py`, in the import block (after `import sys`), add:

```python
import tomllib
```

Note: `tomllib` is stdlib in Python 3.11+, which is the minimum required version for TOML support (same guard as in `tools/status-line.py`). The test calls `tomllib.loads(...)` directly in `test_uncommented_matches_internal_defaults`, so the import must be top-level in the test file — it is not sufficient that `status_line` imports it internally.

- [ ] **Step 3: Run the new test class to verify it fails**

Run: `python3 -m unittest tests.test_status_line.TestSampleRecipe -v`
Expected: FAIL — `test_file_exists` fails (sample file not created yet).

- [ ] **Step 4: Create the sample recipe**

Create `tools/statusline.toml.sample` with EXACTLY this content (prose = `## `, data = `# `; uncommenting the `# ` lines reproduces the internal defaults):

```toml
## ai-kit status line — configuration recipe.
## Copy to ~/.config/ai-kit/statusline.toml (the installer does this if the file
## is absent; it never overwrites an existing one). As shipped EVERY line below is
## commented, so this file is a NO-OP and the built-in defaults apply. Uncomment
## only what you want to change.
##
## Precedence (low -> high): built-in defaults < this file < env (CC_AI_KIT_*).

# version = 1

## ─── [segments] ──────────────────────────────────────────────────────────────
## Show/hide individual segments. Uncomment a single line to flip just that one;
## every other segment keeps its built-in default (this block MERGES over the
## defaults). The values below are the current defaults.
# [segments]
# path = true
# branch = true
# dirty = true
# todo = true
# model = true
# time_ago = true
# clock = true
# effort = true
# lines = true
# cost = false
# total_time = true
# api_time = true
# dimensions = true
# context = true
# chat_size = true
# memory = true
# rate_limits = true

## ─── [[line]] ────────────────────────────────────────────────────────────────
## Full layout override. ALL-OR-NOTHING: if you uncomment ANY [[line]] block you
## must uncomment them ALL (a partial layout would silently drop the omitted
## segments). `min_rows` gates a row by terminal height; segment order is
## left -> right priority (leftmost kept first when space is tight). The blocks
## below are the current default layout.
# [[line]]
# min_rows = 0
# segments = ["path", "branch", "dirty", "todo"]
# [[line]]
# min_rows = 20
# segments = ["model", "time_ago", "clock", "effort", "lines", "cost", "total_time", "api_time"]
# [[line]]
# min_rows = 30
# segments = ["dimensions", "context", "chat_size", "memory", "rate_limits"]

## ─── [palette] ───────────────────────────────────────────────────────────────
## Override named colors with raw ANSI SGR params (no "\033[" / "m" wrapper).
## Overridable names: GREY WHITE CYAN GREEN ORANGE RED YELLOW MAGENTA BLUE
## ORANGE_BOLD MAGENTA_DARK_BOLD. Example — force a truer blue on a screen where
## the default reads purple:
# [palette]
# BLUE = "38;5;33"
```

- [ ] **Step 5: Run the drift test and full suite**

Run: `python3 -m unittest tests.test_status_line.TestSampleRecipe -v`
Expected: PASS — `version`, `segments`, and `line` parsed from the uncommented `# ` lines equal the internal defaults. (The `[palette]` example is not asserted against defaults — it is an illustrative override, and `_uncomment()` includes it but the test only checks `version`/`segments`/`line`.)

Then run the full suite to confirm no regressions:

Run: `python3 -m unittest tests.test_status_line -v`
Expected: PASS — all tests green.

> Note: the `[palette]` example line `# BLUE = "38;5;33"` IS a `# ` data line, so `_uncomment()` will include a `[palette]` table with `BLUE`. That is fine — the drift test only asserts `version`/`segments`/`line`, and `38;5;33` is the real default BLUE, so the example is also non-drifting by construction. Do not assert on `parsed["palette"]`.

- [ ] **Step 6: Commit**

```bash
git add tools/statusline.toml.sample tests/test_status_line.py
git commit -m "feat(status-line): ship fully-commented statusline.toml.sample + drift test (E4a)"
```

---

### Task 11: Installer copies the sample when absent

**Files:**
- Modify: `tools/install.sh`
- Test: `tests/test_install.sh`

- [ ] **Step 1: Add the failing installer assertions**

In `tests/test_install.sh`, after the fixture builds `status-line.py` (the line `printf 'print("sl")\n' > "$FIXTURE/tools/status-line.py"`), add the sample to the fixture:

```bash
printf '# version = 1\n' > "$FIXTURE/tools/statusline.toml.sample"
```

Then, after the section `# --- 1. first install ---` block (after the existing `check "statusLine points at fixture" ...`), add:

```bash
CFG="$WORK/.config/ai-kit/statusline.toml"
check "config sample copied when absent" bash -c '[ -f "'"$CFG"'" ]'
check "copied config equals the sample" \
  bash -c 'diff -q "'"$FIXTURE"'/tools/statusline.toml.sample" "'"$CFG"'" >/dev/null'

# pre-existing config must NOT be overwritten
printf '# user edited\n' > "$CFG"
run_install
check "existing config left untouched" \
  bash -c 'grep -q "user edited" "'"$CFG"'"'
```

(The throwaway env sets `HOME="$WORK"` and uses `env -i`, so `XDG_CONFIG_HOME` is unset → the config resolves to `$WORK/.config/ai-kit/statusline.toml`.)

- [ ] **Step 2: Run it to verify it fails**

Run: `bash tests/test_install.sh`
Expected: FAIL — `config sample copied when absent` fails (installer does not copy yet).

- [ ] **Step 3: Add `install_statusline_config()` to `install.sh`**

In `tools/install.sh`, add this function immediately after the `update_statusline() { ... }` function (before the `# --- uninstall` banner):

```bash
install_statusline_config() {
  local sample="$INSTALL_DIR/tools/statusline.toml.sample"
  local cfg_dir="${XDG_CONFIG_HOME:-$HOME/.config}/ai-kit"
  local cfg="$cfg_dir/statusline.toml"
  [ -f "$sample" ] || return 0
  if [ -f "$cfg" ]; then
    ok "statusline config exists, leaving as-is: $cfg"
    return 0
  fi
  if [ "$DRY_RUN" = 1 ]; then
    printf '%swould%s copy %s -> %s\n' "$C_DIM" "$C_RESET" "$sample" "$cfg"
    return 0
  fi
  run mkdir -p "$cfg_dir"
  run cp "$sample" "$cfg"
  ok "statusline config -> $cfg (commented defaults; edit to customize)"
}
```

- [ ] **Step 4: Call it from `main()`**

In `tools/install.sh`, in `main()`, add the call right after `update_statusline`:

```bash
  update_statusline
  install_statusline_config
```

- [ ] **Step 5: Run the installer test and shellcheck**

Run: `bash tests/test_install.sh`
Expected: PASS (`N passed, 0 failed`).
Run: `shellcheck tools/install.sh`
Expected: no warnings.

- [ ] **Step 6: Commit**

```bash
git add tools/install.sh tests/test_install.sh
git commit -m "feat(install): copy statusline.toml.sample to config path when absent (E4a)"
```

---

### Task 12: CLI introspection — `--print-config` / `--check` / `--help`

**Files:**
- Modify: `tools/status-line.py`
- Test: `tests/test_status_line.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_status_line.py`:

```python
class TestCLI(unittest.TestCase):
    def _write(self, body):
        f = tempfile.NamedTemporaryFile("w", suffix=".toml", delete=False)
        f.write(body)
        f.close()
        self.addCleanup(os.unlink, f.name)
        return f.name

    def test_parse_args_defaults(self):
        ns = sl.parse_args([])
        self.assertFalse(ns.print_config)
        self.assertIs(ns.check, sl._NO_CHECK)

    def test_print_config_emits_resolved_json(self):
        cfg = sl.Config(segments={"path": True}, layout=[sl.Line(0, ["path"])],
                        palette={"BLUE": "1;34"})
        out = sl.cmd_print_config(cfg)
        parsed = json.loads(out)
        self.assertEqual(parsed["segments"], {"path": True})
        self.assertEqual(parsed["layout"], [{"min_rows": 0, "segments": ["path"]}])
        self.assertEqual(parsed["palette"], {"BLUE": "1;34"})

    def test_check_valid_returns_zero(self):
        path = self._write('[segments]\ncost = true\n')
        self.assertEqual(sl.cmd_check(path, {"HOME": "/h"}), 0)

    def test_check_unknown_segment_returns_one(self):
        path = self._write('[segments]\nbogus = true\n')
        self.assertEqual(sl.cmd_check(path, {"HOME": "/h"}), 1)

    def test_check_bad_layout_ref_returns_one(self):
        path = self._write('[[line]]\nsegments = ["nope"]\n')
        self.assertEqual(sl.cmd_check(path, {"HOME": "/h"}), 1)

    def test_check_malformed_returns_one(self):
        path = self._write('= = not toml')
        self.assertEqual(sl.cmd_check(path, {"HOME": "/h"}), 1)
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python3 -m unittest tests.test_status_line.TestCLI -v`
Expected: FAIL with `AttributeError: ... has no attribute 'parse_args'`

- [ ] **Step 3: Add the `argparse` import**

In the import block of `tools/status-line.py`, add (alphabetically near the top):

```python
import argparse
```

- [ ] **Step 4: Implement the CLI helpers**

Add a new section just above `def main():`:

```python
# ═══ CLI introspection ═══════════════════════════════════════════════════════
_NO_CHECK = object()   # sentinel: --check flag absent (vs. present with no FILE)

_ENV_HELP = """\
Environment variables:
  CC_AI_KIT_CONFIG         path to the TOML config file
  CC_AI_KIT_SEGMENT_<KEY>  per-segment bool toggle; KEY is the upper-cased
                           segment name (PATH, MODEL, COST, CONTEXT, ...).
                           true:  1 true t y yes on    false: 0 false f n no off

Config precedence (low -> high): built-in defaults < TOML file < env."""


def cmd_print_config(cfg):
    """Resolved config as pretty JSON (no rendering)."""
    return json.dumps({
        "segments": cfg.segments,
        "layout": [{"min_rows": ln.min_rows, "segments": ln.segments}
                   for ln in cfg.layout],
        "palette": cfg.palette,
    }, indent=2)


def validate_config_file(path, env):
    """Return a list of human-readable error strings for the config at path
    (empty list = valid). Checks: parseability, unknown segment keys, unknown
    palette keys, and [[line]] segments that are not real builders."""
    if tomllib is None:
        return ["tomllib unavailable (Python < 3.11): cannot validate"]
    try:
        with open(path, "rb") as f:
            raw = tomllib.load(f)
    except FileNotFoundError:
        return [f"{path}: no such file"]
    except (OSError, tomllib.TOMLDecodeError) as e:
        return [f"{path}: {e}"]
    errors = []
    defaults = default_config()
    for k in (raw.get("segments") or {}):
        if k not in defaults.segments:
            errors.append(f"unknown segment key: {k}")
    for k in (raw.get("palette") or {}):
        if k not in _PALETTE_DEFAULTS:
            errors.append(f"unknown palette key: {k}")
    for i, line in enumerate(raw.get("line") or []):
        for seg in line.get("segments", []):
            if seg not in BUILDERS:
                errors.append(f"line[{i}] references unknown segment: {seg}")
    return errors


def cmd_check(path, env):
    """Validate a config file; print result. Return process exit code (0/1)."""
    path = path or config_path(env)
    errors = validate_config_file(path, env)
    if errors:
        for e in errors:
            print(f"{path}: {e}", file=sys.stderr)
        return 1
    print(f"{path}: OK")
    return 0


def parse_args(argv):
    p = argparse.ArgumentParser(
        prog="status-line.py",
        description="Claude Code status line. With no flags, reads the status "
                    "JSON on stdin and renders up to three ANSI lines.",
        epilog=_ENV_HELP,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--print-config", action="store_true",
                   help="resolve config (defaults < file < env), print it as "
                        "JSON, and exit (does not read stdin)")
    p.add_argument("--check", nargs="?", const=None, default=_NO_CHECK,
                   metavar="FILE",
                   help="validate a config file (default: the resolved path) "
                        "and exit non-zero if invalid")
    return p.parse_args(argv)
```

- [ ] **Step 5: Wire the flags into `main()`**

Replace `main()` with:

```python
def main():
    args = parse_args(sys.argv[1:])
    if args.check is not _NO_CHECK:
        sys.exit(cmd_check(args.check, os.environ))
    cfg = load_config(os.environ)
    init_palette(cfg.palette)
    if args.print_config:
        print(cmd_print_config(cfg))
        return
    try:
        raw = json.load(sys.stdin)
    except (ValueError, OSError):
        raw = {}
    data, cols, lines = build_data(raw, os.environ)
    print("\n".join(render(data, cols, lines, cfg)))
```

- [ ] **Step 6: Run the new tests + full suite + manual smoke**

Run: `python3 -m unittest tests.test_status_line -v`
Expected: PASS (whole suite).
Run: `echo '{}' | python3 tools/status-line.py --print-config`
Expected: JSON with `segments`, `layout`, `palette` keys; no rendered status line.
Run: `python3 tools/status-line.py --help`
Expected: usage text ending with the `Environment variables:` block.
Run: `printf '{"workspace":{"current_dir":"/tmp"},"model":{"display_name":"Opus"},"context_window":{"used_percentage":10}}' | STATUSLINE_COLS=200 STATUSLINE_LINES=50 python3 tools/status-line.py`
Expected: a normally-rendered status line (no-arg stdin mode unchanged).

- [ ] **Step 7: Commit**

```bash
git add tools/status-line.py tests/test_status_line.py
git commit -m "feat(status-line): --print-config / --check / --help introspection (E4a)"
```

---

### Task 13: Document config in README

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Find the status-line section anchor**

Run: `grep -n "status-line\|statusline\|status line" README.md`
Expected: lines around 21–22 / 43 / 86 reference the status line (the bullet about `statusLine` in `~/.claude/settings.json`).

- [ ] **Step 2: Add a "Status-line configuration" section**

Insert this section after the existing status-line install bullet (after line ~43's `5. **statusline** — ...`). Use real content:

````markdown
### Status-line configuration

The status line works with zero config. To customize it, edit
`~/.config/ai-kit/statusline.toml` (the installer drops a fully-commented
starter there if you don't have one — as shipped it changes nothing). Settings
resolve **built-in defaults < this file < environment variables**.

**Toggle segments** — in the file:

```toml
[segments]
cost   = true     # show the 🪙 cost segment (off by default)
memory = false    # hide the 🧮 process-memory segment
```

…or per-session via env (wins over the file):

```sh
CC_AI_KIT_SEGMENT_COST=1     # 1 true t y yes on  /  0 false f n no off
```

**Reorder / move rows** — uncomment **all** `[[line]]` blocks and edit (layout
is all-or-nothing; a partial layout would silently drop segments):

```toml
[[line]]
min_rows = 0
segments = ["path", "branch", "dirty", "todo"]
```

**Fix a color** (e.g. a blue that reads purple) with raw ANSI SGR params:

```toml
[palette]
BLUE = "38;5;33"
```

**Inspect & validate:**

```sh
python3 tools/status-line.py --print-config   # resolved config as JSON
python3 tools/status-line.py --check          # validate the config file
python3 tools/status-line.py --help           # full env-var list
```

Environment variables: `CC_AI_KIT_CONFIG` (config path),
`CC_AI_KIT_SEGMENT_<KEY>` (per-segment toggle). Requires Python 3.11+ for the
TOML file; on older Python the file is ignored and only env toggles apply.
````

- [ ] **Step 3: Verify the doc renders and references are accurate**

Run: `grep -n "CC_AI_KIT_SEGMENT\|statusline.toml\|--print-config" README.md`
Expected: the new section is present with all three references.

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs(status-line): document config file, env vars, and precedence (E4a)"
```

---

## Phase Wrap-up

- [ ] **Run the complete suite one final time**

Run: `python3 -m unittest tests.test_status_line -v && bash tests/test_install.sh && shellcheck tools/install.sh`
Expected: all Python tests pass, installer test reports `0 failed`, shellcheck clean.

- [ ] **Compact commits by logical unit before closing the phase** (per working agreement)

Review `git log main..feat/e4a-statusline-config`. The per-task commits are already grouped by logical unit (config core, layout, palette, recipe, install, CLI, docs). If any task produced incidental fix-up commits, squash them into their owning logical commit. Do **not** squash across logical units.

- [ ] **Acceptance cross-check against the PRD** (`statusline-config-extensibility-v1.0-prd.md` → Acceptance Criteria)

Confirm each functional criterion has a passing test or a verified manual check:
`CC_AI_KIT_SEGMENT_COST` precedence (Task 4/6); file `[segments]`+`[[line]]` (Tasks 4/7); `[palette]` override + unknown-key warning (Task 9); `--print-config`/`--check`/no-arg stdin (Task 12); malformed-config fallback (Task 3); `SEGMENTS`/`LAYOUT` at top + unchanged rendering (Task 1); sample fully-commented no-op + drift test (Task 10); installer copy-if-absent never overwriting (Task 11).

---

## Notes for the implementer

- **Stdlib only.** Do not add third-party packages. `tomllib`/`argparse`/`json`/`os`/`sys` are all stdlib.
- **Back-compat is load-bearing.** `pack_line`/`render` keep `cfg=None` defaults; never make `cfg` required — existing tests and any external callers depend on the old signatures.
- **`PINNED` stays a module global** (`{"path", "context"}`) — it is not user-configurable in E4a.
- **Palette tests must restore defaults** with `sl.init_palette()` in `tearDown`, because `init_palette` mutates module globals (the same module-global-mutation pattern the existing `SEGMENTS` tests use with try/finally).
- **External drop-in segments are E4b** — do not implement `[external]`, segment discovery, or subprocess execution here. The seam (synthetic builders inserted into `cfg.layout`) is already clean.
