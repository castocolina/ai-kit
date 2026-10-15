"""The one gsd-tools resolver and the only gsd-tools config write wrappers in ai-kit
(D-18, 16.1-CONTEXT.md).

The resolver finds the installed gsd-core's `gsd-tools.cjs` in GSD's own launcher order
(R17): `<root>/gsd-core`, `<root>/.claude/gsd-core`, `<root>/.codex/gsd-core`, then the
per-host config homes, then a `gsd_run` launcher on PATH -- where root = `RUNTIME_DIR` or
`git rev-parse --show-toplevel` of the start dir, else the start dir itself. GSD is
installed per project, so a project-local gsd-core must win over any global one.

`skills/ai-kit-gsd-spec-discuss/scripts/edge_floor.py` keeps its own standalone stdlib copy
of this order (`engine_candidates`); a test in `tests/test_ai_kit_spec_gsd_tools.py` pins
the two together so they cannot drift.

The `config-set`/`config-get`/`config-path`/`config-new-project` wrappers defined here are
the only modules in ai-kit permitted to shell out to gsd-tools for a config write -- every
write passes through gsd-tools' own CLI so GSD's schema validator runs on every write.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from collections.abc import Callable, Mapping
from typing import NamedTuple

# Relative path of the gsd-tools entrypoint inside a gsd-core install root.
GSD_TOOLS_REL = os.path.join("bin", "gsd-tools.cjs")


def project_root(
    env: Mapping[str, str],
    start: str,
    run_fn: Callable[..., subprocess.CompletedProcess] = subprocess.run,
) -> str:
    """`RUNTIME_DIR`, else the git toplevel of `start`, else `start` (gsd_run resolver rule)."""
    if env.get("RUNTIME_DIR", "").strip():
        return env["RUNTIME_DIR"].strip()
    try:
        out = run_fn(["git", "-C", start, "rev-parse", "--show-toplevel"],
                     capture_output=True, text=True, timeout=10, check=False)
    except (OSError, subprocess.SubprocessError):
        return start
    stdout = out.stdout or ""
    return stdout.strip() if out.returncode == 0 and stdout.strip() else start


def _host_homes(env: Mapping[str, str]) -> list[str]:
    """Host config homes, in gsd-core's own `gsd_run` resolver order (gsd-run-resolver.md).

    Copied verbatim from `edge_floor.py`'s `_host_homes`; the drift test keeps them equal.
    """
    home = env.get("HOME", "~")
    xdg = env.get("XDG_CONFIG_HOME", "").strip() or os.path.join(home, ".config")

    def pick(names: tuple[str, ...], default: str) -> str:
        return next((env[n].strip() for n in names if env.get(n, "").strip()), default)

    return [pick(("CLAUDE_CONFIG_DIR",), os.path.join(home, ".claude")),
            pick(("ANTIGRAVITY_CONFIG_DIR",), os.path.join(home, ".gemini", "antigravity")),
            os.path.join(home, ".gemini", "antigravity-ide"),
            os.path.join(home, ".gemini", "antigravity-cli"),
            pick(("AUGMENT_CONFIG_DIR",), os.path.join(home, ".augment")),
            pick(("CLINE_CONFIG_DIR",), os.path.join(home, ".cline")),
            pick(("CODEBUDDY_CONFIG_DIR",), os.path.join(home, ".codebuddy")),
            pick(("CODEX_HOME",), os.path.join(home, ".codex")),
            pick(("COPILOT_CONFIG_DIR", "COPILOT_HOME"), os.path.join(home, ".copilot")),
            pick(("CURSOR_CONFIG_DIR",), os.path.join(home, ".cursor")),
            pick(("HERMES_HOME",), os.path.join(home, ".hermes")),
            pick(("KILO_CONFIG_DIR",), os.path.join(xdg, "kilo")),
            pick(("KIMI_CONFIG_DIR",), os.path.join(home, ".config", "agents")),
            os.path.join(home, ".agents"),
            pick(("KIMI_CODE_HOME",), os.path.join(home, ".kimi-code")),
            pick(("OPENCODE_CONFIG_DIR",), os.path.join(xdg, "opencode")),
            pick(("PI_CODING_AGENT_DIR",), os.path.join(home, ".pi", "agent")),
            pick(("QWEN_CONFIG_DIR",), os.path.join(home, ".qwen")),
            pick(("TRAE_CONFIG_DIR",), os.path.join(home, ".trae")),
            pick(("WINDSURF_CONFIG_DIR",), os.path.join(home, ".codeium", "windsurf")),
            pick(("ZCODE_CONFIG_DIR",), os.path.join(home, ".zcode")),
            pick(("GROK_AGENTS_HOME",), os.path.join(home, ".agents"))]


def local_gsd_core_roots(root: str) -> list[str]:
    """Project-local gsd-core install roots in GSD's launcher order (before any host home).

    Shared by `gsd_core_roots` and the curated-config inventory resolver — never duplicate
    this list elsewhere."""
    return [os.path.join(root, "gsd-core"), os.path.join(root, ".claude", "gsd-core"),
            os.path.join(root, ".codex", "gsd-core")]


def gsd_core_roots(env: Mapping[str, str], root: str) -> list[str]:
    """gsd-core install-root candidates in GSD's launcher order: project-local first, then
    the host homes."""
    roots = list(local_gsd_core_roots(root))
    roots += [os.path.join(h, "gsd-core") for h in _host_homes(env)]
    return roots


def gsd_tools_candidates(
    env: Mapping[str, str], root: str, which_fn: Callable[..., str | None] = shutil.which
) -> list[str]:
    """gsd-tools.cjs locations: the install roots expanded with `GSD_TOOLS_REL`, then the
    `gsd_run` launcher's bin dir when `gsd_run` is on env PATH (the GSD shim puts gsd-core's
    own bin dir on PATH for later shells)."""
    paths = [os.path.expanduser(os.path.join(r, GSD_TOOLS_REL)) for r in gsd_core_roots(env, root)]
    launcher = which_fn("gsd_run", path=env["PATH"]) if env.get("PATH") else None
    if launcher:
        paths.append(os.path.join(os.path.dirname(os.path.realpath(launcher)), "gsd-tools.cjs"))
    return paths


def resolve_gsd_tools(
    env: Mapping[str, str] | None = None,
    start: str | None = None,
    isfile_fn: Callable[[str], bool] = os.path.isfile,
    run_fn: Callable[..., subprocess.CompletedProcess] = subprocess.run,
    which_fn: Callable[..., str | None] = shutil.which,
) -> str | None:
    """First existing gsd-tools.cjs candidate in launcher order, or `None`. `start` defaults
    to the current directory. Never raises, never prints -- the caller decides how to report
    a miss."""
    env = env if env is not None else dict(os.environ)
    if start is None:
        start = os.getcwd()
    for path in gsd_tools_candidates(env, project_root(env, start, run_fn), which_fn):
        if isfile_fn(path):
            return path
    return None


class GsdTools(NamedTuple):
    """The resolved node binary and gsd-tools.cjs path, threaded through every wrapper."""

    node_bin: str
    gsd_tools_path: str


class ConfigGetResult(NamedTuple):
    """`config_get` outcome: `found` distinguishes an absent key (or a clean miss) from a
    failure; `error` carries gsd-tools' stderr for a genuine failure, `None` otherwise."""

    found: bool
    value: object
    error: str | None


def _coerce_value(value: object) -> str:
    """Python `None` maps to gsd-tools' `null` unset sentinel, booleans to the lowercase
    literals config-set parses (`str(True)`'s capitalized form would NOT match), lists/dicts
    to JSON, everything else through `str()`."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (list, dict)):
        return json.dumps(value)
    return str(value)


def config_set(
    tools: GsdTools,
    project_dir: str,
    key: str,
    value: object,
    run_fn: Callable[..., subprocess.CompletedProcess] = subprocess.run,
) -> tuple[bool, str]:
    """Runs `config-set <key> <value> --project-dir <dir>` WITHOUT `--raw` (per RUN-11 the
    undo log reads the prior value from the JSON result's `previousValue`, which `--raw`
    would reduce to `key=value`). Returns `(True, stdout)` on exit 0, `(False, stderr)`
    otherwise -- never raises on a subprocess failure, including a spawn `OSError` (a
    missing `node`), which reads as `(False, str(exc))`."""
    try:
        result = run_fn(
            [tools.node_bin, tools.gsd_tools_path, "config-set", key, _coerce_value(value),
             "--project-dir", project_dir],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        return False, str(exc)
    if result.returncode == 0:
        return True, result.stdout.strip()
    return False, result.stderr.strip()


def prior_value(output: str) -> tuple[bool, object] | None:
    """Extracts the prior value from a `config-set` JSON result: `(True, previousValue)`
    when the key existed, `(False, None)` when gsd-tools omitted `previousValue` (the key
    was absent), `None` when the output is not a JSON object at all."""
    try:
        parsed = json.loads(output)
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, dict):
        return None
    if "previousValue" in parsed:
        return True, parsed["previousValue"]
    return False, None


def config_get(
    tools: GsdTools,
    project_dir: str,
    key: str,
    run_fn: Callable[..., subprocess.CompletedProcess] = subprocess.run,
) -> ConfigGetResult:
    """Runs `config-get <key> --project-dir <dir>` (deliberately no `--raw`: confirmed live
    that `config-get --raw` on an array value comma-joins it into a bare string, which is
    not valid JSON and indistinguishable from a genuine single-element string; plain mode
    always emits `JSON.stringify`d output). A clean "key not found" miss returns
    `(False, None, None)`; any other non-zero exit returns the stderr as `error`; a zero
    exit with unparseable stdout names the bad output in `error`."""
    result = run_fn(
        [tools.node_bin, tools.gsd_tools_path, "config-get", key, "--project-dir", project_dir],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        stderr = result.stderr.strip()
        if stderr == f"Error: Key not found: {key}":
            return ConfigGetResult(False, None, None)
        return ConfigGetResult(False, None, stderr)
    try:
        return ConfigGetResult(True, json.loads(result.stdout), None)
    except json.JSONDecodeError:
        return ConfigGetResult(False, None, f"unparseable config-get output: {result.stdout!r}")


def config_path(
    tools: GsdTools,
    project_dir: str,
    run_fn: Callable[..., subprocess.CompletedProcess] = subprocess.run,
) -> str | None:
    """Runs `config-path --cwd <dir>` (which honors workstreams); returns the resolved
    config path, or `None` on failure or empty output."""
    result = run_fn(
        [tools.node_bin, tools.gsd_tools_path, "config-path", "--cwd", project_dir],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def gsd_core_version(gsd_tools_path: str) -> str | None:
    """The stripped text of the gsd-core `VERSION` file (two directories above
    `bin/gsd-tools.cjs`, i.e. the install root), or `None` on OSError -- callers print it so a
    `previousValue` contract drift on a non-1.16 gsd-core is diagnosable from any run."""
    root = os.path.dirname(os.path.dirname(gsd_tools_path))
    try:
        with open(os.path.join(root, "VERSION"), encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return None


def ensure_config_exists(
    tools: GsdTools,
    project_dir: str,
    run_fn: Callable[..., subprocess.CompletedProcess] = subprocess.run,
) -> bool:
    """Runs `config-new-project --cwd <dir>`. `True` covers both the freshly-created case
    and gsd-tools' own idempotent `already_exists` no-op; `False` otherwise."""
    result = run_fn(
        [tools.node_bin, tools.gsd_tools_path, "config-new-project", "--cwd", project_dir,
         "--raw"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0
