---
created: 2026-11-23T00:00:00.000Z
title: Review notes left open by phase 39
area: tooling
severity: minor
files:
  - .planning/phases/39-lane-capability-blocks-and-lens-skills/39-REVIEW.md
  - skills/ai-kit-spec-review/ai_kit_spec/capability_block.py
  - skills/ai-kit-spec-review/ai_kit_spec/edit_pass.py
  - skills/ai-kit-spec-review/ai_kit_spec/skill_table.py
  - skills/ai-kit-spec-review/ai_kit_spec/config_io.py
  - skills/ai-kit-spec-review/references/cross-ai.mjs
  - skills/ai-kit-spec-review-checklist/SKILL.md
---

## Problem

The phase 39 code review left these items open. None loses data, prints a secret or leaves a process running; each
is a narrow window, a preview that says less than the dispatch, a runner edge no formula reaches, or a decision for
the owner.

## Goal

Close each item below when the named module is next changed, with a test for each behaviour change, and record the
owner's answer for the decision items before any code changes.

## Notes

- Decision (owner): a project's `.aikit/config.toml` can set `[skills.roles]` without the trust step, like `[models]`,
  `[runner]` and `[review]`; only command-bearing lanes need `trust-local`. A role picks which installed skill bodies
  are inlined into a lane's prompt (`lens_set`). Decide whether project-layer roles, and `[review] edit_lens_pass`,
  should need the trust step before they choose prompt content.
- Decision (owner): the code review counted each skill directory the scan finds as a skill root (a skill directory
  linked into a host root, the installer's shape, now passes the embedded-value check; 39-SPEC R8's dated note). A
  SKILL.md linked out of a real in-root directory and a link inside the repository are still outside. Confirm this
  reading, or name a narrower one (for example: only directories ai-kit's own installer linked).
- Decided by the orchestrator (2026-11-23), no longer open: the profile cache (`~/.claude/cache/framework-profiles`,
  the review skill's `CACHE_DIR`) is an allowed root for `--files` and guidance paths, so a cross-AI review that embeds
  a learned framework profile runs again. Reason: before phase 39 such a review ran, and AGENTS.md says never remove an
  existing feature. A sibling folder and a link out of the cache are still refused (`capability_block.profile_cache_root`,
  tests in `test_compose_for_lane` and `test_capability_block`).
- `capability-block` takes only the runtime, model and role (SPEC R4), so a configured lane with a non-default effort,
  cursor mode or codex sandbox prints a block whose SETTINGS (and for codex, ACCESS) differ from what its dispatch
  prepends; the parity test uses defaults only. Consider `--key <lane>` (read the lane from `[lanes]`) or the same
  setting flags as the dispatch, with a parity test on a non-default lane.
- `check-reviewer` and `config-status` summaries preview the bare lane argv, before lens and MCP planning, so a lane that
  gets the run-scoped MCP file at dispatch shows `mcp=unknown` in the summary and `call_file` in the block. Label the
  summary as the base-argv view, or run the same delivery planning (it writes a temporary MCP file).
- `capability-block` writes the run-scoped MCP file to a temporary folder for its preview (removed in `finally`), so the
  block reads "passed to your host for this call"; a GSD hook that prepends that block does not pass the file to its own
  runner call (Phase 44 wires hooks). Phase 44 should either pass the file or have the command print the block without
  that route.
- A SIGTERM to the Python dispatcher skips the `finally` that removes the run-scoped MCP folder (`aikit-mcp-*` in the
  temporary directory, one small file). Wrap the dispatch in the existing `_sigterm_unwinds` pattern (`detection.py`).
- The edit pass snapshots the approved files before the runner takes its execute lock; an execute run that edits one of
  those files in between would have its edit undone by `--reject`. Take the snapshot after the lock, or refuse the pass
  while an execute run holds the checkout.
- The edit pass compares dirty file names before and after, so an unapproved file that was already dirty and that the
  lane changed again is not named (the SKILL text says to check `git status` before accepting). Compare content hashes of
  the dirty paths.
- The runner's `toolListCaps` reads pi `--exclude-tools` entries as literal names; a pattern entry (only reachable through
  `CONFIG.extraArgs`, no formula emits one) that removes `bash` leaves `shell=yes`. Treat a deny pattern as `unknown`,
  with a self-test case, at the next template change.
- `_git_value` and `gsd_tools.project_root` decode git's path output as strict UTF-8; a checkout or worktree whose path
  is not UTF-8 raises `UnicodeDecodeError` out of the composer. Decode with the filesystem encoding and refuse a path
  the prompt cannot carry.
- `edit_pass.record_path` falls back to `HOME`; with no `HOME` and no `XDG_STATE_HOME` the record path is relative to the
  current directory. Refuse an unusable state home like `skill_table.host_root` does.
- `ai-kit-spec-review-checklist/SKILL.md` (Tool preference section) calls `TOOL_AVAILABILITY` the tools "installed on
  this machine"; the block now lists only the tools found on the lane's own PATH, and only when the lane may have a
  shell. Reword when that skill is next judged (a judged skill outside phase 39's diff).
- The runner's `laneCapabilities` gives every unknown field the one frozen `CAP_UNKNOWN` object; nothing mutates it
  today. Return a fresh object at the next template change if a caller ever edits the result.
