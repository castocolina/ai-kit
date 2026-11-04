---
status: complete
phase: 28-fast-environment-proof-gates
source: [28-VERIFICATION.md]
started: 2026-11-04T11:15:00-03:00
updated: 2026-11-04T11:40:00-03:00
---

## Current Test

[testing complete]

## Tests

### 1. Make a real commit touching one module, then a real `git push` to a remote, on the owner's machine
expected: Commit runs only covering modules and is refused on a failure; push finishes the two test hooks in about 60 s or less; a deferred e2e notice appears only for over-budget modules
result: pass — run by the agent on the owner's delegation (2026-11-04). Real commits: the 14 compacted phase commits each ran the staged-tests hook (covering modules only; logs tmp/compact-28/logs/), and a failing staged test was refused at commit in 28-06. Real push: `git push -u origin gsd/phase-28-fast-environment-proof-gates` to GitHub ran every pre-push hook (ruff, pylint, pyright, vulture, py-compile, unittest core, unittest wizard, check-dogfood, deferred-e2e) and exited 0 in 77 s; deferred-e2e found no over-budget module; the two test hooks measured 55.6 s in time_prepush.py.

### 2. Run `make test` once from inside a real opencode or pi session with the real host CLIs on PATH
expected: Same pass/skip result as a plain terminal; no real host binary invoked
result: pass — `make test` ran inside a real pi session (herdr pane, worktree at the phase tree 268e0ad) with AI_KIT_REFUSE_REAL_HOME=1: EXIT=0 in 2 min 0 s, unit 80/80, unit-uv 1/1, integration 4/4, e2e 23/23, install 45 passed 0 failed, arch 1/1 — the same result as a plain terminal; the host-CLI tripwire recorded no real host binary call.

## Summary

total: 2
passed: 2
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps
