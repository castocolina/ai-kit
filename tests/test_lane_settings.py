"""Lane settings and their config_io hooks."""

import copy
import io
import os
import sys
import tempfile
import tomllib
import unittest
from contextlib import redirect_stderr
from pathlib import Path

_REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(_REPO_ROOT, "skills", "ai-kit-spec-review"))

from ai_kit_spec import config_io, lane_data_use, lane_effort, lane_settings

FULL_DATA_USE = {"data_use": "may_be_kept_or_trained",
                 "data_use_line": "The provider's page says prompts may be kept.",
                 "data_use_source": "https://example.com/data-use", "data_use_read": "2000-01-02",
                 "data_use_label": "reported", "data_use_confirmed": True}
UNKNOWN_DATA_USE = {"data_use": "unknown", "data_use_line": "not read", "data_use_source": "none",
                    "data_use_read": "2000-01-02", "data_use_confirmed": True}


def _render(config, existing=""):
    stderr = io.StringIO()
    with redirect_stderr(stderr):
        text = config_io.cfg_render_lanes(config, existing)
    return text, stderr.getvalue()


def _lane(key="k1"):
    return {"key": key, "runtime": "codex", "model": "placeholder-model-1"}


class TestLaneSettingsValidate(unittest.TestCase):
    def test_flags_accept_booleans(self):
        self.assertIsNone(lane_settings.validate_lane_settings(
            {"escalate_runtime": True, "escalate_model": False, "usage_limited": True}, "k1"))

    def test_non_boolean_flag_names_key_and_setting(self):
        for name in lane_settings.LANE_FLAG_KEYS:
            with self.subTest(name=name):
                self.assertEqual(lane_settings.validate_lane_settings({name: 1}, "k1"),
                                 f"k1: '{name}' must be a boolean")

    def test_effort_is_left_to_lane_effort(self):
        self.assertIsNone(lane_settings.validate_lane_settings({"effort": ""}, "k1"))

    def test_validator_chains_effort_problem(self):
        entry = {**_lane(), "effort": ""}
        self.assertIsNotNone(lane_effort.effort_problem(entry))
        self.assertEqual(config_io.validate_reviewer_fields(entry),
                         lane_effort.effort_problem(entry))

    def test_note_needs_the_flag_and_a_string(self):
        for flag in ({}, {"usage_limited": False}):
            self.assertEqual(lane_settings.validate_lane_settings(
                {**flag, "usage_limit_note": "x"}, "k1"),
                             "k1: 'usage_limit_note' needs 'usage_limited = true'")
        self.assertEqual(lane_settings.validate_lane_settings(
            {"usage_limited": True, "usage_limit_note": 5}, "k1"),
            "k1: 'usage_limit_note' must be a string")
        self.assertIsNone(lane_settings.validate_lane_settings(
            {"usage_limited": True, "usage_limit_note": "a daily cap"}, "k1"))

    def test_pool_shape(self):
        self.assertIsNone(lane_settings.validate_lane_settings({"pool": "fake:free"}, "k1"))
        for value in ("fake/free", "fake:", ":free", "fake:FREE", "a" * 65 + ":free", 5):
            with self.subTest(value=value):
                self.assertEqual(lane_settings.validate_lane_settings({"pool": value}, "k1"),
                                 "k1: 'pool' must look like '<provider>:free'")

    def test_data_use_goes_through_validate_note(self):
        self.assertIsNone(lane_data_use.validate_note(FULL_DATA_USE))
        self.assertIsNone(lane_settings.validate_lane_settings(FULL_DATA_USE, "k1"))
        entry = {"key": "k1", "data_use": "unknown"}
        problem = lane_data_use.validate_note(entry)
        self.assertIsNotNone(problem)
        assert problem is not None
        self.assertEqual(lane_settings.validate_lane_settings(entry, "k1"), "k1: " + problem)


class TestLaneSettingsNormalise(unittest.TestCase):
    def test_clean_note(self):
        self.assertEqual(lane_settings.clean_note("a\nb\tc\x1bd"), "abcd")
        self.assertEqual(lane_settings.clean_note("  about 100 requests a day  "),
                         "about 100 requests a day")
        self.assertEqual(lane_settings.clean_note("x" * 250), "x" * 200)

    def test_normalise_cleans_only_the_display_lines(self):
        entry = {"usage_limited": True, "usage_limit_note": "\n\t", "data_use_line": "line\x07one"}
        original = entry.copy()
        result = lane_settings.normalise_lane_settings(entry)
        self.assertNotIn("usage_limit_note", result)
        self.assertEqual(result["data_use_line"], lane_data_use.clean_line(entry["data_use_line"]))
        self.assertEqual(entry, original)
        self.assertEqual(lane_settings.normalise_lane_settings(
            {"usage_limit_note": 5})["usage_limit_note"], 5)


class TestLaneSettingsWriter(unittest.TestCase):
    def test_flag_refused_or_written_through_the_writer(self):
        text, err = _render({"lanes": [{**_lane(), "usage_limited": "yes"},
                                       {**_lane("k2"), "usage_limited": True}]})
        self.assertEqual([x["key"] for x in tomllib.loads(text)["lanes"]["review"]], ["k2"])
        self.assertIn("WARNING: 1 issue(s) found and NOT written", err)
        self.assertIn("k1: 'usage_limited' must be a boolean", err)

    def test_effort_source_refused_through_the_writer(self):
        text, err = _render({"lanes": [{**_lane("k3"),
                                        "effort_source": "accepted by a call on 2000-01-02"}]})
        self.assertNotIn("[[lanes.review]]", text)
        self.assertIn("k3: 'effort_source' needs 'effort'", err)

    def test_nested_data_use_record_refused(self):
        text, err = _render({"lanes": [{**_lane(), "data_use": {"value": "unknown"}}]})
        self.assertNotIn("[[lanes.review]]", text)
        self.assertIn("'data_use' has a nested-object value", err)

    def test_false_flags_are_never_written(self):
        entry = {**_lane("k4"), **dict.fromkeys(lane_settings.LANE_FLAG_KEYS, False)}
        text, _ = _render({"lanes": [entry]})
        self.assertIn("[[lanes.review]]", text)
        for name in lane_settings.LANE_FLAG_KEYS:
            self.assertNotIn(name, text)

    def test_every_new_key_round_trips_byte_equal(self):
        entry = {"key": "k1", "purpose": "execute", "runtime": "opencode",
                 "model": "fake/placeholder-model-3", "effort": "high",
                 "effort_source": "accepted by a call on 2000-01-02", "escalate_runtime": True,
                 "escalate_model": True, "usage_limited": True, "usage_limit_note": "a daily\ncap",
                 "pool": "fake:free", **FULL_DATA_USE}
        config = {"lanes": [entry, {**_lane("k2"), "purpose": "execute"}]}
        existing = "# keep\n[runner.retry]\nbase_s = 1\n"
        text, err = _render(config, existing)
        self.assertEqual(err, "")
        self.assertTrue(text.startswith(existing))
        self.assertEqual(tomllib.loads(text)["lanes"]["execute"][0],
                         {**entry, "usage_limit_note": "a dailycap"})
        self.assertEqual(_render(config, text), (text, ""))


class TestFreeLaneWriteCheck(unittest.TestCase):
    def test_pool_without_a_confirmed_record_is_not_written(self):
        base = {"key": "z1", "runtime": "opencode", "model": "fake/placeholder-model-3",
                "pool": "fake:free"}
        for record in ({}, {k: v for k, v in FULL_DATA_USE.items() if k != "data_use_confirmed"}):
            text, err = _render({"lanes": [{**base, **record}, _lane("k2")]})
            self.assertEqual([x["key"] for x in tomllib.loads(text)["lanes"]["review"]], ["k2"])
            self.assertIn("WARNING: 1 issue(s) found and NOT written", err)
            self.assertIn("z1:", err)
            if not record:
                self.assertIn(lane_settings.FREE_LANE_REFUSAL.format(key="z1"), err)

    def test_pool_with_a_full_or_unknown_record_is_written(self):
        for record in (FULL_DATA_USE, UNKNOWN_DATA_USE):
            entry = {**_lane("z1"), "pool": "fake:free", **record}
            self.assertIsNone(lane_settings.write_problem(entry))
            text, err = _render({"lanes": [entry]})
            self.assertEqual(err, "")
            self.assertEqual(tomllib.loads(text)["lanes"]["review"][0], entry)
        self.assertIsNone(lane_settings.write_problem(_lane()))

    def test_hand_written_pool_lane_still_loads(self):
        entry = {"key": "z1", "runtime": "opencode", "model": "fake/placeholder-model-3",
                 "pool": "fake:free"}
        self.assertIsNone(config_io.validate_reviewer_fields(entry))
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "project"
            project.mkdir()
            config = root / "xdg" / "ai-kit" / "config.toml"
            config.parent.mkdir(parents=True)
            config.write_text('[[lanes.execute]]\nkey = "z1"\nruntime = "opencode"\n'
                              'model = "fake/placeholder-model-3"\npool = "fake:free"\n')
            warnings = []
            resolved = config_io.cfg_resolve(str(project), {"HOME": str(root / "home"),
                                             "XDG_CONFIG_HOME": str(root / "xdg")},
                                             warn_fn=warnings.append)
            self.assertEqual(resolved["execute"], [entry])


class TestModelBoundMerge(unittest.TestCase):
    def global_lane(self):
        return {**_lane(), "strength": "s", "effort": "high", "usage_limited": True,
                "pool": "fake:free", "escalate_model": True, **FULL_DATA_USE}

    def test_model_bound_names(self):
        expected = {"effort", "effort_source", "usage_limited", "usage_limit_note", "pool",
                    "escalate_runtime", "escalate_model", *lane_data_use.DATA_USE_KEYS}
        self.assertEqual(set(lane_settings.MODEL_BOUND), expected)

    def test_model_change_drops_model_bound(self):
        result = config_io.cfg_merge_reviewers(
            [self.global_lane()], [{"key": "k1", "model": "placeholder-model-2"}])[0]
        self.assertEqual(result, {**_lane(), "model": "placeholder-model-2", "strength": "s"})

    def test_runtime_or_command_restated_drops_model_bound(self):
        for update in ({"runtime": "codex"}, {"command": "placeholder-cli-1 {model}"}):
            result = config_io.cfg_merge_reviewers(
                [self.global_lane()], [{"key": "k1", **update}])[0]
            self.assertFalse(set(result) & set(lane_settings.MODEL_BOUND))
            if "command" in update:
                self.assertNotIn("runtime", result)

    def test_same_model_keeps_and_restated_value_wins(self):
        base = self.global_lane()
        result = config_io.cfg_merge_reviewers(
            [base], [{"key": "k1", "model": "placeholder-model-1", "usage_limited": False}])[0]
        self.assertEqual(result, {**base, "usage_limited": False})
        result = config_io.cfg_merge_reviewers([base], [{"key": "k1", "effort": "low"}])[0]
        self.assertEqual(result, {**base, "effort": "low"})

    def test_inputs_are_not_mutated(self):
        global_list = [self.global_lane()]
        local_list = [{"key": "k1", "model": "placeholder-model-2"}]
        originals = copy.deepcopy((global_list, local_list))
        config_io.cfg_merge_reviewers(global_list, local_list)
        self.assertEqual((global_list, local_list), originals)


if __name__ == "__main__":
    unittest.main()
