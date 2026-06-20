"""End-to-end pseudo-terminal tests for the mode-A chip selector (FR-7.4 / T4.5).

These drive `chip_select` on a REAL pty with raw arrow/space/enter byte
sequences and assert on the rendered frames + the final selection — the one
path the headless unit tests cannot cover, because raw mode + the byte reader
only behave on an actual terminal. The non-tty fallback (flag/default contract)
is asserted by running the same driver with a pipe instead of a pty.
"""
import os
import select
import subprocess
import sys
import textwrap
import time
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_SETUP = os.path.join(_HERE, "..", "tools", "setup.py")

try:
    import pty
    import termios
    _PTY_OK = True
except ImportError:                       # non-POSIX
    _PTY_OK = False


def _driver(headless=False):
    """Source for a child process that runs chip_select over a fixed 3-item
    Selection and prints RESULT:<comma-joined enabled names>. With headless=True
    it instead exercises the gate directly so a non-tty falls straight through."""
    return textwrap.dedent(f"""
        import importlib.util, os, sys
        spec = importlib.util.spec_from_file_location("setup", {_SETUP!r})
        m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
        os.environ["TERM"] = "xterm-256color"
        os.environ["COLUMNS"] = "80"; os.environ["LINES"] = "24"
        sel = m.Selection([("seg", "alpha", False),
                           ("seg", "beta", False),
                           ("seg", "gamma", False)])
        gate = m._mode_a_available(os.environ, sys.stdin, sys.stdout)
        if {headless!r}:
            sys.stdout.write("GATE:" + ("on" if gate else "off") + "\\n")
            sys.stdout.flush()
        elif gate:
            try:
                m.chip_select(sel, sys.stdin, sys.stdout, os.environ)
            except KeyboardInterrupt:
                pass
            sys.stdout.write("\\nRESULT:"
                             + ",".join(n for _c, n, e in sel.items if e) + "\\n")
            sys.stdout.flush()
    """)


def _read_available(fd, timeout=0.4):
    out = bytearray()
    while True:
        r, _, _ = select.select([fd], [], [], timeout)
        if not r:
            break
        try:
            chunk = os.read(fd, 4096)
        except OSError:
            break
        if not chunk:
            break
        out += chunk
        timeout = 0.1
    return bytes(out)


@unittest.skipUnless(_PTY_OK, "pty/termios unavailable (non-POSIX)")
class TestChipSelectPty(unittest.TestCase):
    def _spawn(self, headless=False):
        master, slave = pty.openpty()
        import fcntl
        import struct
        fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", 24, 80, 0, 0))
        proc = subprocess.Popen(
            [sys.executable, "-c", _driver(headless)],
            stdin=slave, stdout=slave, stderr=subprocess.PIPE, close_fds=True)
        os.close(slave)
        return proc, master

    def test_chip_drive_arrows_space_enter_selects(self):
        proc, master = self._spawn()
        transcript = bytearray()
        try:
            transcript += _read_available(master)          # first frame
            for key in (b"\x1b[B", b" ", b"\x1b[B", b" ", b"\r"):
                os.write(master, key)
                time.sleep(0.08)
                transcript += _read_available(master)
            proc.wait(timeout=10)
            transcript += _read_available(master)
        finally:
            os.close(master)
            if proc.poll() is None:
                proc.kill()
            if proc.stderr:
                proc.stderr.close()
        text = transcript.decode(errors="replace")
        # rendered the chips + reverse-video focus + live tally, and toggled
        # beta+gamma via arrow/space/enter, accepted with Enter.
        self.assertIn("alpha", text)
        self.assertIn("\x1b[7m", text)                     # reverse-video focus
        self.assertIn("RESULT:beta,gamma", text)

    def test_non_tty_gate_is_off(self):
        # The flag/default contract: with stdin/stdout a PIPE (not a tty), the
        # gate is off → no raw mode, no prompt, falls through immediately.
        proc = subprocess.run(
            [sys.executable, "-c", _driver(headless=True)],
            stdin=subprocess.DEVNULL, capture_output=True, timeout=10, text=True)
        self.assertIn("GATE:off", proc.stdout)


if __name__ == "__main__":
    unittest.main()
