"""This skill's aggregator (REQ-rules-precommit) -- the file plans 11-02 and
11-03 each extend by exactly one call.

Every finding this module returns carries the same unified finding schema
every checker in this family carries: `criticality` and `summary` on
every finding, plus `category` and `issue` for structural findings. Later
plans add checks by appending one call to `check_precommit_rules` below,
never by re-shaping what an existing call already returns.
"""

from __future__ import annotations

from ai_kit_rules_common.precommit_parse import check_precommit_prepush_split

from .parity_checker import check_parity
from .taxonomy_checker import build_unclassified_findings, classify_precommit_tools


def check_precommit_rules(repo_root: str) -> list[dict]:
    """Return a flat list of findings for `repo_root`.

    Calls the bidirectional parity check (plan 11-01) and
    `check_precommit_prepush_split` from the shared package -- the call
    Phase 10's ROADMAP Success Criterion 1 amendment assigns to this phase:
    `check_precommit_prepush_split` sits in
    `skills/_shared/ai_kit_rules_common/precommit_parse.py` with a home and,
    until this function, no caller. Its finding is appended EXACTLY as
    returned -- never re-labelled, re-worded, or re-banded on the way
    through -- so the pre-prune behavior is genuinely reproduced rather than
    approximated.

    Classifies every declared tool exactly once (plan 11-02) and appends
    its unclassified-tool findings. The classification is computed ONCE and
    threaded through -- a future addition to this function (e.g. the
    category-absence checks) must read the SAME `classification` value
    rather than calling `classify_precommit_tools` a second time, so the
    two computations can never diverge on a stale cache read.
    """
    findings = list(check_parity(repo_root))
    stage_split_finding = check_precommit_prepush_split(repo_root)
    if stage_split_finding is not None:
        findings.append(stage_split_finding)
    classification = classify_precommit_tools(repo_root)
    findings.extend(build_unclassified_findings(classification))
    return findings


__all__ = ["check_precommit_rules"]
