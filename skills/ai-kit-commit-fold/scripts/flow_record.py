"""Unit contract, stack record, settings and consent for the unit flow (plan 29.1-01).

The unit contract (`--unit` JSON) is neutral: no adapter names appear here. The stack record is
`<git common dir>/ai-kit-stack.json`, one per repository and never committed. Settings and
consent are `.aikit/flow.json` in the main worktree, never committed. Every write is atomic
(mkstemp in the target directory, then os.replace).
"""

import dataclasses
import datetime
import json
import os
import re
import shlex
import subprocess
import tempfile
from pathlib import Path

CONTRACT_REQUIRED = ("schema", "id", "kind", "branch", "title")
CONTRACT_OPTIONAL = ("target", "goal", "mvp")
KINDS = ("stacked", "hotfix")
_ID = re.compile(r"[A-Za-z0-9._-]{1,64}")
_SCRUBBED = ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE")
RECORD_NAME = "ai-kit-stack.json"
SETTINGS_REL = Path(".aikit") / "flow.json"


class FlowError(Exception):
    """A refusal: `reason` is one reason code and `detail` is one short line."""

    def __init__(self, reason, detail=""):
        super().__init__(f"{reason}: {detail}")
        self.reason = reason
        self.detail = detail


@dataclasses.dataclass(frozen=True)
class Unit:  # pylint: disable=too-many-instance-attributes  # one field per contract key
    id: str
    kind: str
    target: str
    branch: str
    title: str
    goal: str = ""
    mvp: bool = False


def _git(repo, *args, check=True):
    env = {key: value for key, value in os.environ.items() if key not in _SCRUBBED}
    proc = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, env=env,
                          check=False)
    if check and proc.returncode != 0:
        first = proc.stderr.decode("utf-8", "replace").strip().splitlines()
        raise FlowError("git_error", first[0] if first else " ".join(args))
    return proc


def _check_branch(branch):
    proc = subprocess.run(["git", "check-ref-format", "--branch", branch], capture_output=True,
                          check=False)
    if proc.returncode != 0 or not branch:
        raise FlowError("bad_value", f"branch {branch!r} is not a valid git branch name")


def load_unit(data, default_target):
    """Validate a unit contract dict and return a Unit; refusals name the field."""
    if not isinstance(data, dict):
        raise FlowError("bad_value", "unit contract must be a JSON object")
    unknown = sorted(set(data) - set(CONTRACT_REQUIRED) - set(CONTRACT_OPTIONAL))
    if unknown:
        raise FlowError("unknown_field", ", ".join(unknown))
    missing = [key for key in CONTRACT_REQUIRED if key not in data]
    if missing:
        raise FlowError("missing_field", ", ".join(missing))
    if data["schema"] != 1:
        raise FlowError("bad_value", "schema must be 1")
    if not isinstance(data["id"], str) or not _ID.fullmatch(data["id"]):
        raise FlowError("bad_value", "id must match [A-Za-z0-9._-]{1,64}")
    if data["kind"] not in KINDS:
        raise FlowError("bad_value", "kind must be stacked or hotfix")
    if not isinstance(data["title"], str) or not data["title"]:
        raise FlowError("bad_value", "title must be a non-empty string")
    branch = data["branch"]
    if not isinstance(branch, str):
        raise FlowError("bad_value", "branch must be a string")
    _check_branch(branch)
    target = data.get("target", default_target)
    if not isinstance(target, str) or not target:
        raise FlowError("bad_value", "target must be a non-empty string")
    _check_branch(target)
    mvp = data.get("mvp", False)
    if not isinstance(mvp, bool):
        raise FlowError("bad_value", "mvp must be true or false")
    goal = data.get("goal", "")
    if not isinstance(goal, str):
        raise FlowError("bad_value", "goal must be a string")
    return Unit(id=data["id"], kind=data["kind"], target=target, branch=branch,
                title=data["title"], goal=goal, mvp=mvp)


def common_dir(repo):
    """The git common directory (shared by every worktree), absolute."""
    out = _git(repo, "rev-parse", "--path-format=absolute", "--git-common-dir").stdout
    return Path(out.decode("utf-8").strip())


def main_worktree(repo):
    """The main worktree: the parent of the git common directory."""
    return common_dir(repo).parent


def _atomic_write_json(path, data):
    # copied from tools/setup.py _atomic_write_json; skills stay self-contained
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=1, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
    except BaseException:
        if os.path.exists(temp):
            os.unlink(temp)
        raise


def _read_json(path):
    """The parsed object at `path`, or None when missing, empty, unreadable or not an object."""
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def record_path(repo):
    return common_dir(repo) / RECORD_NAME


def read_record(repo):
    """The stack record; a missing record is an empty stack."""
    data = _read_json(record_path(repo))
    if data is None:
        return {"schema": 1, "units": []}
    units = data.get("units")
    if not isinstance(units, list):
        raise FlowError("bad_value", "stack record has no unit list")
    return data


def write_record(repo, data):
    _atomic_write_json(record_path(repo), data)


def find_entry(record, unit_id):
    for entry in record["units"]:
        if entry["id"] == unit_id:
            return entry
    return None


def _default_targets(repo):
    proc = _git(repo, "symbolic-ref", "--short", "-q", "refs/remotes/origin/HEAD", check=False)
    name = proc.stdout.decode("utf-8").strip().removeprefix("origin/")
    return [name or "main"]


def _settings_path(repo):
    return main_worktree(repo) / SETTINGS_REL


def read_settings(repo):
    """The settings with defaults filled in. Missing, empty, unreadable or non-JSON means
    defaults with consent false."""
    defaults = {"schema": 1, "repo": None, "consent": False, "granted": None,
                "remote": "origin", "targets": _default_targets(repo), "gates": [],
                "stack_backend": "plain"}
    data = _read_json(_settings_path(repo))
    if data is None:
        return defaults
    merged = dict(defaults)
    merged.update({key: value for key, value in data.items() if key in defaults})
    return merged


def write_settings(repo, data):
    _atomic_write_json(_settings_path(repo), data)


def _ignored(repo):
    proc = subprocess.run(["git", "-C", str(main_worktree(repo)), "check-ignore", "-q",
                           str(SETTINGS_REL)], capture_output=True, check=False)
    return proc.returncode == 0


def _ensure_ignored(repo, add_exclude):
    if _ignored(repo):
        return
    if not add_exclude:
        raise FlowError("settings_not_ignored", f"{SETTINGS_REL} is not ignored by git")
    exclude = common_dir(repo) / "info" / "exclude"
    exclude.parent.mkdir(parents=True, exist_ok=True)
    with open(exclude, "a", encoding="utf-8") as handle:
        handle.write(f"\n{SETTINGS_REL.parent.as_posix()}/\n")
    if not _ignored(repo):
        raise FlowError("settings_not_ignored", f"{SETTINGS_REL} is still not ignored")


def consented(repo):
    """True only when consent is true and the record was written for this repository."""
    data = _read_json(_settings_path(repo))
    if data is None or data.get("consent") is not True:
        return False
    return data.get("repo") == str(os.path.realpath(common_dir(repo)))


def render(command, unit_id, branch, lines, outcome):
    """The report: first line `flow <command> <unit>: <branch>`, last `outcome: ...`."""
    head = f"flow {command} {unit_id}: {branch}"
    return "\n".join([head, *lines, f"outcome: {unit_id} {outcome}"])


def cmd_consent(args):
    """grant | revoke | status. Status prints `consent: yes` or `consent: no` only."""
    repo = args.repo
    if args.action == "status":
        print("consent: yes" if consented(repo) else "consent: no")
        return 0
    try:
        if args.action == "grant":
            _ensure_ignored(repo, args.add_exclude)
    except FlowError as exc:
        print(render("consent", "repository", "-", [f"refused: {exc.reason}"],
                     f"refused {exc.reason}"))
        return 1
    if args.action == "revoke" and not consented(repo):
        # T-29.1-05: never create an unchecked settings file just to say no
        print(render("consent", "repository", "-", [], "consent revoked"))
        return 0
    settings = read_settings(repo)
    settings["repo"] = str(os.path.realpath(common_dir(repo)))
    if args.action == "grant":
        settings["consent"] = True
        settings["granted"] = datetime.date.today().isoformat()
        outcome = "consent granted"
    else:
        settings["consent"] = False
        outcome = "consent revoked"
    write_settings(repo, settings)
    print(render("consent", "repository", "-", [], outcome))
    return 0


def cmd_settings(args):
    """show prints remote, targets and gates; set updates only the keys given."""
    repo = args.repo
    settings = read_settings(repo)
    if args.action == "show":
        print(f"remote: {settings['remote']}")
        print(f"targets: {', '.join(settings['targets'])}")
        print(f"gates: {'; '.join(shlex.join(gate) for gate in settings['gates']) or 'none'}")
        return 0
    try:
        _ensure_ignored(repo, False)
    except FlowError as exc:
        print(render("settings", "repository", "-", [f"refused: {exc.reason}"],
                     f"refused {exc.reason}"))
        return 1
    if args.remote:
        settings["remote"] = args.remote
    if args.target:
        for branch in args.target:
            _check_branch(branch)
        settings["targets"] = list(args.target)
    if args.gate is not None:
        settings["gates"] = [shlex.split(text) for text in args.gate]
    settings["repo"] = str(os.path.realpath(common_dir(repo)))
    write_settings(repo, settings)
    print(render("settings", "repository", "-", [], "settings saved"))
    return 0
