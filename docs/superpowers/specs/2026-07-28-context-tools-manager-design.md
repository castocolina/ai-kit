# Context Tools Manager (Design Spec)

- **Status**: design ready
- **Date**: 2026-07-28
- **Relates to**: E5 (installer wizard) — extends the existing `tools/setup.py` /
  `tools/wizard_app.py` Textual flow with a new step; does not touch status-line
  rendering (`tools/status-line.py`) at all.

---

## 1. Intent

ai-kit's install wizard currently configures exactly one thing: the status line.
Separately, a family of AI-agent "code intelligence" tools has emerged —
**rtk**, **codegraph**, **grapify**, **gitnexus** — each of which indexes a
codebase or compresses tool output so a coding agent (Claude Code, OpenCode,
Codex, Cursor, Antigravity, VS Code Copilot, …) gets better context. Each tool
already ships its own install script and its own agent-wiring/setup command
(MCP registration, hooks, skill files, `AGENTS.md`/`CLAUDE.md` injection).
ai-kit does not reimplement any of that logic — it adds a **Step 0** to the
existing wizard that detects whether each tool is present, and if so, lets the
user trigger that tool's own setup command, scoped to whichever agent
environments it supports selecting.

**Out of scope**: ai-kit does not verify that a wire-up actually took effect
inside another tool's config (e.g. it cannot introspect Cursor's MCP config to
confirm codegraph registered correctly) — it trusts each tool's own exit code.
ai-kit does not manage updates/versioning of these tools beyond re-running
their install command. ai-kit does not add its own MCP server or agent skill —
it is strictly an orchestrator/menu over commands that already exist.

---

## 2. Two independent actions per tool

Every catalog entry supports up to two actions, offered independently:

- **Install** — get the tool onto disk. Only offered when detection says
  "not found." Uses `pnpm`/`uv tool install`/vendor curl scripts, never `npm`
  (per explicit preference — `pnpm add -g <pkg>` / `pnpm dlx <pkg>@latest ...`
  wherever the tool's docs offer an npm-based path).
- **Configure** — run the tool's own agent-wiring command. Offered whenever
  the tool is present (whether just installed this run, or pre-existing).
  This is the common case: most users already have some of these tools
  installed and only need the wiring step.

| Tool | Install | Configure | Env scoping |
|---|---|---|---|
| rtk | curl install script | `rtk init -g` | none — Claude Code only, no flag |
| codegraph | `pnpm add -g @colbymchenry/codegraph` (or vendor install.sh) | `codegraph install` | none — auto-detects all agents present |
| grapify | `uv tool install graphifyy` | `graphify install --platform <env>` (repeatable) or `graphify install` for all | yes — per-env flag |
| gitnexus | n/a (no persistent global install; always invoked via `pnpm dlx`) | `pnpm dlx gitnexus@latest setup -c <env,env,...>` or `setup` for all | yes — `-c` takes a comma list |

For tools without scoping, the wizard skips the environment chip-picker
entirely and just runs the tool's full auto-detect configure command.

---

## 3. Catalog (`tools/context_tools_inventory.toml`)

A new inventory file, structurally parallel to `segments_inventory.toml`, is
the single source of truth — no tool-specific logic lives in Python:

```toml
[rtk]
name = "rtk"
description = "CLI proxy that compresses shell output before it reaches the agent (60-90% token savings)"
detect = "rtk --version"
install = "curl -fsSL https://raw.githubusercontent.com/rtk-ai/rtk/master/install.sh | sh"
configure = "rtk init -g"
supports_env_scoping = false

[codegraph]
name = "codegraph"
description = "Pre-indexed code knowledge graph; auto-syncs on file changes"
detect = "codegraph --version"
install = "pnpm add -g @colbymchenry/codegraph"
configure = "codegraph install"
supports_env_scoping = false

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
detect = ""                         # no persistent global binary — always offered as "configure only"
install = ""
configure = "pnpm dlx gitnexus@latest setup"
configure_scoped = "pnpm dlx gitnexus@latest setup -c {envs}"
supports_env_scoping = true
envs = ["claude_code", "codex", "cursor", "antigravity", "opencode", "windsurf"]
```

`envs` ids map to a small fixed label table shared across tools (`claude_code`
-> "Claude Code", `opencode` -> "OpenCode", etc.) so the chip picker shows
consistent labels even though each tool's own flag vocabulary differs
slightly (`gitnexus -c cursor,codex` vs `graphify --platform codex`).

A tool with an empty `detect` (gitnexus) is always shown as "configure only" —
there is nothing to detect since it has no persistent install step.

---

## 4. Module (`tools/context_tools.py`)

Three functions, each a thin subprocess wrapper reading from the catalog —
no per-tool branching in Python:

```python
def detect_tool(spec: ToolSpec) -> ToolStatus:
    """Runs spec.detect (if any) with a short timeout. Returns
    ToolStatus(installed: bool, version: str | None). Empty detect ->
    always "configure only" (installed=None, distinct from False)."""

def install_tool(spec: ToolSpec, on_output: Callable[[str], None]) -> CommandResult:
    """Runs spec.install, streaming each output line to on_output (feeds the
    wizard's live log panel). Returns CommandResult(ok: bool, log: str)."""

def configure_tool(spec: ToolSpec, envs: list[str],
                    on_output: Callable[[str], None]) -> CommandResult:
    """envs empty or scoping unsupported -> runs spec.configure (full
    auto-detect). Otherwise formats spec.configure_scoped with the chosen
    env ids (comma-joined or repeated --platform flags per tool's own
    template) and runs that."""
```

`ToolSpec`/`ToolStatus`/`CommandResult` are plain `NamedTuple`s, matching the
existing `ExtSpec` pattern in `status-line.py`. `load_context_tools_inventory`
mirrors `load_segment_inventory` in `setup.py` (same TOML-parsing helper,
same missing-file -> `{}` fallback).

---

## 5. Wizard integration

A new `STEP_TOOLS` screen (Step 1 of 4, before today's Choose/Arrange/Review)
reusing the existing `WizardApp`/Textual shell:

- One row per catalog tool: icon, name, and a status chip — `installed`,
  `not found`, or `configure only` (gitnexus-style, no detect command).
- Focus + Enter on a tool opens an inline action menu: **Install** (hidden
  if already installed), **Configure** (opens the env chip-picker only if
  `supports_env_scoping`; otherwise runs the full auto-detect configure
  immediately), **Skip this tool**.
- `s` at the screen level skips Step 0 entirely (falls straight into today's
  Choose step) — this whole feature is opt-in per run, never forced.
- Selected actions across all tools queue up; Enter on the screen's footer
  CTA starts execution.

## 6. Execution model

All queued actions run in a background worker thread — the exact pattern
`_run_commit` already uses for the real status-line install (`@work(thread=True,
exclusive=True)`, `call_from_thread` back to the UI). A per-tool log line
streams into a scrollable panel: `Installing rtk...`, `rtk: done`,
`Configuring grapify for Claude Code, Cursor...`, `grapify: done`. A
non-zero exit is caught, logged as `⚠ <tool> failed: <last log line>`, and
does **not** block the remaining queued actions or the rest of the wizard —
consistent with the never-blank philosophy already used for status-line
segment builders (`core_safe_build`). ai-kit trusts each tool's exit code as
final; it never re-probes to confirm the wiring took effect (per your
"good" on that question) — that confirmation is each tool's own
responsibility (e.g. its own doctor/status command, out of scope here).

Headless/non-interactive parity with the existing `--examples` flag:
`--context-tools=rtk,grapify` runs install+full-auto-detect-configure for
just those ids with no TUI; `--skip-context-tools` bypasses Step 0's
detection probes entirely (useful in CI where even the lightweight `--version`
probes are unwanted). Omitting both flags in a headless run defaults to
skipping the step (same "wizard-only" opt-in default as interactive mode).

## 7. Testing

- `tests/test_context_tools.py` (plain `unittest`, no Textual needed):
  catalog parsing (missing file, malformed TOML, missing required keys),
  `detect_tool`/`install_tool`/`configure_tool` against a **mocked**
  subprocess (never a real network call in CI), the scoped-vs-unscoped
  configure command templating (comma-join vs repeated flag, per tool).
- `tests/test_wizard_app.py` additions (Textual, `uv run`-gated): Step 0
  screen renders one row per catalog tool, action menu hides Install when
  already-installed, env chip-picker only appears for scoping-capable
  tools, `s` skips straight to Choose, and the background-worker execution
  path is exercised via an injected fake runner (mirrors the existing
  `ctx.commit` fixture injection — no real subprocess in tests).
