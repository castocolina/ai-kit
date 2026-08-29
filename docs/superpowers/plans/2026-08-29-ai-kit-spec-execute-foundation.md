# ai-kit-spec Foundation (Rename + Shared Engine + Dispatch) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rename `review-spec*` → `ai-kit-spec-review*`, split the monolithic `review-spec.py` into a shared `ai_kit_spec` package, and add the new pieces the execute family needs (tool-availability/codegraph detection, task-affinity + context-size candidate resolution, write-capable per-CLI command builders, a generic heartbeat-emitting dispatcher) — all independently testable without yet wiring into GSD or superpowers.

**Architecture:** Pure mechanical rename + refactor first (behavior-preserving, verified by the existing 146-test suite staying green throughout), then additive new modules built on top, each with its own TDD cycle. No task in this plan depends on GSD's or superpowers' actual runtime behavior — those are Plan 2 (`ai-kit-spec-execute-gsd`) and Plan 3 (`ai-kit-spec-execute-superpowers`), written separately, each starting with its own live-verification spike where the design spec flagged one.

**Tech Stack:** Python 3 stdlib only (no new dependencies — matches the existing `review-spec.py` convention), `unittest` (matches existing test suite), bash for skill orchestration.

**Spec:** `docs/superpowers/specs/2026-08-28-ai-kit-spec-execute-design.md`

## Global Constraints

- Stdlib-only Python — no third-party dependency additions (spec §4, matches existing `review-spec.py` convention).
- Every new execute-mode command builder must be live-smoke-tested against the real installed CLI before being trusted — no builder ships on documentation alone (spec §13; the review family's grok builder had 2 real bugs found exactly this way).
- `codegraph` guidance is omitted entirely from any dispatch prompt when MCP registration can't be confirmed for that CLI — never pass a subagent prose it must guess about (spec §9).
- `grok` has no codegraph support (confirmed, not to be re-researched) — its execute-mode builder and any codegraph-guidance path must reflect this explicitly, not silently.
- Minimum 15s timeout for `codegraph sync`/`init`, regardless of typical sub-5s runtime — safety margin over optimizing the happy path (spec §9).
- `codegraph install` uses `--location=global` (registers once per machine, reused across projects) — the *check* for whether a given client is registered runs every session, scoped to whichever client is about to be dispatched; only `install` itself is conditional on that check (spec §9, corrected during brainstorming).
- All existing 146 tests in `tests/test_review_spec.py` must keep passing throughout the rename/split (Tasks 1–2), verified against the module's *actual* current loader (`importlib.util.spec_from_file_location`, see Task 2 Step 3) — not an assumed "flat import" shape.
- Every write-capable execute-mode command builder MUST take a required `target_dir` and scope writes to it via that CLI's own real, `--help`-confirmed flag (never assume a flag name without checking `--help` first) — a builder that silently writes to the orchestrator's cwd instead of a scratch dir is a real security/data-loss risk, not a style nit.
- `dispatch_with_heartbeat` must deliver the prompt EXCLUSIVELY via `communicate(input=prompt, timeout=...)` on the first call, never via a manual `proc.stdin.write()` call and never via `proc.poll()`-then-`communicate()` — both alternatives were tried and both deadlock (poll-then-communicate: the child blocks on unwritten stdin while its own stdout/stderr fills; manual `stdin.write()`: no concurrent output draining, deadlocks on any prompt larger than the OS pipe buffer). On `TimeoutExpired` retry, `input` must be `None` (CPython's `communicate()` resumes any partially-sent input internally — re-passing it would resend). Both deadlock classes were confirmed by live reproduction during Plan 1's own review pass, 2026-08-29.

---

## File Structure

```
skills/ai-kit-spec-review/                    (renamed from skills/review-spec/)
  SKILL.md                                     (renamed content, internal path refs updated)
  ai-kit-spec.py                               (new thin CLI shim, replaces review-spec.py)
  ai_kit_spec/                                 (new package)
    __init__.py
    cache.py                                   (cache_base, cache_read_json, cache_write_json, cache_is_stale)
    detection.py                               (CLI/model detection, tool-availability, codegraph MCP check)
    vendor.py                                  (infer_vendor_from_model)
    commands.py                                (ResolvedReviewer, review + execute command builders, render_reviewer_command)
    config_io.py                               (cfg_* TOML load/merge/resolve/write)
    quota.py                                   (resolve_ladder_pick, resolve_reviewers, probe_reviewer_quota, refresh_quota_cache)
    review_reports.py                          (report_has_status/parse_findings/merge_findings/render_merged_report — review-only, not used by execute)
    execute_selection.py                       (new: task-affinity + context-size candidate resolution)
    dispatch.py                                (new: generic heartbeat-emitting process dispatcher)
    cli.py                                     (main(), argparse wiring — moved from review-spec.py)
  references/
    apply-findings.md                          (unchanged content, moved)
    cli-profiles/*.md                          (unchanged content, moved)

skills/ai-kit-spec-review-checklist/           (renamed from skills/review-spec-checklist/)
skills/ai-kit-spec-review-fixer/               (renamed from skills/review-spec-fixer/)
skills/ai-kit-spec-config/                     (renamed from skills/review-spec-config/)

tests/test_ai_kit_spec.py                      (renamed from tests/test_review_spec.py, imports updated)
```

Splitting `review-spec.py` this way follows the design spec's module boundaries (§4) exactly. `review_reports.py` is an addition beyond the spec's table — it isolates review-only parsing (never used by execute) from the truly shared modules, keeping the shared-engine boundary clean per the spec's own goal ("no duplicated detection/vendor/quota logic between the two families").

---

### Task 1: Rename the skill family

**Files:**
- Rename (git mv): `skills/review-spec/` → `skills/ai-kit-spec-review/`
- Rename (git mv): `skills/review-spec-checklist/` → `skills/ai-kit-spec-review-checklist/`
- Rename (git mv): `skills/review-spec-fixer/` → `skills/ai-kit-spec-review-fixer/`
- Rename (git mv): `skills/review-spec-config/` → `skills/ai-kit-spec-config/`
- Modify: every `SKILL.md` under the 4 renamed directories (internal cross-references to sibling skill names/paths)
- Modify: `Makefile`, `.pre-commit-config.yaml`, `README.md` (references to old skill names/paths)
- Modify: `tests/test_review_spec.py` → renamed to `tests/test_ai_kit_spec.py` (only the import line changes in this task; the module it imports is still `review-spec.py` until Task 2)

**Interfaces:**
- Consumes: nothing (first task).
- Produces: the 4 renamed directories exist at their new paths; every prior cross-reference between them (e.g. `ai-kit-spec-review`'s `Step 0.7` resolving `CHECKLIST_SKILL_MD` as its own sibling) still resolves correctly under the new names.

- [ ] **Step 1: Rename the 4 skill directories**

```bash
cd /var/home/bazzite/git/personal/ai-kit
git mv skills/review-spec skills/ai-kit-spec-review
git mv skills/review-spec-checklist skills/ai-kit-spec-review-checklist
git mv skills/review-spec-fixer skills/ai-kit-spec-review-fixer
git mv skills/review-spec-config skills/ai-kit-spec-config
git mv tests/test_review_spec.py tests/test_ai_kit_spec.py
```

- [ ] **Step 2: Update cross-references to the old skill names — scoped, not a blind global replace**

**Scope this replace to skill/doc cross-references only.** A blind `review-spec\b` replace also
matches `review-spec.py` (the file Task 2 renames separately), `review-spec.toml` (the user's
existing per-project config filename — renaming it is a breaking change for any user who already
has one on disk, not in scope for this task), the cache namespace string (Task 2's own rename),
and Python docstrings inside `review-spec.py` itself (irrelevant until Task 2 moves that code).
Only touch: skill `name:` frontmatter fields, prose cross-references between the 4 skills
(e.g. "see the review-spec-checklist skill"), and path references in `Makefile`/
`.pre-commit-config.yaml`/`README.md` that point at the skill *directory*, not the script file.

```bash
grep -rln "review-spec-checklist\|review-spec-fixer\|review-spec-config\|review-spec\b" \
  skills/ai-kit-spec-review/SKILL.md skills/ai-kit-spec-review-checklist/ \
  skills/ai-kit-spec-review-fixer/ skills/ai-kit-spec-config/ \
  Makefile .pre-commit-config.yaml README.md 2>/dev/null
```

Note the grep is scoped to `skills/ai-kit-spec-review/SKILL.md` specifically (not the whole
directory) — everything else under that directory is `review-spec.py` and its own docstrings,
which Task 2 handles. For each file the grep lists, replace `review-spec-checklist` →
`ai-kit-spec-review-checklist`, `review-spec-fixer` → `ai-kit-spec-review-fixer`,
`review-spec-config` → `ai-kit-spec-config`, and bare `review-spec` (not already matched by the
three above, and NOT the `.py`/`.toml` filename or cache-string occurrences called out above) →
`ai-kit-spec-review`. Order matters — replace the three longer, more specific names first so a
later bare-`review-spec` pass doesn't corrupt them (e.g. don't let `review-spec-config` get
partially replaced into `ai-kit-spec-review-config`).

**Separate, required fix — the Python module reference uses an underscore, not a hyphen, so the
grep above never finds it.** `Makefile:31` and `.pre-commit-config.yaml:53` both invoke
`tests.test_review_spec` (confirmed live, exact lines) — that's `test_review_spec` with an
underscore, which does not match the hyphenated `review-spec\b` pattern at all. After Step 1's
`git mv tests/test_review_spec.py tests/test_ai_kit_spec.py`, both files still reference a module
that no longer exists unless fixed explicitly:

```bash
grep -rln "tests\.test_review_spec" Makefile .pre-commit-config.yaml
```

Replace `tests.test_review_spec` → `tests.test_ai_kit_spec` in both files (each currently has it
once, inside a space-separated list of other `tests.test_*` module names — replace only that one
token, leave every sibling module name in the list untouched).

- [ ] **Step 3: Verify no old name survives**

```bash
grep -rn "skills/review-spec\|reviewing-specs\|applying-review-feedback" \
  skills/ Makefile .pre-commit-config.yaml README.md 2>/dev/null
```

Expected: no output (the `reviewing-specs`/`applying-review-feedback` names were already retired
in the prior rename — this step also catches any straggler).

- [ ] **Step 4: Update the test loader's path constant, then run the full suite**

The test file's real loader (`tests/test_review_spec.py`, now `tests/test_ai_kit_spec.py`) is
`importlib.util.spec_from_file_location("review_spec", _MODULE_PATH)`, where `_MODULE_PATH =
os.path.join(os.path.dirname(__file__), "..", "skills", "review-spec", "review-spec.py")` — not
a plain `import review_spec` statement. Update only the directory segment of `_MODULE_PATH`:

```python
_MODULE_PATH = os.path.join(os.path.dirname(__file__), "..", "skills",
                             "ai-kit-spec-review", "review-spec.py")
```

The filename segment (`"review-spec.py"`) stays unchanged in this task — Task 2 renames the file
itself and updates this constant's filename segment again at that point.

```bash
python3 -m unittest tests.test_ai_kit_spec -v 2>&1 | tail -5
```

Expected: `Ran 146 tests ... OK` — the test file's own logic and its import of the still-flat
`review-spec.py` module (now at `skills/ai-kit-spec-review/review-spec.py`) are unaffected by
Task 1's pure path/name changes; only the containing directory moved.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "refactor(ai-kit-spec): rename review-spec-* family to ai-kit-spec-review-*/ai-kit-spec-config"
```

---

### Task 2: Split `review-spec.py` into the `ai_kit_spec` package

**Files:**
- Create: `skills/ai-kit-spec-review/ai_kit_spec/__init__.py`
- Create: `skills/ai-kit-spec-review/ai_kit_spec/cache.py`
- Create: `skills/ai-kit-spec-review/ai_kit_spec/vendor.py`
- Create: `skills/ai-kit-spec-review/ai_kit_spec/config_io.py`
- Create: `skills/ai-kit-spec-review/ai_kit_spec/detection.py`
- Create: `skills/ai-kit-spec-review/ai_kit_spec/commands.py`
- Create: `skills/ai-kit-spec-review/ai_kit_spec/quota.py`
- Create: `skills/ai-kit-spec-review/ai_kit_spec/review_reports.py`
- Create: `skills/ai-kit-spec-review/ai_kit_spec/cli.py`
- Create: `skills/ai-kit-spec-review/ai-kit-spec.py` (thin shim)
- Delete: `skills/ai-kit-spec-review/review-spec.py`
- Modify: `tests/test_ai_kit_spec.py` (import lines only)
- Modify: `skills/ai-kit-spec-review/SKILL.md`, `skills/ai-kit-spec-review-checklist/../frameworks` references, `skills/ai-kit-spec-config/SKILL.md` (every `TOOLS_PY` reference already points at whatever file is on disk by path, e.g. `$REVIEW_SPEC_SKILL_DIR/review-spec.py` — update the literal filename to `ai-kit-spec.py`)

**Interfaces:**
- Consumes: nothing new (pure move of Task 1's output).
- Produces (exact names every later task and every SKILL.md relies on):
  - `ai_kit_spec.cache.cache_base(env: dict) -> str`
  - `ai_kit_spec.cache.cache_read_json(path: str) -> dict | None`
  - `ai_kit_spec.cache.cache_write_json(path: str, data: dict) -> None`
  - `ai_kit_spec.cache.cache_is_stale(path: str, ttl_seconds: int) -> bool`
  - `ai_kit_spec.detection.cache_runtimes_path(env: dict) -> str`
  - `ai_kit_spec.detection.detect_installed_clis(which_fn=shutil.which) -> dict`
  - `ai_kit_spec.detection.build_runtimes_snapshot(which_fn=shutil.which, run_fn=subprocess.run) -> dict`
  - `ai_kit_spec.vendor.infer_vendor_from_model(model: str) -> str | None`
  - `ai_kit_spec.commands.ResolvedReviewer` (NamedTuple, unchanged fields)
  - `ai_kit_spec.commands.build_reviewer_command(cli: str, **params) -> str`
  - `ai_kit_spec.commands.render_reviewer_command(resolved, prompt: str) -> str`
  - `ai_kit_spec.quota.cache_quota_path(env: dict) -> str`
  - `ai_kit_spec.quota.resolve_reviewers(config, quota, source_vendor, cross_ai) -> list`
  - `ai_kit_spec.quota.probe_reviewer_quota(resolved, run_fn=subprocess.run) -> dict`
  - `ai_kit_spec.config_io.cfg_resolve(cwd: str, env: dict) -> dict`
  - `ai_kit_spec.config_io.cfg_write_toml(path: str, config: dict) -> None`
  - `ai_kit_spec.review_reports.parse_findings(report_text: str) -> list`
  - `ai_kit_spec.review_reports.merge_findings(reports: list) -> list`
  - `ai_kit_spec.cli.main(argv: list, which_fn=shutil.which, run_fn=subprocess.run) -> int`

**Complete function-to-module inventory** (every public name in the current
`skills/review-spec/review-spec.py`, confirmed via `grep -n "^def \|^class "` — this is the full
mapping Step 1 executes, not a partial sample):

| Current function/class | Target module |
|---|---|
| `cfg_local_path`, `cfg_global_path`, `cfg_load_toml`, `cfg_merge_reviewers`, `cfg_resolve`, `_toml_value`, `cfg_render_toml`, `cfg_write_toml` | `config_io.py` |
| `cache_base`, `cache_read_json`, `cache_write_json`, `cache_is_stale` | `cache.py` |
| `cache_runtimes_path`, `detect_installed_clis`, `detect_opencode_models`, `detect_cursor_agent_models`, `group_models_by_family`, `build_runtimes_snapshot` | `detection.py` |
| `infer_vendor_from_model` | `vendor.py` |
| `_reviewer_by_key`, `_to_resolved`, `_has_quota`, `resolve_ladder_pick`, `_native_ladder`, `resolve_reviewers`, `cache_quota_path`, `probe_reviewer_quota`, `refresh_quota_cache` | `quota.py` |
| `class ResolvedReviewer`, `_build_codex_command`, `_build_claude_command`, `_build_grok_command`, `_build_gemini_command`, `_build_opencode_command`, `_build_cursor_agent_command`, `build_reviewer_command`, `build_cursor_agent_model_id`, `build_reviewer_model_id`, `render_reviewer_command` | `commands.py` |
| `report_has_status`, `report_declares_issues`, `parse_findings`, `merge_findings`, `render_merged_report` | `review_reports.py` |
| `main` | `cli.py` |

Note `_reviewer_by_key`/`_to_resolved`/`_has_quota`/`_native_ladder` move into `quota.py` (not
`commands.py`) even though some build `ResolvedReviewer` instances — they're quota-resolution
internals, called only from `resolve_ladder_pick`/`resolve_reviewers`; `quota.py` imports
`ResolvedReviewer` from `commands.py` for this (`from ai_kit_spec.commands import
ResolvedReviewer`). `_to_resolved` also references `_KNOWN_REVIEWER_FIELDS` (assigned to
`config_io.py` in the constants table below) — `quota.py` needs `from ai_kit_spec.config_io
import _KNOWN_REVIEWER_FIELDS` for this, the same cross-module pattern as the `ResolvedReviewer`
import.

**Module-level constants** (the `^def \|^class ` grep above cannot see these — confirmed
separately via `grep -nE "^[A-Z_]+ *="`, every one below is real, on-disk, at the given line):

| Constant | Source line | Target module |
|---|---|---|
| `DEFAULT_POLICY` | 25 | `config_io.py` |
| `RUNTIMES_TTL_SECONDS` | 149 | `detection.py` |
| `QUOTA_TTL_SECONDS` | 150 | `quota.py` |
| `KNOWN_CLIS` | 194 | `detection.py` |
| `_MODEL_TIER_SUFFIXES` | 247 | `vendor.py` |
| `_MODEL_VENDOR_PREFIXES` | 303 | `vendor.py` |
| `NO_CONFIG_FALLBACK` | 349 | `quota.py` (constructs a `ResolvedReviewer` — import it from `commands.py`) |
| `_KNOWN_REVIEWER_FIELDS` | 352 | `config_io.py` |
| `_COMMAND_BUILDERS` | 563 | `commands.py` |
| `_UNAVAILABLE_SIGNALS` | 628 | `quota.py` |
| `_DETAIL_MAX_CHARS` | 637 | `quota.py` |
| `_SEVERITY_HEADINGS`, `_SEVERITY_RE`, `_BULLET_RE` | 768–774 | `review_reports.py` |

- [x] **Step 1: Create the package skeleton and move code verbatim, module by module**

This is a pure move — copy each function/class from `review-spec.py` into its target module
unchanged (no logic edits), fixing only intra-module references (e.g. `commands.py`'s
`render_reviewer_command` calling `build_reviewer_command`, which now lives in the same file, no
import needed; `quota.py`'s `probe_reviewer_quota` calling `commands.render_reviewer_command`,
which now needs `from ai_kit_spec.commands import render_reviewer_command`).

`ai_kit_spec/cache.py`:
```python
"""Generic JSON cache read/write with TTL staleness, shared by detection.py and quota.py."""
import json
import os
import time


def cache_base(env: dict) -> str:
    xdg = env.get("XDG_CACHE_HOME")
    base = xdg if xdg else os.path.join(env.get("HOME", ""), ".cache")
    return os.path.join(base, "ai-kit", "spec")


def cache_read_json(path: str) -> dict | None:
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def cache_write_json(path: str, data: dict) -> None:
    """Atomic write (tmp file + os.replace) so a crash mid-write never leaves a half-written
    cache file for the next reader -- preserved verbatim from the current review-spec.py
    implementation, not simplified away during the move."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, path)


def cache_is_stale(path: str, ttl_seconds: int) -> bool:
    try:
        return time.time() - os.stat(path).st_mtime >= ttl_seconds
    except OSError:
        return True
```

Note `cache_base` now returns `.../ai-kit/spec` (not `.../ai-kit/review-spec`) — this is a
deliberate, called-out namespace rename, not an incidental one. It means any cache file written
by the pre-split `review-spec.py` at the old path is orphaned (never read again) rather than
migrated — acceptable because the cache is pure derived state (runtime/quota snapshots), always
safely rebuildable by the next `detect-runtimes`/`probe-quota` call. Tests that assert the old
`.../ai-kit/review-spec` path in `tests/test_ai_kit_spec.py` (e.g. `test_cache_base_path_shape`)
must be updated to assert `.../ai-kit/spec` in this same step — update their expected path
strings, do not leave them asserting the old namespace and mark that a "pass."

`ai_kit_spec/detection.py`, `vendor.py`, `commands.py`, `config_io.py`, `quota.py`,
`review_reports.py`: move the remaining functions per the Interfaces list above, verbatim, into
their designated module, adding `from ai_kit_spec.<module> import <name>` for any cross-module
call (e.g. `detection.py`'s `cache_runtimes_path` calls `cache.cache_base`; `quota.py`'s
`probe_reviewer_quota` calls `commands.render_reviewer_command`; `quota.py`'s
`refresh_quota_cache` calls `cache.cache_is_stale`/`cache.cache_write_json`).

`ai_kit_spec/cli.py`: move `main()` verbatim, updating every internal call site from a bare name
(`cfg_resolve(...)`) to its now-qualified import (`from ai_kit_spec.config_io import cfg_resolve`
at the top, call site unchanged) — one `from ai_kit_spec.<module> import <name1>, <name2>, ...`
block per module `main()` actually calls into.

`skills/ai-kit-spec-review/ai-kit-spec.py`:
```python
#!/usr/bin/env python3
import sys

from ai_kit_spec.cli import main

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
```

`ai_kit_spec/__init__.py`: empty (marks the directory as a package).

- [x] **Step 2: Delete the old flat file**

```bash
git rm skills/ai-kit-spec-review/review-spec.py
```

- [x] **Step 3: Replace the module loader with explicit per-module imports**

`tests/test_ai_kit_spec.py`'s actual current loader (confirmed against the real file, not
assumed) is:

```python
_MODULE_PATH = os.path.join(os.path.dirname(__file__), "..", "skills",
                             "ai-kit-spec-review", "review-spec.py")


def _load_module():
    spec = importlib.util.spec_from_file_location("review_spec", _MODULE_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


rs = _load_module()
```

Delete this `_MODULE_PATH`/`_load_module()` block entirely (the file it points at no longer
exists after Step 2's `git rm`) and replace it with explicit, named imports from the new
package — never a `dir()`-based reflection loop, so a missing or misspelled export fails loudly
at import time instead of silently vanishing from `rs`.

**Import bootstrap — required, or every import below fails.** `ai_kit_spec` lives at
`skills/ai-kit-spec-review/ai_kit_spec/`, which is NOT on `sys.path` when `python3 -m unittest
tests.test_ai_kit_spec` runs from the repo root (confirmed live: `ModuleNotFoundError:
No module named 'ai_kit_spec'` without this). Add this bootstrap at the very top of
`tests/test_ai_kit_spec.py`, before any `from ai_kit_spec...` import:

```python
import os
import shlex
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills", "ai-kit-spec-review"))
```

`os` is already imported at the top of the real `tests/test_ai_kit_spec.py` (confirmed live —
its existing top-of-file block has `import importlib.util`, `import json`, `import os`, `import
subprocess`, `import tempfile`, `import time`, `import unittest`, and `from unittest import
mock`) — `sys` is NOT already there and must be added alongside `shlex`, in addition to the
`sys.path.insert` line above. `shlex` is needed because Task 5's and Task 7's tests both call
`shlex.quote(...)` directly in test bodies.

The same gap applies to every `python3 -c "from ai_kit_spec... "` smoke-test command in Tasks 3,
5, 6, and 7 below — each must be run with `PYTHONPATH=skills/ai-kit-spec-review` set (or from
inside that directory), e.g.:

```bash
PYTHONPATH=skills/ai-kit-spec-review python3 -c "from ai_kit_spec.detection import ..."
```

Now the explicit named imports:

```python
from ai_kit_spec.cache import cache_base, cache_read_json, cache_write_json, cache_is_stale
from ai_kit_spec.detection import (
    cache_runtimes_path, detect_installed_clis, detect_opencode_models,
    detect_cursor_agent_models, group_models_by_family, build_runtimes_snapshot, KNOWN_CLIS,
)
from ai_kit_spec.vendor import infer_vendor_from_model
from ai_kit_spec.quota import (
    resolve_ladder_pick, resolve_reviewers, cache_quota_path,
    probe_reviewer_quota, refresh_quota_cache, NO_CONFIG_FALLBACK,
)
from ai_kit_spec.commands import (
    ResolvedReviewer, build_reviewer_command, build_cursor_agent_model_id,
    build_reviewer_model_id, render_reviewer_command,
)
from ai_kit_spec.config_io import (
    cfg_local_path, cfg_global_path, cfg_load_toml, cfg_merge_reviewers, cfg_resolve,
    cfg_render_toml, cfg_write_toml,
)
from ai_kit_spec.review_reports import (
    report_has_status, report_declares_issues, parse_findings, merge_findings,
    render_merged_report,
)
from ai_kit_spec.cli import main

# Bare module imports too -- test classes in this file call module-qualified names like
# `detection.detect_tool_availability(...)`, `commands.build_execute_command(...)`, which need
# the module itself in scope, separately from the individual-function imports above (those only
# feed the `rs.<name>` back-compat shim below). Tasks 4/6/8 add `execute_selection`, `dispatch`,
# and `tooling_guidance` to this same line respectively, when those modules are created.
from ai_kit_spec import cache, detection, vendor, commands, config_io, quota, review_reports, cli


# Back-compat shim so every existing `rs.<name>` call in this file keeps working verbatim --
# avoids touching 146 existing test bodies for a pure module-boundary change. Explicit name
# list, not dir()-based reflection: a missing/misspelled export raises KeyError here (from
# globals()[_name]), at import time, instead of silently disappearing from `rs`.
class _RS:
    pass


rs = _RS()
for _name in (
    "cache_base", "cache_read_json", "cache_write_json", "cache_is_stale",
    "cache_runtimes_path", "detect_installed_clis", "detect_opencode_models",
    "detect_cursor_agent_models", "group_models_by_family", "build_runtimes_snapshot",
    "KNOWN_CLIS", "infer_vendor_from_model", "ResolvedReviewer", "resolve_ladder_pick",
    "resolve_reviewers", "cache_quota_path", "probe_reviewer_quota", "refresh_quota_cache",
    "NO_CONFIG_FALLBACK", "build_reviewer_command", "build_cursor_agent_model_id",
    "build_reviewer_model_id", "render_reviewer_command", "cfg_local_path", "cfg_global_path",
    "cfg_load_toml", "cfg_merge_reviewers", "cfg_resolve", "cfg_render_toml", "cfg_write_toml",
    "report_has_status", "report_declares_issues", "parse_findings", "merge_findings",
    "render_merged_report", "main",
):
    setattr(rs, _name, globals()[_name])
```

Before running the suite, grep for every direct attribute access the existing tests make on
`rs` — both private names (`grep -n "rs\._" tests/test_ai_kit_spec.py`) AND uppercase module
constants (`grep -noE "rs\.[A-Z_]+" tests/test_ai_kit_spec.py`, confirmed live to additionally
find `rs.KNOWN_CLIS` and `rs.NO_CONFIG_FALLBACK` — both now included above, but re-run this grep
after the move to catch anything else this plan's own inventory missed). Each name found needs
its own import added to the matching module's import block above and its own entry in the
`_name` tuple; the list shown here covers every name confirmed accessed as of this plan's
writing, not a guarantee against every possible one.

- [x] **Step 4: Run the full test suite — must still be exactly 146 passing (cache-path assertions updated per Step 1's note, no other logic changes)**

```bash
cd /var/home/bazzite/git/personal/ai-kit
python3 -m unittest tests.test_ai_kit_spec -v 2>&1 | tail -5
```

Expected: `Ran 146 tests ... OK`. Any failure here is a transcription bug introduced during the
move (a missed import, a renamed variable) — fix it in the target module, never in the test.

- [x] **Step 5: Update every `TOOLS_PY` filename reference in the 4 skills' SKILL.md files**

```bash
grep -rln "review-spec\.py" skills/ai-kit-spec-review*/  skills/ai-kit-spec-config/
```

For each file listed, replace the literal filename `review-spec.py` → `ai-kit-spec.py` (the
`TOOLS_PY="$REVIEW_SPEC_SKILL_DIR/review-spec.py"`-style lines from the pre-rename design). Leave
the *directory*-resolution logic (`CLAUDE_PLUGIN_ROOT`/`~/.claude/skills`/sibling-of-this-file)
untouched — Task 1 already renamed those directories.

- [x] **Step 6: Commit**

```bash
git add -A
git commit -m "refactor(ai-kit-spec): split review-spec.py into the ai_kit_spec package"
```

---

### Task 3: Tool-availability + codegraph MCP-registration detection

**Files:**
- Modify: `skills/ai-kit-spec-review/ai_kit_spec/detection.py`
- Test: `tests/test_ai_kit_spec.py`

**Interfaces:**
- Consumes: `ai_kit_spec.detection` module from Task 2 (adds to it, doesn't change existing exports).
- Produces:
  - `detect_tool_availability(which_fn=shutil.which) -> dict` — `{"rg": bool, "sd": bool, "bat": bool, "eza": bool, "fd": bool, "codegraph": bool}`
  - `resolve_agents_tooling_path(env=os.environ) -> str | None` — path to `AGENTS-TOOLING.md` if findable, else `None`
  - `_SUPPORTED_CODEGRAPH_CLIENTS: frozenset[str]` — the client names codegraph officially supports (`grok` deliberately absent, confirmed unsupported)
  - `check_codegraph_mcp_healthy(cli: str, run_fn=subprocess.run) -> bool` — checks REGISTRATION AND CURRENT CONNECTION HEALTH, not presence alone (confirmed live: a registered server can be currently disconnected). `False` immediately for any `cli` not in `_SUPPORTED_CODEGRAPH_CLIENTS`. For `claude`/`codex`: primary check is `mcp get codegraph` (exit 0 = registered, then its own output's status line is checked for a failure signal before declaring healthy); on nonzero exit, falls back to parsing `mcp list` before concluding not-registered (a nonzero `get` could mean something other than "not registered"). For `cursor-agent`/`opencode` (no `get` subcommand): `mcp list` is the only check, and the matched entry's own line is checked for a failure signal the same way. Never reads a config file directly — see Step 3's implementation, confirmed live against each installed CLI.

- [x] **Step 1: Write the failing tests**

```python
class TestDetectToolAvailability(unittest.TestCase):
    def test_reports_installed_and_missing_tools(self):
        def fake_which(name):
            return f"/usr/bin/{name}" if name in ("rg", "fd") else None
        result = detection.detect_tool_availability(which_fn=fake_which)
        self.assertEqual(result, {"rg": True, "sd": False, "bat": False,
                                   "eza": False, "fd": True, "codegraph": False})


class TestResolveAgentsToolingPath(unittest.TestCase):
    def test_env_override_wins_when_it_exists(self):
        env = {"AGENTS_TOOLING_PATH": "/custom/AGENTS-TOOLING.md", "HOME": "/home/u"}
        with unittest.mock.patch("os.path.isfile", return_value=True):
            self.assertEqual(detection.resolve_agents_tooling_path(env=env),
                              "/custom/AGENTS-TOOLING.md")

    def test_env_override_ignored_when_it_does_not_exist(self):
        # never pass an unverified path into a dispatch prompt, even one the user configured
        env = {"AGENTS_TOOLING_PATH": "/custom/AGENTS-TOOLING.md", "HOME": "/home/u"}
        with unittest.mock.patch("os.path.isfile", return_value=False):
            self.assertIsNone(detection.resolve_agents_tooling_path(env=env))

    def test_falls_back_to_conventional_home_path_if_it_exists(self):
        env = {"HOME": "/home/u"}
        with unittest.mock.patch("os.path.isfile", return_value=True):
            self.assertEqual(detection.resolve_agents_tooling_path(env=env),
                              "/home/u/.agents/AGENTS-TOOLING.md")

    def test_returns_none_when_nothing_found(self):
        env = {"HOME": "/home/u"}
        with unittest.mock.patch("os.path.isfile", return_value=False):
            self.assertIsNone(detection.resolve_agents_tooling_path(env=env))


class TestCheckCodegraphMcpHealthy(unittest.TestCase):
    def test_grok_is_always_false_no_command_attempted(self):
        # grok is confirmed unsupported by codegraph -- never even run a command for it
        result = detection.check_codegraph_mcp_healthy(
            "grok", run_fn=lambda *a, **k: (_ for _ in ()).throw(
                AssertionError("must not run any command for grok")))
        self.assertFalse(result)

    def test_unknown_cli_is_false(self):
        self.assertFalse(detection.check_codegraph_mcp_healthy("some-future-cli"))

    def test_claude_true_when_mcp_get_exits_zero_and_status_is_connected(self):
        # confirmed live (2026-08-30): `claude mcp get <name>` exits 0 and prints a
        # "Status: ✔ Connected" line when the server is registered AND healthy
        result = detection.check_codegraph_mcp_healthy(
            "claude", run_fn=lambda *a, **k: unittest.mock.MagicMock(
                returncode=0, stdout="codegraph:\n  Scope: user config\n  Status: ✔ Connected\n"))
        self.assertTrue(result)

    def test_claude_false_when_get_exits_zero_but_status_shows_failed_to_connect(self):
        # confirmed live: a REGISTERED server can still be currently disconnected -- `claude
        # mcp get` returned exit 0 with "Status: ✘ Failed to connect" observed live for a real
        # server in this session. Registered-but-unhealthy must be treated as unusable, same as
        # not-registered -- exit code 0 alone is NOT sufficient to declare it usable.
        result = detection.check_codegraph_mcp_healthy(
            "claude", run_fn=lambda *a, **k: unittest.mock.MagicMock(
                returncode=0,
                stdout="codegraph:\n  Scope: user config\n  Status: ✘ Failed to connect — CONNECTION_CLOSED\n"))
        self.assertFalse(result)

    def test_claude_false_when_get_and_list_fallback_both_say_not_registered(self):
        # confirmed live: `claude mcp get nonexistent` exits 1 with "No MCP server named...";
        # this must also cross-check `mcp list` (fallback) before concluding "not registered"
        def fake_run(cmd, **k):
            if "get" in cmd:
                return unittest.mock.MagicMock(returncode=1)
            return unittest.mock.MagicMock(returncode=0, stdout="other-tool: x - Connected\n")
        result = detection.check_codegraph_mcp_healthy("claude", run_fn=fake_run)
        self.assertFalse(result)

    def test_claude_get_succeeds_never_calls_list_fallback(self):
        # the fallback must be nonzero-exit-triggered only -- a successful get is the cheapest
        # path and must not incur a second subprocess call
        seen = []
        detection.check_codegraph_mcp_healthy(
            "claude",
            run_fn=lambda cmd, **k: seen.append(cmd) or unittest.mock.MagicMock(
                returncode=0, stdout="Status: ✔ Connected\n"))
        self.assertEqual(seen, ["claude mcp get codegraph"])

    def test_claude_get_fails_but_list_fallback_finds_it_registered_and_healthy(self):
        # the exact resilience case this fallback exists for: `get` returns nonzero for some
        # unrelated reason (CLI bug, auth hiccup) even though the server genuinely IS registered
        def fake_run(cmd, **k):
            if "get" in cmd:
                return unittest.mock.MagicMock(returncode=1)
            return unittest.mock.MagicMock(returncode=0, stdout="codegraph: x - ✔ Connected\n")
        result = detection.check_codegraph_mcp_healthy("claude", run_fn=fake_run)
        self.assertTrue(result)

    def test_codex_true_when_mcp_get_exits_zero_and_healthy(self):
        # confirmed live: codex mcp get <name> mirrors claude's exit-code contract exactly
        result = detection.check_codegraph_mcp_healthy(
            "codex", run_fn=lambda *a, **k: unittest.mock.MagicMock(
                returncode=0, stdout="Status: ✔ Connected\n"))
        self.assertTrue(result)

    def test_cursor_agent_parses_mcp_list_for_an_actual_server_name_token(self):
        # confirmed live: cursor-agent has no `mcp get`, only `mcp list` -- must parse output.
        # "codegraph" must be the actual name token (text before the first ':'), never a
        # substring match anywhere in the line
        fake_list = "codegraph: some-command - ✔ Connected\nother-tool: x - ✔ Connected\n"
        result = detection.check_codegraph_mcp_healthy(
            "cursor-agent",
            run_fn=lambda *a, **k: unittest.mock.MagicMock(returncode=0, stdout=fake_list))
        self.assertTrue(result)

    def test_cursor_agent_false_when_codegraph_only_appears_outside_the_name_token(self):
        fake_list = "other-tool: some codegraph-related command - ✔ Connected\n"
        result = detection.check_codegraph_mcp_healthy(
            "cursor-agent",
            run_fn=lambda *a, **k: unittest.mock.MagicMock(returncode=0, stdout=fake_list))
        self.assertFalse(result)

    def test_cursor_agent_false_when_codegraph_present_but_disconnected(self):
        # present (name token matches) but its own line shows a failure signal -- must be
        # treated the same as absent, not as usable
        fake_list = "codegraph: some-command - ✘ Failed to connect\n"
        result = detection.check_codegraph_mcp_healthy(
            "cursor-agent",
            run_fn=lambda *a, **k: unittest.mock.MagicMock(returncode=0, stdout=fake_list))
        self.assertFalse(result)

    def test_opencode_parses_mcp_list_the_same_way_as_cursor_agent(self):
        fake_list = "codegraph: ✔ connected\n"
        result = detection.check_codegraph_mcp_healthy(
            "opencode",
            run_fn=lambda *a, **k: unittest.mock.MagicMock(returncode=0, stdout=fake_list))
        self.assertTrue(result)

    def test_list_based_client_false_when_no_servers_configured(self):
        result = detection.check_codegraph_mcp_healthy(
            "cursor-agent",
            run_fn=lambda *a, **k: unittest.mock.MagicMock(
                returncode=0, stdout="No MCP servers configured (expected in .cursor/mcp.json or ~/.cursor/mcp.json)\n"))
        self.assertFalse(result)
```

- [x] **Step 2: Run to verify failure**

```bash
python3 -m unittest tests.test_ai_kit_spec.TestDetectToolAvailability \
  tests.test_ai_kit_spec.TestResolveAgentsToolingPath \
  tests.test_ai_kit_spec.TestCheckCodegraphMcpHealthy -v 2>&1 | tail -20
```

Expected: FAIL — `detect_tool_availability`/`resolve_agents_tooling_path`/
`check_codegraph_mcp_healthy` not defined.

- [x] **Step 3: Implement**

```python
def detect_tool_availability(which_fn=shutil.which) -> dict:
    """Deterministic presence check for the token-efficient tooling AGENTS-TOOLING.md
    recommends. codegraph is included here (binary presence only, Tier 1 of the two-tier
    check design §9 established) -- MCP registration per-client is a separate concern,
    see check_codegraph_mcp_healthy below."""
    return {name: which_fn(name) is not None
            for name in ("rg", "sd", "bat", "eza", "fd", "codegraph")}


def resolve_agents_tooling_path(env=None) -> str | None:
    """Machine-level file, not project-level -- never hardcode one user's absolute path.
    AGENTS_TOOLING_PATH env override wins IF it actually exists on disk; else the conventional
    ~/.agents/AGENTS-TOOLING.md location if it exists; else None (the caller omits tooling
    guidance entirely, same never-guess principle as the codegraph MCP check below). The
    override is validated, not trusted blindly -- a stale/misconfigured env var must never put
    an unverified path into a dispatch prompt."""
    env = env if env is not None else os.environ
    override = env.get("AGENTS_TOOLING_PATH")
    if override:
        return override if os.path.isfile(override) else None
    candidate = os.path.join(env.get("HOME", ""), ".agents", "AGENTS-TOOLING.md")
    return candidate if os.path.isfile(candidate) else None


# Confirmed live, 2026-08-30, against each installed CLI's own --help AND real invocations
# (`claude mcp list`, `codex mcp list`, `cursor-agent mcp list`, `opencode mcp list` all ran
# clean, exit 0, on this machine). grok is deliberately absent -- confirmed unsupported, never
# attempt a lookup for it.
#
# claude/codex: `mcp get <name>` is the PRIMARY check where it exists -- direct per-name lookup,
#   deterministic exit code (0 = registered, nonzero = "No MCP server named ..."). `mcp list`
#   is a FALLBACK for these two as well: `get`'s nonzero exit means "not registered" in the
#   common case, but could also mean something else went wrong with the `get` invocation itself
#   (a CLI bug, an auth hiccup) -- cross-checking via `list` before concluding "not registered"
#   costs one extra subprocess call only in the nonzero-exit case, and avoids a false negative
#   from trusting a single command's exit code alone.
# cursor-agent/opencode: no `get` subcommand exists (confirmed via --help) -- `mcp list` is the
#   ONLY check, not a fallback.
# All `mcp list` parsing looks for a line whose name token (text before the first ':') is
# exactly "codegraph"; every observed list format uses that "name: ..." convention.
#
# HEALTH, not just presence: confirmed live that a registered server can be currently
# disconnected -- `claude mcp list` showed `plugin:playwright:playwright: ... - ✘ Failed to
# connect — CONNECTION_CLOSED`, moments before `claude mcp get plugin:playwright:playwright`
# printed `Status: ✔ Connected` for that same server (connection state visibly fluctuates
# between calls). Registered-but-unhealthy must be treated the same as not-registered for the
# purpose this check serves -- telling a subagent to use a currently-broken MCP tool wastes a
# dispatch on a guaranteed failure. Both `get` and `list` output include a `Status:`/inline
# health indicator; look for an explicit failure signal in the relevant text before declaring
# healthy, never assume health from presence alone.
_SUPPORTED_CODEGRAPH_CLIENTS = frozenset({"claude", "codex", "cursor-agent", "opencode"})

_MCP_GET_COMMANDS = {"claude": "claude mcp get codegraph", "codex": "codex mcp get codegraph"}
_MCP_LIST_COMMANDS = {
    "claude": "claude mcp list", "codex": "codex mcp list",
    "cursor-agent": "cursor-agent mcp list", "opencode": "opencode mcp list",
}

# Confirmed live in claude's own output ("✔ Connected" / "✘ Failed to connect — ..."); codex/
# cursor-agent/opencode not yet observed with a real failing entry (nothing was registered to
# test against during this plan's own session) -- Task 3 Step 5's live smoke test must confirm
# these same signals appear (or find and add the real ones) for whichever of those three CLIs
# it tests against an actually-unhealthy server.
_UNHEALTHY_SIGNALS = ("✘", "failed to connect", "not connected")


def _text_is_healthy(text: str) -> bool:
    lowered = text.lower()
    return not any(signal.lower() in lowered for signal in _UNHEALTHY_SIGNALS)


def _codegraph_entry_healthy_in_list_output(stdout: str) -> bool:
    """False if no 'codegraph' entry is found at all (not registered). False if found but its
    own line shows a failure signal (registered but unhealthy -- treated the same as absent for
    this check's purpose). True only if found AND healthy."""
    for line in stdout.splitlines():
        name = line.split(":", 1)[0].strip()
        if name == "codegraph":
            return _text_is_healthy(line)
    return False


def check_codegraph_mcp_healthy(cli: str, run_fn=subprocess.run) -> bool:
    """Cheap, run every session, scoped to the one client about to be dispatched (never a
    one-time-ever check -- a client installed after codegraph's own setup would otherwise
    never get detected). Uses each client's own real MCP-inspection command, confirmed live
    against the actual installed CLI -- never reads a config file directly (a prior revision of
    this function did that and produced weak substring-match false positives). Verifies HEALTH,
    not just presence -- a registered-but-currently-disconnected server returns False here,
    same as if it were never registered at all (see the module-level note above for why).

    Where `mcp get <name>` exists (claude, codex), it is the primary, cheapest check -- one
    subprocess call, deterministic exit code, then a health-signal check on its own stdout.
    Only on a NONZERO `get` exit does this fall back to `mcp list` for that same client: a
    nonzero `get` exit usually means "not registered," but could also mean the `get` invocation
    itself hit an unrelated problem (a CLI bug, an auth hiccup) -- cross-checking via `list`
    before concluding "not registered" is one extra call in the uncommon case, in exchange for
    not trusting a single command's exit code as the only signal. cursor-agent/opencode have no
    `get` at all, so `list` is their only (not a fallback) check."""
    if cli not in _SUPPORTED_CODEGRAPH_CLIENTS:
        return False
    get_command = _MCP_GET_COMMANDS.get(cli)
    if get_command is not None:
        result = run_fn(get_command, shell=True, capture_output=True, text=True, check=False)
        if result.returncode == 0:
            return _text_is_healthy(result.stdout)
        # nonzero exit -- cross-check via `mcp list` before concluding "not registered"
    list_result = run_fn(_MCP_LIST_COMMANDS[cli], shell=True, capture_output=True, text=True,
                          check=False)
    return _codegraph_entry_healthy_in_list_output(list_result.stdout)
```

Add `import os` at the top of `detection.py` if not already present (it already imports
`shutil`/`subprocess`/`json` per the existing module).

- [x] **Step 4: Run tests to verify pass**

```bash
python3 -m unittest tests.test_ai_kit_spec.TestDetectToolAvailability \
  tests.test_ai_kit_spec.TestResolveAgentsToolingPath \
  tests.test_ai_kit_spec.TestCheckCodegraphMcpHealthy -v 2>&1 | tail -10
```

Expected: PASS, all cases.

- [x] **Step 5: Live smoke test — verify all 4 commands against a real installed client, both states**

Partially closed 2026-08-29: "not registered" (`False`) state confirmed live for both a
`get`-based client (`claude` — `claude mcp get codegraph` exits 1, falls through to
`claude mcp list`, no `codegraph` entry, returns `False`) and a `list`-only client
(`cursor-agent` — `cursor-agent mcp list` reports no MCP servers configured, returns `False`).
`codex`/`opencode` also returned `False`, consistent with codegraph not being installed
anywhere in this environment. The `True` (registered-and-healthy) state was NOT observed —
that requires codegraph actually installed via Task 7, deferred until that task runs.

The command choices above (`mcp get`/`mcp list`) are confirmed live against each CLI's own
`--help` output, but never yet run against a real registered-vs-not comparison (design spec
§14, open risk #4). Before trusting them, for at least one client with `codegraph` NOT yet
registered:

```bash
PYTHONPATH=skills/ai-kit-spec-review python3 -c "
from ai_kit_spec.detection import check_codegraph_mcp_healthy
print(check_codegraph_mcp_healthy('claude'))
"
```

Expected: `False` (matches ground truth — nothing registered yet). Then install codegraph for
that client (per Task 7 below, or manually) and re-run the same command — expected: `True`. Both
states must be observed for at least one `mcp get`-based client (claude or codex) and, if
practical, at least one `mcp list`-based client (cursor-agent or opencode) — confirm the parsed
`stdout` actually contains a `codegraph` entry once registered, matching this function's parsing
assumption. If either check disagrees with ground truth, fix the command or parsing logic and
re-run before moving on. Record which clients were confirmed (both states observed) versus only
spot-checked — this closes design spec open risk #4 for whichever clients get fully verified
here.

- [x] **Step 6: Run the full suite and commit**

```bash
python3 -m unittest tests.test_ai_kit_spec 2>&1 | grep -E "^(Ran|OK|FAILED)"
git add -A
git commit -m "feat(ai-kit-spec): add tool-availability and codegraph MCP-registration detection"
```

---

### Task 4: `execute_selection.py` — task-affinity + context-size candidate resolution

**Files:**
- Create: `skills/ai-kit-spec-review/ai_kit_spec/execute_selection.py`
- Test: `tests/test_ai_kit_spec.py`

**Interfaces:**
- Consumes: nothing from other new modules (pure functions over plain dicts/lists — keeps this
  module trivially testable and reusable by both the GSD and superpowers adapters in Plan 2/3).
- Produces:
  - `filter_by_affinity(candidates: list[dict], task_type: str, affinity_table: dict) -> list[dict]`
  - `filter_by_context(candidates: list[dict], required_context: int) -> list[dict]`
  - `resolve_execute_candidates(candidates: list[dict], task_type: str, required_context: int, affinity_table: dict, top_n_keys: list[str]) -> list[dict]` — the full pipeline: affinity ∩ context ∩ ranked by (confirmed-sufficient-context first, then `top_n_keys` order within each group)
  - `candidates_to_ladder(candidates: list[dict]) -> list[str]` — `[c["key"] for c in candidates]`; the actual adapter between this module's ranked output and `quota.py`'s real `resolve_ladder_pick(reviewers: list, ladder: list, skip_vendor: str, quota: dict, allow_same_vendor_fallback=True)` signature (confirmed against the current `review-spec.py`; `ladder` there is a plain ordered list of key strings, `reviewers` is the raw candidate dict list itself — NOT a list of `ResolvedReviewer` objects). Every caller in Plan 2/3 MUST call `resolve_ladder_pick(candidates, candidates_to_ladder(resolved), skip_vendor="", quota=quota_snapshot)` to get a live-quota-checked pick — never take `resolved[0]` directly, since `resolve_execute_candidates` only narrows/ranks and never itself checks quota.

Each candidate dict has the shape `{"key": str, "cli": str, "model": str, "task_affinity": str
| None, "context_limit": int | None}` — `task_affinity` and `context_limit` are optional fields
on top of what `ai-kit-spec-config`'s existing discovery already captures (populating them is
`ai-kit-spec-config`'s job, not this module's — this module only consumes them).

Before writing this task's tests, add `execute_selection` to the bare-module-import line at the
top of `tests/test_ai_kit_spec.py` (Task 2 Step 3): `from ai_kit_spec import cache, detection,
vendor, commands, config_io, quota, review_reports, cli, execute_selection`.

- [x] **Step 1: Write the failing tests**

```python
class TestFilterByAffinity(unittest.TestCase):
    def test_keeps_only_matching_affinity_when_any_match_exists(self):
        candidates = [{"key": "a", "task_affinity": "frontend"},
                      {"key": "b", "task_affinity": "backend"}]
        result = execute_selection.filter_by_affinity(candidates, "frontend", {})
        self.assertEqual([c["key"] for c in result], ["a"])

    def test_no_matching_affinity_returns_all_unfiltered(self):
        # never narrow to zero candidates just because none declared the right affinity --
        # affinity is a preference signal, not a hard requirement
        candidates = [{"key": "a", "task_affinity": "backend"}]
        result = execute_selection.filter_by_affinity(candidates, "frontend", {})
        self.assertEqual([c["key"] for c in result], ["a"])

    def test_candidates_with_no_declared_affinity_always_pass_through(self):
        candidates = [{"key": "a", "task_affinity": None},
                      {"key": "b", "task_affinity": "frontend"}]
        result = execute_selection.filter_by_affinity(candidates, "frontend", {})
        self.assertEqual({c["key"] for c in result}, {"a", "b"})

    def test_mixed_untagged_and_wrong_tag_excludes_only_the_wrong_tag(self):
        # an untagged candidate existing must not cause a differently-tagged candidate to be
        # silently dropped from consideration in some unexpected way, nor must the wrong-tag
        # candidate survive alongside it -- exactly the untagged one should remain
        candidates = [{"key": "untagged", "task_affinity": None},
                      {"key": "backend-tagged", "task_affinity": "backend"}]
        result = execute_selection.filter_by_affinity(candidates, "frontend", {})
        self.assertEqual([c["key"] for c in result], ["untagged"])


class TestFilterByContext(unittest.TestCase):
    def test_drops_candidates_below_required_context(self):
        candidates = [{"key": "small", "context_limit": 100_000},
                      {"key": "big", "context_limit": 1_000_000}]
        result = execute_selection.filter_by_context(candidates, required_context=500_000)
        self.assertEqual([c["key"] for c in result], ["big"])

    def test_unknown_context_limit_passes_through_not_dropped(self):
        # missing data is not the same as insufficient context -- never silently exclude a
        # candidate just because we haven't curated its context limit yet
        candidates = [{"key": "unknown", "context_limit": None}]
        result = execute_selection.filter_by_context(candidates, required_context=500_000)
        self.assertEqual([c["key"] for c in result], ["unknown"])


class TestResolveExecuteCandidates(unittest.TestCase):
    def test_full_pipeline_ranks_top_n_first(self):
        candidates = [
            {"key": "c", "task_affinity": "backend", "context_limit": 1_000_000},
            {"key": "a", "task_affinity": "backend", "context_limit": 1_000_000},
            {"key": "b", "task_affinity": "backend", "context_limit": 1_000_000},
        ]
        result = execute_selection.resolve_execute_candidates(
            candidates, task_type="backend", required_context=1000,
            affinity_table={}, top_n_keys=["b", "a"])
        self.assertEqual([c["key"] for c in result], ["b", "a", "c"])

    def test_unknown_context_ranks_after_confirmed_sufficient(self):
        # a candidate with no curated context_limit yet must never outrank one whose
        # sufficiency is actually confirmed -- "unknown" is not the same as "fits great"
        candidates = [
            {"key": "unknown", "task_affinity": "backend", "context_limit": None},
            {"key": "confirmed", "task_affinity": "backend", "context_limit": 1_000_000},
        ]
        result = execute_selection.resolve_execute_candidates(
            candidates, task_type="backend", required_context=1000,
            affinity_table={}, top_n_keys=["unknown", "confirmed"])
        self.assertEqual([c["key"] for c in result], ["confirmed", "unknown"])


class TestCandidatesToLadder(unittest.TestCase):
    def test_extracts_ordered_keys(self):
        candidates = [{"key": "b/model"}, {"key": "a/model"}]
        self.assertEqual(execute_selection.candidates_to_ladder(candidates), ["b/model", "a/model"])
```

- [x] **Step 2: Run to verify failure**

```bash
python3 -m unittest tests.test_ai_kit_spec.TestFilterByAffinity \
  tests.test_ai_kit_spec.TestFilterByContext \
  tests.test_ai_kit_spec.TestResolveExecuteCandidates \
  tests.test_ai_kit_spec.TestCandidatesToLadder -v 2>&1 | tail -20
```

Expected: FAIL — module `ai_kit_spec.execute_selection` not found.

- [x] **Step 3: Implement**

```python
"""Deterministic candidate resolution for ai-kit-spec-execute: task-type affinity + context-size
fit. Never LLM judgment per-execution -- both signals come from data curated once at
ai-kit-spec-config time (design spec Section 5)."""


def filter_by_affinity(candidates: list, task_type: str, affinity_table: dict) -> list:
    """Affinity is a preference, never a hard requirement. Precise rule (a mixed candidate set
    of tagged + untagged behaves differently from an all-mismatched set, by design -- read
    carefully): an untagged candidate (`task_affinity is None`) always passes, since it declares
    no preference at all; a tagged candidate only passes when its tag equals `task_type`. If
    that combined result is non-empty -- whether from untagged-only, matching-only, or a mix of
    both -- return exactly that set (a candidate explicitly tagged for a DIFFERENT task_type is
    excluded in favor of the untagged/matching ones, which is the whole point of having
    `task_affinity` at all). ONLY when the result is completely empty (every candidate is tagged
    for some other task_type, none untagged, none matching) does this fall back to returning
    every candidate unfiltered -- an empty result here would otherwise silently break the whole
    resolution pipeline over a curation gap, not a real unavailability.

    `affinity_table` is intentionally UNUSED in Foundation -- reserved as a hook for a future
    task_type-alias mapping (e.g. resolving "front-end-heavy" to "frontend" before comparing
    against each candidate's own `task_affinity`), not yet needed because nothing in this plan
    populates alias variants. Keeping the parameter now (rather than adding it later, which
    would change every caller's signature again) costs nothing and documents the intended
    extension point honestly instead of silently. Do not implement alias-matching logic here
    speculatively -- add it only when a real caller needs it."""
    matching = [c for c in candidates
                if c.get("task_affinity") is None or c.get("task_affinity") == task_type]
    return matching if matching else list(candidates)


def filter_by_context(candidates: list, required_context: int) -> list:
    """A candidate with no curated context_limit yet is passed through, not dropped -- missing
    data must never look identical to 'confirmed insufficient'."""
    return [c for c in candidates
            if c.get("context_limit") is None or c["context_limit"] >= required_context]


def resolve_execute_candidates(candidates: list, task_type: str, required_context: int,
                                affinity_table: dict, top_n_keys: list) -> list:
    """Full candidate-narrowing pipeline. The result's ORDER is what a caller feeds to
    quota.py's resolve_ladder_pick (via candidates_to_ladder, below) for live-availability
    escalation -- this function only narrows and ranks, it never itself probes quota.

    Ranks confirmed-sufficient-context candidates before unknown-context ones -- "unknown" must
    never look like "fits great" (matches filter_by_context's own never-drop-on-missing-data
    rule: unknown is passed through, but ranked conservatively, not favorably)."""
    narrowed = filter_by_context(
        filter_by_affinity(candidates, task_type, affinity_table), required_context)
    rank = {key: i for i, key in enumerate(top_n_keys)}
    return sorted(
        narrowed,
        key=lambda c: (c.get("context_limit") is None, rank.get(c["key"], len(top_n_keys))),
    )


def candidates_to_ladder(candidates: list) -> list:
    """Adapter to quota.py's real resolve_ladder_pick(reviewers, ladder, skip_vendor, quota)
    signature -- `ladder` there is a plain ordered list of key strings. Callers must pass this
    function's output (never `candidates` itself) as that `ladder` argument, and the same
    `candidates` list as `reviewers`, to get a live-quota-checked pick -- resolve_execute_
    candidates above only narrows/ranks, it never checks quota itself."""
    return [c["key"] for c in candidates]
```

- [x] **Step 4: Run tests to verify pass**

```bash
python3 -m unittest tests.test_ai_kit_spec.TestFilterByAffinity \
  tests.test_ai_kit_spec.TestFilterByContext \
  tests.test_ai_kit_spec.TestResolveExecuteCandidates \
  tests.test_ai_kit_spec.TestCandidatesToLadder -v 2>&1 | tail -10
```

Expected: PASS, all cases.

- [x] **Step 5: Commit**

```bash
git add -A
git commit -m "feat(ai-kit-spec): add execute_selection.py (task-affinity + context-size candidate resolution)"
```

---

### Task 5: Execute-mode command builders (codex, cursor-agent, opencode) + explicit-unimplemented for grok/claude

**Files:**
- Modify: `skills/ai-kit-spec-review/ai_kit_spec/commands.py`
- Test: `tests/test_ai_kit_spec.py`

**Interfaces:**
- Consumes: `ai_kit_spec.commands` module from Task 2 (adds a second builder catalog alongside
  the existing review one — the review catalog and its `build_reviewer_command` entry point are
  completely untouched by this task).
- Produces:
  - `_EXECUTE_COMMAND_BUILDERS: dict[str, callable]` — new catalog, parallel to the existing
    `_COMMAND_BUILDERS` (review), never merged with it
  - `build_execute_command(cli: str, **params) -> str` — same shape/error contract as
    `build_reviewer_command`: `ValueError` for an unregistered `cli`

- [ ] **Step 1: Write the failing tests**

```python
class TestBuildExecuteCommand(unittest.TestCase):
    def test_codex_uses_workspace_write_sandbox_with_target_dir(self):
        cmd = commands.build_execute_command("codex", target_dir="/scratch/run1")
        self.assertIn("--sandbox workspace-write", cmd)
        self.assertIn("-C /scratch/run1", cmd)
        self.assertIn("-m {model}", cmd)

    def test_cursor_agent_uses_force_and_workspace_not_plan_mode(self):
        cmd = commands.build_execute_command("cursor-agent", target_dir="/scratch/run1")
        self.assertIn("--force", cmd)
        self.assertIn("--workspace /scratch/run1", cmd)
        self.assertIn("--trust", cmd)
        self.assertNotIn("--mode plan", cmd)
        self.assertNotIn("--mode ask", cmd)

    def test_opencode_uses_auto_flag_and_dir(self):
        cmd = commands.build_execute_command("opencode", target_dir="/scratch/run1")
        self.assertIn("--auto", cmd)
        self.assertIn("--dir /scratch/run1", cmd)
        self.assertIn("-m {model}", cmd)

    def test_codex_requires_target_dir(self):
        with self.assertRaises(ValueError):
            commands.build_execute_command("codex")

    def test_cursor_agent_requires_target_dir(self):
        with self.assertRaises(ValueError):
            commands.build_execute_command("cursor-agent")

    def test_opencode_requires_target_dir(self):
        with self.assertRaises(ValueError):
            commands.build_execute_command("opencode")

    def test_target_dir_with_shell_metacharacters_is_quoted(self):
        cmd = commands.build_execute_command("codex", target_dir="/tmp/a b$(x)")
        self.assertIn(shlex.quote("/tmp/a b$(x)"), cmd)

    def test_grok_not_yet_implemented(self):
        # confirmed design spec open risk #3 -- mechanism not yet identified, must refuse
        # loudly rather than guess at an untested invocation
        with self.assertRaises(ValueError) as ctx:
            commands.build_execute_command("grok")
        self.assertIn("not yet verified", str(ctx.exception).lower())

    def test_claude_not_yet_implemented(self):
        with self.assertRaises(ValueError):
            commands.build_execute_command("claude")

    def test_unknown_cli_raises_value_error(self):
        with self.assertRaises(ValueError):
            commands.build_execute_command("nonexistent-cli")
```

- [ ] **Step 2: Run to verify failure**

```bash
python3 -m unittest tests.test_ai_kit_spec.TestBuildExecuteCommand -v 2>&1 | tail -20
```

Expected: FAIL — `build_execute_command` not defined.

- [ ] **Step 3: Implement**

```python
def _require_target_dir(cli_name, target_dir):
    if not target_dir:
        raise ValueError(
            f"execute-mode dispatch for {cli_name!r} requires target_dir -- a write-capable "
            f"CLI invoked without an explicit scratch directory would write to the "
            f"orchestrator's own cwd instead, which is never the intended target."
        )
    return shlex.quote(target_dir)


def _build_codex_execute_command(target_dir=None, **_params):
    """--sandbox workspace-write -C <target_dir> -- confirmed live during design: reads
    broadly (any absolute path, unrestricted), writes ONLY within target_dir."""
    quoted = _require_target_dir("codex", target_dir)
    return f"codex exec --sandbox workspace-write -C {quoted} -m {{model}}"


def _build_cursor_agent_execute_command(target_dir=None, **_params):
    """--force (alias --yolo) replaces --mode plan/ask -- confirmed live (design brainstorm)
    that --force allows writes. --workspace <path> (confirmed via `cursor-agent --help`, live
    on this machine, 2026-08-29: 'Workspace directory or saved workspace name to use (defaults
    to current working directory)') scopes it to target_dir, matching codex's -C and
    opencode's --dir below. --trust avoids an interactive workspace-trust prompt blocking a
    headless dispatch (confirmed flag: 'Trust the current workspace without prompting')."""
    quoted = _require_target_dir("cursor-agent", target_dir)
    return f"cursor-agent -p --force --trust --workspace {quoted} --model {{model}}"


def _build_opencode_execute_command(target_dir=None, **_params):
    """--auto -- confirmed present in `opencode run --help` ('auto-approve permissions that
    are not explicitly denied (dangerous!)'). --dir <path> (confirmed via `opencode run
    --help`, live on this machine, 2026-08-29: 'directory to run in') scopes it to target_dir,
    matching codex's -C and cursor-agent's --workspace above."""
    quoted = _require_target_dir("opencode", target_dir)
    return f"opencode run --auto --dir {quoted} -m {{model}}"


def _unimplemented_execute_command(cli_name):
    def _builder(**_params):
        raise ValueError(
            f"no execute-mode (write-capable) command builder for {cli_name!r} yet -- "
            f"mechanism not yet verified live (design spec open risk). Refusing rather "
            f"than guessing at an untested invocation."
        )
    return _builder


_EXECUTE_COMMAND_BUILDERS = {
    "codex": _build_codex_execute_command,
    "cursor-agent": _build_cursor_agent_execute_command,
    "opencode": _build_opencode_execute_command,
    "grok": _unimplemented_execute_command("grok"),
    "claude": _unimplemented_execute_command("claude"),
}


def build_execute_command(cli: str, **params) -> str:
    """Factory entry point for write-capable execute dispatch -- parallel to, and never
    merged with, build_reviewer_command's read-only catalog."""
    builder = _EXECUTE_COMMAND_BUILDERS.get(cli)
    if builder is None:
        raise ValueError(f"no execute-mode command builder registered for cli={cli!r}")
    return builder(**params)
```

- [ ] **Step 4: Run tests to verify pass**

```bash
python3 -m unittest tests.test_ai_kit_spec.TestBuildExecuteCommand -v 2>&1 | tail -10
```

Expected: PASS, all cases.

- [ ] **Step 5: Live smoke test each implemented builder against the real CLI**

Do not skip — this is the exact check that caught 2 real bugs in the review family's grok
builder. For each of codex, cursor-agent, opencode:

```bash
PYTHONPATH=skills/ai-kit-spec-review python3 -c "
from ai_kit_spec.commands import build_execute_command
print(build_execute_command('codex', target_dir='/tmp/scratch-test'))
"
# then run the printed command (with {model}/{target_dir} filled to real values) against a
# real scratch directory, exactly as done for the review builders during design:
# 1. confirm it can write inside target_dir
# 2. confirm it CANNOT write outside target_dir
# 3. confirm it can still read arbitrary files elsewhere
```

Repeat the SAME three checks (write inside `target_dir` succeeds, write OUTSIDE `target_dir`
fails, read elsewhere still works) for `cursor-agent` (also confirm `--force` actually grants
write access, and that `--trust` actually suppresses the one-time workspace-trust prompt) and
`opencode` (also confirm `--auto` grants write and doesn't hang waiting for approval).

**Escalation — do not skip.** `--workspace`/`--dir` are documented as selecting a *working
directory*, not as a confinement/sandbox guarantee — check #2 (write outside `target_dir` fails)
is the one that actually proves or disproves real write confinement, and it is not something to
assume from the flag's name alone. If check #2 fails for either CLI (a write outside `target_dir`
actually succeeds), that CLI's execute-mode builder MUST be replaced with
`_unimplemented_execute_command(cli_name)` (same refuse-loudly pattern already used for
grok/claude) rather than shipped with a false confinement promise — update this task's tests to
match (move that CLI's "requires target_dir"/flag-shape tests to the `test_..._not_yet_
implemented` pattern instead) and note the finding in this plan before proceeding. Do not proceed
to Task 6 with any unverified — or falsely-verified — execute-mode builder.

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "feat(ai-kit-spec): add execute-mode command builders for codex/cursor-agent/opencode"
```

---

### Task 6: `dispatch.py` — generic heartbeat-emitting process dispatcher

**Files:**
- Create: `skills/ai-kit-spec-review/ai_kit_spec/dispatch.py`
- Test: `tests/test_ai_kit_spec.py`

**Interfaces:**
- Consumes: nothing from other new modules — takes an already-built command string (from
  `commands.build_execute_command` or `build_reviewer_command`) as an opaque unit, exactly
  matching how `probe_reviewer_quota` already treats a rendered command.
- Produces:
  - `dispatch_with_heartbeat(command: str, prompt: str, heartbeat_interval: int, timeout: int, popen_fn=subprocess.Popen, time_fn=time.time, kill_fn=_default_kill_process_group, print_fn=print) -> dict` — returns `{"returncode": int | None, "stdout": str, "stderr": str, "timed_out": bool}`. No `sleep_fn` parameter — see Step 3's implementation note on why manual sleeping is unnecessary here.
  - `write_resumable_state(path: str, state: dict, write_fn=cache_write_json) -> None` — thin wrapper documenting intent, reuses `cache.cache_write_json`

**Deadlock hazards this design avoids — TWO distinct ones, both confirmed by live reproduction
during this plan's own review:**

1. Polling `proc.poll()` and only calling `communicate(input=prompt)` after the process already
   exited: the child blocks waiting to read a prompt that was never written, while its own
   stdout/stderr can fill their OS pipe buffer if it emits anything before exiting. Both sides
   wait on each other forever.
2. **A subtler one an earlier revision of this plan introduced**: writing the prompt directly
   via `proc.stdin.write(prompt)` before calling `communicate()` at all. `write()` is a plain
   blocking call with no concurrent draining of stdout/stderr — for a prompt larger than the OS
   pipe buffer (reproduced live with an ~8 MiB prompt against a real `cat` process, 2026-08-29),
   the parent blocks inside `write()` while the child's own stdout fills and blocks the child
   from reading more stdin. Same deadlock, different cause.

The only deadlock-safe pattern is to let `communicate()` itself own both directions: pass
`input=prompt` to the FIRST `communicate(input=prompt, timeout=...)` call — CPython's own
implementation writes stdin and drains stdout/stderr concurrently (via a background thread on
POSIX) and, on `TimeoutExpired`, remembers how much of `input` it already sent so a later
`communicate(timeout=...)` call (no `input=` — already delivered) resumes correctly without
re-sending or losing anything. This is the officially documented retry-on-timeout idiom, and the
only one that stays deadlock-safe for arbitrarily large prompts.

**Kill hazard also confirmed by live reproduction**: `proc.kill()` alone, under `shell=True`,
only kills the shell process — a `sleep`/long-running descendant it spawned can survive holding
the stdout/stderr pipes open, so the post-kill `communicate()` call meant to drain final output
hangs indefinitely. Fix: launch with `start_new_session=True` (puts the whole command in its own
process group) and kill the GROUP via `os.killpg`, not just the direct child.

Before writing this task's tests, add `dispatch` to the bare-module-import line at the top of
`tests/test_ai_kit_spec.py` (Task 2 Step 3, already extended by Task 4): `from ai_kit_spec import
cache, detection, vendor, commands, config_io, quota, review_reports, cli, execute_selection,
dispatch`.

- [ ] **Step 1: Write the failing tests**

```python
class TestDispatchWithHeartbeat(unittest.TestCase):
    def test_prints_timestamped_heartbeat_while_process_runs(self):
        class FakeProcess:
            def __init__(self):
                self.stdin = unittest.mock.MagicMock()
                self.returncode = 0
                self._attempts = 0

            def communicate(self, input=None, timeout=None):
                self._attempts += 1
                if self._attempts < 3:
                    raise subprocess.TimeoutExpired(cmd="x", timeout=timeout)
                return ("done", "")

        printed = []
        fake_time = iter([0, 1, 2, 3]).__next__
        dispatch.dispatch_with_heartbeat(
            "echo hi", "prompt text", heartbeat_interval=1, timeout=30,
            popen_fn=lambda *a, **k: FakeProcess(), time_fn=fake_time,
            print_fn=printed.append)
        self.assertTrue(any("still running" in line for line in printed))

    def test_delivers_prompt_via_communicate_never_via_manual_stdin_write(self):
        # manual proc.stdin.write() before communicate() is the SECOND deadlock class this
        # module must avoid (confirmed by live reproduction with a large prompt against a
        # real `cat` process) -- prompt delivery MUST go through communicate(input=...),
        # which drains stdout/stderr concurrently with writing stdin.
        class FakeProcess:
            returncode = 0
            def __init__(self):
                self.stdin = unittest.mock.MagicMock()
            def communicate(self, input=None, timeout=None):
                assert input == "the prompt", "prompt must be delivered via communicate(input=...)"
                return ("done", "")
        proc = FakeProcess()
        dispatch.dispatch_with_heartbeat(
            "cat", "the prompt", heartbeat_interval=60, timeout=30,
            popen_fn=lambda *a, **k: proc, print_fn=lambda *a: None)
        proc.stdin.write.assert_not_called()

    def test_returns_stdout_stderr_and_returncode_on_clean_completion(self):
        class FakeProcess:
            returncode = 0
            stdin = unittest.mock.MagicMock()

            def communicate(self, input=None, timeout=None):
                return ("all good", "")

        result = dispatch.dispatch_with_heartbeat(
            "echo hi", "prompt", heartbeat_interval=60, timeout=30,
            popen_fn=lambda *a, **k: FakeProcess(), print_fn=lambda *a: None)
        self.assertEqual(result, {"returncode": 0, "stdout": "all good",
                                   "stderr": "", "timed_out": False})

    def test_kills_process_group_and_still_returns_output_collected_before_the_kill(self):
        class FakeProcess:
            returncode = None
            stdin = unittest.mock.MagicMock()
            pid = 1234

            def __init__(self):
                self.killed = False

            def communicate(self, input=None, timeout=None):
                if self.killed:
                    self.returncode = -9
                    return ("partial output before kill", "")
                raise subprocess.TimeoutExpired(cmd="x", timeout=timeout)

        proc = FakeProcess()
        killed_targets = []

        def fake_kill_fn(p):
            killed_targets.append(p)
            p.killed = True

        result = dispatch.dispatch_with_heartbeat(
            "sleep 999", "prompt", heartbeat_interval=1000, timeout=1,
            popen_fn=lambda *a, **k: proc, time_fn=iter([0, 2]).__next__,
            kill_fn=fake_kill_fn, print_fn=lambda *a: None)
        self.assertTrue(result["timed_out"])
        self.assertEqual(killed_targets, [proc])
        # the timeout path must not discard output that was actually collected -- an earlier
        # revision forced stdout/stderr to "" unconditionally on timeout, losing diagnostics
        self.assertEqual(result["stdout"], "partial output before kill")
```

- [ ] **Step 2: Run to verify failure**

```bash
python3 -m unittest tests.test_ai_kit_spec.TestDispatchWithHeartbeat -v 2>&1 | tail -20
```

Expected: FAIL — module `ai_kit_spec.dispatch` not found.

- [ ] **Step 3: Implement**

```python
"""Generic process dispatcher shared by review's future JSONL-findings work and
ai-kit-spec-execute: deadlock-safe stdin prompt delivery, timestamped heartbeat while draining
output, process-GROUP timeout enforcement. Never CLI-specific -- takes an already-built command
string as an opaque unit."""
import datetime
import os
import signal
import subprocess
import time

from ai_kit_spec.cache import cache_write_json


def _default_kill_process_group(proc) -> None:
    """Kills the WHOLE process group, not just the direct child -- under shell=True, proc.kill()
    alone only kills the shell; a descendant it spawned (e.g. sleep) can survive holding
    stdout/stderr open, hanging the post-kill communicate() drain (confirmed by live
    reproduction, 2026-08-29). Requires the Popen call to have used start_new_session=True."""
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError, OSError):
        proc.kill()  # fallback: at least kill the direct child if group-kill isn't possible


def dispatch_with_heartbeat(command: str, prompt: str, heartbeat_interval: int, timeout: int,
                             popen_fn=subprocess.Popen, time_fn=time.time,
                             kill_fn=_default_kill_process_group, print_fn=print) -> dict:
    """Runs `command` (shell=True, in its own process group via start_new_session=True).

    Deadlock-safe by construction: `prompt` is delivered via `communicate(input=prompt,
    timeout=...)` -- NEVER via a manual `proc.stdin.write()` -- because CPython's own
    communicate() writes stdin and drains stdout/stderr concurrently (a background thread on
    POSIX). A direct `stdin.write()` call has no such concurrent draining and deadlocks for any
    prompt larger than the OS pipe buffer once the child's own stdout fills (confirmed by live
    reproduction with an ~8 MiB prompt against a real `cat` process, 2026-08-29 -- an earlier
    revision of this function had exactly this bug).

    On `TimeoutExpired` (raised WITHOUT killing the child), `input` is left as `None` on every
    retry call -- CPython's communicate() already remembers and resumes any partially-sent input
    internally across calls on the same Popen object; re-passing it would be wrong. Only the
    FIRST call ever passes `input=prompt`.

    On real timeout (elapsed >= `timeout`), `kill_fn` kills the whole process group (not just
    the shell), then a final `communicate()` drains and returns whatever output was actually
    collected before the kill -- never force-discarded to empty strings, which would erase real
    diagnostics from a dispatch that ran a while before timing out."""
    start = time_fn()
    proc = popen_fn(command, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                     stderr=subprocess.PIPE, text=True, start_new_session=True)
    pending_input = prompt
    while True:
        elapsed = time_fn() - start
        remaining = timeout - elapsed
        if remaining <= 0:
            kill_fn(proc)
            # Bounded, not indefinite -- killing the process group doesn't guarantee every
            # pipe-holding descendant exits immediately (a grandchild that outlived its own
            # setsid parent can still hold stdout/stderr open); confirmed by live reproduction
            # to hang the drain otherwise. 5s is generous for draining an already-terminated
            # process's remaining buffered output.
            try:
                stdout, stderr = proc.communicate(timeout=5)
            except subprocess.TimeoutExpired as exc:
                stdout, stderr = exc.stdout or "", exc.stderr or ""
            return {"returncode": proc.returncode, "stdout": stdout, "stderr": stderr,
                    "timed_out": True}
        try:
            stdout, stderr = proc.communicate(input=pending_input,
                                               timeout=min(heartbeat_interval, remaining))
        except subprocess.TimeoutExpired:
            pending_input = None  # already delivered/buffered internally -- never re-send
            ts = datetime.datetime.now().strftime("%H:%M:%S")
            print_fn(f"[{ts}] still running, {int(elapsed)}s elapsed")
            continue
        return {"returncode": proc.returncode, "stdout": stdout, "stderr": stderr,
                "timed_out": False}


def write_resumable_state(path: str, state: dict, write_fn=cache_write_json) -> None:
    """Persists the minimal state needed to resume after a quota-exhaustion auto-wake
    (design spec Section 10): framework, plan/phase reference, candidates already tried,
    iteration. A thin, documented wrapper around cache_write_json -- the resumability
    guarantee lives in what the caller puts in `state`, not in this function's own logic."""
    write_fn(path, state)
```

- [ ] **Step 4: Run tests to verify pass**

```bash
python3 -m unittest tests.test_ai_kit_spec.TestDispatchWithHeartbeat -v 2>&1 | tail -10
```

Expected: PASS, all cases.

- [ ] **Step 5: Live smoke test against a real stdin-reading process — proves the deadlock fix, not just the mocks**

The unit tests above use fakes and cannot, by construction, prove the real deadlock is gone —
only a real OS-level process with real pipes can. Run:

```bash
PYTHONPATH=skills/ai-kit-spec-review python3 -c "
from ai_kit_spec.dispatch import dispatch_with_heartbeat
# 'cat' reads all of stdin, then echoes it to stdout on EOF -- a faithful stand-in for a
# stdin-driven CLI that blocks until the whole prompt is delivered.
result = dispatch_with_heartbeat('cat', 'hello from the prompt', heartbeat_interval=5, timeout=10)
assert result == {'returncode': 0, 'stdout': 'hello from the prompt', 'stderr': '', 'timed_out': False}, result
print('OK: real stdin round-trip succeeded, no deadlock')
"
```

Then the LARGE-prompt case — this is the one that actually distinguishes the deadlock-safe
`communicate(input=...)` delivery from the broken manual-`stdin.write()` version an earlier
revision of this plan had (confirmed live: the manual-write version hangs on exactly this case,
this version must not):

```bash
PYTHONPATH=skills/ai-kit-spec-review python3 -c "
from ai_kit_spec.dispatch import dispatch_with_heartbeat
big_prompt = 'x' * (8 * 1024 * 1024)  # 8 MiB -- well past any OS pipe buffer (typically 64KiB)
result = dispatch_with_heartbeat('cat', big_prompt, heartbeat_interval=5, timeout=30)
assert result['timed_out'] is False, result
assert result['stdout'] == big_prompt, 'output truncated or corrupted'
print('OK: large-prompt round-trip succeeded, no deadlock')
"
```

Then a real timeout case, confirming the process-GROUP kill path against an actual
shell-spawned long-running descendant (not a fake `sleep 999` that a mock can trivially satisfy
— this specifically catches the shell=True kill-only-the-shell hazard):

```bash
PYTHONPATH=skills/ai-kit-spec-review python3 -c "
from ai_kit_spec.dispatch import dispatch_with_heartbeat
result = dispatch_with_heartbeat('sleep 30', '', heartbeat_interval=1, timeout=2)
assert result['timed_out'] is True, result
print('OK: real process group actually killed on timeout, communicate() did not hang')
"
```

If any assertion fails, the implementation still has a deadlock or a timeout-handling bug — fix
it and re-run all three before proceeding; do not trust the mocked unit tests alone for this
module.

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "feat(ai-kit-spec): add dispatch.py (heartbeat-emitting process dispatcher)"
```

---

### Task 7: codegraph install/init orchestration helper

**Files:**
- Modify: `skills/ai-kit-spec-review/ai_kit_spec/detection.py`
- Test: `tests/test_ai_kit_spec.py`

**Interfaces:**
- Consumes: `check_codegraph_mcp_healthy` (Task 3), `run_fn=subprocess.run` (existing convention).
- Produces:
  - `ensure_codegraph_registered(cli: str, run_fn=subprocess.run, check_fn=check_codegraph_mcp_healthy) -> bool` — returns whether the client is registered after this call (runs `codegraph install --target=<cli> --location=global --yes --init` only if `check_fn(cli)` was `False`; never re-installs an already-registered client; still returns `False` for `grok`/unsupported clients without attempting anything)
  - `build_codegraph_index_command(target_dir: str) -> str` — `f"cd {target_dir} && (codegraph sync || codegraph init)"`
  - `CODEGRAPH_INDEX_TIMEOUT_SECONDS = 15` (module constant — the agreed minimum, regardless of the typically-faster real runtime)

- [ ] **Step 1: Write the failing tests**

```python
class TestEnsureCodegraphRegistered(unittest.TestCase):
    def test_skips_install_when_already_registered(self):
        calls = []
        detection.ensure_codegraph_registered(
            "claude", run_fn=lambda *a, **k: calls.append(a) or unittest.mock.MagicMock(returncode=0),
            check_fn=lambda cli: True)
        self.assertEqual(calls, [])

    def test_installs_when_not_registered(self):
        calls = []
        def fake_run(cmd, **k):
            calls.append(cmd)
            return unittest.mock.MagicMock(returncode=0)
        detection.ensure_codegraph_registered("claude", run_fn=fake_run, check_fn=lambda cli: False)
        self.assertEqual(len(calls), 1)
        self.assertIn("--location=global", calls[0])
        self.assertIn("--target=claude", calls[0])
        self.assertIn("--yes", calls[0])

    def test_grok_never_attempts_install(self):
        calls = []
        result = detection.ensure_codegraph_registered(
            "grok", run_fn=lambda *a, **k: calls.append(a),
            check_fn=lambda cli: False)
        self.assertEqual(calls, [])
        self.assertFalse(result)


class TestBuildCodegraphIndexCommand(unittest.TestCase):
    def test_tries_sync_then_init(self):
        cmd = detection.build_codegraph_index_command("/repo/root")
        self.assertIn("cd /repo/root", cmd)
        self.assertIn("codegraph sync || codegraph init", cmd)

    def test_target_dir_with_shell_metacharacters_is_quoted(self):
        cmd = detection.build_codegraph_index_command("/tmp/a b$(x)")
        self.assertIn(shlex.quote("/tmp/a b$(x)"), cmd)

    def test_minimum_timeout_constant(self):
        self.assertEqual(detection.CODEGRAPH_INDEX_TIMEOUT_SECONDS, 15)
```

- [ ] **Step 2: Run to verify failure**

```bash
python3 -m unittest tests.test_ai_kit_spec.TestEnsureCodegraphRegistered \
  tests.test_ai_kit_spec.TestBuildCodegraphIndexCommand -v 2>&1 | tail -20
```

Expected: FAIL — `ensure_codegraph_registered`/`build_codegraph_index_command` not defined.

- [ ] **Step 3: Implement**

Add `import shlex` to `detection.py`'s existing top-of-file imports (it already has `shutil`,
`subprocess`, `json`, `os` from Tasks 2–3) — needed for `build_codegraph_index_command`'s path
quoting below.

```python
CODEGRAPH_INDEX_TIMEOUT_SECONDS = 15  # agreed minimum, safety margin over the typical <5s runtime


def ensure_codegraph_registered(cli: str, run_fn=subprocess.run,
                                 check_fn=check_codegraph_mcp_healthy) -> bool:
    """Runs every session, scoped to `cli` -- never a one-time-ever check (design spec §9,
    corrected during brainstorming: a client installed after codegraph's own setup would
    otherwise never get detected). Only `install` itself is conditional on check_fn's result."""
    if check_fn(cli):
        return True
    if cli not in _SUPPORTED_CODEGRAPH_CLIENTS:
        return False  # grok and any other unsupported client -- never attempt install
    run_fn(f"codegraph install --target={cli} --location=global --yes --init",
           shell=True, capture_output=True, text=True, check=False)
    return check_fn(cli)


def build_codegraph_index_command(target_dir: str) -> str:
    """sync first (fast, incremental), init as fallback (first-ever index for this repo) --
    confirmed real usage from the design discussion. Caller (the orchestrator, never the
    sandboxed reviewer/executor subagent) runs this with a minimum
    CODEGRAPH_INDEX_TIMEOUT_SECONDS timeout, before dispatch. target_dir is shell-quoted --
    this string is built for shell=True execution, same as every other command builder in this
    package; an unquoted path with a space or shell metacharacter would break or inject."""
    return f"cd {shlex.quote(target_dir)} && (codegraph sync || codegraph init)"
```

- [ ] **Step 4: Run tests to verify pass**

```bash
python3 -m unittest tests.test_ai_kit_spec.TestEnsureCodegraphRegistered \
  tests.test_ai_kit_spec.TestBuildCodegraphIndexCommand -v 2>&1 | tail -10
```

Expected: PASS, all cases.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat(ai-kit-spec): add codegraph install/init orchestration helper"
```

---

### Task 8: Tool-preference guidance decision helper

**Files:**
- Create: `skills/ai-kit-spec-review/ai_kit_spec/tooling_guidance.py`
- Test: `tests/test_ai_kit_spec.py`

**Interfaces:**
- Consumes: `detect_tool_availability`, `resolve_agents_tooling_path`,
  `check_codegraph_mcp_healthy` (all Task 3).
- Produces:
  - `build_tooling_guidance(cli: str, tool_availability: dict, agents_tooling_path: str | None, codegraph_registered: bool) -> str` — returns the exact prose block to append to a dispatch prompt, or `""` when nothing confirmed applies (never a guess-inducing partial mention). codegraph guidance requires BOTH `tool_availability.get("codegraph")` truthy AND `codegraph_registered` truthy — either signal alone is insufficient (binary presence without MCP registration, or a registration claim without a confirmed-installed binary, are each an inconsistent/stale-input scenario this function must not act on).

Before writing this task's tests, add `tooling_guidance` to the bare-module-import line at the
top of `tests/test_ai_kit_spec.py` (Task 2 Step 3, already extended by Tasks 4 and 6).

- [ ] **Step 1: Write the failing tests**

```python
class TestBuildToolingGuidance(unittest.TestCase):
    def test_empty_when_nothing_confirmed(self):
        result = tooling_guidance.build_tooling_guidance(
            "grok", tool_availability={}, agents_tooling_path=None, codegraph_registered=False)
        self.assertEqual(result, "")

    def test_points_to_agents_tooling_file_when_present(self):
        result = tooling_guidance.build_tooling_guidance(
            "claude", tool_availability={}, agents_tooling_path="/home/u/.agents/AGENTS-TOOLING.md",
            codegraph_registered=False)
        self.assertIn("/home/u/.agents/AGENTS-TOOLING.md", result)

    def test_mentions_codegraph_explore_only_when_registered(self):
        result = tooling_guidance.build_tooling_guidance(
            "claude", tool_availability={"codegraph": True}, agents_tooling_path=None,
            codegraph_registered=True)
        self.assertIn("codegraph_explore", result)

    def test_omits_codegraph_explore_when_not_registered_even_if_binary_present(self):
        # binary presence alone is not enough -- MCP registration is the real gate
        result = tooling_guidance.build_tooling_guidance(
            "grok", tool_availability={"codegraph": True}, agents_tooling_path=None,
            codegraph_registered=False)
        self.assertNotIn("codegraph_explore", result)

    def test_omits_codegraph_explore_when_registered_but_binary_not_detected(self):
        # a stale/inconsistent registration claim without a confirmed-installed binary must
        # not be acted on either -- both signals are required, not just one
        result = tooling_guidance.build_tooling_guidance(
            "claude", tool_availability={"codegraph": False}, agents_tooling_path=None,
            codegraph_registered=True)
        self.assertNotIn("codegraph_explore", result)

    def test_grok_never_gets_codegraph_explore_even_with_inconsistent_true_inputs(self):
        # defense in depth -- grok is confirmed unsupported; a caller passing a stale/wrong
        # codegraph_registered=True must still never leak codegraph guidance for grok
        result = tooling_guidance.build_tooling_guidance(
            "grok", tool_availability={"codegraph": True}, agents_tooling_path=None,
            codegraph_registered=True)
        self.assertNotIn("codegraph_explore", result)
```

- [ ] **Step 2: Run to verify failure**

```bash
python3 -m unittest tests.test_ai_kit_spec.TestBuildToolingGuidance -v 2>&1 | tail -20
```

Expected: FAIL — module `ai_kit_spec.tooling_guidance` not found.

- [ ] **Step 3: Implement**

```python
"""Builds the tool-preference prose appended to a dispatch prompt -- never includes anything
not deterministically confirmed for the target CLI (design spec §9: 'never pass a subagent
prose it would have to infer/guess about when the answer should be certain')."""


def build_tooling_guidance(cli: str, tool_availability: dict, agents_tooling_path,
                            codegraph_registered: bool) -> str:
    lines = []
    if agents_tooling_path:
        lines.append(f"Read {agents_tooling_path} for confirmed tool preferences on this machine.")
    # Hard-omit grok regardless of what the caller passes for codegraph_registered -- confirmed
    # unsupported (design spec, Global Constraints above). Defense in depth: check_codegraph_
    # mcp_registered("grok") already always returns False, but this function must never emit
    # codegraph guidance for grok even if a caller passes an inconsistent/stale True by mistake.
    if cli != "grok" and codegraph_registered and tool_availability.get("codegraph"):
        lines.append(
            "codegraph_explore (MCP) is available and confirmed registered for this CLI -- "
            "prefer it over broad file reads for architecture/cross-reference questions, "
            "unless another tool is genuinely simpler for a specific lookup."
        )
    return "\n".join(lines)
```

- [ ] **Step 4: Run tests to verify pass**

```bash
python3 -m unittest tests.test_ai_kit_spec.TestBuildToolingGuidance -v 2>&1 | tail -10
```

Expected: PASS, all cases.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat(ai-kit-spec): add tooling_guidance.py (confirmed-only tool-preference prose)"
```

---

### Task 9: `ai-kit-spec-config` discovery surfaces tool-availability data

**Scope, stated honestly:** this task adds `detect-tools` output ONLY. It does NOT capture
`task_affinity` or `context_limit` for any model/CLI — `ai-kit-spec-config`'s existing wizard
currently records a `strength = ui|coding|planning` field, not a `frontend|backend|mixed`
affinity, and records no context-limit field at all. `execute_selection.py` (Task 4) accepts
both as optional inputs and degrades correctly when they're absent (`None` passes through
unfiltered/unranked-preferentially, per Task 4's own tests) — but until a real producer exists,
every `ai-kit-spec-execute` candidate reaching `resolve_execute_candidates` will have
`task_affinity=None, context_limit=None` for 100% of candidates, meaning affinity/context
filtering is a no-op in practice today. Populating these two fields for real is explicitly
Plan 2/3's (or a later increment's) job, not this task's — do not read this task's name as
implying otherwise.

**Files:**
- Modify: `skills/ai-kit-spec-config/SKILL.md`
- Modify: `skills/ai-kit-spec-review/ai_kit_spec/cli.py` (extend the `detect-runtimes`-equivalent
  subcommand's output, or add a new `detect-tools` subcommand — whichever keeps `main()`'s
  existing subcommand list additive, never breaking the existing `detect-runtimes` output shape)
- Test: `tests/test_ai_kit_spec.py`

**Interfaces:**
- Consumes: `detect_tool_availability` (Task 3).
- Produces: `main()` gains a `detect-tools` subcommand that prints
  `json.dumps(detect_tool_availability())` — mirrors the existing `detect-runtimes` subcommand's
  shape (no flags needed, plain JSON to stdout).

- [ ] **Step 1: Write the failing test**

```python
class TestMainCliDetectTools(unittest.TestCase):
    def test_detect_tools_subcommand_prints_json(self):
        import io, contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            cli.main(["detect-tools"], which_fn=lambda name: "/usr/bin/x" if name == "rg" else None)
        result = json.loads(buf.getvalue())
        self.assertEqual(
            result,
            {"rg": True, "sd": False, "bat": False, "eza": False, "fd": False, "codegraph": False},
        )
```

- [ ] **Step 2: Run to verify failure**

```bash
python3 -m unittest tests.test_ai_kit_spec.TestMainCliDetectTools -v 2>&1 | tail -10
```

Expected: FAIL — `detect-tools` not a recognized subcommand.

- [ ] **Step 3: Implement**

In `ai_kit_spec/cli.py`, add alongside the existing `detect-runtimes` subparser registration:

```python
    sub.add_parser("detect-tools")
```

And in `main()`'s dispatch body, alongside the existing `if args.command == "detect-runtimes":`
branch:

```python
    if args.command == "detect-tools":
        print(json.dumps(detect_tool_availability(which_fn=which_fn)))
        return 0
```

Add `from ai_kit_spec.detection import detect_tool_availability` to `cli.py`'s import block —
this is a NEW import added in this task, not already present from Task 2's move (Task 2 only
imported the names `main()` called at that point, before Task 3 added `detect_tool_availability`
to `detection.py`).

- [ ] **Step 4: Run tests to verify pass**

```bash
python3 -m unittest tests.test_ai_kit_spec.TestMainCliDetectTools -v 2>&1 | tail -10
```

Expected: PASS.

- [ ] **Step 5: Wire into `ai-kit-spec-config`'s discovery step**

In `skills/ai-kit-spec-config/SKILL.md`'s Step 1 (Detect), add alongside the existing
`detect-runtimes` call:

```bash
python3 "$TOOLS_PY" detect-tools
```

Parse the printed JSON; when asking the user optional per-reviewer/per-executor questions later
in the wizard, mention which of `rg`/`sd`/`bat`/`eza`/`fd`/`codegraph` are present on this
machine — informational only, this task does not add new wizard questions, just surfaces the
data `ai-kit-spec-execute` (Plan 2/3) will need later.

- [ ] **Step 6: Run the full suite and commit**

```bash
python3 -m unittest tests.test_ai_kit_spec 2>&1 | grep -E "^(Ran|OK|FAILED)"
git add -A
git commit -m "feat(ai-kit-spec-config): surface detect-tools output during discovery"
```

---

### Task 10: Final integration — skill-judge, full suite, close out

**Files:**
- No new files — verification-only task.

- [ ] **Step 1: Run the full test suite one final time**

```bash
cd /var/home/bazzite/git/personal/ai-kit
python3 -m unittest tests.test_ai_kit_spec -v 2>&1 | tail -15
```

Expected: `OK`, test count = 146 (Task 1–2 baseline) + every new test added in Tasks 3–9.

- [ ] **Step 2: Run `skill-judge` against the 4 renamed skills**

Invoke the `skill-judge` skill against `ai-kit-spec-review`, `ai-kit-spec-review-checklist`,
`ai-kit-spec-review-fixer`, `ai-kit-spec-config` — confirm the rename (Task 1) and the
`TOOLS_PY` filename update (Task 2, Step 5) didn't regress any of the scores already achieved
in the prior review-spec skill-judge pass. Fix any regression found before proceeding.

- [ ] **Step 3: Confirm every open risk from the design spec that this plan could close is closed or explicitly still open**

Re-read `docs/superpowers/specs/2026-08-28-ai-kit-spec-execute-design.md` §14. This plan
addresses: open risk #4 (MCP registration detection — resolved by using each client's own real
`mcp get`/`mcp list` command rather than reading config files at all, closed for whichever
clients Task 3 Step 5 smoke-tested both states for, still open for the rest) and makes real
progress on open risk #3 (execute-mode
builders — grok/claude explicitly still open, refusing loudly rather than silently; codex closed
by construction; cursor-agent and opencode closed ONLY IF Task 5 Step 5's write-confinement
negative test actually passed for each — if either failed that test and was demoted to
`_unimplemented_execute_command` per Task 5's escalation clause, note that here as still-open
too, not closed). Open risks #1, #2, #5 remain entirely for Plan 2 (GSD adapter) — this plan
never touches GSD.

- [ ] **Step 4: Final commit**

```bash
git add -A
git commit -m "chore(ai-kit-spec): foundation plan complete -- rename, shared engine, execute-mode dispatch"
```
