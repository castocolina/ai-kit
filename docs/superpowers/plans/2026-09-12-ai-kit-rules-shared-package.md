# ai-kit Rules Shared Package Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extract the domain-agnostic rule-classification engine, tool-presence
detection, generic per-stack tooling cache, and remediation-ordering helper
out of `ai-kit-agents-md-rules-checker` into a new `skills/_shared/
ai_kit_rules_common/` package, with zero behavior change to the existing
skill's public CLI/test surface, so every future checker skill in the
family (makefile, precommit, arch, docker-compose, cicd, orchestrator) can
import the same infrastructure instead of duplicating it.

**Architecture:** Move each piece of genuinely domain-agnostic logic
verbatim (or lightly generalized — e.g. parameterizing a hardcoded rules
list into a function argument) into `skills/_shared/ai_kit_rules_common/`.
`ai-kit-agents-md-rules-checker`'s existing local modules become thin
delegators to the shared package, preserving every existing public name,
signature, and default so the skill's current 60+ tests keep passing
unmodified as a regression guard. The shared package is reached via a
`sys.path` insert computed from `os.path.realpath(__file__)` in the
consuming skill's `__init__.py` — never a hardcoded path.

This only resolves correctly for ONE of `SKILL.md`'s five candidate
install locations (`skills/ai-kit-agents-md-rules-checker/SKILL.md:17-22`):
`tools/setup.py`'s `link_one` (`tools/setup.py:1030`) symlinks into
`claude_dir` (`$CLAUDE_CONFIG_DIR` or `$HOME/.claude`) only — confirmed by
`rg` finding no `opencode`, `.agents`, or `CLAUDE_PLUGIN_ROOT` linking
anywhere in `tools/setup.py`. A direct checkout (the fifth candidate) also
resolves correctly, since `skills/_shared/` is a sibling directory right
there. For the other three candidates (a Claude Code plugin root, an
opencode install, or an `~/.agents` install), there is no guarantee
`skills/_shared/` exists beside the installed skill at all — those
installers are out of this plan's scope to fix. Task 5 therefore makes the
`sys.path` bootstrap fail LOUDLY and LEGIBLY instead of producing a bare
`ModuleNotFoundError`: if `skills/_shared/ai_kit_rules_common` is not
found relative to the installed skill, `__init__.py` raises an
`ImportError` naming the missing path and pointing at the two install
paths that do carry it (the `~/.claude/skills` symlink install, or a
direct checkout) — so the failure is diagnosable, even though it is not
fixed for every host in this plan.

**Tech Stack:** Python 3.12 stdlib only (no third-party imports — matches
every other skill package in this repo), `unittest` for tests.

**Spec:** `docs/superpowers/specs/2026-09-12-ai-kit-rules-skill-family-design.md`

## Global Constraints

- Every module in `skills/_shared/ai_kit_rules_common/` stays stdlib-only —
  no third-party imports (matches the rest of this repo's skill packages).
- The shared package is reached via a `sys.path` insert computed from
  `os.path.realpath(__file__)`, never a hardcoded `~/.claude/...` path.
- `ai_kit_rules_common.stack_cache`'s cache functions take `cache_root` as
  an explicit parameter with NO module-global mutable default — each
  consuming skill computes and owns its own default via
  `default_cache_root(namespace)`.
- This plan makes ZERO behavior change to `ai-kit-agents-md-rules-checker`'s
  existing public CLI output or test assertions. This constraint is scoped
  to Task 5 (the delegation migration): every existing test in
  `tests/test_ai_kit_agents_md_rules_checker.py` as it exists BEFORE this
  plan's Task 6 must pass unmodified after Task 5, proving the extraction
  itself is behavior-preserving. Task 6 Step 4 is an explicit, additive
  exception to this constraint — it appends new `TestGateRegistration`
  assertions (asserting the new gate wiring exists) to that same file; it
  never deletes or edits an existing assertion, and every assertion that
  predates this plan still passes unmodified. Four known deliberate
  deviations from the spec follow from the zero-behavior-change
  constraint (see Self-Review Notes for detail): the cache payload
  validation contract stays in `cli.py`, not `stack_cache.py`;
  `STALE_AFTER_DAYS` stays `30`, not the spec's `180`; the shared
  `remediation.py` helper performs cross-kind merging that the spec
  assigns to the orchestrator; and the shared package is not reachable
  from three of the five documented install hosts.
- Any new Python file this plan creates must be wired into ai-kit's own
  quality gates (Makefile `lint`/`test-unit`, `.pre-commit-config.yaml`
  `ruff`/`py-compile`/`unittest`, `pyproject.toml`'s `[tool.pyright]
  include` and `[tool.vulture] paths`) in this same plan — never shipped
  ungated.

---

### Task 1: Shared classification engine

**Files:**
- Create: `skills/_shared/ai_kit_rules_common/__init__.py`
- Create: `skills/_shared/ai_kit_rules_common/classification.py`
- Test: `tests/test_ai_kit_rules_common.py` (new file — this task creates it)

**Interfaces:**
- Consumes: nothing (first task).
- Produces: `ai_kit_rules_common.classification.CONDITION_ALWAYS: str` (`"always"`); `ai_kit_rules_common.classification.evaluate_condition(condition: str, tool_presence: dict) -> bool`; `ai_kit_rules_common.classification.check_rules(text: str, tool_presence: dict, rules: tuple[dict, ...], include_present: bool = False) -> list[dict]` — each rule dict must carry `id`/`criticality`/`condition`/`signals`/`summary` keys (this is exactly what `check_rules` reads; filtering is by non-empty `signals`, NOT by any `category` field — see Step 3's docstring). A rule dict MAY also carry a `category` key for the caller's own bookkeeping, matching the shape `ai-kit-agents-md-rules-checker/ai_kit_agents_md_rules_checker/rules.py` already uses, but `check_rules` never reads it. Later tasks in THIS plan (Task 5) bind this to that skill's real 17-rule `RULES` tuple; future skills (not in this plan) bind it to their own rules tuples.

- [ ] **Step 1: Write the failing test**

Create `tests/test_ai_kit_rules_common.py` with this content:

```python
import os
import sys
import unittest

sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "skills", "_shared"),
)

from ai_kit_rules_common.classification import check_rules, evaluate_condition

_RULES = (
    {
        "id": "X01",
        "category": "demo",
        "criticality": 1,
        "condition": "always",
        "signals": ("alpha", "beta", "gamma"),
        "summary": "demo flat rule",
    },
    {
        "id": "X02",
        "category": "demo",
        "criticality": 2,
        "condition": "tool-presence:widget",
        "signals": (("one", "uno"), ("two", "dos")),
        "summary": "demo grouped rule",
    },
    {
        "id": "X03",
        "category": "demo",
        "criticality": 3,
        "condition": "always",
        "signals": (("rg", ("rg", "ripgrep")), ("bat", ("bat", "batcat"))),
        "summary": "demo tool-scoped rule",
    },
)


class TestEvaluateCondition(unittest.TestCase):
    def test_always_is_true(self):
        self.assertTrue(evaluate_condition("always", {}))

    def test_tool_presence_looks_up_dict(self):
        self.assertTrue(evaluate_condition("tool-presence:widget", {"widget": True}))
        self.assertFalse(evaluate_condition("tool-presence:widget", {"widget": False}))
        self.assertFalse(evaluate_condition("tool-presence:widget", {}))

    def test_unknown_condition_shape_is_false(self):
        self.assertFalse(evaluate_condition("bogus", {}))


class TestCheckRulesFlat(unittest.TestCase):
    def test_no_signals_matched_is_missing(self):
        findings = check_rules("nothing relevant here", {}, _RULES, include_present=True)
        x01 = next(f for f in findings if f["id"] == "X01")
        self.assertEqual(x01["status"], "missing")
        self.assertEqual(x01["matched_signals"], [])

    def test_majority_of_three_signals_is_present(self):
        findings = check_rules("alpha and beta both appear", {}, _RULES, include_present=True)
        x01 = next(f for f in findings if f["id"] == "X01")
        self.assertEqual(x01["status"], "present")
        self.assertEqual(x01["matched_signals"], ["alpha", "beta"])

    def test_one_of_three_signals_is_near_miss(self):
        findings = check_rules("only alpha appears", {}, _RULES, include_present=True)
        x01 = next(f for f in findings if f["id"] == "X01")
        self.assertEqual(x01["status"], "near_miss")


class TestCheckRulesGroups(unittest.TestCase):
    def test_condition_not_met_is_not_applicable(self):
        findings = check_rules("one appears", {"widget": False}, _RULES, include_present=True)
        x02 = next(f for f in findings if f["id"] == "X02")
        self.assertEqual(x02["status"], "not_applicable")

    def test_one_group_satisfied_is_near_miss(self):
        findings = check_rules(
            "one appears but the second item does not",
            {"widget": True},
            _RULES,
            include_present=True,
        )
        x02 = next(f for f in findings if f["id"] == "X02")
        self.assertEqual(x02["status"], "near_miss")

    def test_all_groups_satisfied_is_present(self):
        findings = check_rules(
            "one and two both appear", {"widget": True}, _RULES, include_present=True
        )
        x02 = next(f for f in findings if f["id"] == "X02")
        self.assertEqual(x02["status"], "present")


class TestCheckRulesToolScoped(unittest.TestCase):
    def test_no_scoped_tool_present_is_not_applicable(self):
        findings = check_rules(
            "rg and bat both mentioned",
            {"modern-cli:rg": False, "modern-cli:bat": False},
            _RULES,
            include_present=True,
        )
        x03 = next(f for f in findings if f["id"] == "X03")
        self.assertEqual(x03["status"], "not_applicable")

    def test_only_present_tools_are_required(self):
        findings = check_rules(
            "rg is mentioned but not the other one",
            {"modern-cli:rg": True, "modern-cli:bat": False},
            _RULES,
            include_present=True,
        )
        x03 = next(f for f in findings if f["id"] == "X03")
        self.assertEqual(x03["status"], "present")
        self.assertEqual(x03["missing_tools"], [])


class TestCheckRulesIncludePresent(unittest.TestCase):
    def test_default_excludes_present_findings(self):
        findings = check_rules("alpha and beta both appear", {}, _RULES)
        ids = {f["id"] for f in findings}
        self.assertNotIn("X01", ids)

    def test_include_present_keeps_everything(self):
        findings = check_rules("alpha and beta both appear", {}, _RULES, include_present=True)
        ids = {f["id"] for f in findings}
        self.assertIn("X01", ids)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_ai_kit_rules_common -v`
Expected: `ModuleNotFoundError: No module named 'ai_kit_rules_common'`

- [ ] **Step 3: Write minimal implementation**

Create `skills/_shared/ai_kit_rules_common/__init__.py`:

```python
"""Domain-agnostic infrastructure shared across the ai-kit rules-checker
skill family (AGENTS.md/CLAUDE.md, Makefile, pre-commit, arch, Docker
Compose, CI/CD). Each consuming skill reaches this package via its own
`sys.path` insert computed from `os.path.realpath(__file__)` -- see any
consuming skill's `__init__.py` for the exact pattern. This package itself
has no opinion on any specific skill's rule content or cache namespace.
"""
```

Create `skills/_shared/ai_kit_rules_common/classification.py`:

```python
"""Generic rule-classification engine (moved from
`ai-kit-agents-md-rules-checker/ai_kit_agents_md_rules_checker/
rule_checker.py`, generalized to take a `rules` tuple as a parameter
instead of importing one fixed module's `RULES`).

A rule whose `condition` is not met in the caller's environment is
skipped/reframed as `"not_applicable"`, never flagged as a generic gap.
"""

from __future__ import annotations

import math

CONDITION_ALWAYS = "always"


def evaluate_condition(condition: str, tool_presence: dict) -> bool:
    if condition == CONDITION_ALWAYS:
        return True
    if condition.startswith("tool-presence:"):
        name = condition.split(":", 1)[1]
        return bool(tool_presence.get(name, False))
    return False


def _is_tool_scoped_groups(signals: tuple) -> bool:
    """True when `signals` is shaped as a tuple of `(tool_name, phrases)`.

    Distinguished from plain grouped signals (tuple of tuples-of-phrases,
    every element a plain string) by the presence of a nested tuple as the
    SECOND element of the first group.
    """
    group0 = signals[0]
    return (
        isinstance(group0, tuple)
        and len(group0) == 2
        and isinstance(group0[0], str)
        and isinstance(group0[1], tuple)
    )


def _classify_flat(text: str, signals: tuple) -> tuple[str, list[str]]:
    matched = sorted(p for p in signals if p in text)
    n_matched = len(matched)
    n_total = len(signals)
    if n_matched == 0:
        return "missing", matched
    if n_matched == n_total or (n_total >= 3 and n_matched >= math.ceil(n_total / 2)):
        return "present", matched
    return "near_miss", matched


def _classify_plain_groups(text: str, groups: tuple) -> tuple[str, list[str]]:
    matched: set[str] = set()
    satisfied = 0
    for group in groups:
        group_matches = [p for p in group if p in text]
        if group_matches:
            satisfied += 1
            matched.update(group_matches)
    if satisfied == 0:
        status = "missing"
    elif satisfied == len(groups):
        status = "present"
    else:
        status = "near_miss"
    return status, sorted(matched)


def _classify_tool_scoped_groups(
    text: str, groups: tuple, tool_presence: dict
) -> tuple[str, list[str], list[str]]:
    required = [
        (tool_name, phrases)
        for tool_name, phrases in groups
        if tool_presence.get(f"modern-cli:{tool_name}", False)
    ]
    if not required:
        return "not_applicable", [], []
    matched: set[str] = set()
    missing_tools: list[str] = []
    satisfied = 0
    for tool_name, phrases in required:
        group_matches = [p for p in phrases if p in text]
        if group_matches:
            satisfied += 1
            matched.update(group_matches)
        else:
            missing_tools.append(tool_name)
    if satisfied == 0:
        status = "missing"
    elif satisfied == len(required):
        status = "present"
    else:
        status = "near_miss"
    return status, sorted(matched), sorted(missing_tools)


def check_rules(
    text: str,
    tool_presence: dict,
    rules: tuple[dict, ...],
    include_present: bool = False,
) -> list[dict]:
    """Classify every rule in `rules` with a non-empty `signals` tuple.

    Filtered by "has non-empty signals", NOT by any `category` field --
    a caller's rule may carry a category label for its own bookkeeping
    while still having a signals-checkable prose clause.
    """
    lowered = (text or "").lower()
    findings: list[dict] = []
    for rule in rules:
        signals = rule["signals"]
        if not signals:
            continue
        if not evaluate_condition(rule["condition"], tool_presence):
            findings.append(
                {
                    "id": rule["id"],
                    "status": "not_applicable",
                    "reason": (
                        f"condition '{rule['condition']}' not met in this "
                        "environment"
                    ),
                    "matched_signals": [],
                    "criticality": rule["criticality"],
                    "summary": rule["summary"],
                }
            )
            continue

        missing_tools: list[str] | None = None
        if isinstance(signals[0], tuple):
            if _is_tool_scoped_groups(signals):
                status, matched, missing_tools = _classify_tool_scoped_groups(
                    lowered, signals, tool_presence
                )
            else:
                status, matched = _classify_plain_groups(lowered, signals)
        else:
            status, matched = _classify_flat(lowered, signals)

        finding = {
            "id": rule["id"],
            "status": status,
            "matched_signals": matched,
            "criticality": rule["criticality"],
            "summary": rule["summary"],
        }
        if missing_tools is not None:
            finding["missing_tools"] = missing_tools
        findings.append(finding)

    if include_present:
        return findings
    return [f for f in findings if f["status"] != "present"]


__all__ = [
    "CONDITION_ALWAYS",
    "check_rules",
    "evaluate_condition",
]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_ai_kit_rules_common -v`
Expected: all `TestEvaluateCondition`/`TestCheckRules*` tests PASS

- [ ] **Step 5: Commit**

```bash
git add skills/_shared/ai_kit_rules_common/__init__.py \
        skills/_shared/ai_kit_rules_common/classification.py \
        tests/test_ai_kit_rules_common.py
git commit -m "feat(rules-common): add shared rule-classification engine"
```

---

### Task 2: Shared tool-presence detection

**Files:**
- Create: `skills/_shared/ai_kit_rules_common/tool_presence.py`
- Test: `tests/test_ai_kit_rules_common.py` (insert `TestToolPresence` above the `__main__` guard)

**Interfaces:**
- Consumes: nothing from Task 1 (independent module).
- Produces: `ai_kit_rules_common.tool_presence.check_tool_presence(search_path: str | None = None, repo_root: str | None = None) -> dict[str, bool]`; `ai_kit_rules_common.tool_presence.MODERN_CLI_TOOLS: tuple[str, ...]`.

- [ ] **Step 1: Write the failing test**

Insert the following into `tests/test_ai_kit_rules_common.py` ABOVE the
`if __name__ == "__main__":` guard (do not append after it — classes
below that guard never run under `python3 tests/test_ai_kit_rules_common.py`):

```python
import tempfile

from ai_kit_rules_common.tool_presence import MODERN_CLI_TOOLS, check_tool_presence


class TestToolPresence(unittest.TestCase):
    def test_empty_path_and_repo_all_false(self):
        with tempfile.TemporaryDirectory() as repo:
            result = check_tool_presence(search_path="", repo_root=repo)
        self.assertFalse(result["rtk"])
        self.assertFalse(result["modern-cli"])
        self.assertFalse(result["codegraph"])
        self.assertFalse(result["graphify"])
        self.assertFalse(result["gsd"])
        for tool in MODERN_CLI_TOOLS:
            self.assertFalse(result[f"modern-cli:{tool}"])

    def test_codegraph_and_gsd_dirs_detected(self):
        with tempfile.TemporaryDirectory() as repo:
            os.makedirs(os.path.join(repo, ".codegraph"))
            os.makedirs(os.path.join(repo, ".planning"))
            result = check_tool_presence(search_path="", repo_root=repo)
        self.assertTrue(result["codegraph"])
        self.assertTrue(result["gsd"])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_ai_kit_rules_common.TestToolPresence -v`
Expected: `ModuleNotFoundError: No module named 'ai_kit_rules_common.tool_presence'`

- [ ] **Step 3: Write minimal implementation**

Create `skills/_shared/ai_kit_rules_common/tool_presence.py` (moved from
`ai-kit-agents-md-rules-checker/ai_kit_agents_md_rules_checker/
tool_presence.py` — already fully domain-agnostic, so every function body
is byte-identical to the existing file; only the module docstring is
rewritten to de-skill-specificize it, and a new `__all__` is added, since
the existing file has none):

```python
"""Live tool-presence detection: never assume, always verify.

Adapts `tools/hooks/detect.py`'s `shutil.which(name, path=search_path)`
resolution pattern locally (no `tools/`<->`skills/` cross-import). Every
binary is resolved through the `path=` parameter, never by mutating
`os.environ`, so tests stay hermetic on a scratch PATH.
"""

from __future__ import annotations

import os
import shutil

MODERN_CLI_TOOLS = ("rg", "bat", "sd", "fd", "eza")


def check_tool_presence(
    search_path: str | None = None, repo_root: str | None = None
) -> dict[str, bool]:
    """Return a `dict[str, bool]` keyed by each caller's own rule
    `condition` names.

    Also includes one `f"modern-cli:{tool}"` key per `MODERN_CLI_TOOLS`
    entry, individually live-verified -- so a tool-scoped-groups rule
    never has to collapse five tools' presence into one aggregate boolean.
    """
    root = repo_root or "."
    per_tool = {
        f"modern-cli:{name}": shutil.which(name, path=search_path) is not None
        for name in MODERN_CLI_TOOLS
    }
    result: dict[str, bool] = {
        "rtk": shutil.which("rtk", path=search_path) is not None,
        "modern-cli": any(per_tool.values()),
        "codegraph": os.path.isdir(os.path.join(root, ".codegraph")),
        "graphify": (
            shutil.which("graphify", path=search_path) is not None
            or os.path.isdir(os.path.join(root, "graphify-out"))
        ),
        "gsd": os.path.isdir(os.path.join(root, ".planning")),
    }
    result.update(per_tool)
    return result


__all__ = ["MODERN_CLI_TOOLS", "check_tool_presence"]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_ai_kit_rules_common -v`
Expected: all tests PASS, including the new `TestToolPresence` cases

- [ ] **Step 5: Commit**

```bash
git add skills/_shared/ai_kit_rules_common/tool_presence.py \
        tests/test_ai_kit_rules_common.py
git commit -m "feat(rules-common): add shared tool-presence detection"
```

---

### Task 3: Shared generic stack-tooling cache

**Files:**
- Create: `skills/_shared/ai_kit_rules_common/stack_cache.py`
- Test: `tests/test_ai_kit_rules_common.py` (insert `TestStackCache` above the `__main__` guard)

**Interfaces:**
- Consumes: nothing from Tasks 1-2 (independent module).
- Produces: `ai_kit_rules_common.stack_cache.default_cache_root(namespace: str) -> str`; `cache_path(stack: str, cache_root: str) -> str`; `read_stack_cache(stack: str, cache_root: str) -> dict` (returns `{"state": "absent"|"stale"|"fresh", "data": dict|None}`); `write_stack_cache(stack: str, data: dict, cache_root: str) -> None`; `get_stack_tooling(stack: str, cache_root: str) -> tuple[dict | None, bool]`; `STALE_AFTER_DAYS: int`. Unlike the current skill-local `stack_cache.py`, **`cache_root` is always a required, explicit argument here** — this module has no module-global default, since it's shared across skills with different cache namespaces. Each consuming skill computes its own default once via `default_cache_root(namespace)` and threads it through.

- [ ] **Step 1: Write the failing test**

Insert the following into `tests/test_ai_kit_rules_common.py` ABOVE the
`if __name__ == "__main__":` guard (do not append after it — classes
below that guard never run under `python3 tests/test_ai_kit_rules_common.py`):

```python
import json
from datetime import UTC, datetime, timedelta

from ai_kit_rules_common.stack_cache import (
    STALE_AFTER_DAYS,
    cache_path,
    default_cache_root,
    get_stack_tooling,
    read_stack_cache,
    write_stack_cache,
)


class TestStackCache(unittest.TestCase):
    def test_default_cache_root_includes_namespace(self):
        root = default_cache_root("demo-skill")
        self.assertIn("demo-skill", root)
        self.assertTrue(root.endswith(os.path.join("demo-skill", "stack-refs")))

    def test_absent_fresh_stale(self):
        with tempfile.TemporaryDirectory() as scratch:
            cache_root = os.path.join(scratch, "_cache")
            self.assertEqual(
                read_stack_cache("python", cache_root=cache_root)["state"], "absent"
            )

            write_stack_cache(
                "python", {"setup-env": "uv sync"}, cache_root=cache_root
            )
            self.assertEqual(
                read_stack_cache("python", cache_root=cache_root)["state"], "fresh"
            )

            path = cache_path("python", cache_root=cache_root)
            with open(path, encoding="utf-8") as handle:
                payload = json.load(handle)
            stale_dt = datetime.now(UTC) - timedelta(days=STALE_AFTER_DAYS + 1)
            payload["cached_at"] = stale_dt.isoformat()
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(payload, handle)
            self.assertEqual(
                read_stack_cache("python", cache_root=cache_root)["state"], "stale"
            )

    def test_invalid_stack_identifier_raises(self):
        with self.assertRaises(ValueError):
            cache_path("../escape", cache_root="/tmp/whatever")

    def test_get_stack_tooling_needs_research_when_absent_or_stale(self):
        with tempfile.TemporaryDirectory() as scratch:
            cache_root = os.path.join(scratch, "_cache")
            tooling, needs_research = get_stack_tooling("python", cache_root=cache_root)
            self.assertIsNone(tooling)
            self.assertTrue(needs_research)

            write_stack_cache("python", {"setup-env": "uv sync"}, cache_root=cache_root)
            tooling, needs_research = get_stack_tooling("python", cache_root=cache_root)
            self.assertEqual(tooling, {"setup-env": "uv sync"})
            self.assertFalse(needs_research)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_ai_kit_rules_common.TestStackCache -v`
Expected: `ModuleNotFoundError: No module named 'ai_kit_rules_common.stack_cache'`

- [ ] **Step 3: Write minimal implementation**

Create `skills/_shared/ai_kit_rules_common/stack_cache.py` (generalized from
`ai-kit-agents-md-rules-checker/ai_kit_agents_md_rules_checker/
stack_cache.py` — the generic caching engine only; each skill's own
tooling-key schema, e.g. `REQUIRED_STATIC_TARGETS`, stays local to that
skill since this module has no opinion on what a "tooling key" means):

```python
"""Generic per-(namespace, stack) tooling-recommendation cache with a
staleness check. Never invents a recommendation from training data -- this
module only reads/writes a local, staleness-gated cache of per-stack
tool-name strings; filling a cold/stale entry is each consuming skill's own
research-dispatch job.

Domain-agnostic: every function takes `cache_root` explicitly. There is no
module-global default here, since this module is shared across skills with
different cache namespaces -- call `default_cache_root(namespace)` once per
skill and thread the result through.
"""

from __future__ import annotations

import contextlib
import json
import os
import re
import tempfile
from datetime import UTC, datetime, timedelta

STALE_AFTER_DAYS = 30

_STACK_ID_RE = re.compile(r"[a-z0-9][a-z0-9_-]{0,63}")


def default_cache_root(namespace: str) -> str:
    """Return `~/.cache/ai-kit/<namespace>/stack-refs` (or `$XDG_CACHE_HOME`
    equivalent). `namespace` is each consuming skill's own cache-directory
    segment (e.g. `"agents-md-rules-checker"`, `"makefile-rules-checker"`)."""
    xdg_cache = os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache")
    return os.path.join(xdg_cache, "ai-kit", namespace, "stack-refs")


def cache_path(stack: str, cache_root: str) -> str:
    """Return the cache file path for `stack` under `cache_root`, after
    validating `stack`'s shape.

    `stack` must be a bare `[a-z0-9][a-z0-9_-]{0,63}` identifier -- no `/`,
    no `.`, no leading `-`/`_`. Raises `ValueError` BEFORE ever joining the
    value into a filesystem path, so a path-traversal-shaped `stack`
    argument can never resolve to a location outside `cache_root`.
    """
    if not isinstance(stack, str) or _STACK_ID_RE.fullmatch(stack) is None:
        raise ValueError(f"invalid stack identifier: {stack!r}")
    return os.path.join(cache_root, f"{stack}.json")


def read_stack_cache(stack: str, cache_root: str) -> dict:
    """Return `{"state": "absent"|"stale"|"fresh", "data": dict|None}`.

    `data` is populated whenever the file parses, regardless of staleness --
    a stale cache is still returned so a caller CAN fall back to it, but
    must see the `state` flag.
    """
    path = cache_path(stack, cache_root)
    if not os.path.isfile(path):
        return {"state": "absent", "data": None}
    try:
        with open(path, encoding="utf-8") as handle:
            payload = json.load(handle)
    except (json.JSONDecodeError, OSError, UnicodeDecodeError):
        return {"state": "absent", "data": None}
    if not isinstance(payload, dict):
        return {"state": "absent", "data": None}
    cached_at = payload.get("cached_at")
    data = payload.get("tooling")
    if not isinstance(cached_at, str):
        return {"state": "stale", "data": data}
    try:
        cached_dt = datetime.fromisoformat(cached_at)
    except ValueError:
        return {"state": "stale", "data": data}
    if cached_dt.tzinfo is None:
        cached_dt = cached_dt.replace(tzinfo=UTC)
    age = datetime.now(UTC) - cached_dt
    state = "stale" if age > timedelta(days=STALE_AFTER_DAYS) else "fresh"
    return {"state": state, "data": data}


def write_stack_cache(stack: str, data: dict, cache_root: str) -> None:
    """Atomically write `{"cached_at": <iso now>, "stack": stack, "tooling": data}`
    under `cache_root`, via `tempfile.mkstemp` + `os.replace`."""
    path = cache_path(stack, cache_root)
    dirname = os.path.dirname(path)
    os.makedirs(dirname, exist_ok=True)
    payload = {
        "cached_at": datetime.now(UTC).isoformat(),
        "stack": stack,
        "tooling": data,
    }
    fd, tmp = tempfile.mkstemp(dir=dirname, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    except OSError:
        with contextlib.suppress(OSError):
            os.unlink(tmp)
        raise


def get_stack_tooling(stack: str, cache_root: str) -> tuple[dict | None, bool]:
    """Return `(tooling_or_None, needs_research)`.

    `needs_research` is `True` for both `"absent"` and `"stale"` states.
    """
    result = read_stack_cache(stack, cache_root)
    needs_research = result["state"] in ("absent", "stale")
    return result["data"], needs_research


__all__ = [
    "STALE_AFTER_DAYS",
    "cache_path",
    "default_cache_root",
    "get_stack_tooling",
    "read_stack_cache",
    "write_stack_cache",
]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_ai_kit_rules_common -v`
Expected: all tests PASS, including the new `TestStackCache` cases

- [ ] **Step 5: Commit**

```bash
git add skills/_shared/ai_kit_rules_common/stack_cache.py \
        tests/test_ai_kit_rules_common.py
git commit -m "feat(rules-common): add shared generic stack-tooling cache"
```

---

### Task 4: Shared remediation ordering helper

**Files:**
- Create: `skills/_shared/ai_kit_rules_common/remediation.py`
- Test: `tests/test_ai_kit_rules_common.py` (insert `TestRemediation` above the `__main__` guard)

**Interfaces:**
- Consumes: nothing from Tasks 1-3 (independent module).
- Produces: `ai_kit_rules_common.remediation.build_remediation(report: dict) -> dict` returning `{"remediate": [...ordered by criticality...], "blocked": [...]}`.
- **Known scope limit (temporary, not generic yet):** this module branches
  on exactly two literal report keys — `"workflow"` and `"makefile"` — not
  on "every kind the report happens to carry." A report key for any of the
  other five checker skills this plan's Goal names as future consumers
  (precommit/arch/docker-compose/cicd/orchestrator) produces neither a
  `remediate` nor a `blocked` entry for that key's findings; they are
  silently dropped, not errored. This is acceptable ONLY because `workflow`
  and `makefile` are the only two kinds any skill produces today — the
  `"makefile"` branch is a direct carry-over of
  `ai-kit-agents-md-rules-checker/ai_kit_agents_md_rules_checker/
  remediation.py`'s existing logic, kept here unchanged under this plan's
  zero-behavior-change constraint. The named removal point: the follow-up
  `ai-kit-makefile-rules-checker` plan (referenced in Task 5 Step 5's
  `stack_cache.py` docstring) relocates `makefile_checker.py` AND this
  `"makefile"` branch together into that new skill's own remediation
  wrapper, leaving this shared module with only the generic `"workflow"`
  handling — at which point a precommit/arch/docker-compose/cicd checker
  plan can generalize the kind-dispatch properly (e.g. iterating
  `report.keys()` against a declared per-kind shape) instead of adding a
  third hardcoded branch.

- [ ] **Step 1: Write the failing test**

Insert the following into `tests/test_ai_kit_rules_common.py` ABOVE the
`if __name__ == "__main__":` guard (do not append after it — classes
below that guard never run under `python3 tests/test_ai_kit_rules_common.py`):

```python
from ai_kit_rules_common.remediation import build_remediation


class TestRemediation(unittest.TestCase):
    def test_missing_and_near_miss_auto_apply(self):
        report = {
            "workflow": [
                {"id": "X01", "status": "missing", "criticality": 1, "summary": "s1"},
                {"id": "X02", "status": "near_miss", "criticality": 2, "summary": "s2"},
                {"id": "X03", "status": "present", "criticality": 3, "summary": "s3"},
            ]
        }
        result = build_remediation(report)
        ids = {e["id"]: e["auto_apply"] for e in result["remediate"]}
        self.assertEqual(ids, {"X01": True, "X02": False})
        self.assertEqual(result["blocked"], [])

    def test_returns_dict_never_bare_list(self):
        result = build_remediation({"workflow": []})
        self.assertIsInstance(result, dict)
        self.assertEqual(result, {"remediate": [], "blocked": []})

    def test_unknown_kind_keys_ignored_safely(self):
        # A report carrying a kind key this module doesn't branch on (e.g.
        # a future precommit-checker's findings, see this task's Interfaces
        # "Known scope limit" note) must not crash build_remediation -- the
        # unknown kind's findings are silently dropped, not validated
        # against a fixed kind list, and findings under known kinds are
        # still processed normally alongside it.
        result = build_remediation(
            {
                "workflow": [
                    {
                        "id": "X01",
                        "status": "missing",
                        "criticality": 1,
                        "summary": "s1",
                    }
                ],
                "precommit": [{"id": "Y01", "status": "missing", "criticality": 1}],
            }
        )
        self.assertEqual(len(result["remediate"]), 1)
        self.assertEqual(result["remediate"][0]["id"], "X01")
        self.assertEqual(result["blocked"], [])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_ai_kit_rules_common.TestRemediation -v`
Expected: `ModuleNotFoundError: No module named 'ai_kit_rules_common.remediation'`

- [ ] **Step 3: Write minimal implementation**

Create `skills/_shared/ai_kit_rules_common/remediation.py` (moved from
`ai-kit-agents-md-rules-checker/ai_kit_agents_md_rules_checker/
remediation.py` — the `build_remediation` function body is byte-identical
to the existing file; only the module docstring is rewritten to
de-skill-specificize it, and a new `__all__` is added, since the existing
file has none. The `"workflow"` branch is generic; the `"makefile"`
branch is a temporary carry-over — see this task's Interfaces section for
the named removal point. Skills that don't produce a `"makefile"`-shaped
key simply get an empty `report.get("makefile", [])` and are unaffected,
but a skill that produces some OTHER kind key gets no `remediate`/`blocked`
entries for it at all until that removal point generalizes the dispatch):

```python
"""Generic remediation payload builder.

Turns a `check()`-shaped report into an ordered, auto-apply-annotated
hand-off list. Reads only fields a rule-checking module already attaches to
each finding -- never looks anything up in a rules module itself.
"""

from __future__ import annotations


def build_remediation(report: dict) -> dict:
    """Build `{"remediate": [...ordered...], "blocked": [...]}` from `report`.

    `workflow`-kind findings with `status` in `("missing", "near_miss")`
    become `remediate` entries -- `auto_apply` is `True` for `missing`,
    `False` for `near_miss`; `"present"`/`"not_applicable"` findings are
    skipped. `matched_signals` is carried forward so a near-miss
    confirmation has real evidence to name.

    `makefile`-kind findings (both `"target"`- and `"category"`-keyed,
    treated identically) branch ONLY on `recommendation`/`needs_research`,
    never on `present` or on which identifying key is set: any finding with
    a non-`None` `recommendation` becomes a `remediate` entry with
    `auto_apply=True`; any finding with `needs_research=True` and no
    `recommendation` goes into `blocked`, carrying its `criticality`/
    `summary`/identifier/`"stacks"` list forward verbatim.

    Both kinds' `remediate` entries are built into ONE list, then sorted by
    `criticality` ascending, spanning every kind present in `report`
    together -- never separately-ordered lists. Returns a dict, never a
    bare list.
    """
    remediate: list[dict] = []
    blocked: list[dict] = []

    for finding in report.get("workflow", []):
        status = finding.get("status")
        if status not in ("missing", "near_miss"):
            continue
        remediate.append(
            {
                "kind": "workflow",
                "id": finding["id"],
                "status": status,
                "criticality": finding["criticality"],
                "summary": finding["summary"],
                "matched_signals": finding.get("matched_signals", []),
                "auto_apply": status == "missing",
            }
        )

    for finding in report.get("makefile", []):
        identifier = finding.get("target", finding.get("category"))
        recommendation = finding.get("recommendation")
        if recommendation is not None:
            remediate.append(
                {
                    "kind": "makefile",
                    "id": identifier,
                    "criticality": finding["criticality"],
                    "summary": finding["summary"],
                    "auto_apply": True,
                }
            )
        elif finding.get("needs_research"):
            blocked.append(
                {
                    "kind": "makefile",
                    "id": identifier,
                    "criticality": finding["criticality"],
                    "summary": finding["summary"],
                    "stacks": finding.get("stacks", []),
                }
            )

    remediate.sort(key=lambda entry: entry["criticality"])
    return {"remediate": remediate, "blocked": blocked}


__all__ = ["build_remediation"]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_ai_kit_rules_common -v`
Expected: every test in this new file PASSES (Tasks 1-4 combined)

- [ ] **Step 5: Commit**

```bash
git add skills/_shared/ai_kit_rules_common/remediation.py \
        tests/test_ai_kit_rules_common.py
git commit -m "feat(rules-common): add shared remediation ordering helper"
```

---

### Task 5: Migrate `ai-kit-agents-md-rules-checker` to delegate to the shared package

**Files:**
- Modify: `skills/ai-kit-agents-md-rules-checker/ai_kit_agents_md_rules_checker/__init__.py`
- Modify: `skills/ai-kit-agents-md-rules-checker/ai_kit_agents_md_rules_checker/rule_checker.py`
- Modify: `skills/ai-kit-agents-md-rules-checker/ai_kit_agents_md_rules_checker/rules.py`
- Modify: `skills/ai-kit-agents-md-rules-checker/ai_kit_agents_md_rules_checker/tool_presence.py`
- Modify: `skills/ai-kit-agents-md-rules-checker/ai_kit_agents_md_rules_checker/stack_cache.py`
- Modify: `skills/ai-kit-agents-md-rules-checker/ai_kit_agents_md_rules_checker/remediation.py`
- Test: `tests/test_ai_kit_agents_md_rules_checker.py` (no content changes — this task's deliverable IS that this file passes unmodified)

**Interfaces:**
- Consumes: `ai_kit_rules_common.classification.check_rules`/`evaluate_condition`/`CONDITION_ALWAYS` (Task 1), `ai_kit_rules_common.tool_presence.check_tool_presence`/`MODERN_CLI_TOOLS` (Task 2), `ai_kit_rules_common.stack_cache.{default_cache_root,cache_path,read_stack_cache,write_stack_cache,get_stack_tooling,STALE_AFTER_DAYS}` (Task 3), `ai_kit_rules_common.remediation.build_remediation` (Task 4).
- Produces: every existing public name in `rule_checker.py`/`tool_presence.py`/`stack_cache.py`/`remediation.py` is preserved with an identical signature — `makefile_checker.py` and `cli.py` need NO changes in this task, since they import these four modules' names exactly as before.

- [ ] **Step 1: Add the shared-package bootstrap to `__init__.py`**

Replace the full content of `skills/ai-kit-agents-md-rules-checker/
ai_kit_agents_md_rules_checker/__init__.py`:

```python
"""AGENTS.md/CLAUDE.md house-rule checker (provisional package name)."""

import os
import sys

_PKG_DIR = os.path.dirname(os.path.realpath(__file__))
_SKILL_DIR = os.path.dirname(_PKG_DIR)
_SKILLS_ROOT = os.path.dirname(_SKILL_DIR)
_SHARED_DIR = os.path.join(_SKILLS_ROOT, "_shared")

if not os.path.isdir(os.path.join(_SHARED_DIR, "ai_kit_rules_common")):
    raise ImportError(
        f"ai-kit-agents-md-rules-checker requires skills/_shared/"
        f"ai_kit_rules_common to exist beside this skill; looked for it at "
        f"{_SHARED_DIR!r} (resolved from this installed copy's own real "
        f"path) and found nothing there. This directory is only present "
        f"when the skill is reached via the `~/.claude/skills` symlink "
        f"install (`tools/setup.py`) or a direct git checkout of this "
        f"repo -- a copy-install into a different host (e.g. a Claude "
        f"Code plugin root, an opencode skills dir, or ~/.agents) does "
        f"not carry the shared package. Re-run `python3 tools/setup.py` "
        f"or reinstall from a checkout."
    )

if _SHARED_DIR not in sys.path:
    sys.path.insert(0, _SHARED_DIR)
```

- [ ] **Step 2: Make `rules.py` import `CONDITION_ALWAYS` from the shared
  module instead of defining its own copy**

Today `rules.py:19` defines `CONDITION_ALWAYS = "always"` locally, and
every rule dict in its `RULES` tuple references that local name. Task 1's
`classification.py:14` defines the same literal independently. Left as-is,
these two definitions could drift with no error — against this repo's
single-source-of-truth discipline (see `stack_cache.py:6-9`'s own "there is
no module-global default here" framing for the same principle applied to
`cache_root`). Make the shared module the one owner: in
`skills/ai-kit-agents-md-rules-checker/ai_kit_agents_md_rules_checker/
rules.py`, replace line 19:

```python
CONDITION_ALWAYS = "always"
```

with:

```python
from ai_kit_rules_common.classification import CONDITION_ALWAYS
```

This import resolves because `__init__.py` (Step 1, just completed) always
runs before any sibling module in this package is imported, so
`skills/_shared` is already on `sys.path` by the time `rules.py`'s
module-level `from ai_kit_rules_common...` line executes. Every other
reference to `CONDITION_ALWAYS` in `rules.py` (the rule dicts themselves)
is unchanged — only the definition line moves to an import.

- [ ] **Step 3: Rewrite `rule_checker.py` to delegate**

Replace the full content of `skills/ai-kit-agents-md-rules-checker/
ai_kit_agents_md_rules_checker/rule_checker.py`:

```python
"""Workflow-rule prose checker with live tool-presence conditioning.

D-07: a rule whose `condition` is not met in this environment is skipped/
reframed as `"not_applicable"`, never flagged as a generic gap.

The actual classification engine lives in `ai_kit_rules_common.
classification` (shared across the rules-checker skill family). This
module's only job is binding that generic engine to THIS skill's own
17-rule `RULES` tuple.
"""

from __future__ import annotations

from ai_kit_rules_common.classification import check_rules, evaluate_condition

from .rules import RULES


def check_workflow_rules(
    agents_md_text: str, tool_presence: dict, include_present: bool = False
) -> list[dict]:
    return check_rules(agents_md_text, tool_presence, RULES, include_present=include_present)


__all__ = [
    "check_workflow_rules",
    "evaluate_condition",
]
```

- [ ] **Step 4: Rewrite `tool_presence.py` to delegate**

Replace the full content of `skills/ai-kit-agents-md-rules-checker/
ai_kit_agents_md_rules_checker/tool_presence.py`:

```python
"""Live tool-presence detection -- delegates to the shared
`ai_kit_rules_common.tool_presence` module (identical logic, shared across
the rules-checker skill family). Re-exported here under this skill's own
package namespace so existing imports (`from ai_kit_agents_md_rules_checker
import tool_presence`) keep working unchanged.
"""

from __future__ import annotations

from ai_kit_rules_common.tool_presence import MODERN_CLI_TOOLS, check_tool_presence

__all__ = ["MODERN_CLI_TOOLS", "check_tool_presence"]
```

- [ ] **Step 5: Rewrite `stack_cache.py` to bind this skill's namespace and schema**

Replace the full content of `skills/ai-kit-agents-md-rules-checker/
ai_kit_agents_md_rules_checker/stack_cache.py`:

```python
"""This skill's Makefile-tooling schema, bound to the shared generic cache
engine in `ai_kit_rules_common.stack_cache` under this skill's own cache
namespace (`agents-md-rules-checker`).

NOTE: `REQUIRED_STATIC_TARGETS`/`RESEARCH_CATEGORIES`/`ALL_TOOLING_KEYS`
below are Makefile-tooling-specific, not generic -- they stay HERE (not in
the shared package) because `makefile_checker.py` still lives in this
skill. A follow-up plan relocates both this schema and `makefile_checker.py`
together into a dedicated `ai-kit-makefile-rules-checker` skill; this
module's job until then is unchanged from before this refactor.
"""

from __future__ import annotations

from ai_kit_rules_common import stack_cache as _shared

STALE_AFTER_DAYS = _shared.STALE_AFTER_DAYS

REQUIRED_STATIC_TARGETS = (
    "setup-env",
    "validate",
    "test",
    "test-unit",
    "test-integration",
    "e2e-test",
    "arch-test",
)

# Tool-category recommendations the research prompt asks for that do NOT
# map 1:1 to one of the 7 static target names above. `validate-order` and
# `precommit-vs-prepush-split` are deliberately NOT members: both are
# process/structural facts readable directly from the target repo's own
# files (see makefile_checker.check_validate_order and
# check_precommit_prepush_split), not a tool pick that benefits from
# research -- a category with no research-fillable content would be a
# perpetual, unsatisfiable false positive.
RESEARCH_CATEGORIES = (
    "formatter",
    "security-scanner",
    "code-smell-detector",
    "duplicate-code-detector",
    "dead-code-detector",
)

ALL_TOOLING_KEYS = REQUIRED_STATIC_TARGETS + RESEARCH_CATEGORIES

_NAMESPACE = "agents-md-rules-checker"
CACHE_ROOT = _shared.default_cache_root(_NAMESPACE)


def cache_path(stack: str, cache_root: str | None = None) -> str:
    return _shared.cache_path(stack, cache_root or CACHE_ROOT)


def read_stack_cache(stack: str, cache_root: str | None = None) -> dict:
    return _shared.read_stack_cache(stack, cache_root or CACHE_ROOT)


def write_stack_cache(stack: str, data: dict, cache_root: str | None = None) -> None:
    _shared.write_stack_cache(stack, data, cache_root or CACHE_ROOT)


def get_stack_tooling(
    stack: str, cache_root: str | None = None
) -> tuple[dict | None, bool]:
    return _shared.get_stack_tooling(stack, cache_root or CACHE_ROOT)


__all__ = [
    "ALL_TOOLING_KEYS",
    "CACHE_ROOT",
    "REQUIRED_STATIC_TARGETS",
    "RESEARCH_CATEGORIES",
    "STALE_AFTER_DAYS",
    "cache_path",
    "get_stack_tooling",
    "read_stack_cache",
    "write_stack_cache",
]
```

**Why `cache_root or CACHE_ROOT` and not a default-argument binding:**
`CACHE_ROOT` must be looked up as a bare module-global name INSIDE each
function body (not captured as a parameter default at def-time), because
`tests/test_ai_kit_agents_md_rules_checker.py`'s
`TestCheckMakefileShapeTracer.test_arch_test_and_hook_gaps_named_
individually` does `mock.patch.object(stack_cache, "CACHE_ROOT", ...)` and
relies on that patch being visible to every function that reads
`CACHE_ROOT` afterward. A default argument (`cache_root: str | None =
CACHE_ROOT`) would capture the value once at function-definition time and
never see the patch.

- [ ] **Step 6: Rewrite `remediation.py` to delegate**

Replace the full content of `skills/ai-kit-agents-md-rules-checker/
ai_kit_agents_md_rules_checker/remediation.py`:

```python
"""Remediation payload builder -- delegates to the shared
`ai_kit_rules_common.remediation` module. Re-exported here under this
skill's own package namespace so existing imports
(`from ai_kit_agents_md_rules_checker import remediation`) keep working
unchanged.
"""

from __future__ import annotations

from ai_kit_rules_common.remediation import build_remediation

__all__ = ["build_remediation"]
```

- [ ] **Step 7: Run the FULL existing test suite for this skill**

Run: `python3 -m unittest tests.test_ai_kit_agents_md_rules_checker -v`
Expected: every test PASSES unmodified — this is the regression proof that
the extraction changed zero observable behavior. If anything fails, the
delegation in Steps 1-5 introduced a real behavior change; fix the
delegating module (never the test) to restore exact parity.

- [ ] **Step 8: Commit**

```bash
git add skills/ai-kit-agents-md-rules-checker/ai_kit_agents_md_rules_checker/__init__.py \
        skills/ai-kit-agents-md-rules-checker/ai_kit_agents_md_rules_checker/rule_checker.py \
        skills/ai-kit-agents-md-rules-checker/ai_kit_agents_md_rules_checker/rules.py \
        skills/ai-kit-agents-md-rules-checker/ai_kit_agents_md_rules_checker/tool_presence.py \
        skills/ai-kit-agents-md-rules-checker/ai_kit_agents_md_rules_checker/stack_cache.py \
        skills/ai-kit-agents-md-rules-checker/ai_kit_agents_md_rules_checker/remediation.py
git commit -m "refactor(agents-md-rules-checker): delegate to shared ai_kit_rules_common package"
```

---

### Task 6: Wire the shared package into ai-kit's own quality gates

**Files:**
- Modify: `Makefile`
- Modify: `.pre-commit-config.yaml`
- Modify: `pyproject.toml`
- Modify: `tests/test_ai_kit_agents_md_rules_checker.py:1133-1163` (extend `TestGateRegistration`)

**Interfaces:**
- Consumes: nothing new — this task only wires already-existing files
  (from Tasks 1-5) into already-existing gate configs.
- Produces: nothing new for other tasks to consume — this is the final
  task of this plan.

- [ ] **Step 1: Add the shared package to `Makefile`'s `test-unit` and `lint` targets**

In `Makefile`, find the `test-unit:` recipe line (currently ends with
`tests.test_ai_kit_gsd_curated_config`) and add `tests.test_ai_kit_rules_common`
to the end of that same line:

```makefile
test-unit:
	python3 -m unittest tests.test_setup tests.test_status_line tests.test_external_segments tests.test_statusline_doctor tests.test_markdown_to_pdf tests.test_mermaid_style tests.test_ai_kit_spec tests.test_ai_kit_spec_gsd tests.test_ai_kit_spec_superpowers tests.test_ai_kit_opencode_providers tests.test_tool_substitution_hook tests.test_ai_kit_usage_metrics tests.test_ai_kit_agents_md_rules_checker tests.test_ai_kit_gsd_curated_config tests.test_ai_kit_rules_common
	uv run python3 -m unittest tests.test_framework_profiles
```

Find the `lint:` recipe's `py_compile` line (currently ends with
`skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/*.py`) and add
`skills/_shared/ai_kit_rules_common/*.py` to the end of that same line:

```makefile
lint:
	shellcheck $(INSTALL_SH) tests/test_install.sh
	python3 -m py_compile $(SETUP_PY) tools/status-line.py tools/statusline-doctor.py tools/hooks/*.py tools/config_doctor_*.py skills/ai-kit-usage-metrics/ai-kit-usage-metrics.py skills/ai-kit-usage-metrics/ai_kit_usage_metrics/*.py skills/ai-kit-agents-md-rules-checker/ai-kit-agents-md-rules-checker.py skills/ai-kit-agents-md-rules-checker/ai_kit_agents_md_rules_checker/*.py skills/ai-kit-gsd-curated-config/ai-kit-gsd-curated-config.py skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/*.py skills/_shared/ai_kit_rules_common/*.py
```

- [ ] **Step 2: Add the shared package to `.pre-commit-config.yaml`'s `ruff`/`py-compile` file globs and `unittest` entry**

In `.pre-commit-config.yaml`, the `ruff` hook's `files:` regex currently
ends `...|skills/ai-kit-gsd-curated-config/.*)\.py$`. Change it to add an
alternative for the shared package:

```yaml
      - id: ruff
        name: ruff
        entry: uv run ruff check
        language: system
        files: ^((tools|tests)/.*|skills/ai-kit-spec-review/ai-kit-spec-review|skills/ai-kit-spec-execute-gsd/.*|skills/ai-kit-spec-execute/.*|skills/ai-kit-opencode-providers/.*|skills/ai-kit-usage-metrics/.*|skills/ai-kit-agents-md-rules-checker/.*|skills/ai-kit-gsd-curated-config/.*|skills/_shared/.*)\.py$
        require_serial: true
```

The `py-compile` hook's `files:` regex similarly ends
`...|skills/ai-kit-gsd-curated-config/.*)\.py$`. Change it the same way:

```yaml
      - id: py-compile
        name: py-compile
        entry: python3 -m py_compile
        language: system
        files: ^(tools/(status-line|statusline-doctor|setup)|tools/hooks/[a-z_]+|tools/config_doctor_[a-z_]+|skills/ai-kit-spec-review/ai-kit-spec-review|skills/ai-kit-spec-execute-gsd/.*|skills/ai-kit-spec-execute/.*|skills/ai-kit-opencode-providers/.*|skills/ai-kit-usage-metrics/.*|skills/ai-kit-agents-md-rules-checker/.*|skills/ai-kit-gsd-curated-config/.*|skills/_shared/.*)\.py$
```

The `unittest` hook's `entry:` currently ends
`...tests.test_ai_kit_agents_md_rules_checker tests.test_ai_kit_gsd_curated_config`.
Add `tests.test_ai_kit_rules_common` to the end:

```yaml
      - id: unittest
        name: unittest (core)
        entry: python3 -m unittest tests.test_status_line tests.test_setup tests.test_external_segments tests.test_statusline_doctor tests.test_arch tests.test_ai_kit_spec tests.test_ai_kit_spec_gsd tests.test_ai_kit_opencode_providers tests.test_tool_substitution_hook tests.test_config_doctor tests.test_config_doctor_pty tests.test_ai_kit_usage_metrics tests.test_ai_kit_agents_md_rules_checker tests.test_ai_kit_gsd_curated_config tests.test_ai_kit_rules_common
        language: system
        pass_filenames: false
        always_run: true
        stages: [pre-push]
```

- [ ] **Step 3: Add the shared package to `pyproject.toml`'s pyright/vulture scopes**

In `pyproject.toml` line 88 (`[tool.vulture] paths`), change:

```toml
paths = ["tools/status-line.py", "tools/statusline-doctor.py", "tools/setup.py", "skills/ai-kit-usage-metrics", "skills/ai-kit-agents-md-rules-checker", "skills/ai-kit-gsd-curated-config"]
```

to:

```toml
paths = ["tools/status-line.py", "tools/statusline-doctor.py", "tools/setup.py", "skills/ai-kit-usage-metrics", "skills/ai-kit-agents-md-rules-checker", "skills/ai-kit-gsd-curated-config", "skills/_shared"]
```

In `pyproject.toml` line 94 (`[tool.pyright] include`), change:

```toml
include = ["tools/status-line.py", "tools/statusline-doctor.py", "tools/setup.py", "tools/hooks", "tools/config_doctor_checks.py", "tools/config_doctor_readers.py", "tools/config_doctor_app.py", "tools/config_doctor_appliers.py", "skills/ai-kit-usage-metrics", "skills/ai-kit-agents-md-rules-checker", "skills/ai-kit-gsd-curated-config"]
```

to:

```toml
include = ["tools/status-line.py", "tools/statusline-doctor.py", "tools/setup.py", "tools/hooks", "tools/config_doctor_checks.py", "tools/config_doctor_readers.py", "tools/config_doctor_app.py", "tools/config_doctor_appliers.py", "skills/ai-kit-usage-metrics", "skills/ai-kit-agents-md-rules-checker", "skills/ai-kit-gsd-curated-config", "skills/_shared"]
```

`pyproject.toml`'s `[tool.pyright]` block currently has no `extraPaths` key
(verified: only `include`/`pythonVersion`/`typeCheckingMode` are set today).
Without one, `skills/ai-kit-agents-md-rules-checker`'s new
`from ai_kit_rules_common.* import ...` statements (Task 5) are
`reportMissingImports` errors, since pyright has no way to resolve
`ai_kit_rules_common` as an importable root — it is not installed as a
package, only reached via each consumer's own runtime `sys.path` insert.
Add `extraPaths` right after `pythonVersion`/`typeCheckingMode`:

```toml
[tool.pyright]
include = ["tools/status-line.py", "tools/statusline-doctor.py", "tools/setup.py", "tools/hooks", "tools/config_doctor_checks.py", "tools/config_doctor_readers.py", "tools/config_doctor_app.py", "tools/config_doctor_appliers.py", "skills/ai-kit-usage-metrics", "skills/ai-kit-agents-md-rules-checker", "skills/ai-kit-gsd-curated-config", "skills/_shared"]
pythonVersion = "3.12"
typeCheckingMode = "basic"
extraPaths = ["skills/_shared"]
```

- [ ] **Step 4: Extend `TestGateRegistration` to assert the shared package is registered**

In `tests/test_ai_kit_agents_md_rules_checker.py`, add six new assertions
across the four existing test methods of `TestGateRegistration`, right
after each method's existing `assertIn`/assertion calls:
`test_makefile_registers_module_and_package` and
`test_precommit_ruff_and_py_compile_match_package_path` each gain two new
lines; `test_pyright_include_contains_package_directory` and
`test_vulture_paths_contains_package_directory` each gain one new line.
This is an additive exception to the zero-behavior-change constraint —
see the Global Constraints section, which scopes "every existing test
must pass unmodified" to Task 5's regression proof and explicitly carves
out these additive assertions:

```python
class TestGateRegistration(unittest.TestCase):
    def test_makefile_registers_module_and_package(self):
        with open(_MAKEFILE_PATH, encoding="utf-8") as handle:
            text = handle.read()
        self.assertIn("tests.test_ai_kit_agents_md_rules_checker", text)
        self.assertIn("skills/ai-kit-agents-md-rules-checker/", text)
        self.assertIn("tests.test_ai_kit_rules_common", text)
        self.assertIn("skills/_shared/ai_kit_rules_common/", text)

    def test_precommit_ruff_and_py_compile_match_package_path(self):
        for hook_id in ("ruff", "py-compile"):
            regex = _precommit_hook_files_regex(hook_id)
            self.assertIsNotNone(
                re.match(regex, _CLI_PY_CANDIDATE),
                f"{_CLI_PY_CANDIDATE} did not match {hook_id} files: {regex}",
            )
            self.assertIsNotNone(
                re.match(regex, "skills/_shared/ai_kit_rules_common/classification.py"),
                f"shared package did not match {hook_id} files: {regex}",
            )
        entry_block = _precommit_hook_block("unittest")
        match = re.search(r"^\s*entry:\s*(.+)$", entry_block, re.MULTILINE)
        self.assertIsNotNone(match, "no entry: value for hook unittest")
        self.assertIn("tests.test_ai_kit_agents_md_rules_checker", match.group(1))
        self.assertIn("tests.test_ai_kit_rules_common", match.group(1))

    def test_pyright_include_contains_package_directory(self):
        with open(_PYPROJECT_PATH, "rb") as handle:
            data = tomllib.load(handle)
        include = data["tool"]["pyright"]["include"]
        self.assertIn("skills/ai-kit-agents-md-rules-checker", include)
        self.assertIn("skills/_shared", include)

    def test_vulture_paths_contains_package_directory(self):
        with open(_PYPROJECT_PATH, "rb") as handle:
            data = tomllib.load(handle)
        paths = data["tool"]["vulture"]["paths"]
        self.assertIn("skills/ai-kit-agents-md-rules-checker", paths)
        self.assertIn("skills/_shared", paths)
```

- [ ] **Step 5: Run the full relevant test + lint suite**

Run: `python3 -m unittest tests.test_ai_kit_agents_md_rules_checker tests.test_ai_kit_rules_common -v`
Expected: every test PASSES, including the four extended
`TestGateRegistration` assertions.

Run: `make lint`
Expected: `py_compile` succeeds against every file including the new
`skills/_shared/ai_kit_rules_common/*.py` modules; `shellcheck` output
unaffected (no `.sh` files touched in this plan).

Run: `uv run pre-commit run ruff --all-files` and `uv run pre-commit run py-compile --all-files`
Expected: both hooks now pick up `skills/_shared/ai_kit_rules_common/*.py`
and pass.

Run: `make pyright`
Expected: passes — `skills/_shared` is now in `[tool.pyright] include` AND
in `extraPaths`, so `ai-kit-agents-md-rules-checker`'s new
`from ai_kit_rules_common.* import ...` statements resolve with no
`reportMissingImports` errors.

Run: `make vulture`
Expected: passes — `skills/_shared` is now in `[tool.vulture] paths`, so
the new package's dead-code scan runs and finds nothing unused (every name
in each module's `__all__` is imported by at least one consumer).

- [ ] **Step 6: Commit**

```bash
git add Makefile .pre-commit-config.yaml pyproject.toml \
        tests/test_ai_kit_agents_md_rules_checker.py
git commit -m "chore(rules-common): wire shared package into lint/test gates"
```

---

## Self-Review Notes

- **Spec coverage**: this plan implements the spec's "`skills/_shared/
  ai_kit_rules_common/`" component's classification engine, tool_presence,
  and generic stack_cache pieces in full, and its remediation helper with
  one named deviation (cross-kind merging — see deviation 3 below), plus
  the "ai-kit-agents-md-rules-checker (pruned)" component's shared-package
  migration half — NOT yet the "Drops entirely: makefile_checker.py..."
  half, which is deliberately deferred to the follow-up
  `ai-kit-makefile-rules-checker` plan (see rationale in the plan's
  Architecture section: pruning Makefile-checking capability before its
  replacement skill exists would leave a capability gap between plans).
  The spec's stated portability property for `skills/_shared/` (every
  consuming skill "independently copyable to a different host") does NOT
  yet hold for three of `SKILL.md`'s five install hosts — see deviation 4
  below. Every other spec component (makefile/precommit/arch/
  docker-compose/cicd checkers, orchestrator, tooling taxonomy) is out of
  scope for this plan by design — each gets its own plan once this one
  lands.
- **Recorded deviations from the spec** (four known deliberate
  deviations; the first two are forced by the Global Constraint that this
  plan changes zero observable behavior of the existing skill, the last
  two are scope/design carry-overs flagged for a named follow-up plan to
  resolve):
  - The spec (design doc, "same validation contract as today...but keyed
    generically") assigns the cache payload validation contract
    (`ALL_TOOLING_KEYS` membership, non-empty strings, `(source: ...)`
    provenance) to the shared module. This plan deliberately leaves
    `_validate_tooling_payload` in `cli.py` (`cli.py:105-123`), unmoved —
    it validates against THIS skill's own `ALL_TOOLING_KEYS` schema
    (`REQUIRED_STATIC_TARGETS` + `RESEARCH_CATEGORIES`, both
    Makefile-specific), which Task 5 Step 5 explicitly keeps local to this
    skill rather than generalizing into the shared package. Moving the
    validator without moving its schema would split one concern across two
    packages for no behavior change; this plan instead records the
    deviation and leaves both together, to be revisited by whichever
    follow-up plan finally generalizes (or relocates) the tooling-key
    schema itself.
  - The spec's staleness convention is "older than 180 days"; this plan's
    `ai_kit_rules_common.stack_cache.STALE_AFTER_DAYS` is `30`, copied
    verbatim from the existing skill-local `stack_cache.py:49` value, per
    the zero-behavior-change constraint. Reconciling the two conventions
    (either raising the shared default to 180, or confirming 30 is the
    intended value project-wide) is explicitly OUT OF SCOPE here — a
    follow-up plan inherits exactly one shared `STALE_AFTER_DAYS` to
    reconcile, not two independent skill-local copies that could each
    drift further.
  - The spec assigns cross-skill/cross-kind merging of remediation
    findings to the orchestrator, not to the single-domain ordering
    helper (spec: "Cross-skill merging is the orchestrator's job, not
    this helper's"). Task 4's `build_remediation`, as specified in this
    plan, instead merges `"workflow"` and `"makefile"` findings into ONE
    ordered `remediate` list within the helper itself. This is a
    deliberate carry-over of `ai-kit-agents-md-rules-checker`'s existing
    single-skill report shape (today's `cli.py` produces a report
    carrying both kinds at once, and the helper's pre-existing behavior
    merges them) — not yet the spec's multi-skill design, since no
    orchestrator exists yet to do that merging instead. Named removal
    point: the same future orchestrator plan that the spec's design
    anticipates must take over cross-kind ordering from this helper,
    narrowing `build_remediation` to a single-kind-per-call contract at
    that time.
  - The spec's `skills/_shared/` portability property ("each remains
    independently copyable to a different host — only `_shared/` must
    travel with it") does not hold for three of `SKILL.md`'s five
    documented install candidates (a Claude Code plugin root, an opencode
    install, or an `~/.agents` install — see this plan's Architecture
    section), since none of those installers are known to place
    `skills/_shared/` beside the installed skill. It holds only for the
    `~/.claude/skills` symlink install (`tools/setup.py`) and a direct git
    checkout. Task 5 Step 1's loud `ImportError` makes the failure mode
    legible on the three unsupported hosts rather than fixing them; fixing
    those installers' portability is explicitly out of this plan's scope
    and is left for whichever follow-up plan next touches `tools/setup.py`
    or those other install paths.
- **Placeholder scan**: none found — every step has real, runnable code.
- **Type consistency**: `check_rules`/`evaluate_condition` signatures match
  between Task 1's shared module and Task 5's delegating `rule_checker.py`;
  `cache_root` handling is identical in shape (optional, falls back to a
  module-level default) between the old local `stack_cache.py` and the new
  delegating one, verified against the existing `mock.patch.object(stack_cache,
  "CACHE_ROOT", ...)` test usage.
