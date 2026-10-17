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
import hashlib
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Callable
from typing import NamedTuple

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
for _skill in (REPO_ROOT / "skills" / "ai-kit-gsd-curated-config",
               REPO_ROOT / "skills" / "ai-kit-spec-review"):
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
    host_managed = {
        label: _file_sha(path) for label, path in _host_managed_files(home_dir).items()
    }
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
            path.relative_to(root).as_posix().encode() + b"\0"
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
            capture_output=True, text=True, check=False, timeout=30,
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
        if isinstance(entry, dict) and entry.get("op") == "set"
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
    return _MatrixCtx(node_bin, tools_path, home, host,
                      os.path.dirname(os.path.dirname(str(_abs(tools_path)))))


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
        created, _warn = plan_io.read_json_object(
            os.path.join(project, ".planning", "config.json")
        )
        if (created or {}).get("resolve_model_ids") != "omit":
            raise _refusal(1, "poison not copied")

    return seed


def _bundle_for(
    ctx: _MatrixCtx, combo: tuple[str, str], start: str, defaults: dict | None
) -> dict:
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
            capture_output=True, text=True, check=False, timeout=60, env=dict(env),
        )
    except (OSError, subprocess.SubprocessError):
        return {"model": "", "tier": "", "profile": "", "effort": ""}
    parsed = _json_object(_text(getattr(result, "stdout", ""))) or {}
    return {key: parsed.get(key, "") for key in ("model", "tier", "profile", "effort")}


def _resolve_all(ctx: _MatrixCtx, agents: list[str], project: str, env: dict) -> dict:
    return {agent: _resolve_model(ctx, agent, project, env) for agent in agents}


def _mismatches(
    agents: list[str], plan: dict, tables: dict, got: dict,
    *, inheritance_promised: bool = False,
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


def _row_for(ctx: _MatrixCtx, combo: tuple[str, str], start: str, agents: list[str],
             tables: dict) -> dict:
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
        "profile": profile, "rigor": rigor, "path": start, "combo": f"{rigor}/{profile}",
        "mismatches": mismatches, "checks": len(agents),
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
        "expected_failures": len(expected), "observed": len(mismatches),
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
        "mismatches": [row[0] for row in mismatches], "ok": not mismatches,
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
        "combo": "standard/adaptive", "path": "P2", "agent": "gsd-planner",
        "model": str(got["model"]), "tier": str(got["tier"]),
        "runtime_in_config": True, "informational": True, "why": WHY_INFORMATIONAL,
    }


def run_matrix(node_bin: str, tools_path: str, home: str, host: str = "claude",
               ctx: _MatrixCtx | None = None) -> dict:
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
    rows = [
        _row_for(ctx, combo, start, agents, tables) for combo in COMBOS for start in PATHS
    ]
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
    result = run_matrix(node_bin, args.tools, str(_abs(args.home or pathlib.Path.home())),
                        args.host)
    if args.json:
        print(json.dumps(result, sort_keys=True))
    else:
        print(_render_matrix(result))
        verdict = "matrix FAILED" if _matrix_failed(result) else (
            f"matrix ok ({result['checks']} checks)"
        )
        print(verdict)
    if _matrix_failed(result):
        return 1
    return 0


def _matrix_failed(result: dict) -> bool:
    controls = result["controls"]
    return bool(any(row["mismatches"] for row in result["rows"])
                or not controls["control_1"]["ok"]
                or not controls["control_2"]["ok"])


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
