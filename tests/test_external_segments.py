import importlib.util
import json
import os
import stat
import sys
import tempfile
import time
import unittest

_HERE = os.path.dirname(__file__)
_MODULE_PATH = os.path.join(_HERE, "..", "tools", "status-line.py")


def load_module():
    spec = importlib.util.spec_from_file_location("status_line", _MODULE_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


sl = load_module()


def write_script(directory, name, body, executable=True):
    """Write a provider script and (by default) chmod +x it. Returns its path."""
    path = os.path.join(directory, name)
    with open(path, "w", encoding="utf-8") as f:
        f.write(body)
    if executable:
        os.chmod(path, os.stat(path).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return path


class TestParseHeader(unittest.TestCase):
    def test_full_header(self):
        lines = ["#!/bin/sh\n",
                 "# ai-kit-segment: line=2 after=clock id=aws timeout=3 ttl=30\n",
                 "echo hi\n"]
        fields = sl.parse_segment_header(lines)
        self.assertEqual(fields["position"], ("after", "clock"))
        self.assertEqual(fields["line"], "2")
        self.assertEqual(fields["id"], "aws")
        self.assertEqual(fields["timeout"], "3")
        self.assertEqual(fields["ttl"], "30")

    def test_bare_start_end(self):
        self.assertEqual(sl.parse_segment_header(["# ai-kit-segment: start\n"])["position"],
                         ("start", ""))
        self.assertEqual(sl.parse_segment_header(["# ai-kit-segment: end\n"])["position"],
                         ("end", ""))

    def test_no_header_returns_none(self):
        self.assertIsNone(sl.parse_segment_header(["#!/bin/sh\n", "echo hi\n"]))

    def test_header_present_but_empty_fields(self):
        self.assertEqual(sl.parse_segment_header(["# ai-kit-segment:\n"]), {})


if __name__ == "__main__":
    unittest.main()
