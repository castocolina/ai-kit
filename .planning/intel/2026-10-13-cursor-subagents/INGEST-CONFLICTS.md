## Conflict Detection Report

### BLOCKERS (0)

(none)

### WARNINGS (4)

[WARNING] Phase 21 scope does not cover shipping agents
  Found: .planning/todos/pending/2026-10-13-add-cursor-subagents-pinned-to-non-fast-composer-2-5-and-grok.md describes creating and shipping Cursor agent files plus a tools/setup.py link step; the user chose to fold this into Phase 21.
  Impact: .planning/ROADMAP.md Phase 21 "Cursor Live Validation" lists only EVAL-07 and SPEC-06 and three success criteria (smoke run, label removal, wrapped cursor-agent detection). No requirement in .planning/REQUIREMENTS.md covers ship-and-link of agents, so the work has no requirement ID and no success criterion.
  → Add new requirement(s) and success criteria to Phase 21 (for example: pinned agent files shipped, setup.py links them, live check shows non-fast model), or place the work in its own phase.

[WARNING] PROJECT.md defers cursor beyond v1.3, ROADMAP.md schedules it in v1.3
  Found: .planning/PROJECT.md says "Live validation on codex and opencode (cursor and pi deferred beyond v1.3)"; .planning/ROADMAP.md lists Phase 21 (Cursor Live Validation) and Phase 22 (Pi) inside v1.3 phases 16-22; the requested fold target is Phase 21.
  Impact: The fold target sits in a phase PROJECT.md describes as deferred, so it is unclear whether this work ships in v1.3. This inconsistency existed before this doc; it is not introduced by the doc.
  → Confirm Phase 21 is in v1.3 scope and align PROJECT.md, or move the agent work to a phase that is unambiguously in scope.

[WARNING] Pinned grok id depends on user-local cli-config, non-fast billing unconfirmed
  Found: Session decision pins `grok-4.7`. Doc "Verified" section says `grok-4.7` resolved to `grok-4.7-high` with no `-fast` only because the user's ~/.cursor/cli-config.json `modelParameters` stores `grok-4.7: reasoning_effort=high, fast=false`; the doc also states non-fast billing is unconfirmed (stream shows no fast flag). The doc's own hint 2 used the explicit `grok-4.7-medium`, and the doc lists explicit non-fast ids (`grok-4.7-low/-medium/-high/-xhigh`).
  Impact: On a machine without those modelParameters, the bare `grok-4.7` pin may resolve to a fast variant, defeating the purpose. `composer-2.5` has the same dependency (`composer-2.5: fast=false`).
  → Decide between the bare alias (relies on cli-config) and an explicit effort-suffixed id, and check one run in the Cursor usage dashboard before claiming "non-fast".

[WARNING] Agent name resolution across ~/.cursor/agents, .cursor/agents and ~/.claude/agents is unverified
  Found: The doc's step 1 asks how Cursor resolves the same name across the three directories; the Verified section does not answer it. Cursor also reads ~/.claude/agents (35 GSD agents).
  Impact: A shipped agent name could collide with or be shadowed by a GSD agent, so the pin might not apply.
  → Pick names that do not collide with the 35 GSD agents and test delegation live (Phase 21 live run) before relying on them.

### INFO (4)

[INFO] No classified UNKNOWN docs, no cycles, no locked-vs-locked conflict
  Note: One classification consumed (DOC, high confidence, locked false, precedence null). cross_refs are file paths with no inter-doc edges, so no cycle exists. No ADR in the ingest set, so no locked decision to contradict; existing locked decisions in .planning/ (Phase 18 D-01..D-08) were checked and none contradict the doc.

[INFO] Auto-resolved: user session decision over DOC approach hints
  Note: The DOC (lowest precedence) leaves ownership open in step 3 and offers a single unpinned generic agent taking `model` per call (verified to work). The user decided: ai-kit owns the agents, ships them with setup.py linking into ~/.cursor/agents, pins the model in each file, and ships no unpinned generic agent. The user decision wins; the generic-agent option is not carried forward. Sources: orchestrator prompt; DOC "Verified" and "Solution" sections.

[INFO] Doc step 1 (confirm schema) largely answered by the Verified section
  Note: The Verified section lists the parsed frontmatter (name, description, model, force-default-model, readonly, background, tools) and shows `model: composer-2.5` pinning works live. Only cross-directory name resolution remains open (see WARNING above). The optional read-only `composer-explorer` and the step 5 built-in explore override (`cli-config.json` subagentModels.explore / exploreSubagentModel) are not decided by the user; left as open options.

[INFO] Phase 18 coordination is non-blocking
  Note: Doc step 4 says the curated cross-ai.mjs cursor block already pins `--model` and that in-session subagents are a separate surface. Phase 18 is not executed yet (ROADMAP.md); no requirement (XAI-02) is changed by this work, and Phase 21 depends on Phase 19, not on this item.
