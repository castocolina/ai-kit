---
phase: 33-one-config-design
fixed_at: 2026-11-15T00:00:00Z
review_path: .planning/phases/33-one-config-design/33-REVIEW.md
iteration: 3
findings_in_scope: 23
fixed: 14
skipped: 9
status: partial
---

# Phase 33: Code Review Fix Report

**Source review:** `.planning/phases/33-one-config-design/33-REVIEW.md`
**Iteration:** 2 (iteration 1 rows are kept with their commits)
**Verification ran in:** the main checkout (no worktree), branch `gsd/phase-33-one-config-design`.

**Summary:**
- Findings in scope: 23 (the 22 of iteration 1 plus SEC-W1 from the security audit)
- Fixed: 14 (CR-01, CR-51, WR-01, WR-02, WR-03, WR-04, WR-51, WR-52, WR-53, IN-05, IN-06, IN-51 partly, IN-53 partly, SEC-W1)
- Skipped: 9 (all by the brief's own disposition, plus the two IN-51 / IN-53 parts named below)

## Fixed Issues

| Finding | Commit | What changed | Regression test |
|---|---|---|---|
| CR-01 | bf75b05 | iteration 1: project-layer migration and publishes refuse a linked `.aikit` file or one resolving outside `.aikit/` or onto the user config | `TestProjectConfigLink`; runner cases `retry-migrate-project-link`, `-dangling` |
| CR-51 | d5320bc | iteration 1: root-level `runner` keys refused | `pure-toml-subset-refusals`, `retry-migrate-root-runner-key` |
| WR-01 | 5200bcb | iteration 1: dates in the trust digest | `TestCanonicalBytes` |
| WR-03 | f7fbb2c | iteration 1: `trust-local` trusts the bytes it showed | `TestTrustLocalOneRead` |
| WR-04 | 54df2b6 | iteration 1: `_published_intact` compares only `[lanes]` | `TestConcurrency` |
| WR-02 | 916d4a0 | iteration 1: splicer comment attribution | `TestSectionComments` |
| WR-51 + IN-51 | cb8fee5 | `parseTomlSubset` narrowed to D-07: a `'''`/`"""` inside a comment or a one-line string no longer skips the file; a multi-line string inside `[lanes]`/`[[lanes.*]]` is skipped until its delimiter closes (an unclosed one is refused); a multi-line string anywhere else, an array of tables outside `[lanes]` and a nested array stay refused. `__proto__`/`constructor`/`prototype` table or key names under `[runner]` are refused. `docs/config/design.md` (Tables section) and `subprocess-quota-policy.md` state D-07's rule exactly. | `pure-toml-subset-refusals` (new rows), `pure-toml-subset-opaque-strings` |
| WR-53 | 85bdd78 | `--print-argv` skips `migrateRetrySources`. `--self-test`, `--self-test-list` and `--classify-only` already return before the migration, so no other mode needed a change. | case `print-argv-no-migration` (GSD file, user `cross-ai.json`, `.aikit` and the user dir all unchanged) |
| WR-52 + SEC-W1 | 6a70b69 | `splitRetryEntries`: the GSD block and the user `cross-ai.json` migrate key by key; a key that is not bare or is a reserved name, or a value outside the subset, is named with its value in the notice and not migrated, and the block is still retired. `aikitFolderUnsafe`: the project migration is refused (one notice, user layer untouched) when `.aikit` is a link or resolves to the user config folder. D-25 re-read and idempotent publish unchanged. Case times refreshed in `tests/fixtures/cross_ai_selftest_secs.json`. | cases `retry-migrate-odd-key`, `retry-migrate-aikit-link` |
| IN-05 + IN-06 | 8649cb7 | `jev_review consent` with no absolute home returns `{"ok": false, "reason": "no_user_config_dir"}` and exit 2 (no traceback). `render-toml` runs the old-roster refusal and the migration only when the `--out` basename is `config.toml`; the `--replace` guard for an existing `[lanes]` table stays for any name. | `test_consent_without_an_absolute_home_is_a_clear_error_not_a_traceback`; `test_other_out_name_neither_refuses_nor_migrates_a_sibling_roster` |
| IN-53 | e5f0665 | README: a key the file already sets keeps the file's value and the block's value is dropped; design.md: cite `3019-3028`, "by temp file and rename". | `tests/test_config_design_record.py` green |

Notes:
- CR-01, WR-02, WR-03, WR-04, WR-51, WR-52, WR-53 and SEC-W1 are logic changes: fixed, requires human verification.
- SEC-W1 covers the runner migration write path only. The runner's project-layer read through a linked `.aikit` is unchanged (it reads, never writes; not cheap to confine without changing `confinementError` semantics).
- The edit to `skills/ai-kit-cross-ai/references/subprocess-quota-policy.md` was required by the brief; no judged skill folder (`ai-kit-spec-config`, `ai-kit-gsd-curated-config`) was touched. `check-dogfood` result below.

## Skipped Issues

| Finding | Reason |
|---|---|
| IN-51 (part) | skipped: the `5.0`-for-an-integer-key check is not a one-liner (the number scan keeps no float flag), and the U+2028 `kv` regex item was not in the brief |
| IN-53 (part) | skipped: the trailing comment on the `migrated_from` line and the stale `cross-ai.mjs:NNNN` cites in the design.md table row are not in the brief's three items; the "a splice changes only the lines it owns" claim (design.md:145) is still not exact for that one line |
| IN-01 | skipped by the brief: D-08 rewrites a changed key on its own line |
| IN-02 | skipped by the brief |
| IN-03 | skipped by the brief |
| IN-04 | skipped by the brief |
| IN-07 | skipped by the brief: D-11 is owner-locked; secure-phase records it |
| IN-08 | skipped by the brief |
| IN-09 | skipped by the brief |
| IN-52 | skipped by the brief (not a one-line fix) |
| IN-54 | skipped by the brief: the judged skill files under `skills/ai-kit-spec-config/` are frozen |

## Verification

- Runner: `bash tmp/auto/r325/c33-fix-selftest.sh <cases>` with the new and neighbouring cases: `self-test ok` before each runner commit. The template and the dogfood copy were re-rendered with `tmp/auto/r325/c33-sync-runner.py` each time.
- `bash tmp/auto/r325/c33-fix-run.sh tests.test_config_design_record`: exit 0. `... tests.test_jev_fast_decision tests.test_config_layers tests.test_ai_kit_spec tests.test_ai_kit_spec_legacy_config`: exit 0 (4/4).
- Staged-tests hook on every commit: cb8fee5 77/77, 85bdd78 75/75, 6a70b69 139/139, 8649cb7 88/88 modules passed.
- `AI_KIT_REFUSE_REAL_HOME=1 make check-dogfood`: see the orchestrator return message.

---

_Fixed: 2026-11-15_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 2_

## Iteration 3 (close-out orchestrator, after the iteration-2 re-review)

| Finding | Commit | What changed | Regression test |
|---|---|---|---|
| pyright (WR-03 test) | 5234483 | the WR-03 test narrows the digest to bytes before `is_trusted` | `make pyright` rc 0 |
| WR-101 | 61ada6a | `trust-local` relies on the guard inside the migration (pending roster only) | `test_trust_local_trusts_an_in_repo_link_with_nothing_to_migrate` |
| WR-102 | 61ada6a | a `.aikit/config.toml` target is always the project layer for `cfg_migrate_target` | `test_render_toml_refuses_a_project_aikit_dir_linked_to_the_user_folder` |
| WR-51 (doc), WR-103 | e7bdca1, then the closing docs commit (5 jev_review.py / cli.py cites) | design.md skip rule matches the code; moved line cites refreshed | `tests/test_config_design_record.py` green in the commit hook |

Left open (cap reached): WR-02 remainder (comment placement on reorder), WR-51 code remainder (D-07 lists
nested arrays), IN-101, IN-102, IN-103.

