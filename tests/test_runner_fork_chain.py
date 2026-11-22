"""A `node` that runs itself again is bounded by the runner reads' timeouts.

Volta's `node` shim, under a HOME without Volta's toolchain, runs `node` from PATH, which is the
shim itself: an endless parent-to-child chain. The runner's `--describe` and `--print-argv` reads
must return no answer within their timeout and leave no process behind. The fake shim below
stops forking after CHAIN_LINKS links (a counter file) and then hangs, so this test can never
flood the host itself.
"""
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

_REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(_REPO_ROOT, "skills", "ai-kit-spec-review"))

from ai_kit_spec import detection, runner_dispatch, runner_facts

CHAIN_LINKS = 5
SHORT_TIMEOUT_S = 2
REAP_WAIT_S = 30
SHIM = """#!/bin/sh
dir=${0%/*}
n=$(cat "$dir/count" 2>/dev/null || echo 0)
n=$((n + 1))
echo "$n" > "$dir/count"
echo "$$" >> "$dir/pids"
if [ "$n" -lt LINKS ]; then "$0" "$@"; exit $?; fi
exec sleep 60
""".replace("LINKS", str(CHAIN_LINKS))


def _alive(pid: int) -> bool:
    """A live, non-zombie process."""
    try:
        with open(f"/proc/{pid}/stat", encoding="utf-8") as handle:
            return handle.read().rsplit(")", 1)[1].split()[0] != "Z"
    except (OSError, IndexError):
        return False


@unittest.skipUnless(os.path.isdir("/proc") and hasattr(os, "killpg"), "needs /proc and killpg")
class TestSelfRunningNodeShim(unittest.TestCase):
    def setUp(self):
        self.bin = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.bin, ignore_errors=True)
        self.addCleanup(self._kill_leftovers)
        shim = self.bin / "node"
        shim.write_text(SHIM, encoding="utf-8")
        shim.chmod(0o755)
        path = os.pathsep.join([str(self.bin), os.environ.get("PATH", "")])
        patcher = mock.patch.dict(os.environ, {"PATH": path})
        patcher.start()
        self.addCleanup(patcher.stop)

    def _pids(self) -> list[int]:
        pids = self.bin / "pids"
        return [int(line) for line in pids.read_text().split()] if pids.exists() else []

    def _kill_leftovers(self):
        for pid in self._pids():
            try:
                cmdline = Path(f"/proc/{pid}/cmdline").read_bytes()
            except OSError:
                continue
            if str(self.bin).encode() in cmdline or cmdline == b"sleep\x0060\x00":
                os.kill(pid, signal.SIGKILL)

    def assert_bounded_and_gone(self, started: float):
        self.assertLess(time.monotonic() - started, SHORT_TIMEOUT_S + 10)
        self.assertEqual((self.bin / "count").read_text().strip(), str(CHAIN_LINKS))
        # Killed links can take seconds to exit under a loaded, swapping host: wait, bounded.
        deadline = time.monotonic() + REAP_WAIT_S
        while any(_alive(pid) for pid in self._pids()) and time.monotonic() < deadline:
            time.sleep(0.05)
        self.assertEqual([pid for pid in self._pids() if _alive(pid)], [])

    def test_describe_read_returns_no_fact_and_leaves_no_process(self):
        snapshot: dict = {}
        started = time.monotonic()
        with mock.patch.object(runner_facts, "DESCRIBE_TIMEOUT_S", SHORT_TIMEOUT_S):
            # The production seams: shutil.which finds the shim, subprocess.run is the real one.
            self.assertTrue(runner_facts.refresh_fact(snapshot, shutil.which, subprocess.run))
        self.assertIsNone(snapshot["runner"]["describe"])
        self.assert_bounded_and_gone(started)

    def test_print_argv_preview_returns_none_and_leaves_no_process(self):
        spec = runner_dispatch.RunnerSpec("pi", "placeholder-model-1", "review", 30,
                                          cwd=str(self.bin))
        started = time.monotonic()
        with mock.patch.object(runner_dispatch, "PREVIEW_TIMEOUT_S", SHORT_TIMEOUT_S):
            self.assertIsNone(runner_dispatch.print_argv_lines(spec))
        self.assert_bounded_and_gone(started)


class TestRunInOwnGroup(unittest.TestCase):
    def test_keeps_the_subprocess_run_contract(self):
        done = detection.run_in_own_group(["sh", "-c", "echo out; echo err >&2"],
                                          capture_output=True, text=True, timeout=10)
        self.assertEqual((done.returncode, done.stdout, done.stderr), (0, "out\n", "err\n"))
        with self.assertRaises(subprocess.CalledProcessError):
            detection.run_in_own_group(["sh", "-c", "exit 3"], timeout=10, check=True)

    def test_only_the_real_run_is_swapped(self):
        def fake(*_args, **_kwargs):
            return None
        self.assertIs(detection.bounded_run(subprocess.run), detection.run_in_own_group)
        self.assertIs(detection.bounded_run(fake), fake)
        with mock.patch("subprocess.run") as patched:
            self.assertIs(detection.bounded_run(patched), patched)


if __name__ == "__main__":
    unittest.main()
