# Phase 21: Cursor Live Validation - Context

**Gathered:** 2026-10-14 (assumptions mode, `--analyze --all --batch`, jev screening, best over easy)
**Status:** Ready for planning (AGT-01 planning waits on the D-01 spike)

<domain>
## Phase Boundary

The v2 curated-config is validated from the user's interactive cursor session. cursor is detected
behind the shell wrapper, and ai-kit ships two pinned non-fast Cursor subagents linked by
`tools/setup.py`. The WHAT is locked in `21-SPEC.md` (R1–R8). This file locks the HOW.
</domain>

<decisions>
## Implementation Decisions

### Premise check
- **D-01: A wave-0 spike runs before any R6/R7 code is planned.**
  - Static reading of the 2026.10.01 bundle shows the CLI's subagent loader
    (`Vs.computeAgentsDirs()`, `index.js:414`) scanning only workspace-relative `.cursor/agents`,
    `.claude/agents` and `.grok/agents`. The workspace roots come from `workspacePaths`,
    `--add-dir` or the cwd, never `homedir()`.
  - The 2026-10-13 live test used a project-level folder. Cursor's own docs (create-subagent
    skill) list `~/.cursor/agents` as user scope, which may describe the IDE only.
  - Spike: run `cursor-agent -p --model <non-fast id>` from a scratch workspace, with a scratch
    `HOME` holding a symlinked `.cursor/agents/composer-worker.md`. `auth.json` is symlinked
    into the scratch `~/.config/cursor/`, and its values are never read. Nothing is written
    under the real `~/.cursor`.
  - If the CLI ignores user-level agents, the target becomes project-level `.cursor/agents`
    through a decimal phase, with SPEC R6/R7, ROADMAP SC4 and AGT-01 amended formally.
  - TypeSafe spike_first 1.00.
  - Also from the bundle: duplicate names resolve first-wins per root (`.cursor`, then
    `.claude`, then `.grok`, then plugins), and plugin agents drop their `model` (`stripModel`).
    A symlinked file is followed wherever it points; a symlinked directory outside the
    workspace is skipped. So ai-kit links per file, never a directory.

### Setup category (R6)
- **D-02: `"cursor-agents"` is the fourth entry of `CATEGORIES`.**
  - One destination helper replaces the nine `claude_dir/cat/name` joins. `cursor_dir` is
    threaded as a trailing `cursor_dir=None` keyword, and `None` makes the category inert.
  - The existing `link_one`/`unlink_one`, stale-prune, predecessor-repoint and uninstall paths
    then cover it. `validate_entry` gains a `cursor-agents` branch: frontmatter present and a
    non-empty body.
  - The Cursor gate is set once where `entries` is built (`cmd_install`,
    `_headless_paths_and_entries`): `entries["cursor-agents"] = []` unless `paths.cursor_dir`
    exists, the same test as the hook wiring.
  - `tests/test_setup.py:870`'s `CATEGORIES` pin is updated.
  - TypeSafe 1.00.
- **D-03: The wizard's Review summary names the real destinations** (`wizard_app.py:600-608`).
  It is the consent surface for writes under `~/.cursor`.
- **D-04: The plan1 hedge is additive and disjoint.**
  - New logic goes in new helpers: `_headless_link_cursor_agents`, the destination helper and
    `resolve_cursor_agents_flag`.
  - New parameters are trailing keywords with defaults.
  - New tests go in a new module: plan1 appends about 350 lines to `test_setup.py`, so either
    land-or-shelve outcome would conflict there.
  - Only the argparse, `main()` guard and wizard call-line hunks can conflict, and those are
    mechanical.
  - **Laya overridden** (append 0.98): TypeSafe second opinion new_module 0.99.
- **D-05: An unknown name in `--cursor-agents` exits 1 and names it** (the SPEC edge). This
  differs deliberately from `--skills` (warn, exit 0), and the asymmetry is documented.
  `cmd_install_headless` is at 13 of 15 locals, so the logic goes into
  `_headless_link_cursor_agents`. Laya 0.72.

### Subagent files (R5, R7)
- **D-06: The frontmatter test ports the bundle's own line parser** (`Hs`, `index.js:414`), not
  YAML:
  - a `^---\s*\n…\n---` block is required;
  - lines split at the first `:`, keys are lowercased and values raw-trimmed (quotes and
    comments stay);
  - only `name`, `description`, `model`, `force-default-model`, `readonly`,
    `background`/`is_background` and `tools` are read;
  - an empty body drops the file silently;
  - `model` is unvalidated client-side.

  So the shipped files use unquoted single-line scalars.
- **D-07: Name-collision test.** The static rule is: not `gsd-*`, and the name equals the
  filename stem. An optional live cross-check against `gsd_catalog.query_agent_catalog` runs
  `skipUnless` node and gsd-core are present. Real `~/.claude/agents` is never read.
- **D-08: Non-fast pins.** The test asserts each pinned id is in the captured `models` fixture
  and does not end in `-fast`. The R7 live proof runs each agent once under a scratch
  `CURSOR_CONFIG_DIR` with no `modelParameters`, because the user's real config stores
  `composer-2.5: fast=false` and would mask a config dependence. The dashboard check is on
  `composer-worker`. TypeSafe 0.99.

### Detection (R4)
- **D-09: The resolver works over 18.1's `RUNTIMES["cursor"].binaries`.**
  - `cursor-agent` is accepted as found.
  - `agent` is accepted only when some PATH entry's realpath basename is `cursor-agent`,
    scanning every PATH entry, not just the first hit. On this machine `~/.grok/bin/agent`
    resolves to grok.
  - Two names resolving to one real file are reported once.
  - `runtimes.json` records `real_path` next to `path`, and enumeration runs the PATH hit, which
    survives Cursor updates.
  - Tests use real temp-dir symlinks with `functools.partial(shutil.which, path=tmpbin)`, and
    "no shell" is asserted through the injected `run_fn`.
  - Own reasoning; both models were low (Laya first_hit 0.40 fb, TypeSafe scan_all_path
    0.68 fb). Provisional, so it is on the ledger.
- **D-10: The `models` parser splits into a pure `parse_cursor_models(stdout)` and a thin
  `detect_cursor_models`**, like codex.
  - It is token-based, not `" - "`-based: a nameless model such as `auto (current, default)`
    is kept, and ANSI codes are stripped.
  - Output is gated on returncode 0.
  - The fixture `tests/fixtures/cursor_models.txt` is captured from an authed session (a
    read-only, no-model call). The unauthenticated `Authentication required` exit 1 is the
    failure fixture.

### Claude's Discretion
- The helper names; the agent bodies' wording (short, for already-planned tasks).
</decisions>

<canonical_refs>
## Canonical References

- `.planning/phases/21-cursor-live-validation/21-SPEC.md`
- `.planning/todos/pending/2026-10-13-add-cursor-subagents-pinned-to-non-fast-composer-2-5-and-grok.md`
- `.planning/phases/18.1-one-runtime-model/18.1-CONTEXT.md` D-01, D-02 (runtime table, realpath rule)
- `tools/setup.py` (`CATEGORIES`, `link_one:1030-1063`, joins at `850,1077,1090,1131,1156,1360,1364,2921-2923`), `tools/wizard_app.py:483-497,600-608`
- `skills/ai-kit-spec-review/ai_kit_spec/detection.py:123-141` (current cursor enumeration)
- `skills/ai-kit-spec-review/references/cli-profiles/cursor-agent.md:13-20`
- Bundle (read-only): `~/.local/share/cursor-agent/versions/2026.10.01-e373342/index.js:414`, `6436.index.js` (models formatter), `1623.index.js`
</canonical_refs>

<code_context>
## Existing Code Insights

- `Paths.cursor_dir` already exists (`setup.py:60,75`); `_default_selection:1224-1236` defaults new categories OFF on existing installs.
- `parse_codex_debug_models:144` / `detect_codex_models:201` is the parser split precedent; `CODEX_FIXTURE_PATH` loading at `tests/test_ai_kit_spec.py:110-122`.
- `commands.py:335-352` builds `base[fast=false]` ids for `--model` (not verified for frontmatter).
</code_context>

<specifics>
## Specific Ideas

- ~~**Precondition owned by uz:** land or shelve `worktree-context-tools-manager-plan1` before AGT-01 planning.~~ *(resolved 2026-10-14: it does not land in ai-kit; D-04's disjoint layout stays, as it costs nothing.)*
- Open for research: server-side validation of an invalid frontmatter `model` (error or silent inherit), and whether `grok-4.7-medium` is subagent-eligible on other accounts.
- R1–R3 (smoke, matrix, label) reuse Phases 19/20's helper and oracle unchanged.
</specifics>

<deferred>
## Deferred Ideas

- Overriding Cursor's built-in explore subagent model (a user `cli-config.json` setting) — out of scope per SPEC.
</deferred>

---

*Phase: 21-cursor-live-validation*
*Context gathered: 2026-10-14*
