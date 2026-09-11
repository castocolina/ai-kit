"""Detection layer for the two execution/plan-review preference ladders (07-CONTEXT.md D-02,
D-03 Specifics). Reuses `ai_kit_spec`'s own `detect-runtimes` CLI subcommand via subprocess for
the actual CLI/model enumeration -- this module never re-implements detection logic itself, it
only shells out to the already-live-verified pipeline
(`skills/ai-kit-spec-review/ai_kit_spec/detection.py`'s `build_runtimes_snapshot`) and reshapes
its output into a plain `{cli_name: [model_id, ...]}` pool for `preference_match.py` to consume.

`resolve_ai_kit_spec_path` mirrors `ai-kit-spec-execute-gsd/SKILL.md`'s own Step 0 multi-
candidate resolution pattern (`CLAUDE_PLUGIN_ROOT`-relative, then `~/.claude/skills/<name>`,
then a sibling-of-this-skill's-own-directory fallback) since THIS skill has no guaranteed
`CLAUDE_PLUGIN_ROOT` either -- it locates `ai-kit-spec-review`'s own CLI entrypoint
(`ai-kit-spec.py`), never assumes a fixed absolute path.
"""
import json
import os
import subprocess

# The sibling skill this module locates -- never imported/vendored, only invoked as a
# subprocess (detection) or, in preference_match.py/cross_ai_build.py, imported for ONE proven
# helper each, per D-02's "reuse via the CLI boundary, not via a cross-skill Python import"
# framing for detection specifically.
_SIBLING_SKILL_NAME = "ai-kit-spec-review"
_SIBLING_SHIM_NAME = "ai-kit-spec.py"


def resolve_ai_kit_spec_path(this_skill_dir, env=None, isdir_fn=os.path.isdir):
    """Returns the absolute path to `ai-kit-spec-review`'s own `ai-kit-spec.py` CLI entrypoint,
    or `None` when none of the candidate directories exist. Candidates, in order:
      1. `$CLAUDE_PLUGIN_ROOT/skills/ai-kit-spec-review` (only when `CLAUDE_PLUGIN_ROOT` is set)
      2. `$HOME/.claude/skills/ai-kit-spec-review`
      3. `<dirname(this_skill_dir)>/ai-kit-spec-review` (sibling-of-this-skill fallback)
    Never raises -- a missing sibling skill degrades detection to "no candidates", not a crash.
    """
    env = env if env is not None else dict(os.environ)
    candidates = []
    plugin_root = env.get("CLAUDE_PLUGIN_ROOT")
    if plugin_root:
        candidates.append(os.path.join(plugin_root, "skills", _SIBLING_SKILL_NAME))
    home = env.get("HOME") or os.path.expanduser("~")
    candidates.append(os.path.join(home, ".claude", "skills", _SIBLING_SKILL_NAME))
    candidates.append(os.path.join(os.path.dirname(this_skill_dir), _SIBLING_SKILL_NAME))

    for candidate_dir in candidates:
        if isdir_fn(candidate_dir):
            return os.path.join(candidate_dir, _SIBLING_SHIM_NAME)
    return None


def detect_runtimes_snapshot(python_bin, ai_kit_spec_path, run_fn=subprocess.run):
    """Runs `<python_bin> <ai_kit_spec_path> detect-runtimes` (no `--save`/`--if-stale` -- this
    always wants a fresh, unpersisted snapshot, since a stale cached snapshot could hide a
    just-installed CLI), `json.loads`s stdout, and returns the parsed `{"clis": {...}}` dict, or
    `None` on any failure (non-zero exit, timeout, unparseable stdout)."""
    try:
        result = run_fn(
            [python_bin, ai_kit_spec_path, "detect-runtimes"],
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return None


def build_candidate_pool(runtimes_snapshot):
    """Pure function, no I/O, taking the ALREADY-parsed snapshot dict. Returns
    `{"opencode": [model_id, ...], "cursor-agent": [model_id, ...]}`, omitting a CLI key
    entirely when that CLI's `installed` is falsy or it has no `"models"` list at all (never an
    empty-list placeholder for a CLI that was never enumerable in the first place --
    claude/codex/grok never appear as keys, matching `build_runtimes_snapshot`'s own shape:
    only opencode/cursor-agent ever carry a `"models"` list). An installed CLI whose `"models"`
    key is present but genuinely empty (`[]`) DOES appear as a key with an empty list -- that is
    a real "installed, zero models detected" result, distinct from "never enumerable"."""
    pool = {}
    clis = (runtimes_snapshot or {}).get("clis", {}) or {}
    for cli_name, entry in clis.items():
        if not isinstance(entry, dict):
            continue
        if not entry.get("installed"):
            continue
        models = entry.get("models")
        if models is None:
            continue
        pool[cli_name] = models
    return pool
