"""Render types and builder aliases for the Phase 23 D-02 status-line split."""
# pyright: strict

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from common_types import util_parse_color

if TYPE_CHECKING:
    from common_types import Config

# ═══ 1. DEFAULTS — data-only: segment/layout/palette/ramp tables + type decls ═


# A builder takes (ctx, avail_cols, theme) and returns a rendered string or None.
Builder = Callable[["Context", int, "Theme"], str | None]

# ═══ 6. core_ — render machinery: Context, Theme, registry, packer, render ════




def core_str_set() -> set[str]:
    """Typed factory for Context.failed — bare `set` loses the generic parameter."""
    return set()


def core_probe_cache() -> dict[str, Any]:
    """Typed factory for Context.probe_cache — bare `dict` loses the generic parameter."""
    return {}


@dataclass
class Context:  # pylint: disable=too-many-instance-attributes  # per-render bag (D1)
    """Per-render bag handed to every builder (D1). Eager inputs are resolved at
    the SHELL/CONFIG boundary; expensive probes are memoized via `probe_cache`
    so each probe runs synchronously on first access — its cost lands inside the
    *measured* build of the first segment that reads it (FR-R.2) and later reads
    are free. Render bookkeeping (`failed`, `slowest`) lives here too. Attribute
    access only — never `ctx[...]` (D4). `raw` keeps `.get()`-chain access."""
    raw: dict[str, Any]             # incoming status JSON (the ONLY dict-style member)
    line_conf: "Config"
    theme: "Theme"
    # per-render terminal geometry (resolved by the SHELL; D6 — never on Config)
    cols: int
    lines: int
    dim_assumed: bool
    t_start: int | None
    # cheap eager fields (were build_data's `base`)
    model_name: str
    model_id: str
    effort: str
    work_dir: str
    home: str
    clock: str
    added: int
    removed: int
    cost: float
    total_ms: int
    api_ms: int
    context_pct: int
    context_max: int
    rate_limits: dict[str, Any]
    # probe inputs (locate materialized todo/task state; feed the memoized probes)
    transcript: str
    session: str
    claude_dir: str
    # render bookkeeping (D1) — mutated during the render
    failed: set[str] = field(default_factory=core_str_set)
    slowest: tuple[str, int] | None = None
    # memoization cache for per-render probes (keyed by probe name)
    probe_cache: dict[str, Any] = field(default_factory=core_probe_cache)


class Theme:
    """Resolved colors for one render. `palette` maps NAME -> bare SGR params;
    `ramps` band -> [(ceil, escape)]; `effort` level -> (escape, bar). `c()`
    memoizes util_parse_color and never raises (invalid spec -> '')."""

    def __init__(self, palette: dict[str, str],
                 ramps: dict[str, list[tuple[float, str]]],
                 effort: dict[str, tuple[str, str]]) -> None:
        self.palette = palette
        self.ramps = ramps
        self.effort = effort
        self._cache: dict[str, str] = {}

    def c(self, spec: str) -> str:
        """Resolve a color spec to an SGR string, memoizing the lookup."""
        if spec not in self._cache:
            self._cache[spec] = util_parse_color(spec, self.palette) or ""
        return self._cache[spec]
