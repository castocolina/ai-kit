# E4c External Drop-in Segments — Core Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let a user add a new status-line segment by dropping an executable into a segments directory — discovered, placed, executed (timeout + TTL cache), sanitized, and given the same column-budget contract as a built-in builder — without patching `tools/status-line.py`.

**Architecture:** External providers are modeled as **synthetic builders** inserted into E4a's resolved layout, so the existing `pack_line` packing/priority logic handles them unchanged. New code lives in `tools/status-line.py`: header parsing → discovery → execution/sanitization/caching → config wiring (a new `Config.external` field) → a merged builder map threaded through `render`/`pack_line`/`safe_build`. A cross-platform `python3` sample ships in `examples/segments/`.

**Tech Stack:** Python 3.11+ stdlib only (`subprocess`, `os`, `time`, `re`, `json`, `tomllib`). Tests: `unittest` loaded via `importlib` (matching `tests/test_status_line.py`), run with `pytest`.

**Scope:** This plan delivers the fully-working feature usable by editing `~/.config/ai-kit/statusline.toml` and dropping files in `~/.config/ai-kit/segments/`. The **E5 setup-wizard integration** (discovery listing + opt-in sample copy) is a separate follow-up plan: `2026-06-19-e4c-external-segments-wizard.md`.

**Reference:** spec `docs/superpowers/specs/2026-06-19-e4c-statusline-external-segments-design.md`.

---

## File Structure

| File | Responsibility | Action |
|---|---|---|
| `tools/status-line.py` | discovery, execution, sanitization, caching, config wiring, placement, builder threading, CLI surface | Modify |
| `tools/statusline.toml.sample` | add commented `[external]` recipe block | Modify |
| `examples/segments/sysmem` | shipped cross-platform system-available-memory sample provider | Create |
| `tests/test_external_segments.py` | all new unit + integration tests | Create |
| `README.md` | external-segment header grammar, input contract, columns handling, trust model | Modify |

### New objects/functions in `status-line.py` (names are fixed — used across tasks)

- `ExtSpec = namedtuple("ExtSpec", "id path line position timeout ttl cache_path")`
- `position` is a 2-tuple `(kind, ref)`, `kind ∈ {"start","end","after","before"}`, `ref` a segment key or `""`.
- `parse_segment_header(lines) -> dict | None`
- `_segments_dir(file_external, env) -> str`
- `_segments_cache_dir(env) -> str`
- `discover_external(directory, default_ttl, env) -> list[ExtSpec]`
- `_position_str(position) -> str`
- `_truncate_visible(s, avail) -> str`
- `_sanitize_external(text, avail) -> str | None`
- `_run_provider(spec, data, avail) -> str | None`
- `_cache_read(spec) -> str | None` / `_cache_write(spec, text) -> None`
- `run_external(spec, data, avail) -> str | None`
- `_resolve_external(raw, env) -> tuple[str, int]`  (dir, ttl)
- `_place_external(layout, specs) -> tuple[list[Line], list[ExtSpec]]`
- `make_external_builder(spec) -> callable`
- `_builders_for(cfg) -> dict`
- `Config` gains a trailing `external` field (default `None`, treated as `[]`).

---

## Phase 1 — Header parsing & discovery

### Task 1: `ExtSpec` + `parse_segment_header`

**Files:**
- Create: `tests/test_external_segments.py`
- Modify: `tools/status-line.py` (add after the `INF = float("inf")` block, ~line 259)

- [ ] **Step 1: Write the failing test**

Create `tests/test_external_segments.py`:

```python
import importlib.util
import json
import os
import stat
import sys
import tempfile
import time
import unittest

_HERE = os.path.dirname(__file__)
_MODULE_PATH = os.path.join(_HERE, "..", "tools", "status-line.py")


def load_module():
    spec = importlib.util.spec_from_file_location("status_line", _MODULE_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


sl = load_module()


def write_script(directory, name, body, executable=True):
    """Write a provider script and (by default) chmod +x it. Returns its path."""
    path = os.path.join(directory, name)
    with open(path, "w", encoding="utf-8") as f:
        f.write(body)
    if executable:
        os.chmod(path, os.stat(path).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return path


class TestParseHeader(unittest.TestCase):
    def test_full_header(self):
        lines = ["#!/bin/sh\n",
                 "# ai-kit-segment: line=2 after=clock id=aws timeout=3 ttl=30\n",
                 "echo hi\n"]
        fields = sl.parse_segment_header(lines)
        self.assertEqual(fields["position"], ("after", "clock"))
        self.assertEqual(fields["line"], "2")
        self.assertEqual(fields["id"], "aws")
        self.assertEqual(fields["timeout"], "3")
        self.assertEqual(fields["ttl"], "30")

    def test_bare_start_end(self):
        self.assertEqual(sl.parse_segment_header(["# ai-kit-segment: start\n"])["position"],
                         ("start", ""))
        self.assertEqual(sl.parse_segment_header(["# ai-kit-segment: end\n"])["position"],
                         ("end", ""))

    def test_no_header_returns_none(self):
        self.assertIsNone(sl.parse_segment_header(["#!/bin/sh\n", "echo hi\n"]))

    def test_header_present_but_empty_fields(self):
        self.assertEqual(sl.parse_segment_header(["# ai-kit-segment:\n"]), {})


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_external_segments.py::TestParseHeader -v`
Expected: FAIL — `AttributeError: module 'status_line' has no attribute 'parse_segment_header'`

- [ ] **Step 3: Add `ExtSpec` and `parse_segment_header`**

In `tools/status-line.py`, immediately after the `INF = float("inf")` line (~259), add:

```python

# ═══ External drop-in segments (E4c) ═════════════════════════════════════════
# A provider is an executable in the segments dir. Its first 10 lines may carry
#   # ai-kit-segment: line=<N> (after=<key>|before=<key>|start|end) [id=<slug>] [timeout=<s>] [ttl=<s>]
# It is modeled as a synthetic builder inserted into the resolved layout, so the
# existing packer handles placement/priority/overflow unchanged.
ExtSpec = namedtuple("ExtSpec", "id path line position timeout ttl cache_path")

_SEG_HEADER_RE = re.compile(r"^#\s*ai-kit-segment:\s*(.*?)\s*$")


def parse_segment_header(lines):
    """Parse the `# ai-kit-segment:` header from a file's first lines.

    Returns a dict of the raw string fields present (`line`/`id`/`timeout`/`ttl`
    as strings, `position` as a (kind, ref) tuple) — possibly empty if the header
    line exists but lists nothing. Returns None when no header line is present."""
    for ln in lines:
        m = _SEG_HEADER_RE.match(ln)
        if m is None:
            continue
        fields = {}
        for tok in m.group(1).split():
            if tok in ("start", "end"):
                fields["position"] = (tok, "")
            elif "=" in tok:
                k, v = tok.split("=", 1)
                if k in ("after", "before"):
                    fields["position"] = (k, v)
                elif k in ("line", "id", "timeout", "ttl"):
                    fields[k] = v
        return fields
    return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_external_segments.py::TestParseHeader -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add tests/test_external_segments.py tools/status-line.py
git commit -m "feat(e4c): ExtSpec + ai-kit-segment header parser"
```

---

### Task 2: `discover_external` + directory resolution

**Files:**
- Modify: `tools/status-line.py` (after `parse_segment_header`)
- Test: `tests/test_external_segments.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_external_segments.py`:

```python
class TestDiscover(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.addCleanup(lambda: __import__("shutil").rmtree(self.dir, ignore_errors=True))
        self.env = {"XDG_CACHE_HOME": os.path.join(self.dir, "cache")}

    def test_executable_with_header_is_discovered(self):
        write_script(self.dir, "aws.sh",
                     "#!/bin/sh\n# ai-kit-segment: line=2 after=clock id=aws ttl=30\necho hi\n")
        specs = sl.discover_external(self.dir, default_ttl=10, env=self.env)
        self.assertEqual(len(specs), 1)
        s = specs[0]
        self.assertEqual(s.id, "aws")
        self.assertEqual(s.position, ("after", "clock"))
        self.assertEqual(s.line, 2)
        self.assertEqual(s.ttl, 30)
        self.assertEqual(s.timeout, 2.0)
        self.assertTrue(s.cache_path.endswith(os.path.join("ai-kit", "segments", "aws")))

    def test_no_header_uses_defaults_and_stem_id(self):
        write_script(self.dir, "clockx", "#!/bin/sh\necho hi\n")
        specs = sl.discover_external(self.dir, default_ttl=7, env=self.env)
        self.assertEqual(specs[0].id, "clockx")
        self.assertEqual(specs[0].position, ("end", ""))
        self.assertEqual(specs[0].line, 0)        # 0 => "last row", resolved at placement
        self.assertEqual(specs[0].ttl, 7)

    def test_non_executable_skipped(self):
        write_script(self.dir, "noexec", "#!/bin/sh\necho hi\n", executable=False)
        self.assertEqual(sl.discover_external(self.dir, 10, self.env), [])

    def test_sorted_by_filename_then_id(self):
        write_script(self.dir, "b.sh", "#!/bin/sh\n# ai-kit-segment: id=zeta\necho\n")
        write_script(self.dir, "a.sh", "#!/bin/sh\n# ai-kit-segment: id=omega\necho\n")
        ids = [s.id for s in sl.discover_external(self.dir, 10, self.env)]
        self.assertEqual(ids, ["omega", "zeta"])   # a.sh before b.sh

    def test_missing_dir_returns_empty(self):
        self.assertEqual(sl.discover_external("/no/such/dir", 10, self.env), [])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_external_segments.py::TestDiscover -v`
Expected: FAIL — `AttributeError: ... 'discover_external'`

- [ ] **Step 3: Add directory resolvers + `discover_external`**

After `parse_segment_header`, add:

```python
def _segments_cache_dir(env):
    """${XDG_CACHE_HOME:-$HOME/.cache}/ai-kit/segments — per-provider output cache."""
    base = env.get("XDG_CACHE_HOME") or os.path.join(env.get("HOME", ""), ".cache")
    return os.path.join(base, "ai-kit", "segments")


def _segments_dir(file_external, env):
    """Resolve the providers directory: CC_AI_KIT_SEGMENTS_DIR > [external].dir >
    ${XDG_CONFIG_HOME:-$HOME/.config}/ai-kit/segments."""
    d = env.get("CC_AI_KIT_SEGMENTS_DIR") or (file_external or {}).get("dir")
    if d:
        return os.path.expanduser(d)
    base = env.get("XDG_CONFIG_HOME") or os.path.join(env.get("HOME", ""), ".config")
    return os.path.join(base, "ai-kit", "segments")


def discover_external(directory, default_ttl, env):
    """Scan `directory` for executable providers and return a list of ExtSpec,
    sorted by (filename, id). Non-executable files are skipped with a dim warning.
    A file with no header still loads with all defaults (line=0 => last row at
    placement, position=end, id=stem, timeout=2s, ttl=default_ttl)."""
    if not directory or not os.path.isdir(directory):
        return []
    cache_dir = _segments_cache_dir(env)
    specs = []
    for name in sorted(os.listdir(directory)):
        path = os.path.join(directory, name)
        if not os.path.isfile(path):
            continue
        if not os.access(path, os.X_OK):
            print(f"{_DIM}status-line: segment '{name}' not executable — skipped{RESET}",
                  file=sys.stderr)
            continue
        try:
            with open(path, encoding="utf-8", errors="replace") as f:
                head = [f.readline() for _ in range(10)]
        except OSError:
            continue
        fields = parse_segment_header(head) or {}
        sid = fields.get("id") or os.path.splitext(name)[0]
        try:
            timeout = float(fields.get("timeout", 2))
        except (TypeError, ValueError):
            timeout = 2.0
        try:
            ttl = int(fields.get("ttl", default_ttl))
        except (TypeError, ValueError):
            ttl = default_ttl
        try:
            line = int(fields["line"]) if "line" in fields else 0
        except (TypeError, ValueError):
            line = 0
        specs.append(ExtSpec(
            id=sid, path=path, line=line,
            position=fields.get("position", ("end", "")),
            timeout=timeout, ttl=ttl,
            cache_path=os.path.join(cache_dir, sid)))
    specs.sort(key=lambda s: (os.path.basename(s.path), s.id))
    return specs
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_external_segments.py::TestDiscover -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add tools/status-line.py tests/test_external_segments.py
git commit -m "feat(e4c): provider discovery + segments/cache dir resolution"
```

---

## Phase 2 — Execution, sanitization, caching

### Task 3: `_truncate_visible` + `_sanitize_external`

**Files:**
- Modify: `tools/status-line.py` (after `discover_external`)
- Test: `tests/test_external_segments.py`

- [ ] **Step 1: Write the failing test**

Append:

```python
class TestSanitize(unittest.TestCase):
    def test_first_non_empty_line(self):
        self.assertEqual(sl._sanitize_external("\n\n  hello \n second\n", 40), "  hello")

    def test_keeps_sgr_strips_other_csi(self):
        # \033[33m kept (SGR), \033[2J (clear) and cursor move \033[1A stripped
        out = sl._sanitize_external("\033[33mhi\033[0m\033[2J\033[1A", 40)
        self.assertEqual(out, "\033[33mhi\033[0m")

    def test_strips_osc_and_control_chars(self):
        out = sl._sanitize_external("\033]0;title\007ab\tc", 40)
        self.assertEqual(out, "abc")

    def test_truncates_to_avail_and_resets(self):
        out = sl._sanitize_external("\033[33mabcdef\033[0m", 3)
        self.assertEqual(sl.visible_width(out), 3)
        self.assertTrue(out.endswith(sl.RESET))

    def test_empty_after_sanitize_returns_none(self):
        self.assertIsNone(sl._sanitize_external("\033[2J\n", 40))
        self.assertIsNone(sl._sanitize_external("   \n", 40))

    def test_avail_zero_returns_none(self):
        self.assertIsNone(sl._sanitize_external("hi", 0))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_external_segments.py::TestSanitize -v`
Expected: FAIL — `AttributeError: ... '_sanitize_external'`

- [ ] **Step 3: Implement truncation + sanitization**

After `discover_external`, add:

```python
_SGR_SEQ = re.compile(r"\x1b\[[0-9;]*m")           # an SGR color/style escape
_CSI_SEQ = re.compile(r"\x1b\[[0-9;?]*([A-Za-z])")  # any CSI; group = final byte
_OSC_SEQ = re.compile(r"\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)")
_STRAY_ESC = re.compile(r"\x1b(?!\[[0-9;]*m)")      # ESC not starting an SGR
_C0_CTRL = re.compile(r"[\x00-\x08\x0b-\x1a\x1c-\x1f\x7f]")  # controls except ESC(0x1b)


def _truncate_visible(s, avail):
    """Cut s to at most `avail` visible cells, preserving zero-width SGR escapes,
    appending RESET if any SGR was emitted. avail <= 0 -> ''."""
    if avail <= 0:
        return ""
    out, width, i, n, saw_sgr = [], 0, 0, len(s), False
    while i < n:
        m = _SGR_SEQ.match(s, i)
        if m:
            out.append(m.group(0))
            saw_sgr = True
            i = m.end()
            continue
        w = char_width(s[i])
        if width + w > avail:
            break
        out.append(s[i])
        width += w
        i += 1
    res = "".join(out)
    if saw_sgr and not res.endswith(RESET):
        res += RESET
    return res


def _sanitize_external(text, avail):
    """First non-empty line of `text`, SGR colors kept, every other control/CSI/OSC
    sequence stripped, width-truncated to `avail`. None if nothing renderable."""
    line = next((c for c in text.splitlines() if c.strip()), "")
    if not line:
        return None
    line = _OSC_SEQ.sub("", line)
    line = _CSI_SEQ.sub(lambda m: m.group(0) if m.group(1) == "m" else "", line)
    line = _STRAY_ESC.sub("", line)
    line = _C0_CTRL.sub("", line)
    if not line.strip():
        return None
    return _truncate_visible(line, avail) or None
```

Note: `test_first_non_empty_line` expects the trailing space trimmed only by `splitlines`? It is not — `"  hello "` keeps its spaces; the expected value is `"  hello"`. Adjust the test OR rstrip. Decision: rstrip trailing whitespace (leading kept for alignment). Update `_sanitize_external` to `line = line.rstrip()` right after selecting the first non-empty line:

```python
    line = next((c for c in text.splitlines() if c.strip()), "").rstrip()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_external_segments.py::TestSanitize -v`
Expected: PASS (6 tests)

- [ ] **Step 5: Commit**

```bash
git add tools/status-line.py tests/test_external_segments.py
git commit -m "feat(e4c): output sanitization (SGR-only) + width truncation"
```

---

### Task 4: `run_external` — execution + TTL cache

**Files:**
- Modify: `tools/status-line.py` (after `_sanitize_external`)
- Test: `tests/test_external_segments.py`

- [ ] **Step 1: Write the failing test**

Append:

```python
class TestRunExternal(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.cache = tempfile.mkdtemp()
        import shutil
        self.addCleanup(lambda: shutil.rmtree(self.dir, ignore_errors=True))
        self.addCleanup(lambda: shutil.rmtree(self.cache, ignore_errors=True))

    def _spec(self, path, ttl=10, timeout=2.0):
        return sl.ExtSpec(id="t", path=path, line=1, position=("end", ""),
                          timeout=timeout, ttl=ttl,
                          cache_path=os.path.join(self.cache, "t"))

    def _data(self):
        return {"raw": {"workspace": {"current_dir": self.dir}}, "work_dir": self.dir}

    def test_runs_and_returns_first_line(self):
        p = write_script(self.dir, "p", "#!/bin/sh\necho '\033[33mhi\033[0m'\n")
        self.assertEqual(sl.run_external(self._spec(p), self._data(), 40),
                         "\033[33mhi\033[0m")

    def test_receives_cols_via_env(self):
        p = write_script(self.dir, "p", '#!/bin/sh\necho "cols=$AI_KIT_SEGMENT_COLS"\n')
        self.assertEqual(sl.run_external(self._spec(p), self._data(), 17), "cols=17")

    def test_receives_segment_block_on_stdin(self):
        p = write_script(self.dir, "p",
                         '#!/usr/bin/env python3\n'
                         'import sys, json\n'
                         'd = json.load(sys.stdin)\n'
                         'print(d["segment"]["avail_cols"], d["segment"]["id"])\n')
        self.assertEqual(sl.run_external(self._spec(p), self._data(), 9), "9 t")

    def test_runs_in_workspace_dir(self):
        p = write_script(self.dir, "p", "#!/bin/sh\npwd\n")
        out = sl.run_external(self._spec(p), self._data(), 200)
        self.assertEqual(os.path.realpath(out), os.path.realpath(self.dir))

    def test_nonzero_exit_returns_none(self):
        p = write_script(self.dir, "p", "#!/bin/sh\necho x\nexit 1\n")
        self.assertIsNone(sl.run_external(self._spec(p), self._data(), 40))

    def test_timeout_returns_none(self):
        p = write_script(self.dir, "p", "#!/bin/sh\nsleep 5\n")
        self.assertIsNone(sl.run_external(self._spec(p, timeout=0.3), self._data(), 40))

    def test_empty_output_returns_none(self):
        p = write_script(self.dir, "p", "#!/bin/sh\nexit 0\n")
        self.assertIsNone(sl.run_external(self._spec(p), self._data(), 40))

    def test_caches_within_ttl(self):
        # writes a counter file each run; second call within ttl must not re-run
        counter = os.path.join(self.dir, "n")
        p = write_script(self.dir, "p",
                         f'#!/bin/sh\nprintf x >> "{counter}"\necho hi\n')
        spec = self._spec(p, ttl=100)
        self.assertEqual(sl.run_external(spec, self._data(), 40), "hi")
        self.assertEqual(sl.run_external(spec, self._data(), 40), "hi")
        with open(counter) as f:
            self.assertEqual(f.read(), "x")        # ran exactly once

    def test_ttl_zero_always_reruns(self):
        counter = os.path.join(self.dir, "n")
        p = write_script(self.dir, "p",
                         f'#!/bin/sh\nprintf x >> "{counter}"\necho hi\n')
        spec = self._spec(p, ttl=0)
        sl.run_external(spec, self._data(), 40)
        sl.run_external(spec, self._data(), 40)
        with open(counter) as f:
            self.assertEqual(f.read(), "xx")       # ran twice
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_external_segments.py::TestRunExternal -v`
Expected: FAIL — `AttributeError: ... 'run_external'`

- [ ] **Step 3: Implement caching + execution**

After `_sanitize_external`, add:

```python
def _position_str(position):
    """('after','clock') -> 'after:clock'; ('end','') -> 'end'."""
    kind, ref = position
    return f"{kind}:{ref}" if ref else kind


def _cache_read(spec):
    """Cached raw output line if present and younger than ttl, else None.
    ttl <= 0 always misses (forces a re-run every render)."""
    if spec.ttl <= 0:
        return None
    try:
        age = time.time() - os.stat(spec.cache_path).st_mtime
    except OSError:
        return None
    if age >= spec.ttl:
        return None
    try:
        with open(spec.cache_path, encoding="utf-8") as f:
            return f.read()
    except OSError:
        return None


def _cache_write(spec, text):
    """Best-effort: persist raw output. Unwritable cache dir -> silently skip."""
    try:
        os.makedirs(os.path.dirname(spec.cache_path), exist_ok=True)
        with open(spec.cache_path, "w", encoding="utf-8") as f:
            f.write(text)
    except OSError:
        pass


def _run_provider(spec, data, avail):
    """Spawn the provider with the status JSON + segment block on stdin, the
    AI_KIT_SEGMENT_* env mirror, and cwd = workspace dir. Returns the raw first
    non-empty stdout line, or None on timeout / non-zero exit / no output."""
    pos = _position_str(spec.position)
    payload = json.dumps({**(data.get("raw") or {}),
                          "segment": {"id": spec.id, "avail_cols": avail,
                                      "line": spec.line, "position": pos}})
    env = dict(os.environ)
    env.update({"AI_KIT_SEGMENT_COLS": str(avail), "AI_KIT_SEGMENT_ID": spec.id,
                "AI_KIT_SEGMENT_LINE": str(spec.line), "AI_KIT_SEGMENT_POSITION": pos})
    try:
        proc = subprocess.run(
            [spec.path], input=payload, capture_output=True, text=True,
            timeout=spec.timeout, cwd=data.get("work_dir") or ".", env=env)
    except (subprocess.TimeoutExpired, OSError):
        return None
    if proc.returncode != 0:
        return None
    for line in proc.stdout.splitlines():
        if line.strip():
            return line
    return None


def run_external(spec, data, avail):
    """TTL-cached, timeout-bounded provider invocation. Returns the sanitized,
    width-fitted segment string, or None to omit the segment."""
    raw_line = _cache_read(spec)
    if raw_line is None:
        raw_line = _run_provider(spec, data, avail)
        if raw_line is None:
            return None
        _cache_write(spec, raw_line)
    return _sanitize_external(raw_line, avail)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_external_segments.py::TestRunExternal -v`
Expected: PASS (9 tests)

- [ ] **Step 5: Commit**

```bash
git add tools/status-line.py tests/test_external_segments.py
git commit -m "feat(e4c): provider execution + TTL cache (run_external)"
```

---

## Phase 3 — Config wiring & placement

### Task 5: Extend `Config` + `_resolve_external`

**Files:**
- Modify: `tools/status-line.py` (`Config` def ~78; add `_resolve_external` near `load_config`)
- Test: `tests/test_external_segments.py`

- [ ] **Step 1: Write the failing test**

Append:

```python
class TestResolveExternal(unittest.TestCase):
    def test_config_has_external_default_none(self):
        cfg = sl.default_config()
        self.assertIsNone(cfg.external)

    def test_defaults(self):
        d, ttl = sl._resolve_external({}, {})
        self.assertEqual(ttl, 10)
        self.assertTrue(d.endswith(os.path.join("ai-kit", "segments")))

    def test_file_overrides(self):
        raw = {"external": {"ttl": 25, "dir": "/tmp/segs"}}
        d, ttl = sl._resolve_external(raw, {})
        self.assertEqual((d, ttl), ("/tmp/segs", 25))

    def test_env_wins(self):
        raw = {"external": {"ttl": 25, "dir": "/tmp/segs"}}
        env = {"CC_AI_KIT_SEGMENTS_DIR": "/env/segs", "CC_AI_KIT_EXTERNAL_TTL": "3"}
        d, ttl = sl._resolve_external(raw, env)
        self.assertEqual((d, ttl), ("/env/segs", 3))

    def test_bad_env_ttl_falls_back_to_file(self):
        raw = {"external": {"ttl": 25}}
        d, ttl = sl._resolve_external(raw, {"CC_AI_KIT_EXTERNAL_TTL": "notanint"})
        self.assertEqual(ttl, 25)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_external_segments.py::TestResolveExternal -v`
Expected: FAIL — `AttributeError: ... '_resolve_external'` (and `external` field absent)

- [ ] **Step 3a: Add the `external` field to `Config`**

In `tools/status-line.py`, change the `Config` definition (~line 78):

```python
# `git` and `external` default to None so older Config(...) call sites (which
# pass only the original fields) keep working; consumers read git via (cfg.git or
# {}) and external via (cfg.external or []).
Config = namedtuple("Config", "segments layout palette ramps git external",
                    defaults=(None, None))
```

`default_config()` (~line 85) needs no change — it passes the first four fields by keyword, so `git` and `external` both default to `None`. (Confirm `default_config` still omits `git`/`external`; it does.)

- [ ] **Step 3b: Add `_resolve_external`**

Immediately before `load_config` (~line 165), add:

```python
def _resolve_external(raw, env):
    """Resolve (segments_dir, default_ttl) from defaults < [external] file < env.
    Env: CC_AI_KIT_SEGMENTS_DIR (dir), CC_AI_KIT_EXTERNAL_TTL (int seconds)."""
    file_ext = raw.get("external") or {}
    ttl = 10
    fv = file_ext.get("ttl")
    if isinstance(fv, int) and not isinstance(fv, bool):
        ttl = fv
    ev = env.get("CC_AI_KIT_EXTERNAL_TTL")
    if ev is not None:
        try:
            ttl = int(ev)
        except ValueError:
            pass
    return _segments_dir(file_ext, env), ttl
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_external_segments.py::TestResolveExternal -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add tools/status-line.py tests/test_external_segments.py
git commit -m "feat(e4c): Config.external field + [external] dir/ttl resolution"
```

---

### Task 6: `_place_external` — insert into the layout

**Files:**
- Modify: `tools/status-line.py` (after `_resolve_external`)
- Test: `tests/test_external_segments.py`

- [ ] **Step 1: Write the failing test**

Append:

```python
class TestPlace(unittest.TestCase):
    def _layout(self):
        return [sl.Line(0, ["path", "branch"]),
                sl.Line(20, ["model", "clock"]),
                sl.Line(30, ["context", "memory"])]

    def _spec(self, sid, line, position):
        return sl.ExtSpec(id=sid, path=f"/x/{sid}", line=line, position=position,
                          timeout=2.0, ttl=10, cache_path=f"/c/{sid}")

    def test_after_key(self):
        layout, final = sl._place_external(self._layout(),
                                           [self._spec("aws", 2, ("after", "clock"))])
        self.assertEqual(layout[1].segments, ["model", "clock", "aws"])
        self.assertEqual(final[0].line, 2)

    def test_before_key(self):
        layout, _ = sl._place_external(self._layout(),
                                       [self._spec("x", 2, ("before", "clock"))])
        self.assertEqual(layout[1].segments, ["model", "x", "clock"])

    def test_start_and_end(self):
        layout, _ = sl._place_external(self._layout(), [
            self._spec("s", 1, ("start", "")), self._spec("e", 1, ("end", ""))])
        self.assertEqual(layout[0].segments, ["s", "path", "branch", "e"])

    def test_line_zero_means_last_row(self):
        layout, final = sl._place_external(self._layout(),
                                           [self._spec("z", 0, ("end", ""))])
        self.assertEqual(layout[2].segments, ["context", "memory", "z"])
        self.assertEqual(final[0].line, 3)         # resolved to the last row

    def test_out_of_range_clamps_to_last(self):
        layout, final = sl._place_external(self._layout(),
                                           [self._spec("z", 9, ("end", ""))])
        self.assertEqual(layout[2].segments[-1], "z")
        self.assertEqual(final[0].line, 3)

    def test_missing_ref_appends(self):
        layout, _ = sl._place_external(self._layout(),
                                       [self._spec("z", 2, ("after", "nope"))])
        self.assertEqual(layout[1].segments, ["model", "clock", "z"])

    def test_min_rows_preserved(self):
        layout, _ = sl._place_external(self._layout(),
                                       [self._spec("z", 2, ("end", ""))])
        self.assertEqual([ln.min_rows for ln in layout], [0, 20, 30])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_external_segments.py::TestPlace -v`
Expected: FAIL — `AttributeError: ... '_place_external'`

- [ ] **Step 3: Implement placement**

After `_resolve_external`, add:

```python
def _place_external(layout, specs):
    """Insert each spec's id into the resolved layout at its row/position and
    return (new_layout, finalized_specs). Resolves line=0 to the last row and
    clamps out-of-range rows (with a dim warning). Specs are applied in their
    (filename, id) sort order so same-slot externals are deterministic."""
    if not layout:
        return list(layout), []
    rows = [list(ln.segments) for ln in layout]
    nrows = len(rows)
    final = []
    for spec in specs:
        want = spec.line or nrows                      # 0 => last row
        idx = want - 1
        if idx < 0 or idx >= nrows:
            print(f"{_DIM}status-line: segment '{spec.id}' line={want} out of range "
                  f"— clamped to row {nrows}{RESET}", file=sys.stderr)
            idx = nrows - 1
        kind, ref = spec.position
        segs = rows[idx]
        if kind == "start":
            segs.insert(0, spec.id)
        elif kind == "after" and ref in segs:
            segs.insert(segs.index(ref) + 1, spec.id)
        elif kind == "before" and ref in segs:
            segs.insert(segs.index(ref), spec.id)
        else:                                          # end, or after/before missing ref
            segs.append(spec.id)
        final.append(spec._replace(line=idx + 1))
    new_layout = [Line(layout[i].min_rows, rows[i]) for i in range(nrows)]
    return new_layout, final
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_external_segments.py::TestPlace -v`
Expected: PASS (7 tests)

- [ ] **Step 5: Commit**

```bash
git add tools/status-line.py tests/test_external_segments.py
git commit -m "feat(e4c): place external providers into the resolved layout"
```

---

### Task 7: Wire discovery into `load_config`

**Files:**
- Modify: `tools/status-line.py` (`load_config`, ~165-201)
- Test: `tests/test_external_segments.py`

- [ ] **Step 1: Write the failing test**

Append:

```python
class TestLoadConfigExternal(unittest.TestCase):
    def setUp(self):
        import shutil
        self.dir = tempfile.mkdtemp()
        self.segs = os.path.join(self.dir, "segs")
        os.makedirs(self.segs)
        self.cfg = os.path.join(self.dir, "statusline.toml")
        self.addCleanup(lambda: shutil.rmtree(self.dir, ignore_errors=True))

    def _env(self, **extra):
        env = {"CC_AI_KIT_CONFIG": self.cfg, "CC_AI_KIT_SEGMENTS_DIR": self.segs,
               "XDG_CACHE_HOME": os.path.join(self.dir, "cache"), "HOME": self.dir}
        env.update(extra)
        return env

    def test_discovered_provider_enabled_by_default_and_placed(self):
        write_script(self.segs, "sysmem",
                     "#!/bin/sh\n# ai-kit-segment: line=1 end\necho hi\n")
        cfg = sl.load_config(self._env())
        self.assertTrue(cfg.segments.get("sysmem"))            # default-on
        self.assertIn("sysmem", cfg.layout[0].segments)        # placed on row 1
        self.assertEqual([s.id for s in cfg.external], ["sysmem"])

    def test_explicit_disable_in_toml_is_honored(self):
        write_script(self.segs, "sysmem", "#!/bin/sh\necho hi\n")
        with open(self.cfg, "w") as f:
            f.write("[segments]\nsysmem = false\n")
        cfg = sl.load_config(self._env())
        self.assertFalse(cfg.segments["sysmem"])

    def test_env_toggle_disables_external(self):
        write_script(self.segs, "sysmem", "#!/bin/sh\necho hi\n")
        cfg = sl.load_config(self._env(CC_AI_KIT_SEGMENT_SYSMEM="0"))
        self.assertFalse(cfg.segments["sysmem"])

    def test_no_providers_keeps_external_empty(self):
        cfg = sl.load_config(self._env())
        self.assertEqual(cfg.external, [])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_external_segments.py::TestLoadConfigExternal -v`
Expected: FAIL — `sysmem` not in segments / `cfg.external` is None

- [ ] **Step 3: Modify `load_config`**

Replace the body of `load_config` (lines ~165-201) with the version below. The change: discover providers BEFORE resolving segments (so external ids are valid `[segments]` keys and pick up file/env toggles), seed their default-on flags, place them into the layout, and carry the finalized specs in `Config.external`.

```python
def load_config(env):
    """Resolve the full Config: internal defaults < TOML file < env. External
    drop-in providers (E4c) are discovered here so their ids are valid segment
    toggles and they are placed into the resolved layout as synthetic builders."""
    base = default_config()
    raw = _load_toml(config_path(env))

    # External providers first: their ids must be known segment keys before
    # _resolve_segments runs, so `[segments] <id> = false` is honored (not warned)
    # and they default to enabled.
    ext_dir, ext_ttl = _resolve_external(raw, env)
    specs = discover_external(ext_dir, ext_ttl, env)
    seg_defaults = dict(base.segments)
    for s in specs:
        seg_defaults.setdefault(s.id, True)

    segments = _resolve_segments(seg_defaults, raw.get("segments"), env)
    layout = _resolve_layout(base.layout, raw.get("line"))
    layout, external = _place_external(layout, specs)

    palette = {}
    for k, v in (raw.get("palette") or {}).items():
        if k in _PALETTE_DEFAULTS:
            palette[k] = str(v)
        else:
            print(f"{_DIM}status-line: unknown palette key '{k}'{RESET}", file=sys.stderr)
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
    git = dict(_GIT_DEFAULTS)
    for k, v in (raw.get("git") or {}).items():
        if k not in _GIT_DEFAULTS:
            print(f"{_DIM}status-line: unknown [git] key '{k}'{RESET}", file=sys.stderr)
        elif not isinstance(v, bool):
            print(f"{_DIM}status-line: [git] {k} must be true/false, got {v!r} — ignored{RESET}",
                  file=sys.stderr)
        else:
            git[k] = v
    wt = env_bool(env, "CC_AI_KIT_GIT_WORKTREE")   # env wins over file
    if wt is not None:
        git["worktree"] = wt
    return Config(segments=segments, layout=layout, palette=palette, ramps=ramps,
                  git=git, external=external)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_external_segments.py::TestLoadConfigExternal -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Run the full existing suite (no regressions)**

Run: `python3 -m pytest tests/test_status_line.py -q`
Expected: PASS (all existing tests green — `default_config()`/`load_config` still return a valid `Config`).

- [ ] **Step 6: Commit**

```bash
git add tools/status-line.py tests/test_external_segments.py
git commit -m "feat(e4c): discover + place external providers in load_config"
```

---

## Phase 4 — Builder integration

### Task 8: Merged builder map threaded through render/pack_line/safe_build

**Files:**
- Modify: `tools/status-line.py` (`safe_build` ~1144, `pack_line` ~1159, `render` ~1198, `build_data` ~1355 to carry `raw`; add `make_external_builder`/`_builders_for` after `BUILDERS` ~780)
- Test: `tests/test_external_segments.py`

- [ ] **Step 1: Write the failing test**

Append:

```python
class TestRenderIntegration(unittest.TestCase):
    def setUp(self):
        import shutil
        self.dir = tempfile.mkdtemp()
        self.segs = os.path.join(self.dir, "segs")
        os.makedirs(self.segs)
        self.cfg = os.path.join(self.dir, "statusline.toml")
        self.addCleanup(lambda: shutil.rmtree(self.dir, ignore_errors=True))
        self.env = {"CC_AI_KIT_CONFIG": self.cfg, "CC_AI_KIT_SEGMENTS_DIR": self.segs,
                    "XDG_CACHE_HOME": os.path.join(self.dir, "cache"), "HOME": self.dir}

    def _render(self, cols=200, lines=40):
        cfg = sl.load_config(self.env)
        theme = sl.build_theme(cfg)
        raw = {"workspace": {"current_dir": self.dir},
               "context_window": {"used_percentage": 10, "context_window_size": 200000},
               "session_id": "x", "transcript_path": "", "rate_limits": {}}
        data, c, l = sl.build_data(raw, self.env, cfg.segments)
        return "\n".join(sl.render(data, cols, lines, cfg, theme))

    def test_external_segment_appears_in_render(self):
        write_script(self.segs, "ping",
                     "#!/bin/sh\n# ai-kit-segment: line=1 end\necho PONG\n")
        self.assertIn("PONG", self._render())

    def test_disabled_external_absent(self):
        write_script(self.segs, "ping", "#!/bin/sh\n# ai-kit-segment: line=1 end\necho PONG\n")
        with open(self.cfg, "w") as f:
            f.write("[segments]\nping = false\n")
        self.assertNotIn("PONG", self._render())

    def test_failing_provider_never_breaks_line(self):
        write_script(self.segs, "boom",
                     "#!/bin/sh\n# ai-kit-segment: line=1 end\nexit 3\n")
        out = self._render()
        self.assertNotIn("boom", out)              # omitted, no crash marker
        self.assertTrue(out)                        # line still renders

    def test_external_self_tiers_on_cols(self):
        write_script(self.segs, "t",
                     '#!/bin/sh\n# ai-kit-segment: line=1 end\n'
                     'if [ "$AI_KIT_SEGMENT_COLS" -ge 10 ]; then echo LONGFORM; '
                     'else echo S; fi\n')
        self.assertIn("LONGFORM", self._render(cols=200))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_external_segments.py::TestRenderIntegration -v`
Expected: FAIL — provider output not present (builders map not merged yet).

- [ ] **Step 3a: Add builder factory + merged map**

After the `BUILDERS = { ... }` block (~line 789), add:

```python
def make_external_builder(spec):
    """Wrap an ExtSpec as a seg_x(data, avail, theme)-shaped builder so pack_line
    treats it exactly like a built-in. theme is unused (the provider colors itself)."""
    def _builder(data, avail, theme):
        return run_external(spec, data, avail)
    return _builder


def _builders_for(cfg):
    """The built-in BUILDERS merged with one synthetic builder per external
    provider (keyed by id). External ids never collide with built-ins by design;
    if a user names one after a built-in, the external wins for that render."""
    builders = dict(BUILDERS)
    for spec in (cfg.external or []):
        builders[spec.id] = make_external_builder(spec)
    return builders
```

- [ ] **Step 3b: Thread `builders` through `safe_build` and `pack_line`**

Replace `safe_build` (~1144) and `pack_line` (~1159):

```python
def safe_build(key, data, avail, theme, failed, builders=None):
    """Invoke one segment builder in isolation. On ANY exception, record `key`
    in the shared `failed` set and return a width-bounded warning marker instead
    of propagating. `builders` defaults to the built-in BUILDERS registry."""
    builders = builders if builders is not None else BUILDERS
    try:
        return builders[key](data, avail, theme)
    except Exception:                              # noqa: BLE001 — isolation is the point
        failed.add(key)
        named = f"{_WARN}⚠{key}{RESET}"
        if visible_width(named) <= avail:
            return named
        return f"{_WARN}⚠{RESET}"


def pack_line(keys, data, cols, cfg=None, theme=None, failed=None, builders=None):
    """Best-fit pack enabled segments into cols - RIGHT_MARGIN. Pinned segments are
    always kept. Order is priority: leftmost survive. `builders` carries the merged
    built-in + external map; defaults to that derived from cfg."""
    cfg = cfg or default_config()
    theme = theme or build_theme(cfg)
    failed = failed if failed is not None else set()
    builders = builders if builders is not None else _builders_for(cfg)
    budget = cols - RIGHT_MARGIN
    sep_w = visible_width(SEP)
    kept, used = [], 0
    for key in keys:
        if not cfg.segments.get(key, False):   # flag gate: not built => no compute
            continue
        sep = sep_w if kept else 0
        avail = budget - used - sep
        s = safe_build(key, data, max(avail, 0), theme, failed, builders)
        if not s:
            continue
        if key in PINNED or visible_width(s) <= avail:
            kept.append(s)
            used += visible_width(s) + sep
    return SEP.join(kept)
```

- [ ] **Step 3c: Build the merged map once in `render`**

Replace `render` (~1198):

```python
def render(data, cols, lines, cfg=None, theme=None):
    """Render up to len(cfg.layout) lines, gated by terminal height and width.
    A trailing diagnostic line is appended only when a builder crashed."""
    cfg = cfg or default_config()
    theme = theme or build_theme(cfg)
    builders = _builders_for(cfg)
    failed = set()
    out = []
    for ln in cfg.layout:
        if lines < ln.min_rows:
            continue
        packed = pack_line(ln.segments, data, cols, cfg, theme, failed, builders)
        if packed:
            out.append(packed)
    diag = diagnostic_line(failed)
    if diag:
        out.append(diag)
    return out
```

- [ ] **Step 3d: Carry the raw status JSON in `data`**

In `build_data` (~1307), add `"raw": raw,` to the returned `data` dict (so `run_external` can forward the original JSON to providers). Insert it as the first key:

```python
    data = {
        "raw": raw,
        "model_name": model.get("display_name", ""),
        # ... (rest unchanged) ...
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_external_segments.py::TestRenderIntegration -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Full suite (no regressions)**

Run: `python3 -m pytest tests/test_status_line.py tests/test_external_segments.py -q`
Expected: PASS (existing `pack_line`/`render`/`safe_build` callers still work via the `builders=None` default).

- [ ] **Step 6: Commit**

```bash
git add tools/status-line.py tests/test_external_segments.py
git commit -m "feat(e4c): thread merged built-in+external builders through render"
```

---

## Phase 5 — CLI surface

### Task 9: `--print-config`, `--check`/doctor, and env help

**Files:**
- Modify: `tools/status-line.py` (`cmd_print_config` ~1400, `validate_config_file` ~1412, `_ENV_HELP` ~1388)
- Test: `tests/test_external_segments.py`

- [ ] **Step 1: Write the failing test**

Append:

```python
class TestCliSurface(unittest.TestCase):
    def setUp(self):
        import shutil
        self.dir = tempfile.mkdtemp()
        self.segs = os.path.join(self.dir, "segs")
        os.makedirs(self.segs)
        self.cfg = os.path.join(self.dir, "statusline.toml")
        self.addCleanup(lambda: shutil.rmtree(self.dir, ignore_errors=True))
        self.env = {"CC_AI_KIT_CONFIG": self.cfg, "CC_AI_KIT_SEGMENTS_DIR": self.segs,
                    "XDG_CACHE_HOME": os.path.join(self.dir, "cache"), "HOME": self.dir}

    def test_print_config_lists_external(self):
        write_script(self.segs, "sysmem", "#!/bin/sh\n# ai-kit-segment: line=1 end\necho hi\n")
        cfg = sl.load_config(self.env)
        blob = json.loads(sl.cmd_print_config(cfg))
        self.assertEqual(blob["external"]["providers"][0]["id"], "sysmem")
        self.assertIn("ttl", blob["external"])
        # `dir` is the PROVIDERS directory, not the XDG cache dir.
        self.assertEqual(blob["external"]["dir"], self.segs)

    def test_validate_accepts_external_id_in_segments(self):
        write_script(self.segs, "sysmem", "#!/bin/sh\necho hi\n")
        with open(self.cfg, "w") as f:
            f.write("[segments]\nsysmem = false\n")
        self.assertEqual(sl.validate_config_file(self.cfg, self.env), [])

    def test_validate_flags_unknown_external_key(self):
        with open(self.cfg, "w") as f:
            f.write("[external]\nbogus = 1\n")
        errs = sl.validate_config_file(self.cfg, self.env)
        self.assertTrue(any("external" in e for e in errs))

    def test_validate_flags_bad_external_ttl(self):
        with open(self.cfg, "w") as f:
            f.write('[external]\nttl = "soon"\n')
        errs = sl.validate_config_file(self.cfg, self.env)
        self.assertTrue(any("ttl" in e for e in errs))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_external_segments.py::TestCliSurface -v`
Expected: FAIL — `KeyError: 'external'` in print-config; validate flags `sysmem` as unknown segment.

- [ ] **Step 3a: Extend `cmd_print_config`**

Replace `cmd_print_config` (~1400):

```python
def cmd_print_config(cfg):
    """Resolved config as pretty JSON (no rendering)."""
    # Reconstruct the resolved external dir/ttl from the first provider's values
    # (all providers share the same providers dir and the load-time default ttl).
    # `dir` is the PROVIDERS directory (where the scripts live), derived from a
    # spec's own `path` — NOT `cache_path`, which lives under XDG_CACHE_HOME.
    ext_providers = cfg.external or []
    ext_ttl = ext_providers[0].ttl if ext_providers else 10
    ext_dir = (os.path.dirname(ext_providers[0].path)
               if ext_providers else None)
    return json.dumps({
        "segments": cfg.segments,
        "layout": [{"min_rows": ln.min_rows, "segments": ln.segments}
                   for ln in cfg.layout],
        "palette": cfg.palette,
        "ramps": cfg.ramps,
        "git": cfg.git or {},
        "external": {
            "ttl": ext_ttl,
            "dir": ext_dir,
            "providers": [
                {"id": s.id, "path": s.path, "line": s.line,
                 "position": _position_str(s.position),
                 "timeout": s.timeout, "ttl": s.ttl}
                for s in ext_providers
            ],
        },
    }, indent=2)
```

> **Note:** `blob["external"]` always carries `"ttl"` and `"dir"` keys (reflecting the resolved external config), plus `"providers"` (the list of discovered specs). `"dir"` is the **providers directory** (where the scripts live), taken from `os.path.dirname(spec.path)` — deliberately NOT `cache_path`, which resolves under `XDG_CACHE_HOME` and would mislead anyone reading `--print-config` to diagnose discovery. The test `test_print_config_lists_external` asserts `blob["external"]["providers"][0]["id"]`, `"ttl" in blob["external"]`, and `blob["external"]["dir"] == segments_dir` — all satisfied by this implementation.

- [ ] **Step 3b: Make `validate_config_file` external-aware**

In `validate_config_file` (~1412), two changes. First, after `defaults = default_config()` (~1427), discover external ids so they count as known segment keys and known layout segments:

```python
    defaults = default_config()
    ext_dir, ext_ttl = _resolve_external(raw, env)
    ext_ids = {s.id for s in discover_external(ext_dir, ext_ttl, env)}
    known_segments = set(defaults.segments) | ext_ids
    for k in (raw.get("segments") or {}):
        if k not in known_segments:
            errors.append(f"unknown segment key: {k}")
```

(Replace the existing `for k in (raw.get("segments") or {}): if k not in defaults.segments:` loop with the block above.)

Then update the `[[line]]` builder check (~1437) so external ids are valid layout segments:

```python
    for i, line in enumerate(raw.get("line") or []):
        for seg in line.get("segments", []):
            if seg not in BUILDERS and seg not in ext_ids:
                errors.append(f"line[{i}] references unknown segment: {seg}")
```

Finally, before the closing `return errors`, add `[external]` block validation:

```python
    ext = raw.get("external")
    if ext is not None:
        if not isinstance(ext, dict):
            errors.append("[external] must be a table")
        else:
            for k in ext:
                if k not in ("ttl", "dir"):
                    errors.append(f"unknown [external] key: {k}")
            if "ttl" in ext and (not isinstance(ext["ttl"], int) or isinstance(ext["ttl"], bool)):
                errors.append(f"[external] ttl must be an integer, got {ext['ttl']!r}")
            if "dir" in ext and not isinstance(ext["dir"], str):
                errors.append(f"[external] dir must be a string, got {ext['dir']!r}")
```

- [ ] **Step 3c: Document env vars in `_ENV_HELP`**

In `_ENV_HELP` (~1388), append two lines before the closing precedence sentence:

```
  CC_AI_KIT_SEGMENTS_DIR   external drop-in segments directory (default
                           ${XDG_CONFIG_HOME:-~/.config}/ai-kit/segments)
  CC_AI_KIT_EXTERNAL_TTL   default cache TTL (seconds) for external segments
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_external_segments.py::TestCliSurface -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Full suite**

Run: `python3 -m pytest tests/test_status_line.py tests/test_external_segments.py -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add tools/status-line.py tests/test_external_segments.py
git commit -m "feat(e4c): external segments in --print-config, --check, env help"
```

---

## Phase 6 — Sample provider, recipe, README

### Task 10: Ship the cross-platform `sysmem` sample provider

**Files:**
- Create: `examples/segments/sysmem`
- Test: `tests/test_external_segments.py`

- [ ] **Step 1: Write the failing test**

Append:

```python
class TestSampleProvider(unittest.TestCase):
    PATH = os.path.join(_HERE, "..", "examples", "segments", "sysmem")

    def test_is_executable_with_header(self):
        self.assertTrue(os.access(self.PATH, os.X_OK), "sysmem must be chmod +x")
        with open(self.PATH, encoding="utf-8") as f:
            head = [f.readline() for _ in range(10)]
        self.assertIsNotNone(sl.parse_segment_header(head))

    def test_runs_and_emits_one_sgr_line(self):
        spec = sl.ExtSpec(id="sysmem", path=os.path.abspath(self.PATH), line=1,
                          position=("after", "context"), timeout=3.0, ttl=0,
                          cache_path=os.path.join(tempfile.mkdtemp(), "sysmem"))
        data = {"raw": {}, "work_dir": "."}
        out = sl.run_external(spec, data, 40)
        # Renders on Linux/macOS; on an unsupported platform it cleanly drops (None).
        if out is not None:
            self.assertEqual(out.count("\n"), 0)
            self.assertLessEqual(sl.visible_width(out), 40)

    def test_short_budget_tiers_down_or_drops(self):
        spec = sl.ExtSpec(id="sysmem", path=os.path.abspath(self.PATH), line=1,
                          position=("end", ""), timeout=3.0, ttl=0,
                          cache_path=os.path.join(tempfile.mkdtemp(), "sysmem"))
        out = sl.run_external(spec, {"raw": {}, "work_dir": "."}, 4)
        if out is not None:
            self.assertLessEqual(sl.visible_width(out), 4)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_external_segments.py::TestSampleProvider -v`
Expected: FAIL — `examples/segments/sysmem` does not exist.

- [ ] **Step 3: Create the sample provider**

Create `examples/segments/sysmem` (then `chmod +x`):

```python
#!/usr/bin/env python3
# ai-kit-segment: line=1 after=context id=sysmem ttl=10
"""ai-kit external status-line segment — system AVAILABLE memory (cross-platform).

This is a copy-and-edit reference provider. It reports the machine's available
RAM (distinct from the built-in `memory` segment, which is the status-line
process RSS). It demonstrates the external-segment contract:

  * read the column budget from the AI_KIT_SEGMENT_COLS env var (mirrored from
    the `segment.avail_cols` field in the status JSON on stdin);
  * pick a long / medium / short rendering that fits, or print nothing to drop;
  * emit a single line, optionally with SGR color (kept) — any other control
    sequence is stripped by the core.

Drop it in ~/.config/ai-kit/segments/ and make it executable. Disable it with
`[segments] sysmem = false` (or CC_AI_KIT_SEGMENT_SYSMEM=0)."""
import os
import sys

GREEN, YELLOW, RED, RESET = "\033[32m", "\033[33m", "\033[31;1m", "\033[0m"


def available_bytes():
    """Available system memory in bytes, or None on an unsupported platform."""
    # Linux: MemAvailable in /proc/meminfo (kB).
    try:
        with open("/proc/meminfo", encoding="utf-8") as f:
            for line in f:
                if line.startswith("MemAvailable:"):
                    return int(line.split()[1]) * 1024
    except OSError:
        pass
    # macOS / BSD: pages free+inactive+speculative from vm_stat * page size.
    try:
        import subprocess
        vm = subprocess.run(["vm_stat"], capture_output=True, text=True, timeout=1)
        if vm.returncode == 0:
            page = 4096
            free = 0
            for line in vm.stdout.splitlines():
                if "page size of" in line:
                    page = int("".join(c for c in line.split("page size of")[1] if c.isdigit()))
                for label in ("Pages free", "Pages inactive", "Pages speculative"):
                    if line.startswith(label + ":"):
                        free += int(line.rsplit(":", 1)[1].strip().rstrip("."))
            return free * page
    except (OSError, ValueError, ImportError):
        pass
    return None


def fmt_gib(n):
    return n / (1024 ** 3)


def main():
    n = available_bytes()
    if n is None:
        return 0                       # unsupported platform -> print nothing -> dropped
    gib = fmt_gib(n)
    color = GREEN if gib >= 4 else YELLOW if gib >= 1 else RED
    cols = int(os.environ.get("AI_KIT_SEGMENT_COLS", "80") or "80")
    if cols >= 14:
        text = f"🧠 {gib:.1f} GiB free"
    elif cols >= 9:
        text = f"🧠 {gib:.1f}G"
    elif cols >= 4:
        text = f"🧠{gib:.0f}G"
    else:
        return 0                       # no room -> drop
    sys.stdout.write(f"{color}{text}{RESET}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

Then:

```bash
chmod +x examples/segments/sysmem
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_external_segments.py::TestSampleProvider -v`
Expected: PASS (3 tests; the run/tier tests no-op gracefully on unsupported platforms)

- [ ] **Step 5: Commit**

```bash
git add examples/segments/sysmem tests/test_external_segments.py
git commit -m "feat(e4c): ship cross-platform system-available-memory sample segment"
```

---

### Task 11: Recipe `[external]` block + drift guard

**Files:**
- Modify: `tools/statusline.toml.sample`
- Test: `tests/test_external_segments.py`

- [ ] **Step 1: Write the failing test**

Append:

```python
class TestRecipe(unittest.TestCase):
    PATH = os.path.join(_HERE, "..", "tools", "statusline.toml.sample")

    def test_recipe_has_commented_external_block(self):
        with open(self.PATH, encoding="utf-8") as f:
            text = f.read()
        self.assertIn("[external]", text)
        self.assertIn("CC_AI_KIT_SEGMENTS_DIR", text)
        # Block ships fully commented (NO-OP): no live (uncommented) [external].
        for line in text.splitlines():
            self.assertNotEqual(line.strip(), "[external]",
                                "the [external] block must ship commented out")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_external_segments.py::TestRecipe -v`
Expected: FAIL — no `[external]` in the recipe.

- [ ] **Step 3: Add the recipe block**

In `tools/statusline.toml.sample`, insert this block immediately after the `[git]` block (after line ~71, before the color-grammar section):

```toml

## ─── [external] — drop-in segment providers ──────────────────────────────────
## Add a new status-line segment WITHOUT editing status-line.py: drop an
## executable into the segments directory below. Each provider:
##   * carries a header in its first 10 lines:
##       # ai-kit-segment: line=<N> (after=<key>|before=<key>|start|end) [id=<slug>] [timeout=<s>] [ttl=<s>]
##   * receives the status JSON on stdin (plus a "segment" block with avail_cols /
##     id / line / position) and the AI_KIT_SEGMENT_* env mirror, with cwd set to
##     the workspace directory;
##   * prints ONE line (SGR color allowed; other control sequences are stripped),
##     sized to the AI_KIT_SEGMENT_COLS budget — or nothing to omit itself.
## Discovered providers are ENABLED BY DEFAULT; disable one explicitly via
## [segments] <id> = false (or CC_AI_KIT_SEGMENT_<ID>=0). A ready-to-copy sample
## ships at examples/segments/sysmem (system available memory). Each value below
## is the current default.
# [external]
# ttl = 10                              # default cache TTL (s); env CC_AI_KIT_EXTERNAL_TTL
# dir = "~/.config/ai-kit/segments"     # providers directory; env CC_AI_KIT_SEGMENTS_DIR
```

Also add to the bottom "Environment overrides" section (after the `CC_AI_KIT_SEGMENT_<KEY>` lines, ~line 150):

```
##   CC_AI_KIT_SEGMENTS_DIR=/path/to/segments   # external providers directory
##   CC_AI_KIT_EXTERNAL_TTL=10                  # external-segment cache TTL (s)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_external_segments.py::TestRecipe -v`
Expected: PASS

- [ ] **Step 5: Verify the recipe still validates clean**

Run: `python3 tools/status-line.py --check tools/statusline.toml.sample`
Expected: prints `... OK` (the fully-commented block is a no-op).

- [ ] **Step 6: Commit**

```bash
git add tools/statusline.toml.sample tests/test_external_segments.py
git commit -m "docs(e4c): recipe [external] block + env overrides"
```

---

### Task 12: README documentation

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Locate the status-line section**

Run: `grep -n "status.line\|statusline\|## " README.md | head -40`
Expected: find the status-line configuration section to append after.

- [ ] **Step 2: Add the external-segments documentation**

Add a new subsection to `README.md` under the status-line configuration area:

````markdown
### External drop-in segments

Add a status-line segment without editing `status-line.py`: drop an executable
into `~/.config/ai-kit/segments/` (override with `CC_AI_KIT_SEGMENTS_DIR` or
`[external] dir`). It is discovered on the next render, **enabled by default**,
and placed via a header in its first 10 lines:

```
# ai-kit-segment: line=<N> (after=<key>|before=<key>|start|end) [id=<slug>] [timeout=<s>] [ttl=<s>]
```

Defaults: `line` = last row, position = `end`, `id` = filename stem,
`timeout` = 2s, `ttl` = `[external] ttl` (10s).

**Input.** The provider receives the same status JSON Claude passes, augmented
with a `segment` block, on **stdin** — and the key scalars mirrored as env vars
so a shell one-liner needs no JSON parser:

```json
{ "...": "normal status fields",
  "segment": { "id": "aws", "avail_cols": 24, "line": 2, "position": "after:clock" } }
```

`AI_KIT_SEGMENT_COLS`, `AI_KIT_SEGMENT_ID`, `AI_KIT_SEGMENT_LINE`,
`AI_KIT_SEGMENT_POSITION`. The provider runs with `cwd` = the workspace directory.

**Output.** Print **one line**. SGR color escapes (`\033[…m`) are kept; any other
control sequence is stripped. Size it to `AI_KIT_SEGMENT_COLS` (long → medium →
short) — or print nothing to omit the segment. The core truncates as a safety net
and never lets an external push out a pinned segment. Output is cached per `id`
for `ttl` seconds (`ttl=0` re-runs every render).

**Worked example — AWS session expiry (`~/.config/ai-kit/segments/aws-session`):**

```bash
#!/bin/sh
# ai-kit-segment: line=2 after=clock id=aws-session ttl=30
left=$(your-aws-expiry-command)            # e.g. "4h 44m 12s"
cols=${AI_KIT_SEGMENT_COLS:-80}
if   [ "$cols" -ge 14 ]; then printf '\033[33m🔐 %s\033[0m\n' "$left"
elif [ "$cols" -ge 8  ]; then printf '\033[33m🔐 4h44m\033[0m\n'
elif [ "$cols" -ge 4  ]; then printf '\033[33m🔐4h\033[0m\n'
fi                                          # else: nothing -> dropped
```

A cross-platform Python reference (system available memory) ships at
`examples/segments/sysmem` — copy it as a starting point.

**Disable** a provider explicitly: `[segments] aws-session = false` (or
`CC_AI_KIT_SEGMENT_AWS_SESSION=0`).

**Trust model.** Providers are arbitrary executables you place in your own
directory; ai-kit never installs them. Keep them fast and single-line. A
failing, slow (past `timeout`), or empty provider is simply omitted.
````

- [ ] **Step 3: Verify it renders**

Run: `grep -n "External drop-in segments" README.md`
Expected: the new heading is present.

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs(e4c): README external drop-in segments section"
```

---

## Final verification

- [ ] **Run the entire suite**

Run: `python3 -m pytest tests/test_external_segments.py tests/test_status_line.py -q`
Expected: ALL PASS.

- [ ] **Smoke-test the live pipeline**

Run:
```bash
mkdir -p /tmp/aikit-segs
cat > /tmp/aikit-segs/hello <<'EOF'
#!/bin/sh
# ai-kit-segment: line=1 end
echo "HELLO $AI_KIT_SEGMENT_COLS"
EOF
chmod +x /tmp/aikit-segs/hello
echo '{"workspace":{"current_dir":"."},"context_window":{"used_percentage":10,"context_window_size":200000},"session_id":"x","transcript_path":"","rate_limits":{}}' \
  | CC_AI_KIT_SEGMENTS_DIR=/tmp/aikit-segs python3 tools/status-line.py
```
Expected: the rendered status line includes `HELLO <cols>`.

- [ ] **Doctor stays green**

Run: `python3 tools/status-line.py --doctor`
Expected: `OK — config valid, all N segments render cleanly`.

---

## Self-Review (completed during authoring)

- **Spec coverage:** discovery (Task 2), header grammar (Task 1), input contract incl. env mirror + stdin block + cwd (Task 4), columns/tier contract (Tasks 3/8), execution + SGR-only sanitization + truncation (Tasks 3/4), placement + clamp + ordering (Task 6), TTL cache + unwritable-dir best-effort (Task 4), enable/disable default-on (Task 7), `[external]` config + env (Tasks 5/9/11), print-config + check (Task 9), sample provider (Task 10), README contract docs + worked AWS example (Task 12). **Wizard discovery (FR-4c.9) is the separate wizard plan.**
- **Placeholder scan:** none — every code step shows complete code.
- **Type consistency:** `ExtSpec` fields, `position` (kind, ref) tuple, and the `builders` param thread consistently across Tasks 1–9; `Config.external` is a `list[ExtSpec]` everywhere (None only as the back-compat default, read via `cfg.external or []`).
````
