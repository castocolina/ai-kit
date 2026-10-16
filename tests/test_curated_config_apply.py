"""Apply dry-run, backup/marker unit tests (plans 18-16, 18-17)."""
import ast
import contextlib
import copy
import errno
import io
import json
import os
import re
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
import threading
import unittest
from datetime import UTC, datetime
from unittest import mock

sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "skills", "ai-kit-gsd-curated-config"),
)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills", "ai-kit-spec-review"))

from ai_kit_gsd_curated_config import apply as apply_mod
from ai_kit_gsd_curated_config import (
    cli,
    config_backup,
    cross_ai,
    cross_ai_script,
    plan_io,
    plan_schema,
)
from ai_kit_spec.detection import HOST_SIGNAL_ENV_VARS

from tests.test_curated_config_golden import load_fixture, tables_answer
from tests.test_curated_config_inventory import (
    FakeRun,
    _tree_snapshot,
    make_gsd_install,
    run_inventory,
    seed_cache,
)
from tests.test_curated_config_plan_edit import _partial_runner_plan, _run_plan_set
from tests.test_curated_config_recommend import run_recommend
from tests.test_curated_config_skills import add_plugin, add_skill

_FIXED_NOW = datetime(2026, 10, 15, 12, 0, 0, tzinfo=UTC)


def _fixed_now() -> datetime:
    return _FIXED_NOW


def _write_config(path: str, body: bytes, mode: int = 0o640) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as handle:
        handle.write(body)
    os.chmod(path, mode)


class TestBackupRestoreTracer(unittest.TestCase):
    def test_backup_then_restore_bytes_and_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            planning = os.path.join(tmp, ".planning")
            os.makedirs(planning)
            config_path = os.path.join(planning, "config.json")
            original = b'{\n    "x": 1\n}\n'
            with open(config_path, "wb") as handle:
                handle.write(original)
            os.chmod(config_path, 0o640)
            result = config_backup.create_backup(config_path, _fixed_now)
            expected = os.path.join(planning, "config.json.bak-20261015T120000Z")
            self.assertEqual(result.path, expected)
            self.assertFalse(result.reused)
            with open(expected, "rb") as handle:
                self.assertEqual(handle.read(), original)
            self.assertEqual(stat.S_IMODE(os.stat(expected).st_mode), 0o640)
            with open(config_path, "wb") as handle:
                handle.write(b"damaged\n")
            os.chmod(config_path, 0o600)
            config_backup.restore_backup(config_path, expected)
            with open(config_path, "rb") as handle:
                self.assertEqual(handle.read(), original)
            self.assertEqual(stat.S_IMODE(os.stat(config_path).st_mode), 0o640)

    def test_restore_none_removes_config_and_leaves_dir_clean(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            planning = os.path.join(tmp, ".planning")
            os.makedirs(planning)
            config_path = os.path.join(planning, "config.json")
            with open(config_path, "w", encoding="utf-8") as handle:
                handle.write("{}\n")
            config_backup.restore_backup(config_path, None)
            self.assertFalse(os.path.exists(config_path))
            leftovers = [name for name in os.listdir(planning) if name.startswith(".")]
            self.assertEqual(leftovers, [])


class TestBackupNaming(unittest.TestCase):
    def test_same_second_collisions_get_numeric_suffixes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config_path = os.path.join(tmp, ".planning", "config.json")
            for index in range(3):
                _write_config(config_path, f"v{index}\n".encode())
                result = config_backup.create_backup(config_path, _fixed_now)
                self.assertFalse(result.reused)
                basename = os.path.basename(result.path or "")
                expected = (
                    "config.json.bak-20261015T120000Z"
                    if index == 0
                    else f"config.json.bak-20261015T120000Z-{index}"
                )
                self.assertEqual(basename, expected)

    def test_absent_config_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config_path = os.path.join(tmp, ".planning", "config.json")
            os.makedirs(os.path.dirname(config_path))
            result = config_backup.create_backup(config_path, _fixed_now)
            self.assertEqual(result, config_backup.BackupResult(None, False))
            self.assertEqual(os.listdir(os.path.dirname(config_path)), [])

    def test_workstream_config_backups_beside_it(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws_dir = os.path.join(tmp, ".planning", "workstreams", "ws")
            config_path = os.path.join(ws_dir, "config.json")
            _write_config(config_path, b"{}\n")
            result = config_backup.create_backup(config_path, _fixed_now)
            self.assertTrue(result.path and result.path.startswith(ws_dir))


class TestBackupReuse(unittest.TestCase):
    def test_identical_config_reuses_newest_backup(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config_path = os.path.join(tmp, ".planning", "config.json")
            _write_config(config_path, b"same\n")
            first = config_backup.create_backup(config_path, _fixed_now)
            second = config_backup.create_backup(config_path, _fixed_now)
            self.assertEqual(first.path, second.path)
            self.assertTrue(second.reused)
            self.assertEqual(len(config_backup.list_backups(config_path)), 1)

    def test_changed_bytes_create_new_backup(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config_path = os.path.join(tmp, ".planning", "config.json")
            _write_config(config_path, b"one\n")
            config_backup.create_backup(config_path, _fixed_now)
            _write_config(config_path, b"two\n")
            result = config_backup.create_backup(config_path, _fixed_now)
            self.assertFalse(result.reused)
            self.assertEqual(len(config_backup.list_backups(config_path)), 2)

    def test_chmod_only_change_creates_new_backup(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config_path = os.path.join(tmp, ".planning", "config.json")
            _write_config(config_path, b"same\n", 0o640)
            config_backup.create_backup(config_path, _fixed_now)
            os.chmod(config_path, 0o600)
            result = config_backup.create_backup(config_path, _fixed_now)
            self.assertFalse(result.reused)
            assert result.path is not None
            self.assertEqual(stat.S_IMODE(os.stat(result.path).st_mode), 0o600)


class TestPrune(unittest.TestCase):
    def test_keeps_newest_three_by_stamp_and_numeric_suffix(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config_path = os.path.join(tmp, ".planning", "config.json")
            os.makedirs(os.path.dirname(config_path))
            names = [
                "config.json.bak-20261015T120000Z",
                "config.json.bak-20261015T120000Z-1",
                "config.json.bak-20261015T120000Z-10",
                "config.json.bak-20261015T120000Z-2",
                "config.json.bak-20261015T120001Z",
                "config.json.bak-manual",
                "config.json.bak-2026",
                "config.json.bak-20261015T120000Z.tmp",
            ]
            for name in names:
                with open(os.path.join(os.path.dirname(config_path), name), "wb") as handle:
                    handle.write(b"x")
            removed = config_backup.prune_backups(config_path)
            rows = config_backup.list_backups(config_path)
            kept = {os.path.basename(path) for path, _s, _n in rows}
            self.assertEqual(
                kept,
                {
                    "config.json.bak-20261015T120000Z-10",
                    "config.json.bak-20261015T120000Z-2",
                    "config.json.bak-20261015T120001Z",
                },
            )
            self.assertEqual(len(removed), 2)
            for protected in (
                "config.json.bak-manual",
                "config.json.bak-2026",
                "config.json.bak-20261015T120000Z.tmp",
            ):
                protected_path = os.path.join(os.path.dirname(config_path), protected)
                self.assertTrue(os.path.exists(protected_path))

    def test_marker_name_does_not_match_backup_re(self) -> None:
        self.assertIsNone(
            config_backup.BACKUP_RE.match("config.json.ai-kit-apply-marker")
        )


class TestApplyMarker(unittest.TestCase):
    def test_acquire_update_read_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config_path = os.path.join(tmp, ".planning", "config.json")
            _write_config(config_path, b"{}\n")
            self.assertTrue(config_backup.acquire_marker(config_path, True, _fixed_now))
            backup_name = "config.json.bak-20261015T120000Z"
            runner = {
                "path": ".planning/scripts/cross-ai.mjs",
                "snapshot": ".planning/scripts/cross-ai.mjs.ai-kit-apply-backup",
                "kind": "change",
            }
            config_backup.update_marker(
                config_path,
                backup=backup_name,
                runner=runner,
            )
            marker = config_backup.read_marker(config_path)
            assert marker is not None
            self.assertEqual(marker["backup"], backup_name)
            self.assertTrue(marker["config_existed"])
            self.assertEqual(marker["started"], "2026-10-15T12:00:00Z")
            self.assertEqual(marker["runner"], runner)
            self.assertFalse(marker["committed"])

    def test_second_acquire_is_exclusive(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config_path = os.path.join(tmp, ".planning", "config.json")
            _write_config(config_path, b"{}\n")
            self.assertTrue(config_backup.acquire_marker(config_path, True, _fixed_now))
            marker_path = config_backup.marker_path(config_path)
            with open(marker_path, "rb") as handle:
                before = handle.read()
            self.assertFalse(config_backup.acquire_marker(config_path, True, _fixed_now))
            with open(marker_path, "rb") as handle:
                self.assertEqual(handle.read(), before)

    def test_acquire_race_yields_one_winner(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config_path = os.path.join(tmp, ".planning", "config.json")
            _write_config(config_path, b"{}\n")
            results: list[bool] = []
            barrier = threading.Barrier(8)

            def worker() -> None:
                barrier.wait()
                results.append(config_backup.acquire_marker(config_path, True, _fixed_now))

            threads = [threading.Thread(target=worker) for _ in range(8)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()
            self.assertEqual(sum(results), 1)
            planning = os.path.dirname(config_path)
            temps = [name for name in os.listdir(planning) if name.startswith(".bak-tmp-")]
            self.assertEqual(temps, [])

    def test_fresh_project_creates_planning_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config_path = os.path.join(tmp, ".planning", "config.json")
            self.assertTrue(config_backup.acquire_marker(config_path, False, _fixed_now))
            self.assertTrue(os.path.isdir(os.path.dirname(config_path)))
            self.assertTrue(os.path.isfile(config_backup.marker_path(config_path)))
            config_backup.update_marker(config_path, committed=True)
            marker = config_backup.read_marker(config_path)
            assert marker is not None
            self.assertTrue(marker["committed"])

    def test_read_marker_absent_and_corrupt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config_path = os.path.join(tmp, ".planning", "config.json")
            self.assertIsNone(config_backup.read_marker(config_path))
            os.makedirs(os.path.dirname(config_path))
            with open(config_backup.marker_path(config_path), "w", encoding="utf-8") as handle:
                handle.write("not json")
            self.assertEqual(config_backup.read_marker(config_path), {"corrupt": True})

    def test_clear_marker_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config_path = os.path.join(tmp, ".planning", "config.json")
            config_backup.clear_marker(config_path)
            _write_config(config_path, b"{}\n")
            self.assertTrue(config_backup.acquire_marker(config_path, True, _fixed_now))
            config_backup.clear_marker(config_path)
            self.assertIsNone(config_backup.read_marker(config_path))

    def test_update_marker_without_cache_sibling(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config_path = os.path.join(tmp, ".planning", "config.json")
            _write_config(config_path, b"{}\n")
            self.assertTrue(config_backup.acquire_marker(config_path, True, _fixed_now))
            with mock.patch.object(
                config_backup.gsd_catalog,
                "load_ai_kit_spec_module",
                return_value=None,
            ):
                with self.assertRaises(OSError) as ctx:
                    config_backup.update_marker(config_path, committed=True)
                self.assertIn(config_backup.gsd_catalog.SIBLING_MISSING, str(ctx.exception))


class TestRunnerSnapshot(unittest.TestCase):
    def test_snapshot_restore_runner_bytes_and_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            scripts = os.path.join(tmp, ".planning", "scripts")
            os.makedirs(scripts)
            runner = os.path.join(scripts, "cross-ai.mjs")
            original = b"#!/usr/bin/env node\n"
            with open(runner, "wb") as handle:
                handle.write(original)
            os.chmod(runner, 0o755)
            snapshot = config_backup.snapshot_file(runner)
            assert snapshot is not None
            with open(runner, "wb") as handle:
                handle.write(b"changed\n")
            config_backup.restore_backup(runner, snapshot)
            with open(runner, "rb") as handle:
                self.assertEqual(handle.read(), original)
            self.assertEqual(stat.S_IMODE(os.stat(runner).st_mode), 0o755)
            config_backup.discard_snapshot(snapshot)
            self.assertFalse(os.path.exists(snapshot))

    def test_snapshot_absent_and_discard_noop(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            missing = os.path.join(tmp, "nope.mjs")
            self.assertIsNone(config_backup.snapshot_file(missing))
            config_backup.discard_snapshot(os.path.join(tmp, "ghost.ai-kit-apply-backup"))


class TestClearRunnerMarkerOrder(unittest.TestCase):
    def test_failed_marker_update_keeps_snapshot(self) -> None:
        """B IN-03: the marker never points at a snapshot that is already gone."""
        with tempfile.TemporaryDirectory() as tmp:
            config_path = os.path.join(tmp, ".planning", "config.json")
            _write_config(config_path, b"{}")
            config_backup.acquire_marker(config_path, True, _fixed_now)
            snap = os.path.join(tmp, "cross-ai.mjs" + config_backup.SNAPSHOT_SUFFIX)
            _write_config(snap, b"old runner")
            with mock.patch.object(
                config_backup, "update_marker", side_effect=OSError("marker busy")
            ), self.assertRaises(OSError):
                apply_mod._clear_runner_marker(config_path, snap)
            self.assertTrue(os.path.isfile(snap))
            apply_mod._clear_runner_marker(config_path, snap)
            self.assertFalse(os.path.isfile(snap))
            marker = config_backup.read_marker(config_path)
            assert marker is not None
            self.assertIsNone(marker["runner"])


class TestRecoveryText(unittest.TestCase):
    def _config(self, tmp: str) -> str:
        return os.path.join(tmp, ".planning", "config.json")

    def test_none_marker(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config_path = self._config(tmp)
            text = config_backup.recovery_text(None, config_path)
            self.assertIn("run apply again", text)
            self.assertNotIn("put ", text)

    def test_corrupt_marker(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config_path = self._config(tmp)
            text = config_backup.recovery_text({"corrupt": True}, config_path)
            self.assertIn("unreadable", text)
            self.assertNotIn("put ", text)

    def test_committed_no_restore(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config_path = self._config(tmp)
            marker = {"committed": True, "runner": None}
            text = config_backup.recovery_text(marker, config_path)
            self.assertIn("do not restore the backup", text)
            self.assertNotIn("put ", text)
            self.assertIn("delete the marker", text)

    def test_committed_add_runner_no_snapshot_in_text(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config_path = self._config(tmp)
            marker = {
                "committed": True,
                "runner": {"path": ".planning/scripts/cross-ai.mjs", "kind": "add"},
            }
            text = config_backup.recovery_text(marker, config_path)
            self.assertIn("delete the marker", text)
            self.assertNotIn("None", text)
            self.assertNotIn("ai-kit-apply-backup", text)

    def test_uncommitted_backup_and_change_runner(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config_path = self._config(tmp)
            marker = {
                "committed": False,
                "config_existed": True,
                "backup": "config.json.bak-20261015T120000Z",
                "runner": {
                    "path": ".planning/scripts/cross-ai.mjs",
                    "snapshot": ".planning/scripts/cross-ai.mjs.ai-kit-apply-backup",
                    "kind": "change",
                },
            }
            text = config_backup.recovery_text(marker, config_path)
            self.assertIn("apply --dry-run", text)
            backup = os.path.join(tmp, ".planning", "config.json.bak-20261015T120000Z")
            # B IN-02: the backup is named by an absolute path, usable from any cwd.
            self.assertIn(f"put {backup} back over", text)
            self.assertIn(
                "put .planning/scripts/cross-ai.mjs.ai-kit-apply-backup back over",
                text,
            )

    def test_uncommitted_new_config_and_add_runner(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config_path = self._config(tmp)
            marker = {
                "committed": False,
                "config_existed": False,
                "backup": None,
                "runner": {
                    "path": ".planning/scripts/cross-ai.mjs",
                    "kind": "add",
                },
            }
            text = config_backup.recovery_text(marker, config_path)
            self.assertIn("apply --dry-run", text)
            self.assertIn("delete ", text)
            self.assertIn("cross-ai.mjs if it exists", text)

    def test_uncommitted_no_backup_no_runner(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config_path = self._config(tmp)
            marker = {
                "committed": False,
                "config_existed": True,
                "backup": None,
                "runner": None,
            }
            text = config_backup.recovery_text(marker, config_path)
            self.assertEqual(text.count("needs no restore"), 2)
            self.assertNotIn("put ", text)
            self.assertNotIn("delete ", config_path)
            self.assertNotIn("--dry-run", text)


def _scratch_env(home: str, gsd_home: str, xdg: str) -> dict[str, str]:
    return {
        "HOME": home,
        "GSD_HOME": gsd_home,
        "XDG_CACHE_HOME": xdg,
        "PATH": "",
    }


def scratch_inventory(
    project: str,
    env: dict,
    fake: FakeRun,
    inv_path: str,
    *,
    host_name: str = "codex",
) -> dict:
    code, parsed, err = run_inventory(project, env, fake, "--host", host_name)
    if code != 0 or parsed is None:
        raise AssertionError(f"inventory failed: {err}")
    with open(inv_path, "w", encoding="utf-8") as handle:
        handle.write(plan_io.canonical_json(parsed))
    return parsed


def _decide_all_choices(plan_path: str, inv_path: str) -> None:
    while True:
        plan, _err = plan_io.load_plan(plan_path)
        assert plan is not None
        pending = [
            e
            for e in plan.get("entries") or []
            if e.get("status") == "needs_choice"
        ]
        if pending:
            entry = pending[0]
            key = entry["key"]
            cands = entry.get("candidates") or []
            if not cands:
                raise AssertionError(f"no candidates for {key}")
            first = cands[0]
            if isinstance(first, dict) and "model" in first:
                raw = first["model"]
            elif isinstance(first, dict) and "value" in first:
                raw = json.dumps([first["value"]])
            elif isinstance(first, bool):
                raw = "true" if first else "false"
            elif isinstance(first, (list, dict)):
                raw = json.dumps(first)
            else:
                raw = str(first)
            code, _, err = _run_plan_set(plan_path, inv_path, key, raw)
            if code != 0:
                raise AssertionError(err)
            continue
        artifacts = plan.get("artifacts") or []
        if artifacts and artifacts[0].get("status") == "needs_choice":
            art = artifacts[0]
            for runner, detail in (art.get("choices") or {}).items():
                cands = detail.get("candidates") or []
                if not cands:
                    continue
                model = cands[0]["model"] if isinstance(cands[0], dict) else cands[0]
                code, _, err = _run_plan_set(
                    plan_path, inv_path, f"script:cross-ai.model.{runner}", model
                )
                if code != 0:
                    raise AssertionError(err)
                break
            else:
                break
            continue
        break


def _run_apply(
    plan_path: str,
    inv_path: str,
    project: str,
    env: dict,
    fake: "FakeRun | _RecordingRun",
    *,
    dry_run: bool = True,
) -> tuple[int, dict | None, str, str]:
    argv = [
        "apply",
        "--plan",
        plan_path,
        "--inventory",
        inv_path,
        "--project-dir",
        project,
    ]
    if dry_run:
        argv.append("--dry-run")
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = cli.main(
            argv,
            which_fn=lambda name, **_kw: "node" if name == "node" else None,
            env_fn=lambda: dict(env),
            run_fn=fake,
        )
    parsed = json.loads(out.getvalue()) if out.getvalue().strip() else None
    return code, parsed, out.getvalue(), err.getvalue()


def _setup_scratch_project(tmp: str) -> tuple[str, dict, str]:
    project = os.path.join(tmp, "project")
    home = os.path.join(tmp, "home")
    gsd_home = os.path.join(tmp, "gsd_home")
    xdg = os.path.join(tmp, "xdg")
    os.makedirs(project)
    os.makedirs(home, exist_ok=True)
    add_plugin(
        home,
        "ponytail",
        "ponytail",
        ["ponytail", "ponytail-audit", "ponytail-debt", "ponytail-review"],
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
    os.makedirs(os.path.join(project, ".planning"), exist_ok=True)
    with open(os.path.join(project, "AGENTS.md"), "w", encoding="utf-8") as handle:
        handle.write("# agents\n")
    with open(os.path.join(project, "package.json"), "w", encoding="utf-8") as handle:
        json.dump({"dependencies": {"react": "19.0.0"}}, handle)
    make_gsd_install(os.path.join(project, ".claude", "gsd-core"))
    config_path = os.path.join(project, ".planning", "config.json")
    with open(config_path, "w", encoding="utf-8") as handle:
        json.dump({"model_profile": "balanced"}, handle)
    seed_cache(xdg, load_fixture("runtimes.json"), load_fixture("model-catalog.json"))
    env = _scratch_env(home, gsd_home, xdg)
    return project, env, config_path


def _tables_fake(config_path: str, home: str) -> FakeRun:
    return FakeRun(
        node_stdout=lambda argv, h=home: json.dumps(
            tables_answer(json.loads(argv[6]), h)
        ),
        config_path_stdout=config_path,
    )


def _decided_plan(tmp: str) -> tuple[str, dict, str, str, str, dict, FakeRun]:
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


def _assert_no_writes(project: str, fake: FakeRun) -> None:
    planning = os.path.join(project, ".planning")
    for name in os.listdir(planning):
        self_msg = name
        if "bak-" in name or name.endswith(".ai-kit-apply-marker"):
            raise AssertionError(f"unexpected artifact {self_msg}")
    runner = os.path.join(planning, "scripts", "cross-ai.mjs")
    if os.path.isfile(runner):
        raise AssertionError("cross-ai.mjs was written")
    for cmd in fake.argv_log:
        joined = " ".join(str(part) for part in cmd)
        if "config-set" in joined:
            raise AssertionError("config-set was invoked")


class TestApplyRefusals(unittest.TestCase):
    def test_missing_inventory_argparse(self) -> None:
        with self.assertRaises(SystemExit) as ctx:
            cli._build_parser().parse_args(
                ["apply", "--plan", "p.json", "--project-dir", "d"]
            )
        self.assertEqual(ctx.exception.code, 2)

    def test_needs_choice_entry_named(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project, env, inv_path, plan_path, _cfg, _inv, fake = _decided_plan(tmp)
            plan, _ = plan_io.load_plan(plan_path)
            assert plan is not None
            plan["entries"].append(
                {
                    "key": "models.research",
                    "op": "set",
                    "status": "needs_choice",
                    "value": None,
                    "candidates": [],
                }
            )
            with open(plan_path, "w", encoding="utf-8") as handle:
                handle.write(plan_io.canonical_json(plan))
            fake.argv_log.clear()
            before = _tree_snapshot(project)
            code, _report, _out, err = _run_apply(
                plan_path, inv_path, project, env, fake, dry_run=True
            )
            self.assertEqual(code, 2)
            self.assertIn("models.research", err)
            self.assertEqual(_tree_snapshot(project), before)
            _assert_no_writes(project, fake)

    def test_needs_choice_artifact_named(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project, env, inv_path, plan_path, _cfg, inv, fake = _decided_plan(tmp)
            plan, _ = plan_io.load_plan(plan_path)
            assert plan is not None
            plan = _partial_runner_plan(inv, plan)
            cmd = next(
                e for e in plan["entries"] if e["key"] == "workflow.cross_ai_command"
            )
            cmd.pop("status", None)
            with open(plan_path, "w", encoding="utf-8") as handle:
                handle.write(plan_io.canonical_json(plan))
            fake.argv_log.clear()
            code, _, _, err = _run_apply(plan_path, inv_path, project, env, fake)
            self.assertEqual(code, 2)
            self.assertIn(f"artifact:{cross_ai.SCRIPT_PATH}", err)

    def test_needs_choice_sorted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project, env, inv_path, plan_path, _cfg, inv, fake = _decided_plan(tmp)
            plan, _ = plan_io.load_plan(plan_path)
            assert plan is not None
            plan = _partial_runner_plan(inv, plan)
            plan["entries"].append(
                {
                    "key": "models.verification",
                    "op": "set",
                    "status": "needs_choice",
                    "value": None,
                    "candidates": [],
                }
            )
            with open(plan_path, "w", encoding="utf-8") as handle:
                handle.write(plan_io.canonical_json(plan))
            code, _, _, err = _run_apply(plan_path, inv_path, project, env, fake)
            self.assertEqual(code, 2)
            self.assertLess(
                err.index("artifact:"),
                err.index("models.verification"),
            )

    def test_inventory_digest_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project, env, inv_path, plan_path, _cfg, inv, fake = _decided_plan(tmp)
            inv = copy.deepcopy(inv)
            inv["host"] = "claude"
            with open(inv_path, "w", encoding="utf-8") as handle:
                handle.write(plan_io.canonical_json(inv))
            code, _, _, err = _run_apply(plan_path, inv_path, project, env, fake)
            self.assertEqual(code, 2)
            self.assertIn("inventory digest", err)

    def test_rejected_key_preflight(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project, env, inv_path, plan_path, config_path, _inv, _fake = _decided_plan(
                tmp
            )

            def reject_profile(argv, h=env["HOME"]):
                body = tables_answer(json.loads(argv[6]), h)
                body["valid_keys"]["rejected"] = sorted(
                    set(body["valid_keys"]["rejected"]) | {"model_profile"}
                )
                body["valid_keys"]["accepted"] = [
                    k for k in body["valid_keys"]["accepted"] if k != "model_profile"
                ]
                return json.dumps(body)

            fake = FakeRun(
                node_stdout=reject_profile, config_path_stdout=config_path
            )
            fake.argv_log.clear()
            code, _, _, err = _run_apply(plan_path, inv_path, project, env, fake)
            self.assertEqual(code, 2)
            self.assertIn("model_profile", err)
            self.assertIn("1.16.0", err)

    def test_node_null_preflight(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project, env, inv_path, plan_path, config_path, _inv, _fake = _decided_plan(
                tmp
            )
            fake = FakeRun(
                node_stdout=lambda _argv: "null",
                config_path_stdout=config_path,
            )
            code, _, _, err = _run_apply(plan_path, inv_path, project, env, fake)
            self.assertEqual(code, 2)
            self.assertIn("isValidConfigKey unavailable", err)

    def test_node_failure_preflight(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project, env, inv_path, plan_path, config_path, _inv, base = _decided_plan(
                tmp
            )

            class FailTablesRun(FakeRun):
                def __call__(self, cmd, **kw):
                    if len(cmd) >= 3 and cmd[0] == "node" and cmd[1] == "-e":
                        return subprocess.CompletedProcess(cmd, 1, "", "boom")
                    return super().__call__(cmd, **kw)

            fake = FailTablesRun(
                node_stdout=base.node_stdout,
                config_path_stdout=config_path,
            )
            code, _, _, err = _run_apply(plan_path, inv_path, project, env, fake)
            self.assertEqual(code, 2)
            self.assertIn("node exited 1", err)

    def test_encoder_refusal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project, env, inv_path, plan_path, _cfg, _inv, fake = _decided_plan(tmp)
            plan, _ = plan_io.load_plan(plan_path)
            assert plan is not None
            plan["entries"].append(
                {
                    "key": "claude_md_path",
                    "op": "set",
                    "value": "true",
                    "source": "user",
                }
            )
            with open(plan_path, "w", encoding="utf-8") as handle:
                handle.write(plan_io.canonical_json(plan))
            fake.argv_log.clear()
            code, _, _, err = _run_apply(plan_path, inv_path, project, env, fake)
            self.assertEqual(code, 2)
            self.assertIn("claude_md_path", err)

    def test_destination_project_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _project_a, env, inv_path, plan_path, config_a, _inv, fake = _decided_plan(tmp)
            project_b = os.path.join(tmp, "project_b")
            os.makedirs(os.path.join(project_b, ".planning"), exist_ok=True)
            config_b = os.path.join(project_b, ".planning", "config.json")
            with open(config_b, "w", encoding="utf-8") as handle:
                json.dump({}, handle)
            make_gsd_install(os.path.join(project_b, ".claude", "gsd-core"))
            fake_b = FakeRun(
                node_stdout=fake.node_stdout,
                config_path_stdout=config_b,
            )
            before = _tree_snapshot(project_b)
            code, _, _, err = _run_apply(plan_path, inv_path, project_b, env, fake_b)
            self.assertEqual(code, 2)
            self.assertIn(config_b, err)
            self.assertIn(config_a, err)
            self.assertEqual(_tree_snapshot(project_b), before)

    def test_destination_workstream_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project, env, inv_path, plan_path, config_path, _inv, fake = _decided_plan(
                tmp
            )
            ws_config = os.path.join(
                project, ".planning", "workstreams", "ws", "config.json"
            )
            os.makedirs(os.path.dirname(ws_config), exist_ok=True)
            fake_ws = FakeRun(
                node_stdout=fake.node_stdout,
                config_path_stdout=ws_config,
            )
            code, _, _, err = _run_apply(plan_path, inv_path, project, env, fake_ws)
            self.assertEqual(code, 2)
            self.assertIn(ws_config, err)
            self.assertIn(config_path, err)

    def test_inventory_without_config_path(self) -> None:
        """B IN-04: a missing existing_config.path is the clean rerun message, not KeyError."""
        with tempfile.TemporaryDirectory() as tmp:
            project, env, inv_path, plan_path, _cfg, _inv, fake = _decided_plan(tmp)
            plan, _ = plan_io.load_plan(plan_path)
            inv, _ = plan_io.load_inventory(inv_path)
            assert plan is not None and inv is not None
            inv["existing_config"].pop("path")
            inputs = apply_mod.Inputs(plan, plan_path, inv, inv_path, project)
            deps = apply_mod.ApplyDeps(
                lambda name: "node" if name == "node" else None, fake, lambda: dict(env)
            )
            target, error = apply_mod.resolve_target(inputs, deps)
            self.assertIsNone(target)
            assert error is not None
            self.assertIn("rerun inventory", error)

    def test_relative_inventory_config_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project, env, inv_path, plan_path, _cfg, inv, fake = _decided_plan(tmp)
            inv = copy.deepcopy(inv)
            inv["existing_config"]["path"] = ".planning/config.json"
            with open(inv_path, "w", encoding="utf-8") as handle:
                handle.write(plan_io.canonical_json(inv))
            plan, _ = plan_io.load_plan(plan_path)
            assert plan is not None
            plan["inventory_digest"] = plan_schema.inventory_digest(inv)
            with open(plan_path, "w", encoding="utf-8") as handle:
                handle.write(plan_io.canonical_json(plan))
            code, _, _, err = _run_apply(plan_path, inv_path, project, env, fake)
            self.assertEqual(code, 2)
            self.assertIn("not an absolute config path", err)

    def test_hand_edited_plan_refused_at_load(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project, env, inv_path, plan_path, _cfg, _inv, fake = _decided_plan(tmp)
            plan, _ = plan_io.load_plan(plan_path)
            assert plan is not None
            dup = copy.deepcopy(plan["entries"][0])
            plan["entries"].insert(0, dup)
            cmd = next(
                e for e in plan["entries"] if e["key"] == "workflow.cross_ai_command"
            )
            cmd["value"] = "node other.mjs"
            cmd.pop("forced", None)
            plan["entries"].append(
                {
                    "key": "agent_skills_security.trusted_global_roots",
                    "op": "set",
                    "value": ["/abs/evil"],
                    "existing": ["/abs/evil"],
                    "source": "user",
                }
            )
            with open(plan_path, "w", encoding="utf-8") as handle:
                handle.write(plan_io.canonical_json(plan))
            fake.argv_log.clear()
            code, _, _, err = _run_apply(plan_path, inv_path, project, env, fake)
            self.assertEqual(code, 2)
            self.assertIn("duplicate entry key", err)
            node_calls = [a for a in fake.argv_log if a and a[0] == "node"]
            self.assertEqual(node_calls, [])

    def test_forced_command_warning_on_success(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project, env, inv_path, plan_path, _cfg, _inv, fake = _decided_plan(tmp)
            code_set, _, err_set = _run_plan_set(
                plan_path,
                inv_path,
                "workflow.cross_ai_command",
                "node other.mjs",
                force=True,
            )
            self.assertEqual(code_set, 0, err_set)
            code, report, _, err = _run_apply(plan_path, inv_path, project, env, fake)
            self.assertEqual((code, err), (0, ""))
            assert report is not None
            self.assertTrue(
                any("full permissions" in w for w in report.get("warnings", []))
            )


class TestDiffKinds(unittest.TestCase):
    def test_diff_entries_all_kinds(self) -> None:
        plan = {
            "entries": [
                {"key": "a.add", "op": "set", "value": 1},
                {"key": "b.change", "op": "set", "value": 2},
                {"key": "c.keep", "op": "set", "value": 3},
                {"key": "d.remove", "op": "unset"},
                {"key": "e.absent_unset", "op": "unset"},
                {"key": "f.keep_op", "op": "keep", "existing": 9},
            ]
        }
        live = {"a": {}, "b": {"change": 0}, "c": {"keep": 3}, "d": {"remove": 1}}
        rows = apply_mod.diff_entries(plan, live, {})
        kinds = {r["key"]: r["kind"] for r in rows}
        self.assertEqual(
            kinds,
            {
                "a.add": "add",
                "b.change": "change",
                "c.keep": "keep",
                "d.remove": "remove",
                "e.absent_unset": "keep",
                "f.keep_op": "keep",
            },
        )
        self.assertEqual([r["key"] for r in rows], sorted(kinds))

    def test_nested_live_lookup(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project, env, inv_path, plan_path, config_path, _inv, fake = _decided_plan(
                tmp
            )
            with open(config_path, "w", encoding="utf-8") as handle:
                json.dump(
                    {
                        "model_profile": "balanced",
                        "model_policy": {"provider": "openai"},
                    },
                    handle,
                )
            plan, _ = plan_io.load_plan(plan_path)
            assert plan is not None
            plan["entries"] = [
                {
                    "key": "model_policy.provider",
                    "op": "set",
                    "value": "generic",
                    "source": "user",
                }
            ]
            plan["artifacts"] = []
            for entry in list(plan["entries"]):
                if entry["key"].startswith("workflow.cross_ai"):
                    plan["entries"].remove(entry)
            with open(plan_path, "w", encoding="utf-8") as handle:
                handle.write(plan_io.canonical_json(plan))
            code, report, _, err = _run_apply(plan_path, inv_path, project, env, fake)
            self.assertEqual((code, err), (0, ""))
            assert report is not None
            row = next(r for r in report["diff"] if r["key"] == "model_policy.provider")
            self.assertEqual(row["kind"], "change")
            self.assertEqual(row["from"], "openai")

    def test_unreadable_live_config_refused(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project, env, inv_path, plan_path, config_path, _inv, fake = _decided_plan(
                tmp
            )
            with open(config_path, "w", encoding="utf-8") as handle:
                handle.write("{not json")
            code, _, _, err = _run_apply(plan_path, inv_path, project, env, fake)
            self.assertEqual(code, 2)
            self.assertIn(config_path, err)

    def test_agent_skills_translated_in_diff(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project, env, inv_path, plan_path, config_path, inv, fake = _decided_plan(
                tmp
            )
            refs = apply_mod.skill_value(inv, ["react-dev"])
            with open(config_path, "w", encoding="utf-8") as handle:
                json.dump({"agent_skills": {"gsd-executor": refs}}, handle)
            plan, _ = plan_io.load_plan(plan_path)
            assert plan is not None
            plan["entries"] = [
                {
                    "key": "agent_skills.gsd-executor",
                    "op": "set",
                    "value": ["react-dev"],
                    "source": "user",
                }
            ]
            plan["artifacts"] = []
            with open(plan_path, "w", encoding="utf-8") as handle:
                handle.write(plan_io.canonical_json(plan))
            code, report, _, err = _run_apply(plan_path, inv_path, project, env, fake)
            self.assertEqual((code, err), (0, ""))
            assert report is not None
            row = next(
                r for r in report["diff"] if r["key"] == "agent_skills.gsd-executor"
            )
            self.assertEqual(row["kind"], "keep")
            self.assertEqual(row["to"], refs)
            self.assertNotEqual(row["to"], ["react-dev"])


class TestDryRunPredictedReconcile(unittest.TestCase):
    """B WR-06: a fresh-project dry run shows the reconcile removals apply will make."""

    def _report(self, tmp: str, config_exists: bool) -> dict:
        config_path = os.path.join(tmp, ".planning", "config.json")
        if config_exists:
            _write_config(config_path, b"{}")
        plan = {
            "host": "claude",
            "entries": [{"key": "model_profile", "op": "set", "value": "quality"}],
            "artifacts": [],
        }
        inv = {
            "global_defaults": {
                "values": {
                    "model_profile": "balanced",
                    "resolve_model_ids": "omit",
                    "model_policy": {"budget": "low"},
                    "custom_unrelated": "keepme",
                }
            }
        }
        inputs = apply_mod.Inputs(plan, "plan.json", inv, "inv.json", tmp)
        paths = apply_mod.gsd_catalog.GsdCorePaths("node", "model-catalog.cjs", "schema.cjs")
        target = apply_mod.Target(None, paths, config_path, {}, "1.16.0", "/core")
        return apply_mod.dry_run_report(inputs, target, {}, b"")

    def test_absent_config_lists_predicted_removals(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report = self._report(tmp, config_exists=False)
            predicted = {row["key"]: row for row in report["diff"] if row.get("predicted")}
            self.assertEqual(set(predicted), {"model_policy.budget", "resolve_model_ids"})
            self.assertEqual(predicted["resolve_model_ids"]["kind"], "remove")
            self.assertEqual(predicted["resolve_model_ids"]["from"], "omit")
            keys = [row["key"] for row in report["diff"]]
            self.assertEqual(keys, sorted(keys))
            self.assertTrue(any("unverified" in w for w in report["warnings"]))

    def test_existing_config_has_no_predicted_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report = self._report(tmp, config_exists=True)
            self.assertFalse(any(row.get("predicted") for row in report["diff"]))


class TestDryRunDeterminism(unittest.TestCase):
    def test_empty_plan_diff(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project, env, inv_path, plan_path, _cfg, inv, fake = _decided_plan(tmp)
            plan = {
                "schema_version": plan_schema.PLAN_SCHEMA_VERSION,
                "host": inv["host"],
                "profile": "adaptive",
                "rigor": "standard",
                "inventory_digest": plan_schema.inventory_digest(inv),
                "entries": [],
                "artifacts": [],
                "notes": [],
            }
            with open(plan_path, "w", encoding="utf-8") as handle:
                handle.write(plan_io.canonical_json(plan))
            code, report, _, err = _run_apply(plan_path, inv_path, project, env, fake)
            self.assertEqual((code, err), (0, ""))
            assert report is not None
            self.assertEqual(report["diff"], [])

    def test_two_dry_runs_identical_stdout(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project, env, inv_path, plan_path, _cfg, _inv, fake = _decided_plan(tmp)
            fake.argv_log.clear()
            code_a, _, out_a, err_a = _run_apply(
                plan_path, inv_path, project, env, fake, dry_run=True
            )
            fake.argv_log.clear()
            code_b, _, out_b, err_b = _run_apply(
                plan_path, inv_path, project, env, fake, dry_run=True
            )
            self.assertEqual((code_a, err_a), (0, ""))
            self.assertEqual((code_b, err_b), (0, ""))
            self.assertEqual(out_a, out_b)


class TestApplyDispatch(unittest.TestCase):
    def test_exact_name_handlers(self) -> None:
        self.assertIs(cli._COMMAND_HANDLERS["apply"], cli._cmd_apply)
        pairs = (
            ("apply-profile", cli._cmd_apply_profile),
            ("apply-critical-agents", cli._cmd_apply_critical_agents),
            ("apply-execution", cli._cmd_apply_execution),
            ("apply-review", cli._cmd_apply_review),
            ("apply-claude-md-path", cli._cmd_apply_claude_md_path),
            ("apply-workflow-defaults", cli._cmd_apply_workflow_defaults),
        )
        for name, handler in pairs:
            self.assertIs(cli._COMMAND_HANDLERS[name], handler)

    def test_apply_review_does_not_use_v2_apply(self) -> None:
        args = cli._build_parser().parse_args(
            [
                "apply-review",
                "--project-dir",
                ".",
                "--cli",
                "codex",
                "--model",
                "gpt-5",
            ]
        )
        handler = cli._COMMAND_HANDLERS.get(args.command)
        self.assertIs(handler, cli._cmd_apply_review)
        self.assertIsNot(handler, cli._cmd_apply)


class TestDryRunTracer(unittest.TestCase):
    def test_dry_run_shows_diff_and_touches_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project, env, config_path = _setup_scratch_project(tmp)
            fake = _tables_fake(config_path, env["HOME"])
            inv_path = os.path.join(tmp, "inventory.json")
            inv = scratch_inventory(project, env, fake, inv_path, host_name="codex")
            plan_path = os.path.join(tmp, "plan.json")
            code, _plan, raw, err = run_recommend(
                inv, "--profile", "adaptive", "--rigor", "standard"
            )
            self.assertEqual((code, err), (0, ""))
            assert raw is not None
            with open(plan_path, "wb") as handle:
                handle.write(raw)
            _decide_all_choices(plan_path, inv_path)
            before = _tree_snapshot(project)
            fake.argv_log.clear()
            code, report, _out, err = _run_apply(
                plan_path, inv_path, project, env, fake, dry_run=True
            )
            self.assertEqual((code, err), (0, ""))
            assert report is not None
            self.assertTrue(report["dry_run"])
            self.assertEqual(report["config_path"], config_path)
            kinds = {row["key"]: row["kind"] for row in report["diff"]}
            self.assertEqual(kinds.get("model_profile"), "change")
            self.assertIn("add", kinds.values())
            art_rows = [a for a in report["artifacts"] if a["path"].endswith("cross-ai.mjs")]
            self.assertTrue(art_rows)
            self.assertEqual(art_rows[0]["kind"], "add")
            self.assertEqual(_tree_snapshot(project), before)
            node_calls = [a for a in fake.argv_log if a and a[0] == "node"]
            self.assertEqual(len(node_calls), 2)
            self.assertEqual(node_calls[0][2], "config-path")
            self.assertEqual(node_calls[1][1], "-e")
            for cmd in fake.argv_log:
                joined = " ".join(str(part) for part in cmd)
                self.assertNotIn("config-set", joined)
                self.assertNotIn("config-new-project", joined)



from ai_kit_gsd_curated_config import gsd_catalog


def _strict_encode():
    mod = gsd_catalog.load_ai_kit_spec_module("gsd_tools")
    assert mod is not None
    return mod.encode_value_strict


def _write_apply(plan_path, inv_path, project, env, run_fn):
    plan, _ = plan_io.load_plan(plan_path)
    inv, _ = plan_io.load_inventory(inv_path)
    assert plan is not None and inv is not None
    inputs = apply_mod.Inputs(plan, plan_path, inv, inv_path, project)
    deps = apply_mod.ApplyDeps(
        lambda name: "node" if name == "node" else None,
        run_fn,
        lambda: dict(env),
        now_fn=_fixed_now,
    )
    return apply_mod.run_apply(inputs, deps, _strict_encode())


def _decode_config_set_value(encoded: str):
    if encoded == "null":
        return None
    if encoded == "true":
        return True
    if encoded == "false":
        return False
    if encoded and encoded[0] in "[{":
        return json.loads(encoded)
    try:
        return int(encoded)
    except ValueError:
        pass
    try:
        return float(encoded)
    except ValueError:
        return encoded


def _mutate_config_file(config_path: str, key: str, value) -> None:
    with open(config_path, encoding="utf-8") as handle:
        live = json.load(handle)
    parts = key.split(".")
    if value is None:
        node = live
        for part in parts[:-1]:
            if not isinstance(node, dict) or part not in node:
                return
            node = node[part]
        if isinstance(node, dict):
            node.pop(parts[-1], None)
        for index in range(len(parts) - 1, 0, -1):
            parent_key = parts[:index]
            cursor = live
            for part in parent_key:
                cursor = cursor.get(part) if isinstance(cursor, dict) else None
            if isinstance(cursor, dict) and not cursor:
                parent = live
                for part in parent_key[:-1]:
                    parent = parent[part]
                parent.pop(parent_key[-1], None)
    else:
        node = live
        for part in parts[:-1]:
            next_node = node.get(part)
            if not isinstance(next_node, dict):
                next_node = {}
                node[part] = next_node
            node = next_node
        node[parts[-1]] = value
    with open(config_path, "w", encoding="utf-8") as handle:
        json.dump(live, handle)
        handle.write("\n")


class _RecordingRun:
    def __init__(
        self,
        base: FakeRun,
        *,
        fail_config_set: int | None = None,
        config_path: str | None = None,
    ):
        self._base = base
        self.argv_log: list[list[str]] = []
        self.env_log: list[dict] = []
        self._fail_config_set = fail_config_set
        self._set_calls = 0
        self._config_path = config_path

    def __call__(self, cmd, **kw):
        row = [str(part) for part in cmd]
        self.argv_log.append(row)
        env = kw.get("env")
        self.env_log.append(dict(env) if env else {})
        if len(row) >= 4 and row[0] == "node" and row[2] == "query" and row[3] == "config-set":
            self._set_calls += 1
            if self._fail_config_set is not None and self._set_calls == self._fail_config_set:
                return subprocess.CompletedProcess(cmd, 1, "", "injected")
            if self._config_path and len(row) >= 6:
                key = row[4]
                value = _decode_config_set_value(row[5])
                _mutate_config_file(self._config_path, key, value)
            return subprocess.CompletedProcess(cmd, 0, '{"updated": true}', "")
        if len(row) >= 3 and row[0] == "node" and row[2] == "config-new-project":
            return subprocess.CompletedProcess(cmd, 0, "created", "")
        if len(row) >= 4 and row[0] == "node" and row[2] == "query" and row[3] == "agent-skills":
            return subprocess.CompletedProcess(cmd, 0, '{"warnings": []}', "")
        return self._base(cmd, **kw)



def _minimal_plan(host: str, inv: dict, entries: list, artifacts: list | None = None) -> dict:
    plan = {
        "schema_version": 2,
        "host": host,
        "profile": "adaptive",
        "rigor": "standard",
        "inventory_digest": plan_schema.inventory_digest(inv),
        "cross_ai": {"review": False, "execution": False},
        "skill_affinity": {},
        "entries": entries,
        "artifacts": artifacts or [],
        "notes": [],
    }
    problem = plan_io.validate_plan(plan)
    if problem:
        raise AssertionError(problem)
    return plan


def _config_set_keys(log: list[list[str]]) -> list[str]:
    keys: list[str] = []
    for row in log:
        if len(row) >= 5 and row[2] == "query" and row[3] == "config-set":
            keys.append(row[4])
    return keys


def _setup_reapply_change(
    tmp: str,
) -> tuple[str, dict, str, str, str, dict, FakeRun, str, bytes, int]:
    project, env, inv_path, plan_path, config_path, _inv, fake = _decided_plan(tmp)
    template, tmpl_err = cross_ai_script.load_template()
    if template is None:
        raise AssertionError(tmpl_err)
    plan, _ = plan_io.load_plan(plan_path)
    assert plan is not None
    art = copy.deepcopy(plan["artifacts"][0])
    rendered = cross_ai_script.render(
        template,
        cross_ai_script.runner_config(template, art, HOST_SIGNAL_ENV_VARS),
    )
    runner = os.path.join(project, ".planning", "scripts", "cross-ai.mjs")
    os.makedirs(os.path.dirname(runner), exist_ok=True)
    with open(runner, "wb") as handle:
        handle.write(rendered)
    os.chmod(runner, 0o755)
    before_bytes = rendered
    before_mode = stat.S_IMODE(os.stat(runner).st_mode)
    art2 = copy.deepcopy(art)
    art2["config"] = dict(art2["config"])
    models = dict(art2["config"]["models"])
    model_key = next(iter(models))
    models[model_key] = "openai/gpt-5-alt"
    art2["config"]["models"] = models
    plan["artifacts"] = [art2]
    with open(config_path, "w", encoding="utf-8") as handle:
        json.dump(
            {
                "model_profile": "balanced",
                "workflow": {"cross_ai_command": "node .planning/scripts/cross-ai.mjs"},
            },
            handle,
        )
    plan_io.write_plan(plan_path, plan)
    return (
        project,
        env,
        inv_path,
        plan_path,
        config_path,
        _inv,
        fake,
        runner,
        before_bytes,
        before_mode,
    )


class TestApplyWritePath(unittest.TestCase):
    def test_held_marker_refuses_with_recovery_text(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project, env, inv_path, plan_path, config_path, _inv, fake = _decided_plan(tmp)
            config_backup.acquire_marker(config_path, True, _fixed_now)
            config_backup.update_marker(config_path, backup="config.json.bak-20261015T120000Z")
            with open(config_path, "rb") as handle:
                before = handle.read()
            rec = _RecordingRun(fake)
            code, report = _write_apply(plan_path, inv_path, project, env, rec)
            self.assertEqual(code, 2)
            expected = config_backup.recovery_text(
                config_backup.read_marker(config_path), config_path
            )
            self.assertEqual(report["error"], expected)
            with open(config_path, "rb") as handle:
                self.assertEqual(handle.read(), before)

    def test_write_order_unset_before_set(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project, env, config_path = _setup_scratch_project(tmp)
            with open(config_path, "w", encoding="utf-8") as handle:
                json.dump(
                    {
                        "model_profile": "balanced",
                        "model_policy": {"provider": "cursor", "budget": "medium"},
                    },
                    handle,
                )
            fake = _tables_fake(config_path, env["HOME"])
            inv_path = os.path.join(tmp, "inventory.json")
            inv = scratch_inventory(project, env, fake, inv_path, host_name="codex")
            plan = _minimal_plan(
                "codex",
                inv,
                [
                    {"key": "model_policy.provider", "op": "unset", "source": "preset"},
                    {"key": "model_policy.budget", "op": "set", "value": "low", "source": "preset"},
                    {
                        "key": "models.planning",
                        "op": "set",
                        "value": "openai/gpt-5",
                        "source": "preset",
                    },
                ],
            )
            plan_path = os.path.join(tmp, "plan.json")
            plan_io.write_plan(plan_path, plan)
            rec = _RecordingRun(fake)
            code, report = _write_apply(plan_path, inv_path, project, env, rec)
            self.assertEqual((code, report["applied"]), (0, True))
            self.assertEqual(
                _config_set_keys(rec.argv_log),
                ["model_policy.provider", "model_policy.budget", "models.planning"],
            )

    def test_skips_equal_live_and_absent_unset(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project, env, config_path = _setup_scratch_project(tmp)
            fake = _tables_fake(config_path, env["HOME"])
            inv_path = os.path.join(tmp, "inventory.json")
            inv = scratch_inventory(project, env, fake, inv_path, host_name="codex")
            plan = _minimal_plan(
                "codex",
                inv,
                [
                    {
                        "key": "model_profile",
                        "op": "set",
                        "value": "balanced",
                        "source": "preset",
                    },
                    {"key": "models.planning", "op": "unset", "source": "preset"},
                    {"key": "models.research", "op": "keep", "existing": None},
                ],
            )
            plan_path = os.path.join(tmp, "plan.json")
            plan_io.write_plan(plan_path, plan)
            rec = _RecordingRun(fake)
            code, _report = _write_apply(plan_path, inv_path, project, env, rec)
            self.assertEqual(code, 0)
            self.assertEqual(_config_set_keys(rec.argv_log), [])

    def test_restore_on_second_config_set_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project, env, inv_path, plan_path, config_path, _inv, fake = _decided_plan(tmp)
            rec = _RecordingRun(fake, fail_config_set=2)
            real_restore = config_backup.restore_backup
            with mock.patch.object(
                config_backup, "restore_backup", wraps=real_restore
            ) as restore:
                code, report = _write_apply(plan_path, inv_path, project, env, rec)
            self.assertEqual(code, 1)
            keys = _config_set_keys(rec.argv_log)
            self.assertGreaterEqual(len(keys), 2)
            self.assertEqual(report["failed_key"], keys[1])
            runner = os.path.join(project, ".planning", "scripts", "cross-ai.mjs")
            self.assertFalse(os.path.exists(runner))
            self.assertIsNone(config_backup.read_marker(config_path))
            self.assertGreaterEqual(restore.call_count, 2)

    def test_backup_step_failure_leaves_config_untouched(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project, env, inv_path, plan_path, config_path, _inv, fake = _decided_plan(tmp)
            with open(config_path, "rb") as handle:
                before = handle.read()
            with mock.patch.object(
                config_backup, "create_backup", side_effect=OSError("disk full")
            ), mock.patch.object(config_backup, "restore_backup") as restore:
                code, report = _write_apply(plan_path, inv_path, project, env, fake)
            self.assertEqual(code, 1)
            self.assertIn("disk full", report["error"])
            restore.assert_not_called()
            with open(config_path, "rb") as handle:
                self.assertEqual(handle.read(), before)
            self.assertIsNone(config_backup.read_marker(config_path))

    def test_restore_failure_keeps_marker(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project, env, inv_path, plan_path, config_path, _inv, fake = _decided_plan(tmp)
            rec = _RecordingRun(fake, fail_config_set=2)
            real_restore = config_backup.restore_backup

            def boom(path, backup):
                if os.path.abspath(path) == os.path.abspath(config_path):
                    raise OSError("restore broke")
                real_restore(path, backup)

            with mock.patch.object(config_backup, "restore_backup", side_effect=boom):
                code, report = _write_apply(plan_path, inv_path, project, env, rec)
            self.assertEqual(code, 1)
            self.assertIn("restore broke", report["restore_error"])
            self.assertIsNotNone(config_backup.read_marker(config_path))
            code2, _report2 = _write_apply(plan_path, inv_path, project, env, rec)
            self.assertEqual(code2, 2)

    def test_pi_skips_agent_skills_probe(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project, env, config_path = _setup_scratch_project(tmp)
            fake = _tables_fake(config_path, env["HOME"])
            inv_path = os.path.join(tmp, "inventory.json")
            inv = scratch_inventory(project, env, fake, inv_path, host_name="pi")
            plan = _minimal_plan(
                "pi",
                inv,
                [{"key": "model_profile", "op": "set", "value": "quality", "source": "preset"}],
            )
            plan_path = os.path.join(tmp, "plan.json")
            plan_io.write_plan(plan_path, plan)
            rec = _RecordingRun(fake)
            code, report = _write_apply(plan_path, inv_path, project, env, rec)
            self.assertEqual(code, 0)
            self.assertIn("skipped", report["skill_check"])

    def test_forced_command_warning_in_apply_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project, env, inv_path, plan_path, _cfg, _inv, fake = _decided_plan(tmp)
            plan, _ = plan_io.load_plan(plan_path)
            assert plan is not None
            entry = next(
                e for e in plan["entries"] if e["key"] == "workflow.cross_ai_command"
            )
            entry["forced"] = True
            plan_io.write_plan(plan_path, plan)
            rec = _RecordingRun(fake)
            code, report = _write_apply(plan_path, inv_path, project, env, rec)
            self.assertEqual(code, 0)
            self.assertTrue(any("full permissions" in w for w in report["warnings"]))


    def test_absent_config_new_project_precedes_config_set(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project, env, config_path = _setup_scratch_project(tmp)
            fake = _tables_fake(config_path, env["HOME"])
            inv_path = os.path.join(tmp, "inv.json")
            inv = scratch_inventory(project, env, fake, inv_path, host_name="codex")
            planning = os.path.join(project, ".planning")
            shutil.rmtree(planning)
            plan = _minimal_plan(
                "codex",
                inv,
                [{"key": "model_profile", "op": "set", "value": "balanced", "source": "preset"}],
            )
            plan_path = os.path.join(tmp, "plan.json")
            plan_io.write_plan(plan_path, plan)
            rec = _RecordingRun(fake)
            code, report = _write_apply(plan_path, inv_path, project, env, rec)
            self.assertEqual(code, 0)
            joined = [" ".join(r) for r in rec.argv_log]
            new_idx = next(i for i, s in enumerate(joined) if "config-new-project" in s)
            set_idx = next(i for i, s in enumerate(joined) if "config-set" in s)
            self.assertLess(new_idx, set_idx)
            self.assertTrue(report["created_config"])

    def test_agent_skills_carries_gsd_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project, env, inv_path, plan_path, _config_path, _inv, fake = _decided_plan(tmp)
            rec = _RecordingRun(fake)
            code, _report = _write_apply(plan_path, inv_path, project, env, rec)
            self.assertEqual(code, 0)
            for row, call_env in zip(rec.argv_log, rec.env_log, strict=False):
                if len(row) >= 5 and row[3] == "agent-skills":
                    self.assertEqual(call_env.get("GSD_RUNTIME"), "codex")

    def test_clear_marker_failure_still_commits(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project, env, inv_path, plan_path, config_path, _inv, fake = _decided_plan(tmp)
            rec = _RecordingRun(fake)
            with mock.patch.object(config_backup, "clear_marker", side_effect=OSError("busy")):
                code, report = _write_apply(plan_path, inv_path, project, env, rec)
            self.assertEqual(code, 0)
            self.assertTrue(report["applied"])
            self.assertTrue(any("marker" in w for w in report["warnings"]))
            marker = config_backup.read_marker(config_path)
            self.assertTrue(marker and marker.get("committed"))
            code2, report2 = _write_apply(plan_path, inv_path, project, env, rec)
            self.assertEqual(code2, 2)
            self.assertIn("do not restore the backup", report2["error"])

    def test_reapply_runner_rollback_restores_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            (
                project,
                env,
                inv_path,
                plan_path,
                config_path,
                _inv,
                fake,
                runner,
                before_bytes,
                before_mode,
            ) = _setup_reapply_change(tmp)
            rec = _RecordingRun(fake, fail_config_set=1)
            code, _report = _write_apply(plan_path, inv_path, project, env, rec)
            self.assertEqual(code, 1)
            with open(runner, "rb") as handle:
                self.assertEqual(handle.read(), before_bytes)
            self.assertEqual(stat.S_IMODE(os.stat(runner).st_mode), before_mode)
            snap = runner + ".ai-kit-apply-backup"
            self.assertFalse(os.path.exists(snap))
            self.assertIsNone(config_backup.read_marker(config_path))

    def test_reapply_change_success_discards_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            (
                project,
                env,
                inv_path,
                plan_path,
                config_path,
                _inv,
                fake,
                runner,
                before_bytes,
                _before_mode,
            ) = _setup_reapply_change(tmp)
            rec = _RecordingRun(fake)
            code, report = _write_apply(plan_path, inv_path, project, env, rec)
            self.assertEqual((code, report["applied"]), (0, True))
            self.assertFalse(os.path.exists(runner + ".ai-kit-apply-backup"))
            with open(runner, "rb") as handle:
                self.assertNotEqual(handle.read(), before_bytes)
            self.assertIsNone(config_backup.read_marker(config_path))

    def test_edited_runner_writes_new_without_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project, env, inv_path, plan_path, config_path, _inv, fake = _decided_plan(tmp)
            template, tmpl_err = cross_ai_script.load_template()
            if template is None:
                raise AssertionError(tmpl_err)
            plan, _ = plan_io.load_plan(plan_path)
            assert plan is not None
            art = plan["artifacts"][0]
            rendered = cross_ai_script.render(
                template,
                cross_ai_script.runner_config(template, art, HOST_SIGNAL_ENV_VARS),
            )
            runner = os.path.join(project, ".planning", "scripts", "cross-ai.mjs")
            os.makedirs(os.path.dirname(runner), exist_ok=True)
            edited = rendered + b"\n"
            with open(runner, "wb") as handle:
                handle.write(edited)
            rec = _RecordingRun(fake)
            code, report = _write_apply(plan_path, inv_path, project, env, rec)
            self.assertEqual(code, 0)
            script = report["script"]
            assert script is not None
            self.assertEqual(script["kind"], "new-as-.new")
            self.assertFalse(script["active"])
            self.assertTrue(any("is not active" in w for w in report["warnings"]))
            with open(runner, "rb") as handle:
                self.assertEqual(handle.read(), edited)
            new_path = runner + ".new"
            self.assertTrue(os.path.isfile(new_path))
            with open(new_path, "rb") as handle:
                self.assertEqual(cross_ai_script.script_state(handle.read()), "pristine")
            self.assertIsNone(config_backup.read_marker(config_path))

    def test_edited_runner_failed_write_keeps_runner_and_new(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project, env, inv_path, plan_path, config_path, _inv, fake = _decided_plan(tmp)
            template, tmpl_err = cross_ai_script.load_template()
            if template is None:
                raise AssertionError(tmpl_err)
            plan, _ = plan_io.load_plan(plan_path)
            assert plan is not None
            art = plan["artifacts"][0]
            rendered = cross_ai_script.render(
                template,
                cross_ai_script.runner_config(template, art, HOST_SIGNAL_ENV_VARS),
            )
            runner = os.path.join(project, ".planning", "scripts", "cross-ai.mjs")
            os.makedirs(os.path.dirname(runner), exist_ok=True)
            edited = rendered + b"\n"
            with open(runner, "wb") as handle:
                handle.write(edited)
            rec = _RecordingRun(fake, fail_config_set=2)
            code, _report = _write_apply(plan_path, inv_path, project, env, rec)
            self.assertEqual(code, 1)
            with open(runner, "rb") as handle:
                self.assertEqual(handle.read(), edited)
            self.assertTrue(os.path.isfile(runner + ".new"))
            self.assertIsNone(config_backup.read_marker(config_path))

    def test_render_failure_before_config_set(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project, env, inv_path, plan_path, config_path, _inv, fake = _decided_plan(tmp)
            rec = _RecordingRun(fake)
            real_restore = config_backup.restore_backup
            with mock.patch.object(
                cross_ai_script, "plan_script", side_effect=ValueError("template missing")
            ), mock.patch.object(
                config_backup, "restore_backup", wraps=real_restore
            ) as restore:
                code, report = _write_apply(plan_path, inv_path, project, env, rec)
            self.assertEqual(code, 1)
            self.assertIn("template missing", report["error"])
            self.assertGreaterEqual(restore.call_count, 1)
            self.assertEqual(_config_set_keys(rec.argv_log), [])
            self.assertIsNone(config_backup.read_marker(config_path))

    def test_fresh_project_failed_write_removes_planning(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project, env, inv_path, plan_path, _config_path, _inv, fake = _decided_plan(tmp)
            planning = os.path.join(project, ".planning")
            shutil.rmtree(planning)
            rec = _RecordingRun(fake, fail_config_set=2)
            code, _report = _write_apply(plan_path, inv_path, project, env, rec)
            self.assertEqual(code, 1)
            self.assertFalse(os.path.exists(planning))
            joined = [" ".join(r) for r in rec.argv_log]
            new_idx = next(i for i, s in enumerate(joined) if "config-new-project" in s)
            set_indices = [i for i, s in enumerate(joined) if "config-set" in s]
            self.assertTrue(set_indices)
            self.assertLess(new_idx, min(set_indices))

    def test_prune_failure_after_commit_still_exits_zero(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project, env, inv_path, plan_path, config_path, _inv, fake = _decided_plan(tmp)
            rec = _RecordingRun(fake)
            with mock.patch.object(
                config_backup, "prune_backups", side_effect=OSError("prune fail")
            ), mock.patch.object(config_backup, "restore_backup") as restore:
                code, report = _write_apply(plan_path, inv_path, project, env, rec)
            self.assertEqual(code, 0)
            self.assertTrue(report["applied"])
            self.assertTrue(any("prune" in w for w in report["warnings"]))
            restore.assert_not_called()
            self.assertIsNone(config_backup.read_marker(config_path))

    def test_discard_snapshot_failure_after_commit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            (
                project,
                env,
                inv_path,
                plan_path,
                config_path,
                _inv,
                fake,
                runner,
                before_bytes,
                _before_mode,
            ) = _setup_reapply_change(tmp)
            rec = _RecordingRun(fake)
            with mock.patch.object(
                config_backup, "discard_snapshot", side_effect=OSError("snap fail")
            ), mock.patch.object(config_backup, "restore_backup") as restore:
                code, report = _write_apply(plan_path, inv_path, project, env, rec)
            self.assertEqual(code, 0)
            self.assertTrue(report["applied"])
            self.assertTrue(any("snapshot" in w for w in report["warnings"]))
            restore.assert_not_called()
            with open(runner, "rb") as handle:
                self.assertNotEqual(handle.read(), before_bytes)
            self.assertIsNone(config_backup.read_marker(config_path))



class _AgentSkillsFailRun(_RecordingRun):
    def __call__(self, cmd, **kw):
        row = [str(part) for part in cmd]
        if len(row) >= 4 and row[0] == "node" and row[3] == "agent-skills":
            return subprocess.CompletedProcess(cmd, 1, "", "skills probe failed")
        return super().__call__(cmd, **kw)


class _NewProjectRun(_RecordingRun):
    """config-new-project writes a config holding a copied global key, then may raise."""

    def __init__(self, base: FakeRun, config_path: str, *, raise_exc=None):
        super().__init__(base, config_path=config_path)
        self._raise = raise_exc

    def __call__(self, cmd, **kw):
        row = [str(part) for part in cmd]
        if len(row) >= 3 and row[0] == "node" and row[2] == "config-new-project":
            self.argv_log.append(row)
            assert self._config_path is not None
            os.makedirs(os.path.dirname(self._config_path), exist_ok=True)
            with open(self._config_path, "w", encoding="utf-8") as handle:
                json.dump({"model_profile": "balanced", "resolve_model_ids": "omit"}, handle)
            if self._raise is not None:
                raise self._raise
            return subprocess.CompletedProcess(cmd, 0, "created", "")
        return super().__call__(cmd, **kw)


class TestPreCommitExceptions(unittest.TestCase):
    """B CR-01: a raised failure before the commit point rolls back like a returned one."""

    def _assert_fresh_rolled_back(self, project: str, config_path: str) -> None:
        self.assertFalse(os.path.exists(config_path))
        self.assertIsNone(config_backup.read_marker(config_path))
        self.assertFalse(os.path.exists(os.path.join(project, ".planning")))

    def test_new_project_timeout_rolls_back(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project, env, inv_path, plan_path, config_path, _inv, fake = _decided_plan(tmp)
            shutil.rmtree(os.path.join(project, ".planning"))
            rec = _NewProjectRun(
                fake, config_path, raise_exc=subprocess.TimeoutExpired("node", 120)
            )
            code, report = _write_apply(plan_path, inv_path, project, env, rec)
            self.assertEqual(code, 1)
            self.assertFalse(report["applied"])
            self.assertIn("timed out", report["error"])
            self.assertIsNone(report["restore_error"])
            self.assertEqual(_config_set_keys(rec.argv_log), [])
            self._assert_fresh_rolled_back(project, config_path)

    def test_runner_marker_oserror_on_fresh_project_rolls_back(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project, env, inv_path, plan_path, config_path, _inv, fake = _decided_plan(tmp)
            shutil.rmtree(os.path.join(project, ".planning"))
            rec = _NewProjectRun(fake, config_path)
            real_update = config_backup.update_marker

            def fail_runner(path, **fields):
                if "runner" in fields:
                    raise OSError("marker disk full")
                return real_update(path, **fields)

            with mock.patch.object(config_backup, "update_marker", side_effect=fail_runner):
                code, report = _write_apply(plan_path, inv_path, project, env, rec)
            self.assertEqual(code, 1)
            self.assertIn("marker disk full", report["error"])
            self.assertEqual(_config_set_keys(rec.argv_log), [])
            self._assert_fresh_rolled_back(project, config_path)

    def test_snapshot_oserror_restores_existing_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            (
                project,
                env,
                inv_path,
                plan_path,
                config_path,
                _inv,
                fake,
                runner,
                before_bytes,
                _before_mode,
            ) = _setup_reapply_change(tmp)
            with open(config_path, "rb") as handle:
                before_config = handle.read()
            rec = _RecordingRun(fake, config_path=config_path)
            with mock.patch.object(
                config_backup, "snapshot_file", side_effect=OSError("snapshot denied")
            ):
                code, report = _write_apply(plan_path, inv_path, project, env, rec)
            self.assertEqual(code, 1)
            self.assertIn("snapshot denied", report["error"])
            with open(config_path, "rb") as handle:
                self.assertEqual(handle.read(), before_config)
            with open(runner, "rb") as handle:
                self.assertEqual(handle.read(), before_bytes)
            self.assertIsNone(config_backup.read_marker(config_path))
            self.assertEqual(_config_set_keys(rec.argv_log), [])

    def test_cli_prints_json_report_not_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project, env, inv_path, plan_path, config_path, _inv, fake = _decided_plan(tmp)
            shutil.rmtree(os.path.join(project, ".planning"))
            rec = _NewProjectRun(fake, config_path, raise_exc=OSError("node vanished"))
            code, parsed, _out, err = _run_apply(
                plan_path, inv_path, project, env, rec, dry_run=False
            )
            self.assertEqual(code, 1)
            assert parsed is not None
            self.assertFalse(parsed["applied"])
            self.assertIn("node vanished", parsed["error"])
            self.assertIn("node vanished", err)
            self._assert_fresh_rolled_back(project, config_path)


class _AgentSkillsTimeoutRun(_RecordingRun):
    def __call__(self, cmd, **kw):
        row = [str(part) for part in cmd]
        if len(row) >= 4 and row[0] == "node" and row[3] == "agent-skills":
            raise subprocess.TimeoutExpired(cmd, 120)
        return super().__call__(cmd, **kw)


class TestPostCommitNeverRaises(unittest.TestCase):
    """B WR-01: after the commit point the skill check and follow-ups only warn."""

    def test_skill_check_timeout_still_cleans_up(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            (
                project,
                env,
                inv_path,
                plan_path,
                config_path,
                _inv,
                fake,
                runner,
                _before_bytes,
                _before_mode,
            ) = _setup_reapply_change(tmp)
            rec = _AgentSkillsTimeoutRun(fake, config_path=config_path)
            code, report = _write_apply(plan_path, inv_path, project, env, rec)
            self.assertEqual(code, 0)
            self.assertTrue(report["applied"])
            rows = [r for k, r in report["skill_check"].items() if k != "skipped"]
            self.assertTrue(rows)
            for row in rows:
                self.assertIn("timed out", row["error"])
            self.assertIsNone(config_backup.read_marker(config_path))
            self.assertFalse(os.path.isfile(runner + config_backup.SNAPSHOT_SUFFIX))

    def test_skill_check_non_object_json_is_an_error_row(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project, env, inv_path, plan_path, _config_path, _inv, fake = _decided_plan(tmp)

            class ListRun(_RecordingRun):
                def __call__(self, cmd, **kw):
                    row = [str(part) for part in cmd]
                    if len(row) >= 4 and row[0] == "node" and row[3] == "agent-skills":
                        return subprocess.CompletedProcess(cmd, 0, "[1]", "")
                    return super().__call__(cmd, **kw)

            code, report = _write_apply(plan_path, inv_path, project, env, ListRun(fake))
            self.assertEqual(code, 0)
            rows = [r for k, r in report["skill_check"].items() if k != "skipped"]
            self.assertTrue(rows)
            for row in rows:
                self.assertIn("not an object", row["error"])

    def test_unexpected_post_commit_errors_only_warn(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project, env, inv_path, plan_path, config_path, _inv, fake = _decided_plan(tmp)
            rec = _RecordingRun(fake)
            with mock.patch.object(
                apply_mod, "verify_skills", side_effect=RuntimeError("probe exploded")
            ), mock.patch.object(
                apply_mod.followups, "build_followups", side_effect=RuntimeError("npx gone")
            ):
                code, report = _write_apply(plan_path, inv_path, project, env, rec)
            self.assertEqual(code, 0)
            self.assertTrue(report["applied"])
            self.assertTrue(any("probe exploded" in w for w in report["warnings"]))
            self.assertTrue(any("npx gone" in w for w in report["warnings"]))
            self.assertIsNone(config_backup.read_marker(config_path))


class TestCommitPointEdges(unittest.TestCase):
    def test_agent_skills_failure_still_commits(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project, env, inv_path, plan_path, config_path, _inv, fake = _decided_plan(tmp)
            rec = _AgentSkillsFailRun(fake)
            real_restore = config_backup.restore_backup
            with mock.patch.object(
                config_backup, "restore_backup", wraps=real_restore
            ) as restore:
                code, report = _write_apply(plan_path, inv_path, project, env, rec)
            self.assertEqual(code, 0)
            self.assertTrue(report["applied"])
            for key, row in report["skill_check"].items():
                if key == "skipped":
                    continue
                self.assertIn("error", row)
            restore.assert_not_called()
            self.assertIsNone(config_backup.read_marker(config_path))

    def test_commit_record_failure_clears_marker_and_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            (
                project,
                env,
                inv_path,
                plan_path,
                config_path,
                _inv,
                fake,
                runner,
                _before_bytes,
                _before_mode,
            ) = _setup_reapply_change(tmp)
            rec = _RecordingRun(fake, config_path=config_path)
            real_update = config_backup.update_marker

            def fail_committed(path, **fields):
                if fields.get("committed") is True:
                    raise OSError("marker busy")
                return real_update(path, **fields)

            with mock.patch.object(
                config_backup, "update_marker", side_effect=fail_committed
            ), mock.patch.object(config_backup, "restore_backup") as restore:
                code, report = _write_apply(plan_path, inv_path, project, env, rec)
            self.assertEqual(code, 0)
            self.assertTrue(any("committed" in w for w in report["warnings"]))
            restore.assert_not_called()
            self.assertIsNone(config_backup.read_marker(config_path))
            snap = runner + config_backup.SNAPSHOT_SUFFIX
            self.assertFalse(os.path.isfile(snap))

    def test_commit_and_clear_failure_leaves_marker_and_recovery(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            (
                project,
                env,
                inv_path,
                plan_path,
                config_path,
                _inv,
                fake,
                runner,
                _before_bytes,
                _before_mode,
            ) = _setup_reapply_change(tmp)
            rec = _RecordingRun(fake, config_path=config_path)
            real_update = config_backup.update_marker

            def fail_committed(path, **fields):
                if fields.get("committed") is True:
                    raise OSError("marker busy")
                return real_update(path, **fields)

            with mock.patch.object(
                config_backup, "update_marker", side_effect=fail_committed
            ), mock.patch.object(
                config_backup, "clear_marker", side_effect=OSError("clear busy")
            ), mock.patch.object(
                config_backup, "discard_snapshot"
            ) as discard, mock.patch.object(
                config_backup, "prune_backups"
            ) as prune:
                code, report = _write_apply(plan_path, inv_path, project, env, rec)
            self.assertEqual(code, 0)
            self.assertTrue(any("do not restore the backup" in w for w in report["warnings"]))
            discard.assert_not_called()
            prune.assert_not_called()
            self.assertIsNotNone(config_backup.read_marker(config_path))
            snap = runner + config_backup.SNAPSHOT_SUFFIX
            self.assertTrue(os.path.isfile(snap))
            code2, report2 = _write_apply(plan_path, inv_path, project, env, rec)
            self.assertEqual(code2, 2)
            err = report2["error"]
            self.assertIn("apply --dry-run", err)
            self.assertIn(snap, err)
            self.assertIn("restore nothing", err)
            code3, report3, _, _ = _run_apply(
                plan_path, inv_path, project, env, fake, dry_run=True
            )
            self.assertEqual(code3, 0)
            assert report3 is not None
            self.assertTrue(all(row["kind"] == "keep" for row in report3["diff"]))
            marker_path = config_backup.marker_path(config_path)
            with open(marker_path, "rb") as handle:
                before_marker = handle.read()
            code4, _report4, _, _ = _run_apply(
                plan_path, inv_path, project, env, fake, dry_run=True
            )
            self.assertEqual(code4, 0)
            with open(marker_path, "rb") as handle:
                after_marker = handle.read()
            self.assertEqual(before_marker, after_marker)

    def test_marker_acquire_oserror_leaves_no_planning(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project, env, inv_path, plan_path, _config_path, _inv, fake = _decided_plan(tmp)
            planning = os.path.join(project, ".planning")
            shutil.rmtree(planning)
            rec = _RecordingRun(fake)

            def link_fail(_src, _dst):
                raise OSError(errno.EPERM, "link denied")

            with mock.patch.object(os, "link", side_effect=link_fail):
                code, report = _write_apply(plan_path, inv_path, project, env, rec)
            self.assertEqual(code, 1)
            self.assertIn("link denied", report["error"])
            self.assertFalse(os.path.exists(planning))
            joined = [" ".join(row) for row in rec.argv_log]
            self.assertFalse(any("config-new-project" in row for row in joined))
            self.assertFalse(any("config-set" in row for row in joined))



def _apply_write_path_findings(tree: ast.AST) -> list[str]:
    findings: list[str] = []

    def mode_has_write(node: ast.Call) -> bool:
        if len(node.args) < 2:
            return False
        mode = node.args[1]
        if isinstance(mode, ast.Constant) and isinstance(mode.value, str):
            return any(ch in mode.value for ch in "wax")
        return False

    class Visitor(ast.NodeVisitor):
        def __init__(self):
            self.func_stack: list[str] = []

        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            self.func_stack.append(node.name)
            self.generic_visit(node)
            self.func_stack.pop()

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
            self.func_stack.append(node.name)
            self.generic_visit(node)
            self.func_stack.pop()

        def visit_Call(self, node: ast.Call) -> None:
            func = node.func
            if isinstance(func, ast.Name) and func.id == "open" and mode_has_write(node):
                findings.append(f"open write at line {node.lineno}")
            if (
                isinstance(func, ast.Name)
                and func.id == "restore_backup"
                and (not self.func_stack or self.func_stack[-1] != "_rollback")
            ):
                findings.append(
                    f"restore_backup outside _rollback at line {node.lineno}"
                )
            if isinstance(func, ast.Attribute):
                base = func.value
                if isinstance(base, ast.Name):
                    if base.id == "os" and func.attr in ("replace", "rename"):
                        findings.append(f"os.{func.attr} at line {node.lineno}")
                    if base.id == "shutil" and func.attr.startswith("copy"):
                        findings.append(f"shutil.{func.attr} at line {node.lineno}")
                if func.attr in ("cache_write_text", "cache_write_bytes"):
                    findings.append(f"{func.attr} at line {node.lineno}")
                if func.attr == "restore_backup" and (
                    not self.func_stack or self.func_stack[-1] != "_rollback"
                ):
                    findings.append(
                        f"restore_backup outside _rollback at line {node.lineno}"
                    )
            self.generic_visit(node)

    Visitor().visit(tree)
    return findings


_V2_SUBCOMMANDS = frozenset(
    {"inventory", "recommend", "plan-set", "plan-unset", "apply", "followups"}
)
_SKILL_MD = os.path.join(
    os.path.dirname(__file__),
    "..",
    "skills",
    "ai-kit-gsd-curated-config",
    "SKILL.md",
)
_SCRIPT_NAME = "ai-kit-gsd-curated-config.py"


def _skill_md_text() -> str:
    with open(_SKILL_MD, encoding="utf-8") as handle:
        return handle.read()


def _bash_fenced_lines(text: str) -> list[str]:
    lines: list[str] = []
    in_bash = False
    for raw in text.splitlines():
        stripped = raw.strip()
        if stripped.startswith("```"):
            if stripped == "```bash":
                in_bash = True
                continue
            in_bash = False
            continue
        if in_bash and _SCRIPT_NAME in raw and "python3" in raw:
            lines.append(raw.strip())
    return lines


def _argv_after_script(command_line: str) -> list[str]:
    replaced = re.sub(r"<[^>]+>", "x", command_line)
    parts = shlex.split(replaced)
    for idx, token in enumerate(parts):
        if token.endswith(_SCRIPT_NAME):
            return parts[idx + 1 :]
    raise AssertionError(f"no script name in command line: {command_line!r}")


class TestSkillDocCommands(unittest.TestCase):
    def test_documented_commands_parse(self) -> None:
        parser = cli._build_parser()
        seen_v2: set[str] = set()
        for line in _bash_fenced_lines(_skill_md_text()):
            argv = _argv_after_script(line)
            self.assertTrue(argv, line)
            args = parser.parse_args(argv)
            cmd = args.command
            if cmd in _V2_SUBCOMMANDS:
                seen_v2.add(cmd)
        self.assertEqual(seen_v2, _V2_SUBCOMMANDS)

    def test_v2_is_primary(self) -> None:
        headings = re.findall(r"^## (.+)$", _skill_md_text(), re.MULTILINE)
        flow_idx = next(i for i, title in enumerate(headings) if "flow" in title.lower())
        v1_idx = next(i for i, title in enumerate(headings) if "v1" in title.lower())
        self.assertLess(flow_idx, v1_idx)
        self.assertIn("v2", headings[flow_idx].lower())

    def test_required_statements(self) -> None:
        text = _skill_md_text()
        required = (
            "not live-validated",
            "trusted checkouts",
            "opencode.json",
            ".claude/skills",
            "GSD_WORKSTREAM",
            "GSD_PATH_JEV=1",
            "AIKIT-XAI",
            "full permissions",
            "2026-10-15",
            ".opencode/gsd-core",
            "enabledPlugins",
            "unverified",
            "declined",
            "extraArgs",
            ".new",
            "not active",
            "--print-argv",
            "ai-kit-apply-marker",
            "approve_with",
            "--require",
            "committed",
        )
        missing = [phrase for phrase in required if phrase not in text]
        self.assertEqual(missing, [])




class TestWritePathDiscipline(unittest.TestCase):
    def test_apply_has_no_direct_write(self) -> None:
        repo = os.path.join(os.path.dirname(__file__), "..")
        path = os.path.join(
            repo,
            "skills",
            "ai-kit-gsd-curated-config",
            "ai_kit_gsd_curated_config",
            "apply.py",
        )
        with open(path, encoding="utf-8") as handle:
            tree = ast.parse(handle.read(), filename=path)
        self.assertEqual(_apply_write_path_findings(tree), [])

    def test_scan_flags_a_direct_write(self) -> None:
        cases = {
            "open": 'def o():\n    open(p, "w")\n',
            "os.replace": "def o():\n    os.replace(a, b)\n",
            "os.rename": "def o():\n    os.rename(a, b)\n",
            "shutil.copyfile": "def o():\n    shutil.copyfile(a, b)\n",
            "cache_write_bytes": "def o():\n    x.cache_write_bytes(p, b)\n",
            "cache_write_text": "def o():\n    x.cache_write_text(p, s)\n",
            "restore_backup_outside": "def other():\n    restore_backup(c, b)\n",
        }
        for name, src in cases.items():
            with self.subTest(rule=name):
                tree = ast.parse(src)
                hits = _apply_write_path_findings(tree)
                self.assertEqual(len(hits), 1, hits)
        allowed = ast.parse("def _rollback():\n    restore_backup(c, b)\n")
        self.assertEqual(_apply_write_path_findings(allowed), [])


if __name__ == "__main__":
    unittest.main()

