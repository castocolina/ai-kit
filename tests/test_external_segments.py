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


class TestDiscover(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.addCleanup(lambda: __import__("shutil").rmtree(self.dir, ignore_errors=True))
        self.env = {"XDG_CACHE_HOME": os.path.join(self.dir, "cache")}

    def test_executable_with_header_is_discovered(self):
        write_script(self.dir, "aws.sh",
                     "#!/bin/sh\n# ai-kit-segment: line=2 after=clock id=aws ttl=30\necho hi\n")
        specs = sl.discover_external(self.dir, default_ttl=10, env=self.env)
        self.assertEqual(len(specs), 1)
        s = specs[0]
        self.assertEqual(s.id, "aws")
        self.assertEqual(s.position, ("after", "clock"))
        self.assertEqual(s.line, 2)
        self.assertEqual(s.ttl, 30)
        self.assertEqual(s.timeout, 2.0)
        self.assertTrue(s.cache_path.endswith(os.path.join("ai-kit", "segments", "aws")))

    def test_no_header_uses_defaults_and_stem_id(self):
        write_script(self.dir, "clockx", "#!/bin/sh\necho hi\n")
        specs = sl.discover_external(self.dir, default_ttl=7, env=self.env)
        self.assertEqual(specs[0].id, "clockx")
        self.assertEqual(specs[0].position, ("end", ""))
        self.assertEqual(specs[0].line, 0)        # 0 => "last row", resolved at placement
        self.assertEqual(specs[0].ttl, 7)

    def test_non_executable_skipped(self):
        write_script(self.dir, "noexec", "#!/bin/sh\necho hi\n", executable=False)
        self.assertEqual(sl.discover_external(self.dir, 10, self.env), [])

    def test_sorted_by_filename_then_id(self):
        write_script(self.dir, "b.sh", "#!/bin/sh\n# ai-kit-segment: id=zeta\necho\n")
        write_script(self.dir, "a.sh", "#!/bin/sh\n# ai-kit-segment: id=omega\necho\n")
        ids = [s.id for s in sl.discover_external(self.dir, 10, self.env)]
        self.assertEqual(ids, ["omega", "zeta"])   # a.sh before b.sh

    def test_missing_dir_returns_empty(self):
        self.assertEqual(sl.discover_external("/no/such/dir", 10, self.env), [])


class TestSanitize(unittest.TestCase):
    def test_first_non_empty_line(self):
        self.assertEqual(sl._sanitize_external("\n\n  hello \n second\n", 40), "  hello")

    def test_keeps_sgr_strips_other_csi(self):
        # \033[33m kept (SGR), \033[2J (clear) and cursor move \033[1A stripped
        out = sl._sanitize_external("\033[33mhi\033[0m\033[2J\033[1A", 40)
        self.assertEqual(out, "\033[33mhi\033[0m")

    def test_strips_osc_and_control_chars(self):
        out = sl._sanitize_external("\033]0;title\007ab\tc", 40)
        self.assertEqual(out, "abc")

    def test_truncates_to_avail_and_resets(self):
        out = sl._sanitize_external("\033[33mabcdef\033[0m", 3)
        self.assertEqual(sl.visible_width(out), 3)
        self.assertTrue(out.endswith(sl.RESET))

    def test_empty_after_sanitize_returns_none(self):
        self.assertIsNone(sl._sanitize_external("\033[2J\n", 40))
        self.assertIsNone(sl._sanitize_external("   \n", 40))

    def test_avail_zero_returns_none(self):
        self.assertIsNone(sl._sanitize_external("hi", 0))


if __name__ == "__main__":
    unittest.main()
