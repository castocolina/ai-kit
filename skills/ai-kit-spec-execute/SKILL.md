---
name: ai-kit-spec-execute
description: Routes execution of an already-generated plan/phase to the framework-specific ai-kit-spec-execute adapter (GSD or superpowers), based on which framework produced the plan. Use when the user asks to execute/run/implement a plan or phase and the generating framework isn't already known.
---

# ai-kit-spec-execute

## Dependencies

This skill requires `detect_framework.py`, located in the skill's own directory (`skills/ai-kit-spec-execute/detect_framework.py`). Import as:
```python
from skills.ai-kit-spec_execute.detect_framework import detect_framework
```
The function has already been added to sys.path by the skill bootstrap block (Task 1). No additional setup required.

## Routing Procedure

1. If the user just invoked a framework's own planning skill in this conversation (superpowers
   `writing-plans`/`brainstorming`, or a GSD planning skill), note it as `CONVERSATION_SIGNAL`
   (`"superpowers"`/`"gsd"`) — otherwise `CONVERSATION_SIGNAL` is unset.
2. Extract the plan/phase path from the user's request if explicitly provided (e.g., "execute `/path/to/plan.md`" or referencing a file path in the conversation). If no explicit path, document_path is None.
3. Run `detect_framework(cwd, document_path=document_path, conversation_signal=CONVERSATION_SIGNAL)` from `detect_framework.py`.
4. Based on result:
   - `"gsd"` → delegate to `ai-kit-spec-execute-gsd`.
   - `"superpowers"` → delegate to `ai-kit-spec-execute-superpowers` (see that skill's own SKILL.md).
   - `"unknown"` → proceed to "Error Scenarios" below.

## Error Scenarios

**If detect_framework() raises an exception or returns unexpected value:**
- Log the error (include cwd, document_path, CONVERSATION_SIGNAL)
- Ask user: "I couldn't determine whether this plan is a GSD phase or a superpowers plan. Did you generate it with GSD's planning skills or superpowers' writing-plans?"
- Once clarified, route to the appropriate adapter

**If result is "unknown" (no framework markers detected):**
- ASK (do not guess): "Which framework generated this plan — GSD or superpowers?"
- Accept user clarification and route accordingly

**If CONVERSATION_SIGNAL conflicts with document_path signals:**
- CONVERSATION_SIGNAL takes precedence (user just invoked that framework's skill in this conversation; this is the strongest signal)
- Log the conflict if helpful for debugging, but do NOT ask user to confirm

## Anti-Patterns (NEVER Do)

- **NEVER hardcode or guess the framework** based on file naming, location, or your own assumptions about what's "probably GSD" — use detect_framework() every time
- **NEVER skip the CONVERSATION_SIGNAL check** even if routing "seems obvious"; both frameworks can be active in the same session
- **NEVER route to the wrong adapter** — silent routing to the wrong framework breaks the user's workflow and intent
- **NEVER assume document_path is always explicit** — extract it carefully from the user's request or fall back to None
- **NEVER ignore the result "unknown"** — ask user for clarification rather than defaulting to either framework
