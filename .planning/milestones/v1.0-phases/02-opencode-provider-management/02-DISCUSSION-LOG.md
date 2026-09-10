# Phase 2: Opencode Provider Management - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-09-08
**Phase:** 2-Opencode Provider Management
**Areas discussed:** Skill invocation surface, JSONC surgical-edit approach, Cross-reference warning UX, opencode.jsonc discovery

---

## Skill invocation surface

**Trade-off analysis presented:** argparse-style CLI subcommands vs.
natural-language-only skill vs. both (CLI module + SKILL.md wrapper).

| Option | Description | Selected |
|--------|-------------|----------|
| CLI module + SKILL.md wrapper | Matches ai-kit-spec-review's cli.py + SKILL.md pairing | ✓ |
| Natural-language-only skill | No formal CLI, SKILL.md prose drives logic | |

**User's choice:** CLI module + SKILL.md wrapper (recommended option).

---

## JSONC surgical-edit approach

**Trade-off analysis presented:** hand-rolled stdlib scanner vs.
`json.loads`/`dumps` roundtrip vs. third-party JSONC library.

| Option | Description | Selected |
|--------|-------------|----------|
| Hand-rolled scanner (stdlib-only) | Preserves every byte outside the touched block; no dependency | (initial answer: no) |
| Third-party JSONC library | Handles edge cases; new dependency, conflicts with stdlib-only constraint | (initial answer: yes) |

**User's first answer:** Asked a clarifying question — "What's the risk of a
new dependency? We already have `textual` in pyproject.toml — is that
runtime or dev-only? I haven't tested the curl install in a clean
environment without Python, not sure what would happen." — then, after my
explanation of the existing `ensure_rich_runtime()`/`_textual_importable()`
guard+re-exec+fail-closed pattern, explicitly chose **"replicate the
guard+uv-run pattern"** and, on a follow-up, picked **jsonc-parser (or a
format-preserving equivalent)** as the PEP-723 dependency.

**Follow-up block boundary question:**

| Option | Description | Selected |
|--------|-------------|----------|
| Locate the id's string-literal key + balanced-brace value | Finds the key, counts balanced braces respecting strings/escapes, removes key+value+correct comma | ✓ |
| Line-position search | Assume each provider occupies a contiguous line range | |

**User's choice:** balanced-brace key/value location (recommended option) — unaffected by the dependency back-and-forth below.

**Reconsideration:** The user then pushed further — asking whether the
existing `ensure_rich_runtime()` fail-closed path is actually verified in a
truly clean/dockerized environment (no e2e test target found; only unit
tests with `_textual_importable` mocked False), and separately proposed that
the installer *should* offer to auto-install missing pieces rather than fail
closed. After verifying the test coverage (confirmed: no clean-container e2e
test exists) and clarifying that the auto-install idea is a change to the
*existing* wizard, out of this phase's scope, the user was asked directly:

| Final option | Description | Selected |
|--------|-------------|----------|
| Revert to hand-rolled scanner, stdlib-only | No new dependency, no unverified-clean-environment risk, fits the CLI/scriptable invocation decided above | ✓ |
| Keep jsonc-parser + guard+uv-run pattern | Accept the same unverified risk the wizard already carries | |

**User's final choice:** Hand-rolled scanner, stdlib-only — **supersedes**
the earlier "replicate guard+uv-run" answer.
**Notes:** The installer auto-install-missing-deps idea was captured as a
Deferred Idea (see CONTEXT.md), not acted on in this phase.

---

## Cross-reference warning UX

**Trade-off analysis presented:** soft-confirm (y/n) vs. FYI-only, non-blocking.

| Option | Description | Selected |
|--------|-------------|----------|
| FYI only, non-blocking | Matches REQ's literal "non-blocking" wording; consistent with CLI/scriptable invocation | ✓ |
| Soft-confirm interactive | y/n prompt before removing when references found | |

**User's choice:** FYI only, non-blocking (recommended option).

---

## opencode.jsonc discovery

**Trade-off analysis presented:** auto-discover + `--config` override vs.
`--config`-only vs. auto-discover only.

| Option | Description | Selected |
|--------|-------------|----------|
| Auto-discover (`OPENCODE_CONFIG_DIR`/XDG convention) + `--config` override | Matches the exact convention already used in this repo's own GSD workflow scripts; override for non-standard locations | ✓ |
| `--config`-only | No auto-discovery, always explicit | |

**User's choice:** Auto-discover + `--config` override (recommended option).

---

## Claude's Discretion

None — every gray area had an explicit user decision.

## Deferred Ideas

- **Installer auto-install-missing-deps UX** — raised by the user while
  reconsidering the JSONC-editor dependency choice; belongs to a future
  phase/PRD about the installer's wizard bootstrap, not Opencode Provider
  Management.
