# Phase 12: Architecture Rules Checker (ai-kit-project-rules-arch) - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-09-13
**Phase:** 12-Architecture Rules Checker (ai-kit-project-rules-arch)
**Areas discussed:** AST-only check scope (target-aware vs. file-level blanket)

---

## AST-only scope

| Option | Description | Selected |
|--------|-------------|----------|
| Target-aware | Only flag import/exec of the specific module being architecturally checked; ignore unrelated imports elsewhere in the same file. | ✓ |
| File-level blanket | Flag any import/exec call anywhere in the backing test file. | |

**User's choice:** Target-aware
**Notes:** Scouting found ai-kit's own `tests/test_arch.py` — the exact file Success Criterion 1 requires to pass with no finding — calls `importlib.util.exec_module` to load `tools/setup.py` for unrelated inventory-test helpers, while its real architecture checks parse `tools/status-line.py` via pure `ast.parse`. A blanket scan would misfire on this real, canonical file.

---

## Claude's Discretion

- Exact heuristic for locating the backing test file for an `arch-test` target in an arbitrary fixture repo.
- Exact correlation mechanism for identifying "the checked target" (D-02).

## Deferred Ideas

None. `cross_reference_todos` re-confirmed the same 3 historical todos (resolves_phase: 6/7/8) are not live candidates. The blocking-prerequisite note (Phases 9-11 must land first) was recorded in CONTEXT.md's `<domain>` section.
