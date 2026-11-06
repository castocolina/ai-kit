---
name: lens-brief
description: Load right after a lens skill (impeccable, ponytail:ponytail, ponytail:ponytail-review) in ai-kit's GSD agents, and in gsd-phase-researcher, gsd-planner and gsd-executor for the unit-brief check. Use when a GSD agent's agent_skills block lists .planning/lens-brief. It names each agent's expected lens, says how to report a lens that did not load (lens not loaded), applies ai-kit's design rule over ponytail's smallest-change wording, and says what to report when no unit brief (.aikit/brief) was loaded. Not a standalone skill (GSD includes it by path), and not for choosing or wiring lenses (gsd-tools config-set, make check-dogfood).
---

# ai-kit lens brief

GSD includes this file by path in each agent's `agent_skills` block. Lens agents read it
right after their lens. Read the sections your agent needs: lens agents read Expected lenses,
If a lens did not load and Design rule; gsd-planner also reads Unit brief.
gsd-phase-researcher and gsd-executor have no lens: they read Design rule and Unit brief.
Every agent reads Gotchas.

## Expected lenses

- gsd-ui-researcher: global:impeccable
- gsd-ui-checker: global:impeccable
- gsd-ui-auditor: global:impeccable
- gsd-planner: global:ponytail:ponytail
- gsd-plan-checker: global:ponytail:ponytail
- gsd-code-reviewer: global:ponytail:ponytail-review

## If a lens did not load

1. Find your agent name under Expected lenses.
2. Look for that entry in your agent_skills block: an `@` line for `global:impeccable`, a
   Skill-tool line for `global:ponytail:*`.
3. A missing line or a failed Skill call means the lens did not load. A Skill-tool line on a
   non-Claude host also counts as not loaded; an `@` line loads on any host.

Continue without the lens. In your return, name each lens that did not load as
`lens not loaded: <entry>`, with the entry exactly as listed under Expected lenses (for
example `lens not loaded: global:ponytail:ponytail`).

## Design rule

Apply AGENTS.md's Design rule (Non-Negotiable Rules). For a lens: ponytail decides how the
code is built (reuse existing components and helpers, no speculative abstraction), not how
much of the feature ships. Where ponytail's smallest-change wording meets the Design rule,
ponytail yields. With jev loaded, classify the options against the rule through it; without
jev, decide by your own reasoning.

As a checker or reviewer (gsd-plan-checker, gsd-code-reviewer, gsd-ui-checker,
gsd-ui-auditor): a plan or diff that ships less user value, or a half-done feature, to skip
steps that are not hard is a blocker. Speculative abstraction, or new code where an existing
helper fits, is a warning. Cite AGENTS.md's Design rule in the finding.

## Unit brief

For gsd-phase-researcher, gsd-planner and gsd-executor only: the unit brief is the
`@.aikit/brief/SKILL.md` entry listed after this file in your skill list; read it next.
Report no unit brief (say `no unit brief found`, or the unit it names) only when that entry
is absent, the file says "no brief", or it names a different unit than yours (in GSD your
unit is the phase you work on; a `unit: next` brief is the planner's own); then continue.
Other agents ignore this section.

## Gotchas

- A `Load the <x> skill via the Skill tool` line is not a loaded lens. The lens loaded only if
  the Skill call returned its text. GSD prints that line whenever the config's `runtime` is
  `claude` (ai-kit sets it), even on opencode or pi, so on another host report it as not loaded.
- For an `@` lens (`global:impeccable`), GSD drops the line when the file is missing and warns
  only on stderr, so a missing lens is an absent line: compare your block against your line
  under Expected lenses. GSD prints a Skill-tool line even when the plugin is missing.
- GSD loads this file by path, not by trigger matching, so `evals/` has no trigger queries;
  its eval cases check what an agent does with this text.
