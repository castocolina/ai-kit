"""Lens selection, runner refusals per lens, budget loop and MCP pick.

SPEC R5, R1 amendment; D-10, D-21, D-22.
"""

import hashlib
import json
import os
import re
import shutil
import stat

from ai_kit_spec.prompt_guard import BYTES_PER_TOKEN, is_control_char, validate_values
from ai_kit_spec.skill_table import ROLES, load_seed, resolve_role

# Closed list (SPEC R5): disjoint from refusal and runner setting reasons, classes and findings.
LENS_NOTES = ("built_in_no_file", "over_window", "path_rejected", "not_present", "host_cannot_load")
# Kept once for the lanes; drift tests should pin it to the superpowers adapter's
# _FRONTEND_EXTENSIONS (no import either way: tests/test_arch.py frozen allowlist).
UI_EXTENSIONS = (".tsx", ".jsx", ".css", ".vue", ".scss")
UI_ROLE = "ui_lens"
# The runner's own limits (cross-ai.mjs FILE_READ_MAX and SKILL_NAME_RE).
FILE_READ_MAX = 65536
SKILL_NAME_RE = re.compile(r"[a-z0-9][a-z0-9-]{0,63}")
FRONTMATTER_RE = re.compile(r"\A---\r?\n(.*?)\r?\n---(?:\r?\n|\Z)", re.S)
# JavaScript's multiline $ also stops before \r; Python's does not, hence \r?.
FM_NAME_RE = re.compile(r"^name:[ \t]*[\"']?([^\"'\r\n]*?)[\"']?[ \t]*\r?$", re.M)
MCP_FILE_NAME = "mcp-config.json"


def _seed_rows() -> list:
    """Return object seed rows; missing or malformed seed gives [] as in the scan fallback."""
    try:
        rows = load_seed()
    except (OSError, ValueError):
        return []
    return [row for row in rows if isinstance(row, dict)]


def mcp_pick(table_host: dict, child_path: str, user: dict | None = None) -> list:
    """Select seed code-index servers available on the child's PATH, honoring roles."""
    seed = _seed_rows()
    host = table_host.get("mcp")
    roles = {row["name"]: row["role"] for row in host} if isinstance(host, list) else {}
    picks = []
    for row in seed:
        launch = row.get("launch")
        if row.get("kind") != "mcp" or not isinstance(launch, dict):
            continue
        role = roles.get(row["name"]) or resolve_role(row["name"], "mcp", seed, user or {})[0]
        if role != "code_index":
            continue
        found = shutil.which(launch["command"], path=child_path or "")
        if found:
            picks.append({"name": row["name"], "command": os.path.abspath(found),
                          "args": [str(a) for a in launch.get("args", [])]})
    return picks


def write_mcp_file(run_dir: str, picks: list) -> str | None:
    """Write a private run-scoped config; the caller owns and removes the directory."""
    if not picks:
        return None
    path = os.path.join(run_dir, MCP_FILE_NAME)
    data = {"mcpServers": {p["name"]: {"command": p["command"], "args": p["args"]}
                           for p in picks}}
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(json.dumps(data, indent=2, sort_keys=True) + "\n")
    return path


def lens_set(table_host: dict, files, role: str = "review_lens",
             native_host: str | None = None) -> list:
    """Select present lenses and unverified built-ins, sorted by role then name."""
    roles = {role} | ({UI_ROLE} if role == "review_lens" and any(
        str(f).lower().endswith(UI_EXTENSIONS) for f in files) else set())
    kept = {}
    for row in table_host.get("skills") or []:
        if row.get("role") in roles and row["name"] not in kept:
            kept[row["name"]] = {"name": row["name"], "path": row.get("path"),
                                 "role": row["role"]}
    for row in _seed_rows():
        if (row.get("kind") == "skill" and isinstance(row.get("built_in"), str)
                and row.get("role") in roles and row.get("name") not in kept):
            native = native_host == row["built_in"]
            kept[row["name"]] = {"name": row["name"], "path": None, "role": row["role"],
                                 "built_in": row["built_in"],
                                 "note": None if native else "built_in_no_file",
                                 "delivery": "name" if native else None, "label": "unverified"}
    return sorted(kept.values(), key=lambda row: (ROLES.index(row["role"]), row["name"]))


def prose_block_bytes(name: str, path: str, sha256: str, body: str) -> int:
    """Count the runner's UTF-8 prose block, including its delimiters."""
    # Byte for byte the runner's skillBlock; a sync test pins it to skill-block bytes=.
    block = f'<skill name="{name}" path="{path}" sha256="{sha256}">\n{body}\n</skill>\n'
    return len(block.encode())


def _frontmatter_name(text: str) -> str | None:
    front = FRONTMATTER_RE.match(text)
    match = FM_NAME_RE.search(front.group(1)) if front else None
    return match.group(1) if match else None


def _runner_name(text: str, dir_name: str) -> str | None:
    name = _frontmatter_name(text)
    if name and SKILL_NAME_RE.fullmatch(name):
        return name
    return dir_name if SKILL_NAME_RE.fullmatch(dir_name) else None


def _read_raw(file: str) -> tuple[str | None, bytes]:
    try:
        fd = os.open(file, os.O_RDONLY | os.O_NONBLOCK)
    except FileNotFoundError:
        return "not_present", b""
    except OSError:
        return "path_rejected", b""
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            return "path_rejected", b""
        chunks = []
        size = 0
        while size <= FILE_READ_MAX:
            chunk = os.read(fd, FILE_READ_MAX + 1 - size)
            if not chunk:
                break
            chunks.append(chunk)
            size += len(chunk)
        raw = b"".join(chunks)
    except OSError:
        return "path_rejected", b""
    finally:
        os.close(fd)
    return ("path_rejected", b"") if len(raw) > FILE_READ_MAX else (None, raw)


def _decode(raw: bytes) -> tuple[str | None, str]:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return "path_rejected", ""
    if text.startswith("\ufeff"):
        return "path_rejected", ""
    if not text:
        return "not_present", ""
    return None, text


def _check_path(lens: dict, repo: str, skill_roots: list) -> tuple[str | None, str]:
    real = os.path.realpath(lens["path"])
    if not os.path.isdir(real):
        return "not_present", real
    if (validate_values([(f"lens {lens['name']}", lens["path"])], repo, list(skill_roots))
            or any(is_control_char(ch) for ch in real) or '"' in real):
        return "path_rejected", real
    return None, real


def _check_body(real: str, repo: str, skill_roots: list) -> tuple[str | None, bytes, str]:
    file = os.path.join(real, "SKILL.md")
    if not os.path.exists(file):
        return "not_present", b"", ""
    if validate_values([("lens SKILL.md", os.path.realpath(file))], repo, list(skill_roots)):
        return "path_rejected", b"", ""
    note, raw = _read_raw(file)
    if note:
        return note, b"", ""
    note, text = _decode(raw)
    if note or "</skill>" in text:
        return note or "path_rejected", b"", ""
    return None, raw, text


def check_lens(lens: dict, repo: str, skill_roots: list) -> dict:
    """Check one lens against runner refusals; the runner reads it again at launch."""
    out = {**lens, "note": None, "skill_name": None, "aliases": [], "sha256": None, "bytes": 0}
    if not lens.get("path"):
        out["note"] = lens.get("note") if lens.get("delivery") == "name" else "built_in_no_file"
        out["skill_name"] = lens["name"] if lens.get("delivery") == "name" else None
        return out
    note, real = _check_path(lens, repo, skill_roots)
    if note:
        return {**out, "note": note}
    note, raw, text = _check_body(real, repo, skill_roots)
    if note:
        return {**out, "note": note}
    name = _runner_name(text, os.path.basename(real))
    if name is None:
        return {**out, "note": "path_rejected"}
    digest = hashlib.sha256(raw).hexdigest()
    return {**out, "path": real, "skill_name": name,
            "aliases": sorted({os.path.basename(real), _frontmatter_name(text)} - {None, ""}),
            "sha256": digest, "bytes": prose_block_bytes(name, real, digest, text)}


def plan_lenses(lenses: list, base_bytes: int, window: int | None,
                prompt_cap: int | None) -> tuple[list, list]:
    """Deliver fitting, unambiguous lenses in order; skip whole lenses that do not fit."""
    delivered, skipped = [], []
    used = set()
    total = base_bytes
    for lens in lenses:
        if lens.get("note"):
            skipped.append(lens)
            continue
        names = {lens["skill_name"], *lens.get("aliases", [])}
        if names & used:
            skipped.append({**lens, "note": "path_rejected"})
            continue
        new = total + lens["bytes"]
        if ((window is None or -(-new // BYTES_PER_TOKEN) <= window)
                and (prompt_cap is None or new <= prompt_cap)):
            delivered.append(lens)
            used.update(names)
            total = new
        else:
            skipped.append({**lens, "note": "over_window"})
    return delivered, skipped
