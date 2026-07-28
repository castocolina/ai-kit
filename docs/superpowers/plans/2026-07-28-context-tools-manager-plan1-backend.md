# Context Tools Manager — Plan 1: Catalog & Headless CLI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the data-driven catalog and stdlib-only orchestration module for
detecting/installing/configuring rtk, codegraph, grapify, and gitnexus, exposed
today via a headless `--context-tools` CLI flag on `tools/setup.py`.

**Architecture:** A new TOML catalog (`tools/context_tools_inventory.toml`,
structurally parallel to `segments_inventory.toml`) is the single source of
truth for each tool's detect/install/configure shell commands. A new stdlib-only
module (`tools/context_tools.py`) parses it and wraps `subprocess` calls
(always executed through a shell, since catalog commands are opaque shell
command lines that may contain pipes/redirection/`&&` — e.g. rtk's install
script) behind three functions (`detect_tool`, `install_tool`,
`configure_tool`) plus a headless orchestrator (`run_context_tools_headless`).
`tools/setup.py` gains a `--context-tools=all|none|<ids>` flag that drives the
orchestrator with no TUI involved. **This plan does NOT touch the Textual
wizard** (`tools/wizard_app.py`) at all — the interactive Step 0 screen is a
separate follow-on plan, built once this module's API is locked and tested.

**Tech Stack:** Python 3.11 stdlib only (`subprocess`, `tomllib`, `re`) —
no new dependencies. Matches `tools/status-line.py`'s "no non-stdlib import"
philosophy; `tools/context_tools.py` is imported lazily by `setup.py` exactly
the way `wizard_app` already is, so it never forces the `uv`/`textual`
re-exec path.

## Global Constraints

- Every install/configure command uses `pnpm`, never `npm`, wherever a tool's
  own docs offer either (explicit user preference).
- `tools/context_tools.py` must never import from `tools/setup.py` (one-way
  dependency: setup.py -> context_tools.py only), matching the existing
  `wizard_app.py` isolation rule ("imports NOTHING from setup.py").
- No real subprocess/network call may execute during `make test` — every test
  in this plan mocks `subprocess.run`/`subprocess.Popen`.
- `detect_tool`, `install_tool` (via `_run_streaming`), and `configure_tool`
  (via `_run_streaming`) MUST execute their catalog command string through a
  shell — `subprocess.run(cmd, shell=True, ...)` /
  `subprocess.Popen(cmd, shell=True, ...)` — never `shlex.split(cmd)` fed to
  a bare-argv exec. Catalog entries are free to use shell constructs (pipes,
  redirection, `&&` chains — e.g. rtk's `curl -fsSL ... | sh`); a bare-argv
  exec cannot interpret those as shell operators and would hand them to the
  first program as literal arguments instead, silently breaking the entry.
  This is the design doc's §4 binding execution-model requirement.
- `context_tools.py` is imported **lazily** inside the function that needs it
  in `setup.py` (mirrors the existing `wizard_app` lazy-import pattern at
  `tools/setup.py`'s `launch_wizard`, including the `sys.path` guard) — never
  a module-level `import context_tools` at the top of `setup.py`.
- `--context-tools` with no flag present is a full no-op (opt-in only) — there
  is no wizard step yet in this plan to supply an interactive default.
- Follow the repo's existing lint/test gate: `uv run pre-commit run --all-files`
  (ruff, pylint, pyright, vulture, shellcheck, py-compile, unittest core,
  unittest wizard) must pass clean after every task.

---

### Task 1: Catalog file + data types + loader

**Files:**
- Create: `tools/context_tools_inventory.toml`
- Create: `tools/context_tools.py`
- Test: `tests/test_context_tools.py`

**Interfaces:**
- Produces: `ToolSpec` (NamedTuple: `id: str, name: str, description: str,
  detect: str, install: str, configure: str, configure_scoped: str,
  supports_env_scoping: bool, envs: tuple[str, ...]`), `ToolStatus` (NamedTuple:
  `installed: bool | None, version: str | None`), `CommandResult` (NamedTuple:
  `ok: bool, log: str` — not consumed until Task 2, but defined here alongside
  the other data types), `ENV_LABELS: dict[str, str]`,
  `CONTEXT_TOOLS_INVENTORY_PATH: str`, `load_context_tools_inventory(path: str) ->
  dict[str, ToolSpec]`.

- [ ] **Step 1: Write the catalog TOML**

Create `tools/context_tools_inventory.toml`:

```toml
# AI context-tools catalog — installer/wizard-only metadata (never read by the
# status-line render path). Each section is one tool; `detect` is the presence
# probe, `install` gets the binary/package on disk, `configure` runs the tool's
# OWN agent-wiring command (MCP registration, hooks, skill files). Tools that
# support scoping their configure step to specific agent environments also
# carry `configure_scoped` (a template with either a singular {env} placeholder,
# invoked once per selected env, or a plural {envs} placeholder, invoked once
# with a comma-joined list — whichever the tool's own CLI expects) and `envs`
# (the ordered list of environment ids it supports).

[rtk]
name = "rtk"
description = "CLI proxy that compresses shell output before it reaches the agent (60-90% token savings)"
detect = "rtk --version"
install = "curl -fsSL https://raw.githubusercontent.com/rtk-ai/rtk/master/install.sh | sh"
configure = "rtk init -g"
configure_scoped = ""
supports_env_scoping = false
envs = []

[codegraph]
name = "codegraph"
description = "Pre-indexed code knowledge graph; auto-syncs on file changes"
detect = "codegraph --version"
install = "pnpm add -g @colbymchenry/codegraph"
configure = "codegraph install"
configure_scoped = ""
supports_env_scoping = false
envs = []

[grapify]
name = "grapify"
description = "Codebase -> queryable knowledge graph (tree-sitter, local, no vector store)"
detect = "graphify --version"
install = "uv tool install graphifyy"
configure = "graphify install"
configure_scoped = "graphify install --platform {env}"
supports_env_scoping = true
envs = ["claude_code", "cursor", "codex", "gemini_cli", "vscode", "antigravity", "opencode", "aider"]

[gitnexus]
name = "gitnexus"
description = "Knowledge-graph code intelligence engine (MCP), per-repo index"
detect = ""
install = ""
configure = "pnpm dlx gitnexus@latest setup"
configure_scoped = "pnpm dlx gitnexus@latest setup -c {envs}"
supports_env_scoping = true
envs = ["claude_code", "codex", "cursor", "antigravity", "opencode", "windsurf"]
```

- [ ] **Step 2: Write the failing loader tests**

Create `tests/test_context_tools.py`:

```python
import importlib.util
import os
import sys
import tempfile
import unittest

_HERE = os.path.dirname(__file__)
_MODULE_PATH = os.path.join(_HERE, "..", "tools", "context_tools.py")


def load_module():
    spec = importlib.util.spec_from_file_location("context_tools", _MODULE_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


ct = load_module()


class TestLoadInventory(unittest.TestCase):
    def test_real_catalog_loads_all_four_tools(self):
        inv = ct.load_context_tools_inventory(ct.CONTEXT_TOOLS_INVENTORY_PATH)
        self.assertEqual(set(inv), {"rtk", "codegraph", "grapify", "gitnexus"})

    def test_grapify_is_scoped_with_singular_template(self):
        inv = ct.load_context_tools_inventory(ct.CONTEXT_TOOLS_INVENTORY_PATH)
        g = inv["grapify"]
        self.assertTrue(g.supports_env_scoping)
        self.assertIn("{env}", g.configure_scoped)
        self.assertIn("cursor", g.envs)

    def test_gitnexus_has_no_detect_or_install(self):
        inv = ct.load_context_tools_inventory(ct.CONTEXT_TOOLS_INVENTORY_PATH)
        gx = inv["gitnexus"]
        self.assertEqual(gx.detect, "")
        self.assertEqual(gx.install, "")
        self.assertIn("{envs}", gx.configure_scoped)

    def test_missing_file_yields_empty_dict(self):
        self.assertEqual(ct.load_context_tools_inventory("/no/such/file.toml"), {})

    def test_malformed_toml_yields_empty_dict(self):
        with tempfile.NamedTemporaryFile("w", suffix=".toml", delete=False) as f:
            f.write("not = [valid toml")
            path = f.name
        self.addCleanup(os.unlink, path)
        self.assertEqual(ct.load_context_tools_inventory(path), {})

    def test_non_table_entries_are_skipped(self):
        with tempfile.NamedTemporaryFile("w", suffix=".toml", delete=False) as f:
            f.write('version = 1\n[rtk]\nname = "rtk"\n')
            path = f.name
        self.addCleanup(os.unlink, path)
        inv = ct.load_context_tools_inventory(path)
        self.assertEqual(set(inv), {"rtk"})
        self.assertEqual(inv["rtk"].description, "")   # defaults for absent keys

    def test_env_labels_cover_every_catalog_env_id(self):
        inv = ct.load_context_tools_inventory(ct.CONTEXT_TOOLS_INVENTORY_PATH)
        all_envs = {e for spec in inv.values() for e in spec.envs}
        self.assertTrue(all_envs.issubset(set(ct.ENV_LABELS)))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `python3 -S -m unittest tests.test_context_tools -v`
Expected: FAIL — `tools/context_tools.py` does not exist yet (ModuleNotFoundError
surfaces as an import error from `load_module()`).

- [ ] **Step 4: Write `tools/context_tools.py`**

```python
"""ai-kit context-tools catalog + orchestration (stdlib-only, like status-line.py).

Detects, installs, and configures a small family of AI-agent "code
intelligence" tools (rtk, codegraph, grapify, gitnexus) by shelling out to
each tool's OWN install/setup command — this module never reimplements any
tool's agent-wiring logic. `tools/context_tools_inventory.toml` is the single
source of truth for which command to run; no tool-specific branching lives
here. Catalog command strings are opaque shell command lines (may contain
pipes, redirection, or `&&` chains — e.g. rtk's install command, a vendor
curl script piped into `sh`) and are always executed via `shell=True`, never
split into an argv list. Installer/wizard-only concern: never imported by
the status-line render path, and this module must never import from
tools/setup.py (one-way dependency, mirrors wizard_app.py's isolation from
setup.py)."""
import os
import re
import subprocess
import tomllib
from typing import Callable, NamedTuple


class ToolSpec(NamedTuple):
    """One catalog entry. `detect`/`install` are empty strings for a tool with
    no persistent global install (gitnexus) — always "configure only".
    `configure_scoped` is empty when `supports_env_scoping` is False."""
    id: str
    name: str
    description: str
    detect: str
    install: str
    configure: str
    configure_scoped: str
    supports_env_scoping: bool
    envs: tuple[str, ...]


class ToolStatus(NamedTuple):
    """`installed` is None for a tool with no detect command (gitnexus) — a
    third state distinct from True/False, meaning "configure only, presence
    is not knowable"."""
    installed: bool | None
    version: str | None


class CommandResult(NamedTuple):
    ok: bool
    log: str


# Shared label table so the (eventual) wizard chip-picker shows consistent
# names even though each tool's own CLI flag vocabulary differs slightly
# (gitnexus `-c cursor,codex` vs grapify `--platform codex`).
ENV_LABELS = {
    "claude_code": "Claude Code",
    "cursor": "Cursor",
    "codex": "Codex",
    "opencode": "OpenCode",
    "antigravity": "Antigravity",
    "vscode": "VS Code",
    "gemini_cli": "Gemini CLI",
    "aider": "Aider",
    "windsurf": "Windsurf",
}

CONTEXT_TOOLS_INVENTORY_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "context_tools_inventory.toml")


def _read_toml(path: str) -> dict:
    """Parse TOML at `path`. Missing/malformed -> {} (never raises) — same
    fail-closed policy as setup.py's read_toml, duplicated here rather than
    imported (context_tools.py must not depend on setup.py)."""
    try:
        with open(path, "rb") as f:
            return tomllib.load(f)
    except (FileNotFoundError, IsADirectoryError):
        return {}
    except (OSError, tomllib.TOMLDecodeError):
        return {}


def load_context_tools_inventory(path: str) -> dict[str, ToolSpec]:
    """Load the context-tools catalog keyed by tool id. A missing/malformed
    file yields {}. Absent keys in a table fall back to "" / False / ()."""
    data = _read_toml(path)
    out: dict[str, ToolSpec] = {}
    for key, val in data.items():
        if not isinstance(val, dict):
            continue
        out[key] = ToolSpec(
            id=key,
            name=str(val.get("name", key)),
            description=str(val.get("description", "")),
            detect=str(val.get("detect", "")),
            install=str(val.get("install", "")),
            configure=str(val.get("configure", "")),
            configure_scoped=str(val.get("configure_scoped", "")),
            supports_env_scoping=bool(val.get("supports_env_scoping", False)),
            envs=tuple(str(e) for e in val.get("envs", [])),
        )
    return out
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python3 -S -m unittest tests.test_context_tools -v`
Expected: all 7 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add tools/context_tools_inventory.toml tools/context_tools.py tests/test_context_tools.py
git commit -m "feat(context-tools): add catalog + loader for rtk/codegraph/grapify/gitnexus"
```

---

### Task 2: Detection + install execution

**Files:**
- Modify: `tools/context_tools.py`
- Test: `tests/test_context_tools.py`

**Interfaces:**
- Consumes: `ToolSpec`, `ToolStatus`, `CommandResult` (Task 1).
- Produces: `detect_tool(spec: ToolSpec, timeout: float = 3.0) -> ToolStatus`,
  `install_tool(spec: ToolSpec, on_output: Callable[[str], None]) -> CommandResult`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_context_tools.py`:

```python
from unittest import mock


class TestDetectTool(unittest.TestCase):
    def _spec(self, detect="rtk --version", install="", configure=""):
        return ct.ToolSpec(id="x", name="x", description="", detect=detect,
                            install=install, configure=configure,
                            configure_scoped="", supports_env_scoping=False, envs=())

    def test_empty_detect_means_configure_only(self):
        status = ct.detect_tool(self._spec(detect=""))
        self.assertIsNone(status.installed)
        self.assertIsNone(status.version)

    @mock.patch("subprocess.run")
    def test_zero_exit_means_installed_with_version(self, run):
        run.return_value = mock.Mock(returncode=0, stdout="rtk 1.4.0\n", stderr="")
        status = ct.detect_tool(self._spec())
        self.assertTrue(status.installed)
        self.assertEqual(status.version, "rtk 1.4.0")

    @mock.patch("subprocess.run")
    def test_nonzero_exit_means_not_installed(self, run):
        run.return_value = mock.Mock(returncode=1, stdout="", stderr="")
        status = ct.detect_tool(self._spec())
        self.assertFalse(status.installed)
        self.assertIsNone(status.version)

    @mock.patch("subprocess.run", side_effect=FileNotFoundError())
    def test_command_not_found_means_not_installed(self, _run):
        status = ct.detect_tool(self._spec())
        self.assertFalse(status.installed)

    @mock.patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="x", timeout=3))
    def test_timeout_means_not_installed(self, _run):
        status = ct.detect_tool(self._spec())
        self.assertFalse(status.installed)

    @mock.patch("subprocess.run")
    def test_detect_runs_command_through_a_shell_not_bare_argv(self, run):
        # Regression test: shlex.split(cmd) fed to a bare-argv exec cannot
        # interpret shell operators. This asserts the command is passed as
        # ONE string with shell=True, not split into an argv list.
        run.return_value = mock.Mock(returncode=0, stdout="v1\n", stderr="")
        ct.detect_tool(self._spec(detect="rtk --version"))
        run.assert_called_once_with(
            "rtk --version", shell=True, capture_output=True, text=True,
            timeout=3.0, check=False)


class TestInstallTool(unittest.TestCase):
    def _spec(self, install="echo hi"):
        return ct.ToolSpec(id="x", name="x", description="", detect="",
                            install=install, configure="", configure_scoped="",
                            supports_env_scoping=False, envs=())

    def test_no_install_command_fails_without_running_anything(self):
        lines = []
        result = ct.install_tool(self._spec(install=""), lines.append)
        self.assertFalse(result.ok)
        self.assertIn("no install command", result.log)

    @mock.patch("subprocess.Popen")
    def test_streams_output_and_reports_success(self, popen):
        proc = mock.Mock()
        proc.stdout = iter(["line one\n", "line two\n"])
        proc.wait.return_value = None
        proc.returncode = 0
        popen.return_value = proc
        lines = []
        result = ct.install_tool(self._spec(), lines.append)
        self.assertTrue(result.ok)
        self.assertEqual(lines, ["line one", "line two"])
        self.assertEqual(result.log, "line one\nline two")

    @mock.patch("subprocess.Popen")
    def test_nonzero_exit_reports_failure(self, popen):
        proc = mock.Mock()
        proc.stdout = iter(["boom\n"])
        proc.wait.return_value = None
        proc.returncode = 1
        popen.return_value = proc
        result = ct.install_tool(self._spec(), lambda _l: None)
        self.assertFalse(result.ok)

    @mock.patch("subprocess.Popen", side_effect=OSError("no such file"))
    def test_failure_to_start_is_reported_not_raised(self, _popen):
        lines = []
        result = ct.install_tool(self._spec(), lines.append)
        self.assertFalse(result.ok)
        self.assertIn("failed to start", result.log)

    @mock.patch("subprocess.Popen")
    def test_install_runs_pipe_command_through_a_shell_not_bare_argv(self, popen):
        # Regression test for the catalog's real rtk entry: a vendor curl
        # script piped into `sh`. shlex.split() would tokenize this into
        # ['curl', '-fsSL', 'https://...', '|', 'sh'] and hand '|'/'sh' to
        # curl as literal extra arguments instead of a shell pipe. This
        # asserts the command is passed as ONE string with shell=True.
        proc = mock.Mock()
        proc.stdout = iter([])
        proc.wait.return_value = None
        proc.returncode = 0
        popen.return_value = proc
        pipe_cmd = "curl -fsSL https://example.com/install.sh | sh"
        ct.install_tool(self._spec(install=pipe_cmd), lambda _l: None)
        popen.assert_called_once_with(
            pipe_cmd, shell=True, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, text=True)
```

Add `import subprocess` to the test file's imports (needed for
`subprocess.TimeoutExpired` in the mock `side_effect`, and for the
`subprocess.PIPE`/`subprocess.STDOUT` constants asserted against above).

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -S -m unittest tests.test_context_tools.TestDetectTool tests.test_context_tools.TestInstallTool -v`
Expected: FAIL — `detect_tool`/`install_tool` not defined.

- [ ] **Step 3: Implement `detect_tool` and `install_tool`**

Append to `tools/context_tools.py` (add `Callable` is already imported in Task 1's
`typing` import):

```python
def detect_tool(spec: ToolSpec, timeout: float = 3.0) -> ToolStatus:
    """Runs spec.detect (if any) with a short timeout. A tool with no detect
    command (gitnexus) is always "configure only" (installed=None) — there is
    nothing to probe since it has no persistent global install. Runs through
    a shell (shell=True) rather than shlex.split() + bare-argv exec, since
    catalog command strings are opaque shell command lines (see module
    docstring) — matches _run_streaming's execution model below."""
    if not spec.detect:
        return ToolStatus(installed=None, version=None)
    try:
        proc = subprocess.run(
            spec.detect, shell=True, capture_output=True, text=True,
            timeout=timeout, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ToolStatus(installed=False, version=None)
    if proc.returncode != 0:
        return ToolStatus(installed=False, version=None)
    combined = (proc.stdout or proc.stderr or "").strip()
    version = combined.splitlines()[0] if combined else None
    return ToolStatus(installed=True, version=version)


def _run_streaming(cmd: str, on_output: Callable[[str], None]) -> CommandResult:
    """Runs `cmd` through a shell (shell=True) — catalog command strings may
    contain pipes, redirection, or `&&` chains (e.g. rtk's install command,
    a vendor curl script piped into `sh`); shlex.split(cmd) fed to a
    bare-argv exec cannot interpret those as shell operators and would hand
    them to the first program as literal arguments instead, silently
    breaking the entry. Calls on_output once per stdout/stderr line as it
    arrives (feeds a live log panel), and returns the joined log + exit
    status. A failure to even start the process (bad command, shell itself
    missing) is caught and reported through on_output/the result rather than
    raised — this is a UI-feeding helper, never a place to crash the
    caller."""
    lines: list[str] = []
    try:
        proc = subprocess.Popen(
            cmd, shell=True, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, text=True,
        )
    except OSError as e:
        msg = f"failed to start: {e}"
        on_output(msg)
        return CommandResult(ok=False, log=msg)
    for raw_line in proc.stdout:
        line = raw_line.rstrip("\n")
        lines.append(line)
        on_output(line)
    proc.wait()
    return CommandResult(ok=(proc.returncode == 0), log="\n".join(lines))


def install_tool(spec: ToolSpec, on_output: Callable[[str], None]) -> CommandResult:
    """Runs spec.install. A tool with no install command in the catalog
    (gitnexus, which has no persistent global install) fails immediately
    without starting any process."""
    if not spec.install:
        msg = f"{spec.id}: no install command in catalog"
        on_output(msg)
        return CommandResult(ok=False, log=msg)
    return _run_streaming(spec.install, on_output)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -S -m unittest tests.test_context_tools -v`
Expected: all tests PASS (18 total so far: 7 from Task 1 + 6 in
`TestDetectTool` + 5 in `TestInstallTool`).

- [ ] **Step 5: Commit**

```bash
git add tools/context_tools.py tests/test_context_tools.py
git commit -m "feat(context-tools): add detect_tool + install_tool subprocess wrappers"
```

---

### Task 3: Configure command templating (scoped + unscoped)

**Files:**
- Modify: `tools/context_tools.py`
- Test: `tests/test_context_tools.py`

**Interfaces:**
- Consumes: `ToolSpec`, `CommandResult`, `_run_streaming` (Tasks 1-2).
- Produces: `configure_tool(spec: ToolSpec, envs: list[str], on_output:
  Callable[[str], None]) -> CommandResult`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_context_tools.py`:

```python
class TestConfigureTool(unittest.TestCase):
    def _unscoped(self):
        return ct.ToolSpec(id="rtk", name="rtk", description="", detect="",
                            install="", configure="rtk init -g",
                            configure_scoped="", supports_env_scoping=False, envs=())

    def _plural_scoped(self):
        return ct.ToolSpec(id="gitnexus", name="gitnexus", description="",
                            detect="", install="", configure="gitnexus setup",
                            configure_scoped="gitnexus setup -c {envs}",
                            supports_env_scoping=True,
                            envs=("claude_code", "codex", "cursor"))

    def _singular_scoped(self):
        return ct.ToolSpec(id="grapify", name="grapify", description="",
                            detect="", install="", configure="graphify install",
                            configure_scoped="graphify install --platform {env}",
                            supports_env_scoping=True,
                            envs=("claude_code", "codex"))

    def test_no_configure_command_fails_without_running_anything(self):
        spec = self._unscoped()._replace(configure="")
        result = ct.configure_tool(spec, [], lambda _l: None)
        self.assertFalse(result.ok)

    @mock.patch("context_tools._run_streaming")
    def test_no_envs_runs_unscoped_configure(self, run_streaming):
        run_streaming.return_value = ct.CommandResult(ok=True, log="")
        ct.configure_tool(self._unscoped(), [], lambda _l: None)
        run_streaming.assert_called_once_with("rtk init -g", mock.ANY)

    @mock.patch("context_tools._run_streaming")
    def test_unscoped_tool_ignores_envs(self, run_streaming):
        run_streaming.return_value = ct.CommandResult(ok=True, log="")
        ct.configure_tool(self._unscoped(), ["cursor"], lambda _l: None)
        run_streaming.assert_called_once_with("rtk init -g", mock.ANY)

    @mock.patch("context_tools._run_streaming")
    def test_plural_template_joins_envs_into_one_call(self, run_streaming):
        run_streaming.return_value = ct.CommandResult(ok=True, log="")
        ct.configure_tool(self._plural_scoped(), ["cursor", "codex"], lambda _l: None)
        run_streaming.assert_called_once_with(
            "gitnexus setup -c cursor,codex", mock.ANY)

    @mock.patch("context_tools._run_streaming")
    def test_singular_template_runs_once_per_env(self, run_streaming):
        run_streaming.return_value = ct.CommandResult(ok=True, log="ok")
        ct.configure_tool(self._singular_scoped(), ["claude_code", "codex"],
                          lambda _l: None)
        self.assertEqual(run_streaming.call_args_list, [
            mock.call("graphify install --platform claude_code", mock.ANY),
            mock.call("graphify install --platform codex", mock.ANY),
        ])

    @mock.patch("context_tools._run_streaming")
    def test_singular_template_one_failure_makes_overall_result_fail(self, run_streaming):
        run_streaming.side_effect = [
            ct.CommandResult(ok=True, log="a"),
            ct.CommandResult(ok=False, log="b"),
        ]
        result = ct.configure_tool(self._singular_scoped(), ["claude_code", "codex"],
                                    lambda _l: None)
        self.assertFalse(result.ok)
        self.assertEqual(result.log, "a\nb")

    @mock.patch("context_tools._run_streaming")
    def test_empty_envs_on_scoped_tool_runs_unscoped_configure(self, run_streaming):
        run_streaming.return_value = ct.CommandResult(ok=True, log="")
        ct.configure_tool(self._plural_scoped(), [], lambda _l: None)
        run_streaming.assert_called_once_with("gitnexus setup", mock.ANY)
```

Every `@mock.patch("context_tools._run_streaming")` above patches the name
in the module registered by `load_module()`'s
`spec_from_file_location("context_tools", ...)` at the top of this test
file — the same `ct` module the test methods call into.

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -S -m unittest tests.test_context_tools.TestConfigureTool -v`
Expected: FAIL — `configure_tool` not defined.

- [ ] **Step 3: Implement `configure_tool`**

Append to `tools/context_tools.py`:

```python
def configure_tool(
    spec: ToolSpec, envs: list[str], on_output: Callable[[str], None],
) -> CommandResult:
    """Runs the tool's own agent-wiring command. With no envs selected, or on
    a tool that doesn't support scoping, or a scoped tool whose
    configure_scoped template has neither placeholder, runs the full
    auto-detect `spec.configure`. Otherwise formats configure_scoped:
    a plural `{envs}` placeholder is invoked ONCE with a comma-joined list
    (e.g. gitnexus's `-c cursor,codex`); a singular `{env}` placeholder is
    invoked ONCE PER selected env (e.g. grapify's `--platform <one-env>`,
    which the tool's own CLI does not accept as a repeated flag) — the
    overall result is ok only if every per-env call succeeded, and the log
    is every call's log newline-joined in order."""
    if not spec.configure:
        msg = f"{spec.id}: no configure command in catalog"
        on_output(msg)
        return CommandResult(ok=False, log=msg)
    if not envs or not spec.supports_env_scoping or not spec.configure_scoped:
        return _run_streaming(spec.configure, on_output)
    if "{envs}" in spec.configure_scoped:
        cmd = spec.configure_scoped.format(envs=",".join(envs))
        return _run_streaming(cmd, on_output)
    if "{env}" in spec.configure_scoped:
        results = [_run_streaming(spec.configure_scoped.format(env=e), on_output)
                   for e in envs]
        return CommandResult(ok=all(r.ok for r in results),
                              log="\n".join(r.log for r in results))
    return _run_streaming(spec.configure, on_output)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -S -m unittest tests.test_context_tools -v`
Expected: all tests PASS (25 total so far: 18 from Tasks 1-2 + 7 in
`TestConfigureTool`).

- [ ] **Step 5: Commit**

```bash
git add tools/context_tools.py tests/test_context_tools.py
git commit -m "feat(context-tools): add configure_tool with scoped/unscoped templating"
```

---

### Task 4: Headless selection + orchestrator

**Files:**
- Modify: `tools/context_tools.py`
- Test: `tests/test_context_tools.py`

**Interfaces:**
- Consumes: `ToolSpec`, `ToolStatus`, `detect_tool`, `install_tool`,
  `configure_tool` (Tasks 1-3).
- Produces: `resolve_context_tools_selection(flag: str | None, catalog:
  dict[str, ToolSpec]) -> list[str]`, `run_context_tools_headless(catalog:
  dict[str, ToolSpec], ids: list[str], dry: bool, on_output: Callable[[str],
  None]) -> dict[str, dict]`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_context_tools.py`:

```python
class TestResolveSelection(unittest.TestCase):
    def setUp(self):
        self.catalog = {"rtk": None, "codegraph": None, "grapify": None,
                        "gitnexus": None}   # only keys matter for this function

    def test_none_flag_means_nothing_selected(self):
        self.assertEqual(ct.resolve_context_tools_selection(None, self.catalog), [])

    def test_all_selects_every_catalog_id(self):
        self.assertEqual(
            set(ct.resolve_context_tools_selection("all", self.catalog)),
            set(self.catalog))

    def test_none_string_selects_nothing(self):
        self.assertEqual(ct.resolve_context_tools_selection("none", self.catalog), [])

    def test_comma_list_selects_matching_ids_only(self):
        result = ct.resolve_context_tools_selection("rtk,grapify,bogus", self.catalog)
        self.assertEqual(set(result), {"rtk", "grapify"})

    def test_space_separated_list_also_works(self):
        result = ct.resolve_context_tools_selection("rtk grapify", self.catalog)
        self.assertEqual(set(result), {"rtk", "grapify"})


class TestRunHeadless(unittest.TestCase):
    def _catalog(self):
        return ct.load_context_tools_inventory(ct.CONTEXT_TOOLS_INVENTORY_PATH)

    @mock.patch("context_tools.configure_tool")
    @mock.patch("context_tools.install_tool")
    @mock.patch("context_tools.detect_tool")
    def test_not_installed_tool_installs_then_configures(
        self, detect, install, configure,
    ):
        detect.return_value = ct.ToolStatus(installed=False, version=None)
        install.return_value = ct.CommandResult(ok=True, log="")
        configure.return_value = ct.CommandResult(ok=True, log="")
        out = ct.run_context_tools_headless(self._catalog(), ["rtk"], False,
                                             lambda _l: None)
        install.assert_called_once()
        configure.assert_called_once()
        self.assertTrue(out["rtk"]["install_ok"])
        self.assertTrue(out["rtk"]["configure_ok"])

    @mock.patch("context_tools.configure_tool")
    @mock.patch("context_tools.install_tool")
    @mock.patch("context_tools.detect_tool")
    def test_already_installed_tool_skips_install(
        self, detect, install, configure,
    ):
        detect.return_value = ct.ToolStatus(installed=True, version="1.0")
        configure.return_value = ct.CommandResult(ok=True, log="")
        out = ct.run_context_tools_headless(self._catalog(), ["rtk"], False,
                                             lambda _l: None)
        install.assert_not_called()
        configure.assert_called_once()
        self.assertIsNone(out["rtk"]["install_ok"])
        self.assertTrue(out["rtk"]["configure_ok"])

    @mock.patch("context_tools.configure_tool")
    @mock.patch("context_tools.install_tool")
    @mock.patch("context_tools.detect_tool")
    def test_configure_only_tool_never_calls_install(
        self, detect, install, configure,
    ):
        detect.return_value = ct.ToolStatus(installed=None, version=None)
        configure.return_value = ct.CommandResult(ok=True, log="")
        out = ct.run_context_tools_headless(self._catalog(), ["gitnexus"], False,
                                             lambda _l: None)
        install.assert_not_called()
        configure.assert_called_once()
        self.assertIsNone(out["gitnexus"]["install_ok"])

    @mock.patch("context_tools.configure_tool")
    @mock.patch("context_tools.install_tool")
    @mock.patch("context_tools.detect_tool")
    def test_failed_install_skips_configure(self, detect, install, configure):
        detect.return_value = ct.ToolStatus(installed=False, version=None)
        install.return_value = ct.CommandResult(ok=False, log="network error")
        out = ct.run_context_tools_headless(self._catalog(), ["rtk"], False,
                                             lambda _l: None)
        configure.assert_not_called()
        self.assertFalse(out["rtk"]["install_ok"])
        self.assertIsNone(out["rtk"]["configure_ok"])

    @mock.patch("context_tools.configure_tool")
    @mock.patch("context_tools.install_tool")
    @mock.patch("context_tools.detect_tool")
    def test_dry_run_calls_neither_install_nor_configure(
        self, detect, install, configure,
    ):
        detect.return_value = ct.ToolStatus(installed=False, version=None)
        ct.run_context_tools_headless(self._catalog(), ["rtk"], True, lambda _l: None)
        install.assert_not_called()
        configure.assert_not_called()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -S -m unittest tests.test_context_tools.TestResolveSelection tests.test_context_tools.TestRunHeadless -v`
Expected: FAIL — neither function defined yet.

- [ ] **Step 3: Implement both functions**

Append to `tools/context_tools.py` (no new imports needed: `re` — used below
by `resolve_context_tools_selection` to split on commas/whitespace — was
already added to the top-of-file imports in Task 1 Step 4, alongside `os`,
`subprocess`, `tomllib`):

```python
def resolve_context_tools_selection(
    flag: str | None, catalog: dict[str, ToolSpec],
) -> list[str]:
    """Resolve which catalog ids to act on from a --context-tools flag value.
    None (flag absent) -> [] — this feature is opt-in only; there is (yet) no
    interactive wizard step to supply a default the way --examples does.
    'all'/'none' are case-insensitive; otherwise a comma/space-separated id
    list, unknown ids silently ignored (mirrors setup.py's
    resolve_example_selection)."""
    if flag is None:
        return []
    norm = flag.strip().lower()
    if norm == "all":
        return list(catalog)
    if norm == "none":
        return []
    wanted = {t for t in re.split(r"[,\s]+", flag.strip()) if t}
    return [tid for tid in catalog if tid in wanted]


def run_context_tools_headless(
    catalog: dict[str, ToolSpec], ids: list[str], dry: bool,
    on_output: Callable[[str], None],
) -> dict[str, dict]:
    """For each selected id: detect -> install (only when detection says
    False AND the catalog has an install command) -> configure (full
    auto-detect, envs=[] — headless mode has no per-environment picker; that
    is an interactive-wizard-only capability). A failed install skips
    configure for that tool but does not stop the remaining ids. dry=True
    reports the intended action via on_output and calls neither install nor
    configure. Returns {id: {"installed_before": bool | None,
    "install_ok": bool | None, "configure_ok": bool | None}} — None means
    "not attempted" (already installed, configure-only tool, or dry-run)."""
    results: dict[str, dict] = {}
    for tid in ids:
        spec = catalog[tid]
        status = detect_tool(spec)
        entry = {"installed_before": status.installed,
                 "install_ok": None, "configure_ok": None}
        if dry:
            action = "configure" if status.installed is not False else "install + configure"
            on_output(f"{tid}: would {action}")
            results[tid] = entry
            continue
        if status.installed is False and spec.install:
            on_output(f"{tid}: installing...")
            install_result = install_tool(spec, on_output)
            entry["install_ok"] = install_result.ok
            if not install_result.ok:
                on_output(f"{tid}: install failed, skipping configure")
                results[tid] = entry
                continue
        on_output(f"{tid}: configuring...")
        configure_result = configure_tool(spec, [], on_output)
        entry["configure_ok"] = configure_result.ok
        results[tid] = entry
    return results
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -S -m unittest tests.test_context_tools -v`
Expected: all tests PASS (35 total so far: 25 from Tasks 1-3 + 5 in
`TestResolveSelection` + 5 in `TestRunHeadless`).

- [ ] **Step 5: Commit**

```bash
git add tools/context_tools.py tests/test_context_tools.py
git commit -m "feat(context-tools): add resolve_context_tools_selection + headless orchestrator"
```

---

### Task 5: Wire `--context-tools` into `tools/setup.py`

**Files:**
- Modify: `tools/setup.py`
- Test: `tests/test_setup.py`

**Interfaces:**
- Consumes: `context_tools.load_context_tools_inventory`,
  `context_tools.resolve_context_tools_selection`,
  `context_tools.run_context_tools_headless`,
  `context_tools.CONTEXT_TOOLS_INVENTORY_PATH` (Tasks 1-4).
- Produces: `cmd_install(env, tty, dry, examples_flag=None,
  context_tools_flag=None)` (extended signature — the two new params are
  keyword-only-by-convention, appended after the existing `examples_flag`).

- [ ] **Step 1: Write the failing tests**

`cmd_install` will do a lazy `import context_tools` inside its own body
(mirroring `launch_wizard`'s lazy `import wizard_app`) — Python binds a
plain `import` statement inside a function to that function's **local**
scope, not to `setup.context_tools`, so `mock.patch.object(setup,
"context_tools", ...)` cannot work here (there is no such module attribute
to patch). The codebase already solved this exact problem for `wizard_app`:
`tests/test_setup.py`'s `TestLaunchWizardCrash` injects a fake module
directly into `sys.modules["wizard_app"]` before calling the function under
test, so the function's own `import wizard_app` resolves the fake from the
import cache. Mirror that pattern exactly for `context_tools`.

Add a new class to `tests/test_setup.py` (near `TestLaunchWizardCrash` —
`grep -n "class TestLaunchWizardCrash" tests/test_setup.py` to find it):

```python
class TestContextToolsCli(unittest.TestCase):
    """cmd_install does a lazy `import context_tools` inside its own body
    (mirrors launch_wizard's lazy `import wizard_app`) — inject a fake module
    into sys.modules so the function's own import resolves the fake.

    setUp/tearDown save and restore whatever was previously registered at
    sys.modules["context_tools"], rather than unconditionally deleting the
    key. This is NOT optional bookkeeping: cmd_install's own
    `sys.path.insert(0, _tools_dir)` runs unconditionally before its
    `import context_tools`, so once this class's tearDown ran, the REAL
    tools/context_tools.py would become importable for real. If a later
    test in the same process — tests.test_context_tools's own
    TestConfigureTool/TestRunHeadless, which patch
    "context_tools._run_streaming"/"detect_tool"/"install_tool"/
    "configure_tool" by string name — triggered a fresh bare `import
    context_tools` (e.g. via @mock.patch re-importing the target), it would
    get a NEW module object distinct from the `ct` module those tests hold
    (via their own load_module()), so the string-patches would patch the
    wrong object and the REAL functions would run — a real subprocess/
    network call, violating this plan's Global Constraint. Saving+restoring
    whatever was there before (usually None, but the fix must not assume
    that) keeps sys.modules exactly as this class found it."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.install = os.path.join(self.tmp, "ai-kit")
        self.claude = os.path.join(self.tmp, ".claude")
        os.makedirs(os.path.join(self.install, "tools"))
        self.env = {"HOME": self.tmp, "AI_KIT_DIR": self.install,
                    "CLAUDE_CONFIG_DIR": self.claude,
                    "XDG_CONFIG_HOME": os.path.join(self.tmp, ".config")}
        self._prev_context_tools = sys.modules.get("context_tools")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)
        if self._prev_context_tools is None:
            sys.modules.pop("context_tools", None)
        else:
            sys.modules["context_tools"] = self._prev_context_tools

    def _paths(self):
        paths = setup.resolve_paths(self.env)
        os.makedirs(os.path.dirname(paths.config_toml), exist_ok=True)
        with open(paths.config_toml, "w") as f:
            f.write("")
        return paths

    def _fake_context_tools(self):
        mod = mock.MagicMock()
        mod.CONTEXT_TOOLS_INVENTORY_PATH = "/unused"
        return mod

    def test_none_flag_is_a_full_noop(self):
        fake = self._fake_context_tools()
        sys.modules["context_tools"] = fake
        paths = self._paths()
        entries = {cat: [] for cat in setup.CATEGORIES}
        installed = {cat: {} for cat in setup.CATEGORIES}
        with mock.patch.object(setup, "launch_wizard", return_value=None), \
             mock.patch.object(setup, "enumerate_entries", return_value=entries), \
             mock.patch.object(setup, "installed_links", return_value=installed), \
             mock.patch.object(setup, "resolve_paths", return_value=paths), \
             mock.patch.object(setup, "discover_example_segments", return_value=[]):
            setup.cmd_install(self.env, mock.MagicMock(), False,
                              context_tools_flag=None)
        fake.load_context_tools_inventory.assert_not_called()

    def test_flag_present_runs_headless_orchestrator(self):
        fake = self._fake_context_tools()
        fake.load_context_tools_inventory.return_value = {"rtk": object()}
        fake.resolve_context_tools_selection.return_value = ["rtk"]
        fake.run_context_tools_headless.return_value = {"rtk": {}}
        sys.modules["context_tools"] = fake
        paths = self._paths()
        entries = {cat: [] for cat in setup.CATEGORIES}
        installed = {cat: {} for cat in setup.CATEGORIES}
        with mock.patch.object(setup, "launch_wizard", return_value=None), \
             mock.patch.object(setup, "enumerate_entries", return_value=entries), \
             mock.patch.object(setup, "installed_links", return_value=installed), \
             mock.patch.object(setup, "resolve_paths", return_value=paths), \
             mock.patch.object(setup, "discover_example_segments", return_value=[]):
            setup.cmd_install(self.env, mock.MagicMock(), False,
                              context_tools_flag="rtk")
        fake.run_context_tools_headless.assert_called_once()
        call_args = fake.run_context_tools_headless.call_args[0]
        self.assertEqual(call_args[1], ["rtk"])   # ids
        self.assertEqual(call_args[2], False)      # dry

    def test_ids_empty_after_resolution_skips_orchestrator(self):
        fake = self._fake_context_tools()
        fake.load_context_tools_inventory.return_value = {"rtk": object()}
        fake.resolve_context_tools_selection.return_value = []
        sys.modules["context_tools"] = fake
        paths = self._paths()
        entries = {cat: [] for cat in setup.CATEGORIES}
        installed = {cat: {} for cat in setup.CATEGORIES}
        with mock.patch.object(setup, "launch_wizard", return_value=None), \
             mock.patch.object(setup, "enumerate_entries", return_value=entries), \
             mock.patch.object(setup, "installed_links", return_value=installed), \
             mock.patch.object(setup, "resolve_paths", return_value=paths), \
             mock.patch.object(setup, "discover_example_segments", return_value=[]):
            setup.cmd_install(self.env, mock.MagicMock(), False,
                              context_tools_flag="none")
        fake.run_context_tools_headless.assert_not_called()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -S -m unittest tests.test_setup.TestContextToolsCli -v`
Expected: FAIL — `cmd_install` does not accept `context_tools_flag` yet, and
`setup.context_tools` does not exist as a module attribute to patch.

- [ ] **Step 3: Wire it into `tools/setup.py`**

Add the flag to `main()`'s argparse setup (find `parser.add_argument(
"--examples", ...)` around line 2235 and add immediately after it):

```python
    parser.add_argument(
        "--context-tools", default=None, metavar="all|none|<ids>",
        help="AI context tools (rtk/codegraph/grapify/gitnexus) to detect, "
             "install if missing, and configure for whichever agent "
             "environments each tool auto-detects (non-interactive); "
             "comma/space-separated ids, or all/none. Default: skipped "
             "(opt-in only — no wizard step drives this yet).")
```

Update the `cmd_install` dispatch call in `main()` (the `return cmd_install(env,
tty, dry, examples_flag=args.examples)` line) to also pass
`context_tools_flag=args.context_tools`.

Update `cmd_install`'s signature and body. Find:

```python
def cmd_install(env, tty, dry, examples_flag=None):
```

Replace with:

```python
def cmd_install(env, tty, dry, examples_flag=None, context_tools_flag=None):
```

Find the docstring's closing line (`"...keeps existing state."""`) and the
function body's final block (the `examples` handling followed by the
`print(f"summary: ...")` block). Insert a new block AFTER the existing
`examples` handling (the `if result is not None:` block) and BEFORE the
`print(f"summary: ...")` line:

```python
    # AI context tools (rtk/codegraph/grapify/gitnexus) — entirely independent
    # of the status-line wizard's outcome (`result`): this is opt-in headless
    # only via --context-tools; there is no interactive step for it yet.
    if context_tools_flag is not None:
        # Lazy import: context_tools.py is stdlib-only (no textual/rich), but
        # is still imported lazily here to match wizard_app's isolation
        # pattern and keep this module's own import list free of siblings.
        _tools_dir = os.path.dirname(os.path.abspath(__file__))
        if _tools_dir not in sys.path:
            sys.path.insert(0, _tools_dir)
        import context_tools  # pylint: disable=import-outside-toplevel
        catalog = context_tools.load_context_tools_inventory(
            context_tools.CONTEXT_TOOLS_INVENTORY_PATH)
        ids = context_tools.resolve_context_tools_selection(
            context_tools_flag, catalog)
        if ids:
            outcomes = context_tools.run_context_tools_headless(
                catalog, ids, dry,
                lambda line: print(f"context-tools: {line}"))
            for tid, outcome in outcomes.items():
                print(f"context-tools: {tid}: {outcome}")
```

No module-level placeholder is needed: the test's fake module is injected
into `sys.modules["context_tools"]` before `cmd_install` runs, so the
function's own `import context_tools` statement resolves the fake straight
from the import cache — the exact mechanism already proven by
`TestLaunchWizardCrash`'s `sys.modules["wizard_app"] = fake_mod` for
`launch_wizard`'s lazy `import wizard_app`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -S -m unittest tests.test_setup.TestContextToolsCli -v`
Expected: all 3 tests PASS.

- [ ] **Step 5: Run the full existing test_setup.py suite to check no regressions**

Run: `python3 -S -m unittest tests.test_setup -v 2>&1 | tail -30`
Expected: all tests PASS, no new failures.

- [ ] **Step 6: Verify the sys.modules save/restore fix with the exact ordering that would have exposed the bug**

Run: `python3 -S -m unittest tests.test_setup tests.test_context_tools -v 2>&1 | tail -60`
Expected: all tests PASS, in this exact module order (`tests.test_setup`
before `tests.test_context_tools` — the same relative order the Makefile's
`test` target and Task 6 Step 3 use). This ordering matters: without the
setUp/tearDown fix in Step 1, `TestContextToolsCli` running and tearing
down first would leave a real, importable `tools/context_tools.py` on
`sys.path` (from `cmd_install`'s unconditional `sys.path.insert`), and the
later `tests.test_context_tools.TestConfigureTool`/`TestRunHeadless`
string-based `@mock.patch("context_tools....")` decorators would then patch
a fresh, wrong module object — silently letting the REAL
`_run_streaming`/`detect_tool`/`install_tool`/`configure_tool` run (a real
subprocess call). With the fix, this run must show all assertions passing
and zero real subprocess/network activity.

- [ ] **Step 7: Commit**

```bash
git add tools/setup.py tests/test_setup.py
git commit -m "feat(context-tools): wire --context-tools headless flag into setup.py"
```

---

### Task 6: Final verification + docs

**Files:**
- Modify: `README.md`
- Modify: `Makefile` (add `tests.test_context_tools` to the `test` target)
- Test: full suite

**Interfaces:**
- Consumes: everything from Tasks 1-5.
- Produces: nothing new — this task only verifies and documents.

- [ ] **Step 1: Add the new test module to `make test`**

Find the `test:` target in `Makefile`:

```
test:
	python3 -m unittest tests.test_setup tests.test_status_line tests.test_external_segments tests.test_statusline_doctor tests.test_arch tests.test_markdown_to_pdf tests.test_worktree_e2e tests.test_wizard_pty tests.test_system_memory_e2e
	bash tests/test_install.sh
```

Add `tests.test_context_tools` to that list (position alphabetically after
`tests.test_arch`, i.e. immediately before `tests.test_markdown_to_pdf`).

- [ ] **Step 2: Document the new flag in `README.md`**

Find the section documenting `--examples` (search `grep -n "\-\-examples"
README.md`) and add a short paragraph immediately after it:

```markdown
### Context tools (rtk / codegraph / grapify / gitnexus)

A small family of AI-agent "code intelligence" tools — rtk (token-compressing
CLI proxy), codegraph, grapify, and gitnexus (all three index a codebase into
a knowledge graph for coding agents) — can be detected, installed, and
configured non-interactively via `--context-tools=all|none|<ids>` on
`tools/setup.py`. ai-kit never reimplements any of these tools' own
agent-wiring logic; it only shells out to each tool's own install/setup
command (`rtk init -g`, `codegraph install`, `graphify install`,
`gitnexus setup`). There is currently no interactive wizard step for this —
it is a headless-only capability until a follow-on plan adds one.
```

- [ ] **Step 3: Run the full test suite**

Run: `python3 -S -m unittest tests.test_setup tests.test_status_line tests.test_external_segments tests.test_statusline_doctor tests.test_arch tests.test_context_tools tests.test_markdown_to_pdf -v 2>&1 | tail -40`
Expected: all PASS, 0 failures.

- [ ] **Step 4: Run the full lint/type/format gate**

Run: `uv run pre-commit run --all-files`
Expected: every hook (ruff, pylint, pyright, vulture, shellcheck, py-compile,
unittest core, unittest wizard) reports Passed.

- [ ] **Step 5: Commit**

```bash
git add README.md Makefile
git commit -m "docs(context-tools): document --context-tools headless flag; wire into make test"
```

---

## Follow-on (Plan 2 — not part of this plan)

Once this module's API (`ToolSpec`/`ToolStatus`/`CommandResult`,
`detect_tool`/`install_tool`/`configure_tool`/`run_context_tools_headless`) has
shipped and is stable, a second plan adds the interactive wizard Step 0
screen (`tools/wizard_app.py`): one row per catalog tool with an Install/
Configure/Skip action menu, an env chip-picker for scoping-capable tools, and
a background-worker execution path mirroring the existing `_run_commit`
pattern. That plan also adds the `--skip-context-tools` headless flag (which
only makes sense once there is an interactive step to skip).
