---
status: testing
phase: 28-fast-environment-proof-gates
source: [28-VERIFICATION.md]
started: 2026-11-04T11:15:00-03:00
updated: 2026-11-04T11:15:00-03:00
---

## Current Test

number: 1
name: Make a real commit touching one module, then a real `git push` to a remote, on the owner's machine
expected: |
  Commit runs only covering modules and is refused on a failure; push finishes the two test hooks
  in about 60 s or less; a deferred e2e notice appears only for over-budget modules
awaiting: user response

## Tests

### 1. Make a real commit touching one module, then a real `git push` to a remote, on the owner's machine
expected: Commit runs only covering modules and is refused on a failure; push finishes the two test hooks in about 60 s or less; a deferred e2e notice appears only for over-budget modules
result: [pending]

### 2. Run `make test` once from inside a real opencode or pi session with the real host CLIs on PATH
expected: Same pass/skip result as a plain terminal; no real host binary invoked
result: [pending]

## Summary

total: 2
passed: 0
issues: 0
pending: 2
skipped: 0
blocked: 0

## Gaps
