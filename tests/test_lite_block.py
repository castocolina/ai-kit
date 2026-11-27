"""The lite block beside the plan-writer brief: fake pick, fake catalog, temporary project."""

import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills", "ai-kit-spec-review"))
sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "skills", "ai-kit-spec-execute-superpowers"))

from ai_kit_spec import config_io, executor_pick, jev_names
from ai_kit_spec.config_io import ConfigError
from ai_kit_spec.detection import cache_runtimes_path
from ai_kit_spec_superpowers import cli as superpowers_cli
from ai_kit_spec_superpowers import dispatch_injection

KEYS = ["a/one", "b/two"]
CANDIDATES = [{"key": "a/one", "model": "placeholder-model-1", "runtime": "codex",
               "vendor": "v", "task_affinity": None, "context_limit": None},
              {"key": "b/two", "model": "placeholder-model-2", "runtime": "codex",
               "vendor": "v", "task_affinity": None, "context_limit": None}]

SNAPSHOT = {"clis": {"codex": {"installed": True,
                               "models": ["placeholder-model-1", "placeholder-model-2"]}}}


def catalog(klass):
    facts = {"facts": {"class": {"value": klass}}} if klass else {}
    return {"fake/placeholder-model-2": {
        "runtimes": {"codex": {"model_id": "placeholder-model-2"}}, **facts}}


def picker(key, calls):
    def pick(_candidates, labels, _env, _run):
        calls.append(labels)
        return executor_pick.Pick(
            key, "jev" if key else "default", 0.9 if key else None,
            "" if key else "jev absent")
    return pick


def answers_run(table, calls):
    def run(argv, input="", **kwargs):
        calls.append({"payload": json.loads(input), "cwd": kwargs.get("cwd")})
        items = {
            item["id"]: {"decided_by": "fake", "fake": table[item["id"]]}
            for item in json.loads(input)["items"] if item["id"] in table
        }
        return subprocess.CompletedProcess(argv, 0, stdout=json.dumps({"items": items}), stderr="")
    return run


def raising_assembler(_cwd, _env, cfg_resolve_fn=None):
    raise ConfigError("config.toml", "bad config")


def tree_state(base):
    """Every file path under base with its bytes."""
    return {str(path.relative_to(base)): path.read_bytes()
            for path in sorted(Path(base).rglob("*")) if path.is_file()}


class TestLiteBlockCommand(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = tmp.name
        self.root = os.path.join(tmp.name, "project")
        os.makedirs(os.path.join(self.root, ".aikit", "brief"))
        with open(os.path.join(self.root, ".aikit", "brief", "SKILL.md"), "wb") as handle:
            handle.write(b"# Unit brief\nunit: test\n")
        self.home = os.path.join(tmp.name, "home")
        os.makedirs(self.home)
        self.env = {"HOME": self.home}
        self.runtimes_path = cache_runtimes_path(self.env)
        self.calls = []

    def invoke(self, key, klass, **overrides):
        out, err = io.StringIO(), io.StringIO()
        deps = {
            "assemble_candidates_fn": lambda cwd, env, cfg_resolve_fn=None: (CANDIDATES, KEYS),
            "cache_read_json_fn": lambda path: SNAPSHOT if path == self.runtimes_path
            else catalog(klass),
            "env_fn": lambda: dict(self.env),
            "pick_executor_fn": picker(key, self.calls),
            "stdout": out,
            **overrides,
        }
        with redirect_stderr(err):
            rc = superpowers_cli.main(["lite-block", "--cwd", self.root], **deps)
        return rc, out.getvalue(), err.getvalue()

    def run_lite(self, key, klass):
        rc, out, _err = self.invoke(key, klass)
        self.assertEqual(rc, 0)
        return json.loads(out)

    def lite_path(self):
        return os.path.join(self.root, ".aikit", "brief", "lite-executor.md")

    def test_small_pick_writes_the_block(self):
        result = self.run_lite("b/two", "small")
        self.assertTrue(result["lite"])
        self.assertEqual(result["key"], "b/two")
        self.assertEqual(result["decided_by"], "jev")
        self.assertTrue(result["path"].endswith("lite-executor.md"))
        text = Path(self.lite_path()).read_text(encoding="utf-8")
        self.assertEqual(text, superpowers_cli._lite_text())
        self.assertTrue(text.startswith("# Lite executor block (unverified)"))
        self.assertTrue(text.endswith("Effect on a lite model: unverified.\n"))

    def test_fast_is_lite_at_the_edge(self):
        result = self.run_lite("b/two", "fast")
        self.assertTrue(result["lite"])

    def test_strong_unknown_router_and_missing_class_write_nothing(self):
        for klass in ("coding", "unknown", "router", None):
            result = self.run_lite("b/two", klass)
            self.assertFalse(result["lite"], klass)
            self.assertIsNone(result["path"], klass)
            self.assertFalse(os.path.exists(self.lite_path()), klass)

    def test_no_pick_and_a_strong_head_write_nothing(self):
        result = self.run_lite(None, "small")  # head a/one has no catalog entry: not lite
        self.assertFalse(result["lite"])
        self.assertEqual(result["key"], "a/one")
        self.assertEqual(result["decided_by"], "default")
        self.assertFalse(os.path.exists(self.lite_path()))

    def test_no_pick_and_a_lite_head_write_the_block(self):
        rc, out, _err = self.invoke(
            None, "small",
            assemble_candidates_fn=lambda cwd, env, cfg_resolve_fn=None: (
                CANDIDATES, ["b/two", "a/one"]))
        self.assertEqual(rc, 0)
        result = json.loads(out)
        self.assertTrue(result["lite"])
        self.assertEqual(result["key"], "b/two")
        self.assertEqual(result["decided_by"], "default")
        self.assertEqual(Path(self.lite_path()).read_text(encoding="utf-8"),
                         superpowers_cli._lite_text())

    def test_an_empty_roster_writes_nothing(self):
        rc, out, _err = self.invoke(
            None, "small", assemble_candidates_fn=lambda cwd, env, cfg_resolve_fn=None: ([], []))
        self.assertEqual(rc, 0)
        result = json.loads(out)
        self.assertFalse(result["lite"])
        self.assertIsNone(result["key"])
        self.assertFalse(os.path.exists(self.lite_path()))

    def test_stale_file_is_removed(self):
        Path(self.lite_path()).write_text(superpowers_cli._lite_text(), encoding="utf-8")
        result = self.run_lite("b/two", "coding")
        self.assertFalse(result["lite"])
        self.assertIsNone(result["path"])
        self.assertTrue(result["removed_stale"])
        self.assertFalse(os.path.exists(self.lite_path()))

    def test_brief_bytes_and_file_set_unchanged(self):
        brief = os.path.join(self.root, ".aikit", "brief", "SKILL.md")
        before_files = tree_state(self.root)
        before_brief = Path(brief).read_bytes()
        result = self.run_lite("b/two", "small")
        self.assertTrue(result["lite"])
        after_files = tree_state(self.root)
        lite_rel = os.path.join(".aikit", "brief", "lite-executor.md")
        self.assertEqual(set(after_files), set(before_files) | {lite_rel})
        self.assertEqual(Path(brief).read_bytes(), before_brief)

    def test_pick_sees_the_plan_label(self):
        self.invoke("b/two", "small")
        for labels in self.calls:
            for label in labels:
                self.assertEqual(label["task"], "plan")

    def test_skip_route_lane_is_never_offered(self):
        candidates = [*CANDIDATES, {**CANDIDATES[1], "key": "c/three", "runtime": "pi"}]
        keys = [*KEYS, "c/three"]
        self.invoke("b/two", "small",
                    assemble_candidates_fn=lambda cwd, env, cfg_resolve_fn=None: (candidates, keys))
        self.assertEqual(len(self.calls[-1]), 2)

    def test_config_error_exits_2(self):
        rc, out, err = self.invoke("b/two", "small", assemble_candidates_fn=raising_assembler)
        self.assertEqual(rc, 2)
        self.assertIn("config error", err)
        self.assertEqual(out, "")
        self.assertFalse(os.path.exists(self.lite_path()))

    def test_brief_folder_outside_the_project_is_refused(self):
        outside = os.path.join(self.tmp, "outside")
        os.makedirs(os.path.join(outside, "brief"))
        stale = os.path.join(outside, "brief", "lite-executor.md")
        Path(stale).write_text("stale", encoding="utf-8")
        brief = os.path.join(self.root, ".aikit", "brief", "SKILL.md")
        shutil.move(brief, os.path.join(self.tmp, "aside-brief.md"))
        os.rmdir(os.path.join(self.root, ".aikit", "brief"))
        os.rmdir(os.path.join(self.root, ".aikit"))
        os.symlink(outside, os.path.join(self.root, ".aikit"))
        before = tree_state(outside)
        rc, out, err = self.invoke("b/two", "small")
        self.assertEqual(rc, 2)
        self.assertEqual(out, "")
        self.assertIn("ai-kit-spec: lite-block: brief folder outside the project", err)
        self.assertEqual(Path(stale).read_text(encoding="utf-8"), "stale")
        self.assertEqual(tree_state(outside), before)

    def test_pending_config_and_cache_stay_untouched(self):
        old_roster = '[[reviewers]]\nkey = "u"\nruntime = "codex"\nmodel = "placeholder-model-1"\n'
        Path(os.path.join(self.root, ".aikit", "review-spec.toml")).write_text(
            old_roster, encoding="utf-8")
        user_legacy = os.path.join(self.home, ".config", "ai-kit", "review-spec.toml")
        os.makedirs(os.path.dirname(user_legacy))
        Path(user_legacy).write_text(old_roster, encoding="utf-8")
        before = tree_state(self.tmp)
        rc, out, _err = self.invoke(
            None, "small", assemble_candidates_fn=dispatch_injection.assemble_candidates)
        self.assertEqual(rc, 0)
        self.assertFalse(json.loads(out)["lite"])
        self.assertEqual(tree_state(self.tmp), before)

    def test_active_roster_writes_only_the_lite_file(self):
        roster = (
            '[[lanes.execute]]\nkey = "lane-a"\nruntime = "codex"\n'
            'model = "fake/placeholder-model-1"\npurpose = "execute"\n\n'
            '[[lanes.execute]]\nkey = "lane-b"\nruntime = "codex"\n'
            'model = "fake/placeholder-model-2"\npurpose = "execute"\n\n'
            '[lanes.policy.execute]\nladder = ["lane-a", "lane-b"]\n'
        )
        Path(config_io.cfg_local_path(self.root)).write_text(roster, encoding="utf-8")
        before = tree_state(self.root)
        calls = []
        snapshot = {"clis": {"codex": {"installed": True, "models": [
            "fake/placeholder-model-1", "fake/placeholder-model-2"]}}}
        entries = {"fake/placeholder-model-2": {
            "runtimes": {"codex": {"model_id": "fake/placeholder-model-2"}},
            "facts": {"class": {"value": "small"}}}}
        with mock.patch.object(jev_names, "find_jev", return_value="fake-entry"):
            rc, out, _err = self.invoke(
                None, "small",
                assemble_candidates_fn=dispatch_injection.assemble_candidates,
                pick_executor_fn=executor_pick.pick_executor,
                run_fn=answers_run({"x0": {"choice": "c2", "top": 0.95}}, calls),
                cache_read_json_fn=lambda path: snapshot if path == self.runtimes_path
                else entries)
        self.assertEqual(rc, 0)
        result = json.loads(out)
        self.assertTrue(result["lite"])
        self.assertEqual(result["key"], "lane-b")
        self.assertEqual(result["decided_by"], "jev")
        self.assertEqual(len(calls), 1)
        after = tree_state(self.root)
        lite_rel = os.path.join(".aikit", "brief", "lite-executor.md")
        self.assertEqual(set(after), set(before) | {lite_rel})
        for rel, payload in before.items():
            self.assertEqual(after[rel], payload)


class TestLiteBlockDocs(unittest.TestCase):
    REPO = Path(__file__).resolve().parents[1]

    def _flat(self, *parts):
        return " ".join(self.REPO.joinpath(*parts).read_text(encoding="utf-8").split())

    def test_block_text_is_pinned(self):
        self.assertEqual(
            superpowers_cli._lite_text().splitlines(),
            [
                "# Lite executor block (unverified)",
                "",
                "The executor picked for this plan is a lite coding model. "
                "Write every task for it:",
                "- One file group per task; keep each task small.",
                "- Give the exact command, path and expected output for every step.",
                "- State every value the task needs; leave nothing to infer.",
                "- Name the test command and its pass signal in each task.",
                "",
                "Effect on a lite model: unverified.",
            ],
        )

    def test_reference_names_selector_and_router_limit(self):
        flat = self._flat(
            "skills", "ai-kit-spec-execute-superpowers", "references", "lite-block.md")
        self.assertIn("`small` or `fast`", flat)
        self.assertIn("A router alias reads class `router`", flat)
        self.assertIn("It never writes `.aikit/brief/SKILL.md`", flat)
        self.assertIn("with no jev pick", flat)
        self.assertIn("the default order's first lane", flat)
        self.assertNotIn("there is no pick and no file", flat)

    def test_agents_rail_hands_over_only_a_current_lite_file(self):
        flat = self._flat("AGENTS.md")
        self.assertIn(
            "`python3 <adapter skill>/ai-kit-spec-superpowers.py lite-block --cwd .`", flat)
        self.assertIn(
            'when it exits 0 with `"lite": true`, hand `.aikit/brief/lite-executor.md` too',
            flat,
        )
        self.assertNotIn("lite-executor.md` too when it exists", flat)


if __name__ == "__main__":
    unittest.main()
