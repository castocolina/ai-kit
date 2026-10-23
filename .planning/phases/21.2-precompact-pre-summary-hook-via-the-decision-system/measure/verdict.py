#!/usr/bin/env python3
"""Per-host precompact verdict from runs.jsonl (21.2 SPEC R9).

Rule: `positive` only when every hooked time is strictly lower than every
baseline time and the median hooked post-compaction size is not larger;
otherwise `non-positive` (a saving of exactly zero included). Fewer than 3
runs in either arm gives `unmeasured`. Mixed size units within a host, or a
baseline run later than a hooked run, are errors naming the host (exit 2).
"""
import json
import os
import statistics
import sys

HOSTS = ("claude", "pi", "opencode")
MIN_RUNS = 3


def _load_runs(path):
    runs = []
    if not os.path.exists(path):
        return runs
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                runs.append(json.loads(line))
    return runs


def _host_verdict(runs):
    """Apply the R9 rule to one host's runs; raise ValueError on a bad record set."""
    arms = {}
    for run in runs:
        arms.setdefault(run["arm"], []).append(run)
    if any(len(arm) < MIN_RUNS for arm in arms.values()) or set(arms) != {"baseline", "hooked"}:
        return "unmeasured"
    if len({run["size_unit"] for run in runs}) > 1:
        raise ValueError("mixed size_unit values")
    base_ts = sorted(run["ts"] for run in arms["baseline"])
    hooked_ts = sorted(run["ts"] for run in arms["hooked"])
    if base_ts[-1] > hooked_ts[0]:
        raise ValueError("a baseline run is later than a hooked run")
    base_times = [run["seconds"] for run in arms["baseline"]]
    hooked_times = [run["seconds"] for run in arms["hooked"]]
    base_size = statistics.median(run["size"] for run in arms["baseline"])
    hooked_size = statistics.median(run["size"] for run in arms["hooked"])
    if all(h < b for h in hooked_times for b in base_times) and hooked_size <= base_size:
        return "positive"
    return "non-positive"


def _self_test():
    def run(arm, n, ts0, seconds, size, unit="tokens"):
        return [{"arm": arm, "ts": f"2026-01-01T00:00:{ts0 + i:02d}Z",
                 "seconds": seconds, "size": size, "size_unit": unit} for i in range(n)]

    ok = _host_verdict(run("baseline", 3, 0, 10.0, 500) + run("hooked", 3, 30, 5.0, 400))
    assert ok == "positive", ok
    zero = _host_verdict(run("baseline", 3, 0, 5.0, 500) + run("hooked", 3, 30, 5.0, 400))
    assert zero == "non-positive", zero
    unmeasured = _host_verdict(run("baseline", 2, 0, 10.0, 500) + run("hooked", 3, 30, 5.0, 400))
    assert unmeasured == "unmeasured", unmeasured
    try:
        _host_verdict(run("baseline", 3, 0, 10.0, 500) + run("hooked", 3, 30, 5.0, 400, unit="chars"))
        raise AssertionError("mixed units did not raise")
    except ValueError as exc:
        assert "size_unit" in str(exc)
    try:
        _host_verdict(run("baseline", 3, 40, 10.0, 500) + run("hooked", 3, 30, 5.0, 400))
        raise AssertionError("late baseline did not raise")
    except ValueError as exc:
        assert "later than a hooked run" in str(exc)
    print("self-test ok")


def main(argv):
    if "--self-test" in argv:
        _self_test()
        return 0
    runs_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "runs.jsonl")
    runs = _load_runs(runs_path)
    for host in HOSTS:
        host_runs = [run for run in runs if run.get("host") == host]
        try:
            print(f"{host}: {_host_verdict(host_runs)}")
        except ValueError as exc:
            print(f"error: {host}: {exc}", file=sys.stderr)
            return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
