import os
import sys
import unittest

_TOOLS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "tools"))
if _TOOLS_DIR not in sys.path:
    sys.path.insert(0, _TOOLS_DIR)
import marked_block

START = b"<!-- CODEGRAPH_START -->"
END = b"<!-- CODEGRAPH_END -->"
OLD = b"indexing is the user's decision."
NEW = b"run codegraph init -y."


class TestReplaceInBlock(unittest.TestCase):
    def test_replaces_first_occurrence_inside_block_only(self):
        data = b"pre \xc3\xa9\r\n" + START + b"\r\n" + OLD + b"\r\n" + END + b"\r\n" + OLD + b"\n"
        out, reason = marked_block.replace_in_block(data, START, END, OLD, NEW)
        self.assertEqual(reason, "replaced")
        self.assertEqual(out, data.replace(OLD, NEW, 1))

    def test_no_block_when_neither_marker(self):
        self.assertEqual(
            marked_block.replace_in_block(OLD, START, END, OLD, NEW), (None, "no_block")
        )

    def test_one_marker_when_only_start(self):
        data = START + b"\n" + OLD
        self.assertEqual(
            marked_block.replace_in_block(data, START, END, OLD, NEW), (None, "one_marker")
        )

    def test_already_when_block_holds_new_and_not_old(self):
        data = START + b"\n" + NEW + b"\n" + END + OLD
        self.assertEqual(
            marked_block.replace_in_block(data, START, END, OLD, NEW), (None, "already")
        )

    def test_no_sentence_when_block_lacks_both(self):
        data = START + b"\nother\n" + END + OLD
        self.assertEqual(
            marked_block.replace_in_block(data, START, END, OLD, NEW), (None, "no_sentence")
        )

    def test_sentence_outside_block_is_not_searched(self):
        data = OLD + b"\n" + START + b"\nnothing\n" + END
        self.assertEqual(
            marked_block.replace_in_block(data, START, END, OLD, NEW), (None, "no_sentence")
        )

    def test_find_block_returns_inner_span(self):
        data = b"x" + START + b"abc" + END + b"y"
        begin = data.index(START) + len(START)
        self.assertEqual(marked_block.find_block(data, START, END), (begin, begin + 3))


if __name__ == "__main__":
    unittest.main()
