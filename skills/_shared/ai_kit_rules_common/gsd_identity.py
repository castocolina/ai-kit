"""OpenGSD identity probe for the rules-checker family (26 D-17, D-18 as amended, D-19).

Answers one question: does this project's gsd-core identify itself as `@opengsd/gsd-core`?
The answer is `ok` only for that exact `packageName`; every other shape is `absent` (valid
identity naming another package) or `unverified` (no way to prove it: no gsd-tools, no node,
a non-zero exit, a timeout, invalid JSON, or no string `packageName`).

The probe reuses the one shared gsd-tools resolver (`ai_kit_spec.gsd_tools`) and the one node
lookup (`ai_kit_gsd_curated_config.gsd_catalog`), both reached through the sibling skills; this
module holds no second resolver, node lookup or run wrapper. The sibling skills are imported
lazily so importing this module never fails.
"""

from __future__ import annotations

import functools
import importlib
import json
import os
import shutil
import subprocess
import sys

OPENGSD_PACKAGE = "@opengsd/gsd-core"
PROBE_TIMEOUT_SECONDS = 5
_PROBE_ENV_KEYS = ("PATH", "HOME")
_SIBLING_MISSING = (
    "the ai-kit-gsd-curated-config or ai-kit-spec-review sibling skill is not installed"
)

# skills/_shared/ai_kit_rules_common/gsd_identity.py -> skills/
_SKILLS_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
)


def _load_gsd_catalog():
    """`ai_kit_gsd_curated_config.gsd_catalog`, or `None` when the sibling is unavailable."""
    sibling = os.path.join(_SKILLS_ROOT, "ai-kit-gsd-curated-config")
    if sibling not in sys.path:
        sys.path.insert(0, sibling)
    try:
        return importlib.import_module("ai_kit_gsd_curated_config.gsd_catalog")
    except ImportError:
        return None


def _classify_identity(stdout: str) -> tuple[str, str]:
    """(status, reason) for the stdout of a `runtime-identity --raw` call that exited 0."""
    try:
        data = json.loads(stdout)
    except ValueError:
        return "unverified", "runtime-identity printed invalid JSON"
    if not isinstance(data, dict) or not isinstance(data.get("packageName"), str):
        return "unverified", "runtime-identity JSON has no string packageName"
    name = data["packageName"]
    if name == OPENGSD_PACKAGE:
        return "ok", f"runtime-identity names {OPENGSD_PACKAGE}"
    return "absent", f"identity names {name[:80]!r}, not {OPENGSD_PACKAGE}"


def probe(
    env,
    search_path,
    run_fn=subprocess.run,
    which_fn=shutil.which,
    timeout=PROBE_TIMEOUT_SECONDS,
) -> tuple[str, str, str | None]:
    """Return `(status, reason, gsd_tools_path)` for the project rooted at `search_path`.

    `status` is `ok`, `absent` or `unverified`; `gsd_tools_path` is the gsd-tools file the
    resolver located (`None` when none was found), whether or not the identity command then ran.
    The identity command gets an env of only PATH and HOME, so a caller's other variables never
    reach it.
    """
    gsd_catalog = _load_gsd_catalog()
    gsd_tools = gsd_catalog.load_gsd_tools() if gsd_catalog is not None else None
    if gsd_tools is None:
        return "unverified", _SIBLING_MISSING, None

    tools_path = gsd_tools.resolve_gsd_tools(
        env=env, start=search_path, run_fn=run_fn, which_fn=which_fn
    )
    if tools_path is None:
        return "unverified", "no gsd-tools.cjs in the launcher order", None

    path_env = env.get("PATH", "")
    node_bin = (
        gsd_catalog.resolve_node_binary(which_fn=functools.partial(which_fn, path=path_env))
        if path_env and gsd_catalog is not None
        else None
    )
    if node_bin is None:
        return "unverified", "node not on PATH", tools_path

    status, reason = _run_identity(
        gsd_tools.GsdTools(node_bin, tools_path), env, run_fn, timeout
    )
    return status, reason, tools_path


def _run_identity(tools, env, run_fn, timeout) -> tuple[str, str]:
    """Run `runtime-identity --raw` with only PATH and HOME from `env`, classify the result."""
    probe_env = {key: env[key] for key in _PROBE_ENV_KEYS if key in env}
    try:
        result = run_fn(
            [tools.node_bin, tools.gsd_tools_path, "runtime-identity", "--raw"],
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
            env=probe_env,
        )
    except subprocess.TimeoutExpired:
        return "unverified", f"runtime-identity timed out after {timeout}s"
    except (OSError, subprocess.SubprocessError) as exc:
        return "unverified", f"runtime-identity could not run: {exc}"
    if result.returncode != 0:
        return (
            "unverified",
            f"runtime-identity failed (exit {result.returncode}); "
            "an original GSD without the verb looks the same",
        )
    return _classify_identity(result.stdout or "")


__all__ = ["OPENGSD_PACKAGE", "PROBE_TIMEOUT_SECONDS", "probe"]
