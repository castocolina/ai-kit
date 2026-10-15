"""Catalog cache refresh (R3 fresh/stale/none) and scored inventory candidates (D-12..D-15).

Writes only through ai-kit-spec.py into ai-kit's own cache; scoring lives here for REC-01 purity.
Candidate field rules (D-04, D-12..D-15) are centralized in ``build_candidates``.
"""
from __future__ import annotations

import contextlib
import json
import os
import signal
import subprocess
import sys
from typing import Any, NamedTuple

from . import gsd_catalog, model_detect

_THIS_SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SUBPROCESS_TIMEOUT = 120
_TERM_GRACE_S = 10
_DETECT_WARN = "detect-runtimes failed; using the cached runtimes snapshot"
_DETECT_NO_CACHE_WARN = "detect-runtimes failed; no cached runtimes snapshot"
_STALE_WARN = "catalog refresh failed; using the stale cache"
_AA_WARN = "Artificial Analysis refresh failed; scores from cache"
_AA_UNSCORED_WARN = "Artificial Analysis unavailable (no key or fetch failed); catalog unscored"
_MODELS_DEV_WARN = "models.dev refresh failed; prices and capabilities from cache"
_PROBE_WARN = "opencode 2.x image probe failed; image_input unverified for opencode models"

# Inferred from model ids or the catalog provider — never reported by a CLI or the catalog.
CANDIDATE_HEURISTIC_FIELDS = ("family", "fast_twin_of", "vendor")

_SCORE_AXIS_NAMES = ("intelligence_index", "coding_index", "agentic_index")
_ROUTER_PURPOSES = frozenset({"review", "execute"})


class CatalogState(NamedTuple):
    state: str
    scored: bool
    warnings: tuple[str, ...]
    runtimes: dict
    entries: dict
    weights: dict


class _JoinCtx(NamedTuple):
    join_index: dict
    entries: dict
    purpose_by_key: dict
    vendor_mod: object


class _RuntimeCtx(NamedTuple):
    runtime: str
    host_cli: str
    family_map: dict
    model_set: set
    mode_map: dict


class _RefreshPaths(NamedTuple):
    spec_path: str
    runtimes_path: str
    catalog_path: str
    project_dir: str


class _RefreshJob(NamedTuple):
    stack: tuple
    spec_path: str
    project_dir: str
    env: dict
    refresh: bool
    run_fn: object


class _CacheRead(NamedTuple):
    cache: Any
    model_catalog: Any
    paths: _RefreshPaths


def refresh_catalog(project_dir, env, refresh, run_fn):
    """Returns `(CatalogState, None)` or `(None, error_message)`."""
    spec_path = model_detect.resolve_ai_kit_spec_path(_THIS_SKILL_DIR, env)
    if spec_path is None:
        return None, gsd_catalog.SIBLING_MISSING
    stack = _load_spec_stack()
    if stack is None:
        return None, gsd_catalog.SIBLING_MISSING
    job = _RefreshJob(stack, spec_path, project_dir, env, refresh, run_fn)
    return _refresh_with_stack(job), None


def _refresh_with_stack(job: _RefreshJob) -> CatalogState:
    detection, model_catalog, cache, ranker = job.stack
    paths = _RefreshPaths(
        job.spec_path,
        detection.cache_runtimes_path(job.env),
        model_catalog.cache_catalog_path(job.env),
        job.project_dir,
    )
    warnings, fetch_result = _run_refresh(paths, job.refresh, job.env, job.run_fn)
    read = _CacheRead(cache, model_catalog, paths)
    return _catalog_state_from_cache(read, ranker.load_ranking_weights(), warnings, fetch_result)


def _catalog_state_from_cache(read: _CacheRead, weights, warnings, fetch_result) -> CatalogState:
    runtimes, entries = _read_cache(
        read.cache, read.model_catalog, read.paths.runtimes_path, read.paths.catalog_path
    )
    state, state_warnings = _catalog_state(fetch_result, entries)
    if not runtimes:
        warnings = [_DETECT_NO_CACHE_WARN if w == _DETECT_WARN else w for w in warnings]
    if _opencode_probe_failed(runtimes):
        state_warnings.append(_PROBE_WARN)
    merged = sorted(set(warnings) | set(state_warnings))
    return CatalogState(
        state,
        _catalog_is_scored(entries),
        tuple(merged),
        runtimes,
        entries,
        weights,
    )


def _opencode_probe_failed(runtimes) -> bool:
    clis = runtimes.get("clis") if isinstance(runtimes, dict) else None
    opencode = clis.get("opencode") if isinstance(clis, dict) else None
    return isinstance(opencode, dict) and opencode.get("image_input_probe") == "failed"


def _load_spec_stack():
    detection = gsd_catalog.load_ai_kit_spec_module("detection")
    model_catalog = gsd_catalog.load_ai_kit_spec_module("model_catalog")
    cache = gsd_catalog.load_ai_kit_spec_module("cache")
    ranker = gsd_catalog.load_ai_kit_spec_module("model_ranker")
    # vendor is only used by build_candidates, but an older sibling without it must fail
    # here, not yield a "fresh" catalog with zero candidates (B-WR-08).
    vendor = gsd_catalog.load_ai_kit_spec_module("vendor")
    if None in (detection, model_catalog, cache, ranker, vendor):
        return None
    return detection, model_catalog, cache, ranker


def _run_refresh(paths: _RefreshPaths, refresh, env, run_fn):
    warnings: list[str] = []
    detect_argv = _detect_argv(paths.spec_path, paths.runtimes_path, refresh)
    if not _run_subprocess(run_fn, detect_argv, env):
        warnings.append(_DETECT_WARN)
    fetch_argv = _fetch_argv(
        paths.spec_path,
        paths.runtimes_path,
        paths.catalog_path,
        paths.project_dir,
        refresh,
    )
    fetch_result = _run_fetch_json(run_fn, fetch_argv, env)
    return warnings, fetch_result


def _read_cache(cache, model_catalog, runtimes_path, catalog_path):
    runtimes = cache.cache_read_json(runtimes_path) or {}
    raw_catalog = cache.cache_read_json(catalog_path) or {}
    entries, _meta = model_catalog.split_catalog_meta(raw_catalog)
    return runtimes, entries


def _detect_argv(spec_path: str, runtimes_path: str, refresh: bool) -> list:
    base = [sys.executable, spec_path, "detect-runtimes"]
    if refresh:
        return [*base, "--save", runtimes_path]
    return [*base, "--if-stale", runtimes_path]


def _fetch_argv(spec_path, runtimes_path, catalog_path, project_dir, refresh):
    argv = [
        sys.executable,
        spec_path,
        "fetch-model-catalog",
        "--runtimes-json",
        runtimes_path,
        "--catalog-path",
        catalog_path,
        "--cwd",
        project_dir,
    ]
    if not refresh:
        argv.append("--if-stale")
    return argv


def _signal_group(proc, sig) -> None:
    with contextlib.suppress(OSError):
        killpg = getattr(os, "killpg", None)
        if killpg is not None:
            killpg(proc.pid, sig)
        else:
            proc.kill()


def _run_graceful(argv, *, timeout, env, **_kw) -> subprocess.CompletedProcess:
    """`subprocess.run` for the refresh calls, except a timeout SIGTERMs the child's own
    process group first: detect-runtimes' opencode probe unwinds on SIGTERM and stops its
    private server, which a bare SIGKILL of the child would orphan (B-WR-05)."""
    with subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                          env=env, start_new_session=True) as proc:
        try:
            out, err = proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            _signal_group(proc, signal.SIGTERM)
            try:
                proc.communicate(timeout=_TERM_GRACE_S)
            except subprocess.TimeoutExpired:
                _signal_group(proc, getattr(signal, "SIGKILL", signal.SIGTERM))
                proc.communicate()
            raise
    return subprocess.CompletedProcess(argv, proc.returncode, out, err)


def _run(run_fn, argv, env):
    """One refresh subprocess; `None` on spawn error or timeout. Production's
    `subprocess.run` is swapped for the SIGTERM-first runner; tests inject fakes."""
    runner = _run_graceful if run_fn is subprocess.run else run_fn
    try:
        return runner(
            argv,
            capture_output=True,
            text=True,
            check=False,
            timeout=_SUBPROCESS_TIMEOUT,
            env=env,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None


def _run_subprocess(run_fn, argv, env) -> bool:
    result = _run(run_fn, argv, env)
    return result is not None and result.returncode == 0


def _run_fetch_json(run_fn, argv, env) -> dict | None:
    result = _run(run_fn, argv, env)
    if result is None or result.returncode != 0:
        return None
    try:
        parsed = json.loads(result.stdout)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _catalog_state(fetch_result: dict | None, entries: dict) -> tuple[str, list[str]]:
    if not entries:
        return "none", []
    if fetch_result is None:
        return "stale", [_STALE_WARN]
    skipped = bool(fetch_result.get("fetch_skipped"))
    models_ok = bool(fetch_result.get("models_dev_ok"))
    aa_ok = bool(fetch_result.get("artificial_analysis_ok"))
    if skipped or models_ok or aa_ok:
        warns = []
        if not skipped and models_ok and not aa_ok:
            warns.append(_AA_WARN if _catalog_is_scored(entries) else _AA_UNSCORED_WARN)
        if not skipped and not models_ok:
            warns.append(_MODELS_DEV_WARN)
        return "fresh", warns
    return "stale", [_STALE_WARN]


def _catalog_is_scored(entries: dict) -> bool:
    return any(_score_axes(entry) > 0 for entry in entries.values())


def build_candidates(runtimes, entries, host_cli, weights) -> list[dict]:
    """One candidate per installed runtime model id, joined to catalog entries when present.
    Raises ImportError when the ai-kit-spec-review sibling modules are missing."""
    ranker = gsd_catalog.load_ai_kit_spec_module("model_ranker")
    detection = gsd_catalog.load_ai_kit_spec_module("detection")
    vendor_mod = gsd_catalog.load_ai_kit_spec_module("vendor")
    if ranker is None or detection is None or vendor_mod is None:
        raise ImportError(gsd_catalog.SIBLING_MISSING)
    join_index = _build_join_index(entries)
    join = _JoinCtx(
        join_index,
        entries,
        _purpose_scores_by_key(entries, join_index, weights, ranker),
        vendor_mod,
    )
    out: list[dict] = []
    clis = (runtimes or {}).get("clis") or {}
    for runtime in sorted(clis):
        out.extend(_runtime_candidates(clis[runtime], runtime, host_cli, detection, join))
    return sorted(out, key=lambda c: (c["runtime"], c["model"]))


def _runtime_candidates(cli_entry, runtime, host_cli, detection, join: _JoinCtx) -> list[dict]:
    if not isinstance(cli_entry, dict) or not cli_entry.get("installed"):
        return []
    models = cli_entry.get("models")
    if not isinstance(models, list):
        return []
    str_models = [m for m in models if isinstance(m, str)]
    raw_modes = cli_entry.get("reasoning_modes")
    mode_map = raw_modes if isinstance(raw_modes, dict) else {}
    ctx = _RuntimeCtx(
        runtime,
        host_cli,
        _family_lookup(detection.group_models_by_family(str_models), str_models),
        set(str_models),
        mode_map,
    )
    seen: set[str] = set()
    out: list[dict] = []
    for model in str_models:
        if model in seen:
            continue
        seen.add(model)
        out.append(_one_candidate(join, ctx, model))
    return out


def _build_join_index(entries: dict) -> dict[tuple[str, str], str]:
    index: dict[tuple[str, str], str] = {}
    for key in sorted(entries):
        entry = entries[key]
        if not isinstance(entry, dict):
            continue
        for cli, rt in (entry.get("runtimes") or {}).items():
            if not isinstance(rt, dict):
                continue
            model_id = rt.get("model_id")
            if isinstance(model_id, str) and (cli, model_id) not in index:
                index[(cli, model_id)] = key
    return index


def _family_lookup(groups: dict, models: list) -> dict[str, str]:
    lookup: dict[str, str] = {}
    for family, ids in groups.items():
        for mid in ids:
            lookup[mid] = family
    for mid in models:
        lookup.setdefault(mid, mid)
    return lookup


def _purpose_scores_by_key(entries, join_index, weights, ranker) -> dict[str, dict]:
    pool = _scoring_pool(entries, join_index)
    if not pool:
        return {}
    by_key: dict[str, dict] = {}
    for purpose in ranker.CANONICAL_PURPOSES:
        for row in ranker.score_candidates(pool, purpose, weights):
            by_key.setdefault(row["key"], {})[purpose] = row["score_exact"]
    return by_key


def _scoring_pool(entries, join_index) -> list[dict]:
    seen: set[str] = set()
    pool: list[dict] = []
    for key in sorted(set(join_index.values())):
        if key in seen:
            continue
        entry = entries.get(key)
        if not isinstance(entry, dict) or _score_axes(entry) <= 0:
            continue
        seen.add(key)
        pool.append({**entry, "key": key})
    return pool


def _one_candidate(join: _JoinCtx, ctx: _RuntimeCtx, model: str) -> dict:
    catalog_key = join.join_index.get((ctx.runtime, model))
    entry = join.entries.get(catalog_key) if catalog_key else None
    axes = _score_axes(entry) if entry else 0
    is_router = bool(entry and entry.get("is_router"))
    declared = entry.get("name_declared_purpose") if entry else None
    confirmed = entry and "is_router" in (entry.get("heuristic_confirmed") or [])
    router_ok = is_router and confirmed and declared in _ROUTER_PURPOSES
    reasoning = ctx.mode_map.get(model)
    if not isinstance(reasoning, list):
        reasoning = entry.get("reasoning_modes") if entry else None
    if not isinstance(reasoning, list):
        reasoning = []
    purpose = join.purpose_by_key.get(catalog_key, {}) if axes > 0 and catalog_key else {}
    vendor = None
    if entry and not is_router:
        vendor = _candidate_vendor(model, entry, join.vendor_mod)
    image_src = entry.get("image_input_source") if entry else None
    return {
        "runtime": ctx.runtime,
        "model": model,
        "is_host": ctx.runtime == ctx.host_cli,
        "catalog_key": catalog_key,
        "provider": entry.get("provider") if entry else None,
        "vendor": vendor,
        "family": ctx.family_map.get(model, model),
        "fast_twin_of": _fast_twin_of(model, ctx.model_set),
        "is_router": is_router,
        "router_confirmed": router_ok,
        "name_declared_purpose": declared,
        "price": _entry_price(entry) if entry else None,
        "score_axes": axes,
        "scores": _entry_scores(entry) if entry else {},
        "image_input": _entry_image_input(entry) if entry else None,
        "image_input_source": image_src if isinstance(image_src, str) else None,
        "reasoning_modes": reasoning,
        "purpose_scores": dict(purpose) if purpose else {},
    }


def _score_axes(entry: dict | None) -> int:
    if not entry:
        return 0
    scores = entry.get("scores") or {}
    return sum(
        1 for name in _SCORE_AXIS_NAMES if isinstance(scores.get(name), (int, float))
    )


def _entry_scores(entry: dict) -> dict:
    scores = entry.get("scores") or {}
    return {
        name: scores[name]
        for name in _SCORE_AXIS_NAMES
        if isinstance(scores.get(name), (int, float))
    }


def _entry_price(entry: dict):
    pricing = entry.get("pricing") or {}
    val = pricing.get("input_per_1m")
    if isinstance(val, (int, float)):
        return val
    return None


def _entry_image_input(entry: dict):
    val = entry.get("image_input")
    if isinstance(val, bool):
        return val
    return None


def _fast_twin_of(model: str, model_set: set[str]) -> str | None:
    if not model.endswith("-fast"):
        return None
    base = model[:-5]
    return base if base in model_set else None


def _candidate_vendor(model: str, entry: dict, vendor_mod) -> str | None:
    if entry.get("is_router"):
        return None
    for candidate_id in (model, model.rsplit("/", 1)[-1]):
        vendor = vendor_mod.infer_vendor_from_model(candidate_id)
        if vendor:
            return vendor
    provider = entry.get("provider")
    if isinstance(provider, str) and provider in vendor_mod.KNOWN_VENDORS:
        return provider
    return None
