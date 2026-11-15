"""config.toml: the layered reader, role-keyed lanes, the D-11 trust rule and read-only mode
(Plan 33-07; SPEC R2, R3, R4, R5; D-10, D-11, D-24).

Every test uses its own temporary cwd, HOME and XDG_CONFIG_HOME, never the real user config.
Fixtures are synthetic and carry no secret value.
"""

import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills", "ai-kit-spec-review"))

from ai_kit_spec import cli, config_io, config_migrate, trust
from ai_kit_spec.runner_dispatch import RunnerResult

# probe-quota routes every reviewer first: no real binary lookup, listing or runtimes build.
NO_RUNTIMES = {"which_fn": lambda _name, **_kwargs: None, "run_fn": lambda *_a, **_k: None}
UNTRUSTED = "ignoring untrusted project-local config"


def _probe_ok():
    return RunnerResult(0, "", {"status": "ok"}, None, False, ["node", "runner"], "")


def _read(path):
    with open(path, "rb") as handle:
        return handle.read()


class _LayerCase(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = tmp.name
        self.cwd = os.path.join(self.root, "project")
        os.makedirs(self.cwd)
        self.env = {
            "HOME": os.path.join(self.root, "home"),
            "XDG_CONFIG_HOME": os.path.join(self.root, "xdg"),
            "XDG_CACHE_HOME": os.path.join(self.root, "cache"),
        }
        patcher = mock.patch.dict(os.environ, self.env)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.store = config_io.cfg_trust_store_dir(self.env)
        self.warnings = []

    def project_path(self):
        return config_io.cfg_local_path(self.cwd)

    def user_path(self, name="config.toml"):
        return os.path.join(self.env["XDG_CONFIG_HOME"], "ai-kit", name)

    def write(self, path, raw):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as handle:
            handle.write(raw)
        return path

    def resolve(self, migrate=True):
        return config_io.cfg_resolve(self.cwd, self.env, warn_fn=self.warnings.append,
                                     migrate=migrate)

    def tree(self):
        found = []
        for dirpath, dirnames, filenames in os.walk(self.root):
            for name in dirnames + filenames:
                found.append(os.path.relpath(os.path.join(dirpath, name), self.root))
        return sorted(found)

    @staticmethod
    def keys(entries):
        return [entry["key"] for entry in entries]

    def untrusted_warnings(self):
        return [line for line in self.warnings if UNTRUSTED in line]


def _lanes(raw):
    return config_io.cfg_lanes_table(config_io.cfg_parse_toml_bytes(raw, "config.toml"),
                                     "config.toml")


class TestLayeredTable(_LayerCase):
    def test_project_wins_per_key_and_user_fills_the_rest(self):
        self.write(self.user_path(), b'[jev]\nurl = "u"\nknob = true\n')
        self.write(self.project_path(), b'[jev]\nurl = "p"\n')
        self.assertEqual(config_io.cfg_layered_table(self.cwd, self.env, "jev"),
                         {"url": "p", "knob": True})

    def test_missing_files_give_an_empty_table(self):
        self.assertEqual(config_io.cfg_layered_table(self.cwd, self.env, "jev"), {})

    def test_bad_utf8_project_file_raises_naming_the_path(self):
        self.write(self.project_path(), b"\xff\xfe = 1")
        with self.assertRaises(config_io.ConfigError) as ctx:
            config_io.cfg_layered_table(self.cwd, self.env, "jev")
        self.assertEqual(ctx.exception.path, self.project_path())


class TestEmpty(_LayerCase):
    def test_no_config_anywhere_gives_defaults_and_writes_nothing(self):
        before = self.tree()
        resolved = self.resolve()
        self.assertEqual(resolved["policy"], config_io.DEFAULT_POLICY)
        self.assertEqual(resolved["reviewers"], [])
        self.assertEqual(resolved["review"], [])
        self.assertEqual(resolved["execute"], [])
        self.assertEqual(self.tree(), before)
        self.assertEqual(self.warnings, [])


class TestLaneRoles(_LayerCase):
    def test_review_and_execute_lanes_load_under_their_roles(self):
        self.write(self.project_path(),
                   b'[[lanes.review]]\nkey = "r"\nruntime = "codex"\nmodel = "m"\n'
                   b'[[lanes.execute]]\nkey = "x"\nruntime = "codex"\nmodel = "n"\n')
        resolved = self.resolve()
        self.assertEqual(self.keys(resolved["review"]), ["r"])
        self.assertEqual(self.keys(resolved["execute"]), ["x"])
        self.assertEqual(self.keys(resolved["reviewers"]), ["r", "x"])

    def test_same_key_in_both_roles_stays_two_entries(self):
        self.write(self.project_path(),
                   b'[[lanes.review]]\nkey = "k"\nruntime = "codex"\nmodel = "m1"\n'
                   b'[[lanes.execute]]\nkey = "k"\nruntime = "codex"\nmodel = "m2"\n')
        resolved = self.resolve()
        self.assertEqual([(e["key"], e["model"]) for e in resolved["review"]], [("k", "m1")])
        self.assertEqual([(e["key"], e["model"]) for e in resolved["execute"]], [("k", "m2")])
        self.assertEqual([(e["key"], e["model"]) for e in resolved["reviewers"]], [("k", "m1")])

    def test_unknown_table_and_key_read_without_error(self):
        self.write(self.project_path(),
                   b'[foo]\nbar = [1, 2]\n[lanes]\nextra = 1\n'
                   b'[[lanes.review]]\nkey = "r"\nruntime = "codex"\nmodel = "m"\n')
        self.assertEqual(self.keys(self.resolve()["review"]), ["r"])
        self.assertEqual(self.warnings, [])

    def test_execute_lane_merges_project_over_user_within_execute_only(self):
        self.write(self.user_path(),
                   b'[[lanes.execute]]\nkey = "e"\nruntime = "codex"\nmodel = "u"\n'
                   b'effort = "low"\n')
        self.write(self.project_path(), b'[[lanes.execute]]\nkey = "e"\nmodel = "p"\n')
        resolved = self.resolve()
        self.assertEqual(resolved["review"], [])
        self.assertEqual(len(resolved["execute"]), 1)
        entry = resolved["execute"][0]
        self.assertEqual(entry["model"], "p")
        self.assertEqual(entry["runtime"], "codex")
        self.assertEqual(entry["effort"], "low")


class TestTrustRule(_LayerCase):
    COMMAND_LANE = b'[[lanes.review]]\nkey = "c"\nmodel = "m"\ncommand = "echo {model}"\n'

    def test_lane_without_command_applies_with_no_trust_record(self):
        self.write(self.project_path(),
                   b'[[lanes.review]]\nkey = "a"\nruntime = "codex"\nmodel = "m"\n')
        self.assertEqual(self.keys(self.resolve()["review"]), ["a"])
        self.assertEqual(self.warnings, [])
        self.assertFalse(os.path.isdir(self.store))

    def test_command_lane_without_trust_is_ignored_with_a_warning(self):
        self.write(self.project_path(), self.COMMAND_LANE)
        self.assertEqual(self.resolve()["review"], [])
        self.assertTrue(self.untrusted_warnings())

    def test_command_lane_applies_once_trusted(self):
        self.write(self.project_path(), self.COMMAND_LANE)
        config_io.cfg_trust_project(self.cwd, self.env)
        self.assertEqual(self.keys(self.resolve()["review"]), ["c"])
        self.assertEqual(self.untrusted_warnings(), [])

    def test_comment_and_unrelated_table_keep_trust(self):
        self.write(self.project_path(), self.COMMAND_LANE)
        config_io.cfg_trust_project(self.cwd, self.env)
        self.write(self.project_path(),
                   b"# a comment\n" + self.COMMAND_LANE + b"\n[runner.retry]\nmax_attempts = 3\n")
        self.assertEqual(self.keys(self.resolve()["review"]), ["c"])
        self.assertEqual(self.untrusted_warnings(), [])

    def test_command_edit_drops_trust(self):
        self.write(self.project_path(), self.COMMAND_LANE)
        config_io.cfg_trust_project(self.cwd, self.env)
        self.write(self.project_path(), self.COMMAND_LANE.replace(b"echo", b"printf"))
        self.assertEqual(self.resolve()["review"], [])
        self.assertTrue(self.untrusted_warnings())

    def test_user_command_key_makes_a_command_free_override_need_trust(self):
        self.write(self.user_path(),
                   b'[[lanes.review]]\nkey = "g"\nmodel = "m"\ncommand = "echo {model}"\n')
        self.write(self.project_path(), b'[[lanes.review]]\nkey = "g"\nmodel = "p"\n')
        before = self.resolve()["review"]
        self.assertEqual(before[0]["model"], "m")  # the override is ignored until trusted
        self.assertTrue(self.untrusted_warnings())
        config_io.cfg_trust_project(self.cwd, self.env)
        resolved = self.resolve()["review"][0]
        self.assertEqual(resolved["model"], "p")
        self.assertEqual(resolved["command"], "echo {model}")

    def test_local_only_override_needs_no_trust(self):
        self.write(self.user_path(),
                   b'[[lanes.review]]\nkey = "g"\nmodel = "m"\ncommand = "echo {model}"\n')
        self.write(self.project_path(),
                   b'[lanes]\nstrategy = "local-only"\n'
                   b'[[lanes.review]]\nkey = "g"\nruntime = "codex"\nmodel = "p"\n')
        resolved = self.resolve()["review"]
        self.assertEqual([(e["key"], e["model"]) for e in resolved], [("g", "p")])
        self.assertNotIn("command", resolved[0])
        self.assertEqual(self.warnings, [])

    def test_duplicate_key_row_drops_trust(self):
        base = b'[[lanes.review]]\nkey = "x"\ncommand = "{tool} --check"\ntool = "safe"\n'
        self.write(self.project_path(), base)
        config_io.cfg_trust_project(self.cwd, self.env)
        self.assertEqual(self.resolve()["review"][0]["tool"], "safe")
        before = config_io.cfg_project_trust_bytes(_lanes(base), self.env)
        tampered = base + b'[[lanes.review]]\nkey = "x"\ntool = "evil"\n'
        self.write(self.project_path(), tampered)
        after = config_io.cfg_project_trust_bytes(_lanes(tampered), self.env)
        self.assertNotEqual(before, after)
        resolved = self.resolve()
        self.assertTrue(self.untrusted_warnings())
        self.assertFalse(any(e.get("tool") == "evil"
                             for e in resolved["review"] + resolved["reviewers"]))

    def test_duplicate_execute_row_drops_trust(self):
        base = b'[[lanes.execute]]\nkey = "x"\ncommand = "{tool} --check"\ntool = "safe"\n'
        self.write(self.project_path(), base)
        config_io.cfg_trust_project(self.cwd, self.env)
        self.assertEqual(self.resolve()["execute"][0]["tool"], "safe")
        tampered = base + b'[[lanes.execute]]\nkey = "x"\ntool = "evil"\n'
        self.write(self.project_path(), tampered)
        resolved = self.resolve()
        self.assertTrue(self.untrusted_warnings())
        self.assertFalse(any(e.get("tool") == "evil"
                             for e in resolved["execute"] + resolved["reviewers"]))


class TestMigrationThroughResolve(_LayerCase):
    def _legacy_custom(self):
        raw = ('[[reviewers]]\nkey = "c"\nmodel = "m"\ncommand = '
               + json.dumps(sys.executable + " -c pass {model}") + "\n").encode()
        legacy = config_migrate.legacy_path(self.project_path())
        self.write(legacy, raw)
        return legacy, raw

    def test_trusted_legacy_roster_resolves_its_command_after_migration(self):
        legacy, raw = self._legacy_custom()
        trust.record_trust(config_migrate.legacy_trust_dir(self.store),
                           os.path.realpath(legacy), raw)
        resolved = self.resolve()
        self.assertTrue(os.path.exists(self.project_path()))
        self.assertTrue(os.path.exists(legacy + ".migrated"))
        self.assertEqual(self.keys(resolved["review"]), ["c"])
        self.assertIn("command", resolved["review"][0])
        self.assertEqual(self.untrusted_warnings(), [])

    def test_untrusted_legacy_roster_entry_is_absent(self):
        self._legacy_custom()
        resolved = self.resolve()
        self.assertTrue(os.path.exists(self.project_path()))
        self.assertEqual(resolved["review"], [])
        self.assertFalse(any(e.get("key") == "c" for e in resolved["reviewers"]))
        self.assertTrue(self.untrusted_warnings())

    def test_local_only_legacy_project_leaves_the_user_legacy_file_alone(self):
        self.write(config_migrate.legacy_path(self.project_path()),
                   b'strategy = "local-only"\n[[reviewers]]\nkey = "l"\n'
                   b'runtime = "codex"\nmodel = "m"\n')
        user_legacy = self.write(self.user_path("review-spec.toml"),
                                 b'[[reviewers]]\nkey = "u"\nruntime = "codex"\nmodel = "m"\n')
        before = _read(user_legacy)
        resolved = self.resolve()
        self.assertEqual(self.keys(resolved["review"]), ["l"])
        self.assertEqual(_read(user_legacy), before)
        self.assertFalse(os.path.exists(self.user_path()))
        self.assertTrue(os.path.exists(self.project_path()))


class TestReadOnlyMode(_LayerCase):
    def test_probe_quota_no_migrate_reports_pending_and_writes_nothing(self):
        legacy_project = self.write(config_migrate.legacy_path(self.project_path()),
                                    b'[[reviewers]]\nkey = "p"\nruntime = "codex"\n'
                                    b'model = "m"\n')
        legacy_user = self.write(self.user_path("review-spec.toml"),
                                 b'[[reviewers]]\nkey = "u"\nruntime = "codex"\nmodel = "m"\n')

        def rec(spec, prompt, seams):
            del spec, prompt, seams
            return _probe_ok()

        quota_path = os.path.join(self.cwd, "quota.json")
        err = io.StringIO()
        with redirect_stdout(io.StringIO()), redirect_stderr(err):
            code = cli.main(["probe-quota", "--cwd", self.cwd, "--quota-path", quota_path,
                             "--no-save-runtimes", "--no-migrate"],
                            runner_fn=rec, custom_fn=rec, env_fn=lambda: dict(self.env),
                            **NO_RUNTIMES)
        self.assertEqual(code, 0)
        self.assertIn("migration pending", err.getvalue())
        self.assertTrue(os.path.exists(legacy_project))
        self.assertTrue(os.path.exists(legacy_user))
        self.assertFalse(os.path.exists(self.project_path()))
        self.assertFalse(os.path.exists(self.user_path()))


class TestTrustLocalNothingToTrust(_LayerCase):
    def test_runtime_only_lanes_have_nothing_to_trust(self):
        self.write(self.project_path(),
                   b'[[lanes.review]]\nkey = "r"\nruntime = "codex"\nmodel = "m"\n')
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = cli.main(["trust-local", "--cwd", self.cwd])
        self.assertEqual(code, 0)
        self.assertIn("nothing to trust:", out.getvalue())
        self.assertFalse(os.path.exists(self.store))


class TestTrustLocalRevokeLegacy(_LayerCase):
    def test_revoke_before_first_migration_stays_revoked(self):
        legacy = config_migrate.legacy_path(self.project_path())
        raw = ('[[reviewers]]\nkey = "c"\nmodel = "m"\ncommand = '
               + json.dumps(sys.executable + " -c pass {model}") + "\n").encode()
        self.write(legacy, raw)
        trust.record_trust(config_migrate.legacy_trust_dir(self.store),
                           os.path.realpath(legacy), raw)
        out = io.StringIO()
        with redirect_stdout(out), redirect_stderr(io.StringIO()):
            code = cli.main(["trust-local", "--cwd", self.cwd, "--revoke"])
        self.assertEqual(code, 0)
        self.assertIn("revoked 1 trust record(s)", out.getvalue())
        self.assertTrue(os.path.exists(legacy))
        self.assertFalse(os.path.exists(self.project_path()))
        resolved = config_io.cfg_resolve(self.cwd, self.env, warn_fn=self.warnings.append)
        self.assertTrue(os.path.exists(self.project_path()))
        self.assertTrue(os.path.exists(legacy + ".migrated"))
        self.assertTrue(self.untrusted_warnings())
        self.assertFalse(any(e.get("key") == "c"
                             for e in resolved["review"] + resolved["reviewers"]))
        self.assertFalse(os.path.isdir(self.store) and os.listdir(self.store))


if __name__ == "__main__":
    unittest.main()
