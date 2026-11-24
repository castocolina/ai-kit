import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(
    0,
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "skills", "ai-kit-spec-review"),
)

from ai_kit_spec import config_io, detection, reviewer_dispatch, routing, runner_dispatch

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
