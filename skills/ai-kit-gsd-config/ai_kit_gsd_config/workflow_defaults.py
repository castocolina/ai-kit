"""D-07 workflow-flag defaults bundle (07-CONTEXT.md). `WORKFLOW_DEFAULTS` is a fixed, literal
dict sourced from THIS project's own `.planning/config.json` `workflow.*` section as it stood on
2026-09-10 (D-07's "point-in-time baseline, not a live lookup" -- re-confirm the literal values
below still match if this plan is re-run later; they are not re-derived from that file at run
time, and no test or production code in this skill ever opens that real path).

EXCLUDES exactly five `workflow.*` keys, on purpose, so this bundle can never double-write a key
another task/plan already owns:
  - `ui_phase`, `ui_review` -- written by THIS plan's own frontend-detection task
    (`cli.py apply-workflow-defaults`'s `--ui-phase`/`--ui-review` flags), from
    `frontend_detect.detect_frontend_present`'s actual boolean result, never a bundle literal.
  - `cross_ai_execution`, `cross_ai_command`, `cross_ai_timeout`, `plan_review_convergence` --
    owned by Plan 02 (`cli.py apply-execution`/`apply-review`).

A future reader must NOT "helpfully" re-add any of these five keys here -- doing so would create
a double-write against the plan/task that already owns it.
"""

WORKFLOW_DEFAULTS = {
    "research": True,
    "plan_check": True,
    "verifier": True,
    "nyquist_validation": True,
    "auto_advance": False,
    "node_repair": True,
    "node_repair_budget": 2,
    "ui_safety_gate": True,
    "ai_integration_phase": True,
    "tdd_mode": False,
    "human_verify_mode": "end-of-phase",
    "text_mode": False,
    "research_before_questions": False,
    "discuss_mode": "discuss",
    "skip_discuss": False,
    "code_review": True,
    "code_review_depth": "standard",
    "code_review_command": None,
    "pattern_mapper": True,
    "plan_bounce": False,
    "plan_bounce_script": None,
    "plan_bounce_passes": 2,
    "auto_prune_state": False,
    "post_planning_gaps": True,
    "security_enforcement": True,
    "security_asvs_level": 1,
    "security_block_on": "high",
}

# The five keys this bundle deliberately excludes -- owned elsewhere in this phase. Exposed so
# tests (and any future reader) can assert against this list directly rather than re-typing it.
EXCLUDED_KEYS = frozenset(
    {
        "ui_phase",
        "ui_review",
        "cross_ai_execution",
        "cross_ai_command",
        "cross_ai_timeout",
        "plan_review_convergence",
    }
)
