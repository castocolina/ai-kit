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


if __name__ == "__main__":
    unittest.main()

