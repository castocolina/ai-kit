# pylint: disable=line-too-long
"""35 D-03 / Amend-10: Arena leaderboard rows from the official CC-BY-4.0 dataset through the datasets-server JSON API: one /filter query per category, 3 tries, /rows fallback, page ceiling. Returns (data, ok) like model_sources and never raises; network only through fetch_fn."""  # noqa: E501

import time
import urllib.error
import urllib.parse
from collections.abc import Callable
from typing import NamedTuple

from ai_kit_spec.model_sources import _http_get_json

ARENA_BASE = "https://datasets-server.huggingface.co"
ARENA_DATASET = "lmarena-ai/leaderboard-dataset"
ARENA_CONFIG = "text"
ARENA_SPLIT = "latest"
ARENA_CATEGORIES = (
    "overall",
    "coding",
    "math",
    "hard_prompts",
    "instruction_following",
    "creative_writing",
    "multi_turn",
)
PAGE_LENGTH = 100
PAGE_CEILING = 115
FETCH_DEADLINE_S = 240
RETRIES = 3
RETRY_PAUSE_S = 1.0
_ROW_FIELDS = ("rating", "rating_lower", "rating_upper", "vote_count")


class _Fetch(NamedTuple):
    fetch_fn: Callable[..., object]
    sleep_fn: Callable[[float], None]
    progress: Callable[[str], None] | None
    length: int
    clock_fn: Callable[[], float]
    start: float


def filter_url(category: str, offset: int, length: int = PAGE_LENGTH) -> str:
    """Build a datasets-server category-filter URL."""
    query = {
        "dataset": ARENA_DATASET,
        "config": ARENA_CONFIG,
        "split": ARENA_SPLIT,
        "where": '"category"=\'' + category + "'",
        "offset": offset,
        "length": length,
    }
    return f"{ARENA_BASE}/filter?" + urllib.parse.urlencode(query)


def rows_url(offset: int, length: int = PAGE_LENGTH) -> str:
    """Build a datasets-server rows URL."""
    query = {
        "dataset": ARENA_DATASET,
        "config": ARENA_CONFIG,
        "split": ARENA_SPLIT,
        "offset": offset,
        "length": length,
    }
    return f"{ARENA_BASE}/rows?" + urllib.parse.urlencode(query)


def _get(url, fetch_fn, sleep_fn):
    for attempt in range(RETRIES):
        try:
            answer = fetch_fn(url, {})
        except (urllib.error.URLError, TimeoutError, ValueError, OSError):
            answer = None
        if isinstance(answer, dict):
            return answer
        if attempt + 1 < RETRIES:
            sleep_fn(RETRY_PAUSE_S)
    return None


def _keep(row: dict, wanted) -> tuple | None:
    if not isinstance(row, dict):
        return None
    category = row.get("category")
    model_name = row.get("model_name")
    rating = row.get("rating")
    if not isinstance(category, str) or category not in wanted:
        return None
    if not isinstance(model_name, str) or not model_name.strip():
        return None
    if isinstance(rating, bool) or not isinstance(rating, (int, float)):
        return None
    record = {field: row[field] for field in _ROW_FIELDS if field in row}
    return category, model_name, record


def _page_rows(page) -> list | None:
    if not isinstance(page, dict):
        return None
    rows = page.get("rows")
    total = page.get("num_rows_total")
    if (
        not isinstance(rows, list)
        or isinstance(total, bool)
        or not isinstance(total, int)
        or total < 0
    ):
        return None
    if any(not isinstance(item, dict) or not isinstance(item.get("row"), dict) for item in rows):
        return None
    return [item["row"] for item in rows]


def _read_pages(url_for, fetch: _Fetch, wanted, store) -> str:
    offset = 0
    pages = 0
    while True:
        if fetch.clock_fn() - fetch.start > FETCH_DEADLINE_S:
            return "deadline"
        pages += 1
        if pages > PAGE_CEILING:
            return "ceiling"
        if fetch.progress is not None:
            fetch.progress(f"page {pages}")
        page = _get(url_for(offset), fetch.fetch_fn, fetch.sleep_fn)
        if page is None:
            return "failed"
        rows = _page_rows(page)
        if rows is None:
            return "failed"
        for row in rows:
            kept = _keep(row, wanted)
            if kept is not None:
                category, model_name, record = kept
                store[category][model_name] = record
        total = page["num_rows_total"]
        if offset + fetch.length >= total or (not rows and offset >= total):
            return "ok"
        if not rows:
            return "failed"
        offset += fetch.length


def fetch_arena(
    fetch_fn=None,
    progress=None,
    sleep_fn=time.sleep,
    page_length=PAGE_LENGTH,
    clock_fn=time.monotonic,
) -> tuple:
    """Fetch category rows, falling back to one complete rows snapshot on filter failure."""
    fetch_fn = fetch_fn or _http_get_json
    started = clock_fn()
    store = {category: {} for category in ARENA_CATEGORIES}
    result = "ok"
    for category in ARENA_CATEGORIES:
        page_fetch = _Fetch(
            fetch_fn,
            sleep_fn,
            (lambda line, name=category: progress(f"arena: {name} {line}"))
            if progress is not None
            else None,
            page_length,
            clock_fn,
            started,
        )
        outcome = _read_pages(
            lambda off, name=category: filter_url(name, off, page_length),
            page_fetch,
            {category},
            store,
        )
        if outcome == "failed":
            result = "failed"
            break
        if outcome != "ok":
            result = outcome
            break
    if result == "failed":
        fallback = {category: {} for category in ARENA_CATEGORIES}
        page_fetch = _Fetch(
            fetch_fn,
            sleep_fn,
            (lambda line: progress(f"arena: rows {line}")) if progress is not None else None,
            page_length,
            clock_fn,
            started,
        )
        outcome = _read_pages(
            lambda off: rows_url(off, page_length),
            page_fetch,
            set(ARENA_CATEGORIES),
            fallback,
        )
        if outcome == "ok":
            store = fallback
            result = "ok"
    return {"config": ARENA_CONFIG, "split": ARENA_SPLIT, "categories": store}, result == "ok"
