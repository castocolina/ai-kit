---
schema_version: 1
open_count: 1
waived_count: 0
fixed_count: 0
total_count: 1
last_updated: 2026-10-31T13:34:32.748Z
---

# Broken Windows Ledger

> Cross-phase defect register. With `workflow.windows_enforce` enabled, `/gsd-ship` blocks while `open_count > 0`.
> Waive with `gsd-tools windows waive <id> "<reason>"` (reason required).
> Mark fixed with `gsd-tools windows fixed <id>`.

| id | phase | kind | file | line | description | status | reason | recorded_at | resolved_at |
|----|-------|------|------|------|-------------|--------|--------|-------------|-------------|
| 1 | 27 | stub | skills/ai-kit-spec-goal-prompt/SKILL.md |  | Intentional stub SKILL.md; plan 27-10 writes the real skill | open |  | 2026-10-31T13:34:32.748Z |  |

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
  }
]
````
