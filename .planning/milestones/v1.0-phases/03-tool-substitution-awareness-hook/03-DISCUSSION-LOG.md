# Phase 3: Tool-Substitution Awareness Hook - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-09-08
**Phase:** 3-Tool-Substitution Awareness Hook
**Areas discussed:** Detection signal source mismatch, "Genuinely active" verification depth, Message composition content, Hook wiring mechanics, plus a freeform scope-safety concern raised before area selection

---

## Scope-safety concern (raised as "Other" during area selection)

The user's freeform addition to the area-selection question: "For rtk, we
need to be careful — is it really feasible to add extra messages hinting
agents how rtk works and warning about truncation, without breaking commands'
expected output from the agents?"

**Resolution:** Clarified that `REQ-tool-substitution-hook-wiring`'s
`SessionStart` hook delivers content via `hookSpecificOutput.additionalContext`
— a context channel entirely separate from any tool's stdout, fired only on
`startup`/`compact`, never during command execution. It cannot alter command
output.

| Option | Description | Selected |
|--------|-------------|----------|
| Resolved — SessionStart-only as stated in the REQ | The separate-channel mechanism can't break command output; nothing more needed | ✓ |
| Add per-command hints as a deferred idea | Capture per-command truncation warnings (PreToolUse/PostToolUse) as a deferred idea | |

**User's follow-up:** Noted `rtk` is third-party — we must avoid touching its
own hooks — and proposed two mechanisms: one explaining how `rtk` works, one
explaining our own advice/replace mechanism.

**Resolution:** Clarified this is one hook with two message parts, not two
hooks. `settings.json`'s `hooks.SessionStart` array supports multiple
independent entries; `rtk` already registers its own (confirmed via
`rtk init --show`); our new entry is additive, never edits `rtk`'s.

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, both parts | Message includes both the active-substitutions briefing and a provenance note distinguishing it from rtk's own hook | ✓ |
| Part A only | Only the active-substitutions briefing | |

---

## Detection signal source mismatch / "Genuinely active" verification depth

**Investigation:** Verified directly against the installed `rtk` v0.44.1 (not
assumed from the PRD) that `registry.toml`/`audience` — the mechanism
`REQ-tool-substitution-detection-composition` literally names — does not
exist. Checked `rtk config`, `rtk gain`, `rtk --help`, and the filesystem;
found only `config.toml`/`filters.toml`, no `audience` concept.

| Option | Description | Selected |
|--------|-------------|----------|
| Own curated list + binary in PATH + rtk init --show hook active | ai-kit's own curated 5-pair list (already established in REQUIREMENTS.md) × binary presence × rtk hook confirmed active | ✓ |
| Binary in PATH only | Ignore rtk's hook-active state | |

**User's choice:** curated list + binary presence + hook-active check
(recommended option). Confirmed this also resolves the separately-selected
"Genuinely active verification depth" area — same underlying decision.

---

## Message composition content (extended discussion)

The user interrupted the initial tone/length question with a substantive
correction: two distinct things were being conflated under "message
composition" — (1) whether `rtk` itself already advises the agent about its
own output-compression behavior, requesting research via
`github.com/rtk-ai/rtk#how-it-works`; and (2) a separate, new idea — ai-kit's
own guidance on using modern tools directly with the right flags, built as a
catalog at first `SessionStart`, cached, consulted (not rechecked) at
`PreToolUse`.

**Research performed:** Directly against the locally-installed `rtk` v0.44.1
(live verification, per project's core value) rather than only the README:
- `rtk` already self-annotates truncation per-invocation, inline in its own
  output (e.g. `+114 more in tools/status-line.py [see remaining: tail -n
  +26 ...]`) — self-explanatory already.
- `rtk hook claude` is a `PreToolUse` hook that transparently rewrites
  certain Bash tool calls (`grep`→`rtk grep` etc.) — this rewriting is what's
  actually invisible to the agent, confirmed by the user's own `RTK.md`
  ("transparent, 0 tokens overhead").

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, focus on the transparent rewriting | Session-start message focuses on the invisible rewriting fact, not truncation mechanics (already self-documented per-command) | ✓ |
| Explain both | Also explain truncation mechanics even though redundant | |

**Follow-up on caching/PreToolUse:**

| Option | Description | Selected |
|--------|-------------|----------|
| Future design note only — don't build PreToolUse now | Keep the confirmed SessionStart-only scope; capture the cache-consulted-at-PreToolUse idea as a deferred idea | (initial framing) |
| Yes, add a new PreToolUse hook to this phase | Expand REQ-tool-substitution-hook-wiring's scope | |

**User's actual answer:** Asked for clarification on whether "our own
grep→rg mechanism" runs via a different, non-hook mechanism, or is already
contemplated — wanting to know before deciding to drop/defer.

**Final clarification:** Both message parts (transparent-rewrite notice and
modern-tool-usage guidance) are delivered via the SAME SessionStart hook
message, computed once per session — there is no PreToolUse mechanism
anywhere in this phase's scope for either part.

| Final option | Description | Selected |
|--------|-------------|----------|
| Yes, confirmed | One hook, one message, two sections; PreToolUse-cache idea deferred | ✓ |
| No, I want to reconsider the scope | Reopen the scope discussion | |

**User's final choice:** Confirmed — one SessionStart hook, two-part message,
no PreToolUse in this phase.

---

## Hook wiring mechanics

**Trade-off analysis presented:** new `tools/hooks/` script (stdlib-only) +
append-if-absent wiring into `hooks.SessionStart`, vs. an alternative
approach.

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, confirmed | New stdlib-only script in tools/hooks/; append-if-absent to hooks.SessionStart array, reusing _read_json/_write_json, never touching rtk's own entry | ✓ |
| Different approach | User proposes something different | |

**User's choice:** confirmed (recommended option).

---

## Claude's Discretion

None — every gray area had an explicit user decision.

## Deferred Ideas

- **Real-time PreToolUse enforcement mechanism** — a genuine `PreToolUse`
  hook consulting a `SessionStart`-built cache to actively suggest/enforce
  modern-tool usage per-command. Raised mid-discussion; explicitly out of
  this phase's scope (`REQ-tool-substitution-hook-wiring` is
  `SessionStart`-only). Candidate for a future phase.
