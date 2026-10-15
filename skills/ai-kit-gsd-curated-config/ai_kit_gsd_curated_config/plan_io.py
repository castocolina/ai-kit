"""Inventory validation, canonical plan JSON and the atomic plan write.

`load_inventory` is the only file `recommend`'s CLI path reads; `write_plan` is the
only file it writes (mkstemp + os.replace through the shared `ai_kit_spec.cache`
writer, so a reader never sees a partial plan.json). The pure `recommend.build_plan`
performs no I/O itself (REC-01).
"""
import hashlib
import json

from . import gsd_catalog

INVENTORY_SCHEMA_VERSION = 1
PLAN_SCHEMA_VERSION = 1

_ERROR_SUFFIX = "; rerun inventory"


def canonical_json(obj) -> str:
    """The byte-stable serialization every plan.json is written with."""
    return json.dumps(obj, sort_keys=True, indent=2, ensure_ascii=False) + "\n"


def inventory_digest(inventory: dict) -> str:
    """`sha256:` over the compact, sorted inventory JSON (REC-01's input fingerprint)."""
    compact = json.dumps(inventory, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return "sha256:" + hashlib.sha256(compact.encode("utf-8")).hexdigest()


def _missing(inv: dict, key: str) -> str | None:
    if key not in inv:
        return f"missing key: {key}"
    return None


def _type_of(value) -> str:
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, str):
        return "str"
    if isinstance(value, list):
        return "list"
    if isinstance(value, dict):
        return "dict"
    return type(value).__name__


def _ill(inv: dict, key: str, expected: str) -> str | None:
    """Type-checks `inv[key]` against `expected` ("int", "str", "list", "dict" or
    "str-or-null"), never treating a bool as an int/str."""
    value = inv.get(key)
    if expected == "str-or-null":
        if value is None or isinstance(value, str):
            return None
        return f"key {key}: expected str or null, got {_type_of(value)}"
    if expected in ("int", "str") and isinstance(value, bool):
        return f"key {key}: expected {expected}, got bool"
    if not isinstance(value, {"int": int, "str": str, "list": list, "dict": dict}[expected]):
        return f"key {key}: expected {expected}, got {_type_of(value)}"
    return None


def _validate_inventory(inv) -> str | None:
    """Returns the problem string, or `None` when the document matches the
    schema-version-1 contract (17-02-PLAN `<interfaces>`)."""
    if not isinstance(inv, dict):
        return "top-level JSON is not an object"
    schema_version = inv.get("schema_version")
    if isinstance(schema_version, bool) or not isinstance(schema_version, int):
        return f"schema_version {schema_version!r} unsupported (expected 1)"
    if schema_version != INVENTORY_SCHEMA_VERSION:
        return f"schema_version {schema_version} unsupported (expected 1)"
    for problem in (
        _ill(inv, "host", "str") or _missing(inv, "host"),
        _ill(inv, "candidates", "list") or _missing(inv, "candidates"),
        _ill(inv, "project", "dict") or _missing(inv, "project"),
        _ill(inv, "existing_config", "dict") or _missing(inv, "existing_config"),
        _ill(inv, "global_defaults", "dict") or _missing(inv, "global_defaults"),
        _ill(inv, "conflicts", "list") or _missing(inv, "conflicts"),
        _validate_gsd_core(inv.get("gsd_core")) if isinstance(inv.get("gsd_core"), dict)
        else (_missing(inv, "gsd_core") or _ill(inv, "gsd_core", "dict")),
        _validate_project(inv.get("project")) if isinstance(inv.get("project"), dict) else None,
        _validate_config_section(inv.get("existing_config"), "existing_config")
        if isinstance(inv.get("existing_config"), dict) else None,
        _validate_candidates(inv.get("candidates")) if isinstance(inv.get("candidates"), list)
        else None,
    ):
        if problem:
            return problem
    if not isinstance(inv["global_defaults"].get("values"), dict):
        return "key global_defaults.values: expected dict"
    return None


def _validate_gsd_core(gsd_core: dict) -> str | None:
    for key in ("runtime_profile_map", "model_profiles", "agent_to_phase_type", "valid_keys"):
        if not isinstance(gsd_core.get(key), dict):
            return f"key gsd_core.{key}: expected dict"
    valid_keys = gsd_core["valid_keys"]
    for key in ("accepted", "rejected"):
        if not isinstance(valid_keys.get(key), list):
            return f"key gsd_core.valid_keys.{key}: expected list"
    for key in ("path", "scope"):
        value = gsd_core.get(key)
        if value is not None and not isinstance(value, str):
            return f"key gsd_core.{key}: expected str or null"
    version = gsd_core.get("version")
    if version is not None and not isinstance(version, str):
        return "key gsd_core.version: expected str or null"
    return None


def _validate_project(project: dict) -> str | None:
    for key in ("frontend", "intel_index_present"):
        if not isinstance(project.get(key), bool):
            return f"key project.{key}: expected bool"
    return None


def _validate_config_section(section: dict, name: str) -> str | None:
    if not isinstance(section.get("exists"), bool):
        return f"key {name}.exists: expected bool"
    if not isinstance(section.get("values"), dict):
        return f"key {name}.values: expected dict"
    return None


def _validate_candidates(candidates: list) -> str | None:
    for index, cand in enumerate(candidates):
        if not isinstance(cand, dict):
            return f"candidates[{index}]: expected an object"
        for key in ("runtime", "model"):
            if not isinstance(cand.get(key), str):
                return f"candidates[{index}].{key}: expected str"
        if not isinstance(cand.get("is_host"), bool):
            return f"candidates[{index}].is_host: expected bool"
    return None


def load_inventory(path: str) -> tuple[dict | None, str | None]:
    """Reads and validates the inventory JSON. Returns `(inventory, None)` on
    success, else `(None, "<one-line error>; rerun inventory")`. This is the only
    file the recommend CLI path reads."""
    try:
        with open(path, encoding="utf-8") as handle:
            inventory = json.load(handle)
    except OSError as exc:
        reason = exc.strerror or "unreadable"
        return None, f"inventory {path}: cannot read ({reason}){_ERROR_SUFFIX}"
    except json.JSONDecodeError:
        return None, f"inventory {path}: invalid JSON{_ERROR_SUFFIX}"
    problem = _validate_inventory(inventory)
    if problem:
        return None, f"inventory {path}: {problem}{_ERROR_SUFFIX}"
    return inventory, None


def write_plan(path: str, plan: dict) -> None:
    """Writes `canonical_json(plan)` atomically (mkstemp + os.replace) through the
    shared `ai_kit_spec.cache` writer. Raises `OSError` when the ai-kit-spec-review
    sibling is not installed."""
    cache = gsd_catalog.load_ai_kit_spec_module("cache")
    if cache is None:
        raise OSError("ai-kit-spec-review sibling (ai_kit_spec) not installed")
    cache.cache_write_text(path, canonical_json(plan))
