"""Node-run e2e tests of the pi and opencode precompact shims (SPEC R6, R7; D-18).

Each test runs the repo's real ``.ts`` shims through
``tests/fixtures/precompact/run_shim.mjs`` with node's built-in TypeScript type
stripping. The hosts are faked by the harness; no test starts pi or opencode.
``AI_KIT_PYTHON`` points at this interpreter, the decision client at the stub,
and every XDG base at a fresh temp dir, so no test touches a real runtime dir.
The whole class skips only when node is absent or cannot strip types.
"""

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
                    "import os, sys\n"
                    f"with open({pidfile!r}, 'w', encoding='utf-8') as handle:\n"
                    "    handle.write(str(os.getpid()))\n"
                    "os.execv(sys.executable,\n"
                    "    [sys.executable, '-c', 'import time; time.sleep(30)'])\n")
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
                        sleeper = int(handle.read().strip())
                    with self.assertRaises(ProcessLookupError):
                        os.kill(sleeper, 0)
                finally:
                    if os.path.exists(pidfile):
                        try:
                            with open(pidfile, encoding="utf-8") as handle:
                                os.kill(int(handle.read().strip()), signal.SIGKILL)
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
        for host, shim, _fixture in self.HOSTS:
            with self.subTest(host=host):
                files = [path.name for path in shim.parent.iterdir()]
                self.assertEqual(files, [shim.name])
                for line in shim.read_text(encoding="utf-8").splitlines():
                    if re.match(r"\s*import\b", line) and " from " in line:
                        self.assertIn('"node:', line, line)
                base = self._make_base()
                proc, _env = self._run_harness(host, shim, fixture_for(host), base,
                                               mode="exports")
                self.assertEqual(proc.returncode, 0, proc.stderr)
                self.assertEqual(json.loads(proc.stdout), expected_exports[host])

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
        self.assertEqual(result["calls"], 1)
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
        self.assertEqual(result["calls"], 2)
        context = result["output"]["context"]
        self.assertEqual(len(context), 3)
        self.assertTrue(context[1].startswith(HEADER_FIRST_LINE))
        self.assertTrue(context[2].startswith(HEADER_FIRST_LINE))
        self.assertFalse(result["promptSet"])


def header_of(document):
    """The header block of a pre-summary document."""
    return document.split("\n---\n", 1)[0]
