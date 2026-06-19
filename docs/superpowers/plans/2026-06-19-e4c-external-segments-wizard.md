# E4c External Drop-in Segments — Setup-Wizard Integration Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the E5 setup wizard (`tools/setup.py`) discover external drop-in segment providers, list them alongside the built-in segments with their current enabled/disabled state, and offer an opt-in copy of the shipped `sysmem` sample into the user's segments directory.

**Architecture:** The wizard already renders `sorted(state["segments"])` with `[x]/[ ]` toggles and live preview. We fold discovered external ids into that `segments` dict (default-on), so they appear and toggle with zero changes to the command loop. A small discovery helper mirrors the renderer's (the wizard can't import the hyphenated `status-line.py`, so it duplicates a minimal scan — same pattern as the existing `SEGMENT_DEFAULTS` duplication). An opt-in prompt copies `examples/segments/sysmem` into the segments dir during the wizard preamble.

**Tech Stack:** Python 3.11+ stdlib (`os`, `re`, `stat`, `shutil`). Tests: `unittest` via `importlib` (matching `tests/test_setup.py`), run with `pytest`.

**Depends on:** `2026-06-19-e4c-external-segments-core.md` (the renderer engine + the shipped `examples/segments/sysmem` sample). Implement that plan first.

**Reference:** spec `docs/superpowers/specs/2026-06-19-e4c-statusline-external-segments-design.md` (FR-4c.9).

---

## File Structure

| File | Responsibility | Action |
|---|---|---|
| `tools/setup.py` | provider discovery for the wizard, fold externals into segment state, opt-in sample copy | Modify |
| `tests/test_setup.py` | new wizard tests | Modify |

### New / changed objects in `setup.py` (names fixed — used across tasks)

- `wizard_segments_dir(path, env) -> str` — resolve the providers dir (env > `[external].dir` > default).
- `discover_external_ids(directory) -> list[tuple[str, str]]` — `(id, path)` per executable provider.
- `current_segments(path, extra=None)` — gains an `extra` baseline dict for external default-on ids.
- `_segment_changes_vs_recipe(path, segments, extra=None)` — same `extra` baseline so default-on externals aren't needlessly written.
- `copy_sample_segment(install_dir, segments_dir, tty, dry) -> bool` — opt-in copy of `sysmem`.
- `run_statusline_wizard` — preamble copy prompt + external-aware state seeding + notes.

---

## Task W1: Discovery helpers in `setup.py`

**Files:**
- Modify: `tools/setup.py` (add near `current_segments`, ~line 86; ensure `import stat` and `import re` present — `re` already imported)
- Test: `tests/test_setup.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_setup.py` (reuse its existing `load_module()`/module handle — this plan calls it `su`; match the file's actual name if different):

```python
class TestExternalDiscovery(unittest.TestCase):
    def setUp(self):
        import tempfile, shutil, os, stat
        self.dir = tempfile.mkdtemp()
        self.addCleanup(lambda: shutil.rmtree(self.dir, ignore_errors=True))

    def _write(self, name, body, executable=True):
        import os, stat
        p = os.path.join(self.dir, name)
        with open(p, "w") as f:
            f.write(body)
        if executable:
            os.chmod(p, os.stat(p).st_mode | stat.S_IXUSR)
        return p

    def test_lists_executable_providers_with_id(self):
        self._write("aws.sh", "#!/bin/sh\n# ai-kit-segment: id=aws-session\necho\n")
        self._write("plain", "#!/bin/sh\necho\n")
        ids = dict(su.discover_external_ids(self.dir))
        self.assertIn("aws-session", ids)        # explicit id
        self.assertIn("plain", ids)              # stem fallback

    def test_skips_non_executable(self):
        self._write("noexec", "#!/bin/sh\necho\n", executable=False)
        self.assertEqual(su.discover_external_ids(self.dir), [])

    def test_missing_dir_empty(self):
        self.assertEqual(su.discover_external_ids("/no/such/dir"), [])

    def test_segments_dir_env_wins(self):
        env = {"CC_AI_KIT_SEGMENTS_DIR": "/env/segs"}
        self.assertEqual(su.wizard_segments_dir("/tmp/x.toml", env), "/env/segs")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_setup.py::TestExternalDiscovery -v`
Expected: FAIL — `AttributeError: ... 'discover_external_ids'`

- [ ] **Step 3: Add the helpers**

Ensure `import stat` is present near the top of `tools/setup.py` (add it if absent). Then add after `current_layout` (~line 107):

```python
_SEG_HEADER_RE = re.compile(r"^#\s*ai-kit-segment:\s*(.*?)\s*$")


def wizard_segments_dir(path, env):
    """External providers directory for the wizard: CC_AI_KIT_SEGMENTS_DIR >
    the config file's [external].dir > ${XDG_CONFIG_HOME:-$HOME/.config}/ai-kit/segments."""
    d = env.get("CC_AI_KIT_SEGMENTS_DIR") or (read_toml(path).get("external") or {}).get("dir")
    if d:
        return os.path.expanduser(d)
    base = env.get("XDG_CONFIG_HOME") or os.path.join(env.get("HOME", ""), ".config")
    return os.path.join(base, "ai-kit", "segments")


def discover_external_ids(directory):
    """List (id, path) for each executable provider in `directory`, sorted by
    (filename, id). id is the header `id=` value if present, else the filename
    stem. Mirrors status-line.py's discovery (duplicated, not imported: the
    renderer's hyphenated filename isn't an importable module)."""
    out = []
    if not directory or not os.path.isdir(directory):
        return out
    for name in sorted(os.listdir(directory)):
        p = os.path.join(directory, name)
        if not (os.path.isfile(p) and os.access(p, os.X_OK)):
            continue
        sid = os.path.splitext(name)[0]
        try:
            with open(p, encoding="utf-8", errors="replace") as f:
                for _ in range(10):
                    ln = f.readline()
                    if not ln:
                        break
                    m = _SEG_HEADER_RE.match(ln)
                    if m:
                        for tok in m.group(1).split():
                            if tok.startswith("id="):
                                sid = tok[3:]
                        break
        except OSError:
            continue
        out.append((sid, p))
    out.sort(key=lambda t: (os.path.basename(t[1]), t[0]))
    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_setup.py::TestExternalDiscovery -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add tools/setup.py tests/test_setup.py
git commit -m "feat(e4c-wizard): external provider discovery in setup.py"
```

---

## Task W2: Fold externals into segment state (default-on, listed, toggleable)

**Files:**
- Modify: `tools/setup.py` (`current_segments` ~86, `_segment_changes_vs_recipe` ~780, `run_statusline_wizard` ~870, `_print_segments` note lookup ~859)
- Test: `tests/test_setup.py`

- [ ] **Step 1: Write the failing test**

Append:

```python
class TestExternalState(unittest.TestCase):
    def setUp(self):
        import tempfile, shutil, os
        self.dir = tempfile.mkdtemp()
        self.toml = os.path.join(self.dir, "statusline.toml")
        self.addCleanup(lambda: shutil.rmtree(self.dir, ignore_errors=True))

    def test_external_default_on_in_current_segments(self):
        seg = su.current_segments(self.toml, extra={"sysmem": True})
        self.assertTrue(seg["sysmem"])
        self.assertTrue(seg["path"])              # built-ins still present

    def test_external_explicit_disable_honored(self):
        with open(self.toml, "w") as f:
            f.write("[segments]\nsysmem = false\n")
        seg = su.current_segments(self.toml, extra={"sysmem": True})
        self.assertFalse(seg["sysmem"])

    def test_changes_vs_recipe_ignores_default_on_external(self):
        # state matches the default (on); no change should be reported
        seg = {"sysmem": True}
        changes = su._segment_changes_vs_recipe(self.toml, seg, extra={"sysmem": True})
        self.assertNotIn("sysmem", changes)

    def test_changes_vs_recipe_reports_disable(self):
        changes = su._segment_changes_vs_recipe(self.toml, {"sysmem": False},
                                                extra={"sysmem": True})
        self.assertEqual(changes["sysmem"], False)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_setup.py::TestExternalState -v`
Expected: FAIL — `current_segments() got an unexpected keyword argument 'extra'`

- [ ] **Step 3a: Add `extra` to `current_segments`**

Replace `current_segments` (~86):

```python
def current_segments(path, extra=None):
    """Resolved {key: bool}: SEGMENT_DEFAULTS (+ optional `extra` default-on
    external ids) merged with the file's [segments]. Unknown keys and non-bool
    values in the file are ignored (defaults win)."""
    seg = dict(SEGMENT_DEFAULTS)
    if extra:
        seg.update(extra)
    for k, v in (read_toml(path).get("segments") or {}).items():
        if k in seg and isinstance(v, bool):
            seg[k] = v
    return seg
```

- [ ] **Step 3b: Add `extra` to `_segment_changes_vs_recipe`**

Replace `_segment_changes_vs_recipe` (~780):

```python
def _segment_changes_vs_recipe(path, segments, extra=None):
    """The {key: bool} subset of `segments` that DIFFERS from what `path` currently
    resolves to — the minimal set to patch. `extra` carries external default-on ids
    so an unchanged default-on provider is not needlessly written."""
    current = current_segments(path, extra=extra)
    return {k: v for k, v in segments.items() if current.get(k) != v}
```

- [ ] **Step 3c: Seed the wizard state with externals + a note fallback**

> **Note:** SUPERSEDED BY Task W3 Step 3b — the full preamble block (including `ext_dir` resolution) is replaced there. Implement Task W3 Step 3b instead of this step.

In `run_statusline_wizard` (~870), after the existing `raw = read_toml(cfg)` line and before building `state`, discover providers and build the `extra` baseline; thread it through state, the change computation, and the note lookup. Replace the `state = {...}` construction (~882-887):

```python
    raw = read_toml(cfg)
    ext_dir = wizard_segments_dir(cfg, os.environ)
    ext = dict(discover_external_ids(ext_dir))          # {id: path}
    ext_defaults = {sid: True for sid in ext}
    state = {
        "segments": current_segments(cfg, extra=ext_defaults),
        "layout": current_layout(cfg),
        "worktree": bool((raw.get("git") or {}).get("worktree", False)),
        "external": ext_defaults,                       # baseline for save
        "dirty": False,
    }
```

- [ ] **Step 3d: External-aware note in `_print_segments`**

Replace the note line in `_print_segments` (~866) so externals get a generic label:

```python
        note = _SEGMENT_NOTES.get(key) or "external drop-in segment"
```

- [ ] **Step 3e: Pass `extra` when saving**

In `_save_and_report` (~940), thread the external baseline into the change computation:

```python
    seg_changes = _segment_changes_vs_recipe(paths.config_toml, state["segments"],
                                             extra=state.get("external"))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_setup.py::TestExternalState -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Full setup suite (no regressions)**

Run: `python3 -m pytest tests/test_setup.py -q`
Expected: PASS — existing wizard tests still green (`current_segments`/`_segment_changes_vs_recipe` keep their old behavior when `extra` is omitted).

- [ ] **Step 6: Commit**

```bash
git add tools/setup.py tests/test_setup.py
git commit -m "feat(e4c-wizard): list + toggle external segments (default-on)"
```

---

## Task W3: Opt-in copy of the `sysmem` sample

**Files:**
- Modify: `tools/setup.py` (add `copy_sample_segment`; call it in `run_statusline_wizard` preamble ~878)
- Test: `tests/test_setup.py`

- [ ] **Step 1: Write the failing test**

Append:

```python
class TestCopySample(unittest.TestCase):
    def setUp(self):
        import tempfile, shutil, os
        self.root = tempfile.mkdtemp()
        self.install = os.path.join(self.root, "install")
        self.segs = os.path.join(self.root, "segs")
        os.makedirs(os.path.join(self.install, "examples", "segments"))
        with open(os.path.join(self.install, "examples", "segments", "sysmem"), "w") as f:
            f.write("#!/usr/bin/env python3\n# ai-kit-segment: id=sysmem\nprint('x')\n")
        self.addCleanup(lambda: shutil.rmtree(self.root, ignore_errors=True))

    class _TTY:
        def __init__(self, answer): self._a = answer; self.out = []
        def write(self, s): self.out.append(s)
        def flush(self): pass
        def readline(self): return self._a

    def test_yes_copies_and_makes_executable(self):
        import os
        tty = self._TTY("y\n")
        copied = su.copy_sample_segment(self.install, self.segs, tty, dry=False)
        self.assertTrue(copied)
        dst = os.path.join(self.segs, "sysmem")
        self.assertTrue(os.access(dst, os.X_OK))

    def test_no_does_not_copy(self):
        import os
        tty = self._TTY("n\n")
        self.assertFalse(su.copy_sample_segment(self.install, self.segs, tty, dry=False))
        self.assertFalse(os.path.exists(os.path.join(self.segs, "sysmem")))

    def test_skips_when_already_present(self):
        import os
        os.makedirs(self.segs)
        open(os.path.join(self.segs, "sysmem"), "w").close()
        tty = self._TTY("y\n")
        self.assertFalse(su.copy_sample_segment(self.install, self.segs, tty, dry=False))

    def test_dry_run_does_not_write(self):
        import os
        tty = self._TTY("y\n")
        self.assertFalse(su.copy_sample_segment(self.install, self.segs, tty, dry=True))
        self.assertFalse(os.path.exists(os.path.join(self.segs, "sysmem")))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_setup.py::TestCopySample -v`
Expected: FAIL — `AttributeError: ... 'copy_sample_segment'`

- [ ] **Step 3a: Add `copy_sample_segment`**

Add near `copy_recipe_if_absent` (~744):

```python
def copy_sample_segment(install_dir, segments_dir, tty, dry):
    """Offer to copy the bundled system-available-memory sample provider into the
    user's segments dir. Opt-in (default No). Skips silently if the sample is
    missing or a same-named provider already exists. Returns True only if copied."""
    src = os.path.join(install_dir, "examples", "segments", "sysmem")
    dst = os.path.join(segments_dir, "sysmem")
    if not os.path.isfile(src) or os.path.exists(dst):
        return False
    if not ask_yes_no(
            tty, "Copy the sample 'system available memory' segment to %s?" % segments_dir,
            default=False):
        return False
    if dry:
        print("would copy %s -> %s" % (src, dst))
        return False
    os.makedirs(segments_dir, exist_ok=True)
    shutil.copy2(src, dst)
    os.chmod(dst, os.stat(dst).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    print("  ✓ copied sample segment -> %s" % dst, file=tty)
    return True
```

(Ensure `import shutil` and `import stat` are present at the top of `setup.py`.)

- [ ] **Step 3b: Call it in the wizard preamble**

In `run_statusline_wizard` (~878), after `wire_statusline(...)` and before resolving `ext_dir`/`ext`, offer the copy so a freshly-copied sample is discovered in the same run:

```python
    copy_recipe_if_absent(paths.sample, paths.config_toml, dry)
    wire_statusline(paths.settings, paths.status_line, tty, dry)
    cfg = paths.config_toml
    raw = read_toml(cfg)
    ext_dir = wizard_segments_dir(cfg, os.environ)
    copy_sample_segment(paths.install_dir, ext_dir, tty, dry)
    ext = dict(discover_external_ids(ext_dir))
    ext_defaults = {sid: True for sid in ext}
    state = {
        "segments": current_segments(cfg, extra=ext_defaults),
        "layout": current_layout(cfg),
        "worktree": bool((raw.get("git") or {}).get("worktree", False)),
        "external": ext_defaults,
        "dirty": False,
    }
```

> **Note:** `copy_recipe_if_absent` (first line above) only copies the sample TOML when the config file does not yet exist — existing installs will not have the `[external]` block added automatically.

(This replaces the Task W2 Step 3c block — `ext_dir` is now resolved once, before the copy prompt, and reused for discovery.)

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_setup.py::TestCopySample -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Full setup suite**

Run: `python3 -m pytest tests/test_setup.py -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add tools/setup.py tests/test_setup.py
git commit -m "feat(e4c-wizard): opt-in copy of the sysmem sample segment"
```

---

## Final verification

- [ ] **Run the full suite**

Run: `python3 -m pytest tests/test_setup.py tests/test_status_line.py tests/test_external_segments.py -q`
Expected: ALL PASS.

- [ ] **Manual wizard smoke test (optional, interactive)**

Run `make install` (or `python3 tools/setup.py install`) in a scratch `HOME`, drop an executable in `~/.config/ai-kit/segments/`, and confirm it appears in the status-line wizard's numbered list with `[x]`, toggles off/on, and the preview reflects it.

---

## Self-Review (completed during authoring)

- **Spec coverage (FR-4c.9):** wizard discovers providers (W1), lists them with current toml state and toggles them (W2), and offers the opt-in `sysmem` copy (W3). All three are covered.
- **Placeholder scan:** none — complete code in every step. `os.environ` is passed directly to `wizard_segments_dir` in `run_statusline_wizard` (no helper indirection needed).
- **Type consistency:** `discover_external_ids` returns `list[(id, path)]`; `extra` is always a `{id: True}` dict; `current_segments`/`_segment_changes_vs_recipe` accept `extra` consistently across W2/W3. The W3 preamble block supersedes the W2 Step 3c block (noted inline) so `ext_dir` is resolved exactly once.
```
