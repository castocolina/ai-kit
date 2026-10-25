"""Text pins for the subprocess failure ladder (QTA-03, D-23).

The runner template and its self-test are the source of truth. This module pins the
canonical reference and the execute skills that point at it: no repeated or fixed-interval
wording, and every CronCreate line is the ruled one-shot re-invoke.
"""

import pathlib
import re
import unittest

REPO = pathlib.Path(__file__).resolve().parent.parent
REFERENCE = REPO / "skills/ai-kit-cross-ai/references/subprocess-quota-policy.md"
GSD_SKILL = REPO / "skills/ai-kit-spec-execute-gsd/SKILL.md"
REVIEW_SKILL = REPO / "skills/ai-kit-spec-review/SKILL.md"
DISPATCH_REF = REPO / "skills/ai-kit-spec-review/references/cross-ai-dispatch.md"
SUPER_DIR = REPO / "skills/ai-kit-spec-execute-superpowers"
SUPER_SKILL = SUPER_DIR / "SKILL.md"
SUPER_REFS = (
    SUPER_DIR / "references/state-management.md",
    SUPER_DIR / "references/escalation.md",
    SUPER_DIR / "references/design-notes.md",
)
DISPATCH = SUPER_DIR / "ai_kit_spec_superpowers/dispatch_injection.py"
CLASSIFIER = REPO / "skills/ai-kit-spec-review/ai_kit_spec/error_classifier.py"
CURATED_SKILL = REPO / "skills/ai-kit-gsd-curated-config/SKILL.md"
RUNNER_REF = REPO / "skills/ai-kit-gsd-curated-config/references/runner.md"
README = REPO / "README.md"

FALLBACK_SENTENCE = "next runner in the prefer order"
OLD_VERSION = re.compile(r"template[- ]6")

STOP_SENTENCE = "Never re-resolve to another candidate after a failed dispatch."
OLD_REDISPATCH = "Retry Step 3 with the new injection"

WAKE_RE = re.compile(r"\bhourly\b|every hour|recurring", re.IGNORECASE)
POINTER_HEADING = "## Pointer for instruction files"


def wake_lines(text):
    """Lines that schedule a repeated or fixed-interval wake.

    A line that also carries both `one-shot` and `retry_after_s` is the ruled single
    re-invoke, so it is not a wake line.
    """
    found = []
    for line in text.splitlines():
        if not WAKE_RE.search(line):
            continue
        if "one-shot" in line and "retry_after_s" in line:
            continue
        found.append(line)
    return found


def cron_lines(text):
    """Lines that name a CronCreate job."""
    return [line for line in text.splitlines() if "CronCreate" in line]


def pointer_lines(text):
    """Non-empty lines of the first fenced block after the pointer heading."""
    heading = text.find(POINTER_HEADING)
    if heading < 0:
        return []
    fence = text.find("```", heading)
    if fence < 0:
        return []
    start = text.find("\n", fence)
    end = text.find("```", start + 1)
    if start < 0 or end < 0:
        return []
    return [line for line in text[start + 1:end].splitlines() if line.strip()]


class PolicyReference(unittest.TestCase):
    def test_reference_exists_with_a_short_pointer(self):
        text = REFERENCE.read_text(encoding="utf-8")
        lines = pointer_lines(text)
        self.assertIn(len(lines), (3, 4))
        self.assertTrue(all(len(line) <= 100 for line in lines))
        self.assertTrue(any(".planning/scripts/cross-ai.mjs" in line for line in lines))

    def test_reference_has_no_wake_line(self):
        self.assertEqual(wake_lines(REFERENCE.read_text(encoding="utf-8")), [])


class ReviewSkill(unittest.TestCase):
    def test_skill_points_to_cross_ai_and_pins_hard_tier(self):
        text = REVIEW_SKILL.read_text(encoding="utf-8")
        self.assertIn("../ai-kit-cross-ai/SKILL.md", text)
        self.assertEqual(wake_lines(text), [])
        for token in ("retry_after_s", "one-shot", "stopped=hard-waits"):
            self.assertIn(token, text)
        self.assertRegex(text, r"Never switch harness, provider or model")

    def test_dispatch_reference_names_transient(self):
        self.assertIn("transient", DISPATCH_REF.read_text(encoding="utf-8"))


class GsdExecuteSkill(unittest.TestCase):
    def test_skill_points_to_cross_ai_and_schedules_only_the_one_shot(self):
        text = GSD_SKILL.read_text(encoding="utf-8")
        self.assertIn("../ai-kit-cross-ai/SKILL.md", text)
        self.assertEqual(wake_lines(text), [])
        hits = cron_lines(text)
        self.assertTrue(hits)
        for line in hits:
            self.assertIn("one-shot", line)
            self.assertIn("retry_after_s", line)


class SuperpowersExecuteSkill(unittest.TestCase):
    def test_skill_points_to_cross_ai_and_pins_hard_tier(self):
        text = SUPER_SKILL.read_text(encoding="utf-8")
        tokens = ("ai-kit-cross-ai/SKILL.md", "retry_after_s", "one-shot", "stopped=hard-waits")
        for token in tokens:
            self.assertIn(token, text)
        self.assertRegex(text, r"Never switch harness, provider or model")
        self.assertIn(STOP_SENTENCE, text)

    def test_skill_and_references_have_no_wake_line(self):
        texts = [SUPER_SKILL.read_text(encoding="utf-8")]
        texts += [path.read_text(encoding="utf-8") for path in SUPER_REFS]
        for text in texts:
            self.assertEqual(wake_lines(text), [])

    def test_skill_links_the_reference_and_stops_instead_of_re_resolving(self):
        text = SUPER_SKILL.read_text(encoding="utf-8")
        self.assertIn("../ai-kit-cross-ai/SKILL.md", text)
        self.assertIn(STOP_SENTENCE, text)
        self.assertNotIn(OLD_REDISPATCH, text)

    def test_every_cron_line_is_the_ruled_one_shot(self):
        for line in cron_lines(SUPER_SKILL.read_text(encoding="utf-8")):
            self.assertIn("one-shot", line)
            self.assertIn("retry_after_s", line)


class CuratedConfigDocs(unittest.TestCase):
    def test_curated_files_and_readme_drop_the_fallback_and_the_old_version(self):
        for path in (CURATED_SKILL, RUNNER_REF, README):
            text = path.read_text(encoding="utf-8")
            self.assertNotIn(FALLBACK_SENTENCE, text)
            self.assertIsNone(OLD_VERSION.search(text))

    def test_curated_skill_links_the_policy_and_readme_names_the_ladder(self):
        self.assertIn("subprocess-quota-policy.md", CURATED_SKILL.read_text(encoding="utf-8"))
        self.assertIn("no automatic fallback", README.read_text(encoding="utf-8"))
        self.assertIn("## Failure ladder", RUNNER_REF.read_text(encoding="utf-8"))


class PythonMessages(unittest.TestCase):
    def test_dispatch_and_classifier_have_no_wake_line(self):
        for path in (DISPATCH, CLASSIFIER):
            self.assertEqual(wake_lines(path.read_text(encoding="utf-8")), [])


class ExitTableScan(unittest.TestCase):
    EXIT_CODES = {"69", "75", "124", "127"}

    @classmethod
    def rows(cls, text):
        found = []
        for line in text.splitlines():
            cells = line.strip().strip("|").split("|")
            if len(cells) < 2:
                continue
            first = cells[0].strip().replace("`", "")
            if first in cls.EXIT_CODES:
                found.append(line)
        return found

    def test_project_markdown_has_no_runner_exit_code_tables(self):
        paths = [*list((REPO / "skills").rglob("*.md")), README]
        paths = [p for p in paths if "skills/ai-kit-cross-ai/" not in p.as_posix()]
        hits = [(p.relative_to(REPO), row) for p in paths
                for row in self.rows(p.read_text(encoding="utf-8"))]
        self.assertEqual(hits, [])

    def test_exact_first_cell_match_only(self):
        self.assertEqual(len(self.rows("| `75` | retry |")), 1)
        self.assertEqual(self.rows("| any other, including `69` and `75` | real_error |"), [])


class NonVacuity(unittest.TestCase):
    def test_wake_lines_flags_a_seeded_interval_and_passes_a_stop(self):
        self.assertEqual(len(wake_lines("Schedule CronCreate: hourly interval")), 1)
        self.assertEqual(wake_lines("stop and report"), [])

    def test_pointer_lines_returns_every_line_of_a_six_line_block(self):
        body = "\n".join(f"line {n}" for n in range(1, 7))
        synthetic = f"{POINTER_HEADING}\n```\n{body}\n```\n"
        self.assertEqual(len(pointer_lines(synthetic)), 6)


if __name__ == "__main__":
    unittest.main()
