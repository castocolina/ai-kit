# AI-Kit Config Doctor - Product Requirements Document (PRD)

> **Status note**: everything in this document is a PROPOSAL, not an
> accepted decision. Every specific check/value below is written up from
> research with citations — not asserted as definitely correct — and
> remains open to challenge before implementation.

## Requirements Description

### Background

- **Business Problem**: Claude Code, opencode, and codex each have several
  settings that official docs or widely-cited practice recommend changing
  from their defaults — some for cost/token efficiency (cache TTL), some
  for data longevity (history retention), some for safety (sandboxing), and
  some for output quality (reasoning effort). None of these are
  cross-checked today; a user has to know each setting exists, in each
  tool's own docs, and remember to apply it per-machine/per-tool. ai-kit
  already has an analogous pattern for a different domain
  (`tools/statusline-doctor.py`) but nothing that audits these
  cross-runtime configuration settings.
- **Target Users**: ai-kit's own maintainer/user, running Claude Code,
  opencode, and codex on the same machine(s).
- **Value Proposition**: one place to see, per runtime, which recommended
  settings are active vs. still at a suboptimal default, with an explicit,
  reviewable path to apply the ones the user chooses — never a silent
  auto-fix.

### Feature Overview

- **Core Features**: a read-only diagnostic pass across Claude Code,
  opencode, and codex configuration, covering the specific checks in
  §"Checks Catalog" below; a dedicated review screen presenting every
  check's current value, recommended value, and citation; a per-item,
  explicitly confirmed apply step for whichever the user chooses to change.
- **Feature Boundaries**:
  - IN: the specific checks catalogued below (retention, cache TTL,
    sandboxing, telemetry opt-in, reasoning-effort/model defaults,
    history persistence, and — folded in from the sibling
    tool-substitution PRD's Non-Goals — whether `rtk`'s Cursor integration
    is installed on this machine).
  - NOT IN: any setting not explicitly listed in the Checks Catalog (this
    PRD does not attempt to audit "everything configurable" — it's a
    curated, citation-backed list, expandable later); any automatic,
    unconfirmed change to configuration (every apply is a distinct,
    reviewed, explicitly confirmed action per check — never a bulk
    "apply all" default); modifying opencode's session-retention
    behavior (confirmed NOT actually configurable — see Checks Catalog,
    opencode row 4 — so no check/apply exists for it, only a note that
    it's currently unavailable upstream).
- **User Scenarios**:
  - User runs the new diagnostic; sees a table/screen per runtime, each
    row showing check name, current value (auto-detected), recommended
    value, and a one-line "why."
  - User selects one or more checks to apply; for each, the tool shows
    the exact change it's about to make (the literal config key/file/line
    it will write) and asks for explicit confirmation before writing
    anything.
  - A check whose recommended setting genuinely doesn't apply to this
    user's situation (e.g. the 1-hour cache TTL trade-off only pays off
    for idle-then-resume workflows) is still shown, with its trade-off
    noted, but never auto-selected for apply.

### Detailed Requirements

- **Input/Output**: Input = each runtime's own config file/location
  (`~/.claude/settings.json`, `~/.config/opencode/opencode.jsonc`,
  `~/.codex/config.toml` or `$CODEX_HOME`); relevant env vars where the
  setting is env-var-driven instead of file-based (see Checks Catalog).
  Output = the review screen's rendered check table, and — for applied
  checks — the modified config file(s).
- **User Interaction**: a dedicated interactive review-and-apply flow
  (not folded into `tools/statusline-doctor.py`, per this PRD's
  clarification — that script's own scope is the statusline renderer,
  a different domain). Exact UI shape (a new skill's `AskUserQuestion`-
  driven flow vs. a small TUI like `tools-installer`'s own
  `catalog_tui.py`) is an implementation decision, not fixed here — see
  Alternatives Considered.
- **Data Requirements**: no new persistent schema of its own; reads and,
  on explicit confirmation, writes into each runtime's own existing
  config format (JSON, JSONC, TOML respectively).
- **Edge Cases**:
  - A runtime not installed on this machine at all → its whole section is
    skipped (not shown as all-failing), consistent with this PRD's
    "verify installed, don't assume" principle already established for
    the sibling tool-substitution PRD.
  - A setting whose current value can't be determined (file missing,
    unexpected format) → shown as "unknown," never silently treated as
    either pass or fail.
  - Applying a change to a config file this tool doesn't fully own the
    schema of (especially opencode's `.jsonc` with comments, and Codex's
    `.toml`) must not corrupt the rest of the file — same atomic-write +
    minimal-surgical-edit requirement already established in the sibling
    `ai-kit-opencode-provider-management` PRD, reused here rather than
    reinvented.

## Checks Catalog

Every row below is a PROPOSED check, each independently reviewable —
not a committed final list. All findings below are freshly researched for
this PRD with citations; some carry an explicit confidence caveat where the
official docs are ambiguous.

| # | Runtime | Check | Current default | Recommended | Why | Source |
|---|---------|-------|------------------|--------------|-----|--------|
| 1 | Claude Code | Local transcript retention | `cleanupPeriodDays` — 30 days | Raise (e.g. 3650) if 1-year+ retention is wanted | User's own stated goal: keep history much longer | [Data usage](https://code.claude.com/docs/en/data-usage) — note a community-reported bug (GitHub #23710): setting this to literally `0` disables transcript writing entirely rather than meaning "no cleanup"; the check/apply flow must never suggest `0` |
| 2 | Claude Code | Prompt-cache TTL | 5 min | `promptCacheTtl: "1h"` (or `CLAUDE_CODE_PROMPT_CACHE_TTL=1h`) | Avoids full-context reprocessing on idle-then-resume workflows; costs 2x per cache write, so only a net win above ~5-7 cache reads per write | [Prompt caching](https://code.claude.com/docs/en/prompt-caching) |
| 3 | Claude Code | Sandboxed Bash tool | off | `sandbox.enabled: true` (global) or per-project `/sandbox` | OS-level filesystem/network isolation for autonomous execution | [Sandboxing](https://code.claude.com/docs/en/sandboxing) |
| 4 | Claude Code | OpenTelemetry | off | `CLAUDE_CODE_ENABLE_TELEMETRY=1` + exporter env vars | Org/self usage-cost visibility | [Monitoring usage](https://code.claude.com/docs/en/monitoring-usage) |
| 5 | opencode | Session retention | not configurable | N/A — informational only | Confirmed NOT a real shipped setting (only an open, not-planned GitHub feature request, #22110) — this row is shown as "not available upstream," never offered as an apply action | opencode issue #22110 |
| 6 | opencode | `permission` block (bash/edit/webfetch/read) | all default `"allow"` | Lock down per the user's own risk tolerance (`"ask"` or `"deny"` per action) | Wide-open-by-default execution/edit permissions | [Permissions](https://opencode.ai/docs/permissions/) |
| 7 | opencode | `share` mode | `"manual"` | `"disabled"` for privacy-conscious users | Session sharing defaults to manual (not off) | [Share](https://opencode.ai/docs/share/) |
| 8 | Codex | `sandbox_mode` | unset (no sandboxing) | `workspace-write` + `approval_policy = "on-request"` | Safer autonomous execution | [Config reference](https://learn.chatgpt.com/docs/config-file/config-reference) |
| 9 | Codex | `features.hooks` | `false` | Confirm whether the user actually wants Codex's experimental hooks on — informational, not auto-recommended, since it's marked experimental and this PRD's sibling (`ai-kit-tool-substitution-awareness-hook`) explicitly scoped Codex hook work OUT | same as above |
| 10 | Codex | `model_reasoning_effort` | community-documented as `medium` (**official page does not itself assert this default — confidence caveat**) | `high` for complex/multi-file work, per community guides | Default effort may be lower than ideal for agentic coding tasks | [Config reference](https://learn.chatgpt.com/docs/config-file/config-reference); community: [Reasoning effort tuning](https://codex.danielvaughan.com/2026/03/27/reasoning-effort-tuning/) — **this row must be labeled with its lower-confidence sourcing in the actual UI, not presented with the same certainty as the officially-documented rows** |
| 11 | Codex | `history.persistence` | save-all | `"none"` only if the user wants it (privacy trade-off, not a universal recommendation) | Opt-in privacy setting — shown, never defaulted to "recommended: apply" | same as above |
| 12 | Cross-runtime | `rtk` Cursor integration installed | `rtk init --show` reports "not found" on this machine | `rtk init -g --agent cursor` | Folded in from the sibling `ai-kit-tool-substitution-awareness-hook` PRD's Non-Goals — rtk already supports Cursor, just not installed here | this session's own live verification, `rtk init --show` |

## Design Decisions

### Technical Approach

**Alternatives Considered:**

1. **(Rejected) Fold into `tools/statusline-doctor.py`**: that script's
   existing scope is specifically the statusline renderer's own config
   validity — a different domain (rendering correctness, not runtime
   behavioral settings). Rejected per this PRD's own clarification
   (dedicated screen, not folded in).
2. **(Recommended) A new dedicated review-and-apply skill/command**: its
   own interactive flow, modeled loosely on `ai-kit-spec-config`'s
   existing wizard pattern (present findings, ask what to apply, confirm
   before writing) — reuses an established UX shape in this codebase
   rather than inventing a new one, without literally being part of that
   skill (different domain: config-value auditing, not reviewer/model
   selection).
3. **(Alternative, not chosen, noted for completeness) A standalone TUI**
   like `tools-installer`'s own `catalog_tui.py`: more polished, but a
   heavier build for a first version — the `AskUserQuestion`-driven
   flow already used elsewhere in ai-kit is the leaner starting point;
   nothing here rules out a TUI later if the check list grows
   significantly.
- **Key Components**:
  - A checks-catalog data structure (id, runtime, current-value-reader
    function, recommended value, why, source URL, confidence flag for
    rows like #10 above whose default is community-sourced rather than
    officially documented).
  - Per-runtime value readers (JSON/JSONC/TOML/env-var, read-only).
  - The review-and-apply flow (present table → per-item confirm → apply
    writer, reusing the same atomic-write + minimal-surgical-edit pattern
    established in `ai-kit-opencode-provider-management`).
- **Data Storage**: none new.
- **Interface Design**: a new ai-kit skill/command (exact name TBD, e.g.
  `ai-kit-config-doctor`).

### Constraints

- **Compatibility**: never write to a config file for a runtime not
  installed on this machine; never assume a setting exists in a runtime
  version older than what the citation's docs describe (a version check
  or a graceful "couldn't verify" fallback is required, not blind
  application).
- **Security**: applying `sandbox.enabled`, `permission` lockdowns, or
  `sandbox_mode` writes security-relevant config — these applies must be
  at least as carefully confirmed as any other apply here, with the
  literal resulting config shown before writing, never inferred/summarized
  only.
- **Confidence labeling**: any check whose "current default" claim is
  community-sourced rather than confirmed in the tool's own official docs
  (currently: row #10 only) must be visibly flagged as such in the actual
  UI output — never presented with the same certainty as an
  officially-documented row.
- **Skill quality gate**: this PRD creates a new `SKILL.md` — it MUST go
  through the same `skill-judge` review loop established across this
  initiative's other PRDs (no remaining Critical/Important finding, or
  score ≥ 96/120).

### Risk Assessment

- **Technical Risks**: the checks catalog spans three different config
  file formats (JSON, JSONC-with-comments, TOML) plus env-var-driven
  settings — each reader/writer needs its own careful, tested
  implementation; reuse the JSONC surgical-edit approach already designed
  in the sibling provider-management PRD rather than inventing a second
  one.
- **Dependency Risks**: several checks' "recommended" values are drawn
  from third-party/community sources rather than official docs (row #10
  explicitly) — mitigated by the confidence-labeling constraint above.
- **Schedule Risks**: the checks catalog can grow over time without
  blocking a first release — Phase 1 below ships a smaller, high-confidence
  subset first.

## Acceptance Criteria

### Functional Acceptance

- [ ] Every row in the Checks Catalog above is implemented as a
      read-only check showing current vs. recommended value.
- [ ] Row #5 (opencode retention) is shown as informational-only, never
      offered as an "apply" action, since no real setting exists to
      change.
- [ ] Row #10 (Codex reasoning effort) is visibly labeled with its
      lower-confidence sourcing in the UI.
- [ ] No check ever writes to config without an explicit, per-item user
      confirmation naming the exact change about to be made.
- [ ] A runtime not installed on this machine has its whole section
      skipped, not shown as failing checks.
- [ ] Applying a JSONC-format change (opencode) preserves every other
      byte of the file (reuses the sibling PRD's tested surgical-edit
      approach).

### Quality Standards

- [ ] Test Coverage: unit tests per check's value-reader (present/absent/
      malformed config file cases) and for the apply-writer's
      atomic-write + byte-preservation guarantee.
- [ ] Skill Quality: the new `SKILL.md` passes the skill-judge review loop
      before this work is marked complete.
- [ ] Security Review: confirmed every security-relevant apply (sandbox,
      permissions) shows its literal resulting config before writing.

### User Acceptance

- [ ] User Experience: one command surfaces every check across all
      installed runtimes in one screen; applying a change is always a
      distinct, reviewable, confirmed step — never bulk/silent.
- [ ] Documentation: the new skill documents the full Checks Catalog with
      its sources, kept in sync with this PRD's table.

## Execution Phases

### Phase 1: High-confidence checks (read-only)
**Goal**: Ship the checks with official-doc-sourced defaults first.
- [ ] Task 1: implement value readers for rows #1-4, #6-9, #11-12 (every
      row except #10, the community-sourced one, and #5, the
      informational-only one).
- [ ] Task 2: implement the review screen showing all of the above,
      read-only (no apply yet).
- **Deliverables**: a working diagnostic-only pass across all
  high-confidence checks.

### Phase 2: Apply flow
**Goal**: Add the confirmed-apply capability.
- [ ] Task 1: implement the per-item confirm-and-apply flow, reusing the
      atomic-write + surgical-edit pattern from the sibling
      `ai-kit-opencode-provider-management` PRD.
- [ ] Task 2: wire rows #1-4, #6-9, #11-12 into apply (each with its own
      literal-config-shown-before-write confirmation).
- **Deliverables**: a working, confirmed apply path for every
  high-confidence, applicable check.

### Phase 3: Lower-confidence + informational rows
**Goal**: Add row #10 (with its confidence caveat) and row #5
(informational-only) to the review screen.
- [ ] Task 1: add row #10 with visible confidence labeling in the UI.
- [ ] Task 2: add row #5 as informational-only (no apply path).
- [ ] Task 3: run the skill-judge review loop against the finished
      `SKILL.md` before marking this phase — and the PRD — complete.
- **Deliverables**: the complete Checks Catalog live, skill-judge-approved.

---

**Document Version**: 1.0
**Created**: 2026-09-07
**Clarification Rounds**: 2 (plus reuse of prior research from this
session's earlier rounds)
**Quality Score**: 92/100
