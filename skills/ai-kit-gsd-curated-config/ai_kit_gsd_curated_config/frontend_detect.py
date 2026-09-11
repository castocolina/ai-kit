"""Frontend-stack presence detection (07-CONTEXT.md D-08, Claude's Discretion) -- decides the
boolean `workflow.ui_phase`/`workflow.ui_review` get written with. A concrete, testable
heuristic: a `package.json` dependency-manifest scan (exact key match against a fixed
framework-package set) OR a bounded, word-boundary `README.md` text scan. Never raises on
missing/malformed input -- a directory with neither file, or a `package.json` that fails to
parse, degrades to "no signal" for that branch, never an exception the caller has to catch.

Mirrors `gsd_catalog.py`'s/`claude_md_detect.py`'s `isfile_fn=os.path.isfile` DI convention, plus
a `read_fn` injection point so tests can supply canned fixture text instead of real files.
"""
import json
import os
import re

# Exact dependency-manifest keys (checked for membership in `dependencies`/`devDependencies`,
# never a substring match against a key) that signal a frontend framework is in use.
_PACKAGE_JSON_DEPENDENCY_HINTS = ("react", "vue", "svelte", "next", "@angular/core", "solid-js")

# README.md text hints -- each one is wrapped in `re.escape(...)` before being placed inside
# `\b...\b` word-boundary markers (ALWAYS, for every hint, not just "next.js" -- fixes cross-AI
# review Cycle 2 LOW: an unescaped literal `.` in "next.js" acts as a regex wildcard, letting a
# string like "nextzjs" false-positive). Lowercase literals -- matched against the README text
# after it has also been lowercased, for a case-insensitive comparison.
_README_FRAMEWORK_HINTS = ("react", "vue", "svelte", "angular", "next.js")


def _read_text(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def _hint_matches(hint, lowered_text):
    """Delimiter-bounded match: `hint` must not be embedded inside a larger alphanumeric run
    (e.g. "react" must not fire on "reactive"), and every character in `hint` -- including a
    literal `.` -- is treated literally, never as a regex metacharacter."""
    return re.search(rf"\b{re.escape(hint)}\b", lowered_text) is not None


def _package_json_signals_frontend(project_dir, isfile_fn, read_fn):
    package_json_path = os.path.join(project_dir, "package.json")
    if not isfile_fn(package_json_path):
        return False
    try:
        manifest = json.loads(read_fn(package_json_path))
    except (json.JSONDecodeError, OSError):
        return False
    if not isinstance(manifest, dict):
        return False
    deps = {}
    deps.update(manifest.get("dependencies") or {})
    deps.update(manifest.get("devDependencies") or {})
    return any(hint in deps for hint in _PACKAGE_JSON_DEPENDENCY_HINTS)


def _readme_signals_frontend(project_dir, isfile_fn, read_fn):
    readme_path = os.path.join(project_dir, "README.md")
    if not isfile_fn(readme_path):
        return False
    try:
        text = read_fn(readme_path)
    except OSError:
        return False
    lowered = text.lower()
    return any(_hint_matches(hint, lowered) for hint in _README_FRAMEWORK_HINTS)


def detect_frontend_present(project_dir, isfile_fn=os.path.isfile, read_fn=_read_text):
    """Returns `True` when `package.json` exists under `project_dir` AND its
    `dependencies`/`devDependencies` contain any of `_PACKAGE_JSON_DEPENDENCY_HINTS`, OR when a
    `README.md` exists and its text contains a case-insensitive, word-boundary match for any of
    `_README_FRAMEWORK_HINTS`. Returns `False` when neither file exists, neither contains a
    match, or `package.json` exists but is malformed JSON -- a malformed manifest never
    short-circuits the independent README check. Never raises."""
    if _package_json_signals_frontend(project_dir, isfile_fn, read_fn):
        return True
    return _readme_signals_frontend(project_dir, isfile_fn, read_fn)
