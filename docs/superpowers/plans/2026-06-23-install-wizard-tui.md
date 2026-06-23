# Install Wizard TUI + Segment Layout Editor — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the hand-rolled `termios` installer selector with a single interactive **Textual** app (install-picks + 2-D segment-layout editor + live preview) that fails loudly when its prerequisites (tty + uv + textual) are absent, with no plain fallback and no headless path.

**Architecture:** A new `tools/wizard_app.py` holds the Textual UI only; it imports `textual` and a set of **injected engine callables** from `setup.py` (dependency injection — no import back into the main module, no import of the hyphenated `status-line.py`/`statusline-doctor.py`). `setup.py` keeps install mechanics, gains a fixed `open_tty()`, a `uv` bootstrap/re-exec guard, and a dispatch that launches the Textual app when interactive. The app **reuses** the existing in-memory model (`Selection`, the `state` dict + `_apply_wizard_command`) and the existing persistence/preview helpers (`save_statusline_config`, `render_preview`). The status-line **render path is untouched** and stays `python3 -S`, stdlib-only.

**Tech Stack:** Python 3 (stdlib for setup mechanics), `textual` (rich UI, resolved on demand via `uv run` + PEP-723 inline metadata), `uv` (ephemeral env for the wizard only), `unittest` + a `pty`-based harness for E2E.

## Global Constraints

- **Render path purity:** `tools/status-line.py` and its `settings.json` `statusLine.command` stay `python3 -S …`, stdlib-only. `uv`/`textual` MUST NOT appear on the render path — they exist only to launch the `setup.py` wizard. (PRD Addendum A.4.)
- **Module seam:** the wizard reaches `status-line.py` / `statusline-doctor.py` **only by subprocess** (hyphenated filenames forbid import). `wizard_app.py` imports nothing from `setup.py`; it receives engine callables as parameters. (PRD Addendum A.4.)
- **Single path, fail-closed:** no plain-menu fallback, no headless-defaults. Missing tty / uv / textual → one loud one-line reason on stderr + non-zero exit. (PRD Addendum B.)
- **Canonical contract (current names):** segments and layout are owned by `status-line.py` — `SEGMENTS` (`:110`), `LAYOUT` (`:149`, lines keyed by `min_rows` 0/20/30), `_SEG_HEADER_RE` (`:1789`); mirrored as `LAYOUT_DEFAULTS` in `setup.py` under the drift guard (`test_setup.py:80-92`). Current segment keys: `path, git_branch, alt_git_worktree, git_dirty, todo, model, alt_time_ago, alt_time_clock, effort, lines, alt_cost, alt_time_session, alt_time_api, render_time, slowest, alt_term_dimensions, context, chat_size, alt_system_memory, alt_rate_limits`. (PRD Addendum A.2/A.3.)
- **Persistence is doctor-validated:** all config writes go through `save_statusline_config(path, seg_changes, layout, statusline_doctor)` → `write_toml_preserving` → `statusline-doctor.py --doctor` → auto-revert on failure. Never write the TOML any other way. (PRD Addendum A.4, FR-W.5.)
- **uv install method:** the official astral installer `curl -LsSf https://astral.sh/uv/install.sh | sh` (wget form when curl absent), exact command printed before running, only after explicit consent. (PRD FR-W.2.)
- **E2E is mandatory and phase-local:** PTY-driven E2E scenarios are written alongside each phase, not deferred. The gate runs them. (PRD Addendum C.)
- **Quality gate:** `make validate` / pre-commit (ruff, pylint, pyright, vulture, shellcheck, unittest) stays green; status-line render output stays byte-identical (golden tests).

---

## File Structure

| File | Responsibility | Action |
|---|---|---|
| `tools/setup.py` | Install mechanics; `open_tty` fix; uv bootstrap/re-exec; dispatch to the Textual app; **delete** the termios selector + text REPL + headless path. Keeps the engine helpers (`Selection`, `_default_selection`, `apply_selection`, `state`/`_apply_wizard_command`/`_wizard_groups`/`_wizard_order`, `render_preview`, `save_statusline_config`, `enumerate_entries`, `installed_links`, example-segment helpers). | Modify |
| `tools/wizard_app.py` | **New.** Textual UI only: install-picks screen, layout board + off-tray, live preview pane. Pure view over injected callables + the reused model. PEP-723 note documents the `textual` dep. | Create |
| `tools/status-line.py` | Renderer. **Unchanged** (render path purity). | — |
| `tools/statusline-doctor.py` | Validator. **Unchanged.** | — |
| `tests/test_setup.py` | Unit tests for `open_tty` matrix, uv guard, model ops, persistence round-trip. Remove deleted-surface tests. | Modify |
| `tests/test_wizard_app.py` | **New.** Textual component tests via `App.run_test()` / `Pilot` over the app + model. | Create |
| `tests/test_wizard_pty.py` | PTY-driven **E2E** suite (rewritten for the single path). | Modify/Rewrite |
| `tests/test_install.sh` | `install.sh` bootstrapper mechanics (kept; PRD Addendum B.3). | Modify (only if a flag changes) |
| `README.md` | Document the rich wizard, the `uv` requirement, the keybindings, the fail-closed behavior. | Modify |

---

# Phase 1 — Foundations: fix `open_tty`, fail closed, uv bootstrap

**Ships value alone:** a local run is interactive again or exits with a clear reason; the rich runtime is guaranteed before any UI code runs. No Textual yet.

### Task 1.1: Fix `open_tty()` — `/dev/tty` → stdin/stdout-if-tty → None

**Files:**
- Modify: `tools/setup.py:592-605` (`open_tty`, `is_interactive`)
- Test: `tests/test_setup.py` (new `TestOpenTty` class)

**Interfaces:**
- Produces: `open_tty() -> TextIO | None` — returns a readable/writable stream that is a real terminal, or `None` only when nothing usable exists. `is_interactive(tty) -> bool` unchanged (`tty is not None`).

- [ ] **Step 1: Write failing tests for the fallback matrix**

```python
# tests/test_setup.py
import io, os, importlib.util, unittest
from unittest import mock

setup = _load_setup()  # existing helper in this file that imports tools/setup.py

class TestOpenTty(unittest.TestCase):
    def test_dev_tty_used_when_openable(self):
        sentinel = io.StringIO()
        with mock.patch("builtins.open", return_value=sentinel) as op:
            self.assertIs(setup.open_tty(), sentinel)
            op.assert_called_once_with("/dev/tty", "r+", encoding="utf-8")

    def test_falls_back_to_std_streams_when_both_are_ttys(self):
        with mock.patch("builtins.open", side_effect=OSError(6, "No such device")), \
             mock.patch.object(setup.sys, "stdin")  as si, \
             mock.patch.object(setup.sys, "stdout") as so:
            si.isatty.return_value = True
            so.isatty.return_value = True
            tty = setup.open_tty()
            self.assertIsNotNone(tty)            # a usable interactive stream
            self.assertTrue(setup.is_interactive(tty))

    def test_none_when_dev_tty_fails_and_stdin_is_pipe(self):
        # curl | bash: stdin is the script pipe, not a keyboard → not interactive
        with mock.patch("builtins.open", side_effect=OSError(6, "No such device")), \
             mock.patch.object(setup.sys, "stdin")  as si, \
             mock.patch.object(setup.sys, "stdout") as so:
            si.isatty.return_value = False
            so.isatty.return_value = True
            self.assertIsNone(setup.open_tty())

    def test_none_when_nothing_is_a_tty(self):
        with mock.patch("builtins.open", side_effect=OSError(6, "No such device")), \
             mock.patch.object(setup.sys, "stdin")  as si, \
             mock.patch.object(setup.sys, "stdout") as so:
            si.isatty.return_value = False
            so.isatty.return_value = False
            self.assertIsNone(setup.open_tty())
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m unittest tests.test_setup.TestOpenTty -v`
Expected: FAIL (current `open_tty` returns `None` on the `OSError`, so the stdin/stdout cases fail).

- [ ] **Step 3: Implement the fallback**

```python
# tools/setup.py — replace open_tty()
def open_tty():
    """Open an interactive terminal stream, or return None when none exists.

    Prefers /dev/tty (so `curl | bash` — where stdin is the script pipe — still
    reads the keyboard). When /dev/tty cannot be opened (IDE task runners, some
    uv/sandbox contexts), fall back to sys.stdin/stdout ONLY when BOTH are real
    TTYs — i.e. a direct local run where stdin literally is the keyboard. When
    nothing is usable, return None; the caller fails closed (no headless path)."""
    try:
        return open("/dev/tty", "r+", encoding="utf-8")
    except OSError:
        pass
    if _stream_isatty(sys.stdin) and _stream_isatty(sys.stdout):
        return _StdTty(sys.stdin, sys.stdout)
    return None
```

```python
# tools/setup.py — add near open_tty(). A thin read/write adapter so callers can
# treat (stdin, stdout) as one r+ stream like a real /dev/tty handle.
class _StdTty:
    """Adapts separate sys.stdin/sys.stdout into one tty-like object exposing
    readline()/write()/flush()/isatty()/close(). close() is a no-op — we must
    not close the process's own std streams."""
    def __init__(self, rstream, wstream):
        self._r, self._w = rstream, wstream
    def readline(self):       return self._r.readline()
    def write(self, text):    return self._w.write(text)
    def flush(self):          return self._w.flush()
    def isatty(self):         return True
    def tell(self):           raise OSError("std tty is not seekable")
    def seek(self, *a):       raise OSError("std tty is not seekable")
    def close(self):          pass
```

Note: `_StdTty.tell`/`seek` raise `OSError` so the existing `_tty_write` (setup.py:607) takes its non-seekable branch — verify `_tty_write` already catches `(OSError, ValueError)` (it does).

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m unittest tests.test_setup.TestOpenTty -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add tools/setup.py tests/test_setup.py
git commit -m "fix(wizard): open_tty falls back to std streams when both are TTYs (FR-W.1)"
```

---

### Task 1.2: Fail closed — delete the termios selector, text REPL, and headless path

**Files:**
- Modify: `tools/setup.py` — delete `chip_select` (`:1388`), `_read_key` (`:1351`), `_parse_key` (`:1290`), `RawMode` (`:1442`), `_mode_a_available` (`:1248`), `_chip_glyphs`/`_chip_row`/`_chip_frame`/`_clamp_window` (`:1265-1350`), `_CHIP_*` constants (`:1214-1219`); reduce `select_skills` (`:871`) to a non-interactive projection; delete the text REPL in `run_statusline_wizard` (`:1531-1564`) and `_print_segments`/`_preview_lines` (`:1184-1211`). **Keep** the model: `Selection`, `_default_selection`, `apply_selection`, the `state` dict shape, `_apply_wizard_command`, `_wizard_groups`, `_wizard_order`, `_find_line`, `_segment_changes_vs_recipe`, `save_statusline_config`, `render_preview`.
- Modify: `tools/setup.py:1685-1717` (`main`) and `:1600` (`cmd_install`) — fail closed when `tty is None`.
- Test: `tests/test_setup.py` — delete `chip_select`/`_mode_a`/text-REPL tests; add `TestFailClosed`.

**Interfaces:**
- Produces: `require_tty(tty) -> None` — prints a one-line reason to stderr and `sys.exit(2)` when `tty is None`. `select_skills(entries, installed, tty)` becomes: still returns `_default_selection(...)` (the projection the Textual app seeds from); it no longer prompts (the Textual app owns interaction).
- Consumes (Task 1.1): `open_tty`, `is_interactive`.

- [ ] **Step 1: Write the failing fail-closed test**

```python
# tests/test_setup.py
class TestFailClosed(unittest.TestCase):
    def test_install_exits_nonzero_when_no_tty(self):
        with mock.patch.object(setup, "open_tty", return_value=None), \
             mock.patch.object(setup.sys, "stderr", new_callable=io.StringIO) as err:
            with self.assertRaises(SystemExit) as cm:
                setup.main(["install"])
            self.assertEqual(cm.exception.code, 2)
            self.assertIn("terminal", err.getvalue().lower())
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python3 -m unittest tests.test_setup.TestFailClosed -v`
Expected: FAIL (today `cmd_install` runs headless with `tty=None` and returns 0).

- [ ] **Step 3: Add `require_tty` and wire it into `main`**

```python
# tools/setup.py — add near open_tty()
def require_tty(tty):
    """Fail closed: the wizard is interactive-only. With no usable terminal,
    print one clear reason and exit non-zero — never a silent headless default."""
    if tty is None:
        print("setup: no interactive terminal available — run this in a real "
              "terminal (the wizard cannot run headless).", file=sys.stderr)
        sys.exit(2)
```

```python
# tools/setup.py — in main(), the install/reconfigure branch:
    if args.subcommand in ("install", "reconfigure"):
        tty = open_tty()
        require_tty(tty)                 # fail closed (FR-W.1/B)
        ensure_rich_runtime(env)         # Task 1.3 — guarantee uv+textual or exit
        try:
            return cmd_install(env, tty, dry, examples_flag=args.examples)
        finally:
            tty.close()
```

- [ ] **Step 4: Delete the selector/REPL/headless code**

Delete the functions/constants listed in **Files** above. In `select_skills`, drop the interactive block (current `:880-932`) so the body is just:

```python
def select_skills(entries, installed, tty):
    """The pre-checked selection the wizard seeds from. Interaction now lives in
    the Textual app; this is the pure default projection (no prompting)."""
    return _default_selection(entries, installed)
```

In `cmd_install`, the `if is_interactive(tty): run_statusline_wizard(...)` line is replaced in Task 2.1/3.x by the Textual launch; for now leave a single call site placeholder that Task 2.1 fills. Remove the `run_statusline_wizard` REPL body but keep the function name as a thin shim that Task 3.4 repoints, or delete it and add the new launcher in Task 2.1 (preferred — delete it here).

- [ ] **Step 5: Prove the silent fallback is gone**

Run: `grep -nE "except Exception" tools/setup.py`
Expected: no match guards a selector path (the broad-except at old `:901` is deleted). Also: `grep -nE "chip_select|_mode_a_available|RawMode" tools/setup.py` → no matches.

- [ ] **Step 6: Run the suite; fix/remove orphaned tests**

Run: `python3 -m unittest tests.test_setup -v`
Expected: PASS after deleting tests that referenced the removed functions. Engine tests (TestPatchSegments, TestPatchLayout, TestWritePreserving, TestRenderPreview, TestGoldenPreservation, TestExternalSeam) stay green.

- [ ] **Step 7: Commit**

```bash
git add tools/setup.py tests/test_setup.py
git commit -m "refactor(wizard): fail closed; delete termios selector, text REPL, headless path (FR-W.6/B)"
```

---

### Task 1.3: uv bootstrap — detect, consent, install, re-exec (loop-guarded)

**Files:**
- Modify: `tools/setup.py` — add `ensure_rich_runtime`, `_under_uv`, `_textual_importable`, `_have_uv`, `_install_uv`, `_reexec_under_uv`. Add a PEP-723 inline-metadata comment block at the top of `setup.py` declaring `textual`.
- Test: `tests/test_setup.py` — new `TestUvBootstrap`.

**Interfaces:**
- Produces:
  - `ensure_rich_runtime(env) -> None` — returns normally when `textual` is importable (already under uv); otherwise asks consent, installs uv, and re-execs under `uv run`. Exits non-zero (fail closed) on decline/failure/loop. Idempotent guard against re-exec loops via env marker `AI_KIT_UV_REEXEC=1`.
  - `_under_uv(env) -> bool`, `_textual_importable() -> bool`, `_have_uv() -> str | None` (path), `_install_uv(tty) -> bool`, `_reexec_under_uv() -> NoReturn`.
- Consumes: `ask_yes_no` (setup.py:623), `require_tty`/`open_tty` (Tasks 1.1/1.2).

- [ ] **Step 1: Add the PEP-723 metadata block at the top of `setup.py`**

```python
# /// script
# requires-python = ">=3.11"
# dependencies = ["textual>=0.60"]
# ///
# ^ Consumed by `uv run tools/setup.py` to resolve textual into an ephemeral env
#   for the wizard ONLY. Plain `python3 tools/setup.py` ignores this comment; the
#   status-line render path never uses uv/textual (see plan Global Constraints).
```

(Confirm the current textual minimum against context7 during execution; pin a floor, not an exact version.)

- [ ] **Step 2: Write failing tests with a fake uv + import probe**

```python
# tests/test_setup.py
class TestUvBootstrap(unittest.TestCase):
    def test_returns_quietly_when_textual_importable(self):
        with mock.patch.object(setup, "_textual_importable", return_value=True), \
             mock.patch.object(setup, "_reexec_under_uv") as rx:
            setup.ensure_rich_runtime({"AI_KIT_UV_REEXEC": "1"})
            rx.assert_not_called()

    def test_reexecs_once_when_uv_present_and_textual_missing(self):
        with mock.patch.object(setup, "_textual_importable", return_value=False), \
             mock.patch.object(setup, "_have_uv", return_value="/usr/bin/uv"), \
             mock.patch.object(setup, "_reexec_under_uv", side_effect=SystemExit(0)) as rx:
            with self.assertRaises(SystemExit):
                setup.ensure_rich_runtime({})        # marker absent → may re-exec
            rx.assert_called_once()

    def test_no_reexec_loop_when_marker_already_set(self):
        # Under uv (marker set) but textual STILL missing → fail closed, never loop.
        with mock.patch.object(setup, "_textual_importable", return_value=False), \
             mock.patch.object(setup.sys, "stderr", new_callable=io.StringIO) as err:
            with self.assertRaises(SystemExit) as cm:
                setup.ensure_rich_runtime({"AI_KIT_UV_REEXEC": "1"})
            self.assertNotEqual(cm.exception.code, 0)
            self.assertIn("textual", err.getvalue().lower())

    def test_exits_when_uv_missing_and_consent_declined(self):
        with mock.patch.object(setup, "_textual_importable", return_value=False), \
             mock.patch.object(setup, "_have_uv", return_value=None), \
             mock.patch.object(setup, "open_tty", return_value=io.StringIO("n\n")), \
             mock.patch.object(setup.sys, "stderr", new_callable=io.StringIO):
            with self.assertRaises(SystemExit) as cm:
                setup.ensure_rich_runtime({})
            self.assertNotEqual(cm.exception.code, 0)
```

- [ ] **Step 3: Run them to verify they fail**

Run: `python3 -m unittest tests.test_setup.TestUvBootstrap -v`
Expected: FAIL (functions undefined).

- [ ] **Step 4: Implement the bootstrap**

```python
# tools/setup.py
def _textual_importable():
    """True when `textual` can be imported in THIS interpreter."""
    import importlib.util
    return importlib.util.find_spec("textual") is not None

def _under_uv(env):
    return env.get("AI_KIT_UV_REEXEC") == "1"

def _have_uv():
    """Path to the uv binary, or None. Checks PATH then ~/.local/bin (astral default)."""
    cand = shutil.which("uv")
    if cand:
        return cand
    fallback = os.path.expanduser("~/.local/bin/uv")
    return fallback if os.path.exists(fallback) else None

def _install_uv(tty):
    """Install uv via the official astral installer, after showing the exact
    command and getting consent. Returns True on success.

    SECURITY: `shell=True` is required because the official installer is a
    `download | sh` PIPE (two processes joined by the shell). It is safe by
    construction: `cmd` is one of two FIXED string literals below — no user
    input, no f-string interpolation of external data is ever spliced into it,
    so there is no command-injection surface. Do NOT refactor `cmd` to include
    any caller-supplied value; if that ever changes, this must stop using a
    shell. The exact command is printed and consented to before running."""
    cmd = ("curl -LsSf https://astral.sh/uv/install.sh | sh" if shutil.which("curl")
           else "wget -qO- https://astral.sh/uv/install.sh | sh")
    _tty_write(tty, f"\n  uv is required for the wizard. Install it now with:\n    {cmd}\n")
    if not ask_yes_no(tty, "  run this?", default=True):
        return False
    try:
        # cmd is a constant literal (see SECURITY note) — shell is the pipe runner.
        return subprocess.run(cmd, shell=True, check=False).returncode == 0  # noqa: S602  # pylint: disable=subprocess-run-check
    except OSError:
        return False

def _reexec_under_uv():
    """Re-exec this script under `uv run` so the PEP-723 deps resolve. Sets the
    loop-guard marker first; never returns."""
    env = dict(os.environ, AI_KIT_UV_REEXEC="1")
    uv = _have_uv() or "uv"
    script = os.path.abspath(__file__)
    os.execve(uv, [uv, "run", "--script", script, *sys.argv[1:]], env)

def ensure_rich_runtime(env):
    """Guarantee textual is importable, or fail closed. Re-exec under uv at most
    once (env marker guards the loop)."""
    if _textual_importable():
        return
    if _under_uv(env):                       # already re-exec'd, still missing → stop
        print("setup: textual is unavailable under uv — cannot launch the wizard.",
              file=sys.stderr)
        sys.exit(3)
    if _have_uv() is None:
        tty = open_tty(); require_tty(tty)
        if not _install_uv(tty):
            print("setup: uv is required for the wizard and was not installed.",
                  file=sys.stderr)
            sys.exit(3)
    _reexec_under_uv()                       # never returns
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `python3 -m unittest tests.test_setup.TestUvBootstrap -v`
Expected: PASS (4 tests).

- [ ] **Step 6: Commit**

```bash
git add tools/setup.py tests/test_setup.py
git commit -m "feat(wizard): uv bootstrap — detect/consent/install/re-exec, loop-guarded, fail-closed (FR-W.2)"
```

---

### Task 1.4: Phase-1 E2E (PTY) — interactivity + fail-closed + uv guard

**Files:**
- Modify/Create: `tests/test_wizard_pty.py` — `TestPhase1E2E` (PTY harness).

**Interfaces:**
- Consumes: `tools/setup.py` as a subprocess under a PTY.
- Produces: a reusable `spawn_pty(args, env)` helper (returns master fd + pid) used by later phases.

- [ ] **Step 1: Write the PTY harness + Phase-1 E2E scenarios (C.2 #3,#4,#5)**

```python
# tests/test_wizard_pty.py
import os, pty, select, subprocess, sys, time, unittest

SETUP = os.path.join(os.path.dirname(__file__), "..", "tools", "setup.py")

def run_no_tty(args, env):
    """Run setup.py with stdin/stdout NOT a tty (pipes) → must fail closed."""
    return subprocess.run([sys.executable, SETUP, *args], env=env,
                          capture_output=True, text=True)

class TestPhase1E2E(unittest.TestCase):
    def test_no_tty_exits_nonzero_with_reason(self):           # C.2 #4
        env = dict(os.environ, AI_KIT_UV_REEXEC="1")           # skip uv path
        r = run_no_tty(["install"], env)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("terminal", (r.stderr + r.stdout).lower())

    def test_local_run_is_interactive_under_pty(self):         # C.2 #3
        # A pty makes stdin/stdout TTYs; with /dev/tty unopenable in CI the
        # std-stream fallback (Task 1.1) must still present the wizard.
        env = dict(os.environ, AI_KIT_UV_REEXEC="1", CLAUDE_CONFIG_DIR=self._tmp())
        pid, fd = pty.fork()
        if pid == 0:
            os.execve(sys.executable, [sys.executable, SETUP, "--dry-run", "install"], env)
        out = self._drain(fd, deadline=10)
        os.waitpid(pid, 0)
        self.assertTrue(out, "wizard produced no interactive output")
```

(Provide `_tmp()` and `_drain(fd, deadline)` helpers: `_drain` loops `select.select([fd], …)` reading until EOF/timeout, tolerating `OSError` at EOF. Confirm the exact app-ready marker string to assert on once the Textual app exists in Phase 2; for Phase 1 assert non-empty interactive output / the fail-closed reason.)

- [ ] **Step 2: Run the E2E tests**

Run: `python3 -m unittest tests.test_wizard_pty.TestPhase1E2E -v`
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add tests/test_wizard_pty.py
git commit -m "test(wizard): Phase-1 PTY E2E — fail-closed + std-stream interactivity (Addendum C)"
```

---

# Phase 2 — Textual install-picks panel

**Goal:** the Textual app launches from `setup.py` and drives the existing reconcile via `Selection`.

### Task 2.1: Textual app skeleton + launcher

**Files:**
- Create: `tools/wizard_app.py`
- Modify: `tools/setup.py:1600` (`cmd_install`) — replace the old `select_skills` prompt + `run_statusline_wizard` with a single `launch_wizard(...)` call that builds the engine context and runs the app.
- Test: `tests/test_wizard_app.py`

**Interfaces:**
- Produces (in `wizard_app.py`):
  - `WizardContext` — a dataclass/namedtuple carrying: `selection` (a `Selection`), `state` (the `{segments, layout, dirty}` dict), `sample_json` (str), and an `engine` namespace of callables: `render_preview(segments) -> str`, `apply_command(state, cmd) -> (state, err)`, `groups(state) -> [(label, [keys])]`, `order(state) -> [keys]`.
  - `run_wizard(ctx: WizardContext) -> WizardResult | None` — runs the Textual app; returns `WizardResult(selection, state)` on confirm, `None` on abort.
  - `class WizardResult(NamedTuple): selection: Selection; state: dict`
- Consumes: `textual` (App, ComposeResult, widgets). From `setup.py` (injected, not imported): the engine callables above.

- [ ] **Step 1: Write a failing app-boots test via `run_test`**

```python
# tests/test_wizard_app.py
import unittest
from tools import wizard_app  # importable: no hyphen. Skips if textual absent.

try:
    import textual  # noqa
    HAVE_TEXTUAL = True
except ImportError:
    HAVE_TEXTUAL = False

@unittest.skipUnless(HAVE_TEXTUAL, "textual not installed (run under uv)")
class TestWizardApp(unittest.IsolatedAsyncioTestCase):
    async def test_app_boots_and_shows_install_picks(self):
        ctx = _fake_ctx()                      # builds a Selection + minimal state
        app = wizard_app.WizardApp(ctx)
        async with app.run_test() as pilot:
            await pilot.pause()
            self.assertIsNotNone(app.query_one("#install-picks"))
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python3 -m unittest tests.test_wizard_app -v`
Expected: FAIL (module/app undefined). (If textual is not installed locally, the test SKIPS — run this task under `uv run python -m unittest …` per Step 5.)

- [ ] **Step 3: Implement the app skeleton**

```python
# tools/wizard_app.py
"""Textual wizard UI for ai-kit setup. Pure view layer: imports textual and
receives all engine behavior via an injected WizardContext (see plan A.4 seam).
Resolved on demand via `uv run tools/setup.py` (PEP-723 deps in setup.py)."""
from __future__ import annotations
from typing import NamedTuple, Optional
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static, SelectionList
from textual.containers import Horizontal, Vertical


class WizardResult(NamedTuple):
    selection: object   # Selection
    state: dict


class WizardApp(App):
    """Two surfaces over one model: install-picks (Phase 2) and the layout
    board + preview (Phase 3). `q`/`esc` aborts (returns None)."""
    BINDINGS = [("q", "abort", "cancel"), ("escape", "abort", "cancel")]

    def __init__(self, ctx):
        super().__init__()
        self.ctx = ctx
        self.result: Optional[WizardResult] = None

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="install-picks"):
            yield SelectionList(id="picks")   # populated in on_mount from ctx.selection
        yield Footer()

    def on_mount(self):
        picks = self.query_one("#picks", SelectionList)
        for i, (cat, name, on) in enumerate(self.ctx.selection.items):
            picks.add_option((f"{cat}/{name}", i, on))

    def action_abort(self):
        self.result = None
        self.exit()


def run_wizard(ctx) -> Optional[WizardResult]:
    app = WizardApp(ctx)
    app.run()
    return app.result
```

(Textual widget specifics — `SelectionList` option tuple shape, `add_option`, reactive selected state — must be confirmed against context7 `textual` docs during execution; the structure above is the target.)

```python
# tools/setup.py — new launcher, replaces the deleted run_statusline_wizard call
def launch_wizard(paths, entries, installed, tty, dry):
    """Build the engine context and run the Textual wizard. Applies the chosen
    selection + layout on confirm; a None result (abort) leaves everything as-is."""
    import wizard_app                                  # lazy: only after uv guard
    sel = Selection((cat, name, name in _default_selection(entries, installed)[cat])
                    for cat in ("skills", "commands", "agents")
                    for name, _ in entries[cat])
    state = {"segments": current_segments(paths.config_toml),
             "layout": current_layout(paths.config_toml), "dirty": False}
    with open(_sample_input_path(), encoding="utf-8") as f:
        sample_json = f.read()
    ctx = wizard_app.WizardContext(
        selection=sel, state=state, sample_json=sample_json,
        engine=_engine_ns(paths, sample_json))
    result = wizard_app.run_wizard(ctx)
    if result is None:
        return
    apply_selection(result.selection.category_sets(CATEGORIES), entries,
                    paths.claude_dir, dry, _running_counts)
    _persist_layout(paths, result.state, dry)         # Task 3.4
```

(Define `WizardContext` as a `NamedTuple` in `wizard_app.py`; `_engine_ns` bundles `render_preview`/`_apply_wizard_command`/`_wizard_groups`/`_wizard_order` as a `types.SimpleNamespace`. Wire `cmd_install` to call `launch_wizard` instead of `select_skills`+`run_statusline_wizard`.)

- [ ] **Step 4: Run the app test under uv**

Run: `uv run --script tools/setup.py --help >/dev/null && uv run python -m unittest tests.test_wizard_app -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tools/wizard_app.py tools/setup.py tests/test_wizard_app.py
git commit -m "feat(wizard): Textual app skeleton + launcher wired into cmd_install (FR-W.3)"
```

---

### Task 2.2: Install-picks interaction — toggle / all / none + glyph state

**Files:**
- Modify: `tools/wizard_app.py` (install-picks bindings + glyph rendering)
- Test: `tests/test_wizard_app.py` (`TestInstallPicks`)

**Interfaces:**
- Consumes: `ctx.selection` (`Selection` — `toggle`, `set_all`, `category_sets`).
- Produces: keybindings `space` toggle, `a` all, `n` none; on confirm `WizardApp.result.selection` reflects the toggles. On/off shown by glyph shape (`◉`/`◯`) not color alone (FR-W.7).

- [ ] **Step 1: Write failing interaction tests**

```python
@unittest.skipUnless(HAVE_TEXTUAL, "textual not installed")
class TestInstallPicks(unittest.IsolatedAsyncioTestCase):
    async def test_space_toggles_focused_pick(self):
        ctx = _fake_ctx(items=[("skills", "a", True), ("skills", "b", False)])
        app = wizard_app.WizardApp(ctx)
        async with app.run_test() as pilot:
            await pilot.press("space")          # toggles the focused row
            self.assertFalse(ctx.selection.items[0][2])

    async def test_a_selects_all_n_selects_none(self):
        ctx = _fake_ctx(items=[("skills", "a", False), ("agents", "b", False)])
        app = wizard_app.WizardApp(ctx)
        async with app.run_test() as pilot:
            await pilot.press("a")
            self.assertTrue(all(it[2] for it in ctx.selection.items))
            await pilot.press("n")
            self.assertTrue(all(not it[2] for it in ctx.selection.items))
```

- [ ] **Step 2: Run to verify fail**

Run: `uv run python -m unittest tests.test_wizard_app.TestInstallPicks -v`
Expected: FAIL.

- [ ] **Step 3: Implement bindings**

Add to `WizardApp.BINDINGS`: `("space", "toggle", "toggle"), ("a", "all", "all"), ("n", "none", "none")`. Implement `action_toggle`/`action_all`/`action_none` to mutate `ctx.selection` (`toggle(focused_index)` / `set_all(True/False)`) and refresh the `SelectionList`. Render each option label as `f"{'◉' if on else '◯'} {cat}/{name}"`.

- [ ] **Step 4: Run to verify pass**

Run: `uv run python -m unittest tests.test_wizard_app.TestInstallPicks -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tools/wizard_app.py tests/test_wizard_app.py
git commit -m "feat(wizard): install-picks toggle/all/none with glyph state (FR-W.3/W.7)"
```

---

### Task 2.3: Summary + confirm; allow-but-confirm empty; clean abort

**Files:**
- Modify: `tools/wizard_app.py` (confirm screen / final binding)
- Test: `tests/test_wizard_app.py` (`TestConfirm`)

**Interfaces:**
- Produces: `enter` → a plain-text summary screen (install picks + layout); a final confirm sets `result`. Empty selection → a confirm modal "Nothing selected — install nothing?" defaulting to No. `q`/`esc`/Ctrl-C → `result = None`.

- [ ] **Step 1: Write failing tests**

```python
@unittest.skipUnless(HAVE_TEXTUAL, "textual not installed")
class TestConfirm(unittest.IsolatedAsyncioTestCase):
    async def test_enter_confirms_and_sets_result(self):
        ctx = _fake_ctx(items=[("skills", "a", True)])
        app = wizard_app.WizardApp(ctx)
        async with app.run_test() as pilot:
            await pilot.press("enter")          # to summary
            await pilot.press("enter")          # confirm
        self.assertIsNotNone(app.result)
        self.assertIn("a", app.result.selection.category_sets()["skills"])

    async def test_abort_yields_none_result(self):
        app = wizard_app.WizardApp(_fake_ctx())
        async with app.run_test() as pilot:
            await pilot.press("q")
        self.assertIsNone(app.result)
```

- [ ] **Step 2-4:** Run (FAIL) → implement summary/confirm screen + empty-selection modal → run (PASS).

Run: `uv run python -m unittest tests.test_wizard_app.TestConfirm -v`

- [ ] **Step 5: Commit**

```bash
git add tools/wizard_app.py tests/test_wizard_app.py
git commit -m "feat(wizard): summary + confirm, allow-but-confirm empty, clean abort (FR-W.7)"
```

---

### Task 2.4: Phase-2 E2E (PTY) — pick a skill, confirm, assert symlinks

**Files:**
- Modify: `tests/test_wizard_pty.py` (`TestPhase2E2E`)

**Interfaces:**
- Consumes: `spawn_pty` (Task 1.4); a temp `CLAUDE_CONFIG_DIR`.

- [ ] **Step 1: Write the E2E (C.2 #1 partial — install picks only)**

Drive the app under a PTY: wait for the picks screen, send `space`/`enter`/`enter`, then assert the expected symlink set appears under the temp `CLAUDE_CONFIG_DIR/skills` (or is absent when toggled off). Use `uv run` as the spawned interpreter so textual resolves.

```python
class TestPhase2E2E(unittest.TestCase):
    def test_pick_skill_and_confirm_creates_symlink(self):
        cfg = self._tmp()
        env = dict(os.environ, CLAUDE_CONFIG_DIR=cfg, AI_KIT_UV_REEXEC="1")
        pid, fd = pty.fork()
        if pid == 0:
            os.execve("uv", ["uv", "run", "--script", SETUP, "install"], env)
        self._expect(fd, "install", deadline=20)   # picks screen marker
        self._send(fd, "\r")                         # accept defaults → confirm
        self._send(fd, "\r")
        os.waitpid(pid, 0)
        self.assertTrue(os.listdir(os.path.join(cfg, "skills")))
```

- [ ] **Step 2: Run; Step 3: Commit**

```bash
git add tests/test_wizard_pty.py
git commit -m "test(wizard): Phase-2 PTY E2E — pick + confirm creates symlinks (Addendum C #1)"
```

---

# Phase 3 — Segment layout editor + live preview

**Goal:** the 2-D board that motivated the work, persisted truthfully via the existing writer/validator.

### Task 3.1: Layout model adapter — off-tray + move semantics over the existing `state`

**Files:**
- Modify: `tools/setup.py` — add `layout_move(state, seg, direction)` and `layout_toggle(state, seg)` thin adapters that express the editor's `←→`/`↑↓`/`space` in terms of the existing `_apply_wizard_command` semantics, plus an explicit **off-tray** projection.
- Test: `tests/test_setup.py` (`TestLayoutModel`)

**Interfaces:**
- Produces:
  - `layout_move(state, seg, direction) -> (state, err)` where `direction in {"left","right","up","down"}`. `left`/`right` = reorder within the line (`move <seg> up|down`). `up`/`down` = move across lines (`move <seg> line <n±1>`); `up` from line 1 sends the segment to the **off tray** (toggle off); `down` from the off tray re-activates onto line 1.
  - `off_tray(state) -> [keys]` — segments currently toggled off (the "not in layout"/off group). **Min-width gate preserved:** moves never alter any line's `min_rows`.
- Consumes: `_apply_wizard_command`, `_wizard_groups`, `_wizard_order`, `_find_line` (reused).

- [ ] **Step 1: Write failing model tests (incl. off-tray + gate preservation)**

```python
class TestLayoutModel(unittest.TestCase):
    def _state(self):
        return {"segments": {"path": True, "model": True, "cost": False},
                "layout": [{"min_rows": 0,  "segments": ["path"]},
                           {"min_rows": 20, "segments": ["model"]}],
                "dirty": False}

    def test_left_right_reorders_within_line(self):
        st = self._state(); st["layout"][0]["segments"] = ["path", "model"]
        st2, err = setup.layout_move(st, "model", "left")
        self.assertIsNone(err)
        self.assertEqual(st2["layout"][0]["segments"], ["model", "path"])

    def test_up_from_top_line_sends_to_off_tray(self):
        st2, err = setup.layout_move(self._state(), "path", "up")
        self.assertIsNone(err)
        self.assertIn("path", setup.off_tray(st2))
        self.assertFalse(st2["segments"]["path"])

    def test_min_width_gate_preserved_on_move(self):
        st2, _ = setup.layout_move(self._state(), "model", "up")  # line 2 -> line 1
        self.assertEqual([ln["min_rows"] for ln in st2["layout"]], [0, 20])
```

- [ ] **Step 2: Run (FAIL).** `python3 -m unittest tests.test_setup.TestLayoutModel -v`

- [ ] **Step 3: Implement the adapters** in terms of `_apply_wizard_command` (build the `move … up|down|line N` command string and delegate; handle the top-line→off-tray and off-tray→line-1 transitions by toggling `segments[seg]` and inserting/removing from line lists). Keep `min_rows` untouched.

- [ ] **Step 4: Run (PASS).**

- [ ] **Step 5: Commit**

```bash
git add tools/setup.py tests/test_setup.py
git commit -m "feat(wizard): layout-model adapters — move/off-tray over existing state, gate-preserving (FR-W.4/T3.1)"
```

---

### Task 3.2: Textual layout board — chips per line, off-tray, focus + moves

**Files:**
- Modify: `tools/wizard_app.py` (a `LayoutBoard` widget + screen)
- Test: `tests/test_wizard_app.py` (`TestLayoutBoard`)

**Interfaces:**
- Consumes: `ctx.engine.layout_move`/`off_tray` (injected from Task 3.1), `ctx.state`.
- Produces: a board screen reachable from install-picks (e.g. `tab`); chips grouped per layout line + an off-tray row; focused chip moves with arrows / `h j k l`; `space` toggles. `ctx.state` is mutated in place so the launcher persists it.

- [ ] **Step 1: Write failing board tests**

```python
@unittest.skipUnless(HAVE_TEXTUAL, "textual not installed")
class TestLayoutBoard(unittest.IsolatedAsyncioTestCase):
    async def test_arrow_moves_chip_within_line(self):
        ctx = _fake_ctx_layout()                 # path,model on line 1
        app = wizard_app.WizardApp(ctx)
        async with app.run_test() as pilot:
            await pilot.press("tab")             # to layout board
            await pilot.press("right")           # move focused chip right
            self.assertEqual(ctx.state["layout"][0]["segments"][:2], ["model", "path"])
```

- [ ] **Step 2-4:** Run (FAIL) → implement `LayoutBoard` (compose chips from `ctx.engine.groups(state)` + `off_tray`; key handlers call `layout_move` and re-render) → run (PASS). **Dispatch the ui-ux-designer agent** on the running board for a keybinding/legibility review; fold in fixes.

Run: `uv run python -m unittest tests.test_wizard_app.TestLayoutBoard -v`

- [ ] **Step 5: Commit**

```bash
git add tools/wizard_app.py tests/test_wizard_app.py
git commit -m "feat(wizard): Textual layout board — chips, off-tray, focus+moves (FR-W.4/T3.2)"
```

---

### Task 3.3: Live preview pane — real renderer via fixture, debounced

**Files:**
- Modify: `tools/wizard_app.py` (preview pane bound to edits)
- Create: `tests/fixtures/wizard-preview.json` (checked-in representative fixture) — or reuse `tests/fixtures/sample-input.json` if already representative; confirm it carries Claude-only fields (model/context/cost/todo).
- Test: `tests/test_wizard_app.py` (`TestPreview`) + `tests/test_setup.py` (fixture-shape pin)

**Interfaces:**
- Consumes: `ctx.engine.render_preview(segments) -> str` (wraps `render_preview(paths.status_line, segments, sample_json, {})`).
- Produces: a preview `Static` that re-renders on every edit; rapid edits coalesced (debounce via a Textual timer) so the subprocess isn't backlogged.

- [ ] **Step 1: Write the fixture-shape pin test (C.2 #7) in `test_setup.py`**

```python
class TestPreviewFixture(unittest.TestCase):
    def test_fixture_drives_renderer_without_unavailable(self):
        with open(setup._sample_input_path(), encoding="utf-8") as f:
            sample = f.read()
        out = setup.render_preview(_STATUS_LINE, setup.current_segments(_RECIPE),
                                   sample, {})
        self.assertTrue(out and "(preview unavailable)" not in out)
```

- [ ] **Step 2: Run (FAIL if fixture/sample drifted); Step 3: implement preview pane + debounce; pin/extend fixture.**

- [ ] **Step 4: Component test** — toggling a segment in the board changes the preview text:

```python
async def test_toggle_updates_preview(self):
    ...
    before = app.query_one("#preview", Static).renderable
    await pilot.press("space")
    await pilot.pause(0.2)                        # let debounce fire
    self.assertNotEqual(app.query_one("#preview", Static).renderable, before)
```

Run: `uv run python -m unittest tests.test_wizard_app.TestPreview -v`

- [ ] **Step 5: Commit**

```bash
git add tools/wizard_app.py tests/test_wizard_app.py tests/test_setup.py tests/fixtures/
git commit -m "feat(wizard): live preview via real renderer fixture, debounced (FR-W.4/T3.3)"
```

---

### Task 3.4: Persist via the existing writer/validator + round-trip

**Files:**
- Modify: `tools/setup.py` — `_persist_layout(paths, state, dry)` calling `save_statusline_config` (reuse `_segment_changes_vs_recipe` + layout-diff from the old `_save_and_report`).
- Test: `tests/test_setup.py` (`TestPersistRoundTrip`)

**Interfaces:**
- Consumes: `save_statusline_config(path, seg_changes, layout, statusline_doctor)`, `_segment_changes_vs_recipe`, `current_layout`.
- Produces: `_persist_layout(paths, state, dry) -> bool` — writes only the diff; doctor-validates; returns success. On `dry`, writes nothing.

- [ ] **Step 1: Write the round-trip test (C.2 #2 unit half)**

```python
class TestPersistRoundTrip(unittest.TestCase):
    def test_layout_change_round_trips_and_doctor_passes(self):
        cfg = self._seed_recipe()                # copy statusline.toml.sample to tmp
        state = {"segments": setup.current_segments(cfg),
                 "layout": setup.current_layout(cfg), "dirty": True}
        state["layout"][0]["segments"].reverse() # a real change
        ok = setup._persist_layout(_paths(cfg), state, dry=False)
        self.assertTrue(ok)
        self.assertEqual(setup.current_layout(cfg)[0]["segments"],
                         state["layout"][0]["segments"])   # re-read == written
```

- [ ] **Step 2: Run (FAIL); Step 3: implement `_persist_layout`; Step 4: run (PASS).**

Run: `python3 -m unittest tests.test_setup.TestPersistRoundTrip -v`

- [ ] **Step 5: Drift guard** — extend the existing `LAYOUT_DEFAULTS` drift test (`test_setup.py:80-92`) to also assert a layout round-trip through `patch_layout` preserves segment membership. Commit:

```bash
git add tools/setup.py tests/test_setup.py
git commit -m "feat(wizard): persist layout via doctor-validated writer + round-trip guard (FR-W.5/T3.4)"
```

---

### Task 3.5: Phase-3 E2E (PTY) — arrange + confirm; TOML + doctor pass

**Files:**
- Modify: `tests/test_wizard_pty.py` (`TestPhase3E2E`)

- [ ] **Step 1: Full-flow E2E (C.2 #1 complete + #2):** under a PTY (`uv run`), navigate to the board, move one chip across lines + toggle one segment, confirm; then assert (a) the written `statusline.toml` reflects the arrangement and (b) `python3 -S tools/statusline-doctor.py --check` exits 0 against it. Add a **reconfigure** scenario: relaunch and assert the board pre-loads the saved arrangement.

- [ ] **Step 2: Run; Step 3: Commit**

```bash
git add tests/test_wizard_pty.py
git commit -m "test(wizard): Phase-3 PTY E2E — arrange+confirm, TOML round-trip, doctor passes (Addendum C #1,#2)"
```

---

# Phase 4 — Hardening, docs, gate

### Task 4.1: Crash safety + small-terminal — restore screen, exit non-zero

**Files:**
- Modify: `tools/wizard_app.py` (top-level guard), `tools/setup.py` (`launch_wizard` wraps the run)
- Test: `tests/test_wizard_app.py` (`TestCrashSafety`), `tests/test_wizard_pty.py` (Ctrl-C E2E)

**Interfaces:**
- Produces: an unhandled exception in the app restores the terminal (Textual teardown), prints a one-line reason to stderr, and `launch_wizard` exits non-zero — **no menu fall-through** (Addendum B). A too-small terminal prints a reason and exits non-zero before entering the alternate screen.

- [ ] **Step 1: Write failing tests**

```python
async def test_unhandled_error_restores_and_reports(self):
    # inject a failing engine.render_preview → app must exit cleanly, not hang
    ...
# PTY: send Ctrl-C mid-flow → original config intact, no temp files (C.2 #6)
def test_ctrl_c_leaves_config_intact(self): ...
```

- [ ] **Step 2-4:** Run (FAIL) → implement size check + exception guard → run (PASS).

- [ ] **Step 5: Commit**

```bash
git add tools/wizard_app.py tools/setup.py tests/
git commit -m "feat(wizard): crash-safe teardown + small-term guard, fail-closed; Ctrl-C E2E (Addendum B, C #6)"
```

---

### Task 4.2: Docs — README wizard section + keybindings

**Files:**
- Modify: `README.md`

- [ ] **Step 1:** Document: the rich wizard, the `uv` requirement (and that it's wizard-only — render stays stdlib), the layout editor keybindings (`↑↓`/`j k` across lines, `←→`/`h l` within a line, `space` toggle, `a`/`n` all/none, `enter` confirm, `q`/`esc`/Ctrl-C abort), and the fail-closed behavior when no tty/uv. Note the off-tray and that gate/line add-remove is deferred.

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs(wizard): README — rich wizard, uv requirement, keybindings, fail-closed (FR-W docs)"
```

---

### Task 4.3: Full gate + fresh-subagent verification

**Files:** none (verification + memory)

- [ ] **Step 1:** Run the full gate.

Run: `make validate` (or `pre-commit run --all-files`) and `python3 -m unittest discover tests` and `uv run python -m unittest discover tests`.
Expected: all green; status-line golden output byte-identical; `git grep -nE "chip_select|_mode_a_available|except Exception" tools/setup.py` empty.

- [ ] **Step 2:** Dispatch a **fresh subagent** to run the acceptance commands (the 7 PTY E2E scenarios + `--doctor`/`--check`) and return raw PASS output. Do not tick any acceptance box without that raw output (PRD User Acceptance).

- [ ] **Step 3: Code-review gate (G-W).** Run `/requesting-code-review` + `/simplify` scoped to the branch; resolve HIGH/CRITICAL before merge.

- [ ] **Step 4:** Update memory: wizard v2 status, the reuse seam (`Selection`/`state`/`_apply_wizard_command`), the uv-is-wizard-only invariant. Commit any doc/memory deltas.

```bash
git add -A && git commit -m "chore(wizard): close-out — gate green, fresh-subagent verification, memory"
```

---

## Self-Review

**Spec coverage (PRD body + Addenda A/B/C):**
- FR-W.1 → Task 1.1 (open_tty matrix) + 1.4 (E2E #3). ✓
- FR-W.2 → Task 1.3 (uv bootstrap, loop guard, fail-closed) + 1.4 (E2E #5). ✓
- FR-W.3 → Tasks 2.1–2.3 (skeleton, install-picks, summary/confirm) + 2.4 (E2E #1 partial). ✓
- FR-W.4 → Tasks 3.1 (model/off-tray/gate) + 3.2 (board) + 3.3 (preview) + 3.5 (E2E). ✓
- FR-W.5 → Task 3.4 (doctor-validated persist + round-trip) + 3.5 (E2E #2). ✓
- FR-W.6 → Task 1.2 (delete selector/fallback; grep proof). ✓
- FR-W.7 → Tasks 2.2 (glyph state) + 2.3 (summary/confirm/empty/abort). ✓
- Addendum B (single path, fail-closed, deletions) → Tasks 1.1/1.2/1.3/4.1. ✓
- Addendum C (PTY E2E, phase-local, mandatory) → Tasks 1.4, 2.4, 3.3(fixture pin), 3.5, 4.1, 4.3. ✓
- Render-path purity / module seam invariants → Global Constraints + DI in 2.1; verified by 4.3 grep + golden. ✓
- `install.sh` mechanics retained (Addendum B.3) → no task deletes it; `test_install.sh` untouched unless a flag changes. ✓

**Type consistency:** `WizardContext`/`WizardResult`/`run_wizard`/`WizardApp` names are consistent across 2.1→4.1; `layout_move(state, seg, direction)`/`off_tray(state)` consistent 3.1→3.2; engine callables (`render_preview`, `apply_command`, `groups`, `order`, `layout_move`, `off_tray`) are the single injected set. `save_statusline_config(path, seg_changes, layout, statusline_doctor)` used verbatim from the codebase.

**Placeholder scan:** Textual widget-API specifics (`SelectionList` option shape, `Pilot` press semantics, debounce timer) are explicitly flagged for context7 confirmation during execution rather than guessed — the surrounding structure, interfaces, and all tests are concrete. No "TBD"/"add error handling"/"similar to" placeholders remain.

---

**Plan Version:** 1.0 · **Created:** 2026-06-23 · Spec: `docs/prds/install-wizard-tui-v1.0-prd.md` (body + Addenda A/B/C)
