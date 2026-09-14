"""The reuse-source inventory and the command-key machinery both sides of
the CI-vs-repo match share (D-C3, D-C4, D-C5, D-C6).

Only the Makefile surface is inventoried in this plan; plans 14-02 and
14-03 EXTEND `build_reuse_inventory` by appending one more surface's
records to the SAME list rather than adding a parallel structure. The
reuse-invocation TABLE (D-C6) is complete here across all four surfaces
(`make`, `pre-commit run`, `npm`/`pnpm`/`yarn` script forms,
`gradle`/`./gradlew`) -- recognizing an invocation as reuse is a
different direction from inventorying a reuse SOURCE, and only the
second is staged across plans.
"""

from __future__ import annotations

import os
import re

from ai_kit_rules_common.command_text import (
    normalize_token,
    strip_leading_noise,
)
from ai_kit_rules_common.makefile_parse import (
    parse_makefile_prerequisites,
    parse_makefile_recipe,
    parse_makefile_targets_ordered,
)
from ai_kit_rules_common.tool_catalog import OUT_OF_TAXONOMY_GROUPS, resolve_tool_category

# D-T4's marker groups, flattened once and casefolded -- Route 2 of the
# tool-shaped identity gate, and the KNOWN half of D-C5's key
# computation.
_OUT_OF_TAXONOMY_FLAT: frozenset[str] = frozenset(
    marker.casefold()
    for group in OUT_OF_TAXONOMY_GROUPS.values()
    for marker in group["markers"]  # type: ignore[union-attr]
)

# D-C3 clause (a): the delegated-hook-id shape, searched anywhere on a
# real recipe line (never anchored), token-boundary-aware -- the same
# semantics `ai-kit-project-rules-precommit`'s own `_DELEGATE_RE` uses,
# re-expressed here rather than imported (constraints.md's shared-package
# import convention forbids importing a sibling skill's package).
_DELEGATE_RE = re.compile(
    r"(?<![-\w])pre-commit(?![-\w])[ \t]+(?<![-\w])run(?![-\w])[ \t]+(\S+)"
)

# D-C6's reuse-invocation table, checked AFTER prefix stripping. A
# segment matching a row is a reuse invocation and is NEVER a finding.
# Order matters only where two rows could both match the same text (the
# more specific row is listed first); every mapped surface is otherwise
# independent.
_REUSE_TABLE: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"^(?<![-\w])make(?![-\w])"), "makefile"),
    (
        re.compile(r"^(?<![-\w])pre-commit(?![-\w])[ \t]+(?<![-\w])run(?![-\w])[ \t]+\S+"),
        "precommit",
    ),
    (
        re.compile(
            r"^(?<![-\w])npm(?![-\w])[ \t]+(?<![-\w])(run|run-script|test|start)(?![-\w])"
        ),
        "package-json",
    ),
    (re.compile(r"^(?<![-\w])pnpm(?![-\w])[ \t]+(?<![-\w])run(?![-\w])[ \t]+\S+"), "package-json"),
    (re.compile(r"^(?<![-\w])yarn(?![-\w])[ \t]+(?<![-\w])run(?![-\w])[ \t]+\S+"), "package-json"),
    (re.compile(r"^(?<![-\w])yarn(?![-\w])[ \t]+\S+"), "package-json"),
    (re.compile(r"^(?<![-\w])pnpm(?![-\w])[ \t]+\S+"), "package-json"),
    (re.compile(r"^\./gradlew(?![-\w])[ \t]+\S+"), "gradle"),
    (re.compile(r"^(?<![-\w])gradlew(?![-\w])[ \t]+\S+"), "gradle"),
    (re.compile(r"^(?<![-\w])gradle(?![-\w])[ \t]+\S+"), "gradle"),
)


def classify_reuse_invocation(stripped_segment: str) -> str | None:
    """D-C6's reuse-invocation table, checked AFTER prefix stripping. The
    matched surface name (`"makefile"`, `"precommit"`, `"package-json"`,
    `"gradle"`), or `None` if `stripped_segment` matches no row -- meaning
    it may be a direct invocation. Never raises."""
    for pattern, surface in _REUSE_TABLE:
        if pattern.match(stripped_segment):
            return surface
    return None


def _resolves(key: str) -> bool:
    """D-C5's KNOWN test: `resolve_tool_category` answers it, or it is an
    out-of-taxonomy marker."""
    if resolve_tool_category(key) is not None:
        return True
    return key.casefold() in _OUT_OF_TAXONOMY_FLAT


def compute_command_key(stripped_segment: str) -> tuple[str, bool]:
    """D-C5's command-key computation over an already prefix-stripped
    segment: try the two-token form over the first two remaining tokens,
    then the one-token form. `(key, is_known)` -- `is_known` is `True`
    when the RETURNED key resolves via `_resolves`; if neither form
    resolves, the one-token form is returned and marked unknown. Tokens
    are normalized (basename, casefold, `_`->`-`) via
    `normalize_token`. `("", False)` for an empty/blank
    input. Never raises."""
    tokens = stripped_segment.split()
    if not tokens:
        return "", False
    normalized = [normalize_token(t) for t in tokens[:2]]
    if len(normalized) == 2:
        two_token = f"{normalized[0]} {normalized[1]}"
        if _resolves(two_token):
            return two_token, True
    one_token = normalized[0]
    return one_token, _resolves(one_token)


def keys_match(key_a: str, key_b: str) -> bool:
    """D-C5's match rule: exact string equality, OR first-token equality
    AND `resolve_tool_category` answers both keys with the SAME
    non-`None` category. No substring matching, no suffix stripping, no
    edit distance. Never raises."""
    if key_a == key_b:
        return True
    first_a = key_a.split(" ", 1)[0]
    first_b = key_b.split(" ", 1)[0]
    if first_a != first_b:
        return False
    category_a = resolve_tool_category(key_a)
    category_b = resolve_tool_category(key_b)
    if category_a is None or category_b is None:
        return False
    return category_a == category_b


def is_tool_shaped_identity(
    identity: str, source_name: str, derived_from_command_body: bool
) -> bool:
    """D-C4's tool-shaped identity gate. An identity makes its source
    USABLE only when at least one route holds:
      Route 1: `resolve_tool_category(identity)` is not `None`.
      Route 2: `identity` is an out-of-taxonomy marker (exact, casefolded).
      Route 3: `normalize(identity) == normalize(source_name)` AND
        `derived_from_command_body` is `True` -- CLOSED to a name-only
        identity that was never derived from a real command body (a
        recipe line, a hook `entry:`, a script body), since D-C3 clause
        (c) and similar name-equals-own-name shapes elsewhere in this
        family would otherwise make Route 3 a tautology.
    Never raises."""
    if resolve_tool_category(identity) is not None:
        return True
    if identity.strip().casefold() in _OUT_OF_TAXONOMY_FLAT:
        return True
    if derived_from_command_body and normalize_token(identity) == normalize_token(source_name):
        return True
    return False


def _real_recipe_lines(recipe_text: str) -> list[str]:
    """Real lines of a Makefile recipe: blank lines and comment-only
    lines (first non-whitespace character starts a Make comment) are
    never real."""
    lines: list[str] = []
    for line in recipe_text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        lines.append(stripped)
    return lines


def makefile_target_identity(
    name: str, recipe_text: str, prerequisites
) -> tuple[str | None, bool]:
    """D-C3: `(identity, derived_from_command_body)` for Makefile target
    `name`, or `(None, False)` when `name` has no identity.

    Evaluated in order, under a GLOBAL cap evaluated FIRST: more than 2
    real recipe lines, or zero real recipe lines with prerequisites, is
    an aggregate with NO identity. Then clause (a) (a `pre-commit run
    <id>` delegate line, anywhere among the real lines); then clause (b)
    (exactly one real line, identity is its command key); then clause
    (b2) (exactly two real lines, identity is their SHARED command key
    if -- and only if -- both lines compute the same key, otherwise no
    identity); then clause (c) (zero real lines, no prerequisites -- a
    bare name declaration, identity is the target's own name, NOT derived
    from a command body)."""
    real_lines = _real_recipe_lines(recipe_text)

    if len(real_lines) > 2:
        return None, False
    if not real_lines:
        if prerequisites:
            return None, False
        return name, False  # clause (c)

    for line in real_lines:
        match = _DELEGATE_RE.search(line)
        if match is not None:
            return match.group(1), True  # clause (a)

    if len(real_lines) == 1:
        stripped = strip_leading_noise(real_lines[0])
        key, _known = compute_command_key(stripped)
        return key, True  # clause (b)

    key0, _ = compute_command_key(strip_leading_noise(real_lines[0]))
    key1, _ = compute_command_key(strip_leading_noise(real_lines[1]))
    if key0 == key1:
        return key0, True  # clause (b2), same key
    return None, False  # clause (b2), different keys -> no identity


def build_reuse_inventory(repo_root: str) -> list[dict]:
    """The repo's usable reuse sources as `{"key", "surface",
    "reuse_command"}` records, Makefile surface only in this plan; plans
    14-02/14-03 EXTEND this by appending more surfaces' records to the
    SAME list.

    Every shared-Makefile-parser call is wrapped in
    `try/except (OSError, UnicodeDecodeError)` (D-C10): a failed read
    means "no reuse sources", not an exception. When two reuse sources
    produce the same key, the FIRST in discovery order is kept and the
    collision is recorded nowhere else. Never raises."""
    makefile_path = os.path.join(repo_root, "Makefile")
    try:
        ordered_targets = parse_makefile_targets_ordered(makefile_path)
    except (OSError, UnicodeDecodeError):
        ordered_targets = []

    records: list[dict] = []
    seen_keys: set[str] = set()
    for name in ordered_targets:
        try:
            recipe_text = parse_makefile_recipe(makefile_path, name)
            prerequisites = parse_makefile_prerequisites(makefile_path, name)
        except (OSError, UnicodeDecodeError):
            continue
        identity, derived = makefile_target_identity(name, recipe_text, prerequisites)
        if identity is None:
            continue
        if not is_tool_shaped_identity(identity, name, derived):
            continue
        key = normalize_token(identity)
        if key in seen_keys:
            continue
        seen_keys.add(key)
        records.append({"key": key, "surface": "makefile", "reuse_command": f"make {name}"})
    return records


__all__ = [
    "build_reuse_inventory",
    "classify_reuse_invocation",
    "compute_command_key",
    "is_tool_shaped_identity",
    "keys_match",
    "makefile_target_identity",
]
