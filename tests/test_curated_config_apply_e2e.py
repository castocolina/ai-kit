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
import stat
import subprocess
import sys
import tempfile
import unittest
from datetime import UTC, datetime

sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "skills", "ai-kit-gsd-curated-config"),
)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills", "ai-kit-spec-review"))

from ai_kit_gsd_curated_config import apply as apply_mod
from ai_kit_gsd_curated_config import (
    cli,
    config_backup,
    cross_ai_script,
    gsd_catalog,
    plan_io,
    presets,
)
from ai_kit_spec import gsd_tools

from tests.test_curated_config_apply import (
    FakeRun,
    _decide_all_choices,
    _fixed_now,
    _scratch_env,
    scratch_inventory,
)
from tests.test_curated_config_e2e import REPO_ROOT, _real_node_executable, _RealGsdTestCase
from tests.test_curated_config_golden import load_fixture, tables_answer
from tests.test_curated_config_inventory import seed_cache
from tests.test_curated_config_plan_edit import _run_plan_set
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


def _strict_encode():
    mod = gsd_catalog.load_ai_kit_spec_module("gsd_tools")
    assert mod is not None
    return mod.encode_value_strict


def _config_set_keys(log: list[list[str]]) -> list[str]:
    keys: list[str] = []
    for row in log:
        if len(row) >= 5 and row[2] == "query" and row[3] == "config-set":
            keys.append(row[4])
    return keys


class _ConfigSetWrapper:
    def __init__(self, inner, *, fail_nth: int | None = None):
        self.argv_log: list[list[str]] = []
        self._inner = inner
        self._fail_nth = fail_nth
        self._set_calls = 0

    def __call__(self, cmd, **kw):
        row = [str(part) for part in cmd]
        self.argv_log.append(row)
        if (
            self._fail_nth is not None
            and len(row) >= 5
            and row[2] == "query"
            and row[3] == "config-set"
        ):
            self._set_calls += 1
            if self._set_calls == self._fail_nth:
                return subprocess.CompletedProcess(cmd, 1, "", "injected fail")
        return self._inner(cmd, **kw)


def _direct_apply(
    plan_path: str,
    inv_path: str,
    project: str,
    resolve_env: dict,
    node_bin: str,
    run_fn,
    *,
    now_fn=None,
) -> tuple[int, dict]:
    plan, _err = plan_io.load_plan(plan_path)
    inv, _inv_err = plan_io.load_inventory(inv_path)
    assert plan is not None and inv is not None
    inputs = apply_mod.Inputs(plan, plan_path, inv, inv_path, project)
    deps = apply_mod.ApplyDeps(
        lambda name: node_bin if name == "node" else None,
        run_fn,
        lambda: dict(resolve_env),
        now_fn=now_fn or (lambda: datetime.now(UTC)),
    )
    return apply_mod.run_apply(inputs, deps, _strict_encode())


def _gsd16_or_skip(test_case: unittest.TestCase) -> str:
    node_bin = _real_node_executable()
    tools = REPO_ROOT / ".claude" / "gsd-core" / "bin" / "gsd-tools.cjs"
    if node_bin is None or not tools.is_file():
        test_case.skipTest("no node or checkout-local gsd-tools.cjs")
    version = gsd_tools.gsd_core_version(str(tools))
    if not version or not version.startswith("1.16."):
        test_case.skipTest(f"checkout-local gsd-core is {version}; need 1.16.x")
    return node_bin


def _golden_bundle(
    scratch: str,
    *,
    with_planning: bool = True,
    host_name: str = "claude",
) -> dict:
    project = os.path.join(scratch, "project")
    home = os.path.join(scratch, "home")
    gsd_home = os.path.join(scratch, "gsd_home")
    xdg = os.path.join(scratch, "xdg")
    os.makedirs(project)
    _seed_home(home)
    config_path = os.path.join(project, ".planning", "config.json")
    if with_planning:
        os.makedirs(os.path.join(project, ".planning"), exist_ok=True)
        with open(config_path, "w", encoding="utf-8") as handle:
            handle.write('{\n    "model_profile": "balanced"\n}\n')
    with open(os.path.join(project, "AGENTS.md"), "w", encoding="utf-8") as handle:
        handle.write("# agents\n")
    with open(os.path.join(project, "package.json"), "w", encoding="utf-8") as handle:
        json.dump({"dependencies": {"react": "19.0.0"}}, handle)
    seed_cache(xdg, load_fixture("runtimes.json"), load_fixture("model-catalog.json"))
    env = _scratch_env(home, gsd_home, xdg)
    resolve_env = {**env, "RUNTIME_DIR": str(REPO_ROOT)}
    child_env = dict(env)
    fake = _tables_fake(config_path, home)
    inv_path = os.path.join(scratch, "inv.json")
    inv = scratch_inventory(project, resolve_env, fake, inv_path, host_name=host_name)
    inv["existing_config"]["path"] = config_path
    with open(inv_path, "w", encoding="utf-8") as handle:
        handle.write(plan_io.canonical_json(inv))
    plan_path = os.path.join(scratch, "plan.json")
    code, _plan, raw, err = run_recommend(inv, "--profile", "adaptive", "--rigor", "standard")
    if code != 0 or raw is None:
        raise AssertionError(err)
    with open(plan_path, "wb") as handle:
        handle.write(raw)
    _decide_all_choices(plan_path, inv_path)
    return {
        "project": project,
        "resolve_env": resolve_env,
        "child_env": child_env,
        "config_path": config_path,
        "inv_path": inv_path,
        "plan_path": plan_path,
    }


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

    def test_nth_key_failure_restores_bytes(self) -> None:
        node_bin = _gsd16_or_skip(self)
        scratch = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, scratch, ignore_errors=True)
        bundle = _golden_bundle(scratch)
        config_path = bundle["config_path"]
        with open(config_path, "rb") as handle:
            before_bytes = handle.read()
        real = _real_run(bundle["child_env"])
        wrapper = _ConfigSetWrapper(real, fail_nth=3)
        code, report = _direct_apply(
            bundle["plan_path"],
            bundle["inv_path"],
            bundle["project"],
            bundle["resolve_env"],
            node_bin,
            wrapper,
        )
        self.assertEqual(code, 1)
        keys = _config_set_keys(wrapper.argv_log)
        self.assertGreaterEqual(len(keys), 3)
        self.assertEqual(report["failed_key"], keys[2])
        with open(config_path, "rb") as handle:
            self.assertEqual(handle.read(), before_bytes)
        self.assertIsNone(config_backup.read_marker(config_path))
        self.assertGreaterEqual(len(config_backup.list_backups(config_path)), 1)

    def test_nth_key_failure_absent_config(self) -> None:
        node_bin = _gsd16_or_skip(self)
        scratch = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, scratch, ignore_errors=True)
        bundle = _golden_bundle(scratch, with_planning=False)
        planning = os.path.join(bundle["project"], ".planning")
        self.assertFalse(os.path.exists(planning))
        real = _real_run(bundle["child_env"])
        wrapper = _ConfigSetWrapper(real, fail_nth=2)
        code, _report = _direct_apply(
            bundle["plan_path"],
            bundle["inv_path"],
            bundle["project"],
            bundle["resolve_env"],
            node_bin,
            wrapper,
        )
        self.assertEqual(code, 1)
        self.assertFalse(os.path.exists(planning))

    def test_failed_reapply_restores_runner(self) -> None:
        node_bin = _gsd16_or_skip(self)
        scratch = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, scratch, ignore_errors=True)
        bundle = _golden_bundle(scratch)
        config_path = bundle["config_path"]
        project = bundle["project"]
        real = _real_run(bundle["child_env"])
        code, report = _direct_apply(
            bundle["plan_path"],
            bundle["inv_path"],
            project,
            bundle["resolve_env"],
            node_bin,
            real,
        )
        self.assertEqual((code, report["applied"]), (0, True))
        runner = os.path.join(project, ".planning", "scripts", "cross-ai.mjs")
        with open(runner, "rb") as handle:
            runner_bytes = handle.read()
        runner_mode = stat.S_IMODE(os.stat(runner).st_mode)
        with open(config_path, "rb") as handle:
            config_bytes = handle.read()
        code_set, _, err_set = _run_plan_set(
            bundle["plan_path"], bundle["inv_path"], "workflow.cross_ai_timeout", "2400"
        )
        self.assertEqual((code_set, err_set), (0, ""))
        wrapper = _ConfigSetWrapper(real, fail_nth=1)
        code2, report2 = _direct_apply(
            bundle["plan_path"],
            bundle["inv_path"],
            project,
            bundle["resolve_env"],
            node_bin,
            wrapper,
        )
        self.assertEqual(code2, 1)
        self.assertEqual(report2["failed_key"], "workflow.cross_ai_timeout")
        with open(runner, "rb") as handle:
            self.assertEqual(handle.read(), runner_bytes)
        self.assertEqual(stat.S_IMODE(os.stat(runner).st_mode), runner_mode)
        with open(config_path, "rb") as handle:
            self.assertEqual(handle.read(), config_bytes)
        self.assertIsNone(config_backup.read_marker(config_path))
        snap = runner + config_backup.SNAPSHOT_SUFFIX
        self.assertFalse(os.path.isfile(snap))


    def test_fourth_apply_prunes(self) -> None:
        node_bin = _gsd16_or_skip(self)
        tools = str(REPO_ROOT / ".claude" / "gsd-core" / "bin" / "gsd-tools.cjs")
        scratch = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, scratch, ignore_errors=True)
        bundle = _golden_bundle(scratch)
        config_path = bundle["config_path"]
        planning = os.path.dirname(config_path)
        manual = os.path.join(planning, "config.json.bak-manual")
        with open(manual, "wb") as handle:
            handle.write(b"manual\n")
        real = _real_run(bundle["child_env"])
        gt = gsd_tools.GsdTools(node_bin, tools)

        def run(cmd, **kw):
            call_env = kw.pop("env", None) or {}
            return subprocess.run(cmd, env={**bundle["child_env"], **call_env}, **kw)

        for index in range(4):
            code, report = _direct_apply(
                bundle["plan_path"],
                bundle["inv_path"],
                bundle["project"],
                bundle["resolve_env"],
                node_bin,
                real,
                now_fn=_fixed_now,
            )
            self.assertEqual((code, report["applied"]), (0, True))
            if index < 3:
                gsd_tools.config_set_strict(
                    gsd_tools.ConfigCall(gt, bundle["project"], run, bundle["child_env"]),
                    "model_profile",
                    f"balanced-{index}",
                )
        rows = config_backup.list_backups(config_path)
        self.assertEqual(len(rows), 3)
        self.assertTrue(os.path.isfile(manual))

    def test_reapply_is_noop(self) -> None:
        node_bin = _gsd16_or_skip(self)
        scratch = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, scratch, ignore_errors=True)
        bundle = _golden_bundle(scratch)
        config_path = bundle["config_path"]
        real = _real_run(bundle["child_env"])
        code1, _report1 = _direct_apply(
            bundle["plan_path"],
            bundle["inv_path"],
            bundle["project"],
            bundle["resolve_env"],
            node_bin,
            real,
        )
        self.assertEqual(code1, 0)
        with open(config_path, "rb") as handle:
            s1 = handle.read()
        rows1 = config_backup.list_backups(config_path)
        backups_after_1 = [os.path.basename(p) for p, _s, _n in rows1]
        wrapper2 = _ConfigSetWrapper(real)
        code2, report2 = _direct_apply(
            bundle["plan_path"],
            bundle["inv_path"],
            bundle["project"],
            bundle["resolve_env"],
            node_bin,
            wrapper2,
        )
        self.assertEqual(code2, 0)
        self.assertEqual(_config_set_keys(wrapper2.argv_log), [])
        with open(config_path, "rb") as handle:
            self.assertEqual(handle.read(), s1)
        self.assertFalse(report2["backup"]["reused"])
        rows2 = config_backup.list_backups(config_path)
        backups_after_2 = [os.path.basename(p) for p, _s, _n in rows2]
        self.assertEqual(len(backups_after_2), len(backups_after_1) + 1)
        wrapper3 = _ConfigSetWrapper(real)
        code3, report3 = _direct_apply(
            bundle["plan_path"],
            bundle["inv_path"],
            bundle["project"],
            bundle["resolve_env"],
            node_bin,
            wrapper3,
        )
        self.assertEqual(code3, 0)
        self.assertTrue(report3["backup"]["reused"])
        rows3 = config_backup.list_backups(config_path)
        backups_after_3 = [os.path.basename(p) for p, _s, _n in rows3]
        self.assertEqual(backups_after_3, backups_after_2)

    def test_absent_config_reconciles(self) -> None:
        node_bin = _gsd16_or_skip(self)
        scratch = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, scratch, ignore_errors=True)
        bundle = _golden_bundle(scratch, with_planning=False)
        gsd_dir = os.path.join(bundle["child_env"]["GSD_HOME"], ".gsd")
        os.makedirs(gsd_dir, exist_ok=True)
        defaults = {
            "resolve_model_ids": "omit",
            "model_policy": {"provider": "cursor", "budget": "low"},
            "custom_unrelated": "keepme",
        }
        with open(os.path.join(gsd_dir, "defaults.json"), "w", encoding="utf-8") as handle:
            json.dump(defaults, handle)
        real = _real_run(bundle["child_env"])
        code, report = _direct_apply(
            bundle["plan_path"],
            bundle["inv_path"],
            bundle["project"],
            bundle["resolve_env"],
            node_bin,
            real,
        )
        self.assertEqual((code, report["applied"]), (0, True))
        self.assertTrue(report["created_config"])
        live, warn = plan_io.read_json_object(bundle["config_path"])
        assert live is not None and warn is None
        self.assertNotIn("resolve_model_ids", live)
        flat = presets.flatten_config(live)
        self.assertFalse(any(key.startswith("model_policy.") for key in flat))
        self.assertEqual(live.get("custom_unrelated"), "keepme")
        reconciled = report["reconciled"]
        self.assertIn("resolve_model_ids", reconciled)
        self.assertTrue(any(k.startswith("model_policy.") for k in reconciled))


if __name__ == "__main__":
    unittest.main()
