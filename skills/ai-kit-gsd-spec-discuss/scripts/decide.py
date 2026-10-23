#!/usr/bin/env python3
"""Thin caller of the shared jev-fast-decision client: one client call per ladder run.

This file holds no endpoint URL, no model id and no backend order. The backend table lives
entirely in the client, which owns the ladder (local rungs first, one item per call, then one
consented remote batch) and returns a per-item rung trail; decide.py maps that trail onto one
column per table backend and keeps only item validation (summaries only), the scrubbed child
environment, `detect`, `--second-opinion` and the consent delegation. stdlib only. Never
prints a key value: every client JSON field passes a fixed allowlist before it reaches stdout.
Every answer is advisory.

    decide.py detect
    decide.py ladder [--second-opinion] < {"items": [...]}
    decide.py consent grant|revoke|show <backend>
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from collections.abc import Callable, Mapping
from typing import Any, NamedTuple

CLIENT_REL = os.path.join("jev-fast-decision", "scripts", "jev_review.py")
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
# Defense in depth, not a guarantee: obvious key shapes and long opaque base64 runs (48+ so a
# 40-char commit SHA in a summary still passes). A false positive only means own reasoning.
_SECRET_RE = re.compile(r"-----BEGIN|\b(?:sk|pk|ghp|gho|xox[abp])[-_][A-Za-z0-9_-]{12,}|"
                        r"[A-Za-z0-9+/]{48,}")
# Fixed output allowlists (24 D-13): a leaky client's extra fields never reach stdout.
_BACKEND_KEYS = ("name", "remote", "batch", "host", "usable", "reason", "key_source", "consent",
                 "key_check")
_CONSENT_KEYS = ("ok", "backend", "host", "consent", "file", "note", "reason")
_SCALAR_TYPES = (str, bool, int)


class Seams(NamedTuple):
    """Injected side effects, so tests never touch the network, real config or a real client."""

    env: Mapping[str, str]
    run: Callable[..., Any]


def real_seams() -> Seams:
    """The production side effects."""
    return Seams(env=os.environ, run=subprocess.run)


# ─── client discovery ─────────────────────────────────────────────────────────

def client_candidates(env: Mapping[str, str], override: str | None) -> list[str]:
    """Where the jev client may live, in lookup order."""
    home = env.get("HOME", "~")
    xdg = env.get("XDG_CONFIG_HOME", "").strip() or os.path.join(home, ".config")
    # abspath, never realpath: the skill is symlinked into the host's skills dir, beside jev.
    own_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    roots = [
        own_root,
        os.path.join(env.get("CLAUDE_CONFIG_DIR", "").strip() or os.path.join(home, ".claude"),
                     "skills"),
        os.path.join(home, ".agents", "skills"),
        os.path.join(xdg, "opencode", "skills"),
        os.path.join(env.get("CURSOR_CONFIG_DIR", "").strip() or os.path.join(home, ".cursor"),
                     "skills"),
        os.path.join(env.get("PI_CODING_AGENT_DIR", "").strip()
                     or os.path.join(home, ".pi", "agent"), "skills"),
    ]
    explicit = override or env.get("AI_KIT_JEV_CLIENT", "").strip()
    found = [os.path.expanduser(explicit)] if explicit else []
    return found + [os.path.expanduser(os.path.join(root, CLIENT_REL)) for root in roots]


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

def _bad_text(value: Any) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return "empty"
    if len(value) > MAX_FIELD_CHARS:
        return "too_long"
    if "```" in value:
        return "code_fence"
    if _SECRET_RE.search(value):
        return "secret_pattern"
    return None


def _criteria_error(item: dict[str, Any]) -> str | None:
    """`criteria` is validated against the client's builder (present, even null, or missing).

    decide.py rejects, alone and before the one combined call, every shape the client would
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


def item_error(item: Any) -> str | None:
    """Reason code when an item must not be sent anywhere, else None."""
    if (not isinstance(item, dict) or not isinstance(item.get("id"), str)
            or not item["id"].strip()):
        return "missing_id"
    if item["id"].startswith("#"):
        # Reserved for decide.py's own rejection keys: an input id here could collide with
        # the `#<stdin index>` key of a later rejected item.
        return "reserved_id"
    if set(item) - ITEM_KEYS:
        return "unknown_key"
    if item.get("type") not in ITEM_TYPES:
        return "bad_type"
    for field in ("instructions", "context"):
        reason = _bad_text(item.get(field))
        if reason:
            return f"{reason}_{field}"
    return _criteria_error(item)


def partition(items: list[Any]) -> tuple[list[dict[str, Any]], dict[str, Any], list[str]]:
    """(valid items, result rows, stdin-order keys). Rejected items never leave; every later
    item whose id already appeared — valid or not — is `duplicate_id`, and a rejected item
    with a blank, repeated or reserved id is keyed `#<stdin index>` so the first occurrence
    keeps its row and a rejection key never equals a legal id."""
    valid, results, order = [], {}, []
    seen: set[str] = set()
    for index, item in enumerate(items):
        reason = item_error(item)
        identifier = item.get("id") if isinstance(item, dict) else None
        identifier = identifier if isinstance(identifier, str) and identifier.strip() else ""
        if not reason and identifier in seen:
            reason = "duplicate_id"
        if reason:
            own_key = (identifier and not identifier.startswith("#")
                       and identifier not in seen)
            key = identifier if own_key else f"#{index}"
            results[key] = {"error": "invalid_input", "reason": reason,
                            "decided_by": "own_reasoning"}
            order.append(key)
            if identifier:
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


def public_backends(probe_list: Any) -> dict[str, dict[str, Any]]:
    """The client's probe rows reduced to a fixed allowlist of scalar label fields.

    A filtered pass-through, not: a compatible-but-leaky client's extra fields (a debug env,
    a key copy) never reach stdout, whatever their names happen to be.
    """
    public = {}
    for entry in probe_list if isinstance(probe_list, list) else []:
        if not isinstance(entry, dict) or not isinstance(entry.get("name"), str):
            continue
        row = {key: entry[key] for key in _BACKEND_KEYS if key in entry and _scalar(entry[key])}
        row["status"] = "usable" if row.get("usable") else str(row.get("reason") or "unusable")
        public[entry["name"]] = row
    return public


def public_consent_used(raw: Any) -> list[dict[str, str]]:
    """`[{backend, granted}]` string pairs only, so an announcement can name saved consent."""
    used = []
    for entry in raw if isinstance(raw, list) else []:
        if (isinstance(entry, dict) and isinstance(entry.get("backend"), str)
                and isinstance(entry.get("granted"), str)):
            used.append({"backend": entry["backend"], "granted": entry["granted"]})
    return used


def public_remote_available(raw: Any) -> list[str]:
    """Backend names only: the rows a consent question is owed to."""
    if not isinstance(raw, list):
        return []
    return [entry for entry in raw if isinstance(entry, str)]


def public_consent(got: dict[str, Any]) -> dict[str, Any]:
    """The client's consent result reduced to the seven scalar announcement fields."""
    if not isinstance(got.get("ok"), bool):
        return {"ok": False, "reason": "client_bad_output"}
    return {key: got[key] for key in _CONSENT_KEYS if key in got and _scalar(got[key])}


# ─── the one client call ──────────────────────────────────────────────────────

def child_env(seams: Seams, n_items: int) -> dict[str, str]:
    """The child env: control variables scrubbed, decide.py's own bounds set.

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
    """The closed-set status string of a client result that carried no trail."""
    status = got.get("status")
    return status if isinstance(status, str) else "unavailable"


# ─── trail mapping ────────────────────────────────────────────────────────────

def typed_answer(entry: Any, item: Mapping[str, Any]) -> dict[str, Any]:
    """One trail rung reduced to the caller's column: {choice, top, fallback, model} or {error}.

    A score or choice pick is always one of `item`'s own criteria — the level text for a score,
    the key for a choice — never backend text, which could be unbounded or an injection."""
    if not isinstance(entry, dict):
        return {"error": "invalid_response"}
    error = entry.get("error")
    if error is not None:
        return {"error": error if isinstance(error, str) else "invalid_response"}
    top = entry.get("top")
    if not isinstance(top, (int, float)) or isinstance(top, bool):
        return {"error": "invalid_response"}
    fallback = bool(entry.get("needs_fallback"))
    model = entry.get("model") if isinstance(entry.get("model"), str) else None
    choice: Any = None
    noul = entry.get("noul")
    if isinstance(noul, (int, float)) and not isinstance(noul, bool):
        side = float(noul)
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
    return {"choice": choice, "top": round(float(top), 4), "fallback": fallback, "model": model}


def decided_by(trail: list[Any]) -> str:
    """The backend of the last confident rung of the trail, else own reasoning (D-11)."""
    winner = "own_reasoning"
    for rung in trail:
        if (isinstance(rung, dict) and "error" not in rung
                and rung.get("needs_fallback") is False
                and isinstance(rung.get("backend"), str)):
            winner = rung["backend"]
    return winner


def fill_columns(got: dict[str, Any], results: dict[str, Any],
                 valid: list[dict[str, Any]]) -> None:
    """Map each valid item's rung trail onto one column per backend the client's table names."""
    probe = got.get("backends")
    names = [entry["name"] for entry in probe
             if isinstance(entry, dict) and isinstance(entry.get("name"), str)] \
        if isinstance(probe, list) else []
    for item in valid:
        entry = results[item["id"]]
        for name in names:
            entry[name] = None
        rungs = got.get("trail", {}).get(item["id"])
        rungs = [rung for rung in rungs if isinstance(rung, dict)] \
            if isinstance(rungs, list) else []
        for rung in rungs:
            name = rung.get("backend")
            if name in entry:
                entry[name] = typed_answer(rung, item)
        entry["decided_by"] = decided_by(rungs)


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
            "status": status if isinstance(status, str) else "client_bad_output"}


def consent(seams: Seams, action: str, backend: str, override: str | None) -> dict[str, Any]:
    """Grant, revoke or show the consent entry: the client's record owns it (D-06)."""
    client, _ = find_client(seams.env, override)
    if client is None:
        return {"ok": False, "reason": "no_client"}
    if not client_ok(client):
        return {"ok": False, "reason": "incompatible_client"}
    got = call_client(seams, client, child_env(seams, 1), {},
                      args=("consent", action, backend))
    return public_consent(got)


# ─── CLI ──────────────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    """The CLI."""
    parser = argparse.ArgumentParser(
        prog="decide.py", description=(__doc__ or "").split("\n", 1)[0])
    parser.add_argument("--client", help="path to jev_review.py (else AI_KIT_JEV_CLIENT, roots)")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("detect", help="report the client's backend table by label; never a key")
    ladder = sub.add_parser("ladder", help='read {"items":[...]} on stdin')
    ladder.add_argument("--second-opinion", action="store_true",
                        help="skip the local rungs: every valid item goes remote only")
    grant = sub.add_parser("consent", help="record, revoke or show remote-backend consent")
    grant.add_argument("action", choices=("grant", "revoke", "show"))
    grant.add_argument("backend", help="a backend name from the client's table; it validates")
    return parser


def main(argv: list[str] | None = None, seams: Seams | None = None) -> int:
    """Exit 0 for every advisory outcome; 2 for unusable stdin."""
    args = build_parser().parse_args(argv)
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
        if not isinstance(items, list) or not items:
            print(json.dumps({"error": 'stdin needs {"items": [...]} with at least one item'}),
                  file=sys.stderr)
            return 2
        client, _ = find_client(seams.env, args.client)
        result = run_ladder(seams, client, items, args.second_opinion)
    print(json.dumps(result, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
