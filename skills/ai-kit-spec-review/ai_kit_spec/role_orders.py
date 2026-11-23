"""36 SPEC R3, D-04: each role's priority order.

[lanes.policy.review] and [lanes.policy.execute] hold a ladder each; a legacy shared
[lanes.policy] ladder is read as each role's order filtered to that role's lanes.
Pure: it imports nothing from ai_kit_spec, so config_io, quota and the execute adapter may
import it.
"""

ROLES = ("review", "execute")


def _lane_keys(lanes) -> set:
    if not isinstance(lanes, list):
        return set()
    return {lane["key"] for lane in lanes
            if isinstance(lane, dict) and isinstance(lane.get("key"), str)}


def _keep(keys: list, allowed: set) -> tuple[list, list]:
    kept, dropped = [], []
    for entry in keys:
        if entry in kept or entry in dropped:
            continue
        if isinstance(entry, str) and entry in allowed:
            kept.append(entry)
        else:
            dropped.append(entry)
    return kept, dropped


def _table_ladder(policy: dict, role: str, warn_fn) -> list | None:
    if role not in policy:
        return None
    table = policy[role]
    if isinstance(table, dict):
        if "ladder" not in table:
            return None
        if isinstance(table["ladder"], list):
            return table["ladder"]
    warn_fn(f"ai-kit-spec: [lanes.policy.{role}] must be a table holding a ladder list; ignored")
    return None


def role_orders(policy: dict, role_lanes: dict, warn_fn) -> dict:
    """One order per role; role tables win from either layer, legacy fills the rest."""
    orders, legacy_roles = {}, []
    for role in ROLES:
        allowed = _lane_keys(role_lanes.get(role, []))
        ladder = _table_ladder(policy, role, warn_fn)
        if ladder is None:
            legacy_roles.append(role)
        else:
            orders[role], dangling = _keep(ladder, allowed)
            if dangling:
                warn_fn(f"ai-kit-spec: [lanes.policy.{role}] ladder names no {role} lane: "
                        f"{dangling}; dropped")
    legacy = policy.get("ladder")
    if not isinstance(legacy, list):
        legacy = []
    for role in legacy_roles:
        orders[role], _ = _keep(legacy, _lane_keys(role_lanes.get(role, [])))
    if legacy and legacy_roles:
        warn_fn("ai-kit-spec: the shared [lanes.policy] ladder loads as one order per role "
                f"(review: {len(orders['review'])} keys, execute: {len(orders['execute'])} keys); "
                "the next write replaces it with [lanes.policy.review] and [lanes.policy.execute]")
        allowed = (_lane_keys(role_lanes.get("review", []))
                   | _lane_keys(role_lanes.get("execute", [])))
        _, dangling = _keep(legacy, allowed)
        if dangling:
            warn_fn(f"ai-kit-spec: [lanes.policy] ladder names no lane: {dangling}; dropped")
    elif legacy:
        warn_fn("ai-kit-spec: the shared [lanes.policy] ladder is ignored: "
                "[lanes.policy.review] and [lanes.policy.execute] set each role's order")
    return {role: orders[role] for role in ROLES}


def role_order(config: dict, role: str) -> list:
    """Return the role order, falling back for legacy hand-built configs."""
    if isinstance(config.get("orders"), dict):
        return list(config["orders"].get(role, []))
    return list(config.get("policy", {}).get("ladder", []))


def ordered_lanes(config: dict, role: str) -> list:
    """Return each ordered role lane once, taking the first entry for a key."""
    lanes = config.get(role, [])
    by_key = {}
    if isinstance(lanes, list):
        for lane in lanes:
            if isinstance(lane, dict) and isinstance(lane.get("key"), str):
                by_key.setdefault(lane["key"], lane)
    keys, _ = _keep(role_order(config, role), set(by_key))
    return [by_key[key] for key in keys]


def split_policy(policy: dict) -> tuple[dict, dict]:
    """Separate flat policy keys from role tables."""
    flat = {key: value for key, value in policy.items() if key not in ROLES}
    roles = {role: dict(policy[role]) for role in ROLES if isinstance(policy.get(role), dict)}
    return flat, roles
