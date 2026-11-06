"""Status-line toggle commit (phase 30.1 plan 04, R3 / D-06 / D-07 / D-08).

Stdlib only. Every case runs under a scratch HOME built with
``tempfile.mkdtemp(prefix="ai-kit-p301-")``; no real host config is ever read.
"""

import importlib.util
import json
import os
import shlex
import shutil
import sys
import tempfile
import tomllib
import unittest
from unittest import mock

_TOOLS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "tools"))
if _TOOLS_DIR not in sys.path:
    sys.path.insert(0, _TOOLS_DIR)
import config_doctor_appliers


def load_module():
    path = os.path.join(_TOOLS_DIR, "setup.py")
    spec = importlib.util.spec_from_file_location("setup", path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


setup = load_module()


def scratch_env(test):
    """A scratch HOME and XDG roots under one mkdtemp dir, removed after the test."""
    root = tempfile.mkdtemp(prefix="ai-kit-p301-")
    test.addCleanup(shutil.rmtree, root, True)
    home = os.path.join(root, "home")
    os.makedirs(home)
    return {
        "HOME": home,
        "XDG_STATE_HOME": os.path.join(root, "state"),
        "XDG_CONFIG_HOME": os.path.join(root, "config"),
        "XDG_DATA_HOME": os.path.join(root, "data"),
        "CLAUDE_CONFIG_DIR": os.path.join(home, ".claude"),
        "CURSOR_CONFIG_DIR": os.path.join(home, ".cursor"),
        "AI_KIT_DIR": os.path.join(root, "data", "ai-kit"),
    }


def ours_entry(paths, host):
    """The statusLine entry setup writes for ai-kit's own status line."""
    script = paths.status_line if host == "claude" else paths.cursor_status_line
    return {"type": "command", "command": "python3 -S " + shlex.quote(script)}


def write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle)


def read_bytes(path):
    with open(path, "rb") as handle:
        return handle.read()


def read_json(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


class TestToggleCommitTracer(unittest.TestCase):
    def setUp(self):
        self.env = scratch_env(self)
        self.paths = setup.resolve_paths(self.env)

    def _off_state(self, current_command):
        return {"adopt": False, "start_state": "ours", "adopt_command": current_command,
                "segments": {}, "layout": [], "dirty": False}

    def test_cursor_off_on_ours_removes_only_statusline(self):
        path = self.paths.cursor_cli_config
        write_json(path, {"editor": {"vimMode": True},
                          "statusLine": ours_entry(self.paths, "cursor")})
        current = setup.detect_statusline_cursor(self.paths)
        self.assertEqual(current["state"], "ours")
        result = setup._commit_host_statusline(
            self.paths, "cursor", self._off_state(current["current_command"]),
            dry=False, examples_flag=None)
        self.assertTrue(result["ok"], result["log"])
        self.assertEqual(result["action"], "remove_ours")
        data = read_json(path)
        self.assertNotIn("statusLine", data)
        self.assertEqual(data["editor"], {"vimMode": True})

    def test_cursor_off_on_ours_dry_run_writes_nothing(self):
        path = self.paths.cursor_cli_config
        write_json(path, {"editor": {"vimMode": True},
                          "statusLine": ours_entry(self.paths, "cursor")})
        before = read_bytes(path)
        current = setup.detect_statusline_cursor(self.paths)
        result = setup._commit_host_statusline(
            self.paths, "cursor", self._off_state(current["current_command"]),
            dry=True, examples_flag=None)
        self.assertTrue(result["ok"], result["log"])
        self.assertEqual(read_bytes(path), before)

    def test_claude_off_on_ours_removes_statusline_and_keeps_theme(self):
        path = self.paths.settings
        write_json(path, {"theme": "dark", "statusLine": ours_entry(self.paths, "claude")})
        current = setup.detect_statusline(self.paths)
        self.assertEqual(current["state"], "ours")
        result = setup._commit_host_statusline(
            self.paths, "claude", self._off_state(current["current_command"]),
            dry=False, examples_flag=None)
        self.assertTrue(result["ok"], result["log"])
        self.assertEqual(result["action"], "remove_ours")
        self.assertEqual(read_json(path), {"theme": "dark"})

    def test_keep_current_foreign_entry_writes_nothing(self):
        path = self.paths.settings
        write_json(path, {"theme": "dark",
                          "statusLine": {"type": "command", "command": "my-line.sh"}})
        before = read_bytes(path)
        state = {"adopt": False, "start_state": "foreign", "adopt_command": "my-line.sh",
                 "foreign_choice": "keep", "foreign_ok": False}
        result = setup._commit_host_statusline(self.paths, "claude", state,
                                               dry=False, examples_flag=None)
        self.assertEqual(result, {"ok": True, "adopt": False, "log": "",
                                  "action": "keep_foreign"})
        self.assertEqual(read_bytes(path), before)
        self.assertFalse(os.path.exists(self.paths.backups_dir))

    def test_keep_current_writes_nothing_even_when_entry_changed_or_confirmed(self):
        path = self.paths.settings
        write_json(path, {"theme": "dark",
                          "statusLine": {"type": "command", "command": "other.sh"}})
        before = read_bytes(path)
        state = {"adopt": False, "start_state": "foreign", "adopt_command": "my-line.sh",
                 "foreign_choice": "keep", "foreign_ok": True}
        result = setup._commit_host_statusline(self.paths, "claude", state,
                                               dry=False, examples_flag=None)
        self.assertEqual(result, {"ok": True, "adopt": False, "log": "",
                                  "action": "keep_foreign"})
        self.assertEqual(read_bytes(path), before)

    def test_action_table(self):
        rows = [
            ({"adopt": True}, False, "wire"),
            ({"adopt": True, "start_state": "ours", "dirty": True}, False, "update"),
            ({"adopt": True, "start_state": "ours", "dirty": False}, False, "unchanged"),
            ({"adopt": True, "start_state": "ours", "dirty": False}, True, "update"),
            ({"adopt": True, "start_state": "foreign", "dirty": False,
              "foreign_choice": "custom"}, False, "replace_foreign"),
            ({"adopt": True, "start_state": "foreign", "dirty": True,
              "foreign_choice": "custom"}, False, "replace_foreign"),
            ({"adopt": False}, False, "unchanged"),
            ({"adopt": False, "start_state": "ours"}, False, "remove_ours"),
            ({"adopt": False, "start_state": "foreign", "foreign_choice": "keep"},
             False, "keep_foreign"),
            ({"adopt": False, "start_state": "foreign"}, False, "keep_foreign"),
            ({"adopt": False, "start_state": "foreign", "foreign_choice": "remove"},
             False, "remove_foreign"),
        ]
        for state, forced, expected in rows:
            with self.subTest(state=state, forced=forced):
                self.assertEqual(setup._statusline_action(state, examples_forced=forced),
                                 expected)

    def test_resolve_paths_backups_dir_is_the_doctor_helper(self):
        self.assertEqual(self.paths.backups_dir,
                         config_doctor_appliers.backups_root(self.env))
        bare = {key: value for key, value in self.env.items() if key != "XDG_STATE_HOME"}
        self.assertEqual(setup.resolve_paths(bare).backups_dir,
                         config_doctor_appliers.backups_root(bare))


FOREIGN = {"type": "command", "command": "my-line.sh"}


def adopt_state(paths, host, **extra):
    """The toggle-on state the wizard builds from the bundled sample."""
    sample = paths.sample if host == "claude" else paths.cursor_sample
    state = {"adopt": True, "start_state": "unset",
             "segments": dict(setup.current_segments(sample, host)),
             "layout": setup.current_layout(sample, host), "dirty": True}
    state.update(extra)
    return state


def host_file(paths, host):
    return paths.settings if host == "claude" else paths.cursor_cli_config


class ToggleCase(unittest.TestCase):
    """Scratch-HOME helpers shared by the matrix and edge classes."""

    def setUp(self):
        self.env = scratch_env(self)
        self.paths = setup.resolve_paths(self.env)
        # The recipes setup copies on a first wire, and the doctor script the TOML
        # validation runs: link the repo's tools tree read-only in practice (the
        # tests only read it), so the scratch install has both.
        os.makedirs(self.env["AI_KIT_DIR"])
        os.symlink(_TOOLS_DIR, os.path.join(self.env["AI_KIT_DIR"], "tools"))
        self.patch = mock.patch.dict(os.environ,
                                     {"CC_AI_KIT_EXTERNAL_DIR": self.paths.segments_dir})
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def commit(self, host, state, dry=False):
        return setup._commit_host_statusline(self.paths, host, state,
                                             dry=dry, examples_flag=None)

    def toml_path(self, host):
        return self.paths.config_toml if host == "claude" else self.paths.cursor_config_toml

    def seed(self, host, data):
        write_json(host_file(self.paths, host), data)
        return host_file(self.paths, host)

    def ours_on_disk(self, host):
        """Wire ai-kit's entry with setup's own writers (a first on+unset commit)."""
        result = self.commit(host, adopt_state(self.paths, host))
        self.assertTrue(result["ok"], result["log"])
        state = (setup.detect_statusline(self.paths) if host == "claude"
                 else setup.detect_statusline_cursor(self.paths))
        self.assertEqual(state["state"], "ours")
        return state["current_command"]


class TestToggleMatrix(ToggleCase):
    UNRELATED = {"claude": ("theme", "dark"), "cursor": ("editor", {"vimMode": True})}

    def _with_unrelated(self, host, extra=None):
        key, value = self.UNRELATED[host]
        data = {key: value}
        data.update(extra or {})
        return data

    def test_unset_on_wires_ours_and_keeps_the_unrelated_key(self):
        for host in ("claude", "cursor"):
            with self.subTest(host=host):
                path = self.seed(host, self._with_unrelated(host))
                result = self.commit(host, adopt_state(self.paths, host))
                self.assertTrue(result["ok"], result["log"])
                self.assertEqual(result["action"], "wire")
                data = read_json(path)
                self.assertEqual(data[self.UNRELATED[host][0]], self.UNRELATED[host][1])
                self.assertIn("statusLine", data)

    def test_unset_off_is_byte_identical(self):
        for host in ("claude", "cursor"):
            with self.subTest(host=host):
                path = self.seed(host, self._with_unrelated(host))
                before = read_bytes(path)
                result = self.commit(host, {"adopt": False, "start_state": "unset"})
                self.assertEqual(result["action"], "unchanged")
                self.assertEqual(read_bytes(path), before)

    def test_ours_on_clean_writes_nothing_to_the_host_file(self):
        for host in ("claude", "cursor"):
            with self.subTest(host=host):
                path = self.seed(host, self._with_unrelated(host))
                current = self.ours_on_disk(host)
                before = read_bytes(path)
                toml = self.toml_path(host)
                toml_before = read_bytes(toml)
                result = self.commit(host, adopt_state(
                    self.paths, host, start_state="ours", adopt_command=current,
                    dirty=False))
                self.assertTrue(result["ok"], result["log"])
                self.assertEqual(result["action"], "unchanged")
                self.assertEqual(read_bytes(path), before)
                self.assertEqual(read_bytes(toml), toml_before)

    def test_examples_flag_forces_update_on_a_clean_ours_host(self):
        # The scratch install bundles the repo's one example. The wizard's first wire
        # declines it (`system_memory = false`); a clean reconfigure with an explicit
        # --examples=all must win over that toggle and rewrite the TOML.
        bundled = os.path.join(self.env["AI_KIT_DIR"], "examples", "segments")
        os.makedirs(bundled)
        shutil.copy2(os.path.join(_TOOLS_DIR, "..", "examples", "segments", "system_memory"),
                     bundled)
        segments = dict(setup.current_segments(self.paths.sample, "claude"))
        segments["system_memory"] = False
        layout = setup.current_layout(self.paths.sample, "claude")
        layout[2]["segments"].append("system_memory")
        state = adopt_state(self.paths, "claude", segments=segments, layout=layout)
        self.assertEqual(self.commit("claude", state)["action"], "wire")
        toml = self.toml_path("claude")
        before = read_bytes(toml)
        with open(toml, "rb") as handle:
            self.assertIs(tomllib.load(handle)["segments"]["system_memory"], False)
        current = setup.detect_statusline(self.paths)["current_command"]
        clean = dict(state, start_state="ours", adopt_command=current, dirty=False)
        result = setup._commit_host_statusline(self.paths, "claude", clean,
                                               dry=False, examples_flag="all")
        self.assertTrue(result["ok"], result["log"])
        self.assertEqual(result["action"], "update")
        self.assertNotEqual(read_bytes(toml), before)
        with open(toml, "rb") as handle:
            self.assertIs(tomllib.load(handle)["segments"].get("system_memory", True), True)
        self.assertIs(segments["system_memory"], False)  # the caller's state is not mutated

    def test_clean_upkeep_recreates_a_deleted_toml_and_keeps_the_wiring(self):
        current = self.ours_on_disk("claude")
        settings_before = read_bytes(self.paths.settings)
        os.remove(self.toml_path("claude"))
        result = self.commit("claude", adopt_state(
            self.paths, "claude", start_state="ours", adopt_command=current, dirty=False))
        self.assertTrue(result["ok"], result["log"])
        self.assertEqual(result["action"], "unchanged")
        self.assertTrue(os.path.isfile(self.toml_path("claude")))
        self.assertEqual(read_bytes(self.paths.settings), settings_before)

    def test_off_unset_host_creates_nothing(self):
        result = self.commit("claude", {"adopt": False, "start_state": "unset"})
        self.assertEqual(result["action"], "unchanged")
        self.assertFalse(os.path.exists(self.paths.settings))
        self.assertFalse(os.path.exists(self.toml_path("claude")))

    def test_ours_off_removes_statusline_only(self):
        for host in ("claude", "cursor"):
            with self.subTest(host=host):
                path = self.seed(host, self._with_unrelated(host))
                current = self.ours_on_disk(host)
                result = self.commit(host, {"adopt": False, "start_state": "ours",
                                            "adopt_command": current, "dirty": False})
                self.assertTrue(result["ok"], result["log"])
                data = read_json(path)
                self.assertNotIn("statusLine", data)
                self.assertEqual(data[self.UNRELATED[host][0]], self.UNRELATED[host][1])

    def test_foreign_on_custom_with_confirmation_replaces_the_entry(self):
        for host in ("claude", "cursor"):
            with self.subTest(host=host):
                path = self.seed(host, self._with_unrelated(host, {"statusLine": FOREIGN}))
                result = self.commit(host, adopt_state(
                    self.paths, host, start_state="foreign", foreign_choice="custom",
                    adopt_command="my-line.sh", dirty=False, foreign_ok=True))
                self.assertTrue(result["ok"], result["log"])
                self.assertEqual(result["action"], "replace_foreign")
                self.assertTrue(read_json(path)["statusLine"]["command"].startswith("python3 -S "))

    def test_foreign_on_dirty_writes_the_moved_layout_to_the_toml(self):
        for host in ("claude", "cursor"):
            with self.subTest(host=host):
                self.seed(host, self._with_unrelated(host, {"statusLine": FOREIGN}))
                state = adopt_state(self.paths, host, start_state="foreign",
                                    foreign_choice="custom", adopt_command="my-line.sh",
                                    foreign_ok=True)
                layout = [dict(row) for row in state["layout"]]
                self.assertGreaterEqual(len(layout), 2)
                moved = layout[0]["segments"][-1]
                layout[0]["segments"] = layout[0]["segments"][:-1]
                layout[1]["segments"] = [moved] + layout[1]["segments"]
                state["layout"] = layout
                result = self.commit(host, state)
                self.assertTrue(result["ok"], result["log"])
                self.assertEqual(result["action"], "replace_foreign")
                with open(self.toml_path(host), "rb") as handle:
                    rows = tomllib.load(handle)["line"]
                self.assertEqual([row["segments"] for row in rows],
                                 [row["segments"] for row in layout])

    def test_foreign_on_custom_without_confirmation_is_refused(self):
        for host in ("claude", "cursor"):
            with self.subTest(host=host):
                path = self.seed(host, self._with_unrelated(host, {"statusLine": FOREIGN}))
                before = read_bytes(path)
                result = self.commit(host, adopt_state(
                    self.paths, host, start_state="foreign", foreign_choice="custom",
                    adopt_command="my-line.sh", foreign_ok=False))
                self.assertFalse(result["ok"])
                self.assertEqual(read_bytes(path), before)

    def test_foreign_off_remove_with_confirmation_leaves_the_host_default(self):
        for host in ("claude", "cursor"):
            with self.subTest(host=host):
                path = self.seed(host, self._with_unrelated(host, {"statusLine": FOREIGN}))
                result = self.commit(host, {"adopt": False, "start_state": "foreign",
                                            "foreign_choice": "remove",
                                            "adopt_command": "my-line.sh",
                                            "foreign_ok": True})
                self.assertTrue(result["ok"], result["log"])
                self.assertEqual(result["action"], "remove_foreign")
                data = read_json(path)
                self.assertNotIn("statusLine", data)
                self.assertEqual(data[self.UNRELATED[host][0]], self.UNRELATED[host][1])
                self.assertFalse(os.path.exists(self.paths.config_toml))

    def test_foreign_off_keep_writes_nothing_with_or_without_confirmation(self):
        for host in ("claude", "cursor"):
            for choice in ("keep", None):
                for confirmed in (False, True):
                    label = f"{host} choice={choice} foreign_ok={confirmed}"
                    with self.subTest(label):
                        path = self.seed(host, self._with_unrelated(
                            host, {"statusLine": FOREIGN}))
                        before = read_bytes(path)
                        state = {"adopt": False, "start_state": "foreign",
                                 "adopt_command": "my-line.sh", "foreign_ok": confirmed}
                        if choice is not None:
                            state["foreign_choice"] = choice
                        result = self.commit(host, state)
                        self.assertEqual(result, {"ok": True, "adopt": False, "log": "",
                                                  "action": "keep_foreign"})
                        self.assertEqual(read_bytes(path), before)
                        self.assertFalse(os.path.exists(self.paths.backups_dir))


class TestPrepareForeign(ToggleCase):
    def test_claude_backup_is_taken_before_and_matches_the_file(self):
        path = self.seed("claude", {"theme": "dark", "statusLine": FOREIGN})
        before = read_bytes(path)
        out = setup._prepare_foreign(self.paths, "claude")
        self.assertEqual(out["entry"], "my-line.sh")
        self.assertEqual(out["file"], path)
        self.assertTrue(out["backup"].startswith(os.path.join(self.paths.backups_dir, "claude")))
        self.assertEqual(read_bytes(out["backup"]), before)
        self.assertEqual(read_bytes(path), before)

    def test_dry_prepare_takes_no_backup(self):
        path = self.seed("claude", {"theme": "dark", "statusLine": FOREIGN})
        before = read_bytes(path)
        out = setup._prepare_foreign(self.paths, "claude", dry=True)
        self.assertEqual(out["backup"], "")
        self.assertFalse(os.path.exists(self.paths.backups_dir))
        self.assertEqual(read_bytes(path), before)

    def test_jsonc_cursor_config_is_refused_and_left_byte_identical(self):
        path = self.paths.cursor_cli_config
        os.makedirs(os.path.dirname(path), exist_ok=True)
        text = '// kept by hand\n{"statusLine": {"type": "command", "command": "my-line.sh"}}\n'
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)
        out = setup._prepare_foreign(self.paths, "cursor")
        self.assertIn(path, out["error"])
        custom = adopt_state(self.paths, "cursor", start_state="foreign",
                             foreign_choice="custom", adopt_command="my-line.sh",
                             foreign_ok=True)
        remove = {"adopt": False, "start_state": "foreign", "foreign_choice": "remove",
                  "adopt_command": "my-line.sh", "foreign_ok": True}
        for state in (custom, remove):
            with self.subTest(adopt=state["adopt"]):
                result = self.commit("cursor", state)
                self.assertFalse(result["ok"])
                self.assertIn("cli-config.json", result["log"])
        with open(path, encoding="utf-8") as handle:
            self.assertEqual(handle.read(), text)

    def test_entry_changed_after_prepare_is_refused_for_replace_and_remove(self):
        path = self.seed("claude", {"theme": "dark", "statusLine": FOREIGN})
        setup._prepare_foreign(self.paths, "claude")
        write_json(path, {"theme": "dark",
                          "statusLine": {"type": "command", "command": "other.sh"}})
        for choice, state_extra in (("custom", {"adopt": True}),
                                    ("remove", {"adopt": False})):
            with self.subTest(choice=choice):
                result = self.commit("claude", dict(
                    start_state="foreign", foreign_choice=choice, adopt_command="my-line.sh",
                    foreign_ok=True, **state_extra))
                self.assertFalse(result["ok"])
                self.assertIn("changed after approval", result["log"])
                self.assertEqual(read_json(path)["statusLine"]["command"], "other.sh")


class TestForeignBackupBinding(ToggleCase):
    def test_repeat_prepare_reuses_the_backup_while_the_file_is_unchanged(self):
        path = self.seed("claude", {"theme": "dark", "statusLine": FOREIGN})
        cache = {}
        first = setup._prepare_foreign(self.paths, "claude", cache=cache)
        again = setup._prepare_foreign(self.paths, "claude", cache=cache)
        self.assertEqual(again["backup"], first["backup"])
        self.assertEqual(len(os.listdir(os.path.join(self.paths.backups_dir, "claude"))), 1)
        write_json(path, {"theme": "light", "statusLine": FOREIGN})   # the file moved on
        fresh = setup._prepare_foreign(self.paths, "claude", cache=cache)
        self.assertNotEqual(fresh["backup"], first["backup"])

    def test_commit_refuses_when_the_file_differs_from_the_confirmed_backup(self):
        path = self.seed("claude", {"theme": "dark", "statusLine": FOREIGN})
        backup = setup._prepare_foreign(self.paths, "claude")["backup"]
        write_json(path, {"theme": "light", "statusLine": FOREIGN})   # same command, other bytes
        after_edit = read_bytes(path)
        for choice, extra in (("custom", {"adopt": True}), ("remove", {"adopt": False})):
            with self.subTest(choice=choice):
                result = self.commit("claude", dict(
                    start_state="foreign", foreign_choice=choice, adopt_command="my-line.sh",
                    foreign_ok=True, foreign_backup=backup, **extra))
                self.assertFalse(result["ok"])
                self.assertIn("changed after the backup you confirmed", result["log"])
                self.assertEqual(read_bytes(path), after_edit)

    def test_commit_proceeds_when_the_file_still_equals_the_backup(self):
        path = self.seed("claude", {"theme": "dark", "statusLine": FOREIGN})
        backup = setup._prepare_foreign(self.paths, "claude")["backup"]
        result = self.commit("claude", {"adopt": False, "start_state": "foreign",
                                        "foreign_choice": "remove", "adopt_command": "my-line.sh",
                                        "foreign_ok": True, "foreign_backup": backup})
        self.assertTrue(result["ok"], result["log"])
        self.assertNotIn("statusLine", read_json(path))


class TestToggleEdges(ToggleCase):
    def test_missing_host_file_off_writes_nothing_and_on_creates_the_entry(self):
        self.assertTrue(self.commit("claude", {"adopt": False, "start_state": "unset"})["ok"])
        self.assertFalse(os.path.exists(self.paths.settings))
        result = self.commit("claude", adopt_state(self.paths, "claude"))
        self.assertTrue(result["ok"], result["log"])
        self.assertEqual(setup.detect_statusline(self.paths)["state"], "ours")

    def test_remove_entry_refuses_a_changed_entry_and_writes_nothing(self):
        path = self.seed("claude", {"theme": "dark",
                                    "statusLine": {"type": "command", "command": "other.sh"}})
        before = read_bytes(path)
        self.assertFalse(setup._remove_statusline_entry(self.paths, "claude", False, "my-line.sh"))
        self.assertEqual(read_bytes(path), before)

    def test_remove_entry_pops_only_the_approved_entry(self):
        path = self.seed("claude", {"theme": "dark", "statusLine": FOREIGN})
        self.assertTrue(setup._remove_statusline_entry(self.paths, "claude", False, "my-line.sh"))
        self.assertEqual(read_json(path), {"theme": "dark"})

    def test_remove_entry_refuses_when_the_entry_is_already_gone(self):
        path = self.seed("claude", {"theme": "dark"})
        before = read_bytes(path)
        self.assertFalse(setup._remove_statusline_entry(self.paths, "claude", False, "my-line.sh"))
        self.assertEqual(read_bytes(path), before)

    def test_unparseable_claude_settings_is_refused_byte_identical(self):
        os.makedirs(self.paths.claude_dir, exist_ok=True)
        with open(self.paths.settings, "w", encoding="utf-8") as handle:
            handle.write("{not json")
        before = read_bytes(self.paths.settings)
        result = self.commit("claude", {"adopt": False, "start_state": "foreign",
                                        "foreign_choice": "remove",
                                        "adopt_command": "my-line.sh", "foreign_ok": True})
        self.assertFalse(result["ok"])
        self.assertEqual(read_bytes(self.paths.settings), before)

    def test_dry_prepare_and_dry_removal_write_nothing(self):
        path = self.seed("claude", {"theme": "dark", "statusLine": FOREIGN})
        before = read_bytes(path)
        result = self.commit("claude", {"adopt": False, "start_state": "foreign",
                                        "foreign_choice": "remove",
                                        "adopt_command": "my-line.sh", "foreign_ok": True},
                             dry=True)
        self.assertTrue(result["ok"], result["log"])
        self.assertEqual(read_bytes(path), before)


if __name__ == "__main__":
    unittest.main()
