"""Matches a CLI-native model id (e.g. opencode's "openai/gpt-5.6-sol", codex's bare
"gpt-5.6-sol") against models.dev's and Artificial Analysis's own naming -- neither source
shares a clean id with how CLIs name their models (design spec 2026-09-02, Section 3), so
this is a best-effort normalize-AND-FUZZY-MATCH lookup, not a guaranteed key lookup (spec
Section 3/6: "matching against external sources' own slug/name/model_creator fields requires
a normalization + fuzzy-match step, not a direct key lookup" -- CRITICAL finding: an earlier
draft only ever did exact comparison on the normalized string, silently missing any source
whose id spells the same model slightly differently, e.g. an extra version-suffix token or a
minor punctuation/ordering difference that survives normalization). A model this still can't
match either source is the "unmatched" case the wizard (Task 8) escalates to one targeted
search + user confirmation, never guessed here."""
import difflib
import re

_NON_ALNUM = re.compile(r"[^a-z0-9]+")
# Fuzzy fallback only ever runs after an exact normalized match already failed. Both knobs
# exist to keep fuzzy matching conservative -- a false match silently attaches one model's
# real scores/pricing to a completely different one, which is worse than an unmatched
# candidate falling through to the wizard's one-targeted-search-plus-confirmation path.
_FUZZY_THRESHOLD = 0.82   # difflib.SequenceMatcher ratio floor -- below this, "no match".
_FUZZY_MARGIN = 0.05      # top candidate must beat the runner-up by at least this much.


def _normalize(text: str | None) -> str:
    if not text:
        return ""
    return _NON_ALNUM.sub("", text.lower())


def bare_model_part(cli_model_id: str) -> str:
    """Public (Task 7's cli.py imports this rather than redefining it -- a MEDIUM finding,
    round-2 native-opus review, flagged the earlier draft's copy-pasted duplicate)."""
    return cli_model_id.split("/", 1)[1] if "/" in cli_model_id else cli_model_id


def _fuzzy_candidate_indices(target: str, normalized_options: list) -> list:
    """Token/character-similarity fallback (difflib.SequenceMatcher ratio) used ONLY after an
    exact normalized-string match found nothing. Returns every index whose ratio clears
    _FUZZY_THRESHOLD, sorted by ratio descending -- the caller applies the SAME
    collision-disambiguation (single-match / provider-hint) it already applies to exact
    matches, so fuzzy and exact matching share one collision-safety contract rather than two
    separate ones. An empty result means "no fuzzy match either" -- never a guess."""
    scored = [(difflib.SequenceMatcher(None, target, opt).ratio(), i)
              for i, opt in enumerate(normalized_options)]
    ranked = sorted(scored, reverse=True)
    if not ranked or ranked[0][0] < _FUZZY_THRESHOLD:
        return []
    # A close runner-up makes the top pick itself ambiguous -- surface ALL near-ties to the
    # caller (never silently pick the marginal "winner") so provider_hint gets a chance to
    # disambiguate them, exactly as it already does for a multi-way exact match.
    return [i for score, i in ranked if score >= _FUZZY_THRESHOLD and
            (ranked[0][0] - score) < _FUZZY_MARGIN]


_EFFORT_TOKENS = {"minimal", "low", "medium", "high", "xhigh", "thinking"}
# "max" is deliberately NOT a standalone effort token -- it collides with real base-model
# names that end in "-max" (e.g. Alibaba's qwen-max / qwen3-max, a genuinely different,
# smaller-catalog model). It is only ever stripped as part of the two-token compound
# "thinking-max" (Anthropic's own reasoning-effort naming, e.g. "claude-opus-5-thinking-max"),
# never as a bare trailing "-max".


def _strip_known_effort_suffix(bare: str) -> str | None:
    """Repeatedly strips trailing reasoning-EFFORT tokens from a bare model id -- a single
    token from _EFFORT_TOKENS, or the two-token compound "thinking-max". Returns the
    stripped id, or None when nothing was stripped. Vendor-agnostic: OpenAI's own
    reasoning-effort models use the same minimal/low/medium/high vocabulary.

    Safety against crossing a SERVICE-TIER boundary is structural, not a denylist: the loop
    only ever pops a token it positively recognizes as a reasoning-effort word, and stops at
    the first token that isn't one -- a service-tier suffix (`-fast`), a real size/tier
    designation that is simply part of the base model's own name (`-mini`, `-flash`), or
    anything unrecognized is left exactly where it was, never stripped away.

    A single call strips down to the FULLY stripped form, not a ladder of intermediate
    attempts -- e.g. for "claude-opus-5-thinking-high" it returns "claude-opus-5" directly,
    popping "high" then "thinking" in the same call; a caller wanting to also try the
    intermediate "claude-opus-5-thinking" form would need to call it differently."""
    parts = bare.split("-")
    stripped_any = False
    while len(parts) > 1:
        last = parts[-1].lower()
        if last == "max" and len(parts) > 2 and parts[-2].lower() == "thinking":
            parts.pop()
            parts.pop()
            stripped_any = True
            continue
        if last in _EFFORT_TOKENS:
            parts.pop()
            stripped_any = True
            continue
        break
    return "-".join(parts) if stripped_any else None


def match_models_dev(cli_model_id: str, models_dev_data: dict,
                      provider_hint: str | None = None,
                      allow_fuzzy: bool = True) -> dict | None:
    """Three-step lookup: (1) if cli_model_id has a "<hint>/<model>" shape, try
    models_dev_data[hint]["models"][model] directly -- an exact hinted hit is always
    unambiguous and returned immediately, no collision to consider. (2) Only when step 1
    didn't hit, search every provider's models dict for an EXACT bare-id match (a CLI's own
    provider label is not guaranteed to equal models.dev's provider key -- e.g. opencode
    namespaces differently than models.dev does). (3) CRITICAL finding: only when step 2 finds
    NOTHING AT ALL, AND allow_fuzzy is True (default), does a fuzzy fallback run --
    normalized-string similarity across every provider's every model id, via
    _fuzzy_candidate_indices. Pass allow_fuzzy=False to force exact-only matching (steps 1-2
    only) -- used by the effort-suffix enrichment retry (cli.py) to avoid compounding an
    already-inferred effort-stripped id with a second, fuzzy inference. COLLISION-SAFE at
    every step: if more than one provider's model matches (exact OR fuzzy), `provider_hint`
    (when provided) is used to pick the one whose provider_key normalizes to the same value --
    never "whichever came first in dict-iteration order" (a naive first-match would silently
    attach one vendor's fields to a different vendor's model). If more than one candidate
    remains ambiguous (no hint, or the hint doesn't disambiguate), returns None rather than
    guess. A SINGLE match (exact or fuzzy) always wins regardless of hint. Returns the
    matched model's own dict with a "provider" key added, or None."""
    bare = bare_model_part(cli_model_id)
    if "/" in cli_model_id:
        hint = cli_model_id.split("/", 1)[0]
        provider_entry = models_dev_data.get(hint)
        if provider_entry and bare in provider_entry.get("models", {}):
            return {**provider_entry["models"][bare], "provider": hint}
    pool = [(provider_key, model_id, model)
            for provider_key, provider_entry in models_dev_data.items()
            for model_id, model in provider_entry.get("models", {}).items()]
    matches = [(provider_key, model) for provider_key, model_id, model in pool if model_id == bare]
    if not matches and allow_fuzzy:
        normalized_bare = _normalize(bare)
        normalized_ids = [_normalize(model_id) for _, model_id, _ in pool]
        matches = [(pool[i][0], pool[i][2]) for i in
                   _fuzzy_candidate_indices(normalized_bare, normalized_ids)]
    if len(matches) == 1:
        provider_key, model = matches[0]
        return {**model, "provider": provider_key}
    if provider_hint:
        hint = _normalize(provider_hint)
        provider_matches = [(provider_key, model) for provider_key, model in matches
                            if _normalize(provider_key) == hint]
        if len(provider_matches) == 1:
            provider_key, model = provider_matches[0]
            return {**model, "provider": provider_key}
    return None


def match_artificial_analysis(cli_model_id: str, aa_models: list,
                               provider_hint: str | None = None) -> dict | None:
    """Matches by normalized (lowercased, non-alnum-stripped) comparison against AA's own
    `slug` and `name` fields -- AA's slugs (e.g. "gpt-5-6-sol") don't line up character-for-
    character with a CLI's own id (e.g. "gpt-5.6-sol"), so exact string equality would miss
    real matches. CRITICAL finding: when NO exact normalized match exists, a fuzzy fallback
    (_fuzzy_candidate_indices, same conservative threshold/margin as match_models_dev's) runs
    against the same slug/name fields before giving up. COLLISION-SAFE at either stage: if
    matching (exact or fuzzy) yields more than one candidate, `provider_hint` (typically
    match_models_dev's own resolved "provider" for this same cli_model_id, passed by the
    caller) is used to pick the one whose `model_creator.name` normalizes to the same value --
    never "first match wins," which could silently attribute one vendor's scores/pricing to a
    different vendor's model. If more than one candidate remains ambiguous (no hint, or the
    hint doesn't disambiguate), returns None rather than guess -- an ambiguous match becomes
    the wizard's "unmatched" case (Task 8), same as no match at all. A SINGLE match (exact or
    fuzzy) always wins regardless of hint (the common case -- no collision to resolve)."""
    bare = _normalize(bare_model_part(cli_model_id))
    candidates = [m for m in aa_models
                  if _normalize(m.get("slug", "")) == bare or _normalize(m.get("name", "")) == bare]
    if not candidates:
        normalized_options = [_normalize(m.get("slug", "")) or _normalize(m.get("name", ""))
                               for m in aa_models]
        candidates = [aa_models[i] for i in _fuzzy_candidate_indices(bare, normalized_options)]
    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0]
    if provider_hint:
        hint = _normalize(provider_hint)
        creator_matches = [m for m in candidates
                            if _normalize((m.get("model_creator") or {}).get("name", "")) == hint]
        if len(creator_matches) == 1:
            return creator_matches[0]
    return None
