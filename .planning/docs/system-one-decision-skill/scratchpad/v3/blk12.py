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
