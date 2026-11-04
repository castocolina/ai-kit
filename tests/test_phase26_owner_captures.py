"""The Owner-decision answer lines staged for the owner must satisfy the gate's grammar.

Reads a frozen copy of the phase-26 checker and captures (tests/fixtures/archived/26), never
the live project tree (SPEC R9).
"""

import re
import unittest
from pathlib import Path

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "archived" / "26"


class TestOwnerDecisionGrammar(unittest.TestCase):
    def test_staged_answer_lines_match_the_gate_regex(self):
        checker = (FIXTURE / "skill-judge" / "check_verdicts.py.txt").read_text(encoding="utf-8")
        gate = re.search(r're\.findall\(r"(\^Owner-decision:[^"]+)"', checker)
        self.assertIsNotNone(gate)
        assert gate is not None
        captures = (FIXTURE / "26-OWNER-CAPTURES.md").read_text(encoding="utf-8")
        lines = re.findall(r"`(Owner-decision: [^`]+accepts [^`]+)`", captures)
        self.assertEqual(len(lines), 3)
        for line in lines:
            filled = line.replace("<date>", "2026-10-30").replace(
                "<where the owner said it>", "owner chat"
            )
            self.assertRegex(filled, gate.group(1))


if __name__ == "__main__":
    unittest.main()
