# Phase 2: Opencode Provider Management - Research

**Researched:** 2026-09-09
**Domain:** Local CLI tool — surgical text editing of a live JSONC config file (opencode's `provider` block), plus read-only cross-reference scanning of a TOML file and a JSON cache
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** `ai-kit-opencode-providers` is a CLI module (argparse-style
  `list`/`remove <id>` subcommands, testable) with a `SKILL.md` wrapper that
  documents and invokes it — the same shape as `ai-kit-spec-review`'s
  `ai_kit_spec/cli.py` + `SKILL.md` pairing already in this repo.
- **D-02:** The editor is a **hand-rolled, stdlib-only character scanner** —
  no external JSONC library, no PEP-723-declared dependency, no `uv run`
  re-exec pattern. It tracks quote/escape state and brace depth to preserve
  every byte outside the removed provider's block (comments, formatting,
  other providers stay byte-identical).
  — **Reversibility:** reversible — an internal implementation choice with no
  external contract; a future swap to a library wouldn't change the skill's
  CLI surface.
- **D-03:** Block boundaries are found by locating the id's string-literal
  key inside the `"provider"` object, then counting balanced braces from the
  `{` that follows it to its matching closing `}` (respecting strings and
  escapes) — the whole key+value plus the correct adjacent comma is what gets
  removed.
- **Rejected alternative and why:** a library-backed approach
  (`jsonc-parser`-equivalent) behind the same `guard + uv run re-exec +
  fail-closed` pattern `tools/setup.py`'s `ensure_rich_runtime()` already
  uses for `textual` was considered and explicitly **rejected** after
  investigation. Verified facts that drove the rejection: `install.sh` execs
  `python3 tools/setup.py` directly (no `uv run`); `ensure_rich_runtime()`'s
  fail-closed path is covered only by **unit tests with
  `_textual_importable` mocked False** — no Docker/container e2e test exists
  proving the pattern actually works in a genuinely clean environment (no
  `uv`, no pre-installed dependency). Unlike the wizard (an explicitly
  interactive, TTY-driven feature with a real rich-UI justification), this
  skill is meant to be invoked non-interactively/scriptable (per D-01) — the
  unverified dependency-availability risk was judged not worth taking for an
  operation with no interactive-UI justification. The stdlib-only scanner
  sidesteps the risk entirely rather than inheriting it.
- **D-04:** The pre-removal cross-reference check is printed as an
  **informational warning only** — removal proceeds automatically with no
  additional confirmation prompt. Matches REQ-opencode-provider-cross-reference-check's
  literal "non-blocking" wording and is required for consistency with D-01
  (a CLI/scriptable skill can't depend on an interactive y/n gate).
- **D-05:** The skill auto-discovers `opencode.jsonc` at
  `${OPENCODE_CONFIG_DIR:-${XDG_CONFIG_HOME:-$HOME/.config}/opencode}/opencode.jsonc`
  by default — the exact env-var/XDG convention already used by this repo's
  own GSD workflow scripts — with a `--config <path>` flag as an explicit
  override for non-standard locations. (See Assumption A1 below — the
  "already used by this repo's own GSD workflow scripts" provenance claim
  could not be re-verified this session, but the convention itself is
  independently confirmed correct against opencode's own docs.)

### Claude's Discretion

None — every gray area in this phase had an explicit user decision, per
CONTEXT.md's own statement.

### Deferred Ideas (OUT OF SCOPE)

- **Installer auto-install-missing-deps UX**: instead of `ensure_rich_runtime()`
  failing closed with just an error message when `uv`/`textual` aren't
  available, the installer could offer to install them for the user. Raised
  by the user during Phase 2's JSONC-dependency discussion, but it's a change
  to the *existing*, already-shipped wizard bootstrap behavior
  (`tools/setup.py`), not part of Opencode Provider Management's scope.
  Belongs in its own future phase/PRD for installer UX improvements.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| REQ-opencode-provider-list-remove | New `ai-kit-opencode-providers` skill lists custom providers from `opencode.jsonc`'s `"provider"` block (id/npm/baseURL, never apiKey) and removes one by id via a string-literal-aware, brace-counting, byte-preserving, atomically-written edit; a non-existent id no-ops cleanly. | Real `opencode.jsonc` schema verified live (Code Examples); atomic-write precedent (`write_toml_preserving`) located with gap analysis (Pitfall 2); brace-counting scope and its comment-awareness gap analyzed (Pitfall 1, Anti-Patterns); comma-handling and id-anchoring edge cases enumerated (Pitfalls 3-4) |
| REQ-opencode-provider-cross-reference-check | Before removing a provider, warn (non-blocking) if its id is referenced in `.aikit/review-spec.toml` or the cached model catalog; `skills/ai-kit-opencode-providers/SKILL.md` documents both subcommands and passes `skill-judge` review. | Real `.aikit/review-spec.toml` schema verified live; cached-catalog path and entry schema verified from source (`model_catalog.py`); self-contained vs. cross-import tradeoff analyzed (Pattern 3, Alternatives Considered, Assumption A2); `skill-judge` gate flagged as a Wave 0 test-map item (manual-only) |
</phase_requirements>

## Summary

This phase builds a small, fully stdlib Python CLI (`list`/`remove <id>`) that
surgically edits `opencode.jsonc`'s `"provider"` object without a JSONC
parsing library. Every design decision (D-01 through D-05) is already locked
in `02-CONTEXT.md` — this research verifies the concrete data this phase
operates on (the real, live `opencode.jsonc` schema on this machine, the real
`.aikit/review-spec.toml` schema, and the real cached-catalog schema), locates
the exact in-repo precedents for the two things D-01/D-02 say to replicate
(atomic write, CLI-module + `SKILL.md` pairing), and surfaces three concrete
gaps CONTEXT.md's decisions do not yet cover: (1) JSONC's comment syntax means
the brace-counting scanner needs comment-awareness, not just the
string/escape-awareness D-03 names; (2) `tempfile.mkstemp`'s default file mode
(0600) silently downgrades `opencode.jsonc`'s current 0644 permission unless
the write path explicitly preserves it; (3) whether the new skill takes a hard
runtime dependency on `ai-kit-spec-review` being installed (the `sys.path`
cross-import precedent) or stays self-contained (the recommended default,
since the catalog/`XDG_CACHE_HOME` path convention is trivial to replicate
locally and PRD language treats the catalog as optional/best-effort anyway).

**Primary recommendation:** Build `skills/ai-kit-opencode-providers/` as a
new, self-contained `ai_kit_opencode_providers/` package (own `cache.py`-style
~10-line path/JSON helpers, no cross-import from `ai-kit-spec-review`),
mirroring `ai_kit_spec/cli.py`'s argparse-subcommand shape and
`write_toml_preserving`'s atomic-write shape, with a brace-counting scanner
that tracks **four** states (in-string, after-escape, in-line-comment,
in-block-comment) rather than the two D-03 names, and an explicit
`os.chmod(tmp, os.stat(original).st_mode)` before the atomic rename.

## Architectural Responsibility Map

This phase has no browser/server tiers — it is a single-process local CLI
operating on the filesystem. Tiers below are adapted to that shape.

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| `list`/`remove <id>` subcommand dispatch | CLI Entry Point | — | argparse-based, mirrors `ai_kit_spec/cli.py`'s `main(argv, ...)` shape (D-01) |
| Provider-block locate/remove (brace counting) | Core Logic (pure) | — | No file I/O in the function itself (PRD "Key Components"); independently unit-testable |
| Cross-reference scan (review-spec.toml + catalog) | Core Logic (pure) | Filesystem/Config I/O | Reads two already-established data sources; returns a pure list of matches, printed by the CLI layer |
| Atomic file write (temp + rename) | Filesystem/Config I/O | — | `tempfile.mkstemp` (same dir) + `os.replace`, same pattern as `tools/setup.py::write_toml_preserving` |
| `SKILL.md` documentation/invocation wrapper | Skill Wrapper | — | Thin doc layer over the CLI module (D-01), no logic of its own |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `argparse` | stdlib | `list`/`remove <id>` subcommand parsing | Exact shape `ai_kit_spec/cli.py::main()` already uses across ~20 subcommands `[VERIFIED: skills/ai-kit-spec-review/ai_kit_spec/cli.py:489-490]` |
| `tomllib` | stdlib (3.11+) | Read `.aikit/review-spec.toml` for the cross-reference check | Already the sole TOML reader in this repo; guarded import pattern already established `[VERIFIED: skills/ai-kit-spec-review/ai_kit_spec/config_io.py:1-7]` — `try: import tomllib except ModuleNotFoundError: tomllib = None` |
| `json` | stdlib | Read the cached model-catalog JSON | `cache_read_json` in the sibling skill is a 5-line tolerant wrapper (`open` → `json.load`, catches `OSError`/`json.JSONDecodeError`) `[VERIFIED: skills/ai-kit-spec-review/ai_kit_spec/cache.py:13-18]` — trivial to replicate locally, not worth a cross-skill import |
| `tempfile` + `os` | stdlib | Atomic write (`mkstemp` same-dir temp + `os.replace`) | Exact pattern already proven twice in this repo: `write_toml_preserving` `[VERIFIED: tools/setup.py:442-459]` and `cache_write_json` `[VERIFIED: skills/ai-kit-spec-review/ai_kit_spec/cache.py:21-29]` |
| `re` | stdlib | (optional) locating the `"<id>":` key pattern before hand-scanning braces | Only for the initial key search, not for brace/string/comment state tracking (that must be a manual character scan per D-02) |

**No external packages.** D-02 explicitly locks a stdlib-only, hand-rolled
scanner — no `json5`/`commentjson`/`jsonc-parser`-class dependency. This
matches `PROJECT.md`'s "Runtime dependency discipline" constraint
(stdlib-only shipped code) `[VERIFIED: .planning/PROJECT.md:130-132]`.

### Supporting

None — this phase needs no packages beyond stdlib.

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Hand-rolled brace-counting scanner | A JSONC-aware library (`jsonc-parser`-equivalent) | Already investigated and **rejected** in CONTEXT.md's D-02 — see its "Rejected alternative and why" for the full reasoning (the `guard + uv-run re-exec` fail-closed pattern this would require is only unit-tested with mocks, not verified dependency-free) |
| Self-contained cache/TOML helpers | Cross-import `ai_kit_spec.cache`/`ai_kit_spec.model_catalog` via a `sys.path` shim (the `ai-kit-spec-gsd` precedent) | Cross-import couples this skill's install-time correctness to `ai-kit-spec-review` being installed as a sibling directory (that skill's own `SKILL.md` fails closed on this: *"ai-kit-spec-review's own ai-kit-spec.py module is missing"* `[VERIFIED: skills/ai-kit-spec-config/SKILL.md:61-64]`); the catalog is documented as optional/best-effort input in this phase's own PRD (*"if present"*), so a hard install-order dependency for an optional check is not justified — replicate the ~10-line path/read helpers locally instead |

**Installation:** none — nothing to install.

**Version verification:** N/A — no packages to check against a registry.

## Package Legitimacy Audit

**N/A — this phase installs no external packages.** D-02 locks a stdlib-only
implementation; the Package Legitimacy Gate protocol does not apply. If a
future task in this phase's plan considers adding a dependency, that decision
must go back through discuss-phase — it directly contradicts a locked
decision and `PROJECT.md`'s stated constraint.

## Architecture Patterns

### System Architecture Diagram

```
                         ┌─────────────────────────────┐
                         │  ai-kit-opencode-providers   │
                         │  SKILL.md  (thin doc wrapper)│
                         └──────────────┬───────────────┘
                                        │ invokes
                                        ▼
                    ┌───────────────────────────────────────┐
                    │  CLI entry point (argparse)            │
                    │  list | remove <id> [--config PATH]    │
                    └───────────────┬─────────────────────────┘
                                    │
             ┌──────────────────────┼───────────────────────────┐
             ▼                      ▼                            ▼
  ┌────────────────────┐ ┌───────────────────────┐   ┌─────────────────────────┐
  │ Discover config path │ │ Read opencode.jsonc    │   │ Cross-reference scan    │
  │ (D-05 default/--config)│ (raw text, not parsed) │   │ (remove only)           │
  └──────────┬───────────┘ └──────────┬─────────────┘   └───────────┬─────────────┘
             │                        │                             │
             │                        ▼                             ▼
             │           ┌────────────────────────────┐  ┌───────────────────────────┐
             │           │ Locate "provider"."<id>":{} │  │ .aikit/review-spec.toml   │
             │           │ block (brace/string/comment │  │ (tomllib, [[reviewers]]   │
             │           │ -aware scanner)              │  │ cli/model fields)         │
             │           └──────────────┬───────────────┘  └─────────────┬─────────────┘
             │                          │                                 │
             │        list ◄────────────┤                                 ▼
             │        (id/npm/baseURL,  │                    ┌───────────────────────────┐
             │        never apiKey)     │                    │ $XDG_CACHE_HOME/ai-kit/    │
             │                          │ remove              │ spec/model-catalog.json    │
             │                          ▼                    │ (provider / runtimes.*.    │
             │           ┌────────────────────────────┐      │ model_id substring match)  │
             │           │ Excise block + adjacent      │      └─────────────┬─────────────┘
             │           │ comma; rest of file untouched│                    │
             │           └──────────────┬───────────────┘◄───────────────────┘
             │                          │                  (warning text, non-blocking)
             │                          ▼
             │           ┌────────────────────────────┐
             └──────────►│ Atomic write: mkstemp (same  │
                         │ dir) + chmod(orig mode) +    │
                         │ os.replace                   │
                         └────────────────────────────┘
```

A reader can trace `remove <id>` end to end: CLI → locate config path → read
raw bytes → locate+excise the target block → (in parallel, informational)
scan the two cross-reference sources and print warnings → atomically write
the result back, regardless of whether a cross-reference was found.

### Recommended Project Structure

```
skills/ai-kit-opencode-providers/
├── SKILL.md                              # thin wrapper; documents list/remove, example output
├── ai-kit-opencode-providers.py          # entrypoint shim (mirrors ai-kit-spec.py)
└── ai_kit_opencode_providers/
    ├── __init__.py
    ├── cli.py                            # argparse: list, remove
    ├── jsonc_edit.py                     # pure: locate_provider_block(), remove_provider()
    ├── cross_reference.py                # pure: scan_review_spec(), scan_catalog()
    ├── config_paths.py                   # opencode config discovery (D-05) + own cache path helpers
    └── atomic_write.py                   # write_preserving_mode(path, text) — reusable, tested in isolation

tests/
├── test_ai_kit_opencode_providers.py     # new — see Validation Architecture below
└── e2e/docker/fixtures/opencode/
    └── opencode.jsonc                    # new fixture — already planned in the e2e README (see below)
```

### Pattern 1: CLI-module + SKILL.md pairing (D-01)

**What:** A small argparse-based Python CLI module lives inside the skill
directory; `SKILL.md` is a thin instruction wrapper that invokes it by
absolute path and documents its subcommands/output — never re-implements
logic in prose.
**When to use:** Every subcommand this phase needs (`list`, `remove <id>`).
**Example (the exact precedent to replicate):**
```python
# Source: skills/ai-kit-spec-review/ai_kit_spec/cli.py:482-496 (verified read this session)
def main(argv: list, which_fn=shutil.which, run_fn=subprocess.run, ...) -> int:
    import argparse
    parser = argparse.ArgumentParser(prog="review-spec")
    sub = parser.add_subparsers(dest="command", required=True)
    ...
    args = parser.parse_args(argv)
    if args.command == "cache-path":
        ...
        return 0
```
The entrypoint shim (`skills/ai-kit-spec-review/ai-kit-spec.py`) is just:
```python
# Source: skills/ai-kit-spec-review/ai-kit-spec.py (verified, full file, 8 lines)
import sys
from ai_kit_spec.cli import main
if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
```
Replicate this exact two-file shape (`ai-kit-opencode-providers.py` +
`ai_kit_opencode_providers/cli.py`) — Python puts a directly-run script's own
directory on `sys.path[0]` automatically, so the package import resolves
without any path hacking, as long as the entrypoint script and the package
directory are siblings `[VERIFIED: this mechanism is documented inline in
skills/ai-kit-spec-execute-gsd/ai-kit-spec-gsd.py:2-6]`.

### Pattern 2: Atomic write with mode preservation

**What:** Write to a same-directory temp file, then `os.replace()` it over
the target — this makes a crash mid-write leave the *original* file intact
(never a half-written one). Every existing writer in this repo already does
the temp+replace half of this; **none of them explicitly preserves the
original file's permission bits**, which matters uniquely for this phase
because `opencode.jsonc` holds a live API key.
**When to use:** Every `remove <id>` write.
**Example (existing precedent — temp+replace half only):**
```python
# Source: tools/setup.py:442-459 (verified read this session, write_toml_preserving)
fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path) or ".", suffix=".tmp")
try:
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(tmp, path)
except OSError:
    if os.path.exists(tmp):
        os.unlink(tmp)
    return False
```
**Gap this phase must close (not present in the precedent above — see
Pitfall 2):**
```python
# Recommended addition, not found in either existing atomic-write helper
orig_mode = os.stat(path).st_mode
os.chmod(tmp, stat.S_IMODE(orig_mode))
os.replace(tmp, path)
```

### Pattern 3: Sibling-skill dependency resolution (only if the plan chooses cross-import)

**What:** A skill that depends on another skill being installed resolves
that sibling's directory via a fixed three-candidate search
(`CLAUDE_PLUGIN_ROOT`, `~/.claude/skills/<name>`, or a relative sibling of
`SKILL.md`'s own directory), then either subprocess-invokes its CLI
(`ai-kit-spec-config`'s pattern) or `sys.path`-imports its package
(`ai-kit-spec-execute-gsd`'s pattern).
**When to use:** Not recommended for this phase (see Alternatives Considered)
— documented here only because it is a real, established pattern the
planner may reasonably choose instead of the self-contained recommendation.
**Example:**
```python
# Source: skills/ai-kit-spec-execute-gsd/ai-kit-spec-gsd.py (verified, full file)
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_THIS_DIR, "..", "ai-kit-spec-review"))
from ai_kit_spec_gsd.cli import main  # noqa: E402
```

### Anti-Patterns to Avoid

- **Writing a general JSONC parser:** Scope is strictly "locate one known
  top-level object's one immediate-child key, find its matching closing
  brace, delete that span." Do not build a recursive-descent JSONC parser —
  D-02/D-03 deliberately scope this to brace-counting plus string/comment
  skipping, not full parsing.
- **Regex-based brace matching:** Regular expressions cannot correctly
  balance nested braces or track string/comment state across an arbitrary
  file; the scanner must be a linear character walk with explicit state
  (D-03 already specifies this — a regex "shortcut" would violate it).
- **Blind repo-style string search for `"<id>":`:** The id could
  legitimately appear as a *model name* string elsewhere in the same
  provider's `"models"` sub-object (see the real fixture below — model ids
  like `"my-plan-review"` sit one level deeper than the provider id). The
  search must be anchored to immediate children of the `"provider"` object
  only, not any occurrence of the substring in the file.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| TOML parsing | A custom TOML reader | stdlib `tomllib` (guarded import) | Already the established pattern in this repo; TOML is a full grammar, not worth reimplementing for a read-only scan |
| Atomic file replace | A custom fsync/rename dance | `tempfile.mkstemp` (same dir) + `os.replace` | POSIX-guaranteed atomicity on the same filesystem; reinventing this risks a subtly non-atomic "looks fine on my machine" implementation |
| JSON cache read/write | A custom JSON validator/writer | stdlib `json` (`json.load`/`json.dump`), tolerant read (catch `OSError`/`JSONDecodeError`) | The cached catalog is already produced by another skill in exactly this shape; the reader only needs to be tolerant of "missing" and "malformed," nothing more |

**Key insight:** The one genuinely novel piece of logic in this phase is the
brace/string/comment-aware scanner (D-02/D-03) — everything else
(TOML/JSON reads, atomic writes, CLI dispatch) has a direct, verified
precedent already in this codebase. Resist the temptation to also hand-roll
those already-solved pieces; only the scanner is new.

## Common Pitfalls

### Pitfall 1: Brace counter is not comment-aware (only string-aware)

**What goes wrong:** D-03 specifies a scanner that tracks quote/escape state
and brace depth — it does not mention comment state. `opencode.jsonc` is
JSONC, which supports `//` line comments and `/* */` block comments
`[CITED: opencode.ai/v2/docs/config — "OpenCode supports both JSON and JSONC
(JSON with Comments) configuration files"]`. A `{` or `}` character inside a
comment (e.g. `// old provider config { was here }`) would desynchronize a
scanner that only tracks strings, either truncating the removed block early
or consuming bytes past the real closing brace — both corrupt the file, and
the corruption would be silent (no exception) if the truncated/extended
region still happens to parse as syntactically valid-looking text.
**Why it happens:** "JSONC" and "JSON" are easy to conflate; D-02/D-03's
wording ("respecting strings and escapes") is accurate for JSON but
incomplete for JSONC.
**How to avoid:** The scanner must track (at minimum) four states while
walking forward from the target's opening `{`: in-string, after-backslash
(next char is escaped), in-line-comment (`//` until `\n`), in-block-comment
(`/*` until `*/`). Only count `{`/`}` toward depth when in none of the
comment/string states.
**Warning signs:** A test fixture with a comment containing a literal `{` or
`}` character placed between two provider entries is the direct way to catch
this — the PRD's own acceptance criteria already requires a
braces-inside-**string** fixture; a braces-inside-**comment** fixture should
be added alongside it, since it is a distinct failure mode.

### Pitfall 2: Atomic write silently changes the file's permission bits

**What goes wrong:** `tempfile.mkstemp()` creates its temp file with mode
`0600` by default — confirmed on this machine `[VERIFIED: python3 -c
"tempfile.mkstemp"; live check this session, printed 0o600]`, while the real
`opencode.jsonc` on this machine is mode `0644` `[VERIFIED: stat -c "%a"
~/.config/opencode/opencode.jsonc; live check this session, printed 644]`.
Neither existing atomic-write helper in this repo
(`write_toml_preserving` `[VERIFIED: tools/setup.py:442-459]`,
`cache_write_json` `[VERIFIED: skills/ai-kit-spec-review/ai_kit_spec/cache.py:21-29]`)
calls `os.chmod` on the temp file before `os.replace` — both would silently
tighten the target file's permissions to `0600` on every write, an
unannounced side effect. For a config that embeds a live API key, this is
arguably a *desirable* tightening — but it must be a deliberate, documented
choice in this phase's plan, not an accident inherited by blindly copying
the existing pattern.
**Why it happens:** The existing precedents were written for
`statusline.toml`/cache JSON, where permission bits were never a design
concern; copying them verbatim for a secret-bearing file carries the gap
forward silently.
**How to avoid:** Either (a) explicitly `os.chmod(tmp, stat.S_IMODE(os.stat(path).st_mode))`
before `os.replace` to preserve the original mode, or (b) explicitly decide
to tighten to `0600` and document why. Either is defensible; leaving it
unconsidered is not.
**Warning signs:** A test asserting `os.stat(path).st_mode` is unchanged
(or intentionally changed) before/after a `remove` call.

### Pitfall 3: Comma handling differs by removed entry's position

**What goes wrong:** Removing the *last* entry in the `"provider"` object
must also strip the now-dangling comma on the *preceding* entry (otherwise
`{"a": {...}, }` — a trailing comma, which is invalid in strict JSON and
only sometimes tolerated by JSONC parsers depending on implementation);
removing a *first* or *middle* entry must strip its own *trailing* comma
instead. A naive "always eat the following comma" or "always eat the
preceding comma" implementation breaks one of these two cases.
**Why it happens:** The PRD's acceptance criteria call out only the
string-literal brace-counting edge case explicitly; comma placement is
mentioned in passing ("plus the trailing comma/comment handling needed") but
not spelled out as its own case split.
**How to avoid:** After locating the block's `{...}` span, look outward:
if there is a non-provider sibling entry *after* it (skipping whitespace/
comments), eat the comma between them; else if there is a sibling *before*
it, eat that comma instead; else (sole entry) eat neither, leaving `{}`.
**Warning signs:** A test removing the *only* remaining provider (result:
`"provider": {}`), a test removing the *first* of three, and a test removing
the *last* of three — three distinct fixtures, not one.

### Pitfall 4: Anchoring the id search to the wrong nesting depth

**What goes wrong:** A provider entry's own `"models"` sub-object can
contain model keys that collide in spirit with provider ids elsewhere in
the file (verified live: this machine's `opencode.jsonc.bak2` has a
provider id `local-llm-env` whose `models` sub-object contains keys like
`llama-cpp/ornith-35b` — a different naming shape, but the general risk is
real: nothing prevents two different provider entries' sub-keys from
colliding with another provider's own id string). A search for `"<id>":`
that isn't anchored to *immediate children of the `"provider"` object* could
match inside a `models` sub-object instead of the provider-level key.
**Why it happens:** A single global string search is simpler to write than
a depth-aware one.
**How to avoid:** First locate the `"provider": {` opening brace, then walk
forward tracking depth; only treat a `"<id>":` match as the target when it
occurs at depth 1 relative to that opening brace (i.e., immediately inside
`"provider"`, not inside a nested `options`/`models` object).
**Warning signs:** A fixture where a *different* provider's `models` object
happens to contain a key string equal to the id being removed.

## Code Examples

Verified patterns from this codebase (Context7/official docs not applicable —
this phase reuses in-repo precedent, not a third-party library):

### Guarded stdlib TOML import (reuse verbatim)
```python
# Source: skills/ai-kit-spec-review/ai_kit_spec/config_io.py:1-7 (verified read this session)
import os
try:
    import tomllib as _tomllib_impl
    tomllib = _tomllib_impl
except ModuleNotFoundError:
    tomllib = None  # type: ignore[assignment]  # stdlib boundary: optional module absent on <3.11
```

### Tolerant JSON cache read (reuse verbatim, adapted to a new module)
```python
# Source: skills/ai-kit-spec-review/ai_kit_spec/cache.py:13-18 (verified read this session)
def cache_read_json(path: str) -> dict | None:
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None
```

### Real `opencode.jsonc` `"provider"` block shape (verified live on this machine)
```jsonc
// Source: ~/.config/opencode/opencode.jsonc, "provider" key (verified read this session;
// apiKey value redacted here — never print the real value anywhere, per REQ)
"provider": {
  "router-env": {
    "npm": "@ai-sdk/openai-compatible",
    "name": "router-env",
    "options": {
      "baseURL": "http://127.0.0.1:20128/v1",
      "apiKey": "<redacted>"
    },
    "models": {
      "my-planning": { "name": "my-planning (combo)", "limit": { "context": 1000000, "output": 128000 } },
      "my-plan-review": { "name": "my-plan-review (combo)", "limit": { "context": 1000000, "output": 128000 } },
      "my-coding": { "name": "my-coding (combo)", "limit": { "context": 500000, "output": 128000 } }
    }
  }
}
```
This confirms the exact field paths `list` must read: `provider.<id>.npm`
(top level of the entry) and `provider.<id>.options.baseURL` (one level
nested under `options`) — **never** `provider.<id>.options.apiKey`.

### Real `.aikit/review-spec.toml` shape the cross-reference check scans (verified live)
```toml
# Source: .aikit/review-spec.toml (verified read this session, full file)
[[reviewers]]
key = "opencode-local-plan"
cli = "opencode"
model = "router-env/my-plan-review"
vendor = "local"
command = "opencode run -m {model}"
```
Confirms the PRD's stated scan target: each `[[reviewers]]` entry's `model`
field (here literally containing the provider id `router-env` as a prefix)
and `cli` field, substring-matched against the id being removed.

### Cached model-catalog schema the cross-reference check scans (verified from source, not live data — no catalog file exists on this machine yet)
```python
# Source: skills/ai-kit-spec-review/ai_kit_spec/model_catalog.py:42-50 (verified read this session)
def cache_catalog_path(env: dict) -> str:
    return os.path.join(cache_base(env), "model-catalog.json")   # cache_base: cache.py:7-10

def canonical_key(provider: str, bare_model_id: str) -> str:
    return f"{provider}/{bare_model_id}"
```
Catalog path resolves to
`${XDG_CACHE_HOME:-$HOME/.cache}/ai-kit/spec/model-catalog.json`
`[VERIFIED: skills/ai-kit-spec-review/ai_kit_spec/cache.py:7-10 + model_catalog.py:42-43]`.
Each entry's mandatory fields include `"provider"` (str) and `"runtimes"`
(a dict keyed by CLI name, each holding a `"model_id"` string)
`[VERIFIED: skills/ai-kit-spec-review/ai_kit_spec/model_catalog.py:12,64-71]`
— the cross-reference scan must check both `entry["provider"]` and every
`entry["runtimes"][cli]["model_id"]` for a substring match on the id being
removed, matching the PRD's explicit wording ("entries whose `provider` or
`runtimes.<cli>.model_id` contains the provider id being removed").

## State of the Art

Not applicable in the usual sense (no external library/version drift to
track) — the one relevant "current vs. old" fact is opencode's own config
discovery order, verified this session:

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| N/A | `OPENCODE_CONFIG_DIR` env var → project-local `opencode.json(c)`/`.opencode/` (searched from cwd up to filesystem root) → `${XDG_CONFIG_HOME:-~/.config}/opencode/opencode.json(c)` | Current, per opencode's own docs `[CITED: opencode.ai/v2/docs/config]` | D-05's chosen default (`${OPENCODE_CONFIG_DIR:-${XDG_CONFIG_HOME:-$HOME/.config}/opencode}/opencode.jsonc`) matches the **global** tier of this resolution order; it deliberately does not attempt project-local discovery — the `--config` override (also already in D-05) is the escape hatch for a non-default location, matching the PRD's own "exact override mechanism to be confirmed during implementation" note |

**Deprecated/outdated:** Nothing to flag — this is a young, actively
developed CLI (`opencode`) and the config docs read as current.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `02-CONTEXT.md`'s claim that `gsd-core/workflows/ai-integration-phase.md` (inside this repo) already uses the `${OPENCODE_CONFIG_DIR:-${XDG_CONFIG_HOME:-$HOME/.config}/opencode}` convention could not be verified this session — no `gsd-core/` directory exists anywhere in this repo checkout or on this machine's filesystem (it is presumably part of the separately-installed GSD framework, not ai-kit's own tree). The convention itself **was** independently verified against opencode's own public docs (see State of the Art above), so D-05's chosen path is correct regardless — only the specific "this repo already does this" provenance claim is unverified. | opencode.jsonc discovery (D-05) | Low — the convention is independently confirmed correct via opencode's own docs; only the claimed in-repo precedent is unconfirmed, and D-05 is already locked either way |
| A2 | The recommendation that the new skill should stay self-contained (duplicate the ~10-line cache-path/JSON-read helpers) rather than cross-import `ai_kit_spec` via the `ai-kit-spec-execute-gsd` precedent is this research's own judgment call, not a CONTEXT.md-locked decision — CONTEXT.md's "Claude's Discretion: None" note means this specific question was never raised during discuss-phase. | Alternatives Considered / Pattern 3 | Low-Medium — both approaches are real, working precedents in this codebase; choosing the cross-import approach instead would only add an install-order dependency, not break anything functionally |

## Open Questions

1. **Does `--config <path>` accept a directory or the full file path?**
   - What we know: D-05 says `--config <path>` is "an explicit override for
     non-standard locations"; the PRD says the override mechanism is "to be
     confirmed during implementation, not assumed here."
   - What's unclear: whether `--config` takes the `opencode.jsonc` file path
     directly (simplest, and what this research recommends) or a directory
     that the tool then appends `opencode.jsonc` to (mirroring
     `OPENCODE_CONFIG_DIR`'s own directory-based semantics).
   - Recommendation: take the file path directly — simpler, and the
     `--config` flag's purpose (per D-05) is to point at "non-standard
     locations," which could plausibly be a differently-named file, not just
     a differently-located directory.

2. **Should `list` support a `--json` output mode?**
   - What we know: the PRD explicitly specifies human-readable table output
     for `list`; every other subcommand in the sibling `ai_kit_spec/cli.py`
     module emits JSON for scriptability.
   - What's unclear: whether this phase's `list` should also offer a
     `--json` flag for consistency with the rest of the codebase's
     CLI-scriptability convention, or whether the PRD's explicit
     "human-readable table" wording is the deliberate final answer.
   - Recommendation: out of scope for this phase — CONTEXT.md marks every
     gray area as already decided, and REQ-opencode-provider-list-remove's
     acceptance criteria only names id/npm/baseURL columns, not a machine
     format. Flag as a possible follow-up, do not add scope here.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.11+ (`tomllib`) | Cross-reference TOML read | ✓ | 3.14.7 on this dev machine `[VERIFIED: python3 --version, this session]`; repo's own declared floor is `>=3.11` `[VERIFIED: tools/setup.py:3, PEP-723 comment]` | — |
| `~/.config/opencode/opencode.jsonc` | `list`/`remove` (the file this tool edits) | ✓ (exists on this dev machine) `[VERIFIED: ls ~/.config/opencode/, this session]` | — | REQ already specifies the "file missing" edge case: clear error, no attempt to create the file |

No external CLI/service dependency — this is a pure local file-editing tool.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | `unittest` (stdlib) — every existing test file in this repo uses `unittest.TestCase`, no `pytest` in use `[VERIFIED: tests/test_ai_kit_spec.py:1-13, imports unittest not pytest]` |
| Config file | none — `Makefile`'s `test` target explicitly lists module names (no `pytest.ini`/`unittest.cfg`) `[VERIFIED: Makefile:33]` |
| Quick run command | `python3 -m unittest tests.test_ai_kit_opencode_providers` (new file — does not exist yet, see Wave 0 Gaps) |
| Full suite command | `make test` — **but only after the new test module is added to two places**, see Wave 0 Gaps |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| REQ-opencode-provider-list-remove | `list` shows id/npm/baseURL, never apiKey | unit | `python3 -m unittest tests.test_ai_kit_opencode_providers.TestList -v` | ❌ Wave 0 |
| REQ-opencode-provider-list-remove | `remove <id>` deletes exactly that block, byte-identical elsewhere (incl. `{`/`}` inside a string value), atomic write | unit (with a diff assertion) | same file, `TestRemove` | ❌ Wave 0 |
| REQ-opencode-provider-list-remove | `remove <id>` on non-existent id → clean no-op message | unit | same file, `TestRemoveNotFound` | ❌ Wave 0 |
| REQ-opencode-provider-cross-reference-check | Warn (non-blocking) on review-spec.toml reference | unit | same file, `TestCrossReferenceToml` | ❌ Wave 0 |
| REQ-opencode-provider-cross-reference-check | Warn (non-blocking) on cached-catalog reference, and names both locations when both match | unit | same file, `TestCrossReferenceCatalog` | ❌ Wave 0 |
| REQ-opencode-provider-cross-reference-check | `skills/ai-kit-opencode-providers/SKILL.md` passes `skill-judge` review | manual-only (global skill invocation, not a repo test) | invoke the `skill-judge` skill against the new `SKILL.md` | ❌ Wave 0 (SKILL.md itself doesn't exist yet) |

### Sampling Rate
- **Per task commit:** `python3 -m unittest tests.test_ai_kit_opencode_providers`
- **Per wave merge:** `make test` (once wired — see Wave 0 gap 2)
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/test_ai_kit_opencode_providers.py` — does not exist; needs
      creation before any test in the map above can run. Follow the existing
      `sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..",
      "skills", "ai-kit-opencode-providers"))` convention
      `[VERIFIED: tests/test_ai_kit_spec.py:13, same pattern for the sibling skill]`.
- [ ] `Makefile`'s `test` target — must append `tests.test_ai_kit_opencode_providers`
      to the explicit module list, or the new tests never run under `make test`
      / CI `[VERIFIED: Makefile:33, the target is an explicit unittest module
      list, not test discovery]`.
- [ ] `.pre-commit-config.yaml`'s `unittest` hook — same gap, a second explicit
      module list that must also be updated, or `make validate`/the commit
      gate never runs the new tests either
      `[VERIFIED: .pre-commit-config.yaml:52-56, entry: python3 -m unittest tests.test_status_line ... tests.test_ai_kit_spec_gsd — explicit list]`.
- [ ] `.pre-commit-config.yaml`'s `ruff`/`pylint`/`py-compile` hook `files:`
      regexes — currently scoped to `tools/`, `tests/`, and three named
      `skills/ai-kit-spec-*` paths; `skills/ai-kit-opencode-providers/` is
      **not** in that list `[VERIFIED: .pre-commit-config.yaml:16-19, 40-45]`.
      The new skill's own `.py` files (not its tests, which are already
      covered as `tests/*`) will not be linted unless this regex is extended
      — a real gap the plan should decide on explicitly (extend the gate now,
      matching this codebase's stated "the rest of skills/ joins the gate
      later" trajectory `[VERIFIED: .pre-commit-config.yaml:6-8 header
      comment]`, or defer).
- [ ] `tests/e2e/docker/fixtures/opencode/opencode.jsonc` — does not exist
      yet. Already explicitly planned for this exact phase in the e2e
      harness's own README: *"Phase 2 (Opencode Provider Management) — an
      `opencode.jsonc` fixture"* `[VERIFIED: tests/e2e/docker/fixtures/README.md,
      "Adding a fixture (future phases)" section]`. Follow the documented
      copy-into-scratch-tree pattern (never a live in-place reference, never
      a volume mount) — the established precedent is
      `tests/test_system_memory_e2e.py:210-224`'s `shutil.copy` from a fixed
      repo-relative path into a `tempfile.mkdtemp()`-rooted scratch tree
      before pointing environment variables at the scratch copy.

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | Single-user local tool, no auth surface |
| V3 Session Management | No | N/A |
| V4 Access Control | No | N/A — filesystem permissions are the only access boundary, covered under V12 below |
| V5 Input Validation | Yes | Validate the `remove <id>` argument and any `--config` path before use; treat a non-existent id as a clean no-op (already a REQ), never as an unvalidated string spliced into a shell command (this tool never shells out, so injection risk is structurally absent — but the id/path must still be validated as plain strings, not assumed non-empty) |
| V6 Cryptography | No direct control (this tool doesn't encrypt anything) but adjacent: never derive, log, or transform the `apiKey` value — treat it as an opaque secret, pass-through only if ever touched at all (it should never need to be) |
| V12 Files and Resources | Yes | Atomic write (temp + rename, same directory) prevents partial-write corruption; explicit permission-mode preservation (Pitfall 2) prevents an unannounced access-control change to a secret-bearing file; `--config` path should be resolved/normalized before use, not trusted verbatim into `os.replace`'s target |
| V14 Configuration | Yes | Never print/log the `apiKey` value anywhere (REQ, already locked); never dump the whole file to a debug log (PRD "Security" section, verified requirement) |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Secret leakage via `list` output or an error/debug message | Information Disclosure | Explicit field allowlist (`id`/`npm`/`baseURL` only) when building `list` output — never serialize or `str()` the whole provider entry dict, which would include `options.apiKey` |
| Corrupted `opencode.jsonc` from a crash mid-write | Denial of Service (to the user's own opencode setup) | Atomic write (temp + `os.replace`); the original file is provably intact until the rename succeeds |
| Silent brace-miscount corruption from the JSONC comment gap (Pitfall 1) | Tampering (of a file holding a live credential) | Comment-aware scanner state (four states, not two — see Pitfall 1) plus the dedicated test fixture the PRD already requires for the string case, extended to a comment case |
| Unannounced permission tightening/loosening on a secret-bearing file (Pitfall 2) | Elevation of Privilege / Information Disclosure (in the loosening direction) | Explicit `os.chmod` to preserve (or deliberately set) the original mode before `os.replace` |
| `--config` pointed at an attacker/mistake-controlled path (e.g. a symlink) | Tampering | `os.replace` on a temp file in the *same directory* as the resolved target follows the target's existing symlink semantics (replaces the symlink's target file, not the symlink itself, on POSIX) — this is standard and expected behavior, not a new risk this tool introduces, but the `--config` path itself should still be validated as a plausible file path before any read/write attempt |

## Sources

### Primary (HIGH confidence)
- `.planning/phases/02-opencode-provider-management/02-CONTEXT.md` — locked decisions D-01 through D-05, this phase's binding scope
- `docs/prds/ai-kit-opencode-provider-management-v1.0-prd.md` — source PRD, acceptance criteria
- `skills/ai-kit-spec-review/ai_kit_spec/{cli.py,cache.py,config_io.py,model_catalog.py}` — read directly this session, cited with line ranges throughout
- `tools/setup.py:442-459` (`write_toml_preserving`), `tools/setup.py:2320-2411` (`ensure_rich_runtime`/`_textual_importable`) — read directly this session
- `~/.config/opencode/opencode.jsonc`, `.bak2` — live, real config files on this machine, read directly this session (schema verified, secret redacted)
- `.aikit/review-spec.toml` — read directly this session, full file
- `.pre-commit-config.yaml`, `Makefile:33` — read directly this session
- `tests/e2e/docker/fixtures/README.md` — read directly this session, explicitly names this phase's own fixture obligation

### Secondary (MEDIUM confidence)
- opencode config docs (`opencode.ai/v2/docs/config`) — WebSearch result, cross-checked against this machine's live `XDG_CONFIG_HOME`/`OPENCODE_CONFIG_DIR` behavior description; not independently fetched via Context7 (opencode has no Context7-indexed library id for its CLI docs)

### Tertiary (LOW confidence)
- None — every substantive claim above traces to either a file read this session or a cited doc search result.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — 100% stdlib, every helper has a verified in-repo precedent
- Architecture: HIGH — CLI-module/SKILL.md pairing and atomic-write patterns both directly verified from source this session
- Pitfalls: HIGH for Pitfalls 1-4 (each traced to a verified gap between CONTEXT.md's wording and either opencode's real JSONC syntax or this repo's existing code); MEDIUM for the exact severity ranking between them

**Research date:** 2026-09-09
**Valid until:** 30 days (stable domain — stdlib-only, no fast-moving external dependency; re-verify if opencode's own config-file format changes upstream)
