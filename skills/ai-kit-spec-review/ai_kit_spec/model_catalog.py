"""Model catalog cache: canonical identity, type-checked schema validation, single-entry
merge, current-snapshot filtering, and heuristic-correction writeback (design spec
2026-09-02, Sections 4/5/8). One bad entry is rejected and reported; it never aborts the
whole catalog write."""
import os
import re

from ai_kit_spec.cache import cache_base

CATALOG_TTL_SECONDS = 30 * 24 * 3600  # ~30 days -- spec Section 8, same order as RUNTIMES_TTL

# 16 D-12: the catalog's own metadata lives in this reserved top-level object because every
# other top-level key is a `provider/model` canonical key (canonical keys always contain `/`,
# _meta never does); pre-Phase-16 catalogs have no `_meta` and count as version 1.
CATALOG_SCHEMA_VERSION = 2
CATALOG_META_KEY = "_meta"

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
    # 16 D-09 — optional; absent means unknown; written only from a source statement.
    "image_input": bool,
    # 16 D-09 (review cycle 2 MEDIUM) — field-level provenance of image_input.
    "image_input_source": str,
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
_VALID_IMAGE_INPUT_SOURCE = {"models_dev", "opencode"}
# Deliberately duplicated with config_io._VALID_NATIVE_RUNTIME -- the two sets must change
# together (AGENTS.md Architecture). "pi" is here because detect_current_runtime can return it
# since Phase 16.
_VALID_NATIVE_RUNTIME = {"claude", "opencode", "codex", "cursor", "pi", "unknown"}


def cache_catalog_path(env: dict) -> str:
    return os.path.join(cache_base(env), "model-catalog.json")


def split_catalog_meta(raw) -> tuple:
    """16 D-12: splits a raw catalog file's dict into (entries, meta). Entries is every
    top-level key except the reserved CATALOG_META_KEY; meta is a shallow copy of that
    key's value when it is a dict, else {}. Never raises, never mutates its input; a
    non-dict `raw` (None, a list, a string) splits to ({}, {})."""
    if not isinstance(raw, dict):
        return {}, {}
    entries = {k: v for k, v in raw.items() if k != CATALOG_META_KEY}
    meta = raw.get(CATALOG_META_KEY)
    return entries, dict(meta) if isinstance(meta, dict) else {}


def join_catalog_meta(entries: dict, meta: dict) -> dict:
    """16 D-12: inverse of split_catalog_meta -- a new dict of `entries` plus the reserved
    CATALOG_META_KEY only when `meta` is non-empty (an empty meta writes no `_meta` key).
    Never mutates either input."""
    joined = dict(entries)
    if meta:
        joined[CATALOG_META_KEY] = dict(meta)
    return joined


def catalog_schema_is_current(meta) -> bool:
    """16 D-12: mirrors runtimes_schema_is_current -- True only for a dict whose
    `schema_version` is a non-bool int >= CATALOG_SCHEMA_VERSION. A missing or older
    version counts as stale whatever the TTL says. Never raises."""
    if not isinstance(meta, dict):
        return False
    version = meta.get("schema_version")
    return isinstance(version, int) and not isinstance(version, bool) \
        and version >= CATALOG_SCHEMA_VERSION


def canonical_key(provider: str, bare_model_id: str) -> str:
    """The ONE place catalog identity is computed -- every writer of model-catalog.json goes
    through this, so two CLIs naming the same real model differently (opencode's
    "openai/gpt-5.6-sol" vs. codex's bare "gpt-5.6-sol") always collapse to one key."""
    return f"{provider}/{bare_model_id}"


def _validate_mandatory_fields(model_id: str, entry: dict) -> str | None:
    missing = _MANDATORY_CATALOG_FIELDS - entry.keys()
    if missing:
        return f"{model_id}: missing mandatory field(s) {sorted(missing)}"
    return None


def _validate_runtimes_shape(model_id: str, entry: dict) -> str | None:
    if not isinstance(entry.get("runtimes"), dict) or not entry["runtimes"]:
        return f"{model_id}: 'runtimes' must be a non-empty object"
    for cli_name, rt in entry["runtimes"].items():
        if not isinstance(rt, dict):
            return f"{model_id}: every 'runtimes' value must be an object"
        for field, expected_type in _RUNTIME_FIELD_TYPES.items():
            if field in rt and rt[field] is not None and not isinstance(rt[field], expected_type):
                return f"{model_id}: 'runtimes.{cli_name}.{field}' must be of type {expected_type}"
    return None


def _validate_confidence_and_dates(model_id: str, entry: dict) -> str | None:
    if entry.get("confidence") not in _VALID_CONFIDENCE:
        return f"{model_id}: 'confidence' must be one of {sorted(_VALID_CONFIDENCE)}"
    if "last_verified" in entry and isinstance(entry["last_verified"], str) and \
            not _LAST_VERIFIED_RE.match(entry["last_verified"]):
        return f"{model_id}: 'last_verified' must be YYYY-MM-DD"
    return None


def _validate_typed_fields(model_id: str, entry: dict) -> str | None:
    for field, expected_type in _FIELD_TYPES.items():
        if field not in entry:
            continue
        if entry[field] is None:
            if field in _MANDATORY_CATALOG_FIELDS:
                return f"{model_id}: '{field}' must be of type {expected_type} (got None)"
            continue
        if not isinstance(entry[field], expected_type):
            return f"{model_id}: '{field}' must be of type {expected_type}"
    return None


def _validate_declared_purpose_fields(model_id: str, entry: dict) -> str | None:
    if "name_declared_purpose" in entry and entry["name_declared_purpose"] is not None \
            and entry["name_declared_purpose"] not in _VALID_NAME_DECLARED_PURPOSE:
        return (f"{model_id}: 'name_declared_purpose' must be one of "
                f"{sorted(_VALID_NAME_DECLARED_PURPOSE)}")
    if "image_input_source" in entry and entry["image_input_source"] is not None \
            and entry["image_input_source"] not in _VALID_IMAGE_INPUT_SOURCE:
        return (f"{model_id}: 'image_input_source' must be one of "
                f"{sorted(_VALID_IMAGE_INPUT_SOURCE)}")
    if entry.get("image_input_source") is not None \
            and not isinstance(entry.get("image_input"), bool):
        return f"{model_id}: 'image_input_source' requires a bool 'image_input'"
    return None


def _validate_native_runtime_fields(model_id: str, entry: dict) -> str | None:
    if "native_runtime" in entry and entry["native_runtime"] is not None \
            and entry["native_runtime"] not in _VALID_NATIVE_RUNTIME:
        return (f"{model_id}: 'native_runtime' must be one of "
                f"{sorted(_VALID_NATIVE_RUNTIME)}")
    if "native_runtime" in entry and entry.get("native_runtime") is not None \
            and entry.get("cli") is not None:
        return (f"{model_id}: 'native_runtime' must not be set on an "
                f"entry with a non-null 'cli'")
    return None


def _validate_list_and_numeric_tables(model_id: str, entry: dict) -> str | None:
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


_CATALOG_ENTRY_VALIDATORS = (
    _validate_mandatory_fields,
    _validate_runtimes_shape,
    _validate_confidence_and_dates,
    _validate_typed_fields,
    _validate_declared_purpose_fields,
    _validate_native_runtime_fields,
    _validate_list_and_numeric_tables,
)


def validate_catalog_entry(model_id: str, entry: dict) -> str | None:
    """Mandatory fields per spec Section 5: provider, runtimes (non-empty dict), source,
    confidence, last_verified -- checked for PRESENCE and TYPE (last_verified additionally
    checked for YYYY-MM-DD shape). Every optional field IS type-checked when present (a
    missing optional field is never a validation failure -- only a reduced ranking signal
    later, model_ranker.py); a present-but-wrong-typed one is. Every `runtimes` value's own
    `model_id`/`ctx_window` sub-fields are type-checked too when present, not just the
    top-level "is it a dict" shape check."""
    for validator in _CATALOG_ENTRY_VALIDATORS:
        reason = validator(model_id, entry)
        if reason:
            return reason
    return None


def merge_catalog_entry(catalog: dict, model_id: str, entry: dict) -> tuple:
    """Returns (new_catalog, rejection_reason). Never mutates `catalog`. An invalid entry is
    rejected and reported (spec Section 8: "that single entry is rejected and reported; the
    rest of the write proceeds") -- the caller (fetch-model-catalog, Task 7) collects
    rejections across a whole discovery run and reports them together, never aborting.
    `runtimes` is MERGED into any existing entry at this key, never replaced wholesale --
    this is what lets two different CLIs' runtime mappings for the same real model coexist
    under one canonical key (HIGH finding: catalog identity must not lose runtime mappings)."""
    if model_id == CATALOG_META_KEY:
        return catalog, f"{model_id}: reserved catalog key, not a model id"
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
