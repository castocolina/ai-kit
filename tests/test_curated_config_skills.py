"""Skill scan and System One backend detection for curated-config inventory (18-03)."""
from __future__ import annotations

import json
import os
import shlex
import shutil
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "skills", "ai-kit-gsd-curated-config"),
)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills", "ai-kit-spec-review"))

from ai_kit_gsd_curated_config import host, plan_io, recommend, skill_scan, skills

from tests.test_curated_config_golden import tables_answer
from tests.test_curated_config_inventory import (
    FakeRun,
    _inventory_env,
    make_gsd_install,
    run_inventory,
)
from tests.test_curated_config_recommend import entry_map, make_inventory, run_recommend


def make_home(root: str) -> str:
    os.makedirs(os.path.join(root, ".claude", "skills"), exist_ok=True)
    os.makedirs(os.path.join(root, ".claude", "plugins"), exist_ok=True)
    return root


def add_skill(skill_dir: str, name: str, description: str = "") -> str:
    path = os.path.join(skill_dir, name)
    os.makedirs(path, exist_ok=True)
    body = "---\n"
    if description:
        body += f"description: {description}\n"
    body += "---\n# skill\n"
    with open(os.path.join(path, "SKILL.md"), "w", encoding="utf-8") as handle:
        handle.write(body)
    return path


def add_plugin(
    home: str,
    plugin: str,
    marketplace: str,
    skills: list[str],
    scope: str = "user",
    project_path: str | None = None,
    enabled: bool = True,
) -> str:
    plugin_id = f"{plugin}@{marketplace}"
    version_dir = os.path.join(
        home, ".claude", "plugins", "cache", plugin, marketplace, "5.1.0"
    )
    os.makedirs(os.path.join(version_dir, ".claude-plugin"), exist_ok=True)
    with open(
        os.path.join(version_dir, ".claude-plugin", "plugin.json"),
        "w",
        encoding="utf-8",
    ) as handle:
        json.dump({"name": plugin}, handle)
    for skill_name in skills:
        add_skill(os.path.join(version_dir, "skills"), skill_name)
    manifest = {
        "version": 2,
        "plugins": {
            plugin_id: [
                {
                    "scope": scope,
                    "installPath": version_dir,
                    **({"projectPath": project_path} if project_path else {}),
                }
            ]
        },
    }
    with open(
        os.path.join(home, ".claude", "plugins", "installed_plugins.json"),
        "w",
        encoding="utf-8",
    ) as handle:
        json.dump(manifest, handle)
    settings_path = os.path.join(home, ".claude", "settings.json")
    with open(settings_path, "w", encoding="utf-8") as handle:
        json.dump({"enabledPlugins": {plugin_id: enabled}}, handle)
    return version_dir


class TestSkillInventoryEndToEnd(unittest.TestCase):
    def _node_answer(self, home):
        def _answer(cmd):
            keys = json.loads(cmd[6])
            return json.dumps(tables_answer(keys, home))

        return _answer

    def test_claude_host_lists_global_project_and_plugin_skills(self):
        root = tempfile.mkdtemp()
        home = make_home(os.path.join(root, "home"))
        project = os.path.join(root, "project")
        os.makedirs(project)
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        add_skill(os.path.join(home, ".claude", "skills"), "plain")
        vault_parent = os.path.join(home, "vault")
        add_skill(vault_parent, "linked")
        os.symlink(
            os.path.join(vault_parent, "linked"),
            os.path.join(home, ".claude", "skills", "linked"),
        )
        add_skill(os.path.join(project, "skills"), "projskill")
        add_plugin(home, "ponytail", "ponytail", ["ponytail", "ponytail-review"])
        make_gsd_install(os.path.join(project, ".claude", "gsd-core"))
        env = _inventory_env(home)
        fake = FakeRun(node_stdout=self._node_answer(home))
        code, parsed, _err = run_inventory(project, env, fake, "--host", "claude")
        self.assertEqual(code, 0)
        assert parsed is not None
        names = [row["name"] for row in parsed["skills"]]
        self.assertEqual(names, ["linked", "plain", "ponytail", "ponytail-review", "projskill"])
        linked = parsed["skills"][0]
        self.assertTrue(linked["escapes_root"])
        self.assertEqual(linked["real_dir_home"], "~/vault/linked")
        plain = parsed["skills"][1]
        self.assertFalse(plain["escapes_root"])
        plugin_row = parsed["skills"][2]
        self.assertEqual(plugin_row["root_kind"], "plugin")
        self.assertEqual(plugin_row["root"], "ponytail@ponytail")
        self.assertEqual(plugin_row["plugin"], "ponytail")
        proj = parsed["skills"][-1]
        self.assertEqual(proj["root"], "skills")
        ponytail_vis = parsed["ponytail_visibility"]
        self.assertEqual(set(ponytail_vis.keys()), set(host.HOSTS))
        self.assertTrue(all(not names for names in ponytail_vis.values()))

    def test_codex_host_skips_plugin_skills(self):
        root = tempfile.mkdtemp()
        home = make_home(os.path.join(root, "home"))
        project = os.path.join(root, "project")
        os.makedirs(project)
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        add_plugin(home, "ponytail", "ponytail", ["ponytail"])
        make_gsd_install(os.path.join(project, ".claude", "gsd-core"))
        env = _inventory_env(home)
        fake = FakeRun(node_stdout=self._node_answer(home))
        code, parsed, _err = run_inventory(project, env, fake, "--host", "codex")
        self.assertEqual(code, 0)
        assert parsed is not None
        self.assertEqual(parsed["skills"], [])


def write_enabled_layers(home, project, plugin_id, user=None, project_val=None, local=None):
    if user is not None:
        os.makedirs(os.path.join(home, ".claude"), exist_ok=True)
        with open(os.path.join(home, ".claude", "settings.json"), "w", encoding="utf-8") as fh:
            json.dump({"enabledPlugins": {plugin_id: user}}, fh)
    if project_val is not None:
        os.makedirs(os.path.join(project, ".claude"), exist_ok=True)
        with open(
            os.path.join(project, ".claude", "settings.json"), "w", encoding="utf-8"
        ) as fh:
            json.dump({"enabledPlugins": {plugin_id: project_val}}, fh)
    if local is not None:
        os.makedirs(os.path.join(project, ".claude"), exist_ok=True)
        with open(
            os.path.join(project, ".claude", "settings.local.json"), "w", encoding="utf-8"
        ) as fh:
            json.dump({"enabledPlugins": {plugin_id: local}}, fh)


class TestScanSkills(unittest.TestCase):
    def test_adjacent_same_name_in_global_and_project(self):
        root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        home = make_home(os.path.join(root, "home"))
        project = os.path.join(root, "project")
        os.makedirs(project)
        gdir = os.path.join(home, ".claude", "skills")
        add_skill(gdir, "dup")
        add_skill(os.path.join(project, "skills"), "dup")
        roots = {"claude": gdir, "codex": None}
        rows = skill_scan.scan_skills(project, "claude", roots, home)
        self.assertEqual(len(rows), 2)
        self.assertEqual({r["root_kind"] for r in rows}, {"global", "project"})
        self.assertNotEqual(rows[0]["real_dir"], rows[1]["real_dir"])

    def test_symlinked_project_skills_root_outside_escapes(self):
        """C-CR-1: gsd-core confines skills/<name> to the project root, not to skills/."""
        root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        home = make_home(os.path.join(root, "home"))
        project = os.path.join(root, "project")
        os.makedirs(project)
        shared = os.path.join(home, "shared", "skills")
        add_skill(shared, "foo")
        os.symlink(shared, os.path.join(project, "skills"))
        rows = skill_scan.scan_skills(project, "codex", {"codex": None}, home)
        self.assertEqual([r["name"] for r in rows], ["foo"])
        self.assertTrue(rows[0]["escapes_root"])
        self.assertIsNone(skills.locate("foo", _inv(skills=rows)))

    def test_in_project_links_do_not_escape(self):
        """C-CR-1: a link that stays inside the project is accepted, as gsd-core does."""
        root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        home = make_home(os.path.join(root, "home"))
        project = os.path.join(root, "project")
        add_skill(os.path.join(project, "vendor"), "foo")
        os.makedirs(os.path.join(project, "skills"))
        os.symlink(
            os.path.join(project, "vendor", "foo"), os.path.join(project, "skills", "foo")
        )
        bar_dir = os.path.join(project, "skills", "bar")
        os.makedirs(bar_dir)
        docs = os.path.join(project, "docs")
        os.makedirs(docs)
        with open(os.path.join(docs, "bar.md"), "w", encoding="utf-8") as fh:
            fh.write("---\ndescription: x\n---\n")
        os.symlink(os.path.join(docs, "bar.md"), os.path.join(bar_dir, "SKILL.md"))
        rows = {r["name"]: r for r in skill_scan.scan_skills(project, "codex", {}, home)}
        self.assertFalse(rows["foo"]["escapes_root"])
        self.assertFalse(rows["bar"]["escapes_root"])
        row = skills.locate("foo", _inv(skills=list(rows.values())))
        assert row is not None
        self.assertEqual(skills.reference_for(row), "skills/foo")

    def test_empty_roots_and_missing_dirs(self):
        project = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, project, ignore_errors=True)
        rows = skill_scan.scan_skills(project, "codex", {"codex": None}, "/tmp/home")
        self.assertEqual(rows, [])

    def test_encoding_and_symlink_escape(self):
        root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        home = make_home(os.path.join(root, "home"))
        gdir = os.path.join(home, ".claude", "skills")
        for name in ("bad name", "dot.name"):
            add_skill(gdir, name)
        add_skill(gdir, "in")
        outer = os.path.join(root, "outside")
        add_skill(outer, "link-out")
        os.symlink(os.path.join(outer, "link-out"), os.path.join(gdir, "link-out"))
        rows = {r["name"]: r for r in skill_scan.scan_root(gdir, "global", gdir, home)}
        self.assertFalse(rows["bad name"]["addressable"])
        self.assertFalse(rows["dot.name"]["addressable"])
        self.assertTrue(rows["link-out"]["escapes_root"])
        self.assertFalse(rows["in"]["escapes_root"])

    def test_skill_md_symlink_outside_root(self):
        root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        home = make_home(os.path.join(root, "home"))
        gdir = os.path.join(home, ".claude", "skills")
        skill_dir = os.path.join(gdir, "inner")
        os.makedirs(skill_dir)
        outside = os.path.join(home, "vault", "desc.md")
        os.makedirs(os.path.dirname(outside), exist_ok=True)
        with open(outside, "w", encoding="utf-8") as fh:
            fh.write("---\ndescription: x\n---\n")
        os.symlink(outside, os.path.join(skill_dir, "SKILL.md"))
        row = skill_scan.scan_root(gdir, "global", gdir, home)[0]
        self.assertTrue(row["escapes_root"])
        self.assertTrue(row["real_dir"].endswith("vault"))
        self.assertEqual(row["real_dir_home"], "~/vault")

    def test_ordering_by_root_kind_root_name(self):
        root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        home = make_home(os.path.join(root, "home"))
        project = os.path.join(root, "project")
        os.makedirs(project)
        gdir = os.path.join(home, ".claude", "skills")
        for name in ("z-skill", "a-skill"):
            add_skill(gdir, name)
        add_skill(os.path.join(project, "skills"), "m-skill")
        rows = skill_scan.scan_skills(project, "claude", {"claude": gdir}, home)
        self.assertEqual([r["name"] for r in rows], ["a-skill", "z-skill", "m-skill"])

    def test_ignores_non_skill_dirs_and_truncates_description(self):
        root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        gdir = os.path.join(root, "skills")
        os.makedirs(gdir)
        add_skill(gdir, "keep", "x" * 500)
        os.makedirs(os.path.join(gdir, "empty"), exist_ok=True)
        with open(os.path.join(gdir, "plain.txt"), "w", encoding="utf-8") as fh:
            fh.write("n")
        row = skill_scan.scan_root(gdir, "project", "skills", root)[0]
        self.assertEqual(len(row["description"]), skill_scan.DESCRIPTION_MAX)

    def test_dangling_skill_md_link_not_inventoried(self):
        """C-W4: a SKILL.md link to nothing is not an installed skill (D-32)."""
        root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        gdir = os.path.join(root, "skills")
        os.makedirs(os.path.join(gdir, "ghost"))
        os.symlink(os.path.join(root, "missing.md"), os.path.join(gdir, "ghost", "SKILL.md"))
        add_skill(gdir, "real")
        rows = skill_scan.scan_root(gdir, "global", gdir, root)
        self.assertEqual([r["name"] for r in rows], ["real"])

    def test_block_scalar_descriptions(self):
        """C-W2: chomping and indent indicators start a block, not a literal value."""
        for indicator in (">", "|", ">-", "|-", ">+", "|+", ">2", "|2-", ">-2"):
            with self.subTest(indicator=indicator):
                text = f"---\nname: x\ndescription: {indicator}\n  Draws\n  charts\n---\n"
                self.assertEqual(skill_scan._parse_description(text), "Draws charts")
        self.assertEqual(
            skill_scan._parse_description("---\ndescription: >-x\n---\n"), ">-x"
        )

    def test_unreadable_skill_md_keeps_entry(self):
        if os.geteuid() == 0:
            self.skipTest("chmod 000 ineffective as root")
        root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        gdir = os.path.join(root, "skills")
        add_skill(gdir, "locked")
        skill_md = os.path.join(gdir, "locked", "SKILL.md")
        os.chmod(skill_md, 0)
        self.addCleanup(os.chmod, skill_md, 0o644)
        row = skill_scan.scan_root(gdir, "project", "skills", root)[0]
        self.assertEqual(row["description"], "")


class TestPluginSkills(unittest.TestCase):
    def test_project_scope_and_enabled_layers(self):
        root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        home = make_home(os.path.join(root, "home"))
        project = os.path.join(root, "project")
        other = os.path.join(root, "other")
        os.makedirs(project)
        os.makedirs(other)
        plugin_id = "p@m"
        add_plugin(home, "p", "m", ["s1"], scope="project", project_path=other, enabled=True)
        claude_dir = os.path.join(home, ".claude")
        rows = skill_scan.plugin_skills(claude_dir, project, home)
        self.assertEqual(rows, [])
        add_plugin(home, "p", "m", ["s1"], scope="project", project_path=project, enabled=True)
        rows = skill_scan.plugin_skills(claude_dir, project, home)
        self.assertEqual(len(rows), 1)
        write_enabled_layers(home, project, plugin_id, user=True, local=False)
        rows = skill_scan.plugin_skills(claude_dir, project, home)
        self.assertEqual(rows, [])
        write_enabled_layers(home, project, plugin_id, local=True)
        rows = skill_scan.plugin_skills(claude_dir, project, home)
        self.assertEqual(len(rows), 1)

    def test_bad_plugin_name_not_addressable(self):
        root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        home = make_home(os.path.join(root, "home"))
        version_dir = add_plugin(home, "bad.plugin", "m", ["ok"], enabled=True)
        with open(
            os.path.join(version_dir, ".claude-plugin", "plugin.json"), "w", encoding="utf-8"
        ) as fh:
            json.dump({"name": "bad.plugin"}, fh)
        rows = skill_scan.plugin_skills(os.path.join(home, ".claude"), root, home)
        self.assertFalse(rows[0]["addressable"])

    def test_trailing_newline_names_not_addressable(self):
        """C-IN-01: ``$`` accepted ``foo\\n``; gsd-core's regex and plan_io's fullmatch do not."""
        root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        gdir = os.path.join(root, "skills")
        add_skill(gdir, "ok")
        add_skill(gdir, "nl\n")
        rows = {r["name"]: r for r in skill_scan.scan_root(gdir, "global", gdir, root)}
        self.assertTrue(rows["ok"]["addressable"])
        self.assertFalse(rows["nl\n"]["addressable"])
        plugin_rows = skill_scan.scan_root(gdir, "plugin", "p@m", root, plugin="ponytail\n")
        self.assertFalse(any(r["addressable"] for r in plugin_rows))

    def test_missing_install_and_nonstandard_layout(self):
        root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        home = make_home(os.path.join(root, "home"))
        version_dir = add_plugin(home, "p", "m", ["s1"], enabled=True)
        shutil.rmtree(version_dir)
        rows = skill_scan.plugin_skills(os.path.join(home, ".claude"), root, home)
        self.assertEqual(rows, [])
        version_dir = add_plugin(home, "p2", "m", [], enabled=True)
        add_skill(version_dir, "root-skill")
        with open(os.path.join(version_dir, "SKILL.md"), "w", encoding="utf-8") as fh:
            fh.write("---\n---\n")
        with open(
            os.path.join(version_dir, ".claude-plugin", "plugin.json"), "w", encoding="utf-8"
        ) as fh:
            json.dump({"name": "p2", "skills": ["../outside"]}, fh)
        rows = skill_scan.plugin_skills(os.path.join(home, ".claude"), root, home)
        self.assertEqual(rows, [])


class TestPonytailVisibility(unittest.TestCase):
    def test_per_host_global_roots_only(self):
        root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        home = make_home(os.path.join(root, "home"))
        codex_root = os.path.join(home, ".agents", "skills")
        os.makedirs(codex_root, exist_ok=True)
        add_skill(codex_root, "ponytail")
        add_skill(codex_root, "ponytail-review")
        roots = {
            "claude": os.path.join(home, ".claude", "skills"),
            "codex": codex_root,
            "opencode": None,
            "cursor": None,
            "pi": None,
        }
        vis = skill_scan.ponytail_visibility(roots)
        self.assertEqual(vis["codex"], ["ponytail", "ponytail-review"])
        for host_name in host.HOSTS:
            if host_name != "codex":
                self.assertEqual(vis[host_name], [])


class _FakeSocket:
    def close(self) -> None:
        return None


class TestSystemOneBackend(unittest.TestCase):
    def _recorder(self):
        calls: list = []

        def connect(endpoint, timeout=None):
            calls.append((endpoint, timeout))
            return _FakeSocket()

        return connect, calls

    def test_empty_url_never_connects(self):
        connect, calls = self._recorder()
        out = skill_scan.system_one_backend({}, connect)
        self.assertEqual(out, {"detected": False, "via": [], "note": ""})
        self.assertEqual(calls, [])

    def test_url_ports_and_schemes(self):
        connect, calls = self._recorder()
        env = {"JEV_API_URL": "https://jev.example:8443/v1"}
        out = skill_scan.system_one_backend(env, connect)
        self.assertEqual(calls, [(("jev.example", 8443), skill_scan.CONNECT_TIMEOUT_S)])
        self.assertEqual(out["via"], ["url_reachable"])
        connect, calls = self._recorder()
        skill_scan.system_one_backend({"JEV_API_URL": "http://h/x"}, connect)
        self.assertEqual(calls[0][0], ("h", 80))
        connect, calls = self._recorder()
        skill_scan.system_one_backend({"JEV_API_URL": "https://h"}, connect)
        self.assertEqual(calls[0][0], ("h", 443))
        connect, calls = self._recorder()
        skill_scan.system_one_backend({"JEV_API_URL": "ftp://h"}, connect)
        skill_scan.system_one_backend({"JEV_API_URL": "https://h:notaport"}, connect)
        self.assertEqual(calls, [])

    def test_connect_errors_and_success_note(self):
        def refuse(endpoint, timeout=None):
            raise OSError("refused")

        out = skill_scan.system_one_backend({"JEV_API_URL": "https://h/"}, refuse)
        self.assertFalse(out["detected"])
        self.assertEqual(out["via"], [])
        connect, _calls = self._recorder()
        out = skill_scan.system_one_backend({"JEV_API_URL": "https://h/"}, connect)
        self.assertEqual(out["note"], skill_scan.URL_NOTE)

    def test_slow_connect_times_out(self):
        import threading
        import time

        gate = threading.Event()

        def slow(endpoint, timeout=None):
            gate.wait()

        env = {"JEV_API_URL": "https://slow.example/"}
        start = time.monotonic()
        with mock.patch.object(skill_scan, "CONNECT_TIMEOUT_S", 0.2):
            out = skill_scan.system_one_backend(env, slow)
        self.addCleanup(gate.set)
        elapsed = time.monotonic() - start
        self.assertLess(elapsed, 1.0)
        self.assertNotIn("url_reachable", out["via"])

    def test_key_present_env_and_secrets(self):
        connect, _calls = self._recorder()
        out = skill_scan.system_one_backend({"JEV_API_KEY": "set"}, connect)
        self.assertIn("key_present", out["via"])
        root = tempfile.mkdtemp()
        self.addCleanup(__import__("shutil").rmtree, root, True)
        cfg = os.path.join(root, ".config", "ai-kit")
        os.makedirs(cfg, exist_ok=True)
        with open(os.path.join(cfg, "secrets.env"), "w", encoding="utf-8") as fh:
            fh.write("JEV_API_KEY=from-file\n")
        out = skill_scan.system_one_backend({"HOME": root}, connect)
        self.assertIn("key_present", out["via"])

    def test_url_and_key_together(self):
        connect, _calls = self._recorder()
        env = {"JEV_API_URL": "https://h/", "JEV_API_KEY": "x"}
        out = skill_scan.system_one_backend(env, connect)
        self.assertEqual(out["via"], ["url_reachable", "key_present"])

    def test_key_value_never_in_output(self):
        root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        home = make_home(os.path.join(root, "home"))
        project = os.path.join(root, "project")
        os.makedirs(project)
        make_gsd_install(os.path.join(project, ".claude", "gsd-core"))
        cfg = os.path.join(home, ".config", "ai-kit")
        os.makedirs(cfg, exist_ok=True)
        with open(os.path.join(cfg, "secrets.env"), "w", encoding="utf-8") as fh:
            fh.write("JEV_API_KEY=sk-SENTINEL-18-03\n")
        env = _inventory_env(home)
        env["JEV_API_URL"] = "https://user:pw-SENTINEL@h:1/"
        connect, calls = self._recorder()

        def node_answer(cmd):
            keys = json.loads(cmd[6])
            return json.dumps(tables_answer(keys, home))

        stdout = __import__("io").StringIO()
        stderr = __import__("io").StringIO()
        with __import__("contextlib").redirect_stdout(stdout), __import__(
            "contextlib"
        ).redirect_stderr(stderr):
            code = __import__("ai_kit_gsd_curated_config.cli", fromlist=["cli"]).main(
                ["inventory", "--project-dir", project, "--host", "codex"],
                which_fn=lambda name, **_kw: "node" if name == "node" else None,
                env_fn=lambda: dict(env),
                run_fn=FakeRun(node_stdout=node_answer),
                connect_fn=connect,
            )
        self.assertEqual(code, 0)
        blob = stdout.getvalue() + stderr.getvalue()
        self.assertNotIn("sk-SENTINEL-18-03", blob)
        self.assertNotIn("pw-SENTINEL", blob)
        self.assertNotIn("https://user:", blob)
        # C-W1: the injected connect_fn reaches the probe (no real network I/O).
        self.assertTrue(calls)
        self.assertEqual(calls[0][0], ("h", 1))

    def test_missing_spec_sibling_env_key_only(self):
        connect, _calls = self._recorder()
        with mock.patch.object(
            skill_scan.gsd_catalog, "load_ai_kit_spec_module", return_value=None
        ):
            out = skill_scan.system_one_backend({"JEV_API_KEY": "x"}, connect)
        self.assertIn("key_present", out["via"])
        with mock.patch.object(
            skill_scan.gsd_catalog, "load_ai_kit_spec_module", return_value=None
        ):
            out = skill_scan.system_one_backend({}, connect)
        self.assertEqual(out["via"], [])


def _inv(
    host="claude",
    skills=None,
    project=None,
    backend=None,
    existing=None,
    extra_accepted=(),
) -> dict:
    inv = make_inventory(
        host=host,
        project=project,
        existing=existing,
        extra_accepted=extra_accepted,
    )
    if skills is not None:
        inv["skills"] = skills
    if backend is not None:
        inv["system_one_backend"] = backend
    return inv


def _skill_row(
    name: str,
    root_kind: str,
    *,
    plugin: str | None = None,
    addressable: bool = True,
    root: str | None = None,
    escapes_root: bool = False,
    real_dir_home: str | None = None,
    real_dir: str | None = None,
    description: str = "",
) -> dict:
    label = root or ("skills" if root_kind == "project" else "~/.claude/skills")
    row = {
        "name": name,
        "root_kind": root_kind,
        "root": label,
        "plugin": plugin,
        "escapes_root": escapes_root,
        "addressable": addressable,
        "description": description,
    }
    if real_dir_home is not None:
        row["real_dir_home"] = real_dir_home
    if real_dir is not None:
        row["real_dir"] = real_dir
    return row


def _inv_existing_roots(roots: list[str], **kwargs) -> dict:
    existing = {
        "exists": True,
        "values": {"agent_skills_security": {"trusted_global_roots": roots}},
    }
    return _inv(existing=existing, **kwargs)


def _escaping_global(
    name: str,
    home_rel: str,
    *,
    real_dir: str | None = None,
) -> dict:
    return _skill_row(
        name,
        "global",
        escapes_root=True,
        real_dir_home=home_rel,
        real_dir=real_dir or home_rel.replace("~/", "home/user/"),
    )


def _shipped_affinity() -> dict:
    doc, err = plan_io.load_affinity(plan_io.AFFINITY_PATH)
    assert doc is not None and err is None
    return doc


def _plan_with_affinity(inv: dict, rigor: str = "standard", affinity: dict | None = None) -> dict:
    aff = affinity if affinity is not None else _shipped_affinity()
    return recommend.build_plan(
        inv,
        recommend.RecommendOpts("adaptive", rigor, affinity=aff),
    )


class TestAffinityValidation(unittest.TestCase):
    def test_validate_affinity_refuses_bad_schema_version(self):
        bad = {"schema_version": 2, "as_of": "x", "families": []}
        self.assertIsNotNone(skills.validate_affinity(bad))

    def test_validate_affinity_refuses_bool_schema_version(self):
        bad = {"schema_version": True, "as_of": "x", "families": []}
        self.assertIsNotNone(skills.validate_affinity(bad))

    def test_validate_affinity_refuses_bad_when(self):
        doc = {
            "schema_version": 1,
            "as_of": "2026-01-01",
            "families": [{"id": "x", "skills": [], "agents": [], "when": "nope"}],
        }
        self.assertIsNotNone(skills.validate_affinity(doc))

    def test_validate_affinity_refuses_non_list_skills(self):
        doc = {
            "schema_version": 1,
            "as_of": "2026-01-01",
            "families": [{"id": "x", "skills": "bad", "agents": [], "when": None}],
        }
        self.assertIsNotNone(skills.validate_affinity(doc))

    def test_validate_affinity_refuses_duplicate_family_id(self):
        fam = {"id": "dup", "skills": ["a"], "agents": ["gsd-planner"], "when": None}
        doc = {"schema_version": 1, "as_of": "2026-01-01", "families": [fam, fam]}
        self.assertIsNotNone(skills.validate_affinity(doc))

    def test_validate_affinity_refuses_family_id_equal_to_skill_name(self):
        """C-W5: a family id that is also a skill name would name that skill in notes."""
        doc = {
            "schema_version": 1,
            "as_of": "2026-01-01",
            "families": [
                {"id": "a", "skills": ["b"], "agents": ["gsd-planner"], "when": None},
                {"id": "b", "skills": ["c"], "agents": ["gsd-planner"], "when": None},
            ],
        }
        problem = skills.validate_affinity(doc)
        self.assertIsNotNone(problem)
        self.assertIn("'b'", problem or "")
        self.assertIsNone(skills.validate_affinity(_shipped_affinity()))

    def test_load_affinity_invalid_file_suffix(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as handle:
            json.dump({"schema_version": 2, "as_of": "x", "families": []}, handle)
            path = handle.name
        try:
            _doc, err = plan_io.load_affinity(path)
            self.assertIsNone(_doc)
            self.assertTrue(err is not None and err.endswith("; fix skill_affinity.json"))
        finally:
            os.unlink(path)


class TestAffinityResolve(unittest.TestCase):
    def test_reference_for_encoding(self):
        self.assertEqual(skills.reference_for(_skill_row("x", "project")), "skills/x")
        self.assertEqual(skills.reference_for(_skill_row("x", "global")), "global:x")
        row = _skill_row("ponytail-review", "plugin", plugin="ponytail")
        self.assertEqual(skills.reference_for(row), "global:ponytail:ponytail-review")

    def test_dotted_plugin_not_addressable(self):
        row = _skill_row("s", "plugin", plugin="bad.name", addressable=False)
        inv = _inv(skills=[row])
        self.assertIsNone(skills.locate("s", inv))

    def test_cap_boundary_standard_drops_fourth(self):
        affinity = {
            "schema_version": 1,
            "as_of": "t",
            "families": [
                {"id": "f1", "skills": ["a"], "agents": ["gsd-planner"], "when": None},
                {"id": "f2", "skills": ["b"], "agents": ["gsd-planner"], "when": None},
                {"id": "f3", "skills": ["c"], "agents": ["gsd-planner"], "when": None},
                {"id": "f4", "skills": ["d"], "agents": ["gsd-planner"], "when": None},
            ],
        }
        inv = _inv(skills=[_skill_row(n, "global") for n in ("a", "b", "c", "d")],
        )
        facts = skills.skill_facts(inv, [], {})
        resolved, _notes = skills.resolve(affinity, inv, facts, "standard")
        self.assertEqual(resolved.get("gsd-planner"), ["a", "b", "c"])

    def test_cap_rigorous_keeps_four(self):
        affinity = {
            "schema_version": 1,
            "as_of": "t",
            "families": [
                {"id": "f1", "skills": ["a"], "agents": ["gsd-planner"], "when": None},
                {"id": "f2", "skills": ["b"], "agents": ["gsd-planner"], "when": None},
                {"id": "f3", "skills": ["c"], "agents": ["gsd-planner"], "when": None},
                {"id": "f4", "skills": ["d"], "agents": ["gsd-planner"], "when": None},
            ],
        }
        inv = _inv(skills=[_skill_row(n, "global") for n in ("a", "b", "c", "d")],
        )
        resolved, _ = skills.resolve(affinity, inv, skills.skill_facts(inv, [], {}), "rigorous")
        self.assertEqual(resolved.get("gsd-planner"), ["a", "b", "c", "d"])

    def test_empty_agent_no_entry(self):
        affinity = {
            "schema_version": 1,
            "as_of": "t",
            "families": [
                {"id": "f1", "skills": ["a"], "agents": ["gsd-planner"], "when": None},
            ],
        }
        inv = _inv(skills=[])
        resolved, _ = skills.resolve(affinity, inv, skills.skill_facts(inv, [], {}), "standard")
        self.assertNotIn("gsd-debugger", resolved)

    def test_dedupe_same_skill_two_families(self):
        affinity = {
            "schema_version": 1,
            "as_of": "t",
            "families": [
                {"id": "f1", "skills": ["shared"], "agents": ["gsd-executor"], "when": None},
                {"id": "f2", "skills": ["shared"], "agents": ["gsd-executor"], "when": None},
            ],
        }
        inv = _inv(skills=[_skill_row("shared", "global")])
        resolved, _ = skills.resolve(affinity, inv, skills.skill_facts(inv, [], {}), "standard")
        self.assertEqual(resolved["gsd-executor"], ["shared"])

    def test_unknown_agent_note(self):
        affinity = {
            "schema_version": 1,
            "as_of": "t",
            "families": [
                {"id": "fam-x", "skills": ["a"], "agents": ["not-a-real-agent"], "when": None},
            ],
        }
        inv = _inv(skills=[_skill_row("a", "global")])
        facts = skills.skill_facts(inv, [], {})
        _resolved, notes = skills.resolve(affinity, inv, facts, "standard")
        self.assertEqual(len(notes), 1)
        self.assertIn("not-a-real-agent", notes[0]["text"])
        self.assertIn("fam-x", notes[0]["text"])

    def test_unknown_agent_note_needs_a_wireable_family_skill(self):
        """C-W5: no drop note (naming the family) when the family would wire nothing."""
        inv = _inv(host="codex", skills=[])
        plan = _plan_with_affinity(inv)
        agent_notes = [n for n in plan["notes"] if n["kind"] == "affinity_agent"]
        self.assertEqual(agent_notes, [])
        self.assertNotIn("ponytail", json.dumps(plan["notes"]))
        inv = _inv(host="codex", skills=[_skill_row("ponytail-review", "global")])
        plan = _plan_with_affinity(inv)
        texts = [n["text"] for n in plan["notes"] if n["kind"] == "affinity_agent"]
        self.assertIn(
            "dropped unknown agent gsd-security-auditor from family ponytail-reviewers", texts
        )

    def test_precedence_project_over_global_and_plugin(self):
        inv = _inv(skills=[
                _skill_row("dup", "plugin", plugin="ponytail"),
                _skill_row("dup", "global"),
                _skill_row("dup", "project"),
            ],
        )
        row = skills.locate("dup", inv)
        assert row is not None
        self.assertEqual(row["root_kind"], "project")

    def test_global_beats_plugin(self):
        inv = _inv(skills=[
                _skill_row("dup", "plugin", plugin="ponytail"),
                _skill_row("dup", "global"),
            ],
        )
        row = skills.locate("dup", inv)
        assert row is not None
        self.assertEqual(row["root_kind"], "global")

    def test_frontend_gate(self):
        affinity = {
            "schema_version": 1,
            "as_of": "t",
            "families": [
                {
                    "id": "frontend",
                    "skills": ["react-dev"],
                    "agents": ["gsd-executor"],
                    "when": "frontend",
                },
            ],
        }
        inv = _inv(skills=[_skill_row("react-dev", "global")])
        facts_off = skills.skill_facts(inv, [], {})
        resolved_off, _ = skills.resolve(affinity, inv, facts_off, "standard")
        self.assertNotIn("gsd-executor", resolved_off)
        inv_on = _inv(
            project={"frontend": True, "intel_index_present": False, "db": False},
            skills=[_skill_row("react-dev", "global")],
        )
        facts_on = skills.skill_facts(inv_on, [], {})
        resolved_on, _ = skills.resolve(affinity, inv_on, facts_on, "standard")
        self.assertEqual(resolved_on.get("gsd-executor"), ["react-dev"])

    def test_tdd_gate_from_prior_entry(self):
        affinity = {
            "schema_version": 1,
            "as_of": "t",
            "families": [
                {
                    "id": "tdd",
                    "skills": ["test-driven-development"],
                    "agents": ["gsd-planner"],
                    "when": "tdd_mode",
                },
            ],
        }
        inv = _inv(skills=[_skill_row("test-driven-development", "global")])
        prior = [{"key": "workflow.tdd_mode", "value": True}]
        facts = skills.skill_facts(inv, prior, {})
        resolved, _ = skills.resolve(affinity, inv, facts, "rigorous")
        self.assertEqual(resolved.get("gsd-planner"), ["test-driven-development"])

    def test_db_gate(self):
        affinity = {
            "schema_version": 1,
            "as_of": "t",
            "families": [
                {
                    "id": "db",
                    "skills": ["database-schema-designer"],
                    "agents": ["gsd-planner"],
                    "when": "db",
                },
            ],
        }
        inv = _inv(
            project={"frontend": False, "intel_index_present": False, "db": True},
            skills=[_skill_row("database-schema-designer", "global")],
        )
        resolved, _ = skills.resolve(affinity, inv, skills.skill_facts(inv, [], {}), "standard")
        self.assertEqual(resolved.get("gsd-planner"), ["database-schema-designer"])

    def test_jev_once_with_backend(self):
        affinity = {
            "schema_version": 1,
            "as_of": "t",
            "families": [
                {
                    "id": "system-one",
                    "skills": ["jev-fast-decision"],
                    "agents": ["gsd-advisor-researcher", "gsd-assumptions-analyzer"],
                    "when": "system_one_backend",
                },
            ],
        }
        inv = _inv(
            skills=[_skill_row("jev-fast-decision", "global")],
            backend={"detected": True, "via": ["url_reachable", "key_present"], "note": ""},
        )
        inv["gsd_core"]["agent_to_phase_type"]["gsd-advisor-researcher"] = "research"
        inv["gsd_core"]["agent_to_phase_type"]["gsd-assumptions-analyzer"] = "research"
        resolved, _ = skills.resolve(affinity, inv, skills.skill_facts(inv, [], {}), "standard")
        self.assertEqual(resolved["gsd-advisor-researcher"], ["jev-fast-decision"])
        self.assertEqual(resolved["gsd-assumptions-analyzer"], ["jev-fast-decision"])

    def _jev_inv(self, rows, backend=None) -> dict:
        """C-W13: both system-one agents known, so only the gate or the skill can stop it."""
        inv = _inv(
            skills=rows,
            backend=backend,
            extra_accepted=[
                "agent_skills.gsd-advisor-researcher",
                "agent_skills.gsd-assumptions-analyzer",
            ],
        )
        inv["gsd_core"]["agent_to_phase_type"].update({
            "gsd-advisor-researcher": "research",
            "gsd-assumptions-analyzer": "research",
        })
        return inv

    def _assert_jev_silent(self, plan: dict) -> None:
        self.assertNotIn("jev-fast-decision", json.dumps(plan))
        agent_notes = [n for n in plan["notes"] if n["kind"] == "affinity_agent"]
        self.assertFalse(any("advisor" in n["text"] or "assumptions" in n["text"]
                             for n in agent_notes))

    def test_jev_without_backend_not_wired(self):
        jev = [_skill_row("jev-fast-decision", "global")]
        self._assert_jev_silent(_plan_with_affinity(self._jev_inv(jev)))
        backend = {"detected": True, "via": ["key_present"], "note": ""}
        wired = entry_map(_plan_with_affinity(self._jev_inv(jev, backend)))
        self.assertEqual(
            wired["agent_skills.gsd-advisor-researcher"]["value"], ["jev-fast-decision"]
        )

    def test_jev_backend_without_skill_silent(self):
        backend = {"detected": True, "via": ["key_present"], "note": ""}
        self._assert_jev_silent(_plan_with_affinity(self._jev_inv([], backend)))
        jev = [_skill_row("jev-fast-decision", "global")]
        wired = entry_map(_plan_with_affinity(self._jev_inv(jev, backend)))
        self.assertIn("agent_skills.gsd-assumptions-analyzer", wired)


class TestTrustedRoots(unittest.TestCase):
    def test_two_escaping_skills_sorted_candidates(self):
        wired = {
            "z-skill": _escaping_global("z-skill", "~/.vault/z-skill"),
            "a-skill": _escaping_global("a-skill", "~/.vault/a-skill"),
        }
        candidates = skills.trusted_roots(wired, _inv())
        self.assertEqual(
            [item["value"] for item in candidates],
            ["~/.vault/a-skill", "~/.vault/z-skill"],
        )

    def test_same_real_dir_deduped(self):
        wired = {
            "one": _escaping_global("one", "~/.vault/shared"),
            "two": _escaping_global("two", "~/.vault/shared"),
        }
        candidates = skills.trusted_roots(wired, _inv())
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["value"], "~/.vault/shared")

    def test_usable_project_copy_suppresses_candidate(self):
        wired = {
            "react-dev": _escaping_global("react-dev", "~/.agents/skills/react-dev"),
        }
        inv = _inv(skills=[
            _skill_row("react-dev", "project"),
            _escaping_global("react-dev", "~/.agents/skills/react-dev"),
        ])
        candidates = skills.trusted_roots(wired, inv)
        self.assertEqual(candidates, [])

    def test_existing_roots_cover_all_proposed(self):
        wired = {"react-dev": _escaping_global("react-dev", "~/.agents/skills/react-dev")}
        inv = _inv_existing_roots(["~/.agents/skills/react-dev"])
        candidates = skills.trusted_roots(wired, inv)
        self.assertEqual(candidates, [])

    def test_partial_existing_trust_merged_why(self):
        wired = {"react-dev": _escaping_global("react-dev", "~/.agents/skills/react-dev")}
        inv = _inv_existing_roots(["~/vault"])
        candidates = skills.trusted_roots(wired, inv)
        self.assertEqual(candidates[0]["value"], "~/.agents/skills/react-dev")
        why = skills.merged_trusted_roots_why(candidates, inv)
        self.assertIn('["~/vault","~/.agents/skills/react-dev"]', why)

    def test_absolute_existing_root_kept_in_merged_why(self):
        root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        vault = os.path.join(root, "vault")
        wired = {"react-dev": _escaping_global("react-dev", "~/.agents/skills/react-dev")}
        inv = _inv_existing_roots([vault])
        candidates = skills.trusted_roots(wired, inv)
        why = skills.merged_trusted_roots_why(candidates, inv)
        self.assertTrue(why.startswith("approve with plan-set"))
        self.assertIn(vault, why)
        self.assertIn("~/.agents/skills/react-dev", why)

    def test_merged_why_command_is_shell_quoted(self):
        """C-W9: a root holding a quote still yields one runnable plan-set argument."""
        wired = {"react-dev": _escaping_global("react-dev", "~/.agents/skills/react-dev")}
        inv = _inv_existing_roots(["~/Bob's skills/x"])
        candidates = skills.trusted_roots(wired, inv)
        why = skills.merged_trusted_roots_why(candidates, inv)
        command = why.split(" or keep the current value", 1)[0]
        argv = shlex.split(command.removeprefix("approve with "))
        self.assertEqual(argv[:2], ["plan-set", "agent_skills_security.trusted_global_roots"])
        self.assertEqual(
            json.loads(argv[2]), ["~/Bob's skills/x", "~/.agents/skills/react-dev"]
        )

    def test_ancestor_home_root_covers(self):
        wired = {"react-dev": _escaping_global("react-dev", "~/.agents/skills/react-dev")}
        inv = _inv_existing_roots(["~/.agents/skills"])
        candidates = skills.trusted_roots(wired, inv)
        self.assertEqual(candidates, [])

    def test_absolute_ancestor_covers(self):
        root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        parent = os.path.join(root, "agents", "skills")
        real = os.path.join(parent, "react-dev")
        wired = {
            "react-dev": _escaping_global(
                "react-dev",
                "~/.agents/skills/react-dev",
                real_dir=real,
            ),
        }
        inv = _inv_existing_roots([parent])
        candidates = skills.trusted_roots(wired, inv)
        self.assertEqual(candidates, [])

    def test_similar_prefix_does_not_cover(self):
        wired = {"react-dev": _escaping_global("react-dev", "~/.agents/skills/react-dev")}
        inv = _inv_existing_roots(["~/.agents/skills-other"])
        candidates = skills.trusted_roots(wired, inv)
        self.assertEqual(len(candidates), 1)

    def test_too_broad_roots_never_cover(self):
        """C-IN-08: gsd-core drops /, ~ and the home dir itself, so they cover nothing."""
        for root in ("/", "~", "~/", "/home/user", "/home/user/"):
            with self.subTest(root=root):
                self.assertFalse(
                    skills.covered("~/.vault/x", "/home/user/.vault/x", [root])
                )
                self.assertFalse(skills.covered("", "/opt/x", [root]))
        self.assertTrue(skills.covered("~/.vault/x", "/home/user/.vault/x", ["/home/user/.vault"]))

    def test_covered_lexical(self):
        self.assertTrue(
            skills.covered("~/.agents/skills/x", "/any", ["~/.agents/skills"])
        )
        self.assertFalse(
            skills.covered("~/.agents/skills/x", "/any", ["~/.agents/skills-other"])
        )

    def test_escaping_project_skipped_global_wins(self):
        inv = _inv(skills=[
            _skill_row("foo", "project", escapes_root=True),
            _skill_row("foo", "global"),
        ])
        row = skills.locate("foo", inv)
        assert row is not None
        self.assertEqual(row["root_kind"], "global")

    def test_project_only_escaping_unwired_note(self):
        affinity = {
            "schema_version": 1,
            "as_of": "t",
            "families": [
                {"id": "f", "skills": ["foo"], "agents": ["gsd-planner"], "when": None},
            ],
        }
        inv = _inv(skills=[_skill_row("foo", "project", escapes_root=True)])
        facts = skills.skill_facts(inv, [], {})
        _resolved, notes = skills.resolve(affinity, inv, facts, "standard")
        self.assertEqual(len(notes), 1)
        self.assertIn("outside the project", notes[0]["text"])
        self.assertNotIn("/", notes[0]["text"].split("outside the project")[0])

    def test_outside_home_global_unwired(self):
        affinity = {
            "schema_version": 1,
            "as_of": "t",
            "families": [
                {"id": "f", "skills": ["away"], "agents": ["gsd-planner"], "when": None},
            ],
        }
        inv = _inv(skills=[
            _skill_row(
                "away",
                "global",
                escapes_root=True,
                real_dir="/outside/away",
                real_dir_home=None,
            ),
        ])
        resolved, notes = skills.resolve(affinity, inv, skills.skill_facts(inv, [], {}), "standard")
        self.assertEqual(resolved, {})
        self.assertEqual(len(notes), 1)
        self.assertIn("outside the home directory", notes[0]["text"])

    def test_outside_home_global_covered_by_absolute_root_wired(self):
        """C-W3: an already-configured absolute trusted root covers an outside-home skill."""
        affinity = {
            "schema_version": 1,
            "as_of": "t",
            "families": [
                {"id": "f", "skills": ["away"], "agents": ["gsd-planner"], "when": None},
            ],
        }
        inv = _inv_existing_roots(["/opt/skills"], skills=[
            _skill_row(
                "away",
                "global",
                escapes_root=True,
                real_dir="/opt/skills/away",
                real_dir_home=None,
            ),
        ])
        resolved, notes = skills.resolve(affinity, inv, skills.skill_facts(inv, [], {}), "standard")
        self.assertEqual(resolved, {"gsd-planner": ["away"]})
        self.assertEqual(notes, [])
        candidates = skills.trusted_roots(skills.wired_skills(resolved, inv), inv)
        self.assertEqual(candidates, [])

    def test_project_outside_home_still_wired(self):
        affinity = {
            "schema_version": 1,
            "as_of": "t",
            "families": [
                {"id": "f", "skills": ["local"], "agents": ["gsd-planner"], "when": None},
            ],
        }
        inv = _inv(skills=[
            _skill_row(
                "local",
                "project",
                real_dir="/outside/local",
                real_dir_home=None,
            ),
        ])
        resolved, _notes = skills.resolve(
            affinity, inv, skills.skill_facts(inv, [], {}), "standard",
        )
        self.assertEqual(resolved.get("gsd-planner"), ["local"])


class TestProposals(unittest.TestCase):
    def test_unknown_skill_with_description(self):
        inv = _inv(skills=[_skill_row("chart", "global", description="Draws charts")])
        notes = skills.proposals(_shipped_affinity(), inv)
        self.assertEqual(len(notes), 1)
        self.assertEqual(notes[0]["kind"], "skill_proposal")
        self.assertIn("Draws charts", notes[0]["text"])

    def test_proposal_shows_runnable_json_list(self):
        """C-W7: the proposal's plan-set value is the JSON list plan-set parses."""
        inv = _inv(skills=[_skill_row("chart", "global", description="Draws charts")])
        text = skills.proposals(_shipped_affinity(), inv)[0]["text"]
        command = text.split("wire with ", 1)[1].split(" (", 1)[0]
        argv = shlex.split(command)
        self.assertEqual(argv[:2], ["plan-set", "agent_skills.<agent>"])
        self.assertEqual(json.loads(argv[2]), ["chart"])
        self.assertIn("whole list", text)

    def test_empty_description_skipped(self):
        inv = _inv(skills=[_skill_row("quiet", "global", description="")])
        self.assertEqual(skills.proposals(_shipped_affinity(), inv), [])

    def test_gsd_prefix_skipped(self):
        inv = _inv(skills=[_skill_row("gsd-foo", "global", description="x")])
        self.assertEqual(skills.proposals(_shipped_affinity(), inv), [])

    def test_family_skill_skipped(self):
        inv = _inv(skills=[_skill_row("ponytail", "global", description="x")])
        self.assertEqual(skills.proposals(_shipped_affinity(), inv), [])

    def test_only_wireable_skills_once_per_name(self):
        """C-W6: no proposal plan-set would refuse or gsd-core would skip; one per name."""
        inv = _inv(skills=[
            _skill_row("esc", "project", escapes_root=True, description="d"),
            _skill_row(
                "away", "global", escapes_root=True, real_dir="/outside/away",
                real_dir_home=None, description="d",
            ),
            _skill_row("dup", "global", description="global copy"),
            _skill_row("dup", "plugin", plugin="p", description="plugin copy"),
        ])
        notes = skills.proposals(_shipped_affinity(), inv)
        self.assertEqual([n["key"] for n in notes], ["dup"])
        self.assertIn("global copy", notes[0]["text"])

    def test_cap_and_more_note(self):
        rows = [
            _skill_row(f"skill-{idx:02d}", "global", description="d")
            for idx in range(12)
        ]
        inv = _inv(skills=rows)
        notes = skills.proposals(_shipped_affinity(), inv)
        proposals_only = [n for n in notes if n["kind"] == "skill_proposal"]
        self.assertEqual(len(proposals_only), skills.PROPOSAL_CAP)
        self.assertEqual(proposals_only[0]["key"], "skill-00")
        more = [n for n in notes if n["kind"] == "skill_proposal_more"]
        self.assertEqual(len(more), 1)
        self.assertIn("2 more", more[0]["text"])


class TestSkillNotes(unittest.TestCase):
    def test_jev_wired_session_gate_note(self):
        inv = _inv(
            skills=[_skill_row("jev-fast-decision", "global")],
            backend={"detected": True, "via": ["key_present"], "note": ""},
            extra_accepted=[
                "agent_skills.gsd-advisor-researcher",
                "agent_skills.gsd-assumptions-analyzer",
            ],
        )
        inv["gsd_core"]["agent_to_phase_type"]["gsd-advisor-researcher"] = "research"
        inv["gsd_core"]["agent_to_phase_type"]["gsd-assumptions-analyzer"] = "research"
        plan = _plan_with_affinity(inv)
        kinds = [n["kind"] for n in plan["notes"]]
        self.assertIn("jev_session_gate", kinds)
        gate = next(n for n in plan["notes"] if n["kind"] == "jev_session_gate")
        self.assertIn("GSD_PATH_JEV=1", gate["text"])
        self.assertIn("GSD_PATH_JEV_TIMEOUT_SECONDS", gate["text"])

    def test_jev_unwired_no_gate_note(self):
        inv = _inv(skills=[_skill_row("jev-fast-decision", "global")])
        plan = _plan_with_affinity(inv)
        self.assertFalse(any(n["kind"] == "jev_session_gate" for n in plan["notes"]))

    def test_pi_agent_skills_effect(self):
        inv = _inv(host="pi", skills=[_skill_row("ponytail", "global")])
        plan = _plan_with_affinity(inv, rigor="mvp")
        skill_entries = [e for e in plan["entries"] if e["key"].startswith("agent_skills.")]
        self.assertTrue(skill_entries)
        for entry in skill_entries:
            self.assertEqual(entry["effect"], "no effect on pi (no GSD agent files installed)")

    def test_plugin_wired_entry_flagged_unverified(self):
        """C-W11: wiring that rests on the assumed enabledPlugins layering says so."""
        inv = _inv(skills=[
            _skill_row("ponytail", "plugin", plugin="ponytail"),
            _skill_row("systematic-debugging", "global"),
        ])
        em = entry_map(_plan_with_affinity(inv))
        self.assertIn("enabledPlugins", em["agent_skills.gsd-planner"]["effect"])
        self.assertIn("unverified", em["agent_skills.gsd-planner"]["effect"])
        inv = _inv(skills=[_skill_row("ponytail", "global")])
        self.assertNotIn("effect", entry_map(_plan_with_affinity(inv))["agent_skills.gsd-planner"])

    def test_url_only_jev_entry_flagged(self):
        """C-W11: a backend seen only by TCP reachability is not presented as System One."""
        for via, flagged in ((["url_reachable"], True), (["url_reachable", "key_present"], False)):
            inv = _inv(
                skills=[_skill_row("jev-fast-decision", "global")],
                backend={"detected": True, "via": via, "note": ""},
                extra_accepted=[
                    "agent_skills.gsd-advisor-researcher",
                    "agent_skills.gsd-assumptions-analyzer",
                ],
            )
            inv["gsd_core"]["agent_to_phase_type"] = {
                **inv["gsd_core"]["agent_to_phase_type"],
                "gsd-advisor-researcher": "research",
                "gsd-assumptions-analyzer": "research",
            }
            entry = entry_map(_plan_with_affinity(inv))["agent_skills.gsd-advisor-researcher"]
            with self.subTest(via=via):
                self.assertEqual(
                    "not verified as System One" in entry.get("effect", ""), flagged
                )

    def test_trusted_root_entry_on_escaping_global(self):
        inv = _inv(
            project={"frontend": True, "intel_index_present": False, "db": False},
            skills=[_escaping_global("react-dev", "~/.agents/skills/react-dev")],
        )
        plan = _plan_with_affinity(inv)
        em = entry_map(plan)
        entry = em["agent_skills_security.trusted_global_roots"]
        self.assertEqual(entry["status"], "needs_choice")
        self.assertIsNone(entry["value"])
        self.assertIn("plan-unset", entry["why"])
        self.assertIn("skips", entry["why"])


class TestTrustedRootCandidate(unittest.TestCase):
    def test_candidate_value_is_the_merged_list(self):
        """C-W8 (proposal side): the one candidate keeps the configured roots."""
        inv = _inv_existing_roots(
            ["~/vault"],
            project={"frontend": True, "intel_index_present": False, "db": False},
            skills=[_escaping_global("react-dev", "~/.agents/skills/react-dev")],
        )
        entry = entry_map(_plan_with_affinity(inv))["agent_skills_security.trusted_global_roots"]
        self.assertEqual(len(entry["candidates"]), 1)
        candidate = entry["candidates"][0]
        self.assertEqual(candidate["value"], ["~/vault", "~/.agents/skills/react-dev"])
        self.assertEqual(candidate["skills"], ["react-dev"])


class TestSkillsLayer(unittest.TestCase):
    def test_mvp_reviewer_ponytail_not_reducing_entropy(self):
        with tempfile.TemporaryDirectory() as root:
            home = make_home(root)
            add_plugin(
                home,
                "ponytail",
                "ponytail",
                ["ponytail-review", "ponytail-audit", "ponytail"],
            )
            add_skill(os.path.join(home, ".claude", "skills"), "reducing-entropy")
            inv = make_inventory(host="claude")
            inv["skills"] = skill_scan.scan_skills(
                root,
                "claude",
                {"claude": os.path.join(home, ".claude", "skills")},
                home,
            )
            plan = _plan_with_affinity(inv, rigor="mvp")
            em = {e["key"]: e["value"] for e in plan["entries"]}
            self.assertEqual(
                em.get("agent_skills.gsd-code-reviewer"),
                ["ponytail-review", "ponytail-audit"],
            )

    def test_executor_ponytail_once(self):
        affinity = {
            "schema_version": 1,
            "as_of": "t",
            "families": [
                {"id": "a", "skills": ["ponytail"], "agents": ["gsd-executor"], "when": None},
                {"id": "b", "skills": ["ponytail"], "agents": ["gsd-executor"], "when": None},
            ],
        }
        inv = _inv(skills=[_skill_row("ponytail", "plugin", plugin="ponytail")])
        plan = _plan_with_affinity(inv, rigor="standard", affinity=affinity)
        em = {e["key"]: e["value"] for e in plan["entries"]}
        self.assertEqual(em["agent_skills.gsd-executor"], ["ponytail"])

    def test_no_ponytail_inventory_no_names(self):
        inv = _inv(skills=[])
        plan = _plan_with_affinity(inv, rigor="standard")
        skill_entries = [e for e in plan["entries"] if e["key"].startswith("agent_skills.")]
        self.assertEqual(skill_entries, [])

    def test_missing_skill_never_named(self):
        ghost = "ghost-skill-not-installed"
        affinity = {
            "schema_version": 1,
            "as_of": "t",
            "families": [
                {"id": "g", "skills": [ghost], "agents": ["gsd-planner"], "when": None},
            ],
        }
        inv = _inv(skills=[])
        plan = _plan_with_affinity(inv, rigor="standard", affinity=affinity)
        blob = json.dumps(plan)
        self.assertNotIn(ghost, blob)
        # C-W13: the debugging family's agents are known, so only the install check decides.
        inv["gsd_core"]["agent_to_phase_type"].update(
            {"gsd-debugger": "debug", "gsd-debug-session-manager": "debug"}
        )
        code, _plan, _bytes, err = run_recommend(
            inv, "--profile", "adaptive", "--rigor", "standard"
        )
        self.assertEqual(code, 0)
        self.assertNotIn("systematic-debugging", blob + json.dumps(_plan) + err)
        inv["skills"] = [_skill_row("systematic-debugging", "global")]
        inv["gsd_core"]["valid_keys"]["accepted"] += [
            "agent_skills.gsd-debugger", "agent_skills.gsd-debug-session-manager",
        ]
        wired = entry_map(_plan_with_affinity(inv))
        self.assertEqual(wired["agent_skills.gsd-debugger"]["value"], ["systematic-debugging"])


if __name__ == "__main__":
    unittest.main()
