"""36-05: lane_effort forms, write checks and offered levels (SPEC R4)."""

import os
import re
import sys
import unittest
from pathlib import Path

_REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(_REPO_ROOT, "skills", "ai-kit-spec-review"))

from ai_kit_spec import lane_effort, runner_dispatch
from ai_kit_spec.detection import RUNTIMES
from ai_kit_spec.lane_effort import (
    EffortForm,
    LevelOffer,
    effort_form,
    effort_problem,
    effort_source_label,
    has_effort_path,
    listed_ids,
    offered_levels,
    write_problems,
)
from ai_kit_spec.tooling_guidance import resolve_cross_ai_template_path

CAT = {"fake/placeholder-model-1": {"runtimes": {"codex": {
    "model_id": "placeholder-model-1",
    "efforts": ["high", "low", "max", "medium", "minimal", "xhigh"]
}}}}
SNAP = {"clis": {
    "pi": {"reasoning_modes": {"fake/placeholder-model-2": ["off", "low", "high"]}},
    "opencode": {"model_records": {"fake/placeholder-model-3": {"efforts": ["high", "low"]}}},
}}


def row(runtime, ident, levels):
    return {"fake/placeholder-model-1": {"runtimes": {
        runtime: {"model_id": ident, "efforts": levels}
    }}}


class TestEffortForm(unittest.TestCase):
    def test_no_effort_passes_nothing(self):
        for rt in ("codex", "pi", "cursor", "opencode", "claude", "copilot"):
            with self.subTest(rt=rt):
                self.assertEqual(
                    effort_form(rt, "placeholder-model-1", None),
                    EffortForm("placeholder-model-1", (), None),
                )

    def test_runtime_forms(self):
        cases = [
            ("codex", "placeholder-model-1", "placeholder-model-1", ("--codex-effort", "high")),
            ("pi", "fake/placeholder-model-1", "fake/placeholder-model-1:high", ()),
            ("opencode", "fake/placeholder-model-1", "fake/placeholder-model-1#high", ()),
            ("cursor", "placeholder-model-1", "placeholder-model-1[effort=high]", ()),
            ("cursor", "placeholder-model-1[context=1m]",
             "placeholder-model-1[context=1m,effort=high]", ()),
        ]
        for rt, ident, expected, flags in cases:
            with self.subTest(rt=rt, ident=ident):
                self.assertEqual(effort_form(rt, ident, "high"), EffortForm(expected, flags, None))

    def test_carried_effort(self):
        for rt, ident in (("pi", "fake/placeholder-model-1:high"),
                          ("opencode", "fake/placeholder-model-1#high"),
                          ("cursor", "placeholder-model-1[context=1m,effort=high]")):
            with self.subTest(rt=rt):
                self.assertEqual(effort_form(rt, ident, "high"), EffortForm(ident, (), None))
                self.assertEqual(
                    effort_form(rt, ident, "low").ignored,
                    "ignored: the model id already carries effort 'high'; "
                    "lane effort 'low' not applied",
                )

    def test_closed_sets_ignored(self):
        self.assertIn("closed set minimal|low|medium|high|xhigh",
                      effort_form("codex", "placeholder-model-1", "max").ignored or "")
        self.assertIn("not 'ultra'",
                      effort_form("pi", "fake/placeholder-model-1", "ultra").ignored or "")

    def test_no_path_runtimes(self):
        for rt in ("codex", "pi", "cursor", "opencode"):
            self.assertTrue(has_effort_path(rt))
        for rt in ("claude", "copilot", "placeholder-cli-1", None):
            self.assertFalse(has_effort_path(rt))
            if rt:
                self.assertEqual(effort_form(rt, "placeholder-model-1", "high").ignored,
                                 f"ignored: the runner has no effort flag for {rt}")

    def test_bad_shape_and_no_runtime(self):
        for rt, value in (("opencode", "High"), ("opencode", ""), ("pi", 3)):
            self.assertIn("does not match",
                          effort_form(rt, "placeholder-model-1", value).ignored or "")
        key = "sk-" + "A" * 24
        line = effort_form("opencode", "placeholder-model-1", "x\x07" + key).ignored
        assert line is not None
        self.assertIn("[redacted]", line)
        self.assertNotIn(key, line)
        self.assertNotIn("\x07", line)
        line = effort_form(
            "opencode", "placeholder-model-1", "sk-" + "A" * 10 + "\x07" + "A" * 14
        ).ignored
        assert line is not None
        self.assertNotIn("A" * 24, line)
        self.assertIn("[redacted]", line)
        self.assertEqual(effort_form(None, "", "high").ignored, lane_effort.NO_RUNTIME_IGNORED)

    def test_listed_pi_id_keeps_its_suffix(self):
        ident = "fake/placeholder-model-1:high"
        for level in ("low", "high"):
            self.assertEqual(effort_form("pi", ident, level, frozenset({ident})).model,
                             ident + ":" + level)
        ident = "fake/placeholder-model-1#high"
        self.assertIsNotNone(effort_form("opencode", ident, "low", frozenset({ident})).ignored)

    def test_composed_ids_pass_the_runner_grammar(self):
        for rt, ident in (("pi", "fake/placeholder-model-1"),
                          ("opencode", "fake/placeholder-model-1"),
                          ("cursor", "placeholder-model-1")):
            self.assertTrue(runner_dispatch.model_id_ok(rt, effort_form(rt, ident, "high").model))

    def test_runner_sets_match_the_template(self):
        path = resolve_cross_ai_template_path()
        assert path is not None
        text = Path(path).read_text(encoding="utf-8")
        for name, levels in (("CODEX_EFFORTS", lane_effort.RUNNER_CODEX_EFFORTS),
                             ("PI_THINKING", lane_effort.RUNNER_PI_LEVELS)):
            match = re.search(rf"const {name} = new Set\(\[(.*?)\]\);", text)
            self.assertIsNotNone(match)
            assert match is not None
            self.assertEqual(set(re.findall(r"'([^']+)'", match.group(1))), set(levels))
        suffix = RUNTIMES["pi"].model_suffix
        assert suffix is not None
        for level in lane_effort.RUNNER_PI_LEVELS:
            self.assertIsNotNone(re.search(suffix, ":" + level))


class TestEffortProblem(unittest.TestCase):
    def test_absent_effort_and_valid_levels(self):
        self.assertIsNone(effort_problem({"runtime": "codex"}))
        for rt, value in (("codex", "minimal"), ("codex", "xhigh"), ("pi", "off"),
                          ("pi", "max"), ("opencode", "a" * 16), ("claude", "high"),
                          ("copilot", "high")):
            self.assertIsNone(effort_problem({"runtime": rt, "effort": value}))

    def test_type_and_shape_named(self):
        for value in ("", 3, "HIGH", "a" * 17):
            self.assertIn("'effort' must", effort_problem(
                {"key": "k", "runtime": "opencode", "effort": value}) or "")

    def test_effort_needs_a_table_runtime(self):
        for extra in ({}, {"command": "tool {prompt}"}):
            self.assertIn("needs a table runtime", effort_problem(
                {"key": "k", "effort": "high", **extra}) or "")

    def test_closed_sets_refused(self):
        for rt, value in (("codex", "max"), ("pi", "ultra")):
            self.assertIn("cannot be passed", effort_problem(
                {"key": "k", "runtime": rt, "effort": value}) or "")

    def test_effort_source(self):
        label = effort_source_label("2026-11-20")
        self.assertEqual(label, "accepted by a call on 2026-11-20")
        self.assertIsNone(effort_problem(
            {"runtime": "codex", "effort": "high", "effort_source": label}))
        self.assertIn("needs 'effort'", effort_problem({"effort_source": label}) or "")
        for value in ("accepted", 5):
            self.assertIn("<unknown>", effort_problem(
                {"runtime": "pi", "effort": "high", "effort_source": value}) or "")


class TestOfferedLevels(unittest.TestCase):
    def test_catalog_levels_with_runner_refusal(self):
        offer = offered_levels("codex", "placeholder-model-1", CAT, None)
        self.assertEqual(offer.levels, ("minimal", "low", "medium", "high", "xhigh"))
        self.assertEqual(offer.source, "catalog")
        self.assertEqual(offer.refused[0][0], "max")

    def test_snapshot_fallback_in_host_order(self):
        self.assertEqual(offered_levels("pi", "fake/placeholder-model-2", {}, SNAP),
                         LevelOffer(("off", "low", "high"), "runtimes snapshot", ()))
        self.assertEqual(offered_levels("opencode", "fake/placeholder-model-3", None, SNAP).levels,
                         ("high", "low"))

    def test_catalog_set_uses_snapshot_order(self):
        ident = "fake/placeholder-model-2"
        self.assertEqual(offered_levels("pi", ident, row("pi", ident, ["high", "low", "off"]),
                                        SNAP).levels, ("off", "low", "high"))
        self.assertEqual(offered_levels("pi", ident, row("pi", ident, ["high", "medium"]),
                                        SNAP).levels, ("medium", "high"))

    def test_unknown_and_no_path(self):
        for rt in ("opencode", "claude", "copilot"):
            self.assertEqual(offered_levels(rt, "fake/placeholder-model-9", CAT, SNAP),
                             LevelOffer((), None, ()))

    def test_suffix_stripped_and_name_words(self):
        self.assertEqual(offered_levels("pi", "fake/placeholder-model-2:high", {}, SNAP).levels,
                         ("off", "low", "high"))
        offer = offered_levels("cursor", "placeholder-model-4",
                               row("cursor", "placeholder-model-4", ["high", "thinking"]), None)
        self.assertEqual(offer.levels, ("high",))
        self.assertEqual(offer.refused[0][0], "thinking")


class TestWriteProblems(unittest.TestCase):
    def test_outside_listed_set_refused_whole_token(self):
        lane = {"key": "k", "runtime": "codex", "model": "placeholder-model-5", "effort": "high"}
        catalog = row("codex", "placeholder-model-5", ["xhigh"])
        self.assertEqual(write_problems([lane], catalog, None),
                         ["k: effort 'high' is not in the model's list (xhigh) [catalog]"])

    def test_runner_refused_level_named(self):
        lane = {"key": "k", "runtime": "codex", "model": "placeholder-model-1", "effort": "max"}
        self.assertIn("cannot be passed", write_problems([lane], CAT, None)[0])

    def test_unknown_support_and_skips(self):
        lanes = [{"runtime": "opencode", "model": "fake/placeholder-model-9", "effort": "high"},
                 {"runtime": "claude", "model": "placeholder-model-1", "effort": "high"},
                 {}, "not-a-lane"]
        self.assertEqual(write_problems(lanes, CAT, None), [])

    def test_listed_pi_id_offer_and_write(self):
        ident = "fake/placeholder-model-6:high"
        catalog = row("pi", ident, ["high", "low"])
        self.assertEqual(offered_levels("pi", ident, catalog, None).levels, ("low", "high"))
        self.assertEqual(write_problems([{"runtime": "pi", "model": ident, "effort": "low"}],
                                        catalog, None), [])
        self.assertEqual(listed_ids("pi", catalog, {"clis": {"pi": {
            "models": ["fake/placeholder-model-7"]}}}),
            frozenset({ident, "fake/placeholder-model-7"}))

    def test_given_listed_set_replaces_the_scan(self):
        ident = "fake/placeholder-model-6:high"
        snapshot = {"clis": {"pi": {"models": [ident], "reasoning_modes": {ident: ["low"]}}}}
        self.assertEqual(offered_levels("pi", ident, None, snapshot, frozenset({ident})).levels,
                         ("low",))
        self.assertEqual(offered_levels("pi", ident, None, snapshot, frozenset()),
                         LevelOffer((), None, ()))


if __name__ == "__main__":
    unittest.main()
