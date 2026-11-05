"""Plan adapters for ai-kit-commit-fold: GSD and superpowers plans into schema-1 checkpoints.

The adapters read plan files and git history and build the checkpoint that fold_engine consumes.
They name the frameworks; the engine never does. Every refusal raised here is a FoldError with a
reason from fold_engine.REASONS.
"""

import dataclasses
import json
import os
import re
import subprocess
import unicodedata

from fold_engine import Candidate, Checkpoint, FoldError, range_commits

_SCRUBBED = ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE")
_MERGE_PREFIX = "chore: merge executor worktree ("
_TRAILER = "Ai-Kit-Fold: "
_GSD_DOCS = (".planning/",)
_SUBJECT_SCOPE = re.compile(r"^[a-z]+\(([^()]+)\)")
_PLAN_SCOPE = re.compile(r"(\d+(?:\.\d+)?)-(\d{2})")
_TASK = re.compile(r"<task\b[^>]*>(.*?)</task>", re.DOTALL)
_NAME = re.compile(r"<name>(.*?)</name>", re.DOTALL)
_FILES = re.compile(r"<files>(.*?)</files>", re.DOTALL)
_TASK_NUMBER = re.compile(r"^Task\s+\d+\s*:\s*")
_TRAILING_NOTE = re.compile(r"\s*\([^)]*\)\s*$")
_SP_HEAD = re.compile(r"^### Task (\d+): (.+)$")
_SP_SECTION = re.compile(r"^#{2,3} ")
_SP_FILE = re.compile(r"^- (?:Create|Modify|Test): `([^`]+)`")
_LINE_SUFFIX = re.compile(r":\d+(?:-\d+)?$")
_UNIT_CHARS = re.compile(r"[^A-Za-z0-9._-]")


@dataclasses.dataclass(frozen=True)
class _Run:
    """The phase branch's first-parent commits above the base branch, with each one's owner."""

    ref: str
    tip: str
    branch: str
    chain: tuple[str, ...]
    owners: tuple[str | None, ...]


def _proc(repo, *args):
    env = {key: value for key, value in os.environ.items() if key not in _SCRUBBED}
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, env=env,
                          check=False)


def _git(repo, *args):
    proc = _proc(repo, *args)
    if proc.returncode != 0:
        lines = proc.stderr.decode("utf-8", "replace").strip().splitlines()
        raise FoldError("git_error", lines[0] if lines else f"git {args[0]} failed")
    return proc.stdout.decode("utf-8", "replace")


def _rev(repo, spec):
    """The object id of `spec`, or None when it does not resolve."""
    proc = _proc(repo, "rev-parse", "--verify", "--quiet", spec)
    return proc.stdout.decode().strip() if proc.returncode == 0 else None


def _read(path):
    try:
        with open(path, encoding="utf-8") as handle:
            return handle.read()
    except OSError as exc:
        raise FoldError("bad_checkpoint", f"cannot read {os.path.basename(path)}") from exc


def padded_phase(phase):
    """Zero-pad the integer part of a phase number to two digits; a decimal suffix is kept."""
    whole, dot, decimal = phase.partition(".")
    return whole.zfill(2) + dot + decimal


def current_ref(repo):
    """The checked-out branch's full ref name, or HEAD when detached (never raises)."""
    proc = _proc(repo, "symbolic-ref", "-q", "HEAD")
    return proc.stdout.decode().strip() if proc.returncode == 0 else "HEAD"


def _current(repo):
    ref = current_ref(repo)
    if ref == "HEAD":
        raise FoldError("detached_head", "HEAD is not on a branch")
    tip = _rev(repo, ref)
    if tip is None:
        raise FoldError("git_error", f"{ref} does not resolve")
    return ref, tip


def _configured_branch(repo):
    try:
        with open(os.path.join(repo, ".planning", "config.json"), encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return None
    git = data.get("git") if isinstance(data, dict) else None
    value = git.get("base_branch") if isinstance(git, dict) else None
    return value if isinstance(value, str) and value else None


def base_branch(repo):
    """The base branch: git.base_branch in config, else origin's HEAD, else main, else master."""
    configured = _configured_branch(repo)
    if configured:
        return configured
    proc = _proc(repo, "symbolic-ref", "--short", "-q", "refs/remotes/origin/HEAD")
    name = proc.stdout.decode().strip().removeprefix("origin/") if proc.returncode == 0 else ""
    if name:
        return name
    for candidate in ("main", "master"):
        if _rev(repo, f"refs/heads/{candidate}"):
            return candidate
    return "main"


def phase_dir(repo, phase):
    """The one directory of the phase under .planning/phases/ (named `<padded>-<slug>`)."""
    padded = padded_phase(phase)
    root = os.path.join(repo, ".planning", "phases")
    try:
        names = os.listdir(root)
    except OSError:
        names = []
    found = [name for name in names
             if name.startswith(f"{padded}-") and os.path.isdir(os.path.join(root, name))]
    if len(found) != 1:
        raise FoldError("bad_checkpoint", f"phase dir not found for phase {phase}")
    return os.path.join(root, found[0])


def _files_of(body):
    match = _FILES.search(body)
    if not match:
        return ()
    files = []
    for item in match.group(1).split(","):
        path = _TRAILING_NOTE.sub("", item).strip().strip("`").strip()
        if path and path not in files:
            files.append(path)
    return tuple(files)


def parse_gsd_tasks(text):
    """Candidates from a GSD PLAN.md: each task element with a files element, in order."""
    candidates = []
    for match in _TASK.finditer(text):
        files = _files_of(match.group(1))
        if not files:
            continue
        name = _NAME.search(match.group(1))
        title = _TASK_NUMBER.sub("", name.group(1).strip()) if name else ""
        candidates.append(Candidate(f"t{len(candidates) + 1}", title.strip(), files))
    return tuple(candidates)


def parse_superpowers_tasks(text):
    """Candidates from a superpowers plan: each `### Task N:` section's Files bullets."""
    sections = []
    current, in_files = None, False
    for line in text.splitlines():
        head = _SP_HEAD.match(line)
        if head:
            current = (head.group(1), head.group(2).strip(), [])
            sections.append(current)
            in_files = False
        elif _SP_SECTION.match(line):
            current, in_files = None, False
        elif current is None:
            continue
        elif line.strip() == "**Files:**":
            in_files = True
        elif in_files and (bullet := _SP_FILE.match(line)):
            path = _LINE_SUFFIX.sub("", bullet.group(1))
            if path not in current[2]:
                current[2].append(path)
        elif in_files and line.strip() and not line.startswith("- "):
            in_files = False
    return tuple(Candidate(f"t{number}", title, tuple(files))
                 for number, title, files in sections if files)


def gsd_plans(repo, phase):
    """(unit, state) for each PLAN.md of the phase, in plan order; state is finished when a
    SUMMARY.md sits beside it."""
    padded = padded_phase(phase)
    directory = phase_dir(repo, phase)
    pattern = re.compile(rf"{re.escape(padded)}-(\d{{2}})-PLAN\.md")
    plans = []
    for name in os.listdir(directory):
        match = pattern.fullmatch(name)
        if match:
            unit = f"{padded}-{match.group(1)}"
            summary = os.path.join(directory, f"{unit}-SUMMARY.md")
            plans.append((unit, "finished" if os.path.isfile(summary) else "unfinished"))
    return sorted(plans)


def _plan_unit(scope, padded):
    match = _PLAN_SCOPE.fullmatch(scope)
    if not match:
        return None
    if padded_phase(match.group(1)) != padded:
        return "foreign"  # another phase's plan: never fold it into this one
    return f"{padded}-{match.group(2)}"


def _subject_unit(subject, padded):
    scope = _SUBJECT_SCOPE.match(subject)
    return _plan_unit(scope.group(1), padded) if scope else None


def _owner(repo, sha, padded):
    """The plan that owns a commit: `folded:<unit>` for a folded one, a plan unit, `foreign`
    for a merge-back whose commits name no single plan, or None."""
    header, _, message = _git(repo, "cat-file", "commit", sha).partition("\n\n")
    for line in message.splitlines():
        if line.startswith(_TRAILER):
            return f"folded:{line[len(_TRAILER):].strip()}"
    subject = message.split("\n", 1)[0]
    parents = [line for line in header.splitlines() if line.startswith("parent ")]
    if len(parents) < 2:
        return _subject_unit(subject, padded)
    if not subject.startswith(_MERGE_PREFIX):
        return None
    merged = _git(repo, "log", "--format=%s", f"{sha}^1..{sha}^2").splitlines()
    scopes = {_subject_unit(line, padded) for line in merged} - {None}
    return scopes.pop() if len(scopes) == 1 else "foreign"


def _view(repo, phase):
    """The phase branch's first-parent commits above the base branch, with owners."""
    ref, tip = _current(repo)
    branch = base_branch(repo)
    args = ["rev-list", "--reverse", "--first-parent", "--topo-order", tip]
    for name in (f"refs/heads/{branch}", f"refs/remotes/origin/{branch}"):
        resolved = _rev(repo, name)
        if resolved:
            args += ["--not", resolved]
    chain = tuple(_git(repo, *args).split())
    padded = padded_phase(phase)
    owners = tuple(_owner(repo, sha, padded) for sha in chain)
    return _Run(ref, tip, branch, chain, owners)


def gsd_checkpoint(repo, phase, unit):
    """The checkpoint for one GSD plan's unfolded commits, or None when it has none to fold.

    The plan's run runs from its first owned commit to its last; a commit of another plan (or a
    merge-back naming no single plan) inside that run refuses plan_not_contiguous.
    """
    run = _view(repo, phase)
    mine = {unit, f"folded:{unit}"}
    owned = [index for index, owner in enumerate(run.owners) if owner in mine]
    if not any(run.owners[index] == unit for index in owned):
        return None
    first, last = owned[0], owned[-1]
    if any(owner is not None and owner not in mine for owner in run.owners[first:last + 1]):
        raise FoldError("plan_not_contiguous", f"a commit of another plan sits inside {unit}")
    base = _git(repo, "rev-parse", f"{run.chain[first]}^1").strip()
    plan_text = _read(os.path.join(phase_dir(repo, phase), f"{unit}-PLAN.md"))
    return Checkpoint(
        unit=unit, ref=run.ref, base=base, end=run.chain[last], tip=run.tip,
        base_branch=run.branch, merged_refs=(), own_merge_subjects=(_MERGE_PREFIX,),
        candidates=parse_gsd_tasks(plan_text), docs_paths=_GSD_DOCS,
    )


def _status_line(repo, phase, unit, state, run):
    if state != "finished":
        return "unfinished"
    if unit not in run.owners:
        return "folded" if f"folded:{unit}" in run.owners else "no commits"
    checkpoint = gsd_checkpoint(repo, phase, unit)
    return f"unfolded ({len(range_commits(repo, checkpoint))} commits)"


def phase_status(repo, phase):
    """One line per plan of the phase: `<unit>: folded | unfolded (<n> commits) | unfinished |
    no commits`. Read-only."""
    run = _view(repo, phase)
    return [f"{unit}: {_status_line(repo, phase, unit, state, run)}"
            for unit, state in gsd_plans(repo, phase)]


def superpowers_unit(plan_file):
    """The unit id of a superpowers plan: its file stem, unsafe characters replaced, 64 max."""
    stem = os.path.splitext(os.path.basename(plan_file))[0]
    return _UNIT_CHARS.sub("-", stem)[:64]


def superpowers_checkpoint(repo, plan_file, base=None, base_branch_name=None):
    """The checkpoint for a superpowers plan branch: base is --base (resolved) or the merge-base
    of HEAD with the base branch; end and tip are the branch tip."""
    ref, tip = _current(repo)
    branch = base_branch_name or base_branch(repo)
    if base is None:
        resolved = _git(repo, "merge-base", "HEAD", branch).strip()
    else:
        resolved = _rev(repo, base)
        if resolved is None:
            raise FoldError("bad_checkpoint", "--base does not resolve")
    plan_text = _read(os.path.join(repo, plan_file))
    return Checkpoint(
        unit=superpowers_unit(plan_file), ref=ref, base=resolved, end=tip, tip=tip,
        base_branch=branch, merged_refs=(), own_merge_subjects=(),
        candidates=parse_superpowers_tasks(plan_text), docs_paths=(),
    )


_VERIFIED = re.compile(r"^status:\s*passed\s*$", re.MULTILINE)
_TITLE = re.compile(r"^#\s+(.+)$", re.MULTILINE)
_SLUG_BAD = re.compile(r"[^a-z0-9.-]+")
_GSD_BRANCH_DEFAULT = "gsd/phase-{phase}-{slug}"


def _config(repo):
    try:
        with open(os.path.join(repo, ".planning", "config.json"), encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def gsd_mvp(repo, phase):
    """Whether the phase runs in MVP mode, from gsd-tools when it is installed; else False."""
    tools = os.path.join(repo, ".claude", "gsd-core", "bin", "gsd-tools.cjs")
    if not os.path.isfile(tools):
        return False
    proc = subprocess.run(["node", tools, "phase", "mvp-mode", phase, "--raw"],
                          cwd=str(repo), capture_output=True, text=True, timeout=60,
                          check=False)
    try:
        return bool(json.loads(proc.stdout).get("active"))
    except (ValueError, AttributeError):
        return False


def gsd_signals(repo, phase):
    """(finished, verified): every plan of the phase has a SUMMARY; the phase VERIFICATION.md
    front matter reads status: passed."""
    plans = gsd_plans(repo, phase)
    finished = bool(plans) and all(state == "finished" for _unit, state in plans)
    directory = phase_dir(repo, phase)
    verified = False
    for name in os.listdir(directory):
        if name.endswith("-VERIFICATION.md"):
            text = _read(os.path.join(directory, name))
            verified = verified or bool(_VERIFIED.search(text.split("\n---", 1)[0]))
    return finished, verified


def gsd_unit(repo, phase):
    """The contract dict of one GSD phase (stacked, branch from git.phase_branch_template)."""
    padded = padded_phase(phase)
    directory = os.path.basename(phase_dir(repo, phase))
    slug = directory[len(padded) + 1:]
    template = (_config(repo).get("git") or {}).get("phase_branch_template")
    if not isinstance(template, str) or not template:
        template = _GSD_BRANCH_DEFAULT
    branch = template.format(phase=padded, slug=slug)
    return {"schema": 1, "id": f"phase-{padded}", "kind": "stacked", "branch": branch,
            "title": directory, "mvp": gsd_mvp(repo, phase)}


def superpowers_unit_contract(repo, plan_file):
    """The contract dict of a superpowers plan: branch plan/<slug> from the plan title."""
    text = _read(os.path.join(repo, plan_file))
    heading = _TITLE.search(text)
    title = heading.group(1).strip() if heading else superpowers_unit(plan_file)
    folded = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode("ascii")
    slug = _SLUG_BAD.sub("-", folded.lower()).strip("-")[:60] or "plan"
    return {"schema": 1, "id": superpowers_unit(plan_file), "kind": "stacked",
            "branch": f"plan/{slug}", "title": title}


def gsd_health(repo, run=subprocess.run):
    """(ok, summary) of `gsd-tools validate health --raw`; ok only when status is healthy.

    The exit code is ignored: validate health exits 0 even when degraded.
    """
    tools = os.path.join(repo, ".claude", "gsd-core", "bin", "gsd-tools.cjs")
    if not os.path.isfile(tools):
        return False, "health: no .claude/gsd-core/bin/gsd-tools.cjs under the repository"
    proc = run(["node", tools, "validate", "health", "--raw"], cwd=str(repo),
               capture_output=True, text=True, timeout=60, check=False)
    try:
        data = json.loads(proc.stdout)
    except (ValueError, TypeError):
        return False, "health: output is not JSON"
    if not isinstance(data, dict):
        return False, "health: output is not a JSON object"
    status = data.get("status")
    codes = [item.get("code", "") for item in data.get("warnings", []) if isinstance(item, dict)]
    codes += [item.get("code", "") for item in data.get("errors", []) if isinstance(item, dict)]
    summary = f"health: {status}" + (f" ({', '.join(codes)})" if codes else "")
    return status == "healthy", summary


def adapter_gates(repo):
    """The adapter gates for every flow command: the GSD health gate for a GSD project."""
    top = os.path.realpath(repo)
    if not os.path.isfile(os.path.join(top, ".planning", "config.json")):
        return []
    fold_py = os.path.join(os.path.dirname(os.path.realpath(__file__)), "fold.py")
    return [("gsd-tools validate health", ["python3", fold_py, "gsd-health", "--repo", top])]
