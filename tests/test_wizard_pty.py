"""Phase-1 and Phase-2 PTY E2E tests for the install wizard.

These tests spawn ``setup.py`` via ``uv run --script`` — the canonical
invocation — so that ``textual`` resolves (8.2.7, cache is warm) and
``ensure_rich_runtime`` exits cleanly as a no-op, isolating exactly the
fail-closed / interactive-terminal behaviour being exercised.

Scenarios:
  TestPhase1E2E.test_no_tty_exits_nonzero_with_reason   (C.2 #4)
  TestPhase1E2E.test_interactive_under_pty_runs_to_completion  (C.2 #3)
  TestPhase2E2E.test_pick_skill_and_confirm_creates_symlink    (C.2 #1 partial)

The uv-guard re-exec scenario (C.2 #5) is fully covered by unit tests in
``TestUvBootstrap`` in ``test_setup.py`` and is not duplicated here.
"""

import contextlib
import os
import pty
import select
import shutil
import subprocess
import tempfile
import time
import unittest

# Absolute path to the wizard so the tests work from any cwd.
SETUP = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "tools", "setup.py"))

# Repo root: one level above tests/
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# Prefer the uv on PATH; fall back to the standard astral install location.
_UV_WHICH = shutil.which("uv") or os.path.expanduser("~/.local/bin/uv")

# A known skill that must be symlinked on a fresh all-ON install (first entry
# alphabetically, confirmed by enumerate_entries against the live repo).
_KNOWN_SKILL = "applying-review-feedback"


def _uv_cmd():
    """Return the uv executable path, skipping the test if uv is not found."""
    if _UV_WHICH and os.path.exists(_UV_WHICH):
        return _UV_WHICH
    raise unittest.SkipTest("uv not found — skipping PTY E2E tests")


def _tmp_config_dir():
    """Create and return a fresh temp dir for CLAUDE_CONFIG_DIR."""
    return tempfile.mkdtemp(prefix="ai-kit-test-")


# ---------------------------------------------------------------------------
# Shared PTY helpers (seam for both Phase-1 and Phase-2 tests)
# ---------------------------------------------------------------------------

def spawn_pty(args, env):
    """Fork a child process under a PTY, running ``args`` in ``env``.

    Returns ``(pid, master_fd)``.  The child's stdin/stdout/stderr and
    controlling terminal are all the PTY slave by virtue of ``pty.fork()``.

    The caller is responsible for:
      - writing keystrokes to ``master_fd`` (parent side of the PTY),
      - draining output from ``master_fd``,
      - calling ``os.waitpid(pid, 0)`` when done.

    Uses ``os.execvpe`` in the child so the PATH in ``env`` is honoured.
    On ``execvpe`` failure the child calls ``os._exit(127)`` — bypassing
    atexit handlers — to avoid corrupting the parent's stdio.
    """
    pid, master_fd = pty.fork()
    if pid == 0:
        # Child: replace this process image.  contextlib.suppress absorbs the
        # OSError from execvpe on success (never reached) and on the unlikely
        # failure path we fall through to os._exit.
        with contextlib.suppress(OSError):
            os.execvpe(args[0], args, env)
        os._exit(127)
    return pid, master_fd


def spawn_pty_piped_stdin(args, env, pipe_data=b"# leftover script bytes\n"):
    """Spawn ``args`` in the exact shape of ``curl … | bash``: the controlling
    terminal is a PTY, but the child's **fd 0 (stdin) is a pipe**, not the PTY.

    ``pty.fork()`` gives the child the PTY slave as fds 0/1/2 *and* as its
    controlling terminal.  We then ``dup2`` a pipe onto fd 0 only, so:
      - ``os.isatty(0)`` is False (stdin is the script pipe, like curl | bash),
      - ``/dev/tty`` still resolves to the PTY (fds 1/2 and the ctty are intact).

    The parent writes ``pipe_data`` then closes the write end (EOF), mimicking
    bash having drained the script before exec.  Keystrokes are driven through
    ``master_fd`` — i.e. only reachable via ``/dev/tty``, never via fd 0 — so a
    wizard that responds to them *proves* it read the controlling terminal.

    Returns ``(pid, master_fd)``.
    """
    r, w = os.pipe()
    pid, master_fd = pty.fork()
    if pid == 0:
        os.close(w)
        os.dup2(r, 0)        # stdin ← pipe (NOT the PTY); fds 1/2 stay the PTY
        os.close(r)
        with contextlib.suppress(OSError):
            os.execvpe(args[0], args, env)
        os._exit(127)
    os.close(r)
    with contextlib.suppress(OSError):
        os.write(w, pipe_data)
    os.close(w)              # EOF on stdin, as after bash drains the script
    return pid, master_fd


def drive_until(master_fd, marker, deadline, captured=None):
    """Poll ``master_fd`` for ``marker`` (bytes), reading until found or ``deadline``.

    ``marker``   — bytes substring to search for in the accumulated output.
    ``deadline`` — absolute epoch time (``time.time() + timeout_secs``).
    ``captured`` — if a ``list`` is provided, all chunks are appended to it
                   so the caller can inspect the full output on failure.

    Returns the accumulated bytes up to and including the chunk that
    contained the marker.  Raises ``AssertionError`` (with the raw output
    decoded) when the deadline expires without finding the marker.

    Tolerates ``OSError``/``ValueError`` from ``select`` when the slave fd
    is closed at child exit.
    """
    chunks: list[bytes] = []
    while time.time() < deadline:
        remaining = max(0.05, deadline - time.time())
        try:
            rlist, _, _ = select.select([master_fd], [], [], min(remaining, 0.5))
        except (OSError, ValueError):
            break
        if not rlist:
            continue
        try:
            data = os.read(master_fd, 4096)
        except OSError:
            break
        if not data:
            break
        chunks.append(data)
        if captured is not None:
            captured.append(data)
        so_far = b"".join(chunks)
        if marker in so_far:
            return so_far
    # Deadline expired without finding the marker.
    so_far = b"".join(chunks)
    decoded = so_far.decode("utf-8", errors="replace")
    raise AssertionError(
        f"drive_until: marker {marker!r} not found before deadline.\n"
        f"Captured output ({len(so_far)} bytes):\n{decoded}"
    )


def _drain(fd, deadline):
    """Read all available bytes from ``fd`` until EOF or ``deadline`` (epoch secs).

    Loops ``select.select`` with a short timeout, reading each ready chunk.
    Tolerates ``OSError`` (slave closed at child exit) and treats it as EOF.
    Returns the accumulated bytes.
    """
    chunks = []
    while time.time() < deadline:
        remaining = max(0.05, deadline - time.time())
        try:
            rlist, _, _ = select.select([fd], [], [], min(remaining, 1.0))
        except (OSError, ValueError):
            break
        if not rlist:
            continue
        try:
            data = os.read(fd, 4096)
        except OSError:
            break
        if not data:
            break
        chunks.append(data)
    return b"".join(chunks)


class TestPhase1E2E(unittest.TestCase):
    """End-to-end smoke tests for Phase-1 wizard behaviour under real process spawning."""

    def setUp(self):
        self._tmpdirs = []

    def tearDown(self):
        for d in self._tmpdirs:
            shutil.rmtree(d, ignore_errors=True)

    def _mk_config_dir(self):
        d = _tmp_config_dir()
        self._tmpdirs.append(d)
        return d

    # ------------------------------------------------------------------
    # C.2 #4 — fail-closed: no tty → exit non-zero + "terminal" message
    # ------------------------------------------------------------------

    def test_no_tty_exits_nonzero_with_reason(self):
        """Wizard exits non-zero and prints a 'terminal' message when no tty is available.

        ``start_new_session=True`` calls ``setsid()``, detaching the controlling
        terminal so ``open('/dev/tty')`` fails.  stdin/stdout/stderr are pipes,
        so the std-stream fallback also sees non-ttys.  ``open_tty()`` returns
        None → ``require_tty`` exits 2 with a human-readable message.

        Spawned via ``uv run --script`` so ``textual`` resolves and
        ``ensure_rich_runtime`` is a clean no-op, keeping the fail-closed
        assertion squarely about the tty check.
        """
        uv = _uv_cmd()
        config_dir = self._mk_config_dir()
        env = dict(os.environ, CLAUDE_CONFIG_DIR=config_dir)
        result = subprocess.run(
            [uv, "run", "--script", SETUP, "install"],
            env=env,
            capture_output=True,
            text=True,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
        )
        self.assertNotEqual(result.returncode, 0,
                            msg="expected non-zero exit when no tty is available")
        combined = (result.stderr + result.stdout).lower()
        self.assertIn("terminal", combined,
                      msg=f"expected 'terminal' in output; got stderr={result.stderr!r}")

    # ------------------------------------------------------------------
    # C.2 #3 — interactive: wizard runs to completion under a real PTY
    # ------------------------------------------------------------------

    def test_interactive_under_pty_runs_to_completion(self):
        """Wizard runs end-to-end and produces output when stdin/stdout are a real PTY.

        ``pty.fork()`` gives the child process a PTY slave as its controlling
        terminal, satisfying both ``open('/dev/tty')`` (the preferred path in
        ``open_tty``) and the ``sys.stdin.isatty()`` fallback.  ``--dry-run``
        ensures no filesystem mutations; the wizard prints the install summary
        and exits 0.  We assert the drained output is non-empty, proving the
        interactive wizard path ran to completion.

        Uses ``spawn_pty`` + ``drive_until`` shared helpers.  After the picks
        screen is ready (marker: ``◉`` glyph or ``Cancel`` Footer label), we
        send ``q`` to abort; the wizard exits and prints the summary line.
        """
        uv = _uv_cmd()
        config_dir = self._mk_config_dir()
        env = dict(os.environ, CLAUDE_CONFIG_DIR=config_dir, AI_KIT_UV_REEXEC="1")

        pid, master_fd = spawn_pty(
            [uv, "run", "--script", SETUP, "--dry-run", "install"],
            env,
        )

        _BOOT_WAIT = 30.0   # generous: uv + textual startup from warm cache ≈ 5-10 s
        _TOTAL_WAIT = 60    # total wall-clock budget for the full run

        startup_output = b""
        try:
            # Wait until the picks screen renders (glyph ◉ or Footer "Cancel").
            boot_deadline = time.time() + _BOOT_WAIT
            _PICKS_MARKERS = (b"\xe2\x97\x89", b"Cancel", b"\x1b[")  # ◉ (UTF-8), footer, ANSI
            all_captured: list[bytes] = []
            found = False
            for marker in _PICKS_MARKERS:
                try:
                    startup_output = drive_until(
                        master_fd, marker, boot_deadline, captured=all_captured
                    )
                    found = True
                    break
                except AssertionError:
                    pass
            if not found:
                startup_output = b"".join(all_captured)
        except OSError:
            startup_output = b""

        with contextlib.suppress(OSError):
            os.write(master_fd, b"q")

        drain_deadline = time.time() + max(10, _TOTAL_WAIT - _BOOT_WAIT)
        tail_output = _drain(master_fd, drain_deadline)
        with contextlib.suppress(OSError):
            os.close(master_fd)
        with contextlib.suppress(ChildProcessError):
            os.waitpid(pid, 0)

        output = startup_output + tail_output
        self.assertTrue(
            output,
            msg="wizard produced no output under PTY — the interactive path did not run",
        )
        decoded = output.decode("utf-8", errors="replace")
        self.assertIn("summary:", decoded.lower(),
                      msg=f"expected install summary in output; got {decoded!r}")


# ---------------------------------------------------------------------------
# Phase-2 E2E: confirm → assert symlinks created (C.2 #1 partial)
# ---------------------------------------------------------------------------

class TestPhase2E2E(unittest.TestCase):
    """Drive the Textual wizard to a full confirm and assert symlinks are created.

    Scenario:
      1. Spawn ``setup.py install`` under a PTY with a fresh temp CLAUDE_CONFIG_DIR
         that points at the REPO ROOT as AI_KIT_DIR (so enumerate_entries finds
         the real skills/).
      2. On a fresh install all entries default to ON.
      3. Drive: wait for picks screen → send Enter (→ summary) → wait for
         summary screen → send Enter (→ confirm + apply_selection).
      4. Assert: the known skill ``applying-review-feedback`` was symlinked under
         ``<cfg>/skills/``.

    Timing strategy: ``drive_until`` polls the PTY master fd with ``select``
    and returns as soon as the render marker appears — no blind sleeps.
    """

    def setUp(self):
        self._tmpdirs: list[str] = []

    def tearDown(self):
        for d in self._tmpdirs:
            shutil.rmtree(d, ignore_errors=True)

    def _mk_config_dir(self) -> str:
        d = _tmp_config_dir()
        self._tmpdirs.append(d)
        return d

    def test_pick_skill_and_confirm_creates_symlink(self):
        """Fresh install: accept all-ON defaults → confirm → symlink created.

        The picks default to all-ON on a first run.  The minimal confirm path
        is: Enter (picks → summary) then Enter (summary → confirm).  We then
        assert that at least one known skill symlink exists under the temp
        CLAUDE_CONFIG_DIR/skills.
        """
        uv = _uv_cmd()
        config_dir = self._mk_config_dir()

        # Point AI_KIT_DIR at the repo root so enumerate_entries finds the real
        # skills/ directory.  CLAUDE_CONFIG_DIR is the temp dir — symlinks land
        # there, never touching the real ~/.claude.
        env = dict(
            os.environ,
            CLAUDE_CONFIG_DIR=config_dir,
            AI_KIT_DIR=_REPO_ROOT,
            AI_KIT_UV_REEXEC="1",
        )

        _BOOT_DEADLINE = 45.0   # generous: uv + textual init from warm cache
        _SUMMARY_DEADLINE = 30.0
        _DRAIN_DEADLINE = 30.0

        # Markers chosen from static text the app DEFINITELY renders:
        #   picks screen  → ◉ (UTF-8 bytes) — the glyph prepended to every enabled pick
        #   summary screen → "Install Summary" — the literal header in _build_summary_text
        _PICKS_MARKER = "◉".encode()         # b'\xe2\x97\x89'
        _SUMMARY_MARKER = b"Install Summary"

        pid, master_fd = spawn_pty(
            [uv, "run", "--script", SETUP, "install"],
            env,
        )

        captured: list[bytes] = []
        try:
            # ── Step 1: wait for the picks screen ────────────────────────────
            drive_until(
                master_fd,
                _PICKS_MARKER,
                time.time() + _BOOT_DEADLINE,
                captured=captured,
            )

            # ── Step 2: Enter → navigate to summary screen ───────────────────
            with contextlib.suppress(OSError):
                os.write(master_fd, b"\r")

            # ── Step 3: wait for the summary screen ──────────────────────────
            drive_until(
                master_fd,
                _SUMMARY_MARKER,
                time.time() + _SUMMARY_DEADLINE,
                captured=captured,
            )

            # ── Step 4: Enter → confirm; apply_selection creates symlinks ────
            with contextlib.suppress(OSError):
                os.write(master_fd, b"\r")

            # ── Step 5: drain to completion ───────────────────────────────────
            tail = _drain(master_fd, time.time() + _DRAIN_DEADLINE)
            captured.append(tail)

        finally:
            with contextlib.suppress(OSError):
                os.close(master_fd)
            with contextlib.suppress(ChildProcessError, OSError):
                os.waitpid(pid, 0)

        # ── Step 6: assert symlinks were created ─────────────────────────────
        skills_dir = os.path.join(config_dir, "skills")
        all_output = b"".join(captured).decode("utf-8", errors="replace")

        self.assertTrue(
            os.path.isdir(skills_dir),
            msg=(
                f"Expected <cfg>/skills/ to be created after confirm, "
                f"but it does not exist.\n"
                f"config_dir={config_dir}\n"
                f"Captured output:\n{all_output}"
            ),
        )

        skills_created = os.listdir(skills_dir)
        self.assertTrue(
            skills_created,
            msg=(
                f"Expected at least one symlink under <cfg>/skills/ after confirm, "
                f"but the directory is empty.\n"
                f"Captured output:\n{all_output}"
            ),
        )

        known_link = os.path.join(skills_dir, _KNOWN_SKILL)
        self.assertTrue(
            os.path.islink(known_link),
            msg=(
                f"Expected symlink for known skill {_KNOWN_SKILL!r} at {known_link!r}, "
                f"but it is missing.  Skills present: {skills_created}\n"
                f"Captured output:\n{all_output}"
            ),
        )


# ---------------------------------------------------------------------------
# Phase-3 E2E: arrange layout → confirm → TOML reflects + doctor passes;
# reconfigure pre-loads saved arrangement (Addendum C #1 complete + #2)
# ---------------------------------------------------------------------------

class TestPhase3E2E(unittest.TestCase):
    """Drive the Textual wizard into the LayoutBoard, edit the layout, confirm,
    and assert the written TOML reflects the edit AND the doctor passes.

    Scenario 1 — arrange + confirm:
      1. Spawn ``setup.py install`` under a PTY with temp dirs for both
         CLAUDE_CONFIG_DIR (symlinks land there) and XDG_CONFIG_HOME (config_toml
         lands at ``$XDG_CONFIG_HOME/ai-kit/statusline.toml``).
      2. Drive: picks (◉) → tab (enter LayoutBoard) → wait for board render
         (marker: "identity line:") → space (toggle focused chip "path" to OFF-TRAY)
         → wait for OFF-TRAY marker → enter (board → SummaryScreen) → wait for
         "Install Summary" → enter (confirm).
      3. Assert config_toml has ``path = false`` in [segments] via
         ``current_segments``, and that the doctor passes (exit 0) on the file.

    Scenario 2 — reconfigure pre-loads saved arrangement:
      Pre-seed config_toml with a known non-default layout (path toggled OFF).
      Spawn ``setup.py reconfigure``, drive to the LayoutBoard, and assert the
      board renders "OFF-TRAY" (proving the saved arrangement was pre-loaded).
      Abort cleanly with ``q``.
    """

    # ------------------------------------------------------------------
    # Timing budgets (generous — Textual init can be slow on CI)
    # ------------------------------------------------------------------
    _BOOT_DEADLINE = 45.0    # wait for the picks screen
    _BOARD_DEADLINE = 20.0   # wait for board after tab
    _TRAY_DEADLINE = 10.0    # wait for OFF-TRAY after space
    _SUMMARY_DEADLINE = 20.0 # wait for SummaryScreen after enter
    _DRAIN_DEADLINE = 30.0   # drain to completion

    def setUp(self) -> None:
        self._tmpdirs: list[str] = []

    def tearDown(self) -> None:
        for d in self._tmpdirs:
            shutil.rmtree(d, ignore_errors=True)

    def _mk_temp_dir(self) -> str:
        d = tempfile.mkdtemp(prefix="ai-kit-p3-")
        self._tmpdirs.append(d)
        return d

    def _base_env(self, claude_dir: str, xdg_config_home: str) -> dict:
        """Build a minimal env with temp dirs, AI_KIT_UV_REEXEC bypass, and
        AI_KIT_DIR pointing at the repo root so enumerate_entries finds skills/."""
        return dict(
            os.environ,
            CLAUDE_CONFIG_DIR=claude_dir,
            XDG_CONFIG_HOME=xdg_config_home,
            AI_KIT_DIR=_REPO_ROOT,
            AI_KIT_UV_REEXEC="1",
        )

    def _config_toml_path(self, xdg_config_home: str) -> str:
        """Compute the config_toml path given XDG_CONFIG_HOME.

        Mirrors ``resolve_paths``: config_toml = XDG_CONFIG_HOME/ai-kit/statusline.toml.
        """
        return os.path.join(xdg_config_home, "ai-kit", "statusline.toml")

    def _seed_config_toml(self, config_toml: str, content: str) -> None:
        """Write ``content`` to ``config_toml``, creating parent dirs."""
        os.makedirs(os.path.dirname(config_toml), exist_ok=True)
        with open(config_toml, "w", encoding="utf-8") as f:
            f.write(content)

    def _run_doctor_check(self, config_toml: str) -> int:
        """Run ``statusline-doctor.py --check <FILE>`` and return the exit code."""
        doctor = os.path.join(_REPO_ROOT, "tools", "statusline-doctor.py")
        result = subprocess.run(
            ["python3", "-S", doctor, "--check", config_toml],
            capture_output=True,
            timeout=20,
        )
        return result.returncode

    # ------------------------------------------------------------------
    # Scenario 1
    # ------------------------------------------------------------------

    def test_arrange_confirm_toml_reflects_and_doctor_passes(self):
        """arrange (space-toggle path to OFF-TRAY) + confirm → TOML has path=false +
        doctor passes.  Proves the full write pipeline: LayoutBoard state →
        _persist_layout → save_statusline_config → doctor-validated TOML."""
        uv = _uv_cmd()
        claude_dir = self._mk_temp_dir()
        xdg_home = self._mk_temp_dir()
        config_toml = self._config_toml_path(xdg_home)
        env = self._base_env(claude_dir, xdg_home)

        pid, master_fd = spawn_pty(
            [uv, "run", "--script", SETUP, "install"],
            env,
        )
        captured: list[bytes] = []
        try:
            # ── Step 1: wait for the picks screen ────────────────────────────
            drive_until(
                master_fd,
                "◉".encode(),
                time.time() + self._BOOT_DEADLINE,
                captured=captured,
            )

            # ── Step 2: tab → enter LayoutBoard ──────────────────────────────
            with contextlib.suppress(OSError):
                os.write(master_fd, b"\t")

            # ── Step 3: wait for board render (label: "identity line:") ──────
            # The board always renders "  identity line:" as the first row header.
            drive_until(
                master_fd,
                b"identity line:",
                time.time() + self._BOARD_DEADLINE,
                captured=captured,
            )

            # ── Step 4: space → toggle focused chip ("path") to OFF-TRAY ─────
            # On mount, focused_seg = "path" (first chip of first layout line).
            # After toggle, board re-renders and appends "  OFF-TRAY: ..."
            with contextlib.suppress(OSError):
                os.write(master_fd, b" ")

            # ── Step 5: wait for OFF-TRAY to confirm the toggle rendered ──────
            drive_until(
                master_fd,
                b"OFF-TRAY:",
                time.time() + self._TRAY_DEADLINE,
                captured=captured,
            )

            # ── Step 6: enter → board pushes SummaryScreen ───────────────────
            with contextlib.suppress(OSError):
                os.write(master_fd, b"\r")

            # ── Step 7: wait for SummaryScreen ───────────────────────────────
            drive_until(
                master_fd,
                b"Install Summary",
                time.time() + self._SUMMARY_DEADLINE,
                captured=captured,
            )

            # ── Step 8: enter → confirm (apply_selection + _persist_layout) ───
            with contextlib.suppress(OSError):
                os.write(master_fd, b"\r")

            # ── Step 9: drain to completion ───────────────────────────────────
            tail = _drain(master_fd, time.time() + self._DRAIN_DEADLINE)
            captured.append(tail)

        finally:
            with contextlib.suppress(OSError):
                os.close(master_fd)
            with contextlib.suppress(ChildProcessError, OSError):
                os.waitpid(pid, 0)

        all_output = b"".join(captured).decode("utf-8", errors="replace")

        # ── Assert 1: config_toml was written ────────────────────────────────
        self.assertTrue(
            os.path.isfile(config_toml),
            msg=(
                f"Expected config_toml to be written at {config_toml!r} after confirm,\n"
                f"but it does not exist.\n"
                f"XDG_CONFIG_HOME={xdg_home}\n"
                f"Captured output:\n{all_output}"
            ),
        )

        # Import setup.py as a module to use current_segments / current_layout.
        import importlib.util as _ilu
        spec = _ilu.spec_from_file_location("_setup", SETUP)
        setup_mod = _ilu.module_from_spec(spec)  # type: ignore[arg-type]
        spec.loader.exec_module(setup_mod)  # type: ignore[union-attr]

        segs = setup_mod.current_segments(config_toml)

        # ── Assert 2: the toggled segment ("path") is present AND explicitly False ──
        self.assertIn(
            "path",
            segs,
            msg=(
                f"Expected 'path' key in segments dict (toggled to OFF-TRAY), "
                f"but key is absent.\n"
                f"Full segments: {segs}\n"
                f"config_toml={config_toml}\n"
                f"Captured output:\n{all_output}"
            ),
        )
        self.assertIs(
            segs["path"],
            False,
            msg=(
                f"Expected segments['path'] is False after toggling it to the "
                f"OFF-TRAY, but got: {segs['path']!r}\n"
                f"Full segments: {segs}\n"
                f"config_toml={config_toml}\n"
                f"Captured output:\n{all_output}"
            ),
        )

        # ── Assert 3: doctor passes on the written config ─────────────────────
        doctor_rc = self._run_doctor_check(config_toml)
        self.assertEqual(
            doctor_rc, 0,
            msg=(
                f"statusline-doctor.py --check {config_toml!r} exited {doctor_rc} "
                f"(expected 0 — config should be valid after wizard write).\n"
                f"Captured output:\n{all_output}"
            ),
        )

    # ------------------------------------------------------------------
    # Scenario 2
    # ------------------------------------------------------------------

    def test_reconfigure_preloads_saved_arrangement(self):
        """reconfigure pre-loads the on-disk arrangement into the LayoutBoard.

        Pre-seeds config_toml with path=false (path toggled OFF).  Spawns
        reconfigure, drives to the LayoutBoard, and asserts "OFF-TRAY:" appears in
        the board — proving the wizard loaded the on-disk state, not the defaults.
        Then aborts with ``q`` (no write).
        """
        uv = _uv_cmd()
        claude_dir = self._mk_temp_dir()
        xdg_home = self._mk_temp_dir()
        config_toml = self._config_toml_path(xdg_home)
        env = self._base_env(claude_dir, xdg_home)

        # Pre-seed config_toml with path=false so the saved state differs from
        # defaults (defaults: path=true).  The doctor accepts this file.
        self._seed_config_toml(
            config_toml,
            "[segments]\npath = false\n",
        )

        # Verify the doctor accepts the pre-seeded file before we even run.
        pre_check_rc = self._run_doctor_check(config_toml)
        self.assertEqual(
            pre_check_rc, 0,
            msg=f"Pre-seeded config_toml is not valid; doctor check returned {pre_check_rc}",
        )

        pid, master_fd = spawn_pty(
            [uv, "run", "--script", SETUP, "reconfigure"],
            env,
        )
        captured: list[bytes] = []
        try:
            # ── Step 1: wait for the picks screen ────────────────────────────
            drive_until(
                master_fd,
                "◉".encode(),
                time.time() + self._BOOT_DEADLINE,
                captured=captured,
            )

            # ── Step 2: tab → enter LayoutBoard ──────────────────────────────
            with contextlib.suppress(OSError):
                os.write(master_fd, b"\t")

            # ── Step 3: wait for board render — drain until "identity line:" ────
            # The board renders both the layout lines AND the OFF-TRAY in one
            # call to _render_board().  We wait until "identity line:" is in
            # the accumulated output; "OFF-TRAY:" will be in the SAME render
            # frame (already buffered) so we check captured directly afterward
            # rather than issuing a second drive_until that would block on fresh
            # bytes.
            drive_until(
                master_fd,
                b"identity line:",
                time.time() + self._BOARD_DEADLINE,
                captured=captured,
            )

            # Give the TUI one more short poll to finish flushing the render frame.
            # (drive_until returns as soon as "identity line:" hits; "OFF-TRAY:"
            # may still be in the pipe buffer.)
            tail_board = _drain(master_fd, time.time() + 3.0)
            if tail_board:
                captured.append(tail_board)

            # ── Step 4: abort cleanly ─────────────────────────────────────────
            with contextlib.suppress(OSError):
                os.write(master_fd, b"q")

            tail = _drain(master_fd, time.time() + 10.0)
            captured.append(tail)

        finally:
            with contextlib.suppress(OSError):
                os.close(master_fd)
            with contextlib.suppress(ChildProcessError, OSError):
                os.waitpid(pid, 0)

        # Verify that the board text contained OFF-TRAY (already asserted above;
        # this assertion is explicit for the test report).
        all_output = b"".join(captured).decode("utf-8", errors="replace")
        self.assertIn(
            "OFF-TRAY:",
            all_output,
            msg=(
                f"Expected 'OFF-TRAY:' in board output after reconfigure with "
                f"pre-seeded path=false layout.\n"
                f"Captured output:\n{all_output}"
            ),
        )

        # Confirm path is in the off-tray (appears with parens or focus brackets)
        # The board renders tray chips as (chip) or [>chip<] for focused.
        path_in_tray = "(path)" in all_output or "[>path<]" in all_output
        self.assertTrue(
            path_in_tray,
            msg=(
                f"Expected 'path' chip to appear in OFF-TRAY (as '(path)' or '[>path<]'), "
                f"but it was not found.\n"
                f"Captured output:\n{all_output}"
            ),
        )


class TestCurlBashE2E(unittest.TestCase):
    """The ``curl … | bash`` install shape: stdin is the script pipe (not a
    TTY), but a controlling terminal exists via ``/dev/tty``.

    This is the path the PTY suites above do NOT cover — they hand the child a
    real TTY as stdin.  Without ``stdin_on_tty()`` redirecting fd 0 onto
    ``/dev/tty``, Textual (which reads keys from ``sys.__stdin__.fileno()``)
    sees the pipe and the wizard cannot be driven.  Here keystrokes are sent
    only through the PTY master — reachable solely as the controlling terminal
    — so a wizard that renders and responds proves the redirect works.
    """

    def setUp(self):
        self._tmpdirs = []

    def tearDown(self):
        for d in self._tmpdirs:
            shutil.rmtree(d, ignore_errors=True)

    def _mk_config_dir(self):
        d = _tmp_config_dir()
        self._tmpdirs.append(d)
        return d

    def test_piped_stdin_wizard_still_driven_via_dev_tty(self):
        uv = _uv_cmd()
        config_dir = self._mk_config_dir()
        env = dict(
            os.environ,
            CLAUDE_CONFIG_DIR=config_dir,
            AI_KIT_DIR=_REPO_ROOT,
            AI_KIT_UV_REEXEC="1",
        )

        # stdin = pipe (curl|bash); ctty + stdout/stderr = PTY.
        pid, master_fd = spawn_pty_piped_stdin(
            [uv, "run", "--script", SETUP, "--dry-run", "install"],
            env,
        )

        _BOOT_WAIT = 30.0
        _TOTAL_WAIT = 60

        startup_output = b""
        try:
            boot_deadline = time.time() + _BOOT_WAIT
            # Picks screen rendering at all means Textual is reading the PTY —
            # impossible unless fd 0 was redirected off the pipe onto /dev/tty.
            _PICKS_MARKERS = (b"\xe2\x97\x89", b"Cancel", b"\x1b[")  # ◉, footer, ANSI
            all_captured: list[bytes] = []
            found = False
            for marker in _PICKS_MARKERS:
                try:
                    startup_output = drive_until(
                        master_fd, marker, boot_deadline, captured=all_captured
                    )
                    found = True
                    break
                except AssertionError:
                    pass
            if not found:
                startup_output = b"".join(all_captured)
        except OSError:
            startup_output = b""

        # Drive a keystroke through the PTY (i.e. via /dev/tty, never via fd 0):
        # 'q' aborts the wizard.  A clean abort exit proves the key was received.
        with contextlib.suppress(OSError):
            os.write(master_fd, b"q")

        drain_deadline = time.time() + max(10, _TOTAL_WAIT - _BOOT_WAIT)
        tail_output = _drain(master_fd, drain_deadline)
        with contextlib.suppress(OSError):
            os.close(master_fd)
        exit_code = None
        with contextlib.suppress(ChildProcessError):
            _, status = os.waitpid(pid, 0)
            exit_code = os.WEXITSTATUS(status)

        output = startup_output + tail_output
        decoded = output.decode("utf-8", errors="replace")
        # The wizard rendered under piped stdin — only possible via the /dev/tty
        # redirect.  (ANSI escapes / the picks glyph / the summary all qualify.)
        self.assertTrue(
            output,
            msg="wizard produced no output under piped stdin — the /dev/tty "
                "redirect did not take effect",
        )
        self.assertTrue(
            ("\x1b[" in decoded) or ("◉" in decoded) or ("summary:" in decoded.lower()),
            msg=f"wizard did not render a TUI under piped stdin; got {decoded!r}",
        )
        # 'q' abort is a clean exit; a hung/failed driver would not exit 0.
        self.assertEqual(
            exit_code, 0,
            msg=f"expected clean abort exit 0 under piped stdin; got {exit_code}, "
                f"output={decoded!r}",
        )


if __name__ == "__main__":
    unittest.main()
