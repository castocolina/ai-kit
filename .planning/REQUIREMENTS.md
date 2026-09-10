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
- [ ] **REQ-multi-cli-runtime-detection**: A `detect_current_runtime()` function identifies `claude`/`opencode`/`codex`/`cursor`/`unknown`, surfaced as an optional `native_runtime` field on model-catalog entries with `cli: None`; `ai-kit-spec-config/SKILL.md` documents the labeling and passes `skill-judge` review. (Amended 2026-09-08: `cursor` added as a valid value — Phase 1.2's own CONTEXT.md D-02 already scopes `cursor-agent` into the empirical detection research; the original wording omitting it from the valid-value set was an oversight, caught during Phase 4 discussion. Phase renumbered from 1 to 1.2 on 2026-09-08 — see `.planning/ROADMAP.md`'s Phase Numbering note.)
- [ ] **REQ-multi-cli-opencode-ui-research**: A committed markdown research report enumerates opencode's documented plugin hooks, assesses sidebar/status-bar viability, cross-references `anomalyco/opencode#5971`, and gives an explicit recommendation — no code changes.

### Opencode Provider Management

- [ ] **REQ-opencode-provider-list-remove**: New `ai-kit-opencode-providers` skill lists custom providers from `opencode.jsonc`'s `"provider"` block (id/npm/baseURL, never apiKey) and removes one by id via a string-literal-aware, brace-counting, byte-preserving, atomically-written edit; a non-existent id no-ops cleanly.
- [ ] **REQ-opencode-provider-cross-reference-check**: Before removing a provider, warn (non-blocking) if its id is referenced in `.aikit/review-spec.toml` or the cached model catalog; `skills/ai-kit-opencode-providers/SKILL.md` documents both subcommands and passes `skill-judge` review.

### Tool-Substitution Awareness Hook

- [ ] **REQ-tool-substitution-detection-composition**: Pure, independently-tested live-detection + message-composition functions report which curated `rtk` substitutions (`cat`↔`bat`, `grep`↔`rg`, `find`↔`fd`, `sed`↔`sd`, `ls`↔`eza`) are genuinely active on this machine (binary presence + `registry.toml` `audience` + `rtk init --show`), never reciting catalog intent as verified; this curated set is the single source of truth mirrored by the usage-metrics command-family axis.
- [ ] **REQ-tool-substitution-hook-wiring**: A new Claude Code `SessionStart` hook fires on `"startup"` and `"compact"`, injects the composed message via `hookSpecificOutput.additionalContext`, degrades gracefully (no error, no perceptible delay) when `rtk`/`tools-installer` is absent, and documents opencode's lack of an equivalent hook as an accepted gap. (Amended 2026-09-08: Cursor is NOT an accepted gap — live-verified during Phase 4 discussion that Cursor supports a `sessionStart` hook type, currently active on this machine at `~/.cursor/hooks.json`. The equivalent briefing must also be wired for Cursor's `sessionStart` hook; only opencode remains a genuine, documented gap.)

### Config Doctor

- [ ] **REQ-config-doctor-diagnostic-checks**: A read-only Checks Catalog spans Claude Code, opencode, Codex, and Cursor settings (retention, cache TTL, sandboxing, telemetry, permissions, share mode, reasoning effort, history persistence) plus a folded-in cross-runtime `rtk`-Cursor-integration check; informational-only rows (e.g. opencode retention) are never offered as apply actions, lower-confidence rows are visibly labeled, and a runtime with no config file present has its whole section skipped rather than shown as failing. (Amended 2026-09-08: Cursor added as a 4th runtime — the original 12-row catalog covered only Claude Code/opencode/Codex; Cursor's equivalent checks (e.g. `~/.cursor/cli-config.json` permissions, `~/.cursor/sandbox-policies/`) need their own researched, cited rows before planning — this is new research work, not yet done. Row count is no longer fixed at 12 pending that research. Detection of "is this runtime's section shown" is by config-file presence, not by `detect_installed_clis()` binary-on-PATH — a diagnostics tool checks configuration, not CLI availability.)
- [ ] **REQ-config-doctor-review-screen**: A dedicated interactive review screen (not folded into `tools/statusline-doctor.py`) shows every check's current value, recommended value, and citation across all installed runtimes in one command; an undeterminable value shows as "unknown," never silently pass/fail.
- [ ] **REQ-config-doctor-apply-flow**: A per-item, explicitly confirmed apply step (reusing the opencode-provider-management atomic-write + surgical-edit pattern) names the exact change before writing; security-relevant applies show the literal resulting config; there is no bulk "apply all."

### Usage Metrics Dashboard

- [ ] **REQ-usage-metrics-raw-capture**: Per-runtime raw-capture parsers (Claude Code `~/.claude/projects/*.jsonl` and opencode storage/db first; Codex and Cursor follow later) write session logs verbatim/losslessly into an append-only local raw store; one runtime's parser failure, or a runtime's log-format version change, never crashes the others; Cursor's parser is flagged low-confidence (reverse-engineered format); raw/refined data never leave the local machine.
- [ ] **REQ-usage-metrics-refinement-pipeline**: A refinement pipeline (mechanical `&&`/`;`/`|` decomposer + chronological cwd-resolution state machine) normalizes raw records into one cross-runtime schema (date, model, commands + family, tokens, price); a compound command's control-flow segment is tagged opaque `command_shape: control_flow_script`, distinct from `unclassified`; command "family" tagging mirrors the tool-substitution curated set; normalization happens only in the refined layer.
- [ ] **REQ-usage-metrics-dashboard-ui**: A locally-generated, filterable/sortable static HTML dashboard, regenerated by the pipeline script with the refined store's data embedded directly (no export/import step, no browser-sandboxed Artifact mechanism), answers session-grouped queries across the 5 MVP axes directly from refined data with no live re-parse, and never has a hosted-database capability pointed at session content. (Amended 2026-09-08, live-verified during Phase 5 discussion — see `05-CONTEXT.md` D-08/D-09/D-10.)
- [ ] **REQ-usage-metrics-classification-refinement-loop**: A runnable, documented offline pattern-mining pass — run only after real historical logs exist, never speculatively — mines accumulated `control_flow_script`/`unclassified` refined entries for recurring shapes and reclassifies them (or attaches a confidence-flagged `inferred_family`) without re-deriving execution; re-running it with improved rules can reclassify historical entries too, since raw is retained losslessly.

## v2 Requirements

None. All 14 requirements from the 5 ingested proposal PRDs are v1 scope for
this milestone. (Codex/Cursor coverage inside `REQ-usage-metrics-raw-capture`
is sequenced as later plans within its own phase, not deferred to a future
milestone — see that requirement's acceptance criteria.)

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
| REQ-multi-cli-runtime-detection | Phase 1.2 | Pending |
| REQ-multi-cli-opencode-ui-research | Phase 1.2 | Pending |
| REQ-opencode-provider-list-remove | Phase 2 | Pending |
| REQ-opencode-provider-cross-reference-check | Phase 2 | Pending |
| REQ-tool-substitution-detection-composition | Phase 3 | Pending |
| REQ-tool-substitution-hook-wiring | Phase 3 | Pending |
| REQ-config-doctor-diagnostic-checks | Phase 4 | Pending |
| REQ-config-doctor-review-screen | Phase 4 | Pending |
| REQ-config-doctor-apply-flow | Phase 4 | Pending |
| REQ-usage-metrics-raw-capture | Phase 5 | Pending |
| REQ-usage-metrics-refinement-pipeline | Phase 5 | Pending |
| REQ-usage-metrics-dashboard-ui | Phase 5 | Pending |
| REQ-usage-metrics-classification-refinement-loop | Phase 5 | Pending |

**Coverage:**

- v1 requirements: 14 total
- Mapped to phases: 14
- Unmapped: 0 ✓

---
*Requirements defined: 2026-09-07*
*Last updated: 2026-09-08 — amended REQ-usage-metrics-dashboard-ui wording and Out of Scope table per Phase 5 discussion (see `05-CONTEXT.md` D-10)*
