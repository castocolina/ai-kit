# Agent-skills diagnostics

Read only when §0 step 8 finds an agent that is not clean. Report each case with its cause and
continue the run; the fix for a path or wiring cause is re-running `ai-kit-gsd-curated-config`,
which wires only references gsd-core resolves.

## Reasons (`reason` in the `--json` output)

- `not_configured`: the agent has no `agent_skills` entry. gsd-core prints and warns nothing.
  Report it as **not configured**; it is not a failure.
- `configured_empty`: configured with no skill paths. Its warning goes straight to stderr
  (the agent's `.err` file), not into the JSON `warnings`.
- `configured_unresolved`: every configured entry was skipped; the warnings name each skip.
- On non-claude runtimes gsd-core may replace an empty skills block with the agent's persona
  file, so an agent whose entries were all skipped can read `resolved` with warnings. The
  warnings decide, not the reason.

## Warning causes (`[agent-skills] WARNING ...`)

A `[agent-skills] NOTE: Global skill "..." accepted via trusted_global_roots` line is an
acceptance trace, not a warning: that entry resolved (the trusted ai-kit install case).

- "failed path check (symlink escape?)": the skill's real path is outside the host's global
  skills dir and no `agent_skills_security.trusted_global_roots` entry covers it.
- "not found": nothing is at that path.
- "Skipping unsafe path ...: not confined to the project directory": a project path
  (`skills/<name>`) resolves outside the project.
- Any other warning: report it verbatim. Re-running curated-config fixes only path and wiring
  causes; a runtime-caused warning (a namespaced skill on a non-claude runtime, a runtime
  without a skills dir) is not one of them.
