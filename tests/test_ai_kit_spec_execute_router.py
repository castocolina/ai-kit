"""The execute router hands GSD plans to /gsd-execute-phase and names no GSD adapter."""

import unittest
from pathlib import Path

# Built from parts so the removed adapter's full name stays out of the tree (plan 31-01 R1 search).
REMOVED_ADAPTER = "ai-kit-spec-execute" + "-gsd"
ROUTER_SKILL = (
    Path(__file__).resolve().parent.parent / "skills" / "ai-kit-spec-execute" / "SKILL.md"
)


def gsd_bullet_problems(text):
    """Problems with the `"gsd"` bullet of ## Routing Procedure (empty means clean)."""
    in_section = False
    bullet = None
    for line in text.splitlines():
        if line.startswith("## "):
            in_section = line.strip() == "## Routing Procedure"
            continue
        if in_section and line.lstrip().startswith('- `"gsd"`'):
            bullet = line
            break
    if bullet is None:
        return ['no `"gsd"` bullet under ## Routing Procedure']
    problems = []
    if "/gsd-execute-phase" not in bullet:
        problems.append("the gsd bullet does not name /gsd-execute-phase")
    if REMOVED_ADAPTER in bullet:
        problems.append("the gsd bullet names the removed adapter")
    return problems


class TestExecuteRouterGsdBranch(unittest.TestCase):
    def setUp(self):
        self.text = ROUTER_SKILL.read_text(encoding="utf-8")

    def test_gsd_bullet_names_gsd_execute_phase(self):
        self.assertEqual(gsd_bullet_problems(self.text), [])

    def test_description_names_gsd_execute_phase_and_no_gsd_adapter(self):
        description = next(
            line for line in self.text.splitlines() if line.startswith("description:")
        )
        self.assertIn("/gsd-execute-phase", description)
        self.assertIn("ai-kit-spec-execute-superpowers", description)
        self.assertNotIn(REMOVED_ADAPTER, description)

    def test_no_line_names_the_removed_adapter(self):
        offending = [line for line in self.text.splitlines() if REMOVED_ADAPTER in line]
        self.assertEqual(offending, [])

    def test_helper_is_non_vacuous(self):
        synthetic = (
            "## Routing Procedure\n\n"
            f'   - `"gsd"` → delegate to `{REMOVED_ADAPTER}`.\n'
        )
        problems = gsd_bullet_problems(synthetic)
        self.assertTrue(problems, "a bullet naming the removed adapter must be a problem")
        self.assertTrue(any("removed adapter" in problem for problem in problems))


if __name__ == "__main__":
    unittest.main()
