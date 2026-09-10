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
        self.assertIn("claude", [s["runtime"] for s in catalog["sections"]])
        section = next(s for s in catalog["sections"] if s["runtime"] == "claude")
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

