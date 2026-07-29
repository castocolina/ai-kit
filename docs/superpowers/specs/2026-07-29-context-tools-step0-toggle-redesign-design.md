# Context Tools Manager — Step 0 Toggle Redesign & Removal Support (Design Spec)

- **Status**: design ready
- **Date**: 2026-07-29
- **Relates to**: supersedes §5 ("Wizard integration") of
  `2026-07-28-context-tools-manager-design.md` and the Step 0 implementation
  built from it (`docs/superpowers/plans/2026-07-28-context-tools-manager-plan2-wizard.md`,
  branch `worktree-context-tools-manager-plan1`). Everything else from the
  original spec (catalog structure, `detect_tool`/`install_tool`/`configure_tool`,
  shell-execution requirement, headless `--context-tools=`/`--skip-context-tools`
  flags) is unchanged and still binding.

---

## 1. Why this redesign

The shipped Step 0 (menu → Install/Configure/Skip → optional env chip-picker)
was built to generalize over per-tool env-scoping differences, but hands-on
use surfaced three real problems:

1. **Extra indirection for the common case.** Selecting a tool always
   requires opening a submenu and choosing among options, when for almost
   every tool the intent is simply "get this working" — install if needed,
   configure, done.
2. **Footer inconsistency.** Every other wizard step (`Choose` in
   particular) uses a direct `Space`-to-toggle model with a footer reading
   `Continue (Enter) · Toggle (Space) · …`. Step 0's list-mode footer had no
   `Toggle` at all (`Open (Enter) · Move (↑↓) · Skip step (s)`), which reads
   as inconsistent/backwards once you've used Choose.
3. **No removal path.** The wizard could install/configure a tool but never
   uninstall one. Trying several of these tools and cleanly switching away
   from ones that don't pan out required manual cleanup outside the wizard.

This spec replaces the menu/env-picker interaction with a direct 4-state
toggle per tool, removes the per-run env picker in favor of a fixed default
environment set, and adds a catalog-level `uninstall` capability researched
against each tool's actual documented removal command.

---

## 2. Interaction model: fixed 4-state toggle

Each tool row cycles through exactly the same four states on `Space`,
regardless of that tool's detected status — no adaptive skipping:

```
Keep-as-is → Install/Reinstall + Configure → Reconfigure → Remove → Keep-as-is → …
```

- **Keep-as-is** (default/starting state for every row, every run): nothing
  queued for this tool.
- **Install/Reinstall + Configure**: runs `install_tool` then `configure_tool`
  unconditionally — even when the tool is already `installed`. This is a
  deliberate divergence from the headless `run_context_tools_headless`
  behavior (which skips `install` when already present): the wizard's
  version is an explicit "reinstall" the user asked for, not an
  optimization to preserve.
- **Reconfigure**: runs `configure_tool` only. If the tool's detected status
  is `not_found`, this is a **no-op**: log `skipped: <tool> not installed`,
  do not run any command, do not fail the queue.
- **Remove**: runs the tool's new `uninstall` command (§5). If the tool's
  detected status is `not_found`, this is also a no-op: log
  `skipped: <tool> not installed, nothing to remove`.

Cycling past `Remove` returns to `Keep-as-is` (clears the queued entry for
that tool). The row's chip shows the queued action name exactly as today
(`→ reconfigure`, `→ remove`, etc.), just driven by cycle position instead
of a chosen menu item.

This replaces `_key_tools_menu`, `_key_tools_envpick`, `_choose_tools_menu_option`,
and `_tools_menu_options` entirely — `tools_mode` no longer has `"menu"`/
`"envpick"` values, only `"list"`. `tools_queue[row["id"]]` becomes
`{"action": <one of "install_configure"|"reconfigure"|"remove">}` (the
`"envs"` key is dropped from the queue entry — see §4).

### Footer/help

Step 0's list-mode footer becomes structurally identical to Choose's:

```
Continue (Enter) · Toggle (Space) · Move (↑↓) · Help (?)
```

(`FOOTERS[STEP_TOOLS]` in `tools/wizard_app.py` changes from
`[("Open", "Enter", True), ("Move", "↑↓", False), ("Skip step", "s", False), ("Help", "?", False)]`
to
`[("Continue", "Enter", True), ("Toggle", "Space", False), ("Move", "↑↓", False), ("Skip step", "s", False), ("Help", "?", False)]`.)
`HELP[STEP_TOOLS]` gets a matching `("Space", "Cycle the highlighted tool through keep-as-is / install+configure / reconfigure / remove")` entry, and the existing `Enter` help line changes from "Open the action menu…" to "Run queued actions from the Continue row". Whether Enter on a tool row (not the Continue row) becomes fully unbound or does something else is open — see §7, question 4.

---

## 3. Execution semantics (worker + no-op handling)

`_run_tools` (the `@work(thread=True, exclusive=True)` worker) keeps its
existing shape: iterate `tools_queue`, dispatch each action, stream output
through `on_output`/`_tools_log`, and — per the fix already shipped in Plan 2
— only auto-advance to `STEP_CHOOSE` when every queued action reports
`ok: True`; stay on `STEP_TOOLS` otherwise so failures remain visible. The
per-action dispatch table changes from `{"install", "configure"}` to
`{"install_configure", "reconfigure", "remove"}`:

- `install_configure` → `install_tool(spec, on_output)`; if that fails, log
  and stop (do not attempt configure) — same short-circuit
  `install`-fails-skip-`configure` behavior `run_context_tools_headless`
  already uses. If it succeeds (or the tool has no `install` command, e.g.
  gitnexus), proceed to `configure_tool(spec, envs, on_output)` using the
  intersected env set from §4.
- `reconfigure` → no-op if `not_found` (per §2); otherwise
  `configure_tool(spec, envs, on_output)`.
- `remove` → no-op if `not_found`; otherwise runs the new `uninstall_tool`
  (§5) — a single opaque shell command/script, same execution contract as
  `install_tool`/`configure_tool` (streamed output, `CommandResult`).

A no-op is reported as `ok: True` with a log line explaining the skip — it
must never register as a failure that blocks auto-advance, since "nothing to
do" is a valid, successful outcome of choosing Remove/Reconfigure on an
absent tool.

---

## 4. Fixed default environment set (no per-run picker)

The env chip-picker (`_key_tools_envpick`, `_render_tools`'s `envpick` branch,
`tools_env_selected`) is removed. Every `configure`/`reconfigure` action
against a tool with `supports_env_scoping = true` targets a fixed default
set instead of a user-chosen one:

```
DEFAULT_TOOLS_ENVS = ("opencode", "claude_code", "antigravity", "vscode", "codex")
```

**Per-tool intersection rule**: the actual envs passed to `configure_tool`
are `[e for e in DEFAULT_TOOLS_ENVS if e in spec.envs]` — envs the default
set names that a given tool's catalog entry does not support are silently
dropped, never passed through and never surfaced as an error. Concretely,
today's catalog:

- **grapify** (`envs = [claude_code, cursor, codex, gemini_cli, vscode, antigravity, opencode, aider]`)
  → gets all 5 of the default set (all are in its supported list).
- **gitnexus** (`envs = [claude_code, codex, cursor, antigravity, opencode, windsurf]`)
  → gets 4 of the 5 (**`vscode` is dropped** — gitnexus's catalog entry does
  not list it as a supported env).
- **rtk**, **codegraph** (`supports_env_scoping = false`) → the default set
  is irrelevant; `configure_tool` runs the full auto-detect `configure`
  command exactly as it does today.

**Display**: a static line under the tool list shows the default set, with
`OpenCode` and `Claude Code` visually prioritized (bold/first), e.g.:

```
Configuring for: OpenCode, Claude Code, Antigravity, VS Code, Codex
```

This is informational only — not interactive, not per-tool-editable in this
design. `tests/wizard_fixtures.py`'s `make_ctx(with_context_tools=True, ...)`
drops its env-picker-specific synthetic setup accordingly.

---

## 5. Catalog schema: `uninstall`

One new field per catalog entry, matching the existing "opaque shell command
string, executed via `shell=True`" contract that `install`/`configure`
already use (see `2026-07-28-context-tools-manager-design.md` §2/§4's
execution requirement — unchanged, restated here as binding on `uninstall`
too):

```toml
uninstall = "<shell command, or a path to a script under tools/context_tools_scripts/>"
```

**Convention**: if a tool's full teardown (agent-wiring removal + binary/
package removal + any per-repo cleanup) fits in one line — plain command or
an `&&`-chain, the same style `configure_scoped` already uses — inline it
directly in the TOML. If it needs real branching or more than ~3 logical
steps, author it as a small script under a new `tools/context_tools_scripts/`
directory and reference it by relative path, e.g.
`uninstall = "bash tools/context_tools_scripts/rtk.sh"`.

**Path resolution**: script paths in `uninstall` must resolve relative to
the `tools/` directory (where `context_tools_inventory.toml` itself lives),
not the caller's CWD — mirroring how `CONTEXT_TOOLS_INVENTORY_PATH` is
already computed via `os.path.dirname(os.path.abspath(__file__))` in
`tools/context_tools.py`. A small loader-time helper resolves any `uninstall`
value that looks like a bare script path (starts with `bash ` or
`tools/context_tools_scripts/`) against that directory before it's ever
handed to `subprocess.Popen(..., shell=True)`; a plain inline one-liner
passes through unchanged.

`uninstall_tool(spec: ToolSpec, on_output: Callable[[str], None]) -> CommandResult`
is added to `tools/context_tools.py`, structurally identical to
`install_tool` (same "no command in catalog → immediate `ok=False`" guard,
same `_run_streaming` call).

### 5.1 Per-tool commands (researched — see confidence notes)

| Tool | `uninstall` (proposed) | Confidence |
|---|---|---|
| **rtk** | Script (`tools/context_tools_scripts/rtk.sh`) — needs to run `rtk init -g --uninstall` scoped per previously-configured agent, then `rm -f` the curl-installed binary (default `$HOME/.local/bin/rtk`, overridable via `RTK_INSTALL_DIR`). Not a one-liner: agent scoping and the binary path both need real logic. | **High** — `--uninstall` flag verified directly against this machine's installed `rtk init --help` output (*"Remove RTK artifacts for the selected assistant mode"*). Known caveat: rtk-ai/rtk issue #1014 reports the flag can leave some data-directory artifacts behind in some cases — not total cleanup; the script should not claim otherwise in its output. |
| **codegraph** | `codegraph uninstall --yes && pnpm remove -g @colbymchenry/codegraph` | **High** — `codegraph uninstall` is documented (`--target <agent>`, `--yes`) as stripping MCP config, instructions, and permissions per agent; project-local `.codegraph/` index is intentionally left alone by this command (would need a separate `codegraph uninit`, out of scope for the global Remove action). |
| **grapify** | `graphify uninstall --purge` | **Medium** — sourced from the GitHub repo page only; the primary docs site (`graphify.net`/`graphify.com`) 403'd/404'd on fetch, so this could not be cross-verified against a second source. **Verify against a real `graphify --help` / `graphify uninstall --help` before this ships in the TOML.** |
| **gitnexus** | `pnpm dlx gitnexus@latest uninstall --force` | **Medium** — sourced via a WebFetch summarization pass over the README rather than a raw read or `--help` output. **Verify the exact flag names before this ships in the TOML.** Per-repo `.gitnexus/` index cleanup (`gitnexus clean --all --force`) is a separate, project-scoped concern — not part of the global Remove action modeled here (same reasoning as codegraph's `.codegraph/` index). |

The Medium-confidence rows are called out explicitly in §6's open questions —
this spec's *mechanism* (schema field, script convention, path resolution,
no-op semantics) does not depend on the exact command text being final.

---

## 6. Testing impact

- `tests/wizard_fixtures.py`: `make_ctx`'s `with_context_tools=True` path
  drops env-picker-specific setup; synthetic rows stay (installed/not_found/
  configure_only variety), no fixture change needed for the intersection
  rule itself (that's exercised via `context_tools.py`-level tests instead).
- `tests/test_wizard_app.py`'s `TestToolsStep` class (~20 tests) needs a
  substantial rewrite: every test that drives the old
  menu → choose-option → envpick flow is replaced with tests driving
  `Space` cycling and asserting the resulting `tools_queue` entry and
  rendered chip. New tests: no-op logging for `reconfigure`/`remove` on a
  `not_found` tool, queue-clearing on cycling back to `Keep-as-is`.
- `tests/test_context_tools.py`-equivalent (backend): `uninstall_tool` gets
  the same mocked-subprocess test treatment as `install_tool`/`configure_tool`
  (no real network/filesystem calls in CI); a test for the loader-time
  script-path-resolution helper (bare script path vs inline one-liner).
- `tests/test_wizard_pty.py`: unaffected — these already pass
  `--skip-context-tools` (per the Plan 2 fix wave) and never exercise Step 0
  directly.

---

## 7. Open Questions for User Review

1. **grapify/gitnexus `uninstall` commands are Medium-confidence** (§5.1) —
   sourced from docs that couldn't be fully cross-verified. Recommend a
   local spot-check (`graphify --help`, and installing gitnexus once via
   `pnpm dlx gitnexus@latest --help`) before the implementation plan
   hardcodes these into the TOML.
2. **rtk's uninstall needs a real script**, not just a one-liner — is a
   single `tools/context_tools_scripts/rtk.sh` covering all agents rtk might
   have been configured for (looping `--agent` values) acceptable, or should
   it only target whichever agent(s) the wizard itself configured this
   session (would require tracking that state across runs, which nothing
   today persists)?
3. **rtk's known-incomplete cleanup** (GH #1014) — should the Remove log
   output say something like "rtk's own uninstall may leave some data-dir
   artifacts behind" so the user isn't surprised, or is silent best-effort
   fine?
4. **Enter on a tool row**: with the menu gone, is Enter on a tool row (not
   the Continue row) simply unbound/a no-op, or should it do something (e.g.
   act as an alternate way to advance one cycle step, same as Space)?
5. **`.codegraph/`/`.gitnexus/` per-repo index cleanup** is explicitly
   out of scope for the global Remove action (§5.1) — confirm that's
   acceptable, since a user removing codegraph/gitnexus this way would
   still have a per-project index directory left behind.
