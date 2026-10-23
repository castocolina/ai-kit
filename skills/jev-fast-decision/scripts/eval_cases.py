#!/usr/bin/env python3
"""Score labelled cases through screen(). Stdlib only.

One `screen()` call per case in `evals/cases.jsonl` (the kill switch applies: with
`GSD_PATH_JEV` unset the script prints the disabled result and sends nothing). Metrics print
only when all 32 cases came back `ok`; results are written only to the explicit path given
with `--record PATH`, never inside the skill directory. `--calibrate PATH` reads a recorded
results file, proposes each backend's threshold, and rewrites that backend's own
`min_confidence` number in `scripts/jev_review.py` — located with `ast` inside the `TABLE`
assignment, so another row's threshold can never change; a row that is not a dict literal, or
that lacks or repeats the key, exits non-zero before anything is written.

Every saved case carries the client's own `needs_fallback` flag and the answering `backend`
beside `id`, `top`, `correct` and `ambiguous`, so a recorded `fallback_rate` can be re-derived
from the file alone.
"""

from __future__ import annotations

import ast
import importlib.util
import io
import json
import math
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
CASES = ROOT / "evals" / "cases.jsonl"
SCRIPT = ROOT / "scripts" / "jev_review.py"


def _review():
    spec = importlib.util.spec_from_file_location("jev_review_eval", str(SCRIPT))
    assert spec is not None and spec.loader is not None
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
    text = CASES.read_text(encoding="utf-8")
    return [json.loads(line) for line in text.splitlines() if line.strip()]


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
    return {"backend": records[0]["backend"], "n": n, "accuracy": accuracy,
            "fallback_rate": flagged / n, "accuracy_when_not_fallback": kept}


def merge_results(existing: dict, backend: str, cases: list[dict]) -> dict:
    kept = [entry for entry in existing.get("results", []) if entry.get("backend") != backend]
    kept.append({"backend": backend, "cases": cases})
    kept.sort(key=lambda entry: entry["backend"])
    return {**existing, "results": kept}


def calibrate(cases: list[dict]) -> float | None:
    """The lowest threshold that keeps >= 0.95 accuracy on >= max(10, 30% of n) cases.

    Ambiguous rows stay in `n` and in the fallback count but never in the accuracy; among
    qualifying thresholds the lowest wins, ties broken by the lower fallback rate.
    """
    n = len(cases)
    if n == 0:
        return None
    qualifiers: list[tuple[float, float]] = []
    for step in range(10):
        threshold = round(0.50 + 0.05 * step, 2)
        not_fallback = [case for case in cases if case["top"] >= threshold]
        fallback_rate = 1 - len(not_fallback) / n
        clear = [case for case in not_fallback if not case.get("ambiguous", False)]
        accuracy = (sum(case["correct"] for case in clear) / len(clear)) if clear else 0
        if accuracy >= 0.95 and len(not_fallback) >= max(10, math.ceil(0.3 * n)):
            qualifiers.append((threshold, fallback_rate))
    qualifiers.sort()
    return qualifiers[0][0] if qualifiers else None


def _table_min_confidence_span(source: str, backend: str):
    """The (lineno, col_offset, end_col_offset) of one row's `min_confidence` value.

    The row is found with `ast` inside the module-level `TABLE` assignment: the dict literal
    whose `"name"` value is `backend`, holding exactly one `"min_confidence"` key whose value
    is a number constant on a single line. Anything else — no such row, a row that is not a
    dict literal, zero or two such keys, a non-number or multi-line value — raises `LookupError`
    before any caller writes a byte (T-21.1-31).
    """
    tree = ast.parse(source)
    assignments = [node for node in tree.body
                   if (isinstance(node, ast.Assign)
                       and any(isinstance(target, ast.Name) and target.id == "TABLE"
                               for target in node.targets))
                   or (isinstance(node, ast.AnnAssign)
                       and isinstance(node.target, ast.Name) and node.target.id == "TABLE")]
    values = [(node.value if isinstance(node.value, ast.Tuple) else None)
              for node in assignments]
    if len(values) != 1 or values[0] is None:
        raise LookupError("TABLE assignment not found")
    spans = []
    for element in values[0].elts:
        if not (isinstance(element, ast.Dict) and element.keys
                and all(isinstance(key, ast.Constant) for key in element.keys)):
            continue
        names = [index for index, key in enumerate(element.keys)
                 if isinstance(key, ast.Constant) and key.value == "name"]
        row_name = None
        if len(names) == 1:
            candidate = element.values[names[0]]
            if isinstance(candidate, ast.Constant):
                row_name = candidate.value
        if row_name != backend:
            continue
        positions = [index for index, key in enumerate(element.keys)
                     if isinstance(key, ast.Constant) and key.value == "min_confidence"]
        if len(positions) != 1:
            raise LookupError(f"{backend}: min_confidence key found {len(positions)} times")
        value = element.values[positions[0]]
        if (not isinstance(value, ast.Constant)
                or not isinstance(value.value, (int, float))
                or value.lineno != value.end_lineno):
            raise LookupError(f"{backend}: min_confidence value is not a single-line number")
        spans.append((value.lineno, value.col_offset, value.end_col_offset))
    if len(spans) != 1:
        raise LookupError(f"{backend}: row not found as a dict literal")
    return spans[0]


def rewrite_min_confidence(source: str, winners: dict) -> str:
    """The source with each winning row's `min_confidence` number replaced in place."""
    lines = source.splitlines(keepends=True)
    for backend, winner in winners.items():
        lineno, start, end = _table_min_confidence_span(source, backend)
        line = lines[lineno - 1]
        lines[lineno - 1] = line[:start] + repr(winner) + line[end:]
    return "".join(lines)


def _flag_value(name: str) -> str | None:
    if name in sys.argv:
        index = sys.argv.index(name)
        if index + 1 < len(sys.argv):
            return sys.argv[index + 1]
    return None


def _run_calibration(results_path: pathlib.Path) -> int:
    if not results_path.exists():
        print(f"results file missing: {results_path}", file=sys.stderr)
        return 1
    doc = json.loads(results_path.read_text(encoding="utf-8"))
    proposed = {entry["backend"]: calibrate(entry["cases"])
                for entry in doc.get("results", [])}
    print(json.dumps({"JEV_MIN_CONFIDENCE": proposed}, sort_keys=True))
    source = SCRIPT.read_text(encoding="utf-8")
    winners = {backend: winner for backend, winner in proposed.items() if winner is not None}
    try:
        updated = rewrite_min_confidence(source, winners)
    except LookupError as problem:
        print(f"not rewriting: {problem}", file=sys.stderr)
        return 1
    for backend, winner in proposed.items():
        if winner is None:
            print(f"{backend}: no qualifying threshold; keep the current value and say why in "
                  f"backends/{backend}.md", file=sys.stderr)
    SCRIPT.write_text(updated, encoding="utf-8")
    return 0


def main() -> int:
    calibrate_path = _flag_value("--calibrate")
    if calibrate_path:
        return _run_calibration(pathlib.Path(calibrate_path))
    record_path = _flag_value("--record")
    review = _review()
    records: list[dict] = []
    cases_out: list[dict] = []
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
                          "correct": record["correct"], "ambiguous": record["ambiguous"],
                          "needs_fallback": record["needs_fallback"],
                          "backend": record["backend"]})
    report = summarize(records)
    if report["n"] != 32:
        return 1
    print(json.dumps(report, sort_keys=True))
    if record_path and report["backend"]:
        path = pathlib.Path(record_path)
        existing = (json.loads(path.read_text(encoding="utf-8"))
                    if path.exists() else {"results": []})
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = merge_results(existing, report["backend"], cases_out)
        path.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n",
                        encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
