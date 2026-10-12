"""Tests for tools/cursor-status-line-poc.py (Cursor Agent statusline POC)."""

from __future__ import annotations

import importlib.util
import io
import os
import tempfile
import types
import unittest
from pathlib import Path

POC = Path(__file__).resolve().parents[1] / "tools" / "cursor-status-line-poc.py"


def load_poc():
    spec = importlib.util.spec_from_file_location("cursor_status_line_poc", POC)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


class TestPayloadRender(unittest.TestCase):
    def test_model_and_path_from_payload(self):
        mod = load_poc()
        payload = {
            "session_id": "t",
            "model": {"id": "x", "display_name": "GPT POC", "param_summary": "High"},
            "workspace": {"current_dir": "/tmp/poc-proj"},
            "context_window": {
                "used_percentage": 34.5,
                "context_window_size": 200000,
            },
            "render_width_chars": 100,
        }
        with tempfile.TemporaryDirectory() as td:
            env = {"HOME": td, "XDG_CONFIG_HOME": td, "XDG_CACHE_HOME": td}
            out = mod.render_for_test(payload, env)
        self.assertIn("GPT POC", out)
        self.assertIn("34", out)
        self.assertIn("poc-proj", out)
        self.assertIn("200K", out)  # fmt_tokens(200000)
        self.assertIn("High", out)  # param_summary verbatim

    def test_null_context_pct_omits_percent(self):
        mod = load_poc()
        payload = {
            "model": {"display_name": "M"},
            "workspace": {"current_dir": "/tmp/x"},
            "context_window": {"used_percentage": None, "context_window_size": 1000},
        }
        with tempfile.TemporaryDirectory() as td:
            out = mod.render_for_test(
                payload, {"HOME": td, "XDG_CONFIG_HOME": td, "XDG_CACHE_HOME": td}
            )
        self.assertIn("M", out)
        self.assertNotIn("None", out)
        self.assertNotRegex(out, r"\b0%\b")

    def test_max_mode_marker(self):
        mod = load_poc()
        payload = {
            "model": {"display_name": "M", "max_mode": True},
            "workspace": {"current_dir": "/tmp/x"},
            "context_window": {"used_percentage": 1, "context_window_size": 1000},
        }
        with tempfile.TemporaryDirectory() as td:
            out = mod.render_for_test(
                payload, {"HOME": td, "XDG_CONFIG_HOME": td, "XDG_CACHE_HOME": td}
            )
        self.assertIn("· max", out)

    def test_toml_segments_merge_and_line_replace(self):
        mod = load_poc()
        with tempfile.TemporaryDirectory() as td:
            cfg = Path(td) / "ai-kit" / "cursor-statusline-poc.toml"
            cfg.parent.mkdir(parents=True)
            cfg.write_text(
                '[segments]\npath = false\n\n[[line]]\nmin_rows = 0\nsegments = ["model_compact"]\n',
                encoding="utf-8",
            )
            env = {"HOME": td, "XDG_CONFIG_HOME": td, "XDG_CACHE_HOME": td}
            c = mod.load_config(env)
            self.assertFalse(c.segments["path"])
            self.assertEqual(c.layout, [(0, ["model_compact"])])


class TestDumpPayload(unittest.TestCase):
    def test_dump_payload_writes_exact_raw_bytes(self):
        mod = load_poc()
        raw = b'{"model":{"display_name":"D"},"workspace":{"current_dir":"/tmp/x"},'
        raw += b'"context_window":{"used_percentage":1,"context_window_size":1000}}\n'
        with tempfile.TemporaryDirectory() as td:
            dump = Path(td) / "out" / "payload.json"
            env = {"HOME": td, "XDG_CONFIG_HOME": td, "XDG_CACHE_HOME": td}
            mod.render_from_raw(raw, env, dump_payload_path=str(dump))
            self.assertEqual(dump.read_bytes(), raw)

    def test_main_dump_payload_argv(self):
        mod = load_poc()
        raw = b'{"model":{"display_name":"D"},"workspace":{"current_dir":"/tmp/x"},'
        raw += b'"context_window":{"used_percentage":1,"context_window_size":1000}}\n'
        with tempfile.TemporaryDirectory() as td:
            dump = Path(td) / "p.json"
            env = {"HOME": td, "XDG_CONFIG_HOME": td, "XDG_CACHE_HOME": td}
            rc = mod.main(
                argv=["cursor-status-line-poc.py", "--dump-payload", str(dump)],
                stdin=io.BytesIO(raw),
                env=env,
            )
            self.assertEqual(rc, 0)
            self.assertEqual(dump.read_bytes(), raw)

    def test_main_never_raises_on_bad_stdin(self):
        mod = load_poc()
        with tempfile.TemporaryDirectory() as td:
            env = {"HOME": td, "XDG_CONFIG_HOME": td, "XDG_CACHE_HOME": td}
            rc = mod.main(argv=["poc"], stdin=io.BytesIO(b"not-json"), env=env)
            self.assertEqual(rc, 0)
            rc2 = mod.main(argv=["poc"], stdin=io.BytesIO(b""), env=env)
            self.assertEqual(rc2, 0)

    def test_python_s_import(self):
        import subprocess
        import sys

        with tempfile.TemporaryDirectory() as td:
            env = {
                "HOME": td,
                "XDG_CONFIG_HOME": td,
                "XDG_CACHE_HOME": td,
                "PATH": os.environ.get("PATH", ""),
                "LANG": os.environ.get("LANG", "C.UTF-8"),
            }
            r = subprocess.run(
                [sys.executable, "-S", str(POC)],
                input=b"{}",
                capture_output=True,
                env=env,
                check=False,
            )
        self.assertNotIn(b"ImportError", r.stderr)
        self.assertNotIn(b"ModuleNotFoundError", r.stderr)


class TestLocalProbes(unittest.TestCase):
    def test_system_available_bytes_positive_on_linux(self):
        mod = load_poc()
        n = mod.probe_system_available_bytes()
        if os.path.exists("/proc/meminfo"):
            self.assertIsNotNone(n)
            self.assertGreater(n, 0)

    def test_process_rss_returns_int(self):
        if not Path("/proc").is_dir():
            self.skipTest("Linux /proc required for POC RSS probe")
        mod = load_poc()
        n = mod.probe_process_rss_bytes()
        self.assertIsInstance(n, int)
        self.assertGreater(n, 0)

    def test_git_branch_in_repo(self):
        mod = load_poc()
        root = str(Path(__file__).resolve().parents[1])
        snap = mod.probe_git_snapshot(root)
        self.assertIsInstance(snap, dict)
        self.assertTrue(snap["in_repo"])
        self.assertIn(snap["dirty"], ("clean", "modified", "untracked"))
        self.assertTrue(snap["branch"] or snap["is_worktree"])

    def test_worktree_struck_on_main_checkout(self):
        mod = load_poc()
        theme = mod.default_theme()
        ctx = types.SimpleNamespace(work_dir="/tmp/x", home="/tmp")
        mod.probe_git_snapshot = lambda _wd: {
            "in_repo": True,
            "branch": "main",
            "dirty": "clean",
            "is_worktree": False,
            "wt_name": "",
        }
        s = mod.seg_alt_git_worktree(ctx, 80, theme)
        self.assertIsNotNone(s)
        self.assertIn("⎇", s)
        self.assertIn("\033[9m", s)
        self.assertIn(theme.c("GREY"), s)

    def test_worktree_cyan_on_linked(self):
        mod = load_poc()
        theme = mod.default_theme()
        ctx = types.SimpleNamespace(work_dir="/tmp/x", home="/tmp")
        mod.probe_git_snapshot = lambda _wd: {
            "in_repo": True,
            "branch": "feat",
            "dirty": "clean",
            "is_worktree": True,
            "wt_name": "poc-wt",
        }
        s = mod.seg_alt_git_worktree(ctx, 80, theme)
        self.assertIsNotNone(s)
        self.assertIn("poc-wt", s)
        self.assertIn(theme.c("CYAN"), s)
        self.assertNotIn("\033[9m", s)

    def test_process_memory_fmt_shape(self):
        mod = load_poc()
        theme = mod.default_theme()
        ctx = types.SimpleNamespace()
        mod.probe_process_rss_bytes = lambda: 85 * 1024 * 1024
        s = mod.seg_process_memory(ctx, 80, theme)
        self.assertIsNotNone(s)
        self.assertIn("🧮", s)
        self.assertRegex(s, r"\d+(\.\d)?MB")

    def test_system_memory_long_form(self):
        mod = load_poc()
        theme = mod.default_theme()
        ctx = types.SimpleNamespace()
        mod.probe_system_available_bytes = lambda: int(5.5 * 1024**3)
        s = mod.seg_system_memory(ctx, 80, theme)
        self.assertIsNotNone(s)
        self.assertIn("GiB free", s)

    def test_slowest_skips_meta_second_pass(self):
        mod = load_poc()
        payload = {
            "model": {"display_name": "M"},
            "workspace": {"current_dir": str(Path(__file__).resolve().parents[1])},
            "context_window": {"used_percentage": 1, "context_window_size": 1000},
            "render_width_chars": 200,
        }
        with tempfile.TemporaryDirectory() as td:
            out = mod.render_for_test(
                payload, {"HOME": td, "XDG_CONFIG_HOME": td, "XDG_CACHE_HOME": td}
            )
        if "🐌" in out:
            self.assertNotRegex(out, r"🐌\s*(render_time|slowest)\b")

    def test_git_probe_once_per_render(self):
        mod = load_poc()
        n = {"calls": 0}
        real = mod.probe_git_snapshot

        def counted(wd):
            n["calls"] += 1
            return real(wd)

        mod.probe_git_snapshot = counted
        payload = {
            "model": {"display_name": "M"},
            "workspace": {"current_dir": str(Path(__file__).resolve().parents[1])},
            "context_window": {"used_percentage": 1, "context_window_size": 1000},
            "render_width_chars": 200,
        }
        with tempfile.TemporaryDirectory() as td:
            mod.render_for_test(
                payload, {"HOME": td, "XDG_CONFIG_HOME": td, "XDG_CACHE_HOME": td}
            )
        self.assertEqual(n["calls"], 1)


if __name__ == "__main__":
    unittest.main()
