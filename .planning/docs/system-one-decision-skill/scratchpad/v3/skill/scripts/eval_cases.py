#!/usr/bin/env python3
"""Score labeled cases through screen(). Stdlib only."""
from __future__ import annotations

import importlib.util
import io
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
CASES = ROOT / "evals" / "cases.jsonl"
RESULTS = ROOT / "notes" / "eval-results.json"


def _review():
    spec = importlib.util.spec_from_file_location("jev_review", ROOT / "scripts" / "jev_review.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def qtype_of(item: dict) -> str:
    if set(item) == {"id", "criterion", "evidence"}:
        return "choice"
    return item["type"]


def case_correct(answer: dict, expected, qtype: str) -> bool:
    if qtype == "choice":
        return answer["choice"] == expected
    if qtype == "noul":
        return (answer["noul"] > 0.5) == expected
    if qtype == "score":
        return round(answer["score"]) == expected
    raise ValueError(qtype)


def case_record(item_id: str, answer: dict, expected, qtype: str) -> dict:
    top = (max(answer["noul"], 1 - answer["noul"]) if qtype == "noul"
           else max(answer["probabilities"].values()))
    return {"id": item_id, "top": top, "correct": case_correct(answer, expected, qtype)}


def load_cases() -> list[dict]:
    return [json.loads(line) for line in CASES.read_text(encoding="utf-8").splitlines() if line.strip()]


def summarize(records: list[dict]) -> dict:
    n = len(records)
    if n == 0:
        return {"backend": None, "n": 0, "accuracy": 0, "fallback_rate": 0,
                "accuracy_when_not_fallback": 0}
    clear = [row for row in records if not row.get("ambiguous")]
    not_fb = [row for row in clear if not row["needs_fallback"]]
    flagged = sum(1 for row in records if row["needs_fallback"])
    kept = sum(row["correct"] for row in not_fb) / len(not_fb) if not_fb else 0.0
    accuracy = sum(row["correct"] for row in clear) / len(clear) if clear else 0.0
    return {"backend": records[0]["backend"], "n": n,
            "accuracy": accuracy,
            "fallback_rate": flagged / n,
            "accuracy_when_not_fallback": kept}


def merge_results(existing: dict, backend: str, cases: list[dict]) -> dict:
    kept = [entry for entry in existing.get("results", []) if entry.get("backend") != backend]
    kept.append({"backend": backend, "cases": cases})
    kept.sort(key=lambda entry: entry["backend"])
    return {**existing, "results": kept}


def calibrate(cases: list[dict]) -> float | None:
    import math
    n = len(cases)
    if n == 0:
        return None
    qualifiers = []
    for step in range(10):
        threshold = round(0.50 + 0.05 * step, 2)
        not_fallback = [case for case in cases if case["top"] >= threshold]
        fallback_rate = 1 - len(not_fallback) / n
        clear = [case for case in not_fallback if not case.get("ambiguous", False)]
        accuracy = sum(case["correct"] for case in clear) / len(clear) if clear else 0
        if accuracy >= 0.95 and len(not_fallback) >= max(10, math.ceil(0.3 * n)):
            qualifiers.append((threshold, fallback_rate))
    qualifiers.sort()
    return qualifiers[0][0] if qualifiers else None


def main() -> int:
    if "--calibrate" in sys.argv:
        import re
        if not RESULTS.exists():
            print("notes/eval-results.json missing; Task 5 aborted", file=sys.stderr)
            return 1
        doc = json.loads(RESULTS.read_text(encoding="utf-8"))
        proposed = {e["backend"]: calibrate(e["cases"]) for e in doc.get("results", [])}
        print(json.dumps({"JEV_MIN_CONFIDENCE": proposed}, sort_keys=True))
        path = ROOT / "scripts" / "jev_review.py"
        text = path.read_text(encoding="utf-8")
        for backend, winner in proposed.items():
            if winner is None:
                print(f"{backend}: leave 0.7; say why in backends/{backend}.md", file=sys.stderr)
                continue
            text, n = re.subn(rf'("{backend}": \{{.*?"min_confidence": )\d+(?:\.\d+)?', rf"\g<1>{winner}", text, count=1, flags=re.S)
            if n != 1: raise SystemExit(backend)
        path.write_text(text, encoding="utf-8")
        return 0
    review = _review()
    records, cases_out = [], []
    for row in load_cases():
        item = row["item"]
        qtype = qtype_of(item)
        sys.stdin = io.StringIO(json.dumps({"reviewed_head": "0" * 40, "items": [item]}))
        result = review.screen()
        if result.get("status") == "disabled":
            print(json.dumps(result, sort_keys=True))
            return 0
        if result.get("status") != "ok":
            print(json.dumps({"id": item["id"], "reason": result.get("reason"),
                              "status": result.get("status")}, sort_keys=True), file=sys.stderr)
            return 1
        answer = result["answers"][item["id"]]
        record = case_record(item["id"], answer, row["expected"], qtype)
        record["needs_fallback"] = bool(answer["needs_fallback"])
        record["backend"] = result["backend"]
        record["ambiguous"] = bool(row["ambiguous"])
        records.append(record)
        cases_out.append({"id": record["id"], "top": record["top"],
                           "correct": record["correct"], "ambiguous": record["ambiguous"]})
    report = summarize(records)
    if report["n"] != 32:
        return 1
    print(json.dumps(report, sort_keys=True))
    if "--record" in sys.argv and report["backend"]:
        existing = json.loads(RESULTS.read_text()) if RESULTS.exists() else {"results": []}
        RESULTS.parent.mkdir(parents=True, exist_ok=True)
        payload = merge_results(existing, report["backend"], cases_out)
        RESULTS.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
