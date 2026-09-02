import os
import sys
import unittest

# Bootstraps ALL package roots this plan's tests need -- ai_kit_spec_superpowers and
# ai_kit_spec (Plan 1, Foundation) both live outside this file's own directory, on no search
# path by default. skills/ai-kit-spec-execute is ALSO added here because Task 5's detect_framework
# module lives there and this is the ONE bootstrap block for the whole file.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills",
                                 "ai-kit-spec-execute-superpowers"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills",
                                 "ai-kit-spec-execute"))

import detect_framework as router_detect_framework


class TestDetectFrameworkSuperpowers(unittest.TestCase):
    def test_detects_superpowers_from_plans_directory(self):
        def isdir_fn(path):
            return path == os.path.join("/repo", "docs", "superpowers", "plans")

        result = router_detect_framework.detect_framework(
            "/repo", isfile_fn=lambda p: False, isdir_fn=isdir_fn)
        self.assertEqual(result, "superpowers")

    def test_gsd_marker_wins_over_superpowers_marker_when_both_present_and_no_stronger_signal(self):
        result = router_detect_framework.detect_framework(
            "/repo",
            isfile_fn=lambda p: p == os.path.join("/repo", ".planning", "PROJECT.md"),
            isdir_fn=lambda p: p == os.path.join("/repo", "docs", "superpowers", "plans"))
        self.assertEqual(result, "gsd")

    def test_returns_unknown_when_neither_marker_present(self):
        result = router_detect_framework.detect_framework(
            "/repo", isfile_fn=lambda p: False, isdir_fn=lambda p: False)
        self.assertEqual(result, "unknown")

    def test_document_path_overrides_gsd_marker_when_both_markers_present(self):
        # CRITICAL finding (recurrence guard): a repo with BOTH markers present must still route a
        # user-supplied superpowers plan path to superpowers -- markers are supporting evidence
        # only, never the primary signal once an explicit document path is available.
        result = router_detect_framework.detect_framework(
            "/repo", document_path="/repo/docs/superpowers/plans/2026-08-29-widget.md",
            isfile_fn=lambda p: p == os.path.join("/repo", ".planning", "PROJECT.md"),
            isdir_fn=lambda p: p == os.path.join("/repo", "docs", "superpowers", "plans"))
        self.assertEqual(result, "superpowers")

    def test_document_path_under_planning_resolves_gsd_even_without_markers(self):
        result = router_detect_framework.detect_framework(
            "/repo", document_path="/repo/.planning/phases/02-widget/02-01-PLAN.md",
            isfile_fn=lambda p: False, isdir_fn=lambda p: False)
        self.assertEqual(result, "gsd")

    def test_conversation_signal_wins_over_a_contradicting_document_path_and_markers(self):
        # CRITICAL finding: conversation signal is the strongest evidence -- the user just invoked
        # writing-plans in this very conversation, which outranks even an explicit document path
        # that happens to look GSD-shaped (e.g. copied under a .planning/ scratch directory).
        result = router_detect_framework.detect_framework(
            "/repo", document_path="/repo/.planning/scratch/notes.md",
            conversation_signal="superpowers",
            isfile_fn=lambda p: p == os.path.join("/repo", ".planning", "PROJECT.md"),
            isdir_fn=lambda p: False)
        self.assertEqual(result, "superpowers")
