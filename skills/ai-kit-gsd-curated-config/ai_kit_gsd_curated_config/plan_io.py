"""Inventory validation, the `--out` guard and the atomic plan write (canonical JSON and
the digest live in the pure `plan_schema`; `canonical_json` is re-exported here).

`load_inventory` is the only file `recommend`'s CLI path reads; `write_plan` is the
only file it writes (mkstemp + os.replace through the shared `ai_kit_spec.cache`
writer, so a reader never sees a partial plan.json). The pure `recommend.build_plan`
performs no I/O itself (REC-01).
"""
import json
import os
import posixpath
import re

from . import cross_ai, gsd_catalog, host, presets
from . import skills as skills_mod
from .plan_schema import PLAN_SCHEMA_VERSION, canonical_json, inventory_digest

_AFFINITY_SUFFIX = "; fix skill_affinity.json"
_PKG_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AFFINITY_PATH = os.path.join(_PKG_ROOT, "skill_affinity.json")

INVENTORY_SCHEMA_VERSION = 2

_ERROR_SUFFIX = "; rerun inventory"


def read_json_object(path: str) -> tuple[dict | None, str | None]:
    if not os.path.isfile(path):
        return None, None
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError, RecursionError):
        return None, f"{path} unreadable; ignored"
    if not isinstance(data, dict):
        return None, f"{path} unreadable; ignored"
    return data, None


def same_value(a, b) -> bool:
    """JSON equality: Python's ``0 == False`` would hide a retype gsd-core sees (IN-07)."""
    return json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


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


def _skill_entry_problem(entry, index: int) -> str | None:
    if not isinstance(entry, dict):
        return f"key skills[{index}]: expected dict"
    for key, expected in (
        ("name", str),
        ("root_kind", str),
        ("escapes_root", bool),
        ("addressable", bool),
    ):
        val = entry.get(key)
        if not isinstance(val, expected):
            return f"key skills[{index}].{key}: expected {expected.__name__}"
    return None


def _validate_skills(rows) -> str | None:
    if not isinstance(rows, list):
        return "key skills: expected list"
    for index, entry in enumerate(rows):
        problem = _skill_entry_problem(entry, index)
        if problem:
            return problem
    return None


def _validate_system_one_backend(backend) -> str | None:
    if not isinstance(backend, dict):
        return "key system_one_backend: expected dict"
    if not isinstance(backend.get("detected"), bool):
        return "key system_one_backend.detected: expected bool"
    via = backend.get("via")
    if not isinstance(via, list) or not all(isinstance(item, str) for item in via):
        return "key system_one_backend.via: expected list of str"
    return None


def _validate_ponytail_visibility(pvisibility) -> str | None:
    if not isinstance(pvisibility, dict):
        return "key ponytail_visibility: expected dict"
    for host_name in host.HOSTS:
        names = pvisibility.get(host_name)
        if not isinstance(names, list) or not all(isinstance(n, str) for n in names):
            return f"key ponytail_visibility.{host_name}: expected list of str"
    return None


def _validate_inventory_tail(inv: dict) -> str | None:
    if not isinstance(inv["global_defaults"].get("values"), dict):
        return "key global_defaults.values: expected dict"
    runtimes = inv["installed_runtimes"]
    if not all(isinstance(name, str) for name in runtimes):
        return "key installed_runtimes: expected list of str"
    for problem in (
        _missing(inv, "skills") or _validate_skills(inv.get("skills")),
        _missing(inv, "ponytail_visibility") or _validate_ponytail_visibility(
            inv.get("ponytail_visibility")
        ),
        _missing(inv, "system_one_backend") or _validate_system_one_backend(
            inv.get("system_one_backend")
        ),
    ):
        if problem:
            return problem
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


def load_affinity(path: str) -> tuple[dict | None, str | None]:
    """Reads and validates ``skill_affinity.json``. Returns ``(doc, None)`` or an error."""
    try:
        with open(path, encoding="utf-8") as handle:
            doc = json.load(handle)
    except OSError as exc:
        reason = exc.strerror or "unreadable"
        return None, f"skill_affinity {path}: cannot read ({reason}){_AFFINITY_SUFFIX}"
    except ValueError:
        return None, f"skill_affinity {path}: invalid JSON{_AFFINITY_SUFFIX}"
    problem = skills_mod.validate_affinity(doc)
    if problem:
        return None, f"skill_affinity {path}: {problem}{_AFFINITY_SUFFIX}"
    return doc, None


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
    cache.cache_write_text(target, canonical_json(plan), mode=cache.umask_file_mode())


_PLAN_ERROR_SUFFIX = "; rerun recommend"
_SKILL_NAME = re.compile(r"^[A-Za-z0-9_-]+$")


def sibling_inventory_path(plan_path: str) -> str:
    """``inventory.json`` beside ``plan.json``."""
    return os.path.join(os.path.dirname(os.path.abspath(plan_path)), "inventory.json")


def load_plan(path: str) -> tuple[dict | None, str | None]:
    """Read and validate a schema-2 plan. Returns ``(plan, None)`` or ``(None, error)``."""
    try:
        with open(path, encoding="utf-8") as handle:
            plan = json.load(handle)
    except OSError as exc:
        reason = exc.strerror or "unreadable"
        return None, f"plan {path}: cannot read ({reason}){_PLAN_ERROR_SUFFIX}"
    except ValueError:
        return None, f"plan {path}: invalid JSON{_PLAN_ERROR_SUFFIX}"
    if not isinstance(plan, dict):
        return None, f"plan {path}: top-level JSON is not an object{_PLAN_ERROR_SUFFIX}"
    problem = _plan_envelope_problem(plan)
    if problem:
        return None, f"plan {path}: {problem}{_PLAN_ERROR_SUFFIX}"
    problem = validate_plan(plan)
    if problem:
        return None, f"plan {path}: {problem}{_PLAN_ERROR_SUFFIX}"
    return plan, None


def load_plan_and_inventory(
    plan_path: str, inv_path: str
) -> tuple[dict | None, dict | None, str | None]:
    """Both documents, bound by the inventory digest (D-17, D-42) and the plan fields the
    digest does not cover; ``(plan, inv, None)`` or ``(None, None, error)``."""
    plan, error = load_plan(plan_path)
    if plan is None:
        return None, None, error
    inv, error = load_inventory(inv_path)
    if inv is None:
        return None, None, error
    digest = inventory_digest(inv)
    if plan.get("inventory_digest") != digest:
        return None, None, (
            "inventory digest does not match the plan's inventory_digest "
            f"(plan {plan['inventory_digest']!r}, inventory {digest!r})"
        )
    problem = check_plan_inventory(plan, inv)
    if problem:
        return None, None, problem
    return plan, inv, None


def check_plan_inventory(plan: dict, inv: dict) -> str | None:
    """The plan's host and trusted-roots ``existing`` must match the inventory (review cycle 3);
    the digest binds the plan to the inventory, not these plan fields."""
    if plan.get("host") != inv.get("host"):
        return (
            f"plan host {plan.get('host')!r} does not match the inventory host "
            f"{inv.get('host')!r}; rerun recommend"
        )
    key = "agent_skills_security.trusted_global_roots"
    for entry in plan.get("entries") or []:
        if entry.get("key") != key:
            continue
        inv_val = presets.get_dotted(inv["existing_config"]["values"], key)
        if entry.get("existing") != inv_val:
            return f"{key}: the plan's existing value is not the inventory's; rerun recommend"
    return None


def entry_effective_value(entry: dict | None):
    """Effective config value: ``set`` uses ``value``, ``keep`` uses ``existing``."""
    if entry is None:
        return None
    op = entry.get("op")
    if op == "set":
        return entry.get("value")
    if op == "keep":
        return entry.get("existing")
    return None


def execution_effective_on(plan: dict) -> bool:
    entry = _plan_entry(plan, "workflow.cross_ai_execution")
    return entry_effective_value(entry) is True


def _plan_entry(plan: dict, key: str) -> dict | None:
    for entry in plan.get("entries") or []:
        if entry.get("key") == key:
            return entry
    return None


def validate_plan(plan: dict) -> str | None:
    """Shared executable-schema and policy validator; first problem or ``None``."""
    plan_host = plan.get("host")
    if plan_host not in host.HOSTS:
        return f"host {plan_host!r} is not supported"
    problem = _validate_entries(plan.get("entries"))
    if problem:
        return problem
    problem = _validate_artifacts(plan.get("artifacts"), plan_host)
    if problem:
        return problem
    problem = _host_reviewer_problem(plan, plan_host)
    if problem:
        return problem
    return _validate_execution_coupling(plan)


def _host_reviewer_problem(plan: dict, plan_host: str) -> str | None:
    """SPEC R2 must-not: the host CLI never reviews its own plans, even with --force."""
    entry = _plan_entry(plan, "review.default_reviewers")
    if entry is None or entry.get("op") != "set":
        return None
    value = entry.get("value")
    if isinstance(value, list) and plan_host in value:
        return f"review.default_reviewers: {plan_host!r} is the host CLI, not a review lane"
    return None


def _validate_execution_coupling(plan: dict) -> str | None:
    exec_on = execution_effective_on(plan)
    artifacts = plan.get("artifacts") or []
    if not exec_on:
        if artifacts:
            return "a cross-AI script artifact needs workflow.cross_ai_execution on"
        return None
    cmd_entry = _plan_entry(plan, "workflow.cross_ai_command")
    cmd_val = entry_effective_value(cmd_entry)
    ok_cmd = cmd_entry is not None and (
        cmd_entry.get("status") == "needs_choice"
        or cmd_entry.get("forced")
        or cmd_val == cross_ai.CROSS_AI_COMMAND
    )
    if not ok_cmd:
        return (
            "workflow.cross_ai_command is required while "
            "workflow.cross_ai_execution is on"
        )
    if cmd_val != cross_ai.CROSS_AI_COMMAND:
        return None
    if len(artifacts) != 1:
        return (
            "the cross-AI script artifact must exist while "
            "workflow.cross_ai_command runs it; rerun recommend"
        )
    return _validate_runner_timeout(plan)


def timeout_problem(label: str, value) -> str | None:
    """The one runner-timeout rule (PT-07): an int, not a bool, at least MIN_TIMEOUT_S."""
    floor = cross_ai.MIN_TIMEOUT_S
    if isinstance(value, int) and not isinstance(value, bool) and value >= floor:
        return None
    return f"{label} must be an integer >= {floor} (got {value!r})"


def _validate_runner_timeout(plan: dict) -> str | None:
    timeout_entry = _plan_entry(plan, "workflow.cross_ai_timeout")
    return timeout_problem("workflow.cross_ai_timeout", entry_effective_value(timeout_entry))


def _plan_envelope_problem(plan: dict) -> str | None:
    schema_version = plan.get("schema_version")
    exact = isinstance(schema_version, int) and not isinstance(schema_version, bool)
    if not exact or schema_version != PLAN_SCHEMA_VERSION:
        return (
            f"schema_version {schema_version!r} unsupported (expected {PLAN_SCHEMA_VERSION})"
        )
    for key in ("host", "profile", "rigor", "inventory_digest"):
        if not isinstance(plan.get(key), str):
            return f"key {key}: expected str"
    for key in ("entries", "notes", "artifacts"):
        if not isinstance(plan.get(key), list):
            return f"key {key}: expected list"
    return None


def _validate_entries(entries) -> str | None:
    if not isinstance(entries, list):
        return "key entries: expected list"
    seen: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict):
            return "entries: expected list of objects"
        key = entry.get("key")
        if not isinstance(key, str) or not key:
            return "entry key: expected non-empty str"
        if key in seen:
            return f"duplicate entry key: {key}"
        seen.add(key)
        problem = _validate_one_entry(entry)
        if problem:
            return problem
    return None


def _validate_one_entry(entry: dict) -> str | None:
    key = entry["key"]
    op = entry.get("op")
    status = entry.get("status")
    problem = _entry_shape_problem(key, op, status, entry)
    if problem:
        return problem
    if op == "keep":
        existing = entry.get("existing")
        if existing is not None and entry.get("value") != existing:
            return f"{key}: keep value must equal existing"
    value = entry.get("value")
    if op == "set" and value is not None and status != "needs_choice":
        return _validate_entry_value(key, value, entry)
    return None


def _entry_shape_problem(key: str, op, status, entry: dict) -> str | None:
    if op not in ("set", "unset", "keep"):
        return f"{key}: op must be set, unset or keep"
    if status is not None and status != "needs_choice":
        return f"{key}: status must be absent or needs_choice"
    if "candidates" in entry and not isinstance(entry["candidates"], list):
        return f"{key}: candidates must be a list"
    if op == "set" and "value" not in entry:
        return f"{key}: set entry missing value"
    if op == "set" and entry.get("value") is None and status != "needs_choice":
        return f"{key}: set entry value may be None only with needs_choice"
    return None


def _validate_entry_value(key: str, value, entry: dict) -> str | None:
    if key == "workflow.cross_ai_timeout":
        problem = timeout_problem(key, value)
        if problem:
            return problem
    if (
        key == "workflow.cross_ai_command"
        and value != cross_ai.CROSS_AI_COMMAND
        and not entry.get("forced")
    ):
        return f"{key}: must be {cross_ai.CROSS_AI_COMMAND!r} unless forced"
    if key == "agent_skills_security.trusted_global_roots":
        return _validate_trusted_roots(key, value, entry)
    if key.startswith("agent_skills."):
        return _validate_agent_skills(key, value)
    return None


def home_relative_root(root: str) -> bool:
    """``~/<sub>`` that stays strictly inside $HOME once normalized: gsd-core joins the rest
    onto the home dir, so ``~/..`` would widen the trusted roots outside it."""
    if not root.startswith("~/"):
        return False
    rest = posixpath.normpath(root[2:])
    return rest not in (".", "..", "/") and not rest.startswith(("../", "/"))


def _validate_trusted_roots(key: str, value, entry: dict) -> str | None:
    if not isinstance(value, list) or not all(isinstance(x, str) for x in value):
        return f"{key}: expected list of str"
    existing = entry.get("existing")
    existing_list = existing if isinstance(existing, list) else []
    for element in value:
        if element in existing_list or home_relative_root(element):
            continue
        return (
            f"{key}: trusted root {element!r} must be ~/-relative inside $HOME "
            "unless already configured"
        )
    dropped = [root for root in existing_list if root not in value]
    if dropped and not entry.get("forced"):
        return f"{key}: drops already-configured root(s) {dropped!r} without --force"
    return None


def _validate_agent_skills(key: str, value) -> str | None:
    if not isinstance(value, list) or not all(isinstance(x, str) for x in value):
        return f"{key}: expected list of str"
    for name in value:
        if not _SKILL_NAME.fullmatch(name):
            return f"{key}: skill name {name!r} is invalid"
    return None


def _validate_artifacts(artifacts, plan_host: str) -> str | None:
    if not isinstance(artifacts, list):
        return "key artifacts: expected list"
    if len(artifacts) > 1:
        return "artifacts: at most one cross-ai-script artifact"
    if not artifacts:
        return None
    return _validate_artifact_doc(artifacts[0], plan_host)


def _validate_artifact_doc(art, plan_host: str) -> str | None:
    if not isinstance(art, dict):
        return "artifacts[0]: expected object"
    shell = (
        (art.get("kind") != "cross-ai-script", "artifacts[0].kind: must be cross-ai-script"),
        (
            art.get("path") != cross_ai.SCRIPT_PATH,
            f"artifacts[0].path: must be {cross_ai.SCRIPT_PATH!r} (got {art.get('path')!r})",
        ),
        (
            art.get("template") != cross_ai.TEMPLATE_NAME,
            f"artifacts[0].template: must be {cross_ai.TEMPLATE_NAME!r}",
        ),
    )
    for bad, message in shell:
        if bad:
            return message
    version = art.get("version")
    if not isinstance(version, int) or isinstance(version, bool):
        return "artifacts[0].version: expected int"
    return _validate_artifact_config(
        art.get("config"), art.get("choices"), art.get("status"), plan_host
    )


def _validate_artifact_config(config, choices, status, plan_host: str) -> str | None:
    if not isinstance(config, dict):
        return "artifacts[0].config: expected object"
    prefer = config.get("prefer")
    problem = _validate_prefer(prefer, plan_host)
    if problem or not isinstance(prefer, list):
        return problem
    problem = _validate_outer_timeout(config.get("outer_timeout_s"))
    if problem:
        return problem
    models = config.get("models")
    router = config.get("router_backed")
    if not isinstance(models, dict):
        return "artifacts[0].config.models: expected object"
    if not isinstance(router, dict):
        return "artifacts[0].config.router_backed: expected object"
    choice_map = choices if isinstance(choices, dict) else {}
    return _validate_artifact_targets(prefer, models, router, choice_map, status)


def _validate_prefer(prefer, plan_host: str) -> str | None:
    if not isinstance(prefer, list) or not prefer or not all(isinstance(x, str) for x in prefer):
        return "artifacts[0].config.prefer: expected non-empty list of str"
    if len(set(prefer)) != len(prefer):
        return "artifacts[0].config.prefer: ids must be unique"
    for runner_id in prefer:
        if runner_id not in cross_ai.RUNNER_CLI:
            return f"artifacts[0].config.prefer: unknown id {runner_id!r}"
        if runner_id == plan_host:
            return f"artifacts[0].config.prefer: must not include plan host {plan_host!r}"
    return None


def _validate_outer_timeout(timeout) -> str | None:
    return timeout_problem("artifacts[0].config.outer_timeout_s", timeout)


def _validate_artifact_targets(prefer, models, router, choices, status) -> str | None:
    for runner_id, model in models.items():
        problem = _model_row_problem(prefer, runner_id, model)
        if problem:
            return problem
    for runner_id in choices:
        problem = _choice_row_problem(prefer, runner_id, models, choices[runner_id])
        if problem:
            return problem
    for runner_id in router:
        if runner_id not in models:
            return f"artifacts[0].config.router_backed: id {runner_id!r} has no model"
    for runner_id in prefer:
        if (runner_id in models) == (runner_id in choices):
            return (
                f"artifacts[0]: prefer id {runner_id!r} must be in exactly one of "
                "models and choices"
            )
    want_status = "needs_choice" if choices else "ok"
    if status != want_status:
        return f"artifacts[0].status: expected {want_status!r} (got {status!r})"
    return None


def _model_row_problem(prefer, runner_id: str, model) -> str | None:
    if runner_id not in prefer:
        return f"artifacts[0].config.models: id {runner_id!r} not in prefer"
    if not isinstance(model, str) or not model:
        return f"artifacts[0].config.models.{runner_id}: expected non-empty str"
    return None


def _choice_row_problem(prefer, runner_id: str, models, row) -> str | None:
    if runner_id not in prefer:
        return f"artifacts[0].choices: id {runner_id!r} not in prefer"
    if runner_id in models:
        return f"artifacts[0]: id {runner_id!r} present in both models and choices"
    if not isinstance(row, dict) or not isinstance(row.get("candidates"), list):
        return f"artifacts[0].choices.{runner_id}: expected object with candidates list"
    return None
