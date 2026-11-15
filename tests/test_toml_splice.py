"""Tests for ai_kit_spec.toml_splice: the comment-keeping TOML writer (D-08) and its atomic publish
(SPEC R2, R3, R9). Every test works in a temporary directory, never a real config."""
import difflib
import os
import re
import shutil
import stat
import sys
import tempfile
import tomllib
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills", "ai-kit-spec-review"))

from ai_kit_spec import cache, toml_splice
from ai_kit_spec.toml_splice import SpliceError

BASE = """\
# ai-kit config header comment
[runner.retry]
base_s   =   1   # note
factor = 2

# unknown table kept
[foo.bar]
keep = "yes"

# review lane
[[lanes.review]]
key = "a"
model = "m1"
"""


def _changed(before, after):
    """Removed and added lines of a line diff (ndiff guide lines start with '?', not counted)."""
    diff = list(difflib.ndiff(before.splitlines(keepends=True), after.splitlines(keepends=True)))
    removed = [line for line in diff if line.startswith("- ")]
    added = [line for line in diff if line.startswith("+ ")]
    return removed, added


class TestSetTable(unittest.TestCase):
    def test_changed_key_rewrites_only_its_own_line(self):
        out = toml_splice.set_table(BASE, ("runner", "retry"), {"base_s": 2})
        removed, added = _changed(BASE, out)
        self.assertEqual(len(removed), 1)
        self.assertEqual(len(added), 1)
        self.assertIn("base_s   =   1   # note", removed[0])
        self.assertEqual(added[0], "+ base_s = 2\n")
        parsed = tomllib.loads(out)
        self.assertEqual(parsed["runner"]["retry"], {"base_s": 2, "factor": 2})
        self.assertEqual(parsed["foo"], {"bar": {"keep": "yes"}})
        self.assertIn("# ai-kit config header comment\n", out)
        self.assertIn("# review lane\n[[lanes.review]]\n", out)

    def test_equal_values_return_the_input_unchanged(self):
        out = toml_splice.set_table(BASE, ("runner", "retry"), {"base_s": 1})
        self.assertIs(out, BASE)
        self.assertEqual(out, BASE)

    def test_empty_text_gets_only_the_table(self):
        out = toml_splice.set_table("", ("runner", "retry"), {"base_s": 2})
        self.assertEqual(out, "[runner.retry]\nbase_s = 2\n")

    def test_added_key_follows_the_last_key_and_removed_multiline_array_goes(self):
        text = '[runner.retry]\nbase_s = 1\nladder = [\n  1,\n  2,\n  3,\n]\nfactor = 2\n'
        out = toml_splice.set_table(
            text, ("runner", "retry"), {"base_s": 1, "max": 5}, remove=("ladder",))
        self.assertEqual(out, "[runner.retry]\nbase_s = 1\nfactor = 2\nmax = 5\n")

    def test_implicit_table_gets_a_header_at_the_end(self):
        text = "[runner.retry.scopes.x]\nk = 1\n"
        out = toml_splice.set_table(text, ("runner", "retry"), {"base_s": 2})
        self.assertTrue(out.startswith(text))
        self.assertEqual(
            tomllib.loads(out)["runner"]["retry"], {"base_s": 2, "scopes": {"x": {"k": 1}}})

    def test_text_without_final_newline_gets_one_first(self):
        out = toml_splice.set_table("a = 1", ("lanes",), {"strategy": "x"})
        self.assertEqual(out, 'a = 1\n\n[lanes]\nstrategy = "x"\n')

    def test_parent_table_beside_an_array_of_tables_child_changes_only_its_key(self):
        # Regression (Plan 33-09): the parent's values carry the [[lanes.review]] array, which
        # lives in its own blocks and must not be written as an inline key of [lanes].
        text = '[lanes]\nstrategy = "a"\n\n[[lanes.review]]\nkey = "k"\nmodel = "m"\n'
        out = toml_splice.set_table(text, ("lanes",), {"strategy": "b"})
        self.assertEqual(
            out, '[lanes]\nstrategy = "b"\n\n[[lanes.review]]\nkey = "k"\nmodel = "m"\n')

    def test_crlf_file_keeps_crlf_on_every_line(self):
        text = BASE.replace("\n", "\r\n")
        out = toml_splice.set_table(text, ("runner", "retry"), {"base_s": 2})
        self.assertEqual(out.count("\n"), out.count("\r\n"))
        self.assertEqual(tomllib.loads(out)["runner"]["retry"]["base_s"], 2)

    def test_string_final_array_is_one_span_and_is_rewritten(self):
        text = '[runner]\nladder = ["a", "b"]\n'
        runner = next(b for b in toml_splice.split_blocks(text) if b.path == ("runner",))
        self.assertEqual(len(runner.spans), 1)
        self.assertEqual(runner.spans[0].key, ("ladder",))
        self.assertEqual(runner.spans[0].value, ["a", "b"])
        out = toml_splice.set_table(text, ("runner",), {"ladder": ["b", "a"]})
        self.assertEqual(out, '[runner]\nladder = ["b", "a"]\n')

    def test_bracketed_scope_header_is_one_table(self):
        text = '[runner.retry.scopes."p[1]"] # note\nmax_retries = 2\n'
        found = [b for b in toml_splice.split_blocks(text)
                 if b.path == ("runner", "retry", "scopes", "p[1]")]
        self.assertEqual(len(found), 1)
        self.assertFalse(found[0].array)
        out = toml_splice.set_table(text, ("lanes",), {"strategy": "x"})
        self.assertIn('[runner.retry.scopes."p[1]"] # note\nmax_retries = 2\n', out)
        self.assertEqual(tomllib.loads(out)["lanes"], {"strategy": "x"})

    def test_unparsable_header_names_the_line(self):
        text = "['foo]bar']\nx = 1\n"
        self.assertEqual(tomllib.loads(text), {"foo]bar": {"x": 1}})
        message = "line 1: cannot parse this table header"
        with self.assertRaises(SpliceError) as split_ctx:
            toml_splice.split_blocks(text)
        self.assertIs(type(split_ctx.exception), SpliceError)
        self.assertTrue(str(split_ctx.exception).startswith(message))
        with self.assertRaises(SpliceError) as set_ctx:
            toml_splice.set_table(text, ("lanes",), {"strategy": "x"})
        self.assertIs(type(set_ctx.exception), SpliceError)
        self.assertTrue(str(set_ctx.exception).startswith(message))

    def test_list_of_tables_value_is_refused(self):
        with self.assertRaises(SpliceError):
            toml_splice.set_table("", ("lanes",), {"review": [{"key": "a"}]})


class TestPublish(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="ai-kit-splice-")
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)

    def _read(self, path):
        with open(path, encoding="utf-8") as handle:
            return handle.read()

    def test_new_file_gets_exact_text_and_mode_0600(self):
        path = os.path.join(self.dir, "config.toml")
        toml_splice.publish(path, '[lanes]\nstrategy = "x"\n')
        self.assertEqual(self._read(path), '[lanes]\nstrategy = "x"\n')
        self.assertEqual(stat.S_IMODE(os.stat(path).st_mode), 0o600)

    def test_existing_file_keeps_its_mode(self):
        path = os.path.join(self.dir, "config.toml")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("a = 1\n")
        os.chmod(path, 0o644)
        toml_splice.publish(path, "a = 2\n")
        self.assertEqual(self._read(path), "a = 2\n")
        self.assertEqual(stat.S_IMODE(os.stat(path).st_mode), 0o644)

    def test_symlink_stays_a_link_and_the_target_is_written(self):
        target = os.path.join(self.dir, "real.toml")
        link = os.path.join(self.dir, "link.toml")
        with open(target, "w", encoding="utf-8") as handle:
            handle.write("a = 1\n")
        os.symlink(target, link)
        toml_splice.publish(link, "a = 2\n")
        self.assertTrue(os.path.islink(link))
        self.assertEqual(self._read(target), "a = 2\n")

    def test_interrupted_before_rename_keeps_the_old_file(self):
        path = os.path.join(self.dir, "config.toml")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("a = 1\n")
        with mock.patch("ai_kit_spec.cache.os.replace", side_effect=OSError("boom")), \
                self.assertRaises(OSError):
            toml_splice.publish(path, "a = 2\n")
        self.assertEqual(self._read(path), "a = 1\n")
        self.assertEqual([name for name in os.listdir(self.dir) if name.endswith(".tmp")], [])

    def test_invalid_toml_is_refused_and_nothing_is_written(self):
        path = os.path.join(self.dir, "config.toml")
        with self.assertRaises(SpliceError):
            toml_splice.publish(path, "a = = 1\n")
        self.assertFalse(os.path.exists(path))


REVIEW_TWO = (
    "# first lane\n"
    "[[lanes.review]]\n"
    'key = "a"\n'
    'model = "m1"\n'
    "\n"
    "# third lane\n"
    "[[lanes.review]]\n"
    'key = "c"\n'
    'model = "m3"\n'
)

TWO_SHORT = (
    "# lane a\n[[lanes.review]]\nkey = \"a\"\n"
    "# lane c\n[[lanes.review]]\nkey = \"c\"\n"
)

THREE_BLANK = (
    "# lane a\n[[lanes.review]]\nkey = \"a\"\n\n"
    "# lane b\n[[lanes.review]]\nkey = \"b\"\n\n"
    "# lane c\n[[lanes.review]]\nkey = \"c\"\n"
)

INTERLEAVED = (
    '[[lanes.review]]\nkey = "a"\nmodel = "m1"\n\n'
    '[[lanes.execute]]\nkey = "a"\nmodel = "m1"\n\n'
    '[[lanes.review]]\nkey = "b"\n'
)

SUB = (
    "[[lanes.review]]\n"
    'key = "a"\n'
    "# why m1\n"
    'model = "m1"\n'
    "[lanes.review.extra]\n"
    "# tuning\n"
    "depth = 1\n"
)

IMPLICIT = '[[lanes.review]]\nkey = "a"\n[lanes.review.extra.tuning]\ndepth = 1\n'

NESTED = '[[lanes.review]]\nkey = "a"\n[[lanes.review.steps]]\nname = "s"\n'

REVIEW = ("lanes", "review")


class TestSetArray(unittest.TestCase):
    def test_only_the_changed_entry_line_differs(self):
        entries = [{"key": "a", "model": "m1"}, {"key": "c", "model": "m9"}]
        out = toml_splice.set_array(REVIEW_TWO, REVIEW, entries)
        removed, added = _changed(REVIEW_TWO, out)
        self.assertEqual(removed, ['- model = "m3"\n'])
        self.assertEqual(added, ['+ model = "m9"\n'])
        self.assertEqual(tomllib.loads(out), {"lanes": {"review": entries}})

    def test_added_entry_goes_after_the_last_entry(self):
        entries = [{"key": "a", "model": "m1"}, {"key": "c", "model": "m3"},
                   {"key": "d", "model": "m4"}]
        out = toml_splice.set_array(REVIEW_TWO, REVIEW, entries)
        self.assertTrue(out.startswith(REVIEW_TWO))
        self.assertEqual(tomllib.loads(out), {"lanes": {"review": entries}})

    def test_removed_entry_takes_its_header_body_and_comment_above(self):
        entries = [{"key": "c", "model": "m3"}]
        out = toml_splice.set_array(REVIEW_TWO, REVIEW, entries)
        self.assertNotIn("first lane", out)
        self.assertNotIn('key = "a"', out)
        self.assertEqual(tomllib.loads(out), {"lanes": {"review": entries}})

    def test_middle_insertion_keeps_neighbours_byte_equal(self):
        entries = [{"key": "a"}, {"key": "b"}, {"key": "c"}]
        out = toml_splice.set_array(TWO_SHORT, REVIEW, entries)
        self.assertTrue(out.startswith("# lane a\n[[lanes.review]]\nkey = \"a\"\n"))
        self.assertIn("# lane c\n[[lanes.review]]\nkey = \"c\"\n", out)
        self.assertLess(out.index('key = "b"'), out.index("# lane c"))
        self.assertEqual(tomllib.loads(out), {"lanes": {"review": entries}})

    def test_start_insertion_lands_before_the_first_group(self):
        entries = [{"key": "x"}, {"key": "a"}, {"key": "c"}]
        out = toml_splice.set_array(TWO_SHORT, REVIEW, entries)
        self.assertLess(out.index('key = "x"'), out.index("# lane a"))
        self.assertIn("# lane a\n[[lanes.review]]\nkey = \"a\"\n# lane c\n", out)
        self.assertEqual(tomllib.loads(out), {"lanes": {"review": entries}})

    def test_interleaved_insertion_keeps_each_role_in_order(self):
        entries = [{"key": "a", "model": "m1"}, {"key": "x"}, {"key": "b"}]
        out = toml_splice.set_array(INTERLEAVED, REVIEW, entries)
        self.assertIn('[[lanes.execute]]\nkey = "a"\nmodel = "m1"\n\n', out)
        parsed = tomllib.loads(out)
        self.assertEqual(parsed["lanes"]["review"], entries)
        self.assertEqual(parsed["lanes"]["execute"], [{"key": "a", "model": "m1"}])

    def test_reordering_re_emits_each_block_unchanged_in_the_new_order(self):
        entries = [{"key": "c"}, {"key": "a"}, {"key": "b"}]
        out = toml_splice.set_array(THREE_BLANK, REVIEW, entries)
        for block in ('# lane a\n[[lanes.review]]\nkey = "a"\n',
                      '# lane b\n[[lanes.review]]\nkey = "b"\n',
                      '# lane c\n[[lanes.review]]\nkey = "c"\n'):
            self.assertIn(block, out)
        self.assertLess(out.index('key = "c"'), out.index('key = "a"'))
        self.assertLess(out.index('key = "a"'), out.index('key = "b"'))
        self.assertEqual(tomllib.loads(out), {"lanes": {"review": entries}})

    def test_interleaved_change_of_one_role_keeps_the_other_byte_equal(self):
        entries = [{"key": "a", "model": "m2"}, {"key": "b"}]
        out = toml_splice.set_array(INTERLEAVED, REVIEW, entries)
        removed, added = _changed(INTERLEAVED, out)
        self.assertEqual(len(removed), 1)
        self.assertEqual(len(added), 1)
        self.assertIn('[[lanes.execute]]\nkey = "a"\nmodel = "m1"\n\n', out)
        parsed = tomllib.loads(out)
        self.assertEqual(parsed["lanes"]["review"], entries)
        self.assertEqual(parsed["lanes"]["execute"], [{"key": "a", "model": "m1"}])

    def test_entries_without_a_key_match_by_position(self):
        text = '[[lanes.review]]\nmodel = "m1"\n\n[[lanes.review]]\nmodel = "m2"\n'
        entries = [{"model": "m1"}, {"model": "x"}]
        out = toml_splice.set_array(text, REVIEW, entries)
        removed, added = _changed(text, out)
        self.assertEqual(removed, ['- model = "m2"\n'])
        self.assertEqual(added, ['+ model = "x"\n'])
        self.assertEqual(tomllib.loads(out), {"lanes": {"review": entries}})

    def test_empty_entries_remove_every_entry_block(self):
        out = toml_splice.set_array(REVIEW_TWO, REVIEW, [])
        self.assertEqual(tomllib.loads(out), {})
        self.assertNotIn("[[lanes.review]]", out)

    def test_no_entry_of_that_path_appends_at_the_end(self):
        text = '[lanes]\nstrategy = "local-only"\n'
        entries = [{"key": "a"}]
        out = toml_splice.set_array(text, REVIEW, entries)
        self.assertTrue(out.startswith(text))
        self.assertEqual(
            tomllib.loads(out), {"lanes": {"strategy": "local-only", "review": entries}})

    def test_sub_table_is_edited_in_place_for_a_changed_key(self):
        entries = [{"key": "a", "model": "m1", "extra": {"depth": 2}}]
        out = toml_splice.set_array(SUB, REVIEW, entries)
        removed, added = _changed(SUB, out)
        self.assertEqual(removed, ["- depth = 1\n"])
        self.assertEqual(added, ["+ depth = 2\n"])
        self.assertIn("# why m1\n", out)
        self.assertIn("# tuning\n", out)
        self.assertEqual(tomllib.loads(out), {"lanes": {"review": entries}})

    def test_changed_model_keeps_the_sub_table_block_byte_equal(self):
        entries = [{"key": "a", "model": "m2", "extra": {"depth": 1}}]
        out = toml_splice.set_array(SUB, REVIEW, entries)
        removed, added = _changed(SUB, out)
        self.assertEqual(removed, ['- model = "m1"\n'])
        self.assertEqual(added, ['+ model = "m2"\n'])
        self.assertIn("[lanes.review.extra]\n# tuning\ndepth = 1\n", out)
        self.assertIn("# why m1\n", out)

    def test_dropped_sub_table_takes_its_comment_with_it(self):
        entries = [{"key": "a", "model": "m1"}]
        out = toml_splice.set_array(SUB, REVIEW, entries)
        self.assertNotIn("[lanes.review.extra]", out)
        self.assertNotIn("# tuning", out)
        self.assertIn("# why m1\n", out)
        self.assertEqual(tomllib.loads(out), {"lanes": {"review": entries}})

    def test_unchanged_entry_with_sub_table_is_kept_byte_equal(self):
        entries = [{"key": "a", "model": "m1", "extra": {"depth": 1}}]
        self.assertEqual(toml_splice.set_array(SUB, REVIEW, entries), SUB)

    def test_new_key_under_implicit_parent(self):
        entries = [{"key": "a", "extra": {"enabled": True, "tuning": {"depth": 1}}}]
        out = toml_splice.set_array(IMPLICIT, REVIEW, entries)
        self.assertEqual(tomllib.loads(out), {"lanes": {"review": entries}})
        removed, added = _changed(IMPLICIT, out)
        self.assertEqual(removed, [])
        self.assertEqual(len(added), 2)
        self.assertLess(out.index("[lanes.review.extra]\n"),
                        out.index("[lanes.review.extra.tuning]"))

    def test_implicit_table_set_through_a_dotted_key_is_refused(self):
        text = ('[[lanes.review]]\nkey = "a"\nextra.enabled = false\n'
                '[lanes.review.extra.tuning]\ndepth = 1\n')
        entries = [{"key": "a", "extra": {"enabled": True, "tuning": {"depth": 1}}}]
        with self.assertRaises(SpliceError):
            toml_splice.set_array(text, REVIEW, entries)

    def test_changed_entry_with_a_nested_array_of_tables_is_refused(self):
        with self.assertRaises(SpliceError):
            toml_splice.set_array(NESTED, REVIEW, [{"key": "a", "steps": [{"name": "t"}]}])
        unchanged = [{"key": "a", "steps": [{"name": "s"}]}]
        self.assertEqual(toml_splice.set_array(NESTED, REVIEW, unchanged), NESTED)

    def test_crlf_file_keeps_crlf_on_every_written_line(self):
        text = REVIEW_TWO.replace("\n", "\r\n")
        entries = [{"key": "a", "model": "m1"}, {"key": "c", "model": "m9"}]
        out = toml_splice.set_array(text, REVIEW, entries)
        self.assertEqual(out.count("\n"), out.count("\r\n"))
        self.assertEqual(tomllib.loads(out), {"lanes": {"review": entries}})


class TestRemoveTable(unittest.TestCase):
    def test_removes_the_header_and_every_block_under_it(self):
        text = (
            '[lanes]\nstrategy = "x"\n\n'
            '[lanes.policy]\nmode = "single"\n\n'
            '[[lanes.policy.steps]]\nname = "s"\n\n'
            "[other]\nkeep = 1\n"
        )
        out = toml_splice.remove_table(text, ("lanes", "policy"))
        self.assertEqual(tomllib.loads(out), {"lanes": {"strategy": "x"}, "other": {"keep": 1}})
        self.assertNotIn("[lanes.policy", out)
        self.assertIn("[other]\nkeep = 1\n", out)
        self.assertLess(out.index("[lanes]"), out.index("[other]"))

    def test_absent_table_returns_the_input(self):
        text = '[lanes]\nstrategy = "x"\n'
        self.assertIs(toml_splice.remove_table(text, ("nope",)), text)


SECTIONED = (
    '[[lanes.review]]\nkey = "a"\n\n[[lanes.review]]\nkey = "b"\n\n'
    "# ---- runner settings ----\n\n[runner]\nx = 1\n"
)


class TestSectionComments(unittest.TestCase):
    """WR-02: a comment group after a blank line and before the next table belongs to that table."""

    def test_removing_the_last_entry_keeps_the_section_comment(self):
        out = toml_splice.set_array(SECTIONED, REVIEW, [{"key": "a"}])
        self.assertIn("# ---- runner settings ----\n\n[runner]\nx = 1\n", out)
        self.assertNotIn('key = "b"', out)
        self.assertEqual(tomllib.loads(out),
                         {"lanes": {"review": [{"key": "a"}]}, "runner": {"x": 1}})

    def test_removing_the_only_entry_keeps_the_section_comment(self):
        text = '[[lanes.review]]\nkey = "a"\n\n# ---- runner ----\n\n[runner]\nx = 1\n'
        out = toml_splice.set_array(text, REVIEW, [])
        self.assertEqual(out, "# ---- runner ----\n\n[runner]\nx = 1\n")

    def test_appended_entry_goes_before_the_section_comment_with_a_blank_line(self):
        entries = [{"key": "a"}, {"key": "b"}, {"key": "c"}]
        out = toml_splice.set_array(SECTIONED, REVIEW, entries)
        self.assertIn('key = "c"\n\n# ---- runner settings ----\n\n[runner]\n', out)
        self.assertTrue(out.startswith(SECTIONED[: SECTIONED.index("# ----")]))
        self.assertEqual(tomllib.loads(out), {"lanes": {"review": entries}, "runner": {"x": 1}})

    def test_a_comment_right_under_the_last_key_stays_with_its_entry(self):
        text = '[[lanes.review]]\nkey = "a"\n# about a\n\n[runner]\nx = 1\n'
        out = toml_splice.set_array(text, REVIEW, [])
        self.assertNotIn("about a", out)

    def test_remove_table_keeps_a_file_comment_separated_by_a_blank_line(self):
        text = '# ai-kit config, keep me\n\n[lanes.policy]\nmode = "single"\n\n[runner]\nx = 1\n'
        out = toml_splice.remove_table(text, ("lanes", "policy"))
        self.assertTrue(out.startswith("# ai-kit config, keep me\n"))
        self.assertEqual(tomllib.loads(out), {"runner": {"x": 1}})

    def test_remove_table_keeps_the_section_comment_that_follows_it(self):
        text = '[lanes.policy]\nmode = "single"\n\n# ---- runner ----\n\n[runner]\nx = 1\n'
        out = toml_splice.remove_table(text, ("lanes", "policy"))
        self.assertEqual(out, "# ---- runner ----\n\n[runner]\nx = 1\n")


class TestSpliceRefusals(unittest.TestCase):
    def test_wrong_value_writer_is_refused_by_the_reparse(self):
        with mock.patch.object(toml_splice, "toml_value", lambda value: "0"), \
                self.assertRaises(SpliceError):
            toml_splice.set_table("[runner]\nx = 1\n", ("runner",), {"x": 2})

    def test_dotted_key_conflict_is_correct_or_refused(self):
        text = '[lanes]\npolicy.mode = "single"\n'
        try:
            out = toml_splice.set_table(text, ("lanes", "policy"), {"mode": "double"})
        except SpliceError:
            return
        self.assertEqual(tomllib.loads(out)["lanes"]["policy"], {"mode": "double"})


class TestEdgeRows(unittest.TestCase):
    def test_empty_file_gets_only_the_written_table(self):
        out = toml_splice.set_table("", ("lanes",), {"strategy": "local-only"})
        self.assertEqual(out, '[lanes]\nstrategy = "local-only"\n')

    def test_table_order_is_kept_when_one_table_is_edited(self):
        text = "[a]\nx = 1\n\n[b]\ny = 2\n\n[c]\nz = 3\n"
        out = toml_splice.set_table(text, ("b",), {"y": 5})
        self.assertEqual(re.findall(r"^\[(\w+)\]", out, re.MULTILINE), ["a", "b", "c"])
        self.assertEqual(tomllib.loads(out)["b"], {"y": 5})

    def test_toml_value_round_trips_through_tomllib(self):
        values = ['a"b\\c\n\t\x01', 1.5, -3, True, [1, "x"], {"k": [1, 2]}]
        for value in values:
            with self.subTest(value=value):
                parsed = tomllib.loads("v = " + toml_splice.toml_value(value))["v"]
                self.assertEqual(parsed, value)

    def test_toml_value_refuses_nan_and_unknown_types(self):
        with self.assertRaises(SpliceError):
            toml_splice.toml_value(float("nan"))
        with self.assertRaises(SpliceError):
            toml_splice.toml_value(object())


class TestCacheFsync(unittest.TestCase):
    def test_file_and_folder_are_both_fsynced(self):
        folder = tempfile.mkdtemp(prefix="ai-kit-splice-")
        self.addCleanup(shutil.rmtree, folder, ignore_errors=True)
        real_fsync = os.fsync
        calls = []

        def recording(fd):
            calls.append(fd)
            return real_fsync(fd)

        with mock.patch("ai_kit_spec.cache.os.fsync", side_effect=recording):
            cache.cache_write_bytes(os.path.join(folder, "x.toml"), b"a = 1\n", mode=0o600)
        self.assertGreaterEqual(len(calls), 2)


if __name__ == "__main__":
    unittest.main()
