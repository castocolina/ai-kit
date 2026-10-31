#!/usr/bin/env python3
"""E2E command detection for the goal-prompt skill: Makefile, package.json and browser configs.

stdlib only, read-only, no subprocess. Nothing in the scanned project is executed: every command
is a fixed template plus a target or script NAME that passes a safe-name check (T-27-09).
Gate commands (the unit and lint checks that run before e2e) come back as `gates`.
"""

from __future__ import annotations

import itertools
import os
import re
from typing import TypedDict

from gp_common import make_targets, package_runner, read_package_scripts


class E2EResult(TypedDict):
    commands: list[dict[str, str]]
    gates: list[str]
    none: bool


E2E_TARGET_RE = re.compile(r"e2e(?:[-_.].*)?")
SAFE_NAME_RE = re.compile(r"[A-Za-z0-9_.:/@-]+")
BROWSER_RE = re.compile(r"\b(playwright|cypress)\b")
GATE_TARGETS = ("test", "lint", "validate", "test-unit")
PACKAGE_GATES = ("test", "lint")
PKG_PREFIX = {"npm": "npm run", "pnpm": "pnpm run", "yarn": "yarn run", "bun": "bun run"}
BROWSER_CMD = {
    "npm": {"playwright": "npx playwright test", "cypress": "npx cypress run"},
    "pnpm": {"playwright": "pnpm exec playwright test", "cypress": "pnpm exec cypress run"},
    "yarn": {"playwright": "yarn playwright test", "cypress": "yarn cypress run"},
    "bun": {"playwright": "bunx playwright test", "cypress": "bunx cypress run"},
}
PTY_PY_RE = re.compile(
    r"\s*(?:import\s+(?:pty|pexpect|ptyprocess)\b|from\s+(?:pty|pexpect|ptyprocess)\s+import\b)"
)
PTY_JS_RE = re.compile(r"""\s*(?:import\b|(?:const|let|var)\b).*['"]node-pty['"]""")
TEXTUAL_PILOT_RE = re.compile(r"\s*(?:from\s+textual\.pilot\s+import\b|import\s+textual\.pilot\b)")
SAFE_PATH_RE = re.compile(r"[A-Za-z0-9_./-]+")
SCAN_SUFFIXES = (".py", ".js", ".mjs", ".ts")
SCAN_MAX_BYTES = 200 * 1024
SCAN_MAX_LINES = 80
SKIP_DIRS = frozenset({"node_modules", ".git"})
# Unverified runners stay verified False: the count rule is not confirmed here (27-RESEARCH Q6).
# The shell harness has no exit-code rule in the table; its count line is the marker.
ZERO_TEST_MARKERS: tuple[dict[str, object], ...] = (
    {"runner": "unittest", "exit_code": 5, "marker": "NO TESTS RAN", "verified": True},
    {"runner": "node --test", "exit_code": 0, "marker": "tests 0", "verified": True},
    {"runner": "go test", "exit_code": 0, "marker": "[no test files]", "verified": True},
    {"runner": "shell harness", "exit_code": None, "marker": "0 passed", "verified": True},
    {"runner": "pytest", "exit_code": 5, "marker": "no tests ran", "verified": False},
    {"runner": "jest", "exit_code": 1, "marker": "No tests found", "verified": False},
    {"runner": "vitest", "exit_code": 1, "marker": "No test files found", "verified": False},
    {"runner": "playwright", "exit_code": 1, "marker": "No tests found", "verified": False},
    {"runner": "cypress", "exit_code": None, "marker": None, "verified": False},
    {"runner": "cargo", "exit_code": 0, "marker": "running 0 tests", "verified": False},
)
_MARKER_PATTERNS: tuple[tuple[str, str], ...] = (
    ("unittest", r"\bunittest\b"),
    ("node --test", r"\bnode\s+--test\b"),
    ("go test", r"\bgo\s+test\b"),
    ("shell harness", r"test_install\.sh"),
    ("pytest", r"\bpytest\b"),
    ("jest", r"\bjest\b"),
    ("vitest", r"\bvitest\b"),
    ("playwright", r"\bplaywright\b"),
    ("cypress", r"\bcypress\b"),
    ("cargo", r"\bcargo\s+test\b"),
)


def _entry(command: str, source: str, kind: str, confidence: str) -> dict[str, str]:
    return {"command": command, "source": source, "kind": kind, "confidence": confidence}


def _read(path: str) -> str:
    try:
        with open(path, encoding="utf-8") as handle:
            return handle.read()
    except (OSError, UnicodeDecodeError):
        return ""


def _make_signals(targets: list[str]) -> list[dict[str, str]]:
    """Every `e2e`, `e2e-*`, `e2e_*` and `e2e.*` target, in declaration order (none dropped)."""
    return [
        _entry(f"make {name}", f"Makefile:{name}", "make", "detected")
        for name in targets
        if E2E_TARGET_RE.fullmatch(name)
    ]


def _is_e2e_script(name: str) -> bool:
    return name == "e2e" or name.startswith("e2e:") or name.endswith(":e2e")


def _package_signals(
    scripts: list[tuple[str, str]], runner: str
) -> tuple[list[dict[str, str]], set[str]]:
    """Scripts named e2e, e2e:*, *:e2e, or whose body runs a browser runner; also the browsers seen.

    The body is read for matching only and never copied into a command.
    """
    commands: list[dict[str, str]] = []
    browsers: set[str] = set()
    for name, body in scripts:
        if not SAFE_NAME_RE.fullmatch(name):
            continue
        found = set(BROWSER_RE.findall(body))
        browsers |= found
        if found or _is_e2e_script(name):
            command = f"{PKG_PREFIX[runner]} {name}"
            commands.append(_entry(command, f"package.json:{name}", "package", "detected"))
    return commands, browsers


def _has_config(repo: str, browser: str) -> bool:
    try:
        names = os.listdir(repo)
    except OSError:
        return False
    return any(
        name.startswith(f"{browser}.config.") and os.path.isfile(os.path.join(repo, name))
        for name in names
    )


def _config_signals(repo: str, runner: str, browsers: set[str]) -> list[dict[str, str]]:
    """A browser config adds a command only when no package script already runs that browser."""
    found: list[dict[str, str]] = []
    for browser in ("playwright", "cypress"):
        if browser not in browsers and _has_config(repo, browser):
            command = BROWSER_CMD[runner][browser]
            found.append(_entry(command, f"{browser}.config.*", browser, "detected"))
    return found


def _gate_signals(targets: list[str], script_names: set[str], runner: str) -> list[str]:
    """Makefile gate targets in a fixed order; package `test`/`lint` only when there are none."""
    gates = [f"make {name}" for name in GATE_TARGETS if name in targets]
    if not gates:
        gates = [f"{PKG_PREFIX[runner]} {name}" for name in PACKAGE_GATES if name in script_names]
    return gates


def _head(path: str) -> list[str] | None:
    """The first SCAN_MAX_LINES lines of a file no larger than SCAN_MAX_BYTES, or None."""
    try:
        if os.path.getsize(path) > SCAN_MAX_BYTES:
            return None
        with open(path, encoding="utf-8", errors="replace") as handle:
            return list(itertools.islice(handle, SCAN_MAX_LINES))
    except OSError:
        return None


def _scan_tests(repo: str) -> list[tuple[str, list[str]]]:
    """(repo-relative path, head lines) for each scannable file under tests/, in sorted order."""
    found: list[tuple[str, list[str]]] = []
    for dirpath, dirnames, filenames in os.walk(os.path.join(repo, "tests")):
        dirnames[:] = sorted(name for name in dirnames if name not in SKIP_DIRS)
        for name in sorted(filenames):
            path = os.path.join(dirpath, name)
            if not name.endswith(SCAN_SUFFIXES) or os.path.islink(path):
                continue
            head = _head(path)
            if head is not None:
                rel = os.path.relpath(path, repo).replace(os.sep, "/")
                found.append((rel, head))
    return found


def _driver_lang(rel: str, head: list[str]) -> str | None:
    """`py` for a Python PTY driver, `node` for a node-pty one, None otherwise (pilot excluded)."""
    if any(TEXTUAL_PILOT_RE.match(line) for line in head):
        return None
    if rel.endswith(".py"):
        return "py" if any(PTY_PY_RE.match(line) for line in head) else None
    return "node" if any(PTY_JS_RE.match(line) for line in head) else None


def _drivers(repo: str) -> list[tuple[str, str]]:
    """(path, lang) for each PTY driver under tests/; a path with unsafe characters is skipped."""
    drivers: list[tuple[str, str]] = []
    for rel, head in _scan_tests(repo):
        lang = _driver_lang(rel, head)
        if lang and SAFE_PATH_RE.fullmatch(rel):
            drivers.append((rel, lang))
    return drivers


def _recipe(text: str, target: str) -> str:
    """The indented lines under `target:`, up to the next unindented non-blank line."""
    header = re.compile(rf"{re.escape(target)}\s*:(?!=)")
    body: list[str] = []
    inside = False
    for line in text.splitlines():
        if not inside:
            inside = header.match(line) is not None
        elif line[:1] in ("\t", " "):
            body.append(line)
        elif line.strip():
            break
    return "\n".join(body)


def _tokens(rel: str, lang: str) -> tuple[str, ...]:
    """The ways a recipe can name a driver: its path, its dotted module (py only), its basename."""
    base = rel.rsplit("/", 1)[-1]
    if lang == "py":
        return (rel, rel[:-3].replace("/", "."), base)
    return (rel, base)


def _mentions(recipe: str, token: str) -> bool:
    return re.search(rf"(?<![\w./-]){re.escape(token)}(?![\w-])", recipe) is not None


def _owner(
    make_text: str, make_entries: list[dict[str, str]], tokens: tuple[str, ...]
) -> dict[str, str] | None:
    """The first e2e Makefile entry whose recipe names one of the driver's tokens."""
    for entry in make_entries:
        recipe = _recipe(make_text, entry["source"].removeprefix("Makefile:"))
        if any(_mentions(recipe, token) for token in tokens):
            return entry
    return None


def _driver_command(rel: str, lang: str) -> str:
    if lang == "py":
        module = rel[:-3].replace("/", ".")
        return f"python3 -m unittest {module}"
    return f"node {rel}"


def _pty_signals(
    make_text: str, commands: list[dict[str, str]], drivers: list[tuple[str, str]]
) -> list[dict[str, str]]:
    """A driver named by an e2e recipe gains a `driver` key; any other driver is `inferred`.

    When several drivers name one target, the first stays in `driver`; the others are still
    mapped (no duplicate entry is added).
    """
    make_entries = [entry for entry in commands if entry["kind"] == "make"]
    inferred: list[dict[str, str]] = []
    for rel, lang in drivers:
        owner = _owner(make_text, make_entries, _tokens(rel, lang))
        if owner is not None:
            owner.setdefault("driver", rel)
        else:
            inferred.append(_entry(_driver_command(rel, lang), f"PTY driver {rel}", "pty",
                                   "inferred"))
    return inferred


def markers_for_text(command: str) -> list[dict[str, object]]:
    """Marker rows whose runner appears in a command string; an unrelated command gives []."""
    hits = {runner for runner, pattern in _MARKER_PATTERNS if re.search(pattern, command)}
    return [row for row in ZERO_TEST_MARKERS if row["runner"] in hits]


def detect_e2e(repo: str) -> E2EResult:
    """Commands that run e2e checks, the gate commands, and `none` when no e2e signal exists."""
    make_text = _read(os.path.join(repo, "Makefile"))
    targets = make_targets(make_text)
    scripts = read_package_scripts(repo)
    runner = package_runner(repo)
    pkg_commands, browsers = _package_signals(scripts, runner)
    commands = [
        *_make_signals(targets),
        *pkg_commands,
        *_config_signals(repo, runner, browsers),
    ]
    commands += _pty_signals(make_text, commands, _drivers(repo))
    gates = _gate_signals(targets, {name for name, _ in scripts}, runner)
    return {"commands": commands, "gates": gates, "none": not commands}


__all__ = ["ZERO_TEST_MARKERS", "detect_e2e", "markers_for_text"]
