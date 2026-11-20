"""Tests for the phase-35 host model name parser and resolver."""

import os
import sys
import unittest

_REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(_REPO_ROOT, "skills", "ai-kit-spec-review"))

from ai_kit_spec.model_names import (
    BlankNameError,
    candidates,
    known_ids_from_models_dev,
    resolve_many,
    split_effort,
)


class TestEffortParsing(unittest.TestCase):
    def test_pi_style(self):
        self.assertEqual(
            split_effort("pi", "router-env/placeholder-model-1:high"),
            ("router-env/placeholder-model-1:high", "router-env/placeholder-model-1", ("high",)),
        )

    def test_opencode_style(self):
        self.assertEqual(
            split_effort("opencode", "router-env/placeholder-model-1#xhigh").efforts, ("xhigh",)
        )

    def test_cursor_styles(self):
        self.assertEqual(
            split_effort("cursor", "placeholder-model-2[effort=high]").efforts, ("high",)
        )
        self.assertEqual(
            split_effort("cursor", "placeholder-model-2-high").base, "placeholder-model-2"
        )
        self.assertEqual(split_effort("cursor", "fake-name-high").base, "fake-name")
        self.assertEqual(
            split_effort("cursor", "fake-name-non-thinking").efforts, ("non-thinking",)
        )

    def test_known_ids_from_models_dev(self):
        self.assertEqual(
            known_ids_from_models_dev(
                {"fake": {"models": {"placeholder-model-6-max": {}}}, "bad": 3}
            ),
            frozenset({"placeholder-model-6-max", "fake/placeholder-model-6-max"}),
        )

    def test_arena_style(self):
        parts = split_effort("arena", "placeholder-model-3 (thinking)")
        self.assertEqual((parts.base, parts.efforts), ("placeholder-model-3", ("thinking",)))
        self.assertEqual(split_effort("arena", "placeholder-model-3 (bf16)").efforts, ())

    def test_flag_hosts_unchanged(self):
        for runtime, name in (
            ("codex", "placeholder-model-4-high"),
            ("claude", "placeholder-alias-1"),
            ("copilot", "placeholder-model-5"),
        ):
            self.assertEqual(split_effort(runtime, name).base, name)
            self.assertEqual(split_effort(runtime, name).efforts, ())

    def test_known_id_kept_whole(self):
        parts = split_effort(
            "cursor", "placeholder-model-6-max", frozenset({"placeholder-model-6-max"})
        )
        self.assertEqual((parts.base, parts.efforts), ("placeholder-model-6-max", ()))

    def test_blank_name_refused(self):
        with self.assertRaisesRegex(BlankNameError, "^blank model name$"):
            split_effort("pi", "  ")


class TestResolution(unittest.TestCase):
    def test_exact_normalized_match(self):
        result = resolve_many(
            ["Placeholder_Model_1"], {"placeholder-model-1": "router-env/placeholder-model-1"}
        )["Placeholder_Model_1"]
        self.assertEqual(
            (result.state, result.key, result.confidence),
            ("matched", "router-env/placeholder-model-1", None),
        )

    def test_tie_is_unmatched_with_both(self):
        result = resolve_many(
            ["placeholder-model-7"], {"placeholder-model-71": "k1", "placeholder-model-72": "k2"}
        )["placeholder-model-7"]
        self.assertEqual(result.state, "unmatched")
        self.assertEqual(set(result.candidates), {"placeholder-model-71", "placeholder-model-72"})

    def test_confident_judge(self):
        calls = []

        def judge(pairs):
            calls.extend(pairs)
            return [("placeholder-model-72", 0.9, "")]

        result = resolve_many(
            ["placeholder-model-7"],
            {"placeholder-model-71": "k1", "placeholder-model-72": "k2"},
            judge,
        )["placeholder-model-7"]
        self.assertEqual((result.state, result.key, result.confidence), ("judged", "k2", 0.9))
        self.assertEqual(
            calls, [("placeholder-model-7", ["placeholder-model-71", "placeholder-model-72"])]
        )

    def test_no_answer(self):
        result = resolve_many(
            ["placeholder-model-7"],
            {"placeholder-model-71": "k1", "placeholder-model-72": "k2"},
            lambda _pairs: [(None, None, "no answer")],
        )["placeholder-model-7"]
        self.assertEqual(result.state, "unmatched")
        self.assertEqual(len(result.candidates), 2)

    def test_low_answers_unmatched(self):
        pool = {"placeholder-model-71": "k1", "placeholder-model-72": "k2"}
        for answer in (
            ("placeholder-model-72", 0.3, ""),
            ("placeholder-model-72", None, ""),
            ("placeholder-model-72", True, ""),
            ("placeholder-model-72", 1.5, ""),
        ):
            result = resolve_many(
                ["placeholder-model-7"], pool, lambda _pairs, answer=answer: [answer]
            )["placeholder-model-7"]
            self.assertEqual((result.state, result.key), ("unmatched", None))

    def test_judge_outside_or_malformed(self):
        pool = {"placeholder-model-71": "k1", "placeholder-model-72": "k2"}
        for answer in (("placeholder-model-99", 0.9, ""), "not-a-tuple"):
            result = resolve_many(
                ["placeholder-model-7"], pool, lambda _pairs, answer=answer: [answer]
            )["placeholder-model-7"]
            self.assertEqual(result.state, "unmatched")
        results = resolve_many(
            ["placeholder-model-7", "placeholder-model-8"],
            {
                **pool,
                "placeholder-model-81": "k3",
                "placeholder-model-82": "k4",
            },
            lambda _pairs: [("placeholder-model-72", 0.9, "")],
        )
        self.assertEqual(results["placeholder-model-7"].state, "judged")
        self.assertEqual(results["placeholder-model-8"].state, "unmatched")

    def test_unmatched_name_sent_with_floor_candidates(self):
        calls = []

        def judge(pairs):
            calls.extend(pairs)
            return [(None, None, "")]

        result = resolve_many(["placeholder-model-9"], {"placeholder-alias-9": "k9"}, judge)[
            "placeholder-model-9"
        ]
        self.assertEqual(result.state, "unmatched")
        self.assertTrue(calls)
        calls.clear()
        empty = resolve_many(["fake-zz"], {"placeholder-alias-9": "k9"}, judge)["fake-zz"]
        self.assertEqual((empty.candidates, calls), ((), []))

    def test_candidate_limit_and_order(self):
        pool = [
            "placeholder-model-71",
            "placeholder-model-72",
            "placeholder-model-73",
            "placeholder-model-74",
            "placeholder-model-75",
            "placeholder-model-76",
        ]
        self.assertLessEqual(len(candidates("placeholder-model-7", pool)), 5)
        self.assertEqual(
            candidates("placeholder-model-7", pool),
            sorted(
                candidates("placeholder-model-7", pool),
                key=lambda item: (
                    -__import__("difflib")
                    .SequenceMatcher(
                        None, "placeholdermodel7", __import__("re").sub(r"[^a-z0-9]+", "", item)
                    )
                    .ratio(),
                    item,
                ),
            ),
        )

    def test_six_way_tie_decided_on_full_list(self):
        pool = {
            "placeholder-model-1": "k1",
            "Placeholder_Model_1": "k2",
            "PLACEHOLDER MODEL 1": "k3",
            "placeholder.model.1": "k4",
            "placeholder_model-1": "k5",
            "Placeholder-Model_1": "k6",
        }
        result = resolve_many(["placeholder-model-1"], pool)["placeholder-model-1"]
        self.assertEqual((result.state, result.key, len(result.candidates)), ("unmatched", None, 6))
        calls = []

        def judge(pairs):
            calls.extend(pairs)
            return [("placeholder_model-1", 0.9, "")]

        judged = resolve_many(["placeholder-model-1"], pool, judge)["placeholder-model-1"]
        self.assertEqual(judged.state, "unmatched")
        self.assertEqual(
            calls[0][1],
            [
                "PLACEHOLDER MODEL 1",
                "Placeholder-Model_1",
                "Placeholder_Model_1",
                "placeholder-model-1",
                "placeholder.model.1",
            ],
        )


if __name__ == "__main__":
    unittest.main()
