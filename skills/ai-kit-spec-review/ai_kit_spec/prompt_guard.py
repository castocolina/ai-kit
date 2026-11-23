"""SPEC R7, R8 (39 D-12, D-13): closed refusal reasons and prompt value validation.

The validator rejects; it never rewrites, trims or drops a value. Check-then-use
is a stated limit: a path can change after the check, so callers run it last
before the spawn.
"""

import os
import subprocess
import unicodedata

from ai_kit_spec import catalog_context, catalog_labels, gsd_tools, models_config, secret_shapes
from ai_kit_spec.cache import cache_read_json
from ai_kit_spec.detection import RUNTIMES
from ai_kit_spec.model_catalog import cache_catalog_path, split_catalog_meta
from ai_kit_spec.routing import strip_model_suffix
from ai_kit_spec.usability import find_runtime_key

# An escaped bracket suffix is the id-bracket form, which can carry a context setting.
BRACKET_SUFFIX = r"\["

REFUSAL_REASONS = (
    "prompt_over_window",
    "value_control_char",
    "path_outside_roots",
    "path_unresolvable",
)
# 39 D-12: the estimated, judged divisor under-counts code and dense scripts.
BYTES_PER_TOKEN = 4
ESTIMATE_LABEL = "estimated, judged"
# SPEC R7 amendment: unused in the runner's STATUS_TABLE.
REFUSED_EXIT = 65

_CONTROL_CATEGORIES = frozenset({"Cc", "Zl", "Zp"})
_FORMAT_RANGES = (
    (0x200B, 0x200F),
    (0x202A, 0x202E),
    (0x2060, 0x2064),
    (0x2066, 0x2069),
    (0xFEFF, 0xFEFF),
)


def is_control_char(ch: str) -> bool:
    """SPEC R8: Unicode Cc, Zl, Zp and listed bidirectional and zero-width formats."""
    cp = ord(ch)
    return unicodedata.category(ch) in _CONTROL_CATEGORIES or any(
        low <= cp <= high for low, high in _FORMAT_RANGES
    )


def escape_value(value: str) -> str:
    """Display controls as a backslash, u and four lower-case hex digits; keep the rest."""
    return "".join(f"\\u{ord(ch):04x}" if is_control_char(ch) else ch for ch in value)


def repo_root(cwd: str, run_fn=subprocess.run) -> str:
    """38 D-06: git top level or real cwd; ignore RUNTIME_DIR by passing an empty env."""
    return os.path.realpath(gsd_tools.project_root({}, cwd, run_fn))


def _resolved(value, repo: str) -> str | None:
    """Resolve a non-empty path from the given start, allowing nonexistent paths.

    Existing ancestors and links are followed; other resolution errors are rejected.
    """
    if not isinstance(value, str) or not value.strip():
        return None
    path = os.path.join(repo, value)
    try:
        return os.path.realpath(path, strict=True)
    except FileNotFoundError:
        return os.path.realpath(path)
    except (OSError, ValueError):
        return None


def _inside(real: str, roots: list) -> bool:
    return any(os.path.commonpath([real, root]) == root for root in roots)


def _reason(value, repo: str, roots: list) -> str | None:
    if isinstance(value, str) and any(is_control_char(ch) for ch in value):
        return "value_control_char"
    real = _resolved(value, repo)
    if real is None:
        return "path_unresolvable"
    return None if _inside(real, roots) else "path_outside_roots"


def _shown(value) -> str:
    """Redact secret shapes on raw text, then escape controls; never change the value."""
    return (
        escape_value(secret_shapes.redact(value, "[redacted]"))
        if isinstance(value, str)
        else f"<not a string: {type(value).__name__}>"
    )


def validate_values(
    values: list[tuple[str, object]], repo: str, skill_roots: list[str],
    extra_roots: tuple = (), base: str | None = None,
) -> list[dict]:
    """Return rejections in input order, with position, reason and shown value.

    Roots are the repository, scan skill roots and extra roots. Pass the run
    directory only for the run-scoped MCP file (SPEC R8 amendment). Relative
    values resolve from base, the child's working directory, or repo if absent.
    """
    if not isinstance(values, list):
        return [{"position": "values", "reason": "path_unresolvable",
                 "shown": f"<not a list: {type(values).__name__}>"}]
    roots = [os.path.realpath(root) for root in (repo, *skill_roots, *extra_roots)
             if isinstance(root, str) and root.strip()]
    start = base or repo
    rejections = []
    for position, value in values:
        reason = _reason(value, start, roots)
        if reason is not None:
            rejections.append({"position": position, "reason": reason, "shown": _shown(value)})
    return rejections


def estimate_tokens(text: str) -> int:
    """Ceil UTF-8 bytes / divisor; runner preamble and host system prompt are not counted."""
    return (len(text.encode("utf-8")) + BYTES_PER_TOKEN - 1) // BYTES_PER_TOKEN


def _window(value, label: str, source, note) -> dict:
    return {"value": value, "label": label, "source": source, "note": note}


def _catalog_fact(runtime: str, bare: str, env: dict) -> dict | None:
    """Return the first matching catalog row's context dict, or None; never write."""
    entries, _meta = split_catalog_meta(cache_read_json(cache_catalog_path(env)))
    key = find_runtime_key(entries, runtime, bare)
    if key is None:
        return None
    fact = entries[key]["runtimes"][runtime].get("context")
    return fact if isinstance(fact, dict) else None


def _bracket_may_carry_context(suffix: str) -> bool:
    """False only when every bracket entry is key=value with a key other than context.

    An effort-only bracket keeps the catalog window; any other form stays unknown (never capped).
    """
    for entry in suffix.strip()[1:-1].split(","):
        key, sep, _value = entry.partition("=")
        if not sep or key.strip() in ("", "context"):
            return True
    return False


def window_for(runtime: str, model: str, env: dict, cwd: str, context_form_applied: bool) -> dict:
    """Resolve the override, unverified context form, or catalog window, in that order.

    Invalid catalog values are unknown; malformed configuration raises ConfigError.
    """
    bare = strip_model_suffix(runtime, model)
    user = catalog_context.valid_tokens(
        catalog_context.override_for(models_config.read_models_settings(cwd, env), runtime, bare)
    )
    if user is not None:
        return _window(user, "user-stated", "[[models.context]]", None)
    if context_form_applied or (
        bare != model and _bracket_may_carry_context(model[len(bare):])
        and (getattr(RUNTIMES.get(runtime), "model_suffix", None) or "").startswith(BRACKET_SUFFIX)
    ):
        return _window(None, "unknown", None, "context_form_applied")
    fact = _catalog_fact(runtime, bare, env)
    if fact is None:
        return _window(None, "unknown", None, None)
    value = catalog_context.valid_tokens(fact.get("value"))
    if value is None:
        note = None if fact.get("value") is None else "catalog_value_invalid"
        return _window(None, "unknown", None, note)
    label, source = fact.get("label"), fact.get("source")
    shown_label = label if label in catalog_labels.LABELS else catalog_labels.UNKNOWN
    shown_source = (
        secret_shapes.redact(source, "[redacted]") if isinstance(source, str) and source else None
    )
    return _window(value, shown_label, shown_source, None)


def refusal_record(reason: str, detail: dict) -> dict:
    """Return a refused result; reason must be in REFUSAL_REASONS."""
    if reason not in REFUSAL_REASONS:
        raise ValueError(f"unknown refusal reason: {reason}")
    return {"status": "refused", "reason": reason, "detail": detail}


def check_window(estimate: int, window: dict) -> dict | None:
    """Refuse estimates above a known window; equal and unknown pass, without seeing the prompt."""
    value = window.get("value")
    if value is None or estimate <= value:
        return None
    return refusal_record("prompt_over_window", {
        "estimate": estimate, "window": value, "label": window.get("label"),
        "source": window.get("source"), "bytes_per_token": BYTES_PER_TOKEN,
        "estimate_label": ESTIMATE_LABEL,
    })
