"""Roster migration tests (Plan 33-05, SPEC R4 and R5): config_migrate.migrate_layer, the trust
carry to the canonical command-lane digest, the interruption and concurrency rules and the
canonical bytes of trust.command_lanes_bytes.

Every test builds its own temporary project, user folder and trust store and passes them
explicitly; none reads the real roster, the live .aikit/ or ~/.config/ai-kit.
"""

import json
import os
import sys
import tempfile
import tomllib
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills", "ai-kit-spec-review"))

from ai_kit_spec import config_migrate, toml_splice, trust
from ai_kit_spec.config_migrate import LegacyRosterError

LOCAL_ROSTER = (
    "# Local reviewers for this project.\n"
    'strategy = "local-only"\n'
    "\n"
    "# Mode of the review.\n"
    "[policy]\n"
    "# single reviewer\n"
    'mode = "single"\n'
    'ladder = ["a"]\n'
    "\n"
    "# first reviewer\n"
    "[[reviewers]]\n"
    'key = "a"\n'
    'model = "m1"\n'
    'vendor = "v"\n'
    'cli = "codex"\n'
    "\n"
    "# coding lane\n"
    "[[reviewers]]\n"
    'key = "b"\n'
    'model = "m2"\n'
    'vendor = "v"\n'
    'runtime = "codex"\n'
    'purpose = "execute"\n'
)
COMMAND_ROSTER = (
    "[[reviewers]]\n"
    'key = "x"\n'
    'model = "m"\n'
    'command = "{tool} run {model}"\n'
    'tool = "safe"\n'
)
RETRY_TEXT = "[runner.retry]\nmax_retries = 2\n"


def canonical_bytes(lanes: dict, user_command_keys: frozenset = frozenset()) -> bytes:
    """trust.command_lanes_bytes for lanes holding a command-bearing entry (all fixtures do)."""
    raw = trust.command_lanes_bytes(lanes, user_command_keys)
    if raw is None:
        raise AssertionError("expected a command-bearing lane entry")
    return raw


class MigrationCase(unittest.TestCase):
    """One temporary project (.aikit/), user folder (XDG ai-kit) and trust store per test."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        root = self._tmp.name
        self.project = os.path.join(root, "project", ".aikit")
        self.user = os.path.join(root, "xdg", "ai-kit")
        self.store = os.path.join(self.user, "config-trust")
        self.local_config = os.path.join(self.project, "config.toml")
        self.local_old = os.path.join(self.project, "review-spec.toml")
        self.user_config = os.path.join(self.user, "config.toml")
        self.user_old = os.path.join(self.user, "review-spec.toml")
        self.warnings = []

    def write(self, path: str, text: str) -> None:
        self.write_bytes(path, text.encode("utf-8"))

    def write_bytes(self, path: str, raw: bytes) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as handle:
            handle.write(raw)

    def read(self, path: str) -> str:
        with open(path, encoding="utf-8", newline="") as handle:
            return handle.read()

    def read_bytes(self, path: str) -> bytes:
        with open(path, "rb") as handle:
            return handle.read()

    def migrate(self, config: str | None = None, **kwargs) -> str:
        return config_migrate.migrate_layer(
            config or self.local_config, warn_fn=self.warnings.append, **kwargs)

    def trust_kwargs(self) -> dict:
        return {"trust_dir": self.store,
                "trust_bytes_fn": lambda lanes: trust.command_lanes_bytes(lanes, frozenset())}

    def expected_lanes(self, roster: str) -> dict:
        return config_migrate.lanes_from_legacy(tomllib.loads(roster))

    def lanes(self, path: str) -> dict:
        return tomllib.loads(self.read(path))["lanes"]

    def record_legacy_trust(self, raw: bytes) -> None:
        """Write the local old roster with `raw` and trust it under the old rule."""
        self.write_bytes(self.local_old, raw)
        trust.record_trust(config_migrate.legacy_trust_dir(self.store),
                           os.path.realpath(self.local_old), raw)

    def store_has_records(self) -> bool:
        return os.path.isdir(self.store) and any(
            name.endswith(".json") for name in os.listdir(self.store))

    def stamp(self, path: str):
        return self.read_bytes(path), os.stat(path).st_mtime_ns


class TestTracer(MigrationCase):
    def test_local_roster_migrates_into_config_toml(self):
        self.write(self.local_old, LOCAL_ROSTER)
        state = self.migrate()
        self.assertEqual(state, "migrated")
        new_text = self.read(self.local_config)
        self.assertEqual(tomllib.loads(new_text)["lanes"], self.expected_lanes(LOCAL_ROSTER))
        self.assertIn("# Local reviewers for this project.", new_text)
        self.assertIn("# coding lane", new_text)
        self.assertFalse(os.path.exists(self.local_old))
        migrated = self.local_old + config_migrate.MIGRATED_SUFFIX
        self.assertEqual(self.read_bytes(migrated), LOCAL_ROSTER.encode("utf-8"))
        self.assertEqual(len(self.warnings), 1)
        self.assertIn(self.local_old, self.warnings[0])
        self.assertIn(self.local_config, self.warnings[0])

    def test_split_by_purpose_maps_each_entry_to_its_roles(self):
        entries = [
            {"key": "a"},
            {"key": "b", "purpose": "execute"},
            {"key": "c", "purpose": "both"},
            {"key": "d", "purpose": "review"},
        ]
        review, execute = config_migrate.split_by_purpose(entries)
        self.assertEqual([entry["key"] for entry in review], ["a", "c", "d"])
        self.assertEqual([entry["key"] for entry in execute], ["b", "c"])

    def test_command_lanes_bytes_is_canonical_json_of_command_entries(self):
        lanes = {
            "review": [{"key": "a", "command": "x {model}"}, {"key": "b"}],
            "execute": [{"key": "c", "command": "y"}],
        }
        expected = (b'[["execute",{"command":"y","key":"c"}],'
                    b'["review",{"command":"x {model}","key":"a"}]]')
        self.assertEqual(trust.command_lanes_bytes(lanes, frozenset()), expected)
        with_user = canonical_bytes(lanes, frozenset({"b"}))
        self.assertEqual(json.loads(with_user),
                         [["execute", {"command": "y", "key": "c"}],
                          ["review", {"command": "x {model}", "key": "a"}],
                          ["review", {"key": "b"}]])
        self.assertIsNone(trust.command_lanes_bytes({"review": [{"key": "a"}]}, frozenset()))

    def test_entries_sharing_a_command_key_are_in_the_digest(self):
        lanes = {"review": [{"key": "x", "command": "{tool} --check", "tool": "safe"},
                            {"key": "x", "tool": "evil"}]}
        raw = canonical_bytes(lanes)
        self.assertEqual(len(json.loads(raw)), 2)
        lanes["review"][1]["tool"] = "other"
        self.assertNotEqual(trust.command_lanes_bytes(lanes, frozenset()), raw)
        cross_role = {"review": [{"key": "x", "command": "{tool} --check"}],
                      "execute": [{"key": "x", "model": "m"}]}
        self.assertEqual(len(json.loads(canonical_bytes(cross_role))), 2)


class TestLayers(MigrationCase):
    def test_global_only_migrates_without_trust(self):
        self.write(self.user_old, LOCAL_ROSTER)
        self.assertEqual(self.migrate(self.user_config), "migrated")
        self.assertEqual(self.lanes(self.user_config), self.expected_lanes(LOCAL_ROSTER))
        self.assertFalse(os.path.exists(self.user_old))
        self.assertFalse(self.store_has_records())

    def test_local_and_global_migrate_independently(self):
        self.write(self.local_old, LOCAL_ROSTER)
        self.write(self.user_old, LOCAL_ROSTER.replace('key = "a"', 'key = "g"'))
        self.assertEqual(self.migrate(self.local_config), "migrated")
        self.assertEqual(self.migrate(self.user_config), "migrated")
        self.assertEqual(self.lanes(self.local_config)["review"][0]["key"], "a")
        self.assertEqual(self.lanes(self.user_config)["review"][0]["key"], "g")

    def test_existing_user_config_keeps_its_bytes_as_the_prefix(self):
        existing = "# user tuning\n[runner.retry]\n# keep me\nmax_retries = 3\n"
        self.write(self.user_config, existing)
        self.write(self.user_old, LOCAL_ROSTER)
        self.assertEqual(self.migrate(self.user_config), "migrated")
        text = self.read(self.user_config)
        self.assertTrue(text.startswith(existing))
        parsed = tomllib.loads(text)
        self.assertEqual(parsed["runner"]["retry"]["max_retries"], 3)
        self.assertEqual(parsed["lanes"], self.expected_lanes(LOCAL_ROSTER))

    def test_pending_and_read_legacy_report_the_old_roster(self):
        self.assertIsNone(config_migrate.pending(self.local_config))
        self.write(self.local_old, LOCAL_ROSTER)
        self.assertEqual(config_migrate.pending(self.local_config), self.local_old)
        legacy = config_migrate.read_legacy(self.local_config)
        if legacy is None:
            self.fail("the old roster should be read")
        lanes, raw = legacy
        self.assertEqual(raw, LOCAL_ROSTER.encode("utf-8"))
        self.assertEqual(lanes, self.expected_lanes(LOCAL_ROSTER))
        self.assertIsNone(config_migrate.read_legacy(self.user_config))


class TestShapes(MigrationCase):
    def test_local_only_strategy_lands_under_lanes(self):
        self.write(self.local_old, LOCAL_ROSTER)
        self.migrate()
        parsed = tomllib.loads(self.read(self.local_config))
        self.assertEqual(parsed["lanes"]["strategy"], "local-only")
        self.assertNotIn("strategy", parsed)

    def test_legacy_fields_stay_as_written(self):
        self.write(self.local_old, LOCAL_ROSTER)
        self.migrate()
        lanes = self.lanes(self.local_config)
        self.assertEqual(lanes["review"][0]["cli"], "codex")
        self.assertEqual(lanes["execute"][0]["purpose"], "execute")

    def test_both_purpose_appears_in_both_roles(self):
        self.write(self.local_old, '[[reviewers]]\nkey = "c"\nmodel = "m"\npurpose = "both"\n')
        self.migrate()
        lanes = self.lanes(self.local_config)
        self.assertEqual(lanes["review"][0], {"key": "c", "model": "m", "purpose": "both"})
        self.assertEqual(lanes["execute"][0], {"key": "c", "model": "m", "purpose": "both"})

    def test_reviewer_order_stays_within_the_role(self):
        roster = "".join(f'[[reviewers]]\nkey = "{key}"\nmodel = "m"\n' for key in "abc")
        self.write(self.local_old, roster)
        self.migrate()
        self.assertEqual([entry["key"] for entry in self.lanes(self.local_config)["review"]],
                         ["a", "b", "c"])

    def test_entry_sub_tables_follow_their_entry_into_each_role(self):
        roster = ('[[reviewers]]\nkey = "c"\npurpose = "both"\n\n'
                  '# tuning of c\n[reviewers.tuning]\neffort = "high"\n')
        self.write(self.local_old, roster)
        self.migrate()
        lanes = self.lanes(self.local_config)
        self.assertEqual(lanes["review"][0]["tuning"], {"effort": "high"})
        self.assertEqual(lanes["execute"][0]["tuning"], {"effort": "high"})

    def test_empty_old_file_gives_an_empty_lanes_table(self):
        self.write(self.local_old, "")
        self.assertEqual(self.migrate(), "migrated")
        self.assertEqual(tomllib.loads(self.read(self.local_config)), {"lanes": {}})
        self.assertEqual(len(self.warnings), 1)
        self.assertIn(self.local_old, self.warnings[0])

    def test_comment_only_old_file_gives_an_empty_lanes_table(self):
        self.write(self.local_old, "# only a comment\n")
        self.assertEqual(self.migrate(), "migrated")
        self.assertEqual(tomllib.loads(self.read(self.local_config)), {"lanes": {}})
        self.assertEqual(len(self.warnings), 1)

    def test_crlf_old_file_gives_a_crlf_result(self):
        roster = LOCAL_ROSTER.replace("\n", "\r\n")
        self.write(self.local_old, roster)
        self.assertEqual(self.migrate(), "migrated")
        text = self.read(self.local_config)
        self.assertEqual(text.count("\n"), text.count("\r\n"))
        self.assertEqual(tomllib.loads(text)["lanes"], self.expected_lanes(roster))

    def test_inline_reviewers_array_is_refused_and_nothing_is_written(self):
        old = 'reviewers = [{ key = "a", model = "m" }]\n'
        self.write(self.local_old, old)
        with self.assertRaises(LegacyRosterError) as caught:
            self.migrate()
        self.assertIn("inline array", str(caught.exception))
        self.assertFalse(os.path.exists(self.local_config))
        self.assertEqual(self.read(self.local_old), old)


class TestRepeat(MigrationCase):
    def test_second_call_is_none_and_changes_no_byte_or_mtime(self):
        self.write(self.local_old, LOCAL_ROSTER)
        self.assertEqual(self.migrate(), "migrated")
        migrated = self.local_old + config_migrate.MIGRATED_SUFFIX
        before = (self.stamp(self.local_config), self.stamp(migrated))
        self.assertEqual(self.migrate(), "none")
        self.assertEqual((self.stamp(self.local_config), self.stamp(migrated)), before)

    def test_different_lanes_keep_the_new_roster_and_warn_each_run(self):
        other = '[lanes]\nstrategy = "global-merge"\n'
        self.write(self.local_config, other)
        self.write(self.local_old, LOCAL_ROSTER)
        self.assertEqual(self.migrate(), "kept-new")
        self.assertEqual(self.read(self.local_config), other)
        self.assertEqual(self.read(self.local_old), LOCAL_ROSTER)
        self.assertEqual(len(self.warnings), 1)
        self.assertEqual(self.migrate(), "kept-new")
        self.assertEqual(len(self.warnings), 2)

    def test_expected_lanes_already_present_completes_with_the_rename(self):
        self.write(self.local_old, LOCAL_ROSTER)
        self.write(self.local_config, config_migrate.migrate_text(LOCAL_ROSTER))
        self.assertEqual(self.migrate(), "completed")
        self.assertFalse(os.path.exists(self.local_old))
        self.assertTrue(os.path.exists(self.local_old + config_migrate.MIGRATED_SUFFIX))


class TestTrustCarry(MigrationCase):
    def new_digest(self) -> bytes:
        return canonical_bytes(self.lanes(self.local_config))

    def test_trusted_roster_carries_trust_to_the_new_digest(self):
        self.record_legacy_trust(COMMAND_ROSTER.encode("utf-8"))
        self.assertEqual(self.migrate(**self.trust_kwargs()), "migrated")
        self.assertTrue(trust.is_trusted(self.store, os.path.realpath(self.local_config),
                                         self.new_digest()))

    def test_untrusted_roster_gets_no_record(self):
        self.write(self.local_old, COMMAND_ROSTER)
        self.assertEqual(self.migrate(**self.trust_kwargs()), "migrated")
        self.assertFalse(self.store_has_records())

    def test_trusted_roster_without_a_command_records_nothing(self):
        raw = b'[[reviewers]]\nkey = "a"\nmodel = "m"\n'
        self.record_legacy_trust(raw)
        self.assertEqual(self.migrate(**self.trust_kwargs()), "migrated")
        self.assertFalse(self.store_has_records())

    def test_completed_run_never_carries_trust(self):
        self.record_legacy_trust(COMMAND_ROSTER.encode("utf-8"))
        self.write(self.local_config, config_migrate.migrate_text(COMMAND_ROSTER))
        self.assertEqual(self.migrate(**self.trust_kwargs()), "completed")
        self.assertFalse(self.store_has_records())

    def test_user_layer_never_writes_a_trust_record(self):
        self.write(self.user_old, COMMAND_ROSTER)
        self.assertEqual(self.migrate(self.user_config), "migrated")
        self.assertFalse(self.store_has_records())

    def test_revoke_before_first_migration_carries_nothing(self):
        raw = COMMAND_ROSTER.encode("utf-8")
        self.record_legacy_trust(raw)
        self.assertEqual(config_migrate.revoke_legacy_trust(self.local_config, self.store), 1)
        self.assertFalse(trust.is_trusted(config_migrate.legacy_trust_dir(self.store),
                                          os.path.realpath(self.local_old), raw))
        self.assertEqual(self.migrate(**self.trust_kwargs()), "migrated")
        self.assertFalse(self.store_has_records())
        self.assertTrue(os.path.exists(self.local_old + config_migrate.MIGRATED_SUFFIX))

    def test_revoke_without_a_legacy_record_returns_zero(self):
        self.write(self.local_old, COMMAND_ROSTER)
        self.assertEqual(config_migrate.revoke_legacy_trust(self.local_config, self.store), 0)


class TestInterruptions(MigrationCase):
    def test_publish_failure_leaves_the_old_file_and_no_config(self):
        self.write(self.local_old, LOCAL_ROSTER)
        failing = mock.patch.object(toml_splice, "publish", side_effect=OSError("disk full"))
        with failing, self.assertRaises(LegacyRosterError):
            self.migrate()
        self.assertEqual(self.read(self.local_old), LOCAL_ROSTER)
        self.assertFalse(os.path.exists(self.local_config))

    def test_rename_failure_keeps_every_value_in_one_of_the_files(self):
        self.write(self.local_old, LOCAL_ROSTER)
        with mock.patch.object(config_migrate.os, "rename", side_effect=OSError("busy")):
            self.assertEqual(self.migrate(), "migrated")
        self.assertIn("could not rename", self.warnings[-1])
        self.assertEqual(self.lanes(self.local_config), self.expected_lanes(LOCAL_ROSTER))
        self.assertEqual(self.read(self.local_old), LOCAL_ROSTER)
        self.assertEqual(self.migrate(), "completed")
        self.assertFalse(os.path.exists(self.local_old))

    def test_revoke_after_a_failed_rename_stays_revoked(self):
        self.record_legacy_trust(COMMAND_ROSTER.encode("utf-8"))
        with mock.patch.object(config_migrate.os, "rename", side_effect=OSError("busy")):
            self.assertEqual(self.migrate(**self.trust_kwargs()), "migrated")
        digest = canonical_bytes(self.lanes(self.local_config))
        self.assertTrue(trust.is_trusted(self.store, os.path.realpath(self.local_config), digest))
        self.assertEqual(trust.revoke_trust(self.store, os.path.realpath(self.local_config)), 1)
        self.assertEqual(self.migrate(**self.trust_kwargs()), "completed")
        self.assertFalse(trust.is_trusted(self.store, os.path.realpath(self.local_config), digest))


class TestConcurrency(MigrationCase):
    def setUp(self):
        super().setUp()
        self.real_read = config_migrate._read_bytes

    def counting_reader(self, writes: dict):
        """A _read_bytes that writes `writes[path] = (read number, bytes)` on that read of path."""
        counts = {}

        def reader(path):
            counts[path] = counts.get(path, 0) + 1
            if path in writes and counts[path] == writes[path][0]:
                self.write_bytes(path, writes[path][1])
            return self.real_read(path)

        return reader

    def test_write_before_the_publish_is_rebuilt_from_fresh_bytes(self):
        self.write(self.local_old, LOCAL_ROSTER)
        writes = {self.local_config: (2, RETRY_TEXT.encode("utf-8"))}
        with mock.patch.object(config_migrate, "_read_bytes",
                               side_effect=self.counting_reader(writes)):
            self.assertEqual(self.migrate(), "migrated")
        parsed = tomllib.loads(self.read(self.local_config))
        self.assertEqual(parsed["runner"]["retry"]["max_retries"], 2)
        self.assertEqual(parsed["lanes"], self.expected_lanes(LOCAL_ROSTER))

    def test_write_after_the_publish_defers_and_the_next_run_finishes(self):
        self.write(self.local_old, LOCAL_ROSTER)
        raw = self.read_bytes(self.local_old)
        real_publish = toml_splice.publish

        def racing_publish(path, text):
            real_publish(path, text)
            self.write(path, RETRY_TEXT)

        with mock.patch.object(toml_splice, "publish", side_effect=racing_publish):
            self.assertEqual(self.migrate(**self.trust_kwargs()), "deferred")
        self.assertIn("changed while", self.warnings[-1])
        self.assertEqual(self.read_bytes(self.local_old), raw)
        self.assertFalse(self.store_has_records())
        self.assertEqual(self.migrate(), "migrated")
        parsed = tomllib.loads(self.read(self.local_config))
        self.assertEqual(parsed["runner"]["retry"]["max_retries"], 2)
        self.assertEqual(parsed["lanes"], self.expected_lanes(LOCAL_ROSTER))

    def test_other_table_added_after_the_publish_keeps_the_carried_trust(self):
        self.record_legacy_trust(COMMAND_ROSTER.encode("utf-8"))
        real_publish = toml_splice.publish

        def racing_publish(path, text):
            real_publish(path, text)
            self.write(path, text + "\n" + RETRY_TEXT)  # another table, [lanes] intact

        with mock.patch.object(toml_splice, "publish", side_effect=racing_publish):
            self.assertEqual(self.migrate(**self.trust_kwargs()), "migrated")
        self.assertTrue(trust.is_trusted(self.store, os.path.realpath(self.local_config),
                                         canonical_bytes(self.lanes(self.local_config))))
        self.assertTrue(os.path.exists(self.local_old + config_migrate.MIGRATED_SUFFIX))
        self.assertEqual(tomllib.loads(self.read(self.local_config))["runner"]["retry"],
                         {"max_retries": 2})

    def test_old_file_changed_before_the_rename_is_kept(self):
        self.write(self.local_old, LOCAL_ROSTER)
        changed = LOCAL_ROSTER.replace('model = "m1"', 'model = "m9"').encode("utf-8")
        writes = {self.local_old: (2, changed)}
        with mock.patch.object(config_migrate, "_read_bytes",
                               side_effect=self.counting_reader(writes)):
            self.assertEqual(self.migrate(), "deferred")
        self.assertIn("changed during its migration", self.warnings[-1])
        self.assertEqual(self.read_bytes(self.local_old), changed)
        self.assertFalse(os.path.exists(self.local_old + config_migrate.MIGRATED_SUFFIX))
        self.assertEqual(self.lanes(self.local_config), self.expected_lanes(LOCAL_ROSTER))
        self.assertEqual(self.migrate(), "kept-new")


class TestErrors(MigrationCase):
    def test_malformed_old_toml_raises_naming_the_old_path_and_writes_nothing(self):
        bad = "[[reviewers\nkey = \n"
        self.write(self.local_old, bad)
        with self.assertRaises(LegacyRosterError) as caught:
            self.migrate()
        self.assertIn(self.local_old, str(caught.exception))
        self.assertEqual(self.read(self.local_old), bad)
        self.assertFalse(os.path.exists(self.local_config))

    def test_non_utf8_old_bytes_raise_and_write_nothing(self):
        self.write_bytes(self.local_old, b'key = "\xff"\n')
        with self.assertRaises(LegacyRosterError) as caught:
            self.migrate()
        self.assertIn("UTF-8", str(caught.exception))
        self.assertFalse(os.path.exists(self.local_config))

    def test_malformed_config_toml_raises_naming_the_new_path(self):
        self.write(self.local_old, LOCAL_ROSTER)
        self.write(self.local_config, "[broken\n")
        with self.assertRaises(LegacyRosterError) as caught:
            self.migrate()
        self.assertIn(self.local_config, str(caught.exception))
        self.assertEqual(self.read(self.local_old), LOCAL_ROSTER)


class TestNoSecretCopied(MigrationCase):
    SECRET = "sentinel-not-a-key"

    def test_no_environment_or_secrets_value_lands_in_any_file(self):
        secrets_file = os.path.join(self.user, "secrets.env")
        self.write(secrets_file, f"ARTIFICIAL_ANALYSIS_API_KEY={self.SECRET}\n")
        self.write(self.local_old, LOCAL_ROSTER)
        self.write(self.user_old, LOCAL_ROSTER)
        with mock.patch.dict(os.environ, {"ARTIFICIAL_ANALYSIS_API_KEY": self.SECRET}):
            self.migrate(self.local_config)
            self.migrate(self.user_config)
        for folder, _dirs, files in os.walk(self._tmp.name):
            for name in files:
                path = os.path.join(folder, name)
                if path != secrets_file:
                    self.assertNotIn(self.SECRET.encode("utf-8"), self.read_bytes(path), path)


class TestCanonicalBytes(unittest.TestCase):
    def test_spacing_comments_and_key_order_do_not_change_the_bytes(self):
        plain = '[lanes]\n[[lanes.review]]\nkey = "a"\ncommand = "x"\nmodel = "m"\n'
        loose = ('# note\n[lanes]\n\n[[lanes.review]]\n  model =   "m"  \n'
                 '  command = "x"   # trailing\n  key = "a"\n')
        self.assertEqual(trust.command_lanes_bytes(tomllib.loads(plain)["lanes"]),
                         trust.command_lanes_bytes(tomllib.loads(loose)["lanes"]))

    def test_a_date_free_lane_list_keeps_its_pinned_digest(self):
        # The digest taken before dates were encoded: existing trust records stay valid (WR-01).
        raw = canonical_bytes({"review": [{"key": "a", "command": "x"}]})
        self.assertEqual(raw, b'[["review",{"command":"x","key":"a"}]]')
        self.assertEqual(trust.content_sha256(raw),
                         "4b064776fe7b70f04f5474b8b4fb1a16d6eed220cc9bea27537260257c85a492")

    def test_toml_dates_and_times_are_encoded_and_change_the_digest(self):
        def digest(added: str) -> bytes:
            text = f'[[lanes.review]]\nkey = "a"\ncommand = "x"\nadded = {added}\n'
            return canonical_bytes(tomllib.loads(text)["lanes"])
        first = digest("2026-01-01")
        self.assertIn(b'["date","2026-01-01"]', first)
        self.assertNotEqual(first, digest("2026-01-02"))
        self.assertIn(b'["time","07:32:00"]', digest("07:32:00"))
        self.assertIn(b'["datetime","1979-05-27T07:32:00"]', digest("1979-05-27T07:32:00"))

    def test_a_dated_command_entry_resolves_without_a_traceback(self):
        from ai_kit_spec import config_io
        with tempfile.TemporaryDirectory() as root:
            project, home = os.path.join(root, "proj"), os.path.join(root, "home")
            os.makedirs(os.path.join(project, ".aikit"))
            os.makedirs(home)
            with open(os.path.join(project, ".aikit", "config.toml"), "w", encoding="utf-8") as f:
                f.write('[[lanes.review]]\nkey = "x"\ncommand = "echo {prompt}"\n'
                        "added = 2026-01-01\n")
            resolved = config_io.cfg_resolve(project, {"HOME": home}, warn_fn=lambda _m: None)
        self.assertEqual(resolved["review"], [])  # untrusted: ignored, not a crash

    def test_entries_are_ordered_by_sorted_role_then_position(self):
        lanes = {"review": [{"key": "b", "command": "x"}, {"key": "a", "command": "x"}],
                 "execute": [{"key": "c", "command": "y"}]}
        ordered = json.loads(canonical_bytes(lanes))
        self.assertEqual([role for role, _entry in ordered], ["execute", "review", "review"])
        self.assertEqual([entry["key"] for _role, entry in ordered[1:]], ["b", "a"])


if __name__ == "__main__":
    unittest.main()
