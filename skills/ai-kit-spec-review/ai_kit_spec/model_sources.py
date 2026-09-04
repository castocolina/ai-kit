"""HTTP fetchers for the two external model-data sources (design spec 2026-09-02, Section 3).
Both return (data, ok) -- ok=False on any failure (network down, bad status, malformed JSON,
a mid-pagination drop), never raise. `ok` is what lets the caller (`build_model_catalog`, Task
7) tell "this source genuinely has nothing to say" from "this source is unreachable right
now, keep whatever was cached" -- collapsing both into a bare empty return would silently wipe
a previously-enriched catalog entry on every transient network blip. Real network access lives
ONLY behind the injectable `fetch_fn` (this repo's existing which_fn/run_fn dependency-
injection convention), so tests never touch the network."""
import json
import urllib.error
import urllib.request

MODELS_DEV_URL = "https://models.dev/api.json"
ARTIFICIAL_ANALYSIS_URL = "https://artificialanalysis.ai/api/v2/language/models/free"

_TIMEOUT_SECONDS = 15
# models.dev's endpoint returns HTTP 403 to urllib's default "Python-urllib/3.x" User-Agent
# (confirmed live against the real endpoint) but 200 to a real browser-/tool-like UA -- without
# this, the always-on, no-key-needed primary data source never matches anything in production.
_USER_AGENT = "ai-kit-spec-config (+https://models.dev)"


def _http_get_json(url: str, headers: dict) -> dict:
    merged_headers = {"User-Agent": _USER_AGENT, **headers}
    req = urllib.request.Request(url, headers=merged_headers)
    with urllib.request.urlopen(req, timeout=_TIMEOUT_SECONDS) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_models_dev(fetch_fn=None) -> tuple:
    """Free, unauthenticated, single call -- the whole catalog. (dict, ok). ok=False on any
    failure -- caller must then leave models.dev-sourced fields on any existing catalog entry
    untouched rather than treat "no data this run" as "no match" (spec Section 8)."""
    fetch_fn = fetch_fn or _http_get_json
    try:
        return fetch_fn(MODELS_DEV_URL, {}), True
    except (urllib.error.URLError, TimeoutError, ValueError, OSError):
        return {}, False


def fetch_artificial_analysis(api_key: str | None, fetch_fn=None) -> tuple:
    """([], True) immediately when api_key is falsy -- never calls out with no key, and this is
    NOT a failure (ok=True): a deliberately-unconfigured source has nothing cached to protect
    either. Paginates (200/page, confirmed live shape) until pagination.has_more is false; ANY
    failure mid-pagination returns (whatever was collected, False) -- ok=False even with
    partial data, because a truncated page set is not a trustworthy "this model has no AA
    match" signal for the pages never reached."""
    if not api_key:
        return [], True
    fetch_fn = fetch_fn or _http_get_json
    collected = []
    page = 1
    while True:
        try:
            resp = fetch_fn(f"{ARTIFICIAL_ANALYSIS_URL}?page={page}", {"x-api-key": api_key})
        except (urllib.error.URLError, TimeoutError, ValueError, OSError):
            return collected, False
        collected.extend(resp.get("data", []))
        if not resp.get("pagination", {}).get("has_more"):
            break
        page += 1
    return collected, True
