"""Unit tests for the Config Doctor tracer (readers + declarative engine)."""

import importlib.util
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import tomllib
import unittest
from unittest import mock

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


def load_appliers():
    """Load config_doctor_appliers.py; insert tools/ on sys.path first."""
    if _TOOLS_DIR not in sys.path:
        sys.path.insert(0, _TOOLS_DIR)
    path = os.path.join(_TOOLS_DIR, "config_doctor_appliers.py")
    spec = importlib.util.spec_from_file_location("config_doctor_appliers", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["config_doctor_appliers"] = mod
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
        self.assertIn("claude", [s["runtime"] for s in catalog["sections"]])
        row = _row_by_id(catalog, "claude-retention")
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
    "tools/config_doctor_appliers.py",
)


def _write(path, content):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(content)


def _row_by_id(catalog, row_id):
    for section in catalog["sections"]:
        for row in section["rows"]:
            if row["id"] == row_id:
                return row
    raise AssertionError(f"row {row_id!r} not found")


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
        runtimes = self._runtimes(catalog)
        self.assertNotIn("claude", runtimes)
        self.assertNotIn("opencode", runtimes)
        self.assertNotIn("codex", runtimes)
        self.assertNotIn("cursor", runtimes)

    def test_zero_rows_omits_section_when_file_exists(self):
        _write(os.path.join(self.claude, "settings.json"), "{}")
        _write(os.path.join(self.opencode, "opencode.jsonc"), "{}")
        _write(os.path.join(self.codex, "config.toml"), "placeholder = 1\n")
        _write(os.path.join(self.cursor, "cli-config.json"), "{}")
        catalog = checks.build_catalog(self._env())
        self.assertEqual(
            [r for r in self._runtimes(catalog) if r != "cross"],
            ["claude", "opencode", "codex", "cursor"],
        )
        self.assertIn("cross", self._runtimes(catalog))
        self.assertGreaterEqual(len(catalog["sections"][0]["rows"]), 1)

    def test_only_opencode_present_leaks_no_other_runtime(self):
        _write(os.path.join(self.opencode, "opencode.jsonc"), "{}")
        catalog = checks.build_catalog(self._env())
        self.assertNotIn("claude", self._runtimes(catalog))
        self.assertNotIn("codex", self._runtimes(catalog))
        self.assertNotIn("cursor", self._runtimes(catalog))
        self.assertIn("opencode", self._runtimes(catalog))

    def test_only_codex_present_leaks_no_other_runtime(self):
        _write(os.path.join(self.codex, "config.toml"), "placeholder = 1\n")
        catalog = checks.build_catalog(self._env())
        self.assertNotIn("claude", self._runtimes(catalog))
        self.assertNotIn("opencode", self._runtimes(catalog))
        self.assertNotIn("cursor", self._runtimes(catalog))
        self.assertIn("codex", self._runtimes(catalog))

    def test_only_cursor_present_leaks_no_other_runtime(self):
        _write(os.path.join(self.cursor, "cli-config.json"), "{}")
        catalog = checks.build_catalog(self._env())
        self.assertNotIn("claude", self._runtimes(catalog))
        self.assertNotIn("opencode", self._runtimes(catalog))
        self.assertNotIn("codex", self._runtimes(catalog))
        self.assertIn("cursor", self._runtimes(catalog))

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
        self.assertIn("claude", [s["runtime"] for s in catalog["sections"]])
        return _row_by_id(catalog, "claude-retention")

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
        self.assertIn("tools/config_doctor_appliers.py", include)

    def test_pylint_files_does_not_match_config_doctor(self):
        regex = precommit_hook_files_regex("pylint")
        self.assertIsNone(re.match(regex, "tools/config_doctor_checks.py"))

    def test_vulture_paths_does_not_contain_config_doctor(self):
        with open(_PYPROJECT_PATH, "rb") as handle:
            data = tomllib.load(handle)
        paths = data["tool"]["vulture"]["paths"]
        joined = " ".join(paths)
        self.assertNotIn("config_doctor", joined)


_CLAUDE_EXPANDED_IDS = (
    "claude-prompt-cache-ttl",
    "claude-subagent-prompt-cache-ttl",
    "claude-sandbox-enabled",
    "claude-sandbox-fail-if-unavailable",
    "claude-telemetry",
)

_OPENCODE_IDS = (
    "opencode-retention",
    "opencode-permissions",
    "opencode-share-mode",
    "opencode-model-options",
)


class TestClaudeRowsExpanded(_ScratchRuntimes):
    def _claude_settings(self):
        return {
            "cleanupPeriodDays": 15,
            "promptCacheTtl": "1h",
            "subagentPromptCacheTtl": "1h",
            "sandbox": {"enabled": True, "failIfUnavailable": False},
        }

    def test_expanded_claude_rows_against_realistic_fixture(self):
        _write(
            os.path.join(self.claude, "settings.json"),
            json.dumps(self._claude_settings()),
        )
        env = self._env()
        env["CLAUDE_CODE_ENABLE_TELEMETRY"] = "1"
        catalog = checks.build_catalog(env)
        ids = [row.id for row in checks.CONFIG_DOCTOR_ROWS]
        self.assertGreaterEqual(len(checks.CONFIG_DOCTOR_ROWS), 10)
        for row_id in _CLAUDE_EXPANDED_IDS:
            self.assertIn(row_id, ids)
            row = _row_by_id(catalog, row_id)
            self.assertEqual(row["id"], row_id)
            self.assertTrue(row["current_display"])
            self.assertIn(row["confidence"], {"HIGH", "MEDIUM", "LOW"})
            self.assertTrue(row["source"].startswith("https://"))

        ttl = _row_by_id(catalog, "claude-prompt-cache-ttl")
        self.assertEqual(ttl["current_display"], "1h")
        self.assertEqual(ttl["confidence"], "HIGH")
        self.assertIn("v2.1.242", ttl["why"])
        self.assertIn("5m", ttl["why"])
        self.assertEqual(
            ttl["source"],
            "https://code.claude.com/docs/en/prompt-caching",
        )

        sub = _row_by_id(catalog, "claude-subagent-prompt-cache-ttl")
        self.assertEqual(sub["current_display"], "1h")
        self.assertEqual(sub["confidence"], "HIGH")

        sandbox = _row_by_id(catalog, "claude-sandbox-enabled")
        self.assertEqual(sandbox["current_display"], "True")
        self.assertEqual(sandbox["recommended_display"], "True")
        self.assertIn("security-relevant", sandbox["why"])

        fail = _row_by_id(catalog, "claude-sandbox-fail-if-unavailable")
        self.assertEqual(fail["current_display"], "False")
        self.assertIn("risk", fail["why"].lower())

        telem = _row_by_id(catalog, "claude-telemetry")
        self.assertEqual(telem["current_display"], "1")
        self.assertEqual(telem["confidence"], "HIGH")
        self.assertIn("process environment", telem["why"])
        self.assertIn("env", telem["why"])
        self.assertIn("DISABLE_TELEMETRY", telem["why"])

    def test_claude_telemetry_survives_unreadable_settings_json(self):
        _write(os.path.join(self.claude, "settings.json"), '{"cleanupPeriodDays": 1')
        env = self._env()
        env["CLAUDE_CODE_ENABLE_TELEMETRY"] = "1"
        catalog = checks.build_catalog(env)
        telem = _row_by_id(catalog, "claude-telemetry")
        self.assertEqual(telem["current_display"], "1")
        claude_rows = catalog["sections"][0]["rows"]
        others = [row for row in claude_rows if row["id"] != "claude-telemetry"]
        self.assertTrue(others)
        for row in others:
            self.assertEqual(row["current_display"], "unknown")

    def test_absent_prompt_cache_ttl_is_unknown_not_guessed(self):
        _write(os.path.join(self.claude, "settings.json"), "{}")
        catalog = checks.build_catalog(self._env())
        ttl = _row_by_id(catalog, "claude-prompt-cache-ttl")
        self.assertEqual(ttl["current_display"], "unknown")
        sub = _row_by_id(catalog, "claude-subagent-prompt-cache-ttl")
        self.assertEqual(sub["current_display"], "5m")


class TestOpencodeRows(_ScratchRuntimes):
    def _opencode_fixture(self):
        return {
            "share": "disabled",
            "permission": {"bash": "ask", "doom_loop": "ask"},
            "provider": {
                "router-env": {
                    "models": {
                        "my-coding": {
                            "options": {"reasoningEffort": "high"},
                        }
                    }
                }
            },
        }

    def test_opencode_rows_against_realistic_fixture(self):
        _write(
            os.path.join(self.opencode, "opencode.jsonc"),
            json.dumps(self._opencode_fixture()),
        )
        catalog = checks.build_catalog(self._env())
        ids = [row.id for row in checks.CONFIG_DOCTOR_ROWS]
        self.assertGreaterEqual(len(checks.CONFIG_DOCTOR_ROWS), 10)
        for row_id in _OPENCODE_IDS:
            self.assertIn(row_id, ids)
            row = _row_by_id(catalog, row_id)
            self.assertEqual(row["id"], row_id)
            self.assertTrue(row["current_display"])
            self.assertTrue(row["source"].startswith("https://"))

        retention = _row_by_id(catalog, "opencode-retention")
        self.assertEqual(retention["current_display"], "not currently configurable")
        self.assertEqual(retention["recommended_display"], "N/A")
        self.assertEqual(retention["confidence"], "HIGH")
        self.assertIn("permanently", retention["why"])
        self.assertIn("not currently configurable", retention["why"])
        self.assertIn("#22110", retention["why"])

        perms = _row_by_id(catalog, "opencode-permissions")
        self.assertIn("bash=ask", perms["current_display"])
        self.assertEqual(perms["confidence"], "HIGH")
        self.assertIn("doom_loop", perms["why"])

        share = _row_by_id(catalog, "opencode-share-mode")
        self.assertEqual(share["current_display"], "disabled")
        self.assertEqual(share["confidence"], "MEDIUM")

        options = _row_by_id(catalog, "opencode-model-options")
        self.assertIn("router-env/my-coding", options["current_display"])
        self.assertEqual(options["confidence"], "LOW")
        self.assertIn("router-env", options["why"])

    def test_permission_string_value_degrades_to_unknown(self):
        _write(
            os.path.join(self.opencode, "opencode.jsonc"),
            json.dumps({"permission": "allow"}),
        )
        catalog = checks.build_catalog(self._env())
        perms = _row_by_id(catalog, "opencode-permissions")
        self.assertEqual(perms["current_display"], "unknown")

    def test_absent_permission_key_reports_documented_defaults(self):
        _write(os.path.join(self.opencode, "opencode.jsonc"), "{}")
        catalog = checks.build_catalog(self._env())
        perms = _row_by_id(catalog, "opencode-permissions")
        self.assertNotEqual(perms["current_display"], "unknown")
        self.assertIn("defaults", perms["current_display"])


_CODEX_IDS = (
    "codex-sandbox-mode",
    "codex-hooks",
    "codex-model-reasoning-effort",
    "codex-history-max-bytes",
    "codex-memories-durations",
    "codex-history-persistence",
)

_CURSOR_IDS = (
    "cursor-permissions",
    "cursor-approval-mode",
    "cursor-sandbox-cli-config",
    "cursor-sandbox-json",
    "cursor-model-parameters",
    "cursor-local-retention",
    "cursor-cli-telemetry",
    "cursor-attribution",
)

_CODEX_TOML = """\
sandbox_mode = "workspace-write"
model = "gpt-5.6-luna"
model_reasoning_effort = "low"

[features]
hooks = true

[history]
max_bytes = 1048576
persistence = "save-all"

[memories]
max_unused_days = 14
max_rollout_age_days = 7
min_rollout_idle_hours = 3
"""

_CURSOR_CLI_CONFIG = {
    "permissions": {"allow": ["Shell(ls)"], "deny": []},
    "approvalMode": "allowlist",
    "sandbox": {"mode": "disabled", "networkAccess": "user_config_with_defaults"},
    "modelParameters": {
        "gpt-5.2": [{"id": "reasoning", "value": "medium"}],
    },
    "attribution": {
        "attributeCommitsToAgent": True,
        "attributePRsToAgent": False,
    },
}

_SANDBOX_JSON = {
    "type": "workspace_readonly",
    "networkPolicy": {"default": "deny"},
}


class TestCodexRows(_ScratchRuntimes):
    def test_codex_rows_against_realistic_fixture(self):
        _write(os.path.join(self.codex, "config.toml"), _CODEX_TOML)
        catalog = checks.build_catalog(self._env())
        self.assertGreaterEqual(len(checks.CONFIG_DOCTOR_ROWS), 24)
        ids = [row.id for row in checks.CONFIG_DOCTOR_ROWS]
        for row_id in _CODEX_IDS:
            self.assertIn(row_id, ids)
            row = _row_by_id(catalog, row_id)
            self.assertEqual(row["id"], row_id)
            self.assertTrue(row["current_display"])
            self.assertTrue(row["source"].startswith("https://"))

        sandbox = _row_by_id(catalog, "codex-sandbox-mode")
        self.assertEqual(sandbox["current_display"], "workspace-write")
        self.assertEqual(sandbox["confidence"], "MEDIUM")

        hooks = _row_by_id(catalog, "codex-hooks")
        self.assertEqual(hooks["current_display"], "True")
        self.assertIn("permanently", hooks["why"])

        effort = _row_by_id(catalog, "codex-model-reasoning-effort")
        self.assertIn("model=gpt-5.6-luna", effort["current_display"])
        self.assertIn("effort=low", effort["current_display"])
        self.assertEqual(effort["confidence"], "LOW")

        hist = _row_by_id(catalog, "codex-history-max-bytes")
        self.assertEqual(hist["current_display"], "1048576")

        mem = _row_by_id(catalog, "codex-memories-durations")
        self.assertIn("14", mem["current_display"])
        self.assertIn("6015", mem["why"])

        persist = _row_by_id(catalog, "codex-history-persistence")
        self.assertEqual(persist["current_display"], "save-all")

    def test_absent_sandbox_mode_is_unknown(self):
        _write(os.path.join(self.codex, "config.toml"), "placeholder = 1\n")
        catalog = checks.build_catalog(self._env())
        sandbox = _row_by_id(catalog, "codex-sandbox-mode")
        self.assertEqual(sandbox["current_display"], "unknown")
        hooks = _row_by_id(catalog, "codex-hooks")
        self.assertEqual(hooks["current_display"], "False")
        persist = _row_by_id(catalog, "codex-history-persistence")
        self.assertEqual(persist["current_display"], "save-all")
        hist = _row_by_id(catalog, "codex-history-max-bytes")
        self.assertEqual(hist["current_display"], "unset (no cap)")

    def test_codex_hooks_deprecated_alias(self):
        _write(
            os.path.join(self.codex, "config.toml"),
            "[features]\ncodex_hooks = true\n",
        )
        catalog = checks.build_catalog(self._env())
        hooks = _row_by_id(catalog, "codex-hooks")
        self.assertEqual(hooks["current_display"], "True")

    def test_catalog_contains_at_least_twenty_four_rows(self):
        self.assertGreaterEqual(len(checks.CONFIG_DOCTOR_ROWS), 24)


class TestCursorRows(_ScratchRuntimes):
    def _write_cursor_pair(self, cli_config, sandbox=None):
        _write(
            os.path.join(self.cursor, "cli-config.json"),
            json.dumps(cli_config),
        )
        if sandbox is not None:
            _write(
                os.path.join(self.cursor, "sandbox.json"),
                json.dumps(sandbox),
            )

    def test_cursor_rows_against_realistic_fixture(self):
        self._write_cursor_pair(_CURSOR_CLI_CONFIG, _SANDBOX_JSON)
        catalog = checks.build_catalog(self._env())
        self.assertGreaterEqual(len(checks.CONFIG_DOCTOR_ROWS), 24)
        ids = [row.id for row in checks.CONFIG_DOCTOR_ROWS]
        for row_id in _CURSOR_IDS:
            self.assertIn(row_id, ids)
            row = _row_by_id(catalog, row_id)
            self.assertEqual(row["id"], row_id)
            self.assertTrue(row["current_display"] or row["current_display"] == "unknown")

        perms = _row_by_id(catalog, "cursor-permissions")
        self.assertIn("Shell(ls)", perms["current_display"])
        self.assertEqual(perms["confidence"], "HIGH")
        self.assertTrue(perms["source"].startswith("https://"))

        approval = _row_by_id(catalog, "cursor-approval-mode")
        self.assertEqual(approval["current_display"], "allowlist")

        cli_sb = _row_by_id(catalog, "cursor-sandbox-cli-config")
        self.assertIn("mode=disabled", cli_sb["current_display"])
        self.assertEqual(cli_sb["confidence"], "MEDIUM")
        self.assertIn("NOT the same mechanism", cli_sb["why"])

        file_sb = _row_by_id(catalog, "cursor-sandbox-json")
        self.assertIn("workspace_readonly", file_sb["current_display"])
        self.assertEqual(file_sb["confidence"], "HIGH")
        self.assertIn("sandbox-policies", file_sb["why"])

        mp = _row_by_id(catalog, "cursor-model-parameters")
        self.assertIn("gpt-5.2", mp["current_display"])
        self.assertEqual(mp["confidence"], "LOW")
        self.assertIn("permanently", mp["why"])

        attr = _row_by_id(catalog, "cursor-attribution")
        self.assertIn("attributeCommitsToAgent=True", attr["current_display"])
        self.assertIn("attributePRsToAgent=False", attr["current_display"])

        for row_id in ("cursor-local-retention", "cursor-cli-telemetry"):
            row = _row_by_id(catalog, row_id)
            self.assertEqual(row["current_display"], "unknown")
            self.assertIn("permanently", row["why"])

    def test_unconditional_unknown_on_empty_and_populated_cli_config(self):
        self._write_cursor_pair({})
        empty = checks.build_catalog(self._env())
        self._write_cursor_pair(_CURSOR_CLI_CONFIG, _SANDBOX_JSON)
        populated = checks.build_catalog(self._env())
        for catalog in (empty, populated):
            self.assertEqual(
                _row_by_id(catalog, "cursor-local-retention")["current_display"],
                "unknown",
            )
            self.assertEqual(
                _row_by_id(catalog, "cursor-cli-telemetry")["current_display"],
                "unknown",
            )

    def test_model_parameters_string_value_degrades_to_unknown(self):
        self._write_cursor_pair({"modelParameters": "not-an-object"})
        catalog = checks.build_catalog(self._env())
        mp = _row_by_id(catalog, "cursor-model-parameters")
        self.assertEqual(mp["current_display"], "unknown")

    def test_sandbox_json_independent_of_cli_config(self):
        self._write_cursor_pair(_CURSOR_CLI_CONFIG)
        catalog = checks.build_catalog(self._env())
        file_sb = _row_by_id(catalog, "cursor-sandbox-json")
        self.assertIn("workspace_readwrite", file_sb["current_display"])

        self._write_cursor_pair(_CURSOR_CLI_CONFIG, _SANDBOX_JSON)
        catalog = checks.build_catalog(self._env())
        file_sb = _row_by_id(catalog, "cursor-sandbox-json")
        self.assertIn("workspace_readonly", file_sb["current_display"])
        cli_sb = _row_by_id(catalog, "cursor-sandbox-cli-config")
        self.assertIn("mode=disabled", cli_sb["current_display"])

    def test_sandbox_json_survives_unreadable_cli_config(self):
        _write(os.path.join(self.cursor, "cli-config.json"), '{"approvalMode":')
        _write(
            os.path.join(self.cursor, "sandbox.json"),
            json.dumps(_SANDBOX_JSON),
        )
        catalog = checks.build_catalog(self._env())
        file_sb = _row_by_id(catalog, "cursor-sandbox-json")
        self.assertIn("workspace_readonly", file_sb["current_display"])
        cursor_rows = [
            row
            for section in catalog["sections"]
            if section["runtime"] == "cursor"
            for row in section["rows"]
        ]
        others = [row for row in cursor_rows if row["id"] != "cursor-sandbox-json"]
        self.assertTrue(others)
        for row in others:
            self.assertEqual(row["current_display"], "unknown")

    def test_absent_model_parameters_reports_none_configured(self):
        self._write_cursor_pair({})
        catalog = checks.build_catalog(self._env())
        mp = _row_by_id(catalog, "cursor-model-parameters")
        self.assertEqual(mp["current_display"], "no modelParameters configured")

    def test_sandbox_json_reader_docstring_cites_pitfall(self):
        doc = checks.read_cursor_sandbox_json.__doc__ or ""
        self.assertIn("Common Pitfall 5", doc)
        self.assertIn("Open Question 1", doc)

    def test_permanent_apply_none_why_text(self):
        by_id = {row.id: row for row in checks.CONFIG_DOCTOR_ROWS}
        for row_id in (
            "codex-hooks",
            "cursor-model-parameters",
            "cursor-local-retention",
            "cursor-cli-telemetry",
        ):
            self.assertIn("permanently", by_id[row_id].why)


_VERIFIED_RTK_SHOW = """\
rtk Configuration:

[ok] Hook: rtk hook claude (native binary command)
[ok] RTK.md: /home/bazzite/.claude/RTK.md (slim mode)
[ok] Global (~/.claude/CLAUDE.md): @RTK.md reference
[--] Local (./CLAUDE.md): not found
[ok] settings.json: RTK hook configured
[ok] OpenCode: plugin installed (/home/bazzite/.config/opencode/plugins/rtk.ts)
[ok] Cursor hook: registered in hooks.json
"""

_RTK_SHOW_NOT_REGISTERED = _VERIFIED_RTK_SHOW.replace(
    "[ok] Cursor hook: registered in hooks.json",
    "[--] Cursor hook: not registered",
)

_RTK_SHOW_NO_CURSOR_LINE = """\
rtk Configuration:

[ok] Hook: rtk hook claude (native binary command)
[ok] OpenCode: plugin installed (/home/bazzite/.config/opencode/plugins/rtk.ts)
"""


def _rtk_stub_body(stdout_text):
    return (
        "#!/bin/sh\n"
        "if [ \"$1\" = init ] && [ \"$2\" = --show ]; then\n"
        "cat <<'EOF'\n"
        f"{stdout_text}"
        "EOF\n"
        "fi\n"
        "exit 0\n"
    )


def _fake_bin(root, names, body):
    os.makedirs(root, exist_ok=True)
    for name in names:
        path = os.path.join(root, name)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(body)
        os.chmod(path, stat.S_IRWXU)
    return root


def _write_full_catalog_tree(scratch):
    """Realistic fixtures for all four runtimes under a _ScratchRuntimes tree."""
    _write(
        os.path.join(scratch.claude, "settings.json"),
        json.dumps({
            "cleanupPeriodDays": 15,
            "promptCacheTtl": "1h",
            "subagentPromptCacheTtl": "1h",
            "sandbox": {"enabled": True, "failIfUnavailable": False},
        }),
    )
    _write(
        os.path.join(scratch.opencode, "opencode.jsonc"),
        json.dumps({
            "share": "disabled",
            "permission": {"bash": "ask", "doom_loop": "ask"},
            "provider": {
                "router-env": {
                    "models": {
                        "my-coding": {"options": {"reasoningEffort": "high"}},
                    }
                }
            },
        }),
    )
    _write(os.path.join(scratch.codex, "config.toml"), _CODEX_TOML)
    _write(
        os.path.join(scratch.cursor, "cli-config.json"),
        json.dumps(_CURSOR_CLI_CONFIG),
    )
    _write(
        os.path.join(scratch.cursor, "sandbox.json"),
        json.dumps(_SANDBOX_JSON),
    )


class TestCrossRuntimeRow(_ScratchRuntimes):
    def test_appears_when_all_four_config_files_absent(self):
        catalog = checks.build_catalog(self._env())
        self.assertIn("cross", self._runtimes(catalog))
        row = _row_by_id(catalog, "rtk-cursor-integration")
        self.assertEqual(row["id"], "rtk-cursor-integration")
        self.assertTrue(row["current_display"])

    def test_rtk_absent_from_path(self):
        empty = os.path.join(self.tmp, "empty-bin")
        os.makedirs(empty)
        env = self._env()
        env["PATH"] = empty
        catalog = checks.build_catalog(env)
        row = _row_by_id(catalog, "rtk-cursor-integration")
        self.assertEqual(row["current_display"], "rtk not installed on PATH")

    def test_registered_against_verbatim_verified_block(self):
        bin_dir = _fake_bin(
            os.path.join(self.tmp, "bin"),
            ["rtk"],
            _rtk_stub_body(_VERIFIED_RTK_SHOW),
        )
        env = self._env()
        env["PATH"] = bin_dir + os.pathsep + os.environ.get("PATH", "")
        catalog = checks.build_catalog(env, runner=subprocess.run)
        row = _row_by_id(catalog, "rtk-cursor-integration")
        self.assertEqual(row["current_display"], "registered")
        self.assertEqual(row["confidence"], "HIGH")
        self.assertEqual(row["source"], "tools/hooks/README.md")
        self.assertIn("point-in-time", row["why"].lower())
        self.assertIn("re-probe", row["why"])

    def test_not_registered(self):
        bin_dir = _fake_bin(
            os.path.join(self.tmp, "bin"),
            ["rtk"],
            _rtk_stub_body(_RTK_SHOW_NOT_REGISTERED),
        )
        env = self._env()
        env["PATH"] = bin_dir + os.pathsep + os.environ.get("PATH", "")
        catalog = checks.build_catalog(env, runner=subprocess.run)
        row = _row_by_id(catalog, "rtk-cursor-integration")
        self.assertEqual(row["current_display"], "not registered")

    def test_unreadable_when_cursor_line_absent(self):
        bin_dir = _fake_bin(
            os.path.join(self.tmp, "bin"),
            ["rtk"],
            _rtk_stub_body(_RTK_SHOW_NO_CURSOR_LINE),
        )
        env = self._env()
        env["PATH"] = bin_dir + os.pathsep + os.environ.get("PATH", "")
        catalog = checks.build_catalog(env, runner=subprocess.run)
        row = _row_by_id(catalog, "rtk-cursor-integration")
        self.assertEqual(row["current_display"], "unreadable (see Why)")

    def test_probe_docstring_cites_research(self):
        doc = readers._probe_rtk_cursor_hook.__doc__ or ""
        self.assertIn("03-RESEARCH.md:527-540", doc)
        self.assertIn("not fixed by this research session", doc)
        self.assertIn("Cursor hook", doc)

    def test_cross_pass_has_no_isfile_gate(self):
        source = __import__("inspect").getsource(checks.build_catalog)
        cross_half = source.split("matching_cross", 1)[1]
        self.assertNotIn("os.path.isfile", cross_half)


class TestFullCatalogRegression(_ScratchRuntimes):
    def test_five_sections_twenty_five_rows(self):
        _write_full_catalog_tree(self)
        env = self._env()
        env["CLAUDE_CODE_ENABLE_TELEMETRY"] = "1"
        bin_dir = _fake_bin(
            os.path.join(self.tmp, "bin"),
            ["rtk"],
            _rtk_stub_body(_VERIFIED_RTK_SHOW),
        )
        env["PATH"] = bin_dir + os.pathsep + os.environ.get("PATH", "")
        catalog = checks.build_catalog(env, runner=subprocess.run)
        self.assertEqual(len(checks.CONFIG_DOCTOR_ROWS), 25)
        self.assertEqual(
            self._runtimes(catalog),
            ["claude", "opencode", "codex", "cursor", "cross"],
        )
        total = sum(len(section["rows"]) for section in catalog["sections"])
        self.assertEqual(total, 25)
        for section in catalog["sections"]:
            for row in section["rows"]:
                display = row["current_display"]
                self.assertIsInstance(display, str)
                self.assertTrue(display)
                self.assertIsNot(row["current_value"], None)
                self.assertNotIn("<object object", display)


def _parse_jsonc_via_reader(text):
    """Re-verify spliced JSONC through the reader's own strip+parse path."""
    stripped = readers.strip_trailing_commas(readers.strip_jsonc_comments(text))
    return json.loads(stripped)


_OPENCODE_JSONC_WITH_SHARE = """\
{
  // keep this comment byte-identical
  "share": "manual",
  "theme": "system",
  "nested": "value with { braces } and, commas"
}
"""

_OPENCODE_JSONC_WITHOUT_SHARE = """\
{
  // keep this comment byte-identical
  "theme": "system",
  "nested": "value with { braces } and, commas"
}
"""

_OPENCODE_JSONC_EMPTY = "{\n}\n"

_OPENCODE_JSONC_SINGLE_KEY = """\
{
  "theme": "system"
}
"""


class TestAppliers(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="ai-kit-cd-appliers-")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.appliers = load_appliers()

    def _path(self, name):
        return os.path.join(self.tmp, name)

    def _listing(self):
        return sorted(os.listdir(self.tmp))

    def test_atomic_write_json_round_trips_indent2_trailing_newline(self):
        path = self._path("settings.json")
        self.appliers.atomic_write_json(path, {"cleanupPeriodDays": 3650, "theme": "dark"})
        with open(path, encoding="utf-8") as handle:
            raw = handle.read()
        self.assertTrue(raw.endswith("\n"))
        self.assertEqual(json.loads(raw), {"cleanupPeriodDays": 3650, "theme": "dark"})
        self.assertIn("\n  ", raw)

    def test_atomic_write_json_preserves_existing_mode(self):
        path = self._path("settings.json")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("{}\n")
        os.chmod(path, 0o640)
        self.appliers.atomic_write_json(path, {"a": 1})
        self.assertEqual(stat.S_IMODE(os.stat(path).st_mode), 0o640)

    def test_atomic_write_json_fresh_file_is_mode_0600(self):
        path = self._path("settings.json")
        self.appliers.atomic_write_json(path, {"a": 1})
        self.assertEqual(stat.S_IMODE(os.stat(path).st_mode), 0o600)

    def test_atomic_write_json_failure_leaves_target_byte_identical(self):
        path = self._path("settings.json")
        original = b'{"keep": true}\n'
        with open(path, "wb") as handle:
            handle.write(original)
        listing = self._listing()

        def _boom(*_args, **_kwargs):
            raise OSError("injected replace failure")

        with mock.patch.object(os, "replace", side_effect=_boom), self.assertRaises(OSError):
            self.appliers.atomic_write_json(path, {"keep": False})
        with open(path, "rb") as handle:
            self.assertEqual(handle.read(), original)
        self.assertEqual(self._listing(), listing)

    def test_write_toml_region_replace_valid_round_trips(self):
        path = self._path("config.toml")
        new_text = 'sandbox_mode = "workspace-write"\n[history]\npersistence = "none"\n'
        self.assertTrue(self.appliers.write_toml_region_replace(path, new_text))
        with open(path, encoding="utf-8") as handle:
            written = handle.read()
        self.assertEqual(written, new_text)
        self.assertEqual(tomllib.loads(written)["history"]["persistence"], "none")

    def test_write_toml_region_replace_invalid_restores_original(self):
        path = self._path("config.toml")
        original = 'sandbox_mode = "workspace-write"\n'
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(original)
        self.assertFalse(self.appliers.write_toml_region_replace(path, "[[[not toml"))
        with open(path, encoding="utf-8") as handle:
            self.assertEqual(handle.read(), original)

    def test_write_toml_region_replace_failure_leaves_target_byte_identical(self):
        path = self._path("config.toml")
        original = b'sandbox_mode = "workspace-write"\n'
        with open(path, "wb") as handle:
            handle.write(original)
        listing = self._listing()

        def _boom(*_args, **_kwargs):
            raise OSError("injected replace failure")

        with mock.patch.object(os, "replace", side_effect=_boom):
            result = self.appliers.write_toml_region_replace(path, 'x = 1\n')
        self.assertFalse(result)
        with open(path, "rb") as handle:
            self.assertEqual(handle.read(), original)
        self.assertEqual(self._listing(), listing)

    def test_set_jsonc_value_replaces_existing_top_level_key(self):
        text = _OPENCODE_JSONC_WITH_SHARE
        result = self.appliers.set_jsonc_value(text, ("share",), "disabled")
        parsed = _parse_jsonc_via_reader(result)
        self.assertEqual(parsed["share"], "disabled")
        self.assertIn("// keep this comment byte-identical", result)
        self.assertIn('"theme": "system"', result)
        self.assertIn('"nested": "value with { braces } and, commas"', result)
        self.assertEqual(parsed["theme"], "system")
        self.assertEqual(parsed["nested"], "value with { braces } and, commas")
        tmp = self._path("opencode.jsonc")
        with open(tmp, "w", encoding="utf-8") as handle:
            handle.write(result)
        state, data = readers.read_jsonc_checked(tmp)
        self.assertEqual(state, "ok")
        self.assertEqual(data["share"], "disabled")

    def test_set_jsonc_value_inserts_missing_key_as_last(self):
        text = _OPENCODE_JSONC_WITHOUT_SHARE
        result = self.appliers.set_jsonc_value(text, ("share",), "disabled")
        parsed = _parse_jsonc_via_reader(result)
        self.assertEqual(parsed["share"], "disabled")
        self.assertIn("// keep this comment byte-identical", result)
        self.assertIn('"theme": "system"', result)
        self.assertIn('"nested": "value with { braces } and, commas"', result)
        tmp = self._path("opencode.jsonc")
        with open(tmp, "w", encoding="utf-8") as handle:
            handle.write(result)
        state, data = readers.read_jsonc_checked(tmp)
        self.assertEqual(state, "ok")
        self.assertEqual(data["share"], "disabled")

    def test_set_jsonc_value_inserts_into_empty_object(self):
        result = self.appliers.set_jsonc_value(_OPENCODE_JSONC_EMPTY, ("share",), "disabled")
        parsed = _parse_jsonc_via_reader(result)
        self.assertEqual(parsed, {"share": "disabled"})
        tmp = self._path("opencode.jsonc")
        with open(tmp, "w", encoding="utf-8") as handle:
            handle.write(result)
        state, data = readers.read_jsonc_checked(tmp)
        self.assertEqual(state, "ok")
        self.assertEqual(data, {"share": "disabled"})

    def test_set_jsonc_value_inserts_after_single_existing_key(self):
        result = self.appliers.set_jsonc_value(
            _OPENCODE_JSONC_SINGLE_KEY, ("share",), "disabled"
        )
        parsed = _parse_jsonc_via_reader(result)
        self.assertEqual(parsed["share"], "disabled")
        self.assertEqual(parsed["theme"], "system")

    def test_set_jsonc_value_nested_path_raises_not_implemented(self):
        with self.assertRaises(NotImplementedError) as ctx:
            self.appliers.set_jsonc_value("{}", ("sandbox", "enabled"), True)
        message = str(ctx.exception)
        self.assertIn("nested key paths", message)
        self.assertIn("depth 2", message)

    def test_set_jsonc_value_does_not_touch_comment_or_in_string_braces(self):
        text = _OPENCODE_JSONC_WITH_SHARE
        result = self.appliers.set_jsonc_value(text, ("share",), "disabled")
        comment_line = next(ln for ln in text.splitlines() if "keep this comment" in ln)
        self.assertIn(comment_line, result)
        self.assertIn("value with { braces } and, commas", result)
        parsed = _parse_jsonc_via_reader(result)
        self.assertEqual(parsed["nested"], "value with { braces } and, commas")


class TestApplyRows(_ScratchRuntimes):
    def _ctx(self):
        return checks.ReadContext(data=None, env=self._env(), runner=None)

    def test_checkrow_has_apply_target_and_security_relevant(self):
        self.assertIn("apply_target", checks.CheckRow._fields)
        self.assertIn("security_relevant", checks.CheckRow._fields)
        self.assertEqual(checks.ReadContext._fields, ("data", "env", "runner"))
        retention = next(r for r in checks.CONFIG_DOCTOR_ROWS if r.id == "claude-retention")
        self.assertEqual(retention.apply_target, 3650)
        self.assertFalse(retention.security_relevant)
        sandbox = next(r for r in checks.CONFIG_DOCTOR_ROWS if r.id == "claude-sandbox-enabled")
        self.assertIs(sandbox.apply_target, True)
        self.assertTrue(sandbox.security_relevant)
        unwired = next(r for r in checks.CONFIG_DOCTOR_ROWS if r.id == "opencode-retention")
        self.assertIsNone(unwired.apply)
        self.assertIsNone(unwired.apply_target)
        self.assertFalse(unwired.security_relevant)

    def test_evaluate_row_surfaces_apply_fields_without_changing_display(self):
        _write(
            os.path.join(self.claude, "settings.json"),
            json.dumps({"cleanupPeriodDays": 15}),
        )
        catalog = checks.build_catalog(self._env())
        row = _row_by_id(catalog, "claude-retention")
        self.assertEqual(row["current_display"], "15")
        self.assertEqual(row["recommended_display"], "3650")
        self.assertEqual(row["apply_target"], 3650)
        self.assertFalse(row["security_relevant"])
        self.assertTrue(row["apply_eligible"])
        sandbox = _row_by_id(catalog, "claude-sandbox-enabled")
        self.assertTrue(sandbox["security_relevant"])

    def test_apply_claude_retention_writes_3650_and_preserves_siblings(self):
        path = os.path.join(self.claude, "settings.json")
        _write(path, json.dumps({"cleanupPeriodDays": 5, "theme": "dark"}))
        result = checks.apply_row("claude-retention", self._ctx(), dry=False)
        self.assertTrue(result["ok"])
        self.assertEqual(result["before"], 5)
        self.assertEqual(result["after"], 3650)
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
        self.assertEqual(data["cleanupPeriodDays"], 3650)
        self.assertEqual(data["theme"], "dark")
        self.assertNotIn("literal_resulting_config", result)

    def test_apply_claude_retention_refuses_zero_without_writing(self):
        path = os.path.join(self.claude, "settings.json")
        original = json.dumps({"cleanupPeriodDays": 5})
        _write(path, original)
        result = checks._apply_claude_retention(self._ctx(), 0, dry=False)
        self.assertFalse(result["ok"])
        self.assertIn("cleanupPeriodDays 0 is never writable", result["reason"])
        with open(path, encoding="utf-8") as handle:
            self.assertEqual(handle.read(), original)

    def test_apply_row_converts_applier_exception(self):
        def _boom(_ctx, _target, _dry):
            raise RuntimeError("injected")

        fake = checks.CheckRow(
            id="fake-boom",
            runtime="claude",
            scope="runtime",
            check="boom",
            read=lambda _ctx: None,
            recommended=None,
            confidence="HIGH",
            why="test",
            source="test",
            apply=_boom,
        )
        checks.CONFIG_DOCTOR_ROWS.append(fake)
        try:
            result = checks.apply_row("fake-boom", self._ctx(), dry=False)
        finally:
            checks.CONFIG_DOCTOR_ROWS.pop()
        self.assertFalse(result["ok"])
        self.assertIn("applier error", result["reason"])
        self.assertIn("injected", result["reason"])

    def test_apply_claude_sandbox_preserves_sibling_and_carries_literal(self):
        path = os.path.join(self.claude, "settings.json")
        _write(
            path,
            json.dumps({
                "sandbox": {"enabled": False, "failIfUnavailable": True},
                "theme": "dark",
            }),
        )
        dry = checks.apply_row("claude-sandbox-enabled", self._ctx(), dry=True)
        self.assertTrue(dry["ok"])
        self.assertIn("literal_resulting_config", dry)
        lit = dry["literal_resulting_config"]
        if isinstance(lit, str):
            lit = json.loads(lit)
        self.assertIs(lit["sandbox"]["enabled"], True)
        self.assertIs(lit["sandbox"]["failIfUnavailable"], True)
        with open(path, encoding="utf-8") as handle:
            on_disk = json.load(handle)
        self.assertIs(on_disk["sandbox"]["enabled"], False)

        result = checks.apply_row("claude-sandbox-enabled", self._ctx(), dry=False)
        self.assertTrue(result["ok"])
        self.assertIn("literal_resulting_config", result)
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
        self.assertIs(data["sandbox"]["enabled"], True)
        self.assertIs(data["sandbox"]["failIfUnavailable"], True)
        self.assertEqual(data["theme"], "dark")

    def test_apply_claude_sandbox_enabled_normalizes_non_dict_sandbox_value(self):
        """A present-but-non-dict "sandbox" value must not crash the applier.

        dict.setdefault only inserts a default when the key is ABSENT; since
        "sandbox" is already present here (as a string), a naive setdefault
        would return that string unchanged and the next .get("enabled") call
        would raise AttributeError. apply_row's generic except would still
        catch that, but the applier should refuse cleanly / normalize instead
        of surfacing a raw Python exception message as the refusal reason.
        """
        path = os.path.join(self.claude, "settings.json")
        _write(path, json.dumps({"sandbox": "not-a-dict", "theme": "dark"}))
        result = checks.apply_row("claude-sandbox-enabled", self._ctx(), dry=False)
        self.assertTrue(result["ok"])
        self.assertIsNone(result["before"])
        self.assertIs(result["after"], True)
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
        self.assertIs(data["sandbox"]["enabled"], True)
        self.assertEqual(data["theme"], "dark")

    def test_apply_opencode_share_mode_sets_disabled_and_preserves_bytes(self):
        path = os.path.join(self.opencode, "opencode.jsonc")
        _write(path, _OPENCODE_JSONC_WITH_SHARE)
        result = checks.apply_row("opencode-share-mode", self._ctx(), dry=False)
        self.assertTrue(result["ok"])
        with open(path, encoding="utf-8") as handle:
            written = handle.read()
        self.assertIn("// keep this comment byte-identical", written)
        self.assertIn('"theme": "system"', written)
        parsed = _parse_jsonc_via_reader(written)
        self.assertEqual(parsed["share"], "disabled")

        _write(path, _OPENCODE_JSONC_WITHOUT_SHARE)
        result = checks.apply_row("opencode-share-mode", self._ctx(), dry=False)
        self.assertTrue(result["ok"])
        with open(path, encoding="utf-8") as handle:
            written = handle.read()
        self.assertIn("// keep this comment byte-identical", written)
        self.assertEqual(_parse_jsonc_via_reader(written)["share"], "disabled")

    def test_apply_opencode_share_mode_refuses_invalid_splice_without_write(self):
        path = os.path.join(self.opencode, "opencode.jsonc")
        _write(path, _OPENCODE_JSONC_WITH_SHARE)
        with open(path, "rb") as handle:
            before = handle.read()
        with mock.patch.object(
            checks.config_doctor_appliers, "set_jsonc_value", return_value="{not-json"
        ), mock.patch.object(
            checks.config_doctor_appliers, "_atomic_write_text"
        ) as writer:
            result = checks.apply_row("opencode-share-mode", self._ctx(), dry=False)
        self.assertFalse(result["ok"])
        self.assertIn("spliced JSONC failed self-validation", result["reason"])
        writer.assert_not_called()
        with open(path, "rb") as handle:
            self.assertEqual(handle.read(), before)

    def test_apply_codex_history_persistence_three_upsert_cases(self):
        path = os.path.join(self.codex, "config.toml")
        _write(path, _CODEX_TOML)
        result = checks.apply_row("codex-history-persistence", self._ctx(), dry=False)
        self.assertTrue(result["ok"])
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
        parsed = tomllib.loads(text)
        self.assertEqual(parsed["history"]["persistence"], "none")
        self.assertEqual(parsed["history"]["max_bytes"], 1048576)
        self.assertEqual(parsed["sandbox_mode"], "workspace-write")
        self.assertTrue(parsed["features"]["hooks"])

        no_key = 'sandbox_mode = "workspace-write"\n\n[history]\nmax_bytes = 10\n'
        _write(path, no_key)
        result = checks.apply_row("codex-history-persistence", self._ctx(), dry=False)
        self.assertTrue(result["ok"])
        with open(path, encoding="utf-8") as handle:
            parsed = tomllib.loads(handle.read())
        self.assertEqual(parsed["history"]["persistence"], "none")
        self.assertEqual(parsed["history"]["max_bytes"], 10)

        absent = 'sandbox_mode = "workspace-write"\n'
        _write(path, absent)
        result = checks.apply_row("codex-history-persistence", self._ctx(), dry=False)
        self.assertTrue(result["ok"])
        with open(path, encoding="utf-8") as handle:
            parsed = tomllib.loads(handle.read())
        self.assertEqual(parsed["history"]["persistence"], "none")
        self.assertEqual(parsed["sandbox_mode"], "workspace-write")

    def test_apply_codex_history_persistence_ignores_decoy_bracket_text_in_comment(self):
        """A "[history]"-shaped comment before the real table must not divert the write.

        _toml_table_span used to be a raw text.find("[history]") substring
        search, so a comment like "# ... [history] ..." above the real
        [history] table would be mistaken for the table header and the
        splice would land in the wrong place. The line-anchored regex fix
        must find the REAL table only.
        """
        path = os.path.join(self.codex, "config.toml")
        decoy = (
            'sandbox_mode = "workspace-write"\n'
            "# see [history] below for persistence config\n"
            "\n"
            "[history]\n"
            'max_bytes = 1048576\n'
            'persistence = "save-all"\n'
        )
        _write(path, decoy)
        result = checks.apply_row("codex-history-persistence", self._ctx(), dry=False)
        self.assertTrue(result["ok"])
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
        self.assertIn("# see [history] below for persistence config", text)
        parsed = tomllib.loads(text)
        self.assertEqual(parsed["history"]["persistence"], "none")
        self.assertEqual(parsed["history"]["max_bytes"], 1048576)
        self.assertEqual(parsed["sandbox_mode"], "workspace-write")

    def test_apply_row_dry_true_writes_nothing(self):
        claude = os.path.join(self.claude, "settings.json")
        _write(claude, json.dumps({"cleanupPeriodDays": 5}))
        with open(claude, "rb") as handle:
            before = handle.read()
        result = checks.apply_row("claude-retention", self._ctx(), dry=True)
        self.assertTrue(result["ok"])
        self.assertEqual(result["after"], 3650)
        with open(claude, "rb") as handle:
            self.assertEqual(handle.read(), before)

        openc = os.path.join(self.opencode, "opencode.jsonc")
        _write(openc, _OPENCODE_JSONC_WITH_SHARE)
        with open(openc, "rb") as handle:
            before = handle.read()
        result = checks.apply_row("opencode-share-mode", self._ctx(), dry=True)
        self.assertTrue(result["ok"])
        with open(openc, "rb") as handle:
            self.assertEqual(handle.read(), before)

        codex = os.path.join(self.codex, "config.toml")
        _write(codex, _CODEX_TOML)
        with open(codex, "rb") as handle:
            before = handle.read()
        result = checks.apply_row("codex-history-persistence", self._ctx(), dry=True)
        self.assertTrue(result["ok"])
        with open(codex, "rb") as handle:
            self.assertEqual(handle.read(), before)

        _write(claude, json.dumps({"sandbox": {"enabled": False}}))
        with open(claude, "rb") as handle:
            before = handle.read()
        result = checks.apply_row("claude-sandbox-enabled", self._ctx(), dry=True)
        self.assertTrue(result["ok"])
        with open(claude, "rb") as handle:
            self.assertEqual(handle.read(), before)

    def test_apply_row_not_eligible_performs_no_write(self):
        path = os.path.join(self.opencode, "opencode.jsonc")
        _write(path, _OPENCODE_JSONC_WITH_SHARE)
        with open(path, "rb") as handle:
            before = handle.read()
        result = checks.apply_row("opencode-retention", self._ctx(), dry=False)
        self.assertEqual(result, {"ok": False, "reason": "not apply-eligible"})
        with open(path, "rb") as handle:
            self.assertEqual(handle.read(), before)
        missing = checks.apply_row("no-such-row", self._ctx(), dry=False)
        self.assertEqual(missing, {"ok": False, "reason": "not apply-eligible"})

    def test_cmd_config_doctor_injects_apply_closure(self):
        with open(os.path.join(_TOOLS_DIR, "setup.py"), encoding="utf-8") as handle:
            text = handle.read()
        start = text.find("def cmd_config_doctor")
        self.assertGreater(start, 0)
        nxt = text.find("\ndef ", start + 1)
        body = text[start:nxt]
        self.assertIn("apply_row", body)
        self.assertIn("ReadContext(data=None, env=env, runner=None)", body)
        self.assertNotIn("apply=None", body)
        self.assertIn("TOCTOU", body)


_BULK_APPLY_NAME = re.compile(
    r"\b(?:apply_all|bulk_apply|apply_every_row|apply_rows|apply_selected|"
    r"apply_each|apply_many|apply_every)\b",
    re.IGNORECASE,
)
_BULK_APPLY_DEF = re.compile(
    r"^\s*(?:async\s+)?def\s+(\w*(?:apply\w*(?:all|bulk|many|every|rows|"
    r"selected|each)|(?:all|bulk|many|every|rows|selected|each)\w*apply)\w*)"
    r"\s*\(",
    re.IGNORECASE | re.MULTILINE,
)


class TestNoBulkApply(unittest.TestCase):
    """Naming-convention TRIPWIRE, not an exhaustive structural proof.

    A helper named ``_do_it`` that happens to loop over multiple rows
    internally would not be caught by any name pattern. The PRIMARY
    guarantee is architectural: ``apply_row``'s own signature takes exactly
    one ``row_id``, and every call site (the confirm modal's
    ``ctx.apply(row_id, dry=False)``) passes exactly one. This test
    cross-checks that guarantee at the naming level; it does not replace it.
    """

    _SCAN_FILES = (
        "tools/config_doctor_checks.py",
        "tools/config_doctor_appliers.py",
        "tools/config_doctor_app.py",
    )

    def test_no_bulk_apply_function_names(self):
        hits = []
        for rel in self._SCAN_FILES:
            path = os.path.join(_REPO, rel)
            with open(path, encoding="utf-8") as handle:
                text = handle.read()
            for match in _BULK_APPLY_DEF.finditer(text):
                hits.append(f"{rel}:{match.group(1)}")
            for match in _BULK_APPLY_NAME.finditer(text):
                hits.append(f"{rel}:{match.group(0)}")
        self.assertEqual(hits, [])

    def test_no_bulk_apply_binding_action_names(self):
        app = load_app()
        bindings = getattr(app.ConfigDoctorApp, "BINDINGS", [])
        hits = []
        for binding in bindings:
            action = binding[1] if isinstance(binding, (tuple, list)) else str(binding)
            if _BULK_APPLY_NAME.search(str(action)) or _BULK_APPLY_DEF.search(
                f"def {action}("
            ):
                hits.append(str(action))
        self.assertEqual(hits, [])


def load_app():
    """Load config_doctor_app.py. Requires textual (run under uv)."""
    try:
        import textual  # noqa: F401
    except ImportError:
        raise unittest.SkipTest("textual not installed (run under uv)") from None
    if _TOOLS_DIR not in sys.path:
        sys.path.insert(0, _TOOLS_DIR)
    path = os.path.join(_TOOLS_DIR, "config_doctor_app.py")
    spec = importlib.util.spec_from_file_location("config_doctor_app", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["config_doctor_app"] = mod
    spec.loader.exec_module(mod)
    return mod


try:
    import textual  # noqa: F401

    _HAVE_TEXTUAL = True
except ImportError:
    _HAVE_TEXTUAL = False


@unittest.skipUnless(_HAVE_TEXTUAL, "textual not installed (run under uv)")
class TestConfirmApplyScreen(unittest.IsolatedAsyncioTestCase):
    def _row(self, **overrides):
        row = {
            "id": "claude-retention",
            "check": "Local transcript retention (cleanupPeriodDays)",
            "current_display": "5",
            "apply_target": 3650,
            "apply_eligible": True,
            "security_relevant": False,
            "why": "why",
            "source": "src",
            "recommended_display": "3650",
        }
        row.update(overrides)
        return row

    def _catalog(self, *rows):
        return {"sections": [{"runtime": "claude", "rows": list(rows)}]}

    async def test_cancel_calls_apply_zero_times(self):
        app_mod = load_app()
        calls = []

        def apply(row_id, dry):
            calls.append((row_id, dry))
            return {"ok": True, "after": 3650, "current_display": "3650"}

        row = self._row()
        ctx = app_mod.ConfigDoctorContext(catalog=self._catalog(row), apply=apply)
        app = app_mod.ConfigDoctorApp(ctx)
        async with app.run_test() as pilot:
            await pilot.press("a")
            screen = app.screen
            self.assertIsInstance(screen, app_mod.ConfirmApplyScreen)
            body = str(screen.query_one("#confirm-body").content)
            self.assertIn("5", body)
            self.assertIn("3650", body)
            await pilot.press("escape")
        self.assertEqual(calls, [])

    async def test_confirm_calls_apply_once_and_refreshes_display(self):
        app_mod = load_app()
        calls = []

        def apply(row_id, dry):
            calls.append((row_id, dry))
            if dry:
                return {"ok": True, "after": 3650, "current_display": "3650"}
            return {"ok": True, "after": 3650, "current_display": "3650"}

        row = self._row()
        ctx = app_mod.ConfigDoctorContext(catalog=self._catalog(row), apply=apply)
        app = app_mod.ConfigDoctorApp(ctx)
        async with app.run_test() as pilot:
            await pilot.press("a")
            self.assertIsInstance(app.screen, app_mod.ConfirmApplyScreen)
            await pilot.press("y")
            table = app.query_one("#catalog-table")
            cell = table.get_cell(row["id"], table.ordered_columns[2].key)
            self.assertEqual(str(cell), "3650")
        self.assertEqual(calls, [("claude-retention", False)])

    async def test_refused_apply_surfaces_reason_and_leaves_cell(self):
        app_mod = load_app()
        calls = []

        def apply(row_id, dry):
            calls.append((row_id, dry))
            return {"ok": False, "reason": "refused: cleanupPeriodDays 0 is never writable"}

        row = self._row(current_display="5")
        ctx = app_mod.ConfigDoctorContext(catalog=self._catalog(row), apply=apply)
        app = app_mod.ConfigDoctorApp(ctx)
        async with app.run_test() as pilot:
            await pilot.press("a")
            await pilot.press("y")
            self.assertIsInstance(app.screen, app_mod.ConfirmApplyScreen)
            body = str(app.screen.query_one("#confirm-body").content)
            self.assertIn("never writable", body)
            table = app.query_one("#catalog-table")
            cell = table.get_cell(row["id"], table.ordered_columns[2].key)
            self.assertEqual(str(cell), "5")
            await pilot.press("escape")
        self.assertEqual(calls, [("claude-retention", False)])

    async def test_security_relevant_preview_shows_literal_config(self):
        app_mod = load_app()

        def apply(row_id, dry):
            if dry:
                return {
                    "ok": True,
                    "literal_resulting_config": {"sandbox": {"enabled": True}},
                    "after": True,
                }
            return {"ok": True, "after": True, "current_display": "True"}

        row = self._row(
            id="claude-sandbox-enabled",
            check="Sandboxed Bash tool (sandbox.enabled)",
            current_display="False",
            apply_target=True,
            security_relevant=True,
        )
        ctx = app_mod.ConfigDoctorContext(catalog=self._catalog(row), apply=apply)
        app = app_mod.ConfigDoctorApp(ctx)
        async with app.run_test() as pilot:
            await pilot.press("a")
            body = str(app.screen.query_one("#confirm-body").content)
            self.assertIn("sandbox", body)
            self.assertIn("enabled", body)

    async def test_ineligible_row_a_key_is_silent_noop(self):
        app_mod = load_app()
        calls = []

        def apply(row_id, dry):
            calls.append((row_id, dry))
            return {"ok": True}

        row = self._row(
            id="opencode-retention",
            check="Session retention",
            apply_eligible=False,
            apply_target=None,
        )
        ctx = app_mod.ConfigDoctorContext(catalog=self._catalog(row), apply=apply)
        app = app_mod.ConfigDoctorApp(ctx)
        async with app.run_test() as pilot:
            await pilot.press("a")
            self.assertNotIsInstance(app.screen, app_mod.ConfirmApplyScreen)
        self.assertEqual(calls, [])

