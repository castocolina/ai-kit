# E3 — Status-Line Bug Fixes + Cross-Platform Clarity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix seven status-line defects (effort level + auto setting, blue→purple, wezterm/macOS memory, macOS dims, chat-size color) and make the two platform-specific spots genuinely cross-platform and clear.

**Architecture:** All changes live in `tools/status-line.py`, expressed as module-level constants/ramps at single named lookup points (mirroring `CONTEXT_RAMP` + `pick_color`) so E4 can later swap their source to config. The two OS-specific concerns — process RSS and terminal size — become clear helpers selected by capability probe (`/proc` present?) with an ordered fallback chain.

**Tech Stack:** Python 3 stdlib only (`os`, `subprocess`, `re`, `unicodedata`), `unittest` (run via `python3 -m unittest`), `unittest.mock` for platform-branch tests.

**Spec:** `docs/superpowers/specs/2026-06-18-e3-statusline-fixes-crossplatform-design.md`

**Test conventions (already in `tests/test_status_line.py`):** `sl = load_module()` loads `tools/status-line.py`; `_data(**over)` builds the segment data dict; `strip(s)` removes ANSI; assertions compare against `sl.<CONSTANT>` (so changing a color's value is safe). Run a single class with `python3 -m unittest tests.test_status_line.<Class> -v`.

---

## File Structure

| File | Responsibility | Action |
|------|----------------|--------|
| `tools/status-line.py` | All fixes: palette constants, `CHAT_SIZE_RAMP`, `resolve_effort` + `effort_setting_is_auto`, cross-platform `proc_rss_bytes` + `terminal_size` | Modify |
| `tests/test_status_line.py` | New test classes per cluster (append) | Modify |
| `docs/prds/000-ai-kit-overhaul-requirements.md` | Remove "E4 first"; mark E3 progress | Modify |

---

### Task 1: Blue that reads blue (FR-3.3)

**Files:**
- Modify: `tools/status-line.py:55` (the `BLUE = …` line, in the Palette block)
- Test: `tests/test_status_line.py`

- [ ] **Step 1: Write the failing test** — append to `tests/test_status_line.py`:

```python
class TestBlueFix(unittest.TestCase):
    def test_blue_is_256color_true_blue(self):
        # 1;34 bold-ANSI-blue reads purple on many terminals; use 256-color blue.
        self.assertEqual(sl.BLUE, "\033[38;5;33m")

    def test_lightblue_defined_for_chat_ramp(self):
        self.assertEqual(sl.LIGHTBLUE, "\033[38;5;75m")

    def test_path_emits_true_blue_not_bold_ansi(self):
        out = sl.seg_path(_data(), 80)
        self.assertIn("38;5;33", out)
        self.assertNotIn("\033[1;34m", out)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_status_line.TestBlueFix -v`
Expected: FAIL — `AssertionError` on `sl.BLUE` and `AttributeError: module has no attribute 'LIGHTBLUE'`.

- [ ] **Step 3: Edit the palette** — in `tools/status-line.py`, replace the single line

```python
BLUE = "\033[1;34m"
```

with

```python
BLUE = "\033[38;5;33m"        # true blue — 1;34 bold-ANSI-blue reads purple on many terminals
LIGHTBLUE = "\033[38;5;75m"   # cornflower — chat-size ramp band 3 (distinct from BLUE)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_status_line.TestBlueFix -v`
Expected: PASS. Also run the existing suite to confirm no regression (the context-ramp test compares against `sl.BLUE` by identity, so it still passes):
Run: `python3 -m unittest tests.test_status_line -v`
Expected: OK.

- [ ] **Step 5: Commit**

```bash
git add tools/status-line.py tests/test_status_line.py
git commit -m "fix(status-line): true-blue SGR so default no longer reads purple (FR-3.3)"
```

---

### Task 2: chat-size colored ramp (FR-3.7)

**Files:**
- Modify: `tools/status-line.py` — add `CHAT_SIZE_RAMP` after `RATE_RAMP` (~line 69); color `seg_chat_size` (~line 340)
- Test: `tests/test_status_line.py`

- [ ] **Step 1: Write the failing test** — append:

```python
class TestChatSizeRamp(unittest.TestCase):
    KB = 1024
    MB = 1024 * 1024

    def test_ramp_bands(self):
        KB, MB = self.KB, self.MB
        cases = [
            (400 * KB, sl.WHITE), (512 * KB, sl.CYAN), (900 * KB, sl.CYAN),
            (1 * MB, sl.LIGHTBLUE), (1 * MB + 1, sl.LIGHTBLUE),
            (2 * MB, sl.GREEN), (3 * MB, sl.YELLOW), (4 * MB, sl.ORANGE),
            (5 * MB, sl.RED), (5 * MB + 1, sl.RED), (9 * MB, sl.RED),
            (10 * MB, sl.MAGENTA), (20 * MB, sl.MAGENTA),
        ]
        for n, want in cases:
            self.assertEqual(sl.pick_color(n, sl.CHAT_SIZE_RAMP), want, n)

    def test_seg_chat_size_colors_the_size(self):
        out = sl.seg_chat_size(_data(chat_bytes=6 * self.MB), 40)
        self.assertIn("💾", out)
        self.assertIn(sl.RED, out)       # 6 MB -> red band

    def test_seg_chat_size_none_when_no_bytes(self):
        self.assertIsNone(sl.seg_chat_size(_data(chat_bytes=None), 40))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_status_line.TestChatSizeRamp -v`
Expected: FAIL — `AttributeError: module has no attribute 'CHAT_SIZE_RAMP'`.

- [ ] **Step 3: Add the ramp** — in `tools/status-line.py`, directly after the `RATE_RAMP = …` line, add:

```python
_MB = 1024 * 1024
# Chat-transcript size bands (bytes). Mirrors the context bar's color progression;
# top two bands are pinned: >=5 MB red, >=10 MB purple. Same "first ceil the value
# is strictly below wins" rule as CONTEXT_RAMP, so exactly 5 MB -> red, 10 MB -> purple.
CHAT_SIZE_RAMP = [
    (512 * 1024, WHITE), (1 * _MB, CYAN), (2 * _MB, LIGHTBLUE), (3 * _MB, GREEN),
    (4 * _MB, YELLOW), (5 * _MB, ORANGE), (10 * _MB, RED), (INF, MAGENTA),
]
```

- [ ] **Step 4: Color the segment** — replace the body of `seg_chat_size`:

```python
def seg_chat_size(data, avail):
    n = data.get("chat_bytes")
    if n is None:
        return None
    color = pick_color(n, CHAT_SIZE_RAMP)
    return _first_fitting([f"💾 {color}{fmt_bytes(n)}{RESET}"], avail)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python3 -m unittest tests.test_status_line.TestChatSizeRamp -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add tools/status-line.py tests/test_status_line.py
git commit -m "feat(status-line): threshold-colored chat-size ramp (FR-3.7)"
```

---

### Task 3: effort level table + auto annotation render (FR-3.2)

The resolved level always renders in its own fixed color; the **auto setting** (passed in
as `data["effort_auto"]`, wired up in Task 4) only adds a degrading `[auto]` → `*` →
dropped annotation. No rainbow — `auto` is a *setting*, not a resolved level.

**Files:**
- Modify: `tools/status-line.py` — `_EFFORT_BARS` table (low/medium/high/xhigh/max only); rework `seg_effort`
- Test: `tests/test_status_line.py`

- [ ] **Step 1: Write the failing test** — append:

```python
class TestEffortAutoSetting(unittest.TestCase):
    def test_auto_appends_bracket_when_room(self):
        out = strip(sl.seg_effort(_data(effort="high", effort_auto=True), 40))
        self.assertIn("high", out); self.assertIn("[auto]", out)

    def test_resolved_level_keeps_its_color_in_auto(self):
        out = sl.seg_effort(_data(effort="high", effort_auto=True), 40)
        self.assertIn(f"{sl.YELLOW}high", out)

    def test_auto_compacts_to_asterisk_when_tight(self):
        out = strip(sl.seg_effort(_data(effort="medium", effort_auto=True), 18))
        self.assertIn("medium*", out); self.assertNotIn("[auto]", out)

    def test_non_auto_has_no_annotation(self):
        out = strip(sl.seg_effort(_data(effort="high", effort_auto=False), 40))
        self.assertIn("high", out); self.assertNotIn("[auto]", out); self.assertNotIn("*", out)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_status_line.TestEffortAutoSetting -v`
Expected: FAIL — `seg_effort` has no auto-annotation behavior yet.

- [ ] **Step 3: Set the level table** — `_EFFORT_BARS` carries only the five resolved levels
(no `auto`, no `ultracode`), each with a clear fixed color and fill count = intensity:

```python
# API-resolved effort levels, lowest -> highest; fill count = intensity (1..5), each
# with a clear fixed color. `ultracode` is NOT a level (it reports as xhigh + standing
# multi-agent permission), and `auto` is a *setting*, not a resolved level — neither
# belongs here. The auto setting is surfaced as a "[auto]" suffix in seg_effort.
_EFFORT_BARS = {
    "low":    (CYAN,   f"{CYAN}▁{GREY}▃▄▆█"),
    "medium": (BLUE,   f"{BLUE}▁▃{GREY}▄▆█"),
    "high":   (YELLOW, f"{YELLOW}▁▃▄{GREY}▆█"),
    "xhigh":  (ORANGE, f"{ORANGE}▁▃▄▆{GREY}█"),
    "max":    (RED,    f"{RED}▁▃▄▆█"),
}
```

- [ ] **Step 4: Rework `seg_effort`** — the resolved level always renders in its fixed
color; only `effort_auto` adds the degrading annotation:

```python
def seg_effort(data, avail):
    level = data.get("effort", "")
    if not level:
        return None
    color, bar = _EFFORT_BARS.get(level.lower(), ("", f"{GREY}▁▃▄▆█"))
    word = f"{color}{level}{RESET}"
    bars = f"🧠 {bar}{RESET}"
    if data.get("effort_auto"):
        # effortLevel is unset/auto in settings: flag the resolved level as
        # auto-chosen. The flag degrades [auto] -> * -> dropped as space tightens.
        variants = [f"{bars} {word} {GREY}[auto]{RESET}",
                    f"{bars} {color}{level}*{RESET}",
                    f"{bars} {word}",
                    bars]
    else:
        variants = [f"{bars} {word}", bars]
    return _first_fitting(variants, avail)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python3 -m unittest tests.test_status_line.TestEffortAutoSetting -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add tools/status-line.py tests/test_status_line.py
git commit -m "feat(status-line): annotate auto-chosen effort level (FR-3.2)"
```

---

### Task 4: effort level resolution + auto-setting detection (FR-3.1)

`resolve_effort` normalizes the always-present resolved level from the input JSON;
`effort_setting_is_auto` reads the on-disk settings chain to decide whether that level was
auto-chosen. The input JSON never carries `"auto"` — that lives only in settings.

**Files:**
- Modify: `tools/status-line.py` — `resolve_effort` docstring; add `effort_setting_is_auto(work_dir, home)`; wire `effort_auto` into `build_data`
- Test: `tests/test_status_line.py`

- [ ] **Step 1: Write the failing test** — append (needs `import json, tempfile, shutil` at the top):

```python
class TestEffortSettingAuto(unittest.TestCase):
    def _dirs(self):
        proj = tempfile.mkdtemp(); home = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, proj, ignore_errors=True)
        self.addCleanup(shutil.rmtree, home, ignore_errors=True)
        return proj, home

    def _write(self, root, name, obj):
        path = os.path.join(root, ".claude", name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f: json.dump(obj, f)

    def test_absent_everywhere_is_auto(self):
        proj, home = self._dirs(); self.assertTrue(sl.effort_setting_is_auto(proj, home))

    def test_explicit_user_level_is_not_auto(self):
        proj, home = self._dirs(); self._write(home, "settings.json", {"effortLevel": "high"})
        self.assertFalse(sl.effort_setting_is_auto(proj, home))

    def test_literal_auto_value_is_auto(self):
        proj, home = self._dirs(); self._write(home, "settings.json", {"effortLevel": "auto"})
        self.assertTrue(sl.effort_setting_is_auto(proj, home))

    def test_project_setting_wins_over_user(self):
        proj, home = self._dirs(); self._write(home, "settings.json", {"effortLevel": "auto"})
        self._write(proj, "settings.json", {"effortLevel": "high"})
        self.assertFalse(sl.effort_setting_is_auto(proj, home))

    def test_keyless_file_falls_through_to_next(self):
        proj, home = self._dirs(); self._write(proj, "settings.local.json", {"model": "opus"})
        self._write(home, "settings.json", {"effortLevel": "max"})
        self.assertFalse(sl.effort_setting_is_auto(proj, home))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_status_line.TestEffortSettingAuto -v`
Expected: FAIL — `AttributeError: module has no attribute 'effort_setting_is_auto'`.

- [ ] **Step 3: Add the detector** — keep `resolve_effort` as the normalizer (input JSON
never carries `"auto"`), and add `effort_setting_is_auto` reading the settings chain:

```python
def resolve_effort(raw, env):
    """The *resolved* effort level (low..max) as a normalized lowercase string, or "".

    Source priority: raw["effort"]["level"] > CLAUDE_EFFORT env. It is never "auto" —
    auto is a *setting*, detected separately from disk by effort_setting_is_auto.
    """
    level = ((raw.get("effort") or {}).get("level") or env.get("CLAUDE_EFFORT", ""))
    return level.strip().lower()


def effort_setting_is_auto(work_dir, home):
    """True when the effort *setting* is auto — i.e. `effortLevel` is absent (or
    literally "auto") across the settings chain.

    Precedence high->low: <repo>/.claude/settings.local.json, then
    <repo>/.claude/settings.json, then ~/.claude/settings.json. The first file that
    defines `effortLevel` decides; if none does, the setting is auto.
    """
    for path in (os.path.join(work_dir, ".claude", "settings.local.json"),
                 os.path.join(work_dir, ".claude", "settings.json"),
                 os.path.join(home, ".claude", "settings.json")):
        try:
            with open(path) as f:
                cfg = json.load(f)
        except (OSError, ValueError):
            continue
        if isinstance(cfg, dict) and "effortLevel" in cfg:
            return str(cfg["effortLevel"]).strip().lower() == "auto"
    return True
```

- [ ] **Step 4: Wire it into `build_data`** — after the `effort = resolve_effort(raw, env)`
line, add the auto-setting lookup, and add `"effort_auto"` to the data dict:

```python
    effort = resolve_effort(raw, env)
    effort_auto = effort_setting_is_auto(work_dir, env.get("HOME", ""))
    # ... in the data dict, next to "effort": effort,
    "effort_auto": effort_auto,
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python3 -m unittest tests.test_status_line.TestEffortSettingAuto -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add tools/status-line.py tests/test_status_line.py
git commit -m "fix(status-line): detect auto effort setting from settings chain (FR-3.1)"
```

---

### Task 5: Cross-platform process RSS — Linux + "only on match" fix (FR-3.4)

**Files:**
- Modify: `tools/status-line.py` — replace `proc_rss_bytes` (~lines 476-500) with split `/proc` reader helpers + a unified walker
- Test: `tests/test_status_line.py`

- [ ] **Step 1: Write the failing test** — append (add `from unittest import mock` near the top imports of the test file if not present):

```python
class TestProcRssLinux(unittest.TestCase):
    def test_returns_none_when_no_claude_ancestor(self):
        # the wezterm bug: walk finds no `claude`, must return None (not a stray RSS)
        comm = {10: "zsh", 11: "wezterm-gui", 1: "systemd"}
        ppid = {10: 11, 11: 1, 1: 0}
        with mock.patch.object(sl.os.path, "isdir", return_value=True), \
             mock.patch.object(sl.os, "getppid", return_value=10), \
             mock.patch.object(sl, "_comm_via_proc", side_effect=comm.get), \
             mock.patch.object(sl, "_ppid_via_proc", side_effect=ppid.get), \
             mock.patch.object(sl, "_rss_kb_via_proc", side_effect=lambda p: 5000):
            self.assertIsNone(sl.proc_rss_bytes())

    def test_returns_rss_when_claude_found(self):
        comm = {10: "zsh", 11: "claude", 1: "systemd"}
        ppid = {10: 11, 11: 1, 1: 0}
        with mock.patch.object(sl.os.path, "isdir", return_value=True), \
             mock.patch.object(sl.os, "getppid", return_value=10), \
             mock.patch.object(sl, "_comm_via_proc", side_effect=comm.get), \
             mock.patch.object(sl, "_ppid_via_proc", side_effect=ppid.get), \
             mock.patch.object(sl, "_rss_kb_via_proc",
                               side_effect=lambda p: 204800 if p == 11 else 5000):
            self.assertEqual(sl.proc_rss_bytes(), 204800 * 1024)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_status_line.TestProcRssLinux -v`
Expected: FAIL — `AttributeError: module has no attribute '_comm_via_proc'`.

- [ ] **Step 3: Replace `proc_rss_bytes`** — replace the entire existing `proc_rss_bytes` function with these `/proc` readers plus the unified walker (the `_via_ps` readers are added in Task 6; reference them now so the selector is complete):

```python
# ── Process RSS (cross-platform) ──────────────────────────────────────────────
# Two capability-probed backends read the same three facts about a pid: its command
# name, its parent pid, and its resident memory. Linux uses /proc; everything else
# falls back to `ps`. proc_rss_bytes walks the parent chain and returns RSS ONLY when
# it actually finds `claude` — otherwise None, so the segment hides instead of
# reporting a stray process (the wezterm <10mb bug).
def _comm_via_proc(pid):
    try:
        return open(f"/proc/{pid}/comm").read().strip()
    except OSError:
        return None


def _ppid_via_proc(pid):
    try:
        return int(open(f"/proc/{pid}/stat").read().split()[3])
    except (OSError, IndexError, ValueError):
        return None


def _rss_kb_via_proc(pid):
    try:
        for line in open(f"/proc/{pid}/status"):
            if line.startswith("VmRSS:"):
                return int(line.split()[1])
    except OSError:
        return None
    return None


def proc_rss_bytes():
    """Resident memory (bytes) of the ancestor `claude` process, or None.

    Cross-platform via a capability probe: Linux /proc, else `ps`. Walk up the parent
    chain (bounded) and return RSS only on a `claude` match."""
    use_proc = os.path.isdir("/proc")
    comm_of = _comm_via_proc if use_proc else _comm_via_ps
    ppid_of = _ppid_via_proc if use_proc else _ppid_via_ps
    rss_kb_of = _rss_kb_via_proc if use_proc else _rss_kb_via_ps

    pid = os.getppid()
    for _ in range(8):
        name = comm_of(pid)
        if name is None:
            return None
        if os.path.basename(name) == "claude":
            kb = rss_kb_of(pid)
            return kb * 1024 if kb is not None else None
        parent = ppid_of(pid)
        if parent is None or parent in (0, pid):
            return None
        pid = parent
    return None
```

- [ ] **Step 4: Add temporary stubs so the module imports** — Task 6 supplies the real `_via_ps` readers. To keep the module importable and Task 5 self-contained/green, add minimal stubs now, immediately after `_rss_kb_via_proc` (Task 6 replaces them):

```python
def _comm_via_ps(pid):  # replaced in Task 6
    return None


def _ppid_via_ps(pid):  # replaced in Task 6
    return None


def _rss_kb_via_ps(pid):  # replaced in Task 6
    return None
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python3 -m unittest tests.test_status_line.TestProcRssLinux -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add tools/status-line.py tests/test_status_line.py
git commit -m "fix(status-line): RSS returns None unless a claude ancestor matched (FR-3.4)"
```

---

### Task 6: Process RSS — macOS `ps` fallback (FR-3.5)

**Files:**
- Modify: `tools/status-line.py` — replace the three `_via_ps` stubs from Task 5 with real `ps`-based readers
- Test: `tests/test_status_line.py`

- [ ] **Step 1: Write the failing test** — append:

```python
class TestProcRssMacOS(unittest.TestCase):
    def test_ps_fallback_when_no_proc(self):
        comm = {10: "login", 11: "claude", 1: "launchd"}
        ppid = {10: 11, 11: 1, 1: 0}
        rss = {11: 307200, 10: 100}
        with mock.patch.object(sl.os.path, "isdir", return_value=False), \
             mock.patch.object(sl.os, "getppid", return_value=10), \
             mock.patch.object(sl, "_comm_via_ps", side_effect=comm.get), \
             mock.patch.object(sl, "_ppid_via_ps", side_effect=ppid.get), \
             mock.patch.object(sl, "_rss_kb_via_ps", side_effect=rss.get):
            self.assertEqual(sl.proc_rss_bytes(), 307200 * 1024)

    def test_ps_field_parses_one_value(self):
        class R:
            stdout = "  12345\n"
        with mock.patch.object(sl.subprocess, "run", return_value=R()):
            self.assertEqual(sl._ps_field(99, "rss"), "12345")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_status_line.TestProcRssMacOS -v`
Expected: FAIL — `_ps_field` missing / stubs return None so the first test fails.

- [ ] **Step 3: Replace the three stubs** — swap the Task-5 `_via_ps` stubs for:

```python
def _ps_field(pid, field):
    """One `ps -o <field>= -p <pid>` value as a stripped string, or None."""
    try:
        out = subprocess.run(["ps", "-o", f"{field}=", "-p", str(pid)],
                             capture_output=True, text=True, timeout=1).stdout.strip()
        return out or None
    except (OSError, subprocess.SubprocessError):
        return None


def _comm_via_ps(pid):
    out = _ps_field(pid, "comm")
    return os.path.basename(out) if out else None


def _ppid_via_ps(pid):
    out = _ps_field(pid, "ppid")
    try:
        return int(out) if out else None
    except ValueError:
        return None


def _rss_kb_via_ps(pid):
    out = _ps_field(pid, "rss")
    try:
        return int(out) if out else None
    except ValueError:
        return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_status_line.TestProcRssMacOS -v`
Expected: PASS. Then the full suite:
Run: `python3 -m unittest tests.test_status_line -v`
Expected: OK.

- [ ] **Step 5: Commit**

```bash
git add tools/status-line.py tests/test_status_line.py
git commit -m "feat(status-line): macOS ps fallback for process RSS (FR-3.5)"
```

---

### Task 7: Terminal dimensions — `tput` fallback (FR-3.6)

**Files:**
- Modify: `tools/status-line.py` — add a `tput` fallback in `terminal_size` (~lines 433-442), before the assumed default
- Test: `tests/test_status_line.py`

- [ ] **Step 1: Write the failing test** — append:

```python
class TestTputFallback(unittest.TestCase):
    def test_tput_used_when_stty_yields_nothing(self):
        def fake_run(cmd, **kw):
            class R:
                stdout = ""
            r = R()
            if cmd[:1] == ["stty"]:
                r.stdout = ""               # stty size unavailable
            elif cmd == ["tput", "cols"]:
                r.stdout = "123\n"
            elif cmd == ["tput", "lines"]:
                r.stdout = "44\n"
            return r
        with mock.patch.object(sl.subprocess, "run", side_effect=fake_run), \
             mock.patch("builtins.open", mock.mock_open(read_data="")):
            cols, lines, assumed = sl.terminal_size({})
        self.assertEqual((cols, lines), (123, 44))
        self.assertFalse(assumed)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_status_line.TestTputFallback -v`
Expected: FAIL — falls through to the assumed `200, 40` with `assumed=True`.

- [ ] **Step 3: Add the `tput` fallback** — in `terminal_size`, immediately **after** the existing `stty` block (the `try/except` that runs `stty size`) and **before** `assumed = False`, insert:

```python
    if cols is None or lines is None:
        # tput reads terminfo against the controlling tty — works where `stty size`
        # is unavailable on some macOS / terminal setups.
        try:
            with open("/dev/tty") as tty:
                def _tput(cap):
                    r = subprocess.run(["tput", cap], stdin=tty,
                                       capture_output=True, text=True, timeout=1).stdout.strip()
                    return int(r) if r.isdigit() else None
                cols = cols or _tput("cols")
                lines = lines or _tput("lines")
        except Exception:
            pass
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_status_line.TestTputFallback -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tools/status-line.py tests/test_status_line.py
git commit -m "feat(status-line): tput fallback for terminal size (FR-3.6)"
```

---

### Task 8: Cross-platform clarity pass — `/simplify` + `/reduce-entropy` (cluster 6)

**Files:**
- Modify: `tools/status-line.py` — the two platform helpers only (`terminal_size`, the `proc_rss_bytes` cluster)

This task carries no new behavior — it removes incidental complexity from the two platform-specific helpers and makes the Linux/macOS branches obvious. It is bounded by a hard invariant: **every test still passes and observable output is unchanged.**

- [ ] **Step 1: Snapshot green baseline**

Run: `python3 -m unittest tests.test_status_line -v`
Expected: OK. Note the test count — it must not drop.

- [ ] **Step 2: Run `/simplify` scoped to the platform helpers**

Invoke the `/simplify` skill on `tools/status-line.py`, **restricted to** `terminal_size` and the `proc_rss_bytes` + `_*_via_proc` / `_*_via_ps` / `_ps_field` cluster. Accept only changes that preserve each function's signature and return contract (`proc_rss_bytes() -> int|None`, `terminal_size(env) -> (cols, lines, assumed)`). Do **not** touch the already-portable code (builders, packer, `git_info`, formatters).

- [ ] **Step 3: Run `/reduce-entropy` on the same scope**

Invoke `/reduce-entropy` on the same two helpers — collapse duplicated try/except shapes, name the capability probe and fallback chain clearly, drop dead locals. Same invariant.

- [ ] **Step 4: Verify behavior unchanged**

Run: `python3 -m unittest tests.test_status_line -v`
Expected: OK, with the **same test count** as Step 1. If any test changed meaning, revert that edit — the pass is refactor-only.

- [ ] **Step 5: Eyeball the diff for the clarity goal**

Run: `git diff tools/status-line.py`
Confirm the diff is confined to the two helpers and that a reader can now see "Linux: /proc · macOS: ps · else: None" and the dims fallback order at a glance. Revert anything outside scope.

- [ ] **Step 6: Commit**

```bash
git add tools/status-line.py
git commit -m "refactor(status-line): clarify cross-platform RSS + dims helpers (simplify + reduce-entropy)"
```

---

### Task 9: Roadmap index correction + mark E3 progress

**Files:**
- Modify: `docs/prds/000-ai-kit-overhaul-requirements.md`

- [ ] **Step 1: Correct the sequencing note** — in `docs/prds/000-ai-kit-overhaul-requirements.md`, change the suggested-sequence line

```markdown
**Suggested sequence**: E1 → E3 → E2 → E5, with **E4 first** (keystone; E3 and E5 depend on it).
```

to

```markdown
**Suggested sequence**: E1 → E2 → E3 → E4 → E5. E3 ships standalone with hardcoded
defaults; **E4 later makes E3's colors/thresholds user-configurable** (E4 is not a
prerequisite — the earlier "E4 first" note was a planning error).
```

- [ ] **Step 2: Mark the E3 row** — change the E3 table row status to:

```markdown
| **E3** | status-line bug fixes (effort/blue/memory/macOS) | **done** → `tools/status-line.py` cross-platform; plan `docs/superpowers/plans/2026-06-18-e3-statusline-fixes-crossplatform.md` |
```

- [ ] **Step 3: Soften the E3 dependency line** — in the E3 section's **Dependencies** paragraph, replace the sentence stating E3 depends on E4 with:

```markdown
**Dependencies**: none for shipping the fixes (standalone). E4 *consumes* E3 by making
its colors/thresholds (blue, chat-size ramp, per-level effort colors) overridable; E3 does not block on E4.
```

- [ ] **Step 4: Run the full suite once more**

Run: `python3 -m unittest discover -s tests -p 'test_*.py'`
Expected: OK.

- [ ] **Step 5: Commit**

```bash
git add docs/prds/000-ai-kit-overhaul-requirements.md
git commit -m "docs(e3): correct E4-first sequencing error; mark E3 done"
```

---

## Self-Review

**1. Spec coverage:**
- FR-3.1 (resolve level + detect auto setting) → Task 4 (`resolve_effort` + `effort_setting_is_auto`).
- FR-3.2 (annotate auto-chosen level) → Task 3 (`_EFFORT_BARS` fixed colors + `[auto]`/`*` degradation).
- FR-3.3 (robust blue) → Task 1 (`BLUE` 38;5;33, `LIGHTBLUE` 38;5;75).
- FR-3.4 (memory wrong process) → Task 5 (return None unless `claude` matched).
- FR-3.5 (macOS RSS) → Task 6 (`ps` fallback).
- FR-3.6 (macOS dims) → Task 7 (`tput` fallback).
- FR-3.7 (color chat-size) → Task 2 (`CHAT_SIZE_RAMP`, full 8-band ramp).
- Cluster 6 (cross-platform clarity) → Tasks 5–7 structure it; Task 8 applies `/simplify` + `/reduce-entropy`.
- Index correction → Task 9. No gaps.

**2. Placeholder scan:** No TBD/TODO. The auto setting (FR-3.2) is read deterministically from the on-disk `settings.json` chain — no live sample needed. Task 8 is a refactor task with hard pass/scope invariants, not vague work.

**3. Type consistency:** `pick_color(value, ramp)` reused for bytes (Task 2) exactly as for pct. `resolve_effort(raw, env) -> str` (Task 4) feeds `build_data`'s `effort`; `effort_setting_is_auto(work_dir, home) -> bool` (Task 4) feeds `effort_auto`, which `seg_effort` (Task 3) reads via `data.get("effort_auto")`. The RSS backend trio `_comm_via_proc/_ppid_via_proc/_rss_kb_via_proc` (Task 5) and `_comm_via_ps/_ppid_via_ps/_rss_kb_via_ps` (Task 6) share one signature `(pid) -> value|None`; `proc_rss_bytes` selects between them by the `os.path.isdir("/proc")` probe and returns `int|None`. `terminal_size(env) -> (cols, lines, assumed)` unchanged. Consistent.

---

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-06-18-e3-statusline-fixes-crossplatform.md`. Two execution options:**

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration.

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints.

**Which approach?**
