# Phase 38 spike record (D-23)

start-time: proc ok median_us=5; ps ok median_ms=1 resolution=seconds; paren-name ok
setsid: setsid from util-linux 2.42.4 leader-caller forks=yes own-group=yes; non-leader-caller forks=no own-group=yes
real-home probes: not run (no ledger consent line)

The two lines above come from scratch-only checks (no host CLI, no real-HOME read) on Linux, probe 2026-11-21.
The `/proc/<pid>/stat` start-time field (index 19 after the last `)`) read the same digits twice for a process
named `sp (x) y`; `ps -o lstart=` (LC_ALL=C) gives whole seconds only. A `setsid` called from a process that
leads its own group forks (the launcher's pid file must be written by the re-executed shell, not taken from the
caller); called from a non-leader it runs in the same pid; both end in a new session and group.

## Host output timing

- claude -> not probed (no ledger consent line), unverified
- opencode -> not probed (no ledger consent line), unverified
- pi-text -> not probed (no ledger consent line), unverified
- pi-json -> not probed (no ledger consent line), unverified

## Not probed by design

- hosted timing per host -> not probed (no herdr in 38-01), unverified
- macOS start-time read -> not probed (no macOS host), unverified

The SIGKILL plus --sweep run against a real herdr is plan 38-26's live check.

## Real config audit

no host call, no audit needed

## Cleanup

- leftovers: none among recorded groups (a detached or relocated descendant is not covered by this check)
- removed: tmp/run-2026-11-19/p38-spike/out, tmp/run-2026-11-19/p38-spike/bin (home, prompts and r-* were never created)
- no raw host output was written
