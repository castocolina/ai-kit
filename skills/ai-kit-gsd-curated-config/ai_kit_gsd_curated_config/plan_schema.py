"""The pure plan.json contract: schema version, canonical serialization and the
inventory digest. Imports only `hashlib`/`json`, so the pure `recommend` engine can
depend on it without reaching any I/O module (REC-01)."""
import hashlib
import json

PLAN_SCHEMA_VERSION = 1


def canonical_json(obj) -> str:
    """The byte-stable serialization every plan.json is written with."""
    return json.dumps(obj, sort_keys=True, indent=2, ensure_ascii=False) + "\n"


def inventory_digest(inventory: dict) -> str:
    """`sha256:` over the compact, sorted inventory JSON (REC-01's input fingerprint)."""
    compact = json.dumps(inventory, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return "sha256:" + hashlib.sha256(compact.encode("utf-8")).hexdigest()
