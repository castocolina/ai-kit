#!/usr/bin/env python3
"""S1 spike: measure the local Laya's non-truncating state bound and latency (D-03).

Runs against the real 21.1 client and the precompact core, both loaded by path
from the repo this script lives in. Every child env pins HOME and the XDG roots
under the repo's tmp/p212/ scratch tree, so no real user config, state or
consent record is ever touched. If the local Laya is not usable, prints
{"measured": false, ...} and exits 0 - measurement must never block.

Stdlib only. Run from the repo root:
    python3 .planning/.../spike/s1_laya.py > tmp/p212/s1.json
"""

import importlib.util
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
CLIENT_PATH = REPO / "skills" / "jev-fast-decision" / "scripts" / "jev_review.py"
CORE_PATH = REPO / "tools" / "hooks" / "precompact_core.py"
SCRATCH = REPO / "tmp" / "p212" / "s1"
HEAD = "0" * 40
PROBE_RUNS = 10
CALL_RUNS = 30
CALL_CHUNK_CHARS = 1000
BISECT_LOW = 100
BISECT_HIGH = 8000


def load_module(name, path):
    """A module loaded by path (neither is importable by name)."""
    spec = importlib.util.spec_from_file_location(name, str(path))
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


jr = load_module("jev_review_s1", CLIENT_PATH)
core = load_module("precompact_core_s1", CORE_PATH)


def scratch_env():
    """A parent env whose every base lives under the scratch tree; no inherited
    JEV_*/GSD_PATH_JEV* value, key or consent ever reaches a child."""
    env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin")}
    for key in ("HOME", "XDG_STATE_HOME", "XDG_CONFIG_HOME", "XDG_CACHE_HOME",
                "XDG_RUNTIME_DIR"):
        env[key] = str(SCRATCH / key.lower())
    return env


def laya_url():
    """The laya endpoint this run answers to: the override, else the default."""
    raw = os.environ.get("AI_KIT_LAYA_URL", "").strip()
    base = raw if raw else jr.LAYA_DEFAULT_URL
    return jr._systemone_url(base)  # noqa: SLF001 - the spike reads the client's own rule


def loopback(url):
    host = urllib.parse.urlsplit(url).hostname or ""
    if host.lower() == "localhost":
        return True
    import ipaddress
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def synth_code():
    """Python-like lines: brackets, quotes and symbols."""
    lines = []
    for index in range(400):
        lines.append(f'def handler_{index}(request, ctx={{"retry": {index}}}) -> "Result":')
        lines.append(f'    rows = [r for r in ctx["rows"] if r.size >= {index} * 2]')
        lines.append(f'    return render("tpl/{index}.j2", rows=rows, cache=True)')
    return "\n".join(lines)


def synth_prose():
    sentences = [
        "The parser walks the token stream and folds each operator into the tree.",
        "When a retry budget is exhausted the client gives up and reports the cause.",
        "A reviewer only needs the outline of an old exchange to continue the work.",
        "The cache key mixes the tenant id with the normalized query parameters.",
    ]
    out = []
    while sum(len(s) for s in out) < 12000:
        for sentence in sentences:
            out.append(sentence)
    return " ".join(out)


def synth_non_english():
    spanish = ("El analizador recorre el flujo de tokens y dobla cada operador en el árbol. "
               "Cuando el presupuesto de reintentos se agota, el cliente lo informa con la "
               "causa exacta y cierra la conexión sin ningún retraso adicional. ")
    japanese = ("パーサーはトークン列をたどり、各演算子を木に折りたたみます。"
                "再試行の予算が尽きたとき、クライアントは原因を報告して接続を閉じます。")
    text = ""
    while len(text) < 12000:
        text += spanish + japanese
    return text


def post_screen(url, text):
    """POST one item through the client's own request_body; (truncated, usage)."""
    payload = core.build_request(HEAD, "c0000", text)
    body, _specs = jr.request_body(payload, "jev-1")
    data = json.dumps(body).encode("utf-8")
    request = urllib.request.Request(url, data=data,
                                     headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=30) as stream:
        answer = json.loads(stream.read().decode("utf-8"))
    usage = answer.get("usage") or {}
    truncated = bool(usage.get("truncated")) or \
        float(usage.get("state_tokens_dropped") or 0) > 0
    return truncated, usage


def state_chars_at(text, length):
    """The state size in the same units fits() and the client's guard count: the
    request_state_chars of the payload itself, without the questions envelope."""
    return core.request_state_chars(core.build_request(HEAD, "c0000", text[:length]))


def bisect_bound(url, text, usage_keys):
    """The largest prefix length in [LOW, HIGH] whose Laya answer is not truncated."""
    low_truncated, low_usage = post_screen(url, text[:BISECT_LOW])
    usage_keys.update(low_usage)
    if low_truncated:
        return BISECT_LOW, state_chars_at(text, BISECT_LOW), True
    high_truncated, high_usage = post_screen(url, text[:BISECT_HIGH])
    usage_keys.update(high_usage)
    if not high_truncated:
        return BISECT_HIGH, state_chars_at(text, BISECT_HIGH), False
    lo, hi = BISECT_LOW, BISECT_HIGH
    while hi - lo > 1:
        mid = (lo + hi) // 2
        truncated, usage = post_screen(url, text[:mid])
        usage_keys.update(usage)
        if truncated:
            hi = mid
        else:
            lo = mid
    return lo, state_chars_at(text, lo), True


def percentile(samples, fraction):
    ordered = sorted(samples)
    return ordered[min(len(ordered) - 1, int(round(fraction * (len(ordered) - 1))))]


def main():
    SCRATCH.mkdir(parents=True, exist_ok=True)
    env = scratch_env()
    client = core.find_client(env)
    if client is None:
        print(json.dumps({"measured": False, "reason": "repo client not found"}))
        return 0
    config_home = str(SCRATCH / "no-config")  # never created: no consent record applies
    deadline = time.monotonic() + 60.0
    report = core.probe_backend(client, env, deadline, config_home)
    backend = core.pick_local_backend(report) if report else None
    if backend is None:
        print(json.dumps({"measured": False,
                          "reason": "no usable local backend",
                          "probe": report}))
        return 0
    url = laya_url()
    if not loopback(url):
        print(f"refusing non-loopback laya endpoint: {url}", file=sys.stderr)
        return 2

    usage_keys: set[str] = set()
    truncation = {}
    for name, text in (("code", synth_code()), ("prose", synth_prose()),
                       ("non_english", synth_non_english())):
        length, chars, truncated = bisect_bound(url, text, usage_keys)
        truncation[name] = {"prefix_chars": length, "state_chars": chars,
                            "truncation_reached": truncated}

    probe_times, probe_reports = [], []
    for _ in range(PROBE_RUNS):
        started = time.perf_counter()
        result = core.probe_backend(client, env, time.monotonic() + 10.0, config_home)
        probe_times.append(time.perf_counter() - started)
        probe_reports.append(bool(result and core.pick_local_backend(result)))

    call_env = core.client_env(env, backend, core.PER_CALL_CAP_SECONDS, config_home)
    prose_chunk = "plain english sentence about retries and caches. " * 16
    prose_chunk = prose_chunk[:CALL_CHUNK_CHARS]
    call_times, call_labels = [], []
    for _ in range(CALL_RUNS):
        started = time.perf_counter()
        label = core.classify_chunk(client, call_env, "c0000", prose_chunk, HEAD)
        call_times.append(time.perf_counter() - started)
        call_labels.append(label)

    with urllib.request.urlopen(
            urllib.parse.urlunsplit(urllib.parse.urlsplit(url)[:2] + ("/health", "", "")),
            timeout=10) as stream:
        health = stream.read().decode("utf-8", errors="replace")

    print(json.dumps({
        "measured": True,
        "backend": backend,
        "endpoint": url,
        "truncation": truncation,
        "usage_keys_seen": sorted(usage_keys),
        "latency": {
            "probe": {"p50": percentile(probe_times, 0.5), "max": max(probe_times),
                      "runs": PROBE_RUNS, "usable": sum(probe_reports)},
            "call": {"p50": percentile(call_times, 0.5),
                     "p95": percentile(call_times, 0.95), "max": max(call_times),
                     "runs": CALL_RUNS,
                     "labeled": sum(1 for label in call_labels if label in core.LABELS)},
        },
        "health_body": health,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
