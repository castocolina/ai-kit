# Phase 3: Tool-Substitution Awareness Hook - Research

**Researched:** 2026-09-09
**Domain:** Claude Code / Cursor session-lifecycle hooks; local CLI tool-detection; stdlib-only JSON config wiring
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Scope and safety boundary**
- **D-01:** The hook fires only on `SessionStart` (`"startup"` and
  `"compact"`) and delivers its message via `hookSpecificOutput.additionalContext`
  — a context channel entirely separate from any Bash tool's stdout. It
  cannot alter or interfere with a command's expected output shape because it
  never touches command execution. There is **no** `PreToolUse` mechanism in
  this phase's scope (raised and explicitly ruled out mid-discussion — see
  Deferred Ideas).
- **D-02:** The new hook is a **separate, additional** entry in
  `settings.json`'s `hooks.SessionStart` array. It never edits, replaces, or
  otherwise touches `rtk`'s own hook registration (`rtk hook claude`,
  confirmed present via `rtk init --show`: `[ok] Hook: rtk hook claude`).
  Claude Code supports multiple independent hook entries per event; both run
  side-by-side and their outputs are concatenated.

**Message composition — two parts, one message**
- **D-03 (Part A — transparent-rewrite notice):** Live-verified against the
  actually-installed `rtk` (v0.44.1, not assumed from docs): `rtk` **already
  self-annotates truncation per-invocation**, inline in its own output (e.g.
  `+114 more in tools/status-line.py [see remaining: tail -n +26
  ~/.local/share/rtk/tee/...]`) — this is self-explanatory at the moment it
  happens and does NOT need repeating in a session-start message. What IS
  invisible: `rtk hook claude` (a `PreToolUse` hook) **transparently rewrites**
  certain Bash tool calls (`grep`→`rtk grep`, etc. — confirmed by the user's
  own `RTK.md`: "transparent, 0 tokens overhead"). Part A's content focuses
  on **this rewriting fact**, not on truncation mechanics.
- **D-04 (Part B — modern-tool-usage guidance):** A second section advises
  the agent on using available modern tools (`bat`, `rg`, `fd`, `sd`, `eza`)
  **directly**, with the flags matching its actual need (e.g. `bat --plain`
  to disable highlighting, line-range flags, etc.), rather than relying on
  `rtk`'s after-the-fact rewrite — but only for tools actually detected
  present (per D-06).
- **D-05:** Both parts are delivered as a compact, one-liner-per-substitution
  style message (not a verbose per-tool breakdown) — minimizes tokens
  injected on every session start/compact, consistent with `rtk`'s own
  compression philosophy.

**Detection signal source (corrects REQ's literal wording)**
- **D-06:** `REQ-tool-substitution-detection-composition`'s literal wording
  ("`registry.toml` `audience`") does **not** match the real, installed `rtk`
  (v0.44.1) — verified directly: `rtk`'s actual config is `config.toml` /
  `filters.toml`, with **no `registry.toml` and no `audience` field anywhere**
  (checked `rtk config`, `rtk gain`, `rtk --help`, and the filesystem). The
  curated 5-pair substitution list (`cat`↔`bat`, `grep`↔`rg`, `find`↔`fd`,
  `sed`↔`sd`, `ls`↔`eza`) was already established in `REQUIREMENTS.md` as
  **ai-kit's own** curated list, not something read from `rtk`. Detection
  composition is therefore: **ai-kit's own curated pair list × (binary
  presence via `shutil.which()` AND `rtk init --show` confirming
  `rtk`'s hook is active)** — without the hook actually wired, no
  substitution counts as "genuinely active" even if the modern binary exists
  on PATH, since `rtk` wouldn't be intercepting anything.
  — **Reversibility:** reversible — an internal detection-logic choice, no
  external contract; if `rtk`'s config format changes again, only the
  detection function's internals change.

**Hook wiring mechanics**
- **D-07:** New hook script lives at `tools/hooks/` (new directory — no
  existing hooks convention in this repo), stdlib-only, following the same
  style as `tools/status-line.py`.
- **D-08:** Wiring into `~/.claude/settings.json` uses the existing
  `_read_json`/`_write_json` primitives from `tools/setup.py`, but with
  **append-if-absent** semantics on the `hooks.SessionStart` array (not
  `wire_statusline()`'s overwrite-a-scalar-key pattern, since `hooks.SessionStart`
  is an array that may already hold `rtk`'s own entry or others) — detect
  whether ai-kit's own entry is already present (to avoid duplicating on
  reinstall) and never touch any other entry.

**Amendment (2026-09-08, during Phase 4 discussion)**
- **D-09:** `REQUIREMENTS.md`'s original wording only documented opencode as
  lacking a `SessionStart`-equivalent injection point. **Live-verified during
  Phase 4's discussion this was incomplete**: Cursor has its own
  `sessionStart` hook type (`~/.cursor/hooks.json` — confirmed present and
  currently active on this machine, alongside `beforeSubmitPrompt`, `stop`,
  `preToolUse`, `postToolUse`, `postToolUseFailure`, `beforeShellExecution`,
  `beforeMCPExecution`, `afterAgentResponse`, `subagentStart`, `subagentStop`).
  This phase's scope now includes wiring the equivalent tool-substitution
  briefing (D-03/D-04's two-part message) into Cursor's `sessionStart` hook
  too, alongside Claude Code's — **opencode remains the only genuine,
  accepted gap**. The researcher must confirm Cursor's `sessionStart` hook
  payload contract (does it support an `additionalContext`-equivalent field,
  or something else?) before planning locks the exact wiring mechanism.
  — **Reversibility:** reversible — adds a second wiring target using the
  same message-composition logic (D-03/D-04); no change to the detection
  logic (D-06) or the Claude-Code-specific wiring mechanics (D-07/D-08),
  which still apply as originally decided for the Claude Code side.
- **D-10 (found during Phase 4 discussion, 2026-09-08):** `tools/setup.py::cmd_uninstall()` currently removes ai-kit's symlinks and unwires `statusLine` (`unwire_statusline()`) but has **no equivalent for `hooks.SessionStart`** — an ai-kit-added hook entry would be left orphaned after uninstall. This phase's plan must add a symmetric `unwire_hook()` (or equivalent) that removes only ai-kit's own `hooks.SessionStart` entry/entries (Claude Code's, and — per D-09 — Cursor's `sessionStart` entry too) without touching `rtk`'s or any other third-party entry, called from `cmd_uninstall()` alongside the existing `unwire_statusline()` call.
  — **Reversibility:** reversible — an addition to existing uninstall logic, no external contract change.

### Claude's Discretion
None — every gray area in this phase had an explicit user decision.

### Deferred Ideas (OUT OF SCOPE)
- **Real-time PreToolUse enforcement mechanism**: a genuine `PreToolUse` hook
  that intercepts each Bash tool call and consults a cache built at
  `SessionStart` to actively suggest/enforce modern-tool usage per-command,
  rather than a one-time session-start briefing. Raised by the user mid-
  discussion; explicitly ruled out of this phase's scope (D-01) —
  `REQ-tool-substitution-hook-wiring` only covers `SessionStart` on
  `startup`/`compact`. Belongs in a future phase if real-time per-command
  intervention is ever wanted.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| REQ-tool-substitution-detection-composition | Pure, independently-tested live-detection + message-composition functions report which curated `rtk` substitutions (`cat`↔`bat`, `grep`↔`rg`, `find`↔`fd`, `sed`↔`sd`, `ls`↔`eza`) are genuinely active on this machine (binary presence + `registry.toml` `audience` + `rtk init --show`), never reciting catalog intent as verified; this curated set is the single source of truth mirrored by the usage-metrics command-family axis. | Detection mechanism fully re-derived and verified live (Standard Stack, Architecture Pattern 1, Pitfall 3) — REQ's literal `registry.toml`/`audience` wording is superseded by D-06's already-locked correction; this research confirms no such mechanism exists on the installed binary and documents the actual `[ok] Hook: rtk hook claude` text-parsing signal plus the curated-pair × binary-presence composition. |
| REQ-tool-substitution-hook-wiring | A new Claude Code `SessionStart` hook fires on `"startup"` and `"compact"`, injects the composed message via `hookSpecificOutput.additionalContext`, degrades gracefully (no error, no perceptible delay) when `rtk`/`tools-installer` is absent, and documents opencode's lack of an equivalent hook as an accepted gap. Cursor's `sessionStart` hook gets the equivalent briefing wired too (amended). | Both host contracts fully specified with primary-source citations (Architecture Pattern 1, Code Examples): Claude Code's `matcher: "startup\|compact"` syntax confirmed against official docs; Cursor's `{additional_context}` output schema confirmed by reading the live, working `gsd-cursor-session-start.js`. Append-if-absent/remove-only-ours wiring mechanics derived from the existing `unwire_statusline()` precedent (Architecture Pattern 2, Don't Hand-Roll). Atomic-write gap in the existing `_write_json()` helper flagged as Pitfall 1 so the planner doesn't silently reuse a non-atomic primitive. |
</phase_requirements>

## Summary

This phase is almost entirely de-risked by Phase 3's own `03-CONTEXT.md` (D-01
through D-10), which already resolved every open design question through live
verification against the actually-installed `rtk` v0.44.1 and the actually-
active `~/.cursor/hooks.json`. This research session re-verified those
findings directly (not re-trusting CONTEXT.md's prose) and closed the two
items CONTEXT.md left open: (1) the exact Cursor `sessionStart` payload
contract (D-09's stated open question), and (2) the official Claude Code
`SessionStart` matcher/schema details needed to satisfy REQ-tool-substitution-
hook-wiring's "fires on `startup` and `compact`" wording precisely.

Both hook targets are now fully specified with primary-source citations. Claude
Code's `SessionStart` hook accepts a single `matcher: "startup|compact"` entry
(pipe-separated exact-match list) rather than requiring two separate array
entries, confirmed against the official hooks reference. Cursor's `sessionStart`
hook contract was confirmed by reading GSD's own already-installed script at
`~/.cursor/hooks/gsd-cursor-session-start.js` — a real, working example on this
exact machine, not third-party docs — which documents the input/output schema
directly in its header comment and outputs `{ additional_context: string }` on
stdout. rtk detection has no reliable JSON output for "is my hook active";
`rtk init --show` is text-only and must be parsed by matching the `[ok] Hook:`
line prefix, exactly as D-06 already established.

One material gap surfaced during this research that CONTEXT.md did not flag:
`tools/setup.py`'s existing `_write_json()` helper (the primitive D-08
explicitly says to reuse) is **not** atomic — it opens the target path
directly with `"w"` mode and writes in place, with no `tempfile.mkstemp()` +
`os.replace()`. This contradicts `AGENTS.md`'s non-negotiable rule that "every
write to a runtime's config file ... is atomic," which explicitly lists
"ai-kit's own `settings.json` wiring" as covered. Phase 2 already built and
tested the correct atomic-write primitive (`write_preserving_mode()` in
`ai_kit_opencode_providers/atomic_write.py`) for exactly this class of
problem. The planner must decide: wrap `_write_json`'s call sites in an
atomic temp-file+replace step (reusing or adapting Phase 2's primitive) rather
than reusing `_write_json` verbatim for this phase's two new config writes.

**Primary recommendation:** Build one pure `compose_message()` function
(stdlib-only, independently unit-testable) that takes a detection result and
returns the two-part message string; call it identically from both the new
Claude Code hook script and the new Cursor hook script, wiring each host's own
JSON envelope around the same core. Detect ai-kit's own hook entries in both
`hooks.SessionStart` (Claude Code, capital S) and `hooks.sessionStart`
(Cursor, lowercase s) by a command-string substring match against the install
dir — mirroring the exact `_is_inside_str()` pattern `unwire_statusline()`
already uses — not by inventing a new marker-key convention (this repo has no
existing precedent for one on the Claude Code side, though GSD's own Cursor
entries do carry an unrelated `"gsd-managed": true` key ai-kit must never
touch or imitate as if it were shared vocabulary).

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Detect installed curated-pair binaries (`bat`/`rg`/`fd`/`sd`/`eza`) | CLI / local tool script | — | Pure `shutil.which()` calls, no host involvement |
| Detect rtk hook-active state | CLI / local tool script | — | Subprocess call to `rtk init --show`, parsed locally |
| Compose the two-part briefing message | CLI / local tool script (shared core) | — | Pure function, no I/O, shared by both hook wrappers |
| Claude Code session-start injection | Claude Code host (`SessionStart` hook contract) | CLI script (produces the JSON) | Host owns the wire format (`hookSpecificOutput.additionalContext`); script owns content |
| Cursor session-start injection | Cursor host (`sessionStart` hook contract) | CLI script (produces the JSON) | Host owns its own wire format (`additional_context`); script owns content |
| Config-file wiring (settings.json / hooks.json) | Installer (`tools/setup.py`) | — | Existing install/uninstall lifecycle owns all runtime-config mutation |
| opencode gap documentation | Docs / skill | — | No injection point exists; a documentation-only responsibility |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python stdlib (`shutil.which`, `subprocess`, `json`, `os`, `tempfile`) | 3.11+ (repo's own floor per AGENTS.md) | Binary detection, rtk subprocess call, JSON read/write, atomic file replace | Matches the repo's hard "runtime code stays stdlib-only" rule; no new dependency needed anywhere in this phase |
| Node.js (already required by Cursor's own hook runtime — see `~/.cursor/hooks/gsd-cursor-session-start.js`) | whatever `node` Cursor's hook shim resolves (`/var/home/bazzite/.volta/bin/node` or PATH `node`) `[VERIFIED: /home/bazzite/.cursor/hooks/gsd-cursor-session-start.js:1]` | Cursor hook entrypoint execution | Cursor's `sessionStart` hook is invoked as a `command` hook; other entries in this repo's `hooks.json` (GSD's own) are Node scripts, establishing the pattern for wiring a script-based Cursor hook. ai-kit's own script does **not** have to be Node — Cursor's `command` field can point at any executable, including a Python script marked executable, matching D-07's "stdlib-only script" preference and keeping ai-kit's own runtime dependency-free even on the Cursor side. |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| None | — | — | This phase installs zero new third-party packages in either ecosystem. |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Parsing `rtk init --show` text output | A hypothetical `rtk config --json`/`rtk init --show --json` | Does not exist on the installed v0.44.1 binary — `rtk config --help` only offers `--create`/`--ultra-compact`/`--skip-env` flags, no JSON mode `[VERIFIED: local rtk v0.44.1 --help output, this session]`. Text-parsing the `[ok] Hook: rtk hook claude` line is the only available signal. |
| Two separate `hooks.SessionStart` array entries (one per source) | Single entry with `matcher: "startup|compact"` | The official docs confirm the matcher accepts a pipe-separated exact-match list in one entry — simpler, avoids a double-injection race if both entries somehow both fired for a compound-source session `[CITED: code.claude.com/docs/en/hooks]`. |

**Installation:** None required — this phase ships pure Python and reuses the JS runtime Cursor already invokes for its other hooks. No `pip install` / `npm install` step.

**Version verification:** No packages to verify (zero-dependency phase). The one live-installed tool this phase *detects but does not depend on at build time* is `rtk` — confirmed installed at `/home/bazzite/.local/bin/rtk`, version `0.44.1` `[VERIFIED: rtk --version, this session]`.

## Package Legitimacy Audit

Not applicable — this phase installs zero external packages (npm/PyPI/crates or otherwise). Both the Claude Code hook script and the Cursor hook script are new stdlib-only/no-dependency scripts written directly in this repo. The Package Legitimacy Gate is therefore skipped per its own trigger condition ("every phase that installs external packages").

## Architecture Patterns

### System Architecture Diagram

```
                    ┌─────────────────────────────┐
                    │   tools/hooks/detect.py      │   (new, shared, stdlib-only)
                    │  - detect_substitutions()    │
                    │  - compose_message()         │
                    └──────────────┬───────────────┘
                                   │ imported by both wrappers
              ┌────────────────────┴────────────────────┐
              ▼                                          ▼
┌───────────────────────────────┐        ┌───────────────────────────────────┐
│ tools/hooks/claude_session_    │        │ tools/hooks/cursor_session_        │
│ start.py  (Claude Code wrapper)│        │ start.py  (Cursor wrapper)         │
│ - reads stdin (unused/ignored) │        │ - reads stdin JSON (session_id,    │
│ - calls compose_message()      │        │   cursor_version, ...)             │
│ - emits {hookSpecificOutput:   │        │ - calls compose_message()          │
│   {hookEventName:"SessionStart"│        │ - emits {additional_context: msg}  │
│   , additionalContext: msg}}   │        │   on stdout                        │
└───────────────┬────────────────┘        └──────────────┬──────────────────┘
                │ registered in                            │ registered in
                ▼                                           ▼
   ~/.claude/settings.json                       ~/.cursor/hooks.json
   hooks.SessionStart[]                          hooks.sessionStart[]
   matcher: "startup|compact"                    (Cursor has no matcher
   (append-if-absent, wired by                    concept for sessionStart —
   tools/setup.py's cmd_install,                  fires on every session)
   unwired by cmd_uninstall)                      (wired/unwired same way)
                │                                           │
                ▼                                           ▼
        Claude Code injects msg                    Cursor injects msg
        into model context at                      into agent context at
        session startup/compact                    session start
                                                             │
                                                             ▼
                                              (opencode: no equivalent
                                               injection point exists —
                                               documented gap, no code path)
```

### Recommended Project Structure
```
tools/
├── hooks/                          # new directory (D-07) — no prior convention
│   ├── __init__.py                 # empty; makes the package importable for tests
│   ├── detect.py                   # shared, host-agnostic: detect_substitutions() + compose_message()
│   ├── claude_session_start.py     # thin Claude Code SessionStart wrapper (stdlib, no argv deps)
│   └── cursor_session_start.py     # thin Cursor sessionStart wrapper (stdlib, no argv deps)
├── setup.py                        # gains wire_hook()/unwire_hook() calls, called from
│                                    #   cmd_install()/cmd_uninstall() alongside wire_statusline()
tests/
└── test_tool_substitution_hook.py  # new — unit tests for detect_substitutions()/compose_message()
                                     #   + wire_hook()/unwire_hook() append-if-absent/remove-only-ours
```

### Pattern 1: Pure detect-then-compose, host-agnostic core
**What:** `detect_substitutions()` returns a plain data structure (e.g. a list
of `{pair: "grep/rg", installed: bool}` dicts plus an overall `rtk_hook_active:
bool`); `compose_message(detection) -> str` is a pure function with no I/O.
Both host wrappers are then reduced to "call detect, call compose, wrap in the
host's own envelope, print it."
**When to use:** Any time the same content needs to reach two structurally
different host contracts (Claude Code's `hookSpecificOutput.additionalContext`
vs. Cursor's `additional_context`) — keeping composition logic hostagnostic
means one set of unit tests (REQ-tool-substitution-detection-composition) covers
both wiring targets (REQ-tool-substitution-hook-wiring) without duplication.
**Example — Claude Code wrapper's output shape** (verified against a real,
currently-installed, working hook in this exact environment):
```python
# Source: verified against /home/bazzite/.claude/hooks/gsd-session-state.sh's
# actual production JSON envelope (this session's Read of that file) —
# not third-party docs. Reproduced in Python; the bash original builds this
# via `node -e '...JSON.stringify({hookSpecificOutput: {...}})'`.
import json, sys

def emit_claude_session_start(additional_context: str) -> None:
    sys.stdout.write(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": additional_context,
        }
    }))
```
**Example — Cursor wrapper's output shape** (verified by reading the
already-installed `~/.cursor/hooks/gsd-cursor-session-start.js`, lines 1-56):
```javascript
// Source: /home/bazzite/.cursor/hooks/gsd-cursor-session-start.js (read
// verbatim this session). Output schema per that file's own header comment:
//   { additional_context?: string }   <- injected into the session as context
process.stdout.write(JSON.stringify({ additional_context: msg }));
```

### Pattern 2: Append-if-absent / remove-only-ours config wiring (mirrors `unwire_statusline`)
**What:** Detect ai-kit's own hook entry by checking whether the install dir
(or the specific script path) appears as a substring of the entry's
`command` string — exactly the `_is_inside_str(install_dir, cur_cmd)` test
`unwire_statusline()` already uses — rather than any marker-key scheme.
**When to use:** Both `hooks.SessionStart` (Claude Code, array of `{hooks:
[...]}` wrapper objects, each `hooks[]` item has a `command` string) and
`hooks.sessionStart` (Cursor, flat array of `{command, ...}` objects — no
`{hooks: [...]}` wrapper layer, confirmed by reading the live file).
**Example (Claude Code side, adapted from the verified precedent):**
```python
# Source: tools/setup.py:1415-1433 (read verbatim this session)
# def unwire_statusline(settings, install_dir, dry):
#     data = _read_json(settings)
#     cur = data.get("statusLine")
#     cur_cmd = cur.get("command", "") if isinstance(cur, dict) else ""
#     if not (cur_cmd and _is_inside_str(install_dir, cur_cmd)):
#         return
#     ...
#     data.pop("statusLine", None)
#     _write_json(settings, data)
#
# def _is_inside_str(install_dir, command):
#     return install_dir in command
#
# The array case (SessionStart) needs the same substring test applied
# per-entry with filtering, not popping a single scalar key:
def unwire_hook(settings_path, install_dir, read_json, atomic_write_json):
    data = read_json(settings_path)
    hooks = data.get("hooks", {})
    session_start = hooks.get("SessionStart", [])
    kept = [
        entry for entry in session_start
        if not any(
            install_dir in h.get("command", "")
            for h in entry.get("hooks", [])
        )
    ]
    if kept == session_start:
        return  # nothing of ours was present
    hooks["SessionStart"] = kept
    atomic_write_json(settings_path, data)
```

### Anti-Patterns to Avoid
- **Trusting `registry.toml`/`audience` as REQ's wording literally states:**
  D-06 already found this mechanism does not exist on the installed rtk;
  don't resurrect it. Detection is ai-kit's own curated pair list × binary
  presence × `rtk init --show` hook-active parsing.
- **Reusing `_write_json()` unmodified for this phase's new writes:** it is
  not atomic (see Common Pitfalls below) — wrap it or replace it for the two
  new call sites this phase adds.
- **Inventing a `"ai-kit-managed": true` marker key:** no such convention
  exists anywhere in this repo's own hook/config wiring (`wire_statusline`
  uses substring detection, not a marker key). GSD's own Cursor entries do
  carry `"gsd-managed": true`, but that is GSD's private vocabulary in a
  shared file — ai-kit must not read or write that key, and must not assume
  Claude Code or Cursor validates/preserves unrecognized keys as a stable
  contract just because GSD's entries happen to have one.
- **Blocking session start on rtk detection:** `rtk init --show` is a
  subprocess call; guard it with a short timeout (the SessionStart hook
  itself has a generous 600s host-side default timeout, but D-01/REQ's "no
  perceptible delay" success criterion means the subprocess call itself
  should be bounded far below that — a few seconds at most, with the message
  degrading to omit rtk-hook-active content on timeout/absence rather than
  waiting).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Atomic JSON config write | A new from-scratch tempfile+replace routine | Reuse/adapt `write_preserving_mode()` from `skills/ai-kit-opencode-providers/ai_kit_opencode_providers/atomic_write.py` (already handles mode-preservation, symlink-safety, fsync durability, ownership) | Phase 2 already built, tested, and skill-judge-reviewed this exact primitive; this phase's config files (`settings.json`, `hooks.json`) are plain JSON (not JSONC), so the simpler byte-serialize-then-atomic-write half of that pattern applies directly — no need to re-derive WR-01/WR-02's durability reasoning from scratch. |
| JSON read/write to `settings.json`/`hooks.json` | A new ad hoc JSON loader | `tools/setup.py::_read_json()` (line 1320) for reads — it already handles missing-file and malformed-JSON gracefully, matching D-08 | Already exists, already tested, already the established convention for this exact file |
| rtk hook-active detection | Guessing from binary presence alone | Parse the `[ok] Hook: rtk hook claude` line from `rtk init --show` stdout (D-06) | Binary-on-PATH alone doesn't prove the `PreToolUse` hook is wired — `rtk` could be installed but never `rtk init`'d, in which case no substitution is "genuinely active" per the phase's own success criterion 1 |

**Key insight:** Every non-trivial primitive this phase needs (atomic config
write, JSON read helper, hook-array append/remove pattern) already exists in
this repo from Phase 2 or from the pre-existing statusline wiring — the only
genuinely new code is the detection/composition logic itself and the two thin
host-wrapper scripts.

## Runtime State Inventory

Not applicable in the rename/refactor/migration sense — this phase adds new
capability (a new hook + new config entries), it does not rename or migrate
an existing string/identifier. For completeness, verified explicitly:

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — no database/datastore is touched by this phase | None |
| Live service config | `rtk`'s own `~/.config/rtk/config.toml` (`[tracking]`, `[filters]`, `[hooks]`, `[limits]` sections — verified this session, no `registry.toml`/`audience` anywhere) is read-adjacent only (this phase never writes it) | None — read-only awareness |
| OS-registered state | None — no OS-level task/service registration involved | None |
| Secrets/env vars | None — no secret material is read, written, or referenced by this phase | None |
| Build artifacts | None — new files are plain scripts, not compiled/packaged artifacts | None |

## Common Pitfalls

### Pitfall 1: `_write_json()` is not atomic despite AGENTS.md's atomic-write rule
**What goes wrong:** Reusing `tools/setup.py::_write_json()` verbatim (as
D-08's wording could be read to suggest) for the new `hooks.SessionStart`
write produces a non-atomic write — a crash mid-write could leave
`settings.json` truncated/corrupted, exactly the failure mode `AGENTS.md`'s
"every write to a runtime's config file ... is atomic" rule exists to
prevent.
**Why it happens:** `_write_json()` (verified this session,
`tools/setup.py:1332-1337`) is:
```python
def _write_json(path, data):
    """Write JSON with a 2-space indent + trailing newline, creating parents."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")
```
This predates Phase 2's atomic-write work and was never retrofitted —
`wire_statusline`/`unwire_statusline` (its only current callers) inherited
the gap silently.
**How to avoid:** For this phase's two new write call sites (Claude Code
`hooks.SessionStart` append/remove, Cursor `hooks.sessionStart`
append/remove), either (a) adapt `write_preserving_mode()` from Phase 2's
`atomic_write.py` to accept pre-serialized JSON text, or (b) write a small
`_atomic_write_json()` variant using the same `tempfile.mkstemp` +
`os.replace` + `fsync` shape. Do not silently perpetuate the existing gap
into new code — flag it to the planner as an explicit task, and optionally
note the pre-existing `_write_json()` gap as a candidate follow-up (out of
this phase's literal scope, since `wire_statusline`/`unwire_statusline`
aren't being touched by Phase 3, but worth a one-line note in the plan so
it isn't mistaken for "already fixed").
**Warning signs:** A test that kills the write mid-flight (or a code
reviewer checking for `tempfile`/`os.replace` in the diff) is the way to
catch this before it ships.

### Pitfall 2: Claude Code vs. Cursor hook-array key casing and shape differ
**What goes wrong:** Writing to `hooks.sessionStart` (Cursor's actual
lowercase key, verified by reading the live `~/.cursor/hooks.json`) using
Claude Code's capitalized `SessionStart` key silently creates a dead,
never-fired second key, or vice versa.
**Why it happens:** The two hosts' schemas are independently designed and
happen to differ only in casing, which is easy to typo past.
**How to avoid:** Use two distinct, explicitly-named constants in the
wiring code (`CLAUDE_HOOK_EVENT = "SessionStart"`,
`CURSOR_HOOK_EVENT = "sessionStart"`) rather than a shared string. Also
note the **array shape differs**: Claude Code's `hooks.SessionStart` is an
array of `{"matcher": ..., "hooks": [{"type": "command", "command": ...}]}`
wrapper objects (matcher-then-hooks-list nesting); Cursor's
`hooks.sessionStart` is a **flat** array of `{"command": ..., "type":
...}` objects with no matcher/nesting layer (verified this session by
reading the live file — Cursor's `sessionStart` array has exactly one
un-nested entry). Code that assumes both arrays share one shape will break
one side.
**Warning signs:** A unit test asserting on the exact written JSON shape
for each host, using synthetic fixture files (never uz's real
`~/.claude/settings.json` or `~/.cursor/hooks.json`, per `AGENTS.md`'s
testing rule) catches this immediately.

### Pitfall 3: `rtk init --show`'s exact text format is not a documented, versioned contract
**What goes wrong:** A future `rtk` release could reword or reformat the
`[ok] Hook: rtk hook claude` line (or drop the leading `[ok]`/`[--]`
bracket convention entirely), silently breaking the parser with no error —
producing a false "rtk hook not active" reading even though it is.
**Why it happens:** This is a third-party CLI's human-readable diagnostic
output, not a stable machine-readable API — there is no `--json` flag on
`rtk init`/`rtk config` on the installed v0.44.1 `[VERIFIED: rtk --help,
rtk config --help, this session]`.
**How to avoid:** Parse defensively (substring/regex match on `Hook:` +
`rtk hook claude`, not a rigid full-line match), and treat a parse miss as
"rtk hook not confirmed active" (fail toward the shorter/degraded message,
consistent with success criterion 3's "degrades ... instead of erroring"),
never as a crash. Confidence-label this detection path (`[LOW confidence —
reverse-engineered from CLI text output]`) per `AGENTS.md`'s
confidence-labeling constraint.
**Warning signs:** A parser unit test using a fixture string that omits the
`[ok] Hook:` line entirely (simulating a future rtk version) should still
produce a valid, non-crashing "degraded" message.

### Pitfall 4: Claude Code SessionStart hooks can silently receive no visible effect when misregistered inside a plugin
**What goes wrong:** A known Claude Code issue: when a `SessionStart` hook
is defined inside a plugin's own `hooks.json` (as opposed to the user/
project `settings.json` this phase targets), `hookSpecificOutput.
additionalContext` is executed but never surfaced to the model — Claude
only sees a generic success message `[CITED: github.com/anthropics/
claude-code/issues/16538]`.
**Why it happens:** A host-side bug specific to the plugin-hooks delivery
path, not to the `settings.json`-registered path this phase actually uses.
**How to avoid:** This phase wires via `~/.claude/settings.json`'s
top-level `hooks.SessionStart` (matching D-08 and the already-working GSD
precedent scripts at `~/.claude/hooks/*`), **not** via a Claude Code
plugin manifest — so this bug does not apply, but it's worth confirming
during implementation that the chosen `ai-kit-spec-review`-adjacent
install path never routes through a plugin `hooks.json` instead.
**Warning signs:** If a manual smoke test shows the hook script's own
stderr/log confirms it ran, but the injected context never appears in a
fresh Claude Code session's visible context, check whether it accidentally
ended up registered as a plugin hook rather than a settings.json hook.

## Code Examples

### Claude Code SessionStart — matcher syntax for exactly `startup` + `compact`
```json
// Source: code.claude.com/docs/en/hooks (WebFetch this session) — matcher
// accepts "Exact string, or list of exact strings separated by `|` or `,`"
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "startup|compact",
        "hooks": [
          {
            "type": "command",
            "command": "python3 /path/to/tools/hooks/claude_session_start.py"
          }
        ]
      }
    ]
  }
}
```
This satisfies REQ-tool-substitution-hook-wiring's "fires on `startup` and
`compact`" precisely — `resume`, `clear`, and `fork` sources (the other three
valid matcher values `[CITED: code.claude.com/docs/en/hooks]`) never trigger
this hook, avoiding redundant injection on every `resume`.

### rtk hook-active detection — the actual, current `rtk init --show` output
```
[VERIFIED: rtk init --show output, this session, rtk v0.44.1]
rtk Configuration:

[ok] Hook: rtk hook claude (native binary command)
[ok] RTK.md: /home/bazzite/.claude/RTK.md (slim mode)
[ok] Global (~/.claude/CLAUDE.md): @RTK.md reference
[--] Local (./CLAUDE.md): not found
[ok] settings.json: RTK hook configured
[ok] OpenCode: plugin installed (/home/bazzite/.config/opencode/plugins/rtk.ts)
[ok] Cursor hook: registered in hooks.json
```
Note this output already reports per-host status lines (`settings.json`,
`OpenCode`, `Cursor hook`) — the same `[ok]`/`[--]` bracket convention could
in principle be reused as a detection signal for Cursor's rtk hook too
(`[ok] Cursor hook: registered in hooks.json`), though D-06/D-09 only
required Claude Code's line for the curated-pair detection; the planner may
choose to also parse the `Cursor hook:` line for symmetry when composing the
Cursor-side message.

### Real, already-installed rtk `PreToolUse` entry (what NOT to touch)
```
[VERIFIED: /home/bazzite/.claude/settings.json, hooks.PreToolUse[9], this session]
{"matcher": "Bash", "hooks": [{"type": "command", "command": "rtk hook claude"}]}
```
This is rtk's own registration — confirmed present at `PreToolUse` index 9 of
10 (matcher `"Bash"`). Confirms D-02's premise: rtk's own hook lives under a
**different** event (`PreToolUse`), not `SessionStart` at all — so there is
currently no existing `SessionStart` entry belonging to rtk to collide with;
the append-if-absent guard only needs to guard against duplicating *ai-kit's
own* prior installs, not against rtk's entry.

### Cursor's existing `sessionStart` array shape (flat, no matcher wrapper)
```json
[VERIFIED: /home/bazzite/.cursor/hooks.json, this session]
"sessionStart": [
  {
    "type": "command",
    "command": "\"$(for n in ...node resolution...)\" \"/home/bazzite/.cursor/hooks/gsd-cursor-session-start.js\"",
    "gsd-managed": true
  }
]
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| SessionStart hooks show a user-visible transcript message | Silent context injection via `hookSpecificOutput.additionalContext` | Claude Code 2.1.0 ("ultrathink" update) `[CITED: WebSearch summary of code.claude.com/docs/en/hooks-guide + third-party guides, this session]` | The message this phase composes is invisible in the transcript by design — don't design around the assumption uz will "see" the briefing printed; it's context the model sees, not chat output. |

**Deprecated/outdated:** REQUIREMENTS.md's literal `registry.toml`/`audience`
wording (see D-06) — already formally superseded within this phase's own
CONTEXT.md; the planner should treat the curated-pair-list × binary-presence
× rtk-hook-active-parse approach as the only correct detection mechanism.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Cursor's `command` hook entries can point at a Python script directly (not requiring Node), mirroring how the existing entries point at `.js` files run through a resolved `node` binary | Standard Stack / Architecture | If Cursor's hook runner requires a shebang-executable file specifically, or behaves differently for a `.py` vs `.js` target, ai-kit's Cursor wrapper may need a thin shell/node shim instead of a bare Python script — low risk since `command` is a free-form shell string in every observed entry (including the rtk entry, `"command": "rtk hook cursor"`, which is a compiled binary, not JS), so an executable Python script should work identically, but this hasn't been positively confirmed by running a Python-based Cursor hook end-to-end on this machine. |
| A2 | Cursor's `sessionStart` hook has no `matcher`/source-filtering concept (unlike Claude Code's `startup`/`resume`/`clear`/`compact`/`fork`) and simply fires on every session start | Architecture Diagram | If Cursor does distinguish session-start sources and silently drops entries without a matcher, the hook might fire less often than expected (not more) — low risk to correctness of the message content, only to injection frequency. Not found in any Cursor-side documentation during this research pass; inferred from the single live example, which has no matcher-equivalent field. |
| A3 | `rtk init --show`'s `Cursor hook: registered in hooks.json` line reliably reflects whether `rtk hook cursor`'s `PreToolUse` entry is genuinely wired (mirroring the Claude Code line's reliability) | Code Examples | If this line's semantics differ from the Claude Code line (e.g., checks file *presence* rather than *entry-active* state), a Cursor-side "genuinely active" claim could overstate confidence — same risk class D-06 already flagged for the Claude Code line, just not yet separately verified for the Cursor line specifically. |

**If this table is empty:** N/A — see entries above.

## Open Questions

1. **Should the Cursor-side message also mention rtk's Cursor `PreToolUse`
   hook (`rtk hook cursor`, confirmed present in `~/.cursor/hooks.json`'s
   `preToolUse` array), or reuse the identical Claude-Code-worded message
   verbatim?**
   - What we know: `rtk` registers functionally-equivalent `PreToolUse`
     hooks for both Claude Code (`rtk hook claude`) and Cursor (`rtk hook
     cursor`) — confirmed live in both hosts' config files this session.
   - What's unclear: CONTEXT.md's D-09 amendment says "wiring the
     equivalent tool-substitution briefing... into Cursor's `sessionStart`
     hook too" without specifying whether "equivalent" means byte-identical
     text or host-appropriately-reworded text (e.g., referencing `rtk hook
     cursor` instead of `rtk hook claude` by name).
   - Recommendation: Share the exact same `compose_message()` output for
     both hosts (Pattern 1 above) — the message's content (which
     substitutions are active) doesn't actually depend on which host-specific
     rtk hook subcommand is registered, only on whether *a* rtk hook is
     active for *that host*. Keep host-name references out of the message
     body entirely to avoid this asymmetry; if the planner disagrees, this
     is a one-line change to `compose_message()`'s signature (accept a
     `host: str` param), not an architectural change.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `rtk` binary | Detection of rtk-hook-active state | ✓ | 0.44.1 `[VERIFIED, this session]` | Detection function returns `rtk_hook_active: False`; message degrades per success criterion 2/3 |
| `bat` | Curated-pair detection | ✓ | present at `~/.local/bin/bat` `[VERIFIED]` | Pair reported as not-installed |
| `rg` (ripgrep) | Curated-pair detection | ✓ | present at `~/.local/bin/rg` `[VERIFIED]` | Pair reported as not-installed |
| `fd` | Curated-pair detection | ✓ | present at `~/.local/bin/fd` `[VERIFIED]` | Pair reported as not-installed |
| `sd` | Curated-pair detection | ✓ | present at `~/.local/bin/sd` `[VERIFIED]` | Pair reported as not-installed |
| `eza` | Curated-pair detection | ✓ | present at `~/.local/bin/eza` `[VERIFIED]` | Pair reported as not-installed |
| `~/.claude/settings.json` | Claude Code hook wiring | ✓ | exists, valid JSON, has 3 existing `SessionStart` entries `[VERIFIED]` | N/A — file always exists once Claude Code has run once; installer already handles absent case via `_read_json`'s empty-dict fallback |
| `~/.cursor/hooks.json` | Cursor hook wiring | ✓ | exists, valid JSON, has 1 existing `sessionStart` entry (GSD's own) `[VERIFIED]` | Same — `_read_json`-equivalent empty-dict fallback needed for a machine with Cursor never configured |
| `node` (for Cursor's *existing* GSD hooks, not required by ai-kit's own new script per A1) | N/A to this phase directly | ✓ | resolved via `/var/home/bazzite/.volta/bin/node` fallback chain in existing entries | N/A |

**Missing dependencies with no fallback:** None.

**Missing dependencies with fallback:** `rtk` and each curated-pair binary
already have documented graceful-degradation behavior built into the
detection/composition design itself (success criteria 2 and 3) — not a gap,
by design.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | `unittest` (stdlib), invoked via `python3 -m unittest` — the whole repo's convention, no pytest `[VERIFIED: AGENTS.md Testing section + Makefile:34]` |
| Config file | none — `Makefile`'s `test:` target lists modules explicitly |
| Quick run command | `python3 -m unittest tests.test_tool_substitution_hook -v` |
| Full suite command | `make test` (after adding the new module to `Makefile:34`'s list) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| REQ-tool-substitution-detection-composition | `detect_substitutions()` reports only genuinely-installed pairs; never recites catalog intent | unit | `python3 -m unittest tests.test_tool_substitution_hook.TestDetect -v` | ❌ Wave 0 |
| REQ-tool-substitution-detection-composition | `compose_message()` degrades to short/empty message when rtk absent, with no exception raised | unit | `python3 -m unittest tests.test_tool_substitution_hook.TestCompose -v` | ❌ Wave 0 |
| REQ-tool-substitution-hook-wiring | Claude Code wrapper emits valid `{hookSpecificOutput: {hookEventName, additionalContext}}` JSON on stdout | unit | `python3 -m unittest tests.test_tool_substitution_hook.TestClaudeWrapper -v` | ❌ Wave 0 |
| REQ-tool-substitution-hook-wiring | Cursor wrapper emits valid `{additional_context}` JSON on stdout | unit | `python3 -m unittest tests.test_tool_substitution_hook.TestCursorWrapper -v` | ❌ Wave 0 |
| REQ-tool-substitution-hook-wiring | `wire_hook()`/`unwire_hook()` append-if-absent and remove-only-ours, never touching rtk's or a foreign entry, using synthetic fixture JSON (never uz's real config files) | unit | `python3 -m unittest tests.test_tool_substitution_hook.TestWiring -v` | ❌ Wave 0 |
| REQ-tool-substitution-hook-wiring | opencode gap documented in code/skill, not silently absent | manual/doc-review | grep for the documented gap string during code review | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `python3 -m unittest tests.test_tool_substitution_hook -v`
- **Per wave merge:** `make test` (full suite, including `tests/test_install.sh`)
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_tool_substitution_hook.py` — covers both REQs above; must
      use synthetic fixture JSON, never `~/.claude/settings.json` or
      `~/.cursor/hooks.json` directly (per `AGENTS.md`'s testing rule)
- [ ] `Makefile:34`'s `test:` target — add `tests.test_tool_substitution_hook`
      to the module list
- [ ] No new fixtures directory needed — `tests/fixtures/` already exists and
      follows the convention other test modules use

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-------------------|
| V2 Authentication | no | No authentication surface in this phase |
| V3 Session Management | no | "Session" here means a Claude Code/Cursor conversational session, not an ASVS auth session |
| V4 Access Control | no | Local single-user CLI tool, no multi-principal access boundary |
| V5 Input Validation | yes | Subprocess output (`rtk init --show`) and JSON config file contents are both untrusted-ish inputs — parse defensively (Pitfall 3), never `eval`/`exec` any of it, and validate JSON shape (`isinstance(data, dict)`, matching `_read_json`'s existing convention) before mutating |
| V6 Cryptography | no | No cryptographic operation in this phase |
| V10 Malicious Code / Command Injection | yes | The `rtk init --show` subprocess call must use an argv list (`subprocess.run(["rtk", "init", "--show"], ...)`), never `shell=True` with string interpolation — no user-controlled input reaches this call, but the pattern should still be safe-by-construction |
| V12 Files and Resources | yes | Atomic config writes (Pitfall 1), and confirm the target config path is always the resolved `~/.claude/settings.json`/`~/.cursor/hooks.json` (via the same `resolve_paths()`-style env-var precedence already used for `settings.json`, not a hardcoded path that could resolve outside the intended config dir) |
| V14 Configuration | yes | New hook registration must never overwrite or reorder existing unrelated entries (D-02/D-08's explicit non-negotiable) — this is itself a security property: a corrupted `settings.json`/`hooks.json` could silently disable other security-relevant hooks (e.g. a permission-gating `PreToolUse` hook) |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|-----------------------|
| Subprocess command injection via unsanitized arguments | Tampering | Fixed argv list for the `rtk init --show` call, never shell string interpolation |
| Config-file corruption from a non-atomic write racing a concurrent Claude Code/Cursor process | Tampering / Denial of Service | Atomic write (tempfile + `os.replace` + fsync), per Pitfall 1 and Phase 2's `write_preserving_mode()` precedent |
| Overwriting/losing another tool's hook entry (rtk's own, or a third-party's) during append/unwire | Tampering | Append-if-absent + remove-only-ours substring-match discipline (Pattern 2), same non-negotiable D-02/D-08 already established |
| Prompt-injection-style content smuggled into `additionalContext`/`additional_context` via a maliciously-named binary or crafted `rtk` output | Tampering / Elevation of Privilege (indirect, via model context) | Compose the message from a fixed template with only enum-like/boolean inputs (pair names are hardcoded, not read from any external string) — never interpolate raw `rtk init --show` output text verbatim into the injected message |

## Sources

### Primary (HIGH confidence)
- `code.claude.com/docs/en/hooks` (WebFetch, this session) — SessionStart
  matcher values/syntax, JSON input/output schema, timeout defaults,
  blocking/error-handling behavior
- Local, live-verified `rtk` v0.44.1 binary (`rtk --version`, `rtk init
  --show`, `rtk --help`, `rtk config --help`, `rtk gain --help`, this
  session)
- `/home/bazzite/.claude/settings.json` (read directly, this session) —
  actual `hooks.SessionStart`/`hooks.PreToolUse` contents, including rtk's
  own `PreToolUse` entry
- `/home/bazzite/.cursor/hooks.json` (read directly, this session) — actual
  `hooks.sessionStart` contents and every other registered Cursor hook event
- `/home/bazzite/.cursor/hooks/gsd-cursor-session-start.js` (Read tool, this
  session, lines 1-56) — ground-truth Cursor `sessionStart` input/output
  schema, documented in the file's own header comment
- `/home/bazzite/.claude/hooks/gsd-session-state.sh` (Read tool, this
  session) — ground-truth Claude Code `SessionStart`
  `hookSpecificOutput.additionalContext` envelope, from a script that is
  currently active and working in this exact environment
- `tools/setup.py` (Read tool, this session, lines 1312-1441) —
  `_read_json`/`_write_json`/`wire_statusline`/`unwire_statusline`/
  `_is_inside_str`, verbatim with line numbers
- `skills/ai-kit-opencode-providers/ai_kit_opencode_providers/atomic_write.py`
  (Read tool, this session, full file) — the established atomic-write
  primitive this phase should reuse/adapt

### Secondary (MEDIUM confidence)
- `github.com/anthropics/claude-code/issues/16538` (WebSearch result,
  this session) — plugin-hooks `additionalContext` delivery bug; confirmed
  not applicable to this phase's settings.json-based wiring approach

### Tertiary (LOW confidence)
- None used as load-bearing claims in this document — every substantive
  claim above was either live-verified against this machine's actual state
  or cited to the official Claude Code hooks reference.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — zero new dependencies, entirely reused/verified primitives
- Architecture: HIGH — both host contracts confirmed against live, working, already-installed precedent (not docs alone)
- Pitfalls: HIGH — all four pitfalls are grounded in direct reads of this repo's/machine's actual files, not speculation

**Research date:** 2026-09-09
**Valid until:** 30 days (stable domain — Claude Code hook schema is documented/versioned, `rtk` config format is the only fast-moving piece and is already isolated behind defensive parsing per Pitfall 3)
