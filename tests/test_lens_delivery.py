"""39-11: lens delivery and the MCP pick (SPEC R5, R1 amendment)."""

import ast
import copy
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

_REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(_REPO_ROOT, "skills", "ai-kit-spec-review"))

from ai_kit_spec import runner_facts, tooling_guidance
from ai_kit_spec.capability_block import HOST_CANNOT_LOAD, lane_facts
from ai_kit_spec.lens_delivery import (
    FILE_READ_MAX,
    LENS_NOTES,
    SKILL_NAME_RE,
    UI_EXTENSIONS,
    check_lens,
    lens_set,
    mcp_pick,
    plan_lenses,
    write_mcp_file,
)
from ai_kit_spec.prompt_guard import REFUSAL_REASONS
from ai_kit_spec.runner_dispatch import RunnerSeams, RunnerSpec, child_env, print_argv_lines

from tests.cross_ai_selftest import require_real_node


def skill(root, dir_name, data: bytes) -> str:
    directory = Path(root) / dir_name
    directory.mkdir(parents=True)
    (directory / "SKILL.md").write_bytes(data)
    return str(directory)


class TestLensChecks(unittest.TestCase):
    def test_check_lens_runner_refusals(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "skills"
            repo = Path(tmp) / "repo"
            root.mkdir()
            repo.mkdir()
            outside = Path(tmp) / "elsewhere"
            outside.mkdir()
            (outside / "SKILL.md").write_text("body", encoding="utf-8")
            cases = [
                ("lens-a", b"---\nname: lens-a\n---\nbody", None, "lens-a"),
                ("empty", b"", "not_present", None),
                ("bare", None, "not_present", None),
                ("limit", b"---\nname: lens-b\n---\n".ljust(65536, b"x"), None, "lens-b"),
                ("too-large", b"x" * 65537, "path_rejected", None),
                ("invalid", b"\xff\xfe bad", "path_rejected", None),
                ("bom", b"\xef\xbb\xbf---\nname: lens-a\n---\n", "path_rejected", None),
                ("Bad_Name", b"body", "path_rejected", None),
                ("Bad_Other", b"---\nname: lens-b\n---\n", None, "lens-b"),
                ("Other_C", b"---\r\nname: other-a\r\n---\r\nbody\r\n", None, "other-a"),
                ("close", b"</skill>", "path_rejected", None),
                ("lens-\nx", b"body", "path_rejected", None),
            ]
            for name, data, note, expected_name in cases:
                with self.subTest(name=name):
                    directory = root / name
                    directory.mkdir()
                    if data is not None:
                        (directory / "SKILL.md").write_bytes(data)
                    result = check_lens({"name": name, "path": str(directory)}, str(repo),
                                        [str(root)])
                    self.assertEqual(result["note"], note)
                    self.assertEqual(result["skill_name"], expected_name)
                    if note:
                        self.assertIn(note, LENS_NOTES)
            (root / "directory" / "SKILL.md").mkdir(parents=True)
            (root / "link").mkdir()
            (root / "link" / "SKILL.md").symlink_to(outside / "SKILL.md")
            for path, note in ((root / "missing", "not_present"),
                               (root / "directory", "path_rejected"),
                               (outside, "path_rejected"), (root / "link", "path_rejected"),
                               (None, "built_in_no_file")):
                with self.subTest(path=path):
                    result = check_lens({"name": "lens-a", "path": str(path) if path else None},
                                        str(repo), [str(root)])
                    self.assertEqual(result["note"], note)
                    self.assertIn(note, LENS_NOTES)

    def test_plan_lenses_budget(self):
        def lens(name, size):
            return {"name": name, "path": "/fake/" + name, "note": None, "skill_name": name,
                    "aliases": [name], "bytes": size}

        first = lens("lens-a", 100)
        duplicate = lens("lens-b", 100)
        duplicate["skill_name"] = "lens-a"
        crossed = {**first, "skill_name": "lens-b", "aliases": ["lens-a", "lens-b"]}
        other = {**duplicate, "aliases": ["lens-a", "other-a"]}
        for rows in ([first, duplicate], [crossed, other]):
            original = copy.deepcopy(rows)
            delivered, skipped = plan_lenses(rows, 0, None, None)
            self.assertEqual(delivered, [rows[0]])
            self.assertEqual(skipped, [{**rows[1], "note": "path_rejected"}])
            self.assertEqual(rows, original)
        large, small = lens("lens-a", 80000), lens("lens-b", 400)
        delivered, skipped = plan_lenses([large, small], 4000, 4000, None)
        self.assertEqual(delivered, [small])
        self.assertEqual(skipped, [{**large, "note": "over_window"}])
        self.assertEqual(plan_lenses([large, small], 4000, None, None), ([large, small], []))
        for window, cap in ((1000, None), (None, 5000)):
            base = 3000 if window else 4000
            for size, fits in ((1000, True), (1001, False)):
                row = lens("lens-a", size)
                delivered, skipped = plan_lenses([row], base, window, cap)
                self.assertEqual(delivered, [row] if fits else [])
                self.assertEqual(skipped, [] if fits else [{**row, "note": "over_window"}])
        rejected = {**large, "note": "path_rejected"}
        self.assertEqual(plan_lenses([rejected, small], 0, 100, None), ([small], [rejected]))
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "skills"
            path = skill(root, "lens-a", b"x" * 20000)
            checked = check_lens({"name": "lens-a", "path": path}, tmp, [str(root)])
            self.assertIsNone(checked["note"])
            delivered, skipped = plan_lenses([checked], 1000, 4000, None)
            self.assertEqual(delivered, [])
            self.assertEqual(skipped, [{**checked, "note": "over_window"}])

    def test_lens_set_order_and_ui(self):
        rows = [{"name": name, "role": role, "path": path} for name, role, path in (
            ("ui-a", "ui_lens", "A/ui-a"), ("lens-b", "review_lens", "A/lens-b"),
            ("lens-a", "review_lens", "A/lens-a"), ("lens-a", "review_lens", "B/lens-a"),
            ("edit-a", "edit_lens", "A/edit-a"), ("other-a", "unsorted", "A/other-a"))]
        for files, names in ((["docs/plan.md"], ["lens-a", "lens-b"]),
                             (["web/app.tsx"], ["lens-a", "lens-b", "ui-a"]),
                             (["WEB/APP.TSX"], ["lens-a", "lens-b", "ui-a"])):
            with self.subTest(files=files):
                result = lens_set({"skills": rows}, files)
                self.assertEqual([row["name"] for row in result], names)
                self.assertEqual(result[0]["path"], "A/lens-a")
        self.assertEqual(lens_set({"skills": []}, []), [])
        with patch("ai_kit_spec.lens_delivery.load_seed", side_effect=ValueError):
            self.assertEqual([r["name"] for r in lens_set({"skills": rows}, [])],
                             ["lens-a", "lens-b"])
            self.assertEqual(mcp_pick({"mcp": []}, ""), [])
        for host in ("claude", None, "pi"):
            result = lens_set({"skills": []}, [], "edit_lens", host)
            built_in = next(row for row in result if row["name"] == "simplify")
            self.assertIsNone(built_in["path"])
            self.assertEqual(built_in["note"], None if host == "claude" else "built_in_no_file")
            if host == "claude":
                self.assertEqual(built_in["delivery"], "name")
                checked = check_lens(built_in, ".", [])
                self.assertIsNone(checked["note"])
                self.assertEqual(checked["bytes"], 0)
        scanned = {"name": "simplify", "path": "A/simplify", "role": "edit_lens"}
        self.assertEqual(lens_set({"skills": [scanned]}, [], "edit_lens", "claude"), [scanned])
        self.assertNotIn("simplify", [r["name"] for r in lens_set({"skills": []}, [])])


class TestPins(unittest.TestCase):
    def test_ui_extensions_match_the_adapter(self):
        path = (Path(_REPO_ROOT) / "skills/ai-kit-spec-execute-superpowers"
                / "ai_kit_spec_superpowers/task_classification.py")
        tree = ast.parse(path.read_text(encoding="utf-8"))
        values = [ast.literal_eval(node.value) for node in tree.body
                  if isinstance(node, ast.Assign)
                  and any(isinstance(target, ast.Name) and target.id == "_FRONTEND_EXTENSIONS"
                          for target in node.targets)]
        self.assertEqual(values, [UI_EXTENSIONS])

    def test_runner_limits_pinned(self):
        template = tooling_guidance.resolve_cross_ai_template_path()
        assert template is not None
        path = Path(template)
        text = path.read_text(encoding="utf-8")
        self.assertIn(f"const FILE_READ_MAX = {FILE_READ_MAX};", text)
        self.assertIn("const SKILL_NAME_RE = /^" + SKILL_NAME_RE.pattern + "$/;", text)

    def test_lens_notes_closed_and_disjoint(self):
        self.assertEqual(len(set(LENS_NOTES)), 5)
        self.assertIn(HOST_CANNOT_LOAD, LENS_NOTES)
        self.assertTrue(set(LENS_NOTES).isdisjoint(REFUSAL_REASONS))
        node = require_real_node(self)
        template = tooling_guidance.resolve_cross_ai_template_path()
        with (tempfile.TemporaryDirectory() as tmp,
              patch.dict(os.environ, {"HOME": tmp, "AI_KIT_REFUSE_REAL_HOME": "1"})):
            doc = runner_facts.read_runner_describe(node, template)["describe"]
        self.assertIsNotNone(doc)
        assert doc is not None
        for values in (doc["reasons"], doc["classes"], [f["code"] for f in doc["findings"]]):
            self.assertTrue(set(LENS_NOTES).isdisjoint(values))


class TestMcpPick(unittest.TestCase):
    def test_mcp_pick_and_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            binary_dir = Path(tmp) / "bin"
            empty = Path(tmp) / "empty"
            run = Path(tmp) / "run"
            run_empty = Path(tmp) / "run-empty"
            for directory in (binary_dir, empty, run, run_empty):
                directory.mkdir()
            binary = binary_dir / "codebase-memory-mcp"
            binary.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            binary.chmod(0o755)
            host = {"skills": [], "mcp": "unknown"}
            picks = mcp_pick(host, str(binary_dir))
            self.assertEqual(picks, [{"name": "codebase-memory-mcp", "command": str(binary),
                                      "args": ["--tool-profile=analysis"]}])
            self.assertEqual(mcp_pick({"skills": [], "mcp": []}, ""), [])
            self.assertEqual(mcp_pick(host, str(empty)), [])
            with patch.dict(os.environ, {"PATH": str(binary_dir)}):
                self.assertEqual(mcp_pick(host, str(empty)), [])
                self.assertEqual(mcp_pick(host, ""), [])
            self.assertEqual(mcp_pick({"skills": [], "mcp": [
                {"name": "codebase-memory-mcp", "role": "unsorted"}]}, str(binary_dir)), [])
            self.assertEqual(mcp_pick(host, str(binary_dir),
                                      {"codebase-memory-mcp": "unsorted"}), [])
            path = write_mcp_file(str(run), picks)
            self.assertEqual(path, str(run / "mcp-config.json"))
            assert path is not None
            self.assertEqual(os.stat(path).st_mode & 0o077, 0)
            self.assertEqual(json.loads(Path(path).read_text(encoding="utf-8")),
                             {"mcpServers": {"codebase-memory-mcp": {
                                 "command": str(binary), "args": ["--tool-profile=analysis"]}}})
            self.assertIsNone(write_mcp_file(str(run_empty), []))
            self.assertEqual(os.listdir(run_empty), [])


class TestRunnerSync(unittest.TestCase):
    def setUp(self):
        self.node = require_real_node(self)

    def _run(self, tmp, spec):
        node = self.node
        assert node is not None
        env = child_env()
        env.update(HOME=tmp, XDG_STATE_HOME=os.path.join(tmp, "state"),
                   AI_KIT_REFUSE_REAL_HOME="1")
        env.pop("HERDR_ENV", None)
        return lane_facts(print_argv_lines(
            spec, RunnerSeams(which_fn=lambda _: node, env_fn=lambda: env)))

    def test_mcp_file_applies_in_the_runner(self):
        with tempfile.TemporaryDirectory() as tmp:
            binary = Path(tmp) / "codebase-memory-mcp"
            binary.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            binary.chmod(0o755)
            picks = mcp_pick({"skills": [], "mcp": "unknown"}, tmp)
            path = write_mcp_file(tmp, picks)
            assert path is not None
            spec = RunnerSpec("copilot", "placeholder-model-1", "review", 30, cwd=tmp,
                              mcp_config=path)
            facts = self._run(tmp, spec)
            self.assertEqual(facts.mcp_settings, ({"name": "codebase-memory-mcp",
                                                   "state": "applied", "reason": None},))
            facts = self._run(tmp, spec._replace(runtime="pi", model="fake/placeholder-model-1"))
            self.assertEqual(facts.mcp_settings, ({"name": "codebase-memory-mcp",
                                                   "state": "ignored", "reason": "mode_forbids"},))

    def test_prose_bytes_match_the_runner(self):
        with tempfile.TemporaryDirectory() as tmp:
            roots = os.path.join(tmp, "skills")
            repo = os.path.join(tmp, "repo")
            body = "---\nname: lens-a\n---\nLens body \u00fc.\n".encode()
            directory = skill(roots, "lens-a", body)
            lens = check_lens({"name": "lens-a", "path": directory, "role": "review_lens"},
                              repo, [roots])
            self.assertIsNone(lens["note"])
            self.assertEqual(lens["skill_name"], "lens-a")
            self.assertEqual(lens["path"], os.path.realpath(directory))
            spec = RunnerSpec("copilot", "placeholder-model-1", "review", 30, cwd=tmp,
                              skill_names=(lens["skill_name"],), skill_paths=(lens["path"],))
            facts = self._run(tmp, spec)
            self.assertEqual(facts.skill_blocks[0]["bytes"], lens["bytes"])
            self.assertEqual(facts.skill_blocks[0]["sha256"], lens["sha256"])
            pi = spec._replace(runtime="pi", model="fake/placeholder-model-1")
            facts = self._run(tmp, pi)
            self.assertEqual(facts.skill_settings[0]["form"], "path")
            self.assertTrue(all(row["state"] == "applied" for row in facts.skill_settings))
            second = skill(roots, "Lens_B", b"---\nname: lens-b\n---\nBody.\n")
            lens_b = check_lens({"name": "lens-b", "path": second, "role": "review_lens"},
                                repo, [roots])
            self.assertEqual(lens_b["skill_name"], "lens-b")
            both = (lens, lens_b)
            facts = self._run(tmp, spec._replace(
                skill_names=tuple(row["skill_name"] for row in both),
                skill_paths=tuple(row["path"] for row in both)))
            self.assertEqual([(r["name"], r["state"], r["form"]) for r in facts.skill_settings],
                             [("lens-a", "applied", "prose"), ("lens-b", "applied", "prose")])
            self.assertEqual([r["bytes"] for r in facts.skill_blocks],
                             [r["bytes"] for r in both])
            bad = Path(roots) / "other-a"
            (bad / "SKILL.md").mkdir(parents=True)
            self.assertEqual(check_lens({"name": "other-a", "path": str(bad)}, repo, [roots])
                             ["note"], "path_rejected")

    def test_rejections_and_alias_collisions(self):
        with tempfile.TemporaryDirectory() as tmp:
            roots = os.path.join(tmp, "skills")
            directory = skill(roots, "lens-a", b"---\nname: lens-b\n---\nBody\n")
            row = {"name": "lens-a", "path": directory, "role": "review_lens"}
            checked = check_lens(row, tmp, [roots])
            self.assertEqual(checked["aliases"], ["lens-a", "lens-b"])
            second = {"skill_name": "lens-a", "bytes": 0, "aliases": []}
            delivered, skipped = plan_lenses([checked, second], 0, None, None)
            self.assertEqual(len(delivered), 1)
            self.assertEqual(skipped[0]["note"], "path_rejected")
            file = Path(directory) / "SKILL.md"
            for content, expected in ((b"", "not_present"), (b"\xff", "path_rejected"),
                                      (b"a" * 65537, "path_rejected"),
                                      (b"</skill>", "path_rejected"),
                                      ("\ufeffbody".encode(), "path_rejected")):
                with self.subTest(content=content[:10]):
                    file.write_bytes(content)
                    self.assertEqual(check_lens(row, tmp, [roots])["note"], expected)

    def test_selection_and_budget(self):
        rows = [{"name": "lens-a", "path": "/example", "role": "review_lens"},
                {"name": "ui-a", "path": "/example-ui", "role": "ui_lens"}]
        self.assertEqual([r["name"] for r in lens_set({"skills": rows}, ["view.TSX"])],
                         ["lens-a", "ui-a"])
        lenses = [{"skill_name": "lens-a", "aliases": [], "bytes": 8},
                  {"skill_name": "lens-b", "aliases": [], "bytes": 9},
                  {"skill_name": "edit-a", "aliases": [], "bytes": 1}]
        delivered, skipped = plan_lenses(lenses, 0, 2, None)
        self.assertEqual([r["skill_name"] for r in delivered], ["lens-a"])
        self.assertEqual([r["note"] for r in skipped], ["over_window", "over_window"])
