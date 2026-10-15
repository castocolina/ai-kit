"""E2E tier: real node apply through checkout-local gsd-core under a scratch HOME/GSD_HOME.

Skips when node or `.claude/gsd-core/bin/gsd-tools.cjs` is missing or gsd-core is not 1.16.x.
"""
from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "skills", "ai-kit-gsd-curated-config"),
)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills", "ai-kit-spec-review"))

from ai_kit_gsd_curated_config import cli, config_backup, cross_ai_script, plan_io
from ai_kit_spec import gsd_tools

from tests.test_curated_config_apply import (
    FakeRun,
    _decide_all_choices,
    _scratch_env,
    scratch_inventory,
)
from tests.test_curated_config_e2e import REPO_ROOT, _real_node_executable, _RealGsdTestCase
from tests.test_curated_config_golden import load_fixture, tables_answer
from tests.test_curated_config_inventory import seed_cache
from tests.test_curated_config_recommend import run_recommend
from tests.test_curated_config_skills import add_plugin, add_skill

_REPO_CONFIG = REPO_ROOT / ".planning" / "config.json"
_REPO_RUNNER = REPO_ROOT / ".planning" / "scripts" / "cross-ai.mjs"


def _sha256(path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        digest.update(handle.read())
    return digest.hexdigest()


def _seed_home(home: str) -> None:
    add_plugin(
        home,
        "ponytail",
        "ponytail",
        [
            "ponytail",
            "ponytail-audit",
            "ponytail-debt",
            "ponytail-review",
            "ponytail-gain",
            "ponytail-help",
        ],
    )
    agents_skills = os.path.join(home, ".agents", "skills")
    os.makedirs(agents_skills, exist_ok=True)
    add_skill(agents_skills, "react-dev", "React patterns")
    claude_skills = os.path.join(home, ".claude", "skills")
    os.makedirs(claude_skills, exist_ok=True)
    os.symlink(
        os.path.join(agents_skills, "react-dev"),
        os.path.join(claude_skills, "react-dev"),
    )


def _tables_fake(config_path: str, home: str) -> FakeRun:
    return FakeRun(
        node_stdout=lambda argv, h=home: json.dumps(tables_answer(json.loads(argv[6]), h)),
        config_path_stdout=config_path,
    )


def _real_run(child_env: dict):
    def run(cmd, **kw):
        call_env = kw.pop("env", None) or {}
        return subprocess.run(cmd, env={**child_env, **call_env}, **kw)

    return run


def _real_apply(plan_path, inv_path, project, resolve_env, child_env, node_bin):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = cli.main(
            [
                "apply",
                "--plan",
                plan_path,
                "--inventory",
                inv_path,
                "--project-dir",
                project,
            ],
            which_fn=lambda name: node_bin if name == "node" else None,
            env_fn=lambda: dict(resolve_env),
            run_fn=_real_run(child_env),
        )
    parsed = json.loads(out.getvalue()) if out.getvalue().strip() else None
    return code, parsed, out.getvalue(), err.getvalue()


class TestRealApply(_RealGsdTestCase):
    def test_apply_golden_plan(self) -> None:
        node_bin = _real_node_executable()
        tools = REPO_ROOT / ".claude" / "gsd-core" / "bin" / "gsd-tools.cjs"
        if node_bin is None or not tools.is_file():
            self.skipTest("no node or checkout-local gsd-tools.cjs")
        version = gsd_tools.gsd_core_version(str(tools))
        if not version or not version.startswith("1.16."):
            self.skipTest(f"checkout-local gsd-core is {version}; need 1.16.x")

        before_cfg = _sha256(_REPO_CONFIG)
        before_runner = _sha256(_REPO_RUNNER)

        scratch = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, scratch, ignore_errors=True)
        project = os.path.join(scratch, "project")
        home = os.path.join(scratch, "home")
        gsd_home = os.path.join(scratch, "gsd_home")
        xdg = os.path.join(scratch, "xdg")
        os.makedirs(project)
        _seed_home(home)
        os.makedirs(os.path.join(project, ".planning"), exist_ok=True)
        with open(os.path.join(project, "AGENTS.md"), "w", encoding="utf-8") as handle:
            handle.write("# agents\n")
        with open(os.path.join(project, "package.json"), "w", encoding="utf-8") as handle:
            json.dump({"dependencies": {"react": "19.0.0"}}, handle)
        config_path = os.path.join(project, ".planning", "config.json")
        with open(config_path, "w", encoding="utf-8") as handle:
            handle.write('{\n    "model_profile": "balanced"\n}\n')
        seed_cache(xdg, load_fixture("runtimes.json"), load_fixture("model-catalog.json"))
        env = _scratch_env(home, gsd_home, xdg)
        resolve_env = {**env, "RUNTIME_DIR": str(REPO_ROOT)}
        child_env = dict(env)
        fake = _tables_fake(config_path, home)
        inv_path = os.path.join(scratch, "inv.json")
        inv = scratch_inventory(project, resolve_env, fake, inv_path, host_name="claude")
        inv["existing_config"]["path"] = config_path
        with open(inv_path, "w", encoding="utf-8") as handle:
            handle.write(plan_io.canonical_json(inv))

        plan_path = os.path.join(scratch, "plan.json")
        code, _plan, raw, err = run_recommend(
            inv, "--profile", "adaptive", "--rigor", "standard"
        )
        self.assertEqual((code, err), (0, ""))
        assert raw is not None
        with open(plan_path, "wb") as handle:
            handle.write(raw)
        _decide_all_choices(plan_path, inv_path)

        code, report, _stdout, apply_err = _real_apply(
            plan_path, inv_path, project, resolve_env, child_env, node_bin
        )
        self.assertEqual((code, apply_err.strip()), (0, ""))
        assert report is not None
        self.assertTrue(report["applied"])

        got = gsd_tools.config_get(
            gsd_tools.GsdTools(node_bin, str(tools)),
            project,
            "agent_skills.gsd-executor",
            run_fn=lambda cmd, **kw: subprocess.run(cmd, env=child_env, **kw),
        )
        self.assertIsNone(got.error)
        self.assertEqual(
            got.value,
            ["global:ponytail:ponytail", "global:react-dev"],
        )

        for key, row in report["skill_check"].items():
            if key == "skipped":
                continue
            self.assertEqual(row.get("warnings"), [])

        runner = os.path.join(project, ".planning", "scripts", "cross-ai.mjs")
        self.assertTrue(os.path.isfile(runner))
        with open(runner, "rb") as handle:
            self.assertEqual(cross_ai_script.script_state(handle.read()), "pristine")

        script = report["script"]
        assert script is not None
        self.assertEqual(script["kind"], "add")
        self.assertTrue(script["active"])

        cmd = gsd_tools.config_get(
            gsd_tools.GsdTools(node_bin, str(tools)),
            project,
            "workflow.cross_ai_command",
            run_fn=lambda cmd, **kw: subprocess.run(cmd, env=child_env, **kw),
        )
        self.assertEqual(cmd.value, "node .planning/scripts/cross-ai.mjs")

        backups = config_backup.list_backups(config_path)
        self.assertEqual(len(backups), 1)
        self.assertIsNone(config_backup.read_marker(config_path))
        snap_path = config_path + config_backup.SNAPSHOT_SUFFIX
        self.assertFalse(os.path.isfile(snap_path))

        self.assertEqual(_sha256(_REPO_CONFIG), before_cfg)
        self.assertEqual(_sha256(_REPO_RUNNER), before_runner)


if __name__ == "__main__":
    unittest.main()
