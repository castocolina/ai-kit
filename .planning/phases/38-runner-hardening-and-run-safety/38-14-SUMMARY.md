# 38-14 Summary: run lock stale and edge rules (part 2)

Status: complete. Two commits through two cross-AI lanes (pi router-env/my-coding), both status=ok on their first run:
e30afff (`feat(38-14): Tracer: the lock verdict and the stale clear of a dead runner's record`, Task 1, 255 s) and 967043e
(`feat(38-14): lock refusals that keep the file, narrowed review note, ps fallback and the clear race`, Tasks 2 and 3, 409 s).

## What changed

- skills/ai-kit-spec-review/references/cross-ai.mjs (lock block): `LOCK_REREAD_MS` (2000), `LOCK_MAX_BYTES` (65536), `LOCK_CLEAR_STALE_MS`
  (10000); `procReadable`, `lockStartTime` (`/proc` start ticks where `/proc` reads, else `ps -o lstart=` with `LC_ALL=C`, else `-`),
  `lockPidAlive` (EPERM counts as alive), `lockRecordValid` (a record missing or mistyping an identity field is unreadable), `lockGroupAlive`
  (`groupMembers` with the leader's start time; off Linux `process.kill(-pgid, 0)`), the pure `lockVerdict` (`own`, `foreign`, `held`,
  `orphan`, `stale`), `lockProbe`, `lockSince`, `lockForeignLine`, `readLockOnce` / `readLockRecord` (re-read every 100 ms for 2 s from the
  reader's own start; non-regular, oversized or future-mtime files count as unreadable), `createLockFile` (the 38-13 create code, moved),
  `clearStaleLock` (the `<lock>.clearing` mkdir mutex, abandoned after 10 s; dev/ino and bytes re-checked before the rename to a unique
  `.stale-` name). `acquireLock` runs at most 3 rounds of create, read, verdict and clear; `lockSeen` notes only `held`, `orphan` or
  `foreign`. Export list gains `clearStaleLock`, `lockGroupAlive`, `lockRecordValid`, `lockStartTime`, `lockVerdict`, `readLockOnce`.
- skills/ai-kit-spec-review/references/cross-ai-selftest.mjs: helper `deadPid()` (`plantLock(c, overrides)` came with 38-13); eleven cases:
  `lock-unreadable-refuses`, `lock-invalid-refuses`, `lock-unreadable-reread`, `lock-stale-race` (runtime) and `pure-lock-verdict`,
  `lock-stale-cleared`, `lock-orphan-refuses`, `lock-foreign-refuses`, `lock-review-no-note-stale`, `pure-lock-start-ps` (fake `ps`, never the
  real one), `pure-lock-clear-race` (logic).

## Verification (run by the chunk agent)

- Acceptance greps: every named function and constant once, `spawnSync('ps'` once, the narrowed `lockSeen` return once, the eleven case names
  once; `node --check` on both files.
- Eighteen cases (the eleven new ones plus `lock-two-at-once`, `lock-held-refuses`, `lock-not-taken`, `lock-gone-after-signal`,
  `lock-review-note`, `host-overlap`, `session-chosen-pi`) print `self-test ok`; `--self-test-list` 668 lines, 23 `lock-`/`pure-lock-` lines at
  the planned kinds.
- `--print-argv` of six calls byte-equal to the 38-13 tip; detection.py and the model-literal baseline unchanged; runner and sibling diffs
  reviewed against the plan. Shards and wave gates: see the ledger (c38-4, waves 8-9).

## Deviations

- The guard grep `rg -c "linkSync|shortcut: we renamed"` prints 1, not 0: it matches the pre-existing `fs.unlinkSync(tmp)` (a temp-file
  cleanup outside the lock block, present before this plan). No `fs.linkSync` exists; the guard's intent (no rename/link-back design) holds.
- The plan's `selftest.sh` (bare `node` under a scratch HOME, the Volta-shim fork hazard) was replaced by `tmp/run-2026-11-19/p38-14/selftest.py`.
- One commit for Tasks 2 and 3 (the chunk's lane prompt) instead of one per task; `deadPid()` was defined in Task 1's commit (used there first).
- `lock-stale-race` reports `pi lockhold calls <n>` (the plan's `pi slowok` reason named the wrong fake mode).
