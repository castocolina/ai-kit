# Phase 3: Tool-Substitution Awareness Hook - Context

**Gathered:** 2026-09-08
**Status:** Ready for planning

<domain>
## Phase Boundary

Claude Code sessions start with an accurate, live-verified briefing about
which `rtk`-driven tool substitutions are genuinely active on this machine,
delivered via a new `SessionStart` hook firing on `"startup"` and `"compact"`.
The hook composes a message with two distinct parts — (1) a notice that
`rtk`'s own `PreToolUse` hook transparently rewrites certain Bash tool calls,
and (2) guidance on using the available modern tools directly with the right
flags — injected via `hookSpecificOutput.additionalContext`, a context
channel entirely separate from any tool's stdout. The hook degrades
gracefully (no error, no perceptible delay) when `rtk`/`tools-installer` is
absent, and never touches `rtk`'s own hook registration.

</domain>

<decisions>
## Implementation Decisions

### Scope and safety boundary
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

### Message composition — two parts, one message
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

### Detection signal source (corrects REQ's literal wording)
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

### Hook wiring mechanics
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

### Amendment (2026-09-08, during Phase 4 discussion)
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

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Source PRD and synthesized intel
- `docs/prds/ai-kit-tool-substitution-awareness-hook-v1.0-prd.md` — the
  proposal PRD this phase implements; note D-06 corrects one of its
  assumptions (`registry.toml`/`audience`) against live verification
- `.planning/intel/requirements.md` — synthesized requirement detail
- `.planning/REQUIREMENTS.md` §Tool-Substitution Awareness Hook —
  REQ-tool-substitution-detection-composition, REQ-tool-substitution-hook-wiring
- `.planning/ROADMAP.md` §Phase 3 — success criteria this phase must make true
- `.planning/PROJECT.md` — core value (never claim more certainty than
  verified) directly drove D-06's correction; constraints (confidence
  labeling, runtime dependency discipline)

### Third-party tool documentation (external, not a repo path)
- `github.com/rtk-ai/rtk` (`#how-it-works` section referenced by the user) —
  the researcher/planner should still read this for full mechanism detail;
  this discussion's D-03/D-06 findings were verified directly against the
  locally-installed `rtk` binary (v0.44.1) rather than the docs, since the
  docs may not reflect exactly what's installed

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `tools/setup.py::_read_json()` / `_write_json()` (line ~1332): JSON
  read/write primitives to reuse for D-08's settings.json wiring.
- `tools/setup.py::wire_statusline()` (line ~1340): the closest existing
  precedent for "wire something into settings.json, guard against a foreign
  value" — but its overwrite-a-scalar-key logic does NOT directly apply here;
  `hooks.SessionStart` is an array requiring append-if-absent, not overwrite.

### Established Patterns
- `tools/status-line.py`: stdlib-only script pattern to follow for the new
  `tools/hooks/` script (D-07) — no `uv`/PEP-723 dependency declaration,
  consistent with the runtime-dependency-discipline constraint reaffirmed in
  Phase 2's discussion.
- `rtk init --show` output shape (locally verified):
  ```
  [ok] Hook: rtk hook claude (native binary command)
  [ok] RTK.md: /home/bazzite/.claude/RTK.md (slim mode)
  [ok] settings.json: RTK hook configured
  ```
  Parsing the `[ok] Hook: rtk hook claude` line (or equivalent `[--]` absence)
  is the mechanism for D-06's "is rtk's hook active" check.
- `rtk`'s self-truncation-annotation format (locally verified, one real
  example): `+114 more in tools/status-line.py [see remaining: tail -n +26
  ~/.local/share/rtk/tee/1788891192_grep_0_tools_status_line_py.log]` —
  confirms D-03's finding that truncation is already self-documented
  per-invocation.

### Integration Points
- `~/.claude/settings.json`'s `hooks.SessionStart` array is the sole
  integration point for D-02/D-08 — must coexist with `rtk`'s own entry
  there.
- `tools/install.sh` / `tools/setup.py` install flow is where the new hook
  script gets wired in, alongside the existing `wire_statusline()` call.

</code_context>

<specifics>
## Specific Ideas

- The user asked to research `github.com/rtk-ai/rtk#how-it-works` directly;
  this discussion instead verified live against the actually-installed `rtk`
  v0.44.1 binary (more authoritative than docs per the project's own core
  value of live verification) — planner/researcher should still consult the
  README for anything not directly observable locally.
- The two-part message structure (transparent-rewrite notice + modern-tool
  guidance) and the "why" behind each part came directly from a real
  back-and-forth where the user first worried about breaking command output
  (resolved: additionalContext is a separate channel), then proposed two
  mechanisms (clarified: one hook, two message sections), then asked about
  caching architecture (clarified/deferred: no PreToolUse in this phase).

</specifics>

<deferred>
## Deferred Ideas

- **Real-time PreToolUse enforcement mechanism**: a genuine `PreToolUse` hook
  that intercepts each Bash tool call and consults a cache built at
  `SessionStart` to actively suggest/enforce modern-tool usage per-command,
  rather than a one-time session-start briefing. Raised by the user mid-
  discussion; explicitly ruled out of this phase's scope (D-01) —
  `REQ-tool-substitution-hook-wiring` only covers `SessionStart` on
  `startup`/`compact`. Belongs in a future phase if real-time per-command
  intervention is ever wanted.

### Reviewed Todos (not folded)
None — no matching todos found (`todo_count: 0` for Phase 3).

</deferred>

---

*Phase: 3-Tool-Substitution Awareness Hook*
*Context gathered: 2026-09-08*
