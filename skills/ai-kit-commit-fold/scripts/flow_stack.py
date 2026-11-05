"""Stack reconciliation for the unit flow (plan 29.1-01): sync and the cascade handoff.

`sync` runs first in every flow command except consent, settings and show. With consent it
fetches; it records externally merged units as merged; and it refuses trunk_moved when the
remote trunk carries non-merge commits that the bottom unmerged unit does not hold.
`cascade` is the handoff for a lower unit that was refolded under units stacked above it;
plan 03 replaces its body and keeps its signature.
"""

import subprocess

from flow_git import merged_on_remote, primary_remote, run_git
from flow_record import FlowError, consented, write_record


def sync(repo, settings, record):
    """Fetch with consent, reconcile merges, and return the trunk_moved reason or None."""
    remote = primary_remote(repo, settings)
    if consented(repo):
        run_git(repo, "fetch", "--prune", "-q", remote)
    changed = False
    for entry in record["units"]:
        if entry["state"] != "merged" and merged_on_remote(repo, settings, entry):
            entry["state"] = "merged"
            changed = True
    if changed:
        write_record(repo, record)
    bottom = next((entry for entry in record["units"]
                   if entry["kind"] == "stacked" and entry["state"] != "merged"), None)
    if bottom is None:
        return None
    target = bottom["target"]
    proc = subprocess.run(
        ["git", "-C", str(repo), "rev-list", "--no-merges", "--count",
         f"refs/remotes/{remote}/{target}", f"^refs/heads/{bottom['branch']}"],
        capture_output=True, check=False)
    if proc.returncode != 0:
        return None
    count = proc.stdout.decode("utf-8").strip()
    return "trunk_moved" if count not in ("", "0") else None


def cascade(repo, settings, record, moved_unit=None, old_tip=None):
    """Restack the units above a refolded lower unit; plan 03 fills this body.

    Returns the list of restacked unit ids. Plan 01 only refuses, naming the command to run.
    """
    del repo, settings, record, moved_unit, old_tip
    raise FlowError("restack_needed", "fold.py restack")
