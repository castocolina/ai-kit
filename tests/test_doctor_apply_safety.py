"""Guarded doctor apply: refusal of unparseable files, backup, prune, dry run (30.1 R6, D-08, D-09).

Every test builds its own scratch HOME under a TemporaryDirectory; nothing reads the real
~/.claude, ~/.cursor, ~/.config/opencode, ~/.codex, ~/.pi or ~/.gsd.
"""

import datetime
import json
import os
import shutil
import sys
import tempfile
import time
import unittest
from unittest import mock

_HERE = os.path.dirname(os.path.abspath(__file__))
_TOOLS_DIR = os.path.join(os.path.dirname(_HERE), "tools")
if _TOOLS_DIR not in sys.path:
    sys.path.insert(0, _TOOLS_DIR)

import config_doctor_appliers as appliers
import config_doctor_checks as checks

UTC = datetime.UTC


class _Scratch(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="ai-kit-p301-")
        self.addCleanup(shutil.rmtree, self.root, True)
        self.home = os.path.join(self.root, "home")
        os.makedirs(os.path.join(self.home, ".claude"))
        self.env = {"HOME": self.home}
        self.settings = os.path.join(self.home, ".claude", "settings.json")
        self.backups = appliers.backups_root(self.env)
        self.claude_backups = os.path.join(self.backups, "claude")

    def write(self, text):
        with open(self.settings, "w", encoding="utf-8") as handle:
            handle.write(text)

    def read(self):
        with open(self.settings, "rb") as handle:
            return handle.read()

    def ctx(self):
        return checks.ReadContext(data=None, env=self.env, runner=None)

    def backup_names(self, folder):
        return sorted(os.listdir(folder)) if os.path.isdir(folder) else []


class TestBackupHelper(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="ai-kit-p301-")
        self.addCleanup(shutil.rmtree, self.root, True)
        self.backups_dir = os.path.join(self.root, "backups")
        self.target = os.path.join(self.root, "settings.json")
        with open(self.target, "w", encoding="utf-8") as handle:
            handle.write('{"a": 1}\n')
        self.folder = os.path.join(self.backups_dir, "claude")

    def test_missing_path_needs_no_backup(self):
        missing = os.path.join(self.root, "absent.json")
        self.assertEqual(appliers.backup_before_write(missing, self.backups_dir, "claude"), "")
        self.assertFalse(os.path.exists(self.backups_dir))

    def test_relative_backups_dir_raises(self):
        with self.assertRaises(OSError):
            appliers.backup_before_write(self.target, "relative/backups", "claude")

    def test_same_fixed_now_gives_two_distinct_paths(self):
        now = datetime.datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)
        first = appliers.backup_before_write(self.target, self.backups_dir, "claude", now=now)
        second = appliers.backup_before_write(self.target, self.backups_dir, "claude", now=now)
        self.assertNotEqual(first, second)
        self.assertTrue(second.endswith("-1.bak"), second)
        self.assertTrue(os.path.isfile(first) and os.path.isfile(second))

    def test_prune_keeps_new_backup_by_path_and_leaves_other_files(self):
        os.makedirs(self.folder)
        base = time.time()
        for i in range(12):
            name = f"settings.json.20260101T{100000 + i:06d}000000Z.bak"
            path = os.path.join(self.folder, name)
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(str(i))
            # Newer mtimes than the new backup: only the exclude rule keeps it.
            os.utime(path, (base + 100 + i, base + 100 + i))
        for name in ("other.json.20260101T100000000000Z.bak", "notes.txt"):
            with open(os.path.join(self.folder, name), "w", encoding="utf-8") as handle:
                handle.write("keep")
        earlier = datetime.datetime(2025, 1, 1, tzinfo=UTC)
        new_path = appliers.backup_before_write(
            self.target, self.backups_dir, "claude", now=earlier
        )
        names = sorted(os.listdir(self.folder))
        settings_backups = [n for n in names if n.startswith("settings.json.")]
        self.assertEqual(len(settings_backups), 10)
        self.assertIn(os.path.basename(new_path), settings_backups)
        self.assertIn("other.json.20260101T100000000000Z.bak", names)
        self.assertIn("notes.txt", names)

    def test_backup_is_byte_identical(self):
        with open(self.target, "rb") as handle:
            before = handle.read()
        path = appliers.backup_before_write(self.target, self.backups_dir, "claude")
        with open(path, "rb") as handle:
            self.assertEqual(handle.read(), before)
        self.assertEqual(os.stat(path).st_mode & 0o777, 0o600)


class TestGuardedApply(_Scratch):
    def test_refused_targets_stay_byte_identical_with_no_backup(self):
        for text in ("{not json", "", "[1, 2]"):
            with self.subTest(text=text):
                self.write(text)
                before = self.read()
                result = checks.apply_row("claude-retention", self.ctx(), dry=False)
                self.assertFalse(result["ok"])
                self.assertTrue(result["reason"].startswith("refused:"), result["reason"])
                self.assertIn(self.settings, result["reason"])
                self.assertEqual(self.read(), before)
                self.assertEqual(self.backup_names(self.claude_backups), [])

    def test_valid_target_is_backed_up_then_written(self):
        self.write('{"cleanupPeriodDays": 5, "theme": "dark"}')
        before = self.read()
        result = checks.apply_row("claude-retention", self.ctx(), dry=False)
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["before"], 5)
        self.assertEqual(result["after"], 3650)
        backup = result["backup"]
        self.assertTrue(backup.startswith(self.claude_backups + os.sep), backup)
        self.assertTrue(os.path.basename(backup).startswith("settings.json."))
        with open(backup, "rb") as handle:
            self.assertEqual(handle.read(), before)
        with open(self.settings, encoding="utf-8") as handle:
            data = json.load(handle)
        self.assertEqual(data["cleanupPeriodDays"], 3650)
        self.assertEqual(data["theme"], "dark")

    def test_dry_run_writes_neither_backup_nor_target(self):
        self.write('{"cleanupPeriodDays": 5}')
        before = self.read()
        result = checks.apply_row("claude-retention", self.ctx(), dry=True)
        self.assertTrue(result["ok"])
        self.assertNotIn("backup", result)
        self.assertEqual(self.read(), before)
        self.assertFalse(os.path.isdir(self.claude_backups))

    def test_absent_file_is_created_without_backup(self):
        result = checks.apply_row("claude-retention", self.ctx(), dry=False)
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["backup"], "")
        with open(self.settings, encoding="utf-8") as handle:
            self.assertEqual(json.load(handle), {"cleanupPeriodDays": 3650})

    def test_two_applies_make_two_backups_second_holds_first_result(self):
        self.write('{"cleanupPeriodDays": 5}')
        checks.apply_row("claude-retention", self.ctx(), dry=False)
        after_first = self.read()
        second = checks.apply_row("claude-retention", self.ctx(), dry=False)
        self.assertEqual(len(self.backup_names(self.claude_backups)), 2)
        with open(second["backup"], "rb") as handle:
            self.assertEqual(handle.read(), after_first)


BAD_TEXT = {"claude": "{not json", "opencode": '{ "share": ', "codex": "[[["}
GOOD_TEXT = {
    "claude": '{"theme": "dark"}\n',
    "opencode": '{ "theme": "dark" }\n',
    "codex": 'model = "x"\n',
}
# Phase 30's codegraph sentence applier keeps its own backup under backups/global-rules/ (R11).
EXEMPT_APPLIERS = {"codegraph-global-sentence"}


class TestEveryApplierRefusesAndBacksUp(_Scratch):
    def test_exempt_set_names_a_real_row(self):
        row_ids = {row.id for row in checks.CONFIG_DOCTOR_ROWS}
        self.assertTrue(row_ids >= EXEMPT_APPLIERS, "Phase 30 row renamed or removed")

    def test_every_applier_refuses_unparseable_and_backs_up_valid(self):
        appliers_rows = [
            row
            for row in checks.CONFIG_DOCTOR_ROWS
            if row.apply is not None and row.id not in EXEMPT_APPLIERS
        ]
        self.assertGreaterEqual(len(appliers_rows), 4)
        paths = checks.resolve_runtime_config_paths(self.env)
        for row in appliers_rows:
            with self.subTest(row=row.id):
                path = paths[row.runtime]
                os.makedirs(os.path.dirname(path), exist_ok=True)
                shutil.rmtree(self.backups, ignore_errors=True)
                self._check_refusal(row, path)
                if row.apply_when is None:
                    self._check_backup_and_dry(row, path)

    def _check_refusal(self, row, path):
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(BAD_TEXT[row.runtime])
        before = _bytes(path)
        result = checks.apply_row(row.id, self.ctx(), dry=False)
        self.assertFalse(result["ok"], result)
        self.assertTrue(result["reason"].startswith("refused:"), result["reason"])
        self.assertEqual(_bytes(path), before)
        self.assertFalse(os.path.isdir(os.path.join(self.backups, row.runtime)))

    def _check_backup_and_dry(self, row, path):
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(GOOD_TEXT[row.runtime])
        before = _bytes(path)
        dry = checks.apply_row(row.id, self.ctx(), dry=True)
        self.assertTrue(dry["ok"], dry)
        self.assertNotIn("backup", dry)
        self.assertEqual(_bytes(path), before)
        self.assertFalse(os.path.isdir(os.path.join(self.backups, row.runtime)))
        result = checks.apply_row(row.id, self.ctx(), dry=False)
        self.assertTrue(result["ok"], result)
        with open(result["backup"], "rb") as handle:
            self.assertEqual(handle.read(), before)
        self.assertTrue(result["backup"].startswith(os.path.join(self.backups, row.runtime)))


def _bytes(path):
    with open(path, "rb") as handle:
        return handle.read()


class TestApplyEdges(_Scratch):
    def test_utf8_target_backed_up_byte_identically_and_value_kept(self):
        self.write('{"cleanupPeriodDays": 5, "note": "café ✓"}')
        before = self.read()
        result = checks.apply_row("claude-retention", self.ctx(), dry=False)
        self.assertTrue(result["ok"], result)
        with open(result["backup"], "rb") as handle:
            self.assertEqual(handle.read(), before)
        with open(self.settings, encoding="utf-8") as handle:
            self.assertEqual(json.load(handle)["note"], "café ✓")

    def test_target_changed_before_replace_is_refused_and_backup_kept(self):
        self.write('{"cleanupPeriodDays": 5}')
        hook_bytes = b'{"cleanupPeriodDays": 7, "hook": true}'

        def hook():
            with open(self.settings, "wb") as handle:
                handle.write(hook_bytes)

        def compute(_text, parsed):
            data = dict(parsed)
            data["cleanupPeriodDays"] = 3650
            return data, {"ok": True}

        result = appliers.apply_guarded(
            self.settings,
            compute,
            False,
            parse=json.loads,
            kind="a JSON object",
            write=appliers.atomic_write_json,
            backups_dir=self.backups,
            label="claude",
            before_replace=hook,
        )
        self.assertFalse(result["ok"])
        self.assertIn("changed since it was read", result["reason"])
        self.assertEqual(self.read(), hook_bytes)
        self.assertEqual(len(self.backup_names(self.claude_backups)), 1)

    def test_backup_failure_aborts_before_write(self):
        self.write('{"cleanupPeriodDays": 5}')
        before = self.read()
        blocker = os.path.join(self.root, "blocker")
        with open(blocker, "w", encoding="utf-8") as handle:
            handle.write("not a folder")
        writes = []
        result = appliers.apply_guarded(
            self.settings,
            lambda _t, parsed: (dict(parsed), {"ok": True}),
            False,
            parse=json.loads,
            kind="a JSON object",
            write=lambda path, data: writes.append(path),
            backups_dir=os.path.join(blocker, "backups"),
            label="claude",
        )
        self.assertFalse(result["ok"])
        self.assertTrue(result["reason"].startswith("refused: backup failed"), result["reason"])
        self.assertEqual(writes, [])
        self.assertEqual(self.read(), before)

    def test_write_failure_keeps_target_and_backup(self):
        self.write('{"cleanupPeriodDays": 5}')
        before = self.read()

        def failing_write(_path, _data):
            raise OSError("disk full")

        result = appliers.apply_guarded(
            self.settings,
            lambda _t, parsed: (dict(parsed), {"ok": True}),
            False,
            parse=json.loads,
            kind="a JSON object",
            write=failing_write,
            backups_dir=self.backups,
            label="claude",
        )
        self.assertFalse(result["ok"])
        self.assertTrue(result["reason"].startswith("refused: write failed"), result["reason"])
        self.assertEqual(self.read(), before)
        backups = self.backup_names(self.claude_backups)
        self.assertEqual(len(backups), 1)
        self.assertIn("backup kept at", result["reason"])


ROW_ID = "claude-playwright-mcp-browser"


def _make_executable(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("#!/bin/sh\n")
    os.chmod(path, 0o755)


def _tree(root, skip):
    """Bytes of every file under root, skipping paths that start with `skip`."""
    out = {}
    for dirpath, _dirs, files in os.walk(root):
        for name in files:
            full = os.path.join(dirpath, name)
            if not full.startswith(skip):
                out[full] = _bytes(full)
    return out


class TestPlaywrightRow(_Scratch):
    def setUp(self):
        super().setUp()
        self.default_chrome = os.path.join(self.root, "opt", "google", "chrome")
        self.wrapper = os.path.join(self.root, "flatpak dir", "com.google.Chrome")
        _make_executable(self.wrapper)
        for name, value in (
            ("PLAYWRIGHT_DEFAULT_CHROME", self.default_chrome),
            ("PLAYWRIGHT_FLATPAK_CHROME", self.wrapper),
        ):
            patcher = mock.patch.object(checks, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def set_settings(self, data):
        self.write(json.dumps(data))

    def find_row(self):
        with mock.patch.object(checks.shutil, "which", return_value=None):
            catalog = checks.build_catalog(self.env, runner=None)
        for section in catalog["sections"]:
            for row in section["rows"]:
                if row["id"] == ROW_ID:
                    return row
        return None

    def catalog_row(self):
        row = self.find_row()
        if row is None:
            self.fail(f"{ROW_ID} is not in the catalog")
        return row

    def enabled(self, extra=None):
        data = {"enabledPlugins": {checks.PLAYWRIGHT_PLUGIN_ID: True}}
        data.update(extra or {})
        return data

    def test_row_hidden_without_plugin_and_shown_with_it(self):
        self.set_settings({"enabledPlugins": {checks.PLAYWRIGHT_PLUGIN_ID: False}})
        self.assertIsNone(self.find_row())
        self.set_settings(self.enabled())
        self.assertIsNotNone(self.find_row())

    def test_default_chrome_present_is_ok_without_apply(self):
        _make_executable(self.default_chrome)
        self.set_settings(self.enabled())
        row = self.catalog_row()
        self.assertTrue(row["current_display"].startswith("ok"), row["current_display"])
        self.assertFalse(row["apply_eligible"])

    def test_variable_naming_executable_is_ok_without_apply(self):
        self.set_settings(self.enabled({"env": {checks.PLAYWRIGHT_ENV_KEY: self.wrapper}}))
        row = self.catalog_row()
        self.assertTrue(row["current_display"].startswith("ok"), row["current_display"])
        self.assertFalse(row["apply_eligible"])

    def test_neither_path_is_problem_with_apply_offered(self):
        self.set_settings(self.enabled())
        row = self.catalog_row()
        self.assertEqual(
            row["current_display"],
            f"problem: no Chrome at {self.default_chrome}; "
            f"{checks.PLAYWRIGHT_ENV_KEY} unset",
        )
        self.assertTrue(row["apply_eligible"])

    def test_variable_naming_missing_file_is_problem_naming_it(self):
        missing = os.path.join(self.root, "gone", "chrome")
        self.set_settings(self.enabled({"env": {checks.PLAYWRIGHT_ENV_KEY: missing}}))
        row = self.catalog_row()
        self.assertTrue(row["current_display"].startswith("problem"), row["current_display"])
        self.assertIn(missing, row["current_display"])
        self.assertTrue(row["apply_eligible"])

    def test_wrapper_missing_offers_no_apply_and_direct_apply_refuses(self):
        os.remove(self.wrapper)
        self.set_settings(self.enabled())
        before = self.read()
        row = self.catalog_row()
        self.assertFalse(row["apply_eligible"])
        result = checks.apply_row(ROW_ID, self.ctx(), dry=False)
        self.assertFalse(result["ok"])
        self.assertTrue(result["reason"].startswith("refused:"), result["reason"])
        self.assertEqual(self.read(), before)

    def test_default_and_wrapper_both_present_is_ok_without_apply(self):
        _make_executable(self.default_chrome)
        self.set_settings(self.enabled())
        row = self.catalog_row()
        self.assertTrue(row["current_display"].startswith("ok"))
        self.assertFalse(row["apply_eligible"])
        result = checks.apply_row(ROW_ID, self.ctx(), dry=False)
        self.assertEqual(result["reason"], "refused: nothing to fix; nothing was written")

    def test_apply_writes_one_env_key_then_refuses_second_apply(self):
        self.set_settings(self.enabled({"theme": "dark", "env": {"KEEP": "1"}}))
        result = checks.apply_row(ROW_ID, self.ctx(), dry=False)
        self.assertTrue(result["ok"], result)
        self.assertEqual(len(self.backup_names(self.claude_backups)), 1)
        with open(self.settings, encoding="utf-8") as handle:
            data = json.load(handle)
        self.assertEqual(data["env"], {"KEEP": "1", checks.PLAYWRIGHT_ENV_KEY: self.wrapper})
        self.assertEqual(data["theme"], "dark")
        self.assertIn(checks.PLAYWRIGHT_PLUGIN_ID, data["enabledPlugins"])
        after_first = self.read()
        second = checks.apply_row(ROW_ID, self.ctx(), dry=False)
        self.assertFalse(second["ok"])
        self.assertEqual(second["reason"], "refused: nothing to fix; nothing was written")
        self.assertEqual(self.read(), after_first)
        self.assertEqual(len(self.backup_names(self.claude_backups)), 1)
        row = self.catalog_row()
        self.assertTrue(row["current_display"].startswith("ok"), row["current_display"])
        self.assertFalse(row["apply_eligible"])

    def test_no_settings_file_is_created_with_only_the_env_key(self):
        result = checks.apply_row(ROW_ID, self.ctx(), dry=False)
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["backup"], "")
        with open(self.settings, encoding="utf-8") as handle:
            self.assertEqual(json.load(handle), {"env": {checks.PLAYWRIGHT_ENV_KEY: self.wrapper}})

    def test_non_object_env_is_refused_without_write(self):
        self.set_settings(self.enabled({"env": "not-an-object"}))
        before = self.read()
        result = checks.apply_row(ROW_ID, self.ctx(), dry=False)
        self.assertFalse(result["ok"])
        self.assertEqual(self.read(), before)
        self.assertEqual(self.backup_names(self.claude_backups), [])

    def test_only_settings_json_changes_in_the_scratch_tree(self):
        self.set_settings(self.enabled({"env": {"KEEP": "1"}}))
        skip = self.backups
        before = _tree(self.root, skip)
        result = checks.apply_row(ROW_ID, self.ctx(), dry=False)
        self.assertTrue(result["ok"], result)
        after = _tree(self.root, skip)
        self.assertEqual(set(before), set(after))
        changed = [path for path in before if before[path] != after[path]]
        self.assertEqual(changed, [self.settings])
        self.assertFalse(os.path.exists(os.path.join(self.home, ".claude.json")))

    def test_row_text_names_the_inference_and_medium_confidence(self):
        self.set_settings(self.enabled())
        row = self.catalog_row()
        self.assertEqual(row["confidence"], "MEDIUM")
        self.assertIn("inferred", row["why"])
        self.assertIn("the variable reaching the MCP process and a headed launch", row["why"])
        self.assertIn("Phase 54 live check", row["why"])


if __name__ == "__main__":
    unittest.main()
