"""E2E tier: real node and git, hermetic env for the cross-AI runner template."""

from __future__ import annotations

import contextlib
import glob
import importlib.util
import io
import json
import math
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, "skills", "ai-kit-gsd-curated-config"))
sys.path.insert(0, os.path.join(REPO_ROOT, "skills", "ai-kit-spec-review"))

from ai_kit_gsd_curated_config import cross_ai_script
from ai_kit_spec.detection import HOST_SIGNAL_ENV_VARS
from ai_kit_spec.execute_dispatch import (
    ExecuteDispatchSpec,
    ExecuteSeams,
    dispatch_execute,
)
from ai_kit_spec.reviewer_dispatch import (
    ReviewerDispatchSpec,
    ReviewerSeams,
    dispatch_reviewer,
)
from ai_kit_spec.runner_dispatch import RunnerSeams, RunnerSpec, run_runner
from ai_kit_spec.tooling_guidance import resolve_cross_ai_template_path


def _real_node_executable() -> str | None:
    if shutil.which("node") is None:
        return None
    try:
        proc = subprocess.run(
            ["node", "-e", "process.stdout.write(process.execPath)"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return proc.stdout if proc.returncode == 0 and os.path.isfile(proc.stdout) else None

_RESOLVED_TEMPLATE = resolve_cross_ai_template_path()
assert _RESOLVED_TEMPLATE is not None, "the shipped runner template is missing"
TEMPLATE = _RESOLVED_TEMPLATE


def runner_env(tmp: str) -> dict[str, str]:
    """Hermetic env matching cross-ai.mjs --self-test (fakes + node + git + mkfifo only)."""
    bin_dir = os.path.join(tmp, "bin")
    os.makedirs(bin_dir, exist_ok=True)
    node_bin = _real_node_executable()
    git_bin = shutil.which("git")
    # the FIFO cases (overlay-fifo-refused, retry-config-fifo) create their FIFO with mkfifo
    mkfifo_bin = shutil.which("mkfifo")
    if mkfifo_bin:
        link = os.path.join(bin_dir, "mkfifo")
        if not os.path.lexists(link):
            os.symlink(mkfifo_bin, link)
    if node_bin:
        link = os.path.join(bin_dir, "node")
        if not os.path.lexists(link):
            os.symlink(node_bin, link)
    if git_bin:
        link = os.path.join(bin_dir, "git")
        if not os.path.lexists(link):
            os.symlink(git_bin, link)
    # the fake bin stays first; the real node dir is added so a seam whose which_fn reads PATH
    # (the default) still resolves node, while the child itself only ever sees bin_dir
    path = bin_dir
    if node_bin:
        path = bin_dir + os.pathsep + os.path.dirname(node_bin)
    home = os.path.join(tmp, "home")
    os.makedirs(home, exist_ok=True)
    return {
        "PATH": path,
        "HOME": home,
        "XDG_CONFIG_HOME": os.path.join(home, ".config"),
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_AUTHOR_NAME": "xai-selftest",
        "GIT_COMMITTER_NAME": "xai-selftest",
        "GIT_AUTHOR_EMAIL": "xai-selftest@example.invalid",
        "GIT_COMMITTER_EMAIL": "xai-selftest@example.invalid",
        "LANG": "C",
    }


# The full self-test runs are guarded by these hard limits. Each guard and the ceilings it guards
# are sized from ONE load reading (`load_reading`, passed to Node as AIKIT_XAI_SELFTEST_LOAD): a
# second, independently sampled reading (or Python's CPU count against Node's availableParallelism
# under an affinity mask) could differ, so the guard could fire before the ceilings it guards.
SELF_TEST_GUARD_SECS = 300
RENDER_SELF_TEST_GUARD_SECS = 900
MAX_LOAD_FACTOR = 4
_RUNNER_PATH = os.path.join(REPO_ROOT, "tools", "run_unittest_parallel.py")


def _load_runner():
    spec = importlib.util.spec_from_file_location("run_unittest_parallel", _RUNNER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_reading() -> float:
    """One-minute load per CPU over the runner's own CPU count; 0.0 when unreadable."""
    cpus = _load_runner().available_cpus()
    try:
        load = os.getloadavg()[0]
    except OSError:
        return 0.0
    return load / cpus if cpus else 0.0


def load_factor(reading: float) -> float:
    """The reading clamped to 1..MAX_LOAD_FACTOR; 1 for a non-finite or non-positive reading."""
    if not math.isfinite(reading) or reading <= 0:
        return 1.0
    return min(float(MAX_LOAD_FACTOR), max(1.0, reading))


def guard_secs(base: int, factor: float) -> int:
    return math.ceil(base * factor)


def assert_factor_printed(case: unittest.TestCase, stderr: str, reading: float) -> None:
    match = re.search(r"self-test load factor (\S+)\n", stderr)
    assert match is not None, stderr
    case.assertAlmostEqual(float(match.group(1)), load_factor(reading), delta=1e-9)


# The runner stops this module with SIGTERM to its process group (MODULE_STOP_GRACE_SECS = 15 s).
# Each session started here is stopped the same way, so the self-test's selfTestAbort() reaps its
# detached case runners before any hard kill. STOP_GRACE_SECS must stay below the runner's grace.
STOP_GRACE_SECS = 10
_LIVE_GROUPS: set[subprocess.Popen] = set()


def stop_group(proc: subprocess.Popen, grace: float) -> None:
    """SIGTERM to the group of `proc`, up to `grace` seconds to exit, then SIGKILL to the group."""
    with contextlib.suppress(ProcessLookupError):
        os.killpg(proc.pid, signal.SIGTERM)
    with contextlib.suppress(subprocess.TimeoutExpired):
        proc.wait(timeout=grace)
    with contextlib.suppress(ProcessLookupError):
        os.killpg(proc.pid, signal.SIGKILL)


def _forward_sigterm(_signum, _frame) -> None:
    for proc in list(_LIVE_GROUPS):
        stop_group(proc, STOP_GRACE_SECS)
    os._exit(128 + signal.SIGTERM)


def setUpModule() -> None:
    signal.signal(signal.SIGTERM, _forward_sigterm)


def start_group(argv: list[str], **kwargs) -> subprocess.Popen:
    """Start `argv` in a new session and register it for SIGTERM forwarding."""
    proc = subprocess.Popen(
        argv,
        start_new_session=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        **kwargs,
    )
    _LIVE_GROUPS.add(proc)
    return proc


def run_group(argv: list[str], timeout: int, **kwargs) -> subprocess.CompletedProcess:
    """`subprocess.run` in a new session; a timeout stops the whole group (SIGTERM, then SIGKILL),
    not just the leader, so no fake CLI outlives the test."""
    proc = start_group(argv, **kwargs)
    try:
        with proc:
            try:
                out, err = proc.communicate(timeout=timeout)
            except subprocess.TimeoutExpired:
                stop_group(proc, STOP_GRACE_SECS)
                out, err = proc.communicate()
                raise
            return subprocess.CompletedProcess(argv, proc.returncode, out, err)
    finally:
        _LIVE_GROUPS.discard(proc)


_FAKE_OPENCODE = """\
#!/usr/bin/env node
import fs from 'node:fs';
const calls = process.env.FAKE_CALLS;
const log = (line) => { if (calls) fs.appendFileSync(calls, line + '\\n'); };
const argOf = (flag) => {
  const i = process.argv.indexOf(flag);
  return i >= 0 ? process.argv[i + 1] || '' : '';
};
const sub = process.argv.slice(2);
const MODES = ['ok', 'empty', 'quota', 'auth', 'billing', 'capacity', 'crash', 'hang', 'nochange'];
if (sub[0] === 'models') {
  log('opencode models');
  for (const mode of MODES) console.log('fake/' + mode);
  process.exit(0);
}
const model = argOf('--model');
const mode = model.startsWith('fake/') ? model.slice(5).replace(/#[^#/]+$/, '') : '';
log('opencode ' + model);
const okLines = () => {
  const lines = [
    JSON.stringify({ type: 'text', sessionID: 'ses_1',
      part: { id: 'p1', messageID: 'm1', type: 'text', text: 'Plan first.' } }),
    JSON.stringify({ type: 'tool_use', sessionID: 'ses_1',
      part: { type: 'tool', tool: 'bash' } }),
    JSON.stringify({ type: 'text', sessionID: 'ses_1',
      part: { id: 'p2', messageID: 'm2', type: 'text', text: '## Summary\\ndone' } }),
  ];
  for (const l of lines) console.log(l);
};
let stdin = '';
process.stdin.on('data', (chunk) => { stdin += chunk; }).on('end', () => {
  const stdinLog = process.env.FAKE_STDIN;
  if (stdinLog) fs.appendFileSync(stdinLog, stdin);
  if (mode === 'empty') process.exit(0);
  if (mode === 'quota') { process.stderr.write('quota exceeded\\n'); process.exit(1); }
  if (mode === 'auth') { process.stderr.write('401 unauthorized\\n'); process.exit(1); }
  if (mode === 'billing') { process.stderr.write('402 payment required\\n'); process.exit(1); }
  if (mode === 'capacity') { process.stderr.write('503 Service Unavailable\\n'); process.exit(1); }
  if (mode === 'crash') { process.stderr.write('boom\\n'); process.exit(7); }
  if (mode === 'hang') { setInterval(() => {}, 1 << 30); return; }
  if (mode === 'nochange') { okLines(); return; }
  if (process.argv.includes('--auto')) fs.appendFileSync('a.txt', 'oc\\n');
  okLines();
});
"""


def write_fake_opencode(bin_dir: str) -> None:
    """The template's own fake opencode, extended with `fake/<mode>` behaviors.

    `models` lists every mode except `missing`. `ok` drains stdin, appends `oc` to `a.txt` only
    under `--auto`, and prints the three JSON lines; the other modes follow the template's fake pi.
    """
    path = os.path.join(bin_dir, "opencode")
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(_FAKE_OPENCODE)
    os.chmod(path, 0o755)


def _git_init(repo: str) -> None:
    env = runner_env(os.path.dirname(repo))
    subprocess.run(
        ["git", "init", "-q", "-b", "main"], cwd=repo, env=env, check=True,
        capture_output=True, text=True,
    )
    with open(os.path.join(repo, "a.txt"), "w", encoding="utf-8") as handle:
        handle.write("base\n")
    subprocess.run(
        ["git", "add", "a.txt"], cwd=repo, env=env, check=True,
        capture_output=True, text=True,
    )
    subprocess.run(
        ["git", "commit", "-q", "-m", "base"], cwd=repo, env=env, check=True,
        capture_output=True, text=True,
    )


def pids_with_cwd_under(root: str) -> list[int]:
    out = []
    for name in os.listdir("/proc"):
        if not name.isdigit():
            continue
        try:
            cwd = os.readlink(f"/proc/{name}/cwd")
        except OSError:
            continue
        if cwd == root or cwd.startswith(root + os.sep):
            out.append(int(name))
    return out


class TestRunnerTemplate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._skip = None
        if _real_node_executable() is None:
            cls._skip = "no node executable"
        elif shutil.which("git") is None:
            cls._skip = "git not on PATH"

    def setUp(self):
        if self._skip:
            self.skipTest(self._skip)

    def test_self_test(self):
        node_bin = _real_node_executable()
        assert node_bin is not None
        reading = load_reading()
        with tempfile.TemporaryDirectory() as tmp:
            env = {**runner_env(tmp), "AIKIT_XAI_SELFTEST_LOAD": repr(reading)}
            proc = run_group(
                [node_bin, TEMPLATE, "--self-test"],
                guard_secs(SELF_TEST_GUARD_SECS, load_factor(reading)),
                cwd=REPO_ROOT,
                env=env,
            )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        self.assertIn("self-test ok", proc.stdout)
        assert_factor_printed(self, proc.stderr, reading)

    @unittest.skipUnless(os.path.isdir("/proc/self"), "needs /proc to find survivors")
    def test_interrupted_self_test_leaves_nothing(self):
        node_bin = _real_node_executable()
        assert node_bin is not None
        with tempfile.TemporaryDirectory() as tmp:
            st_tmp = os.path.join(tmp, "st")
            os.makedirs(st_tmp)
            env = {
                **runner_env(tmp),
                "TMPDIR": st_tmp,
                "AIKIT_XAI_SELFTEST_CASES": "sigterm-hang",
            }
            with subprocess.Popen(
                [node_bin, TEMPLATE, "--self-test"],
                cwd=REPO_ROOT,
                env=env,
                start_new_session=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            ) as proc:
                try:
                    deadline = time.monotonic() + 30
                    pattern = os.path.join(st_tmp, "xai-st-*", "r-sigterm-hang", "gc.pid")
                    while not glob.glob(pattern):
                        self.assertLess(time.monotonic(), deadline, "fake CLI never started")
                        time.sleep(0.05)
                    proc.send_signal(signal.SIGTERM)
                    rc = proc.wait(timeout=15)
                finally:
                    if proc.poll() is None:
                        os.killpg(proc.pid, signal.SIGKILL)
            survivors = pids_with_cwd_under(st_tmp)
            for pid in survivors:
                os.kill(pid, signal.SIGKILL)
            self.assertEqual(rc, 128 + signal.SIGTERM)
            self.assertEqual(survivors, [])
            self.assertEqual(os.listdir(st_tmp), [])


class SelfTestLoadFactorTest(unittest.TestCase):
    """The self-test reads one load factor per run: injected readings give 1, in between, 4."""

    @classmethod
    def setUpClass(cls):
        cls._skip = None
        if _real_node_executable() is None:
            cls._skip = "no node executable"
        elif shutil.which("git") is None:
            cls._skip = "git not on PATH"

    def setUp(self):
        if self._skip:
            self.skipTest(self._skip)

    def _run(self, reading: str | None) -> subprocess.CompletedProcess:
        node_bin = _real_node_executable()
        assert node_bin is not None
        with tempfile.TemporaryDirectory() as tmp:
            env = {**runner_env(tmp), "AIKIT_XAI_SELFTEST_CASES": "load-factor-math"}
            if reading is not None:
                env["AIKIT_XAI_SELFTEST_LOAD"] = reading
            return run_group([node_bin, TEMPLATE, "--self-test"], 120, cwd=REPO_ROOT, env=env)

    def test_injected_readings(self):
        for reading, expected in (
            ("0", "1"), ("0.5", "1"), ("1", "1"), ("2.5", "2.5"), ("4", "4"), ("10", "4"),
            ("junk", "1"),
        ):
            with self.subTest(reading=reading):
                proc = self._run(reading)
                self.assertEqual(proc.returncode, 0, msg=proc.stderr)
                self.assertIn("self-test ok", proc.stdout)
                self.assertIn(f"self-test load factor {expected}\n", proc.stderr)

    def test_measured_factor_is_in_range(self):
        proc = self._run(None)
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        match = re.search(r"self-test load factor (\S+)\n", proc.stderr)
        assert match is not None, proc.stderr
        self.assertTrue(1.0 <= float(match.group(1)) <= 4.0, msg=match.group(0))


class GuardFactorTest(unittest.TestCase):
    """The hang guards follow one load factor from the runner's CPU count (Python 3.12 safe)."""

    def test_reading_is_load_over_the_runners_cpu_count(self):
        runner = mock.Mock(available_cpus=lambda: 8)
        with (
            mock.patch(f"{__name__}._load_runner", return_value=runner),
            mock.patch("os.getloadavg", return_value=(12.0, 0.0, 0.0)),
        ):
            self.assertEqual(load_reading(), 1.5)

    def test_reading_is_zero_without_a_load_average_or_cpu_count(self):
        runner = mock.Mock(available_cpus=lambda: 8)
        with (
            mock.patch(f"{__name__}._load_runner", return_value=runner),
            mock.patch("os.getloadavg", side_effect=OSError),
        ):
            self.assertEqual(load_reading(), 0.0)
        runner = mock.Mock(available_cpus=lambda: None)
        with (
            mock.patch(f"{__name__}._load_runner", return_value=runner),
            mock.patch("os.getloadavg", return_value=(3.0, 0.0, 0.0)),
        ):
            self.assertEqual(load_reading(), 0.0)

    def test_factor_is_clamped(self):
        for reading, expected in (
            (0.0, 1.0), (0.5, 1.0), (1.0, 1.0), (2.5, 2.5), (4.0, 4.0), (9.0, 4.0),
            (float("nan"), 1.0), (float("inf"), 1.0), (-1.0, 1.0),
        ):
            with self.subTest(reading=reading):
                self.assertEqual(load_factor(reading), expected)

    def test_guard_rounds_up(self):
        self.assertEqual(guard_secs(300, 1.0), 300)
        self.assertEqual(guard_secs(300, 2.5), 750)
        self.assertEqual(guard_secs(7, 1.5), 11)


def _proc_fields(pid: int) -> list[str] | None:
    """The stat fields after the command name: state, ppid, pgrp, session, ..."""
    try:
        with open(f"/proc/{pid}/stat", encoding="utf-8") as handle:
            return handle.read().rsplit(")", 1)[1].split()
    except (OSError, IndexError):
        return None


def _case_runner_pids(node_pid: int) -> list[int]:
    found = []
    for name in os.listdir("/proc"):
        fields = _proc_fields(int(name)) if name.isdigit() else None
        if fields and int(fields[1]) == node_pid:
            try:
                with open(f"/proc/{name}/cmdline", "rb") as handle:
                    cmdline = handle.read()
            except OSError:
                continue
            if b".mjs" in cmdline:
                found.append(int(name))
    return found


def _pids_in_session(sid: int) -> list[int]:
    out = []
    for name in os.listdir("/proc"):
        fields = _proc_fields(int(name)) if name.isdigit() else None
        if fields and fields[0] != "Z" and int(fields[3]) == sid:
            out.append(int(name))
    return out


class DeadlineCouplingTest(unittest.TestCase):
    """The runner's deadline for this module covers the load-scaled guards (D-10)."""

    def test_runner_deadline_covers_scaled_guards(self):
        runner = _load_runner()
        need = MAX_LOAD_FACTOR * (SELF_TEST_GUARD_SECS + RENDER_SELF_TEST_GUARD_SECS) + 600
        self.assertGreaterEqual(runner.module_timeout_secs(__name__), need)
        self.assertGreater(runner.MODULE_STOP_GRACE_SECS, STOP_GRACE_SECS)


@unittest.skipUnless(os.path.isdir("/proc/self"), "needs /proc to find the case runner's session")
class StopGroupTest(unittest.TestCase):
    """stop_group reaches the self-test's detached case runners through selfTestAbort()."""

    def test_stopping_the_self_test_leaves_no_case_runner_session(self):
        node_bin = _real_node_executable()
        if node_bin is None or shutil.which("git") is None:
            self.skipTest("needs node and git")
        with tempfile.TemporaryDirectory() as tmp:
            st_tmp = os.path.join(tmp, "st")
            os.makedirs(st_tmp)
            sentinel = os.path.join(tmp, "outside.txt")
            with open(sentinel, "w", encoding="utf-8") as handle:
                handle.write("keep")
            env = {**runner_env(tmp), "TMPDIR": st_tmp, "AIKIT_XAI_SELFTEST_CASES": "hang"}
            proc = start_group([node_bin, TEMPLATE, "--self-test"], cwd=REPO_ROOT, env=env)
            sid = 0
            try:
                deadline = time.monotonic() + 60
                while not sid:
                    runners = _case_runner_pids(proc.pid)
                    if runners:
                        fields = _proc_fields(runners[0])
                        sid = int(fields[3]) if fields else 0
                    self.assertLess(time.monotonic(), deadline, "no case runner appeared")
                    time.sleep(0.02)
                self.assertNotEqual(sid, proc.pid)  # detached: its own session
                stop_group(proc, STOP_GRACE_SECS)
                proc.communicate(timeout=30)
            finally:
                _LIVE_GROUPS.discard(proc)
                if proc.poll() is None:
                    os.killpg(proc.pid, signal.SIGKILL)
                    proc.communicate()
            survivors = _pids_in_session(sid)
            for pid in survivors:
                with contextlib.suppress(ProcessLookupError):
                    os.kill(pid, signal.SIGKILL)
            self.assertEqual(survivors, [])
            self.assertEqual(os.listdir(st_tmp), [])
            self.assertTrue(os.path.exists(sentinel))


class TestRenderedRunner(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._skip = None
        if _real_node_executable() is None:
            cls._skip = "no node executable"
        elif shutil.which("git") is None:
            cls._skip = "git not on PATH"
        with open(TEMPLATE, "rb") as f:
            cls._template = f.read()

    def setUp(self):
        if self._skip:
            self.skipTest(self._skip)

    def _artifact(self) -> dict:
        return {
            "kind": "cross-ai-script",
            "path": ".planning/scripts/cross-ai.mjs",
            "template": "cross-ai.mjs",
            "version": 3,
            "config": {
                "runtime": "pi",
                "models": {"pi": "router-env/my-coding"},
                "outer_timeout_s": 1800,
                "router_backed": {"pi": True},
            },
            "choices": {},
            "status": "ok",
            "source": "preset",
            "why": "e2e render",
        }

    def test_render_and_self_test(self):
        node_bin = _real_node_executable()
        assert node_bin is not None
        with tempfile.TemporaryDirectory() as tmp:
            plan = cross_ai_script.plan_script(
                tmp, self._artifact(), self._template, HOST_SIGNAL_ENV_VARS
            )
            self.assertEqual(plan.kind, "add")
            cross_ai_script.write_script(plan)
            script_path = os.path.join(tmp, ".planning", "scripts", "cross-ai.mjs")
            with open(script_path, "rb") as f:
                written = f.read()
            self.assertEqual(cross_ai_script.script_state(written), "pristine")
            # The self-test alone takes about 175 s and about 480 s beside the other e2e modules
            # on a host under memory pressure; 300 s timed out there (27-13 gate runs).
            reading = load_reading()
            proc = run_group(
                [node_bin, script_path, "--self-test"],
                guard_secs(RENDER_SELF_TEST_GUARD_SECS, load_factor(reading)),
                cwd=tmp,
                env={**runner_env(tmp), "AIKIT_XAI_SELFTEST_LOAD": repr(reading)},
            )
            self.assertEqual(proc.returncode, 0, msg=proc.stderr)
            assert_factor_printed(self, proc.stderr, reading)

    def test_rendered_deadline_below_timeout(self):
        node_bin = _real_node_executable()
        assert node_bin is not None
        with tempfile.TemporaryDirectory() as tmp:
            cfg_dir = os.path.join(tmp, ".planning")
            os.makedirs(cfg_dir, exist_ok=True)
            with open(os.path.join(cfg_dir, "config.json"), "w", encoding="utf-8") as f:
                json.dump({"workflow": {"cross_ai_timeout": 1800}}, f)
            plan = cross_ai_script.plan_script(
                tmp, self._artifact(), self._template, HOST_SIGNAL_ENV_VARS
            )
            cross_ai_script.write_script(plan)
            script_path = os.path.join(tmp, ".planning", "scripts", "cross-ai.mjs")
            proc = subprocess.run(
                [node_bin, script_path, "--print-argv"],
                cwd=tmp,
                env=runner_env(tmp),
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, msg=proc.stderr)
            match = re.search(r"cross-ai: deadline (\d+)s \(outer (\d+)s\)", proc.stderr)
            assert match is not None, proc.stderr
            self.assertEqual(int(match.group(2)), 1800)
            self.assertLess(int(match.group(1)), 1800)  # SPEC R6: strictly below the timeout


class TestRunnerDispatchE2E(unittest.TestCase):
    """run_runner drives the real template with a fake opencode."""

    def setUp(self):
        if _real_node_executable() is None:
            self.skipTest("node not on PATH: runner e2e skipped")
        if shutil.which("git") is None:
            self.skipTest("git not on PATH: runner e2e skipped")

    def _dispatch(self, tmp, model, repo):
        env = runner_env(tmp)
        env["FAKE_CALLS"] = os.path.join(tmp, "calls.log")
        write_fake_opencode(os.path.join(tmp, "bin"))
        lines: list[str] = []
        seams = RunnerSeams(env_fn=lambda: env, print_fn=lines.append)
        spec = RunnerSpec("opencode", model, "review", 30, cwd=repo)
        result = run_runner(spec, "hi", seams)
        return result, lines, env["FAKE_CALLS"]

    def test_review_ok(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = os.path.join(tmp, "repo")
            os.makedirs(repo)
            _git_init(repo)
            result, _lines, calls_path = self._dispatch(tmp, "fake/ok", repo)
            self.assertEqual(result.returncode, 0, msg="".join(_lines))
            self.assertIsNone(result.reason)
            assert result.status is not None
            self.assertEqual(result.status["status"], "ok")
            self.assertIn("done", result.stdout)
            self.assertNotIn("--child-pgid-file", result.argv)
            self.assertEqual(pids_with_cwd_under(tmp), [])
            with open(calls_path, encoding="utf-8") as handle:
                calls = handle.read()
            self.assertIn("opencode models", calls)
            self.assertIn("opencode fake/ok", calls)

    def test_review_bad_model(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = os.path.join(tmp, "repo")
            os.makedirs(repo)
            _git_init(repo)
            result, _lines, calls_path = self._dispatch(tmp, "fake/missing", repo)
            self.assertEqual(result.reason, "configuration")
            assert result.status is not None
            self.assertEqual(result.status["status"], "bad_model")
            with open(calls_path, encoding="utf-8") as handle:
                calls = [line.strip() for line in handle if line.strip()]
            self.assertTrue(calls)
            self.assertTrue(all(line.startswith("opencode models") for line in calls))

    def test_non_git_dir_dispatches(self):
        with tempfile.TemporaryDirectory() as tmp:
            scratch = os.path.join(tmp, "scratch")
            os.makedirs(scratch)
            env = runner_env(tmp)
            env["GIT_CEILING_DIRECTORIES"] = os.path.dirname(scratch)
            write_fake_opencode(os.path.join(tmp, "bin"))
            lines: list[str] = []
            seams = RunnerSeams(env_fn=lambda: env, print_fn=lines.append)
            spec = RunnerSpec("opencode", "fake/ok", "review", 30, cwd=scratch)
            result = run_runner(spec, "hi", seams)
            self.assertIsNone(result.reason, msg="".join(lines))
            assert result.status is not None
            self.assertEqual(result.status["status"], "ok")
            self.assertEqual(result.status["tree"], "unknown")
            self.assertTrue(any("is not inside a git work tree" in line for line in lines))
            self.assertEqual(pids_with_cwd_under(tmp), [])


_REVIEW_STATUSES = (
    ("fake/ok", None, "ok", [600]),
    ("fake/empty", "real_error", "empty_answer", [600]),
    ("fake/quota", "quota", "quota", [600]),
    ("fake/auth", "auth", "auth", [600]),
    ("fake/billing", "billing_or_access", "billing", [600]),
    ("fake/capacity", "capacity", "transient", [30]),
    ("fake/crash", "real_error", "crash", [600]),
    ("fake/hang", "timeout", "timeout", [3]),
    ("fake/missing", "configuration", "bad_model", [600]),
)


class TestReviewStatusesE2E(unittest.TestCase):
    """Every review status the map handles, through the real runner and a fake opencode."""

    def setUp(self):
        if _real_node_executable() is None:
            self.skipTest("node not on PATH: review status e2e skipped")
        if shutil.which("git") is None:
            self.skipTest("git not on PATH: review status e2e skipped")

    def _entry(self, model: str) -> dict:
        return {"key": "oc", "model": model, "vendor": "opencode", "runtime": "opencode"}

    def _review(self, tmp, model, tiers, cwd, env):
        write_fake_opencode(os.path.join(tmp, "bin"))
        lines: list[str] = []
        seams = ReviewerSeams(
            runner_seams=RunnerSeams(env_fn=lambda: env, print_fn=lines.append),
            codegraph_health_fn=lambda _runtime: False,
        )
        result = dispatch_reviewer(
            ReviewerDispatchSpec(self._entry(model), "hi", tiers, {}, cwd=cwd), seams,
        )
        return result, lines

    def test_each_review_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = os.path.join(tmp, "repo")
            os.makedirs(repo)
            _git_init(repo)
            env = runner_env(tmp)
            with open(os.path.join(repo, "a.txt"), encoding="utf-8") as handle:
                baseline = handle.read()
            for model, reason, status, tiers in _REVIEW_STATUSES:
                with self.subTest(model=model):
                    result, lines = self._review(tmp, model, tiers, repo, env)
                    self.assertEqual(result["reason"], reason, msg="".join(lines))
                    assert result["status"] is not None
                    self.assertEqual(result["status"]["status"], status)
                    with open(os.path.join(repo, "a.txt"), encoding="utf-8") as handle:
                        self.assertEqual(handle.read(), baseline)
                    self.assertEqual(pids_with_cwd_under(tmp), [])

    def test_non_git_dir_dispatches(self):
        with tempfile.TemporaryDirectory() as tmp:
            scratch = os.path.join(tmp, "scratch")
            os.makedirs(scratch)
            env = runner_env(tmp)
            env["GIT_CEILING_DIRECTORIES"] = os.path.dirname(scratch)
            result, lines = self._review(tmp, "fake/ok", [600], scratch, env)
            self.assertIsNone(result["reason"], msg="".join(lines))
            assert result["status"] is not None
            self.assertEqual(result["status"]["tree"], "unknown")
            self.assertTrue(any("is not inside a git work tree" in line for line in lines))
            self.assertEqual(pids_with_cwd_under(tmp), [])


class TestExecStatusesE2E(unittest.TestCase):
    """dispatch_execute runs a fake opencode exec through the real runner template."""

    def setUp(self):
        if _real_node_executable() is None:
            self.skipTest("node not on PATH: exec status e2e skipped")
        if shutil.which("git") is None:
            self.skipTest("git not on PATH: exec status e2e skipped")

    def _execute(self, tmp, model, target, timeout, env):
        write_fake_opencode(os.path.join(tmp, "bin"))
        lines: list[str] = []
        seams = ExecuteSeams(
            runner_seams=RunnerSeams(env_fn=lambda: env, print_fn=lines.append),
        )
        result = dispatch_execute(
            ExecuteDispatchSpec(
                {"runtime": "opencode", "model": model}, "do it", target, timeout,
            ),
            seams,
        )
        return result, lines

    def test_statuses(self):
        cases = (
            ("fake/nochange", "real_error", "no_change", 30),
            ("fake/empty", "real_error", "empty_answer", 30),
            ("fake/quota", "quota", "quota", 30),
            ("fake/auth", "auth", "auth", 30),
            ("fake/billing", "billing_or_access", "billing", 30),
            ("fake/capacity", "capacity", "transient", 30),
            ("fake/crash", "real_error", "crash", 30),
            ("fake/hang", "timeout", "timeout", 3),
            ("fake/missing", "configuration", "bad_model", 30),
        )
        with tempfile.TemporaryDirectory() as tmp:
            repo = os.path.join(tmp, "repo")
            os.makedirs(repo)
            _git_init(repo)
            env = runner_env(tmp)
            for model, reason, status, timeout in cases:
                with self.subTest(model=model):
                    result, lines = self._execute(tmp, model, repo, timeout, env)
                    self.assertEqual(result["reason"], reason, msg="".join(lines))
                    assert result["status"] is not None
                    self.assertEqual(result["status"]["status"], status)
                    self.assertEqual(pids_with_cwd_under(tmp), [])
            scratch = os.path.join(tmp, "scratch")
            os.makedirs(scratch)
            non_git = {**env, "GIT_CEILING_DIRECTORIES": os.path.dirname(scratch)}
            with self.subTest(model="non-git"):
                result, lines = self._execute(tmp, "fake/ok", scratch, 30, non_git)
                self.assertIsNone(result["reason"], msg="".join(lines))
                assert result["status"] is not None
                self.assertEqual(result["status"]["status"], "ok")
                self.assertEqual(result["status"]["tree"], "unknown")
                self.assertEqual(pids_with_cwd_under(tmp), [])

    def test_exec_ok(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = os.path.join(tmp, "repo")
            os.makedirs(repo)
            _git_init(repo)
            env = runner_env(tmp)
            result, lines = self._execute(tmp, "fake/ok", repo, 30, env)
            self.assertEqual(result["returncode"], 0, msg="".join(lines))
            self.assertIsNone(result["reason"])
            node_bin = shutil.which("node")
            self.assertTrue(result["command"].startswith(node_bin or ""), msg=result["command"])
            with open(os.path.join(repo, "a.txt"), encoding="utf-8") as handle:
                self.assertIn("oc", handle.read())
            self.assertEqual(pids_with_cwd_under(tmp), [])


def _codex_pair(message: str) -> str:
    return "\n".join((
        json.dumps({"type": "error", "message": message}),
        json.dumps({"type": "turn.failed", "error": {"message": message}}),
    ))


def _oc_error(error: dict) -> str:
    return json.dumps({"type": "error", "sessionID": "ses_1", "error": error})


class TestClassifyOnly(unittest.TestCase):
    """The shipped runner's --classify-only prints one JSON line per captured case."""

    def setUp(self):
        if _real_node_executable() is None:
            self.skipTest("node not on PATH: classify-only e2e skipped")

    def test_seven_cases_match_pinned_fields(self):
        node_bin = _real_node_executable()
        assert node_bin is not None
        curly = "You\u2019ve hit your usage limit. Try again later."
        cases = [
            {"name": "codex-curly", "cli": "codex", "stdout": _codex_pair(curly)},
            {
                "name": "oc-monthly-unknown", "cli": "opencode", "route": "unknown",
                "stdout": _oc_error({
                    "type": "provider.auth", "status": 401,
                    "response": {"body": json.dumps({"type": "MonthlyLimitError"})},
                }),
            },
            {
                "name": "oc-monthly-router", "cli": "opencode", "route": "router",
                "stdout": _oc_error({
                    "type": "provider.auth", "status": 401,
                    "response": {"body": json.dumps({"type": "MonthlyLimitError"})},
                }),
            },
            {
                "name": "pi-answer-only", "cli": "pi",
                "stdout": "You have hit your usage limit according to the model.",
            },
            {"name": "pi-4021", "cli": "pi", "stderr": "used 4021 tokens"},
            {
                "name": "cursor-usage", "cli": "cursor",
                "stderr": "ActionRequiredError: You've hit your usage limit",
            },
            {"name": "inferred", "cli": "pi", "model": "router-env/my-coding"},
        ]
        want = [
            {"status": "quota", "pattern": "verified"},
            {"status": "billing"},
            {"status": "quota"},
            {"status": "crash", "pattern": "none", "rule": "-"},
            {"status": "crash", "pattern": "none", "rule": "-"},
            {"status": "quota", "pattern": "unverified"},
            {"route": "router-inferred"},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "cases.json")
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(cases, handle)
            proc = run_group(
                [node_bin, TEMPLATE, "--classify-only", path],
                60, cwd=tmp, env=runner_env(tmp),
            )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        lines = [line for line in proc.stdout.splitlines() if line.strip()]
        self.assertEqual(len(lines), 7, msg=proc.stdout)
        parsed = [json.loads(line) for line in lines]
        unknown = parsed[1]
        router = parsed[2]
        self.assertEqual(unknown["status"], "billing")
        self.assertEqual(router["status"], "quota")
        self.assertEqual(unknown["rule"], router["rule"])
        for got, pinned in zip(parsed, want, strict=True):
            for key, value in pinned.items():
                self.assertEqual(got[key], value, msg=got)
        err_lines = [line for line in proc.stderr.splitlines() if line.strip()]
        self.assertTrue(err_lines, msg=proc.stderr)
        self.assertTrue(err_lines[-1].startswith("AIKIT-XAI status=ok"), msg=err_lines[-1])


class TestGsdHookE2E(unittest.TestCase):
    """The hook string, run through GSD's own run-with-timeout, drives the project runner."""

    def setUp(self):
        if _real_node_executable() is None:
            self.skipTest("node not on PATH: GSD hook e2e skipped")
        bash_bin = shutil.which("bash") or next(
            (p for p in ("/bin/bash", "/usr/bin/bash") if os.path.isfile(p)), None
        )
        if bash_bin is None:
            self.skipTest("bash not found: GSD hook e2e skipped")
        self.bash_bin = bash_bin
        gsd_tools = os.path.join(REPO_ROOT, ".claude", "gsd-core", "bin", "gsd-tools.cjs")
        if not os.path.isfile(gsd_tools):
            self.skipTest(f"GSD's gsd-tools.cjs is absent ({gsd_tools}): GSD hook e2e skipped")
        self.gsd_tools = gsd_tools

    def test_hook_as_gsd_runs_it(self):
        sys.path.insert(
            0, os.path.join(REPO_ROOT, "skills", "ai-kit-spec-execute-gsd")
        )
        from ai_kit_gsd_curated_config import cli as curated_cli
        from ai_kit_spec_gsd import cli as gsd_cli
        from ai_kit_spec_gsd.gsd_cross_ai import build_cross_ai_command

        with tempfile.TemporaryDirectory() as tmp:
            repo = os.path.join(tmp, "repo")
            os.makedirs(repo)
            _git_init(repo)
            env = runner_env(tmp)
            env["FAKE_CALLS"] = os.path.join(tmp, "calls.log")
            env["FAKE_STDIN"] = os.path.join(tmp, "bin", "stdin.log")
            write_fake_opencode(os.path.join(tmp, "bin"))
            out = io.StringIO()
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                rc = gsd_cli.main([
                    "print-dispatch-guidance", "--runtime", "opencode", "--model", "fake/ok",
                ], stdout=out)
            self.assertEqual(rc, 0, msg=err.getvalue())
            guidance = out.getvalue()
            self.assertTrue(guidance.strip())
            with (
                contextlib.redirect_stdout(io.StringIO()),
                mock.patch("sys.stdin", io.StringIO(guidance)),
            ):
                ensure_rc = curated_cli.main([
                    "ensure-runner", "--cwd", repo, "--guidance-file", "-",
                ])
            self.assertEqual(ensure_rc, 0)
            hook = build_cross_ai_command(
                {"runtime": "opencode", "model": "fake/ok", "key": "oc"}
            )
            assert hook is not None
            proc = subprocess.run(
                [self.bash_bin, "-c",
                 'echo "$P" | node "$GSD_TOOLS" run-with-timeout 60 -- ${CROSS_AI_CMD}'],
                cwd=repo, env={**env, "GSD_TOOLS": self.gsd_tools, "CROSS_AI_CMD": hook,
                               "P": "TASK-BODY"},
                capture_output=True, text=True, timeout=90, check=False,
            )
            self.assertEqual(proc.returncode, 0, msg=proc.stderr)
            self.assertIn("done", proc.stdout)
            with open(env["FAKE_STDIN"], encoding="utf-8") as handle:
                seen = handle.read()
            body = seen.find("TASK-BODY")
            self.assertGreater(body, 0)
            self.assertLess(seen.find("phase:"), body)
            self.assertIn("the current working directory (this project's root)", seen)
            self.assertNotIn("<executor_rules>", seen)
            self.assertEqual(pids_with_cwd_under(tmp), [])


def _route_catalog(cache_home: str) -> None:
    """A synthetic catalog: one confirmed router model, under a scratch cache home."""
    directory = os.path.join(cache_home, "ai-kit", "spec")
    os.makedirs(directory)
    raw = {
        "_meta": {"schema_version": 3},
        "vendor/fake": {
            "provider": "vendor",
            "runtimes": {"opencode": {"model_id": "fake/quota"}},
            "source": {},
            "confidence": "high",
            "last_verified": "2026-01-01",
            "fallback_quota": True,
            "heuristic_confirmed": ["fallback_quota"],
        },
    }
    with open(os.path.join(directory, "model-catalog.json"), "w", encoding="utf-8") as handle:
        json.dump(raw, handle)


class TestRouteFlagE2E(unittest.TestCase):
    """A confirmed catalog route reaches the real runner; no catalog leaves the heuristic."""

    def setUp(self):
        if _real_node_executable() is None:
            self.skipTest("node not on PATH: route flag e2e skipped")
        if shutil.which("git") is None:
            self.skipTest("git not on PATH: route flag e2e skipped")

    def _run(self, tmp, env):
        repo = os.path.join(tmp, "repo")
        os.makedirs(repo)
        _git_init(repo)
        write_fake_opencode(os.path.join(tmp, "bin"))
        lines: list[str] = []
        result = run_runner(
            RunnerSpec("opencode", "fake/quota", "review", 30, cwd=repo),
            "hi",
            RunnerSeams(env_fn=lambda: dict(env), print_fn=lines.append),
        )
        return result, lines

    def test_confirmed_route_reaches_the_runner(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = runner_env(tmp)
            env["XDG_CACHE_HOME"] = os.path.join(tmp, "cache")
            _route_catalog(env["XDG_CACHE_HOME"])
            result, lines = self._run(tmp, env)
            self.assertIn("--route-opencode", result.argv)
            self.assertEqual(
                result.argv[result.argv.index("--route-opencode") + 1], "router",
            )
            assert result.status is not None
            self.assertEqual(result.status["route"], "router")
            self.assertEqual(result.status["status"], "quota")
            self.assertEqual(result.reason, "quota")
            self.assertEqual(sum("cross-ai: report" in line for line in lines), 1)
            self.assertEqual(pids_with_cwd_under(tmp), [])

    def test_without_a_catalog_the_runner_uses_its_heuristic(self):
        with tempfile.TemporaryDirectory() as tmp:
            result, _lines = self._run(tmp, runner_env(tmp))
            self.assertFalse(any(token.startswith("--route-") for token in result.argv))
            assert result.status is not None
            self.assertEqual(result.status["route"], "unknown")
            self.assertEqual(result.status["status"], "quota")
            self.assertEqual(pids_with_cwd_under(tmp), [])


class TestRunnerDispatchNoNode(unittest.TestCase):
    def test_no_node_fails_closed(self):
        spawned: list[list[str]] = []

        def popen_fn(*_args, **_kwargs):
            spawned.append(["called"])
            raise AssertionError("popen must not be called without node")

        lines: list[str] = []
        seams = RunnerSeams(
            which_fn=lambda _name: None, popen_fn=popen_fn, print_fn=lines.append,
        )
        result = run_runner(RunnerSpec("opencode", "fake/ok", "review", 30), "hi", seams)
        self.assertEqual(result.reason, "dispatch_unavailable")
        self.assertEqual(spawned, [])
        self.assertTrue(any(
            "subprocess dispatch needs Node (node not found on PATH)" in line for line in lines
        ))


if __name__ == "__main__":
    unittest.main()
