"""Unit tests of the host-neutral pre-summary core (SPEC R1-R4; D-15, D-16).

The core is loaded by path (it is runnable as ``python3 -S`` but not importable
by name from the tests package). Every test points AI_KIT_PRECOMPACT_CLIENT at
the env-driven stub client, so no test reaches the real client, a real backend
or a real runtime dir: HOME and every XDG base live under a fresh temp dir.
"""

import importlib.util
import os
import shutil
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CORE_PATH = REPO / "tools" / "hooks" / "precompact_core.py"
STUB_PATH = REPO / "tests" / "fixtures" / "precompact" / "stub_client.py"


def load_core():
    """The core module, loaded by path."""
    spec = importlib.util.spec_from_file_location("precompact_core_under_test",
                                                  str(CORE_PATH))
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


core = load_core()


class CoreEnvMixin:
    """A scratch env: every base under a fresh temp dir, the stub as the client."""

    def make_env(self, tmp=None, **extra):
        base = tmp or tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, base, ignore_errors=True)
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
        env = dict(paths)
        env["AI_KIT_PRECOMPACT_CLIENT"] = str(STUB_PATH)
        env.update(extra)
        return env

    def make_meta(self, session_id="sess-1", env=None):
        """The meta dict presummarize expects; config_home lives in the private dir."""
        directory = core.private_dir(env) if env else "/nonexistent"
        return {"session_id": session_id, "host": "claude",
                "skipped": {"malformed": 0, "unknown_type": 0, "boundary_unrecognized": 0,
                            "dropped_before_classify": 0},
                "started": core._monotonic(),
                "config_home": os.path.join(directory, ".no-config")}


class TestTracerCorePresummarize(CoreEnvMixin, unittest.TestCase):
    """Task 1 tracer: six host-neutral messages through the stub's label cycle."""

    @staticmethod
    def _pad(role, text, fraction, tools=()):
        """A message whose rendered form takes ~`fraction` of the chunk state budget,
        so chunk boundaries are deterministic without hardcoding character counts."""
        overhead = core.request_state_chars(core.build_request("0" * 40, "c0000", ""))
        budget = core.CHUNK_STATE_CHARS - overhead
        message = {"role": role, "text": text, "tools": list(tools)}
        while len(core.render_message(message)) < int(budget * fraction):
            message["text"] += "x"
        return message

    def _messages(self):
        """Five chunks across three adjacency groups: [m0], [m1+m2], [m3], [m4], [m5]."""
        return [
            self._pad("user", "alpha text ", 0.2),
            self._pad("assistant", "beta plan ", 0.85, ["Read"]),
            {"role": "tool", "text": "gamma result", "tools": []},
            self._pad("user", "delta request ", 0.85),
            self._pad("assistant", "epsilon note ", 0.85),
            self._pad("user", "zeta final ", 0.85),
        ]

    def test_tracer_core_presummarize(self):
        env = self.make_env(STUB_LABEL_CYCLE="keep,summarize,discard")
        meta = self.make_meta(env=env)
        messages = self._messages()
        self.assertEqual(len(core.chunk_messages(messages)), 5)
        document = core.presummarize(messages, meta, env)
        self.assertIsNotNone(document)
        header = document.split("\n---\n", 1)[0]
        self.assertIn("chunks: 5 total, 5 classified, keep 2, summarize 2, "
                      "discard 1, unclassified 0", header)
        # Kept chunks appear verbatim (rendered form included).
        self.assertIn("[user]\nalpha text", document)
        # A summarize chunk appears as its first non-empty lines only: the tool
        # result body below the second line is cut.
        self.assertIn("[assistant] Read\nbeta plan", document)
        self.assertNotIn("gamma result", document)
        self.assertIn("[assistant]\nepsilon note", document)
        self.assertIn("[user]\nzeta final", document)
        # The discarded chunk's text is absent.
        self.assertNotIn("delta request", document)


if __name__ == "__main__":
    unittest.main()
