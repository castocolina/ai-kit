"""36 D-04, D-17 / SPEC R3, R12 c: the per-role order writer."""

import difflib
import io
import json
import os
import sys
import tempfile
import tomllib
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest import mock

_REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(_REPO_ROOT, "skills", "ai-kit-spec-review"))

from ai_kit_spec import cli, config_io, lane_settings, skill_classify


def _lane(key, model, **extra):
    return {"key": key, "runtime": "codex", "model": model, **extra}


LANES = [_lane("a", "placeholder-model-1"), _lane("b", "placeholder-model-2"),
         _lane("x", "placeholder-model-3", purpose="execute"),
         {"key": "c", "runtime": "pi", "model": "placeholder-model-4", "purpose": "both"}]
FULL_DATA_USE = {"data_use": "may_be_kept_or_trained",
                 "data_use_line": "The provider's page says prompts may be kept.",
                 "data_use_source": "https://example.com/data-use", "data_use_read": "2000-01-02",
                 "data_use_label": "reported", "data_use_confirmed": True}


def _render(config, existing=""):
    err = io.StringIO()
    with redirect_stderr(err):
        text = config_io.cfg_render_lanes(config, existing)
    return text, err.getvalue()


def _changed(before, after):
    return [line for line in difflib.ndiff(before.splitlines(), after.splitlines())
            if line.startswith(("- ", "+ "))]


class TestConfigFolderLock(unittest.TestCase):
    def test_confirm_and_render_toml_share_the_lock(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "project", ".aikit", "config.toml")
            with mock.patch.object(config_io, "cfg_folder_lock",
                                   wraps=config_io.cfg_folder_lock) as lock:
                skill_classify.confirm_role(path, "lens-a", "review_lens")
                config_io.cfg_write_toml(path, {"lanes": LANES})
                with open(path, "rb") as stream:
                    parsed = tomllib.load(stream)
                self.assertEqual(parsed["skills"]["roles"], {"lens-a": "review_lens"})
                self.assertTrue(parsed["lanes"]["review"])
                self.assertEqual(lock.call_count, 2)
                config_io.cfg_write_toml(path, {"lanes": LANES})
                skill_classify.confirm_role(path, "edit-a", "edit_lens")
                with open(path, "rb") as stream:
                    parsed = tomllib.load(stream)
                self.assertEqual(parsed["skills"]["roles"],
                                 {"lens-a": "review_lens", "edit-a": "edit_lens"})
                self.assertTrue(parsed["lanes"]["review"])

    def test_lock_leaves_no_folder_after_a_failed_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "project", ".aikit", "config.toml")
            with self.assertRaises(RuntimeError), config_io.cfg_folder_lock(path):
                raise RuntimeError("a refused write")
            self.assertFalse(os.path.exists(os.path.dirname(path)))
            skill_classify.confirm_role(path, "lens-a", "review_lens")
            self.assertTrue(os.path.isfile(path))

    def test_render_toml_cli_holds_the_lock(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = {"HOME": os.path.join(tmp, "home"), "XDG_CONFIG_HOME": os.path.join(tmp, "xdg"),
                   "XDG_CACHE_HOME": os.path.join(tmp, "cache")}
            path = os.path.join(tmp, "project", ".aikit", "config.toml")
            skill_classify.confirm_role(path, "lens-a", "review_lens")
            source = os.path.join(tmp, "config.json")
            with open(source, "w", encoding="utf-8") as stream:
                json.dump({"lanes": LANES}, stream)
            with (mock.patch.object(cli, "cfg_folder_lock", wraps=config_io.cfg_folder_lock)
                  as lock, mock.patch.dict(os.environ, env),
                  redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO())):
                code = cli.main(["render-toml", "--json-config", source, "--out", path],
                                env_fn=lambda: dict(env))
            self.assertEqual(code, 0)
            lock.assert_called_once_with(path)
            with open(path, "rb") as stream:
                parsed = tomllib.load(stream)
            self.assertEqual(parsed["skills"]["roles"], {"lens-a": "review_lens"})
            self.assertTrue(parsed["lanes"]["review"])


class TestRoleOrderWrite(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.cwd = os.path.join(self.tmp.name, "project")
        os.mkdir(self.cwd)
        self.env = {"HOME": os.path.join(self.tmp.name, "home"),
                    "XDG_CONFIG_HOME": os.path.join(self.tmp.name, "xdg"),
                    "XDG_CACHE_HOME": os.path.join(self.tmp.name, "cache")}
        self.warnings = []

    def test_both_orders_written_and_read_back(self):
        policy = {"mode": "single", "review": {"ladder": ["b", "c", "a"]},
                  "execute": {"ladder": ["c", "x"]}}
        path = os.path.join(self.env["XDG_CONFIG_HOME"], "ai-kit", "config.toml")
        config_io.cfg_write_toml(path, {"policy": policy, "lanes": LANES})
        with open(path, encoding="utf-8") as stream:
            text = stream.read()
        parsed = tomllib.loads(text)["lanes"]
        self.assertEqual(parsed["policy"], policy)
        self.assertEqual([e["key"] for e in parsed["review"]], ["a", "b", "c"])
        self.assertEqual([e["key"] for e in parsed["execute"]], ["x", "c"])
        self.assertIn('[lanes.policy]\nmode = "single"\n', text)
        for role in ("review", "execute"):
            self.assertIn(f"# Priority fallback order, {role} lanes", text)
        resolved = config_io.cfg_resolve(self.cwd, self.env, warn_fn=self.warnings.append)
        self.assertEqual(resolved["orders"], {"review": ["b", "c", "a"], "execute": ["c", "x"]})

    def test_ladder_comment_cannot_inject_a_table(self):
        key = "k\n[hooks]\nx = 1"
        lane = {"key": key, "runtime": "pi", "model": "fake/placeholder-model-1",
                "purpose": "review"}
        text, _ = _render({"lanes": [lane], "policy": {"review": {"ladder": [key]}}})
        self.assertEqual(set(tomllib.loads(text)), {"lanes"})
        self.assertIn("#   1. k [hooks] x = 1\n", text)

    def test_byte_preservation_on_a_second_write(self):
        existing = '# top\n[runner.retry]\n  base_s   =  1  # keep\n\n[foo]\nbar = 1\n'
        config = {"policy": {"mode": "single", "review": {"ladder": ["a", "b"]}},
                  "lanes": LANES[:2]}
        first, _ = _render(config, existing)
        config["policy"]["review"]["ladder"] = ["b", "a"]
        second, _ = _render(config, first)
        self.assertTrue(first.startswith(existing) and second.startswith(existing))
        self.assertTrue(all("#" in line or "ladder" in line for line in _changed(first, second)))
        self.assertEqual(_render(config, second)[0], second)

    def test_legacy_file_is_rewritten_per_role(self):
        existing = ('# my top comment\n[runner.retry]\nbase_s = 1\n'
                    '# Priority fallback order (first available reviewer wins the\n'
                    '# primary slot):\n'
                    '#   1. a\n#   2. x\n[lanes.policy]\nmode = "single"\nladder = ["a", "x"]\n')
        policy = {"mode": "single", "review": {"ladder": ["a"]}, "execute": {"ladder": ["x"]}}
        text, _ = _render({"policy": policy, "lanes": [LANES[0], LANES[2]]}, existing)
        self.assertTrue(text.startswith('# my top comment\n[runner.retry]\nbase_s = 1\n'))
        self.assertNotIn('first available reviewer wins', text)
        self.assertEqual(tomllib.loads(text)["lanes"]["policy"], policy)
        self.assertIn('execute lanes (first available', text)

    def test_flat_ladder_input_is_split_with_a_note(self):
        text, err = _render({"policy": {"mode": "single", "ladder": ["a", "x", "ghost"]},
                             "lanes": [LANES[0], LANES[2]]})
        self.assertIn(config_io._FLAT_LADDER_NOTE, err)
        self.assertIn("policy.ladder: dropped key(s) naming no lane ['ghost']", err)
        self.assertEqual(tomllib.loads(text)["lanes"]["policy"],
                         {"mode": "single", "review": {"ladder": ["a"]},
                          "execute": {"ladder": ["x"]}})

    def test_dangling_and_rejected_keys_are_dropped_with_a_warning(self):
        bad = _lane("bad", "placeholder-model-9", route="native")
        text, err = _render({"policy": {"review": {"ladder": ["a", "x", "bad"]}},
                             "lanes": [LANES[0], LANES[2], bad]})
        self.assertIn("rejected lane key(s) ['bad']", err)
        self.assertIn("naming no review lane ['x']", err)
        self.assertEqual(tomllib.loads(text)["lanes"]["policy"]["review"]["ladder"], ["a"])

    def test_duplicate_key_keeps_its_first_place(self):
        text, _ = _render({"policy": {"review": {"ladder": ["a", "b", "a"]}}, "lanes": LANES[:2]})
        self.assertEqual(tomllib.loads(text)["lanes"]["policy"]["review"]["ladder"], ["a", "b"])

    def test_role_without_lane_gets_no_table_and_an_old_one_is_removed(self):
        config = {"policy": {"mode": "single", "review": {"ladder": ["a", "b"]},
                             "execute": {"ladder": ["x"]}}, "lanes": LANES[:3]}
        first, _ = _render(config)
        config["lanes"] = LANES[:2]
        text, err = _render(config, first)
        self.assertNotIn('[lanes.policy.execute]', text)
        self.assertNotIn('execute lanes (first available', text)
        self.assertNotIn('[[lanes.execute]]', text)
        self.assertIn("naming no execute lane ['x']", err)

    def test_unconfigured_role_gets_no_order(self):
        text, _ = _render({"policy": {"review": {"ladder": ["a", "b"]}}, "lanes": LANES[:2]})
        self.assertNotIn("execute", tomllib.loads(text)["lanes"]["policy"])

    def test_inline_role_table_is_rewritten_as_a_header(self):
        existing = '[lanes.policy]\nmode = "single"\nreview = { ladder = ["a"] }\n'
        text, _ = _render({"policy": {"mode": "single", "review": {"ladder": ["a"]}},
                           "lanes": LANES[:1]}, existing)
        self.assertNotIn('review = {', text)
        self.assertEqual(tomllib.loads(text)["lanes"]["policy"]["review"]["ladder"], ["a"])

    def test_writer_rejects_what_the_validator_rejects(self):
        bad = _lane("a", "placeholder-model-1", usage_limited="yes")
        text, err = _render({"policy": {"review": {"ladder": ["a"]}}, "lanes": [bad]})
        self.assertNotIn('[[lanes.review]]', text)
        self.assertIn(config_io.validate_reviewer_fields(bad), err)
        self.assertIn("rejected lane key(s) ['a']", err)

    def test_explicit_none_writes_with_the_warning(self):
        e1 = _lane("e1", "placeholder-model-1", purpose="execute", usage_limited=True,
                   pool="fake:free", **FULL_DATA_USE)
        e2 = _lane("e2", "placeholder-model-2", purpose="execute", usage_limited=True)
        config = {"policy": {"execute": {"ladder": ["e1", "e2"]}}, "lanes": [e1, e2]}
        text, err = _render(config)
        warning = lane_settings.fallback_warnings({"execute": [e1, e2]},
                                                  {"execute": ["e1", "e2"]})[0]
        self.assertIn(warning, err)
        self.assertEqual(len(tomllib.loads(text)["lanes"]["execute"]), 2)

    def test_same_pool_omitted_lane_and_role_cases(self):
        e1 = _lane("e1", "placeholder-model-1", purpose="execute", usage_limited=True,
                   pool="fake:free", **FULL_DATA_USE)
        e2 = _lane("e2", "placeholder-model-2", purpose="execute", pool="fake:free",
                   **FULL_DATA_USE)
        config = {"policy": {"execute": {"ladder": ["e1", "e2"]}}, "lanes": [e1, e2]}
        warning = lane_settings.fallback_warnings({"execute": [e1, e2]},
                                                  {"execute": ["e1", "e2"]})[0]
        self.assertIn(warning, _render(config)[1])
        e2 = _lane("e2", "placeholder-model-2", purpose="execute")
        config["lanes"] = [e1, e2]
        self.assertNotIn("ai-kit-spec: usage_limited", _render(config)[1])
        config["policy"]["execute"]["ladder"] = ["e1"]
        self.assertNotIn("ai-kit-spec: usage_limited", _render(config)[1])
        r1 = _lane("r1", "placeholder-model-1", usage_limited=True, pool="fake:free",
                   **FULL_DATA_USE)
        r2 = _lane("r2", "placeholder-model-2")
        _, err = _render({"policy": {"review": {"ladder": ["r1"]}}, "lanes": [r1, r2]})
        self.assertIn("r1", err)

    def test_no_written_order_cases(self):
        rf = _lane("rf", "placeholder-model-1", usage_limited=True)
        rp = _lane("rp", "placeholder-model-2")
        self.assertIn("rf", _render({"lanes": [rf, rp]})[1])
        ef = _lane("ef", "placeholder-model-1", purpose="execute", usage_limited=True)
        ep = _lane("ep", "placeholder-model-2", purpose="execute")
        self.assertNotIn("ai-kit-spec: usage_limited", _render({"lanes": [ef, ep]})[1])

    def test_render_toml_cli_and_reader_print_the_same_warning(self):
        e1 = _lane("e1", "placeholder-model-1", purpose="execute", usage_limited=True,
                   pool="fake:free", **FULL_DATA_USE)
        e2 = _lane("e2", "placeholder-model-2", purpose="execute", usage_limited=True)
        config = {"policy": {"execute": {"ladder": ["e1", "e2"]}}, "lanes": [e1, e2]}
        source = os.path.join(self.tmp.name, "config.json")
        with open(source, "w", encoding="utf-8") as stream:
            json.dump(config, stream)
        out = os.path.join(self.cwd, ".aikit", "config.toml")
        stderr = io.StringIO()
        with mock.patch.dict(os.environ, self.env), redirect_stdout(io.StringIO()), \
                redirect_stderr(stderr):
            code = cli.main(["render-toml", "--json-config", source, "--out", out],
                            env_fn=lambda: dict(self.env))
        self.assertEqual(code, 0)
        self.assertTrue(os.path.exists(out))
        warning = lane_settings.fallback_warnings({"execute": [e1, e2]},
                                                  {"execute": ["e1", "e2"]})[0]
        self.assertIn(warning, stderr.getvalue())
        config_io.cfg_resolve(self.cwd, self.env, warn_fn=self.warnings.append)
        self.assertIn(warning, self.warnings)
