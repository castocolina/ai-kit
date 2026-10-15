"""Apply dry-run, backup/marker unit tests (plans 18-16, 18-17)."""
import contextlib
import io
import json
import os
import stat
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

from ai_kit_gsd_curated_config import cli, config_backup, plan_io

from tests.test_curated_config_golden import load_fixture, tables_answer
from tests.test_curated_config_inventory import (
    FakeRun,
    _tree_snapshot,
    make_gsd_install,
    run_inventory,
    seed_cache,
)
from tests.test_curated_config_plan_edit import _run_plan_set
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
            self.assertIn("put config.json.bak-20261015T120000Z back over", text)
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
    fake: FakeRun,
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


if __name__ == "__main__":
    unittest.main()

