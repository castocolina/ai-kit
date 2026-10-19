"""Tests for scripts/jev_review.py in this skill."""
from __future__ import annotations

import importlib.util
import pathlib

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "scripts/jev_review.py"


def load():
    spec = importlib.util.spec_from_file_location("jev_review", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


import http.server
import json
import threading

import pytest


class LayaStub(http.server.BaseHTTPRequestHandler):
    bodies: list[dict] = []

    def do_GET(self):
        self.send_response(200 if self.path == "/health" else 404)
        self.end_headers()
        self.wfile.write(b'{"status":"ok","device":"cuda"}')

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        LayaStub.bodies.append(body)
        answers = {}
        for qid, spec in body["questions"].items():
            qtype = spec.get("type", "noul")
            if qtype == "choice":
                opts = list(spec.get("criteria", {"x": ""}).keys()) or ["x"]
                top = opts[0]
                tail = (1.0 - 0.9) / (len(opts) - 1) if len(opts) > 1 else 0.0
                answers[qid] = {
                    "type": "choice", "choice": top, "confidence": 0.9,
                    "probabilities": {o: (0.9 if o == top else tail) for o in opts},
                }
            elif qtype == "score":
                levels = spec.get("criteria", ["low", "mid", "high"])
                n = len(levels)
                legend = {str(i): levels[i] for i in range(n)}
                score_i = min(2, n - 1)
                tail = (1.0 - 0.9) / (n - 1) if n > 1 else 0.0
                probs = {str(i): (0.9 if i == score_i else tail) for i in range(n)}
                answers[qid] = {
                    "type": "score", "score": float(score_i), "confidence": 0.9,
                    "legend": legend, "probabilities": probs,
                }
            else:
                answers[qid] = {"type": "noul", "noul": 0.9, "confidence": 0.9}
        payload = {"model": "laya-rl-agent", "answers": answers,
                   "usage": {"input_tokens": 10, "output_tokens": 0}}
        self.send_response(200)
        self.end_headers()
        self.wfile.write(json.dumps(payload).encode())

    def log_message(self, *args):
        pass


@pytest.fixture
def laya(clean_env, monkeypatch):  # clean_env first, so this URL override runs last
    LayaStub.bodies = []
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), LayaStub)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    monkeypatch.setenv("JEV_LAYA_URL", f"http://127.0.0.1:{server.server_port}")
    yield server
    server.shutdown()


@pytest.fixture
def clean_env(monkeypatch, tmp_path):
    for name in (
        "JEV_BACKEND", "JEV_ALLOW_REMOTE", "TYPESAFE_API_KEY", "OPENCODE_API_KEY", "LAYA_API_KEY",
        "JEV_LAYA_URL", "JEV_MIN_CONFIDENCE", "JEV_API_URL", "JEV_MODEL", "JEV_RESPONSE_MODEL", "JEV_API_KEY",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))  # no auth.json
    monkeypatch.setenv("JEV_LAYA_URL", "http://127.0.0.1:9")  # closed port


def test_auto_prefers_laya_when_healthy(clean_env, laya):
    usable, _ = load().candidates()
    assert usable[0] == "laya"


def test_auto_without_consent_considers_only_laya(clean_env):
    usable, reasons = load().candidates()
    assert usable == []
    assert reasons == {"laya": "unreachable"}


def test_auto_with_consent_skips_unreachable_laya_and_keyless_remotes(clean_env, monkeypatch):
    monkeypatch.setenv("JEV_ALLOW_REMOTE", "1")
    usable, reasons = load().candidates()
    assert usable == []
    assert reasons == {"laya": "unreachable", "typesafe": "missing_api_key", "opencode": "missing_api_key"}


def test_laya_non_loopback_url_is_not_local(clean_env, monkeypatch):
    monkeypatch.setenv("JEV_LAYA_URL", "http://203.0.113.9:8010")
    usable, reasons = load().candidates()
    assert "laya" not in usable
    assert reasons["laya"] == "non_loopback_url"


def test_opencode_key_comes_from_auth_json(clean_env, tmp_path, monkeypatch):
    monkeypatch.setenv("JEV_ALLOW_REMOTE", "1")
    (tmp_path / "opencode").mkdir()
    (tmp_path / "opencode/auth.json").write_text(json.dumps({"opencode": {"type": "api", "key": "k"}}))
    usable, _ = load().candidates()
    assert usable == ["opencode"]


def test_explicit_backend_never_falls_back(clean_env, monkeypatch):
    monkeypatch.setenv("JEV_ALLOW_REMOTE", "1")
    monkeypatch.setenv("JEV_BACKEND", "typesafe")
    monkeypatch.setenv("OPENCODE_API_KEY", "k")
    usable, reasons = load().candidates()
    assert usable == []
    assert reasons == {"typesafe": "missing_api_key"}


def test_explicit_remote_requires_allow_remote(clean_env, monkeypatch):
    monkeypatch.setenv("JEV_BACKEND", "typesafe")
    monkeypatch.setenv("TYPESAFE_API_KEY", "k")
    usable, reasons = load().candidates()
    assert usable == []
    assert reasons == {"typesafe": "consent_required_for_remote"}


def test_explicit_backend_probe_reports_composite_reason(clean_env, monkeypatch, capsys):
    monkeypatch.setenv("JEV_ALLOW_REMOTE", "1")
    monkeypatch.setenv("JEV_BACKEND", "typesafe")
    monkeypatch.setattr("sys.argv", ["jev_review.py", "--probe"])
    load().main()
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "unavailable"
    assert payload["reason"] == "backend_unavailable:typesafe:missing_api_key"
    assert payload["selected"] is None
    assert payload["unavailable"] == {"typesafe": "missing_api_key"}


def test_probe_auto_laya_down_remote_key_needs_consent(clean_env, monkeypatch, capsys):
    monkeypatch.setenv("TYPESAFE_API_KEY", "k")
    monkeypatch.setattr("sys.argv", ["jev_review.py", "--probe"])
    load().main()
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "consent_required_for_remote" and payload["remote_available"] == ["typesafe"]


def test_unknown_backend_name_is_rejected(clean_env, monkeypatch):
    monkeypatch.setenv("JEV_BACKEND", "zen")
    usable, reasons = load().candidates()
    assert usable == [] and reasons == {"zen": "unknown_backend"}


def run_screen(module, monkeypatch, payload, **env):
    import io
    monkeypatch.setenv("GSD_PATH_JEV", "1")
    monkeypatch.setenv("GSD_PATH_JEV_TIMEOUT_SECONDS", "5")
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
    return module.screen()


THREE_ITEMS = {"reviewed_head": "0" * 40, "items": [
    {"id": "a", "type": "noul", "instructions": "Refund requested?", "context": "charged twice"},
    {"id": "b", "type": "noul", "instructions": "Wants a human?", "context": "get me a person"},
    {"id": "c", "type": "noul", "instructions": "Is it a bug?", "context": "app crashes"},
]}


def test_laya_sends_one_request_per_item_with_only_that_item_in_state(clean_env, laya, monkeypatch):
    result = run_screen(load(), monkeypatch, THREE_ITEMS)
    assert result["status"] == "ok" and result["backend"] == "laya"
    assert len(LayaStub.bodies) == 3
    for body, item_id in zip(LayaStub.bodies, "abc"):
        assert list(body["questions"]) == [item_id]
        assert [i["id"] for i in body["state"]["items"]] == [item_id]
        assert body["model"] == "jev-1"
    assert set(result["answers"]) == {"a", "b", "c"}
    assert result["usage"]["input_tokens"] == 30


def test_request_sha256_is_the_wire_bodies(clean_env, laya, monkeypatch):
    import hashlib
    result = run_screen(load(), monkeypatch, THREE_ITEMS)
    encoded = b"".join(
        json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
        for body in LayaStub.bodies
    )
    assert result["request_sha256"] == hashlib.sha256(encoded).hexdigest()


def test_request_sha256_includes_the_body_whose_send_raised(clean_env, laya, monkeypatch):
    import hashlib
    module = load()
    real_send = module._send

    def flaky(name, body, timeout):
        response, encoded = real_send(name, body, timeout)
        if len(LayaStub.bodies) == 2:
            raise OSError("down")
        return response, encoded

    monkeypatch.setattr(module, "_send", flaky)
    result = run_screen(module, monkeypatch, THREE_ITEMS)
    encoded = b"".join(
        json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
        for body in LayaStub.bodies
    )
    assert result["status"] == "unavailable"
    assert result["request_sha256"] == hashlib.sha256(encoded).hexdigest()


def test_direct_send_and_dispatch_transmit_nothing_when_gated(clean_env, monkeypatch):
    module = load()

    def boom(*_args, **_kwargs):
        raise AssertionError("transmitted")

    monkeypatch.setattr(module.urllib.request, "build_opener", boom)
    monkeypatch.delenv("GSD_PATH_JEV", raising=False)
    with pytest.raises(PermissionError, match="disabled"):
        module._send("laya", {"model": "jev-1"}, 1)
    with pytest.raises(module.DispatchError) as killed:
        module._dispatch("laya", THREE_ITEMS, 1)
    assert isinstance(killed.value.cause, PermissionError)

    monkeypatch.setenv("GSD_PATH_JEV", "1")
    monkeypatch.delenv("JEV_ALLOW_REMOTE", raising=False)
    with pytest.raises(PermissionError, match="consent_required_for_remote"):
        module._send("typesafe", {"model": "jev-latest"}, 1)
    with pytest.raises(module.DispatchError) as remote:
        module._dispatch("opencode", THREE_ITEMS, 1)
    assert isinstance(remote.value.cause, PermissionError)

    monkeypatch.setenv("JEV_LAYA_URL", "http://203.0.113.9:8010")
    with pytest.raises(PermissionError, match="non_loopback_url"):
        module._send("laya", {"model": "jev-1"}, 1)
    with pytest.raises(module.DispatchError) as offhost:
        module._dispatch("laya", THREE_ITEMS, 1)
    assert isinstance(offhost.value.cause, PermissionError)
    assert str(offhost.value.cause) == "non_loopback_url"


def _ok_noul(body, model):
    return ({"model": model, "usage": {"input_tokens": 1, "output_tokens": 0},
             "answers": {q: {"type": "noul", "noul": 0.95} for q in body["questions"]}}, b"")


def test_auto_falls_through_on_http_error_and_reports_attempts(clean_env, laya, monkeypatch):
    module = load()
    monkeypatch.setenv("JEV_ALLOW_REMOTE", "1")
    monkeypatch.setenv("TYPESAFE_API_KEY", "k")
    calls = []

    def fake_send(name, body, timeout):
        calls.append(name)
        if name == "laya":
            raise OSError("down")
        return _ok_noul(body, "jev-latest")

    monkeypatch.setattr(module, "_send", fake_send)
    result = run_screen(module, monkeypatch, THREE_ITEMS)
    assert result["status"] == "ok" and result["backend"] == "typesafe"
    assert calls == ["laya", "typesafe"]
    assert result["attempts"] == [{"backend": "laya", "reason": "network_error"}]


def test_auto_laya_failure_does_not_send_remote_without_consent(clean_env, laya, monkeypatch):
    module = load()
    monkeypatch.setenv("TYPESAFE_API_KEY", "k")
    calls = []

    def fake_send(name, body, timeout):
        calls.append(name)
        if name == "laya":
            raise OSError("down")
        raise AssertionError(name)

    monkeypatch.setattr(module, "_send", fake_send)
    result = run_screen(module, monkeypatch, THREE_ITEMS)
    assert calls == ["laya"]
    assert result["status"] == "consent_required_for_remote"
    assert result["remote_available"] == ["typesafe"]


def test_no_backend_available_reports_reasons(clean_env, monkeypatch):
    result = run_screen(load(), monkeypatch, THREE_ITEMS)
    assert result["status"] == "unavailable"
    assert result["reason"] == "no_backend_available"
    assert result["unavailable"]["laya"] == "unreachable"


def test_auto_retains_probe_unavailable_when_laya_unreachable_and_typesafe_429(clean_env, monkeypatch):
    import urllib.error
    module = load()
    monkeypatch.setenv("JEV_ALLOW_REMOTE", "1")
    monkeypatch.setenv("TYPESAFE_API_KEY", "k")

    def fake_send(name, body, timeout):
        if name == "typesafe":
            raise urllib.error.HTTPError(
                module.BACKENDS["typesafe"]["url"], 429, "quota", hdrs=None, fp=None,
            )
        raise AssertionError(name)

    monkeypatch.setattr(module, "_send", fake_send)
    result = run_screen(module, monkeypatch, THREE_ITEMS)
    assert result["status"] == "unavailable"
    assert result["unavailable"]["laya"] == "unreachable"
    assert result["attempts"] == [{"backend": "typesafe", "reason": "http_429"}]


def test_invalid_jev_min_confidence_is_rejected(clean_env, laya, monkeypatch):
    monkeypatch.setenv("JEV_MIN_CONFIDENCE", "not-a-number")
    result = run_screen(load(), monkeypatch, THREE_ITEMS)
    assert result["status"] == "unavailable"
    assert result["reason"] == "invalid_min_confidence"


def test_backend_default_min_confidence_used_when_env_unset(clean_env, laya, monkeypatch):
    module = load()
    module.BACKENDS["laya"]["min_confidence"] = 0.8
    monkeypatch.setattr(module, "_send", lambda n, b, t: (
        {"model": "laya-rl-agent", "usage": {"input_tokens": 1, "output_tokens": 0},
         "answers": {q: {"type": "noul", "noul": 0.75} for q in b["questions"]}}, b""))
    result = run_screen(module, monkeypatch, THREE_ITEMS)
    assert result["status"] == "ok"
    assert all(a["needs_fallback"] for a in result["answers"].values())


def test_explicit_backend_screen_reports_composite_reason(clean_env, monkeypatch):
    monkeypatch.setenv("JEV_ALLOW_REMOTE", "1")
    monkeypatch.setenv("JEV_BACKEND", "typesafe")
    result = run_screen(load(), monkeypatch, THREE_ITEMS)
    assert result["status"] == "unavailable"
    assert result["reason"] == "backend_unavailable:typesafe:missing_api_key"


def test_explicit_remote_screen_requires_allow_remote(clean_env, monkeypatch):
    monkeypatch.setenv("JEV_BACKEND", "opencode")
    monkeypatch.setenv("OPENCODE_API_KEY", "k")
    result = run_screen(load(), monkeypatch, THREE_ITEMS)
    assert result["status"] == "unavailable"
    assert result["reason"] == "backend_unavailable:opencode:consent_required_for_remote"


def test_needs_fallback_marks_low_confidence(clean_env, laya, monkeypatch):
    module = load()
    module.BACKENDS["laya"]["min_confidence"] = 0.7  # not the calibrated file default
    monkeypatch.setattr(module, "_send", lambda n, b, t: (
        {"model": "laya-rl-agent", "usage": {"input_tokens": 1, "output_tokens": 0},
         "answers": {q: {"type": "noul", "noul": 0.6} for q in b["questions"]}}, b""))
    result = run_screen(module, monkeypatch, THREE_ITEMS)
    assert all(a["needs_fallback"] for a in result["answers"].values())


def test_malformed_response_is_invalid_response_not_a_traceback(clean_env, laya, monkeypatch):
    module = load()
    monkeypatch.setattr(module, "_send", lambda n, b, t: ({"model": "not-a-model"}, b""))
    result = run_screen(module, monkeypatch, THREE_ITEMS)
    assert result["status"] == "unavailable"
    assert result["attempts"] == [{"backend": "laya", "reason": "invalid_response"}]


def test_json_decode_error_is_invalid_response(clean_env, laya, monkeypatch):
    module = load()

    def fake_send(name, body, timeout):
        raise json.JSONDecodeError("bad", "", 0)

    monkeypatch.setattr(module, "_send", fake_send)
    result = run_screen(module, monkeypatch, THREE_ITEMS)
    assert result["status"] == "unavailable"
    assert result["attempts"] == [{"backend": "laya", "reason": "invalid_response"}]


def _opencode(monkeypatch):
    monkeypatch.setenv("JEV_ALLOW_REMOTE", "1")
    monkeypatch.setenv("JEV_BACKEND", "opencode")
    monkeypatch.setenv("OPENCODE_API_KEY", "k")


def _http_error(module, code, body: bytes):
    import io
    import urllib.error
    return urllib.error.HTTPError(
        module.BACKENDS["opencode"]["url"], code, "err", hdrs=None, fp=io.BytesIO(body),
    )


def test_opencode_free_429_uses_paid(clean_env, monkeypatch):
    module = load()
    _opencode(monkeypatch)
    calls = []

    def fake_send(name, body, timeout):
        calls.append(body["model"])
        if body["model"] == "jev-1.13-free":
            raise _http_error(module, 429, b'{"type":"error","error":{"type":"FreeUsageLimitError","message":"Rate limit exceeded. Please try again later."}}')
        return _ok_noul(body, body["model"])

    monkeypatch.setattr(module, "_send", fake_send)
    result = run_screen(module, monkeypatch, THREE_ITEMS)
    assert calls == ["jev-1.13-free", "jev-1.13"]
    assert result["status"] == "ok" and result["backend"] == "opencode"
    assert result["model"] == "jev-1.13"
    assert result["attempts"] == [{"backend": "opencode", "model": "jev-1.13-free", "reason": "http_429"}]


def test_opencode_free_400_model_unavailable_uses_paid(clean_env, monkeypatch):
    module = load()
    _opencode(monkeypatch)
    calls = []

    def fake_send(name, body, timeout):
        calls.append(body["model"])
        if body["model"] == "jev-1.13-free":
            raise _http_error(module, 400, b'{"message":"Model is unavailable"}')
        return _ok_noul(body, body["model"])

    monkeypatch.setattr(module, "_send", fake_send)
    result = run_screen(module, monkeypatch, THREE_ITEMS)
    assert calls == ["jev-1.13-free", "jev-1.13"]
    assert result["status"] == "ok" and result["model"] == "jev-1.13"


def test_opencode_free_400_other_does_not_call_paid(clean_env, monkeypatch):
    module = load()
    _opencode(monkeypatch)
    calls = []

    def fake_send(name, body, timeout):
        calls.append(body["model"])
        raise _http_error(module, 400, b'{"message":"invalid questions"}')

    monkeypatch.setattr(module, "_send", fake_send)
    result = run_screen(module, monkeypatch, THREE_ITEMS)
    assert calls == ["jev-1.13-free"]
    assert result["status"] == "unavailable"


def test_opencode_free_ok_does_not_call_paid(clean_env, monkeypatch):
    module = load()
    _opencode(monkeypatch)
    calls = []

    def fake_send(name, body, timeout):
        calls.append(body["model"])
        return _ok_noul(body, body["model"])

    monkeypatch.setattr(module, "_send", fake_send)
    result = run_screen(module, monkeypatch, THREE_ITEMS)
    assert calls == ["jev-1.13-free"]
    assert result["status"] == "ok" and result["model"] == "jev-1.13-free"
    assert result["attempts"] == []


@pytest.mark.parametrize("code", [500, 503])
def test_opencode_free_5xx_uses_paid(clean_env, monkeypatch, code):
    module = load()
    _opencode(monkeypatch)
    calls = []

    def fake_send(name, body, timeout):
        calls.append(body["model"])
        if body["model"] == "jev-1.13-free":
            raise _http_error(module, code, b"unavailable")
        return _ok_noul(body, body["model"])

    monkeypatch.setattr(module, "_send", fake_send)
    result = run_screen(module, monkeypatch, THREE_ITEMS)
    assert calls == ["jev-1.13-free", "jev-1.13"]
    assert result["status"] == "ok" and result["model"] == "jev-1.13"


def test_opencode_free_network_error_uses_paid(clean_env, monkeypatch):
    module = load()
    _opencode(monkeypatch)
    calls = []

    def fake_send(name, body, timeout):
        calls.append(body["model"])
        if body["model"] == "jev-1.13-free":
            raise OSError("down")
        return _ok_noul(body, body["model"])

    monkeypatch.setattr(module, "_send", fake_send)
    result = run_screen(module, monkeypatch, THREE_ITEMS)
    assert calls == ["jev-1.13-free", "jev-1.13"]
    assert result["status"] == "ok" and result["model"] == "jev-1.13"


@pytest.mark.parametrize("code", [401, 403])
def test_opencode_free_auth_error_does_not_call_paid(clean_env, monkeypatch, code):
    module = load()
    _opencode(monkeypatch)
    calls = []

    def fake_send(name, body, timeout):
        calls.append(body["model"])
        raise _http_error(module, code, b"denied")

    monkeypatch.setattr(module, "_send", fake_send)
    result = run_screen(module, monkeypatch, THREE_ITEMS)
    assert calls == ["jev-1.13-free"]
    assert result["status"] == "unavailable"


@pytest.mark.parametrize("total, ok", [(0.9999, True), (0.98, False)])
def test_probability_rounding_tolerance(total, ok):
    module = load()
    answer = {"type": "choice", "choice": "x", "confidence": 0.5,
              "probabilities": {"x": total - 0.1, "y": 0.1}}
    if ok:
        module._check_choice_answer(answer, {"x": "", "y": ""})
    else:
        with pytest.raises(ValueError):
            module._check_choice_answer(answer, {"x": "", "y": ""})


def _eval():
    import importlib.util
    spec = importlib.util.spec_from_file_location("eval_cases", SCRIPT.parent / "eval_cases.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_cases_jsonl_composition():
    rows = [json.loads(line) for line in (SCRIPT.parents[1] / "evals" / "cases.jsonl").read_text().splitlines() if line.strip()]
    assert len(rows) == 32

    def kind(row):
        item = row["item"]
        return "shorthand" if set(item) == {"id", "criterion", "evidence"} else item["type"]

    counts, ambiguous = {}, {}
    for row in rows:
        counts[kind(row)] = counts.get(kind(row), 0) + 1
        if row["ambiguous"]:
            ambiguous[kind(row)] = ambiguous.get(kind(row), 0) + 1
    assert counts == {"choice": 10, "noul": 10, "score": 6, "shorthand": 6}
    assert ambiguous == {"choice": 2, "noul": 1, "score": 1, "shorthand": 1}
    assert {row["item"]["id"] for row in rows if row["ambiguous"]} == {"c09", "c10", "n10", "r06", "s06"}


def test_eval_cases_reports_accuracy(clean_env, laya, monkeypatch, capsys):
    monkeypatch.setenv("GSD_PATH_JEV", "1")
    monkeypatch.setenv("GSD_PATH_JEV_TIMEOUT_SECONDS", "5")
    monkeypatch.setattr("sys.argv", ["eval_cases.py"])
    assert _eval().main() == 0
    report = json.loads(capsys.readouterr().out)
    assert report["backend"] == "laya" and report["n"] == 32


def test_ambiguous_rows_stay_in_n_and_fallback_rate_and_out_of_accuracy():
    module = _eval()
    rows = [
        {"backend": "laya", "ambiguous": False, "correct": True, "needs_fallback": False},
        {"backend": "laya", "ambiguous": False, "correct": False, "needs_fallback": False},
        {"backend": "laya", "ambiguous": True, "correct": False, "needs_fallback": True},
    ]
    report = module.summarize(rows)
    assert report["n"] == 3
    assert report["accuracy"] == 0.5
    assert report["fallback_rate"] == 1 / 3
    assert report["accuracy_when_not_fallback"] == 0.5
    saved = module.merge_results({"results": []}, "laya", [
        {"id": "c09", "top": 0.4, "correct": False, "ambiguous": True},
        {"id": "c01", "top": 0.9, "correct": True, "ambiguous": False},
    ])
    assert [case["id"] for case in saved["results"][0]["cases"]] == ["c09", "c01"]
    assert saved["results"][0]["cases"][0]["ambiguous"] is True


def test_eval_cases_sends_nothing_when_kill_switch_unset(clean_env, laya, monkeypatch, capsys):
    monkeypatch.delenv("GSD_PATH_JEV", raising=False)
    monkeypatch.setattr("sys.argv", ["eval_cases.py"])
    assert _eval().main() == 0
    assert LayaStub.bodies == []


def test_case_correct_and_case_record():
    module = _eval()
    assert module.case_correct({"choice": "setup"}, "setup", "choice")
    assert not module.case_correct({"choice": "clean"}, "setup", "choice")
    assert module.case_correct({"choice": "supported"}, "supported", "choice")
    assert not module.case_correct({"choice": "unsupported"}, "supported", "choice")
    assert module.case_correct({"noul": 0.9}, True, "noul")
    assert module.case_correct({"score": 1.4}, 1, "score")
    record = module.case_record("n01", {"noul": 0.9}, True, "noul")
    assert record == {"id": "n01", "top": 0.9, "correct": True}
    assert module.case_record("n01", {"noul": 0.9}, True, "noul") == record
    merged = module.merge_results({"results": []}, "laya", [record])
    assert merged == module.merge_results(merged, "laya", [record])


def test_calibrate_returns_none_when_nothing_qualifies():
    assert _eval().calibrate([{"top": 0.4, "correct": True}] * 30) is None

def test_calibrate_picks_lowest_qualifying_threshold():
    rows = [{"top": 0.96, "correct": True}] * 20 + [{"top": 0.2, "correct": False}] * 10
    assert _eval().calibrate(rows) == 0.50

def test_calibrate_excludes_ambiguous_from_accuracy():
    clear = [{"top": 0.96, "correct": True}] * 20
    confident_wrong_ambiguous = [{"top": 0.96, "correct": False, "ambiguous": True}] * 5
    flagged_ambiguous = [{"top": 0.2, "correct": False, "ambiguous": True}] * 5
    assert _eval().calibrate(clear + confident_wrong_ambiguous + flagged_ambiguous) == 0.50


def test_jev_min_confidence_overrides_backend_default(clean_env, laya, monkeypatch):
    module = load()
    module.BACKENDS["laya"]["min_confidence"] = 0.5
    monkeypatch.setenv("JEV_MIN_CONFIDENCE", "0.99")
    monkeypatch.setattr(module, "_send", lambda n, b, t: (
        {"model": "laya-rl-agent", "usage": {"input_tokens": 1, "output_tokens": 0},
         "answers": {q: {"type": "noul", "noul": 0.8} for q in b["questions"]}}, b""))
    result = run_screen(module, monkeypatch, THREE_ITEMS)
    assert all(answer["needs_fallback"] for answer in result["answers"].values())
