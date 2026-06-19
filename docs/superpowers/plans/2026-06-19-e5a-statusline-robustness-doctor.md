# E5a — Status-line Renderer Robustness + Doctor — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `status-line.py` never blank the bar — isolate each segment builder so one crash can't kill the line, surface failures inline + on a diagnostic line, and ship a `--doctor` that validates config and dry-renders every segment.

**Architecture:** Builders are invoked at a single site (`pack_line`). Wrap that one call in `safe_build`, which catches any exception, records the failing key in a shared `failed` set, and returns a width-bounded `⚠` marker. `render` threads the `failed` set through every line and appends one diagnostic line that points at a concrete, copy-pasteable doctor command. `main`'s render path is wrapped so even a catastrophic failure prints a single diagnostic line and exits 0. `--doctor` reuses the existing `validate_config_file` plus a dry render against a built-in sample input.

**Tech Stack:** Python 3 stdlib only (`unittest`, `argparse`). No new dependencies. Source: `tools/status-line.py`. Tests: `tests/test_status_line.py` (run via `python3 -m unittest tests.test_status_line`).

**Scope note (deliberate):** This phase does NOT add an on-bar "bad .toml" indicator that re-validates config on every render — config errors already degrade to defaults with a dim stderr warning (never blank) and are fully reported by `--doctor`. Re-validating on the hot render path would add cost for no blank-bar risk. The blank-bar cause is a *raising builder*, which Tasks 1–5 fix.

**Spec:** `docs/superpowers/specs/2026-06-19-e5-installer-wizard-design.md` §5.4.

---

## File Structure

| File | Responsibility | Change |
|---|---|---|
| `tools/status-line.py` | The renderer | Add `_WARN`, `_doctor_cmd`, `safe_build`, `diagnostic_line`, `safe_render`, `_DOCTOR_SAMPLE`, `_dry_render_failures`, `cmd_doctor`; thread `failed` through `pack_line`/`render`; wrap `main`'s render; add `--doctor` |
| `tests/test_status_line.py` | unittest suite | Add `TestRendererRobustness` + `TestDoctor` classes |

Existing anchors (current line numbers — verify before editing, they shift as you go):
- `RIGHT_MARGIN = 4` (48), `SEP = " | "` (49), `RESET` (206), `_DIM` (208)
- `visible_width` (279), `pack_line` (1131), `render` (1157)
- `validate_config_file` (1363), `cmd_check` (1417), `parse_args` (1429), `main` (1447)
- Test harness: `sl = load_module()` (23), `strip()` removes ANSI, builders live in `sl.BUILDERS`.

---

## Task 1: `_WARN` color + `_doctor_cmd()` helper

**Files:**
- Modify: `tools/status-line.py` (near `_DIM`, ~208; new helper after the color constants block)
- Test: `tests/test_status_line.py` (new `TestRendererRobustness` class)

- [ ] **Step 1: Write the failing test**

Add at the end of `tests/test_status_line.py`:

```python
class TestRendererRobustness(unittest.TestCase):
    def test_doctor_cmd_is_concrete(self):
        cmd = sl._doctor_cmd()
        # A copy-pasteable command, not a bare flag: ends with --doctor,
        # names a python executable, and references this script's path.
        self.assertTrue(cmd.endswith("--doctor"), cmd)
        self.assertIn("status-line.py", cmd)
        self.assertRegex(cmd, r"^\S*python\S*\s")

    def test_warn_is_an_sgr_code(self):
        self.assertTrue(sl._WARN.startswith("\033["))
        self.assertTrue(sl._WARN.endswith("m"))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_status_line.TestRendererRobustness -v`
Expected: FAIL — `AttributeError: module 'status_line' has no attribute '_doctor_cmd'`.

- [ ] **Step 3: Write minimal implementation**

In `tools/status-line.py`, immediately after the `_DIM = "\033[90m" ...` line (~208), add:

```python
_WARN = "\033[33m"            # fixed yellow for failure markers (palette-independent)


def _doctor_cmd():
    """A concrete, copy-pasteable doctor invocation for THIS install — resolved
    from the running interpreter and this file's path (~-collapsed). Never a bare
    '--doctor', which would assume the user is sitting in a repo clone."""
    py = os.path.basename(sys.executable) or "python3"
    path = os.path.abspath(__file__)
    home = os.path.expanduser("~")
    if path == home or path.startswith(home + os.sep):
        path = "~" + path[len(home):]
    return f"{py} {path} --doctor"
```

(`os`, `sys` are already imported at the top of the file.)

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_status_line.TestRendererRobustness -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add tools/status-line.py tests/test_status_line.py
git commit -m "feat(status-line): _WARN color + concrete _doctor_cmd helper (E5a)"
```

---

## Task 2: `safe_build()` — isolate one builder invocation

**Files:**
- Modify: `tools/status-line.py` (new function just above `pack_line`, ~1131)
- Test: `tests/test_status_line.py` (`TestRendererRobustness`)

- [ ] **Step 1: Write the failing test**

Add to `TestRendererRobustness`:

```python
    def test_safe_build_passes_through_ok_builder(self):
        failed = set()
        def good(data, avail, theme):
            return "HELLO"
        with mock.patch.dict(sl.BUILDERS, {"path": good}):
            out = sl.safe_build("path", _data(), 40, THEME, failed)
        self.assertEqual(out, "HELLO")
        self.assertEqual(failed, set())

    def test_safe_build_records_and_marks_on_raise(self):
        failed = set()
        def boom(data, avail, theme):
            raise RuntimeError("kaboom")
        with mock.patch.dict(sl.BUILDERS, {"path": boom}):
            out = sl.safe_build("path", _data(), 40, THEME, failed)
        self.assertIn("path", failed)
        self.assertIn("path", strip(out))          # name shown when width allows
        self.assertLessEqual(sl.visible_width(out), 40)

    def test_safe_build_bare_marker_when_no_room_for_name(self):
        failed = set()
        def boom(data, avail, theme):
            raise RuntimeError("x")
        with mock.patch.dict(sl.BUILDERS, {"context": boom}):
            out = sl.safe_build("context", _data(), 1, THEME, failed)
        self.assertIn("context", failed)
        self.assertNotIn("context", strip(out))    # name dropped, icon kept
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_status_line.TestRendererRobustness -v`
Expected: FAIL — `AttributeError: module 'status_line' has no attribute 'safe_build'`.

- [ ] **Step 3: Write minimal implementation**

In `tools/status-line.py`, add this function immediately above `def pack_line(` (~1131):

```python
def safe_build(key, data, avail, theme, failed):
    """Invoke one segment builder in isolation. On ANY exception, record `key`
    in the shared `failed` set and return a width-bounded warning marker instead
    of propagating — so a single bad segment can never blank the whole bar. The
    marker shows the segment name when it fits `avail`, else just the icon."""
    try:
        return BUILDERS[key](data, avail, theme)
    except Exception:                              # noqa: BLE001 — isolation is the point
        failed.add(key)
        named = f"{_WARN}⚠{key}{RESET}"
        if visible_width(named) <= avail:
            return named
        return f"{_WARN}⚠{RESET}"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_status_line.TestRendererRobustness -v`
Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add tools/status-line.py tests/test_status_line.py
git commit -m "feat(status-line): safe_build isolates a raising segment builder (E5a)"
```

---

## Task 3: Thread `failed` through `pack_line`

**Files:**
- Modify: `tools/status-line.py` — `pack_line` (~1131)
- Test: `tests/test_status_line.py` (`TestRendererRobustness`)

- [ ] **Step 1: Write the failing test**

Add to `TestRendererRobustness`:

```python
    def test_pack_line_survives_a_raising_pinned_builder(self):
        # "path" is PINNED — even when its builder raises, the line still renders
        # the other segments and records the failure.
        failed = set()
        def boom(data, avail, theme):
            raise ValueError("nope")
        cfg = sl.default_config()
        def ok(data, avail, theme):
            return "CTX"
        with mock.patch.dict(sl.BUILDERS, {"path": boom, "context": ok}):
            line = sl.pack_line(["path", "context"], _data(), 80, cfg, THEME, failed)
        self.assertIn("path", failed)
        self.assertIn("CTX", strip(line))          # the healthy segment still shows
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_status_line.TestRendererRobustness.test_pack_line_survives_a_raising_pinned_builder -v`
Expected: FAIL — `TypeError: pack_line() takes ... arguments` (no `failed` param yet) or the raise propagates.

- [ ] **Step 3: Write minimal implementation**

In `tools/status-line.py`, change the `pack_line` signature and its builder call. Replace:

```python
def pack_line(keys, data, cols, cfg=None, theme=None):
```
with:
```python
def pack_line(keys, data, cols, cfg=None, theme=None, failed=None):
```

Then, inside `pack_line`, after the `theme = theme or build_theme(cfg)` line, add:

```python
    failed = failed if failed is not None else set()
```

And replace the builder invocation line:

```python
        s = BUILDERS[key](data, max(avail, 0), theme)
```
with:
```python
        s = safe_build(key, data, max(avail, 0), theme, failed)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_status_line.TestRendererRobustness -v`
Expected: PASS. Then run the **full** suite to confirm no regression (existing `TestPackLine`):
Run: `python3 -m unittest tests.test_status_line -v`
Expected: PASS (all existing + new).

- [ ] **Step 5: Commit**

```bash
git add tools/status-line.py tests/test_status_line.py
git commit -m "feat(status-line): pack_line routes builders through safe_build (E5a)"
```

---

## Task 4: `diagnostic_line()` + wire into `render`

**Files:**
- Modify: `tools/status-line.py` — new `diagnostic_line` above `render`; `render` body (~1157)
- Test: `tests/test_status_line.py` (`TestRendererRobustness`)

- [ ] **Step 1: Write the failing test**

Add to `TestRendererRobustness`:

```python
    def test_diagnostic_line_none_when_no_failures(self):
        self.assertIsNone(sl.diagnostic_line(set()))

    def test_diagnostic_line_lists_failures_and_doctor(self):
        line = strip(sl.diagnostic_line({"git", "context"}))
        self.assertIn("2 segments failed", line)
        self.assertIn("context, git", line)         # sorted
        self.assertIn("--doctor", line)

    def test_render_appends_diagnostic_on_builder_crash(self):
        def boom(data, avail, theme):
            raise RuntimeError("x")
        cfg = sl.default_config()
        layout = [sl.Line(0, ["path"])]
        cfg = cfg._replace(layout=layout)
        with mock.patch.dict(sl.BUILDERS, {"path": boom}):
            out = sl.render(_data(), 80, 40, cfg, THEME)
        self.assertTrue(any("--doctor" in strip(l) for l in out))
        self.assertTrue(any("path" in strip(l) for l in out))

    def test_render_no_diagnostic_when_healthy(self):
        cfg = sl.default_config()
        out = sl.render(_data(), 80, 40, cfg, THEME)
        self.assertFalse(any("--doctor" in strip(l) for l in out))
```

> Note: `cfg._replace(...)` works because `Config` is a namedtuple; `sl.Line` is the layout row namedtuple. If the field name differs, use `sl.default_config()` and patch a builder for a segment already in the default layout instead.

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_status_line.TestRendererRobustness -v`
Expected: FAIL — `AttributeError: ... 'diagnostic_line'`.

- [ ] **Step 3: Write minimal implementation**

In `tools/status-line.py`, add `diagnostic_line` immediately above `def render(` (~1157):

```python
def diagnostic_line(failed):
    """One line naming the segments that crashed this render, pointing at the
    doctor. Returns None when nothing failed (no cost on the happy path)."""
    if not failed:
        return None
    names = ", ".join(sorted(failed))
    n = len(failed)
    noun = "segment" if n == 1 else "segments"
    return (f"{_WARN}⚠ {n} {noun} failed: {names} — "
            f"run the doctor: {_doctor_cmd()}{RESET}")
```

Then rewrite the body of `render` to thread a shared `failed` set and append the diagnostic:

```python
def render(data, cols, lines, cfg=None, theme=None):
    """Render up to len(cfg.layout) lines, gated by terminal height and width.
    A trailing diagnostic line is appended only when a builder crashed."""
    cfg = cfg or default_config()
    theme = theme or build_theme(cfg)
    failed = set()
    out = []
    for ln in cfg.layout:
        if lines < ln.min_rows:
            continue
        packed = pack_line(ln.segments, data, cols, cfg, theme, failed)
        if packed:
            out.append(packed)
    diag = diagnostic_line(failed)
    if diag:
        out.append(diag)
    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_status_line -v`
Expected: PASS (all, including existing `TestRenderLayout` / `TestEndToEnd`).

- [ ] **Step 5: Commit**

```bash
git add tools/status-line.py tests/test_status_line.py
git commit -m "feat(status-line): render appends a diagnostic line for failed segments (E5a)"
```

---

## Task 5: Never-blank `main()` — `safe_render()` wrapper

**Files:**
- Modify: `tools/status-line.py` — new `safe_render` above `main`; `main` render path (~1447)
- Test: `tests/test_status_line.py` (`TestRendererRobustness`)

- [ ] **Step 1: Write the failing test**

Add to `TestRendererRobustness`:

```python
    def test_safe_render_returns_diagnostic_on_catastrophic_failure(self):
        cfg = sl.default_config()
        theme = THEME
        with mock.patch.object(sl, "build_data", side_effect=RuntimeError("boom")):
            out = sl.safe_render({}, os.environ, cfg, theme, 0)
        self.assertEqual(len(out), 1)
        self.assertIn("status-line error", strip(out[0]))
        self.assertIn("--doctor", strip(out[0]))

    def test_safe_render_normal_path(self):
        cfg = sl.default_config()
        out = sl.safe_render({}, os.environ, cfg, THEME, 0)
        self.assertIsInstance(out, list)
        self.assertFalse(any("status-line error" in strip(l) for l in out))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_status_line.TestRendererRobustness -v`
Expected: FAIL — `AttributeError: ... 'safe_render'`.

- [ ] **Step 3: Write minimal implementation**

In `tools/status-line.py`, add `safe_render` immediately above `def main(` (~1447):

```python
def safe_render(raw, env, cfg, theme, t_start):
    """Build data and render; on ANY unexpected failure return a single
    diagnostic line instead of a blank bar. Never raises. This is the backstop
    above safe_build's per-segment isolation (covers build_data itself)."""
    try:
        data, cols, lines = build_data(
            raw, env, cfg.segments, t_start, (cfg.git or {}).get("worktree", False))
        return render(data, cols, lines, cfg, theme)
    except Exception:                              # noqa: BLE001 — never blank the bar
        return [f"{_WARN}⚠ status-line error — "
                f"run the doctor: {_doctor_cmd()}{RESET}"]
```

Then, in `main`, replace the existing render block:

```python
    try:
        raw = json.load(sys.stdin)
    except (ValueError, OSError):
        raw = {}
    data, cols, lines = build_data(raw, os.environ, cfg.segments, t0,
                                   (cfg.git or {}).get("worktree", False))
    print("\n".join(render(data, cols, lines, cfg, theme)))
```
with:
```python
    try:
        raw = json.load(sys.stdin)
    except (ValueError, OSError):
        raw = {}
    print("\n".join(safe_render(raw, os.environ, cfg, theme, t0)))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_status_line -v`
Expected: PASS (all).

- [ ] **Step 5: Commit**

```bash
git add tools/status-line.py tests/test_status_line.py
git commit -m "feat(status-line): safe_render backstop so main never blanks the bar (E5a)"
```

---

## Task 6: `--doctor` — validate config + dry-render every segment

**Files:**
- Modify: `tools/status-line.py` — `_DOCTOR_SAMPLE`, `_dry_render_failures`, `cmd_doctor` (CLI section near `cmd_check`, ~1417); `--doctor` in `parse_args` (~1429); dispatch in `main` (~1450)
- Test: `tests/test_status_line.py` (new `TestDoctor` class)

- [ ] **Step 1: Write the failing test**

Add at the end of `tests/test_status_line.py`:

```python
class TestDoctor(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        # Resolve config to a path that does NOT exist → defaults, which are valid.
        self.env = {"HOME": self.tmp,
                    "CC_AI_KIT_CONFIG": os.path.join(self.tmp, "absent.toml")}

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_doctor_ok_on_defaults(self):
        rc = sl.cmd_doctor(self.env)
        self.assertEqual(rc, 0)

    def test_doctor_flags_a_raising_builder(self):
        def boom(data, avail, theme):
            raise RuntimeError("x")
        with mock.patch.dict(sl.BUILDERS, {"path": boom}):
            rc = sl.cmd_doctor(self.env)
        self.assertEqual(rc, 1)

    def test_doctor_flags_invalid_config_file(self):
        bad = os.path.join(self.tmp, "bad.toml")
        with open(bad, "w") as f:
            f.write("[segments]\nthis_is_not_a_segment = true\n")
        env = dict(self.env, CC_AI_KIT_CONFIG=bad)
        rc = sl.cmd_doctor(env)
        self.assertEqual(rc, 1)

    def test_check_flag_still_works(self):
        # Back-compat: --check path is untouched.
        rc = sl.cmd_check(os.path.join(self.tmp, "absent.toml"), self.env)
        self.assertEqual(rc, 1)   # absent file → cmd_check reports it (existing behavior)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_status_line.TestDoctor -v`
Expected: FAIL — `AttributeError: ... 'cmd_doctor'`.

- [ ] **Step 3: Write minimal implementation**

In `tools/status-line.py`, in the CLI introspection section just above `def cmd_check(` (~1417), add the sample, the dry-render helper, and the doctor command:

```python
# A representative status JSON for the doctor's dry render. Self-contained (no
# fixture file): exercises every default builder so one that raises is surfaced.
_DOCTOR_SAMPLE = {
    "model": {"display_name": "Opus 4.8", "id": "claude-opus-4-8"},
    "cost": {"total_lines_added": 12, "total_lines_removed": 3,
             "total_cost_usd": 0.0123, "total_duration_ms": 45000,
             "total_api_duration_ms": 12000},
    "context_window": {"used_percentage": 42, "context_window_size": 200000},
    "workspace": {"current_dir": "."},
    "transcript_path": "",
    "session_id": "doctor-sample",
    "rate_limits": {},
    "effort": {"level": "high"},
}


def _dry_render_failures(cfg, theme, env):
    """Run every enabled builder once against the sample input; return the set of
    segment keys whose builder raised (caught by safe_build via pack_line)."""
    failed = set()
    data, _cols, _lines = build_data(
        dict(_DOCTOR_SAMPLE), env, cfg.segments, time.perf_counter_ns(),
        (cfg.git or {}).get("worktree", False))
    for ln in cfg.layout:
        pack_line(ln.segments, data, 200, cfg, theme, failed)
    return failed


def cmd_doctor(env):
    """Validate the resolved config AND dry-render every enabled segment. Prints a
    report; returns process exit code (0 healthy, 1 if any problem)."""
    path = config_path(env)
    errors = []
    if os.path.exists(path):
        errors = [f"{path}: {e}" for e in validate_config_file(path, env)]
    failed = set()
    cfg = load_config(env)                         # never raises (degrades to defaults)
    try:
        theme = build_theme(cfg)
        failed = _dry_render_failures(cfg, theme, env)
    except Exception as e:                         # noqa: BLE001
        errors.append(f"render pipeline crashed: {e!r}")
    for e in errors:
        print(e, file=sys.stderr)
    for key in sorted(failed):
        print(f"segment '{key}' raised during render", file=sys.stderr)
    if errors or failed:
        print(f"after fixing, re-run: {_doctor_cmd()}", file=sys.stderr)
        return 1
    print(f"{path}: OK — config valid, all {len(cfg.segments)} segments render cleanly")
    return 0
```

In `parse_args` (~1429), add the flag after the `--check` argument:

```python
    p.add_argument("--doctor", action="store_true",
                   help="validate the config AND dry-render every segment to "
                        "surface a builder that raises; exit non-zero if unhealthy")
```

In `main` (~1450), add the dispatch immediately after the `--check` block:

```python
    if args.doctor:
        sys.exit(cmd_doctor(os.environ))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_status_line.TestDoctor -v`
Expected: PASS (4 tests).

Then exercise the real CLI end-to-end:
Run: `python3 tools/status-line.py --doctor; echo "exit=$?"`
Expected: prints `<path>: OK — config valid, all N segments render cleanly` and `exit=0` (or, if your live config has issues, the specific errors and `exit=1`).

- [ ] **Step 5: Commit**

```bash
git add tools/status-line.py tests/test_status_line.py
git commit -m "feat(status-line): --doctor validates config + dry-renders segments (E5a)"
```

---

## Task 7: Full-suite + lint gate

**Files:** none (verification only)

- [ ] **Step 1: Run the whole unit suite**

Run: `python3 -m unittest tests.test_status_line -v`
Expected: PASS — all prior tests plus `TestRendererRobustness` (9) and `TestDoctor` (4), zero failures.

- [ ] **Step 2: Smoke-test the never-blank guarantee by hand**

Run:
```bash
echo '{"model":{"display_name":"Opus"},"workspace":{"current_dir":"."}}' | python3 tools/status-line.py; echo "exit=$?"
```
Expected: a rendered bar (not empty) and `exit=0`.

- [ ] **Step 3: Confirm a crashing builder degrades, not blanks**

Run:
```bash
python3 - <<'PY'
import importlib.util, os
spec = importlib.util.spec_from_file_location("sl", "tools/status-line.py")
sl = importlib.util.module_from_spec(spec); spec.loader.exec_module(sl)
def boom(d,a,t): raise RuntimeError("x")
sl.BUILDERS["path"] = boom
cfg = sl.default_config()
data = {"work_dir":".","home":os.path.expanduser("~"),
    "model_name":"O","model_id":"x","effort":"high","effort_auto":False,
    "branch":"","dirty":"clean","is_worktree":False,"clock":"12:00","ago":"",
    "added":0,"removed":0,"cost":0,"total_ms":0,"api_ms":0,"context_pct":0,
    "context_max":0,"chat_bytes":None,"mem_bytes":None,"rate_limits":{},
    "todo_state":None,"todo_text":None,"dim_assumed":False,"cols":80,"lines":40,
    "t_start":None}
out = sl.render(data, 80, 40, cfg, sl.default_theme())
print("\n".join(out))
assert any("--doctor" in l for l in out), "expected diagnostic line"
print("OK: degraded with a diagnostic line, not blank")
PY
```
Expected: prints the bar with a `⚠ 1 segment failed: path — run the doctor: …` line and `OK: degraded …`.

- [ ] **Step 4: Commit (if any doc/log tweak needed; otherwise skip)**

No code change in this task. If everything passed, proceed to plan self-review.

---

## Self-Review Checklist (run after implementing)

1. **Spec coverage (§5.4):**
   - Centralized `safe_build` isolation at the single `pack_line` call site → Task 2–3 ✅
   - Inline `⚠` marker (name if width allows, else icon) → Task 2 ✅
   - Diagnostic line naming failed segments + concrete doctor command → Task 4 ✅
   - Never-blank top-level guard, exit 0 → Task 5 ✅
   - `--doctor` = config validation + dry render of every segment → Task 6 ✅
   - Doctor reachability (concrete `sys.executable` + `__file__` command) → Task 1 (`_doctor_cmd`) ✅
   - Deferred-by-design: on-bar "bad .toml" indicator (scope note) — documented, not built.
2. **Placeholder scan:** every step has real code/commands — no TBD/TODO.
3. **Type/name consistency:** `safe_build(key, data, avail, theme, failed)`, `pack_line(..., failed=None)`, `render(...)` appends `diagnostic_line(failed)`, `safe_render(raw, env, cfg, theme, t_start)`, `cmd_doctor(env)`, `_dry_render_failures(cfg, theme, env)`, `_doctor_cmd()`, `_DOCTOR_SAMPLE`, `_WARN` — names match across all tasks.

---

## Notes for the executor

- **Test runner is `unittest`, NOT pytest:** `python3 -m unittest tests.test_status_line`.
- The test module imports the file via `sl = load_module()`; reference everything as `sl.<name>`.
- Simulate a crashing builder with `mock.patch.dict(sl.BUILDERS, {"path": boom})` — `pack_line` reads the `BUILDERS` global, so the patch takes effect.
- `Config`/`Line` are namedtuples; use `._replace(...)` to vary layout in a test if needed.
- Do NOT touch `tools/statusline.toml.sample` (no defaults changed) — the drift test stays green.
- Keep `--check` working unchanged; `--doctor` is additive.
