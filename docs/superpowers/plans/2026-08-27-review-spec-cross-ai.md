# review-spec Cross-AI Reviewer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `review-spec`'s reviewer selection config-driven, quota-aware,
and optionally cross-vendor, instead of hardcoded to a single Claude
subagent.

**Architecture:** One new stdlib-only Python module,
`skills/review-spec/review-spec.py` — **placed inside the `review-spec`
skill's own directory, not a top-level `tools/`**, because that directory
is the one thing `tools/setup.py` actually installs (its `CATEGORIES`
symlink `agents`/`commands`/`skills` into `~/.claude`, never a top-level
`tools/`); a real orchestrator invocation must reach this module from an
installed skill, and the same three-candidate resolution pattern the
skill already uses for `SEEDS_DIR` (`CLAUDE_PLUGIN_ROOT`/`~/.claude/skills`/
sibling-of-this-file) is what makes that possible (see Task 11 Step 2
point 0). Despite the different location, it still mirrors
`tools/status-line.py`'s file layout and testing style — one flat file,
`importlib`-loaded by its test module since the filename is hyphenated,
and — matching `status-line.py`'s own precedent exactly, since this
module also runs under the user's bare system `python3` (per the
`Makefile`'s `test:` target and this repo's pre-commit config, which both
run tests on system `python3`, not the `.venv`) — `tomllib` is imported
inside a `try/except ModuleNotFoundError` guard, degrading to `tomllib =
None` on Python <3.11 exactly like `status-line.py`'s `cfg_load_toml`
does. Holds config load/write, cache read/write, CLI/model detection,
policy resolution, and cross-reviewer findings merge as pure,
independently unit-tested functions. Two skills are renamed
(`reviewing-specs` → `review-spec-checklist`, `applying-review-feedback` →
`review-spec-fixer`) and one is added (`review-spec-config`, an
interactive setup wizard). `review-spec/SKILL.md` gains a new Step 0.7 and
a Step 1.5, both driving `review-spec.py`'s CLI entrypoint via `Bash`, and
a `mktemp -d` fix for a pre-existing temp-file collision bug.

**Tech Stack:** bare system `python3` (unpinned version — the `Makefile`'s
`test:` target and `.pre-commit-config.yaml`'s `unittest` hook both run
it directly, not `.venv/bin/python3`; `.python-version` (3.12) governs
only the separate `uv`-managed dev venv, which is why `tomllib` is
imported behind a guard rather than assumed present), stdlib only
(`tomllib` for reading TOML — read-only, so this plan adds a small
hand-rolled TOML writer since there is no stdlib writer and this repo has
zero external dependencies; `json` for cache files), `unittest` (this repo's test runner, not pytest —
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
- Test runner for this repo: `python3 -m unittest tests.test_review_spec[.Class[.test]] -v` (NOT pytest).

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
  - Frontmatter `description:` (line 3): the single occurrence of
    `reviewing-specs` (`"a review report from \`reviewing-specs\`"`) →
    `review-spec-checklist`. **Leave the line's other backtick mention,
    `` `/review-spec` `` (the orchestrator example), untouched** — that's
    the public entrypoint skill, unaffected by this rename.
  - Line 8: `flagged by \`reviewing-specs\`.` → `flagged by
    \`review-spec-checklist\`.`
- `skills/review-spec-checklist/references/frameworks/SCHEMA.md` line 118:
  `(\`applying-review-feedback\`).` → `(\`review-spec-fixer\`).`

- [ ] **Step 5: Fix the two Python files that hardcode the old skill names — required before this task can even commit**

```bash
git grep -l "reviewing-specs\|applying-review-feedback" -- "*.py"
```

(`git grep`, not plain `grep -r` — scopes to tracked files only. A plain
recursive grep also matches stale copies under `.claude/worktrees/` and
other gitignored paths, which `grep -r` doesn't skip; `git grep` does.)

Verified live against this repo's actual current state, this matches
exactly:
- `tests/test_framework_profiles.py:13` — builds a path via
  `os.path.join(_HERE, "..", "skills", "reviewing-specs", "references",
  "frameworks")`. Change `"reviewing-specs"` to `"review-spec-checklist"`.
- `tests/test_wizard_pty.py:50` — `_KNOWN_SKILL = "applying-review-feedback"`.
  Change to `_KNOWN_SKILL = "review-spec-fixer"`. Also fix its docstring
  mention at line 358 ("the known skill \`\`applying-review-feedback\`\`
  was symlinked").

**This step cannot be skipped or deferred to Step 7**:
`tests.test_wizard_pty` is both in the `Makefile`'s `test:` target and in
`.pre-commit-config.yaml`'s `unittest-wizard` hook (`uv run python -m
unittest tests.test_wizard_app tests.test_wizard_pty`) — after Step 1's
`git mv`, that test's `_KNOWN_SKILL` constant points at a symlink name
that no longer exists, so the repo's own commit gate fails and Step 8's
commit cannot be made until this step runs.

- [ ] **Step 6: Verify no stale references remain in Markdown — and fix the ones that need it**

```bash
git grep -l "reviewing-specs\|applying-review-feedback" -- "*.md"
```

(Same `git grep` scoping as Step 5, for the same reason.) Run this
**after** Steps 1–5. Verified live against this repo's actual
current state (pre-rename), the full match set — Markdown and Python
combined — is these **19 files** (17 `.md`, handled by this step, plus
the 2 `.py` files Step 5 already fixed):

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

By the time you run this step's grep (after Steps 1–4), the paths have
already moved and 4 of these 17 are already fixed —
`skills/review-spec/SKILL.md` by Step 3, and the 3 self-references by
Step 4 (`review-spec-checklist/SKILL.md`, `review-spec-fixer/SKILL.md`,
`review-spec-checklist/references/frameworks/SCHEMA.md`) — so what you'll
actually see is **13** post-move `.md` paths, split into two groups:

1. **MUST fix (8 files)** — living documentation and active test
   fixtures, not history:
   - `README.md` lines 28, 29, 34 (three separate mentions — `reviewing-specs`→`review-spec-checklist`, `applying-review-feedback`→`review-spec-fixer`, including the one inside the `review-spec` row's description).
   - `skills/review-spec/evals/01-superpowers-plan-routes-writing-plans.md`, `02-gsd-plan-routes-native-cmd.md`, `03-generic-doc-direct-edit.md`, `04-ambiguous-detection-fallback.md`
   - `skills/review-spec-checklist/evals/orchestrator-integration.md`, `skills/review-spec-checklist/evals/test-scenarios.md`
   - `skills/review-spec-fixer/evals/test-scenarios.md` — also fix its
     relative fixture path `../../reviewing-specs/evals/fixtures/` →
     `../../review-spec-checklist/evals/fixtures/` (it points at the
     reviewer skill's shared fixtures directory).

   Replace every `reviewing-specs`/`applying-review-feedback` mention in
   these 8 files with the new names, same substitution as Step 3.

2. **MUST NOT touch (5 files)**: `docs/prds/000-ai-kit-overhaul-requirements.md`,
   `docs/superpowers/plans/2026-06-14-e1-review-spec-skill.md`,
   `docs/superpowers/plans/2026-06-24-wizard-redesign-B-ui.md`, and this
   plan + its spec (`docs/superpowers/plans/2026-08-27-review-spec-cross-ai.md`,
   `docs/superpowers/specs/2026-08-27-review-spec-cross-ai-design.md`) —
   these are immutable historical record or documents *about* the rename
   itself; leave their old-name mentions exactly as written.

Re-run the grep after fixing group 1 — it should now match exactly the
5 group-2 paths, not zero.

- [ ] **Step 7: Verify the moved skills' own internal `references/` paths still resolve**

```bash
ls skills/review-spec-checklist/references/frameworks/SCHEMA.md
```

Expected: file exists (the move preserved the directory's internal
structure — only the top-level directory name changed).

- [ ] **Step 8: Note for the user — local symlink refresh**

Add a one-line note to the commit message (Step 9) that
`~/.claude/skills/reviewing-specs` and `~/.claude/skills/applying-review-feedback`
are stale symlinks now — `tools/setup.py`'s existing housekeeping/prune
logic (it already detects "ai-kit symlinks whose repo entry no longer
exists" — see `tools/setup.py`'s symlink-diff functions) removes them and
creates `review-spec-checklist`/`review-spec-fixer` symlinks on the next
`tools/setup.py` run. No new symlink code needed in this plan.

- [ ] **Step 9: Commit**

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
- Create: `skills/review-spec/review-spec.py`
- Test: `tests/test_review_spec.py`

**Interfaces:**
- Produces: `cfg_local_path(cwd: str) -> str`, `cfg_global_path(env: dict) -> str`,
  `cfg_load_toml(path: str) -> dict`, `cfg_merge_reviewers(global_list: list[dict], local_list: list[dict]) -> list[dict]`,
  `cfg_resolve(cwd: str, env: dict) -> dict` (returns `{"policy": {...}, "reviewers": [...]}`),
  `cfg_render_toml(config: dict) -> str`, `cfg_write_toml(path: str, config: dict) -> None`.
  Consumed by Task 5 (policy resolution), Task 8 (`render-toml` subcommand
  calls `cfg_render_toml` directly and, when its `--out` flag is given,
  `cfg_write_toml` too — see Task 8), and Task 10 (`review-spec-config`
  shells out to the `render-toml --out <path>` subcommand rather than
  importing this module — see Task 8's Interfaces note on why).

- [ ] **Step 1: Write the failing tests**

Create `tests/test_review_spec.py`:

```python
import importlib.util
import os
import tempfile
import unittest

_MODULE_PATH = os.path.join(os.path.dirname(__file__), "..", "skills", "review-spec", "review-spec.py")


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
    @unittest.skipIf(rs.tomllib is None, "tomllib not available on this interpreter")
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

    @unittest.skipIf(rs.tomllib is None, "tomllib not available on this interpreter")
    def test_escapes_quotes_and_backslashes_in_strings(self):
        rendered = rs.cfg_render_toml({"policy": {}, "reviewers": [
            {"key": "a", "command": 'echo "hi" \\ done'}]})
        import tomllib
        parsed = tomllib.loads(rendered)
        self.assertEqual(parsed["reviewers"][0]["command"], 'echo "hi" \\ done')

    @unittest.skipIf(rs.tomllib is None, "tomllib not available on this interpreter")
    def test_renders_top_level_strategy_when_present(self):
        rendered = rs.cfg_render_toml({"strategy": "local-only", "policy": {"mode": "single"},
                                        "reviewers": []})
        import tomllib
        parsed = tomllib.loads(rendered)
        self.assertEqual(parsed["strategy"], "local-only")

    @unittest.skipIf(rs.tomllib is None, "tomllib not available on this interpreter")
    def test_omits_strategy_line_when_absent(self):
        rendered = rs.cfg_render_toml({"policy": {"mode": "single"}, "reviewers": []})
        import tomllib
        parsed = tomllib.loads(rendered)
        self.assertNotIn("strategy", parsed)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m unittest tests.test_review_spec -v`

Expected: FAIL — `skills/review-spec/review-spec.py` does not exist yet
(`FileNotFoundError` from `spec_from_file_location`/`exec_module`, or an
`AttributeError` once the empty file exists).

- [ ] **Step 3: Implement**

Create `skills/review-spec/review-spec.py`:

```python
#!/usr/bin/env python3
"""review-spec cross-AI reviewer support: config (TOML), cache (JSON),
runtime/CLI detection, policy resolution, and cross-reviewer findings
merge. Stdlib-only, no external dependencies (see pyproject.toml)."""

import os

try:
    import tomllib as _tomllib_impl
    tomllib = _tomllib_impl
except ModuleNotFoundError:        # Python < 3.11 — degrade to env-only config.
    tomllib = None  # type: ignore[assignment]  # stdlib boundary: optional module absent on <3.11


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
    """Parse the TOML at path. Missing/malformed/no-tomllib -> {}. Never
    raises (mirrors tools/status-line.py's cfg_load_toml exactly, since
    this module runs under the same bare system python3, not the .venv)."""
    if tomllib is None:
        return {}
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
    """Hand-rolled TOML serializer for this schema only (an optional
    top-level `strategy` string, a flat [policy] table, and an
    array-of-tables [[reviewers]] with flat string/bool/list values) —
    tomllib is read-only in stdlib, and adding a writer dependency would
    break this repo's zero-dependency runtime."""
    lines = []
    if "strategy" in config:
        lines.append(f"strategy = {_toml_value(config['strategy'])}")
        lines.append("")
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

Run: `python3 -m unittest tests.test_review_spec -v`

Expected: PASS for every `TestConfigPaths`, `TestLoadToml`,
`TestMergeReviewers`, `TestResolveConfig`, `TestRenderAndWriteToml` test.

- [ ] **Step 5: Commit**

```bash
git add skills/review-spec/review-spec.py tests/test_review_spec.py
git commit -m "feat(review-spec): add TOML config load/write with local/global strategy merge"
```

---

### Task 3: Cache module — JSON read/write + TTL staleness

**Files:**
- Modify: `skills/review-spec/review-spec.py`
- Test: `tests/test_review_spec.py`

**Interfaces:**
- Consumes: nothing from Task 2.
- Produces: `cache_base(env: dict) -> str`, `cache_runtimes_path(env: dict) -> str`,
  `cache_quota_path(env: dict) -> str`, `cache_read_json(path: str) -> dict | None`,
  `cache_write_json(path: str, data: dict) -> None`, `cache_is_stale(path: str, ttl_seconds: int) -> bool`,
  `RUNTIMES_TTL_SECONDS: int`, `QUOTA_TTL_SECONDS: int`.
  `cache_read_json`/`cache_write_json` are consumed directly by Task 8's
  `main()` on caller-supplied paths. `cache_base`/`cache_runtimes_path`/
  `cache_quota_path`/`cache_is_stale`/`RUNTIMES_TTL_SECONDS` are consumed
  by Task 8's new `cache-path` subcommand and `detect-runtimes --if-stale`
  flag (see Task 8) — this is how callers outside Python (the orchestrator
  in Task 11, `review-spec-config` in Task 10) resolve the
  `${XDG_CACHE_HOME:-$HOME/.cache}`-aware cache paths and check runtimes
  staleness without duplicating the formula in bash. Task 4/Task 5 do not
  read the cache themselves — persistence is entirely the CLI entrypoint's
  job (Task 8).

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
`importlib.util`, `os`, `tempfile`, `unittest`), in alphabetically sorted
position: `importlib.util`, `os`, `tempfile`, `time`, `unittest` — this
file is ruff-scoped (`.pre-commit-config.yaml`'s hook covers `tests/`) and
ruff's `I001` fails an out-of-order import block, not just an unused one.

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m unittest tests.test_review_spec.TestCachePaths tests.test_review_spec.TestCacheReadWrite tests.test_review_spec.TestCacheStaleness -v`

Expected: FAIL — `AttributeError: module 'review_spec' has no attribute 'cache_base'` (and similarly for the other new names).

- [ ] **Step 3: Implement**

Add `import json`, `import time`, and `from typing import Optional` to
`skills/review-spec/review-spec.py`'s import block at the top (below
`import os`, above the `try: import tomllib` block) — Task 2 only needed
`os`/`tomllib`, this task is the first to need JSON, mtimes, and
`cache_read_json`'s `Optional[dict]` return type. `.pre-commit-config.yaml`'s
ruff hook only scopes `^(tools|tests)/.*\.py$`, so this file itself
(`skills/review-spec/review-spec.py`) is never ruff-linted at all —
introducing imports incrementally here is simply good hygiene, not a
lint-gate requirement. `tests/test_review_spec.py` **is** ruff-scoped,
though (it's under `tests/`), which is why the same incremental
discipline is load-bearing for that file specifically (see Task 8 Step 1
for the concrete case this avoids).

Append to `skills/review-spec/review-spec.py`:

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

Run: `python3 -m unittest tests.test_review_spec -v`

Expected: PASS, all tests including Task 2's.

- [ ] **Step 5: Commit**

```bash
git add skills/review-spec/review-spec.py tests/test_review_spec.py
git commit -m "feat(review-spec): add JSON cache read/write with TTL staleness check"
```

---

### Task 4: Runtime/CLI detection

**Files:**
- Modify: `skills/review-spec/review-spec.py`
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

Run: `python3 -m unittest tests.test_review_spec.TestDetectInstalledClis tests.test_review_spec.TestDetectOpencodeModels tests.test_review_spec.TestBuildRuntimesSnapshot -v`

Expected: FAIL — `AttributeError: module 'review_spec' has no attribute 'KNOWN_CLIS'` (and similarly for the functions).

- [ ] **Step 3: Implement**

Add `import shutil` and `import subprocess` to the top import block.

Append to `skills/review-spec/review-spec.py`:

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

Run: `python3 -m unittest tests.test_review_spec -v`

Expected: PASS, all tests including Tasks 2–3's.

- [ ] **Step 5: Commit**

```bash
git add skills/review-spec/review-spec.py tests/test_review_spec.py
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
- Modify: `skills/review-spec/review-spec.py`
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

    def test_double_mode_primary_is_best_native_entry_tier_aware(self):
        config = dict(self.config)
        config["policy"] = {"mode": "double", "ladder": self.config["policy"]["ladder"]}
        result = rs.resolve_reviewers(config, quota={}, source_vendor="anthropic", cross_ai=True)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].key, "claude-opus")   # best NATIVE entry (guaranteed baseline), tier-aware
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

    def test_double_mode_secondary_is_dropped_not_substituted_with_same_vendor(self):
        # regression: the design's guarantee for the secondary slot is
        # "cross-vendor alternate, DROPPED if none survives" — an earlier
        # draft's resolve_ladder_pick fell back to a same-vendor pick
        # instead (its generic same-vendor-fallback pass), so a ladder
        # with a same-vendor EXTERNAL entry (e.g. an "anthropic"-vendor
        # CLI profile) would incorrectly seat it as the secondary,
        # running two same-vendor reviewers under "double review".
        config = {
            "policy": {"mode": "double", "ladder": ["claude-opus", "claude-cli-opus"]},
            "reviewers": [
                {"key": "claude-opus", "model": "opus", "vendor": "anthropic"},
                {"key": "claude-cli-opus", "model": "opus", "vendor": "anthropic",
                 "cli": "claude", "command": "claude -p --model {model} {prompt}"},
            ],
        }
        result = rs.resolve_reviewers(config, quota={}, source_vendor="openai", cross_ai=True)
        self.assertEqual(len(result), 1)  # secondary dropped, not substituted
        self.assertEqual(result[0].key, "claude-opus")

    def test_double_mode_secondary_dropped_when_no_native_entry_and_only_source_vendor_available(self):
        # regression: when NO native entry is configured at all, primary
        # is NO_CONFIG_FALLBACK (vendor == "") -- an empty skip_vendor
        # disables resolve_ladder_pick's vendor filter entirely, so the
        # secondary walk must fall back to filtering against source_vendor
        # instead, or a same-source-vendor external entry (e.g. another
        # "anthropic"-vendor CLI) would wrongly fill the "cross-vendor"
        # slot opposite a native anthropic baseline.
        config = {
            "policy": {"mode": "double", "ladder": ["claude-cli-opus"]},
            "reviewers": [
                {"key": "claude-cli-opus", "model": "opus", "vendor": "anthropic",
                 "cli": "claude", "command": "claude -p --model {model} {prompt}"},
            ],
        }
        result = rs.resolve_reviewers(config, quota={}, source_vendor="anthropic", cross_ai=True)
        self.assertEqual(len(result), 1)  # secondary dropped, not substituted
        self.assertEqual(result[0], rs.NO_CONFIG_FALLBACK)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m unittest tests.test_review_spec.TestResolveLadderPick tests.test_review_spec.TestResolveReviewers -v`

Expected: FAIL — `AttributeError: module 'review_spec' has no attribute 'resolve_ladder_pick'`.

- [ ] **Step 3: Implement**

Add `from typing import NamedTuple` to the top import block (`Optional`
was already added in Task 3, for `cache_read_json`'s return type).

Append to `skills/review-spec/review-spec.py`:

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


def resolve_ladder_pick(reviewers: list, ladder: list, skip_vendor: str, quota: dict,
                         allow_same_vendor_fallback: bool = True) -> Optional[ResolvedReviewer]:
    """First ladder entry that (a) exists in `reviewers`, (b) has a
    different vendor than skip_vendor (empty skip_vendor disables this
    filter — used for "best overall, any vendor"), and (c) has quota. If
    nothing survives both filters and `allow_same_vendor_fallback` is True
    (the default), retry ignoring the vendor filter (same-vendor coverage
    beats no reviewer at all) — this is `single` mode's behavior, and
    `double` mode's PRIMARY slot (whose `skip_vendor` is always `""`
    anyway, so the fallback never actually triggers there). None only if
    every candidate lacks quota or doesn't exist.

    Pass `allow_same_vendor_fallback=False` for `double` mode's SECONDARY
    slot specifically: the design's guarantee for that slot is "a
    cross-vendor alternate, dropped (not substituted) if none survives" —
    silently degrading to a same-vendor pick there would run two
    same-vendor reviewers under a "double review" banner while billing a
    second CLI call for zero independent perspective.

    This is where tier-awareness comes from: a caller passing an ordered
    ladder like ["claude-opus", "claude-sonnet", ...] gets the flagship
    tier whenever it has quota, and falls through to the next configured
    tier automatically otherwise — no separate "tier" concept needed."""
    for key in ladder:
        entry = _reviewer_by_key(reviewers, key)
        if entry is None or (skip_vendor and entry.get("vendor") == skip_vendor) or not _has_quota(quota, key):
            continue
        return _to_resolved(entry)
    if not allow_same_vendor_fallback:
        return None
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
    from primary's — or, when primary is NO_CONFIG_FALLBACK (whose vendor
    is unknown, `""`), different from `source_vendor` instead, since an
    unknown-vendor filter is no filter at all and would defeat the
    cross-vendor guarantee exactly when there's no configured native
    entry to compare against — dropped (not substituted) if none
    survives (a native-only, or all-same-vendor, ladder degrades to a
    single reviewer, not an error).

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
        secondary_skip_vendor = primary.vendor or source_vendor
        secondary = resolve_ladder_pick(reviewers, ladder, skip_vendor=secondary_skip_vendor, quota=quota,
                                         allow_same_vendor_fallback=False)
        if secondary is None or secondary.key == primary.key:
            return [primary]
        return [primary, secondary]
    pick = resolve_ladder_pick(reviewers, ladder, skip_vendor=source_vendor, quota=quota)
    return [pick] if pick else [NO_CONFIG_FALLBACK]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m unittest tests.test_review_spec -v`

Expected: PASS, all tests including Tasks 2–4's.

- [ ] **Step 5: Commit**

```bash
git add skills/review-spec/review-spec.py tests/test_review_spec.py
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
low-effort/fast-tier call — see `skills/review-spec/references/cli-profiles/codex.md`)
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
- Modify: `skills/review-spec/review-spec.py`
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

Add `import subprocess` to the test file's import block — this task's
`test_timeout_is_unavailable` (below) constructs a
`subprocess.TimeoutExpired`, and nothing earlier in the test file imports
`subprocess` (the module itself gains it in Task 4, but the *test file*
tracks its own imports task-by-task since it's ruff-scoped). Insert it in
alphabetically sorted position: `importlib.util`, `os`, `subprocess`,
`tempfile`, `time`, `unittest` — ruff's `I001` fails an out-of-order
import block.

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

    def test_missing_command_raises_value_error_not_attribute_error(self):
        # a cli-set entry with no command is a malformed config (schema:
        # command is "required iff cli present") — must be a reportable
        # ValueError, never a raw AttributeError from `None.format(...)`
        resolved = rs.ResolvedReviewer(key="codex-gpt", model="gpt-5.2", vendor="openai",
                                        cli="codex", command=None, extra={})
        with self.assertRaises(ValueError):
            rs.render_reviewer_command(resolved, "hello")

    def test_malformed_template_raises_value_error_not_key_error(self):
        # {unknown_field} isn't {model}/{prompt}/in extra -> str.format
        # raises KeyError; must surface as a reportable ValueError instead
        resolved = rs.ResolvedReviewer(key="codex-gpt", model="gpt-5.2", vendor="openai",
                                        cli="codex", command="codex -m {model} {unknown_field} {prompt}",
                                        extra={})
        with self.assertRaises(ValueError):
            rs.render_reviewer_command(resolved, "hello")

    def test_extra_field_colliding_with_reserved_placeholder_raises_value_error(self):
        # a hand-written config entry that defines extra={"prompt": ...} or
        # extra={"model": ...} collides with the reserved keyword args
        # passed to str.format, raising a TypeError that must not escape
        # as a raw crash either
        resolved = rs.ResolvedReviewer(key="codex-gpt", model="gpt-5.2", vendor="openai",
                                        cli="codex", command="codex -m {model} {prompt}",
                                        extra={"prompt": "oops"})
        with self.assertRaises(ValueError):
            rs.render_reviewer_command(resolved, "hello")


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

    def test_cli_entry_with_missing_command_is_unavailable_not_true(self):
        # regression: a cli-set entry with no command template can never
        # actually be dispatched — must classify as unavailable, not
        # silently `available: True` (which would let it win a ladder
        # walk and only fail later, in real dispatch)
        resolved = rs.ResolvedReviewer(key="codex-gpt", model="gpt-5.2", vendor="openai",
                                        cli="codex", command=None, extra={})
        result = rs.probe_reviewer_quota(resolved, run_fn=lambda *a, **k: (_ for _ in ()).throw(
            AssertionError("should never shell out for a malformed command")))
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

Run: `python3 -m unittest tests.test_review_spec.TestRenderReviewerCommand tests.test_review_spec.TestProbeReviewerQuota tests.test_review_spec.TestRefreshQuotaCache -v`

Expected: FAIL — `AttributeError: module 'review_spec' has no attribute 'render_reviewer_command'`.

- [ ] **Step 3: Implement**

Add `import shlex` to the top import block.

Append to `skills/review-spec/review-spec.py`:

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
    `'{prompt}'` — the quoting is already applied here).

    Raises `ValueError` — never a raw `KeyError`/`AttributeError`/
    `IndexError`/`TypeError` — when `resolved.command` is missing (a
    `cli`-set entry with no `command` is a malformed config, per the
    schema's "required iff `cli` present"), the template references a
    placeholder that isn't `{model}`/`{prompt}`/one of `extra`'s keys,
    contains a literal unescaped brace, or `extra` itself defines a
    `model`/`prompt` key (a hand-written config collision with the two
    reserved placeholder names — `str.format`'s duplicate-keyword-argument
    `TypeError` in that case is exactly as much a malformed-config problem
    as a bad placeholder, and gets the same treatment). A malformed
    `review-spec.toml` entry must surface as a reportable config error,
    never crash the caller."""
    if not resolved.command:
        raise ValueError(f"reviewer {resolved.key!r} has cli={resolved.cli!r} set but no command template")
    try:
        return resolved.command.format(model=resolved.model, prompt=shlex.quote(prompt),
                                        **resolved.extra)
    except (KeyError, IndexError, ValueError, TypeError) as exc:
        raise ValueError(f"reviewer {resolved.key!r} has a malformed command template: {exc}") from exc


def probe_reviewer_quota(resolved: "ResolvedReviewer", run_fn=subprocess.run) -> dict:
    """Native (cli-less) entries are never probed — there is nothing to
    shell out to, and dispatch mechanics there are the current session's
    own concern, not a quota this module can observe. For CLI entries: run
    a trivial prompt through the reviewer's own command and classify
    availability generically — a nonzero exit code, or stdout/stderr
    containing a case-insensitive usage/quota/rate-limit phrase, means
    unavailable; anything else (including plain success) means available.
    This generic heuristic is what makes the confirmed codex usage-limit
    error (see skills/review-spec/references/cli-profiles/codex.md) detectable
    without a CLI-specific parser. A `cli`-set entry with a missing or
    malformed `command` template is deliberately classified `available:
    False` here rather than skipped/True — it can never actually be
    dispatched, so reporting it as available would let a broken config
    entry win the ladder walk and fail later, in real dispatch, instead
    of here where the failure is cheap and diagnosable."""
    if not resolved.cli:
        return {"available": True, "checked_at": time.time()}
    try:
        filled = render_reviewer_command(resolved, "Only say: Hello world!")
    except ValueError:
        return {"available": False, "checked_at": time.time()}
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

Run: `python3 -m unittest tests.test_review_spec -v`

Expected: PASS, all tests including Task 5's.

- [ ] **Step 5: Commit**

```bash
git add skills/review-spec/review-spec.py tests/test_review_spec.py
git commit -m "feat(review-spec): add quota probing (render_reviewer_command, probe_reviewer_quota, refresh_quota_cache)"
```

---

### Task 7: Findings merge (Step 1.5 — double-review reconciliation)

**Files:**
- Modify: `skills/review-spec/review-spec.py`
- Test: `tests/test_review_spec.py`

**Interfaces:**
- Consumes: nothing from Tasks 2–6 (pure text-in/text-out, deliberately
  decoupled so it's testable with plain fixture strings).
- Produces: `parse_findings(report_text: str) -> list[dict]`,
  `report_has_status(report_text: str) -> bool`,
  `report_declares_issues(report_text: str) -> bool`,
  `merge_findings(reports: list[tuple[str, str]]) -> list[dict]`,
  `render_merged_report(findings: list[dict], doc_paths: str, any_source_issues: bool = False) -> str`.
  Consumed by Task 8 (`merge-reports` uses `report_has_status` to detect a
  failed/non-conforming reviewer *before* merging, and `report_declares_issues`
  on every source report to compute `any_source_issues` — see that task's
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

    def test_low_severity_bullets_keep_their_own_tag_not_medium(self):
        # regression: a plan-archetype review may legitimately emit a
        # ### LOW heading (reviewing-specs's LOW/Tooling-Catchable tier);
        # before this fix its bullets fell through to severity None and
        # render_merged_report silently re-labeled them MEDIUM.
        report = """## Review: plan.md
### LOW
- **Trailing whitespace** — Location: §4. Required: trim it. Why: lint noise.
### Status: Issues Found — fix and re-invoke
"""
        findings = rs.parse_findings(report)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["severity"], "LOW")


class TestReportHasStatus(unittest.TestCase):
    def test_true_when_status_line_present(self):
        self.assertTrue(rs.report_has_status(_REPORT_A))

    def test_false_for_garbage_text(self):
        self.assertFalse(rs.report_has_status("some random CLI error output, no status here"))

    def test_false_for_empty_text(self):
        self.assertFalse(rs.report_has_status(""))


class TestReportDeclaresIssues(unittest.TestCase):
    def test_true_for_issues_found_status(self):
        self.assertTrue(rs.report_declares_issues(_REPORT_A))

    def test_false_for_approved_status(self):
        approved = "## Review: spec.md\n### Status: Approved\n"
        self.assertFalse(rs.report_declares_issues(approved))

    def test_false_for_garbage_text(self):
        self.assertFalse(rs.report_declares_issues("no status line at all"))


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

    def test_low_findings_render_under_their_own_heading_not_medium(self):
        findings = [{"severity": "LOW", "title": "Trailing whitespace", "location": "§4",
                     "required": "trim it", "why": "lint noise", "reviewers": ["claude-opus"]}]
        rendered = rs.render_merged_report(findings, "plan.md")
        self.assertIn("### LOW", rendered)
        self.assertNotIn("### MEDIUM", rendered)

    def test_any_source_issues_prevents_false_approved_when_no_findings_parsed(self):
        # regression: a source report can say "Issues Found" while its
        # bullet(s) fail _BULLET_RE's strict single-line shape (e.g. a
        # wrapped Required: clause) — parse_findings then returns nothing
        # for it, but the merge must never report Approved in that case.
        rendered = rs.render_merged_report([], "spec.md", any_source_issues=True)
        self.assertIn("### Status: Issues Found — fix and re-invoke", rendered)
        self.assertNotIn("### Status: Approved", rendered)

    def test_any_source_issues_false_still_renders_approved_when_no_findings(self):
        rendered = rs.render_merged_report([], "spec.md", any_source_issues=False)
        self.assertIn("### Status: Approved", rendered)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m unittest tests.test_review_spec.TestParseFindings tests.test_review_spec.TestMergeFindings tests.test_review_spec.TestRenderMergedReport -v`

Expected: FAIL — `AttributeError: module 'review_spec' has no attribute 'parse_findings'`.

- [ ] **Step 3: Implement**

Add `import re` to the top import block.

Append to `skills/review-spec/review-spec.py`:

```python
# ── Findings merge (Step 1.5 double-review reconciliation) ──────────────

_SEVERITY_HEADINGS = {
    "CRITICAL": "CRITICAL", "HIGH": "HIGH", "MEDIUM": "MEDIUM", "LOW": "LOW",
    "Cross-Document Consistency": "CROSS-DOC",
}
_SEVERITY_RE = re.compile(
    r"^### (CRITICAL|HIGH|MEDIUM|LOW|Cross-Document Consistency)\s*$", re.MULTILINE)
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


def report_declares_issues(report_text: str) -> bool:
    """True iff report_text's own Status line says Issues Found. A plain
    substring check, deliberately independent of `_BULLET_RE`'s strict
    per-bullet shape — `parse_findings` can miss a bullet that wraps across
    lines or uses slightly different punctuation, but the report's own
    Status line is a single fixed string every conforming report ends
    with. Used as a second, structurally-independent signal alongside
    parsed findings so a report that says "Issues Found" can never merge
    into a false "Approved" just because none of its bullets happened to
    match the strict bullet regex."""
    return "### Status: Issues Found" in report_text


def parse_findings(report_text: str) -> list:
    """[{severity, title, location, required, why}] in document order, per
    the review-spec-checklist output template (`### SEVERITY` headings —
    `CRITICAL`/`HIGH`/`MEDIUM`/`LOW`, plus `### Cross-Document Consistency`
    normalized to the `"CROSS-DOC"` severity tag — followed by
    `- **title** — Location: .... Required: .... Why: ....` bullets).
    `LOW` is recognized because a plan-archetype review may legitimately
    emit it (reviewing-specs's Plan checklist defines a LOW/Tooling-
    Catchable tier); without recognizing it, its bullets would fall
    through to severity None and get silently re-labeled MEDIUM by
    `render_merged_report`, escalating severity that was never intended.
    A bullet appearing before any recognized heading (malformed input)
    still gets severity None."""
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


def render_merged_report(findings: list, doc_paths: str, any_source_issues: bool = False) -> str:
    """Renders CRITICAL/HIGH/MEDIUM/LOW under their own headings and
    CROSS-DOC findings under the same `### Cross-Document Consistency`
    heading the source reports use (never a raw `### CROSS-DOC`, which
    isn't part of the output template). A finding whose severity didn't
    match any recognized heading (malformed input — e.g. a bullet before
    any `### SEVERITY` heading) falls back to MEDIUM, tagged exactly as
    parsed — this can only happen on non-conforming input, since
    report_has_status (Task 8) already filters those out before this
    function ever runs. Deliberately drops each source report's own
    `### Document Type`/`### Files Read` lines — those describe a single
    reviewer's run, not a property of the merge — in favor of a fixed
    `cross-ai merged` marker.

    `any_source_issues` (from `report_declares_issues` on each raw source
    report, computed by the caller) is OR'd into the parsed-findings-based
    status: a report can legitimately say "Issues Found" while containing
    a bullet `_BULLET_RE` fails to parse (wrapped line, off-template
    punctuation), and without this the merge would silently downgrade that
    to "Approved" purely because no *parsed* finding survived."""
    by_sev = {"CRITICAL": [], "HIGH": [], "MEDIUM": [], "LOW": [], "CROSS-DOC": []}
    for f in findings:
        sev = f["severity"] if f["severity"] in by_sev else "MEDIUM"
        by_sev[sev].append(f)
    lines = [f"## Review: {doc_paths}", "### Document Type", "cross-ai merged"]
    any_issues = any(by_sev.values()) or any_source_issues
    heading_for = {"CRITICAL": "### CRITICAL", "HIGH": "### HIGH", "MEDIUM": "### MEDIUM",
                   "LOW": "### LOW", "CROSS-DOC": "### Cross-Document Consistency"}
    for sev in ("CRITICAL", "HIGH", "MEDIUM", "LOW", "CROSS-DOC"):
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

Run: `python3 -m unittest tests.test_review_spec -v`

Expected: PASS, all tests including Tasks 2–5's.

- [ ] **Step 5: Commit**

```bash
git add skills/review-spec/review-spec.py tests/test_review_spec.py
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
- Modify: `skills/review-spec/review-spec.py`
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
  `Bash` calls), both of which shell out to `python3 skills/review-spec/review-spec.py
  <subcommand> ...` rather than importing the module directly (they run
  from Claude Code's `Bash` tool, not from Python).

- [ ] **Step 1: Write the failing tests**

Add `import json` and `from unittest import mock` to
`tests/test_review_spec.py`'s import block at the top (neither is there
yet — `json` is first needed by this task's own `json.loads`/`json.dump`
calls below, and adding it earlier would be an unused import `ruff`
would catch on an intermediate commit, since `tests/*.py` — unlike
`skills/review-spec/review-spec.py` itself — is in `.pre-commit-config.yaml`'s
ruff scope; `mock` is needed by the `mock.patch.object` calls below).
Final sorted import block: `importlib.util`, `json`, `os`, `subprocess`,
`tempfile`, `time`, `unittest`, then `from unittest import mock` last
(ruff's `I001` groups straight imports before `from` imports of the same
module) — an out-of-order block fails this task's own commit step, same
as an unused one.
Then add to `tests/test_review_spec.py`:

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

    def test_cache_path_honors_xdg_cache_home(self):
        import io
        from contextlib import redirect_stdout
        env = {"XDG_CACHE_HOME": "/x/cache"}
        buf = io.StringIO()
        with mock.patch.object(rs.os, "environ", env), redirect_stdout(buf):
            code = rs.main(["cache-path", "--kind", "runtimes"])
        self.assertEqual(code, 0)
        self.assertEqual(buf.getvalue().strip(), "/x/cache/ai-kit/review-spec/runtimes.json")

    def test_cache_path_quota_kind(self):
        import io
        from contextlib import redirect_stdout
        env = {"HOME": "/home/u"}
        buf = io.StringIO()
        with mock.patch.object(rs.os, "environ", env), redirect_stdout(buf):
            code = rs.main(["cache-path", "--kind", "quota"])
        self.assertEqual(code, 0)
        self.assertEqual(buf.getvalue().strip(), "/home/u/.cache/ai-kit/review-spec/quota.json")

    def test_detect_runtimes_if_stale_skips_detection_when_fresh(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "runtimes.json")
            rs.cache_write_json(path, {"clis": {}})  # just written -> fresh
            import io
            from contextlib import redirect_stdout
            buf = io.StringIO()
            probe_calls = []
            with redirect_stdout(buf):
                code = rs.main(["detect-runtimes", "--if-stale", path],
                                which_fn=lambda n: probe_calls.append(n) or None,
                                run_fn=lambda *a, **k: None)
            self.assertEqual(code, 0)
            self.assertEqual(probe_calls, [])  # detection never ran
            self.assertEqual(json.loads(buf.getvalue()), {})

    def test_detect_runtimes_if_stale_redetects_when_missing(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "runtimes.json")  # never written -> stale
            code = rs.main(["detect-runtimes", "--if-stale", path],
                            which_fn=lambda n: None, run_fn=lambda *a, **k: None)
            self.assertEqual(code, 0)
            self.assertIn("clis", rs.cache_read_json(path))

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

    def test_render_command_returns_nonzero_on_malformed_template(self):
        with tempfile.TemporaryDirectory() as d:
            reviewers_path = os.path.join(d, "reviewers.json")
            with open(reviewers_path, "w", encoding="utf-8") as f:
                json.dump([{"key": "codex-gpt", "model": "gpt-5.2", "vendor": "openai",
                            "cli": "codex", "command": None, "extra": {}}], f)
            prompt_path = os.path.join(d, "prompt.txt")
            with open(prompt_path, "w", encoding="utf-8") as f:
                f.write("hello")
            code = rs.main(["render-command", "--reviewers-json", reviewers_path,
                             "--index", "0", "--prompt-file", prompt_path])
            self.assertEqual(code, 1)

    def test_render_toml_prints_only_without_out(self):
        import io
        from contextlib import redirect_stdout
        with tempfile.TemporaryDirectory() as d:
            json_path = os.path.join(d, "config.json")
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump({"policy": {"mode": "single"}, "reviewers": []}, f)
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = rs.main(["render-toml", "--json-config", json_path])
            self.assertEqual(code, 0)
            self.assertIn("mode", buf.getvalue())
            self.assertFalse(os.path.exists(os.path.join(d, "review-spec.toml")))

    def test_render_toml_with_out_writes_via_cfg_write_toml(self):
        with tempfile.TemporaryDirectory() as d:
            json_path = os.path.join(d, "config.json")
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump({"policy": {"mode": "double", "ladder": ["a"]}, "reviewers": []}, f)
            out_path = os.path.join(d, "nested", "review-spec.toml")
            code = rs.main(["render-toml", "--json-config", json_path, "--out", out_path])
            self.assertEqual(code, 0)
            written = rs.cfg_load_toml(out_path)
            self.assertEqual(written["policy"]["mode"], "double")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m unittest tests.test_review_spec.TestMainCli -v`

Expected: FAIL — `AttributeError: module 'review_spec' has no attribute 'main'`.

- [ ] **Step 3: Implement**

Add `import sys` to the top import block (`argparse` is imported locally
inside `main()` itself, below — no top-level import needed for it).

Append to `skills/review-spec/review-spec.py`:

```python
# ── CLI entrypoint ────────────────────────────────────────────────────────

def main(argv: list, which_fn=shutil.which, run_fn=subprocess.run) -> int:
    import argparse

    parser = argparse.ArgumentParser(prog="review-spec")
    sub = parser.add_subparsers(dest="command", required=True)

    p_cache_path = sub.add_parser("cache-path")
    p_cache_path.add_argument("--kind", choices=["runtimes", "quota"], required=True)

    p_detect = sub.add_parser("detect-runtimes")
    p_detect.add_argument("--save", default=None, help="write the snapshot to this path via cache_write_json")
    p_detect.add_argument("--if-stale", default=None, metavar="PATH",
                           help="skip detection entirely (print {} and exit 0) when PATH exists "
                                "and is fresher than RUNTIMES_TTL_SECONDS; else detect and --save to PATH")

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
    p_toml.add_argument("--out", default=None,
                         help="write the rendered TOML to this path via cfg_write_toml (creating parent dirs) "
                              "instead of only printing it")

    p_render = sub.add_parser("render-command")
    p_render.add_argument("--reviewers-json", required=True,
                           help="path to resolve-reviewers' saved JSON array output")
    p_render.add_argument("--index", type=int, required=True,
                           help="0 for the primary/only reviewer, 1 for the secondary")
    p_render.add_argument("--prompt-file", required=True)

    args = parser.parse_args(argv)

    if args.command == "cache-path":
        env = dict(os.environ)
        print(cache_runtimes_path(env) if args.kind == "runtimes" else cache_quota_path(env))
        return 0

    if args.command == "detect-runtimes":
        if args.if_stale and not cache_is_stale(args.if_stale, RUNTIMES_TTL_SECONDS):
            print(json.dumps({}))  # fresh — caller should treat this as "nothing to do"
            return 0
        snapshot = build_runtimes_snapshot(which_fn=which_fn, run_fn=run_fn)
        save_path = args.if_stale or args.save
        if save_path:
            cache_write_json(save_path, snapshot)
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
        any_source_issues = any(report_declares_issues(text) for _, text in reports)
        print(render_merged_report(merged, args.doc_paths, any_source_issues))
        return 0

    if args.command == "render-toml":
        with open(args.json_config, encoding="utf-8") as f:
            config = json.load(f)
        rendered = cfg_render_toml(config)
        if args.out:
            cfg_write_toml(args.out, config)
        print(rendered)
        return 0

    if args.command == "render-command":
        with open(args.reviewers_json, encoding="utf-8") as f:
            reviewers = json.load(f)
        r = reviewers[args.index]
        resolved = ResolvedReviewer(key=r["key"], model=r["model"], vendor=r["vendor"],
                                     cli=r["cli"], command=r["command"], extra=r["extra"])
        with open(args.prompt_file, encoding="utf-8") as f:
            prompt = f.read()
        try:
            print(render_reviewer_command(resolved, prompt))
        except ValueError as exc:
            # Deliberately no "### Status:" substring — same fail-closed
            # convention as merge-reports (Task 7/8): the orchestrator's
            # existing "No Status line -> Surface failure" rule catches
            # this without any new special-casing (Task 11 Step 3).
            print(f"render-command: {exc}", file=sys.stderr)
            return 1
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m unittest tests.test_review_spec -v`

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
git add skills/review-spec/review-spec.py tests/test_review_spec.py Makefile
git commit -m "feat(review-spec): add CLI entrypoint (detect-runtimes, probe-quota, resolve-reviewers, merge-reports, render-toml); wire cfg_resolve; register with make test"
```

---

### Task 9: CLI profile reference docs

**Files:**
- Create: `skills/review-spec/references/cli-profiles/claude.md`
- Create: `skills/review-spec/references/cli-profiles/codex.md`
- Create: `skills/review-spec/references/cli-profiles/opencode.md`
- Create: `skills/review-spec/references/cli-profiles/grok.md`
- Create: `skills/review-spec/references/cli-profiles/cursor-agent.md`
- Create: `skills/review-spec/references/cli-profiles/gemini.md`
- Test: none (reference docs, not code)

**Interfaces:**
- Produces: the profile paths `review-spec-config` (Task 10) reads when
  helping the user write `[[reviewers]]` entries.

**Read-only posture — required in every profile below.** Design §1 puts
"an external CLI editing the working tree as a separate process" out of
scope as "a different, riskier problem" — a reviewer must never be
dispatched with real write access to the repo under review. Each profile
below states its confirmed status:
- `codex`: **confirmed** — `--sandbox read-only` in its own template.
- `gemini`: **partial** — its template adds `--sandbox` (isolates writes
  to an ephemeral container per the existing `gemini` skill's own flag
  list; the container itself is still writable, but changes never reach
  the real working tree), combined with `--approval-mode yolo` (required
  for non-interactive dispatch — `default` hangs, per that skill).
- `claude`, `opencode`, `grok`, `cursor-agent`: **unconfirmed** — none of
  these CLIs' non-interactive/print modes are confirmed here to forbid
  tool-driven writes; verify (and add the appropriate read-only/sandbox
  flag, or a permission-mode flag if one exists) during
  `review-spec-config`'s implementation (Task 10), before marking any of
  them `status: confirmed` for real dispatch. Each profile below records
  a `read_only:` frontmatter field with its current status so Task 10 can
  warn the user when they configure a `[[reviewers]]` entry for a CLI
  whose profile still says `unconfirmed`.

- [ ] **Step 1: Write `skills/review-spec/references/cli-profiles/claude.md`**

(Four backticks below — this file's own content contains a nested
triple-backtick bash fence, and a 3-backtick outer fence would close early
at that inner fence's closing marker per CommonMark's fence-matching
rules. Every other profile block in this task uses the same 4-backtick
outer fence for the same reason.)

````markdown
---
id: claude
display_name: Claude Code CLI
status: confirmed
read_only: unconfirmed
detect: "which claude"
last_verified: 2026-08-27
---

# claude — reviewer profile

Non-interactive: `-p`/`--print` (print response and exit). Model selection:
`--model <model>`. Output shaping: `--output-format <format>` (only works
with `--print`).

```bash
claude -p --model {model} --output-format text {prompt}
```

`{model}`/`{prompt}` above are the literal config `command` template
placeholders (§3) — written bare, never wrapped in extra quotes.
`render_reviewer_command` (Task 6) applies `shlex.quote` to `{prompt}`
itself before substitution, so a template that adds its own quotes around
`{prompt}` ends up double-quoted. Copy this shape directly into a
`command` field.

Quota/context-window introspection: unconfirmed syntax — research during
the `review-spec-config` implementation task if a dedicated Claude usage
subcommand exists; otherwise rely on the same "low-effort call, detect a
usage-limit error" mechanism confirmed for `codex` (below).
````

- [ ] **Step 2: Write `skills/review-spec/references/cli-profiles/codex.md`**

````markdown
---
id: codex
display_name: OpenAI Codex CLI
status: confirmed
read_only: "confirmed (--sandbox read-only)"
detect: "which codex"
last_verified: 2026-08-27
---

# codex — reviewer profile

Non-interactive: `codex exec`. Model: `-m <model>`. Reasoning effort and
service speed tier are SEPARATE knobs, each set via `-c key='"value"'`:

```bash
codex exec --sandbox read-only --skip-git-repo-check \
  -m {model} \
  -c model_reasoning_effort='"<low|medium|high|xhigh>"' \
  -c service_tier='"<fast|...>"' \
  {prompt}
```

`{model}`/`{prompt}` above are the literal config `command` template
placeholders (§3) — bare, unquoted (`render_reviewer_command` already
`shlex.quote`s `{prompt}`); `model_reasoning_effort`/`service_tier` stay
literal `<...>` since they're config-level `extra` fields, not filled by
`render_reviewer_command` itself. **Do not append `2>/dev/null`** —
`probe_reviewer_quota` (Task 6) classifies availability from
`stdout + stderr` combined, so suppressing stderr hides the exact
usage-limit signal the probe below depends on.

**Quota probe — confirmed live**: a low-effort/fast-tier call against an
exhausted quota returns a usage-limit error. Example that produced exactly
that error during this design's research:

```bash
codex exec -m gpt-5.6-luna -c model_reasoning_effort='"low"' -c service_tier='"fast"' 'Only say: Hello world!'
```

This is the reference implementation for the "cheap probe, detect the
error" quota-check mechanism — parse the exit code / stderr for a
usage-limit signal rather than looking for a dedicated quota subcommand.
````

- [ ] **Step 3: Write `skills/review-spec/references/cli-profiles/opencode.md`**

````markdown
---
id: opencode
display_name: OpenCode CLI
status: confirmed
read_only: unconfirmed
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
opencode run -m {model} {prompt}
```

(`{model}` here is the full `<provider/model>` id, e.g.
`opencode-go/kimi-k3` — `{model}`/`{prompt}` are bare config `command`
template placeholders, per the `claude` profile's note above.)

`opencode stats` shows token usage/cost statistics — likely the quota
introspection source; exact parseable shape unconfirmed, research during
implementation.
````

- [ ] **Step 4: Write `skills/review-spec/references/cli-profiles/grok.md`**

````markdown
---
id: grok
display_name: Grok CLI (xAI)
status: confirmed
read_only: unconfirmed
detect: "which grok"
last_verified: 2026-08-27
---

# grok — reviewer profile

Model: `-m/--model <MODEL>`. Output shaping: `--output-format
<OUTPUT_FORMAT>`; `--json-schema <SCHEMA>` for structured output (implies
`--output-format json`).

```bash
grok -m {model} --output-format json {prompt}
```

(`{model}`/`{prompt}` are bare config `command` template placeholders, per
the `claude` profile's note above.)

Quota/context-window introspection: unconfirmed syntax — research during
implementation.
````

- [ ] **Step 5: Write `skills/review-spec/references/cli-profiles/cursor-agent.md`**

````markdown
---
id: cursor-agent
display_name: Cursor Agent CLI
status: stub (web-research only — not installed on the reference machine)
read_only: unconfirmed
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
cursor-agent -p {prompt} --output-format json --model {model}
```

(`{model}`/`{prompt}` are bare config `command` template placeholders, per
the `claude` profile's note above.)

Not yet verified against a real installation. Verify all of the above with
`cursor-agent --help` before marking this profile `status: confirmed`.
````

- [ ] **Step 6: Write `skills/review-spec/references/cli-profiles/gemini.md`**

````markdown
---
id: gemini
display_name: Gemini CLI
status: stub (carried over from the existing `gemini` skill's documented flags — not installed on the reference machine)
read_only: "partial (--sandbox isolates writes to an ephemeral container; not a true no-write guarantee)"
detect: "which gemini"
last_verified: 2026-08-27
---

# gemini — reviewer profile (STUB — unverified live on this machine)

Per the existing `gemini` skill (`~/.claude/skills/gemini/SKILL.md`):
model via `-m/--model <MODEL>`; **background/non-interactive runs require
`--approval-mode yolo`** (the `default` approval mode hangs indefinitely in
a non-interactive shell — do not use it here); `-s`/`--sandbox` runs the
call in an isolated container, so `yolo`-approved writes never reach the
real working tree — include it always, since `yolo` alone grants
unrestricted write access to whatever it runs against.

```bash
gemini -m {model} --sandbox --approval-mode yolo {prompt}
```

(`{model}`/`{prompt}` are bare config `command` template placeholders, per
the `claude` profile's note above.)

Quota/context-window introspection: unconfirmed syntax — research during
implementation.
````

- [ ] **Step 7: Commit**

```bash
git add skills/review-spec/references/cli-profiles/
git commit -m "docs(review-spec): add CLI profiles for claude, codex, opencode, grok (confirmed) + cursor-agent, gemini (stub)"
```

---

### Task 10: `review-spec-config` skill (new)

**Files:**
- Create: `skills/review-spec-config/SKILL.md`
- Test: none (interactive skill, no automated test — matches this repo's
  precedent for interactive/prose skills)

**Interfaces:**
- Consumes: `skills/review-spec/review-spec.py`'s `detect-runtimes` and `render-toml`
  subcommands (Task 8), the CLI profiles (Task 9).
- Produces: writes `review-spec.toml` (global by default, `--local` for
  `./.aikit/review-spec.toml`) and `runtimes.json`. Consumed by
  `review-spec`'s Step 0.7 (Task 11).

- [ ] **Step 1: Write `skills/review-spec-config/SKILL.md`**

(Four backticks below — this file's own content contains several nested
triple-backtick `bash`/`markdown` fences, and a 3-backtick outer fence
would close early at the first inner closing marker per CommonMark's
fence-matching rules.)

````markdown
---
name: review-spec-config
description: Interactive setup for review-spec's cross-AI reviewer config — detects installed CLIs/models, asks which to use as reviewers and in what priority, writes review-spec.toml. Use when the user asks to configure cross-AI review, or when review-spec warns no config exists. Supports --check-only (report availability, no writes) and --local (write ./.aikit/review-spec.toml instead of the global config).
---

## Your task

Set up (or refresh) `review-spec`'s cross-AI reviewer configuration.

### Step 0 — Locate `review-spec.py` and the CLI profiles

`review-spec.py` and its `references/cli-profiles/` live inside the
**`review-spec`** skill's own directory (a sibling of this skill, not
this skill's own directory, and not a top-level `tools/`/`references/` —
see `review-spec/SKILL.md`'s Step 0.7 point 0 — Task 11 — for why).
Resolve them the identical way `review-spec/SKILL.md` itself resolves
these same two paths (Task 11 Step 2 point 0) — same three candidates,
self-contained, no shared variable between the two skills — so both
agree on one procedure:

```bash
for d in "${CLAUDE_PLUGIN_ROOT:+$CLAUDE_PLUGIN_ROOT/skills/review-spec}" \
         "$HOME/.claude/skills/review-spec" \
         "$(dirname "<absolute path to THIS SKILL.md>")/../review-spec"; do
  [ -d "$d" ] && { REVIEW_SPEC_SKILL_DIR="$d"; break; }
done
TOOLS_PY="$REVIEW_SPEC_SKILL_DIR/review-spec.py"
CLI_PROFILES_DIR="$REVIEW_SPEC_SKILL_DIR/references/cli-profiles"
RUNTIMES_JSON="$(python3 "$TOOLS_PY" cache-path --kind runtimes)"
printf '%s\n' "$TOOLS_PY" "$CLI_PROFILES_DIR" "$RUNTIMES_JSON"
```

(The third candidate is `review-spec-config`'s own sibling — matching
`SEEDS_DIR`'s own third candidate — since this skill's directory and
`review-spec`'s are installed alongside each other in every shape:
plugin, `~/.claude/skills`, or a direct dev checkout. `cache-path`
resolves the `${XDG_CACHE_HOME:-$HOME/.cache}`-aware path through Task 3's
`cache_runtimes_path` — the same call `review-spec/SKILL.md` itself uses
— so both skills always agree on where this file lives.)

**Resolve this whole block once, in one `Bash` call, and record
`TOOLS_PY`/`CLI_PROFILES_DIR`/`RUNTIMES_JSON` from its `printf` output as
literal absolute paths — not shell environment variables.** Every `Bash`
tool call in this harness starts a fresh shell, so a variable assigned in
one call is gone by the next; every `$TOOLS_PY`/`$CLI_PROFILES_DIR`/
`$RUNTIMES_JSON` reference in Steps 1–3 below means "the literal path
captured here", substituted directly, exactly the way `review-spec/SKILL.md`'s
own `TOOLS_PY`/`RUN_TMP_DIR` work (Task 11 Step 2 point 0/point 1) — this
skill has its own separate `AskUserQuestion` interaction (Step 2) between
this resolution and Step 3's write, guaranteeing at least one call
boundary in between.

### Step 1 — Detect

```bash
python3 "$TOOLS_PY" detect-runtimes
```

Parse the printed JSON: for each CLI marked `"installed": true`, note its
path; for `opencode`, note its `models` list.

**If `--check-only` was passed**: report which CLIs are installed, which
have a `review-spec.toml` reviewer entry already, and stop here — do not
persist the snapshot and do not write anything else, matching this
skill's own `--check-only` contract (frontmatter `description:` above).

**Otherwise**, persist the snapshot before continuing to Step 2:
```bash
python3 "$TOOLS_PY" detect-runtimes --save "$RUNTIMES_JSON"
```
(re-running detection here is cheap and keeps this step's logic linear —
`--save` persists via `cache_write_json`, Task 8, so `review-spec` doesn't
have to re-detect next session.)

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
needs. **If the profile's `read_only:` field says `unconfirmed`**, print
one line before writing that entry: "Note: `<id>` has no confirmed
read-only invocation — this reviewer runs with the CLI's normal write
permissions against your working tree." (per design §5's read-only
posture) — inform, don't block; the user is choosing to accept that CLI's
default risk.

**For a native (cli-less) reviewer entry** — e.g. the current
session's own runtime, or another Claude tier reachable without an
external CLI — `model` must be one of the four `Agent`-tool aliases
(`sonnet`/`opus`/`haiku`/`fable`), never a full model id like `"opus-5"`;
ask the user to pick one of those four rather than typing a version
string.

Then ask: `policy.mode` (`single` or `double`) and the `policy.ladder`
order (default to the order the user answered the per-CLI questions in,
but let them reorder). If `--local` was passed, also ask whether this
local config should be `local-only` or the default `global-merge` — set
the JSON config's top-level `strategy` key to `"local-only"` if so
(`cfg_render_toml` renders it as a bare `strategy = "..."` line at the
top of the file, §3); omit the key entirely for the default (global
default applies, no line needed).

### Step 3 — Write

Build the JSON shape `skills/review-spec/review-spec.py`'s `render-toml` subcommand
expects (`{"strategy": "...", "policy": {...}, "reviewers": [...]}` — the
`strategy` key only when Step 2 asked for `local-only`), write it to a
temp JSON file, then let `--out` do the write directly (via
`cfg_write_toml`, creating parent dirs as needed) rather than piping
stdout through a second write yourself:

```bash
python3 "$TOOLS_PY" render-toml --json-config <temp.json> --out <target path>
```

Target path: `~/.config/ai-kit/review-spec.toml` by default, or
`./.aikit/review-spec.toml` if `--local` was passed. (The runtimes
snapshot was already persisted in Step 1 via `--save` — no separate write
needed here.)

### Step 4 — Report

Print a short summary: which reviewers are now configured, in what
mode/order, and the path written to.
````

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
- Consumes: `skills/review-spec/review-spec.py`'s `probe-quota`, `resolve-reviewers`,
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
  `anthropic`) — the document's authoring vendor, used by Step 0.7's
  ladder walk to prefer an independent perspective. Design §4's default is
  "the current session's own vendor"; `anthropic` is that default's
  concrete value here specifically because this orchestrator has no
  runtime introspection API telling it what vendor its own model actually
  is — it can only assume the overwhelmingly common case (a native
  Claude Code session). Design §3's caveat still applies: a session
  pointed at a compatible third-party endpoint would make this default
  wrong, which is exactly the escape hatch `--source-vendor` itself
  exists for — pass the real vendor explicitly in that case. This is a
  **vendor** (`anthropic`, `openai`, `xai`, ...), matching the `vendor`
  field in `review-spec.toml` reviewer entries — not a model id, since
  deriving a vendor from an arbitrary model-id string has no sanctioned
  mapping (model names churn too fast to hardcode a lookup table).
```

- [ ] **Step 2: Add Step 0.7 after the existing Step 0.6**

Insert into `skills/review-spec/SKILL.md`, immediately after Step 0.6's
final paragraph (the one ending "...If no sibling context exists, pass
`none`."):

(Four backticks below — this insertion contains several nested
triple-backtick `bash` fences, and a 3-backtick outer fence would close
early at the first inner closing marker per CommonMark's fence-matching
rules, regardless of the inner fences' list-item indentation.)

````markdown
## Step 0.7 — Resolve the reviewer list (cross-AI)

Runs once per invocation, after Step 0.6.

0. Resolve `TOOLS_PY` and `CHECKLIST_SKILL_MD`. **`review-spec.py` lives
   inside `skills/review-spec/` itself** (not at a top-level `tools/` —
   that placement was tried in an earlier draft of this plan and
   rejected: it isn't reachable from an installed skill, since
   `tools/setup.py`'s symlinks only cover `agents/commands/skills`, per
   its `CATEGORIES`). Because it's inside `review-spec`'s own skill
   directory, it resolves the same way `SEEDS_DIR` (in the `## Constants`
   section, below this Step 0.7 insertion point) is *meant* to (three
   candidates: `CLAUDE_PLUGIN_ROOT`/`~/.claude/skills`/
   sibling-of-this-file) — this snippet is **self-contained** and does
   not read any variable assigned elsewhere; it computes its own
   directory inline via `$(dirname ...)`. (Task 11 Step 7 separately
   fixes a real pre-existing bug in `SEEDS_DIR`'s own block — its third
   candidate references an `$SKILL_DIR` that block never actually
   assigns — bringing that block's behavior in line with what its
   comment always claimed, and with this new snippet.):
   ```bash
   for d in "${CLAUDE_PLUGIN_ROOT:+$CLAUDE_PLUGIN_ROOT/skills/review-spec}" \
            "$HOME/.claude/skills/review-spec" \
            "$(dirname "<absolute path to THIS SKILL.md>")"; do
     [ -d "$d" ] && { REVIEW_SPEC_SKILL_DIR="$d"; break; }
   done
   TOOLS_PY="$REVIEW_SPEC_SKILL_DIR/review-spec.py"
   CHECKLIST_SKILL_MD="$(dirname "$REVIEW_SPEC_SKILL_DIR")/review-spec-checklist/SKILL.md"
   RUNTIMES_JSON="$(python3 "$TOOLS_PY" cache-path --kind runtimes)"
   QUOTA_JSON="$(python3 "$TOOLS_PY" cache-path --kind quota)"
   printf '%s\n' "$TOOLS_PY" "$CHECKLIST_SKILL_MD" "$RUNTIMES_JSON" "$QUOTA_JSON"
   ```
   `CHECKLIST_SKILL_MD` is the path Step 1's external-CLI dispatch tells
   the external reviewer to `Read` — `review-spec-checklist` (renamed
   from `reviewing-specs` by Task 1) is always installed as
   `review-spec`'s own sibling, since both live under the same `skills/`
   tree in every installed shape (plugin, `~/.claude/skills`, or a dev
   checkout), so deriving it from `$REVIEW_SPEC_SKILL_DIR`'s own parent
   needs no separate three-candidate search. `cache-path` (Task 8)
   resolves `RUNTIMES_JSON`/`QUOTA_JSON` through the module's own
   `cache_runtimes_path`/`cache_quota_path` (Task 3) — the
   `${XDG_CACHE_HOME:-$HOME/.cache}/ai-kit/review-spec/...` formula lives
   in exactly one place, not duplicated as a bash literal here.
   Resolve this whole block once, in one `Bash` call, and — exactly like
   `RUN_TMP_DIR` below — record `TOOLS_PY`/`CHECKLIST_SKILL_MD`/
   `RUNTIMES_JSON`/`QUOTA_JSON` from the trailing `printf`'s stdout (four
   lines, in that order) as literal absolute paths substituted into every
   later command and prose reference; they are **not** shell environment
   variables that survive across separate `Bash` tool calls (this bit a
   first draft of this very step — see this plan's Self-review notes). If
   `TOOLS_PY` does not exist at the resolved path, treat this
   exactly like `--no-cross-ai` (point 2 below) — cross-AI support isn't
   installed, never block the review over it.
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
2. **If `--no-cross-ai` was requested (or `TOOLS_PY` is missing, point 0
   above)**: set `REVIEWER_LIST` directly, in-context, to the single-entry
   array `[{"key": "session-default", "model": "", "vendor": "", "cli":
   null, "command": null, "extra": {}}]` — `NO_CONFIG_FALLBACK`'s exact
   shape (Task 5). **Do not run `resolve-reviewers`, `probe-quota`, or
   `detect-runtimes`, and do not write `$RUN_TMP_DIR/reviewers.json`** —
   points 3–5 below are entirely skipped, not just their side effects;
   this is the "skip it entirely, minimal overhead" case the flag exists
   for. Because this entry's `cli` is always `null`, Step 1's dispatch
   never needs `reviewers.json` for it either (only the external branch
   reads that file), so nothing downstream is left dangling. Go directly
   to Step 1.
3. Refresh the runtimes snapshot if it's missing or older than
   `RUNTIMES_TTL_SECONDS` (~30 days — CLI/model presence rarely changes):
   ```bash
   python3 "$TOOLS_PY" detect-runtimes --if-stale "$RUNTIMES_JSON"
   ```
   `--if-stale` (Task 8) checks `cache_is_stale` itself and no-ops
   (prints `{}`, doesn't touch the file) when the existing snapshot is
   still fresh; when missing or stale it detects and saves in the same
   call, so this is always safe to run. If this was the first-ever save
   (i.e. `$RUNTIMES_JSON` didn't exist before this call — check with `[ ]`
   before running it if you need to know), print one line — "No cross-AI
   config saved yet — run `review-spec-config` so this doesn't repeat
   every invocation." — then continue to step 4 regardless; do NOT skip
   reviewer resolution (there's usually no `review-spec.toml` yet either,
   so `resolve-reviewers` in step 5 degrades to `NO_CONFIG_FALLBACK` on
   its own — no special-casing needed here beyond the detection call and
   the hint).
4. Refresh quota for anything the config's ladder might need:
   ```bash
   python3 "$TOOLS_PY" probe-quota --cwd <CODEBASE_ROOT> \
     --quota-path "$QUOTA_JSON"
   ```
   (No-op — writes `{}` — when there is no config/ladder to probe.)
5. Resolve the reviewer list, saving its output to a file (Step 1's
   external dispatch needs a stable path to feed `render-command`, not
   just the in-context text). This point is only reached when cross-AI is
   actually active — `--no-cross-ai` already short-circuited at step 2
   above — so `--cross-ai` is always passed here, never conditionally
   (fixing a broken shell line-continuation from an earlier draft: a
   trailing `\` followed by an inline `#` comment escapes the *space*
   before the comment, not the newline, so the redirect below it silently
   became a separate command that truncated the file):
   ```bash
   python3 "$TOOLS_PY" resolve-reviewers \
     --cwd <CODEBASE_ROOT> \
     --quota "$QUOTA_JSON" \
     --source-vendor <SOURCE_VENDOR from the "## Inputs" section's flag parsing, Task 11 Step 1> \
     --cross-ai \
     > "$RUN_TMP_DIR/reviewers.json"
   ```
   `resolve-reviewers` itself calls `cfg_resolve(cwd, env)` (Task 2),
   which already handles the local-vs-global/`strategy` resolution — this
   step never re-implements that logic, it only picks which `--cwd` to
   pass (`CODEBASE_ROOT` from Step 0.1, so the resolved local config is
   the one that actually owns the document under review).
6. **(Active cross-AI path only — point 2's degraded path already set
   `REVIEWER_LIST` directly and skipped straight to Step 1.)**
   `$RUN_TMP_DIR/reviewers.json` holds a JSON array of 1 or 2 reviewer
   objects. Record its contents as `REVIEWER_LIST` (index 0 = primary/only
   reviewer, index 1 = the secondary in double mode) — Step 1 both reasons
   over this in-context and passes the same file's path to `render-command`
   for external dispatch.
````

- [ ] **Step 3: Rewrite Step 1 to branch on `REVIEWER_LIST`**

Replace the existing "Step 1 — Dispatch reviewer (every iteration)"
section's opening (the part before the reviewer prompt template) with:

(Four backticks below — this insertion contains nested triple-backtick
fences (the prompt-text block and the `render-command` bash block), and a
3-backtick outer fence would close early at the first inner closing
marker per CommonMark's fence-matching rules.)

````markdown
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
     Read the file at <CHECKLIST_SKILL_MD (Step 0.7 point 0)>
     and follow it exactly, substituting:
     - ARCHETYPE = <ARCHETYPE>
     - FRAMEWORK_PROFILE_PATH = <FRAMEWORK_PROFILE_PATH>
     Read every file under review fresh from disk: <DOC_PATHS>
     Complementary grounding documents (Read for context — DO NOT review,
     score, or emit findings about these): <GROUNDING_DOCS>
     These are the upstream context/research the document under review is
     derived from. Use them to detect drift — where the document under
     review contradicts or omits what its own intent/research established —
     and fold that into findings about the REVIEWED document only. If
     "none", there are none.
     Codebase root(s) for grounding: <CODEBASE_ROOT>
     The paths the document itself declares (worktree/target locations,
     cross-repo references) are AUTHORITATIVE for this review — do not flag
     them or "correct" them just because they differ from CLAUDE.md /
     .claude/worktrees convention; only flag a path if it's internally
     inconsistent or violates a hard constraint.
     ARCHETYPE is the ceiling per document: judge an upstream doc (e.g.
     intent) only at its own level — never demand downstream detail
     (tasks, exact files, interfaces) it isn't meant to have.
     Emit the report following that skill's Output template strictly, ending
     with the ### Status: line. Do not edit any file under review.
     ```

     (External CLIs can't call our `Skill` tool, but they can read a file
     path — this keeps `review-spec-checklist` the single source of truth
     for the checklist instead of duplicating its content into every
     CLI's prompt. The substitutions and rules above mirror the native
     template's `<GROUNDING_DOCS>`, declared-paths-authoritative, and
     ARCHETYPE-ceiling clauses verbatim — see `skills/review-spec/SKILL.md`'s
     Step 1 reviewer prompt template — so an external reviewer works from
     the exact same contract a native one does, not a thinner one.)
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
     yourself. **If this exits nonzero** (a malformed or missing `command`
     template on this reviewer entry — a config error, not a runtime
     failure), do not attempt to run anything: this reviewer's slot
     failed to dispatch. Do not write `$RUN_TMP_DIR/iter<N>-<key>.md` for
     it — leaving it absent is what makes Step 1.5's `merge-reports`
     (double mode) or the missing-file case (single mode) fail closed
     through the existing `### Status:`-line-based rules, with no new
     special-casing needed here.
  3. Execute the printed command via the `Bash` tool with an explicit
     timeout (e.g. 300000ms / 5 minutes — generous for a real review call,
     distinct from the quota probe's 30s timeout since this is a full
     document review, not a trivial probe), redirecting stdout to
     `$RUN_TMP_DIR/iter<N>-<key>.md`.

Then continue with the existing reviewer prompt template (for the native
case) unchanged below, except the skill name substitution above.
````

- [ ] **Step 4: Add Step 1.5 after the new Step 1**

(Four backticks below — this insertion contains a nested triple-backtick
`bash` fence.)

````markdown
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
````

- [ ] **Step 5: Point Step 2 at `EFFECTIVE_REPORT_PATH`, then replace every remaining `/tmp/review-spec` reference with `$RUN_TMP_DIR`**

First: `skills/review-spec/SKILL.md`'s `### Step 2 — Parse reviewer Status`
currently opens with `Locate the line beginning \`### Status:\` in the
reviewer's output.` — this assumed the reviewer's text is still in
context, which is no longer true for ANY dispatch shape after Step 1/1.5
(native reports are now written to disk too, per Step 3's native branch
above; external reports always were; merged reports always were). Change
it to `Read \`EFFECTIVE_REPORT_PATH\` (Step 1.5) from disk; locate the
line beginning \`### Status:\` in it.` — otherwise a single-reviewer
external-CLI run (the common `single`-mode cross-AI case) has nothing in
context to parse and every such run falsely reads as "No Status line".

Find every occurrence — there are more than the two obvious ones (the
cross-AI dry run caught a missed one at the GSD-handoff Surface message):

```bash
grep -n "/tmp/review-spec" skills/review-spec/SKILL.md
```

Fix each — every one below points at the SAME `EFFECTIVE_REPORT_PATH`
(Step 1.5) rather than inventing its own new filename, closing a bug the
live re-review found (three different invented names —
`fixer-input.md`/`report.md`/the raw per-key name — for what should be one
path). Verified live against the real current file — the exact locations
are:
- **Line 323** (Step 3): `Save the reviewer's report to a temp file
  (\`/tmp/review-spec-report-iter<N>.md\`) so downstream subagents/skills
  can \`Read\` it.` → `The reviewer's report is already at
  \`EFFECTIVE_REPORT_PATH\` (Step 1.5) — no separate save needed here.`
- **Every `<REPORT_TEMP_PATH>` placeholder that reads this saved report**
  (lines 360, 383, 392, 430 — the fixer's prompt-template substitution
  list and its two "Review report: ..." lines) — since Step 3's own save
  is being removed by the bullet above, `<REPORT_TEMP_PATH>` is no longer
  bound by anything. Rename every one of these four occurrences to
  `<EFFECTIVE_REPORT_PATH>`, bound to the value Step 1.5 (Task 11 Step 4)
  established — one name for the same path throughout the whole skill,
  not two.
- The Constants section's `**Loop state file (optional):**
  /tmp/review-spec-<doc-basename>-<timestamp>.log` → `**Loop state file
  (optional):** \`$RUN_TMP_DIR/loop.log\``.
- **Line 438** (Step 3b-surface's example sentence): `... run: /gsd-plan-phase 2 --reviews  (findings: /tmp/review-spec-report-iter<N>.md), then re-run /review-spec.\`` →
  `... run: /gsd-plan-phase 2 --reviews  (findings: EFFECTIVE_REPORT_PATH), then re-run /review-spec.\`` —
  note line 474's Surface table row already uses a generic `<report
  path>` placeholder with no literal `/tmp/` string, so it needs no
  change; only this one concrete example sentence does.
- **Line 183** (the `NEVER` rule): `**NEVER run the generic fixer before
  the reviewer's report is written to its temp file** (Step 3). The
  fixer has nothing to \`Read\` otherwise.` → `**NEVER run the generic
  fixer before \`EFFECTIVE_REPORT_PATH\` exists on disk** (Step 1.5).
  The fixer has nothing to \`Read\` otherwise.` — the old wording still
  named "Step 3" and "its temp file", both stale now that the save
  happens at Step 1.5 (the merge/single-report step) and there's no
  separate temp-file write.

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

- [ ] **Step 7: Update the Constants section's fixer/reviewer skill names — and delete the hardcoded reviewer model line**

Change `**Reviewer skill:** \`reviewing-specs\`` to `**Reviewer skill:**
\`review-spec-checklist\`` and `**Fixer skill:** \`applying-review-feedback\``
to `**Fixer skill:** \`review-spec-fixer\`` (if Task 1 hasn't already
caught these specific lines — re-grep to confirm).

Also fix a real, pre-existing bug in the `SEEDS_DIR` resolution block
(lines 156–169) directly below the `**Loop state file**` line — its
third candidate references `$SKILL_DIR` (`"$SKILL_DIR/../reviewing-specs/references/frameworks"`),
but nothing in this skill ever assigns that variable; the comment
`# SKILL_DIR = the directory containing this SKILL.md` documents intent,
not an assignment. **Verified live against the real file.** Add the
missing assignment as the first line inside the `for d in ...` block:
```bash
SKILL_DIR="$(dirname "<absolute path to THIS SKILL.md>")"
for d in "${CLAUDE_PLUGIN_ROOT:+$CLAUDE_PLUGIN_ROOT/skills/review-spec-checklist/references/frameworks}" \
```
(the `for d in ...` line itself is already being rewritten by Task 1 Step
3 to the new `review-spec-checklist` name — this just adds the missing
`SKILL_DIR=` line immediately before it, in the same block). This bug
predates this plan, but the new `TOOLS_PY`/`CHECKLIST_SKILL_MD`
resolution (Step 2 point 0 below) is modeled directly on this exact
block, so fixing it here keeps both resolutions genuinely consistent
instead of one working and the other's precedent silently broken.

Also replace line 153, `**Subagent model for both:** \`sonnet\` (Haiku
misses subtle defects; Opus burns tokens for no extra review-quality
signal)`, with `**Fixer subagent model:** \`sonnet\` (Haiku misses subtle
defects; Opus burns tokens for no extra fix-quality signal — the fixer
stays Claude-only and sonnet-pinned; design §1 explicitly puts changing
who edits out of scope). The reviewer's model is no longer a Constant at
all — it comes from `REVIEWER_LIST` (Step 5), set per-entry.`. **Verified
live: this line is never touched by any other step in this task**, and
left as-is it directly contradicts Step 3's dispatch rule (the entry's
`model`, omitted only when empty) — two readings of the same skill with
opposite outcomes, and a literal reintroduction of the exact
hardcoded-model anti-pattern this whole plan exists to remove.

- [ ] **Step 8: Update the loop diagram for 1–2 reviewer dispatches and the merge step**

`skills/review-spec/SKILL.md`'s ` ```dot ` loop diagram (the `digraph
review_spec { ... }` block, immediately above the Constants section)
still names a single `"Dispatch reviewer subagent (fresh)"` node feeding
straight into `"Parse Status line"` — a single-reviewer flow. After Steps
2–5 above, the real flow is 1 or 2 dispatches, an optional merge
(`Step 1.5`, only when `REVIEWER_LIST` has 2 entries), then reading
`EFFECTIVE_REPORT_PATH` — leaving the diagram as-is would ship a skill
whose diagram contradicts its own prose.

Rename the node `"Dispatch reviewer subagent (fresh)"` to `"Dispatch
reviewer(s) (fresh)"` everywhere it appears (every edge target/source
using that exact string — there are several, feeding back into it from
the fixer-loop nodes on the next iteration; keep every one of those edges
pointed at the renamed node, just renamed). Insert one new node between
it and `"Parse Status line"`:
```dot
"Read EFFECTIVE_REPORT_PATH" [shape=box];
```
with edges:
```dot
"Dispatch reviewer(s) (fresh)" -> "Read EFFECTIVE_REPORT_PATH";
"Read EFFECTIVE_REPORT_PATH" -> "Parse Status line";
```
replacing the old direct `"Dispatch reviewer subagent (fresh)" -> "Parse
Status line"` edge. This one box stands in for both the single-reviewer
case (raw report) and the double-reviewer case (Step 1.5's merge already
produced this same path) — the diagram is a coarse per-iteration overview
(it doesn't branch on `policy.mode` today either, e.g. it doesn't show
the fixer-route resolution's own internal branching in detail), so one
node capturing "however many reviewers ran, this is what gets parsed" is
consistent with its existing level of detail, not a gap.

- [ ] **Step 9: Manual dry run — verify `RUN_TMP_DIR` and merge wiring**

This task's own automated tests (Task 8) only exercise `skills/review-spec/review-spec.py`
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

- [ ] **Step 10: Commit**

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
  consolidates into one `skills/review-spec/review-spec.py`, matching this repo's
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
| CRITICAL | `tools/review-spec.py` and `references/review-spec/cli-profiles/` (their location at the time of this first review round) live at the repo root, which `tools/setup.py` never symlinks (only `agents`/`commands`/`skills`) — unreachable from an installed skill | First fix: a `KIT_ROOT`/`TOOLS_PY`/`CLI_PROFILES_DIR` resolution deriving the repo root via `realpath`+suffix-strip. **This fix was itself superseded in the second review round below** — it reintroduced the exact fresh-shell-variable bug it was fixing for `RUN_TMP_DIR`, and depended on a `SKILL_DIR` variable this skill never actually defines. The real fix: relocate both artifacts inside `skills/review-spec/` itself and resolve them with the same three-candidate pattern already used for `SEEDS_DIR` — see the second table |
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
| CROSS-DOC | Design §3/§7/§11 still described a `scripts/review-spec/detect-runtimes.sh` shell script and its own unit tests — the plan builds none of that (one `skills/review-spec/review-spec.py`) | Design §3 Scope, §7, and §11's testing section rewritten to the actual `skills/review-spec/review-spec.py` shape |
| CROSS-DOC | Design's example `policy.ladder` ordering only made sense under the old (incorrect) double-mode semantics | Resolved as a side effect of the double-mode fix above — the example's only native entry (`claude-opus`) now correctly becomes the primary regardless of its position in the ladder, verified by trace and by the new regression tests |

MEDIUM findings (all fixed, no table): `cfg_render_toml`/`cfg_write_toml`
added to Task 2's Interfaces (they were implemented and tested but never
listed as produced); `parse_findings`'s docstring already matched its
`### ` regex correctly by this point (left as-is, verified);
`render_merged_report`'s docstring now states explicitly that it drops
each source report's own `Document Type`/`Files Read` lines by design; the
one remaining Spanish string (Step 0.7's hint message, and its design §6
mirror) translated to English to match the rest of the skill.

### Third review: a second clean-context Opus 5 subagent (native, live)

The second Opus 5 round's fixes were themselves reviewed by a THIRD
clean-context Opus 5 subagent, run the same way and told explicitly not
to trust the "already fixed" summary — read the current documents fresh.
It found the second round's `KIT_ROOT` fix had reintroduced the exact bug
it was fixing, plus a real Task 1 gap the first two rounds both missed
(two Python files, not just Markdown), plus several more real defects.
7 CRITICAL/HIGH findings, all fixed:

| Severity | Finding | Fix |
|---|---|---|
| CRITICAL | `TOOLS_PY`/`KIT_ROOT`/`CLI_PROFILES_DIR` were resolved in one `Bash` call (Task 11 Step 2 point 0) but then referenced via `"$TOOLS_PY"` from several LATER, separate `Bash` calls (probe-quota, resolve-reviewers, render-command, merge-reports, and independently in Task 10) — the exact fresh-shell-variable bug already fixed once for `RUN_TMP_DIR`, reintroduced one paragraph below it | Root-caused and fixed properly: `tools/review-spec.py` and `references/review-spec/cli-profiles/` relocated to `skills/review-spec/review-spec.py` and `skills/review-spec/references/cli-profiles/` — INSIDE the already-guaranteed-installed `review-spec` skill directory — so they resolve with the exact three-candidate pattern (`CLAUDE_PLUGIN_ROOT`/`~/.claude/skills`/sibling-of-this-file) the skill already uses for `SEEDS_DIR`, in one `Bash` call, substituted literally afterward exactly like `RUN_TMP_DIR` |
| CRITICAL | The `KIT_ROOT` derivation depended on a `SKILL_DIR` variable the comment claimed was "already established above" — verified live, `review-spec/SKILL.md` never defines any such variable; `SEEDS_DIR` is resolved from three full candidate paths directly, with no intermediate name | Eliminated along with the `KIT_ROOT` mechanism above — the replacement resolves `REVIEW_SPEC_SKILL_DIR` directly via the same three literal candidates `SEEDS_DIR` uses, no intermediate "resolve my own directory first" step |
| CRITICAL | Task 1's verification grep was scoped to `--include="*.md"` and missed `tests/test_framework_profiles.py:13` and `tests/test_wizard_pty.py:50/358`, which hardcode the old skill names — verified live via an unscoped repo grep | New Task 1 Step 5 fixes both Python files explicitly, BEFORE the Markdown sweep — `tests.test_wizard_pty` is in both the `Makefile` `test:` target and a `.pre-commit-config.yaml` hook, so skipping it would break this task's own commit gate |
| CRITICAL | Task 1's old Step 5 file-count arithmetic was wrong (claimed 16 post-move/11-must-fix when the real numbers are 13 post-move/8-must-fix, and claimed "6 already fixed" when it's 4) | Recomputed against a live grep of the real repo and corrected throughout (now Task 1 Step 6) |
| HIGH | Deleting Step 3's report-save sentence (round 2's `EFFECTIVE_REPORT_PATH` fix) left `<REPORT_TEMP_PATH>` — the fixer prompt's substitution placeholder, used at 4 separate lines — permanently undefined | Task 11 Step 5 now also renames every `<REPORT_TEMP_PATH>` occurrence to `<EFFECTIVE_REPORT_PATH>`, bound once, used everywhere |
| HIGH | Constants line `**Subagent model for both:** \`sonnet\`` was never updated, directly contradicting Step 3's per-entry `model` dispatch rule — and reintroducing the exact hardcoded-model anti-pattern this plan exists to remove | Task 11 Step 7 now replaces it with a fixer-only `**Fixer subagent model:** \`sonnet\`` constant; the reviewer's model is no longer a Constant, it comes from `REVIEWER_LIST` |
| HIGH | Step 2 ("Parse reviewer Status") still said "Locate the line... in the reviewer's output" — but every report is now written to disk, not left in context, so a single external-CLI reviewer run had nothing to parse | Task 11 Step 5 rewrites Step 2's opening to read `EFFECTIVE_REPORT_PATH` from disk first |
| HIGH | Design's example `codex`/`grok` `command` templates ended in `2>/dev/null`, discarding the exact stderr signal `probe_reviewer_quota` depends on to detect a usage-limit error | Removed `2>/dev/null` from both example templates in design §3 |
| HIGH | `tomllib` import-guard rationale claimed `.python-version` (3.12) governs the runtime, and cited the `Makefile`'s `test:` target as running `.venv/bin/python3` | Both claims were wrong — `.python-version` governs the `uv`-managed dev venv, and the `Makefile`/pre-commit both run bare system `python3`, exactly like `status-line.py`. Reverted to matching `status-line.py`'s actual guarded-import pattern (`try/except ModuleNotFoundError`, degrade to `tomllib = None`) instead of arguing the guard was unnecessary |
| MEDIUM | Task 2's original Step 3 imported all 9 of this module's eventual dependencies (`json`, `re`, `shlex`, `shutil`, `subprocess`, `sys`, `time`, `tomllib`, `NamedTuple`/`Optional`) upfront — `ruff`'s `F401` would fail Task 2's own commit, since ~7 are unused until later tasks | Each task now adds only the import(s) it newly needs, in the order tasks are executed (`Optional` moved to Task 3, where `cache_read_json`'s return type first needs it) |
| MEDIUM | Task 10's `SKILL_DIR` candidate list used a different, inconsistent form from Task 11's | Both now resolve the same way, pointed at `review-spec`'s directory either way (Task 10 as a sibling skill, Task 11 as itself) |
| MEDIUM | A Task 5 test name/comment (`test_double_mode_primary_is_best_overall_regardless_of_vendor`, `# best overall = top of ladder`) still asserted the pre-native-baseline-fix semantics | Renamed to `test_double_mode_primary_is_best_native_entry_tier_aware`, comment updated |
| MEDIUM | Task 11 Step 5's third `/tmp/review-spec` bullet mislabeled its own location ("Step 5's Surface row" when the literal string is actually in Step 3b-surface's example sentence; the Surface table row itself already uses a generic placeholder) | Corrected to name the real location (line 438's example sentence) |
| MEDIUM | Task 1's old Step 7 said "Add a... note to the commit message (Step 7)" — self-referential, meant Step 8/9 | Fixed to reference the actual commit step (now Step 9) |
| MEDIUM | Design §11's testing section didn't mention Tasks 6/7 (quota probing, findings merge) at all, and cited "the real captured output in §5 as a fixture" — §5 has no captured output, only a summary table | Added both tasks to §11; fixture reference corrected to "built from the model ids confirmed live in §5's table" |
| CROSS-DOC | Double mode's SECONDARY slot could still be filled by a same-vendor reviewer: `resolve_ladder_pick`'s same-vendor-fallback pass (needed for `single` mode and the primary slot) also ran for the secondary slot, contradicting design §3's "dropped, not substituted" guarantee | `resolve_ladder_pick` gained an `allow_same_vendor_fallback` parameter, `False` for the secondary-slot call only; new regression test proves a same-vendor-only ladder now drops the secondary instead of duplicating the vendor |
| CROSS-DOC | Design §8's dedup rule ("(severity, exact Location string)") read as the exact same-report-collision bug the second round's `merge_findings` fix exists to avoid | §8 now states the cross-report-only scope explicitly, matching the implementation |
| CROSS-DOC | Design §4 described the source-vendor default as dynamically "the current session's own vendor"; the plan just hardcodes the literal `anthropic` | Both documents now state explicitly that `anthropic` is that abstract default's concrete value, chosen because the orchestrator has no runtime introspection API for its own vendor — not a contradiction, but previously stated inconsistently |

### Fourth review: a third clean-context Opus 5 subagent (native, live)

The third round's fixes were themselves reviewed by a FOURTH clean-context
Opus 5 subagent, run the same way and told explicitly not to trust the
"already fixed" summary. 9 findings, all fixed:

| Severity | Finding | Fix |
|---|---|---|
| CRITICAL | Step 0.7's `--no-cross-ai` path was internally contradictory across two points in the same step — one point said `resolve-reviewers` is never called when cross-AI is disabled, another still described it running | The disabled case now sets `REVIEWER_LIST` directly in-context to the `NO_CONFIG_FALLBACK`-shaped single entry, skips points 3-5 entirely, and goes straight to Step 1 — `resolve-reviewers`/`reviewers.json` are never touched on this path |
| CRITICAL | The plan claimed (four separate locations) that `SEEDS_DIR`'s existing three-candidate pattern "never names an intermediate `SKILL_DIR`" — verified live against the real `skills/review-spec/SKILL.md`, its third candidate DOES reference `$SKILL_DIR`, and nothing anywhere assigns it; a genuine pre-existing bug, not a documentation error on my part | Corrected the false claim at all four locations (plan Architecture/Task 11/Task 10, design §3/§8); Task 11 Step 7 now also fixes the real bug by adding `SKILL_DIR="$(dirname "<path to this SKILL.md>")"` before `SEEDS_DIR`'s loop |
| CRITICAL | Task 1's verification commands used plain `grep -rl`, which also matches gitignored paths (stale worktree copies, `.atl/`, `.superpowers/sdd/*`) — the file counts derived from it were unreliable | Switched every verification command to `git grep -l ... -- "*.py"` / `"*.md"`, scoped to tracked files only; re-verified live, restores the original correct 2-file/17-file counts |
| CRITICAL | The stated rationale for `skills/review-spec/review-spec.py`'s incremental-import discipline (ruff would fail the commit) was wrong — verified live, `.pre-commit-config.yaml`'s ruff hook only covers `tools/`/`tests/`, not `skills/`; meanwhile a REAL ruff violation existed unnoticed: Task 2's test file imported `json` before it was used | Corrected the rationale (the module file isn't ruff-scoped; `tests/test_review_spec.py` is, and that's where the discipline is actually load-bearing); moved the `import json` from Task 2's test-file Step 1 to Task 8's, where it's first used |
| HIGH | Double mode's secondary-slot cross-vendor guarantee silently disappeared whenever the primary resolved to `NO_CONFIG_FALLBACK` (`vendor == ""`) — an empty `skip_vendor` disables `resolve_ladder_pick`'s vendor filter entirely by its own documented contract, so the secondary could land on the same vendor as the document's author with no baseline to compare against | `resolve_reviewers` now computes `secondary_skip_vendor = primary.vendor or source_vendor`, falling back to the document's actual authoring vendor when there's no native baseline; new regression test `test_double_mode_secondary_dropped_when_no_native_entry_and_only_source_vendor_available` |
| HIGH | `render_reviewer_command` raised raw `KeyError`/`AttributeError`/`IndexError` on a `cli`-set config entry with no `command`, or a malformed template — an unhandled traceback mid-dispatch, contradicting the design's "never blocks the whole run" promise; `probe_reviewer_quota`'s early-return also masked the missing-command case as `available: True` | `render_reviewer_command` now raises `ValueError` uniformly (wrapping the format-string failure) or when `command` is missing; `probe_reviewer_quota` only skips probing for truly native (`not resolved.cli`) entries and catches `ValueError` to report `available: False`; the `render-command` CLI subcommand catches `ValueError`, prints to stderr, exits 1 (no `### Status:` line, so the existing fail-closed convention catches it); Task 11 Step 3's orchestrator prose now explains a nonzero `render-command` exit means that slot failed to dispatch, so no report file is written for it and the existing fail-closed rules take over — no new special-casing |
| MEDIUM | `skills/review-spec/SKILL.md`'s `NEVER` rule (line 183) still said "before the reviewer's report is written to its temp file (Step 3)" — stale since the temp-file save was removed in round 2's `EFFECTIVE_REPORT_PATH` fix | Task 11 Step 5 now also rewrites this rule to reference `EFFECTIVE_REPORT_PATH` existing on disk (Step 1.5), not a Step-3 temp file |
| MEDIUM | Task 2's tests (`test_round_trips_through_tomllib`, `test_escapes_quotes_and_backslashes_in_strings`) did unguarded `import tomllib`, which would ImportError on an interpreter below 3.11 even though the module itself degrades gracefully | Both tests now `@unittest.skipIf(rs.tomllib is None, ...)` |
| CROSS-DOC | Design §8 point 3 said quota is refreshed only "for any ladder candidate actually needed this run" — the actual implementation (`probe-quota`'s CLI handler) refreshes every stale key in the FULL `policy.ladder`, since which candidates the walk needs isn't known until quota is already known | Design §8 corrected to describe the real behavior and explain why a narrower "only what's needed" set isn't computable up front |

### Fifth review: a fourth clean-context Opus 5 subagent (native, live)

The fourth round's fixes were themselves reviewed by a FIFTH clean-context
Opus 5 subagent, run the same way. 9 findings, all fixed:

| Severity | Finding | Fix |
|---|---|---|
| CRITICAL | Design §4's rejection of git-trailer-based authorship detection claimed "this repo's commits don't carry such trailers today (verified: `git log` shows none)" — verified live, `git log --format='%b' \| grep -c "Co-Authored-By"` returns 7, including on the three most recent commits | §4's rejection rewritten around the real reasons (a spec under review is frequently uncommitted; a commit trailer names whoever commits, not necessarily the authoring session) rather than the false "no trailers exist" claim |
| CRITICAL | Task 1 Step 4 told the executor to rename "both occurrences" of `reviewing-specs` in `applying-review-feedback/SKILL.md`'s frontmatter description, but the line has exactly one `reviewing-specs` occurrence and one `` `/review-spec` `` mention — the public orchestrator entrypoint, which design §2 says stays unchanged | Step 4 now names the single real occurrence to rename and explicitly calls out `` `/review-spec` `` as untouched |
| CRITICAL | Task 11 Step 7 said the `SEEDS_DIR` block sits "directly above" the `**Loop state file**` line — verified live against `skills/review-spec/SKILL.md`, the Loop state file line is 155 and the `SEEDS_DIR` block is 156–169, i.e. below it | Corrected to "directly below", with the right line range (156–169) |
| HIGH | Task 6's `test_timeout_is_unavailable` uses `subprocess.TimeoutExpired`, but the test file only gains `import subprocess` in a task that doesn't exist yet — Task 4 adds it to the *module*, never to the test file | Task 6 Step 1 now instructs adding `import subprocess` to the test file |
| HIGH | The double-review merge derived its `### Status:` purely from parsed findings — a source report that says "Issues Found" but whose bullet(s) don't match `_BULLET_RE`'s strict one-line shape would silently merge into a false "Approved" | New `report_declares_issues` (Task 7) checks each source report's own Status line directly; `render_merged_report` gained an `any_source_issues` parameter OR'd into its Approved/Issues-Found decision; `merge-reports` (Task 8) now computes and passes it; 2 new regression tests |
| HIGH | Task 9's CLI profiles (the source `review-spec-config` copies `command` templates from) quoted `{prompt}` as `"{prompt}"` in every example — double-quoting once `render_reviewer_command`'s own `shlex.quote` runs — and `codex.md`'s example still ended in `2>/dev/null`, the exact stderr suppression round 3 removed from design §3 | All six profiles rewritten to bare `{model}`/`{prompt}` placeholders with an explanatory note (on the first profile); `2>/dev/null` removed from `codex.md` |
| HIGH | `cache_base`/`cache_runtimes_path`/`cache_quota_path`/`cache_is_stale`/`RUNTIMES_TTL_SECONDS` (Task 3) had no real caller — Task 4/5 don't read the cache, and Task 11/Task 10 hardcoded `~/.cache/ai-kit/review-spec/...` literally, silently ignoring `XDG_CACHE_HOME` and never checking runtimes staleness | New `cache-path` CLI subcommand (Task 8) prints the XDG-aware path for `--kind runtimes\|quota`; new `detect-runtimes --if-stale PATH` flag uses `cache_is_stale`/`RUNTIMES_TTL_SECONDS` to skip re-detection when fresh; Task 11 Step 2 point 0 now resolves `RUNTIMES_JSON`/`QUOTA_JSON` once via `cache-path`, substituted literally like `RUN_TMP_DIR`; Task 10 does the same; 4 new tests |
| MEDIUM | Global Constraints and every task's "Run:" step said `.venv/bin/python3`, contradicting the Architecture paragraph's (correct, verified) claim that the `Makefile`/pre-commit actually run bare system `python3` | All 15 command references switched to bare `python3`, matching the real `Makefile` `test:` target |
| MEDIUM | Task 3 Step 3 told the executor Task 2's test file "only imported `importlib.util`, `json`, `os`, `tempfile`, `unittest`" — verified live, Task 2's actual test code never imports `json` (that's added in Task 8) | Dropped the false `json` claim from the list |
| MEDIUM | Design §3's grok `command` example included a `-p` flag §5's confirmed grok flag list never mentions (`-p` is `claude`'s flag, not grok's) | Removed `-p` from the example, matching Task 9's own grok profile |
| MEDIUM | Design's Scope bullet had a dangling clause ("...a pre-existing bug — so `review-spec-config` — a sibling skill — reaches them the same way") with no antecedent, and referred to itself as "this plan" inside a design spec | Rewritten as complete sentences, "this plan" → "this design" |
| CROSS-DOC | Design §3's double-mode secondary-slot rule ("vendor differs from the baseline's") never covered the case where the baseline is the session-default fallback (`vendor == ""`) — the plan's actual `secondary_skip_vendor = primary.vendor or source_vendor` fix (round 3) has no counterpart in the design text | §3 now states the fallback-to-source-vendor case explicitly |

### Sixth review: a fifth clean-context Opus 5 subagent (native, live)

The fifth round's fixes were themselves reviewed by a SIXTH clean-context
Opus 5 subagent. 6 findings, all fixed:

| Severity | Finding | Fix |
|---|---|---|
| HIGH | The external-CLI reviewer prompt (Task 11 Step 3) dropped `<GROUNDING_DOCS>`, the declared-paths-authoritative rule, and the ARCHETYPE-ceiling rule that the native prompt template carries — verified live against `skills/review-spec/SKILL.md` lines 263–305, the string "GROUNDING" appeared nowhere in either document, so an external reviewer couldn't detect plan/design drift (Step 0.6's whole purpose) and had no instruction suppressing findings about the grounding docs | The external prompt now carries `<GROUNDING_DOCS>` plus its drift-detection guidance, the declared-paths-authoritative rule, and the ARCHETYPE-ceiling rule — mirroring the native template's contract verbatim, with a note pointing at the source |
| HIGH | No profile enforced a read-only constraint for external reviewer dispatch, and `gemini.md`'s template used `--approval-mode yolo` alone — fully-automated write access into the repo under review — contradicting design §1's own "external CLI editing the working tree... out of scope, a different riskier problem" | Every Task 9 profile now records a `read_only:` frontmatter field (`codex`: confirmed via `--sandbox read-only`; `gemini`: partial via a new `--sandbox` flag added to its template, isolating writes to an ephemeral container; `claude`/`opencode`/`grok`/`cursor-agent`: unconfirmed); a new Task 9 intro note and design §5 addition state the posture; Task 10 Step 2 now warns the user when configuring an `unconfirmed` CLI |
| MEDIUM | `parse_findings`/`render_merged_report` silently re-labeled a `### LOW` severity heading as MEDIUM — a real risk since reviewing-specs's Plan checklist defines a LOW/Tooling-Catchable tier a plan-archetype reviewer can legitimately emit, silently escalating severity in the merged report | `_SEVERITY_HEADINGS`/`_SEVERITY_RE` now recognize `LOW` explicitly; `render_merged_report` renders it under its own `### LOW` heading; 2 new regression tests |
| MEDIUM | Several outer ` ```markdown `/backtick blocks in Task 9 (all 6 profiles), Task 10 Step 1, and Task 11 Steps 2/3/4 contained their own nested triple-backtick fences — under CommonMark's fence-matching rules a 3-backtick outer fence closes at the FIRST inner closing marker, corrupting everything after it | Every affected outer fence bumped to 4 backticks (verified with a proper single-active-fence CommonMark trace across the whole file, not just a naive backtick-count parity check) |
| MEDIUM | Task 3/6/8's instructions to add `import time`/`import subprocess`/`import json`+`from unittest import mock` to the ruff-scoped test file never specified sorted position — an out-of-order block fails ruff's `I001`, not just `F401` | Each instruction now states the exact sorted position in the growing import block |
| CROSS-DOC | Design §1 called `--no-cross-ai` "today's exact behavior, unchanged" — but the plan removes `review-spec/SKILL.md`'s hardcoded `sonnet` pin, so the disabled path now inherits the session's own model instead of always running `sonnet` | §1 now scopes the "unchanged" claim to *selection* semantics only, and states explicitly that the model pin removal is a deliberate hardcoded-model-name bugfix applied everywhere, not just on cross-AI paths |

Two non-blocking notes from this round were also applied: design §11's
testing enumeration now lists `report_declares_issues` (previously
omitted), and design §6/the plan's Step 0.7 point 3 now both describe the
`detect-runtimes --if-stale` mechanism consistently (§6 previously still
said plain `--save`).

### Seventh review: a sixth clean-context Opus 5 subagent (native, live)

The sixth round's fixes were themselves reviewed by a SEVENTH clean-context
Opus 5 subagent, which also independently re-verified the fifth round's
4-backtick nested-fence fix holds (it does). 4 findings, all fixed:

| Severity | Finding | Fix |
|---|---|---|
| HIGH | The external-CLI reviewer prompt's `<ABSOLUTE PATH to skills/review-spec-checklist/SKILL.md>` placeholder was never bound by any earlier step — Step 0.7 point 0 only resolved `REVIEW_SPEC_SKILL_DIR`/`TOOLS_PY`/`CLI_PROFILES_DIR`, none of which name the sibling `review-spec-checklist` skill's `SKILL.md`, so the orchestrator had to guess this path at dispatch time for the feature's own headline path | Point 0 now also resolves `CHECKLIST_SKILL_MD="$(dirname "$REVIEW_SPEC_SKILL_DIR")/review-spec-checklist/SKILL.md"` (siblings under the same `skills/` tree in every installed shape, so no separate three-candidate search is needed) and the external prompt references `<CHECKLIST_SKILL_MD (Step 0.7 point 0)>` instead of an unbound guess; design §8 updated to match |
| MEDIUM | `CLI_PROFILES_DIR` was resolved in `review-spec/SKILL.md`'s own Step 0.7 point 0 but nothing there ever reads it — the same "resolved but never consumed" defect class the fifth round flagged for `cache_base`/`cache_runtimes_path` | Dropped from Step 0.7 point 0 entirely (Task 10's `review-spec-config` already resolves its own copy for its own real use, at its own Step 0) |
| MEDIUM | Step 0.7 point 5's `--source-vendor <SOURCE_VENDOR from Step 1's flag parsing>` pointed at the wrong step — once inserted, "Step 1" inside `review-spec/SKILL.md` names `### Step 1 — Dispatch reviewer(s)`, which parses no flags and runs *after* Step 0.7, not the step that actually produced `SOURCE_VENDOR` | Corrected to reference the `## Inputs` section (extended by Task 11 Step 1), the step that actually parses `--source-vendor` |
| CROSS-DOC | Design §6 said the runtimes-detection hint fires "when this call actually did a fresh detection" (covering both missing and stale-refresh cases), while the plan's Task 11 Step 2 point 3 fires it only on a true first-ever save — under the design's reading, a routine 30-day TTL refresh on a fully-configured install would falsely re-print "No cross-AI config saved yet", exactly the nagging the hint exists to prevent | Design §6 narrowed to state the plan's actual condition explicitly: the hint fires only when `runtimes.json` was missing before the call, never on a stale-but-present refresh |

### Eighth review: a seventh clean-context Opus 5 subagent (native, live)

The seventh round's fixes were themselves reviewed by an EIGHTH
clean-context Opus 5 subagent, which re-verified every codebase-grounding
claim in both documents fresh and found **zero CRITICAL findings** for the
first time. 6 findings (1 HIGH cross-doc, 4 MEDIUM, 1 MEDIUM cross-doc),
all fixed:

| Severity | Finding | Fix |
|---|---|---|
| HIGH (CROSS-DOC) | Design §8 point 0 still described resolving `TOOLS_PY`/`CLI_PROFILES_DIR` and never mentioned `CHECKLIST_SKILL_MD` — directly contradicting its own Step 1 bullet, which already claimed `CHECKLIST_SKILL_MD` is "resolved once alongside `TOOLS_PY` in Step 0.7 point 0". The plan's actual Step 0.7 point 0 resolves `TOOLS_PY`/`CHECKLIST_SKILL_MD` (no `CLI_PROFILES_DIR`) — design and plan described two different Step 0.7s | Design §8 point 0 rewritten to match the plan exactly: resolves `TOOLS_PY`/`CHECKLIST_SKILL_MD`, explicitly states `CLI_PROFILES_DIR` is deliberately not resolved there (no consumer in `review-spec/SKILL.md`; `review-spec-config` resolves its own copy) |
| MEDIUM | Design §8 point 3's quota-probe cost bound cited "(§7)" for `QUOTA_TTL_SECONDS`, but §7 is the `review-spec-config` skill section and defines no TTL | Corrected to `(§6)`, the actual Cache section |
| MEDIUM | Plan's Tech Stack line said "Python 3.12 (`.venv`)" — contradicting its own Architecture paragraph and every `Run:` step (all bare `python3`), and giving an executor grounds to drop the `tomllib` guard the plan elsewhere insists on | Rewritten to state the real runtime (bare system `python3`, unpinned; `.python-version` governs only the separate `uv` dev venv) |
| MEDIUM | `cfg_write_toml` was produced (Task 2) but had no production consumer — Task 8's `render-toml` only printed via `cfg_render_toml`, and Task 10 wrote the file itself with the `Write` tool, bypassing it entirely; the same "produced but never consumed" defect class the fifth round flagged for `cache_base`/`cache_runtimes_path` | `render-toml` gained an `--out <path>` flag that calls `cfg_write_toml` directly; Task 10 Step 3 now uses `--out` instead of a separate `Write`-tool write; `cfg_render_toml` also gained support for an optional top-level `strategy` key (previously only prependable by hand, which `--out`'s single-write path couldn't do) — Task 10 Step 2 now asks for `local-only`/`global-merge` and sets it in the JSON config directly; 4 new tests |
| MEDIUM | `render_reviewer_command`'s "never crashes the caller" contract didn't cover a reviewer's `extra` field colliding with the reserved `{model}`/`{prompt}` keyword names — `command.format(model=..., prompt=..., **extra)` raises a `TypeError` on the duplicate keyword, which the existing `except (KeyError, IndexError, ValueError)` doesn't catch | `TypeError` added to the caught exception tuple, wrapped into the same reportable `ValueError`; docstring updated; 1 new regression test |
| MEDIUM (CROSS-DOC) | Design §3 said `--no-cross-ai` "skips the ladder walk and quota probe entirely" and §6's runtimes-detection rule was written as unconditional for every invocation — under that reading a `--no-cross-ai` run could still shell out to `detect-runtimes` and print the first-run hint, contradicting the plan's actual Step 0.7 point 2 (which explicitly skips `detect-runtimes` too) and the "zero detection overhead" property §1 promises | §3 now says `--no-cross-ai` skips "the ladder walk, quota probe, **and runtimes detection/refresh entirely**"; §6 now opens with "(cross-AI active only — `--no-cross-ai` skips this whole step, §3)" |

### Ninth review: an eighth clean-context Opus 5 subagent (native, live)

The eighth round's fixes were themselves reviewed by a NINTH clean-context
Opus 5 subagent, which re-verified every codebase-grounding claim in both
documents fresh. 6 findings (1 CRITICAL, 1 HIGH cross-doc, 4 MEDIUM), all
fixed:

| Severity | Finding | Fix |
|---|---|---|
| CRITICAL | `skills/review-spec-config/SKILL.md`'s own produced content (Task 10 Step 1) never told the agent following it to record `TOOLS_PY`/`CLI_PROFILES_DIR`/`RUNTIMES_JSON` as literal absolute paths across separate `Bash` calls — the exact fresh-shell defect the plan classifies as CRITICAL for the orchestrator (fixed there in Task 11), left unfixed in the shipped setup skill itself. Step 0 assigns the variables in one `bash` block; Step 1 (`detect-runtimes --save "$RUNTIMES_JSON"`) and Step 3 (`render-toml … --out …`) reference them from separate blocks, with a guaranteed `AskUserQuestion` call-boundary (Step 2) in between | Task 10 Step 1's SKILL.md content now includes the same literal-substitution instruction Task 11 gives its own orchestrator, with a `printf` added to Step 0's block so the values are actually capturable |
| HIGH (CROSS-DOC) | Design §7 says `--check-only` means "(no writes)", but the plan's Task 10 Step 1 ran `detect-runtimes --save "$RUNTIMES_JSON"` (persisting the snapshot) BEFORE checking whether `--check-only` was passed — contradicting itself in adjacent sentences, and observably changing future `/review-spec` behavior since `runtimes.json`'s mere existence permanently suppresses the first-run hint (§6) | Task 10 Step 1 restructured: detection now runs without `--save` first (so `--check-only` truly writes nothing and reports-then-stops); the persisting `--save` call only runs in the non-`--check-only` branch |
| MEDIUM | Both the plan's Task 11 Step 2 point 0 and Task 10 Step 0 path-resolution `bash` blocks ended in bare assignments with no output — an agent following the "record these as literal paths" instruction had nothing to actually capture | Both blocks gained a trailing `printf '%s\n' ...` line; the surrounding prose now says "from the trailing `printf`'s stdout" instead of just "record ... as literal absolute paths" |
| MEDIUM | Both documents said `SEEDS_DIR` sits "above"/"just above" Step 0.7 — verified live, `SEEDS_DIR` lives in the `## Constants` section, which follows Step 0.7's insertion point (right after Step 0.6), not precedes it — the same stale-direction defect the fifth round already fixed once elsewhere in this same task (`SEEDS_DIR` "directly above" → "directly below" the Loop state file line) | Both documents corrected to describe `SEEDS_DIR` as being in Constants, below Step 0.7's insertion point |
| MEDIUM | `review-spec/SKILL.md`'s existing `` ```dot `` loop diagram still named a single `"Dispatch reviewer subagent (fresh)"` node feeding straight into `"Parse Status line"` — a single-reviewer flow that no longer matches the real 1–2-dispatch-then-optional-merge-then-read-`EFFECTIVE_REPORT_PATH` flow Task 11 Steps 2–5 build | New Task 11 Step 8 renames the node to `"Dispatch reviewer(s) (fresh)"` and inserts a `"Read EFFECTIVE_REPORT_PATH"` node between it and `"Parse Status line"`, covering both the single- and double-reviewer cases at the diagram's existing level of detail; old Steps 8/9 renumbered to 9/10 |
| MEDIUM | Design §11's testing enumeration never mentioned the CLI entrypoint (`main`, Task 8's `TestMainCli`, 16 tests) or the TOML writer (`cfg_render_toml`/`cfg_write_toml`, Task 2) — the only integration surface between the module and both consuming skills, and the same "produced but not covered in §11" class this document has already corrected twice | §11 gained two new bullets: TOML writer coverage, and CLI-entrypoint coverage naming every subcommand exercised through `main()`'s `argv` parsing |

A ninth review round should confirm this document reaches Approved before execution begins.
