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
from unittest import mock

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
from ai_kit_session_wake.hosts import HOSTS, WAKE_SCRUB
from ai_kit_session_wake.state import (
    ARM_WINDOW_S,
    WAKE_CAP,
    read_state,
    session_paths,
    state_dir,
    update_state,
)

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
    "liveness_source",
    "pid_source",
    "armed_at",
    "wake_count",
    "cap",
    "not_before",
    "wake_source",
    "reset_evidence",
    "reset_at",
    "launch_cwd",
    "launch_cwd_verified",
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
        return [
            e["argv"]
            for e in fakes.read_log(self.env["AI_KIT_FAKE_LOG"])
            if e["name"] == "systemctl"
        ]


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
        for key in (
            "PATH",
            "HOME",
            "XDG_CONFIG_HOME",
            "XDG_STATE_HOME",
            "XDG_DATA_HOME",
            "XDG_CACHE_HOME",
        ):
            self.assertIn(f'Environment="{key}=', service_text)
        self.assertNotIn("CLAUDECODE", service_text)
        calls = self.systemctl_calls()
        self.assertEqual(["--user", "show", "-p", "Version"], calls[0])
        self.assertEqual(["--user", "daemon-reload"], calls[1])
        self.assertEqual(["--user", "enable", "--now", timer_name], calls[2])

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
        for name in ("arm", "disarm", "fire", "done", "status", "matrix"):
            self.assertIn(name, proc.stdout)


class TestRearm(_Scratch):
    """Re-arming refreshes liveness while preserving the wake's identity."""

    def test_rearm_keeps_state_and_only_one_timer_pair(self):
        sid = uuid.uuid4().hex
        launch = os.path.join(self.root, "launch")
        os.makedirs(launch)
        fakes.fake_host(self.bin_dir, "claude")
        fakes.claude_session(self.env["HOME"], sid)
        ref = os.path.join(self.root, "ref.json")
        with open(ref, "w", encoding="utf-8") as handle:
            handle.write("{}")
        env = {
            **self.env,
            "CLAUDECODE": "1",
            "CLAUDE_CODE_SESSION_ID": sid,
        }
        host_a = fakes.start_host_process(launch)
        self.addCleanup(self._kill, host_a)
        env["CLAUDE_PID"] = str(host_a.pid)
        seams = fakes.fixed_seams(env, T0)
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(0, cli.main(["arm", "--ref", ref], seams=seams))
        paths = session_paths(env, "claude", sid)
        first, reason = read_state(paths.state, "claude", sid)
        self.assertEqual("ok", reason)
        self.assertIsNotNone(first)
        assert first is not None
        update_state(paths.state, lambda state: {**state, "wake_count": 5})
        armed_at = first["armed_at"]
        created = first["created"]
        host_a.kill()
        host_a.wait()
        host_b = fakes.start_host_process(launch)
        self.addCleanup(self._kill, host_b)
        env["CLAUDE_PID"] = str(host_b.pid)
        second_ref = os.path.join(self.root, "second-ref.json")
        with open(second_ref, "w", encoding="utf-8") as handle:
            handle.write("{}")
        for refs in ((ref, second_ref), (ref,)):
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(
                    0,
                    cli.main(
                        ["arm", "--ref", refs[0], *(["--ref", refs[1]] if len(refs) > 1 else [])],
                        seams=seams,
                    ),
                )
        refreshed, reason = read_state(paths.state, "claude", sid)
        self.assertEqual("ok", reason)
        self.assertIsNotNone(refreshed)
        assert refreshed is not None
        self.assertEqual(5, refreshed["wake_count"])
        self.assertEqual(host_b.pid, refreshed["pid"])
        self.assertNotEqual(first["pid_start"], refreshed["pid_start"])
        self.assertEqual([os.path.abspath(ref), os.path.abspath(second_ref)], refreshed["refs"])
        self.assertEqual(armed_at, refreshed["armed_at"])
        self.assertEqual(created, refreshed["created"])
        for field in (
            "arm_id",
            "cap",
            "permission_mode",
            "permission_source",
            "not_before",
            "wake_source",
            "reset_evidence",
            "reset_at",
            "last_resume_exit",
        ):
            self.assertEqual(first[field], refreshed[field], field)
        unit_path = os.path.join(units.unit_dir(env))
        names = os.listdir(unit_path)
        self.assertEqual(1, sum(name.endswith(".timer") for name in names))
        self.assertEqual(1, sum(name.endswith(".service") for name in names))
        calls = self.systemctl_calls()
        timer_name = units.unit_names("claude", sid).timer
        self.assertEqual(
            [
                ["--user", "daemon-reload"],
                ["--user", "enable", "--now", timer_name],
            ],
            calls[-2:],
        )
        self.assertIn(f"refreshed claude-{sid}", output.getvalue())

    def test_changed_timer_text_restarts_after_reload(self):
        sid = uuid.uuid4().hex
        launch = os.path.join(self.root, "launch")
        os.makedirs(launch)
        host = fakes.start_host_process(launch)
        self.addCleanup(self._kill, host)
        fakes.fake_host(self.bin_dir, "claude")
        fakes.claude_session(self.env["HOME"], sid)
        env = {
            **self.env,
            "CLAUDECODE": "1",
            "CLAUDE_PID": str(host.pid),
            "CLAUDE_CODE_SESSION_ID": sid,
        }
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(0, cli.main(["arm"], seams=fakes.fixed_seams(env, T0)))
        timer = os.path.join(units.unit_dir(env), units.unit_names("claude", sid).timer)
        with open(timer, "a", encoding="utf-8") as handle:
            handle.write("# changed\n")
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(0, cli.main(["arm"], seams=fakes.fixed_seams(env, T0)))
        calls = self.systemctl_calls()
        self.assertEqual(
            [
                ["--user", "show", "-p", "Version"],
                ["--user", "daemon-reload"],
                ["--user", "restart", units.unit_names("claude", sid).timer],
                ["--user", "enable", "--now", units.unit_names("claude", sid).timer],
            ],
            calls[-4:],
        )

    @staticmethod
    def _kill(host):
        host.kill()
        host.wait()


class TestArmIdentity(_Scratch):
    def test_missing_empty_and_unsafe_ids_refused_without_writes(self):
        # Full host setup is intentionally deferred until after id validation.
        for sid in ("", "../x", "a b", "x;y", "a*", "x" * 129):
            with self.subTest(session_id=sid):
                out = io.StringIO()
                err = io.StringIO()
                with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                    rc = cli.main(
                        ["arm", "--host", "claude", "--session-id", sid],
                        seams=fakes.fixed_seams(self.env, T0),
                    )
                self.assertEqual(2, rc)
                if sid:
                    self.assertIn(sid, err.getvalue())
                else:
                    self.assertIn("--session-id", err.getvalue())
                for directory in (state_dir(self.env), units.unit_dir(self.env)):
                    self.assertFalse(os.path.exists(directory) and os.listdir(directory))
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            self.assertEqual(
                2, cli.main(["arm", "--host", "claude"], seams=fakes.fixed_seams(self.env, T0))
            )
        self.assertIn("CLAUDE_CODE_SESSION_ID", err.getvalue())

    def test_two_sessions_disarm_and_fire_only_the_selected_id(self):
        ids = ("first-session", "second-session")
        launch = os.path.join(self.root, "shared-launch")
        os.makedirs(launch)
        fakes.fake_host(self.bin_dir, "claude")
        hosts = []
        states = []
        for sid in ids:
            fakes.claude_session(self.env["HOME"], sid)
            host = fakes.start_host_process(launch)
            hosts.append(host)
            self.addCleanup(self._kill, host)
            env = {
                **self.env,
                "CLAUDECODE": "1",
                "CLAUDE_PID": str(host.pid),
                "CLAUDE_CODE_SESSION_ID": sid,
            }
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(0, cli.main(["arm"], seams=fakes.fixed_seams(env, T0)))
            states.append(_read(session_paths(env, "claude", sid).state))
        second_paths = set()
        for base in (state_dir(self.env), units.unit_dir(self.env)):
            for root, _dirs, files in os.walk(base):
                second_paths.update(os.path.join(root, name) for name in files if ids[1] in name)
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(
                0,
                cli.main(
                    ["disarm", "--host", "claude", "--session-id", ids[0]],
                    seams=fakes.fixed_seams(self.env, T0),
                ),
            )
        self.assertTrue(all(os.path.exists(path) for path in second_paths))
        hosts[1].kill()
        hosts[1].wait()
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(
                0,
                cli.main(
                    ["fire", "--host", "claude", "--session-id", ids[1]],
                    seams=fakes.fixed_seams(self.env, T0 + 120),
                ),
            )
        calls = [
            entry
            for entry in fakes.read_log(self.env["AI_KIT_FAKE_LOG"])
            if entry["name"] == "claude"
        ]
        self.assertEqual(1, len(calls))
        self.assertIn(ids[1], calls[0]["argv"])
        forbidden = {"--continue", "-c", "--fork-session", "--last"}
        self.assertFalse(any(forbidden.intersection(row.resume) for row in HOSTS.values()))

    def test_length_limit_and_exact_mixed_case_id(self):
        sid = "A" * 128
        self._arm_sid(sid)
        state = _read(session_paths(self.env, "claude", sid).state)
        self.assertEqual(sid, state["session_id"])
        mixed_uuid = "aBcDeF01-2345-6789-AbCd-Ef0123456789"
        self._arm_sid(mixed_uuid)
        self.assertEqual(
            mixed_uuid, _read(session_paths(self.env, "claude", mixed_uuid).state)["session_id"]
        )

    @staticmethod
    def _kill(host):
        host.kill()
        host.wait()

    def _arm_sid(self, sid):
        launch = os.path.join(self.root, "launch")
        os.makedirs(launch, exist_ok=True)
        host = fakes.start_host_process(launch)
        self.addCleanup(self._kill, host)
        fakes.fake_host(self.bin_dir, "claude")
        fakes.claude_session(self.env["HOME"], sid)
        env = {
            **self.env,
            "CLAUDECODE": "1",
            "CLAUDE_PID": str(host.pid),
            "CLAUDE_CODE_SESSION_ID": sid,
        }
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(0, cli.main(["arm"], seams=fakes.fixed_seams(env, T0)))


class TestArmSafety(_Scratch):
    def _arm(self, sid: str, env: dict[str, str], args: list[str] | None = None) -> int:
        launch = os.path.join(self.root, "launch")
        os.makedirs(launch, exist_ok=True)
        host = fakes.start_host_process(launch)
        self.addCleanup(self._kill, host)
        if not os.path.exists(os.path.join(self.bin_dir, "claude")):
            fakes.fake_host(self.bin_dir, "claude")
        fakes.claude_session(env["HOME"], sid)
        arm_env = {
            **env,
            "CLAUDECODE": "1",
            "CLAUDE_PID": str(host.pid),
            "CLAUDE_CODE_SESSION_ID": sid,
        }
        with contextlib.redirect_stdout(io.StringIO()):
            return cli.main(
                ["arm", "--host", "claude", "--session-id", sid, *(args or [])],
                seams=fakes.fixed_seams(arm_env, T0),
            )

    @staticmethod
    def _kill(host):
        host.kill()
        host.wait()

    def test_secret_sentinels_never_reach_any_written_file_or_systemctl_log(self):
        api = "sk-ant-" + "sentinel-not-a-real-key"
        github = "ghp_" + "sentinel-not-a-real-token"
        sid = uuid.uuid4().hex
        fakes.fake_host(self.bin_dir, "claude")
        env = {**self.env, "ANTHROPIC_API_KEY": api, "GITHUB_TOKEN": github}
        self.assertEqual(0, self._arm(sid, env))
        paths = [self.env["XDG_STATE_HOME"], units.unit_dir(self.env)]
        contents = []
        for base in paths:
            for root, _dirs, files in os.walk(base):
                for name in files:
                    with open(os.path.join(root, name), "rb") as handle:
                        contents.append(handle.read())
        with open(self.env["AI_KIT_FAKE_LOG"], "rb") as handle:
            contents.append(handle.read())
        self.assertFalse(any(api.encode() in part or github.encode() in part for part in contents))

    def test_filtered_service_path_environment_allowlist(self):
        fakes.fake_host(self.bin_dir, "claude")
        sid = uuid.uuid4().hex
        fnm = os.path.join(self.root, "fnm_multishells", "7", "bin")
        env = {
            **self.env,
            "PATH": os.pathsep.join((self.bin_dir, fnm)),
            "SECRET_SENTINEL": "hidden",
        }
        self.assertEqual(0, self._arm(sid, env))
        service_path = os.path.join(units.unit_dir(env), units.unit_names("claude", sid).service)
        with open(service_path, encoding="utf-8") as handle:
            text = handle.read()
        self.assertNotIn("fnm_multishells", text)
        keys = {
            line.split('="', 1)[1].split("=", 1)[0]
            for line in text.splitlines()
            if line.startswith("Environment=")
        }
        self.assertLessEqual(
            keys,
            {
                "PATH",
                "HOME",
                "XDG_CONFIG_HOME",
                "XDG_STATE_HOME",
                "XDG_DATA_HOME",
                "XDG_CACHE_HOME",
            },
        )

    def test_shebang_interpreter_is_checked_against_filtered_path(self):
        sid = uuid.uuid4().hex
        fakes.write_fake(self.bin_dir, "claude", "pass\n", shebang="#!/usr/bin/env fakenode")
        stable = os.path.join(self.root, "stable")
        fnm = os.path.join(self.root, "fnm_multishells", "1", "bin")
        os.makedirs(fnm)
        fakes.write_fake(fnm, "fakenode", "pass\n")
        fakes.claude_session(self.env["HOME"], sid)
        env = {**self.env, "PATH": os.pathsep.join((self.bin_dir, fnm))}
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            self.assertEqual(2, self._arm(sid, env))
        self.assertIn("fakenode", err.getvalue())
        self.assertIn("wake's PATH", err.getvalue())
        self.assertFalse(os.path.exists(state_dir(env)))
        os.makedirs(stable)
        fakes.write_fake(stable, "fakenode", "pass\n")
        env["PATH"] = os.pathsep.join((self.bin_dir, stable, fnm))
        self.assertEqual(0, self._arm(sid, env))

    def test_missing_absolute_shebang_interpreter_refused(self):
        sid = uuid.uuid4().hex
        absent = os.path.join(self.root, "missing-interpreter")
        fakes.write_fake(self.bin_dir, "claude", "pass\n", shebang=f"#!{absent}")
        fakes.claude_session(self.env["HOME"], sid)
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            self.assertEqual(2, self._arm(sid, self.env))
        self.assertIn(absent, err.getvalue())
        self.assertFalse(os.path.exists(state_dir(self.env)))

    def test_atomic_refresh_failure_preserves_bytes_and_modes(self):
        fakes.fake_host(self.bin_dir, "claude")
        sid = uuid.uuid4().hex
        self.assertEqual(0, self._arm(sid, self.env))
        state_path = session_paths(self.env, "claude", sid).state
        with open(state_path, "rb") as handle:
            before = handle.read()
        st_dir = state_dir(self.env)
        self.assertEqual(0o700, os.stat(st_dir).st_mode & 0o777)
        self.assertEqual(0o600, os.stat(state_path).st_mode & 0o777)
        for suffix in (".timer", ".service"):
            unit = os.path.join(
                units.unit_dir(self.env), "ai-kit-session-wake-claude-" + sid + suffix
            )
            self.assertEqual(0o600, os.stat(unit).st_mode & 0o777)
        with (
            mock.patch(
                "ai_kit_session_wake.state.os.replace", side_effect=OSError("replace failed")
            ),
            self.assertRaises(OSError),
        ):
            self._arm(sid, self.env)
        with open(state_path, "rb") as handle:
            self.assertEqual(before, handle.read())
        self.assertEqual([], [name for name in os.listdir(st_dir) if name.endswith(".tmp")])

    def test_filtered_service_path_and_linger_file_fallback(self):
        root = tempfile.mkdtemp(prefix="wake-linger-")
        self.addCleanup(shutil.rmtree, root, True)
        linger = os.path.join(root, "linger")
        os.makedirs(linger)
        with open(os.path.join(linger, "wake-test"), "w", encoding="utf-8"):
            pass
        env = {"PATH": f"/stable:{root}/fnm_multishells/1/bin", "USER": "wake-test"}
        self.assertEqual("/stable", dict(units.service_environment(env))["PATH"])
        self.assertTrue(units.linger_enabled(fakes.fixed_seams(env, T0), linger_dir=linger))


class TestMatrix(_Scratch):
    def test_rows_are_evidence_labelled_ranked_and_json_contract(self):
        from ai_kit_session_wake.matrix import (
            MATRIX,
            best_primitive,
            matrix_json,
            rank,
            render_matrix,
            rows_for,
        )

        self.assertTrue(
            all(row["source"] in {"verified", "unverified"} and row["evidence"] for row in MATRIX)
        )
        self.assertTrue(
            all("spike 00" in row["evidence"] for row in MATRIX if row["source"] == "verified")
        )
        self.assertEqual(
            "unverified", next(row for row in MATRIX if row["host"] == "codex")["source"]
        )
        self.assertEqual([], rows_for("cursor"))
        text = render_matrix()
        self.assertIn("verified; unverified: reboot, first fire after enable", text)
        self.assertEqual(
            1,
            rank(
                {"survives_stall": True, "survives_process_death": False, "survives_reboot": False}
            ),
        )
        self.assertEqual(
            2,
            rank(
                {"survives_stall": True, "survives_process_death": True, "survives_reboot": False}
            ),
        )
        claude = rows_for("claude")
        best_with_timer = best_primitive("claude", True)
        best_without_timer = best_primitive("claude", False)
        self.assertIsNotNone(best_with_timer)
        self.assertIsNotNone(best_without_timer)
        assert best_with_timer is not None and best_without_timer is not None
        self.assertEqual("systemd user timer", best_with_timer["primitive"])
        self.assertEqual("CronCreate one-shot", best_without_timer["primitive"])
        self.assertIsNone(best_primitive("cursor", True))
        cron = [row["primitive"] for row in claude if row["primitive"].startswith("CronCreate")]
        self.assertEqual(["CronCreate one-shot", "CronCreate recurring"], cron)
        document = json.loads(matrix_json())
        self.assertEqual(1, document["schema_version"])
        keys = {
            "host",
            "primitive",
            "kind",
            "surface",
            "survives_stall",
            "survives_process_death",
            "survives_reboot",
            "source",
            "evidence",
            "unverified",
            "version_floor",
            "rank",
        }
        self.assertTrue(all(set(row) == keys for row in document["rows"]))
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(
                0, cli.main(["matrix", "--json"], seams=fakes.fixed_seams(self.env, T0))
            )
        self.assertEqual(document, json.loads(output.getvalue()))


class TestArmPrimitive(_Scratch):
    @staticmethod
    def _kill(host):
        host.kill()
        host.wait()

    def test_no_systemd_fallback_and_unknown_host(self):
        from ai_kit_session_wake.state import Seams

        sid = uuid.uuid4().hex
        launch = os.path.join(self.root, "launch")
        os.makedirs(launch)
        host = fakes.start_host_process(launch)
        self.addCleanup(self._kill, host)
        fakes.fake_host(self.bin_dir, "claude")
        fakes.claude_session(self.env["HOME"], sid)
        env = {
            **self.env,
            "FAKE_SYSTEMCTL_DOWN": "1",
            "CLAUDE_PID": str(host.pid),
            "CLAUDE_CODE_SESSION_ID": sid,
        }
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = cli.main(
                ["arm", "--host", "claude", "--session-id", sid],
                seams=Seams(env=env),
            )
        self.assertEqual(3, result)
        self.assertIn("CronCreate one-shot", output.getvalue())
        self.assertFalse(os.path.exists(state_dir(self.env)))
        self.assertFalse(os.path.exists(units.unit_dir(self.env)))
        cursor_out = io.StringIO()
        with contextlib.redirect_stdout(cursor_out):
            self.assertEqual(
                3,
                cli.main(
                    ["arm", "--host", "cursor", "--session-id", "c"],
                    seams=fakes.fixed_seams(self.env, T0),
                ),
            )
        self.assertIn("no surviving primitive for cursor", cursor_out.getvalue())
        self.assertFalse(os.path.exists(state_dir(self.env)))
        self.assertFalse(os.path.exists(units.unit_dir(self.env)))


class TestStatus(_Scratch):
    def _arm(self, sid: str, host) -> dict:
        fakes.fake_host(self.bin_dir, "claude")
        fakes.claude_session(self.env["HOME"], sid)
        env = {
            **self.env,
            "CLAUDECODE": "1",
            "CLAUDE_PID": str(host.pid),
            "CLAUDE_CODE_SESSION_ID": sid,
        }
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(0, cli.main(["arm"], seams=fakes.fixed_seams(env, T0)))
        return env

    def test_status_displays_armed_state_alive_and_paths(self):
        sid = uuid.uuid4().hex
        launch = os.path.join(self.root, "launch")
        os.makedirs(launch)
        host = fakes.start_host_process(launch)
        self.addCleanup(TestArmIdentity._kill, host)
        env = self._arm(sid, host)
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(
                0,
                cli.main(
                    ["status", "--host", "claude", "--session-id", sid],
                    seams=fakes.fixed_seams(env, T0),
                ),
            )
        text = output.getvalue()
        self.assertIn(session_paths(env, "claude", sid).state, text)
        self.assertIn("wakes: 0/24", text)
        self.assertIn("next wake: hourly", text)
        self.assertIn("permission_mode: unknown (unknown)", text)
        self.assertIn("host process: alive", text)
        self.assertIn("created:", text)
        self.assertIn("active", text)
        self.assertIn("linger: True", text)

    def test_invalid_status_and_rearm_leave_state_and_systemctl_log_unchanged(self):
        sid = uuid.uuid4().hex
        launch = os.path.join(self.root, "launch")
        os.makedirs(launch)
        host = fakes.start_host_process(launch)
        self.addCleanup(TestArmIdentity._kill, host)
        env = self._arm(sid, host)
        path = session_paths(env, "claude", sid).state
        with open(path, encoding="utf-8") as handle:
            state = json.load(handle)
        state["wake_count"] = "3"
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(state, handle)
        with open(path, "rb") as handle:
            before = handle.read()
        calls = self.systemctl_calls()
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(0, cli.main(["status"], seams=fakes.fixed_seams(env, T0)))
        self.assertIn("invalid state", output.getvalue())
        self.assertIn("wake_count", output.getvalue())
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            self.assertEqual(2, cli.main(["arm"], seams=fakes.fixed_seams(env, T0)))
        self.assertIn("run disarm first", err.getvalue())
        with open(path, "rb") as handle:
            self.assertEqual(before, handle.read())
        self.assertEqual(calls, self.systemctl_calls())

    def test_empty_status(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(0, cli.main(["status"], seams=fakes.fixed_seams(self.env, T0)))
        self.assertIn("nothing armed", output.getvalue())


class TestArmOptionsShape(unittest.TestCase):
    """The ArmOptions contract the executors will call (D-23)."""

    def test_options_are_a_named_tuple(self):
        opts = ArmOptions(host="claude", session_id="s", pid=None, permission_mode=None, refs=())
        self.assertIsNone(opts.pid)
        self.assertEqual((), opts.refs)


if __name__ == "__main__":
    unittest.main()
