"""Deterministic candidate resolution for ai-kit-spec-execute: task-type affinity + context-size
fit. Never LLM judgment per-execution -- both signals come from data curated once at
ai-kit-spec-config time (design spec Section 5)."""


def purpose_matches(purpose: str | None, wanted: str) -> bool:
    """A candidate's `purpose` ("review" | "execute" | "both" | None) matches a consumer's
    `wanted` role ("review" or "execute") when it's unset (no preference declared -- the
    field did not exist before this design, spec 2026-09-02), equals `wanted` exactly, or is
    the explicit "both" value. Shared by filter_by_purpose (execute-side, candidate-dict
    shape) and quota.py's own ladder-key-list-shaped filter -- one predicate, two shapes."""
    return purpose is None or purpose == wanted or purpose == "both"


def filter_by_purpose(candidates: list, purpose: str) -> list:
    """Same never-empty-on-curation-gap contract as filter_by_affinity: an entry with no
    `purpose` set always passes (no preference declared); if the matching-or-unset subset is
    empty, every candidate is returned unfiltered rather than starving the whole pipeline over
    a config that simply hasn't been curated with `purpose` yet."""
    matching = [c for c in candidates if purpose_matches(c.get("purpose"), purpose)]
    return matching if matching else list(candidates)


def filter_by_affinity(candidates: list, task_type: str, affinity_table: dict) -> list:
    """Affinity is a preference, never a hard requirement. Precise rule (a mixed candidate set
    of tagged + untagged behaves differently from an all-mismatched set, by design -- read
    carefully): an untagged candidate (`task_affinity is None`) always passes, since it declares
    no preference at all; a tagged candidate only passes when its tag equals `task_type`. If
    that combined result is non-empty -- whether from untagged-only, matching-only, or a mix of
    both -- return exactly that set (a candidate explicitly tagged for a DIFFERENT task_type is
    excluded in favor of the untagged/matching ones, which is the whole point of having
    `task_affinity` at all). ONLY when the result is completely empty (every candidate is tagged
    for some other task_type, none untagged, none matching) does this fall back to returning
    every candidate unfiltered -- an empty result here would otherwise silently break the whole
    resolution pipeline over a curation gap, not a real unavailability.

    `affinity_table` is intentionally UNUSED in Foundation -- reserved as a hook for a future
    task_type-alias mapping (e.g. resolving "front-end-heavy" to "frontend" before comparing
    against each candidate's own `task_affinity`), not yet needed because nothing in this plan
    populates alias variants. Keeping the parameter now (rather than adding it later, which
    would change every caller's signature again) costs nothing and documents the intended
    extension point honestly instead of silently. Do not implement alias-matching logic here
    speculatively -- add it only when a real caller needs it."""
    matching = [c for c in candidates
                if c.get("task_affinity") is None or c.get("task_affinity") == task_type]
    return matching if matching else list(candidates)


def filter_by_context(candidates: list, required_context: int) -> list:
    """A candidate with no curated context_limit yet is passed through, not dropped -- missing
    data must never look identical to 'confirmed insufficient'."""
    return [c for c in candidates
            if c.get("context_limit") is None or c["context_limit"] >= required_context]


def resolve_execute_candidates(candidates: list, task_type: str, required_context: int,
                                affinity_table: dict, top_n_keys: list) -> list:
    """Full candidate-narrowing pipeline. The result's ORDER is what a caller feeds to
    quota.py's resolve_ladder_pick (via candidates_to_ladder, below) for live-availability
    escalation -- this function only narrows and ranks, it never itself probes quota.

    Ranks confirmed-sufficient-context candidates before unknown-context ones -- "unknown" must
    never look like "fits great" (matches filter_by_context's own never-drop-on-missing-data
    rule: unknown is passed through, but ranked conservatively, not favorably).

    Purpose narrowing runs FIRST (2026-09-02 design): an execute consumer only wants
    purpose in {"execute", "both", None} candidates before task_affinity/context even apply.

    Ranking also applies the design's `task_affinity_match` bonus (spec §6) as a BOUNDED
    TIE-BREAK, ordered AFTER top_n_keys rank in the sort key (CRITICAL finding, round 3: an
    earlier draft placed it BEFORE rank, which is not "capped at +15" at all -- it let an
    exact-affinity, dead-last candidate outrank an explicit top_n_keys #1 pick, an unbounded
    override rather than a small additive bonus on a 0-100 score). Placed after rank, the
    bonus only ever matters among candidates the ladder itself treats as equally ranked --
    both explicitly tied, or (the common real case) both absent from top_n_keys and sharing
    the same fallback rank -- never a real, distinguishing rank difference. This is where that
    bonus actually applies -- it needs a real task_type, which only exists here, at real
    dispatch time, never at Plan A's generic wizard-time ranking (see that plan's Global
    Constraints)."""
    narrowed = filter_by_context(
        filter_by_affinity(filter_by_purpose(candidates, "execute"), task_type, affinity_table),
        required_context)
    rank = {key: i for i, key in enumerate(top_n_keys)}
    return sorted(
        narrowed,
        key=lambda c: (c.get("context_limit") is None,
                        rank.get(c["key"], len(top_n_keys)),
                        c.get("task_affinity") != task_type),
    )


def candidates_to_ladder(candidates: list) -> list:
    """Adapter to quota.py's real resolve_ladder_pick(reviewers, ladder, skip_vendor, quota)
    signature -- `ladder` there is a plain ordered list of key strings. Callers must pass this
    function's output (never `candidates` itself) as that `ladder` argument, and the same
    `candidates` list as `reviewers`, to get a live-quota-checked pick -- resolve_execute_
    candidates above only narrows/ranks, it never checks quota itself."""
    return [c["key"] for c in candidates]
