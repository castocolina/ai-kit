#!/usr/bin/env python3
"""The six-environment proof of SPEC R7: `make test-env-matrix`.

Runs every test tier (`make -j1 -k -C <checkout> test`) in six environments, one after another
(never concurrently), and compares the results module by module: pass or fail, and the skip
reasons. The plain run is the baseline and must itself be green and complete (make rc 0, exactly
one report for every expected module, no failure); otherwise the matrix stops with
`env plain: baseline not green`. Every other environment must match plain's make rc, its module
inventory and its results. A host CLI call logged by an outer shim fails the matrix too.

Not part of `make test`, `make validate` or any hook (tests/test_gate_scope.py pins that). Six
environments take about six times the plain run, so run it in the background and wait for it.

What it can and cannot show: the runner baseline already strips host signals, puts the tripwire
stubs first on PATH and runs every module with cwd = the checkout. So for runner modules the
host-session, no-host-cli and outside-git environments differ only before the runner (make, uv)
and in `bash tests/test_install.sh`, which does not run through the runner. `outside-git` checks
a run started from a cwd outside any repository; `make -C <checkout>` still runs the recipes, uv
and the install script in the checkout. `no-host-cli` proves the host executables are absent from
PATH, not uninstalled, and runner modules still see the tripwire stubs first on PATH in every
environment. The module-level evidence comes mainly from the long-path and custom-tmpdir
environments. The long-path clone has no `.planning/` (removed after the clone), so it is the
run-time check of the rule that no test may read `.planning/`.
"""

import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from types import ModuleType
from typing import NamedTuple

TOOLS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TOOLS_DIR.parent
ENV_NAMES = ("plain", "host-session", "no-host-cli", "long-path", "custom-tmpdir", "outside-git")
BASELINE = "plain"
# Make variables an outer `make -jN` leaves behind: the inner make must run serially and alone.
SCRUBBED_MAKE_VARS = ("MAKEFLAGS", "MFLAGS", "MAKELEVEL")
MAKE_ARGS = ("-j1", "-k")
# The long-path environment's checkout path is at least this long (SPEC R7's long-path case).
LONG_PATH_MIN = 200


def _load_runner() -> ModuleType:
    """The runner by file path (as tools/staged_mapper.py does): its constants and helpers."""
    spec = importlib.util.spec_from_file_location(
        "run_unittest_parallel", TOOLS_DIR / "run_unittest_parallel.py"
    )
    if spec is None or spec.loader is None:
        raise ImportError("cannot load tools/run_unittest_parallel.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


runner = _load_runner()


class Report(NamedTuple):
    """One module's result as the matrix compares it. plan 28-09 reuses this shape."""

    passed: bool
    skips: tuple[str, ...]
    ran: int


class Spec(NamedTuple):
    """One environment: its env, the cwd and checkout make runs in, its reports folder and the
    outer logging-shim folder (None when the environment has no shim folder)."""

    name: str
    env: dict[str, str]
    cwd: Path
    checkout: Path
    reports: Path
    shims: Path | None


def say(line: str) -> None:
    print(line, flush=True)


def _report_rank(path: Path) -> tuple[str, int]:
    """Orders a module's files as the runner created them: `<module>.json` first, then
    `<module>.2.json`, `<module>.3.json` (a plain name sort would put .10 before .2)."""
    stem = path.name.removesuffix(".json")
    base, dot, number = stem.rpartition(".")
    if dot and number.isdigit():
        return base, int(number)
    return stem, 1


def load_reports(directory: Path) -> tuple[dict[str, Report], list[str]]:
    """The reports in `directory`, keyed by module, and one line per module that has more than
    one report file (the first one, as created, is kept)."""
    files: dict[str, list[str]] = {}
    reports: dict[str, Report] = {}
    for path in sorted(directory.glob("*.json"), key=_report_rank):
        data = json.loads(path.read_text(encoding="utf-8"))
        module = data["module"]
        files.setdefault(module, []).append(path.name)
        if len(files[module]) == 1:
            reports[module] = Report(data["rc"] == 0, tuple(data["skips"]), data["ran"])
    duplicates = [
        f"duplicate report: {module} ({', '.join(names)})"
        for module, names in sorted(files.items()) if len(names) > 1
    ]
    return reports, duplicates


def expected_modules(checkout: Path) -> set[str]:
    """Every module of every group, discovered from the checkout's own tests folder."""
    groups = runner.group_modules(runner.discover_modules(checkout / "tests"))
    return {name for names in groups.values() for name in names}


def inventory_problems(
    reports: dict[str, Report], expected: set[str], duplicates: list[str]
) -> list[str]:
    """Missing, extra and duplicated reports: one line each."""
    problems = [f"no report for {module}" for module in sorted(expected - reports.keys())]
    problems += [f"unexpected report for {module}"
                 for module in sorted(reports.keys() - expected)]
    return problems + duplicates


def baseline_problems(
    reports: dict[str, Report], make_rc: int, expected: set[str], duplicates: list[str]
) -> list[str]:
    """Why the plain run cannot serve as the baseline; [] only for a green, complete run."""
    problems = [] if make_rc == 0 else [f"make exited {make_rc}"]
    problems += inventory_problems(reports, expected, duplicates)
    problems += [f"failing module: {module}"
                 for module, report in sorted(reports.items()) if not report.passed]
    return problems


def compare_reports(baseline: dict[str, Report], other: dict[str, Report]) -> list[str]:
    """One line per module that is missing from or extra in `other`, or whose pass or fail or
    skip reasons differ. `ran` is not compared: it is the same tests either way."""
    lines = []
    for module in sorted(baseline.keys() | other.keys()):
        if module not in other:
            lines.append(f"{module}: missing in this environment")
        elif module not in baseline:
            lines.append(f"{module}: extra in this environment")
        else:
            lines.extend(_module_difference(module, baseline[module], other[module]))
    return lines


def _module_difference(module: str, base: Report, here: Report) -> list[str]:
    lines = []
    if base.passed != here.passed:
        lines.append(f"{module}: plain {_verdict(base)}, this environment {_verdict(here)}")
    if base.skips != here.skips:
        lines.append(f"{module}: skip reasons differ: plain {list(base.skips)}, "
                     f"this environment {list(here.skips)}")
    return lines


def _verdict(report: Report) -> str:
    return "passed" if report.passed else "failed"


def make_command(checkout: Path) -> list[str]:
    """The inner command: serial make over the whole test target, in the checkout."""
    return ["make", *MAKE_ARGS, "-C", str(checkout), "test"]


def run_make(argv: list[str], env: dict[str, str], cwd: Path) -> int:
    """Run one inner make with its output on this process's output; return its rc."""
    return subprocess.run(argv, env=env, cwd=cwd, check=False).returncode


def run_environment(spec: Spec) -> tuple[int, dict[str, Report], list[str], float]:
    """Run the inner make for `spec`; return its rc, its reports, the duplicate lines, seconds."""
    start = time.monotonic()
    rc = run_make(make_command(spec.checkout), spec.env, spec.cwd)
    secs = time.monotonic() - start
    reports, duplicates = load_reports(spec.reports)
    return rc, reports, duplicates, secs


def host_calls(spec: Spec) -> list[str]:
    """The calls the outer logging shims recorded during the environment's run."""
    if spec.shims is None:
        return []
    log = spec.shims / "calls.log"
    return log.read_text(encoding="utf-8", errors="replace").splitlines() if log.exists() else []


def _scrubbed(name: str) -> bool:
    """Caller variables no matrix environment keeps: make job state, host signals, host config,
    credentials and git state (GIT_EXEC_PATH stays, as in the runner's baseline)."""
    return (
        name in SCRUBBED_MAKE_VARS or name in runner.HOST_SIGNAL_VARS
        or name in runner.HOME_OVERRIDE_VARS or name in runner.CREDENTIAL_ENV_VARS
        or name.startswith(runner.HOST_CONFIG_ENV_PREFIXES)
        or (name.startswith("GIT_") and name not in runner.GIT_KEPT_VARS)
    )


def base_env(caller: dict[str, str], forwards: dict[str, str], folder: Path) -> dict[str, str]:
    """The caller's environment minus what no matrix environment keeps, a scratch HOME with the
    caller's toolchain forwards (computed once, before HOME changes), AI_KIT_REFUSE_REAL_HOME=1
    and this environment's reports folder."""
    home = folder / "home"
    home.mkdir(parents=True)
    env = {name: value for name, value in caller.items() if not _scrubbed(name)}
    env.update(forwards)
    env.update({
        "HOME": str(home),
        "AI_KIT_REFUSE_REAL_HOME": "1",
        runner.REPORT_DIR_ENV: str(folder / "reports"),
    })
    return env


def _join_path(*parts: str | Path) -> str:
    return os.pathsep.join(str(part) for part in parts if str(part))


def _git_env() -> dict[str, str]:
    """The caller's environment without git's own variables (a commit hook exports some)."""
    return {name: value for name, value in os.environ.items() if not name.startswith("GIT_")}


def _git_lines(repo: Path, *args: str) -> list[str]:
    """The NUL-separated output of one git command in `repo`."""
    out = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, check=True,
                         env=_git_env()).stdout
    return [os.fsdecode(raw) for raw in out.split(b"\0") if raw]


def long_checkout_path(scratch: Path) -> Path:
    """A checkout path of at least LONG_PATH_MIN characters under `scratch`."""
    path = scratch / "checkout"
    depth = 0
    while len(str(path)) < LONG_PATH_MIN:
        depth += 1
        path = path / f"segment-{depth:02d}-long-checkout-padding"
    return path


def host_free_path(farm: Path, path_value: str, names) -> str:
    """A folder of symlinks to every executable on `path_value` except `names` (first copy of a
    name wins); returns it as the whole PATH. Raises if a name is still found on it."""
    farm.mkdir(parents=True, exist_ok=True)
    for folder in path_value.split(os.pathsep):
        if not folder or not os.path.isdir(folder):
            continue
        for entry in sorted(os.listdir(folder)):
            full = os.path.abspath(os.path.join(folder, entry))
            if entry in names or not os.path.isfile(full) or not os.access(full, os.X_OK):
                continue
            if not os.path.lexists(farm / entry):
                os.symlink(full, farm / entry)
    for name in names:
        if shutil.which(name, path=str(farm)) is not None:
            raise RuntimeError(f"host CLI {name} is still on the no-host PATH")
    return str(farm)


def _ensure_parent(target: Path, rel: str) -> None:
    """Make the folders above `rel` real folders in the clone; a file or link in the way is
    removed (a link is unlinked, never followed)."""
    parent = target
    for part in Path(rel).parts[:-1]:
        parent = parent / part
        if os.path.lexists(parent) and (os.path.islink(parent) or not os.path.isdir(parent)):
            os.unlink(parent)
        parent.mkdir(exist_ok=True)


def _overlay_one(source: Path, target: Path, rel: str) -> None:
    """Make the clone's `rel` hold the source's state: remove what is there (lexists: a link is
    unlinked, never written through), then recreate a link or a file; a folder is skipped."""
    _ensure_parent(target, rel)
    dst = target / rel
    if os.path.lexists(dst):
        if os.path.isdir(dst) and not os.path.islink(dst):
            shutil.rmtree(dst)
        else:
            os.unlink(dst)
    src = source / rel
    if os.path.islink(src):
        os.symlink(os.readlink(src), dst)
    elif os.path.isfile(src):
        shutil.copy2(src, dst)


def make_long_checkout(source: Path, target: Path) -> Path:
    """A clone of `source` holding the same bytes as its working tree: committed history, every
    path that differs from HEAD (staged or not, both sides of a rename), every untracked
    non-ignored file, the gitignored gsd-core and scripts folders, and no .planning/."""
    target.parent.mkdir(parents=True, exist_ok=True)
    # --no-hardlinks: /tmp is a different device from the checkout, and git cannot hard-link
    # across devices (`git clone --local` fails there with "Invalid cross-device link").
    subprocess.run(["git", "clone", "--quiet", "--local", "--no-hardlinks", str(source),
                    str(target)], check=True, capture_output=True, env=_git_env())
    paths = set(_git_lines(source, "diff", "--name-only", "-z", "--no-renames", "HEAD"))
    paths |= set(_git_lines(source, "ls-files", "-z", "-o", "--exclude-standard"))
    for rel in sorted(p for p in paths if p != ".planning" and not p.startswith(".planning/")):
        _overlay_one(source, target, rel)
    for rel in (".claude/gsd-core", ".claude/scripts"):
        if os.path.isdir(source / rel) and not os.path.islink(source / rel):
            (target / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(source / rel, target / rel, symlinks=True, dirs_exist_ok=True)
    planning = target / ".planning"
    if os.path.islink(planning) or os.path.isfile(planning):
        os.unlink(planning)
    elif os.path.isdir(planning):
        shutil.rmtree(planning)
    return target


def custom_tmpdir(folder: Path) -> Path:
    """A TMPDIR whose path has a space and lies inside a freshly initialised git repository.
    The repository also holds a synthetic `.planning/config.json`, so a project the tests
    create under TMPDIR sits inside another GSD project."""
    repo = folder / "repo with space"
    tmp_dir = repo / "tmp dir"
    tmp_dir.mkdir(parents=True)
    subprocess.run(["git", "-C", str(repo), "init", "-q"], check=True, capture_output=True,
                   env=_git_env())
    (repo / ".planning").mkdir()
    (repo / ".planning" / "config.json").write_text(
        '{"model_profile": "balanced"}\n', encoding="utf-8"
    )
    return tmp_dir


def build_spec(
    name: str, caller: dict[str, str], forwards: dict[str, str], scratch: Path, source: Path
) -> Spec:
    """The environment `name` over the checkout `source`, under the scratch root `scratch`."""
    folder = scratch / name
    env = base_env(caller, forwards, folder)
    shims: Path | None = folder / "shims"
    cwd = checkout = source
    if name == "no-host-cli":
        env["PATH"] = host_free_path(folder / "farm", caller.get("PATH", ""),
                                     runner.HOST_CLI_NAMES)
        shims = None
    else:
        runner.write_tripwire(folder / "shims")
        env["PATH"] = _join_path(folder / "shims" / "bin", caller.get("PATH", ""))
    if name == "host-session":
        env.update(dict.fromkeys(runner.HOST_SIGNAL_VARS, "1"))
    elif name == "long-path":
        checkout = make_long_checkout(source, long_checkout_path(folder))
        cwd = checkout
        env.update({"UV_PROJECT_ENVIRONMENT": str(source / ".venv"), "UV_NO_SYNC": "1"})
    elif name == "custom-tmpdir":
        env["TMPDIR"] = str(custom_tmpdir(folder))
    elif name == "outside-git":
        cwd = folder / "outside"
        cwd.mkdir(parents=True)
    elif name not in (BASELINE, "no-host-cli"):
        raise ValueError(f"unknown environment {name}")
    return Spec(name, env, cwd, checkout, folder / "reports", shims)


def inside_git_worktree(path: Path) -> bool:
    """True when `path` lies inside a git work tree (git's own variables are not inherited)."""
    proc = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "--is-inside-work-tree"],
        capture_output=True, text=True, check=False, env=_git_env(),
    )
    return proc.returncode == 0 and proc.stdout.strip() == "true"


def run_order(only: list[str] | None) -> list[str]:
    """The environments to run: plain first and always, then the others in ENV_NAMES order."""
    chosen = set(only or ENV_NAMES) | {BASELINE}
    return [name for name in ENV_NAMES if name in chosen]


def _env_differences(
    spec: Spec, baseline: dict[str, Report], base_rc: int, outcome: tuple
) -> list[str]:
    """The differences of one non-plain environment against plain (make rc, inventory, results)."""
    rc, reports, duplicates, _secs = outcome
    expected = expected_modules(spec.checkout)
    lines = [] if rc == base_rc else [f"make rc {rc}, plain rc {base_rc}"]
    return lines + inventory_problems(reports, expected, duplicates) + compare_reports(
        baseline, reports
    )


def _say_result(name: str, problems: list[str], calls: list[str], outcome: tuple) -> None:
    rc, reports, _duplicates, secs = outcome
    for line in calls:
        say(f"env {name}: host CLI calls: {line}")
    if problems:
        say(f"env {name}: {len(problems)} differences")
        for line in problems:
            say(f"  {line}")
    else:
        say(f"env {name}: identical ({len(reports)} modules, make rc {rc}, {secs:.0f}s)")


def _run_plain(spec: Spec) -> tuple[bool, tuple, dict[str, Report], int]:
    """The baseline: green and complete, or the matrix stops."""
    outcome = run_environment(spec)
    rc, reports, duplicates, secs = outcome
    problems = baseline_problems(reports, rc, expected_modules(spec.checkout), duplicates)
    if problems:
        say("env plain: baseline not green:")
        for line in problems:
            say(f"  {line}")
        say("matrix: differences found")
        return False, outcome, reports, rc
    say(f"matrix: plain took {secs:.0f}s; expect about {6 * secs:.0f}s for six environments")
    return True, outcome, reports, rc


def _run_matrix(names: list[str], caller: dict[str, str], forwards: dict[str, str],
                scratch: Path) -> int:
    baseline: dict[str, Report] = {}
    base_rc = 0
    failed = False
    for name in names:
        spec = build_spec(name, caller, forwards, scratch, REPO_ROOT)
        if name == "long-path":
            say(f"env long-path: checkout path is {len(str(spec.checkout))} characters")
        say(f"env {name}: running make -j1 -k -C {spec.checkout} test")
        if name == BASELINE:
            green, outcome, baseline, base_rc = _run_plain(spec)
            if not green:
                return 1
            problems: list[str] = []
        else:
            outcome = run_environment(spec)
            problems = _env_differences(spec, baseline, base_rc, outcome)
        calls = host_calls(spec)
        _say_result(name, problems, calls, outcome)
        failed = failed or bool(problems) or bool(calls)
    if failed:
        say("matrix: differences found")
        return 1
    say(f"matrix: identical in {len(names)} environments")
    return 0


def _parser() -> argparse.ArgumentParser:
    listing = "\n".join(f"  {name}" for name in ENV_NAMES)
    parser = argparse.ArgumentParser(
        description="Run all four test tiers in six environments and compare the results "
                    "module by module (SPEC R7). plain always runs first as the baseline.\n\n"
                    "environments:\n" + listing,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--only", action="append", choices=ENV_NAMES, metavar="NAME",
        help="run only this environment (repeatable; plain is always run first)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    names = run_order(args.only)
    caller = dict(os.environ)
    forwards = runner.tool_cache_forwards(caller)
    scratch = Path(tempfile.mkdtemp(prefix="aikit-matrix-"))
    try:
        if inside_git_worktree(scratch):
            print(f"matrix: refusing: scratch root {scratch} is inside a git work tree",
                  file=sys.stderr)
            return 2
        return _run_matrix(names, caller, forwards, scratch)
    finally:
        shutil.rmtree(scratch)


if __name__ == "__main__":
    sys.exit(main())
