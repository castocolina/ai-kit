---
schema_version: 1
open_count: 2
waived_count: 0
fixed_count: 6
total_count: 8
last_updated: 2026-10-31T15:20:53.069Z
---

# Broken Windows Ledger

> Cross-phase defect register. With `workflow.windows_enforce` enabled, `/gsd-ship` blocks while `open_count > 0`.
> Waive with `gsd-tools windows waive <id> "<reason>"` (reason required).
> Mark fixed with `gsd-tools windows fixed <id>`.

| id | phase | kind | file | line | description | status | reason | recorded_at | resolved_at |
|----|-------|------|------|------|-------------|--------|--------|-------------|-------------|
| 1 | 27 | stub | skills/ai-kit-spec-goal-prompt/SKILL.md |  | Intentional stub SKILL.md; plan 27-10 writes the real skill | fixed |  | 2026-10-31T13:34:32.748Z | 2026-10-31T15:20:53.069Z |
| 2 | 27 | deviation | skills/ai-kit-spec-goal-prompt/scripts/gp_scope.py |  | detect_scope does not restrict plan files to a requested plans work set (ScopeInputs has no file list); the caller restricts until the CLI plan wires the answers | fixed |  | 2026-10-31T13:43:40.051Z | 2026-10-31T15:11:25.372Z |
| 3 | 27 | deviation | skills/ai-kit-spec-goal-prompt/scripts/gp_matrix.py |  | A user request for autonomous on a superpowers or none scope has no matrix row (M08 covers gsd-unproven only); the request is ignored, not listed in dropped. Decide: strategy or dropped request | fixed |  | 2026-10-31T14:20:32.696Z | 2026-10-31T15:11:25.447Z |
| 4 | 27 | stub | skills/ai-kit-spec-goal-prompt/scripts/gp_render.py |  | render raises NotImplementedError for non-OpenGSD scopes and plans work sets until plan 27-07 | fixed |  | 2026-10-31T14:33:12.924Z | 2026-10-31T14:44:15.030Z |
| 5 | 27 | stub | skills/ai-kit-spec-goal-prompt/scripts/gp_sections.py |  | done_lines raises NotImplementedError for an e2e none result and for mockups until plan 27-08 | fixed |  | 2026-10-31T14:33:13.001Z | 2026-10-31T14:53:15.996Z |
| 6 | 27 | todo | tests/test_ai_kit_spec_goal_prompt_render.py |  | R18/R19 parity through check_rules is not run in 27-06; owned by 27-09 Task 2 | fixed |  | 2026-10-31T14:33:13.067Z | 2026-10-31T15:11:25.511Z |
| 7 | 27 | deviation | skills/ai-kit-spec-goal-prompt/scripts/gp_render.py |  | Autonomous block names an unverified primitive in its heading only; its first line must stay flags-only (D-12), so the paste text does not say unverified | open |  | 2026-10-31T14:44:20.838Z |  |
| 8 | 27 | deviation | skills/ai-kit-spec-goal-prompt/scripts/gp_render.py |  | A rule line over 200 characters (a long plan title in OBJECTIVE or a long objective) refuses generation instead of wrapping; no wrapped-title test exists | open |  | 2026-10-31T14:44:20.909Z |  |

````json
[
  {
    "id": 1,
    "kind": "stub",
    "phase": "27",
    "file": "skills/ai-kit-spec-goal-prompt/SKILL.md",
    "line": null,
    "description": "Intentional stub SKILL.md; plan 27-10 writes the real skill",
    "status": "fixed",
    "reason": "",
    "recorded_at": "2026-10-31T13:34:32.748Z",
    "resolved_at": "2026-10-31T15:20:53.069Z",
    "milestone": "v1.3"
  },
  {
    "id": 2,
    "kind": "deviation",
    "phase": "27",
    "file": "skills/ai-kit-spec-goal-prompt/scripts/gp_scope.py",
    "line": null,
    "description": "detect_scope does not restrict plan files to a requested plans work set (ScopeInputs has no file list); the caller restricts until the CLI plan wires the answers",
    "status": "fixed",
    "reason": "",
    "recorded_at": "2026-10-31T13:43:40.051Z",
    "resolved_at": "2026-10-31T15:11:25.372Z",
    "milestone": "v1.3"
  },
  {
    "id": 3,
    "kind": "deviation",
    "phase": "27",
    "file": "skills/ai-kit-spec-goal-prompt/scripts/gp_matrix.py",
    "line": null,
    "description": "A user request for autonomous on a superpowers or none scope has no matrix row (M08 covers gsd-unproven only); the request is ignored, not listed in dropped. Decide: strategy or dropped request",
    "status": "fixed",
    "reason": "",
    "recorded_at": "2026-10-31T14:20:32.696Z",
    "resolved_at": "2026-10-31T15:11:25.447Z",
    "milestone": "v1.3"
  },
  {
    "id": 4,
    "kind": "stub",
    "phase": "27",
    "file": "skills/ai-kit-spec-goal-prompt/scripts/gp_render.py",
    "line": null,
    "description": "render raises NotImplementedError for non-OpenGSD scopes and plans work sets until plan 27-07",
    "status": "fixed",
    "reason": "",
    "recorded_at": "2026-10-31T14:33:12.924Z",
    "resolved_at": "2026-10-31T14:44:15.030Z",
    "milestone": "v1.3"
  },
  {
    "id": 5,
    "kind": "stub",
    "phase": "27",
    "file": "skills/ai-kit-spec-goal-prompt/scripts/gp_sections.py",
    "line": null,
    "description": "done_lines raises NotImplementedError for an e2e none result and for mockups until plan 27-08",
    "status": "fixed",
    "reason": "",
    "recorded_at": "2026-10-31T14:33:13.001Z",
    "resolved_at": "2026-10-31T14:53:15.996Z",
    "milestone": "v1.3"
  },
  {
    "id": 6,
    "kind": "todo",
    "phase": "27",
    "file": "tests/test_ai_kit_spec_goal_prompt_render.py",
    "line": null,
    "description": "R18/R19 parity through check_rules is not run in 27-06; owned by 27-09 Task 2",
    "status": "fixed",
    "reason": "",
    "recorded_at": "2026-10-31T14:33:13.067Z",
    "resolved_at": "2026-10-31T15:11:25.511Z",
    "milestone": "v1.3"
  },
  {
    "id": 7,
    "kind": "deviation",
    "phase": "27",
    "file": "skills/ai-kit-spec-goal-prompt/scripts/gp_render.py",
    "line": null,
    "description": "Autonomous block names an unverified primitive in its heading only; its first line must stay flags-only (D-12), so the paste text does not say unverified",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-10-31T14:44:20.838Z",
    "resolved_at": null,
    "milestone": "v1.3"
  },
  {
    "id": 8,
    "kind": "deviation",
    "phase": "27",
    "file": "skills/ai-kit-spec-goal-prompt/scripts/gp_render.py",
    "line": null,
    "description": "A rule line over 200 characters (a long plan title in OBJECTIVE or a long objective) refuses generation instead of wrapping; no wrapped-title test exists",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-10-31T14:44:20.909Z",
    "resolved_at": null,
    "milestone": "v1.3"
  }
]
````
