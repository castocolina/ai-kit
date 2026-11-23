"""39-01 / SPEC R1: the closed roles, the seed rows and the role resolver of
ai_kit_spec.skill_table.
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "skills" / "ai-kit-spec-review"))
sys.path.insert(0, str(REPO))
from ai_kit_spec import config_io, skill_table

from tests.test_arch_hardcoded_models import scan_text

SEED_REL = "skills/ai-kit-spec-review/references/skill-roles.json"
SEED_SOURCE = "judged 2026-11-16 from the skill's own description"


class TestSkillTableSeed(unittest.TestCase):
    def test_seed_rows_follow_d07(self):
        rows = skill_table.load_seed()
        self.assertEqual(len(rows), 14)
        self.assertEqual(
            [row["name"] for row in rows],
            [
                "ponytail-review", "ponytail-audit", "ponytail-debt", "reducing-entropy",
                "naming-analyzer", "ponytail", "simplify", "impeccable", "codebase-memory",
                "graphify", "codebase-memory-mcp", "jev-fast-decision", "herdr", "skill-judge",
            ],
        )
        self.assertEqual(
            [row["role"] for row in rows],
            ["review_lens"] * 5 + ["edit_lens"] * 2 + ["ui_lens"] + ["code_index"] * 3
            + ["decision_helper", "host_control", "skill_judge"],
        )
        self.assertEqual([row["source"] for row in rows], [SEED_SOURCE] * 14)
        self.assertEqual([row["kind"] for row in rows], ["skill"] * 10 + ["mcp"] + ["skill"] * 3)
        self.assertEqual([(r["name"], r["built_in"]) for r in rows if "built_in" in r],
                         [("simplify", "claude")])
        self.assertEqual(
            [(r["name"], r["launch"]) for r in rows if "launch" in r],
            [("codebase-memory-mcp", {
                "command": "codebase-memory-mcp",
                "args": ["--tool-profile=analysis"],
                "source": "codebase-memory-mcp 0.12.1 --help 2026-11-23: bare command runs "
                "the MCP server on stdio; --tool-profile=analysis|scout exposes a restricted "
                "inspection surface (effect unverified)",
            })],
        )

    def test_roles_lock_code_and_seed_file(self):
        roles = (
            "review_lens", "edit_lens", "ui_lens", "code_index", "decision_helper",
            "host_control", "skill_judge", "unsorted",
        )
        self.assertEqual(skill_table.ROLES, roles)
        doc = json.loads(Path(skill_table.SEED_PATH).read_text(encoding="utf-8"))
        self.assertEqual(doc["roles"], list(skill_table.ROLES))

    def test_seed_path_resolves_from_the_module(self):
        self.assertTrue(
            skill_table.SEED_PATH.endswith(os.path.join("references", "skill-roles.json"))
        )
        self.assertTrue(os.path.isfile(skill_table.SEED_PATH))
        self.assertEqual(skill_table.load_seed(skill_table.SEED_PATH), skill_table.load_seed())


def guard(text):
    return scan_text(SEED_REL, text)


class TestSeedProblems(unittest.TestCase):
    def test_shipped_seed_has_no_problems(self):
        self.assertEqual(skill_table.seed_problems(skill_table.load_seed(), literal_hits=guard), [])

    def test_each_problem_fires(self):
        ok = {"name": "lens-a", "kind": "skill", "role": "review_lens", "source": "fixture"}
        cases = [
            ([{**ok, "source": ""}], ["row 0 (lens-a): no source label"]),
            ([{k: v for k, v in ok.items() if k != "source"}],
             ["row 0 (lens-a): no source label"]),
            ([{**ok, "role": "made_up"}], ["row 0 (lens-a): role 'made_up' is not in ROLES"]),
            ([{**ok, "role": "unsorted"}], ["row 0 (lens-a): role unsorted is not a seed role"]),
            ([{**ok, "kind": "plugin"}], ["row 0 (lens-a): kind 'plugin' is not skill or mcp"]),
            ([{**ok, "name": ""}], ["row 0 (?): name is not a non-empty string"]),
            ([{**ok, "launch": {"command": "x", "args": [], "source": "s"}}],
             ["row 0 (lens-a): launch on a skill row"]),
            ([{**ok, "kind": "mcp", "launch": {"command": "x", "args": "--a", "source": "s"}}],
             ["row 0 (lens-a): launch needs command, args and source"]),
            ([ok, dict(ok)], ["row 1 (lens-a): duplicate name and kind"]),
            (["text"], ["row 0: not an object"]),
            ([{**ok, "name": ["x"]}], ["row 0 (['x']): name is not a non-empty string"]),
        ]
        for rows, expected in cases:
            with self.subTest(rows=rows):
                self.assertEqual(skill_table.seed_problems(rows), expected)

    def test_built_in_only_on_skill_rows(self):
        ok = {"name": "lens-a", "kind": "skill", "role": "review_lens", "source": "fixture"}
        self.assertEqual(skill_table.seed_problems([{**ok, "kind": "mcp", "built_in": "claude"}]),
                         ["row 0 (lens-a): built_in on a non-skill row"])
        self.assertEqual(skill_table.seed_problems([{**ok, "built_in": "placeholder-cli-1"}]),
                         ["row 0 (lens-a): built_in 'placeholder-cli-1' is not a host"])
        self.assertEqual(skill_table.seed_problems([{**ok, "built_in": "claude"}]), [])

    def test_model_literal_caught_by_the_guard(self):
        ok = {"name": "lens-a", "kind": "skill", "role": "review_lens", "source": "fixture"}
        bad_name = {**ok, "name": "vendorq/" + "qmodel-4"}
        bad_args = {**ok, "kind": "mcp", "launch": {
            "command": "x", "args": ["--model", "qq" + "model-7"], "source": "s",
        }}
        self.assertEqual(skill_table.seed_problems([bad_name], literal_hits=guard), [
            "row 0 (" + "vendorq/" + "qmodel-4" + "): model or provider literal "
            + "vendorq/" + "qmodel-4",
        ])
        self.assertEqual(skill_table.seed_problems([bad_args], literal_hits=guard), [
            "row 0 (lens-a): model or provider literal " + "qq" + "model-7",
        ])
        self.assertEqual(skill_table.seed_problems([bad_name]), [])


def _write(path: str, text: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)


class TestUserRoles(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = self.temp.name
        self.home = os.path.join(self.root, "home")
        self.cwd = os.path.join(self.root, "proj")
        self.env = {"HOME": self.home}
        self.user_path = os.path.join(self.home, ".config", "ai-kit", "config.toml")
        self.project_path = os.path.join(self.cwd, ".aikit", "config.toml")

    def _layered(self):
        _write(self.user_path, '[skills.roles]\nlens-a = "review_lens"\nedit-a = "edit_lens"\n')
        _write(self.project_path, '[skills.roles]\nlens-a = "ui_lens"\n')

    def test_project_over_user_per_key(self):
        self._layered()
        self.assertEqual(skill_table.user_roles(self.cwd, self.env),
                         {"lens-a": "ui_lens", "edit-a": "edit_lens"})

    def test_no_config_is_empty(self):
        self.assertEqual(skill_table.user_roles(self.cwd, self.env), {})
        _write(self.user_path, "[lanes]\n")
        self.assertEqual(skill_table.user_roles(self.cwd, self.env), {})

    def test_role_outside_the_closed_list_raises(self):
        message = ("[skills.roles]: entry 'lens-a' needs a role from: review_lens, edit_lens, "
                   "ui_lens, code_index, decision_helper, host_control, skill_judge")
        for value in ('"made_up"', '"unsorted"', "3"):
            with self.subTest(value=value):
                _write(self.user_path, f"[skills.roles]\nlens-a = {value}\n")
                with self.assertRaises(config_io.ConfigError) as caught:
                    skill_table.user_roles(self.cwd, self.env)
                self.assertEqual(str(caught.exception), message)
        _write(self.user_path, '[skills]\nroles = "x"\n')
        with self.assertRaises(config_io.ConfigError) as caught:
            skill_table.user_roles(self.cwd, self.env)
        self.assertEqual(str(caught.exception), "[skills.roles]: must be a table")
        _write(self.user_path, "[skills.roles\n")
        with self.assertRaises(config_io.ConfigError):
            skill_table.user_roles(self.cwd, self.env)

    def test_user_roles_feed_resolve_role(self):
        self._layered()
        roles = skill_table.user_roles(self.cwd, self.env)
        seed = skill_table.load_seed()
        self.assertEqual(skill_table.resolve_role("lens-a", "skill", seed, roles),
                         ("ui_lens", "user-stated"))
        self.assertEqual(skill_table.resolve_role("ponytail", "skill", seed, roles),
                         ("edit_lens", "seed"))

    def test_table_inputs_never_raises(self):
        self._layered()
        self.assertEqual(
            skill_table.table_inputs(self.cwd, self.env),
            (skill_table.load_seed(), {"lens-a": "ui_lens", "edit-a": "edit_lens"}, []),
        )
        bad_seed = os.path.join(self.root, "bad-seed.json")
        _write(bad_seed, '{"rows": ["text"]}')
        _write(self.user_path, '[skills.roles]\nlens-a = "made_up"\n')
        _write(self.project_path, "[skills.roles]\n")
        seed, user, notes = skill_table.table_inputs(self.cwd, self.env, seed_path=bad_seed)
        self.assertEqual(seed, [])
        self.assertEqual(user, {})
        self.assertEqual(len(notes), 2)
        self.assertTrue(notes[0].startswith("skill seed ignored: "))
        self.assertTrue(notes[1].startswith("skills.roles ignored: [skills.roles]: entry 'lens-a'"))


class TestResolveRole(unittest.TestCase):
    def test_user_beats_seed_beats_none(self):
        seed = skill_table.load_seed()
        resolve = skill_table.resolve_role
        self.assertEqual(resolve("ponytail-review", "skill", seed, {}), ("review_lens", "seed"))
        self.assertEqual(
            resolve("ponytail-review", "skill", seed, {"ponytail-review": "edit_lens"}),
            ("edit_lens", "user-stated"),
        )
        self.assertEqual(resolve("other-a", "skill", seed, {}), ("unsorted", "none"))
        self.assertEqual(resolve("codebase-memory-mcp", "mcp", seed, {}), ("code_index", "seed"))
        self.assertEqual(resolve("codebase-memory-mcp", "skill", seed, {}), ("unsorted", "none"))
        self.assertEqual(resolve("lens-a", "mcp", seed, {"lens-a": "review_lens"}),
                         ("review_lens", "user-stated"))
        self.assertEqual(resolve("Ponytail", "skill", seed, {}), ("unsorted", "none"))
        damaged = [{"name": "lens-a", "kind": "skill"},
                   {"name": "lens-a", "kind": "skill", "role": "unsorted"}]
        self.assertEqual(resolve("lens-a", "skill", damaged, {}), ("unsorted", "none"))
