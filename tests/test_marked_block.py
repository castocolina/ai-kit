import os
import sys
import unittest

_TOOLS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "tools"))
if _TOOLS_DIR not in sys.path:
    sys.path.insert(0, _TOOLS_DIR)
import marked_block

START = b"<!-- DEMO_START -->"
END = b"<!-- DEMO_END -->"


class TestFindBlock(unittest.TestCase):
    def test_find_block_returns_inner_span(self):
        data = b"x" + START + b"abc" + END + b"y"
        begin = data.index(START) + len(START)
        self.assertEqual(marked_block.find_block(data, START, END), (begin, begin + 3))

    def test_no_block_when_neither_marker(self):
        self.assertEqual(marked_block.find_block(b"text", START, END), "no_block")

    def test_one_marker_when_only_start_or_only_end(self):
        self.assertEqual(marked_block.find_block(START + b"\ntext", START, END), "one_marker")
        self.assertEqual(marked_block.find_block(b"text" + END, START, END), "one_marker")


if __name__ == "__main__":
    unittest.main()
