---
name: ai-kit-lens-brief
description: Read right after a lens skill (impeccable, ponytail, ponytail-review) in ai-kit's GSD agents. Names each agent's expected lenses, says what to do when a lens did not load, and applies ai-kit's design rule over ponytail's smallest-change wording. The three unit-brief agents (gsd-phase-researcher, gsd-planner, gsd-executor) also read its Unit brief section.
---

# ai-kit lens brief

This file follows the lens skill that lists it in the same agent's skill list. Read it
after that lens, because the design rule below qualifies the lens.

## Expected lenses

- gsd-ui-researcher: global:impeccable
- gsd-ui-checker: global:impeccable
- gsd-ui-auditor: global:impeccable
- gsd-planner: global:ponytail:ponytail
- gsd-plan-checker: global:ponytail:ponytail
- gsd-code-reviewer: global:ponytail:ponytail-review

## If a lens did not load

Continue without the lens. In your return, name each lens that did not load as
`lens not loaded: <name>`. GSD skips a missing skill, and it emits the plugin lenses
(`global:ponytail:...`) only on Claude Code. On any other runtime, name them as not loaded.

## Design rule

Apply AGENTS.md's design rule (the **Design rule** bullet under Non-Negotiable Rules).
Short form: simple is not the same as easy. Never choose the easier option when it gives
the user less value only to skip a few steps that are not hard, and never ship a half-done
feature or less value to keep a change small. Ponytail decides how the code is built
(reuse existing components, helpers and well-known patterns before writing from scratch,
with no speculative abstraction), not how much of the feature ships. Where ponytail's
smallest-change wording meets this rule, ponytail yields. Without jev, apply the rule by
your own reasoning.

## Unit brief

For gsd-phase-researcher, gsd-planner and gsd-executor only: if .aikit/brief/SKILL.md was not loaded above, say that no unit brief was found and continue. Other agents ignore this section.
