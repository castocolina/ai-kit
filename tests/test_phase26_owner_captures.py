"""The Owner-decision answer lines staged for the owner must satisfy the gate's grammar."""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PHASES = ROOT / ".planning" / "milestones" / "v1.3-phases"
PHASE = next(PHASES.glob("26-session-self-resume*"), None)


@unittest.skipUnless(PHASE and (PHASE / "26-OWNER-CAPTURES.md").is_file(), "phase 26 dir absent")
class TestOwnerDecisionGrammar(unittest.TestCase):
    def test_staged_answer_lines_match_the_gate_regex(self):
        assert PHASE is not None
        checker = (PHASE / "skill-judge" / "check_verdicts.py").read_text(encoding="utf-8")
        gate = re.search(r're\.findall\(r"(\^Owner-decision:[^"]+)"', checker)
        self.assertIsNotNone(gate)
        assert gate is not None
        captures = (PHASE / "26-OWNER-CAPTURES.md").read_text(encoding="utf-8")
        lines = re.findall(r"`(Owner-decision: [^`]+accepts [^`]+)`", captures)
        self.assertEqual(len(lines), 3)
        for line in lines:
            filled = line.replace("<date>", "2026-10-30").replace(
                "<where the owner said it>", "owner chat"
            )
            self.assertRegex(filled, gate.group(1))


if __name__ == "__main__":
    unittest.main()
