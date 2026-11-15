---
phase: "33"
slug: "one-config-design"
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: "2026-11-15"
---

# Phase 33 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| Project layer (`.aikit/config.toml`, old `.aikit/review-spec.toml`) | A cloned repository controls these files; command-bearing lanes run only after trust (D-11) | lane commands and runtime/model pairs (untrusted input) |
| User layer (`${XDG_CONFIG_HOME:-~/.config}/ai-kit/`) | The user's own config, trust store and secrets; never resolved from the cwd | roster, trust records, secrets.env (sensitive) |
| GSD config (`.planning/config.json` and workstream copies) | The runner removes only the `cross_ai_retry` block; ai-kit writes no other GSD key | retry tuning values |
| Runner child processes | External CLIs started from trusted lanes only | prompts, model ids |
| Judge lanes (plan 33-12) | External referees read the repo with a clean-tree check | skill text, verdicts |

---

## Threat Register

Source: the `<threat_model>` tables of 33-01..33-12-PLAN.md. Verified by gsd-security-auditor (opus, ASVS L1,
block_on high) on 2026-11-15 against the tree after review fixes bf75b05..916d4a0: SECURED, 50 of 50 rows closed.

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-33-01 | Tampering | toml_splice set_table/set_array/remove_table | high | mitigate | every operation re-parses its result with tomllib and raises SpliceError unless it equals the intended document; TestSpliceRefusals proves the check is not vacuous; a changed entry is edited block by block, so comments inside it survive (C1-1), and an inserted entry lands in its intended position (C1-2); a key under an implicit parent gets the missing block (C2-1); a header name is cut outside quotes, so a bracketed scope table the runner wrote is kept whole (C2-2); a nested array of tables inside a changed entry, or dotted keys of an implicit table, are refused, never rewritten | closed |
| T-33-02 | Tampering | toml_splice.publish / cache.cache_write_bytes | high | mitigate | temp file in the target folder, fsync, os.replace, folder fsync; an interrupted publish leaves the old file (TestPublish); invalid TOML is never written | closed |
| T-33-03 | Information disclosure | publish file mode | medium | mitigate | a new file gets 0600 (mkstemp), an existing file keeps its mode, a symlink's target is written so the link is not replaced by a world-readable copy Since review fix CR-01 (bf75b05) the project layer never writes through a link: `config_io.cfg_confine_project_file` refuses a linked `config.toml` or old roster, a real path outside `.aikit/` and one onto the user `config.toml` (tests/test_config_layers.py TestProjectConfigLink). | closed |
| T-33-SC | Tampering | package installs (one row per plan, 12 rows) | low | accept | no package install in this plan | closed (accepted) |
| T-33-04 | Tampering | resolveRetry project layer | medium | mitigate | every value still passes validateRetryKey (bounded ranges, hard waits at most capS, capS clamped to 14400); a symlink leaving `.aikit` is refused by confinementError; the same exposure existed with the GSD block, which a repository also controls | closed |
| T-33-05 | Denial of service | readConfigText / readTomlSubset | medium | mitigate | 1 MiB cap and regular-file check before any read (one copy of the checks in readConfigText); invalid UTF-8, anything outside the subset and a table/value collision in either order (C1-4) skip the file with one notice and the next source fills the keys (fail closed, never a crash or a TypeError) | closed |
| T-33-06 | Spoofing | aiKitConfigDir | medium | mitigate | a relative or blank XDG_CONFIG_HOME is ignored and an unset, empty or relative HOME yields no user layer with no ambient home lookup, so a working folder is never used as the user layer and every copy agrees (self-tests pure-config-dir-rule, pure-retry-user-config-without-home) | closed |
| T-33-07 | Spoofing | every user-dir resolver copy | high | mitigate | relative and blank values are ignored and an unset, empty or relative HOME yields no folder with no ambient lookup (C1-3), so a repository cannot supply the "user" layer, trust store or secrets file and no copy guesses `/` or the working folder; the parity test pins every copy on the HOME-unset and HOME-empty rows with the ambient lookups patched to fail | closed |
| T-33-08 | Tampering | `_recover_incompatible_config` | medium | mitigate | `.bak` first, then temp file plus os.replace with the old mode; interruption keeps the live file (tests) | closed |
| T-33-09 | Information disclosure | local_secrets / jev_review secrets.env | medium | mitigate | both readers now read the same file; values are never printed or logged; the test sentinel never reaches output | closed |
| T-33-10 | Tampering | removeRetryBlock / writeFileAtomic on config.json | high | mitigate | the result must JSON.parse and equal the original object minus the block before any write; the removal is computed from the snapshot and written only while the file still equals it (C1-6); every migration read refuses invalid UTF-8, so no replacement character is ever published (C1-8); temp file beside the real path, fsync, rename, mode kept; cases keep-bytes, last-key, symlink, interrupted, snapshot-changed, invalid-utf8 | closed |
| T-33-11 | Repudiation | migration notices | low | mitigate | one notice per migrated file naming source and target; the user JSON is renamed, never deleted; `[runner] migrated_from` records every source. Residual, accepted (review concern C3-3): the locked D-14 order is merge, retire, record (recording first would ignore a block that was never retired), so a stop between retiring a source (step 2) and recording it in `migrated_from` (step 3) leaves no marker; a block or `cross-ai.json` re-added there later migrates again instead of being ignored, merging under D-14's target-wins rule (its conflicting keys are named in a notice and dropped) and, for the user JSON, renamed to the first free `cross-ai.json.migrated.<n>`, so nothing already migrated is lost or overridden | closed |
| T-33-12 | Elevation of privilege | GSD file read outside `.planning` | medium | mitigate | readJsonObject keeps confinementError: a config.json whose real path leaves `.planning` is not read or rewritten | closed |
| T-33-13 | Tampering | concurrent migrations into one config.toml (runner scopes, user layer, roster migration of Plan 05) | medium | mitigate | no lock exists (D-25): `mergeTomlTable` re-reads before publishing (rebuild on change), publishes by temp plus rename and re-reads after publishing; a source is retired only after its values are confirmed in the target and only while it still equals its snapshot, so an overwritten publish keeps the source and the next run merges again (retry-migrate-overwritten, snapshot-changed, user-json-changed); a migration error is logged and never stops the dispatch. Residual, accepted under D-25 (the owner chose no lock): a writer that read the target before our publish and renames after our post-publish re-read replaces our values after our source was retired; the window is that writer's read-to-rename span (one temp write plus fsync), both migrations run once per machine, the user JSON stays recoverable as `cross-ai.json.migrated`, and a GSD block's values are then lost; /gsd-secure-phase reviews this row | closed |
| T-33-14 | Elevation of privilege | migrate_layer trust carry | high | mitigate | a record is written only when the old file's exact bytes were trusted under the old rule in the user's own `review-spec-trust/`, and only by the run that publishes the new lanes; an untrusted file gets none (TestTrustCarry); the canonical bytes cover entries that override user command entries and entries sharing a key with a command entry of the same file (D-11 refinements, C1-12) | closed |
| T-33-15 | Tampering | migrate_layer | high | mitigate | parse-and-compare before publish, a pre-publish re-read that rebuilds from fresh bytes, atomic publish, a post-publish re-read that compares the whole document, rename only after and only while the old file equals its snapshot; failures and concurrent writes leave the old file (TestInterruptions, TestConcurrency); residual under D-25 (no lock) shared with T-33-13: a writer that read before our publish and renames after our post-publish check can replace the new lanes after the old file was renamed; its text stays recoverable as `review-spec.toml.migrated` Since review fix WR-04 (54df2b6) the post-publish re-read compares the `[lanes]` table only, which is the table trust covers. | closed |
| T-33-16 | Information disclosure | migrate_layer | medium | mitigate | only the old roster's own text is copied; nothing reads the environment or secrets.env (TestNoSecretCopied); notices name paths, never values | closed |
| T-33-17 | Tampering | command_lanes_bytes | medium | mitigate | sha256 over canonical JSON (sorted keys, fixed separators, ASCII) through hashlib; role and position order is fixed, so equal entries always give equal bytes; every entry that can change an effective command after cfg_merge_reviewers (a `command` entry, an entry sharing its key in any role, a user-command override) is in the list (C1-12) | closed |
| T-33-37 | Elevation of privilege | restarted migration after a failed rename; revoke before the first migration | high | mitigate | a `completed` run never reads the legacy trust record, so trust is never re-derived after `trust-local --revoke` (C1-10, TestInterruptions revoke case); a run cut off between the publish and the trust write fails closed (untrusted, the trust-local instruction is printed); `revoke_legacy_trust` deletes the old-rule records of the old roster, so a revoke before the first migration leaves nothing to carry (C2-3, `test_revoke_before_first_migration_carries_nothing`; the CLI wiring is Plan 07, T-33-36) | closed |
| T-33-18 | Tampering | curated-config and cross-ai docs | low | mitigate | the docs no longer direct anyone to hand-edit a key into GSD's config; the test pins the documented table to the template values so the docs cannot drift | closed |
| T-33-19 | Elevation of privilege | cfg_resolve trust gate (D-11 narrows what HARD-03/HARD-05 hashes; /gsd-secure-phase must review it) | high | mitigate | the digest covers every project row that can change an effective command entry after `cfg_merge_reviewers`: a row with `command`, a row sharing its `key` with a command row of the same file in any role, duplicates included (C1-12), and a row overriding a user command entry (unless local-only, where the user file is never read); untrusted means the whole project `[lanes]` is ignored with a warning; TestTrustRule pins edit-keeps, edit-drops, the override case and the duplicate-key row. Narrowed surface, accepted under D-11 (owner decision): without a new trust a repository can still change rows whose key matches no command row (table-runtime lanes the runner builds from its own table), `[lanes.policy]` (ladder order and mode), `strategy` and every other table; none of them can change a command's argv | closed |
| T-33-20 | Spoofing | trust record key | medium | mitigate | records stay keyed by the realpath of the project config.toml plus the digest, under the user's own config folder (`config-trust/`), never in the project | closed |
| T-33-21 | Denial of service | broken config.toml | medium | mitigate | invalid UTF-8 or TOML, a non-table `[lanes]` or a failed migration raise ConfigError (exit 2) naming the file: review is never silently disabled | closed |
| T-33-22 | Information disclosure | check-providers / --no-migrate | low | mitigate | read-only paths: a pending legacy roster is read in memory and reported, nothing written; provider ids only, never keys | closed |
| T-33-36 | Elevation of privilege | `trust-local --revoke` before the first migration (C2-3) | high | mitigate | the revoke deletes the `config-trust/` records of the config.toml real path and, through `config_migrate.revoke_legacy_trust`, the old-rule records of the old roster's real path, and runs before any migration, so the next read migrates the roster untrusted and ignores its command entry; `TestTrustLocalRevokeLegacy` pins it end to end | closed |
| T-33-23 | Spoofing | untrusted-config instructions | low | mitigate | the warning prefix and the `trust-local --show` before trust sequence are unchanged; only the file name changes, so agents keep showing commands before any trust | closed |
| T-33-24 | Tampering | render-toml --out | high | mitigate | an existing roster, a `[lanes]` table or an old `review-spec.toml` beside the target, is replaced only with `--replace` (the user's approval); the guard runs before the migration, so a refusal writes nothing at all (C1-17, C1-18); other tables are kept (tests) | closed |
| T-33-38 | Denial of service | render-toml target read | medium | mitigate | the target is read with `cfg_read_bytes` and `cfg_parse_toml_bytes`, so an unreadable, malformed or non-UTF-8 target is a ConfigError, exit 2, file byte-equal, never a traceback or a partial write (C1-16) | closed |
| T-33-25 | Tampering | cfg_render_lanes / publish | high | mitigate | every splice is verified by re-parse; the final roster check compares the written lanes; atomic publish with fsync; interrupted write keeps the old file | closed |
| T-33-26 | Elevation of privilege | lane entries written | medium | mitigate | validate_reviewer_fields still rejects `route`, nested values, bad purposes and invalid runtime/command pairs before anything is written; a written project command entry needs a new trust (render-toml never trusts) | closed |
| T-33-27 | Elevation of privilege | spec-config trust instructions | medium | mitigate | the NEVER rule (no trusting `trust-local` without an explicit yes after `--show`) stays; the new text states exactly which edits drop trust, so an agent never claims an edited command entry is still trusted | closed |
| T-33-28 | Tampering | GSD config writes | high | mitigate | TestForeignKeys fails on any function of ai-kit's Python or the runner template that names a GSD config path and writes, unless it is the block removal or a scratch-repository fixture (C1-19, D-17), on any Python naming `cross_ai_retry`, and on the runner naming it outside the migrator; GSD keys go through `config-set`, which rejects unknown keys. Residual: the scan is static and sees only functions that name the path themselves; a write through a path passed in from elsewhere (as curated-config's verbatim backup restore receives it) is not seen; the record lists that restore | closed |
| T-33-29 | Information disclosure | docs/config/design.md | medium | mitigate | key names only; a test rejects key-shaped values and a value after a secrets key name | closed |
| T-33-30 | Repudiation | old roster names | low | mitigate | TestOldNameScan keeps the old name only on migration lines, so docs never send a user to a file the code no longer reads | closed |
| T-33-31 | Tampering | external lanes | high | mitigate | `--mode review` stops a lane on `tree=dirty`; outputs only under ignored `tmp/`; a verdict counts only with `tree=clean`; HEAD and tracked files checked unchanged at the checkpoint | closed |
| T-33-32 | Information disclosure | host configs and HOME | high | mitigate | AI_KIT_REFUSE_REAL_HOME=1 for every child; the drivers read `.planning/config.json` only for judge ids; `effort-env` prints set or unset, never values | closed |
| T-33-33 | Tampering | publish step | high | mitigate | byte-for-byte copy refusing different existing bytes; generated report; `check --require-current` before the commit; check-dogfood guards every later push | closed |
| T-33-34 | Repudiation | substitutes | medium | mitigate | every substitute is a referee-three lane ingested with `--replaces` and `--reason`; verdict_facts lists every probe and substitution; quota and auth stops are reported, never retried on another model | closed |
| T-33-35 | Tampering | judged set | medium | mitigate | `judged.py` stops on any changed skill outside the judged and fact-only sets, and never judges commit-fold or a project-rules skill | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

### Findings outside the plan register

| Ref | Severity | Finding | Status |
|-----|----------|---------|--------|
| CR-01 (code review) | critical | A symlinked project `.aikit/config.toml` let the roster migration write a cloned repo's command lane into the trust-free user layer | closed: fixed bf75b05 with tests |
| WR-01 (code review) | medium | A TOML date in a command entry crashed the trust digest with a traceback | closed: fixed 5200bcb |
| WR-03 (code review) | medium | `trust-local` recorded trust from a second read, not the content it showed | closed: fixed f7fbb2c |
| SEC-W1 (audit warning 1) | medium | The runner's retry migration could write into the user `config.toml` when the project `.aikit` directory itself links to the user config folder (only `[runner.retry]` values, each validated on read; no command lanes) | closed: fixed 6a70b69 (runner project migration refused when .aikit is a link or resolves to the user config folder; self-test retry-migrate-aikit-link); the read path through a linked .aikit stays read-only and each value is validated (T-33-04) |

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-33-01 | T-33-13, T-33-15 (D-25) | Migration concurrency without a lock: re-read before publish, idempotent merge, temp file plus rename; a residual race window remains. Owner-locked decision D-25 (33-CONTEXT.md) | owner (D-25, 2026-11-14) | 2026-11-15 |
| AR-33-02 | T-33-11 (C3-3) | A stop between retiring the old source and recording `migrated_from` leaves the record one step behind; the old file stays recoverable (renamed, never deleted). Accepted in the plan row per the locked D-14 order | owner (plan review C3-3) | 2026-11-15 |
| AR-33-03 | T-33-19 (D-11) | Trust hashes the command-bearing lane entries only; edits to `[lanes.policy]`, `strategy` or non-command rows keep trust and cannot change a command's argv. Owner-locked D-11 | owner (D-11, 2026-11-14) | 2026-11-15 |
| AR-33-04 | review IN-07 (D-11 consequence) | A project `[lanes]` with no command-bearing entry applies without trust, so a cloned repo can reorder, swap or (with `strategy = "local-only"`) empty the reviewer roster with runtime/model pairs only; it cannot run a command. Owner-locked D-11 | owner (D-11, 2026-11-14) | 2026-11-15 |
| AR-33-05 | T-33-28 | The static foreign-key scan cannot see a GSD config write through a path passed in at run time; listed in docs/config/design.md | plan 33-11 threat row | 2026-11-15 |
| AR-33-06 | T-33-SC (12 rows) | No package install in phase 33 (`git diff --stat ab06802 HEAD` over pyproject.toml, uv.lock and lock files is empty) | plan threat rows | 2026-11-15 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-11-15 | 50 | 50 | 0 | gsd-security-auditor (opus), close-out part 1 |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-11-15
