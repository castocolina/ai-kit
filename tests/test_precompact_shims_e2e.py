"""Node-run e2e tests of the pi and opencode precompact shims (SPEC R6, R7; D-18).

Each test runs the repo's real ``.ts`` shims through
``tests/fixtures/precompact/run_shim.mjs`` with node's built-in TypeScript type
stripping. The hosts are faked by the harness; no test starts pi or opencode.
``AI_KIT_PYTHON`` points at this interpreter, the decision client at the stub,
and every XDG base at a fresh temp dir, so no test touches a real runtime dir.
The whole class skips only when node is absent or cannot strip types.
"""

import contextlib
import json
import os
import re
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
HARNESS = REPO / "tests" / "fixtures" / "precompact" / "run_shim.mjs"
PI_SHIM = REPO / "tools" / "hooks" / "pi" / "ai-kit-precompact.ts"
PI_ADVISOR_SHIM = REPO / "tools" / "hooks" / "pi" / "ai-kit-tool-advisor.ts"
PI_REMINDER_SHIM = REPO / "tools" / "hooks" / "pi" / "ai-kit-tool-reminder.ts"
PI_TOOL_FIXTURE = REPO / "tests" / "fixtures" / "advisor" / "pi_tool_result_bash.json"
OC_SHIM = REPO / "tools" / "hooks" / "opencode" / "ai-kit-precompact.ts"
PI_FIXTURE = REPO / "tests" / "fixtures" / "precompact" / "pi_preparation.json"
OC_FIXTURE = REPO / "tests" / "fixtures" / "precompact" / "opencode_messages.json"
STUB_CLIENT = REPO / "tests" / "fixtures" / "precompact" / "stub_client.py"
HEADER_FIRST_LINE = "<!-- ai-kit precompact v1 -->"


def _node_bin():
    """The real node binary, resolved under the caller's own env: a version-manager shim on
    PATH (Volta, asdf) needs the real HOME, which the scratch env replaces."""
    node = shutil.which("node")
    if node is None:
        return None
    real = subprocess.run([node, "-e", "process.stdout.write(process.execPath)"],
                          capture_output=True, text=True, check=False, timeout=30)
    return real.stdout.strip() if real.returncode == 0 and real.stdout.strip() else node


NODE = _node_bin()


def _node_ready():
    """Whether node is on PATH and its type stripping handles our syntax."""
    node = NODE
    if node is None:
        return False
    probe = subprocess.run(
        [node, "-e", "process.exit(process.features && process.features.typescript ? 0 : 1)"],
        capture_output=True, check=False, timeout=30)
    return probe.returncode == 0


class ShimHarnessMixin(unittest.TestCase):
    """Runs the shared node harness under a scratch env."""

    def _make_base(self):
        base = tempfile.mkdtemp(prefix="ai-kit-shim-e2e-")
        self.addCleanup(shutil.rmtree, base, ignore_errors=True)
        return base

    def _harness_env(self, base, extra=None):
        """Scratch env: temp HOME/XDG bases, this interpreter, the stub client."""
        paths = {
            "HOME": os.path.join(base, "home"),
            "XDG_RUNTIME_DIR": os.path.join(base, "run"),
            "XDG_CACHE_HOME": os.path.join(base, "cache"),
            "XDG_CONFIG_HOME": os.path.join(base, "config"),
            "XDG_STATE_HOME": os.path.join(base, "state"),
        }
        for path in paths.values():
            os.makedirs(path, exist_ok=True)
        os.chmod(paths["XDG_RUNTIME_DIR"], 0o700)
        env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), **paths,
               "AI_KIT_PYTHON": sys.executable,
               "AI_KIT_PRECOMPACT_CLIENT": str(STUB_CLIENT)}
        env.update(extra or {})
        return env

    def _run_harness(self, host, shim, fixture, base, mode=None, extra=None, timeout=60):
        """One harness run; returns (proc, env). The fixture may be a path or a
        dict (written into the base dir as a temp JSON file)."""
        if isinstance(fixture, dict):
            fixture_path = os.path.join(base, "fixture.json")
            with open(fixture_path, "w", encoding="utf-8") as handle:
                json.dump(fixture, handle)
        else:
            fixture_path = str(fixture)
        env = self._harness_env(base, extra)
        cmd = [NODE or "node", str(HARNESS), host, str(shim), fixture_path]
        if mode:
            cmd.append(mode)
        proc = subprocess.run(cmd, capture_output=True, text=True, cwd=str(REPO),
                              env=env, timeout=timeout, check=False)
        return proc, env

    @staticmethod
    def _compact_dir(env):
        return os.path.join(env["XDG_RUNTIME_DIR"], "ai-kit", "compact")

    def _write_interpreter_script(self, base, name, body):
        """A 0700 `#!/usr/bin/env python` script under `base`; never committed."""
        path = os.path.join(base, name)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(f"#!{sys.executable}\n" + body + "\n")
        os.chmod(path, stat.S_IRWXU)
        return path


@unittest.skipUnless(_node_ready(), "node with type stripping is not available")
class TestShimsE2E(ShimHarnessMixin, unittest.TestCase):
    """Every shim case runs node from PATH; failure cases cover both hosts."""

    HOSTS = (("pi", PI_SHIM, PI_FIXTURE), ("opencode", OC_SHIM, OC_FIXTURE))

    def _pi_fixture(self, **prep_overrides):
        """The recorded pi fixture with `preparation` fields overridden."""
        fixture = json.loads(PI_FIXTURE.read_text(encoding="utf-8"))
        fixture["preparation"].update(prep_overrides)
        return fixture

    def _oc_fixture(self, **overrides):
        """The recorded opencode fixture with top-level fields overridden."""
        fixture = json.loads(OC_FIXTURE.read_text(encoding="utf-8"))
        fixture.update(overrides)
        return fixture

    def test_shims_empty_input_gives_nothing(self):
        base = self._make_base()
        with self.subTest(host="pi"):
            proc, _env = self._run_harness(
                "pi", PI_SHIM, self._pi_fixture(messagesToSummarize=[]), base)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertEqual(proc.stdout.strip(), "null")
        with self.subTest(host="opencode"):
            proc, _env = self._run_harness(
                "opencode", OC_SHIM, self._oc_fixture(messages=[]), base)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            result = json.loads(proc.stdout)
            self.assertEqual(result["output"], {"context": ["prior plugin context"]})
            self.assertFalse(result["promptSet"])

    def test_shims_core_failure_gives_nothing(self):
        base = self._make_base()
        empty_exit0 = self._write_interpreter_script(
            base, "empty_exit0.py", "import sys\nsys.stdin.buffer.read()\n")
        cases = (("missing interpreter", {"AI_KIT_PYTHON": os.path.join(base, "no-python")}, None),
                 ("exit 0 empty stdout", {"AI_KIT_PYTHON": empty_exit0}, None),
                 ("backend down", None, "down"))
        for host, shim, fixture in self.HOSTS:
            for name, extra, probe in cases:
                with self.subTest(host=host, case=name):
                    merged = dict(extra or {})
                    if probe:
                        merged["STUB_PROBE"] = probe
                    proc, _env = self._run_harness(host, shim, fixture, base, extra=merged)
                    self.assertEqual(proc.returncode, 0, proc.stderr)
                    if host == "pi":
                        self.assertEqual(proc.stdout.strip(), "null")
                    else:
                        result = json.loads(proc.stdout)
                        self.assertEqual(result["output"],
                                         {"context": ["prior plugin context"]})
                        self.assertFalse(result["promptSet"])

    def test_shims_hanging_interpreter_killed(self):
        for host, shim, fixture in self.HOSTS:
            with self.subTest(host=host):
                base = self._make_base()
                pidfile = os.path.join(base, "sleeper.pid")
                script = self._write_interpreter_script(
                    base, "sleeper.py",
                    "import os, subprocess, sys, time\n"
                    f"with open({pidfile!r}, 'w', encoding='utf-8') as handle:\n"
                    "    child = subprocess.Popen([sys.executable, '-c',\n"
                    "        'import time; time.sleep(30)'])\n"
                    "    handle.write(f'{os.getpid()} {child.pid}')\n"
                    "time.sleep(30)\n")
                env = self._harness_env(base, {"AI_KIT_PYTHON": script})
                cmd = [NODE or "node", str(HARNESS), host, str(shim), str(fixture)]
                started = time.monotonic()
                proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                        text=True, cwd=str(REPO), env=env)
                timed_out = False
                stdout = ""
                try:
                    stdout, _stderr = proc.communicate(timeout=15)
                except subprocess.TimeoutExpired:
                    timed_out = True
                elapsed = time.monotonic() - started
                try:
                    self.assertFalse(timed_out)
                    self.assertGreaterEqual(elapsed, 9.5)
                    self.assertLessEqual(elapsed, 11.0)
                    if host == "pi":
                        self.assertEqual(stdout.strip(), "null")
                    else:
                        result = json.loads(stdout)
                        self.assertEqual(result["output"],
                                         {"context": ["prior plugin context"]})
                    with open(pidfile, encoding="utf-8") as handle:
                        pids = [int(pid) for pid in handle.read().split()]
                    for pid in pids:
                        with self.assertRaises(ProcessLookupError):
                            os.kill(pid, 0)
                finally:
                    if os.path.exists(pidfile):
                        try:
                            with open(pidfile, encoding="utf-8") as handle:
                                for pid in handle.read().split():
                                    os.kill(int(pid), signal.SIGKILL)
                        except (OSError, ValueError):
                            pass
                    if proc.poll() is None:
                        proc.kill()
                    proc.wait()

    def test_shims_text_encoding(self):
        weird = ("café_accents, 日本語_CJK, \U0001f680_emoji, "
                 "\x07_bell \x1b[31m_escape \x00_nul \x7f_del")
        pi_fixture = self._pi_fixture(messagesToSummarize=[{"role": "user",
                                                            "content": weird}])
        oc_fixture = self._oc_fixture(messages=[
            {"info": {"role": "user", "time": {"created": 1000}},
             "parts": [{"type": "text", "text": weird}]}])
        for host, shim, fixture in (("pi", PI_SHIM, pi_fixture),
                                    ("opencode", OC_SHIM, oc_fixture)):
            with self.subTest(host=host):
                base = self._make_base()
                proc, _env = self._run_harness(host, shim, fixture, base)
                self.assertEqual(proc.returncode, 0, proc.stderr)
                if host == "pi":
                    document = json.loads(proc.stdout)["compaction"]["summary"]
                else:
                    document = json.loads(proc.stdout)["output"]["context"][1]
                for marker in ("café_accents", "日本語_CJK", "\U0001f680_emoji"):
                    self.assertIn(marker, document)
                bad = [char for char in document
                       if (ord(char) < 0x20 and char not in "\n\t") or ord(char) == 0x7f]
                self.assertEqual(bad, [])

    def test_shims_self_contained(self):
        expected_exports = {"pi": ["default"], "opencode": ["AiKitPrecompact"]}
        expected_pi_files = {"ai-kit-precompact.ts", "ai-kit-tool-advisor.ts",
                             "ai-kit-tool-reminder.ts"}
        for host, shim, _fixture in self.HOSTS:
            with self.subTest(host=host):
                files = [path.name for path in shim.parent.iterdir()]
                if host == "pi":
                    self.assertEqual(set(files), expected_pi_files)
                else:
                    self.assertEqual(files, [shim.name])
                for line in shim.read_text(encoding="utf-8").splitlines():
                    if re.match(r"\s*import\b", line) and " from " in line:
                        self.assertIn('"node:', line, line)
                base = self._make_base()
                proc, _env = self._run_harness(host, shim, fixture_for(host), base,
                                               mode="exports")
                self.assertEqual(proc.returncode, 0, proc.stderr)
                self.assertEqual(json.loads(proc.stdout), expected_exports[host])
        for shim in (PI_ADVISOR_SHIM, PI_REMINDER_SHIM):
            with self.subTest(shim=shim.name):
                for line in shim.read_text(encoding="utf-8").splitlines():
                    if re.match(r"\s*import\b", line) and " from " in line:
                        self.assertIn('"node:', line, line)
                base = self._make_base()
                proc, _env = self._run_harness("pi-tool", shim, PI_TOOL_FIXTURE, base,
                                               mode="exports")
                self.assertEqual(proc.returncode, 0, proc.stderr)
                self.assertEqual(json.loads(proc.stdout), ["default"])

    def test_shims_symlinked_finds_core(self):
        base = self._make_base()
        for host, shim, fixture in self.HOSTS:
            with self.subTest(host=host):
                link = os.path.join(base, f"linked-{host}-{shim.name}")
                os.symlink(shim, link)
                proc, _env = self._run_harness(host, Path(link), fixture, base)
                self.assertEqual(proc.returncode, 0, proc.stderr)
                result = json.loads(proc.stdout)
                if host == "pi":
                    self.assertTrue(result["compaction"]["summary"])
                else:
                    self.assertEqual(len(result["output"]["context"]), 2)
        tool_bin = Path(base) / "tool-bin"
        tool_bin.mkdir()
        rg = tool_bin / "rg"
        rg.write_text("#!/bin/sh\\nexit 0\\n", encoding="utf-8")
        rg.chmod(0o700)
        for name, shim in (("advisor", PI_ADVISOR_SHIM), ("reminder", PI_REMINDER_SHIM)):
            with self.subTest(shim=name):
                link = os.path.join(base, f"linked-pi-tool-{shim.name}")
                os.symlink(shim, link)
                fixture = json.loads(PI_TOOL_FIXTURE.read_text(encoding="utf-8"))
                fixture["event"]["toolCallId"] = f"linked-{name}"
                fixture["ctx"]["sessionId"] = f"linked-{name}"
                proc, _env = self._run_harness("pi-tool", Path(link), fixture, base,
                                               extra={"PATH": str(tool_bin)})
                self.assertEqual(proc.returncode, 0, proc.stderr)
                self.assertIsNotNone(json.loads(proc.stdout))

    def test_pi_abort_returns_nothing(self):
        base = self._make_base()
        proc, _env = self._run_harness("pi", PI_SHIM, PI_FIXTURE, base, mode="abort",
                                       timeout=2)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout.strip(), "null")

    def test_pi_image_data_blanked_on_stdin(self):
        base = self._make_base()
        sink = os.path.join(base, "sink.bin")
        image_data = "A" * 200000
        fixture = self._pi_fixture(messagesToSummarize=[
            {"role": "user", "content": [
                {"type": "text", "text": "describe this image"},
                {"type": "image", "data": image_data},
            ]}])
        interpreter = self._write_interpreter_script(
            base, "sink.py",
            "import os, sys\n"
            "with open(os.environ['SINK_PATH'], 'wb') as handle:\n"
            "    handle.write(sys.stdin.buffer.read())\n"
            "raise SystemExit(1)\n")
        proc, _env = self._run_harness("pi", PI_SHIM, fixture, base,
                                      extra={"AI_KIT_PYTHON": interpreter,
                                             "SINK_PATH": sink})
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout.strip(), "null")
        with open(sink, "rb") as handle:
            piped = handle.read()
        self.assertNotIn(b"A" * 1000, piped)


def fixture_for(host):
    """The recorded fixture path of one host."""
    return PI_FIXTURE if host == "pi" else OC_FIXTURE


class TestToolAdvisorPiEntry(unittest.TestCase):
    """Python-only contract tests for advisor_core's pi entry."""

    def test_pi_entry_contract(self):
        fixture = json.loads(PI_TOOL_FIXTURE.read_text(encoding="utf-8"))
        data = {**fixture["event"], **fixture["ctx"], "kind": "advisor"}
        bin_dir = tempfile.mkdtemp(prefix="pi-core-path-")
        self.addCleanup(shutil.rmtree, bin_dir, ignore_errors=True)
        rg = Path(bin_dir) / "rg"
        rg.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        rg.chmod(0o700)
        cases: list[tuple[str, str, list[str], Path | None]] = [
            ("event", json.dumps(data), ["pi"], None),
            ("invalid JSON", "{", ["pi"], None),
            ("array", "[]", ["pi"], None),
            ("other argv", "{}", ["other"], None),
        ]
        with tempfile.TemporaryDirectory(prefix="pi-core-contract-") as base:
            hooks = Path(base) / "tools" / "hooks"
            shutil.copytree(REPO / "tools/hooks", hooks,
                            ignore=shutil.ignore_patterns("__pycache__", "pi", "opencode"))
            (hooks / "detect.py").write_text('raise RuntimeError("x")\\n', encoding="utf-8")
            cases.append(("raising sibling", json.dumps(data), ["pi"], hooks / "advisor_core.py"))
            for name, payload, argv, script in cases:
                with self.subTest(case=name):
                    target = script or REPO / "tools/hooks/advisor_core.py"
                    cmd = [sys.executable, "-S", str(target), *argv]
                    runtime_dir = Path(bin_dir) / "runtime"
                    runtime_dir.mkdir(mode=0o700, exist_ok=True)
                    env = {**os.environ, "PATH": bin_dir, "HOME": bin_dir,
                           "XDG_RUNTIME_DIR": str(runtime_dir), "XDG_CACHE_HOME": bin_dir,
                           "XDG_CONFIG_HOME": bin_dir, "XDG_STATE_HOME": bin_dir}
                    if script:
                        env["PYTHONPATH"] = str(hooks)
                    proc = subprocess.run(cmd, input=payload, text=True, capture_output=True,
                                          env=env, check=False, timeout=10)
                    self.assertEqual(proc.returncode, 0, proc.stderr)
                    self.assertEqual(proc.stderr, "")
                    result = json.loads(proc.stdout)
                    self.assertEqual(set(result), {"text"} if name == "event" else set())


@unittest.skipUnless(_node_ready(), "node with type stripping is not available")
class TestToolAdvisorShims(ShimHarnessMixin, unittest.TestCase):
    """pi tool_result adapters preserve results and fail open."""

    SHIMS = (("advisor", PI_ADVISOR_SHIM), ("reminder", PI_REMINDER_SHIM))

    def _fixture(self, **changes):
        data = json.loads(PI_TOOL_FIXTURE.read_text(encoding="utf-8"))
        data["event"].update(changes)
        return data

    def _run_tool(self, shim, fixture, base, mode=None, extra=None, timeout=60):
        return self._run_harness("pi-tool", shim, fixture, base, mode=mode, extra=extra,
                                 timeout=timeout)

    def _rg_path(self, base, include=True):
        bindir = Path(base) / "bin"
        bindir.mkdir(exist_ok=True)
        if include:
            tool = bindir / "rg"
            tool.write_text("#!/bin/sh\\nexit 0\\n", encoding="utf-8")
            tool.chmod(0o700)
        return str(bindir)

    def test_pi_advisor_tracer_appends_block(self):
        base = self._make_base()
        env = {"PATH": self._rg_path(base)}
        proc, _ = self._run_tool(PI_ADVISOR_SHIM, PI_TOOL_FIXTURE, base, extra=env)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        result = json.loads(proc.stdout)
        original = json.loads(PI_TOOL_FIXTURE.read_text(encoding="utf-8"))["event"]["content"]
        self.assertEqual(set(result), {"content"})
        self.assertEqual([json.dumps(item, sort_keys=True) for item in result["content"][:-1]],
                         [json.dumps(item, sort_keys=True) for item in original])
        self.assertEqual(result["content"][-1]["type"], "text")
        self.assertTrue(result["content"][-1]["text"].startswith("ai-kit advice: "))
        self.assertIn("rg -n", result["content"][-1]["text"])

    def test_pi_shims_register_only_tool_result(self):
        for name, shim in self.SHIMS:
            with self.subTest(shim=name):
                base = self._make_base()
                proc, _ = self._run_tool(shim, PI_TOOL_FIXTURE, base, mode="events")
                self.assertEqual(proc.returncode, 0, proc.stderr)
                self.assertEqual(json.loads(proc.stdout), ["tool_result"])

    def test_pi_reminder_counts(self):
        base = self._make_base()
        bindir = self._rg_path(base)
        for label, text, truncation, expected in (
                ("lines", "x\n" * 500, None, "printed 500 lines"),
                ("truncated", "short", {"truncated": True, "totalLines": 5000,
                                          "totalBytes": 300000}, "printed 5000 lines")):
            with self.subTest(case=label):
                event = self._fixture()
                event["event"]["toolCallId"] = f"reminder-{label}"
                event["ctx"]["sessionId"] = f"pi-reminder-{label}"
                event["event"]["content"] = [{"type": "text", "text": text}]
                if truncation:
                    event["event"]["details"] = {"truncation": truncation}
                    event["event"]["text"] = text
                proc, _ = self._run_tool(PI_REMINDER_SHIM, event, base,
                                         extra={"PATH": bindir})
                self.assertEqual(proc.returncode, 0, proc.stderr)
                self.assertIn(expected, json.loads(proc.stdout)["content"][-1]["text"])

    def test_pi_shims_hanging_interpreter_killed(self):
        for name, shim in self.SHIMS:
            with self.subTest(shim=name):
                base = self._make_base()
                pidfile = Path(base) / "sleeper.pid"
                script = self._write_interpreter_script(
                    base, "sleeping-python",
                    "import os, time\n"
                    f"open({str(pidfile)!r}, 'w', encoding='utf-8').write(str(os.getpid()))\n"
                    "time.sleep(30)")
                started = time.monotonic()
                try:
                    proc, _ = self._run_tool(shim, PI_TOOL_FIXTURE, base,
                                             extra={"PATH": self._rg_path(base),
                                                    "AI_KIT_PYTHON": script}, timeout=8)
                    elapsed = time.monotonic() - started
                    self.assertEqual(proc.returncode, 0, proc.stderr)
                    self.assertEqual(proc.stdout.strip(), "null")
                    self.assertGreaterEqual(elapsed, 1.8)
                    self.assertLess(elapsed, 4)
                    pid = int(pidfile.read_text(encoding="utf-8"))
                    with self.assertRaises(ProcessLookupError):
                        os.kill(pid, 0)
                finally:
                    if pidfile.exists():
                        with contextlib.suppress(OSError, ValueError):
                            os.kill(int(pidfile.read_text(encoding="utf-8")), signal.SIGKILL)

    def test_pi_shims_silent_cases(self):
        for name, shim in self.SHIMS:
            cases = [("no rg", {}, {"PATH": self._rg_path(tempfile.mkdtemp(), False)}),
                     ("other tool", {"toolName": "edit"}, {"PATH": os.environ.get("PATH", "")}),
                     ("missing python", {}, {"PATH": os.environ.get("PATH", ""),
                                               "AI_KIT_PYTHON": "/missing/python"})]
            for label, changes, extra in cases:
                with self.subTest(shim=name, case=label):
                    base = self._make_base()
                    proc, _ = self._run_tool(shim, self._fixture(**changes), base, extra=extra)
                    self.assertEqual(proc.returncode, 0, proc.stderr)
                    self.assertEqual(proc.stdout.strip(), "null")

    def test_pi_shims_empty_content(self):
        for name, shim in self.SHIMS:
            with self.subTest(shim=name):
                base = self._make_base()
                event = self._fixture()
                event["event"]["toolCallId"] = f"empty-{name}"
                event["ctx"]["sessionId"] = f"pi-empty-{name}"
                event["event"]["content"] = []
                if name == "reminder":
                    event["event"]["text"] = "x\n" * 500
                    event["event"]["details"] = {"truncation": {"truncated": True,
                                               "totalLines": 500, "totalBytes": 1000}}
                proc, _ = self._run_tool(shim, event, base,
                                         extra={"PATH": self._rg_path(base)})
                self.assertEqual(proc.returncode, 0, proc.stderr)
                result = json.loads(proc.stdout)
                self.assertEqual(len(result["content"]), 1)
                self.assertEqual(result["content"][0]["type"], "text")

    def test_pi_advisor_large_read(self):
        with tempfile.TemporaryDirectory(prefix="pi-read-") as directory:
            path = Path(directory) / "large.py"
            path.write_text("line\n" * 3000, encoding="utf-8")
            for raw_path in (str(path), path.name):
                with self.subTest(path=raw_path):
                    base = self._make_base()
                    event = self._fixture(toolName="read", input={"path": raw_path})
                    event["ctx"]["cwd"] = directory
                    proc, _ = self._run_tool(PI_ADVISOR_SHIM, event, base,
                                             extra={"PATH": self._rg_path(base)})
                    self.assertEqual(proc.returncode, 0, proc.stderr)
                    result = json.loads(proc.stdout)
                    self.assertIn("3000 lines", result["content"][-1]["text"])
            base = self._make_base()
            limited = self._fixture(toolName="read", input={"path": str(path), "limit": 20})
            proc, _ = self._run_tool(PI_ADVISOR_SHIM, limited, base,
                                     extra={"PATH": self._rg_path(base)})
            self.assertEqual(proc.stdout.strip(), "null")

    def test_pi_advisor_and_reminder_dedupe(self):
        for order in ((PI_ADVISOR_SHIM, PI_REMINDER_SHIM),
                      (PI_REMINDER_SHIM, PI_ADVISOR_SHIM)):
            for label, output, truncation in (
                    ("short", "x\n" * 20, None),
                    ("large", "x\n" * 500, None),
                    ("truncated", "short", {"truncated": True,
                                                "totalLines": 5000,
                                                "totalBytes": 300000})):
                with self.subTest(order=[shim.name for shim in order], case=label):
                    base = self._make_base()
                    event = self._fixture()
                    event["event"]["toolCallId"] = f"dedupe-{label}"
                    event["ctx"]["sessionId"] = "dedupe-session"
                    event["event"]["content"] = [{"type": "text", "text": output}]
                    if truncation:
                        event["event"]["details"] = {"truncation": truncation}
                        event["event"]["text"] = output
                    current = event
                    for shim in order:
                        proc, _ = self._run_tool(shim, current, base,
                                                 extra={"PATH": self._rg_path(base)})
                        result = json.loads(proc.stdout)
                        if result is not None:
                            current = {"event": {**event["event"],
                                                  "content": result["content"]},
                                       "ctx": event["ctx"]}
                    blocks = current["event"]["content"]
                    advice = [block["text"] for block in blocks if isinstance(block, dict)
                              and block.get("type") == "text"
                              and block.get("text", "").startswith("ai-kit ")]
                    self.assertEqual(len(advice), 1)
                    self.assertIn("rg", advice[0])

    def test_pi_shims_keep_structured_content(self):
        base = self._make_base()
        event = self._fixture()
        event["event"]["structuredContent"] = {"k": 1}
        proc, _ = self._run_tool(PI_ADVISOR_SHIM, event, base,
                                 extra={"PATH": self._rg_path(base)})
        self.assertEqual(json.loads(proc.stdout)["structuredContent"], {"k": 1})


class TestPiTracer(ShimHarnessMixin, unittest.TestCase):
    """Task 1 tracer: a recorded pi preparation through the repo shim."""

    def test_pi_tracer_summary_returned(self):
        base = self._make_base()
        proc, env = self._run_harness("pi", PI_SHIM, PI_FIXTURE, base)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        result = json.loads(proc.stdout)
        self.assertIsNotNone(result)
        compaction = result["compaction"]
        summary = compaction["summary"]
        self.assertIsInstance(summary, str)
        self.assertLessEqual(len(summary), 9500)
        # After the header the pinned previous summary comes first.
        body = summary.split("\n---\n", 1)[1]
        self.assertTrue(body.startswith("[previous summary]\nEarlier compacted summary:"))
        self.assertEqual(compaction["firstKeptEntryId"], "e42")
        self.assertEqual(compaction["tokensBefore"], 123456)
        self.assertEqual(set(compaction["details"]),
                         {"total", "classified", "keep", "summarize",
                          "discard", "unclassified"})
        # The kept messages are classified and present; the compactionSummary
        # role is skipped and the unknown role is counted, not raised on.
        self.assertIn("[user]", summary)
        self.assertIn("$ pnpm test tokenizer", summary)
        self.assertNotIn("Superseded summary text", summary)
        header = summary.split("\n---\n", 1)[0]
        self.assertIn("unknown_type 1", header)
        self.assertIn("host: pi", header)
        self.assertIn("session_id: pi-sess-1", header)
        # The private file is written and deleted within the same call.
        leftovers = [name for name in os.listdir(self._compact_dir(env))
                     if name.endswith("-compact.md")]
        self.assertEqual(leftovers, [])


class TestOpencodeTracer(ShimHarnessMixin, unittest.TestCase):
    """Task 2 tracer: a recorded opencode session through the repo plugin."""

    def test_opencode_tracer_pushes_once(self):
        base = self._make_base()
        proc, env = self._run_harness("opencode", OC_SHIM, OC_FIXTURE, base)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        result = json.loads(proc.stdout)
        self.assertFalse(result["promptSet"])
        context = result["output"]["context"]
        self.assertEqual(len(context), 2)
        self.assertEqual(context[0], "prior plugin context")
        summary = context[1]
        self.assertTrue(summary.startswith(HEADER_FIRST_LINE))
        self.assertLessEqual(len(summary), 9500)
        # Only the part after the last boundary is summarized; dropped parts.
        self.assertNotIn("earlier segment", summary)
        self.assertNotIn("hidden reasoning", summary)
        self.assertNotIn("before the last compaction", summary)
        self.assertNotIn("data:", summary)
        self.assertNotIn("U1RPUkFHSUVTREVG", summary)
        # Completed, not-yet-compacted tool output is kept to its head lines.
        self.assertIn("line one of store.py", summary)
        self.assertNotIn("line six past the head", summary)
        self.assertIn("host: opencode", header_of(summary))
        leftovers = [name for name in os.listdir(self._compact_dir(env))
                     if name.endswith("-compact.md")]
        self.assertEqual(leftovers, [])

    def test_opencode_messages_failure_untouched(self):
        base = self._make_base()
        for mode in ("throw", "hang", "array"):
            with self.subTest(mode=mode):
                proc, _env = self._run_harness("opencode", OC_SHIM, OC_FIXTURE, base,
                                               mode=mode,
                                               timeout=12 if mode == "hang" else 60)
                self.assertEqual(proc.returncode, 0, proc.stderr)
                result = json.loads(proc.stdout)
                self.assertFalse(result["promptSet"])
                expected = 2 if mode == "array" else 1
                self.assertEqual(len(result["output"]["context"]), expected)
                self.assertEqual(result["output"]["context"][:1], ["prior plugin context"])

    def test_opencode_messages_hang_finishes_within_11s(self):
        base = self._make_base()
        started = time.monotonic()
        proc, _env = self._run_harness("opencode", OC_SHIM, OC_FIXTURE, base,
                                       mode="hang", timeout=15)
        elapsed = time.monotonic() - started
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertLess(elapsed, 11.0)

    def test_opencode_two_events_push_twice(self):
        base = self._make_base()
        proc, _env = self._run_harness("opencode", OC_SHIM, OC_FIXTURE, base, mode="twice")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        result = json.loads(proc.stdout)
        context = result["output"]["context"]
        self.assertEqual(len(context), 3)
        self.assertTrue(context[1].startswith(HEADER_FIRST_LINE))
        self.assertTrue(context[2].startswith(HEADER_FIRST_LINE))
        self.assertFalse(result["promptSet"])


def header_of(document):
    """The header block of a pre-summary document."""
    return document.split("\n---\n", 1)[0]
