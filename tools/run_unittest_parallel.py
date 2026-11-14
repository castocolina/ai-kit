#!/usr/bin/env python3
"""Run unittest modules in parallel, one subprocess per module.

Usage:
    run_unittest_parallel.py MODULE [MODULE ...]
    run_unittest_parallel.py --group NAME [--group NAME ...] [-- MODULE ...]
    run_unittest_parallel.py --staged [PATH ...]
    run_unittest_parallel.py --pushed
    run_unittest_parallel.py --list-groups

Each module runs under the same interpreter as this script, so the caller picks
the runtime (system python3 or `uv run python`), with the repo root as its cwd.
Output is buffered per module and printed whole, so failures never interleave.
Exits 1 if any module fails or exceeds its deadline (MODULE_TIMEOUT_SECS); exits 130 when
interrupted.

--staged runs exactly the modules that cover the staged files: the name index in
tools/staged_mapper.py picks them. Unit and arch modules run under this interpreter; unit-uv,
integration and the covering e2e modules within COMMIT_E2E_BUDGET_SECS run in one
`uv run python <this runner> <modules>` child after them. The full unit and arch groups run when
the mapper says so (shared machinery, a shared helper or fixture, any mapper failure), and every
covering unit-uv, integration and in-budget e2e module runs with them. An e2e module over the
budget, or with no recorded time in E2E_RECORDED_SECS, is not run at commit: the notice names it
and the pre-push `deferred-e2e` hook runs it. No PATH means the paths from `git diff --cached`.
It excludes --group and module names.

--pushed runs, under uv, every over-budget covering e2e module for the pushed range. It narrows to
that range only when the proof holds: the checkout is the pushed commit and no commit that a local
branch or worktree HEAD holds lies outside it (local tags and the stash are left out). Otherwise it
runs every over-budget e2e module and prints why. Like every push hook, it tests the checkout.

Names after `--` are ignored: they are the generated listing that keeps a hook
entry searchable by module (tools/gen_test_groups.py). `--list-groups` prints
that listing.

Groups (each discovered tests/test_*.py lands in exactly one):
    unit        everything not named in an explicit set below (system python3)
    arch        ARCH_MODULES
    unit-uv     UNIT_UV_MODULES (needs the uv env)
    integration INTEGRATION_MODULES (Textual app and PTY-driven, under uv)
    e2e         E2E_MODULES (make e2e-test; kept out of validate, its over-budget covering
                modules run at push)

Each module runs with a tripwire first on PATH: one stub per host CLI name that logs the call
and exits 127, and a non-empty log fails the module. It sees PATH lookups only (a call through
an absolute path is not seen; the arch rule covers literal commands). Host behaviour comes from
tests/host_fakes.py. Because the stubs sit on PATH, PATH-based detection such as
`shutil.which("claude")` finds every host inside a module; a test that needs a host to be
absent sets its own PATH.

Each module also gets a baseline env (baseline_env): no host signals, no inherited git state,
no host config, status-line, credential or backend-URL overrides, a temporary HOME with
AI_KIT_REFUSE_REAL_HOME=1, and the caller's tool caches forwarded by tool_cache_forwards.

With AI_KIT_TEST_REPORT_DIR set, a top-level run also writes one JSON report per module into
that folder (`module`, `rc`, `skips`, `ran`; see report_text and publish_report). Module envs
never carry the variable, so a nested runner a test starts writes nothing.

Each module starts in its own session. Stopping a module (its deadline, or SIGINT/SIGTERM to this
runner) sends SIGTERM to its process group first and SIGKILL after MODULE_STOP_GRACE_SECS; a
test that starts its own session must forward SIGTERM to it (tests/cross_ai_selftest.py
does). An interrupted run starts no queued module and stops every live one.

Workers are a share of the available CPUs, capped at 40 percent
(os.process_cpu_count(), then the affinity mask, then os.cpu_count()).
AI_KIT_TEST_CPU_SHARE may lower that share, never raise it.
"""
import ast
import contextlib
import importlib.util
import json
import math
import os
import re
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
from collections.abc import Mapping
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from types import FrameType, ModuleType

REPO_ROOT = Path(__file__).resolve().parent.parent
TESTS_DIR = REPO_ROOT / "tests"

# arch-test tier: the AST architecture-fitness module.
ARCH_MODULES = frozenset({"tests.test_arch"})
# Needs PyYAML or LibCST, which only the uv env provides.
UNIT_UV_MODULES = frozenset({
    "tests.test_cst_refactor_codemods",  # needs LibCST from the uv dev group (32.1)
    "tests.test_framework_profiles",
    "tests.test_skill_frontmatter_pyyaml",
})
# Textual app and PTY-driven suites; they run under uv (the wizard hook).
INTEGRATION_MODULES = frozenset({
    "tests.test_config_doctor",
    "tests.test_config_doctor_pty",
    "tests.test_doctor_screen",
    # the wizard view tests, split in three so they run in parallel (quick 261104-hzc)
    "tests.test_wizard_app_1",
    "tests.test_wizard_app_2",
    "tests.test_wizard_app_3",
    # the host pane tests, split in two so they run in parallel
    "tests.test_wizard_hostpane",
    "tests.test_wizard_hostpane_2",
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
    # the runner template's self-test, split by kind into timed shards (quick 261104-cxr)
    "tests.test_cross_ai_selftest_logic_1_e2e",
    "tests.test_cross_ai_selftest_logic_2_e2e",
    "tests.test_cross_ai_selftest_logic_3_e2e",
    "tests.test_cross_ai_selftest_logic_4_e2e",
    "tests.test_cross_ai_selftest_runtime_1_e2e",
    "tests.test_cross_ai_selftest_runtime_2_e2e",
    "tests.test_cross_ai_selftest_runtime_3_e2e",
    "tests.test_cross_ai_selftest_runtime_4_e2e",
    "tests.test_precompact_shims_e2e",  # node runs of the pi and opencode shims (D-18)
    # real dispatch of the six checkers; the agents domain runs the project-local gsd-core
    # through node (26-08)
    "tests.test_ai_kit_project_rules_all_e2e",
    # real goal_prompt.py subprocess runs on temp git repos with a fake node; dogfood detect (27-09)
    "tests.test_ai_kit_spec_goal_prompt_e2e",
    # real mmdc and headless Chrome from the caller's Puppeteer cache; named skips decided by
    # a probe render (28-01)
    "tests.test_markdown_to_pdf_e2e",
    # real git commits through the real pre-commit hook in a temp repo (28-06)
    "tests.test_staged_commit_e2e",
    # real gsd-core runs of the fold capability in a temp fixture project (29-12)
    "tests.test_ai_kit_commit_fold_e2e",
    # real gsd-tools and real git worktrees for the index step (30-01)
    "tests.test_flow_index_e2e",
})
# Commit budget (SPEC R1, amended 2026-11-03): an e2e module recorded above this runs at push, not
# at commit. It equals SPEC R3's push target for the two test hooks (the 2026-11-02 e2e run split
# there: 57.7 s at most, against 360.5 s for tests.test_cross_ai_runner_e2e).
COMMIT_E2E_BUDGET_SECS = 60
# Whole seconds per e2e module, rounded up from the `=== <module>: ok in <s>` lines of one
# `--group e2e` run on the frozen tree (2026-11-04, 24 CPUs, one-minute load 1.57 at start). These
# are this machine's times and are not scaled by CPU count. Refresh on a quiet machine with that
# command. A module missing from this table is over the budget.
E2E_RECORDED_SECS = {
    "tests.test_flow_index_e2e": 9,
    "tests.test_ai_kit_commit_fold_e2e": 15,
    "tests.test_ai_kit_gsd_curated_config_matrix": 1,
    "tests.test_ai_kit_gsd_spec_discuss_e2e": 1,
    "tests.test_ai_kit_project_rules_all_e2e": 1,
    "tests.test_ai_kit_spec_e2e": 1,
    "tests.test_ai_kit_spec_goal_prompt_e2e": 1,
    "tests.test_cross_ai_runner_e2e": 17,
    "tests.test_cross_ai_selftest_logic_1_e2e": 22,
    "tests.test_cross_ai_selftest_logic_2_e2e": 22,
    "tests.test_cross_ai_selftest_logic_3_e2e": 22,
    "tests.test_cross_ai_selftest_logic_4_e2e": 22,
    "tests.test_cross_ai_selftest_runtime_1_e2e": 24,
    "tests.test_cross_ai_selftest_runtime_2_e2e": 24,
    "tests.test_cross_ai_selftest_runtime_3_e2e": 24,
    "tests.test_cross_ai_selftest_runtime_4_e2e": 24,
    "tests.test_curated_config_apply_e2e": 1,
    "tests.test_curated_config_e2e": 6,
    "tests.test_hook_registry_e2e": 2,
    "tests.test_jev_skill_install_e2e": 1,
    "tests.test_markdown_to_pdf_e2e": 1,
    "tests.test_precompact_shims_e2e": 13,
    "tests.test_staged_commit_e2e": 4,
    "tests.test_system_memory_e2e": 1,
    "tests.test_worktree_e2e": 1,
}
# Whole seconds per unit, arch, unit-uv or integration module of 5 s or more, rounded up from the
# `=== <module>: ok in <s>` lines of one run of the two test hooks' groups (2026-11-13, 24 CPUs,
# one-minute load 3.00 at start). Only the start order reads them: the slowest modules start
# first, so a long one never starts last. Refresh after splitting or slowing a module.
HOOK_RECORDED_SECS = {
    "tests.test_ai_kit_session_wake_fire": 10,
    "tests.test_ai_kit_spec_runner_dispatch": 8,
    "tests.test_arch": 7,
    "tests.test_claude_precompact": 10,
    "tests.test_cursor_quota": 6,
    "tests.test_flow_checkpoint": 8,
    "tests.test_flow_checkpoint_2": 11,
    "tests.test_flow_contract": 8,
    "tests.test_flow_contract_2": 10,
    "tests.test_flow_contract_3": 11,
    "tests.test_flow_stack": 15,
    "tests.test_flow_stack_2": 8,
    "tests.test_flow_stack_3": 12,
    "tests.test_jev_fast_decision": 18,
    "tests.test_precompact_core": 7,
    "tests.test_run_unittest_parallel": 8,
    "tests.test_wizard_app_1": 13,
    "tests.test_wizard_app_2": 18,
    "tests.test_wizard_app_3": 13,
    "tests.test_wizard_hostpane": 11,
    "tests.test_wizard_hostpane_2": 12,
    "tests.test_wizard_pty": 18,
}
# Files whose change can alter how any module runs or is selected: staging one runs the full
# unit and arch groups. A tests/ helper or fixture covering two or more modules counts too, but
# the mapper computes those from the index.
SHARED_MACHINERY = frozenset({
    "tools/run_unittest_parallel.py", "tools/staged_mapper.py", "tools/gen_test_groups.py",
    ".pre-commit-config.yaml", "Makefile", "pyproject.toml", "uv.lock",
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
# API keys and backend URLs product code reads or used to read: no test makes a credentialed
# call through the caller's key.
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
# A hung module fails the gate instead of hanging it; generous for slow machines. It is the one
# deadline for every module; the runner self-test shards size their guards under it.
MODULE_TIMEOUT_SECS = 900
# SIGTERM to a module's group, this long to clean up, then SIGKILL.
MODULE_STOP_GRACE_SECS = 15
REAP_SECS = 5
CPU_SHARE_ENV = "AI_KIT_TEST_CPU_SHARE"
# The folder a top-level run writes per-module reports into (tools/env_matrix.py reads them).
# baseline_env drops it, so only the top-level runner writes reports.
REPORT_DIR_ENV = "AI_KIT_TEST_REPORT_DIR"
_SKIP_RE = re.compile(r" \.\.\. skipped (.*)$", re.MULTILINE)
_RAN_RE = re.compile(r"^Ran (\d+) tests? in ", re.MULTILINE)


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


def stale_machinery_names(root: Path = REPO_ROOT) -> list[str]:
    """SHARED_MACHINERY entries that do not exist under root."""
    return sorted(name for name in SHARED_MACHINERY if not (root / name).exists())


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
        and name != REPORT_DIR_ENV
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


def parse_skips(output: str, temp_dir: str, checkout: str) -> list[str]:
    """Sorted skip reasons of a verbose unittest run. The module's temp dir and the checkout path
    become `<tmp>` and `<checkout>`, so one skip compares equal across environments."""
    reasons = []
    for raw in _SKIP_RE.findall(output):
        try:
            text = str(ast.literal_eval(raw))
        except (ValueError, SyntaxError):
            text = raw
        if temp_dir:
            text = text.replace(temp_dir, "<tmp>")
        if checkout:
            text = text.replace(checkout, "<checkout>")
        reasons.append(text)
    return sorted(reasons)


def report_text(module: str, rc: int, output: str, temp_dir: str, checkout: str) -> str:
    """The JSON text of one module's report: module, rc, normalized skips and the Ran count."""
    ran = _RAN_RE.search(output)
    report = {
        "module": module,
        "rc": rc,
        "skips": parse_skips(output, temp_dir, checkout),
        "ran": int(ran.group(1)) if ran else 0,
    }
    return json.dumps(report, sort_keys=True, indent=2) + "\n"


def publish_report(folder: Path, module: str, text: str) -> None:
    """Create `<module>.json` exclusively. A second report for the same module is written as
    `<module>.<n>.json` beside the first, so the matrix flags it and nothing is overwritten."""
    folder.mkdir(parents=True, exist_ok=True)
    index = 1
    while True:
        name = f"{module}.json" if index == 1 else f"{module}.{index}.json"
        try:
            with (folder / name).open("x", encoding="utf-8") as handle:
                handle.write(text)
            return
        except FileExistsError:
            index += 1


def _unittest_argv(module: str) -> list[str]:
    """The unittest command; a reporting run adds -v so skip reasons appear in the output."""
    verbose = ["-v"] if os.environ.get(REPORT_DIR_ENV) else []
    return [sys.executable, "-m", "unittest", *verbose, module]


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
        proc = _start_registered(_unittest_argv(module), cwd, env)
        if proc is None:
            return module, 130, "not started: the run was interrupted", 0.0
        try:
            rc, output = _communicate(proc, MODULE_TIMEOUT_SECS)
        finally:
            with _LOCK:
                _LIVE.discard(proc)
        rc, output = _with_tripwire(rc, output, log_path)
        report_dir = os.environ.get(REPORT_DIR_ENV)
        if report_dir:
            text = report_text(module, rc, output, temp_dir, str(cwd.resolve()))
            publish_report(Path(report_dir), module, text)
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


def _load_mapper() -> ModuleType:
    """tools/staged_mapper.py, loaded by path so the runner works the same however it is loaded."""
    path = Path(__file__).resolve().with_name("staged_mapper.py")
    spec = importlib.util.spec_from_file_location("staged_mapper", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def split_e2e(modules: list[str]) -> tuple[list[str], list[str]]:
    """(within the commit budget, deferred to push). A module is within when its recorded
    whole-second time is at most COMMIT_E2E_BUDGET_SECS; an unrecorded one is deferred."""
    within, deferred = [], []
    for module in sorted(modules):
        recorded = E2E_RECORDED_SECS.get(module)
        if recorded is not None and recorded <= COMMIT_E2E_BUDGET_SECS:
            within.append(module)
        else:
            deferred.append(module)
    return within, deferred


def _deferral_line(module: str) -> str:
    recorded = E2E_RECORDED_SECS.get(module)
    when = "no recorded time" if recorded is None else f"recorded {recorded} s"
    return (f"staged: deferred to push (over the {COMMIT_E2E_BUDGET_SECS} s commit budget): "
            f"{module} ({when}); run now: uv run python tools/run_unittest_parallel.py {module}")


def _staged_selection(paths: list[str], cwd: Path) -> tuple[int, list[str], str | None]:
    """(staged file count, covering modules, full-run reason). A full run keeps every
    covering module the index found (unit-uv, integration and e2e too); a mapper failure has no
    covering set, so it names every e2e module."""
    try:
        mapper = _load_mapper()
        staged = paths or mapper.staged_paths(cwd)
        if not staged:
            return 0, [], None
        decision = mapper.decide(cwd, staged, SHARED_MACHINERY)
        if not decision.index_built:
            return len(set(staged)), sorted(E2E_MODULES), decision.full_reason
        arch = sorted(ARCH_MODULES & set(discover_modules())) if decision.arch else []
        return len(set(staged)), sorted({*decision.modules, *arch}), decision.full_reason
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return 0, sorted(E2E_MODULES), f"mapper error: {type(exc).__name__}: {exc}"


def _uv_missing(modules: list[str], prefix: str) -> bool:
    """True (and a `make setup-env` pointer printed) when uv is absent and modules need it."""
    if shutil.which("uv") is not None:
        return False
    print(f"{prefix} uv not found; the modules {' '.join(modules)} need it; run make setup-env")
    return True


def _run_under_uv(modules: list[str], cwd: Path, prefix: str) -> list[str]:
    """Run `modules` as one `uv run python <this runner> <modules>` child; the names that failed.
    The caller checks uv first with `_uv_missing`."""
    print(f"{prefix} under uv: {' '.join(modules)}")
    _STOPPING.clear()
    argv = ["uv", "run", "python", str(Path(__file__).resolve()), *modules]
    proc = _start_registered(argv, cwd, os.environ)
    if proc is None:
        return list(modules)
    try:
        rc, output = _communicate(proc, MODULE_TIMEOUT_SECS * len(modules))
    finally:
        with _LOCK:
            _LIVE.discard(proc)
    print(output, end="" if output.endswith("\n") else "\n")
    if rc == 0:
        return []
    named = [ln.removeprefix("failed: ").split() for ln in output.splitlines()
             if ln.startswith("failed: ")]
    return named[-1] if named else list(modules)


def _run_staged_modules(modules: list[str], cwd: Path) -> int:
    groups = group_modules(modules)
    within, deferred = split_e2e(groups["e2e"])
    for module in deferred:
        print(_deferral_line(module))
    core = groups["unit"] + groups["arch"]
    heavy = groups["unit-uv"] + groups["integration"] + within
    ran = core + heavy
    if not ran:
        return 0
    if heavy and _uv_missing(heavy, "staged:"):
        return 1
    failed = _run_all(core, cwd) if core else []
    if heavy:
        failed += _run_under_uv(heavy, cwd, "staged:")
    print(f"{len(ran) - len(failed)}/{len(ran)} modules passed")
    if failed:
        print("failed: " + " ".join(sorted(failed)))
    return 1 if failed else 0


def _staged_main(argv: list[str], cwd: Path) -> int:
    if argv[0] != "--staged" or any(arg.startswith("--") for arg in argv[1:]):
        print("usage: run_unittest_parallel.py --staged [PATH ...]", file=sys.stderr)
        return 2
    stale = stale_exception_names(discover_modules())
    if stale:
        print("error: stale exception names: " + " ".join(stale), file=sys.stderr)
        return 2
    stale = stale_machinery_names()
    if stale:
        print("error: stale shared machinery names: " + " ".join(stale), file=sys.stderr)
        return 2
    files, covering, reason = _staged_selection(argv[1:], cwd)
    if reason is not None:
        print(f"staged: full unit+arch run: {reason}")
        groups = group_modules(discover_modules())
        modules = sorted({*groups["unit"], *groups["arch"], *covering})
    elif not covering:
        print(f"staged: {files} files -> 0 modules" if files
              else "staged: no staged files; 0 modules")
        return 0
    else:
        modules = covering
        print(f"staged: {files} files -> {len(modules)} modules")
        for module in modules:
            print(f"staged: {module}")
    try:
        return _run_staged_modules(modules, cwd)
    except KeyboardInterrupt:
        _STOPPING.set()
        _stop_live_groups()
        print("interrupted: every module was stopped", file=sys.stderr)
        return 130


def _fallback(reason: str) -> list[str]:
    """Print why every over-budget e2e module runs at push, and return those modules."""
    print(f"{reason}; running every e2e module over the commit budget")
    return split_e2e(sorted(E2E_MODULES))[1]


# The proof that the pushed range is the whole push. pre-commit hands a pre-push hook one ref's
# range only, so the range is trusted only when the checkout is the pushed commit and no commit a
# local branch or worktree HEAD holds lies outside it (every such commit is then in the range or
# already on a remote). Like every push hook, this tests the checkout: a ref pushed alongside it is
# covered by the selection but run through the checkout's code.
# shortcut: local tags are left out of the proof (unpushed archive and backup tags would defeat it
# on every push); a tag pushed by name, --tags or --mirror together with the checked-out branch and
# pointing outside it, or a commit no branch or worktree HEAD reaches (a sha typed from the reflog)
# pushed as a second ref, is not seen; push such a ref on its own, which takes the fallback unless
# it points at the checkout.
def _proof_refusal(cwd: Path, mapper: ModuleType, to_ref: str) -> str | None:
    """Why the pushed range is not the whole push, or None when the proof holds."""
    if mapper.commit_sha(cwd, "HEAD") != mapper.commit_sha(cwd, to_ref):
        return f"pushed: the checkout HEAD is not the pushed commit {to_ref}"
    unpushed = mapper.outside_commits(cwd, to_ref)
    if unpushed:
        return (f"pushed: {len(unpushed)} unpushed local commits lie outside {to_ref}"
                " (another ref may be in this push)")
    return None


def _range_deferred(
    cwd: Path, mapper: ModuleType, from_ref: str, to_ref: str
) -> tuple[int, list[str]]:
    """(files in the range, over-budget e2e modules covering them). Raises when no covering set
    is known, so the caller falls back to every over-budget module."""
    paths = mapper.pushed_paths(cwd, from_ref, to_ref)
    decision = mapper.decide(cwd, paths, SHARED_MACHINERY)
    if not decision.index_built:
        raise RuntimeError(f"no covering set ({decision.full_reason})")
    covered = [module for module in decision.modules if module in E2E_MODULES]
    return len(paths), split_e2e(covered)[1]


def _range_problem(from_ref: str, to_ref: str) -> str | None:
    """Why pre-commit's range cannot be used, or None when both refs are usable."""
    if not from_ref or not to_ref:
        return "pushed: no push range"
    bad = next((ref for ref in (from_ref, to_ref) if ref.startswith("-")), None)
    return None if bad is None else f"pushed: bad ref {bad}"


def _pushed_modules(cwd: Path) -> list[str]:
    """The over-budget e2e modules this push runs: the pushed range's when the proof holds,
    otherwise every over-budget module with the reason printed."""
    from_ref = os.environ.get("PRE_COMMIT_FROM_REF", "")
    to_ref = os.environ.get("PRE_COMMIT_TO_REF", "")
    problem = _range_problem(from_ref, to_ref)
    if problem is not None:
        return _fallback(problem)
    try:
        mapper = _load_mapper()
        refusal = _proof_refusal(cwd, mapper, to_ref)
        if refusal is not None:
            return _fallback(refusal)
        count, deferred = _range_deferred(cwd, mapper, from_ref, to_ref)
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return _fallback(f"pushed: mapper error: {type(exc).__name__}: {exc}")
    print(f"pushed: {count} files in {from_ref}...{to_ref} -> {len(deferred)} deferred e2e modules")
    return deferred


def _pushed_main(argv: list[str], cwd: Path) -> int:
    if argv != ["--pushed"]:
        print("usage: run_unittest_parallel.py --pushed (takes no other argument)", file=sys.stderr)
        return 2
    modules = _pushed_modules(cwd)
    if not modules:
        print("pushed: no deferred e2e modules")
        return 0
    for module in modules:
        print(f"pushed: {module}")
    if _uv_missing(modules, "pushed:"):
        return 1
    try:
        failed = _run_under_uv(modules, cwd, "pushed:")
    except KeyboardInterrupt:
        _STOPPING.set()
        _stop_live_groups()
        print("interrupted: every module was stopped", file=sys.stderr)
        return 130
    print(f"{len(modules) - len(failed)}/{len(modules)} modules passed")
    if failed:
        print("failed: " + " ".join(sorted(failed)))
    return 1 if failed else 0


def _mode_main(argv: list[str], cwd: Path) -> int | None:
    """The --list-groups, --pushed and --staged modes; None for a run of test modules."""
    if argv == ["--list-groups"]:
        return _emit_group_listing()
    if "--pushed" in argv:
        return _pushed_main(argv, cwd)
    if "--staged" in argv:
        return _staged_main(argv, cwd)
    return None


def main(argv: list[str], cwd: Path = REPO_ROOT) -> int:
    mode_code = _mode_main(argv, cwd)
    if mode_code is not None:
        return mode_code
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
    # Longest recorded module first (e2e or hook table), so a slow one never starts last (a stable
    # sort).
    ordered = sorted(
        modules, key=lambda m: -(E2E_RECORDED_SECS.get(m) or HOOK_RECORDED_SECS.get(m, 0)))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(run_module, m, cwd) for m in ordered]
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
