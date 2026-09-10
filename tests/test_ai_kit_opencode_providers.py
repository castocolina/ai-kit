import glob
import io
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import types
import unittest
from unittest import mock

sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "skills", "ai-kit-opencode-providers"),
)

from ai_kit_opencode_providers import atomic_write, jsonc_edit
from ai_kit_opencode_providers.cli import (
    EXIT_ERROR,
    EXIT_NO_CONFIG,
    cmd_list,
    cmd_remove,
)

FIXTURE_DIR = os.path.join(
    os.path.dirname(__file__), "e2e", "docker", "fixtures", "opencode"
)
SCRATCH_REVIEW_SPEC_RELPATH = ".aikit/review-spec.toml"
SHIM = os.path.join(
    os.path.dirname(__file__),
    "..",
    "skills",
    "ai-kit-opencode-providers",
    "ai-kit-opencode-providers.py",
)


def run_cli(*args, cwd, env=None):
    return subprocess.run(
        [sys.executable, SHIM, *args],
        cwd=cwd,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        check=False,
    )


def scratch_env(root):
    env = dict(os.environ)
    env["HOME"] = root
    env["XDG_CONFIG_HOME"] = os.path.join(root, ".config")
    env["XDG_CACHE_HOME"] = os.path.join(root, ".cache")
    return env


class TestTracerRemoveEndToEnd(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.scratch, ignore_errors=True)
        self.config = os.path.join(self.scratch, "opencode.jsonc")
        shutil.copy(os.path.join(FIXTURE_DIR, "opencode.jsonc"), self.config)
        self.review_spec = os.path.join(self.scratch, SCRATCH_REVIEW_SPEC_RELPATH)

    def test_remove_beta_router_matches_hand_authored_fixture(self):
        with open(self.config, encoding="utf-8") as handle:
            original = handle.read()
        mode_before = stat.S_IMODE(os.stat(self.config).st_mode)
        result = run_cli(
            "remove",
            "beta-router",
            "--config",
            self.config,
            cwd=self.scratch,
            env=scratch_env(self.scratch),
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        with open(self.config, encoding="utf-8") as handle:
            actual = handle.read()
        expected_path = os.path.join(
            FIXTURE_DIR, "opencode-expected-remove-beta.jsonc"
        )
        with open(expected_path, encoding="utf-8") as handle:
            expected = handle.read()
        self.assertEqual(actual, expected)
        key_marker = '"beta-router": {\n      "npm": "@ai-sdk/anthropic"'
        key_at = original.index(key_marker)
        close_marker = "} /* keep { this } comment */"
        value_end = original.index(close_marker) + 1
        removed_span = value_end - key_at
        self.assertEqual(len(actual) + removed_span + 1, len(original))
        self.assertEqual(stat.S_IMODE(os.stat(self.config).st_mode), mode_before)

    def test_iter_provider_entries_skips_nested_decoy(self):
        fixture = os.path.join(FIXTURE_DIR, "opencode.jsonc")
        with open(fixture, encoding="utf-8") as handle:
            text = handle.read()
        ids = [e.provider_id for e in jsonc_edit.iter_provider_entries(text)]
        self.assertEqual(ids, ["alpha-router", "beta-router", "gamma-router"])

    def test_find_provider_object_depth_zero_only(self):
        nested_only = '{ "backup": { "provider": { "decoy-router": {} } } }\n'
        self.assertIsNone(jsonc_edit.find_provider_object(nested_only))
        both = (
            '{ "backup": { "provider": { "decoy-router": {} } },\n'
            '  "provider": { "real-router": {} }\n}\n'
        )
        span = jsonc_edit.find_provider_object(both)
        self.assertIsNotNone(span)
        slice_text = both[span[0] : span[1]]
        self.assertIn("real-router", slice_text)
        self.assertNotIn("decoy-router", slice_text)

    def test_missing_config_exits_no_config(self):
        missing = os.path.join(self.scratch, "missing", "opencode.jsonc")
        result = run_cli(
            "remove",
            "x",
            "--config",
            missing,
            cwd=self.scratch,
            env=scratch_env(self.scratch),
        )
        self.assertEqual(result.returncode, EXIT_NO_CONFIG)
        self.assertIn(missing, result.stderr)
        self.assertFalse(os.path.exists(missing))


def _fixture_text(name="opencode.jsonc"):
    with open(os.path.join(FIXTURE_DIR, name), encoding="utf-8") as handle:
        return handle.read()


def _assert_parses(test, text):
    parsed = json.loads(jsonc_edit.strip_jsonc_comments(text))
    test.assertIsInstance(parsed, dict)
    return parsed


def _call_cmd_remove(config_path, provider_id, cwd):
    args = types.SimpleNamespace(config=config_path, provider_id=provider_id)
    out = io.StringIO()
    err = io.StringIO()
    code = cmd_remove(args, scratch_env(cwd), cwd, out, err)
    return code, out.getvalue(), err.getvalue()


class TestRemoveCommaCases(unittest.TestCase):
    def test_remove_first_leaves_no_leading_comma(self):
        original = _fixture_text()
        result = jsonc_edit.remove_provider(original, "alpha-router")
        self.assertIsNotNone(result)
        parsed = _assert_parses(self, result)
        self.assertEqual(
            list(parsed["provider"].keys()), ["beta-router", "gamma-router"]
        )
        provider_slice = result[
            result.index('"provider"') : result.index("} /* after provider")
        ]
        self.assertNotRegex(provider_slice, r'\{\s*,')
        self.assertIn("// leftover { retired } unmatched", result)
        self.assertIn("/* keep { this } comment */", result)
        self.assertIn("/* after provider { brace } */", result)

    def test_remove_middle_leaves_one_comma(self):
        original = _fixture_text()
        result = jsonc_edit.remove_provider(original, "beta-router")
        parsed = _assert_parses(self, result)
        self.assertEqual(
            list(parsed["provider"].keys()), ["alpha-router", "gamma-router"]
        )
        self.assertIn("/* keep { this } comment */", result)
        between = result[
            result.index('    },\n    // leftover') : result.index('"gamma-router"')
        ]
        self.assertEqual(jsonc_edit.strip_jsonc_comments(between).count(","), 1)

    def test_remove_last_consumes_preceding_comma_keeps_comment(self):
        original = _fixture_text()
        result = jsonc_edit.remove_provider(original, "gamma-router")
        parsed = _assert_parses(self, result)
        self.assertEqual(
            list(parsed["provider"].keys()), ["alpha-router", "beta-router"]
        )
        decoy = "// decoy separator , between last two"
        self.assertIn(decoy, result)
        after_beta = result[
            result.index("/* keep { this } comment */") : result.index(
                "} /* after provider"
            )
        ]
        stripped = jsonc_edit.strip_jsonc_comments(after_beta)
        self.assertNotIn(",", stripped)
        self.assertIn(decoy, result)

    def test_remove_sole_entry_leaves_empty_object(self):
        original = _fixture_text("opencode-single-provider.jsonc")
        result = jsonc_edit.remove_provider(original, "solo-router")
        parsed = _assert_parses(self, result)
        self.assertEqual(parsed["provider"], {})
        self.assertIn("// keep this comment for byte-identity", result)
        self.assertNotIn('"solo-router"', jsonc_edit.strip_jsonc_comments(result))


class TestRemoveEdgeCases(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.scratch, ignore_errors=True)
        self.config = os.path.join(self.scratch, "opencode.jsonc")

    def test_nested_id_only_returns_none(self):
        text = (
            '{ "provider": { "alpha-router": { "models": { "beta-router": {} } } } }'
        )
        self.assertIsNone(jsonc_edit.remove_provider(text, "beta-router"))

    def test_missing_id_is_clean_noop(self):
        shutil.copy(os.path.join(FIXTURE_DIR, "opencode.jsonc"), self.config)
        with open(self.config, encoding="utf-8") as handle:
            before = handle.read()
        result = run_cli(
            "remove",
            "no-such-id",
            "--config",
            self.config,
            cwd=self.scratch,
            env=scratch_env(self.scratch),
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("no-such-id", result.stdout)
        with open(self.config, encoding="utf-8") as handle:
            after = handle.read()
        self.assertEqual(before, after)

    def test_missing_provider_key_is_clean_noop(self):
        with open(self.config, "w", encoding="utf-8") as handle:
            handle.write('{ "model": "x" }\n')
        with open(self.config, encoding="utf-8") as handle:
            before = handle.read()
        code, out, err = _call_cmd_remove(self.config, "beta-router", self.scratch)
        self.assertEqual(code, 0)
        self.assertIn("beta-router", out)
        self.assertIn("nothing to remove", out)
        self.assertEqual(err, "")
        with open(self.config, encoding="utf-8") as handle:
            after = handle.read()
        self.assertEqual(before, after)

    def test_nested_provider_key_before_real_is_ignored(self):
        text = (
            '{ "backup": { "provider": { "decoy-router": { "npm": "x" } } },\n'
            '  "provider": { "real-router": { "npm": "y" } }\n}\n'
        )
        ids = [e.provider_id for e in jsonc_edit.iter_provider_entries(text)]
        self.assertEqual(ids, ["real-router"])
        result = jsonc_edit.remove_provider(text, "real-router")
        self.assertIsNotNone(result)
        self.assertIn("decoy-router", result)
        self.assertNotIn("real-router", jsonc_edit.strip_jsonc_comments(result))

    def test_nested_provider_key_only_is_noop(self):
        text = '{ "backup": { "provider": { "decoy-router": { "npm": "x" } } } }\n'
        self.assertIsNone(jsonc_edit.find_provider_object(text))
        with open(self.config, "w", encoding="utf-8") as handle:
            handle.write(text)
        code, out, err = _call_cmd_remove(self.config, "decoy-router", self.scratch)
        self.assertEqual(code, 0)
        self.assertIn("nothing to remove", out)
        self.assertEqual(err, "")
        with open(self.config, encoding="utf-8") as handle:
            after = handle.read()
        self.assertEqual(after, text)


class TestWalkerStates(unittest.TestCase):
    def test_string_and_comment_are_mutually_suppressing(self):
        text = _fixture_text()
        ids = [e.provider_id for e in jsonc_edit.iter_provider_entries(text)]
        self.assertEqual(ids, ["alpha-router", "beta-router", "gamma-router"])
        stripped = jsonc_edit.strip_jsonc_comments(text)
        self.assertIn("https://beta.invalid/v1/*path}{tail", stripped)
        self.assertIn("https://alpha.invalid/v1", stripped)
        self.assertNotIn("leftover { retired }", stripped)
        self.assertNotIn("keep { this } comment", stripped)
        comment_start = text.index("// leftover")
        comment_end = text.index("\n", comment_start)
        self.assertTrue(
            all(ch == " " or ch == "\n" for ch in stripped[comment_start:comment_end])
        )


class TestWalkerSeeding(unittest.TestCase):
    def test_significant_indices_match_strip_jsonc_comments(self):
        text = _fixture_text()
        span = jsonc_edit.find_provider_object(text)
        self.assertIsNotNone(span)
        open_i, close_i = span
        sig = set(jsonc_edit.significant_indices(text, open_i, close_i))
        stripped = jsonc_edit.strip_jsonc_comments(text)
        independent = {
            i
            for i in range(open_i, close_i)
            if not text[i].isspace() and stripped[i] == text[i]
        }
        self.assertEqual(sig, independent)

    def test_last_entry_deletes_real_comma_not_decoy(self):
        original = _fixture_text()
        result = jsonc_edit.remove_provider(original, "gamma-router")
        self.assertIn("// decoy separator , between last two", result)
        _assert_parses(self, result)
        after_beta = result[
            result.index("/* keep { this } comment */") : result.index(
                "} /* after provider"
            )
        ]
        self.assertNotIn(",", jsonc_edit.strip_jsonc_comments(after_beta))


class TestDuplicateProviderId(unittest.TestCase):
    def test_first_match_removed_second_survives(self):
        text = (
            '{ "provider": {\n'
            '    "dup-router": { "npm": "first" },\n'
            '    "dup-router": { "npm": "second" }\n'
            "} }\n"
        )
        first = jsonc_edit.remove_provider(text, "dup-router")
        self.assertIsNotNone(first)
        self.assertNotIn('"npm": "first"', first)
        self.assertIn('"npm": "second"', first)
        second = jsonc_edit.remove_provider(first, "dup-router")
        self.assertIsNotNone(second)
        self.assertNotIn("dup-router", jsonc_edit.strip_jsonc_comments(second))


class TestNonObjectProviderValue(unittest.TestCase):
    TEXT = (
        '{ "provider": {\n'
        '    "obj-one": { "npm": "a" },\n'
        '    "str-key": "not-an-object",\n'
        '    "arr-key": ["has,comma", { "x": 1 }],\n'
        '    "obj-two": { "npm": "b" }\n'
        "} }\n"
    )

    def test_iter_skips_non_objects_and_resumes(self):
        ids = [e.provider_id for e in jsonc_edit.iter_provider_entries(self.TEXT)]
        self.assertEqual(ids, ["obj-one", "obj-two"])
        self.assertEqual(
            jsonc_edit.non_object_provider_keys(self.TEXT),
            ["str-key", "arr-key"],
        )

    def test_remove_non_object_id_is_none(self):
        self.assertIsNone(jsonc_edit.remove_provider(self.TEXT, "str-key"))

    def test_remove_following_object_still_works(self):
        result = jsonc_edit.remove_provider(self.TEXT, "obj-two")
        self.assertIsNotNone(result)
        ids = [e.provider_id for e in jsonc_edit.iter_provider_entries(result)]
        self.assertEqual(ids, ["obj-one"])

    def test_cmd_remove_reports_not_an_object(self):
        scratch = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, scratch, ignore_errors=True)
        config = os.path.join(scratch, "opencode.jsonc")
        with open(config, "w", encoding="utf-8") as handle:
            handle.write(self.TEXT)
        code, out, err = _call_cmd_remove(config, "str-key", scratch)
        self.assertEqual(code, 0)
        self.assertIn("str-key", out)
        self.assertIn("not an object", out)
        self.assertNotIn("nothing to remove", out)
        self.assertEqual(err, "")
        with open(config, encoding="utf-8") as handle:
            after = handle.read()
        self.assertEqual(after, self.TEXT)


class TestAtomicWrite(unittest.TestCase):
    def test_replace_failure_leaves_original_intact(self):
        scratch = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, scratch, ignore_errors=True)
        path = os.path.join(scratch, "opencode.jsonc")
        original = '{ "ok": true }\n'
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(original)
        with (
            mock.patch.object(
                atomic_write.os, "replace", side_effect=OSError("disk")
            ),
            self.assertRaises(OSError),
        ):
            atomic_write.write_preserving_mode(path, '{ "ok": false }\n')
        with open(path, encoding="utf-8") as handle:
            self.assertEqual(handle.read(), original)
        self.assertEqual(glob.glob(os.path.join(scratch, "*.tmp")), [])


@unittest.skipUnless(hasattr(os, "symlink"), "os.symlink unavailable")
class TestSymlinkedConfig(unittest.TestCase):
    def test_remove_through_symlink_keeps_link(self):
        a = tempfile.mkdtemp()
        b = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, a, ignore_errors=True)
        self.addCleanup(shutil.rmtree, b, ignore_errors=True)
        real = os.path.join(a, "opencode.jsonc")
        link = os.path.join(b, "opencode.jsonc")
        shutil.copy(os.path.join(FIXTURE_DIR, "opencode.jsonc"), real)
        os.chmod(real, 0o644)
        mode_before = stat.S_IMODE(os.stat(real).st_mode)
        os.symlink(real, link)
        result = run_cli(
            "remove",
            "beta-router",
            "--config",
            link,
            cwd=b,
            env=scratch_env(b),
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(os.path.islink(link))
        with open(real, encoding="utf-8") as handle:
            edited = handle.read()
        expected_path = os.path.join(
            FIXTURE_DIR, "opencode-expected-remove-beta.jsonc"
        )
        with open(expected_path, encoding="utf-8") as handle:
            expected = handle.read()
        self.assertEqual(edited, expected)
        self.assertEqual(stat.S_IMODE(os.stat(real).st_mode), mode_before)


class TestWriteFailureExitCode(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.scratch, ignore_errors=True)
        self.config = os.path.join(self.scratch, "opencode.jsonc")
        shutil.copy(os.path.join(FIXTURE_DIR, "opencode.jsonc"), self.config)

    def test_replace_oserror_is_exit_error(self):
        with mock.patch(
            "ai_kit_opencode_providers.cli.write_preserving_mode",
            side_effect=OSError("disk full"),
        ):
            code, out, err = _call_cmd_remove(
                self.config, "beta-router", self.scratch
            )
        self.assertEqual(code, EXIT_ERROR)
        error_lines = [ln for ln in err.splitlines() if ln.startswith("error:")]
        self.assertEqual(len(error_lines), 1)
        self.assertIn(self.config, error_lines[0])
        self.assertNotIn("Traceback", err)
        self.assertNotIn("Traceback", out)

    def test_non_utf8_read_is_exit_error(self):
        with open(self.config, "wb") as handle:
            handle.write(b"{\xff}")
        code, out, err = _call_cmd_remove(self.config, "beta-router", self.scratch)
        self.assertEqual(code, EXIT_ERROR)
        error_lines = [ln for ln in err.splitlines() if ln.startswith("error:")]
        self.assertEqual(len(error_lines), 1)
        self.assertIn(self.config, error_lines[0])
        self.assertNotIn("Traceback", err)
        self.assertNotIn("Traceback", out)


def _call_cmd_list(config_path, cwd):
    args = types.SimpleNamespace(config=config_path)
    out = io.StringIO()
    err = io.StringIO()
    code = cmd_list(args, scratch_env(cwd), cwd, out, err)
    return code, out.getvalue(), err.getvalue()


def _data_rows(stdout):
    lines = [ln for ln in stdout.splitlines() if ln.strip()]
    return [ln for ln in lines if not ln.startswith("note:")]


class TestListOutput(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.scratch, ignore_errors=True)
        self.config = os.path.join(self.scratch, "opencode.jsonc")

    def test_three_provider_table(self):
        shutil.copy(os.path.join(FIXTURE_DIR, "opencode.jsonc"), self.config)
        code, out, err = _call_cmd_list(self.config, self.scratch)
        self.assertEqual(code, 0, err)
        rows = _data_rows(out)
        self.assertEqual(len(rows), 4)
        self.assertTrue(rows[0].startswith("ID"))
        self.assertIn("NPM", rows[0])
        self.assertIn("BASE URL", rows[0])
        self.assertIn("alpha-router", rows[1])
        self.assertIn("beta-router", rows[2])
        self.assertIn("gamma-router", rows[3])
        self.assertIn("@ai-sdk/anthropic", rows[2])
        self.assertIn("https://beta.invalid/v1/*path}{tail", rows[2])

    def test_missing_fields_render_dash(self):
        text = '{ "provider": { "bare-router": {} } }\n'
        with open(self.config, "w", encoding="utf-8") as handle:
            handle.write(text)
        code, out, err = _call_cmd_list(self.config, self.scratch)
        self.assertEqual(code, 0, err)
        rows = _data_rows(out)
        self.assertEqual(len(rows), 2)
        self.assertIn("bare-router", rows[1])
        self.assertIn(" - ", rows[1] + " ")
        self.assertTrue(rows[1].rstrip().endswith("-"))

    def test_trailing_comma_entry_renders_real_values(self):
        text = (
            '{ "provider": {\n'
            '    "trail-router": {\n'
            '      "npm": "@ai-sdk/openai-compatible",\n'
            '      "options": { "baseURL": "https://example.invalid/v1", }\n'
            "    },\n"
            "} }\n"
        )
        with open(self.config, "w", encoding="utf-8") as handle:
            handle.write(text)
        code, out, err = _call_cmd_list(self.config, self.scratch)
        self.assertEqual(code, 0, err)
        rows = _data_rows(out)
        self.assertIn("@ai-sdk/openai-compatible", rows[1])
        self.assertIn("https://example.invalid/v1", rows[1])
        self.assertNotIn(" - ", f" {rows[1]} ")

    def test_comma_brace_inside_string_is_preserved(self):
        entry = (
            '{\n'
            '  "npm": "@ai-sdk/openai-compatible",\n'
            '  "options": { "baseURL": "https://h.invalid/,}" }\n'
            "}"
        )
        self.assertEqual(jsonc_edit.strip_trailing_commas(entry), entry)
        text = '{ "provider": { "str-router": ' + entry + " } }\n"
        with open(self.config, "w", encoding="utf-8") as handle:
            handle.write(text)
        code, out, err = _call_cmd_list(self.config, self.scratch)
        self.assertEqual(code, 0, err)
        rows = _data_rows(out)
        self.assertIn("https://h.invalid/,}", rows[1])

    def test_malformed_entry_renders_dashes(self):
        text = '{ "provider": { "bad-router": { npm: not-json } } }\n'
        with open(self.config, "w", encoding="utf-8") as handle:
            handle.write(text)
        code, out, err = _call_cmd_list(self.config, self.scratch)
        self.assertEqual(code, 0, err)
        rows = _data_rows(out)
        self.assertIn("bad-router", rows[1])
        cells = rows[1].split()
        self.assertGreaterEqual(len(cells), 3)
        self.assertEqual(cells[1], "-")
        self.assertEqual(cells[2], "-")

    def test_non_object_key_emits_note(self):
        text = (
            '{ "provider": {\n'
            '    "obj-one": { "npm": "a", "options": { "baseURL": "https://a" } },\n'
            '    "str-key": "not-an-object"\n'
            "} }\n"
        )
        with open(self.config, "w", encoding="utf-8") as handle:
            handle.write(text)
        code, out, err = _call_cmd_list(self.config, self.scratch)
        self.assertEqual(code, 0, err)
        self.assertEqual(out.count("str-key"), 1)
        self.assertIn("note:", out)
        rows = _data_rows(out)
        joined = "\n".join(rows)
        self.assertIn("obj-one", joined)
        self.assertNotIn("str-key", joined)

    def test_empty_provider_prints_explanatory_line(self):
        text = '{ "provider": {} }\n'
        with open(self.config, "w", encoding="utf-8") as handle:
            handle.write(text)
        code, out, err = _call_cmd_list(self.config, self.scratch)
        self.assertEqual(code, 0, err)
        self.assertEqual(len(out.strip().splitlines()), 1)
        self.assertIn(self.config, out)
        self.assertEqual(err, "")

    def test_absent_provider_prints_explanatory_line(self):
        text = '{ "model": "x" }\n'
        with open(self.config, "w", encoding="utf-8") as handle:
            handle.write(text)
        code, out, err = _call_cmd_list(self.config, self.scratch)
        self.assertEqual(code, 0, err)
        self.assertEqual(len(out.strip().splitlines()), 1)
        self.assertIn(self.config, out)

    def test_missing_path_exits_no_config(self):
        missing = os.path.join(self.scratch, "nope.jsonc")
        result = run_cli(
            "list",
            "--config",
            missing,
            cwd=self.scratch,
            env=scratch_env(self.scratch),
        )
        self.assertEqual(result.returncode, EXIT_NO_CONFIG)
        self.assertIn(missing, result.stderr)
        self.assertFalse(os.path.exists(missing))

    def test_non_utf8_list_is_exit_error(self):
        with open(self.config, "wb") as handle:
            handle.write(b"{\xff}")
        code, out, err = _call_cmd_list(self.config, self.scratch)
        self.assertEqual(code, EXIT_ERROR)
        self.assertTrue(err.startswith("error:"))
        self.assertIn(self.config, err)
        self.assertNotIn("Traceback", err)
        self.assertNotIn("Traceback", out)


class TestListRedaction(unittest.TestCase):
    def test_list_never_prints_apikey_sentinel(self):
        scratch = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, scratch, ignore_errors=True)
        config = os.path.join(scratch, "opencode.jsonc")
        fixture = os.path.join(FIXTURE_DIR, "opencode.jsonc")
        shutil.copy(fixture, config)
        with open(fixture, encoding="utf-8") as handle:
            fixture_text = handle.read()
        sentinel = "DO-NOT-PRINT"
        self.assertIn(sentinel, fixture_text)
        result = run_cli(
            "list",
            "--config",
            config,
            cwd=scratch,
            env=scratch_env(scratch),
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        combined = result.stdout + result.stderr
        self.assertEqual(combined.count(sentinel), 0)


if __name__ == "__main__":
    unittest.main()
