"""Pure decision logic for D-03 (amended)'s critical-agent model/effort overrides
(07-CONTEXT.md). `compute_overrides` is a pure function (no I/O, no subprocess, no imports)
consuming `gsd_catalog.query_agent_catalog()`'s output -- the boundary between "read live
gsd-core state" and "decide what to write" is a function call, so this decision logic is
unit-testable against a fake catalog without ever invoking `node`.

The heavy-tier agent NAMES are never hardcoded here -- they are read from the live `tiers`
dict at run time. Only the two named top-up/floor AGENT IDs (`gsd-code-reviewer`,
`gsd-executor`) and the two phase-type floor KEYS (`models.research`/`models.execution`) are
literal, and both of those are explicit, individually-reasoned decisions from 07-CONTEXT.md
D-03, not a phase-type-bucket guess.
"""

CODE_REVIEWER_AGENT = "gsd-code-reviewer"
EXECUTOR_AGENT = "gsd-executor"
RESEARCH_PHASE_KEY = "models.research"
EXECUTION_PHASE_KEY = "models.execution"
FLOOR_MODEL = "haiku"
HEAVY_TIER_MODEL = "opus"
HEAVY_TIER_EFFORT = "high"

HEAVY_TIER_VALUE = "heavy"


def _model_override_key(agent: str) -> str:
    return f"model_overrides.{agent}"


def _effort_override_key(agent: str) -> str:
    return f"effort.agent_overrides.{agent}"


def compute_overrides(tiers):
    """Always includes, regardless of `tiers`'s value (even `None`), these five unconditional
    pairs -- never conditional on successfully reading the live catalog (D-03: the
    `gsd-executor` floor "must hold even without this phase's critical-agent logic at all"):
      - model_overrides.gsd-code-reviewer -> opus
      - effort.agent_overrides.gsd-code-reviewer -> high
      - model_overrides.gsd-executor -> haiku
      - models.research -> haiku
      - models.execution -> haiku

    When `tiers` is a non-empty dict, for EVERY (agent, tier) pair where tier == "heavy" AND
    agent != EXECUTOR_AGENT, additionally includes model_overrides.<agent> -> opus and
    effort.agent_overrides.<agent> -> high. The EXECUTOR_AGENT exclusion applies to the WHOLE
    agent in the iteration itself, not merely a dedup against the five already-written keys --
    this closes the cross-AI review Cycle 2 MEDIUM finding: deduping only by already-known key
    path would let a future gsd-core reclassifying gsd-executor as "heavy" add
    effort.agent_overrides.gsd-executor: "high" (a key the unconditional set does NOT already
    contain) alongside the unconditional model_overrides.gsd-executor: "haiku" floor -- an
    internally contradictory cheapest-model/maximum-effort pairing that directly undercuts
    D-03's "cheapest tier, always" guarantee for gsd-executor. Skipping EXECUTOR_AGENT in the
    iteration itself closes this for every future key the sweep might otherwise add for that
    agent, not just the one key this phase happens to write today.

    For an agent whose tier is "standard"/"light" and who is not gsd-code-reviewer/
    gsd-executor, writes NOTHING for that agent.

    When `tiers` is `None` or empty, returns ONLY the five unconditional pairs -- no heavy-
    tier sweep keys, and this never raises.
    """
    overrides = {
        _model_override_key(CODE_REVIEWER_AGENT): HEAVY_TIER_MODEL,
        _effort_override_key(CODE_REVIEWER_AGENT): HEAVY_TIER_EFFORT,
        _model_override_key(EXECUTOR_AGENT): FLOOR_MODEL,
        RESEARCH_PHASE_KEY: FLOOR_MODEL,
        EXECUTION_PHASE_KEY: FLOOR_MODEL,
    }

    if tiers:
        for agent, tier in tiers.items():
            if tier != HEAVY_TIER_VALUE:
                continue
            if agent == EXECUTOR_AGENT:
                continue
            overrides[_model_override_key(agent)] = HEAVY_TIER_MODEL
            overrides[_effort_override_key(agent)] = HEAVY_TIER_EFFORT

    return overrides
