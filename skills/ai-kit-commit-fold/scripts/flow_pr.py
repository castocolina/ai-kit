"""Plain-gh pull requests for the unit flow (plan 29.1-01): draft create and ready.

`run_gh` is the only gh runner. Every `gh pr` call goes through `pr_cmd`, which pins
`--repo OWNER/NAME` from the primary remote's URL. Every output reaching a report is redacted.
"""

import os
import re
import subprocess
import tempfile

from flow_git import github_repo, is_github, primary_remote
from flow_record import FlowError

_TOKEN = re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}")


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
    return (f"{unit.title}\n\n"
            f"Unit {unit.id}: {entry.get('checkpoints', 0)} checkpoint(s) folded.\n")


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
    fd, body_path = tempfile.mkstemp(prefix="pr-body-", suffix=".md")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(pr_body(unit, entry))
        code, text = pr_cmd(repo, settings, "create", "--base", base_of(record, unit),
                            "--head", unit.branch, "--draft", "--title", unit.title,
                            "--body-file", body_path)
    finally:
        os.unlink(body_path)
    if code != 0:
        raise FlowError("pr_failed", text.strip().splitlines()[0] if text.strip() else "gh pr")
    number = text.strip().rsplit("/", 1)[-1]
    return int(number) if number.isdigit() else None


def mark_ready(repo, settings, entry):
    code, text = pr_cmd(repo, settings, "ready", str(entry["pr"]))
    if code != 0:
        raise FlowError("pr_failed", text.strip().splitlines()[0] if text.strip() else "gh pr")
