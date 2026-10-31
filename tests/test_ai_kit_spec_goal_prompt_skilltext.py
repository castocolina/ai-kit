"""Drift tests between the goal-prompt skill prose and its data (GPS-01..04; plan 27-10).

SKILL.md and references/ quote the matrix rows, the zero-test marker table, the CLI flags and the
golden excerpt. Each test fails when a quoted fact drifts from the code or fixture it cites. A
test that fails here is fixed in the prose, never by weakening the test.
"""

import os
import re
import subprocess
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SKILL = REPO / "skills" / "ai-kit-spec-goal-prompt"
SCRIPTS = SKILL / "scripts"
REFS = SKILL / "references"
SKILL_MD = SKILL / "SKILL.md"
GOLDEN = REPO / "tests" / "fixtures" / "goal_prompt" / "golden" / "opengsd-recommended.md"
sys.path.insert(0, str(SCRIPTS))
for shared in (REPO / "skills" / "_shared", REPO / "skills" / "ai-kit-project-rules-agents"):
    sys.path.insert(0, str(shared))

import goal_prompt
import gp_e2e
import gp_matrix

MACHINE_PATH = re.compile(r"(?<![\w.])/(?:var/home|home/[A-Za-z0-9_.-]+|Users/[A-Za-z0-9_.-]+)")
FENCE = re.compile(r"^```")


def _skill_docs() -> dict[str, str]:
    """Every Markdown file of the skill: SKILL.md, the references and the assets."""
    paths = [SKILL_MD, *sorted(REFS.glob("*.md")), *sorted((SKILL / "assets").glob("*.md"))]
    return {str(path.relative_to(REPO)): path.read_text(encoding="utf-8") for path in paths}


def _frontmatter(text: str) -> dict[str, str]:
    lines = text.split("\n")
    assert lines[0] == "---", "SKILL.md must open with frontmatter"
    end = lines.index("---", 1)
    fields: dict[str, str] = {}
    for line in lines[1:end]:
        key, _, value = line.partition(":")
        fields[key.strip()] = value.strip().strip('"')
    return fields


def _section(text: str, heading: str) -> list[str]:
    """Lines under `## heading` up to the next level-2 heading."""
    lines = text.split("\n")
    start = next(i for i, line in enumerate(lines) if line.startswith(f"## {heading}"))
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
    return lines[start + 1 : end]


def _fenced_blocks(text: str) -> list[list[str]]:
    blocks: list[list[str]] = []
    current: list[str] | None = None
    for line in text.split("\n"):
        if FENCE.match(line):
            if current is None:
                current = []
            else:
                blocks.append(current)
                current = None
        elif current is not None:
            current.append(line)
    return blocks


def _is_contiguous(needle: list[str], haystack: list[str]) -> bool:
    size = len(needle)
    return any(haystack[i : i + size] == needle for i in range(len(haystack) - size + 1))


def _excerpt_is_golden(excerpt: list[str], golden: str) -> bool:
    return _is_contiguous(excerpt, golden.split("\n"))


def _cli_flags() -> set[str]:
    """Every option string the real goal_prompt CLI accepts, for each subcommand."""
    parser = goal_prompt.build_parser()
    flags: set[str] = set()
    for action in parser._actions:
        for sub in (getattr(action, "choices", None) or {}).values():
            flags.update(sub._option_string_actions)
    return flags


class TestSkillText(unittest.TestCase):
    def test_skill_md_within_line_budget(self):
        lines = SKILL_MD.read_text(encoding="utf-8").count("\n")
        self.assertLessEqual(lines, 300)

    def test_frontmatter_has_exactly_name_and_description(self):
        fields = _frontmatter(SKILL_MD.read_text(encoding="utf-8"))
        self.assertEqual(set(fields), {"name", "description"})

    def test_name_equals_directory_name(self):
        fields = _frontmatter(SKILL_MD.read_text(encoding="utf-8"))
        self.assertEqual(fields["name"], SKILL.name)

    def test_description_opens_with_trigger_words(self):
        description = _frontmatter(SKILL_MD.read_text(encoding="utf-8"))["description"]
        head = description[:200]
        for word in ("/goal", "loop", "one-shot", "autonomous"):
            self.assertIn(word, head)

    def test_every_reference_is_linked_and_exists(self):
        text = SKILL_MD.read_text(encoding="utf-8")
        for ref in sorted(REFS.glob("*.md")):
            self.assertIn(f"references/{ref.name}", text, f"{ref.name} is orphaned")
        for target in set(re.findall(r"references/[\w.-]+\.md", text)):
            self.assertTrue((SKILL / target).is_file(), f"broken link {target}")

    def test_each_reference_states_purpose_and_load_condition(self):
        for ref in sorted(REFS.glob("*.md")):
            head = ref.read_text(encoding="utf-8").split("\n")[:5]
            self.assertTrue(any("Load when" in line for line in head), ref.name)

    def test_cli_flags_in_docs_exist_in_the_real_parser(self):
        flags = _cli_flags() | {"--help"}
        for name, text in _skill_docs().items():
            for line in text.split("\n"):
                if "goal_prompt.py" not in line:
                    continue
                for flag in re.findall(r"--[a-z][a-z-]*", line):
                    self.assertIn(flag, flags, f"{name} invents {flag}")

    def test_named_python_scripts_exist(self):
        names = set()
        for text in _skill_docs().values():
            names.update(re.findall(r"\b(?:goal_prompt|gp_\w+)\.py\b", text))
        self.assertIn("goal_prompt.py", names)
        for name in names:
            self.assertTrue((SCRIPTS / name).is_file(), name)

    def test_questions_section_asks_exactly_four_numbered_questions(self):
        lines = _section(SKILL_MD.read_text(encoding="utf-8"), "1.")
        numbered = [line for line in lines if re.match(r"^\d+\. ", line)]
        self.assertEqual([line.split(".")[0] for line in numbered], ["1", "2", "3", "4"])

    def test_never_list_has_at_least_eight_reasoned_bullets(self):
        bullets = [
            line
            for line in _section(SKILL_MD.read_text(encoding="utf-8"), "NEVER")
            if line.startswith("- ")
        ]
        self.assertGreaterEqual(len(bullets), 8)
        for bullet in bullets:
            self.assertIn(" — ", bullet, bullet)

    def test_mandatory_triggers_each_name_a_reference(self):
        lines = [
            line for line in SKILL_MD.read_text(encoding="utf-8").split("\n") if "MANDATORY" in line
        ]
        self.assertGreaterEqual(len(lines), 3)
        for line in lines:
            self.assertIn("references/", line)

    def test_do_not_load_names_the_template_within_five_lines(self):
        lines = _section(SKILL_MD.read_text(encoding="utf-8"), "Do NOT load")
        self.assertTrue(any("prompt-template.md" in line for line in lines[:5]))

    def test_unverified_section_lists_at_least_five_items(self):
        items = [
            line
            for line in _section(SKILL_MD.read_text(encoding="utf-8"), "Unverified")
            if line.startswith("- ")
        ]
        self.assertGreaterEqual(len(items), 5)

    def test_matrix_rows_documented_and_no_unknown_row_id(self):
        text = (REFS / "strategy-matrix.md").read_text(encoding="utf-8")
        known = {row["id"] for row in gp_matrix.RULES}
        for row_id in known:
            self.assertRegex(text, rf"(?m)^- {row_id}:", f"row {row_id} is not documented")
        mentioned = set(re.findall(r"\bM\d{2}[a-z]?\b", text))
        self.assertLessEqual(mentioned, known)

    def test_marker_table_rows_match_data_and_labels(self):
        lines = (REFS / "e2e-and-evidence.md").read_text(encoding="utf-8").split("\n")
        rows = {}
        for line in lines:
            cells = [cell.strip().strip("`") for cell in line.strip().strip("|").split("|")]
            if len(cells) >= 4 and line.startswith("|"):
                rows.setdefault(cells[0], cells[-1])
        for marker in gp_e2e.ZERO_TEST_MARKERS:
            label = rows.get(marker["runner"])
            self.assertIsNotNone(label, f"runner {marker['runner']} missing from the table")
            want = "verified" if marker["verified"] else "unverified"
            self.assertEqual(label, want, marker["runner"])

    def test_worked_example_excerpt_is_contiguous_golden_lines(self):
        text = (REFS / "worked-example.md").read_text(encoding="utf-8")
        golden = GOLDEN.read_text(encoding="utf-8")
        excerpts = [
            block
            for block in _fenced_blocks(text)
            if block and block[0].startswith("/gsd-autonomous")
        ]
        self.assertEqual(len(excerpts), 1)
        self.assertLessEqual(len(excerpts[0]), 25)
        self.assertTrue(_excerpt_is_golden(excerpts[0], golden))

    def test_excerpt_check_fails_on_a_mutated_copy(self):
        golden = GOLDEN.read_text(encoding="utf-8")
        excerpt = golden.split("\n")[9:20]
        self.assertTrue(_excerpt_is_golden(excerpt, golden))
        mutated = list(excerpt)
        mutated[3] = mutated[3] + " (edited)"
        self.assertFalse(_excerpt_is_golden(mutated, golden))

    def test_no_machine_path_and_no_skip_flag_in_skill_text(self):
        for name, text in _skill_docs().items():
            self.assertIsNone(MACHINE_PATH.search(text), f"machine path in {name}")
            self.assertNotIn("--no" + "-verify", text, name)

    def test_machine_path_guard_catches_a_planted_path(self):
        planted = os.sep + os.path.join("home", "fixture-user", "repo")  # built at run time
        self.assertIsNotNone(MACHINE_PATH.search(f"see {planted}"))
        self.assertIsNone(MACHINE_PATH.search("see .planning/goals/file.md"))

    def test_skill_dir_has_no_tracked_pycache(self):
        try:
            done = subprocess.run(
                ["git", "ls-files", "--", str(SKILL.relative_to(REPO))],
                cwd=REPO,
                capture_output=True,
                text=True,
                check=False,
                timeout=30,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            self.skipTest(f"git unavailable: {exc}")
        if done.returncode != 0:
            self.skipTest("not a git checkout")
        self.assertNotIn("__pycache__", done.stdout)


if __name__ == "__main__":
    unittest.main()
