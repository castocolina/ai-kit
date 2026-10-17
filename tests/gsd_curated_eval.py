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

from ai_kit_gsd_curated_config import config_backup, plan_io
from ai_kit_spec import gsd_tools

from tests.test_curated_config_apply_e2e import (
    GSD_CORE_PREFIXES,
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


def check_digests(paths: list[str], digest: str) -> list[str]:
    """Why these evidence files do not bind `digest`; empty when every one of them does.

    Each file needs at least one live row, and every live row's token must equal `digest`.
    Plan 03 adds the section/column refinement for its scenario-table schema.
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
    problems = check_digests(args.check, digest)
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
    dig.set_defaults(func=_cmd_digest)

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
