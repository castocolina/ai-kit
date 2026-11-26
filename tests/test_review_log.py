"""The review round log and the partial-report outcome (judged lanes, reasons)."""

import json
import os
import sys
import tempfile
import unittest

_REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(_REPO_ROOT, "skills", "ai-kit-spec-review"))

from ai_kit_spec import review_log
from ai_kit_spec.error_classifier import REASONS


def ev(rnd, key, state, reason=None, by=None):
    return {"round": rnd, "key": key, "state": state, "reason": reason,
            "cause": None, "by": by, "at": 1.0}


class TestLogFile(unittest.TestCase):
    def test_events_round_trip_one_line_each(self):
        events = [
            {"round": 0, "sizing": {"lanes": 2, "keys": ["lane-a", "lane-b"],
                                    "reason": "signal security"}, "at": 1.0},
            ev(1, "lane-a", "chosen"),
            {"round": 1, "stop": "no_lane_left", "at": 2.0},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "events")
            for event in events:
                review_log.append_event(path, event)
            self.assertEqual(review_log.read_events(path), events)
            with open(path, encoding="utf-8") as stream:
                self.assertEqual(len(stream.readlines()), 3)
            self.assertEqual(os.stat(path).st_mode & 0o777, 0o600)

    def test_bad_lines_are_skipped_and_a_missing_file_reads_empty(self):
        event = ev(1, "lane-a", "chosen")
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "events")
            with open(path, "w", encoding="utf-8") as stream:
                stream.write("not json\n[1, 2]\n\n" + json.dumps(event) + "\n")
            self.assertEqual(review_log.read_events(path), [event])
            self.assertEqual(review_log.read_events(os.path.join(tmp, "missing")), [])


class TestRoundStates(unittest.TestCase):
    def test_last_event_per_key_wins_and_keyless_events_are_skipped(self):
        failed = ev(1, "lane-a", "failed", "quota")
        events = [ev(1, "lane-a", "chosen"), failed, ev(2, "lane-a", "chosen"),
                  {"round": 0, "sizing": {}}, {"round": 1, "stop": "no_lane_left"}]
        self.assertEqual(review_log.round_states(events, 1), {"lane-a": failed})
        self.assertEqual(review_log.round_states(events, 0), {})

    def test_incomplete_lane_objects_are_skipped(self):
        events = [{"round": 1, "key": "lane-a"}, {"round": 1, "key": "lane-b", "state": "lost"},
                  {**ev(1, "lane-c", "judged"), "round": 0},
                  {**ev(1, "lane-c", "judged"), "round": True},
                  {**ev(1, "lane-c", "judged"), "round": "1"}, ev(1, "lane-d", "judged")]
        self.assertEqual(review_log.round_states(events, 1), {"lane-d": ev(1, "lane-d", "judged")})
        review_log.review_outcome(events, 1, [])


class TestReviewOutcome(unittest.TestCase):
    def test_all_judged_is_clean(self):
        events = [ev(1, "lane-a", "chosen"), ev(1, "lane-a", "judged"),
                  ev(1, "lane-b", "chosen"), ev(1, "lane-b", "judged")]
        outcome = review_log.review_outcome(events, 1, ["lane-a", "lane-b"])
        self.assertFalse(outcome.partial)
        self.assertEqual(outcome.judged, ["lane-a", "lane-b"])
        self.assertEqual(review_log.judged_line(outcome), "Judged by: lane-a, lane-b")

    def test_failed_lane_reads_partial_with_its_reason(self):
        events = [ev(1, "lane-a", "judged"), ev(1, "lane-b", "failed", "quota")]
        outcome = review_log.review_outcome(events, 1, ["lane-a", "lane-b"])
        self.assertTrue(outcome.partial)
        self.assertEqual(review_log.judged_line(outcome),
                         "Judged by: lane-a; not judged: lane-b (quota)")

    def test_replaced_lane_and_its_replacement_both_appear(self):
        events = [ev(1, "lane-a", "replaced", "replaced", by="lane-c"),
                  ev(1, "lane-c", "chosen"), ev(1, "lane-c", "judged"),
                  ev(1, "lane-b", "judged")]
        outcome = review_log.review_outcome(events, 1, ["lane-c", "lane-b"])
        self.assertTrue(outcome.partial)
        self.assertEqual(review_log.judged_line(outcome),
                         "Judged by: lane-c, lane-b; not judged: lane-a (replaced, by lane-c)")

    def test_chosen_lane_without_a_result_reads_never_resolved(self):
        outcome = review_log.review_outcome([ev(1, "lane-a", "judged"),
                                             ev(1, "lane-b", "chosen")], 1, [])
        self.assertTrue(outcome.partial)
        self.assertEqual(outcome.others[0][1], "never_resolved")

    def test_an_earlier_round_failure_keeps_the_review_partial(self):
        events = [ev(1, "lane-b", "failed", "capacity"), ev(2, "lane-a", "judged"),
                  ev(2, "lane-b", "judged")]
        outcome = review_log.review_outcome(events, 2, ["lane-a", "lane-b"])
        self.assertTrue(outcome.partial)
        self.assertEqual(review_log.judged_line(outcome),
                         "Judged by: lane-a, lane-b; not judged: lane-b (capacity, round 1)")

    def test_judged_line_follows_the_roster_not_the_log(self):
        events = [ev(1, "lane-b", "judged"), ev(1, "judge-x", "judged"),
                  ev(1, "lane-a", "judged")]
        outcome = review_log.review_outcome(events, 1, ["lane-a", "lane-b"])
        self.assertEqual(outcome.judged, ["lane-a", "lane-b", "judge-x"])
        self.assertEqual(review_log.judged_line(outcome), "Judged by: lane-a, lane-b, judge-x")

    def test_nothing_judged(self):
        events = [ev(1, "lane-a", "failed", "quota"), ev(1, "lane-b", "failed", "capacity")]
        self.assertTrue(review_log.review_outcome(events, 1, []).none_judged)

    def test_unknown_reason_prints_real_error(self):
        events = [ev(1, "lane-a", "judged"), ev(1, "lane-b", "failed", "made_up_reason")]
        outcome = review_log.review_outcome(events, 1, [])
        self.assertEqual(review_log.judged_line(outcome),
                         "Judged by: lane-a; not judged: lane-b (real_error)")

    def test_every_recorded_reason_is_a_listed_key(self):
        events = [ev(1, "lane-a", "judged"), ev(1, "lane-b", "failed", "quota"),
                  ev(1, "lane-c", "replaced", "replaced", by="lane-d"),
                  ev(1, "lane-d", "chosen"), ev(2, "lane-b", "failed", "capacity"),
                  ev(2, "lane-c", "never_resolved", "never_resolved")]
        reasons = set(REASONS)
        for event in events:
            if event["reason"] is not None:
                self.assertIn(event["reason"], reasons)
        for _, reason, _, _ in review_log.review_outcome(events, 2, []).others:
            self.assertIn(reason, reasons)


class TestRecordMerge(unittest.TestCase):
    def test_missing_report_after_chosen_is_never_resolved_else_real_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "events")
            for event in [ev(1, "lane-a", "chosen"), ev(1, "lane-b", "chosen"),
                          ev(1, "lane-c", "chosen"), ev(1, "lane-c", "failed", "quota")]:
                review_log.append_event(path, event)
            self.assertEqual(review_log.record_merge(path, 1, ["lane-a"],
                                                      [("lane-b", True), ("lane-c", True)], 5.0),
                             ["lane-a"])
            states = review_log.round_states(review_log.read_events(path), 1)
            self.assertEqual(states["lane-a"]["state"], "judged")
            self.assertEqual((states["lane-b"]["state"], states["lane-b"]["reason"]),
                             ("never_resolved", "never_resolved"))
            self.assertEqual(states["lane-c"], ev(1, "lane-c", "failed", "quota"))
            review_log.record_merge(path, 1, [], [("lane-d", False)], 5.0)
            states = review_log.round_states(review_log.read_events(path), 1)
            self.assertEqual((states["lane-d"]["state"], states["lane-d"]["reason"]),
                             ("failed", "real_error"))

    def test_re_merge_keeps_never_resolved(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "events")
            review_log.append_event(path, ev(1, "lane-b", "chosen"))
            for _ in range(2):
                review_log.record_merge(path, 1, [], [("lane-b", True)], 5.0)
            states = review_log.round_states(review_log.read_events(path), 1)
            self.assertEqual((states["lane-b"]["state"], states["lane-b"]["reason"]),
                             ("never_resolved", "never_resolved"))
            self.assertEqual(len(review_log.read_events(path)), 2)

    def test_readable_report_never_overturns_failed_or_replaced(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "events")
            events = [ev(1, "lane-a", "chosen"), ev(1, "lane-b", "chosen"),
                      ev(1, "lane-c", "chosen"), ev(1, "lane-b", "failed", "quota"),
                      ev(1, "lane-a", "replaced", "replaced", by="lane-c")]
            for event in events:
                review_log.append_event(path, event)
            readable = ["lane-a", "lane-b", "lane-c"]
            self.assertEqual(review_log.record_merge(path, 1, readable, [], 5.0), ["lane-c"])
            recorded = review_log.read_events(path)
            states = review_log.round_states(recorded, 1)
            self.assertEqual(states["lane-a"], events[-1])
            self.assertEqual(states["lane-b"], events[-2])
            self.assertEqual(states["lane-c"]["state"], "judged")
            self.assertEqual(review_log.record_merge(path, 1, readable, [], 5.0), ["lane-c"])
            self.assertEqual(len(review_log.read_events(path)), len(recorded))


if __name__ == "__main__":
    unittest.main()
