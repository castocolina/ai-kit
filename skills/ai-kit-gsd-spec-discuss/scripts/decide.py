#!/usr/bin/env python3
"""Decision ladder: Laya (local, one item per call) -> TypeSafe (remote, batched) -> own reasoning.

stdlib only. Calls the installed jev-fast-decision client; never copies its protocol. Never
prints a key value: detection reports key sources by label only. Every answer is advisory.

    decide.py detect
    decide.py ladder [--second-opinion] < {"items": [...]}
    decide.py consent grant|revoke|show <typesafe|laya>
"""

from __future__ import annotations

import argparse
import datetime
import ipaddress
import json
import os
import re
import socket
import subprocess
import sys
import tempfile
from collections.abc import Callable, Mapping
from typing import Any, NamedTuple
from urllib.parse import urlsplit

TYPESAFE_URL = "https://api.typesafe.ai/v1/systemone"
BACKEND_ENV = {
    "laya": {"JEV_MODEL": "jev-1", "JEV_RESPONSE_MODEL": "laya-rl-agent"},
    "typesafe": {"JEV_API_URL": TYPESAFE_URL, "JEV_MODEL": "jev-latest",
                 "JEV_RESPONSE_MODEL": "jev-1.13.0"},
}
CALL_TIMEOUT_SECONDS = "30"
MIN_CONFIDENCE = "0.7"
CONNECT_TIMEOUT_SECONDS = 2.0
ZERO_HEAD = "0" * 40
CLIENT_REL = os.path.join("jev-fast-decision", "scripts", "jev_review.py")
# Inherited variables the client would otherwise read (a parent-shell key must never reach Laya).
_SCRUB_PREFIXES = ("JEV_", "GSD_PATH_JEV")
_SCRUB_NAMES = {"OPENCODE_API_KEY", "AI_KIT_LAYA_URL", "AI_KIT_JEV_CLIENT"}

ITEM_KEYS = {"id", "type", "instructions", "context", "criteria"}
ITEM_TYPES = {"choice", "noul"}
MAX_FIELD_CHARS = 1500
# Defense in depth, not a guarantee: obvious key shapes and long opaque base64 runs (48+ so a
# 40-char commit SHA in a summary still passes). A false positive only means own reasoning.
_SECRET_RE = re.compile(r"-----BEGIN|\b(?:sk|pk|ghp|gho|xox[abp])[-_][A-Za-z0-9_-]{12,}|"
                        r"[A-Za-z0-9+/]{48,}")


class Seams(NamedTuple):
    """Injected side effects, so tests never touch the network, real config or a real client."""

    env: Mapping[str, str]
    run: Callable[..., Any]
    connect: Callable[..., Any]


def real_seams() -> Seams:
    """The production side effects."""
    return Seams(env=os.environ, run=subprocess.run, connect=socket.create_connection)


# ─── configuration and detection ──────────────────────────────────────────────

def config_dir(env: Mapping[str, str]) -> str:
    """ai-kit's per-user config dir: ${XDG_CONFIG_HOME:-~/.config}/ai-kit."""
    base = env.get("XDG_CONFIG_HOME", "").strip() or os.path.join(env.get("HOME", "~"), ".config")
    return os.path.join(os.path.expanduser(base), "ai-kit")


def is_loopback(host: str | None) -> bool:
    """True for localhost and loopback IPs only."""
    if not host:
        return False
    if host.lower() == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def laya_url(env: Mapping[str, str]) -> tuple[str | None, str | None]:
    """(url, source). JEV_API_URL counts only when loopback: it is also the client's target var."""
    dedicated = env.get("AI_KIT_LAYA_URL", "").strip()
    if dedicated:
        return dedicated, "AI_KIT_LAYA_URL"
    shared = env.get("JEV_API_URL", "").strip()
    if shared and is_loopback(urlsplit(shared).hostname):
        return shared, "JEV_API_URL"
    return None, None


def reachable(url: str, connect: Callable[..., Any]) -> bool:
    """TCP reachability of the URL's host and port; proves nothing about the protocol."""
    parts = urlsplit(url)
    if not parts.hostname:
        return False
    port = parts.port or (443 if parts.scheme == "https" else 80)
    try:
        connect((parts.hostname, port), timeout=CONNECT_TIMEOUT_SECONDS).close()
    except OSError:
        return False
    return True


def _secrets_env_value(path: str, name: str) -> str | None:
    """Flat KEY=VALUE parser (adapted from ai_kit_spec.local_secrets; this skill ships alone)."""
    try:
        with open(path, encoding="utf-8") as handle:
            lines = handle.read().splitlines()
    except OSError:
        return None
    for line in lines:
        key, sep, value = line.strip().partition("=")
        if sep and key.strip() == name and not key.lstrip().startswith("#"):
            return value.strip().strip("'\"") or None
    return None


def typesafe_key(env: Mapping[str, str]) -> tuple[str | None, str | None]:
    """(value, source label). Callers print only the label."""
    value = env.get("JEV_API_KEY", "").strip()
    if value:
        return value, "env"
    key_file = env.get("JEV_API_KEY_FILE", "").strip()
    if key_file:
        try:
            with open(os.path.expanduser(key_file), encoding="utf-8") as handle:
                value = handle.read().strip()
        except OSError:
            value = ""
        if value:
            return value, "key_file"
    value = _secrets_env_value(os.path.join(config_dir(env), "secrets.env"), "JEV_API_KEY") or ""
    return (value, "secrets_env") if value else (None, None)


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


# ─── consent ──────────────────────────────────────────────────────────────────

def consent_path(env: Mapping[str, str]) -> str:
    """The per-user consent record."""
    return os.path.join(config_dir(env), "jev-consent.json")


def read_consent(env: Mapping[str, str]) -> dict[str, Any]:
    """The consent record, or {} when absent or unreadable."""
    try:
        with open(consent_path(env), encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def write_consent(env: Mapping[str, str], data: dict[str, Any]) -> None:
    """Atomic write (mkstemp + os.replace)."""
    path = consent_path(env)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), prefix=".jev-consent-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2, sort_keys=True)
            handle.write("\n")
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def backend_host(backend: str, env: Mapping[str, str]) -> str | None:
    """The endpoint host a consent entry is bound to."""
    if backend == "typesafe":
        return urlsplit(TYPESAFE_URL).hostname
    url, _ = laya_url(env)
    return urlsplit(url).hostname if url else None


def consent_date(env: Mapping[str, str], backend: str) -> str | None:
    """Consent is keyed by backend and endpoint host: a moved endpoint needs new consent."""
    entry = read_consent(env).get(backend)
    if isinstance(entry, dict) and entry.get("host") == backend_host(backend, env):
        granted = entry.get("granted")
        return granted if isinstance(granted, str) else None
    return None


# ─── items and calls ──────────────────────────────────────────────────────────

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
    criteria = item.get("criteria")
    if item["type"] == "choice" and (not isinstance(criteria, dict) or len(criteria) < 2):
        return "choice_needs_two_criteria"
    if criteria is not None and (not isinstance(criteria, dict) or any(
            _bad_text(text) for text in criteria.values())):
        return "bad_criteria"
    return None


def item_error(item: Any) -> str | None:
    """Reason code when an item must not be sent anywhere, else None."""
    if not isinstance(item, dict) or not isinstance(item.get("id"), str) or not item["id"]:
        return "missing_id"
    if set(item) - ITEM_KEYS:
        return "unknown_key"
    if item.get("type") not in ITEM_TYPES:
        return "bad_type"
    for field in ("instructions", "context"):
        reason = _bad_text(item.get(field))
        if reason:
            return f"{reason}_{field}"
    return _criteria_error(item)


def child_env(seams: Seams, backend: str, url: str, key: str | None) -> dict[str, str]:
    """The client env for one backend: inherited JEV_*/OPENCODE_API_KEY dropped first."""
    env = {name: value for name, value in seams.env.items()
           if not name.startswith(_SCRUB_PREFIXES) and name not in _SCRUB_NAMES}
    env.update(BACKEND_ENV[backend])
    env.update({"JEV_API_URL": url, "GSD_PATH_JEV": "1",
                "GSD_PATH_JEV_TIMEOUT_SECONDS": CALL_TIMEOUT_SECONDS,
                "JEV_MIN_CONFIDENCE": MIN_CONFIDENCE})
    if key:
        env["JEV_API_KEY"] = key
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


def call_client(seams: Seams, client: str, env: dict[str, str],
                payload: dict[str, Any]) -> dict[str, Any]:
    """Run the jev client; return its parsed JSON or a closed-set failure. Raw output is dropped."""
    try:
        out = seams.run([sys.executable, "-B", client], input=json.dumps(payload),
                        capture_output=True, text=True, env=env, check=False,
                        timeout=float(CALL_TIMEOUT_SECONDS) + 10)
    except subprocess.TimeoutExpired:
        return {"status": "unavailable", "reason": "client_timeout"}
    except OSError:
        return {"status": "unavailable", "reason": "client_not_runnable"}
    try:
        result = json.loads(out.stdout)
    except (TypeError, ValueError):
        return {"status": "unavailable", "reason": "client_bad_output"}
    return result if isinstance(result, dict) else {"status": "unavailable",
                                                    "reason": "client_bad_output"}


def typed_answer(answer: Any) -> dict[str, Any]:
    """Re-emit only typed fields: choice, winning probability, fallback flag."""
    if not isinstance(answer, dict):
        return {"error": "invalid_response"}
    if answer.get("type") == "noul" and isinstance(answer.get("noul"), (int, float)):
        p = float(answer["noul"])
        choice, top = ("yes", p) if p >= 0.5 else ("no", 1 - p)
    elif isinstance(answer.get("probabilities"), dict) and isinstance(answer.get("choice"), str):
        probabilities = answer["probabilities"].values()
        if not all(isinstance(value, (int, float)) for value in probabilities):
            return {"error": "invalid_response"}
        choice, top = answer["choice"], float(max(probabilities))
    else:
        return {"error": "invalid_response"}
    return {"choice": choice, "top": round(top, 4), "fallback": bool(answer.get("needs_fallback"))}


def answers_for(result: dict[str, Any], ids: list[str]) -> dict[str, dict[str, Any]]:
    """Per-id typed answers from one client result; a failed call marks every id with its reason."""
    if result.get("status") != "ok":
        reason = result.get("reason") if isinstance(result.get("reason"), str) else "unavailable"
        return {identifier: {"error": reason} for identifier in ids}
    answers = result.get("answers")
    answers = answers if isinstance(answers, dict) else {}
    return {identifier: typed_answer(answers.get(identifier)) for identifier in ids}


# ─── the ladder ───────────────────────────────────────────────────────────────

def backend_status(seams: Seams) -> dict[str, dict[str, Any]]:
    """Which backends are usable, and why not; carries the key internally, never printed."""
    url, source = laya_url(seams.env)
    laya: dict[str, Any] = {"url_source": source, "usable": False}
    if not url:
        laya["skip"] = "not_configured"
    elif not reachable(url, seams.connect):
        laya["skip"] = "unreachable"
    elif not is_loopback(urlsplit(url).hostname) and not consent_date(seams.env, "laya"):
        laya["skip"] = "no_consent"
    else:
        laya.update(usable=True, url=url)
    key, key_source = typesafe_key(seams.env)
    typesafe: dict[str, Any] = {"key_source": key_source, "usable": False}
    if not key:
        typesafe["skip"] = "no_key"
    elif not consent_date(seams.env, "typesafe"):
        typesafe["skip"] = "no_consent"
    else:
        typesafe.update(usable=True, key=key)
    return {"laya": laya, "typesafe": typesafe}


def needs_typesafe(entry: dict[str, Any], second_opinion: bool) -> bool:
    """Laya missing, errored or low-confidence (or a forced second opinion)."""
    laya = entry["laya"]
    return second_opinion or laya is None or "error" in laya or laya["fallback"]


def decided_by(entry: dict[str, Any]) -> str:
    """The confident rung that settles an item; own reasoning when none is confident."""
    for backend in ("typesafe", "laya"):
        answer = entry[backend]
        if answer and "error" not in answer and not answer["fallback"]:
            return backend
    return "own_reasoning"


def partition(items: list[Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Valid items, plus result rows: rejected items carry their reason and never leave."""
    valid, results = [], {}
    for index, item in enumerate(items):
        reason = item_error(item)
        if reason:
            identifier = item.get("id") if isinstance(item, dict) and item.get("id") else ""
            results[str(identifier or f"#{index}")] = {
                "error": "invalid_input", "reason": reason, "decided_by": "own_reasoning"}
        else:
            valid.append(item)
            results[item["id"]] = {"laya": None, "typesafe": None}
    return valid, results


def run_ladder(seams: Seams, client: str | None, items: list[Any],
               second_opinion: bool = False) -> dict[str, Any]:
    """Laya per item, then one TypeSafe batch of low or errored items (all, if second opinion)."""
    status = backend_status(seams)
    valid, results = partition(items)
    head = reviewed_head(seams)
    if client and status["laya"]["usable"] and not second_opinion:
        env = child_env(seams, "laya", status["laya"]["url"], None)
        for item in valid:  # one call per item: Laya reads the whole state, so contexts bleed
            got = call_client(seams, client, env, {"reviewed_head": head, "items": [item]})
            results[item["id"]]["laya"] = answers_for(got, [item["id"]])[item["id"]]
    todo = [item for item in valid if needs_typesafe(results[item["id"]], second_opinion)]
    if client and status["typesafe"]["usable"] and todo:
        env = child_env(seams, "typesafe", TYPESAFE_URL, status["typesafe"]["key"])
        got = call_client(seams, client, env, {"reviewed_head": head, "items": todo})
        for identifier, answer in answers_for(got, [item["id"] for item in todo]).items():
            results[identifier]["typesafe"] = answer
    for item in valid:
        results[item["id"]]["decided_by"] = decided_by(results[item["id"]])
    public = {name: {k: v for k, v in info.items() if k not in ("key", "url")}
              for name, info in status.items()}
    public["client"] = {"found": bool(client)}
    return {"advisory": True, "backends": public, "items": results}


def detect(seams: Seams, override: str | None) -> dict[str, Any]:
    """Detection report by label: no key values, no URL credentials."""
    client, tried = find_client(seams.env, override)
    status = backend_status(seams)
    url, _ = laya_url(seams.env)
    laya = {k: v for k, v in status["laya"].items() if k != "url"}
    if url:
        laya["endpoint"] = urlsplit(url).netloc.rpartition("@")[2]
        laya["note"] = "TCP reachability only, not verified as a System One server"
    typesafe = {k: v for k, v in status["typesafe"].items() if k != "key"}
    for name, info in (("laya", laya), ("typesafe", typesafe)):
        info["consent"] = consent_date(seams.env, name)
    return {"laya": laya, "typesafe": typesafe,
            "client": {"path": client, "tried": tried}}


def consent(seams: Seams, action: str, backend: str) -> dict[str, Any]:
    """Grant, revoke or show the consent entry for one remote backend."""
    host = backend_host(backend, seams.env)
    data = read_consent(seams.env)
    if action == "grant":
        if not host:
            return {"ok": False, "reason": "no_endpoint_configured"}
        data[backend] = {"host": host, "granted": datetime.date.today().isoformat()}
        write_consent(seams.env, data)
    elif action == "revoke" and backend in data:
        del data[backend]
        write_consent(seams.env, data)
    return {"ok": True, "backend": backend, "host": host,
            "consent": consent_date(seams.env, backend), "file": consent_path(seams.env)}


# ─── CLI ──────────────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    """The CLI."""
    parser = argparse.ArgumentParser(
        prog="decide.py", description=(__doc__ or "").split("\n", 1)[0])
    parser.add_argument("--client", help="path to jev_review.py (else AI_KIT_JEV_CLIENT, roots)")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("detect", help="report backends by label; never prints a key")
    ladder = sub.add_parser("ladder", help='read {"items":[...]} on stdin')
    ladder.add_argument("--second-opinion", action="store_true",
                        help="send every valid item to TypeSafe only")
    grant = sub.add_parser("consent", help="record, revoke or show remote-backend consent")
    grant.add_argument("action", choices=("grant", "revoke", "show"))
    grant.add_argument("backend", choices=("typesafe", "laya"))
    return parser


def main(argv: list[str] | None = None, seams: Seams | None = None) -> int:
    """Exit 0 for every advisory outcome; 2 for unusable stdin."""
    args = build_parser().parse_args(argv)
    seams = seams or real_seams()
    if args.command == "detect":
        result = detect(seams, args.client)
    elif args.command == "consent":
        result = consent(seams, args.action, args.backend)
    else:
        try:
            payload = json.load(sys.stdin)
        except ValueError:
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
