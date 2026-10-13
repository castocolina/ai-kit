#!/usr/bin/env python3
"""Run unittest modules in parallel, one subprocess per module.

Usage: run_unittest_parallel.py tests.test_a tests.test_b ...

Each module runs under the same interpreter as this script, so the caller picks
the runtime (system python3 or `uv run python`). Output is buffered per module and
printed whole, so failures never interleave. Exits 1 if any module fails.
"""
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed


def run_module(module: str) -> tuple[str, int, str, float]:
    start = time.monotonic()
    proc = subprocess.run(
        [sys.executable, "-m", "unittest", module],
        capture_output=True, text=True, check=False,
    )
    return module, proc.returncode, proc.stdout + proc.stderr, time.monotonic() - start


def main(modules: list[str]) -> int:
    if not modules:
        print("usage: run_unittest_parallel.py MODULE [MODULE ...]", file=sys.stderr)
        return 2
    failed: list[str] = []
    with ThreadPoolExecutor(max_workers=min(len(modules), os.cpu_count() or 4)) as pool:
        for fut in as_completed([pool.submit(run_module, m) for m in modules]):
            module, rc, output, secs = fut.result()
            ran = next((ln for ln in output.splitlines() if ln.startswith("Ran ")), "")
            status = "ok" if rc == 0 else f"FAILED (rc={rc})"
            print(f"=== {module}: {status} in {secs:.1f}s  {ran}")
            if rc != 0:
                failed.append(module)
                print(output)
    print(f"{len(modules) - len(failed)}/{len(modules)} modules passed")
    if failed:
        print("failed: " + " ".join(sorted(failed)))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
