---
name: ai-kit-project-rules-agents
description: Use when an AGENTS.md or CLAUDE.md-style agent-instruction file needs checking against ai-kit's own 17-rule house ruleset, or when asked "is my AGENTS.md missing any workflow rules". Wraps `/agent-md-refactor` with a house-rule check it has no awareness of on its own.
---

# ai-kit-project-rules-agents

## Scope

This skill checks a target repo's AGENTS.md/CLAUDE.md-style instruction file against ai-kit's own 17-rule house ruleset (`rules.py`). The 17 rules are ai-kit's own accumulated convention, applied here to whichever repo is being checked — they are NOT a general-purpose rules engine offered to other projects.

## Resolve the entrypoint

Resolve once per invocation, in one Bash call, and record the printed path as a literal absolute path:

```bash
for d in "${CLAUDE_PLUGIN_ROOT:+$CLAUDE_PLUGIN_ROOT/skills/ai-kit-project-rules-agents}" \
         "$HOME/.claude/skills/ai-kit-project-rules-agents" \
         "${XDG_CONFIG_HOME:-$HOME/.config}/opencode/skills/ai-kit-project-rules-agents" \
         "$HOME/.agents/skills/ai-kit-project-rules-agents" \
         "$(dirname "<absolute path to THIS SKILL.md>")"; do
  [ -f "$d/ai-kit-project-rules-agents.py" ] && { printf '%s\n' "$d/ai-kit-project-rules-agents.py"; break; }
done
```

If no candidate exists, stop and report that the skill is not installed. The fifth candidate covers a from-checkout invocation — substitute the directory actually containing this `SKILL.md`.

Only the `$HOME/.claude/skills/...` symlink install (`tools/setup.py`) and a direct git checkout can actually import this skill: those layouts keep `skills/_shared/` beside the skill package. The other three candidates (`$CLAUDE_PLUGIN_ROOT`, opencode's skills dir, `~/.agents/skills`) raise `ImportError` at import time by design — they are copy-installs that do not carry `skills/_shared/`. A successful path lookup is not proof the import will succeed; prefer the symlink or a checkout.

## Run the check

```bash
python3 "$ENTRYPOINT" check <repo_root>
python3 "$ENTRYPOINT" remediate <repo_root>
```

`check` returns `{"workflow": [...], "links": [...]}`. `links` lists broken relative links from the root instruction file (image links included, `#anchor`/`?query` stripped, anchor-only links skipped); fix a broken link by correcting or removing it, since `remediate` does not touch links. `remediate` runs `check` internally and returns the ordered hand-off payload this skill wraps around: `{"remediate": [...ordered...], "blocked": [...]}` — the shared builder always returns both keys, but this skill has no research-dispatch domain, so `blocked` is always empty here. Trimmed example:

```json
{
  "remediate": [
    {"kind": "workflow", "id": "R01", "status": "missing", "criticality": 1,
     "summary": "...", "matched_signals": [], "auto_apply": true},
    {"kind": "workflow", "id": "R05", "status": "near_miss", "criticality": 2,
     "summary": "...", "matched_signals": ["..."], "auto_apply": false}
  ],
  "blocked": []
}
```

## Wrap mechanism (what makes this different from plain `/agent-md-refactor`)

Invoking plain `/agent-md-refactor` only runs its own five-phase structural refactor (Find Contradictions -> Identify the Essentials -> Group the Rest -> Create the File Structure -> Flag for Deletion) and has no house-rule awareness at all. Invoking THIS skill always runs `check`/`remediate` FIRST, and only when `remediate`'s payload is non-empty does it proceed toward `/agent-md-refactor`. `/agent-md-refactor` has no CLI, no importable/callable interface, and no per-rule insertion mode — it is a single Markdown-only, whole-file refactor pass with its own user-confirmation gate on internal contradictions. Because of that real shape, this skill invokes it EXACTLY ONCE per wrapping run, never once per rule: the confirmed remediation list is handed off as additional input into that skill's own Phase 2/Phase 3, never as N separate full-refactor passes that would risk each pass pruning the previous insert.

The hand-off is Steps A/B/C.

**Step A (confirm near-misses first, owned by THIS skill).** For every `remediate` entry with `auto_apply: false` (a near-miss), STOP and ask the user to confirm or decline individually — name the rule id, its current near-miss evidence (the entry's own `matched_signals` list: the literal phrases this checker already found in the target file, never an unsupported "trust me" claim), and what would be inserted if confirmed. This confirmation happens BEFORE `/agent-md-refactor` is invoked at all, and is owned entirely by this wrapping skill — it is deliberately NOT routed through `/agent-md-refactor`'s own Phase 1 ("Find Contradictions"), because that phase exists for a different concern (conflicting instructions already in the file), not for confirming whether to insert a missing house rule.

**Step B (assemble one ordered list).** Build the final ordered list = every `auto_apply: true` entry, plus every user-confirmed near-miss entry, in the same most-critical-first order `remediate` already returned. Declined near-miss entries are dropped and reported inline as skipped (D-05).

**Step C (one invocation, named injection point).** Invoke `/agent-md-refactor` against the target file EXACTLY ONCE. Treat the Step B list's `summary` strings — paraphrased, never the todo/rule text pasted verbatim — as additional "essential content" candidates for that skill's OWN Phase 2 ("Identify the Essentials") and Phase 3 ("Group the Rest"), preserving the list's most-critical-first order as the priority when Phase 2 has to choose what earns root-file placement. This is what makes the hand-off concrete: a named injection point and an exact ordering, not a vague "then run agent-md-refactor" instruction.

Invoke `/agent-md-refactor` via WHICHEVER skill-invocation mechanism the current host provides for an already-installed skill it knows about: a slash command, a named subagent/Task dispatch (Claude Code's `Agent` tool with `subagent_type: general-purpose` is named here as one worked example, never a requirement), or loading that skill's own `SKILL.md` instructions directly into context. Resolve `agent-md-refactor/SKILL.md`'s own location with the SAME host-neutral candidate-list pattern used above for this skill's own entrypoint — never a hardcoded `~/.claude/...` path. **Portable fallback:** on a host with no subagent-dispatch mechanism available at all, read `agent-md-refactor/SKILL.md`'s instructions directly into context and follow them manually for this one invocation. There is no Python import or subprocess call into `agent-md-refactor` anywhere — it has no such interface; the hand-off is always a documented instruction sequence for whichever agent is executing this skill, never code.

## Anti-patterns (NEVER)

- **NEVER treat a paraphrase as sufficient.** `rule_checker.py` classifies by
  literal lowercase substring matching against each rule's `signals` tuple —
  it does **not** do semantic matching. Writing AGENTS.md content that is
  semantically equivalent to a rule but uses different wording will still
  report `missing`/`near_miss`. When inserting a rule's content, the exact
  signal phrase (or enough of its synonyms to clear the ≥50%-of-signals
  threshold) must appear verbatim, lowercased, somewhere in the prose —
  phrase it naturally, but never assume "captures the meaning" is enough.
  (Discovered by diagnosing 9 false-"missing" findings after a refactor pass
  that deliberately avoided verbatim phrasing.)
- **NEVER route near-miss confirmation through `/agent-md-refactor`'s own
  Phase 1** ("Find Contradictions") — that phase is for conflicts already in
  the file, not for confirming whether to insert a missing house rule. Step
  A of this skill owns that confirmation itself.
- **NEVER invoke `/agent-md-refactor` more than once per wrapping run.** It
  is a whole-file refactor pass with no per-rule insertion mode; a second
  pass risks pruning the first pass's insert.
- **NEVER hardcode a `~/.claude/...` path** when resolving this skill's own
  entrypoint or `agent-md-refactor`'s — always walk the host-neutral
  candidate list (Claude Code plugin root, `$HOME/.claude`, opencode XDG
  path, `~/.agents`, from-checkout sibling).
- **NEVER assume `rules.py`'s `category` field drives what gets checked
  here.** `check_workflow_rules` filters by non-empty `signals`, not by
  `category`. R02 carries a non-workflow `category` label, yet its
  AGENTS.md-prose clause is still checked here because its `signals` are
  non-empty. R02's structural half is another skill's concern and is not
  read by this skill at all. Don't "fix" a rule's category thinking it
  changes routing; it doesn't.

## Reporting rule (D-05)

Findings and remediation results are reported INLINE in the conversation only. This skill never writes a persisted report file into the target repo — git is already the history of AGENTS.md edits, and a separate "why this file was edited" report is exactly the kind of file the user does not want.

## Ruleset reference

`rules.py` is the source of truth for the 17 house rules (id/category/criticality/condition/signals/summary). This document points at it rather than restating the rule text.
