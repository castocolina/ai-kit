"""Tests for the maintainer command; covers tools/record_cli_help.py."""

import contextlib
import importlib.util
import io
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location(
    "record_cli_help", ROOT / "tools" / "record_cli_help.py"
)
if spec is None or spec.loader is None:
    raise ImportError("cannot load record_cli_help")
record_cli_help = importlib.util.module_from_spec(spec)
spec.loader.exec_module(record_cli_help)


class TestRecordCliHelp(unittest.TestCase):
    def test_child_env_isolates_the_home(self):
        home = Path("scratch-home")
        env = record_cli_help.child_env(home, {"PATH": "bin", "OPENCODE_X": "1", "KEEP": "2"})
        self.assertNotIn("OPENCODE_X", env)
        for key in (
            "OPENCODE_DISABLE_AUTOUPDATE",
            "OPENCODE_DISABLE_PROJECT_CONFIG",
            "OPENCODE_CONFIG_PROJECT_DISABLE",
        ):
            self.assertEqual(env[key], "1")
        self.assertEqual(env["KEEP"], "2")
        self.assertEqual(env["PATH"], "bin")
        self.assertEqual(env["HOME"], str(home))
        self.assertEqual(env["XDG_CONFIG_HOME"], str(home / ".config"))
        self.assertEqual(env["AI_KIT_REFUSE_REAL_HOME"], "1")

    def test_main_records_the_four_help_files_and_meta(self):
        calls = []

        def fake_run(argv, **kwargs):
            calls.append((argv, kwargs))
            text = "opencode 9.8.7\n" if argv[1:] == ["--version"] else (
                f"help text for {' '.join(argv[1:])}\n"
            )
            return subprocess.CompletedProcess(argv, 0, stdout=text, stderr="")

        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / "out"
            home = Path(directory) / "home"
            with (
                patch.object(record_cli_help, "OUT", out),
                patch.object(record_cli_help, "ROOT", Path(directory)),
                patch.object(record_cli_help.shutil, "which", return_value="fake-opencode"),
                patch.object(record_cli_help.subprocess, "run", side_effect=fake_run),
                contextlib.redirect_stdout(io.StringIO()),
            ):
                self.assertEqual(record_cli_help.main(["--home", str(home)]), 0)
            self.assertEqual(
                {path.name for path in out.iterdir()},
                {"version.txt", "help.txt", "run-help.txt", "models-help.txt", "meta.json"},
            )
            meta = json.loads((out / "meta.json").read_text(encoding="utf-8"))
            self.assertEqual(meta["version"], "9.8.7")
            self.assertEqual(len(meta["commands"]), 4)
            self.assertEqual(len(calls), 4)
            for argv, kwargs in calls:
                self.assertEqual(argv[0], "fake-opencode")
                self.assertEqual(kwargs["cwd"], home.resolve())
                self.assertEqual(kwargs["env"]["AI_KIT_REFUSE_REAL_HOME"], "1")

    def test_main_stops_on_a_failing_command_and_writes_no_meta(self):
        def fake_run(argv, **kwargs):
            del kwargs
            code = 2 if argv[1:] == ["models", "--help"] else 0
            return subprocess.CompletedProcess(argv, code, stdout="text\n", stderr="")

        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / "out"
            home = Path(directory) / "home"
            with (
                patch.object(record_cli_help, "OUT", out),
                patch.object(record_cli_help.shutil, "which", return_value="fake-opencode"),
                patch.object(record_cli_help.subprocess, "run", side_effect=fake_run),
                contextlib.redirect_stderr(io.StringIO()),
            ):
                self.assertEqual(record_cli_help.main(["--home", str(home)]), 1)
            self.assertFalse((out / "meta.json").exists())
            self.assertTrue((out / "version.txt").is_file())

    def test_main_without_opencode_returns_1(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / "out"
            home = Path(directory) / "home"
            with (
                patch.object(record_cli_help, "OUT", out),
                patch.object(record_cli_help.shutil, "which", return_value=None),
                patch.object(record_cli_help.subprocess, "run") as run,
                contextlib.redirect_stderr(io.StringIO()),
            ):
                self.assertEqual(record_cli_help.main(["--home", str(home)]), 1)
            run.assert_not_called()
            self.assertTrue(not out.exists() or not list(out.iterdir()))

    def test_main_requires_home(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / "out"
            with (
                patch.object(record_cli_help, "OUT", out),
                patch.object(record_cli_help.shutil, "which", return_value=None),
                patch.object(record_cli_help.subprocess, "run"),
                contextlib.redirect_stderr(io.StringIO()),
                self.assertRaises(SystemExit),
            ):
                record_cli_help.main([])

    def test_write_atomic_replaces_whole_text(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "help.txt"
            record_cli_help._write_atomic(path, "one")
            record_cli_help._write_atomic(path, "two")
            self.assertEqual(path.read_text(encoding="utf-8"), "two")
            self.assertEqual(list(path.parent.iterdir()), [path])
