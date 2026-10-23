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
import shutil
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


def _node_ready():
    """Whether node is on PATH and its type stripping handles our syntax."""
    node = shutil.which("node")
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
        cmd = ["node", str(HARNESS), host, str(shim), fixture_path]
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
