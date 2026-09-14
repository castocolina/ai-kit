"""The three ruff-specific checks ROADMAP Phase 11 Success Criterion 5
names: annotation rules mistaken for type-checking (D-C4), preview rules
without a pinned version (D-C5), and a child ruff config that discards its
parent's ignore list (D-C6).

D-C1's ruff discovery order (the project metadata file's ruff table, then
a dedicated ruff config file in either of its two conventional names) is
this module's own -- the SAME candidate order `enable_everything.py`'s
ruff row already uses, re-derived locally rather than reaching into that
module's internals, so each check module owns its own read path over the
one shared `config_read.py` reader layer.
"""

from __future__ import annotations

import os
import re

from ai_kit_rules_common.criticality import CRITICALITY_HIGH, CRITICALITY_MEDIUM
from ai_kit_rules_common.makefile_parse import (
    parse_makefile_prerequisites,
    parse_makefile_recipe,
    parse_makefile_targets,
)
from ai_kit_rules_common.tool_catalog import resolve_tool_category

from . import config_read
from .parity_checker import classify_target_shape
from .taxonomy_checker import classify_precommit_tools

_RUFF_CANDIDATES = ("pyproject.toml", "ruff.toml", ".ruff.toml")


def _locate_ruff_config(repo_root: str) -> tuple[str | None, object]:
    """D-C1's ruff discovery: the project metadata file's ruff table,
    then a dedicated ruff config file at the repo root in either of its
    two conventional names. Returns `(repo_relative_path, parsed_toml)`
    for the first candidate that exists, or `(None, config_read.NOT_READABLE)`."""
    return config_read.first_existing_candidate(
        repo_root, _RUFF_CANDIDATES, config_read.read_toml
    )


def _ruff_top_table(matched_path: str, parsed) -> dict | None:
    """The `[tool.ruff]` table for a `pyproject.toml` match, or a
    dedicated config's own top level -- the scope `preview` lives in."""
    if parsed is config_read.NOT_READABLE or not isinstance(parsed, dict):
        return None
    if matched_path == "pyproject.toml":
        tool = parsed.get("tool")
        ruff = tool.get("ruff") if isinstance(tool, dict) else None
        return ruff if isinstance(ruff, dict) else None
    return parsed


def _ruff_lint_table(matched_path: str, parsed) -> dict | None:
    """The `[tool.ruff.lint]` table for a `pyproject.toml` match, or a
    dedicated ruff config's `[lint]` table (falling back to its own top
    level, since a dedicated `ruff.toml`/`.ruff.toml` may declare
    `select` with no `[lint]` table at all)."""
    top = _ruff_top_table(matched_path, parsed)
    if top is None:
        return None
    lint = top.get("lint")
    if matched_path != "pyproject.toml" and not isinstance(lint, dict):
        lint = top
    return lint if isinstance(lint, dict) else None


# D-C4: annotation-presence and type-import rule families. Matched by
# PREFIX on each selected code -- never substring anywhere in the
# selection string, so a rule whose code merely contains these letters
# (e.g. a fabricated 'FANN001') is never mistaken for one of these two
# families.
_TYPE_SAFETY_RULE_FAMILY_PREFIXES = ("ANN", "TC")


def _select_has_type_safety_family(select) -> bool:
    if not isinstance(select, list):
        return False
    return any(
        isinstance(code, str)
        and any(code.startswith(prefix) for prefix in _TYPE_SAFETY_RULE_FAMILY_PREFIXES)
        for code in select
    )


def _has_type_checking_evidence(repo_root: str) -> bool:
    """D-C4: 'a real type-checker is present' is answered by plan 11-02's
    classifier -- never a private keyword list here. Two evidence
    sources: a classified hook, or a tool-shaped Makefile target that
    resolves into the type-checking category via the shared catalog
    (read-only reuse of `parity_checker.classify_target_shape`, the same
    predicate the parity check itself uses)."""
    classification = classify_precommit_tools(repo_root)
    if classification["taxonomy"].get("type-checking"):
        return True

    makefile_path = os.path.join(repo_root, "Makefile")
    for target in parse_makefile_targets(makefile_path):
        recipe_text = parse_makefile_recipe(makefile_path, target)
        prerequisites = parse_makefile_prerequisites(makefile_path, target)
        shape = classify_target_shape(target, recipe_text, prerequisites)
        if not shape["tool_shaped"]:
            continue
        if resolve_tool_category(shape["identity"]) == "type-checking":
            return True
    return False


def check_ruff_type_safety(repo_root: str) -> dict | None:
    """D-C4: fire when the ruff selection carries the annotation-presence
    or type-import rule families AND nothing resolves into the
    type-checking category. `None` when the ecosystem's config is absent,
    unreadable, does not carry the family, or a real type-checker is
    already present."""
    matched_path, parsed = _locate_ruff_config(repo_root)
    if matched_path is None:
        return None
    lint = _ruff_lint_table(matched_path, parsed)
    if lint is None:
        return None
    select = lint.get("select")
    if not _select_has_type_safety_family(select):
        return None
    if _has_type_checking_evidence(repo_root):
        return None

    recommendation = (
        f"ruff configuration at '{matched_path}' selects the annotation-"
        "presence/type-import rule families (ANN/TC), which check "
        "annotation presence/style, never type correctness -- add a real "
        "type-checker (mypy or pyright, per the shared catalog's Python "
        "baseline row) to close the gap"
    )
    return {
        "category": "ruff-type-safety",
        "issue": "annotation_rules_are_not_type_checking",
        "config_path": matched_path,
        "recommendation": recommendation,
        "needs_research": False,
        "criticality": CRITICALITY_HIGH,
        "summary": recommendation,
    }


# D-C5: three pin sources, any one sufficing.
_EXACT_RUFF_PIN_RE = re.compile(r"^ruff\s*==\s*\S+")


def _dependency_declares_exact_ruff_pin(repo_root: str) -> bool:
    pyproject_path = os.path.join(repo_root, "pyproject.toml")
    parsed = config_read.read_toml(pyproject_path)
    if parsed is config_read.NOT_READABLE or not isinstance(parsed, dict):
        return False
    candidates: list[str] = []
    project = parsed.get("project")
    if isinstance(project, dict):
        deps = project.get("dependencies")
        if isinstance(deps, list):
            candidates.extend(d for d in deps if isinstance(d, str))
        optional = project.get("optional-dependencies")
        if isinstance(optional, dict):
            for group in optional.values():
                if isinstance(group, list):
                    candidates.extend(d for d in group if isinstance(d, str))
    groups = parsed.get("dependency-groups")
    if isinstance(groups, dict):
        for group in groups.values():
            if isinstance(group, list):
                candidates.extend(d for d in group if isinstance(d, str))
    return any(_EXACT_RUFF_PIN_RE.match(entry.strip()) for entry in candidates)


# `repo:` sits ABOVE its hook's own `- id:` line, so the block-scoped hook
# iterator (`precommit_parse.iter_precommit_hook_blocks`) cannot see it --
# this scans the WHOLE pre-commit file text, split into per-repo blocks,
# rather than one hook's block (the off-by-one-block mistake that would
# silently make this check always fire).
_REPO_LINE_RE = re.compile(r"^\s*-\s*repo:\s*(\S+)\s*$", re.MULTILINE)
_REV_LINE_RE = re.compile(r"^\s*rev:\s*(\S+)\s*$", re.MULTILINE)


def _precommit_hook_repo_pins_ruff(repo_root: str) -> bool:
    path = os.path.join(repo_root, ".pre-commit-config.yaml")
    if not os.path.isfile(path):
        return False
    try:
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
    except OSError:
        return False
    repo_matches = list(_REPO_LINE_RE.finditer(text))
    for idx, match in enumerate(repo_matches):
        repo_url = match.group(1)
        if "ruff" not in repo_url.lower():
            continue
        start = match.start()
        end = repo_matches[idx + 1].start() if idx + 1 < len(repo_matches) else len(text)
        block = text[start:end]
        if _REV_LINE_RE.search(block):
            return True
    return False


_LOCKFILE_CANDIDATES = ("uv.lock", "poetry.lock")
_LOCKFILE_NAME_RE = re.compile(r'(?m)^name\s*=\s*"ruff"\s*$')


def _lockfile_names_ruff(repo_root: str) -> bool:
    for name in _LOCKFILE_CANDIDATES:
        path = os.path.join(repo_root, name)
        if not os.path.isfile(path):
            continue
        try:
            with open(path, encoding="utf-8") as handle:
                text = handle.read()
        except OSError:
            continue
        if _LOCKFILE_NAME_RE.search(text):
            return True
    return False


def _preview_has_pin(repo_root: str) -> bool:
    """D-C5: one function checking all three pin sources in turn -- an
    exact-equality specifier, a revision-pinned pre-commit hook repo, or a
    lockfile naming the tool. Any one suffices."""
    return (
        _dependency_declares_exact_ruff_pin(repo_root)
        or _precommit_hook_repo_pins_ruff(repo_root)
        or _lockfile_names_ruff(repo_root)
    )


def check_ruff_preview_without_pin(repo_root: str) -> dict | None:
    """D-C5: fire when the ruff configuration enables `preview` and none
    of the three accepted pins is present."""
    matched_path, parsed = _locate_ruff_config(repo_root)
    if matched_path is None:
        return None
    top = _ruff_top_table(matched_path, parsed)
    if not isinstance(top, dict):
        return None
    if top.get("preview") is not True:
        return None
    if _preview_has_pin(repo_root):
        return None

    recommendation = (
        f"ruff configuration at '{matched_path}' sets `preview = true` "
        "with no pinned ruff version -- preview rules are not covered by "
        "ruff's normal stability guarantee, so an unpinned version can "
        "change the gate under the repo without a config change; pin an "
        "exact ruff version, a revision on the ruff pre-commit hook repo, "
        "or via a lockfile"
    )
    return {
        "category": "ruff-preview",
        "issue": "preview_without_pinned_version",
        "config_path": matched_path,
        "recommendation": recommendation,
        "needs_research": False,
        "criticality": CRITICALITY_MEDIUM,
        "summary": recommendation,
    }


# D-C6: bounded, pruned child-config walk (T-11-15) -- delegated to
# `config_read.iter_non_root_files`, the shared discovery helper
# `config_read.py` gains for this task. Never a second, independently
# drifting walk with different limits.
_CHILD_RUFF_CONFIG_NAMES = ("ruff.toml", ".ruff.toml")


def _iter_child_ruff_configs(repo_root: str):
    """Repo-relative paths to every non-root `ruff.toml`/`.ruff.toml`."""
    return config_read.iter_non_root_files(repo_root, _CHILD_RUFF_CONFIG_NAMES)


def _child_discards_parent_ignore(repo_root: str, rel_path: str) -> bool:
    abs_path = os.path.join(repo_root, rel_path)
    parsed = config_read.read_toml(abs_path)
    if parsed is config_read.NOT_READABLE or not isinstance(parsed, dict):
        return False
    extends = parsed.get("extend")
    if not isinstance(extends, str) or not extends.strip():
        return False
    lint = parsed.get("lint")
    if not isinstance(lint, dict):
        return False
    select = lint.get("select")
    if not (isinstance(select, list) and select):
        return False
    ignore = lint.get("ignore")
    return not (isinstance(ignore, list) and ignore)


def check_ruff_child_config_discards_parent_ignore(repo_root: str) -> list[dict]:
    """D-C6: flag every non-root ruff config that extends a parent,
    declares its own rule selection, and does not itself declare the
    ignore list the parent declares. The claim that the parent's ignore
    list is thereby discarded is the design spec's own locked finding
    (11-CONTEXT D-03) -- stated as the reason, not re-derived."""
    findings = []
    for rel_path in sorted(_iter_child_ruff_configs(repo_root)):
        if not _child_discards_parent_ignore(repo_root, rel_path):
            continue
        recommendation = (
            f"'{rel_path}' extends a parent ruff config and declares its "
            "own `lint.select` without also declaring the parent's "
            "`lint.ignore` -- that selection silently discards the "
            "parent's ignore list (11-CONTEXT D-03); declare the same "
            "ignore list in the child, or omit `select` there"
        )
        findings.append(
            {
                "category": "ruff-config-inheritance",
                "issue": "child_select_discards_parent_ignore",
                "config_path": rel_path,
                "recommendation": recommendation,
                "needs_research": False,
                "criticality": CRITICALITY_HIGH,
                "summary": recommendation,
            }
        )
    return findings


def build_ruff_findings(repo_root: str) -> list[dict]:
    """All three ruff-specific checks, aggregated. `precommit_checker.py`
    appends this call to the aggregate."""
    findings: list[dict] = []
    type_safety = check_ruff_type_safety(repo_root)
    if type_safety is not None:
        findings.append(type_safety)
    preview = check_ruff_preview_without_pin(repo_root)
    if preview is not None:
        findings.append(preview)
    findings.extend(check_ruff_child_config_discards_parent_ignore(repo_root))
    return findings


__all__ = [
    "build_ruff_findings",
    "check_ruff_child_config_discards_parent_ignore",
    "check_ruff_preview_without_pin",
    "check_ruff_type_safety",
]
