#!/usr/bin/env python3
"""The live-project check that replaced the tests reading `.planning/` (28 D-11).

Run as `make check-dogfood` (also a pre-push hook). It checks that the project's own cross-AI
runner copy is a pristine render of the shipped template, and that the curated-config write
flows leave the live `.planning/config.json*` and runner files untouched (they run in a child
process under the test runner's baseline env and tripwire). It prints only relative paths, test
ids and short reasons, never file contents or hashes. When the project has a gsd-core, it also
checks the GSD flow config (branch per phase, healthy, the capability and its hook points)
through read-only gsd-tools calls. It also runs the edge-floor check on every current phase SPEC
that has an Edge Coverage section. It also checks that every ROADMAP phase after 32 that names a
SKILL.md cites JDG-04 in its success criteria. It also runs tools/judge_loop.py check on the judge
records.
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
from typing import Any

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
# The golden-plan apply skips only when the checkout-local gsd-core is older than
# GSD_CORE_MIN_VERSION (tests/test_curated_config_apply_e2e.py); the run then prints an
# unguarded-apply warning.

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
    skipped, never as executed, and a skipped guard other than the apply guard is a problem."""
    problems, notes = [], []
    executed = skipped = 0
    for test_id in GUARD_TESTS:
        found = _result_for(results, test_id)
        if found is None:
            problems.append(f"no-write guard missing result: {test_id}")
        elif found[0] == "skipped":
            skipped += 1
            notes.append(f"no-write guard skipped: {test_id}: {found[1]}")
            if test_id != APPLY_GUARD:  # only the apply guard's skip is the documented exception
                problems.append(f"no-write guard skipped: {test_id}; the live project is unguarded")
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


GSD_TOOLS_REL = ".claude/gsd-core/bin/gsd-tools.cjs"
FLOW_CAP = "ai-kit-commit-fold"
# point -> (hook kind, the text the hook must run). GSD dispatches commands at steps and gates;
# a contribution is text the planner acts on, so its expected text is a command the planner runs.
# FLOW_EMPTY_POINTS must hold no entry at all.
FLOW_EXPECT = {
    "discuss:pre": ("step", "ai-kit-fold start"),
    "plan:pre": ("contribution", "ai-kit-fold boundary-plan"),
    "execute:wave:pre": ("step", "ai-kit-fold boundary-wave"),
    "execute:wave:post": ("step", "ai-kit-fold checkpoint"),
    "ship:pre": ("gate", "ai-kit-fold ship"),
}
FLOW_EMPTY_POINTS = ("verify:post",)

FlowRun = Callable[..., subprocess.CompletedProcess[str]]


def _run_gsd(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """One project-local gsd-tools call (argv list, no shell)."""
    return subprocess.run(["node", str(root / GSD_TOOLS_REL), *args], cwd=root,
                          capture_output=True, text=True, timeout=60, check=False)


def _parse_json(text: str) -> object | None:
    """The first JSON object or array in `text` (gsd-tools may print a line before it)."""
    starts = [i for i in (text.find("{"), text.find("[")) if i >= 0]
    if not starts:
        return None
    try:
        return json.JSONDecoder().raw_decode(text[min(starts):])[0]
    except ValueError:
        return None


def _active_hooks(root: Path, run: FlowRun, point: str) -> list[dict] | None:
    proc = run(root, "loop", "render-hooks", point, "--raw")
    report = _parse_json(proc.stdout) if proc.returncode == 0 else None
    if not isinstance(report, dict) or not isinstance(report.get("activeHooks"), list):
        return None
    return [hook for hook in report["activeHooks"] if isinstance(hook, dict)]


def _sub_command(hook: dict, *keys: str) -> object:
    """The value at `keys` inside one hook entry, or None when any level is absent."""
    value: object = hook
    for key in keys:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value


def _hook_text(hook: dict) -> str:
    return f"{_sub_command(hook, 'ref', 'command') or ''} " \
           f"{_sub_command(hook, 'check', 'predicate', 'command') or ''} " \
           f"{_sub_command(hook, 'fragment', 'inline') or ''}"


def _fold_entries(hooks: list[dict]) -> list[dict]:
    return [hook for hook in hooks
            if hook.get("capId") == FLOW_CAP or "ai-kit-fold" in _hook_text(hook)]


def _check_point(point: str, hooks: list[dict] | None) -> list[str]:
    """The one named problem for the first drift found at an expected point, or none."""
    kind, expected = FLOW_EXPECT[point]
    if hooks is None:
        return [f"{point}: loop render-hooks gave no hook list"]
    entries = _fold_entries(hooks)
    if len(entries) != 1:
        return [f"{point}: expected one {FLOW_CAP} {kind}, found {len(entries)}"]
    hook = entries[0]
    command = _sub_command(hook, "ref", "command")
    checks = [
        (hook.get("capId") == FLOW_CAP, f"entry capId {hook.get('capId')} is not {FLOW_CAP}"),
        (hook.get("kind") == kind, f"entry kind {hook.get('kind')} is not {kind}"),
        (kind != "step" or command == expected,
         f"step command {command!r} is not {expected!r}"),
        (kind != "gate" or expected in _hook_text(hook), f"gate does not run {expected}"),
        (kind != "gate" or hook.get("blocking") is True, "gate is not blocking"),
        (kind != "contribution" or hook.get("into") == "planner",
         "contribution is not into planner"),
        (kind != "contribution" or expected in _hook_text(hook),
         f"contribution does not run {expected}"),
    ]
    failed = [message for ok, message in checks if not ok]
    return [f"{point}: {failed[0]}"] if failed else []


def check_flow_config(root: Path, run: FlowRun = _run_gsd) -> tuple[list[str], list[str]]:
    """(problems, notes) for ai-kit's own GSD flow: branch per phase, clean health, the capability
    installed, and the hook points of the capability (read-only; `run` is the test seam)."""
    if not (root / GSD_TOOLS_REL).is_file():
        return [], ["flow config not checked: no project-local gsd-core"]
    problems = []
    branching = run(root, "config-get", "git.branching_strategy", "--raw").stdout.strip()
    if branching != "phase":
        problems.append(f"git.branching_strategy is {branching or 'unset'}, not phase")
    health = _parse_json(run(root, "validate", "health", "--raw").stdout)
    if not isinstance(health, dict):
        problems.append("validate health printed no JSON report")
    else:
        codes = [str(w.get("code", "?")) for w in health.get("warnings") or []
                 if isinstance(w, dict)]
        if health.get("status") != "healthy" or codes:
            warned = f" with warnings {', '.join(codes)}" if codes else ""
            problems.append(f"validate health is {health.get('status')}{warned}")
    caps = _parse_json(run(root, "capability", "list", "--raw").stdout)
    installed = isinstance(caps, list) and any(
        isinstance(cap, dict) and cap.get("id") == FLOW_CAP for cap in caps)
    if not installed:
        problems.append(f"capability {FLOW_CAP} is not installed")
        return problems, []
    for point in FLOW_EXPECT:
        problems += _check_point(point, _active_hooks(root, run, point))
    for point in FLOW_EMPTY_POINTS:
        hooks = _active_hooks(root, run, point)
        if hooks is None:
            problems.append(f"{point}: loop render-hooks gave no hook list")
        elif _fold_entries(hooks):
            problems.append(f"{point} lists a {FLOW_CAP} entry; GSD never dispatches it there")
    return problems, []


LENS_BRIEF_REL = ".planning/lens-brief/SKILL.md"
LENS_BRIEF_ENTRY = ".planning/lens-brief"
BRIEF_ENTRY = ".aikit/brief"
BRIEF_AGENTS = ("gsd-phase-researcher", "gsd-planner", "gsd-executor")
JEV_ENTRY = "skills/jev-fast-decision"
TRUSTED_ROOTS = ["~/.agents/skills"]
_LENS_LINE = re.compile(r"^- (gsd-[\w-]+): (\S+)$")


def _expected_lenses(brief: str) -> dict[str, str]:
    """agent -> lens entry, from the brief's `## Expected lenses` list only."""
    lenses, in_section = {}, False
    for line in brief.splitlines():
        if line.startswith("## "):
            in_section = line.strip() == "## Expected lenses"
        match = _LENS_LINE.match(line) if in_section else None
        if match:
            lenses[match.group(1)] = match.group(2)
    return lenses


def _lens_problem(agent: str, lens: str, entries: list) -> str | None:
    if lens not in entries:
        return f"{agent}: lens {lens} is not in its list"
    if entries[0] != lens:
        return f"{agent}: lens {lens} is not first"
    if entries[1:2] != [LENS_BRIEF_ENTRY]:
        return f"{agent}: {LENS_BRIEF_ENTRY} is not right after the lens"
    return None


def _brief_problem(agent: str, entries: list) -> str | None:
    if LENS_BRIEF_ENTRY not in entries:
        return f"{agent}: {LENS_BRIEF_ENTRY} is missing"
    if BRIEF_ENTRY not in entries:
        return f"{agent}: {BRIEF_ENTRY} is missing"
    if entries.index(LENS_BRIEF_ENTRY) > entries.index(BRIEF_ENTRY):
        return f"{agent}: {LENS_BRIEF_ENTRY} is not before {BRIEF_ENTRY}"
    return None


def _list_problem(agent: str, lens: str | None, entries: list) -> str | None:
    """The first named problem in one agent's list, or None."""
    problem = _lens_problem(agent, lens, entries) if lens is not None else None
    if problem is None and JEV_ENTRY not in entries:
        problem = f"{agent}: {JEV_ENTRY} is missing"
    if problem is None and agent in BRIEF_AGENTS:
        problem = _brief_problem(agent, entries)
    return problem


def check_lens_wiring(root: Path, run: FlowRun = _run_gsd) -> tuple[list[str], list[str]]:
    """(problems, notes) for the lens and unit-brief wiring in agent_skills (read-only: config-get
    only). `run` is the test seam."""
    brief_file = root / LENS_BRIEF_REL
    if not brief_file.is_file():
        return [], [f"lens wiring not checked: no {LENS_BRIEF_REL}"]
    if not (root / GSD_TOOLS_REL).is_file():
        return [], ["lens wiring not checked: no project-local gsd-core"]
    lenses = _expected_lenses(brief_file.read_text(encoding="utf-8"))
    skills = _parse_json(run(root, "config-get", "agent_skills").stdout)
    if not isinstance(skills, dict):
        return ["agent_skills printed no JSON object"], []
    problems = []
    for agent in sorted({*lenses, *BRIEF_AGENTS}):
        entries = skills.get(agent)
        if not isinstance(entries, list):
            problems.append(f"{agent}: no agent_skills list")
            continue
        problem = _list_problem(agent, lenses.get(agent), entries)
        if problem:
            problems.append(problem)
    for agent, entries in skills.items():
        for entry in entries if isinstance(entries, list) else []:
            if isinstance(entry, str) and entry.startswith("/"):
                problems.append(f"{agent}: entry {entry} is an absolute path")
            if isinstance(entry, str) and entry.startswith("global:") \
                    and lenses.get(agent) != entry:
                problems.append(f"{agent}: global entry {entry} is not in the lens brief")
    # No --raw: raw prints a one-element array as its bare string, not as JSON.
    roots_out = run(root, "config-get", "agent_skills_security.trusted_global_roots").stdout
    roots = _parse_json(roots_out)
    if roots != TRUSTED_ROOTS:
        problems.append(f"trusted_global_roots is {roots!r}, not {TRUSTED_ROOTS!r}")
    review = run(root, "config-get", "workflow.ui_review", "--raw").stdout.strip()
    if review != "true":
        problems.append(f"workflow.ui_review is {review or 'unset'}, not true")
    return problems, []


EDGE_FLOOR_REL = "skills/ai-kit-gsd-spec-discuss/scripts/edge_floor.py"
EDGE_ENGINE_REL = ".claude/gsd-core/bin/lib/edge-probe.cjs"
_EDGE_SECTION = re.compile(r"^## Edge Coverage", re.MULTILINE)


def _run_floor(root: Path, spec_rel: str) -> subprocess.CompletedProcess[str]:
    """This checkout's edge-floor script against the checked root's engine (argv list, no shell)."""
    return subprocess.run([sys.executable, str(REPO_ROOT / EDGE_FLOOR_REL), "check",
                           str(root / spec_rel), "--engine", str(root / EDGE_ENGINE_REL)],
                          cwd=root, capture_output=True, text=True, timeout=120, check=False)


def _drift_problem(rel: str, stdout: str) -> str:
    result = _parse_json(stdout)
    missing = result.get("missing") if isinstance(result, dict) else None
    if not isinstance(missing, list):
        return f"edge floor drift: {rel} missing (unreadable result)"
    rows = ", ".join(" ".join(str(part) for part in item)
                     for item in missing if isinstance(item, list))
    return f"edge floor drift: {rel} missing {rows or 'no rows listed'}"


def check_edge_floors(root: Path, run: FlowRun = _run_floor,
                      which: Callable[[str], str | None] = shutil.which,
                      ) -> tuple[list[str], list[str]]:
    """(problems, notes): the edge-floor check on each phase SPEC that has an Edge Coverage section,
    in sorted path order. A SPEC without that section is a note, never a problem."""
    phases = root / ".planning" / "phases"
    if not which("node"):
        return [], ["edge floors not checked: node not found"]
    if not (root / EDGE_ENGINE_REL).is_file():
        return [], ["edge floors not checked: no project-local gsd-core engine"]
    if not phases.is_dir():
        return [], ["edge floors not checked: no .planning/phases"]
    problems, notes = [], []
    for phase_dir in sorted(path for path in phases.iterdir() if path.is_dir()):
        spec = phase_dir / f"{phase_dir.name.split('-', 1)[0]}-SPEC.md"
        if not spec.is_file():
            continue
        rel = spec.relative_to(root).as_posix()
        if not _EDGE_SECTION.search(spec.read_text(encoding="utf-8", errors="replace")):
            notes.append(f"edge floor for {rel} not checked: no Edge Coverage section")
            continue
        try:
            proc = run(root, rel)
        except (OSError, subprocess.SubprocessError):
            notes.append(f"edge floor for {rel} not checked: engine failed closed")
            continue
        if proc.returncode == 1:
            problems.append(_drift_problem(rel, proc.stdout))
        elif proc.returncode != 0:
            notes.append(f"edge floor for {rel} not checked: engine failed closed")
    return problems, notes


_PHASE_DETAILS = re.compile(r"^## Phase Details$", re.MULTILINE)
_SECTION_HEAD = re.compile(r"^## ", re.MULTILINE)
_PHASE_HEAD = re.compile(r"^### Phase (\d+(?:\.\d+)*):", re.MULTILINE)
_JDG04 = re.compile(r"(?<![A-Za-z0-9-])JDG-04(?![A-Za-z0-9])")
_CRITERIA = "**Success Criteria**"
_PLANS = "**Plans**"
_JDG04_FLOOR = (32,)


def _phase_key(number: str) -> tuple[int, ...]:
    return tuple(int(part) for part in number.split("."))


def _phase_blocks(text: str) -> list[tuple[str, str]]:
    """(number, block) for each `### Phase N:` under `## Phase Details`, in roadmap order."""
    head = _PHASE_DETAILS.search(text)
    if head is None:
        return []
    rest = text[head.end():]
    next_section = _SECTION_HEAD.search(rest)
    section = rest if next_section is None else rest[:next_section.start()]
    heads = list(_PHASE_HEAD.finditer(section))
    blocks = []
    for index, phase in enumerate(heads):
        stop = heads[index + 1].start() if index + 1 < len(heads) else len(section)
        blocks.append((phase.group(1), section[phase.start():stop]))
    return blocks


def _criteria(block: str) -> str | None:
    """The success-criteria text of one phase block, or None when the marker is absent."""
    start = block.find(_CRITERIA)
    if start < 0:
        return None
    body = block[start + len(_CRITERIA):]
    stop = body.find(_PLANS)
    return body if stop < 0 else body[:stop]


def check_jdg04_citations(root: Path) -> tuple[list[str], list[str]]:
    """(problems, notes): every ROADMAP phase after 32 that names a SKILL.md cites JDG-04 in its
    success criteria (32 D-21). Backlog entries sit after `## Backlog` and are not scanned."""
    roadmap = root / ".planning" / "ROADMAP.md"
    if not roadmap.is_file():
        return [], ["JDG-04 citations not checked: no .planning/ROADMAP.md"]
    text = roadmap.read_text(encoding="utf-8", errors="replace")
    if _PHASE_DETAILS.search(text) is None:
        return [], ["JDG-04 citations not checked: no ## Phase Details section"]
    problems = []
    for number, block in _phase_blocks(text):
        if _phase_key(number) <= _JDG04_FLOOR or "SKILL.md" not in block:
            continue
        criteria = _criteria(block)
        if criteria is None or _JDG04.search(criteria) is None:
            problems.append(
                f"Phase {number} names a SKILL.md but no success criterion cites JDG-04")
    return problems, []


JUDGE_LOOP_REL = "tools/judge_loop.py"
JUDGE_RECORDS_REL = ".planning/judge"


@functools.cache
def _judge_loop():
    """tools/judge_loop.py, loaded by path from this checkout and registered as `judge_loop`."""
    spec = importlib.util.spec_from_file_location("judge_loop", REPO_ROOT / JUDGE_LOOP_REL)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {JUDGE_LOOP_REL}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["judge_loop"] = module
    spec.loader.exec_module(module)
    return module


def check_judge_records(root: Path,
                        load: Callable[[], Any] = _judge_loop) -> tuple[list[str], list[str]]:
    """(problems, notes): the judge records under .planning/judge reproduce REJUDGE.md (32 D-07);
    stale digests are notes."""
    records = root / JUDGE_RECORDS_REL
    if not records.is_dir():
        return [], ["judge records not checked: no .planning/judge"]
    judge_loop = load()
    try:
        _lines, problems, notes = judge_loop.check(root, records, judge_loop.CheckOptions())
    except judge_loop.JudgeLoopError as exc:
        return [f"judge records: {exc}"], []
    except (OSError, ValueError, KeyError, TypeError) as exc:
        # a record the checker did not expect must be a problem line, not a traceback
        return [f"judge records: {type(exc).__name__}: {exc}"], []
    return [f"judge records: {p}" for p in problems], [f"judge records: {n}" for n in notes]


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
    # Each check returns (problems, notes); the order here is the printed order.
    results = [check_runner_copy(root, args.template), check_flow_config(root),
               check_lens_wiring(root), check_edge_floors(root), check_jdg04_citations(root),
               check_judge_records(root)]
    if not args.skip_no_write:
        results.append(check_no_write(root))
    problems = [item for found, _notes in results for item in found]
    notes = [item for _problems, found in results for item in found]
    for line in [*notes, *problems]:
        print(f"{PREFIX} {line}")
    if problems:
        return 1
    print(f"{PREFIX} ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
