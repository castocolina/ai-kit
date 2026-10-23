#!/usr/bin/env python3
"""Run unittest modules in parallel, one subprocess per module.

Usage:
    run_unittest_parallel.py MODULE [MODULE ...]
    run_unittest_parallel.py --group NAME [--group NAME ...] [-- MODULE ...]
    run_unittest_parallel.py --list-groups

Each module runs under the same interpreter as this script, so the caller picks
the runtime (system python3 or `uv run python`), with the repo root as its cwd.
Output is buffered per module and printed whole, so failures never interleave.
Exits 1 if any module fails or exceeds MODULE_TIMEOUT_SECS.

Names after `--` are ignored: they are the generated listing that keeps a hook
entry searchable by module (tools/gen_test_groups.py). `--list-groups` prints
that listing.

Groups (each discovered tests/test_*.py lands in exactly one):
    unit        everything not named in an explicit set below (system python3)
    arch        ARCH_MODULES
    unit-uv     UNIT_UV_MODULES (needs the uv env)
    integration INTEGRATION_MODULES (Textual app and PTY-driven, under uv)
    e2e         E2E_MODULES (make e2e-test only; the one set kept out of validate)

Workers are a share of the available CPUs, capped at 40 percent
(os.process_cpu_count(), then the affinity mask, then os.cpu_count()).
AI_KIT_TEST_CPU_SHARE may lower that share, never raise it.
"""
import math
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TESTS_DIR = REPO_ROOT / "tests"

# arch-test tier: the AST architecture-fitness module.
ARCH_MODULES = frozenset({"tests.test_arch"})
# Needs PyYAML, which only the uv env provides.
UNIT_UV_MODULES = frozenset({"tests.test_framework_profiles"})
# Textual app and PTY-driven suites; they run under uv (the wizard hook).
INTEGRATION_MODULES = frozenset({
    "tests.test_config_doctor",
    "tests.test_config_doctor_pty",
    "tests.test_wizard_app",
    "tests.test_wizard_pty",
})
# Real git worktrees, memory checks, and real `node` runs against the checkout-local
# gsd-core; make e2e-test only, out of validate.
E2E_MODULES = frozenset({
    "tests.test_worktree_e2e",
    "tests.test_system_memory_e2e",
    "tests.test_curated_config_e2e",
    "tests.test_curated_config_apply_e2e",
    "tests.test_ai_kit_gsd_curated_config_matrix",
    "tests.test_ai_kit_spec_e2e",
    "tests.test_ai_kit_gsd_spec_discuss_e2e",
    "tests.test_jev_skill_install_e2e",  # R8: real setup.py runs under a temp HOME
    "tests.test_cross_ai_runner_e2e",
})
EXPLICIT_GROUPS = {
    "arch": ARCH_MODULES,
    "unit-uv": UNIT_UV_MODULES,
    "integration": INTEGRATION_MODULES,
    "e2e": E2E_MODULES,
}

MAX_CPU_SHARE = 0.40
# A hung module fails the gate instead of hanging it; generous for slow machines.
MODULE_TIMEOUT_SECS = 900
CPU_SHARE_ENV = "AI_KIT_TEST_CPU_SHARE"


def discover_modules(tests_dir: Path = TESTS_DIR) -> list[str]:
    """Sorted `tests.<stem>` names for every test_*.py directly in tests_dir."""
    return sorted(f"tests.{path.stem}" for path in tests_dir.glob("test_*.py"))


def group_modules(discovered: list[str]) -> dict[str, list[str]]:
    """Every discovered module in exactly one group; `unit` is the remainder."""
    found = set(discovered)
    groups = {
        name: sorted(modules & found) for name, modules in EXPLICIT_GROUPS.items()
    }
    groups["unit"] = sorted(found - set().union(*EXPLICIT_GROUPS.values()))
    return groups


def hook_groups() -> dict[str, list[str]]:
    """What each validate hook runs."""
    groups = group_modules(discover_modules())
    return {
        "unittest": groups["unit"] + groups["arch"],
        "unittest-wizard": groups["unit-uv"] + groups["integration"],
    }


def stale_exception_names(discovered: list[str]) -> list[str]:
    """Explicit-set names that have no matching tests file."""
    found = set(discovered)
    return sorted(
        name for modules in EXPLICIT_GROUPS.values() for name in modules if name not in found
    )


def available_cpus() -> int | None:
    """CPUs this process may use: process count, then affinity, then cpu_count."""
    process_cpu_count = getattr(os, "process_cpu_count", None)
    if process_cpu_count is not None:
        count = process_cpu_count()
        if isinstance(count, int) and count > 0:
            return count
    get_affinity = getattr(os, "sched_getaffinity", None)
    if get_affinity is not None:
        return len(get_affinity(0))
    return os.cpu_count()


def worker_count(n_modules: int, cpus: int | None, share_env: str | None = None) -> int:
    """At most the 40% share of cpus, never more than the module count, at least 1."""
    share = MAX_CPU_SHARE
    if share_env is not None:
        try:
            requested = float(share_env)
        except ValueError:
            requested = None
        if requested is not None and 0 < requested < MAX_CPU_SHARE:
            share = requested
    if not cpus or cpus <= 0:
        return 1
    return min(n_modules, max(1, math.floor(share * cpus)))


def run_module(module: str, cwd: Path = REPO_ROOT) -> tuple[str, int, str, float]:
    start = time.monotonic()
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "unittest", module],
            capture_output=True, text=True, check=False, cwd=cwd,
            timeout=MODULE_TIMEOUT_SECS,
        )
    except subprocess.TimeoutExpired:
        output = f"timed out after {MODULE_TIMEOUT_SECS}s"
        return module, 124, output, time.monotonic() - start
    return module, proc.returncode, proc.stdout + proc.stderr, time.monotonic() - start


def _parse_groups(argv: list[str]) -> tuple[list[str] | None, str | None]:
    """Group names from repeatable `--group NAME` pairs, or an error string."""
    groups: list[str] = []
    index = 0
    while index < len(argv):
        if argv[index] != "--group":
            return None, "usage: run_unittest_parallel.py --group NAME [--group NAME ...]"
        if index + 1 >= len(argv):
            return None, "error: --group needs a NAME"
        name = argv[index + 1]
        if name not in (*EXPLICIT_GROUPS, "unit"):
            return None, f"error: unknown group {name}"
        groups.append(name)
        index += 2
    return groups, None


def _modules_for_groups(argv: list[str]) -> tuple[list[str] | None, str | None]:
    groups, error = _parse_groups(argv)
    if error or groups is None:
        return None, error
    discovered = discover_modules()
    stale = stale_exception_names(discovered)
    if stale:
        return None, "error: stale exception names: " + " ".join(stale)
    grouped = group_modules(discovered)
    return [module for name in groups for module in grouped[name]], None


def _emit_group_listing() -> int:
    """Print one `group: module ...` line per group, for the generated listings."""
    for name, names in group_modules(discover_modules()).items():
        print(f"{name}: {' '.join(names)}")
    for name, names in hook_groups().items():
        print(f"hook {name}: {' '.join(names)}")
    return 0


def main(argv: list[str]) -> int:
    if argv == ["--list-groups"]:
        return _emit_group_listing()
    # Names after `--` are the generated listing: discovery decides what runs,
    # and the names keep the hook entry searchable by module.
    if "--" in argv:
        argv = argv[:argv.index("--")]
    if "--group" in argv:
        selected, error = _modules_for_groups(argv)
        if error or selected is None:
            print(error, file=sys.stderr)
            return 2
        modules = selected
    else:
        modules = argv
    if not modules:
        print("usage: run_unittest_parallel.py MODULE [MODULE ...]", file=sys.stderr)
        return 2
    failed = _run_all(modules)
    print(f"{len(modules) - len(failed)}/{len(modules)} modules passed")
    if failed:
        print("failed: " + " ".join(sorted(failed)))
    return 1 if failed else 0


def _run_all(modules: list[str]) -> list[str]:
    workers = worker_count(len(modules), available_cpus(), os.environ.get(CPU_SHARE_ENV))
    failed: list[str] = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for fut in as_completed([pool.submit(run_module, m) for m in modules]):
            module, rc, output, secs = fut.result()
            ran = next((ln for ln in output.splitlines() if ln.startswith("Ran ")), "")
            status = "ok" if rc == 0 else f"FAILED (rc={rc})"
            print(f"=== {module}: {status} in {secs:.1f}s  {ran}")
            if rc != 0:
                failed.append(module)
                print(output)
    return failed


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
