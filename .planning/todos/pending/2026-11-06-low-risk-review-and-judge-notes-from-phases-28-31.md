---
created: 2026-11-06T20:30:00.000Z
title: Low-risk review and judge notes left open by phases 28-31
area: tooling
severity: minor
files:
  - .planning/phases/28-fast-environment-proof-gates/28-REVIEW-FIX.md
  - .planning/phases/29-logical-commit-folding-and-the-shared-jev-ladder/29-REVIEW-FIX.md
  - .planning/phases/29-logical-commit-folding-and-the-shared-jev-ladder/29-JUDGE.md
  - .planning/phases/29.1-stacked-phase-branches-chained-prs-and-the-merge-chain-inserted/29.1-REVIEW-FIX.md
  - .planning/phases/29.1-stacked-phase-branches-chained-prs-and-the-merge-chain-inserted/29.1-JUDGE.md
  - .planning/phases/30-phase-boundary-index-refresh-code-exploration-rules-and-lens/30-REVIEW-FIX.md
  - .planning/phases/30-phase-boundary-index-refresh-code-exploration-rules-and-lens/30-JUDGE.md
  - .planning/phases/30.1-setup-wizard-component-cards-and-host-status-line-panes-inse/30.1-REVIEW-FIX.md
  - .planning/phases/30.2-cursor-status-line-parity-inserted/30.2-REVIEW-FIX.md
  - .planning/phases/31-removals-and-small-defects/31-REVIEW-FIX.md
---

## Problem

Quick task 261106-n8k (2026-11-06) went through every low/info review finding the phase 28-31 run
skipped, deferred or dismissed, and every open medium skill-judge finding. Owner rule (2026-11-06):
fix only a defect that could silently lose data or mislead with no agent noticing; record the rest
here. Each item below is low risk because it fails closed, shows up in a report or a refusal, or is
wording an agent reading the file can resolve itself. Fix them when the owning skill or module is
next touched (skill text items: the Phase 32.x re-judge batches).

## Notes

Format: item (phase): why low risk; how an agent notices it.

### Code and tests

- 28 IN-01 `--pushed` trusts a covering set the mapper marked untrusted (28): owner decision, matches the documented behaviour; the push hook prints the covering set it ran.
- 28 IN-02 guard result regex fails closed on interleaved stderr (28): fails closed; check-dogfood reports `no-write guard missing result`.
- 28 IN-03 env matrix final `rmtree` can replace the verdict's exit code (28): only with a test that leaves a mode-000 folder; the traceback is printed next to the verdict.
- 28 IN-04 a missing module is reported twice per environment (28): cosmetic count; visible in the matrix output.
- 28 IN-06 empty `ALL_SKIP_OK` allowlist (28): documented hook for a future all-skip case, no behaviour.
- 29 IN-02 fold trailer matched on any body line (29): only a hand-written commit quoting the trailer at a line start; the fold's tree-equality check keeps content, and the status form shows the plan as folded.
- 29 IN-03 a group whose paths cancel out gives an empty commit (29): no content lost; the empty commit shows in `git log`.
- 29 IN-04 one `plan_not_contiguous` hides all status lines (29): read-only report; the refusal is printed by name.
- 29 IN-05 missing-HOME rule differs in the precompact lookup copy (29): behaviour differs only with no HOME set; the lookup reports not found.
- 29 WR-03 follow-up: a repeatable `--merged-ref REF` for the `gsd`/`superpowers` fold forms (29): the forms already refuse the base branch; SKILL.md tells the agent to check the PR first.
- 29.1 WR-12 parent merged outside the chain leaves `base_mismatch` (29.1): fails safe with a named refusal; FLOW-11 live run covers it.
- 29.1 WR-16 two pass-through `sync` layers (29.1): cleanup, no behaviour.
- 29.1 IN-01 `stale_lease` detection depends on the locale (29.1): under another locale the push is reported `push_failed`, still a refusal, nothing pushed.
- 29.1 IN-02 MVP target push sets upstream tracking (29.1): visible in `git status`; no wrong push.
- 29.1 IN-03 `merge-chain` reads the record before the lock (29.1): the `--until`, consent and `no_pr` checks refuse before the lock; the lock still serialises merges.
- 29.1 IN-04 uncaught helper exceptions in the adapter and dogfood helpers (29.1): a traceback is loud, never silent.
- 29.1 IN-05 a fold's backup tag is left out of the record when publish refuses (29.1): the tag itself stays in `refs/tags`; the publish refusal is printed.
- 29.1 IN-07 skill README slightly stale (29.1): wording; README is not agent-facing.
- 29.1 IN-08 `stack_backend` has no setter (29.1): undocumented knob, default path works; settings show prints it.
- 29.1 IN-09 SKILL.md says to commit `.gsd-capabilities.json`, which this repo ignores (29.1): `git add` reports the ignore; the agent sees it.
- 29.1 IN-12 duplicated worktree-list parsing and `head_branch` (29.1): duplication, same behaviour.
- 30 WR-08 one-entry seam used by three test sites (30): no defect.
- 30 IN-03 symlinked host files: second write skipped, next install reports `already` (30): wording only.
- 30 IN-04 post-checkout `GIT_DIR` inferred failure (30): not reproduced.
- 30 IN-05 `.graphifyignore` line added once per project (30): the boundary prints a `commit it` note; a later checkpoint refuses `dirty_tree` by name.
- 30.1 IN-01 "unchanged" outcome for an on, ai-kit-owned host still writes and validates (30.1): idempotent write of the same bytes.
- 30.1 IN-05 chmod 0600 on a file mkstemp already made 0600 (30.1): redundant call.
- 30.1 IN-06 resize hook overrides Textual's private `App._on_resize` (30.1): a Textual upgrade that breaks it fails the wizard PTY tests.
- 30.2 IN-02 `--doctor` loads the Cursor config twice (30.2): duplicate read, same output.
- 30.2 IN-03 `cursor_limit_text` builds the cache path by hand (30.2): on purpose (D-12, the label must create nothing); value labelled inferred.
- 30.2 IN-05 plan 04's added test missing from its file list (30.2): process note.
- 31 WR-04 `check-providers` exits 2 on a relative `HOME`/`XDG_CONFIG_HOME` (31): loud exit with a message.
- 31 WR-05 JSONC drift test counts "both None" as agreement (31): five fixtures, each with a parse result in the reader tests; a reader regression fails those.
- 31 WR-06 remainder: the headless summary prints no pruned count (31): each pruned link is printed on its own line.
- 31 WR-07 `git check-ignore` without `--` (31): the target comes from the repo's own AGENTS.md and the existence check runs first.
- 31 IN-02..IN-05 unused `ReadContext.runner`, an unreachable `ValueError` branch, rtk ban identifier forms, `config_get` `@file:` gap (31): no defect today.

### Skill text (judge mediums and carried lows)

- goal-prompt D6-2 "remove this worktree last" loosely scoped (29): the cleanup lines already limit removal to worktrees the run created and recorded, with a clean-tree check first. (The "remove finished backlog entries and directories" half was fixed in 261106-n8k.)
- goal-prompt D8-3 no rule names the run ledger file (29): the cleanup line says "recorded in a run ledger under tmp/"; an agent picks a file there.
- commit-fold D8-3 merged-PR check sits only in the `range_on_merged_branch` row (29, 29.1, 30): the fold refuses the base branch, and a merged branch shows in `gh pr view`.
- commit-fold D3-1 NEVER list without reasons, no Gotchas section (29.1, 30): style; the rules themselves are stated.
- commit-fold D7-1 evals miss the boundary, plan:pre, wave:pre and spec carry (30): fixture tests cover them; evals are a judge-score item.
- commit-fold D8-4..D8-9, D2-1, D7-2, D1-1, D4-2, D5-1, D6-1 lows (30 round 3, `tmp/judge-30/round3/ai-kit-commit-fold.md`): each either refuses by name or is wording (for example `adapter-guide.md` calls the unit id "the phase number"; the code prints `phase-<NN>`).
- superpowers D8-6 the start boundary's `.graphifyignore` note has no commit rule in `start-step.md` (30): Step 5's `checkpoint --final` refuses `dirty_tree` by name.
- superpowers D8-2 a second boundary refresh in the start block (30): costs time, same result.
- superpowers D8-3 long resume paragraph; D6-1 duplicated wave-fold block; D7-1/D7-2 evals for the unit-brief line, quota stops and round-4 escalation (29.1, 30): readability and judge-score items; the shim and tests cover the behaviour.
- lens-brief D7-1 evals miss the host rule and no-brief cases (30): GSD loads the file by path; `make check-dogfood` checks the wiring.
- spec-execute D8-1 (high, pre-existing detector behaviour): already moved to Phase 32.2 (31-VERIFICATION.md).

## Solution

Fix each when its module or skill is next changed; skill-text items go into the Phase 32.x
re-judge batches, which re-run the judge anyway.
