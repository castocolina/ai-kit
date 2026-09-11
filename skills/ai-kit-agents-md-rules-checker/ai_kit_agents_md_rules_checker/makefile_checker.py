"""Makefile target-shape + pre-commit-hook-parity checker (REQ-agtmd-makefile-rules).

Every finding this module returns -- static-target, hook-derived, chain/
alias structural, or tooling-category -- carries the same `criticality` and
`summary` fields every `workflow` finding (rule_checker.py) carries: one
unified finding schema across both checkers.

Mechanically verifying "lightest/cheapest-first" COST ORDER among chained
Makefile targets is explicitly NOT attempted here -- only chain/alias
MEMBERSHIP (via a word-boundary-aware recipe reference OR a genuine Make
prerequisite) is verified. This is a permanent, structural limitation of a
regex-based checker, stated once here rather than re-asserted as a per-run
finding.
"""

from __future__ import annotations

import os
import re

from .rules import CRITICALITY_CRITICAL, CRITICALITY_MEDIUM
from .stack_cache import REQUIRED_STATIC_TARGETS, RESEARCH_CATEGORIES
from .stack_cache import get_stack_tooling as _default_get_stack_tooling
from .stack_detect import detect_stacks

_TARGET_HEADER_RE = re.compile(r"^(?!\.)([A-Za-z0-9_.-]+)\s*:(?!=)(.*)$", re.MULTILINE)

CATEGORY_KEYWORDS = {
    "formatter": ("format", "fmt"),
    "security-scanner": ("security", "bandit", "safety", "gosec", "semgrep", "trivy"),
    "code-smell-detector": ("lint", "pylint", "golangci", "eslint"),
    "duplicate-code-detector": ("dup", "duplicate", "jscpd"),
    "dead-code-detector": ("dead", "vulture", "unused", "deadcode"),
}

SLOW_HOOK_KEYWORDS = (
    "test",
    "pytest",
    "unittest",
    "mypy",
    "pyright",
    "vulture",
    "integration",
    "e2e",
    "arch",
)

_ID_LINE_RE = re.compile(r"^\s*-\s*id:\s*(.+?)\s*$", re.MULTILINE)
_ENTRY_LINE_RE = re.compile(r"^\s*entry:\s*(.+?)\s*$", re.MULTILINE)
_STAGES_LINE_RE = re.compile(r"^\s*stages:\s*(.+?)\s*$", re.MULTILINE | re.IGNORECASE)


def _strip_yaml_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        return value[1:-1]
    return value


def parse_makefile_targets(path: str) -> set[str]:
    """Return the set of real target names defined in `path`.

    `.PHONY:`/other special targets and recipe lines are never mistaken for
    targets; a `VAR := value` / `VAR ?= value` assignment is excluded via
    the `(?!=)` guard on the colon. Empty set if `path` does not exist.
    """
    if not os.path.isfile(path):
        return set()
    with open(path, encoding="utf-8") as handle:
        text = handle.read()
    return {m.group(1) for m in _TARGET_HEADER_RE.finditer(text)}


def parse_makefile_prerequisites(path: str, target: str) -> set[str]:
    """Return `target`'s Make prerequisite tokens (`target: dep1 dep2`).

    Distinct from `parse_makefile_recipe`: prerequisites are declared on the
    header line itself, recipe lines are the indented lines that follow.
    Empty set if `target` is absent or declares no prerequisites.
    """
    if not os.path.isfile(path):
        return set()
    with open(path, encoding="utf-8") as handle:
        text = handle.read()
    pattern = re.compile(
        rf"^(?!\.){re.escape(target)}\s*:(?!=)(.*)$", re.MULTILINE
    )
    match = pattern.search(text)
    if match is None:
        return set()
    prereq_text = match.group(1).split("#", 1)[0]
    return set(prereq_text.split())


def parse_makefile_recipe(path: str, target: str) -> str:
    """Return the joined text of `target`'s indented recipe lines.

    `""` if `target` is absent. Stops at the next non-indented, non-blank
    line after the header.
    """
    if not os.path.isfile(path):
        return ""
    with open(path, encoding="utf-8") as handle:
        lines = handle.readlines()
    pattern = re.compile(rf"^(?!\.){re.escape(target)}\s*:(?!=)")
    header_idx = None
    for idx, line in enumerate(lines):
        if pattern.match(line):
            header_idx = idx
            break
    if header_idx is None:
        return ""
    recipe_lines = []
    for line in lines[header_idx + 1 :]:
        if line.strip() == "" or line[:1] in (" ", "\t"):
            recipe_lines.append(line)
            continue
        break
    return "".join(recipe_lines)


def _iter_precommit_hook_blocks(text: str):
    """Yield `(hook_id, entry_or_None, block_text)` for every `- id:` hook.

    `hook_id` is normalized to its bare string regardless of bare/single/
    double-quoted YAML form. A hook's block runs from its own `- id:` line
    up to (not including) the next `- id:` line, or end of file.
    """
    id_matches = list(_ID_LINE_RE.finditer(text))
    for pos, match in enumerate(id_matches):
        hook_id = _strip_yaml_quotes(match.group(1))
        start = match.start()
        end = id_matches[pos + 1].start() if pos + 1 < len(id_matches) else len(text)
        block = text[start:end]
        entry_match = _ENTRY_LINE_RE.search(block)
        entry = entry_match.group(1) if entry_match else None
        yield hook_id, entry, block


def parse_precommit_hooks(path: str) -> dict[str, str | None]:
    """Return `dict[hook_id, entry_command_or_None]` for every hook id.

    Matches a hook id whether declared bare, double-quoted, or single-
    quoted. `None` when that hook has no inline `entry:` line (e.g. a
    non-`local` `repo:` block whose real command lives in an external
    hook-repo manifest). Empty dict if `path` does not exist.
    """
    if not os.path.isfile(path):
        return {}
    with open(path, encoding="utf-8") as handle:
        text = handle.read()
    return {hook_id: entry for hook_id, entry, _block in _iter_precommit_hook_blocks(text)}


def _recipe_mentions_target(recipe_text: str, name: str) -> bool:
    """Word-boundary-aware check: never a raw substring match.

    `name="lint"` does not match a recipe invoking `"pylint"`, but
    `name="test-unit"` matches the literal token `"test-unit"` (the
    internal hyphen is not a boundary point; `\\b` is only evaluated at the
    two ends of `name`).
    """
    return re.search(rf"\b{re.escape(name)}\b", recipe_text) is not None


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


def check_validate_order(repo_root: str, chain_incomplete_found: bool) -> None:
    """Structural check for the removed `validate-order` research category.

    Never appends its own finding in either branch. When chain membership
    is incomplete, the existing `chain_incomplete` finding (from
    `check_makefile_shape`) is the sole source of truth for that gap. When
    chain membership is complete, mechanically verifying true cost ORDER
    ("lightest/cheapest first") among the chained targets is still not
    attempted -- a permanent, structural limitation of a regex-based
    checker, documented here (and in this plan's `<done>`/
    `success_criteria`) rather than re-asserted as a per-run finding that
    would report the same non-actionable caveat on every single invocation.
    """
    del repo_root, chain_incomplete_found  # intentionally unused; see docstring
    return None


def check_precommit_prepush_split(repo_root: str) -> dict | None:
    """Structural check for the removed `precommit-vs-prepush-split` category.

    Classifies each present hook as "slow" via `SLOW_HOOK_KEYWORDS`
    (case-insensitive substring match against that hook's id OR its
    `entry:` command), then checks EACH slow hook's OWN YAML block for its
    own `stages:` value naming `pre-push`/`push` -- never "does ANY hook
    anywhere have a push stage". Returns `None` when there is nothing to
    verify (no slow hook at all) or every slow hook already has its own
    push stage; otherwise returns one finding naming every slow hook still
    missing its own push stage.
    """
    path = os.path.join(repo_root, ".pre-commit-config.yaml")
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as handle:
        text = handle.read()
    missing = []
    for hook_id, entry, block in _iter_precommit_hook_blocks(text):
        haystack = f"{hook_id} {entry or ''}".lower()
        if not any(keyword in haystack for keyword in SLOW_HOOK_KEYWORDS):
            continue
        stages_match = _STAGES_LINE_RE.search(block)
        value = stages_match.group(1).lower() if stages_match else ""
        if "pre-push" in value or "push" in value:
            continue
        missing.append(hook_id)
    if not missing:
        return None
    ids = sorted(missing)
    recommendation = (
        "split the slower hooks into a pre-push stage (e.g. add "
        "`stages: [pre-push]` to: " + ", ".join(ids) + ") so `pre-commit` "
        "itself stays fast"
    )
    return {
        "category": "precommit-vs-prepush-split",
        "issue": "slow_hooks_not_pushed",
        "slow_hooks_missing_push_stage": ids,
        "recommendation": recommendation,
        "needs_research": False,
        "criticality": CRITICALITY_MEDIUM,
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
                    _recipe_mentions_target(validate_recipe, member)
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
            _recipe_mentions_target(test_recipe, "test-unit")
            or _recipe_mentions_target(test_unit_recipe, "test")
            or "test-unit" in test_prereqs
            or "test" in test_unit_prereqs
            or test_recipe.strip() == test_unit_recipe.strip()
        )
        if not aliased:
            recommendation = (
                "make `test` invoke `test-unit` (e.g. `$(MAKE) test-unit`), "
                "list it as a Make prerequisite (`test: test-unit`), or keep "
                "their recipes identical so the two names are a genuine "
                "alias, per REQ-agtmd-makefile-rules"
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

    check_validate_order(repo_root, chain_incomplete_found)

    split_finding = check_precommit_prepush_split(repo_root)
    if split_finding is not None:
        findings.append(split_finding)

    return findings
