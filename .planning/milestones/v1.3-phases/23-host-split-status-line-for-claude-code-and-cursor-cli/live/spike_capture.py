#!/usr/bin/env python3
"""Owner-only scaffolding, never shipped or linked. Run with --out DIR [--sleep-ms N]."""

import argparse
import json
import pathlib
import signal
import sys
import time

_ACTIVE: dict[str, object] = {}


def _finish(_signum, _frame):
    now = int(time.time() * 1000)
    record = {"start_ms": _ACTIVE.get("start_ms"), "end_ms": now, "killed": True}
    path = pathlib.Path(_ACTIVE["out"]) / "runs.jsonl"
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record) + "\n")
    raise SystemExit(143)


def capture(out: pathlib.Path, sleep_ms: int) -> None:
    started = int(time.time() * 1000)
    _ACTIVE.update(out=str(out), start_ms=started)
    out.mkdir(parents=True, exist_ok=True)
    payload_dir = out / "payloads"
    payload_dir.mkdir(exist_ok=True)
    payload = sys.stdin.buffer.read()
    (payload_dir / f"{started}.json").write_bytes(payload)
    if sleep_ms:
        time.sleep(sleep_ms / 1000)
    record = {"start_ms": started, "end_ms": int(time.time() * 1000), "killed": False}
    with (out / "runs.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record) + "\n")
    print("captured Cursor payload")


def self_test() -> None:
    import io
    import tempfile

    with tempfile.TemporaryDirectory() as directory:
        target = pathlib.Path(directory)
        previous_stdin = sys.stdin
        sys.stdin = io.TextIOWrapper(io.BytesIO(b'{"synthetic":true}'))
        capture(target / "out", 0)
        sys.stdin.close()
        sys.stdin = previous_stdin
        saved = next((target / "out" / "payloads").glob("*.json"))
        assert json.loads(saved.read_text()) == {"synthetic": True}
        run = json.loads((target / "out" / "runs.jsonl").read_text().splitlines()[0])
        assert run["end_ms"] >= run["start_ms"] and not run["killed"]
    print("self-test ok")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=pathlib.Path)
    parser.add_argument("--sleep-ms", type=int, default=0)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    if args.out is None or args.sleep_ms < 0:
        parser.error("--out is required and --sleep-ms must be non-negative")
    signal.signal(signal.SIGTERM, _finish)
    capture(args.out, args.sleep_ms)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
