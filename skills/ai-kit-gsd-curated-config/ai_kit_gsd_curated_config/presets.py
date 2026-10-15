"""Rigor preset tables and pure dotted-key helpers for the recommend engine.

Source of the tables: spec §5 of
`docs/superpowers/specs/2026-09-23-gsd-curated-config-v2-design.md`; every key and
value below was verified valid against a live gsd-core 1.16 `isValidConfigKey` probe
(2026-10-15). `workflow.live_dom_uat` is deliberately absent from every table
(17 D-29: it is never set or unset by the plan; the rigorous+frontend case surfaces
as a note instead, see `recommend._preset_layer`).

This module is data plus pure functions only: no I/O, no clock, no environment.
"""
from typing import Any

RIGORS = ("mvp", "standard", "rigorous")
TIERS = ("opus", "sonnet", "haiku")

# The at-most-7 specialist agents that may receive a `model_overrides.<agent>` key
# (spec §4; Pattern 10).
SPECIALISTS = (
    "gsd-plan-checker",
    "gsd-code-reviewer",
    "gsd-ui-auditor",
    "gsd-dom-verifier",
    "gsd-ui-researcher",
    "gsd-executor",
    "gsd-code-fixer",
)

# Rigor presets (spec §5). Keys absent from a rigor's table are simply not set by it.
PRESETS: dict[str, dict[str, Any]] = {
    "mvp": {
        "granularity": "coarse",
        "workflow.mvp_mode": True,
        "effort.routing_tier_defaults.heavy": "high",
        "effort.routing_tier_defaults.standard": "medium",
        "effort.routing_tier_defaults.light": "minimal",
        "effort.agent_overrides.gsd-executor": "medium",
        "effort.agent_overrides.gsd-code-fixer": "medium",
        "workflow.research": True,
        "workflow.plan_check": True,
        "workflow.verifier": True,
        "workflow.pattern_mapper": True,
        "workflow.nyquist_validation": False,
        "workflow.tdd_mode": False,
        "workflow.code_review_depth": "quick",
        "workflow.security_asvs_level": 1,
        "workflow.security_block_on": "critical",
        "workflow.ui_review": False,
        "intel.enabled": False,
    },
    "standard": {
        "granularity": "standard",
        "effort.routing_tier_defaults.heavy": "xhigh",
        "effort.routing_tier_defaults.standard": "high",
        "effort.routing_tier_defaults.light": "low",
        "effort.agent_overrides.gsd-executor": "medium",
        "effort.agent_overrides.gsd-code-fixer": "medium",
        "workflow.research": True,
        "workflow.plan_check": True,
        "workflow.verifier": True,
        "workflow.pattern_mapper": True,
        "workflow.nyquist_validation": True,
        "workflow.tdd_mode": False,
        "workflow.code_review_depth": "standard",
        "workflow.security_asvs_level": 1,
        "workflow.security_block_on": "high",
        "intel.enabled": True,
    },
    "rigorous": {
        "granularity": "fine",
        "effort.routing_tier_defaults.heavy": "xhigh",
        "effort.routing_tier_defaults.standard": "high",
        "effort.routing_tier_defaults.light": "low",
        "effort.agent_overrides.gsd-executor": "medium",
        "effort.agent_overrides.gsd-code-fixer": "medium",
        "effort.agent_overrides.gsd-code-reviewer": "xhigh",
        "workflow.research": True,
        "workflow.plan_check": True,
        "workflow.verifier": True,
        "workflow.pattern_mapper": True,
        "workflow.nyquist_validation": True,
        "workflow.tdd_mode": True,
        "workflow.code_review_depth": "deep",
        "workflow.security_asvs_level": 2,
        "workflow.security_block_on": "medium",
        "workflow.ui_review": True,
        "intel.enabled": True,
        "code_quality.fallow.enabled": True,
        "code_quality.fallow.profile": "standard",
        "refactor.trigger_enabled": True,
        "dynamic_routing.enabled": True,
        "dynamic_routing.escalate_on_failure": True,
        "dynamic_routing.max_escalations": 1,
    },
}

# Rigor-level phase shifts: the whole phase type moves to a tier (spec §5, R8).
PHASE_SHIFTS: dict[str, dict[str, str]] = {
    "mvp": {"research": "haiku", "verification": "haiku"},
    "standard": {},
    "rigorous": {"planning": "opus", "verification": "sonnet"},
}

# Conditional preset keys: `workflow.ui_phase` on every rigor, `workflow.ui_review`
# on standard (both mirror `project.frontend`), and the grounding authority only
# when the intel index exists.
CONDITIONAL_KEYS = (
    "workflow.ui_phase",
    "workflow.ui_review",
    "plan_review.source_grounding_authority",
)

# Cross-AI answer keys (17 D-19): the two booleans are set from the answers; a yes
# additionally reserves a needs_choice slot for the Phase 18 selection keys.
CROSS_AI_KEYS = (
    "workflow.plan_review_convergence",
    "workflow.cross_ai_execution",
    "workflow.cross_ai_command",
    "review.default_reviewers",
)

DYNAMIC_ROUTING_EFFECT = (
    "unverified: no tier_models; resolve-model --attempt unchanged in gsd-core 1.16"
)
PI_EFFECT = "effect unverified on pi (gsd-core registry: namedDispatch false)"

PRICE_PERCENTILE = {"mvp": 0.40, "standard": 0.75, "rigorous": None}

CODEX_EFFECT = "resolve-model only (codex bakes only explicit model_overrides)"

# review.* and effort.* are narrowed to what the plan can write (17-REVIEW A-IN-09), so user
# tuning knobs such as review.max_prompt_tokens or effort.default are never unset.
MANAGED_PREFIXES = (
    "models.",
    "model_overrides.",
    "effort.routing_tier_defaults.",
    "effort.agent_overrides.",
    "dynamic_routing.",
    "review.models.",
    "review.effort.",
    "agent_skills.",
)


def _managed_key_set() -> frozenset:
    keys: set = set()
    for table in PRESETS.values():
        keys.update(table)
    keys.update(CONDITIONAL_KEYS)
    keys.update(CROSS_AI_KEYS)
    keys.add("model_profile")
    return frozenset(keys)


MANAGED_KEYS = _managed_key_set()

RUNTIME_MANAGED_HOSTS = ("opencode", "codex")


def is_managed(key: str, host: str) -> bool:
    """True when `key` belongs to a plan-managed config family for `host`.

    `runtime`, `resolve_model_ids` and `model_policy` are reconciled from inventory
    conflicts, never by family (D-08, D-21, D-23)."""
    if key in MANAGED_KEYS:
        return True
    for prefix in MANAGED_PREFIXES:
        if key.startswith(prefix):
            return True
    return key.startswith(f"model_profile_overrides.{host}.")


def preset_values(rigor: str, project: dict) -> dict:
    """The §5 preset dict for `rigor` plus its conditional keys, resolved from the
    inventory's `project` facts. Returns a fresh dict on every call."""
    values = dict(PRESETS[rigor])
    values["workflow.ui_phase"] = bool(project.get("frontend", False))
    if rigor == "standard":
        values["workflow.ui_review"] = values["workflow.ui_phase"]
    if rigor == "rigorous" and project.get("intel_index_present", False):
        values["plan_review.source_grounding_authority"] = "intel"
    return values


def closed_key_set(host: str) -> list:
    """Every dotted config key `recommend` can propose for `host` (D-09): the union
    of the preset tables over all rigors, the conditional and cross-AI keys, the
    tier-layer keys and one `model_overrides.<agent>` per specialist. `inventory`
    probes these against the host gsd-core's `isValidConfigKey`."""
    keys: set = set()
    for table in PRESETS.values():
        keys.update(table)
    keys.update(CONDITIONAL_KEYS)
    keys.update(CROSS_AI_KEYS)
    keys.update(("model_profile", "runtime", "resolve_model_ids"))
    for phases in PHASE_SHIFTS.values():
        keys.update(f"models.{phase}" for phase in phases)
    for tier in TIERS:
        keys.add(f"model_profile_overrides.{host}.{tier}")
    for agent in SPECIALISTS:
        keys.add(f"model_overrides.{agent}")
    return sorted(keys)


def get_dotted(values: dict, key: str) -> Any:
    """The value at dotted `key` in a nested dict, or `None` when any segment is
    missing."""
    node: Any = values
    for segment in key.split("."):
        if not isinstance(node, dict) or segment not in node:
            return None
        node = node[segment]
    return node


def flatten_config(values: dict) -> dict:
    """Dotted leaf -> value view of a nested config dict.

    Recursion stops at non-dict values and at the two value-object shapes the live
    gsd-core 1.16 `isValidConfigKey` accepts as single keys (verified 2026-10-15):
    a dict at path depth 3 under `model_profile_overrides`
    (`model_profile_overrides.<rt>.<tier>`) and a dict at path depth 4 under
    `model_policy.runtime_tiers` (`model_policy.runtime_tiers.<rt>.<tier>`). The
    `.model` / `.reasoning_effort` paths below those are rejected live, so they must
    never appear as flattened keys. Empty dicts yield no leaf.
    """
    out: dict = {}

    def _walk(node: dict, parts: tuple) -> None:
        for name, value in node.items():
            path = (*parts, name)
            dotted = ".".join(path)
            if isinstance(value, dict):
                if not value:
                    continue
                value_object = len(path) == 3 and path[0] == "model_profile_overrides"
                tier_object = (
                    len(path) == 4 and path[0] == "model_policy" and path[1] == "runtime_tiers"
                )
                if value_object or tier_object:
                    out[dotted] = value
                else:
                    _walk(value, path)
                continue
            out[dotted] = value

    _walk(values, ())
    return out
