# Context Tools Worktree UX Fixes - Product Requirements Document (PRD)

## Requirements Description

### Background
- **Business Problem**: Two related UX defects surface when running the ai-kit installer/wizard from a git worktree. (1) The statusline's `path` and `worktree` ("gittree") segments duplicate the same string, because `path` merely mirrors the literal cwd (collapsing to a basename when too long) rather than conveying "which project," and a worktree session's cwd *is* the worktree directory. (2) The installer performs directory/asset/statusline detection — and even symlink repoint/prune prompts — via raw terminal `print`/`input()` **before** the Textual wizard UI ever mounts. When invoked from a worktree (whose `install_dir` differs from the main checkout), the user is dropped into a plain-text Y/N prompt about `~/.claude/skills` links pointing elsewhere, disconnected from and ahead of the wizard experience.
- **Target Users**: The repo maintainer running `setup.py install`/`reconfigure` from a worktree (or the main checkout), with or without the `alt_git_worktree` statusline segment enabled.
- **Value Proposition**: Statusline segments become non-redundant and semantically distinct (project identity vs. active worktree); the installer's directory/link/tool-detection UX becomes consistent — always inside the TUI — and reflects live state instead of a stale one-shot CLI snapshot.

### Feature Overview
- **Core Features**:
  1. Redefine the `path` statusline segment to always render the **main repo checkout's folder name** ("project root"), regardless of cwd depth or whether the session is inside a worktree.
  2. Move the pre-wizard CLI-side prompts (`prune_stale`, `adopt_predecessor_links`) and detection (`detect_statusline`, component/context-tools catalog probing) so they render and execute **inside** the Textual wizard, with detection kept live/re-probed (mirroring how `status-line.py` itself recomputes per render) instead of a frozen pre-UI snapshot.
- **Feature Boundaries**: No change to the `alt_git_worktree` ("worktree"/"gittree") segment's own logic — it already correctly shows the worktree top-level basename. No change to the *decision semantics* of predecessor/stale-link handling — stays immediate and unconditional, not deferred to Review→Confirm. No change to the "`wizard_app.py` never imports `setup.py`" architecture rule — detection logic stays in `setup.py`/`context_tools.py`; only its trigger point and call-site move.
- **User Scenarios**:
  - Developer runs the installer from inside `.claude/worktrees/<name>` with `alt_git_worktree` enabled — statusline used to show the same worktree name twice; now `path` shows the main repo name, `worktree` shows the worktree name.
  - Developer runs `setup.py install`/`reconfigure` from a worktree whose `install_dir` differs from a prior install — previously got a raw-terminal Y/N wall of text before ever seeing the wizard; now sees the same choice as a screen inside the TUI, and any statusline/tool-detection reflects live directory context rather than a value computed once before the UI existed.

### Detailed Requirements
- **Input/Output**:
  - `seg_path` (`tools/status-line.py:2181-2182`) resolves "project root" via the git common-dir probe (reusing/extending the existing `probe_git_for`/`probe_git_worktree_info` machinery — conceptually `git rev-parse --path-format=absolute --git-common-dir`, parent basename), replacing the current home-relative/cwd-basename (`util_display_dir`) rendering for this segment. Outside any git repo, `path` keeps today's cwd-based fallback.
  - `seg_alt_git_worktree` (`tools/status-line.py:2202-2214`) is unchanged.
  - `adopt_predecessor_links` / `prune_stale` (`tools/setup.py:1055`, `:1126`) move from being called synchronously in `cmd_install()` (`setup.py:2040`, `:2044`, before `launch_wizard()`) to being invoked from inside the wizard — an early Textual screen/step, using the same injected-callable pattern already established for `commit`/`context_tools_run` in `WizardContext` — while preserving today's immediate/unconditional apply semantics.
  - `detect_statusline()` (`setup.py:1352`) and `_build_context_tools_rows()` (`setup.py:1865`) move from `_build_wizard_context()`'s synchronous pre-construction call (`setup.py:1951`, `:1977`) to a background Textual worker triggered on wizard mount, live-probed rather than a one-shot snapshot.
- **User Interaction**: The wizard's first TUI frame renders immediately (no blank-terminal delay), with a loading/probing indicator while detection runs in the background. Predecessor-link and stale-link decisions are presented and confirmed as a wizard screen rather than a raw terminal prompt.
- **Data Requirements**: `WizardContext` gains injected callables for (a) triggering/applying the predecessor/stale-link screen's decision, and (b) running the live statusline/tool detection refresh — both following the existing `commit`/`context_tools_run` pattern. `wizard_app.py` continues to import nothing from `setup.py`/`context_tools.py` directly.
- **Edge Cases**:
  - Session outside any git repo (no common-dir) — `path` keeps current cwd-based rendering.
  - Repo with no linked worktrees — `path` shows its own root name as before (no visible change).
  - Wizard invoked non-interactively/headless (`is_interactive(tty)` false) — predecessor/stale-link handling keeps today's headless warn-only, non-blocking behavior (untouched).

## Design Decisions

### Technical Approach
- **Architecture Choice**: Detection logic stays in `setup.py`/`context_tools.py` per the existing "`wizard_app.py` never imports `setup.py`" rule; only the call site and timing move — from CLI-synchronous/pre-UI to a Textual worker invoked via an injected callable, matching the precedent already set by `commit` and `context_tools_run`.
- **Key Components**: `seg_path` / `util_display_dir` (`status-line.py`); `adopt_predecessor_links`, `prune_stale`, `detect_statusline`, `_build_context_tools_rows`, `cmd_install`, `launch_wizard`, `_build_wizard_context` (`setup.py`); `WizardContext`, `WizardApp` (`wizard_app.py`).
- **Data Storage**: N/A — no persisted-state changes beyond the existing symlink and `settings.json` writes.
- **Interface Design**: New/extended `WizardContext` callables for (a) predecessor/stale-link apply, (b) live statusline/tool detection refresh.

### Constraints
- **Performance Requirements**: The detection worker must not block the first TUI frame; existing per-tool subprocess probing cost is unchanged, only relocated.
- **Compatibility**: The headless/non-interactive install path keeps its current warn-only, non-blocking behavior for predecessor/stale links.
- **Security**: No change beyond existing symlink-safety guards (never clobber a real file or an unrelated foreign symlink).
- **Scalability**: N/A.

### Risk Assessment
- **Technical Risks**: Moving `adopt_predecessor_links`/`prune_stale` into the TUI while keeping "immediate/unconditional" semantics means the wizard must apply filesystem changes before/independent of its own Review-confirm step. Mitigation: give it its own explicit early screen, clearly separated from the Review/Confirm flow, so it doesn't read as part of the deferred install plan.
- **Dependency Risks**: None new — reuses existing `ask_yes_no`, `is_interactive`, `_tty_write` primitives, now driven through Textual widgets instead of raw tty writes.
- **Schedule Risks**: Two logically separate fixes (statusline segment, wizard startup flow) are bundled in one PRD but can be implemented/landed independently if needed.

## Acceptance Criteria

### Functional Acceptance
- [ ] Inside a worktree with `alt_git_worktree` enabled, `path` and `worktree` segments render different strings (project root name vs. worktree name).
- [ ] Outside any git repo, `path` segment rendering is unchanged from current behavior.
- [ ] Running `setup.py install`/`reconfigure` from a worktree no longer prints a raw pre-UI terminal prompt about `~/.claude/skills` (or other categories) pointing at a previous install; the same choice appears as a screen inside the Textual wizard.
- [ ] The `prune_stale` stale-link warning/prompt also renders inside the TUI, not as a raw pre-UI terminal print.
- [ ] Predecessor/stale-link decisions still apply immediately and unconditionally (not deferred to Review→Confirm), matching current semantics.
- [ ] `detect_statusline` and context-tools catalog detection run after the wizard's first frame is visible (no blank-terminal delay), live-probed similar to how `status-line.py` recomputes on each render.
- [ ] The headless/non-interactive install path is unaffected (still warn-only, non-blocking).

### Quality Standards
- [ ] Code Quality: Detection logic remains in `setup.py`/`context_tools.py`; `wizard_app.py` continues to import nothing from either module directly (data/behavior only via `WizardContext`).
- [ ] Test Coverage: Update/add tests in `tests/test_status_line.py` (path segment inside a worktree vs. non-worktree vs. non-repo) and `tests/test_wizard_app.py` / `tests/test_context_tools.py` (predecessor/stale-link screen, detection worker timing).
- [ ] Performance Metrics: First TUI frame renders before detection subprocess probes complete.
- [ ] Security Review: No change to symlink-safety guards.

### User Acceptance
- [ ] User Experience: No duplicated segment text in worktree sessions; no raw-terminal prompts before the wizard UI appears.
- [ ] Documentation: Update `docs/prds/e7-install-ux-worktree-visibility-v1.0-prd.md` cross-reference and `tools/statusline.toml.sample` comments if segment semantics text changes.
- [ ] Training Materials: N/A.

## Execution Phases

### Phase 1: Preparation
**Goal**: Confirm project-root resolution helper and the worker/callable pattern to reuse.
- [ ] Identify or add a git-common-dir resolution helper in `status-line.py` (reuse existing `probe_git_for`/`probe_git_worktree_info` machinery where possible).
- [ ] Confirm the exact `WizardContext` callable shape for predecessor/stale-link apply + detection refresh (mirroring `commit`/`context_tools_run`).
- **Deliverables**: Confirmed helper signatures; no behavior change yet.
- **Time**: 0.5 day.

### Phase 2: Core Development
**Goal**: Implement both fixes.
- [ ] `status-line.py`: change `seg_path` to resolve/render the project-root name; keep the non-repo fallback.
- [ ] `setup.py`: extract the `adopt_predecessor_links`/`prune_stale` invocation and the `detect_statusline`/`_build_context_tools_rows` calls out of `cmd_install`/`_build_wizard_context`'s synchronous pre-UI path; expose them as `WizardContext` callables.
- [ ] `wizard_app.py`: add a screen/step for predecessor/stale-link handling; add an on-mount Textual worker that invokes the detection callables and updates state/loading indicator.
- **Deliverables**: Working wizard with both fixes; no raw pre-UI terminal prompts remain on the interactive path.
- **Time**: 2 days.

### Phase 3: Integration & Testing
**Goal**: Verify behavior end-to-end and update tests.
- [ ] Update/add unit tests for `seg_path` (worktree vs. non-worktree vs. non-repo).
- [ ] Update/add wizard tests (PTY-based, `tests/test_wizard_pty.py`) confirming no raw terminal output precedes the TUI, and that the predecessor/stale-link screen behaves like today's CLI prompt (same default, same apply semantics).
- [ ] Manually verify the headless/non-interactive path is unaffected.
- **Deliverables**: Green test suite covering both fixes.
- **Time**: 1 day.

### Phase 4: Deployment
**Goal**: Ship and validate in real worktree usage.
- [ ] Run the installer from a live worktree and confirm statusline + wizard behavior.
- [ ] Update `statusline.toml.sample` / relevant PRD comments if segment description text needs adjusting.
- **Deliverables**: Verified fix in real usage; docs consistent.
- **Time**: 0.5 day.

---

**Document Version**: 1.0
**Created**: 2026-07-30
**Clarification Rounds**: 2
**Quality Score**: 90/100

**Implemented** — see `docs/superpowers/plans/2026-07-30-context-tools-worktree-ux-fixes.md`. Note: the "component/context-tools catalog probing" scope item under Feature Overview does not apply — that code (`tools/context_tools.py`, `_build_context_tools_rows()`) does not exist on `main`; see the plan's "Correction to originating PRD" section.
