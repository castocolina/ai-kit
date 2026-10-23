# tests/test_jev_fast_decision.py
"""Unit tests for skills/jev-fast-decision/scripts/jev_review.py, against in-process stubs.

stdlib `unittest` only (D-20). Every test runs under `patch.dict(os.environ, ..., clear=True)`
with HOME and the XDG roots inside a temp dir and `JEV_LAYA_URL` on a closed loopback port
unless it starts its own stub: no test may reach the real local Laya on 127.0.0.1:8010, the
real user config, a real key file or any remote host. The client is loaded by path (the v3
`load()` shim), so nothing imports `jev_review` by name and no pyright `extraPaths` entry is
needed.

`JevStub` is importable by sibling test modules (`from tests.test_jev_fast_decision import
JevStub`), the precedent of tests/test_curated_config_followups.py. Method tags
(`test_probe_*`, `test_screen_*`, `test_tolerance_*`, `test_taxonomy_*`) make `-k` select them.
"""

import ast
import datetime
import hashlib
import http.client
import http.server
import importlib.util
import io
import json
import math
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

SCRIPT = (Path(__file__).resolve().parents[1] / "skills" / "jev-fast-decision"
          / "scripts" / "jev_review.py")


def load():
    """The client, loaded by path."""
    spec = importlib.util.spec_from_file_location("jev_review_under_test", str(SCRIPT))
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


JR = load()
HEAD = "0" * 40
ROW_NAMES = ["laya", "typesafe", "opencode"]  # the table's order, Task 2 onward
REMOTE_HOST = "203.0.113.9"  # TEST-NET-3 documentation range: no test ever connects to it

THREE_ITEMS = {"reviewed_head": HEAD,
               "items": [{"id": "a", "type": "noul", "instructions": "Is this a real bug?",
                          "context": "app crashes on save"},
                         {"id": "b", "type": "noul", "instructions": "Was a human asked for?",
                          "context": "get me a person"},
                         {"id": "c", "type": "noul", "instructions": "Is it a bug?",
                          "context": "the refund is duplicated"}]}


def closed_port_url():
    """A loopback URL on a port nothing listens on (bound, then released right away)."""
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    return f"http://127.0.0.1:{port}/v1/systemone"


def noul_item(identifier, context="app crashes on save"):
    return {"id": identifier, "type": "noul", "instructions": "Is this a real bug?",
            "context": context}


def choice_item(identifier, context="the diff moves the refund call"):
    return {"id": identifier, "type": "choice", "instructions": "Which risk is higher?",
            "context": context,
            "criteria": {"bug": "a real defect", "style": "a style nit", "other": "a rename"}}


def score_item(identifier, context="the refund is duplicated"):
    return {"id": identifier, "type": "score", "instructions": "How severe is it?",
            "context": context, "criteria": ["low", "mid", "high"]}


def payload(*items):
    return {"reviewed_head": HEAD, "items": list(items) or [noul_item("a")]}


def _maybe_json(raw):
    try:
        value = json.loads(raw)
    except (ValueError, UnicodeError):
        return None
    return value if isinstance(value, dict) else None


def _distribution(top, slots, winner=0, uniform=False, places=4):
    """Probabilities over `slots` summing to ~1, with `winner` on top.

    `uniform` with `places=4` is Laya's rounding (a 3-way answer sums to 0.9999); with
    `places=2` it is TypeSafe's (a 3-way answer sums to 0.99).
    """
    if uniform:
        flat = round(1.0 / len(slots), places)
        return {slot: flat for slot in slots}
    rest = (1.0 - top) / (len(slots) - 1) if len(slots) > 1 else 0.0
    return {slot: (top if i == winner else rest) for i, slot in enumerate(slots)}


class JevStub:
    """An in-process System One stub on 127.0.0.1: answers like Laya and records every request.

    ``model`` is the answering id it echoes, ``top`` the winning probability, ``tops`` the
    per-question overrides, ``truncated`` sets ``usage.truncated``, ``uniform`` answers with
    flat 4-decimal probabilities, ``delay`` sleeps before each answer, ``health`` is the
    ``GET /health`` status, and ``script`` is a per-request queue of
    ``{"status": ..., "headers": ..., "body": ...}`` entries (a ``None`` entry answers
    normally, an ``{"answer": True, "truncated": bool}`` entry answers that request's
    questions with the given ``usage.truncated`` value), which is how the error-taxonomy and
    the truncated-escalation cases are driven. An entry with ``drip`` (seconds per byte) and
    ``drip_part`` (`body` by default, `headers`, `chunked`) trickles a raw response one byte
    per interval for the total-deadline cases; the trickle stops when the client gives up or
    the stub is closed.
    """

    def __init__(self, model="laya-rl-agent", top=0.9, tops=None, truncated=False,
                 uniform=False, delay=0.0, health=200, script=None, places=4):
        self.model = model
        self.top = top
        self.tops = dict(tops or {})
        self.truncated = truncated
        self.uniform = uniform
        self.delay = delay
        self.health = health
        self.script = list(script or [])
        self.places = places  # how the provider rounds: Laya 4 decimals, TypeSafe 2
        self.stopped = False  # set when __exit__ begins: an in-flight drip must stop at once
        self.requests = []
        self.server: http.server.ThreadingHTTPServer | None = None
        self.thread: threading.Thread | None = None

    def __enter__(self):
        stub = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                # Any path answers with `health`: the local row probes GET /health, the remote
                # rows probe their own paths, and each test asserts on the recorded path.
                stub.record("GET", self.path, {}, b"")
                self.reply(stub.health, b'{"status":"ok"}')

            def do_POST(self):
                raw = self.rfile.read(int(self.headers.get("Content-Length") or 0))
                stub.record("POST", self.path, dict(self.headers), raw)
                if stub.delay:
                    time.sleep(stub.delay)
                entry = stub.take_script()
                if entry is not None and entry.get("drip") is not None:
                    stub.drip_reply(self, entry)
                    return
                if entry is None:
                    entry = {"status": 200, "body": stub.answer_json(raw)}
                elif entry.get("answer"):
                    entry = {"status": 200,
                             "body": stub.answer_json(raw, truncated=entry.get("truncated"))}
                self.reply(entry.get("status", 200), entry.get("body", b""),
                           entry.get("headers"))

            def reply(self, status, body, headers=None):
                data = body.encode() if isinstance(body, str) else body
                self.send_response(status)
                for key, value in (headers or {}).items():
                    self.send_header(key, value)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                try:
                    self.wfile.write(data)
                except OSError:  # the client gave up (the timeout case): nothing to report
                    self.close_connection = True

            def log_message(self, *_ignored):
                pass

        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever,
                                       kwargs={"poll_interval": 0.05}, daemon=True)
        self.thread.start()
        return self

    def __exit__(self, *_exc):
        assert self.server is not None and self.thread is not None  # set by __enter__
        self.stopped = True
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
        return False

    @property
    def port(self):
        assert self.server is not None  # set by __enter__
        return self.server.server_port

    @property
    def url(self):
        return f"http://127.0.0.1:{self.port}/v1/systemone"

    @property
    def posts(self):
        return [record for record in self.requests if record["method"] == "POST"]

    @property
    def bodies(self):
        return [record["json"] for record in self.posts]

    def record(self, method, path, headers, raw):
        self.requests.append({"method": method, "path": path, "headers": headers, "body": raw,
                              "json": _maybe_json(raw), "at": time.monotonic()})

    def take_script(self):
        return self.script.pop(0) if self.script else None

    def drip(self, handler, data, interval):
        """Write `data` one byte per `interval` seconds, stopping on close or a dead socket."""
        for index in range(len(data)):
            if self.stopped:
                return
            try:
                handler.wfile.write(data[index:index + 1])
                handler.wfile.flush()
            except OSError:  # the run's watchdog shut the socket down: nothing to report
                return
            if interval:
                time.sleep(interval)

    def drip_reply(self, handler, entry):
        """Send one scripted response raw, trickling the part named by `drip_part`.

        `headers` dribbles the status line and the whole header block; `body` sends the
        headers at once and dribbles the body; `chunked` sends chunked headers at once and
        dribbles a chunk-size line padded with leading zeros. This is how a server that keeps
        every individual read under the socket timeout is tested against the total deadline.
        """
        status = entry.get("status", 200)
        body = entry.get("body", b"")
        if isinstance(body, str):
            body = body.encode()
        head = f"HTTP/1.1 {status} {http.client.responses.get(status, 'OK')}\r\n".encode()
        for key, value in (entry.get("headers") or {}).items():
            head += f"{key}: {value}\r\n".encode()
        head += b"\r\n"
        part = entry.get("drip_part", "body")
        if part == "headers":
            self.drip(handler, head, entry["drip"])
            if not self.stopped:
                self.drip(handler, body, 0)
        elif part == "chunked":
            self.drip(handler, head, 0)
            self.drip(handler, b"0" * 300 + b"1\r\n", entry["drip"])
        else:
            self.drip(handler, head, 0)
            self.drip(handler, body, entry["drip"])

    def answer_json(self, raw, truncated=None):
        questions = (_maybe_json(raw) or {}).get("questions") or {}
        usage = {"input_tokens": 10, "output_tokens": 0}
        forced = self.truncated if truncated is None else truncated
        if forced:
            usage["truncated"] = True
        answers = {qid: self.answer_for(qid, spec or {}) for qid, spec in questions.items()}
        return json.dumps({"model": self.model, "answers": answers, "usage": usage}).encode()

    def answer_for(self, qid, spec):
        qtype = spec.get("type", "noul")
        top = self.tops.get(qid, self.top)
        if qtype == "choice":
            options = list(spec.get("criteria") or {"x": "x"})
            probs = _distribution(top, options, uniform=self.uniform, places=self.places)
            return {"type": "choice", "choice": options[0], "confidence": probs[options[0]],
                    "probabilities": probs}
        if qtype == "score":
            levels = list(spec.get("criteria") or ["low", "mid", "high"])
            slots = [str(index) for index in range(len(levels))]
            winner = min(2, len(levels) - 1)
            return {"type": "score", "score": float(winner), "confidence": top,
                    "legend": dict(zip(slots, levels, strict=True)),
                    "probabilities": _distribution(top, slots, winner, self.uniform,
                                                   self.places)}
        return {"type": "noul", "noul": top}


class _ClientCase(unittest.TestCase):
    """A cleared env, a temp home, and Laya pointed at a closed port unless a stub says else."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        home = self.tmp / "home"
        home.mkdir(parents=True)
        patcher = mock.patch.dict(os.environ, {
            "HOME": str(home),
            "XDG_CONFIG_HOME": str(home / ".config"),
            "XDG_STATE_HOME": str(home / ".local/state"),
            "XDG_DATA_HOME": str(home / ".local/share"),
            "JEV_LAYA_URL": closed_port_url(),
        }, clear=True)
        patcher.start()
        self.addCleanup(patcher.stop)

    def point_at(self, stub):
        os.environ["JEV_LAYA_URL"] = stub.url

    def enable(self, backend: str | None = "laya"):
        os.environ["GSD_PATH_JEV"] = "1"
        os.environ["GSD_PATH_JEV_TIMEOUT_SECONDS"] = "5"
        if backend is not None:
            os.environ["JEV_BACKEND"] = backend

    def enable_remote(self, backend: str | None = None):
        """Consent and keys for both remote rows: the in-process stub is the only remote there is.

        `backend=None` keeps the choice on auto, which is how a remote rung gets reached by
        escalation instead of by name.
        """
        self.enable(backend)
        os.environ["JEV_ALLOW_REMOTE"] = "1"
        os.environ["TYPESAFE_API_KEY"] = "typesafe-key"
        os.environ["OPENCODE_ZEN_API_KEY"] = "zen-key"

    def run_screen(self, payload_value, stdin_text=None):
        text = stdin_text if stdin_text is not None else json.dumps(payload_value)
        with mock.patch.object(sys, "stdin", io.StringIO(text)):
            return JR.screen()

    def run_main(self, payload_value):
        """main([]) on a payload: (exit code, the parsed stdout JSON)."""
        code, text, _err = self.run_main_text(payload_value)
        return code, json.loads(text)

    def run_main_text(self, payload_value):
        """main([]) on a payload, returning the raw stdout too: (exit code, stdout, stderr)."""
        out, err = io.StringIO(), io.StringIO()
        with (mock.patch.object(sys, "stdin", io.StringIO(json.dumps(payload_value))),
              mock.patch.object(sys, "stdout", out), mock.patch.object(sys, "stderr", err)):
            code = JR.main([])
        return code, out.getvalue(), err.getvalue()

    def run_probe(self):
        """main(["--probe"]): (exit code, the parsed stdout JSON)."""
        code, text = self.run_probe_text()
        return code, json.loads(text)

    def run_cli_screen(self, payload_value, argv):
        """main(argv) on a screen payload: (exit code, the parsed stdout JSON)."""
        out = io.StringIO()
        with (mock.patch.object(sys, "stdin", io.StringIO(json.dumps(payload_value))),
              mock.patch.object(sys, "stdout", out)):
            code = JR.main(argv)
        return code, json.loads(out.getvalue())

    def run_probe_text(self):
        """main(["--probe"]) with the raw stdout too, so a test can grep for a key value."""
        out = io.StringIO()
        with mock.patch.object(sys, "stdout", out):
            code = JR.main(["--probe"])
        return code, out.getvalue()

    def backend_entry(self, report, name):
        return next(entry for entry in report["backends"] if entry["name"] == name)

    def assert_no_posts(self, stub):
        self.assertEqual(stub.posts, [], "a probe must never send question content")

    def point_remote(self, name, stub):
        """Point one remote row's own URL env at `stub`'s origin: no test dials a real host.

        The row's `url` adapter reads `JEV_TYPESAFE_URL` / `JEV_OPENCODE_URL`, so the override
        happens in the environment exactly where it would for a real user.
        """
        env = {"typesafe": "JEV_TYPESAFE_URL", "opencode": "JEV_OPENCODE_URL"}[name]
        os.environ[env] = f"http://127.0.0.1:{stub.port}"

    def stub_row(self, name, stub, **changes):
        """A fourth backend invented for the test: url/key/probe/classify over `stub`."""
        row = dict(JR.row_named("laya"))
        row.update({"name": name, "models": ("q-1", "q-2"), "model_env": "JEV_Q_MODEL",
                    "url": lambda: (stub.url, None), "key": lambda: ("k", "env"),
                    "probe": lambda _row, _timeout, _deadline: None})
        row.update(changes)
        return row


class TestProbe(_ClientCase):
    def test_probe_laya_up(self):
        with JevStub() as stub:
            self.point_at(stub)
            code, report = self.run_probe()
        self.assertEqual(code, 0)
        self.assertEqual(report["status"], "ok")
        self.assertEqual(report["selected"], "laya")
        self.assertEqual(report["candidates"], ["laya"])
        self.assertEqual([entry["name"] for entry in report["backends"]], ROW_NAMES)
        self.assertEqual(self.backend_entry(report, "laya"),
                         {"name": "laya", "remote": False, "batch": False,
                          "host": "127.0.0.1", "usable": True, "key_source": None})
        self.assert_no_posts(stub)

    def test_probe_laya_url_sources(self):
        # Adapter only, no socket: nothing here resolves a name or opens a connection.
        del os.environ["JEV_LAYA_URL"]
        self.assertEqual(JR._laya_url(), ("http://127.0.0.1:8010/v1/systemone", None))
        os.environ["JEV_API_URL"] = "https://opencode.ai/zen/v1/systemone"
        self.assertEqual(JR._laya_url(), ("http://127.0.0.1:8010/v1/systemone", None),
                         "a non-loopback JEV_API_URL is skipped, never refused")
        os.environ["JEV_API_URL"] = f"http://{REMOTE_HOST}:8010/v1/systemone"
        self.assertEqual(JR._laya_url(), ("http://127.0.0.1:8010/v1/systemone", None))
        os.environ["JEV_API_URL"] = "http://127.0.0.1:8123/v1/systemone"
        self.assertEqual(JR._laya_url(), ("http://127.0.0.1:8123/v1/systemone", None),
                         "a loopback JEV_API_URL is used")
        os.environ["JEV_LAYA_URL"] = "http://127.0.0.1:8123"
        self.assertEqual(JR._laya_url(), ("http://127.0.0.1:8123/v1/systemone", None),
                         "JEV_LAYA_URL wins over JEV_API_URL")
        del os.environ["JEV_API_URL"], os.environ["JEV_LAYA_URL"]
        for name in ("JEV_LAYA_URL", "AI_KIT_LAYA_URL"):
            os.environ[name] = f"http://{REMOTE_HOST}:8010"
            self.assertEqual(JR._laya_url(), (None, "non_loopback_url"), name)
            del os.environ[name]
        os.environ["JEV_LAYA_URL"] = "http://localhost:8010"
        self.assertEqual(JR._laya_url(), ("http://localhost:8010/v1/systemone", None))

    def test_probe_nothing_reachable(self):
        with JevStub(health=503) as stub:
            self.point_at(stub)
            started = time.monotonic()
            code, report = self.run_probe()
            elapsed = time.monotonic() - started
        self.assertEqual(code, 0)
        self.assertEqual(report["status"], "unavailable")
        self.assertEqual(report["reason"], "no_backend_available")
        self.assertEqual(report["selected"], None)
        self.assertEqual(self.backend_entry(report, "laya")["reason"], "unreachable")
        self.assertEqual([entry["name"] for entry in report["backends"]], ROW_NAMES)
        self.assertLess(elapsed, 3.0)
        self.assert_no_posts(stub)

    def test_probe_non_loopback_laya(self):
        os.environ["JEV_LAYA_URL"] = f"http://{REMOTE_HOST}:8010"
        _code, report = self.run_probe()
        self.assertEqual(self.backend_entry(report, "laya")["reason"], "non_loopback_url")
        self.assertEqual(report["unavailable"]["laya"], "non_loopback_url")
        self.enable()
        with JevStub() as stub:  # the endpoint exists; the refusal has to happen before it
            with self.assertRaises(PermissionError) as refused:
                JR._send(JR.row_named("laya"),
                         {"model": "jev-1", "state": payload(noul_item("a")),
                          "questions": {"a": {"type": "noul", "instructions": "x"}}}, 1.0)
            self.assertEqual(str(refused.exception), "non_loopback_url")
            self.assertEqual(stub.posts, [])

    def test_probe_uses_get_health_and_never_posts(self):
        with JevStub() as stub:
            self.point_at(stub)
            _code, report = self.run_probe()
        self.assertEqual(report["status"], "ok")
        self.assertEqual([(entry["method"], entry["path"]) for entry in stub.requests],
                         [("GET", "/health")])
        self.assert_no_posts(stub)

    def test_probe_backend_choice_narrows_candidates(self):
        with JevStub() as stub:
            self.point_at(stub)
            os.environ["JEV_BACKEND"] = "laya"
            _code, report = self.run_probe()
        self.assertEqual(report["candidates"], ["laya"])
        self.assertEqual(report["selected"], "laya")
        self.assert_no_posts(stub)

    def test_probe_unknown_backend_name(self):
        # A name that is not a row: the composite reason says so, and every row still gets its
        # own entry -- the same `backend_unavailable:<name>:unknown_backend` screen reports.
        with JevStub() as stub:
            self.point_at(stub)
            os.environ["JEV_BACKEND"] = "zen"
            code, report = self.run_probe()
        self.assertEqual(code, 0)
        self.assertEqual(report["status"], "unavailable")
        self.assertEqual(report["reason"], "backend_unavailable:zen:unknown_backend")
        self.assertEqual(report["candidates"], [])
        self.assertEqual(report["unavailable"], {"zen": "unknown_backend"})
        self.assertEqual([entry["name"] for entry in report["backends"]], ROW_NAMES)
        self.assert_no_posts(stub)

    def test_probe_works_with_the_kill_switch_off(self):
        with JevStub() as stub:
            self.point_at(stub)
            os.environ.pop("GSD_PATH_JEV", None)
            code, report = self.run_probe()
        self.assertEqual(code, 0)
        self.assertEqual(report["status"], "ok")
        self.assertEqual(report["selected"], "laya")


class TestScreen(_ClientCase):
    def test_screen_laya_one_request_per_item(self):
        with JevStub() as stub:
            self.point_at(stub)
            self.enable("laya")
            result = self.run_screen(THREE_ITEMS)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["backend"], "laya")
        self.assertEqual(len(stub.posts), 3)  # N items, N requests: sequential, never batched
        for body, item_id in zip(stub.bodies, ["a", "b", "c"], strict=True):
            self.assertEqual([item["id"] for item in body["state"]["items"]], [item_id])
            self.assertEqual(list(body["questions"]), [item_id])
            self.assertEqual(body["model"], "jev-1")
        self.assertEqual(set(result["answers"]), {"a", "b", "c"})
        for answer in result["answers"].values():
            self.assertEqual(answer["model"], "laya-rl-agent")
            self.assertFalse(answer["needs_fallback"])
        self.assertEqual(result["usage"]["input_tokens"], 30)

    def test_screen_kill_switch_before_stdin(self):
        class _NoStdin:
            def read(self, *_ignored):
                raise AssertionError("stdin was read with the kill switch off")

        os.environ.pop("GSD_PATH_JEV", None)
        with JevStub() as stub:
            self.point_at(stub)
            with mock.patch.object(sys, "stdin", _NoStdin()):
                result = JR.screen()
        self.assertEqual(result, {"status": "disabled"})
        self.assert_no_posts(stub)

    def test_screen_empty_items_rejected(self):
        with JevStub() as stub:
            self.point_at(stub)
            self.enable("laya")
            result = self.run_screen({"reviewed_head": HEAD, "items": []})
        self.assertEqual(result["status"], "unavailable")
        self.assertEqual(result["reason"], "invalid_input")
        self.assert_no_posts(stub)

    def test_screen_bad_head_is_invalid_input(self):
        self.enable("laya")
        result = self.run_screen({"reviewed_head": "not-a-sha", "items": [noul_item("a")]})
        self.assertEqual(result["reason"], "invalid_input")

    def test_screen_invalid_min_confidence_and_timeout(self):
        self.enable("laya")
        os.environ["JEV_MIN_CONFIDENCE"] = "not-a-number"
        self.assertEqual(self.run_screen(THREE_ITEMS)["reason"], "invalid_min_confidence")
        del os.environ["JEV_MIN_CONFIDENCE"]
        os.environ["GSD_PATH_JEV_TIMEOUT_SECONDS"] = "0"
        self.assertEqual(self.run_screen(THREE_ITEMS)["reason"], "invalid_timeout")

    def test_screen_unknown_backend_reason(self):
        self.enable("zen")
        result = self.run_screen(THREE_ITEMS)
        self.assertEqual(result["status"], "unavailable")
        self.assertEqual(result["reason"], "backend_unavailable:zen:unknown_backend")

    def test_screen_no_backend_available_reports_reasons(self):
        self.enable(None)  # auto
        result = self.run_screen(THREE_ITEMS)
        self.assertEqual(result["status"], "unavailable")
        self.assertEqual(result["reason"], "no_backend_available")
        # Task 2: the two remote rows are gated, so they are reported and never dialled.
        self.assertEqual(result["unavailable"], {"laya": "unreachable",
                                                 "typesafe": "missing_api_key",
                                                 "opencode": "missing_api_key"})

    def test_screen_min_confidence_override_marks_fallback(self):
        with JevStub(top=0.8) as stub:
            self.point_at(stub)
            self.enable("laya")
            os.environ["JEV_MIN_CONFIDENCE"] = "0.99"
            result = self.run_screen(THREE_ITEMS)
        self.assertEqual(result["status"], "ok")
        self.assertTrue(all(a["needs_fallback"] for a in result["answers"].values()))


class TestTolerance(_ClientCase):
    def test_tolerance_four_decimals(self):
        self.assertEqual(JR._PROB_SUM_TOLERANCE, 2e-2)  # D-15 pinned as a literal
        answer = {"type": "choice", "choice": "x", "confidence": 0.3333,
                  "probabilities": {"x": 0.3333, "y": 0.3333, "z": 0.3333}}
        checked = JR._check_choice_answer(answer, {"x": "", "y": "", "z": ""})
        self.assertEqual(checked["type"], "choice")
        self.assertAlmostEqual(math.fsum(answer["probabilities"].values()), 0.9999, places=4)
        with JevStub(top=0.3333, uniform=True) as stub:
            self.point_at(stub)
            self.enable("laya")
            result = self.run_screen(payload(choice_item("c1")))
        self.assertEqual(result["status"], "ok")
        got = result["answers"]["c1"]
        self.assertAlmostEqual(math.fsum(got["probabilities"].values()), 0.9999, places=4)
        self.assertTrue(got["needs_fallback"])  # 0.3333 sits below the row's threshold

    def test_tolerance_score_end_to_end(self):
        with JevStub(top=0.9) as stub:
            self.point_at(stub)
            self.enable("laya")
            result = self.run_screen(payload(score_item("s1")))
        self.assertEqual(result["status"], "ok")
        answer = result["answers"]["s1"]
        self.assertEqual(answer["type"], "score")
        self.assertEqual(answer["legend"], {"0": "low", "1": "mid", "2": "high"})
        self.assertEqual(answer["model"], "laya-rl-agent")


class TestTaxonomy(_ClientCase):
    """One test per row of the 2026-10-11 Laya error taxonomy (D-13), plus the two size guards."""

    def scripted(self, script, items=None, **stub_kwargs):
        with JevStub(script=script, **stub_kwargs) as stub:
            self.point_at(stub)
            self.enable("laya")
            result = self.run_screen(items or payload(noul_item("a")))
        return result, stub

    def test_taxonomy_503_retried_then_ok(self):
        naps = []
        script = [{"status": 503, "headers": {"Retry-After": "1"}, "body": b"busy"},
                  {"status": 503, "headers": {"Retry-After": "1"}, "body": b"busy"}]
        with mock.patch.object(JR, "_sleep", side_effect=naps.append):
            result, stub = self.scripted(script)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(len(stub.posts), 3)  # the original plus the two retries it allows
        self.assertEqual(naps, [1.0, 1.0])  # Retry-After, honored through the patched _sleep

    def test_taxonomy_503_exhausted_explicit(self):
        script = [{"status": 503, "headers": {"Retry-After": "0"}, "body": b"busy"}] * 3
        with mock.patch.object(JR, "_sleep", side_effect=lambda _seconds: None):
            result, stub = self.scripted(script)
        self.assertEqual(len(stub.posts), 3)
        self.assertEqual(result["status"], "unavailable")
        self.assertEqual(result["reason"], "http_503")
        self.assertEqual(result["errors"], {"a": "http_503"})

    def test_taxonomy_503_exhausted_auto_falls_back(self):
        """The full 21.1-01 wire shape: Laya exhausts its 503s in auto, typesafe answers, Zen
        is never touched. The laya stub is the `laya` row; the typesafe stub is the `typesafe`
        row pointed at its own port by `JEV_TYPESAFE_URL`."""
        with (JevStub(script=[{"status": 503, "headers": {"Retry-After": "0"},
                                "body": b"busy"}] * 3) as laya,
              JevStub(model="typesafe-1") as typesafe,
              JevStub(model="opencode-1") as zen):
            self.point_at(laya)
            self.point_remote("typesafe", typesafe)
            self.point_remote("opencode", zen)
            self.enable_remote(None)
            with mock.patch.object(JR, "_sleep", side_effect=lambda _seconds: None):
                result = self.run_screen(payload(noul_item("a")))
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["backend"], "typesafe")
        self.assertEqual(result["model"], "typesafe-1")
        self.assertEqual(len(laya.posts), 3)  # the original plus the two retries it allows
        self.assertEqual(len(typesafe.posts), 1)
        self.assertEqual(zen.posts, [])  # the item is answered: nothing reaches the next rung
        # One attempt-log entry per rung that failed, not per retry inside that rung.
        self.assertEqual([entry["reason"] for entry in result["attempts"]], ["http_503"])

    def test_typesafe_row_targets_documented_endpoint(self):
        """The default is the documented POST URL, and the probe is the documented bearer GET
        `/v1/models` on the row's own origin (docs.typesafe.ai/api.md)."""
        os.environ.pop("JEV_TYPESAFE_URL", None)
        self.assertEqual(JR._typesafe_url(), ("https://api.typesafe.ai/v1/systemone", None))
        with JevStub() as typesafe:
            self.point_remote("typesafe", typesafe)
            os.environ["TYPESAFE_API_KEY"] = "dummy"
            row = JR.row_named("typesafe")
            self.assertIsNone(row["probe"](row, 5))
        self.assertEqual([(r["method"], r["path"]) for r in typesafe.requests],
                         [("GET", "/v1/models")])

    def test_opencode_row_targets_documented_endpoint(self):
        """The default POST target is Zen's documented Jev endpoint (opencode.ai/docs/zen)."""
        os.environ.pop("JEV_OPENCODE_URL", None)
        self.assertEqual(JR._opencode_url(),
                         ("https://opencode.ai/inference/systemone/v1/systemone", None))

    def test_taxonomy_500_escalates_without_retry(self):
        result, stub = self.scripted([{"status": 500, "body": b"inference failed"}])
        self.assertEqual(len(stub.posts), 1)
        self.assertEqual(result["errors"], {"a": "http_500"})
        self.assertEqual(result["status"], "unavailable")

    def test_taxonomy_refused_connection(self):
        # The row is selectable (the probe answers), then the connection itself is refused: the
        # classifier, not the socket, is what this row of the taxonomy is about.
        with JevStub() as stub:
            self.point_at(stub)
            self.enable("laya")
            with mock.patch.object(JR, "_send",
                                   side_effect=ConnectionRefusedError("[Errno 111] refused")):
                result = self.run_screen(payload(noul_item("a")))
        self.assertEqual(result["status"], "unavailable")
        self.assertEqual(result["errors"], {"a": "network_error"})
        self.assertEqual(stub.posts, [])

    def test_taxonomy_timeout(self):
        with JevStub(delay=0.6) as stub:
            self.point_at(stub)
            self.enable("laya")
            os.environ["GSD_PATH_JEV_TIMEOUT_SECONDS"] = "0.2"
            result = self.run_screen(payload(noul_item("a")))
        self.assertEqual(result["errors"], {"a": "network_error"})
        self.assertEqual(len(stub.posts), 1)

    def test_taxonomy_400_caller_error(self):
        result, stub = self.scripted([{"status": 400, "body": b'{"error":"bad request"}'}])
        self.assertEqual(result["errors"], {"a": "caller_error:http_400"})
        self.assertEqual(len(stub.posts), 1)

    def test_taxonomy_413_caller_error(self):
        result, stub = self.scripted([{"status": 413, "body": b"too large"}])
        self.assertEqual(result["errors"], {"a": "caller_error:http_413"})
        self.assertEqual(len(stub.posts), 1)

    def test_taxonomy_422_caller_error(self):
        result, stub = self.scripted([{"status": 422, "body": b"unknown type"}])
        self.assertEqual(result["errors"], {"a": "caller_error:http_422"})
        self.assertEqual(len(stub.posts), 1)

    def test_taxonomy_malformed_json_is_invalid_response(self):
        result, stub = self.scripted([{"status": 200, "body": b"{not json"}])
        self.assertEqual(result["errors"], {"a": "invalid_response"})
        self.assertEqual(len(stub.posts), 1)

    def test_taxonomy_wrong_response_model_is_invalid_response(self):
        with JevStub(model="gpt-4o") as stub:
            self.point_at(stub)
            self.enable("laya")
            result = self.run_screen(payload(noul_item("a")))
        self.assertEqual(result["errors"], {"a": "invalid_response"})

    def test_taxonomy_truncated(self):
        self.enable("laya")
        limit = JR.row_named("laya")["state_chars_limit"]
        with JevStub(top=0.95, truncated=True) as stub:
            self.point_at(stub)
            flagged = self.run_screen(payload(noul_item("a")))["answers"]["a"]
        long_item = noul_item("a", context="x" * (limit + 500))
        with JevStub(top=0.95) as stub:  # no `truncated` field at all: the size guard alone
            self.point_at(stub)
            over_size = self.run_screen(payload(long_item))["answers"]["a"]
        with JevStub(top=0.95) as stub:
            self.point_at(stub)
            clean = self.run_screen(payload(noul_item("a")))["answers"]["a"]
        self.assertTrue(flagged["needs_fallback"], "usage.truncated forces the flag at 0.95")
        self.assertTrue(over_size["needs_fallback"], "an over-limit state forces the flag")
        self.assertFalse(clean["needs_fallback"], "0.95 with neither condition is confident")

    def test_taxonomy_oversized_200(self):
        padded = json.dumps({"model": "laya-rl-agent",
                             "answers": {"b": {"type": "noul", "noul": 0.95}},
                             "usage": {"input_tokens": 1, "output_tokens": 0},
                             "pad": "x" * 2000}).encode()
        script = [None, {"status": 200, "body": padded}]
        with (mock.patch.object(JR, "_MAX_RESPONSE_BYTES", 1024),
              JevStub(script=script) as stub):
            self.point_at(stub)
            self.enable("laya")
            code, result = self.run_main(THREE_ITEMS)
        self.assertEqual(code, 0)
        self.assertEqual(len(stub.posts), 3)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(set(result["answers"]), {"a", "c"})  # the siblings keep their answers
        self.assertEqual(result["errors"], {"b": "invalid_response"})

    def test_taxonomy_302_is_not_an_answer(self):
        # The redirect target is never re-opened, so the Authorization header can not follow it.
        result, stub = self.scripted([{"status": 302,
                                       "headers": {"Location": "/elsewhere"}, "body": b""}])
        self.assertEqual(result["errors"], {"a": "http_302"})
        self.assertEqual(len(stub.posts), 1)

    def test_taxonomy_request_sha256_covers_the_raised_body(self):
        self.enable("laya")
        real_send = JR._send
        calls = []

        def flaky(row, body, timeout, deadline=None):
            calls.append(body)
            response, encoded = real_send(row, body, timeout, deadline)
            if len(calls) == 2:
                raise OSError("down")
            return response, encoded

        with (mock.patch.object(JR, "_send", flaky), JevStub() as stub):
            self.point_at(stub)
            result = self.run_screen(THREE_ITEMS)
        wire = b"".join(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
                        for body in calls)
        self.assertEqual(result["request_sha256"], hashlib.sha256(wire).hexdigest())
        self.assertEqual(result["errors"], {"b": "network_error"})


class TestProbabilityRules(unittest.TestCase):
    """The client is the authority on what a probability is (D-15): pure functions, no stub."""

    def test_bool_is_never_a_probability_or_a_token_count(self):
        self.assertFalse(JR.probability(True), "bool is an int subclass: True is not 1.0 here")
        self.assertFalse(JR.probability(False))
        self.assertFalse(JR.whole(True))
        self.assertTrue(JR.probability(1))
        self.assertTrue(JR.probability(0.9999))
        self.assertTrue(JR.whole(0))

    def test_noul_answer_rejects_bool_and_nan(self):
        for answer in ({"type": "noul", "noul": True}, {"type": "noul", "noul": float("nan")},
                       {"type": "noul", "noul": "0.9"}, {"type": "noul", "noul": 1.5}):
            with self.assertRaises(ValueError, msg=str(answer)):
                JR._check_noul_answer(answer, None)


class TestRemoteRows(_ClientCase):
    """The two remote rows (D-09, D-11, D-26): batch shape, model policy, error taxonomy."""

    def remote_screen(self, name, stub, items=None):
        """A remote row's screen run: the stub is that backend's endpoint, consent given."""
        self.point_remote(name, stub)
        self.enable_remote(name)
        return self.run_screen(items or payload(noul_item("a")))

    def test_typesafe_batch_two_items_one_request(self):
        items = payload(noul_item("a"), noul_item("b"))
        with JevStub(model="typesafe-1") as stub:
            self.point_remote("typesafe", stub)
            self.enable_remote("typesafe")
            result = self.run_screen(items)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["backend"], "typesafe")
        self.assertEqual(len(stub.posts), 1)  # batch: True — two items, one request
        self.assertEqual(sorted(stub.bodies[0]["questions"]), ["a", "b"])
        self.assertEqual([item["id"] for item in stub.bodies[0]["state"]["items"]], ["a", "b"])
        self.assertEqual(set(result["answers"]), {"a", "b"})

    def test_tolerance_typesafe_two_decimals_are_accepted(self):
        # TypeSafe rounds to 2 decimals: a 3-way answer sums to 0.99, inside the tolerance.
        items = payload(choice_item("c1"))
        with JevStub(model="typesafe-1", uniform=True, places=2, top=0.33) as stub:
            self.point_remote("typesafe", stub)
            self.enable_remote("typesafe")
            os.environ["JEV_MIN_CONFIDENCE"] = "0.3"  # below the row's own 0.8
            result = self.run_screen(items)
        self.assertEqual(result["status"], "ok")
        self.assertNotIn("errors", result)
        answer = result["answers"]["c1"]
        self.assertAlmostEqual(math.fsum(answer["probabilities"].values()), 0.99, places=4)
        self.assertFalse(answer["needs_fallback"])  # 0.33 >= the overridden 0.3 threshold

    def test_typesafe_one_decimal_sum_is_rejected(self):
        # The tolerance is bounded: a 3-way answer summing to 0.90 is not a probability space.
        items = payload(choice_item("c1"))
        with JevStub(model="typesafe-1", uniform=True, places=1, top=0.3) as stub:
            self.point_remote("typesafe", stub)
            self.enable_remote("typesafe")
            result = self.run_screen(items)
        self.assertEqual(result["errors"], {"c1": "invalid_response"})

    def test_model_policy_typesafe_single_id_402_escalates(self):
        with JevStub(script=[{"status": 402, "body": b"billing"}], model="typesafe-1") as stub:
            self.point_remote("typesafe", stub)
            self.enable_remote("typesafe")
            result = self.run_screen(payload(noul_item("a")))
        self.assertEqual(len(stub.posts), 1)  # one model id: nothing else to try
        self.assertEqual(result["status"], "unavailable")
        self.assertEqual(result["errors"], {"a": "http_402"})

    def test_model_policy_typesafe_pinned_sends_only_that_id(self):
        with JevStub(model="typesafe-1") as stub:
            self.point_remote("typesafe", stub)
            self.enable_remote("typesafe")
            os.environ["JEV_TYPESAFE_MODEL"] = "jev-2027-01"
            _result = self.run_screen(payload(noul_item("a"), noul_item("b")))
        self.assertEqual({body["model"] for body in stub.bodies}, {"jev-2027-01"})

    def test_model_policy_opencode_free_id_first_then_paid(self):
        script = [{"status": 429, "body": b"quota"}]
        with JevStub(script=script, model="opencode-1") as stub:
            self.point_remote("opencode", stub)
            self.enable_remote("opencode")
            result = self.run_screen(payload(noul_item("a")))
        self.assertEqual(result["status"], "ok")
        self.assertEqual([body["model"] for body in stub.bodies],
                         ["jev-1.13-free", "jev-1.13"])  # the same group body, next id
        self.assertEqual(result["answers"]["a"]["model"], "opencode-1")
        self.assertEqual(result["attempts"], [])  # a recovered free 429 leaves no entry

    def test_model_policy_opencode_402_switches_model(self):
        script = [{"status": 402, "body": b"billing"}]
        with JevStub(script=script, model="opencode-1") as stub:
            self.point_remote("opencode", stub)
            self.enable_remote("opencode")
            result = self.run_screen(payload(noul_item("a")))
        self.assertEqual(result["status"], "ok")
        self.assertEqual([body["model"] for body in stub.bodies],
                         ["jev-1.13-free", "jev-1.13"])

    def test_opencode_both_models_exhausted_keeps_the_last_reason(self):
        script = [{"status": 429, "body": b"quota"}] * 2
        with JevStub(script=script, model="opencode-1") as stub:
            self.point_remote("opencode", stub)
            self.enable_remote("opencode")
            result = self.run_screen(payload(noul_item("a")))
        self.assertEqual(len(stub.posts), 2)  # both model ids, both refused
        self.assertEqual([body["model"] for body in stub.bodies],
                         ["jev-1.13-free", "jev-1.13"])
        self.assertEqual(result["status"], "unavailable")
        self.assertEqual(result["errors"]["a"], "http_429")
        # the entry names the paid id that gave the final error, not the free one
        self.assertEqual(result["attempts"],
                         [{"backend": "opencode", "model": "jev-1.13", "reason": "http_429"}])

    def test_model_policy_opencode_pinned_sends_only_that_id(self):
        script = [{"status": 429, "body": b"quota"}] * 2
        with JevStub(script=script, model="opencode-1") as stub:
            self.point_remote("opencode", stub)
            self.enable_remote("opencode")
            os.environ["JEV_OPENCODE_MODEL"] = "jev-custom"
            result = self.run_screen(payload(noul_item("a"), noul_item("b")))
        self.assertEqual([body["model"] for body in stub.bodies], ["jev-custom", "jev-custom"])
        self.assertEqual({item["id"] for body in stub.bodies
                          for item in body["state"]["items"]}, {"a", "b"})
        self.assertEqual(result["errors"], {"a": "http_429", "b": "http_429"})

    def test_opencode_5xx_retries_then_escalates(self):
        script = [{"status": 500, "body": b"bad gateway"}] * 3
        with (JevStub(script=script, model="opencode-1") as stub,
              mock.patch.object(JR, "_sleep", side_effect=lambda _seconds: None)):
            self.point_remote("opencode", stub)
            self.enable_remote("opencode")
            result = self.run_screen(payload(noul_item("a")))
        self.assertEqual(len(stub.posts), 3)  # the original plus retry_limit retries
        self.assertEqual(result["errors"], {"a": "http_500"})

    def test_opencode_401_is_unauthorized_and_not_retried(self):
        with JevStub(script=[{"status": 401, "body": b"nope"}], model="opencode-1") as stub:
            self.point_remote("opencode", stub)
            self.enable_remote("opencode")
            result = self.run_screen(payload(noul_item("a")))
        self.assertEqual(len(stub.posts), 1)
        self.assertEqual(result["errors"], {"a": "unauthorized"})

    def test_opencode_400_is_a_caller_error(self):
        # The 2026-10-11 note: a 400 from Zen means a model id that does not exist.
        with JevStub(script=[{"status": 400, "body": b"unknown model"}],
                     model="opencode-1") as stub:
            self.point_remote("opencode", stub)
            self.enable_remote("opencode")
            result = self.run_screen(payload(noul_item("a")))
        self.assertEqual(result["errors"], {"a": "caller_error:http_400"})

    def test_wrong_response_model_pattern_is_invalid_response(self):
        # The typesafe row only accepts `typesafe-*`: a Zen id in that seat is a bad response.
        with JevStub(model="opencode-1") as stub:
            self.point_remote("typesafe", stub)
            self.enable_remote("typesafe")
            result = self.run_screen(payload(noul_item("a")))
        self.assertEqual(result["errors"], {"a": "invalid_response"})

    def test_remote_row_needs_the_gate_before_a_socket(self):
        row = JR.row_named("typesafe")
        body, _specs = JR.request_body(payload(noul_item("a")), "jev-latest")
        self.enable(None)  # the kill switch is on, consent for the remote is not
        with (mock.patch.object(JR, "_read_key", return_value=("ssn-key", None)),
              self.assertRaises(PermissionError) as refused):
            JR._send(row, body, 1.0)
        self.assertEqual(str(refused.exception), "consent_required_for_remote")


class TestGate(_ClientCase):
    """The session consent gate (D-17, SPEC R5): a remote call answers with uz's money."""

    def test_gate_open_by_number(self):
        os.environ["JEV_ALLOW_REMOTE"] = "1"
        self.assertTrue(JR._gate_open("typesafe"))
        self.assertTrue(JR._gate_open("opencode"))

    def test_gate_open_by_name_list(self):
        os.environ["JEV_ALLOW_REMOTE"] = "typesafe, opencode"
        self.assertTrue(JR._gate_open("typesafe"))
        self.assertTrue(JR._gate_open("opencode"))
        self.assertFalse(JR._gate_open("other"))

    def test_gate_closed_by_anything_else(self):
        for value in ("", "0", "yes", "laya"):
            os.environ["JEV_ALLOW_REMOTE"] = value
            self.assertFalse(JR._gate_open("typesafe"), value)
        os.environ.pop("JEV_ALLOW_REMOTE", None)
        self.assertFalse(JR._gate_open("typesafe"))

    def test_screen_remote_requires_consent_and_sends_zero(self):
        with JevStub(model="typesafe-1") as stub:
            self.point_remote("typesafe", stub)
            os.environ["TYPESAFE_API_KEY"] = "ssn-key"
            os.environ.pop("JEV_ALLOW_REMOTE", None)  # auto, no consent
            self.enable(None)
            result = self.run_screen(payload(noul_item("a")))
            self.assertIn("consent_required_for_remote", result["status"])
            self.assertEqual(result["remote_available"], ["typesafe"])
            self.assertEqual(stub.requests, [])

    def test_probe_reports_consent_required_without_dialling(self):
        with JevStub(model="typesafe-1") as stub:
            self.point_remote("typesafe", stub)
            os.environ["TYPESAFE_API_KEY"] = "ssn-key"
            os.environ["LAYA_API_KEY"] = ""
            _code, report = self.run_probe()
        self.assertEqual(self.backend_entry(report, "typesafe")["usable"], False)
        self.assertEqual(self.backend_entry(report, "typesafe")["reason"],
                         "consent_required_for_remote")
        self.assertEqual(self.backend_entry(report, "typesafe")["key_source"], "env")
        self.assertEqual(self.backend_entry(report, "typesafe")["remote"], True)
        self.assertEqual(stub.requests, [])

    def test_gate_by_name_dials_only_the_named_remote(self):
        with JevStub(model="typesafe-1") as typesafe, JevStub(model="opencode-1") as zen:
            os.environ["JEV_ALLOW_REMOTE"] = "typesafe"
            os.environ["TYPESAFE_API_KEY"] = "ssn-key"
            os.environ["OPENCODE_ZEN_API_KEY"] = "zen-key"
            self.point_remote("typesafe", typesafe)
            self.point_remote("opencode", zen)
            self.enable(None)
            _code, report = self.run_probe()
            self.assertEqual(report["candidates"], ["typesafe"])  # named, reachable
            self.assertEqual(self.backend_entry(report, "opencode")["reason"],
                             "consent_required_for_remote")
            result = self.run_screen(payload(noul_item("a")))
        self.assertEqual(result["backend"], "typesafe")
        self.assertEqual(zen.requests, [])  # the other remote was never dialled

    def test_consent_seam_is_logged_when_the_gate_is_closed(self):
        with JevStub(model="typesafe-1") as stub:
            self.point_remote("typesafe", stub)
            os.environ["TYPESAFE_API_KEY"] = "ssn-key"
            self.enable(None)
            with self.assertLogs("jev_review", level="INFO") as captured:
                result = self.run_screen(payload(noul_item("a")))
        self.assertIn("consent_required_for_remote", result["status"])
        self.assertEqual(len(captured.output), 1)
        self.assertIn("typesafe", captured.output[0])

    def test_consent_seam_is_silent_when_the_gate_is_open(self):
        with JevStub(model="typesafe-1") as stub:
            self.point_remote("typesafe", stub)
            self.enable_remote("typesafe")
            with self.assertNoLogs("jev_review", level="INFO"):
                result = self.run_screen(payload(noul_item("a")))
        self.assertEqual(result["status"], "ok")

    def test_consent_seam_is_silent_when_no_remote_has_a_key(self):
        self.enable(None)  # auto, gate closed, and no remote row has a key
        with self.assertNoLogs("jev_review", level="INFO"):
            result = self.run_screen(payload(noul_item("a")))
        self.assertEqual(result["reason"], "no_backend_available")


class TestKeys(_ClientCase):
    """Key resolution and the non-disclosure rules (D-09, D-11, SPEC R5)."""

    SENTINEL = "NEVER-PRINT-ME"

    def typesafe_file(self, text="ssn-from-file\n", mode=0o600):
        path = Path(os.environ["XDG_STATE_HOME"]) / "typesafe" / "api_key"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        os.chmod(path, mode)
        return path

    def test_keys_typesafe_env_vs_file(self):
        self.typesafe_file()
        os.environ["TYPESAFE_API_KEY"] = self.SENTINEL
        self.assertEqual(JR._typesafe_key(), (self.SENTINEL, "env"))

    def test_typesafe_file_key_when_no_env(self):
        os.environ.pop("TYPESAFE_API_KEY", None)
        self.typesafe_file()
        self.assertEqual(JR._typesafe_key(), ("ssn-from-file", "file"))

    def test_typesafe_0644_file_is_refused_as_world_readable(self):
        os.environ.pop("TYPESAFE_API_KEY", None)
        self.typesafe_file(mode=0o644)
        self.assertEqual(JR._typesafe_key(), (None, "world_readable"))

    def test_keys_typesafe_0600_file_is_accepted(self):
        os.environ.pop("TYPESAFE_API_KEY", None)
        path = self.typesafe_file(mode=0o600)
        value, label = JR._read_key(str(path))
        self.assertEqual((value, label), ("ssn-from-file", None))

    def test_typesafe_empty_and_missing_file_reasons(self):
        os.environ.pop("TYPESAFE_API_KEY", None)
        path = self.typesafe_file(text="\n   \n")
        self.assertEqual(JR._typesafe_key(), (None, "empty_file"))
        path.unlink()
        self.assertEqual(JR._typesafe_key(), (None, "missing_file"))

    def test_zen_key_reads_the_opencode_zen_entry(self):
        os.environ.pop("OPENCODE_ZEN_API_KEY", None)
        keys = Path(os.environ["HOME"]) / ".pi" / "agent"
        keys.mkdir(parents=True)
        (keys / "keys.json").write_text(json.dumps({"opencode-zen": {"key": self.SENTINEL}}),
                                        encoding="utf-8")
        self.assertEqual(JR._opencode_key(), (self.SENTINEL, "file"))

    def test_zen_missing_file_is_a_reason_not_an_exception(self):
        os.environ.pop("OPENCODE_ZEN_API_KEY", None)
        os.environ["HOME"] = str(self.tmp / "nope")
        self.assertEqual(JR._opencode_key(), (None, "missing_file"))

    def test_zen_unparseable_file_is_a_reason_not_an_exception(self):
        os.environ.pop("OPENCODE_ZEN_API_KEY", None)
        keys = Path(os.environ["HOME"]) / ".pi" / "agent"
        keys.mkdir(parents=True)
        (keys / "keys.json").write_text("{not json", encoding="utf-8")
        self.assertEqual(JR._opencode_key(), (None, "missing_file"))

    def test_probe_labels_key_sources_and_never_prints_a_value(self):
        self.typesafe_file()
        os.environ.pop("TYPESAFE_API_KEY", None)
        os.environ["LAYA_API_KEY"] = self.SENTINEL
        os.environ["JEV_ALLOW_REMOTE"] = "1"
        code, text = self.run_probe_text()
        self.assertEqual(code, 0)
        self.assertNotIn(self.SENTINEL, text)
        report = json.loads(text)
        self.assertEqual(self.backend_entry(report, "laya")["key_source"], "env")
        self.assertEqual(self.backend_entry(report, "typesafe")["key_source"], "file")
        self.assertEqual(self.backend_entry(report, "opencode")["key_source"], "missing_file")

    def test_screen_never_prints_a_key_value(self):
        os.environ["LAYA_API_KEY"] = self.SENTINEL
        with JevStub() as stub:
            self.point_at(stub)
            self.enable("laya")
            code, out, err = self.run_main_text(THREE_ITEMS)
        self.assertEqual(code, 0)
        self.assertNotIn(self.SENTINEL, out + err)
        self.assertNotIn(self.SENTINEL, json.dumps(stub.bodies))  # not even on the wire here


class TestSeam(_ClientCase):
    """D-06: a backend is a row plus adapters, and nothing else in the client knows its name."""

    NAMES = ("laya", "typesafe", "opencode")

    def backend_literals(self, tree):
        """Every backend-name string literal outside an adapter and outside the table literal."""
        offenders = []
        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and any(
                    node.name.startswith(f"_{name}_") for name in self.NAMES):
                continue  # an adapter: naming its own backend is the whole point
            if isinstance(node, (ast.Assign, ast.AnnAssign)):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                names = []
                for target in targets:
                    if isinstance(target, ast.Name):
                        names.append(target.id)
                    elif isinstance(target, (ast.Tuple, ast.List)):
                        names.extend(elt.id for elt in target.elts
                                     if isinstance(elt, ast.Name))
                if "TABLE" in names:
                    continue  # the registry itself: naming a row there is the point
            for text in (n.value for n in ast.walk(node)
                         if isinstance(n, ast.Constant) and isinstance(n.value, str)):
                for name in self.NAMES:
                    if re.search(rf"(?:^|[^a-z]){name}(?:[^a-z]|$)", text):
                        offenders.append((name, node.lineno, text[:60]))
        return offenders

    def test_seam_ast_rule_accepts_the_real_client(self):
        # D-06. Docstrings are prose and are excluded: this is about a *branch* keyed on a name.
        tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
        code_only = [hit for hit in self.backend_literals(tree)
                     if not hit[2].startswith(("One stdlib", "None when", "The 2026"))]
        self.assertEqual(code_only, [])

    def test_seam_ast_rule_flags_a_name_branch(self):
        # non-vacuity: the synthetic branch the plan names must be caught, or the rule is decoration
        hits = self.backend_literals(ast.parse(
            "def select(n):\n    return n == \"laya\"\n"))
        self.assertEqual([hit[0] for hit in hits], ["laya"])

    def test_seam_probe_lists_a_stub_fourth_row(self):
        # D-06: adding a backend means adding a row, and `--probe` sees it with no other edit.
        with JevStub(model="laya-4") as stub:
            stub_row = self.stub_row("stub", stub)
            with mock.patch.object(JR, "TABLE", (*JR.TABLE, stub_row)):
                _code, report = self.run_probe()
        self.assertIn("stub", [entry["name"] for entry in report["backends"]])
        self.assertEqual(self.backend_entry(report, "stub")["usable"], True)
        self.assert_no_posts(stub)  # a probe asks no question of any row

    def test_seam_auto_order_selects_the_stub_row(self):
        # Laya is unreachable here (the case default is a closed port), so the new row is the
        # one auto selection picks, and the request lands on its own stub.
        with JevStub(model="laya-4") as stub:
            stub_row = self.stub_row("stub", stub)
            with mock.patch.object(JR, "TABLE", (*JR.TABLE, stub_row)):
                self.enable(None)
                result = self.run_screen(payload(noul_item("a")))
                _code, report = self.run_probe()
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["backend"], "stub")
        self.assertEqual(report["candidates"], ["stub"])
        self.assertEqual(len(stub.posts), 1)  # one question to the stub row, not to Laya

    def test_seam_missing_row_is_an_unknown_backend(self):
        # D-06 again, from the other side: removing a row degrades, it does not crash.
        rows = tuple(row for row in JR.TABLE if row["name"] != "opencode")
        with mock.patch.object(JR, "TABLE", rows):
            self.enable("opencode")
            result = self.run_screen(payload(noul_item("a")))
            _code, report = self.run_probe()
        self.assertEqual(result["reason"], "backend_unavailable:opencode:unknown_backend")
        self.assertEqual([entry["name"] for entry in report["backends"]],
                         ["laya", "typesafe"])

    def test_seam_table_without_the_row_stays_green(self):
        # the SPEC R2 acceptance: deleting the row leaves probe and screen green, no other edit
        rows = tuple(row for row in JR.TABLE if row["name"] != "opencode")
        with (JevStub() as laya, mock.patch.object(JR, "TABLE", rows)):
            self.point_at(laya)
            self.enable(None)
            result = self.run_screen(payload(noul_item("a")))
            code, report = self.run_probe()
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["backend"], "laya")
        self.assertEqual(code, 0)
        self.assertEqual(report["status"], "ok")
        self.assertEqual([entry["name"] for entry in report["backends"]], ["laya", "typesafe"])

    def test_seam_stub_row_does_not_leak_after_the_patch(self):
        # a patched TABLE is per-test: a later test must see exactly the shipped three rows
        self.assertEqual([row["name"] for row in JR.TABLE], list(self.NAMES))


LADDER_ITEMS = payload(noul_item("a1"), noul_item("a2"), noul_item("a3"))


class TestEscalation(_ClientCase):
    """The auto ladder (SPEC R3, D-11): local first, one consented remote batch, the rung
    trail back to the caller, and an explicit backend that never escalates."""

    def scenario(self, laya, typesafe, zen, record=True, items=LADDER_ITEMS,
                 allow=None):
        """Run LADDER_ITEMS through the full three-row ladder over the three stubs.

        The in-process stubs are the only remotes: the typesafe record (or the named
        `grant_note` override) is what opens the remote rung, exactly like uz's
        `consent grant` on a real machine.
        """
        self.point_at(laya)
        self.point_remote("typesafe", typesafe)
        self.point_remote("opencode", zen)
        os.environ["TYPESAFE_API_KEY"] = "typesafe-key"
        os.environ["OPENCODE_ZEN_API_KEY"] = "zen-key"
        if record:
            self.assertTrue(JR.consent_command("grant", "typesafe")["ok"])
        if allow is not None:
            os.environ["JEV_ALLOW_REMOTE"] = allow
        self.enable(None)
        return self.run_screen(items)

    def test_escalation_low_items(self):
        with (JevStub(tops={"a1": 0.5, "a3": 0.5}) as laya,
              JevStub(model="typesafe-1") as typesafe,
              JevStub(model="opencode-1") as zen):
            result = self.scenario(laya, typesafe, zen)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(len(laya.posts), 3)  # local first, one item per Laya request
        self.assertEqual(len(typesafe.posts), 1)  # the low items in one batch
        body = typesafe.bodies[0]
        self.assertEqual(list(body["questions"]), ["a1", "a3"])  # stdin order, original ids
        self.assertEqual([item["id"] for item in body["state"]["items"]], ["a1", "a3"])
        self.assertEqual(result["answers"]["a2"]["backend"], "laya")
        trail = result["trail"]["a1"]
        self.assertEqual([entry["backend"] for entry in trail], ["laya", "typesafe"])
        self.assertTrue(trail[0]["needs_fallback"])
        self.assertEqual(trail[0]["top"], 0.5)
        self.assertFalse(trail[1]["needs_fallback"])
        self.assertEqual(trail[1]["model"], "typesafe-1")
        self.assertEqual(zen.posts, [])

    def test_escalation_explicit_never_escalates(self):
        with (JevStub(tops={"a1": 0.5, "a3": 0.5}) as laya,
              JevStub(model="typesafe-1") as typesafe):
            self.point_at(laya)
            self.point_remote("typesafe", typesafe)
            self.assertTrue(JR.consent_command("grant", "typesafe")["ok"])
            self.enable("laya")  # explicit: one rung, ever
            result = self.run_screen(LADDER_ITEMS)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(typesafe.requests, [])
        self.assertTrue(result["answers"]["a1"]["needs_fallback"])
        self.assertTrue(result["answers"]["a3"]["needs_fallback"])
        self.assertFalse(result["answers"]["a2"]["needs_fallback"])
        self.assertEqual([entry["backend"] for entry in result["trail"]["a1"]], ["laya"])

    def test_escalation_threshold_is_confident(self):
        # SPEC R3 adjacency edge: `top >= threshold` is confident, not `<`.
        laya_threshold = JR.row_named("laya")["min_confidence"]
        with (JevStub(top=laya_threshold) as laya,  # exactly the laya row's min_confidence
              JevStub(model="typesafe-1") as typesafe,
              JevStub(model="opencode-1") as zen):
            result = self.scenario(laya, typesafe, zen)
        self.assertEqual(typesafe.posts, [])
        self.assertFalse(any(a["needs_fallback"] for a in result["answers"].values()))
        self.assertEqual(len(laya.posts), 3)

    def test_escalation_truncated_high_escalates(self):
        # Review cycle 2 / T-21.1-28: a truncated answer at 0.95 is not confident in auto.
        script = [{"answer": True, "truncated": True}, None]  # a1 truncated, a2 clean
        with (JevStub(top=0.95, script=script) as laya,
              JevStub(model="typesafe-1") as typesafe,
              JevStub(model="opencode-1") as zen):
            result = self.scenario(laya, typesafe, zen, items=payload(noul_item("a1"),
                                                                      noul_item("a2")))
        self.assertEqual(len(typesafe.posts), 1)
        self.assertEqual(list(typesafe.bodies[0]["questions"]), ["a1"])
        trail = result["trail"]["a1"]
        self.assertEqual([entry["backend"] for entry in trail], ["laya", "typesafe"])
        self.assertTrue(trail[0]["needs_fallback"])  # 0.95, but truncated: not final
        self.assertEqual(result["answers"]["a2"]["backend"], "laya")
        # and under JEV_BACKEND=laya the same answers make zero remote requests (RESEARCH
        # Pitfall 2): the explicit run keeps needs_fallback: true instead of escalating.
        with (JevStub(top=0.95, script=list(script)) as laya2,
              JevStub(model="typesafe-1") as typesafe2):
            self.point_at(laya2)
            self.point_remote("typesafe", typesafe2)
            self.enable("laya")
            explicit = self.run_screen(payload(noul_item("a1"), noul_item("a2")))
        self.assertEqual(typesafe2.requests, [])
        self.assertTrue(explicit["answers"]["a1"]["needs_fallback"])

    def test_escalation_none_low(self):
        # SPEC R3 empty edge: every Laya answer high means no remote request at all.
        with (JevStub(top=0.9) as laya,
              JevStub(model="typesafe-1") as typesafe,
              JevStub(model="opencode-1") as zen):
            result = self.scenario(laya, typesafe, zen)
        self.assertEqual(typesafe.posts, [])
        self.assertEqual(zen.posts, [])
        self.assertEqual(set(result["answers"]), {"a1", "a2", "a3"})

    def test_escalation_remote_low_is_final(self):
        # A low answer from a remote row is final with needs_fallback: true (D-11).
        with (JevStub(top=0.5) as laya,
              JevStub(model="typesafe-1", top=0.5) as typesafe,
              JevStub(model="opencode-1") as zen):
            self.point_at(laya)
            self.point_remote("typesafe", typesafe)
            self.point_remote("opencode", zen)
            os.environ["TYPESAFE_API_KEY"] = "typesafe-key"
            os.environ["OPENCODE_ZEN_API_KEY"] = "zen-key"
            os.environ["JEV_ALLOW_REMOTE"] = "typesafe,opencode"  # both remotes allowed
            self.enable(None)
            result = self.run_screen(LADDER_ITEMS)
        self.assertEqual(zen.posts, [])  # the opencode rung receives nothing
        self.assertEqual(len(typesafe.posts), 1)
        answer = result["answers"]["a1"]
        self.assertTrue(answer["needs_fallback"])
        self.assertEqual(answer["backend"], "typesafe")
        self.assertEqual([e["backend"] for e in result["trail"]["a1"]], ["laya", "typesafe"])

    def test_escalation_remote_error_falls_through(self):
        # Only escalate-errored items fall through to a later remote row.
        script = [{"status": 503, "headers": {"Retry-After": "0"}, "body": b"busy"}] * 3
        with (JevStub(top=0.5) as laya,
              JevStub(model="typesafe-1", script=script) as typesafe,
              JevStub(model="opencode-1") as zen):
            self.point_at(laya)
            self.point_remote("typesafe", typesafe)
            self.point_remote("opencode", zen)
            os.environ["TYPESAFE_API_KEY"] = "typesafe-key"
            os.environ["OPENCODE_ZEN_API_KEY"] = "zen-key"
            os.environ["JEV_ALLOW_REMOTE"] = "1"
            self.enable(None)
            result = self.run_screen(payload(noul_item("a1")))
        self.assertEqual(len(typesafe.posts), 3)  # its two retries spent, then escalate
        self.assertEqual(len(zen.posts), 1)  # one request: the row is non-batching, one item
        self.assertEqual(result["answers"]["a1"]["backend"], "opencode")
        self.assertEqual([e["backend"] for e in result["trail"]["a1"]],
                         ["laya", "typesafe", "opencode"])

    def test_escalation_caller_error_stays(self):
        # A caller_error is final: the item never goes to a remote row (D-13).
        script = [{"status": 422, "body": b"bad"}, None]
        with (JevStub(script=script) as laya,
              JevStub(model="typesafe-1") as typesafe,
              JevStub(model="opencode-1") as zen):
            result = self.scenario(laya, typesafe, zen)
        self.assertEqual(typesafe.posts, [])
        self.assertEqual(result["errors"]["a1"], "caller_error:http_422")
        self.assertEqual(result["answers"]["a2"]["backend"], "laya")
        trail = result["trail"]["a1"]
        self.assertEqual(trail[0]["backend"], "laya")
        self.assertEqual(trail[0]["error"], "caller_error:http_422")

    def test_escalation_laya_503_exhausted_falls_through(self):
        # SPEC R1 / D-13 / the 2026-02 todo: a Laya 503 whose two retries are spent sends
        # that item to the consented remote batch, after its error rung in the trail.
        script = [None] + [{"status": 503, "headers": {"Retry-After": "0"},
                             "body": b"busy"}] * 3
        with (JevStub(script=script) as laya,
              JevStub(model="typesafe-1") as typesafe,
              JevStub(model="opencode-1") as zen):
            result = self.scenario(laya, typesafe, zen,
                                   items=payload(noul_item("a1"), noul_item("a2")))
        self.assertEqual(len(laya.posts), 4)  # a1 once; a2 the first try plus two retries
        self.assertEqual(len(typesafe.posts), 1)
        self.assertEqual(list(typesafe.bodies[0]["questions"]), ["a2"])
        trail = result["trail"]["a2"]
        self.assertEqual([entry["backend"] for entry in trail], ["laya", "typesafe"])
        self.assertEqual(trail[0]["error"], "http_503")
        self.assertEqual(result["answers"]["a2"]["backend"], "typesafe")

    def test_escalation_skip_local(self):
        # D-11: --skip-local skips every non-remote row, so a second opinion makes zero
        # Laya requests — not even the health probe.
        with (JevStub() as laya,
              JevStub(model="typesafe-1") as typesafe,
              JevStub(model="opencode-1") as zen):
            self.point_at(laya)
            self.point_remote("typesafe", typesafe)
            self.point_remote("opencode", zen)
            os.environ["TYPESAFE_API_KEY"] = "typesafe-key"
            self.assertTrue(JR.consent_command("grant", "typesafe")["ok"])
            self.enable(None)
            _code, result = self.run_cli_screen(LADDER_ITEMS, ["--skip-local"])
        self.assertEqual(laya.requests, [])
        self.assertEqual(len(typesafe.posts), 1)
        self.assertEqual(list(typesafe.bodies[0]["questions"]), ["a1", "a2", "a3"])
        self.assertEqual(result["status"], "ok")

    def test_escalation_slow_local_backstop(self):
        # SPEC R3 concurrency edge (backstop): escalation starts only after every local
        # answer is in — the remote request arrives after the last Laya response.
        with (JevStub(top=0.5, delay=0.2) as laya,
              JevStub(model="typesafe-1") as typesafe,
              JevStub(model="opencode-1") as zen):
            result = self.scenario(laya, typesafe, zen)
        self.assertEqual(len(typesafe.posts), 1)
        self.assertGreater(typesafe.posts[0]["at"], laya.posts[-1]["at"])
        self.assertEqual(result["answers"]["a1"]["backend"], "typesafe")


class TestConsent(_ClientCase):
    """The persisted record (D-06, D-07, SPEC R6): `${XDG_CONFIG_HOME:-~/.config}/ai-kit/jev-
    consent.json`, `{backend: {host, granted}}`, atomic, and the gate it feeds."""

    def remotes(self, laya_top=0.5):
        """The stub trio open on the stack for the rest of the test: the caller owns them."""
        return (JevStub(top=laya_top), JevStub(model="typesafe-1"),
                JevStub(model="opencode-1"))

    def wire(self, laya, typesafe, zen, keys="typesafe"):
        """The stub trio wired as the three rows: only the named remotes have a key.

        `keys="typesafe"` keeps opencode unkeyed, so an unconsented result can name exactly
        the row a consent decision is about; `keys="both"` tempts the fallthrough."""
        self.point_at(laya)
        self.point_remote("typesafe", typesafe)
        self.point_remote("opencode", zen)
        os.environ["TYPESAFE_API_KEY"] = "typesafe-key"
        if keys == "both":
            os.environ["OPENCODE_ZEN_API_KEY"] = "zen-key"
        self.enable(None)

    def run_cli(self, argv):
        """main(argv) with stdout captured: (exit code, the parsed JSON it printed)."""
        return self._run(JR.main, argv)

    def _run(self, call, argv):
        out = io.StringIO()
        with mock.patch.object(sys, "stdout", out):
            code = call(argv)
        return code, json.loads(out.getvalue())

    def test_consent_no_record_zero_remote(self):
        # SPEC R6 acceptance: no record means zero remote requests — and an ok result that
        # names the rows a consent decision is about.
        laya, typesafe, zen = self.remotes()
        with laya, typesafe, zen:
            self.wire(laya, typesafe, zen)
            result = self.run_screen(payload(noul_item("a1")))
        self.assertEqual(typesafe.requests, [])
        self.assertEqual(zen.requests, [])
        self.assertEqual(result["status"], "ok")
        self.assertTrue(result["answers"]["a1"]["needs_fallback"])
        self.assertEqual(result["remote_available"], ["typesafe"])

    def test_consent_record_for_another_host_is_no_consent(self):
        # SPEC R6 adjacency: the endpoint moved to host B; the record says host A. Zero.
        laya, typesafe, zen = self.remotes()
        with laya, typesafe, zen:
            self.wire(laya, typesafe, zen)
            JR.write_consent({"typesafe": {"host": "10.9.9.9", "granted": "2026-01-01"}})
            result = self.run_screen(payload(noul_item("a1")))
        self.assertEqual(typesafe.requests, [])
        self.assertEqual(result["remote_available"], ["typesafe"])

    def test_consent_matching_record_opens_the_batch(self):
        laya, typesafe, zen = self.remotes()
        with laya, typesafe, zen:
            self.wire(laya, typesafe, zen)
            self.assertTrue(JR.consent_command("grant", "typesafe")["ok"])
            result = self.run_screen(payload(noul_item("a1")))
        self.assertEqual(len(typesafe.posts), 1)
        today = datetime.date.today().isoformat()
        self.assertEqual(result["consent_used"], [{"backend": "typesafe", "granted": today}])
        self.assertNotIn("remote_available", result)

    def test_consent_revoke_stops_the_next_run(self):
        # SPEC R6 acceptance: after `consent revoke` the next run makes zero remote requests.
        laya, typesafe, zen = self.remotes()
        with laya, typesafe, zen:
            self.wire(laya, typesafe, zen)
            JR.consent_command("grant", "typesafe")
            _code, out = self.run_cli(["consent", "revoke", "typesafe"])
            self.assertTrue(out["ok"])
            self.assertIsNone(out["consent"])
            result = self.run_screen(payload(noul_item("a1")))
        self.assertEqual(typesafe.requests, [])
        self.assertEqual(result["remote_available"], ["typesafe"])

    def test_consent_empty_or_unreadable_file_is_no_consent(self):
        # SPEC R6 empty edge.
        for text in ("", "{not json"):
            with self.subTest(text=text):
                Path(JR.consent_path()).parent.mkdir(parents=True, exist_ok=True)
                Path(JR.consent_path()).write_text(text, encoding="utf-8")
                laya, typesafe, zen = self.remotes()
                with laya, typesafe, zen:
                    self.wire(laya, typesafe, zen)
                    result = self.run_screen(payload(noul_item("a1")))
                self.assertEqual(typesafe.requests, [], text)
                self.assertEqual(result["remote_available"], ["typesafe"], text)

    def test_consent_grant_non_remote_row_is_not_remote(self):
        code, out = self.run_cli(["consent", "grant", "laya"])
        self.assertEqual(code, 0)
        self.assertEqual(out, {"ok": False, "reason": "not_remote"})

    def test_consent_grant_unknown_backend(self):
        _code, out = self.run_cli(["consent", "grant", "zen"])
        self.assertEqual(out, {"ok": False, "reason": "unknown_backend"})

    def test_consent_typesafe_only_never_reaches_opencode(self):
        # D-07 / T-21.1-13: a record for one remote never enables another on fallthrough.
        script = [{"status": 503, "headers": {"Retry-After": "0"}, "body": b"busy"}] * 3
        laya = JevStub(top=0.5)
        typesafe = JevStub(model="typesafe-1", script=script)
        zen = JevStub(model="opencode-1")
        with laya, typesafe, zen:
            self.wire(laya, typesafe, zen, keys="both")
            JR.consent_command("grant", "typesafe")
            result = self.run_screen(payload(noul_item("a1")))
        self.assertEqual(zen.requests, [])  # not even the reachability probe
        self.assertEqual(len(typesafe.posts), 3)
        self.assertEqual(result["answers"]["a1"]["backend"], "laya")  # the low local answer
        self.assertTrue(result["answers"]["a1"]["needs_fallback"])
        self.assertEqual(result["trail"]["a1"][-1]["error"], "http_503")

    def test_consent_show_prints_the_record(self):
        laya, typesafe, zen = self.remotes()
        with laya, typesafe, zen:
            self.point_remote("typesafe", typesafe)
            _code, _granted = self.run_cli(["consent", "grant", "typesafe"])
            code, out = self.run_cli(["consent", "show", "typesafe"])
        self.assertEqual(code, 0)
        self.assertEqual(out["backend"], "typesafe")
        self.assertEqual(out["host"], "127.0.0.1")
        self.assertEqual(out["consent"], datetime.date.today().isoformat())
        self.assertTrue(out["file"].endswith(os.path.join("ai-kit", "jev-consent.json")))

    def test_consent_grant_announces_host_and_unverified_retention(self):
        # RESEARCH Answer 11: retention terms unverified — the note must not promise more.
        laya, typesafe, zen = self.remotes()
        with laya, typesafe, zen:
            self.point_remote("typesafe", typesafe)
            _code, out = self.run_cli(["consent", "grant", "typesafe"])
        self.assertIn("127.0.0.1", out["note"])
        self.assertIn("retention terms unverified", out["note"])
        self.assertIn("consent revoke typesafe", out["note"])
        self.assertNotIn("never stored", json.dumps(out))

    def test_consent_probe_backends_carry_the_date(self):
        laya, typesafe, zen = self.remotes()
        with laya, typesafe, zen:
            self.point_remote("typesafe", typesafe)
            JR.consent_command("grant", "typesafe")
            _code, report = self.run_probe()
        entries = {e["name"]: e for e in report["backends"]}
        self.assertEqual(entries["typesafe"]["consent"], datetime.date.today().isoformat())
        self.assertIsNone(entries["opencode"]["consent"])
        self.assertNotIn("consent", entries["laya"])  # a local row has no consent to show

    def test_consent_record_shape_and_mode(self):
        laya, typesafe, zen = self.remotes()
        with laya, typesafe, zen:
            self.point_remote("typesafe", typesafe)
            JR.consent_command("grant", "typesafe")
            raw = json.loads(Path(JR.consent_path()).read_text(encoding="utf-8"))
            mode = os.stat(JR.consent_path()).st_mode & 0o777
        self.assertEqual(set(raw), {"typesafe"})
        self.assertEqual(set(raw["typesafe"]), {"host", "granted"})
        self.assertEqual(raw["typesafe"]["host"], "127.0.0.1")
        self.assertEqual(mode, 0o600)  # mkstemp's mode carried over by os.replace


class TestAnswerLog(_ClientCase):
    """D-19, SPEC R7: one line per dispatched item in `$XDG_STATE_HOME/ai-kit` — and nothing
    the caller did not send as its own question: no context, no state, no criteria text, no
    key value, no image data."""

    LOG_FIELDS = {"ts", "caller", "id", "type", "instructions", "backend", "model",
                  "choice", "top", "needs_fallback", "request_sha256"}

    def log_lines(self):
        path = JR.answer_log_path()
        if not os.path.exists(path):
            return []
        with open(path, encoding="utf-8") as handle:
            return [json.loads(line) for line in handle if line.strip()]

    def reset_state(self, tag):
        """A fresh state root per subtest: each case counts lines in its own file."""
        os.environ["XDG_STATE_HOME"] = str(self.tmp / f"state-{tag}")

    def test_answer_log_three_items(self):
        self.enable("laya")
        with JevStub(top=0.9) as stub:
            self.point_at(stub)
            result = self.run_screen(payload(noul_item("a"), choice_item("b"),
                                             score_item("c")))
        self.assertEqual(result["status"], "ok")
        lines = self.log_lines()
        self.assertEqual([line["id"] for line in lines], ["a", "b", "c"])
        self.assertEqual(set(lines[0]), self.LOG_FIELDS)
        self.assertEqual(lines[0]["caller"], "direct")
        self.assertEqual(lines[0]["choice"], "yes")  # a noul item's pick is yes or no
        self.assertEqual(lines[0]["backend"], "laya")
        self.assertEqual(lines[1]["choice"], "bug")
        self.assertEqual(set(lines[2]), self.LOG_FIELDS - {"choice"} | {"score"})
        os.environ["JEV_CALLER"] = "ai-kit-gsd-spec-discuss"
        with JevStub(top=0.9) as stub:
            self.point_at(stub)
            self.run_screen(payload(noul_item("a")))
        self.assertEqual(self.log_lines()[-1]["caller"], "ai-kit-gsd-spec-discuss")

    def test_answer_log_unwritable(self):
        # SPEC R7: a log failure never changes the answer or the exit code.
        self.enable("laya")
        with JevStub() as stub:
            self.point_at(stub)
            baseline = self.run_screen(payload(noul_item("a")))
        self.assertEqual(baseline["status"], "ok")
        for tag, point in (("file", self.tmp / "plain-file"), ("ro", self.tmp / "ro-state")):
            with self.subTest(state=tag):
                if tag == "file":
                    point.write_text("a regular file where a directory belongs")
                else:
                    point.mkdir(mode=0o500)
                    self.addCleanup(point.chmod, 0o700)  # so cleanup can remove the tree
                os.environ["XDG_STATE_HOME"] = str(point)
                with JevStub() as stub:
                    self.point_at(stub)
                    result = self.run_screen(payload(noul_item("a")))
                self.assertEqual(result, baseline)
                self.assertFalse((point / "ai-kit").exists())

    def test_answer_log_no_secrets(self):
        # D-19: a fixed field list, never a filtered dump — but prove the sentinels stay out.
        os.environ["TYPESAFE_API_KEY"] = "TYPESAFE-KEY-SENTINEL"
        self.enable("laya")
        item = choice_item("b", context="CONTEXT-SENTINEL")
        item["criteria"] = {"bug": "CRITERIA-SENTINEL", "style": "s", "other": "o"}
        with JevStub() as stub:
            self.point_at(stub)
            self.run_screen(payload(item))
        blob = Path(JR.answer_log_path()).read_bytes()
        self.assertNotIn(b"SENTINEL", blob)

    def test_answer_log_edges(self):
        self.enable("laya")
        with self.subTest(case="long instructions"):
            self.reset_state("long")
            item = noul_item("a")
            item["instructions"] = "i" * 1500
            with JevStub() as stub:
                self.point_at(stub)
                self.run_screen(payload(item))
            self.assertEqual(len(self.log_lines()[0]["instructions"]), 1500)
        with self.subTest(case="errored item"):
            self.reset_state("errored")
            with JevStub(script=[{"status": 422, "body": b"nope"}]) as stub:
                self.point_at(stub)
                self.run_screen(payload(noul_item("a")))
            lines = self.log_lines()
            self.assertEqual(len(lines), 1)
            self.assertIn("error", lines[0])
            for field in ("choice", "score", "model", "top"):
                self.assertNotIn(field, lines[0])
        with self.subTest(case="runs that dispatch nothing"):
            def disabled_run():
                os.environ.pop("GSD_PATH_JEV", None)  # the kill switch: screen returns early
                return self.run_screen(THREE_ITEMS)

            def invalid_run():
                self.enable("laya")
                return self.run_screen(None, stdin_text="not json")

            for case, run in (("disabled", disabled_run), ("invalid", invalid_run),
                              ("consent", self.screen_without_consent)):
                with self.subTest(run=case):
                    self.reset_state(case)
                    result = run()
                    self.assertEqual(self.log_lines(), [])
                    self.assertFalse(os.path.exists(JR.answer_log_path()))
                    self.assertNotEqual(result["status"], "ok")
        with self.subTest(case="newline stays one line"):
            self.reset_state("newline")
            self.enable("laya")
            item = noul_item("a")
            item["instructions"] = "two\nlines"
            with JevStub() as stub:
                self.point_at(stub)
                self.run_screen(payload(item))
            with open(JR.answer_log_path(), encoding="utf-8") as handle:
                self.assertEqual(len([line for line in handle if line.strip()]), 1)
            self.assertEqual(self.log_lines()[0]["instructions"], "two\nlines")
        with self.subTest(case="top keeps its decimals"):
            self.reset_state("top")
            self.enable("laya")
            with JevStub(top=0.8333) as stub:
                self.point_at(stub)
                self.run_screen(payload(noul_item("a")))
            self.assertEqual(self.log_lines()[0]["top"], 0.8333)

    def screen_without_consent(self):
        """Auto mode with a keyed-but-unconsented remote and no Laya: consent_required."""
        os.environ["TYPESAFE_API_KEY"] = "typesafe-key"
        os.environ.pop("JEV_BACKEND", None)
        self.enable(None)
        return self.run_screen(payload(noul_item("a")))  # JEV_LAYA_URL: the closed default

    def test_answer_log_mode_and_symlink(self):
        self.enable("laya")
        with JevStub() as stub:
            self.point_at(stub)
            self.run_screen(payload(noul_item("a")))
        self.assertEqual(os.stat(JR.answer_log_path()).st_mode & 0o777, 0o600)
        target = self.tmp / "elsewhere.jsonl"
        target.write_text("keep out\n", encoding="utf-8")
        os.unlink(JR.answer_log_path())
        os.symlink(target, JR.answer_log_path())
        with JevStub() as stub:
            self.point_at(stub)
            result = self.run_screen(payload(noul_item("a")))
        self.assertEqual(result["status"], "ok")  # O_NOFOLLOW refused the symlink, quietly
        self.assertEqual(target.read_text(encoding="utf-8"), "keep out\n")

    # Run by `-c`: no import, no cache, load the module by path and append 200 lines.
    WORKER = ("import importlib.util, json, sys\n"
              "spec = importlib.util.spec_from_file_location('jr', sys.argv[1])\n"
              "module = importlib.util.module_from_spec(spec)\n"
              "spec.loader.exec_module(module)\n"
              "lines = [json.dumps({'worker': sys.argv[2], 'i': i}) + '\\n'\n"
              "         for i in range(200)]\n"
              "module.append_answer_log(lines)\n")

    def test_answer_log_two_processes_backstop(self):
        # T-21.1-05's premise, measured rather than trusted: concurrent O_APPEND writers.
        workers = [subprocess.Popen([sys.executable, "-B", "-c", self.WORKER, str(SCRIPT), tag],
                                    env=dict(os.environ), stdout=subprocess.DEVNULL,
                                    stderr=subprocess.DEVNULL)
                   for tag in ("w1", "w2")]
        for worker in workers:
            self.assertEqual(worker.wait(timeout=120), 0)
        lines = self.log_lines()
        self.assertEqual(len(lines), 400)
        self.assertEqual(sorted({line["worker"] for line in lines}), ["w1", "w2"])

    def test_answer_log_short_write(self):
        # A short write stops this run's logging: no second write that could tear another
        # process's line, and no exception the caller would have to forgive (T-21.1-05).
        calls = []

        def half(_fd, data):
            calls.append(len(data))
            return len(data) // 2

        with mock.patch.object(os, "write", half):
            JR.append_answer_log(["first line\n", "second line\n"])
        self.assertEqual(len(calls), 1)
        self.assertEqual(Path(JR.answer_log_path()).read_text(encoding="utf-8"), "")


class TestDeadline(_ClientCase):
    """D-12, SPEC R7: GSD_PATH_JEV_DEADLINE_SECONDS bounds the whole run — probes, requests,
    waits and body reads alike — and a server that trickles bytes at any layer cannot push
    the run past its own instant. Partial answers come back; the deadline never escalates."""

    def wire_typesafe(self, laya, typesafe):
        """Auto mode, Laya on `laya`, a granted typesafe record over `typesafe`'s origin."""
        self.point_at(laya)
        self.point_remote("typesafe", typesafe)
        os.environ["TYPESAFE_API_KEY"] = "typesafe-key"
        JR.consent_command("grant", "typesafe")
        self.enable(None)
        os.environ["GSD_PATH_JEV_DEADLINE_SECONDS"] = "0.5"

    def test_deadline_partial(self):
        self.enable("laya")
        os.environ["GSD_PATH_JEV_DEADLINE_SECONDS"] = "0.5"
        with JevStub(delay=0.3) as stub:
            self.point_at(stub)
            started = time.monotonic()
            result = self.run_screen(payload(noul_item("a1"), noul_item("a2"), noul_item("a3")))
            elapsed = time.monotonic() - started
        self.assertEqual(result["status"], "ok")
        self.assertEqual(list(result["answers"]), ["a1"])  # the one request that finished
        self.assertEqual(result["errors"], {"a2": "deadline", "a3": "deadline"})
        self.assertNotIn("network_error", result["errors"].values())
        self.assertEqual(len(stub.posts), 2)  # the third item never got a request
        self.assertLess(elapsed, 1.5)

    def test_deadline_never_escalates(self):
        laya, typesafe = JevStub(delay=0.3), JevStub(model="typesafe-1")
        with laya, typesafe:
            self.wire_typesafe(laya, typesafe)
            started = time.monotonic()
            result = self.run_screen(payload(noul_item("a1"), noul_item("a2"), noul_item("a3")))
            elapsed = time.monotonic() - started
        self.assertEqual(result["status"], "ok")
        self.assertEqual(list(result["answers"]), ["a1"])
        self.assertEqual(result["errors"], {"a2": "deadline", "a3": "deadline"})
        self.assertEqual(typesafe.posts, [])  # a deadline is final: it never climbs a rung
        self.assertLess(elapsed, 1.5)

    def run_drip(self, drip):
        """The trickle setup shared by the three deadline-at-any-layer cases: item one is
        answered normally, item two gets `drip`, and the run must stop at the deadline."""
        laya = JevStub(script=[None, drip])
        typesafe = JevStub(model="typesafe-1")
        with laya, typesafe:
            self.wire_typesafe(laya, typesafe)
            os.environ["GSD_PATH_JEV_DEADLINE_SECONDS"] = "0.8"
            started = time.monotonic()
            result = self.run_screen(payload(noul_item("a1"), noul_item("a2")))
            elapsed = time.monotonic() - started
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["answers"]["a1"]["backend"], "laya")
        self.assertEqual(result["errors"], {"a2": "deadline"})
        self.assertEqual(typesafe.posts, [])
        self.assertLess(elapsed, 2.0)

    def test_deadline_slow_drip(self):
        # A body of 4000 bytes dribbled at one byte per 0.05 s: every individual read stays
        # under the socket timeout — only the deadline (and its watchdog) can stop this.
        self.run_drip({"drip": 0.05, "drip_part": "body", "status": 200,
                       "headers": {"Content-Type": "application/json",
                                   "Content-Length": "4000"},
                       "body": b"p" * 4000})

    def test_deadline_trickling_headers(self):
        # urllib reads the status line and headers inside its own readline calls, below the
        # read1 loop: a >=100-byte header block at one byte per 0.05 s must still stop here.
        self.run_drip({"drip": 0.05, "drip_part": "headers", "status": 200,
                       "headers": {"Content-Type": "application/json",
                                   "Content-Length": "4000", "X-Pad": "p" * 90},
                       "body": b"p" * 4000})

    def test_deadline_chunk_framing(self):
        # Chunk framing is the third layer: the chunk-size line padded with leading zeros
        # trickles forever inside http.client's own read.
        self.run_drip({"drip": 0.05, "drip_part": "chunked", "status": 200,
                       "headers": {"Transfer-Encoding": "chunked"}})

    def test_deadline_invalid(self):
        for value in ("abc", "0", "-1", "nan", "inf"):
            with self.subTest(value=value):
                self.enable("laya")
                os.environ["GSD_PATH_JEV_DEADLINE_SECONDS"] = value
                with JevStub() as stub:
                    self.point_at(stub)
                    result = self.run_screen(THREE_ITEMS)
                self.assertEqual(result, {"status": "unavailable", "reason": "invalid_timeout"})
                self.assertEqual(stub.requests, [])


class TestMatrix(_ClientCase):
    """D-21, D-24, D-25, SPEC R10: capability cells per row, the per-item feature filter
    that refuses unbuilt shapes before any socket, and `score` end to end."""

    def image_item(self, identifier, count=1):
        item = {"id": identifier, "type": "noul", "instructions": "Is it a cat?",
                "context": "a photo"}
        item["images"] = [f"scratch/p{n}.png" for n in range(count)]
        return item

    def box_item(self, identifier):
        return {"id": identifier, "type": "box", "instructions": "Where is the button?",
                "context": "a screenshot"}

    def levels_item(self, identifier, count):
        item = score_item(identifier)
        item["criteria"] = [f"L{index}" for index in range(count)]
        return item

    def wire_typesafe(self, typesafe):
        os.environ["JEV_ALLOW_REMOTE"] = "1"
        os.environ["TYPESAFE_API_KEY"] = "typesafe-key"
        self.point_remote("typesafe", typesafe)

    def test_matrix_explicit_documented_accepted(self):
        # A score cell may be only `documented` for typesafe, but documented is enough (D-24).
        self.enable("typesafe")
        with JevStub(model="typesafe-1") as typesafe:
            self.wire_typesafe(typesafe)
            result = self.run_screen(payload(score_item("s")))
        self.assertEqual(len(typesafe.posts), 1)
        self.assertEqual(result["answers"]["s"]["backend"], "typesafe")

    def test_matrix_explicit_unverified_rejected(self):
        # The mirror case: `unverified` is never enough — an equal-shaped item is refused.
        self.enable("opencode")
        os.environ["JEV_ALLOW_REMOTE"] = "1"
        os.environ["OPENCODE_ZEN_API_KEY"] = "zen-key"
        with JevStub(model="opencode-1") as zen:
            self.point_remote("opencode", zen)
            result = self.run_screen(payload(score_item("s")))
        self.assertEqual(result["status"], "unavailable")
        self.assertEqual(result["reason"], "unsupported_feature")
        self.assertEqual(result["item"], "s")
        self.assertEqual(zen.requests, [])

    def test_matrix_image_item(self):
        # D-21: no builder exists for image or box — the refusal is the same on every row.
        laya, typesafe = JevStub(), JevStub(model="typesafe-1")
        with laya, typesafe:
            for backend in ("laya", "typesafe"):
                for case, item in (("image", self.image_item("img")),
                                   ("box", self.box_item("bx"))):
                    with self.subTest(backend=backend, item=case):
                        self.enable(backend)
                        if backend == "laya":
                            self.point_at(laya)
                            stub = laya
                        else:
                            self.wire_typesafe(typesafe)
                            stub = typesafe
                        result = self.run_screen(payload(item))
                        self.assertEqual(result["reason"], "unsupported_feature")
                        self.assertEqual(result["item"], item["id"])
                        self.assertEqual(stub.requests, [])

    def test_matrix_auto_skips_rung(self):
        # D-25: the score item's rung list drops opencode (cell `unverified`), so the
        # typesafe error is where the item ends — never a detour through that rung.
        typesafe = JevStub(model="typesafe-1", script=[{"status": 503, "body": b"busy"}] * 3)
        zen = JevStub(model="opencode-1")
        with typesafe, zen:
            self.point_remote("typesafe", typesafe)
            self.point_remote("opencode", zen)
            self.enable_remote(None)  # auto; Laya stays on the closed default port
            result = self.run_screen(payload(score_item("s")))
        self.assertEqual(result["status"], "unavailable")
        self.assertEqual(result["errors"], {"s": "http_503"})
        self.assertEqual(zen.posts, [])

    def test_matrix_order(self):
        # The feature check runs before validation and before any request: a mixed run of
        # one image item and one choice item makes zero requests, not even a probe.
        self.enable("laya")
        with JevStub() as stub:
            self.point_at(stub)
            result = self.run_screen(payload(self.image_item("img"), choice_item("c")))
        self.assertEqual(result["reason"], "unsupported_feature")
        self.assertEqual(result["item"], "img")
        self.assertEqual(stub.requests, [])

    def test_matrix_score_levels(self):
        # The 2..10 level bound stays in `_build_score`, before any request (D-15).
        self.enable("laya")
        for count, accepted in ((1, False), (11, False), (2, True), (10, True)):
            with self.subTest(levels=count):
                with JevStub() as stub:
                    self.point_at(stub)
                    result = self.run_screen(payload(self.levels_item("s", count)))
                if accepted:
                    self.assertEqual(len(stub.posts), 1)
                    self.assertEqual(result["status"], "ok")
                else:
                    self.assertEqual(result["status"], "unavailable")
                    self.assertEqual(result["reason"], "invalid_input")
                    self.assertEqual(result["item"], "s")
                    self.assertEqual(stub.requests, [])

    def test_matrix_score_answer(self):
        # A score answer keeps the raw legend and probabilities and gains the pick (D-25).
        self.enable("laya")
        with JevStub(top=0.9) as stub:
            self.point_at(stub)
            result = self.run_screen(payload(score_item("s")))
        answer = result["answers"]["s"]
        self.assertEqual(answer["legend"], {"0": "low", "1": "mid", "2": "high"})
        self.assertEqual(answer["level"], "2")
        self.assertEqual(answer["top"], 0.9)
        self.assertEqual(len(answer["probabilities"]), 3)

    def test_matrix_batch_backstop(self):
        # The batch shape the docs promise: one consented remote request over one state
        # holds every question; the local row still asks one question per request.
        laya = JevStub(top=0.5)  # low on Laya: the items escalate to the remote batch
        typesafe = JevStub(model="typesafe-1")
        zen = JevStub(model="opencode-1")
        with laya, typesafe, zen:
            self.point_at(laya)
            self.point_remote("typesafe", typesafe)
            self.point_remote("opencode", zen)
            self.enable_remote(None)
            result = self.run_screen(payload(noul_item("a"), noul_item("b"), noul_item("c")))
        self.assertEqual(result["status"], "ok")
        self.assertEqual([sorted(body["questions"]) for body in laya.bodies],
                         [["a"], ["b"], ["c"]])
        self.assertEqual(len(typesafe.posts), 1)
        self.assertEqual(sorted(typesafe.bodies[0]["questions"]), ["a", "b", "c"])
        self.assertEqual(zen.posts, [])

    def test_matrix_cells_complete(self):
        # The matrix data the docs will show lives in the rows: every feature has a cell of
        # (status, source, date), and no cell is an unlabelled guess.
        for row in JR.rows_in_order():
            with self.subTest(row=row["name"]):
                self.assertEqual(set(row["cells"]), set(JR.CELL_FEATURES))
                for status, source, date in row["cells"].values():
                    self.assertIn(status, JR.CELL_STATUSES)
                    self.assertTrue(source.strip())
                    self.assertRegex(date, r"^\d{4}-\d{2}-\d{2}$")


def _eval():
    """The eval script, loaded by path."""
    path = SCRIPT.parent / "eval_cases.py"
    spec = importlib.util.spec_from_file_location("eval_cases_under_test", str(path))
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestDocs(unittest.TestCase):
    """Doc tests (tag `doc`): the shipped documents cannot drift from the client table."""

    SKILL_MD = (Path(__file__).resolve().parents[1] / "skills" / "jev-fast-decision"
                / "SKILL.md")
    REFERENCE_MD = (Path(__file__).resolve().parents[1] / "skills" / "jev-fast-decision"
                    / "reference.md")

    @classmethod
    def setUpClass(cls):
        cls.skill_text = cls.SKILL_MD.read_text(encoding="utf-8")
        cls.reference_text = cls.REFERENCE_MD.read_text(encoding="utf-8")
        lines = cls.skill_text.splitlines()
        closes = [i for i, line in enumerate(lines) if line == "---"]
        cls.frontmatter = "\n".join(lines[1:closes[1]])
        cls.body = "\n".join(lines[closes[1] + 1:])

    def test_doc_frontmatter(self):
        name = re.search(r"^name:\s*(\S+)", self.frontmatter, re.M)
        description = re.search(r'^description:\s*"(.*)"\s*$', self.frontmatter, re.M)
        assert name is not None and description is not None
        self.assertEqual(name.group(1), "jev-fast-decision")
        text = description.group(1)
        self.assertTrue(text.startswith("Use when"))
        self.assertLess(len(text), 500)
        for needle in ("Laya", "TypeSafe", "OpenCode Zen", "needs_fallback", "consent"):
            self.assertIn(needle, text)

    def test_doc_body_words(self):
        # the plan's awk rule: words after the closing frontmatter `---`
        self.assertLess(len(self.body.split()), 500)

    def test_doc_required_reading(self):
        for url in ("https://typesafe.ai/blog/jev-1-14", "https://docs.typesafe.ai/primitives",
                    "https://docs.typesafe.ai/images", "https://docs.typesafe.ai/confidence"):
            self.assertIn(url, self.skill_text)

    def test_doc_recipes(self):
        self.assertIn("--probe", self.body)
        self.assertIn("backends/<selected>.md", self.body)
        self.assertRegex(self.body, r"needs_fallback[\s\S]*you decide that item "
                                    r"with your own reasoning")
        self.assertRegex(self.body, r"consent_required_for_remote[\s\S]*ask the user")

    def test_doc_matrix_matches_table(self):
        # Every matrix cell is non-empty, one of the four statuses, carries a source and an
        # ISO date, and equals the status of that row's `cells` entry in the client table.
        section = self.reference_text.split("## Capability matrix", 1)[1].split("\n## ", 1)[0]
        rows = [line for line in section.splitlines() if line.startswith("| ")]
        header = [cell.strip() for cell in rows[0].strip("|").split("|")]
        self.assertEqual(header[0], "Feature")
        columns = header[1:]
        self.assertEqual(sorted(columns), sorted(row["name"] for row in JR.TABLE))
        parsed = {}
        for line in rows[2:]:
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            feature = cells[0].strip()
            parsed[feature] = dict(zip(columns, cells[1:], strict=True))
        features = {"choice": JR.CHOICE, "noul": JR.NOUL, "score": JR.SCORE, "box": JR.BOX,
                    "image": JR.IMAGE, "images_compared": JR.IMAGES_COMPARED,
                    "long_context": JR.LONG_CONTEXT, "batch": JR.BATCH}
        self.assertEqual(sorted(parsed), sorted(features))
        for row in JR.TABLE:
            for doc_name, table_key in features.items():
                cell = parsed[doc_name][row["name"]]
                self.assertTrue(cell.strip(), f"empty cell: {row['name']}/{doc_name}")
                status, rest = cell.split(" (", 1)
                source, date = rest.rstrip(")").rsplit(", ", 1)
                self.assertIn(status, JR.CELL_STATUSES)
                self.assertTrue(source.strip())
                self.assertRegex(date, r"^\d{4}-\d{2}-\d{2}$")
                self.assertEqual(status, row["cells"][table_key][0])

    def test_doc_backend_files(self):
        for row in JR.TABLE:
            path = self.SKILL_MD.parent / "backends" / f"{row['name']}.md"
            self.assertTrue(path.is_file(), path)

    def test_doc_hosts(self):
        self.assertIn("documented gap", self.reference_text)
        self.assertIn("learn.chatgpt.com/docs/build-skills", self.reference_text)
        self.assertIn("cursor.com/docs/context/skills", self.reference_text)
        self.assertIn("~/.claude/skills", self.reference_text)
        self.assertIn("not live-verified", self.reference_text)


TABLE_SOURCE = '''TABLE = (
    {
        "name": "laya",
        "min_confidence": 0.7,
    },
    {
        "name": "typesafe",
        "min_confidence": 0.8,
    },
)
'''

TABLE_SOURCE_NO_LAYA = TABLE_SOURCE.replace('        "min_confidence": 0.7,\n', '')
TABLE_SOURCE_DOUBLE = TABLE_SOURCE.replace('        "min_confidence": 0.7,\n',
                                           '        "min_confidence": 0.7,\n'
                                           '        "min_confidence": 0.6,\n')


class TestEval(_ClientCase):
    """The 32-case eval script (tag `eval`): metrics, recording and the bounded calibration."""

    def run_eval(self, *argv):
        """eval_cases.main(argv) with captured stdout: (exit code, parsed stdout line)."""
        out = io.StringIO()
        with (mock.patch.object(sys, "argv", ["eval_cases.py", *argv]),
              mock.patch.object(sys, "stdout", out)):
            code = _eval().main()
        text = out.getvalue().strip()
        return code, (json.loads(text) if text else None)

    def test_eval_cases_composition(self):
        cases = SCRIPT.parents[1] / "evals" / "cases.jsonl"
        rows = [json.loads(line) for line in cases.read_text(encoding="utf-8").splitlines()
                if line.strip()]
        self.assertEqual(len(rows), 32)

        def kind(row):
            item = row["item"]
            return "shorthand" if set(item) == {"id", "criterion", "evidence"} else item["type"]

        counts, ambiguous = {}, {}
        for row in rows:
            counts[kind(row)] = counts.get(kind(row), 0) + 1
            if row["ambiguous"]:
                ambiguous[kind(row)] = ambiguous.get(kind(row), 0) + 1
        self.assertEqual(counts, {"choice": 10, "noul": 10, "score": 6, "shorthand": 6})
        self.assertEqual({row["item"]["id"] for row in rows if row["ambiguous"]},
                         {"c09", "c10", "n10", "r06", "s06"})

    def test_eval_reports_accuracy(self):
        with JevStub() as stub:
            self.point_at(stub)
            self.enable("laya")
            code, report = self.run_eval()
        self.assertEqual(code, 0)
        assert report is not None
        self.assertEqual(report["backend"], "laya")
        self.assertEqual(report["n"], 32)
        for key in ("accuracy", "fallback_rate", "accuracy_when_not_fallback"):
            self.assertIn(key, report)

    def test_eval_ambiguous_rows(self):
        module = _eval()
        rows = [{"backend": "laya", "ambiguous": False, "correct": True,
                 "needs_fallback": False},
                {"backend": "laya", "ambiguous": False, "correct": False,
                 "needs_fallback": False},
                {"backend": "laya", "ambiguous": True, "correct": False,
                 "needs_fallback": True}]
        report = module.summarize(rows)
        self.assertEqual(report["n"], 3)
        self.assertEqual(report["accuracy"], 0.5)
        self.assertAlmostEqual(report["fallback_rate"], 1 / 3)
        self.assertEqual(report["accuracy_when_not_fallback"], 0.5)

    def test_eval_kill_switch(self):
        with JevStub() as stub:
            self.point_at(stub)
            code, report = self.run_eval()
        self.assertEqual(code, 0)
        self.assertEqual(report, {"status": "disabled"})
        self.assertEqual(stub.bodies, [])

    def test_eval_record_path(self):
        target = self.tmp / "results.json"
        other = self.tmp / "elsewhere.json"
        with JevStub() as stub:
            self.point_at(stub)
            self.enable("laya")
            code, _report = self.run_eval("--record", str(target))
            self.assertEqual(code, 0)
            self.assertTrue(target.is_file())
            self.assertFalse(other.exists())
            code, _report = self.run_eval()
            self.assertEqual(code, 0)
        # without --record nothing new is written anywhere under the temp dir
        self.assertEqual([path.name for path in self.tmp.iterdir() if path.name.endswith("json")],
                         ["results.json"])

    def test_eval_record_fallback_flags(self):
        target = self.tmp / "results.json"
        with JevStub(tops={"c01": 0.4, "n02": 0.4, "r01": 0.4}) as stub:
            self.point_at(stub)
            self.enable("laya")
            code, report = self.run_eval("--record", str(target))
            self.assertEqual(code, 0)
            assert report is not None
        saved = json.loads(target.read_text(encoding="utf-8"))
        laya = next(entry for entry in saved["results"] if entry["backend"] == "laya")
        self.assertEqual(len(laya["cases"]), 32)
        for case in laya["cases"]:
            self.assertIsInstance(case["needs_fallback"], bool)
            self.assertEqual(case["backend"], "laya")
        self.assertAlmostEqual(report["fallback_rate"],
                               sum(case["needs_fallback"] for case in laya["cases"]) / 32)

    def test_eval_calibrate_none(self):
        self.assertIsNone(_eval().calibrate([{"top": 0.4, "correct": True}] * 30))

    def test_eval_calibrate_picks_lowest_qualifying_threshold(self):
        rows = ([{"top": 0.96, "correct": True}] * 20
                + [{"top": 0.2, "correct": False}] * 10)
        self.assertEqual(_eval().calibrate(rows), 0.50)

    def test_eval_calibrate_excludes_ambiguous_from_accuracy(self):
        clear = [{"top": 0.96, "correct": True}] * 20
        confident_wrong_ambiguous = [{"top": 0.96, "correct": False, "ambiguous": True}] * 5
        flagged_ambiguous = [{"top": 0.2, "correct": False, "ambiguous": True}] * 5
        self.assertEqual(
            _eval().calibrate(clear + confident_wrong_ambiguous + flagged_ambiguous), 0.50)

    def _calib_dir(self, source):
        skill = self.tmp / "skill"
        (skill / "scripts").mkdir(parents=True, exist_ok=True)
        script = skill / "scripts" / "eval_cases.py"
        shutil.copy(SCRIPT.parent / "eval_cases.py", script)
        (skill / "scripts" / "jev_review.py").write_text(source, encoding="utf-8")
        results = skill / "results.json"
        results.write_text(json.dumps({"results": [
            {"backend": "laya", "cases": ([{"top": 0.96, "correct": True,
                                            "ambiguous": False}] * 20
                                          + [{"top": 0.2, "correct": False}] * 10)}]}),
            encoding="utf-8")
        return script, skill / "scripts" / "jev_review.py", results

    def test_eval_calibrate_rewrites_one_row(self):
        script, target, results = self._calib_dir(TABLE_SOURCE)
        proc = subprocess.run([sys.executable, "-B", str(script), "--calibrate", str(results)],
                              capture_output=True, text=True, check=False)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        text = target.read_text(encoding="utf-8")
        self.assertIn('"min_confidence": 0.5,', text)
        self.assertIn('"min_confidence": 0.8,', text)  # the typesafe row is untouched
        self.assertEqual(len(text.splitlines()), len(TABLE_SOURCE.splitlines()))

    def test_eval_calibrate_row_bounded(self):
        for source in (TABLE_SOURCE_NO_LAYA, TABLE_SOURCE_DOUBLE):
            with self.subTest(case="missing" if source is TABLE_SOURCE_NO_LAYA else "double"):
                script, target, results = self._calib_dir(source)
                before = target.read_bytes()
                proc = subprocess.run(
                    [sys.executable, "-B", str(script), "--calibrate", str(results)],
                    capture_output=True, text=True, check=False)
                self.assertNotEqual(proc.returncode, 0)
                self.assertEqual(target.read_bytes(), before, "the file must stay byte-identical")

    def test_eval_min_confidence_env_overrides(self):
        with JevStub() as stub:
            self.point_at(stub)
            self.enable("laya")
            os.environ["JEV_MIN_CONFIDENCE"] = "0.99"
            code, report = self.run_eval()
        self.assertEqual(code, 0)
        assert report is not None
        self.assertEqual(report["fallback_rate"], 1.0)


if __name__ == "__main__":
    unittest.main()
