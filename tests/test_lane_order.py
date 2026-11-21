"""Phase 36: lane_order and the jev score seam (propose-lanes order)."""

import copy
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

_REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(_REPO_ROOT, "skills", "ai-kit-spec-review"))

from ai_kit_spec import catalog_bands, jev_names, lane_order, lane_pool, model_ranker

T = "2026-11-20T00:00:00Z"
W = copy.deepcopy(model_ranker.DEFAULT_WEIGHTS)


def _fact(value):
    return {"value": value, "label": "measured", "source": "fixture", "fetched_at": T}


def _entry(n, score=None, klass="flagship", tier="frontier", band="high", efforts=None):
    row = {"model_id": f"fake/placeholder-model-{n}"}
    if efforts is not None:
        row["efforts"] = efforts
    return {"provider": "fake", "runtimes": {"pi": row},
            "scores": {"intelligence_index": score} if score is not None else {},
            "facts": {"tier": _fact(tier), "class": _fact(klass), "cost_band": _fact(band)}}


def _rows(*numbered):
    return lane_pool.build_rows({f"fake/placeholder-model-{n}": entry for n, entry in numbered},
                                {"clis": {}})


class _Judge:
    def __init__(self, answers):
        self.answers = answers
        self.calls = []

    def __call__(self, pairs):
        self.calls.append(pairs)
        return self.answers[:len(pairs)]


def _sample():
    return _rows((1, _entry(1, 70)), (2, _entry(2, 90)), (3, _entry(3, 90)))


def _ids(ranked):
    return [item.row.key.rsplit("-", 1)[-1] for item in ranked]


class TestDeterministicOrder(unittest.TestCase):
    def test_scorer_order_and_tie_by_key(self):
        pairs = lane_order.deterministic_order(_sample(), "review", W)
        self.assertEqual([row.key[-1] for row, _ in pairs], ["2", "3", "1"])
        self.assertEqual(pairs[0][1], pairs[1][1])

    def test_score_uses_only_the_row_runtime(self):
        entry = _entry(4)
        entry["runtimes"]["pi"]["ctx_window"] = 1000000
        entry["runtimes"]["opencode"] = {"model_id": "fake/placeholder-model-4", "ctx_window": 1000}
        pairs = lane_order.deterministic_order(_rows((4, entry)), "review", W)
        self.assertEqual([row.runtime for row, _ in pairs], ["pi", "opencode"])

    def test_malformed_numbers_score_as_missing(self):
        first, second, third = _entry(1), _entry(2), _entry(3)
        first.update(pricing={"input_per_1m": "cheap"}, scores={"intelligence_index": True})
        first["runtimes"]["pi"]["ctx_window"] = "big"
        third["runtimes"]["pi"]["ctx_window"] = -5
        pairs = lane_order.deterministic_order(
            _rows((1, first), (2, second), (3, third)), "review", W)
        self.assertEqual(len({score for _, score in pairs}), 1)
        self.assertEqual([row.key[-1] for row, _ in pairs], ["1", "2", "3"])

    def test_huge_integer_scores_as_missing(self):
        pairs = lane_order.deterministic_order(
            _rows((1, _entry(1, 10**400)), (2, _entry(2))), "review", W)
        self.assertEqual(pairs[0][1], pairs[1][1])


class TestRank(unittest.TestCase):
    def test_confident_jev_reorders(self):
        judge = _Judge([("fair fit", 0.9, ""), ("fair fit", 0.9, ""), ("excellent fit", 0.9, "")])
        result = lane_order.rank(_sample(), "review", W, judge, set())
        self.assertEqual(_ids(result), ["1", "2", "3"])
        self.assertTrue(all(x.ranked_by == "jev" and x.asked for x in result))
        self.assertEqual((result[0].level, result[0].top, result[0].reason),
                         ("excellent fit", 0.9, "jev: excellent fit (top 0.90)"))
        self.assertEqual([p[0] for p in judge.calls[0]], ["review"] * 3)
        self.assertEqual(len(judge.calls), 1)

    def test_absent_jev_keeps_the_scorer_order(self):
        result = lane_order.rank(_sample(), "review", W, None, set())
        self.assertEqual(_ids(result), ["2", "3", "1"])
        self.assertTrue(all(x.reason == lane_order.JEV_NOT_USED and not x.asked for x in result))

    def test_low_answers_keep_the_scorer_order(self):
        judge = _Judge([("excellent fit", .79, ""), ("excellent fit", .74, ""), (None, .67, "low")])
        result = lane_order.rank(_sample(), "review", W, judge, set())
        self.assertEqual(_ids(result), ["2", "3", "1"])
        self.assertTrue(all(x.reason == "scorer: jev gave a low answer" and x.level is None
                            and x.top is None for x in result))

    def test_error_answers_name_their_reason(self):
        judge = _Judge([(None, None, "no answer"), (None, None, "timeout"), (None, None, "old")])
        result = lane_order.rank(_sample(), "review", W, judge, set())
        self.assertEqual([x.reason for x in result], ["scorer: jev gave no answer",
                         "scorer: jev timed out", "scorer: jev too old"])
        judge.answers = judge.answers[:2]
        self.assertEqual(lane_order.rank(_sample(), "review", W, judge, set())[2].reason,
                         "scorer: jev gave no answer")

    def test_window_holds_seven_plus_five_zero_rows_in_one_call(self):
        rows = _rows(*[(n, _entry(n, 100 - n)) for n in range(1, 15)])
        zero = {(f"fake/placeholder-model-{n}", "pi") for n in (3, 9, 10, 11, 12, 13)}
        judge = _Judge([("good fit", .9, "")] * 14)
        result = lane_order.rank(rows, "review", W, judge, zero)
        self.assertEqual(len(judge.calls[0]), 11)
        self.assertEqual(_ids(result), list(map(str, (1, 2, 3, 4, 5, 6, 7, 9, 10, 11, 12,
                                                      8, 13, 14))))
        self.assertTrue(all(x.asked for x in result[:11]))
        self.assertTrue(all(not x.asked and x.reason == lane_order.OUTSIDE_WINDOW
                            for x in result[11:]))

    def test_unknown_rows_last_and_never_sent(self):
        rows = _rows((1, _entry(1, 70)), (2, _entry(2, 80)), (5, _entry(5, 99, klass="unknown")))
        judge = _Judge([])
        result = lane_order.rank(rows, "review", W, judge, set())
        self.assertEqual(_ids(result), ["2", "1", "5"])
        self.assertEqual(result[-1].reason, lane_order.UNKNOWN_FACTS)
        self.assertEqual(len(judge.calls[0]), 2)

    def test_inputs_not_mutated(self):
        rows = _sample()
        before = copy.deepcopy(rows)
        lane_order.rank(rows, "review", W, _Judge([]), set())
        self.assertEqual(rows, before)

    def test_raising_judge_falls_back(self):
        def fail(_pairs):
            raise RuntimeError("boom")
        for judge in (fail, _Judge([None, ("good fit",), ("good fit", .9, ["x"])])):
            result = lane_order.rank(_sample(), "review", W, judge, set())
            self.assertEqual(_ids(result), ["2", "3", "1"])
            self.assertTrue(all(x.reason == lane_order.JEV_ERROR for x in result))


class TestFactsSummary(unittest.TestCase):
    def test_closed_facts_only(self):
        entry = _entry(1, klass="coding", tier="strong", band="low",
                       efforts=["high", "off", "abc-12", "ghp_" + "A" * 24, "x y"])
        entry["facts"]["strengths"] = _fact(["coding"])
        summary = lane_order.facts_summary(_rows((1, entry))[0])
        self.assertEqual(summary, "Facts: tier strong; class coding; cost band low; "
                         "strengths coding; effort levels high.")
        item = jev_names.score_item(0, "execute", summary)
        self.assertTrue(json.dumps(item).isascii())
        for text in ("placeholder", "fake/", "router-env", "abc-12", "ghp_"):
            self.assertNotIn(text, json.dumps(item))
        self.assertEqual(item["context"], summary)

    def test_no_facts_reads_unknown(self):
        entry = _entry(1)
        entry["facts"] = {}
        self.assertEqual(lane_order.facts_summary(_rows((1, entry))[0]),
                         "Facts: tier unknown; class unknown; cost band unknown; "
                         "strengths none; effort levels none.")


class TestScoreJudge(unittest.TestCase):
    def test_score_item_shape(self):
        item = jev_names.score_item(3, "review", "Facts: x\né" + "y" * 300)
        self.assertEqual((item["id"], item["type"], item["instructions"], item["criteria"]),
                         ("c3", "score", jev_names.SCORE_QUESTIONS["review"],
                          list(jev_names.SCORE_LEVELS)))
        self.assertTrue(item["context"].isascii())
        self.assertEqual(len(item["context"]), 240)
        self.assertNotIn("\n", item["context"])

    def test_score_judge_maps_answers(self):
        with tempfile.TemporaryDirectory() as folder:
            root = pathlib.Path(folder)
            entry = root / "jev-fast-decision" / "scripts" / "jev_review.py"
            entry.parent.mkdir(parents=True)
            entry.touch()
            calls = []
            def run(_args, input, **_kwargs):
                calls.append(json.loads(input))
                data = {"items": {
                    "c0": {"decided_by": "fake", "fake": {"choice": "good fit", "top": .9}},
                    "c1": {"decided_by": "fake", "fake": {"choice": "good fit", "top": .9,
                                                           "needs_fallback": True}}}}
                return subprocess.CompletedProcess([], 0, stdout=json.dumps(data), stderr="")
            judge = jev_names.score_judge({"HOME": str(root / "home")}, str(root), run)
            assert judge is not None
            self.assertEqual(judge([("review", "Facts: a"), ("execute", "Facts: b")]),
                             [("good fit", .9, ""), (None, .9, "low")])
            self.assertEqual(len(calls), 1)
            self.assertEqual([x["instructions"] for x in calls[0]["items"]],
                             [jev_names.SCORE_QUESTIONS["review"],
                              jev_names.SCORE_QUESTIONS["execute"]])

    def test_score_judge_absent(self):
        with tempfile.TemporaryDirectory() as folder:
            self.assertIsNone(jev_names.score_judge({"HOME": folder},
                                                    str(pathlib.Path(folder) / "empty")))

    def test_worst_case_window_is_one_batch(self):
        entries = []
        for n in range(12):
            entry = _entry(n, band="free_or_local", efforts=list(lane_order.EFFORT_FACT_LEVELS))
            entry["facts"]["strengths"] = _fact(list(catalog_bands.STRENGTH_CATEGORIES))
            entries.append((n, entry))
        items = [jev_names.score_item(i, "review", lane_order.facts_summary(row))
                 for i, row in enumerate(_rows(*entries))]
        text = json.dumps({"items": items})
        self.assertTrue(text.isascii())
        self.assertLessEqual(len(text), jev_names.BATCH_CHARS)
        self.assertEqual(len(jev_names._batches(items)), 1)


if __name__ == "__main__":
    unittest.main()
