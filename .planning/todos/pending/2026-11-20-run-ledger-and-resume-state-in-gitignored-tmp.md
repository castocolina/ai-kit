---
created: 2026-11-20T04:55:00.000Z
title: Keep every run ledger and resume state in a gitignored tmp folder inside the project
area: tooling
severity: minor
files:
  - skills/ai-kit-gsd-spec-discuss/SKILL.md
  - skills/ai-kit-spec-goal-prompt/scripts/gp_sections.py
---

## Problem

Owner request during the 2026-11-19 autonomous run (translated): for the ai-kit spec-discuss skill and for the goal
prompt, state that the run ledger must live in a gitignored `./tmp/` inside the same project, so it is not lost
across restarts.

- `ai-kit-gsd-spec-discuss` SKILL.md section 4 says the ledger is "a run file under the system temp dir
  (`tempfile.gettempdir()`)". A reboot, a `/tmp` cleanup or a session wake can lose it, and it contradicts the
  project rule that scratch lives under `./tmp/`. The committed DISCUSSION-LOG keeps only "own reasoning ... ledger"
  marks, so after a restart the decisions are unrecoverable.
- `ai-kit-spec-goal-prompt` already says "run ledger under tmp/" in its CLEANUP rail, but the rails do not say that
  every ledger, rails file and resume state the run writes lives there.

## Solution

TBD. Natural home: Phase 47.2 (goal prompt learns rails from sessions) for the goal-prompt rail, plus a small
spec-discuss skill text change that needs the skill-judge loop (JDG-04).

- spec-discuss: the ledger is `tmp/<run-name>/ledger.md` in the project (the folder is gitignored, created when
  missing); the skill checks `git check-ignore -q tmp/` first and refuses to write elsewhere.
- goal-prompt: one rail line says the run ledger, the rails file and the resume state are files under the project's
  gitignored `tmp/`, never the system temp dir, so a restart or a session wake finds them; the session-wake `--ref`
  points at them.
- Evidence that the rule works: the 2026-11-19 run kept `tmp/run-2026-11-19/{ledger,state,rails}.md` and survived two
  context resets.

Severity is the orchestrator's suggestion from an unattended run; confirm it at triage.
