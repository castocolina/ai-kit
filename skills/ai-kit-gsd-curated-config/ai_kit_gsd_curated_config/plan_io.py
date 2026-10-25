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
import shlex

from . import cross_ai, gsd_catalog, host, presets, roles, skill_scan
from . import skills as skills_mod
from .plan_schema import PLAN_SCHEMA_VERSION, canonical_json, inventory_digest

_AFFINITY_SUFFIX = "; fix skill_affinity.json"
_PKG_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AFFINITY_PATH = os.path.join(_PKG_ROOT, "skill_affinity.json")

INVENTORY_SCHEMA_VERSION = 3

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
    schema-version-3 contract."""
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


_ROOT_KINDS = ("project", "global", "plugin")


def _skill_entry_problem(entry, index: int) -> str | None:
    if not isinstance(entry, dict):
        return f"key skills[{index}]: expected dict"
    for key, expected in (
        ("name", str),
        ("root_kind", str),
        ("root", str),
        ("real_dir", str),
        ("description", str),
        ("escapes_root", bool),
        ("addressable", bool),
    ):
        val = entry.get(key)
        if not isinstance(val, expected):
            return f"key skills[{index}].{key}: expected {expected.__name__}"
    return _skill_value_problem(entry, f"key skills[{index}]")


def _skill_home_paths_problem(entry: dict, where: str) -> str | None:
    home_rel = entry.get("real_dir_home")
    if home_rel is not None and not (isinstance(home_rel, str) and home_rel.startswith("~/")):
        return f"{where}.real_dir_home: expected null or a ~/ path"
    ai_kit_dir = entry.get("ai_kit_skills_dir")
    if ai_kit_dir is not None and not (
        isinstance(ai_kit_dir, str) and home_relative_root(ai_kit_dir)
    ):
        return f"{where}.ai_kit_skills_dir: expected null or a ~/ path inside $HOME"
    return None


def _skill_value_problem(entry: dict, where: str) -> str | None:
    """Values recommend and apply consume verbatim: trusted-root candidates, skill refs (C-W10)."""
    if entry["root_kind"] not in _ROOT_KINDS:
        return f"{where}.root_kind: expected one of {', '.join(_ROOT_KINDS)}"
    problem = _skill_home_paths_problem(entry, where)
    if problem:
        return problem
    plugin = entry.get("plugin")
    if plugin is not None and not isinstance(plugin, str):
        return f"{where}.plugin: expected str or null"
    valid = skill_scan.SKILL_NAME_RE.fullmatch
    if entry["addressable"] and not valid(entry["name"]):
        return f"{where}.name: not a valid skill name for an addressable row"
    if entry["addressable"] and plugin is not None and not valid(plugin):
        return f"{where}.plugin: not a valid plugin name for an addressable row"
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
    enumeration = inv.get("runtime_enumeration", {})
    if not isinstance(enumeration, dict) or not all(
        state in ("failed", "empty", "ok") for state in enumeration.values()
    ):
        return "key runtime_enumeration: expected object of failed/empty/ok"
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
    for key in (
        "slug", "transport", "binary", "model_key", "effort_key", "default_effort", "runtime",
    ):
        if key not in lane:
            return f"key gsd_core.review_lanes[{index}]: missing {key}"
    slug = lane["slug"]
    if not isinstance(slug, str):
        return f"key gsd_core.review_lanes[{index}].slug: expected str"
    for key in ("transport", "binary", "model_key", "effort_key", "default_effort", "runtime"):
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


def _load_doc(path: str, label: str, suffix: str, validate) -> tuple[dict | None, str | None]:
    """Read one JSON document and validate it: ``(doc, None)`` or a one-line error."""
    try:
        with open(path, encoding="utf-8") as handle:
            doc = json.load(handle)
    except OSError as exc:
        reason = exc.strerror or "unreadable"
        return None, f"{label} {path}: cannot read ({reason}){suffix}"
    except (ValueError, RecursionError):  # JSONDecodeError, UnicodeDecodeError, deep nesting
        return None, f"{label} {path}: invalid JSON{suffix}"
    problem = validate(doc)
    if problem:
        return None, f"{label} {path}: {problem}{suffix}"
    return doc, None


def load_affinity(path: str) -> tuple[dict | None, str | None]:
    """Reads and validates ``skill_affinity.json``. Returns ``(doc, None)`` or an error."""
    return _load_doc(path, "skill_affinity", _AFFINITY_SUFFIX, skills_mod.validate_affinity)


def load_inventory(path: str) -> tuple[dict | None, str | None]:
    """Reads and validates the inventory JSON. Returns `(inventory, None)` on
    success, else `(None, "<one-line error>; rerun inventory")`. This is the only
    file the recommend CLI path reads."""
    return _load_doc(path, "inventory", _ERROR_SUFFIX, _validate_inventory)


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


def sibling_inventory_path(plan_path: str) -> str:
    """``inventory.json`` beside ``plan.json``."""
    return os.path.join(os.path.dirname(os.path.abspath(plan_path)), "inventory.json")


def load_plan(path: str) -> tuple[dict | None, str | None]:
    """Read and validate a schema-2 plan. Returns ``(plan, None)`` or ``(None, error)``."""
    return _load_doc(path, "plan", _PLAN_ERROR_SUFFIX, _plan_problem)


def _plan_problem(plan) -> str | None:
    if not isinstance(plan, dict):
        return "top-level JSON is not an object"
    return _plan_envelope_problem(plan) or validate_plan(plan)


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
    problem = pi_sonnet_problem(plan, inv)
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


def _plan_entry(plan: dict, key: str) -> dict | None:
    for entry in plan.get("entries") or []:
        if entry.get("key") == key:
            return entry
    return None


PI_SONNET_KEY = "model_profile_overrides.pi.sonnet"


def pi_sonnet_value_problem(inv: dict, value) -> str | None:
    """The one membership rule for plan-set and for a hand-edited plan (22 D-05).

    gsd-core's hook writes this value into every request, so a provider/model string or
    any id the session provider does not serve is refused. ``--force`` cannot pin it.
    """
    allowed = roles.pi_session_ids(inv)
    session = inv.get("pi_session")
    provider = session.get("provider") if isinstance(session, dict) else None
    if not allowed:
        return (
            f"{PI_SONNET_KEY}: no candidate from the session provider "
            "(PI_PROVIDER was unset when inventory ran, or the provider serves no listed "
            "model); run inventory inside the pi session, or plan-unset it"
        )
    if value not in allowed:
        return (
            f"{value!r} is not a bare model id the session provider {provider} serves "
            f"(candidates: {', '.join(allowed)}); gsd-core's hook writes it into every "
            "request, so --force cannot pin it"
        )
    return None


def pi_sonnet_problem(plan: dict, inv: dict) -> str | None:
    """Refuse a decided ``pi.sonnet`` before a dry run or an apply writes anything."""
    entry = _plan_entry(plan, PI_SONNET_KEY)
    if entry is None or entry.get("op") != "set" or entry.get("status") == "needs_choice":
        return None
    return pi_sonnet_value_problem(inv, entry.get("value"))


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


_TRUSTED_ROOTS_KEY = "agent_skills_security.trusted_global_roots"


def effective_trusted_roots(plan: dict, inv: dict) -> list[str]:
    """The roots gsd-core would see after apply; an open choice counts as its first
    candidate (apply refuses an open choice anyway)."""
    entry = _plan_entry(plan, _TRUSTED_ROOTS_KEY)
    if entry is None:
        return skills_mod.existing_roots(inv)
    value = entry_effective_value(entry)
    if entry.get("status") == "needs_choice":
        candidates = entry.get("candidates")
        first = candidates[0] if isinstance(candidates, list) and candidates else None
        value = first.get("value") if isinstance(first, dict) else skills_mod.existing_roots(inv)
    return [item for item in value if isinstance(item, str)] if isinstance(value, list) else []


def _root_covers(path: str, root: str) -> bool:
    """gsd-core's containment: both realpaths exist and ``path`` stays inside ``root``.

    Like gsd-core (``loadTrustedGlobalRoots``), ``~``/``~/`` expand against the home dir, a
    root that is not absolute after expansion is dropped, and the filesystem root and the
    home dir itself are too broad to trust."""
    if root == "~" or root.startswith("~/"):
        root = os.path.expanduser(root)
    if not os.path.isabs(root):
        return False
    root_real, path_real = skill_scan._real(root), skill_scan._real(path)  # pylint: disable=protected-access
    if root_real in (os.path.abspath(os.sep), skill_scan._real(os.path.expanduser("~"))):  # pylint: disable=protected-access
        return False
    return (
        root_real is not None
        and path_real is not None
        and skill_scan._inside(path_real, root_real)  # pylint: disable=protected-access
    )


def _live_global_problem(name: str, inv: dict, roots: list[str]) -> str | None:
    """Why a kept ``global:<name>`` no longer resolves the way inventory recorded it.

    Re-reads the host skills dir: the entry must exist, hold a ``SKILL.md``, and that file's
    realpath must sit inside the host skills dir or an effective trusted root (gsd-core's
    rule). None when it still resolves, or when inventory recorded no host skills dir.
    """
    skills_dir = skills_mod.host_skills_dir(inv)
    if skills_dir is None:
        return None
    skill_md = os.path.join(skills_dir, name, "SKILL.md")
    if not os.path.isfile(skill_md):
        return f"{name}: the host skills dir no longer holds its SKILL.md"
    if _root_covers(skill_md, skills_dir) or any(_root_covers(skill_md, r) for r in roots):
        return None
    return (
        f"{name}: its SKILL.md realpath is outside the host skills dir and no trusted root "
        "covers it"
    )


# gsd-core's accepted global skill name: [A-Za-z0-9_-]+ segments joined by single colons.
_GLOBAL_NAME_RE = re.compile(r"[A-Za-z0-9_-]+(?::[A-Za-z0-9_-]+)*")


def _kept_global_skip(item: str, inv: dict, roots: list[str]) -> tuple[str, str] | None:
    """A kept ``global:`` ref gsd-core skips: a name outside gsd-core's grammar, a bare
    ``global:<name>`` judged live against the filesystem (gsd-core's own check, which
    resolves symlinked roots; the inventory's lexical verdict only when inventory recorded no
    host skills dir), or a namespaced ``global:<plugin>:<name>`` on a non-claude host."""
    name = item[len("global:"):]
    if not _GLOBAL_NAME_RE.fullmatch(name):
        return name, f"global:{name} is not a valid gsd-core skill name"
    if item.count(":") == 1:
        if skills_mod.host_skills_dir(inv) is not None:
            cause = _live_global_problem(name, inv, roots)
        else:
            cause = skills_mod.global_ref_skip_reason(name, inv, roots)
        return (name, cause) if cause else None
    if inv.get("host") != "claude":
        name = item[len("global:"):]
        return name, f"global:{name} is namespaced and gsd-core skips it on a non-claude host"
    return None


def _project_root_of(inv: dict) -> str | None:
    """The project dir the inventory was taken for: the parent of its ``.planning`` dir."""
    recorded = (inv.get("existing_config") or {}).get("path")
    if not isinstance(recorded, str) or not recorded:
        return None
    # The lexical path first: a symlinked .planning or config.json realpaths elsewhere.
    for start in (os.path.abspath(recorded), os.path.realpath(recorded)):
        probe = os.path.dirname(start)
        while os.path.basename(probe) != ".planning":
            parent = os.path.dirname(probe)
            if parent == probe:
                break
            probe = parent
        else:
            return os.path.dirname(probe)
    return None


def _project_ref_skip_reason(ref: str, inv: dict) -> tuple[str, str] | None:
    """gsd-core's rule for a project-relative reference (any path without the ``global:``
    prefix, ``skills/<name>`` included): the skill directory must resolve inside the project
    and hold a SKILL.md (``SKILL.md`` itself is not resolved). ``(name, cause)`` when it
    would be skipped, else None; ``name`` is the bare name for ``skills/<name>``, else the
    path."""
    tail = ref[len("skills/"):] if ref.startswith("skills/") else ""
    name = tail if tail and "/" not in tail and tail not in (".", "..") else ref
    if os.path.isabs(ref):
        return name, f"{name}: gsd-core takes only a project-relative path, not {ref}"
    project = _project_root_of(inv)
    if project is None:
        return name, f"{name}: the inventory records no project to confine it to"
    skill_dir = os.path.join(project, ref)
    if skill_scan._escapes_project(skill_dir, project):  # pylint: disable=protected-access
        return name, f"{name}: {ref} resolves outside the project"
    if not os.path.isfile(os.path.join(skill_dir, "SKILL.md")):
        return name, f"{name}: no SKILL.md at {ref}"
    return None


def _kept_skip(item: str, inv: dict, roots: list[str]) -> tuple[str, str] | None:
    """(name, cause) when a kept config reference is one gsd-core skips; None otherwise."""
    if item.startswith("global:"):
        return _kept_global_skip(item, inv, roots)
    return _project_ref_skip_reason(item, inv)


def _skipped_items(entry: dict, inv: dict, roots: list[str]) -> list[tuple[str, str]]:
    """(bare name, cause) for each item gsd-core would skip; not-installed names are apply's
    own refusal. A kept entry is checked both as ``global:<name>`` and as ``skills/<name>``
    (a project copy must resolve inside the project and hold a SKILL.md)."""
    value = entry_effective_value(entry)
    items = [value] if isinstance(value, str) else value if isinstance(value, list) else []
    found: list[tuple[str, str]] = []
    for item in items:
        if not isinstance(item, str):
            continue
        if entry.get("op") == "set":
            # shortcut: a newly wired name is checked against the inventory snapshot only;
            # re-run inventory after the filesystem changes (kept refs are revalidated live)
            cause = skills_mod.skip_reason(item, inv, roots)
            skipped = (item, cause) if cause and cause != skills_mod.NOT_INSTALLED else None
        elif entry.get("op") == "keep":
            skipped = _kept_skip(item, inv, roots)
        else:
            skipped = None
        if skipped:
            found.append(skipped)
    return found


def _plan_set_command(key: str, value: list[str]) -> str:
    return f"plan-set {key} {shlex.quote(json.dumps(value, separators=(',', ':')))}"


def _round_trip_name(item: str, inv: dict) -> str | None:
    """The bare name that re-resolves to the same reference, or None when none does: a bare
    name itself, a ``skills/<name>``, or a ``global:<name>`` that ``locate`` (recommend's
    choice) still resolves to the global copy — not when a project copy shadows it or the
    inventory has no row for it (the bare name would then fail apply's "not installed"
    refusal)."""
    if "/" not in item and ":" not in item:
        return item  # a bare name, the form a fresh plan holds, already round-trips
    tail = item[len("skills/"):] if item.startswith("skills/") else ""
    if tail and "/" not in tail:
        return tail
    if item.startswith("global:") and item.count(":") == 1:
        name = item[len("global:"):]
        row = skills_mod.locate(name, inv)
        if row is not None and row.get("root_kind") == "global":
            return name
    return None


def _kept_names(items: list, skipped: list[str], inv: dict) -> tuple[list[str], str]:
    """Bare names to keep, plus a note for refs that cannot round-trip through one.

    Only a reference whose bare name re-resolves to the same reference is reduced to it
    (``_round_trip_name``). Any other healthy reference — a namespaced
    ``global:<plugin>:<name>``, a project path outside ``skills/``, or a ``global:<name>``
    that a project copy would shadow — is named and left for an explicit decision, never
    dropped from the printed command silently or switched to another copy.
    """
    keep: list[str] = []
    pending: list[str] = []
    for item in items:
        if not isinstance(item, str):
            continue
        name = _round_trip_name(item, inv)
        if name is None:
            if item not in skipped and item[len("global:"):] not in skipped:
                pending.append(item)
        elif name not in skipped:
            keep.append(name)
    note = ""
    if pending:
        note = (
            "; kept " + ", ".join(pending) + " cannot round-trip through a bare name, so it "
            "is not in that command: decide it explicitly"
        )
    return keep, note


def _skip_message(entry: dict, inv: dict, roots: list[str]) -> str | None:
    skipped = _skipped_items(entry, inv, roots)
    if not skipped:
        return None
    key = entry["key"]
    names = [name for name, _cause in skipped]
    fixes = []
    needed = sorted({r for n in names if (r := skills_mod.needed_root(n, inv)) and r not in roots})
    if needed:
        fixes.append(_plan_set_command(_TRUSTED_ROOTS_KEY, roots + needed))
    value = entry_effective_value(entry)
    items = [value] if isinstance(value, str) else value or []
    keep, note = _kept_names(items, names, inv)
    fixes.append(_plan_set_command(key, keep))
    causes = "; ".join(cause for _name, cause in skipped)
    return (
        f"{key}: gsd-core would skip {', '.join(names)} ({causes}); fix: "
        + " or ".join(fixes) + note
    )


def skipped_skill_problem(plan: dict, inv: dict, keys: set[str] | None = None) -> str | None:
    """A decided agent_skills entry gsd-core would skip, with cause and fix; None when none.
    Plan edits and apply both call this; it is not reachable through ``--force``."""
    roots = effective_trusted_roots(plan, inv)
    messages: list[str] = []
    for entry in plan.get("entries") or []:
        key = entry.get("key")
        if not (isinstance(key, str) and key.startswith("agent_skills.")):
            continue
        if entry.get("status") == "needs_choice" or (keys is not None and key not in keys):
            continue
        message = _skip_message(entry, inv, roots)
        if message:
            messages.append(message)
    return "; ".join(messages) or None


def execution_effective_on(plan: dict) -> bool:
    entry = _plan_entry(plan, "workflow.cross_ai_execution")
    return entry_effective_value(entry) is True


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
    if cross_ai.timeout_ok(value):
        return None
    return f"{label} must be an integer >= {cross_ai.MIN_TIMEOUT_S} (got {value!r})"


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
    if cross_ai.is_model_key(key):
        return cross_ai.model_id_problem(key, value)
    if key == "workflow.cross_ai_timeout":
        problem = timeout_problem(key, value)
        if problem:
            return problem
    if (
        key in cross_ai.COMMAND_KEYS
        and value != cross_ai.COMMAND_KEYS[key]
        and not entry.get("forced")
    ):
        return f"{key}: must be {cross_ai.COMMAND_KEYS[key]!r} unless forced"
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
        if not skill_scan.SKILL_NAME_RE.fullmatch(name):
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
    return _validate_effort(config.get("effort", {}), models) or _validate_artifact_targets(
        prefer, models, router, choice_map, status
    )


def _validate_effort(effort, models: dict) -> str | None:
    """Optional per-runner effort pin (WR-06): only runners that can pin it, on a set model."""
    if not isinstance(effort, dict):
        return "artifacts[0].config.effort: expected object"
    for runner_id, level in effort.items():
        levels = cross_ai.EFFORT_LEVELS.get(runner_id)
        if levels is None:
            return f"artifacts[0].config.effort: {runner_id!r} cannot pin effort"
        if runner_id not in models:
            return f"artifacts[0].config.effort: id {runner_id!r} has no model"
        if level not in levels:
            return f"artifacts[0].config.effort.{runner_id}: expected one of {list(levels)}"
    return None


def _validate_prefer(prefer, plan_host: str) -> str | None:
    if not isinstance(prefer, list) or not prefer or not all(isinstance(x, str) for x in prefer):
        return "artifacts[0].config.prefer: expected non-empty list of str"
    if len(set(prefer)) != len(prefer):
        return "artifacts[0].config.prefer: ids must be unique"
    for runner_id in prefer:
        if runner_id not in cross_ai.RUNNER_IDS:
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
    return cross_ai.model_id_problem(f"artifacts[0].config.models.{runner_id}", model)


def _choice_row_problem(prefer, runner_id: str, models, row) -> str | None:
    if runner_id not in prefer:
        return f"artifacts[0].choices: id {runner_id!r} not in prefer"
    if runner_id in models:
        return f"artifacts[0]: id {runner_id!r} present in both models and choices"
    if not isinstance(row, dict) or not isinstance(row.get("candidates"), list):
        return f"artifacts[0].choices.{runner_id}: expected object with candidates list"
    return None
