# Phase 4: Config Doctor - Context

**Gathered:** 2026-09-08
**Status:** Ready for planning

<domain>
## Phase Boundary

Users get a single, trustworthy interactive screen showing how their Claude
Code / opencode / Codex / **Cursor** (scope expanded during this discussion —
see D-03) configuration compares to recommended settings, with confidence
labeling per row and a per-item, explicitly-confirmed apply flow reusing
Phase 2's atomic-write/surgical-edit pattern. No bulk "apply all." A read-only
diagnostic layer (the Checks Catalog) plus a write layer (the apply flow),
both driven by a declarative, extensible check registry rather than
per-check hardcoded functions.

</domain>

<decisions>
## Implementation Decisions

### Checks Catalog structure
- **D-01:** The catalog is **data-driven**, not 12+ hardcoded functions: each
  row is a record (`runtime`, `check`, `current-value-reader`, `recommended`,
  `confidence`, `apply-fn` or `None` for informational-only rows) consumed by
  one generic check/apply engine. Adding or removing a row is a data change,
  not an engine rewrite — matches the PRD's own framing ("PROPOSED, not
  committed final list").
- **D-02 (found mid-discussion):** The schema needs a **`scope` field**
  (`runtime` vs. `model`) — some checks (e.g. row #10, Codex
  `model_reasoning_effort`) should vary by which *model/vendor* is active
  within a runtime, not be a single fixed runtime-wide recommendation (e.g. a
  model-appropriate reasoning-effort recommendation should track the
  configured model, whether that's an Anthropic model routed through
  opencode or a third-party model in Codex). The exact mechanism for a
  `model`-scoped row to resolve "which model is active" is left to the
  researcher/planner — not designed in this discussion.

### Runtime-installed detection (and Cursor scope expansion)
- **D-03 (major — expands REQ-config-doctor-diagnostic-checks):** A
  runtime's section is shown/skipped based on **config-file presence**
  (`~/.claude/settings.json`, `~/.config/opencode/opencode.jsonc`,
  `~/.codex/config.toml`, `~/.cursor/cli-config.json`), not
  `detect_installed_clis()` (Phase 1.2's binary-on-PATH detector, which answers
  a different question). **Cursor is added as a 4th runtime** to this
  phase's scope — live-verified as actually installed and actively used on
  this machine (`~/.cursor/cli-config.json` with `permissions`/`modelParameters`
  per model, `~/.cursor/hooks.json` with a real hooks system including
  `sessionStart`). This is a deliberate scope expansion, not creep — the user
  explicitly chose it after being offered "defer to a future phase" and
  pushing back with a real feasibility question. `REQUIREMENTS.md` and
  `ROADMAP.md` were amended (commit `28766ce`) to reflect it formally, since
  the phase boundary these downstream agents trust lives there, not only in
  this file.
  — **Reversibility:** costly — once the researcher produces cited Cursor
  rows and the planner schedules them into this phase's plan set, descoping
  Cursor back out would mean re-deriving Phase 4's plan boundaries; treat
  this as locked for this milestone unless the user explicitly reopens it.
- **D-03b (cross-phase amendment, same investigation):** Phase 1.2's
  `native_runtime` valid-value set and Phase 3's opencode-only hook gap were
  both found incomplete for the same reason (Cursor never assessed when
  those PRDs were written) and amended: Phase 1.2 now allows `"cursor"` as a
  `native_runtime` value (01-CONTEXT.md D-09); Phase 3 now also wires the
  briefing into Cursor's `sessionStart` hook, not just Claude Code's
  (03-CONTEXT.md D-09) — opencode remains the only genuine hook-gap runtime.
  See those files' amendment sections for full detail; not re-derived here.

### Row 9 (Codex `features.hooks`) apply semantics
- **D-04:** Row 9 is **informational only, no apply action** — same
  treatment as row 5 (opencode retention). The PRD's "confirm whether the
  user actually wants Codex's experimental hooks on" reads as a question to
  surface, not an automatic toggle; Phase 3 already scoped Codex hook work
  OUT of ai-kit's own tool-substitution hook, so offering an apply action
  here would be confusing/out of place.

### Review-screen presentation format
- **D-05:** The review screen is an **interactive TUI built with `textual`**
  (not a plain CLI report like `statusline-doctor.py`) — unlike Phase 2's
  JSONC editor (which had no interactive-UI justification and was kept
  stdlib-only), reviewing ~15+ rows across 4 runtimes with per-item apply
  genuinely benefits from a rich interface; `ROADMAP.md` already flags this
  phase `UI hint: yes`.
- **D-06:** The TUI reuses `tools/setup.py`'s existing `ensure_rich_runtime()`
  guard function as-is (entrypoint-agnostic — no reason to duplicate its
  logic) and the same visual style as `wizard_app.py`'s `WizardApp`, but
  lives in its **own separate module** (e.g. `tools/config_doctor_app.py`) —
  not literally embedded as another screen inside the existing `WizardApp`
  instance, since Config Doctor is invoked independently at any time, not
  only during install/reconfigure (`wizard_app.py` currently has exactly one
  `App` subclass and no separate `Screen` classes to plug into).
- **D-07 (naming, avoids a real collision):** The new flow is reached via a
  **new `--config-doctor` flag on `tools/setup.py`** (TUI by default,
  `curl | bash`-compatible like the install flow), NOT by repurposing the
  existing `doctor` subcommand — `setup.py doctor` already has an
  established, different meaning today (delegates to `statusline-doctor.py
  --doctor`, validates the status-line config) and changing its default
  behavior would be a breaking surprise for existing usage. `doctor` stays
  exactly as it is.

### Claude's Discretion
None — every gray area in this phase had an explicit user decision. Several
factual questions (see Open Research Questions below) were explicitly
**not** answered by invention, per the project's confidence-labeling
constraint.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Source PRD and synthesized intel
- `docs/prds/ai-kit-config-doctor-v1.0-prd.md` — the proposal PRD this phase
  implements; note this discussion expanded its scope (Cursor) and corrected
  some assumptions — see D-03 and Open Research Questions
- `.planning/intel/requirements.md` — synthesized requirement detail
- `.planning/REQUIREMENTS.md` §Config Doctor (amended 2026-09-08, commit
  `28766ce`) — REQ-config-doctor-diagnostic-checks,
  REQ-config-doctor-review-screen, REQ-config-doctor-apply-flow
- `.planning/ROADMAP.md` §Phase 4 (amended same commit) — success criteria
- `.planning/PROJECT.md` — core value (never claim more certainty than
  verified) drove D-03's Cursor-research requirement and the explicit
  refusal to invent answers to the open research questions below

### Cross-phase amendments (same investigation, different files)
- `.planning/phases/01-multi-cli-runtime-foundation/01-CONTEXT.md` D-09 —
  `native_runtime` now allows `"cursor"`
- `.planning/phases/03-tool-substitution-awareness-hook/03-CONTEXT.md` D-09
  (Cursor `sessionStart` hook wiring) and D-10 (uninstall must remove ai-kit's
  own `hooks.SessionStart` entries — a real gap found in `cmd_uninstall()`
  during this phase's discussion, fixed there since it's Phase 3's wiring
  that creates the entry)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `tools/setup.py::ensure_rich_runtime()` / `_textual_importable()` (lines
  ~2189-2270): reuse as-is for D-06 — entrypoint-agnostic guard.
- `tools/wizard_app.py::WizardApp(App)` (line ~148): the only existing
  `textual` app in this repo — one class, no separate `Screen` subclasses;
  study its structure/style for the new Config Doctor module, but do not
  embed into it (D-06).
- `tools/setup.py::unwire_statusline()`: the pattern to mirror for Phase 3's
  new `unwire_hook()` (03-CONTEXT.md D-10) — not this phase's own code, but
  relevant since Config Doctor's own apply flow may want the same
  read-current/guard-foreign-value/write-back shape for its per-runtime
  config edits.
- `tools/setup.py::_read_json()`/`_write_json()` and the atomic-write pattern
  from `write_toml_preserving()` (line ~442) — reuse for Claude Code/Cursor
  (JSON-ish) and any TOML (Codex) apply targets; opencode's JSONC apply
  reuses Phase 2's surgical-edit module directly (per REQ-config-doctor-apply-flow).

### Established Patterns
- `tools/setup.py`'s `argparse` subcommand/flag structure (line ~2290-2296):
  `choices=["install", "reconfigure", "uninstall", "doctor", "check"]` — the
  new `--config-doctor` flag (D-07) is added alongside this, not into it, to
  avoid the `doctor` naming collision.
- Live-verified real config file locations for detection (D-03): Claude Code
  `~/.claude/settings.json`, opencode `~/.config/opencode/opencode.jsonc`,
  Codex `~/.codex/config.toml`, Cursor `~/.cursor/cli-config.json`.

### Integration Points
- `tools/setup.py::main()`'s argument parser is where `--config-doctor` gets
  wired in (D-07).
- Phase 2's `ai-kit-opencode-providers` surgical-edit module is a direct
  dependency for this phase's opencode apply-flow rows.

</code_context>

<specifics>
## Specific Ideas

- The user wants Claude Code's transcript-retention row raised specifically
  because it feeds Phase 5's usage-metrics dashboard — longer local retention
  directly serves that later phase's data needs. This is motivation/context
  for row #1's recommendation, not a scope change.
- The user wants the review screen to explain **pros/cons per value or per
  range extreme**, not just show current-vs-recommended — richer explanatory
  content than the PRD's terse "Why" column implies. Feed this to the
  planner as a UI-content requirement.

</specifics>

<deferred>
## Deferred Ideas

- **Shared core between Config Doctor's TUI and a future CLI variant**
  (proposed by the user after this phase's context was already captured,
  2026-09-08). This phase's D-05/D-06 build the review screen as a `textual`
  TUI. The user's later instruction: the CLI-mode Config Doctor that will
  eventually exist should **not** be a second, independently-written
  implementation — it should be built by extracting the check-running/apply
  logic (the D-01 declarative engine: read current value, compare to
  recommended, apply on confirm) into a **shared core module**, with the TUI
  (this phase) and a future plain-CLI/scriptable mode both as thin front-ends
  over that same core, rather than the CLI later re-deriving what the TUI
  already does. Not built now — this phase still ships TUI-only per D-05/D-07
  — but the engine from D-01 should be written with this eventual split in
  mind (i.e., don't couple the check/apply logic to `textual` widgets
  directly) so extracting a CLI front-end later is an addition, not a
  rewrite. Solo-dev project note from the user: raise this as a **GSD
  proposal** (an idea for the GSD framework/tooling itself — "core logic
  shared across a TUI and a CLI front-end" is a pattern GSD's own agents
  could recognize/scaffold) — not a task for this project's own backlog to
  execute now, and not re-litigated as an in-discussion decision.

### Reviewed Todos (not folded)
None — no matching todos found (`todo_count: 0` for Phase 4).

</deferred>

<open_research_questions>
## Open Research Questions (MANDATORY for gsd-phase-researcher)

These were raised during discussion and deliberately **not** answered by
guessing — the project's own core value forbids presenting unverified claims
with borrowed certainty. The researcher must resolve each with real citations
before the planner locks the Checks Catalog's final row set:

1. **Cursor's own Checks Catalog rows** — equivalent settings to the existing
   12 rows (retention, cache/context behavior, sandboxing, telemetry,
   permissions — `~/.cursor/cli-config.json` already shows a `permissions`
   block and per-model `modelParameters`) need real citations, same rigor as
   the existing rows. This is the biggest open item — D-03 depends on it.
2. **Does opencode genuinely lack any local session-retention control?**
   Row 5 claims "not configurable," cited to opencode issue #22110. Local
   `opencode.jsonc` here has no retention-like key (consistent, not
   conclusive). Confirm definitively.
3. **Is Claude Code telemetry (row 4) safely universal, or account-type
   conditional?** The user asked whether enabling `CLAUDE_CODE_ENABLE_TELEMETRY`
   is something an individual user can/should always do, versus something a
   corporate/enterprise account may not have the authority (or reason) to
   toggle. If conditional, the row's recommendation logic may need an
   account-type signal, or an explicit caveat in its "Why" text.
4. **Does a Claude-Code-style long-retention setting exist for Codex, Cursor,
   and opencode?** The user wants to retain chat/session history longer
   across all 4 runtimes (feeds Phase 5's usage-metrics dashboard, per
   Specific Ideas above) — row 11 already covers Codex's
   `history.persistence` (save-all vs. none, not a duration), but a
   duration-style retention control (like Claude Code's `cleanupPeriodDays`)
   for Cursor/opencode/Codex needs to be confirmed to exist (or confirmed
   absent) with citations.
5. **Additional useful tweakable settings beyond the current 13 rows**,
   across all 4 runtimes — the user explicitly asked for this to not be
   limited to the PRD's original list.
6. **Third-party-model-specific settings within opencode and Cursor** — both
   are multi-provider/multi-model CLIs (Cursor's `cli-config.json` already
   shows distinct `modelParameters` per model: `gpt-5.2`, `glm-5.2`,
   `gpt-5.6-luna`). The user wants config-doctor to surface useful
   model-specific recommendations for non-Anthropic models too, not just
   Anthropic-hosted ones — this is what D-02's `scope: model` schema field
   exists to support; the researcher should identify which specific
   model-parameter checks are worth surfacing.
7. **Candidate new row: `rtk`'s `[tee].max_files` setting** (found 2026-09-08
   during Phase 5's discussion). Currently defaults to `20` in
   `~/.config/rtk/config.toml`'s `[tee]` block (`mode = "failures"`,
   `max_file_size = 1048576`) — live-verified on this machine. The user
   proposed raising it to roughly `100` so more failure-debugging context is
   retained; this also feeds Phase 5's usage-metrics dashboard, which (per
   `05-CONTEXT.md`) ingests `rtk`'s tee logs as one of its raw sources — more
   retained tee entries means more data available to that pipeline. Add as a
   13th-ish cross-runtime row (same family as row #12's rtk-Cursor-integration
   check) once the researcher confirms rtk's own guidance/docs on a sensible
   `max_files` value and any disk-usage tradeoff worth citing (each file
   capped at `max_file_size` = 1 MiB, so raising the count has a bounded,
   citable disk-usage impact).

</open_research_questions>

---

*Phase: 4-Config Doctor*
*Context gathered: 2026-09-08*
