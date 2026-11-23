# 38-01 Summary: live spike (D-23)

Status: complete. Commit 12d35d4 (`docs(38-01): live spike record for host output timing and start-time reads`) names only `38-SPIKE.md`. Run by the chunk agent itself (orchestrator-type plan, cross_ai false), no lane.

## What ran

- Task 1 (scratch only, no host CLI, no real-HOME read): marker, `setup.py` (`out/` mode 700), `starttime.py` (1000 `/proc/<pid>/stat` reads, 20 `ps -o lstart=` reads under LC_ALL=C, a `/bin/sleep` symlink named `sp (x) y` in its own recorded group, killed in a `finally`), `setsid_check.py` with `setsid-child.sh` (leader and non-leader callers, the `exec /usr/bin/setsid /bin/sh` shape of `buildLauncher` at cross-ai.mjs:4808), `doc_check.py`.
- Task 2: the anchored consent regex matched 0 lines of `tmp/run-2026-11-19/ledger.md` (the owner has not written `p38-spike real-home: allowed`). Every host line is `not probed (no ledger consent line), unverified`.
- Task 3: `leftovers.py` twice (`leftovers: none` both times), scratch `out/` and `bin/` removed, record completed, `doc_check.py --final` prints `spike doc: ok`, commit.

## Evidence

- `start-time: proc ok median_us=5; ps ok median_ms=1 resolution=seconds; paren-name ok`: the runner's after-last-`)` parse holds for a name with spaces and parentheses; the `ps` fallback has whole-second resolution only.
- `setsid: setsid from util-linux 2.42.4 leader-caller forks=yes own-group=yes; non-leader-caller forks=no own-group=yes`: from a group leader (a pane job) `setsid` forks, so the launcher's pid must come from the re-executed shell's own `pid` file (as `buildLauncher` does), never from the caller's pid.

## Skipped for lack of the consent line (owner items)

- The real-HOME host timing calls: claude (`-p --output-format json`), opencode (`run --format json`), pi text mode and `pi -p --mode json`, each in a scratch repository. Not run; `capture.py`, `timing.py` and `audit.py` were not copied because no host call ran. 38-23's limit text must call each host's output timing unverified.
- Hosted timing per host (no herdr in this plan; 38-26's live check) and the macOS start-time read: not probed by design.

What the spike's decisions rest on instead: the scratch-only start-time and setsid observations above, and the runner's existing code; the silent-host limit for review lanes stays a documented, unverified limit.

## Deviations

- `setsid_check.py` records only the leader caller's pgid in `pgids.txt` (the non-leader case shares the script's own group, which must not be signalled); the forked setsid child exits right after writing its file, so nothing else is signalled.
- Real config audit: `no host call, no audit needed`.
