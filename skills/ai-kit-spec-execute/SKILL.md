---
name: ai-kit-spec-execute
description: Routes execution of an already-generated plan/phase to the framework-specific ai-kit-spec-execute adapter (GSD or superpowers), based on which framework produced the plan. Use when the user asks to execute/run/implement a plan or phase and the generating framework isn't already known.
---

# ai-kit-spec-execute

1. If the user just invoked a framework's own planning skill in this conversation (superpowers
   `writing-plans`/`brainstorming`, or a GSD planning skill), note it as `CONVERSATION_SIGNAL`
   (`"superpowers"`/`"gsd"`) — otherwise `CONVERSATION_SIGNAL` is unset.
2. Run `detect_framework(cwd, document_path=<the plan/phase path the user asked to execute, if
   any>, conversation_signal=CONVERSATION_SIGNAL)` from `detect_framework.py`.
3. `"gsd"` → delegate to `ai-kit-spec-execute-gsd`.
4. `"superpowers"` → delegate to `ai-kit-spec-execute-superpowers` (see that skill's own SKILL.md).
5. `"unknown"` → ask the user which framework generated this plan; do not guess.
