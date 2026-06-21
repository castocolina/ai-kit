# E7 — Install UX + Worktree Visibility — Product Requirements Document (PRD)

> **Capture mode → resolved (v1.1).** This PRD was dumped to stop an implementation that had
> sprawled. FR-7.1 and FR-7.2 carried resolved design decisions; FR-7.3 and FR-7.4 were originally
> captured at low clarity and deferred. They have since been **designed, implemented, and verified**
> on `feat/e7-loop` via the execution design and the loop PLAN ledger, and a fifth requirement
> (FR-7.5 — bootstrap offers example segments) was added during that work. This document is now
> updated to record the resolved decisions for all five FRs.
>
> **Design source of truth:** `docs/superpowers/specs/2026-06-20-e7-execution-design.md`.
> **Execution ledger:** `docs/superpowers/plans/2026-06-20-e7-loop-PLAN.md`.

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
- **Core Features** (now five — the four findings plus one surfaced during build):
  - **① Predecessor-link adoption** — re-point stale skill symlinks from an old ai-kit
    checkout (e.g. the former `uz-kit` repo) instead of leaving them silently broken. *(DONE)*
  - **② Worktree visibility** — a dedicated status-line segment that shows the worktree the
    current session is in. *(DONE)*
  - **③ "Slowest segment" diagnostic** — surface which segment dominated render time when the
    status line overruns its SLO. *(DECIDED + DONE)*
  - **④ Wizard UX rework** — a richer, still-lightweight interactive installer. *(DECIDED + DONE)*
  - **⑤ Example-segment offer** — the bootstrap discovers `examples/segments/` providers (e.g.
    `sysmem`) and offers to install them, default-ON, with a headless flag. *(DECIDED + DONE)*
- **Feature Boundaries**: This epic is install-UX + status-line ergonomics only. It does not
  touch the color subsystem (E4b), the doc-to-PDF skill (E6). It builds directly on external
  segments (E4c, shipped): FR-7.5 reuses that provider contract to ship copy-and-edit examples.
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

#### FR-7.2 — Worktree as its own status-line segment (singular, active worktree) · **DONE**
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
- **Status**: **implemented and verified** on `feat/e7-loop` (FR-7.2 tasks T2.1–T2.7 + gate G2).
  The singular `seg_worktree` builder, the shared cached `git_snapshot` probe + one-`rev-parse`
  `_git_worktree_info`, the `[git] cache_ttl` / `CC_AI_KIT_GIT_TTL` knob, and the migration of the
  legacy `[git] worktree` toggle to `segments.worktree` all landed; the plural `seg_worktrees`
  list/tier design was dropped. E2E (T2.6) proves `⎇ feat-x` inside `.claude/worktrees/`, `⎇ feat-y`
  outside at `../worktrees/.ai-kit/`, struck `⎇ wt` on the main checkout, and nothing outside a repo.
  G2 code review: 0 HIGH/CRITICAL.

#### FR-7.3 — "Slowest segment" diagnostic segment · **DECIDED + DONE**
- **Problem**: on a larger codebase the status line overran its render SLO and there was no
  way to see *which* segment was the culprit.
- **Decided design** (resolves the prior open questions):
  - **Always-on** (`segments.slowest` ON by default), a diagnostic sibling to `render_time` on the
    diagnostics layout line. It is cheap: the packer already builds each segment, so timing is one
    `time.perf_counter_ns()` bracket per build with negligible overhead.
  - `seg_slowest` reads `data["slowest"] = (name, ns)` — the max recorded by the packer — and renders
    `🐌 <name> <fmt_duration>`, colored via **one shared `[ramp.slowest]` band** (default
    `15ms`→green, `40ms`→yellow, beyond→red+bold; no per-segment override bands).
  - **Accuracy rules** (G3 review): `slowest` sits **last** on the diagnostics line so every other
    segment is timed before it reads the max; the meta-segments `render_time` and `slowest` are
    **excluded** from being crowned; only segments actually **kept** (not overflow-dropped) are
    recorded — so it reports the true render-wide slowest *visible, non-meta* segment.
  - The FR-7.2 git cache narrowed but did not fully close the SLO gap, so this diagnostic is still
    worth shipping always-on.
- **Status**: implemented and verified on `feat/e7-loop` (T3.1–T3.4 + gate G3, 0 unresolved HIGH).

#### FR-7.4 — Wizard UX rework (richer, still-lightweight installer) · **DECIDED + DONE**
- **Problem**: the current bootstrap/wizard interface is spartan (plain numbered menus).
- **Decided design** (resolves the prior open questions) — a **hybrid B+A**, not a full `curses` TUI:
  - **One shared `Selection` model** (ordered `(category, name, enabled)` + cursor) drives both the
    skills picker and the segment toggles, so the two render modes never diverge.
  - **Mode B** — a polished numbered menu with grouping, per-item descriptions, `all`/`none`/`done`,
    an `on/off` word column, and a **live preview footer** that calls the real `status-line.py`
    render with the in-progress config. It is fully **tty-agnostic** (renders without a terminal).
  - **Mode A** — a raw-ANSI **arrow-key chip selector** (`◉/◯/❯`, ASCII `[x]/[ ]/>` fallback),
    bounded redraw (cursor-up + erase-line, never alt-screen), windowed scroll, `SIGWINCH` redraw,
    behind a **conjunctive tty gate** (stdin&stdout isatty AND `TERM`∉{dumb,""} AND cols≥40 AND
    rows≥8); `--plain` / `AIKIT_PLAIN=1` forces Mode B. A `termios` raw-mode context manager
    guarantees terminal restore (cursor + SIGINT handler) on **every** exit path, including
    terminal disconnect (the reader cancels to the safe default instead of crashing or busy-looping).
  - **Constraints kept**: stdlib-only, **no new dependencies**. *(Revised from the original capture:
    headless IS now a first-class contract — any hostile/absent-tty condition degrades cleanly to
    Mode B / the flag-driven default, and that path is unit- and pty-E2E-tested.)*
- **Status**: implemented and verified on `feat/e7-loop` (T4.1–T4.7 + gate G4: ui-ux-designer
  plan/exec/e2e reviews + pty E2E for both modes; both G4 HIGHs on the disconnect/teardown path fixed).

#### FR-7.5 — Bootstrap offers example segments (default ON) · **DECIDED + DONE**
- **Problem** (surfaced during the FR-7.4 wizard build): ai-kit ships copy-and-edit example external
  segments under `examples/segments/` (e.g. `sysmem`, the machine's available RAM), but a new user had
  no path to install one short of hand-copying it into their config dir and `chmod +x`.
- **Decided design**:
  - The installer **scans `examples/segments/`**, parses each provider's `# ai-kit-segment: … id=<slug>`
    header (the same marker `status-line.py` reads — the matcher is kept **byte-identical** to the
    renderer's `_SEG_HEADER_RE` so the two never disagree on what is a provider), and **offers every
    example pre-checked** (default-ON) through the shared `Selection` picker.
  - Chosen examples are **installed into the XDG-aware config segments dir**
    (`resolve_paths(env).config_dir/segments`, honoring `XDG_CONFIG_HOME`), made executable, and the
    write is **atomic** (temp file in the same dir + `os.replace`). It is **idempotent** (unchanged
    dest skipped, re-run never duplicates) and **robust** (a bad/blocked dest is skipped with a warning,
    never aborting the whole install). External segments are default-ON via the renderer's discovery, so
    no `[segments] <id> = true` write is needed.
  - **Headless contract**: `--examples=all|none|<ids>` (default = all). A non-tty / flag-driven run
    **never prompts**; `all`/`none` are case-insensitive, explicit ids are matched verbatim.
- **Status**: implemented and verified on `feat/e7-loop` (T5.1–T5.5 + gate G5: code review + `/simplify`;
  the one HIGH — unguarded dest write — and the header-parser parity finding fixed and re-reviewed clean).
  E2E (T5.4) installs `sysmem` end-to-end into a temp HOME and asserts it renders in the status line.

## Design Decisions

### Technical Approach
- **Architecture Choice**: keep all of E7 inside the existing stdlib-only tools
  (`tools/status-line.py`, `tools/setup.py`); no new runtime dependencies.
- **Key Components**: `setup.py` link reconciliation (FR-7.1); `status-line.py` git probe +
  segment builders and the shared git cache (FR-7.2); packer per-segment timing hooks + `seg_slowest`
  + the `[ramp.slowest]` band (FR-7.3); the shared `Selection` model, Mode B menu, `termios` raw-mode
  manager, and Mode A chip selector in `setup.py` (FR-7.4); example-segment discovery + atomic install
  in `setup.py` (FR-7.5).
- **Interface Design**: `segments.worktree` / `segments.slowest` toggles; `CC_AI_KIT_GIT_TTL` and
  `[git] cache_ttl`; legacy `[git]` block tolerated-but-ignored; `[ramp.slowest]` color band;
  `--plain` / `AIKIT_PLAIN=1` wizard mode override; `--examples=all|none|<ids>` install flag.

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
- **Schedule Risks**: FR-7.3 / FR-7.4 were open-ended at capture; capturing them here de-risked
  scope creep by keeping them out of the FR-7.1 / FR-7.2 delivery, and they have since been
  designed, implemented, and gate-reviewed on `feat/e7-loop` (along with the added FR-7.5).

## Acceptance Criteria

### Functional Acceptance
- [x] **FR-7.1**: a predecessor `uz-kit` skill link is offered re-point (default) or drop;
      already-current links untouched; dry-run reports without mutating.
- [x] **FR-7.2**: `branch` shows only the branch (🌿, no 🌳); a separate `worktree` segment
      shows `⎇ <name>` in a worktree, struck `⎇ wt` on the main checkout, nothing outside a repo;
      singular (active worktree only); ON by default; `[git]` knob gone; git probe cached ~5s.
- [x] **FR-7.3**: always-on `slowest` segment renders `🐌 <name> <ms>` for the true slowest
      *visible, non-meta* segment, colored via one shared `[ramp.slowest]` band; sits last on the
      diagnostics line; `render_time`/`slowest` never crowned; overflow-dropped segments not recorded.
- [x] **FR-7.4**: hybrid wizard — shared `Selection` model; polished Mode B numbered menu with live
      preview (tty-agnostic); Mode A arrow-key chip selector behind the conjunctive tty gate;
      `--plain`/`AIKIT_PLAIN` forces B; terminal always restored (cursor + SIGINT) on every exit path
      incl. disconnect; stdlib-only; pty E2E for both modes.
- [x] **FR-7.5**: bootstrap offers `examples/segments/` providers pre-checked; installs chosen ones
      atomically + executable into the XDG segments dir, idempotent + skip-on-bad-dest; header matcher
      byte-identical to the renderer; `--examples=all|none|<ids>` headless contract never prompts.

### Quality Standards
- [x] Code Quality: matches surrounding style; lint clean (`make lint`).
- [x] Test Coverage: `make test` green; FR-7.2 has unit tests for `seg_worktree`,
      `_git_worktree_info`, and `git_snapshot` cache behavior, plus E2E for both worktree
      locations; FR-7.3/7.4/7.5 have unit + E2E (slowest accuracy, pty wizard, sysmem install).
- [x] `--doctor` reports all segments render cleanly.

### User Acceptance
- [x] Documentation: README worktree section + `statusline.toml.sample` reflect the singular
      `worktree` segment and `CC_AI_KIT_GIT_TTL`. *(Final closeout re-checks README/sample coverage of
      `slowest`, the wizard modes, and example segments under C2/C3.)*

## Execution Phases

### Phase 1: FR-7.1 — Predecessor-link adoption · **DONE**
- [x] Implement `predecessor_candidates` + `adopt_predecessor_links`; wire into `cmd_install`.
- [x] `TestAdoptPredecessorLinks` (8 tests).
- **Deliverables**: committed as `1236345`.

### Phase 2: FR-7.2 — Singular worktree segment · **DONE**
- [x] Rework to singular `seg_worktree`; drop the branch worktree glyph; add `_git_worktree_info`.
- [x] Simplify `git_snapshot`; remove `git_worktrees` + its tests; rename `worktrees`→`worktree`.
- [x] Update `build_data`/data dict; rework tests; run `make test` + `--doctor`.
- [x] E2E: worktrees inside `.claude/worktrees/` and outside `../worktrees/.ai-kit/`; main checkout.
- [x] Update README + `statusline.toml.sample`.
- [ ] Compact the branch into clean logical commits; finish the branch (merge/publish). *(CLOSEOUT C4/C5)*
- **Deliverables**: merged `worktree` segment; green tests; updated docs.

### Phase 3: FR-7.3 — Slowest-segment diagnostic · **DONE**
- [x] Per-segment timing in the packer (`data["slowest"] = (name, ns)`); single `[ramp.slowest]` band.
- [x] `seg_slowest` builder (ON by default); accuracy fixes (last on line, exclude meta, kept-only).
- [x] Unit tests (timing, ramp, accuracy) + `--doctor`; gate G3 review clean.

### Phase 4: FR-7.4 — Wizard UX rework · **DONE**
- [x] Shared `Selection` model; polished Mode B menu + live preview; `termios` raw-mode manager.
- [x] Mode A chip selector behind the conjunctive tty gate; hardened against terminal disconnect.
- [x] Unit + pty E2E for both modes; ui-ux-designer plan/exec/e2e reviews; gate G4 clean.

### Phase 5: FR-7.5 — Example-segment offer · **DONE**
- [x] Discover `examples/segments/` providers (header `id=`); offer pre-checked via the shared model.
- [x] Atomic, executable, idempotent install into the XDG segments dir; `--examples` headless flag.
- [x] Unit tests + sysmem E2E; gate G5 review clean (header parser aligned byte-for-byte with renderer).

### Closeout
- [ ] Full verification sweep, final holistic review, compact into per-FR commits, finish the branch
  *(CLOSEOUT C2–C5 in the loop PLAN ledger)*.

---

**Document Version**: 1.1
**Created**: 2026-06-20
**Updated**: 2026-06-20 (capture-mode FRs resolved; FR-7.5 added; all five FRs implemented + verified
on `feat/e7-loop`)
**Clarification Rounds**: 0 (capture mode → resolved during execution on `feat/e7-loop`)
**Quality Score**: FR-7.1 … FR-7.5 ≈ 95/100 (all designed, implemented, and gate-reviewed)
