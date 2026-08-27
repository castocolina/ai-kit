# review-spec Cross-AI Reviewer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `review-spec`'s reviewer selection config-driven, quota-aware,
and optionally cross-vendor, instead of hardcoded to a single Claude
subagent.

**Architecture:** One new stdlib-only Python module, `tools/review-spec.py`
(mirrors `tools/status-line.py`'s file layout and testing style — one flat
file, `importlib`-loaded by its test module since the filename is
hyphenated; unlike `status-line.py` this module imports `tomllib`
unguarded at module scope rather than degrading to `{}` on import failure,
since this repo's `.python-version` pins 3.12 and `tomllib` has been
stdlib since 3.11 — no fallback path is reachable), holds config
load/write, cache read/write, CLI/model detection, policy resolution, and
cross-reviewer findings merge as pure, independently unit-tested functions.
Two skills are renamed (`reviewing-specs` → `review-spec-checklist`,
`applying-review-feedback` → `review-spec-fixer`) and one is added
(`review-spec-config`, an interactive setup wizard). `review-spec/SKILL.md`
gains a new Step 0.7 and a Step 1.5, both driving `tools/review-spec.py`'s
CLI entrypoint via `Bash`, and a `mktemp -d` fix for a pre-existing
temp-file collision bug.

**Tech Stack:** Python 3.12 (`.venv`), stdlib only (`tomllib` for reading
TOML — read-only, so this plan adds a small hand-rolled TOML writer since
there is no stdlib writer and this repo has zero external dependencies;
`json` for cache files), `unittest` (this repo's test runner, not pytest —
`Makefile`'s `test:` target confirms this).

**Spec:** `docs/superpowers/specs/2026-08-27-review-spec-cross-ai-design.md`

## Global Constraints

- Zero new external dependencies (no PyYAML, no `tomli-w`) — matches
  `pyproject.toml`'s explicit "runtime is stdlib-only" comment.
- Config: TOML, `./.aikit/review-spec.toml` (local) → `strategy` field
  decides `local-only` vs `global-merge` (default) against
  `${XDG_CONFIG_HOME:-$HOME/.config}/ai-kit/review-spec.toml` (global).
- Cache: JSON, `${XDG_CACHE_HOME:-$HOME/.cache}/ai-kit/review-spec/` —
  `runtimes.json` (near-static) and `quota.json` (short-TTL) as separate
  files.
- Fixer stays Claude-only always — this plan never adds cross-AI dispatch
  for the fixer, only the reviewer.
- Test runner for this repo: `.venv/bin/python3 -m unittest tests.test_review_spec[.Class[.test]] -v` (NOT pytest).

---

### Task 1: Rename `reviewing-specs` → `review-spec-checklist`, `applying-review-feedback` → `review-spec-fixer`

**Files:**
- Move: `skills/reviewing-specs/` → `skills/review-spec-checklist/`
- Move: `skills/applying-review-feedback/` → `skills/review-spec-fixer/`
- Modify: `skills/review-spec-checklist/SKILL.md` (frontmatter `name:`)
- Modify: `skills/review-spec-fixer/SKILL.md` (frontmatter `name:`)
- Modify: `skills/review-spec/SKILL.md` (every reference to the old names)
- Test: none (mechanical rename + grep verification, no code)

**Interfaces:**
- Produces: the skill names `review-spec-checklist` and `review-spec-fixer`,
  which Task 11's orchestrator changes reference directly.

- [ ] **Step 1: Move the directories**

```bash
git mv skills/reviewing-specs skills/review-spec-checklist
git mv skills/applying-review-feedback skills/review-spec-fixer
```

- [ ] **Step 2: Fix the frontmatter `name:` field in each moved skill**

In `skills/review-spec-checklist/SKILL.md`, the frontmatter currently
starts:

```yaml
---
name: reviewing-specs
```

Change to:

```yaml
---
name: review-spec-checklist
```

In `skills/review-spec-fixer/SKILL.md`, the frontmatter currently starts:

```yaml
---
name: applying-review-feedback
```

Change to:

```yaml
---
name: review-spec-fixer
```

- [ ] **Step 3: Fix every reference inside `skills/review-spec/SKILL.md`**

Find every occurrence with:

```bash
grep -n "reviewing-specs\|applying-review-feedback" skills/review-spec/SKILL.md
```

Replace each `"reviewing-specs"` (skill-name string, e.g. `Invoke the Skill
tool with skill name "reviewing-specs"`, the `SEEDS_DIR` fallback path
`.../reviewing-specs/references/frameworks/`, and the Constants section's
`**Reviewer skill:** \`reviewing-specs\``) with `"review-spec-checklist"`
(and the matching path segment `review-spec-checklist/references/frameworks/`),
and every `"applying-review-feedback"` (including the Constants section's
`**Fixer skill:** \`applying-review-feedback\``) with
`"review-spec-fixer"`.

- [ ] **Step 4: Fix the moved skills' own self-references**

The two `git mv`s in Step 1 only moved directories — they didn't touch the
*content* of the moved files, so each moved skill still mentions the
*other* skill's old name in its own prose. Verified live against this
repo (`grep -n "reviewing-specs\|applying-review-feedback"` inside each
file) — fix every line below:

- `skills/review-spec-checklist/SKILL.md` line 13: `task
  (\`applying-review-feedback\`).` → `task (\`review-spec-fixer\`).`
- `skills/review-spec-fixer/SKILL.md`:
  - Frontmatter `description:` (line 3): both occurrences of
    `reviewing-specs` (`"a review report from \`reviewing-specs\`"`, and
    the orchestrator example) → `review-spec-checklist`.
  - Line 8: `flagged by \`reviewing-specs\`.` → `flagged by
    \`review-spec-checklist\`.`
- `skills/review-spec-checklist/references/frameworks/SCHEMA.md` line 118:
  `(\`applying-review-feedback\`).` → `(\`review-spec-fixer\`).`

- [ ] **Step 5: Verify no stale references remain — and fix the ones that need it**

```bash
grep -rln "reviewing-specs\|applying-review-feedback" --include="*.md" .
```

Run this **after** Steps 1–4. Verified live against this repo's actual
current state (pre-rename), the full match set is these **17 files**:

```
docs/prds/000-ai-kit-overhaul-requirements.md
docs/superpowers/plans/2026-06-14-e1-review-spec-skill.md
docs/superpowers/plans/2026-06-24-wizard-redesign-B-ui.md
docs/superpowers/plans/2026-08-27-review-spec-cross-ai.md
docs/superpowers/specs/2026-08-27-review-spec-cross-ai-design.md
README.md
skills/applying-review-feedback/evals/test-scenarios.md
skills/applying-review-feedback/SKILL.md
skills/reviewing-specs/evals/orchestrator-integration.md
skills/reviewing-specs/evals/test-scenarios.md
skills/reviewing-specs/references/frameworks/SCHEMA.md
skills/reviewing-specs/SKILL.md
skills/review-spec/evals/01-superpowers-plan-routes-writing-plans.md
skills/review-spec/evals/02-gsd-plan-routes-native-cmd.md
skills/review-spec/evals/03-generic-doc-direct-edit.md
skills/review-spec/evals/04-ambiguous-detection-fallback.md
skills/review-spec/SKILL.md
```

By the time you run the grep (after Steps 1–4), the paths have already
moved and 6 of these are already fixed (`skills/review-spec/SKILL.md` by
Step 3; the two self-reference files by Step 4), so what you'll actually
see is the **16** post-move paths, split into two groups:

1. **MUST fix (11 files)** — living documentation and active test
   fixtures, not history:
   - `README.md` lines 28, 29, 34 (three separate mentions — `reviewing-specs`→`review-spec-checklist`, `applying-review-feedback`→`review-spec-fixer`, including the one inside the `review-spec` row's description).
   - `skills/review-spec/evals/01-superpowers-plan-routes-writing-plans.md`, `02-gsd-plan-routes-native-cmd.md`, `03-generic-doc-direct-edit.md`, `04-ambiguous-detection-fallback.md`
   - `skills/review-spec-checklist/evals/orchestrator-integration.md`, `skills/review-spec-checklist/evals/test-scenarios.md`
   - `skills/review-spec-fixer/evals/test-scenarios.md` — also fix its
     relative fixture path `../../reviewing-specs/evals/fixtures/` →
     `../../review-spec-checklist/evals/fixtures/` (it points at the
     reviewer skill's shared fixtures directory).

   Replace every `reviewing-specs`/`applying-review-feedback` mention in
   these 11 files with the new names, same substitution as Step 3.

2. **MUST NOT touch (5 files)**: `docs/prds/000-ai-kit-overhaul-requirements.md`,
   `docs/superpowers/plans/2026-06-14-e1-review-spec-skill.md`,
   `docs/superpowers/plans/2026-06-24-wizard-redesign-B-ui.md`, and this
   plan + its spec (`docs/superpowers/plans/2026-08-27-review-spec-cross-ai.md`,
   `docs/superpowers/specs/2026-08-27-review-spec-cross-ai-design.md`) —
   these are immutable historical record or documents *about* the rename
   itself; leave their old-name mentions exactly as written.

Re-run the grep after fixing group 1 — it should now match exactly the
5 group-2 paths, not zero.

- [ ] **Step 6: Verify the moved skills' own internal `references/` paths still resolve**

```bash
ls skills/review-spec-checklist/references/frameworks/SCHEMA.md
```

Expected: file exists (the move preserved the directory's internal
structure — only the top-level directory name changed).

- [ ] **Step 7: Note for the user — local symlink refresh**

Add a one-line note to the commit message (Step 7) that
`~/.claude/skills/reviewing-specs` and `~/.claude/skills/applying-review-feedback`
are stale symlinks now — `tools/setup.py`'s existing housekeeping/prune
logic (it already detects "ai-kit symlinks whose repo entry no longer
exists" — see `tools/setup.py`'s symlink-diff functions) removes them and
creates `review-spec-checklist`/`review-spec-fixer` symlinks on the next
`tools/setup.py` run. No new symlink code needed in this plan.

- [ ] **Step 8: Commit**

```bash
git add -A
git commit -m "$(cat <<'EOF'
refactor(skills): rename reviewing-specs -> review-spec-checklist, applying-review-feedback -> review-spec-fixer

Shared review-spec-* prefix resolves the review-spec/reviewing-specs
name confusion. review-spec itself is unchanged (public /review-spec
entrypoint). Stale ~/.claude/skills symlinks self-heal via
tools/setup.py's existing housekeeping prune on next run.
EOF
)"
```

---

### Task 2: Config module — TOML read + local/global resolve + `strategy` merge

**Files:**
- Create: `tools/review-spec.py`
- Test: `tests/test_review_spec.py`

**Interfaces:**
- Produces: `cfg_local_path(cwd: str) -> str`, `cfg_global_path(env: dict) -> str`,
  `cfg_load_toml(path: str) -> dict`, `cfg_merge_reviewers(global_list: list[dict], local_list: list[dict]) -> list[dict]`,
  `cfg_resolve(cwd: str, env: dict) -> dict` (returns `{"policy": {...}, "reviewers": [...]}`),
  `cfg_render_toml(config: dict) -> str`, `cfg_write_toml(path: str, config: dict) -> None`.
  Consumed by Task 5 (policy resolution), Task 8 (`render-toml` subcommand
  calls `cfg_render_toml` directly), and Task 10 (`review-spec-config`
  shells out to the `render-toml` subcommand rather than importing this
  module — see Task 8's Interfaces note on why).

- [ ] **Step 1: Write the failing tests**

Create `tests/test_review_spec.py`:

```python
import importlib.util
import json
import os
import tempfile
import unittest

_MODULE_PATH = os.path.join(os.path.dirname(__file__), "..", "tools", "review-spec.py")


def _load_module():
    spec = importlib.util.spec_from_file_location("review_spec", _MODULE_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


rs = _load_module()


class TestConfigPaths(unittest.TestCase):
    def test_local_path_under_cwd_aikit(self):
        self.assertEqual(rs.cfg_local_path("/repo"), "/repo/.aikit/review-spec.toml")

    def test_global_path_uses_xdg_config_home(self):
        env = {"XDG_CONFIG_HOME": "/x/config"}
        self.assertEqual(rs.cfg_global_path(env), "/x/config/ai-kit/review-spec.toml")

    def test_global_path_falls_back_to_home_dot_config(self):
        env = {"HOME": "/home/u"}
        self.assertEqual(rs.cfg_global_path(env), "/home/u/.config/ai-kit/review-spec.toml")


class TestLoadToml(unittest.TestCase):
    def test_missing_file_returns_empty_dict(self):
        self.assertEqual(rs.cfg_load_toml("/no/such/file.toml"), {})

    def test_malformed_toml_returns_empty_dict(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "bad.toml")
            with open(path, "w", encoding="utf-8") as f:
                f.write("this is not [ valid toml")
            self.assertEqual(rs.cfg_load_toml(path), {})

    def test_valid_toml_parses(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "good.toml")
            with open(path, "w", encoding="utf-8") as f:
                f.write('[policy]\nmode = "double"\n')
            self.assertEqual(rs.cfg_load_toml(path), {"policy": {"mode": "double"}})


class TestMergeReviewers(unittest.TestCase):
    def test_local_overrides_matching_key_fields_only(self):
        global_list = [{"key": "codex-gpt", "model": "gpt-5.2", "effort": "high"}]
        local_list = [{"key": "codex-gpt", "effort": "low"}]
        merged = rs.cfg_merge_reviewers(global_list, local_list)
        self.assertEqual(merged, [{"key": "codex-gpt", "model": "gpt-5.2", "effort": "low"}])

    def test_local_only_key_is_appended(self):
        global_list = [{"key": "a", "model": "m1"}]
        local_list = [{"key": "b", "model": "m2"}]
        merged = rs.cfg_merge_reviewers(global_list, local_list)
        self.assertEqual([r["key"] for r in merged], ["a", "b"])

    def test_global_only_key_is_preserved(self):
        global_list = [{"key": "a", "model": "m1"}, {"key": "b", "model": "m2"}]
        local_list = [{"key": "a", "model": "m1-override"}]
        merged = rs.cfg_merge_reviewers(global_list, local_list)
        self.assertEqual([r["key"] for r in merged], ["a", "b"])
        self.assertEqual(merged[0]["model"], "m1-override")

    def test_entry_with_no_key_is_skipped_not_raised(self):
        # one hand-written mistake in review-spec.toml must not crash the
        # whole orchestrator (matches cfg_load_toml's never-raises contract)
        global_list = [{"key": "a", "model": "m1"}, {"model": "no-key-here"}]
        local_list = [{"model": "also-no-key"}]
        merged = rs.cfg_merge_reviewers(global_list, local_list)
        self.assertEqual([r["key"] for r in merged], ["a"])


class TestResolveConfig(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(__import__("shutil").rmtree, self.tmp, ignore_errors=True)
        self.global_home = tempfile.mkdtemp()
        self.addCleanup(__import__("shutil").rmtree, self.global_home, ignore_errors=True)
        self.env = {"HOME": self.global_home}
        os.makedirs(os.path.join(self.global_home, ".config", "ai-kit"), exist_ok=True)
        with open(os.path.join(self.global_home, ".config", "ai-kit", "review-spec.toml"),
                   "w", encoding="utf-8") as f:
            f.write('[policy]\nmode = "single"\nladder = ["a"]\n'
                    '[[reviewers]]\nkey = "a"\nmodel = "m1"\nvendor = "openai"\n')

    def test_no_local_file_uses_global_only(self):
        resolved = rs.cfg_resolve(self.tmp, self.env)
        self.assertEqual(resolved["policy"]["mode"], "single")
        self.assertEqual(resolved["reviewers"][0]["key"], "a")

    def test_local_only_strategy_ignores_global(self):
        os.makedirs(os.path.join(self.tmp, ".aikit"), exist_ok=True)
        with open(os.path.join(self.tmp, ".aikit", "review-spec.toml"),
                   "w", encoding="utf-8") as f:
            f.write('strategy = "local-only"\n[policy]\nmode = "double"\n')
        resolved = rs.cfg_resolve(self.tmp, self.env)
        self.assertEqual(resolved["policy"]["mode"], "double")
        self.assertEqual(resolved["reviewers"], [])  # local declared no reviewers, global not consulted

    def test_global_merge_is_the_default_strategy(self):
        os.makedirs(os.path.join(self.tmp, ".aikit"), exist_ok=True)
        with open(os.path.join(self.tmp, ".aikit", "review-spec.toml"),
                   "w", encoding="utf-8") as f:
            f.write('[[reviewers]]\nkey = "a"\nmodel = "m1"\nvendor = "openai"\neffort = "low"\n')
        resolved = rs.cfg_resolve(self.tmp, self.env)
        self.assertEqual(resolved["policy"]["mode"], "single")  # inherited from global
        self.assertEqual(resolved["reviewers"][0]["effort"], "low")  # local override applied


class TestRenderAndWriteToml(unittest.TestCase):
    def test_round_trips_through_tomllib(self):
        import tomllib
        config = {"policy": {"mode": "double", "ladder": ["a", "b"]},
                  "reviewers": [{"key": "a", "model": "m1", "vendor": "openai"}]}
        rendered = rs.cfg_render_toml(config)
        parsed = tomllib.loads(rendered)
        self.assertEqual(parsed["policy"]["mode"], "double")
        self.assertEqual(parsed["policy"]["ladder"], ["a", "b"])
        self.assertEqual(parsed["reviewers"][0]["key"], "a")

    def test_write_toml_creates_parent_dirs(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "nested", "review-spec.toml")
            rs.cfg_write_toml(path, {"policy": {"mode": "single"}, "reviewers": []})
            self.assertTrue(os.path.exists(path))

    def test_escapes_quotes_and_backslashes_in_strings(self):
        rendered = rs.cfg_render_toml({"policy": {}, "reviewers": [
            {"key": "a", "command": 'echo "hi" \\ done'}]})
        import tomllib
        parsed = tomllib.loads(rendered)
        self.assertEqual(parsed["reviewers"][0]["command"], 'echo "hi" \\ done')


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python3 -m unittest tests.test_review_spec -v`

Expected: FAIL — `tools/review-spec.py` does not exist yet
(`FileNotFoundError` from `spec_from_file_location`/`exec_module`, or an
`AttributeError` once the empty file exists).

- [ ] **Step 3: Implement**

Create `tools/review-spec.py`:

```python
#!/usr/bin/env python3
"""review-spec cross-AI reviewer support: config (TOML), cache (JSON),
runtime/CLI detection, policy resolution, and cross-reviewer findings
merge. Stdlib-only, no external dependencies (see pyproject.toml)."""

import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import time
import tomllib
from typing import NamedTuple, Optional


# ── Config (TOML) ────────────────────────────────────────────────────────

DEFAULT_POLICY = {"mode": "single", "ladder": []}


def cfg_local_path(cwd: str) -> str:
    """./.aikit/review-spec.toml under cwd."""
    return os.path.join(cwd, ".aikit", "review-spec.toml")


def cfg_global_path(env: dict) -> str:
    """${XDG_CONFIG_HOME:-$HOME/.config}/ai-kit/review-spec.toml."""
    base = env.get("XDG_CONFIG_HOME") or os.path.join(env.get("HOME", ""), ".config")
    return os.path.join(base, "ai-kit", "review-spec.toml")


def cfg_load_toml(path: str) -> dict:
    """Parse the TOML at path. Missing/malformed -> {}. Never raises."""
    try:
        with open(path, "rb") as f:
            return tomllib.load(f)
    except FileNotFoundError:
        return {}
    except (OSError, tomllib.TOMLDecodeError):
        return {}


def cfg_merge_reviewers(global_list: list, local_list: list) -> list:
    """Merge [[reviewers]] by key: local fields override/extend matching
    global entries; local-only keys are appended; global-only keys are
    preserved unchanged. Order: global order first, then new local keys.
    A malformed entry with no `key` at all is silently skipped (never
    raises) — matches cfg_load_toml's "never raises on bad input"
    contract: one hand-written mistake in review-spec.toml must not crash
    the whole orchestrator."""
    global_list = [r for r in global_list if "key" in r]
    local_list = [r for r in local_list if "key" in r]
    by_key = {r["key"]: dict(r) for r in global_list}
    for r in local_list:
        key = r["key"]
        if key in by_key:
            by_key[key].update(r)
        else:
            by_key[key] = dict(r)
    global_keys = [r["key"] for r in global_list]
    new_local_keys = [r["key"] for r in local_list if r["key"] not in global_keys]
    order = global_keys + new_local_keys
    return [by_key[k] for k in order]


def cfg_resolve(cwd: str, env: dict) -> dict:
    """Resolve the effective config: local (with its own `strategy`) vs
    global, per the design's local/global precedence rules."""
    local = cfg_load_toml(cfg_local_path(cwd))
    if not local:
        global_cfg = cfg_load_toml(cfg_global_path(env))
        return {"policy": {**DEFAULT_POLICY, **global_cfg.get("policy", {})},
                "reviewers": global_cfg.get("reviewers", [])}
    strategy = local.get("strategy", "global-merge")
    if strategy == "local-only":
        return {"policy": {**DEFAULT_POLICY, **local.get("policy", {})},
                "reviewers": local.get("reviewers", [])}
    global_cfg = cfg_load_toml(cfg_global_path(env))
    merged_policy = {**DEFAULT_POLICY, **global_cfg.get("policy", {}), **local.get("policy", {})}
    merged_reviewers = cfg_merge_reviewers(global_cfg.get("reviewers", []), local.get("reviewers", []))
    return {"policy": merged_policy, "reviewers": merged_reviewers}


def _toml_value(v) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    if isinstance(v, list):
        return "[" + ", ".join(_toml_value(x) for x in v) + "]"
    escaped = str(v).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def cfg_render_toml(config: dict) -> str:
    """Hand-rolled TOML serializer for this schema only (flat [policy] table
    + array-of-tables [[reviewers]] with flat string/bool/list values) —
    tomllib is read-only in stdlib, and adding a writer dependency would
    break this repo's zero-dependency runtime."""
    lines = []
    policy = config.get("policy", {})
    if policy:
        lines.append("[policy]")
        for k, v in policy.items():
            lines.append(f"{k} = {_toml_value(v)}")
        lines.append("")
    for r in config.get("reviewers", []):
        lines.append("[[reviewers]]")
        for k, v in r.items():
            lines.append(f"{k} = {_toml_value(v)}")
        lines.append("")
    return "\n".join(lines).rstrip("\n") + "\n"


def cfg_write_toml(path: str, config: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(cfg_render_toml(config))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python3 -m unittest tests.test_review_spec -v`

Expected: PASS for every `TestConfigPaths`, `TestLoadToml`,
`TestMergeReviewers`, `TestResolveConfig`, `TestRenderAndWriteToml` test.

- [ ] **Step 5: Commit**

```bash
git add tools/review-spec.py tests/test_review_spec.py
git commit -m "feat(review-spec): add TOML config load/write with local/global strategy merge"
```

---

### Task 3: Cache module — JSON read/write + TTL staleness

**Files:**
- Modify: `tools/review-spec.py`
- Test: `tests/test_review_spec.py`

**Interfaces:**
- Consumes: nothing from Task 2.
- Produces: `cache_base(env: dict) -> str`, `cache_runtimes_path(env: dict) -> str`,
  `cache_quota_path(env: dict) -> str`, `cache_read_json(path: str) -> dict | None`,
  `cache_write_json(path: str, data: dict) -> None`, `cache_is_stale(path: str, ttl_seconds: int) -> bool`,
  `RUNTIMES_TTL_SECONDS: int`, `QUOTA_TTL_SECONDS: int`.
  Consumed by Task 4 (detection writes `runtimes.json`) and Task 5 (policy
  resolution reads `quota.json`).

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_review_spec.py`:

```python
class TestCachePaths(unittest.TestCase):
    def test_base_uses_xdg_cache_home(self):
        env = {"XDG_CACHE_HOME": "/x/cache"}
        self.assertEqual(rs.cache_base(env), "/x/cache/ai-kit/review-spec")

    def test_base_falls_back_to_home_dot_cache(self):
        env = {"HOME": "/home/u"}
        self.assertEqual(rs.cache_base(env), "/home/u/.cache/ai-kit/review-spec")

    def test_runtimes_and_quota_paths(self):
        env = {"HOME": "/home/u"}
        self.assertEqual(rs.cache_runtimes_path(env), "/home/u/.cache/ai-kit/review-spec/runtimes.json")
        self.assertEqual(rs.cache_quota_path(env), "/home/u/.cache/ai-kit/review-spec/quota.json")


class TestCacheReadWrite(unittest.TestCase):
    def test_read_missing_file_returns_none(self):
        self.assertIsNone(rs.cache_read_json("/no/such/file.json"))

    def test_write_then_read_round_trips(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "sub", "data.json")
            rs.cache_write_json(path, {"a": 1})
            self.assertEqual(rs.cache_read_json(path), {"a": 1})

    def test_read_malformed_json_returns_none(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "bad.json")
            with open(path, "w", encoding="utf-8") as f:
                f.write("{not valid json")
            self.assertIsNone(rs.cache_read_json(path))


class TestCacheStaleness(unittest.TestCase):
    def test_missing_file_is_stale(self):
        self.assertTrue(rs.cache_is_stale("/no/such/file.json", 3600))

    def test_fresh_file_is_not_stale(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "f.json")
            rs.cache_write_json(path, {})
            self.assertFalse(rs.cache_is_stale(path, 3600))

    def test_old_file_is_stale(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "f.json")
            rs.cache_write_json(path, {})
            old = time.time() - 7200
            os.utime(path, (old, old))
            self.assertTrue(rs.cache_is_stale(path, 3600))
```

Add `import time` to `tests/test_review_spec.py`'s import block at the top
of the file (it is not there yet — Task 2's test file only imported
`importlib.util`, `json`, `os`, `tempfile`, `unittest`).

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python3 -m unittest tests.test_review_spec.TestCachePaths tests.test_review_spec.TestCacheReadWrite tests.test_review_spec.TestCacheStaleness -v`

Expected: FAIL — `AttributeError: module 'review_spec' has no attribute 'cache_base'` (and similarly for the other new names).

- [ ] **Step 3: Implement**

Append to `tools/review-spec.py`:

```python
# ── Cache (JSON) ─────────────────────────────────────────────────────────

RUNTIMES_TTL_SECONDS = 30 * 24 * 3600   # ~30 days: CLI/model presence is near-static
QUOTA_TTL_SECONDS = 3600                 # 1 hour: quota/context headroom is highly dynamic


def cache_base(env: dict) -> str:
    """${XDG_CACHE_HOME:-$HOME/.cache}/ai-kit/review-spec."""
    base = env.get("XDG_CACHE_HOME") or os.path.join(env.get("HOME", ""), ".cache")
    return os.path.join(base, "ai-kit", "review-spec")


def cache_runtimes_path(env: dict) -> str:
    return os.path.join(cache_base(env), "runtimes.json")


def cache_quota_path(env: dict) -> str:
    return os.path.join(cache_base(env), "quota.json")


def cache_read_json(path: str) -> Optional[dict]:
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def cache_write_json(path: str, data: dict) -> None:
    """Atomic write (tmp file + os.replace) so a crash mid-write never
    leaves a half-written cache file for the next reader."""
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

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python3 -m unittest tests.test_review_spec -v`

Expected: PASS, all tests including Task 2's.

- [ ] **Step 5: Commit**

```bash
git add tools/review-spec.py tests/test_review_spec.py
git commit -m "feat(review-spec): add JSON cache read/write with TTL staleness check"
```

---

### Task 4: Runtime/CLI detection

**Files:**
- Modify: `tools/review-spec.py`
- Test: `tests/test_review_spec.py`

**Interfaces:**
- Consumes: nothing from Tasks 2–3 directly (writes via `cache_write_json`
  are the caller's job, done by the CLI entrypoint in Task 8, not by these
  functions themselves — keeps detection pure/testable).
- Produces: `KNOWN_CLIS: tuple[str, ...]`, `detect_installed_clis(which_fn=shutil.which) -> dict`,
  `detect_opencode_models(binary: str, run_fn=subprocess.run) -> list[str]`,
  `build_runtimes_snapshot(which_fn=shutil.which, run_fn=subprocess.run) -> dict`.
  Consumed by Task 10 (`review-spec-config`) and Task 11 (Step 0.7).

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_review_spec.py`:

```python
class TestDetectInstalledClis(unittest.TestCase):
    def test_reports_installed_and_missing(self):
        def fake_which(name):
            return f"/usr/bin/{name}" if name in ("claude", "codex") else None
        result = rs.detect_installed_clis(which_fn=fake_which)
        self.assertEqual(result["claude"], "/usr/bin/claude")
        self.assertEqual(result["codex"], "/usr/bin/codex")
        self.assertIsNone(result["cursor-agent"])

    def test_covers_all_known_clis(self):
        result = rs.detect_installed_clis(which_fn=lambda n: None)
        self.assertEqual(set(result.keys()), set(rs.KNOWN_CLIS))


class TestDetectOpencodeModels(unittest.TestCase):
    def test_parses_one_model_per_line(self):
        class FakeResult:
            stdout = "opencode-go/kimi-k3\nopencode-go/qwen3.8-max\n\n"
        result = rs.detect_opencode_models("/usr/bin/opencode",
                                            run_fn=lambda *a, **k: FakeResult())
        self.assertEqual(result, ["opencode-go/kimi-k3", "opencode-go/qwen3.8-max"])

    def test_returns_empty_list_on_failure(self):
        def fake_run(*a, **k):
            raise OSError("not found")
        self.assertEqual(rs.detect_opencode_models("/usr/bin/opencode", run_fn=fake_run), [])


class TestBuildRuntimesSnapshot(unittest.TestCase):
    def test_marks_missing_clis_not_installed(self):
        snapshot = rs.build_runtimes_snapshot(which_fn=lambda n: None,
                                               run_fn=lambda *a, **k: None)
        self.assertFalse(snapshot["clis"]["grok"]["installed"])

    def test_lists_opencode_models_when_installed(self):
        class FakeResult:
            stdout = "opencode-go/kimi-k3\n"

        def fake_which(name):
            return "/usr/bin/opencode" if name == "opencode" else None

        snapshot = rs.build_runtimes_snapshot(which_fn=fake_which,
                                               run_fn=lambda *a, **k: FakeResult())
        self.assertTrue(snapshot["clis"]["opencode"]["installed"])
        self.assertEqual(snapshot["clis"]["opencode"]["models"], ["opencode-go/kimi-k3"])

    def test_non_opencode_clis_have_no_models_key(self):
        def fake_which(name):
            return "/usr/bin/codex" if name == "codex" else None
        snapshot = rs.build_runtimes_snapshot(which_fn=fake_which,
                                               run_fn=lambda *a, **k: None)
        self.assertNotIn("models", snapshot["clis"]["codex"])
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python3 -m unittest tests.test_review_spec.TestDetectInstalledClis tests.test_review_spec.TestDetectOpencodeModels tests.test_review_spec.TestBuildRuntimesSnapshot -v`

Expected: FAIL — `AttributeError: module 'review_spec' has no attribute 'KNOWN_CLIS'` (and similarly for the functions).

- [ ] **Step 3: Implement**

Append to `tools/review-spec.py`:

```python
# ── Runtime/CLI detection ───────────────────────────────────────────────

KNOWN_CLIS = ("claude", "codex", "opencode", "grok", "cursor-agent", "gemini")


def detect_installed_clis(which_fn=shutil.which) -> dict:
    """{cli_name: absolute_path_or_None} for each KNOWN_CLIS entry."""
    return {cli: which_fn(cli) for cli in KNOWN_CLIS}


def detect_opencode_models(binary: str, run_fn=subprocess.run) -> list:
    """Runs `<binary> models`; one model id per non-blank line. opencode is
    the only known-installed multi-provider CLI today (confirmed live:
    lists opencode-go/kimi-k3, opencode-go/qwen3.8-max, opencode-go/grok-4.6,
    etc. under its own routing) — other CLIs name their model directly on
    invocation with no separate list subcommand to parse."""
    try:
        result = run_fn([binary, "models"], capture_output=True, text=True,
                         check=False, timeout=15)
    except (OSError, subprocess.TimeoutExpired):
        return []
    return [ln.strip() for ln in result.stdout.splitlines() if ln.strip()]


def build_runtimes_snapshot(which_fn=shutil.which, run_fn=subprocess.run) -> dict:
    """{"clis": {name: {"installed": bool, "path"?: str, "models"?: [str]}}}.
    Pure function — the caller (Task 8's CLI entrypoint) decides whether/
    where to persist this via cache_write_json."""
    installed = detect_installed_clis(which_fn=which_fn)
    snapshot = {"clis": {}}
    for cli, binpath in installed.items():
        if not binpath:
            snapshot["clis"][cli] = {"installed": False}
            continue
        entry = {"installed": True, "path": binpath}
        if cli == "opencode":
            entry["models"] = detect_opencode_models(binpath, run_fn=run_fn)
        snapshot["clis"][cli] = entry
    return snapshot
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python3 -m unittest tests.test_review_spec -v`

Expected: PASS, all tests including Tasks 2–3's.

- [ ] **Step 5: Commit**

```bash
git add tools/review-spec.py tests/test_review_spec.py
git commit -m "feat(review-spec): add CLI/model detection (detect_installed_clis, build_runtimes_snapshot)"
```

---

### Task 5: Policy resolution — unified ladder walk, tier-aware by construction

**Design correction (caught by the cross-AI dry run, §below):** an earlier
draft of this task modeled "the current session's own reviewer" as a fixed
`CURRENT_SESSION` sentinel with a hardcoded `model` — which reintroduced
exactly the "fixed model name" anti-pattern the spec's §1 opens by
rejecting (Opus-when-available, cheaper-tier-under-budget, never a fixed
name). The fix: there is no special sentinel. `policy.ladder` is one
unified ordered list mixing native (`cli`-less) and external entries —
e.g. `["claude-opus", "claude-sonnet", "codex-gpt", "grok-flagship"]`. In
`single` mode, the **best overall entry** (first with quota, preferring a
different vendor than the source) is always tried first; this is what
delivers tier-awareness, because the user's own config naturally orders
their preferred Claude tier first, and a quota miss on `claude-opus` falls
through to `claude-sonnet` (or the next configured entry) automatically —
no special-casing needed. Only when *nothing at all* has quota (or no
config exists) does resolution fall back to `NO_CONFIG_FALLBACK`, which
dispatches via the `Agent` tool with **no `model` override at all** —
inheriting whatever model this Claude Code session already runs as, rather
than hardcoding `sonnet`.

**Second design correction (from the live Opus-5 re-review of this plan —
see the Self-review notes at the end of this document):** the first draft
of `double` mode reused the exact same "best overall entry, any vendor"
walk for its primary slot — which could let an *external* ladder entry
become the primary/baseline reviewer whenever it happened to rank above
every native entry (e.g. `ladder = ["codex-gpt", "claude-opus"]`). That
directly contradicts the design's own guarantee (spec §3): double mode's
first slot is always the **native** reviewer, unconditionally. Fixed:
`double` mode's primary walks `policy.ladder` **restricted to its
`cli`-less entries only** (still tier-aware within that restricted set —
`claude-opus` before `claude-sonnet` when both are native and Opus has
quota), falling back to `NO_CONFIG_FALLBACK` only when no native entry is
configured or none has quota — never by promoting an external entry into
the baseline slot. The secondary slot is unrestricted (native or external,
whichever ranks best with a different vendor than the primary) and is
still simply dropped, not substituted, when nothing survives.

**Files:**
- Modify: `tools/review-spec.py`
- Test: `tests/test_review_spec.py`

**Interfaces:**
- Consumes: the `config` shape produced by Task 2's `cfg_resolve` (a dict
  with `"policy"` and `"reviewers"` keys) and a `quota` dict shaped like
  `{"<reviewer-key>": {"available": bool}}` (Task 3's `cache_read_json` on
  `quota.json` — this task does not read the cache file itself, it takes
  the already-loaded dict as a parameter, keeping it pure/testable).
- Produces: `ResolvedReviewer` (`NamedTuple`: `key, model, vendor, cli,
  command, extra` — `model == ""` means "no override, inherit the current
  session's default"), `NO_CONFIG_FALLBACK: ResolvedReviewer`,
  `resolve_ladder_pick(reviewers: list, ladder: list, skip_vendor: str, quota: dict) -> ResolvedReviewer | None`,
  `resolve_reviewers(config: dict, quota: dict, source_vendor: str, cross_ai: bool) -> list[ResolvedReviewer]`.
  Consumed by Task 11 (Step 0.7/Step 1 dispatch).

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_review_spec.py`:

```python
class TestResolveLadderPick(unittest.TestCase):
    def setUp(self):
        self.reviewers = [
            {"key": "codex-gpt", "model": "gpt-5.2", "vendor": "openai"},
            {"key": "grok-flagship", "model": "grok-4.6", "vendor": "xai"},
        ]

    def test_picks_first_available_non_same_vendor(self):
        pick = rs.resolve_ladder_pick(self.reviewers, ["codex-gpt", "grok-flagship"],
                                       skip_vendor="anthropic", quota={})
        self.assertEqual(pick.key, "codex-gpt")

    def test_skips_same_vendor_as_source(self):
        pick = rs.resolve_ladder_pick(self.reviewers, ["codex-gpt", "grok-flagship"],
                                       skip_vendor="openai", quota={})
        self.assertEqual(pick.key, "grok-flagship")

    def test_skips_candidate_without_quota(self):
        quota = {"codex-gpt": {"available": False}}
        pick = rs.resolve_ladder_pick(self.reviewers, ["codex-gpt", "grok-flagship"],
                                       skip_vendor="anthropic", quota=quota)
        self.assertEqual(pick.key, "grok-flagship")

    def test_no_quota_entry_means_available(self):
        pick = rs.resolve_ladder_pick(self.reviewers, ["codex-gpt"],
                                       skip_vendor="anthropic", quota={})
        self.assertEqual(pick.key, "codex-gpt")

    def test_falls_back_to_same_vendor_before_giving_up(self):
        # only same-vendor-as-source candidate exists and has quota -> still picked,
        # rather than returning None
        pick = rs.resolve_ladder_pick(self.reviewers, ["codex-gpt"],
                                       skip_vendor="openai", quota={})
        self.assertEqual(pick.key, "codex-gpt")

    def test_returns_none_when_nothing_survives(self):
        quota = {"codex-gpt": {"available": False}}
        pick = rs.resolve_ladder_pick([self.reviewers[0]], ["codex-gpt"],
                                       skip_vendor="anthropic", quota=quota)
        self.assertIsNone(pick)

    def test_unknown_ladder_key_is_skipped(self):
        pick = rs.resolve_ladder_pick(self.reviewers, ["nonexistent", "grok-flagship"],
                                       skip_vendor="anthropic", quota={})
        self.assertEqual(pick.key, "grok-flagship")

    def test_entry_missing_model_resolves_to_empty_string_not_a_crash(self):
        reviewers = [{"key": "no-model", "vendor": "openai"}]
        pick = rs.resolve_ladder_pick(reviewers, ["no-model"], skip_vendor="anthropic", quota={})
        self.assertEqual(pick.model, "")


class TestResolveReviewers(unittest.TestCase):
    def setUp(self):
        self.config = {
            "policy": {"mode": "single", "ladder": ["claude-opus", "claude-sonnet", "codex-gpt"]},
            "reviewers": [
                {"key": "claude-opus", "model": "opus", "vendor": "anthropic"},
                {"key": "claude-sonnet", "model": "sonnet", "vendor": "anthropic"},
                {"key": "codex-gpt", "model": "gpt-5.2", "vendor": "openai",
                 "cli": "codex", "command": "codex exec -m {model} {prompt}"},
            ],
        }

    def test_no_cross_ai_returns_only_the_no_config_fallback(self):
        result = rs.resolve_reviewers(self.config, quota={}, source_vendor="anthropic", cross_ai=False)
        self.assertEqual(result, [rs.NO_CONFIG_FALLBACK])

    def test_no_config_at_all_falls_back_to_session_default(self):
        config = {"policy": {"mode": "single", "ladder": []}, "reviewers": []}
        result = rs.resolve_reviewers(config, quota={}, source_vendor="anthropic", cross_ai=True)
        self.assertEqual(result, [rs.NO_CONFIG_FALLBACK])

    def test_single_mode_skips_same_vendor_as_source(self):
        # single mode's whole point is an independent perspective, so the two
        # same-vendor-as-source (anthropic) ladder entries are skipped even
        # though they're earlier in the ladder
        result = rs.resolve_reviewers(self.config, quota={}, source_vendor="anthropic", cross_ai=True)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].key, "codex-gpt")

    def test_single_mode_falls_through_tiers_when_flagship_lacks_quota(self):
        quota = {"codex-gpt": {"available": False}}
        result = rs.resolve_reviewers(self.config, quota=quota, source_vendor="anthropic", cross_ai=True)
        # only same-vendor entries left with quota -> the vendor-skip fallback picks
        # the ladder's best surviving entry, which is claude-opus (tier-aware: tried
        # before claude-sonnet because it is earlier in the ladder)
        self.assertEqual(result[0].key, "claude-opus")

    def test_double_mode_primary_is_best_overall_regardless_of_vendor(self):
        config = dict(self.config)
        config["policy"] = {"mode": "double", "ladder": self.config["policy"]["ladder"]}
        result = rs.resolve_reviewers(config, quota={}, source_vendor="anthropic", cross_ai=True)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].key, "claude-opus")   # best overall = top of ladder, tier-aware
        self.assertEqual(result[1].key, "codex-gpt")      # first DIFFERENT-vendor entry

    def test_double_mode_primary_falls_through_tiers_when_flagship_lacks_quota(self):
        config = dict(self.config)
        config["policy"] = {"mode": "double", "ladder": self.config["policy"]["ladder"]}
        quota = {"claude-opus": {"available": False}}
        result = rs.resolve_reviewers(config, quota=quota, source_vendor="anthropic", cross_ai=True)
        self.assertEqual(result[0].key, "claude-sonnet")  # falls through the tier ladder
        self.assertEqual(result[1].key, "codex-gpt")

    def test_double_mode_drops_to_single_when_no_other_vendor_has_quota(self):
        config = dict(self.config)
        config["policy"] = {"mode": "double", "ladder": self.config["policy"]["ladder"]}
        quota = {"codex-gpt": {"available": False}}
        result = rs.resolve_reviewers(config, quota=quota, source_vendor="anthropic", cross_ai=True)
        self.assertEqual(len(result), 1)  # no cross-vendor survivor -> just the primary
        self.assertEqual(result[0].key, "claude-opus")

    def test_double_mode_with_empty_ladder_falls_back_to_session_default(self):
        config = {"policy": {"mode": "double", "ladder": []}, "reviewers": []}
        result = rs.resolve_reviewers(config, quota={}, source_vendor="anthropic", cross_ai=True)
        self.assertEqual(result, [rs.NO_CONFIG_FALLBACK])

    def test_double_mode_baseline_is_always_native_even_when_external_ranks_first(self):
        # regression for the design's "double mode always runs a native
        # baseline, guaranteed" guarantee (spec §3): an external entry
        # ranked ABOVE every native entry in the ladder must never become
        # the baseline — it can only ever take the second (cross-vendor)
        # slot.
        config = {
            "policy": {"mode": "double", "ladder": ["codex-gpt", "claude-opus", "claude-sonnet"]},
            "reviewers": self.config["reviewers"],
        }
        result = rs.resolve_reviewers(config, quota={}, source_vendor="anthropic", cross_ai=True)
        self.assertEqual(result[0].key, "claude-opus")   # native baseline, not codex-gpt
        self.assertIsNone(result[0].cli)
        self.assertEqual(result[1].key, "codex-gpt")     # external takes the secondary slot only

    def test_double_mode_baseline_falls_back_to_session_default_when_no_native_entry_configured(self):
        # ladder is entirely external -> the native-baseline guarantee still
        # holds via NO_CONFIG_FALLBACK, never by promoting an external entry
        config = {
            "policy": {"mode": "double", "ladder": ["codex-gpt"]},
            "reviewers": [self.config["reviewers"][2]],  # codex-gpt only, no native entries at all
        }
        result = rs.resolve_reviewers(config, quota={}, source_vendor="anthropic", cross_ai=True)
        self.assertEqual(result[0], rs.NO_CONFIG_FALLBACK)
        self.assertEqual(result[1].key, "codex-gpt")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python3 -m unittest tests.test_review_spec.TestResolveLadderPick tests.test_review_spec.TestResolveReviewers -v`

Expected: FAIL — `AttributeError: module 'review_spec' has no attribute 'resolve_ladder_pick'`.

- [ ] **Step 3: Implement**

Append to `tools/review-spec.py`:

```python
# ── Policy resolution ────────────────────────────────────────────────────

class ResolvedReviewer(NamedTuple):
    """A reviewer chosen for this run. cli/command are None for native
    (current-runtime) dispatch. model == "" means "no override — inherit
    the current session's own default model" (never a hardcoded name).
    extra holds any reviewer-entry fields beyond key/model/vendor/cli/
    command (e.g. effort, service_tier) for the caller to interpolate into
    `command`."""

    key: str
    model: str
    vendor: str
    cli: Optional[str]
    command: Optional[str]
    extra: dict


NO_CONFIG_FALLBACK = ResolvedReviewer(key="session-default", model="", vendor="",
                                       cli=None, command=None, extra={})

_KNOWN_REVIEWER_FIELDS = {"key", "model", "vendor", "cli", "command"}


def _reviewer_by_key(reviewers: list, key: str) -> Optional[dict]:
    for r in reviewers:
        if r.get("key") == key:
            return r
    return None


def _to_resolved(entry: dict) -> ResolvedReviewer:
    """entry["key"] is always present here — every caller reaches this via
    _reviewer_by_key, which already filters by key. entry.get("model", "")
    tolerates a config entry that forgot to set model (never raises); an
    empty model is already a valid sentinel elsewhere in this module (see
    ResolvedReviewer's docstring) — "no override"."""
    return ResolvedReviewer(
        key=entry["key"], model=entry.get("model", ""), vendor=entry.get("vendor", ""),
        cli=entry.get("cli"), command=entry.get("command"),
        extra={k: v for k, v in entry.items() if k not in _KNOWN_REVIEWER_FIELDS},
    )


def _has_quota(quota: dict, key: str) -> bool:
    """No entry -> never probed / no probe support for this CLI yet ->
    assume available (never block a review on the ABSENCE of quota data)."""
    entry = quota.get(key)
    if entry is None:
        return True
    return entry.get("available", True)


def resolve_ladder_pick(reviewers: list, ladder: list, skip_vendor: str, quota: dict) -> Optional[ResolvedReviewer]:
    """First ladder entry that (a) exists in `reviewers`, (b) has a
    different vendor than skip_vendor (empty skip_vendor disables this
    filter — used for "best overall, any vendor"), and (c) has quota. If
    nothing survives both filters, retry ignoring the vendor filter
    (same-vendor coverage beats no reviewer at all). None only if every
    candidate lacks quota or doesn't exist. This is where tier-awareness
    comes from: a caller passing an ordered ladder like ["claude-opus",
    "claude-sonnet", ...] gets the flagship tier whenever it has quota, and
    falls through to the next configured tier automatically otherwise — no
    separate "tier" concept needed."""
    for key in ladder:
        entry = _reviewer_by_key(reviewers, key)
        if entry is None or (skip_vendor and entry.get("vendor") == skip_vendor) or not _has_quota(quota, key):
            continue
        return _to_resolved(entry)
    for key in ladder:
        entry = _reviewer_by_key(reviewers, key)
        if entry is None or not _has_quota(quota, key):
            continue
        return _to_resolved(entry)
    return None


def _native_ladder(reviewers: list, ladder: list) -> list:
    """The sub-list of `ladder` whose keys resolve to a cli-less
    (native/current-runtime) reviewer entry, order preserved. Used to keep
    double mode's baseline guaranteed-native (see resolve_reviewers)."""
    result = []
    for key in ladder:
        entry = _reviewer_by_key(reviewers, key)
        if entry is not None and not entry.get("cli"):
            result.append(key)
    return result


def resolve_reviewers(config: dict, quota: dict, source_vendor: str, cross_ai: bool) -> list:
    """The full policy decision (design spec §3, as corrected during
    planning — see Task 5's design-correction notes, including the
    live-review fix to double mode's native-baseline guarantee). Returns 1
    or 2 ResolvedReviewer entries; dispatch mechanics are the caller's
    concern (Task 11), this only decides WHO.

    single: one reviewer, preferring a vendor different from source_vendor
    (independent perspective on the document), quota-aware, tier-aware via
    ladder order.

    double: `primary` walks ONLY the ladder's native (cli-less) entries —
    tier-aware within that restricted set, guaranteed to never be an
    external entry, falling back to NO_CONFIG_FALLBACK if no native entry
    is configured or none has quota (never zero reviewers, and never a
    promoted external entry standing in for the baseline). `secondary` is
    the best entry anywhere in the FULL ladder with a vendor DIFFERENT
    from primary's, dropped (not substituted) if none survives (a
    native-only ladder degrades to a single reviewer, not an error).

    Either mode falls back to NO_CONFIG_FALLBACK when --no-cross-ai was
    passed, the ladder is empty, or nothing in it has quota."""
    if not cross_ai:
        return [NO_CONFIG_FALLBACK]
    policy = config.get("policy", {})
    mode = policy.get("mode", "single")
    ladder = policy.get("ladder", [])
    reviewers = config.get("reviewers", [])
    if mode == "double":
        primary = resolve_ladder_pick(reviewers, _native_ladder(reviewers, ladder),
                                       skip_vendor="", quota=quota)
        if primary is None:
            primary = NO_CONFIG_FALLBACK
        secondary = resolve_ladder_pick(reviewers, ladder, skip_vendor=primary.vendor, quota=quota)
        if secondary is None or secondary.key == primary.key:
            return [primary]
        return [primary, secondary]
    pick = resolve_ladder_pick(reviewers, ladder, skip_vendor=source_vendor, quota=quota)
    return [pick] if pick else [NO_CONFIG_FALLBACK]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python3 -m unittest tests.test_review_spec -v`

Expected: PASS, all tests including Tasks 2–4's.

- [ ] **Step 5: Commit**

```bash
git add tools/review-spec.py tests/test_review_spec.py
git commit -m "feat(review-spec): add single/double ladder policy resolution"
```

---

### Task 6: Quota probing (delivers spec §1's "quota-aware" goal)

**Added during planning (caught by the cross-AI dry run — see Self-review
notes at the end of this plan):** without this task, `quota.json` is never
written by anything, so `_has_quota` (Task 5) always sees an empty dict and
"quota-aware" is unimplemented. This task closes that gap with a generic,
CLI-agnostic probe: run a trivial prompt through a reviewer's own `command`
template and classify availability from the outcome (exit code / stderr
content), rather than requiring a confirmed quota-subcommand per CLI (most
of which are still "unconfirmed syntax" per the CLI profiles, Task 9). The
one CLI with a confirmed richer signal (`codex`'s usage-limit error on a
low-effort/fast-tier call — see `references/review-spec/cli-profiles/codex.md`)
is covered by the same generic heuristic (its error text contains "usage
limit", which the heuristic's substring check catches) — no special-casing
needed.

**Cost bound, and scope narrower than the design's `quota.json` shape**:
this probe only ever answers a boolean — `available` — from a real (if
trivial) call to each CLI; it does **not** capture remaining context-window
headroom, despite design §6/§10 describing `quota.json` as holding
"remaining context window and quota/usage headroom" and an edge case
("has quota but the window can't fit the document"). That headroom
capture has no confirmed CLI mechanism today (every profile in Task 9
marks context-window introspection "unconfirmed syntax — research during
implementation"), so this task deliberately ships the boolean-only shape
now and the design is corrected to match (see this plan's Self-review
notes). On cost: each ladder entry is charged for **at most one** trivial
probe call per `QUOTA_TTL_SECONDS` (1 hour) — `refresh_quota_cache` skips
any entry whose cached `checked_at` is still fresh, regardless of how many
`/review-spec` invocations happen inside that hour.

**Files:**
- Modify: `tools/review-spec.py`
- Test: `tests/test_review_spec.py`

**Interfaces:**
- Consumes: `ResolvedReviewer`/`_to_resolved` (Task 5), `cache_read_json`/
  `cache_write_json`/`QUOTA_TTL_SECONDS` (Task 3).
- Produces: `render_reviewer_command(resolved: ResolvedReviewer, prompt: str) -> str`,
  `probe_reviewer_quota(resolved: ResolvedReviewer, run_fn=subprocess.run) -> dict`,
  `refresh_quota_cache(config: dict, ladder_keys: list, existing: dict, ttl_seconds: int, run_fn=subprocess.run) -> dict`.
  `render_reviewer_command` is also consumed by Task 11's Step 1 (real
  dispatch) — the same template-filling logic backs both the quota probe
  and the actual reviewer invocation, so they can never drift apart.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_review_spec.py`:

```python
class TestRenderReviewerCommand(unittest.TestCase):
    def test_fills_model_and_prompt(self):
        resolved = rs.ResolvedReviewer(key="codex-gpt", model="gpt-5.2", vendor="openai",
                                        cli="codex", command='codex exec -m {model} {prompt}',
                                        extra={})
        self.assertEqual(rs.render_reviewer_command(resolved, "hello"),
                          'codex exec -m gpt-5.2 hello')

    def test_fills_extra_fields(self):
        resolved = rs.ResolvedReviewer(key="codex-gpt", model="gpt-5.2", vendor="openai",
                                        cli="codex",
                                        command="codex exec -m {model} -c service_tier='\"{service_tier}\"' {prompt}",
                                        extra={"service_tier": "fast"})
        out = rs.render_reviewer_command(resolved, "hi")
        self.assertIn("service_tier='\"fast\"'", out)

    def test_prompt_is_shell_escaped_but_extra_fields_are_not(self):
        # {prompt} is free text built from document paths/content signals —
        # the one field that MUST survive as a single shell argument no
        # matter what it contains. {model}/extra fields are short,
        # human-typed config values whose own quoting idiom (e.g. codex's
        # -c key='"value"') the template author controls directly — auto-
        # quoting those would break that idiom, so only {prompt} is quoted.
        resolved = rs.ResolvedReviewer(key="codex-gpt", model="gpt-5.2", vendor="openai",
                                        cli="codex", command="codex exec -m {model} {prompt}",
                                        extra={})
        dangerous_prompt = 'Read this; rm -rf / #'
        out = rs.render_reviewer_command(resolved, dangerous_prompt)
        import shlex as _shlex
        tokens = _shlex.split(out)
        self.assertEqual(tokens[-1], dangerous_prompt)  # survives as ONE argument


class TestProbeReviewerQuota(unittest.TestCase):
    def test_native_entry_is_always_available(self):
        resolved = rs.ResolvedReviewer(key="claude-opus", model="opus", vendor="anthropic",
                                        cli=None, command=None, extra={})
        result = rs.probe_reviewer_quota(resolved, run_fn=lambda *a, **k: (_ for _ in ()).throw(
            AssertionError("should never shell out for a native entry")))
        self.assertTrue(result["available"])

    def test_successful_call_is_available(self):
        resolved = rs.ResolvedReviewer(key="codex-gpt", model="gpt-5.2", vendor="openai",
                                        cli="codex", command="echo ok", extra={})
        class FakeResult:
            returncode = 0
            stdout = "ok\n"
            stderr = ""
        result = rs.probe_reviewer_quota(resolved, run_fn=lambda *a, **k: FakeResult())
        self.assertTrue(result["available"])

    def test_nonzero_exit_is_unavailable(self):
        resolved = rs.ResolvedReviewer(key="codex-gpt", model="gpt-5.2", vendor="openai",
                                        cli="codex", command="false", extra={})
        class FakeResult:
            returncode = 1
            stdout = ""
            stderr = "some error"
        result = rs.probe_reviewer_quota(resolved, run_fn=lambda *a, **k: FakeResult())
        self.assertFalse(result["available"])

    def test_usage_limit_text_is_unavailable_even_on_exit_zero(self):
        # confirmed live: codex can print a usage-limit message and still
        # be worth treating as unavailable regardless of exit code
        resolved = rs.ResolvedReviewer(key="codex-gpt", model="gpt-5.6-luna", vendor="openai",
                                        cli="codex", command="echo 'usage limit reached'", extra={})
        class FakeResult:
            returncode = 0
            stdout = "You have hit your usage limit.\n"
            stderr = ""
        result = rs.probe_reviewer_quota(resolved, run_fn=lambda *a, **k: FakeResult())
        self.assertFalse(result["available"])

    def test_timeout_is_unavailable(self):
        resolved = rs.ResolvedReviewer(key="codex-gpt", model="gpt-5.2", vendor="openai",
                                        cli="codex", command="sleep 999", extra={})
        def fake_run(*a, **k):
            raise subprocess.TimeoutExpired(cmd="sleep 999", timeout=30)
        result = rs.probe_reviewer_quota(resolved, run_fn=fake_run)
        self.assertFalse(result["available"])


class TestRefreshQuotaCache(unittest.TestCase):
    def setUp(self):
        self.config = {
            "policy": {"mode": "single", "ladder": ["codex-gpt"]},
            "reviewers": [{"key": "codex-gpt", "model": "gpt-5.2", "vendor": "openai",
                           "cli": "codex", "command": "echo ok"}],
        }

    def test_probes_missing_entries(self):
        class FakeResult:
            returncode = 0
            stdout = "ok"
            stderr = ""
        updated = rs.refresh_quota_cache(self.config, ["codex-gpt"], existing={},
                                          ttl_seconds=3600, run_fn=lambda *a, **k: FakeResult())
        self.assertTrue(updated["codex-gpt"]["available"])

    def test_skips_fresh_entries(self):
        existing = {"codex-gpt": {"available": False, "checked_at": time.time()}}
        def fail_if_called(*a, **k):
            raise AssertionError("should not re-probe a fresh entry")
        updated = rs.refresh_quota_cache(self.config, ["codex-gpt"], existing,
                                          ttl_seconds=3600, run_fn=fail_if_called)
        self.assertFalse(updated["codex-gpt"]["available"])  # untouched

    def test_reprobes_stale_entries(self):
        existing = {"codex-gpt": {"available": False, "checked_at": time.time() - 7200}}
        class FakeResult:
            returncode = 0
            stdout = "ok"
            stderr = ""
        updated = rs.refresh_quota_cache(self.config, ["codex-gpt"], existing,
                                          ttl_seconds=3600, run_fn=lambda *a, **k: FakeResult())
        self.assertTrue(updated["codex-gpt"]["available"])  # re-probed, flipped to available
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python3 -m unittest tests.test_review_spec.TestRenderReviewerCommand tests.test_review_spec.TestProbeReviewerQuota tests.test_review_spec.TestRefreshQuotaCache -v`

Expected: FAIL — `AttributeError: module 'review_spec' has no attribute 'render_reviewer_command'`.

- [ ] **Step 3: Implement**

Append to `tools/review-spec.py`:

```python
# ── Quota probing ─────────────────────────────────────────────────────────

_UNAVAILABLE_SIGNALS = ("usage limit", "quota", "rate limit", "rate_limit")


def render_reviewer_command(resolved: "ResolvedReviewer", prompt: str) -> str:
    """Fill a resolved reviewer's `command` template. {model} and {prompt}
    are always available; any of the entry's extra fields (effort,
    service_tier, ...) fill their own {placeholder} when the command
    references it. Shared by probe_reviewer_quota (below) and Task 11's
    real dispatch, so probing and dispatching can never drift apart.

    Only {prompt} is shell-escaped (via shlex.quote) before substitution —
    it is free text built from document paths/content signals and MUST
    survive as exactly one shell argument no matter what it contains (this
    fixes a real command-injection risk: an unescaped {prompt} spliced into
    a `shell=True` command string via a document path containing `"`, `$`,
    or `` ` `` would corrupt or inject into the command). {model} and any
    `extra` field are deliberately left unescaped — they're short,
    human-typed config values, and some CLIs need their own literal
    quoting idiom in the template around them (e.g. codex's `-c
    key='"{effort}"'`), which auto-quoting would break. Command templates
    must therefore write a bare `{prompt}` (never `"{prompt}"` or
    `'{prompt}'` — the quoting is already applied here)."""
    return resolved.command.format(model=resolved.model, prompt=shlex.quote(prompt),
                                    **resolved.extra)


def probe_reviewer_quota(resolved: "ResolvedReviewer", run_fn=subprocess.run) -> dict:
    """Native (cli-less) entries are never probed — there is nothing to
    shell out to, and dispatch mechanics there are the current session's
    own concern, not a quota this module can observe. For CLI entries: run
    a trivial prompt through the reviewer's own command and classify
    availability generically — a nonzero exit code, or stdout/stderr
    containing a case-insensitive usage/quota/rate-limit phrase, means
    unavailable; anything else (including plain success) means available.
    This generic heuristic is what makes the confirmed codex usage-limit
    error (see references/review-spec/cli-profiles/codex.md) detectable
    without a CLI-specific parser."""
    if not resolved.cli or not resolved.command:
        return {"available": True, "checked_at": time.time()}
    filled = render_reviewer_command(resolved, "Only say: Hello world!")
    try:
        result = run_fn(filled, shell=True, capture_output=True, text=True,
                         check=False, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return {"available": False, "checked_at": time.time()}
    combined = (result.stdout + result.stderr).lower()
    if result.returncode != 0 or any(s in combined for s in _UNAVAILABLE_SIGNALS):
        return {"available": False, "checked_at": time.time()}
    return {"available": True, "checked_at": time.time()}


def refresh_quota_cache(config: dict, ladder_keys: list, existing: dict, ttl_seconds: int,
                         run_fn=subprocess.run) -> dict:
    """Returns an updated quota dict: probes only ladder_keys entries that
    are missing or whose last probe is older than ttl_seconds; entries
    still fresh are left untouched (no re-probe, no wasted quota-checking
    quota)."""
    reviewers = config.get("reviewers", [])
    updated = dict(existing)
    now = time.time()
    for key in ladder_keys:
        current = updated.get(key)
        if current is not None and now - current.get("checked_at", 0) < ttl_seconds:
            continue
        entry = _reviewer_by_key(reviewers, key)
        if entry is None:
            continue
        updated[key] = probe_reviewer_quota(_to_resolved(entry), run_fn=run_fn)
    return updated
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python3 -m unittest tests.test_review_spec -v`

Expected: PASS, all tests including Task 5's.

- [ ] **Step 5: Commit**

```bash
git add tools/review-spec.py tests/test_review_spec.py
git commit -m "feat(review-spec): add quota probing (render_reviewer_command, probe_reviewer_quota, refresh_quota_cache)"
```

---

### Task 7: Findings merge (Step 1.5 — double-review reconciliation)

**Files:**
- Modify: `tools/review-spec.py`
- Test: `tests/test_review_spec.py`

**Interfaces:**
- Consumes: nothing from Tasks 2–6 (pure text-in/text-out, deliberately
  decoupled so it's testable with plain fixture strings).
- Produces: `parse_findings(report_text: str) -> list[dict]`,
  `report_has_status(report_text: str) -> bool`,
  `merge_findings(reports: list[tuple[str, str]]) -> list[dict]`,
  `render_merged_report(findings: list[dict], doc_paths: str) -> str`.
  Consumed by Task 8 (`merge-reports` uses `report_has_status` to detect a
  failed/non-conforming reviewer *before* merging — see that task's
  "Bug fixed here" note) and Task 11 (Step 1.5).

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_review_spec.py`:

```python
_REPORT_A = """## Review: spec.md
### Document Type
superpowers · design
### CRITICAL
- **Missing field** — Location: §2.1. Required: add the field. Why: breaks downstream.
### HIGH
- **Vague wording** — Location: §3. Required: clarify. Why: ambiguous.
### Status: Issues Found — fix and re-invoke
"""

_REPORT_B = """## Review: spec.md
### Document Type
superpowers · design
### CRITICAL
- **Missing field entirely** — Location: §2.1. Required: define it. Why: undefined behavior.
### MEDIUM
- **Typo** — Location: §1. Required: fix spelling. Why: readability.
### Status: Issues Found — fix and re-invoke
"""


class TestParseFindings(unittest.TestCase):
    def test_extracts_title_location_required_why_and_severity(self):
        findings = rs.parse_findings(_REPORT_A)
        self.assertEqual(len(findings), 2)
        self.assertEqual(findings[0]["severity"], "CRITICAL")
        self.assertEqual(findings[0]["title"], "Missing field")
        self.assertEqual(findings[0]["location"], "§2.1")
        self.assertEqual(findings[1]["severity"], "HIGH")

    def test_report_with_no_findings_returns_empty_list(self):
        approved = "## Review: spec.md\n### Status: Approved\n"
        self.assertEqual(rs.parse_findings(approved), [])

    def test_cross_document_consistency_bullets_are_not_misattributed(self):
        report = """## Review: a.md, b.md
### HIGH
- **Real high finding** — Location: §1. Required: fix it. Why: reasons.
### Cross-Document Consistency
- **Docs disagree** — Location: §2 vs §3. Required: reconcile. Why: contradiction.
### Status: Issues Found — fix and re-invoke
"""
        findings = rs.parse_findings(report)
        self.assertEqual(len(findings), 2)
        self.assertEqual(findings[0]["severity"], "HIGH")
        self.assertEqual(findings[1]["severity"], "CROSS-DOC")
        self.assertEqual(findings[1]["title"], "Docs disagree")


class TestReportHasStatus(unittest.TestCase):
    def test_true_when_status_line_present(self):
        self.assertTrue(rs.report_has_status(_REPORT_A))

    def test_false_for_garbage_text(self):
        self.assertFalse(rs.report_has_status("some random CLI error output, no status here"))

    def test_false_for_empty_text(self):
        self.assertFalse(rs.report_has_status(""))


class TestMergeFindings(unittest.TestCase):
    def test_same_severity_and_location_merges_into_one_tagged_entry(self):
        merged = rs.merge_findings([("claude-opus", _REPORT_A), ("codex-gpt", _REPORT_B)])
        crit = [f for f in merged if f["severity"] == "CRITICAL"]
        self.assertEqual(len(crit), 1)  # both CRITICAL findings share (CRITICAL, "§2.1")
        self.assertEqual(crit[0]["reviewers"], ["claude-opus", "codex-gpt"])

    def test_distinct_locations_stay_separate_each_tagged_with_its_own_source(self):
        merged = rs.merge_findings([("claude-opus", _REPORT_A), ("codex-gpt", _REPORT_B)])
        high = [f for f in merged if f["severity"] == "HIGH"]
        medium = [f for f in merged if f["severity"] == "MEDIUM"]
        self.assertEqual(high[0]["reviewers"], ["claude-opus"])
        self.assertEqual(medium[0]["reviewers"], ["codex-gpt"])

    def test_single_report_passthrough(self):
        merged = rs.merge_findings([("claude-opus", _REPORT_A)])
        self.assertEqual(len(merged), 2)
        self.assertTrue(all(f["reviewers"] == ["claude-opus"] for f in merged))

    def test_two_distinct_findings_from_the_same_reviewer_at_the_same_location_both_survive(self):
        # regression: a single report can legitimately raise two different
        # findings at the same Location (e.g. two separate HIGH issues both
        # in "§3") — these must never collapse into one just because their
        # (severity, location) pair matches; only cross-reviewer matches at
        # the same (severity, location) should merge.
        report = """## Review: spec.md
### HIGH
- **First issue** — Location: §3. Required: fix A. Why: reason A.
- **Second issue** — Location: §3. Required: fix B. Why: reason B.
### Status: Issues Found — fix and re-invoke
"""
        merged = rs.merge_findings([("claude-opus", report)])
        self.assertEqual(len(merged), 2)
        titles = {f["title"] for f in merged}
        self.assertEqual(titles, {"First issue", "Second issue"})
        self.assertTrue(all(f["reviewers"] == ["claude-opus"] for f in merged))


class TestRenderMergedReport(unittest.TestCase):
    def test_groups_by_severity_and_tags_reviewers(self):
        merged = rs.merge_findings([("claude-opus", _REPORT_A), ("codex-gpt", _REPORT_B)])
        rendered = rs.render_merged_report(merged, "spec.md")
        self.assertIn("### CRITICAL", rendered)
        self.assertIn("### HIGH", rendered)
        self.assertIn("### MEDIUM", rendered)
        self.assertIn("(Reviewers: claude-opus, codex-gpt)", rendered)
        self.assertIn("### Status: Issues Found — fix and re-invoke", rendered)

    def test_no_findings_renders_approved_status(self):
        rendered = rs.render_merged_report([], "spec.md")
        self.assertIn("### Status: Approved", rendered)
        self.assertNotIn("Issues Found", rendered)

    def test_cross_doc_findings_render_under_their_own_heading(self):
        findings = [{"severity": "CROSS-DOC", "title": "Docs disagree", "location": "§2 vs §3",
                     "required": "reconcile", "why": "contradiction", "reviewers": ["claude-opus"]}]
        rendered = rs.render_merged_report(findings, "a.md, b.md")
        self.assertIn("### Cross-Document Consistency", rendered)
        self.assertNotIn("### CROSS-DOC", rendered)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python3 -m unittest tests.test_review_spec.TestParseFindings tests.test_review_spec.TestMergeFindings tests.test_review_spec.TestRenderMergedReport -v`

Expected: FAIL — `AttributeError: module 'review_spec' has no attribute 'parse_findings'`.

- [ ] **Step 3: Implement**

Append to `tools/review-spec.py`:

```python
# ── Findings merge (Step 1.5 double-review reconciliation) ──────────────

_SEVERITY_HEADINGS = {
    "CRITICAL": "CRITICAL", "HIGH": "HIGH", "MEDIUM": "MEDIUM",
    "Cross-Document Consistency": "CROSS-DOC",
}
_SEVERITY_RE = re.compile(
    r"^### (CRITICAL|HIGH|MEDIUM|Cross-Document Consistency)\s*$", re.MULTILINE)
_BULLET_RE = re.compile(
    r"^- \*\*(.+?)\*\* — Location: (.+?)\. Required: (.+?)\. Why: (.+?)\.\s*$",
    re.MULTILINE)


def report_has_status(report_text: str) -> bool:
    """True iff report_text contains a `### Status:` line — the one thing
    every conforming reviewer report guarantees (per review-spec-checklist's
    output template). Used by the merge-reports CLI subcommand (Task 8) to
    detect a failed/non-conforming/empty reviewer report BEFORE merging, so
    a broken external CLI call can never silently read as a clean Approved
    merge (it never produces findings, so an unguarded merge would treat it
    as "zero issues")."""
    return "### Status:" in report_text


def parse_findings(report_text: str) -> list:
    """[{severity, title, location, required, why}] in document order, per
    the review-spec-checklist output template (`### SEVERITY` headings,
    including the `### Cross-Document Consistency` section — normalized to
    the `"CROSS-DOC"` severity tag — followed by `- **title** — Location:
    .... Required: .... Why: ....` bullets). A bullet appearing before any
    recognized heading (malformed input) gets severity None."""
    sev_matches = list(_SEVERITY_RE.finditer(report_text))
    findings = []
    for m in _BULLET_RE.finditer(report_text):
        pos = m.start()
        severity = None
        for i, sm in enumerate(sev_matches):
            nxt = sev_matches[i + 1].start() if i + 1 < len(sev_matches) else len(report_text)
            if sm.start() <= pos < nxt:
                severity = _SEVERITY_HEADINGS[sm.group(1)]
                break
        findings.append({"severity": severity, "title": m.group(1), "location": m.group(2),
                          "required": m.group(3), "why": m.group(4)})
    return findings


def merge_findings(reports: list) -> list:
    """reports: [(reviewer_key, report_text), ...]. Union of every finding,
    each tagged with which reviewer(s) surfaced it. Findings sharing the
    exact same (severity, location) ACROSS DIFFERENT reports are combined
    into one entry with both reviewers tagged — deliberately NOT fuzzy
    title-text matching (two models rarely word the same finding
    identically), so this only merges the case where they flag literally
    the same passage. Within a single report, two distinct findings that
    happen to share a (severity, location) — e.g. two separate HIGH issues
    both in "§3" — are never collapsed into each other: only the first
    occurrence per report claims the bare (severity, location) key; any
    later same-report finding at that same key is disambiguated by adding
    its own title into the key, so it always survives as its own entry."""
    merged = {}
    order = []
    for key, text in reports:
        seen_this_report = set()
        for f in parse_findings(text):
            dedup_key = (f["severity"], f["location"])
            if dedup_key in seen_this_report:
                dedup_key = (f["severity"], f["location"], f["title"])
            seen_this_report.add((f["severity"], f["location"]))
            if dedup_key in merged:
                merged[dedup_key]["reviewers"].append(key)
            else:
                entry = dict(f)
                entry["reviewers"] = [key]
                merged[dedup_key] = entry
                order.append(dedup_key)
    return [merged[k] for k in order]


def render_merged_report(findings: list, doc_paths: str) -> str:
    """Renders CRITICAL/HIGH/MEDIUM under their own headings and CROSS-DOC
    findings under the same `### Cross-Document Consistency` heading the
    source reports use (never a raw `### CROSS-DOC`, which isn't part of
    the output template). A finding whose severity didn't match any
    recognized heading (malformed input) falls back to MEDIUM, tagged
    exactly as parsed — this can only happen on non-conforming input,
    since report_has_status (Task 8) already filters those out before this
    function ever runs. Deliberately drops each source report's own
    `### Document Type`/`### Files Read` lines — those describe a single
    reviewer's run, not a property of the merge — in favor of a fixed
    `cross-ai merged` marker."""
    by_sev = {"CRITICAL": [], "HIGH": [], "MEDIUM": [], "CROSS-DOC": []}
    for f in findings:
        sev = f["severity"] if f["severity"] in by_sev else "MEDIUM"
        by_sev[sev].append(f)
    lines = [f"## Review: {doc_paths}", "### Document Type", "cross-ai merged"]
    any_issues = any(by_sev.values())
    heading_for = {"CRITICAL": "### CRITICAL", "HIGH": "### HIGH", "MEDIUM": "### MEDIUM",
                   "CROSS-DOC": "### Cross-Document Consistency"}
    for sev in ("CRITICAL", "HIGH", "MEDIUM", "CROSS-DOC"):
        items = by_sev.get(sev, [])
        if not items:
            continue
        lines.append(heading_for[sev])
        for f in items:
            tag = ", ".join(f["reviewers"])
            lines.append(f"- **{f['title']}** — Location: {f['location']}. "
                          f"Required: {f['required']}. Why: {f['why']}. (Reviewers: {tag})")
    lines.append("### Status: Issues Found — fix and re-invoke" if any_issues else "### Status: Approved")
    return "\n".join(lines) + "\n"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python3 -m unittest tests.test_review_spec -v`

Expected: PASS, all tests including Tasks 2–5's.

- [ ] **Step 5: Commit**

```bash
git add tools/review-spec.py tests/test_review_spec.py
git commit -m "feat(review-spec): add double-review findings merge (union + reviewer tags)"
```

---

### Task 8: CLI entrypoint (argparse subcommands)

**Bug fixed here (caught by the cross-AI dry run):** an earlier draft had
`resolve-reviewers` take a single `--config <path>` and call
`cfg_load_toml` directly — bypassing Task 2's `cfg_resolve` entirely, so
the tested local/global `strategy` merge never actually ran in production.
Fixed: `resolve-reviewers` takes `--cwd <path>` and calls `cfg_resolve(cwd,
os.environ)`, exactly like every other consumer must.

**Second bug fixed here (caught by the live Opus-5 re-review — see this
plan's Self-review notes):** `merge-reports`'s first draft unconditionally
merged whatever it could read, so a failed/unreadable/non-conforming
external reviewer report (a garbage CLI error, a truncated file) parsed as
zero findings and merged into a false `### Status: Approved` for the whole
run. Fixed: each report is checked via `report_has_status` (Task 7) before
merging; if any is missing its `### Status:` line, `merge-reports` prints
a plain diagnostic with **no** `### Status:` line of its own and returns 0
— `review-spec/SKILL.md`'s existing Step 2 already treats "No Status
line" as "surface a failure" (a rule that predates this plan), so this
reuses that guard instead of inventing a new one.

**Files:**
- Modify: `tools/review-spec.py`
- Modify: `Makefile` (add `tests.test_review_spec` to the `test:` target)
- Test: `tests/test_review_spec.py`

**Interfaces:**
- Consumes: every function from Tasks 2–7.
- Produces: a `main(argv: list) -> int` function and `if __name__ ==
  "__main__": sys.exit(main(sys.argv[1:]))`, with subcommands
  `detect-runtimes` (with `--save <path>`), `probe-quota`,
  `resolve-reviewers`, `merge-reports` (fails closed — see "Bug fixed
  here" below — via `report_has_status`, Task 7), `render-toml`,
  `render-command` (the orchestrator's only way to reach Task 6's
  `render_reviewer_command` from a `Bash` dispatch, since it's Python —
  see Task 11 Step 3).
  Consumed by Task 10 (`review-spec-config`) and Task 11 (orchestrator's
  `Bash` calls), both of which shell out to `python3 tools/review-spec.py
  <subcommand> ...` rather than importing the module directly (they run
  from Claude Code's `Bash` tool, not from Python).

- [ ] **Step 1: Write the failing tests**

Add `from unittest import mock` to `tests/test_review_spec.py`'s import
block at the top (not there yet — needed by the `mock.patch.object` calls
below). Then add to `tests/test_review_spec.py`:

```python
class TestMainCli(unittest.TestCase):
    def test_detect_runtimes_prints_json_snapshot(self):
        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = rs.main(["detect-runtimes"], which_fn=lambda n: None, run_fn=lambda *a, **k: None)
        self.assertEqual(code, 0)
        parsed = json.loads(buf.getvalue())
        self.assertIn("clis", parsed)

    def test_detect_runtimes_save_writes_cache_file(self):
        with tempfile.TemporaryDirectory() as d:
            save_path = os.path.join(d, "runtimes.json")
            code = rs.main(["detect-runtimes", "--save", save_path],
                            which_fn=lambda n: None, run_fn=lambda *a, **k: None)
            self.assertEqual(code, 0)
            self.assertIn("clis", rs.cache_read_json(save_path))

    def test_resolve_reviewers_uses_cfg_resolve_local_global_merge(self):
        # regression test for the CRITICAL bug: resolve-reviewers must go
        # through cfg_resolve (local/global + strategy), not a single
        # --config path — write ONLY a local file that overrides one field
        # of a global-declared reviewer, and confirm the override lands.
        import io
        from contextlib import redirect_stdout
        with tempfile.TemporaryDirectory() as cwd, tempfile.TemporaryDirectory() as home:
            os.makedirs(os.path.join(home, ".config", "ai-kit"))
            rs.cfg_write_toml(os.path.join(home, ".config", "ai-kit", "review-spec.toml"), {
                "policy": {"mode": "single", "ladder": ["codex-gpt"]},
                "reviewers": [{"key": "codex-gpt", "model": "gpt-5.2", "vendor": "openai"}],
            })
            os.makedirs(os.path.join(cwd, ".aikit"))
            with open(os.path.join(cwd, ".aikit", "review-spec.toml"), "w", encoding="utf-8") as f:
                f.write('[[reviewers]]\nkey = "codex-gpt"\nmodel = "gpt-5.2-mini"\n')
            quota_path = os.path.join(cwd, "quota.json")
            rs.cache_write_json(quota_path, {})
            buf = io.StringIO()
            env = {"HOME": home}
            with mock.patch.object(rs.os, "environ", env), redirect_stdout(buf):
                code = rs.main(["resolve-reviewers", "--cwd", cwd, "--quota", quota_path,
                                 "--source-vendor", "anthropic", "--cross-ai"])
            self.assertEqual(code, 0)
            parsed = json.loads(buf.getvalue())
            self.assertEqual(parsed[0]["model"], "gpt-5.2-mini")  # local override applied

    def test_probe_quota_refreshes_stale_entries_and_writes_cache(self):
        with tempfile.TemporaryDirectory() as cwd, tempfile.TemporaryDirectory() as home:
            os.makedirs(os.path.join(home, ".config", "ai-kit"))
            rs.cfg_write_toml(os.path.join(home, ".config", "ai-kit", "review-spec.toml"), {
                "policy": {"mode": "single", "ladder": ["codex-gpt"]},
                "reviewers": [{"key": "codex-gpt", "model": "gpt-5.2", "vendor": "openai",
                               "cli": "codex", "command": "echo ok"}],
            })
            quota_path = os.path.join(cwd, "quota.json")
            env = {"HOME": home}
            with mock.patch.object(rs.os, "environ", env):
                code = rs.main(["probe-quota", "--cwd", cwd, "--quota-path", quota_path])
            self.assertEqual(code, 0)
            written = rs.cache_read_json(quota_path)
            self.assertTrue(written["codex-gpt"]["available"])

    def test_merge_reports_reads_files_and_prints_markdown(self):
        import io
        from contextlib import redirect_stdout
        with tempfile.TemporaryDirectory() as d:
            path_a = os.path.join(d, "a.md")
            path_b = os.path.join(d, "b.md")
            with open(path_a, "w", encoding="utf-8") as f:
                f.write(_REPORT_A)
            with open(path_b, "w", encoding="utf-8") as f:
                f.write(_REPORT_B)
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = rs.main(["merge-reports", "--doc-paths", "spec.md",
                                 "claude-opus=" + path_a, "codex-gpt=" + path_b])
            self.assertEqual(code, 0)
            self.assertIn("### CRITICAL", buf.getvalue())

    def test_merge_reports_fails_closed_on_a_non_conforming_report(self):
        # regression: a garbage/failed external CLI report (no Status
        # line) must never silently merge into a false Approved
        import io
        from contextlib import redirect_stdout
        with tempfile.TemporaryDirectory() as d:
            path_a = os.path.join(d, "a.md")
            path_b = os.path.join(d, "b.md")
            with open(path_a, "w", encoding="utf-8") as f:
                f.write(_REPORT_A)
            with open(path_b, "w", encoding="utf-8") as f:
                f.write("codex: error: usage limit exceeded\n")  # no ### Status: line
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = rs.main(["merge-reports", "--doc-paths", "spec.md",
                                 "claude-opus=" + path_a, "codex-gpt=" + path_b])
            self.assertEqual(code, 0)
            self.assertNotIn("### Status:", buf.getvalue())
            self.assertIn("codex-gpt", buf.getvalue())

    def test_render_command_fills_the_indexed_reviewer(self):
        import io
        from contextlib import redirect_stdout
        with tempfile.TemporaryDirectory() as d:
            reviewers_path = os.path.join(d, "reviewers.json")
            with open(reviewers_path, "w", encoding="utf-8") as f:
                json.dump([{"key": "codex-gpt", "model": "gpt-5.2", "vendor": "openai",
                            "cli": "codex", "command": "codex exec -m {model} {prompt}",
                            "extra": {}}], f)
            prompt_path = os.path.join(d, "prompt.txt")
            with open(prompt_path, "w", encoding="utf-8") as f:
                f.write("hello")
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = rs.main(["render-command", "--reviewers-json", reviewers_path,
                                 "--index", "0", "--prompt-file", prompt_path])
            self.assertEqual(code, 0)
            self.assertEqual(buf.getvalue().strip(), "codex exec -m gpt-5.2 hello")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python3 -m unittest tests.test_review_spec.TestMainCli -v`

Expected: FAIL — `AttributeError: module 'review_spec' has no attribute 'main'`.

- [ ] **Step 3: Implement**

Append to `tools/review-spec.py`:

```python
# ── CLI entrypoint ────────────────────────────────────────────────────────

def main(argv: list, which_fn=shutil.which, run_fn=subprocess.run) -> int:
    import argparse

    parser = argparse.ArgumentParser(prog="review-spec")
    sub = parser.add_subparsers(dest="command", required=True)

    p_detect = sub.add_parser("detect-runtimes")
    p_detect.add_argument("--save", default=None, help="write the snapshot to this path via cache_write_json")

    p_quota = sub.add_parser("probe-quota")
    p_quota.add_argument("--cwd", required=True)
    p_quota.add_argument("--quota-path", required=True)

    p_resolve = sub.add_parser("resolve-reviewers")
    p_resolve.add_argument("--cwd", required=True)
    p_resolve.add_argument("--quota", required=True)
    p_resolve.add_argument("--source-vendor", default="")
    p_resolve.add_argument("--cross-ai", action="store_true")

    p_merge = sub.add_parser("merge-reports")
    p_merge.add_argument("--doc-paths", required=True)
    p_merge.add_argument("reports", nargs="+", help="key=path/to/report.md")

    p_toml = sub.add_parser("render-toml")
    p_toml.add_argument("--json-config", required=True, help="path to a JSON file shaped like the TOML config")

    p_render = sub.add_parser("render-command")
    p_render.add_argument("--reviewers-json", required=True,
                           help="path to resolve-reviewers' saved JSON array output")
    p_render.add_argument("--index", type=int, required=True,
                           help="0 for the primary/only reviewer, 1 for the secondary")
    p_render.add_argument("--prompt-file", required=True)

    args = parser.parse_args(argv)

    if args.command == "detect-runtimes":
        snapshot = build_runtimes_snapshot(which_fn=which_fn, run_fn=run_fn)
        if args.save:
            cache_write_json(args.save, snapshot)
        print(json.dumps(snapshot))
        return 0

    if args.command == "probe-quota":
        config = cfg_resolve(args.cwd, dict(os.environ))
        ladder = config.get("policy", {}).get("ladder", [])
        existing = cache_read_json(args.quota_path) or {}
        updated = refresh_quota_cache(config, ladder, existing, QUOTA_TTL_SECONDS, run_fn=run_fn)
        cache_write_json(args.quota_path, updated)
        print(json.dumps(updated))
        return 0

    if args.command == "resolve-reviewers":
        config = cfg_resolve(args.cwd, dict(os.environ))
        quota = cache_read_json(args.quota) or {}
        reviewers = resolve_reviewers(config, quota, args.source_vendor, args.cross_ai)
        print(json.dumps([r._asdict() for r in reviewers]))
        return 0

    if args.command == "merge-reports":
        reports = []
        unreadable = []
        for item in args.reports:
            key, _, path = item.partition("=")
            try:
                with open(path, encoding="utf-8") as f:
                    text = f.read()
            except OSError:
                unreadable.append(key)
                continue
            if not report_has_status(text):
                unreadable.append(key)
                continue
            reports.append((key, text))
        if unreadable:
            # Deliberately prints NO "### Status:" line — review-spec/SKILL.md's
            # existing Step 2 already treats "No Status line" as a failure to
            # surface (its own long-standing rule, unrelated to this plan), so a
            # failed/unreadable external reviewer can never silently merge into
            # a false "### Status: Approved". No new orchestrator special-case
            # needed.
            print(f"merge-reports: reviewer(s) {', '.join(unreadable)} produced "
                  f"no readable report with a Status line — cannot merge.")
            return 0
        merged = merge_findings(reports)
        print(render_merged_report(merged, args.doc_paths))
        return 0

    if args.command == "render-toml":
        with open(args.json_config, encoding="utf-8") as f:
            config = json.load(f)
        print(cfg_render_toml(config))
        return 0

    if args.command == "render-command":
        with open(args.reviewers_json, encoding="utf-8") as f:
            reviewers = json.load(f)
        r = reviewers[args.index]
        resolved = ResolvedReviewer(key=r["key"], model=r["model"], vendor=r["vendor"],
                                     cli=r["cli"], command=r["command"], extra=r["extra"])
        with open(args.prompt_file, encoding="utf-8") as f:
            prompt = f.read()
        print(render_reviewer_command(resolved, prompt))
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python3 -m unittest tests.test_review_spec -v`

Expected: PASS, all tests.

- [ ] **Step 5: Add the new test module to the Makefile's `test:` target**

In `Makefile`, change:

```makefile
test:
	python3 -m unittest tests.test_setup tests.test_status_line tests.test_external_segments tests.test_statusline_doctor tests.test_arch tests.test_markdown_to_pdf tests.test_worktree_e2e tests.test_wizard_pty tests.test_system_memory_e2e
	bash tests/test_install.sh
```

to:

```makefile
test:
	python3 -m unittest tests.test_setup tests.test_status_line tests.test_external_segments tests.test_statusline_doctor tests.test_arch tests.test_markdown_to_pdf tests.test_worktree_e2e tests.test_wizard_pty tests.test_system_memory_e2e tests.test_review_spec
	bash tests/test_install.sh
```

- [ ] **Step 6: Commit**

```bash
git add tools/review-spec.py tests/test_review_spec.py Makefile
git commit -m "feat(review-spec): add CLI entrypoint (detect-runtimes, probe-quota, resolve-reviewers, merge-reports, render-toml); wire cfg_resolve; register with make test"
```

---

### Task 9: CLI profile reference docs

**Files:**
- Create: `references/review-spec/cli-profiles/claude.md`
- Create: `references/review-spec/cli-profiles/codex.md`
- Create: `references/review-spec/cli-profiles/opencode.md`
- Create: `references/review-spec/cli-profiles/grok.md`
- Create: `references/review-spec/cli-profiles/cursor-agent.md`
- Create: `references/review-spec/cli-profiles/gemini.md`
- Test: none (reference docs, not code)

**Interfaces:**
- Produces: the profile paths `review-spec-config` (Task 10) reads when
  helping the user write `[[reviewers]]` entries.

- [ ] **Step 1: Write `references/review-spec/cli-profiles/claude.md`**

```markdown
---
id: claude
display_name: Claude Code CLI
status: confirmed
detect: "which claude"
last_verified: 2026-08-27
---

# claude — reviewer profile

Non-interactive: `-p`/`--print` (print response and exit). Model selection:
`--model <model>`. Output shaping: `--output-format <format>` (only works
with `--print`).

```bash
claude -p --model <model> --output-format text "<prompt>"
```

Quota/context-window introspection: unconfirmed syntax — research during
the `review-spec-config` implementation task if a dedicated Claude usage
subcommand exists; otherwise rely on the same "low-effort call, detect a
usage-limit error" mechanism confirmed for `codex` (below).
```

- [ ] **Step 2: Write `references/review-spec/cli-profiles/codex.md`**

```markdown
---
id: codex
display_name: OpenAI Codex CLI
status: confirmed
detect: "which codex"
last_verified: 2026-08-27
---

# codex — reviewer profile

Non-interactive: `codex exec`. Model: `-m <model>`. Reasoning effort and
service speed tier are SEPARATE knobs, each set via `-c key='"value"'`:

```bash
codex exec --sandbox read-only --skip-git-repo-check \
  -m <model> \
  -c model_reasoning_effort='"<low|medium|high|xhigh>"' \
  -c service_tier='"<fast|...>"' \
  "<prompt>" 2>/dev/null
```

**Quota probe — confirmed live**: a low-effort/fast-tier call against an
exhausted quota returns a usage-limit error. Example that produced exactly
that error during this design's research:

```bash
codex exec -m gpt-5.6-luna -c model_reasoning_effort='"low"' -c service_tier='"fast"' 'Only say: Hello world!'
```

This is the reference implementation for the "cheap probe, detect the
error" quota-check mechanism — parse the exit code / stderr for a
usage-limit signal rather than looking for a dedicated quota subcommand.
```

- [ ] **Step 3: Write `references/review-spec/cli-profiles/opencode.md`**

```markdown
---
id: opencode
display_name: OpenCode CLI
status: confirmed
detect: "which opencode"
last_verified: 2026-08-27
---

# opencode — reviewer profile

**Multi-provider by design** — `opencode models` lists every model it
routes to, under its own provider namespaces. Confirmed live output
includes third-party models with no separate CLI needed:
`opencode-go/kimi-k3`, `opencode-go/qwen3.8-max`, `opencode-go/grok-4.6`,
`opencode-go/gpt-5.6-luna`, plus `ollama-cloud/*` and local-model entries.
This is how Kimi/Qwen reviewers are reachable in this design without a
dedicated Kimi/Qwen CLI profile — set `cli = "opencode"` and
`model = "opencode-go/kimi-k3"` (or whichever listed id), with `vendor`
set explicitly to the model's real maker (`moonshot`, `alibaba`, etc.), not
`"opencode"` itself.

Non-interactive: `opencode run [message..]`. Model: `-m/--model
<provider/model>`.

```bash
opencode run -m <provider/model> "<prompt>"
```

`opencode stats` shows token usage/cost statistics — likely the quota
introspection source; exact parseable shape unconfirmed, research during
implementation.
```

- [ ] **Step 4: Write `references/review-spec/cli-profiles/grok.md`**

```markdown
---
id: grok
display_name: Grok CLI (xAI)
status: confirmed
detect: "which grok"
last_verified: 2026-08-27
---

# grok — reviewer profile

Model: `-m/--model <MODEL>`. Output shaping: `--output-format
<OUTPUT_FORMAT>`; `--json-schema <SCHEMA>` for structured output (implies
`--output-format json`).

```bash
grok -m <model> --output-format json "<prompt>"
```

Quota/context-window introspection: unconfirmed syntax — research during
implementation.
```

- [ ] **Step 5: Write `references/review-spec/cli-profiles/cursor-agent.md`**

```markdown
---
id: cursor-agent
display_name: Cursor Agent CLI
status: stub (web-research only — not installed on the reference machine)
detect: "which cursor-agent"
last_verified: 2026-08-27
source: https://cursor.com/docs/cli/overview , https://cursor.com/docs/cli/using
---

# cursor-agent — reviewer profile (STUB — unverified live)

Non-interactive: `-p`/`--print`, combine with `--output-format json` (or
`text`). Model: `--model <name>`. `cursor-agent ls` lists sessions,
`cursor-agent resume` resumes one, `cursor-agent status` reports
auth/version (possibly a quota source — unconfirmed).

```bash
cursor-agent -p "<prompt>" --output-format json --model <model>
```

Not yet verified against a real installation. Verify all of the above with
`cursor-agent --help` before marking this profile `status: confirmed`.
```

- [ ] **Step 6: Write `references/review-spec/cli-profiles/gemini.md`**

```markdown
---
id: gemini
display_name: Gemini CLI
status: stub (carried over from the existing `gemini` skill's documented flags — not installed on the reference machine)
detect: "which gemini"
last_verified: 2026-08-27
---

# gemini — reviewer profile (STUB — unverified live on this machine)

Per the existing `gemini` skill (`~/.claude/skills/gemini/SKILL.md`):
model via `-m/--model <MODEL>`; **background/non-interactive runs require
`--approval-mode yolo`** (the `default` approval mode hangs indefinitely in
a non-interactive shell — do not use it here).

```bash
gemini -m <model> --approval-mode yolo "<prompt>"
```

Quota/context-window introspection: unconfirmed syntax — research during
implementation.
```

- [ ] **Step 7: Commit**

```bash
git add references/review-spec/cli-profiles/
git commit -m "docs(review-spec): add CLI profiles for claude, codex, opencode, grok (confirmed) + cursor-agent, gemini (stub)"
```

---

### Task 10: `review-spec-config` skill (new)

**Files:**
- Create: `skills/review-spec-config/SKILL.md`
- Test: none (interactive skill, no automated test — matches this repo's
  precedent for interactive/prose skills)

**Interfaces:**
- Consumes: `tools/review-spec.py`'s `detect-runtimes` and `render-toml`
  subcommands (Task 8), the CLI profiles (Task 9).
- Produces: writes `review-spec.toml` (global by default, `--local` for
  `./.aikit/review-spec.toml`) and `runtimes.json`. Consumed by
  `review-spec`'s Step 0.7 (Task 11).

- [ ] **Step 1: Write `skills/review-spec-config/SKILL.md`**

```markdown
---
name: review-spec-config
description: Interactive setup for review-spec's cross-AI reviewer config — detects installed CLIs/models, asks which to use as reviewers and in what priority, writes review-spec.toml. Use when the user asks to configure cross-AI review, or when review-spec warns no config exists. Supports --check-only (report availability, no writes) and --local (write ./.aikit/review-spec.toml instead of the global config).
---

## Your task

Set up (or refresh) `review-spec`'s cross-AI reviewer configuration.

### Step 0 — Locate `tools/review-spec.py` and the CLI profiles

`tools/review-spec.py` and `references/review-spec/cli-profiles/` live at
the ai-kit repo root, not inside any individually-installed skill
directory (`tools/setup.py` only symlinks `agents`/`commands`/`skills`),
so resolve them the same way `review-spec/SKILL.md` resolves its own
`TOOLS_PY`/`CLI_PROFILES_DIR` (see that skill's Step 0.7 point 0 — Task
11): take the first existing of, in order, `${CLAUDE_PLUGIN_ROOT}` (when
set), `~/.claude/skills/review-spec-config` (this skill's own installed
symlink), or the directory containing this `SKILL.md` directly (dev
checkout, no symlink); call that `SKILL_DIR`, then:

```bash
SKILL_DIR_REAL="$(realpath "$SKILL_DIR")"
KIT_ROOT="${SKILL_DIR_REAL%/skills/*}"
TOOLS_PY="$KIT_ROOT/tools/review-spec.py"
CLI_PROFILES_DIR="$KIT_ROOT/references/review-spec/cli-profiles"
```

### Step 1 — Detect

```bash
python3 "$TOOLS_PY" detect-runtimes --save ~/.cache/ai-kit/review-spec/runtimes.json
```

`--save` persists the snapshot immediately (via `cache_write_json` — see
Task 8), so `review-spec` doesn't have to re-detect next session; the
command also prints the same JSON to stdout. Parse it: for each CLI marked
`"installed": true`, note its path; for `opencode`, note its `models`
list.

If `--check-only` was passed: report which CLIs are installed, which have
a `review-spec.toml` reviewer entry already, and stop — do not write
anything.

### Step 2 — Ask

For each installed CLI (beyond the current session's own runtime), use
`AskUserQuestion` to ask whether the user wants it available as a cross-AI
reviewer. For `opencode`, additionally ask which of its listed models (if
any) to register as reviewer entries — read
`$CLI_PROFILES_DIR/opencode.md` first so you know real vendor attributions
for common model-id prefixes (Moonshot for `kimi-*`, Alibaba for `qwen*`,
xAI for `grok-*`, etc.) rather than guessing.

For each CLI the user wants, read its profile under
`$CLI_PROFILES_DIR/<id>.md` for the exact non-interactive command shape,
and ask the user to confirm/adjust: model id, `vendor`, and any extra
knobs (`effort`, `service_tier`, ...) that profile's `command` template
needs. **For a native (cli-less) reviewer entry** — e.g. the current
session's own runtime, or another Claude tier reachable without an
external CLI — `model` must be one of the four `Agent`-tool aliases
(`sonnet`/`opus`/`haiku`/`fable`), never a full model id like `"opus-5"`;
ask the user to pick one of those four rather than typing a version
string.

Then ask: `policy.mode` (`single` or `double`) and the `policy.ladder`
order (default to the order the user answered the per-CLI questions in,
but let them reorder).

### Step 3 — Write

Build the JSON shape `tools/review-spec.py`'s `render-toml` subcommand
expects (`{"policy": {...}, "reviewers": [...]}`), write it to a temp JSON
file, then:

```bash
python3 "$TOOLS_PY" render-toml --json-config <temp.json>
```

Write that output to the target path: `~/.config/ai-kit/review-spec.toml`
by default, or `./.aikit/review-spec.toml` if `--local` was passed (and
add a `strategy = "..."` line at the top if the user wants
`local-only` — ask; default `global-merge`, which needs no explicit line).
(The runtimes snapshot was already persisted in Step 1 via `--save` — no
separate write needed here.)

### Step 4 — Report

Print a short summary: which reviewers are now configured, in what
mode/order, and the path written to.
```

- [ ] **Step 2: Commit**

```bash
git add skills/review-spec-config/SKILL.md
git commit -m "feat(review-spec-config): add interactive cross-AI reviewer setup skill"
```

---

### Task 11: Orchestrator integration — `review-spec/SKILL.md`

**Files:**
- Modify: `skills/review-spec/SKILL.md`
- Test: none (orchestration prose — validated per spec §11 via manual dry
  run, listed in this task's steps)

**Interfaces:**
- Consumes: `tools/review-spec.py`'s `probe-quota`, `resolve-reviewers`,
  and `merge-reports` subcommands (Task 8), the renamed skills (Task 1).

- [ ] **Step 1: Add `--cross-ai`/`--no-cross-ai`/`--source-vendor` to the Inputs section**

In `skills/review-spec/SKILL.md`'s existing "## Inputs" section, extend
the "Document path(s)" bullet to also parse three optional flags from the
same invocation-arguments string (all three, unlike doc paths, have
defaults — never block on their absence):

```markdown
- **Flags (optional, parsed from the same invocation arguments):**
  `--cross-ai` (default) or `--no-cross-ai` — whether Step 0.7 attempts
  cross-AI reviewer resolution at all. `--source-vendor=<vendor>` (default
  `anthropic`, since this orchestrator only ever runs as a Claude Code
  skill) — the document's authoring vendor, used by Step 0.7's ladder walk
  to prefer an independent perspective. This is a **vendor** (`anthropic`,
  `openai`, `xai`, ...), matching the `vendor` field in `review-spec.toml`
  reviewer entries — not a model id, since deriving a vendor from an
  arbitrary model-id string has no sanctioned mapping (model names churn
  too fast to hardcode a lookup table).
```

- [ ] **Step 2: Add Step 0.7 after the existing Step 0.6**

Insert into `skills/review-spec/SKILL.md`, immediately after Step 0.6's
final paragraph (the one ending "...If no sibling context exists, pass
`none`."):

```markdown
## Step 0.7 — Resolve the reviewer list (cross-AI)

Runs once per invocation, after Step 0.6.

0. Resolve `KIT_ROOT`, `TOOLS_PY`, and `CLI_PROFILES_DIR` — needed because
   `tools/review-spec.py` and `references/review-spec/cli-profiles/`
   live at the ai-kit repo root, **not** inside any individually-installed
   skill directory, so neither `tools/setup.py`'s symlinks (which only
   cover `agents/commands/skills`, per its `CATEGORIES`) nor a
   sibling-of-`SKILL_DIR` shortcut (the trick `SEEDS_DIR` above uses,
   which only works because *both* `review-spec` and
   `review-spec-checklist` are independently symlinked into the same
   `~/.claude/skills/` tier) can reach them directly:
   ```bash
   # SKILL_DIR is already established above (the directory containing
   # THIS SKILL.md, resolved via the same CLAUDE_PLUGIN_ROOT /
   # ~/.claude/skills/review-spec / sibling-of-this-file fallback used for
   # SEEDS_DIR). realpath follows the ~/.claude/skills/review-spec symlink
   # (when installed) to the real repo checkout, so stripping the known
   # "/skills/review-spec" suffix off the end reliably yields the repo root
   # in every install shape: plugin, symlinked ~/.claude/skills, or a
   # direct dev checkout with no symlink at all (realpath is then a no-op).
   SKILL_DIR_REAL="$(realpath "$SKILL_DIR")"
   KIT_ROOT="${SKILL_DIR_REAL%/skills/*}"
   TOOLS_PY="$KIT_ROOT/tools/review-spec.py"
   CLI_PROFILES_DIR="$KIT_ROOT/references/review-spec/cli-profiles"
   ```
   If `TOOLS_PY` does not exist at that resolved path, treat this exactly
   like `--no-cross-ai` (skip straight to step 5's fallback) — cross-AI
   support isn't installed, never block the review over it.
1. Run `mktemp -d` via `Bash`, and record its printed absolute path as
   `RUN_TMP_DIR` in this skill's own working notes — **not** a shell
   environment variable. Every `Bash` tool call in this harness starts a
   fresh shell, so a variable set in one call is gone by the next one;
   from here on, substitute `RUN_TMP_DIR`'s literal absolute path into
   every command and every prose reference below, exactly the way
   `CODEBASE_ROOT` is already resolved once (Step 0.1) and substituted
   literally everywhere after. (This doc keeps writing `$RUN_TMP_DIR` for
   readability, matching how `<CODEBASE_ROOT>` reads elsewhere in this
   skill — read every `$RUN_TMP_DIR` below as "the literal path captured
   here", never as an actual shell variable reference.) Every artifact
   this run produces (raw reviewer reports, the double-review merge, the
   fixer's report) lives under this one directory, replacing the old flat
   `/tmp/review-spec-*` paths (which collided across concurrent runs on
   different projects/worktrees — fixed here).
2. If `--no-cross-ai`: skip straight to step 5 with an empty reviewer
   list request (`resolve-reviewers` degrades to the session-default
   fallback on its own when `--cross-ai` is omitted) — no detection, no
   quota probing, minimal overhead, exactly the "skip it entirely" case
   this flag exists for.
3. Otherwise, check whether `~/.cache/ai-kit/review-spec/runtimes.json`
   exists:
   - **Missing**: this is the first invocation ever to reach this step (no
     `review-spec-config` run yet, and no prior `/review-spec` run got
     this far either). Run
     ```bash
     python3 "$TOOLS_PY" detect-runtimes \
       --save ~/.cache/ai-kit/review-spec/runtimes.json
     ```
     — `--save` both prints the snapshot (unused here, informational only)
     *and* persists it via `cache_write_json` in the same call, so this
     branch never runs again after today: the next invocation finds the
     file present and skips straight to the "Present" case below. Print
     one line — "No cross-AI config saved yet — run `review-spec-config`
     so this doesn't repeat every invocation." — then continue to step 4;
     do NOT skip reviewer resolution (there's usually no
     `review-spec.toml` yet either, so `resolve-reviewers` in step 5
     degrades to `NO_CONFIG_FALLBACK` on its own — no special-casing
     needed here beyond persisting the detection snapshot and printing the
     hint).
   - **Present**: nothing to do here — `resolve-reviewers` (step 5) reads
     the real `review-spec.toml` config independently; `runtimes.json`'s
     only consumer is `review-spec-config` (Task 10), which reads it to
     avoid a redundant re-detection when the user runs that skill.
4. Refresh quota for anything the config's ladder might need:
   ```bash
   python3 "$TOOLS_PY" probe-quota --cwd <CODEBASE_ROOT> \
     --quota-path ~/.cache/ai-kit/review-spec/quota.json
   ```
   (No-op — writes `{}` — when there is no config/ladder to probe.)
5. Resolve the reviewer list, saving its output to a file (Step 1's
   external dispatch needs a stable path to feed `render-command`, not
   just the in-context text):
   ```bash
   python3 "$TOOLS_PY" resolve-reviewers \
     --cwd <CODEBASE_ROOT> \
     --quota ~/.cache/ai-kit/review-spec/quota.json \
     --source-vendor <SOURCE_VENDOR from Step 1's flag parsing> \
     --cross-ai \  # omit this flag entirely when --no-cross-ai was requested (step 2)
     > "$RUN_TMP_DIR/reviewers.json"
   ```
   `resolve-reviewers` itself calls `cfg_resolve(cwd, env)` (Task 2),
   which already handles the local-vs-global/`strategy` resolution — this
   step never re-implements that logic, it only picks which `--cwd` to
   pass (`CODEBASE_ROOT` from Step 0.1, so the resolved local config is
   the one that actually owns the document under review).
6. `$RUN_TMP_DIR/reviewers.json` holds a JSON array of 1 or 2 reviewer
   objects. Record its contents as `REVIEWER_LIST` (index 0 = primary/only
   reviewer, index 1 = the secondary in double mode) — Step 1 both reasons
   over this in-context and passes the same file's path to `render-command`
   for external dispatch.
```

- [ ] **Step 3: Rewrite Step 1 to branch on `REVIEWER_LIST`**

Replace the existing "Step 1 — Dispatch reviewer (every iteration)"
section's opening (the part before the reviewer prompt template) with:

```markdown
### Step 1 — Dispatch reviewer(s) (every iteration)

For each entry in `REVIEWER_LIST`:

- **`cli` is `null`** (native dispatch): use the `Agent` tool exactly as
  before —
  - `subagent_type`: `general-purpose`
  - `model`: the entry's `model`, **omitted entirely when `model == ""`**
    (the `NO_CONFIG_FALLBACK`/session-default case — never substitute a
    hardcoded name here; an empty `model` means "let the `Agent` tool use
    its own default"). A non-empty `model` value here **must be one of the
    four `Agent`-tool model aliases** (`sonnet`/`opus`/`haiku`/`fable` —
    Claude Code's `Agent` tool does not accept a full model id like
    `"opus-5"`); `review-spec-config` (Task 10) is responsible for writing
    exactly one of these four strings for every native reviewer entry, so
    surface anything else as a config error rather than passing it through.
  - `description`: `review-spec iter N reviewer (<key>)`
  - `prompt`: the template below, with the skill name updated to
    `review-spec-checklist` (was `reviewing-specs`)
  - After the `Agent` tool returns its report text, write it verbatim to
    `$RUN_TMP_DIR/iter<N>-<key>.md` via the `Write` tool (mirroring the
    external branch below, which redirects `Bash` stdout to the same
    path). Step 1.5's merge reads both reviewers' reports from files
    unconditionally — a native reviewer's report must land on disk exactly
    like an external one's, or `merge-reports` (Task 8) has no file to
    open for it and crashes the loop the first time `policy.mode =
    "double"` actually runs.

- **`cli` is set** (external CLI dispatch):
  1. Write the prompt text below to `$RUN_TMP_DIR/iter<N>-<key>-prompt.txt`
     via the `Write` tool, with `{prompt}` filled in as:

     ```
     Read the file at <ABSOLUTE PATH to skills/review-spec-checklist/SKILL.md>
     and follow it exactly, substituting:
     - ARCHETYPE = <ARCHETYPE>
     - FRAMEWORK_PROFILE_PATH = <FRAMEWORK_PROFILE_PATH>
     Read every file under review fresh from disk: <DOC_PATHS>
     Codebase root(s) for grounding: <CODEBASE_ROOT>
     Emit the report following that skill's Output template strictly, ending
     with the ### Status: line. Do not edit any file under review.
     ```

     (External CLIs can't call our `Skill` tool, but they can read a file
     path — this keeps `review-spec-checklist` the single source of truth
     for the checklist instead of duplicating its content into every
     CLI's prompt.)
  2. Fill the entry's `command` template via the `render-command`
     subcommand (Task 8), which calls `render_reviewer_command` (Task 6)
     internally — this is the ONLY way the orchestrator's `Bash`-tool
     dispatch reaches that function, since it's Python and the
     orchestrator dispatches via shell, not by importing the module:
     ```bash
     python3 "$TOOLS_PY" render-command \
       --reviewers-json "$RUN_TMP_DIR/reviewers.json" \
       --index <0 for the primary/single reviewer, 1 for the secondary> \
       --prompt-file "$RUN_TMP_DIR/iter<N>-<key>-prompt.txt"
     ```
     This prints the fully filled, shell-safe command string to stdout —
     `{prompt}` already shell-escaped, per Task 6's `render_reviewer_command`
     docstring. Never hand-splice the prompt into a command string
     yourself.
  3. Execute the printed command via the `Bash` tool with an explicit
     timeout (e.g. 300000ms / 5 minutes — generous for a real review call,
     distinct from the quota probe's 30s timeout since this is a full
     document review, not a trivial probe), redirecting stdout to
     `$RUN_TMP_DIR/iter<N>-<key>.md`.

Then continue with the existing reviewer prompt template (for the native
case) unchanged below, except the skill name substitution above.
```

- [ ] **Step 4: Add Step 1.5 after the new Step 1**

```markdown
### Step 1.5 — Merge reviewer reports (only when `REVIEWER_LIST` has 2 entries)

```bash
python3 "$TOOLS_PY" merge-reports --doc-paths "<DOC_PATHS>" \
  "<key1>=$RUN_TMP_DIR/iter<N>-<key1>.md" \
  "<key2>=$RUN_TMP_DIR/iter<N>-<key2>.md" \
  > "$RUN_TMP_DIR/iter<N>-merged.md"
```

Record `EFFECTIVE_REPORT_PATH`: `$RUN_TMP_DIR/iter<N>-merged.md` when
`REVIEWER_LIST` had 2 entries, else `$RUN_TMP_DIR/iter<N>-<key>.md` (the
single reviewer's own raw report) when it had 1. **Every later step reads
`EFFECTIVE_REPORT_PATH` and only that name** — there is exactly one
report artifact per iteration from Step 1.5 onward, never three or four
different invented filenames for the same underlying thing. The merged
report becomes the input to Step 2 (parse `### Status:`) exactly as a
single reviewer's report would — the merge already reproduces that line
(`Approved` when no findings survived the merge, `Issues Found — fix and
re-invoke` otherwise). When `REVIEWER_LIST` has only 1 entry, skip the
merge call — that entry's raw report (or the native `Agent` tool's output,
written to the same `iter<N>-<key>.md` path per Step 1) is
`EFFECTIVE_REPORT_PATH` directly, unchanged from today's behavior.
```

- [ ] **Step 5: Replace every remaining `/tmp/review-spec` reference with `$RUN_TMP_DIR`**

Find every occurrence — there are more than the two obvious ones (the
cross-AI dry run caught a missed one at the GSD-handoff Surface message):

```bash
grep -n "/tmp/review-spec" skills/review-spec/SKILL.md
```

Fix each — every one below points at the SAME `EFFECTIVE_REPORT_PATH`
(Step 1.5) rather than inventing its own new filename, closing a bug the
live re-review found (three different invented names —
`fixer-input.md`/`report.md`/the raw per-key name — for what should be one
path):
- Step 3's `Save the reviewer's report to a temp file
  (\`/tmp/review-spec-report-iter<N>.md\`)` → `The reviewer's report is
  already at \`EFFECTIVE_REPORT_PATH\` (Step 1.5) — no separate save
  needed here.`
- The Constants section's `**Loop state file (optional):**
  /tmp/review-spec-<doc-basename>-<timestamp>.log` → `**Loop state file
  (optional):** \`$RUN_TMP_DIR/loop.log\``.
- Step 5's "Native revise handed off" Surface row example (the GSD-handoff
  message: `... (findings: /tmp/review-spec-report-iter<N>.md), then
  re-run /review-spec.\``) → `... (findings: \`EFFECTIVE_REPORT_PATH\`),
  then re-run /review-spec.\`` — this is the same string wherever it
  recurs in the Surface table/examples.

Re-run the grep after fixing — expect zero matches.

- [ ] **Step 6: Rewrite the Cleanup section**

Replace:

```markdown
## Cleanup

After the loop ends (any outcome), delete the temp report file(s) from `/tmp/`. They are debugging artifacts, not deliverables.
```

with:

```markdown
## Cleanup

After the loop ends (any outcome): `rm -rf "$RUN_TMP_DIR"`. Every artifact
this run produced (reviewer reports, the double-review merge, fixer
reports, the loop log) lives under that one directory — a single command
replaces the old file-by-file `/tmp/review-spec-*` cleanup, and there's
nothing to accidentally miss.
```

- [ ] **Step 7: Update the Constants section's fixer/reviewer skill names**

Change `**Reviewer skill:** \`reviewing-specs\`` to `**Reviewer skill:**
\`review-spec-checklist\`` and `**Fixer skill:** \`applying-review-feedback\``
to `**Fixer skill:** \`review-spec-fixer\`` (if Task 1 hasn't already
caught these specific lines — re-grep to confirm).

- [ ] **Step 8: Manual dry run — verify `RUN_TMP_DIR` and merge wiring**

This task's own automated tests (Task 8) only exercise `tools/review-spec.py`
in isolation via fakes — they never invoke a real CLI. This step is the
only check on the orchestration prose itself, so it must actually run,
not be deferred on an external CLI's usage limit clearing:

1. Run `/review-spec` against a real spec/plan doc in this repo with
   `--no-cross-ai` first (fastest smoke test, and it is **always**
   runnable regardless of any external CLI's quota state — confirms
   `RUN_TMP_DIR` is created, Step 1 dispatches exactly as before via the
   renamed `review-spec-checklist`/`review-spec-fixer` skills, and cleanup
   removes the directory).
2. Run `python3 "$TOOLS_PY" probe-quota --cwd <this-repo> --quota-path
   <tmp path>` and inspect the result to find **whichever** configured CLI
   currently has quota (of `claude`/`codex`/`opencode`/`grok` — do not
   assume it's `codex` specifically; pick whichever the probe reports
   `available: true`, and if none currently do, run this sub-step again
   later rather than skipping it — it must eventually run once, not be
   waived).
3. With `policy.mode = "single"` pointing at that available CLI, run
   `/review-spec --cross-ai` and confirm the external `Bash` dispatch path
   (Step 1's `render-command` call, then executing the printed command)
   produces a parseable `### Status:` line in
   `$RUN_TMP_DIR/iter<N>-<key>.md`.
4. With `policy.mode = "double"`, run `/review-spec --cross-ai` again and
   confirm Step 1.5's merge produces a single well-formed report with
   `(Reviewers: ...)` tags, and that the native reviewer's report was
   also written to a file (the CRITICAL fix from the live re-review —
   confirm `merge-reports` did NOT fail with a missing-file error).

Report the outcome of all four dry runs — this is the closest this task
gets to an automated test, per the design spec's §11 note that
orchestration prose has no unit-test equivalent.

- [ ] **Step 9: Commit**

```bash
git add skills/review-spec/SKILL.md
git commit -m "feat(review-spec): wire cross-AI reviewer resolution, quota probing, external CLI dispatch, double-review merge, and RUN_TMP_DIR"
```

---

## Self-review notes (writing-plans Self-Review checklist, applied)

- **Spec coverage**: every numbered section of
  `2026-08-27-review-spec-cross-ai-design.md` maps to a task — §2 renaming
  → Task 1; §3 config → Tasks 2, 10; §5 CLI profiles → Task 9; §6 cache →
  Task 3; §7 `review-spec-config` → Task 10; §8 orchestrator integration →
  Task 11; §9 temp-file fix → Task 11 Step 2/6. §4 (source-vendor, renamed
  from "source-model" — see cross-AI review below) is folded into Task 11
  Steps 1/2 rather than its own task — it's a small orchestrator decision,
  not a standalone deliverable. Quota-awareness (spec §1's headline goal)
  is delivered by the new Task 6, absent from the first draft (caught by
  the cross-AI review below).
- **File-path correction from the spec**: the spec's illustrative paths
  said `scripts/review-spec/*.py` (several small files); this plan
  consolidates into one `tools/review-spec.py`, matching this repo's
  established single-flat-file-per-tool convention
  (`tools/status-line.py`, `tools/setup.py`) instead of introducing a new
  multi-file `scripts/` top-level directory. This is a plan-time
  refinement of an illustrative (not load-bearing) spec detail, not a
  contradiction of the spec's actual requirements.
- **Type consistency**: `ResolvedReviewer` (Task 5) is the one shape
  produced by `resolve_reviewers`/`resolve_ladder_pick` and consumed by
  Task 8's CLI entrypoint (`r._asdict()`) and Task 11's Step 3 — same
  field names (`key, model, vendor, cli, command, extra`) throughout.

### Cross-AI review of this plan (dogfooding, live)

Before finishing this plan, it was reviewed by `opencode run -m
opencode-go/kimi-k3` against both this document and its spec — a manual,
one-off rehearsal of the exact mechanism this plan builds (see the CLI
profile confirmed in Task 9's `opencode.md`). Kimi actually wrote the
assembled module + tests to a scratch directory and ran the 53-test suite
(all passed under Python 3.14) rather than just reading the prose, and
cross-checked every file/path claim against the real repo. It found one
CRITICAL and four HIGH issues, all fixed inline before this plan was
finalized:

| Severity | Finding | Fix |
|---|---|---|
| CRITICAL | `resolve-reviewers` called `cfg_load_toml` on a single `--config` path — the tested local/global `strategy` merge (Task 2) was never actually invoked at runtime | Task 8's `resolve-reviewers` now takes `--cwd` and calls `cfg_resolve(cwd, env)` directly; regression test added |
| HIGH | Nothing wrote `quota.json` — `_has_quota` always saw an empty dict, so "quota-aware" was unimplemented | New Task 6 (quota probing): `probe_reviewer_quota`, `refresh_quota_cache`, a `probe-quota` CLI subcommand, wired into Task 11's Step 0.7 before reviewer resolution |
| HIGH | Task 11 Step 1 hardcoded `model: sonnet` for the native reviewer — the exact "fixed model name" anti-pattern the spec's §1 opens by rejecting | Task 5 redesigned: no `CURRENT_SESSION` sentinel; a unified ladder walk makes the best-quota-having entry win (tier-aware by construction), falling back to `NO_CONFIG_FALLBACK` (no `model` override at all, not a hardcoded name) only when nothing has quota |
| HIGH | Task 1's grep verification (`grep -rn ... --include="*.md" .` expecting zero matches) is unsatisfiable — 17 files actually match, not just `review-spec/SKILL.md` | Task 1 Step 4 rewritten to enumerate all 17 into "must fix" (evals, README) vs. "must not touch" (historical plans/PRDs, this plan/spec) |
| HIGH | `--source-model=<id>` implied deriving a vendor from a model id with no sanctioned mapping | Renamed to `--source-vendor=<vendor>` throughout (Task 11 Step 1), removing the need for any id→vendor guess |

Also fixed at MEDIUM/LOW severity: `tests.test_review_spec` added to the
`Makefile` `test:` target (Task 8 Step 5); the fragile `python3 -c`
one-liner in `review-spec-config` replaced with a `detect-runtimes --save`
flag (Task 8/10); the second, previously-missed `/tmp/review-spec-report`
reference at the GSD-handoff Surface message (Task 11 Step 5); a dead
condition in `cfg_merge_reviewers` simplified (Task 2); `import time`
correctly flagged as a real addition rather than "already present" (Task
3). Kimi's dedup-key observation (spec §8 said "(file, line, category)",
Task 7 implements "(severity, exact Location string)") was resolved by
correcting the design spec's own wording — the checklist output format
has no separate file/line fields, only a free-text `Location:` string, so
the spec's original phrasing was aspirational rather than achievable as
written.

### Second review: clean-context Opus 5 subagent (native, live)

After the kimi round above, this plan (and the corrected spec) were
reviewed a second time by a fresh, clean-context general-purpose subagent
running Opus 5 natively (the `Agent` tool, no external CLI this time),
following the `reviewing-specs` skill's own methodology — the same
methodology `review-spec-checklist` will run under once Task 1's rename
lands. Unlike the kimi round, this reviewer read the actual current repo
state (via `Read`/`Grep`) rather than trusting the plan's prose, and it
caught several bugs the first round missed entirely, plus a real
first-round regression (the double-mode redesign from the kimi round
broke the design's own "guaranteed native baseline" guarantee, and nobody
propagated that fix back to the spec). It found 4 CRITICAL, 11 HIGH,
6 MEDIUM, and 5 cross-document-consistency findings — every one fixed
inline, listed by category:

| Severity | Finding | Fix |
|---|---|---|
| CRITICAL | `$RUN_TMP_DIR` was written as `RUN_TMP_DIR=$(mktemp -d)`, a shell variable — but every `Bash` tool call in this harness starts a fresh shell, so it was empty in every later reference (merge output, cleanup) | Step 0.7 point 1 now captures `mktemp -d`'s output as a literal absolute path substituted into every later reference, exactly like `CODEBASE_ROOT` already is |
| CRITICAL | Task 1 Step 4's file enumeration didn't match the real repo — verified live via `grep`, the true set is 17 files, and 3 were missing entirely (the moved skills' own self-references to each other's old names) | New Step 4 fixes those 3 self-references explicitly; Step 5's enumeration now matches the real 17-file grep output exactly, verified against this repo |
| CRITICAL | Double-review merge had no defined report file for a *native* reviewer — the `Agent` tool returns text, not a file, so `merge-reports` would crash on a missing path the first time `policy.mode = "double"` ran with a native primary (the common case) | Task 11 Step 3's native branch now writes the `Agent` tool's returned text to `$RUN_TMP_DIR/iter<N>-<key>.md` too, exactly like the external branch |
| CRITICAL | `tools/review-spec.py` and `references/review-spec/cli-profiles/` live at the repo root, which `tools/setup.py` never symlinks (only `agents`/`commands`/`skills`) — unreachable from an installed skill | New `KIT_ROOT`/`TOOLS_PY`/`CLI_PROFILES_DIR` resolution (Task 11 Step 2 point 0, and independently in Task 10): `realpath` the skill's own resolved `SKILL_DIR` and strip the trailing `/skills/<name>` to derive the repo root reliably across every install shape |
| HIGH | Merge could turn a failed/garbage external reviewer report into a false `### Status: Approved` (empty findings ≠ a clean pass) | New `report_has_status` (Task 7) checked by `merge-reports` (Task 8) before merging; on any missing/unreadable report it prints no `### Status:` line at all, reusing `review-spec/SKILL.md`'s existing "No Status line → Surface failure" rule instead of inventing a new one |
| HIGH | Dedup key `(severity, location)` collapsed two DIFFERENT findings from the same reviewer at the same location into one, silently dropping the second's content | `merge_findings` now tracks per-report `seen` locations and only collapses across DIFFERENT reports; a second same-report finding at the same location is disambiguated by title |
| HIGH | `parse_findings` had no notion of the `### Cross-Document Consistency` section — its bullets fell inside whichever severity heading preceded them | `_SEVERITY_RE` now recognizes that heading too, normalized to a `"CROSS-DOC"` tag; `render_merged_report` renders it under its own `### Cross-Document Consistency` heading, never a raw `### CROSS-DOC` |
| HIGH | `render_reviewer_command`'s `{prompt}` was spliced unescaped into a `shell=True` command string — a `"`/`$`/backtick in a document path could corrupt or inject into the command; the real dispatch had no timeout either | `{prompt}` is now `shlex.quote`d before substitution (model/extra fields stay bare, since CLI-specific quoting idioms like codex's `-c key='"{effort}"'` are template-authored); Task 11 Step 3 now specifies an explicit 5-minute `Bash`-tool timeout for real dispatch |
| HIGH | `render_reviewer_command` was declared "shared" with the real dispatch path but nothing in the orchestrator (which dispatches via `Bash`, not Python) could actually reach it | New `render-command` CLI subcommand (Task 8) — orchestrator writes the prompt to a file, calls `render-command`, executes the printed result |
| HIGH | A native reviewer's `model` example (`"opus-5"`) isn't a value the `Agent` tool accepts (only `sonnet`/`opus`/`haiku`/`fable`) | Design §3 and all plan fixtures switched to the 4 real aliases; `review-spec-config` (Task 10) explicitly instructed to ask for one of those 4, never a version string |
| HIGH | Step 0.7's "declined cross-AI, stub persisted" branch checked a file's existence and then read content from that same (missing) file — self-contradictory, and nothing ever wrote the stub | Redesigned: no separate "declined" concept. Missing `runtimes.json` → live-detect AND persist in the same `--save` call, so the hint fires exactly once; design §6 updated to match |
| HIGH | The "missing, never asked" branch's live detection output had no consumer — printed and discarded | Same fix as above: it's now persisted via `--save`, which is itself the consumer (next invocation reads it back) |
| HIGH | Config loading raised `KeyError` on a `[[reviewers]]` entry missing `key`/`model` — the only place in this module that didn't match `cfg_load_toml`'s documented "never raises" contract | `cfg_merge_reviewers` skips keyless entries; `_to_resolved` defaults a missing `model` to `""` (already a valid sentinel elsewhere in this module) |
| HIGH | `quota.json`'s shape (boolean `available` only) is thinner than design §6/§10 promised (context-window headroom), with no stated cost bound on repeated probing | Design §6/§10 corrected to the boolean-only shape actually built (headroom capture has no confirmed CLI mechanism yet); Task 6 states the cost bound explicitly (≤1 probe per ladder entry per `QUOTA_TTL_SECONDS`) |
| HIGH | Design §1 described three review modes; §3's schema only has two `policy.mode` values | §1 rewritten: two `policy.mode` values plus `--no-cross-ai` as the (non-config) third case, matching what the plan actually builds |
| HIGH | Design has no stated behavior for a dispatched CLI erroring, timing out, or producing a non-conforming report | New §10 edge case: single mode falls through the existing "No Status line" rule unchanged; double mode's merge step surfaces the same rule rather than fabricating a verdict from an incomplete pair |
| HIGH | Task 11 Step 8's only real (non-mocked) verification was gated on "once codex's usage limit clears" — a precondition the plan itself flagged as unmet, leaving the whole orchestrator change effectively untested | Step 8 rewritten: the `--no-cross-ai` leg is always runnable regardless of quota; the `--cross-ai` leg probes first and uses whichever CLI actually has quota, never assuming codex specifically |
| CROSS-DOC | Double-mode semantics contradicted outright: design promised a guaranteed native baseline, but the kimi-round Task 5 redesign picked the best entry "any vendor", which could seat an external reviewer as primary | Task 5's `resolve_reviewers` now walks a `_native_ladder`-filtered list for the primary slot only (still tier-aware within it), guaranteeing the baseline is always native or `NO_CONFIG_FALLBACK`; design §3 updated to match; 2 new regression tests added |
| CROSS-DOC | Design §3/§7/§11 still described a `scripts/review-spec/detect-runtimes.sh` shell script and its own unit tests — the plan builds none of that (one `tools/review-spec.py`) | Design §3 Scope, §7, and §11's testing section rewritten to the actual `tools/review-spec.py` shape |
| CROSS-DOC | Design's example `policy.ladder` ordering only made sense under the old (incorrect) double-mode semantics | Resolved as a side effect of the double-mode fix above — the example's only native entry (`claude-opus`) now correctly becomes the primary regardless of its position in the ladder, verified by trace and by the new regression tests |

MEDIUM findings (all fixed, no table): `cfg_render_toml`/`cfg_write_toml`
added to Task 2's Interfaces (they were implemented and tested but never
listed as produced); `parse_findings`'s docstring already matched its
`### ` regex correctly by this point (left as-is, verified);
`render_merged_report`'s docstring now states explicitly that it drops
each source report's own `Document Type`/`Files Read` lines by design; the
one remaining Spanish string (Step 0.7's hint message, and its design §6
mirror) translated to English to match the rest of the skill.
