"""Locates the installed gsd-core's gsd-tools.cjs and its lib modules, and queries them via
`node -e`: AGENT_DEFAULT_TIERS/AGENT_TO_PHASE_TYPE for the v1 flow, and for the v2 inventory
RUNTIME_PROFILE_MAP, MODEL_PROFILES (stored profile-first), AGENT_TO_PHASE_TYPE and
`isValidConfigKey` probes in one call.

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
from typing import NamedTuple

from . import model_detect

_THIS_SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SIBLING_MISSING = (
    "the ai-kit-spec-review sibling skill (ai_kit_spec) is not installed next to this skill"
)


def load_ai_kit_spec_module(name: str):
    """Returns the shared `ai_kit_spec.<name>` module, or `None` when the
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
        return importlib.import_module(f"ai_kit_spec.{name}")
    except ImportError:
        return None


def load_gsd_tools():
    return load_ai_kit_spec_module("gsd_tools")


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


def resolve_config_schema_cjs_path(gsd_tools_path, isfile_fn=os.path.isfile):
    """Returns `<dirname(gsd_tools_path)>/lib/config-schema.cjs` when that sibling exists,
    else `None`."""
    if not gsd_tools_path:
        return None
    candidate = os.path.join(os.path.dirname(gsd_tools_path), "lib", "config-schema.cjs")
    return candidate if isfile_fn(candidate) else None


class GsdCorePaths(NamedTuple):
    """Resolved node binary and the two gsd-core lib modules for one inventory query."""

    node_bin: str
    model_catalog: str
    config_schema: str


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


_GSD_TABLES_QUERY_SCRIPT = (
    "try { const m = require(process.argv[1]); const cs = require(process.argv[2]); "
    "if (typeof cs.isValidConfigKey !== 'function') throw new Error('missing'); "
    "const cwd = process.argv[3]; const keys = JSON.parse(process.argv[4]); "
    "const accepted = keys.filter((k) => cs.isValidConfigKey(k, cwd) === true); "
    "const rejected = keys.filter((k) => !accepted.includes(k)); "
    "process.stdout.write(JSON.stringify({runtime_profile_map: m.RUNTIME_PROFILE_MAP, "
    "model_profiles: m.MODEL_PROFILES, agent_to_phase_type: m.AGENT_TO_PHASE_TYPE, "
    "valid_keys: {accepted, rejected}})); } catch (e) { process.stdout.write('null'); }"
)


def profile_first(agent_first) -> dict:
    """gsd-core exports `MODEL_PROFILES` agent -> {profile: tier}; the inventory stores
    it profile -> {agent: tier}, the shape `roles` reads. Non-dict rows and non-str
    tiers are dropped."""
    out: dict[str, dict[str, str]] = {}
    for agent, per_profile in agent_first.items():
        if not isinstance(per_profile, dict):
            continue
        for profile, tier in per_profile.items():
            if isinstance(tier, str):
                out.setdefault(profile, {})[agent] = tier
    return out


def _parse_tables_output(stdout: str) -> dict | None:
    try:
        parsed = json.loads(stdout)
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, dict):
        return None
    rpm = parsed.get("runtime_profile_map")
    profiles = parsed.get("model_profiles")
    phase = parsed.get("agent_to_phase_type")
    valid_keys = parsed.get("valid_keys")
    if not isinstance(valid_keys, dict):
        valid_keys = {}
    accepted = valid_keys.get("accepted")
    rejected = valid_keys.get("rejected")
    by_profile = profile_first(profiles) if isinstance(profiles, dict) else {}
    tables_ok = isinstance(rpm, dict) and rpm and isinstance(phase, dict) and phase and by_profile
    if not tables_ok or not isinstance(accepted, list) or not isinstance(rejected, list):
        return None
    if not all(isinstance(k, str) for k in accepted + rejected):
        return None
    return {
        "runtime_profile_map": rpm,
        "model_profiles": by_profile,
        "agent_to_phase_type": phase,
        "valid_keys": {"accepted": sorted(accepted), "rejected": sorted(rejected)},
    }


class NodeQueryError(RuntimeError):
    """`node` itself failed (spawn error, timeout or non-zero exit). The query script
    catches its own errors and prints `null`, so this never means missing exports."""


_TABLES_TIMEOUT_S = 30


def query_gsd_tables(paths: GsdCorePaths, project_dir, keys, run_fn=subprocess.run, env=None):
    """One node call: gsd-core tables plus `isValidConfigKey` probes for `keys`. Returns
    `None` when the script reports `null` (require failed or exports missing) or prints
    malformed output; raises `NodeQueryError` when node itself fails. `env` (default:
    this process's) reaches node, so gsd-core sees the same GSD_HOME as the inventory."""
    try:
        result = run_fn(
            [
                paths.node_bin,
                "-e",
                _GSD_TABLES_QUERY_SCRIPT,
                paths.model_catalog,
                paths.config_schema,
                project_dir,
                json.dumps(keys),
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=_TABLES_TIMEOUT_S,
            env=env,
        )
    except OSError as exc:
        raise NodeQueryError(f"node failed to start ({exc.strerror or exc})") from exc
    except subprocess.TimeoutExpired as exc:
        raise NodeQueryError(f"node timed out after {_TABLES_TIMEOUT_S}s") from exc
    if result.returncode != 0:
        lines = (result.stderr or "").strip().splitlines()
        detail = f": {lines[-1]}" if lines else ""
        raise NodeQueryError(f"node exited {result.returncode}{detail}")
    return _parse_tables_output(result.stdout)
