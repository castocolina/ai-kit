"""Cursor payload adapter; depends on Cursor quota and host-neutral render modules only."""
# pyright: strict

import os
import time
from typing import TYPE_CHECKING, Any, NamedTuple, cast

import common_config
from common_probe import probe_terminal_size
from common_render import Context
from cursor_quota import QuotaResult, probe_read_quota

if TYPE_CHECKING:
    from common_render import Theme
    from common_types import Config


class CursorData(NamedTuple):
    quota: QuotaResult


class PayloadFields(NamedTuple):
    model_name: str
    model_id: str
    work_dir: str
    context_pct: int | None
    context_max: int | None
    transcript_path: str = ""
    model_max: bool = False


# ═══ 6. CORE — render machinery and host payload ═══════════════════════════
def core_payload_fields(raw: dict[str, Any]) -> PayloadFields:
    """Coerce payload display values defensively before constructing Context."""
    model = raw.get("model")
    model = cast(dict[str, Any], model) if isinstance(model, dict) else {}
    window = raw.get("context_window")
    window = cast(dict[str, Any], window) if isinstance(window, dict) else {}
    workspace = raw.get("workspace")
    workspace = cast(dict[str, Any], workspace) if isinstance(workspace, dict) else {}
    name = model.get("display_name")
    name = name if isinstance(name, str) else ""
    summary = model.get("param_summary")
    if isinstance(summary, str) and summary.strip():
        # Live Cursor display names already end with the context/effort (`... 272K High`).
        squash = "".join(name.split()).casefold()
        if not squash.endswith("".join(summary.split()).casefold()):
            name += f" · {summary.strip()}" if name else summary.strip()
    model_id = model.get("id")
    model_id = model_id if isinstance(model_id, str) and model_id else "unknown"
    directory = workspace.get("current_dir") or raw.get("cwd") or "."
    work_dir = os.path.abspath(directory if isinstance(directory, str) else ".")
    percentage = window.get("used_percentage")
    context_pct = None
    if isinstance(percentage, (int, float)) and not isinstance(percentage, bool):
        context_pct = int(percentage)
    maximum = window.get("context_window_size")
    context_max = maximum if isinstance(maximum, int) and not isinstance(maximum, bool) else None
    return PayloadFields(
        name,
        model_id,
        work_dir,
        context_pct,
        context_max,
        raw["transcript_path"] if isinstance(raw.get("transcript_path"), str) else "",
        model.get("max_mode") is True,
    )


def core_cursor_data(ctx: Context) -> CursorData:
    """Return Cursor-only data attached to a neutral render context."""
    return cast(CursorData, ctx.host)


def core_cursor_context(
    raw: dict[str, Any], config: "Config", theme: "Theme", env: Any, t_start: int | None
) -> Context:
    """Map untrusted Cursor JSON defensively and read quota through the cache-only API."""
    fields = core_payload_fields(raw)
    cols_value = raw.get("render_width_chars")
    if isinstance(cols_value, int) and not isinstance(cols_value, bool) and cols_value > 0:
        cols, lines, assumed = cols_value, 0, False
    else:
        cols, lines, assumed = probe_terminal_size(env)
    home = env.get("HOME", "")
    child = dict(env)
    quota = probe_read_quota(common_config.cfg_cache_base(child), child, time.time())
    return Context(
        raw=raw,
        line_conf=config,
        theme=theme,
        cols=cols,
        lines=lines,
        dim_assumed=assumed,
        t_start=t_start,
        model_name=fields.model_name,
        model_id=fields.model_id,
        work_dir=fields.work_dir,
        home=home,
        clock=time.strftime("%H:%M"),
        context_pct=fields.context_pct,
        context_max=fields.context_max,
        host=CursorData(quota),
        transcript_path=fields.transcript_path,
        model_max=fields.model_max,
    )
