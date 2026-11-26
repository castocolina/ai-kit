# Sorting unknown skills (spec-config Step 1.6)

Read this only after Step 1.6's `classify-skills --cwd <project root>` listing printed at least one
`unsorted` line and the owner agreed to sort. `$TOOLS_PY` and `<project root>` are the literal values
SKILL.md Step 0 resolved.

## Read the listing

It prints one `unsorted <name> hosts=<hosts>` line per addressable unsorted skill of the shared role
table (a skill whose name the runner cannot address gets a
`not offered <name> hosts=<hosts> reason=<reason>` line instead and no proposal) and, when jev is
present, at most one `proposal <name> role=<role> confidence=<c> advisory` line per skill (jev sees
only the skill's name and the first 300 characters of its description). With jev absent it prints
`jev absent: nothing proposed`; after a low or missing answer the skill has no proposal. Say so and
offer the closed roles yourself. MCP servers are never sent to jev.

## Ask, then write after Step 2.1

A proposal is advice: ask the owner about each skill and note each role the owner confirms. Write
nothing yet: once Step 2.1 has resolved and announced the write target, run for each confirmed role

```bash
python3 "$TOOLS_PY" confirm-skill-role --name <skill> --role <role> --cwd <project root>
```

with `--global` in place of `--cwd <project root>` when the target is the user file. Each call
writes one `[skills.roles]` entry, labeled `user-stated`, which beats the seed row; a name the
command refuses stays unsorted. These writes come before the roster write and stand on their own:
a later roster failure does not undo them, so say so before the first call. Step 4 reports each
role written, each failed confirm and each skill left unsorted.
