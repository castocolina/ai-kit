"""One runtime-id table: snapshot keys, legacy names, and host precedence (18.1 R1)."""

import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills", "ai-kit-spec-review"))

from ai_kit_spec import commands, detection
from ai_kit_spec.cli import main
from ai_kit_spec.detection import normalize_runtime_keys, runtime_id
from ai_kit_spec.model_catalog import split_catalog_meta

_SCRUB_NAMES = {
    "AI_AGENT",
    "CLAUDECODE",
    "CLAUDE_CODE_ENTRYPOINT",
    "CLAUDE_CODE_SSE_PORT",
    "OPENCODE",
    "CURSOR_AGENT",
    "PI_CODING_AGENT",
    "CODEX_THREAD_ID",
    "CODEX_SANDBOX",
    "GROK_AGENT",
    "CODEX_VERSION",
}


class _ModelsResult:
    stdout = "auto - Auto\n"
    returncode = 0


class TestRuntimeTracer(unittest.TestCase):
    def test_cursor_host_matches_cursor_snapshot(self):
        def which_fn(name):
            if name in ("cursor-agent", "node"):
                return f"/usr/bin/{name}"
            return None

        buf = io.StringIO()
        with redirect_stdout(buf):
            code = main(
                ["detect-runtimes"],
                which_fn=which_fn,
                run_fn=lambda *_a, **_k: _ModelsResult(),
            )
        self.assertEqual(code, 0)
        snapshot = json.loads(buf.getvalue())
        self.assertEqual(snapshot["schema_version"], 5)
        cursor = snapshot["clis"]["cursor"]
        self.assertTrue(cursor["installed"])
        self.assertEqual(cursor["models"], ["auto"])
        self.assertNotIn("cursor-agent", snapshot["clis"])
        self.assertTrue(snapshot["node"]["installed"])
        host = detection.detect_current_runtime({"CURSOR_AGENT": "1"})
        self.assertEqual(host, "cursor")
        self.assertIn(host, snapshot["clis"])


class TestRuntimeTable(unittest.TestCase):
    def test_ids_follow_host_precedence_and_known_clis(self):
        self.assertEqual(
            list(detection.RUNTIMES),
            ["pi", "opencode", "cursor", "codex", "claude", "grok"],
        )
        self.assertEqual(detection.KNOWN_CLIS, tuple(detection.RUNTIMES))
        self.assertTrue(detection.RUNTIMES["claude"].review_only)
        self.assertFalse(detection.RUNTIMES["grok"].runner)
        self.assertEqual(detection.RUNTIMES["cursor"].model_suffix, r"\[[^\]]*\]$")

    def test_grok_agent_is_never_a_detected_host(self):
        self.assertEqual(detection.detect_current_runtime({"GROK_AGENT": "1"}), "unknown")

    def test_scrub_set_keeps_the_same_eleven_names(self):
        self.assertEqual(detection.HOST_SIGNAL_ENV_VARS, _SCRUB_NAMES)
        self.assertEqual(len(detection.HOST_SIGNAL_ENV_VARS), 11)

    def test_precedence_pairs(self):
        pairs = (
            ({"PI_CODING_AGENT": "1", "OPENCODE": "1"}, "pi"),
            ({"OPENCODE": "1", "CURSOR_AGENT": "1"}, "opencode"),
            ({"CURSOR_AGENT": "1", "CODEX_THREAD_ID": "1"}, "cursor"),
            ({"CODEX_THREAD_ID": "1", "CLAUDECODE": "1"}, "codex"),
        )
        for env, expected in pairs:
            self.assertEqual(detection.detect_current_runtime(env), expected)


class TestCatalogRuntimeMigration(unittest.TestCase):
    def test_schema_2_renames_cursor_agent_and_keeps_confirmations(self):
        raw = {
            "_meta": {"schema_version": 2},
            "openai/x": {
                "provider": "openai",
                "runtimes": {"cursor-agent": {"model_id": "x"}},
                "heuristic_confirmed": ["is_router"],
            },
        }
        entries, _meta = split_catalog_meta(raw)
        entry = entries["openai/x"]
        self.assertEqual(entry["runtimes"], {"cursor": {"model_id": "x"}})
        self.assertEqual(entry["heuristic_confirmed"], ["is_router"])
        self.assertEqual(raw["openai/x"]["runtimes"], {"cursor-agent": {"model_id": "x"}})

    def test_cursor_value_wins_when_both_keys_exist(self):
        raw = {
            "_meta": {"schema_version": 2},
            "openai/x": {
                "runtimes": {
                    "cursor-agent": {"model_id": "legacy"},
                    "cursor": {"model_id": "x"},
                },
            },
        }
        entries, _meta = split_catalog_meta(raw)
        self.assertEqual(entries["openai/x"]["runtimes"], {"cursor": {"model_id": "x"}})

    def test_schema_3_is_returned_unrenamed(self):
        raw = {
            "_meta": {"schema_version": 3},
            "openai/x": {"runtimes": {"cursor-agent": {"model_id": "x"}}},
        }
        entries, _meta = split_catalog_meta(raw)
        self.assertEqual(entries["openai/x"]["runtimes"], {"cursor-agent": {"model_id": "x"}})
        self.assertIs(entries["openai/x"], raw["openai/x"])

    def test_missing_meta_counts_as_old(self):
        raw = {"openai/x": {"runtimes": {"cursor-agent": {"model_id": "x"}}}}
        entries, meta = split_catalog_meta(raw)
        self.assertEqual(meta, {})
        self.assertEqual(entries["openai/x"]["runtimes"], {"cursor": {"model_id": "x"}})


class TestRuntimeId(unittest.TestCase):
    def test_legacy_names_map_to_cursor_and_unknown_names_pass_through(self):
        self.assertEqual(runtime_id("cursor-agent"), "cursor")
        self.assertEqual(runtime_id("agent"), "cursor")
        self.assertEqual(runtime_id("opencode"), "opencode")
        self.assertEqual(runtime_id("not-a-runtime"), "not-a-runtime")


class TestNormalizeRuntimeKeys(unittest.TestCase):
    def test_id_key_wins_and_input_is_unchanged(self):
        src = {"cursor-agent": "legacy", "cursor": "id"}
        self.assertEqual(normalize_runtime_keys(src), {"cursor": "id"})
        self.assertEqual(src, {"cursor-agent": "legacy", "cursor": "id"})

    def test_non_dict_returns_empty(self):
        self.assertEqual(normalize_runtime_keys(None), {})
        self.assertEqual(normalize_runtime_keys("cursor-agent"), {})
        self.assertEqual(normalize_runtime_keys(["cursor"]), {})


def _which_in(directory):
    def which_fn(name):
        path = os.path.join(directory, name)
        return path if os.path.exists(path) else None

    return which_fn


def _touch(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8"):
        pass


class TestGuardedAgentBinary(unittest.TestCase):
    def test_agent_symlink_to_cursor_agent_resolves(self):
        with tempfile.TemporaryDirectory() as tmp:
            bin_dir = os.path.join(tmp, "bin")
            os.makedirs(bin_dir)
            real = os.path.join(tmp, "versions", "cursor-agent")
            _touch(real)
            agent = os.path.join(bin_dir, "agent")
            os.symlink(real, agent)
            found = detection.resolve_runtime_binary("cursor", which_fn=_which_in(bin_dir))
            self.assertEqual(found, agent)

    def test_agent_symlink_to_grok_does_not_resolve(self):
        with tempfile.TemporaryDirectory() as tmp:
            bin_dir = os.path.join(tmp, "bin")
            os.makedirs(bin_dir)
            real = os.path.join(tmp, "grok", "grok-1.0.52-linux-x86_64")
            _touch(real)
            os.symlink(real, os.path.join(bin_dir, "agent"))
            found = detection.resolve_runtime_binary("cursor", which_fn=_which_in(bin_dir))
            self.assertIsNone(found)

    def test_cursor_agent_wins_when_both_are_present(self):
        with tempfile.TemporaryDirectory() as tmp:
            bin_dir = os.path.join(tmp, "bin")
            os.makedirs(bin_dir)
            cursor_agent = os.path.join(bin_dir, "cursor-agent")
            _touch(cursor_agent)
            real = os.path.join(tmp, "versions", "cursor-agent")
            _touch(real)
            os.symlink(real, os.path.join(bin_dir, "agent"))
            found = detection.resolve_runtime_binary("cursor", which_fn=_which_in(bin_dir))
            self.assertEqual(found, cursor_agent)

    def test_no_binaries_maps_every_id_to_none(self):
        result = detection.detect_installed_clis(which_fn=lambda _name: None)
        self.assertEqual(set(result), set(detection.RUNTIMES))
        self.assertEqual(set(result.values()), {None})


class TestLegacyEntryPoints(unittest.TestCase):
    def test_install_hint_and_mcp_list_use_the_cursor_id(self):
        for name in ("cursor", "cursor-agent"):
            command = detection.codegraph_install_command(name)
            self.assertIn("--target=cursor", command)
            self.assertNotIn("--target=cursor-agent", command)
        self.assertEqual(
            detection._MCP_LIST_COMMANDS["cursor"],
            ("cursor-agent", "mcp", "list"),
        )

    def test_find_alternative_reads_a_legacy_snapshot_key(self):
        snapshot = {
            "clis": {"cursor-agent": {"installed": True, "models": ["grok-4.6"]}},
        }
        self.assertEqual(
            detection.find_codegraph_alternative("grok", "grok-4.6", snapshot),
            "cursor",
        )

    def test_builders_accept_the_legacy_name(self):
        self.assertEqual(
            commands.build_reviewer_command("cursor"),
            commands.build_reviewer_command("cursor-agent"),
        )
        self.assertTrue(commands.build_reviewer_command("cursor").startswith("cursor-agent -p"))
        self.assertIsNone(commands.execute_cli_error("cursor"))
        self.assertIsNone(commands.execute_cli_error("cursor-agent"))
        rejection = commands.execute_cli_error("claude")
        self.assertIsNotNone(rejection)
        assert rejection is not None
        self.assertIn("cannot be an execution CLI", rejection)
        self.assertEqual(
            commands.build_reviewer_model_id("cursor", "m", effort="high"),
            "m[effort=high]",
        )

    def test_cli_runtime_flag_matches_the_legacy_alias(self):
        legacy = io.StringIO()
        with redirect_stdout(legacy):
            code_legacy = main(["build-command", "--cli", "cursor-agent", "--mode", "ask"])
        current = io.StringIO()
        with redirect_stdout(current):
            code_current = main(["build-command", "--runtime", "cursor", "--mode", "ask"])
        self.assertEqual(code_legacy, 0)
        self.assertEqual(code_current, 0)
        self.assertEqual(legacy.getvalue(), current.getvalue())

    def test_group_models_reads_legacy_and_id_snapshot_keys(self):
        for key in ("cursor-agent", "cursor"):
            with tempfile.TemporaryDirectory() as tmp, self.subTest(key=key):
                path = os.path.join(tmp, "runtimes.json")
                with open(path, "w", encoding="utf-8") as handle:
                    json.dump({"clis": {key: {"installed": True, "models": ["auto"]}}}, handle)
                buf = io.StringIO()
                with redirect_stdout(buf):
                    code = main(["group-models", "--runtimes-json", path, "--runtime", "cursor"])
                self.assertEqual(code, 0)
                self.assertIn("auto", buf.getvalue())


class TestRegistryIdsInTable(unittest.TestCase):
    def test_command_and_codegraph_registries_use_table_ids(self):
        ids = set(detection.RUNTIMES)
        builder_clis = {cli_name for _kind, cli_name in commands._COMMAND_BUILDERS}
        self.assertTrue(builder_clis <= ids)
        self.assertTrue(set(commands.SUPPORTED_EXECUTE_CLIS) <= ids)
        self.assertTrue(set(commands.NO_HARD_SANDBOX_CLIS) <= ids)
        self.assertTrue(set(detection._SUPPORTED_CODEGRAPH_CLIENTS) <= ids)
        self.assertTrue(set(detection._MCP_LIST_COMMANDS) <= ids)
        self.assertTrue(set(detection._CODEGRAPH_CAPABLE_MULTI_PROVIDER_CLIS) <= ids)
