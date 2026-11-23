"""39-01 / SPEC R1: the closed roles, the seed rows and the role resolver of
ai_kit_spec.skill_table.
"""

import contextlib
import io
import json
import os
import shutil
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "skills" / "ai-kit-spec-review"))
sys.path.insert(0, str(REPO))
from ai_kit_spec import cli, config_io, skill_table

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


class TestScanTracer(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = os.path.join(self.temp.name, "home")
        self.project = os.path.join(self.temp.name, "project")
        self.env = {"HOME": self.home}
        self.root = Path(self.home) / ".agents" / "skills"
        self.add_skill("reducing-entropy")
        self.add_skill("other-a")

    def add_skill(self, name):
        directory = self.root / name
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "SKILL.md").write_text(
            "---\ndescription: fixture\n---\n# skill\n", encoding="utf-8"
        )

    def run_cli(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = cli.main(["skill-table", "--cwd", self.project], env_fn=lambda: self.env)
        self.assertEqual(code, 0)
        return json.loads(output.getvalue())

    def test_seed_and_unknown_skill_through_cli(self):
        result = self.run_cli()
        self.assertEqual(
            set(result), {"claude", "codex", "opencode", "cursor", "copilot", "pi", "agents"}
        )
        rows = result["agents"]["skills"]
        self.assertEqual([row["name"] for row in rows], ["other-a", "reducing-entropy"])
        self.assertEqual((rows[0]["role"], rows[0]["role_source"]), ("unsorted", "none"))
        self.assertEqual((rows[1]["role"], rows[1]["role_source"]), ("review_lens", "seed"))
        self.assertEqual(rows[1]["root_kind"], "global")
        self.assertIs(rows[1]["addressable"], True)
        self.assertEqual(rows[1]["path"], str(self.root / "reducing-entropy"))
        for host in set(result) - {"agents"}:
            self.assertEqual(result[host]["skills"], [])

    def test_seed_row_never_makes_presence(self):
        for host in self.run_cli().values():
            self.assertNotIn("ponytail-review", [row["name"] for row in host["skills"]])

    def test_rescan_sees_add_and_remove(self):
        def names():
            return [r["name"] for r in skill_table.scan(self.env, self.project)["agents"]["skills"]]

        self.assertNotIn("lens-b", names())
        self.add_skill("lens-b")
        self.assertIn("lens-b", names())
        shutil.rmtree(self.root / "lens-b")
        self.assertNotIn("lens-b", names())

    def test_malformed_roles_config_noted(self):
        _write(os.path.join(self.project, ".aikit", "config.toml"), "[skills.roles")
        result = self.run_cli()
        for host in result.values():
            self.assertEqual(len(host["notes"]), 1)
            self.assertTrue(host["notes"][0].startswith("skills.roles ignored: "))
        row = result["agents"]["skills"][1]
        self.assertEqual((row["role"], row["role_source"]), ("review_lens", "seed"))

    def test_broken_seed_noted(self):
        bad = os.path.join(self.temp.name, "bad.json")
        _write(bad, "{not json")
        with mock.patch.object(skill_table, "SEED_PATH", bad):
            result = skill_table.scan(self.env, self.project)
        for host in result.values():
            self.assertEqual(len(host["notes"]), 1)
            self.assertTrue(host["notes"][0].startswith("skill seed ignored: "))
        row = result["agents"]["skills"][1]
        self.assertEqual((row["role"], row["role_source"]), ("unsorted", "none"))


class TestScanEdges(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name) / "home"
        self.project = Path(self.temp.name) / "project"
        self.env = {"HOME": str(self.home)}

    def add_skill(self, root, name):
        path = root / name
        _write(str(path / "SKILL.md"), "---\ndescription: fixture\n---\n")
        return path

    def plugins(self, enabled):
        claude = self.home / ".claude"
        records = {}
        settings = {}
        for package, name, is_enabled in enabled:
            install = claude / "plugins" / "cache" / package / "version"
            self.add_skill(install / "skills", name)
            key = f"{package}@market-{package[-1]}"
            records[key] = [{"scope": "user", "installPath": str(install)}]
            settings[key] = is_enabled
        manifest = claude / "plugins" / "installed_plugins.json"
        manifest.parent.mkdir(parents=True, exist_ok=True)
        with manifest.open("w", encoding="utf-8") as handle:
            json.dump({"version": 2, "plugins": records}, handle)
        with (claude / "settings.json").open("w", encoding="utf-8") as handle:
            json.dump({"enabledPlugins": settings}, handle)

    def scan(self):
        return skill_table.scan(self.env, str(self.project))

    def test_plugin_skills_enabled_only(self):
        self.plugins([("pkg-a", "edit-a", True), ("pkg-b", "lens-b", False)])
        rows = self.scan()["claude"]["skills"]
        self.assertEqual([row["name"] for row in rows], ["edit-a"])
        self.assertEqual(rows[0]["root_kind"], "plugin")
        self.assertEqual(rows[0]["path"], str(
            self.home / ".claude/plugins/cache/pkg-a/version/skills/edit-a"
        ))

    def test_empty_or_missing_plugin_manifest(self):
        self.assertEqual(self.scan()["claude"]["skills"], [])
        self.plugins([])
        self.assertEqual(self.scan()["claude"]["skills"], [])

    def test_description_cut_at_300(self):
        path = self.add_skill(self.home, "lens-a")
        for length in (300, 301):
            _write(str(path / "SKILL.md"), f"---\ndescription: {'a' * length}\n---\n")
            self.assertEqual(skill_table.read_description(str(path)), "a" * 300)
        _write(str(path / "SKILL.md"), "no frontmatter")
        self.assertEqual(skill_table.read_description(str(path)), "")
        self.assertEqual(skill_table.read_description(str(path / "missing")), "")

    def test_name_outside_pattern_not_addressable(self):
        self.add_skill(self.home / ".agents/skills", "lens.x")
        row = self.scan()["agents"]["skills"][0]
        self.assertFalse(row["addressable"])
        self.assertEqual((row["role"], row["role_source"]), ("unsorted", "none"))

    def test_dir_without_skill_md_ignored(self):
        _write(str(self.home / ".agents/skills/other-a/README.md"), "fixture")
        self.assertEqual(self.scan()["agents"]["skills"], [])

    def test_same_name_two_roots(self):
        agents = self.add_skill(self.home / ".agents/skills", "lens-a")
        claude = self.add_skill(self.home / ".claude/skills", "lens-a")
        result = self.scan()
        self.assertEqual(result["agents"]["skills"][0]["path"], str(agents))
        self.assertEqual(result["claude"]["skills"][0]["path"], str(claude))

    def test_user_role_beats_seed(self):
        _write(str(self.project / ".aikit/config.toml"),
               '[skills.roles]\nreducing-entropy = "edit_lens"\n')
        self.add_skill(self.home / ".agents/skills", "reducing-entropy")
        row = self.scan()["agents"]["skills"][0]
        self.assertEqual((row["role"], row["role_source"]), ("edit_lens", "user-stated"))

    def test_rows_sorted(self):
        for name in ("lens-b", "lens-a"):
            self.add_skill(self.home / ".claude/skills", name)
        self.plugins([("pkg-a", "edit-a", True), ("pkg-b", "ui-a", True)])
        result = self.scan()["claude"]
        self.assertEqual([row["name"] for row in result["skills"]],
                         ["lens-a", "lens-b", "edit-a", "ui-a"])
        self.assertEqual(len(result["roots"]), 3)
        self.assertEqual(set(result["roots"]), {
            str(self.home / ".claude/skills"),
            str(self.home / ".claude/plugins/cache/pkg-a/version/skills"),
            str(self.home / ".claude/plugins/cache/pkg-b/version/skills"),
        })

    def test_env_dirs_honored(self):
        variables = {"claude": "CLAUDE_CONFIG_DIR", "codex": "CODEX_HOME",
                     "cursor": "CURSOR_CONFIG_DIR", "copilot": "COPILOT_HOME",
                     "pi": "PI_CODING_AGENT_DIR", "opencode": "XDG_CONFIG_HOME"}
        for host, variable in variables.items():
            base = self.home / host
            self.env[variable] = str(base)
            self.add_skill(base / ("opencode/skills" if host == "opencode" else "skills"),
                           f"{host}-a")
        result = self.scan()
        for host in variables:
            self.assertEqual([row["name"] for row in result[host]["skills"]], [f"{host}-a"])
        self.env["CODEX_HOME"] = "rel"
        self.assertEqual(self.scan()["codex"]["skills"], [])

    def test_parallel_scans_equal(self):
        self.add_skill(self.home / ".agents/skills", "lens-a")
        results = [None, None]
        def run(index):
            results[index] = self.scan()
        threads = [threading.Thread(target=run, args=(index,)) for index in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(results[0], results[1])
        self.assertEqual(results[0], self.scan())


class TestScanMcp(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name) / "home"
        self.env = {"HOME": str(self.home)}

    def scan(self):
        return skill_table.scan(self.env, str(self.home / "project"))

    def test_names_only_with_roles(self):
        _write(str(self.home / ".claude.json"), json.dumps({"mcpServers": {
            "codebase-memory-mcp": {"command": "x", "env": {"K": "fixture-secret-a"}},
            "srv-b": {},
        }}))
        result = self.scan()
        self.assertEqual(result["claude"]["mcp"], [
            {"name": "codebase-memory-mcp", "role": "code_index"},
            {"name": "srv-b", "role": "unsorted"},
        ])
        self.assertEqual(result["claude"]["mcp_note"], "")
        self.assertNotIn("fixture-secret-a", json.dumps(result))

    def test_malformed_config_unknown_for_that_host_only(self):
        _write(str(self.home / ".cursor/mcp.json"), "{not json")
        result = self.scan()
        self.assertEqual(result["cursor"]["mcp"], "unknown")
        self.assertTrue(result["cursor"]["mcp_note"].startswith("unreadable or malformed: "))
        self.assertIsInstance(result["claude"]["mcp"], list)

    def test_unreadable_config_unknown(self):
        path = self.home / ".copilot/mcp-config.json"
        path.mkdir(parents=True)
        self.assertEqual(self.scan()["copilot"]["mcp"], "unknown")
        path.rmdir()
        path.parent.rmdir()
        path.parent.write_text("file", encoding="utf-8")
        entry = self.scan()["copilot"]
        self.assertEqual(entry["mcp"], "unknown")
        self.assertTrue(entry["mcp_note"].startswith("unreadable or malformed: "))
        _write(str(self.home / ".cursor/mcp.json"), '{"mcpServers": null}')
        self.assertEqual(self.scan()["cursor"]["mcp"], "unknown")

    def test_unsafe_names_hidden_and_counted(self):
        token = "gh" + "p_" + "a" * 24
        bad = "bad\x07name"
        _write(str(self.home / ".claude.json"), json.dumps({"mcpServers": {
            "srv-a": {}, bad: {}, token: {},
        }}))
        result = self.scan()
        self.assertEqual(result["claude"]["mcp"], [{"name": "srv-a", "role": "unsorted"}])
        self.assertEqual(result["claude"]["mcp_note"],
                         "2 server name(s) not shown: outside [A-Za-z0-9_.@-] or secret-shaped")
        self.assertNotIn(token, json.dumps(result))
        self.assertNotIn(json.dumps(bad)[1:-1], json.dumps(result))

    def test_fifo_and_oversize_config_unknown(self):
        path = self.home / ".cursor/mcp.json"
        path.parent.mkdir(parents=True)
        os.mkfifo(path)
        entry = self.scan()["cursor"]
        self.assertEqual(entry["mcp"], "unknown")
        self.assertTrue(entry["mcp_note"].startswith("not a regular file or over 1048576 bytes: "))
        _write(str(self.home / ".copilot/mcp-config.json"), "{" + " " * 1048575 + "}")
        entry = self.scan()["copilot"]
        self.assertEqual(entry["mcp"], "unknown")
        self.assertTrue(entry["mcp_note"].startswith("not a regular file or over 1048576 bytes: "))

    def test_empty_root_still_a_root(self):
        root = self.home / ".agents/skills"
        root.mkdir(parents=True)
        result = self.scan()
        self.assertEqual(result["agents"]["skills"], [])
        self.assertEqual(result["agents"]["roots"], [os.path.realpath(root)])
        self.assertIn(os.path.realpath(root), skill_table.skill_roots(result))

    def test_absent_config_empty(self):
        result = self.scan()
        for host in ("claude", "codex", "opencode", "cursor", "copilot"):
            self.assertEqual(result[host]["mcp"], [])
            self.assertEqual(result[host]["mcp_note"], "")

    def test_codex_toml_and_opencode_jsonc(self):
        codex = self.home / "custom-codex"
        config = self.home / "custom-opencode.jsonc"
        self.env.update(CODEX_HOME=str(codex), OPENCODE_CONFIG=str(config))
        _write(str(codex / "config.toml"), '[mcp_servers.srv-c]\ncommand = "x"\n')
        _write(str(config), '// comment\n{"mcp": {"srv-d": {"type": "local"}}}')
        result = self.scan()
        self.assertEqual(result["codex"]["mcp"], [{"name": "srv-c", "role": "unsorted"}])
        self.assertEqual(result["opencode"]["mcp"], [{"name": "srv-d", "role": "unsorted"}])

    def test_pi_unknown_agents_empty(self):
        result = self.scan()
        self.assertEqual(result["pi"]["mcp"], "unknown")
        self.assertEqual(result["pi"]["mcp_note"], skill_table.PI_MCP_NOTE)
        self.assertEqual(result["agents"]["mcp"], [])
        self.assertEqual(result["agents"]["mcp_note"], skill_table.AGENTS_MCP_NOTE)

    def test_skill_roots(self):
        agents = self.home / ".agents/skills"
        claude = self.home / ".claude/skills"
        target = Path(self.temp.name) / "vault/lens-b"
        _write(str(agents / "lens-a/SKILL.md"), "fixture")
        _write(str(target / "SKILL.md"), "fixture")
        claude.mkdir(parents=True)
        (claude / "lens-b").symlink_to(target, target_is_directory=True)
        self.assertEqual(skill_table.skill_roots(self.scan()),
                         sorted({os.path.realpath(agents), os.path.realpath(claude)}))
