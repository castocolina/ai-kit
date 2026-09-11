"""The ONLY place in this whole skill that constructs a `config-set`/`config-new-project`
argv (D-01, 07-CONTEXT.md). Every config write in this skill goes through gsd-tools' own
CLI subcommands so GSD's own schema manifest/validator (`config-schema.manifest.json`) runs
on every write -- this module never calls `open(...)` on a `.planning/config.json` path, and
no other module in this skill may shell out to gsd-tools directly.

Contrast with `skills/ai-kit-spec-execute-gsd/ai_kit_spec_gsd/gsd_config.py`, a sibling skill
that deliberately hand-rolls its own JSON read/write of `.planning/config.json` -- that module
owns an ephemeral, adapter-owned per-run dispatch config with its own backup/ownership-marker
conventions, a genuinely different use case. This skill's writes are durable, user-facing
config keys that must pass GSD's real schema validation, so they are written exclusively
through gsd-tools' own CLI, never through a hand-rolled read/write of the file.
"""
import subprocess


def ensure_config_exists(node_bin, gsd_tools_path, target_dir, run_fn=subprocess.run) -> bool:
    """Runs `config-new-project --cwd <target_dir>`. Returns `True` when the subprocess exit
    code is 0 -- covers BOTH the freshly-created case and gsd-tools' own idempotent
    `already_exists` no-op, both success from this function's point of view. Returns `False`
    otherwise."""
    result = run_fn(
        [node_bin, gsd_tools_path, "config-new-project", "--cwd", target_dir, "--raw"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0


def _coerce_value(value):
    """A Python `bool` True/False serializes to the literal strings `config-set` itself
    parses (`"true"`/`"false"`) -- the Python-native capitalized `str(True)` == "True" form
    would NOT match config-set's own value parser, so booleans get an explicit lowercase
    coercion here rather than the default `str()`."""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def config_set(node_bin, gsd_tools_path, target_dir, key, value, run_fn=subprocess.run):
    """Runs `config-set <key> <value> --project-dir <target_dir>`. Returns `(True, stdout)`
    on exit code 0, `(False, stderr)` on non-zero exit -- never raises on a subprocess
    failure, only on a genuinely unexpected exception (e.g. `node` missing from PATH), which
    it lets propagate since that is an environment problem the CLI's own top-level handler
    reports."""
    result = run_fn(
        [
            node_bin,
            gsd_tools_path,
            "config-set",
            key,
            _coerce_value(value),
            "--project-dir",
            target_dir,
            "--raw",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode == 0:
        return True, result.stdout.strip()
    return False, result.stderr.strip()
