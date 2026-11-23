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
TEMPLATE = REPO / "skills" / "ai-kit-spec-review" / "references" / "cross-ai.mjs"
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "skills" / "ai-kit-spec-review"))
from ai_kit_spec import config_io, prompt_guard
from ai_kit_spec.model_catalog import CATALOG_SCHEMA_VERSION
from ai_kit_spec.runner_facts import read_runner_describe

from tests.cross_ai_selftest import _real_node_executable, require_real_node

NODE = _real_node_executable()

PI_ROW = {
    "fake/placeholder-model-1": {
        "runtimes": {"pi": {
            "model_id": "fake/placeholder-model-1",
            "context": {
                "value": 4000, "label": "measured", "source": "pi listing",
                "fetched_at": "2026-01-01T00:00:00Z",
            },
        }},
    },
}


def _write_catalog(cache_home: str, entries: dict) -> None:
    directory = os.path.join(cache_home, "ai-kit", "spec")
    os.makedirs(directory, exist_ok=True)
    path = os.path.join(directory, "model-catalog.json")
    with open(path, "w", encoding="utf-8") as handle:
        json.dump({"_meta": {"schema_version": CATALOG_SCHEMA_VERSION}, **entries}, handle)


def _window_env(root: str) -> tuple[dict, str]:
    home, cache, project = (os.path.join(root, name) for name in ("home", "cache", "proj"))
    for path in (home, cache, project):
        os.makedirs(path)
    return {"HOME": home, "XDG_CACHE_HOME": cache}, project


def _user_config(env: dict, text: str) -> None:
    path = os.path.join(env["HOME"], ".config", "ai-kit", "config.toml")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    Path(path).write_text(text, encoding="utf-8")


class TestWindowCheck(unittest.TestCase):
    def test_estimate_tokens(self):
        with tempfile.TemporaryDirectory():
            for text, expected in (("", 0), ("abcd", 1), ("abcde", 2),
                                   (chr(0xE9) * 2, 1), (chr(0x1F600) * 3, 3)):
                self.assertEqual(prompt_guard.estimate_tokens(text), expected)

    def test_catalog_window_refuses_over_and_passes_equal(self):
        with tempfile.TemporaryDirectory() as root:
            env, cwd = _window_env(root)
            _write_catalog(env["XDG_CACHE_HOME"], PI_ROW)
            window = prompt_guard.window_for("pi", "fake/placeholder-model-1:high", env, cwd, False)
            self.assertEqual(window, {
                "value": 4000, "label": "measured", "source": "pi listing", "note": None,
            })
            self.assertIsNone(prompt_guard.check_window(4000, window))
            self.assertEqual(prompt_guard.check_window(4001, window), {
                "status": "refused", "reason": "prompt_over_window", "detail": {
                    "estimate": 4001, "window": 4000, "label": "measured", "source": "pi listing",
                    "bytes_per_token": 4, "estimate_label": "estimated, judged",
                },
            })

    def test_live_override_beats_catalog(self):
        with tempfile.TemporaryDirectory() as root:
            env, cwd = _window_env(root)
            _write_catalog(env["XDG_CACHE_HOME"], PI_ROW)
            _user_config(env, '[[models.context]]\nruntime = "pi"\n'
                         'model = "fake/placeholder-model-1"\ntokens = 9000\n')
            window = prompt_guard.window_for("pi", "fake/placeholder-model-1", env, cwd, False)
            self.assertEqual(window, {
                "value": 9000, "label": "user-stated", "source": "[[models.context]]", "note": None,
            })

    def test_no_entry_is_unknown_and_never_capped(self):
        with tempfile.TemporaryDirectory() as root:
            env, cwd = _window_env(root)
            window = prompt_guard.window_for("pi", "fake/placeholder-model-2", env, cwd, False)
            self.assertEqual(window, {
                "value": None, "label": "unknown", "source": None, "note": None,
            })
            self.assertIsNone(prompt_guard.check_window(10**9, window))


    def test_context_form_applied(self):
        with tempfile.TemporaryDirectory() as root:
            env, cwd = _window_env(root)
            cache = env["XDG_CACHE_HOME"]
            _write_catalog(cache, PI_ROW)
            unknown = {"value": None, "label": "unknown", "source": None,
                       "note": "context_form_applied"}
            window = prompt_guard.window_for("pi", "fake/placeholder-model-1", env, cwd, True)
            self.assertEqual(window, unknown)
            self.assertIsNone(prompt_guard.check_window(10**9, window))
            _user_config(env, '[[models.context]]\nruntime = "pi"\n'
                         'model = "fake/placeholder-model-1"\ntokens = 9000\n')
            self.assertEqual(prompt_guard.window_for(
                "pi", "fake/placeholder-model-1", env, cwd, True), {
                    "value": 9000, "label": "user-stated", "source": "[[models.context]]",
                    "note": None,
                })
            _user_config(env, "")
            row = {"fake/placeholder-model-1": {"runtimes": {"pi": {
                "model_id": "fake/placeholder-model-1", "context": {
                    "value": 5000, "label": "user-stated", "source": "[[models.context]]",
                },
            }}}}
            _write_catalog(cache, row)
            self.assertEqual(prompt_guard.window_for(
                "pi", "fake/placeholder-model-1", env, cwd, True), unknown)
            self.assertEqual(prompt_guard.window_for(
                "pi", "fake/placeholder-model-1", env, cwd, False), {
                    "value": 5000, "label": "user-stated", "source": "[[models.context]]",
                    "note": None,
                })

    def test_invalid_catalog_values_are_unknown(self):
        with tempfile.TemporaryDirectory() as root:
            env, cwd = _window_env(root)
            for bad in (0, -5, "4000", True, 4000.0, None):
                with self.subTest(bad=bad):
                    row = {"fake/placeholder-model-1": {"runtimes": {"pi": {
                        "model_id": "fake/placeholder-model-1",
                        "context": {"value": bad, "label": "measured", "source": "models.dev"},
                    }}}}
                    _write_catalog(env["XDG_CACHE_HOME"], row)
                    self.assertEqual(prompt_guard.window_for(
                        "pi", "fake/placeholder-model-1", env, cwd, False), {
                            "value": None, "label": "unknown", "source": None,
                            "note": None if bad is None else "catalog_value_invalid",
                        })
            _write_catalog(env["XDG_CACHE_HOME"], {"fake/placeholder-model-1": {
                "runtimes": {"pi": {"model_id": "fake/placeholder-model-1"}},
            }})
            self.assertEqual(prompt_guard.window_for(
                "pi", "fake/placeholder-model-1", env, cwd, False), {
                    "value": None, "label": "unknown", "source": None, "note": None,
                })

    def test_unlabeled_catalog_value_still_refuses(self):
        with tempfile.TemporaryDirectory() as root:
            env, cwd = _window_env(root)
            _write_catalog(env["XDG_CACHE_HOME"], {"fake/placeholder-model-1": {
                "runtimes": {"pi": {"model_id": "fake/placeholder-model-1",
                                    "context": {"value": 100}}},
            }})
            window = prompt_guard.window_for("pi", "fake/placeholder-model-1", env, cwd, False)
            self.assertEqual(window, {
                "value": 100, "label": "unknown", "source": None, "note": None,
            })
            result = prompt_guard.check_window(101, window)
            assert result is not None
            self.assertEqual(result["reason"], "prompt_over_window")
            self.assertEqual(result["detail"]["label"], "unknown")

    def test_catalog_provenance_checked(self):
        with tempfile.TemporaryDirectory() as root:
            env, cwd = _window_env(root)
            secret = "ghp_" + "a" * 20
            _write_catalog(env["XDG_CACHE_HOME"], {"fake/placeholder-model-1": {
                "runtimes": {"pi": {"model_id": "fake/placeholder-model-1", "context": {
                    "value": 700, "label": "made-up", "source": "listing " + secret,
                }}},
            }})
            window = prompt_guard.window_for("pi", "fake/placeholder-model-1", env, cwd, False)
            self.assertEqual((window["value"], window["label"], window["note"]),
                             (700, "unknown", None))
            self.assertIn("[redacted]", window["source"])
            self.assertNotIn(secret, window["source"])
            result = prompt_guard.check_window(701, window)
            assert result is not None
            self.assertNotIn(secret, result["detail"]["source"])

    def test_id_carried_bracket_is_unknown(self):
        with tempfile.TemporaryDirectory() as root:
            env, cwd = _window_env(root)
            row = {"fake-model-9": {"runtimes": {"cursor": {
                "model_id": "fake-model-9", "context": {
                    "value": 4000, "label": "measured", "source": "fixture",
                },
            }}}}
            _write_catalog(env["XDG_CACHE_HOME"], {**PI_ROW, **row})
            bracket = "fake-model-9[context=long]"
            self.assertEqual(prompt_guard.window_for("cursor", bracket, env, cwd, False), {
                "value": None, "label": "unknown", "source": None, "note": "context_form_applied",
            })
            self.assertEqual(prompt_guard.window_for("cursor", "fake-model-9", env, cwd, False)
                             ["value"], 4000)
            # A bracket of keys other than context keeps the catalog value; any other form
            # (a context key, a bare value) stays unknown, never capped.
            for suffix, value in (("[effort=high]", 4000), ("[effort=high,fast=false]", 4000),
                                  ("[effort=high,context=1m]", None), ("[1m]", None),
                                  ("[=x]", None)):
                self.assertEqual(prompt_guard.window_for(
                    "cursor", "fake-model-9" + suffix, env, cwd, False)["value"], value, suffix)
            self.assertEqual(prompt_guard.window_for(
                "pi", "fake/placeholder-model-1:high", env, cwd, False)["value"], 4000)
            _user_config(env, '[[models.context]]\nruntime = "cursor"\n'
                         'model = "fake-model-9"\ntokens = 9000\n')
            window = prompt_guard.window_for("cursor", bracket, env, cwd, False)
            self.assertEqual((window["value"], window["label"]), (9000, "user-stated"))

    def test_malformed_config_raises(self):
        with tempfile.TemporaryDirectory() as root:
            env, cwd = _window_env(root)
            _user_config(env, '[[models.context]]\nruntime = "pi"\n')
            with self.assertRaises(config_io.ConfigError):
                prompt_guard.window_for("pi", "fake/placeholder-model-1", env, cwd, False)

    def test_two_lanes_independent(self):
        with tempfile.TemporaryDirectory() as root:
            env, cwd = _window_env(root)
            row = {"fake/placeholder-model-3": {"runtimes": {"opencode": {
                "model_id": "fake/placeholder-model-3", "context": {
                    "value": 8000, "label": "measured", "source": "models.dev",
                },
            }}}}
            _write_catalog(env["XDG_CACHE_HOME"], {**PI_ROW, **row})
            result = prompt_guard.check_window(5000, prompt_guard.window_for(
                "pi", "fake/placeholder-model-1", env, cwd, False))
            assert result is not None
            self.assertEqual(result["reason"], "prompt_over_window")
            self.assertIsNone(prompt_guard.check_window(5000, prompt_guard.window_for(
                "opencode", "fake/placeholder-model-3", env, cwd, False)))
            with self.assertRaises(ValueError):
                prompt_guard.refusal_record("made_up", {})


class TestRefusalDisjoint(unittest.TestCase):
    def setUp(self):
        if NODE is None:
            require_real_node(self, "node not on PATH: the disjointness checks need the real node")

    def test_reasons_disjoint_from_runner_lists(self):
        obj = read_runner_describe(NODE, str(TEMPLATE))["describe"]
        assert isinstance(obj, dict)
        # The lens-note half is added by 39-11.
        for name, values in (("reasons", set(obj["reasons"])),
                             ("classes", set(obj["classes"])),
                             ("findings", {item["code"] for item in obj["findings"]})):
            with self.subTest(name=name):
                self.assertTrue(values)
                self.assertEqual(set(prompt_guard.REFUSAL_REASONS) & values, set())

    def test_refused_exit_is_free(self):
        obj = read_runner_describe(NODE, str(TEMPLATE))["describe"]
        assert isinstance(obj, dict)
        statuses = set(obj["statuses"].values())
        self.assertTrue(statuses)
        self.assertEqual(prompt_guard.REFUSED_EXIT, 65)
        self.assertNotIn(65, statuses)


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
