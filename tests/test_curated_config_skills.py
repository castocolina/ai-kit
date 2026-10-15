"""Skill scan and System One backend detection for curated-config inventory (18-03)."""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "skills", "ai-kit-gsd-curated-config"),
)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills", "ai-kit-spec-review"))

from ai_kit_gsd_curated_config import host

from tests.test_curated_config_golden import tables_answer
from tests.test_curated_config_inventory import (
    FakeRun,
    _inventory_env,
    make_gsd_install,
    run_inventory,
)


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
