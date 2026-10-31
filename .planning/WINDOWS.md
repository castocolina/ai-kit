---
schema_version: 1
open_count: 3
waived_count: 0
fixed_count: 0
total_count: 3
last_updated: 2026-10-31T14:20:32.696Z
---

# Broken Windows Ledger

> Cross-phase defect register. With `workflow.windows_enforce` enabled, `/gsd-ship` blocks while `open_count > 0`.
> Waive with `gsd-tools windows waive <id> "<reason>"` (reason required).
> Mark fixed with `gsd-tools windows fixed <id>`.

| id | phase | kind | file | line | description | status | reason | recorded_at | resolved_at |
|----|-------|------|------|------|-------------|--------|--------|-------------|-------------|
| 1 | 27 | stub | skills/ai-kit-spec-goal-prompt/SKILL.md |  | Intentional stub SKILL.md; plan 27-10 writes the real skill | open |  | 2026-10-31T13:34:32.748Z |  |
| 2 | 27 | deviation | skills/ai-kit-spec-goal-prompt/scripts/gp_scope.py |  | detect_scope does not restrict plan files to a requested plans work set (ScopeInputs has no file list); the caller restricts until the CLI plan wires the answers | open |  | 2026-10-31T13:43:40.051Z |  |
| 3 | 27 | deviation | skills/ai-kit-spec-goal-prompt/scripts/gp_matrix.py |  | A user request for autonomous on a superpowers or none scope has no matrix row (M08 covers gsd-unproven only); the request is ignored, not listed in dropped. Decide: strategy or dropped request | open |  | 2026-10-31T14:20:32.696Z |  |

````json
[
  {
    "id": 1,
    "kind": "stub",
    "phase": "27",
    "file": "skills/ai-kit-spec-goal-prompt/SKILL.md",
    "line": null,
    "description": "Intentional stub SKILL.md; plan 27-10 writes the real skill",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-10-31T13:34:32.748Z",
    "resolved_at": null,
    "milestone": "v1.3"
  },
  {
    "id": 2,
    "kind": "deviation",
    "phase": "27",
    "file": "skills/ai-kit-spec-goal-prompt/scripts/gp_scope.py",
    "line": null,
    "description": "detect_scope does not restrict plan files to a requested plans work set (ScopeInputs has no file list); the caller restricts until the CLI plan wires the answers",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-10-31T13:43:40.051Z",
    "resolved_at": null,
    "milestone": "v1.3"
  },
  {
    "id": 3,
    "kind": "deviation",
    "phase": "27",
    "file": "skills/ai-kit-spec-goal-prompt/scripts/gp_matrix.py",
    "line": null,
    "description": "A user request for autonomous on a superpowers or none scope has no matrix row (M08 covers gsd-unproven only); the request is ignored, not listed in dropped. Decide: strategy or dropped request",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-10-31T14:20:32.696Z",
    "resolved_at": null,
    "milestone": "v1.3"
  }
]
````
