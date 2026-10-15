"""Inventory validation, the `--out` guard and the atomic plan write (canonical JSON and
the digest live in the pure `plan_schema`; `canonical_json` is re-exported here).

`load_inventory` is the only file `recommend`'s CLI path reads; `write_plan` is the
only file it writes (mkstemp + os.replace through the shared `ai_kit_spec.cache`
writer, so a reader never sees a partial plan.json). The pure `recommend.build_plan`
performs no I/O itself (REC-01).
"""
import json
import os

from . import gsd_catalog
from .plan_schema import canonical_json

INVENTORY_SCHEMA_VERSION = 2

_ERROR_SUFFIX = "; rerun inventory"


def _missing(inv: dict, key: str) -> str | None:
    if key not in inv:
        return f"missing key: {key}"
    return None


def _ill(inv: dict, key: str, expected: type) -> str | None:
    value = inv.get(key)
    if isinstance(value, expected):
        return None
    return f"key {key}: expected {expected.__name__}, got {type(value).__name__}"


def _schema_version_problem(inv: dict) -> str | None:
    schema_version = inv.get("schema_version")
    # A bool or a float 1.0 compares equal to 1 but is not schema version 1.
    exact_int = isinstance(schema_version, int) and not isinstance(schema_version, bool)
    if not exact_int or schema_version != INVENTORY_SCHEMA_VERSION:
        return (
            f"schema_version {schema_version!r} unsupported "
            f"(expected {INVENTORY_SCHEMA_VERSION})"
        )
    return None


def _validate_inventory(inv) -> str | None:
    """Returns the problem string, or `None` when the document matches the
    schema-version-2 contract (18-02)."""
    if not isinstance(inv, dict):
        return "top-level JSON is not an object"
    problem = _schema_version_problem(inv)
    if problem:
        return problem
    for key, expected in (
        ("host", str),
        ("gsd_core", dict),
        ("candidates", list),
        ("project", dict),
        ("existing_config", dict),
        ("global_defaults", dict),
        ("conflicts", list),
        ("installed_runtimes", list),
    ):
        problem = _missing(inv, key) or _ill(inv, key, expected)
        if problem:
            return problem
    for problem in (
        _validate_gsd_core(inv["gsd_core"]),
        _validate_project(inv["project"]),
        _validate_config_section(inv["existing_config"], "existing_config"),
        _validate_candidates(inv["candidates"]),
        _validate_conflicts(inv["conflicts"]),
    ):
        if problem:
            return problem
    tail = _validate_inventory_tail(inv)
    return tail


def _validate_inventory_tail(inv: dict) -> str | None:
    if not isinstance(inv["global_defaults"].get("values"), dict):
        return "key global_defaults.values: expected dict"
    runtimes = inv["installed_runtimes"]
    if not all(isinstance(name, str) for name in runtimes):
        return "key installed_runtimes: expected list of str"
    return None


def _lane_field_problem(lane: dict, index: int) -> str | None:
    if not isinstance(lane, dict):
        return f"key gsd_core.review_lanes[{index}]: expected dict"
    for key in ("slug", "transport", "binary", "model_key", "effort_key", "default_effort"):
        if key not in lane:
            return f"key gsd_core.review_lanes[{index}]: missing {key}"
    slug = lane["slug"]
    if not isinstance(slug, str):
        return f"key gsd_core.review_lanes[{index}].slug: expected str"
    for key in ("transport", "binary", "model_key", "effort_key", "default_effort"):
        val = lane[key]
        if val is not None and not isinstance(val, str):
            return f"key gsd_core.review_lanes[{index}].{key}: expected str or null"
    return None


def _validate_review_lanes(lanes) -> str | None:
    if not isinstance(lanes, list):
        return "key gsd_core.review_lanes: expected list"
    for index, lane in enumerate(lanes):
        problem = _lane_field_problem(lane, index)
        if problem:
            return problem
    return None


def _validate_skills_roots(roots) -> str | None:
    if not isinstance(roots, dict):
        return "key gsd_core.skills_roots: expected dict"
    for key, val in roots.items():
        if not isinstance(key, str):
            return "key gsd_core.skills_roots: expected str keys"
        if val is not None and not isinstance(val, str):
            return f"key gsd_core.skills_roots.{key}: expected str or null"
    return None


def _validate_gsd_core_tables(gsd_core: dict) -> str | None:
    for key in ("runtime_profile_map", "model_profiles", "agent_to_phase_type", "valid_keys"):
        if not isinstance(gsd_core.get(key), dict):
            return f"key gsd_core.{key}: expected dict"
    valid_keys = gsd_core["valid_keys"]
    for key in ("accepted", "rejected"):
        if not isinstance(valid_keys.get(key), list):
            return f"key gsd_core.valid_keys.{key}: expected list"
    return _model_profiles_problem(gsd_core["model_profiles"])


def _validate_gsd_core(gsd_core: dict) -> str | None:
    for problem in (
        _validate_gsd_core_tables(gsd_core),
        _validate_review_lanes(gsd_core.get("review_lanes")),
        _validate_skills_roots(gsd_core.get("skills_roots")),
        _gsd_core_meta_problem(gsd_core),
    ):
        if problem:
            return problem
    return None


def _gsd_core_meta_problem(gsd_core: dict) -> str | None:
    for key in ("path", "scope", "version"):
        value = gsd_core.get(key)
        if value is not None and not isinstance(value, str):
            return f"key gsd_core.{key}: expected str or null"
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
    return inventory, None


def out_path_problem(out: str, inventory_path: str, inventory: dict) -> str | None:
    """SPEC must-not: `--out` never replaces the inventory, a GSD config file or anything
    under the project's `.planning/` (the config's own dir when it is not inside one).
    Returns the refusal reason."""
    target = os.path.realpath(out)
    protected = [os.path.realpath(inventory_path)]
    for section in ("existing_config", "global_defaults"):
        path = inventory[section].get("path")
        if isinstance(path, str):
            protected.append(os.path.realpath(path))
    if target in protected:
        return f"--out {out} would overwrite an input or GSD config file"
    config_path = inventory["existing_config"].get("path")
    if isinstance(config_path, str):
        guarded = _planning_root(os.path.realpath(os.path.dirname(config_path)))
        if target.startswith(guarded + os.sep):
            return f"--out {out} is inside the project's GSD dir {guarded}"
    return None


def _planning_root(config_dir: str) -> str:
    """The nearest `.planning` ancestor of the config dir (a workstream config sits at
    `.planning/workstreams/<ws>/`), else the config dir itself."""
    probe = config_dir
    while os.path.basename(probe) != ".planning":
        parent = os.path.dirname(probe)
        if parent == probe:
            return config_dir
        probe = parent
    return probe


def write_plan(path: str, plan: dict) -> None:
    """Writes `canonical_json(plan)` atomically (mkstemp + os.replace) through the
    shared `ai_kit_spec.cache` writer, with the umask-derived mode a plain `open()` would
    give. Raises `OSError` when the parent directory is missing (never created) or the
    ai-kit-spec-review sibling is not installed."""
    cache = gsd_catalog.load_ai_kit_spec_module("cache")
    if cache is None:
        raise OSError(gsd_catalog.SIBLING_MISSING)
    # abspath: a bare `plan.json` has dirname "" and the shared writer's makedirs("") fails.
    target = os.path.abspath(path)
    parent = os.path.dirname(target)
    if not os.path.isdir(parent):
        raise FileNotFoundError(f"directory {parent} does not exist")
    # Reading the umask means setting it; safe here because the CLI is single-threaded.
    umask = os.umask(0)
    os.umask(umask)
    cache.cache_write_text(target, canonical_json(plan), mode=0o666 & ~umask)
