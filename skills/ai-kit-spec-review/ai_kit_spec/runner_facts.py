"""37 D-10 / SPEC R9: the runner's own --describe, recorded in the runtimes snapshot.

Python reads this fact instead of mirroring the runner's tables. An absent, unreadable or stale
fact never refuses a lane; the runner refuses at run time with its own named reason. Only stdlib,
the cache helpers and the template path resolver are used.
"""
import hashlib
import json
import subprocess

from ai_kit_spec.cache import cache_read_json
from ai_kit_spec.detection import bounded_run, cache_runtimes_path, run_in_own_group
from ai_kit_spec.tooling_guidance import resolve_cross_ai_template_path

DESCRIBE_TIMEOUT_S = 30
FACT_SOURCE = "cross-ai.mjs --describe, recorded in the runtimes snapshot"


def template_sha256(path) -> str | None:
    """Hash the template bytes, or return None when unavailable."""
    if not path:
        return None
    try:
        with open(path, "rb") as stream:
            return hashlib.sha256(stream.read()).hexdigest()
    except OSError:
        return None


def read_runner_describe(node, template_path, run_fn=run_in_own_group) -> dict:
    """Read the runner's description without trusting failed or malformed output."""
    run_fn = bounded_run(run_fn)
    describe = None
    if node and template_path:
        try:
            proc = run_fn([node, template_path, "--describe"], stdin=subprocess.DEVNULL,
                          capture_output=True, text=True, timeout=DESCRIBE_TIMEOUT_S, check=False)
            if proc.returncode == 0:
                result = json.loads(proc.stdout)
                if isinstance(result, dict) and isinstance(result.get("runtimes"), dict):
                    describe = result
        except (OSError, subprocess.SubprocessError, ValueError):
            pass
    return {"template_sha256": template_sha256(template_path), "describe": describe}


def fact_is_current(fact, template_path) -> bool:
    """A successful fact is current only for the readable template it describes."""
    current = template_sha256(template_path)
    return (current is not None and isinstance(fact, dict)
            and fact.get("template_sha256") == current and isinstance(fact.get("describe"), dict))


def refresh_fact(snapshot: dict, which_fn, run_fn) -> bool:
    """Refresh a missing, failed or stale fact in the snapshot."""
    template = resolve_cross_ai_template_path()
    if fact_is_current(snapshot.get("runner"), template):
        return False
    snapshot["runner"] = read_runner_describe(which_fn("node"), template, run_fn)
    return True


def runner_has_exec(fact, runtime) -> bool | None:
    """Return only a current, explicitly boolean exec formula fact."""
    if not fact_is_current(fact, resolve_cross_ai_template_path()):
        return None
    value = fact["describe"]
    for key in ("runtimes", runtime, "formulas", "exec"):
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value if isinstance(value, bool) else None


def stored_fact(env: dict) -> dict | None:
    """Read the current runner fact from the runtimes cache, if available."""
    snapshot = cache_read_json(cache_runtimes_path(env))
    fact = snapshot.get("runner") if isinstance(snapshot, dict) else None
    return fact if fact_is_current(fact, resolve_cross_ai_template_path()) else None
