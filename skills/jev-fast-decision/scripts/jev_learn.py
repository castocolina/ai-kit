"""Laya version, fingerprint and the version-keyed Laya records (Phase 34 D-04..D-07), and the
TypeSafe model records (SPEC R4): a pending note per new model id and one doc-flow read per id.

Pure functions: the caller injects the fetcher (a callable from a URL to bytes that raises OSError
or ValueError on failure), so nothing here touches the network. Stdlib only. The stored notes are
text for an agent to read, never instructions (T-34-09). Nothing here writes a capability cell.
"""

import contextlib
import datetime
import hashlib
import importlib.util
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
MODEL_RECORDS = "typesafe-models.json"
DOCS_PREFIX = "https://docs.typesafe.ai/"
DOCS_INDEX_URL = "https://docs.typesafe.ai/llms.txt"
DOCS_CHANGELOG_URL = "https://docs.typesafe.ai/changelog.md"
DOCS_MODELS_URL = "https://docs.typesafe.ai/models.md"
SERVES = ("box", "image", "long_context", "batch")
KNOWN_PRIMITIVES = ("choice", "noul", "score", "box")
_VERSIONED_ID = re.compile(r"jev-\d+(?:\.\d+)+(?:-[A-Za-z0-9.]+)?")
_LINK = re.compile(r"\[[^\]]*\]\((https://[^)\s]+)\)")
_HEADING = ("**", "#")
_UNKNOWN_NAME = re.compile(r"(?:primitive|option):[A-Za-z][A-Za-z0-9_.-]{0,63}")
_UNKNOWN_LIMIT = 16


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


def note_model(state_dir, model_id, now=None):
    """Note a versioned model id an answer reported, as a local pending entry (D-09, SPEC R4).

    Writes only status and first_seen, with no network call. False for an alias, a missing id, an id
    already recorded or a failed write: the answer path never fails on a state write.
    """
    if not isinstance(model_id, str) or not _VERSIONED_ID.fullmatch(model_id):
        return False
    path = records_path(state_dir, MODEL_RECORDS)
    records = read_records(path)
    if model_id in records:
        return False
    records[model_id] = {"status": "pending", "first_seen": now or now_iso()}
    try:
        write_records(path, records)
    except OSError:
        return False
    return True


def latest_model(records):
    """The model id with the greatest first_seen, any status; None when there is none."""
    seen = [
        (entry["first_seen"], key)
        for key, entry in records.items()
        if isinstance(entry, dict) and isinstance(entry.get("first_seen"), str)
    ]
    return max(seen)[1] if seen else None


def doc_links(index_text):
    """basename -> url for every link under DOCS_PREFIX in the llms.txt index, first one wins.

    Links off the docs site are ignored, so an index cannot redirect a fetch (T-34-16).
    """
    links = {}
    for url in _LINK.findall(index_text):
        if url.startswith(DOCS_PREFIX):
            links.setdefault(url.rsplit("/", 1)[-1], url)
    return links


def _get_page(url, fetch, sources, errors):
    """The decoded text of one doc page, or None. The URL joins sources or errors."""
    try:
        raw = fetch(url)
    except (OSError, ValueError) as error:
        errors.append(f"{url}: {type(error).__name__}")
        return None
    sources.append(url)
    return raw.decode("utf-8", errors="replace")


def fetch_model_docs(fetch):
    """(texts, sources, errors) of the official doc flow: llms.txt, then changelog.md and models.md.

    The two content pages take their URL from the index when it links them under DOCS_PREFIX, else
    the fixed defaults. texts holds only the pages that arrived, under index, changelog and models.
    """
    texts, sources, errors = {}, [], []
    index = _get_page(DOCS_INDEX_URL, fetch, sources, errors)
    links = {}
    if index is not None:
        texts["index"] = index
        links = doc_links(index)
    pages = (
        ("changelog", "changelog.md", DOCS_CHANGELOG_URL),
        ("models", "models.md", DOCS_MODELS_URL),
    )
    for key, name, default in pages:
        page = _get_page(links.get(name, default), fetch, sources, errors)
        if page is not None:
            texts[key] = page
    return texts, sources, errors


def model_notes(changelog, model_id):
    """The changelog block that names model_id: from the nearest heading at or before its line up to
    the next heading, stripped and cut to NOTES_MAX_CHARS. "" when the id is absent."""
    lines = changelog.splitlines()
    at = next((i for i, line in enumerate(lines) if f"`{model_id}`" in line), None)
    if at is None:
        return ""
    start = max((i for i in range(at + 1) if lines[i].startswith(_HEADING)), default=at)
    end = next(
        (i for i in range(at + 1, len(lines)) if lines[i].startswith(_HEADING)), len(lines)
    )
    return "\n".join(lines[start:end]).strip()[:NOTES_MAX_CHARS]


def _row_cells(line):
    """The stripped cells of a Markdown table row, without the empty ends."""
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def model_primitives(models_text, model_id):
    """The sorted, lowercased question types the models table documents for model_id.

    [] when the id's row or the question-types row is missing.
    """
    rows = [_row_cells(line) for line in models_text.splitlines() if line.startswith("|")]
    token = f"`{model_id}`"
    id_row = next((cells for cells in rows if token in cells), None)
    types_row = next(
        (cells for cells in rows if cells and cells[0].lower() == "question types"), None
    )
    if id_row is None or types_row is None:
        return []
    column = id_row.index(token)
    if column >= len(types_row):
        return []
    return sorted({p.strip().lower() for p in types_row[column].split(",") if p.strip()})


def model_entry(model_id, texts, sources):
    """The recorded fields of one model id, taken from the doc pages that arrived."""
    notes = model_notes(texts.get("changelog", ""), model_id)
    primitives = model_primitives(texts.get("models", ""), model_id)
    return {
        "status": "recorded",
        "sources": sources,
        "notes": notes,
        "primitives_documented": primitives,
        "new_primitives": [p for p in primitives if p not in KNOWN_PRIMITIVES],
        "serves": [f for f in features_in(notes) if f in SERVES],
    }


def _model_targets(records, latest, force):
    """The pending model ids, plus the latest recorded id when a forced refresh asks for it."""
    targets = [
        key
        for key, entry in records.items()
        if isinstance(entry, dict) and entry.get("status") == "pending"
    ]
    if force and latest is not None and latest not in targets:
        targets.append(latest)
    return sorted(targets)


def _unknown_seen(entry):
    """The unknown names a record entry holds, as strings."""
    seen = entry.get("unknown_seen")
    return [name for name in seen if isinstance(name, str)] if isinstance(seen, list) else []


def _documented_unknowns(names, texts):
    """The names whose part after the colon appears as a whole word in the changelog or models."""
    pages = (texts.get("changelog", ""), texts.get("models", ""))
    documented = []
    for name in names:
        word = re.compile(rf"\b{re.escape(name.split(':', 1)[1])}\b", re.IGNORECASE)
        if any(word.search(page) for page in pages):
            documented.append(name)
    return documented


def _model_result(targets, entries, records, docs, force):
    """The outcome of a recorded doc read: the ids, what they could serve and the notice."""
    texts, _sources, errors = docs
    serves = sorted({f for entry in entries.values() for f in entry["serves"]})
    new = sorted({p for entry in entries.values() for p in entry["new_primitives"]})
    notice = [
        f"TypeSafe model {', '.join(targets)} documented upstream, not verified here: "
        f"could serve {', '.join(serves) or 'no listed feature'}; "
        f"new primitives: {', '.join(new) or 'none'}"
    ]
    result = {
        "model_record": "refreshed" if force else "new",
        "model_ids": targets,
        "serves": serves,
        "new_primitives": new,
    }
    unknown = sorted({name for target in targets for name in _unknown_seen(records[target])})
    if unknown:
        documented = _documented_unknowns(unknown, texts)
        result.update(unknown_seen=unknown, unknown_documented=documented)
        notice.append(
            f"met here but unknown to the skill: {', '.join(unknown)} "
            f"(documented upstream: {', '.join(documented) or 'none'})"
        )
    if any(error.startswith(DOCS_INDEX_URL) for error in errors):
        notice.append("llms.txt not read, default doc URLs used")
    result["notice"] = "; ".join(notice)
    return result


def _record_models(path, targets, docs, opts):
    """Write each target's recorded entry over its old one, keeping first_seen, then report it."""
    texts, sources, _errors = docs
    entries = {target: model_entry(target, texts, sources) for target in targets}
    records = read_records(path)
    now = opts["now"] or now_iso()
    for target, entry in entries.items():
        old = records.get(target)
        records[target] = {**(old if isinstance(old, dict) else {}), **entry, "checked_at": now}
    try:
        write_records(path, records)
    except OSError:
        return {"model_record": "write_failed"}
    return _model_result(targets, entries, records, docs, opts["force"])


def learn_models(state_dir, fetch, options):
    """Read the official doc flow once per pending model id (or on a forced refresh), record it.

    Each record holds its changelog notes, the question types the models table documents and the
    features it could serve (D-09, SPEC R4). Records only when both changelog.md and models.md
    arrived (review C1-11); an incomplete flow keeps every target pending and writes nothing.
    """
    opts = {**DEFAULT_OPTIONS, **options}
    path = records_path(state_dir, MODEL_RECORDS)
    records = read_records(path)
    latest = latest_model(records)
    targets = _model_targets(records, latest, opts["force"])
    if not targets:
        return {"model_record": "known" if records else "none", "model_id": latest}
    if not opts["fetch_allowed"]:
        return {"model_record": "skipped_deadline", "model_ids": targets}
    docs = fetch_model_docs(fetch)
    texts, _sources, errors = docs
    if "changelog" not in texts or "models" not in texts:
        return {
            "model_record": "fetch_failed",
            "model_ids": targets,
            "notice": f"TypeSafe docs fetch failed ({'; '.join(errors)}); "
            "the model ids stay pending",
        }
    return _record_models(path, targets, docs, opts)


def _load_secret_shapes():
    """The sibling secret_shapes.py, loaded by path: this module is itself loaded by path, and from
    copied skill folders, so its own folder is not always on the import path."""
    path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "secret_shapes.py")
    spec = importlib.util.spec_from_file_location("jev_learn_secret_shapes", path)
    if spec is None or spec.loader is None or not os.path.isfile(path):
        raise ImportError(f"jev-fast-decision: cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_SECRET_SHAPES = _load_secret_shapes()


def _screened_names(names):
    """The sorted, unique primitive or option names that hold no key shape, at most 16.

    Any other name is dropped silently and never logged (T-34-42, review C2-4): the names come from
    a server response or a caller's item, and a key must never reach the record.
    """
    kept = {
        name
        for name in names or ()
        if isinstance(name, str)
        and _UNKNOWN_NAME.fullmatch(name)
        and not _SECRET_SHAPES.detect(name)
    }
    return sorted(kept)[:_UNKNOWN_LIMIT]


def note_unknown(state_dir, model_id, names, now=None):
    """Note primitive or option names the skill does not know, with no network call (review C1-10).

    The names go under model_id, or under the latest recorded id when model_id is None. The id turns
    pending once per new name; a name already seen never triggers again. False when no fresh name is
    left, no id is known or the write fails.
    """
    path = records_path(state_dir, MODEL_RECORDS)
    records = read_records(path)
    fresh_names = _screened_names(names)
    target = latest_model(records) if model_id is None else model_id
    if not fresh_names or not isinstance(target, str) or not _VERSIONED_ID.fullmatch(target):
        return False
    entry = records.get(target)
    if not isinstance(entry, dict):
        entry = {"status": "pending", "first_seen": now or now_iso()}
    seen = _unknown_seen(entry)
    fresh = [name for name in fresh_names if name not in seen]
    if not fresh:
        return False
    records[target] = {**entry, "status": "pending", "unknown_seen": sorted([*seen, *fresh])}
    try:
        write_records(path, records)
    except OSError:
        return False
    return True
