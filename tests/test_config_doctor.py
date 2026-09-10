"""Unit tests for the Config Doctor tracer (readers + declarative engine)."""

import importlib.util
import json
import os
import re
import shutil
import sys
import tempfile
import tomllib
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
_TOOLS_DIR = os.path.join(_REPO, "tools")


def load_readers():
    """Load config_doctor_readers.py; insert tools/ on sys.path first."""
    if _TOOLS_DIR not in sys.path:
        sys.path.insert(0, _TOOLS_DIR)
    path = os.path.join(_TOOLS_DIR, "config_doctor_readers.py")
    spec = importlib.util.spec_from_file_location("config_doctor_readers", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["config_doctor_readers"] = mod
    spec.loader.exec_module(mod)
    return mod


def load_checks():
    """Load config_doctor_checks.py after readers so its sibling import resolves."""
    load_readers()
    path = os.path.join(_TOOLS_DIR, "config_doctor_checks.py")
    spec = importlib.util.spec_from_file_location("config_doctor_checks", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["config_doctor_checks"] = mod
    spec.loader.exec_module(mod)
    return mod


readers = load_readers()
checks = load_checks()


class TestReaders(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="ai-kit-cd-readers-")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def _path(self, name):
        return os.path.join(self.tmp, name)

    def test_read_json_checked_ok(self):
        path = self._path("settings.json")
        with open(path, "w", encoding="utf-8") as handle:
            json.dump({"cleanupPeriodDays": 15}, handle)
        state, data = readers.read_json_checked(path)
        self.assertEqual(state, "ok")
        self.assertEqual(data, {"cleanupPeriodDays": 15})

    def test_read_jsonc_checked_ok(self):
        path = self._path("opencode.jsonc")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write('{\n  // comment\n  "share": "manual",\n}\n')
        state, data = readers.read_jsonc_checked(path)
        self.assertEqual(state, "ok")
        self.assertEqual(data, {"share": "manual"})

    def test_read_toml_checked_ok(self):
        path = self._path("config.toml")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write('sandbox_mode = "workspace-write"\n')
        state, data = readers.read_toml_checked(path)
        self.assertEqual(state, "ok")
        self.assertEqual(data, {"sandbox_mode": "workspace-write"})

    def test_get_nested_returns_default_when_missing(self):
        self.assertIs(
            readers.get_nested({}, "missing"),
            readers.UNKNOWN,
        )
        self.assertEqual(
            readers.get_nested({}, "cleanupPeriodDays", default=30),
            30,
        )

    def test_get_nested_walks_string_keys(self):
        data = {"sandbox": {"enabled": True}}
        self.assertTrue(readers.get_nested(data, "sandbox", "enabled"))
        self.assertIs(
            readers.get_nested(data, "sandbox", "missing"),
            readers.UNKNOWN,
        )


class TestCatalogTracer(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="ai-kit-cd-catalog-")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.claude = os.path.join(self.tmp, "claude")
        self.opencode = os.path.join(self.tmp, "opencode")
        self.codex = os.path.join(self.tmp, "codex")
        self.cursor = os.path.join(self.tmp, "cursor")
        for path in (self.claude, self.opencode, self.codex, self.cursor):
            os.makedirs(path)

    def _env(self):
        return {
            "HOME": self.tmp,
            "CLAUDE_CONFIG_DIR": self.claude,
            "OPENCODE_CONFIG_DIR": self.opencode,
            "CODEX_HOME": self.codex,
            "CURSOR_CONFIG_DIR": self.cursor,
        }

    def test_build_catalog_one_claude_retention_row(self):
        with open(os.path.join(self.claude, "settings.json"), "w", encoding="utf-8") as handle:
            json.dump({"cleanupPeriodDays": 15}, handle)
        catalog = checks.build_catalog(self._env())
        self.assertEqual(len(catalog["sections"]), 1)
        section = catalog["sections"][0]
        self.assertEqual(section["runtime"], "claude")
        self.assertEqual(len(section["rows"]), 1)
        row = section["rows"][0]
        self.assertEqual(row["id"], "claude-retention")
        self.assertEqual(row["current_display"], "15")
        self.assertEqual(row["recommended_display"], "3650")
        self.assertIn("code.claude.com", row["source"])

    def test_resolve_runtime_config_paths_four_keys(self):
        paths = checks.resolve_runtime_config_paths(self._env())
        self.assertEqual(
            set(paths),
            {"claude", "opencode", "codex", "cursor"},
        )
        self.assertTrue(paths["cursor"].endswith("cli-config.json"))
        self.assertTrue(paths["claude"].endswith("settings.json"))
        self.assertTrue(paths["opencode"].endswith("opencode.jsonc"))
        self.assertTrue(paths["codex"].endswith("config.toml"))


_PRECOMMIT_PATH = os.path.join(_REPO, ".pre-commit-config.yaml")
_MAKEFILE_PATH = os.path.join(_REPO, "Makefile")
_PYPROJECT_PATH = os.path.join(_REPO, "pyproject.toml")
_CONFIG_DOCTOR_PY = (
    "tools/config_doctor_checks.py",
    "tools/config_doctor_readers.py",
    "tools/config_doctor_app.py",
)


def _write(path, content):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(content)


def precommit_hook_block(hook_id):
    with open(_PRECOMMIT_PATH, encoding="utf-8") as handle:
        text = handle.read()
    needle = f"- id: {hook_id}"
    start = text.find(needle)
    if start < 0:
        raise AssertionError(f"hook id {hook_id!r} not found in .pre-commit-config.yaml")
    rest = text[start:]
    nxt = rest.find("\n      - id:", len(needle))
    return rest if nxt < 0 else rest[:nxt]


def precommit_hook_files_regex(hook_id):
    """Return the `files:` value for `- id: <hook_id>` by reading YAML as text."""
    block = precommit_hook_block(hook_id)
    match = re.search(r"^\s*files:\s*(\S+)\s*$", block, re.MULTILINE)
    if match is None:
        raise AssertionError(f"no files: value for hook {hook_id!r}")
    return match.group(1).strip().strip("'\"")


class _ScratchRuntimes(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="ai-kit-cd-presence-")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.claude = os.path.join(self.tmp, "claude")
        self.opencode = os.path.join(self.tmp, "opencode")
        self.codex = os.path.join(self.tmp, "codex")
        self.cursor = os.path.join(self.tmp, "cursor")
        for path in (self.claude, self.opencode, self.codex, self.cursor):
            os.makedirs(path)

    def _env(self):
        return {
            "HOME": self.tmp,
            "CLAUDE_CONFIG_DIR": self.claude,
            "OPENCODE_CONFIG_DIR": self.opencode,
            "CODEX_HOME": self.codex,
            "CURSOR_CONFIG_DIR": self.cursor,
        }

    def _runtimes(self, catalog):
        return [section["runtime"] for section in catalog["sections"]]


class TestPresence(_ScratchRuntimes):
    def test_no_config_files_yields_empty_catalog(self):
        catalog = checks.build_catalog(self._env())
        self.assertEqual(catalog, {"sections": []})

    def test_zero_rows_omits_section_when_file_exists(self):
        _write(os.path.join(self.claude, "settings.json"), "{}")
        _write(os.path.join(self.opencode, "opencode.jsonc"), "{}")
        _write(os.path.join(self.codex, "config.toml"), "placeholder = 1\n")
        _write(os.path.join(self.cursor, "cli-config.json"), "{}")
        catalog = checks.build_catalog(self._env())
        self.assertEqual(self._runtimes(catalog), ["claude"])
        self.assertEqual(len(catalog["sections"][0]["rows"]), 1)

    def test_only_opencode_present_leaks_no_other_runtime(self):
        _write(os.path.join(self.opencode, "opencode.jsonc"), "{}")
        catalog = checks.build_catalog(self._env())
        self.assertNotIn("claude", self._runtimes(catalog))
        self.assertNotIn("codex", self._runtimes(catalog))
        self.assertNotIn("cursor", self._runtimes(catalog))
        self.assertEqual(catalog["sections"], [])

    def test_only_codex_present_leaks_no_other_runtime(self):
        _write(os.path.join(self.codex, "config.toml"), "placeholder = 1\n")
        catalog = checks.build_catalog(self._env())
        self.assertNotIn("claude", self._runtimes(catalog))
        self.assertNotIn("opencode", self._runtimes(catalog))
        self.assertNotIn("cursor", self._runtimes(catalog))
        self.assertEqual(catalog["sections"], [])

    def test_only_cursor_present_leaks_no_other_runtime(self):
        _write(os.path.join(self.cursor, "cli-config.json"), "{}")
        catalog = checks.build_catalog(self._env())
        self.assertNotIn("claude", self._runtimes(catalog))
        self.assertNotIn("opencode", self._runtimes(catalog))
        self.assertNotIn("codex", self._runtimes(catalog))
        self.assertEqual(catalog["sections"], [])

    def test_cursor_xdg_fallback_resolves_cli_config_json(self):
        home = tempfile.mkdtemp(prefix="ai-kit-cd-xdg-home-")
        xdg = tempfile.mkdtemp(prefix="ai-kit-cd-xdg-")
        self.addCleanup(shutil.rmtree, home, ignore_errors=True)
        self.addCleanup(shutil.rmtree, xdg, ignore_errors=True)
        cursor_xdg = os.path.join(xdg, "cursor")
        os.makedirs(cursor_xdg)
        target = os.path.join(cursor_xdg, "cli-config.json")
        _write(target, "{}")
        decoy_dir = os.path.join(home, ".cursor")
        os.makedirs(decoy_dir)
        _write(os.path.join(decoy_dir, "cli-config.json"), "{}")
        env = {"HOME": home, "XDG_CONFIG_HOME": xdg}
        paths = checks.resolve_runtime_config_paths(env)
        self.assertEqual(paths["cursor"], target)


class TestUnknownDegrade(_ScratchRuntimes):
    def _claude_row(self, catalog):
        self.assertEqual(len(catalog["sections"]), 1)
        self.assertEqual(catalog["sections"][0]["runtime"], "claude")
        self.assertEqual(len(catalog["sections"][0]["rows"]), 1)
        return catalog["sections"][0]["rows"][0]

    def test_malformed_json_current_display_unknown(self):
        _write(os.path.join(self.claude, "settings.json"), '{"cleanupPeriodDays": 1')
        row = self._claude_row(checks.build_catalog(self._env()))
        self.assertEqual(row["current_display"], "unknown")
        self.assertIs(row["current_value"], checks.UNKNOWN)

    def test_non_dict_top_level_current_display_unknown(self):
        _write(os.path.join(self.claude, "settings.json"), "[1, 2, 3]")
        row = self._claude_row(checks.build_catalog(self._env()))
        self.assertEqual(row["current_display"], "unknown")
        self.assertIs(row["current_value"], checks.UNKNOWN)

    def test_absent_key_uses_documented_default_30(self):
        _write(os.path.join(self.claude, "settings.json"), "{}")
        row = self._claude_row(checks.build_catalog(self._env()))
        self.assertEqual(row["current_display"], "30")


class TestGateRegistration(unittest.TestCase):
    def test_py_compile_regex_matches_config_doctor_modules(self):
        regex = precommit_hook_files_regex("py-compile")
        for path in _CONFIG_DOCTOR_PY:
            self.assertIsNotNone(
                re.match(regex, path),
                f"{path} did not match py-compile files: {regex}",
            )

    def test_unittest_core_entry_includes_config_doctor_modules(self):
        block = precommit_hook_block("unittest")
        match = re.search(r"^\s*entry:\s*(.+)$", block, re.MULTILINE)
        self.assertIsNotNone(match, "no entry: value for hook unittest")
        entry = match.group(1)
        self.assertIn("tests.test_config_doctor", entry)
        self.assertIn("tests.test_config_doctor_pty", entry)

    def test_pyright_include_contains_config_doctor_modules(self):
        with open(_PYPROJECT_PATH, "rb") as handle:
            data = tomllib.load(handle)
        include = data["tool"]["pyright"]["include"]
        for path in _CONFIG_DOCTOR_PY:
            self.assertIn(path, include)

    def test_pylint_files_does_not_match_config_doctor(self):
        regex = precommit_hook_files_regex("pylint")
        self.assertIsNone(re.match(regex, "tools/config_doctor_checks.py"))

    def test_vulture_paths_does_not_contain_config_doctor(self):
        with open(_PYPROJECT_PATH, "rb") as handle:
            data = tomllib.load(handle)
        paths = data["tool"]["vulture"]["paths"]
        joined = " ".join(paths)
        self.assertNotIn("config_doctor", joined)

