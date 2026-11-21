"""Phase 36: lane_data_use (the data-use record of a free lane)."""

import copy
import os
import sys
import unittest

_REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(_REPO_ROOT, "skills", "ai-kit-spec-review"))

from ai_kit_spec import lane_data_use

GOOD = {"data_use": "zero_retention", "data_use_line": "Inputs are not kept.",
        "data_use_source": "https://example.invalid/data-policy", "data_use_read": "2026-11-20",
        "data_use_label": "verified", "data_use_confirmed": True}
UNKNOWN = {"data_use": "unknown", "data_use_line": "not read", "data_use_source": "none",
           "data_use_read": "2026-11-20", "data_use_confirmed": True}


class TestDataUseRecord(unittest.TestCase):
    def test_no_record_is_valid(self):
        self.assertIsNone(lane_data_use.validate_note({}))
        self.assertIsNone(lane_data_use.validate_note(
            {"runtime": "pi", "model": "placeholder-model-1"}))

    def test_full_records_valid(self):
        for entry in (GOOD, {**GOOD, "data_use": "may_be_kept_or_trained",
                             "data_use_label": "reported"},
                      UNKNOWN, {**UNKNOWN, "data_use_source": "https://example.invalid/data-policy"}):
            self.assertIsNone(lane_data_use.validate_note(entry))

    def test_incomplete_record(self):
        self.assertEqual(lane_data_use.validate_note({"data_use": "unknown"}),
                         "data-use record is incomplete: missing data_use_line, data_use_source, "
                         "data_use_read, data_use_confirmed")
        entry = dict(GOOD)
        del entry["data_use_read"]
        self.assertEqual(lane_data_use.validate_note(entry),
                         "data-use record is incomplete: missing data_use_read")

    def test_field_values_refused(self):
        secret = "ghp_" + "A" * 24
        cases: list = [({"data_use": "safe"}, "data_use must be one of: zero_retention, "
                  "may_be_kept_or_trained, unknown")]
        for value in ("two\nlines", "", "x" * 201, "key " + secret):
            cases.append(({"data_use_line": value}, "data_use_line must be one non-empty line "
                          "of at most 200 characters, with no control characters "
                          "and no key shapes"))
        for value in ("http://example.invalid", "https://example.invalid/" + "a" * 280,
                      "https://example.invalid/?k=" + secret):
            cases.append(({"data_use_source": value}, "data_use_source must be an https:// address "
                          "of at most 300 characters with no key shape, or none"))
        for value in ("2026-13-01", "20261120"):
            cases.append(({"data_use_read": value},
                          "data_use_read must be a date in the form YYYY-MM-DD"))
        for value in (False, "true"):
            cases.append(({"data_use_confirmed": value}, "data_use_confirmed must be true "
                          "(a lane the owner declined is not written)"))
        for override, message in cases:
            with self.subTest(override=override):
                self.assertEqual(lane_data_use.validate_note({**GOOD, **override}), message)

    def test_source_rejects_control_characters(self):
        entry = {**GOOD, "data_use_source": "https://example.org/a\x1bb"}
        self.assertEqual(lane_data_use.validate_note(entry),
                         "data_use_source must be an https:// address of at most 300 characters "
                         "with no key shape, or none")
        entry["data_use_source"] = "https://example.org/a"
        self.assertIsNone(lane_data_use.validate_note(entry))

    def test_label_rules(self):
        self.assertEqual(lane_data_use.validate_note({**UNKNOWN, "data_use_label": "verified"}),
                         "data_use_label must be absent when data_use is unknown")
        entry = dict(GOOD)
        del entry["data_use_label"]
        for item in (entry, {**GOOD, "data_use_label": "checked"}):
            self.assertEqual(lane_data_use.validate_note(item),
                             "data_use_label must be one of: verified, reported "
                             "(required when data_use is not unknown)")

    def test_known_value_needs_a_source(self):
        entry = {**GOOD, "data_use_source": "none"}
        before = copy.deepcopy(entry)
        self.assertEqual(lane_data_use.validate_note(entry),
                         "data_use zero_retention or may_be_kept_or_trained needs the https:// "
                         "source it was read from")
        self.assertEqual(entry, before)

    def test_clean_line(self):
        text = "a\nb\x1bc\t d " + "ghp_" + "A" * 24 + " " + "x" * 300
        result = lane_data_use.clean_line(text)
        self.assertTrue(result.startswith("a b c d [redacted] x"))
        self.assertEqual(len(result), 200)
        self.assertEqual(lane_data_use.clean_line(result), result)
        self.assertEqual(lane_data_use.clean_line("  spaced  "), "spaced")


if __name__ == "__main__":
    unittest.main()
