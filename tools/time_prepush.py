#!/usr/bin/env python3
"""Times the pre-push hooks the way the 2026-11-03 before time was taken (SPEC R3; D-14).

The two test hooks (`unittest`, then `unittest-wizard`) run back to back; their summed wall time
is the test-hook subtotal the 60 s target covers. The other four pre-push hooks (`pyright`,
`vulture`, `check-dogfood`, `deferred-e2e`) run one at a time after them and are recorded beside
the subtotal, never inside it. `push-worst` is the sum of all six timed alone: the worst-case
whole push the owner can wait.

The commands are read from `.pre-commit-config.yaml`, so they cannot drift from the hooks. Each
hook runs in a fresh scratch HOME with the caller's tool caches forwarded and no inherited
`AI_KIT_TEST_CPU_SHARE` (the default 40 % share applies). The check-dogfood hook alone keeps the
caller's GSD_HOME (else the caller's HOME), where gsd-core finds the project's capability consent.
The verdict reads the per-module reports of each test hook: a failed, missing, unexpected,
duplicated or all-skipped module, or a total that differs from the inventory, makes the run
`invalid`, however fast it was.

Usage: python3 tools/time_prepush.py   (prints one `push-timing` record line; exit 0 only when
the verdict is `pass` and every auxiliary hook exited 0)
"""

import datetime
import importlib.util
import os
import re
import shlex
import subprocess
import sys
import tempfile
import time
from collections.abc import Mapping
from pathlib import Path
from types import ModuleType
from typing import NamedTuple

TOOLS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TOOLS_DIR.parent
TEST_HOOK_LIMIT_SECS = 60.0
TEST_HOOKS = ("unittest", "unittest-wizard")
AUXILIARY_HOOKS = ("pyright", "vulture", "check-dogfood", "deferred-e2e")
# Modules that skip every test by design under their hook's interpreter, with the reason.
# Empty unless the all-skip scan finds a case (28-09 Task 1 step 1).
ALL_SKIP_OK: dict[str, str] = {}
# Variables the timing run must not inherit: a lower CPU share would change the worker count,
# and the push refs would make deferred-e2e narrow to a range (its worst case is the no-range run).
# GSD_HOME reaches the check-dogfood hook alone (see `_timed`).
DROPPED_ENV = ("AI_KIT_TEST_CPU_SHARE", "PRE_COMMIT_FROM_REF", "PRE_COMMIT_TO_REF", "GSD_HOME")
SUMMARY_RE = re.compile(r"(\d+)/(\d+) modules passed")
OUTPUT_TAIL_LINES = 30


def _load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


env_matrix = _load_module("env_matrix", TOOLS_DIR / "env_matrix.py")
runner = env_matrix.runner


class HookRun(NamedTuple):
    """One timed hook: its exit code, wall seconds, the `N/M modules passed` summary, the
    problems that make a test hook's run invalid, and the number of skipped tests."""

    name: str
    rc: int
    secs: float
    passed: int
    total: int
    problems: tuple[str, ...]
    skipped: int


def hook_command(config_text: str, hook_id: str) -> list[str]:
    """The argv of one hook's `entry:`, read from the config, cut before `--` (the listing)."""
    lines = config_text.splitlines()
    for index, line in enumerate(lines):
        if line.strip() != f"- id: {hook_id}":
            continue
        for later in lines[index + 1:]:
            if later.strip().startswith("- id:"):
                break
            if later.strip().startswith("entry:"):
                argv = shlex.split(later.split("entry:", 1)[1].strip())
                return argv[:argv.index("--")] if "--" in argv else argv
    raise ValueError(f"hook {hook_id} has no entry in the pre-commit config")


def hook_env(source: Mapping[str, str], home: Path, report_dir: Path | None) -> dict[str, str]:
    """The environment of one timed hook: the caller's env minus the dropped names, the tool
    caches forwarded from the caller's HOME (computed before HOME is replaced), a fresh HOME
    with AI_KIT_REFUSE_REAL_HOME=1, and the report folder of a test hook when given."""
    env = {key: value for key, value in source.items() if key not in DROPPED_ENV}
    env.update(runner.tool_cache_forwards(source))
    env["HOME"] = str(home)
    env["AI_KIT_REFUSE_REAL_HOME"] = "1"
    env.pop(runner.REPORT_DIR_ENV, None)
    if report_dir is not None:
        env[runner.REPORT_DIR_ENV] = str(report_dir)
    return env


def _summary(output: str) -> tuple[int, int]:
    """The last `N/M modules passed` line, or 0/0 when the hook printed none."""
    found = SUMMARY_RE.findall(output)
    return (int(found[-1][0]), int(found[-1][1])) if found else (0, 0)


def _module_problems(
    name: str, rc: int, reports: dict, duplicates: list[str], expected: set[str]
) -> list[str]:
    """Why a test hook's reports cannot be an after time; [] only for a complete, green run."""
    problems = [f"{name} exited {rc}"] if rc != 0 else []
    problems += env_matrix.baseline_problems(reports, 0, expected, duplicates)
    for module, report in sorted(reports.items()):
        if module not in ALL_SKIP_OK and (report.ran == 0 or len(report.skips) >= report.ran):
            problems.append(f"all skipped: {module} (ran {report.ran}, "
                            f"skipped {len(report.skips)})")
    return problems


def _report_checks(
    name: str, rc: int, folder: Path, expected: set[str], total: int
) -> tuple[list[str], int]:
    """(problems, skipped tests) of one test hook, from its report folder."""
    reports, duplicates = env_matrix.load_reports(folder)
    problems = _module_problems(name, rc, reports, duplicates, expected)
    if total != len(expected):
        problems.append(f"total mismatch: {name} reports {total} modules, "
                        f"the inventory has {len(expected)}")
    return problems, sum(len(report.skips) for report in reports.values())


def run_hook(
    name: str, argv: list[str], env: dict[str, str], expected: set[str] | None = None
) -> HookRun:
    """Runs one hook from the checkout root and times it. For a test hook (`expected` given),
    the reports in its AI_KIT_TEST_REPORT_DIR are checked against the expected modules."""
    start = time.monotonic()
    proc = subprocess.run(argv, cwd=REPO_ROOT, env=env, capture_output=True, text=True,
                          check=False)
    secs = time.monotonic() - start
    output = proc.stdout + proc.stderr
    passed, total = _summary(output)
    problems: list[str] = []
    skipped = 0
    if expected is not None:
        problems, skipped = _report_checks(
            name, proc.returncode, Path(env[runner.REPORT_DIR_ENV]), expected, total
        )
    if proc.returncode != 0 or problems:
        print("\n".join(output.splitlines()[-OUTPUT_TAIL_LINES:]))
    for line in problems:
        print(f"problem {name}: {line}")
    return HookRun(name, proc.returncode, secs, passed, total, tuple(problems), skipped)


def _valid(run: HookRun) -> bool:
    return run.rc == 0 and run.total > 0 and run.passed == run.total and not run.problems


def verdict(
    core: HookRun, wizard: HookRun, limit: float = TEST_HOOK_LIMIT_SECS
) -> tuple[str, float]:
    """(`pass`, `fail` or `invalid`, unrounded total). Invalid when either test hook is not a
    complete green run, whatever the time; otherwise pass when the total is within the limit."""
    total = core.secs + wizard.secs
    if not (_valid(core) and _valid(wizard)):
        return "invalid", total
    return ("pass" if total <= limit else "fail"), total


def stale_all_skip_ok(inventory: set[str]) -> list[str]:
    """ALL_SKIP_OK names that are not in the inventory of the test hooks."""
    return sorted(name for name in ALL_SKIP_OK if name not in inventory)


def _workers(name: str, cpus: int | None) -> int:
    """The worker count the runner gives this test hook at the default share."""
    return runner.worker_count(len(runner.hook_groups()[name]), cpus, None)


def _test_part(label: str, run: HookRun, cpus: int | None) -> str:
    return (f"{label}={run.secs:.1f}s(rc={run.rc}, {run.passed}/{run.total}, "
            f"skipped={run.skipped}, workers={_workers(run.name, cpus)})")


def _timed(
    name: str, config_text: str, scratch: Path, expected: set[str] | None = None
) -> HookRun:
    home = scratch / f"home-{name}"
    home.mkdir(parents=True, exist_ok=True)
    report_dir = scratch / f"reports-{name}" if expected is not None else None
    env = hook_env(os.environ, home, report_dir)
    if name == "check-dogfood":
        # Read-only: gsd-core looks up this project's capability consent under GSD_HOME (default
        # HOME), so the fold capability renders its hooks as on a real push.
        env["GSD_HOME"] = os.environ.get("GSD_HOME") or str(Path.home())
    return run_hook(name, hook_command(config_text, name), env, expected)


def _run_hooks(config_text: str) -> tuple[HookRun, HookRun, list[HookRun]]:
    """The two test hooks back to back, then the auxiliary hooks one at a time."""
    groups = runner.hook_groups()
    with tempfile.TemporaryDirectory(prefix="aikit-prepush-",
                                     ignore_cleanup_errors=True) as scratch_name:
        scratch = Path(scratch_name)
        core = _timed("unittest", config_text, scratch, set(groups["unittest"]))
        wizard = _timed("unittest-wizard", config_text, scratch,
                        set(groups["unittest-wizard"]))
        aux = [_timed(name, config_text, scratch) for name in AUXILIARY_HOOKS]
    return core, wizard, aux


def _record(core: HookRun, wizard: HookRun, aux: list[HookRun], cpus: int | None,
            load1: float) -> str:
    """The one `push-timing` line the owner and the docs read."""
    result, total = verdict(core, wizard)
    push_worst = sum(run.secs for run in (core, wizard, *aux))
    by_name = {run.name: run for run in aux}
    pyright, vulture = by_name["pyright"], by_name["vulture"]
    dogfood, deferred = by_name["check-dogfood"], by_name["deferred-e2e"]
    return " ".join([
        f"push-timing date={datetime.date.today().isoformat()} cpus={cpus} "
        f"load1={load1:.2f} share={runner.MAX_CPU_SHARE:.2f}",
        _test_part("core", core, cpus),
        _test_part("wizard", wizard, cpus),
        f"test-hooks={total:.1f}s limit={TEST_HOOK_LIMIT_SECS:.1f}s",
        f"pyright={pyright.secs:.1f}s(rc={pyright.rc})",
        f"vulture={vulture.secs:.1f}s(rc={vulture.rc})",
        f"dogfood={dogfood.secs:.1f}s(rc={dogfood.rc})",
        f"deferred-e2e={deferred.secs:.1f}s(rc={deferred.rc}, {deferred.passed}/"
        f"{deferred.total}, no range)",
        f"push-worst={push_worst:.1f}s",
        f"verdict={result}",
    ])


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if args:
        print("usage: time_prepush.py (takes no arguments)", file=sys.stderr)
        return 2
    config_text = (REPO_ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8")
    load1 = os.getloadavg()[0]
    cpus = runner.available_cpus()
    print(f"push timing: {cpus} CPUs, one-minute load {load1:.2f} at start, "
          f"share {runner.MAX_CPU_SHARE:.2f}, workers {_workers('unittest', cpus)} and "
          f"{_workers('unittest-wizard', cpus)}", flush=True)
    core, wizard, aux = _run_hooks(config_text)
    print(_record(core, wizard, aux, cpus, load1), flush=True)
    failed_aux = [run.name for run in aux if run.rc != 0]
    if failed_aux:
        print("auxiliary hooks failed: " + " ".join(failed_aux))
    result = verdict(core, wizard)[0]
    return 0 if result == "pass" and not failed_aux else 1


if __name__ == "__main__":
    sys.exit(main())
