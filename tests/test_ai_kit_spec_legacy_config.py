import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest import mock

sys.path.insert(0, "skills/ai-kit-spec-review")

from ai_kit_spec.cli import main
from ai_kit_spec.config_io import (
    _emit_legacy_note,
    _legacy_command_knobs,
    cfg_load_toml,
    infer_legacy_native,
    normalize_legacy_entry,
    normalize_legacy_reviewers,
)


class TestLegacyTracer(unittest.TestCase):
    def test_old_file_normalizes_in_memory_with_one_safe_note(self):
        command = (
            "codex exec --sandbox read-only --skip-git-repo-check -m {model} "
            "-c model_reasoning_effort='\"high\"'"
        )
        text = (
            '[[reviewers]]\nkey = "cx"\ncli = "codex"\nmodel = "gpt-5.6-sol"\n'
            f"command = {json.dumps(command)}\n\n"
            '[[reviewers]]\nkey = "nc"\nnative_runtime = "claude"\nmodel = "opus"\n\n'
            '[[reviewers]]\nkey = "ss"\nmodel = "sonnet"\n'
        )
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "review-spec.toml")
            with open(path, "w", encoding="utf-8") as stream:
                stream.write(text)
            with open(path, "rb") as stream:
                before = stream.read()
            reviewers = cfg_load_toml(path)["reviewers"]
            migrated, notes = normalize_legacy_reviewers(reviewers)
            inferred, inferred_notes = infer_legacy_native(migrated)
            lines = []
            _emit_legacy_note(path, notes + inferred_notes, lines.append)
            self.assertEqual(inferred[0]["runtime"], "codex")
            self.assertEqual(inferred[0]["effort"], "high")
            self.assertNotIn("command", inferred[0])
            self.assertEqual(inferred[1]["runtime"], "claude")
            self.assertEqual(inferred[1]["model"], "opus")
            self.assertEqual(inferred[2]["runtime"], "claude")
            self.assertEqual(inferred[2]["model"], "sonnet")
            self.assertEqual(len(lines), 1)
            self.assertIn(path, lines[0])
            self.assertTrue(all(key in lines[0] for key in ("cx", "nc", "ss")))
            self.assertIn("inferred", lines[0])
            self.assertNotIn(command, lines[0])
            with open(path, "rb") as stream:
                self.assertEqual(stream.read(), before)


class TestLegacyLoad(unittest.TestCase):
    def test_tracer(self):
        command = ("codex exec --sandbox read-only --skip-git-repo-check -m {model} "
                   "-c model_reasoning_effort='\"high\"'")
        with tempfile.TemporaryDirectory() as root:
            home = os.path.join(root, "home")
            xdg = os.path.join(root, "xdg")
            os.makedirs(os.path.join(xdg, "ai-kit"))
            path = os.path.join(xdg, "ai-kit", "review-spec.toml")
            text = ('[[reviewers]]\nkey = "cx"\ncli = "codex"\nmodel = "gpt-5.6-sol"\n'
                    f"command = {json.dumps(command)}\n[policy]\nladder = [\"cx\"]\n")
            with open(path, "w", encoding="utf-8") as stream:
                stream.write(text)
            env = {"HOME": home, "XDG_CONFIG_HOME": xdg}
            out, err = io.StringIO(), io.StringIO()
            with open(path, "rb") as stream:
                before = stream.read()
            with mock.patch.dict(os.environ, env), \
                    redirect_stdout(out), redirect_stderr(err):
                self.assertEqual(main(["resolve-reviewers", "--cwd", root, "--cross-ai",
                                       "--quota-path", os.path.join(root, "quota.json")]), 0)
            result = json.loads(out.getvalue())[0]
            self.assertEqual(result["runtime"], "codex")
            self.assertIsNone(result["command"])
            self.assertEqual(result["extra"]["effort"], "high")
            self.assertIn(path, err.getvalue())
            self.assertIn("cx", err.getvalue())
            self.assertEqual(err.getvalue().count("legacy reviewer fields loaded"), 1)
            with open(path, "rb") as stream:
                self.assertEqual(stream.read(), before)

class TestLegacyForms(unittest.TestCase):
    def test_legacy_form_matrix(self):
        cases = [
            ({"key": "a", "native_runtime": "claude", "model": "opus"}, "claude"),
            ({"key": "b", "native_runtime": "unknown", "model": "opus"}, None),
            ({"key": "c", "cli": "opencode", "command": "opencode run -m {model}"}, "opencode"),
            ({"key": "d", "cli": "gemini", "command": "gemini {model}"}, None),
            (
                {
                    "key": "e",
                    "cli": "grok",
                    "command": "grok -p {prompt} -m {model} --output-format plain",
                },
                None,
            ),
            ({"key": "f", "cli": "gemini"}, "gemini"),
            ({"key": "g", "runtime": "cursor-agent"}, "cursor"),
            (
                {
                    "key": "h",
                    "cli": "codex",
                    "model": "",
                    "command": "codex exec --sandbox read-only --skip-git-repo-check -m {model}",
                },
                "codex",
            ),
        ]
        for entry, runtime in cases:
            with self.subTest(entry=entry):
                mapped, notes = normalize_legacy_entry(entry)
                self.assertEqual(mapped.get("runtime"), runtime)
                self.assertTrue(any(entry["key"] in note for note in notes))
        cursor = "cursor-agent -p --output-format text --mode ask --trust --model {model}"
        mapped, _ = normalize_legacy_entry({"key": "cur", "cli": "cursor-agent", "command": cursor})
        self.assertEqual(mapped["runtime"], "cursor")
        self.assertEqual(mapped["cursor_mode"], "ask")
        self.assertNotIn("command", mapped)
        custom = "codex exec --sandbox read-only --skip-git-repo-check -m {model} --profile fast"
        mapped, notes = normalize_legacy_entry({"key": "custom", "cli": "codex", "command": custom})
        self.assertEqual(mapped["command"], custom)
        self.assertTrue(any("runner formula does not reproduce" in note for note in notes))
        mapped, _ = normalize_legacy_entry({"key": "pi", "cli": "pi", "command": "pi x"})
        self.assertEqual(mapped["command"], "pi x")
        mapped, _ = normalize_legacy_entry(
            {
                "key": "keep",
                "cli": "codex",
                "effort": "low",
                "command": (
                    "codex exec --sandbox read-only --skip-git-repo-check -m {model} "
                    "-c model_reasoning_effort='\"high\"'"
                ),
            }
        )
        self.assertEqual(mapped["effort"], "low")

    def test_junk_types_do_not_raise(self):
        for field, value in (
            ("cli", 3),
            ("cli", ["codex"]),
            ("cli", {"a": 1}),
            ("runtime", ["x"]),
            ("native_runtime", {"t": 1}),
            ("command", 5),
        ):
            with self.subTest(field=field, value=value):
                entry = {"key": "junk", field: value}
                mapped, notes = normalize_legacy_entry(entry)
                self.assertEqual(mapped, entry)
                self.assertTrue(any(field in note for note in notes))
        self.assertEqual(normalize_legacy_entry("bad"), ("bad", []))
        entry = {"key": "quote", "cli": "codex", "command": "'unterminated"}
        mapped, notes = normalize_legacy_entry(entry)
        self.assertEqual(mapped["command"], entry["command"])
        self.assertTrue(notes)


class TestInferLegacyNative(unittest.TestCase):
    def test_alias_default_and_explicit_entries(self):
        result, notes = infer_legacy_native(
            [
                {"key": "alias", "model": "opus"},
                {"key": "other", "model": "gpt-5.6-sol"},
                {"key": "runtime", "runtime": "codex", "model": "opus"},
                {"key": "command", "command": "x", "model": "opus"},
            ]
        )
        self.assertEqual(result[0]["runtime"], "claude")
        self.assertEqual(result[1]["model"], "")
        self.assertTrue(any("alias" in n and "inferred" in n for n in notes))
        self.assertTrue(any("other" in n and "gpt-5.6-sol" in n for n in notes))
        self.assertEqual(result[2]["runtime"], "codex")
        self.assertEqual(result[3]["command"], "x")


class TestFactoryTemplates(unittest.TestCase):
    def test_exact_templates_and_rejections(self):
        for runtime, command in (
            ("claude", "claude -p --model {model} --output-format text"),
            ("opencode", "opencode run -m {model}"),
            ("codex", "codex exec --sandbox read-only --skip-git-repo-check -m {model}"),
            ("cursor", "cursor-agent -p --output-format text --mode plan --trust --model {model}"),
        ):
            with self.subTest(runtime=runtime):
                self.assertIsNotNone(_legacy_command_knobs(runtime, command))
                self.assertIsNone(_legacy_command_knobs(runtime, command + " --profile y"))
        self.assertEqual(
            _legacy_command_knobs(
                "cursor", "cursor-agent -p --output-format text --mode ask --trust --model {model}"
            ),
            {"cursor_mode": "ask"},
        )
        self.assertIsNone(
            _legacy_command_knobs("claude", "claude -p --model {model} --output-format text text")
        )
        self.assertIsNone(_legacy_command_knobs("opencode", "opencode run -m {model} -m {model}"))
        self.assertIsNone(
            _legacy_command_knobs("codex", "codex exec --skip-git-repo-check -m {model}")
        )
        self.assertIsNone(
            _legacy_command_knobs(
                "cursor", "cursor-agent -p --output-format text --mode edit --trust --model {model}"
            )
        )
        self.assertIsNone(_legacy_command_knobs("claude", "claude -p --model"))
        codex_base = "codex exec --sandbox read-only --skip-git-repo-check -m {model}"
        for suffix, expected in (
            (" -c model_reasoning_effort='\\\"high\\\"'", {"effort": "high"}),
            (" -c service_tier='\\\"priority\\\"'", {"service_tier": "priority"}),
            (
                " -c model_reasoning_effort='\\\"high\\\"' -c service_tier='\\\"priority\\\"'",
                {"effort": "high", "service_tier": "priority"},
            ),
        ):
            self.assertEqual(_legacy_command_knobs("codex", codex_base + suffix), expected)
        invalid = (
            ("claude", "claude --output-format text -p --model {model}"),
            ("codex", codex_base + " -c model_reasoning_effort=high -c model_reasoning_effort=low"),
            ("codex", codex_base + " -c service_tier=priority -c model_reasoning_effort=high"),
            (
                "codex",
                "codex exec --sandbox read-only --skip-git-repo-check -m {model} -c unknown=x",
            ),
        )
        for runtime, command in invalid:
            self.assertIsNone(_legacy_command_knobs(runtime, command))


class TestLegacyNotes(unittest.TestCase):
    def test_once_and_adjacency_without_mutation(self):
        recorded = []
        _emit_legacy_note("file", ["old: migrated"], recorded.append)
        _emit_legacy_note("file", ["old: migrated"], recorded.append)
        self.assertEqual(len(recorded), 1)
        entries = [{"key": "old", "cli": "codex"}, {"key": "new", "runtime": "pi"}]
        original = [dict(item) for item in entries]
        mapped, notes = normalize_legacy_reviewers(entries)
        self.assertEqual(entries, original)
        self.assertEqual(len(mapped), 2)
        self.assertTrue(all("old" in note for note in notes))
        self.assertFalse(any("new" in note for note in notes))


class TestHostCanSelect(unittest.TestCase):
    def test_host_native_selectors_only(self):
        from ai_kit_spec.routing import host_can_select

        self.assertTrue(host_can_select("claude", "opus", "claude"))
        self.assertFalse(host_can_select("claude", "claude-opus-5-5", "claude"))
        self.assertFalse(host_can_select("claude", "opus", "opencode"))
        self.assertFalse(host_can_select("opencode", "opencode-go/x", "opencode"))
        self.assertFalse(host_can_select(None, "", "claude"))


if __name__ == "__main__":
    unittest.main()
