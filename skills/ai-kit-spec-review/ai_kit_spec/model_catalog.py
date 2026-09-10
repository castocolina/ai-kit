"""Model catalog cache: canonical identity, type-checked schema validation, single-entry
merge, current-snapshot filtering, and heuristic-correction writeback (design spec
2026-09-02, Sections 4/5/8). One bad entry is rejected and reported; it never aborts the
whole catalog write."""
import os
import re

from ai_kit_spec.cache import cache_base

CATALOG_TTL_SECONDS = 30 * 24 * 3600  # ~30 days -- spec Section 8, same order as RUNTIMES_TTL

_MANDATORY_CATALOG_FIELDS = {"provider", "runtimes", "source", "confidence", "last_verified"}
_VALID_CONFIDENCE = {"high", "medium", "low"}
_LAST_VERIFIED_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
# type checks for every field this design names -- mandatory AND optional. A field not in this
# table (there shouldn't be one; every field the design spec names is listed) is left unchecked
# rather than rejected, so an unrecognized-but-harmless future field never blocks a write.
_FIELD_TYPES = {
    "provider": str, "source": dict, "confidence": str, "last_verified": str,
    "batch_mode": bool, "is_router": bool, "fallback_quota": bool,
    "tokens_per_sec": (int, float), "max_output_tokens": int, "structured_output": bool,
    "tool_calling": bool, "native": bool, "reasoning_modes": list, "fast_mode": bool,
    "speed_tier": str, "name_declared_purpose": str, "native_runtime": str,
    # HIGH finding: is_router/batch_mode/fallback_quota have no external source (spec §3) --
    # they are ALWAYS either a naming heuristic's guess or a user's explicit confirmation of
    # that guess, and a plain bool alone cannot tell those two provenances apart. This list
    # records which of those three field names the user has actually been asked about and
    # answered (Step 8 of ai-kit-spec-config, Task 8) -- whether they left the heuristic's
    # value unchanged or corrected it -- so the wizard never re-asks about a field already
    # confirmed. Written exclusively by apply_heuristic_corrections below.
    "heuristic_confirmed": list,
}
_NUMERIC_SUBFIELD_TABLES = {
    "scores": {"intelligence_index", "coding_index", "agentic_index"},
    "pricing": {"input_per_1m", "output_per_1m"},
}
_RUNTIME_FIELD_TYPES = {"model_id": str, "ctx_window": (int, float)}
_VALID_NAME_DECLARED_PURPOSE = {"review", "execute"}
_VALID_NATIVE_RUNTIME = {"claude", "opencode", "codex", "cursor", "unknown"}


def cache_catalog_path(env: dict) -> str:
    return os.path.join(cache_base(env), "model-catalog.json")


def canonical_key(provider: str, bare_model_id: str) -> str:
    """The ONE place catalog identity is computed -- every writer of model-catalog.json goes
    through this, so two CLIs naming the same real model differently (opencode's
    "openai/gpt-5.6-sol" vs. codex's bare "gpt-5.6-sol") always collapse to one key."""
    return f"{provider}/{bare_model_id}"


def validate_catalog_entry(model_id: str, entry: dict) -> str | None:
    """Mandatory fields per spec Section 5: provider, runtimes (non-empty dict), source,
    confidence, last_verified -- checked for PRESENCE and TYPE (last_verified additionally
    checked for YYYY-MM-DD shape). Every optional field IS type-checked when present (a
    missing optional field is never a validation failure -- only a reduced ranking signal
    later, model_ranker.py); a present-but-wrong-typed one is. Every `runtimes` value's own
    `model_id`/`ctx_window` sub-fields are type-checked too when present, not just the
    top-level "is it a dict" shape check."""
    missing = _MANDATORY_CATALOG_FIELDS - entry.keys()
    if missing:
        return f"{model_id}: missing mandatory field(s) {sorted(missing)}"
    if not isinstance(entry.get("runtimes"), dict) or not entry["runtimes"]:
        return f"{model_id}: 'runtimes' must be a non-empty object"
    for cli_name, rt in entry["runtimes"].items():
        if not isinstance(rt, dict):
            return f"{model_id}: every 'runtimes' value must be an object"
        for field, expected_type in _RUNTIME_FIELD_TYPES.items():
            if field in rt and rt[field] is not None and not isinstance(rt[field], expected_type):
                return f"{model_id}: 'runtimes.{cli_name}.{field}' must be of type {expected_type}"
    if entry.get("confidence") not in _VALID_CONFIDENCE:
        return f"{model_id}: 'confidence' must be one of {sorted(_VALID_CONFIDENCE)}"
    if "last_verified" in entry and isinstance(entry["last_verified"], str) and \
            not _LAST_VERIFIED_RE.match(entry["last_verified"]):
        return f"{model_id}: 'last_verified' must be YYYY-MM-DD"
    for field, expected_type in _FIELD_TYPES.items():
        if field not in entry:
            continue
        # HIGH finding: an explicit None on an OPTIONAL field means "no value" (and, per
        # merge_catalog_entry below, "clear this field on merge") -- it must never be rejected
        # as a type mismatch, the same way a runtime sub-field's None is already exempted above.
        # Important finding: that exemption must NOT extend to a MANDATORY field -- provider/
        # source/last_verified are mandatory (in _MANDATORY_CATALOG_FIELDS) even though they
        # also appear in this type table, so an explicit None there is a missing-mandatory-field
        # failure, not a harmless clear signal.
        if entry[field] is None:
            if field in _MANDATORY_CATALOG_FIELDS:
                return f"{model_id}: '{field}' must be of type {expected_type} (got None)"
            continue
        if not isinstance(entry[field], expected_type):
            return f"{model_id}: '{field}' must be of type {expected_type}"
    if "name_declared_purpose" in entry and entry["name_declared_purpose"] is not None \
            and entry["name_declared_purpose"] not in _VALID_NAME_DECLARED_PURPOSE:
        return (f"{model_id}: 'name_declared_purpose' must be one of "
                f"{sorted(_VALID_NAME_DECLARED_PURPOSE)}")
    # Forward-compatible schema support only: no current code path in this
    # codebase produces a model_catalog.py entry with a `cli` key at all
    # (verified this phase: `cli` does not appear anywhere in `_FIELD_TYPES` /
    # `_MANDATORY_CATALOG_FIELDS` / `_RUNTIME_FIELD_TYPES`). Satisfies
    # REQUIREMENTS.md's literal "model-catalog entries" wording without
    # claiming it is reachable by any live code path today.
    if "native_runtime" in entry and entry["native_runtime"] is not None \
            and entry["native_runtime"] not in _VALID_NATIVE_RUNTIME:
        return (f"{model_id}: 'native_runtime' must be one of "
                f"{sorted(_VALID_NATIVE_RUNTIME)}")
    if "native_runtime" in entry and entry.get("native_runtime") is not None \
            and entry.get("cli") is not None:
        return (f"{model_id}: 'native_runtime' must not be set on an "
                f"entry with a non-null 'cli'")
    if "reasoning_modes" in entry and isinstance(entry["reasoning_modes"], list) and \
            not all(isinstance(m, str) for m in entry["reasoning_modes"]):
        return f"{model_id}: 'reasoning_modes' must be a list of strings"
    if "heuristic_confirmed" in entry and isinstance(entry["heuristic_confirmed"], list) and \
            not all(isinstance(f, str) for f in entry["heuristic_confirmed"]):
        return f"{model_id}: 'heuristic_confirmed' must be a list of strings"
    for table_field, subfields in _NUMERIC_SUBFIELD_TABLES.items():
        table = entry.get(table_field)
        if table is None:
            continue
        if not isinstance(table, dict):
            return f"{model_id}: '{table_field}' must be an object"
        for k, v in table.items():
            if k in subfields and v is not None and not isinstance(v, (int, float)):
                return f"{model_id}: '{table_field}.{k}' must be numeric"
    return None


def merge_catalog_entry(catalog: dict, model_id: str, entry: dict) -> tuple:
    """Returns (new_catalog, rejection_reason). Never mutates `catalog`. An invalid entry is
    rejected and reported (spec Section 8: "that single entry is rejected and reported; the
    rest of the write proceeds") -- the caller (fetch-model-catalog, Task 7) collects
    rejections across a whole discovery run and reports them together, never aborting.
    `runtimes` is MERGED into any existing entry at this key, never replaced wholesale --
    this is what lets two different CLIs' runtime mappings for the same real model coexist
    under one canonical key (HIGH finding: catalog identity must not lose runtime mappings)."""
    reason = validate_catalog_entry(model_id, entry)
    if reason:
        return catalog, reason
    updated = dict(catalog)
    existing = updated.get(model_id)
    if existing:
        merged = {**existing, **entry}
        merged["runtimes"] = {**existing.get("runtimes", {}), **entry.get("runtimes", {})}
        # CRITICAL finding: an explicit None in the INCOMING `entry` means "this field's owning
        # source no longer confirms it -- clear it", not "leave whatever's cached untouched".
        # Plain dict-spread (`{**existing, **entry}`) cannot express that distinction on its
        # own: a key entirely ABSENT from `entry` is correctly preserved from `existing` (a
        # source that's simply down this run never wrote the key at all), but a key PRESENT in
        # `entry` with value None is a deliberate clear -- stripped here so a later re-query
        # that flips a source's provenance to false can never leave stale scores/pricing/etc.
        # behind under a now-false `source.*` flag.
        merged = {k: v for k, v in merged.items() if not (k in entry and entry[k] is None)}
        updated[model_id] = merged
    else:
        # A brand-new entry never needs the clear-signal: strip any None-valued optional field
        # so the catalog stays free of meaningless nulls for a key that never had a prior value.
        updated[model_id] = {k: v for k, v in entry.items() if v is not None}
    return updated, None


def current_candidate_keys(catalog: dict, discovered_models: list) -> set:
    """The subset of catalog keys whose `runtimes` contain at least one (cli, model_id) pair
    from `discovered_models` (the same [{"cli", "model_id"}, ...] shape Task 7 builds from a
    fresh runtimes snapshot). Used to exclude stale entries -- a model no longer installed --
    from ranking/presentation (Task 8) without deleting them from the cache."""
    discovered_pairs = {(c["cli"], c["model_id"]) for c in discovered_models}
    return {
        key for key, entry in catalog.items()
        if any((cli, rt.get("model_id")) in discovered_pairs
               for cli, rt in entry.get("runtimes", {}).items())
    }


def apply_heuristic_corrections(catalog: dict, model_id: str, corrections: dict) -> tuple:
    """Merges user-confirmed heuristic fields (is_router/batch_mode/fallback_quota, any
    subset) into one existing entry. Never mutates `catalog`. A `model_id` not already in
    `catalog` is a no-op -- correcting a field on an entry that doesn't exist has nothing to
    do (the wizard, Task 8, only ever corrects an entry it just displayed, which is always
    already in the catalog by then). Returns (new_catalog, rejection_reason) -- CRITICAL
    finding: a correction is validated through validate_catalog_entry BEFORE it is applied,
    exactly like merge_catalog_entry's own contract, since cache_write_json only writes
    atomically and never validates. A rejected correction leaves the existing entry
    untouched and is reported, never silently written.

    HIGH finding: is_router/batch_mode/fallback_quota have no external source (spec §3) --
    every value on these three fields is either the naming heuristic's own guess or a value
    this function has recorded as user-confirmed; a plain bool alone cannot distinguish the
    two, so a re-run of the wizard could never tell "never asked" apart from "asked and the
    user's answer happened to match the heuristic's guess." EVERY key present in
    `corrections` is therefore added to the merged entry's `heuristic_confirmed` list --
    regardless of whether the corrected value actually differs from what was already stored
    -- because it is the act of asking-and-answering that matters, not whether the answer
    changed anything. Callers (Task 7's `apply-heuristic-correction` subcommand, and Task 8's
    wizard Step 8) MUST call this for every field they present to the user, even when the
    user simply confirms the heuristic's guess as correct -- calling it only on an actual
    correction would leave confirmed-but-unchanged fields indistinguishable from
    never-asked ones, defeating the whole point of this field."""
    if model_id not in catalog:
        return catalog, None
    candidate = {**catalog[model_id], **corrections}
    already_confirmed = set(catalog[model_id].get("heuristic_confirmed", []))
    candidate["heuristic_confirmed"] = sorted(already_confirmed | set(corrections.keys()))
    reason = validate_catalog_entry(model_id, candidate)
    if reason:
        return catalog, reason
    updated = dict(catalog)
    updated[model_id] = candidate
    return updated, None
