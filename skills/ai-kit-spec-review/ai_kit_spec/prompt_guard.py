"""SPEC R7, R8 (39 D-12, D-13): closed refusal reasons and prompt value validation.

The validator rejects; it never rewrites, trims or drops a value. Check-then-use
is a stated limit: a path can change after the check, so callers run it last
before the spawn.
"""

import os
import subprocess
import unicodedata

from ai_kit_spec import gsd_tools, secret_shapes

REFUSAL_REASONS = (
    "prompt_over_window",
    "value_control_char",
    "path_outside_roots",
    "path_unresolvable",
)
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
