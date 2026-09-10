# Phase 2: Opencode Provider Management - Context

**Gathered:** 2026-09-08
**Status:** Ready for planning

<domain>
## Phase Boundary

Users can safely inspect and remove custom opencode providers from their
config without hand-editing JSONC or risking corruption. A new
`ai-kit-opencode-providers` skill exposes `list` (id/npm/baseURL, never
apiKey) and `remove <id>` subcommands, backed by a byte-preserving surgical
edit to `opencode.jsonc`'s `"provider"` block, plus a non-blocking
cross-reference warning against `.aikit/review-spec.toml` and the cached
model catalog before removal.

</domain>

<decisions>
## Implementation Decisions

### Skill invocation surface
- **D-01:** `ai-kit-opencode-providers` is a CLI module (argparse-style
  `list`/`remove <id>` subcommands, testable) with a `SKILL.md` wrapper that
  documents and invokes it — the same shape as `ai-kit-spec-review`'s
  `ai_kit_spec/cli.py` + `SKILL.md` pairing already in this repo.

### JSONC surgical-edit approach
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

### Cross-reference warning UX
- **D-04:** The pre-removal cross-reference check is printed as an
  **informational warning only** — removal proceeds automatically with no
  additional confirmation prompt. Matches REQ-opencode-provider-cross-reference-check's
  literal "non-blocking" wording and is required for consistency with D-01
  (a CLI/scriptable skill can't depend on an interactive y/n gate).

### opencode.jsonc discovery
- **D-05:** The skill auto-discovers `opencode.jsonc` at
  `${OPENCODE_CONFIG_DIR:-${XDG_CONFIG_HOME:-$HOME/.config}/opencode}/opencode.jsonc`
  by default — the exact env-var/XDG convention already used by this repo's
  own GSD workflow scripts — with a `--config <path>` flag as an explicit
  override for non-standard locations.

### Claude's Discretion
None — every gray area in this phase had an explicit user decision.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Source PRD and synthesized intel
- `docs/prds/ai-kit-opencode-provider-management-v1.0-prd.md` — the proposal
  PRD this phase implements; full acceptance criteria and rationale
- `.planning/intel/requirements.md` — synthesized requirement detail
- `.planning/REQUIREMENTS.md` §Opencode Provider Management —
  REQ-opencode-provider-list-remove, REQ-opencode-provider-cross-reference-check
- `.planning/ROADMAP.md` §Phase 2 — success criteria this phase must make true
- `.planning/PROJECT.md` — core value (never corrupt config) and constraints
  (config safety: atomic writes, byte-preservation; runtime dependency
  discipline: stdlib-only) that directly shaped D-02/D-03

### Prior-phase precedent (informs but doesn't lock this phase)
- `.planning/phases/01-multi-cli-runtime-foundation/01-CONTEXT.md` — no
  direct decision overlap, but D-02's rejection of the `guard + uv-run`
  dependency pattern was investigated and decided during this phase's
  discussion, not carried over from Phase 1.2

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `skills/ai-kit-spec-review/ai_kit_spec/cli.py` + `SKILL.md`: the exact
  CLI-module + SKILL.md-wrapper shape to replicate for D-01.
- `tools/setup.py::write_toml_preserving()` (line ~442): existing
  atomic-write pattern (`tempfile.mkstemp` in the same directory +
  `os.replace()`) — reuse the same atomicity technique for the surgical
  JSONC write, even though the surrounding text-preservation logic is new.

### Established Patterns
- `tools/setup.py::ensure_rich_runtime()` / `_textual_importable()` (lines
  ~2189-2270): the existing "guard, conditionally re-exec under `uv run`,
  fail closed with a clear error" pattern for the one non-stdlib runtime
  dependency (`textual`) this repo has. Investigated in detail during this
  phase's discussion and **deliberately not replicated** for the new JSONC
  editor (see D-02's rejected-alternative note) — its fail-closed path is
  only unit-tested with mocks, not verified in a genuinely dependency-free
  environment, and this skill has no interactive-UI justification the wizard
  has.
- `install.sh` execs `python3 "$INSTALL_DIR/tools/setup.py" "$@"` directly,
  no `uv run` — confirms the curl-piped install path never depends on `uv`
  being present except when the interactive wizard itself needs `textual`.
- `${OPENCODE_CONFIG_DIR:-${XDG_CONFIG_HOME:-$HOME/.config}/opencode}` is the
  exact opencode-config-dir convention already used across this repo's own
  GSD workflow scripts (e.g. `gsd-core/workflows/ai-integration-phase.md`) —
  reuse verbatim for D-05.

### Integration Points
- New module lives alongside `skills/ai-kit-spec-review/ai_kit_spec/` peers
  as a new `skills/ai-kit-opencode-providers/` skill directory (mirroring the
  existing `skills/<name>/<name>_pkg>/cli.py` + `SKILL.md` layout).
- `.aikit/review-spec.toml` (read-only for the cross-reference check) and the
  cached model catalog (`skills/ai-kit-spec-review/ai_kit_spec/model_catalog.py`'s
  `cache_catalog_path()`) are the two things D-04's warning checks against.

</code_context>

<specifics>
## Specific Ideas

- The rejection of the `guard + uv-run` dependency pattern (D-02) came from a
  real back-and-forth: the user first picked "replicate the wizard's
  pattern," then asked pointed questions about whether that pattern is
  actually verified in a clean environment. Verification (reading
  `install.sh`'s direct `python3` exec, `tools/setup.py`'s deferred/guarded
  `textual` import, and `tests/test_setup.py`'s mock-only coverage of the
  fail-closed path) confirmed the user's suspicion was well-founded, and the
  final decision reversed to stdlib-only.
- The user separately suggested the *existing* wizard's install flow should
  offer to auto-install missing pieces (`uv`/`python`/`textual`) instead of
  just failing closed — this is a real idea but explicitly **not** part of
  this phase (see Deferred Ideas below).

</specifics>

<deferred>
## Deferred Ideas

- **Installer auto-install-missing-deps UX**: instead of `ensure_rich_runtime()`
  failing closed with just an error message when `uv`/`textual` aren't
  available, the installer could offer to install them for the user. Raised
  by the user during Phase 2's JSONC-dependency discussion, but it's a change
  to the *existing*, already-shipped wizard bootstrap behavior
  (`tools/setup.py`), not part of Opencode Provider Management's scope.
  Belongs in its own future phase/PRD for installer UX improvements.

### Reviewed Todos (not folded)
None — no matching todos found (`todo_count: 0` for Phase 2).

</deferred>

---

*Phase: 2-Opencode Provider Management*
*Context gathered: 2026-09-08*
