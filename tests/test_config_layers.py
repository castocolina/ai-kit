"""config.toml: the layered reader, role-keyed lanes, the D-11 trust rule and read-only mode
(Plan 33-07; SPEC R2, R3, R4, R5; D-10, D-11, D-24).

Every test uses its own temporary cwd, HOME and XDG_CONFIG_HOME, never the real user config.
Fixtures are synthetic and carry no secret value.
"""

import copy
import difflib
import io
import json
import os
import sys
import tempfile
import tomllib
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
        # effort is model-bound (36 contract item 6): it was set for model u, so it is dropped
        self.assertNotIn("effort", entry)


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
        self.env[config_migrate.KEEP_BACKUP_ENV] = "1"
        legacy, raw = self._legacy_custom()
        trust.record_trust(config_migrate.legacy_trust_dir(self.store),
                           os.path.realpath(legacy), raw)
        resolved = self.resolve()
        self.assertTrue(os.path.exists(self.project_path()))
        self.assertTrue(os.path.exists(legacy + ".migrated"))
        self.assertEqual(self.keys(resolved["review"]), ["c"])
        self.assertIn("command", resolved["review"][0])
        self.assertEqual(self.untrusted_warnings(), [])

    def test_verified_migration_deletes_the_old_roster_by_default(self):
        legacy = self.write(config_migrate.legacy_path(self.project_path()),
                            b'[[reviewers]]\nkey = "d"\nruntime = "codex"\n'
                            b'model = "placeholder-model-1"\n')
        self.assertEqual(self.keys(self.resolve()["review"]), ["d"])
        self.assertFalse(os.path.exists(legacy))
        self.assertFalse(os.path.exists(legacy + ".migrated"))
        self.assertTrue(any("the old file was deleted" in w for w in self.warnings))

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


class TestProjectConfigLink(_LayerCase):
    """CR-01: a project config.toml that links to the user config.toml is never written."""

    EVIL = (b'[[reviewers]]\nkey = "evil"\nmodel = "m"\n'
            b'command = "sh -c touch-pwned {prompt}"\n')

    def _link(self, user_text):
        if user_text is not None:
            self.write(self.user_path(), user_text)
        else:
            os.makedirs(os.path.dirname(self.user_path()), exist_ok=True)
        self.write(config_migrate.legacy_path(self.project_path()), self.EVIL)
        os.symlink(self.user_path(), self.project_path())

    def _assert_refused(self, user_text):
        self._link(user_text)
        before = _read(self.user_path()) if user_text is not None else None
        with self.assertRaises(config_io.ConfigError) as caught:
            self.resolve()
        self.assertIn(self.project_path(), str(caught.exception))
        if before is None:
            self.assertFalse(os.path.exists(self.user_path()))
        else:
            self.assertEqual(_read(self.user_path()), before)

    def test_link_to_an_absent_user_config_is_refused_and_nothing_is_written(self):
        self._assert_refused(None)

    def test_link_to_a_runner_only_user_config_leaves_it_unchanged(self):
        self._assert_refused(b"[runner.retry]\nattempts = 3\n")

    def test_linked_old_roster_is_refused(self):
        outside = self.write(os.path.join(self.root, "elsewhere.toml"), self.EVIL)
        os.makedirs(os.path.dirname(self.project_path()), exist_ok=True)
        os.symlink(outside, config_migrate.legacy_path(self.project_path()))
        with self.assertRaises(config_io.ConfigError):
            self.resolve()
        self.assertFalse(os.path.exists(self.project_path()))

    def test_trust_local_refuses_a_linked_project_config(self):
        self._link(b'[[lanes.review]]\nkey = "e"\ncommand = "x"\n')
        err = io.StringIO()
        with redirect_stdout(io.StringIO()), redirect_stderr(err):
            code = cli.main(["trust-local", "--cwd", self.cwd])
        self.assertEqual(code, 2)
        self.assertFalse(os.path.isdir(self.store) and os.listdir(self.store))

    def test_render_toml_out_refuses_a_linked_project_config(self):
        self._link(b"[runner.retry]\nattempts = 3\n")
        before = _read(self.user_path())
        config = os.path.join(self.root, "cfg.json")
        self.write(config, b'{"lanes": [{"key": "a", "runtime": "codex", "model": "m1"}]}')
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            code = cli.main(["render-toml", "--json-config", config, "--out",
                             self.project_path(), "--replace"])
        self.assertEqual(code, 2)
        self.assertEqual(_read(self.user_path()), before)

    def test_trust_local_trusts_an_in_repo_link_with_nothing_to_migrate(self):
        # WR-101: the guard belongs to the migration; a link with no old roster is only read.
        target = self.write(os.path.join(os.path.dirname(self.project_path()), "lanes.toml"),
                            b'[[lanes.review]]\nkey = "e"\ncommand = "x {prompt}"\n')
        os.symlink(target, self.project_path())
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            code = cli.main(["trust-local", "--cwd", self.cwd])
        self.assertEqual(code, 0)
        self.assertTrue(os.listdir(self.store))

    def test_render_toml_refuses_a_project_aikit_dir_linked_to_the_user_folder(self):
        # WR-102: `.aikit` itself links to the user config folder; the write is refused.
        user_dir = os.path.dirname(self.user_path())
        self.write(self.user_path(), b"[runner.retry]\nattempts = 3\n")
        os.symlink(user_dir, os.path.dirname(self.project_path()))
        before = _read(self.user_path())
        config = os.path.join(self.root, "cfg.json")
        self.write(config, b'{"lanes": [{"key": "a", "runtime": "codex", "model": "m1"}]}')
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            code = cli.main(["render-toml", "--json-config", config, "--out",
                             self.project_path(), "--replace"])
        self.assertEqual(code, 2)
        self.assertEqual(_read(self.user_path()), before)

    def test_a_regular_project_config_still_migrates(self):
        self.write(config_migrate.legacy_path(self.project_path()), self.EVIL)
        self.resolve()
        self.assertTrue(os.path.exists(self.project_path()))
        self.assertFalse(os.path.islink(self.project_path()))


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


class TestProbeQuotaReviewOrder(_LayerCase):
    def test_probe_quota_probes_the_shared_ladders_review_lanes(self):
        self.write(self.user_path(),
                   b'[lanes.policy]\nladder = ["r1", "e1", "r2"]\n'
                   b'[[lanes.review]]\nkey = "r1"\nmodel = "placeholder-model-1"\n'
                   b'command = "placeholder-cli-1 {model}"\n'
                   b'[[lanes.review]]\nkey = "r2"\nmodel = "placeholder-model-2"\n'
                   b'command = "placeholder-cli-1 {model}"\n'
                   b'[[lanes.execute]]\nkey = "e1"\nmodel = "placeholder-model-3"\n'
                   b'command = "placeholder-cli-1 {model}"\n')
        seen = []
        def rec(spec, prompt, seams):
            seen.append(spec.key)
            return _probe_ok()
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            code = cli.main(["probe-quota", "--cwd", self.cwd, "--quota-path",
                             os.path.join(self.root, "quota.json"), "--no-save-runtimes"],
                            runner_fn=rec, custom_fn=rec, env_fn=lambda: dict(self.env),
                            **NO_RUNTIMES)
        self.assertEqual(code, 0)
        self.assertEqual(seen, ["r1", "r2"])

    def test_resolve_reviewers_routes_a_shared_key_by_its_review_lane(self):
        self.write(self.user_path(),
                   b'[lanes.policy.review]\nladder = ["k"]\n'
                   b'[[lanes.review]]\nkey = "k"\nmodel = "placeholder-model-1"\n'
                   b'command = "placeholder-cli-1 {model}"\n')
        self.write(self.project_path(),
                   b'[[lanes.execute]]\nkey = "k"\nruntime = "codex"\n'
                   b'model = "placeholder-model-6"\n')
        out = io.StringIO()
        with redirect_stdout(out), redirect_stderr(io.StringIO()):
            code = cli.main(["resolve-reviewers", "--cwd", self.cwd, "--cross-ai",
                             "--quota-path", os.path.join(self.root, "quota.json")],
                            env_fn=lambda: dict(self.env), **NO_RUNTIMES)
        self.assertEqual(code, 0)
        rows = json.loads(out.getvalue())
        self.assertEqual(len(rows), 1)
        for key, value in (("key", "k"), ("model", "placeholder-model-1"),
                           ("command", "placeholder-cli-1 {model}"), ("route", "custom")):
            self.assertEqual(rows[0][key], value)


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


class TestTrustLocalOneRead(_LayerCase):
    SHOWN = b'[[lanes.review]]\nkey = "c"\ncommand = "echo shown {model}"\nmodel = "m"\n'

    def test_trust_covers_the_bytes_that_were_read_and_shown(self):
        evil = self.SHOWN.replace(b"shown", b"evil")
        self.write(self.project_path(), self.SHOWN)
        real_read = cli.cfg_read_bytes

        def read_then_swap(path):
            raw = real_read(path)
            self.write(path, evil)  # an edit right after the one read
            return raw

        out = io.StringIO()
        with mock.patch.object(cli, "cfg_read_bytes", read_then_swap), \
                redirect_stdout(out), redirect_stderr(io.StringIO()):
            code = cli.main(["trust-local", "--cwd", self.cwd])
        self.assertEqual(code, 0)
        self.assertIn("shown", out.getvalue())
        self.assertNotIn("evil", out.getvalue())
        real = os.path.realpath(self.project_path())
        for raw, expect in ((self.SHOWN, True), (evil, False)):
            canonical = config_io.cfg_project_trust_bytes(_lanes(raw), self.env)
            assert canonical is not None  # both files carry a command entry
            self.assertEqual(trust.is_trusted(self.store, real, canonical), expect)


class TestTrustLocalRevokeLegacy(_LayerCase):
    def test_revoke_before_first_migration_stays_revoked(self):
        self.env[config_migrate.KEEP_BACKUP_ENV] = "1"
        os.environ[config_migrate.KEEP_BACKUP_ENV] = "1"
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


class TestLaneWriter(unittest.TestCase):
    """cfg_render_lanes writes the roster through toml_splice and keeps the rest of the file
    (D-08, D-24; SPEC R3, R9). It is pure text: no path, HOME or cwd is involved."""

    ROSTER = {
        "policy": {"mode": "single", "ladder": ["a", "b", "c"]},
        "lanes": [
            {"key": "a", "runtime": "codex", "model": "m1"},
            {"key": "b", "runtime": "codex", "model": "m2"},
            {"key": "c", "runtime": "codex", "model": "m3"},
        ],
    }
    EXISTING = (
        "# my top comment\n"
        "[runner.retry]\n"
        "  max_attempts   =  3\n"
        "[foo]\n"
        "bar = 1\n"
        "# Priority fallback order (first available reviewer wins the\n"
        "# primary slot):\n"
        "#   1. a\n"
        "#   2. b\n"
        "#   3. c\n"
        "[lanes.policy]\n"
        'mode = "single"\n'
        'ladder = ["a", "b", "c"]\n'
        "[[lanes.review]]\n"
        'key = "a"\nruntime = "codex"\nmodel = "m1"\n'
        "[[lanes.review]]\n"
        'key = "b"\nruntime = "codex"\nmodel = "m2"\n'
        "[[lanes.review]]\n"
        'key = "c"\nruntime = "codex"\nmodel = "m3"\n'
    )

    @staticmethod
    def _changed(before, after):
        diff = list(difflib.ndiff(before.splitlines(keepends=True),
                                  after.splitlines(keepends=True)))
        return [line for line in diff if line.startswith(("- ", "+ "))]

    def test_one_model_change_is_one_line(self):
        changed = copy.deepcopy(self.ROSTER)
        changed["lanes"][1]["model"] = "m2x"
        after = config_io.cfg_render_lanes(changed, self.EXISTING)
        self.assertEqual(self._changed(self.EXISTING, after),
                         ['- model = "m2"\n', '+ model = "m2x"\n'])

    def test_entries_file_by_purpose_and_keep_their_order(self):
        config = {"lanes": [
            {"key": "a", "runtime": "codex", "model": "m1"},
            {"key": "b", "runtime": "codex", "model": "m2", "purpose": "execute"},
            {"key": "c", "runtime": "codex", "model": "m3", "purpose": "both"},
        ]}
        parsed = tomllib.loads(config_io.cfg_render_lanes(config, ""))["lanes"]
        self.assertEqual([e["key"] for e in parsed["review"]], ["a", "c"])
        self.assertEqual([e["key"] for e in parsed["execute"]], ["b", "c"])
        self.assertEqual(parsed["execute"][1]["purpose"], "both")

    def test_empty_existing_text_gives_only_the_lanes_tables(self):
        parsed = tomllib.loads(config_io.cfg_render_lanes(self.ROSTER, ""))
        self.assertEqual(set(parsed), {"lanes"})
        self.assertEqual(parsed["lanes"]["policy"], {"mode": "single", "ladder": ["a", "b", "c"]})
        self.assertEqual([e["key"] for e in parsed["lanes"]["review"]], ["a", "b", "c"])

    def test_reviewers_json_key_is_refused(self):
        config = {"reviewers": [{"key": "a", "runtime": "codex", "model": "m"}]}
        with self.assertRaises(ValueError) as ctx:
            config_io.cfg_render_lanes(config, "")
        self.assertTrue(str(ctx.exception).startswith(
            "render-toml: the JSON key 'reviewers' is now 'lanes'"))

    def test_invalid_entry_is_dropped_from_roster_and_ladder_with_a_warning(self):
        config = {"policy": {"mode": "single", "ladder": ["a", "x"]}, "lanes": [
            {"key": "a", "runtime": "codex", "model": "m1"},
            {"key": "x", "runtime": "codex", "model": "m2", "route": "native"},
        ]}
        err = io.StringIO()
        with redirect_stderr(err):
            text = config_io.cfg_render_lanes(config, "")
        parsed = tomllib.loads(text)["lanes"]
        self.assertEqual([e["key"] for e in parsed["review"]], ["a"])
        self.assertEqual(parsed["policy"]["ladder"], ["a"])
        self.assertIn("WARNING: 2 issue(s) found and NOT written", err.getvalue())
        self.assertIn("'route' is decided per run", err.getvalue())

    def test_rendering_the_same_roster_again_is_byte_equal(self):
        first = config_io.cfg_render_lanes(self.ROSTER, "")
        self.assertEqual(config_io.cfg_render_lanes(self.ROSTER, first), first)

    def test_unknown_lanes_key_and_unknown_table_are_byte_equal(self):
        existing = ('[lanes]\nextra = 1\n\n[foo]\nbar = "x"  # keep this\n\n'
                    '[lanes.policy]\nmode = "single"\nladder = ["a"]\n\n'
                    '[[lanes.review]]\nkey = "a"\nruntime = "codex"\nmodel = "m1"\n')
        config = {"policy": {"mode": "single", "ladder": ["a"]},
                  "lanes": [{"key": "a", "runtime": "codex", "model": "m2"}]}
        after = config_io.cfg_render_lanes(config, existing)
        self.assertIn('[foo]\nbar = "x"  # keep this\n', after)
        self.assertIn("[lanes]\nextra = 1\n", after)
        self.assertIn('model = "m2"', after)

    def test_strategy_is_written_beside_role_arrays_of_an_existing_lanes_table(self):
        existing = '[lanes]\nstrategy = "global-merge"\n\n' + self.EXISTING
        config = dict(self.ROSTER, strategy="local-only")
        parsed = tomllib.loads(config_io.cfg_render_lanes(config, existing))["lanes"]
        self.assertEqual(parsed["strategy"], "local-only")
        self.assertEqual([e["key"] for e in parsed["review"]], ["a", "b", "c"])

    def test_first_write_puts_the_generated_ladder_block_above_the_policy(self):
        config = {"policy": {"mode": "single", "ladder": ["a", "b"]},
                  "lanes": [{"key": "a", "runtime": "codex", "model": "m1"},
                            {"key": "b", "runtime": "codex", "model": "m2"}]}
        text = config_io.cfg_render_lanes(config, "")
        self.assertIn("# Priority fallback order (first available reviewer wins the\n"
                      "# primary slot):\n#   1. a\n#   2. b\n[lanes.policy]\n", text)
        config["policy"]["ladder"] = ["b", "a"]
        reordered = config_io.cfg_render_lanes(config, text)
        self.assertIn("#   1. b\n#   2. a\n[lanes.policy]\n", reordered)
        changed = self._changed(text, reordered)
        self.assertTrue(changed)
        self.assertTrue(all("#" in line or "ladder" in line for line in changed))

    def test_user_comment_above_the_policy_is_kept_and_no_block_is_added(self):
        existing = ('# my note\n[lanes.policy]\nmode = "single"\nladder = ["a"]\n'
                    '[[lanes.review]]\nkey = "a"\nruntime = "codex"\nmodel = "m1"\n')
        config = {"policy": {"mode": "single", "ladder": ["a"]},
                  "lanes": [{"key": "a", "runtime": "codex", "model": "m1"}]}
        text = config_io.cfg_render_lanes(config, existing)
        self.assertTrue(text.startswith("# my note\n[lanes.policy]\n"))
        self.assertNotIn("# Priority fallback order", text)


class TestRenderTomlCli(_LayerCase):
    """render-toml --out: the guard runs before any write (C1-16, C1-17, C1-18).

    An old roster beside the target migrates only once the guard passes; a broken target is
    exit 2 (D-08, D-10)."""

    ROSTER = {"policy": {"mode": "single", "ladder": ["a"]},
              "lanes": [{"key": "a", "runtime": "codex", "model": "m1"}]}

    def _json(self, config):
        path = os.path.join(self.root, "render.json")
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(config, handle)
        return path

    def _render(self, out, *extra, config=None):
        err = io.StringIO()
        with redirect_stdout(io.StringIO()), redirect_stderr(err):
            code = cli.main(["render-toml", "--json-config", self._json(config or self.ROSTER),
                             "--out", out, *extra])
        return code, err.getvalue()

    def test_other_tables_are_kept_and_no_replace_is_needed(self):
        target = self.project_path()
        runner = '[runner.retry]\n  base_s   =  1  # keep\n'
        self.write(target, runner.encode())
        code, _ = self._render(target)
        self.assertEqual(code, 0)
        with open(target, encoding="utf-8") as handle:
            text = handle.read()
        self.assertTrue(text.startswith(runner))
        self.assertIn("[lanes.policy]", text)

    def test_legacy_roster_beside_the_target_is_refused_and_nothing_is_written(self):
        old = b'[[reviewers]]\nkey = "old"\nruntime = "codex"\nmodel = "m"\n'
        legacy = self.write(config_migrate.legacy_path(self.project_path()), old)
        self._json(self.ROSTER)  # the JSON input is not part of the write under test
        before = self.tree()
        code, err = self._render(self.project_path())
        self.assertEqual(code, 1)
        self.assertIn("refusing to replace the old roster", err)
        self.assertIn("(nothing written)", err)
        self.assertEqual(self.tree(), before)
        self.assertEqual(_read(legacy), old)
        self.assertFalse(os.path.exists(legacy + ".migrated"))
        self.assertFalse(os.path.exists(self.project_path()))

    def test_other_out_name_neither_refuses_nor_migrates_a_sibling_roster(self):
        old = b'[[reviewers]]\nkey = "old"\nruntime = "codex"\nmodel = "m"\n'
        legacy = self.write(config_migrate.legacy_path(self.project_path()), old)
        preview = os.path.join(os.path.dirname(self.project_path()), "preview.toml")
        code, _err = self._render(preview, "--replace")
        self.assertEqual(code, 0)
        self.assertEqual(_read(legacy), old)
        self.assertFalse(os.path.exists(legacy + ".migrated"))
        self.assertFalse(os.path.exists(self.project_path()))
        self.assertTrue(os.path.exists(preview))
        code, _err = self._render(os.path.join(os.path.dirname(preview), "preview2.toml"))
        self.assertEqual(code, 0)  # no --replace needed: no roster migrates into this name

    def test_legacy_roster_beside_the_target_migrates_with_replace(self):
        legacy = self.write(config_migrate.legacy_path(self.project_path()),
                            b'[[reviewers]]\nkey = "old"\nruntime = "codex"\nmodel = "m"\n')
        code, err = self._render(self.project_path(), "--replace", "--keep-backup")
        self.assertEqual(code, 0)
        self.assertIn("migrated", err)
        self.assertEqual(_read(legacy + ".migrated"),
                         b'[[reviewers]]\nkey = "old"\nruntime = "codex"\nmodel = "m"\n')
        self.assertFalse(os.path.exists(legacy))
        parsed = config_io.cfg_load_toml(self.project_path())
        self.assertEqual([e["key"] for e in parsed["lanes"]["review"]], ["a"])

    def test_legacy_roster_migrates_with_replace_and_deletes_by_default(self):
        os.environ.pop(config_migrate.KEEP_BACKUP_ENV, None)
        legacy = self.write(config_migrate.legacy_path(self.project_path()),
                            b'[[reviewers]]\nkey = "old"\nruntime = "codex"\n'
                            b'model = "placeholder-model-1"\n')
        code, err = self._render(self.project_path(), "--replace")
        self.assertEqual(code, 0)
        self.assertFalse(os.path.exists(legacy))
        self.assertFalse(os.path.exists(legacy + ".migrated"))
        self.assertIn("the old file was deleted", err)
        self.assertEqual(self.keys(config_io.cfg_load_toml(self.project_path())['lanes']['review']),
                         ["a"])

    def test_broken_target_is_exit_2_and_stays_byte_equal(self):
        target = self.project_path()
        self.write(target, b"[[[")
        code, err = self._render(target)
        self.assertEqual(code, 2)
        self.assertIn("config error", err)
        self.assertEqual(_read(target), b"[[[")

    def test_non_utf8_target_is_exit_2_and_stays_byte_equal(self):
        target = self.project_path()
        self.write(target, b"\xff\xfe")
        code, _ = self._render(target)
        self.assertEqual(code, 2)
        self.assertEqual(_read(target), b"\xff\xfe")

    def test_reviewers_json_key_is_refused_with_the_rename_message(self):
        config = {"reviewers": [{"key": "a", "runtime": "codex", "model": "m"}]}
        code, err = self._render(self.project_path(), config=config)
        self.assertEqual(code, 1)
        self.assertTrue(err.startswith(
            "render-toml: the JSON key 'reviewers' is now 'lanes'"))
        self.assertFalse(os.path.exists(self.project_path()))

    def test_interrupted_publish_leaves_the_old_file_byte_equal(self):
        target = self.project_path()
        original = b"# my note\n[runner.retry]\nbase_s = 1\n"
        self.write(target, original)
        with mock.patch("ai_kit_spec.cache.os.replace", side_effect=OSError("interrupted")), \
                self.assertRaises(OSError):
            self._render(target)
        self.assertEqual(_read(target), original)


if __name__ == "__main__":
    unittest.main()
