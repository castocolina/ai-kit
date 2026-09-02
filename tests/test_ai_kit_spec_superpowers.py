import os
import sys
import tempfile
import unittest

# Bootstraps every package root this plan's tests need. ai_kit_spec_superpowers (this plan) and
# ai_kit_spec (Plan 1, Foundation) both live outside this file's own directory, on no search path
# by default. skills/ai-kit-spec-execute is ALSO added here (not just
# skills/ai-kit-spec-execute-superpowers) because Task 5's detect_framework module lives there --
# this is the ONE bootstrap block for the whole file, at the top; it is never repeated.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills", "ai-kit-spec-review"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills",
                                 "ai-kit-spec-execute-superpowers"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills", "ai-kit-spec-execute"))

from ai_kit_spec_superpowers import task_classification


class TestClassifyTask(unittest.TestCase):
    def test_classifies_frontend_from_file_extensions(self):
        task = "### Task 3: Button\n**Files:**\n- Create: `src/components/Button.tsx`\n"
        self.assertEqual(task_classification.classify_task(task), "frontend")

    def test_classifies_backend_from_file_paths(self):
        task = "### Task 4: API\n**Files:**\n- Create: `server/api/handlers.py`\n"
        self.assertEqual(task_classification.classify_task(task), "backend")

    def test_classifies_mixed_when_both_signal_types_present(self):
        task = ("### Task 5: Full-stack widget\n**Files:**\n"
                "- Create: `src/components/Widget.tsx`\n- Create: `server/api/widget.py`\n")
        self.assertEqual(task_classification.classify_task(task), "mixed")

    def test_returns_none_with_no_confident_signal(self):
        task = "### Task 6: Docs\n**Files:**\n- Modify: `README.md`\n"
        self.assertIsNone(task_classification.classify_task(task))


class TestExtractTouchedPaths(unittest.TestCase):
    def test_extracts_every_backtick_path_in_order(self):
        task = "### Task 1\n**Files:**\n- Create: `a.py`\n- Modify: `b.py`\n"
        self.assertEqual(task_classification.extract_touched_paths(task), ["a.py", "b.py"])

    def test_preserves_writing_plans_line_qualified_paths_verbatim(self):
        # CRITICAL finding: writing-plans' own task template routinely emits a `Modify:` target
        # as a line-range-qualified path (`existing.py:123-145`, per the skill's own Task
        # Structure example), not a bare filesystem path. extract_touched_paths must return this
        # EXACT string, unmodified -- it is the SAME string estimate_required_context uses as a
        # files_touched_sizes dict key, and Task 2's derive_files_touched_sizes (the one place
        # that ever touches the filesystem) is where the line-range suffix gets stripped for
        # stat'ing, not here. Normalizing it in two places would let the two drift.
        task = "### Task 1\n**Files:**\n- Modify: `existing.py:123-145`\n"
        self.assertEqual(task_classification.extract_touched_paths(task),
                          ["existing.py:123-145"])


class TestEstimateRequiredContext(unittest.TestCase):
    def test_sums_file_sizes_plus_overhead(self):
        task = "### Task 1\n**Files:**\n- Modify: `a.py`\n- Modify: `b.py`\n"
        sizes = {"a.py": 4000, "b.py": 8000}
        result = task_classification.estimate_required_context(task, sizes)
        self.assertEqual(result, (4000 + 8000) // 4 + task_classification.OVERHEAD_TOKENS)

    def test_missing_size_data_counts_as_zero_not_an_error(self):
        task = "### Task 1\n**Files:**\n- Create: `new.py`\n"
        result = task_classification.estimate_required_context(task, {})
        self.assertEqual(result, task_classification.OVERHEAD_TOKENS)
