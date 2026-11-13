#!/usr/bin/env python3
"""The ladder caller of jev-fast-decision: one client call per ladder run.

Reached through `jev_review.py ladder|detect` and `consent --client`; never run on its own.
This file holds no endpoint URL, no model id and no backend order. The backend table lives
entirely in the client, which owns the ladder (local rungs first, one item per call, then one
consented remote batch) and returns a per-item rung trail; this module maps that trail onto one
column per table backend and keeps only item validation (summaries only), the scrubbed child
environment, `detect`, `--second-opinion` and the consent delegation. The client runs as a
child process, once per ladder run. stdlib only. Never prints a key value: every client JSON
field passes a fixed allowlist before it reaches stdout. Every answer is advisory.

    jev_review.py detect [--client PATH]
    jev_review.py ladder [--second-opinion] [--client PATH] < {"items": [...]}
    jev_review.py consent grant|revoke|show <backend> [--client PATH]
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import os
import re
import subprocess
import sys
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any, NamedTuple

# The client's entry point, relative to a skills root (the lookup's last step, per root).
JEV_ENTRY_REL = os.path.join("jev-fast-decision", "scripts", "jev_review.py")
# Where a host keeps its skills, in lookup order: (env var overriding the root, the fallback
# under HOME, the suffix under the root). A plain tuple, so a drift test can compare it with
# every other copy (plan 29-15). Order is the lookup order.
SKILLS_ROOTS = (
    ("CLAUDE_CONFIG_DIR", ".claude", "skills"),
    (None, ".agents", "skills"),
    ("XDG_CONFIG_HOME", ".config", "opencode/skills"),
    ("CURSOR_CONFIG_DIR", ".cursor", "skills"),
    ("PI_CODING_AGENT_DIR", ".pi/agent", "skills"),
)
CALL_TIMEOUT_SECONDS = 30
ZERO_HEAD = "0" * 40
CLIENT_PROTOCOL_RE = re.compile(r"^CLIENT_PROTOCOL = 2$", re.M)
# The client's control variables: a parent-shell value must never widen the child's gate (D-09).
# Key and URL variables pass through untouched, so each key reaches only its own backend's row.
_CONTROL_NAMES = {"JEV_BACKEND", "JEV_ALLOW_REMOTE", "JEV_MIN_CONFIDENCE"}
_CONTROL_PREFIXES = ("GSD_PATH_JEV",)

ITEM_KEYS = {"id", "type", "instructions", "context", "criteria"}
ITEM_TYPES = {"choice", "noul", "score"}
MAX_FIELD_CHARS = 1500
# Defense in depth, not a guarantee: the shared key shapes (the sibling secret_shapes.py, a
# byte-identical copy of the shared scanner) and long opaque base64 runs (48+ so a 40-char
# commit SHA in a summary still passes). A false positive only means own reasoning.
_BASE64_RUN_RE = re.compile(r"[A-Za-z0-9+/]{48,}")


def _load_secret_shapes() -> Any:
    """The sibling secret_shapes.py, loaded by path: this module is itself loaded by path, and
    from copied skill folders, so its own folder is not always on the import path."""
    path = Path(__file__).resolve().parent / "secret_shapes.py"
    spec = importlib.util.spec_from_file_location("jev_secret_shapes", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"jev-fast-decision: cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_SECRET_SHAPES = _load_secret_shapes()


def _has_secret(value: str) -> bool:
    """Whether `value` holds a shared key shape or a long opaque base64 run."""
    return bool(_SECRET_SHAPES.detect(value)) or _BASE64_RUN_RE.search(value) is not None
# Fixed output allowlists (24 D-13): a leaky client's extra fields never reach stdout. The
# boundary is enforced on *values*, not only on field names (WR-02): every string printed here
# has to be one of the documented codes or match the documented shape of its field, or it is
# replaced by a fixed code — an allowlisted field name is not a licence to print its content.
_CONSENT_KEYS = ("ok", "backend", "host", "consent", "file", "note", "reason")
_SCALAR_TYPES = (str, bool, int)
_STATUS_CODES = frozenset({"ok", "unavailable", "disabled", "no_consent", "unusable", "usable",
                           "consent_required_for_remote", "no_client", "incompatible_client",
                           "client_timeout", "client_not_runnable", "client_bad_output"})
# The client's own label for "this row reads its key from here" (jev_review._first_key).
_KEY_SOURCES = frozenset({"env", "file", "missing_file", "world_readable", "empty_file",
                          "missing_api_key", "non_loopback_url", "insecure_url"})
# How a probe row's certainty about its key was obtained (jev_review CELL_STATUSES).
_KEY_CHECKS = frozenset({"verified-live", "documented", "unsupported", "unverified"})
# A status, reason or item-error code: lowercase snake tokens, up to four colon-qualified.
_CODE_RE = re.compile(r"^[a-z][a-z0-9_]{0,63}(?::[a-z0-9_+.:-]{1,63}){0,3}$")
# A backend or probe name (the client's own table ids), a provider model id, a bare host, an
# ISO date, and the consent record's documented path.
_NAME_RE = re.compile(r"^[a-z][a-z0-9_-]{0,31}$")
_MODEL_RE = re.compile(r"^[a-z0-9][a-z0-9._:/+-]{0,63}$")
_HOST_RE = re.compile(r"^[a-z0-9][a-z0-9.-]{0,253}$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_CONSENT_FILE_RE = re.compile(r"^[A-Za-z0-9._/ -]{1,4096}$")
_CONSENT_FILE_TAIL = os.path.join("ai-kit", "jev-consent.json")
# The client's single fixed grant announcement (jev_review.consent_command): free prose is
# never printed, whatever field name it arrives under.
_NOTE_PREFIX = "questions go to "
MAX_NOTE_CHARS = 200


class Seams(NamedTuple):
    """Injected side effects, so tests never touch the network, real config or a real client."""

    env: Mapping[str, str]
    run: Callable[..., Any]


def real_seams() -> Seams:
    """The production side effects."""
    return Seams(env=os.environ, run=subprocess.run)


# ─── client discovery ─────────────────────────────────────────────────────────

def skills_roots(env: Mapping[str, str], own_root: str | None) -> list[str]:
    """The skills dirs to search, in lookup order: `own_root` first when given, then the
    `SKILLS_ROOTS` rows (the variable's value when set, else HOME plus the fallback)."""
    home = env.get("HOME", "~")
    roots = [own_root] if own_root else []
    for variable, fallback, suffix in SKILLS_ROOTS:
        base = (env.get(variable, "").strip() if variable else "") or os.path.join(home, fallback)
        roots.append(os.path.join(base, suffix))
    return [os.path.expanduser(root) for root in roots]


def client_candidates(env: Mapping[str, str], override: str | None) -> list[str]:
    """Where the jev client may live, in lookup order."""
    # abspath, never realpath: the skill is symlinked into the host's skills dir, beside jev.
    own_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    explicit = override or env.get("AI_KIT_JEV_CLIENT", "").strip()
    found = [os.path.expanduser(explicit)] if explicit else []
    return found + [os.path.expanduser(os.path.join(root, JEV_ENTRY_REL))
                    for root in skills_roots(env, own_root)]


def find_client(env: Mapping[str, str], override: str | None) -> tuple[str | None, list[str]]:
    """First existing client path, plus every path tried (for `detect`)."""
    tried = client_candidates(env, override)
    for path in tried:
        if os.path.isfile(path):
            return path, tried
    return None, tried


def client_ok(path: str) -> bool:
    """True only when the client's own text declares CLIENT_PROTOCOL = 2.

    The text is read, never imported (D-10): an import would execute the client in this
    process and reopen the env leak 24 D-06 closed. A client without the line — the live
    global copy is env-driven and has no consent gate — is never run, so it never receives
    the passed-through keys and URLs (T-21.1-22).
    """
    try:
        with open(path, encoding="utf-8") as handle:
            text = handle.read(256 * 1024 + 1)
    except (OSError, UnicodeError):
        return False
    if len(text) > 256 * 1024:
        return False
    return CLIENT_PROTOCOL_RE.search(text) is not None


# ─── items ────────────────────────────────────────────────────────────────────

def _probability(value: Any) -> float | None:
    """A finite probability in [0, 1]: never NaN, never an infinity, never an out-of-range
    number, never a bool (WR-03 — an invalid number is not an answer worth printing)."""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        number = float(value)
        if math.isfinite(number) and 0.0 <= number <= 1.0:
            return number
    return None


def _bad_text(value: Any) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return "empty"
    if len(value) > MAX_FIELD_CHARS:
        return "too_long"
    if "```" in value:
        return "code_fence"
    if _has_secret(value):
        return "secret_pattern"
    return None


def _criteria_error(item: dict[str, Any]) -> str | None:
    """`criteria` is validated against the client's builder (present, even null, or missing).

    This module rejects, alone and before the one combined call, every shape the client would
    reject the whole request for (T-21.1-29), so one bad item never loses its siblings'
    answers.
    """
    if "criteria" not in item:
        # Only noul may omit criteria; the client rejects a whole request whose choice or
        # score item lacks them (jev_review.request_body).
        return None if item["type"] == "noul" else "missing_criteria"
    criteria = item["criteria"]
    if item["type"] == "noul":
        ok = (isinstance(criteria, dict) and set(criteria) == {"true", "false"}
              and not any(_bad_text(text) for text in criteria.values()))
        return None if ok else "bad_criteria"
    if item["type"] == "score":
        ok = (isinstance(criteria, list) and 2 <= len(criteria) <= 10
              and not any(_bad_text(level) for level in criteria))
        return None if ok else "bad_criteria"
    if not isinstance(criteria, dict) or len(criteria) < 2:
        return "choice_needs_two_criteria"
    if any(_bad_text(key) or _bad_text(text) for key, text in criteria.items()):
        return "bad_criteria"
    return None


def _id_error(item: Any) -> str | None:
    """Why this item's own id may not be sent anywhere or echoed back.

    An id is payload text and a log line like any other field: the client keys its question
    state by id, quotes the id inside the instruction text and writes it to the persistent
    answer log, so it takes the same length/fence/secret guard before any call or output — a
    schema-valid item must not smuggle a key through its own name (CR-01, D-11, SPEC R6).
    """
    identifier = item.get("id") if isinstance(item, dict) else None
    if not isinstance(identifier, str) or not identifier.strip():
        return "missing_id"
    if identifier.startswith("#"):
        # Reserved for this module's own rejection keys: an input id here could collide with
        # the `#<stdin index>` key of a later rejected item.
        return "reserved_id"
    reason = _bad_text(identifier)
    return f"{reason}_id" if reason else None


def item_error(item: Any) -> str | None:
    """Reason code when an item must not be sent anywhere, else None."""
    if not isinstance(item, dict):
        return "missing_id"
    id_reason = _id_error(item)
    if id_reason:
        return id_reason
    if set(item) - ITEM_KEYS:
        return "unknown_key"
    # WR-01: membership in a set requires a hashable value, and `[]` / `{}` are valid JSON.
    # An unhashable type must fail this item alone (D-07), not raise over the whole batch.
    item_type = item.get("type")
    if not isinstance(item_type, str) or item_type not in ITEM_TYPES:
        return "bad_type"
    for field in ("instructions", "context"):
        reason = _bad_text(item.get(field))
        if reason:
            return f"{reason}_{field}"
    return _criteria_error(item)


def _echoable(identifier: str) -> bool:
    """Whether an id may stand as a result key: it has to pass the payload guard itself.

    A rejection is printed as a result key, so an id that tripped the guard is keyed
    `#<stdin index>` instead of echoed: the reason code is a fixed string (CR-01).
    """
    return bool(identifier) and _bad_text(identifier) is None and not identifier.startswith("#")


def partition(items: list[Any]) -> tuple[list[dict[str, Any]], dict[str, Any], list[str]]:
    """(valid items, result rows, stdin-order keys). Rejected items never leave; every later
    item whose id already appeared — valid or not — is `duplicate_id`, and a rejected item
    with a blank, repeated, reserved or guard-tripping id is keyed `#<stdin index>` so the
    first occurrence keeps its row, a rejection key never equals a legal id, and a rejected
    unsafe id is never echoed back in the output it was rejected for."""
    valid, results, order = [], {}, []
    seen: set[str] = set()
    for index, item in enumerate(items):
        reason = item_error(item)
        identifier = item.get("id") if isinstance(item, dict) else None
        identifier = identifier if isinstance(identifier, str) and identifier.strip() else ""
        if not reason and identifier in seen:
            reason = "duplicate_id"
        if reason:
            own_key = _echoable(identifier) and identifier not in seen
            key = identifier if own_key else f"#{index}"
            results[key] = {"error": "invalid_input", "reason": reason,
                            "decided_by": "own_reasoning"}
            order.append(key)
            if _echoable(identifier):
                seen.add(identifier)
            continue
        valid.append(item)
        seen.add(identifier)
        results[identifier] = {}
        order.append(identifier)
    return valid, results, order


# ─── output allowlists ────────────────────────────────────────────────────────

def _scalar(value: Any) -> bool:
    return value is None or isinstance(value, _SCALAR_TYPES)


def _code(value: Any, fallback: str = "unavailable") -> str | None:
    """A status, reason or item-error code: the documented code shape, else the fallback.

    An explicit None is the client's own "not set" and stays None; anything else that is not a
    code (prose, a credential, a path) becomes the fixed `fallback` (WR-02).
    """
    if value is None:
        return None
    if (isinstance(value, str) and _CODE_RE.match(value) and not _has_secret(value)):
        return value
    return fallback


def _closed(value: Any, allowed: frozenset[str]) -> str | None:
    """A label from a closed vocabulary (key source, key-check), else None: never a guess."""
    return value if isinstance(value, str) and value in allowed else None


def _shape(value: Any, pattern: re.Pattern[str]) -> str | None:
    """A value with a documented shape (name, host, model id, date), else None."""
    if (isinstance(value, str) and pattern.fullmatch(value)
            and not _has_secret(value)):
        return value
    return None


def _note(value: Any) -> str | None:
    """The client's one fixed grant announcement, by its documented prefix.

    Free prose is never printed whatever field name it arrives under: a note that is not the
    documented sentence (or carries the shape of a secret) is dropped, not passed through.
    """
    if (isinstance(value, str) and value.startswith(_NOTE_PREFIX)
            and len(value) <= MAX_NOTE_CHARS and "```" not in value
            and not _has_secret(value)):
        return value
    return None


def _consent_file(value: Any) -> str | None:
    """The consent record's own path (D-10): the documented file under `ai-kit/`, else None."""
    if (isinstance(value, str) and _CONSENT_FILE_RE.fullmatch(value)
            and not _has_secret(value)
            and os.path.basename(value) == os.path.basename(_CONSENT_FILE_TAIL)):
        return value
    return None


def public_backends(probe_list: Any) -> dict[str, dict[str, Any]]:
    """The client's probe rows reduced to a fixed allowlist of value-checked label fields.

    Two bounds, not one: a compatible-but-leaky client's extra fields (a debug env, a key copy)
    never reach stdout whatever their names happen to be, and an allowlisted field only prints
    a value that matches that field's documented vocabulary or shape (24 D-13, WR-02).
    """
    public = {}
    for entry in probe_list if isinstance(probe_list, list) else []:
        if not isinstance(entry, dict):
            continue
        name = _shape(entry.get("name"), _NAME_RE)
        if name is None:
            continue
        row: dict[str, Any] = {"name": name}
        for key in ("remote", "batch", "usable"):
            if key in entry:
                row[key] = bool(entry[key])
        for key, guard in (("host", lambda v: _shape(v, _HOST_RE)),
                           ("reason", _code),
                           ("key_source", lambda v: _closed(v, _KEY_SOURCES)),
                           ("key_check", lambda v: _closed(v, _KEY_CHECKS)),
                           ("consent", lambda v: _shape(v, _DATE_RE))):
            if key in entry:
                row[key] = guard(entry[key])
        row["status"] = ("usable" if row.get("usable")
                         else _code(entry.get("reason")) or "unusable")
        public[name] = row
    return public


def public_consent_used(raw: Any) -> list[dict[str, str]]:
    """`[{backend, granted}]` value-checked pairs only, so an announcement can name consent."""
    used = []
    for entry in raw if isinstance(raw, list) else []:
        if not isinstance(entry, dict):
            continue
        backend, granted = (entry.get("backend"), entry.get("granted"))
        if isinstance(granted, bool) or not isinstance(granted, (str, int)):
            continue
        granted = str(granted)
        backend, granted = _shape(backend, _NAME_RE), _shape(granted, _DATE_RE)
        if backend is not None and granted is not None:
            used.append({"backend": backend, "granted": granted})
    return used


def public_remote_available(raw: Any) -> list[str]:
    """Backend names only: the rows a consent question is owed to."""
    if not isinstance(raw, list):
        return []
    return [name for entry in raw if (name := _shape(entry, _NAME_RE)) is not None]


def public_consent(got: dict[str, Any]) -> dict[str, Any]:
    """The client's consent result: the seven announcement fields, each value-checked."""
    if not isinstance(got.get("ok"), bool):
        return {"ok": False, "reason": "client_bad_output"}
    public = {key: got[key] for key in _CONSENT_KEYS if key in got and _scalar(got[key])}
    for key, guard in (("backend", lambda v: _shape(v, _NAME_RE)),
                       ("host", lambda v: _shape(v, _HOST_RE)),
                       ("consent", lambda v: _shape(v, _DATE_RE)),
                       ("file", _consent_file),
                       ("note", _note),
                       ("reason", lambda v: _code(v, "client_bad_output"))):
        if key in public:
            public[key] = guard(public[key])
    return public


def public_consent_grant(got: Any) -> dict[str, Any]:
    """A client consent result reduced to the announcement fields, whatever shape it arrived
    in: a non-object (a bare string, a list, a null) is a fail-closed `{"ok": False}`."""
    return public_consent(got if isinstance(got, dict) else {})


# ─── the one client call ──────────────────────────────────────────────────────

def child_env(seams: Seams, n_items: int) -> dict[str, str]:
    """The child env: control variables scrubbed, this module's own bounds set.

    Only the control variables are dropped; every key and URL variable passes through so the
    client's rows resolve them (D-09). The deadline scales with the item count plus the local
    rung's retry allowance: one call per item, two retries, one remote batch (D-12).
    """
    env = {name: value for name, value in seams.env.items()
           if name not in _CONTROL_NAMES
           and not any(name.startswith(prefix) for prefix in _CONTROL_PREFIXES)}
    env.update({"GSD_PATH_JEV": "1",
                "GSD_PATH_JEV_TIMEOUT_SECONDS": str(CALL_TIMEOUT_SECONDS),
                "GSD_PATH_JEV_DEADLINE_SECONDS": str(CALL_TIMEOUT_SECONDS * (n_items + 3)),
                "JEV_CALLER": "ai-kit-gsd-spec-discuss"})
    return env


def reviewed_head(seams: Seams) -> str:
    """HEAD's 40-hex SHA, else zeros (the client requires the shape, not a real commit)."""
    try:
        out = seams.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True,
                        check=False, timeout=5)
    except (OSError, subprocess.SubprocessError):
        return ZERO_HEAD
    head = (out.stdout or "").strip()
    return head if re.fullmatch(r"[0-9a-f]{40}", head) else ZERO_HEAD


def call_client(seams: Seams, client: str, env: dict[str, str], payload: dict[str, Any],
                args: tuple[str, ...] = ()) -> dict[str, Any]:
    """Run the jev client once with `args` after it; parsed JSON or a closed-set failure.

    argv is a list, never a shell. The subprocess timeout is the run deadline (scaled from
    the item count) plus ten seconds. Raw client output is dropped on a parse failure: only
    the closed-set status strings below can reach the caller.
    """
    items = payload.get("items")
    timeout = float(CALL_TIMEOUT_SECONDS) * (len(items) + 3 if isinstance(items, list) else 3)
    try:
        out = seams.run([sys.executable, "-B", client, *args], input=json.dumps(payload),
                        capture_output=True, text=True, env=env, check=False, timeout=timeout + 10)
    except subprocess.TimeoutExpired:
        return {"status": "unavailable", "reason": "client_timeout"}
    except OSError:
        return {"status": "unavailable", "reason": "client_not_runnable"}
    try:
        result = json.loads(out.stdout)
    except (TypeError, ValueError, RecursionError):
        return {"status": "unavailable", "reason": "client_bad_output"}
    return result if isinstance(result, dict) else {"status": "unavailable",
                                                    "reason": "client_bad_output"}


def closed_status(got: dict[str, Any]) -> str:
    """A status from the supported set, else `unavailable` (never raw client text, WR-02)."""
    status = got.get("status")
    return status if isinstance(status, str) and status in _STATUS_CODES else "unavailable"


# ─── trail mapping ────────────────────────────────────────────────────────────

def typed_answer(entry: Any, item: Mapping[str, Any]) -> dict[str, Any]:
    """One trail rung reduced to the caller's column: {choice, top, fallback, forced, model}
    or {error}. `forced` is the client's own flag (a truncated or oversized request), false
    when an older client does not send it.

    A score or choice pick is always one of `item`'s own criteria — the level text for a score,
    the key for a choice — never backend text, which could be unbounded or an injection. A
    `top`/`noul` has to be a finite probability in [0, 1] (never NaN or infinity: that is not a
    probability and it is not printable JSON), `needs_fallback` a real boolean, and the model
    id the documented shape, never whatever string came back (WR-02, WR-03).
    """
    if not isinstance(entry, dict):
        return {"error": "invalid_response"}
    error = entry.get("error")
    if error is not None:
        return {"error": _code(error, "invalid_response") or "invalid_response"}
    top = _probability(entry.get("top"))
    if top is None:
        return {"error": "invalid_response"}
    fallback = entry.get("needs_fallback")
    if not isinstance(fallback, bool):
        return {"error": "invalid_response"}
    model = _shape(entry.get("model"), _MODEL_RE)
    choice: Any = None
    side = _probability(entry.get("noul"))
    if side is not None:
        choice = "yes" if side >= 0.5 else "no"
        top = max(side, 1.0 - side)
    elif item.get("type") == "score":
        levels, level = item.get("criteria"), entry.get("level")
        if isinstance(levels, list) and isinstance(level, str) and level.isdigit() \
                and int(level) < len(levels):
            choice = levels[int(level)]
    elif isinstance(entry.get("choice"), str) and entry["choice"] in (item.get("criteria") or {}):
        choice = entry["choice"]
    if not isinstance(choice, str):
        return {"error": "invalid_response"}
    forced = entry.get("forced") is True
    return {"choice": choice, "top": round(top, 4), "fallback": fallback, "forced": forced,
            "model": model}


def fill_columns(got: dict[str, Any], results: dict[str, Any],
                 valid: list[dict[str, Any]]) -> None:
    """Map each valid item's rung trail onto one column per backend the client's table names.

    `decided_by` is the last confident rung of the *validated* columns — a rung whose answer
    failed validation is an error column and can never be reported as the backend that
    decided the item (WR-03, 21.1 D-11).
    """
    probe = got.get("backends")
    names = [name for name in (_shape(entry.get("name"), _NAME_RE) for entry in probe
                               if isinstance(entry, dict)) if name] \
        if isinstance(probe, list) else []
    for item in valid:
        entry = results[item["id"]]
        for name in names:
            entry[name] = None
        rungs = got.get("trail", {}).get(item["id"])
        rungs = [rung for rung in rungs if isinstance(rung, dict)] \
            if isinstance(rungs, list) else []
        winner = "own_reasoning"
        for rung in rungs:
            name = rung.get("backend")
            if isinstance(name, str) and name in entry:
                column = typed_answer(rung, item)
                entry[name] = column
                if "choice" in column and column["fallback"] is False:
                    winner = name
        entry["decided_by"] = winner


# ─── the ladder ───────────────────────────────────────────────────────────────

def run_ladder(seams: Seams, client: str | None, items: list[Any],
               second_opinion: bool = False) -> dict[str, Any]:
    """One client call carries every valid item; the trail becomes the per-backend columns.

    `--second-opinion` asks the client to skip its local rungs, so every valid item goes to
    the remote rung only. Without a compatible client every item is own reasoning (SPEC R4).
    """
    valid, results, order = partition(items)
    backends: dict[str, Any] = {}
    consent_used: list[dict[str, str]] = []
    remote_available: list[str] = []
    client_status: str | None = None
    answered = False
    if client is not None and valid:
        if client_ok(client):
            got = call_client(seams, client, child_env(seams, len(valid)),
                              {"reviewed_head": reviewed_head(seams), "items": valid},
                              args=("--skip-local",) if second_opinion else ())
            if isinstance(got.get("trail"), dict):
                answered = True
                backends = public_backends(got.get("backends"))
                consent_used = public_consent_used(got.get("consent_used"))
                remote_available = public_remote_available(got.get("remote_available"))
                fill_columns(got, results, valid)
            else:
                client_status = closed_status(got)
        else:
            client_status = "incompatible_client"
    if not answered:
        for item in valid:
            results[item["id"]]["decided_by"] = "own_reasoning"
    result = {"advisory": True, "backends": backends, "client": {"found": client is not None},
              "consent_used": consent_used, "items": results, "order": order,
              "remote_available": remote_available}
    if client_status is not None:
        result["client_status"] = client_status
    return result


# ─── detect and consent: delegated ────────────────────────────────────────────

def detect(seams: Seams, override: str | None) -> dict[str, Any]:
    """Detection by label: one client `--probe`, its rows reduced to the fixed allowlist."""
    client, tried = find_client(seams.env, override)
    if client is None:
        return {"backends": {}, "client": {"path": None, "tried": tried},
                "status": "no_client"}
    if not client_ok(client):
        return {"backends": {}, "client": {"path": client, "tried": tried},
                "status": "incompatible_client"}
    got = call_client(seams, client, child_env(seams, 1), {}, args=("--probe",))
    status = got.get("status")
    return {"backends": public_backends(got.get("backends")),
            "client": {"path": client, "tried": tried},
            "status": status if isinstance(status, str) and status in _STATUS_CODES
            else "client_bad_output"}


def consent(seams: Seams, action: str, backend: str, override: str | None) -> dict[str, Any]:
    """Grant, revoke or show the consent entry: the client's record owns it (D-06)."""
    client, _ = find_client(seams.env, override)
    if client is None:
        return {"ok": False, "reason": "no_client"}
    if not client_ok(client):
        return {"ok": False, "reason": "incompatible_client"}
    got = call_client(seams, client, child_env(seams, 1), {},
                      args=("consent", action, backend))
    return public_consent_grant(got)


# ─── CLI entry (called by jev_review.py, never run directly) ──────────────────

def main(args: argparse.Namespace, seams: Seams | None = None) -> int:
    """Run `ladder`, `detect` or `consent` from jev_review.py's parsed arguments.

    Exit 0 for every advisory outcome (an empty item list included); 2 for unusable stdin.
    """
    seams = seams or real_seams()
    if args.command == "detect":
        result = detect(seams, args.client)
    elif args.command == "consent":
        result = consent(seams, args.action, args.backend, args.client)
    else:
        try:
            payload = json.load(sys.stdin)
        except (ValueError, RecursionError):
            print(json.dumps({"error": "stdin is not JSON"}), file=sys.stderr)
            return 2
        items = payload.get("items") if isinstance(payload, dict) else None
        if not isinstance(items, list):
            print(json.dumps({"error": 'stdin needs {"items": [...]}'}), file=sys.stderr)
            return 2
        client, _ = find_client(seams.env, args.client)
        result = run_ladder(seams, client, items, args.second_opinion)
    print(json.dumps(result, indent=1, sort_keys=True))
    return 0
