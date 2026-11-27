"""Transport chooser: verified labels, precedence, renewal, the per-plan record and the
locked round start/end."""

import contextlib
import io
import json
import multiprocessing
import os
import sys
import tempfile
import time
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills", "ai-kit-spec-review"))
sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "skills", "ai-kit-spec-execute-superpowers"))

from ai_kit_spec import (
    cache,
    capability_block,
    config_io,
    detection,
    execute_dispatch,
    herdr_pane,
    lane_transport,
    reviewer_dispatch,
    runner_dispatch,
    runner_facts,
)
from ai_kit_spec import cli as review_cli
from ai_kit_spec_superpowers import cli as adapter_cli
from ai_kit_spec_superpowers import dispatch_injection


def describe_fact(runtime, state="verified", source="codex 0.170.0 live resume") -> dict:
    """A runner describe fact with one runtime's session label."""
    return {"runtimes": {runtime: {"session": {"label": {"state": state, "source": source}}}}}


def runtimes_snapshot(runtime, version_line="codex-cli 0.170.0") -> dict:
    """A runtimes snapshot whose clis.<id>.listed_from.version is version_line."""
    return {"schema_version": detection.RUNTIMES_SCHEMA_VERSION,
            "clis": {runtime: {"installed": True,
                               "listed_from": {"command": "fake-cli models",
                                               "version": version_line, "at": "fake-time"}}}}


def request(verified=frozenset(), interactive=False, herdr_ok=True,
            lane_id="execute:0:lane-a", **pair) -> lane_transport.TransportRequest:
    """A codex/placeholder-model-1/execute request; pair may override runtime, model or mode."""
    fields = {"runtime": "codex", "model": "placeholder-model-1", "mode": "execute"}
    fields.update(pair)
    return lane_transport.TransportRequest(
        lane_id=lane_id, runtime=fields["runtime"], interactive=interactive,
        verified=verified, herdr_ok=herdr_ok, model=fields["model"], mode=fields["mode"])


def scratch_env(root: str) -> dict:
    """HOME and XDG_CACHE_HOME under the run's temp dir; no cache files exist yet."""
    return {"HOME": os.path.join(root, "home"), "XDG_CACHE_HOME": os.path.join(root, "xdg")}


def seed_cache(env: dict, runtime: str, version_line: str, describe: dict) -> None:
    """Write the runtimes snapshot with the runner fact the way stored_fact reads it."""
    snapshot = runtimes_snapshot(runtime, version_line)
    snapshot["runner"] = {"template_sha256": runner_facts.template_sha256(
        runner_facts.resolve_cross_ai_template_path()), "describe": describe}
    cache.cache_write_json(detection.cache_runtimes_path(env), snapshot)


class TestVerifiedTransports(unittest.TestCase):
    def test_verified_label_matching_snapshot_version_offers_resume(self):
        self.assertEqual(lane_transport.verified_transports(
            describe_fact("codex"), runtimes_snapshot("codex"), "codex"), frozenset({"resume"}))

    def test_version_drift_state_and_missing_fields_read_empty(self):
        self.assertEqual(lane_transport.verified_transports(
            describe_fact("codex"), runtimes_snapshot("codex", "codex-cli 0.171.0"), "codex"),
            frozenset())
        self.assertEqual(lane_transport.verified_transports(
            describe_fact("codex", state="unverified"), runtimes_snapshot("codex"), "codex"),
            frozenset())
        snapshot = runtimes_snapshot("codex")
        del snapshot["clis"]["codex"]["listed_from"]["version"]
        self.assertEqual(lane_transport.verified_transports(
            describe_fact("codex"), snapshot, "codex"), frozenset())
        self.assertEqual(lane_transport.verified_transports(
            None, runtimes_snapshot("codex"), "codex"), frozenset())
        self.assertEqual(lane_transport.verified_transports(
            describe_fact("codex"), None, "codex"), frozenset())
        self.assertEqual(lane_transport.verified_transports(
            describe_fact("codex", source="codex live resume"), runtimes_snapshot("codex"),
            "codex"), frozenset())

    def test_pane_label_reads_unverified_until_patched(self):
        verified = lane_transport.verified_transports(
            describe_fact("codex"), runtimes_snapshot("codex"), "codex")
        self.assertNotIn("pane", verified)
        with mock.patch.dict(lane_transport.PANE_LABEL, {"state": "verified"}):
            verified = lane_transport.verified_transports(
                describe_fact("codex"), runtimes_snapshot("codex"), "codex")
        self.assertIn("pane", verified)

    def test_no_resume_modes_block_resume_only(self):
        fact = describe_fact("codex")
        fact["runtimes"]["codex"]["session"]["noResume"] = ["review", "sandbox"]
        self.assertEqual(lane_transport.verified_transports(
            fact, runtimes_snapshot("codex"), "codex"), frozenset({"resume"}))
        for mode in ("review", "sandbox"):
            with self.subTest(mode=mode):
                self.assertEqual(lane_transport.verified_transports(
                    fact, runtimes_snapshot("codex"), "codex", mode), frozenset())

    def test_formula_labels_never_count(self):
        fact = describe_fact("codex", state="unverified")
        fact["runtimes"]["codex"]["formula_labels"] = {
            "resume": {"state": "verified", "source": "codex 0.170.0 --help"}}
        self.assertEqual(lane_transport.verified_transports(
            fact, runtimes_snapshot("codex"), "codex"), frozenset())


class TestChooseTransport(unittest.TestCase):
    def test_unbound_entry_reads_lane_pair_or_mode_changed(self):
        verified = frozenset({"resume"})
        entry = {"session_id": "fake-sid-1", "rounds": 1,
                 "runtime": "codex", "model": "placeholder-model-1", "mode": "execute"}
        for label, changed in (("model", request(verified, model="placeholder-model-2")),
                               ("runtime", request(verified, runtime="pi")),
                               ("mode", request(verified, mode="review"))):
            with self.subTest(changed=label):
                self.assertEqual(
                    lane_transport.choose_transport(changed, entry),
                    lane_transport.TransportChoice(
                        "subprocess", None, "lane pair or mode changed"))
        self.assertEqual(
            lane_transport.choose_transport(
                request(verified),
                {"session_id": "fake-sid-1", "rounds": 1, "runtime": None, "model": None,
                 "mode": None}),
            lane_transport.TransportChoice("subprocess", None, "lane pair or mode changed"))

    def test_invalid_rounds_read_as_no_recorded_session(self):
        verified = frozenset({"resume"})
        for rounds in (-1, True, "2"):
            with self.subTest(rounds=rounds):
                entry = {"session_id": "fake-sid-1", "rounds": rounds,
                         "runtime": "codex", "model": "placeholder-model-1", "mode": "execute"}
                self.assertEqual(
                    lane_transport.choose_transport(request(verified), entry),
                    lane_transport.TransportChoice("subprocess", None, "no recorded session"))

    def test_nothing_verified_reads_subprocess(self):
        entry = {"session_id": "fake-sid-1", "rounds": 1,
                 "runtime": "codex", "model": "placeholder-model-1", "mode": "execute"}
        self.assertEqual(lane_transport.choose_transport(request(frozenset()), entry),
                         lane_transport.TransportChoice("subprocess", None,
                                                         "no verified resume"))

    def test_verified_resume_rounds_and_renewal(self):
        verified = frozenset({"resume"})
        entry = {"session_id": "fake-sid-1", "rounds": 1,
                 "runtime": "codex", "model": "placeholder-model-1", "mode": "execute"}
        self.assertEqual(lane_transport.choose_transport(request(verified), entry),
                         lane_transport.TransportChoice(
                             "resume", "fake-sid-1", "verified resume, round 2 of 3"))
        self.assertEqual(
            lane_transport.choose_transport(request(verified), {**entry, "rounds": 3}),
            lane_transport.TransportChoice("subprocess", None, "renewed after 3 rounds"))
        self.assertEqual(lane_transport.choose_transport(request(verified), None),
                         lane_transport.TransportChoice("subprocess", None,
                                                         "no recorded session"))
        self.assertEqual(
            lane_transport.choose_transport(request(verified), {**entry, "session_id": ""}),
            lane_transport.TransportChoice("subprocess", None, "no recorded session"))

    def test_pane_needs_interactive_and_herdr(self):
        self.assertEqual(
            lane_transport.choose_transport(request(frozenset({"pane"}), interactive=True),
                                            None),
            lane_transport.TransportChoice("pane", None, "interactive lane with a verified pane"))
        self.assertEqual(
            lane_transport.choose_transport(
                request(frozenset({"pane"}), interactive=True, herdr_ok=False), None),
            lane_transport.TransportChoice("subprocess", None, "no verified resume"))
        resume_entry = {"session_id": "fake-sid-1", "rounds": 1,
                        "runtime": "codex", "model": "placeholder-model-1", "mode": "execute"}
        self.assertEqual(
            lane_transport.choose_transport(request(frozenset({"pane", "resume"})), resume_entry),
            lane_transport.TransportChoice(
                "resume", "fake-sid-1", "verified resume, round 2 of 3"))

    def test_pane_renewal_rules(self):
        verified = frozenset({"pane"})
        pane_entry = {"transport": "pane", "session_id": None, "rounds": 2,
                      "runtime": "codex", "model": "placeholder-model-1", "mode": "execute"}
        self.assertEqual(
            lane_transport.choose_transport(request(verified, interactive=True), pane_entry),
            lane_transport.TransportChoice("pane", None, "interactive lane with a verified pane"))
        self.assertEqual(
            lane_transport.choose_transport(
                request(verified, interactive=True), {**pane_entry, "rounds": 3}),
            lane_transport.TransportChoice("pane", None, lane_transport.PANE_RENEWED))
        self.assertEqual(
            lane_transport.choose_transport(
                request(verified, interactive=True, model="placeholder-model-2"),
                {**pane_entry, "rounds": 1}),
            lane_transport.TransportChoice("pane", None, lane_transport.PANE_RENEWED))


class TestRecordRound(unittest.TestCase):
    def test_subprocess_round_starts_the_count(self):
        choice = lane_transport.TransportChoice("subprocess", None, "no recorded session")
        record = lane_transport.record_round({"version": 1, "lanes": {}}, "execute:0:lane-a",
                                             choice, "fake-sid-1", request())
        self.assertEqual(record, {"version": 1, "lanes": {"execute:0:lane-a": {
            "transport": "subprocess", "session_id": "fake-sid-1", "rounds": 1, "pane": None,
            "runtime": "codex", "model": "placeholder-model-1", "mode": "execute"}}})

    def test_resume_round_adds_one_and_keeps_the_session(self):
        entry = {"transport": "resume", "session_id": "fake-sid-1", "rounds": 1,
                 "runtime": "codex", "model": "placeholder-model-1", "mode": "execute"}
        choice = lane_transport.TransportChoice("resume", "fake-sid-1",
                                               "verified resume, round 2 of 3")
        record = lane_transport.record_round({"version": 1, "lanes": {"execute:0:lane-a": entry}},
                                            "execute:0:lane-a", choice, "fake-sid-1", request())
        self.assertEqual(record["lanes"]["execute:0:lane-a"],
                         {"transport": "resume", "session_id": "fake-sid-1", "rounds": 2,
                          "pane": None, "runtime": "codex", "model": "placeholder-model-1",
                          "mode": "execute"})

    def test_pane_rounds_after_renewal_reuse_and_first_use(self):
        old_pane = {"transport": "pane", "session_id": None, "rounds": 3,
                    "runtime": "codex", "model": "placeholder-model-1", "mode": "execute"}
        renewed = lane_transport.record_round(
            {"version": 1, "lanes": {"execute:0:lane-a": old_pane}}, "execute:0:lane-a",
            lane_transport.TransportChoice("pane", None, lane_transport.PANE_RENEWED),
            None, request())
        self.assertEqual(renewed["lanes"]["execute:0:lane-a"]["rounds"], 1)
        reused = lane_transport.record_round(
            {"version": 1, "lanes": {"execute:0:lane-a": {**old_pane, "rounds": 2}}},
            "execute:0:lane-a",
            lane_transport.TransportChoice("pane", None, "interactive lane with a verified pane"),
            None, request())
        self.assertEqual(reused["lanes"]["execute:0:lane-a"]["rounds"], 3)
        after_resume = lane_transport.record_round(
            {"version": 1, "lanes": {"execute:0:lane-a": {
                "transport": "resume", "session_id": "fake-sid-1", "rounds": 1,
                "runtime": "codex", "model": "placeholder-model-1", "mode": "execute"}}},
            "execute:0:lane-a",
            lane_transport.TransportChoice("pane", None, "interactive lane with a verified pane"),
            None, request())
        self.assertEqual(after_resume["lanes"]["execute:0:lane-a"]["rounds"], 1)

    def test_existing_pane_field_is_kept(self):
        old = {"transport": "pane", "session_id": None, "rounds": 2, "pane": "pane-7",
               "runtime": "codex", "model": "placeholder-model-1", "mode": "execute"}
        record = lane_transport.record_round({"version": 1, "lanes": {"execute:0:lane-a": old}},
                                            "execute:0:lane-a",
                                            lane_transport.TransportChoice(
                                                "pane", None,
                                                "interactive lane with a verified pane"),
                                            None, request())
        self.assertEqual(record["lanes"]["execute:0:lane-a"]["pane"], "pane-7")

    def test_input_record_is_not_mutated(self):
        entry = {"transport": "resume", "session_id": "fake-sid-1", "rounds": 1,
                 "runtime": "codex", "model": "placeholder-model-1", "mode": "execute"}
        record = {"version": 1, "lanes": {"execute:0:lane-a": entry}}
        lane_transport.record_round(record, "execute:0:lane-a",
                                    lane_transport.TransportChoice("resume", "fake-sid-1",
                                                                   "verified resume, round 2 of 3"),
                                    "fake-sid-1", request())
        self.assertEqual(record, {"version": 1, "lanes": {"execute:0:lane-a": entry}})
        self.assertEqual(entry["rounds"], 1)

    def test_lane_ids_keep_separate_entries(self):
        record = {"version": 1, "lanes": {"execute:0:lane-a": {
            "transport": "resume", "session_id": "fake-sid-9", "rounds": 2, "pane": None,
            "runtime": "codex", "model": "placeholder-model-1", "mode": "execute"}}}
        choice = lane_transport.TransportChoice("subprocess", None, "no recorded session")
        record = lane_transport.record_round(record, "execute:1:lane-b", choice, "fake-sid-2",
                                            request(lane_id="execute:1:lane-b"))
        self.assertEqual(record["lanes"]["execute:0:lane-a"]["session_id"], "fake-sid-9")
        self.assertEqual(record["lanes"]["execute:1:lane-b"]["session_id"], "fake-sid-2")


class TestRecordFile(unittest.TestCase):
    def test_write_then_read_round_trips(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "nested", "record.json")
            record = {"version": lane_transport.RECORD_VERSION,
                      "lanes": {"execute:0:lane-a": {
                          "transport": "resume", "session_id": "fake-sid-1", "rounds": 2,
                          "pane": None, "runtime": "codex", "model": "placeholder-model-1",
                          "mode": "execute"}}}
            lane_transport.write_record(path, record)
            self.assertEqual(lane_transport.read_record(path), record)

    def test_missing_or_foreign_files_read_empty(self):
        empty = {"version": lane_transport.RECORD_VERSION, "lanes": {}}
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(lane_transport.read_record(os.path.join(tmp, "missing.json")),
                             empty)
            listed = os.path.join(tmp, "list.json")
            with open(listed, "w", encoding="utf-8") as handle:
                handle.write('["not", "a", "record"]')
            self.assertEqual(lane_transport.read_record(listed), empty)
            foreign = os.path.join(tmp, "foreign.json")
            lane_transport.write_record(foreign, {"version": 2, "lanes": {}})
            self.assertEqual(lane_transport.read_record(foreign), empty)


class TestFiveRounds(unittest.TestCase):
    def test_three_rounds_then_renewal_through_the_file(self):
        verified = lane_transport.verified_transports(
            describe_fact("codex"), runtimes_snapshot("codex"), "codex")
        lane_id = "execute:0:lane-a"
        transports = []
        passed = []
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "record.json")
            for n in range(1, 6):
                entry = lane_transport.read_record(path)["lanes"].get(lane_id)
                choice = lane_transport.choose_transport(request(verified), entry)
                transports.append(choice.transport)
                passed.append(choice.session_id)
                session = choice.session_id or f"fake-sid-{n}"
                lane_transport.write_record(path, lane_transport.record_round(
                    lane_transport.read_record(path), lane_id, choice, session, request(verified)))
        self.assertEqual(transports, ["subprocess", "resume", "resume", "subprocess", "resume"])
        self.assertEqual(passed, [None, "fake-sid-1", "fake-sid-1", None, "fake-sid-4"])


class TestCallMode(unittest.TestCase):
    def test_mode_by_role_and_runtime(self):
        self.assertEqual(lane_transport.call_mode("review", "opencode"), "review")
        self.assertEqual(lane_transport.call_mode("execute", "codex"), "sandbox")
        self.assertEqual(lane_transport.call_mode("execute", "opencode"), "execute")


class TestLaneRequest(unittest.TestCase):
    OPENCODE = {"key": "lane-a", "runtime": "opencode", "model": "fake/placeholder-model-1"}

    def test_no_cache_files_read_empty_and_unavailable(self):
        with tempfile.TemporaryDirectory() as tmp:
            req = lane_transport.lane_request(
                "execute", 0, self.OPENCODE, scratch_env(tmp), which_fn=lambda _name: None)
            self.assertEqual(req, lane_transport.TransportRequest(
                lane_id="execute:0:lane-a", runtime="opencode", interactive=False,
                verified=frozenset(), herdr_ok=False, model="fake/placeholder-model-1",
                mode="execute"))

    def test_verified_label_matching_the_snapshot_offers_resume(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = scratch_env(tmp)
            seed_cache(env, "opencode", "opencode 1.2.3",
                       describe_fact("opencode", source="opencode 1.2.3 live resume"))
            req = lane_transport.lane_request(
                "execute", 0, self.OPENCODE, env, which_fn=lambda _name: None)
            self.assertEqual(req.verified, frozenset({"resume"}))

    def test_snapshot_version_drift_offers_no_resume(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = scratch_env(tmp)
            seed_cache(env, "opencode", "opencode 1.2.4",
                       describe_fact("opencode", source="opencode 1.2.3 live resume"))
            req = lane_transport.lane_request(
                "execute", 0, self.OPENCODE, env, which_fn=lambda _name: None)
            self.assertEqual(req.verified, frozenset())

    def test_no_resume_modes_forbid_resume_for_both_roles(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = scratch_env(tmp)
            describe = describe_fact("codex")
            describe["runtimes"]["codex"]["session"]["noResume"] = ["review", "sandbox"]
            seed_cache(env, "codex", "codex-cli 0.170.0", describe)
            entry = {"key": "lane-a", "runtime": "codex", "model": "placeholder-model-1"}
            execute = lane_transport.lane_request(
                "execute", 0, entry, env, which_fn=lambda _name: None)
            review = lane_transport.lane_request(
                "review", 0, entry, env, which_fn=lambda _name: None)
            self.assertEqual(execute.mode, "sandbox")
            self.assertEqual(execute.verified, frozenset())
            self.assertEqual(review.mode, "review")
            self.assertEqual(review.verified, frozenset())

    def test_typed_marker_reads_true_with_herdr_absent(self):
        with tempfile.TemporaryDirectory() as tmp:
            req = lane_transport.lane_request(
                "execute", 0, {**self.OPENCODE, "interactive": True}, scratch_env(tmp),
                which_fn=lambda _name: None)
            self.assertTrue(req.interactive)
            self.assertFalse(req.herdr_ok)

    def test_a_non_boolean_marker_reads_false_with_one_note(self):
        for value in ("yes", 1, "true", None):
            with self.subTest(value=value), tempfile.TemporaryDirectory() as tmp:
                with contextlib.redirect_stderr(io.StringIO()) as captured:
                    req = lane_transport.lane_request(
                        "execute", 0, {**self.OPENCODE, "interactive": value}, scratch_env(tmp),
                        which_fn=lambda _name: None)
                self.assertFalse(req.interactive)
                self.assertEqual(captured.getvalue().splitlines(), [
                    "ai-kit-spec: lane-a: 'interactive' must be a boolean; read as not "
                    "interactive"])


class TestBeginEndRound(unittest.TestCase):
    def test_begin_round_on_empty_record_prints_one_subprocess_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "record.json")
            start = lane_transport.RoundStart(path, request())
            with contextlib.redirect_stderr(io.StringIO()) as captured:
                choice = lane_transport.begin_round(start)
            self.assertEqual(choice, lane_transport.TransportChoice(
                "subprocess", None, "no verified resume"))
            self.assertEqual(captured.getvalue().splitlines(),
                             ["ai-kit-spec: transport execute:0:lane-a: subprocess "
                              "(no verified resume)"])

    def test_end_round_stores_the_session_and_a_clear_busy_mark(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "record.json")
            start = lane_transport.RoundStart(path, request())
            with contextlib.redirect_stderr(io.StringIO()):
                choice = lane_transport.begin_round(start)
            lane_transport.end_round(start, choice, {"status": "ok", "session": "fake-sid-1"})
            self.assertEqual(lane_transport.read_record(path)["lanes"]["execute:0:lane-a"], {
                "transport": "subprocess", "session_id": "fake-sid-1", "rounds": 1,
                "pane": None, "runtime": "codex", "model": "placeholder-model-1",
                "mode": "execute", "busy_pid": None})

    def test_end_round_with_dash_session_stores_null(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "record.json")
            start = lane_transport.RoundStart(path, request())
            with contextlib.redirect_stderr(io.StringIO()):
                choice = lane_transport.begin_round(start)
            lane_transport.end_round(start, choice, {"status": "ok", "session": "-"})
            entry = lane_transport.read_record(path)["lanes"]["execute:0:lane-a"]
            self.assertIsNone(entry["session_id"])
            self.assertEqual(entry["rounds"], 1)
            self.assertIsNone(entry["busy_pid"])

    def test_resume_cycle_through_the_locked_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = scratch_env(tmp)
            seed_cache(env, "opencode", "opencode 1.2.3",
                       describe_fact("opencode", source="opencode 1.2.3 live resume"))
            req = lane_transport.lane_request(
                "execute", 0, {"key": "lane-a", "runtime": "opencode",
                               "model": "fake/placeholder-model-1"},
                env, which_fn=lambda _name: None)
            path = os.path.join(tmp, "record.json")
            start = lane_transport.RoundStart(path, req)
            status = {"status": "ok", "session": "fake-sid-1"}
            with contextlib.redirect_stderr(io.StringIO()):
                first = lane_transport.begin_round(start)
            self.assertEqual(first.transport, "subprocess")
            lane_transport.end_round(start, first, status)
            entry = lane_transport.read_record(path)["lanes"]["execute:0:lane-a"]
            self.assertEqual((entry["transport"], entry["session_id"], entry["rounds"]),
                             ("subprocess", "fake-sid-1", 1))
            for round_no in (2, 3):
                with self.subTest(round_no=round_no):
                    with contextlib.redirect_stderr(io.StringIO()) as captured:
                        resumed = lane_transport.begin_round(start)
                    self.assertEqual(resumed, lane_transport.TransportChoice(
                        "resume", "fake-sid-1", f"verified resume, round {round_no} of 3"))
                    self.assertEqual(len(captured.getvalue().splitlines()), 1)
                    lane_transport.end_round(start, resumed, status)
                    entry = lane_transport.read_record(path)["lanes"]["execute:0:lane-a"]
                    self.assertEqual(entry["rounds"], round_no)
            with contextlib.redirect_stderr(io.StringIO()) as captured:
                fourth = lane_transport.begin_round(start)
            self.assertEqual(fourth, lane_transport.TransportChoice(
                "subprocess", None, "renewed after 3 rounds"))
            self.assertEqual(len(captured.getvalue().splitlines()), 1)
            lane_transport.end_round(start, fourth, {"status": "ok", "session": "fake-sid-2"})
            entry = lane_transport.read_record(path)["lanes"]["execute:0:lane-a"]
            self.assertEqual((entry["transport"], entry["session_id"], entry["rounds"]),
                             ("subprocess", "fake-sid-2", 1))

    def test_pair_reset_rewrites_the_entry(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "record.json")
            lane_transport.write_record(path, {"version": 1, "lanes": {"execute:0:lane-a": {
                "transport": "resume", "session_id": "fake-sid-9", "rounds": 1, "pane": None,
                "runtime": "codex", "model": "placeholder-model-2", "mode": "execute"}}})
            start = lane_transport.RoundStart(path, request(verified=frozenset({"resume"})))
            with contextlib.redirect_stderr(io.StringIO()):
                choice = lane_transport.begin_round(start)
            self.assertEqual(choice, lane_transport.TransportChoice(
                "subprocess", None, "lane pair or mode changed"))
            lane_transport.end_round(start, choice, {"status": "ok", "session": "fake-sid-1"})
            self.assertEqual(lane_transport.read_record(path)["lanes"]["execute:0:lane-a"], {
                "transport": "subprocess", "session_id": "fake-sid-1", "rounds": 1,
                "pane": None, "runtime": "codex", "model": "placeholder-model-1",
                "mode": "execute", "busy_pid": None})

    def test_adjacent_lanes_keep_separate_entries(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "record.json")
            verified = frozenset({"resume"})
            sessions = {}
            for lane_id, session in (("execute:0:lane-a", "fake-sid-1"),
                                     ("execute:1:lane-b", "fake-sid-2")):
                start = lane_transport.RoundStart(path, request(verified, lane_id=lane_id))
                with contextlib.redirect_stderr(io.StringIO()):
                    choice = lane_transport.begin_round(start)
                lane_transport.end_round(start, choice, {"status": "ok", "session": session})
                sessions[lane_id] = lane_transport.read_record(path)["lanes"][lane_id]
            self.assertEqual(set(sessions), {"execute:0:lane-a", "execute:1:lane-b"})
            self.assertEqual(sessions["execute:0:lane-a"]["session_id"], "fake-sid-1")
            self.assertEqual(sessions["execute:1:lane-b"]["session_id"], "fake-sid-2")

    def test_busy_mark_rules(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "record.json")
            resume = lane_transport.TransportChoice(
                "resume", "fake-sid-1", "verified resume, round 2 of 3")
            entry = {"transport": "resume", "session_id": "fake-sid-1", "rounds": 1,
                     "pane": None, "runtime": "codex", "model": "placeholder-model-1",
                     "mode": "execute", "busy_pid": 4242}
            start = lane_transport.RoundStart(path, request(verified=frozenset({"resume"})),
                                               pid=4242)
            lane_transport.write_record(
                path, {"version": 1, "lanes": {"execute:0:lane-a": entry}})
            lane_transport.end_round(start, resume, {"status": "ok", "session": "fake-sid-1"})
            self.assertIsNone(
                lane_transport.read_record(path)["lanes"]["execute:0:lane-a"]["busy_pid"])

            with mock.patch.object(herdr_pane, "pid_alive", return_value=False):
                lane_transport.write_record(path, {"version": 1, "lanes": {"execute:0:lane-a": {
                    **entry, "busy_pid": 999}}})
                lane_transport.end_round(start, resume, {"status": "ok", "session": "fake-sid-1"})
                self.assertEqual(
                    lane_transport.read_record(path)["lanes"]["execute:0:lane-a"]["busy_pid"], 999)

                lane_transport.write_record(path, {"version": 1, "lanes": {"execute:0:lane-a": {
                    **entry, "transport": "pane", "session_id": None, "rounds": 2,
                    "busy_pid": 999}}})
                lane_transport.end_round(
                    start,
                    lane_transport.TransportChoice("pane", None,
                                                    "interactive lane with a verified pane"),
                    {"status": "ok", "session": "-"})
                self.assertEqual(lane_transport.read_record(path)["lanes"]["execute:0:lane-a"], {
                    "transport": "subprocess", "session_id": None, "rounds": 1, "pane": None,
                    "runtime": "codex", "model": "placeholder-model-1", "mode": "execute",
                    "busy_pid": 999})

                lane_transport.write_record(path, {"version": 1, "lanes": {"execute:0:lane-a": {
                    **entry, "transport": "pane", "session_id": None, "rounds": 2,
                    "busy_pid": 999}}})
                with open(path, "rb") as handle:
                    before = handle.read()
                with mock.patch.object(herdr_pane, "pid_alive", return_value=True):
                    lane_transport.end_round(
                        start, resume, {"status": "ok", "session": "fake-sid-9"})
                with open(path, "rb") as handle:
                    self.assertEqual(handle.read(), before)


class TestLockedUpdate(unittest.TestCase):
    def test_none_update_removes_the_record_and_keeps_the_lock(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "record.json")
            lane_transport.write_record(path, {"version": 1, "lanes": {}})
            self.assertIsNone(lane_transport._locked_update(path, lambda record: None))
            self.assertFalse(os.path.exists(path))
            self.assertTrue(os.path.exists(path + ".lock"))

    def test_two_writers_racing_lose_no_update(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "record.json")
            fork = multiprocessing.get_context("fork")
            writers = [fork.Process(target=_add_lanes, args=(path, name, 25))
                       for name in ("a", "b")]
            for writer in writers:
                writer.start()
            for writer in writers:
                writer.join(30)
            self.assertEqual([writer.exitcode for writer in writers], [0, 0])
            self.assertEqual(len(lane_transport.read_record(path)["lanes"]), 50)


def _add_lanes(path: str, name: str, count: int) -> None:
    """One writer process: count read-modify-writes, each slow enough to overlap the other."""
    def add(index: int):
        def update(record: dict) -> dict:
            time.sleep(0.002)
            return {**record, "lanes": {**record["lanes"], f"{name}{index}": {}}}
        return update

    for index in range(count):
        lane_transport._locked_update(path, add(index))


FOREIGN =b'{"owner": "data", "keep": [1, 2, 3]}\n'


class TestRecordRefusal(unittest.TestCase):
    """A file that is not a transport record is refused and left byte-identical."""

    def test_round_updates_refuse_a_foreign_file(self):
        for data in (FOREIGN, b"{not json", b"\xff\xfe", b"[1, 2]"):
            with self.subTest(data=data), tempfile.TemporaryDirectory() as tmp:
                path = os.path.join(tmp, "record.json")
                with open(path, "wb") as handle:
                    handle.write(data)
                start = lane_transport.RoundStart(path, request())
                with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(ValueError):
                    lane_transport.begin_round(start)
                with self.assertRaises(ValueError):
                    lane_transport.end_round(start, lane_transport.TransportChoice(
                        "subprocess", None, "no verified resume"), {"status": "ok"})
                with open(path, "rb") as handle:
                    self.assertEqual(handle.read(), data)

    def test_try_end_round_prints_one_line_and_leaves_the_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "record.json")
            with open(path, "wb") as handle:
                handle.write(FOREIGN)
            start = lane_transport.RoundStart(path, request())
            with contextlib.redirect_stderr(io.StringIO()) as err:
                lane_transport.try_end_round(start, lane_transport.TransportChoice(
                    "subprocess", None, "no verified resume"), {"status": "ok"})
            self.assertEqual(err.getvalue().splitlines(), [
                f"ai-kit-spec: transport record {path} unusable: not a transport record; "
                "the round is not counted"])
            with open(path, "rb") as handle:
                self.assertEqual(handle.read(), FOREIGN)

    def test_begin_round_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "record.json")
            start = lane_transport.RoundStart(path, request())
            with contextlib.redirect_stderr(io.StringIO()):
                lane_transport.begin_round(start)
            self.assertFalse(os.path.exists(path))
            lane_transport.write_record(path, {"version": 1, "lanes": {"execute:0:lane-a": {
                "transport": "subprocess", "session_id": None, "rounds": 1, "pane": None,
                "runtime": "codex", "model": "placeholder-model-1", "mode": "execute"}}})
            with open(path, "rb") as handle:
                before = handle.read()
            os.utime(path, ns=(1_000_000_000, 1_000_000_000))
            with contextlib.redirect_stderr(io.StringIO()):
                lane_transport.begin_round(start)
            self.assertEqual(os.stat(path).st_mtime_ns, 1_000_000_000)
            with open(path, "rb") as handle:
                self.assertEqual(handle.read(), before)

    def test_the_record_lock_has_one_implementation(self):
        with open(lane_transport.__file__, encoding="utf-8") as handle:
            source = handle.read()
        self.assertEqual(source.count("fcntl.LOCK_EX"), 1)


class TestRunnerSpecSessionId(unittest.TestCase):
    def test_candidate_session_id_reaches_the_runner_argv(self):
        with tempfile.TemporaryDirectory() as tmp:
            spec = execute_dispatch.ExecuteDispatchSpec(
                {"runtime": "codex", "model": "placeholder-model-1", "session_id": "fake-sid-1"},
                "do the task", tmp, 900)
            argv = runner_dispatch.build_runner_argv(
                execute_dispatch._runner_spec(spec.candidate, spec),
                "fake-runner.mjs", "fake-node")
            self.assertIn("--session-id", argv)
            self.assertEqual(argv[argv.index("--session-id") + 1], "fake-sid-1")

    def test_candidate_without_session_id_adds_no_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            spec = execute_dispatch.ExecuteDispatchSpec(
                {"runtime": "codex", "model": "placeholder-model-1"},
                "do the task", tmp, 900)
            argv = runner_dispatch.build_runner_argv(
                execute_dispatch._runner_spec(spec.candidate, spec),
                "fake-runner.mjs", "fake-node")
            self.assertNotIn("--session-id", argv)


class TestDispatchTaskRequestSessionId(unittest.TestCase):
    INJECTION = {"mode": "external_cli", "runtime": "codex",
                 "model": "fake/placeholder-model-1"}

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = tmp.name

    def _dispatched_candidate(self, request):
        seen = []

        def fake_execute(spec):
            seen.append(dict(spec.candidate))
            return {"runtime": spec.candidate["runtime"], "model": spec.candidate["model"],
                    "command": "fake-command", "stdout": "DONE", "returncode": 0,
                    "timed_out": False, "reason": None, "status": None}

        dispatch_injection.dispatch_superpowers_task(
            request,
            seams=dispatch_injection.SuperpowersDispatchSeams(
                dispatch_execute_fn=fake_execute,
                env_fn=lambda: {"HOME": self.tmp}))
        return seen[0]

    def test_request_without_session_id_keeps_the_candidate_as_today(self):
        candidate = self._dispatched_candidate(
            dispatch_injection.DispatchTaskRequest(self.INJECTION, "do the task", self.tmp, 900))
        self.assertEqual(candidate, {"runtime": "codex", "model": "fake/placeholder-model-1",
                                    "effort": None, "service_tier": None, "pool": None})

    def test_request_session_id_reaches_the_candidate(self):
        candidate = self._dispatched_candidate(
            dispatch_injection.DispatchTaskRequest(
                self.INJECTION, "do the task", self.tmp, 900, session_id="fake-sid-1"))
        self.assertEqual(candidate["session_id"], "fake-sid-1")


class TestDispatchTaskTransport(unittest.TestCase):
    """dispatch-task through the adapter CLI: the transport record's round around today's
    dispatch, driven with the fake-runner pattern of test_dispatch_guidance_gates."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = tmp.name
        self.env = scratch_env(self.tmp)
        self.record = os.path.join(self.tmp, "record.json")
        self.target = os.path.join(self.tmp, "project")
        os.makedirs(self.target)
        self.row = {"key": "lane-a", "runtime": "opencode", "model": "fake/placeholder-model-1"}
        self.injection = {"mode": "external_cli", "key": "lane-a", "runtime": "opencode",
                          "model": "fake/placeholder-model-1"}
        for name, text in (("prompt.txt", "do the task"), ("format.md", "REPLY.")):
            with open(os.path.join(self.tmp, name), "w", encoding="utf-8") as stream:
                stream.write(text)
        self.assemble_calls = []
        self.requests = []
        self.argvs = []
        # the sessions the fake runner reports, one per call; empty repeats fake-sid-1
        self.sessions = []
        self.foreign_mid_round = False
        isolated = mock.patch.dict(os.environ, self.env)
        isolated.start()
        self.addCleanup(isolated.stop)

    @staticmethod
    def transport_lines(err: str) -> list:
        return [line for line in err.splitlines()
                if line.startswith("ai-kit-spec: transport ")
                and not line.startswith("ai-kit-spec: transport record ")]

    def _dispatch(self, injection=None, rows=None, transport_record=True, assemble=None):
        injection = self.injection if injection is None else injection
        rows = [self.row] if rows is None else rows
        argv = ["dispatch-task",
                "--injection-json", json.dumps(injection),
                "--prompt-file", os.path.join(self.tmp, "prompt.txt"),
                "--target-dir", self.target,
                "--heartbeat-interval", "30",
                "--timeout", "900",
                "--format-block-file", os.path.join(self.tmp, "format.md"),
                "--report-file", os.path.join(self.tmp, "report.md")]
        if transport_record:
            argv += ["--transport-record", self.record]

        def fake_assemble(cwd, env, cfg_resolve_fn=None):
            self.assemble_calls.append((cwd, cfg_resolve_fn))
            return ([{"key": row["key"], "roster_entry": dict(row)} for row in rows], [])

        def fake_runner(spec, _prompt, _seams=None):
            if self.foreign_mid_round:
                with open(self.record, "wb") as handle:
                    handle.write(FOREIGN)
            self.argvs.append(runner_dispatch.build_runner_argv(
                spec, "fake-runner.mjs", "fake-node"))
            session = self.sessions.pop(0) if self.sessions else "fake-sid-1"
            return runner_dispatch.RunnerResult(
                0, "", {"status": "ok", "session": session}, None, False, ["fake-node"], "")

        def wrapped(request, guidance=None):
            self.requests.append(request)
            compose = mock.Mock(
                return_value=capability_block.ComposeResult(block="BLOCK"))
            seams = dispatch_injection.SuperpowersDispatchSeams(
                dispatch_execute_fn=lambda spec: execute_dispatch.dispatch_execute(
                    spec,
                    execute_dispatch.ExecuteSeams(
                        compose_fn=compose, runner_fn=fake_runner, print_fn=lambda _s: None),
                ),
                env_fn=lambda: dict(self.env),
            )
            return dispatch_injection.dispatch_superpowers_task(request, guidance, seams=seams)

        out, err = io.StringIO(), io.StringIO()
        deps = adapter_cli.CliDeps()._replace(
            assemble_candidates_fn=assemble or fake_assemble,
            dispatch_superpowers_task_fn=wrapped,
            detect_tool_availability_fn=lambda: {},
            resolve_agents_tooling_path_fn=lambda: None,
            cbm_registered_fn=lambda _: False,
            which_fn=lambda _name, path=None: None,
            env_fn=lambda: dict(self.env),
            stdout=out,
        )
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = adapter_cli.main(argv, deps=deps)
        return code, out.getvalue(), err.getvalue()

    def test_no_transport_record_is_todays_path(self):
        code, out, err = self._dispatch(transport_record=False)
        self.assertEqual(code, 0, err)
        self.assertEqual(len(self.requests), 1)
        self.assertIsNone(self.requests[0].session_id)
        self.assertEqual(self.assemble_calls, [])
        self.assertFalse(os.path.exists(self.record))
        self.assertFalse(os.path.exists(self.record + ".lock"))
        self.assertEqual(self.transport_lines(err), [])
        self.assertEqual(json.loads(out)["status"]["session"], "fake-sid-1")

    def test_record_without_verified_transport_runs_one_subprocess(self):
        code, _out, err = self._dispatch()
        self.assertEqual(code, 0, err)
        self.assertEqual(len(self.argvs), 1)
        self.assertNotIn("--session-id", self.argvs[0])
        self.assertEqual(lane_transport.read_record(self.record)["lanes"], {
            "execute:0:lane-a": {"transport": "subprocess", "session_id": "fake-sid-1",
                                 "rounds": 1, "pane": None, "runtime": "opencode",
                                 "model": "fake/placeholder-model-1", "mode": "execute",
                                 "busy_pid": None}})
        self.assertEqual(self.transport_lines(err), [
            "ai-kit-spec: transport execute:0:lane-a: subprocess (no verified resume)"])
        self.sessions = ["-"]
        code, _out, _err = self._dispatch()
        self.assertEqual(code, 0)
        entry = lane_transport.read_record(self.record)["lanes"]["execute:0:lane-a"]
        self.assertIsNone(entry["session_id"])
        self.assertEqual(entry["rounds"], 1)

    def test_verified_resume_then_renewal_through_the_cli(self):
        seed_cache(self.env, "opencode", "opencode 1.2.3",
                   describe_fact("opencode", source="opencode 1.2.3 live resume"))
        code, _out, _err = self._dispatch()
        self.assertEqual(code, 0)
        self.assertIsNone(self.requests[0].session_id)
        self.assertNotIn("--session-id", self.argvs[0])
        entry = lane_transport.read_record(self.record)["lanes"]["execute:0:lane-a"]
        self.assertEqual((entry["transport"], entry["session_id"], entry["rounds"]),
                         ("subprocess", "fake-sid-1", 1))
        for round_no in (2, 3):
            with self.subTest(round_no=round_no):
                code, _out, err = self._dispatch()
                self.assertEqual(code, 0, err)
                self.assertEqual(self.requests[-1].session_id, "fake-sid-1")
                self.assertIn("--session-id", self.argvs[-1])
                self.assertEqual(self.argvs[-1][self.argvs[-1].index("--session-id") + 1],
                                 "fake-sid-1")
                entry = lane_transport.read_record(self.record)["lanes"]["execute:0:lane-a"]
                self.assertEqual((entry["transport"], entry["rounds"]), ("resume", round_no))
                self.assertEqual(len(self.transport_lines(err)), 1)
        code, _out, err = self._dispatch()
        self.assertEqual(code, 0, err)
        self.assertIsNone(self.requests[-1].session_id)
        self.assertNotIn("--session-id", self.argvs[-1])
        self.assertEqual(self.transport_lines(err), [
            "ai-kit-spec: transport execute:0:lane-a: subprocess (renewed after 3 rounds)"])
        entry = lane_transport.read_record(self.record)["lanes"]["execute:0:lane-a"]
        self.assertEqual((entry["transport"], entry["rounds"]), ("subprocess", 1))

    def test_codex_execute_mode_never_resumes(self):
        describe = describe_fact("codex")
        describe["runtimes"]["codex"]["session"]["noResume"] = ["review", "sandbox"]
        seed_cache(self.env, "codex", "codex-cli 0.170.0", describe)
        injection = {"mode": "external_cli", "key": "lane-a", "runtime": "codex",
                     "model": "placeholder-model-1"}
        row = {"key": "lane-a", "runtime": "codex", "model": "placeholder-model-1"}
        lane_transport.write_record(self.record, {"version": 1, "lanes": {
            "execute:0:lane-a": {"transport": "resume", "session_id": "fake-sid-9",
                                 "rounds": 1, "pane": None, "runtime": "codex",
                                 "model": "placeholder-model-1", "mode": "sandbox"}}})
        code, _out, err = self._dispatch(injection=injection, rows=[row])
        self.assertEqual(code, 0, err)
        self.assertIsNone(self.requests[0].session_id)
        self.assertNotIn("--session-id", self.argvs[0])
        self.assertEqual(self.transport_lines(err), [
            "ai-kit-spec: transport execute:0:lane-a: subprocess (no verified resume)"])

    def test_pair_reset_rewrites_the_entry(self):
        seed_cache(self.env, "opencode", "opencode 1.2.3",
                   describe_fact("opencode", source="opencode 1.2.3 live resume"))
        lane_transport.write_record(self.record, {"version": 1, "lanes": {
            "execute:0:lane-a": {"transport": "resume", "session_id": "fake-sid-9",
                                 "rounds": 1, "pane": None, "runtime": "opencode",
                                 "model": "fake/placeholder-model-2", "mode": "execute"}}})
        code, _out, err = self._dispatch()
        self.assertEqual(code, 0, err)
        self.assertIsNone(self.requests[0].session_id)
        self.assertEqual(lane_transport.read_record(self.record)["lanes"], {
            "execute:0:lane-a": {"transport": "subprocess", "session_id": "fake-sid-1",
                                 "rounds": 1, "pane": None, "runtime": "opencode",
                                 "model": "fake/placeholder-model-1", "mode": "execute",
                                 "busy_pid": None}})

    def test_roster_row_mismatch_runs_todays_path(self):
        row = {"key": "lane-a", "runtime": "codex", "model": "fake/placeholder-model-1"}
        sentinel = {"version": 1, "lanes": {
            "execute:9:other": {"transport": "subprocess", "session_id": "fake-sid-7",
                                 "rounds": 2, "pane": None, "runtime": "pi",
                                 "model": "placeholder-model-3", "mode": "execute"}}}
        lane_transport.write_record(self.record, sentinel)
        code, _out, err = self._dispatch(rows=[row])
        self.assertEqual(code, 0, err)
        self.assertEqual(len(self.argvs), 1)
        self.assertNotIn("--session-id", self.argvs[0])
        self.assertEqual(self.argvs[0][self.argvs[0].index("--runtime") + 1], "opencode")
        self.assertEqual(self.transport_lines(err), [])
        self.assertEqual(lane_transport.read_record(self.record), sentinel)
        self.assertEqual(len(self.assemble_calls), 1)

    def test_snapshot_version_drift_gives_a_fresh_subprocess(self):
        seed_cache(self.env, "opencode", "opencode 1.2.4",
                   describe_fact("opencode", source="opencode 1.2.3 live resume"))
        lane_transport.write_record(self.record, {"version": 1, "lanes": {
            "execute:0:lane-a": {"transport": "resume", "session_id": "fake-sid-9",
                                 "rounds": 1, "pane": None, "runtime": "opencode",
                                 "model": "fake/placeholder-model-1", "mode": "execute"}}})
        code, _out, err = self._dispatch()
        self.assertEqual(code, 0, err)
        self.assertIsNone(self.requests[0].session_id)
        self.assertNotIn("--session-id", self.argvs[0])
        self.assertEqual(self.transport_lines(err), [
            "ai-kit-spec: transport execute:0:lane-a: subprocess (no verified resume)"])

    def test_adjacent_lanes_keep_two_entries(self):
        row_b = {"key": "lane-b", "runtime": "opencode", "model": "fake/placeholder-model-1"}
        injection_b = {"mode": "external_cli", "key": "lane-b", "runtime": "opencode",
                       "model": "fake/placeholder-model-1"}
        self.sessions = ["fake-sid-1", "fake-sid-2"]
        code, _out, _err = self._dispatch()
        self.assertEqual(code, 0)
        code, _out, _err = self._dispatch(injection=injection_b, rows=[self.row, row_b])
        self.assertEqual(code, 0)
        lanes = lane_transport.read_record(self.record)["lanes"]
        self.assertEqual(set(lanes), {"execute:0:lane-a", "execute:1:lane-b"})
        self.assertEqual(lanes["execute:0:lane-a"]["session_id"], "fake-sid-1")
        self.assertEqual(lanes["execute:1:lane-b"]["session_id"], "fake-sid-2")

    def test_interactive_lane_without_herdr_reads_subprocess(self):
        row = {"key": "lane-a", "runtime": "opencode", "model": "fake/placeholder-model-1",
               "interactive": True}
        code, _out, err = self._dispatch(rows=[row])
        self.assertEqual(code, 0, err)
        self.assertIsNone(self.requests[0].session_id)
        self.assertEqual(self.transport_lines(err), [
            "ai-kit-spec: transport execute:0:lane-a: subprocess (no verified resume)"])

    def test_a_non_boolean_marker_still_dispatches(self):
        code, _out, err = self._dispatch(rows=[{**self.row, "interactive": "yes"}])
        self.assertEqual(code, 0, err)
        self.assertEqual(len(self.requests), 1)
        self.assertIn("ai-kit-spec: lane-a: 'interactive' must be a boolean; read as not "
                      "interactive", err.splitlines())
        self.assertNotIn("Traceback", err)
        self.assertEqual(self.transport_lines(err), [
            "ai-kit-spec: transport execute:0:lane-a: subprocess (no verified resume)"])

    def test_roster_lookup_is_passed_the_quiet_resolver(self):
        code, _out, _err = self._dispatch()
        self.assertEqual(code, 0)
        self.assertEqual(len(self.assemble_calls), 1)
        self.assertIs(self.assemble_calls[0][1], config_io.cfg_resolve_quiet)

    def test_config_error_gives_todays_path(self):
        def raising_assemble(cwd, env, cfg_resolve_fn=None):
            raise config_io.ConfigError(cwd, "no config surface")

        code, _out, err = self._dispatch(assemble=raising_assemble)
        self.assertEqual(code, 0, err)
        self.assertEqual(len(self.argvs), 1)
        self.assertIsNone(self.requests[0].session_id)
        self.assertNotIn("--session-id", self.argvs[0])
        self.assertEqual(self.transport_lines(err), [])
        self.assertEqual(lane_transport.read_record(self.record)["lanes"], {})

    def test_a_foreign_record_runs_a_plain_round_and_is_left_alone(self):
        with open(self.record, "wb") as handle:
            handle.write(FOREIGN)
        code, out, err = self._dispatch()
        self.assertEqual(code, 0, err)
        self.assertEqual(len(self.requests), 1)
        self.assertIsNone(self.requests[0].session_id)
        self.assertEqual(self.transport_lines(err), [])
        self.assertEqual([line for line in err.splitlines()
                          if line.startswith("ai-kit-spec: transport record ")],
                         [f"ai-kit-spec: transport record {self.record} unusable: not a transport "
                          "record; the round runs as a fresh subprocess"])
        with open(self.record, "rb") as handle:
            self.assertEqual(handle.read(), FOREIGN)
        self.assertEqual(json.loads(out)["status"]["session"], "fake-sid-1")

    def test_a_record_that_turns_foreign_mid_round_is_left_alone(self):
        self.foreign_mid_round = True
        code, out, err = self._dispatch()
        self.assertEqual(code, 0, err)
        self.assertEqual([line for line in err.splitlines()
                          if line.startswith("ai-kit-spec: transport record ")],
                         [f"ai-kit-spec: transport record {self.record} unusable: not a transport "
                          "record; the round is not counted"])
        with open(self.record, "rb") as handle:
            self.assertEqual(handle.read(), FOREIGN)
        self.assertEqual(json.loads(out)["status"]["session"], "fake-sid-1")


class TestDispatchReviewerTransport(unittest.TestCase):
    """dispatch-reviewer through the review CLI: the record's path, its lane id and the rows
    that write no record."""

    OPENCODE = {"key": "lane-a", "model": "placeholder-model-1", "vendor": "",
                "runtime": "opencode", "command": None, "extra": {}}

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = tmp.name
        self.env = scratch_env(self.tmp)
        self.record = os.path.join(self.tmp, "transport.json")
        self.reviewers = os.path.join(self.tmp, "reviewers.json")
        self.prompt = os.path.join(self.tmp, "prompt.txt")
        with open(self.prompt, "w", encoding="utf-8") as stream:
            stream.write("review this")
        self.specs = []
        self.foreign_mid_round = False

    def transport_lines(self, err: str) -> list:
        return [line for line in err.splitlines()
                if line.startswith("ai-kit-spec: transport ")
                and not line.startswith("ai-kit-spec: transport record ")]

    def _dispatch(self, row, argv_extra=()):
        with open(self.reviewers, "w", encoding="utf-8") as stream:
            json.dump([row], stream)

        def fake_dispatch(spec, seams=None):
            if self.foreign_mid_round:
                with open(self.record, "wb") as handle:
                    handle.write(FOREIGN)
            self.specs.append(spec)
            return {"stdout": "### Status: Approved\n", "returncode": 0, "timed_out": False,
                    "reason": None, "status": {"status": "ok", "session": "fake-sid-1"},
                    "argv": []}

        argv = ["dispatch-reviewer", "--reviewers-json", self.reviewers, "--index", "0",
                "--prompt-file", self.prompt, "--timeout-tiers", "60", *argv_extra]
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = review_cli.main(argv, env_fn=lambda: dict(self.env),
                                   which_fn=lambda _name, path=None: None,
                                   dispatch_reviewer_fn=fake_dispatch)
        return code, out.getvalue(), err.getvalue()

    def test_without_flags_is_todays_call(self):
        code, out, err = self._dispatch(self.OPENCODE)
        self.assertEqual(code, 0, err)
        self.assertIsNone(self.specs[0].session_id)
        self.assertEqual(self.transport_lines(err), [])
        self.assertEqual(json.loads(out)["status"]["session"], "fake-sid-1")
        self.assertEqual(sorted(os.listdir(self.tmp)), ["prompt.txt", "reviewers.json"])

    def test_lane_log_writes_transport_json_beside_it(self):
        log = os.path.join(self.tmp, "lanes.jsonl")
        code, _out, err = self._dispatch(self.OPENCODE, ["--lane-log", log, "--round", "1"])
        self.assertEqual(code, 0, err)
        self.assertEqual(self.transport_lines(err), [
            "ai-kit-spec: transport review:0:lane-a: subprocess (no verified resume)"])
        self.assertEqual(lane_transport.read_record(self.record)["lanes"], {
            "review:0:lane-a": {"transport": "subprocess", "session_id": "fake-sid-1",
                                "rounds": 1, "pane": None, "runtime": "opencode",
                                "model": "placeholder-model-1", "mode": "review",
                                "busy_pid": None}})

    def test_a_non_boolean_marker_still_dispatches_and_logs_the_lane(self):
        log = os.path.join(self.tmp, "lanes.jsonl")
        row = {**self.OPENCODE, "extra": {"interactive": "yes"}}
        code, _out, err = self._dispatch(row, ["--lane-log", log, "--round", "1"])
        self.assertEqual(code, 0, err)
        self.assertEqual(len(self.specs), 1)
        self.assertIn("ai-kit-spec: lane-a: 'interactive' must be a boolean; read as not "
                      "interactive", err.splitlines())
        self.assertTrue(os.path.exists(log))

    def test_transport_record_flag_names_the_path_and_resumes(self):
        seed_cache(self.env, "opencode", "opencode 1.2.3",
                   describe_fact("opencode", source="opencode 1.2.3 live resume"))
        log_dir = os.path.join(self.tmp, "logs")
        os.makedirs(log_dir)
        extra = ["--transport-record", self.record, "--round", "1",
                 "--lane-log", os.path.join(log_dir, "lanes.jsonl")]
        code, _out, _err = self._dispatch(self.OPENCODE, extra)
        self.assertEqual(code, 0)
        entry = lane_transport.read_record(self.record)["lanes"]["review:0:lane-a"]
        self.assertEqual((entry["transport"], entry["session_id"], entry["rounds"]),
                         ("subprocess", "fake-sid-1", 1))
        self.assertFalse(os.path.exists(os.path.join(log_dir, "transport.json")))
        code, _out, err = self._dispatch(self.OPENCODE, extra)
        self.assertEqual(code, 0, err)
        self.assertEqual(self.specs[-1].session_id, "fake-sid-1")
        self.assertEqual(self.transport_lines(err), [
            "ai-kit-spec: transport review:0:lane-a: resume (verified resume, round 2 of 3)"])
        entry = lane_transport.read_record(self.record)["lanes"]["review:0:lane-a"]
        self.assertEqual((entry["transport"], entry["rounds"]), ("resume", 2))

    def test_native_or_runtimeless_rows_write_no_record(self):
        rows = ({"key": "lane-a", "model": "placeholder-model-1", "vendor": "",
                 "runtime": "opencode", "route": "native", "extra": {}},
                {"key": "lane-b", "model": "placeholder-model-2", "vendor": "v",
                 "command": "my-cli {prompt}", "extra": {}})
        for row in rows:
            with self.subTest(key=row["key"]):
                code, _out, err = self._dispatch(row, ["--transport-record", self.record])
                self.assertEqual(code, 0, err)
                self.assertEqual(self.transport_lines(err), [])
                self.assertFalse(os.path.exists(self.record))
                self.assertFalse(os.path.exists(self.record + ".lock"))

    def test_codex_review_mode_never_resumes(self):
        describe = describe_fact("codex")
        describe["runtimes"]["codex"]["session"]["noResume"] = ["review", "sandbox"]
        seed_cache(self.env, "codex", "codex-cli 0.170.0", describe)
        row = {"key": "lane-a", "model": "placeholder-model-1", "vendor": "",
               "runtime": "codex", "command": None, "extra": {}}
        lane_transport.write_record(self.record, {"version": 1, "lanes": {
            "review:0:lane-a": {"transport": "resume", "session_id": "fake-sid-9",
                                "rounds": 1, "pane": None, "runtime": "codex",
                                "model": "placeholder-model-1", "mode": "review"}}})
        code, _out, err = self._dispatch(row, ["--transport-record", self.record])
        self.assertEqual(code, 0, err)
        self.assertIsNone(self.specs[0].session_id)
        self.assertEqual(self.transport_lines(err), [
            "ai-kit-spec: transport review:0:lane-a: subprocess (no verified resume)"])
        entry = lane_transport.read_record(self.record)["lanes"]["review:0:lane-a"]
        self.assertEqual((entry["transport"], entry["session_id"], entry["rounds"]),
                         ("subprocess", "fake-sid-1", 1))

    def test_a_foreign_record_runs_a_plain_round_and_is_left_alone(self):
        with open(self.record, "wb") as handle:
            handle.write(FOREIGN)
        code, _out, err = self._dispatch(self.OPENCODE, ["--transport-record", self.record])
        self.assertEqual(code, 0, err)
        self.assertIsNone(self.specs[0].session_id)
        self.assertEqual(self.transport_lines(err), [])
        self.assertIn(f"ai-kit-spec: transport record {self.record} unusable: not a transport "
                      "record; the round runs as a fresh subprocess", err.splitlines())
        with open(self.record, "rb") as handle:
            self.assertEqual(handle.read(), FOREIGN)

    def test_a_record_that_turns_foreign_mid_round_is_left_alone(self):
        self.foreign_mid_round = True
        code, _out, err = self._dispatch(self.OPENCODE, ["--transport-record", self.record])
        self.assertEqual(code, 0, err)
        self.assertEqual([line for line in err.splitlines()
                          if line.startswith("ai-kit-spec: transport record ")],
                         [f"ai-kit-spec: transport record {self.record} unusable: not a transport "
                          "record; the round is not counted"])
        with open(self.record, "rb") as handle:
            self.assertEqual(handle.read(), FOREIGN)

    def test_an_unreadable_prompt_starts_no_transport_round(self):
        self.prompt = os.path.join(self.tmp, "missing.txt")
        code, _out, err = self._dispatch(self.OPENCODE, ["--transport-record", self.record])
        self.assertEqual(code, 1)
        self.assertEqual(self.transport_lines(err), [])
        self.assertFalse(os.path.exists(self.record + ".lock"))


_PANE_LABEL = {"state": "verified", "source": "fake"}


def _pane_dict(run_dir: str, token: str = "0123456789ab") -> dict:
    """The pane open_pane's fake returns: a token, tab, pane and the temp run dir."""
    return {"token": token, "tab_id": "t1", "pane_id": "p1", "run_dir": run_dir}


def _status_for(spec, returncode) -> dict:
    """A status line that names this run, so run_runner's trailer check keeps it."""
    code = "" if returncode is None else str(returncode)
    return {"status": "ok", "exit": code, "cli": spec.runtime or "-",
            "model": spec.model or "-"}


class _PaneRoundHarness:
    """Fake pane verbs around one record: open, round, verdict, close and pid probes."""

    def __init__(self, case: unittest.TestCase, root: str):
        self.case = case
        self.root = root
        self.run_dir = os.path.join(root, "run")
        os.makedirs(self.run_dir)
        self.opened: list[dict] = []
        self.closed: list[dict] = []
        self.jobs: list = []
        self.printed: list[str] = []
        self.kills: list = []
        self.runner_calls: list = []
        self.open_result: dict | None = _pane_dict(self.run_dir)
        self.verdict = {"code": 0, "signal": None, "bad": None, "out": "",
                        "status": None, "err_tail": ""}
        self.round_end = "rc"
        self.alive = False
        self.launcher: int | None = 4242
        self.seen_busy: list = []
        self.env = scratch_env(root)
        self.env["HERDR_ENV"] = "1"
        self._patches = [
            mock.patch.dict(lane_transport.PANE_LABEL, _PANE_LABEL),
            mock.patch.object(herdr_pane, "open_pane", self._open),
            mock.patch.object(herdr_pane, "run_round", self._round),
            mock.patch.object(herdr_pane, "read_verdict", lambda _run_dir: dict(self.verdict)),
            mock.patch.object(herdr_pane, "close_pane", self._close),
            mock.patch.object(herdr_pane, "pid_alive", lambda _pid: self.alive),
            mock.patch.object(herdr_pane, "live_launcher_pid",
                              lambda _pane, _alive_fn=None: self.launcher, create=True),
            mock.patch.object(runner_dispatch, "run_runner",
                              wraps=runner_dispatch.run_runner,
                              side_effect=self._ran),
        ]

    def __enter__(self):
        for patch in self._patches:
            patch.start()
            self.case.addCleanup(patch.stop)
        return self

    def __exit__(self, *_exc):
        return False

    def _open(self, role, runtime, cwd, env=None, seams=None):
        self.opened.append({"role": role, "runtime": runtime, "cwd": cwd})
        if self.open_result is None:
            return None
        return dict(self.open_result)

    def _close(self, pane, env=None, seams=None):
        self.closed.append(dict(pane))
        return True

    def _round(self, pane, job, seams=None):
        entry = lane_transport.read_record(
            os.path.join(self.root, "record.json"))["lanes"].get("execute:0:lane")
        self.seen_busy.append(entry.get("busy_pid") if isinstance(entry, dict) else None)
        self.jobs.append(job)
        with open(os.path.join(self.run_dir, "err"), "w", encoding="utf-8") as handle:
            handle.write(self.verdict.get("err_tail") or "")
        if self.round_end != "rc":
            pane["closed"] = True
        return self.round_end

    def _ran(self, spec, prompt, seams=None):
        self.runner_calls.append((spec, prompt, seams))
        return mock.DEFAULT

    def seams(self):
        """Runner seams: a fake node and template, no route, the test env, recording seams."""
        return runner_dispatch.RunnerSeams(
            which_fn=lambda _name, path=None: "fake-node",
            runner_path_fn=lambda: "fake-runner.mjs",
            route_fn=lambda *_args: None,
            env_fn=lambda: dict(self.env),
            kill_fn=lambda pgid, sig: self.kills.append((pgid, sig)),
            print_fn=self.printed.append,
        )

    def start(self, pid: int = 111, **pair) -> lane_transport.RoundStart:
        """A pane-eligible execute round against this harness's record."""
        return lane_transport.RoundStart(
            os.path.join(self.root, "record.json"),
            request(interactive=True, herdr_ok=True, verified=frozenset({"pane"}),
                    lane_id="execute:0:lane", **pair),
            pid)

    def spec(self, timeout_s: int = 30):
        return runner_dispatch.RunnerSpec(
            "codex", "placeholder-model-1", "exec", timeout_s, cwd=self.root)


class TestPaneRunner(unittest.TestCase):
    """The pane branch of pane_runner: one run_runner call per round, reuse, busy, renewal."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = tmp.name
        self.harness = _PaneRoundHarness(self, self.tmp)
        self.harness.__enter__()

    def _fallback_calls(self):
        calls = []

        def fallback(spec, tiers, prompt, seams=None):
            calls.append(prompt)
            return runner_dispatch.RunnerResult(0, "", None, None, False, [], "")

        return calls, fallback

    def test_a_foreign_record_falls_back_with_one_line_and_is_left_alone(self):
        start = self.harness.start()
        with open(start.record_path, "wb") as handle:
            handle.write(FOREIGN)
        calls, fallback = self._fallback_calls()
        with contextlib.redirect_stderr(io.StringIO()) as err:
            lane_transport.pane_runner(start, self.tmp, "execute", fallback)(
                self.harness.spec(), [30], "do the task", self.harness.seams())
        self.assertEqual(calls, ["do the task"])
        self.assertEqual(self.harness.opened, [])
        self.assertEqual(err.getvalue().splitlines(), [
            f"ai-kit-spec: transport record {start.record_path} unusable: not a transport "
            "record; the round runs as a fresh subprocess"])
        with open(start.record_path, "rb") as handle:
            self.assertEqual(handle.read(), FOREIGN)

    def test_a_record_turning_foreign_in_a_pane_round_prints_one_line(self):
        start = self.harness.start()
        with open(start.record_path, "wb") as handle:
            handle.write(FOREIGN)
        calls, fallback = self._fallback_calls()
        with contextlib.redirect_stderr(io.StringIO()) as err:
            lane_transport.pane_runner(start, self.tmp, "execute", fallback)(
                self.harness.spec(), [30], "do the task", self.harness.seams())
            lane_transport.try_end_round(
                start, lane_transport.TransportChoice("pane", None, "held"), None)
        self.assertEqual(calls, ["do the task"])
        self.assertEqual(len([line for line in err.getvalue().splitlines()
                              if " unusable: " in line]), 1)
        with open(start.record_path, "rb") as handle:
            self.assertEqual(handle.read(), FOREIGN)

    def test_a_pane_that_cannot_be_recorded_is_closed_before_the_fallback(self):
        start = self.harness.start()

        def open_then_foreign(role, runtime, cwd, env=None, seams=None):
            with open(start.record_path, "wb") as handle:
                handle.write(FOREIGN)
            return _pane_dict(self.harness.run_dir)

        calls, fallback = self._fallback_calls()
        with mock.patch.object(herdr_pane, "open_pane", open_then_foreign), \
                contextlib.redirect_stderr(io.StringIO()) as err:
            lane_transport.pane_runner(start, self.tmp, "execute", fallback)(
                self.harness.spec(), [30], "do the task", self.harness.seams())
        self.assertEqual(calls, ["do the task"])
        self.assertEqual([pane["token"] for pane in self.harness.closed], ["0123456789ab"])
        self.assertEqual(self.harness.jobs, [])
        self.assertEqual(len([line for line in err.getvalue().splitlines()
                              if " unusable: " in line]), 1)
        with open(start.record_path, "rb") as handle:
            self.assertEqual(handle.read(), FOREIGN)

    def _run(self, start=None, tiers=(30, 90), prompt="do the task"):
        start = self.harness.start() if start is None else start
        runner = lane_transport.pane_runner(
            start, self.tmp, "execute", lambda *_args: self.fail("fallback"))
        spec = self.harness.spec()
        self.harness.verdict["status"] = _status_for(spec, 0)
        self.harness.verdict["err_tail"] = "cross-ai: starting\n"
        result = runner(spec, list(tiers), prompt, self.harness.seams())
        lane_transport.end_round(start, lane_transport.TransportChoice("pane", None, "held"), None)
        return result

    def test_round_one_opens_and_round_two_reuses(self):
        first = self._run(prompt="round one")
        second = self._run(self.harness.start(pid=222), prompt="round two")
        self.assertEqual(len(self.harness.opened), 1)
        self.assertEqual(len(self.harness.runner_calls), 2)
        for spec, _prompt, seams in self.harness.runner_calls:
            self.assertEqual(spec.host, "none")
            self.assertEqual(spec.timeout_s, 90)
            self.assertIsNotNone(seams.spawn_fn)
        self.assertEqual([job.prompt for job in self.harness.jobs], ["round one", "round two"])
        job = self.harness.jobs[0]
        self.assertIn("--host", job.argv)
        self.assertEqual(job.argv[job.argv.index("--host") + 1], "none")
        self.assertEqual(job.argv.count("--child-pgid-file"), 1)
        self.assertEqual(job.timeout_s, 90 + runner_dispatch.RUNNER_OUTER_MARGIN_S
                         + runner_dispatch._KILL_GRACE_S)
        self.assertEqual(job.env, runner_dispatch.child_env(env=self.harness.env))
        self.assertEqual(first.returncode, 0)
        self.assertEqual(second.returncode, 0)
        self.assertEqual(first.stderr_tail, "cross-ai: starting\n")
        self.assertIn("cross-ai: starting", self.harness.printed)
        entry = lane_transport.read_record(self.harness.start().record_path)["lanes"]
        self.assertEqual(entry["execute:0:lane"]["pane"]["token"], "0123456789ab")
        self.assertEqual(entry["execute:0:lane"]["rounds"], 2)
        self.assertEqual(self.harness.seen_busy, [111, 222])
        self.assertIsNone(entry["execute:0:lane"]["busy_pid"])

    def test_a_live_busy_pid_falls_back_and_stays(self):
        calls = []

        def fallback(spec, tiers, prompt, seams=None):
            calls.append((spec, tiers, prompt))
            return runner_dispatch.RunnerResult(0, "", None, None, False, [], "")

        first = self.harness.start(pid=111)
        lane_transport.pane_runner(
            first, self.tmp, "execute", fallback)(
            self.harness.spec(), [30], "round one", self.harness.seams())
        self.harness.alive = True
        second = self.harness.start(pid=222)
        choice = lane_transport.TransportChoice("pane", None, "held")
        with contextlib.redirect_stderr(io.StringIO()) as err:
            lane_transport.pane_runner(second, self.tmp, "execute", fallback)(
                self.harness.spec(), [30], "round two", self.harness.seams())
        lane_transport.end_round(second, choice, None)
        entry = lane_transport.read_record(first.record_path)["lanes"]["execute:0:lane"]
        self.assertNotIn("transport", entry)
        self.assertEqual(entry["rounds"], 0)
        self.assertIn("ai-kit-spec: transport execute:0:lane: subprocess "
                      "(pane fallback: pane busy)", err.getvalue().splitlines())
        self.assertEqual(entry["busy_pid"], 111)
        self.assertEqual(len(calls), 1)
        self.harness.alive = False
        lane_transport.end_round(first, choice, None)
        third = self.harness.start(pid=333)
        lane_transport.pane_runner(third, self.tmp, "execute", fallback)(
            self.harness.spec(), [30], "round three", self.harness.seams())
        self.assertEqual(len(self.harness.opened), 1)
        self.assertEqual(len(self.harness.jobs), 2)
        self.assertEqual(len(calls), 1)

    def test_open_pane_none_clears_busy_and_falls_back(self):
        self.harness.open_result = None
        calls = []

        def fallback(spec, tiers, prompt, seams=None):
            calls.append(prompt)
            return runner_dispatch.RunnerResult(0, "", None, None, False, [], "")

        start = self.harness.start()
        lane_transport.pane_runner(start, self.tmp, "execute", fallback)(
            self.harness.spec(), [30], "do the task", self.harness.seams())
        lane_transport.end_round(start, lane_transport.TransportChoice("pane", None, "held"), None)
        entry = lane_transport.read_record(start.record_path)["lanes"]["execute:0:lane"]
        self.assertIsNone(entry["busy_pid"])
        self.assertEqual(entry["transport"], "subprocess")
        self.assertEqual(calls, ["do the task"])
        self.assertEqual(self.harness.jobs, [])

    def _renewed(self, entry: dict):
        lane_transport.write_record(self.harness.start().record_path,
                                    {"version": 1, "lanes": {"execute:0:lane": entry}})
        self._run()
        record = lane_transport.read_record(self.harness.start().record_path)
        return record["lanes"]["execute:0:lane"]

    def test_renewal_closes_the_old_pane_and_restarts_the_count(self):
        old = _pane_dict(os.path.join(self.tmp, "old"), token="abcdef012345")
        base = {"transport": "pane", "session_id": None, "pane": old, "runtime": "codex",
                "model": "placeholder-model-1", "mode": "execute", "busy_pid": None}
        cases = ({"rounds": lane_transport.TRANSPORT_RENEW_ROUNDS},
                 {"rounds": 1, "model": "placeholder-model-2"},
                 {"rounds": 1, "runtime": "opencode"},
                 {"rounds": 1, "mode": "review"},
                 {"rounds": 1, "transport": "subprocess"},
                 {"rounds": 1, "pane": {**old, "closed": True}})
        for override in cases:
            with self.subTest(override=sorted(override)):
                self.harness.opened.clear()
                self.harness.closed.clear()
                entry = self._renewed({**base, **override})
                self.assertEqual(len(self.harness.closed), 1)
                self.assertEqual(self.harness.closed[0]["token"], "abcdef012345")
                self.assertEqual(len(self.harness.opened), 1)
                self.assertEqual(entry["rounds"], 1)
                self.assertEqual(entry["pane"]["token"], "0123456789ab")

    def test_a_timeout_or_a_gone_launcher_drops_the_pane(self):
        ends = (("timeout", "timeout", True),
                ("launcher gone", "dispatch_unavailable", False))
        for end, reason, timed in ends:
            with self.subTest(end=end):
                self.harness.round_end = end
                self.harness.jobs.clear()
                result = self._run()
                self.assertEqual(result.reason, reason)
                self.assertIs(result.timed_out, timed)
                entry = lane_transport.read_record(
                    self.harness.start().record_path)["lanes"]["execute:0:lane"]
                self.assertIsNone(entry["pane"])
                self.assertEqual(len(self.harness.jobs), 1)

    def test_a_signal_verdict_keeps_a_none_returncode(self):
        spec = self.harness.spec()
        self.harness.verdict = {"code": None, "signal": "SIGKILL", "bad": None, "out": "",
                                "status": {"status": "ok", "exit": "SIGKILL",
                                           "cli": spec.runtime, "model": spec.model},
                                "err_tail": "killed\n"}
        start = self.harness.start()
        runner = lane_transport.pane_runner(
            start, self.tmp, "execute", lambda *_args: self.fail("fallback"))
        result = runner(spec, [30], "do the task", self.harness.seams())
        self.assertIsNone(result.returncode)
        self.assertEqual(result.reason,
                         runner_dispatch.reason_for_status(None, None))

    def test_a_dead_launcher_is_renewed_before_the_round(self):
        old = _pane_dict(os.path.join(self.tmp, "old"), token="abcdef012345")
        self.harness.launcher = None
        entry = self._renewed({"transport": "pane", "session_id": None, "rounds": 1, "pane": old,
                               "runtime": "codex", "model": "placeholder-model-1",
                               "mode": "execute", "busy_pid": None})
        self.assertEqual([pane["token"] for pane in self.harness.closed], ["abcdef012345"])
        self.assertEqual(len(self.harness.opened), 1)
        self.assertEqual(entry["pane"]["token"], "0123456789ab")
        self.assertEqual(entry["rounds"], 1)

    def test_a_failed_open_after_a_renewal_forgets_the_old_pane(self):
        old = _pane_dict(os.path.join(self.tmp, "old"), token="abcdef012345")
        self.harness.open_result = None
        start = self.harness.start()
        lane_transport.write_record(start.record_path, {"version": 1, "lanes": {"execute:0:lane": {
            "transport": "pane", "session_id": None,
            "rounds": lane_transport.TRANSPORT_RENEW_ROUNDS, "pane": old, "runtime": "codex",
            "model": "placeholder-model-1", "mode": "execute", "busy_pid": None}}})
        calls = []

        def fallback(spec, tiers, prompt, seams=None):
            calls.append(prompt)
            return runner_dispatch.RunnerResult(0, "", None, None, False, [], "")

        with contextlib.redirect_stderr(io.StringIO()) as err:
            lane_transport.pane_runner(start, self.tmp, "execute", fallback)(
                self.harness.spec(), [30], "do the task", self.harness.seams())
        entry = lane_transport.read_record(start.record_path)["lanes"]["execute:0:lane"]
        self.assertIsNone(entry["pane"])
        self.assertIsNone(entry["busy_pid"])
        self.assertEqual(calls, ["do the task"])
        self.assertEqual([pane["token"] for pane in self.harness.closed], ["abcdef012345"])
        self.assertIn("ai-kit-spec: transport execute:0:lane: subprocess "
                      "(pane fallback: pane did not open)", err.getvalue().splitlines())

    def test_claim_returns_the_entry_it_wrote_and_prepare_reads_no_record(self):
        start = self.harness.start(pid=111)
        lane_transport.write_record(start.record_path, {"version": 1, "lanes": {
            "execute:0:lane": {"transport": "pane", "rounds": 2, "pane": None}}})
        entry = lane_transport._claim_pane(start)
        self.assertEqual(entry, {"transport": "pane", "rounds": 2, "pane": None, "busy_pid": 111})
        self.harness.alive = True
        self.assertIsNone(lane_transport._claim_pane(self.harness.start(pid=222)))
        assert entry is not None
        with mock.patch.object(lane_transport, "read_record",
                               side_effect=AssertionError("unlocked record read")):
            pane = lane_transport._prepare_pane(start, entry, self.harness.spec(), self.tmp,
                                                "execute")
        assert pane is not None
        self.assertEqual(pane["token"], "0123456789ab")


def _which_herdr(name, path=None):
    """herdr is present; nothing else is."""
    return "fake-herdr" if name == "herdr" else None


class TestPaneThroughDispatchTask(unittest.TestCase):
    """dispatch-task --transport-record runs an interactive herdr lane through pane_runner."""

    def test_the_round_reaches_run_runner_with_a_spawn_fn(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = scratch_env(tmp)
            env["HERDR_ENV"] = "1"
            target = os.path.join(tmp, "project")
            os.makedirs(target)
            record = os.path.join(tmp, "record.json")
            for name, text in (("prompt.txt", "do the task"), ("format.md", "REPLY.")):
                with open(os.path.join(tmp, name), "w", encoding="utf-8") as stream:
                    stream.write(text)
            row = {"key": "lane-a", "runtime": "opencode",
                   "model": "fake/placeholder-model-1", "interactive": True}
            injection = {"mode": "external_cli", "key": "lane-a", "runtime": "opencode",
                         "model": "fake/placeholder-model-1"}
            seen = []

            def wrapped(request, guidance=None, seams=None):
                assert seams is not None
                real = seams.dispatch_execute_fn

                def spy(spec, inner=None):
                    active = inner or real.keywords["seams"]
                    return execute_dispatch.dispatch_execute(
                        spec, active._replace(
                            compose_fn=lambda *_args: capability_block.ComposeResult(),
                            runner_fn=active.runner_fn,
                            print_fn=lambda _line: None))

                return dispatch_injection.dispatch_superpowers_task(
                    request, guidance, seams=seams._replace(dispatch_execute_fn=spy,
                                                            env_fn=lambda: dict(env)))

            def spy_runner(spec, prompt, seams=None):
                seen.append(seams)
                return runner_dispatch.RunnerResult(
                    0, "", _status_for(spec, 0), None, False, ["fake-node"], "")

            argv = ["dispatch-task", "--injection-json", json.dumps(injection),
                    "--prompt-file", os.path.join(tmp, "prompt.txt"),
                    "--target-dir", target, "--heartbeat-interval", "30",
                    "--timeout", "900", "--format-block-file", os.path.join(tmp, "format.md"),
                    "--report-file", os.path.join(tmp, "report.md"),
                    "--transport-record", record]
            deps = adapter_cli.CliDeps()._replace(
                assemble_candidates_fn=lambda *_args, **_kwargs: (
                    [{"key": row["key"], "roster_entry": dict(row)}], []),
                dispatch_superpowers_task_fn=wrapped,
                detect_tool_availability_fn=lambda: {},
                resolve_agents_tooling_path_fn=lambda: None,
                cbm_registered_fn=lambda _name: False,
                which_fn=_which_herdr,
                env_fn=lambda: dict(env),
                stdout=io.StringIO(),
            )
            os.makedirs(os.path.join(tmp, "run"))
            with mock.patch.dict(lane_transport.PANE_LABEL, _PANE_LABEL), \
                    mock.patch.object(herdr_pane, "open_pane",
                                      return_value=_pane_dict(os.path.join(tmp, "run"))), \
                    mock.patch.object(herdr_pane, "run_round", return_value="rc"), \
                    mock.patch.object(herdr_pane, "read_verdict",
                                      return_value={"code": 0, "out": "", "err_tail": ""}), \
                    mock.patch.object(runner_dispatch, "run_runner", spy_runner):
                code = adapter_cli.main(argv, deps=deps)
            self.assertEqual(code, 0)
            self.assertEqual(len(seen), 1)
            self.assertIsNotNone(seen[0].spawn_fn)


class TestPaneThroughDispatchReviewer(unittest.TestCase):
    """dispatch-reviewer: an explicit record gets a pane; a lane-log record never does."""

    def _dispatch(self, tmp, extra, which):
        reviewers = os.path.join(tmp, "reviewers.json")
        prompt = os.path.join(tmp, "prompt.txt")
        row = {"key": "lane-a", "model": "placeholder-model-1", "vendor": "",
               "runtime": "opencode", "command": None,
               "extra": {"interactive": True}}
        with open(reviewers, "w", encoding="utf-8") as stream:
            json.dump([row], stream)
        with open(prompt, "w", encoding="utf-8") as stream:
            stream.write("review this")
        opened = []
        seen = []

        def fake_dispatch(spec, seams=None):
            assert seams is not None
            seen.append(seams)
            # the pane branch is the only one whose tiers callable is pane_runner's
            if seams.runner_tiers_fn.__name__ != "run":
                return {"stdout": "", "returncode": 0, "timed_out": False, "reason": None,
                        "status": {"status": "ok", "session": "fake-sid-1"}, "argv": []}
            result = seams.runner_tiers_fn(
                reviewer_dispatch.review_spec(
                    spec.reviewer_entry["runtime"], spec.reviewer_entry["model"], {},
                    spec.timeout_tiers[0]),
                spec.timeout_tiers, spec.prompt, seams.runner_seams)
            return {"stdout": result.stdout, "returncode": result.returncode,
                    "timed_out": result.timed_out, "reason": result.reason,
                    "status": result.status, "argv": result.argv}

        def spy_runner(spec, _prompt, seams=None):
            opened.append(seams)
            return runner_dispatch.RunnerResult(
                0, "", _status_for(spec, 0), None, False, ["fake-node"], "")

        argv = ["dispatch-reviewer", "--reviewers-json", reviewers, "--index", "0",
                "--prompt-file", prompt, "--timeout-tiers", "60", *extra]
        env = scratch_env(tmp)
        env["HERDR_ENV"] = "1"
        os.makedirs(os.path.join(tmp, "run"))
        with mock.patch.dict(lane_transport.PANE_LABEL, _PANE_LABEL), \
                mock.patch.object(herdr_pane, "open_pane",
                                  return_value=_pane_dict(os.path.join(tmp, "run"))), \
                mock.patch.object(herdr_pane, "run_round", return_value="rc"), \
                mock.patch.object(herdr_pane, "read_verdict",
                                  return_value={"code": 0, "out": "", "err_tail": ""}), \
                mock.patch.object(runner_dispatch, "run_runner", spy_runner):
            code = review_cli.main(argv, env_fn=lambda: dict(env), which_fn=which,
                                   dispatch_reviewer_fn=fake_dispatch)
        return code, opened, seen

    def test_an_explicit_record_runs_through_pane_runner(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, opened, _seen = self._dispatch(
                tmp, ["--transport-record", os.path.join(tmp, "record.json")], _which_herdr)
            self.assertEqual(code, 0)
            self.assertEqual(len(opened), 1)
            self.assertIsNotNone(opened[0].spawn_fn)

    def test_a_lane_log_record_never_opens_a_pane(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = os.path.join(tmp, "lanes.jsonl")
            code, opened, seen = self._dispatch(
                tmp, ["--lane-log", log, "--round", "1"], _which_herdr)
            self.assertEqual(code, 0)
            self.assertEqual(opened, [])
            # pane_runner only builds its closure; the dummy start is never read
            pane_run = lane_transport.pane_runner(
                lane_transport.RoundStart("", request()), tmp, "review", None)
            # the pane branch's tiers callable is pane_runner's closure;
            # the lane-log round must not get it
            self.assertEqual(pane_run.__name__, "run")
            self.assertNotEqual(seen[0].runner_tiers_fn.__name__, pane_run.__name__)


def _pane_entry(pane) -> dict:
    """A recorded pane lane, not marked busy."""
    return {"transport": "pane", "session_id": None, "rounds": 1, "pane": pane,
            "runtime": "codex", "model": "placeholder-model-1", "mode": "execute",
            "busy_pid": None}


def _sweep_result(returncode=0, reason=None, stderr_tail="") -> runner_dispatch.RunnerResult:
    """A fake sweep result; the counts line lives in stderr_tail."""
    return runner_dispatch.RunnerResult(
        returncode, "", None, reason, False, ["fake-node"], stderr_tail)


class TestCloseTransports(unittest.TestCase):
    """close-transports through the adapter CLI, with faked close and sweep seams."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self._tmp.name, "record.json")
        self.stdout = io.StringIO()
        self.closed = []
        self.swept = []

    def tearDown(self):
        self._tmp.cleanup()

    def _seed(self, lanes: dict) -> None:
        lane_transport.write_record(self.path, {"version": 1, "lanes": lanes})

    def _close(self, pane) -> bool:
        self.closed.append(pane)
        return pane.get("ok") is True

    def _sweep(self):
        self.swept.append(1)
        return _sweep_result(stderr_tail="noise\ncross-ai: sweep: closed 1\n")

    def _run(self, close_fn=None, sweep_fn=None, path=None):
        deps = adapter_cli.CliDeps()._replace(
            close_pane_fn=self._close if close_fn is None else close_fn,
            run_sweep_fn=self._sweep if sweep_fn is None else sweep_fn,
            stdout=self.stdout)
        argv = ["close-transports", "--transport-record", self.path if path is None else path]
        with contextlib.redirect_stderr(io.StringIO()) as captured:
            code = adapter_cli.main(argv, deps=deps)
        return code, captured.getvalue()

    def _payload(self) -> dict:
        return json.loads(self.stdout.getvalue())

    def test_one_closed_pane_removes_the_record_and_keeps_the_lock(self):
        self._seed({"execute:0:lane-a": _pane_entry({"ok": True, "token": "0123456789ab"})})
        code, _err = self._run()
        self.assertEqual(code, 0)
        self.assertEqual(self._payload(), {
            "closed": ["execute:0:lane-a"], "failed": [], "busy": [],
            "sweep": "cross-ai: sweep: closed 1"})
        self.assertFalse(os.path.lexists(self.path))
        self.assertTrue(os.path.lexists(self.path + ".lock"))
        self.assertEqual(self.swept, [1])

    def test_a_false_close_keeps_the_entry_and_exits_one(self):
        pane = {"ok": False, "token": "0123456789ab"}
        self._seed({"execute:0:lane-a": _pane_entry(pane)})
        code, _err = self._run()
        self.assertEqual(code, 1)
        self.assertEqual(self._payload()["failed"], ["execute:0:lane-a"])
        self.assertEqual(self._payload()["closed"], [])
        saved = lane_transport.read_record(self.path)
        self.assertEqual(saved["lanes"]["execute:0:lane-a"]["pane"], pane)
        self.assertTrue(os.path.lexists(self.path))
        self.assertEqual(self.swept, [1])

    def test_a_close_raising_oserror_is_a_failed_entry(self):
        def boom(_pane):
            raise OSError("pane gone")

        self._seed({"execute:0:lane-a": _pane_entry({"token": "0123456789ab"})})
        code, _err = self._run(close_fn=boom)
        self.assertEqual(code, 1)
        self.assertEqual(self._payload()["failed"], ["execute:0:lane-a"])
        self.assertTrue(os.path.lexists(self.path))

    def test_a_live_busy_pid_is_listed_busy_and_not_closed(self):
        pane = {"ok": True, "token": "0123456789ab"}
        entry = {**_pane_entry(pane), "busy_pid": 4242}
        self._seed({"execute:0:lane-a": entry})
        with mock.patch.object(herdr_pane, "pid_alive", return_value=True) as alive:
            code, _err = self._run()
        self.assertEqual(code, 0)
        self.assertEqual(self._payload()["busy"], ["execute:0:lane-a"])
        self.assertEqual(self.closed, [])
        alive.assert_called_once_with(4242)
        saved = lane_transport.read_record(self.path)
        self.assertEqual(saved["lanes"]["execute:0:lane-a"]["pane"], pane)
        self.assertTrue(os.path.lexists(self.path))

    def test_an_entry_without_a_pane_dict_is_left_out_of_every_list(self):
        bare = {**_pane_entry(None), "pane": None}
        self._seed({"execute:0:bare": bare,
                    "execute:0:lane-a": _pane_entry({"ok": True})})
        code, _err = self._run()
        self.assertEqual(code, 0)
        self.assertEqual(self._payload()["closed"], ["execute:0:lane-a"])
        self.assertNotIn("execute:0:bare", json.dumps(self._payload()["closed"]))
        self.assertEqual(self._payload()["failed"], [])
        self.assertEqual(self._payload()["busy"], [])

    def test_a_pane_whose_run_dir_is_gone_counts_as_closed(self):
        gone = {"ok": False, "token": "0123456789ab",
                "run_dir": os.path.join(self._tmp.name, "gone")}
        kept = {"ok": False, "token": "abcdef012345", "run_dir": self._tmp.name}
        self._seed({"execute:0:lane-a": _pane_entry(gone), "execute:0:lane-b": _pane_entry(kept)})
        code, _err = self._run()
        self.assertEqual(code, 1)
        self.assertEqual(self._payload()["closed"], ["execute:0:lane-a"])
        self.assertEqual(self._payload()["failed"], ["execute:0:lane-b"])
        saved = lane_transport.read_record(self.path)["lanes"]
        self.assertIsNone(saved["execute:0:lane-a"]["pane"])
        self.assertEqual(saved["execute:0:lane-b"]["pane"], kept)

    def test_a_missing_record_skips_the_sweep_and_creates_no_lock(self):
        missing = os.path.join(self._tmp.name, "absent.json")
        code, _err = self._run(path=missing)
        self.assertEqual(code, 0)
        self.assertEqual(self._payload(), {
            "closed": [], "failed": [], "busy": [],
            "sweep": "skipped: no transport record"})
        self.assertEqual(self.swept, [])
        self.assertFalse(os.path.lexists(missing + ".lock"))

    def test_sweep_outcomes_stay_exit_zero(self):
        cases = (
            (_sweep_result(returncode=1, reason="sweep_failed"), "unavailable: sweep_failed"),
            (_sweep_result(stderr_tail="no counts here\n"), "ran"),
            (_sweep_result(stderr_tail="cross-ai: sweep: closed 1\n"
                           "cross-ai: sweep: closed 2\n"), "cross-ai: sweep: closed 2"),
        )
        for result, expected in cases:
            with self.subTest(expected=expected):
                self.stdout = io.StringIO()
                self._seed({"execute:0:lane-a": _pane_entry({"ok": True})})
                code, _err = self._run(sweep_fn=lambda held=result: held)
                self.assertEqual(code, 0)
                self.assertEqual(self._payload()["sweep"], expected)

    def test_a_sweep_raising_oserror_reports_the_error_text(self):
        def boom():
            raise OSError("node missing")

        self._seed({"execute:0:lane-a": _pane_entry({"ok": True})})
        code, _err = self._run(sweep_fn=boom)
        self.assertEqual(code, 0)
        self.assertEqual(self._payload()["sweep"], "unavailable: node missing")

    def test_a_foreign_record_exits_two_and_is_not_rewritten(self):
        with open(self.path, "w", encoding="utf-8") as handle:
            handle.write("{" + '"other": 1}')
        with open(self.path, "rb") as handle:
            before = handle.read()
        code, err = self._run()
        self.assertEqual(code, 2)
        self.assertEqual(err, f"close-transports: unreadable transport record {self.path}\n")
        with open(self.path, "rb") as handle:
            self.assertEqual(handle.read(), before)
        self.assertEqual(self.swept, [])
        self.assertEqual(self.stdout.getvalue(), "")

    def test_a_non_json_record_exits_two_unchanged(self):
        with open(self.path, "wb") as handle:
            handle.write(b"not json")
        code, err = self._run()
        self.assertEqual(code, 2)
        self.assertEqual(err, f"close-transports: unreadable transport record {self.path}\n")
        with open(self.path, "rb") as handle:
            self.assertEqual(handle.read(), b"not json")
        self.assertEqual(self.swept, [])

    def test_a_directory_at_the_record_path_exits_two(self):
        os.mkdir(self.path)
        code, err = self._run()
        self.assertEqual(code, 2)
        self.assertTrue(err.startswith(
            f"close-transports: cannot read transport record {self.path}: "))
        self.assertEqual(self.swept, [])
        self.assertTrue(os.path.isdir(self.path))


if __name__ == "__main__":
    unittest.main()
