"""36-05: lane_effort forms, write checks and offered levels (SPEC R4)."""

import os
import sys
import unittest

_REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(_REPO_ROOT, "skills", "ai-kit-spec-review"))

from ai_kit_spec.lane_effort import (
    LevelOffer,
    effort_problem,
    effort_source_label,
    listed_ids,
    offered_levels,
    write_problems,
)

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

    def test_levels_are_tokens_not_sets(self):
        for rt, value in (("codex", "max"), ("pi", "ultra")):
            self.assertIsNone(effort_problem(
                {"key": "k", "runtime": rt, "effort": value}))

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
    def test_catalog_levels_in_order(self):
        offer = offered_levels("codex", "placeholder-model-1", CAT, None)
        self.assertEqual(offer.levels, ("minimal", "low", "medium", "high", "xhigh", "max"))
        self.assertEqual(offer.source, "catalog")
        self.assertEqual(offer.refused, ())

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

    def test_unknown_and_every_runtime_offered(self):
        for rt in ("opencode", "claude", "copilot"):
            self.assertEqual(offered_levels(rt, "fake/placeholder-model-9", CAT, SNAP),
                             LevelOffer((), None, ()))

        for rt in ("claude", "copilot"):
            self.assertEqual(offered_levels(rt, "placeholder-model-1",
                             row(rt, "placeholder-model-1", ["high"]), None),
                             LevelOffer(("high",), "catalog", ()))

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

    def test_listed_level_beyond_old_sets_is_written(self):
        lane = {"key": "k", "runtime": "codex", "model": "placeholder-model-1", "effort": "max"}
        self.assertEqual(write_problems([lane], CAT, None), [])

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
