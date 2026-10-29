"""Session-wake tests (QTA-04): the full tracer path on claude with fakes and
scratch dirs, plus the pinned resume prompt. Never real systemd, never a real
home (D-26); every spawned process is killed in cleanup."""
import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import uuid

sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "skills",
        "ai-kit-session-wake",
    ),
)

from ai_kit_session_wake import cli, units
from ai_kit_session_wake import fire as fire_mod
from ai_kit_session_wake.arm import ArmOptions
from ai_kit_session_wake.hosts import WAKE_SCRUB
from ai_kit_session_wake.state import ARM_WINDOW_S, WAKE_CAP, session_paths

from tests import session_wake_fakes as fakes

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SHIM = os.path.join(_REPO, "skills", "ai-kit-session-wake", "ai-kit-session-wake.py")

T0 = 1_700_000_000.0

# D-16/D-36: the resume prompt is a code constant; only {state_path} is filled
# in. This is the independent pin the constant must equal.
PROMPT_TEMPLATE = (
    "ai-kit session wake: this session stalled and its wake timer resumed it. "
    "Read the wake state at {state_path} and every state file listed in its refs, "
    "including pending cross-AI waits. Continue only unfinished work. Continue a pending "
    "cross-AI hard-tier wait from its own state file (cycle, due_at); never restart it at "
    "cycle 0, and never switch harness, provider or model. Re-run the ai-kit-session-wake "
    "skill's arm to refresh this session's wake. When nothing remains, run its done."
)

WAKE_STATE_KEYS = (
    "schema_version",
    "host",
    "session_id",
    "arm_id",
    "pid",
    "pid_start",
    "boot_id",
    "armed_at",
    "wake_count",
    "cap",
    "not_before",
    "wake_source",
    "reset_evidence",
    "reset_at",
    "launch_cwd",
    "cli_path",
    "permission_mode",
    "permission_source",
    "backend",
    "refs",
    "created",
    "last_resume_exit",
)


def _read(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


class _Scratch(unittest.TestCase):
    """Scratch root, fake bin dir, fake log; nothing survives the test."""

    def setUp(self):
        super().setUp()
        self.root = tempfile.mkdtemp(prefix="wake-")
        self.addCleanup(shutil.rmtree, self.root, True)
        self.bin_dir = os.path.join(self.root, "bin")
        os.makedirs(self.bin_dir)
        self.env = fakes.scoped_env(self.root)
        fakes.fake_systemctl(self.bin_dir)
        fakes.fake_loginctl(self.bin_dir)

    def systemctl_calls(self):
        return [e["argv"] for e in fakes.read_log(self.env["AI_KIT_FAKE_LOG"])
                if e["name"] == "systemctl"]


class TestWakeTracer(_Scratch):
    """One full path end to end: arm at T0, host dies, fire at T0+120 resumes
    the exact id once, the resumed agent runs done, everything is removed."""

    def test_arm_host_gone_one_resume_then_done_removes_all(self):
        sid = uuid.uuid4().hex
        launch = os.path.join(self.root, "launch")
        os.makedirs(launch)
        host = fakes.start_host_process(launch)
        self.addCleanup(self._kill, host)
        env = {
            **self.env,
            "CLAUDECODE": "1",
            "CLAUDE_PID": str(host.pid),
            "CLAUDE_CODE_SESSION_ID": sid,
            "FAKE_WAKE_DONE": "1",
            "FAKE_WAKE_SHIM": _SHIM,
        }
        fakes.fake_host(self.bin_dir, "claude")
        fakes.claude_session(env["HOME"], sid)
        paths = session_paths(env, "claude", sid)
        timer_name, service_name = units.unit_names("claude", sid)

        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            rc = cli.main(["arm"], seams=fakes.fixed_seams(env, T0))
        self.assertEqual(0, rc)
        lines = out.getvalue().splitlines()
        self.assertIn(f"armed claude-{sid}", lines)
        wrote = [line for line in lines if line.startswith("wrote ")]
        self.assertEqual(4, len(wrote))
        creates = [line for line in lines if line.startswith("systemctl creates ")]
        self.assertEqual(2, len(creates))
        self.assertIn("permission_mode: unknown (unknown)", lines)

        state_path = paths.state
        state = _read(state_path)
        self.assertEqual(sorted(WAKE_STATE_KEYS), sorted(state))
        self.assertEqual(1, state["schema_version"])
        self.assertEqual("claude", state["host"])
        self.assertEqual(sid, state["session_id"])
        self.assertEqual(16, len(state["arm_id"]))
        int(state["arm_id"], 16)
        self.assertEqual(host.pid, state["pid"])
        self.assertEqual(os.path.realpath(launch), os.path.realpath(state["launch_cwd"]))
        self.assertEqual(0, state["wake_count"])
        self.assertEqual(WAKE_CAP, state["cap"])
        self.assertEqual(T0 + ARM_WINDOW_S, state["not_before"])
        self.assertEqual(6, len(state["created"]))
        ud = env["XDG_CONFIG_HOME"] + "/systemd/user"
        stamp = env["XDG_DATA_HOME"] + f"/systemd/timers/stamp-{timer_name}"
        self.assertEqual(
            [
                state_path,
                paths.lock,
                f"{ud}/{service_name}",
                f"{ud}/{timer_name}",
                f"{ud}/timers.target.wants/{timer_name}",
                stamp,
            ],
            state["created"],
        )
        self.assertTrue(os.path.exists(paths.lock))
        with open(f"{ud}/{timer_name}", encoding="utf-8") as handle:
            timer_text = handle.read()
        for needle in (
            "OnCalendar=hourly",
            "Persistent=true",
            f"Unit={service_name}",
            "WantedBy=timers.target",
        ):
            self.assertIn(needle, timer_text)
        with open(f"{ud}/{service_name}", encoding="utf-8") as handle:
            service_text = handle.read()
        self.assertIn("Type=oneshot", service_text)
        self.assertIn(f'ExecStart="{sys.executable}" "{_SHIM}" "fire"', service_text)
        self.assertIn(f'"--session-id" "{sid}"', service_text)
        for key in ("PATH", "HOME", "XDG_CONFIG_HOME", "XDG_STATE_HOME", "XDG_DATA_HOME",
                    "XDG_CACHE_HOME"):
            self.assertIn(f'Environment="{key}=', service_text)
        self.assertNotIn("CLAUDECODE", service_text)
        calls = self.systemctl_calls()
        self.assertEqual(["--user", "daemon-reload"], calls[0])
        self.assertEqual(["--user", "enable", "--now", timer_name], calls[1])

        host.kill()
        host.wait()

        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            rc = cli.main(
                ["fire", "--host", "claude", "--session-id", sid],
                seams=fakes.fixed_seams(env, T0 + 120),
            )
        self.assertEqual(0, rc)
        self.assertIn(f"ai-kit-session-wake: claude-{sid} resume exit 0", out.getvalue())

        entries = fakes.read_log(self.env["AI_KIT_FAKE_LOG"])
        host_calls = [e for e in entries if e["name"] == "claude"]
        self.assertEqual(1, len(host_calls))
        call = host_calls[0]
        self.assertEqual(
            [
                "--resume",
                sid,
                "--permission-prompts",
                "none",
                "-p",
                PROMPT_TEMPLATE.replace("{state_path}", state_path),
            ],
            call["argv"],
        )
        self.assertEqual(os.path.realpath(launch), os.path.realpath(call["cwd"]))
        self.assertTrue(call["stdin_null"])
        self.assertEqual(set(), set(WAKE_SCRUB) & set(call["env_names"]))
        self.assertIn("AI_KIT_SESSION_WAKE_FIRE", call["env_names"])

        for path in (
            state_path,
            paths.lock,
            paths.done,
            f"{ud}/{timer_name}",
            f"{ud}/{service_name}",
            f"{ud}/timers.target.wants/{timer_name}",
            stamp,
        ):
            self.assertFalse(os.path.exists(path), path)
        calls = self.systemctl_calls()
        self.assertEqual(
            [
                ["--user", "disable", "--now", timer_name],
                ["--user", "clean", "--what=state", timer_name],
                ["--user", "daemon-reload"],
            ],
            calls[-3:],
        )
        self.assertFalse(any("stop" in argv for argv in calls))

    @staticmethod
    def _kill(host):
        host.kill()
        host.wait()

    def test_resume_prompt_is_pinned(self):
        """D-16/D-36: the constant is exactly the pinned text."""
        self.assertEqual(PROMPT_TEMPLATE, fire_mod.RESUME_PROMPT)

    def test_shim_help_names_the_subcommands(self):
        """The shim runs as a subprocess on the scratch env and names all four
        subcommands (26-03 extends the pin to six)."""
        env = {**self.env, "PYTHONDONTWRITEBYTECODE": "1"}
        proc = subprocess.run(
            [sys.executable, _SHIM, "--help"],
            env=env,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        self.assertEqual(0, proc.returncode, proc.stderr)
        for name in ("arm", "disarm", "fire", "done"):
            self.assertIn(name, proc.stdout)


class TestArmOptionsShape(unittest.TestCase):
    """The ArmOptions contract the executors will call (D-23)."""

    def test_options_are_a_named_tuple(self):
        opts = ArmOptions(host="claude", session_id="s", pid=None, permission_mode=None, refs=())
        self.assertIsNone(opts.pid)
        self.assertEqual((), opts.refs)


if __name__ == "__main__":
    unittest.main()
