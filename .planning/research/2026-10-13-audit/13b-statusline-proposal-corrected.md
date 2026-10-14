# 13b — Status-line backlog/todo proposal, corrected with the user's input (2026-10-13)

This supersedes §5 of `13-statusline-review.md`. The user's corrections:
1. **Render kill.** Do not conclude that Cursor kills the render. In the user's own tests parts of the render completed without problems, and the user keeps a timing metric for this. The "300 ms kill" came from documentation, not from observation. Treat fetch timing as something to measure.
2. **The POC is a reference, not a promotion candidate.** Whether it is fully functional is unknown and must be inventoried first.
3. **Cursor quota splits into separate segments:** API usage, included usage (auto + models), and extra usage (on-demand).
4. **Coloring for both hosts is a proximity gauge.** Compare spend % with elapsed %, using bands of 5 / 10 / 15 points from optimal.
   - Claude: the v1.3 gap commits already implement ≤5 green, ≤10 yellow, ≤15 orange, >15 red.
   - Cursor must use the same shared helper.

## 5a'. ROADMAP §Backlog: Phase 999.4 replacement text

```markdown
### Phase 999.4: Host-split status line for Claude Code and Cursor CLI (BACKLOG)

**Goal:** [Captured for future planning] Ship a Cursor CLI status line next to
the Claude Code one, both on `main`. Split `tools/status-line.py` into a
host-neutral `common_statusline.py`, one module per host (`claude_statusline.py`,
`cursor_statusline.py`) and an isolated `cursor_quota.py` (the only network and
credential code), with thin `claude-status-line.py` / `cursor-status-line.py`
entries. The Cursor line shows model + context and three separate quota segments:
API usage, included usage (auto + models), and extra (on-demand) usage against
its ceiling, plus the billing-cycle reset. Every quota segment on both hosts is
colored by one shared proximity gauge: spend % vs elapsed % of its window/cycle,
with bands of 5 / 10 / 15 points from optimal (green / yellow / orange / red).
Quota comes from Cursor's undocumented Dashboard API and is always marked
inferred (`≈`). `setup.py` wires each detected host headless first; the
wizard's per-host flow comes last.

**Depends on (before promotion):**

- The 5 quota-gap commits `d23749b..52def0f` cherry-picked onto `main`. The
  user asked for this proximity gauge (5/10/15); confirm the `+`/`-` sign
  rendering, then mark the gap spec accepted and amend PROJECT.md/REQ (burn
  pace is superseded).
- A decision on `worktree-context-tools-manager-plan1` (21 commits, rewrites
  the same `setup.py`/`wizard_app.py` seams): rebase and land, or shelve,
  before Phase A.
- v1.3's own backlog item "999.4 Ponytail …" renumbered to 999.5.

**Linked assets:**

- Design spec + review: `.planning/specs/2026-10-10-host-split-statusline-design.md`
  and `…-REVIEW.md` (copied from branch `spec/host-split-statusline`).
- Review of POC + spec + Claude tip: session research notes `13-statusline-review.md`
  and `13b-statusline-proposal-corrected.md`. Fold them into this phase's CONTEXT.md.
- External: <https://cursor.com/docs/cli/reference/configuration>,
  <https://code.claude.com/docs/en/statusline>. Cursor's `statusLine` schema
  is documented only in the CLI's bundled `statusline` skill.

**Spike / POC (branch `poc/cursor-statusline`): reference only, never promoted
or merged as code.** It was built quickly with cheap models, and how much of it
works end to end has not been inventoried yet. Facts it surfaced:

- Payload (cursor-agent 2026.10.01): `model` has only `id` and `display_name`
  (no `param_summary`/`max_mode`, so no "effort" wording for Cursor);
  `render_width_chars` is present; `used_percentage` is a float.
- Dashboard Connect-JSON: POST `{}` to
  `aiserver.v1.DashboardService/{GetCurrentPeriodUsage,GetHardLimit,GetPlanInfo}`;
  camelCase responses; spend in cents, `hardLimit` in dollars.
- Fetch timing: about 1.9 s for a cold fetch of all three calls in one probe.
  The user's live runs show the render completing, and the user keeps a timing
  metric. Measure render vs fetch timing in discuss-phase before deciding
  between an inline fetch with a cache and a background refresher.
- Process RSS must match `cursor-agent`/`agent` by cmdline (Node's `comm` is
  `MainThread`).

**When extracting (POC review findings to address):**

1. Cache keeps `data_fetched_at` apart from `last_attempt_at`/`last_error`.
   Hide quota on 401/403 and after `cycle_end` instead of showing old data as
   stale indefinitely.
2. One shared gauge helper (spend % vs elapsed %, bands 5/10/15) for Claude
   windows and all three Cursor segments; the POC's 50/80 ramp goes away.
3. The three Cursor segments (API, included auto+models, extra on-demand) are
   separate, individually placeable segments.
4. Reuse `common_statusline.py` instead of the POC's ~620 duplicated lines;
   full banner and role-prefix compliance under `tests/test_arch.py`.
5. `CURSOR_API_ENDPOINT` host allowlist (`*.cursor.sh`), https only.
6. Timeouts on every `git` call (both hosts); reset times shown in local time,
   not UTC; a bad TOML value shows an error segment instead of crashing.
7. Redacted real Dashboard responses as test fixtures.

**Phases (each shippable):** A split (byte-identical Claude render, lint debt
cleared, stale `docs/architecture/status-line-pipeline.md` fixed or deleted) →
B Cursor host + quota segments → C1 headless `--with-statusline[=claude,cursor]`
→ C2 wizard per-host gate.

**Requirements:** TBD
**Plans:** 0 plans

Plans:

- [ ] TBD (promote with /gsd-review-backlog when ready)
```

## 5b'. Todo `2026-10-12-promote-cursor-statusline-poc-into-999-4.md`: replacement text

```markdown
---
created: 2026-10-12T12:50:00.000Z
updated: 2026-10-13T00:00:00.000Z
title: Use the Cursor statusline POC as reference for Phase 999.4 discuss/plan
area: statusline
severity: major
files:
  - .planning/ROADMAP.md
  - tools/status-line.py
  - .claude/worktrees/poc-cursor-statusline/
  - .claude/worktrees/host-split-statusline-spec/.planning/specs/
  - .claude/worktrees/context-tools-manager-plan1/
---

## Problem

Both status lines must end up on `main`. Today `main` ships only the Claude
`tools/status-line.py`, without its latest proximity-gauge coloring: the 5
gap commits `d23749b..52def0f` live only on `gsd/v1.3-curated-config-v2`.
The Cursor line exists only as a quick POC, which is a reference and not a
promotion candidate. How much of it works end to end has not been inventoried,
and a ponytail review found duplication (~620 lines), no stale-data expiry,
the old 50/80 color ramp, and no split between API, included and extra usage.

## Solution

1. Inventory the POC: list which segments and paths work live (with the
   user's timing metric) and which do not, before discuss-phase.
2. Copy the host-split spec + REVIEW onto `main` `.planning/specs/` and amend
   them with the spike facts and the three-segment quota split.
3. Confirm the gap `+`/`-` sign rendering, then cherry-pick `d23749b^..52def0f`
   onto `main` (dry-run verified clean) plus one doc commit: gap spec accepted,
   PROJECT.md decision row, REQ amendment.
4. On the v1.3 branch, renumber "999.4 Ponytail …" to 999.5.
5. Decide `worktree-context-tools-manager-plan1` (land or shelve) before Phase A.
6. `/gsd-review-backlog` → `/gsd-discuss-phase 999.4` (fold research 13/13b,
   decide R3-1..R3-6 and inline vs background fetch from measurements) →
   `/gsd-plan-phase`, on a worktree from `main`.
7. Keep redacted payload and Dashboard responses as fixtures before deleting
   the POC worktree.

## Acceptance

- [ ] POC functional inventory recorded
- [ ] Gap gauge (5/10/15) on `main` for Claude; spec accepted; PROJECT.md/REQ updated
- [ ] Spec + REVIEW on `main`, with the three-segment split
- [ ] Backlog id collision resolved (ponytail → 999.5)
- [ ] Context-tools-manager worktree decided before Phase A
- [ ] 999.4 promoted with plans citing spec, REVIEW and research 13/13b
- [ ] Cursor API / included (auto+models) / extra segments, same gauge as Claude
- [ ] Both entries on `main`, `make test` and `make validate` green
```
