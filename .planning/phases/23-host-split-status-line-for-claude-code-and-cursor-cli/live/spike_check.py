#!/usr/bin/env python3
"""Owner-only scaffolding, never shipped or linked. Run with --self-test, --record MD or DIR."""

import argparse
import json
import math
import pathlib
import re
import sys

TOKEN_PATTERNS = (re.compile(r"eyJ[A-Za-z0-9_-]{12,}"), re.compile(r"Bearer\s+\S+"),
                  re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}"),
                  re.compile(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F-]{27,}\b"))


def percentile(values: list[float], pct: float) -> float:
    ordered = sorted(values)
    return ordered[max(0, math.ceil(len(ordered) * pct) - 1)]


def decision(concurrent_p95: float, render_p95: float, shortest_gap: float) -> str:
    total = concurrent_p95 + render_p95
    return "inline" if total < shortest_gap and total < 300 else "refresher"


def redaction_problems(value) -> list[str]:
    text = json.dumps(value, sort_keys=True)
    return [pattern.pattern for pattern in TOKEN_PATTERNS if pattern.search(text)]


def redact(value):
    if isinstance(value, dict):
        return {key: redact(item) for key, item in value.items()}
    if isinstance(value, list):
        return [redact(item) for item in value]
    return "<redacted>" if isinstance(value, str) else value


def check_bundle(directory: pathlib.Path) -> list[str]:
    problems = []
    payloads = list((directory / "responses").glob("*.json"))
    for path in payloads:
        try:
            body = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            problems.append(f"invalid JSON: {path.name}")
            continue
        problems.extend(f"sensitive data: {item}" for item in redaction_problems(body))
    timings = json.loads((directory / "timings.json").read_text(encoding="utf-8"))
    samples = timings.get("concurrent_ms", [])
    gaps = timings.get("update_gaps_ms", [])
    if not samples or not gaps:
        problems.append("missing latency or cadence samples")
    return problems


def record_problems(path: pathlib.Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    results = []
    table = False
    for line in text.splitlines():
        if line.strip() == "## Results":
            table = True
            continue
        if table and line.startswith("## "):
            break
        if (table and line.startswith("|") and line.count("|") == 4
                and ("not run (owner)" in line or "| pass |" not in line)):
            results.append(line.strip())
    return results


def self_test() -> None:
    token = "eyJ" + "syntheticpayloadvalue" + "." + "payload" + ".signature"
    assert redaction_problems({"token": token})
    assert redaction_problems({"auth": "Bearer " + "synthetic"})
    assert redaction_problems({"email": "person@example.test"})
    assert redaction_problems({"id": "123e4567-e89b-12d3-a456-426614174000"})
    assert percentile([1, 2, 3, 4, 5], 0.5) == 3
    assert percentile([1, 2, 3, 4, 5], 0.95) == 5
    assert decision(1921, 40, 300) == "refresher"
    assert decision(10, 20, 100) == "inline"
    print("self-test ok")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", nargs="?", type=pathlib.Path)
    parser.add_argument("--record", type=pathlib.Path)
    parser.add_argument("--promote", type=pathlib.Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        self_test()
        return 0
    if args.record:
        pending = record_problems(args.record)
        if pending:
            for line in pending:
                print(line)
            return 1
        return 0
    if args.promote:
        problems = check_bundle(args.promote)
        if problems:
            print("\n".join(problems), file=sys.stderr)
            return 1
        destination = pathlib.Path(__file__).resolve().parents[4]
        destination /= "tests" / "fixtures" / "cursor" / "dashboard_real"
        destination.mkdir(parents=True, exist_ok=True)
        for source in (args.promote / "responses").glob("*.json"):
            body = json.loads(source.read_text(encoding="utf-8"))
            (destination / source.name).write_text(
                json.dumps(redact(body), indent=2) + "\\n", encoding="utf-8")
        return 0
    if args.path:
        problems = check_bundle(args.path)
        if problems:
            print("\n".join(problems), file=sys.stderr)
            return 1
        timings = json.loads((args.path / "timings.json").read_text(encoding="utf-8"))
        print("decision: " + decision(percentile(timings["concurrent_ms"], .95),
                                       percentile(timings["render_ms"], .95),
                                       min(timings["update_gaps_ms"])))
        return 0
    parser.error("provide DIR, --record MD, --promote DIR, or --self-test")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
