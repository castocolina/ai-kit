---
created: 2026-10-18T17:21:10.347Z
title: PreCompact hook pre-summarizes transcript chunks via the decision system
area: tooling
severity: major
files:
  - tools/hooks/
  - .planning/todos/pending/2026-10-18-atomic-reusable-decision-system-skills.md
---

## Problem

Compaction re-reads the whole active history, which is slow and expensive. Each session has a
transcript file whose active part can be split into chunks.

## Solution

- A PreCompact hook takes each chunk of the active history, sends it to the decision system to
  catalog, classify, keep or discard part or all of it, and writes a pre-summary that the
  compaction then uses, so compaction is faster, simpler and cheaper.
- Delivery: hook output or a Markdown file the compaction reads, the same way `/compact <prompt>`
  takes instructions from the command line. If it is a file, name it like
  `{session-id}-{name}-compact.md` in an ephemeral/temporary path.
- Depends on the decision-system skills. Jev classifies; the summary text itself must come from
  a model or from the compaction, so the split of work needs a spike: what PreCompact can return
  and how the transcript format marks chunks and compact boundaries (verify against current
  Claude Code docs; theory -> hypothesis -> spike before planning).
- Installable and removable as its own setup knob.

## Research notes (2026-10-18, fast pass; docs read via a summarizing fetch, confirm wording)

- PreCompact receives `trigger` (manual/auto), `custom_instructions` (manual only) and
  `transcript_path`, but its only output is blocking (exit 2 or `decision: block`); it cannot add
  or replace compaction instructions or supply a summary (not documented).
- PostCompact exists and receives `compact_summary`; no decision control.
- Documented route for a pre-made summary: a `SessionStart` hook with matcher `compact` that
  injects a file as `additionalContext` after compaction (post-compaction injection, not a summary
  replacement). Manual route: `/compact <instructions>` pointing at the prepared file.
- Candidate design for the spike: PreCompact (or a slash command) prepares
  `{session-id}-{name}-compact.md` in a temp dir from Jev-classified chunks; the compact-matcher
  SessionStart hook injects it; a manual `/compact` variant passes it as instructions.
- The transcript JSONL is internal and changes between versions (compact boundaries undocumented),
  so chunking must be defensive and version-tolerant; the file may lag the in-memory conversation.
- `additionalContext`/`systemMessage` are capped at 10,000 characters each (larger output goes to a
  file with a 2,000-character preview), so the injected summary must fit that budget.

## Promoted

Promoted to Phase 21.2 on 2026-10-18 (ROADMAP and REQUIREMENTS updated). Owner-approved order: 21.1 -> 21.2 -> 21.3, all before Phases 22 and 23.
