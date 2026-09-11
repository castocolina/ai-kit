---
phase: 06-agents-md-rules-checker-skill
reviewed: 2026-09-11T00:00:00Z
depth: deep
files_reviewed: 15
files_reviewed_list:
  - skills/ai-kit-agents-md-rules-checker/SKILL.md
  - skills/ai-kit-agents-md-rules-checker/ai-kit-agents-md-rules-checker.py
  - skills/ai-kit-agents-md-rules-checker/ai_kit_agents_md_rules_checker/__init__.py
  - skills/ai-kit-agents-md-rules-checker/ai_kit_agents_md_rules_checker/cli.py
  - skills/ai-kit-agents-md-rules-checker/ai_kit_agents_md_rules_checker/makefile_checker.py
  - skills/ai-kit-agents-md-rules-checker/ai_kit_agents_md_rules_checker/remediation.py
  - skills/ai-kit-agents-md-rules-checker/ai_kit_agents_md_rules_checker/rule_checker.py
  - skills/ai-kit-agents-md-rules-checker/ai_kit_agents_md_rules_checker/rules.py
  - skills/ai-kit-agents-md-rules-checker/ai_kit_agents_md_rules_checker/stack_cache.py
  - skills/ai-kit-agents-md-rules-checker/ai_kit_agents_md_rules_checker/stack_detect.py
  - skills/ai-kit-agents-md-rules-checker/ai_kit_agents_md_rules_checker/tool_presence.py
  - tests/test_ai_kit_agents_md_rules_checker.py
  - Makefile
  - .pre-commit-config.yaml
  - pyproject.toml
findings:
  critical: 2
  warning: 3
  info: 3
  total: 8
status: issues_found
---

# Phase 6: Code Review Report

**Reviewed:** 2026-09-11
**Depth:** deep
**Files Reviewed:** 15
**Status:** issues_found

## Summary

Reviewed the full `skills/ai-kit-agents-md-rules-checker/` package (renamed
from the provisional `ai-kit-agents-md-checker`) plus its 59-test suite and
the four Makefile/`.pre-commit-config.yaml`/`pyproject.toml` registration
surfaces it added. All 59 tests pass locally; `ruff`, `pyright`, and
`vulture` are clean against the package; `pylint` (not wired as a gate for
this package by design) scores 9.82/10 with only complexity/docstring
nits. The rename is complete with zero leftover references to the
provisional name outside `.planning/`. Running the checker against this
repo's own Makefile produces real, non-trivial findings, confirming
ROADMAP SC-3's "observably distinct from plain `/agent-md-refactor`" claim.

The locked design went through five cross-AI review cycles and repeatedly
closed false-positive bugs in the Makefile chain/alias "membership" check
(raw substring matches like `lint` inside `pylint`). Direct testing found
that one class of exactly that bug is still open — for hyphenated target
names, which is every multi-word name in `REQUIRED_STATIC_TARGETS`. A
second crash-class bug was found in the stack-cache reader: it has no
exception handling around `json.load`, so a malformed cache file crashes
every future `check`/`remediate` invocation against any repo matching
that stack, contradicting the "never crash" contract this module's sibling
functions (`check_makefile_shape`) explicitly document and test for missing
files. Both are demonstrated below with a minimal reproduction, not
inferred from reading alone.

## Critical Issues

### CR-01: Corrupted/malformed stack-cache JSON crashes every future `check`/`remediate` call for that stack

**File:** `skills/ai-kit-agents-md-rules-checker/ai_kit_agents_md_rules_checker/stack_cache.py:86-98`
**Issue:** `read_stack_cache()` calls `json.load(handle)` with no exception
handling. A malformed cache file (partial write from a killed process on a
filesystem without atomic-rename guarantees, manual edit, disk corruption,
or any cause other than this module's own atomic writer) raises
`json.JSONDecodeError`, which propagates uncaught through
`get_stack_tooling()` → `_resolve_across_stacks()` →
`check_makefile_shape()` → `cli.check()`/`cli.remediate()` → `main()`,
crashing the CLI with a raw traceback instead of degrading to
`state: "stale"`/`"absent"` the way a missing `cached_at` field already
does (`except (TypeError, ValueError)` a few lines below only catches the
timestamp-parsing failure, not the JSON-parsing failure). This directly
contradicts the "never a crash" contract `check_makefile_shape`'s own
docstring makes for the missing-file case, and there is no test covering
this path. Reproduced directly:

```
$ python3 - <<'EOF'
from ai_kit_agents_md_rules_checker import stack_cache
# cache file contains "{not valid json!!"
stack_cache.read_stack_cache("python", cache_root=cache_root)
EOF
CRASH: JSONDecodeError Expecting property name enclosed in double quotes: line 1 column 2 (char 1)
```

**Fix:**
```python
def read_stack_cache(stack: str, cache_root: str | None = None) -> dict:
    path = cache_path(stack, cache_root)
    if not os.path.isfile(path):
        return {"state": "absent", "data": None}
    try:
        with open(path, encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return {"state": "stale", "data": None}
    cached_at = payload.get("cached_at")
    data = payload.get("tooling")
    ...
```

### CR-02: Word-boundary "mentions target" check still false-positives for every hyphenated required target name

**File:** `skills/ai-kit-agents-md-rules-checker/ai_kit_agents_md_rules_checker/makefile_checker.py:154-162`
**Issue:** `_recipe_mentions_target` uses `re.search(rf"\b{re.escape(name)}\b", recipe_text)`.
`\b` treats `-` as a non-word character, so it is a valid boundary on
*either* side of a hyphen. For `name="test-unit"`, the pattern matches not
only the standalone token `test-unit` but also as a prefix inside any
longer hyphenated token, e.g. `test-unit-integration-suite` — because the
boundary right after `unit` (word-char `t` → non-word-char `-`) still
satisfies `\b`. This is exactly the false-positive-membership class five
cross-AI review cycles fought to close for the `lint`/`pylint` case (now
correctly rejected, per `TestWiredCheckWordBoundary`), but it reopens for
every multi-word name in `REQUIRED_STATIC_TARGETS` (`test-unit`,
`test-integration`, `e2e-test`, `arch-test`) — precisely the names this
module's own chain/alias checks (`validate` chaining, `test`/`test-unit`
aliasing) rely on. A repo whose `validate` recipe happens to invoke an
unrelated command like `run-test-unit-smoke-checks` would be incorrectly
reported as having wired a `test-unit`-named hook into `validate`,
silently hiding a genuine gap. Reproduced directly:

```python
>>> _recipe_mentions_target("run test-unit-integration-suite", "test-unit")
True   # should be False: "test-unit" here is a prefix of a different token
```

No existing test exercises a hyphenated target name against a longer
hyphenated recipe token — all of `TestWiredCheckWordBoundary`'s cases use
single-word names (`lint`).

**Fix:** Require both ends of the match to be true token boundaries (not
a hyphen-adjacency boundary) by asserting the adjacent character, if any,
is whitespace/start/end-of-string rather than relying on `\b`:
```python
def _recipe_mentions_target(recipe_text: str, name: str) -> bool:
    pattern = rf"(?<![\w-]){re.escape(name)}(?![\w-])"
    return re.search(pattern, recipe_text) is not None
```
This keeps `lint` from matching inside `pylint` (still a word-char
boundary violation) while also keeping `test-unit` from matching inside
`test-unit-integration` (now a `-`-adjacency violation too).

## Warnings

### WR-01: Multi-target Makefile rule lines are invisible to target detection

**File:** `skills/ai-kit-agents-md-rules-checker/ai_kit_agents_md_rules_checker/makefile_checker.py:26,59-70`
**Issue:** `_TARGET_HEADER_RE = re.compile(r"^(?!\.)([A-Za-z0-9_.-]+)\s*:(?!=)(.*)$", re.MULTILINE)`
captures exactly one target name per header line. GNU Make allows
declaring several targets on one header line (`test test-unit: common`),
a valid and not-uncommon idiom. Against such a line, the character class
excludes the space between the two names, the match attempt at `^` fails
(no colon immediately after the first captured run of target-name
characters), and `finditer` never retries mid-line because the pattern is
anchored on `^`. Result: neither `test` nor `test-unit` is recorded as
present, and both are reported as missing gaps — and, per D-08, a missing
target is auto-applied without a confirmation gate, so `/agent-md-refactor`
would be handed a recommendation to add a target that already exists.
Reproduced directly: `parse_makefile_targets()` against
`"test test-unit: common\n\techo hi\n"` returns `set()`.
**Fix:** Split the captured group on whitespace before returning, e.g.
change the target-set comprehension to
`{name for m in _TARGET_HEADER_RE.finditer(text) for name in m.group(1).split()}` —
but `[A-Za-z0-9_.-]+` would need broadening to also match internal
whitespace between names (or a second regex pass) since the current
character class does not include space; a small follow-up test fixture
with a real multi-target line should back this.

### WR-02: Non-UTF-8 instruction files crash `check`/`remediate` instead of degrading

**File:** `skills/ai-kit-agents-md-rules-checker/ai_kit_agents_md_rules_checker/cli.py:53-55,82-83`
**Issue:** `resolve_instruction_text()` opens the root `AGENTS.md`/`CLAUDE.md`
and every followed link with `open(path, encoding="utf-8")` and no
exception handling. A real-world instruction file saved with a different
encoding, or containing a single stray non-UTF-8 byte (e.g. pasted from a
Windows clipboard), raises `UnicodeDecodeError` uncaught, crashing
`check()`/`remediate()` for the entire repo rather than degrading
gracefully (the module elsewhere is careful to make missing-file and
dangling-link cases non-fatal, but not bad-encoding ones).
**Fix:** Wrap both `open(...).read()` calls in
`try/except (OSError, UnicodeDecodeError)` and fall back to `""` for that
source, the same posture already used for a missing/dangling link.

### WR-03: `write_stack_cache`'s directory-creation step is outside its own error handling, contradicting `cache_update`'s "never raises" docstring

**File:** `skills/ai-kit-agents-md-rules-checker/ai_kit_agents_md_rules_checker/stack_cache.py:108-116`; `skills/ai-kit-agents-md-rules-checker/ai_kit_agents_md_rules_checker/cli.py:176-180`
**Issue:** `write_stack_cache()`'s `os.makedirs(dirname, exist_ok=True)` and
`tempfile.mkstemp(dir=dirname, ...)` calls sit before the function's own
`try/except OSError` block. A filesystem-level failure at either point
(read-only `XDG_CACHE_HOME`, permission-denied, disk full) raises an
uncaught `OSError` that propagates through `cache_update()`, which only
catches `ValueError` from `write_stack_cache()` — not the `OSError` the
module's own docstring contract ("Never raises: ... all print a one-line
stderr error and return 1") implies should be covered for any filesystem
failure during a write attempt.
**Fix:** Move `os.makedirs`/`mkstemp` inside the existing `try` block (or
add a second `try/except OSError` around them) in `write_stack_cache`, or
catch `OSError` (in addition to `ValueError`) around the
`stack_cache.write_stack_cache(...)` call in `cache_update()`.

## Info

### IN-01: Keyword-majority classifier can mark a genuinely-absent rule "present" on generic word co-occurrence

**File:** `skills/ai-kit-agents-md-rules-checker/ai_kit_agents_md_rules_checker/rule_checker.py:39-47`
**Issue:** `_classify_flat` marks a rule `present` once `n_matched >=
ceil(n_total / 2)` for `n_total >= 3` — i.e. 2 of 3 signal phrases matched
anywhere in the lowercased text, with no proximity or context check.
Every flat rule in `rules.py` has exactly 3 signals, so this path always
applies. R09's signals are `("orphan", "orphaned process", "kill")`; "kill"
is common enough in unrelated contexts ("kill the test runner if it
hangs") that co-occurring with an unrelated "orphan" mention elsewhere in
a long AGENTS.md would classify R09 `present` even though the actual
no-orphaned-processes guidance is absent. This is consistent with D-03's
explicit "start lenient" intent, but is worth tightening in a later pass
(e.g. requiring the matched phrases to appear within the same
sentence/paragraph window, or derating very common dictionary words).
**Fix:** Not urgent given the explicit first-pass mandate; consider a
co-location window or a signal-specificity weight in a follow-up.

### IN-02: `cli.main()`'s dispatch branches (`-h`/no-arg usage, unknown subcommand, `cache-update` arg-count usage) are untested

**File:** `skills/ai-kit-agents-md-rules-checker/ai_kit_agents_md_rules_checker/cli.py:187-214`; `tests/test_ai_kit_agents_md_rules_checker.py`
**Issue:** None of the 59 tests exercise `main(["-h"])`, `main([])`,
`main(["bogus"])`, or `main(["cache-update", "onlyonearg"])`. Low risk
(simple string branches) but leaves the CLI's actual entry dispatch
partially unverified by the otherwise-thorough suite.
**Fix:** Add a handful of direct `cli.main([...])` assertions for these
branches' return codes.

### IN-03: Accumulating structural-check complexity in `makefile_checker.py` is exempted from this project's own complexity gate by construction, not by review

**File:** `skills/ai-kit-agents-md-rules-checker/ai_kit_agents_md_rules_checker/makefile_checker.py:249` (`check_makefile_shape`); `pyproject.toml:61-71`
**Issue:** `pylint` reports `check_makefile_shape` at 30 locals / 19
branches / 80 statements against this project's own configured thresholds
(`max-locals = 15`, `max-branches = 12`, `max-statements = 50`). The
pre-commit `pylint` hook's `files:` regex is scoped only to
`tools/(status-line|statusline-doctor|setup)\.py` (by Plan 01's own,
deliberate must-have — only `ruff`/`py-compile`/`pyright`/`vulture`/
`unittest` are wired as gates for this package), so this is not a broken
promise, but it does mean the one function most likely to keep growing as
future plans add more structural checks has no automated complexity
tripwire at all, unlike the rest of the codebase.
**Fix:** Consider registering this package's `files:` under the `pylint`
hook too (with the same `too-many-*` disables already used elsewhere in
`pyproject.toml` if warranted), or split `check_makefile_shape` into the
static-target loop, the category loop, and the chain/alias checks as
separate top-level functions the way `check_precommit_prepush_split` and
`check_validate_order` already were split out.

---

_Reviewed: 2026-09-11_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: deep_
