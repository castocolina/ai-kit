# Design: installer registry — ordering, audience, severity, enable/disable

- Date: 2026-06-07
- Project: uz-kit installer (`tools/installer/`, `tools/setup.py`)
- Status: approved (design); next step is an implementation plan
- Supersedes: none. Follows the declarative `[[tool]]` registry rewrite (commit `98e513f`).

## Problem

After the declarative-registry rewrite, the setup wizard regressed in four ways:

1. **Priority disappeared from the list and nothing is sorted.** `priority` (P0–P3)
   still exists on every `[[tool]]` row, but `setup.py` renders `Tool / Category /
   Status / Notes` in raw `registry.toml` file order with no Priority column and no
   sort. The list reads as unordered.
2. **No per-tool explanation of what each tool does, and for whom.** The "for a human
   vs for an AI agent" rationale exists only as prose in `docs/ia-helper-tools.md`; it
   is not structured data, so the wizard cannot surface it.
3. **GSD nags forever.** In `engine.py`, any `launcher` with `cmd == "npx"` returns
   `"unknown"` unconditionally, so GSD (invoked via `npx`) can never report
   "installed" and is permanently dumped into the loud "ACTIONS NEEDED" panel — even
   when it is installed, wired, and current. There is no severity gradient: "must
   install" and "an update exists" look identical.
4. **No way to disable a tool.** There is no `enabled` flag; turning off a tool (e.g.
   `pi`) means deleting its row.

## Decisions (locked with the user)

| # | Decision |
|---|---|
| 1 | Sort the list by **priority P0→P3, then category A→Z, then tool name A→Z**. Restore a `Pri` column. |
| 2 | "Classifier" = **audience**: who the tool serves — `ai` / `human` / `both` — shown as a `For` column. |
| 3 | **Six-state status model** with four severity levels + pin + disabled (table below). |
| 4 | GSD / npx launchers detect status from the **state file the tool already writes**, not via `npx`. |
| 5 | Per-tool **one-line `desc` + `audience` tag** in the registry; full rationale stays in `docs/ia-helper-tools.md`. |
| 6 | Add an **`enabled`** flag (default `true`). Disabled = dim, visible, excluded from install/actions. |
| 7 | Disabled tool that is a hard dependency of an enabled tool → **dependency wins** (dragged in with a warning). |
| 8 | Add a **`pin`** field: when set, suppress the update nag for that tool. |

## Schema additions to `[[tool]]`

Added to the `Tool` dataclass (`model.py`) and the loader, all optional/back-compatible:

| Field | Type | Default | Purpose |
|---|---|---|---|
| `enabled` | bool | `true` | `false` → dim row, excluded from install/actionable sets |
| `audience` | `"ai"` \| `"human"` \| `"both"` | `"both"` | the `For` column ("classifier") |
| `desc` | str | `""` | one-line "what it does"; shown in the list. `notes` stays an impl detail |
| `pin` | str | `""` | version being held; presence suppresses the `update` state |

New optional `[tool.state]` block (launcher state-file detection, replaces npx guessing):

```toml
[tool.state]
file = "~/.cache/gsd/gsd-update-check-opengsd-gsd-core.json"
installed_key = "installed"      # e.g. "1.3.1"
latest_key = "latest"            # e.g. "1.3.1"
update_key = "update_available"  # e.g. false
```

Loaded into the dataclass as `state_file`, `state_installed_key`, `state_latest_key`,
`state_update_key` (flat fields, consistent with how `[tool.version]` is flattened).

## Status model (`engine.py` — `status()` rewrite)

`status()` returns one canonical state string. Each maps to a severity bucket that
decides where it renders.

| State | Accent | Bucket | Meaning |
|---|---|---|---|
| `missing` | `✗` red | **LOUD** (ACTIONS NEEDED) | not installed |
| `needs_wiring` | `●` yellow | **LOUD** (ACTIONS NEEDED) | installed but unwired (launcher) |
| `alias_needed` | `●` yellow | **LOUD** (ACTIONS NEEDED) | debian alias missing (existing case, folded into LOUD) |
| `update` | `↑` cyan | **CALM** ("Updates available" line) | installed, newer version exists, not pinned |
| `pinned` | `◆` blue | silent | installed, update suppressed by `pin` |
| `current` | `✓` green | silent | installed and up to date |
| `disabled` | `·` dim | silent | `enabled = false` |

Resolution order inside `status()`:

1. `enabled is False` → `disabled` (short-circuit, before any subprocess).
2. `kind == "marketplace"` → `current` if `marketplace_enabled` else `missing`
   (unchanged behaviour, renamed states).
3. `kind == "launcher"` **with `[tool.state]`**: read + parse the JSON state file.
   - file missing / unreadable → fall through to binary/marker checks below;
   - `update_key` truthy and **not** `pin` → `update`;
   - `pin` set → `pinned`;
   - installed value present → `current`.
4. `kind == "launcher"` without `[tool.state]`: existing binary + `wired_marker`
   logic, but the npx `"unknown"` branch is removed — a launcher with neither a binary
   nor a state file → `missing`; binary present but `wired_marker` absent →
   `needs_wiring`; else `current`.
5. Default (`pkg`/`cargo`/`node`/`curl`/`github-release`/`custom`): `check()` →
   `installed` becomes `current`; `alias_needed` preserved; otherwise `missing`.

**GSD result:** with `[tool.state]` pointing at `~/.cache/gsd/...json`
(`update_available: false`), GSD resolves to `current` — silent, never in the alarm
panel. When GSD writes `update_available: true`, it becomes `update` — a calm cyan
line, not a red action.

**Performance contract:** the main wizard does **only cheap local checks** (file
reads, `shutil.which`, `--version`). Network version lookups stay in menu 6
(`Version sync`, the existing `[tool.version]` / `sync()` path). So the `update` state
in the main wizard appears only for tools with a local state cache (e.g. GSD); other
tools' update status is surfaced on demand via menu 6.

## Ordering (`model.py`)

New `sort_tools(tools) -> list[Tool]`:

```
key = (priority_rank(t.priority), t.category.lower(), t.name.lower())
priority_rank: P0→0, P1→1, P2→2, P3→3, anything else → 99
```

Applied wherever tools are rendered (`audit_table`, `audit_ai_table`, `summary`).
`categories()` keeps manifest order for the category-picker menu (independent of row
sort).

## Tables (`setup.py`)

- `audit_table` (CLI) and `audit_ai_table` (AI) → columns
  **`Pri │ Tool │ For │ What it does │ Status`**, rows sorted by `sort_tools`,
  disabled rows rendered dim. `What it does` = `desc`; `For` = `audience`.
- Status cell uses the accent map above.
- ACTIONS NEEDED panel (`run_ai_tools`) includes **LOUD states only**
  (`missing`, `needs_wiring`, `alias_needed`). A new **"Updates available"** calm
  line/panel lists `update`-state tools separately (cyan, no alarm styling).
- `summary` counts roll up by the new states (installed-ish = `current`/`pinned`/
  `update`; everything else = still missing), disabled excluded from "missing".

## Enable / disable behaviour

- `enabled = false` → `status()` returns `disabled` before any check; the tool is
  excluded from `actionable`, from `with_required` *selection*, and from install
  loops. It still renders as a dim row for visibility.
- **Dependency override:** if an *enabled* tool lists a *disabled* tool in `requires`,
  `with_required` still drags the disabled dep in (it is needed to make the enabled
  tool work) and emits a warning:
  `⚠ <dep> is disabled but required by <tool> — installing it anyway.`
- `pi` ships with `enabled = false`.

## registry.toml content changes

- Add `audience` + a one-line `desc` to all 40 rows (lifted/condensed from
  `docs/ia-helper-tools.md`).
- `pi` → `enabled = false`.
- `gsd` → add the `[tool.state]` block above.
- No `pin` set by default (the field exists for future use).

## Tests (bare `unittest`, TDD per repo convention)

New / updated coverage:

- `sort_tools`: P0→P3, category A→Z, name A→Z; unknown priority sorts last.
- Loader: `enabled` defaults true; `audience`/`desc`/`pin` parse; `[tool.state]`
  flattens to `state_*` fields.
- `status()`:
  - `disabled` short-circuits with no subprocess;
  - launcher `[tool.state]`: file absent → falls through; `update_available: true` →
    `update`; `false` → `current`; `pin` set + update true → `pinned`;
  - npx launcher with no binary and no state → `missing` (regression test for the old
    permanent `unknown`).
- `with_required`: enabled tool requiring a disabled dep drags it in + warns.
- Severity bucketing: LOUD set vs CALM set vs silent set.
- Update existing tests asserting the old `"installed"`/`"unwired"`/`"unknown"`
  strings to the new state names.

## Docs

Update the registry-schema section of `docs/ia-helper-tools.md` to document
`enabled`, `audience`, `desc`, `pin`, and `[tool.state]`.

## Out of scope

- Redesigning menu 6 network `sync` (stays as-is; still the place for network version
  checks).
- New install strategies / `kind`s.
- The pending GitLab force-push (branch protection) — unrelated, and the user has
  stated no push permission; do not attempt push.

## Constraints carried from project memory

- npm/pip banned → volta/pnpm for Node, uv for Python.
- Source artifacts (identifiers, comments, registry/docs copy) in English.
- Registry stays the single declarative source of truth (no hardcoded tool lists).
- Tests run with `python3 -m unittest discover -s tests -p 'test_*.py'` (no pytest).
