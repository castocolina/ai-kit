---
created: 2026-11-19T10:00:00.000Z
title: Scan git projects and auto-update their project-local open-GSD install on a schedule
area: tooling
severity: minor
files:
  - tools/setup.py
  - tools/install.sh
---

## Problem

open-GSD is installed per project (`<project>/.claude/gsd-core`, with that project's own agents,
skills and commands), never at user level. So every project that uses it drifts from the latest
release on its own, and the owner has to visit each one to update it. Owner request (translated):
scan the projects under `~/git/` (HOME-agnostic) that have an open-GSD install and update or upgrade
them automatically every so often.

## Solution

TBD. Idea to refine when planned:

- **Scan.** Walk the projects under the owner's git folder (default `~/git/`, resolved from `$HOME`,
  never a hardcoded path; configurable). A project counts when it has a project-local gsd-core
  (`.claude/gsd-core/bin/gsd-tools.cjs`, or the Codex layout `.codex/gsd-core`), proven with the
  tool's own `runtime-identity` check rather than by file name alone.
- **Update.** For each match, run the project-local installer (`npx -y @opengsd/gsd-core@latest
  --<runtime> --local`) inside that project. Never a user-level install and never `gsd update`:
  a user-level GSD install is the thing the owner removes (see the global CLAUDE.md rule).
- **Schedule.** A timer on Bazzite (systemd user timer) and macOS (launchd), chosen in the wizard
  like the self-update schedule of the registry todo, with frequency and time.
- **Safety, to decide with evidence.** Skip a project with a dirty working tree or one mid-run;
  record each project's before and after version and a failure per project, never stop the whole
  sweep on one failure; leave the update uncommitted (or on a branch) so the owner reviews it; add
  a dry-run listing mode that only reports what would change.
- **Related.** Shares the scheduler and the wizard toggle with
  `2026-11-17-wizard-step-for-a-component-registry-cross-host-install-self.md`; plan them together.
