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
