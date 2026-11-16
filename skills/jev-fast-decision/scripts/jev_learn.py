"""Laya version, fingerprint and the version-keyed Laya records (Phase 34 D-04..D-07).

Pure functions: the caller injects the fetcher (a callable from a URL to bytes that raises OSError
or ValueError on failure), so nothing here touches the network. Stdlib only. The stored notes are
text for an agent to read, never instructions (T-34-09). Nothing here writes a capability cell.
"""

import contextlib
import datetime
import hashlib
import json
import os
import re
import tempfile
import urllib.parse

PYPI_LATEST_URL = "https://pypi.org/pypi/laya/json"
PYPI_VERSION_URL = "https://pypi.org/pypi/laya/{version}/json"
README_URL = "https://raw.githubusercontent.com/NandhaKishorM/laya/main/README.md"
NOTES_MAX_CHARS = 4000
LAYA_RECORDS = "laya-capabilities.json"
VERSION_FIELDS = ("version", "package_version", "laya_version")
HTTP_METHODS = frozenset({"get", "put", "post", "delete", "options", "head", "patch", "trace"})
FEATURE_PATTERNS = {
    "box": re.compile(r"\bbounding[- ]box|\bbox\b", re.IGNORECASE),
    "image": re.compile(r"\bimages?\b", re.IGNORECASE),
    "images_compared": re.compile(
        r"\bcompar\w* (?:two )?images\b|\bimage comparison\b", re.IGNORECASE
    ),
    "long_context": re.compile(r"\blong[- ](?:context|documents?)\b", re.IGNORECASE),
    "batch": re.compile(r"\bbatch(?:es|ed|ing)?\b", re.IGNORECASE),
    "score": re.compile(r"\bscore\b", re.IGNORECASE),
    "choice": re.compile(r"\bchoice\b", re.IGNORECASE),
    "noul": re.compile(r"\bnoul\b|\byes/no\b", re.IGNORECASE),
}
DEFAULT_OPTIONS = {"force": False, "fetch_allowed": True, "verified": (), "now": None}


def now_iso():
    """The current UTC time, to the second."""
    return datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds")


def records_path(state_dir, name):
    """The record file under the jev folder of the state directory."""
    return os.path.join(state_dir, "jev", name)


def read_records(path):
    """The record object, or {} when the file is absent, unreadable or not an object."""
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError, RecursionError):
        return {}
    return data if isinstance(data, dict) else {}


def write_json_atomic(path, data, prefix):
    """mkstemp in the target folder plus os.replace, so a reader never sees a half-written file.
    The 0600 mkstemp mode carries over to the file. Creates no folder."""
    folder = os.path.dirname(path)
    fd, tmp = tempfile.mkstemp(dir=folder, prefix=prefix)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2, sort_keys=True)
            handle.write("\n")
        os.replace(tmp, path)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(tmp)
        raise


def write_records(path, data):
    """Create the private jev folder if needed, then write the records atomically."""
    os.makedirs(os.path.dirname(path), mode=0o700, exist_ok=True)
    write_json_atomic(path, data, ".jev-records-")


def server_version(health):
    """The first non-empty string version field of /health, or None."""
    if not isinstance(health, dict):
        return None
    for field in VERSION_FIELDS:
        value = health.get(field)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def openapi_part(openapi):
    """The OpenAPI part of the fingerprint: the info object and the sorted METHOD path list."""
    if not isinstance(openapi, dict):
        return None
    info, paths = openapi.get("info"), openapi.get("paths")
    if not isinstance(info, dict) or not isinstance(paths, dict):
        return None
    routes = sorted(
        f"{method.upper()} {path}"
        for path, item in paths.items()
        if isinstance(item, dict)
        for method in item
        if method in HTTP_METHODS
    )
    return {"info": info, "routes": routes}


def canonical_sha(doc):
    """sha256 hex of the canonical JSON of doc."""
    text = json.dumps(doc, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _idle_fingerprint(openapi_sha, records):
    """The fingerprint an idle server reuses: the newest record whose OpenAPI part matches.

    An idle server reports no loaded models, so its own fingerprint cannot be computed. Its routes
    are the same as before the unload, so the last recorded fingerprint with the same OpenAPI part
    stands in (Resolved Open Question 3). None when no record matches.
    """
    matches = [
        entry
        for entry in records.values()
        if isinstance(entry, dict)
        and entry.get("openapi_sha256") == openapi_sha
        and isinstance(entry.get("fingerprint"), str)
    ]
    if not matches:
        return None
    return max(matches, key=lambda entry: str(entry.get("checked_at", "")))["fingerprint"]


def fingerprint(health, openapi, records):
    """The route and checkpoint fingerprint of the running Laya (D-04).

    Hashes the OpenAPI part plus the loaded models and their revisions. idle_seconds and every
    other /health field stay out, so an idle unload keeps the same fingerprint.
    """
    part = openapi_part(openapi)
    if part is None:
        return {"fingerprint": None, "idle": False, "openapi_sha256": None}
    openapi_sha = canonical_sha(part)
    loaded = health.get("loaded") if isinstance(health, dict) else None
    if isinstance(loaded, list) and loaded:
        identity = {**part, "loaded": loaded, "revisions": health.get("revisions")}
        return {
            "fingerprint": canonical_sha(identity),
            "idle": False,
            "openapi_sha256": openapi_sha,
        }
    return {
        "fingerprint": _idle_fingerprint(openapi_sha, records),
        "idle": True,
        "openapi_sha256": openapi_sha,
    }


def laya_identity(server, records):
    """The version, its source and the record key of the running Laya (D-04, D-05).

    server holds the health object, the openapi object and the configured version. The record key
    is the version when one is known, else `fp:<fingerprint>`, else None.
    """
    health = server.get("health")
    fp = fingerprint(health, server.get("openapi"), records)
    version = server_version(health)
    configured = server.get("configured_version")
    if version:
        source = "server"
    elif isinstance(configured, str) and configured.strip():
        version, source = configured.strip(), "config"
    else:
        source = "not_exposed"
    key = version or (f"fp:{fp['fingerprint']}" if fp["fingerprint"] else None)
    return {"version": version, "version_source": source, **fp, "key": key}


def section(text, version):
    """The `## What's new in <version>` section of text, stripped and cut to NOTES_MAX_CHARS."""
    if not version:
        return ""
    heading = re.compile(rf"## What's new in {re.escape(version)}\b")
    lines = text.splitlines()
    start = next((index for index, line in enumerate(lines) if heading.match(line)), None)
    if start is None:
        return ""
    body = [lines[start]]
    for line in lines[start + 1 :]:
        if line.startswith("## "):
            break
        body.append(line)
    return "\n".join(body).strip()[:NOTES_MAX_CHARS]


def features_in(text):
    """The sorted feature names whose pattern appears in text."""
    return sorted(name for name, pattern in FEATURE_PATTERNS.items() if pattern.search(text))


def _pypi_info(url, text):
    """(info, None) for a PyPI JSON object with an info object, else (None, the error text)."""
    try:
        document = json.loads(text)
    except (ValueError, RecursionError) as error:
        return None, f"{url}: {type(error).__name__}"
    info = document.get("info") if isinstance(document, dict) else None
    if not isinstance(info, dict):
        return None, f"{url}: unexpected JSON shape"
    return info, None


def _read_source(url, fetch, is_pypi, version):
    """(text, latest, error) for one source: its text, the latest version a PyPI page names when
    no version is exposed, and the error that stopped it (None when it answered)."""
    try:
        raw = fetch(url)
    except (OSError, ValueError) as error:
        return None, None, f"{url}: {type(error).__name__}"
    text = raw.decode("utf-8", errors="replace")
    if not is_pypi:
        return text, None, None
    info, problem = _pypi_info(url, text)
    if info is None:
        return None, None, problem
    description = info.get("description")
    latest = info.get("version") if not version else None
    return (
        description if isinstance(description, str) else "",
        latest if isinstance(latest, str) else None,
        None,
    )


def _first_section(texts, version):
    """The first non-empty `## What's new in <version>` section over the texts, or ""."""
    return next((found for found in (section(text, version) for text in texts) if found), "")


def fetch_laya_notes(version, fetch):
    """(entry, errors) with the published notes of version, or of the latest release when no
    version is exposed, from PyPI and the README. entry is None when nothing usable came back.

    A source that failed is named in errors. With no notes found and a source failed, nothing is
    recorded: "no published notes" is not proven, so the key stays unknown (D-06, review C1-7).
    """
    if version:
        urls = [PYPI_VERSION_URL.format(version=urllib.parse.quote(version, safe=""))]
    else:
        urls = [PYPI_LATEST_URL]
    urls.append(README_URL)
    sources, texts, errors, latest = [], [], [], None
    for index, url in enumerate(urls):
        text, found_latest, problem = _read_source(url, fetch, index == 0, version)
        if problem:
            errors.append(problem)
            continue
        latest = latest or found_latest
        sources.append(url)
        texts.append(text)
    if not sources:
        return None, errors
    notes = _first_section(texts, version or latest)
    if not notes and errors:
        return None, errors
    entry = {
        "sources": sources,
        "notes": notes,
        "status": "ok" if notes else "no_published_notes",
        "features_documented": features_in(notes),
    }
    if not version:
        entry["upstream_version"] = latest
        entry["note"] = (
            "version not exposed: the latest upstream release is recorded; "
            "the running one may differ"
        )
    return entry, errors


def _short(hex_digest):
    """The first 12 hex characters of a fingerprint, or None."""
    return hex_digest[:12] if isinstance(hex_digest, str) else None


def _is_stale(old, identity):
    """True when a stored entry's fingerprint differs from the loaded one (SPEC R2 adjacency)."""
    return (
        old is not None
        and identity["fingerprint"] is not None
        and old.get("fingerprint") != identity["fingerprint"]
    )


def _laya_decision(identity, old, opts):
    """The early record word, or None when the notes should be fetched.

    Decided before any fetch, in this order (review C1-6): no key; an idle server with no matching
    fingerprint; a stored entry that still matches and no forced refresh; no fetch allowed.
    """
    if identity["key"] is None:
        return "pending_idle" if identity["idle"] and identity["openapi_sha256"] else "unknown"
    if identity["idle"] and identity["fingerprint"] is None:
        return "pending_idle"
    if old is not None and not opts["force"] and not _is_stale(old, identity):
        return "known"
    if not opts["fetch_allowed"]:
        return "skipped_deadline"
    return None


def _laya_summary(server, identity):
    """The identity fields every learn_laya result carries."""
    out = {
        "version": identity["version"],
        "version_source": identity["version_source"],
        "fingerprint": _short(identity["fingerprint"]),
        "idle": identity["idle"],
    }
    health = server.get("health")
    revisions = health.get("revisions") if isinstance(health, dict) else None
    if isinstance(revisions, dict) and revisions:
        out["revisions"] = revisions
    return out


def _notice(errors, documented):
    """One notice from up to two parts: the failed sources, then the new documented features."""
    parts = []
    if errors:
        parts.append(
            f"Laya notes source failed ({'; '.join(errors)}); "
            "recorded from the sources that answered"
        )
    if documented:
        parts.append(
            f"new Laya features documented upstream: {', '.join(documented)}; not verified here"
        )
    return "; ".join(parts)


def learn_laya(server, state_dir, fetch, options):
    """Learn the published notes of the running Laya once per key (D-05, D-06, D-07).

    Returns the identity fields and the record word: unknown, pending_idle, known, skipped_deadline,
    fetch_failed, write_failed, new, changed or refreshed. Nothing here writes a capability cell.
    """
    opts = {**DEFAULT_OPTIONS, **options}
    path = records_path(state_dir, LAYA_RECORDS)
    records = read_records(path)
    identity = laya_identity(server, records)
    key = identity["key"]
    old = records.get(key) if key else None
    old = old if isinstance(old, dict) else None
    out = _laya_summary(server, identity)
    early = _laya_decision(identity, old, opts)
    if early is not None:
        out["record"] = early
        if key and early != "pending_idle":
            out["record_key"] = key
        return out
    out["record_key"] = key
    out.update(_learn_fetch(path, identity, old, fetch, opts))
    return out


def _store(path, key, entry):
    """Write entry under key, re-reading the file first so another writer's keys survive."""
    current = read_records(path)
    current[key] = entry
    write_records(path, current)


def _learn_fetch(path, identity, old, fetch, opts):
    """Fetch the notes for a key that needs them, record them and return the outcome fields."""
    entry, errors = fetch_laya_notes(identity["version"], fetch)
    if entry is None:
        return {
            "record": "fetch_failed",
            "notice": f"Laya notes fetch failed ({'; '.join(errors)}); previous records kept",
        }
    entry.update(
        checked_at=opts["now"] or now_iso(),
        fingerprint=identity["fingerprint"],
        openapi_sha256=identity["openapi_sha256"],
        version_source=identity["version_source"],
    )
    result = {}
    stale = _is_stale(old, identity)
    if opts["force"]:
        result["record"] = "refreshed"
    elif stale:
        result["record"] = "changed"
        result["previous_fingerprint"] = _short((old or {}).get("fingerprint"))
    else:
        result["record"] = "new"
    try:
        _store(path, identity["key"], entry)
    except OSError:
        return {"record": "write_failed"}
    documented = [name for name in entry["features_documented"] if name not in opts["verified"]]
    if documented:
        result["documented_upstream"] = documented
    notice = _notice(errors, documented)
    if notice:
        result["notice"] = notice
    return result
