import argparse
import ast
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest import mock

sys.path.insert(
    0,
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "skills", "ai-kit-spec-review"),
)

from ai_kit_spec import (
    cli,
    config_io,
    config_status,
    detection,
    reviewer_dispatch,
    routing,
    runner_dispatch,
    vendor,
)

_FAKE_LANE = '[[lanes.review]]\nkey = "fr"\nruntime = "fake-runtime"\nmodel = "fake-model-1"\n'


def _project(root, text):
    folder = os.path.join(root, ".aikit")
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, "config.toml")
    with open(path, "w", encoding="utf-8") as stream:
        stream.write(text)
    return path


def _user(root, text):
    folder = os.path.join(root, "xdg", "ai-kit")
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, "config.toml")
    with open(path, "w", encoding="utf-8") as stream:
        stream.write(text)
    return path


def _env(root):
    return {"HOME": root, "XDG_CONFIG_HOME": os.path.join(root, "xdg")}


def _load(root):
    lines = []
    result = config_io.cfg_resolve(root, _env(root), warn_fn=lines.append, migrate=False)
    return result, lines


def _fixture_grok_model():
    path = os.path.join(os.path.dirname(__file__), "fixtures", "cursor_models.txt")
    with open(path, encoding="utf-8") as stream:
        return next(line.split()[0] for line in stream
                    if line.split() and "grok" in line.split()[0])


def _tree(root):
    result = {}
    for folder, _, files in os.walk(root):
        for name in files:
            path = os.path.join(folder, name)
            with open(path, "rb") as stream:
                result[path] = stream.read()
    return result


class _Reached(Exception):
    pass


def _dispatch(entry, spy):
    spec = reviewer_dispatch.ReviewerDispatchSpec(
        reviewer_entry=entry, prompt="", timeout_tiers=[600], tool_availability={}
    )
    return reviewer_dispatch.dispatch_reviewer(
        spec, seams=reviewer_dispatch.ReviewerSeams(runner_tiers_fn=spy, custom_fn=spy)
    )


class TestRuntimeTableWithoutGrok(unittest.TestCase):
    def test_grok_stub_on_path_is_ignored(self):
        with tempfile.TemporaryDirectory() as folder:
            stub = os.path.join(folder, "grok")
            with open(stub, "w", encoding="utf-8") as stream:
                stream.write("#!/bin/sh\nexit 0\n")
            os.chmod(stub, 0o755)
            with mock.patch.dict(os.environ, {"PATH": folder}):
                self.assertNotIn("grok", detection.detect_installed_clis())

    def test_empty_path_maps_every_table_key_to_none(self):
        with tempfile.TemporaryDirectory() as folder, mock.patch.dict(os.environ, {"PATH": folder}):
            result = detection.detect_installed_clis()
        self.assertEqual(result, dict.fromkeys(
            ("pi", "opencode", "cursor", "codex", "claude", "copilot")))

    def test_table_ids_and_order(self):
        expected = ("pi", "opencode", "cursor", "codex", "claude", "copilot")
        self.assertEqual(detection.KNOWN_CLIS, expected)
        self.assertEqual(tuple(detection.RUNTIMES), expected)

    def test_grok_agent_is_an_unknown_signal(self):
        for value in ("1", ""):
            self.assertEqual(detection.detect_current_runtime({"GROK_AGENT": value}), "unknown")
        scrub = detection.HOST_SIGNAL_ENV_VARS
        self.assertNotIn("GROK_AGENT", scrub)
        self.assertNotIn("GROK_AGENTS_HOME", scrub)
        env = {"GROK_AGENT": "1", "GROK_AGENTS_HOME": "x"}
        self.assertEqual({key: value for key, value in env.items() if key not in scrub}, env)

    def test_scrub_lists_agree_without_grok_agent(self):
        root = os.path.join(os.path.dirname(__file__), "..")
        template = os.path.join(root, "skills", "ai-kit-spec-review", "references", "cross-ai.mjs")
        runner = os.path.join(root, "tools", "run_unittest_parallel.py")
        gsd = os.path.join(root, "skills", "ai-kit-spec-review", "ai_kit_spec", "gsd_tools.py")
        with open(template, encoding="utf-8") as stream:
            self.assertNotIn('"GROK_AGENT"', stream.read())
        with open(runner, encoding="utf-8") as stream:
            text = stream.read()
        self.assertNotIn('"GROK_AGENT"', text)
        self.assertIn('"GROK_AGENTS_HOME"', text)
        with open(gsd, encoding="utf-8") as stream:
            tree = ast.parse(stream.read())
        self.assertTrue(any(isinstance(node, ast.Constant) and node.value == "GROK_AGENTS_HOME"
                            for node in ast.walk(tree)))

    def test_stale_snapshot_row_is_ignored(self):
        snapshot = {"clis": {
            "grok": {"installed": True, "models": ["fake-model-1"]},
            "pi": {"installed": True, "models": ["fake-model-2"]},
        }}
        inventory = routing.inventory_from_snapshot(snapshot)
        self.assertEqual(inventory.installed, frozenset({"pi"}))
        self.assertNotIn("grok", inventory.models)
        self.assertEqual(inventory.models["pi"], ("fake-model-2",))

    def test_catalog_fixture_names_no_grok_runtime(self):
        path = os.path.join(os.path.dirname(__file__), "fixtures", "curated_config_v2",
                            "model-catalog.json")
        with open(path, encoding="utf-8") as stream:
            catalog = json.load(stream)
        entries = [entry for key, entry in catalog.items() if key != "_meta" and "grok" in key]
        self.assertTrue(entries)
        for entry in entries:
            self.assertNotIn("grok", entry["runtimes"])

    def test_bare_grok_model_vendor_is_unchanged(self):
        path = os.path.join(os.path.dirname(__file__), "fixtures", "cursor_models.txt")
        with open(path, encoding="utf-8") as stream:
            model = next(line.split()[0] for line in stream if line.startswith("grok-"))
        self.assertIsNone(vendor.infer_vendor_from_model(model))

    def test_catalog_build_without_grok_models_raises_nothing(self):
        discovered = [{"runtime": "opencode", "model_id": f"fake/fake-model-{i}"}
                      for i in (1, 2)]
        result = cli.build_model_catalog(discovered, cli.CatalogSources({}, True, [], True), {})
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 3)


class TestDetectRuntimesRemoved(unittest.TestCase):
    def test_unlisted_excludes_removed(self):
        result = detection.detect_unlisted_runtimes(
            ["grok", "fake-runtime"], which_fn=lambda name, **_k: "/fake/bin/" + name
        )
        self.assertNotIn("grok", result)
        self.assertIn("fake-runtime", result)

    def test_drop_reports_once(self):
        clis = {"grok": {"installed": False}, "pi": {"installed": False}}
        err = io.StringIO()
        with redirect_stderr(err):
            cli._drop_removed_runtimes(["grok", "fake-runtime", "grok"], clis)
        message = detection.removed_runtime_message("grok")
        assert message is not None
        self.assertEqual(err.getvalue(), "detect-runtimes: " + message + "\n")
        self.assertEqual(clis, {"pi": {"installed": False}})

    def test_cli_detect_runtimes_drops_and_reports_grok(self):
        with tempfile.TemporaryDirectory() as root:
            deps = cli.CliDeps(
                which_fn=lambda name, **_k: "/fake/bin/fake-runtime"
                if name == "fake-runtime" else None,
                run_fn=mock.Mock(return_value=subprocess.CompletedProcess(
                    args=[], returncode=1, stdout="", stderr="")),
                env_fn=lambda: {"HOME": root, "XDG_CACHE_HOME": os.path.join(root, "cache"),
                                "XDG_CONFIG_HOME": os.path.join(root, "xdg")},
            )
            out, err = io.StringIO(), io.StringIO()
            with redirect_stdout(out), redirect_stderr(err):
                code = cli.main(["detect-runtimes", "--runtime", "grok", "--runtime",
                                 "fake-runtime", "--runtime", "grok"], deps=deps)
        self.assertEqual(code, 0)
        self.assertNotIn("grok", json.loads(out.getvalue())["clis"])
        self.assertIn("fake-runtime", json.loads(out.getvalue())["clis"])
        message = detection.removed_runtime_message("grok")
        assert message is not None
        self.assertEqual([line for line in err.getvalue().splitlines()
                          if line.startswith("detect-runtimes: ")],
                         ["detect-runtimes: " + message])


class TestBuildCommandRemoved(unittest.TestCase):
    @staticmethod
    def _run(argv):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = cli.main(argv)
        return code, out.getvalue(), err.getvalue()

    def test_removed_runtime_exits_1_with_the_message(self):
        code, out, err = self._run(["build-command", "--runtime", "grok"])
        message = detection.removed_runtime_message("grok")
        assert message is not None
        self.assertEqual((code, out, err), (1, "", "build-command: " + message + "\n"))

    def test_case_variant_gets_the_generic_refusal(self):
        code, out, err = self._run(["build-command", "--runtime", "Grok"])
        self.assertEqual((code, out, err), (
            1, "", "build-command: Grok is not in the runtime table; register it as a "
            "custom entry with a hand-written command\n",
        ))

    def test_empty_id_gets_the_generic_refusal(self):
        code, out, err = self._run(["build-command", "--runtime", ""])
        self.assertEqual(code, 1)
        self.assertEqual(out, "")
        self.assertIn("is not in the runtime table", err)

    def test_commands_module_defines_no_grok_function(self):
        path = os.path.join(os.path.dirname(__file__), "..", "skills", "ai-kit-spec-review",
                            "ai_kit_spec", "commands.py")
        with open(path, encoding="utf-8") as stream:
            tree = ast.parse(stream.read())
        self.assertFalse(any(isinstance(node, ast.FunctionDef) and "grok" in node.name.lower()
                             for node in ast.walk(tree)))


class TestConfigStatusRemovedLane(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = self.temp.name

    def test_removed_only_project_is_empty(self):
        _project(self.root, '[[lanes.review]]\nkey = "gk"\nruntime = "grok"\n')
        state, checked = config_status.config_status(self.root, _env(self.root))
        self.assertEqual(state, "none")
        self.assertEqual(checked[0][2], "empty")

    def test_removed_plus_pi_is_active(self):
        _project(self.root, '[[lanes.review]]\nkey = "gk"\nruntime = "grok"\n'
                 '[[lanes.review]]\nkey = "pl"\nruntime = "pi"\nmodel = "fake-model-2"\n')
        self.assertEqual(config_status.config_status(self.root, _env(self.root))[0], "active")

    def test_status_prints_the_removal_note(self):
        _project(self.root, '[[lanes.review]]\nkey = "gk"\nruntime = "grok"\n')
        out = io.StringIO()
        with redirect_stdout(out):
            code = config_status.cmd_config_status(
                argparse.Namespace(cwd=self.root, role=None),
                mock.Mock(env_fn=lambda: _env(self.root)))
        self.assertEqual(code, 0)
        lines = out.getvalue().splitlines()
        self.assertEqual(lines[0], "none")
        notes = [line for line in lines if "[review gk]" in line]
        self.assertEqual(len(notes), 1)
        message = detection.removed_runtime_message("grok")
        assert message is not None
        self.assertIn(message, notes[0])
        self.assertGreater(lines.index(notes[0]), 2)

    def test_project_removed_lane_over_a_user_lane_is_none(self):
        _user(self.root, '[[lanes.review]]\nkey = "k"\nruntime = "pi"\nmodel = "fake-model-2"\n')
        _project(self.root, '[[lanes.review]]\nkey = "k"\nruntime = "grok"\n'
                 'model = "fake-model-1"\n')
        self.assertEqual(config_status.config_status(self.root, _env(self.root))[0], "none")


class TestSilentPreview(unittest.TestCase):
    def test_quiet_preview_keeps_the_notice(self):
        with tempfile.TemporaryDirectory() as root:
            _project(root, '[[lanes.review]]\nkey = "gk"\nruntime = "grok"\n'
                     'model = "fake-model-1"\n'
                     '[[lanes.review]]\nkey = "pl"\nruntime = "pi"\nmodel = "fake-model-2"\n')
            before = set(config_io._LEGACY_NOTED)
            config_io.cfg_resolve_quiet(root, _env(root))
            self.assertEqual(config_io._LEGACY_NOTED, before)
            _, lines = _load(root)
            self.assertEqual(len(lines), 1)
            self.assertIn("[review gk]", lines[0])

    def test_quiet_preview_keeps_another_loads_dedupe(self):
        with tempfile.TemporaryDirectory() as root:
            a, b = os.path.join(root, "a"), os.path.join(root, "b")
            text = '[[lanes.review]]\nkey = "gk"\nruntime = "grok"\nmodel = "fake-model-1"\n'
            _project(a, text)
            _project(b, text)
            self.assertEqual(len(_load(a)[1]), 1)
            config_io.cfg_resolve_quiet(b, _env(b))
            self.assertEqual(_load(a)[1], [])


class TestRemovedLaneLoad(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR"))
        self.addCleanup(self.temp.cleanup)
        self.root = self.temp.name

    def lane(self, role, key, runtime=None, model="fake-model-1", extra=""):
        pair = f'runtime = "{runtime}"\n' if runtime else ""
        return f'[[lanes.{role}]]\nkey = "{key}"\n{pair}model = "{model}"\n{extra}\n'

    def test_grok_lane_is_skipped_and_the_pi_lane_runs(self):
        path = _project(self.root, self.lane("review", "gk", "grok")
                        + self.lane("review", "pl", "pi", "fake-model-2"))
        with open(path, "rb") as stream:
            before = stream.read()
        result, lines = _load(self.root)
        self.assertEqual(len(lines), 1)
        message = detection.removed_runtime_message("grok")
        assert message is not None
        for text in (message, "opencode, pi, cursor-agent", "render-toml --out <file> --replace",
                     "[review gk]", "this lane is skipped"):
            self.assertIn(text, lines[0])
        self.assertEqual(lines[0].count("re-save"), 1)
        for role in ("review", "reviewers"):
            self.assertEqual([e["key"] for e in result[role]], ["pl"])
        spy = mock.Mock(side_effect=_Reached())
        for entry in result["review"]:
            with self.assertRaises(_Reached):
                _dispatch(entry, spy)
        self.assertEqual(spy.call_count, 1)
        self.assertNotIn("fake-model-1", repr(spy.call_args_list))
        with open(path, "rb") as stream:
            self.assertEqual(stream.read(), before)

    def test_project_removed_lane_never_exposes_the_user_lane(self):
        _user(self.root, self.lane("review", "k", "pi", "fake-model-2"))
        _project(self.root, self.lane("review", "k", "grok"))
        result, lines = _load(self.root)
        self.assertEqual(result["review"], [])
        self.assertEqual(result["reviewers"], [])
        self.assertEqual(len(lines), 1)
        self.assertIn("[review k]", lines[0])

    def test_execute_role_collision_is_dropped_too(self):
        _user(self.root, self.lane("execute", "k", "pi", "fake-model-2"))
        _project(self.root, self.lane("execute", "k", "grok"))
        result, lines = _load(self.root)
        self.assertEqual(result["execute"], [])
        self.assertEqual(len(lines), 1)
        self.assertIn("[execute k]", lines[0])

    def test_user_removed_lane_under_a_project_override_is_dropped(self):
        _user(self.root, self.lane("review", "k", "grok"))
        _project(self.root, self.lane("review", "k", model="fake-model-2"))
        result, lines = _load(self.root)
        self.assertEqual(result["review"], [])
        self.assertEqual(len(lines), 1)
        self.assertIn("[review k]", lines[0])

    def test_project_pair_over_a_user_removed_lane_runs(self):
        _user(self.root, self.lane("review", "k", "grok"))
        _project(self.root, self.lane("review", "k", "pi", "fake-model-2"))
        result, lines = _load(self.root)
        self.assertEqual([(e["key"], e["runtime"]) for e in result["review"]], [("k", "pi")])
        self.assertEqual(lines, [])

    def test_same_key_in_the_other_role_keeps_its_own_lane(self):
        _project(self.root, self.lane("review", "k", "grok")
                 + self.lane("execute", "k", "pi", "fake-model-2"))
        result, lines = _load(self.root)
        self.assertEqual(result["review"], [])
        self.assertEqual([(e["key"], e["runtime"]) for e in result["execute"]], [("k", "pi")])
        self.assertEqual(result["reviewers"], [])
        self.assertEqual(len(lines), 1)
        self.assertIn("[review k]", lines[0])

    def test_ladder_naming_the_dropped_key_has_no_second_note(self):
        _project(self.root, self.lane("review", "gk", "grok")
                 + self.lane("review", "pl", "pi", "fake-model-2")
                 + '[lanes.policy.review]\nladder = ["gk", "pl"]\n')
        result, lines = _load(self.root)
        self.assertEqual(len(lines), 1)
        self.assertEqual(result["orders"]["review"], ["pl"])

    def test_malformed_ladder_entry_beside_a_dropped_key_still_warns(self):
        _project(self.root, self.lane("review", "gk", "grok")
                 + self.lane("review", "pl", "pi", "fake-model-2")
                 + '[lanes.policy.review]\nladder = ["gk", ["nested"], "pl"]\n')
        result, lines = _load(self.root)
        self.assertEqual(len(lines), 2)
        warnings = [line for line in lines if "ladder names no review lane" in line]
        self.assertEqual(len(warnings), 1)
        self.assertIn("nested", warnings[0])
        self.assertNotIn("'gk'", warnings[0])
        self.assertEqual(result["orders"]["review"], ["pl"])

    def test_removed_lane_legacy_fields_add_no_note(self):
        _project(self.root, self.lane("review", "gr", "grok", extra='route = "fake-route-zz93"\n')
                 + self.lane("review", "gn", model="fake-model-3",
                             extra='native_runtime = "grok"\n')
                 + self.lane("review", "pl", "pi", "fake-model-2"))
        result, lines = _load(self.root)
        self.assertEqual(len(lines), 2)
        self.assertTrue(any("[review gr]" in line for line in lines))
        self.assertTrue(any("[review gn]" in line for line in lines))
        for line in lines:
            for text in ("zz93", "fake-model-3", "legacy reviewer fields"):
                self.assertNotIn(text, line)
        for role in ("review", "reviewers"):
            self.assertEqual([e["key"] for e in result[role]], ["pl"])


class TestRemovedLaneEdges(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR"))
        self.addCleanup(self.temp.cleanup)
        self.root = self.temp.name

    def lane(self, role, key, runtime, model="fake-model-1"):
        return f'[[lanes.{role}]]\nkey = "{key}"\nruntime = "{runtime}"\nmodel = "{model}"\n'

    def test_save_refuses_a_removed_runtime(self):
        message = detection.removed_runtime_message("grok")
        assert message is not None
        self.assertEqual(config_io.validate_reviewer_fields(
            {"key": "gk", "runtime": "grok", "model": "fake-model-1"}), "gk: " + message)

    def test_save_keeps_the_generic_refusal(self):
        for runtime in ("Grok", "placeholder-cli-1"):
            with self.subTest(runtime=runtime):
                message = config_io.validate_reviewer_fields(
                    {"key": "gk", "runtime": runtime, "model": "fake-model-1"})
                assert message is not None
                self.assertTrue(message.endswith("is not in the runtime table; store a custom "
                                                 "`command` lane instead (no 'runtime')"))

    def test_legacy_cli_is_dropped_with_or_without_a_command(self):
        _user(self.root, '[[lanes.review]]\nkey = "lc"\ncli = "grok"\nmodel = "fake-model-1"\n'
              '[[lanes.review]]\nkey = "lk"\ncli = "grok"\n'
              'command = "fake-cli -p {prompt} -m {model}"\n' + self.lane("review", "pl", "pi"))
        result, lines = _load(self.root)
        self.assertEqual([e["key"] for e in result["reviewers"]], ["pl"])
        self.assertEqual(len(lines), 2)
        for key in ("lc", "lk"):
            self.assertTrue(any(f"[review {key}]" in line for line in lines))

    def test_custom_command_lane_still_loads(self):
        _user(self.root, '[[lanes.review]]\nkey = "cc"\n'
              'command = "grok -p {prompt} -m {model}"\nmodel = "fake-model-1"\n')
        result, lines = _load(self.root)
        self.assertEqual([e["key"] for e in result["reviewers"]], ["cc"])
        self.assertFalse(any("removed" in line for line in lines))

    def test_cursor_lane_with_a_grok_model_has_no_note(self):
        model = _fixture_grok_model()
        _project(self.root, self.lane("review", "cu", "cursor", model))
        result, lines = _load(self.root)
        self.assertEqual([(e["key"], e["model"]) for e in result["reviewers"]], [("cu", model)])
        self.assertEqual(lines, [])

    def test_only_removed_lane_loads_empty(self):
        _project(self.root, self.lane("review", "gk", "grok"))
        result, lines = _load(self.root)
        self.assertEqual(len(lines), 1)
        for role in ("reviewers", "review", "execute"):
            self.assertEqual(result[role], [])

    def test_second_load_in_the_same_process_is_silent(self):
        _project(self.root, self.lane("review", "gk", "grok"))
        self.assertEqual(len(_load(self.root)[1]), 1)
        self.assertEqual(_load(self.root)[1], [])

    def test_remaining_lanes_keep_their_order(self):
        _project(self.root, ''.join(self.lane("review", key, runtime, f"fake-model-{i}")
                                    for i, (key, runtime) in enumerate(
                                        (("a", "pi"), ("gk", "grok"), ("b", "opencode"),
                                         ("c", "claude")), 1)))
        result, _ = _load(self.root)
        self.assertEqual([e["key"] for e in result["reviewers"]], ["a", "b", "c"])

    def test_execute_role_is_dropped_too(self):
        _project(self.root, self.lane("execute", "gk", "grok") + self.lane("execute", "pl", "pi"))
        result, lines = _load(self.root)
        self.assertEqual([e["key"] for e in result["execute"]], ["pl"])
        self.assertEqual(len(lines), 1)
        self.assertIn("[execute gk]", lines[0])

    def test_case_variant_keeps_generic_handling(self):
        _project(self.root, self.lane("review", "gk", "Grok"))
        result, lines = _load(self.root)
        self.assertEqual([e["key"] for e in result["reviewers"]], ["gk"])
        self.assertEqual(lines, [])

    def test_message_echoes_no_config_value(self):
        _user(self.root, self.lane("review", "pl", "pi")
              + self.lane("review", "gk", "grok", "fake-model-zz91")
              + '[[lanes.review]]\nkey = "lc"\ncli = "grok"\n'
                'command = "fake-cli --secret-zz92 {model}"\n')
        result, lines = _load(self.root)
        self.assertEqual([e["key"] for e in result["reviewers"]], ["pl"])
        self.assertEqual(len(lines), 2)
        for line in lines:
            self.assertNotIn("zz91", line)
            self.assertNotIn("zz92", line)

    def test_duplicate_key_in_one_role_gets_one_note(self):
        _user(self.root, self.lane("review", "gk", "grok")
              + self.lane("review", "gk", "grok", "fake-model-2"))
        result, lines = _load(self.root)
        self.assertEqual(len(lines), 1)
        self.assertEqual(result["reviewers"], [])

    def test_default_load_writes_nothing(self):
        _project(self.root, self.lane("review", "gk", "grok")
                 + self.lane("review", "pl", "pi", "fake-model-2"))
        before = _tree(self.root)
        lines = []
        config_io.cfg_resolve(self.root, _env(self.root), warn_fn=lines.append)
        self.assertEqual(_tree(self.root), before)
        self.assertEqual(len(lines), 1)

    def legacy(self, folder, removed):
        os.makedirs(folder, exist_ok=True)
        text = ('[[reviewers]]\nkey = "gk"\nruntime = "grok"\nmodel = "fake-model-1"\n\n'
                if removed else '')
        text += '[[reviewers]]\nkey = "pl"\nruntime = "pi"\nmodel = "fake-model-2"\n'
        with open(os.path.join(folder, "review-spec.toml"), "w", encoding="utf-8") as stream:
            stream.write(text)

    def check_removed_legacy(self, folder):
        self.legacy(folder, True)
        before = _tree(self.root)
        lines = []
        result = config_io.cfg_resolve(self.root, _env(self.root), warn_fn=lines.append)
        self.assertEqual(_tree(self.root), before)
        self.assertFalse(os.path.exists(os.path.join(folder, "config.toml")))
        self.assertEqual([e["key"] for e in result["reviewers"]], ["pl"])
        self.assertEqual(sum("[review gk]" in line for line in lines), 1)

    def test_user_legacy_file_with_a_removed_lane_is_not_migrated(self):
        self.check_removed_legacy(os.path.join(self.root, "xdg", "ai-kit"))

    def test_project_legacy_file_with_a_removed_lane_is_not_migrated(self):
        self.check_removed_legacy(os.path.join(self.root, ".aikit"))

    def test_clean_legacy_file_still_migrates(self):
        folder = os.path.join(self.root, "xdg", "ai-kit")
        self.legacy(folder, False)
        lines = []
        result = config_io.cfg_resolve(self.root, _env(self.root), warn_fn=lines.append)
        with open(os.path.join(folder, "config.toml"), encoding="utf-8") as stream:
            self.assertIn('key = "pl"', stream.read())
        self.assertEqual([e["key"] for e in result["reviewers"]], ["pl"])
        self.assertFalse(any("was removed from ai-kit" in line for line in lines))


class TestUnknownRuntimeToday(unittest.TestCase):
    def test_unknown_runtime_lane_loads_silently(self):
        with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as root:
            _project(root, _FAKE_LANE)
            result, lines = _load(root)
            self.assertEqual([e["key"] for e in result["review"]], ["fr"])
            self.assertEqual(lines, [])

    def test_unknown_runtime_routes_unverified(self):
        with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as root:
            _project(root, _FAKE_LANE)
            entry = {"key": "fr", "runtime": "fake-runtime", "model": "fake-model-1"}
            self.assertEqual(
                routing.route(
                    routing.RouteInput.of(entry),
                    "unknown",
                    "review",
                    routing.Inventory(frozenset(), {}),
                ),
                "unverified",
            )

    def test_unknown_runtime_reaches_the_runner(self):
        with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as root:
            _project(root, _FAKE_LANE)
            self.assertIs(
                reviewer_dispatch.ReviewerSeams._field_defaults["runner_tiers_fn"],
                runner_dispatch.run_runner_tiers,
            )
            spy = mock.Mock(side_effect=_Reached())
            with self.assertRaises(_Reached):
                _dispatch(
                    {
                        "key": "fr",
                        "runtime": "fake-runtime",
                        "model": "fake-model-1",
                        "route": "unverified",
                    },
                    spy,
                )
            self.assertEqual(spy.call_count, 1)
