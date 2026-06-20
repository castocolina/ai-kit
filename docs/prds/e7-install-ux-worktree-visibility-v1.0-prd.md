# E7 — Install UX + Worktree Visibility — Product Requirements Document (PRD)

> **Capture mode.** This PRD was dumped to stop an implementation that had sprawled.
> FR-7.1 and FR-7.2 carry resolved design decisions (and partial code on
> `feat/e7-install-ux-fixes`). FR-7.3 and FR-7.4 are **intentionally captured at low
> clarity** — they are deferred to a follow-up discussion, not ready for implementation.

## Requirements Description

### Background
- **Business Problem**: Dogfooding the bootstrap install (first on macOS, then confirmed
  on Linux — these are **general** findings, not macOS-specific) surfaced four rough edges
  in the install/status-line UX. They were being fixed ad-hoc on one branch, which sprawled;
  this PRD captures all four as discrete requirements so nothing is lost and each can be
  scoped independently.
- **Target Users**: ai-kit end users installing via the bootstrapper / `setup.py` wizard,
  and agents whose Claude Code session runs inside a git worktree.
- **Value Proposition**: A clean upgrade path from a predecessor install, a reliable
  on-statusline signal of *where* the session is working, and a path toward a less spartan
  installer — without breaking the stdlib-only / slim philosophy.

### Feature Overview
- **Core Features** (the four findings):
  - **① Predecessor-link adoption** — re-point stale skill symlinks from an old ai-kit
    checkout (e.g. the former `uz-kit` repo) instead of leaving them silently broken.
  - **② Worktree visibility** — a dedicated status-line segment that shows the worktree the
    current session is in.
  - **③ "Slowest segment" diagnostic** — surface which segment dominated render time when the
    status line overruns its SLO. *(open / to discuss)*
  - **④ Wizard UX rework** — a richer, still-lightweight interactive installer. *(open / to discuss)*
- **Feature Boundaries**: This epic is install-UX + status-line ergonomics only. It does not
  touch the color subsystem (E4b), external segments (E4c, shipped), or the doc-to-PDF skill (E6).
- **User Scenarios**:
  - A user who previously installed from `uz-kit` re-runs the bootstrap and is offered a
    one-keypress re-point of their existing skill links.
  - An agent is told "create a worktree to build feature X"; from any terminal/IDE the user
    glances at the status line and sees the active worktree name without reading the chat.

### Detailed Requirements

#### FR-7.1 — Adopt skill links from a predecessor install (rename-safe) · **DONE**
- **Decided**: when bootstrap/`setup.py` finds `.claude/skills/*` symlinks pointing at a
  *previous* ai-kit checkout (different `INSTALL_DIR`, e.g. an old `uz-kit` path), it must
  **offer to re-point them to the current install (default action)**, with **drop as the
  alternative**. The prior behavior left such links intact and silent.
- **Status**: implemented and committed (`1236345`) — `predecessor_candidates()` +
  `adopt_predecessor_links()` in `tools/setup.py`, wired into `cmd_install` after
  `prune_stale`, with `installed_links()` refreshed afterward. Covered by
  `TestAdoptPredecessorLinks` (8 tests).
- **Input/Output**: input = the set of installed skill symlinks + their resolved targets;
  output = re-pointed (or dropped) links plus a count summary in the wizard.
- **Edge cases**: a link that already points at the current install is left untouched; a
  broken/dangling link is treated as droppable; dry-run mode reports without mutating.

#### FR-7.2 — Worktree as its own status-line segment (singular, active worktree) · **DESIGN FINAL, IMPL IN PROGRESS**
- **Problem**: when the session runs inside a linked git worktree, the user had no
  on-statusline signal of *where* they are working. Earlier in the E-series this worked
  (the worktree showed when inside `.claude/worktrees/`); it regressed when worktree detection
  was made opt-in/off-by-default, and a subsequent attempt over-built it into a *list of all
  worktrees* with display tiers — which the user rejected.
- **Decided design** (final, supersedes the list version):
  - The **`branch` segment shows ONLY the branch name** with the 🌿 icon. The 🌳 worktree
    glyph it briefly carried is **removed** — branch is just the branch.
  - A **new `worktree` segment** shows **only the worktree the current session is in** (the
    *active* one — never a list, even when 10 worktrees exist):
    - In a linked worktree → `⎇ <worktree-basename>` (basename, truncated to 20 chars with `…`,
      same treatment the `path` segment gives a long repo dir).
    - In a repo but on the main checkout → struck-through `⎇ wt` (strike-out placeholder).
    - Not in a git repo → hidden (returns nothing), like `branch`.
  - **ON by default**, toggled via `segments.worktree` like any other segment. There is **no
    `[git] worktree` knob** — the legacy `[git]` block is tolerated but ignored (a legacy
    `worktree` key under `[git]` does not error; any other `[git]` key still warns).
  - **Shared cached git probe**: one probe feeds `branch` + `dirty` + `worktree`. Branch and
    worktree info (which change rarely) are cached ~5s, keyed by work dir
    (`CC_AI_KIT_GIT_TTL` env override); `dirty` is always read fresh. This addresses the
    finding that on a larger codebase the status line overran its render SLO — the cache lets
    rapid re-renders skip `rev-parse` / `git worktree` calls.
- **Status**: partial code on `feat/e7-install-ux-fixes` (`36bc313`) reflects the earlier
  *list* design and the cached probe; it must be reworked to the singular design above.
- **Remaining implementation work**:
  - Replace `seg_worktrees` (list + tiers) with a singular `seg_worktree`.
  - Drop the 🌳/🌿 worktree glyph branch from `seg_branch`.
  - Add a one-`rev-parse` `_git_worktree_info(work_dir) -> (in_repo, is_worktree, name)`.
  - Simplify `git_snapshot` to carry `in_repo` / `is_worktree` / `wt_name`; remove
    `git_worktrees` (the list function) and its tests.
  - Rename `worktrees` → `worktree` in `SEGMENTS`, `BUILDERS`, `LAYOUT`,
    `SEGMENT_DEFAULTS` (setup), and `statusline.toml.sample`.
  - Update `build_data` + the data dict keys; rework the affected tests.
  - **E2E verification**: prove correct display for worktrees created both inside
    `.claude/worktrees/` and outside at `../worktrees/.ai-kit/…`, and that the main checkout
    shows the struck `⎇ wt`.

#### FR-7.3 — "Slowest segment" diagnostic segment · **OPEN — to discuss**
- **Problem**: on a larger codebase the status line overran its render SLO and there was no
  way to see *which* segment was the culprit.
- **Idea**: a diagnostic segment, sibling to `render_time`, surfacing the single
  most-expensive segment of the last render (name + ms).
- **Open questions** (for the deferred discussion):
  - Always-on, or debug/opt-in only?
  - Cost and mechanism of per-segment timing instrumentation in the packer.
  - Display format and default state.
  - Does the FR-7.2 git cache already close enough of the SLO gap to make this lower priority?

#### FR-7.4 — Wizard UX rework (richer, still-lightweight installer) · **OPEN — to discuss**
- **Problem**: the current bootstrap/wizard interface is spartan (plain numbered menus).
- **Idea**: something closer to the SvelteKit `create` installer — chips / arrow-key
  selection / a nicer TUI feel — while staying lightweight, inspired by how `uv`-based
  installers feel.
- **Decided constraints**: stdlib-only, **no new dependencies**; non-tty / headless is **not**
  a concern (CI / headless users drive it with flags manually).
- **Open questions** (for the deferred discussion):
  - How far to go: full `curses` TUI vs. raw-ANSI arrow-key "chips" vs. polished numbered menu?
  - Scope and maintenance cost vs. the slim philosophy.
  - Which wizard flows benefit most (skills selection, status-line config)?

## Design Decisions

### Technical Approach
- **Architecture Choice**: keep all of E7 inside the existing stdlib-only tools
  (`tools/status-line.py`, `tools/setup.py`); no new runtime dependencies.
- **Key Components**: `setup.py` link reconciliation (FR-7.1); `status-line.py` git probe +
  segment builders and the shared git cache (FR-7.2); packer timing hooks (FR-7.3, if pursued);
  wizard rendering layer (FR-7.4, if pursued).
- **Interface Design**: `segments.worktree` toggle; `CC_AI_KIT_GIT_TTL` env var; legacy
  `[git]` block tolerated-but-ignored.

### Constraints
- **Compatibility**: Python 3.11+ stdlib only; tests via `python3 -m unittest` (not pytest).
- **Performance**: status-line render must stay within its SLO; the git cache exists to
  protect it on large repos.
- **Security**: unchanged from E4c — external segments still run without `shell=True`, with
  SGR-only sanitization, per-script timeout, and silent omission on failure; ai-kit never
  auto-installs providers. (No new surface in E7.)

### Risk Assessment
- **Technical Risks**: the worktree probe must not reintroduce the SLO regression — mitigated
  by the shared cache. The singular rework must not leave dangling `worktrees` (plural) refs.
- **Schedule Risks**: FR-7.3 / FR-7.4 are open-ended; capturing them here de-risks scope creep
  by keeping them out of the FR-7.1 / FR-7.2 delivery.

## Acceptance Criteria

### Functional Acceptance
- [x] **FR-7.1**: a predecessor `uz-kit` skill link is offered re-point (default) or drop;
      already-current links untouched; dry-run reports without mutating.
- [ ] **FR-7.2**: `branch` shows only the branch (🌿, no 🌳); a separate `worktree` segment
      shows `⎇ <name>` in a worktree, struck `⎇ wt` on the main checkout, nothing outside a repo;
      singular (active worktree only); ON by default; `[git]` knob gone; git probe cached ~5s.
- [ ] **FR-7.3**: *(deferred — acceptance to be defined after discussion)*
- [ ] **FR-7.4**: *(deferred — acceptance to be defined after discussion)*

### Quality Standards
- [ ] Code Quality: matches surrounding style; lint clean.
- [ ] Test Coverage: `make test` green; FR-7.2 has unit tests for `seg_worktree`,
      `_git_worktree_info`, and `git_snapshot` cache behavior, plus E2E for both worktree
      locations.
- [ ] `--doctor` reports all segments render cleanly.

### User Acceptance
- [ ] Documentation: README worktree section + `statusline.toml.sample` reflect the singular
      `worktree` segment and `CC_AI_KIT_GIT_TTL`.

## Execution Phases

### Phase 1: FR-7.1 — Predecessor-link adoption · **DONE**
- [x] Implement `predecessor_candidates` + `adopt_predecessor_links`; wire into `cmd_install`.
- [x] `TestAdoptPredecessorLinks` (8 tests).
- **Deliverables**: committed as `1236345`.

### Phase 2: FR-7.2 — Singular worktree segment
- [ ] Rework to singular `seg_worktree`; drop the branch worktree glyph; add `_git_worktree_info`.
- [ ] Simplify `git_snapshot`; remove `git_worktrees` + its tests; rename `worktrees`→`worktree`.
- [ ] Update `build_data`/data dict; rework tests; run `make test` + `--doctor`.
- [ ] E2E: worktrees inside `.claude/worktrees/` and outside `../worktrees/.ai-kit/`; main checkout.
- [ ] Update README + `statusline.toml.sample`.
- [ ] Compact the branch into clean logical commits; finish the branch (merge/publish).
- **Deliverables**: merged `worktree` segment; green tests; updated docs.

### Phase 3: FR-7.3 — Slowest-segment diagnostic · **DISCUSS FIRST**
- [ ] Hold the deferred discussion; resolve the open questions; then plan.

### Phase 4: FR-7.4 — Wizard UX rework · **DISCUSS FIRST**
- [ ] Hold the deferred discussion; resolve the open questions; then plan.

---

**Document Version**: 1.0
**Created**: 2026-06-20
**Clarification Rounds**: 0 (capture mode — per user direction, discussion deferred)
**Quality Score**: FR-7.1 / FR-7.2 ≈ 95/100; FR-7.3 / FR-7.4 ≈ 50/100 (intentionally open)
