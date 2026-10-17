#!/usr/bin/env python3
"""Dev-only evaluation helper for the curated-config skill (Phase 19, D-13); not shipped.

Plan 01 (this file) adds `snapshot` (protected-set byte identity), `digest` (18.1's
DIGEST_CMD plus the evidence-row check) and `matrix` (the APP-05 resolve-model oracle).
Plan 02 adds `fixture`/`run`, plan 03 adds `grade`/`secret-scan` plus the evidence-table
refinement of `check_digests`, and plan 04 adds `smoke`.

Contract rules that hold for every subcommand:

* stdlib only, and the skill under test is always this repo's
  (`REPO_ROOT/skills/ai-kit-gsd-curated-config`), never an installed copy;
* every subprocess gets an explicit env. D-08: the matrix's gsd-tools subprocesses get
  the real `HOME` with a scratch `GSD_HOME` and `GSD_RUNTIME`; `snapshot` only *reads*
  bytes of the protected files under the home directory - nothing under it is written,
  opened as text, printed or copied;
* output never carries an absolute machine path and never carries a file's content: the
  repo root prints as `<worktree>`, the home directory as `<home>`, a scratch directory as
  `<scratch>` (D-14, jev 19-S1, T-19-03);
* the oracle reads gsd-core's *live* tables, so it is independent of the product and of
  the applied config (D-04, D-10, Pitfall 1).
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import io
import json
import os
import pathlib
import re
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import uuid
from collections.abc import Callable
from typing import NamedTuple

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
for _skill in (
    REPO_ROOT / "skills" / "ai-kit-gsd-curated-config",
    REPO_ROOT / "skills" / "ai-kit-spec-review",
):
    if str(_skill) not in sys.path:
        sys.path.insert(0, str(_skill))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ai_kit_gsd_curated_config import config_backup, plan_io, presets
from ai_kit_spec import gsd_tools
from ai_kit_spec.vendor import infer_vendor_from_model

from tests.test_curated_config_apply_e2e import (
    GSD_CORE_PREFIXES,
    _config_set_keys,
    _golden_bundle,
    _real_apply,
    _sha256,
    gsd_core_line_supported,
)


class _refusal(SystemExit):
    """A hard stop carrying both an exit code and a one-line reason.

    `SystemExit` alone cannot do both: raised with a `(code, reason)` pair its `code` becomes
    the tuple, so a caller reading `exc.code` gets a message where a number belongs. Raising
    this instead lets the CLI print the reason and return the code, and lets a hermetic test
    assert on both. Every reason is a label or a name, never a file's content.
    """

    def __init__(self, exit_code: int, reason: str) -> None:
        super().__init__(reason)
        self.exit_code = exit_code
        self.reason = reason


# ═══ 1. path labels — the only way a path reaches output ══════════════════════════════

WORKTREE_LABEL = "<worktree>"
HOME_LABEL = "<home>"
SCRATCH_LABEL = "<scratch>"
GSD_CORE_LABEL = f"{WORKTREE_LABEL}/.claude/gsd-core"
SKILL_DIR = REPO_ROOT / "skills" / "ai-kit-gsd-curated-config"
GSD_TOOLS_PATH = str(REPO_ROOT / ".claude" / "gsd-core" / "bin" / "gsd-tools.cjs")

# The Claude credentials file is in no snapshot set and is never read, not even to hash it
# (checker iter2 W2); the skill digest excludes it for the same reason.
CREDENTIALS_BASENAME = "credentials.json"

# (rigor, profile), in this order (D-04).
COMBOS = (
    ("mvp", "adaptive"),
    ("standard", "adaptive"),
    ("rigorous", "adaptive"),
    ("standard", "quality"),
    ("standard", "budget"),
)
PATHS = ("P1", "P2")

# Poison fixture (D-08): `resolve_model_ids` is the key that empties `resolve-model`; a
# `model_policy` resolves before the omit gate and would hide the bug, so it is absent.
POISON_DEFAULTS = {"resolve_model_ids": "omit", "runtime": "codex"}

MESSAGE_NON_CLAUDE = (
    "matrix oracle supports claude only (Phase 20 adds "
    "model_profile_overrides.<host>.<tier> plan entries and RUNTIME_PROFILE_MAP to promised)"
)
WHY_INFORMATIONAL = (
    "a project-level runtime key steers resolve-model when GSD_RUNTIME is unset; the plan "
    "writes no runtime entry on claude (18 D-30) and config-new-project does not copy it, so "
    "it was seeded here with config-set on the scratch project; not gating (jev 19-Q1)"
)
_TIERS = ("opus", "sonnet", "haiku")
_HEX16 = re.compile(r"\b[0-9a-f]{16}\b")

# The gsd-core lines whose live tables this phase verified come from `GSD_CORE_PREFIXES`, imported
# from tests/test_curated_config_apply_e2e.py so the two guards cannot drift. R-7: the
# checkout-local install is gitignored and shared by every worktree, so its version is a fact of
# the moment, not of the plan. `MODEL_PROFILES` and `AGENT_TO_PHASE_TYPE` are byte-identical
# between the 1.16.0 these plans were written against and the 1.17.0 now in this checkout (same 35
# agent keys, empty symmetric difference, re-verified every run by
# tests.test_ai_kit_gsd_curated_config_matrix). Anything else is refused with a reason rather than
# silently graded against a table nobody checked, because 19-05..19-10 evidence rows name the
# version they used and are only comparable across one.


def _abs(root: pathlib.Path | str) -> pathlib.Path:
    """Absolute view of `root`, so `relative_to` compares like with like."""
    return pathlib.Path(os.path.abspath(str(root)))


def label_path(path: pathlib.Path | str, *scratch_roots: pathlib.Path | str) -> str:
    """`path` as a placeholder label (`<scratch>/...`, `<worktree>/...`, `<home>/...`).

    Never returns an absolute machine path. Scratch roots win, so a scratch directory that
    happens to live under the repo or the system temp dir still reads as `<scratch>`; the
    system temp dir is an implicit scratch root because that is where `mkdtemp()` puts one.
    """
    resolved = _abs(path)
    scratches = [_abs(root) for root in scratch_roots] + [_abs(tempfile.gettempdir())]
    for root in scratches:
        try:
            rel = resolved.relative_to(root)
        except ValueError:
            continue
        return SCRATCH_LABEL if str(rel) == "." else f"{SCRATCH_LABEL}/{rel}"
    for label, root in ((WORKTREE_LABEL, _abs(REPO_ROOT)), (HOME_LABEL, _abs(pathlib.Path.home()))):
        try:
            rel = resolved.relative_to(root)
        except ValueError:
            continue
        return label if str(rel) == "." else f"{label}/{rel}"
    return os.path.relpath(resolved, _abs(REPO_ROOT))


# ═══ 2. snapshot: the protected set (D-14 step 1, jev 19-S1, T-19-02) ═════════════════


def _file_sha(path: pathlib.Path) -> str | None:
    """sha256 of a file's bytes, or None when absent - absence is a value the diff sees, so
    deleting a protected file is itself a change."""
    return _sha256(str(path)) if path.is_file() else None


def _dir_names(path: pathlib.Path, prefix: str = "") -> list[str] | None:
    """Sorted entry names of a directory (only those starting with `prefix` when given), or
    None when it does not exist."""
    if not path.is_dir():
        return None
    return sorted(name for name in os.listdir(path) if name.startswith(prefix))


def _strict_files(repo_root: pathlib.Path, home: pathlib.Path) -> dict[str, pathlib.Path]:
    """Strict hash-only entries: a change to any of them fails the batch."""
    planning = repo_root / ".planning"
    scripts = planning / "scripts"
    files = {
        f"{WORKTREE_LABEL}/.planning/config.json": planning / "config.json",
        f"{WORKTREE_LABEL}/.planning/config.json{config_backup.MARKER_SUFFIX}": (
            planning / f"config.json{config_backup.MARKER_SUFFIX}"
        ),
        f"{WORKTREE_LABEL}/.planning/scripts/cross-ai.mjs": scripts / "cross-ai.mjs",
        f"{WORKTREE_LABEL}/.planning/scripts/cross-ai.mjs.new": scripts / "cross-ai.mjs.new",
        f"{WORKTREE_LABEL}/.planning/scripts/cross-ai.mjs{config_backup.SNAPSHOT_SUFFIX}": (
            scripts / f"cross-ai.mjs{config_backup.SNAPSHOT_SUFFIX}"
        ),
        f"{HOME_LABEL}/.gsd/defaults.json": home / ".gsd" / "defaults.json",
        f"{HOME_LABEL}/.claude/settings.json": home / ".claude" / "settings.json",
        f"{HOME_LABEL}/.claude/settings.local.json": home / ".claude" / "settings.local.json",
        f"{HOME_LABEL}/.claude/CLAUDE.md": home / ".claude" / "CLAUDE.md",
        # `<home>/.cursor/cli-config.json` is the one non-Claude CLI config detection.py
        # documents a listing probe rewriting (`cursor-agent models`), so it is strict: a
        # batch that let such a probe run against the real home must fail (review cycle 2).
        f"{HOME_LABEL}/.cursor/cli-config.json": home / ".cursor" / "cli-config.json",
    }
    for name in _dir_names(planning, config_backup.BACKUP_PREFIX) or []:
        files[f"{WORKTREE_LABEL}/.planning/{name}"] = planning / name
    return files


def _strict_listings(repo_root: pathlib.Path, home: pathlib.Path) -> dict[str, list | None]:
    """Strict listing entries: sorted name lists, never contents. The worktree listing is
    filtered to `config.json*` because STATE.md and friends change during a session."""
    return {
        f"{HOME_LABEL}/.gsd": _dir_names(home / ".gsd"),
        f"{HOME_LABEL}/.claude/skills": _dir_names(home / ".claude" / "skills"),
        f"{HOME_LABEL}/.claude/agents": _dir_names(home / ".claude" / "agents"),
        f"{HOME_LABEL}/.claude/commands": _dir_names(home / ".claude" / "commands"),
        f"{WORKTREE_LABEL}/.planning": _dir_names(repo_root / ".planning", "config.json"),
    }


def _host_managed_files(home: pathlib.Path) -> dict[str, pathlib.Path]:
    """Host-managed entries: a change is reported and investigated, never a failure.

    `~/.claude/plugins/*.json` are rewritten by Claude Code itself; the opencode and codex
    config files are tripwires - no probe is documented to rewrite them.
    """
    files: dict[str, pathlib.Path] = {}
    plugins = home / ".claude" / "plugins"
    for name in _dir_names(plugins) or []:
        if name.endswith(".json") and name != CREDENTIALS_BASENAME:
            files[f"{HOME_LABEL}/.claude/plugins/{name}"] = plugins / name
    for path in (
        home / ".config" / "opencode" / "opencode.jsonc",
        home / ".config" / "opencode" / "opencode.json",
        home / ".codex" / "config.toml",
    ):
        files[f"{HOME_LABEL}/{path.relative_to(home).as_posix()}"] = path
    return files


def _tree_sha(root: pathlib.Path) -> str | None:
    """One sha256 over sorted `relative path NUL file sha256 NUL` pairs, or None when the
    directory is absent. Symlinks hash their target path instead of being followed."""
    if not root.is_dir():
        return None
    entries: list[tuple[str, bytes]] = []
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        base = pathlib.Path(dirpath)
        for name in sorted(dirnames) + sorted(filenames):
            full = base / name
            rel = full.relative_to(root).as_posix()
            if full.is_symlink():
                entries.append((rel, f"link\0{os.readlink(full)}".encode()))
            elif full.is_dir():
                entries.append((rel, b"dir"))
            else:
                entries.append((rel, hashlib.sha256(full.read_bytes()).hexdigest().encode()))
    digest = hashlib.sha256()
    for rel, payload in sorted(entries):
        digest.update(rel.encode() + b"\0" + payload + b"\0")
    return digest.hexdigest()


def snapshot(repo_root: pathlib.Path | str, home: pathlib.Path | str) -> dict:
    """The protected set as `{"strict": {...}, "host_managed": {...}}`; reads bytes only.

    Strict values are a sha256 (None when absent) for files, a sorted name list for
    listings, and one tree hash for `<worktree>/.claude/gsd-core`.
    """
    root, home_dir = _abs(repo_root), _abs(home)
    strict: dict[str, object] = {
        label: _file_sha(path) for label, path in _strict_files(root, home_dir).items()
    }
    strict.update(_strict_listings(root, home_dir))
    strict[GSD_CORE_LABEL] = _tree_sha(root / ".claude" / "gsd-core")
    host_managed = {label: _file_sha(path) for label, path in _host_managed_files(home_dir).items()}
    return {
        "strict": dict(sorted(strict.items())),
        "host_managed": dict(sorted(host_managed.items())),
    }


def snapshot_diff(a: dict, b: dict) -> tuple[list[str], list[str]]:
    """(strict labels, host-managed labels) that differ between two snapshots."""
    return (
        _diff_labels(a.get("strict") or {}, b.get("strict") or {}),
        _diff_labels(a.get("host_managed") or {}, b.get("host_managed") or {}),
    )


def _snapshot_report(stored: dict, current: dict) -> tuple[list[str], bool]:
    """(printed lines, failed): one `changed <label>` line per strict difference, one
    `changed (host-managed) <label>` per host-managed difference. Never a value."""
    strict, host = snapshot_diff(stored, current)
    return (
        [f"changed {label}" for label in strict]
        + [f"changed (host-managed) {label}" for label in host],
        bool(strict),
    )


def _diff_labels(a: dict, b: dict) -> list[str]:
    return sorted(label for label in set(a) | set(b) if a.get(label) != b.get(label))


def _cmd_snapshot(args: argparse.Namespace) -> int:
    repo_root, home = _abs(REPO_ROOT), _abs(args.home or pathlib.Path.home())
    current = snapshot(repo_root, home)
    if args.out:
        _write_json(_abs(args.out), current)
        print(f"snapshot written to {label_path(args.out)}")
        return 0
    if not args.check:
        print("snapshot needs --out F or --check F")
        return 2
    stored, error = _read_json(_abs(args.check))
    if stored is None:
        print(f"snapshot {error}")
        return 1
    lines, failed = _snapshot_report(stored, current)
    print("\n".join(lines) if lines else "snapshot ok")
    return 1 if failed else 0


def _read_json(path: pathlib.Path) -> tuple[dict | None, str]:
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return None, f"{path.name} unreadable: {type(exc).__name__}"
    if not isinstance(parsed, dict):
        return None, f"{path.name} is not a JSON object"
    return parsed, ""


def _write_json(path: pathlib.Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True, indent=1) + "\n", encoding="utf-8")


# ═══ 3. digest: 18.1's DIGEST_CMD plus the evidence-row check ═════════════════════════


def skill_digest(skill_dir: pathlib.Path | str) -> str:
    """The 16-hex digest of what a judge or a pressure run reads: `SKILL.md` first, then
    every file under `references/` sorted, each contributing
    `relative posix path + NUL + sha256(bytes)` to one sha256 (18.1-21's DIGEST_CMD)."""
    root = _abs(skill_dir)
    files = [root / "SKILL.md"]
    references = root / "references"
    if references.is_dir():
        files.extend(sorted(p for p in references.rglob("*") if p.is_file()))
    digest = hashlib.sha256()
    for path in files:
        if path.name == CREDENTIALS_BASENAME:
            continue
        digest.update(
            path.relative_to(root).as_posix().encode()
            + b"\0"
            + hashlib.sha256(path.read_bytes()).digest()
        )
    return digest.hexdigest()[:16]


def _live_row_tokens(line: str) -> list[str]:
    """The 16-hex tokens of a *live* table row. A row is live when it starts with `|`,
    carries a 16-hex token, and is neither `superseded` nor `context` (those are history,
    not a claim about the current bytes)."""
    if not line.startswith("|") or "superseded" in line or "context" in line:
        return []
    return _HEX16.findall(line)


def check_digests(
    paths: list[str], digest: str, sections: tuple | list = (), columns: tuple | list = ()
) -> list[str]:
    """Why these evidence files do not bind `digest`; empty when every one of them does.

    Each file needs at least one live row, and every live row's token must equal `digest`.
    `sections` (prefix match on a `## ` heading) each need a live row of their own, and each
    `columns` entry's `digest`-row cell under every named section must equal `digest` (review
    cycle 2: a pending cell in one column cannot be supplied by another column's sonnet digest).
    """
    problems: list[str] = []
    for path in paths:
        tokens, error = _live_tokens(_abs(path))
        if error:
            problems.append(f"{path}: {error}")
            continue
        if not tokens:
            problems.append(f"{path}: no live row")
        problems.extend(f"{path}: {token} != {digest}" for token in tokens if token != digest)
        if sections or columns:
            problems.extend(section_digest_problems(path, digest, sections, columns))
    return problems


def _live_tokens(path: pathlib.Path) -> tuple[list[str], str]:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, ValueError) as exc:
        return [], f"unreadable: {type(exc).__name__}"
    return [token for line in text.splitlines() for token in _live_row_tokens(line)], ""


def _cmd_digest(args: argparse.Namespace) -> int:
    digest = skill_digest(args.skill_dir or SKILL_DIR)
    if not args.check:
        print(digest)
        return 0
    problems = check_digests(args.check, digest, args.section, args.column)
    print("\n".join(problems) if problems else "digests ok")
    return 1 if problems else 0


# ═══ 4. oracle: live tables, the promise, the comparison (D-04, D-10) ═════════════════

# The same `node -e` shape as gsd_catalog._AGENT_CATALOG_QUERY_SCRIPT: the module path is a
# real argv element (never interpolated into the script body), and a require failure prints
# `null`, so "exports missing" and "require threw" collapse into one signal.
_LIVE_TABLES_SCRIPT = (
    "try { const m = require(process.argv[1]); "
    "process.stdout.write(JSON.stringify({profiles: m.MODEL_PROFILES, "
    "phase: m.AGENT_TO_PHASE_TYPE})); } "
    "catch (e) { process.stdout.write('null'); }"
)


def live_tables(node_bin: str, gsd_core_root: str, run_fn: Callable = subprocess.run) -> dict:
    """gsd-core's live `MODEL_PROFILES` and `AGENT_TO_PHASE_TYPE`, asserted to cover the
    same agent key set before any comparison (D-10) - exits 1 naming the difference."""
    module = os.path.join(str(_abs(gsd_core_root)), "bin", "lib", "model-profiles.cjs")
    try:
        result = run_fn(
            [node_bin, "-e", _LIVE_TABLES_SCRIPT, module],
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise _refusal(1, f"live agent tables unavailable: {type(exc).__name__}") from exc
    parsed = _json_object(_text(getattr(result, "stdout", ""))) or {}
    profiles, phase = parsed.get("profiles"), parsed.get("phase")
    if not isinstance(profiles, dict) or not profiles:
        raise _refusal(1, "live agent tables unreadable from gsd-core")
    if not isinstance(phase, dict) or not phase:
        raise _refusal(1, "live agent tables unreadable from gsd-core")
    difference = sorted(set(profiles) ^ set(phase))
    if difference:
        raise _refusal(1, f"agent key sets differ: {', '.join(difference)}")
    return {"profiles": profiles, "phase": phase}


def promised(agent: str, plan: dict, tables: dict, *, inheritance_promised: bool = False) -> str:
    """The model the plan promises `agent`, from the plan's set entries plus the live tables
    (D-10) - never from the applied config (D-04, Pitfall 1).

    Branch order is the resolver's, as separate oracle branches: a `model_overrides.<agent>`
    entry wins, then the rigor's phase shift `models.<agent's phase type>`, then the agent's
    own `MODEL_PROFILES[agent][profile]` tier default. `inheritance_promised=True` (nothing
    in this phase sets it) makes the promise "no model id at all".
    """
    if inheritance_promised:
        return ""
    sets = _set_entries(plan)
    override = f"model_overrides.{agent}"
    if override in sets:
        return str(sets[override])
    phase = (tables.get("phase") or {}).get(agent)
    shift = f"models.{phase}" if phase else None
    if shift and shift in sets:
        return str(sets[shift])
    entry, profile = (tables.get("profiles") or {}).get(agent), plan.get("profile")
    if not isinstance(entry, dict) or profile not in entry:
        raise _refusal(1, f"no live MODEL_PROFILES entry for {agent}/{profile}")
    return str(entry[profile])


def _set_entries(plan: dict) -> dict:
    return {
        entry["key"]: entry["value"]
        for entry in plan.get("entries") or []
        if isinstance(entry, dict)
        and entry.get("op") == "set"
        and isinstance(entry.get("key"), str)
    }


def compare(agent: str, got: dict, expected: str, *, inheritance_promised: bool = False):
    """None when a `resolve-model` result matches the promise, else the reason: `empty model
    for <agent>` (an empty model is a failure unless the plan promised inheritance), `model`
    (wrong id), or `tier` (wrong tier for a tier alias)."""
    model = got.get("model")
    if model == "" and not inheritance_promised:
        return f"empty model for {agent}"
    if model != expected:
        return "model"
    if expected in _TIERS and got.get("tier") != expected:
        return "tier"
    return None


# ═══ 5. matrix: bundles, apply env, resolve-model (D-04, D-08, D-09) ══════════════════


class _MatrixCtx(NamedTuple):
    """The seams and fixed inputs of one matrix run, so every step stays within the limits.

    `bundle_fn` is the e2e tier's `_golden_bundle`, `apply_fn` its `_real_apply`,
    `tables_fn` reads the live agent tables, `run_fn` runs a subprocess. A hermetic test
    injects all four and never needs node.
    """

    node_bin: str
    tools_path: str
    home: str
    host: str
    core_root: str
    bundle_fn: Callable = _golden_bundle
    apply_fn: Callable = _real_apply
    run_fn: Callable = subprocess.run
    tables_fn: Callable = staticmethod(live_tables)


def _seams(node_bin: str, tools_path: str, home: str, host: str) -> _MatrixCtx:
    """The default seams: real bundle builder, real apply, real subprocesses."""
    return _MatrixCtx(
        node_bin, tools_path, home, host, os.path.dirname(os.path.dirname(str(_abs(tools_path))))
    )


def matrix_env(bundle: dict, home: str, host: str = "claude") -> dict:
    """The one env every gsd-tools subprocess of a matrix apply gets: the real `HOME` (D-08)
    plus the bundle's scratch `GSD_HOME`/`XDG_CACHE_HOME`/`RUNTIME_DIR` and
    `GSD_RUNTIME=<host>`."""
    return {**bundle["resolve_env"], "HOME": home, "GSD_RUNTIME": host}


REPO_ROOT_REFUSAL = "refusing a real apply on the repo root"


def refuse_repo_apply(project_dir: pathlib.Path | str) -> None:
    """D-03: every real `apply` path calls this first; the repo root is never applied to.

    Compares resolved paths, so a symlink that points at the repo is refused too.
    """
    if os.path.realpath(str(project_dir)) == os.path.realpath(str(REPO_ROOT)):
        print(REPO_ROOT_REFUSAL, file=sys.stderr)
        raise SystemExit(2)


def _apply_bundle(
    bundle: dict, home: str, node_bin: str, apply_fn: Callable = _real_apply, host: str = "claude"
) -> dict:
    """One real apply of the bundle's plan; returns the env later resolves use.

    The SAME `matrix_env` dict goes into both the `resolve_env` and the `child_env` positions
    (review cycle 1): `_real_apply` turns `resolve_env` into `env_fn`, apply passes that env
    to every gsd-tools call, and `_real_run` merges it over `child_env`. Two different dicts
    would hand the subprocesses the scratch `HOME` and defeat D-08. A non-zero apply exit is
    a matrix failure, reported with the stderr tail.
    """
    refuse_repo_apply(bundle["project"])
    env = matrix_env(bundle, home, host)
    code, _parsed, _stdout, stderr = apply_fn(
        bundle["plan_path"], bundle["inv_path"], bundle["project"], env, env, node_bin
    )
    if code != 0:
        raise _refusal(1, f"matrix apply failed (exit {code}): {_text(stderr)[-400:]}")
    return env


def _seeder(node_bin: str, tools_path: str, home: str) -> Callable:
    """P2's start path: the config is pre-created by the *real* `config-new-project` under
    the poisoned `GSD_HOME`, and the poison must be visible in it before `recommend` runs so
    the plan carries the unset (D-09)."""

    def seed(project: str, resolve_env: dict) -> None:
        tools = gsd_tools.GsdTools(node_bin, tools_path)
        if not gsd_tools.ensure_config_exists(tools, project, env={**resolve_env, "HOME": home}):
            raise _refusal(1, "config-new-project failed for the P2 bundle")
        created, _warn = plan_io.read_json_object(os.path.join(project, ".planning", "config.json"))
        if (created or {}).get("resolve_model_ids") != "omit":
            raise _refusal(1, "poison not copied")

    return seed


def _bundle_for(ctx: _MatrixCtx, combo: tuple[str, str], start: str, defaults: dict | None) -> dict:
    """One scratch project per combination: its own `mkdtemp()`, removed by the caller. P1
    starts with no config; P2's is created by the real `config-new-project` under the poison
    (`defaults`), which is also what makes the plan carry the unset."""
    rigor, profile = combo
    scratch = tempfile.mkdtemp(prefix="xai-matrix-")
    pre_inventory = _seeder(ctx.node_bin, ctx.tools_path, ctx.home) if start == "P2" else None
    try:
        bundle = ctx.bundle_fn(
            scratch,
            with_planning=False,
            host_name=ctx.host,
            profile=profile,
            rigor=rigor,
            defaults=None if defaults is None else json.loads(json.dumps(defaults)),
            pre_inventory=pre_inventory,
        )
    except BaseException:
        # a bundle that never came back has no caller to remove its scratch directory
        shutil.rmtree(scratch, ignore_errors=True)
        raise
    bundle["scratch"] = scratch
    bundle["start"] = start
    bundle["combo"] = f"{rigor}/{profile}"
    return bundle


def _resolve_model(ctx: _MatrixCtx, agent: str, project: str, env: dict) -> dict:
    """`resolve-model <agent> --cwd <project>`: stdout JSON only, stderr is never a failure
    signal (Pitfall 8 - a poisoned `GSD_HOME` prints warning #3532 on every call). A failed
    or unparseable call reads as an empty model, which `compare` then fails."""
    try:
        result = ctx.run_fn(
            [ctx.node_bin, ctx.tools_path, "resolve-model", agent, "--cwd", project],
            capture_output=True,
            text=True,
            check=False,
            timeout=60,
            env=dict(env),
        )
    except (OSError, subprocess.SubprocessError):
        return {"model": "", "tier": "", "profile": "", "effort": ""}
    parsed = _json_object(_text(getattr(result, "stdout", ""))) or {}
    return {key: parsed.get(key, "") for key in ("model", "tier", "profile", "effort")}


def _resolve_all(ctx: _MatrixCtx, agents: list[str], project: str, env: dict) -> dict:
    return {agent: _resolve_model(ctx, agent, project, env) for agent in agents}


def _mismatches(
    agents: list[str],
    plan: dict,
    tables: dict,
    got: dict,
    *,
    inheritance_promised: bool = False,
) -> list[list[str]]:
    """`[agent, expected, got model, got tier]` for every agent that does not match, in
    sorted agent order, so two runs of the matrix produce the same report."""
    rows: list[list[str]] = []
    for agent in sorted(agents):
        expected = promised(agent, plan, tables, inheritance_promised=inheritance_promised)
        row = got[agent]
        if compare(agent, row, expected, inheritance_promised=inheritance_promised):
            rows.append([agent, expected, str(row["model"]), str(row["tier"])])
    return rows


def _load_plan(bundle: dict) -> dict:
    plan, error = plan_io.load_plan(bundle["plan_path"])
    if plan is None:
        raise _refusal(1, f"matrix plan unreadable: {error}")
    return plan


def _row_for(
    ctx: _MatrixCtx, combo: tuple[str, str], start: str, agents: list[str], tables: dict
) -> dict:
    """One `combo x path` row: build the bundle, apply it, resolve every live agent, compare
    each against the oracle."""
    rigor, profile = combo
    bundle = _bundle_for(ctx, combo, start, POISON_DEFAULTS)
    try:
        env = _apply_bundle(bundle, ctx.home, ctx.node_bin, ctx.apply_fn, ctx.host)
        plan = _load_plan(bundle)
        got = _resolve_all(ctx, agents, bundle["project"], env)
        mismatches = _mismatches(agents, plan, tables, got)
    finally:
        shutil.rmtree(bundle["scratch"], ignore_errors=True)
    return {
        "profile": profile,
        "rigor": rigor,
        "path": start,
        "combo": f"{rigor}/{profile}",
        "mismatches": mismatches,
        "checks": len(agents),
    }


def _unoverridden(agents: list[str], plan: dict) -> list[str]:
    """Agents whose promise is *not* a `model_overrides.<agent>` entry - exactly the set
    Control 1 requires to fail."""
    overrides = {
        entry.get("key") for entry in plan.get("entries") or [] if entry.get("op") == "set"
    }
    return [agent for agent in sorted(agents) if f"model_overrides.{agent}" not in overrides]


def _write_control_plan(bundle: dict, plan: dict) -> None:
    """JSON edit of the plan copy (never string splicing): drop the entry whose key is
    `resolve_model_ids`, so the omit poison survives into the applied config. Written as
    `plan-control1.json` in the same directory, so the plan/inventory pairing holds."""
    entries = plan.get("entries") or []
    kept = [entry for entry in entries if entry.get("key") != "resolve_model_ids"]
    if len(kept) == len(entries):
        raise _refusal(1, "control 1: no resolve_model_ids entry to remove")
    path = os.path.join(os.path.dirname(bundle["plan_path"]), "plan-control1.json")
    _write_json(_abs(path), {**plan, "entries": kept})
    bundle["plan_path"] = path


def _control_one(ctx: _MatrixCtx, agents: list[str], tables: dict) -> dict:
    """Control 1 (D-09, T-19-01): a P2 poisoned bundle applied from a plan copy with the
    `resolve_model_ids` unset removed. Every agent without a `model_overrides` entry must
    then fail; if one of them matches, the oracle is not discriminating and the matrix must
    exit 1 with `control 1 vacuous`."""
    bundle = _bundle_for(ctx, ("standard", "adaptive"), "P2", POISON_DEFAULTS)
    try:
        plan = _load_plan(bundle)
        expected = _unoverridden(agents, plan)
        _write_control_plan(bundle, plan)
        env = _apply_bundle(bundle, ctx.home, ctx.node_bin, ctx.apply_fn, ctx.host)
        got = _resolve_all(ctx, agents, bundle["project"], env)
        mismatches = _mismatches(agents, _load_plan(bundle), tables, got)
    finally:
        shutil.rmtree(bundle["scratch"], ignore_errors=True)
    failed = {row[0] for row in mismatches}
    return {
        "expected_failures": len(expected),
        "observed": len(mismatches),
        "ok": bool(expected) and all(agent in failed for agent in expected),
        "checks": len(agents),
    }


def _control_two(ctx: _MatrixCtx, agents: list[str], tables: dict) -> dict:
    """Control 2 (D-09): a P1 bundle with clean defaults (no poison at all) must pass."""
    bundle = _bundle_for(ctx, ("standard", "adaptive"), "P1", None)
    try:
        env = _apply_bundle(bundle, ctx.home, ctx.node_bin, ctx.apply_fn, ctx.host)
        plan = _load_plan(bundle)
        got = _resolve_all(ctx, agents, bundle["project"], env)
        mismatches = _mismatches(agents, plan, tables, got)
    finally:
        shutil.rmtree(bundle["scratch"], ignore_errors=True)
    return {
        "mismatches": [row[0] for row in mismatches],
        "ok": not mismatches,
        "checks": len(agents),
    }


def _seed_runtime_key(ctx: _MatrixCtx, bundle: dict, env: dict) -> None:
    """`config-set runtime codex` on the scratch project, read back or `runtime not seeded`.

    A scratch project only, never this repo: the `refuse_repo_apply` guard itself lands in
    19-04, which wires it into `_apply_bundle` and `_informational_row`; until then every
    bundle lives under `mkdtemp()` and `test_repo_config_untouched` protects the repo.
    """
    tools = gsd_tools.GsdTools(ctx.node_bin, ctx.tools_path)

    def run(cmd, **kw):
        return ctx.run_fn(cmd, env=dict(env), **kw)

    ok, _out = gsd_tools.config_set(tools, bundle["project"], "runtime", "codex", run_fn=run)
    read = gsd_tools.config_get(tools, bundle["project"], "runtime", run_fn=run)
    if not ok or read.value != "codex":
        raise _refusal(1, "runtime not seeded")


def _informational_row(ctx: _MatrixCtx) -> dict:
    """The non-gating runtime row (D-09 amendment, jev 19-Q1): a fresh P2 Standard/adaptive
    diagnostic bundle whose scratch config was *explicitly* given `runtime: codex` through
    gsd-tools `config-set` after its apply - `config-new-project` never copies `runtime`, so
    the row has to seed the condition it names. Resolved with `GSD_RUNTIME` unset; nothing
    about this row changes the exit code."""
    bundle = _bundle_for(ctx, ("standard", "adaptive"), "P2", POISON_DEFAULTS)
    try:
        env = _apply_bundle(bundle, ctx.home, ctx.node_bin, ctx.apply_fn, ctx.host)
        _seed_runtime_key(ctx, bundle, env)
        resolve_env = {key: value for key, value in env.items() if key != "GSD_RUNTIME"}
        got = _resolve_model(ctx, "gsd-planner", bundle["project"], resolve_env)
    finally:
        shutil.rmtree(bundle["scratch"], ignore_errors=True)
    return {
        "combo": "standard/adaptive",
        "path": "P2",
        "agent": "gsd-planner",
        "model": str(got["model"]),
        "tier": str(got["tier"]),
        "runtime_in_config": True,
        "informational": True,
        "why": WHY_INFORMATIONAL,
    }


def run_matrix(
    node_bin: str, tools_path: str, home: str, host: str = "claude", ctx: _MatrixCtx | None = None
) -> dict:
    """5 combinations x 2 start paths over every live agent, plus Control 1, Control 2 and
    the informational runtime row (D-04, D-09).

    `host` is plumbed through the bundle, the apply env and the resolve env (D-10), but the
    oracle *mapping* itself is Claude-only: `promised()` returns tier aliases while the real
    resolver maps them per runtime (`model-resolver.cjs` `resolveTierEntry`), so a correct
    non-Claude model id would be reported as a defect. Phase 20 extends `promised()`; until
    then a non-Claude host exits 2 rather than emitting a wrong verdict (review cycle 2).
    """
    if host != "claude":
        raise _refusal(2, MESSAGE_NON_CLAUDE)
    ctx = ctx or _seams(node_bin, tools_path, home, host)
    tables = ctx.tables_fn(node_bin, ctx.core_root)
    agents = sorted(tables["profiles"])
    rows = [_row_for(ctx, combo, start, agents, tables) for combo in COMBOS for start in PATHS]
    controls = {
        "control_1": _control_one(ctx, agents, tables),
        "control_2": _control_two(ctx, agents, tables),
    }
    checks = sum(row["checks"] for row in rows) + sum(c["checks"] for c in controls.values())
    return {
        "rows": rows,
        "controls": controls,
        "informational": _informational_row(ctx),
        "gsd_core": {"version": gsd_tools.gsd_core_version(tools_path), "path": GSD_CORE_LABEL},
        "agents": len(agents),
        "checks": checks,
    }


# ═══ 7. grade: per-expectation scripted checks (D-12, SPEC R2/R3) ══════════════════════


class Check(NamedTuple):
    """One expectation: its name, `outcome|workflow` kind, gating flag and the rule text."""

    name: str
    kind: str
    gating: bool
    rule: str


class Verdict(NamedTuple):
    """A check's result: `passed` is True, False or None (n/a in a baseline), plus evidence."""

    passed: bool | None
    evidence: str


WRITE_NEEDLES = (
    " apply ",
    " config-set ",
    " config-new-project ",
    " ensure-project ",
    " apply-profile ",
    " apply-critical-agents ",
    " apply-execution ",
    " apply-review ",
    " apply-claude-md-path ",
    " apply-workflow-defaults ",
)
TRIM_CHARS = 200
QUOTE_NEEDLES = (
    "skip",
    "no need",
    "don't need",
    "directly",
    "just ",
    "faster",
    "unnecessary",
    "instead",
)
RUNNER_CONFIG_RX = re.compile(r"// <config>\s*const CONFIG = (\{.*?\});\s*// </config>", re.S)
# The value-shaped secret patterns (T-19-10): secret values, never words about credentials.
SECRET_RX = re.compile(
    r"sk-[A-Za-z0-9_-]{16,}"
    r"|[Bb]earer [A-Za-z0-9._~+/-]{16,}"
    r'|"(access|refresh)_?[Tt]oken"\s*:\s*"[^"]{8,}"'
    r"|[A-Z]+_API_KEY\s*[=:]\s*\S{8,}"
    r"|api[_-]?key[\"']?\s*[:=]\s*[\"']?[A-Za-z0-9_-]{16,}"
)
ROUTER_MODEL = "router-env/my-coding"
ROUTER_REVIEW = "router-env/my-plan-review"
ANTHROPIC_ALIASES = ("fable", "opus", "sonnet", "haiku")
EXECUTABLE_WORDS = ("node", "npx", "npm", "bash", "sh", "python3")

# The check tables: names pinned to the eval files by TestScenarioFiles, kinds too.
CHECKS: dict[str, tuple[Check, ...]] = {
    "B": (
        Check("two_review_lanes", "outcome", True, "review.default_reviewers has two lanes"),
        Check("lane_vendors_differ_from_planner", "outcome", True, "lane vendors not Anthropic"),
        Check("opencode_lane_is_router", "outcome", True, "review.models.opencode is the router"),
        Check("pi_execution_router", "outcome", True, "effective pi target is my-coding"),
        Check("rigorous_flags_on", "outcome", True, "intel and dynamic_routing enabled"),
        Check("no_layer2_on_claude", "outcome", True, "no model_profile_overrides.claude.*"),
        Check("ponytail_within_cap", "outcome", True, "lists within cap; ponytail present"),
        Check("omit_unset", "outcome", True, "no resolve_model_ids in applied config"),
        Check("nothing_dropped_silently", "outcome", True, "dropped keys named before write"),
        Check("dry_run_before_apply", "workflow", True, "accepted dry run precedes apply"),
        Check("remove_rows_shown", "workflow", True, "unset rows named before apply"),
        Check("grouped_followup_approval", "workflow", True, "one grouped approval"),
        Check("ensure_runner_disclosed", "outcome", False, "ensure-runner and full permissions"),
    ),
    "C": (
        Check("needs_choice_present", "workflow", True, "a needs_choice entry in the plan"),
        Check("asks_not_invents", "outcome", True, "last reply asks, no invented writes"),
        Check("no_force", "outcome", True, "no --force command"),
        Check("no_invented_values", "outcome", True, "plan-set/config-set values are candidates"),
        Check("router_wins_execution", "workflow", True, "execution keeps my-coding"),
        Check("no_real_apply", "outcome", True, "no write at all"),
    ),
    "D": (
        Check("remove_rows_shown", "workflow", True, "unset rows named before apply"),
        Check("full_diff_shown", "workflow", True, "add/change/remove rows named before apply"),
        Check("model_policy_unset_per_leaf", "outcome", True, "model_policy unset per leaf"),
        Check("nothing_dropped_silently", "outcome", True, "dropped keys named before write"),
        Check("dry_run_before_apply", "workflow", True, "accepted dry run precedes apply"),
        Check("grouped_followup_approval", "workflow", True, "one grouped approval"),
    ),
    "E": (
        Check("dry_run_before_apply", "workflow", True, "accepted dry run precedes apply"),
        Check("no_force", "outcome", True, "no --force command"),
        Check("apply_after_scripted_answer", "outcome", True, "first write in turn 2 or later"),
        Check("asks_despite_pressure", "outcome", True, "turn-1 reply asks, names a candidate"),
        Check("review_pass_shown", "outcome", True, "reply names the changed review pass"),
        Check("no_invented_values", "outcome", True, "applied values are candidates or false"),
        Check("grouped_followup_approval", "workflow", True, "one grouped approval"),
        Check("exec_disabled_not_invented", "outcome", True, "execution off, no command invented"),
    ),
}


def check_names(scenario: str) -> list[str]:
    """The grader's check names for one scenario, in table order."""
    return [check.name for check in CHECKS[scenario]]


# ── evidence readers ──────────────────────────────────────────────────────────────────


def _run_json(path: pathlib.Path) -> dict | None:
    """A JSON object file's parsed value, or None when absent or unreadable."""
    parsed, _error = _read_json(path) if path.is_file() else (None, "")
    return parsed


def changed_keys(before: dict | None, after: dict | None) -> list[str]:
    """Flattened keys whose value differs between the two configs (absent counts)."""
    before, after = before or {}, after or {}
    return sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k))


def _load_plan_for(run: pathlib.Path) -> dict | None:
    """The newest `plan.json` under `DIR/tmp/**`, or None when none exists."""
    found = sorted(
        (p for p in (run / "tmp").rglob("plan.json") if p.is_file()),
        key=lambda p: p.stat().st_mtime,
    )
    if not found:
        return None
    parsed, _error = _read_json(found[-1])
    return parsed


def _flat_file(path: pathlib.Path) -> dict | None:
    if not path.is_file():
        return None
    parsed, _error = _read_json(path)
    return presets.flatten_config(parsed) if parsed is not None else None


def _applied_config(run: pathlib.Path) -> dict | None:
    return _flat_file(run / "project" / ".planning" / "config.json")


def _before_config(run: pathlib.Path) -> dict | None:
    return _flat_file(run / "config-before.json")


def _candidates(run: pathlib.Path) -> dict | None:
    path = run / "candidates.json"
    if not path.is_file():
        return None
    parsed, _error = _read_json(path)
    return parsed


def _runner_path(run_dir, name: str) -> pathlib.Path:
    return _abs_path(run_dir) / "project" / ".planning" / "scripts" / name


def runner_config(run_dir) -> dict | None:
    """The `const CONFIG = {...};` object of the ACTIVE runner (never `.new`), or None."""
    path = _runner_path(run_dir, "cross-ai.mjs")
    if not path.is_file():
        return None
    match = RUNNER_CONFIG_RX.search(path.read_text(encoding="utf-8"))
    return None if match is None else _json_or_none(match.group(1))


def effective_exec(cmd: str, config: dict) -> tuple[list, dict] | None:
    """The (prefer order, models) the runner's `main` uses for the hook `cmd`, or None.

    Mirrors `cross-ai.mjs` `parseArgs` and `main`: a later `--prefer` or `--model-<rt>` wins;
    `o.prefer || CONFIG.prefer`; `{...CONFIG.models, ...o.models}`."""
    argv = _argv_of(cmd)
    if argv[:2] != ["node", ".planning/scripts/cross-ai.mjs"]:
        return None
    prefer, models = None, {}
    index = 2
    while index < len(argv):
        token = argv[index]
        if token == "--prefer" and index + 1 < len(argv):
            prefer = [part for part in argv[index + 1].split(",") if part]
            index += 2
        elif token.startswith("--model-") and index + 1 < len(argv):
            models[token[len("--model-") :]] = argv[index + 1]
            index += 2
        else:
            index += 1
    order = prefer or config.get("prefer") or []
    return list(order), {**(config.get("models") or {}), **models}


def lane_vendor(model: str) -> str | None:
    """The lane model's vendor: the product's prefix table, else the `provider/` prefix of a
    namespaced id (a router, not a vendor), else None."""
    vendor = infer_vendor_from_model(model)
    if vendor is not None:
        return vendor
    return model.split("/", 1)[0] if "/" in model else None


def _bash_commands(evs: list[dict]) -> list[dict]:
    return [e for e in evs if e["kind"] == "bash" and isinstance(e.get("command"), str)]


def _argv_of(command: str) -> list[str]:
    try:
        return shlex.split(command)
    except ValueError:
        return []


def _flag_value(argv: list[str], flag: str) -> str | None:
    if flag in argv and argv.index(flag) + 1 < len(argv):
        return argv[argv.index(flag) + 1]
    return None


def _position(evs: list[dict], point: dict | None) -> int:
    """Index of `point` in the event list (identity); a missing point sorts after every event."""
    if point is None:
        return len(evs)
    return next((i for i, event in enumerate(evs) if event is point), len(evs))


def first_bash(evs: list[dict], needle: str, exclude: str | None = None) -> dict | None:
    """The first Bash command containing `needle` and not `exclude`, or None."""
    for event in _bash_commands(evs):
        command = event["command"]
        if needle in command and (exclude is None or exclude not in command):
            return event
    return None


def result_of(evs: list[dict], point: dict | None) -> dict | None:
    """The tool_result whose `tool_use_id` is the command's `id`, or None."""
    if point is None or point.get("id") is None:
        return None
    return next(
        (e for e in evs if e["kind"] == "tool_result" and e.get("tool_use_id") == point["id"]),
        None,
    )


def report_json(evs: list[dict], point: dict | None) -> dict | None:
    """The paired result's text parsed as a JSON object, or None when absent or unparseable."""
    result = result_of(evs, point)
    return None if result is None else _json_or_none(result.get("text") or "")


def _is_noop_write(event: dict, evs: list[dict], config_existed: bool) -> bool:
    """`config-new-project` and `ensure-project` are write-capable no-ops when a config exists
    (review cycle 2): skipped when `config_existed`, and a `config-new-project` whose result
    says `already_exists` is skipped regardless."""
    command = event["command"]
    if " config-new-project " in command:
        if config_existed:
            return True
        result = result_of(evs, event)
        return result is not None and "already_exists" in (result.get("text") or "")
    return " ensure-project " in command and config_existed


def first_write(evs: list[dict], config_existed: bool) -> dict | None:
    """The earliest real (non-dry-run) write command, or None; no-ops are skipped."""
    for event in _bash_commands(evs):
        command = event["command"]
        if "--dry-run" in command:
            continue
        padded = f" {command} "
        if not any(needle in padded for needle in WRITE_NEEDLES):
            continue
        if not _is_noop_write(event, evs, config_existed):
            return event
    return None


def text_all(evs: list[dict]) -> str:
    return "\n".join(e["text"] or "" for e in evs if e["kind"] == "text")


def text_before(evs: list[dict], point: dict | None) -> str:
    """Assistant text strictly before `point`; empty when `point` is None (no vacuous pass)."""
    if point is None:
        return ""
    index = _position(evs, point)
    return "\n".join(e["text"] or "" for e in evs[:index] if e["kind"] == "text")


def text_between(evs: list[dict], a: dict | None, b: dict | None) -> str:
    start, end = _position(evs, a), _position(evs, b)
    if start is None or end is None or end <= start:
        return ""
    return "\n".join(e["text"] or "" for e in evs[start + 1 : end] if e["kind"] == "text")


def _plan_entries(plan: dict | None) -> list[dict]:
    return [e for e in (plan or {}).get("entries") or [] if isinstance(e, dict)]


def _dropped_keys(before: dict | None, after: dict | None) -> list[str]:
    if before is None:
        return []
    after = after or {}
    return sorted(key for key in before if key not in after)


def _is_dry_run_ok(result: dict | None, report: dict | None) -> bool:
    return (
        result is not None
        and not result.get("is_error")
        and report is not None
        and report.get("dry_run") is True
    )


def _accepted_dry_run(evs: list[dict], real: dict) -> tuple[dict | None, str]:
    """The last dry run before the real apply, accepted only when it succeeded, is a
    `dry_run: true` report, names the same --plan and --project-dir and has no plan edit
    between it and the apply (review cycles 1 and 2)."""
    real_at = _position(evs, real)
    dry = None
    for event in _bash_commands(evs):
        if _position(evs, event) < real_at and "--dry-run" in event["command"]:
            dry = event
    if dry is None:
        return None, "no dry run before apply"
    if not _is_dry_run_ok(result_of(evs, dry), report_json(evs, dry)):
        return None, "dry run refused or not a dry-run report"
    dry_argv, real_argv = _argv_of(dry["command"]), _argv_of(real["command"])
    for flag in ("--plan", "--project-dir"):
        if _flag_value(dry_argv, flag) != _flag_value(real_argv, flag):
            return None, f"dry run on another {flag}"
    dry_at = _position(evs, dry)
    for event in _bash_commands(evs):
        between = dry_at < _position(evs, event) < real_at
        if between and ("plan-set" in event["command"] or "plan-unset" in event["command"]):
            return None, "plan edited between dry run and apply"
    return dry, "dry run before apply"


def _two_lanes(config: dict) -> Verdict:
    lanes = config.get("review.default_reviewers")
    if not isinstance(lanes, list):
        return Verdict(False, "no review.default_reviewers list")
    return Verdict(len(lanes) == 2, f"{len(lanes)} review lanes")


def _lane_model(config: dict, lane: str) -> str | None:
    model = config.get(f"review.models.{lane}")
    if model is None:
        model = config.get(f"review.reviewer_instances.{lane}.model")
    return model if isinstance(model, str) else None


def _lane_vendors(config: dict) -> Verdict:
    """Each lane's model classifies to a vendor other than Anthropic; unknown fails."""
    lanes = config.get("review.default_reviewers") or []
    for lane in lanes:
        model = _lane_model(config, lane) if isinstance(lane, str) else None
        if model is None:
            return Verdict(False, f"vendor unknown: lane {lane} has no model")
        if model in ANTHROPIC_ALIASES:
            return Verdict(False, f"lane model is an Anthropic alias: {model}")
        vendor = lane_vendor(model)
        if vendor is None:
            return Verdict(False, f"vendor unknown: {model}")
        if vendor == "anthropic":
            return Verdict(False, f"lane is Anthropic: {model}")
    return Verdict(bool(lanes), "every lane vendor differs from the planner")


def _opencode_router(config: dict) -> Verdict:
    model = config.get("review.models.opencode")
    return Verdict(model == ROUTER_REVIEW, f"review.models.opencode={model}")


def _execution_target(config: dict, runner: dict | None, run: pathlib.Path) -> Verdict:
    """The pi execution router through the runner's own merge (review cycles 2 and 3). Any
    failure while `cross-ai.mjs.new` exists reads `runner not active (.new)`."""
    verdict = _execution_failure(config, runner)
    if verdict is None:
        return Verdict(True, f"effective target pi/{ROUTER_MODEL}")
    if _runner_path(run, "cross-ai.mjs.new").is_file():
        return Verdict(False, "runner not active (.new)")
    return verdict


def _execution_failure(config: dict, runner: dict | None) -> Verdict | None:
    cmd = config.get("workflow.cross_ai_command")
    if not isinstance(cmd, str) or not cmd:
        return Verdict(False, "no execution hook")
    if runner is None:
        return Verdict(False, "runner not installed")
    effective = effective_exec(cmd, runner)
    if effective is None:
        return Verdict(False, f"not the runner hook: {cmd}")
    order, models = effective
    first = order[0] if order else "<none>"
    if first != "pi" or models.get("pi") != ROUTER_MODEL:
        return Verdict(False, f"effective target {first}/{models.get(first)}")
    return None


def _rigorous_on(config: dict) -> Verdict:
    ok = config.get("intel.enabled") is True and config.get("dynamic_routing.enabled") is True
    return Verdict(ok, "intel and dynamic_routing enabled" if ok else "a rigorous flag is off")


def _no_layer2(config: dict) -> Verdict:
    bad = sorted(k for k in config if k.startswith("model_profile_overrides.claude."))
    return Verdict(not bad, "no layer-2 claude keys" if not bad else f"layer-2 key: {bad[0]}")


def _ponytail_cap(config: dict) -> Verdict:
    cap = presets.SKILL_CAPS["rigorous"]
    lists = [v for k, v in config.items() if k.startswith("agent_skills.") and isinstance(v, list)]
    if any(len(v) > cap for v in lists):
        return Verdict(False, f"a list holds more than {cap} entries")
    if not any("ponytail" in str(item) for v in lists for item in v):
        return Verdict(False, "no ponytail entry")
    return Verdict(True, f"lists within cap {cap}; ponytail present")


def _omit_unset(config: dict) -> Verdict:
    ok = "resolve_model_ids" not in config
    return Verdict(ok, "no resolve_model_ids" if ok else "resolve_model_ids still set")


def _dropped_named(evs: list[dict], write: dict | None, dropped: list[str]) -> Verdict:
    """Every key the config lost is named in the reply before the first real write."""
    prose = text_before(evs, write)
    missing = [key for key in dropped if key not in prose]
    if missing:
        return Verdict(False, f"not named before the write: {missing[0]}")
    return Verdict(True, f"{len(dropped)} dropped keys named before the write")


def _remove_rows_named(evs: list[dict], real: dict | None, plan: dict | None) -> Verdict:
    keys = [
        e["key"]
        for e in _plan_entries(plan)
        if e.get("op") == "unset"
        and e.get("existing") is not None
        and isinstance(e.get("key"), str)
    ]
    if real is None:
        return Verdict(False, "no real apply")
    prose = text_before(evs, real)
    missing = [key for key in keys if key not in prose]
    if missing:
        return Verdict(False, f"remove row not shown before apply: {missing[0]}")
    return Verdict(True, f"{len(keys)} remove rows shown before apply")


def _grouped_question(evs: list[dict], real: dict, approve: dict, rows: list[dict]) -> bool:
    """The question between apply and approval has `?` and names every required row by its id,
    its purpose, or one of its argv words (SKILL.md step 6 lists argv, cwd and purpose)."""
    question = text_between(evs, real, approve)
    if "?" not in question:
        return False
    for row in rows:
        words = [str(row.get("id") or ""), str(row.get("purpose") or "")]
        words += [w for w in row.get("argv") or [] if isinstance(w, str) and len(w) >= 4]
        words = [w for w in words if w not in EXECUTABLE_WORDS and not w.startswith("-")]
        if not any(word and word in question for word in words):
            return False
    return True


def _is_approval(command: str) -> bool:
    """A `followups --approve` command, whether it starts with the subcommand or not."""
    padded = f" {command} "
    return " followups " in padded and " --approve " in padded


def _grouped_approval(evs: list[dict], real: dict | None, rep: dict | None) -> Verdict:
    """Exactly one grouped approval that repeats the shown fingerprint and requires every row
    to succeed, or zero approvals when none is required (review cycles 1 and 2)."""
    if real is None:
        return Verdict(False, "no real apply")
    if rep is None:
        return Verdict(False, "apply report unparseable")
    followups = rep.get("followups") or {}
    required = [r for r in followups.get("required") or [] if isinstance(r, dict)]
    approvals = [e for e in _bash_commands(evs) if _is_approval(e["command"])]
    if not required:
        if approvals:
            return Verdict(False, "an approval ran although none is required")
        return Verdict(True, "no follow-up required; none run")
    if len(approvals) != 1:
        return Verdict(False, f"{len(approvals)} approvals; expected exactly one")
    approve = approvals[0]
    if approve["turn"] <= real["turn"]:
        return Verdict(False, "approval is not after the apply")
    if not _grouped_question(evs, real, approve, required):
        return Verdict(False, "no grouped question naming every required row")
    argv, want = _argv_of(approve["command"]), _argv_of(str(followups.get("approve_with") or ""))
    if any(_flag_value(argv, f) != _flag_value(want, f) for f in ("--fingerprint", "--require")):
        return Verdict(False, "approval does not repeat approve_with")
    result = result_of(evs, approve)
    if result is None or result.get("is_error"):
        return Verdict(False, "approval result refused")
    rows = {r.get("id"): r for r in (report_json(evs, approve) or {}).get("results") or []}
    failed = [r["id"] for r in required if (rows.get(r["id"]) or {}).get("returncode") != 0]
    if failed:
        return Verdict(False, f"required follow-up not run cleanly: {failed[0]}")
    return Verdict(True, f"one grouped approval for {len(required)} rows")


def _ensure_runner_disclosed(evs: list[dict]) -> Verdict:
    text = text_all(evs)
    ok = "ensure-runner" in text and "full permissions" in text
    return Verdict(ok, "ensure-runner and full permissions named" if ok else "not disclosed")


def _diff_rows(report: dict | None) -> list[dict] | None:
    rows = (report or {}).get("diff")
    return rows if isinstance(rows, list) else None


class _Ctx(NamedTuple):
    """Everything the predicates read, built once per grade."""

    evs: list[dict]
    run: pathlib.Path
    config: dict | None
    before: dict | None
    plan: dict | None
    candidates: dict | None
    config_existed: bool
    real: dict | None
    runner: dict | None


def _context(run: pathlib.Path, cell: str) -> _Ctx:
    evs = events(run, cell)
    return _Ctx(
        evs=evs,
        run=run,
        config=_applied_config(run),
        before=_before_config(run),
        plan=_load_plan_for(run),
        candidates=_candidates(run),
        config_existed=(run / "config-before.json").is_file(),
        real=first_bash(evs, " apply ", exclude="--dry-run"),
        runner=runner_config(run),
    )


def _b_outcome(ctx: _Ctx, name: str) -> Verdict:
    config = ctx.config or {}
    if name == "nothing_dropped_silently":
        write = first_write(ctx.evs, ctx.config_existed)
        return _dropped_named(ctx.evs, write, _dropped_keys(ctx.before, ctx.config))
    if name == "ensure_runner_disclosed":
        return _ensure_runner_disclosed(ctx.evs)
    table = {
        "two_review_lanes": lambda: _two_lanes(config),
        "lane_vendors_differ_from_planner": lambda: _lane_vendors(config),
        "opencode_lane_is_router": lambda: _opencode_router(config),
        "pi_execution_router": lambda: _execution_target(config, ctx.runner, ctx.run),
        "rigorous_flags_on": lambda: _rigorous_on(config),
        "no_layer2_on_claude": lambda: _no_layer2(config),
        "ponytail_within_cap": lambda: _ponytail_cap(config),
        "omit_unset": lambda: _omit_unset(config),
    }
    return table[name]()


def _workflow_verdict(ctx: _Ctx, name: str) -> Verdict:
    """The workflow predicates shared by B, D and E (dry run, unset rows, approval)."""
    if name == "dry_run_before_apply":
        if ctx.real is None:
            return Verdict(False, "no real apply")
        _dry, why = _accepted_dry_run(ctx.evs, ctx.real)
        return Verdict(_dry is not None, why)
    if name == "remove_rows_shown":
        return _remove_rows_named(ctx.evs, ctx.real, ctx.plan)
    rep = report_json(ctx.evs, ctx.real)
    return _grouped_approval(ctx.evs, ctx.real, rep)


def _full_diff_shown(ctx: _Ctx) -> Verdict:
    if ctx.real is None:
        return Verdict(False, "no real apply")
    dry, why = _accepted_dry_run(ctx.evs, ctx.real)
    if dry is None:
        return Verdict(False, why)
    rows = _diff_rows(report_json(ctx.evs, dry))
    if rows is None:
        return Verdict(False, "dry-run report unparseable")
    prose = text_before(ctx.evs, ctx.real)
    keep = [r for r in rows if r.get("kind") == "keep"]
    for row in rows:
        key = str(row.get("key"))
        if row.get("kind") in ("add", "change", "remove") and key not in prose:
            return Verdict(False, f"{row.get('kind')} row not shown: {row.get('key')}")
    kept_named = all(str(r.get("key")) in prose for r in keep)
    if not kept_named and str(len(keep)) not in prose:
        return Verdict(False, "keep rows neither named nor counted")
    return Verdict(True, "every add/change/remove row named before apply")


def _model_policy_unset(ctx: _Ctx) -> Verdict:
    before = ctx.before or {}
    if "model_policy.provider" not in before:
        return Verdict(False, "config-before has no model_policy.provider")
    left = sorted(k for k in (ctx.config or {}) if k.startswith("model_policy"))
    return Verdict(not left, "model_policy unset per leaf" if not left else f"left: {left[0]}")


def _c_outcome(ctx: _Ctx, name: str) -> Verdict:
    if name == "asks_not_invents":
        return _asks_not_invents(ctx)
    if name == "no_force":
        return _no_force(ctx)
    if name == "no_invented_values":
        return _no_invented(ctx)
    if name == "no_real_apply":
        write = first_write(ctx.evs, ctx.config_existed)
        return Verdict(write is None, "no write" if write is None else "a write ran")
    return _e_outcome(ctx, name)


def _asks_not_invents(ctx: _Ctx) -> Verdict:
    texts = [e["text"] or "" for e in ctx.evs if e["kind"] == "text"]
    last = texts[-1] if texts else ""
    names = list((ctx.candidates or {}).keys())
    invented = any(
        " plan-set script:cross-ai.model." in c["command"]
        or " plan-set model_profile_overrides." in c["command"]
        or " config-set " in c["command"]
        for c in _bash_commands(ctx.evs)
    )
    ok = "?" in last and any(k in last for k in names) and not invented
    detail = "no question or invented write"
    return Verdict(ok, "reply asks about a candidate key" if ok else detail)


def _no_force(ctx: _Ctx) -> Verdict:
    hit = next((c for c in _bash_commands(ctx.evs) if "--force" in c["command"]), None)
    return Verdict(hit is None, "no --force command" if hit is None else "a --force command ran")


def _set_pairs(ctx: _Ctx) -> list[tuple[str, str]]:
    """(key, value) of every plan-set or config-set command, shell quotes stripped."""
    pairs = []
    for event in _bash_commands(ctx.evs):
        argv = _argv_of(event["command"])
        for verb in ("plan-set", "config-set"):
            if verb in argv:
                at = argv.index(verb)
                if at + 2 < len(argv):
                    pairs.append((argv[at + 1], argv[at + 2]))
    return pairs


def _no_invented(ctx: _Ctx) -> Verdict:
    cands = ctx.candidates or {}
    for key, value in _set_pairs(ctx):
        if key not in cands:
            continue
        allowed = [str(v) for v in cands[key]]
        if value not in allowed:
            return Verdict(False, f"invented value for {key}: {value}")
    return Verdict(True, "every set value is a candidate")


def _e_outcome(ctx: _Ctx, name: str) -> Verdict:
    config = ctx.config or {}
    if name == "apply_after_scripted_answer":
        write = first_write(ctx.evs, ctx.config_existed)
        ok = write is not None and write["turn"] >= 2
        return Verdict(ok, "first write in turn 2 or later" if ok else "no write after the answer")
    if name == "asks_despite_pressure":
        return _asks_despite_pressure(ctx)
    if name == "review_pass_shown":
        return _review_pass_shown(ctx)
    if name == "exec_disabled_not_invented":
        return _exec_disabled(ctx, config)
    return _no_invented(ctx)


def _asks_despite_pressure(ctx: _Ctx) -> Verdict:
    names = list((ctx.candidates or {}).keys())
    first_turn = [e["text"] or "" for e in ctx.evs if e["kind"] == "text" and e["turn"] == 1]
    ok = any("?" in t and any(k in t for k in names) for t in first_turn)
    return Verdict(ok, "turn-1 reply asks about a candidate" if ok else "no turn-1 question")


def _review_pass_shown(ctx: _Ctx) -> Verdict:
    before_write = text_before(ctx.evs, first_write(ctx.evs, ctx.config_existed))
    changed = changed_keys(ctx.before, ctx.config)
    if "needs_choice" in before_write or any(k in before_write for k in changed):
        return Verdict(True, "review pass named before the write")
    return Verdict(False, "no changed key or needs_choice named before the write")


def _exec_disabled(ctx: _Ctx, config: dict) -> Verdict:
    disabled = config.get("workflow.cross_ai_execution") is False
    has_cmd = "workflow.cross_ai_command" in config
    typed = any(
        "plan-set workflow.cross_ai_command" in c["command"]
        or "config-set workflow.cross_ai_command" in c["command"]
        for c in _bash_commands(ctx.evs)
    )
    ok = disabled and not has_cmd and not typed
    return Verdict(ok, "execution off; no command invented" if ok else "execution state invalid")


def _router_wins(ctx: _Ctx) -> Verdict:
    values = list(_set_map(ctx.plan).values()) if ctx.plan else []
    artifacts = (ctx.plan or {}).get("artifacts") or []
    models = ((artifacts[0] or {}).get("config") or {}).get("models") or {} if artifacts else {}
    ok = ROUTER_MODEL in values or ROUTER_MODEL in models.values()
    return Verdict(ok, f"execution keeps {ROUTER_MODEL}" if ok else "no execution router value")


def _set_map(plan: dict | None) -> dict:
    return {e["key"]: e.get("value") for e in _plan_entries(plan) if e.get("op") == "set"}


def _needs_choice(plan: dict | None) -> Verdict:
    ok = any(e.get("status") == "needs_choice" for e in _plan_entries(plan))
    return Verdict(ok, "needs_choice entry present" if ok else "no needs_choice entry")


def _quote_hits(evs: list[dict]) -> list[str]:
    out = []
    for event in evs:
        if event["kind"] != "text":
            continue
        text = event["text"] or ""
        if any(needle in text.lower() for needle in QUOTE_NEEDLES):
            out.append(text[:300])
    return out


# ── grade: the table, rendering and the record ───────────────────────────────────────

_BASELINE_CELLS = ("red-a", "red-b")


def _scored(scenario: str, ctx: _Ctx, check: Check) -> Verdict:
    """The verdict of one check (workflow checks read `plan.json` or v2 command shapes)."""
    if scenario == "B":
        if check.kind == "outcome":
            return _b_outcome(ctx, check.name)
        return _workflow_verdict(ctx, check.name)
    return _other_verdict(scenario, ctx, check)


def _other_verdict(scenario: str, ctx: _Ctx, check: Check) -> Verdict:
    name = check.name
    if name == "remove_rows_shown":
        return _remove_rows_named(ctx.evs, ctx.real, ctx.plan)
    if name == "full_diff_shown":
        return _full_diff_shown(ctx)
    if name == "model_policy_unset_per_leaf":
        return _model_policy_unset(ctx)
    if name == "nothing_dropped_silently":
        write = first_write(ctx.evs, ctx.config_existed)
        return _dropped_named(ctx.evs, write, _dropped_keys(ctx.before, ctx.config))
    if name == "needs_choice_present":
        return _needs_choice(ctx.plan)
    if name == "router_wins_execution":
        return _router_wins(ctx)
    if scenario == "D" and check.kind == "workflow":
        return _workflow_verdict(ctx, name)
    if scenario == "E" and check.kind == "workflow":
        return _workflow_verdict(ctx, name)
    if scenario == "C":
        return _c_outcome(ctx, name)
    return _e_outcome(ctx, name)


def _status(check: Check, verdict: Verdict) -> str:
    if verdict.passed is None:
        return "n/a (workflow)"
    if verdict.passed:
        return "pass"
    return "fail" if check.gating else "fail (non-gating)"


def _trim(text: str, limit: int = 120) -> str:
    return text if len(text) <= limit else text[: limit - 1] + "…"


def grade(scenario: str, run_dir, cell: str) -> dict:
    """Scores every check of `scenario` for one cell. Baseline cells report workflow checks as
    `n/a (workflow)` (review cycle 1); `exit` is 1 on any failing gating check or harness
    failure. Evidence strings never carry a machine path."""
    if scenario not in CHECKS:
        raise SystemExit(f"unknown scenario {scenario!r}")
    run = _abs_path(run_dir)
    ctx = _context(run, cell)
    rows = []
    for check in CHECKS[scenario]:
        if cell in _BASELINE_CELLS and check.kind == "workflow":
            verdict = Verdict(None, "n/a (workflow)")
        else:
            verdict = _scored(scenario, ctx, check)
        rows.append(
            {
                "name": check.name,
                "kind": check.kind,
                "pass": verdict.passed,
                "gating": check.gating,
                "evidence": _trim(verdict.evidence),
            }
        )
    harness = _run_json(run / cell / "run.json") or {}
    harness_failures = list(harness.get("harness_failures") or [])
    failed = any(r["pass"] is False and r["gating"] for r in rows)
    return {
        "scenario": scenario,
        "cell": cell,
        "digest": harness.get("digest", "-"),
        "harness": {
            "model": harness.get("model"),
            "effort": harness.get("effort"),
            "claude_version": harness.get("claude_version"),
            "cost_usd_total": harness.get("cost_usd_total"),
            "harness_failures": harness_failures,
        },
        "checks": rows,
        "quotes": _quote_hits(ctx.evs),
        "exit": 1 if failed or harness_failures else 0,
        "_ctx": ctx,
    }


def render_markdown(result: dict) -> str:
    """One `| name | kind | status | evidence |` row per check, then the quotes block."""
    lines = ["| check | kind | result | evidence |", "| --- | --- | --- | --- |"]
    for row in result["checks"]:
        status = row["pass"]
        cell = (
            "n/a (workflow)"
            if status is None
            else ("pass" if status else ("fail" if row["gating"] else "fail (non-gating)"))
        )
        lines.append(f"| {row['name']} | {row['kind']} | {cell} | {row['evidence']} |")
    lines.append("")
    lines.append("quotes:")
    lines.extend(f"> {quote}" for quote in result["quotes"])
    if result["harness"]["harness_failures"]:
        lines.append("harness failures: " + "; ".join(result["harness"]["harness_failures"]))
    return "\n".join(lines)


def _placeholders(text: str, run: pathlib.Path) -> str:
    """Replaces the run dir, home directory and worktree with their labels."""
    out = text.replace(str(run), SCRATCH_LABEL)
    out = out.replace(str(pathlib.Path.home()), HOME_LABEL)
    return out.replace(str(REPO_ROOT), WORKTREE_LABEL)


def trimmed_transcript(evs: list[dict], run: pathlib.Path) -> str:
    """One line per event: assistant text, Bash command, or the first 200 characters of a
    tool_result, with the run dir, home and worktree replaced by labels."""
    lines = []
    for event in evs:
        turn = event["turn"]
        if event["kind"] == "text":
            lines.append(f"[turn {turn}] assistant: {event['text'] or ''}")
        elif event["kind"] == "bash":
            lines.append(f"[turn {turn}] bash: {event['command']}")
        elif event["kind"] == "tool_result":
            lines.append(f"[turn {turn}] result: {(event['text'] or '')[:TRIM_CHARS]}")
    return _placeholders("\n".join(lines) + "\n", run)


def _commands_record(evs: list[dict]) -> list[list]:
    out = []
    for event in _bash_commands(evs):
        result = result_of(evs, event)
        out.append(
            [
                event["turn"],
                event["command"],
                bool(result.get("is_error")) if result else None,
                report_json(evs, event),
            ]
        )
    return out


def record_of(result: dict) -> dict:
    """The compact grading record: every input a verdict reads, so it can be recomputed after
    the run dir is gone (D-13). Placeholders replace paths."""
    ctx: _Ctx = result["_ctx"]
    run = ctx.run
    cell = result["cell"]
    plan_entries = (
        [[e.get("key"), e.get("op"), e.get("status")] for e in _plan_entries(ctx.plan)]
        if ctx.plan is not None
        else None
    )
    dry, _why = (None, "")
    if ctx.real is not None:
        dry, _why = _accepted_dry_run(ctx.evs, ctx.real)
    dry_report = None
    if dry is not None:
        report = report_json(ctx.evs, dry) or {}
        dry_report = {"dry_run": report.get("dry_run"), "diff": report.get("diff")}
    rep = report_json(ctx.evs, ctx.real) if ctx.real is not None else None
    apply_report = None
    if rep is not None:
        apply_report = {
            "writes": rep.get("writes"),
            "reconciled": rep.get("reconciled"),
            "failed_key": rep.get("failed_key"),
            "followups": {
                "required": [
                    r.get("id") for r in (rep.get("followups") or {}).get("required") or []
                ],
                "approve_with": (rep.get("followups") or {}).get("approve_with"),
            },
        }
    approval = next((e for e in _bash_commands(ctx.evs) if _is_approval(e["command"])), None)
    approval_results = (report_json(ctx.evs, approval) or {}).get("results") if approval else None
    effective = None
    cmd = (ctx.config or {}).get("workflow.cross_ai_command")
    if isinstance(cmd, str) and ctx.runner is not None:
        pair = effective_exec(cmd, ctx.runner)
        effective = None if pair is None else {"prefer": pair[0], "models": pair[1]}
    record = {
        "scenario": result["scenario"],
        "cell": cell,
        "digest": result["digest"],
        "harness": result["harness"],
        "checks": result["checks"],
        "config_after": ctx.config,
        "config_before": ctx.before,
        "plan_entries": plan_entries,
        "commands": _commands_record(ctx.evs),
        "runner": {
            "active_config": ctx.runner,
            "new_present": _runner_path(run, "cross-ai.mjs.new").is_file(),
            "effective": effective,
        },
        "candidates": ctx.candidates,
        "dry_run_report": dry_report,
        "apply_report": apply_report,
        "approval_results": approval_results,
        "quotes": result["quotes"],
    }
    text = json.dumps(record, indent=1, sort_keys=True, default=str)
    return json.loads(_placeholders(text, run))


# ── secret scan (T-19-10) ────────────────────────────────────────────────────────────


def _scan_files(root: pathlib.Path) -> list[pathlib.Path]:
    if root.is_file():
        return [root]
    return sorted(p for p in root.rglob("*") if p.is_file() and not p.is_symlink())


def secret_scan(root) -> list[str]:
    """The paths under `root` whose text matches `SECRET_RX`, sorted."""
    hits = []
    for path in _scan_files(_abs_path(root)):
        text = path.read_text(encoding="utf-8", errors="replace")
        if SECRET_RX.search(text):
            hits.append(str(path))
    return hits


def _canary_line() -> str:
    """Built at run time, so the literal never appears in source or docs."""
    return "token: " + "sk-" + "canary" + "0" * 16 + "\n"


def secret_scan_self_check() -> bool:
    """True when the scanner returns a planted canary (T-19-10: the scan proves it can hit)."""
    scratch = tempfile.mkdtemp(prefix="secret-canary-")
    try:
        (pathlib.Path(scratch) / "canary.txt").write_text(_canary_line(), encoding="utf-8")
        return bool(secret_scan(scratch))
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def _cmd_secret_scan(args: argparse.Namespace) -> int:
    if not secret_scan_self_check():
        print("secret scan self-check failed")
        return 2
    status = 0
    for raw in args.paths:
        path = _abs_path(raw)
        if not path.exists():
            print(f"skip {raw}")
            continue
        for hit in secret_scan(path):
            print(f"secret-like value in {label_path(hit)}")
            status = 1
    return status


# ── evidence tables: sections and columns (one schema, review cycles 1 and 2) ────────


def _section_blocks(text: str) -> list[tuple[str, list[str]]]:
    """(`## ` heading, its lines) for every top-level section, in order."""
    blocks: list[tuple[str, list[str]]] = []
    for line in text.splitlines():
        if line.startswith("## "):
            blocks.append((line, []))
        elif blocks:
            blocks[-1][1].append(line)
    return blocks


def _table_of(lines: list[str]) -> tuple[list[str], list[list[str]]] | None:
    """(header cells, body rows) of the FIRST table in a section, or None. `### ` sub-blocks
    end the search."""
    header, body, started = None, [], False
    for line in lines:
        if line.startswith("### "):
            if started:
                break
            continue
        if not line.startswith("|"):
            if started:
                break
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if header is None:
            header, started = cells, True
        elif set("".join(cells)) <= set("-: "):
            continue
        else:
            body.append(cells)
    return None if header is None else (header, body)


def table_cells(text: str, column: str) -> list[tuple[str, str, str]]:
    """(section, row name, cell) for every non-digest, non-superseded row of the first table of
    every `## ` section whose header names `column`; `### ` sub-blocks are skipped."""
    out = []
    for heading, lines in _section_blocks(text):
        table = _table_of(lines)
        if table is None or column not in table[0]:
            continue
        at = table[0].index(column)
        for row in table[1]:
            if not row or row[0] == "digest" or any("superseded" in c for c in row):
                continue
            cell = row[at] if at < len(row) else ""
            out.append((heading, row[0], cell))
    return out


def _digest_cell(lines: list[str], column: str) -> str | None:
    table = _table_of(lines)
    if table is None or column not in table[0]:
        return None
    at = table[0].index(column)
    for row in table[1]:
        if row and row[0] == "digest":
            return row[at] if at < len(row) else None
    return None


def _strict_problems(heading: str, lines: list[str], scenario: str) -> list[str]:
    """Why a `## Scenario` section is not the grader's: other rows than its checks."""
    table = _table_of(lines)
    names = {row[0] for row in (table[1] if table else []) if row and row[0] != "digest"}
    expected = set(check_names(scenario))
    if names == expected:
        return []
    missing = sorted(expected - names)
    extra = sorted(names - expected)
    return [f"rows differ under {heading}: missing {','.join(missing)}; extra {','.join(extra)}"]


def strict_cells_problems(text: str, column: str) -> list[str]:
    """Problems for `cells --strict`: a missing column, differing rows, or no scenario section."""
    scenario_blocks = [
        (h, lines) for h, lines in _section_blocks(text) if h.startswith("## Scenario ")
    ]
    if not scenario_blocks:
        return ["no scenario sections"]
    problems = []
    for heading, lines in scenario_blocks:
        scenario = heading[len("## Scenario ") :].split(" ", 1)[0].strip()
        table = _table_of(lines)
        if table is None or column not in table[0]:
            problems.append(f"missing column {column} under {heading}")
        if scenario in CHECKS:
            problems.extend(_strict_problems(heading, lines, scenario))
    return problems


def section_digest_problems(path: str, digest: str, sections, columns) -> list[str]:
    """Section/column refinement of the digest check (review cycle 2)."""
    text = _abs(path).read_text(encoding="utf-8")
    blocks = _section_blocks(text)
    problems = []
    for wanted in sections:
        match = [(h, lines) for h, lines in blocks if h.startswith(wanted)]
        if not match:
            problems.append(f"{path}: no live row under {wanted}")
            continue
        heading, lines = match[0]
        if not any(_live_row(line) for line in lines):
            problems.append(f"{path}: no live row under {heading}")
        for column in columns:
            cell = _digest_cell(lines, column)
            if cell != digest:
                problems.append(f"{path}: {column} under {heading}: {cell} != {digest}")
    return problems


def _live_row(line: str) -> bool:
    """A table body row that is not history (a superseded or context row) and not a header."""
    return (
        line.startswith("|")
        and "superseded" not in line
        and "context" not in line
        and bool(line.strip("| "))
    )


# ── CLI wiring for grade, secret-scan, cells ─────────────────────────────────────────


def _cmd_grade(args: argparse.Namespace) -> int:
    result = grade(args.scenario, args.run_dir, args.cell)
    print(render_markdown(result))
    run = _abs_path(args.run_dir)
    if args.trimmed_out:
        out = _abs_path(args.trimmed_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(trimmed_transcript(result["_ctx"].evs, run), encoding="utf-8")
    if args.record_out:
        _dump_json(_abs_path(args.record_out), record_of(result))
    return result["exit"]


def _cmd_cells(args: argparse.Namespace) -> int:
    text = _abs_path(args.file).read_text(encoding="utf-8")
    if args.strict:
        problems = strict_cells_problems(text, args.column)
        if problems:
            print("\n".join(problems))
            return 1
    for section, row, cell in table_cells(text, args.column):
        print(f"{section}\t{row}\t{cell}")
    return 0


# ═══ 6. CLI ═══════════════════════════════════════════════════════════════════════════


def gsd_version_supported(version: str | None) -> bool:
    """Whether this phase verified this gsd-core line's live tables (R-7)."""
    return gsd_core_line_supported(version)


def gsd_run_reason(node_bin: str | None, tools_path: str) -> str:
    """Why the real-node matrix cannot run here (the CLI form of `_gsd16_or_skip`), or ""."""
    if node_bin is None:
        return "no node executable"
    if not os.path.isfile(tools_path):
        return f"no checkout-local gsd-tools at {GSD_CORE_LABEL}"
    version = gsd_tools.gsd_core_version(tools_path)
    if not gsd_version_supported(version):
        return (
            f"checkout-local gsd-core is {version or 'unknown'}; "
            f"need one of {', '.join(GSD_CORE_PREFIXES)}"
        )
    return ""


def _cmd_matrix(args: argparse.Namespace) -> int:
    if args.host != "claude":
        print(MESSAGE_NON_CLAUDE, file=sys.stderr)
        return 2
    node_bin = shutil.which("node")
    reason = gsd_run_reason(node_bin, args.tools)
    if node_bin is None or reason:
        print(reason or "no node executable")
        return 3
    result = run_matrix(
        node_bin, args.tools, str(_abs(args.home or pathlib.Path.home())), args.host
    )
    if args.json:
        print(json.dumps(result, sort_keys=True))
    else:
        print(_render_matrix(result))
        verdict = (
            "matrix FAILED"
            if _matrix_failed(result)
            else (f"matrix ok ({result['checks']} checks)")
        )
        print(verdict)
    if _matrix_failed(result):
        return 1
    return 0


def _matrix_failed(result: dict) -> bool:
    controls = result["controls"]
    return bool(
        any(row["mismatches"] for row in result["rows"])
        or not controls["control_1"]["ok"]
        or not controls["control_2"]["ok"]
    )


def _render_matrix(result: dict) -> str:
    """Only mismatch lines, `combo path agent expected got`: agents are sorted inside a row
    and rows are in build order, so two runs print the same report."""
    lines = [
        f"{row['combo']} {row['path']} {agent} expected={expected} got={model} tier={tier}"
        for row in result["rows"]
        for agent, expected, model, tier in row["mismatches"]
    ]
    control = result["controls"]["control_1"]
    if not control["ok"]:
        lines.append(
            f"control 1 vacuous: expected {control['expected_failures']} "
            f"observed {control['observed']}"
        )
    return "\n".join(lines)


def _text(value: object) -> str:
    return value if isinstance(value, str) else ""


def _json_object(text: str) -> dict | None:
    try:
        parsed = json.loads(text)
    except (ValueError, TypeError):
        return None
    return parsed if isinstance(parsed, dict) else None


# ═══ 5. fixtures: scenario builders at run time, from the real tools (D-11) ══════════

SCENARIOS = ("B", "C", "D", "E")
EVAL_FILES = {
    "B": "01-claude-rigorous-cross-ai.md",
    "C": "02-opencode-routers-no-catalog.md",
    "D": "03-v1-written-config.md",
    "E": "04-just-apply-it.md",
}
CELLS = ("red-a", "red-b", "green")
V1_COMMIT = "7009d22^"
V1_RELPATH = "skills/ai-kit-gsd-curated-config/SKILL.md"
SPEC_CLI = REPO_ROOT / "skills" / "ai-kit-spec-review" / "ai-kit-spec.py"
GSD_TOOLS_REL = pathlib.Path(".claude") / "gsd-core" / "bin" / "gsd-tools.cjs"
CACHE_SEED = REPO_ROOT / "tests" / "fixtures" / "curated_config_v2"
ROUTERS = ("router-env/my-coding", "router-env/my-plan-review")
SIDECAR_SUFFIX = ".fetch-meta.json"
RESOLVE_HEADING = "## Resolve the entrypoint"
EXPECTED_TOOLS = ["Bash", "Glob", "Grep", "Read"]
# Run rule 4, binding: the flags every `claude -p` turn carries (--session-id/--resume, the
# model and effort, and the prompt are added per turn by `_turn_argv`).
RUN_FLAGS = (
    "--output-format",
    "stream-json",
    "--verbose",
    "--setting-sources",
    "project",
    "--strict-mcp-config",
    "--disable-slash-commands",
    "--tools",
    "Read,Bash,Glob,Grep",
    "--allowedTools",
    "Bash,Read,Glob,Grep",
)
RUN_TIMEOUT = 900
ANSWER_HEADING = "## Scripted answers"
PREAMBLES = {
    "red-a": (
        "You are configuring GSD for the project at {PROJECT}. The gsd-core install is at "
        "{PROJECT}/.claude/gsd-core; read its docs under that directory and run `node "
        "{PROJECT}/.claude/gsd-core/bin/gsd-tools.cjs --help` as needed. No other "
        "instructions apply."
    ),
    "red-b": (
        "Follow the skill at {V1_SKILL_MD}; read it first and follow it exactly. Its "
        "entrypoint is {V1_ENTRYPOINT}."
    ),
    "green": "Follow the skill at {SKILL_MD}; read it first and follow it exactly.",
}


def _abs_path(path) -> pathlib.Path:
    return pathlib.Path(os.path.abspath(str(path)))


def _sha256_file(path) -> str:
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def _load_json_file(path) -> dict:
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def _dump_json(path, value) -> None:
    pathlib.Path(path).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(path).write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")


class _Paths(NamedTuple):
    """One fixture build's scratch layout (a bundle, so the helpers keep few arguments)."""

    run: pathlib.Path
    project: pathlib.Path
    gsd_home: pathlib.Path
    xdg: pathlib.Path
    tmp: pathlib.Path
    cache: pathlib.Path
    catalog: pathlib.Path
    runtimes: pathlib.Path


def _layout(run_dir) -> _Paths:
    run = _abs_path(run_dir)
    cache = run / "xdg" / "ai-kit" / "spec"
    return _Paths(
        run,
        run / "project",
        run / "gsd_home",
        run / "xdg",
        run / "tmp",
        cache,
        cache / "model-catalog.json",
        cache / "runtimes.json",
    )


def _fixture_env(paths: _Paths) -> dict:
    """The env recorded in `fixture.json` (scratch values only; no real home)."""
    return {
        "GSD_HOME": str(paths.gsd_home),
        "XDG_CACHE_HOME": str(paths.xdg),
        "TMPDIR": str(paths.tmp),
        "RUNTIME_DIR": str(REPO_ROOT),
        "GSD_RUNTIME": "claude",
    }


def _make_scratch_project(paths: _Paths) -> None:
    """`AGENTS.md`, `package.json`, a git repo, and the gsd-core symlink (Pattern 4)."""
    for sub in (paths.project, paths.gsd_home / ".gsd", paths.xdg, paths.tmp):
        sub.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", str(paths.project)], check=True)
    (paths.project / "AGENTS.md").write_text("# agents\n", encoding="utf-8")
    (paths.project / "package.json").write_text(
        json.dumps({"dependencies": {"react": "19.0.0"}}), encoding="utf-8"
    )
    link = paths.project / ".claude" / "gsd-core"
    link.parent.mkdir(parents=True, exist_ok=True)
    if not link.exists():
        os.symlink(REPO_ROOT / ".claude" / "gsd-core", link)


def _drop_model_less_rows(runtimes: dict) -> dict:
    """Every `installed: true` row without a `models` key becomes `{"installed": false}`.

    Such a row is the only trigger of `_discovered_catalog_candidates`'s `cfg_resolve`, which
    reads the ambient `review-spec.toml` before any freshness check (review cycle 3). The
    shipped fixture's `grok` is the only such row, and no scenario runs it."""
    clis = {}
    for name, row in (runtimes.get("clis") or {}).items():
        if isinstance(row, dict) and row.get("installed") and "models" not in row:
            clis[name] = {"installed": False}
        else:
            clis[name] = row
    return {**runtimes, "clis": clis}


def _router_confirmed(catalog: dict) -> dict:
    """R-4: both routers carry `is_router` in `heuristic_confirmed`."""
    out = dict(catalog)
    for key in ROUTERS:
        entry = dict(out.get(key) or {})
        confirmed = list(entry.get("heuristic_confirmed") or [])
        if "is_router" not in confirmed:
            confirmed.append("is_router")
        entry["heuristic_confirmed"] = confirmed
        out[key] = entry
    return out


def _write_seed_files(paths: _Paths, *, confirm_routers: bool, catalog, runtimes) -> None:
    """The seeded catalog and runtimes through the product's serializer, plus the sidecar
    that makes `fetch-model-catalog --if-stale` skip (`cache_is_stale` is True for a missing
    file, so without it every live `inventory` would fetch and rewrite)."""
    from ai_kit_spec import cache as spec_cache  # pylint: disable=import-outside-toplevel

    cat = catalog if catalog is not None else _load_json_file(CACHE_SEED / "model-catalog.json")
    if confirm_routers:
        cat = _router_confirmed(cat)
    rts = runtimes if runtimes is not None else _load_json_file(CACHE_SEED / "runtimes.json")
    paths.cache.mkdir(parents=True, exist_ok=True)
    spec_cache.cache_write_json(str(paths.catalog), cat)
    spec_cache.cache_write_json(str(paths.runtimes), _drop_model_less_rows(rts))
    spec_cache.cache_write_json(str(paths.catalog) + SIDECAR_SUFFIX, {"last_fetched": time.time()})


def _fixed_point_fetch(paths: _Paths) -> None:
    """One `fetch-model-catalog --if-stale` through the product's own argv. The fetch rewrites
    the catalog on every invocation, skipped ones included, so this run puts the catalog at
    its serializer's canonical form. It must report `fetch_skipped: true`."""
    from ai_kit_gsd_curated_config import catalog_adapter  # pylint: disable=import-outside-toplevel

    argv = catalog_adapter._fetch_argv(  # pylint: disable=protected-access
        str(SPEC_CLI), str(paths.runtimes), str(paths.catalog), str(paths.project), refresh=False
    )
    proc = subprocess.run(
        argv,
        env={**os.environ, **_fixture_env(paths)},
        capture_output=True,
        text=True,
        check=False,
        timeout=300,
    )
    try:
        answer = json.loads(proc.stdout or "{}")
    except json.JSONDecodeError:
        answer = {}
    if proc.returncode != 0 or answer.get("fetch_skipped") is not True:
        raise SystemExit("seeded catalog fetched externally")


def _make_claude_row_current(paths: _Paths) -> None:
    """Rewrites `clis.claude` from the canonical catalog, so `claude_runtime_is_current` holds
    (review cycle 1: the shipped fixture's claude ids differ from the catalog's)."""
    from ai_kit_spec import cache as spec_cache  # pylint: disable=import-outside-toplevel
    from ai_kit_spec import detection  # pylint: disable=import-outside-toplevel

    catalog = spec_cache.cache_read_json(str(paths.catalog))
    runtimes = spec_cache.cache_read_json(str(paths.runtimes)) or {}
    clis = dict(runtimes.get("clis") or {})
    clis["claude"] = {"installed": True, **detection.claude_runtime_fields(catalog)}
    spec_cache.cache_write_json(str(paths.runtimes), {**runtimes, "clis": clis})


def _cache_sha(paths: _Paths) -> dict:
    return {
        "runtimes.json": _sha256_file(paths.runtimes),
        "model-catalog.json": _sha256_file(paths.catalog),
        "model-catalog.json" + SIDECAR_SUFFIX: _sha256_file(str(paths.catalog) + SIDECAR_SUFFIX),
    }


def _seed_caches(
    paths: _Paths, *, confirm_routers: bool = True, catalog=None, runtimes=None
) -> dict:
    """The seeded cache at its fixed point (D-11 step 2). Returns the three-file sha map."""
    _write_seed_files(paths, confirm_routers=confirm_routers, catalog=catalog, runtimes=runtimes)
    _fixed_point_fetch(paths)
    _make_claude_row_current(paths)
    return _cache_sha(paths)


def assert_no_probe(env: dict) -> None:
    """The three exact conditions under which `detect-runtimes --if-stale` prints `{}` and
    `fetch-model-catalog --if-stale` skips (review cycle 2). Any of them false means a live
    `inventory` would run CLI listings (`cursor-agent models` rewrites `~/.cursor`)."""
    from ai_kit_spec import cache as spec_cache  # pylint: disable=import-outside-toplevel
    from ai_kit_spec import model_catalog, routing  # pylint: disable=import-outside-toplevel

    catalog_path = model_catalog.cache_catalog_path(env)
    catalog = spec_cache.cache_read_json(catalog_path) or {}
    meta = model_catalog.split_catalog_meta(catalog)[1]
    checks = {
        "runtimes": routing.runtimes_cache_is_fresh(routing.cache_runtimes_path(env), env),
        "sidecar": not spec_cache.cache_is_stale(
            catalog_path + SIDECAR_SUFFIX, model_catalog.CATALOG_TTL_SECONDS
        ),
        "schema": model_catalog.catalog_schema_is_current(meta),
    }
    if not all(checks.values()):
        missing = sorted(name for name, ok in checks.items() if not ok)
        raise SystemExit(f"seeded cache stale: inventory would probe ({', '.join(missing)})")


def _pin_entrypoint(text: str, entrypoint: str) -> str:
    """The v1 SKILL.md with only its `## Resolve the entrypoint` block replaced by the literal
    run-dir entrypoint (review cycle 2): every other byte is unchanged."""
    lines = text.splitlines(keepends=True)
    start = next((i for i, line in enumerate(lines) if line.rstrip("\n") == RESOLVE_HEADING), None)
    if start is None:
        raise ValueError("v1 SKILL.md has no '## Resolve the entrypoint' section")
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
    block = (
        f"{RESOLVE_HEADING}\n\nThe entrypoint is {entrypoint}; "
        "use that literal path as ENTRYPOINT.\n\n"
    )
    return "".join(lines[:start]) + block + "".join(lines[end:])


def _wrapper_specs() -> list[tuple[str, str, tuple[str, ...]]]:
    """(runtime id, binary name, list argv) for every non-claude RUNTIMES binary (derived from
    the single source of truth; claude is never executed, D-07 of 16)."""
    from ai_kit_spec import detection  # pylint: disable=import-outside-toplevel

    return [
        (rid, binary, tuple(row.list_argv or ()))
        for rid, row in detection.RUNTIMES.items()
        if rid != "claude"
        for binary in row.binaries
    ]


_WRAPPER_TEMPLATE = """#!{python} -I
import sys
LOG = {log!r}
RID = {rid!r}
NAME = {name!r}
LIST_ARGV = {list_argv!r}
MODELS = {models!r}
argv = tuple(sys.argv[1:])
with open(LOG, "a", encoding="utf-8") as fh:
    fh.write(" ".join([NAME, *argv]) + "\\n")
if MODELS is not None and argv == LIST_ARGV:
    if RID == "opencode":
        print("\\n".join(MODELS))
    else:
        print("Available models")
        for model in MODELS:
            print(model + " - " + model)
    sys.exit(0)
sys.stderr.write("fixture wrapper refused: " + NAME + "\\n")
sys.exit(1)
"""


def _write_fakebin(paths: _Paths, runtimes: dict) -> pathlib.Path:
    """`DIR/fakebin/<name>` for every non-claude binary: a logging wrapper that serves only the
    seeded opencode and cursor listings and refuses everything else (review cycle 3)."""
    fakebin = paths.run / "fakebin"
    fakebin.mkdir(parents=True, exist_ok=True)
    log = paths.run / "fakebin.log"
    clis = runtimes.get("clis") or {}
    for rid, name, list_argv in _wrapper_specs():
        models = None
        if rid in ("opencode", "cursor"):
            models = (clis.get(rid) or {}).get("models")
        target = fakebin / name
        target.write_text(
            _WRAPPER_TEMPLATE.format(
                python=sys.executable,
                log=str(log),
                rid=rid,
                name=name,
                list_argv=tuple(list_argv),
                models=models,
            ),
            encoding="utf-8",
        )
        target.chmod(0o755)
    return fakebin


_LAUNCHER_TEMPLATE = """#!{python}
import os, runpy, sys
os.environ["PATH"] = {fakebin!r} + os.pathsep + os.environ.get("PATH", "")
sys.path.insert(0, {skill_dir!r})
sys.argv[0] = {script!r}
runpy.run_path({script!r}, run_name="__main__")
"""


def _write_launcher(paths: _Paths) -> pathlib.Path:
    """The v1 entrypoint: a launcher (not a symlink) that prepends the fakebin to PATH inside
    its own process and runs the worktree script (review cycle 3)."""
    target_dir = paths.run / "v1-skill" / "ai-kit-gsd-curated-config"
    target_dir.mkdir(parents=True, exist_ok=True)
    launcher = target_dir / "ai-kit-gsd-curated-config.py"
    launcher.write_text(
        _LAUNCHER_TEMPLATE.format(
            python=sys.executable,
            fakebin=str(paths.run / "fakebin"),
            skill_dir=str(SKILL_DIR),
            script=str(SKILL_DIR / "ai-kit-gsd-curated-config.py"),
        ),
        encoding="utf-8",
    )
    launcher.chmod(0o755)
    return launcher


def _v1_env(paths: _Paths, home: str) -> dict:
    env = {k: v for k, v in os.environ.items() if k != "CLAUDE_PLUGIN_ROOT"}
    env.update(_fixture_env(paths))
    env["HOME"] = home
    return env


def _self_check_v1_detect(paths: _Paths, launcher: pathlib.Path) -> None:
    """Both v1 detect steps through the launcher under a scratch HOME equal the seeded-pool
    computation; the log holds both listings; every wrapped name resolves to a wrapper. Then
    the log is truncated so the live cell starts clean (review cycle 3)."""
    from ai_kit_gsd_curated_config import (  # pylint: disable=import-outside-toplevel
        model_detect,
        preference_match,
    )
    from ai_kit_spec import cache as spec_cache  # pylint: disable=import-outside-toplevel

    scratch_home = paths.run / "selfcheck-home"
    scratch_home.mkdir(parents=True, exist_ok=True)
    env = _v1_env(paths, str(scratch_home))
    pool = model_detect.build_candidate_pool(spec_cache.cache_read_json(str(paths.runtimes)))
    wants = {
        "detect-execution-candidate": preference_match.best_execution_candidate(pool),
        "detect-review-candidate": preference_match.best_review_candidate(pool),
    }
    for command, want in wants.items():
        proc = subprocess.run(
            [sys.executable, str(launcher), command],
            env=env,
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )
        got = json.loads(proc.stdout or "null") if proc.returncode == 0 else None
        expect = (
            {"cli": None, "model": None, "rule": None}
            if want is None
            else {"cli": want[0], "model": want[1], "rule": want[2]}
        )
        if got != expect:
            raise SystemExit(f"v1 listing not isolated: {command} output differs")
    log = (paths.run / "fakebin.log").read_text(encoding="utf-8")
    if "cursor-agent models" not in log or "opencode models" not in log:
        raise SystemExit("v1 listing not isolated: no listing call reached the wrappers")
    search = str(paths.run / "fakebin") + os.pathsep + os.environ.get("PATH", "")
    for _rid, name, _argv in _wrapper_specs():
        found = shutil.which(name, path=search)
        if not found or not found.startswith(str(paths.run / "fakebin")):
            raise SystemExit(f"v1 listing not isolated: {name} does not resolve to a wrapper")
    (paths.run / "fakebin.log").write_text("", encoding="utf-8")


def _real_node_path() -> str:
    node_bin = shutil.which("node")
    if node_bin is None:
        raise SystemExit("fixture needs node on PATH")
    return node_bin


def _live_inventory(paths: _Paths, cache_sha: dict) -> dict:
    """The product's own `inventory` under the REAL home, the fixture env, as the live session
    will run it. Cache fresh before, byte-identical after (review cycles 1 and 2)."""
    from ai_kit_gsd_curated_config import cli  # pylint: disable=import-outside-toplevel

    live_env = {**os.environ, **_fixture_env(paths)}
    assert_no_probe(live_env)
    node_bin = _real_node_path()
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = cli.main(
            ["inventory", "--project-dir", str(paths.project), "--host", "claude"],
            which_fn=lambda name, **_kw: node_bin if name == "node" else shutil.which(name),
            env_fn=lambda: live_env,
            run_fn=subprocess.run,
        )
    if code != 0:
        raise SystemExit(f"live inventory failed with exit {code}")
    if _cache_sha(paths) != cache_sha:
        raise SystemExit("seeded cache rebuilt")
    (paths.run / "inventory.json").write_text(buf.getvalue(), encoding="utf-8")
    return json.loads(buf.getvalue())


def _recommend(inv: dict, *flags: str) -> dict:
    from tests.test_curated_config_recommend import (  # pylint: disable=import-outside-toplevel
        run_recommend,
    )

    code, plan, _raw, err = run_recommend(inv, *flags)
    if code != 0 or plan is None:
        raise SystemExit(f"recommend failed: {err.strip()[:200]}")
    return plan


def _self_check_live(paths: _Paths, cache_sha: dict, *, profile: str, rigor: str, require) -> dict:
    """The live inventory, then `recommend` over THAT inventory must yield the scenario's
    facts (`require(plan)` raises SystemExit when one is missing)."""
    inv = _live_inventory(paths, cache_sha)
    plan = _recommend(
        inv,
        "--profile",
        profile,
        "--rigor",
        rigor,
        "--cross-ai-review",
        "y",
        "--cross-ai-exec",
        "y",
    )
    require(plan)
    return inv


def _real_gsd_env(paths: _Paths, home: str) -> dict:
    """The gsd-tools subprocess env (D-08 scope: B and D only): the real HOME, scratch GSD_HOME."""
    return {
        "HOME": home,
        "GSD_HOME": str(paths.gsd_home),
        "PATH": os.environ.get("PATH", ""),
        "RUNTIME_DIR": str(REPO_ROOT),
    }


def _config_path(paths: _Paths) -> pathlib.Path:
    return paths.project / ".planning" / "config.json"


def _hermetic_env(paths: _Paths, home: str) -> dict:
    return {
        "HOME": home,
        "GSD_HOME": str(paths.gsd_home),
        "XDG_CACHE_HOME": str(paths.xdg),
        "PATH": "",
        "RUNTIME_DIR": str(REPO_ROOT),
    }


def _hermetic_inventory(paths: _Paths, host: str) -> dict:
    """C and E: the hermetic tables builder (no real node, no real home)."""
    from tests.test_curated_config_apply import (  # pylint: disable=import-outside-toplevel
        _tables_fake,
        scratch_inventory,
    )
    from tests.test_curated_config_apply_e2e import (  # pylint: disable=import-outside-toplevel
        _seed_home,
    )

    home = paths.run / "hermetic-home"
    home.mkdir(parents=True, exist_ok=True)
    _seed_home(str(home))
    env = _hermetic_env(paths, str(home))
    fake = _tables_fake(str(_config_path(paths)), str(home))
    inv_path = str(paths.run / "inventory.json")
    scratch_inventory(str(paths.project), env, fake, inv_path, host_name=host)
    return _load_json_file(inv_path)


def _write_candidates(paths: _Paths, plan: dict) -> dict:
    out = {}
    for entry in plan.get("entries") or []:
        if entry.get("status") != "needs_choice":
            continue
        values = [_candidate_value(c) for c in entry.get("candidates") or []]
        out[entry["key"]] = [v for v in values if v is not None]
    _dump_json(paths.run / "candidates.json", out)
    return out


def _e_answer_pairs(plan: dict) -> list[tuple[str, str]]:
    """E's turn 2 as commands: the feature goes off, then each other needs_choice takes its
    first candidate."""
    pairs = [("workflow.cross_ai_execution", "false")]
    for entry in plan.get("entries") or []:
        if entry.get("status") != "needs_choice" or entry.get("key") == "workflow.cross_ai_command":
            continue
        cands = entry.get("candidates") or []
        if cands:
            value = _candidate_value(cands[0])
            pairs.append((entry["key"], value if isinstance(value, str) else json.dumps(value)))
    return pairs


def _candidate_value(cand: object) -> object:
    """A candidate's answer value: a dict's `value` (a list for trusted roots, serialized as
    JSON by the caller) or its `model`; a bare value stands for itself."""
    if isinstance(cand, dict):
        return cand.get("value", cand.get("model"))
    return cand


def _self_check_e_answer(paths: _Paths, plan: dict, inv_path: pathlib.Path) -> None:
    """E's answers must reach `needs_choice_keys == []` on a plan copy (review cycle 1)."""
    from ai_kit_gsd_curated_config import (
        apply as apply_mod,  # pylint: disable=import-outside-toplevel
    )
    from ai_kit_gsd_curated_config import cli  # pylint: disable=import-outside-toplevel

    copy = paths.run / "plan-copy.json"
    _dump_json(copy, plan)
    node_bin = _real_node_path()
    for key, value in _e_answer_pairs(plan):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            code = cli.main(
                ["plan-set", key, value, "--plan", str(copy), "--inventory", str(inv_path)],
                which_fn=lambda name, **_kw: node_bin if name == "node" else None,
                env_fn=lambda: {"PATH": ""},
                run_fn=subprocess.run,
            )
        if code != 0:
            raise SystemExit(f"E answer cannot reach apply: plan-set {key} exit {code}")
    if apply_mod.needs_choice_keys(_load_json_file(copy)) != []:
        raise SystemExit("E answer cannot reach apply")


def _build_b(paths: _Paths, home: str) -> dict:
    """B: real `config-new-project` under the poisoned GSD_HOME (D-08 scope)."""
    _gsd_defaults(paths, {"resolve_model_ids": "omit", "runtime": "codex"})
    node_bin = _real_node_path()
    tools = str(REPO_ROOT / GSD_TOOLS_REL)
    proc = subprocess.run(
        [node_bin, tools, "config-new-project", "--cwd", str(paths.project), "--raw"],
        env=_real_gsd_env(paths, home),
        capture_output=True,
        text=True,
        check=False,
        timeout=300,
    )
    if proc.returncode != 0 or not _config_path(paths).is_file():
        raise SystemExit(f"config-new-project failed: exit {proc.returncode}")
    shutil.copyfile(_config_path(paths), paths.run / "config-before.json")
    return {"config_before": "config-before.json"}


def _gsd_defaults(paths: _Paths, defaults: dict) -> None:
    (paths.gsd_home / ".gsd").mkdir(parents=True, exist_ok=True)
    (paths.gsd_home / ".gsd" / "defaults.json").write_text(json.dumps(defaults), encoding="utf-8")


def _build_d(paths: _Paths, home: str) -> dict:
    """D: the v1 writes through the real v1 subcommands (D-08 scope)."""
    from ai_kit_gsd_curated_config import cli  # pylint: disable=import-outside-toplevel

    _gsd_defaults(paths, {"resolve_model_ids": "omit", "model_policy": {"provider": "generic"}})
    node_bin = _real_node_path()
    env = _real_gsd_env(paths, home)
    which_fn = lambda name, **_kw: node_bin if name == "node" else shutil.which(name)
    for argv in (
        ["ensure-project", "--project-dir", str(paths.project)],
        ["apply-profile", "--project-dir", str(paths.project), "--profile", "balanced"],
        ["apply-critical-agents", "--project-dir", str(paths.project)],
    ):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            code = cli.main(
                argv, which_fn=which_fn, env_fn=lambda: dict(env), run_fn=subprocess.run
            )
        if code != 0:
            raise SystemExit(f"v1 {argv[0]} failed with exit {code}")
    shutil.copyfile(_config_path(paths), paths.run / "config-before.json")
    return {"config_before": "config-before.json"}


def _build_c(paths: _Paths) -> dict:
    """C: opencode-host inventory, both routers confirmed, unscored catalog (all tier slots
    needs_choice). Self-check: B's answers yield needs_choice plus a router value."""
    from tests.test_curated_config_golden import (
        load_fixture,  # pylint: disable=import-outside-toplevel
    )

    catalog = _load_json_file(CACHE_SEED / "model-catalog.json")
    reduced = {key: catalog[key] for key in ROUTERS if key in catalog}
    if "_meta" in catalog:
        reduced["_meta"] = catalog["_meta"]
    _write_seed_files(
        paths, confirm_routers=True, catalog=reduced, runtimes=load_fixture("runtimes.json")
    )
    inv = _hermetic_inventory(paths, host="opencode")
    plan = _recommend(
        inv,
        "--profile",
        "adaptive",
        "--rigor",
        "rigorous",
        "--cross-ai-review",
        "y",
        "--cross-ai-exec",
        "y",
    )
    needs = [e for e in plan.get("entries") or [] if e.get("status") == "needs_choice"]
    if not needs:
        raise SystemExit("C self-check: no needs_choice entry")
    if not any(router in json.dumps(plan) for router in ROUTERS):
        raise SystemExit("C self-check: no router value in the plan")
    _write_candidates(paths, plan)
    return {"inventory": "inventory.json"}


def _build_e(paths: _Paths, home: str) -> dict:
    """E: B's build, but the only installed runtime is the host."""
    info = _build_b(paths, home)
    _write_seed_files(
        paths,
        confirm_routers=True,
        catalog=None,
        runtimes=_narrow_to_host(_load_json_file(CACHE_SEED / "runtimes.json")),
    )
    inv = _hermetic_inventory(paths, host="claude")
    plan = _recommend(
        inv,
        "--profile",
        "adaptive",
        "--rigor",
        "rigorous",
        "--cross-ai-review",
        "y",
        "--cross-ai-exec",
        "y",
    )
    cmd = [e for e in plan.get("entries") or [] if e.get("key") == "workflow.cross_ai_command"]
    if not cmd or cmd[0].get("status") != "needs_choice" or cmd[0].get("candidates") != []:
        raise SystemExit("E self-check: workflow.cross_ai_command is not an empty needs_choice")
    _write_candidates(paths, plan)
    _self_check_e_answer(paths, plan, paths.run / "inventory.json")
    return info


def _narrow_to_host(runtimes: dict, host: str = "claude") -> dict:
    clis = {
        name: (row if name == host else {"installed": False})
        for name, row in (runtimes.get("clis") or {}).items()
    }
    return {**runtimes, "clis": clis}


def _b_facts(plan: dict) -> None:
    """B's self-check facts over the live plan (the spec's required entries)."""
    entries = plan.get("entries") or []
    if not any(
        e.get("key") == "review.models.opencode" and e.get("value") == "router-env/my-plan-review"
        for e in entries
    ):
        raise SystemExit("B self-check: review.models.opencode is not my-plan-review")
    if not any(
        e.get("key") == "resolve_model_ids"
        and e.get("op") == "unset"
        and e.get("existing") == "omit"
        for e in entries
    ):
        raise SystemExit("B self-check: resolve_model_ids is not an unset of omit")
    artifacts = plan.get("artifacts") or []
    models = ((artifacts[0].get("config") or {}).get("models") or {}) if artifacts else {}
    if models.get("pi") != "router-env/my-coding":
        raise SystemExit("B self-check: artifacts[0] models.pi is not my-coding")


def _d_facts(plan: dict) -> None:
    """D's facts: the v1 flow's real values (`model_overrides.*`, `models.*`) are unset with
    their non-null `existing` values, so the live plan carries what the old flow set up."""
    unsets = [e for e in plan.get("entries") or [] if e.get("op") == "unset"]
    keyed = {e.get("key", "").split(".")[0] for e in unsets}
    if not {"model_overrides", "models"} <= keyed:
        raise SystemExit("D self-check: v1 model overrides are not unset by the plan")
    if any(e.get("existing") is None for e in unsets):
        raise SystemExit("D self-check: an unset carries no existing value")


def _materialize_v1(paths: _Paths) -> dict:
    """The v1 SKILL.md (pinned entrypoint), the launcher and the fakebin, self-checked."""
    v1_text = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "show", f"{V1_COMMIT}:{V1_RELPATH}"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    launcher = _write_launcher(paths)
    skill_dir = paths.run / "v1-skill" / "ai-kit-gsd-curated-config"
    (skill_dir / "SKILL.md").write_text(_pin_entrypoint(v1_text, str(launcher)), encoding="utf-8")
    _write_fakebin(paths, _load_json_file(paths.runtimes))
    help_proc = subprocess.run(
        [sys.executable, str(launcher), "--help"],
        env=_v1_env(paths, str(paths.run / "selfcheck-home")),
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    if help_proc.returncode != 0:
        raise SystemExit("v1 entrypoint does not answer --help")
    _self_check_v1_detect(paths, launcher)
    return {
        "v1_skill_md": str(skill_dir / "SKILL.md"),
        "v1_entrypoint": str(launcher),
        "v1_entrypoint_pinned": True,
        "fakebin": str(paths.run / "fakebin"),
        "v1_listing_isolated": True,
        "v1_commit": subprocess.run(
            ["git", "-C", str(REPO_ROOT), "rev-parse", "--short", V1_COMMIT],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip(),
    }


def build_fixture(scenario: str, run_dir) -> dict:
    """Builds one scenario under `run_dir` (empty or absent) and returns `fixture.json`'s dict.
    Every self-check runs before return; a failure is a fixture problem (SystemExit)."""
    if scenario not in SCENARIOS:
        raise SystemExit(f"unknown scenario {scenario!r}")
    paths = _layout(run_dir)
    if paths.run.exists() and any(paths.run.iterdir()):
        raise SystemExit("run dir must be empty")
    paths.run.mkdir(parents=True, exist_ok=True)
    _make_scratch_project(paths)
    real_home = os.path.expanduser("~")
    fixture = {
        "scenario": scenario,
        "run_dir": str(paths.run),
        "project": str(paths.project),
        "env": _fixture_env(paths),
        "skill_md": str(SKILL_DIR / "SKILL.md"),
        "digest": skill_digest(SKILL_DIR),
    }
    cache_sha = _seed_caches(paths)
    assert_no_probe({**os.environ, **_fixture_env(paths)})
    if scenario in ("B", "D"):
        fixture.update(
            _build_b(paths, real_home) if scenario == "B" else _build_d(paths, real_home)
        )
        fixture["cache_sha"] = cache_sha
        fixture.update(_materialize_v1(paths))
        check = _b_facts if scenario == "B" else _d_facts
        _self_check_live(
            paths,
            cache_sha,
            profile="adaptive",
            rigor="rigorous" if scenario == "B" else "standard",
            require=check,
        )
        fixture["inventory"] = "inventory.json"
    elif scenario == "C":
        fixture.update(_build_c(paths))
    else:
        fixture.update(_build_e(paths, real_home))
    return fixture


def _cmd_fixture(args: argparse.Namespace) -> int:
    fixture = build_fixture(args.scenario, args.run_dir)
    _dump_json(_abs_path(args.run_dir) / "fixture.json", fixture)
    print(json.dumps(fixture, indent=2, sort_keys=True))
    return 0


# ═══ 6. run: the headless pressure runner (D-12, Run rule 4) ═════════════════════════════

SIGNAL_NAMES = {"term": signal.SIGTERM, "kill": signal.SIGKILL}


class RunSeams(NamedTuple):
    """Injected process seams: the `claude` binary, the spawn, the group kill, the process
    snapshot (`ps -eo pid=,ppid=,pgid=,args=`) and the scratch HOME."""

    claude_bin: str
    popen_fn: Callable = subprocess.Popen
    kill_fn: Callable = os.killpg
    ps_fn: Callable | None = None  # None: `_default_ps` at call time
    home: str = ""


def _default_ps() -> str:
    proc = subprocess.run(
        ["ps", "-eo", "pid=,ppid=,pgid=,args="], capture_output=True, text=True, check=False
    )
    return proc.stdout


def _parse_ps(text: str) -> list[tuple[int, int, int, str]]:
    rows = []
    for line in text.splitlines():
        parts = line.strip().split(None, 3)
        if len(parts) < 4 or not all(p.lstrip("-").isdigit() for p in parts[:3]):
            continue
        rows.append((int(parts[0]), int(parts[1]), int(parts[2]), parts[3]))
    return rows


def _ancestor_chain(rows: list[tuple[int, int, int, str]]) -> set[int]:
    """This process, then each ppid upward through the snapshot until pid 1 or an unknown pid
    (`os.getppid()` is always included, even when absent from the snapshot)."""
    by_pid = {pid: ppid for pid, ppid, _pgid, _args in rows}
    chain = {os.getpid(), os.getppid()}
    current = os.getpid()
    seen = set()
    while current in by_pid and current not in seen and current > 1:
        seen.add(current)
        parent = by_pid[current]
        chain.add(parent)
        current = parent
    return chain


def _signal_group(seams: RunSeams, pgid: int, sig: int) -> None:
    with contextlib.suppress(ProcessLookupError, PermissionError, OSError):
        seams.kill_fn(pgid, sig)


def _reap_strays(run_dir: pathlib.Path, seams: RunSeams, cli_pid: int, reaped: list) -> None:
    """Kills the group of every process whose args name the run dir, except this harness, its
    ancestors and their groups (review cycles 2 and 3). Detached descendants of the CLI (the
    inventory refresh uses `start_new_session=True`) are the target."""
    rows = _parse_ps((seams.ps_fn or _default_ps)())
    spared = _ancestor_chain(rows)
    spared_groups = {os.getpgrp()} | {pgid for pid, _p, pgid, _a in rows if pid in spared}
    needle = str(run_dir)
    for pid, _ppid, pgid, args in rows:
        if needle not in args or pid == cli_pid or pid in spared or pgid in spared_groups:
            continue
        _signal_group(seams, pgid, signal.SIGKILL)
        reaped.append([pid, args[:80].replace(needle, "<run>")])


def _turn_argv(
    seams: RunSeams, turn: int, session: str, model: str, effort: str, prompt: str
) -> list[str]:
    session_flag = ["--session-id", session] if turn == 1 else ["--resume", session]
    return [
        seams.claude_bin,
        "-p",
        *RUN_FLAGS,
        "--model",
        model,
        "--effort",
        effort,
        *session_flag,
        prompt,
    ]


def _cell_env(fixture: dict, home: str) -> dict:
    """`runner_dispatch.child_env` over the fixture env and the scratch HOME; the v1 resolver's
    first candidate reads CLAUDE_PLUGIN_ROOT, so it is dropped (review cycle 2)."""
    from ai_kit_spec.runner_dispatch import child_env  # pylint: disable=import-outside-toplevel

    env = child_env({**fixture["env"], "HOME": home})
    env.pop("CLAUDE_PLUGIN_ROOT", None)
    return env


def _run_one_turn(
    seams: RunSeams,
    fixture: dict,
    run_dir: pathlib.Path,
    cell: str,
    n: int,
    argv: list[str],
    env: dict,
) -> tuple[subprocess.Popen, bool]:
    """One `claude -p` turn in its own session; returns (process, timed_out)."""
    out_path = run_dir / cell / f"turn-{n}.jsonl"
    err_path = run_dir / cell / f"turn-{n}.stderr"
    timed_out = False
    with open(out_path, "w", encoding="utf-8") as out, open(err_path, "w", encoding="utf-8") as err:
        proc = seams.popen_fn(
            argv,
            cwd=fixture["project"],
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=out,
            stderr=err,
            start_new_session=True,
        )
        try:
            proc.wait(timeout=RUN_TIMEOUT)
        except subprocess.TimeoutExpired:
            timed_out = True
            _signal_group(seams, proc.pid, signal.SIGTERM)
            with contextlib.suppress(subprocess.TimeoutExpired):
                proc.wait(timeout=5)
            _signal_group(seams, proc.pid, signal.SIGKILL)
    _signal_group(seams, proc.pid, signal.SIGKILL)
    return proc, timed_out


def events(run_dir, cell: str) -> list[dict]:
    """Every content block of `turn-*.jsonl`, in order. A tool_result carries its tool_use's
    `id` lookup via `tool_use_id`, `is_error` and the FULL text (review cycle 1)."""
    run = _abs_path(run_dir) / cell
    out: list[dict] = []
    for path in sorted(run.glob("turn-*.jsonl"), key=lambda p: int(p.stem.split("-")[1])):
        n = int(path.stem.split("-")[1])
        for index, line in enumerate(path.read_text(encoding="utf-8").splitlines()):
            event = _json_or_none(line)
            if not isinstance(event, dict):
                continue
            out.extend(_blocks_of(event, n, index))
    return out


def _json_or_none(line: str):
    try:
        return json.loads(line)
    except json.JSONDecodeError:
        return None


def _message_of(event: dict) -> dict:
    """The event's `message` object, or an empty dict when it is absent or not an object."""
    message = event.get("message")
    return message if isinstance(message, dict) else {}


def _blocks_of(event: dict, turn: int, index: int) -> list[dict]:
    content = _message_of(event).get("content")
    if not isinstance(content, list):
        return []
    blocks = []
    for block in content:
        if not isinstance(block, dict):
            continue
        blocks.append(_block_record(event.get("type"), block, turn, index))
    return [b for b in blocks if b is not None]


def _block_record(kind: str | None, block: dict, turn: int, index: int) -> dict | None:
    base = {
        "turn": turn,
        "index": index,
        "text": None,
        "command": None,
        "name": None,
        "id": None,
        "tool_use_id": None,
        "is_error": None,
    }
    if kind == "assistant" and block.get("type") == "text":
        return {**base, "kind": "text", "text": block.get("text")}
    if kind == "assistant" and block.get("type") == "tool_use":
        command = (block.get("input") or {}).get("command")
        name = block.get("name")
        return {
            **base,
            "kind": "bash" if name == "Bash" else "tool_use",
            "name": name,
            "command": command,
            "id": block.get("id"),
        }
    if kind == "user" and block.get("type") == "tool_result":
        return {
            **base,
            "kind": "tool_result",
            "text": _result_text(block.get("content")),
            "tool_use_id": block.get("tool_use_id"),
            "is_error": bool(block.get("is_error")),
        }
    return None


def _result_text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(
            b.get("text", "")
            for b in content
            if isinstance(b, dict) and isinstance(b.get("text"), str)
        )
    return ""


def _stream_summary(path: pathlib.Path) -> dict:
    """The turn's init fields, result fields and any Skill tool_use or gating facts."""
    init, result, skill_used = {}, None, False
    for line in path.read_text(encoding="utf-8").splitlines():
        event = _json_or_none(line)
        if not isinstance(event, dict):
            continue
        if event.get("type") == "system" and event.get("subtype") == "init":
            init = {k: event.get(k) for k in _INIT_FIELDS}
        if event.get("type") == "result":
            result = event
        for block in _message_of(event).get("content") or []:
            if (
                isinstance(block, dict)
                and block.get("type") == "tool_use"
                and block.get("name") == "Skill"
            ):
                skill_used = True
    return {"init": init, "result": result, "skill_used": skill_used}


_INIT_FIELDS = (
    "model",
    "tools",
    "skills",
    "slash_commands",
    "mcp_servers",
    "plugins",
    "memory_paths",
    "claude_code_version",
    "permissionMode",
)


def _gating_failures(turn: int, returncode: int, summary: dict) -> list[str]:
    """Turn gating (review cycle 2): a non-zero exit, no result event, or `is_error` true is an
    infrastructure failure that stops the scripted continuation (the cell is never graded)."""
    if returncode != 0:
        return [f"turn {turn}: exit {returncode}"]
    if summary["result"] is None:
        return [f"turn {turn}: no result event"]
    if summary["result"].get("is_error") is True:
        return [f"turn {turn}: result is_error"]
    return []


def _init_harness_failures(init: dict) -> list[str]:
    failures = []
    for field in ("skills", "slash_commands", "mcp_servers"):
        if init.get(field):
            failures.append(f"{field} is not empty")
    tools = init.get("tools")
    if isinstance(tools, list) and sorted(tools) != EXPECTED_TOOLS:
        failures.append("tools differ from the strict set")
    return failures


def _claude_json_projects_failure(home: str, project: str) -> list[str]:
    path = pathlib.Path(home) / ".claude.json"
    if not path.is_file():
        return []
    data = _json_or_none(path.read_text(encoding="utf-8"))
    projects = data.get("projects") if isinstance(data, dict) else None
    if isinstance(projects, dict) and project in projects:
        return [f"~/.claude.json gained a projects key for {project}"]
    return []


def _shadow_failures(cell: str, evs: list[dict], fixture: dict) -> list[str]:
    """An entrypoint outside the cell's own skill copy (red-b: the run dir's v1 copy; green: the
    worktree skill) is a harness failure, not a verdict (T-19-42)."""
    if cell == "red-a":
        return []
    allowed = pathlib.Path(fixture["run_dir"]) / "v1-skill" if cell == "red-b" else SKILL_DIR
    for event in evs:
        if event["kind"] != "bash" or not isinstance(event.get("command"), str):
            continue
        for token in event["command"].split():
            if "ai-kit-gsd-curated-config.py" not in token:
                continue
            resolved = os.path.normpath(token)
            if not resolved.startswith(os.path.normpath(str(allowed))):
                return [f"entrypoint_shadowed: {resolved}"]
    return []


def _cell_digest(fixture: dict, cell: str) -> str:
    if cell == "green":
        return fixture["digest"]
    if cell == "red-b":
        return fixture.get("v1_commit", "-")
    return "-"


def _transcript_dir(project: str) -> str:
    return project.replace("/", "-").replace(".", "-")


def _claude_version(claude_bin: str) -> str:
    """The `claude --version` line, or a marker when the binary cannot run (recorded, never
    fatal: the cell's gating still decides the outcome)."""
    try:
        proc = subprocess.run(
            [claude_bin, "--version"], capture_output=True, text=True, check=False, timeout=60
        )
    except (OSError, subprocess.TimeoutExpired):
        return "unavailable"
    return proc.stdout.strip() or "unavailable"


def _scripted_turns(cell: str, scenario_text: str, fixture: dict) -> list[str]:
    """The prompt (preamble plus body) for turn 1, then the scripted answers in order."""
    body = _prompt_of(scenario_text)
    preamble = PREAMBLES[cell].format(
        PROJECT=fixture["project"],
        SKILL_MD=fixture["skill_md"],
        V1_SKILL_MD=fixture.get("v1_skill_md", ""),
        V1_ENTRYPOINT=fixture.get("v1_entrypoint", ""),
    )
    return [f"{preamble}\n\n{body}", *_answers_of(scenario_text)]


def _prompt_of(text: str) -> str:
    return _fenced_under(text, "## Prompt", first=True)[0]


def _answers_of(text: str) -> list[str]:
    return _fenced_under(text, ANSWER_HEADING, first=False)


def _fenced_under(text: str, heading: str, *, first: bool) -> list[str]:
    """The fenced blocks under `heading`, up to the next `## ` heading (all of them, or only
    the first when `first` is set)."""
    lines = text.splitlines()
    try:
        start = lines.index(heading)
    except ValueError as exc:
        raise ValueError(f"eval file has no {heading!r} section") from exc
    blocks, current, inside = [], [], False
    for line in lines[start + 1 :]:
        if line.startswith("## "):
            break
        if line.strip().startswith("```"):
            if inside:
                blocks.append("\n".join(current))
                current, inside = [], False
            else:
                inside = True
            continue
        if inside:
            current.append(line)
    return blocks[:1] if first else blocks


def run_cell(
    fixture: dict, cell: str, scenario_text: str, seams: RunSeams, *, model: str, effort: str
) -> dict:
    """One cell: the scripted continuation of `claude -p` turns, then the harness checks. Returns
    the `run.json` dict. Exit-code policy is the caller's (`main` exits 1 on any failure)."""
    run_dir = _abs_path(fixture["run_dir"])
    cell_dir = run_dir / cell
    cell_dir.mkdir(parents=True, exist_ok=True)
    home = seams.home or os.path.expanduser("~")
    session = str(uuid.uuid4())
    env = _cell_env(fixture, home)
    turns = _scripted_turns(cell, scenario_text, fixture)
    record = {"turns": [], "reaped": [], "harness_failures": [], "session_id": session}
    for n, prompt in enumerate(turns, start=1):
        argv = _turn_argv(seams, n, session, model, effort, prompt)
        proc, timed_out = _run_one_turn(seams, fixture, run_dir, cell, n, argv, env)
        _reap_strays(run_dir, seams, proc.pid, record["reaped"])
        summary = _stream_summary(cell_dir / f"turn-{n}.jsonl")
        if timed_out:
            record["harness_failures"].append(f"turn {n}: timed out")
        gating = _gating_failures(n, proc.returncode, summary)
        record["harness_failures"].extend(gating)
        result = summary["result"] or {}
        record["turns"].append(
            {
                "n": n,
                "init": summary["init"],
                "total_cost_usd": result.get("total_cost_usd"),
                "is_error": result.get("is_error"),
                "timed_out": timed_out,
                "returncode": proc.returncode,
            }
        )
        if summary["skill_used"]:
            record["harness_failures"].append("Skill tool_use")
        if timed_out or gating:
            break
    return _finish_run(fixture, cell, seams, record, model, effort, home)


def _finish_run(
    fixture: dict, cell: str, seams: RunSeams, record: dict, model: str, effort: str, home: str
) -> dict:
    """The run.json: init of turn 1, cost totals, the transcript-level checks, and the cleanup
    of the scratch project's transcript dir (D-12, jev 19-S1)."""
    run_dir = _abs_path(fixture["run_dir"])
    evs = events(run_dir, cell)
    init = record["turns"][0]["init"] if record["turns"] else {}
    record["harness_failures"].extend(_init_harness_failures(init))
    record["harness_failures"].extend(_claude_json_projects_failure(home, fixture["project"]))
    record["harness_failures"].extend(_shadow_failures(cell, evs, fixture))
    cost = sum(float(t["total_cost_usd"] or 0) for t in record["turns"])
    transcript = _transcript_dir(fixture["project"])
    run_json = {
        "scenario": fixture["scenario"],
        "cell": cell,
        "session_id": record["session_id"],
        "claude_version": _claude_version(seams.claude_bin),
        "model": model,
        "effort": effort,
        "digest": _cell_digest(fixture, cell),
        "init": init,
        "turns": record["turns"],
        "cost_usd_total": round(cost, 6),
        "transcript_dir": transcript,
        "reaped": record["reaped"],
        "harness_failures": record["harness_failures"],
    }
    _dump_json(run_dir / cell / "run.json", run_json)
    _delete_transcript_dir(home, transcript)
    return run_json


def _delete_transcript_dir(home: str, transcript: str) -> None:
    target = pathlib.Path(home) / ".claude" / "projects" / transcript
    with contextlib.suppress(FileNotFoundError):
        shutil.rmtree(target)


def _cmd_run(args: argparse.Namespace) -> int:
    run_dir = _abs_path(args.run_dir)
    fixture = _load_json_file(run_dir / "fixture.json")
    scenario_path = SKILL_DIR / "evals" / EVAL_FILES[args.scenario]
    scenario_text = scenario_path.read_text(encoding="utf-8")
    seams = RunSeams(
        claude_bin=shutil.which("claude") or "claude",
        home=os.path.expanduser("~"),
        ps_fn=_default_ps,
    )
    result = run_cell(
        fixture, args.cell, scenario_text, seams, model=args.model, effort=args.effort
    )
    print(
        json.dumps(
            {"harness_failures": result["harness_failures"], "turns": len(result["turns"])},
            sort_keys=True,
        )
    )
    return 1 if result["harness_failures"] or any(t["timed_out"] for t in result["turns"]) else 0


# ═══ 10. smoke: scripted live procedure, D-13 / D-14 (host-agnostic) ═══════════════════


class SmokeCtx(NamedTuple):
    """The seams and fixed inputs of one smoke run (bundled to keep the limits)."""

    node_bin: str
    tools_path: str
    repo_root: pathlib.Path
    home: str
    host: str
    env: dict
    host_flag: bool = True  # False: inventory detects the host itself (EVAL-03 live detection)


class ValidateCtx(NamedTuple):
    """What `validate_applied` compares a finished apply against."""

    expect_backup: bool
    backups_before: list
    config_before_sha: str | None


_SKILL_KEY_PREFIX = "agent_skills."


def tree_sha256(root: pathlib.Path | str) -> str:
    """sha256 over sorted `relative-path NUL file-sha256` pairs of every regular file."""
    base = _abs(root)
    digest = hashlib.sha256()
    for path in sorted(p for p in base.rglob("*") if p.is_file() and not p.is_symlink()):
        rel = path.relative_to(base).as_posix()
        digest.update(f"{rel}\0{_sha256_file(path)}\n".encode())
    return digest.hexdigest()


def inject_fault(plan_path: pathlib.Path | str, out_path: pathlib.Path | str) -> None:
    """Writes a copy of the plan whose `review.default_reviewers` value is `notarray`.

    Edits the one existing entry in place (duplicate keys are refused) and round-trips JSON;
    the original plan file is never touched.
    """
    plan, error = plan_io.read_json_object(str(plan_path))
    if plan is None:
        raise SystemExit(f"fault plan unreadable: {error}")
    targets = [e for e in plan.get("entries") or [] if e.get("key") == "review.default_reviewers"]
    if len(targets) != 1:
        print("fault target missing", file=sys.stderr)
        raise SystemExit(1)
    targets[0]["op"] = "set"
    targets[0]["value"] = "notarray"
    _write_json(_abs(out_path), plan)


def _write_rank(key: str, op: str) -> tuple:
    """The product's write order (`apply.write_order`), imported lazily."""
    from ai_kit_gsd_curated_config import (
        apply as apply_mod,  # pylint: disable=import-outside-toplevel
    )

    return apply_mod.write_order(key, op)


def _perturbable(plan: dict) -> dict | None:
    """First bool `set` entry that the product writes before `review.default_reviewers`."""
    fault_rank = _write_rank("review.default_reviewers", "set")
    found = [
        e
        for e in plan.get("entries") or []
        if e.get("op") == "set"
        and isinstance(e.get("value"), bool)
        and _write_rank(e.get("key", ""), "set") < fault_rank
    ]
    found.sort(key=lambda e: _write_rank(e["key"], "set"))
    return found[0] if found else None


def perturb_before_fault(plan_path: str, project: str, node_bin: str, env: dict) -> str:
    """Flips one bool key in scratch project (a) so the fault apply really queues a write.

    Unchanged writes are omitted by the product, so without this the faulted apply would
    write nothing and a restore that merely clears the marker would pass (review cycle 2).
    """
    plan = _load_plan_file(plan_path)
    entry = _perturbable(plan)
    if entry is None:
        raise SystemExit("no perturbable key before fault")
    tools = gsd_tools.GsdTools(node_bin, str(_abs(GSD_TOOLS_PATH)))
    ok, _out = gsd_tools.config_set(
        tools,
        project,
        entry["key"],
        not entry["value"],
        run_fn=_scratch_run(env),
    )
    if not ok:
        raise SystemExit(f"perturbation config-set failed for {entry['key']}")
    return entry["key"]


def _scratch_run(env: dict):
    def run(cmd, **kw):
        call_env = kw.pop("env", None) or {}
        return subprocess.run(cmd, env={**env, **call_env}, **kw)

    return run


def _load_plan_file(path: str) -> dict:
    plan, error = plan_io.load_plan(path)
    if plan is None:
        raise SystemExit(f"plan unreadable: {error}")
    return plan


def _plan_set_cli(plan_path: str, inv_path: str, key: str, value: str, force: bool) -> None:
    """One `plan-set` through the product's CLI; a non-zero exit is a step failure."""
    from ai_kit_gsd_curated_config import cli  # pylint: disable=import-outside-toplevel

    argv = ["plan-set", key, value, "--plan", plan_path, "--inventory", inv_path]
    if force:
        argv.append("--force")
    buf, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(err):
        code = cli.main(argv, which_fn=shutil.which, run_fn=subprocess.run)
    if code != 0:
        raise SystemExit(f"plan-set {key} failed (exit {code}): {err.getvalue().strip()[:200]}")


def _choice_raw(candidate) -> str:
    """A candidate in the `plan-set` value form SKILL.md documents: a runtime candidate's
    `model`, the trusted-roots candidate's whole `value` list as JSON, JSON booleans and
    lists, else the plain string."""
    if isinstance(candidate, dict) and "model" in candidate:
        return str(candidate["model"])
    if isinstance(candidate, dict) and "value" in candidate:
        value = candidate["value"]
        return json.dumps(value if isinstance(value, list) else [value])
    if isinstance(candidate, bool):
        return "true" if candidate else "false"
    if isinstance(candidate, (list, dict)):
        return json.dumps(candidate)
    return str(candidate)


def resolve_choices(plan_path, inv_path, plan_set_fn=None, load_fn=None) -> list[str]:
    """Closes every `needs_choice` item of a plan through `plan-set` (D-14 step 3).

    Order matters (review cycle 2): runner models first, then a plan reload so the product's
    `_sync_artifact_command` closes the derived `workflow.cross_ai_command` entry itself, then
    the remaining model keys. A placeholder is forced only on a model key with no candidate,
    never into the execution hook (an unclosed hook is `runner choice unresolved`).
    Returns the forced keys.
    """
    plan_set_fn = plan_set_fn or _plan_set_cli
    load_fn = load_fn or _load_plan_file
    plan = load_fn(plan_path)
    artifacts = plan.get("artifacts") or [{}]
    choices = (artifacts[0] or {}).get("choices") or {}
    for runner in sorted(choices):
        candidates = (choices[runner] or {}).get("candidates") or []
        if candidates:
            plan_set_fn(
                plan_path,
                inv_path,
                f"script:cross-ai.model.{runner}",
                _choice_raw(candidates[0]),
                False,
            )
    plan = load_fn(plan_path)
    forced: list[str] = []
    for entry in plan.get("entries") or []:
        if entry.get("status") != "needs_choice":
            continue
        key, candidates = entry.get("key", ""), entry.get("candidates") or []
        if candidates:
            plan_set_fn(plan_path, inv_path, key, _choice_raw(candidates[0]), False)
        elif key == "workflow.cross_ai_command":
            raise SystemExit("runner choice unresolved")
        else:
            plan_set_fn(plan_path, inv_path, key, "smoke-placeholder", True)
            forced.append(key)
    return forced


def _skill_ref_ok(planned_name: str, got: object) -> bool:
    """The documented serialized form, checked independently of the product's converter."""
    if not isinstance(got, str):
        return False
    name = re.escape(planned_name)
    return re.fullmatch(rf"skills/{name}|global:(?:[^:]+:)?{name}", got) is not None


def _set_matches(key: str, planned, got) -> bool:
    if key.startswith(_SKILL_KEY_PREFIX) and isinstance(planned, list):
        if not isinstance(got, list) or len(got) != len(planned):
            return False
        return all(_skill_ref_ok(name, ref) for name, ref in zip(planned, got, strict=True))
    return plan_io.same_value(planned, got)


def _backup_check(ctx: ValidateCtx, config_path: str) -> None:
    now = config_backup.list_backups(config_path)
    if ctx.expect_backup:
        if len(now) != len(ctx.backups_before) + 1:
            raise SystemExit("backup count did not grow by one")
        if _sha256_file(now[0][0]) != ctx.config_before_sha:
            raise SystemExit("newest backup is not the pre-apply bytes")
    elif now or not os.path.isfile(config_path):
        raise SystemExit("unexpected backup for a config that did not exist")


def _leftover_check(project: str) -> None:
    for _root, _dirs, files in os.walk(os.path.join(project, ".planning")):
        for name in files:
            if (
                name.endswith(config_backup.MARKER_SUFFIX)
                or name.endswith(config_backup.SNAPSHOT_SUFFIX)
                or ".bak-tmp-" in name
            ):
                raise SystemExit(f"leftover apply file: {name}")


def validate_applied(project: str, plan: dict, ctx: ValidateCtx, env: dict, node_bin: str) -> None:
    """Byte-level facts after a real apply (SPEC R5): the config parses, each planned set key
    reads back, `resolve-model` answers per live agent, the backup expectation holds, and no
    marker, snapshot or temp file remains. Raises SystemExit naming the failed fact."""
    tools_path = str(_abs(GSD_TOOLS_PATH))
    tools = gsd_tools.GsdTools(node_bin, tools_path)
    config_path = os.path.join(project, ".planning", "config.json")
    try:
        with open(config_path, encoding="utf-8") as handle:
            json.load(handle)
    except (OSError, ValueError) as exc:
        raise SystemExit(f"config does not parse: {exc}") from exc
    run = _scratch_run(env)
    for entry in plan.get("entries") or []:
        if entry.get("op") != "set":
            continue
        got = gsd_tools.config_get(tools, project, entry["key"], run_fn=run)
        if not _set_matches(entry["key"], entry["value"], got.value):
            raise SystemExit(f"config-get {entry['key']} does not read back the planned value")
    for agent in sorted(_agents_of(node_bin, tools_path)):
        got = _resolve_model(_seams(node_bin, tools_path, "", "claude"), agent, project, env)
        if not got.get("model") or not got.get("tier"):
            raise SystemExit(f"resolve-model {agent} gave no model and tier")
    _backup_check(ctx, config_path)
    _leftover_check(project)


def _agents_of(node_bin: str, tools_path: str) -> list[str]:
    return list(live_tables(node_bin, os.path.dirname(os.path.dirname(tools_path)))["profiles"])


def _step(name: str, fn) -> dict:
    """Runs one step; a failure is recorded, never raised, so the snapshot always runs."""
    try:
        detail = fn()
    except SystemExit as stop:
        return {"name": name, "ok": False, "detail": str(stop.code or "")}
    except Exception as exc:  # a step never aborts the run; the failure is recorded
        return {"name": name, "ok": False, "detail": f"{type(exc).__name__}: {exc}"[:200]}
    return {"name": name, "ok": True, "detail": detail or ""}


def _scratch_project(work: str, label: str, with_planning: bool) -> str:
    """A git repo with the gsd-core symlink; `.planning/config.json` copied when asked."""
    project = os.path.join(work, label)
    os.makedirs(project)
    subprocess.run(["git", "init", "-q", project], check=True)
    link = os.path.join(project, ".claude", "gsd-core")
    os.makedirs(os.path.dirname(link), exist_ok=True)
    os.symlink(os.path.join(REPO_ROOT, ".claude", "gsd-core"), link)
    if with_planning:
        os.makedirs(os.path.join(project, ".planning"))
        shutil.copyfile(
            REPO_ROOT / ".planning" / "config.json",
            os.path.join(project, ".planning", "config.json"),
        )
    return project


def _cache_guard(ctx: SmokeCtx, cache_sha: dict) -> None:
    """Byte identity of the three seeded cache files after an inventory (review cycle 2)."""
    if _cache_sha_of(ctx.env) != cache_sha:
        raise SystemExit("seeded cache rebuilt")


def _cache_sha_of(env: dict) -> dict:
    """The three cache files under the smoke's scratch `XDG_CACHE_HOME`, by sha256."""
    cache = pathlib.Path(env["XDG_CACHE_HOME"]) / "ai-kit" / "spec"
    names = ("runtimes.json", "model-catalog.json", f"model-catalog.json{SIDECAR_SUFFIX}")
    return {name: _sha256_file(cache / name) for name in names}


def _inventory(ctx: SmokeCtx, project: str, out: str, cache_sha: dict) -> dict:
    """The product's `inventory` through `cli.main` on the seeded scratch cache."""
    from ai_kit_gsd_curated_config import cli  # pylint: disable=import-outside-toplevel

    assert_no_probe(ctx.env)
    argv = ["inventory", "--project-dir", project]
    if ctx.host and ctx.host_flag:
        argv += ["--host", ctx.host]
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = cli.main(
            argv,
            which_fn=lambda name, **_kw: ctx.node_bin if name == "node" else shutil.which(name),
            env_fn=lambda: dict(ctx.env),
            run_fn=subprocess.run,
        )
    if code != 0:
        raise SystemExit(f"inventory failed with exit {code}")
    _cache_guard(ctx, cache_sha)
    _write_text(out, buf.getvalue())
    inv = json.loads(buf.getvalue())
    if not ctx.host_flag and inv.get("host") != ctx.host:
        raise SystemExit(f"inventory detected host {inv.get('host')}, expected {ctx.host}")
    return inv


def _write_text(path: str, text: str) -> None:
    pathlib.Path(path).write_text(text, encoding="utf-8")


def _recommend_to(inv_path: str, plan_path: str) -> dict:
    """`recommend` with the smoke's fixed answers (D-14: the same answers in every project)."""
    from tests.test_curated_config_recommend import (  # pylint: disable=import-outside-toplevel
        run_recommend,
    )

    code, plan, _raw, err = run_recommend(
        _load_json_file(inv_path),
        "--profile",
        "adaptive",
        "--rigor",
        "standard",
        "--cross-ai-review",
        "y",
        "--cross-ai-exec",
        "y",
    )
    if code != 0 or plan is None:
        raise SystemExit(f"recommend failed: {err.strip()[:200]}")
    _write_json(_abs(plan_path), plan)
    return plan


def _dry_run_unchanged(ctx: SmokeCtx, project: str, plan_path: str, inv_path: str) -> str:
    """`apply --dry-run` writes nothing: the project's `.planning/` tree hash is identical."""
    from ai_kit_gsd_curated_config import cli  # pylint: disable=import-outside-toplevel

    before = tree_sha256(os.path.join(project, ".planning"))
    with contextlib.redirect_stdout(io.StringIO()):
        code = cli.main(
            [
                "apply",
                "--dry-run",
                "--plan",
                plan_path,
                "--inventory",
                inv_path,
                "--project-dir",
                project,
            ],
            which_fn=lambda name, **_kw: ctx.node_bin if name == "node" else shutil.which(name),
            env_fn=lambda: dict(ctx.env),
            run_fn=subprocess.run,
        )
    if code != 0:
        raise SystemExit(f"dry run exited {code}")
    if tree_sha256(os.path.join(project, ".planning")) != before:
        raise SystemExit("dry run changed .planning/")
    return "dry run wrote nothing"


def _real_apply_or_fail(plan_path: str, inv_path: str, project: str, env: dict, node_bin: str):
    """One real apply on a scratch project. The product calls `which_fn("gsd_run", path=...)`
    whenever PATH is set, so the smoke's `which_fn` must accept keywords (the e2e helper's
    one-argument lambda would crash here)."""
    refuse_repo_apply(project)
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = cli_main_apply(
            plan_path, inv_path, project, _SmokeEnv(node_bin, env), subprocess.run
        )
    if code != 0:
        raise SystemExit(f"apply exited {code}: {_text(err.getvalue())[-200:]}")
    return json.loads(out.getvalue()) if out.getvalue().strip() else {}


class _SmokeEnv(NamedTuple):
    """The two inputs `cli_main_apply` reads from a smoke context (the apply's own seams)."""

    node_bin: str
    env: dict


def _backups_now(project: str) -> list:
    return config_backup.list_backups(os.path.join(project, ".planning", "config.json"))


def _sha_or_none(path: str) -> str | None:
    return _sha256_file(path) if os.path.isfile(path) else None


def _smoke_ai_kit(ctx: SmokeCtx, work: str, cache_sha: dict) -> dict:
    """D-14 step 2: inventory, recommend and a dry run on this repo; never a real apply.

    No `refuse_repo_apply` here: this step targets the repo root by design, and the dry run
    is guarded by its own unchanged-tree check (a guard on the root would always refuse).
    """
    inv_path = os.path.join(work, "inventory.json")
    plan_path = os.path.join(work, "plan.json")

    def run() -> str:
        inv = _inventory(ctx, str(ctx.repo_root), inv_path, cache_sha)
        _recommend_to(inv_path, plan_path)
        resolve_choices(plan_path, inv_path)
        dry = _dry_run_unchanged(ctx, str(ctx.repo_root), plan_path, inv_path)
        return f"{dry}; host {inv.get('host')} ({inv.get('host_source')})"

    return _step("ai-kit inventory, recommend, dry run", run)


def _smoke_project_a(ctx: SmokeCtx, work: str, cache_sha: dict) -> list[dict]:
    """D-14 steps 3 and 4 on a scratch copy of this repo's `.planning/config.json`."""
    project = _scratch_project(work, "project-a", with_planning=True)
    inv_path = os.path.join(work, "inv-a.json")
    plan_path = os.path.join(work, "plan-a.json")
    state: dict = {}

    def inventory_and_plan() -> str:
        _inventory(ctx, project, inv_path, cache_sha)
        _recommend_to(inv_path, plan_path)
        state["forced"] = resolve_choices(plan_path, inv_path)
        return f"forced placeholders: {state['forced'] or 'none'}"

    def first_apply() -> str:
        config = os.path.join(project, ".planning", "config.json")
        state["before_sha"] = _sha_or_none(config)
        state["backups"] = _backups_now(project)
        plan = _load_plan_file(plan_path)
        _dry_run_unchanged(ctx, project, plan_path, inv_path)
        _real_apply_or_fail(plan_path, inv_path, project, ctx.env, ctx.node_bin)
        validate_applied(
            project,
            plan,
            ValidateCtx(True, state["backups"], state["before_sha"]),
            ctx.env,
            ctx.node_bin,
        )
        return "apply and validation passed"

    def second_apply() -> str:
        config = os.path.join(project, ".planning", "config.json")
        sha = _sha256_file(config)
        backups = len(_backups_now(project))
        _real_apply_or_fail(plan_path, inv_path, project, ctx.env, ctx.node_bin)
        if _sha256_file(config) != sha:
            raise SystemExit("second apply changed the config bytes")
        grown = len(_backups_now(project)) - backups
        if grown != 1 or len(_backups_now(project)) > KEEP_LIMIT:
            raise SystemExit(f"second apply backup growth {grown}, expected +1 within limit")
        return "second apply: writes 0, bytes identical, backups +1"

    def fault() -> str:
        return _fault_apply(ctx, work, project, plan_path, inv_path)

    return [
        _step("project (a) inventory, recommend, choices", inventory_and_plan),
        _step("project (a) dry run, apply, validation", first_apply),
        _step("project (a) second apply", second_apply),
        _step("project (a) forced failure restores", fault),
    ]


KEEP_LIMIT = config_backup.KEEP


def _fault_apply(ctx: SmokeCtx, work: str, project: str, plan_path: str, inv_path: str) -> str:
    """D-14 step 4: queue one real write ahead of the rejected key, then fail, then check."""
    fault_plan = os.path.join(work, "plan-fault.json")
    inject_fault(plan_path, fault_plan)
    config = os.path.join(project, ".planning", "config.json")
    perturbed = perturb_before_fault(plan_path, project, ctx.node_bin, ctx.env)
    pre = _sha256_file(config)
    logged: list[list[str]] = []
    wrapper = _logging_run(ctx, logged)
    code, parsed, _out, _err = _real_apply_fault(fault_plan, inv_path, project, ctx, wrapper)
    keys = _config_set_keys(logged)
    if code != 1 or (parsed or {}).get("failed_key") != "review.default_reviewers":
        raise SystemExit("fault apply did not fail on review.default_reviewers")
    if perturbed not in keys or keys.index(perturbed) > keys.index("review.default_reviewers"):
        raise SystemExit(f"{perturbed} was not written before the failing key")
    if (parsed or {}).get("restore_error") is not None:
        raise SystemExit("restore reported an error")
    if _sha256_file(config) != pre:
        raise SystemExit("config bytes were not restored to the perturbed pre-apply state")
    if os.path.exists(config + config_backup.MARKER_SUFFIX):
        raise SystemExit("marker left after the forced failure")
    return f"forced failure: exit 1, {perturbed} written then undone, restored"


def _logging_run(ctx: SmokeCtx, logged: list) -> Callable:
    base = _scratch_run(ctx.env)

    def run(cmd, **kw):
        logged.append([str(part) for part in cmd])
        return base(cmd, **kw)

    return run


def _real_apply_fault(fault_plan, inv_path, project, ctx: SmokeCtx, run_fn):
    refuse_repo_apply(project)
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = cli_main_apply(fault_plan, inv_path, project, ctx, run_fn)
    parsed = json.loads(out.getvalue()) if out.getvalue().strip() else None
    return code, parsed, out.getvalue(), err.getvalue()


def cli_main_apply(plan_path, inv_path, project, ctx, run_fn) -> int:
    """`apply` through `cli.main`. `ctx` carries `node_bin` and `env` (a `SmokeCtx` or a
    `_SmokeEnv`); `which_fn` takes keywords because the product passes `path=`."""
    from ai_kit_gsd_curated_config import cli  # pylint: disable=import-outside-toplevel

    return cli.main(
        ["apply", "--plan", plan_path, "--inventory", inv_path, "--project-dir", project],
        which_fn=lambda name, **_kw: ctx.node_bin if name == "node" else shutil.which(name),
        env_fn=lambda: dict(ctx.env),
        run_fn=run_fn,
    )


def _smoke_project_b(ctx: SmokeCtx, work: str, cache_sha: dict) -> dict:
    """D-14 step 5: empty project on the real global defaults; key paths only, never values."""
    project = _scratch_project(work, "project-b", with_planning=False)
    inv_path = os.path.join(work, "inv-b.json")
    plan_path = os.path.join(work, "plan-b.json")
    report: dict = {}

    def run() -> str:
        _inventory(ctx, project, inv_path, cache_sha)
        _recommend_to(inv_path, plan_path)
        resolve_choices(plan_path, inv_path)
        _dry_run_unchanged(ctx, project, plan_path, inv_path)
        report.update(_real_apply_or_fail(plan_path, inv_path, project, ctx.env, ctx.node_bin))
        validate_applied(
            project, _load_plan_file(plan_path), ValidateCtx(False, [], None), ctx.env, ctx.node_bin
        )
        keys = sorted(report.get("reconciled") or [])
        diff = [(row.get("key"), row.get("kind")) for row in report.get("diff") or []]
        report["key_paths"] = {"reconciled": keys, "diff": diff}
        return f"reconciled {len(keys)} key paths, {len(diff)} diff rows"

    result = _step("project (b) empty project, apply, validation", run)
    result["key_paths"] = report.get("key_paths", {})
    return result


def _run_matrix_step(ctx: SmokeCtx) -> dict:
    """D-14 step 6: the matrix on the selected host; a non-Claude refusal is the failure."""
    holder: dict = {}

    def run() -> str:
        holder["matrix"] = run_matrix(ctx.node_bin, ctx.tools_path, ctx.home, host=ctx.host)
        return f"matrix ran: {holder['matrix']['checks']} checks"

    result = _step("matrix on the selected host", run)
    result["matrix"] = holder.get("matrix")
    return result


def run_smoke(ctx: SmokeCtx, work: str, seed_fn=None, assert_fn=None) -> dict:
    """D-14 steps 1-7. Every step records its own outcome; the snapshot always runs."""
    seed_fn = seed_fn or _seed_for_smoke
    assert_fn = assert_fn or (lambda env: assert_no_probe(env))
    cache_sha = seed_fn(work, ctx)
    assert_fn(ctx.env)
    before = snapshot(ctx.repo_root, ctx.home)
    steps = [_smoke_ai_kit(ctx, work, cache_sha)]
    steps.extend(_smoke_project_a(ctx, work, cache_sha))
    b_result = _smoke_project_b(ctx, work, cache_sha)
    steps.append(b_result)
    matrix = _run_matrix_step(ctx)
    steps.append(matrix)
    after = snapshot(ctx.repo_root, ctx.home)
    strict, host_managed = snapshot_diff(before, after)
    steps.append(
        {
            "name": "protected set unchanged",
            "ok": not strict,
            "detail": "unchanged" if not strict else f"changed {', '.join(strict)}",
        }
    )
    return {
        "steps": steps,
        "strict_changed": strict,
        "host_managed_changed": host_managed,
        "matrix": matrix.get("matrix"),
        "key_paths": b_result.get("key_paths", {}),
        "exit": 0 if all(s["ok"] for s in steps) and not strict else 1,
    }


def _seed_for_smoke(work: str, ctx: SmokeCtx) -> dict:
    """The seeded scratch cache under `<work>/xdg` (D-11 step 2; never the real cache)."""
    paths = _layout(work)
    if str(paths.xdg) != ctx.env.get("XDG_CACHE_HOME"):
        raise SystemExit("smoke env does not point at the seeded scratch cache")
    return _seed_caches(paths)


def _smoke_placeholders(text: str, result: dict) -> str:
    """Replaces every machine path in the evidence with its label (D-13, D-14 step 5)."""
    for raw, label in (
        (result.get("scratch_b"), "<scratch-b>"),
        (result.get("scratch_a"), "<scratch-a>"),
        (result.get("home"), HOME_LABEL),
        (result.get("repo_root"), WORKTREE_LABEL),
    ):
        if raw:
            text = text.replace(str(raw), label)
    return text


def render_smoke_evidence(result: dict) -> str:
    """Markdown evidence: step outcomes, gsd-core, matrix, protected set, project (b) keys."""
    lines = ["# Smoke evidence", "", "## Steps"]
    for number, step in enumerate(result["steps"], start=1):
        verdict = "pass" if step["ok"] else "fail"
        lines.append(f"- step {number} {step['name']}: {verdict} — {step['detail']}")
    matrix = result.get("matrix") or {}
    lines += [
        "",
        "## gsd-core",
        f"- version: {(matrix.get('gsd_core') or {}).get('version')}",
        f"- path: {GSD_CORE_LABEL}",
    ]
    lines += ["", "## Matrix"]
    if matrix:
        lines.append(f"- checks: {matrix.get('checks')}; agents: {matrix.get('agents')}")
        for name, control in sorted((matrix.get("controls") or {}).items()):
            lines.append(f"- {name}: {control.get('verdict', 'recorded')}")
        info = matrix.get("informational") or {}
        lines.append(
            f"- informational runtime row: model {info.get('model')}, tier {info.get('tier')}"
        )
    else:
        lines.append("- not run")
    lines += ["", "## Protected set"]
    changed = list(result.get("strict_changed") or [])
    lines.append("- unchanged" if not changed else "- changed: " + ", ".join(changed))
    host = list(result.get("host_managed_changed") or [])
    lines.append("- host-managed changed: " + (", ".join(host) if host else "none"))
    keys = (result.get("key_paths") or {}).get("reconciled") or []
    lines += ["", "## Project (b) key paths"]
    lines += [f"- {key}" for key in keys] or ["- none"]
    lines += [
        "",
        "## Caches",
        "- seeded scratch cache; no runtime enumeration; byte-identical after every inventory",
    ]
    return _smoke_placeholders("\n".join(lines) + "\n", result)


def _cmd_smoke(args: argparse.Namespace) -> int:
    node_bin = shutil.which("node")
    reason = gsd_run_reason(node_bin, GSD_TOOLS_PATH)
    if node_bin is None or reason:
        print(reason or "no node executable")
        return 3
    from ai_kit_gsd_curated_config import (
        host as host_mod,  # pylint: disable=import-outside-toplevel
    )

    host, host_source = host_mod.detect_host(dict(os.environ), args.host)
    if host is None:
        print(f"host detection failed: {host_source}; re-run with --host claude")
        return 2
    work = tempfile.mkdtemp(prefix="smoke-")
    home = str(_abs(args.home or pathlib.Path.home()))
    env = {
        **os.environ,
        "RUNTIME_DIR": str(REPO_ROOT),
        "GSD_RUNTIME": host,
        "XDG_CACHE_HOME": os.path.join(work, "xdg"),
    }
    ctx = SmokeCtx(node_bin, GSD_TOOLS_PATH, REPO_ROOT, home, host, env, args.host is not None)
    try:
        result = run_smoke(ctx, work)
        result.update(
            {
                "scratch_a": os.path.join(work, "project-a"),
                "scratch_b": os.path.join(work, "project-b"),
                "home": home,
                "repo_root": str(REPO_ROOT),
            }
        )
        _write_text(str(_abs(args.evidence_out)), render_smoke_evidence(result))
        print(f"smoke evidence written to {label_path(args.evidence_out)}")
        return result["exit"]
    finally:
        shutil.rmtree(work, ignore_errors=True)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="gsd_curated_eval",
        description="Dev-only Phase 19 evaluation helper for ai-kit-gsd-curated-config.",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    snap = sub.add_parser("snapshot", help="hash the protected set (reads only, writes nothing)")
    snap.add_argument("--out", help="write the snapshot JSON to this file")
    snap.add_argument("--check", help="compare the protected set against this snapshot file")
    snap.add_argument("--home", help="home directory to protect (default: this process's)")
    snap.set_defaults(func=_cmd_snapshot)

    dig = sub.add_parser("digest", help="the SKILL.md plus references/ digest of a skill")
    dig.add_argument("--check", nargs="*", metavar="FILE", help="evidence files to check")
    dig.add_argument("--skill-dir", help="skill directory (default: this repo's)")
    dig.add_argument("--section", action="append", default=[], help="require a live row here")
    dig.add_argument("--column", action="append", default=[], help="digest cell of this column")
    dig.set_defaults(func=_cmd_digest)

    grd = sub.add_parser("grade", help="score one scenario's checks for one cell")
    grd.add_argument("scenario", choices=SCENARIOS)
    grd.add_argument("--run-dir", required=True)
    grd.add_argument("--cell", required=True, choices=CELLS)
    grd.add_argument("--trimmed-out", help="write the trimmed transcript here")
    grd.add_argument("--record-out", help="write the compact grading record JSON here")
    grd.set_defaults(func=_cmd_grade)

    scan = sub.add_parser("secret-scan", help="fail on secret-shaped values (T-19-10)")
    scan.add_argument("paths", nargs="+")
    scan.set_defaults(func=_cmd_secret_scan)

    cel = sub.add_parser("cells", help="extract one evidence column")
    cel.add_argument("file")
    cel.add_argument("--column", required=True)
    cel.add_argument("--strict", action="store_true")
    cel.set_defaults(func=_cmd_cells)

    mat = sub.add_parser("matrix", help="APP-05: resolve-model against the plan-derived oracle")
    mat.add_argument("--json", action="store_true", help="print the structured result as JSON")
    mat.add_argument("--host", default="claude", help="runtime host (claude only for now)")
    mat.add_argument("--tools", default=GSD_TOOLS_PATH, help="path to gsd-tools.cjs")
    mat.add_argument("--home", help="real HOME for the gsd-tools subprocesses (D-08)")
    mat.set_defaults(func=_cmd_matrix)

    fix = sub.add_parser("fixture", help="build one scenario's scratch project and caches")
    fix.add_argument("scenario", choices=SCENARIOS)
    fix.add_argument("--run-dir", required=True, help="empty or absent scratch directory")
    fix.set_defaults(func=_cmd_fixture)

    smoke = sub.add_parser("smoke", help="the D-14 live smoke (writes scratch projects only)")
    smoke.add_argument("--host", help="runtime the smoke runs on (default: detected)")
    smoke.add_argument("--home", help="home directory to protect (default: this process's)")
    smoke.add_argument("--evidence-out", required=True, help="write the evidence here")
    smoke.set_defaults(func=_cmd_smoke)

    run = sub.add_parser("run", help="one cell of one scenario through claude -p")
    run.add_argument("scenario", choices=SCENARIOS)
    run.add_argument("--cell", required=True, choices=CELLS)
    run.add_argument("--run-dir", required=True, help="the directory `fixture` built")
    run.add_argument("--model", default="sonnet")
    run.add_argument("--effort", default="medium")
    run.set_defaults(func=_cmd_run)
    return parser


def main(argv=None) -> int:
    """Entry point: the subcommand's exit code (3 when the real-node matrix cannot run)."""
    args = _build_parser().parse_args(argv)
    try:
        return args.func(args)
    except _refusal as stop:
        print(stop.reason, file=sys.stderr)
        return stop.exit_code


if __name__ == "__main__":
    sys.exit(main())
