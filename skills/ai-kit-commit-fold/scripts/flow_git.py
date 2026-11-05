"""Git side of the unit flow (plan 29.1-01): remotes, start points and the one push choke point.

Every push argv is built by `push_argv` and sent only through `push` (or `delete_remote`), so a
lease, a target bound and a merged-branch bound cannot be skipped by a caller. The lease value
is always the recorded `pushed` sha, never a tip read from refs/remotes/ after a fetch.
"""

import os
import re
import subprocess

from flow_record import FlowError, consented

_SCRUBBED = ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE")
_GITHUB = re.compile(
    r"^(?:https://github\.com/|ssh://git@github\.com/|git@github\.com:)"
    r"([A-Za-z0-9._-]+)/([A-Za-z0-9._-]+?)(?:\.git)?/?$")


def _env():
    return {key: value for key, value in os.environ.items() if key not in _SCRUBBED}


def _run(repo, *args, check=True):
    proc = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, env=_env(),
                          check=False)
    if check and proc.returncode != 0:
        first = proc.stderr.decode("utf-8", "replace").strip().splitlines()
        raise FlowError("git_error", first[0] if first else " ".join(args))
    return proc


def run_git(repo, *args):
    """Run git with an argv list; its stdout as text. Raises git_error on failure."""
    return _run(repo, *args).stdout.decode("utf-8")


def _rev(repo, name):
    proc = _run(repo, "rev-parse", "--verify", "-q", name, check=False)
    return proc.stdout.decode("utf-8").strip() if proc.returncode == 0 else None


def rev(repo, name):
    """The sha a ref name resolves to, or None."""
    return _rev(repo, name)


def is_ancestor(repo, older, newer):
    return _run(repo, "merge-base", "--is-ancestor", older, newer, check=False).returncode == 0


def merge_base(repo, first, second):
    proc = _run(repo, "merge-base", first, second, check=False)
    return proc.stdout.decode("utf-8").strip() if proc.returncode == 0 else ""


def primary_remote(repo, settings):
    """The settings remote, which must be configured; no_remote when it is not."""
    name = settings["remote"]
    names = run_git(repo, "remote").split()
    if name not in names:
        raise FlowError("no_remote", f"no remote named {name}; the work stays local")
    return name


def github_repo(repo, remote):
    """OWNER/NAME of the remote's URL when its host is exactly github.com, else None."""
    proc = _run(repo, "config", "--get", f"remote.{remote}.url", check=False)
    url = proc.stdout.decode("utf-8").strip() if proc.returncode == 0 else ""
    match = _GITHUB.fullmatch(url)
    return f"{match.group(1)}/{match.group(2)}" if match else None


def is_github(repo, remote):
    return github_repo(repo, remote) is not None


def remote_tip(repo, remote, branch):
    """The remote-tracking sha of a branch; for reports and ancestry only, never a lease."""
    return _rev(repo, f"refs/remotes/{remote}/{branch}")


def merged_on_remote(repo, settings, entry):
    """True when the unit has its own commit and its tip is an ancestor of the remote target."""
    branch = entry["branch"]
    tip = _rev(repo, f"refs/heads/{branch}")
    if tip is None or tip == entry.get("parent_tip"):
        return False
    remote = settings["remote"]
    target_tip = _rev(repo, f"refs/remotes/{remote}/{entry['target']}")
    if target_tip is None:
        return False
    proc = _run(repo, "merge-base", "--is-ancestor", f"refs/heads/{branch}",
                f"refs/remotes/{remote}/{entry['target']}", check=False)
    return proc.returncode == 0


def push_argv(remote, refs):
    """The one push argv. refs: (branch, expected, src) triples.

    Each ref adds the refspec `<src or refs/heads/<branch>>:refs/heads/<branch>`; a non-None
    `expected` adds `--force-with-lease=refs/heads/<branch>:<expected>`. One ref with no
    `expected` is a first push (`-u`); more than one ref is atomic. Never `+`, `--force`, `-f`.
    """
    argv = ["git", "push"]
    if len(refs) > 1:
        argv.append("--atomic")
    if len(refs) == 1 and refs[0][1] is None:
        argv.append("-u")
    refspecs = []
    for branch, expected, src in refs:
        if expected is not None:
            argv.append(f"--force-with-lease=refs/heads/{branch}:{expected}")
        refspecs.append(f"{src or f'refs/heads/{branch}'}:refs/heads/{branch}")
    return [*argv, remote, *refspecs]


def push(repo, settings, record, refs):
    """Push refs through push_argv after every bound; updates the remote-tracking refs."""
    if not consented(repo):
        raise FlowError("no_consent", "no consent for this repository; nothing was pushed")
    remote = primary_remote(repo, settings)
    merged = {entry["branch"] for entry in record["units"] if entry["state"] == "merged"}
    for branch, expected, _src in refs:
        if expected is not None and branch in settings["targets"]:
            raise FlowError("target_branch_push", f"refusing to rewrite target {branch}")
        if branch in merged:
            raise FlowError("merged_branch_push", f"refusing to push merged unit {branch}")
    proc = subprocess.run(push_argv(remote, refs), cwd=str(repo), capture_output=True,
                          env=_env(), check=False)
    if proc.returncode != 0:
        text = proc.stderr.decode("utf-8", "replace")
        if "stale info" in text:
            raise FlowError("stale_lease", "the remote branch moved since the recorded push")
        first = text.strip().splitlines()
        raise FlowError("push_failed", first[-1] if first else "git push failed")
    for branch, _expected, src in refs:
        sha = src or _rev(repo, f"refs/heads/{branch}")
        _run(repo, "update-ref", f"refs/remotes/{remote}/{branch}", sha)


def delete_remote(repo, settings, record, branch):
    """Delete a merged unit's remote branch (plan 03 merge chain); bounds as in push."""
    if not consented(repo):
        raise FlowError("no_consent", "no consent for this repository; nothing was pushed")
    remote = primary_remote(repo, settings)
    if branch in settings["targets"]:
        raise FlowError("target_branch_push", f"refusing to delete target {branch}")
    merged = {entry["branch"] for entry in record["units"] if entry["state"] == "merged"}
    if branch not in merged:
        raise FlowError("merged_branch_push", f"{branch} is not a merged recorded unit")
    proc = _run(repo, "push", remote, "--delete", branch, check=False)
    if proc.returncode != 0:
        first = proc.stderr.decode("utf-8", "replace").strip().splitlines()
        raise FlowError("push_failed", first[-1] if first else "delete failed")


def start_point(repo, settings, record, target=None):
    """(parent branch, parent tip): the newest unmerged stacked unit, else the remote target."""
    for entry in reversed(record["units"]):
        if entry["kind"] == "stacked" and entry["state"] != "merged":
            return entry["branch"], _rev(repo, f"refs/heads/{entry['branch']}")
    target = target or settings["targets"][0]
    tip = remote_tip(repo, primary_remote(repo, settings), target)
    if tip is None:
        raise FlowError("no_trunk", f"no remote {target} ref to stack on")
    return target, tip
