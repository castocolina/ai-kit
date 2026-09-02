---
name: ai-kit-spec-execute
description: Routes execution of an already-generated plan/phase to the framework-specific adapter (ai-kit-spec-execute-gsd or ai-kit-spec-execute-superpowers) by detecting which framework generated it. Use when the user asks to execute/run/implement a plan or phase and the generating framework isn't already known.
---

# ai-kit-spec-execute

## Step 0: Resolve detect_framework.py's path

Same shim pattern as `ai-kit-spec-execute-superpowers/SKILL.md` (different target path, no shared
helper yet, so it stays inline). Tries each install shape in turn — plugin, user-global, git
checkout, bare cwd — first existing directory wins; hard-fails rather than guessing. Run the whole
block below in one `Bash` call; every branch is executable, not a placeholder to hand-substitute:

```bash
for d in "${CLAUDE_PLUGIN_ROOT:+$CLAUDE_PLUGIN_ROOT/skills/ai-kit-spec-execute}" \
         "$HOME/.claude/skills/ai-kit-spec-execute" \
         "$(git rev-parse --show-toplevel 2>/dev/null)/skills/ai-kit-spec-execute" \
         "$(pwd)/skills/ai-kit-spec-execute"; do
  [ -n "$d" ] && [ -d "$d" ] && { SKILL_DIR="$d"; break; }
done
if [ -z "$SKILL_DIR" ]; then
  printf 'ERROR: could not resolve skills/ai-kit-spec-execute under any known installation shape '
  printf '(CLAUDE_PLUGIN_ROOT, ~/.claude/skills, git toplevel, or cwd) -- STOP and tell the user '
  printf 'rather than guessing a path.\n'
  exit 1
fi
DETECT_FRAMEWORK_PY="$SKILL_DIR/detect_framework.py"
printf 'DETECT_FRAMEWORK_PY=%s\n' "$DETECT_FRAMEWORK_PY"
```

**Record the printed line as this wave's own literal value.** Every later invocation below uses
this resolved `$DETECT_FRAMEWORK_PY` path. Either invoke it as a subprocess (`python3
$DETECT_FRAMEWORK_PY <cwd> [document_path] [conversation_signal]`, which prints the result on
stdout) or, from Python already running with `$SKILL_DIR` on `sys.path`, `import
detect_framework` as a bare top-level module and call
`detect_framework.detect_framework(cwd, document_path=..., conversation_signal=...)` directly.

This step's failure means the *script* is missing; "Error Scenarios" below covers the script
running fine but *detection* being inconclusive — tell the two apart before troubleshooting.

Before routing, ask: has the user already told me which framework this is, more recently than
whatever the document itself suggests? A plan file's own content is a static, possibly-stale
signal — it reflects whichever framework wrote it, even if the user has since moved on (e.g. an
old GSD-generated file being reused as a template for superpowers work). What the user just did
*in this conversation* is live and current. Getting this backwards means silently routing to the
framework that generated the file's boilerplate instead of the one the user is actually asking to
run right now (see Anti-Patterns item 1 below).

## Routing Procedure

1. If the user just invoked a framework's own planning skill in this conversation (superpowers
   `writing-plans`/`brainstorming`, or GSD's `/gsd-plan-phase`), note it as `CONVERSATION_SIGNAL`
   (`"superpowers"`/`"gsd"`) — otherwise `CONVERSATION_SIGNAL` is unset.
2. Extract the plan/phase path from the user's request if explicitly provided (e.g., "execute `/path/to/plan.md`" or referencing a file path in the conversation). If no explicit path, document_path is None.
3. Run `detect_framework(cwd, document_path=document_path, conversation_signal=CONVERSATION_SIGNAL)` from `$DETECT_FRAMEWORK_PY` (Step 0), passing `CONVERSATION_SIGNAL` through — never omit it, it is the strongest signal (see Anti-Patterns).
4. Based on result:
   - `"gsd"` → delegate to `ai-kit-spec-execute-gsd`.
   - `"superpowers"` → delegate to `ai-kit-spec-execute-superpowers` (see that skill's own SKILL.md).
   - `"unknown"` → proceed to "Error Scenarios" below.

## Error Scenarios

**If detect_framework() raises an exception or returns unexpected value:**
- `detect_framework()` itself has no `raise` in its body — its only I/O is `isfile`/`isdir` on two fixed paths — so an exception here means something upstream broke (bad `cwd`, a permission error walking to `.planning/` or `docs/superpowers/plans/`, a malformed `CONVERSATION_SIGNAL` value from the caller), not an ordinary "framework unclear" case
- Log the error (include cwd, document_path, CONVERSATION_SIGNAL) and fix the underlying cause before retrying, rather than treating it as equivalent to "unknown"
- Ask user: "I couldn't determine whether this plan is a GSD phase or a superpowers plan. Did you generate it with GSD's planning skills or superpowers' writing-plans?"
- Once clarified, route to the appropriate adapter

**If result is "unknown" (no framework markers detected):**
- ASK (do not guess): "Which framework generated this plan — GSD or superpowers?"
- Accept user clarification and route accordingly

## Anti-Patterns (NEVER Do)

- **NEVER skip passing CONVERSATION_SIGNAL just because it's unset this turn** — it's the only signal that outranks *both* document_path and repo markers. Omit it and the old-GSD-repo-reused-for-superpowers case (Step 0 above) silently loses: `.planning/PROJECT.md` still exists on disk from prior GSD use, so the repo-marker fallback returns `"gsd"` even though the user just ran superpowers' `writing-plans` two messages ago.
- **NEVER treat a bare filename ("plan.md") as "no document_path was given."** `_framework_from_document_path` only matches full path substrings (`.planning/` or `docs/superpowers/plans/`); a correctly-extracted but unqualified filename produces the *same* `None` result as truly having no path, silently demoting a real signal to the repo-marker fallback instead of raising it as evidence.
- **NEVER trust repo markers in a mixed-framework repo without knowing their precedence.** If both `.planning/PROJECT.md` and `docs/superpowers/plans/` exist (e.g. a repo that migrated frameworks, or runs both), the GSD marker is checked first and wins — so a repo with leftover GSD scaffolding will route to GSD by default even for a superpowers-only session, unless CONVERSATION_SIGNAL or document_path override it first.
- **NEVER let "unknown" fall through to a default framework.** The GSD and superpowers adapters aren't interchangeable no-ops on a wrong guess — `ai-kit-spec-execute-gsd` writes phase-completion state back into `.planning/`, so running it against a document that isn't actually a GSD phase can leave bogus `.planning/` state behind, not just produce a confusing error.
