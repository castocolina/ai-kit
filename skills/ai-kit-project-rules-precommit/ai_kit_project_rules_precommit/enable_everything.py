"""Cross-ecosystem "enable-everything" uncurated-ruleset heuristic (ROADMAP
Phase 11 Success Criterion 3), plus D-C3's statically-unreadable-config
limitation finding.

D-C2: one table, `_ENABLE_EVERYTHING_TABLE`, one row per ecosystem carrying
its ordered config candidates (D-C1: a fixed, bounded discovery order --
never a search for a shape), its marker predicate, and the design spec's
own citation. A fifth ecosystem is a row, not a branch. An ecosystem whose
config is absent produces nothing -- flagging a Python repo for having no
Go linter configuration would make this check useless on every real repo.

Every reader this module calls is one of `config_read.py`'s degrade-not-
crash functions: a malformed, truncated, or wrong-typed config makes the
matching ecosystem's marker predicate return `False` (no finding), never
raise (T-11-13).
"""

from __future__ import annotations

import os
import re

from ai_kit_rules_common.criticality import CRITICALITY_ADVISORY, CRITICALITY_HIGH

from . import config_read

# The design spec's own reason (design.md's precommit-component ruleset
# bullet), quoted so every finding's recommendation carries it verbatim
# rather than a paraphrase.
_EVERYTHING_REASON = (
    "every researched ecosystem's own docs independently discourage this "
    "pattern in favor of a maintained preset plus explicit, reviewed "
    "extension"
)


def _identity_reader(path: str) -> str:
    """A `first_existing_candidate` reader that defers parsing to the
    marker predicate itself -- used where an ecosystem's candidates span
    more than one format (Go) and there is no single generic
    whole-document parse to hand back (a YAML candidate cannot support
    one under this module's degrade-not-crash contract)."""
    return path


def _ruff_selection(repo_root: str, matched_path: str) -> list | None:
    abs_path = os.path.join(repo_root, matched_path)
    parsed = config_read.read_toml(abs_path)
    if parsed is config_read.NOT_READABLE or not isinstance(parsed, dict):
        return None
    if matched_path == "pyproject.toml":
        tool = parsed.get("tool")
        ruff = tool.get("ruff") if isinstance(tool, dict) else None
        lint = ruff.get("lint") if isinstance(ruff, dict) else None
    else:
        lint = parsed.get("lint")
        if not isinstance(lint, dict):
            # A dedicated ruff.toml/.ruff.toml may also declare `select`
            # at its own top level, with no `[lint]` table.
            lint = parsed
    if not isinstance(lint, dict):
        return None
    select = lint.get("select")
    return select if isinstance(select, list) else None


def _ruff_marker(repo_root: str, matched_path: str) -> bool:
    select = _ruff_selection(repo_root, matched_path)
    return select is not None and "ALL" in select


def _go_marker(repo_root: str, matched_path: str) -> bool:
    abs_path = os.path.join(repo_root, matched_path)
    value = config_read.read_config_value(abs_path, ("linters", "enable-all"))
    if value is config_read.NOT_READABLE:
        return False
    return str(value).strip().lower() == "true"


def _node_marker(repo_root: str, matched_path: str) -> bool:
    abs_path = os.path.join(repo_root, matched_path)
    parsed = config_read.read_json(abs_path)
    if parsed is config_read.NOT_READABLE or not isinstance(parsed, dict):
        return False
    extends = parsed.get("extends")
    if isinstance(extends, str):
        entries = [extends]
    elif isinstance(extends, list):
        entries = extends
    else:
        entries = []
    for entry in entries:
        if not isinstance(entry, str):
            continue
        segment = entry.rsplit(":", 1)[-1].strip().lower()
        if segment == "all":
            return True
    return False


# D-C1's Java row: a NAMED, BOUNDED candidate list -- `pmd.xml` and
# `ruleset.xml` at the repo root, then `rulesets/*.xml` one directory deep
# (a plain, non-recursive `os.listdir`, never a walk), then a ruleset path
# named inside the project's Maven build file if one is present. Never a
# search for anything XML-shaped anywhere in the tree -- that would be a
# smaller instance of T-11-15's own threat.
_POM_RULESET_RE = re.compile(r"<ruleset>\s*([^<\s][^<]*?)\s*</ruleset>")


def _discover_pmd_ruleset(repo_root: str) -> str | None:
    for name in ("pmd.xml", "ruleset.xml"):
        if os.path.isfile(os.path.join(repo_root, name)):
            return name

    rulesets_dir = os.path.join(repo_root, "rulesets")
    if os.path.isdir(rulesets_dir):
        try:
            entries = sorted(e for e in os.listdir(rulesets_dir) if e.endswith(".xml"))
        except OSError:
            entries = []
        for entry in entries:
            rel = os.path.join("rulesets", entry)
            if os.path.isfile(os.path.join(repo_root, rel)):
                return rel

    pom_path = os.path.join(repo_root, "pom.xml")
    if os.path.isfile(pom_path):
        try:
            with open(pom_path, encoding="utf-8") as handle:
                pom_text = handle.read()
        except OSError:
            pom_text = ""
        match = _POM_RULESET_RE.search(pom_text)
        if match:
            rel = match.group(1).strip()
            if rel and os.path.isfile(os.path.join(repo_root, rel)):
                return rel

    return None


# The XML-shaped ruleset is scanned with a LINE REGEX, never an XML parser
# (T-11-14): the standard library's XML parsers expand entities from the
# document by default, a denial-of-service surface on untrusted input, and
# no finding in this skill is worth opening it.
_PMD_RULE_REF_RE = re.compile(r'<rule\s+ref="([^"]+)"')


def _java_marker(repo_root: str, matched_path: str) -> bool:
    abs_path = os.path.join(repo_root, matched_path)
    try:
        with open(abs_path, encoding="utf-8") as handle:
            text = handle.read()
    except OSError:
        return False
    for match in _PMD_RULE_REF_RE.finditer(text):
        ref = match.group(1).strip()
        if ref.lower().endswith(".xml"):
            return True
    return False


_ENABLE_EVERYTHING_TABLE = (
    {
        "ecosystem": "ruff",
        "candidates": ("pyproject.toml", "ruff.toml", ".ruff.toml"),
        "reader": config_read.read_toml,
        "marker": _ruff_marker,
        "marker_description": "lint.select contains the everything token 'ALL'",
        "reason": _EVERYTHING_REASON,
    },
    {
        "ecosystem": "go",
        "candidates": (".golangci.yml", ".golangci.yaml", ".golangci.toml", ".golangci.json"),
        "reader": _identity_reader,
        "marker": _go_marker,
        "marker_description": "linters.enable-all is true",
        "reason": _EVERYTHING_REASON,
    },
    {
        "ecosystem": "node",
        "candidates": (".eslintrc.json",),
        "reader": config_read.read_json,
        "marker": _node_marker,
        "marker_description": "extends names a preset ending in the everything segment 'all'",
        "reason": _EVERYTHING_REASON,
    },
    {
        "ecosystem": "java",
        "candidates": (),  # discovered dynamically via _discover_pmd_ruleset
        "reader": _identity_reader,
        "marker": _java_marker,
        "marker_description": (
            "a <rule ref=\"...\"/> references a whole category file rather than named rules"
        ),
        "reason": _EVERYTHING_REASON,
    },
)


def _match_config(repo_root: str, row: dict) -> str | None:
    if row["ecosystem"] == "java":
        return _discover_pmd_ruleset(repo_root)
    matched, _content = config_read.first_existing_candidate(
        repo_root, row["candidates"], row["reader"]
    )
    return matched


def build_enable_everything_findings(repo_root: str) -> list[dict]:
    """D-C2's loop over `_ENABLE_EVERYTHING_TABLE`: for each ecosystem
    whose config is found (D-C1) and whose marker predicate hits, emit one
    finding naming the ecosystem, the repo-relative config path, and the
    spec's own alternative. An ecosystem with no config present, or whose
    config exists but is not readable / does not match the marker,
    produces nothing."""
    findings = []
    for row in _ENABLE_EVERYTHING_TABLE:
        matched = _match_config(repo_root, row)
        if matched is None:
            continue
        if not row["marker"](repo_root, matched):
            continue
        recommendation = (
            f"{row['ecosystem']} configuration at '{matched}' selects an "
            f"enable-everything ruleset ({row['marker_description']}) -- "
            f"{row['reason']}; use a maintained preset plus explicit, "
            "reviewed extension instead"
        )
        findings.append(
            {
                "category": "enable-everything",
                "issue": "uncurated_ruleset",
                "ecosystem": row["ecosystem"],
                "config_path": matched,
                "marker": row["marker_description"],
                "recommendation": recommendation,
                "needs_research": False,
                "criticality": CRITICALITY_HIGH,
                "summary": recommendation,
            }
        )
    return findings


# D-C3: the statically-unreadable-config limitation. The JavaScript-module
# form of the ESLint flat configuration cannot be read statically with the
# standard library -- it is a program, not data -- and guessing at its
# contents by regex would be exactly the false certainty PROJECT.md
# forbids. The design spec's own convention is the precedent: an open gap
# is explicitly flagged, never silently dropped, because a silent skip
# reads to a user exactly like a clean result.
_ESLINT_FLAT_JS_CANDIDATES = ("eslint.config.js", "eslint.config.mjs", "eslint.config.cjs")
_ESLINT_JSON_CANDIDATES = (".eslintrc.json",)


def build_check_limitation_findings(repo_root: str) -> list[dict]:
    """Emit the advisory limitation finding when a JavaScript-module
    ESLint flat config is present and no statically-readable ESLint
    configuration is -- naming the file and saying what could not be
    checked and why. Produces nothing when no JS-module config is
    present, or when a JSON-form config is present alongside it (the
    normal check already covers that file)."""
    js_flat_path, _content = config_read.first_existing_candidate(
        repo_root, _ESLINT_FLAT_JS_CANDIDATES, _identity_reader
    )
    if js_flat_path is None:
        return []
    json_path, _content = config_read.first_existing_candidate(
        repo_root, _ESLINT_JSON_CANDIDATES, _identity_reader
    )
    if json_path is not None:
        return []
    summary = (
        f"'{js_flat_path}' is a JavaScript-module ESLint flat configuration -- "
        "it is a program, not data, and this skill reads configuration "
        "statically only, so the enable-everything check could not be "
        "applied to it"
    )
    return [
        {
            "category": "check-limitation",
            "issue": "config_not_statically_readable",
            "config_path": js_flat_path,
            "recommendation": (
                f"review '{js_flat_path}' by hand for an enable-everything "
                "preset -- this skill cannot statically read a JavaScript-"
                "module ESLint configuration"
            ),
            "needs_research": False,
            "advisory": True,
            "criticality": CRITICALITY_ADVISORY,
            "summary": summary,
        }
    ]


__all__ = [
    "build_check_limitation_findings",
    "build_enable_everything_findings",
]
