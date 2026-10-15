"""The reuse-source inventory and the command-key machinery both sides of
the CI-vs-repo match share (D-C3, D-C4, D-C5, D-C6).

The Makefile surface (plan 14-01) and the pre-commit-hook surface (plan
14-02, D-C15) are inventoried here; plan 14-03 EXTENDS `build_reuse_
inventory` by appending its own two surfaces' records to the SAME list
rather than adding a parallel structure. The reuse-invocation TABLE
(D-C6) is complete here across all four surfaces (`make`, `pre-commit
run`, `npm`/`pnpm`/`yarn` script forms, `gradle`/`./gradlew`) --
recognizing an invocation as reuse is a different direction from
inventorying a reuse SOURCE, and only the second is staged across plans.

D-C16: the inventory is built in the FIXED order `SURFACE_ORDER`
(`makefile`, `precommit`, `package-json`, `gradle`) declared once for all
four surfaces, and when two surfaces produce the same command key the
FIRST one inventoried wins -- a property of insertion order plus a
first-wins `seen_keys` set shared across every surface's loop, not a
post-hoc sort or a per-surface priority number.
"""

from __future__ import annotations

import os
import re

from ai_kit_rules_common.command_text import (
    normalize_token,
    split_top_level_segments,
    strip_leading_noise,
)
from ai_kit_rules_common.makefile_parse import (
    parse_makefile_prerequisites,
    parse_makefile_recipe,
    parse_makefile_targets_ordered,
)
from ai_kit_rules_common.precommit_parse import parse_precommit_hooks
from ai_kit_rules_common.tool_catalog import OUT_OF_TAXONOMY_GROUPS, resolve_tool_category
from ai_kit_rules_common.yaml_text import strip_yaml_quotes

from . import gradle_tasks, package_scripts

# D-C16: the four-surface precedence order, declared once here so plan
# 14-03 APPENDS to a settled rule rather than inventing its own tie-break.
# A plain (non-annotated) assignment: this exact literal tuple shape is
# what the SURFACE-ORDER-OK acceptance criterion asserts exists exactly
# once.
SURFACE_ORDER = ("makefile", "precommit", "package-json", "gradle")

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
#
# The bare `yarn <script>`/`pnpm <script>` rows exclude `dlx`/`exec` as
# the immediate next token (a negative lookahead): those are D-C6's
# two-token direct-runner forms (stripped as noise BEFORE this table is
# ever checked), not package.json script names, and an unqualified
# `\S+` here would read `pnpm exec eslint .` as if `exec` were a script
# id -- the exact false-classification the ordering proof in this
# skill's test suite pins against.
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
    (
        re.compile(r"^(?<![-\w])yarn(?![-\w])[ \t]+(?!dlx(?![-\w]))\S+"),
        "package-json",
    ),
    (
        re.compile(r"^(?<![-\w])pnpm(?![-\w])[ \t]+(?!exec(?![-\w]))(?!dlx(?![-\w]))\S+"),
        "package-json",
    ),
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
    identity: str,
    source_name: str,
    derived_from_command_body: bool,
    from_plugin_table: bool = False,
) -> bool:
    """D-C4's tool-shaped identity gate -- the ONE function the Makefile
    surface, the pre-commit-hook surface (plan 14-02), and the
    package-json and Gradle surfaces (plan 14-03) ALL call, never a
    per-surface copy (T-14-18). An identity makes its source USABLE only
    when at least one route holds:
      Route 1: `resolve_tool_category(identity)` is not `None`.
      Route 2: `identity` is an out-of-taxonomy marker (exact,
        casefolded), read directly from `OUT_OF_TAXONOMY_GROUPS` --
        the SAME groups `_OUT_OF_TAXONOMY_FLAT` is built from, checked
        inline here so this ONE function is unambiguously identifiable
        as D-C4's gate.
      Route 3: `normalize(identity) == normalize(source_name)` AND
        `derived_from_command_body` is `True` -- CLOSED to a name-only
        identity that was never derived from a real command body (a
        recipe line, a hook `entry:`, a script body), since D-C3 clause
        (c) and similar name-equals-own-name shapes elsewhere in this
        family would otherwise make Route 3 a tautology.
      Route 4 (D-C19b, plan 14-03): `from_plugin_table` is `True`. This
        is a PARAMETER the CALLER passes, DEFAULTING TO OFF, never a
        membership test this function performs on `identity` itself --
        only the Gradle surface ever passes it, and only after it has
        already confirmed the pinned plugin table's plugin-id evidence
        is present in the build script. Table membership is a property
        of the STRING, not of where the string came from: `ktlint`,
        `detekt` and `dependency-check` are ordinary names a repo can
        give a pre-commit hook, a `package.json` script, or a Makefile
        target, and a membership-test implementation would silently
        admit all three there too. Passing the flag from the caller
        keeps the route meaning "this identity came OUT OF the plugin
        table", never "this identity happens to look like something in
        the plugin table".
    Never raises."""
    if from_plugin_table:
        return True
    if resolve_tool_category(identity) is not None:
        return True
    folded = identity.strip().casefold()
    for group in OUT_OF_TAXONOMY_GROUPS.values():
        if folded in {marker.casefold() for marker in group["markers"]}:  # type: ignore[union-attr]
            return True
    return derived_from_command_body and normalize_token(identity) == normalize_token(
        source_name
    )


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


def _identity_from_recipe_lines(real_lines: list[str]) -> tuple[str | None, bool]:
    for line in real_lines:
        match = _DELEGATE_RE.search(line)
        if match is not None:
            return match.group(1), True
    if len(real_lines) == 1:
        stripped = strip_leading_noise(real_lines[0])
        key, _known = compute_command_key(stripped)
        return key, True
    key0, _ = compute_command_key(strip_leading_noise(real_lines[0]))
    key1, _ = compute_command_key(strip_leading_noise(real_lines[1]))
    if key0 == key1:
        return key0, True
    return None, False


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
        return name, False
    return _identity_from_recipe_lines(real_lines)


def precommit_hook_identity(hook_id: str, entry: str | None) -> tuple[str | None, bool]:
    """D-C15: `(identity, derived_from_command_body)` for a pre-commit
    hook `hook_id` with entry `entry`, both read from the SHARED
    `parse_precommit_hooks` -- never a second `.pre-commit-config.yaml`
    parser inside this skill.

    When `entry` is not `None`: the entry is quote-stripped FIRST via the
    shared `yaml_text.strip_yaml_quotes` (the shared hook reader
    normalizes the hook ID's quoting but NOT the entry's, verified live
    2026-09-14 -- without this step a real `entry: "ruff check"` computes
    the key `"ruff` and matches nothing). The multi-segment aggregate
    test (a top-level `&&`, `||` or `;`, via the shared `command_text.
    split_top_level_segments`) then runs on the UNQUOTED entry, so a
    quoted aggregate is judged on its real content: more than one
    top-level segment means the entry is an aggregate with NO identity,
    the same judgement D-C3's real-line cap makes on the Makefile
    surface. Otherwise the identity is the entry's command key, computed
    by the SAME `strip_leading_noise` + `compute_command_key` a CI line
    goes through, and `derived_from_command_body` is `True`.

    When `entry` is `None` (a non-`local` `repo:` block, whose real
    command lives in an external hook-repo manifest this skill does not
    fetch): the identity is `hook_id` itself, `derived_from_command_body`
    is `False` -- Route 3 of `is_tool_shaped_identity` is therefore
    CLOSED to it, and only Route 1 (`AMBIGUOUS_TOOL_DEFAULTS`'s bare
    `ruff`) or Route 2 (the hygiene group) can admit it. Never raises."""
    if entry is not None:
        unquoted = strip_yaml_quotes(entry)
        if len(split_top_level_segments(unquoted)) > 1:
            return None, False
        stripped = strip_leading_noise(unquoted)
        key, _known = compute_command_key(stripped)
        return key, True
    return hook_id, False


def build_precommit_reuse_records(repo_root: str) -> list[dict]:
    """The pre-commit surface's `{"key", "surface", "reuse_command"}`
    records (D-C15), read ONLY through the shared `parse_precommit_
    hooks` -- wrapped in `try/except (OSError, UnicodeDecodeError)`
    (D-C10): that shared reader guards a MISSING file itself (returns
    `{}`) but not a read failure on a PRESENT one (verified live
    2026-09-14: it raises `UnicodeDecodeError` on binary content), so
    this wrap is the one this task adds. The reuse invocation is
    `pre-commit run <hook_id> --all-files` -- the hook's REAL id, never
    its identity, and deliberately WITHOUT the Phase 11 sibling's `uv
    run` prefix: that prefix is ai-kit's own local convention, while this
    recommendation targets a CI file in an arbitrary repo whose runner
    may not have `uv` at all. Never raises."""
    path = os.path.join(repo_root, ".pre-commit-config.yaml")
    try:
        hooks = parse_precommit_hooks(path)
    except (OSError, UnicodeDecodeError):
        hooks = {}

    records: list[dict] = []
    for hook_id, entry in hooks.items():
        identity, derived = precommit_hook_identity(hook_id, entry)
        if identity is None:
            continue
        if not is_tool_shaped_identity(identity, hook_id, derived):
            continue
        key = normalize_token(identity)
        records.append(
            {
                "key": key,
                "surface": "precommit",
                "reuse_command": f"pre-commit run {hook_id} --all-files",
            }
        )
    return records


def build_package_json_reuse_records(repo_root: str) -> list[dict]:
    """D-C18/D-C18b: the `package.json` script surface's `{"key",
    "surface", "reuse_command"}` records. Each script's command is
    checked for a top-level `&&`/`||`/`;` split FIRST (an aggregate has
    NO identity, the same judgement D-C3's real-line cap and D-C15's
    multi-segment check make); otherwise the identity is the SAME
    `strip_leading_noise` + `compute_command_key` a CI line goes through.
    D-C4's gate applies with `derived_from_command_body=True` -- a
    script's identity always comes from its body -- which is what admits
    a script literally named for its tool (`"eslint": "eslint ."`) even
    when the catalog has never heard of it. The reuse invocation is
    D-C18b's resolved runner plus `run <script-name>` -- the script's REAL
    name, never its identity. `package_scripts.read_package_scripts`
    already degrades every malformed shape to an empty list, so this
    function never raises either."""
    runner = package_scripts.resolve_package_manager_runner(repo_root)
    records: list[dict] = []
    for script_name, command in package_scripts.read_package_scripts(repo_root):
        if len(split_top_level_segments(command)) > 1:
            continue
        stripped = strip_leading_noise(command)
        identity, _known = compute_command_key(stripped)
        if not identity:
            continue
        if not is_tool_shaped_identity(identity, script_name, True):
            continue
        key = normalize_token(identity)
        records.append(
            {
                "key": key,
                "surface": "package-json",
                "reuse_command": f"{runner} run {script_name}",
            }
        )
    return records


def build_gradle_reuse_records(repo_root: str) -> list[dict]:
    """D-C19/D-C19b/D-C20: the Gradle task surface's `{"key", "surface",
    "reuse_command"}` records, both routes over the union of root
    `build.gradle` and `build.gradle.kts` text.

    Route 1 (declared tasks): the identity IS the task name --
    `derived_from_command_body=False` is passed to the gate, since this
    surface never sees a task's body, which is what keeps Route 3 closed
    to a Route-1 identity (see `gradle_tasks`'s module docstring). A
    lifecycle task name (`check`, `build`, `test`, `assemble`) is
    excluded before the gate is ever consulted.

    Route 2 (plugin-contributed tasks): `gradle_tasks.plugin_table_matches`
    already required the plugin-id evidence; this function passes
    `from_plugin_table=True` to the gate for exactly those rows -- D-C19b's
    fourth route, scoped to this surface alone by the caller-passed flag,
    never a membership test the gate performs.

    The reuse invocation is D-C20's wrapper-aware form, naming the task's
    REAL name. `gradle_tasks.read_gradle_build_scripts` already degrades
    every malformed shape to empty text, so this function never raises
    either."""
    text = gradle_tasks.read_gradle_build_scripts(repo_root)
    records: list[dict] = []

    seen_declared: set[str] = set()
    for task_name in gradle_tasks.extract_declared_task_names(text):
        if task_name in gradle_tasks.LIFECYCLE_TASK_NAMES:
            continue
        if task_name in seen_declared:
            continue
        seen_declared.add(task_name)
        if not is_tool_shaped_identity(task_name, task_name, False):
            continue
        key = normalize_token(task_name)
        records.append(
            {
                "key": key,
                "surface": "gradle",
                "reuse_command": gradle_tasks.resolve_gradle_invocation(repo_root, task_name),
            }
        )

    seen_plugin_route: set[str] = set()
    for task_name, tool_identity in gradle_tasks.plugin_table_matches(text):
        if task_name in gradle_tasks.LIFECYCLE_TASK_NAMES:
            continue
        if task_name in seen_plugin_route:
            continue
        seen_plugin_route.add(task_name)
        if not is_tool_shaped_identity(tool_identity, task_name, False, from_plugin_table=True):
            continue
        key = normalize_token(tool_identity)
        records.append(
            {
                "key": key,
                "surface": "gradle",
                "reuse_command": gradle_tasks.resolve_gradle_invocation(repo_root, task_name),
            }
        )

    return records


def build_reuse_inventory(repo_root: str) -> list[dict]:
    """The repo's usable reuse sources as `{"key", "surface",
    "reuse_command"}` records, in `SURFACE_ORDER`'s fixed order (D-C16):
    the Makefile surface (plan 14-01), then the pre-commit-hook surface
    (plan 14-02); plan 14-03 EXTENDS this by appending its own two
    surfaces' records to the SAME list, in the same ONE-list-built-once
    shape.

    Every shared-parser call is wrapped in `try/except (OSError,
    UnicodeDecodeError)` (D-C10): a failed read means "no reuse
    sources", not an exception. When two reuse sources across ANY
    surfaces produce the same key, the FIRST one inventoried wins -- a
    SINGLE `seen_keys` set shared across every surface's loop, not a
    per-surface set or a post-hoc sort -- and the losing source is
    recorded nowhere else. Never raises."""
    makefile_path = os.path.join(repo_root, "Makefile")
    try:
        ordered_targets = parse_makefile_targets_ordered(makefile_path)
    except (OSError, UnicodeDecodeError):
        ordered_targets = []

    records: list[dict] = []
    seen_keys: set[str] = set()

    # SURFACE_ORDER position 1: makefile.
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

    # SURFACE_ORDER position 2: precommit.
    for record in build_precommit_reuse_records(repo_root):
        if record["key"] in seen_keys:
            continue
        seen_keys.add(record["key"])
        records.append(record)

    # SURFACE_ORDER position 3: package-json.
    for record in build_package_json_reuse_records(repo_root):
        if record["key"] in seen_keys:
            continue
        seen_keys.add(record["key"])
        records.append(record)

    # SURFACE_ORDER position 4: gradle.
    for record in build_gradle_reuse_records(repo_root):
        if record["key"] in seen_keys:
            continue
        seen_keys.add(record["key"])
        records.append(record)

    return records


__all__ = [
    "SURFACE_ORDER",
    "build_gradle_reuse_records",
    "build_package_json_reuse_records",
    "build_precommit_reuse_records",
    "build_reuse_inventory",
    "classify_reuse_invocation",
    "compute_command_key",
    "is_tool_shaped_identity",
    "keys_match",
    "makefile_target_identity",
    "precommit_hook_identity",
]
