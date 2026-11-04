"""Shared harness for the cross-AI runner template's self-test e2e modules.

The full self-test takes minutes, so it runs as logic and runtime shard modules
(tests/test_cross_ai_selftest_<kind>_<i>_e2e.py), each well inside the commit e2e budget.
Membership is never a hand list: the template lists its cases with their kind
(`cross-ai.mjs --self-test-list`), and split_cases deals each kind into SHARD_COUNTS[kind]
shards, heaviest first, by the per-case seconds in tests/fixtures/cross_ai_selftest_secs.json.
That file is generated: `python3 tests/cross_ai_selftest.py --record-times` (see record_times).

Every session started here is registered for SIGTERM forwarding (setUpModule), so a stopped
module reaps the self-test's detached case runners. tests/test_cross_ai_runner_e2e.py uses the
same harness.
"""

from __future__ import annotations

import contextlib
import importlib.util
import json
import math
import os
import re
import shutil
import signal
import statistics
import subprocess
import sys
import tempfile
import time
import unittest
from collections.abc import Mapping, Sequence

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, "skills", "ai-kit-spec-review"))

from ai_kit_spec.tooling_guidance import resolve_cross_ai_template_path


def _real_node_executable() -> str | None:
    if shutil.which("node") is None:
        return None
    try:
        proc = subprocess.run(
            ["node", "-e", "process.stdout.write(process.execPath)"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return proc.stdout if proc.returncode == 0 and os.path.isfile(proc.stdout) else None


_RESOLVED_TEMPLATE = resolve_cross_ai_template_path()
assert _RESOLVED_TEMPLATE is not None, "the shipped runner template is missing"
TEMPLATE = _RESOLVED_TEMPLATE


def runner_env(tmp: str) -> dict[str, str]:
    """Hermetic env matching cross-ai.mjs --self-test (fakes + node + git + mkfifo only)."""
    bin_dir = os.path.join(tmp, "bin")
    os.makedirs(bin_dir, exist_ok=True)
    node_bin = _real_node_executable()
    git_bin = shutil.which("git")
    # the FIFO cases (overlay-fifo-refused, retry-config-fifo) create their FIFO with mkfifo
    mkfifo_bin = shutil.which("mkfifo")
    if mkfifo_bin:
        link = os.path.join(bin_dir, "mkfifo")
        if not os.path.lexists(link):
            os.symlink(mkfifo_bin, link)
    if node_bin:
        link = os.path.join(bin_dir, "node")
        if not os.path.lexists(link):
            os.symlink(node_bin, link)
    if git_bin:
        link = os.path.join(bin_dir, "git")
        if not os.path.lexists(link):
            os.symlink(git_bin, link)
    # the fake bin stays first; the real node dir is added so a seam whose which_fn reads PATH
    # (the default) still resolves node, while the child itself only ever sees bin_dir
    path = bin_dir
    if node_bin:
        path = bin_dir + os.pathsep + os.path.dirname(node_bin)
    home = os.path.join(tmp, "home")
    os.makedirs(home, exist_ok=True)
    return {
        "PATH": path,
        "HOME": home,
        "XDG_CONFIG_HOME": os.path.join(home, ".config"),
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_AUTHOR_NAME": "xai-selftest",
        "GIT_COMMITTER_NAME": "xai-selftest",
        "GIT_AUTHOR_EMAIL": "xai-selftest@example.invalid",
        "GIT_COMMITTER_EMAIL": "xai-selftest@example.invalid",
        "LANG": "C",
    }


# Each shard run is guarded by a hard limit. The guard and the ceilings it guards are sized from
# ONE load reading (`load_reading`, passed to Node as AIKIT_XAI_SELFTEST_LOAD): a second,
# independently sampled reading (or Python's CPU count against Node's availableParallelism under
# an affinity mask) could differ, so the guard could fire before the ceilings it guards. One shard
# takes about 25 s at idle; 4 x 120 s plus 300 s for the rest of a module stays under the
# runner's 900 s module deadline (DeadlineCouplingTest pins it).
SHARD_GUARD_SECS = 120
MAX_LOAD_FACTOR = 4
SHARD_COUNTS = {"logic": 4, "runtime": 4}
LIST_TIMEOUT_SECS = 60
TIMES_FIXTURE = os.path.join(REPO_ROOT, "tests", "fixtures", "cross_ai_selftest_secs.json")
SHARD_MODULE = "tests.test_cross_ai_selftest_{kind}_{index}_e2e"
_RUNNER_PATH = os.path.join(REPO_ROOT, "tools", "run_unittest_parallel.py")


def _load_runner():
    spec = importlib.util.spec_from_file_location("run_unittest_parallel", _RUNNER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_reading() -> float:
    """One-minute load per CPU over the runner's own CPU count; 0.0 when unreadable."""
    cpus = _load_runner().available_cpus()
    try:
        load = os.getloadavg()[0]
    except OSError:
        return 0.0
    return load / cpus if cpus else 0.0


def load_factor(reading: float) -> float:
    """The reading clamped to 1..MAX_LOAD_FACTOR; 1 for a non-finite or non-positive reading."""
    if not math.isfinite(reading) or reading <= 0:
        return 1.0
    return min(float(MAX_LOAD_FACTOR), max(1.0, reading))


def guard_secs(base: int, factor: float) -> int:
    return math.ceil(base * factor)


def assert_factor_printed(case: unittest.TestCase, stderr: str, reading: float) -> None:
    match = re.search(r"self-test load factor (\S+)\n", stderr)
    assert match is not None, stderr
    case.assertAlmostEqual(float(match.group(1)), load_factor(reading), delta=1e-9)


# The runner stops this module with SIGTERM to its process group (MODULE_STOP_GRACE_SECS = 15 s).
# Each session started here is stopped the same way, so the self-test's selfTestAbort() reaps its
# detached case runners before any hard kill. STOP_GRACE_SECS must stay below the runner's grace.
STOP_GRACE_SECS = 10
_LIVE_GROUPS: set[subprocess.Popen] = set()


def stop_group(proc: subprocess.Popen, grace: float) -> None:
    """SIGTERM to the group of `proc`, up to `grace` seconds to exit, then SIGKILL to the group."""
    with contextlib.suppress(ProcessLookupError):
        os.killpg(proc.pid, signal.SIGTERM)
    with contextlib.suppress(subprocess.TimeoutExpired):
        proc.wait(timeout=grace)
    with contextlib.suppress(ProcessLookupError):
        os.killpg(proc.pid, signal.SIGKILL)


def _forward_sigterm(_signum, _frame) -> None:
    for proc in list(_LIVE_GROUPS):
        stop_group(proc, STOP_GRACE_SECS)
    os._exit(128 + signal.SIGTERM)


def setUpModule() -> None:
    signal.signal(signal.SIGTERM, _forward_sigterm)


def start_group(argv: list[str], **kwargs) -> subprocess.Popen:
    """Start `argv` in a new session and register it for SIGTERM forwarding."""
    proc = subprocess.Popen(
        argv,
        start_new_session=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        **kwargs,
    )
    _LIVE_GROUPS.add(proc)
    return proc


def run_group(argv: list[str], timeout: int, **kwargs) -> subprocess.CompletedProcess:
    """`subprocess.run` in a new session; a timeout stops the whole group (SIGTERM, then SIGKILL),
    not just the leader, so no fake CLI outlives the test."""
    proc = start_group(argv, **kwargs)
    try:
        with proc:
            try:
                out, err = proc.communicate(timeout=timeout)
            except subprocess.TimeoutExpired:
                stop_group(proc, STOP_GRACE_SECS)
                out, err = proc.communicate()
                raise
            return subprocess.CompletedProcess(argv, proc.returncode, out, err)
    finally:
        _LIVE_GROUPS.discard(proc)


def list_cases(template: str = TEMPLATE) -> list[tuple[str, str]]:
    """(name, kind) of every self-test case, in the template's order (`--self-test-list`)."""
    node_bin = _real_node_executable()
    assert node_bin is not None
    with tempfile.TemporaryDirectory() as tmp:
        proc = subprocess.run(
            [node_bin, template, "--self-test-list"],
            cwd=REPO_ROOT,
            env=runner_env(tmp),
            capture_output=True,
            text=True,
            timeout=LIST_TIMEOUT_SECS,
            check=False,
        )
    if proc.returncode != 0:
        raise AssertionError(f"--self-test-list exited {proc.returncode}: {proc.stderr}")
    cases = []
    for line in proc.stdout.splitlines():
        name, kind = line.split("\t")
        cases.append((name, kind))
    return cases


def recorded_secs() -> dict[str, float]:
    """Per-case seconds from TIMES_FIXTURE (written by record_times)."""
    with open(TIMES_FIXTURE, encoding="utf-8") as handle:
        return json.load(handle)


def split_cases(names: Sequence[str], count: int, secs: Mapping[str, float]) -> list[list[str]]:
    """Deal `names` into `count` shards: heaviest first (ties by name) onto the lightest shard
    (lowest index on a tie); each shard's names sorted.

    A name missing from `secs` weighs the median of the known weights among `names` (1.0 when
    none is known). The table only affects balance, never membership: every name lands in exactly
    one shard.
    """
    known = [secs[name] for name in names if name in secs]
    default = statistics.median(known) if known else 1.0
    weight = {name: secs.get(name, default) for name in names}
    shards: list[list[str]] = [[] for _ in range(count)]
    loads = [0.0] * count
    for name in sorted(weight, key=lambda n: (-weight[n], n)):
        index = loads.index(min(loads))
        shards[index].append(name)
        loads[index] += weight[name]
    return [sorted(shard) for shard in shards]


def shard_names(kind: str, index: int) -> list[str]:
    """The case names of shard `index` (1-based) of `kind`."""
    names = [name for name, case_kind in list_cases() if case_kind == kind]
    return split_cases(names, SHARD_COUNTS[kind], recorded_secs())[index - 1]


def run_cases(
    names: Sequence[str],
    template: str = TEMPLATE,
    cwd: str = REPO_ROOT,
    guard_base: int = SHARD_GUARD_SECS,
) -> tuple[subprocess.CompletedProcess, float]:
    """Run the named cases through `--self-test` in one session; (result, the load reading)."""
    node_bin = _real_node_executable()
    assert node_bin is not None
    reading = load_reading()
    with tempfile.TemporaryDirectory() as tmp:
        env = {
            **runner_env(tmp),
            "AIKIT_XAI_SELFTEST_LOAD": repr(reading),
            "AIKIT_XAI_SELFTEST_CASES": ",".join(names),
        }
        proc = run_group(
            [node_bin, template, "--self-test"],
            guard_secs(guard_base, load_factor(reading)),
            cwd=cwd,
            env=env,
        )
    return proc, reading


def shard_case(kind: str, index: int) -> type[unittest.TestCase]:
    """The TestCase that runs shard `index` (1-based) of `kind`, named like LogicShard1Test."""

    class ShardTest(unittest.TestCase):
        @classmethod
        def setUpClass(cls):
            cls._skip = None
            if _real_node_executable() is None:
                cls._skip = "no node executable"
            elif shutil.which("git") is None:
                cls._skip = "git not on PATH"

        def setUp(self):
            if self._skip:
                self.skipTest(self._skip)

        def test_shard(self):
            names = shard_names(kind, index)
            self.assertTrue(names, f"{kind} shard {index} is empty")
            proc, reading = run_cases(names)
            self.assertEqual(proc.returncode, 0, msg=proc.stderr)
            self.assertIn("self-test ok", proc.stdout)
            assert_factor_printed(self, proc.stderr, reading)

    ShardTest.__name__ = ShardTest.__qualname__ = f"{kind.title()}Shard{index}Test"
    return ShardTest


def record_times() -> int:
    """Run every case alone and rewrite TIMES_FIXTURE with its seconds (about 4 minutes).

    Refresh it on a quiet machine after adding a case or making one slower:
    `python3 tests/cross_ai_selftest.py --record-times`. A stale table only unbalances the
    shards; it never drops or duplicates a case.
    """
    secs: dict[str, float] = {}
    for name, _kind in list_cases():
        start = time.monotonic()
        proc, _reading = run_cases([name])
        if proc.returncode != 0:
            raise SystemExit(f"case {name} failed (rc {proc.returncode}):\n{proc.stderr}")
        secs[name] = round(time.monotonic() - start, 2)
    fd, tmp_path = tempfile.mkstemp(
        dir=os.path.dirname(TIMES_FIXTURE), prefix=".cross_ai_selftest_secs-", suffix=".json"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(secs, handle, indent=2, sort_keys=True)
            handle.write("\n")
        os.replace(tmp_path, TIMES_FIXTURE)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(tmp_path)
        raise
    print(f"recorded {len(secs)} cases in {TIMES_FIXTURE}")
    return 0


if __name__ == "__main__":
    if sys.argv[1:] != ["--record-times"]:
        sys.exit("usage: python3 tests/cross_ai_selftest.py --record-times")
    setUpModule()
    sys.exit(record_times())
