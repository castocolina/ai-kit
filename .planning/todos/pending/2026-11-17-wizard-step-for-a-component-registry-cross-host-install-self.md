---
created: 2026-11-17T14:25:52.876Z
title: Wizard step for a component registry, cross-host install, self-update and scheduled updates
area: tooling
severity: minor
files:
  - tools/setup.py
  - tools/wizard_app.py
  - tools/install.sh
---

## Problem

The setup wizard has no step for third-party skill packs, plugins or extensions, and no way to keep
them (or ai-kit itself) up to date. The owner installs the same pack on several hosts by hand, with
`npx skills`, with each host's marketplace, or both, and has seen a component show up twice when a
marketplace install and `npx skills` overlap. Written as an owner wish list, to be split into phases
when it is planned.

## Solution

TBD. Seven features, in the owner's words (translated):

1. **Registry step in the wizard, before the status-line step.**
   - A registry file (JSON, YAML or TOML; format to decide) lists packs, plugins and extensions:
     superpowers, ponytail, mattpockock, Google Chrome modern-web-guidance, impeccable and others.
   - Each entry shows as an accordion: opening one closes the others, so the owner picks what they
     want without long scrolling.
   - A pack can hold hooks, agents, commands, skills, extensions and MCP servers.
   - Study, for skills and commands, whether the target runtime's marketplace or symlinks (as
     `npx skills` does) is the better install route. Record the finding with its evidence.

2. **Per-component host choice.** For own and third-party skills, agents, hooks, commands and
   plugins, the owner decides: Claude only, or also opencode, pi, cursor, copilot and codex. The hosts
   do not discover components the same way (skills, agents, hooks, commands, plugins, extensions,
   MCP servers), so each host needs its own mapping.

3. **Duplicate detection.** Detect whether a component is already installed on the system or as a
   plugin. A marketplace install followed by enabling a skill can show it twice next to an
   `npx skills` install.

4. **Self-updating `ai-kit` executable.**
   - After the `curl ... | bash` download, install an `ai-kit` executable that checks for an update
     and downloads it only when there is one, before it starts the wizard.
   - A scheduled script runs at a time the owner picks in the wizard: a final toggle asks for
     auto-update and for the frequency and times.
   - A second toggle detects changes in the skills and updates them.
   - The scheduler works on Bazzite (systemd user timer) and macOS (launchd) first.

5. **Headless update of third-party packs.** Using feature 1, check whether the packs changed and
   update them without the wizard. A toggle in the same wizard view asks whether third-party packs
   are updated too, and if yes the schedule runs that action. Goal: no visiting each host to run
   `npx skills` or to switch on a marketplace auto-update flag.

6. **`ai-kit load` subcommand.** Show which components in the global user config add to the context
   of a session, and let the owner turn some off for one repository. For skills the agent can see
   only the name, the name and description, or the full load as usual.

7. **Repository-local install.** Standing in a repository, the owner can install skills for that
   repository only (for example open-gsd or impeccable). A `--local` flag makes local the default for
   that run, and a toggle switches between global (default) and local (active with the flag).

Constraints that apply when this is planned:
- Runtime code stays stdlib-only; the wizard parts reach Textual only through the existing guard
  (AGENTS.md).
- Config writes are atomic and keep every unrelated byte.
- Whatever is inferred about a host's discovery paths is flagged as inferred, not shown as documented.
- Overlaps Phase 36 (spec-config in the wizard) and the visible-hooks todo; decide the order then.
