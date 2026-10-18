"""One runtime-id table: snapshot keys, legacy names, and host precedence (18.1 R1)."""

import ast
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills", "ai-kit-spec-review"))

from ai_kit_spec import commands, detection, execute_dispatch
from ai_kit_spec.cli import main
from ai_kit_spec.detection import normalize_runtime_keys, runtime_id
from ai_kit_spec.error_classifier import REASONS, STATUS_TO_REASON, reason_for_status
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

    def test_codex_labels_are_live_verified(self):
        labels = dict(detection.RUNTIMES["codex"].host_signals)
        self.assertEqual(set(labels), {"CODEX_THREAD_ID", "CODEX_VERSION"})
        prefix = "live-verified (Phase 20)"
        self.assertTrue(all(label.startswith(prefix) for label in labels.values()))
        doc = " ".join((detection.detect_current_runtime.__doc__ or "").split())
        for label in labels.values():
            self.assertIn(" ".join(label.split()), doc)

    def test_non_claude_hosts_have_no_native_selectors(self):
        from ai_kit_spec.routing import host_can_select

        self.assertEqual(detection.RUNTIMES["codex"].native_selectors, ())
        self.assertEqual(detection.RUNTIMES["opencode"].native_selectors, ())
        # ROADMAP Phase 20 SC3's session-default-only OR branch satisfies the criterion;
        # native selection remains an optional live probe (18.1-VERIFICATION deferred item 1).
        self.assertFalse(host_can_select("codex", "gpt-5.6-sol", "codex"))

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

    def test_legacy_name_matches_the_runtime_id(self):
        self.assertIsNone(commands.execute_cli_error("cursor"))
        self.assertIsNone(commands.execute_cli_error("cursor-agent"))
        rejection = commands.execute_cli_error("claude")
        self.assertIsNotNone(rejection)
        assert rejection is not None
        self.assertIn("cannot be an execution CLI", rejection)
        self.assertEqual(
            commands.build_reviewer_model_id("cursor", "m", effort="high"),
            commands.build_reviewer_model_id("cursor-agent", "m", effort="high"),
        )
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

    def test_build_command_cursor_default_previews_the_runner_default(self):
        # SJ: with no --mode, the preview omits --cursor-mode, as dispatch does for an entry
        # with no cursor_mode, so the runner's own `ask` default applies.
        out = io.StringIO()
        with redirect_stdout(out), redirect_stderr(io.StringIO()):
            code = main(["build-command", "--runtime", "cursor"])
        self.assertEqual(code, 0)
        self.assertNotIn("--cursor-mode", json.loads(out.getvalue())["argv"])

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
        self.assertTrue(set(commands.SUPPORTED_EXECUTE_CLIS) <= ids)
        self.assertTrue(set(execute_dispatch.OS_SANDBOXED_EXEC) <= ids)
        self.assertTrue(set(detection._SUPPORTED_CODEGRAPH_CLIENTS) <= ids)
        self.assertTrue(set(detection._MCP_LIST_COMMANDS) <= ids)
        self.assertTrue(set(detection._CODEGRAPH_CAPABLE_MULTI_PROVIDER_CLIS) <= ids)

    def test_curated_config_registries_use_table_ids(self):
        curated_path = os.path.join(
            os.path.dirname(__file__), "..", "skills", "ai-kit-gsd-curated-config"
        )
        sys.path.insert(0, curated_path)
        try:
            from ai_kit_gsd_curated_config import cross_ai, cross_ai_build, preference_match
        finally:
            sys.path.remove(curated_path)
        ids = set(detection.RUNTIMES)
        self.assertLessEqual(set(cross_ai.RUNNER_IDS), ids)
        self.assertLessEqual(set(cross_ai_build.REVIEWER_SLUGS), ids)
        self.assertLessEqual(set(preference_match._RUNTIME_ORDER), ids)

    def test_runner_template_keys_use_table_ids(self):
        path = os.path.join(
            os.path.dirname(__file__), "..", "skills", "ai-kit-spec-review",
            "references", "cross-ai.mjs",
        )
        with open(path, encoding="utf-8") as handle:
            source = handle.read()
        block = source.split("const RUNTIMES = {", 1)[1].split("};", 1)[0]
        runtime_ids = set(re.findall(r"^  ([\w-]+): \{", block, re.MULTILINE))
        self.assertTrue(runtime_ids)
        self.assertLessEqual(runtime_ids, set(detection.RUNTIMES))

    def test_gsd_lane_runtimes_map_to_table_ids(self):
        from ai_kit_gsd_curated_config.gsd_catalog import _parse_review_lanes

        fixture = os.path.join(
            os.path.dirname(__file__), "fixtures", "curated_config_v2", "gsd_tables_1_16.json"
        )
        with open(fixture, encoding="utf-8") as handle:
            raw = json.load(handle)
        lanes = _parse_review_lanes(raw.get("review_lanes")) or []
        expected_non_table = {"agy", "coderabbit", "kimi", "qwen"}
        table_ids = set(detection.RUNTIMES)
        lane_ids = {lane.get("runtime") for lane in lanes if lane.get("runtime")}
        self.assertEqual(lane_ids - table_ids, expected_non_table)
        self.assertIn("cursor", lane_ids)
        self.assertNotIn("cursor-agent", lane_ids)

    def test_runtime_subset_helper_non_vacuity(self):
        values = ["codex", "cursor-agent"]
        unknown = [value for value in values if value not in detection.RUNTIMES]
        self.assertEqual(unknown, ["cursor-agent"])


_ID_SHAPED = (
    r"cursor-agent\.md",
    r"--(?:cli|runtime)[ =]cursor-agent\b",
    r"[\"']cursor-agent[\"']\s*:",
    r"\b(?:clis|runtimes)\.cursor-agent\b",
    r"\b(?:cli|runtime)\s*=\s*[\"']cursor-agent[\"']",
)


def id_shaped_hits(relpath, text):
    patterns = [re.compile(pattern, re.IGNORECASE) for pattern in _ID_SHAPED]
    return [
        f"{relpath}:{line_number}"
        for line_number, line in enumerate(text.splitlines(), 1)
        if "legacy" not in line.lower() and any(pattern.search(line) for pattern in patterns)
    ]


class TestRetiredIdUsage(unittest.TestCase):
    def test_tree_clean(self):
        try:
            paths = subprocess.run(
                ["git", "ls-files", "skills", "tools", "README.md", "AGENTS.md"],
                check=True, capture_output=True, text=True,
            ).stdout.splitlines()
        except (FileNotFoundError, subprocess.CalledProcessError):
            self.skipTest("git is unavailable; tracked-text scan cannot run")
        hits = []
        for path in paths:
            if path == "skills/ai-kit-spec-review/ai_kit_spec/detection.py":
                continue
            try:
                with open(path, encoding="utf-8") as handle:
                    hits.extend(id_shaped_hits(path, handle.read()))
            except (UnicodeDecodeError, OSError):
                continue
        self.assertEqual([], hits)

    def test_flags_each_pattern(self):
        examples = (
            "cursor-agent.md",
            "--cli cursor-agent",
            '"cursor-agent": {}',
            "clis.cursor-agent",
            'runtime = "cursor-agent"',
        )
        for example in examples:
            self.assertEqual(1, len(id_shaped_hits("sample.txt", example)), example)
        self.assertEqual([], id_shaped_hits("sample.txt", "legacy cursor-agent"))
        self.assertEqual([], id_shaped_hits("sample.txt", "cursor-agent -p prompt"))


class TestConfigDoctorRuntimeLiterals(unittest.TestCase):
    CONFIG_DOCTOR_SENTINELS = frozenset({"cross"})

    @staticmethod
    def runtime_keyword_literals(tree):
        values = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                for keyword in node.keywords:
                    if keyword.arg == "runtime" and isinstance(keyword.value, ast.Constant) \
                            and isinstance(keyword.value.value, str):
                        values.append(keyword.value.value)
        return values

    @classmethod
    def unknown_runtime_literals(cls, values):
        return [
            value for value in values
            if value not in detection.RUNTIMES and value not in cls.CONFIG_DOCTOR_SENTINELS
        ]

    def test_live_file(self):
        path = os.path.join(os.path.dirname(__file__), "..", "tools", "config_doctor_checks.py")
        with open(path, encoding="utf-8") as handle:
            tree = ast.parse(handle.read())
        values = self.runtime_keyword_literals(tree)
        self.assertTrue(values)
        self.assertIn("cross", values)
        self.assertEqual([], self.unknown_runtime_literals(values))

    def test_flags_retired_id(self):
        source = 'f(runtime="cursor-agent")'
        values = self.runtime_keyword_literals(ast.parse(source))
        self.assertEqual(["cursor-agent"], self.unknown_runtime_literals(values))
        for source in ('f(runtime="cross")', 'f(runtime="codex")'):
            self.assertEqual([], self.unknown_runtime_literals(
                self.runtime_keyword_literals(ast.parse(source))
            ))


def _runner_template_text():
    path = os.path.join(
        os.path.dirname(__file__), "..", "skills", "ai-kit-spec-review",
        "references", "cross-ai.mjs",
    )
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def template_model_suffixes(text):
    """Map each template runtime id to its modelSuffix source, or None."""
    block = text.split("const RUNTIMES = {", 1)[1]
    end = re.search(r"^};", block, re.M)
    block = block[: end.start() if end else 0]
    parts = re.split(r"^  (\w+): \{", block, flags=re.M)
    suffixes = {}
    rows = iter(parts[1:])
    for name, body in zip(rows, rows, strict=True):
        match = re.search(r"modelSuffix: /(.+)/,", body)
        suffixes[name] = match.group(1) if match else None
    return suffixes


def model_suffix_mismatches(text):
    """Runtimes whose template modelSuffix source differs from the Python table."""
    suffixes = template_model_suffixes(text)
    names = set(suffixes) | {
        name for name, spec in detection.RUNTIMES.items() if spec.runner
    }
    bad = []
    for name in sorted(names):
        spec = detection.RUNTIMES.get(name)
        expected = spec.model_suffix if spec is not None else None
        if suffixes.get(name) != expected:
            bad.append(name)
    return bad


class TestModelSuffixParity(unittest.TestCase):
    def test_template_suffixes_match_the_runtime_table(self):
        self.assertEqual(model_suffix_mismatches(_runner_template_text()), [])

    def test_doctored_cursor_suffix_is_a_mismatch(self):
        text = _runner_template_text()
        doctored = text.replace(
            "modelSuffix: /\\[[^\\]]*\\]$/,",
            "modelSuffix: /WRONG$/,",
            1,
        )
        self.assertNotEqual(doctored, text)
        self.assertIn("cursor", model_suffix_mismatches(doctored))


def _js_strings(array_source):
    return tuple(re.findall(r"'([^']*)'", array_source))


def template_bins_and_list_argv(text):
    """Each template row's `bins` and its listing argv (`PI_RPC_ARGS` resolved; None for
    `list: null`)."""
    pi_rpc = _js_strings(text.split("const PI_RPC_ARGS = [", 1)[1].split("];", 1)[0])
    block = text.split("const RUNTIMES = {", 1)[1]
    end = re.search(r"^};", block, re.M)
    parts = re.split(r"^  (\w+): \{", block[: end.start() if end else 0], flags=re.M)
    rows = iter(parts[1:])
    found = {}
    for name, body in zip(rows, rows, strict=True):
        bins = re.search(r"bins: \[([^\]]*)\]", body)
        listing = re.search(r"list: (null|\{ argv: (PI_RPC_ARGS|\[[^\]]*\]))", body)
        argv = None
        if listing and listing.group(1) != "null":
            argv = pi_rpc if listing.group(2) == "PI_RPC_ARGS" else _js_strings(listing.group(2))
        found[name] = (_js_strings(bins.group(1)) if bins else None, argv)
    return found


def binary_and_listing_mismatches(text):
    """Runner runtimes whose template bins or listing argv differ from the Python table."""
    found = template_bins_and_list_argv(text)
    names = set(found) | {name for name, spec in detection.RUNTIMES.items() if spec.runner}
    bad = []
    for name in sorted(names):
        spec = detection.RUNTIMES.get(name)
        expected = (spec.binaries, spec.list_argv) if spec is not None else None
        if found.get(name) != expected:
            bad.append(name)
    return bad


class TestBinaryAndListingParity(unittest.TestCase):
    """PT-07: routing calls a model `subprocess` from a listing the runner must reproduce."""

    def test_template_bins_and_listing_argv_match_the_runtime_table(self):
        self.assertEqual(binary_and_listing_mismatches(_runner_template_text()), [])

    def test_doctored_bins_and_listing_are_mismatches(self):
        text = _runner_template_text()
        for old, new, name in (
            ("bins: ['cursor-agent', 'agent'],", "bins: ['cursor-agent'],", "cursor"),
            ("list: { argv: ['debug', 'models'],", "list: { argv: ['models'],", "codex"),
            ("  '--no-skills', '--no-context-files', '--no-mcp',\n];",
             "  '--no-skills', '--no-context-files',\n];", "pi"),
        ):
            with self.subTest(name=name):
                doctored = text.replace(old, new, 1)
                self.assertNotEqual(doctored, text)
                self.assertIn(name, binary_and_listing_mismatches(doctored))


def template_status_keys(text):
    """STATUS_TABLE keys between `const STATUS_TABLE = {` and the closing `};`."""
    start = text.index("const STATUS_TABLE = {")
    end = text.index("};", start)
    block = text[start:end]
    return re.findall(r"^  (\w+):", block, re.M)


def status_map_drift(text):
    """Template STATUS_TABLE keys missing from STATUS_TO_REASON."""
    return [key for key in template_status_keys(text) if key not in STATUS_TO_REASON]


class TestStatusMapDrift(unittest.TestCase):
    def test_every_template_status_is_mapped(self):
        self.assertEqual(status_map_drift(_runner_template_text()), [])

    def test_map_values_are_none_or_known_reasons(self):
        known = set(REASONS)
        bad = [
            (status, reason) for status, reason in STATUS_TO_REASON.items()
            if reason is not None and reason not in known
        ]
        self.assertEqual(bad, [])

    def test_unverified_is_neither_a_map_key_nor_a_template_status(self):
        self.assertNotIn("unverified", STATUS_TO_REASON)
        self.assertNotIn("unverified", template_status_keys(_runner_template_text()))

    def test_doctored_status_is_a_drift(self):
        text = _runner_template_text()
        needle = "const STATUS_TABLE = {"
        doctored = text.replace(needle, needle + "\n  zzz_new: { exit: 1, action: 'stop' },", 1)
        self.assertNotEqual(doctored, text)
        self.assertIn("zzz_new", status_map_drift(doctored))

    def test_reason_for_status_maps_named_statuses(self):
        cases = (
            ("quota", None, "quota"),
            ("quota_wait", None, "quota"),
            ("billing", None, "billing_or_access"),
            ("capacity", None, "capacity"),
            ("git_timeout", None, "git_timeout"),
            ("git_error", None, "real_error"),
            ("empty_answer", None, "real_error"),
            (None, 0, None),
            (None, 127, "dispatch_unavailable"),
            (None, 2, "configuration"),
            (None, 124, "timeout"),
            (None, 3, "real_error"),
        )
        for status, code, want in cases:
            self.assertEqual(reason_for_status(status, code), want, status)


# Built by concatenation so neither retired name is a literal in this file.
_RETIRED_FIELD = "native" + "_runtime"
_RETIRED_MODE = "native" + "_claude"

PAIR_RULE_PARAGRAPH = (
    "A reviewer or executor is a (runtime, model) pair. Each call runs it natively when its "
    "runtime is the current host and the host can select that model; otherwise it runs as a "
    "subprocess through the supervised runner. An entry with neither a runtime nor a model is "
    "the session default, which the host always runs natively. Today only Claude Code selects "
    "a model per call (its sonnet, opus, haiku and fable aliases); every other host runs only "
    "its session default natively."
)

_REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")

REWRITTEN = [
    "skills/ai-kit-spec-review/SKILL.md",
    "skills/ai-kit-spec-config/SKILL.md",
    "skills/ai-kit-spec-execute-superpowers/SKILL.md",
    "skills/ai-kit-spec-execute-gsd/SKILL.md",
    "skills/ai-kit-gsd-curated-config/SKILL.md",
    "skills/ai-kit-opencode-providers/SKILL.md",
]
# The canonical paragraph describes dispatch, so only the skills that do dispatch carry it.
# curated-config and opencode-providers are checked for forbidden tokens only.
PAIR_RULE_SKILLS = REWRITTEN[:4]
REFERENCES = [
    "skills/ai-kit-spec-review/references/cross-ai-dispatch.md",
    "skills/ai-kit-spec-review/references/reviewer-prompts.md",
    "skills/ai-kit-spec-review/references/apply-findings.md",
    "skills/ai-kit-spec-review/references/cli-profiles/claude.md",
    "skills/ai-kit-spec-review/references/cli-profiles/codex.md",
    "skills/ai-kit-spec-review/references/cli-profiles/cursor.md",
    "skills/ai-kit-spec-review/references/cli-profiles/opencode.md",
    "skills/ai-kit-spec-review/references/cli-profiles/grok.md",
    "skills/ai-kit-spec-config/references/cli-model-selection.md",
    "skills/ai-kit-spec-execute-superpowers/references/escalation.md",
    "skills/ai-kit-spec-execute-superpowers/references/design-notes.md",
    "skills/ai-kit-spec-execute-gsd/references/dispatch-notes.md",
    "skills/ai-kit-gsd-curated-config/references/runner.md",
    "skills/ai-kit-gsd-curated-config/references/v1-path.md",
]
_EXEC_SKILLS = (
    "skills/ai-kit-spec-execute-superpowers/SKILL.md",
    "skills/ai-kit-spec-execute-gsd/SKILL.md",
)
_CONFINEMENT_TOKENS = (
    "--codex-sandbox",
    "/tmp",
    "$TMPDIR",
    "full permissions",
    "self-test",
    "Phase 22",
)

_FORBIDDEN = (
    _RETIRED_FIELD,
    _RETIRED_MODE,
    "cursor-agent.md",
    "`cli` is `null`",
    "`cli`-omitted",
    "cli=None",
)


def _read_repo(relpath):
    with open(os.path.join(_REPO_ROOT, relpath), encoding="utf-8") as handle:
        return handle.read()


def _agents_architecture():
    """AGENTS.md text from `## Architecture` up to, but not including, the next heading."""
    text = _read_repo("AGENTS.md")
    start = text.index("## Architecture")
    rest = text[start + len("## Architecture"):]
    end = rest.find("\n## ")
    return text[start:] if end < 0 else text[start:start + len("## Architecture") + end]


class TestWordingGrep(unittest.TestCase):
    def test_forbidden_tokens(self):
        scopes = [(path, _read_repo(path)) for path in (*REWRITTEN, *REFERENCES)]
        scopes.append(("AGENTS.md##Architecture", _agents_architecture()))
        hits = [
            f"{path}: {token}"
            for path, text in scopes
            for token in _FORBIDDEN
            if token in text
        ]
        self.assertEqual(hits, [])

    def test_pair_rule_paragraph(self):
        missing = [path for path in PAIR_RULE_SKILLS if PAIR_RULE_PARAGRAPH not in _read_repo(path)]
        self.assertEqual(missing, [])

    def test_exec_confinement_statement(self):
        missing = [
            f"{path}: {token}"
            for path in _EXEC_SKILLS
            for token in _CONFINEMENT_TOKENS
            if token not in _read_repo(path)
        ]
        self.assertEqual(missing, [])

    def test_review_only_label(self):
        paths = (
            "skills/ai-kit-spec-review/SKILL.md",
            "skills/ai-kit-spec-review/references/cli-profiles/claude.md",
        )
        missing = [path for path in paths if "review-only" not in _read_repo(path)]
        self.assertEqual(missing, [])

    def test_node_floor(self):
        text = _read_repo("skills/ai-kit-spec-review/SKILL.md")
        self.assertIn("Node 24 (GSD's declared floor); older versions untested", text)

    def test_codex_confinement_statement(self):
        text = _read_repo("skills/ai-kit-spec-review/references/cli-profiles/codex.md")
        for token in (
            "--codex-sandbox workspace-write",
            "--dangerously-bypass-approvals-and-sandbox",
            "/tmp",
            "$TMPDIR",
            "unverified",
        ):
            self.assertIn(token, text, token)
