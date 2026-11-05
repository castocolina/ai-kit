---
phase: 29
fixed_at: 2026-11-04T00:00:00Z
review_path: .planning/phases/29-logical-commit-folding-and-the-shared-jev-ladder/29-REVIEW.md
iteration: 1
findings_in_scope: 9
fixed: 9
skipped: 4
status: all_fixed
---

# Phase 29: Code Review Fix Report

**Source review:** 29-REVIEW.md. **Iteration:** 1. Scope: WR-01..WR-07 and IN-01 (IN-02..IN-05 left for the orchestrator).
**Verification ran in:** the main checkout (no worktree), on the affected test modules only.

## Fixed Issues

### WR-01: another phase's plan commit folded into this plan
**Commit:** f5bcd7c. `_plan_unit` returns `"foreign"` for a parsable scope of another phase, so `_owner` (including the merge branch) refuses `plan_not_contiguous`. Test: `fix(28-03)` between two plan commits refuses.

### WR-02: `consent_used` named backends that never answered
**Commit:** 32e88d5. Fixed at the source: `_consent_used(run)` in `jev_review.py` lists only remote rows with a non-error trail entry. The ladder passes the client's list through, so it is consistent. Tests: a local-only answer with a consent record gives no `consent_used`; a TypeSafe 500 gives no TypeSafe entry. Both fail on the old code.

### WR-03: FOLD-8 enforcement wording
**Commit:** 4c09f13. The Enforcement line in `folding-policy.md` now says the merged-branch half is enforced only when the caller supplies merged refs and the `gsd`/`superpowers` forms check the base branch only. No test pins that wording.
- **Follow-up (not done here):** `SKILL.md:37` lists `range_on_merged_branch` as an outcome the user may see; it needs a matching edit after the separate judge run (SKILL.md untouched by instruction).
- **Backlog recommendation:** a repeatable `--merged-ref REF` option on both subcommands, passed through to `merged_refs`, with the unit flow supplying the parent branch.

### WR-04: host config variables reached the fold unit tests
**Commit:** 259a84b. `git_env` drops `HOST_CONFIG_VARS` (now defined in `tests/fold_fixtures.py`, plus `AI_KIT_JEV_CLIENT`); the e2e module no longer duplicates the tuple or the pop loop.

### WR-05: cross-skill rule blind to computed imports
**Commit:** 8abf9c7. `check_cross_skill_refs` reads the leading literal of `importlib.import_module` / `import_module` / `__import__` (plain string or f-string head). Added the `gsd_catalog.py` -> `ai-kit-spec-review` allowlist entry (and its frozen-set twin, which the shrink-only check requires). Non-vacuity: three new violating forms and two clean forms in the existing `TestArchNonVacuity` cases.

### WR-06: GSD command phase regex
**Commit:** 38806b1. `.cjs` now uses `/^\d+(\.\d+)?$/`; e2e test: `--phase 1.2.3` exits 2 with usage.

### WR-07: jev per-call timeout
**Commit:** 2a071f9. `ask_jev` reports `timeout` and the note reads `jev: timeout for c<i>`. `JEV_TIMEOUT_SECONDS` is 130 (30 * (1 + 3) + 10, the ladder's one-item bound plus its client margin), a named constant with a comment because the skill is stdlib-only and cannot import the sibling. Test via `_ask_commits` with a run that raises `TimeoutExpired`. Not restructured into a batched call.

### IN-01: root commit crash
**Commit:** cb9985f. `_commit` raises `FoldError("foreign_merge", ...)` for a commit with no parents; test calls it on the fixture's root commit.

### CR-01: real gsd-tools e2e runs walked up into the checkout's `.planning/` (fixed by the orchestrator)
**Commit:** 0a760d8. Each scratch project in `tests/test_ai_kit_spec_e2e.py` owns `.planning/`, both real cases assert the resolved config is inside their temp root before any write, and `TestRealGsdRunsStayInTheirTempRoot` reruns both with TMPDIR inside the checkout. Not covered: other modules that run the real gsd-tools (the curated-config ones refuse an in-repo TMPDIR instead). A runner-level before/after check on the checkout's config was not added: a content hash misses the identical-content rewrite seen at 18:52, and an mtime check would fail on legitimate concurrent GSD writes.

## Skipped Issues (orchestrator triage)

- IN-02 (trailer matched on any body line): deferred. Only a hand-written commit quoting the trailer at a line start trips it; recommend reading the trailer block only (`git interpret-trailers --parse`).
- IN-03 (a group whose paths cancel out yields an empty commit): deferred. No content is lost; recommend skipping `commit-tree` when the tree equals the parent's.
- IN-04 (one `plan_not_contiguous` hides all status lines): deferred. Read-only report, cosmetic; recommend catching `FoldError` per plan in `_status_line`.
- IN-05 (missing-HOME rule differs in the precompact lookup copy): deferred. Behaviour only differs with no HOME set; recommend stating the rule in `reference.md`'s lookup section.

## Pending after the skill-judge run

- `skills/ai-kit-commit-fold/SKILL.md:37` lists `range_on_merged_branch` as a user-visible outcome; it needs the same caveat as the corrected policy line (WR-03). Backlog recommendation: a repeatable `--merged-ref` option on both fold subcommands.

## Tests run (AI_KIT_REFUSE_REAL_HOME=1)

- tests.test_ai_kit_commit_fold: OK (58)
- tests.test_ai_kit_commit_fold_adapters: OK (21)
- tests.test_ai_kit_commit_fold_e2e: OK (8)
- tests.test_jev_fast_decision: OK (214 before the lint-only edit)
- tests.test_arch: OK (93)
- Pre-commit hooks (ruff, pylint, pyright, staged-tests) passed on every commit; two hook failures (ruff SIM401, ruff E501, pylint R0911) were fixed and re-committed.

_Fixer: Claude (gsd-code-fixer)_
