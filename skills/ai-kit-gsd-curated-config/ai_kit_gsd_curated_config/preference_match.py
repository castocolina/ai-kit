"""Pure decision logic for D-03's two literal preference ladders (07-CONTEXT.md Specifics):
execution-delegation preference and plan-review preference. Consumes `model_detect.
build_candidate_pool`'s output (a plain `{cli_name: [model_id, ...]}` pool) -- no I/O, no
subprocess -- so this decision logic is unit-testable against a synthetic pool with zero
subprocess calls.

Deliberate, scoped exception to "this skill stays self-contained" (D-02): imports
`_hint_matches`, `ai_kit_spec`'s own proven delimiter-bounded substring-match regex helper, from
`ai_kit_spec.model_heuristics` -- reusing that ONE regex mechanism, never `ai_kit_spec`'s
detection/ranking classes wholesale. `ai_kit_spec`'s own skill directory is resolved via
`model_detect.resolve_ai_kit_spec_path`'s sibling-dir logic and added to `sys.path` before the
import, since this skill has no declared dependency contract on `ai_kit_spec` being importable
otherwise. The import is wrapped in `try/except ImportError` with a local fallback that
reimplements the same delimiter-bounded match: since `ai_kit_spec` is not a declared dependency,
its absence must degrade this module's regex helper, never crash the whole CLI at import time.
"""
import os
import re
import sys

from . import model_detect

_THIS_SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_ai_kit_spec_shim = model_detect.resolve_ai_kit_spec_path(_THIS_SKILL_DIR)
if _ai_kit_spec_shim is not None:
    _ai_kit_spec_skill_dir = os.path.dirname(_ai_kit_spec_shim)
    if _ai_kit_spec_skill_dir not in sys.path:
        sys.path.insert(0, _ai_kit_spec_skill_dir)

try:
    from ai_kit_spec.model_heuristics import _hint_matches  # pyright: ignore
except ImportError:
    # `ai_kit_spec` is a best-effort sibling, never a hard dependency (module docstring above):
    # if its skill directory can't be resolved, or the sibling install is missing/broken, this
    # skill must keep working rather than take the whole CLI down at import time. Fallback
    # reimplements the exact delimiter-bounded substring match `_hint_matches` documents.
    def _hint_matches(hint: str, lowered: str) -> bool:
        return re.search(rf"\b{re.escape(hint)}\b", lowered) is not None

# Fixed runtime search order for BOTH ladders (07-CONTEXT.md's Specifics section states this
# order for plan-review explicitly and gives no contrary order for execution, so this module
# applies the same order to both for one consistent, documented search policy rather than
# inventing a second one).
_RUNTIME_ORDER = ("opencode", "cursor-agent")

# `best_review_candidate` has no "no match" return value at all -- this is it.
NATIVE_LAST_RESORT = ("claude", "opus", "native-last-resort")

_GPT_SOL_PATTERN = re.compile(r"\bgpt-[0-9]+(?:\.[0-9]+)*-sol\b")


def _version_at_least(model_id: str, family: str, min_version: str) -> bool:
    """Extracts the numeric dotted version immediately following a bounded `family-` prefix and
    returns True only when that version, compared component-wise as integers (shorter tuple
    zero-padded), is >= the parsed `min_version` tuple. A model id with no such bounded
    family-version match returns False -- never raises on a non-numeric or absent segment."""
    match = re.search(rf"\b{re.escape(family)}-([0-9]+(?:\.[0-9]+)*)", model_id.lower())
    if match is None:
        return False
    found = tuple(int(p) for p in match.group(1).split("."))
    wanted = tuple(int(p) for p in min_version.split("."))
    length = max(len(found), len(wanted))
    found = found + (0,) * (length - len(found))
    wanted = wanted + (0,) * (length - len(wanted))
    return found >= wanted


def _bounded_hint_predicate(*hints):
    def _predicate(model_id: str) -> bool:
        lowered = model_id.lower()
        return any(_hint_matches(h, lowered) for h in hints)

    return _predicate


def _version_predicate(family: str, min_version: str):
    def _predicate(model_id: str) -> bool:
        return _version_at_least(model_id, family, min_version)

    return _predicate


def _gpt_sol_predicate(model_id: str) -> bool:
    return _GPT_SOL_PATTERN.search(model_id.lower()) is not None


# Declared rule order (07-CONTEXT.md D-03 Specifics, execution): coding/executor bounded-
# substring; composer>=2.5; grok>=4.6; deepseek-flash bounded-substring; luna bounded-substring.
EXECUTION_RULES = (
    ("coding-or-executor", _bounded_hint_predicate("coding", "executor")),
    ("composer>=2.5", _version_predicate("composer", "2.5")),
    ("grok>=4.6", _version_predicate("grok", "4.6")),
    ("deepseek-flash", _bounded_hint_predicate("deepseek-flash")),
    ("luna", _bounded_hint_predicate("luna")),
)

# Declared rule order (07-CONTEXT.md D-03 Specifics, plan-review): plan-review bounded-
# substring; gpt-<ver>-sol bounded pattern; glm-5.2/glm-5.3 bounded-substring.
REVIEW_RULES = (
    ("plan-review", _bounded_hint_predicate("plan-review")),
    ("gpt-sol", _gpt_sol_predicate),
    ("glm-5.2-or-5.3", _bounded_hint_predicate("glm-5.2", "glm-5.3")),
)


def _walk_rules(pool, rules):
    """Walks `rules` in declared order; for EACH rule, searches `pool.get("opencode", [])` then
    `pool.get("cursor-agent", [])` before moving to the next rule. Returns the FIRST
    `(cli, model, rule_label)` match found in that nested order, or `None` if no rule matches
    anything in either list."""
    for label, predicate in rules:
        for cli in _RUNTIME_ORDER:
            for model_id in pool.get(cli, []):
                if predicate(model_id):
                    return (cli, model_id, label)
    return None


def best_execution_candidate(pool):
    """Returns the first `(cli, model, rule_label)` match per `EXECUTION_RULES`'s declared
    order, or `None` if nothing matches anything."""
    return _walk_rules(pool, EXECUTION_RULES)


def best_review_candidate(pool):
    """Returns the first `(cli, model, rule_label)` match per `REVIEW_RULES`'s declared order;
    when NONE of the three rules match anything, returns the fixed native fallback
    `NATIVE_LAST_RESORT` -- this function has no "no match" return value at all."""
    result = _walk_rules(pool, REVIEW_RULES)
    if result is None:
        return NATIVE_LAST_RESORT
    return result
