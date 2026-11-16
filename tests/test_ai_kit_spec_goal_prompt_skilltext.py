"""Drift tests between the goal-prompt skill prose and its data (GPS-01..04; plan 27-10).

SKILL.md and references/ quote the matrix rows, the zero-test marker table, the CLI flags and the
golden excerpt. Each test fails when a quoted fact drifts from the code or fixture it cites. A
test that fails here is fixed in the prose, never by weakening the test.
"""

import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SKILL = REPO / "skills" / "ai-kit-spec-goal-prompt"
SCRIPTS = SKILL / "scripts"
REFS = SKILL / "references"
SKILL_MD = SKILL / "SKILL.md"
GOLDEN = REPO / "tests" / "fixtures" / "goal_prompt" / "golden" / "opengsd-recommended.md"
GOLDEN_POINTER = REPO / "tests" / "fixtures" / "goal_prompt" / "golden" / "opengsd-goal-pointer.md"
sys.path.insert(0, str(SCRIPTS))
for shared in (REPO / "skills" / "_shared", REPO / "skills" / "ai-kit-project-rules-agents"):
    sys.path.insert(0, str(shared))

import goal_prompt
import gp_common
import gp_e2e
import gp_matrix
import gp_render
import gp_sections

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

    def test_pointer_form_prose_matches_the_code_constants(self):
        skill = SKILL_MD.read_text(encoding="utf-8")
        matrix = (REFS / "strategy-matrix.md").read_text(encoding="utf-8")
        threshold = f"{gp_render.GOAL_POINTER_THRESHOLD:,}"
        for text in (skill, matrix):
            self.assertIn(threshold, text)
            self.assertIn(gp_render.FULL_GOAL_HEADING, text)
            self.assertIn("goal_form", text)
        for style in gp_render.GOAL_STYLES:
            self.assertIn(f"`{style}`", skill)
            self.assertIn(f"`{style}`", matrix)
        self.assertIn("GOAL_POINTER_THRESHOLD", matrix)
        self.assertIn(f"{gp_render.GOAL_BUDGET:,}", skill)

    def test_pointer_form_is_labelled_unverified_in_skill_and_matrix(self):
        skill = SKILL_MD.read_text(encoding="utf-8")
        unverified = "\n".join(_section(skill, "Unverified"))
        self.assertIn("/goal read document", unverified)
        matrix = "\n".join(_section((REFS / "strategy-matrix.md").read_text(encoding="utf-8"),
                                    "Unverified"))
        self.assertIn("/goal read document", matrix)
        self.assertIn("unverified", gp_render.POINTER_WARNING)

    def test_worked_example_pointer_line_is_a_golden_line(self):
        text = (REFS / "worked-example.md").read_text(encoding="utf-8")
        golden = GOLDEN_POINTER.read_text(encoding="utf-8")
        excerpts = [b for b in _fenced_blocks(text) if b and b[0].startswith("/goal read")]
        self.assertEqual(len(excerpts), 1)
        self.assertTrue(_excerpt_is_golden(excerpts[0], golden))

    def test_sources_of_closed_checks_live_in_the_evidence_reference(self):
        evidence = (REFS / "evidence.md").read_text(encoding="utf-8")
        for needle in ("2.1.314", "4000 UTF-16 units", "ARGUMENTS", "ASCII `--`",
                       "thread_goal_updated", "tool_search", "1.17.0", "1.16.0", "3.12.12"):
            self.assertIn(needle, evidence)

    def test_skill_md_main_flow_pins_no_version_or_observation_date(self):
        skill = SKILL_MD.read_text(encoding="utf-8")
        self.assertIsNone(re.search(r"\d+\.\d+\.\d+|20\d\d-\d\d-\d\d", skill))
        section = "\n".join(_section(skill, "Evidence and limits"))
        self.assertIn("references/evidence.md", section)
        self.assertIn("Load", section)

    def test_never_edit_bullet_matches_the_unique_path_behaviour(self):
        bullets = [b for b in _section(SKILL_MD.read_text(encoding="utf-8"), "NEVER")
                   if b.startswith("- Never edit the rendered file by hand")]
        self.assertEqual(len(bullets), 1)
        self.assertNotIn("overwrite it", bullets[0])
        self.assertIn("render never overwrites", bullets[0])
        self.assertIn("new `-2` file", bullets[0])
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "a.md").write_text("x", encoding="utf-8")
            self.assertTrue(gp_common.unique_path(tmp, "a.md").endswith("a-2.md"))
            with self.assertRaises(gp_common.GuardError):
                gp_render.write_atomic(tmp, "a.md", "y")

    def test_tmp_prose_matches_what_render_does_without_an_ignored_tmp(self):
        skill = SKILL_MD.read_text(encoding="utf-8")
        self.assertIn("mkdir -p tmp", skill)
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run(["git", "init", "-q", tmp], check=True, timeout=30)
            with self.assertRaises(gp_common.GuardError) as caught:
                gp_render.choose_path(tmp, "none", "2026-01-02", "x", None)
            self.assertFalse(Path(tmp, "tmp").exists())
            Path(tmp, ".gitignore").write_text("tmp/\n", encoding="utf-8")
            path = gp_render.choose_path(tmp, "none", "2026-01-02", "x", None)
            self.assertEqual(path, "tmp/2026-01-02-x.md")
        self.assertIn(str(caught.exception), skill)

    def test_full_objective_prose_matches_the_code(self):
        skill = SKILL_MD.read_text(encoding="utf-8")
        matrix = (REFS / "strategy-matrix.md").read_text(encoding="utf-8")
        shown = gp_sections.OBJECTIVE_POINTER.format(path="<path> ").strip()
        for text in (skill, matrix):
            self.assertIn(gp_render.FULL_OBJECTIVE_HEADING, text)
            self.assertIn("full_objective", text)
        self.assertIn(shown, matrix)
        self.assertIn(f"{gp_sections.LINE_CAP}-character", matrix)

    def test_skill_md_documents_every_owner_field(self):
        flat = " ".join(SKILL_MD.read_text(encoding="utf-8").split())
        for name in goal_prompt.OWNER_FIELDS:
            self.assertIn(f"`{name}`", flat)
        self.assertIn(f"never below {gp_sections.TURN_FLOOR}", flat)

    def test_the_validator_checks_every_owner_field(self):
        """OWNER_FIELDS and the validator name the same fields: a wrong type in each is refused
        by that field's name, so a field cannot be validated without being documented."""
        for name in goal_prompt.OWNER_FIELDS:
            with self.subTest(field=name), self.assertRaisesRegex(
                    goal_prompt.UsageError, f"answers field {name} must be"):
                goal_prompt._check_owner_fields({name: {"not": "valid"}})

    def test_caller_supplied_answers_replace_the_four_questions(self):
        flat = " ".join(SKILL_MD.read_text(encoding="utf-8").split())
        self.assertIn("its answers replace the four questions", flat)

    def test_owner_fields_come_from_stated_sources_never_a_fifth_question(self):
        flat = " ".join(SKILL_MD.read_text(encoding="utf-8").split())
        self.assertIn("Fill an owner field only when a source states it", flat)
        self.assertIn("never ask a fifth question for one", flat)

    def test_cross_ai_line_cap_limit_names_the_guard_message(self):
        flat = " ".join(SKILL_MD.read_text(encoding="utf-8").split())
        self.assertIn(f"more than {gp_render.RULE_CAP} rule lines", flat)
        self.assertIn("every owner field set", flat)

    def test_wrapping_is_documented(self):
        flat = " ".join(SKILL_MD.read_text(encoding="utf-8").split())
        self.assertIn("three-space continuation lines", flat)

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
