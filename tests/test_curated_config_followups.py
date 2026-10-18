"""Follow-up block and approval gate tests (plan 18-20)."""
from __future__ import annotations

import contextlib
import io
import json
import os
import shlex
import subprocess
import sys
import tempfile
import unittest
from datetime import UTC, datetime
from unittest import mock

sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "skills", "ai-kit-gsd-curated-config"),
)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills", "ai-kit-spec-review"))

from ai_kit_gsd_curated_config import cli, followups, plan_io

from tests.test_curated_config_apply import (
    _decide_all_choices,
    _minimal_plan,
    _RecordingRun,
    _scratch_env,
    _setup_scratch_project,
    _tables_fake,
    _write_apply,
    scratch_inventory,
)
from tests.test_curated_config_golden import tables_answer
from tests.test_curated_config_inventory import FakeRun, make_gsd_install, seed_cache
from tests.test_curated_config_recommend import make_inventory, run_recommend


def _effort_stdout(cmd):
    if len(cmd) >= 5 and cmd[2] == "effort" and cmd[3] == "sync":
        if cmd[4] == "--dry-run":
            return json.dumps({"changes": [{}, {}]})
        return json.dumps({"synced": 0, "changes": []})
    return None


def _tables_followups(config_path: str, home: str, **kwargs) -> FollowupsRun:
    return FollowupsRun(
        node_stdout=lambda argv, h=home: json.dumps(
            tables_answer(json.loads(argv[6]), h)
        ),
        config_path_stdout=config_path,
        **kwargs,
    )


class FollowupsRun(FakeRun):
    """FakeRun that answers effort sync and npx; records all argv."""

    def __init__(self, *args, npx_rc=0, **kwargs):
        super().__init__(*args, **kwargs)
        self.npx_rc = npx_rc
        self.npx_log: list[list] = []

    def __call__(self, cmd, **kw):
        if cmd and cmd[0] == "npx":
            self.npx_log.append(list(cmd))
            self.kw_log.append(dict(kw))
            return subprocess.CompletedProcess(cmd, self.npx_rc, "", "")
        if cmd and cmd[0] == "node" and len(cmd) >= 5 and cmd[2] == "effort":
            out = _effort_stdout(cmd)
            if out is not None:
                self.argv_log.append(list(cmd))
                self.kw_log.append(dict(kw))
                return subprocess.CompletedProcess(cmd, 0, out, "")
        return super().__call__(cmd, **kw)


def _run_followups_cli(argv, env, fake):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = cli.main(
            argv,
            which_fn=lambda name, **_kw: "node" if name == "node" else None,
            env_fn=lambda: dict(env),
            run_fn=fake,
        )
    raw = out.getvalue().strip()
    parsed = json.loads(raw) if raw else None
    return code, parsed, err.getvalue()


def _setup_opencode_global(tmp: str) -> tuple[str, dict, str, FollowupsRun]:
    project = os.path.join(tmp, "project")
    home = os.path.join(tmp, "home")
    gsd_home = os.path.join(tmp, "gsd_home")
    xdg = os.path.join(tmp, "xdg")
    os.makedirs(project)
    os.makedirs(os.path.join(project, ".planning"))
    config_path = os.path.join(project, ".planning", "config.json")
    with open(config_path, "w", encoding="utf-8") as handle:
        json.dump({"model_profile": "quality"}, handle)
    opencode_cfg = os.path.join(home, ".config", "opencode")
    make_gsd_install(os.path.join(opencode_cfg, "gsd-core"), version="1.16.0")
    seed_cache(xdg, {"clis": {}}, {"_meta": {"schema_version": 1}})
    env = _scratch_env(home, gsd_home, xdg)
    fake = _tables_followups(config_path, home)
    return project, env, config_path, fake


def _opencode_plan_inv(tmp, project, env, fake, config_path):
    inv_path = os.path.join(tmp, "inventory.json")
    inv = scratch_inventory(project, env, fake, inv_path, host_name="opencode")
    inv["gsd_core"]["version"] = "1.16.0"
    with open(inv_path, "w", encoding="utf-8") as handle:
        handle.write(plan_io.canonical_json(inv))
    plan = _minimal_plan(
        "opencode",
        inv,
        [
            {
                "key": "model_profile",
                "op": "set",
                "value": "adaptive",
                "existing": "quality",
                "source": "preset",
            },
        ],
    )
    plan_path = os.path.join(tmp, "plan.json")
    plan_io.write_plan(plan_path, plan)
    return inv_path, plan_path, inv


class TestFollowupsTracer(unittest.TestCase):
    def test_apply_lists_installer_without_running_it(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project, env, config_path, fake = _setup_opencode_global(tmp)
            inv_path, plan_path, _inv = _opencode_plan_inv(
                tmp, project, env, fake, config_path
            )
            rec = _RecordingRun(fake, config_path=config_path)
            code, report = _write_apply(plan_path, inv_path, project, env, rec)
            self.assertEqual(code, 0)
            req = report["followups"]["required"]
            self.assertEqual(len(req), 1)
            self.assertEqual(
                req[0]["argv"],
                [
                    "npx",
                    "-y",
                    "--registry=https://registry.npmjs.org/",
                    "--@opengsd:registry=https://registry.npmjs.org/",
                    "@opengsd/gsd-core@1.16.0",
                    "--opencode",
                    "--local",
                ],
            )
            self.assertEqual(req[0]["cwd"], project)
            self.assertTrue(any("gitignore by prefix" in n for n in report["followups"]["notes"]))
            npx_calls = [c for c in rec.argv_log if c and c[0] == "npx"]
            self.assertEqual(npx_calls, [])

    def test_followups_approve_runs_installer_once(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project, env, config_path, fake = _setup_opencode_global(tmp)
            inv_path, plan_path, _inv = _opencode_plan_inv(
                tmp, project, env, fake, config_path
            )
            argv = [
                "followups",
                "--plan",
                plan_path,
                "--inventory",
                inv_path,
                "--project-dir",
                project,
                "--approve",
                "--require",
                "installer",
            ]
            code, parsed, _err = _run_followups_cli(argv, env, fake)
            self.assertEqual(code, 0)
            assert parsed is not None
            self.assertEqual(parsed["results"][0]["id"], "installer")
            self.assertEqual(parsed["results"][0]["returncode"], 0)
            self.assertEqual(len(fake.npx_log), 1)
            self.assertEqual(fake.npx_log[0][-2:], ["--opencode", "--local"])
            self.assertEqual(fake.kw_log[-1].get("cwd"), project)

    def test_approve_refused_while_apply_marker_held(self) -> None:
        """B WR-08: no installer or effort sync over a running or failed apply."""
        from ai_kit_gsd_curated_config import config_backup

        with tempfile.TemporaryDirectory() as tmp:
            project, env, config_path, fake = _setup_opencode_global(tmp)
            inv_path, plan_path, _inv = _opencode_plan_inv(
                tmp, project, env, fake, config_path
            )
            config_backup.acquire_marker(config_path, True, lambda: datetime.now(UTC))
            base = ["followups", "--plan", plan_path, "--inventory", inv_path,
                    "--project-dir", project]
            code, parsed, err = _run_followups_cli(
                [*base, "--approve", "--require", "installer"], env, fake
            )
            self.assertEqual(code, 2)
            self.assertIsNone(parsed)
            self.assertIn("an apply is running or did not finish", err)
            self.assertEqual(fake.npx_log, [])
            code, parsed, _err = _run_followups_cli(base, env, fake)
            self.assertEqual(code, 0)
            assert parsed is not None
            self.assertIn("required", parsed)


def _inv_deps(env, fake):
    from ai_kit_gsd_curated_config import host

    return host.InventoryDeps(
        lambda n: "node" if n == "node" else None,
        fake,
        lambda: dict(env),
    )


def _build_block(plan, inv, plan_path, inv_path, project, env, fake, force=()):
    ctx = followups.FollowupCtx(plan_path, inv_path, project, _inv_deps(env, fake))
    return followups.build_followups(plan, inv, ctx, force_ids=force)


class TestEffortSync(unittest.TestCase):
    def test_claude_effort_sync_with_dry_run_count(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project, env, config_path = _setup_scratch_project(tmp)
            fake = _tables_followups(config_path, env["HOME"])
            inv_path = os.path.join(tmp, "inventory.json")
            inv = scratch_inventory(project, env, fake, inv_path, host_name="claude")
            plan = _minimal_plan(
                "claude",
                inv,
                [
                    {
                        "key": "effort.agent_overrides.gsd-executor",
                        "op": "set",
                        "value": "high",
                        "existing": "medium",
                        "source": "preset",
                    },
                ],
            )
            plan_path = os.path.join(tmp, "plan.json")
            plan_io.write_plan(plan_path, plan)
            block = _build_block(plan, inv, plan_path, inv_path, project, env, fake)
            self.assertEqual(len(block["required"]), 1)
            row = block["required"][0]
            self.assertEqual(row["id"], "effort_sync")
            tools = os.path.join(project, ".claude", "gsd-core", "bin", "gsd-tools.cjs")
            self.assertEqual(
                row["argv"][:3],
                ["node", tools, "effort"],
            )
            self.assertIn("2 change", row["detail"])
            self.assertTrue(any("config-dir" in n for n in block["notes"]))

    def test_workstream_path_skips_effort(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project, env, _config_path = _setup_scratch_project(tmp)
            ws_cfg = os.path.join(project, ".planning", "workstreams", "ws", "config.json")
            os.makedirs(os.path.dirname(ws_cfg), exist_ok=True)
            fake = _tables_followups(ws_cfg, env["HOME"])
            inv_path = os.path.join(tmp, "inventory.json")
            inv = scratch_inventory(project, env, fake, inv_path, host_name="claude")
            inv["existing_config"] = {"path": ws_cfg, "exists": True, "values": {}}
            with open(inv_path, "w", encoding="utf-8") as handle:
                handle.write(plan_io.canonical_json(inv))
            plan = _minimal_plan(
                "claude",
                inv,
                [
                    {
                        "key": "effort.agent_overrides.gsd-executor",
                        "op": "set",
                        "value": "high",
                        "existing": "medium",
                        "source": "preset",
                    },
                ],
            )
            plan_path = os.path.join(tmp, "plan.json")
            plan_io.write_plan(plan_path, plan)
            block = _build_block(plan, inv, plan_path, inv_path, project, env, fake)
            self.assertEqual(block["required"], [])
            self.assertTrue(
                any("workstream config" in n and ws_cfg in n for n in block["notes"])
            )
            effort_calls = [c for c in fake.argv_log if len(c) > 3 and c[2] == "effort"]
            self.assertEqual(effort_calls, [])

    def test_gsd_workstream_env_skips_effort(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project, env, config_path = _setup_scratch_project(tmp)
            env = dict(env)
            env["GSD_WORKSTREAM"] = "ws"
            fake = _tables_followups(config_path, env["HOME"])
            inv_path = os.path.join(tmp, "inventory.json")
            inv = scratch_inventory(project, env, fake, inv_path, host_name="claude")
            plan = _minimal_plan(
                "claude",
                inv,
                [
                    {
                        "key": "effort.agent_overrides.gsd-executor",
                        "op": "set",
                        "value": "high",
                        "existing": "medium",
                        "source": "preset",
                    },
                ],
            )
            plan_path = os.path.join(tmp, "plan.json")
            plan_io.write_plan(plan_path, plan)
            block = _build_block(plan, inv, plan_path, inv_path, project, env, fake)
            self.assertEqual(block["required"], [])
            self.assertTrue(any("ws" in n for n in block["notes"]))

    def test_pi_cursor_skip_effort(self) -> None:
        for host_name in ("pi", "cursor"):
            with self.subTest(host=host_name), tempfile.TemporaryDirectory() as tmp:
                project, env, config_path = _setup_scratch_project(tmp)
                fake = _tables_followups(config_path, env["HOME"])
                inv_path = os.path.join(tmp, "inventory.json")
                inv = scratch_inventory(
                    project, env, fake, inv_path, host_name=host_name
                )
                plan = _minimal_plan(
                    host_name,
                    inv,
                    [
                        {
                            "key": "effort.agent_overrides.gsd-executor",
                            "op": "set",
                            "value": "high",
                            "existing": "medium",
                            "source": "preset",
                        },
                    ],
                )
                plan_path = os.path.join(tmp, "plan.json")
                plan_io.write_plan(plan_path, plan)
                block = _build_block(
                    plan, inv, plan_path, inv_path, project, env, fake
                )
                self.assertEqual(block["required"], [])
                self.assertTrue(
                    any(host_name in n and "frontmatter" in n for n in block["notes"])
                )

    def test_no_local_claude_skips_effort(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = os.path.join(tmp, "project")
            home = os.path.join(tmp, "home")
            xdg = os.path.join(tmp, "xdg")
            os.makedirs(os.path.join(project, ".planning"))
            config_path = os.path.join(project, ".planning", "config.json")
            with open(config_path, "w", encoding="utf-8") as handle:
                json.dump({}, handle)
            make_gsd_install(os.path.join(home, ".claude", "gsd-core"))
            seed_cache(xdg, {"clis": {}}, {"_meta": {"schema_version": 1}})
            env = _scratch_env(home, home, xdg)
            fake = _tables_followups(config_path, env["HOME"])
            inv_path = os.path.join(tmp, "inventory.json")
            inv = scratch_inventory(project, env, fake, inv_path, host_name="claude")
            plan = _minimal_plan(
                "claude",
                inv,
                [
                    {
                        "key": "effort.agent_overrides.gsd-executor",
                        "op": "set",
                        "value": "high",
                        "existing": "medium",
                        "source": "preset",
                    },
                ],
            )
            plan_path = os.path.join(tmp, "plan.json")
            plan_io.write_plan(plan_path, plan)
            block = _build_block(plan, inv, plan_path, inv_path, project, env, fake)
            self.assertEqual(block["required"], [])
            self.assertTrue(any("no project-local gsd-core" in n for n in block["notes"]))


class TestFollowupOrdering(unittest.TestCase):
    def test_installer_before_effort_and_reresolve(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project, env, config_path, fake = _setup_opencode_global(tmp)
            inv_path, plan_path, inv = _opencode_plan_inv(
                tmp, project, env, fake, config_path
            )
            plan, _ = plan_io.load_plan(plan_path)
            assert plan is not None
            plan["entries"].append(
                {
                    "key": "effort.agent_overrides.gsd-executor",
                    "op": "set",
                    "value": "high",
                    "existing": "medium",
                    "source": "preset",
                }
            )
            plan_io.write_plan(plan_path, plan)
            block = _build_block(plan, inv, plan_path, inv_path, project, env, fake)
            self.assertEqual([r["id"] for r in block["required"]], ["installer", "effort_sync"])
            self.assertIn("until the local install exists", block["required"][1]["detail"])

            base = _tables_followups(config_path, env["HOME"])

            class NpxInstallRun(FollowupsRun):
                def __call__(self, cmd, **kw):
                    if cmd and cmd[0] == "npx":
                        make_gsd_install(os.path.join(project, ".opencode", "gsd-core"))
                        return subprocess.CompletedProcess(cmd, 0, "", "")
                    return super().__call__(cmd, **kw)

            fake_with_npx = NpxInstallRun(
                node_stdout=base.node_stdout,
                config_path_stdout=config_path,
            )
            with mock.patch(
                "ai_kit_gsd_curated_config.followups.local_gsd_tools",
                wraps=followups.local_gsd_tools,
            ) as wrapped:
                ctx = followups.FollowupCtx(
                    plan_path, inv_path, project, _inv_deps(env, fake_with_npx)
                )
                code, results = followups.run_followups(block, "opencode", ctx)
            self.assertEqual(code, 0)
            self.assertEqual(len(results), 2)
            self.assertGreater(wrapped.call_count, 0)
            tools_path = os.path.join(project, ".opencode", "gsd-core", "bin", "gsd-tools.cjs")
            self.assertEqual(results[1]["argv"][1], tools_path)


class TestDisclosures(unittest.TestCase):
    def test_changed_keys_pure(self) -> None:
        plan = {
            "entries": [
                {"key": "a", "op": "set", "value": 1, "existing": 2},
                {"key": "b", "op": "unset", "existing": "x"},
                {"key": "c", "op": "keep", "existing": 1},
                {"key": "d", "op": "set", "value": 1, "existing": 1},
            ]
        }
        self.assertEqual(followups.changed_keys(plan), ["a", "b"])

    def test_disclosures_and_map_codebase(self) -> None:
        inv = make_inventory(host="opencode", project={"intel_index_present": False})
        plan = _minimal_plan(
            "opencode",
            inv,
            [{"key": "intel.enabled", "op": "set", "value": True, "source": "preset"}],
        )
        plan_path = "/tmp/plan.json"
        inv_path = "/tmp/inv.json"
        fake = FollowupsRun()
        block = _build_block(plan, inv, plan_path, inv_path, "/tmp/p", {"HOME": "/tmp"}, fake)
        text = json.dumps(block)
        self.assertIn("downloads and runs", text)
        self.assertIn("pnpm dlx", text)
        self.assertIn("defaults.json", text)
        self.assertIn("no-legacy-cleanup", text)
        self.assertIn(".npmrc", text)  # U-2
        rec = block["recommended"]
        self.assertTrue(rec and rec[0]["id"] == "map_codebase")
        if block["required"]:
            joined = " ".join(block["required"][0]["argv"])
            self.assertNotIn("--no-legacy-cleanup", joined)

    def test_codex_workstream_still_offers_installer(self) -> None:
        inv = make_inventory(host="codex")
        ws = os.path.join("/proj", ".planning", "workstreams", "ws", "config.json")
        inv["existing_config"] = {"path": ws, "exists": True, "values": {}}
        plan = _minimal_plan(
            "codex",
            inv,
            [
                {
                    "key": "model_overrides.gsd-executor",
                    "op": "set",
                    "value": "opus",
                    "existing": "gpt",
                    "source": "preset",
                },
            ],
        )
        block = _build_block(
            plan,
            inv,
            "/p",
            "/i",
            "/proj",
            {"HOME": "/h"},
            FollowupsRun(),
        )
        self.assertEqual(block["required"][0]["id"], "installer")

    def test_gitignore_prefix_note_is_only_for_non_claude_hosts(self):
        for host_name, expected_dir in (("opencode", ".opencode"), ("codex", ".codex")):
            note = followups._gitignore_prefix_note(host_name)
            self.assertIsNotNone(note)
            self.assertIn(f"{expected_dir}/agents/gsd-*", note or "")
            self.assertIn(f"{expected_dir}/commands/gsd-*", note or "")
            self.assertIn("never edits .gitignore", note or "")
        self.assertIsNone(followups._gitignore_prefix_note("claude"))

    def test_phase_20_evidence_notes_are_explicitly_verified(self):
        root = followups._opencode_root_note("/project")
        self.assertIn("verified by the Phase 20 opencode smoke", root)
        self.assertNotIn("inferred (unverified until Phase 20)", root)
        installer = followups._codex_installer_note()
        self.assertIn("local layout and the --codex --local flags were verified", installer)
        self.assertIn("shipped npx launcher and its registry fetch were not exercised", installer)

    def test_codex_installer_only_on_model_overrides(self) -> None:
        inv = make_inventory(host="codex")
        plan = _minimal_plan(
            "codex",
            inv,
            [
                {
                    "key": "model_overrides.gsd-executor",
                    "op": "set",
                    "value": "opus",
                    "existing": "gpt",
                    "source": "preset",
                },
            ],
        )
        block = _build_block(
            plan, inv, "/p", "/i", "/proj", {"HOME": "/h"}, FollowupsRun()
        )
        self.assertEqual(block["required"][0]["id"], "installer")
        plan2 = _minimal_plan("codex", inv, [])
        block2 = _build_block(
            plan2, inv, "/p", "/i", "/proj", {"HOME": "/h"}, FollowupsRun()
        )
        self.assertEqual(block2["required"], [])

    def test_unknown_version_no_installer(self) -> None:
        inv = make_inventory(host="opencode")
        inv["gsd_core"]["version"] = None
        plan = _minimal_plan("opencode", inv, [])
        block = _build_block(
            plan, inv, "/p", "/i", "/proj", {"HOME": "/h"}, FollowupsRun(), force=("installer",)
        )
        self.assertEqual(block["required"], [])
        self.assertTrue(any("pin a version" in n for n in block["notes"]))

    def test_non_release_version_never_reaches_npx(self) -> None:
        """B WR-07: a dist-tag or package spec in VERSION is not a pinned version."""
        for version in ("latest", "next", "file:../x", "git+https://h/x", "1.16", "1.16.0 x"):
            with self.subTest(version=version):
                inv = make_inventory(host="opencode")
                inv["gsd_core"]["version"] = version
                plan = _minimal_plan("opencode", inv, [])
                block = _build_block(
                    plan, inv, "/p", "/i", "/proj", {"HOME": "/h"}, FollowupsRun(),
                    force=("installer",),
                )
                self.assertEqual(block["required"], [])
                self.assertTrue(any("pin a version" in n for n in block["notes"]))
        inv = make_inventory(host="opencode")
        inv["gsd_core"]["version"] = "1.17.0-rc.1"
        block = _build_block(
            _minimal_plan("opencode", inv, []), inv, "/p", "/i", "/proj", {"HOME": "/h"},
            FollowupsRun(), force=("installer",),
        )
        self.assertIn("@opengsd/gsd-core@1.17.0-rc.1", block["required"][0]["argv"])

    def test_installer_failure_stderr(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project, env, config_path, fake = _setup_opencode_global(tmp)
            inv_path, plan_path, inv = _opencode_plan_inv(
                tmp, project, env, fake, config_path
            )
            plan, _ = plan_io.load_plan(plan_path)
            assert plan is not None
            block = _build_block(plan, inv, plan_path, inv_path, project, env, fake)
            fake_fail = _tables_followups(config_path, env["HOME"], npx_rc=1)
            ctx = followups.FollowupCtx(
                plan_path, inv_path, project, _inv_deps(env, fake_fail)
            )
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                code, _results = followups.run_followups(block, "opencode", ctx)
            self.assertEqual(code, 1)
            self.assertIn("run it yourself:", err.getvalue())
            self.assertIn("--opencode", err.getvalue())
            self.assertIn(f"(cwd {project})", err.getvalue())


class TestFollowupsApprovalGate(unittest.TestCase):
    def test_nothing_runs_without_approve(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project, env, config_path = _setup_scratch_project(tmp)
            fake = _tables_followups(config_path, env["HOME"])
            inv_path = os.path.join(tmp, "inventory.json")
            inv = scratch_inventory(project, env, fake, inv_path, host_name="claude")
            plan = _minimal_plan(
                "claude",
                inv,
                [
                    {
                        "key": "effort.agent_overrides.gsd-executor",
                        "op": "set",
                        "value": "high",
                        "existing": "medium",
                        "source": "preset",
                    },
                ],
            )
            plan_path = os.path.join(tmp, "plan.json")
            plan_io.write_plan(plan_path, plan)
            rec = _RecordingRun(fake, config_path=config_path)
            _write_apply(plan_path, inv_path, project, env, rec)
            npx = [c for c in rec.argv_log if c and c[0] == "npx"]
            apply_effort = [
                c for c in rec.argv_log if len(c) > 4 and c[2] == "effort" and c[4] == "--apply"
            ]
            self.assertEqual(npx, [])
            self.assertEqual(apply_effort, [])
            fake.argv_log.clear()
            code, parsed, _ = _run_followups_cli(
                [
                    "followups",
                    "--plan",
                    plan_path,
                    "--inventory",
                    inv_path,
                    "--project-dir",
                    project,
                ],
                env,
                fake,
            )
            self.assertEqual(code, 0)
            assert parsed is not None
            npx2 = [c for c in fake.argv_log if c and c[0] == "npx"]
            apply2 = [
                c for c in fake.argv_log if len(c) > 4 and c[2] == "effort" and c[4] == "--apply"
            ]
            self.assertEqual(npx2, [])
            self.assertEqual(apply2, [])

    def test_empty_block_approve(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project, env, config_path = _setup_scratch_project(tmp)
            fake = _tables_followups(config_path, env["HOME"])
            inv_path = os.path.join(tmp, "inventory.json")
            inv = scratch_inventory(project, env, fake, inv_path, host_name="claude")
            plan = _minimal_plan("claude", inv, [])
            plan_path = os.path.join(tmp, "plan.json")
            plan_io.write_plan(plan_path, plan)
            fake.argv_log.clear()
            code, parsed, _ = _run_followups_cli(
                [
                    "followups",
                    "--plan",
                    plan_path,
                    "--inventory",
                    inv_path,
                    "--project-dir",
                    project,
                    "--approve",
                ],
                env,
                fake,
            )
            self.assertEqual(code, 0)
            self.assertEqual(parsed, {"results": []})
            npx = [c for c in fake.argv_log if c and c[0] == "npx"]
            effort = [c for c in fake.argv_log if len(c) > 2 and c[2] == "effort"]
            self.assertEqual(npx, [])
            self.assertEqual(effort, [])

    def test_require_grok_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project, env, config_path = _setup_scratch_project(tmp)
            fake = _tables_followups(config_path, env["HOME"])
            inv_path = os.path.join(tmp, "inventory.json")
            inv = scratch_inventory(project, env, fake, inv_path, host_name="claude")
            plan = _minimal_plan("claude", inv, [])
            plan_path = os.path.join(tmp, "plan.json")
            plan_io.write_plan(plan_path, plan)
            code, _parsed, err = _run_followups_cli(
                [
                    "followups",
                    "--plan",
                    plan_path,
                    "--inventory",
                    inv_path,
                    "--project-dir",
                    project,
                    "--require",
                    "grok",
                ],
                env,
                fake,
            )
            self.assertEqual(code, 2)
            self.assertIn("installer", err)

    def test_require_installer_ignored_on_claude(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project, env, config_path = _setup_scratch_project(tmp)
            fake = _tables_followups(config_path, env["HOME"])
            inv_path = os.path.join(tmp, "inventory.json")
            inv = scratch_inventory(project, env, fake, inv_path, host_name="claude")
            plan = _minimal_plan("claude", inv, [])
            plan_path = os.path.join(tmp, "plan.json")
            plan_io.write_plan(plan_path, plan)
            code, parsed, _ = _run_followups_cli(
                [
                    "followups",
                    "--plan",
                    plan_path,
                    "--inventory",
                    inv_path,
                    "--project-dir",
                    project,
                    "--require",
                    "installer",
                ],
                env,
                fake,
            )
            self.assertEqual(code, 0)
            assert parsed is not None
            self.assertEqual(parsed["required"], [])

    def test_idempotent_second_approve(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project, env, config_path = _setup_scratch_project(tmp)
            fake = _tables_followups(config_path, env["HOME"])
            inv_path = os.path.join(tmp, "inventory.json")
            inv = scratch_inventory(project, env, fake, inv_path, host_name="claude")
            plan = _minimal_plan(
                "claude",
                inv,
                [
                    {
                        "key": "effort.agent_overrides.gsd-executor",
                        "op": "set",
                        "value": "high",
                        "existing": "medium",
                        "source": "preset",
                    },
                ],
            )
            plan_path = os.path.join(tmp, "plan.json")
            plan_io.write_plan(plan_path, plan)
            argv = [
                "followups",
                "--plan",
                plan_path,
                "--inventory",
                inv_path,
                "--project-dir",
                project,
                "--approve",
                "--require",
                "effort_sync",
            ]
            code1, _parsed1, _ = _run_followups_cli(argv, env, fake)
            self.assertEqual(code1, 0)
            code2, parsed2, _ = _run_followups_cli(argv, env, fake)
            self.assertEqual(code2, 0)
            assert parsed2 is not None
            self.assertEqual(parsed2["results"][0]["returncode"], 0)
            self.assertIn("changes", parsed2["results"][0]["stdout_tail"])

    def test_opencode_one_approve_runs_installer_and_effort(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project, env, config_path, fake = _setup_opencode_global(tmp)
            inv_path, plan_path, _inv = _opencode_plan_inv(
                tmp, project, env, fake, config_path
            )
            plan, _ = plan_io.load_plan(plan_path)
            assert plan is not None
            plan["entries"].append(
                {
                    "key": "effort.agent_overrides.gsd-executor",
                    "op": "set",
                    "value": "high",
                    "existing": "medium",
                    "source": "preset",
                }
            )
            plan_io.write_plan(plan_path, plan)
            argv = [
                "followups",
                "--plan",
                plan_path,
                "--inventory",
                inv_path,
                "--project-dir",
                project,
                "--approve",
                "--require",
                "installer,effort_sync",
            ]

            class NpxInstallRun(FollowupsRun):
                def __call__(self, cmd, **kw):
                    if cmd and cmd[0] == "npx":
                        make_gsd_install(os.path.join(project, ".opencode", "gsd-core"))
                        return subprocess.CompletedProcess(cmd, 0, "", "")
                    return super().__call__(cmd, **kw)

            base = _tables_followups(config_path, env["HOME"])
            runner = NpxInstallRun(
                node_stdout=base.node_stdout,
                config_path_stdout=config_path,
            )
            code, parsed, _ = _run_followups_cli(argv, env, runner)
            self.assertEqual(code, 0)
            assert parsed is not None
            self.assertEqual(len(parsed["results"]), 2)

    def test_results_follow_required_order(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project, env, config_path, fake = _setup_opencode_global(tmp)
            inv_path, plan_path, inv = _opencode_plan_inv(
                tmp, project, env, fake, config_path
            )
            plan, _ = plan_io.load_plan(plan_path)
            assert plan is not None
            plan["entries"].append(
                {
                    "key": "effort.agent_overrides.gsd-executor",
                    "op": "set",
                    "value": "high",
                    "existing": "medium",
                    "source": "preset",
                }
            )
            plan_io.write_plan(plan_path, plan)
            block = _build_block(plan, inv, plan_path, inv_path, project, env, fake)
            order: list[str] = []

            class OrderRun(FollowupsRun):
                def __call__(self, cmd, **kw):
                    if cmd and cmd[0] == "npx":
                        make_gsd_install(os.path.join(project, ".opencode", "gsd-core"))
                        order.append("installer")
                        return subprocess.CompletedProcess(cmd, 0, "", "")
                    if cmd and cmd[0] == "node" and len(cmd) > 2 and cmd[2] == "effort":
                        order.append("effort_sync")
                    return super().__call__(cmd, **kw)

            base = _tables_followups(config_path, env["HOME"])
            runner = OrderRun(
                node_stdout=base.node_stdout,
                config_path_stdout=config_path,
            )
            ctx = followups.FollowupCtx(
                plan_path, inv_path, project, _inv_deps(env, runner)
            )
            code, results = followups.run_followups(block, "opencode", ctx)
            self.assertEqual(code, 0)
            self.assertEqual(order, ["installer", "effort_sync"])
            self.assertEqual([r["id"] for r in results], ["installer", "effort_sync"])

    def test_destination_binding(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _project_a, env, inv_path, plan_path, config_a, _inv, _fake = _decided_plan_followups(
                tmp
            )
            project_b = os.path.join(tmp, "project_b")
            os.makedirs(os.path.join(project_b, ".planning"))
            config_b = os.path.join(project_b, ".planning", "config.json")
            with open(config_b, "w", encoding="utf-8") as handle:
                json.dump({}, handle)
            make_gsd_install(os.path.join(project_b, ".claude", "gsd-core"))
            fake_b = _tables_followups(config_b, env["HOME"])
            for approve in (False, True):
                fake_b.argv_log.clear()
                code, _parsed, err = _run_followups_cli(
                    [
                        "followups",
                        "--plan",
                        plan_path,
                        "--inventory",
                        inv_path,
                        "--project-dir",
                        project_b,
                        *(
                            ["--approve", "--require", "effort_sync"]
                            if approve
                            else []
                        ),
                    ],
                    env,
                    fake_b,
                )
                self.assertEqual(code, 2)
                self.assertIn(config_b, err)
                self.assertIn(config_a, err)
                npx = [c for c in fake_b.argv_log if c and c[0] == "npx"]
                effort = [c for c in fake_b.argv_log if len(c) > 2 and c[2] == "effort"]
                self.assertEqual(npx, [])
                self.assertEqual(effort, [])


    def test_apply_then_followups_same_block(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = os.path.join(tmp, "my project")
            home = os.path.join(tmp, "home")
            gsd_home = os.path.join(tmp, "gsd_home")
            xdg = os.path.join(tmp, "xdg")
            os.makedirs(project)
            os.makedirs(home, exist_ok=True)
            os.makedirs(os.path.join(project, ".planning"))
            config_path = os.path.join(project, ".planning", "config.json")
            with open(config_path, "w", encoding="utf-8") as handle:
                json.dump({"model_profile": "balanced"}, handle)
            make_gsd_install(os.path.join(project, ".claude", "gsd-core"))
            seed_cache(xdg, {"clis": {}}, {"_meta": {"schema_version": 1}})
            env = _scratch_env(home, gsd_home, xdg)
            fake = _tables_followups(config_path, env["HOME"])
            inv_path = os.path.join(tmp, "inventory.json")
            inv = scratch_inventory(project, env, fake, inv_path, host_name="claude")
            plan = _minimal_plan(
                "claude",
                inv,
                [
                    {
                        "key": "effort.agent_overrides.gsd-executor",
                        "op": "set",
                        "value": "high",
                        "existing": "medium",
                        "source": "preset",
                    },
                ],
            )
            plan_path = os.path.join(tmp, "plan.json")
            plan_io.write_plan(plan_path, plan)
            rec = _RecordingRun(fake, config_path=config_path)
            code, report = _write_apply(plan_path, inv_path, project, env, rec)
            self.assertEqual(code, 0)
            req = report["followups"]["required"]
            self.assertEqual(len(req), 1)
            argv_a = req[0]["argv"]
            self.assertIn("effort_sync", report["followups"]["approve_with"])
            with open(config_path, "w", encoding="utf-8") as handle:
                json.dump({"effort": {"agent_overrides": {"gsd-executor": "high"}}}, handle)
            code2, block2, _ = _run_followups_cli(
                [
                    "followups",
                    "--plan",
                    plan_path,
                    "--inventory",
                    inv_path,
                    "--project-dir",
                    project,
                ],
                env,
                fake,
            )
            self.assertEqual(code2, 0)
            assert block2 is not None
            self.assertEqual(block2["required"], req)
            tail = shlex.split(report["followups"]["approve_with"])
            self.assertIn("--fingerprint", tail)
            # B IN-08: an approval bound to other rows than the rebuilt ones runs nothing.
            stale = [*tail[: tail.index("--fingerprint") + 1], "0" * 16]
            calls_before = len(fake.argv_log)
            code_stale, parsed_stale, err_stale = _run_followups_cli(stale, env, fake)
            self.assertEqual(code_stale, 2)
            self.assertIsNone(parsed_stale)
            self.assertIn("changed since they were listed", err_stale)
            self.assertFalse(
                any("--apply" in row for row in fake.argv_log[calls_before:])
            )
            code3, parsed3, _ = _run_followups_cli(tail, env, fake)
            self.assertEqual(code3, 0)
            assert parsed3 is not None
            self.assertEqual(parsed3["results"][0]["argv"], argv_a)

    def test_drift_apply_forces_effort_require(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project, env, config_path = _setup_scratch_project(tmp)
            with open(config_path, "w", encoding="utf-8") as handle:
                json.dump(
                    {"effort": {"agent_overrides": {"gsd-executor": "low"}}},
                    handle,
                )
            fake = _tables_followups(config_path, env["HOME"])
            inv_path = os.path.join(tmp, "inventory.json")
            inv = scratch_inventory(project, env, fake, inv_path, host_name="claude")
            plan = _minimal_plan(
                "claude",
                inv,
                [
                    {
                        "key": "effort.agent_overrides.gsd-executor",
                        "op": "set",
                        "value": "high",
                        "existing": "high",
                        "source": "preset",
                    },
                ],
            )
            plan_path = os.path.join(tmp, "plan.json")
            plan_io.write_plan(plan_path, plan)
            rec = _RecordingRun(fake, config_path=config_path)
            code, report = _write_apply(plan_path, inv_path, project, env, rec)
            self.assertEqual(code, 0)
            self.assertEqual(len(report["followups"]["required"]), 1)
            self.assertIn("--require effort_sync", report["followups"]["approve_with"])
            code2, block2, _ = _run_followups_cli(
                [
                    "followups",
                    "--plan",
                    plan_path,
                    "--inventory",
                    inv_path,
                    "--project-dir",
                    project,
                ],
                env,
                fake,
            )
            self.assertEqual(code2, 0)
            assert block2 is not None
            self.assertEqual(block2["required"], [])


def _decided_plan_followups(tmp):
    project, env, config_path = _setup_scratch_project(tmp)
    fake = _tables_fake(config_path, env["HOME"])
    inv_path = os.path.join(tmp, "inventory.json")
    inv = scratch_inventory(project, env, fake, inv_path, host_name="codex")
    plan_path = os.path.join(tmp, "plan.json")
    code, _plan, raw, err = run_recommend(inv, "--profile", "adaptive", "--rigor", "standard")
    if code != 0 or raw is None:
        raise AssertionError(err)
    with open(plan_path, "wb") as handle:
        handle.write(raw)
    _decide_all_choices(plan_path, inv_path)
    return project, env, inv_path, plan_path, config_path, inv, fake



class TestFollowupSubprocessTimeouts(unittest.TestCase):
    """B WR-01: a timed-out subprocess is a failed row, never an escaped exception."""

    @staticmethod
    def _raise_timeout(cmd, **_kw):
        raise subprocess.TimeoutExpired(cmd, 600)

    def test_effort_dry_run_timeout_is_unavailable(self) -> None:
        self.assertIsNone(
            followups.effort_dry_run_count(["node", "t", "effort"], self._raise_timeout, {})
        )

    def test_effort_dry_run_non_object_json_is_unavailable(self) -> None:
        def run(cmd, **_kw):
            return subprocess.CompletedProcess(cmd, 0, "[1, 2]", "")

        self.assertIsNone(followups.effort_dry_run_count(["node"], run, {}))

    def test_run_one_timeout_is_a_failed_result(self) -> None:
        row = followups.FollowUp("installer", ["npx", "-y", "x"], "/p", "", "", "")
        result = followups._run_one(row, self._raise_timeout, {})
        self.assertEqual(result["returncode"], 1)
        self.assertIn("timed out", result["stderr_tail"])


if __name__ == "__main__":
    unittest.main()
