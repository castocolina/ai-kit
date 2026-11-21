"""Lane settings and their config_io hooks."""

import ast
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


def _lane(key="k1", *, flagged=False, pool=None, runtime="codex", model="placeholder-model-1"):
    lane: dict = {"key": key, "runtime": runtime, "model": model}
    if flagged:
        lane["usage_limited"] = True
    if pool:
        lane["pool"] = pool
    return lane


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
        self.assertEqual(lane_settings.clean_note("a\nb\tc\x1bd"), "a b c d")
        self.assertEqual(lane_settings.clean_note("daily cap\n100 requests"),
                         "daily cap 100 requests")
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
                         {**entry, "usage_limit_note": "a daily cap"})
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


REPO = Path(__file__).resolve().parents[1]
SCANNED = (REPO / "skills" / "ai-kit-spec-review" / "ai_kit_spec",
           REPO / "skills" / "ai-kit-spec-execute-superpowers" / "ai_kit_spec_superpowers")
FLAGS = frozenset(lane_settings.LANE_FLAG_KEYS)
READERS = frozenset({"lane_escalation", "escalation_target", "lane_usage_limit", "lane_fallback"})


def _flag_literal_lines(text: str) -> list[int]:
    return sorted(n.lineno for n in ast.walk(ast.parse(text))
                  if isinstance(n, ast.Constant) and isinstance(n.value, str) and n.value in FLAGS)


def _reader_lines(text: str) -> list[int]:
    return sorted(n.lineno for n in ast.walk(ast.parse(text))
                  if (isinstance(n, ast.Name) and n.id in READERS)
                  or (isinstance(n, ast.Attribute) and n.attr in READERS)
                  or (isinstance(n, ast.alias) and n.name in READERS))


def _scanned_files():
    return sorted(p for folder in SCANNED for p in folder.glob("*.py")
                  if p.name != "lane_settings.py")


class _ScratchLayers(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.cwd = str(self.root / "project")
        Path(self.cwd).mkdir()
        self.env = {"HOME": str(self.root / "home"), "XDG_CONFIG_HOME": str(self.root / "xdg")}
        self.warnings = []

    def write_user(self, text):
        path = self.root / "xdg" / "ai-kit" / "config.toml"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def write_project(self, text):
        path = Path(self.cwd) / ".aikit" / "config.toml"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def resolve(self):
        return config_io.cfg_resolve(self.cwd, self.env, warn_fn=self.warnings.append)


def _toml_lane(role, key, extra="", model="placeholder-model-1", runtime="codex"):
    return (f'[[lanes.{role}]]\nkey = "{key}"\nruntime = "{runtime}"\n'
            f'model = "{model}"\n{extra}\n')


class TestLaneUsageLimit(_ScratchLayers):
    def test_absent_is_not_limited(self):
        self.assertEqual(lane_settings.lane_usage_limit(_lane()), (False, ""))

    def test_flag_and_note(self):
        self.assertEqual(lane_settings.lane_usage_limit({**_lane(), "usage_limited": True,
                                                        "usage_limit_note": "a daily cap"}),
                         (True, "a daily cap"))

    def test_note_removes_terminal_escape(self):
        entry = {"key": "a", "usage_limited": True, "usage_limit_note": "cap\x1b[31m red"}
        self.assertNotIn("\x1b", lane_settings.lane_usage_limit(entry).note)

    def test_non_boolean_raises_naming_the_key(self):
        with self.assertRaisesRegex(lane_settings.LaneSettingError,
                                    "k1: 'usage_limited' must be a boolean"):
            lane_settings.lane_usage_limit({**_lane(), "usage_limited": "yes"})

    def test_layered_merge(self):
        self.write_user(_toml_lane("execute", "k1", 'usage_limited = true\n'
                                   'usage_limit_note = "a daily cap"\npool = "fake:free"',
                                   "fake/placeholder-model-3", "opencode"))
        self.write_project('[[lanes.execute]]\nkey = "k1"\nusage_limit_note = "about 100 a day"\n')
        self.assertEqual(lane_settings.lane_usage_limit(self.resolve()["execute"][0]),
                         (True, "about 100 a day"))
        self.write_project('[[lanes.execute]]\nkey = "k1"\nmodel = "fake/placeholder-model-4"\n')
        self.assertEqual(lane_settings.lane_usage_limit(self.resolve()["execute"][0]), (False, ""))


class TestLaneFallback(unittest.TestCase):
    def test_first_unflagged_in_order(self):
        lanes = [_lane("A", flagged=True, pool="fake:free"), _lane("B", flagged=True),
                 _lane("C"), _lane("D")]
        self.assertEqual(lane_settings.lane_fallback(lanes, "A"), "C")

    def test_same_pool_lane_is_skipped(self):
        lanes = [_lane("A", flagged=True, pool="fake:free"), _lane("B", pool="fake:free"),
                 _lane("C", pool="fake-other:free")]
        self.assertEqual(lane_settings.lane_fallback(lanes, "A"), "C")

    def test_none_when_every_other_lane_is_flagged_or_pooled(self):
        lanes = [_lane("A", flagged=True, pool="fake:free"), _lane("B", pool="fake:free")]
        self.assertIsNone(lane_settings.lane_fallback(lanes, "A"))
        self.assertIsNone(lane_settings.lane_fallback(
            [_lane("A", flagged=True), _lane("B", flagged=True)], "A"))
        self.assertEqual(lane_settings.lane_fallback(
            [_lane("A", flagged=True), _lane("B")], "A"), "B")

    def test_unknown_key_and_duplicate_key(self):
        lanes = [_lane("A", flagged=True, pool="fake:free"), _lane("C"), _lane("A")]
        self.assertIsNone(lane_settings.lane_fallback(lanes, "missing"))
        self.assertEqual(lane_settings.lane_fallback(lanes, "A"), "C")

    def test_malformed_collections_never_raise(self):
        lanes = ["x", None, {"key": 5}, {"no": "key"}, _lane("A", flagged=True), _lane("B")]
        self.assertEqual(lane_settings.lane_fallback(lanes, "A"), "B")
        malformed = None
        self.assertIsNone(lane_settings.lane_fallback(malformed, "A"))  # type: ignore[arg-type]
        roles = {"review": None, "execute": ["x", None, _lane("A", flagged=True)]}
        self.assertEqual(lane_settings.fallback_warnings(roles, {"execute": ["A"]}),
                         [lane_settings.FALLBACK_WARNING.format(role="execute", keys="A")])

    def test_duplicates_are_removed_first(self):
        lanes = [_lane("A", flagged=True), _lane("A"), _lane("B", flagged=True)]
        self.assertIsNone(lane_settings.lane_fallback(lanes, "A"))
        self.assertEqual(lane_settings.fallback_warnings({"execute": lanes},
                                                         {"execute": ["A", "B"]}),
                         [lane_settings.FALLBACK_WARNING.format(role="execute", keys="A, B")])
        lanes = [_lane("A", flagged=True, pool="fake:free"), _lane("B", pool="fake:free"),
                 _lane("B")]
        self.assertIsNone(lane_settings.lane_fallback(lanes, "A"))

    def test_selectable_lanes_per_role(self):
        a, b, c = _lane("a"), _lane("b"), _lane("c")
        self.assertEqual(lane_settings.selectable_lanes("review", [a, b, c], ["c", "a", "zz"]),
                         [c, a])
        self.assertEqual(lane_settings.selectable_lanes("execute", [a, b, c], ["c", "a"]),
                         [c, a, b])
        self.assertEqual(lane_settings.selectable_lanes("review", [a, b], []), [])
        self.assertEqual(lane_settings.selectable_lanes("execute", [a, b], None), [a, b])


class TestFallbackWarnings(_ScratchLayers):
    def test_warning_text_and_no_warning_cases(self):
        roles = {"review": [_lane("R")], "execute": [_lane("E", flagged=True, pool="fake:free"),
                                                     _lane("F", pool="fake:free")]}
        warning = ("ai-kit-spec: usage_limited execute lane(s) E have no lane to fall back to: "
                   "every other execute lane is usage_limited or in the same pool")
        self.assertEqual(lane_settings.fallback_warnings(
            roles, {"review": ["R"], "execute": ["E", "F"]}), [warning])
        self.assertEqual(lane_settings.fallback_warnings(
            {"execute": [_lane("E", flagged=True), _lane("G")]}, {}), [])
        self.assertEqual(lane_settings.fallback_warnings(
            {"review": [_lane("R2", flagged=True), _lane("R")]}, {}),
            [lane_settings.FALLBACK_WARNING.format(role="review", keys="R2")])

    def test_reader_warns_for_a_hand_written_file(self):
        self.write_user(_toml_lane("execute", "k1", "usage_limited = true")
                        + _toml_lane("execute", "k2", "usage_limited = true", "placeholder-model-2")
                        + '[lanes.policy.execute]\nladder = ["k1", "k2"]\n')
        resolved = self.resolve()
        self.assertEqual([x["key"] for x in resolved["execute"]], ["k1", "k2"])
        warning = lane_settings.FALLBACK_WARNING.format(role="execute", keys="k1, k2")
        self.assertEqual(self.warnings.count(warning), 1)

    def test_reader_uses_the_selectable_lanes_of_each_role(self):
        for role in ("execute", "review"):
            self.warnings.clear()
            self.write_user(_toml_lane(role, "x1")
                            + _toml_lane(role, "x2", 'usage_limited = true\npool = "fake:free"',
                                         "placeholder-model-2")
                            + _toml_lane(role, "x3", 'pool = "fake:free"', "placeholder-model-3")
                            + f'[lanes.policy.{role}]\nladder = ["x3", "x2"]\n')
            self.resolve()
            lines = [x for x in self.warnings if x.startswith("ai-kit-spec: usage_limited")]
            warning = lane_settings.FALLBACK_WARNING.format(role="review", keys="x2")
            self.assertEqual(lines, [] if role == "execute" else [warning])


class TestLaneEscalation(_ScratchLayers):
    def test_absent_is_false(self):
        self.assertEqual(lane_settings.lane_escalation(_lane()), (False, False))

    def test_both_true(self):
        self.assertEqual(lane_settings.lane_escalation(
            {**_lane(), "escalate_runtime": True, "escalate_model": True}), (True, True))

    def test_non_boolean_raises(self):
        with self.assertRaisesRegex(lane_settings.LaneSettingError,
                                    "k1: 'escalate_model' must be a boolean"):
            lane_settings.lane_escalation({**_lane(), "escalate_model": "yes"})

    def test_layered_merge(self):
        self.write_user(_toml_lane("review", "k1", "escalate_model = true"))
        self.write_project('[[lanes.review]]\nkey = "k1"\nescalate_runtime = true\n')
        self.assertEqual(lane_settings.lane_escalation(self.resolve()["review"][0]), (True, True))
        self.write_project('[[lanes.review]]\nkey = "k1"\nescalate_runtime = true\n'
                           'model = "placeholder-model-2"\n')
        self.assertEqual(lane_settings.lane_escalation(self.resolve()["review"][0]), (True, False))


class TestEscalationTarget(unittest.TestCase):
    def test_runtime_and_model_kinds(self):
        lanes = [_lane("a"), _lane("b", model="placeholder-model-2"),
                 _lane("c", runtime="pi", model="placeholder-model-3"),
                 _lane("d", model="placeholder-model-4")]
        for key, kind, target in (("a", "runtime", "c"), ("a", "model", "b"),
                                  ("b", "model", "d"), ("c", "runtime", "d")):
            self.assertEqual(lane_settings.escalation_target(lanes, key, kind), target)

    def test_one_lane_and_last_lane_have_no_target(self):
        for kind in ("runtime", "model"):
            self.assertIsNone(lane_settings.escalation_target([_lane("a")], "a", kind))
        self.assertIsNone(lane_settings.escalation_target([_lane("a"), _lane("d")], "d", "runtime"))

    def test_unknown_key_and_bad_kind(self):
        self.assertIsNone(lane_settings.escalation_target([_lane("a")], "missing", "runtime"))
        with self.assertRaises(ValueError):
            lane_settings.escalation_target([_lane("a")], "a", "vendor")


class TestNoFlagSetter(unittest.TestCase):
    def test_only_lane_settings_holds_a_flag_literal(self):
        files = _scanned_files()
        self.assertTrue(files)
        self.assertEqual([f"{p.relative_to(REPO)}:{lines}" for p in files
                          if (lines := _flag_literal_lines(p.read_text()))], [])

    def test_no_module_calls_a_lane_reader(self):
        files = _scanned_files()
        self.assertTrue(files)
        self.assertEqual([f"{p.relative_to(REPO)}:{lines}" for p in files
                          if (lines := _reader_lines(p.read_text()))], [])

    def test_scanners_catch_a_planted_setter_and_reader(self):
        self.assertEqual(_flag_literal_lines('entry["usage_limited"] = True'), [1])
        self.assertEqual(_flag_literal_lines('"""usage_limited is the owner\'s yes."""'), [])
        self.assertEqual(_reader_lines('from ai_kit_spec import lane_settings\n'
                                       'lane_settings.lane_fallback([], "k")'), [2])
        self.assertEqual(_reader_lines('from ai_kit_spec.lane_settings import lane_usage_limit'),
                         [1])

    def test_writer_and_defaults_set_no_flag(self):
        text, _ = _render({"policy": {"mode": "single"},
                           "lanes": [_lane("r1"), {**_lane("e1"), "purpose": "execute"},
                                     {**_lane("b1"), "purpose": "both"}]})
        for flag in FLAGS:
            self.assertNotIn(flag, text)
            self.assertNotIn(flag, config_io.DEFAULT_POLICY)

    def test_zero_price_lane_gets_no_flag_on_write(self):
        text, err = _render({"lanes": [{**_lane("z1", runtime="opencode",
                                               model="fake/placeholder-model-3", pool="fake:free"),
                                        "purpose": "execute", **FULL_DATA_USE}]})
        self.assertIn("pool", tomllib.loads(text)["lanes"]["execute"][0])
        self.assertNotIn("WARNING", err)
        for flag in FLAGS:
            self.assertNotIn(flag, text)


if __name__ == "__main__":
    unittest.main()
