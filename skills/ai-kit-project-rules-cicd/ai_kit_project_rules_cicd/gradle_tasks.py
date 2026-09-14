"""The Gradle task reuse surface (D-C19): a task name extracted from the
root build script's own declaration forms (Route 1), or a task
contributed by a small pinned plugin table whose plugin id is actually
present in that build script (Route 2). Both routes require real
evidence in the repo -- this module never invokes `gradle`, never parses
the `plugins {}` block, and never resolves a plugin.

Declaration-form extraction (Route 1) is TEXT/regex over the build
script, in the same stdlib-only spirit 14-CONTEXT D-02 inherits from
Phase 13's D-01: `task <name>`, `task("<name>")`,
`tasks.register("<name>")`, `tasks.register<Type>("<name>")`,
`tasks.named("<name>")`, and the Kotlin `val <name> by tasks.registering`
/ `by tasks.creating` forms.

Limits, stated here rather than discovered later:
  - ROOT build scripts only. A subproject's `build.gradle` and
    `settings.gradle`'s project list are not read.
  - No Gradle execution of any kind. `gradle tasks` is never run, so a
    task contributed by a plugin outside the pinned `PLUGIN_TASK_TABLE`
    is invisible to this reader.
  - The plugin-id evidence check is a plain containment test against the
    build-script TEXT, not a parse of the `plugins {}` block -- both
    `plugins { id "com.diffplug.spotless" }` and
    `apply plugin: "com.diffplug.spotless"` count, and a comment
    mentioning the plugin id counts too. This is an accepted
    over-admission: nobody comments out a plugin they never applied, so
    the recommendation is for a task the repo probably does have.
  - A declared task's (Route 1) identity is its NAME with no command
    body behind it. `is_tool_shaped_identity`'s Route 3 (name-equality)
    is therefore CLOSED to a Route-1 identity -- a declared task must be
    catalog-answerable, an out-of-taxonomy marker, or come through Route
    2's plugin table. Concretely: `tasks.register("jscpd")` covers a CI
    `jscpd .` line (the name IS the tool name, and the shared catalog
    answers it), while `tasks.register("jscpdReport")` covers NOTHING --
    the catalog cannot answer `jscpdReport`, and even if it could, this
    family's match rule (D-C5) never does substring matching or suffix
    stripping. This is a genuine, accepted gap: `<tool><Purpose>` task
    names are ordinary Gradle convention, and the alternative (stripping
    a suffix to recover the tool name) is the exact mechanism that would
    make a `ruff format` call match a `ruff` linter target elsewhere in
    this family.
"""

from __future__ import annotations

import os
import re

# D-C19: the generic lifecycle tasks are deliberately NOT reuse sources --
# each runs many tools, so recommending one as the replacement for a
# single tool's invocation is the aggregate mistake D-C18 and D-C3 both
# refuse. A named constant with this comment, not a silent omission.
LIFECYCLE_TASK_NAMES: frozenset[str] = frozenset({"check", "build", "test", "assemble"})

# Route 1 declaration forms, each its own pattern so no one shape can
# shadow another (`task <name>` requires whitespace right after `task`
# and therefore never matches `task("<name>")`, `tasks.register(...)`,
# or `tasks.named(...)`, all of which have a non-whitespace character
# immediately following the `task`/`tasks` token).
_TASK_BARE_RE = re.compile(r"(?<![-\w])task[ \t]+([A-Za-z_][A-Za-z0-9_]*)")
_TASK_CALL_RE = re.compile(r"(?<![-\w])task\([ \t]*[\"']([^\"']+)[\"'][ \t]*\)")
_TASKS_REGISTER_RE = re.compile(
    r"(?<![-\w])tasks\.register(?:<[^>]*>)?\([ \t]*[\"']([^\"']+)[\"']"
)
_TASKS_NAMED_RE = re.compile(r"(?<![-\w])tasks\.named\([ \t]*[\"']([^\"']+)[\"']")
_KOTLIN_BY_TASKS_RE = re.compile(
    r"(?<![-\w])val[ \t]+([A-Za-z_][A-Za-z0-9_]*)[ \t]+by[ \t]+tasks\.(?:registering|creating)(?![-\w])"
)

_DECLARATION_PATTERNS: tuple[re.Pattern[str], ...] = (
    _TASK_BARE_RE,
    _TASK_CALL_RE,
    _TASKS_REGISTER_RE,
    _TASKS_NAMED_RE,
    _KOTLIN_BY_TASKS_RE,
)


def extract_declared_task_names(build_script_text: str) -> list[str]:
    """Route 1 (D-C19): every task name declared via any of the forms
    above, in extraction order, duplicates included -- the caller
    dedupes. Text/regex extraction only; this function never evaluates
    the build script. Never raises for any string input."""
    names: list[str] = []
    for pattern in _DECLARATION_PATTERNS:
        for match in pattern.finditer(build_script_text):
            names.append(match.group(1))
    return names


# Route 2 (D-C19): the pinned plugin table. Each row is
# `(task_name, plugin_id_fragment, tool_identity)`. Seeded with the rows
# a Java/Kotlin repo in this family's taxonomy really has, verified live
# 2026-09-14 against the shared catalog (see this plan's SUMMARY for the
# Gradle documentation source and date for each plugin's real id).
PLUGIN_TASK_TABLE: tuple[tuple[str, str, str], ...] = (
    ("spotlessCheck", "com.diffplug.spotless", "spotless"),
    ("spotlessApply", "com.diffplug.spotless", "spotless"),
    ("checkstyleMain", "checkstyle", "checkstyle"),
    ("pmdMain", "pmd", "PMD"),
    ("spotbugsMain", "spotbugs", "SpotBugs"),
    ("detekt", "io.gitlab.arturbosch.detekt", "detekt"),
    ("ktlintCheck", "org.jlleitschuh.gradle.ktlint", "ktlint"),
    ("dependencyCheckAnalyze", "org.owasp.dependencycheck", "dependency-check"),
)


def plugin_table_matches(build_script_text: str) -> list[tuple[str, str]]:
    """Route 2 (D-C19): `(task_name, tool_identity)` for every
    `PLUGIN_TASK_TABLE` row whose plugin-id fragment is present ANYWHERE
    in `build_script_text` -- a plain containment test, not a parse of
    the `plugins {}` block (see module docstring for the accepted
    over-admission this implies). Without this evidence requirement, this
    module would tell a plain Java repo to call `spotlessCheck`, a task
    that repo does not have. Never raises."""
    return [
        (task_name, tool_identity)
        for task_name, plugin_fragment, tool_identity in PLUGIN_TASK_TABLE
        if plugin_fragment in build_script_text
    ]


_BUILD_SCRIPT_FILENAMES: tuple[str, ...] = ("build.gradle", "build.gradle.kts")


def read_gradle_build_scripts(repo_root: str) -> str:
    """Root `build.gradle` and `build.gradle.kts`, concatenated when both
    exist -- Groovy and Kotlin DSL are two spellings of the same
    information, and reading only one would silently halve coverage. A
    missing file contributes nothing; an unreadable-binary file
    contributes nothing (wrapped in `(OSError, UnicodeDecodeError)`); a
    syntactically-broken-but-readable file contributes its raw text,
    which downstream regex extraction simply fails to match against --
    never a parse, never a raise. Subprojects and `settings.gradle`'s
    project list are not read (a stated limit)."""
    parts: list[str] = []
    for filename in _BUILD_SCRIPT_FILENAMES:
        path = os.path.join(repo_root, filename)
        try:
            with open(path, encoding="utf-8") as handle:
                parts.append(handle.read())
        except (OSError, UnicodeDecodeError):
            continue
    return "\n".join(parts)


def resolve_gradle_invocation(repo_root: str, task_name: str) -> str:
    """D-C20: `./gradlew <task_name>` when a root `gradlew` file exists,
    `gradle <task_name>` otherwise -- the wrapper is what a CI job can
    run without a preinstalled Gradle. Never raises."""
    if os.path.isfile(os.path.join(repo_root, "gradlew")):
        return f"./gradlew {task_name}"
    return f"gradle {task_name}"


__all__ = [
    "LIFECYCLE_TASK_NAMES",
    "PLUGIN_TASK_TABLE",
    "extract_declared_task_names",
    "plugin_table_matches",
    "read_gradle_build_scripts",
    "resolve_gradle_invocation",
]
