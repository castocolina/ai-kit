# Routing table — who rewrites what (convenience snapshot)

Routing is data-driven from each profile's `revise_protocol.routes`. This table is a **convenience
snapshot** of the seed profiles (FR-1.5) — it is not authoritative and may lag. **The authoritative
routing is each framework profile's `revise_protocol.routes` — when in doubt, read the profile, not
this table.** Adding a framework or changing a route means editing its profile; this snapshot may
then be stale until someone updates it too.

| Framework (detected) | Archetype | Rewrite handled by | Mechanism |
|---|---|---|---|
| superpowers | design | `brainstorming` skill | hybrid subagent → surface if it stalls (Step 3b-skill) |
| superpowers | plan | `writing-plans` skill | hybrid subagent → surface if it stalls (Step 3b-skill) |
| GSD | plan | `/gsd-plan-phase {phase_id} --reviews`, then `gsd-plan-checker` | slash-command or surface (3b-cmd) + validate (3c) |
| GSD | intent / requirements / design | `ai-kit-spec-review-fixer` | direct edit (3a) |
| any other framework, generic, or `none` | all | `ai-kit-spec-review-fixer` | direct edit (3a) |
| ambiguous / low-confidence detection | all | `ai-kit-spec-review-fixer` | direct edit (3a) — Surface notes the ambiguity |

The reviewer (`ai-kit-spec-review-checklist`) is identical for every framework; only the
**rewrite** stage is routed. To change routing, edit the framework profile's
`revise_protocol.routes` — never hard-code tools here.
