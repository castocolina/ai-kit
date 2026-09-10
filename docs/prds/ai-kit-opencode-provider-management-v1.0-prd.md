# AI-Kit opencode Provider Management - Product Requirements Document (PRD)

> **Status note**: everything in this document is a PROPOSAL, not an accepted
> decision. Where a single approach is written up in detail, it is the
> author's recommendation after comparing alternatives (see each
> "Alternatives Considered" subsection) — not a foregone conclusion. Treat
> every "Design Decision" below as open to challenge until explicitly
> approved.

## Requirements Description

### Background

- **Business Problem**: opencode has two fundamentally different kinds of
  "provider" configuration, and only one of them is manageable via a native
  command:
  1. **Credential-based providers** — added via `opencode auth login`,
     stored in `~/.local/share/opencode/auth.json`, listed via
     `opencode auth list`, removed via `opencode auth logout`. This path is
     already fully served by opencode itself; not a gap.
  2. **Config-based custom providers** — a raw `"provider"` block written
     directly into `~/.config/opencode/opencode.jsonc` (confirmed live on
     this machine: a `router-env` entry using
     `@ai-sdk/openai-compatible` with an embedded `baseURL`/`apiKey`).
     Confirmed empirically: `opencode auth list` does not surface this
     entry at all, and no `opencode` subcommand lists, edits, or removes
     it — the only way today is manual JSONC editing. Evidence this is a
     real, recurring pain: `opencode.jsonc.bak`/`.bak2` files already exist
     on this machine from prior manual edits.
- **Target Users**: ai-kit's own maintainer/user, who runs at least one
  config-based custom provider (`router-env`) that is also referenced by
  ai-kit's own reviewer configuration (`.aikit/review-spec.toml`).
- **Value Proposition**: a safe, scriptable way to list and remove
  config-based providers without hand-editing JSON-with-comments and
  without accidentally breaking an ai-kit config that references the
  provider being removed.

### Feature Overview

- **Core Features**: list all config-based providers in
  `opencode.jsonc`; remove one by id, preserving every other byte of the
  file (comments, formatting, unrelated keys) exactly as-is; before
  removing, check whether the target provider id is referenced anywhere in
  ai-kit's own configuration (`.aikit/review-spec.toml`'s `cli`/`model`
  fields, and the cached model catalog) and warn if so — informational
  only, never blocking.
- **Feature Boundaries**:
  - IN: `opencode.jsonc`'s `"provider"` block only (list, remove-by-id,
    cross-reference warning against ai-kit's own config).
  - NOT IN: anything touching `auth.json`/`opencode auth login`/`logout`
    (already solved natively by opencode); adding a new provider (already
    solved — the user already knows how); editing/updating an existing
    provider's fields (only full removal is in scope, per this PRD's
    clarification round — could be a follow-up); any change to opencode
    itself (this is a standalone ai-kit tool operating on opencode's config
    file, not a patch to opencode).
- **User Scenarios**:
  - User runs the new skill/command to see every config-based provider
    currently defined in `opencode.jsonc` (id + `npm` package + `baseURL`,
    never printing the raw `apiKey` value).
  - User asks to remove `router-env`; the tool finds it's referenced in
    `.aikit/review-spec.toml`'s reviewer ladder, prints a clear warning
    naming the referencing file/key, and proceeds only after the user
    confirms (or the tool's chosen UX makes confirmation implicit via a
    required flag — see Design Decisions).
  - The removal is byte-exact everywhere outside the deleted provider's own
    block: any comment, unrelated provider, or custom formatting elsewhere
    in `opencode.jsonc` is untouched.

### Detailed Requirements

- **Input/Output**: Input = `~/.config/opencode/opencode.jsonc`'s path
  (default) or an explicit override path; a provider id (for removal).
  Output (list) = a human-readable table of provider id, `npm` package,
  `baseURL` (never the API key). Output (remove) = the rewritten
  `opencode.jsonc` with only the target block excised, plus a warning line
  if a cross-reference was found.
- **User Interaction**: invoked as a new ai-kit skill,
  `ai-kit-opencode-providers` (e.g. `/ai-kit-opencode-providers list`,
  `/ai-kit-opencode-providers remove <id>`).
- **Data Requirements**: no new persistent schema — this tool reads and
  surgically rewrites an existing file it does not own the format of
  (opencode's own `opencode.jsonc`). The cross-reference check reads
  `.aikit/review-spec.toml` (already-established TOML format, `[[reviewers]]`
  entries with `cli`/`model` fields) and, if present, the cached model
  catalog JSON (entries whose `provider` or `runtimes.<cli>.model_id`
  contains the provider id being removed).
- **Edge Cases**:
  - Removing a provider id that doesn't exist in the file → clean no-op
    message, not a crash or silent success.
  - `opencode.jsonc` missing entirely (opencode never configured, or config
    at a non-default path) → clear error, no attempt to create the file.
  - A provider block with nested braces inside string values (e.g. a
    `baseURL` or `apiKey` containing a literal `{`/`}` character) — the
    surgical brace-counting approach (see Design Decisions) must count
    braces only outside of string literals, not blindly count every `{`/`}`
    byte. This is the single trickiest correctness requirement in this PRD
    and needs explicit test coverage.
  - The provider id is referenced in `.aikit/review-spec.toml` AND appears
    as `key`/`provider` in a locally-cached model-catalog JSON — the
    warning names both locations, not just one.

## Design Decisions

### Technical Approach

- **Removal mechanism — surgical text edit, not a JSONC parser library**:
  confirmed no JSONC-aware library (`json5`, `commentjson`, `jsonc-parser`)
  is installed in this project's Python environment today. Two real
  approaches were compared:
  1. **(Recommended) Surgical brace-counting removal**: locate the target
     provider's key (`"<id>": {`) inside the `"provider"` block, then walk
     forward counting `{`/`}` while correctly skipping over string-literal
     content (so a brace inside a quoted `baseURL`/`apiKey` value is never
     mis-counted) to find the matching close brace, then delete that exact
     span (plus the trailing comma/comment handling needed to keep the
     surrounding JSON valid). Every other byte of the file — comments,
     unrelated providers, formatting — is untouched. Pro: zero new
     dependencies, consistent with this codebase's existing minimal-
     dependency style (`model_heuristics.py`, `model_catalog.py` are pure
     stdlib). Con: the string-literal-aware brace counter is a genuine
     small parser that must be written and tested carefully — the edge
     case above (braces inside string values) is the main risk.
  2. **(Rejected for this PRD, noted as a real alternative) Adopt a
     JSONC-aware parsing library**: more robust against unusual nesting or
     malformed input, but introduces a new dependency for what is
     otherwise a small, single-purpose tool — rejected per this PRD's
     clarification round, but flagged here explicitly as the fallback if
     the surgical approach proves too fragile in practice (e.g. if testing
     surfaces real-world JSONC files this approach can't handle safely).
- **Cross-reference check**: read `.aikit/review-spec.toml` with the
  existing TOML parser this codebase already uses (`tomllib`, stdlib since
  Python 3.11 — confirm the actual import already used elsewhere in
  `ai_kit_spec/*.py` and reuse it rather than adding a new TOML dependency);
  scan every `[[reviewers]]` entry's `cli`/`model` fields for a substring
  match on the provider id being removed. Separately, if a cached model
  catalog JSON exists at its established path, scan its entries the same
  way. Both checks are read-only and additive to the removal flow — never
  block removal, only warn.
- **Key Components**:
  - New skill directory `skills/ai-kit-opencode-providers/` (SKILL.md +
    a small Python module, following the existing `ai-kit-spec-*` skill
    package shape — e.g. `ai_kit_spec_review/`'s own `ai_kit_spec/`
    package-per-skill convention).
  - The surgical block-removal function (pure, testable in isolation, no
    file I/O in the core logic — matching this codebase's existing
    preference for pure heuristic/logic functions with I/O kept at the
    edges).
  - The cross-reference scanner (reads `.aikit/review-spec.toml` + the
    cached catalog, both already-established formats).
- **Data Storage**: none new.
- **Interface Design**: `list` and `remove <id>` subcommands under the new
  skill; a `--path` override for `opencode.jsonc`'s location (never
  hardcode `~/.config/opencode/opencode.jsonc`, since the research
  confirmed opencode also supports project-local config and an env-var
  override — exact override mechanism to be confirmed during
  implementation, not assumed here).

### Constraints

- **Performance Requirements**: N/A — single small local file, single-user
  invocation.
- **Compatibility**: must never alter opencode's own `auth.json` or any
  credential-based provider — this tool's entire scope is the
  `"provider"` block in `opencode.jsonc` only.
- **Security**: never print a provider's `apiKey` value in `list` output
  (only id/`npm`/`baseURL`); never log the full file contents anywhere
  that could leak a key (e.g. no debug dump of the whole JSONC to a log
  file). The removal edit must not leave a partial/corrupted JSONC file on
  a crash mid-write — write to a temp file and atomically rename over the
  original (same pattern `install.sh`'s tarball-fallback path already uses
  for its own atomic swap).
- **Scalability**: N/A.
- **Skill quality gate**: this PRD creates a new `SKILL.md`
  (`skills/ai-kit-opencode-providers/SKILL.md`) — it MUST go through the
  same `skill-judge` review loop already established for this initiative
  (see the sibling `ai-kit-multi-cli-runtime-support` PRD's Constraints
  section for the exact bar: no remaining Critical/Important finding, or
  score ≥ 96/120, before the task that creates it is considered complete).

### Risk Assessment

- **Technical Risks**: the string-literal-aware brace counter is the one
  piece of real parsing logic in this PRD — a bug there could corrupt a
  live `opencode.jsonc` (which also holds an embedded API key). Mitigated
  by: (a) the atomic-write requirement above (a bug produces a clean
  failure, never a half-written file), and (b) mandatory test coverage
  with a fixture containing a provider whose `baseURL`/`apiKey` values
  themselves contain `{`/`}` characters, proving the counter correctly
  ignores braces inside strings.
- **Dependency Risks**: none (explicitly avoiding a new dependency is the
  chosen approach).
- **Schedule Risks**: low — this is a small, self-contained tool once the
  brace-counting edge case is handled correctly.

## Acceptance Criteria

### Functional Acceptance

- [ ] `list` shows every entry under `opencode.jsonc`'s `"provider"` block
      (id, `npm`, `baseURL`), never the `apiKey` value.
- [ ] `remove <id>` deletes exactly that provider's block; every other byte
      of the file (comments, unrelated providers, formatting) is verified
      byte-identical before/after via a diff in the test suite.
- [ ] `remove <id>` on a non-existent id produces a clear no-op message,
      not a crash or a silent success.
- [ ] Before removing, the tool checks `.aikit/review-spec.toml` and the
      cached model catalog (if present) for a reference to the target id
      and prints a warning naming every referencing location found; the
      removal still proceeds (informational, non-blocking) per this PRD's
      clarification.
- [ ] A provider whose `baseURL`/`apiKey` value contains a literal `{` or
      `}` character is removed correctly (pinned by a dedicated test
      fixture) — proving the brace counter is string-literal-aware, not a
      naive byte count.
- [ ] The write is atomic (temp file + rename) — a simulated failure
      mid-write never leaves a corrupted `opencode.jsonc`.

### Quality Standards

- [ ] Code Quality: the brace-counting removal function is pure (no file
      I/O), independently unit-testable, following this codebase's
      existing style (`model_heuristics.py`).
- [ ] Test Coverage: unit tests for list, remove (happy path + not-found),
      the string-literal brace-counting edge case, the cross-reference
      warning (both TOML-only and catalog-only and both-at-once cases),
      and the atomic-write failure path.
- [ ] Skill Quality: `skills/ai-kit-opencode-providers/SKILL.md` passes the
      `skill-judge` review loop (Constraints section above) before this
      work is marked complete.
- [ ] Security Review: confirmed no code path prints or logs a raw
      `apiKey` value; confirmed the atomic-write pattern is actually used
      (not just described).

### User Acceptance

- [ ] User Experience: a single new skill invocation replaces manual JSONC
      editing for this operation; the cross-reference warning is
      unambiguous about exactly which file/entry references the provider
      being removed.
- [ ] Documentation: the new `SKILL.md` documents both subcommands with
      example output.
- [ ] Training Materials: not applicable (internal tooling, single user).

## Execution Phases

### Phase 1: Core removal logic
**Goal**: A correct, tested, dependency-free provider block remover.
- [ ] Task 1: implement the string-literal-aware brace-counting block
      locator/remover as a pure function; unit tests including the
      brace-inside-string edge case.
- [ ] Task 2: implement atomic file write (temp file + rename); test the
      simulated-failure path leaves the original file untouched.
- **Deliverables**: pure removal function + atomic writer, both unit
  tested in isolation from any CLI/skill wiring.
- **Skill quality gate**: does not apply to this phase (no `SKILL.md`
  touched yet).

### Phase 2: Cross-reference check + skill wiring
**Goal**: Wire the removal logic into a real, invokable skill with the
ai-kit-config cross-reference warning.
- [ ] Task 1: implement the `.aikit/review-spec.toml` + cached-catalog
      scanner; unit tests for TOML-only, catalog-only, both, and neither.
- [ ] Task 2: implement `list` (read-only, no removal logic needed).
- [ ] Task 3: create `skills/ai-kit-opencode-providers/SKILL.md` wiring
      `list`/`remove` as subcommands; document example output for both.
- [ ] Task 4: run the `skill-judge` review loop against the new
      `SKILL.md` (Constraints section) before marking this phase complete.
- **Deliverables**: a working, documented, skill-judge-approved skill.

---

**Document Version**: 1.0
**Created**: 2026-09-06
**Clarification Rounds**: 3
**Quality Score**: 93/100
