---
name: ai-kit-agents-md-rules-checker
description: Use when an AGENTS.md or CLAUDE.md-style agent-instruction file needs checking against ai-kit's own 17-rule house ruleset, when a repo's Makefile/`.pre-commit-config.yaml` target shape (setup-env, per-hook targets, validate chaining, test pyramid) needs auditing for gaps, or when asked "is my AGENTS.md missing any workflow rules" / "does my Makefile have the right targets". Wraps `/agent-md-refactor` with a house-rule check it has no awareness of on its own.
---

# ai-kit-agents-md-rules-checker

## Scope

This skill checks a target repo's AGENTS.md/CLAUDE.md-style instruction file and its Makefile/`.pre-commit-config.yaml` against ai-kit's own 17-rule house ruleset (`rules.py`: workflow conventions plus Makefile target shape). The 17 rules are ai-kit's own accumulated convention, applied here to whichever repo is being checked — they are NOT a general-purpose rules engine offered to other projects.

## Resolve the entrypoint

Resolve once per invocation, in one Bash call, and record the printed path as a literal absolute path:

```bash
for d in "${CLAUDE_PLUGIN_ROOT:+$CLAUDE_PLUGIN_ROOT/skills/ai-kit-agents-md-rules-checker}" \
         "$HOME/.claude/skills/ai-kit-agents-md-rules-checker" \
         "${XDG_CONFIG_HOME:-$HOME/.config}/opencode/skills/ai-kit-agents-md-rules-checker" \
         "$HOME/.agents/skills/ai-kit-agents-md-rules-checker" \
         "$(dirname "<absolute path to THIS SKILL.md>")"; do
  [ -f "$d/ai-kit-agents-md-rules-checker.py" ] && { printf '%s\n' "$d/ai-kit-agents-md-rules-checker.py"; break; }
done
```

If no candidate exists, stop and report that the skill is not installed. The fifth candidate covers a from-checkout invocation — substitute the directory actually containing this `SKILL.md`.

Only the `$HOME/.claude/skills/...` symlink install (`tools/setup.py`) and a direct git checkout can actually import this skill: those layouts keep `skills/_shared/` beside the skill package. The other three candidates (`$CLAUDE_PLUGIN_ROOT`, opencode's skills dir, `~/.agents/skills`) raise `ImportError` at import time by design — they are copy-installs that do not carry `skills/_shared/`. A successful path lookup is not proof the import will succeed; prefer the symlink or a checkout.

## Run the check

```bash
python3 "$ENTRYPOINT" check <repo_root>
python3 "$ENTRYPOINT" remediate <repo_root>
```

`check` returns `{"makefile": [...], "workflow": [...]}`. `remediate` runs `check` internally and returns the ordered hand-off payload this skill wraps around: `{"remediate": [...ordered...], "blocked": [...]}`. Trimmed example:

```json
{
  "remediate": [
    {"kind": "workflow", "id": "R01", "status": "missing", "criticality": 1,
     "summary": "...", "matched_signals": [], "auto_apply": true},
    {"kind": "makefile", "id": "test-unit-alias", "criticality": 1,
     "summary": "...", "auto_apply": true}
  ],
  "blocked": [
    {"kind": "makefile", "id": "setup-env", "criticality": 1,
     "summary": "...", "stacks": ["python"]}
  ]
}
```

## Wrap mechanism (what makes this different from plain `/agent-md-refactor`)

Invoking plain `/agent-md-refactor` only runs its own five-phase structural refactor (Find Contradictions -> Identify the Essentials -> Group the Rest -> Create the File Structure -> Flag for Deletion) and has no house-rule awareness at all. Invoking THIS skill always runs `check`/`remediate` FIRST, and only when `remediate`'s payload is non-empty does it proceed toward `/agent-md-refactor`. `/agent-md-refactor` has no CLI, no importable/callable interface, and no per-rule insertion mode — it is a single Markdown-only, whole-file refactor pass with its own user-confirmation gate on internal contradictions. Because of that real shape, this skill invokes it EXACTLY ONCE per wrapping run, never once per rule: the confirmed remediation list is handed off as additional input into that skill's own Phase 2/Phase 3, never as N separate full-refactor passes that would risk each pass pruning the previous insert.

The hand-off is Steps A/B/C, plus an optional Step D for research-blocked Makefile/tooling gaps.

**Step A (confirm near-misses first, owned by THIS skill).** For every `remediate` entry with `auto_apply: false` (a near-miss), STOP and ask the user to confirm or decline individually — name the rule id, its current near-miss evidence (the entry's own `matched_signals` list: the literal phrases this checker already found in the target file, never an unsupported "trust me" claim), and what would be inserted if confirmed. This confirmation happens BEFORE `/agent-md-refactor` is invoked at all, and is owned entirely by this wrapping skill — it is deliberately NOT routed through `/agent-md-refactor`'s own Phase 1 ("Find Contradictions"), because that phase exists for a different concern (conflicting instructions already in the file), not for confirming whether to insert a missing house rule.

**Step B (assemble one ordered list).** Build the final ordered list = every `auto_apply: true` entry, plus every user-confirmed near-miss entry, in the same most-critical-first order `remediate` already returned. Declined near-miss entries are dropped and reported inline as skipped (D-05).

**Step C (one invocation, named injection point).** Invoke `/agent-md-refactor` against the target file EXACTLY ONCE. Treat the Step B list's `summary` strings — paraphrased, never the todo/rule text pasted verbatim — as additional "essential content" candidates for that skill's OWN Phase 2 ("Identify the Essentials") and Phase 3 ("Group the Rest"), preserving the list's most-critical-first order as the priority when Phase 2 has to choose what earns root-file placement. This is what makes the hand-off concrete: a named injection point and an exact ordering, not a vague "then run agent-md-refactor" instruction.

Invoke `/agent-md-refactor` via WHICHEVER skill-invocation mechanism the current host provides for an already-installed skill it knows about: a slash command, a named subagent/Task dispatch (Claude Code's `Agent` tool with `subagent_type: general-purpose` is named here as one worked example, never a requirement), or loading that skill's own `SKILL.md` instructions directly into context. Resolve `agent-md-refactor/SKILL.md`'s own location with the SAME host-neutral candidate-list pattern used above for this skill's own entrypoint — never a hardcoded `~/.claude/...` path. **Portable fallback:** on a host with no subagent-dispatch mechanism available at all, read `agent-md-refactor/SKILL.md`'s instructions directly into context and follow them manually for this one invocation. There is no Python import or subprocess call into `agent-md-refactor` anywhere — it has no such interface; the hand-off is always a documented instruction sequence for whichever agent is executing this skill, never code.

**Step D (research-dispatch for `blocked` entries — optional, timing-constrained).** A `blocked` entry (a Makefile/tooling-category gap with `needs_research: true`) has no concrete content yet, so it is NEVER fed into the Step C `/agent-md-refactor` call in the run that discovered it. What varies is WHEN Step D runs relative to Steps A-C — and this is the one explicit rule: if Step D runs at all, it runs BEFORE Step A of this invocation, never after Step C, never interleaved with an already-started Steps A-C pass. Choose one option BEFORE Step A begins:

1. Run Step D first — dispatch one independent research sub-task per distinct stack named in the `blocked` entries' `"stacks"` lists, call `cache-update` for each, then re-run `remediate` ONE time — and treat that refreshed payload's `remediate` list (now folding in any newly-unblocked entries alongside the originally-non-blocked ones) as the ONE list Steps A, B, and C run against, for the ONE Step C invocation this run performs.
2. Skip Step D entirely this invocation, run Steps A-C once against the ORIGINAL `remediate` list (the `blocked` entries stay blocked and unfed), and defer Step D to the NEXT invocation of this skill against the same repo, where the same research-then-refresh-then-Steps-A-C sequence applies from a clean start.

Both options invoke `/agent-md-refactor` EXACTLY ONCE: Step D, when chosen, always completes and refreshes the list BEFORE Steps A-C start, so there is never a second pass through Steps A-C — and therefore never a second Step C invocation — within one skill invocation. The one invariant that never changes: a `blocked` entry is fed into `/agent-md-refactor` only after `cache-update` has made it un-blocked and a FRESH `remediate` call confirms it, and that confirmation always happens before, never after, this invocation's single Step C.

On a host that provides a subagent/Task-dispatch primitive, use it for each research sub-task (Claude Code's `Agent` tool, `subagent_type: general-purpose`, is named as an example, never a requirement); on a host with no such primitive, perform the research directly in the current conversation instead of assuming one exists.

Each research sub-task is asked, for its one stack, for CURRENT (not training-data-stale) recommendations covering ONLY the categories that actually map onto an `ALL_TOOLING_KEYS` entry — never "cheapest/fail-fastest check ordering" or "the pre-commit-vs-pre-push split": Plan 01's `check_validate_order`/`check_precommit_prepush_split` already answer both structurally, directly from the target repo's own Makefile/`.pre-commit-config.yaml`, with no cache key reserved for either. The full combined key list (`ALL_TOOLING_KEYS` = `REQUIRED_STATIC_TARGETS` union `RESEARCH_CATEGORIES`) the sub-task must key its findings by — shown here so it cannot guess wrong:

- `REQUIRED_STATIC_TARGETS`: `setup-env`, `validate`, `test`, `test-unit`, `test-integration`, `e2e-test`, `arch-test`
- `RESEARCH_CATEGORIES`: `formatter`, `security-scanner`, `code-smell-detector`, `duplicate-code-detector`, `dead-code-detector`

Every value must be formatted `"<tool + invocation> (source: <url or concrete rationale the research sub-task actually consulted>)"` — a bare tool-name guess with no stated evidence is not an acceptable value, and `cache-update` rejects it. Example findings object:

```json
{"setup-env": "uv venv && uv sync (source: https://docs.astral.sh/uv/)",
 "formatter": "ruff format (source: https://docs.astral.sh/ruff/formatter/)"}
```

Write the findings to a scratch JSON file under `./tmp/` (this repo's own rule 10 convention, applied to whichever repo is running the check), then call:

```bash
python3 "$ENTRYPOINT" cache-update <stack> <path-to-that-file>
```

`cache-update` validates the JSON against `ALL_TOOLING_KEYS` membership, non-empty-string-ness, and the `(source: ...)` provenance requirement before writing — rejecting anything else with a one-line error and writing nothing. It also accepts a `--cache-root <path>` flag, but that flag is TEST-ONLY (documented in `cli.py`'s own docstring) and is never used by this skill's research-dispatch step.

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
- **NEVER accept a bare tool-name guess with no `(source: ...)`** in a Step D
  research finding — `cache-update` rejects it, and an unsourced
  recommendation is exactly the kind of claim Required Start #3 forbids.
- **NEVER assume `rules.py`'s `category` field drives what gets checked
  here.** `check_workflow_rules` filters by non-empty `signals`, not by
  `category == "workflow"`. R02 is labeled `category: "makefile"` but its
  AGENTS.md-prose clause is still checked by this skill because its signals
  are non-empty — only R02's Makefile-*shape* half lives in
  `makefile_checker.py`, read structurally from the real Makefile, never
  from AGENTS.md prose. Don't "fix" a rule's category thinking it changes
  routing; it doesn't.

## Deciding Step D's option 1 vs 2

Step D names two options but doesn't tell you which to pick — that choice
depends on context, not on a fixed rule:

- **Pick option 1 (research now)** when the `blocked` list names few distinct
  stacks (1-2) and the user is already mid-flow on this repo — the research
  cost is small and deferring it just means paying it next invocation anyway.
- **Pick option 2 (defer)** when `blocked` spans many stacks, the user
  explicitly wants a fast pass focused on what's already resolvable, or this
  invocation is itself time-boxed (e.g. part of a larger orchestrated run that
  budgets one skill call per target).
- When genuinely unsure, ask the user which they'd prefer rather than
  guessing — the cost of researching the wrong priority first is a wasted
  sub-task dispatch.

## Reporting rule (D-05)

Findings and remediation results are reported INLINE in the conversation only. This skill never writes a persisted report file into the target repo — git is already the history of AGENTS.md edits, and a separate "why this file was edited" report is exactly the kind of file the user does not want.

## Ruleset reference

`rules.py` is the source of truth for the 17 house rules (id/category/criticality/condition/signals/summary). This document points at it rather than restating the rule text.
