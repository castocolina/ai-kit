"""config-status (36 SPEC R1, D-02): active, pending or none from scratch layers; read only."""

import io
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout

_REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(_REPO_ROOT, "skills", "ai-kit-spec-review"))

from ai_kit_spec import cli, config_io, config_migrate

REVIEW_LANE = '[[lanes.review]]\nkey = "{key}"\nruntime = "codex"\nmodel = "placeholder-model-1"\n'
COMMAND_LANE = ('[[lanes.review]]\nkey = "c1"\nmodel = "placeholder-model-2"\n'
                'command = "placeholder-cli-1 {model}"\n')
OLD_ROSTER = '[[reviewers]]\nkey = "o1"\nruntime = "codex"\nmodel = "placeholder-model-3"\n'
EXECUTE_LANE = '[[lanes.execute]]\nkey = "x1"\nruntime = "codex"\nmodel = "placeholder-model-4"\n'


class _StatusCase(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = tmp.name
        self.cwd = os.path.join(self.root, "project")
        os.makedirs(self.cwd)
        self.env = {"HOME": os.path.join(self.root, "home"),
                    "XDG_CONFIG_HOME": os.path.join(self.root, "xdg"),
                    "XDG_CACHE_HOME": os.path.join(self.root, "cache")}

    def project_path(self):
        return config_io.cfg_local_path(self.cwd)

    def user_path(self):
        return config_io.cfg_global_path(self.env)

    def write(self, path, text):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)

    def run_status(self, *extra):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = cli.main(["config-status", "--cwd", self.cwd, *extra],
                            env_fn=lambda: dict(self.env))
        return code, out.getvalue().splitlines(), err.getvalue()

    def expect(self, state, project, user, *extra):
        code, lines, err = self.run_status(*extra)
        self.assertEqual(code, 0, err)
        self.assertEqual(lines, [
            state, f"checked project {os.path.abspath(self.project_path())} {project}",
            f"checked user {self.user_path()} {user}",
        ])


class TestConfigStatusTracer(_StatusCase):
    def test_no_config_is_none(self):
        self.expect("none", "missing", "missing")

    def test_user_layer_only_is_active(self):
        self.write(self.user_path(), REVIEW_LANE.format(key="u1"))
        self.expect("active", "missing", "lanes")

    def test_project_layer_only_is_active(self):
        self.write(self.project_path(), REVIEW_LANE.format(key="p1"))
        self.expect("active", "lanes", "missing")


class TestConfigStatusStates(_StatusCase):
    def test_both_layers_active_lists_project_first(self):
        self.write(self.project_path(), REVIEW_LANE.format(key="p1"))
        self.write(self.user_path(), REVIEW_LANE.format(key="u1"))
        self.expect("active", "lanes", "lanes")

    def test_untrusted_command_lane_is_pending_even_with_user_lanes(self):
        self.write(self.project_path(), COMMAND_LANE)
        self.write(self.user_path(), REVIEW_LANE.format(key="u1"))
        self.expect("pending", "untrusted", "lanes")

    def test_trusted_command_lane_is_active(self):
        self.write(self.project_path(), COMMAND_LANE)
        config_io.cfg_trust_project(self.cwd, self.env)
        self.expect("active", "lanes", "missing")

    def test_old_project_roster_is_pending_migration(self):
        old = config_migrate.legacy_path(self.project_path())
        self.write(old, OLD_ROSTER)
        self.expect("pending", "pending-migration", "missing")
        self.assertTrue(os.path.exists(old))
        self.assertFalse(os.path.exists(self.project_path()))

    def test_old_user_roster_is_pending_migration(self):
        self.write(config_migrate.legacy_path(self.user_path()), OLD_ROSTER)
        self.expect("pending", "missing", "pending-migration")

    def test_local_only_empty_project_beside_full_user_is_none(self):
        self.write(self.project_path(), '[lanes]\nstrategy = "local-only"\n')
        self.write(self.user_path(), REVIEW_LANE.format(key="u1"))
        self.expect("none", "empty", "skipped-local-only")

    def test_empty_lanes_table_is_empty(self):
        for text in ('[lanes.policy]\nmode = "single"\n', '[lanes]\nreview = []\n'):
            with self.subTest(text=text):
                self.write(self.project_path(), text)
                self.expect("none", "empty", "missing")

    def test_session_default_lane_counts_as_a_roster(self):
        self.write(self.user_path(), '[[lanes.review]]\nkey = "session-default"\n')
        self.expect("active", "missing", "lanes")


class TestConfigStatusErrors(_StatusCase):
    def assert_error(self, path):
        code, lines, err = self.run_status()
        self.assertEqual(code, 2)
        self.assertEqual(lines, [])
        self.assertTrue(err.startswith("ai-kit-spec: config error: "), err)
        self.assertIn(path, err)

    def test_malformed_project_file_is_exit_2(self):
        self.write(self.project_path(), '[lanes\n')
        self.assert_error(self.project_path())

    def test_malformed_user_file_is_exit_2(self):
        self.write(self.user_path(), '[lanes\n')
        self.assert_error(self.user_path())

    def test_malformed_old_roster_is_exit_2(self):
        old = config_migrate.legacy_path(self.project_path())
        self.write(old, '[[reviewers\n')
        self.assert_error(old)


class TestConfigStatusReadOnly(_StatusCase):
    def _tree(self):
        result = []
        for root, dirs, files in os.walk(self.root):
            for name in dirs:
                result.append((os.path.relpath(os.path.join(root, name), self.root), None))
            for name in files:
                path = os.path.join(root, name)
                with open(path, "rb") as handle:
                    result.append((os.path.relpath(path, self.root), handle.read()))
        return sorted(result)

    def test_config_status_writes_and_migrates_nothing(self):
        old = config_migrate.legacy_path(self.project_path())
        self.write(old, OLD_ROSTER)
        self.write(self.user_path(), REVIEW_LANE.format(key="u1"))
        before = self._tree()
        for _ in range(2):
            code, lines, _err = self.run_status()
            self.assertEqual(code, 0)
            self.assertEqual(lines[0], "pending")
        self.assertEqual(before, self._tree())
        self.assertFalse(os.path.exists(config_io.cfg_trust_store_dir(self.env)))
        self.assertTrue(os.path.exists(old))


class TestConfigStatusCombinations(_StatusCase):
    def test_old_project_roster_beside_project_lanes_stays_active(self):
        old = config_migrate.legacy_path(self.project_path())
        self.write(old, OLD_ROSTER)
        self.write(self.project_path(), REVIEW_LANE.format(key="p1"))
        self.expect("active", "lanes", "missing")
        self.assertTrue(os.path.exists(old))

    def test_old_user_roster_beside_user_lanes_stays_active(self):
        self.write(config_migrate.legacy_path(self.user_path()), OLD_ROSTER)
        self.write(self.user_path(), REVIEW_LANE.format(key="u1"))
        self.expect("active", "missing", "lanes")

    def test_local_only_project_never_reads_a_malformed_user_file(self):
        self.write(self.project_path(), '[lanes]\nstrategy = "local-only"\n')
        self.write(self.user_path(), '[lanes\n')
        self.expect("none", "empty", "skipped-local-only")

    def test_local_only_project_with_an_old_roster_is_none(self):
        self.write(self.project_path(), '[lanes]\nstrategy = "local-only"\n')
        self.write(config_migrate.legacy_path(self.project_path()), OLD_ROSTER)
        self.write(self.user_path(), REVIEW_LANE.format(key="u1"))
        self.expect("none", "empty", "skipped-local-only")

    def test_malformed_old_roster_beside_lanes_is_exit_2(self):
        old = config_migrate.legacy_path(self.project_path())
        self.write(old, '[[reviewers\n')
        self.write(self.project_path(), REVIEW_LANE.format(key="p1"))
        code, lines, err = self.run_status()
        self.assertEqual(code, 2)
        self.assertEqual(lines, [])
        self.assertIn(old, err)

    def test_resolve_reviewers_migrates_the_pending_roster(self):
        self.write(config_migrate.legacy_path(self.project_path()), OLD_ROSTER)
        self.expect("pending", "pending-migration", "missing")
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            code = cli.main(["resolve-reviewers", "--cwd", self.cwd, "--quota-path",
                             os.path.join(self.root, "quota.json")],
                            env_fn=lambda: dict(self.env), which_fn=lambda _name, **_kwargs: None,
                            run_fn=lambda *_a, **_k: None)
        self.assertEqual(code, 0)
        self.expect("active", "lanes", "missing")


class TestConfigStatusRole(_StatusCase):
    def test_role_review_ignores_an_execute_only_roster(self):
        self.write(self.user_path(), EXECUTE_LANE)
        self.expect("none", "missing", "empty", "--role", "review")

    def test_role_execute_ignores_a_review_only_roster(self):
        self.write(self.user_path(), REVIEW_LANE.format(key="u1"))
        self.expect("none", "missing", "empty", "--role", "execute")

    def test_both_roles_are_active_for_each_role_flag(self):
        self.write(self.user_path(), REVIEW_LANE.format(key="u1") + EXECUTE_LANE)
        for role in ("review", "execute"):
            self.expect("active", "missing", "lanes", "--role", role)

    def test_no_role_flag_counts_either_role(self):
        for text in (EXECUTE_LANE, REVIEW_LANE.format(key="u1")):
            self.write(self.user_path(), text)
            self.expect("active", "missing", "lanes")


if __name__ == "__main__":
    unittest.main()
