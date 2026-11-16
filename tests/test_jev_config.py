"""Behaviour of the [jev] settings module skills/jev-fast-decision/scripts/jev_config.py (plan
34-01). config_set writes only the [jev] table of the user config.toml and the copied reader reads
it back. Every test uses a temp HOME and a plain env dict, never the real HOME or os.environ."""

import importlib.util
import os
import shutil
import tempfile
import threading
import tomllib
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MODULE = REPO / "skills" / "jev-fast-decision" / "scripts" / "jev_config.py"


def _load():
    spec = importlib.util.spec_from_file_location("jev_config_under_test", MODULE)
    assert spec is not None and spec.loader is not None, MODULE
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


jev_config = _load()


class TestConfigSet(unittest.TestCase):
    def setUp(self):
        root = tempfile.mkdtemp(prefix="jev-config-")
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        home = os.path.join(root, "home")
        self.cwd = os.path.join(root, "proj")
        os.makedirs(self.cwd)
        self.env = {"HOME": home, "XDG_CONFIG_HOME": os.path.join(home, ".config")}
        self.user_file = os.path.join(home, ".config", "ai-kit", "config.toml")

    def _write_user(self, data: bytes):
        os.makedirs(os.path.dirname(self.user_file), exist_ok=True)
        with open(self.user_file, "wb") as handle:
            handle.write(data)

    def _read_user(self) -> bytes:
        with open(self.user_file, "rb") as handle:
            return handle.read()

    def test_set_then_read_back(self):
        result = jev_config.config_set("laya_url", "http://192.0.2.7:8010", self.env)
        self.assertTrue(result["ok"])
        self.assertTrue(result["file"].endswith(os.path.join("ai-kit", "config.toml")))
        table = jev_config.jev_table(self.cwd, self.env)
        self.assertEqual(table["laya_url"], "http://192.0.2.7:8010")

    def test_set_keeps_other_bytes(self):
        original = '# keep me\n[lanes]\nstrategy = "single"\n\n[jev]\nenabled = true\n'
        self._write_user(original.encode("utf-8"))
        self.assertTrue(jev_config.config_set("laya_version", "0.4.27", self.env)["ok"])
        expected = original + 'laya_version = "0.4.27"\n'
        self.assertEqual(self._read_user().decode("utf-8"), expected)
        self.assertEqual(tomllib.loads(expected)["jev"]["laya_version"], "0.4.27")

    def test_set_refuses_bad_values_and_writes_nothing(self):
        cases = [
            ("laya_url", "ftp://h/x", "invalid_value:laya_url"),
            ("laya_url", "http://user:pw@h:1", "invalid_value:laya_url"),
            ("laya_url", "http://", "invalid_value:laya_url"),
            ("laya_url", "http://h:99999", "invalid_value:laya_url"),
            ("laya_url", "http://h:1/?token=abc", "invalid_value:laya_url"),
            ("laya_url", "http://h:1/#frag", "invalid_value:laya_url"),
            ("laya_version", "0.4 beta", "invalid_value:laya_version"),
            ("enabled", "yes", "invalid_value:enabled"),
            ("other", "x", "unknown_key"),
        ]
        for key, raw, reason in cases:
            with self.subTest(key=key, raw=raw):
                result = jev_config.config_set(key, raw, self.env)
                self.assertEqual(result, {"ok": False, "reason": reason})
        self.assertFalse(os.path.exists(self.user_file))

    def test_declined_laya_is_an_empty_string(self):
        self.assertTrue(jev_config.config_set("laya_url", "", self.env)["ok"])
        self.assertEqual(jev_config.jev_table(self.cwd, self.env)["laya_url"], "")

    def test_set_refuses_a_broken_file(self):
        self._write_user(b"[jev\n")
        result = jev_config.config_set("laya_url", "http://192.0.2.7:8010", self.env)
        self.assertFalse(result["ok"])
        self.assertEqual(result["reason"], "config_unwritable")
        self.assertEqual(self._read_user(), b"[jev\n")

    def test_set_keeps_crlf_line_endings(self):
        self._write_user(b"# keep me\r\n[jev]\r\nenabled = true\r\n")
        self.assertTrue(jev_config.config_set("laya_version", "0.4.27", self.env)["ok"])
        raw = self._read_user()
        self.assertTrue(raw.startswith(b"# keep me\r\n"))
        self.assertNotIn(b"\n", raw.replace(b"\r\n", b""))
        parsed = tomllib.loads(raw.decode("utf-8"))["jev"]
        self.assertIs(parsed["enabled"], True)
        self.assertEqual(parsed["laya_version"], "0.4.27")

    def test_two_writers_keep_one_answer(self):
        results = []

        def write(value):
            results.append(jev_config.config_set("laya_url", value, self.env))

        values = ["http://192.0.2.1:1", "http://192.0.2.2:2"]
        threads = [threading.Thread(target=write, args=(value,)) for value in values]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertTrue(all(result["ok"] for result in results))
        self.assertIn(jev_config.jev_table(self.cwd, self.env)["laya_url"], values)


class TestKnobAndUrl(unittest.TestCase):
    def setUp(self):
        root = tempfile.mkdtemp(prefix="jev-knob-")
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        home = os.path.join(root, "home")
        self.cwd = os.path.join(root, "proj")
        os.makedirs(self.cwd)
        self.env = {"HOME": home, "XDG_CONFIG_HOME": os.path.join(home, ".config")}
        self.user_file = os.path.join(home, ".config", "ai-kit", "config.toml")
        self.project_file = os.path.join(self.cwd, ".aikit", "config.toml")

    def _write(self, path: str, text: str):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)

    def test_knob_env_wins_both_ways(self):
        self._write(self.user_file, "[jev]\nenabled = true\n")
        on_env = {**self.env, "GSD_PATH_JEV": "1"}
        off_env = {**self.env, "GSD_PATH_JEV": "0"}
        no_env = {**self.env, "GSD_PATH_JEV": "no"}
        self.assertEqual(
            jev_config.knob(self.cwd, on_env),
            {"on": True, "source": "env:GSD_PATH_JEV", "needs_answer": False, "problem": None},
        )
        self.assertEqual(jev_config.knob(self.cwd, off_env)["on"], False)
        self.assertEqual(jev_config.knob(self.cwd, no_env)["source"], "env:GSD_PATH_JEV")
        self._write(self.user_file, "[jev]\nenabled = false\n")
        self.assertEqual(jev_config.knob(self.cwd, on_env)["on"], True)
        self._write(self.user_file, "[jev\n")
        self.assertEqual(jev_config.knob(self.cwd, on_env)["on"], True)

    def test_knob_blank_env_is_unset(self):
        self._write(self.user_file, "[jev]\nenabled = false\n")
        for blank in ("", "   "):
            with self.subTest(env=blank):
                result = jev_config.knob(self.cwd, {**self.env, "GSD_PATH_JEV": blank})
                self.assertEqual(result["on"], False)
                self.assertEqual(result["source"], "config")

    def test_knob_project_over_user(self):
        self._write(self.user_file, "[jev]\nenabled = true\n")
        self._write(self.project_file, "[jev]\nenabled = false\n")
        self.assertEqual(
            jev_config.knob(self.cwd, self.env),
            {"on": False, "source": "config", "needs_answer": False, "problem": None},
        )
        self._write(self.user_file, "[jev]\nenabled = false\n")
        self._write(self.project_file, "[jev]\nenabled = true\n")
        self.assertEqual(jev_config.knob(self.cwd, self.env)["on"], True)

    def test_knob_absent_defaults_on_and_asks(self):
        self.assertEqual(
            jev_config.knob(self.cwd, self.env),
            {"on": True, "source": "default", "needs_answer": True, "problem": None},
        )

    def test_knob_bad_value_and_broken_file_fail_closed(self):
        self._write(self.user_file, '[jev]\nenabled = "false"\n')
        result = jev_config.knob(self.cwd, self.env)
        self.assertEqual(result["on"], False)
        self.assertEqual(result["problem"], "invalid_value:enabled")
        self._write(self.user_file, "[jev\n")
        result = jev_config.knob(self.cwd, self.env)
        self.assertEqual(result["on"], False)
        self.assertTrue(result["problem"].startswith("config_error"))

    def test_url_order_env_project_user_default(self):
        self.assertEqual(jev_config.laya_url_setting(self.cwd, self.env), (None, "default"))
        self._write(self.user_file, '[jev]\nlaya_url = "http://user.example:1"\n')
        self.assertEqual(
            jev_config.laya_url_setting(self.cwd, self.env), ("http://user.example:1", "config")
        )
        self._write(self.project_file, '[jev]\nlaya_url = "http://project.example:2"\n')
        self.assertEqual(
            jev_config.laya_url_setting(self.cwd, self.env),
            ("http://project.example:2", "config"),
        )
        ai_kit_env = {**self.env, "AI_KIT_LAYA_URL": "http://ai-kit.example:3"}
        self.assertEqual(
            jev_config.laya_url_setting(self.cwd, ai_kit_env),
            ("http://ai-kit.example:3", "env:AI_KIT_LAYA_URL"),
        )
        both_env = {**ai_kit_env, "JEV_LAYA_URL": "http://jev.example:4"}
        self.assertEqual(
            jev_config.laya_url_setting(self.cwd, both_env),
            ("http://jev.example:4", "env:JEV_LAYA_URL"),
        )
        blank_env = {**self.env, "JEV_LAYA_URL": "  "}
        self.assertEqual(
            jev_config.laya_url_setting(self.cwd, blank_env),
            ("http://project.example:2", "config"),
        )
        self._write(self.project_file, '[jev]\nlaya_url = ""\n')
        self.assertEqual(jev_config.laya_url_setting(self.cwd, self.env), ("", "config"))

    def test_url_bad_value_and_broken_file(self):
        self._write(self.user_file, "[jev]\nlaya_url = 5\n")
        self.assertEqual(
            jev_config.laya_url_setting(self.cwd, self.env), (None, "invalid_value:laya_url")
        )
        self._write(self.user_file, "[jev\n")
        self.assertEqual(jev_config.laya_url_setting(self.cwd, self.env), (None, "config_error"))


if __name__ == "__main__":
    unittest.main()
