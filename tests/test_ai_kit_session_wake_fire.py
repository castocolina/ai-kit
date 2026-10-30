"""fire under concurrency and every D-10 edge (QTA-04; plan 26-05).

TestOverlap: two concurrent real fire processes on one gone session run
exactly one resume and both wakes count. TestFireInterleaving: every done,
disarm, re-arm or refresh that lands between a fire's checks and its spawn
yields no resume. TestFireSequence/TestGiveUp (26-05 Task 2) pin the order's
liveness edges, the arm window, the cap give-up notice and the resume
timeout; TestDisarm (Task 3) pins every disarm and done trigger. Fakes and
scratch dirs only (D-26); every spawned process is killed in cleanup.
"""

import contextlib
import fcntl
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
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
sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "skills",
        "ai-kit-spec-review",
    ),
)

from ai_kit_session_wake import cli, units
from ai_kit_session_wake import fire as fire_mod
from ai_kit_session_wake.state import (
    session_paths,
    state_dir,
    update_state,
    write_json_atomic,
)

from tests import session_wake_fakes as fakes

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SHIM = os.path.join(_REPO, "skills", "ai-kit-session-wake", "ai-kit-session-wake.py")
_SKILL_DIR = os.path.join(_REPO, "skills", "ai-kit-session-wake")

T0 = 1_700_000_000.0
FIRE_AT = T0 + 120.0


def _read(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def _kill(proc):
    """Kill and reap one spawned process; safe to call twice."""
    if proc.poll() is None:
        proc.kill()
    proc.wait()


def _leftover_files(env):
    """Every file left under the wake's three write roots (dirs may remain)."""
    bases = (
        state_dir(env),
        units.unit_dir(env),
        os.path.join(env["XDG_DATA_HOME"], "systemd"),
    )
    leftovers = []
    for base in bases:
        if os.path.isdir(base):
            for root, _dirs, files in os.walk(base):
                leftovers += [os.path.join(root, name) for name in files]
    return leftovers


def _silence():
    return contextlib.redirect_stdout(io.StringIO())


class _Scratch(unittest.TestCase):
    """Scratch root, fake bin dir, fake log; nothing survives the test."""

    def setUp(self):
        super().setUp()
        self.root = tempfile.mkdtemp(prefix="wake-fire-")
        self.addCleanup(shutil.rmtree, self.root, True)
        self.bin_dir = os.path.join(self.root, "bin")
        os.makedirs(self.bin_dir)
        self.env = fakes.scoped_env(self.root)
        fakes.fake_systemctl(self.bin_dir)
        fakes.fake_loginctl(self.bin_dir)

    def systemctl_calls(self):
        if not os.path.exists(self.env["AI_KIT_FAKE_LOG"]):
            return []
        return [
            e["argv"]
            for e in fakes.read_log(self.env["AI_KIT_FAKE_LOG"])
            if e["name"] == "systemctl"
        ]

    def host_calls(self):
        if not os.path.exists(self.env["AI_KIT_FAKE_LOG"]):
            return []
        return [e for e in fakes.read_log(self.env["AI_KIT_FAKE_LOG"]) if e["name"] == "claude"]

    def start_host(self, name="launch"):
        """A real `sleep` stand-in for a host process; killed in cleanup."""
        launch = os.path.join(self.root, name)
        os.makedirs(launch, exist_ok=True)
        host = fakes.start_host_process(launch)
        self.addCleanup(_kill, host)
        return host

    def arm_claude(self, sid, host, env=None):
        """Arm one claude session in-process on the fake host and transcript."""
        arm_env = {
            **(env or self.env),
            "CLAUDECODE": "1",
            "CLAUDE_PID": str(host.pid),
            "CLAUDE_CODE_SESSION_ID": sid,
        }
        fakes.fake_host(self.bin_dir, "claude")
        fakes.claude_session(arm_env["HOME"], sid)
        with _silence():
            self.assertEqual(0, cli.main(["arm"], seams=fakes.fixed_seams(arm_env, T0)))
        return arm_env

    def disarm_claude(self, sid, env):
        with _silence():
            self.assertEqual(
                0,
                cli.main(
                    ["disarm", "--host", "claude", "--session-id", sid],
                    seams=fakes.fixed_seams(env, FIRE_AT),
                ),
            )

    def fire_claude(self, sid, env, seams=None):
        """One in-process fire; returns (returncode, stdout)."""
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            code = cli.main(
                ["fire", "--host", "claude", "--session-id", sid],
                seams=seams or fakes.fixed_seams(env, FIRE_AT),
            )
        return code, out.getvalue()

    def arm_window_open(self, paths):
        """Set not_before to 0 so a fire counts regardless of the arm window."""
        update_state(paths.state, lambda state: {**state, "not_before": 0.0})

    def assert_no_wake_files(self, env, paths):
        self.assertEqual([], _leftover_files(env))
        for path in (paths.state, paths.lock, paths.done):
            self.assertFalse(os.path.exists(path), path)


class TestOverlap(_Scratch):
    """SPEC R4 concurrency: the lock file makes a second overlapping wake exit
    without resuming; the count lives in the state file (D-10 step 5, D-11)."""

    def _fire_subprocess(self, sid, env):
        return subprocess.Popen(
            [sys.executable, _SHIM, "fire", "--host", "claude", "--session-id", sid],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

    def _wait_for_resume_logged(self, timeout=10.0):
        """A readiness barrier: poll until the fake log holds the resume call,
        so the second fire starts only after the first holds the lock."""
        deadline = time.monotonic() + timeout
        log_path = self.env["AI_KIT_FAKE_LOG"]
        while time.monotonic() < deadline:
            try:
                with open(log_path, encoding="utf-8") as handle:
                    lines = handle.readlines()
            except FileNotFoundError:
                lines = []
            for line in lines:
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue  # a concurrent appender's partially written line
                if entry.get("name") == "claude":
                    return
            time.sleep(0.05)
        self.fail("the first fire never started its resume")

    def test_two_concurrent_fires_one_resume_two_wakes(self):
        sid = uuid.uuid4().hex
        host = self.start_host()
        arm_env = self.arm_claude(sid, host)
        paths = session_paths(arm_env, "claude", sid)
        host.kill()
        host.wait()
        self.arm_window_open(paths)
        fire_env = {**self.env, "FAKE_HOST_SLEEP": "5"}
        first = self._fire_subprocess(sid, fire_env)
        self.addCleanup(_kill, first)
        self._wait_for_resume_logged()
        second = self._fire_subprocess(sid, fire_env)
        self.addCleanup(_kill, second)
        _first_out, first_err = first.communicate(timeout=120)
        second_out, second_err = second.communicate(timeout=120)
        self.assertEqual(0, first.returncode, first_err)
        self.assertEqual(0, second.returncode, second_err)
        # exactly one resume of the recorded id
        self.assertEqual(1, len(self.host_calls()))
        self.assertIn(sid, self.host_calls()[0]["argv"])
        # both wakes counted, in the state file
        self.assertEqual(2, _read(paths.state)["wake_count"])
        # the second fire found the lock held and resumed nothing
        self.assertIn("a resume is already running", second_out)

    def test_update_state_serializes_fifty_plus_fifty_increments(self):
        """SPEC R5 precision: two processes incrementing 50 times each on one
        scratch state leave 100 (every increment serialized)."""
        path = os.path.join(self.root, "counts.json")
        write_json_atomic(path, {"wake_count": 0})
        script = (
            "import os, sys\n"
            "sys.path.insert(0, os.environ['WAKE_SKILL_DIR'])\n"
            "from ai_kit_session_wake.state import update_state\n"
            "def bump(state):\n"
            "    state['wake_count'] = int(state.get('wake_count', 0)) + 1\n"
            "    return state\n"
            "for _ in range(50):\n"
            "    update_state(os.environ['WAKE_STATE_PATH'], bump)\n"
        )
        env = {
            **self.env,
            "WAKE_SKILL_DIR": _SKILL_DIR,
            "WAKE_STATE_PATH": path,
            "PYTHONDONTWRITEBYTECODE": "1",
        }
        procs = [
            subprocess.Popen(
                [sys.executable, "-c", script],
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
            )
            for _ in range(2)
        ]
        for proc in procs:
            self.addCleanup(_kill, proc)
        for proc in procs:
            _out, err = proc.communicate(timeout=120)
            self.assertEqual(0, proc.returncode, err)
        self.assertEqual(100, _read(path)["wake_count"])


class TestFireInterleaving(_Scratch):
    """Deterministic, in-process interleavings: whatever lands between a
    fire's checks and its spawn must never make it resume (review rounds
    1-3). Each case patches the function fire calls at the chosen point with
    a wrapper that runs the real function and then the interleaved action."""

    def _interleaved_fire(self, sid, env, point, action):
        """Run one fire whose `point` (`is_alive` | `session_exists` |
        `update_state`) is wrapped so `action()` runs once at that step:
        after the real call for the two probes, before the real call for the
        count's `update_state` (review round 3). Returns (rc, stdout)."""
        real = getattr(fire_mod, point)
        ran = []
        if point == "update_state":

            def wrapper_count(path, fn, *args, **kwargs):
                if not ran:
                    ran.append(True)
                    action()
                return real(path, fn, *args, **kwargs)

            wrapper = wrapper_count
        else:

            def wrapper_probe(*args, **kwargs):
                result = real(*args, **kwargs)
                if not ran:
                    ran.append(True)
                    action()
                return result

            wrapper = wrapper_probe

        out = io.StringIO()
        with (
            mock.patch.object(fire_mod, point, wrapper),
            contextlib.redirect_stdout(out),
            contextlib.redirect_stderr(io.StringIO()),
        ):
            code = cli.main(
                ["fire", "--host", "claude", "--session-id", sid],
                seams=fakes.fixed_seams(env, FIRE_AT),
            )
        return code, out.getvalue()

    def _gone_session(self, sid):
        """Arm a claude session, kill its host, open the arm window."""
        host = self.start_host()
        env = self.arm_claude(sid, host)
        paths = session_paths(env, "claude", sid)
        host.kill()
        host.wait()
        self.arm_window_open(paths)
        return env, paths

    def _assert_no_host_call(self):
        self.assertEqual([], self.host_calls())

    def _rearm_env(self, sid):
        """A live host stand-in B for a re-arm of the same session id."""
        host_b = self.start_host("launch-b")
        env_b = {
            **self.env,
            "CLAUDECODE": "1",
            "CLAUDE_PID": str(host_b.pid),
            "CLAUDE_CODE_SESSION_ID": sid,
        }
        return host_b, env_b

    def assert_wake_intact(self, env, paths, state):
        """Every file the wake's own arm wrote is still in place, and nothing
        else was left behind. (`created` also names the wants link and stamp,
        which systemd creates and the fake systemctl does not.)"""
        unit_directory = units.unit_dir(env)
        arm_wrote = [paths.state, paths.lock] + [
            path for path in state["created"] if os.path.dirname(path) == unit_directory
        ]
        for path in arm_wrote:
            self.assertTrue(os.path.exists(path), path)
        own = set(state["created"]) | {paths.state, paths.lock, paths.done}
        self.assertEqual(set(), set(_leftover_files(env)) - own)

    # (a) a disarm landing inside step (5) liveness: nothing remains.
    def test_a_disarm_during_liveness_leaves_nothing(self):
        sid = uuid.uuid4().hex
        env, paths = self._gone_session(sid)

        def action():
            self.disarm_claude(sid, env)  # 26-02's removal, not Task 3's idle done

        code, out = self._interleaved_fire(sid, env, "is_alive", action)
        self.assertEqual(0, code)
        self.assertNotIn("gave up", out)
        self._assert_no_host_call()
        self.assert_no_wake_files(env, paths)

    # (b) disarm plus a first arm from a live host B inside step (5): the fire
    # locks the new inode, sees the other arm_id and abandons.
    def test_b_disarm_rearm_during_liveness_abandons(self):
        sid = uuid.uuid4().hex
        env, paths = self._gone_session(sid)
        old_arm_id = _read(paths.state)["arm_id"]
        host_b, env_b = self._rearm_env(sid)

        def action():
            self.disarm_claude(sid, env)
            with _silence():
                self.assertEqual(0, cli.main(["arm"], seams=fakes.fixed_seams(env_b, FIRE_AT)))

        code, out = self._interleaved_fire(sid, env, "is_alive", action)
        self.assertEqual(0, code)
        self.assertNotIn("gave up", out)
        self.assertIn("wake re-armed", out)
        self._assert_no_host_call()
        new_state = _read(paths.state)
        self.assertEqual(host_b.pid, new_state["pid"])
        self.assertEqual(0, new_state["wake_count"])
        self.assertNotEqual(old_arm_id, new_state["arm_id"])
        # the fire released the new lock inode: it is free to take right now
        fd = os.open(paths.lock, os.O_RDONLY)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)
        self.assert_wake_intact(env, paths, new_state)

    # (c) a .done marker landing inside the session probe: the re-check
    # before Popen disarms.
    def test_c_done_marker_during_probe_disarms(self):
        sid = uuid.uuid4().hex
        env, paths = self._gone_session(sid)

        def action():
            from ai_kit_session_wake.state import touch_marker

            touch_marker(paths.done)

        code, out = self._interleaved_fire(sid, env, "session_exists", action)
        self.assertEqual(0, code)
        self.assertNotIn("gave up", out)
        self._assert_no_host_call()
        self.assert_no_wake_files(env, paths)

    # (d) a re-arm recording a live host B lands inside the session probe:
    # the re-check before Popen logs the live host and the wake stays armed.
    def test_d_live_rearm_during_probe_logs_alive(self):
        sid = uuid.uuid4().hex
        env, paths = self._gone_session(sid)
        host_b, env_b = self._rearm_env(sid)

        def action():
            with _silence():
                self.assertEqual(0, cli.main(["arm"], seams=fakes.fixed_seams(env_b, FIRE_AT)))

        code, out = self._interleaved_fire(sid, env, "session_exists", action)
        self.assertEqual(0, code)
        self.assertIn("host alive; log only", out)
        self.assertNotIn("gave up", out)
        self._assert_no_host_call()
        state = _read(paths.state)
        self.assertEqual(host_b.pid, state["pid"])
        self.assert_wake_intact(env, paths, state)

    # (e) review round 2: disarm, a first arm from B, then B exits; the old
    # fire locks the new lock, sees the other arm_id and abandons; B's wake
    # keeps every file with wake_count 0.
    def test_e_disarm_rearm_then_b_gone_abandons(self):
        sid = uuid.uuid4().hex
        env, paths = self._gone_session(sid)
        old_arm_id = _read(paths.state)["arm_id"]
        host_b, env_b = self._rearm_env(sid)

        def action():
            self.disarm_claude(sid, env)
            with _silence():
                self.assertEqual(0, cli.main(["arm"], seams=fakes.fixed_seams(env_b, FIRE_AT)))
            _kill(host_b)

        code, out = self._interleaved_fire(sid, env, "is_alive", action)
        self.assertEqual(0, code)
        self.assertNotIn("gave up", out)
        self.assertIn("wake re-armed", out)
        self._assert_no_host_call()
        new_state = _read(paths.state)
        self.assertEqual(0, new_state["wake_count"])
        self.assertNotEqual(old_arm_id, new_state["arm_id"])
        self.assert_wake_intact(env, paths, new_state)

    # (f) review round 2: a same-arm refresh moves not_before into the future
    # (what 26-06's reset re-arm writes), then B exits; the re-check before
    # Popen sees now < not_before and refuses; the wake stays armed with its
    # arm_id unchanged.
    def test_f_refresh_not_before_before_popen_refuses(self):
        sid = uuid.uuid4().hex
        env, paths = self._gone_session(sid)
        old_arm_id = _read(paths.state)["arm_id"]
        host_b, env_b = self._rearm_env(sid)

        def action():
            with _silence():
                self.assertEqual(0, cli.main(["arm"], seams=fakes.fixed_seams(env_b, FIRE_AT)))
            update_state(paths.state, lambda state: {**state, "not_before": FIRE_AT + 3600.0})
            _kill(host_b)

        code, out = self._interleaved_fire(sid, env, "session_exists", action)
        self.assertEqual(0, code)
        self.assertIn("not resuming this wake: not before", out)
        self.assertNotIn("gave up", out)
        self._assert_no_host_call()
        state = _read(paths.state)
        self.assertEqual(old_arm_id, state["arm_id"])
        self.assertEqual(FIRE_AT + 3600.0, state["not_before"])
        self.assert_wake_intact(env, paths, state)

    # (g) review round 3: a same-arm reset refresh landing just before the
    # step (4) increment moves not_before past now, so the count itself
    # declines: not counted, count stays 23, every file stays.
    def test_g_reset_refresh_at_count_not_counted(self):
        sid = uuid.uuid4().hex
        env, paths = self._gone_session(sid)
        update_state(paths.state, lambda state: {**state, "wake_count": 23})

        def action():
            update_state(paths.state, lambda state: {**state, "not_before": FIRE_AT + 3600.0})

        code, out = self._interleaved_fire(sid, env, "update_state", action)
        self.assertEqual(0, code)
        self.assertIn("not counted", out)
        self.assertNotIn("gave up", out)
        self._assert_no_host_call()
        state = _read(paths.state)
        self.assertEqual(23, state["wake_count"])
        self.assertEqual(FIRE_AT + 3600.0, state["not_before"])
        self.assert_wake_intact(env, paths, state)

    # (h) review round 3: a disarm plus first arm landing just before the
    # step (4) increment: the fire exits uncounted, the new arm keeps
    # wake_count 0 and every file, no host call, no give-up line.
    def test_h_disarm_rearm_at_count_uncounted(self):
        sid = uuid.uuid4().hex
        env, paths = self._gone_session(sid)
        old_arm_id = _read(paths.state)["arm_id"]
        _host_b, env_b = self._rearm_env(sid)

        def action():
            self.disarm_claude(sid, env)
            with _silence():
                self.assertEqual(0, cli.main(["arm"], seams=fakes.fixed_seams(env_b, FIRE_AT)))

        code, out = self._interleaved_fire(sid, env, "update_state", action)
        self.assertEqual(0, code)
        self.assertNotIn("gave up", out)
        self._assert_no_host_call()
        new_state = _read(paths.state)
        self.assertEqual(0, new_state["wake_count"])
        self.assertNotEqual(old_arm_id, new_state["arm_id"])
        self.assert_wake_intact(env, paths, new_state)


class TestFireSequence(_Scratch):
    """The fixed D-10 order: liveness edges (D-08), done first, the arm
    window boundary (D-29), the missing-state empty edge."""

    def _write_units_only(self, sid, env):
        """Both unit files, but no state file (SPEC R4 empty edge)."""
        timer, service = units.unit_names("claude", sid)
        ud = units.unit_dir(env)
        write_json_atomic(os.path.join(ud, timer), {})
        write_json_atomic(os.path.join(ud, service), {})

    def test_live_host_logs_only_counts_and_never_resumes(self):
        sid = uuid.uuid4().hex
        host = self.start_host()
        env = self.arm_claude(sid, host)
        paths = session_paths(env, "claude", sid)
        self.arm_window_open(paths)
        code, out = self.fire_claude(sid, env)
        self.assertEqual(0, code)
        self.assertIn("host alive; log only (wake 1/24)", out)
        self.assertEqual(1, _read(paths.state)["wake_count"])
        self.assertEqual([], self.host_calls())

    def test_reaped_pid_resumes_once(self):
        sid = uuid.uuid4().hex
        host = self.start_host()
        env = self.arm_claude(sid, host)
        paths = session_paths(env, "claude", sid)
        host.kill()
        host.wait()
        self.arm_window_open(paths)
        code, out = self.fire_claude(sid, env)
        self.assertEqual(0, code)
        self.assertIn("resume exit 0", out)
        calls = self.host_calls()
        self.assertEqual(1, len(calls))
        self.assertIn(["--resume", sid], [call["argv"][:2] for call in calls])
        self.assertEqual(1, _read(paths.state)["wake_count"])

    def test_recorded_pid_with_other_start_time_resumes_once(self):
        """SPEC R4 adjacency: a recorded pid reused by an unrelated process
        (other start time) does not count as alive."""
        sid = uuid.uuid4().hex
        host = self.start_host()
        env = self.arm_claude(sid, host)
        paths = session_paths(env, "claude", sid)
        update_state(paths.state, lambda state: {**state, "not_before": 0.0, "pid_start": "1"})
        code, _out = self.fire_claude(sid, env)
        self.assertEqual(0, code)
        self.assertEqual(1, len(self.host_calls()))
        self.assertEqual(1, _read(paths.state)["wake_count"])

    def test_recorded_pid_with_other_boot_id_resumes_once(self):
        sid = uuid.uuid4().hex
        host = self.start_host()
        env = self.arm_claude(sid, host)
        paths = session_paths(env, "claude", sid)
        update_state(
            paths.state,
            lambda state: {**state, "not_before": 0.0, "boot_id": "0" * 32},
        )
        code, _out = self.fire_claude(sid, env)
        self.assertEqual(0, code)
        self.assertEqual(1, len(self.host_calls()))

    def test_done_marker_with_live_host_disarms_first_without_counting(self):
        sid = uuid.uuid4().hex
        host = self.start_host()
        env = self.arm_claude(sid, host)
        paths = session_paths(env, "claude", sid)
        from ai_kit_session_wake.state import touch_marker

        touch_marker(paths.done)
        calls = []
        real_update = fire_mod.update_state

        def spy(path, fn):
            calls.append(path)
            return real_update(path, fn)

        with mock.patch.object(fire_mod, "update_state", spy):
            code, out = self.fire_claude(sid, env)
        self.assertEqual(0, code)
        self.assertEqual([], calls)  # done is checked before the count
        self.assertEqual([], self.host_calls())
        self.assertNotIn("host alive", out)
        self.assert_no_wake_files(env, paths)

    def test_missing_state_with_units_disarms_by_name(self):
        sid = uuid.uuid4().hex
        self._write_units_only(sid, self.env)
        timer, _service = units.unit_names("claude", sid)
        code, _out = self.fire_claude(sid, self.env)
        self.assertEqual(0, code)
        self.assertEqual(
            [
                ["--user", "disable", "--now", timer],
                ["--user", "clean", "--what=state", timer],
                ["--user", "daemon-reload"],
            ],
            self.systemctl_calls()[-3:],
        )
        self.assertEqual([], _leftover_files(self.env))

    def test_arm_window_boundary_not_before(self):
        sid = uuid.uuid4().hex
        host = self.start_host()
        env = self.arm_claude(sid, host)
        paths = session_paths(env, "claude", sid)
        host.kill()
        host.wait()
        code, out = self.fire_claude(sid, env, seams=fakes.fixed_seams(env, T0 + 59))
        self.assertEqual(0, code)
        self.assertIn("not counted", out)
        self.assertEqual(0, _read(paths.state)["wake_count"])
        self.assertEqual([], self.host_calls())
        code, out = self.fire_claude(sid, env, seams=fakes.fixed_seams(env, T0 + 60))
        self.assertEqual(0, code)
        self.assertEqual(1, _read(paths.state)["wake_count"])
        self.assertEqual(1, len(self.host_calls()))


class TestGiveUp(_Scratch):
    """The cap give-up (D-11, D-31): one finish step after every counted exit,
    one journal line and one bounded desktop notice, never a silent disarm."""

    def _gone_at_count(self, sid, count, bus=False):
        """Arm, kill the host, pin the count and open the arm window."""
        host = self.start_host()
        env = self.arm_claude(sid, host)
        paths = session_paths(env, "claude", sid)
        host.kill()
        host.wait()
        update_state(
            paths.state,
            lambda state: {**state, "not_before": 0.0, "wake_count": count},
        )
        if bus:
            runtime = os.path.join(self.root, "xdgr")
            os.makedirs(runtime, exist_ok=True)
            with open(os.path.join(runtime, "bus"), "w", encoding="utf-8"):
                pass
            env = {**env, "XDG_RUNTIME_DIR": runtime}
        return env, paths

    def notify_calls(self):
        if not os.path.exists(self.env["AI_KIT_FAKE_LOG"]):
            return []
        return [
            e
            for e in fakes.read_log(self.env["AI_KIT_FAKE_LOG"])
            if e["name"] == "notify-send"
        ]

    def test_cap_reached_after_resume_gives_up_once(self):
        sid = uuid.uuid4().hex
        env, paths = self._gone_at_count(sid, 23)
        code, out = self.fire_claude(sid, env)
        self.assertEqual(0, code)
        self.assertEqual(1, len(self.host_calls()))  # the 24th wake ran
        self.assertIn("gave up", out)
        self.assertIn(paths.state, out)
        self.assertIn("last resume exit 0", out)
        self.assert_no_wake_files(env, paths)

    def test_state_already_at_cap_gives_up_without_resuming(self):
        sid = uuid.uuid4().hex
        env, paths = self._gone_at_count(sid, 24)
        code, out = self.fire_claude(sid, env)
        self.assertEqual(0, code)
        self.assertEqual([], self.host_calls())  # no 25th
        self.assertIn("gave up", out)
        self.assert_no_wake_files(env, paths)

    def test_give_up_notifies_once_with_session_bus(self):
        sid = uuid.uuid4().hex
        fakes.fake_notify_send(self.bin_dir)
        env, paths = self._gone_at_count(sid, 23, bus=True)
        code, out = self.fire_claude(sid, env)
        self.assertEqual(0, code)
        self.assertIn("gave up", out)
        notices = self.notify_calls()
        self.assertEqual(1, len(notices))
        self.assertEqual("ai-kit session wake gave up", notices[0]["argv"][0])
        self.assertIn(paths.state, notices[0]["argv"][1])

    def test_no_session_bus_no_notification(self):
        sid = uuid.uuid4().hex
        fakes.fake_notify_send(self.bin_dir)
        env, _paths = self._gone_at_count(sid, 24, bus=False)
        code, out = self.fire_claude(sid, env)
        self.assertEqual(0, code)
        self.assertIn("gave up", out)  # the journal line is the record
        self.assertEqual([], self.notify_calls())

    def test_failing_notifier_never_fails_the_fire(self):
        sid = uuid.uuid4().hex
        fakes.fake_notify_send(self.bin_dir)
        env, _paths = self._gone_at_count(sid, 24, bus=True)
        env = {**env, "FAKE_NOTIFY_FAIL": "1"}
        code, out = self.fire_claude(sid, env)
        self.assertEqual(0, code)
        self.assertEqual(1, len(self.notify_calls()))
        self.assertIn("gave up", out)

    def test_slow_notifier_is_bounded_and_never_fails_the_fire(self):
        sid = uuid.uuid4().hex
        fakes.fake_notify_send(self.bin_dir)
        env, _paths = self._gone_at_count(sid, 24, bus=True)
        env = {**env, "FAKE_NOTIFY_SLEEP": "5"}
        started = time.monotonic()
        with mock.patch.object(fire_mod, "NOTIFY_TIMEOUT_S", 0.5):
            code, out = self.fire_claude(sid, env)
        elapsed = time.monotonic() - started
        self.assertEqual(0, code)
        self.assertEqual(1, len(self.notify_calls()))
        self.assertIn("gave up", out)
        self.assertLess(elapsed, 3.0)

    def test_missing_session_at_fire_time_gives_up(self):
        sid = uuid.uuid4().hex
        host = self.start_host()
        env = self.arm_claude(sid, host)
        paths = session_paths(env, "claude", sid)
        host.kill()
        host.wait()
        self.arm_window_open(paths)
        transcript = fakes.claude_session(env["HOME"], sid)
        os.remove(transcript)
        code, out = self.fire_claude(sid, env)
        self.assertEqual(0, code)
        self.assertIn("gave up", out)
        self.assertIn(f"session {sid} not found", out)
        self.assertEqual([], self.host_calls())
        self.assert_no_wake_files(env, paths)

    # Cap finalization (review round 1): every 24th-wake route prints exactly
    # one give-up line, notifies once, and leaves no session file.

    def test_cap_finalize_unknown_probe(self):
        sid = uuid.uuid4().hex
        fakes.fake_notify_send(self.bin_dir)
        env, paths = self._gone_at_count(sid, 23, bus=True)
        with mock.patch.object(
            fire_mod, "session_exists", lambda *args, **kwargs: ("unknown", "probe down")
        ):
            code, out = self.fire_claude(sid, env)
        self.assertEqual(0, code)
        self.assertIn("cannot check the session", out)
        self.assertEqual(1, len(self.notify_calls()))
        self.assert_no_wake_files(env, paths)

    def test_cap_finalize_spawn_error_names_127(self):
        sid = uuid.uuid4().hex
        fakes.fake_notify_send(self.bin_dir)
        env, paths = self._gone_at_count(sid, 23, bus=True)
        vanished = os.path.join(self.root, "vanished", "claude")
        update_state(paths.state, lambda state: {**state, "cli_path": vanished})
        code, out = self.fire_claude(sid, env)
        self.assertEqual(0, code)
        self.assertIn("gave up", out)
        self.assertIn("last resume exit 127", out)
        self.assertEqual([], self.host_calls())  # nothing was spawned
        self.assertEqual(1, len(self.notify_calls()))
        self.assert_no_wake_files(env, paths)

    def test_cap_finalize_live_host(self):
        sid = uuid.uuid4().hex
        fakes.fake_notify_send(self.bin_dir)
        host = self.start_host()
        env = self.arm_claude(sid, host)
        paths = session_paths(env, "claude", sid)
        update_state(
            paths.state,
            lambda state: {**state, "not_before": 0.0, "wake_count": 23},
        )
        runtime = os.path.join(self.root, "xdgr")
        os.makedirs(runtime, exist_ok=True)
        with open(os.path.join(runtime, "bus"), "w", encoding="utf-8"):
            pass
        env = {**env, "XDG_RUNTIME_DIR": runtime}
        code, out = self.fire_claude(sid, env)
        self.assertEqual(0, code)
        self.assertIn("host alive; log only (wake 24/24)", out)
        self.assertEqual(1, len(self.notify_calls()))
        self.assertIn("gave up", out)
        self.assert_no_wake_files(env, paths)

    def test_cap_finalize_normal_resume(self):
        sid = uuid.uuid4().hex
        fakes.fake_notify_send(self.bin_dir)
        env, paths = self._gone_at_count(sid, 23, bus=True)
        code, out = self.fire_claude(sid, env)
        self.assertEqual(0, code)
        self.assertEqual(1, len(self.notify_calls()))
        self.assertEqual(1, out.count("gave up"))
        self.assert_no_wake_files(env, paths)

    def test_wake_25_gives_up_once_never_silently(self):
        sid = uuid.uuid4().hex
        fakes.fake_notify_send(self.bin_dir)
        env, paths = self._gone_at_count(sid, 24, bus=True)
        code, out = self.fire_claude(sid, env)
        self.assertEqual(0, code)
        self.assertEqual([], self.host_calls())
        self.assertEqual(1, len(self.notify_calls()))
        self.assertEqual(1, out.count("gave up"))
        self.assert_no_wake_files(env, paths)

    def test_held_lock_skips_wake_and_the_holder_finishes(self):
        sid = uuid.uuid4().hex
        env, paths = self._gone_at_count(sid, 23)
        helper = fakes.hold_lock(paths.lock, 2.0)
        self.addCleanup(_kill, helper)
        stream = helper.stdout
        assert stream is not None
        self.assertEqual("locked", stream.readline().strip())
        code, out = self.fire_claude(sid, env)
        self.assertEqual(0, code)
        self.assertIn("not resuming this wake", out)
        self.assertNotIn("gave up", out)  # the lock holder finishes this wake
        self.assertEqual([], self.host_calls())
        self.assertEqual(24, _read(paths.state)["wake_count"])
        helper.wait(timeout=60)
        code, out = self.fire_claude(sid, env)
        self.assertEqual(0, code)
        self.assertEqual(1, out.count("gave up"))
        self.assert_no_wake_files(env, paths)

    def test_resume_timeout_kills_group_and_records_124(self):
        sid = uuid.uuid4().hex
        host = self.start_host()
        env = self.arm_claude(sid, host)
        paths = session_paths(env, "claude", sid)
        host.kill()
        host.wait()
        self.arm_window_open(paths)
        hung_env = {**env, "FAKE_HOST_SLEEP": "30"}
        fake_claude = os.path.join(self.bin_dir, "claude")
        with mock.patch.object(fire_mod, "RESUME_TIMEOUT_S", 1):
            code, out = self.fire_claude(sid, hung_env)
        self.assertEqual(0, code)
        self.assertIn("resume exit 124", out)
        self.assertEqual(124, _read(paths.state)["last_resume_exit"])
        # the resume child and its process group are gone
        for entry in os.listdir("/proc"):
            if not entry.isdigit():
                continue
            try:
                with open(f"/proc/{entry}/cmdline", "rb") as handle:
                    cmdline = handle.read().decode("utf-8", "replace")
            except OSError:
                continue
            self.assertNotIn(fake_claude, cmdline, f"/proc/{entry} still runs the resume")
        # the lock is free
        fd = os.open(paths.lock, os.O_RDONLY)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)

    def test_normal_resume_records_its_exit_code(self):
        sid = uuid.uuid4().hex
        host = self.start_host()
        env = self.arm_claude(sid, host)
        paths = session_paths(env, "claude", sid)
        host.kill()
        host.wait()
        self.arm_window_open(paths)
        code, out = self.fire_claude(sid, {**env, "FAKE_HOST_EXIT": "3"})
        self.assertEqual(0, code)
        self.assertIn("resume exit 3", out)
        self.assertEqual(3, _read(paths.state)["last_resume_exit"])


class TestDisarm(_Scratch):
    """Disarm and done under every trigger (SPEC R5; D-02, D-13): nothing
    armed, the lock wait, the in-fire fallback, idle done, and exactly the
    wake's own paths removed."""

    def _armed(self, sid):
        host = self.start_host()
        env = self.arm_claude(sid, host)
        paths = session_paths(env, "claude", sid)
        return env, paths, host

    def test_disarm_with_nothing_armed(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = cli.main(
                ["disarm", "--host", "claude", "--session-id", "never-armed"],
                seams=fakes.fixed_seams(self.env, T0),
            )
        self.assertEqual(0, code)
        self.assertIn("nothing to disarm", out.getvalue())

    def test_disarm_waits_for_the_running_resume_lock(self):
        sid = uuid.uuid4().hex
        env, paths, _host = self._armed(sid)
        helper = fakes.hold_lock(paths.lock, 2.0)
        self.addCleanup(_kill, helper)
        stream = helper.stdout
        assert stream is not None
        self.assertEqual("locked", stream.readline().strip())
        started = time.monotonic()
        proc = subprocess.Popen(
            [sys.executable, _SHIM, "disarm", "--host", "claude", "--session-id", sid],
            env=self.env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.addCleanup(_kill, proc)
        _out, err = proc.communicate(timeout=120)
        elapsed = time.monotonic() - started
        self.assertEqual(0, proc.returncode, err)
        self.assertGreaterEqual(elapsed, 1.5)  # it finished only after the release
        helper.wait(timeout=60)
        self.assert_no_wake_files(env, paths)

    def test_disarm_inside_fire_child_writes_done_and_removes_nothing(self):
        sid = uuid.uuid4().hex
        env, paths, _host = self._armed(sid)
        marked_env = {**env, "AI_KIT_SESSION_WAKE_FIRE": f"claude-{sid}"}
        timer, _service = units.unit_names("claude", sid)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = cli.main(
                ["disarm", "--host", "claude", "--session-id", sid],
                seams=fakes.fixed_seams(marked_env, FIRE_AT),
            )
        self.assertEqual(0, code)
        self.assertIn("removes everything when its resume exits", out.getvalue())
        self.assertTrue(os.path.exists(paths.done), paths.done)
        self.assertTrue(os.path.exists(paths.state), paths.state)
        self.assertTrue(os.path.exists(os.path.join(units.unit_dir(env), timer)))

    def test_done_with_lock_free_disarms_at_once(self):
        sid = uuid.uuid4().hex
        env, paths, _host = self._armed(sid)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = cli.main(
                ["done", "--host", "claude", "--session-id", sid],
                seams=fakes.fixed_seams(env, FIRE_AT),
            )
        self.assertEqual(0, code)
        self.assertIn(paths.done, out.getvalue())
        self.assert_no_wake_files(env, paths)

    def test_done_with_lock_held_writes_marker_only(self):
        sid = uuid.uuid4().hex
        env, paths, _host = self._armed(sid)
        timer, _service = units.unit_names("claude", sid)
        helper = fakes.hold_lock(paths.lock, 2.0)
        self.addCleanup(_kill, helper)
        stream = helper.stdout
        assert stream is not None
        self.assertEqual("locked", stream.readline().strip())
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = cli.main(
                ["done", "--host", "claude", "--session-id", sid],
                seams=fakes.fixed_seams(env, FIRE_AT),
            )
        self.assertEqual(0, code)
        self.assertIn("a wake resume is running; it disarms when the resume exits", out.getvalue())
        self.assertTrue(os.path.exists(paths.done), paths.done)
        self.assertTrue(os.path.exists(paths.state), paths.state)
        self.assertTrue(os.path.exists(os.path.join(units.unit_dir(env), timer)))
        helper.wait(timeout=60)

    def test_done_inside_fire_child_stops_after_marker(self):
        sid = uuid.uuid4().hex
        env, paths, _host = self._armed(sid)
        timer, _service = units.unit_names("claude", sid)
        marked_env = {**env, "AI_KIT_SESSION_WAKE_FIRE": f"claude-{sid}"}
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = cli.main(
                ["done", "--host", "claude", "--session-id", sid],
                seams=fakes.fixed_seams(marked_env, FIRE_AT),
            )
        self.assertEqual(0, code)
        self.assertTrue(os.path.exists(paths.done), paths.done)
        self.assertTrue(os.path.exists(paths.state), paths.state)
        self.assertTrue(os.path.exists(os.path.join(units.unit_dir(env), timer)))

    def test_three_triggers_each_leave_no_wake_file(self):
        for trigger in ("done-then-fire", "disarm", "cap"):
            with self.subTest(trigger=trigger):
                sid = uuid.uuid4().hex
                env, paths, host = self._armed(sid)
                if trigger == "done-then-fire":
                    from ai_kit_session_wake.state import touch_marker

                    touch_marker(paths.done)
                    host.kill()
                    host.wait()
                    code, _out = self.fire_claude(sid, env)
                    self.assertEqual(0, code)
                elif trigger == "disarm":
                    self.disarm_claude(sid, env)
                else:
                    host.kill()
                    host.wait()
                    update_state(paths.state, lambda state: {**state, "wake_count": 24})
                    code, out = self.fire_claude(sid, env)
                    self.assertEqual(0, code)
                    self.assertIn("gave up", out)
                ud = units.unit_dir(env)
                wants = os.path.join(ud, "timers.target.wants")
                for base in (ud, wants):
                    if os.path.isdir(base):
                        self.assertEqual(
                            [],
                            [name for name in os.listdir(base) if "ai-kit-session-wake-" in name],
                            base,
                        )
                self.assert_no_wake_files(env, paths)

    def test_foreign_created_entries_survive_disarm(self):
        sid_a, sid_b = uuid.uuid4().hex, uuid.uuid4().hex
        env_a, paths_a, host_a = self._armed(sid_a)
        host_b = self.start_host("launch-b")
        env_b = {
            **self.env,
            "CLAUDECODE": "1",
            "CLAUDE_PID": str(host_b.pid),
            "CLAUDE_CODE_SESSION_ID": sid_b,
        }
        fakes.claude_session(env_b["HOME"], sid_b)
        with _silence():
            self.assertEqual(0, cli.main(["arm"], seams=fakes.fixed_seams(env_b, T0)))
        paths_b = session_paths(env_b, "claude", sid_b)
        keep = os.path.join(self.root, "keep.txt")
        with open(keep, "w", encoding="utf-8") as handle:
            handle.write("keep")
        update_state(
            paths_a.state,
            lambda state: {**state, "created": [*state["created"], keep, paths_b.state]},
        )
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(
                0,
                cli.main(
                    ["disarm", "--host", "claude", "--session-id", sid_a],
                    seams=fakes.fixed_seams(env_a, FIRE_AT),
                ),
            )
        text = out.getvalue()
        self.assertIn(f"skipped foreign path {keep}", text)
        self.assertIn(f"skipped foreign path {paths_b.state}", text)
        self.assertTrue(os.path.exists(keep), keep)
        self.assertTrue(os.path.exists(paths_b.state), paths_b.state)
        self.assertFalse(os.path.exists(paths_a.state), paths_a.state)
        self.assertEqual([], self.host_calls())
        _kill(host_a)

    def test_same_named_files_in_foreign_folders_survive(self):
        """Review round 2 (T-26-40): the wake's exact file names under other
        folders are foreign and survive; only the seams-derived paths go."""
        sid = uuid.uuid4().hex
        env, paths, _host = self._armed(sid)
        timer, service = units.unit_names("claude", sid)
        foreign = os.path.join(self.root, "foreign")
        foreign_files = {
            os.path.join(foreign, "user", service),
            os.path.join(foreign, "session-wake", f"claude-{sid}.json"),
            os.path.join(foreign, "timers", f"stamp-{timer}"),
            os.path.join(foreign, "timers.target.wants", timer),
        }
        for path in foreign_files:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as handle:
                handle.write("foreign")
        update_state(
            paths.state,
            lambda state: {**state, "created": [*state["created"], *foreign_files]},
        )
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(
                0,
                cli.main(
                    ["disarm", "--host", "claude", "--session-id", sid],
                    seams=fakes.fixed_seams(env, FIRE_AT),
                ),
            )
        text = out.getvalue()
        for path in foreign_files:
            self.assertIn(f"skipped foreign path {path}", text)
            self.assertTrue(os.path.exists(path), path)
        self.assert_no_wake_files(env, paths)

    _MUTATIONS = (
        ("schema_version", 2, "schema_version"),
        ("host", "codex", "host"),
        ("session_id", "another-id", "session_id"),
        ("wake_count", -1, "wake_count"),
        ("wake_count", "3", "wake_count"),
        ("wake_count", True, "wake_count"),
        ("cap", 25, "cap"),
        ("created", "not-a-list", "created"),
    )

    def test_one_field_invalid_states_are_removed_by_name(self):
        for field, value, needle in self._MUTATIONS:
            with self.subTest(field=field, value=value):
                sid = uuid.uuid4().hex
                env, paths, host = self._armed(sid)
                host.kill()
                host.wait()
                self.arm_window_open(paths)
                foreign = os.path.join(self.root, f"keep-{field}.txt")
                with open(foreign, "w", encoding="utf-8") as handle:
                    handle.write("keep")
                update_state(
                    paths.state,
                    lambda state, extra=foreign: {
                        **state,
                        "created": [*state["created"], extra],
                    },
                )
                state = _read(paths.state)
                state[field] = value
                write_json_atomic(paths.state, state)
                code, out = self.fire_claude(sid, env)
                self.assertEqual(0, code)
                self.assertIn("invalid state", out)
                self.assertIn(needle, out)
                self.assertEqual([], self.host_calls())  # no resume on an invalid state
                self.assert_no_wake_files(env, paths)
                self.assertTrue(os.path.exists(foreign), foreign)  # created is never trusted


if __name__ == "__main__":
    unittest.main()
