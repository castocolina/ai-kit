---
name: ai-kit-spec-execute
description: Routes execution of an already-generated plan/phase to the framework-specific ai-kit-spec-execute adapter (GSD or superpowers), based on which framework produced the plan. Use when the user asks to execute/run/implement a plan or phase and the generating framework isn't already known.
---

# ai-kit-spec-execute

1. Run `detect_framework(cwd)` from `detect_framework.py`.
2. `"gsd"` → delegate to `ai-kit-spec-execute-gsd`.
3. `"superpowers"` → delegate to `ai-kit-spec-execute-superpowers` (see that skill's own SKILL.md).
4. `"unknown"` → ask the user which framework generated this plan; do not guess.
