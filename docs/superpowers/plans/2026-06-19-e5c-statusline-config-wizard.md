# E5c — Status-line Config Wizard (Segment Toggles, Reorder, Live Preview, Preservation) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the E5b status-line wizard stub with a real interactive editor that lets a human toggle segments on/off, reorder/move them within and across `[[line]]` rows, flip the `[git] worktree` knob, see a live preview after every change, and — on save — write the result back to `~/.config/ai-kit/statusline.toml` with a **surgical, comment-preserving, key-granularity text patch** that never disturbs `[palette]`, `[ramp.*]`, `[external]`, comments, or the `# version` line. The wizard self-validates its own output via the doctor and refuses to leave a broken file.

**Architecture:** `tools/setup.py` (stdlib-only, created by E5b) reads the recipe with `tomllib` (read helpers `read_toml`/`current_segments`/`current_layout`) and resolves the *effective* segment/layout/worktree state by merging built-in defaults with the file. The interactive loop (`run_statusline_wizard`) mutates in-memory dicts/lists; the live preview (`render_preview`) shells out to `tools/status-line.py < tests/fixtures/sample-input.json` with `CC_AI_KIT_SEGMENT_<KEY>=<bool>` env overrides so the preview reuses the real renderer with no temp files. On quit, three pure text-patch functions (`patch_segments`, `patch_layout`, `patch_git_worktree`) operate on the file's **raw text**, locating each managed block by header and rewriting only the managed `key = value` lines in place (uncommenting `# cost = false` → `cost = true`), appending a missing managed key with its recipe doc-comment, and leaving every other byte untouched. `write_toml_preserving` does an atomic write then runs `status-line.py --doctor` against the result; a failing doctor reverts the file.

**Why no `tomlkit` / no parse→re-emit:** Python's stdlib ships `tomllib` (read-only) but **no TOML writer**. A `tomllib.load` → re-serialize round-trip would destroy every comment and the self-documenting recipe layout, and a style-preserving third-party writer (`tomlkit`) is **forbidden** by the project's stdlib-only constraint. The only design satisfying both "zero deps" and "never lose customizations" is a surgical text patch on the raw file — the core of this phase.

**Tech Stack:** Python 3 stdlib only (`unittest`, `tomllib`, `subprocess`, `os`, `tempfile`, `re`). No new dependencies. Source: `tools/setup.py` (extended). Tests: `tests/test_setup.py` (run via `python3 -m unittest tests.test_setup`). Fixture: `tests/fixtures/sample-input.json`. The wizard reads prompts from the `tty` handle E5b's `open_tty()` returns and writes the TOML at `paths.config_toml`.

**Spec:** `docs/superpowers/specs/2026-06-19-e5-installer-wizard-design.md` §5, §5.1, §5.2. (§5.3 schema migration is explicitly OUT OF SCOPE.)

**Depends on:** E5b (creates `tools/setup.py` with the shared skeleton: `Paths`, `resolve_paths`, `open_tty`, `is_interactive`, `ask_yes_no`, `wire_statusline`, `copy_recipe_if_absent`, a STUB `run_statusline_wizard`, `main`). E5a (adds `status-line.py --doctor`). This plan **adds to** that `setup.py`; it does not recreate it.

---

## File Structure

| File | Responsibility | Change |
|---|---|---|
| `tools/setup.py` | Wizard + install engine (stdlib-only) | Add `read_toml`, `current_segments`, `current_layout`, `render_preview`, `patch_segments`, `patch_layout`, `patch_git_worktree`, `write_toml_preserving`; **replace** the E5b `run_statusline_wizard` stub with the real interactive loop; wire it into the menu's "Status line" branch |
| `tests/test_setup.py` | unittest suite (created by E5b) | Add `TestTomlRead`, `TestRenderPreview`, `TestPatchSegments`, `TestPatchLayout`, `TestPatchGitWorktree`, `TestWritePreserving`, `TestGoldenPreservation`, `TestExternalSeam`, `TestWizardLoop` classes |
| `tests/fixtures/sample-input.json` | Deterministic status-line input for previews | **New** — a representative status JSON checked in so previews are reproducible in tests |
| `tests/fixtures/statusline-edited.toml` | Golden input: a user-edited recipe | **New** — recipe with hand-edited `[palette]`/`[ramp.*]`, a user comment, and an `[external]` block, used by preservation + external-seam tests |

**Reference anchors in `tools/status-line.py` (read-only — do not edit in this phase):**
- Segment keys = keys of `SEGMENTS` (status-line.py:32) and `BUILDERS` (status-line.py:767): `path, branch, dirty, todo, model, time_ago, clock, effort, lines, cost, total_time, api_time, render_time, dimensions, context, chat_size, memory, rate_limits`.
- Env override grammar: `CC_AI_KIT_SEGMENT_<KEY>` truthy `1 true t y yes on` / falsy `0 false f n no off` (status-line.py:90–91).
- `--doctor` is added by E5a (validates config + dry-renders).
- Default segments (the recipe's commented values mirror these): all `True` except `cost = false` and `dimensions = false`.
- Default layout (3 rows, status-line.py:57–62): `["path","branch","dirty","todo"]` (min_rows 0), `["model","time_ago","clock","effort","lines","cost","total_time","api_time"]` (20), `["render_time","dimensions","context","chat_size","memory","rate_limits"]` (30).

**Recipe shape that the patch functions must respect (`tools/statusline.toml.sample`):** EVERY managed line ships **commented out** (the file is a no-op so built-in defaults apply). Toggling a segment means uncommenting `# cost = false` → `cost = true`. `[[line]]` is **all-or-nothing**: a custom layout means uncommenting ALL three `[[line]]` blocks. The patch must preserve comments, `[palette]`, every `[ramp.*]`, `[external]`, and the `# version = 1` line byte-for-byte except the managed keys it changes.

---

## Task 1: `tests/fixtures/sample-input.json` — deterministic preview input

**Files:**
- New: `tests/fixtures/sample-input.json`
- Test: `tests/test_setup.py` (new `TestFixture` class)

The live preview must be deterministic in tests. We check in one representative status JSON (mirrors `status-line.py`'s input contract: `model`, `workspace`, `cost`, `context_window`, `transcript_path`, `session_id`, `rate_limits`). It deliberately omits a real `transcript_path` so transcript/RSS probes degrade quietly and output stays stable across machines.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_setup.py` (the harness loads setup.py the same way E5b set up — `setup = load_module()`; reuse it):

```python
import json
import os
import unittest

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "fixtures")
SAMPLE_INPUT = os.path.join(FIXTURE_DIR, "sample-input.json")


class TestFixture(unittest.TestCase):
    def test_sample_input_is_valid_json_with_required_keys(self):
        with open(SAMPLE_INPUT) as f:
            raw = json.load(f)
        for key in ("model", "workspace", "cost", "context_window"):
            self.assertIn(key, raw)
        self.assertIn("display_name", raw["model"])
        self.assertIn("used_percentage", raw["context_window"])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_setup.TestFixture -v`
Expected: FAIL — `FileNotFoundError: .../tests/fixtures/sample-input.json`.

- [ ] **Step 3: Create the fixture**

Create the directory and file:

```bash
mkdir -p tests/fixtures
```

Write `tests/fixtures/sample-input.json`:

```json
{
  "model": { "id": "claude-opus-4", "display_name": "Opus" },
  "workspace": { "current_dir": "/home/dev/project" },
  "cost": {
    "total_lines_added": 128,
    "total_lines_removed": 42,
    "total_cost_usd": 0.1234,
    "total_duration_ms": 754000,
    "total_api_duration_ms": 98000
  },
  "context_window": { "used_percentage": 23, "context_window_size": 200000 },
  "transcript_path": "",
  "session_id": "sample-input",
  "rate_limits": {
    "five_hour": { "used_percentage": 41, "resets_at": 1750000000 }
  }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_setup.TestFixture -v`
Expected: PASS (1 test).

- [ ] **Step 5: Commit**

```bash
git add tests/fixtures/sample-input.json tests/test_setup.py
git commit -m "test(setup): deterministic sample-input fixture for status-line preview (E5c)"
```

---

## Task 2: `read_toml` / `current_segments` / `current_layout` — resolved state

**Files:**
- Modify: `tools/setup.py` (new helpers; place near the top, after the E5b path helpers)
- Test: `tests/test_setup.py` (new `TestTomlRead` class)

These mirror `status-line.py`'s resolution semantics but **without env** (the wizard edits the file's persisted state, not per-session env): `current_segments` = defaults merged with `[segments]`; `current_layout` = the file's `[[line]]` blocks if any (all-or-nothing replace), else the default 3-row layout. `read_toml` returns `{}` for absent/malformed files (never raises) so the wizard runs on a missing or hand-broken file.

The segment defaults and the default layout are duplicated here as small module constants so `setup.py` does not import `status-line.py` (its filename has a hyphen — not importable — and the wizard must run even if the renderer is mid-edit). A drift test (Task 2, Step 1) pins them to the recipe so they can't silently diverge.

- [ ] **Step 1: Write the failing test**

```python
import tempfile

SAMPLE_RECIPE = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "tools", "statusline.toml.sample")


class TestTomlRead(unittest.TestCase):
    def test_read_toml_missing_returns_empty(self):
        self.assertEqual(setup.read_toml("/no/such/file.toml"), {})

    def test_read_toml_malformed_returns_empty(self):
        with tempfile.NamedTemporaryFile("w", suffix=".toml", delete=False) as f:
            f.write("this is = = not toml\n")
            path = f.name
        self.addCleanup(os.unlink, path)
        self.assertEqual(setup.read_toml(path), {})

    def test_current_segments_defaults_on_noop_recipe(self):
        # The shipped sample is all-commented (a no-op) -> pure defaults.
        seg = setup.current_segments(SAMPLE_RECIPE)
        self.assertTrue(seg["path"])
        self.assertFalse(seg["cost"])        # cost OFF by default
        self.assertFalse(seg["dimensions"])  # dimensions OFF by default
        self.assertEqual(set(seg), set(setup.SEGMENT_DEFAULTS))

    def test_current_segments_merges_file_override(self):
        with tempfile.NamedTemporaryFile("w", suffix=".toml", delete=False) as f:
            f.write("[segments]\ncost = true\nmemory = false\n")
            path = f.name
        self.addCleanup(os.unlink, path)
        seg = setup.current_segments(path)
        self.assertTrue(seg["cost"])
        self.assertFalse(seg["memory"])
        self.assertTrue(seg["path"])         # untouched default survives

    def test_current_layout_default_on_noop_recipe(self):
        layout = setup.current_layout(SAMPLE_RECIPE)
        self.assertEqual([r["segments"] for r in layout],
                         [["path", "branch", "dirty", "todo"],
                          ["model", "time_ago", "clock", "effort", "lines",
                           "cost", "total_time", "api_time"],
                          ["render_time", "dimensions", "context", "chat_size",
                           "memory", "rate_limits"]])

    def test_current_layout_file_replaces_all(self):
        with tempfile.NamedTemporaryFile("w", suffix=".toml", delete=False) as f:
            f.write('[[line]]\nmin_rows = 0\nsegments = ["path", "context"]\n')
            path = f.name
        self.addCleanup(os.unlink, path)
        layout = setup.current_layout(path)
        self.assertEqual(layout, [{"min_rows": 0, "segments": ["path", "context"]}])

    def test_segment_defaults_match_recipe_drift(self):
        # Drift guard: every [segments] key commented in the recipe must exist in
        # SEGMENT_DEFAULTS with the same default bool.
        import re as _re
        with open(SAMPLE_RECIPE) as f:
            text = f.read()
        in_seg = False
        for line in text.splitlines():
            if line.strip().startswith("# [segments]"):
                in_seg = True
                continue
            if in_seg and _re.match(r"#\s*\[", line):   # next section header
                break
            m = _re.match(r"#\s*(\w+)\s*=\s*(true|false)\b", line)
            if in_seg and m:
                key, val = m.group(1), m.group(2) == "true"
                self.assertIn(key, setup.SEGMENT_DEFAULTS)
                self.assertEqual(setup.SEGMENT_DEFAULTS[key], val,
                                 f"{key} default drifted from recipe")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_setup.TestTomlRead -v`
Expected: FAIL — `AttributeError: module 'setup' has no attribute 'read_toml'`.

- [ ] **Step 3: Write the implementation**

In `tools/setup.py`, add (after the E5b path helpers; `tomllib`, `os` are imported at top — add `import tomllib` if E5b did not already):

```python
# ── Status-line config defaults (mirrors status-line.py SEGMENTS/LAYOUT) ───────
# Duplicated here, not imported: status-line.py's hyphenated filename isn't an
# importable module, and the wizard must run even while the renderer is mid-edit.
# TestTomlRead.test_segment_defaults_match_recipe_drift pins these to the recipe.
SEGMENT_DEFAULTS = {
    "path": True, "branch": True, "dirty": True, "todo": True,
    "model": True, "time_ago": True, "clock": True, "effort": True,
    "lines": True, "cost": False, "total_time": True, "api_time": True,
    "render_time": True, "dimensions": False, "context": True, "chat_size": True,
    "memory": True, "rate_limits": True,
}
LAYOUT_DEFAULTS = [
    {"min_rows": 0, "segments": ["path", "branch", "dirty", "todo"]},
    {"min_rows": 20, "segments": ["model", "time_ago", "clock", "effort", "lines",
                                  "cost", "total_time", "api_time"]},
    {"min_rows": 30, "segments": ["render_time", "dimensions", "context",
                                  "chat_size", "memory", "rate_limits"]},
]


def read_toml(path):
    """Parse the TOML at `path`. Missing / empty / malformed → {} (never raises).
    Read-only — the wizard writes back via surgical text patch, not re-emit."""
    try:
        with open(path, "rb") as f:
            return tomllib.load(f)
    except (FileNotFoundError, IsADirectoryError):
        return {}
    except (OSError, tomllib.TOMLDecodeError):
        return {}


def current_segments(path):
    """Resolved {key: bool}: SEGMENT_DEFAULTS merged with the file's [segments].
    Unknown keys and non-bool values in the file are ignored (defaults win), the
    same lenient policy the renderer applies."""
    seg = dict(SEGMENT_DEFAULTS)
    for k, v in (read_toml(path).get("segments") or {}).items():
        if k in seg and isinstance(v, bool):
            seg[k] = v
    return seg


def current_layout(path):
    """Resolved layout as a list of {"min_rows": int, "segments": [str]} dicts.
    Any [[line]] block in the file REPLACES the whole layout (all-or-nothing,
    matching the renderer); otherwise the default 3-row layout (deep-copied)."""
    raw = read_toml(path).get("line")
    if not raw:
        return [{"min_rows": r["min_rows"], "segments": list(r["segments"])}
                for r in LAYOUT_DEFAULTS]
    return [{"min_rows": int(item.get("min_rows", 0)),
             "segments": list(item.get("segments", []))} for item in raw]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_setup.TestTomlRead -v`
Expected: PASS (7 tests).

- [ ] **Step 5: Commit**

```bash
git add tools/setup.py tests/test_setup.py
git commit -m "feat(setup): read_toml + resolved current_segments/current_layout (E5c)"
```

---

## Task 3: `render_preview` — live preview via subprocess + env overrides

**Files:**
- Modify: `tools/setup.py` (`render_preview` near the read helpers)
- Test: `tests/test_setup.py` (new `TestRenderPreview` class)

`render_preview` is the live-showcase engine: it runs `python3 status-line.py < sample-input.json` with the current toggles expressed as `CC_AI_KIT_SEGMENT_<KEY>` env overrides and returns the rendered text. Reuses the real renderer; no temp files; the sample is the checked-in fixture so it is deterministic. The env passes ONLY the segment toggles (and worktree, via `CC_AI_KIT_GIT_WORKTREE`) so the preview reflects in-memory edits before they are saved. Layout reorder is previewed by writing the file first (Task 8 handles that ordering); segment/worktree toggles preview live via env.

- [ ] **Step 1: Write the failing test**

```python
class TestRenderPreview(unittest.TestCase):
    def _status_line(self):
        return os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "tools", "status-line.py")

    def test_preview_renders_and_reflects_toggle_off(self):
        seg = dict(setup.SEGMENT_DEFAULTS)
        with open(SAMPLE_INPUT) as f:
            sample_json = f.read()
        on = setup.render_preview(self._status_line(), seg, sample_json, {})
        self.assertIn("Opus", on)            # model segment present by default
        seg["model"] = False
        off = setup.render_preview(self._status_line(), seg, sample_json, {})
        self.assertNotIn("Opus", off)        # toggling model off removes it

    def test_preview_passes_env_overrides_for_every_segment(self):
        # cost is OFF by default; turning it on must surface the 🪙 marker.
        seg = dict(setup.SEGMENT_DEFAULTS)
        seg["cost"] = True
        with open(SAMPLE_INPUT) as f:
            sample_json = f.read()
        out = setup.render_preview(self._status_line(), seg, sample_json, {})
        self.assertIn("🪙", out)

    def test_preview_never_raises_on_renderer_error(self):
        # A bogus interpreter/path must degrade to an empty string, not crash.
        out = setup.render_preview("/no/such/status-line.py",
                                   dict(setup.SEGMENT_DEFAULTS), "{}", {})
        self.assertEqual(out, "")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_setup.TestRenderPreview -v`
Expected: FAIL — `AttributeError: ... 'render_preview'`.

- [ ] **Step 3: Write the implementation**

```python
def _bool_env(value):
    return "1" if value else "0"


def render_preview(status_line, segments, sample_json, env):
    """Render the status line with the given segment toggles, for the live preview.

    Shells out to `python3 status-line.py` feeding `sample_json` on stdin and the
    toggles as CC_AI_KIT_SEGMENT_<KEY> env overrides (so it reflects in-memory
    edits before they are written). `env` carries only the keys to override
    (CC_AI_KIT_GIT_WORKTREE and/or forced terminal size); it is merged ON TOP OF
    os.environ so the subprocess inherits PATH, HOME, and PYTHONPATH.
    Returns the rendered text ("" on any failure — the preview is best-effort
    and must never crash the wizard)."""
    child = {**os.environ, **env}   # inherit full env; overrides layer on top
    # Force a wide, tall terminal so all rows/segments render in the preview
    # regardless of the wizard's own window size.
    child.setdefault("STATUSLINE_COLS", "200")
    child.setdefault("STATUSLINE_LINES", "40")
    for key, on in segments.items():
        child[f"CC_AI_KIT_SEGMENT_{key.upper()}"] = _bool_env(on)
    try:
        proc = subprocess.run(
            [sys.executable, "-S", status_line],
            input=sample_json, capture_output=True, text=True,
            env=child, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return ""
    if proc.returncode != 0:
        return ""
    return proc.stdout.rstrip("\n")
```

(`subprocess`, `sys` are imported at the top of `setup.py`; add the imports if E5b did not.)

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_setup.TestRenderPreview -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add tools/setup.py tests/test_setup.py
git commit -m "feat(setup): render_preview shells out to status-line.py with segment env (E5c)"
```

---

## Task 4: `patch_segments` — comment-aware, key-granularity segment patch

**Files:**
- Modify: `tools/setup.py` (`patch_segments` + a shared `_patch_keys` helper)
- Test: `tests/test_setup.py` (new `TestPatchSegments` class)

This is the hardest function. Contract: given the file's **raw text** and a `changes` dict `{key: bool}` of segments the user changed, rewrite ONLY those keys' `key = value` lines, **inside the `[segments]` block**, and leave every other byte unchanged.

Rules:
1. A managed key line may be **commented** (`# cost = false`) or **live** (`cost = true`). Match either form (allowing leading whitespace and `#` + spaces). Rewrite to the live form `<key> = <true|false>` preserving the original indentation and **any trailing `# comment`** on that line.
2. The `[segments]` header itself is commented in the shipped recipe (`# [segments]`). If we are writing ANY live `key = value` line, the header **must be uncommented too** (else the keys parse as top-level, breaking TOML). So when at least one changed key is written, ensure the `[segments]` header line is live.
3. A changed key **absent** from the file is **appended** at the end of the `[segments]` block, carrying its one-line doc comment from the recipe (`_SEGMENT_NOTES`), so the file stays self-documented.
4. Everything outside `[segments]` is byte-for-byte untouched.

Implementation strategy: operate line-by-line, tracking which `[...]` section we are in (a line is a section header if, after stripping an optional leading `# `, it matches `^\[`). Within `[segments]`, for each line matching a managed `key = ...` whose key is in `changes`, replace it. After the block ends (next header or EOF), append any still-unwritten changed keys.

- [ ] **Step 1: Write the failing test**

```python
class TestPatchSegments(unittest.TestCase):
    def test_uncomments_and_sets_single_key(self):
        text = ("# [segments]\n"
                "# path = true          # 📂 working directory\n"
                "# cost = false         # 🪙 session cost\n")
        out = setup.patch_segments(text, {"cost": True})
        self.assertIn("[segments]\n", out)              # header uncommented
        self.assertIn("cost = true", out)               # key flipped + live
        self.assertIn("# 🪙 session cost", out)          # trailing comment kept
        self.assertIn("# path = true", out)             # untouched key still commented

    def test_only_changed_key_touched(self):
        text = ("# [segments]\n"
                "# cost = false\n"
                "# memory = true\n")
        out = setup.patch_segments(text, {"cost": True})
        self.assertIn("cost = true", out)
        self.assertIn("# memory = true", out)           # memory untouched

    def test_set_false_writes_live_false(self):
        text = "# [segments]\n# memory = true\n"
        out = setup.patch_segments(text, {"memory": False})
        self.assertIn("memory = false", out)

    def test_appends_missing_key_with_note(self):
        text = "# [segments]\n# path = true\n"
        out = setup.patch_segments(text, {"clock": False})
        self.assertIn("clock = false", out)
        self.assertIn("⏰", out)                          # the clock note glyph

    def test_no_changes_returns_text_unchanged(self):
        text = "# [segments]\n# cost = false\n"
        self.assertEqual(setup.patch_segments(text, {}), text)

    def test_preserves_lines_outside_segments(self):
        text = ("# version = 1\n"
                "# [segments]\n# cost = false\n"
                "# [palette]\n# RED = \"31\"\n")
        out = setup.patch_segments(text, {"cost": True})
        self.assertIn("# version = 1\n", out)
        self.assertIn("# [palette]\n# RED = \"31\"\n", out)

    def test_result_parses_as_valid_toml(self):
        text = ("# [segments]\n"
                "# path = true\n# cost = false\n")
        out = setup.patch_segments(text, {"cost": True})
        import tomllib
        parsed = tomllib.loads(out)
        self.assertEqual(parsed["segments"]["cost"], True)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_setup.TestPatchSegments -v`
Expected: FAIL — `AttributeError: ... 'patch_segments'`.

- [ ] **Step 3: Write the implementation**

```python
import re   # at top of setup.py if not already imported

# One-line doc notes carried when a managed key is appended (keeps the recipe
# self-documenting). Lifted verbatim from tools/statusline.toml.sample comments.
_SEGMENT_NOTES = {
    "path": "📂 working directory, ~-relative   (pinned)",
    "branch": "🌿 git branch  (🌳 in a worktree)",
    "dirty": "working-tree dirty marker",
    "todo": "📝 current TODO  (📝 in-progress / ⏸ pending)",
    "model": "active model name (e.g. Opus)",
    "time_ago": "time since the session's first message",
    "clock": "⏰ current wall-clock time",
    "effort": "🧠 reasoning-effort ladder + level ([auto] when auto)",
    "lines": "📃 lines added / removed this session",
    "cost": "🪙 session cost in USD            (OFF by default)",
    "total_time": "💬 total session duration",
    "api_time": "📡 cumulative API response time",
    "render_time": "⏱ status-line's own render time, SLO/SLA-colored",
    "dimensions": "terminal size cols×lines (? if assumed)  (debug; OFF by default)",
    "context": "📊 context-window % used (and max) (pinned)",
    "chat_size": "💾 transcript file size on disk",
    "memory": "🧮 status-line process memory (RSS)",
    "rate_limits": "⚡ rate-limit buckets with reset time",
}

# A section header, optionally commented:  "# [segments]"  /  "[ramp.context]"
_HEADER_RE = re.compile(r"^\s*#?\s*\[")
# A managed key line, optionally commented, capturing key + trailing comment:
#   "# cost = false   # 🪙 ..."   ->  key="cost", trailing="# 🪙 ..."
_KEY_RE = re.compile(
    r"^(?P<indent>\s*)#?\s*(?P<key>\w+)\s*=\s*[^#\n]*?(?P<trail>\s*#.*)?$")


def _header_name(line):
    """The bracketed header name on `line` (commented or not), else None.
    "# [segments]" -> "segments"; "[ramp.context]" -> "ramp.context"."""
    m = re.match(r"^\s*#?\s*\[\[?\s*([^\]]+?)\s*\]\]?\s*$", line)
    return m.group(1) if m else None


def patch_segments(text, changes):
    """Surgically set the given {key: bool} segment toggles in `text`'s raw TOML.

    Key-granularity: rewrites ONLY each changed key's `key = value` line in place
    (uncommenting it and the [segments] header), appends a missing key with its
    doc note, and leaves every other byte — comments, [palette], [ramp.*],
    [external], the version line — untouched. Returns the patched text."""
    if not changes:
        return text
    lines = text.splitlines(keepends=True)
    out = []
    in_seg = False
    seg_header_idx = None          # index in `out` of the [segments] header line
    written = set()
    i = 0
    while i < len(lines):
        line = lines[i]
        name = _header_name(line)
        if name is not None:                       # a section header
            if in_seg:                             # leaving [segments]: append rest
                _append_missing(out, changes, written)
                in_seg = False
            if name == "segments":
                in_seg = True
                seg_header_idx = len(out)
                out.append(line)                   # may be uncommented below
                i += 1
                continue
            out.append(line)
            i += 1
            continue
        if in_seg:
            m = _KEY_RE.match(line)
            if m and m.group("key") in changes:
                key = m.group("key")
                trail = m.group("trail") or ""
                nl = "\n" if line.endswith("\n") else ""
                out.append(f"{m.group('indent')}{key} = "
                           f"{'true' if changes[key] else 'false'}{trail}{nl}")
                written.add(key)
                i += 1
                continue
        out.append(line)
        i += 1
    if in_seg:                                     # [segments] ran to EOF
        _append_missing(out, changes, written)
    # If we wrote any live key, the [segments] header must be live too.
    if written and seg_header_idx is not None:
        out[seg_header_idx] = re.sub(r"^(\s*)#\s*", r"\1", out[seg_header_idx], count=1)
    return "".join(out)


def _append_missing(out, changes, written):
    """Append any not-yet-written changed segment keys to the end of the
    [segments] block, each with its recipe doc note."""
    for key, val in changes.items():
        if key in written:
            continue
        note = _SEGMENT_NOTES.get(key, "")
        comment = f"          # {note}" if note else ""
        out.append(f"{key} = {'true' if val else 'false'}{comment}\n")
        written.add(key)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_setup.TestPatchSegments -v`
Expected: PASS (7 tests).

- [ ] **Step 5: Commit**

```bash
git add tools/setup.py tests/test_setup.py
git commit -m "feat(setup): patch_segments — comment-aware key-granularity TOML patch (E5c)"
```

---

## Task 5: `patch_layout` — all-or-nothing `[[line]]` rewrite, preserve rest

**Files:**
- Modify: `tools/setup.py` (`patch_layout`)
- Test: `tests/test_setup.py` (new `TestPatchLayout` class)

`[[line]]` is **all-or-nothing**: a custom layout means writing ALL line blocks (uncommented), because a partial layout silently drops the omitted segments. So `patch_layout(text, lines)` removes any existing `[[line]]` blocks (commented or live) and writes the full set of `lines` (each `{"min_rows": int, "segments": [str]}`) as live `[[line]]` blocks, placed where the first `[[line]]` block began (or, if none existed, immediately after the `[segments]` block / before the next non-line section). Everything else — `[segments]`, `[git]`, `[palette]`, `[ramp.*]`, `[external]`, comments — is preserved.

To keep it simple and robust: locate the contiguous region spanning the recipe's `[[line]]` blocks (the shipped recipe groups all three together, each preceded by its `# [[line]]` header), replace that whole region with the freshly rendered blocks, and leave a one-line header comment above them.

- [ ] **Step 1: Write the failing test**

```python
class TestPatchLayout(unittest.TestCase):
    LINES = [
        {"min_rows": 0, "segments": ["path", "branch"]},
        {"min_rows": 20, "segments": ["model", "clock"]},
    ]

    def test_writes_all_blocks_live(self):
        text = ("# [[line]]\n# min_rows = 0\n"
                '# segments = ["path", "branch", "dirty", "todo"]\n'
                "# [[line]]\n# min_rows = 20\n"
                '# segments = ["model", "clock"]\n')
        out = setup.patch_layout(text, self.LINES)
        import tomllib
        parsed = tomllib.loads(out)
        self.assertEqual([r["segments"] for r in parsed["line"]],
                         [["path", "branch"], ["model", "clock"]])
        self.assertEqual([r["min_rows"] for r in parsed["line"]], [0, 20])

    def test_preserves_surrounding_sections(self):
        text = ("# [segments]\n# cost = false\n"
                "# [[line]]\n# min_rows = 0\n# segments = [\"path\"]\n"
                "# [palette]\n# RED = \"31\"\n")
        out = setup.patch_layout(text, self.LINES)
        self.assertIn("# [segments]\n# cost = false\n", out)
        self.assertIn("# [palette]\n# RED = \"31\"\n", out)

    def test_roundtrip_parses(self):
        text = "# [[line]]\n# min_rows = 0\n# segments = [\"path\"]\n"
        out = setup.patch_layout(text, self.LINES)
        import tomllib
        tomllib.loads(out)          # must not raise
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_setup.TestPatchLayout -v`
Expected: FAIL — `AttributeError: ... 'patch_layout'`.

- [ ] **Step 3: Write the implementation**

```python
def _render_line_blocks(lines):
    """The full [[line]] section as live TOML text (all-or-nothing)."""
    chunks = ["## [[line]] layout written by the ai-kit status-line wizard.\n"
              "## ALL-OR-NOTHING: these blocks fully define the layout.\n"]
    for row in lines:
        segs = ", ".join(f'"{s}"' for s in row["segments"])
        chunks.append(f"[[line]]\nmin_rows = {int(row['min_rows'])}\n"
                      f"segments = [{segs}]\n")
    return "".join(chunks)


def patch_layout(text, lines):
    """Replace the file's [[line]] layout with `lines` (all-or-nothing), preserving
    every other section byte-for-byte. `lines` is a list of
    {"min_rows": int, "segments": [str]} dicts."""
    src = text.splitlines(keepends=True)
    out = []
    block = _render_line_blocks(lines)
    region_start = None
    i = 0
    n = len(src)
    while i < n:
        name = _header_name(src[i])
        if name == "line":
            # Consume the whole contiguous [[line]] region: this header, its body,
            # and any immediately-following [[line]] headers + bodies (plus the
            # comment lines that introduce them).
            if region_start is None:
                region_start = len(out)
            i += 1
            while i < n:
                nm = _header_name(src[i])
                if nm == "line":
                    i += 1
                    continue
                if nm is None and not src[i].lstrip().startswith("##"):
                    # a body line (min_rows / segments / blank) — part of the region
                    if src[i].strip() == "" or re.match(r"^\s*#?\s*(min_rows|segments)\b",
                                                         src[i]):
                        i += 1
                        continue
                break
            continue
        out.append(src[i])
        i += 1
    if region_start is None:                 # no [[line]] region existed: append
        if out and not out[-1].endswith("\n"):
            out.append("\n")
        out.append(block)
    else:
        out.insert(region_start, block)
    return "".join(out)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_setup.TestPatchLayout -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add tools/setup.py tests/test_setup.py
git commit -m "feat(setup): patch_layout — all-or-nothing [[line]] rewrite, preserve rest (E5c)"
```

---

## Task 6: `patch_git_worktree` — toggle `[git] worktree`, preserve rest

**Files:**
- Modify: `tools/setup.py` (`patch_git_worktree`)
- Test: `tests/test_setup.py` (new `TestPatchGitWorktree` class)

Reuse the same comment-aware key rewrite as `patch_segments`, scoped to the `[git]` block, for the single `worktree` key. If `[git]` is absent, append a `[git]` block with the `worktree` key + its doc note.

- [ ] **Step 1: Write the failing test**

```python
class TestPatchGitWorktree(unittest.TestCase):
    def test_uncomments_and_sets_true(self):
        text = "# [git]\n# worktree = false     # detect linked worktrees.\n"
        out = setup.patch_git_worktree(text, True)
        self.assertIn("[git]\n", out)
        self.assertIn("worktree = true", out)
        self.assertIn("# detect linked worktrees.", out)

    def test_sets_false(self):
        text = "[git]\nworktree = true\n"
        out = setup.patch_git_worktree(text, False)
        self.assertIn("worktree = false", out)

    def test_appends_git_block_when_absent(self):
        text = "# [segments]\n# cost = false\n"
        out = setup.patch_git_worktree(text, True)
        import tomllib
        self.assertEqual(tomllib.loads(out)["git"]["worktree"], True)

    def test_preserves_other_sections(self):
        text = "# [git]\n# worktree = false\n# [palette]\n# RED = \"31\"\n"
        out = setup.patch_git_worktree(text, True)
        self.assertIn("# [palette]\n# RED = \"31\"\n", out)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_setup.TestPatchGitWorktree -v`
Expected: FAIL — `AttributeError: ... 'patch_git_worktree'`.

- [ ] **Step 3: Write the implementation**

```python
def patch_git_worktree(text, value):
    """Set [git] worktree to `value`, preserving every other byte. Rewrites the
    key in place (uncommenting it + the [git] header); appends a [git] block with
    the key + doc note if [git] is absent."""
    lines = text.splitlines(keepends=True)
    out = []
    in_git = False
    git_header_idx = None
    written = False
    for line in lines:
        name = _header_name(line)
        if name is not None:
            in_git = (name == "git")
            if in_git:
                git_header_idx = len(out)
            out.append(line)
            continue
        if in_git and not written:
            m = _KEY_RE.match(line)
            if m and m.group("key") == "worktree":
                trail = m.group("trail") or ""
                nl = "\n" if line.endswith("\n") else ""
                out.append(f"{m.group('indent')}worktree = "
                           f"{'true' if value else 'false'}{trail}{nl}")
                written = True
                continue
        out.append(line)
    if written and git_header_idx is not None:
        out[git_header_idx] = re.sub(r"^(\s*)#\s*", r"\1", out[git_header_idx], count=1)
    if not written:
        if out and not out[-1].endswith("\n"):
            out.append("\n")
        out.append(f"[git]\nworktree = {'true' if value else 'false'}"
                   f"          # detect linked worktrees (🌳 vs 🌿).\n")
    return "".join(out)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_setup.TestPatchGitWorktree -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add tools/setup.py tests/test_setup.py
git commit -m "feat(setup): patch_git_worktree — toggle [git] worktree, preserve rest (E5c)"
```

---

## Task 7: `write_toml_preserving` — atomic write + doctor self-validation

**Files:**
- Modify: `tools/setup.py` (`write_toml_preserving`)
- Test: `tests/test_setup.py` (new `TestWritePreserving` class)

Atomic write: write to a temp file in the same directory, then `os.replace`. After writing, run `status-line.py --doctor` against the new file (via `CC_AI_KIT_CONFIG`); if the doctor exits non-zero, **revert** to the previous content and raise/return failure so the wizard refuses to leave a broken file (§5.1). The function takes the resolved status-line path so it can run the doctor.

- [ ] **Step 1: Write the failing test**

```python
class TestWritePreserving(unittest.TestCase):
    def _status_line(self):
        return os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "tools", "status-line.py")

    def test_writes_valid_toml_and_validates(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "statusline.toml")
            ok = setup.write_toml_preserving(
                path, "[segments]\ncost = true\n", self._status_line())
            self.assertTrue(ok)
            with open(path) as f:
                self.assertIn("cost = true", f.read())

    def test_rejects_broken_output_and_reverts(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "statusline.toml")
            with open(path, "w") as f:
                f.write("# good original\n")
            # An unknown segment key fails the doctor.
            ok = setup.write_toml_preserving(
                path, "[segments]\nbogus_key = true\n", self._status_line())
            self.assertFalse(ok)
            with open(path) as f:
                self.assertEqual(f.read(), "# good original\n")   # reverted
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_setup.TestWritePreserving -v`
Expected: FAIL — `AttributeError: ... 'write_toml_preserving'`.

- [ ] **Step 3: Write the implementation**

```python
def write_toml_preserving(path, text, status_line):
    """Atomically write `text` to `path`, then self-validate via the doctor.

    Writes to a sibling temp file and os.replace()s it into place (atomic). Then
    runs `status-line.py --doctor` against the result (CC_AI_KIT_CONFIG=path); if
    the doctor reports problems, the previous file content is restored and False
    is returned — the wizard must never leave a broken config (§5.1). Returns True
    on success."""
    prev = None
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            prev = f.read()
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path) or ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp, path)
    except OSError:
        if os.path.exists(tmp):
            os.unlink(tmp)
        return False
    env = dict(os.environ)
    env["CC_AI_KIT_CONFIG"] = path
    try:
        proc = subprocess.run([sys.executable, "-S", status_line, "--doctor"],
                              capture_output=True, text=True, env=env, timeout=10)
        ok = proc.returncode == 0
    except (OSError, subprocess.SubprocessError):
        ok = False
    if not ok:
        if prev is None:
            os.unlink(path)
        else:
            with open(path, "w", encoding="utf-8") as f:
                f.write(prev)
        return False
    return True
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_setup.TestWritePreserving -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add tools/setup.py tests/test_setup.py
git commit -m "feat(setup): write_toml_preserving — atomic write + doctor self-validate (E5c)"
```

---

## Task 8: Golden-file preservation + external-seam tests

**Files:**
- New: `tests/fixtures/statusline-edited.toml`
- Test: `tests/test_setup.py` (new `TestGoldenPreservation`, `TestExternalSeam` classes)

The headline guarantee (§5.1/§5.2): editing one segment leaves `[palette]`, `[ramp.*]`, `[external]`, the version line, and hand-written comments **byte-for-byte unchanged** — only the one managed line changes. We assert this with a golden fixture that contains hand edits and an `[external]` block.

- [ ] **Step 1: Create the golden fixture**

Write `tests/fixtures/statusline-edited.toml` (a user-customized recipe — uncommented sections, a hand comment, an `[external]` block):

```toml
# version = 1

# my own note: I like cost visible
[segments]
cost = false          # 🪙 session cost in USD            (OFF by default)
memory = true         # 🧮 status-line process memory (RSS)

[git]
worktree = false

[palette]
RED = "38;5;196"      # hand-tuned brighter red
BLUE = "38;5;33"

[ramp.context]
10 = "WHITE"
50 = "RED+bold"
inf = "MAGENTA_DARK+bold"

[external]
ttl = 60
dir = "~/.config/ai-kit/segments"
```

- [ ] **Step 2: Write the failing test**

```python
EDITED_RECIPE = os.path.join(FIXTURE_DIR, "statusline-edited.toml")


def _diff_lines(a, b):
    al, bl = a.splitlines(), b.splitlines()
    return [(i, x, y) for i, (x, y) in enumerate(zip(al, bl)) if x != y] + \
           [("len", len(al), len(bl))] if len(al) != len(bl) else \
           [(i, x, y) for i, (x, y) in enumerate(zip(al, bl)) if x != y]


class TestGoldenPreservation(unittest.TestCase):
    def test_one_segment_toggle_changes_only_that_line(self):
        with open(EDITED_RECIPE) as f:
            before = f.read()
        after = setup.patch_segments(before, {"cost": True})
        diffs = _diff_lines(before, after)
        self.assertEqual(len(diffs), 1, diffs)               # exactly one line changed
        _, old, new = diffs[0]
        self.assertIn("cost = false", old)
        self.assertIn("cost = true", new)
        # palette / ramp / external / version / comment all intact
        for marker in ('RED = "38;5;196"', "hand-tuned brighter red",
                       "[ramp.context]", "[external]", "# version = 1",
                       "my own note"):
            self.assertIn(marker, after)

    def test_palette_and_ramp_blocks_byte_for_byte(self):
        with open(EDITED_RECIPE) as f:
            before = f.read()
        after = setup.patch_segments(before, {"memory": False})
        for block in ("[palette]\nRED = \"38;5;196\"      # hand-tuned brighter red\n"
                      "BLUE = \"38;5;33\"\n",
                      "[ramp.context]\n10 = \"WHITE\"\n50 = \"RED+bold\"\n"
                      "inf = \"MAGENTA_DARK+bold\"\n"):
            self.assertIn(block, after)


class TestExternalSeam(unittest.TestCase):
    def test_external_block_survives_segment_patch(self):
        with open(EDITED_RECIPE) as f:
            before = f.read()
        after = setup.patch_segments(before, {"cost": True})
        self.assertIn("[external]\nttl = 60\n"
                      'dir = "~/.config/ai-kit/segments"\n', after)

    def test_external_block_survives_layout_patch(self):
        with open(EDITED_RECIPE) as f:
            before = f.read()
        after = setup.patch_layout(before, [{"min_rows": 0, "segments": ["path"]}])
        self.assertIn("[external]\nttl = 60\n", after)

    def test_external_block_survives_worktree_patch(self):
        with open(EDITED_RECIPE) as f:
            before = f.read()
        after = setup.patch_git_worktree(before, True)
        self.assertIn("[external]\nttl = 60\n", after)
        self.assertIn("worktree = true", after)
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python3 -m unittest tests.test_setup.TestGoldenPreservation tests.test_setup.TestExternalSeam -v`
Expected: FAIL initially (fixture missing) → after Step 1, run again; if any patch function over-reaches it FAILS here. (These tests are the acceptance gate for Tasks 4–6; fix the patch functions if they fail.)

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_setup.TestGoldenPreservation tests.test_setup.TestExternalSeam -v`
Expected: PASS (5 tests). The patch functions from Tasks 4–6 should already satisfy these; if not, the bug is in those functions, not the tests.

- [ ] **Step 5: Commit**

```bash
git add tests/fixtures/statusline-edited.toml tests/test_setup.py
git commit -m "test(setup): golden-file preservation + external-seam guarantees (E5c)"
```

---

## Task 9: `run_statusline_wizard` — the interactive loop (replaces E5b stub)

**Files:**
- Modify: `tools/setup.py` (replace the E5b `run_statusline_wizard` stub; add small prompt helpers if needed)
- Test: `tests/test_setup.py` (new `TestWizardLoop` class)

The real wizard. It reads the current state (`current_segments`, `current_layout`, worktree from `read_toml`), shows a numbered segment list with `[x]`/`[ ]` markers (accent name when on, dim when off) + the one-line note, shows the live preview, and loops on plain-stdin commands:

- `<n>` — toggle segment number `n`.
- `move <seg> up|down` — reorder within its line.
- `move <seg> line <n>` — move `<seg>` to line `n` (1-based), appended at its end.
- `worktree` — toggle the `[git] worktree` knob.
- `p` — re-print the live preview.
- `s` — save (write back via the three patch functions + `write_toml_preserving`), then continue.
- `q` — quit (save if dirty), print the TOML path + concrete doctor command + "edit colors/ramps by hand here".

To keep it testable without a TTY, factor the **pure** state machine into `_apply_wizard_command(state, cmd)` returning a new state (or an error string), and keep the I/O loop thin. `state` is a dict `{"segments": {...}, "layout": [...], "worktree": bool, "dirty": bool}`. Tests drive `_apply_wizard_command`; the loop itself is exercised by a scripted-input integration test.

- [ ] **Step 1: Write the failing test**

```python
class TestWizardLoop(unittest.TestCase):
    def _state(self):
        return {"segments": dict(setup.SEGMENT_DEFAULTS),
                "layout": [{"min_rows": 0, "segments": ["path", "branch", "dirty"]},
                           {"min_rows": 20, "segments": ["model", "clock"]}],
                "worktree": False, "dirty": False}

    def test_toggle_by_number_flips_segment(self):
        st = self._state()
        order = sorted(st["segments"])          # numbering is sorted-key order
        idx = order.index("cost") + 1
        st2, err = setup._apply_wizard_command(st, str(idx))
        self.assertIsNone(err)
        self.assertTrue(st2["segments"]["cost"])
        self.assertTrue(st2["dirty"])

    def test_move_up_reorders_within_line(self):
        st, err = setup._apply_wizard_command(self._state(), "move branch up")
        self.assertIsNone(err)
        self.assertEqual(st["layout"][0]["segments"][:2], ["branch", "path"])

    def test_move_down_reorders_within_line(self):
        st, err = setup._apply_wizard_command(self._state(), "move path down")
        self.assertIsNone(err)
        self.assertEqual(st["layout"][0]["segments"][:2], ["branch", "path"])

    def test_move_across_lines(self):
        st, err = setup._apply_wizard_command(self._state(), "move clock line 1")
        self.assertIsNone(err)
        self.assertIn("clock", st["layout"][0]["segments"])
        self.assertNotIn("clock", st["layout"][1]["segments"])

    def test_worktree_toggles(self):
        st, err = setup._apply_wizard_command(self._state(), "worktree")
        self.assertIsNone(err)
        self.assertTrue(st["worktree"])

    def test_unknown_command_returns_error(self):
        st, err = setup._apply_wizard_command(self._state(), "frobnicate")
        self.assertIsNotNone(err)

    def test_move_unknown_segment_errors(self):
        _, err = setup._apply_wizard_command(self._state(), "move nope up")
        self.assertIsNotNone(err)

    def test_save_writes_only_diff_from_recipe(self):
        # Integration: a save against the shipped recipe writes a valid file that
        # toggles cost on and preserves the palette section.
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "statusline.toml")
            with open(SAMPLE_RECIPE) as f:
                original = f.read()
            with open(path, "w") as f:
                f.write(original)
            status_line = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), "tools", "status-line.py")
            ok = setup.save_statusline_config(
                path, {"cost": True}, None, None, status_line)
            self.assertTrue(ok)
            import tomllib
            with open(path, "rb") as f:
                parsed = tomllib.load(f)
            self.assertTrue(parsed["segments"]["cost"])
            with open(path) as f:
                self.assertIn("# [palette]", f.read())   # palette comments intact
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_setup.TestWizardLoop -v`
Expected: FAIL — `AttributeError: ... '_apply_wizard_command'`.

- [ ] **Step 3: Write the implementation**

Replace the E5b `run_statusline_wizard` stub and add the pure helpers:

```python
def _segment_changes_vs_recipe(path, segments):
    """The {key: bool} subset of `segments` that DIFFERS from what `path` currently
    resolves to — the minimal set of segment keys to patch (key granularity)."""
    current = current_segments(path)
    return {k: v for k, v in segments.items() if current.get(k) != v}


def save_statusline_config(path, seg_changes, layout, worktree, status_line):
    """Apply the managed edits to the file at `path` via surgical text patches,
    then atomically write + doctor-validate. `seg_changes` is the minimal changed
    {key: bool}; `layout` is None (unchanged) or the full list of line dicts;
    `worktree` is None (unchanged) or a bool. Returns True on success."""
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    if seg_changes:
        text = patch_segments(text, seg_changes)
    if layout is not None:
        text = patch_layout(text, layout)
    if worktree is not None:
        text = patch_git_worktree(text, worktree)
    return write_toml_preserving(path, text, status_line)


def _find_line(layout, seg):
    for li, row in enumerate(layout):
        if seg in row["segments"]:
            return li, row["segments"].index(seg)
    return None, None


def _apply_wizard_command(state, cmd):
    """Pure state transition for one wizard command. Returns (new_state, error):
    on success error is None; on a bad command new_state is `state` unchanged and
    error is a human message. Recognized: a segment number, `move <seg> up|down`,
    `move <seg> line <n>`, `worktree`."""
    import copy
    cmd = cmd.strip()
    st = copy.deepcopy(state)
    order = sorted(st["segments"])
    if cmd.isdigit():
        n = int(cmd)
        if not (1 <= n <= len(order)):
            return state, f"no segment #{n}"
        key = order[n - 1]
        st["segments"][key] = not st["segments"][key]
        st["dirty"] = True
        return st, None
    if cmd == "worktree":
        st["worktree"] = not st["worktree"]
        st["dirty"] = True
        return st, None
    parts = cmd.split()
    if len(parts) >= 3 and parts[0] == "move":
        seg = parts[1]
        li, pos = _find_line(st["layout"], seg)
        if li is None:
            return state, f"segment '{seg}' is not in the layout"
        if parts[2] == "up" and pos > 0:
            row = st["layout"][li]["segments"]
            row[pos - 1], row[pos] = row[pos], row[pos - 1]
            st["dirty"] = True
            return st, None
        if parts[2] == "down" and pos < len(st["layout"][li]["segments"]) - 1:
            row = st["layout"][li]["segments"]
            row[pos + 1], row[pos] = row[pos], row[pos + 1]
            st["dirty"] = True
            return st, None
        if parts[2] == "line" and len(parts) == 4 and parts[3].isdigit():
            dst = int(parts[3]) - 1
            if not (0 <= dst < len(st["layout"])):
                return state, f"no line #{parts[3]}"
            st["layout"][li]["segments"].remove(seg)
            st["layout"][dst]["segments"].append(seg)
            st["dirty"] = True
            return st, None
        return state, f"can't move '{seg}' {' '.join(parts[2:])}"
    return state, f"unknown command: {cmd!r}"


def _print_segments(tty, state):
    """Render the numbered segment list with [x]/[ ] + accent/dim + note."""
    accent, dim, reset = "\033[36m", "\033[90m", "\033[0m"
    for i, key in enumerate(sorted(state["segments"]), start=1):
        on = state["segments"][key]
        box = "[x]" if on else "[ ]"
        color = accent if on else dim
        note = _SEGMENT_NOTES.get(key, "")
        print(f"  {i:2}. {box} {color}{key}{reset}  {dim}{note}{reset}", file=tty)


def run_statusline_wizard(paths, tty, dry):
    """Interactive status-line editor: toggle segments, reorder/move across lines,
    flip the [git] worktree knob, live-preview after each change, write back via
    surgical patch + doctor self-validate. Replaces the E5b stub."""
    cfg = paths.config_toml
    raw = read_toml(cfg)
    state = {
        "segments": current_segments(cfg),
        "layout": current_layout(cfg),
        "worktree": bool((raw.get("git") or {}).get("worktree", False)),
        "dirty": False,
    }
    with open(paths.sample_input if hasattr(paths, "sample_input")
              else _sample_input_path()) as f:
        sample_json = f.read()

    def show_preview():
        env = {}
        if state["worktree"]:
            env["CC_AI_KIT_GIT_WORKTREE"] = "1"
        out = render_preview(paths.status_line, state["segments"], sample_json, env)
        print("\n  ── live preview ──", file=tty)
        print(out or "  (preview unavailable)", file=tty)

    print("\nStatus-line configuration", file=tty)
    while True:
        _print_segments(tty, state)
        print(f"  worktree detection: "
              f"{'on' if state['worktree'] else 'off'} (type 'worktree' to toggle)",
              file=tty)
        show_preview()
        print("\n  commands: <n> toggle · move <seg> up|down · move <seg> line <n>"
              " · worktree · p preview · s save · q quit", file=tty)
        tty.write("  > ")
        tty.flush()
        cmd = tty.readline()
        if not cmd:
            cmd = "q"
        cmd = cmd.strip()
        if cmd in ("q", "quit", ""):
            break
        if cmd in ("p", "preview"):
            continue
        if cmd in ("s", "save"):
            _save_and_report(paths, state, tty, dry)
            state["dirty"] = False
            continue
        new_state, err = _apply_wizard_command(state, cmd)
        if err:
            print(f"  ! {err}", file=tty)
        else:
            state = new_state

    if state["dirty"]:
        _save_and_report(paths, state, tty, dry)
    else:
        _print_closing(paths, tty)


def _save_and_report(paths, state, tty, dry):
    if dry:
        print("  [dry-run] would write status-line config — no changes made",
              file=tty)
        _print_closing(paths, tty)
        return
    seg_changes = _segment_changes_vs_recipe(paths.config_toml, state["segments"])
    layout = state["layout"] if state["layout"] != current_layout(paths.config_toml) \
        else None
    raw = read_toml(paths.config_toml)
    cur_wt = bool((raw.get("git") or {}).get("worktree", False))
    worktree = state["worktree"] if state["worktree"] != cur_wt else None
    if not (seg_changes or layout is not None or worktree is not None):
        _print_closing(paths, tty)
        return
    ok = save_statusline_config(paths.config_toml, seg_changes, layout, worktree,
                                paths.status_line)
    if ok:
        print("  ✓ saved", file=tty)
    else:
        print("  ! the doctor rejected the change — file left unchanged", file=tty)
    _print_closing(paths, tty)


def _print_closing(paths, tty):
    print(f"\n  config: {paths.config_toml}", file=tty)
    print(f"  edit colors / ramps / palette by hand in that file.", file=tty)
    # _doctor_cmd(paths) is defined in E5b — reuse it; do NOT redefine it here.
    # E5b signature: _doctor_cmd(paths: Paths) -> str
    # E5b call site in cmd_install already uses _doctor_cmd(paths); leave it unchanged.
    print(f"  validate any time:  {_doctor_cmd(paths)}", file=tty)


def _sample_input_path():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "..", "tests", "fixtures", "sample-input.json")
```

> **Note for the implementer:** `_sample_input_path()` resolves the fixture relative to `setup.py`. If E5b's `Paths` namedtuple already carries a `sample_input` field, prefer that; otherwise the fallback above is used. Keep `render_preview`/`save_*`/patch functions as the tested units — the loop is glue.

> **`_doctor_cmd` — do NOT redefine in E5c.** E5b already defines `_doctor_cmd(paths: Paths) -> str` (used in `cmd_install`'s closing summary). E5c's `_print_closing` calls `_doctor_cmd(paths)` — the same Paths-accepting function. E5c adds NO new `_doctor_cmd` definition and makes NO changes to E5b's `cmd_install` call site.

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_setup.TestWizardLoop -v`
Expected: PASS (8 tests).

- [ ] **Step 5: Commit**

```bash
git add tools/setup.py tests/test_setup.py
git commit -m "feat(setup): real run_statusline_wizard — toggle/reorder/preview/save (E5c)"
```

---

## Task 10: Wire the wizard into the menu's "Status line" branch

**Files:**
- Modify: `tools/setup.py` (the menu shell E5b created — fill the "Status line" branch to call `run_statusline_wizard`)
- Test: `tests/test_setup.py` (extend an existing menu/dispatch test or add a small `TestMenuWiring`)

E5b ships the two-level menu (configure Skills and/or Status line). E5c fills the Status-line branch so selecting it invokes `run_statusline_wizard(paths, tty, dry)`. Keep this minimal — the branch is a one-liner dispatch; the logic is all in Task 9.

- [ ] **Step 1: Write the failing test**

```python
import io


class TestMenuWiring(unittest.TestCase):
    def test_statusline_branch_invokes_wizard(self):
        """Verify that cmd_install's interactive branch delegates to run_statusline_wizard.

        E5b defines cmd_install(paths, tty, dry) and calls run_statusline_wizard(paths, tty, dry)
        when is_interactive(tty) is True and the user selects the Status-line option.
        E5c wires the real wizard into that call. This test replaces run_statusline_wizard with a
        spy and drives cmd_install through an interactive tty stub to confirm the wizard is reached.
        """
        called = {}
        orig = setup.run_statusline_wizard
        setup.run_statusline_wizard = lambda paths, tty, dry: called.setdefault("ok", True)
        self.addCleanup(lambda: setattr(setup, "run_statusline_wizard", orig))
        paths = setup.resolve_paths(dict(os.environ))
        # Feed a tty that looks interactive to is_interactive() and selects
        # "Status line" (option 2 in the E5b two-option menu) then quits.
        tty = io.StringIO("2\nq\n")
        # cmd_install is the E5b function that owns the menu dispatch.
        setup.cmd_install(paths, tty, dry=True)
        self.assertTrue(called.get("ok"),
                        "run_statusline_wizard was not called — check the Status-line branch in cmd_install")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_setup.TestMenuWiring -v`
Expected: FAIL — `called` dict is empty because E5b's `run_statusline_wizard` is still the stub (it does not set `called["ok"]`).

- [ ] **Step 3: Wire the branch**

In the E5b menu dispatcher, replace the Status-line stub call with:

```python
# Status line branch (E5c):
run_statusline_wizard(paths, tty, dry)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_setup.TestMenuWiring -v`
Expected: PASS.

- [ ] **Step 5: Full suite + commit**

```bash
python3 -m unittest tests.test_setup -v
git add tools/setup.py tests/test_setup.py
git commit -m "feat(setup): wire run_statusline_wizard into the Status-line menu branch (E5c)"
```

---

## Task 11: Phase wrap — full suite, drift check, compact commits

**Files:** none new (verification + history tidy)

- [ ] **Step 1: Run the full setup suite + the renderer suite (unchanged by us)**

Run:
```bash
python3 -m unittest tests.test_setup -v
python3 -m unittest tests.test_status_line -v
```
Expected: all PASS. `status-line.py` is read-only this phase — its suite must stay green.

- [ ] **Step 2: Confirm no recipe drift**

Run: `python3 -m unittest tests.test_setup.TestTomlRead.test_segment_defaults_match_recipe_drift -v`
Expected: PASS — `SEGMENT_DEFAULTS` still mirrors `tools/statusline.toml.sample`. (If `status-line.py`'s `SEGMENTS` changed upstream, update `SEGMENT_DEFAULTS`/`LAYOUT_DEFAULTS` and the recipe together.)

- [ ] **Step 3: Compact the working history by logical unit (per the working agreements)**

Squash the WIP commits into coherent units before closing the phase, e.g.:
- `test(setup): preview fixtures + golden preservation recipe (E5c)`
- `feat(setup): TOML read helpers + render_preview (E5c)`
- `feat(setup): surgical comment-aware TOML patch (segments/layout/worktree) + write-preserving (E5c)`
- `feat(setup): interactive status-line wizard + menu wiring (E5c)`

Use an interactive-free squash (the environment forbids `-i`); reset to the phase base and re-commit grouped, or `git reset --soft` + selective `git add`. Do NOT push.

---

## Self-Review checklist

Map each spec requirement to its task and scan for gaps before declaring done.

**§5 — Status-line wizard surface:**
- [ ] Toggle each segment on/off, `[x]`/`[ ]` + accent-on/dim-off + one-line note → Task 9 (`_print_segments`, `_apply_wizard_command` digit branch); notes from `_SEGMENT_NOTES` (Task 4).
- [ ] Reorder within a line + move across lines (`move <seg> up|down`, `move <seg> line <n>`) → Task 9 (`_apply_wizard_command` move branch).
- [ ] `[git] worktree` knob toggle → Task 9 (`worktree` command) + Task 6 (`patch_git_worktree`).
- [ ] Live preview re-renders after each change via `CC_AI_KIT_SEGMENT_*` + sample JSON, no temp files → Task 3 (`render_preview`) + Task 9 (`show_preview`).
- [ ] Write `[segments]` + `[[line]]` back to the TOML → Tasks 4, 5, 9 (`save_statusline_config`).

**§5.1 — Preservation (merge-not-regenerate, key-granularity):**
- [ ] Key-granularity surgical patch (rewrite the one `key = value` line; append missing key with its doc note) → Task 4 (`patch_segments`, `_append_missing`).
- [ ] `[palette]`, every `[ramp.*]`, comments, `# version` preserved byte-for-byte → Task 8 golden tests gate Tasks 4–6.
- [ ] Self-validate via doctor; refuse to leave a broken file → Task 7 (`write_toml_preserving` reverts on doctor failure).
- [ ] Never overwrite wholesale; only managed keys touched → Tasks 4–6 (text patch, not re-emit) + Task 8 (one-line-diff assertion).

**§5.2 — External-segment seam:**
- [ ] `[external]` block preserved by every patch → Task 8 (`TestExternalSeam`, all three patch functions).
- [ ] Never touch `~/.config/ai-kit/segments/` or `~/.cache/ai-kit/` → out of scope for the patch functions (they touch only `config_toml`); prune behavior lives in E5b. Asserted here only that patches preserve `[external]`.

**§5.3 — Schema migration:** OUT OF SCOPE — no alias table / version stamp / migration engine added. ✅ (confirm nothing of the sort was introduced.)

**Stdlib-only / no tomlkit:**
- [ ] Writes are surgical text patches on raw text; reads use `tomllib`; `subprocess` runs the renderer/doctor. No third-party imports. (`grep -n "import" tools/setup.py` shows only stdlib.)
- [ ] Rationale for rejecting `tomlkit` documented in Architecture section. ✅

**Placeholder / consistency scan:**
- [ ] No `TODO`, `...`, `pass  # stub`, or `NotImplementedError` left in `setup.py` (`grep -nE 'TODO|NotImplementedError|\bpass\b *$|\.\.\.' tools/setup.py`).
- [ ] Names consistent across tasks: `read_toml`, `current_segments`, `current_layout`, `render_preview`, `patch_segments`, `patch_layout`, `patch_git_worktree`, `write_toml_preserving`, `save_statusline_config`, `_apply_wizard_command`, `_segment_changes_vs_recipe`, `run_statusline_wizard`, `SEGMENT_DEFAULTS`, `LAYOUT_DEFAULTS`, `_SEGMENT_NOTES`, `_HEADER_RE`/`_header_name`, `_KEY_RE`.
- [ ] `render_preview(status_line, segments, sample_json, env)` and `write_toml_preserving(path, text, status_line)` signatures match every call site.
- [ ] Test runner is `unittest` (`python3 -m unittest tests.test_setup`), not pytest. ✅
- [ ] The preview/doctor are deterministic in tests (checked-in `sample-input.json`, forced `STATUSLINE_COLS/LINES`). ✅
