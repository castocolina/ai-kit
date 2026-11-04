#!/usr/bin/env python3
"""The live-project check that replaced the tests reading `.planning/` (28 D-11).

Run as `make check-dogfood` (also a pre-push hook). It checks that the project's own cross-AI
runner copy is a pristine render of the shipped template, and that the curated-config write
flows leave the live `.planning/config.json*` and runner files untouched (they run in a child
process under the test runner's baseline env and tripwire). It prints only relative paths, test
ids and short reasons, never file contents or hashes.
"""
from __future__ import annotations

import argparse
import functools
import hashlib
import importlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILL_DIR = REPO_ROOT / "skills" / "ai-kit-gsd-curated-config"
RUNNER_REL = ".planning/scripts/cross-ai.mjs"
TEMPLATE_REL = "skills/ai-kit-spec-review/references/cross-ai.mjs"
PREFIX = "check-dogfood:"
GUARD_TIMEOUT_S = 600

# The curated-config write flows whose real-file hashes this command replaced. Running the tests
# reuses their whole flow, and their own assertions (exit 0, the scratch config, profile and
# runner) are what make a do-nothing run fail.
_REAL_INTEGRATION = "tests.test_curated_config_e2e.TestRealIntegration"
GUARD_TESTS = (
    f"{_REAL_INTEGRATION}.test_tracer_against_real_installed_gsd_tools",
    f"{_REAL_INTEGRATION}.test_parent_project_config_is_never_touched",
    "tests.test_curated_config_apply_e2e.TestRealApply.test_apply_golden_plan",
)
APPLY_GUARD = GUARD_TESTS[2]
# shortcut: the golden-plan apply skips while the checkout-local gsd-core is outside
# GSD_CORE_PREFIXES (1.18.0 on 2026-11-03), so apply writes to the live project are unguarded
# until that table-parity check lands (backlog 999.18); the run prints a warning each time.

GuardRun = Callable[[], tuple[int | None, str, list[str]]]


@functools.cache
def _script():
    """The skill's render module, imported on first use from the checkout's own skill folder."""
    sys.path.insert(0, str(SKILL_DIR))
    return importlib.import_module("ai_kit_gsd_curated_config.cross_ai_script")


def _outside_config(data: bytes) -> bytes | None:
    """Shebang plus the body before `// <config>` and from `// </config>`; None when the
    header or the config markers are unusable."""
    parts = _script().split_header(data)
    if parts is None:
        return None
    shebang, _header, body = parts
    start, end = body.find(b"// <config>"), body.find(b"// </config>")
    if not 0 <= start < end:
        return None
    return shebang + body[:start] + body[end:]


def _config_names_runner(root: Path) -> tuple[bool, str | None]:
    """(config.json names the runner as workflow.cross_ai_command, a problem or None)."""
    path = root / ".planning" / "config.json"
    if not path.is_file():
        return False, None
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False, ".planning/config.json is unreadable, so the absent runner copy is unjudged"
    command = (config.get("workflow") or {}).get("cross_ai_command") if isinstance(
        config, dict) else None
    return isinstance(command, str) and RUNNER_REL in command, None


def check_runner_copy(root: Path, template: Path) -> tuple[list[str], list[str]]:
    """(problems, notes) for the runner copy under `root` against `template`."""
    copy_path = root / RUNNER_REL
    if not copy_path.is_file():
        named, unreadable = _config_names_runner(root)
        problems = [unreadable] if unreadable else []
        if named:
            problems.append(f"{RUNNER_REL} is absent but .planning/config.json names it")
        return problems, ["runner copy absent"]
    try:
        tmpl = template.read_bytes()
    except OSError:
        return [f"template unreadable: {template.name}"], []
    copy = copy_path.read_bytes()
    problems = []
    try:
        if _script().template_version(copy) != _script().template_version(tmpl):
            problems.append(f"{RUNNER_REL} template version differs from the shipped template")
    except ValueError as exc:
        problems.append(f"{RUNNER_REL} header unusable: {exc}")
    state = _script().script_state(copy)
    if state != "pristine":
        problems.append(f"{RUNNER_REL} is {state}, not pristine")
    outside = _outside_config(copy)
    if outside is None or outside != _outside_config(tmpl):
        problems.append(f"{RUNNER_REL} differs from the template outside the config block")
    return problems, []


def _fingerprint(root: Path) -> dict[str, str]:
    """relative path -> sha256 of every `config.json*` and `cross-ai.mjs*` file of the live
    project; an absent file is simply not a key."""
    found = [*(root / ".planning").glob("config.json*"),
             *(root / ".planning" / "scripts").glob("cross-ai.mjs*")]
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in found if path.is_file()
    }


def _changed_files(before: dict[str, str], after: dict[str, str]) -> list[str]:
    tail = "during a curated-config run (or was edited meanwhile; re-run make check-dogfood)"
    problems = []
    for rel in sorted(before.keys() | after.keys()):
        if before.get(rel) == after.get(rel):
            continue
        kind = "added" if rel not in before else "removed" if rel not in after else "changed"
        problems.append(f"{rel} {kind} {tail}")
    return problems


_RESULT_RE = re.compile(
    r"\((?P<id>[\w.]+)\)(?:\n[^\n]*?)? \.\.\. "
    r"(?P<status>ok|FAIL|ERROR|skipped (?P<q>['\"])(?P<reason>.*)(?P=q))$",
    re.MULTILINE,
)


def parse_verbose(output: str) -> dict[str, tuple[str, str]]:
    """dotted id -> (status, reason) from `unittest -v` output; status is ok, FAIL, ERROR or
    skipped. A test with a docstring puts its result on the next line; a class-level skip is
    reported under the class id."""
    results = {}
    for match in _RESULT_RE.finditer(output):
        status = "skipped" if match["status"].startswith("skipped") else match["status"]
        results[match["id"]] = (status, match["reason"] or "")
    return results


def _result_for(results: dict[str, tuple[str, str]], test_id: str) -> tuple[str, str] | None:
    return results.get(test_id) or results.get(test_id.rsplit(".", 1)[0])


def _guard_report(results: dict[str, tuple[str, str]]) -> tuple[list[str], list[str]]:
    """Problems and notes from the child's parsed results; a skipped test is counted as
    skipped, never as executed."""
    problems, notes = [], []
    executed = skipped = 0
    for test_id in GUARD_TESTS:
        found = _result_for(results, test_id)
        if found is None:
            problems.append(f"no-write guard missing result: {test_id}")
        elif found[0] == "skipped":
            skipped += 1
            notes.append(f"no-write guard skipped: {test_id}: {found[1]}")
        else:
            executed += 1
            if found[0] != "ok":
                problems.append(f"no-write guard failed: {test_id}")
    notes.append(
        f"no-write guard: {len(GUARD_TESTS)} attempted, {executed} executed, {skipped} skipped")
    apply_result = _result_for(results, APPLY_GUARD)
    if apply_result and apply_result[0] == "skipped":
        notes.append(
            f"warning: the apply no-write guard did not run ({apply_result[1]}); apply writes "
            "to the live project are unguarded until it runs")
    return problems, notes


def _load_runner():
    """tools/run_unittest_parallel.py by file path (it is a script, not a package)."""
    path = REPO_ROOT / "tools" / "run_unittest_parallel.py"
    spec = importlib.util.spec_from_file_location("run_unittest_parallel", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _run_guard_tests() -> tuple[int | None, str, list[str]]:
    """(child rc or None on timeout, its output, tripwire log lines). The child runs from the
    checkout cwd in its own session under the runner's baseline env (temporary HOME,
    AI_KIT_REFUSE_REAL_HOME=1, host-CLI tripwire first on PATH)."""
    runner = _load_runner()
    scratch = Path(tempfile.mkdtemp(prefix="aikit-dogfood-"))
    try:
        log = runner.write_tripwire(scratch / "tripwire")
        env = runner.baseline_env(os.environ, scratch, log.parent / "bin")
        argv = [sys.executable, "-m", "unittest", "-v", *GUARD_TESTS]
        with subprocess.Popen(
            argv, cwd=REPO_ROOT, env=env, text=True, start_new_session=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        ) as proc:
            try:
                output, _ = proc.communicate(timeout=GUARD_TIMEOUT_S)
                rc: int | None = proc.returncode
            except subprocess.TimeoutExpired:
                runner.stop_process_group(proc)
                rc, output = None, ""
        return rc, output, log.read_text(encoding="utf-8", errors="replace").splitlines()
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def check_no_write(root: Path, run: GuardRun | None = None) -> tuple[list[str], list[str]]:
    """(problems, notes) for one run of GUARD_TESTS bracketed by fingerprints of the live
    `config.json*` and `cross-ai.mjs*` files under `root`; `run` is the test seam."""
    before = _fingerprint(root)
    rc, output, calls = (run or _run_guard_tests)()
    problems = _changed_files(before, _fingerprint(root))
    if rc is None:
        problems.append(f"no-write guard timed out after {GUARD_TIMEOUT_S}s")
    elif rc != 0:
        problems.append(f"no-write guard child exited {rc}")
    guard_problems, notes = _guard_report(parse_verbose(output))
    problems += guard_problems
    if calls:
        problems.append(f"no-write guard host CLI calls: {'; '.join(calls)}")
    return problems, notes


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--root", type=Path, default=REPO_ROOT,
                        help="checkout whose runner copy is checked")
    parser.add_argument("--template", type=Path, default=REPO_ROOT / TEMPLATE_REL)
    parser.add_argument("--skip-no-write", action="store_true",
                        help="skip the no-write guard (runner-copy check only)")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    if not args.skip_no_write and root != REPO_ROOT:
        # The guard child always runs in this checkout, so it can only bracket this checkout.
        print(f"{PREFIX} --root applies to the runner-copy check only; add --skip-no-write")
        return 2
    problems, notes = check_runner_copy(root, args.template)
    if not args.skip_no_write:
        write_problems, write_notes = check_no_write(root)
        problems, notes = problems + write_problems, notes + write_notes
    for line in [*notes, *problems]:
        print(f"{PREFIX} {line}")
    if problems:
        return 1
    print(f"{PREFIX} ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
