"""The one supervision core: argv, charset, trailer, tiers, cleanup, custom entries (R7)."""

import contextlib
import errno
import io
import json
import os
import re
import signal
import sys
import tempfile
import textwrap
import time
import unittest
import uuid
from contextlib import redirect_stderr, redirect_stdout
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills", "ai-kit-spec-review"))

from ai_kit_spec import detection, reviewer_dispatch
from ai_kit_spec import runner_dispatch as rd
from ai_kit_spec.cli import main
from ai_kit_spec.detection import HOST_SIGNAL_ENV_VARS
from ai_kit_spec.runner_dispatch import (
    CURSOR_MODEL_ID_SRC,
    MODEL_ID_SRC,
    CustomSpec,
    RunnerSeams,
    RunnerSpec,
    build_runner_argv,
    parse_status_line,
    run_custom_command,
    run_runner,
    run_runner_tiers,
    runner_flags,
)
from ai_kit_spec.tooling_guidance import resolve_cross_ai_template_path

_STATUS = (
    "AIKIT-XAI status={status} cli={cli} model={model} exit={exit} cli_rc=0 "
    "elapsed=1s out=4 tree=clean action=stop"
)


def _status_line(status="ok", cli="opencode", model="fake/ok", exit_code="0"):
    return _STATUS.format(status=status, cli=cli, model=model, exit=exit_code)


class _FakeClock:
    """Monotonic time the test drives: each sleep jumps the clock forward."""

    def __init__(self):
        self.now = 0.0

    def time(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds


class _FakeProc:
    """A child that emits scripted stderr lines and then exits with `returncode`."""

    def __init__(self, stderr_lines, returncode=0, hang=False):
        self.pid = 4242
        self.returncode = None
        self._lines = list(stderr_lines)
        self._exit = returncode
        self._hang = hang
        self.stderr = self
        self.signals: list[int] = []

    def readline(self):
        if self._lines:
            return self._lines.pop(0) + "\n"
        return ""

    def poll(self):
        if self._hang or self._lines:
            return None
        self.returncode = self._exit
        return self.returncode

    def wait(self, timeout=None):
        del timeout
        self.returncode = self._exit
        return self.returncode

    def close(self):
        return None

    def kill(self):
        self.signals.append(signal.SIGKILL)


class _ScriptedPopen:
    """Serves one fake child per call and records the argv it was given."""

    def __init__(self, procs):
        self._procs = list(procs)
        self.argvs: list[list[str]] = []

    def __call__(self, argv, **_kwargs):
        self.argvs.append(list(argv))
        return self._procs.pop(0)


def _seams(popen, lines, kills, clock=None):
    clock = clock or _FakeClock()
    return RunnerSeams(
        which_fn=lambda name: "/usr/bin/node" if name == "node" else None,
        popen_fn=popen,
        time_fn=clock.time,
        sleep_fn=clock.sleep,
        kill_fn=lambda pgid, sig: kills.append((pgid, sig)),
        print_fn=lines.append,
        runner_path_fn=lambda: "/runner/cross-ai.mjs",
        env_fn=lambda: {"PATH": "/usr/bin"},
    )


def _spec(**overrides):
    fields = {"runtime": "opencode", "model": "fake/ok", "mode": "review", "timeout_s": 30}
    fields.update(overrides)
    return RunnerSpec(**fields)


class TestProjectRunnerCommand(unittest.TestCase):
    def test_opencode_exec_token_order(self):
        spec = RunnerSpec("opencode", "router-env/my-coding", "exec", 0)
        self.assertEqual(
            rd.project_runner_command(spec),
            "node .planning/scripts/cross-ai.mjs --prefer opencode "
            "--model-opencode router-env/my-coding --mode exec",
        )

    def test_codex_sandbox_only_in_exec_mode(self):
        exec_spec = RunnerSpec("codex", "m", "exec", 0, codex_sandbox="workspace-write")
        review_spec = exec_spec._replace(mode="review")
        exec_cmd = rd.project_runner_command(exec_spec)
        assert exec_cmd is not None
        self.assertTrue(exec_cmd.endswith("--codex-sandbox workspace-write"))
        review_cmd = rd.project_runner_command(review_spec)
        assert review_cmd is not None
        self.assertNotIn("codex-sandbox", review_cmd)

    def test_guidance_appends_prepend_file(self):
        spec = RunnerSpec("opencode", "m", "exec", 0)
        command = rd.project_runner_command(spec, guidance=True)
        assert command is not None
        self.assertTrue(command.endswith(
            "--no-preamble --prepend-file .planning/scripts/cross-ai-guidance.md"
        ))

    def test_unsupported_runtime_is_none(self):
        spec = RunnerSpec("claude", "opus", "exec", 0)
        self.assertIsNone(rd.project_runner_command(spec))

    def test_unsafe_model_tokens_are_none(self):
        for model in ("has space", "quo'te", "dol$lar", "star*", "paren("):
            with self.subTest(model=model):
                spec = RunnerSpec("opencode", model, "exec", 0)
                self.assertIsNone(rd.project_runner_command(spec))

    def test_bracket_model_is_never_a_hook_token(self):
        # GSD globs the unquoted hook: `gpt-6[effort=high]` would match a file `gpt-6e`.
        for runtime in ("cursor", "opencode"):
            with self.subTest(runtime=runtime):
                spec = RunnerSpec(runtime, "gpt-6[effort=high]", "exec", 0)
                self.assertIsNone(rd.project_runner_command(spec))


class TestBuildRunnerArgv(unittest.TestCase):
    def test_opencode_review(self):
        spec = _spec(timeout_s=600)
        argv = build_runner_argv(spec, "/runner/cross-ai.mjs", "node")
        self.assertEqual(argv, [
            "node", "/runner/cross-ai.mjs", "--prefer", "opencode", "--model-opencode",
            "fake/ok", "--mode", "review", "--timeout", "600", "--outer-timeout", "630",
            "--no-preamble",
        ])

    def test_codex_exec_knobs(self):
        spec = _spec(
            runtime="codex", model="gpt", mode="exec", effort="high",
            service_tier="priority", codex_sandbox="workspace-write",
        )
        flags = runner_flags(spec)
        self.assertIn("--codex-effort", flags)
        self.assertIn("--codex-service-tier", flags)
        self.assertEqual(flags[flags.index("--codex-sandbox") + 1], "workspace-write")

    def test_every_codex_exec_spec_is_sandboxed(self):
        flags = runner_flags(_spec(runtime="codex", model="gpt", mode="exec"))
        self.assertEqual(flags[-2:], ["--codex-sandbox", "workspace-write"])
        self.assertNotIn("--codex-sandbox",
                         runner_flags(_spec(runtime="opencode", model="m", mode="exec")))

    def test_codex_review_has_no_sandbox(self):
        spec = _spec(runtime="codex", model="gpt", mode="review",
                     codex_sandbox="workspace-write")
        self.assertNotIn("--codex-sandbox", runner_flags(spec))

    def test_cursor_review_mode(self):
        spec = _spec(runtime="cursor", model="auto", mode="review", cursor_mode="plan")
        flags = runner_flags(spec)
        self.assertEqual(flags[flags.index("--cursor-mode") + 1], "plan")

    def test_cursor_exec_has_no_cursor_mode(self):
        spec = _spec(runtime="cursor", model="auto", mode="exec", cursor_mode="plan")
        self.assertNotIn("--cursor-mode", runner_flags(spec))

    def test_bracket_cursor_model_passes_through(self):
        spec = _spec(runtime="cursor", model="gpt[effort=high]", mode="review")
        flags = runner_flags(spec)
        self.assertEqual(flags[flags.index("--model-cursor") + 1], "gpt[effort=high]")


def _template_regex(name: str) -> str:
    template = resolve_cross_ai_template_path()
    assert template is not None
    with open(template, encoding="utf-8") as handle:
        source = handle.read()
    match = re.search(rf"const {name} = (/.*?/);", source)
    assert match is not None, name
    return match.group(1)


class TestModelIdCharsetParity(unittest.TestCase):
    def test_sources_match_the_template(self):
        self.assertEqual(MODEL_ID_SRC, _template_regex("MODEL_ID"))
        self.assertEqual(CURSOR_MODEL_ID_SRC, _template_regex("CURSOR_MODEL_ID"))

    def _refused(self, model):
        popen = _ScriptedPopen([])
        lines: list[str] = []
        result = run_runner(_spec(model=model), "hi", _seams(popen, lines, []))
        self.assertEqual(result.reason, "configuration")
        self.assertEqual(popen.argvs, [])
        self.assertTrue(any("is not a valid opencode model id" in line for line in lines))

    def test_leading_dash_refused(self):
        self._refused("-x")

    def test_space_refused(self):
        self._refused("a b")

    def test_bracket_refused_for_opencode_accepted_for_cursor(self):
        popen = _ScriptedPopen([_FakeProc([_status_line(cli="cursor", model="m[e=1]")])])
        lines: list[str] = []
        refused = run_runner(_spec(model="m[e=1]"), "hi", _seams(popen, lines, []))
        self.assertEqual(refused.reason, "configuration")
        self.assertEqual(popen.argvs, [])
        accepted = run_runner(
            _spec(runtime="cursor", model="m[e=1]"), "hi", _seams(popen, lines, [])
        )
        self.assertIsNone(accepted.reason)
        self.assertEqual(len(popen.argvs), 1)


class TestParseStatusLine(unittest.TestCase):
    def test_full_line(self):
        parsed = parse_status_line(_status_line())
        assert parsed is not None
        for key in ("status", "cli", "model", "exit", "cli_rc", "elapsed", "out", "tree",
                    "action"):
            self.assertIn(key, parsed)
        self.assertEqual(parsed["elapsed"], "1s")

    def test_bracket_model_kept(self):
        parsed = parse_status_line(_status_line(cli="cursor", model="x[effort=high]"))
        assert parsed is not None
        self.assertEqual(parsed["cli"], "cursor")
        self.assertEqual(parsed["model"], "x[effort=high]")

    def test_non_status_line(self):
        self.assertIsNone(parse_status_line("cross-ai: cli=opencode running"))
        self.assertIsNone(parse_status_line("AIKIT-XAI"))


class TestRunRunnerFake(unittest.TestCase):
    def _run(self, stderr_lines, returncode=0, hang=False, spec=None, timeout_s=30):
        proc = _FakeProc(stderr_lines, returncode, hang)
        popen = _ScriptedPopen([proc])
        lines: list[str] = []
        kills: list[tuple[int, int]] = []
        clock = _FakeClock()
        seams = _seams(popen, lines, kills, clock)
        result = run_runner(spec or _spec(timeout_s=timeout_s), "hi", seams)
        return result, lines, kills, popen, clock

    def test_relay_order_and_last_status(self):
        first = _status_line(status="crash", exit_code="1")
        last = _status_line(status="quota", exit_code="75")
        result, lines, _kills, _popen, _clock = self._run(
            ["cross-ai: starting", first, "cross-ai: retry", last], returncode=75
        )
        self.assertEqual(lines[:4], ["cross-ai: starting", first, "cross-ai: retry", last])
        assert result.status is not None
        self.assertEqual(result.status["status"], "quota")
        self.assertEqual(result.reason, "quota")

    def test_billing_capacity_git(self):
        cases = {
            "billing": "billing_or_access",
            "capacity": "capacity",
            "git_timeout": "git_timeout",
            "git_error": "real_error",
        }
        for status, reason in cases.items():
            result, *_rest = self._run([_status_line(status=status, exit_code="1")], 1)
            self.assertEqual(result.reason, reason, msg=status)

    def test_empty_answer_is_real_error(self):
        result, *_rest = self._run([_status_line(status="empty_answer", exit_code="1")], 1)
        self.assertEqual(result.reason, "real_error")

    def test_exit_127_without_status(self):
        result, *_rest = self._run(["cross-ai: boom"], returncode=127)
        self.assertIsNone(result.status)
        self.assertEqual(result.reason, "dispatch_unavailable")

    def test_deadline_backstop(self):
        result, _lines, kills, _popen, clock = self._run(
            [_status_line()], hang=True, timeout_s=30
        )
        self.assertTrue(result.timed_out)
        self.assertEqual(result.reason, "timeout")
        self.assertGreaterEqual(clock.now, 30 + 30 + 10)
        self.assertIn((4242, signal.SIGTERM), kills)
        self.assertIn((4242, signal.SIGKILL), kills)

    def test_interrupt_during_wait_reaps_the_group(self):
        clock = _FakeClock()
        interrupted: list[bool] = []

        def sleep(seconds):
            if not interrupted:
                interrupted.append(True)
                raise KeyboardInterrupt
            clock.sleep(seconds)

        kills: list[tuple[int, int]] = []
        seams = _seams(_ScriptedPopen([_FakeProc([], hang=True)]), [], kills, clock)
        with self.assertRaises(KeyboardInterrupt):
            run_runner(_spec(), "hi", seams._replace(sleep_fn=sleep))
        self.assertIn((4242, signal.SIGTERM), kills)
        self.assertIn((4242, signal.SIGKILL), kills)

    def test_second_interrupt_during_cleanup_still_kills_the_group(self):
        clock = _FakeClock()
        calls: list[int] = []

        def sleep(seconds):
            calls.append(1)
            if len(calls) == 1:
                raise KeyboardInterrupt
            if len(calls) == 2:  # inside _reap_group's grace wait: a real Ctrl+C
                os.kill(os.getpid(), signal.SIGINT)
            clock.sleep(seconds)

        kills: list[tuple[int, int]] = []
        seams = _seams(_ScriptedPopen([_FakeProc([], hang=True)]), [], kills, clock)
        with self.assertRaises(KeyboardInterrupt):
            run_runner(_spec(), "hi", seams._replace(sleep_fn=sleep))
        self.assertIn((4242, signal.SIGKILL), kills)
        self.assertIs(signal.getsignal(signal.SIGINT), signal.default_int_handler)

    def test_interrupt_right_after_popen_reaps_the_child(self):
        inner = _ScriptedPopen([_FakeProc([], hang=True)])

        def popen(argv, **kwargs):
            proc = inner(argv, **kwargs)
            os.kill(os.getpid(), signal.SIGINT)  # lands before the child is recorded
            return proc

        kills: list[tuple[int, int]] = []
        seams = _seams(popen, [], kills)
        with self.assertRaises(KeyboardInterrupt):
            run_runner(_spec(), "hi", seams)
        self.assertIn((4242, signal.SIGKILL), kills)

    def test_popen_oserror(self):
        def popen(_argv, **_kwargs):
            raise OSError("node missing at spawn")

        lines: list[str] = []
        seams = _seams(popen, lines, [])
        result = run_runner(_spec(), "hi", seams)
        self.assertEqual(result.reason, "dispatch_unavailable")
        self.assertTrue(any("node missing at spawn" in line for line in lines))

    def test_pgid_flag_and_dir_removed(self):
        seen: list[str] = []

        def popen(argv, **_kwargs):
            seen.append(argv[argv.index("--child-pgid-file") + 1])
            return _FakeProc([_status_line()])

        result = run_runner(_spec(), "hi", _seams(popen, [], []))
        self.assertNotIn("--child-pgid-file", result.argv)
        self.assertEqual(len(seen), 1)
        self.assertFalse(os.path.exists(os.path.dirname(seen[0])))

    def _forged(self, line, returncode):
        return self._run([line], returncode)

    def test_forged_exit_ignored(self):
        result, lines, *_rest = self._forged(_status_line(exit_code="0"), 1)
        self.assertIsNone(result.status)
        self.assertEqual(result.reason, "real_error")
        self.assertTrue(any("does not match this run" in line for line in lines))

    def test_forged_cli_ignored(self):
        result, lines, *_rest = self._forged(_status_line(cli="codex"), 0)
        self.assertIsNone(result.status)
        self.assertTrue(any("does not match this run" in line for line in lines))

    def test_forged_model_ignored(self):
        result, lines, *_rest = self._forged(_status_line(model="other/m"), 0)
        self.assertIsNone(result.status)
        self.assertTrue(any("does not match this run" in line for line in lines))

    def test_dash_trailer_accepted(self):
        result, *_rest = self._forged(_status_line(cli="-", model="-"), 0)
        assert result.status is not None
        self.assertEqual(result.status["status"], "ok")
        self.assertIsNone(result.reason)

    def test_valid_trailer_accepted(self):
        result, lines, *_rest = self._forged(_status_line(), 0)
        assert result.status is not None
        self.assertEqual(result.status["status"], "ok")
        self.assertFalse(any("does not match this run" in line for line in lines))


class TestRunRunnerTiers(unittest.TestCase):
    def _tiers(self, statuses, tiers=(600, 1200, 1800)):
        procs = [
            _FakeProc(
                [_status_line(status=status, exit_code="124" if status == "timeout" else "0")],
                124 if status == "timeout" else 0,
            )
            for status in statuses
        ]
        popen = _ScriptedPopen(procs)
        result = run_runner_tiers(_spec(), list(tiers), "hi", _seams(popen, [], []))
        timeouts = [
            argv[argv.index("--timeout") + 1] for argv in popen.argvs
        ]
        return result, timeouts

    def test_timeout_then_ok(self):
        result, timeouts = self._tiers(["timeout", "ok"])
        self.assertEqual(timeouts, ["600", "1200"])
        self.assertIsNone(result.reason)

    def test_auth_stops(self):
        result, timeouts = self._tiers(["auth"])
        self.assertEqual(timeouts, ["600"])
        self.assertEqual(result.reason, "auth")

    def test_all_timeouts(self):
        result, timeouts = self._tiers(["timeout", "timeout", "timeout"])
        self.assertEqual(timeouts, ["600", "1200", "1800"])
        self.assertEqual(result.reason, "timeout")

    def test_empty_tiers_raise(self):
        with self.assertRaises(ValueError):
            run_runner_tiers(_spec(), [], "hi", _seams(_ScriptedPopen([]), [], []))

    def test_git_timeout_stops(self):
        procs = [_FakeProc([_status_line(status="git_timeout", exit_code="1")], 1)]
        popen = _ScriptedPopen(procs)
        result = run_runner_tiers(_spec(), [600, 1200], "hi", _seams(popen, [], []))
        self.assertEqual(len(popen.argvs), 1)
        self.assertEqual(result.reason, "git_timeout")


def _marker() -> str:
    return f"aikit-leak-marker-{uuid.uuid4().hex}"


class _ChildTracker(unittest.TestCase):
    """Kills only the pids this test recorded, and only those."""

    def setUp(self):
        self._pids: list[int] = []
        self.addCleanup(self._kill_recorded)

    def record(self, pid: int) -> None:
        self._pids.append(pid)

    def _kill_recorded(self):
        for pid in self._pids:
            with contextlib.suppress(OSError):
                os.kill(pid, signal.SIGKILL)

    def marker_alive(self, marker: str) -> bool:
        for name in os.listdir("/proc"):
            if not name.isdigit():
                continue
            try:
                with open(f"/proc/{name}/cmdline", "rb") as handle:
                    cmdline = handle.read().replace(b"\x00", b" ").decode()
            except OSError:
                continue
            if marker in cmdline:
                return True
        return False


def _write_script(path: str, body: str) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(textwrap.dedent(body))


class TestSpawnCleanup(_ChildTracker):
    def test_grandchild_in_group_is_killed(self):
        marker = _marker()
        with tempfile.TemporaryDirectory() as tmp:
            script = os.path.join(tmp, "child.py")
            _write_script(script, f"""
                import subprocess, sys, time
                subprocess.Popen(
                    [sys.executable, "-c", "import time; time.sleep(60)", "{marker}"],
                    start_new_session=False)
                time.sleep(0.3)
                sys.exit(0)
            """)
            started = time.monotonic()
            result = run_custom_command(
                CustomSpec("k", [sys.executable, script, marker], [5]), "hi"
            )
            self.assertLess(time.monotonic() - started, 10)
            self.assertEqual(result.returncode, 0)
            self.assertFalse(self.marker_alive(marker))

    def test_escaped_grandchild_is_abandoned(self):
        marker = _marker()
        with tempfile.TemporaryDirectory() as tmp:
            pid_file = os.path.join(tmp, "gc.pid")
            script = os.path.join(tmp, "child.py")
            _write_script(script, f"""
                import os, subprocess, sys, time
                proc = subprocess.Popen(
                    [sys.executable, "-c",
                     "import os,sys,time; open(sys.argv[1],'w').write(str(os.getpid()));"
                     "time.sleep(60)", "{pid_file}", "{marker}"],
                    start_new_session=True)
                time.sleep(0.3)
                os.dup2(proc.stderr.fileno(), 2)
                sys.exit(0)
            """)
            lines: list[str] = []
            seams = RunnerSeams(print_fn=lines.append)
            started = time.monotonic()
            run_custom_command(
                CustomSpec("k", [sys.executable, script, marker], [5]), "hi", seams
            )
            self.assertLess(time.monotonic() - started, rd._DRAIN_S + 5)
            self.assertTrue(any("stderr still open" in line for line in lines))
            for _attempt in range(50):
                if os.path.exists(pid_file):
                    break
                time.sleep(0.05)
            if os.path.exists(pid_file):
                with open(pid_file, encoding="utf-8") as handle:
                    self.record(int(handle.read().strip()))

    def test_wedged_runner_recorded_group_killed(self):
        marker = _marker()
        with tempfile.TemporaryDirectory() as tmp:
            runner = os.path.join(tmp, "fake-runner.py")
            _write_script(runner, f"""
                import signal, subprocess, sys, time
                signal.signal(signal.SIGTERM, signal.SIG_IGN)
                flag = sys.argv[sys.argv.index("--child-pgid-file") + 1]
                proc = subprocess.Popen(
                    [sys.executable, "-c", "import time; time.sleep(60)", "{marker}"],
                    start_new_session=True)
                with open(flag, "a", encoding="utf-8") as handle:
                    handle.write(f"spawn {{proc.pid}}\\n")
                time.sleep(60)
            """)
            seams = RunnerSeams(
                which_fn=lambda name: sys.executable if name == "node" else None,
                runner_path_fn=lambda: runner,
            )
            with (
                mock.patch.object(rd, "RUNNER_OUTER_MARGIN_S", 0),
                mock.patch.object(rd, "_KILL_GRACE_S", 0),
                mock.patch.object(rd, "_TERM_GRACE_S", 1),
            ):
                result = run_runner(_spec(timeout_s=1), "hi", seams)
            self.assertTrue(result.timed_out)
            self.assertEqual(result.reason, "timeout")
            self.assertFalse(self.marker_alive(marker))

    def test_recorded_group_validation(self):
        own = os.getpgrp()
        with tempfile.TemporaryDirectory() as tmp:
            pgid_file = os.path.join(tmp, "child-pgids")
            with open(pgid_file, "w", encoding="utf-8") as handle:
                handle.write(
                    f"spawn 1\nspawn 0\nspawn -5\nspawn abc\nspawn {own}\n"
                    "spawn 4242\nexit 4242\nspawn 5151\nnot a line\n"
                )
            kills: list[tuple[int, int]] = []

            def kill_fn(pgid, sig):
                kills.append((pgid, sig))
                if sig == 0:
                    raise ProcessLookupError

            seams = RunnerSeams(kill_fn=kill_fn, sleep_fn=lambda _seconds: None)
            rd._kill_recorded_groups(pgid_file, seams)
            sent = [(pgid, sig) for pgid, sig in kills if sig != 0]
            self.assertEqual(sent, [(5151, signal.SIGTERM), (5151, signal.SIGKILL)])


class TestRunCustomCommand(_ChildTracker):
    def test_tier_escalation(self):
        marker = _marker()
        with tempfile.TemporaryDirectory() as tmp:
            stamp = os.path.join(tmp, "stamp")
            script = os.path.join(tmp, "child.py")
            _write_script(script, f"""
                import os, sys, time
                if not os.path.exists({stamp!r}):
                    open({stamp!r}, "w").close()
                    time.sleep(3)
                sys.exit(0)
            """)
            lines: list[str] = []
            seams = RunnerSeams(print_fn=lines.append)
            result = run_custom_command(
                CustomSpec("k", [sys.executable, script, marker], [1, 5]), "hi", seams
            )
            self.assertEqual(result.returncode, 0)
            self.assertIsNone(result.reason)
            self.assertTrue(any("escalating to tier 2" in line for line in lines))
            self.assertFalse(self.marker_alive(marker))

    def test_exit_3_is_real_error(self):
        result = run_custom_command(
            CustomSpec("k", [sys.executable, "-c", "import sys; sys.exit(3)"], [5]), "hi"
        )
        self.assertEqual(result.reason, "real_error")

    def test_quota_and_auth_from_stderr(self):
        quota = run_custom_command(CustomSpec("k", [
            sys.executable, "-c",
            "import sys; sys.stderr.write('quota exceeded\\n'); sys.exit(1)",
        ], [5]), "hi")
        self.assertEqual(quota.reason, "quota")
        auth = run_custom_command(CustomSpec("k", [
            sys.executable, "-c",
            "import sys; sys.stderr.write('401 unauthorized\\n'); sys.exit(1)",
        ], [5]), "hi")
        self.assertEqual(auth.reason, "auth")

    def test_argument_too_large_is_configuration(self):
        def popen(_argv, **_kwargs):
            raise OSError(errno.E2BIG, "Argument list too long")

        lines: list[str] = []
        result = run_custom_command(
            CustomSpec("k", ["mycli", "x" * 10], [30]), "p", _seams(popen, lines, []))
        self.assertEqual(result.reason, "configuration")
        self.assertTrue(any("prompt too large" in line for line in lines))

    def test_missing_executable(self):
        result = run_custom_command(
            CustomSpec("k", ["/no/such/command-aikit", _marker()], [5]), "hi"
        )
        self.assertEqual(result.reason, "dispatch_unavailable")

    def test_sigterm_ignored_then_sigkill(self):
        marker = _marker()
        result = run_custom_command(CustomSpec("k", [
            sys.executable, "-c",
            "import signal,time; signal.signal(signal.SIGTERM, signal.SIG_IGN); time.sleep(60)",
            marker,
        ], [1]), "hi")
        self.assertIsNotNone(result.returncode)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.marker_alive(marker))

    def test_child_env_scrubs_host_signals(self):
        marker = _marker()
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "env.txt")
            script = (
                "import os,sys; open(sys.argv[1],'w').write('\\n'.join(sorted(os.environ)))"
            )
            env = {name: "1" for name in HOST_SIGNAL_ENV_VARS}
            env["PATH"] = os.environ.get("PATH", "")
            seams = RunnerSeams(env_fn=lambda: dict(env))
            run_custom_command(CustomSpec("k", [
                sys.executable, "-c", script, out, marker,
            ], [5]), "hi", seams)
            with open(out, encoding="utf-8") as handle:
                child_names = set(handle.read().splitlines())
            self.assertTrue(HOST_SIGNAL_ENV_VARS.isdisjoint(child_names))


def _runner_result(stdout="### Status: Approved\n", returncode=0, reason=None,
                   status="ok", argv=None):
    return rd.RunnerResult(
        returncode, stdout, {"status": status} if status else None, reason, False,
        argv if argv is not None else ["node", "runner"], "",
    )


class TestDispatchReviewerRunner(unittest.TestCase):
    """dispatch-reviewer runs a table runtime through the runner and a custom entry
    through the launcher (D-11, D-21)."""

    def setUp(self):
        # dispatch-reviewer's default codegraph health check would run `<cli> mcp list` for real.
        skip = detection.CodegraphProbe(False, False, None, "skip")
        patcher = mock.patch.object(detection, "probe_codegraph", return_value=skip)
        patcher.start()
        self.addCleanup(patcher.stop)

    def _reviewers(self, tmp, entries, name="reviewers.json"):
        path = os.path.join(tmp, name)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(entries, handle)
        prompt = os.path.join(tmp, "prompt.txt")
        with open(prompt, "w", encoding="utf-8") as handle:
            handle.write("review this")
        return path, prompt

    def _argv(self, reviewers, prompt, extra=None):
        argv = ["dispatch-reviewer", "--reviewers-json", reviewers, "--index", "0",
                "--prompt-file", prompt, "--timeout-tiers", "600,1200"]
        return argv + (extra or [])

    def test_runtime_entry_reaches_the_runner_with_its_tiers(self):
        seen = {}

        def fake_tiers(spec, tiers, prompt, seams):
            seen["spec"] = spec
            seen["tiers"] = tiers
            seen["prompt"] = prompt
            return _runner_result(
                reason="quota", status="quota", argv=["node", "cross-ai.mjs"],
            )

        with tempfile.TemporaryDirectory() as tmp:
            reviewers, prompt = self._reviewers(tmp, [{
                "key": "oc", "runtime": "opencode", "model": "x/y",
                "extra": {"effort": "high"}, "route": "subprocess",
            }])
            out, err = io.StringIO(), io.StringIO()
            with redirect_stdout(out), redirect_stderr(err):
                code = main(
                    self._argv(reviewers, prompt),
                    dispatch_reviewer_fn=reviewer_dispatch.dispatch_reviewer,
                    runner_tiers_fn=fake_tiers,
                )
        self.assertEqual(code, 0, err.getvalue())
        spec = seen["spec"]
        self.assertEqual(spec.runtime, "opencode")
        self.assertEqual(spec.model, "x/y")
        self.assertEqual(spec.mode, "review")
        self.assertEqual(spec.timeout_s, 600)
        self.assertIsNone(spec.cwd)
        self.assertEqual(seen["tiers"], [600, 1200])
        self.assertIn("review this", seen["prompt"])
        body = json.loads(out.getvalue())
        self.assertEqual(body["reason"], "quota")
        self.assertEqual(body["status"]["status"], "quota")
        self.assertEqual(body["argv"], ["node", "cross-ai.mjs"])
        self.assertIn("stdout", body)
        self.assertIn("returncode", body)
        self.assertIn("timed_out", body)

    def test_stdout_only_prints_the_report_and_exits_with_the_runner_code(self):
        def fake_tiers(spec, tiers, prompt, seams):
            del spec, tiers, prompt, seams
            return _runner_result(stdout="### Status: Approved\n", returncode=7)

        with tempfile.TemporaryDirectory() as tmp:
            reviewers, prompt = self._reviewers(tmp, [{
                "key": "oc", "runtime": "opencode", "model": "x/y", "route": "subprocess",
            }])
            out, err = io.StringIO(), io.StringIO()
            with redirect_stdout(out), redirect_stderr(err):
                code = main(
                    self._argv(reviewers, prompt, ["--stdout-only"]),
                    runner_tiers_fn=fake_tiers,
                )
        self.assertEqual(code, 7)
        self.assertEqual(out.getvalue(), "### Status: Approved\n")

    def test_native_route_exits_1_and_spawns_nothing(self):
        spawned = []

        def fake_tiers(*_args):
            spawned.append("runner")
            raise AssertionError("a native route must not reach the runner")

        def fake_custom(*_args):
            spawned.append("custom")
            raise AssertionError("a native route must not reach the launcher")

        with tempfile.TemporaryDirectory() as tmp:
            reviewers, prompt = self._reviewers(tmp, [{
                "key": "host", "runtime": "claude", "model": "opus", "route": "native",
            }])
            err = io.StringIO()
            with redirect_stdout(io.StringIO()), redirect_stderr(err):
                code = main(
                    self._argv(reviewers, prompt),
                    runner_tiers_fn=fake_tiers, custom_fn=fake_custom,
                )
        self.assertEqual(code, 1)
        self.assertIn("dispatch-reviewer: reviewer host routes native", err.getvalue())
        self.assertEqual(spawned, [])

    def test_render_command_shows_the_entry_first_tier_and_knobs(self):
        with tempfile.TemporaryDirectory() as tmp:
            reviewers, prompt = self._reviewers(tmp, [{
                "key": "cx", "runtime": "codex", "model": "gpt",
                "extra": {"timeout_tiers": [900, 1800], "effort": "high"},
            }])
            out = io.StringIO()
            with redirect_stdout(out), redirect_stderr(io.StringIO()):
                code = main(["render-command", "--reviewers-json", reviewers, "--index", "0",
                             "--prompt-file", prompt], which_fn=lambda _name: None)
        self.assertEqual(code, 0)
        argv = json.loads(out.getvalue())
        self.assertEqual(argv[argv.index("--timeout") + 1], "900")
        self.assertEqual(argv[argv.index("--codex-effort") + 1], "high")

    def test_skip_route_and_model_less_entry_raise_and_spawn_nothing(self):
        def never(*_args):
            raise AssertionError("a refused entry must not reach a spawn")

        seams = reviewer_dispatch.ReviewerSeams(
            runner_tiers_fn=never, custom_fn=never,
            build_tooling_guidance_fn=lambda *_a, **_kw: "",
            resolve_shared_reference_fn=lambda: None, codegraph_health_fn=lambda _rt: False,
        )
        entries = (
            {"key": "oc", "runtime": "opencode", "model": "x/y", "route": "bad_model"},
            {"key": "oc", "runtime": "opencode", "route": "subprocess"},
        )
        for entry in entries:
            with self.subTest(entry=entry), self.assertRaises(ValueError):
                reviewer_dispatch.dispatch_reviewer(
                    reviewer_dispatch.ReviewerDispatchSpec(entry, "p", [600], {}), seams)

    def test_cwd_flag_reaches_both_specs_and_never_changes_the_process_cwd(self):
        seen = {}

        def fake_tiers(spec, tiers, prompt, seams):
            del tiers, prompt, seams
            seen.setdefault("runner", []).append(spec.cwd)
            return _runner_result()

        def fake_custom(spec, prompt, seams):
            del prompt, seams
            seen["custom"] = spec.cwd
            return _runner_result()

        before = os.getcwd()
        with tempfile.TemporaryDirectory() as tmp:
            scratch = os.path.join(tmp, "scratch")
            os.makedirs(scratch)
            runtime, prompt = self._reviewers(tmp, [{
                "key": "oc", "runtime": "opencode", "model": "x/y", "route": "subprocess",
            }], "runtime.json")
            custom, _prompt = self._reviewers(tmp, [{
                "key": "mine", "command": "mycli --model {model}", "model": "m",
            }], "custom.json")
            seams = {"runner_tiers_fn": fake_tiers, "custom_fn": fake_custom}
            err = io.StringIO()
            with redirect_stdout(io.StringIO()), redirect_stderr(err):
                code = main(self._argv(runtime, prompt, ["--cwd", scratch]), **seams)
                self.assertEqual(code, 0, err.getvalue())
                self.assertEqual(
                    main(self._argv(custom, prompt, ["--cwd", scratch]), **seams), 0)
                self.assertEqual(main(self._argv(runtime, prompt), **seams), 0)
        self.assertEqual(seen["runner"], [scratch, None])
        self.assertEqual(seen["custom"], scratch)
        self.assertEqual(os.getcwd(), before)

    def test_without_cwd_both_specs_carry_none(self):
        seen = {}

        def fake_tiers(spec, tiers, prompt, seams):
            del tiers, prompt, seams
            seen["runner"] = spec.cwd
            return _runner_result()

        def fake_custom(spec, prompt, seams):
            del prompt, seams
            seen["custom"] = spec.cwd
            return _runner_result()

        before = os.getcwd()
        with tempfile.TemporaryDirectory() as tmp:
            runtime, prompt = self._reviewers(tmp, [{
                "key": "oc", "runtime": "opencode", "model": "x/y", "route": "subprocess",
            }], "runtime.json")
            custom, _prompt = self._reviewers(tmp, [{
                "key": "mine", "command": "mycli --model {model}", "model": "m",
            }], "custom.json")
            seams = {"runner_tiers_fn": fake_tiers, "custom_fn": fake_custom}
            err = io.StringIO()
            with redirect_stdout(io.StringIO()), redirect_stderr(err):
                code = main(self._argv(runtime, prompt), **seams)
            self.assertEqual(code, 0, err.getvalue())
            with redirect_stdout(io.StringIO()), redirect_stderr(err):
                main(self._argv(custom, prompt), **seams)
        self.assertIsNone(seen["runner"])
        self.assertIsNone(seen["custom"])
        self.assertEqual(os.getcwd(), before)


if __name__ == "__main__":
    unittest.main()
