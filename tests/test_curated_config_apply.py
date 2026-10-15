"""Apply pipeline backup, marker and restore unit tests (plan 18-16)."""
import os
import stat
import sys
import tempfile
import unittest
from datetime import UTC, datetime

sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "skills", "ai-kit-gsd-curated-config"),
)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills", "ai-kit-spec-review"))

from ai_kit_gsd_curated_config import config_backup

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


if __name__ == "__main__":
    unittest.main()

