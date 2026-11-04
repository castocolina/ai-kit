#!/usr/bin/env python3
"""Run unittest modules in parallel, one subprocess per module.

Usage:
    run_unittest_parallel.py MODULE [MODULE ...]
    run_unittest_parallel.py --group NAME [--group NAME ...] [-- MODULE ...]
    run_unittest_parallel.py --list-groups

Each module runs under the same interpreter as this script, so the caller picks
the runtime (system python3 or `uv run python`), with the repo root as its cwd.
Output is buffered per module and printed whole, so failures never interleave.
Exits 1 if any module fails or exceeds its deadline (module_timeout_secs); exits 130 when
interrupted.

Names after `--` are ignored: they are the generated listing that keeps a hook
entry searchable by module (tools/gen_test_groups.py). `--list-groups` prints
that listing.

Groups (each discovered tests/test_*.py lands in exactly one):
    unit        everything not named in an explicit set below (system python3)
    arch        ARCH_MODULES
    unit-uv     UNIT_UV_MODULES (needs the uv env)
    integration INTEGRATION_MODULES (Textual app and PTY-driven, under uv)
    e2e         E2E_MODULES (make e2e-test only; the one set kept out of validate)

Each module runs with a tripwire first on PATH: one stub per host CLI name that logs the call
and exits 127, and a non-empty log fails the module. It sees PATH lookups only (a call through
an absolute path is not seen; the arch rule covers literal commands). Host behaviour comes from
tests/host_fakes.py. Because the stubs sit on PATH, PATH-based detection such as
`shutil.which("claude")` finds every host inside a module; a test that needs a host to be
absent sets its own PATH.

Each module also gets a baseline env (baseline_env): no host signals, no inherited git state,
no host config, status-line, credential or backend-URL overrides, a temporary HOME with
AI_KIT_REFUSE_REAL_HOME=1, and the caller's tool caches forwarded by tool_cache_forwards.

Each module starts in its own session. Stopping a module (its deadline, or SIGINT/SIGTERM to this
runner) sends SIGTERM to its process group first and SIGKILL after MODULE_STOP_GRACE_SECS; a
test that starts its own session must forward SIGTERM to it (tests/test_cross_ai_runner_e2e.py
does). An interrupted run starts no queued module and stops every live one.

Workers are a share of the available CPUs, capped at 40 percent
(os.process_cpu_count(), then the affinity mask, then os.cpu_count()).
AI_KIT_TEST_CPU_SHARE may lower that share, never raise it.
"""
import contextlib
import math
import os
import shlex
import signal
import subprocess
import sys
import tempfile
import threading
import time
from collections.abc import Mapping
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from types import FrameType, MappingProxyType

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
    "tests.test_hook_registry_e2e",  # R10: real setup.py hook runs under a temp HOME
    "tests.test_cross_ai_runner_e2e",
    "tests.test_precompact_shims_e2e",  # node runs of the pi and opencode shims (D-18)
    # real dispatch of the six checkers; the agents domain runs the project-local gsd-core
    # through node (26-08)
    "tests.test_ai_kit_project_rules_all_e2e",
    # real goal_prompt.py subprocess runs on temp git repos with a fake node; dogfood detect (27-09)
    "tests.test_ai_kit_spec_goal_prompt_e2e",
    # real mmdc and headless Chrome from the caller's Puppeteer cache; named skips decided by
    # a probe render (28-01)
    "tests.test_markdown_to_pdf_e2e",
})
EXPLICIT_GROUPS = {
    "arch": ARCH_MODULES,
    "unit-uv": UNIT_UV_MODULES,
    "integration": INTEGRATION_MODULES,
    "e2e": E2E_MODULES,
}

# Host CLI binary names the tripwire stubs: copied from the RUNTIMES binaries plus the
# goal-prompt HOST_BINARY values (cursor-agent comes from the table); pinned by a drift test.
HOST_CLI_NAMES = frozenset({
    "agent", "claude", "codex", "copilot", "cursor-agent", "grok", "opencode", "pi",
})
TRIPWIRE_MAX_LINES = 20
# Copied from detection.HOST_SIGNAL_ENV_VARS (pinned by a drift test): a caller's host marker
# must not make a module believe it runs inside a host.
HOST_SIGNAL_VARS = frozenset({
    "AI_AGENT", "CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT", "CLAUDE_CODE_SSE_PORT", "CODEX_SANDBOX",
    "CODEX_THREAD_ID", "CODEX_VERSION", "CURSOR_AGENT", "GROK_AGENT", "OPENCODE",
    "PI_CODING_AGENT",
})
# Env names product code reads as a host config dir, XDG home, credential file, tooling path or
# install dir (found by the drift scan): a caller's value would point a test at owner state.
HOME_OVERRIDE_VARS = frozenset({
    "ANTIGRAVITY_CONFIG_DIR", "AUGMENT_CONFIG_DIR", "CLAUDE_CONFIG_DIR", "CLINE_CONFIG_DIR",
    "CODEBUDDY_CONFIG_DIR", "CODEX_HOME", "COPILOT_CONFIG_DIR", "COPILOT_HOME",
    "CURSOR_CONFIG_DIR", "GROK_AGENTS_HOME", "GSD_HOME", "HERMES_HOME", "KILO_CONFIG_DIR",
    "KIMI_CODE_HOME", "KIMI_CONFIG_DIR", "OPENCODE_CONFIG_DIR", "PI_CODING_AGENT_DIR",
    "QWEN_CONFIG_DIR", "TRAE_CONFIG_DIR", "WINDSURF_CONFIG_DIR", "XDG_CACHE_HOME",
    "XDG_CONFIG_HOME", "XDG_DATA_HOME", "XDG_STATE_HOME", "XDG_RUNTIME_DIR", "ZCODE_CONFIG_DIR",
    "AGENTS_TOOLING_PATH", "SHARED_TOOLING_PATH", "AI_KIT_DIR", "CLAUDE_JOB_DIR",
    "CLAUDE_PLUGIN_ROOT", "RUNTIME_DIR", "JEV_API_KEY_FILE",
})
# API keys and backend URLs product code reads: no test makes a credentialed call through the
# caller's key.
CREDENTIAL_ENV_VARS = frozenset({
    "JEV_API_KEY", "JEV_API_URL", "TYPESAFE_API_KEY", "LAYA_API_KEY", "OPENCODE_ZEN_API_KEY",
    "ARTIFICIAL_ANALYSIS_API_KEY", "JEV_LAYA_URL", "JEV_OPENCODE_URL", "JEV_TYPESAFE_URL",
    "AI_KIT_LAYA_URL",
})
# The status-line ConfigSpec env prefixes: <prefix>CONFIG_FILE is read before HOME and
# <prefix>EXTERNAL_DIR selects an executable provider folder.
HOST_CONFIG_ENV_PREFIXES = ("CC_AI_KIT_", "AI_KIT_CURSOR_")
GIT_KEPT_VARS = frozenset({"GIT_EXEC_PATH"})

MAX_CPU_SHARE = 0.40
# A hung module fails the gate instead of hanging it; generous for slow machines.
MODULE_TIMEOUT_SECS = 900
# The self-test module runs the full runner self-test twice, each guarded by a hang guard sized
# from one load reading (300 s and 900 s at idle, times the 1..4 load factor): 4 x (300 + 900) s
# plus 600 s for the rest of the module. Its own guards fire first. A real hang of this module can
# therefore hold `make e2e-test` for up to 5400 s at the 4x cap (1200 s plus the rest at idle).
SELF_TEST_MODULE_TIMEOUT_SECS = 5400
MODULE_TIMEOUT_OVERRIDES = MappingProxyType({
    "tests.test_cross_ai_runner_e2e": SELF_TEST_MODULE_TIMEOUT_SECS,
})
# SIGTERM to a module's group, this long to clean up, then SIGKILL.
MODULE_STOP_GRACE_SECS = 15
REAP_SECS = 5
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


_STUB = """#!/bin/sh
printf '%s %s\\n' {name} "$*" >> {log}
echo 'ai-kit tripwire: real host CLI {name} called from a test; use tests/host_fakes.py' >&2
exit 127
"""


def write_tripwire(directory: Path) -> Path:
    """Create `directory/bin/<host>` stubs (log, message, exit 127) and an empty
    `directory/calls.log`; return the log path. The log path is baked into each stub."""
    bin_dir = directory / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    log = directory / "calls.log"
    log.write_text("", encoding="utf-8")
    for name in sorted(HOST_CLI_NAMES):
        stub = bin_dir / name
        stub.write_text(
            _STUB.format(name=shlex.quote(name), log=shlex.quote(str(log))), encoding="utf-8"
        )
        stub.chmod(0o755)
    return log


def _tripwire_report(log_path: Path) -> str:
    """The `tripwire:` block for a non-empty calls log (at most TRIPWIRE_MAX_LINES calls)."""
    calls = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
    if not calls:
        return ""
    lines = ["tripwire: real host CLI calls (fakes only, tests/host_fakes.py):"]
    lines += calls[:TRIPWIRE_MAX_LINES]
    if len(calls) > TRIPWIRE_MAX_LINES:
        lines.append(f"... and {len(calls) - TRIPWIRE_MAX_LINES} more calls")
    return "\n".join(lines) + "\n"


def _with_tripwire(rc: int, output: str, log_path: Path) -> tuple[int, str]:
    """A non-empty tripwire log fails the module: rc 0 becomes 1, the calls are appended."""
    report = _tripwire_report(log_path)
    if not report:
        return rc, output
    return rc or 1, output + ("" if output.endswith("\n") or not output else "\n") + report


def tool_cache_forwards(source: Mapping[str, str]) -> dict[str, str]:
    """Tool caches and toolchains the pinned HOME would hide, from the caller's `source`.

    Never host configuration. A caller-set value is kept; an unset one is computed from the
    caller's HOME (the two folders only when they exist). Plans that replace HOME call this
    on the caller's env first.
    shortcut: other version managers (asdf, mise, nvm) resolve their shims under HOME too and
    are not forwarded; forward their data-dir variable the day a caller needs one."""
    home = source.get("HOME")
    defaults = {}
    if home:
        defaults = {
            "PUPPETEER_CACHE_DIR": os.path.join(home, ".cache", "puppeteer"),
            "UV_CACHE_DIR": os.path.join(home, ".cache", "uv"),
        }
        for name, rel in (("UV_PYTHON_INSTALL_DIR", ".local/share/uv/python"),
                          ("VOLTA_HOME", ".volta")):
            if os.path.isdir(os.path.join(home, rel)):
                defaults[name] = os.path.join(home, rel)
    names = ("PUPPETEER_CACHE_DIR", "UV_CACHE_DIR", "UV_PYTHON_INSTALL_DIR", "VOLTA_HOME")
    forwards = {name: source[name] for name in names if source.get(name)}
    for name, value in defaults.items():
        forwards.setdefault(name, value)
    return forwards


def baseline_env(
    source: Mapping[str, str], temp_dir: Path, tripwire_bin: Path
) -> dict[str, str]:
    """The module's pinned environment: `source` without host signals, git state, host config,
    status-line and credential overrides, a temporary HOME, the tripwire first on PATH."""
    forwards = tool_cache_forwards(source)
    env = {
        name: value for name, value in source.items()
        if name not in HOST_SIGNAL_VARS | HOME_OVERRIDE_VARS | CREDENTIAL_ENV_VARS
        and not name.startswith(HOST_CONFIG_ENV_PREFIXES)
        and not (name.startswith("GIT_") and name not in GIT_KEPT_VARS)
    }
    home = temp_dir / "home"
    home.mkdir(parents=True, exist_ok=True)
    env.update(forwards)
    env.update({
        "TMPDIR": str(temp_dir), "TEMP": str(temp_dir), "TMP": str(temp_dir),
        "HOME": str(home), "AI_KIT_REFUSE_REAL_HOME": "1",
        "GIT_CEILING_DIRECTORIES": str(temp_dir.parent), "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_AUTHOR_NAME": "ai-kit test", "GIT_COMMITTER_NAME": "ai-kit test",
        "GIT_AUTHOR_EMAIL": "test@ai-kit.invalid", "GIT_COMMITTER_EMAIL": "test@ai-kit.invalid",
        "PATH": os.pathsep.join([str(tripwire_bin), source.get("PATH", "")]),
    })
    return env


def module_timeout_secs(module: str) -> int:
    """The deadline of `module`; the global is read at call time so a test can patch it."""
    return MODULE_TIMEOUT_OVERRIDES.get(module, MODULE_TIMEOUT_SECS)


_LOCK = threading.Lock()
_LIVE: set[subprocess.Popen[str]] = set()
_STOPPING = threading.Event()


def _signal_group(proc: subprocess.Popen[str], sig: int) -> None:
    with contextlib.suppress(ProcessLookupError):  # the group is already gone
        os.killpg(proc.pid, sig)


def stop_process_group(proc: subprocess.Popen[str], grace: float | None = None) -> None:
    """Stop `proc` and everything in its group: SIGTERM, up to `grace` seconds for the leader to
    exit, SIGKILL to the group, then a bounded reap that never blocks on a pipe a descendant in
    another session still holds. Call it from the thread that reads the pipes of `proc`.
    shortcut: a pid reused between the leader's exit and the SIGKILL is not guarded, upgrade
    to waitid(WNOWAIT) if a stop ever hits an unrelated group."""
    _signal_group(proc, signal.SIGTERM)
    with contextlib.suppress(subprocess.TimeoutExpired):
        proc.wait(timeout=MODULE_STOP_GRACE_SECS if grace is None else grace)
    _signal_group(proc, signal.SIGKILL)
    try:
        proc.communicate(timeout=REAP_SECS)
    except subprocess.TimeoutExpired:
        for pipe in (proc.stdout, proc.stderr):
            if pipe:
                pipe.close()
        with contextlib.suppress(subprocess.TimeoutExpired):
            proc.wait(timeout=REAP_SECS)


def _stop_live_groups() -> None:
    """Interrupt path: stop every registered group (SIGTERM, grace, SIGKILL). The pipes stay with
    their worker threads, which finish once the groups are dead.
    shortcut: a stray in another session that holds a module's pipe delays the pool shutdown
    until it exits; modules forward SIGTERM to their sessions so none is left."""
    with _LOCK:
        procs = list(_LIVE)
    for proc in procs:
        _signal_group(proc, signal.SIGTERM)
    deadline = time.monotonic() + MODULE_STOP_GRACE_SECS
    while time.monotonic() < deadline and any(proc.poll() is None for proc in procs):
        time.sleep(0.05)
    for proc in procs:
        _signal_group(proc, signal.SIGKILL)


def _start_registered(
    argv: list[str], cwd: Path, env: Mapping[str, str]
) -> subprocess.Popen[str] | None:
    """Start a module in its own session and register it, unless the run is being stopped. The
    stop flag is read under the lock that registers, so no process starts after a stop."""
    with _LOCK:
        if _STOPPING.is_set():
            return None
        proc = subprocess.Popen(  # pylint: disable=consider-using-with
            argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=cwd,
            env=dict(env), start_new_session=True,
        )
        _LIVE.add(proc)
        return proc


def _communicate(proc: subprocess.Popen[str], timeout: float) -> tuple[int, str]:
    try:
        out, err = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        stop_process_group(proc)
        return 124, f"timed out after {timeout}s"
    return proc.returncode, out + err


def run_module(module: str, cwd: Path = REPO_ROOT) -> tuple[str, int, str, float]:
    start = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="aikit-ut-", ignore_cleanup_errors=True) as temp_dir:
        log_path = write_tripwire(Path(temp_dir) / "tripwire")
        env = baseline_env(os.environ, Path(temp_dir), log_path.parent / "bin")
        proc = _start_registered([sys.executable, "-m", "unittest", module], cwd, env)
        if proc is None:
            return module, 130, "not started: the run was interrupted", 0.0
        try:
            rc, output = _communicate(proc, module_timeout_secs(module))
        finally:
            with _LOCK:
                _LIVE.discard(proc)
        rc, output = _with_tripwire(rc, output, log_path)
        return module, rc, output, time.monotonic() - start


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


def main(argv: list[str], cwd: Path = REPO_ROOT) -> int:
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
    try:
        failed = _run_all(modules, cwd)
    except KeyboardInterrupt:
        _STOPPING.set()
        _stop_live_groups()  # also a child started outside the pool
        print("interrupted: every module was stopped", file=sys.stderr)
        return 130
    print(f"{len(modules) - len(failed)}/{len(modules)} modules passed")
    if failed:
        print("failed: " + " ".join(sorted(failed)))
    return 1 if failed else 0


def _raise_interrupt(_signum: int, _frame: FrameType | None) -> None:
    raise KeyboardInterrupt


def install_signal_handlers() -> None:
    """SIGINT and SIGTERM both stop the run (only valid in the main thread). SIGINT is set
    explicitly: a runner started from a background job inherits it ignored."""
    signal.signal(signal.SIGINT, signal.default_int_handler)
    signal.signal(signal.SIGTERM, _raise_interrupt)


def _run_all(modules: list[str], cwd: Path = REPO_ROOT) -> list[str]:
    workers = worker_count(len(modules), available_cpus(), os.environ.get(CPU_SHARE_ENV))
    failed: list[str] = []
    _STOPPING.clear()
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(run_module, m, cwd) for m in modules]
        try:
            for fut in as_completed(futures):
                module, rc, output, secs = fut.result()
                ran = next((ln for ln in output.splitlines() if ln.startswith("Ran ")), "")
                status = "ok" if rc == 0 else f"FAILED (rc={rc})"
                print(f"=== {module}: {status} in {secs:.1f}s  {ran}")
                if rc != 0:
                    failed.append(module)
                    print(output)
        except KeyboardInterrupt:
            _STOPPING.set()
            for fut in futures:
                fut.cancel()
            _stop_live_groups()
            pool.shutdown(wait=True, cancel_futures=True)
            raise
    return failed


if __name__ == "__main__":
    install_signal_handlers()
    sys.exit(main(sys.argv[1:]))
