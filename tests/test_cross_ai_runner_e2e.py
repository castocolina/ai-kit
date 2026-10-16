"""E2E tier: real node and git, hermetic env for the cross-AI runner template."""

from __future__ import annotations

import glob
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, "skills", "ai-kit-gsd-curated-config"))
sys.path.insert(0, os.path.join(REPO_ROOT, "skills", "ai-kit-spec-review"))

from ai_kit_gsd_curated_config import cross_ai_script
from ai_kit_spec.detection import HOST_SIGNAL_ENV_VARS
from ai_kit_spec.reviewer_dispatch import (
    ReviewerDispatchSpec,
    ReviewerSeams,
    dispatch_reviewer,
)
from ai_kit_spec.runner_dispatch import RunnerSeams, RunnerSpec, run_runner


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

TEMPLATE = os.path.join(
    REPO_ROOT, "skills", "ai-kit-spec-review", "references", "cross-ai.mjs"
)


def runner_env(tmp: str) -> dict[str, str]:
    """Hermetic env matching cross-ai.mjs --self-test (fakes + node + git only)."""
    bin_dir = os.path.join(tmp, "bin")
    os.makedirs(bin_dir, exist_ok=True)
    node_bin = _real_node_executable()
    git_bin = shutil.which("git")
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


def run_group(argv: list[str], timeout: int, **kwargs) -> subprocess.CompletedProcess:
    """`subprocess.run` in a new session; a timeout kills the whole group, not just the
    leader, so no fake CLI outlives the test."""
    with subprocess.Popen(
        argv,
        start_new_session=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        **kwargs,
    ) as proc:
        try:
            out, err = proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            out, err = proc.communicate()
            raise
        return subprocess.CompletedProcess(argv, proc.returncode, out, err)


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
process.stdin.on('data', () => {}).on('end', () => {
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
        with tempfile.TemporaryDirectory() as tmp:
            proc = run_group(
                [node_bin, TEMPLATE, "--self-test"], 180, cwd=REPO_ROOT, env=runner_env(tmp)
            )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        self.assertIn("self-test ok", proc.stdout)

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
                "prefer": ["pi", "cursor"],
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
            proc = run_group(
                [node_bin, script_path, "--self-test"], 180, cwd=tmp, env=runner_env(tmp)
            )
            self.assertEqual(proc.returncode, 0, msg=proc.stderr)

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
    ("fake/capacity", "capacity", "capacity", [600]),
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
