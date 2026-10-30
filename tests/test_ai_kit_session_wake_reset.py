"""Reset-parser tests (QTA-04, SPEC R4 amendment): the arm tracer, the reset
grammar, the 7-day bounds, `--reset-at`, and the evidence redaction (D-28,
D-29, D-30, D-37). Fakes and scratch dirs only (D-26); nothing real is ever
armed. Tests that need a named zone skip with a reason when the system zone
database lacks it (no `tzdata` package; 26-12 checks the clean-room case)."""

import contextlib
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
import uuid
from datetime import UTC, datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "skills",
        "ai-kit-session-wake",
    ),
)

from ai_kit_session_wake import cli, units
from ai_kit_session_wake.reset_parse import (
    MAX_RESET_AHEAD_S,
    calendar_line,
    cap_code_points,
    check_bounds,
    parse_reset_at,
    parse_reset_text,
    redact,
)
from ai_kit_session_wake.state import read_state, session_paths

from tests import session_wake_fakes as fakes

_NOW = datetime(2026, 10, 25, 22, 44, 0, tzinfo=UTC).timestamp()
_ZONE = "America/Santiago"
_LIMIT_TEXT = "You've hit your session limit · resets 1pm (America/Santiago)"
_WEEKLY_TEXT = "You've hit your weekly limit · resets Oct 27, 10pm (America/Santiago)"


def _zone_available() -> bool:
    try:
        ZoneInfo(_ZONE)
    except (ZoneInfoNotFoundError, ValueError):
        return False
    return True


def _utc(*args) -> float:
    return datetime(*args, tzinfo=UTC).timestamp()


class _Scratch(unittest.TestCase):
    """Scratch root, fake bin dir, fake log; nothing survives the test."""

    def setUp(self):
        super().setUp()
        self.root = tempfile.mkdtemp(prefix="wake-reset-")
        self.addCleanup(shutil.rmtree, self.root, True)
        self.bin_dir = os.path.join(self.root, "bin")
        os.makedirs(self.bin_dir)
        self.env = fakes.scoped_env(self.root)
        fakes.fake_systemctl(self.bin_dir)
        fakes.fake_loginctl(self.bin_dir)

    def systemctl_calls(self):
        return [
            e["argv"]
            for e in fakes.read_log(self.env["AI_KIT_FAKE_LOG"])
            if e["name"] == "systemctl"
        ]

    def _claude_env(self, sid: str, host_process) -> dict:
        fakes.fake_host(self.bin_dir, "claude")
        fakes.claude_session(self.env["HOME"], sid)
        return {
            **self.env,
            "CLAUDECODE": "1",
            "CLAUDE_PID": str(host_process.pid),
            "CLAUDE_CODE_SESSION_ID": sid,
        }

    @staticmethod
    def _kill(host_process):
        host_process.kill()
        host_process.wait()


class TestResetTracer(_Scratch):
    """One reset path end to end (SC 5): an hourly arm re-armed with the
    host's limit text moves the wake to reset + 60 s, adds the absolute
    OnCalendar line, and every output marks it inferred; the fire honors
    not_before."""

    def setUp(self):
        super().setUp()
        if not _zone_available():
            self.skipTest(f"no system zone database ({_ZONE} unavailable)")

    def test_limit_text_moves_the_wake_and_the_fire_honors_not_before(self):
        sid = uuid.uuid4().hex
        launch = os.path.join(self.root, "launch")
        os.makedirs(launch)
        host = fakes.start_host_process(launch)
        self.addCleanup(self._kill, host)
        env = self._claude_env(sid, host)
        paths = session_paths(env, "claude", sid)
        timer_name, service_name = units.unit_names("claude", sid)
        timer_path = os.path.join(units.unit_dir(env), timer_name)
        reset = _utc(2026, 10, 26, 16, 0, 0)
        not_before = reset + 60

        # a first hourly arm, then the reset re-arm changes the timer text
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(0, cli.main(["arm"], seams=fakes.fixed_seams(env, _NOW)))
        hourly, reason = read_state(paths.state, "claude", sid)
        self.assertEqual("ok", reason)
        assert hourly is not None
        self.assertEqual("hourly", hourly["wake_source"])

        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(
                0,
                cli.main(
                    ["arm", "--reset-text", _LIMIT_TEXT], seams=fakes.fixed_seams(env, _NOW)
                ),
            )
        arm_text = out.getvalue()
        self.assertIn("inferred", arm_text)
        self.assertIn(
            "reset: 2026-10-26T16:00:00Z (inferred); next wake 2026-10-26T16:01:00Z = "
            "host-reported reset + 60 s margin; the host did not state this wake time",
            arm_text,
        )
        self.assertIn(
            "companion: create one one-shot in-session wake at 2026-10-26T16:01:00Z (inferred); "
            "a fire inside the limit is lost (spike 004)",
            arm_text,
        )
        with open(timer_path, encoding="utf-8") as handle:
            timer_text = handle.read()
        self.assertIn("OnCalendar=hourly", timer_text)
        self.assertIn("OnCalendar=2026-10-26 16:01:00 UTC", timer_text)
        self.assertNotIn(f"OnCalendar={_LIMIT_TEXT}", timer_text)
        state, reason = read_state(paths.state, "claude", sid)
        self.assertEqual("ok", reason)
        assert state is not None
        self.assertEqual(not_before, state["not_before"])
        self.assertEqual("reset_inferred", state["wake_source"])
        self.assertEqual("2026-10-26T16:00:00Z", state["reset_at"])
        self.assertEqual(_LIMIT_TEXT, state["reset_evidence"])

        # the changed timer text ran daemon-reload plus restart (26-03, D-28)
        self.assertIn(["--user", "restart", timer_name], self.systemctl_calls())

        status_out = io.StringIO()
        with contextlib.redirect_stdout(status_out):
            self.assertEqual(
                0,
                cli.main(
                    ["status", "--host", "claude", "--session-id", sid],
                    seams=fakes.fixed_seams(env, _NOW),
                ),
            )
        status_text = status_out.getvalue()
        self.assertIn("inferred", status_text)
        self.assertIn(
            "next wake: 2026-10-26T16:01:00Z UTC (inferred: host-reported reset + 60 s; "
            "the host did not state this wake time), then hourly",
            status_text,
        )

        # a fire one second before not_before is logged, not counted
        early = io.StringIO()
        with contextlib.redirect_stdout(early):
            self.assertEqual(
                0,
                cli.main(
                    ["fire", "--host", "claude", "--session-id", sid],
                    seams=fakes.fixed_seams(env, reset + 59),
                ),
            )
        self.assertIn("not counted", early.getvalue())
        state, _reason = read_state(paths.state, "claude", sid)
        assert state is not None
        self.assertEqual(0, state["wake_count"])

        # a fire exactly at not_before counts
        on_time = io.StringIO()
        with contextlib.redirect_stdout(on_time):
            self.assertEqual(
                0,
                cli.main(
                    ["fire", "--host", "claude", "--session-id", sid],
                    seams=fakes.fixed_seams(env, reset + 60),
                ),
            )
        self.assertIn("host alive; log only (wake 1/24)", on_time.getvalue())
        state, _reason = read_state(paths.state, "claude", sid)
        assert state is not None
        self.assertEqual(1, state["wake_count"])

        # nothing of the wake was lost along the way (the wants link and the
        # stamp are systemctl's own creations, so the fake never makes them)
        ud = units.unit_dir(env)
        for path in (
            paths.state,
            paths.lock,
            timer_path,
            os.path.join(ud, service_name),
        ):
            self.assertTrue(os.path.exists(path), path)

    def test_refused_reset_arms_hourly(self):
        sid = uuid.uuid4().hex
        launch = os.path.join(self.root, "launch")
        os.makedirs(launch)
        host = fakes.start_host_process(launch)
        self.addCleanup(self._kill, host)
        env = self._claude_env(sid, host)
        paths = session_paths(env, "claude", sid)
        stale = "You've hit your weekly limit · resets Oct 22, 10pm (America/Santiago)"
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(
                0, cli.main(["arm", "--reset-text", stale], seams=fakes.fixed_seams(env, _NOW))
            )
        self.assertIn(
            "reset refused: reset date is not within the next 7 days; the hourly wake stands",
            out.getvalue(),
        )
        state, reason = read_state(paths.state, "claude", sid)
        self.assertEqual("ok", reason)
        assert state is not None
        self.assertEqual("hourly", state["wake_source"])
        self.assertEqual(_NOW + 60, state["not_before"])
        self.assertIsNone(state["reset_at"])
        self.assertIsNone(state["reset_evidence"])


class TestResetGrammar(unittest.TestCase):
    """Every observed reset form (spike 004, research Q4 reference values)
    parses to its UTC instant; malformed, unknown and out-of-window forms are
    refused with a reason."""

    def setUp(self):
        if not _zone_available():
            self.skipTest(f"no system zone database ({_ZONE} unavailable)")

    def test_reference_values(self):
        zone = _ZONE
        cases = [
            (f"You've hit your session limit · resets 12:30am ({zone})", _utc(2026, 10, 26, 3, 30)),
            (f"You've hit your session limit · resets 4:50pm ({zone})", _utc(2026, 10, 26, 19, 50)),
            (_LIMIT_TEXT, _utc(2026, 10, 26, 16, 0)),
            (f"resets 3am ({zone})", _utc(2026, 10, 26, 6, 0)),
            (_WEEKLY_TEXT, _utc(2026, 10, 28, 1, 0)),
        ]
        for text, expected in cases:
            with self.subTest(text=text):
                result = parse_reset_text(text, _NOW)
                self.assertIsNone(result.reason)
                self.assertEqual(expected, result.at)

    def test_dateless_is_the_next_such_time_strictly_after_now(self):
        zone = _ZONE
        # local now is 19:44; 7:44pm today equals now to the second, so the
        # strict reading rolls to tomorrow; 11:59pm tonight is still future
        cases = [
            (f"resets 7:44pm ({zone})", _utc(2026, 10, 26, 22, 44)),
            (f"resets 11:59pm ({zone})", _utc(2026, 10, 26, 2, 59)),
        ]
        for text, expected in cases:
            with self.subTest(text=text):
                result = parse_reset_text(text, _NOW)
                self.assertIsNone(result.reason)
                self.assertEqual(expected, result.at)

    def test_out_of_window_dated_forms_are_refused(self):
        for text in (
            # 2026-10-23T01:00Z is past; the 2027 date is more than 7 days away
            "resets Oct 22, 10pm (America/Santiago)",
            # 2026-01-03 is past; 2027-01-03T12:00Z is more than 7 days away
            "resets Jan 3, 9am (America/Santiago)",
        ):
            with self.subTest(text=text):
                result = parse_reset_text(text, _NOW)
                self.assertIsNone(result.at)
                self.assertEqual("reset date is not within the next 7 days", result.reason)

    def test_malformed_and_unknown_forms_are_refused(self):
        for text, needle in (
            ("resets 13pm (America/Santiago)", "malformed"),
            ("resets 1:75pm (America/Santiago)", "malformed"),
            ("resets Feb 30, 1pm (America/Santiago)", "does not exist"),
            ("no reset clause here, back at 5pm", "not recognized"),
        ):
            with self.subTest(text=text):
                result = parse_reset_text(text, _NOW)
                self.assertIsNone(result.at)
                self.assertIsNotNone(result.reason)
                assert result.reason is not None
                self.assertIn(needle, result.reason)

    def test_unknown_zone_names_the_zone_database(self):
        result = parse_reset_text("resets 1pm (Nowhere/Zone)", _NOW)
        self.assertIsNone(result.at)
        self.assertIsNotNone(result.reason)
        assert result.reason is not None
        self.assertIn("Nowhere/Zone", result.reason)
        self.assertIn("system zone database", result.reason)


class TestResetBounds(unittest.TestCase):
    """SPEC R4 boundary and precision: the 7-day edges, the fire-time edge is
    fire's own (26-02), the calendar line carries seconds."""

    def test_seven_day_edges(self):
        now = 1_000_000.0
        self.assertIsNone(check_bounds(now + MAX_RESET_AHEAD_S, now))
        self.assertEqual(
            "reset is more than 7 days away", check_bounds(now + MAX_RESET_AHEAD_S + 1, now)
        )
        self.assertEqual("reset is not in the future", check_bounds(now, now))
        self.assertEqual("reset is not in the future", check_bounds(now - 1, now))

    def test_reset_at_seven_day_edges(self):
        now = 1_000_000.0
        edge = parse_reset_at(str(int(now + MAX_RESET_AHEAD_S)), now)
        self.assertIsNone(edge.reason)
        self.assertEqual(now + MAX_RESET_AHEAD_S, edge.at)
        late = parse_reset_at(str(int(now + MAX_RESET_AHEAD_S + 1)), now)
        self.assertEqual("reset is more than 7 days away", late.reason)

    def test_calendar_line_format(self):
        self.assertEqual(
            "OnCalendar=2026-10-26 16:01:00 UTC", calendar_line(_utc(2026, 10, 26, 16, 1))
        )

    def test_reset_at_forms(self):
        now = _utc(2026, 10, 25, 22, 44)
        reset = _utc(2026, 10, 26, 16, 0)
        for value in (str(int(reset)), "2026-10-26T16:00:00Z", "2026-10-26T16:00:00+00:00"):
            with self.subTest(value=value):
                result = parse_reset_at(value, now)
                self.assertIsNone(result.reason, value)
                self.assertEqual(reset, result.at)
        for value in ("2026-10-26T16:00:00", "soon"):
            with self.subTest(value=value):
                result = parse_reset_at(value, now)
                self.assertIsNone(result.at)
                self.assertIsNotNone(result.reason)
        naive = parse_reset_at("2026-10-26T16:00:00", now)
        assert naive.reason is not None
        self.assertIn("no UTC offset", naive.reason)


class TestResetEvidence(unittest.TestCase):
    """The stored evidence is the runner's redaction policy (T-26-20) capped
    at 2000 code points."""

    def test_secret_shapes_are_replaced(self):
        api_key = "sk-" + "x9y8z7w6v5u4"
        github = "ghp_" + "A1b2C3d4E5f6G7h8I9j0K1l2M3n4"
        bearer = "T" + "o0k1e2n3v4a5l6"
        for text, secret in (
            (json.dumps({"api_key": api_key}), api_key),
            (f"auth token {github} rejected", github),
            (f"Authorization: Bearer {bearer} expired", bearer),
        ):
            with self.subTest(text=text):
                out = redact(text)
                self.assertNotIn(secret, out)
                self.assertIn("<redacted>", out)

    def test_hex_runs_are_replaced(self):
        run = "a" * 40
        out = redact(f"state digest {run} recorded")
        self.assertNotIn(run, out)
        self.assertIn("<redacted>", out)
        short = "a" * 31
        self.assertIn(short, redact(f"state digest {short} recorded"))

    def test_long_text_is_capped_whole(self):
        emoji = "\U0001f600"
        for text in ("x" * 2500, emoji * 2500):
            with self.subTest(kind=text[0]):
                capped = cap_code_points(text, 2000)
                self.assertEqual(2000, len(capped))
                self.assertEqual(text[:2000], capped)

    def test_separator_and_evidence_cap(self):
        if not _zone_available():
            self.skipTest(f"no system zone database ({_ZONE} unavailable)")
        result = parse_reset_text(_WEEKLY_TEXT, _NOW)
        self.assertIsNone(result.reason)
        self.assertIn("·", result.evidence)
        self.assertLessEqual(len(result.evidence), 2000)

    def test_structured_payload_keys_are_redacted(self):
        opaque = "opaque" + "-value-" + "7"
        for key in ("token", "password", "passwd", "secret", "api_key", "apiKey"):
            payload = json.dumps(
                {
                    "error": "rate_limit",
                    "error_details": {key: opaque},
                    "last_assistant_message": _LIMIT_TEXT,
                }
            )
            for text in (payload, json.dumps(payload)):
                with self.subTest(key=key, escaped=text != payload):
                    if not _zone_available():
                        self.skipTest(f"no system zone database ({_ZONE} unavailable)")
                    result = parse_reset_text(text, _NOW)
                    self.assertIsNone(result.reason, key)
                    self.assertNotIn(opaque, result.evidence)
                    self.assertIn(key, result.evidence)

    def test_keyed_value_is_removed_wherever_else_it_appears(self):
        opaque = "opaque" + "-value-" + "7"
        payload = json.dumps({"error": "rate_limit", "error_details": {"token": opaque}})
        text = f"{payload} echoed at {opaque} · {_LIMIT_TEXT}"
        result = parse_reset_text(text, _NOW)
        self.assertIsNone(result.reason)
        self.assertNotIn(opaque, result.evidence)
        self.assertIn("<redacted>", result.evidence)


if __name__ == "__main__":
    unittest.main()
