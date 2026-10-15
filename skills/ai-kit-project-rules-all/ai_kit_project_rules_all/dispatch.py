"""Subprocess fan-out to the 6 sibling `ai-kit-project-rules-*` checkers.

The only module in this skill that imports `subprocess`. `DOMAIN_ORDER` is
the single source of truth for both dispatch iteration order and
`aggregate.py`'s tie-break order -- `aggregate.py` imports it from here
rather than repeating the tuple.

D-04: `run_domain` always subprocess-invokes a sibling's `remediate`
subcommand, never a bare `check` -- every sibling's own `remediate` already
calls that sibling's own `check` internally before running the shared
`build_remediation()` builder, so `remediate`'s output is a strict superset
of what a bare `check` call would return.

D-06: `dispatch_all` calls the 6 siblings one at a time, in fixed
`DOMAIN_ORDER`, never in parallel.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys

DOMAIN_ORDER = ("agents", "makefile", "precommit", "arch", "docker", "cicd")

SKILL_NAMES = {
    "agents": "ai-kit-project-rules-agents",
    "makefile": "ai-kit-project-rules-makefile",
    "precommit": "ai-kit-project-rules-precommit",
    "arch": "ai-kit-project-rules-arch",
    "docker": "ai-kit-project-rules-docker",
    "cicd": "ai-kit-project-rules-cicd",
}

# D-06's per-domain budget. Read LIVE from this module's namespace inside
# `run_domain`'s body -- never bound as a function-default parameter value,
# whose default would be captured once at function-definition time and make
# a test's monkeypatch of this name silently no-op.
DOMAIN_TIMEOUT_SECONDS = 30


def resolve_entrypoint(skill_name: str) -> str | None:
    """Walk the host-neutral candidates every sibling `SKILL.md` already
    documents, returning the first candidate whose `<name>/<name>.py` file
    exists, or `None` if none do. The from-checkout sibling is tried first:
    an installed copy (`~/.claude/skills`, plugin root) may point at another
    branch, so the checkout's own sibling must win.
    """
    candidates: list[str] = []

    # From-checkout sibling, FIRST: walk up from this module's own real
    # path -- dispatch.py's directory -> package dir -> this skill's dir
    # (ai-kit-project-rules-all) -> skills root -> join <name>.
    pkg_dir = os.path.dirname(os.path.realpath(__file__))
    skill_dir = os.path.dirname(pkg_dir)
    skills_root = os.path.dirname(skill_dir)
    candidates.append(os.path.join(skills_root, skill_name))

    plugin_root = os.environ.get("CLAUDE_PLUGIN_ROOT")
    if plugin_root:
        # Mirrors bash's `${CLAUDE_PLUGIN_ROOT:+$CLAUDE_PLUGIN_ROOT/skills/<name>}`
        # pattern (verified `agents/SKILL.md:17`) -- an unset or empty var
        # skips this candidate entirely rather than joining an empty string
        # into a bogus `/skills/<name>` path.
        candidates.append(os.path.join(plugin_root, "skills", skill_name))

    home = os.path.expanduser("~")
    candidates.append(os.path.join(home, ".claude", "skills", skill_name))

    xdg_config_home = os.environ.get("XDG_CONFIG_HOME") or os.path.join(home, ".config")
    candidates.append(os.path.join(xdg_config_home, "opencode", "skills", skill_name))

    candidates.append(os.path.join(home, ".agents", "skills", skill_name))

    for candidate in candidates:
        entry = os.path.join(candidate, f"{skill_name}.py")
        if os.path.isfile(entry):
            return entry
    return None


def run_domain(domain: str, repo_root: str) -> dict:
    """Resolve `domain`'s entrypoint and subprocess-invoke its `remediate`
    subcommand (D-04), returning its parsed JSON payload.

    D-02: every failure mode -- an unresolvable entrypoint, a non-zero
    exit, a timeout past `DOMAIN_TIMEOUT_SECONDS`, or stdout that is not
    valid JSON -- degrades to D-05's failure-entry shape instead of
    raising, so one sibling's crash never aborts `dispatch_all`'s run of
    the other 5 domains.
    """
    skill_name = SKILL_NAMES[domain]
    entrypoint = resolve_entrypoint(skill_name)
    if entrypoint is None:
        return {
            "domain": domain,
            "status": "failed",
            "error": f"entrypoint not found for {skill_name!r}",
            "returncode": None,
        }

    try:
        result = subprocess.run(
            [sys.executable, entrypoint, "remediate", repo_root],
            capture_output=True,
            text=True,
            timeout=DOMAIN_TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return {
            "domain": domain,
            "status": "failed",
            "error": f"timed out after {DOMAIN_TIMEOUT_SECONDS}s",
            "returncode": None,
        }

    if result.returncode != 0:
        stderr_tail = result.stderr.strip().splitlines()[-1] if result.stderr.strip() else ""
        error = f"exited {result.returncode}"
        if stderr_tail:
            error += f": {stderr_tail}"
        return {
            "domain": domain,
            "status": "failed",
            "error": error,
            "returncode": result.returncode,
        }

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        return {
            "domain": domain,
            "status": "failed",
            "error": f"invalid JSON on stdout: {exc}",
            "returncode": result.returncode,
        }


def dispatch_all(repo_root: str) -> dict:
    """Call `run_domain` for every key in `DOMAIN_ORDER`, sequentially
    (D-06), returning `{domain: result}` for all 6.
    """
    return {domain: run_domain(domain, repo_root) for domain in DOMAIN_ORDER}
