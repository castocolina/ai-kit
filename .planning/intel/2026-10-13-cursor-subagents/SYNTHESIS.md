# Synthesis: Cursor subagents pinned to non-fast models

Mode: merge. Target: ROADMAP.md Phase 21 "Cursor Live Validation" (user's choice).

## Doc counts
- Total: 1 (DOC 1, ADR 0, SPEC 0, PRD 0, UNKNOWN 0)
- Source: /var/home/bazzite/git/personal/ai-kit/.planning/todos/pending/2026-10-13-add-cursor-subagents-pinned-to-non-fast-composer-2-5-and-grok.md

## Per-type intel
- Decisions locked: 0 (no ADR). Session decisions are recorded in context.md under "Session decisions".
- Requirements: 0 extracted (a DOC yields context only). The work needs new requirement IDs; see the first WARNING.
- Constraints: 0
- Context topics: 6 (problem, environment facts, live-verified behavior, approach hints, file references, session decisions)

Files:
- /var/home/bazzite/git/personal/ai-kit/.claude/worktrees/v13-curated-config-v2/.planning/intel/2026-10-13-cursor-subagents/context.md
- decisions.md, requirements.md, constraints.md: not written (nothing to put in them)

## Key facts for the roadmapper
- Live-verified: a per-agent `model:` pin in `.cursor/agents/*.md` works (composer-2.5 confirmed); frontmatter keys parsed by cursor-agent include name, description, model, force-default-model, readonly, background, tools.
- User decisions: ai-kit owns and ships the agents; tools/setup.py links them into ~/.cursor/agents; model pinned in each file (composer-2.5, grok-4.7); no unpinned generic agent.
- Unconfirmed: non-fast billing (check Cursor usage dashboard); name resolution across ~/.cursor/agents, .cursor/agents, ~/.claude/agents.

## Conflicts
- 0 blockers, 4 warnings (competing-variants/needs-user-input class), 4 info (auto-resolved/notes)
- Detail: /var/home/bazzite/git/personal/ai-kit/.claude/worktrees/v13-curated-config-v2/.planning/intel/2026-10-13-cursor-subagents/INGEST-CONFLICTS.md
