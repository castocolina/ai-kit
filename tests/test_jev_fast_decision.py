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

import hashlib
import http.server
import importlib.util
import io
import json
import math
import os
import shutil
import socket
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


def _distribution(top, slots, winner=0, uniform=False):
    """Probabilities over `slots` summing to ~1, with `winner` on top."""
    if uniform:
        flat = round(1.0 / len(slots), 4)  # Laya rounds to 4 decimals: three ways sums 0.9999
        return {slot: flat for slot in slots}
    rest = (1.0 - top) / (len(slots) - 1) if len(slots) > 1 else 0.0
    return {slot: (top if i == winner else rest) for i, slot in enumerate(slots)}


class JevStub:
    """An in-process System One stub on 127.0.0.1: answers like Laya and records every request.

    ``model`` is the answering id it echoes, ``top`` the winning probability, ``tops`` the
    per-question overrides, ``truncated`` sets ``usage.truncated``, ``uniform`` answers with
    flat 4-decimal probabilities, ``delay`` sleeps before each answer, ``health`` is the
    ``GET /health`` status, and ``script`` is a per-request queue of
    ``{"status": ..., "headers": ..., "body": ...}`` entries (a ``None`` entry answers normally),
    which is how the error-taxonomy cases are driven.
    """

    def __init__(self, model="laya-rl-agent", top=0.9, tops=None, truncated=False,
                 uniform=False, delay=0.0, health=200, script=None):
        self.model = model
        self.top = top
        self.tops = dict(tops or {})
        self.truncated = truncated
        self.uniform = uniform
        self.delay = delay
        self.health = health
        self.script = list(script or [])
        self.requests = []
        self.server = None
        self.thread = None

    def __enter__(self):
        stub = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                status = stub.health if self.path == "/health" else 404
                stub.record("GET", self.path, {}, b"")
                self.reply(status, b'{"status":"ok"}')

            def do_POST(self):
                raw = self.rfile.read(int(self.headers.get("Content-Length") or 0))
                stub.record("POST", self.path, dict(self.headers), raw)
                if stub.delay:
                    time.sleep(stub.delay)
                entry = stub.take_script()
                if entry is None:
                    entry = {"status": 200, "body": stub.answer_json(raw)}
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

            def log_message(self, *args):
                pass

        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever,
                                       kwargs={"poll_interval": 0.05}, daemon=True)
        self.thread.start()
        return self

    def __exit__(self, *exc):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
        return False

    @property
    def port(self):
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

    def answer_json(self, raw):
        questions = (_maybe_json(raw) or {}).get("questions") or {}
        usage = {"input_tokens": 10, "output_tokens": 0}
        if self.truncated:
            usage["truncated"] = True
        answers = {qid: self.answer_for(qid, spec or {}) for qid, spec in questions.items()}
        return json.dumps({"model": self.model, "answers": answers, "usage": usage}).encode()

    def answer_for(self, qid, spec):
        qtype = spec.get("type", "noul")
        top = self.tops.get(qid, self.top)
        if qtype == "choice":
            options = list(spec.get("criteria") or {"x": "x"})
            probs = _distribution(top, options, uniform=self.uniform)
            return {"type": "choice", "choice": options[0], "confidence": probs[options[0]],
                    "probabilities": probs}
        if qtype == "score":
            levels = list(spec.get("criteria") or ["low", "mid", "high"])
            slots = [str(index) for index in range(len(levels))]
            winner = min(2, len(levels) - 1)
            return {"type": "score", "score": float(winner), "confidence": top,
                    "legend": dict(zip(slots, levels, strict=True)),
                    "probabilities": _distribution(top, slots, winner, self.uniform)}
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

    def enable(self, backend="laya"):
        os.environ["GSD_PATH_JEV"] = "1"
        os.environ["GSD_PATH_JEV_TIMEOUT_SECONDS"] = "5"
        if backend is not None:
            os.environ["JEV_BACKEND"] = backend

    def run_screen(self, payload_value, stdin_text=None):
        text = stdin_text if stdin_text is not None else json.dumps(payload_value)
        with mock.patch.object(sys, "stdin", io.StringIO(text)):
            return JR.screen()

    def run_main(self, payload_value):
        """main([]) on a payload: (exit code, the parsed stdout JSON)."""
        out = io.StringIO()
        with (mock.patch.object(sys, "stdin", io.StringIO(json.dumps(payload_value))),
              mock.patch.object(sys, "stdout", out)):
            code = JR.main([])
        return code, json.loads(out.getvalue())

    def run_probe(self):
        """main(["--probe"]): (exit code, the parsed stdout JSON)."""
        out = io.StringIO()
        with mock.patch.object(sys, "stdout", out):
            code = JR.main(["--probe"])
        return code, json.loads(out.getvalue())

    def backend_entry(self, report, name):
        return next(entry for entry in report["backends"] if entry["name"] == name)

    def assert_no_posts(self, stub):
        self.assertEqual(stub.posts, [], "a probe must never send question content")


class TestProbe(_ClientCase):
    def test_probe_laya_up(self):
        with JevStub() as stub:
            self.point_at(stub)
            code, report = self.run_probe()
        self.assertEqual(code, 0)
        self.assertEqual(report["status"], "ok")
        self.assertEqual(report["selected"], "laya")
        self.assertEqual(report["candidates"], ["laya"])
        self.assertEqual([entry["name"] for entry in report["backends"]], ["laya"])
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
        self.assertEqual([entry["name"] for entry in report["backends"]], ["laya"])
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
        self.assertEqual([entry["name"] for entry in report["backends"]], ["laya"])
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
            def read(self, *args):
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
        self.assertEqual(result["unavailable"], {"laya": "unreachable"})

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

        def flaky(row, body, timeout):
            calls.append(body)
            response, encoded = real_send(row, body, timeout)
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


if __name__ == "__main__":
    unittest.main()
