"""Locates the installed gsd-core's gsd-tools.cjs and lib/model-catalog.cjs, and queries the
live AGENT_DEFAULT_TIERS/AGENT_TO_PHASE_TYPE export via a `node -e` subprocess call.

The gsd-tools path resolution itself is delegated to the one shared resolver in
`ai_kit_spec.gsd_tools` (D-18, 16.1-CONTEXT.md), which searches the PROJECT-LOCAL gsd-core
installs first (in GSD's own launcher order) before any per-host global one, and returns
`None` when this skill's ai-kit-spec-review sibling is not importable.
"""
import importlib
import json
import os
import shutil
import subprocess
import sys

from . import model_detect

_THIS_SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_gsd_tools():
    """Returns the shared `ai_kit_spec.gsd_tools` module, or `None` when the
    ai-kit-spec-review sibling skill cannot be located/imported (importlib keeps pyright
    clean with no ignore comment; the caller reports the miss, never raising at import
    time)."""
    shim = model_detect.resolve_ai_kit_spec_path(_THIS_SKILL_DIR)
    if shim is None:
        return None
    skill_dir = os.path.dirname(shim)
    if skill_dir not in sys.path:
        sys.path.insert(0, skill_dir)
    try:
        return importlib.import_module("ai_kit_spec.gsd_tools")
    except ImportError:
        return None


def resolve_gsd_tools_path(env: dict | None = None, isfile_fn=os.path.isfile, start=None):
    """Delegates to `ai_kit_spec.gsd_tools.resolve_gsd_tools` (project-local gsd-core
    first, D-18); returns `None` when the shared module is unavailable or nothing is found.
    Never raises, never prints -- the caller decides how to report a miss."""
    gsd_tools = load_gsd_tools()
    if gsd_tools is None:
        return None
    return gsd_tools.resolve_gsd_tools(env=env, start=start, isfile_fn=isfile_fn)


def resolve_model_catalog_cjs_path(gsd_tools_path, isfile_fn=os.path.isfile):
    """Returns `<dirname(gsd_tools_path)>/lib/model-catalog.cjs` when that sibling file
    exists, else `None`. Never resolves `model-catalog.json` directly -- the `.cjs` module
    itself resolves that relative to its own `__dirname`, so this skill only ever needs the
    module path."""
    if not gsd_tools_path:
        return None
    candidate = os.path.join(os.path.dirname(gsd_tools_path), "lib", "model-catalog.cjs")
    return candidate if isfile_fn(candidate) else None


def resolve_node_binary(which_fn=shutil.which):
    """Every `node -e` call in this skill resolves `node` through this one function so a
    test can inject a fake resolver."""
    return which_fn("node")


# A single-line Node expression that requires `process.argv[1]` (the model-catalog.cjs path,
# passed as a real argv element -- never string-interpolated into the script body, avoiding
# any quoting hazard from a path containing a space or quote character) and writes
# `JSON.stringify({tiers: ..., phaseTypes: ...})` to stdout. If `require()` throws (a future
# gsd-core version without these exports), the script instead writes the literal string
# `null` to stdout and exits 0 -- this makes "exports missing" and "require failed" both
# collapse to the SAME detectable signal (`stdout == "null"`) rather than needing the caller
# to parse a Node stack trace.
_AGENT_CATALOG_QUERY_SCRIPT = (
    "try { const m = require(process.argv[1]); "
    "process.stdout.write(JSON.stringify({tiers: m.AGENT_DEFAULT_TIERS, "
    "phaseTypes: m.AGENT_TO_PHASE_TYPE})); } "
    "catch (e) { process.stdout.write('null'); }"
)


def _parse_catalog_output(stdout: str) -> dict | None:
    try:
        parsed = json.loads(stdout)
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, dict):
        return None
    tiers = parsed.get("tiers")
    phase_types = parsed.get("phaseTypes")
    if not isinstance(tiers, dict) or not tiers:
        return None
    if not isinstance(phase_types, dict) or not phase_types:
        return None
    return {"tiers": tiers, "phaseTypes": phase_types}


def query_agent_catalog(node_bin, model_catalog_path, run_fn=subprocess.run):
    """Returns the parsed `{"tiers": {...}, "phaseTypes": {...}}` dict on a clean `node -e`
    run (exit 0, valid JSON, both keys present and non-empty dicts); returns `None` on ANY
    of: non-zero exit, timeout, unparseable stdout, a parsed result missing either key, or
    either key not being a non-empty dict. Never returns a partial/malformed result for the
    caller to guess about."""
    try:
        result = run_fn(
            [node_bin, "-e", _AGENT_CATALOG_QUERY_SCRIPT, model_catalog_path],
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
    except subprocess.TimeoutExpired:
        return None
    if result.returncode != 0:
        return None
    return _parse_catalog_output(result.stdout)
