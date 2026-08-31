"""GSD-specific instantiation of the shared dispatch-reinforcement pattern (ai_kit_spec.
dispatch_guidance) -- Task 7 smoke-test finding: GSD's own cross_ai_delegation step pipes the
task prompt to an external CLI and expects its raw stdout to already BE a valid SUMMARY.md
(gsd-core/workflows/execute-phase.md's own "has at least a heading and description" check), but
never itself tells the external CLI what that shape actually is -- confirmed live: a naive prompt
produced plain, unstructured prose GSD would reject; the SAME task with this format block appended
produced byte-correct SUMMARY.md-shaped output. This module holds that confirmed-real knowledge
(GSD_SUMMARY_FORMAT_BLOCK) so only GSD's own adapter carries it -- ai_kit_spec.dispatch_guidance
itself stays framework-agnostic."""
from ai_kit_spec.dispatch_guidance import build_dispatch_reinforcement_guidance

GSD_SUMMARY_FORMAT_BLOCK = """---
phase: <this phase's own id, e.g. 99-smoke-test>
plan: <this plan's own number, e.g. 01>
subsystem: <primary category: auth, payments, ui, api, database, infra, testing, etc.>
tags: [<searchable tech keywords>]
requirements-completed: []
duration: <your real elapsed time estimate, e.g. 1min>
completed: <today's date, YYYY-MM-DD>
---

# Phase <id>: <name> Summary

**<one-line substantive outcome -- NOT "phase complete" or "implementation finished">**

## Accomplishments

- <bullet list of what you actually did>

## Files Created/Modified

- <path> -- <one line on what changed>

Do not add any other top-level heading, and do not print any explanatory prose before the
frontmatter or after the Files Created/Modified section."""


def build_gsd_cross_ai_guidance(resolved_label: str) -> str:
    """The only entry point this module exposes -- composes the shared, framework-agnostic
    reinforcement guidance with GSD's own confirmed-real SUMMARY.md format block. Used ONLY for
    cross_ai_hook dispatch (Task 5's SKILL.md Step 3) -- native (in-framework) dispatch already
    knows GSD's own conventions and needs no reinforcement."""
    return build_dispatch_reinforcement_guidance(resolved_label, GSD_SUMMARY_FORMAT_BLOCK)
