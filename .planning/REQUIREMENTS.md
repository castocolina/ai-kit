# Requirements: ai-kit

**Defined:** 2026-09-07
**Core Value:** ai-kit must never corrupt uz's AI-CLI configuration and must never claim more certainty than it has

Requirement IDs and full acceptance criteria are carried over verbatim from
`.planning/intel/requirements.md` (synthesized from 5 ingested proposal PRDs
under `docs/prds/`). This file summarizes each into one testable line; read
the intel file for complete acceptance detail before planning a phase.

## v1 Requirements

Requirements for this milestone. Each maps to exactly one roadmap phase.
All 5 source PRDs are proposals (no ADR locks them) — see PROJECT.md Key
Decisions.

### Multi-CLI Runtime Support

- [x] **REQ-multi-cli-install-single-branch**: `tools/install.sh`'s primary git clone adds `--single-branch` (alongside existing `--branch`/`--depth 1`), leaving the tarball-fallback and `git pull --ff-only` paths unchanged, pinned by a new `tests/test_install.sh` case.
- [x] **REQ-multi-cli-runtime-detection**: A `detect_current_runtime()` function identifies `claude`/`opencode`/`codex`/`cursor`/`unknown`, surfaced as an optional `native_runtime` field on model-catalog entries with `cli: None`; `ai-kit-spec-config/SKILL.md` documents the labeling and passes `skill-judge` review. (Amended 2026-09-08: `cursor` added as a valid value — Phase 1.2's own CONTEXT.md D-02 already scopes `cursor-agent` into the empirical detection research; the original wording omitting it from the valid-value set was an oversight, caught during Phase 4 discussion. Phase renumbered from 1 to 1.2 on 2026-09-08 — see `.planning/ROADMAP.md`'s Phase Numbering note. Amended 2026-09-09: plan 01.2-02 resolved Open Question 1 — `native_runtime` schema support was added to both `model_catalog.py` (forward-compatible only, no live `cli`-key producer today) and `config_io.py` (the functionally-reachable native review-spec.toml entry path), since `cli: None` semantics actually live in `review-spec.toml`, not `model_catalog.py`. See `01.2-02-PLAN.md`'s objective and `AGENTS.md`'s Architecture section.)
- [x] **REQ-multi-cli-opencode-ui-research**: A committed markdown research report enumerates opencode's documented plugin hooks, assesses sidebar/status-bar viability, cross-references `anomalyco/opencode#5971`, and gives an explicit recommendation — no code changes. (Amended 2026-09-09: delivered at `docs/research/opencode-sidebar-status-bar-viability.md` — also cross-references `anomalyco/opencode#23539`, the status-bar-widgets issue, per the phase's own "sidebar/status-bar" scope; recommends "wait for upstream." See `01.2-03-PLAN.md`/`01.2-03-SUMMARY.md`.)

### Opencode Provider Management

- [x] **REQ-opencode-provider-list-remove**: New `ai-kit-opencode-providers` skill lists custom providers from `opencode.jsonc`'s `"provider"` block (id/npm/baseURL, never apiKey) and removes one by id via a string-literal-aware, brace-counting, byte-preserving, atomically-written edit; a non-existent id no-ops cleanly. (Complete 2026-09-09 — see `02-01-PLAN.md`/`02-01-SUMMARY.md`.)
- [x] **REQ-opencode-provider-cross-reference-check**: Before removing a provider, warn (non-blocking) if its id is referenced in `.aikit/review-spec.toml` or the cached model catalog; `skills/ai-kit-opencode-providers/SKILL.md` documents both subcommands and passes `skill-judge` review. (Complete 2026-09-09 — see `02-02-PLAN.md`/`02-02-SUMMARY.md`.)

### Tool-Substitution Awareness Hook

- [x] **REQ-tool-substitution-detection-composition**: Pure, independently-tested live-detection + message-composition functions report which curated `rtk` substitutions (`cat`↔`bat`, `grep`↔`rg`, `find`↔`fd`, `sed`↔`sd`, `ls`↔`eza`) are genuinely active on this machine (binary presence + `registry.toml` `audience` + `rtk init --show`), never reciting catalog intent as verified; this curated set is the single source of truth mirrored by the usage-metrics command-family axis. (Complete 2026-09-09 — see `03-01-PLAN.md`/`03-01-SUMMARY.md`.)
- [x] **REQ-tool-substitution-hook-wiring**: A new Claude Code `SessionStart` hook fires on `"startup"` and `"compact"`, injects the composed message via `hookSpecificOutput.additionalContext`, degrades gracefully (no error, no perceptible delay) when `rtk`/`tools-installer` is absent, and documents opencode's lack of an equivalent hook as an accepted gap. (Amended 2026-09-08: Cursor is NOT an accepted gap — live-verified during Phase 4 discussion that Cursor supports a `sessionStart` hook type, currently active on this machine at `~/.cursor/hooks.json`. The equivalent briefing must also be wired for Cursor's `sessionStart` hook; only opencode remains a genuine, documented gap. Complete 2026-09-09 — see `03-01-PLAN.md`/`03-01-SUMMARY.md`, `03-02-PLAN.md`/`03-02-SUMMARY.md`.)

### Config Doctor

- [x] **REQ-config-doctor-diagnostic-checks**: A read-only Checks Catalog spans Claude Code, opencode, Codex, and Cursor settings (retention, cache TTL, sandboxing, telemetry, permissions, share mode, reasoning effort, history persistence) plus a folded-in cross-runtime `rtk`-Cursor-integration check; informational-only rows (e.g. opencode retention) are never offered as apply actions, lower-confidence rows are visibly labeled, and a runtime with no config file present has its whole section skipped rather than shown as failing. (Amended 2026-09-08: Cursor added as a 4th runtime — the original 12-row catalog covered only Claude Code/opencode/Codex; Cursor's equivalent checks (e.g. `~/.cursor/cli-config.json` permissions, `~/.cursor/sandbox-policies/`) need their own researched, cited rows before planning — this is new research work, not yet done. Row count is no longer fixed at 12 pending that research. Detection of "is this runtime's section shown" is by config-file presence, not by `detect_installed_clis()` binary-on-PATH — a diagnostics tool checks configuration, not CLI availability.)
- [x] **REQ-config-doctor-review-screen**: A dedicated interactive review screen (not folded into `tools/statusline-doctor.py`) shows every check's current value, recommended value, and citation across all installed runtimes in one command; an undeterminable value shows as "unknown," never silently pass/fail.
- [x] **REQ-config-doctor-apply-flow**: A per-item, explicitly confirmed apply step (reusing the opencode-provider-management atomic-write + surgical-edit pattern) names the exact change before writing; security-relevant applies show the literal resulting config; there is no bulk "apply all."

### Usage Metrics Dashboard

- [x] **REQ-usage-metrics-raw-capture**: Per-runtime raw-capture parsers (Claude Code `~/.claude/projects/*.jsonl` and opencode storage/db first; Codex and Cursor follow later) write session logs verbatim/losslessly into an append-only local raw store; one runtime's parser failure, or a runtime's log-format version change, never crashes the others; Cursor's parser is flagged low-confidence (reverse-engineered format); raw/refined data never leave the local machine. (Amended 2026-09-10 (Phase 5, Plan 05-03, Round 1 review): Cursor's `store.db` is confirmed out of scope for structured capture — live-verified to hold only opaque, undocumented BLOB rows (`blobs` table, `meta` table empty). `agent-transcripts/*.jsonl` is Cursor's sole practical raw source for this milestone; `store.db` support is additive future work if the format is ever documented or reverse-engineered.)
- [x] **REQ-usage-metrics-refinement-pipeline**: A refinement pipeline (mechanical `&&`/`;`/`|` decomposer + chronological cwd-resolution state machine) normalizes raw records into one cross-runtime schema (date, model, commands + family, tokens, price); a compound command's control-flow segment is tagged opaque `command_shape: control_flow_script`, distinct from `unclassified`; command "family" tagging mirrors the tool-substitution curated set; normalization happens only in the refined layer.
- [x] **REQ-usage-metrics-dashboard-ui**: A locally-generated, filterable/sortable static HTML dashboard, regenerated by the pipeline script with the refined store's data embedded directly (no export/import step, no browser-sandboxed Artifact mechanism), answers session-grouped queries across the 5 MVP axes directly from refined data with no live re-parse, and never has a hosted-database capability pointed at session content. (Amended 2026-09-08, live-verified during Phase 5 discussion — see `05-CONTEXT.md` D-08/D-09/D-10.)
- [x] **REQ-usage-metrics-classification-refinement-loop**: A runnable, documented offline pattern-mining pass — run only after real historical logs exist, never speculatively — mines accumulated `control_flow_script`/`unclassified` refined entries for recurring shapes and reclassifies them (or attaches a confidence-flagged `inferred_family`) without re-deriving execution; re-running it with improved rules can reclassify historical entries too, since raw is retained losslessly.

## v1.1 Requirements

Requirements for milestone v1.1. Sourced from 3 pending todos captured during
v1.0 (`.planning/todos/pending/`), not from research — scope was already
detailed in the todo files themselves. Each maps to exactly one roadmap
phase.

### AGENTS.md Rules Checker Skill

- [ ] **REQ-agtmd-wrapper**: A new skill wraps `/agent-md-refactor` and can be invoked to check an existing AGENTS.md/CLAUDE.md-style file against a house ruleset, not just perform a plain progressive-disclosure refactor.
- [ ] **REQ-agtmd-makefile-rules**: The skill flags a missing/incomplete Makefile target structure — `setup-env`, one target per pre-commit hook (1:1 with `.pre-commit-config.yaml`), a `validate` target chaining all hook targets lightest-first, `test`/`test-unit` alias, `test-integration`, `e2e-test`, `arch-test` — with per-language tool conventions (e.g. gofmt/black/prettier for formatting).
- [ ] **REQ-agtmd-workflow-rules**: The skill flags absence of: English-only communication, per-plan commit compaction, cross-AI plan-review + cross-AI cheap-model execution (both path-agnostic), rtk/modern-CLI(`rg`/`bat`/`sd`/`fd`/`eza`)/CodeGraph/graphify tool-awareness, no-absolute-paths, no-excuse-deflection on failing tests/bugs, stale-knowledge verification for gray-area topics, theory→hypothesis→spike methodology, no-orphaned-processes, `./tmp/` ephemeral-file convention, README/nested-docs currency, no-uncommitted-files-at-plan-close, and concise (non-narrative) documentation — the full rule set accumulated in the source todo.
- [ ] **REQ-agtmd-skill-pipeline**: The skill is scaffolded via `/superpowers:writing-skills`, reviewed via `/skill-judge` (no remaining Critical/Important finding), and named via `/naming-analyzer`.

### Curated GSD Config Skill

- [ ] **REQ-cfg-curated-questions**: A new skill asks a small, curated question set — not the full `gsd-config`/`gsd-settings` interrogation — and applies the user's preset preferences (high effort for analysis tasks, Haiku for execution, cross-AI execution enabled, convergence of plan checks enabled) by default.
- [ ] **REQ-cfg-writes-config**: The skill generates `.planning/config.json` in the same shape `gsd-settings`/`gsd-config` produce today.
- [ ] **REQ-cfg-schema-validate**: The skill validates the generated config against the open-GSD config JSON schema when one exists.
- [ ] **REQ-cfg-skill-pipeline**: The skill is scaffolded via `/superpowers:writing-skills`, reviewed via `/skill-judge`, and named via `/naming-analyzer`.

### Status-line Quota Color Refactor

- [ ] **REQ-stln-time-relative-color**: Rate-limit bucket coloring in `tools/status-line.py` (`util_render_rate_limits` / `theme.ramps["rate"]`) is computed relative to time-remaining-in-window (using each bucket's `resets_at`), not raw `used_percentage` alone. Color-only change: the displayed `used_percentage` value and `resets_at`-derived reset-time suffix are unchanged — only which ramp color is picked shifts. All window/reset timing values are read from the Claude-provided rate-limit context (`resets_at` etc.) on every render; nothing about window length or elapsed time is hardcoded. Example: identical 50%+ usage reads red near the start of a 5h window, but the same 30% usage late in the window (e.g. hour 4 of 5) can read green/blue — driven purely by (elapsed-fraction-of-window) vs. (usage-fraction), not a static percent-only threshold.
- [ ] **REQ-stln-ramp-tests**: The existing SLO/SLA ramp test pattern in `tests/test_status_line.py` is extended to cover the new time-relative coloring formula.

## v2 Requirements

None. All 14 requirements from the 5 ingested proposal PRDs are v1 scope for
this milestone. (Codex/Cursor coverage inside `REQ-usage-metrics-raw-capture`
is sequenced as later plans within its own phase, not deferred to a future
milestone — see that requirement's acceptance criteria.) v1.1's 10
requirements (see above) are this milestone's own scope, sourced from the
pending-todo backlog rather than from further PRD ingest.

## Out of Scope

| Feature | Reason |
|---------|--------|
| Bulk "apply all" in config doctor | Security-relevant settings must be reviewed per item; bulk-apply was a considered-and-rejected alternative. |
| Config doctor folded into `tools/statusline-doctor.py` | Different domain — that script validates the statusline renderer's own config, not runtime behavioral settings. |
| A real, settable "opencode session retention" config value | No such setting exists upstream; shown informational-only in config doctor. |
| A SessionStart-equivalent hook for opencode | No documented injection point exists today; accepted, documented gap pending upstream support. |
| Hosted-database capability behind the usage-metrics dashboard | Session data must never leave the local machine; privacy-rejected alternative. |
| An export/import step for the usage-metrics dashboard | The dashboard is a locally-regenerated static HTML page with direct filesystem access, not a browser-sandboxed Artifact — no export step is needed (amended 2026-09-08, see `05-CONTEXT.md` D-08). |
| A local HTTP server serving the refined store live (this phase) | Static HTML regenerated with embedded data is simpler to start with; a live server remains a future evolution only if data volume ever requires it (see `05-CONTEXT.md` D-09). |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| REQ-multi-cli-install-single-branch | Phase 1.2 | Complete |
| REQ-multi-cli-runtime-detection | Phase 1.2 | Complete |
| REQ-multi-cli-opencode-ui-research | Phase 1.2 | Complete |
| REQ-opencode-provider-list-remove | Phase 2 | Complete |
| REQ-opencode-provider-cross-reference-check | Phase 2 | Complete |
| REQ-tool-substitution-detection-composition | Phase 3 | Complete |
| REQ-tool-substitution-hook-wiring | Phase 3 | Complete |
| REQ-config-doctor-diagnostic-checks | Phase 4 | Done |
| REQ-config-doctor-review-screen | Phase 4 | Done |
| REQ-config-doctor-apply-flow | Phase 4 | Done |
| REQ-usage-metrics-raw-capture | Phase 5 | Done |
| REQ-usage-metrics-refinement-pipeline | Phase 5 | Done |
| REQ-usage-metrics-dashboard-ui | Phase 5 | Done |
| REQ-usage-metrics-classification-refinement-loop | Phase 5 | Done |
| REQ-agtmd-wrapper | Phase 6 | Pending |
| REQ-agtmd-makefile-rules | Phase 6 | Pending |
| REQ-agtmd-workflow-rules | Phase 6 | Pending |
| REQ-agtmd-skill-pipeline | Phase 6 | Pending |
| REQ-cfg-curated-questions | Phase 7 | Pending |
| REQ-cfg-writes-config | Phase 7 | Pending |
| REQ-cfg-schema-validate | Phase 7 | Pending |
| REQ-cfg-skill-pipeline | Phase 7 | Pending |
| REQ-stln-time-relative-color | Phase 8 | Pending |
| REQ-stln-ramp-tests | Phase 8 | Pending |

**Coverage:**

- v1 requirements: 14 total, mapped: 14, unmapped: 0 ✓
- v1.1 requirements: 10 total, mapped: 10, unmapped: 0 ✓
- Combined: 24 total, mapped: 24, unmapped: 0 ✓

---
*Requirements defined: 2026-09-07*
*Last updated: 2026-09-10 — added v1.1 Traceability rows (REQ-agtmd-*, REQ-cfg-*, REQ-stln-* -> Phases 6-8, Status: Pending) and updated Coverage; v1.0 rows/content unchanged.*
</content>
