---
name: ai-kit-opencode-providers
description: List and remove config-based custom opencode providers from opencode.jsonc (id, npm, baseURL — never apiKey). Use when the user asks to list, show, inspect, or remove a custom opencode provider, mentions the "provider" block in opencode.jsonc, or types "ai-kit-opencode-providers", "list providers", or "remove provider". Does not touch auth.json; adding or editing a provider is out of scope.
---

# ai-kit-opencode-providers

Thin wrapper around `ai-kit-opencode-providers.py`. Invoke the CLI; do not
re-implement listing, removal, or the cross-reference scan in prose.

## Scope

Operates **only** on the `"provider"` object inside `opencode.jsonc`.

Before invoking, distinguish the two provider kinds:

- Config-based custom providers — a `"provider"` block in `opencode.jsonc`.
  This skill lists and removes those.
- Credential-based providers — `auth.json`, already served by
  `opencode auth login` / `list` / `logout`. This skill never reads or
  writes that file.

Adding a provider and editing an existing provider's fields are out of
scope; only full removal is supported. If the user asked to add, edit, or
log in, stop and say so — do not stretch `remove` into those jobs.

## Resolve the entrypoint

Resolve once per invocation, in one Bash call, and record the printed path as
a **literal absolute path** — each Bash call starts a fresh shell, so a
variable assigned here is gone by the next call.

Candidates, in order:

```bash
for d in "${CLAUDE_PLUGIN_ROOT:+$CLAUDE_PLUGIN_ROOT/skills/ai-kit-opencode-providers}" \
         "$HOME/.claude/skills/ai-kit-opencode-providers" \
         "${XDG_CONFIG_HOME:-$HOME/.config}/opencode/skills/ai-kit-opencode-providers" \
         "$HOME/.agents/skills/ai-kit-opencode-providers" \
         "$(dirname "<absolute path to THIS SKILL.md>")"; do
  [ -f "$d/ai-kit-opencode-providers.py" ] && { printf '%s\n' "$d/ai-kit-opencode-providers.py"; break; }
done
```

Substitute the directory containing this SKILL.md for the fifth candidate
(used when the skill is invoked from a checkout). The resolved script is
`ai-kit-opencode-providers.py` in that directory. If no candidate exists,
stop and report that the skill is not installed.

## Config discovery

Default path (D-05):

`${OPENCODE_CONFIG_DIR:-${XDG_CONFIG_HOME:-$HOME/.config}/opencode}/opencode.jsonc`

`--config PATH` takes the full path to the **file**, not to a directory.

## Subcommands

### `list [--config PATH]`

```bash
python3 "$TOOLS_PY" list --config /tmp/scratch/opencode.jsonc
```

`$TOOLS_PY` is the literal absolute path recorded from the resolution block.

Example output:

```
ID           NPM                        BASE URL
demo-router  @ai-sdk/openai-compatible  https://demo.invalid/v1
note: "legacy" is a provider entry whose value is not an object — not a config-based provider, not listed above
```

Columns are `ID`, `NPM`, `BASE URL`. There is no apiKey column. A missing
`npm` or `baseURL` renders as `-`. If the file has no config-based
providers, the CLI prints a single line
`no config-based providers found in PATH` — report that and stop; do not
invent rows.

### `remove <id> [--config PATH]`

```bash
python3 "$TOOLS_PY" remove demo-router --config /tmp/scratch/opencode.jsonc
```

Example output (id referenced in more than one source; removal still happens):

```
cross-reference: /tmp/scratch/.aikit/review-spec.toml scanned
cross-reference: /tmp/scratch/.config/ai-kit/review-spec.toml scanned-inactive
cross-reference: /tmp/scratch/.cache/ai-kit/spec/model-catalog.json scanned
warning: "demo-router" is referenced in /tmp/scratch/.aikit/review-spec.toml: demo-reviewer model=demo-router/demo-model
warning: "demo-router" is referenced in /tmp/scratch/.config/ai-kit/review-spec.toml: global-reviewer model=demo-router/demo-model (not active: local review-spec sets strategy = "local-only")
warning: "demo-router" is referenced in /tmp/scratch/.cache/ai-kit/spec/model-catalog.json: demo-router/demo provider=demo-router
removed provider "demo-router" from /tmp/scratch/opencode.jsonc
```

Clean no-op (id not present):

```
no provider "no-such-id" in /tmp/scratch/opencode.jsonc — nothing to remove
```

Non-object value (key is present; this is **not** the same as absent):

```
provider "legacy" in /tmp/scratch/opencode.jsonc is not a config-based provider (its value is not an object) — nothing removed
```

## Cross-reference warning

Informational and **never blocks** (D-04). The tool prints which sources it
scanned, prints one warning line per referencing location, and removes the
provider either way. No prompt, no `--force`.

Three scanned sources, in order:

1. Local `./.aikit/review-spec.toml` (relative to the process cwd)
2. Global `${XDG_CONFIG_HOME:-$HOME/.config}/ai-kit/review-spec.toml`
3. Cached catalog `${XDG_CACHE_HOME:-$HOME/.cache}/ai-kit/spec/model-catalog.json`

A hit in the **global** review-spec tier is reported with a "not active"
qualifier when the local review-spec sets `strategy = "local-only"`, because
`cfg_resolve` skips the global tier entirely under that strategy — a warning
naming the global file does not by itself mean the referencing reviewer is
live.

Matching is **substring**-based and informational. A provider id that is also
a runtime name — `opencode` or `codex`, say — matches the `cli` field of every
reviewer configured for that runtime, producing warnings that have nothing to
do with the provider being removed. That is expected; it never blocks
removal. Read the named field and locator to judge each line. Over-warning is
the deliberate direction for a non-blocking check.

## Exit codes

- `0` — success, including the clean no-op (`no provider "ID" in PATH — nothing to remove`) and the non-object report (`is not a config-based provider (its value is not an object) — nothing removed`).
- `1` — `OSError` (or a non-UTF-8 read) during the read or the write. One `error:` line on stderr; config untouched.
- `2` — config file missing (`error: no opencode config at PATH` on
  stderr). Report the path and stop; never create the file.

## Edge cases

- Comments survive a removal. Only the provider's own key..value span and one
  comma are deleted.
- Duplicate ids: `remove` deletes the first match; a second invocation
  deletes the other.
- A `provider` child whose value is not an object (for example a hand-edited
  `"legacy": "a-string"`) is not a config-based provider. `list` shows it in a
  `note:` line rather than as a row; `remove` reports that its value is not
  an object and removes nothing, exiting 0. This is **not** the same answer
  as "that id is not in your config" — the key is in the file.

## NEVER

- Never hand-edit `opencode.jsonc` to do what `remove` does — the scanner
  preserves comments, commas, and unrelated bytes; a hand edit does not.
- Never run this against the user's real config to "check that it works" —
  use a copy.
- Never surface an apiKey value in any summary you write back to the user.
  `list` has no such column; do not invent one from the file.
- Never touch `auth.json`.
- Never present the cross-reference result as proof that nothing else
  references the provider when a source was reported `absent` — that source
  was not scanned because it was not there.
- Never relay a `scanned-inactive` global-tier hit to the user as an active
  reviewer.
- Never relay a "its value is not an object" result to the user as "that
  provider is not in your config" — the key **is** in their file.
- Never present a substring match on a `cli` field as proof that the reviewer
  uses the provider being removed. A provider id that is also a runtime name
  matches every reviewer configured for that runtime.
