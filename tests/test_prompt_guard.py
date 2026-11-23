"""39-03 / SPEC R8: embedded-value validation and its closed reasons."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
FIXTURE = REPO / "tests" / "fixtures" / "prompt_control_chars.json"
sys.path.insert(0, str(REPO / "skills" / "ai-kit-spec-review"))
from ai_kit_spec import prompt_guard


def _touch(path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    Path(path).write_text("x\n", encoding="utf-8")


def _layout(root: str) -> dict:
    repo = os.path.join(root, "repo")
    sibling = os.path.join(root, "repo-other")
    skills = os.path.join(root, "skills")
    secret = os.path.join(root, "outside", "secret.md")
    for path in (os.path.join(repo, "doc.md"), os.path.join(sibling, "x.md"),
                 os.path.join(skills, "lens-a", "SKILL.md"), secret):
        _touch(path)
    os.symlink(secret, os.path.join(repo, "link.md"))
    return {"repo": repo, "sibling": sibling, "skills": skills, "root": root}


class TestControlCharFixture(unittest.TestCase):
    def test_fixture_matches_the_rule(self):
        doc = json.loads(FIXTURE.read_text(encoding="utf-8"))
        self.assertEqual(set(doc), {"rejected", "accepted"})
        self.assertEqual(len(doc["rejected"]), 87)
        self.assertEqual(len(doc["accepted"]), 15)
        for key, expected in (("rejected", True), ("accepted", False)):
            for pair in doc[key]:
                self.assertEqual(len(pair), 2)
                self.assertTrue(all(isinstance(item, str) for item in pair))
                code, _name = pair
                with self.subTest(code=code):
                    self.assertEqual(prompt_guard.is_control_char(chr(int(code, 16))), expected)

    def test_fixture_is_exhaustive(self):
        doc = json.loads(FIXTURE.read_text(encoding="utf-8"))
        self.assertEqual(
            {cp for cp in range(0x110000) if prompt_guard.is_control_char(chr(cp))},
            {int(h, 16) for h, _ in doc["rejected"]},
        )

    def test_escape_value(self):
        self.assertEqual(prompt_guard.escape_value("a\tb" + chr(0x2028) + "c" + chr(0xFEFF) + "d"),
                         "a\\u0009b\\u2028c\\ufeffd")
        plain = "plain " + chr(0xE9) + " " + chr(0xAD)
        self.assertEqual(prompt_guard.escape_value(plain), plain)


class TestRepoRoot(unittest.TestCase):
    def test_git_top_level_else_realpath(self):
        with tempfile.TemporaryDirectory() as top:
            sub = os.path.join(top, "sub")
            os.mkdir(sub)
            calls = []

            def fake(argv, **_kwargs):
                calls.append(argv)
                return subprocess.CompletedProcess(argv, 0, stdout=top + "\n", stderr="")

            def failed(argv, **_kwargs):
                return subprocess.CompletedProcess(argv, 128, stdout="", stderr="")

            def raising(*_args, **_kwargs):
                raise OSError("fake")

            self.assertEqual(prompt_guard.repo_root(sub, run_fn=fake), os.path.realpath(top))
            self.assertEqual(calls, [["git", "-C", sub, "rev-parse", "--show-toplevel"]])
            self.assertEqual(prompt_guard.repo_root(sub, run_fn=failed), os.path.realpath(sub))
            self.assertEqual(prompt_guard.repo_root(sub, run_fn=raising), os.path.realpath(sub))


class TestValidateValues(unittest.TestCase):
    def test_eight_spec_fixtures(self):
        with tempfile.TemporaryDirectory() as directory:
            root = os.path.realpath(directory)
            layout = _layout(root)
            repo, sibling, skills = layout["repo"], layout["sibling"], layout["skills"]
            doc = os.path.join(repo, "doc.md")
            sibling_doc = os.path.join(sibling, "x.md")
            lens = os.path.join(skills, "lens-a", "SKILL.md")
            link = os.path.join(repo, "link.md")
            result = prompt_guard.validate_values([
                ("plan", os.path.join(repo, "doc\n.md")),
                ("spec", os.path.join(repo, "doc" + chr(0x202E) + ".md")),
                ("files[0]", ""),
                ("files[1]", 42),
                ("files[2]", link),
                ("files[3]", sibling_doc),
                ("lens", lens),
                ("files[4]", doc),
            ], repo, [skills])
            self.assertEqual(result, [
                {"position": "plan", "reason": "value_control_char",
                 "shown": os.path.join(repo, "doc\\u000a.md")},
                {"position": "spec", "reason": "value_control_char",
                 "shown": os.path.join(repo, "doc\\u202e.md")},
                {"position": "files[0]", "reason": "path_unresolvable", "shown": ""},
                {"position": "files[1]", "reason": "path_unresolvable",
                 "shown": "<not a string: int>"},
                {"position": "files[2]", "reason": "path_outside_roots", "shown": link},
                {"position": "files[3]", "reason": "path_outside_roots", "shown": sibling_doc},
            ])

    def test_repo_root_itself_and_relative_values(self):
        with tempfile.TemporaryDirectory() as directory:
            layout = _layout(os.path.realpath(directory))
            repo = layout["repo"]
            self.assertEqual(prompt_guard.validate_values([("root", repo), ("rel", "doc.md")],
                                                          repo, []), [])
            up = os.path.join("..", "repo-other", "x.md")
            self.assertEqual(prompt_guard.validate_values([("up", up)], repo, []), [
                {"position": "up", "reason": "path_outside_roots", "shown": up},
            ])

    def test_missing_list_and_whitespace(self):
        with tempfile.TemporaryDirectory() as repo:
            self.assertEqual(prompt_guard.validate_values(None, repo, []), [  # type: ignore[arg-type]
                {"position": "values", "reason": "path_unresolvable",
                 "shown": "<not a list: NoneType>"},
            ])
            self.assertEqual(prompt_guard.validate_values([("w", "   ")], repo, []), [
                {"position": "w", "reason": "path_unresolvable", "shown": "   "},
            ])
            self.assertEqual(prompt_guard.validate_values([("t", "\t")], repo, []), [
                {"position": "t", "reason": "value_control_char", "shown": "\\u0009"},
            ])

    def test_extra_roots_cover_their_call_only(self):
        with tempfile.TemporaryDirectory() as directory:
            layout = _layout(os.path.realpath(directory))
            repo = layout["repo"]
            run = os.path.join(layout["root"], "run")
            path = os.path.join(run, "mcp.json")
            _touch(path)
            values: list[tuple[str, object]] = [("mcp_config", path)]
            self.assertEqual(prompt_guard.validate_values(values, repo, [], extra_roots=(run,)), [])
            self.assertEqual(prompt_guard.validate_values(values, repo, []), [
                {"position": "mcp_config", "reason": "path_outside_roots", "shown": path},
            ])

    def test_new_file_inside_repo_passes(self):
        with tempfile.TemporaryDirectory() as directory:
            layout = _layout(os.path.realpath(directory))
            repo, root = layout["repo"], layout["root"]
            self.assertEqual(prompt_guard.validate_values(
                [("new", os.path.join(repo, "new", "file.py"))], repo, []), [])
            outside = os.path.join(root, "outside", "new.py")
            self.assertEqual(prompt_guard.validate_values([("new", outside)], repo, []), [
                {"position": "new", "reason": "path_outside_roots", "shown": outside},
            ])

    def test_shown_redacts_secrets(self):
        with tempfile.TemporaryDirectory() as directory:
            layout = _layout(os.path.realpath(directory))
            secret = "ghp_" + "a" * 20
            path = os.path.join(layout["root"], "outside", secret, "x.md")
            result = prompt_guard.validate_values([("leak", path)], layout["repo"], [])
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0]["reason"], "path_outside_roots")
            self.assertIn("[redacted]", result[0]["shown"])
            self.assertNotIn(secret, result[0]["shown"])

    def test_non_nfc_name_compared_as_given(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = _layout(os.path.realpath(directory))["repo"]
            name = "e" + chr(0x301) + ".md"
            path = os.path.join(repo, name)
            _touch(path)
            self.assertEqual(prompt_guard.validate_values([("nfd", path)], repo, []), [])
            self.assertEqual(prompt_guard.escape_value(name), name)

    def test_relative_values_follow_the_child_base(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = _layout(os.path.realpath(directory))["repo"]
            sub = os.path.join(repo, "sub")
            os.mkdir(sub)
            self.assertEqual(prompt_guard.validate_values([("rel", "link.md")], repo, []), [
                {"position": "rel", "reason": "path_outside_roots", "shown": "link.md"},
            ])
            self.assertEqual(prompt_guard.validate_values(
                [("rel", "link.md")], repo, [], base=sub), [])
            up = os.path.join("..", "link.md")
            self.assertEqual(prompt_guard.validate_values([("up", up)], repo, [], base=sub), [
                {"position": "up", "reason": "path_outside_roots", "shown": up},
            ])

    def test_symlink_loop_is_unresolvable(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = _layout(os.path.realpath(directory))["repo"]
            os.symlink("loop-b", os.path.join(repo, "loop-a"))
            os.symlink("loop-a", os.path.join(repo, "loop-b"))
            path = os.path.join(repo, "loop-a")
            self.assertEqual(prompt_guard.validate_values([("loop", path)], repo, []), [
                {"position": "loop", "reason": "path_unresolvable", "shown": path},
            ])

    def test_refusal_reasons_closed(self):
        self.assertEqual(prompt_guard.REFUSAL_REASONS, (
            "prompt_over_window", "value_control_char", "path_outside_roots", "path_unresolvable",
        ))
