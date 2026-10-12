# Roadmap: ai-kit

## Milestones

- ✅ **v1.0 Multi-CLI Foundation & Config Safety** — Phases 1.1–5 (shipped 2026-09-10)
- ✅ **v1.1 Agent Workflow Hygiene & Tooling Polish** — Phases 6–8.1 (shipped 2026-09-13)
- ✅ **v1.2 ai-kit Rules Skill Family** — Phases 9–15.2 (shipped 2026-09-23)

Phase numbering continues across milestone boundaries and is never reset. Integer `0`
and `999` are reserved by `gsd-core`'s phase-id parser as non-milestone sentinels
(`999.x` = Backlog).

## Phases

<details>
<summary>✅ v1.0 Multi-CLI Foundation & Config Safety (Phases 1.1–5) — SHIPPED 2026-09-10</summary>

- [x] Phase 1.1: Autonomous-Run Infrastructure (INSERTED) (1/1 plans) — completed 2026-09-09
- [x] Phase 1.2: Multi-CLI Runtime Foundation (4/4 plans) — completed 2026-09-09
- [x] Phase 2: Opencode Provider Management (2/2 plans) — completed 2026-09-09
- [x] Phase 3: Tool-Substitution Awareness Hook (2/2 plans) — completed 2026-09-09
- [x] Phase 4: Config Doctor (3/3 plans) — completed 2026-09-10
- [x] Phase 5: Usage Metrics Dashboard (6/6 plans) — completed 2026-09-10

Full details: `milestones/v1.0-ROADMAP.md` · phase dirs: `milestones/v1.0-phases/`

</details>

<details>
<summary>✅ v1.1 Agent Workflow Hygiene & Tooling Polish (Phases 6–8.1) — SHIPPED 2026-09-13</summary>

- [x] Phase 6: AGENTS.md Rules Checker Skill (3/3 plans) — completed 2026-09-11
- [x] Phase 7: Curated GSD Config Skill (4/4 plans) — completed 2026-09-11
- [x] Phase 8: Status-line Quota Color Refactor (1/1 plan) — completed 2026-09-10
- [x] Phase 8.1: Status-line Rate-Burn Pace Fix (INSERTED) (1/1 plan) — completed 2026-09-13

Full details: `milestones/v1.1-ROADMAP.md` · phase dirs: `milestones/v1.1-phases/`

</details>

<details>
<summary>✅ v1.2 ai-kit Rules Skill Family (Phases 9–15.2) — SHIPPED 2026-09-23</summary>

- [x] Phase 9: AGENTS.md Checker Prune (ai-kit-project-rules-agents) (2/2 plans) — completed 2026-09-14
- [x] Phase 10: Makefile Rules Checker (ai-kit-project-rules-makefile) (3/3 plans) — completed 2026-09-14
- [x] Phase 11: Pre-commit Rules Checker (ai-kit-project-rules-precommit) (4/4 plans) — completed 2026-09-14
- [x] Phase 12: Architecture Rules Checker (ai-kit-project-rules-arch) (3/3 plans) — completed 2026-09-14
- [x] Phase 13: Docker Rules Checker (ai-kit-project-rules-docker) (4/4 plans) — completed 2026-09-14
- [x] Phase 14: CI/CD Rules Checker (ai-kit-project-rules-cicd) (4/4 plans) — completed 2026-09-14
- [x] Phase 15: Rules Orchestrator (ai-kit-project-rules-all) (2/2 plans) — completed 2026-09-14
- [x] Phase 15.1: Usage Metrics Dashboard UX/Perf Overhaul (INSERTED) (5/5 plans) — completed 2026-09-21
- [x] Phase 15.2: v1.2 Tech Debt Cleanup (pre-close) (INSERTED) (1/1 plan) — completed 2026-09-23

Full details: `milestones/v1.2-ROADMAP.md` · phase dirs: `milestones/v1.2-phases/`

</details>

## Backlog

### Phase 999.1: Shared core for Config Doctor's TUI and a future CLI variant (BACKLOG)

**Goal:** [Captured for future planning] Phase 4 (Config Doctor) builds the
review screen as a `textual` TUI (D-05/D-06 in
`.planning/milestones/v1.0-phases/04-config-doctor/04-CONTEXT.md`). The user's proposal: a
future CLI-mode Config Doctor should never be a second, independently-written
implementation — the check-running/apply engine (D-01's declarative registry:
read current value, compare to recommended, apply on confirm) should be
extracted into a shared core module, with both the TUI and a future
plain-CLI/scriptable front-end sitting on top of that same core. Not built in
Phase 4 (which ships TUI-only) — this is a note that Phase 4's engine should
be written without coupling check/apply logic directly to `textual` widgets,
so a CLI front-end can be added later without a rewrite. Framed by the user
as a pattern GSD itself could recognize/scaffold ("core logic shared across a
TUI and a CLI front-end"), not just an ai-kit-specific task.
**Requirements:** TBD
**Plans:** 0 plans

Plans:

- [ ] TBD (promote with /gsd-review-backlog when ready)

### Phase 999.2: Cron/scheduling automation for usage-metrics daily ingestion (BACKLOG)

**Goal:** [Captured for future planning] Phase 5 (Usage Metrics Dashboard)
builds the ingestion/refinement pipeline script to be idempotent and
incremental — safe to run once a day (D-07 in
`.planning/milestones/v1.0-phases/05-usage-metrics-dashboard/05-CONTEXT.md`) — but does not
wire an actual recurring trigger for it. Not built in Phase 5 (manual
invocation only) — this is a note that a future phase should add a real
daily automation mechanism (cron job, systemd user timer, or equivalent)
that invokes the already-idempotent pipeline script, without requiring any
change to the script itself. Deferred explicitly by the user during Phase 5
discussion ("the cron can stay deferred to the backlog for now").
**Requirements:** TBD
**Plans:** 0 plans

Plans:

- [ ] TBD (promote with /gsd-review-backlog when ready)

### Phase 999.3: Architecture-layer test suite (BACKLOG)

**Goal:** [Captured for future planning] `tests/test_arch.py` currently
enforces structural invariants (banner-block boundaries, `cfg_`/`probe_`/
`fmt_`/`util_`/`core_`/`seg_` role-prefix conventions) for a single file,
`tools/status-line.py`, via AST parsing. The user's proposal: extend this
into a real architecture-layer test suite following standard
software-architecture testing practices — e.g. dependency-direction rules
(runtime code never importing dev-only packages), layering boundaries
enforced across the whole `tools/`/`skills/` tree (not just one file), and
similar fitness functions for other structurally-significant modules
(`tools/setup.py`, the `ai_kit_spec` package). Not built yet — this is a
note that architecture-fitness testing should generalize beyond the current
single-file, single-convention check. Raised while drafting this project's
`AGENTS.md`/`docs/agent-instructions/testing.md`.
**Requirements:** TBD
**Plans:** 0 plans

Plans:

- [ ] TBD (promote with /gsd-review-backlog when ready)

**Note (2026-09-13):** Promoted and resolved at a scoped-down,
form/convention-only ambition by v1.2's Phase 12 (`ai-kit-project-rules-arch`
— see `REQ-rules-arch`). Phase 12 verifies `arch-test` Makefile target
existence/chaining/AST-only-ness; the fuller dependency-direction/layering-
boundary enforcement ambition described above remains an explicitly-flagged
known gap, not built by Phase 12. This stub is left as-is for history; it is
not duplicated as a second active roadmap item.

### Phase 999.4: Host-split status line for Claude Code and Cursor CLI (BACKLOG)

**Goal:** [Captured for future planning] Split `tools/status-line.py` into
reusable `common_*` modules plus per-host `claude_*`/`cursor_*` modules with
thin `claude-status-line.py`/`cursor-status-line.py` entries, add a
Cursor-native status line (included quota, billing cycle, on-demand ceiling
— quota data from an undocumented Cursor API, flagged as inferred), and make
setup and the wizard run the verify/replace/keep status-line flow per
detected host.

**Linked assets:**

- Design spec + review (open findings R3-1..R3-6; owner decisions final) live
  on branch/worktree `spec/host-split-statusline` →
  `.claude/worktrees/host-split-statusline-spec/.planning/specs/2026-10-10-host-split-statusline-design.md`
  and `…-REVIEW.md` (not yet copied onto `main`).
- External: Cursor CLI `cli-config.json` location and env overrides
  (`CURSOR_CONFIG_DIR`, `XDG_CONFIG_HOME/cursor`):
  <https://cursor.com/docs/cli/reference/configuration>. Claude Code status
  line reference, which Cursor's `statusLine` aligns with:
  <https://code.claude.com/docs/en/statusline>. Cursor's own `statusLine`
  schema is documented only in the CLI's bundled `statusline` skill.

**Spike / POC evidence (not merged; do not treat as production):**

- Branch `poc/cursor-statusline`, worktree
  `.claude/worktrees/poc-cursor-statusline` —
  `tools/cursor-status-line-poc.py`, sample TOML, unit tests, and plan
  `docs/superpowers/plans/2026-10-11-cursor-statusline-poc.md`.
- Proved: Cursor `statusLine` stdin payload + Dashboard Connect-JSON quota
  (included/auto/api %, cycle reset, on-demand ceiling); Claude-like column
  packing/icons/ramps; 3-row layout with quota on row 2; process RSS must
  match `cursor-agent` via cmdline (Node `comm` is often `MainThread`) using
  Claude-style `/proc`|`ps` backends — never the statusline script's own RSS.
- Caveats: quota `%` come from live API/cache (not hardcoded) but look "stuck"
  when Dashboard fetch times out and the POC serves last-good with `≈`/stale
  (`_FRESH_TTL=120`, `_NEG_TTL=600`); cold fetch ~1.9s — prefer
  background/single-flight in the real 999.4 design. Live `cli-config.json`
  wiring was ephemeral and restored to unset after the spike.

**Requirements:** TBD
**Plans:** 0 plans

Plans:

- [ ] TBD (promote with /gsd-review-backlog when ready)
