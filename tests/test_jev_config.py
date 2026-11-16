"""Behaviour of the [jev] settings module skills/jev-fast-decision/scripts/jev_config.py (plan
34-01). config_set writes only the [jev] table of the user config.toml and the copied reader reads
it back. Every test uses a temp HOME and a plain env dict, never the real HOME or os.environ."""

import importlib.util
import io
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import tomllib
import unittest
from pathlib import Path
from unittest import mock

from tests.test_jev_fast_decision import (
    JR,
    REMOTE_HOST,
    SCRIPT,
    JevStub,
    _ClientCase,
    choice_item_ladder,
    closed_port_url,
    jev_ladder,
    noul_item,
    payload,
)

REPO = Path(__file__).resolve().parents[1]
MODULE = REPO / "skills" / "jev-fast-decision" / "scripts" / "jev_config.py"


def _load():
    spec = importlib.util.spec_from_file_location("jev_config_under_test", MODULE)
    assert spec is not None and spec.loader is not None, MODULE
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


jev_config = _load()


class TestConfigSet(unittest.TestCase):
    def setUp(self):
        root = tempfile.mkdtemp(prefix="jev-config-")
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        home = os.path.join(root, "home")
        self.cwd = os.path.join(root, "proj")
        os.makedirs(self.cwd)
        self.env = {"HOME": home, "XDG_CONFIG_HOME": os.path.join(home, ".config")}
        self.user_file = os.path.join(home, ".config", "ai-kit", "config.toml")

    def _write_user(self, data: bytes):
        os.makedirs(os.path.dirname(self.user_file), exist_ok=True)
        with open(self.user_file, "wb") as handle:
            handle.write(data)

    def _read_user(self) -> bytes:
        with open(self.user_file, "rb") as handle:
            return handle.read()

    def test_set_then_read_back(self):
        result = jev_config.config_set("laya_url", "http://192.0.2.7:8010", self.env)
        self.assertTrue(result["ok"])
        self.assertTrue(result["file"].endswith(os.path.join("ai-kit", "config.toml")))
        table = jev_config.jev_table(self.cwd, self.env)
        self.assertEqual(table["laya_url"], "http://192.0.2.7:8010")

    def test_set_keeps_other_bytes(self):
        original = '# keep me\n[lanes]\nstrategy = "single"\n\n[jev]\nenabled = true\n'
        self._write_user(original.encode("utf-8"))
        self.assertTrue(jev_config.config_set("laya_version", "0.4.27", self.env)["ok"])
        expected = original + 'laya_version = "0.4.27"\n'
        self.assertEqual(self._read_user().decode("utf-8"), expected)
        self.assertEqual(tomllib.loads(expected)["jev"]["laya_version"], "0.4.27")

    def test_set_refuses_bad_values_and_writes_nothing(self):
        cases = [
            ("laya_url", "ftp://h/x", "invalid_value:laya_url"),
            ("laya_url", "http://user:pw@h:1", "invalid_value:laya_url"),
            ("laya_url", "http://", "invalid_value:laya_url"),
            ("laya_url", "http://h:99999", "invalid_value:laya_url"),
            ("laya_url", "http://h:1/?token=abc", "invalid_value:laya_url"),
            ("laya_url", "http://h:1/#frag", "invalid_value:laya_url"),
            ("laya_url", "http://exa mple.com:8010", "invalid_value:laya_url"),
            ("laya_version", "0.4 beta", "invalid_value:laya_version"),
            ("enabled", "yes", "invalid_value:enabled"),
            ("other", "x", "unknown_key"),
        ]
        for key, raw, reason in cases:
            with self.subTest(key=key, raw=raw):
                result = jev_config.config_set(key, raw, self.env)
                self.assertEqual(result, {"ok": False, "reason": reason})
        self.assertFalse(os.path.exists(self.user_file))

    def test_declined_laya_is_an_empty_string(self):
        self.assertTrue(jev_config.config_set("laya_url", "", self.env)["ok"])
        self.assertEqual(jev_config.jev_table(self.cwd, self.env)["laya_url"], "")

    def test_set_refuses_a_broken_file(self):
        self._write_user(b"[jev\n")
        result = jev_config.config_set("laya_url", "http://192.0.2.7:8010", self.env)
        self.assertFalse(result["ok"])
        self.assertEqual(result["reason"], "config_unwritable")
        self.assertEqual(self._read_user(), b"[jev\n")

    def test_set_keeps_crlf_line_endings(self):
        self._write_user(b"# keep me\r\n[jev]\r\nenabled = true\r\n")
        self.assertTrue(jev_config.config_set("laya_version", "0.4.27", self.env)["ok"])
        raw = self._read_user()
        self.assertTrue(raw.startswith(b"# keep me\r\n"))
        self.assertNotIn(b"\n", raw.replace(b"\r\n", b""))
        parsed = tomllib.loads(raw.decode("utf-8"))["jev"]
        self.assertIs(parsed["enabled"], True)
        self.assertEqual(parsed["laya_version"], "0.4.27")

    def test_two_writers_keep_one_answer(self):
        results = []

        def write(value):
            results.append(jev_config.config_set("laya_url", value, self.env))

        values = ["http://192.0.2.1:1", "http://192.0.2.2:2"]
        threads = [threading.Thread(target=write, args=(value,)) for value in values]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertTrue(all(result["ok"] for result in results))
        self.assertIn(jev_config.jev_table(self.cwd, self.env)["laya_url"], values)


class TestKnobAndUrl(unittest.TestCase):
    def setUp(self):
        root = tempfile.mkdtemp(prefix="jev-knob-")
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        home = os.path.join(root, "home")
        self.cwd = os.path.join(root, "proj")
        os.makedirs(self.cwd)
        self.env = {"HOME": home, "XDG_CONFIG_HOME": os.path.join(home, ".config")}
        self.user_file = os.path.join(home, ".config", "ai-kit", "config.toml")
        self.project_file = os.path.join(self.cwd, ".aikit", "config.toml")

    def _write(self, path: str, text: str):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)

    def test_knob_env_wins_both_ways(self):
        self._write(self.user_file, "[jev]\nenabled = true\n")
        on_env = {**self.env, "GSD_PATH_JEV": "1"}
        off_env = {**self.env, "GSD_PATH_JEV": "0"}
        no_env = {**self.env, "GSD_PATH_JEV": "no"}
        self.assertEqual(
            jev_config.knob(self.cwd, on_env),
            {"on": True, "source": "env:GSD_PATH_JEV", "needs_answer": False, "problem": None},
        )
        self.assertEqual(jev_config.knob(self.cwd, off_env)["on"], False)
        self.assertEqual(jev_config.knob(self.cwd, no_env)["source"], "env:GSD_PATH_JEV")
        for odd in ("true", "no"):  # IN-101: still off, but the value is reported as not understood
            result = jev_config.knob(self.cwd, {**self.env, "GSD_PATH_JEV": odd})
            self.assertEqual((result["on"], result["problem"]),
                             (False, "invalid_value:GSD_PATH_JEV"))
        self._write(self.user_file, "[jev]\nenabled = false\n")
        self.assertEqual(jev_config.knob(self.cwd, on_env)["on"], True)
        self._write(self.user_file, "[jev\n")
        self.assertEqual(jev_config.knob(self.cwd, on_env)["on"], True)

    def test_knob_blank_env_is_unset(self):
        self._write(self.user_file, "[jev]\nenabled = false\n")
        for blank in ("", "   "):
            with self.subTest(env=blank):
                result = jev_config.knob(self.cwd, {**self.env, "GSD_PATH_JEV": blank})
                self.assertEqual(result["on"], False)
                self.assertEqual(result["source"], "config")

    def test_knob_project_over_user(self):
        self._write(self.user_file, "[jev]\nenabled = true\n")
        self._write(self.project_file, "[jev]\nenabled = false\n")
        self.assertEqual(
            jev_config.knob(self.cwd, self.env),
            {"on": False, "source": "config", "needs_answer": False, "problem": None},
        )
        self._write(self.user_file, "[jev]\nenabled = false\n")
        self._write(self.project_file, "[jev]\nenabled = true\n")
        self.assertEqual(jev_config.knob(self.cwd, self.env)["on"], True)

    def test_knob_absent_defaults_on_and_asks(self):
        self.assertEqual(
            jev_config.knob(self.cwd, self.env),
            {"on": True, "source": "default", "needs_answer": True, "problem": None},
        )

    def test_knob_bad_value_and_broken_file_fail_closed(self):
        self._write(self.user_file, '[jev]\nenabled = "false"\n')
        result = jev_config.knob(self.cwd, self.env)
        self.assertEqual(result["on"], False)
        self.assertEqual(result["problem"], "invalid_value:enabled")
        self._write(self.user_file, "[jev\n")
        result = jev_config.knob(self.cwd, self.env)
        self.assertEqual(result["on"], False)
        self.assertTrue(result["problem"].startswith("config_error"))

    def test_url_order_env_project_user_default(self):
        self.assertEqual(jev_config.laya_url_setting(self.cwd, self.env), (None, "default"))
        self._write(self.user_file, '[jev]\nlaya_url = "http://user.example:1"\n')
        self.assertEqual(
            jev_config.laya_url_setting(self.cwd, self.env), ("http://user.example:1", "config")
        )
        self._write(self.project_file, '[jev]\nlaya_url = "http://project.example:2"\n')
        self.assertEqual(
            jev_config.laya_url_setting(self.cwd, self.env),
            ("http://project.example:2", "config"),
        )
        ai_kit_env = {**self.env, "AI_KIT_LAYA_URL": "http://ai-kit.example:3"}
        self.assertEqual(
            jev_config.laya_url_setting(self.cwd, ai_kit_env),
            ("http://ai-kit.example:3", "env:AI_KIT_LAYA_URL"),
        )
        both_env = {**ai_kit_env, "JEV_LAYA_URL": "http://jev.example:4"}
        self.assertEqual(
            jev_config.laya_url_setting(self.cwd, both_env),
            ("http://jev.example:4", "env:JEV_LAYA_URL"),
        )
        blank_env = {**self.env, "JEV_LAYA_URL": "  "}
        self.assertEqual(
            jev_config.laya_url_setting(self.cwd, blank_env),
            ("http://project.example:2", "config"),
        )
        self._write(self.project_file, '[jev]\nlaya_url = ""\n')
        self.assertEqual(jev_config.laya_url_setting(self.cwd, self.env), ("", "config"))

    def test_url_bad_value_and_broken_file(self):
        self._write(self.user_file, "[jev]\nlaya_url = 5\n")
        self.assertEqual(
            jev_config.laya_url_setting(self.cwd, self.env), (None, "invalid_value:laya_url")
        )
        self._write(self.user_file, "[jev\n")
        self.assertEqual(jev_config.laya_url_setting(self.cwd, self.env), (None, "config_error"))


class TestClientSettings(_ClientCase):
    """The client reads the [jev] settings (plan 34-02): the config, the session environment, the
    first-run answer and host-bound consent. Every test runs in the _ClientCase temp home."""

    def setUp(self):
        super().setUp()
        os.environ.pop("JEV_LAYA_URL", None)  # each test sets the address it needs
        # WR-104: a test with no address of its own falls back to a closed port, never the owner's
        # real Laya at 127.0.0.1:8010, and a connect to 8010 fails the test at its end.
        default = mock.patch.object(JR, "LAYA_DEFAULT_URL", closed_port_url())
        default.start()
        self.addCleanup(default.stop)
        self.dialed_default_port = []
        real_connect = socket.socket.connect

        def guarded_connect(sock, address, *args, **kwargs):
            if isinstance(address, tuple) and address[1:2] == (8010,):
                self.dialed_default_port.append(address)
                raise ConnectionRefusedError("the test guard refuses port 8010")
            return real_connect(sock, address, *args, **kwargs)

        guard = mock.patch.object(socket.socket, "connect", guarded_connect)
        guard.start()
        self.addCleanup(guard.stop)
        self.addCleanup(lambda: self.assertEqual(self.dialed_default_port, []))

    def write_user_config(self, text):
        path = Path(os.environ["XDG_CONFIG_HOME"]) / "ai-kit" / "config.toml"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def run_cli(self, argv):
        """main(argv) with its stdout parsed: (exit code, the JSON it printed)."""
        out = io.StringIO()
        with mock.patch.object(sys, "stdout", out):
            code = JR.main(argv)
        return code, json.loads(out.getvalue())

    def test_config_set_reports_a_project_override(self):
        """WR-103: the user value is saved, and the project file that wins is named."""
        _code, plain = self.run_cli(["config", "set", "enabled", "false"])
        self.assertTrue(plain["ok"])
        self.assertNotIn("overridden_by", plain)
        project = self.tmp / "proj" / ".aikit" / "config.toml"
        project.parent.mkdir()
        project.write_text("[jev]\nenabled = true\n", encoding="utf-8")
        code, out = self.run_cli(["config", "set", "enabled", "false"])
        self.assertEqual(code, 0)
        self.assertEqual(out["overridden_by"], str(project))
        self.assertIn("wins", out["notice"])
        _code, same = self.run_cli(["config", "set", "enabled", "true"])
        self.assertNotIn("overridden_by", same)

    def test_config_set_reports_a_broken_project_file_and_a_session_override(self):
        """IN-504: a project file that cannot be parsed, or a session variable, is named."""
        project = self.tmp / "proj" / ".aikit" / "config.toml"
        project.parent.mkdir()
        project.write_text("[jev\nbroken", encoding="utf-8")
        code, out = self.run_cli(["config", "set", "enabled", "true"])
        self.assertEqual(code, 0)
        self.assertTrue(out["ok"])
        self.assertEqual(out["overridden_by"], str(project))
        self.assertIn("cannot be read", out["notice"])
        project.unlink()
        for key, value, name in (("enabled", "true", "GSD_PATH_JEV"),
                                 ("laya_url", "http://127.0.0.1:9", "JEV_LAYA_URL"),
                                 ("laya_url", "http://127.0.0.1:9", "AI_KIT_LAYA_URL")):
            with self.subTest(name=name), mock.patch.dict(os.environ, {name: "0"}):
                _code, out = self.run_cli(["config", "set", key, value])
                self.assertEqual(out["overridden_by"], f"env:{name}")
                self.assertIn(name, out["notice"])
        _code, plain = self.run_cli(["config", "set", "laya_version", "0.4.27"])
        self.assertNotIn("overridden_by", plain)

    def test_config_set_then_probe_finds_laya_there(self):
        with JevStub() as stub:
            code, saved = self.run_cli(["config", "set", "laya_url",
                                        f"http://127.0.0.1:{stub.port}"])
            self.assertEqual((code, saved["ok"]), (0, True))
            code, report = self.run_probe()
            self.assertEqual(code, 0)
            self.assertEqual(report["selected"], "laya")
            laya = self.backend_entry(report, "laya")
            self.assertEqual((laya["host"], laya["usable"]), ("127.0.0.1", True))
            self.assert_no_posts(stub)

    def test_env_override_beats_config(self):
        self.write_user_config('[jev]\nlaya_url = "http://127.0.0.1:1"\n')
        with JevStub() as stub:
            self.point_at(stub)
            _code, report = self.run_probe()
        self.assertTrue(self.backend_entry(report, "laya")["usable"])

    def test_knob_off_in_config_disables_probe_and_screen(self):
        self.write_user_config("[jev]\nenabled = false\n")
        os.environ["GSD_PATH_JEV_TIMEOUT_SECONDS"] = "5"  # no GSD_PATH_JEV: the config decides
        with JevStub() as stub:
            self.point_at(stub)
            code, report = self.run_probe()
            self.assertEqual(code, 0)
            self.assertEqual(report["status"], "disabled")
            self.assertEqual(report["settings"], {"enabled": False, "enabled_source": "config"})

            class _NoStdin:
                def read(self, *_ignored):
                    raise AssertionError("stdin was read with jev switched off")

            with mock.patch.object(sys, "stdin", _NoStdin()):
                self.assertEqual(JR.screen(), {"status": "disabled"})
            self.assert_no_posts(stub)

    def test_session_switch_wins_both_ways(self):
        # GSD_PATH_JEV beats [jev] enabled: 1 runs jev against a false config, 0 stops it.
        self.write_user_config("[jev]\nenabled = false\n")
        with JevStub() as stub:
            self.point_at(stub)
            os.environ["GSD_PATH_JEV"] = "1"
            code, report = self.run_probe()
            self.assertEqual((code, report["status"]), (0, "ok"))
            self.assertEqual(report["settings"],
                             {"enabled": True, "enabled_source": "env:GSD_PATH_JEV"})
            self.write_user_config("[jev]\nenabled = true\n")
            os.environ["GSD_PATH_JEV"] = "0"
            code, report = self.run_probe()
            self.assertEqual((code, report["status"]), (0, "disabled"))
            self.assert_no_posts(stub)

    def test_knob_absent_is_on_and_asked_once(self):
        os.environ.pop("GSD_PATH_JEV", None)
        with JevStub() as stub:
            self.point_at(stub)
            code, report = self.run_probe()
            self.assertEqual((code, report["status"]), (0, "ok"))
            self.assertEqual(report["settings"]["enabled_source"], "default")
            self.assertIn("notice", report["settings"])
            self.assertIn("enabled", report["needs_answer"])
            code, saved = self.run_cli(["config", "set", "enabled", "true"])
            self.assertEqual((code, saved["ok"]), (0, True))
            _code, report = self.run_probe()
            self.assertEqual(report["settings"]["enabled_source"], "config")
            self.assertNotIn("notice", report["settings"])
            self.assertNotIn("enabled", report["needs_answer"])

    def test_project_knob_wins_over_user(self):
        project_config = self.tmp / "proj" / ".aikit" / "config.toml"  # the _cwd project layer
        project_config.parent.mkdir(parents=True)
        project_config.write_text("[jev]\nenabled = false\n", encoding="utf-8")
        self.write_user_config("[jev]\nenabled = true\n")
        code, report = self.run_probe()
        self.assertEqual((code, report["status"]), (0, "disabled"))
        self.assertEqual(report["settings"], {"enabled": False, "enabled_source": "config"})

    def test_broken_config_fails_closed_with_a_reason(self):
        self.write_user_config("[jev\n")
        _code, report = self.run_probe()
        self.assertEqual(report["status"], "disabled")
        self.assertTrue(report["settings"]["problem"].startswith("config_error"))
        with JevStub() as stub:
            self.point_at(stub)
            os.environ["GSD_PATH_JEV"] = "1"  # the session switch still runs jev for this session
            code, report = self.run_probe()
        self.assertEqual((code, report["status"]), (0, "ok"))

    def test_ladder_knob_off_is_own_reasoning(self):
        self.write_user_config("[jev]\nenabled = false\n")
        os.environ.pop("GSD_PATH_JEV", None)
        previous = os.getcwd()
        os.chdir(self.tmp / "proj")  # the client's project layer is read from its cwd
        self.addCleanup(os.chdir, previous)
        seams = jev_ladder.Seams(env=dict(os.environ), run=subprocess.run)
        result = jev_ladder.run_ladder(seams, str(SCRIPT), [choice_item_ladder("low1")])
        self.assertEqual(result["client_status"], "disabled")
        row = result["items"]["low1"]
        self.assertEqual(row["decided_by"], "own_reasoning")
        # ai-kit-commit-fold's fold_group.ask_jev reads row[row["decided_by"]]["choice"]: with no
        # own_reasoning column it gets (None, "no answer"), so no choice may sit there.
        self.assertNotIn("choice", row.get("own_reasoning") or {})
        # ai-kit-spec-goal-prompt's gp_host._jev_reading reads only detect's backends: {} gives
        # "no usable backend", so the status and the empty backends are both pinned here.
        detected = jev_ladder.detect(seams, str(SCRIPT))
        self.assertEqual(detected["status"], "disabled")
        self.assertEqual(detected["backends"], {})

    def send_refusal(self, name):
        """The message of the PermissionError `_send` raises for this row; no socket may open."""
        self.enable(None)
        body = {"model": "x", "state": {}, "questions": {}}
        socket_guard = mock.patch.object(JR, "_exchange", side_effect=AssertionError("socket"))
        with (socket_guard, self.assertRaises(PermissionError) as refused):
            JR._send(JR.row_named(name), body, 1.0)
        return str(refused.exception)

    def test_send_reads_the_laya_address_once(self):
        """WR-101: the address changes to an unconsented host between two reads; the request
        still goes only to the address the consent check saw."""
        loopback = closed_port_url()
        reads = iter([(loopback, None)])

        def flipping():
            return next(reads, (f"http://{REMOTE_HOST}:8010/v1/systemone", None))

        row = {**JR.row_named("laya"), "url": flipping}
        urls = []
        real_request = JR.urllib.request.Request

        def recording(url, *args, **kwargs):
            urls.append(url)
            return real_request(url, *args, **kwargs)

        self.enable(None)
        body = {"model": "x", "state": {}, "questions": {}}
        with (mock.patch.object(JR.urllib.request, "Request", recording),
              self.assertRaises(OSError)):  # the closed port refuses; nothing else is dialled
            JR._send(row, body, 1.0)
        self.assertEqual(urls, [loopback])

    def test_off_loopback_laya_needs_consent_and_sends_nothing(self):
        code, _saved = self.run_cli(["config", "set", "laya_url", f"http://{REMOTE_HOST}:8010"])
        self.assertEqual(code, 0)
        _code, report = self.run_probe()
        laya = self.backend_entry(report, "laya")
        self.assertEqual(report["status"], "consent_required_for_remote")
        self.assertIn("laya", report["remote_available"])
        self.assertEqual((laya["reason"], laya["host"], laya["url_source"]),
                         ("consent_required_for_remote", REMOTE_HOST, "config"))
        self.assertEqual(self.send_refusal("laya"), "consent_required_for_remote")

    def test_consented_off_loopback_laya_answers(self):
        # Every address here is off loopback in the client's eyes; the stub is the only host.
        with JevStub() as stub, mock.patch.object(JR, "_is_loopback", return_value=False):
            self.point_at(stub)
            code, granted = self.run_cli(["consent", "grant", "laya"])
            self.assertEqual((code, granted["ok"], granted["host"]), (0, True, "127.0.0.1"))
            self.enable("laya")
            code, out = self.run_main(payload(noul_item("a")))
            self.assertEqual((code, out["status"]), (0, "ok"))
            self.assertEqual(len(stub.posts), 1)
            self.run_cli(["consent", "revoke", "laya"])
            code, out = self.run_main(payload(noul_item("a")))
            self.assertNotEqual(out["status"], "ok")
            self.assertEqual(len(stub.posts), 1, "a revoked Laya host is refused before a socket")

    def test_every_off_loopback_row_is_refused_before_a_socket(self):
        self.enable(None)
        for row in JR.TABLE:
            name = row["name"]
            if name == "laya":
                os.environ["JEV_LAYA_URL"] = f"http://{REMOTE_HOST}:8010"
            elif name == "typesafe":
                os.environ["JEV_TYPESAFE_URL"] = f"https://{REMOTE_HOST}/v1/systemone"
                os.environ["TYPESAFE_API_KEY"] = "typesafe-key"
            else:
                self.fail(f"no off-loopback address is set up for the new row {name}")
            self.assertEqual(self.send_refusal(name), "consent_required_for_remote", name)

    def test_configured_default_counts_as_configured(self):
        closed = closed_port_url()
        with mock.patch.object(JR, "LAYA_DEFAULT_URL", closed):
            code, _saved = self.run_cli(["config", "set", "laya_url", closed])
            self.assertEqual(code, 0)
            _code, report = self.run_probe()
        self.assertEqual(self.backend_entry(report, "laya")["url_source"], "config")
        self.assertEqual(report["needs_answer"], ["enabled"])  # the knob is still unanswered

    def test_first_run_question_answered_and_declined(self):
        closed = closed_port_url()
        with mock.patch.object(JR, "LAYA_DEFAULT_URL", closed):
            _code, report = self.run_probe()
            self.assertEqual(report["needs_answer"], ["enabled", "laya_url"])
            self.assertEqual(self.backend_entry(report, "laya")["url_source"], "default")
            code, _saved = self.run_cli(["config", "set", "laya_url", ""])
            self.assertEqual(code, 0)
            _code, report = self.run_probe()
        self.assertEqual(self.backend_entry(report, "laya")["reason"], "laya_declined")
        self.assertEqual(report["needs_answer"], ["enabled"])
        os.environ["TYPESAFE_API_KEY"] = "typesafe-key"
        os.environ["JEV_ALLOW_REMOTE"] = "1"
        with JevStub() as stub:
            self.point_remote("typesafe", stub)
            _code, report = self.run_probe()
        self.assertEqual(report["candidates"], ["typesafe"])

    def test_malformed_typesafe_url_is_a_probe_error(self):
        """IN-104: an unclosed bracket in JEV_TYPESAFE_URL is a probe error, not a traceback."""
        os.environ["TYPESAFE_API_KEY"] = "sentinel-key-not-sent"
        os.environ["JEV_TYPESAFE_URL"] = "http://[bad"
        code, report = self.run_probe()
        self.assertEqual(code, 0)
        self.assertEqual(self.backend_entry(report, "typesafe")["reason"],
                         "invalid_url:jev_typesafe_url")

    def test_malformed_url_is_a_probe_error(self):
        self.write_user_config('[jev]\nlaya_url = "http://[bad"\n')
        code, report = self.run_probe()
        self.assertEqual(code, 0)
        self.assertEqual(self.backend_entry(report, "laya")["reason"], "invalid_url:laya_url")
        os.environ["JEV_LAYA_URL"] = "http://user:pw@127.0.0.1:1"
        code, report = self.run_probe()
        self.assertEqual(code, 0)
        self.assertEqual(self.backend_entry(report, "laya")["reason"], "invalid_url:jev_laya_url")

    def test_session_gate_never_opens_an_off_loopback_laya(self):
        self.run_cli(["config", "set", "laya_url", f"http://{REMOTE_HOST}:8010"])
        for gate in ("1", "laya"):
            os.environ["JEV_ALLOW_REMOTE"] = gate
            _code, report = self.run_probe()
            self.assertEqual(self.backend_entry(report, "laya")["reason"],
                             "consent_required_for_remote", gate)
            self.assertEqual(self.send_refusal("laya"), "consent_required_for_remote", gate)
        # Only a record bound to the host can open it: grant on the stub's host, then move the
        # address to REMOTE_HOST and the same row asks again.
        del os.environ["JEV_ALLOW_REMOTE"]
        with JevStub() as stub, mock.patch.object(JR, "_is_loopback", return_value=False):
            self.point_at(stub)
            self.run_cli(["consent", "grant", "laya"])
            _code, report = self.run_probe()
            self.assertTrue(self.backend_entry(report, "laya")["usable"])
            del os.environ["JEV_LAYA_URL"]
            self.run_cli(["config", "set", "laya_url", f"http://{REMOTE_HOST}:8010"])
            _code, report = self.run_probe()
        self.assertEqual(self.backend_entry(report, "laya")["reason"],
                         "consent_required_for_remote")
        self.assertEqual(self.send_refusal("laya"), "consent_required_for_remote")

    def test_off_loopback_http_laya_never_gets_a_key(self):
        key = "NEVER-PRINT-LAYA-KEY"
        cases = (("http", key, "insecure_url"),
                 ("https", key, "consent_required_for_remote"),
                 ("http", None, "consent_required_for_remote"))
        for scheme, laya_key, reason in cases:
            if laya_key:
                os.environ["LAYA_API_KEY"] = laya_key
            else:
                os.environ.pop("LAYA_API_KEY", None)
            self.run_cli(["config", "set", "laya_url", f"{scheme}://{REMOTE_HOST}:8010"])
            code, text = self.run_probe_text()
            self.assertEqual(code, 0)
            self.assertNotIn(key, text)
            self.assertEqual(self.backend_entry(json.loads(text), "laya")["reason"], reason,
                             scheme)
            self.assertEqual(self.send_refusal("laya"), reason, scheme)

    def test_probe_key_hint_without_env_key(self):
        key = "NEVER-PRINT-TYPESAFE-KEY"
        os.environ.pop("TYPESAFE_API_KEY", None)
        code, text = self.run_probe_text()
        self.assertEqual(code, 0)
        typesafe = self.backend_entry(json.loads(text), "typesafe")
        self.assertEqual(typesafe["reason"], "missing_api_key")
        self.assertIn("multiplexer", typesafe["key_hint"])
        self.assertNotIn("key_hint", self.backend_entry(json.loads(text), "laya"))
        creds = Path(os.environ["HOME"]) / ".mycreds"  # a synthetic file in the scratch HOME
        creds.write_text(f"TYPESAFE_API_KEY={key}\n", encoding="utf-8")
        creds.chmod(0o600)
        code, text = self.run_probe_text()
        self.assertNotIn(key, text)
        typesafe = self.backend_entry(json.loads(text), "typesafe")
        self.assertEqual(typesafe["key_source"], "file:~/.mycreds")
        self.assertIn("multiplexer", typesafe["key_hint"])
        os.environ["TYPESAFE_API_KEY"] = key
        code, text = self.run_probe_text()
        self.assertNotIn(key, text)
        self.assertNotIn("key_hint", self.backend_entry(json.loads(text), "typesafe"))


if __name__ == "__main__":
    unittest.main()
