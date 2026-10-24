#!/usr/bin/env python3
"""Owner-only Dashboard probe; self-test never reads credentials or accesses the network."""

import argparse
import json
import pathlib
import sys
import tempfile
import time

ROOT = pathlib.Path(__file__).resolve().parents[4]


def load_quota_module():
    sys.path.insert(0, str(ROOT / "tools"))
    import cursor_quota

    return cursor_quota


cursor_quota = load_quota_module()


def self_test() -> None:
    """Exercise timing/redaction output with canned production-seam responses."""
    calls = []

    def canned_fetch(base, token, opener, timeout_s):
        calls.append((base, timeout_s))
        return cursor_quota.FetchResult(
            {"planUsage": {"totalPercentUsed": 25}}, {}, {"planInfo": {}}, None)

    with tempfile.TemporaryDirectory() as directory:
        config = pathlib.Path(directory) / "config" / "cursor"
        config.mkdir(parents=True)
        synthetic = "synthetic-" + "only-token"
        (config / "auth.json").write_text(json.dumps({"accessToken": synthetic}),
                                           encoding="utf-8")
        env = {"HOME": directory, "XDG_CONFIG_HOME": str(config.parent),
               "CURSOR_API_ENDPOINT": "https://api2.cursor.sh"}
        started = time.monotonic()
        data, error, diagnostic = cursor_quota.probe_fetch_quota(env, fetch=canned_fetch)
        elapsed = (time.monotonic() - started) * 1000
        assert error is None and diagnostic == "" and data is not None
        assert data["included_pct"] == 25 and len(calls) == 1
        evidence = {"result": "ok", "error": error, "diagnostic": diagnostic,
                    "elapsed_ms": elapsed, "sequential_ms": [elapsed],
                    "concurrent_ms": [elapsed], "methods": 3}
        encoded = json.dumps(evidence, sort_keys=True)
        assert synthetic not in encoded and "Bearer" not in encoded
        print(json.dumps(evidence, sort_keys=True))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--out", type=pathlib.Path)
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    if args.out is None:
        parser.error("--out is required outside self-test")
    started = time.monotonic()
    data, error, diagnostic = cursor_quota.probe_fetch_quota(dict(__import__("os").environ))
    evidence = {"result": "ok" if error is None else error, "diagnostic": diagnostic,
                "elapsed_ms": (time.monotonic() - started) * 1000,
                "data": data}
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "evidence.json").write_text(json.dumps(evidence, sort_keys=True) + "\n",
                                             encoding="utf-8")
    print(json.dumps({key: value for key, value in evidence.items() if key != "data"},
                     sort_keys=True))
    return 0 if error is None else 1


if __name__ == "__main__":
    raise SystemExit(main())
