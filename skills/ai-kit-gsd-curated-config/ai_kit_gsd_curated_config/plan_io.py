"""Inventory validation, canonical plan JSON and the atomic plan write.

`load_inventory` is the only file `recommend`'s CLI path reads; `write_plan` is the
only file it writes (mkstemp + os.replace through the shared `ai_kit_spec.cache`
writer, so a reader never sees a partial plan.json). The pure `recommend.build_plan`
performs no I/O itself (REC-01).
"""
import json

from . import gsd_catalog
from .plan_schema import canonical_json

INVENTORY_SCHEMA_VERSION = 1

_ERROR_SUFFIX = "; rerun inventory"


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



def _schema_version_problem(inv: dict) -> str | None:
    schema_version = inv.get("schema_version")
    if isinstance(schema_version, bool) or not isinstance(schema_version, int):
        return f"schema_version {schema_version!r} unsupported (expected 1)"
    if schema_version != INVENTORY_SCHEMA_VERSION:
        return f"schema_version {schema_version} unsupported (expected 1)"
    return None


def _validate_inventory(inv) -> str | None:
    """Returns the problem string, or `None` when the document matches the
    schema-version-1 contract (17-02-PLAN `<interfaces>`)."""
    if not isinstance(inv, dict):
        return "top-level JSON is not an object"
    problem = _schema_version_problem(inv)
    if problem:
        return problem
    for key, expected in (
        ("host", "str"),
        ("gsd_core", "dict"),
        ("candidates", "list"),
        ("project", "dict"),
        ("existing_config", "dict"),
        ("global_defaults", "dict"),
        ("conflicts", "list"),
    ):
        problem = _missing(inv, key) or _ill(inv, key, expected)
        if problem:
            return problem
    for problem in (
        _validate_gsd_core(inv["gsd_core"]),
        _validate_project(inv["project"]),
        _validate_config_section(inv["existing_config"], "existing_config"),
        _validate_candidates(inv["candidates"]),
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
    problem = _model_profiles_problem(gsd_core["model_profiles"])
    if problem:
        return problem
    for key in ("path", "scope"):
        value = gsd_core.get(key)
        if value is not None and not isinstance(value, str):
            return f"key gsd_core.{key}: expected str or null"
    version = gsd_core.get("version")
    if version is not None and not isinstance(version, str):
        return "key gsd_core.version: expected str or null"
    return None


def _model_profiles_problem(profiles: dict) -> str | None:
    if not all(
        isinstance(column, dict) and all(isinstance(t, str) for t in column.values())
        for column in profiles.values()
    ):
        return "key gsd_core.model_profiles: expected profile -> {agent: tier}"
    # The balanced column is gsd-core's fallback; its absence means an agent-first table.
    if "balanced" not in profiles:
        return "key gsd_core.model_profiles: no balanced profile column"
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


def _conflict_item_problem(item, index: int) -> str | None:
    well_formed = (
        isinstance(item, dict)
        and isinstance(item.get("kind"), str)
        and isinstance(item.get("key"), str)
        and isinstance(item.get("why"), str)
        and item.get("scope") in ("project", "global")
        and isinstance(item.get("effect", ""), str)
        and (item["kind"] != "model_policy" or isinstance(item.get("value"), dict))
    )
    return None if well_formed else f"conflicts[{index}] malformed"


def _validate_conflicts(conflicts: list) -> str | None:
    for index, item in enumerate(conflicts):
        problem = _conflict_item_problem(item, index)
        if problem:
            return problem
    return None


def _is_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


# Every candidate field `recommend` reads: (name, check, required, expected-type label).
_CANDIDATE_FIELDS = (
    ("runtime", lambda v: isinstance(v, str), True, "str"),
    ("model", lambda v: isinstance(v, str), True, "str"),
    ("family", lambda v: isinstance(v, str), True, "str"),
    ("is_host", lambda v: isinstance(v, bool), True, "bool"),
    ("is_router", lambda v: isinstance(v, bool), True, "bool"),
    ("score_axes", lambda v: isinstance(v, int) and not isinstance(v, bool), True, "int"),
    (
        "purpose_scores",
        lambda v: isinstance(v, dict) and all(_is_number(x) for x in v.values()),
        True,
        "dict of number",
    ),
    ("price", lambda v: v is None or _is_number(v), True, "number or null"),
    ("fast_twin_of", lambda v: v is None or isinstance(v, str), True, "str or null"),
    ("vendor", lambda v: v is None or isinstance(v, str), False, "str or null"),
    ("image_input", lambda v: v is None or isinstance(v, bool), False, "bool or null"),
    ("reasoning_modes", lambda v: isinstance(v, list), False, "list"),
    ("router_confirmed", lambda v: isinstance(v, bool), False, "bool"),
    ("name_declared_purpose", lambda v: v is None or isinstance(v, str), False, "str or null"),
)


def _candidate_problem(cand, index: int) -> str | None:
    if not isinstance(cand, dict):
        return f"candidates[{index}]: expected an object"
    for name, check, required, label in _CANDIDATE_FIELDS:
        if name not in cand:
            if required:
                return f"candidates[{index}].{name}: missing"
            continue
        if not check(cand[name]):
            return f"candidates[{index}].{name}: expected {label}"
    return None


def _validate_candidates(candidates: list) -> str | None:
    for index, cand in enumerate(candidates):
        problem = _candidate_problem(cand, index)
        if problem:
            return problem
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
    except ValueError:  # JSONDecodeError and UnicodeDecodeError
        return None, f"inventory {path}: invalid JSON{_ERROR_SUFFIX}"
    problem = _validate_inventory(inventory)
    if problem:
        return None, f"inventory {path}: {problem}{_ERROR_SUFFIX}"
    problem = _validate_conflicts(inventory["conflicts"])
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
