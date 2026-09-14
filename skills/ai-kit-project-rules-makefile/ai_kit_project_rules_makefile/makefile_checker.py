"""This skill's Makefile target-shape checker (REQ-rules-makefile).

Every finding this module returns -- static-target, hook-derived, chain/
alias structural, or tooling-category -- carries the same `criticality` and
`summary` fields every finding the sibling `ai-kit-project-rules-agents`
skill's rule checker returns carries: one unified finding schema across
every checker skill in this family.

Mechanically verifying "lightest/cheapest-first" COST ORDER among chained
Makefile targets is explicitly NOT attempted here -- only chain/alias
MEMBERSHIP (via a word-boundary-aware recipe reference OR a genuine Make
prerequisite) is verified. This is a permanent, structural limitation of a
regex-based checker, stated once here rather than re-asserted as a per-run
finding.

OWNERSHIP NOTE: this checker does NOT call `check_precommit_prepush_split`.
That function moved to `skills/_shared/ai_kit_rules_common/precommit_parse.py`
(D-01) because it and the other pre-commit-hook parsers travel as one unit,
but the design spec assigns the precommit-vs-prepush-split CHECK itself to
`ai-kit-project-rules-precommit` (Phase 11), not to this skill. ROADMAP
Phase 10 Success Criterion 1 names exactly three inherited checks and this
is not one of them.
"""

from __future__ import annotations

import os
import re

from ai_kit_rules_common.criticality import (
    CRITICALITY_ADVISORY,
    CRITICALITY_CRITICAL,
    CRITICALITY_HIGH,
    CRITICALITY_MEDIUM,
)
from ai_kit_rules_common.makefile_parse import (
    parse_makefile_prerequisites,
    parse_makefile_prerequisites_ordered,
    parse_makefile_recipe,
    parse_makefile_targets,
    recipe_mentions_target,
)
from ai_kit_rules_common.precommit_parse import parse_precommit_hooks
from ai_kit_rules_common.stack_detect import detect_stacks

from .stack_cache import REQUIRED_STATIC_TARGETS, RESEARCH_CATEGORIES
from .stack_cache import get_stack_tooling as _default_get_stack_tooling

CATEGORY_KEYWORDS = {
    "formatter": ("format", "fmt"),
    "security-scanner": ("security", "bandit", "safety", "gosec", "semgrep", "trivy"),
    "code-smell-detector": ("lint", "pylint", "golangci", "eslint"),
    "duplicate-code-detector": ("dup", "duplicate", "jscpd"),
    "dead-code-detector": ("dead", "vulture", "unused", "deadcode"),
}

# validate-<category> alias family (ROADMAP Phase 10 Success Criterion 2).
# Three names are pinned literally by the roadmap and are not the
# executor's to rename: security, duplicate and dead map to
# `validate-security`, `validate-duplicate` and `validate-dead`. The
# remaining two (formatter, code-smell-detector) are this plan's own
# choice, following the same short-name convention the pinned three
# follow (the category's own primary recognizable keyword, spelled out in
# full rather than abbreviated): `validate-format` and `validate-lint`.
# Stated once here, in code -- Phase 11 and Phase 15 inherit these two
# names rather than re-deriving them (see SUMMARY for the recorded
# decision).
CATEGORY_ALIAS_MAP = {
    "formatter": "validate-format",
    "security-scanner": "validate-security",
    "code-smell-detector": "validate-lint",
    "duplicate-code-detector": "validate-duplicate",
    "dead-code-detector": "validate-dead",
}

# Docker build-before-up (ROADMAP Phase 10 SC5, first clause). PINNED,
# not left to taste -- Phase 13 copies this exact vocabulary rather than
# inventing a second one. Shape-based (a target NAME pattern), not a
# fixed name list, so the docker-prefixed target family Phase 13 will
# later define is covered without this skill enumerating it. Compiled
# once as `re.Pattern` objects at module scope.
_DOCKER_UP_SHAPE_RE = re.compile(r"(?i)^docker(?:-[a-z0-9]+)*-up$")
_DOCKER_BUILD_SHAPE_RE = re.compile(r"(?i)^docker(?:-[a-z0-9]+)*-build$")

# Shellcheck threshold (ROADMAP Phase 10 SC5, second clause).
SHELLCHECK_TARGET_NAME = "shellcheck"
SHELLCHECK_KEYWORDS = ("shellcheck",)
SHELLCHECK_SCRIPT_THRESHOLD = 5
# Pruned during the bounded directory walk: every dot-directory (checked
# separately via `name.startswith(".")`) plus this fixed set of
# dependency/build directory names.
_PRUNED_DIR_NAMES = frozenset(
    {"node_modules", "vendor", "dist", "build", "target", "venv", "__pycache__"}
)
# Names the walk reports the CI half of this rule is confirmed by instead
# -- stated rather than faked, because this skill standalone cannot
# confirm a CI/CD pipeline actually runs shellcheck.
_SHELLCHECK_CI_HALF_NOTE = (
    " This skill standalone confirms only the Makefile target and "
    "pre-commit-hook halves of this rule; the CI half is confirmed by the "
    "`ai-kit-project-rules-cicd` skill (the CI/CD rules checker) and the "
    "`ai-kit-project-rules-all` orchestrator."
)

# Advisory fast-vs-slow ordering heuristic (ROADMAP Phase 10 SC5, third
# clause). Reused baseline knowledge from the design spec's own
# fast-vs-slow ordering guidance, never mechanically verified cost order.
SPEED_TIER_FORMATTER = 1
SPEED_TIER_FAST_LINTER = 2
SPEED_TIER_TYPE_ANALYSIS = 3
SPEED_TIER_SLOWEST = 4

# FOUR KEYWORDS ARE PINNED beyond the design spec's own concrete name
# list: `test`/`unittest`/`pytest` in the slowest tier, `ruff` in the
# fast-linter tier. The spec names `ruff` but no test runner at all, and
# an untiered name is skipped by design -- without this pin the advisory
# check would be silently inert. Matched SLOWEST-TIER-FIRST by
# `speed_tier` below (see its own docstring for why the direction
# matters).
_SPEED_TIERS = (
    (
        SPEED_TIER_SLOWEST,
        ("cargo-udeps", "govulncheck", "bandit", "semgrep", "test", "unittest", "pytest"),
    ),
    (
        SPEED_TIER_TYPE_ANALYSIS,
        ("clippy", "golangci-lint", "mypy", "tsc"),
    ),
    (
        SPEED_TIER_FAST_LINTER,
        ("cargo-machete", "gosec", "ruff"),
    ),
    (
        SPEED_TIER_FORMATTER,
        ("rustfmt", "gofmt", "prettier", "format", "fmt"),
    ),
)


def speed_tier(name: str) -> int | None:
    """Return `name`'s speed tier (1=fastest .. 4=slowest), or `None` for
    an unrecognized name -- never guessed at, so it is excluded from
    inversion detection entirely.

    Matched SLOWEST-TIER-FIRST: several fast-tier keywords are substrings
    of slow-tier tool names (the tier-2 keyword `lint` is a substring of
    the tier-3 tool `golangci-lint`), so a fastest-first scan would
    misclassify a slow tool as fast. Checking tier 4 first, then 3, then
    2, then 1 resolves `golangci-lint` to tier 3 before tier 2's `lint`
    keyword ever gets a chance to match it.
    """
    lowered = name.lower()
    for tier, keywords in _SPEED_TIERS:
        if any(keyword in lowered for keyword in keywords):
            return tier
    return None


# Help/fail reachability (ROADMAP Phase 10 SC3). Both read the raw Makefile
# text directly -- neither form survives `parse_makefile_targets` (its
# header pattern excludes lines starting with a dot, and its character
# class contains no `%`), so neither mechanism can be detected by looking
# in the parsed target set.
_DEFAULT_GOAL_RE = re.compile(r"^\s*\.DEFAULT_GOAL\s*(?::=|=)\s*(\S+)", re.MULTILINE)

# PINNED: a STEMLESS catch-all target only -- a line-leading `%` followed by
# optional horizontal whitespace and then a `:` that is not the `:=` of an
# assignment. A STEMMED pattern/suffix rule (`%.o: %.c`) must NOT satisfy
# this: it tells Make how to build one file class from another and does
# nothing for an unknown-target invocation.
_CATCHALL_RE = re.compile(r"^%[ \t]*:(?!=)", re.MULTILINE)

# Header-line pattern used ONLY to build the single-pass target->recipe
# mapping below (`_build_recipe_map`), mirroring
# `ai_kit_rules_common.makefile_parse`'s own private `_TARGET_HEADER_RE`
# character-for-character (that pattern is module-private there, so it is
# re-derived here rather than imported) -- so this module's own recipe-cap
# scan can never disagree with the shared parser about what counts as a
# target header.
_HEADER_LINE_RE = re.compile(r"^(?!\.)([A-Za-z0-9_.-]+)\s*:(?!=)")


def _default_goal_target(text: str) -> str | None:
    match = _DEFAULT_GOAL_RE.search(text)
    return match.group(1) if match else None


def _has_stemless_catchall(text: str) -> bool:
    return _CATCHALL_RE.search(text) is not None


def _build_recipe_map(text: str) -> dict[str, str]:
    """Single pass over `text` building `target -> recipe text`.

    Guards against the quadratic scan a naive per-target call to
    `parse_makefile_recipe` would cause on a large Makefile (that reader
    re-reads and re-scans the whole file per target): this walks the file
    ONCE, mirroring `parse_makefile_recipe`'s own header/recipe boundary
    rules (a blank or indented line continues the current recipe; the
    first non-indented, non-blank line ends it) so results agree with the
    shared reader. First occurrence wins for a duplicated target name,
    matching `parse_makefile_recipe`'s own first-match behavior.
    """
    recipes: dict[str, str] = {}
    current_target: str | None = None
    current_lines: list[str] = []

    def _flush():
        nonlocal current_target, current_lines
        if current_target is not None and current_target not in recipes:
            recipes[current_target] = "".join(current_lines)
        current_target = None
        current_lines = []

    for line in text.splitlines(keepends=True):
        header_match = _HEADER_LINE_RE.match(line)
        if header_match:
            _flush()
            current_target = header_match.group(1)
            continue
        if current_target is None:
            continue
        if line.strip() == "" or line[:1] in (" ", "\t"):
            current_lines.append(line)
        else:
            _flush()
    _flush()
    return recipes


def _real_recipe_line_count(recipe_text: str) -> int:
    """Count `recipe_text`'s real lines: blank lines and comment-only
    lines (first non-whitespace character starts a Make comment) are not
    real lines."""
    count = 0
    for line in recipe_text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        count += 1
    return count


def _resolve_across_stacks(name, detected_stacks, get_tooling):
    """Shared staleness-gated, all-stacks-covered resolution helper.

    Returns `(recommendation_or_None, needs_research, missing_stacks)`.
    Used by BOTH the static-target loop and the tooling-category loop --
    one staleness-gating implementation, not two.
    """
    if not detected_stacks:
        return None, True, []
    covering = {}
    for stack in sorted(detected_stacks):
        tooling, needs_research = get_tooling(stack)
        if not needs_research and tooling is not None and tooling.get(name) is not None:
            covering[stack] = tooling[name]
    missing = sorted(s for s in detected_stacks if s not in covering)
    if missing:
        return None, True, missing
    combined = "; ".join(f"{s}: {covering[s]}" for s in sorted(covering))
    return combined, False, []


def _alias_required_targets(category: str, present_targets: set[str]) -> list[str]:
    """Return the sorted present target names that make `category`'s
    `validate-<...>` alias required.

    A target whose lowercased name begins with `validate` never counts --
    otherwise `validate-security` would make itself required, and
    `validate` would trigger every category.
    """
    keywords = CATEGORY_KEYWORDS[category]
    return sorted(
        name
        for name in present_targets
        if not name.lower().startswith("validate")
        and any(kw in name.lower() for kw in keywords)
    )


def _docker_build_before_up_findings(
    makefile_path: str, present_targets: set[str]
) -> list[dict]:
    """Docker build-before-up (ROADMAP Phase 10 SC5, first clause).

    For each present up-shaped target, satisfied when EITHER one of its
    Make prerequisites is build-shaped, OR its recipe token-boundary-
    references a build-shaped target that is actually present -- the same
    `prerequisite OR token-boundary recipe reference` wiring rule the
    inherited `chain_incomplete` check already uses. There is deliberately
    NO "standalone build token" clause: the token-boundary helper's
    pattern (`(?<![-\\w])NAME(?![-\\w])`) cannot match a bare `build`
    token inside `docker compose up --build` (the character immediately
    before is `-`), so a `docker-up` whose only build is that inline flag
    IS flagged, with a summary naming what was checked rather than
    claiming the recipe performs no build.
    """
    findings: list[dict] = []
    up_targets = sorted(t for t in present_targets if _DOCKER_UP_SHAPE_RE.match(t))
    build_targets = {t for t in present_targets if _DOCKER_BUILD_SHAPE_RE.match(t)}

    for target in up_targets:
        prereqs = parse_makefile_prerequisites(makefile_path, target)
        recipe = parse_makefile_recipe(makefile_path, target)
        satisfied = any(_DOCKER_BUILD_SHAPE_RE.match(p) for p in prereqs) or any(
            recipe_mentions_target(recipe, build_target) for build_target in build_targets
        )
        if satisfied:
            continue
        recommendation = (
            f"add a build-shaped Make prerequisite to `{target}` (e.g. "
            f"`{target}: docker-build`), or invoke an existing build-shaped "
            "target from its recipe (e.g. `$(MAKE) docker-build`)"
        )
        summary = (
            f"`{target}` declares no build-shaped Make prerequisite and its "
            "recipe does not invoke an existing build-shaped target"
        )
        findings.append(
            {
                "target": target,
                "present": True,
                "issue": "docker_build_not_wired",
                "recommendation": recommendation,
                "needs_research": False,
                "criticality": CRITICALITY_HIGH,
                "summary": summary,
            }
        )
    return findings


def _count_shell_scripts(
    repo_root: str, threshold: int = SHELLCHECK_SCRIPT_THRESHOLD
) -> tuple[int, bool]:
    """Bounded walk of `repo_root`: prune every dot-directory and every
    directory named in `_PRUNED_DIR_NAMES`, counting `.sh` files, and
    STOP as soon as `threshold` is reached.

    Returns `(count, is_floor)`. `is_floor` is `True` when the walk
    stopped early -- `count` is then a FLOOR (`"at least this many"`),
    never an exact total above threshold. Stopping early bounds the walk
    on a pathological target repo: this check only ever needs to know "at
    least `threshold`", never the exact number above it.
    """
    count = 0
    for _root, dirnames, filenames in os.walk(repo_root):
        dirnames[:] = [
            d for d in dirnames if not d.startswith(".") and d not in _PRUNED_DIR_NAMES
        ]
        for name in filenames:
            if name.endswith(".sh"):
                count += 1
                if count >= threshold:
                    return count, True
    return count, False


def _shellcheck_threshold_findings(
    repo_root: str, present_targets: set[str], hooks: dict[str, str | None]
) -> list[dict]:
    """Shellcheck threshold (ROADMAP Phase 10 SC5, second clause)."""
    count, is_floor = _count_shell_scripts(repo_root)
    if count < SHELLCHECK_SCRIPT_THRESHOLD:
        return []

    count_field = "script_count_floor" if is_floor else "script_count"
    count_prefix = "at least " if is_floor else ""
    has_target = any(
        any(kw in name.lower() for kw in SHELLCHECK_KEYWORDS) for name in present_targets
    )
    if not has_target:
        recommendation = (
            f"add a `{SHELLCHECK_TARGET_NAME}` Makefile target running "
            "shellcheck over this repo's shell scripts"
        )
        summary = (
            f"{count_prefix}{count} shell scripts were found and no present "
            "Makefile target's name carries a shellcheck keyword."
            + _SHELLCHECK_CI_HALF_NOTE
        )
        return [
            {
                "target": SHELLCHECK_TARGET_NAME,
                "present": False,
                "issue": "shellcheck_target_missing",
                count_field: count,
                "recommendation": recommendation,
                "needs_research": False,
                "criticality": CRITICALITY_HIGH,
                "summary": summary,
            }
        ]

    has_hook = any(
        any(kw in hook_id.lower() for kw in SHELLCHECK_KEYWORDS) for hook_id in hooks
    )
    if has_hook:
        return []

    recommendation = (
        f"wire the existing `{SHELLCHECK_TARGET_NAME}` Makefile target into "
        "`.pre-commit-config.yaml` as a hook"
    )
    summary = (
        f"{count_prefix}{count} shell scripts were found and a "
        "shellcheck-shaped Makefile target exists but no pre-commit hook id "
        "names it." + _SHELLCHECK_CI_HALF_NOTE
    )
    return [
        {
            "target": SHELLCHECK_TARGET_NAME,
            "present": True,
            "issue": "shellcheck_target_not_wired",
            count_field: count,
            "recommendation": recommendation,
            "needs_research": False,
            "criticality": CRITICALITY_HIGH,
            "summary": summary,
        }
    ]


def check_validate_order(repo_root: str, chain_incomplete_found: bool) -> dict | None:
    """Advisory, non-blocking fast-vs-slow ordering suggestion for
    `validate`'s prerequisite list (ROADMAP Phase 10 SC5, third clause).

    When chain membership is incomplete, the existing `chain_incomplete`
    finding (from `check_makefile_shape`) is the sole source of truth for
    that gap -- ordering advice about a list that is missing members is
    noise, so this returns `None`. Otherwise, mechanically verifying true
    cost ORDER ("lightest/cheapest first") among the chained targets is
    still not attempted for BLOCKING purposes -- a permanent, structural
    limitation of a regex-based checker. What this now returns is a
    best-effort suggestion built from hardcoded baseline knowledge
    (`speed_tier`), never a blocking finding: the returned dict (when not
    `None`) always carries `advisory: True` and `CRITICALITY_ADVISORY`.
    """
    if chain_incomplete_found:
        return None

    makefile_path = os.path.join(repo_root, "Makefile")
    prereqs = parse_makefile_prerequisites_ordered(makefile_path, "validate")
    tiered = [(name, speed_tier(name)) for name in prereqs]
    tiered = [(name, tier) for name, tier in tiered if tier is not None]

    inversions: list[tuple[str, str]] = []
    for i, (earlier_name, earlier_tier) in enumerate(tiered):
        for later_name, later_tier in tiered[i + 1 :]:
            if earlier_tier > later_tier:
                inversions.append((earlier_name, later_name))

    if not inversions:
        return None

    pairs_text = "; ".join(f"'{a}' before '{b}'" for a, b in inversions)
    recommendation = (
        "reorder `validate`'s prerequisites so faster checks run first "
        f"(currently inverted: {pairs_text})"
    )
    return {
        "target": "validate",
        "present": True,
        "issue": "validate_order_advisory",
        "inverted_pairs": inversions,
        "advisory": True,
        "recommendation": recommendation,
        "needs_research": False,
        "criticality": CRITICALITY_ADVISORY,
        "summary": recommendation,
    }


def check_makefile_shape(repo_root: str, get_tooling=None) -> list[dict]:
    """Return a list of Makefile-target/tooling-category gap findings.

    A missing Makefile or `.pre-commit-config.yaml` is reported as the
    maximal, most informative gap (every required target missing), never a
    crash -- both parsers return an empty result for an absent file.
    """
    if get_tooling is None:
        get_tooling = _default_get_stack_tooling

    makefile_path = os.path.join(repo_root, "Makefile")
    precommit_path = os.path.join(repo_root, ".pre-commit-config.yaml")

    present_targets = parse_makefile_targets(makefile_path)
    hooks = parse_precommit_hooks(precommit_path)
    detected = detect_stacks(repo_root)

    # Read once, shared by the reachability check and the recipe-cap
    # check's single-pass recipe map (Task 2) -- avoids re-reading the
    # file per check and per target.
    makefile_text = ""
    if os.path.isfile(makefile_path):
        with open(makefile_path, encoding="utf-8") as handle:
            makefile_text = handle.read()

    findings: list[dict] = []

    required = set(REQUIRED_STATIC_TARGETS) | set(hooks.keys())
    for name in sorted(required):
        if name in present_targets:
            continue
        finding = {"target": name, "present": False, "criticality": CRITICALITY_CRITICAL}
        if name in hooks:
            cmd = hooks[name] if hooks[name] else f"pre-commit run {name}"
            finding["recommendation"] = f"add a `{name}` target running: {cmd}"
            finding["summary"] = f"Add Makefile target '{name}' running: {cmd}"
            finding["needs_research"] = False
        else:
            recommendation, needs_research, missing_stacks = _resolve_across_stacks(
                name, detected, get_tooling
            )
            if needs_research and detected:
                finding["recommendation"] = None
                finding["needs_research"] = True
                finding["stacks"] = missing_stacks
                finding["summary"] = (
                    f"Makefile target '{name}' needs research for stack(s): "
                    f"{', '.join(missing_stacks)}"
                )
            elif needs_research:
                finding["recommendation"] = None
                finding["needs_research"] = True
                finding["stacks"] = []
                finding["summary"] = (
                    f"Makefile target '{name}' needs a detected stack before "
                    "any tooling recommendation is possible -- no stack "
                    "markers found in this repo"
                )
            else:
                finding["recommendation"] = recommendation
                finding["needs_research"] = False
                finding["summary"] = f"Add Makefile target '{name}': {recommendation}"
        findings.append(finding)

    already_present_names = {n.lower() for n in present_targets} | {
        n.lower() for n in hooks
    }
    for category in RESEARCH_CATEGORIES:
        keywords = CATEGORY_KEYWORDS[category]
        if any(kw in name for name in already_present_names for kw in keywords):
            continue
        recommendation, needs_research, missing_stacks = _resolve_across_stacks(
            category, detected, get_tooling
        )
        finding = {"category": category, "criticality": CRITICALITY_CRITICAL}
        if needs_research and detected:
            finding["recommendation"] = None
            finding["needs_research"] = True
            finding["stacks"] = missing_stacks
            finding["summary"] = (
                f"Tooling category '{category}' needs research for stack(s): "
                f"{', '.join(missing_stacks)}"
            )
        elif needs_research:
            finding["recommendation"] = None
            finding["needs_research"] = True
            finding["stacks"] = []
            finding["summary"] = (
                f"Tooling category '{category}' needs a detected stack "
                "before any tooling recommendation is possible -- no stack "
                "markers found in this repo"
            )
        else:
            finding["recommendation"] = recommendation
            finding["needs_research"] = False
            finding["summary"] = f"Add tooling category '{category}': {recommendation}"
        findings.append(finding)

    chain_incomplete_found = False
    if "validate" in present_targets:
        validate_recipe = parse_makefile_recipe(makefile_path, "validate")
        validate_prereqs = parse_makefile_prerequisites(makefile_path, "validate")
        chainable = {hook_id for hook_id in hooks if hook_id in present_targets}
        if chainable:

            def _wired(member):
                return (
                    recipe_mentions_target(validate_recipe, member)
                    or member in validate_prereqs
                )

            missing_chain_members = sorted(m for m in chainable if not _wired(m))
            if missing_chain_members:
                chain_incomplete_found = True
                recommendation = (
                    "restructure `validate` to invoke each of: "
                    + ", ".join(sorted(chainable))
                    + " explicitly (via its recipe or as a Make prerequisite; "
                    "lightest/cheapest check first)"
                )
                findings.append(
                    {
                        "target": "validate",
                        "present": True,
                        "issue": "chain_incomplete",
                        "missing_chain_members": missing_chain_members,
                        "recommendation": recommendation,
                        "needs_research": False,
                        "criticality": CRITICALITY_CRITICAL,
                        "summary": recommendation,
                    }
                )

    if "test" in present_targets and "test-unit" in present_targets:
        test_recipe = parse_makefile_recipe(makefile_path, "test")
        test_unit_recipe = parse_makefile_recipe(makefile_path, "test-unit")
        test_prereqs = parse_makefile_prerequisites(makefile_path, "test")
        test_unit_prereqs = parse_makefile_prerequisites(makefile_path, "test-unit")
        aliased = (
            recipe_mentions_target(test_recipe, "test-unit")
            or recipe_mentions_target(test_unit_recipe, "test")
            or "test-unit" in test_prereqs
            or "test" in test_unit_prereqs
            or test_recipe.strip() == test_unit_recipe.strip()
        )
        if not aliased:
            recommendation = (
                "make `test` invoke `test-unit` (e.g. `$(MAKE) test-unit`), "
                "list it as a Make prerequisite (`test: test-unit`), or keep "
                "their recipes identical so the two names are a genuine "
                "alias, per REQ-rules-makefile"
            )
            findings.append(
                {
                    "target": "test-unit-alias",
                    "present": True,
                    "issue": "not_aliased",
                    "recommendation": recommendation,
                    "needs_research": False,
                    "criticality": CRITICALITY_CRITICAL,
                    "summary": recommendation,
                }
            )

    # validate-<category> alias family (ROADMAP Phase 10 SC2). Placed after
    # the inherited chain block above so both see the same parsed target
    # set (`present_targets`).
    required_aliases: list[tuple[str, str, list[str]]] = []
    for category in RESEARCH_CATEGORIES:
        triggering = _alias_required_targets(category, present_targets)
        if not triggering:
            continue  # this category requires no alias
        required_aliases.append((category, CATEGORY_ALIAS_MAP[category], triggering))

    for category, alias, triggering in required_aliases:
        if alias in present_targets:
            continue
        recommendation = (
            f"add Makefile target '{alias}' and chain it into `validate` "
            f"(required by the {category} category's concrete target(s): "
            + ", ".join(triggering)
            + ")"
        )
        findings.append(
            {
                "target": alias,
                "present": False,
                "issue": "alias_missing",
                "alias_category": category,
                "triggering_targets": triggering,
                "recommendation": recommendation,
                "needs_research": False,
                "criticality": CRITICALITY_HIGH,
                "summary": recommendation,
            }
        )

    if "validate" in present_targets and required_aliases:
        validate_recipe = parse_makefile_recipe(makefile_path, "validate")
        validate_prereqs = parse_makefile_prerequisites(makefile_path, "validate")

        def _alias_wired(alias_name):
            return (
                recipe_mentions_target(validate_recipe, alias_name)
                or alias_name in validate_prereqs
            )

        unchained_aliases = sorted(
            {
                alias
                for _category, alias, _triggering in required_aliases
                if alias in present_targets and not _alias_wired(alias)
            }
        )
        if unchained_aliases:
            recommendation = (
                "chain the following alias target(s) into `validate` (via "
                "its recipe or as a Make prerequisite): "
                + ", ".join(unchained_aliases)
            )
            findings.append(
                {
                    "target": "validate",
                    "present": True,
                    "issue": "alias_chain_incomplete",
                    "missing_alias_members": unchained_aliases,
                    "recommendation": recommendation,
                    "needs_research": False,
                    "criticality": CRITICALITY_HIGH,
                    "summary": recommendation,
                }
            )

    # Help/fail reachability (ROADMAP Phase 10 SC3).
    default_goal_name = _default_goal_target(makefile_text)
    has_catchall = _has_stemless_catchall(makefile_text)
    default_goal_satisfied = (
        default_goal_name is not None and default_goal_name in present_targets
    )
    if not default_goal_satisfied and not has_catchall:
        if default_goal_name is not None:
            reach_summary = (
                f"`.DEFAULT_GOAL` points at '{default_goal_name}', which is not a "
                "defined target, so an unknown-target invocation has no reachable "
                "help path"
            )
        else:
            reach_summary = (
                "no `.DEFAULT_GOAL` directive naming a real target and no "
                "stemless catch-all `%:` rule, so an unknown-target invocation "
                "has no reachable help path"
            )
        findings.append(
            {
                "target": "help",
                "present": "help" in present_targets,
                "issue": "no_reachable_help_path",
                "recommendation": (
                    "add a `.DEFAULT_GOAL := help`-style directive naming a real "
                    "target, or a stemless catch-all rule (`%:`) that prints usage"
                ),
                "needs_research": False,
                "criticality": CRITICALITY_MEDIUM,
                "summary": reach_summary,
            }
        )

    # 3-line recipe cap (ROADMAP Phase 10 SC4). The exempt set has exactly
    # two members, both fixture-discriminable: the target named by the
    # default-goal directive, and a target literally named `help`. The
    # stemless catch-all is deliberately NOT a member --
    # `parse_makefile_targets`'s header pattern contains no `%`, so a
    # catch-all never enters `present_targets` and this loop never sees its
    # body; an exemption for it would be unreachable by construction.
    recipe_exempt_targets = set()
    if default_goal_name is not None and default_goal_name in present_targets:
        recipe_exempt_targets.add(default_goal_name)
    if "help" in present_targets:
        recipe_exempt_targets.add("help")

    recipe_map = _build_recipe_map(makefile_text)
    for target in sorted(present_targets):
        if target in recipe_exempt_targets:
            continue
        line_count = _real_recipe_line_count(recipe_map.get(target, ""))
        if line_count > 3:
            cap_recommendation = (
                f"extract `{target}`'s {line_count}-line recipe into a shell "
                "script the target then calls"
            )
            findings.append(
                {
                    "target": target,
                    "present": True,
                    "issue": "recipe_too_long",
                    "line_count": line_count,
                    "recommendation": cap_recommendation,
                    "needs_research": False,
                    "criticality": CRITICALITY_MEDIUM,
                    "summary": cap_recommendation,
                }
            )

    # Docker build-before-up (ROADMAP Phase 10 SC5, first clause).
    findings.extend(_docker_build_before_up_findings(makefile_path, present_targets))

    # Shellcheck threshold (ROADMAP Phase 10 SC5, second clause).
    findings.extend(_shellcheck_threshold_findings(repo_root, present_targets, hooks))

    # Advisory fast-vs-slow ordering heuristic (ROADMAP Phase 10 SC5, third
    # clause).
    validate_order_finding = check_validate_order(repo_root, chain_incomplete_found)
    if validate_order_finding is not None:
        findings.append(validate_order_finding)

    return findings
