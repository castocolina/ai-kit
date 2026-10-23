"""Unit tests of the host-neutral pre-summary core (SPEC R1-R4; D-15, D-16).

The core is loaded by path (it is runnable as ``python3 -S`` but not importable
by name from the tests package). Every test points AI_KIT_PRECOMPACT_CLIENT at
the env-driven stub client, so no test reaches the real client, a real backend
or a real runtime dir: HOME and every XDG base live under a fresh temp dir.
"""

import importlib.util
import json
import os
import random
import re
import shutil
import subprocess
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

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

_COUNTS_RE = re.compile(r"chunks: (\d+) total, (\d+) classified, keep (\d+), "
                        r"summarize (\d+), discard (\d+), unclassified (\d+)")


class CoreEnvMixin(unittest.TestCase):
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

    def stub_log_lines(self, env):
        """The stub call log when STUB_LOG was set for this env."""
        with open(env["STUB_LOG"], encoding="utf-8") as handle:
            return [json.loads(line) for line in handle if line.strip()]

    @staticmethod
    def header_counts(document):
        """The six header counts of a document as a dict."""
        match = _COUNTS_RE.search(document)
        assert match is not None
        keys = ("total", "classified", "keep", "summarize", "discard", "unclassified")
        return dict(zip(keys, (int(g) for g in match.groups()), strict=True))

    @staticmethod
    def synthetic_transcript(base, lines):
        """A minimal synthetic transcript file under `base`; its absolute path."""
        path = os.path.join(base, "transcript.jsonl")
        with open(path, "w", encoding="utf-8") as handle:
            for index, text in enumerate(lines):
                handle.write(json.dumps({"type": "user", "timestamp": f"t{index}",
                                         "message": {"role": "user",
                                                     "content": text}}) + "\n")
        return path

    @staticmethod
    def pad_message(role, text, fraction, tools=()):
        """A message whose rendered form takes ~`fraction` of the chunk state
        budget, so chunk boundaries are deterministic without hardcoded counts."""
        overhead = core.request_state_chars(core.build_request("0" * 40, "c0000", ""))
        budget = core.CHUNK_STATE_CHARS - overhead
        message = {"role": role, "text": text, "tools": list(tools)}
        while len(core.render_message(message)) < int(budget * fraction):
            message["text"] += "x"
        return message

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

    def _messages(self):
        """Five chunks across three adjacency groups: [m0], [m1+m2], [m3], [m4], [m5]."""
        pad = self.pad_message
        return [
            pad("user", "alpha text ", 0.2),
            pad("assistant", "beta plan ", 0.85, ["Read"]),
            {"role": "tool", "text": "gamma result", "tools": []},
            pad("user", "delta request ", 0.85),
            pad("assistant", "epsilon note ", 0.85),
            pad("user", "zeta final ", 0.85),
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


class TestHeaderCounts(CoreEnvMixin, unittest.TestCase):
    """Header counts equal the classified chunks per label exactly (SPEC R1)."""

    CYCLE = ("keep", "summarize", "discard")

    def _chunk_messages(self, count):
        return [self.pad_message("user", f"MARK-{i:02d} ", 0.85) for i in range(count)]

    def test_header_counts_match_stub_labels(self):
        env = self.make_env(STUB_LABEL_CYCLE="keep,summarize,discard",
                            STUB_LOG=os.path.join(tempfile.mkdtemp(), "stub.log"))
        messages = self._chunk_messages(40)
        chunks = core.chunk_messages(messages)
        self.assertEqual(len(chunks), 40)
        document = core.presummarize(messages, self.make_meta(env=env), env)
        expected = {label: sum(1 for i in range(len(chunks))
                               if self.CYCLE[i % 3] == label) for label in self.CYCLE}
        counts = self.header_counts(document)
        self.assertEqual(counts["total"], 40)
        self.assertEqual(counts["classified"], 40)
        self.assertEqual(counts["unclassified"], 0)
        for label in self.CYCLE:
            self.assertEqual(counts[label], expected[label], label)

    def test_header_counts_property(self):
        rng = random.Random(42)
        messages = self._chunk_messages(40)
        chunks = core.chunk_messages(messages)
        self.assertEqual(len(chunks), 40)
        ids = [f"c{i:04d}" for i in range(len(chunks))]
        for _trial in range(50):
            mapping = {identifier: rng.choice(self.CYCLE) for identifier in ids}
            errored = set(rng.sample(ids, rng.randrange(0, 4)))
            env = self.make_env(STUB_LABELS=json.dumps(mapping),
                                STUB_ERROR_IDS=",".join(sorted(errored)))
            document = core.presummarize(messages, self.make_meta(env=env), env)
            counts = self.header_counts(document)
            self.assertEqual(counts["total"], len(chunks))
            self.assertEqual(counts["unclassified"], len(errored))
            self.assertEqual(counts["classified"], len(chunks) - len(errored))
            for label in self.CYCLE:
                expected = sum(1 for identifier in ids
                               if identifier not in errored
                               and mapping[identifier] == label)
                self.assertEqual(counts[label], expected, (label, mapping, errored))


class TestChunking(CoreEnvMixin, unittest.TestCase):
    """Chunk-boundary and adjacency edges (SPEC R1)."""

    @staticmethod
    def _grown_message(role, text, tools=()):
        """A message grown until its rendered form just fits one chunk."""
        message = {"role": role, "text": text, "tools": list(tools)}
        while core.fits(core.render_message(message)):
            message["text"] += "x"
        message["text"] = message["text"][:-1]
        return message

    def test_chunk_limit_boundary(self):
        message = self._grown_message("user", "l0\nl1\nl2\n")
        rendered = core.render_message(message)
        self.assertTrue(core.fits(rendered))
        self.assertEqual(core.chunk_messages([message]), [rendered])
        # One character more: the message no longer fits and splits at line
        # boundaries, never mid-line.
        bigger = dict(message, text=message["text"] + "x")
        rendered_more = core.render_message(bigger)
        self.assertFalse(core.fits(rendered_more))
        parts = core.chunk_messages([bigger])
        self.assertGreater(len(parts), 1)
        self.assertEqual("\n".join(parts), rendered_more)
        for part in parts:
            for line in part.split("\n"):
                self.assertIn(line, rendered_more.split("\n"))

    def test_chunk_overlong_line_cut_with_marker(self):
        message = {"role": "user", "text": "y" * 8000, "tools": []}
        chunks = core.chunk_messages([message])
        # A cut line loses its tail (that is what the marker counts); the head
        # lines before it still rejoin whole.
        cut_chunk = next(chunk for chunk in chunks if " [cut " in chunk)
        self.assertTrue(core.fits(cut_chunk))
        marker_start = cut_chunk.rfind(" [cut ")
        marker = cut_chunk[marker_start:]
        self.assertRegex(marker, r"^ \[cut \d+ chars\]$")
        cut = int(marker[len(" [cut "):-len(" chars]")])
        prefix = len(cut_chunk) - len(marker)
        self.assertEqual(prefix + cut, len(message["text"]))

    def test_chunk_tool_results_stay_together(self):
        pad = self.pad_message
        earlier = pad("user", "earlier turn ", 0.85)
        assistant = pad("assistant", "the plan ", 0.7, ["Read", "Bash"])
        tool_a = {"role": "tool", "text": "RESULT-A output", "tools": []}
        tool_b = {"role": "tool", "text": "RESULT-B output", "tools": []}
        chunks = core.chunk_messages([earlier, assistant, tool_a, tool_b])
        self.assertEqual(len(chunks), 2)
        self.assertTrue(chunks[1].startswith("[assistant] Read, Bash\n"))
        self.assertIn("RESULT-A output", chunks[1])
        self.assertIn("RESULT-B output", chunks[1])


class TestCoreEdges(CoreEnvMixin, unittest.TestCase):
    """Empty, encoding, ordering, concurrency and budget edges of the core."""

    def test_zero_messages_no_file(self):
        env = self.make_env(STUB_LOG=os.path.join(tempfile.mkdtemp(), "stub.log"))
        self.assertIsNone(core.presummarize([], self.make_meta(env=env), env))
        self.assertFalse(os.path.exists(env["STUB_LOG"]))

    def test_unicode_survives_and_slug_ascii(self):
        env = self.make_env()
        text = "café análisis 中文 🚀 end marker"
        document = core.presummarize(
            [{"role": "user", "text": text, "tools": []}],
            self.make_meta(env=env), env)
        self.assertIsNotNone(document)
        self.assertIn(text, document)
        self.assertIn(text.encode("utf-8"), document.encode("utf-8"))
        slug = core.slugify("Proyecto Ñandú 🚀")
        self.assertNotEqual(slug, "")
        self.assertRegex(slug, r"^[A-Za-z0-9._-]+$")

    def test_chunks_chronological(self):
        env = self.make_env(STUB_LABEL_CYCLE="keep")
        messages = [self.pad_message("user", f"MARK-{i:02d} ", 0.85) for i in range(6)]
        document = core.presummarize(messages, self.make_meta(env=env), env)
        self.assertIsNotNone(document)
        positions = [document.index(f"MARK-{i:02d}") for i in range(6)]
        self.assertEqual(positions, sorted(positions))

    def test_two_sessions_distinct_files(self):
        env = self.make_env()
        base = os.path.dirname(env["HOME"])
        transcript = self.synthetic_transcript(base, ["turn one", "turn two"])
        cwd = os.path.join(base, "proj")
        os.makedirs(cwd)
        paths = [core.run_claude({"session_id": session_id,
                                  "transcript_path": transcript, "cwd": cwd}, env)
                 for session_id in ("s-a", "s-b")]
        directory = core.private_dir(env)
        self.assertIsNotNone(directory)
        names = sorted(os.listdir(directory))
        self.assertEqual(len(names), 2, names)
        self.assertEqual({os.path.dirname(path) for path in paths}, {directory})
        headers = {core.read_header(os.path.join(directory, name))["session_id"]
                   for name in names}
        self.assertEqual(headers, {"s-a", "s-b"})

    def test_chunk_max_chunks_dropped_counted(self):
        env = self.make_env(STUB_LOG=os.path.join(tempfile.mkdtemp(), "stub.log"))
        messages = [self.pad_message("user", f"OLD-{i} ", 0.85) for i in range(5)]
        with mock.patch.object(core, "MAX_CHUNKS", 3):
            document = core.presummarize(messages, self.make_meta(env=env), env)
        self.assertIsNotNone(document)
        counts = self.header_counts(document)
        self.assertEqual(counts["total"], 3)
        self.assertIn("dropped_before_classify 2", document)
        self.assertNotIn("OLD-0 ", document)
        self.assertNotIn("OLD-1 ", document)
        self.assertIn("OLD-2 ", document)
        calls = self.stub_log_lines(env)
        screens = [call for call in calls if call["argv"] != ["--probe"]]
        self.assertEqual(len(calls), 4)
        self.assertEqual(len(screens), 3)

    def test_classify_stops_below_ten_ms(self):
        now = 1000.0
        ctx = {"head": "0" * 40, "deadline": now + 0.005, "parent": {},
               "config_home": os.path.join(tempfile.mkdtemp(), ".no-config")}
        with mock.patch.object(core, "_monotonic", return_value=now), \
                mock.patch("subprocess.run",
                           side_effect=AssertionError("no client process may start")):
            labels = core.classify_all(["a", "b", "c"], "/nowhere/client.py", "laya", ctx)
        self.assertEqual(labels, [None, None, None])


class TestCap(CoreEnvMixin, unittest.TestCase):
    """The 9,500-character cap: newest kept whole, no model call (SPEC R4)."""

    def test_cap_newest_kept_whole_and_no_model_call(self):
        env = self.make_env(STUB_LABEL_CYCLE="keep",
                            STUB_LOG=os.path.join(tempfile.mkdtemp(), "stub.log"))
        messages = [self.pad_message("user", f"MARK-{i:02d} ", 0.85) for i in range(30)]
        chunks = core.chunk_messages(messages)
        self.assertGreaterEqual(sum(len(chunk) for chunk in chunks), 30000)
        real_run = subprocess.run
        argvs = []

        def spy(cmd, **kwargs):
            argvs.append(list(cmd))
            return real_run(cmd, **kwargs)

        with mock.patch("subprocess.run", side_effect=spy):
            document = core.presummarize(messages, self.make_meta(env=env), env)
        self.assertIsNotNone(document)
        self.assertLessEqual(len(document), core.CAP_CHARS)
        newest = core.render_message(messages[-1])
        self.assertIn(newest, document)
        stub = str(STUB_PATH)
        self.assertTrue(all(stub in " ".join(argv) for argv in argvs), argvs)
        self.assertEqual(len(argvs), 1 + len(chunks))
        self.assertEqual(sum(1 for argv in argvs if "--probe" in argv), 1)

    def test_cap_boundary(self):
        header = "h" * 100
        newest = "n" * 100
        oldest = "\n".join(["a" * 50] * 182 + ["a" * 16])
        self.assertEqual(len(header + oldest + "\n\n" + newest), core.CAP_CHARS)
        result = core.apply_cap(header, [("keep", oldest), ("keep", newest)])
        self.assertEqual(result, header + oldest + "\n\n" + newest)
        result = core.apply_cap(header, [("keep", oldest + "a"), ("keep", newest)])
        self.assertLessEqual(len(result), core.CAP_CHARS)
        self.assertTrue(result.endswith(newest))
        self.assertFalse(result.startswith("a" * 50))

    def test_cap_summaries_go_first(self):
        header = "h" * 10
        big_kept = "\n".join(["a" * 50] * 300)
        entries = [("summarize", "S1 line a\nS1 line b"),
                   ("summarize", "S2 line a\nS2 line b"),
                   ("keep", "K1 head\n" + big_kept),
                   ("keep", "NEWEST kept tail")]
        result = core.apply_cap(header, entries)
        self.assertIsNotNone(result)
        self.assertLessEqual(len(result), core.CAP_CHARS)
        self.assertNotIn("S1 line", result)
        self.assertNotIn("S2 line", result)
        self.assertNotIn("K1 head", result)
        self.assertTrue(result.endswith("NEWEST kept tail"))

    def test_cap_all_discarded_header_only(self):
        env = self.make_env()
        meta = self.make_meta(env=env)
        document = core.build_document(meta, ["c1 text", "c2 text"],
                                       ["discard", "discard"])
        self.assertEqual(document, core.render_header(meta, ["c1 text", "c2 text"],
                                                      ["discard", "discard"]))
        self.assertIn("keep 0", document)

    def test_cap_trim_whole_lines_only(self):
        lines = ["ñ code line 🚀", "```", "fence body 中文", "```", "tail é"] * 250
        header = "h" * 10
        result = core.apply_cap(header, [("keep", "\n".join(lines)), ("keep", "newest")])
        self.assertIsNotNone(result)
        self.assertLessEqual(len(result), core.CAP_CHARS)
        body = result[len(header):].split("\n\n", 1)[0]
        for line in body.split("\n"):
            self.assertIn(line, lines)

    def test_cap_atomic_write(self):
        env = self.make_env()
        base = os.path.dirname(env["HOME"])
        transcript = self.synthetic_transcript(base, ["turn one", "turn two"])
        cwd = os.path.join(base, "proj")
        os.makedirs(cwd)
        real_replace = os.replace
        seen = {}

        def spy(src, dst):
            seen["tmp"] = src
            seen["dst"] = dst
            seen["mode"] = os.stat(src).st_mode & 0o777
            with open(src, encoding="utf-8") as handle:
                seen["text"] = handle.read()
            return real_replace(src, dst)

        with mock.patch("os.replace", side_effect=spy):
            path = core.run_claude({"session_id": "sess-w",
                                    "transcript_path": transcript, "cwd": cwd}, env)
        self.assertTrue(path)
        directory = core.private_dir(env)
        self.assertEqual(os.path.dirname(seen["tmp"]), directory)
        self.assertTrue(os.path.basename(seen["tmp"]).startswith(".precompact-"))
        self.assertEqual(seen["mode"], 0o600)
        self.assertTrue(seen["text"].startswith(core.HEADER_FIRST_LINE))
        with open(path, encoding="utf-8") as handle:
            self.assertEqual(handle.read(), seen["text"])


class TestPrivateDir(CoreEnvMixin, unittest.TestCase):
    """The private dir and its modes; the 24 h sweep (D-15)."""

    def _prepare_run(self, env):
        base = os.path.dirname(env["HOME"])
        transcript = self.synthetic_transcript(base, ["turn one", "turn two"])
        cwd = os.path.join(base, "proj")
        os.makedirs(cwd)
        return transcript, cwd

    def test_private_dir_modes_and_never_cwd(self):
        env = self.make_env()
        transcript, cwd = self._prepare_run(env)
        path = core.run_claude({"session_id": "sess-x",
                                "transcript_path": transcript, "cwd": cwd}, env)
        directory = core.private_dir(env)
        self.assertIsNotNone(path)
        self.assertTrue(path.startswith(directory + os.sep))
        self.assertFalse(path.startswith(cwd + os.sep))
        self.assertEqual(os.stat(directory).st_mode & 0o777, 0o700)
        self.assertEqual(os.stat(path).st_mode & 0o777, 0o600)

    def test_private_dir_cache_fallback(self):
        env = self.make_env()
        base = os.path.dirname(env["HOME"])
        fallback = {"HOME": env["HOME"], "XDG_CACHE_HOME": env["XDG_CACHE_HOME"],
                    "AI_KIT_PRECOMPACT_CLIENT": env["AI_KIT_PRECOMPACT_CLIENT"]}
        directory = core.private_dir(fallback)
        self.assertEqual(directory,
                         os.path.join(base, "cache", "ai-kit", "compact"))
        neither = {"HOME": "relative/home",
                   "AI_KIT_PRECOMPACT_CLIENT": env["AI_KIT_PRECOMPACT_CLIENT"]}
        self.assertIsNone(core.private_dir(neither))
        transcript, cwd = self._prepare_run(env)
        self.assertIsNone(core.run_claude({"session_id": "sess-y",
                                           "transcript_path": transcript,
                                           "cwd": cwd}, neither))

    def test_private_dir_refuses_symlink_or_open_mode(self):
        env = self.make_env()
        base = os.path.dirname(env["HOME"])
        ai_dir = os.path.join(base, "run", "ai-kit")
        os.makedirs(ai_dir)
        target = os.path.join(base, "elsewhere")
        os.makedirs(target)
        os.symlink(target, os.path.join(ai_dir, "compact"))
        self.assertIsNone(core.private_dir(env))
        os.unlink(os.path.join(ai_dir, "compact"))
        os.makedirs(os.path.join(ai_dir, "compact"), mode=0o755)
        self.assertIsNone(core.private_dir(env))

    def test_sweep_removes_only_old_ours(self):
        env = self.make_env()
        directory = core.private_dir(env)
        old = time.time() - 25 * 3600
        fresh = time.time() - 23 * 3600
        ages = {"s1-proj-compact.md": old, "s2-proj-compact.md": old,
                ".precompact-abc.tmp": old, "s3-fresh-compact.md": fresh,
                "notes.txt": old}
        for name, mtime in ages.items():
            path = os.path.join(directory, name)
            with open(path, "w", encoding="utf-8") as handle:
                handle.write("x")
            os.utime(path, (mtime, mtime))
        core.sweep(directory)
        self.assertEqual(set(os.listdir(directory)),
                         {"s3-fresh-compact.md", "notes.txt"})


if __name__ == "__main__":
    unittest.main()
