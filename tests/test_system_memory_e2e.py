"""T5.4 — End-to-end install + render of the system_memory example external segment.

Hermetic: one self-contained tmpdir is the fake HOME and the ai-kit install dir,
so the suite never touches the live workspace. Runs the REAL setup.py installer
through a real pseudo-tty (tools/setup.py's wizard is fail-closed on tty since
the wizard redesign — see `open_tty`/`require_tty` in tools/setup.py — so a
headless subprocess can no longer reach the install path at all; `--examples=all`
only ever overrides which EXAMPLE segments get installed, it does not bypass the
main install wizard). A pty gives the subprocess a genuine controlling terminal,
so the real Textual wizard launches; scripted keystrokes walk it through its
default "adopt everything, confirm" path (Choose -> Arrange -> gate -> Review ->
commit -> Done -> exit), exactly the sequence `tests/test_wizard_app.py`'s
`TestReviewDone.test_review_enter_commits_and_done` exercises in-process. This
then asserts the system_memory provider lands executable under
~/.config/ai-kit/segments/, and renders the REAL status-line.py to assert the
system_memory segment shows up in the output line.

The render assertion needs a platform whose available memory the provider can
read (Linux /proc/meminfo); it is skipped elsewhere. The install/executable
assertions are platform-independent.
"""
import fcntl
import json
import os
import re
import select
import shutil
import signal
import stat
import struct
import subprocess
import sys
import tempfile
import termios
import time
import types
import unittest

_HERE = os.path.dirname(__file__)
_REPO = os.path.abspath(os.path.join(_HERE, ".."))
_ANSI = re.compile(r"\033\[[0-9;]*m")
# The wizard is a full-screen Textual TUI: every redraw is full of cursor-
# positioning CSI sequences (e.g. `\033[4;3H`), not just SGR color codes.
# Stripping only `...m` (as `_ANSI` does, correct for status-line.py's
# single-line, color-only output) leaves those `...H`/etc. sequences in
# place and can fragment a word like "Review" mid-string — matching against
# that half-stripped text can time out even though the wizard rendered the
# text just fine. Strip the full CSI grammar (`ESC [ params letter`) instead.
_CSI = re.compile(r"\033\[[0-9;?]*[A-Za-z]")


def _pty_read_until(master_fd, pattern, buf, timeout=20):
    """Read from `master_fd` into `buf[0]`, until the CSI-stripped decoded
    text matches `pattern` (a compiled regex). Raises AssertionError with the
    captured transcript on timeout — this is a small hand-rolled substitute
    for pexpect's `expect()` (not a project dependency), sized for driving
    exactly one Textual screen transition at a time."""
    deadline = time.monotonic() + timeout
    while True:
        text = _CSI.sub("", buf[0].decode("utf-8", "replace"))
        if pattern.search(text):
            return
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise AssertionError(
                f"timed out waiting for {pattern.pattern!r} in wizard output.\n"
                f"--- captured so far ---\n{text}")
        ready, _, _ = select.select([master_fd], [], [], min(remaining, 0.25))
        if master_fd not in ready:
            continue
        try:
            chunk = os.read(master_fd, 65536)
        except OSError:
            return
        if not chunk:
            return
        buf[0] += chunk


def _run_wizard_install(argv, env, timeout=45):
    """Drive `tools/setup.py install --examples=all` through a REAL pty so the
    wizard's fail-closed `open_tty()`/`require_tty()` gate sees a genuine
    controlling terminal and launches for real (see module docstring). Scripts
    the wizard's default accept-everything path and returns a
    `types.SimpleNamespace(returncode, stdout, stderr)` shaped like a
    `subprocess.run(..., capture_output=True, text=True)` result (stdout and
    stderr both carry the same combined transcript — Textual writes its own
    redraws to stderr, see `stdin_on_tty`'s docstring in tools/setup.py, and
    normal prints go to stdout; a single pty merges both anyway)."""
    import pty as _pty
    master_fd, slave_fd = _pty.openpty()
    # A real size so Textual renders a full wizard screen, not a 0x0 stub.
    fcntl.ioctl(slave_fd, termios.TIOCSWINSZ, struct.pack("HHHH", 40, 120, 0, 0))

    pid = os.fork()
    if pid == 0:
        # Child: become a session leader and make the pty slave our
        # controlling terminal (the standard forkpty dance), then exec.
        try:
            os.close(master_fd)
            os.setsid()
            fcntl.ioctl(slave_fd, termios.TIOCSCTTY, 0)
            os.dup2(slave_fd, 0)
            os.dup2(slave_fd, 1)
            os.dup2(slave_fd, 2)
            if slave_fd > 2:
                os.close(slave_fd)
            os.execvpe(argv[0], argv, env)
        except Exception:  # pylint: disable=broad-exception-caught
            os._exit(127)  # noqa: SLF001 - unreachable except on exec failure
    os.close(slave_fd)

    buf = [b""]

    def _kill_and_reap(grace=3):
        """Hard-kill the child and reap it — used both when the scripted walk
        itself fails partway (fail fast, don't also sit through the full
        drain-timeout below) and as the drain loop's own backstop. Never
        blocks unboundedly: a bounded grace-period drain, then SIGKILL, then
        one bounded reap (falls back to a short poll loop rather than an
        unbounded os.waitpid if even the post-SIGKILL reap is somehow slow)."""
        deadline = time.monotonic() + grace
        while time.monotonic() < deadline:
            ready, _, _ = select.select([master_fd], [], [], 0.25)
            if master_fd in ready:
                try:
                    chunk = os.read(master_fd, 65536)
                except OSError:
                    chunk = b""
                if chunk:
                    buf[0] += chunk
            reaped, status = os.waitpid(pid, os.WNOHANG)
            if reaped == pid:
                return status
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        for _ in range(40):  # up to ~2s of bounded polling, never unbounded
            reaped, status = os.waitpid(pid, os.WNOHANG)
            if reaped == pid:
                return status
            time.sleep(0.05)
        return 0  # gave up reaping; treat as a non-zero-signaling failure below

    try:
        _pty_read_until(master_fd, re.compile(r"\bChoose\b"), buf, timeout)
        os.write(master_fd, b"\r")                      # choose -> arrange (gate)
        _pty_read_until(master_fd, re.compile(r"\bArrange\b"), buf, timeout)
        os.write(master_fd, b"\r")                      # gate: default Yes (adopt)
        os.write(master_fd, b"\r")                       # arrange -> review
        _pty_read_until(master_fd, re.compile(r"\bReview\b"), buf, timeout)
        os.write(master_fd, b"\r")                      # review -> commit
        # The Done screen's title, once the in-UI commit worker finishes, is
        # literally "✓ ai-kit is installed" (see TITLES[STEP_DONE] in
        # tools/wizard_app.py) — NOT the word "Done" (that only appears in
        # the Step-of-3 header pips label and the in-code HELP title, neither
        # of which land in the title line we're scanning). Match "installed"
        # (present only on success; "Installing…" and "install incomplete"
        # are the other two possible titles at this step and don't contain
        # it) so we wait for the real commit to finish, not just the screen
        # transition.
        _pty_read_until(master_fd, re.compile(r"\binstalled\b"), buf, timeout)
        os.write(master_fd, b"\r")                      # done -> exit
    except AssertionError:
        # The scripted walk itself broke (a step never rendered what we
        # expected) — kill fast with a short grace period rather than also
        # sitting through the full drain-timeout below, and preserve the
        # original AssertionError (it already carries the transcript).
        _kill_and_reap(grace=3)
        os.close(master_fd)
        raise

    # Drain remaining output (post-wizard prints: summary/doctor lines) until
    # the child exits, or hard-kill after the overall timeout — never an
    # unbounded blocking wait, so a broken exit path fails this call instead
    # of hanging the whole test run.
    deadline = time.monotonic() + timeout
    reaped_pid = 0
    status = 0
    while time.monotonic() < deadline:
        ready, _, _ = select.select([master_fd], [], [], 0.25)
        if master_fd in ready:
            try:
                chunk = os.read(master_fd, 65536)
            except OSError:
                chunk = b""
            if chunk:
                buf[0] += chunk
        reaped_pid, status = os.waitpid(pid, os.WNOHANG)
        if reaped_pid == pid:
            break
    if reaped_pid != pid:
        status = _kill_and_reap(grace=0)
        os.close(master_fd)
        raise AssertionError(
            "wizard subprocess did not exit within the timeout after the "
            "scripted walkthrough; killed it. captured transcript:\n"
            + _CSI.sub("", buf[0].decode("utf-8", "replace")))
    os.close(master_fd)

    returncode = os.waitstatus_to_exitcode(status)
    output = buf[0].decode("utf-8", "replace")
    return types.SimpleNamespace(returncode=returncode, stdout=output, stderr=output)


class TestSystemMemoryInstallE2E(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="aikit-system-memory-e2e-")
        cls.home = os.path.join(cls.tmp, "home")
        cls.inst = os.path.join(cls.tmp, "share", "ai-kit")
        os.makedirs(cls.home)
        os.makedirs(os.path.join(cls.inst, "examples", "segments"))
        shutil.copy(os.path.join(_REPO, "examples", "segments", "system_memory"),
                    os.path.join(cls.inst, "examples", "segments", "system_memory"))
        shutil.copytree(os.path.join(_REPO, "tools"),
                        os.path.join(cls.inst, "tools"))
        # The wizard now runs for real (see below), and launch_wizard() reads
        # tools/../tests/fixtures/sample-input.json (a live-preview sample for
        # the wizard's status-line preview panel) relative to its own __file__,
        # so that fixture needs to exist under the copied install tree too.
        os.makedirs(os.path.join(cls.inst, "tests", "fixtures"), exist_ok=True)
        shutil.copy(os.path.join(_REPO, "tests", "fixtures", "sample-input.json"),
                    os.path.join(cls.inst, "tests", "fixtures", "sample-input.json"))
        cls.setup_py = os.path.join(cls.inst, "tools", "setup.py")
        cls.status_line = os.path.join(cls.inst, "tools", "status-line.py")
        cls.env = {
            **os.environ,
            "HOME": cls.home,
            "AI_KIT_DIR": cls.inst,
            "CLAUDE_CONFIG_DIR": os.path.join(cls.home, ".claude"),
            "XDG_CACHE_HOME": os.path.join(cls.home, ".cache"),
        }
        # Drop XDG_CONFIG_HOME so config lands at ~/.config/ai-kit — the path the
        # done-definition names and that status-line.py's default segments dir uses.
        cls.env.pop("XDG_CONFIG_HOME", None)
        # The wizard is fail-closed on tty (open_tty/require_tty in tools/setup.py)
        # since the wizard redesign — there is no headless install path any more.
        # Drive the REAL wizard through a real pty so open_tty() sees a genuine
        # controlling terminal (see module docstring + _run_wizard_install).
        cls.proc = _run_wizard_install(
            [sys.executable, cls.setup_py, "install", "--examples=all"],
            cls.env, timeout=60)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def _seg(self):
        return os.path.join(self.home, ".config", "ai-kit", "segments", "system_memory")

    def test_install_succeeded(self):
        self.assertEqual(self.proc.returncode, 0, self.proc.stderr)

    def test_system_memory_installed_and_executable(self):
        self.assertTrue(os.path.isfile(self._seg()),
                        f"system_memory not installed.\nstdout:\n{self.proc.stdout}\n"
                        f"stderr:\n{self.proc.stderr}")
        self.assertTrue(os.stat(self._seg()).st_mode & stat.S_IXUSR,
                        "installed system_memory is not executable")

    @unittest.skipUnless(os.path.exists("/proc/meminfo"),
                         "system_memory reads /proc/meminfo (Linux) to render")
    def test_system_memory_renders_in_status_line(self):
        sample = json.dumps({
            "model": {"display_name": "Opus 4.8", "id": "claude-opus-4-8"},
            "workspace": {"current_dir": self.home},
            "context_window": {"used_percentage": 10, "context_window_size": 200000},
            "transcript_path": "", "session_id": "e2e",
        })
        env = {**self.env, "STATUSLINE_COLS": "200", "STATUSLINE_LINES": "50"}
        p = subprocess.run([sys.executable, self.status_line], input=sample,
                           capture_output=True, text=True, env=env, cwd=self.home)
        self.assertEqual(p.returncode, 0, p.stderr)
        plain = _ANSI.sub("", p.stdout)
        self.assertIn("💻", plain)              # the system_memory segment's glyph
        self.assertIn("free", plain)            # "<N> GiB free" — the long form


if __name__ == "__main__":
    unittest.main()
