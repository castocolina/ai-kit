"""The pure plan.json contract: schema version, canonical serialization and the
inventory digest. Imports only `hashlib`/`json`, so the pure `recommend` engine can
depend on it without reaching any I/O module (REC-01)."""
import hashlib
import json

# 18-04 adds top-level ``artifacts`` on plans.
PLAN_SCHEMA_VERSION = 3


def canonical_json(obj) -> str:
    """The byte-stable serialization every plan.json is written with."""
    return json.dumps(obj, sort_keys=True, indent=2, ensure_ascii=False) + "\n"


def inventory_digest(inventory: dict) -> str:
    """`sha256:` over the compact, sorted inventory JSON (REC-01's input fingerprint).
    Candidate order is not significant (R7): candidates are sorted by runtime and model
    first, so every caller gets the same digest for a reordered inventory."""
    stable = dict(inventory)
    if isinstance(inventory.get("candidates"), list):
        stable["candidates"] = sorted(
            inventory["candidates"],
            key=lambda c: (c.get("runtime") or "", c.get("model") or ""),
        )
    compact = json.dumps(stable, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return "sha256:" + hashlib.sha256(compact.encode("utf-8")).hexdigest()
