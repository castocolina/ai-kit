"""Plain-gh pull requests for the unit flow (plan 29.1-01): draft create and ready.

`run_gh` is the only gh runner. Every `gh pr` call goes through `pr_cmd`, which pins
`--repo OWNER/NAME` from the primary remote's URL. Every output reaching a report is redacted.
"""

import contextlib
import os
import re
import subprocess
import tempfile

from flow_git import github_repo, is_github, primary_remote
from flow_record import FlowError, Unit

_TOKEN = re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}")
_BACKEND_ENV = "AI_KIT_FLOW_PR_BACKEND"


def redact(text):
    return _TOKEN.sub("[redacted]", text)


def run_gh(repo, *args):
    """(exit code, redacted stdout+stderr) of `gh <args>` run in `repo`."""
    try:
        proc = subprocess.run(["gh", *args], cwd=str(repo), capture_output=True, check=False)
    except FileNotFoundError:
        return 127, "gh not found"
    text = (proc.stdout + proc.stderr).decode("utf-8", "replace")
    return proc.returncode, redact(text)


def pr_body(unit, entry):
    """Only the unit's title, goal, branch and checkpoint count (T-29.1-08: no other content)."""
    return (f"{unit.title}\n\n"
            f"Goal: {entry.get('goal') or 'not stated'}\n\n"
            f"Branch: {unit.branch}\n"
            f"checkpoints: {entry.get('checkpoints', 0)}\n")


@contextlib.contextmanager
def _body_file(text):
    """A temp file holding the PR body, removed when the block exits."""
    fd, path = tempfile.mkstemp(prefix="pr-body-", suffix=".md")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
        yield path
    finally:
        os.unlink(path)


def base_of(record, unit):
    """The one base rule: the parent unit's branch while that parent is unmerged in the record,
    else the unit's target."""
    entry = next(item for item in record["units"] if item["id"] == unit.id)
    parent = entry["parent"]
    for other in record["units"]:
        if other["branch"] == parent and other["state"] != "merged":
            return parent
    return unit.target


def pr_cmd(repo, settings, *args):
    """`gh pr <args> --repo OWNER/NAME` for the primary remote's repository."""
    slug = github_repo(repo, primary_remote(repo, settings))
    if slug is None:
        return 1, "no GitHub repository on the primary remote"
    return run_gh(repo, "pr", *args, "--repo", slug)


def open_draft(repo, settings, unit, entry, record):
    """Open a draft PR for the unit's branch when the primary remote is GitHub; its number."""
    if not is_github(repo, primary_remote(repo, settings)):
        return None
    with _body_file(pr_body(unit, entry)) as body_path:
        code, text = pr_cmd(repo, settings, "create", "--base", base_of(record, unit),
                            "--head", unit.branch, "--draft", "--title", unit.title,
                            "--body-file", body_path)
    if code != 0:
        raise FlowError("pr_failed", text.strip().splitlines()[0] if text.strip() else "gh pr")
    number = text.strip().rsplit("/", 1)[-1]
    return int(number) if number.isdigit() else None


def update_pr(repo, settings, unit, entry):
    """Edit the open PR's title and body so they follow the unit after a pushed checkpoint."""
    with _body_file(pr_body(unit, entry)) as body_path:
        code, text = pr_cmd(repo, settings, "edit", str(entry["pr"]), "--title", unit.title,
                            "--body-file", body_path)
    if code != 0:
        raise FlowError("pr_failed", text.strip().splitlines()[0] if text.strip() else "gh pr")


def backend(repo):
    """`none` (gh missing), `signed_out` (gh auth status fails), `gh-stack` or `gh`.

    gh-stack when `gh stack --help` exits 0. AI_KIT_FLOW_PR_BACKEND=gh forces the plain path;
    AI_KIT_FLOW_PR_BACKEND=gh-stack forces the stack path without the probe (test seam; the
    fake gh has no `stack --help`).
    """
    code, _text = run_gh(repo, "auth", "status")
    if code == 127:
        return "none"
    if code != 0:
        return "signed_out"
    forced = os.environ.get(_BACKEND_ENV)
    if forced in ("gh", "gh-stack"):
        return forced
    code, _text = run_gh(repo, "stack", "--help")
    return "gh-stack" if code == 0 else "gh"


def _first_line(text):
    lines = text.strip().splitlines()
    return lines[0] if lines else "gh failed"


def _unit_of_entry(entry):
    return Unit(id=entry["id"], kind=entry["kind"], target=entry["target"],
                branch=entry["branch"], title=entry["title"])


def _stack_adopt(repo, settings, record):
    """gh-stack adoption (D-04): `stack init` of the recorded unmerged stacked units with PRs,
    then `stack link` with their PR URLs, bottom to top. Never `submit` or `push` (review HIGH 6:
    the guarded flow_git.push is the only push). Returns None, or the failing call's first line.
    """
    units = [e for e in record["units"] if e["kind"] == "stacked" and e["state"] != "merged"
             and e["pr"] is not None]
    if not units:
        return None
    trunk = units[0]["target"]
    code, text = run_gh(repo, "stack", "init", "--base", trunk, *[e["branch"] for e in units])
    if code != 0:
        return _first_line(text)
    slug = github_repo(repo, primary_remote(repo, settings))
    urls = [f"https://github.com/{slug}/pull/{e['pr']}" for e in units]
    code, text = run_gh(repo, "stack", "link", "--base", trunk, *urls)
    return None if code == 0 else _first_line(text)


def _plain_bases(repo, settings, record):
    """The plain-gh fallback: set every unmerged stacked unit's PR base to the one base rule."""
    for entry in record["units"]:
        if entry["kind"] != "stacked" or entry["state"] == "merged" or entry["pr"] is None:
            continue
        base = base_of(record, _unit_of_entry(entry))
        code, text = pr_cmd(repo, settings, "edit", str(entry["pr"]), "--base", base)
        if code != 0:
            raise FlowError("pr_failed", _first_line(text))


def ensure_pr(repo, settings, record, unit, entry):
    """Open the unit's draft PR after a pushed checkpoint. Returns (number or None, report lines).

    Without a GitHub primary remote, or with gh missing or signed out, nothing is opened and the
    report says why; the push has already happened. The base of each PR is `base_of`.
    """
    if not is_github(repo, primary_remote(repo, settings)):
        return None, ["no PR opened: PRs not supported on this remote"]
    kind = backend(repo)
    if kind == "none":
        return None, ["no PR opened: gh not found"]
    if kind == "signed_out":
        return None, ["no PR opened: gh not signed in"]
    number = open_draft(repo, settings, unit, entry, record)
    entry["pr"] = number
    if kind == "gh-stack":
        reason = _stack_adopt(repo, settings, record)
        if reason is None:
            return number, [f"draft PR {number} (pr backend: gh-stack)"]
        _plain_bases(repo, settings, record)
        return number, [f"draft PR {number} (pr backend: gh (gh-stack failed: {reason}))"]
    return number, [f"draft PR {number} (pr backend: gh)"]


def mark_ready(repo, settings, entry):
    code, text = pr_cmd(repo, settings, "ready", str(entry["pr"]))
    if code != 0:
        raise FlowError("pr_failed", text.strip().splitlines()[0] if text.strip() else "gh pr")
