"""Shared 6-category tooling taxonomy vocabulary for the ai-kit rules-checker
skill family (11-CONTEXT D-01).

Lives here rather than inside `ai-kit-project-rules-precommit` because D-01
converges per-language tool knowledge into ONE catalog so a correction
benefits every checker at once: Phases 12-15 classify their own findings
against these same six names, and a second, independently-maintained copy
inside any one skill would be exactly the split-ownership defect D-01
exists to prevent.

What this module carries TODAY: only the six category identifier strings
and their one-line definitions (transcribed from
`docs/superpowers/specs/2026-09-12-ai-kit-rules-skill-family-design.md`'s
Tooling Taxonomy table). What it deliberately does NOT carry yet, and which
plan adds it: plan 11-02 adds the baseline stack tables (which concrete
tool covers which category per language), the tool-name-to-category
reverse index, the category alias table reconciling these six names with
the sibling `ai-kit-project-rules-makefile` skill's five cache categories,
and the redundant-vs-complementary pairs table. Adding any of that here,
one plan early, would be the second independently-maintained dataset D-01
forbids -- landing content before the catalog module that is supposed to
own it.
"""

from __future__ import annotations

TAXONOMY_CATEGORIES = (
    "formatting",
    "type-checking",
    "linting",
    "security",
    "duplicate-code",
    "dead-code",
)

TAXONOMY_DEFINITIONS = {
    "formatting": (
        "Deterministic, opinionated code-shape rewriting. No semantic judgment."
    ),
    "type-checking": (
        "Static type/contract verification requiring a type system or annotations."
    ),
    "linting": (
        "Syntactic/semantic rule-based checks for bugs, anti-patterns, complexity."
    ),
    "security": (
        "Pattern/taint-based detection of exploitable vulnerability classes."
    ),
    "duplicate-code": "Clone/copy-paste detection via token or AST matching.",
    "dead-code": "Reachability/usage analysis for unused symbols, exports, files, deps.",
}

__all__ = [
    "TAXONOMY_CATEGORIES",
    "TAXONOMY_DEFINITIONS",
]
