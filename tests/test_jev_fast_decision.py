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
import hashlib
import http.server
import importlib.util
import io
import json
import math
import os
import re
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
    ``{"status": ..., "headers": ..., "body": ...}`` entries (a ``None`` entry answers normally),
    which is how the error-taxonomy cases are driven.
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

    def __exit__(self, *_exc):
        assert self.server is not None and self.thread is not None  # set by __enter__
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
                    "probe": lambda _row, _timeout: None})
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
        # Task 2: the two remote rows are gated, so they are reported and never dialled.
        self.assertEqual(result["unavailable"], {"laya": "unreachable",
                                                 "typesafe": "consent_required",
                                                 "opencode": "consent_required"})

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
        self.assertEqual(str(refused.exception), "consent_required")


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
        self.assertEqual(self.backend_entry(report, "typesafe")["reason"], "consent_required")
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
                             "consent_required")
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


if __name__ == "__main__":
    unittest.main()
