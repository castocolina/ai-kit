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
