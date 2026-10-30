"""The StopFailure hook (26-07, QTA-04, D-30): the reset text refreshes an armed
wake, nothing else ever happens, and the hook always exits before its row's
10 s timeout. Fakes and scratch dirs only (D-26); the hook runs under an explicit
scratch env, never a copy of os.environ, and the stand-in host process keeps the
host lookup away from any real Claude Code."""

import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import uuid
from datetime import UTC, datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "skills",
        "ai-kit-session-wake",
    ),
)

from ai_kit_session_wake import cli, units
from ai_kit_session_wake.state import read_state, session_paths

from tests import session_wake_fakes as fakes

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_HOOK = os.path.join(_REPO, "tools", "hooks", "claude_session_wake.py")
_ZONE = "America/Santiago"
_NOW = datetime(2026, 10, 25, 22, 44, 0, tzinfo=UTC).timestamp()


def _zone_available() -> bool:
    try:
        ZoneInfo(_ZONE)
    except (ZoneInfoNotFoundError, ValueError):
        return False
    return True


def _limit_text() -> str:
    """A limit text whose reset is about two hours after the real now (inside the
    7-day bound), in the host's `resets <H:MMam|pm> (UTC)` form."""
    local = datetime.fromtimestamp(time.time() + 2 * 3600, tz=UTC)
    hour = local.hour % 12 or 12
    suffix = "am" if local.hour < 12 else "pm"
    return f"You've hit your session limit · resets {hour}:{local.minute:02d}{suffix} (UTC)"


class _HookScratch(unittest.TestCase):
    """A scratch root with fake systemctl and loginctl, and a claude session."""

    def setUp(self):
        super().setUp()
        self.root = tempfile.mkdtemp(prefix="wake-hook-")
        self.addCleanup(shutil.rmtree, self.root, True)
        self.bin_dir = os.path.join(self.root, "bin")
        os.makedirs(self.bin_dir)
        self.env = fakes.scoped_env(self.root)
        fakes.fake_systemctl(self.bin_dir)
        fakes.fake_loginctl(self.bin_dir)
        fakes.fake_host(self.bin_dir, "claude")
        self.launch = os.path.join(self.root, "launch")
        os.makedirs(self.launch)
        self.host = fakes.start_host_process(self.launch)
        self.addCleanup(self._kill_host)

    def _kill_host(self):
        self.host.kill()
        self.host.wait()

    def _armed_env(self, sid: str) -> dict:
        fakes.claude_session(self.env["HOME"], sid)
        return {
            **self.env,
            "CLAUDE_PID": str(self.host.pid),
            "CLAUDE_CODE_SESSION_ID": sid,
        }

    def _arm(self, env: dict, *extra: str) -> None:
        with contextlib.redirect_stdout(io.StringIO()):
            code = cli.main(
                ["arm", "--host", "claude", *extra], seams=fakes.fixed_seams(env, _NOW)
            )
        self.assertEqual(0, code)

    def _run_hook(self, stdin: bytes, env: dict) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, "-S", _HOOK],
            input=stdin,
            capture_output=True,
            env=env,
            timeout=30,
            check=False,
        )

    def _systemctl_calls(self):
        log = self.env["AI_KIT_FAKE_LOG"]
        if not os.path.exists(log):
            return []
        return [e["argv"] for e in fakes.read_log(log) if e["name"] == "systemctl"]


@unittest.skipUnless(_zone_available(), f"no system zone database ({_ZONE} unavailable)")
class TestStopFailureHook(_HookScratch):
    """A StopFailure payload with the reset text refreshes only an armed session."""

    def _payload(self, sid: str, **fields) -> bytes:
        body = {"session_id": sid, "error": "rate_limit", **fields}
        return json.dumps(body).encode("utf-8")

    def test_armed_session_moves_to_the_reset_and_writes_nothing_to_stdout(self):
        sid = uuid.uuid4().hex
        env = self._armed_env(sid)
        self._arm(env)
        paths = session_paths(env, "claude", sid)
        timer_name, _service = units.unit_names("claude", sid)
        timer_path = os.path.join(units.unit_dir(env), timer_name)

        result = self._run_hook(
            self._payload(sid, last_assistant_message=_limit_text()), env
        )

        self.assertEqual(0, result.returncode)
        self.assertEqual(b"", result.stdout)
        state, reason = read_state(paths.state, "claude", sid)
        self.assertEqual("ok", reason)
        assert state is not None
        self.assertEqual("reset_inferred", state["wake_source"])
        with open(timer_path, encoding="utf-8") as handle:
            timer_text = handle.read()
        self.assertEqual(
            2, sum(1 for line in timer_text.splitlines() if line.startswith("OnCalendar="))
        )

    def test_an_unarmed_session_writes_nothing(self):
        sid = uuid.uuid4().hex
        env = self._armed_env(sid)
        paths = session_paths(env, "claude", sid)

        result = self._run_hook(
            self._payload(sid, last_assistant_message=_limit_text()), env
        )

        self.assertEqual(0, result.returncode)
        self.assertEqual(b"", result.stdout)
        self.assertFalse(os.path.exists(paths.state))
        self.assertEqual([], self._systemctl_calls())

    def test_a_payload_without_resets_never_calls_arm(self):
        sid = uuid.uuid4().hex
        env = self._armed_env(sid)
        self._arm(env)
        calls_before = len(self._systemctl_calls())

        result = self._run_hook(
            self._payload(sid, last_assistant_message="a plain stop, no limit"), env
        )

        self.assertEqual(0, result.returncode)
        self.assertEqual(b"", result.stdout)
        self.assertEqual(calls_before, len(self._systemctl_calls()))

    def test_malformed_input_exits_zero_with_no_output(self):
        sid = uuid.uuid4().hex
        env = self._armed_env(sid)
        self._arm(env)
        calls_before = len(self._systemctl_calls())
        for stdin in (b"", b"not json {", b"[1, 2, 3]", b'{"session_id": 7}',
                      b'{"session_id": "bad id!", "error": "resets 1pm (UTC)"}'):
            with self.subTest(stdin=stdin):
                result = self._run_hook(stdin, env)
                self.assertEqual(0, result.returncode)
                self.assertEqual(b"", result.stdout)
        self.assertEqual(calls_before, len(self._systemctl_calls()))

    def test_structured_error_details_store_the_redacted_value_only(self):
        sid = uuid.uuid4().hex
        env = self._armed_env(sid)
        self._arm(env)
        token = "tok" + uuid.uuid4().hex
        paths = session_paths(env, "claude", sid)

        result = self._run_hook(
            self._payload(
                sid,
                error_details={"token": token},
                last_assistant_message=_limit_text(),
            ),
            env,
        )

        self.assertEqual(0, result.returncode)
        state, reason = read_state(paths.state, "claude", sid)
        self.assertEqual("ok", reason)
        assert state is not None
        self.assertNotIn(token, json.dumps(state))


_SHIM_BODY = """import os, subprocess, sys, time
grand = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
tmp = PIDS + ".tmp"
with open(tmp, "w", encoding="utf-8") as handle:
    handle.write(f"{os.getpid()} {grand.pid}")
os.replace(tmp, PIDS)
time.sleep(60)
"""


class TestHookDeadline(_HookScratch):
    """One 8 s monotonic deadline over the stdin read and the arm child, so the
    hook exits by itself before the row's 10 s timeout (review round 1)."""

    def setUp(self):
        super().setUp()
        hooks_dir = os.path.join(self.root, "tools", "hooks")
        os.makedirs(hooks_dir)
        for name in ("claude_session_wake.py", "claude_session_start.py"):
            shutil.copyfile(
                os.path.join(_REPO, "tools", "hooks", name), os.path.join(hooks_dir, name)
            )
        self.hook = os.path.join(hooks_dir, "claude_session_wake.py")
        self.pids_file = os.path.join(self.root, "pids.txt")
        shim_dir = os.path.join(self.root, "skills", "ai-kit-session-wake")
        os.makedirs(shim_dir)
        self.shim = os.path.join(shim_dir, "ai-kit-session-wake.py")
        with open(self.shim, "w", encoding="utf-8") as handle:
            handle.write(f"PIDS = {self.pids_file!r}\n" + _SHIM_BODY)
        self.sid = uuid.uuid4().hex
        self.addCleanup(self._kill_survivors)

    def _kill_survivors(self):
        for pid in self._recorded_pids():
            with contextlib.suppress(ProcessLookupError, PermissionError):
                os.kill(pid, 9)

    def _recorded_pids(self):
        if not os.path.exists(self.pids_file):
            return []
        with open(self.pids_file, encoding="utf-8") as handle:
            return [int(token) for token in handle.read().split()]

    def _wait_for_pids(self):
        for _ in range(200):
            pids = self._recorded_pids()
            if len(pids) == 2:
                return pids
            time.sleep(0.05)
        self.fail("the fake shim never recorded its pids")

    @staticmethod
    def _dead(pid):
        """Dead, or a zombie (reaped by no one yet): both count as gone."""
        try:
            with open(f"/proc/{pid}/stat", encoding="utf-8") as handle:
                stat = handle.read()
        except FileNotFoundError:
            return True
        except OSError:
            return True
        return stat[stat.rindex(")") + 2:].split()[0] == "Z"

    def _payload(self) -> bytes:
        return json.dumps({
            "session_id": self.sid,
            "last_assistant_message": "You've hit your limit · resets 1pm (UTC)",
        }).encode("utf-8")

    def _hook_env(self) -> dict:
        return {**self.env, "CLAUDE_PID": str(self.host.pid)}

    def test_slow_child_is_killed_with_its_group_before_the_deadline(self):
        started = time.monotonic()
        result = subprocess.run(
            [sys.executable, "-S", self.hook],
            input=self._payload(),
            capture_output=True,
            env=self._hook_env(),
            timeout=30,
            check=False,
        )
        wall = time.monotonic() - started

        self.assertEqual(0, result.returncode)
        self.assertEqual(b"", result.stdout)
        self.assertLess(wall, 9.0)
        shim_pid, grand = self._wait_for_pids()
        self.assertTrue(self._dead(shim_pid), "the arm child survived the deadline")
        self.assertTrue(self._dead(grand), "the arm child's grandchild survived the deadline")

    def test_slow_input_exits_before_the_deadline(self):
        proc = subprocess.Popen(
            [sys.executable, "-S", self.hook],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=self._hook_env(),
        )
        stdin_pipe, stdout_pipe, stderr_pipe = proc.stdin, proc.stdout, proc.stderr
        assert stdin_pipe is not None and stdout_pipe is not None and stderr_pipe is not None
        stop = threading.Event()

        def trickle():
            # a complete payload, then one space every 0.3 s: the read keeps the
            # stream open until its own 5 s cap; trailing whitespace stays valid JSON
            stdin_pipe.write(self._payload())
            stdin_pipe.flush()
            while not stop.is_set():
                try:
                    stdin_pipe.write(b" ")
                    stdin_pipe.flush()
                except (BrokenPipeError, OSError, ValueError):
                    return
                time.sleep(0.3)

        feeder = threading.Thread(target=trickle, daemon=True)
        started = time.monotonic()
        feeder.start()
        try:
            proc.wait(timeout=30)
        finally:
            stop.set()
            feeder.join(timeout=5)
            with contextlib.suppress(OSError, ValueError):
                stdin_pipe.close()
        wall = time.monotonic() - started
        out = stdout_pipe.read()
        stdout_pipe.close()
        stderr_pipe.close()

        self.assertEqual(0, proc.returncode)
        self.assertEqual(b"", out)
        self.assertLess(wall, 9.0)
        # the read ended at its cap with the payload complete, so the child ran
        # and was killed at the deadline with its group
        shim_pid, grand = self._wait_for_pids()
        self.assertTrue(self._dead(shim_pid))
        self.assertTrue(self._dead(grand))


if __name__ == "__main__":
    unittest.main()
