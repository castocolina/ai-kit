"""Pane end to end: open, one real round through the launcher loop, verdict, close."""

import contextlib
import io
import json
import os
import shlex
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

_REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(_REPO_ROOT, "skills", "ai-kit-spec-review"))
sys.path.insert(0, os.path.dirname(__file__))

from ai_kit_spec import herdr_pane, runner_dispatch
from ai_kit_spec.cache import cache_read_json
from ai_kit_spec.detection import HOST_SIGNAL_ENV_VARS
from herdr_fakes import herdr_calls, write_herdr_fake

_FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "runner_host_protocol.json")
_TOKEN = "0123456789ab"
_TAB_ANSWER = '{"result":{"tab":{"tab_id":"t1"},"root_pane":{"pane_id":"p1"}}}'


class TestPaneTracer(unittest.TestCase):
    """A fake herdr run seam, a real launcher under /bin/sh, the real clock and pid checks."""

    def setUp(self):
        for path in herdr_pane.PANE_TOOLS:
            if not os.access(path, os.X_OK):
                self.skipTest(f"needs {path}")
        if not os.path.exists("/proc/self/stat"):
            self.skipTest("needs /proc/<pid>/stat")
        self.tmp = tempfile.mkdtemp(prefix="herdr-pane-")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        if herdr_pane.PATH_SAFE_RE.fullmatch(self.tmp) is None:
            self.skipTest("temp path holds a character the typed line refuses")
        self.env = {
            "HERDR_ENV": "1",
            "PATH": "/usr/bin:/bin",
            "XDG_STATE_HOME": os.path.join(self.tmp, "state"),
            "HOME": self.tmp,
        }
        self.run_dir = os.path.join(self.tmp, "state", "ai-kit", "spec", "host", _TOKEN)
        self.calls = []
        self.label = f"aikit:execute:placeholder-cli-1:{_TOKEN}"
        self.launcher_proc: subprocess.Popen | None = None
        self.addCleanup(self._stop_launcher)
        self.seams = herdr_pane.PaneSeams(
            run_fn=self._fake_herdr,
            which_fn=lambda name, path=None: "fake-herdr",
            token_fn=lambda: _TOKEN,
        )

    def _fake_herdr(self, argv, **kwargs):
        """Record every argv and answer each verb; pane run starts the typed launcher."""
        self.calls.append(argv)
        verb = " ".join(argv[1:3])
        if verb == "tab create":
            return subprocess.CompletedProcess(argv, 0, _TAB_ANSWER, "")
        if verb == "pane run":
            typed = argv[-1]
            assert typed.startswith("sh "), f"typed line is not sh <launcher>: {typed}"
            self.launcher_proc = subprocess.Popen(
                ["/bin/sh", typed[3:]], stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return subprocess.CompletedProcess(argv, 0, "", "")
        if verb == "tab list":
            return subprocess.CompletedProcess(argv, 0, json.dumps(
                {"result": {"tabs": [{"tab_id": "t1", "label": self.label}]}}), "")
        if verb == "tab close":
            return subprocess.CompletedProcess(argv, 0, "", "")
        raise AssertionError(f"unexpected herdr call: {argv}")

    def _stop_launcher(self):
        """Kill the launcher's whole process group so no pane shell outlives the test."""
        try:
            with open(os.path.join(self.run_dir, "pid"), encoding="utf-8") as handle:
                text = handle.read()
        except OSError:
            text = ""
        pid = int(text) if text.strip().isdigit() else None
        if pid is not None and herdr_pane.pid_alive(pid):
            with contextlib.suppress(ProcessLookupError):
                os.killpg(pid, signal.SIGKILL)
        if self.launcher_proc is not None:
            self.launcher_proc.wait(timeout=10)

    def _open_pane(self) -> dict:
        pane = herdr_pane.open_pane("execute", "placeholder-cli-1", self.tmp, self.env,
                                    self.seams)
        assert pane is not None
        return pane

    def test_open_pane_records_the_hosted_lane(self):
        pane = self._open_pane()
        self.assertEqual(pane, {"token": _TOKEN, "tab_id": "t1", "pane_id": "p1",
                               "run_dir": self.run_dir})
        record = cache_read_json(os.path.join(self.run_dir, "run.json"))
        assert record is not None
        self.assertEqual(record["tab_id"], "t1")
        self.assertEqual(record["pane_id"], "p1")
        self.assertIsInstance(record["launcher_pid"], int)
        self.assertIsInstance(record["launcher_pgid"], int)
        self.assertEqual(record["launcher_pgid"], record["launcher_pid"])
        self.assertEqual(record["role"], "execute")
        self.assertEqual(record["runtime"], "placeholder-cli-1")
        self.assertEqual(record["label"], f"aikit:execute:placeholder-cli-1:{_TOKEN}")
        with open(_FIXTURE, encoding="utf-8") as handle:
            fixture = json.load(handle)
        self.assertEqual(sorted(record), sorted(fixture["run_record_fields"]))
        self.assertEqual(record["version"], 1)

    def test_module_mirrors_the_protocol_fixture(self):
        with open(_FIXTURE, encoding="utf-8") as handle:
            fixture = json.load(handle)
        self.assertEqual(herdr_pane.PANE_VERBS, tuple(fixture["herdr_verbs"]))
        self.assertEqual(herdr_pane.HOST_FILES, fixture["files"])
        self.assertEqual(herdr_pane.LABEL_PREFIX, fixture["label"]["prefix"])
        self.assertEqual(herdr_pane.LABEL_MAX, fixture["label"]["max_length"])
        self.assertEqual(herdr_pane.LABEL_RE.pattern, fixture["label"]["pattern"])
        self.assertEqual(herdr_pane.TOKEN_RE.pattern, fixture["token_pattern"])
        self.assertEqual(herdr_pane.RC_RE.pattern, fixture["rc_pattern"])
        self.assertEqual(herdr_pane.DIR_MODE, int(fixture["dir_mode"], 8))
        self.assertEqual(herdr_pane.FILE_MODE, int(fixture["file_mode"], 8))
        self.assertEqual(herdr_pane.typed_line("/s/host/ab/launch.sh"),
                         fixture["typed_line"].replace("<launcher path>", "/s/host/ab/launch.sh"))
        self.assertEqual(
            herdr_pane.run_dir_for({"XDG_STATE_HOME": "/s"}, "ab"),
            fixture["run_dir"].replace("<state home>", "/s").replace("<token>", "ab"),
        )
        self.assertIn(fixture["verdict"], herdr_pane.ROUND_ENDS)
        launcher = herdr_pane.launcher_text("/s/host/ab", "ab")
        done = fixture["done_line"].replace("<token>", "%s").replace("<rc>", "%s")
        self.assertIn("printf '" + done + "\\n'", launcher)

    def test_run_round_reads_the_verdict_from_the_round_files(self):
        pane = self._open_pane()
        job = herdr_pane.PaneRound(
            argv=["/bin/sh", "-c",
                  'IFS= read -r l; printf \'%s|%s\' "$l" "$AIKIT_T1"; '
                  'printf \'AIKIT-XAI status=ok session=fake-sid-1\\n\' >&2; exit 3'],
            prompt="prompt-line\n",
            cwd=self.tmp,
            timeout_s=30,
            env={"PATH": "/usr/bin:/bin", "AIKIT_T1": "from-env"},
        )
        self.assertEqual(herdr_pane.run_round(pane, job, self.seams), "rc")
        verdict = herdr_pane.read_verdict(pane["run_dir"])
        assert verdict is not None
        self.assertEqual(verdict["code"], 3)
        self.assertIsNone(verdict["signal"])
        self.assertIsNone(verdict["bad"])
        self.assertEqual(verdict["out"], "prompt-line|from-env")
        self.assertEqual(verdict["status"], {"status": "ok", "session": "fake-sid-1"})
        for name in ("env", "prompt", "round.run"):
            self.assertFalse(os.path.exists(os.path.join(pane["run_dir"], name)),
                             f"{name} should be gone after the round")

    def test_second_round_reuses_the_tab(self):
        pane = self._open_pane()
        job = herdr_pane.PaneRound(argv=["/bin/sh", "-c", "exit 0"], prompt="",
                                   cwd=self.tmp, timeout_s=30)
        self.assertEqual(herdr_pane.run_round(pane, job, self.seams), "rc")
        self.assertEqual(herdr_pane.run_round(pane, job, self.seams), "rc")
        creates = [argv for argv in self.calls if argv[1:3] == ["tab", "create"]]
        self.assertEqual(1, len(creates))

    def test_close_pane_closes_the_tab_and_ends_the_loop(self):
        pane = self._open_pane()
        record = cache_read_json(os.path.join(self.run_dir, "run.json"))
        assert record is not None
        launcher_pid = record["launcher_pid"]
        self.assertTrue(herdr_pane.close_pane(pane, self.env, self.seams))
        self.assertFalse(os.path.exists(self.run_dir))
        self.assertIn(["fake-herdr", "tab", "close", "t1"], self.calls)
        end = time.monotonic() + 5
        while herdr_pane.pid_alive(launcher_pid) and time.monotonic() < end:
            time.sleep(0.05)
        self.assertFalse(herdr_pane.pid_alive(launcher_pid))


class _PaneFakeHarness(unittest.TestCase):
    """The fake clock, fake herdr answers, recording kill seam and fake open shared by
    the pane suites. No test methods live here: TestPaneEdges and TestPaneBoundary inherit
    it, so none of its helpers ever runs twice."""

    tmp_prefix = "herdr-pane-edges-"

    def setUp(self):
        for path in herdr_pane.PANE_TOOLS:
            if not os.access(path, os.X_OK):
                self.skipTest(f"needs {path}")
        if not os.path.exists("/proc/self/stat"):
            self.skipTest("needs /proc/<pid>/stat")
        self.tmp = tempfile.mkdtemp(prefix=self.tmp_prefix)
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        if herdr_pane.PATH_SAFE_RE.fullmatch(self.tmp) is None:
            self.skipTest("temp path holds a character the typed line refuses")
        self.env = {
            "HERDR_ENV": "1",
            "PATH": "/usr/bin:/bin",
            "XDG_STATE_HOME": os.path.join(self.tmp, "state"),
            "HOME": self.tmp,
        }
        self.run_dir = os.path.join(self.tmp, "state", "ai-kit", "spec", "host", _TOKEN)
        self.label = f"aikit:execute:placeholder-cli-1:{_TOKEN}"
        self.now = 0.0
        self.on_sleep = None
        self.alive = True
        self.kills = []
        self.kill_clock: float | None = None
        self.calls = []
        self.round_text = ""
        self.answers = {
            "tab create": (0, _TAB_ANSWER, ""),
            "pane run": (0, "", ""),
            "tab list": (
                0, json.dumps({"result": {"tabs": [{"tab_id": "t1", "label": self.label}]}}),
                ""),
            "tab close": (0, "", ""),
        }

        def _time():
            return self.now

        def _sleep(seconds):
            self.now += seconds
            if self.on_sleep is not None:
                self.on_sleep()

        self.clock_time = _time
        self.clock_sleep = _sleep
        self.seams = herdr_pane.PaneSeams(
            run_fn=self._fake_herdr,
            which_fn=lambda name, path=None: "fake-herdr",
            time_fn=_time,
            sleep_fn=_sleep,
            token_fn=lambda: _TOKEN,
            alive_fn=lambda pid: self.alive,
            killpg_fn=self._killpg,
            start_fn=lambda pid: "777",
        )

    def _fake_herdr(self, argv, **kwargs):
        """Record the argv and answer from the per-test table; nothing is ever started."""
        self.calls.append(list(argv))
        verb = " ".join(argv[1:3])
        if verb not in self.answers:
            raise AssertionError(f"unexpected herdr call: {argv}")
        code, stdout, stderr = self.answers[verb]
        return subprocess.CompletedProcess(argv, code, stdout, stderr)

    def _killpg(self, pgid, sig):
        """Record every signal so the targets and their order can be asserted."""
        self.kills.append((pgid, sig))
        self.calls.append(["killpg", sig])
        if len(self.kills) == 1:
            self.kill_clock = self.now

    def _steps(self):
        """Every recorded call as a short token: the herdr verb or a killpg signal."""
        steps = []
        for entry in self.calls:
            if entry[0] == "killpg":
                steps.append(f"killpg {signal.Signals(entry[1]).name}")
            else:
                steps.append(" ".join(entry[1:3]))
        return steps

    def _open(self) -> dict:
        """A pane whose run.json names a fake group: every signal goes to the recorder."""

        def write_pid():
            with open(os.path.join(self.run_dir, "pid"), "w", encoding="utf-8") as handle:
                handle.write(f"{os.getpid()}\n")

        self.on_sleep = write_pid
        pane = herdr_pane.open_pane("execute", "placeholder-cli-1", self.tmp, self.env,
                                    self.seams)
        self.on_sleep = None
        self.assertIsNotNone(pane)
        assert pane is not None
        record = herdr_pane._read_run_record(pane["run_dir"])
        self.assertIsNotNone(record)
        assert record is not None
        record["launcher_pid"] = 424242
        record["launcher_pgid"] = 424242
        record["launcher_start"] = "777"
        herdr_pane._write_record(pane["run_dir"], record)
        return pane

    def _play_the_round(self):
        """The fake sleep plays the launcher: its first call ends the round with rc 0."""
        fired = []

        def on_sleep():
            if fired:
                return
            fired.append(True)
            os.unlink(os.path.join(self.run_dir, herdr_pane.ROUND_FILE))
            with open(os.path.join(self.run_dir, "out"), "w", encoding="utf-8") as handle:
                handle.write("round-out\n")
            with open(os.path.join(self.run_dir, "err"), "w", encoding="utf-8") as handle:
                handle.write("AIKIT-XAI status=ok session=fake-sid-2\n")
            with open(os.path.join(self.run_dir, "rc"), "w", encoding="utf-8") as handle:
                handle.write("0\n")

        self.on_sleep = on_sleep


class TestPaneEdges(_PaneFakeHarness, unittest.TestCase):
    """A fake clock and a recording kill seam: abandonment, ownership and refusal edges."""

    def test_timeout_retires_the_verified_group(self):
        pane = self._open()
        self.alive = True
        job = herdr_pane.PaneRound(["/bin/true"], "", self.tmp, 3)
        self.assertEqual(herdr_pane.run_round(pane, job, self.seams), "timeout")
        self.assertEqual(self.kills[0], (424242, signal.SIGTERM))
        self.assertEqual(self.kills[-1], (424242, signal.SIGKILL))
        self.assertIs(pane["closed"], True)
        for name in (herdr_pane.ROUND_FILE, "env", "prompt"):
            self.assertFalse(os.path.exists(os.path.join(pane["run_dir"], name)))

    def test_start_mismatch_leaves_the_group_alone(self):
        pane = self._open()
        self.seams = self.seams._replace(start_fn=lambda pid: "999")
        job = herdr_pane.PaneRound(["/bin/true"], "", self.tmp, 3)
        self.assertEqual(herdr_pane.run_round(pane, job, self.seams), "timeout")
        self.assertEqual(self.kills, [])
        self.assertIs(pane["closed"], True)

    def test_closed_pane_starts_nothing(self):
        pane = self._open()
        pane["closed"] = True
        job = herdr_pane.PaneRound(["/bin/true"], "", self.tmp, 3)
        self.assertEqual(herdr_pane.run_round(pane, job, self.seams), "launcher gone")
        for name in (herdr_pane.ROUND_FILE, "env", "prompt"):
            self.assertFalse(os.path.exists(os.path.join(pane["run_dir"], name)))

    def test_stale_rc_is_not_accepted_while_round_sh_exists(self):
        pane = self._open()
        fired = []

        def on_sleep():
            if fired:
                return
            fired.append(True)
            with open(os.path.join(pane["run_dir"], "rc"), "w", encoding="utf-8") as handle:
                handle.write("0\n")

        self.on_sleep = on_sleep
        job = herdr_pane.PaneRound(["/bin/true"], "", self.tmp, 2)
        self.assertEqual(herdr_pane.run_round(pane, job, self.seams), "timeout")

    def test_round_command_line_is_the_quoted_argv(self):
        pane = self._open()
        fired = []

        def on_sleep():
            if fired:
                return
            fired.append(True)
            round_path = os.path.join(pane["run_dir"], herdr_pane.ROUND_FILE)
            with open(round_path, encoding="utf-8") as handle:
                self.round_text = handle.read()
            os.unlink(round_path)
            with open(os.path.join(pane["run_dir"], "rc"), "w", encoding="utf-8") as handle:
                handle.write("0\n")

        self.on_sleep = on_sleep
        job = herdr_pane.PaneRound(["/bin/echo", "a b", "--x"], "", self.tmp, 5)
        self.assertEqual(herdr_pane.run_round(pane, job, self.seams), "rc")
        last_line = self.round_text.rstrip("\n").split("\n")[-1]
        self.assertTrue(last_line.endswith("/bin/echo 'a b' --x <&3 3<&-"),
                        f"round line does not run the quoted argv: {last_line}")

    def test_err_tail_keeps_the_last_characters(self):
        pane = self._open()
        err = "x" * 3000 + "\nAIKIT-XAI status=ok session=fake-sid-2\n"
        with open(os.path.join(pane["run_dir"], "err"), "w", encoding="utf-8") as handle:
            handle.write(err)
        with open(os.path.join(pane["run_dir"], "rc"), "w", encoding="utf-8") as handle:
            handle.write("0\n")
        verdict = herdr_pane.read_verdict(pane["run_dir"])
        assert verdict is not None
        self.assertEqual(verdict["err_tail"], err[-herdr_pane.STDERR_TAIL_CHARS:])
        self.assertEqual(verdict["status"]["session"], "fake-sid-2")
        os.unlink(os.path.join(pane["run_dir"], "err"))
        verdict = herdr_pane.read_verdict(pane["run_dir"])
        assert verdict is not None
        self.assertEqual(verdict["err_tail"], "")

    def test_close_retires_the_group_before_tab_close(self):
        pane = self._open()
        self.assertTrue(herdr_pane.close_pane(pane, self.env, self.seams))
        self.assertFalse(os.path.exists(pane["run_dir"]))
        steps = self._steps()
        self.assertLess(steps.index("tab list"), steps.index("killpg SIGTERM"))
        self.assertLess(steps.index("killpg SIGTERM"), steps.index("tab close"))
        self.assertEqual(self.kills[0], (424242, signal.SIGTERM))

    def test_close_without_herdr_keeps_only_the_record(self):
        pane = self._open()
        self.seams = self.seams._replace(which_fn=lambda name, path=None: None)
        self.assertFalse(herdr_pane.close_pane(pane, self.env, self.seams))
        self.assertEqual(os.listdir(pane["run_dir"]), ["run.json"])
        self.assertEqual(self.kills, [])

    def test_close_accepts_tab_not_found(self):
        pane = self._open()
        self.answers["tab close"] = (1, "", '{"error":{"code":"tab_not_found"}}')
        self.assertTrue(herdr_pane.close_pane(pane, self.env, self.seams))
        self.assertFalse(os.path.exists(pane["run_dir"]))

    def test_close_with_a_run_dir_outside_the_state_home(self):
        pane = self._open()
        other = os.path.join(self.tmp, "other", "ai-kit", "spec", "host", _TOKEN)
        os.makedirs(other)
        record = herdr_pane._read_run_record(pane["run_dir"])
        assert record is not None
        herdr_pane._write_record(other, record)
        moved = dict(pane)
        moved["run_dir"] = other
        self.assertFalse(herdr_pane.close_pane(moved, self.env, self.seams))
        self.assertTrue(os.path.exists(other))
        self.assertTrue(os.path.exists(pane["run_dir"]))
        self.assertNotIn(["fake-herdr", "tab", "close", "t1"], self.calls)
        self.assertEqual(self.kills, [])

    def test_close_with_a_record_mismatch_keeps_the_record(self):
        cases = {
            "token": "ba9876543210",
            "label": f"aikit:execute:placeholder-cli-2:{_TOKEN}",
            "host_name": "other-host",
        }
        for field, value in cases.items():
            with self.subTest(field=field):
                shutil.rmtree(self.run_dir, ignore_errors=True)
                pane = self._open()
                record = herdr_pane._read_run_record(pane["run_dir"])
                assert record is not None
                record[field] = value
                herdr_pane._write_record(pane["run_dir"], record)
                self.assertFalse(herdr_pane.close_pane(pane, self.env, self.seams))
                self.assertNotIn(["fake-herdr", "tab", "close", "t1"], self.calls)
                self.assertTrue(os.path.exists(os.path.join(pane["run_dir"], "run.json")))
                self.assertEqual(self.kills, [])

    def test_close_with_an_unproven_tab_keeps_the_record(self):
        cases = {
            "other label": [{"tab_id": "t1",
                             "label": f"aikit:execute:placeholder-cli-2:{_TOKEN}"}],
            "no t1": [{"tab_id": "t2", "label": self.label}],
        }
        for name, tabs in cases.items():
            with self.subTest(case=name):
                shutil.rmtree(self.run_dir, ignore_errors=True)
                pane = self._open()
                self.answers["tab list"] = (
                    0, json.dumps({"result": {"tabs": tabs}}), "")
                self.assertFalse(herdr_pane.close_pane(pane, self.env, self.seams))
                self.assertNotIn(["fake-herdr", "tab", "close", "t1"], self.calls)
                self.assertEqual(os.listdir(pane["run_dir"]), ["run.json"])
                self.assertEqual(self.kills, [])

    def test_close_with_a_symlinked_run_dir(self):
        pane = self._open()
        real = os.path.join(self.tmp, "real")
        os.rename(pane["run_dir"], real)
        os.symlink(real, pane["run_dir"])
        self.assertFalse(herdr_pane.close_pane(pane, self.env, self.seams))
        self.assertTrue(os.path.exists(os.path.join(real, "run.json")))
        self.assertEqual(self.kills, [])

    def test_close_with_a_symlinked_run_record(self):
        pane = self._open()
        record = herdr_pane._read_run_record(pane["run_dir"])
        assert record is not None
        elsewhere = os.path.join(self.tmp, "elsewhere.json")
        with open(elsewhere, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(record))
        os.unlink(os.path.join(pane["run_dir"], "run.json"))
        os.symlink(elsewhere, os.path.join(pane["run_dir"], "run.json"))
        self.assertFalse(herdr_pane.close_pane(pane, self.env, self.seams))
        self.assertTrue(os.path.exists(os.path.join(
            pane["run_dir"], herdr_pane.HOST_FILES["launcher"])))
        self.assertTrue(os.path.exists(elsewhere))
        self.assertEqual(self.kills, [])

    def test_close_with_an_oversized_run_record(self):
        pane = self._open()
        record = herdr_pane._read_run_record(pane["run_dir"])
        assert record is not None
        record["padding"] = "p" * (herdr_pane.RUN_RECORD_MAX_BYTES + 100)
        herdr_pane._write_record(pane["run_dir"], record)
        self.assertFalse(herdr_pane.close_pane(pane, self.env, self.seams))
        self.assertTrue(os.path.exists(os.path.join(
            pane["run_dir"], herdr_pane.HOST_FILES["launcher"])))
        self.assertEqual(self.kills, [])

    def test_tab_create_failure_through_the_real_fake_binary(self):
        bin_dir = os.path.join(self.tmp, "bin")
        log_path = os.path.join(self.tmp, "herdr.log")
        write_herdr_fake(bin_dir, {}, log_path)
        env = dict(self.env)
        env["PATH"] = bin_dir
        seams = self.seams._replace(run_fn=subprocess.run, which_fn=shutil.which)
        with contextlib.redirect_stderr(io.StringIO()):
            pane = herdr_pane.open_pane("review", "placeholder-cli-1", self.tmp, env, seams)
        self.assertIsNone(pane)
        self.assertFalse(os.path.exists(self.run_dir))
        self.assertEqual(herdr_calls(log_path), [
            ["tab", "create", "--label", "aikit:review:placeholder-cli-1:0123456789ab",
             "--no-focus", "--cwd", self.tmp]])

    def test_tab_create_answer_not_json_keeps_only_the_record(self):
        self.answers["tab create"] = (0, "not json", "")
        with contextlib.redirect_stderr(io.StringIO()):
            pane = herdr_pane.open_pane("execute", "placeholder-cli-1", self.tmp,
                                       self.env, self.seams)
        self.assertIsNone(pane)
        self.assertEqual(os.listdir(self.run_dir), ["run.json"])

    def test_no_pid_within_the_grace_closes_the_tab(self):
        with contextlib.redirect_stderr(io.StringIO()):
            pane = herdr_pane.open_pane("execute", "placeholder-cli-1", self.tmp,
                                       self.env, self.seams)
        self.assertIsNone(pane)
        self.assertEqual(self.calls.count(["fake-herdr", "tab", "close", "t1"]), 1)
        self.assertFalse(os.path.exists(self.run_dir))

    def test_open_pane_writes_the_runner_record_grammar(self):
        with open(_FIXTURE, encoding="utf-8") as handle:
            fixture = json.load(handle)

        def write_pid():
            with open(os.path.join(self.run_dir, "pid"), "w", encoding="utf-8") as handle:
                handle.write(f"{os.getpid()}\n")

        self.on_sleep = write_pid
        with contextlib.redirect_stderr(io.StringIO()):
            pane = herdr_pane.open_pane("execute", "placeholder-cli-1", self.tmp,
                                        self.env, self.seams)
        self.on_sleep = None
        self.assertIsNotNone(pane)
        assert pane is not None
        record = herdr_pane._read_run_record(pane["run_dir"])
        self.assertIsNotNone(record)
        assert record is not None
        self.assertEqual(sorted(record), sorted(fixture["run_record_fields"]))
        self.assertEqual(record["version"], 1)
        self.assertIsNotNone(herdr_pane.TOKEN_RE.fullmatch(record["token"]))
        self.assertIn(record["role"], ("review", "execute"))
        self.assertEqual(record["label"],
                         herdr_pane.pane_label(record["role"], record["runtime"],
                                               record["token"]))
        self.assertLessEqual(len(record["label"]), 63)
        self.assertIsInstance(record["runner_pid"], int)
        self.assertGreater(record["runner_pid"], 0)
        self.assertIsInstance(record["runner_start"], str)
        self.assertIsInstance(record["host_name"], str)
        self.assertGreater(len(record["host_name"]), 0)
        tab_id = record["tab_id"]
        if tab_id is not None:
            self.assertIsNotNone(herdr_pane.HOST_ID_RE.fullmatch(tab_id))
        launcher_pgid = record["launcher_pgid"]
        if launcher_pgid is not None:
            self.assertIsInstance(launcher_pgid, int)
            self.assertGreater(launcher_pgid, 1)
        self.assertIsInstance(record["launcher_start"], str)
        self.assertEqual(format(stat.S_IMODE(os.stat(pane["run_dir"]).st_mode), "o"),
                         fixture["dir_mode"])
        record_path = os.path.join(pane["run_dir"], herdr_pane.HOST_FILES["run"])
        self.assertEqual(format(stat.S_IMODE(os.stat(record_path).st_mode), "o"),
                         fixture["file_mode"])

    def test_fake_clock_round_reads_the_verdict(self):
        pane = self._open()
        self._play_the_round()
        job = herdr_pane.PaneRound(["/bin/true"], "", self.tmp, 30)
        self.assertEqual(herdr_pane.run_round(pane, job, self.seams), "rc")
        verdict = herdr_pane.read_verdict(self.run_dir)
        assert verdict is not None
        self.assertEqual(verdict["code"], 0)
        self.assertEqual(verdict["status"]["session"], "fake-sid-2")

    def test_launcher_gone_before_the_round_writes_nothing(self):
        pane = self._open()
        self.alive = False
        job = herdr_pane.PaneRound(["/bin/true"], "", self.tmp, 30)
        self.assertEqual(herdr_pane.run_round(pane, job, self.seams), "launcher gone")
        for name in ("env", "prompt", herdr_pane.ROUND_FILE):
            self.assertFalse(os.path.exists(os.path.join(self.run_dir, name)))

    def test_launcher_gone_mid_round_drops_the_round_files(self):
        pane = self._open()
        fired = []

        def on_sleep():
            if fired:
                return
            fired.append(True)
            self.alive = False

        self.on_sleep = on_sleep
        job = herdr_pane.PaneRound(["/bin/true"], "", self.tmp, 30)
        self.assertEqual(herdr_pane.run_round(pane, job, self.seams), "launcher gone")
        for name in ("env", "prompt", herdr_pane.ROUND_FILE):
            self.assertFalse(os.path.exists(os.path.join(self.run_dir, name)))

    def test_timeout_lands_at_the_deadline_before_retirement(self):
        pane = self._open()
        start = self.now
        job = herdr_pane.PaneRound(["/bin/true"], "", self.tmp, 3)
        self.assertEqual(herdr_pane.run_round(pane, job, self.seams), "timeout")
        kill_clock = self.kill_clock
        assert kill_clock is not None
        waited = kill_clock - start
        self.assertGreaterEqual(waited, job.timeout_s)
        self.assertLess(waited, job.timeout_s + 1)
        for name in ("env", "prompt", herdr_pane.ROUND_FILE):
            self.assertFalse(os.path.exists(os.path.join(self.run_dir, name)))


class TestPaneBoundary(_PaneFakeHarness, unittest.TestCase):
    """A pane round driven through run_runner's spawn seam: one argv, one pgid file, one
    env, one trailer rule and one reason path."""

    tmp_prefix = "herdr-pane-boundary-"
    pgid_file: str = ""

    def _spec(self, timeout_s=30):
        return runner_dispatch.RunnerSpec(
            "placeholder-cli-1", "placeholder-model-1", "exec", timeout_s, cwd=self.tmp)

    def _runner_seams(self, pane):
        """run_runner's seams for one pane round: the pane as the spawn seam, the shared
        fake clock, recording print and kill seams, and a host-signal-bearing env_fn."""
        self.printed: list[str] = []
        self.runner_kills: list[tuple[int, int]] = []
        return runner_dispatch.RunnerSeams(
            which_fn=lambda name: "fake-node",
            runner_path_fn=lambda: "fake-runner.mjs",
            route_fn=lambda *args: None,
            env_fn=lambda: {"PATH": "/usr/bin:/bin", "CLAUDECODE": "1", "AIKIT_T2": "kept"},
            print_fn=self.printed.append,
            kill_fn=lambda pgid, sig: self.runner_kills.append((pgid, sig)),
            time_fn=self.clock_time,
            sleep_fn=self.clock_sleep,
            spawn_fn=herdr_pane.pane_spawn(pane, self.seams),
        )

    def _play_the_rc_round(self, pane, out="", err="", rc="0\n"):
        """The fake launcher plays the round once: the round's verdict files land."""
        fired = []

        def on_sleep():
            if fired:
                return
            fired.append(True)
            round_path = os.path.join(pane["run_dir"], herdr_pane.ROUND_FILE)
            with open(round_path, encoding="utf-8") as handle:
                self.round_text = handle.read()
            os.unlink(round_path)
            with open(os.path.join(pane["run_dir"], "out"), "w", encoding="utf-8") as handle:
                handle.write(out)
            with open(os.path.join(pane["run_dir"], "err"), "w", encoding="utf-8") as handle:
                handle.write(err)
            with open(os.path.join(pane["run_dir"], "rc"), "w", encoding="utf-8") as handle:
                handle.write(rc)

        return on_sleep

    def _play_the_pgid_round(self, pane, end):
        """The fake launcher records one lane group into run_runner's pgid file, then
        ends the round (rc) or never answers (timeout)."""
        fired = []

        def on_sleep():
            if fired:
                return
            fired.append(True)
            round_path = os.path.join(pane["run_dir"], herdr_pane.ROUND_FILE)
            with open(round_path, encoding="utf-8") as handle:
                self.round_text = handle.read()
            os.unlink(round_path)
            argv = shlex.split(self.round_text.rstrip("\n").split("\n")[-1])[3:-2]
            self.pgid_file = argv[argv.index("--child-pgid-file") + 1]
            with open(self.pgid_file, "w", encoding="utf-8") as handle:
                handle.write("spawn 5150\n")
            if end == "rc":
                with open(os.path.join(pane["run_dir"], "rc"), "w",
                          encoding="utf-8") as handle:
                    handle.write("0\n")

        return on_sleep

    def test_round_sh_command_line_is_run_runner_argv(self):
        pane = self._open()
        self.on_sleep = self._play_the_rc_round(pane)
        spec = self._spec()
        result = runner_dispatch.run_runner(spec, "hi", self._runner_seams(pane))
        self.assertEqual(result.returncode, 0)
        tokens = shlex.split(self.round_text.rstrip("\n").split("\n")[-1])
        self.assertEqual(tokens[:3], ["cd", self.tmp, "&&"])
        self.assertEqual(tokens[-2:], ["<&3", "3<&-"])
        argv = tokens[3:-2]
        pgid_file = argv[argv.index("--child-pgid-file") + 1]
        self.assertEqual(
            argv, [*runner_dispatch.build_runner_argv(spec, "fake-runner.mjs", "fake-node"),
                   "--child-pgid-file", pgid_file])
        self.assertEqual(1, argv.count("--child-pgid-file"))
        self.assertFalse(pgid_file.startswith(pane["run_dir"]))
        self.assertEqual(os.path.basename(pgid_file), "child-pgids")
        self.assertFalse(os.path.exists(os.path.dirname(pgid_file)))

    def test_env_file_carries_no_host_signal_name(self):
        pane = self._open()
        self.on_sleep = self._play_the_rc_round(pane)
        runner_dispatch.run_runner(self._spec(), "hi", self._runner_seams(pane))
        self.assertIn("CLAUDECODE", HOST_SIGNAL_ENV_VARS)
        with open(os.path.join(pane["run_dir"], "env"), encoding="utf-8") as handle:
            env_text = handle.read()
        self.assertNotIn("CLAUDECODE", env_text)
        self.assertIn("export AIKIT_T2=kept", env_text)

    def test_ok_round_returns_the_verdict_and_relays_stderr(self):
        pane = self._open()
        trailer = ("AIKIT-XAI status=ok exit=0 cli=placeholder-cli-1 "
                   "model=placeholder-model-1 session=fake-sid-3")
        err = f"cross-ai: starting\n{trailer}\n"
        self.on_sleep = self._play_the_rc_round(pane, out="round-out\n", err=err)
        result = runner_dispatch.run_runner(self._spec(), "hi", self._runner_seams(pane))
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "round-out\n")
        self.assertEqual(result.stderr_tail, err)
        self.assertEqual(self.printed, err.splitlines())
        status = result.status
        self.assertIsNotNone(status)
        assert status is not None
        self.assertEqual(status["session"], "fake-sid-3")
        self.assertEqual(result.reason, runner_dispatch.reason_for_status("ok", 0))

    def test_a_trailer_naming_another_cli_is_dropped(self):
        pane = self._open()
        err = ("AIKIT-XAI status=ok exit=0 cli=other model=placeholder-model-1 "
               "session=fake-sid-3\n")
        self.on_sleep = self._play_the_rc_round(pane, err=err)
        result = runner_dispatch.run_runner(self._spec(), "hi", self._runner_seams(pane))
        self.assertIsNone(result.status)
        self.assertEqual(result.returncode, 0)
        self.assertIn("ai-kit-spec: ignoring a runner status line that does not match "
                      "this run", self.printed)

    def test_no_rc_until_the_deadline_is_a_timeout(self):
        pane = self._open()
        spec = self._spec(timeout_s=3)
        start = self.now
        result = runner_dispatch.run_runner(spec, "hi", self._runner_seams(pane))
        self.assertTrue(result.timed_out)
        self.assertEqual(result.reason, "timeout")
        self.assertIs(pane["closed"], True)
        self.assertGreaterEqual(self.now - start, 3 + 30 + 10)
        self.assertIn((424242, signal.SIGTERM), self.kills)
        self.assertIn((424242, signal.SIGKILL), self.kills)

    def test_a_gone_launcher_is_dispatch_unavailable(self):
        pane = self._open()
        self.alive = False
        result = runner_dispatch.run_runner(self._spec(), "hi", self._runner_seams(pane))
        self.assertEqual(result.reason, "dispatch_unavailable")
        self.assertIs(pane["closed"], True)
        self.assertIn("pane launcher gone", self.printed)

    def test_the_recorded_group_is_signalled_on_every_exit(self):
        for end in ("rc", "timeout"):
            with self.subTest(end=end):
                shutil.rmtree(self.run_dir, ignore_errors=True)
                pane = self._open()
                self.on_sleep = self._play_the_pgid_round(pane, end)
                result = runner_dispatch.run_runner(self._spec(timeout_s=3), "hi",
                                                    self._runner_seams(pane))
                if end == "rc":
                    self.assertEqual(result.returncode, 0)
                else:
                    self.assertTrue(result.timed_out)
                self.assertIn((5150, signal.SIGTERM), self.runner_kills)
                self.assertIn((5150, signal.SIGKILL), self.runner_kills)
                self.assertFalse(os.path.exists(os.path.dirname(self.pgid_file)))


class TestPaneRefusals(unittest.TestCase):
    """Pane refusals that hold on every host: fixed strings, no skips, no herdr."""

    def _tmp(self, prefix):
        work = tempfile.mkdtemp(prefix=prefix)
        self.addCleanup(shutil.rmtree, work, ignore_errors=True)
        return work

    def _recording_run(self):
        """A run seam that records every call; the test fails if any call lands."""
        calls = []

        def run_fn(argv, **kwargs):
            calls.append(list(argv))
            return subprocess.CompletedProcess(argv, 1, "", "")

        return run_fn, calls

    def test_a_colliding_run_directory_is_refused_and_left_alone(self):
        work = self._tmp("herdr-pane-collide-")
        run_dir = os.path.join(work, "runs", "tok")
        self.assertIsNone(herdr_pane._make_run_dir(run_dir, "tok"))
        Path(run_dir, "run.json").write_text("{}", encoding="utf-8")
        self.assertEqual(herdr_pane._make_run_dir(run_dir, "tok"), "run directory exists: tok")
        self.assertEqual(os.listdir(run_dir), ["run.json"])

    def test_herdr_absent_refuses_without_a_call(self):
        work = self._tmp("herdr-pane-absent-")
        cases = (
            ("no HERDR_ENV",
             {"PATH": "/usr/bin:/bin", "XDG_STATE_HOME": os.path.join(work, "state")},
             lambda name, path=None: "fake-herdr"),
            ("no herdr CLI on PATH",
             {"HERDR_ENV": "1", "PATH": "/usr/bin:/bin",
              "XDG_STATE_HOME": os.path.join(work, "state")},
             lambda name, path=None: None),
        )
        for case_name, env, which_fn in cases:
            with self.subTest(case=case_name):
                run_fn, calls = self._recording_run()
                seams = herdr_pane.PaneSeams(run_fn=run_fn, which_fn=which_fn,
                                            token_fn=lambda: _TOKEN)
                with contextlib.redirect_stderr(io.StringIO()):
                    self.assertIsNone(herdr_pane.open_pane(
                        "execute", "placeholder-cli-1", work, env, seams))
                self.assertEqual(calls, [])
                self.assertFalse(os.path.exists(os.path.join(work, "state", "ai-kit")))

    def test_unsafe_state_home_refuses_without_a_call(self):
        work = self._tmp("herdr-pane-unsafe-")
        env = {"HERDR_ENV": "1", "PATH": "/usr/bin:/bin",
               "XDG_STATE_HOME": os.path.join(work, "a b")}
        run_fn, calls = self._recording_run()
        seams = herdr_pane.PaneSeams(run_fn=run_fn,
                                     which_fn=lambda name, path=None: "fake-herdr",
                                     token_fn=lambda: _TOKEN)
        capture = io.StringIO()
        with contextlib.redirect_stderr(capture):
            self.assertIsNone(herdr_pane.open_pane(
                "execute", "placeholder-cli-1", work, env, seams))
        self.assertEqual(capture.getvalue(),
                         "ai-kit-spec: pane: state home path holds a character "
                         "outside [A-Za-z0-9._/-]\n")
        self.assertEqual(calls, [])

    def test_pane_problem_names_the_missing_tool(self):
        self._tmp("herdr-pane-problem-")
        self.assertEqual(
            herdr_pane.pane_problem("/x/ai-kit/spec/host/0123456789ab",
                                    access_fn=lambda path, mode: path != "/usr/bin/setsid"),
            "/usr/bin/setsid is not executable")

    def test_herdr_call_refuses_an_unknown_verb(self):
        self._tmp("herdr-pane-verb-")
        run_fn, calls = self._recording_run()
        with self.assertRaises(ValueError) as caught:
            herdr_pane._herdr_call("fake-herdr", "pane read", [], {}, run_fn)
        message = str(caught.exception)
        for verb in herdr_pane.PANE_VERBS:
            self.assertIn(verb, message)
        self.assertEqual(calls, [])

    def test_rc_grammar(self):
        work = self._tmp("herdr-pane-rc-")
        rc_path = os.path.join(work, "rc")

        def write_rc(body):
            with open(rc_path, "w", encoding="utf-8") as handle:
                handle.write(body)

        write_rc("255")
        verdict = herdr_pane.read_verdict(work)
        assert verdict is not None
        self.assertEqual(verdict["code"], 255)
        self.assertIsNone(verdict["signal"])
        self.assertIsNone(verdict["bad"])

        write_rc("SIGTERM\n")
        verdict = herdr_pane.read_verdict(work)
        assert verdict is not None
        self.assertEqual(verdict["signal"], "SIGTERM")
        self.assertIsNone(verdict["code"])
        self.assertIsNone(verdict["bad"])

        for body in ("256", "007", "-1", "sigterm"):
            with self.subTest(body=body):
                write_rc(body)
                verdict = herdr_pane.read_verdict(work)
                assert verdict is not None
                self.assertIsNotNone(verdict["bad"])
                self.assertIsNone(verdict["code"])

        write_rc("")
        self.assertIsNone(herdr_pane.read_verdict(work))
        os.unlink(rc_path)
        self.assertIsNone(herdr_pane.read_verdict(work))


class TestProtocolMirror(unittest.TestCase):
    """The pane module mirrors the runner's committed protocol fixture."""

    def setUp(self):
        fixture_path = Path(__file__).resolve().parent / "fixtures" / "runner_host_protocol.json"
        self.fixture = json.loads(fixture_path.read_text(encoding="utf-8"))

    def test_module_mirrors_the_runner_protocol_fixture(self):
        fixture = self.fixture
        self.assertEqual(herdr_pane.HOST_FILES, fixture["files"])
        self.assertLessEqual(set(herdr_pane.PANE_VERBS), set(fixture["herdr_verbs"]))
        self.assertEqual(herdr_pane.LABEL_PREFIX, fixture["label"]["prefix"])
        self.assertEqual(herdr_pane.LABEL_RE.pattern, fixture["label"]["pattern"])
        self.assertEqual(herdr_pane.LABEL_MAX, fixture["label"]["max_length"])
        self.assertEqual(herdr_pane.TOKEN_RE.pattern, fixture["token_pattern"])
        self.assertEqual(herdr_pane.RC_RE.pattern, fixture["rc_pattern"])
        self.assertEqual(format(herdr_pane.DIR_MODE, "o"), fixture["dir_mode"])
        self.assertEqual(format(herdr_pane.FILE_MODE, "o"), fixture["file_mode"])
        self.assertEqual(
            herdr_pane.run_dir_for({"XDG_STATE_HOME": "/H"}, "0123456789ab"),
            fixture["run_dir"].replace("<state home>", "/H").replace("<token>",
                                                                    "0123456789ab"))
        self.assertEqual(herdr_pane.typed_line("/X/launch.sh"),
                         fixture["typed_line"].replace("<launcher path>", "/X/launch.sh"))
        self.assertIn(fixture["verdict"], herdr_pane.HOST_FILES)
        self.assertIn("AIKIT-HOST-DONE %s rc=%s",
                      herdr_pane.launcher_text("/H/ai-kit/spec/host/0123456789ab",
                                               "0123456789ab"))


class TestLiveLauncherPid(unittest.TestCase):
    """The launcher pid from run.json while it is alive, else None."""

    def test_missing_record_dead_pid_and_live_pid(self):
        with tempfile.TemporaryDirectory() as tmp:
            pane = {"run_dir": tmp}
            self.assertIsNone(herdr_pane.live_launcher_pid(pane, lambda _pid: True))
            herdr_pane._write_record(tmp, {"launcher_pid": 4242})
            self.assertIsNone(herdr_pane.live_launcher_pid(pane, lambda _pid: False))
            self.assertEqual(herdr_pane.live_launcher_pid(pane, lambda _pid: True), 4242)
            herdr_pane._write_record(tmp, {"launcher_pid": True})
            self.assertIsNone(herdr_pane.live_launcher_pid(pane, lambda _pid: True))
            self.assertIsNone(herdr_pane.live_launcher_pid({"run_dir": ""}, lambda _pid: True))


if __name__ == "__main__":
    unittest.main()
