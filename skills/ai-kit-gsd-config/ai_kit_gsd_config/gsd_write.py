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
import json
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


def config_get(node_bin, gsd_tools_path, project_dir, key_path, run_fn=subprocess.run):
    """Runs `config-get <key_path> --project-dir <project_dir>` and returns the JSON-decoded
    current value at `key_path` (e.g. `["opencode"]`), or `None` when the key is absent/unset or
    the subprocess otherwise fails. gsd-tools' own `config-get` reports a clean "not set" result
    distinctly from an unrelated error, but this function treats both identically as `None`,
    since the only use of this result is deciding whether to append into an existing list --
    appending into an absent list degrades safely to a fresh one-element list either way.

    Deliberately omits `--raw` (a documented deviation -- see 07-02-SUMMARY.md): confirmed live
    against the installed gsd-tools.cjs that `config-get --raw` on an array value serializes via
    JS's own `String(array)`, which comma-joins elements into a BARE string (`"opencode,cursor"`,
    no brackets) -- not valid JSON, and indistinguishable from a genuine single-element string
    value. Plain (non-raw) mode always emits real `JSON.stringify`d output
    (`["opencode","cursor"]` / `"adaptive"`), which `json.loads` here decodes correctly for both
    list and scalar keys -- the only way to actually satisfy this function's own "JSON-decoded
    current value" contract for a list-typed key like `review.default_reviewers`."""
    result = run_fn(
        [node_bin, gsd_tools_path, "config-get", key_path, "--project-dir", project_dir],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return None
