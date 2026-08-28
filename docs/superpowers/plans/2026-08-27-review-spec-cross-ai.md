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
point 0). **This repo already has a skill-local Python precedent** —
`skills/mermaid-audit/scripts/mermaid_style.py` and
`skills/markdown-to-pdf/scripts/markdown_to_pdf.py`, both under a
`scripts/` subdirectory with underscore-safe names. Verified live: both
ARE invoked directly as standalone CLIs from `Bash` by their own skills
(`skills/mermaid-audit/SKILL.md:55` runs `python3 scripts/mermaid_style.py
<target>`; `skills/markdown-to-pdf/SKILL.md:36,65,72` runs `python3
scripts/markdown_to_pdf.py <source.md>` with flags — both have their own
`argparse`/`main()`), and are ALSO plain-`import`ed by their tests
(`tests/test_mermaid_style.py:5-7`'s `sys.path.insert` + `import
mermaid_style`) — the underscore/`scripts/` convention already covers
CLI invocation, not just library use. `review-spec.py` still departs from
it, but for a narrower, real reason: those two scripts are each invoked
only from their *own* skill's instructions, at a fixed relative path
(`scripts/<name>.py`) resolved implicitly against that skill's own
directory. `review-spec.py` is invoked via `Bash` from **two different
skills** (`review-spec/SKILL.md`'s Step 0.7/Step 1 and
`review-spec-config`'s own Step 0/1/3), from whatever `CWD` the
orchestrator happens to be running in — it needs the same explicit
three-candidate absolute-path resolution `SEEDS_DIR` already uses, which
a bare relative `scripts/<name>.py` path can't provide. Keeping the flat,
skill-name-matching layout (rather than moving under a `scripts/`
subdirectory) is a naming choice this plan makes for call-site legibility
at that resolved absolute path, not a technical requirement — an
underscore-named `review_spec.py` in the same flat location would work
identically and avoid `importlib.util.spec_from_file_location` in favor
of a plain `import`, matching `mermaid_style.py`'s test pattern exactly;
this plan keeps the hyphenated name to match the skill directory's own
name (`review-spec`) at the call site, accepting the `importlib.util`
cost in the test module as the trade-off. This deviation is deliberate,
not an oversight: it still mirrors `tools/status-line.py`'s file layout
and testing style — one flat
file, `importlib`-loaded by its test module for the same hyphenated-name
reason `status-line.py`'s own tests already load it that way — and,
matching `status-line.py`'s own precedent exactly, since this
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
hand-rolled TOML writer since there is no stdlib writer and the ai-kit
*runtime* has zero external dependencies (`pyproject.toml`'s own
"runtime is stdlib-only" scoping — the separate dev/lint env already
depends on `pyyaml` transitively via `pre-commit`, but that's a dev-only
dependency, never a runtime one); `json` for cache files), `unittest` (this repo's test runner, not pytest —
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
- Modify: `skills/review-spec-checklist/SKILL.md` (frontmatter `name:` and
  its own self-reference, Step 4)
- Modify: `skills/review-spec-fixer/SKILL.md` (frontmatter `name:` and
  its own self-references, Step 4)
- Modify: `skills/review-spec-checklist/references/frameworks/SCHEMA.md`
  (self-reference, Step 4)
- Modify: `skills/review-spec/SKILL.md` (every reference to the old names)
- Modify: `tests/test_framework_profiles.py`, `tests/test_wizard_pty.py`
  (hardcoded old skill names — Step 5, required before this task's own
  commit gate passes)
- Modify: `README.md`, `skills/review-spec-checklist/evals/orchestrator-integration.md`,
  `skills/review-spec-checklist/evals/test-scenarios.md`,
  `skills/review-spec-fixer/evals/test-scenarios.md`,
  `skills/review-spec/evals/01`–`04-*.md` (Step 6 — name substitution;
  the eval docs also get content updates beyond the substitution that
  depend on Task 11's Step 0.7/`REVIEWER_LIST`/`EFFECTIVE_REPORT_PATH`/
  Step 1.5 design, described there and applied here since Step 6 is
  where these files are touched — see Task 11's Interfaces for the
  reverse-dependency note)
- Test: none new (mechanical rename + grep verification), but Step 5
  modifies two EXISTING test modules (`tests/test_framework_profiles.py`,
  `tests/test_wizard_pty.py`) — not optional, see Step 5

**Interfaces:**
- Produces: the skill names `review-spec-checklist` and `review-spec-fixer`,
  which Task 11's orchestrator changes reference directly.
- Consumes (reverse dependency, Step 6 only): Task 11's Step 0.7/
  `REVIEWER_LIST`/`EFFECTIVE_REPORT_PATH`/Step 1.5 design, needed to write
  the eval-doc content updates Step 6 group 1 makes beyond mechanical
  renaming. This task can be executed before Task 11 exists in the repo
  (the renames/grep-fixes don't need it), but Step 6's eval-content edits
  specifically should be done last, once Task 11's design is settled —
  or, if executed strictly in task order, revisited after Task 11 lands
  to confirm the eval text still matches what actually shipped.

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
  was symlinked"). **Also fix the now-false comment directly above the
  constant** (lines 48–49: "A known skill that must be symlinked on a
  fresh all-ON install (first entry alphabetically, confirmed by
  enumerate_entries against the live repo)") — `applying-review-feedback`
  really is alphabetically first among `skills/` today, but
  `review-spec-fixer` is not (`commit-message` sorts before it); the
  test's behavior doesn't depend on alphabetical order (verified: the
  constant is only used for a symlink-existence assertion), so drop the
  now-false "(first entry alphabetically...)" parenthetical rather than
  re-verifying a new "first" claim: "A known skill that must be
  symlinked on a fresh all-ON install."

**This step cannot be skipped or deferred to Step 6**:
`tests.test_wizard_pty` is both in the `Makefile`'s `test:` target and in
`.pre-commit-config.yaml`'s `unittest-wizard` hook (`uv run python -m
unittest tests.test_wizard_app tests.test_wizard_pty`) — after Step 1's
`git mv`, that test's `_KNOWN_SKILL` constant points at a symlink name
that no longer exists, so the repo's own commit gate fails and Step 9's
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

By the time you run this step's grep (after Steps 1–5), the paths have
already moved and 4 of these 17 are already fixed —
`skills/review-spec/SKILL.md` by Step 3, and the 3 self-references by
Step 4 (`review-spec-checklist/SKILL.md`, `review-spec-fixer/SKILL.md`,
`review-spec-checklist/references/frameworks/SCHEMA.md`) — so what you'll
actually see is **13** post-move `.md` paths, split into two groups:

1. **MUST fix (8 files)** — living documentation and active test
   fixtures, not history:
   - `README.md` lines 28, 29, 34 — **7 tokens across 3 lines, not 3**:
     line 28 has 2 `reviewing-specs` tokens (the row's link text and link
     path); line 29 has 2 `applying-review-feedback` tokens (its own link
     text and path) plus 1 `reviewing-specs` token (in its description,
     "a `reviewing-specs` report"); line 34 (the `review-spec` row's
     description) has 1 `reviewing-specs` and 1 `applying-review-feedback`
     token, both prose mentions, no link tokens (`review-spec` itself is
     unrenamed). Replace every one of the 7 with the new name, per line —
     do not stop after the first substitution on a line.
   - `skills/review-spec/evals/01-superpowers-plan-routes-writing-plans.md`, `02-gsd-plan-routes-native-cmd.md`, `03-generic-doc-direct-edit.md`, `04-ambiguous-detection-fallback.md`
   - `skills/review-spec-checklist/evals/orchestrator-integration.md`, `skills/review-spec-checklist/evals/test-scenarios.md`
   - `skills/review-spec-fixer/evals/test-scenarios.md` — also fix its
     relative fixture path `../../reviewing-specs/evals/fixtures/` →
     `../../review-spec-checklist/evals/fixtures/` (it points at the
     reviewer skill's shared fixtures directory).

   Replace every `reviewing-specs`/`applying-review-feedback` mention in
   these 8 files with the new names, same substitution as Step 3.

   **Beyond the name substitution, five of these files also describe
   orchestrator behavior this plan changes — a rename alone would leave
   them asserting a contract Task 11 deletes:**
   - `skills/review-spec-checklist/evals/orchestrator-integration.md`'s
     "What the user should look for" table has a row: `Reviewer subagent
     dispatched (visible as \`Agent\` tool call) | Yes, with \`model:
     sonnet\`, paths only in prompt`. Task 11 Step 7 removes the hardcoded
     sonnet pin — the reviewer's model now comes from `REVIEWER_LIST`
     (Step 0.7). Change the expected value to: `Yes — native reviewers use
     the model \`REVIEWER_LIST\` resolved (omitted/session-default unless
     \`review-spec.toml\` pins one); external reviewers (if configured) run
     via \`Bash\`, not the \`Agent\` tool; paths only in prompt`. Add a new
     row above it: `Step 0.7 resolves REVIEWER_LIST before the first
     dispatch (1 entry unless review-spec.toml configures cross-AI double
     mode) | Yes — visible as the Bash calls to review-spec.py
     detect-runtimes/probe-quota/resolve-reviewers, before the first
     reviewer Agent/Bash dispatch`, and one more row after it: `Step 1.5
     binds EFFECTIVE_REPORT_PATH every iteration (merging two reports only
     when REVIEWER_LIST has 2 entries) | Yes — Step 2 reads
     EFFECTIVE_REPORT_PATH from disk, never text still in a subagent's
     context`. Its
     "Known patch candidates" section also has a stale bullet — "The
     orchestrator may forget to delete the temp report file after the
     loop. Cleanup section is already explicit" — which describes the
     pre-cross-AI per-file cleanup this plan replaces with a single
     `rm -rf "$RUN_TMP_DIR"`. Update it to: "Cleanup now removes the
     whole `$RUN_TMP_DIR` in one `rm -rf` rather than per-file — verify
     no per-run artifact survives outside that directory."
   - `skills/review-spec/evals/01-superpowers-plan-routes-writing-plans.md`
     and `skills/review-spec/evals/02-gsd-plan-routes-native-cmd.md` each
     have an "Expected behavior" step ("Dispatches reviewer subagent…")
     that predates Step 0.7/`REVIEWER_LIST`/`EFFECTIVE_REPORT_PATH`/
     Step 1.5. Insert a step before it: "Runs Step 0.7 — resolves
     `TOOLS_PY`/`CHECKLIST_SKILL_MD`, `RUN_TMP_DIR`, and `REVIEWER_LIST`
     (1 entry unless `review-spec.toml` configures cross-AI `double`
     mode; in this eval's default no-config state, `REVIEWER_LIST` is the
     single-entry `NO_CONFIG_FALLBACK`)." and append to the existing
     dispatch step: "; report written to
     `$RUN_TMP_DIR/iter<N>-<key>.md`, read as `EFFECTIVE_REPORT_PATH` by
     Step 2 (Step 1.5 runs every iteration to bind that name; its merge
     call itself is skipped here since `REVIEWER_LIST` has only 1
     entry)."
   - `skills/review-spec/evals/03-generic-doc-direct-edit.md`'s step 4
     ("Dispatcher reviewer subagent…") and
     `skills/review-spec/evals/04-ambiguous-detection-fallback.md`'s step
     7 ("Reviewer dispatched with `FRAMEWORK_PROFILE_PATH = none`") get
     the same treatment: insert the Step 0.7/`REVIEWER_LIST` step before
     each, and append the same `$RUN_TMP_DIR`/`EFFECTIVE_REPORT_PATH`/
     Step 1.5 note to each dispatch step, worded identically to the 01/02
     fix above.

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
are stale symlinks now — `tools/setup.py`'s existing `prune_stale` (verified
live, `tools/setup.py:1084-1106`) already detects "ai-kit symlinks whose
repo entry no longer exists" and, **in a headless run**, auto-removes
them and prints a warning before `tools/setup.py` recreates the
`review-spec-checklist`/`review-spec-fixer` symlinks in the same run.
**In an interactive run it only offers to prune** (`ask_yes_no(...,
default=False)`) — answering the default No leaves the two dead
symlinks in place with no further action taken. State both outcomes in
the note: run `tools/setup.py` and either accept the interactive prune
prompt or re-run it headless; no new symlink code needed in this plan
either way.

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

_MODULE_PATH = os.path.join(os.path.dirname(__file__), "..", "skills",
                             "review-spec", "review-spec.py")


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
        # local declared no reviewers, global not consulted
        self.assertEqual(resolved["reviewers"], [])

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
    merged_reviewers = cfg_merge_reviewers(
        global_cfg.get("reviewers", []), local.get("reviewers", [])
    )
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
        self.assertEqual(rs.cache_runtimes_path(env),
                          "/home/u/.cache/ai-kit/review-spec/runtimes.json")
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

Add `import json` and `import time` to
`skills/review-spec/review-spec.py`'s import block at the top (below
`import os`, above the `try: import tomllib` block) — Task 2 only needed
`os`/`tomllib`, this task is the first to need JSON and mtimes.
`cache_read_json`'s return type is written `dict | None` (PEP 604 union
syntax, no `typing` import needed — this repo's ruff config targets
`py312`, which enables `UP007`, so this plan uses `X | None` everywhere
instead of `Optional[X]`). At this point in the plan,
`.pre-commit-config.yaml`'s ruff hook does not yet scope
`skills/review-spec/review-spec.py` at all (Task 8 Step 7 extends it
later) — introducing imports incrementally here is simply good hygiene,
not a lint-gate requirement yet. `tests/test_review_spec.py` **is**
ruff-scoped from the start, though (it's under `tests/`), which is why
the same incremental discipline is load-bearing for that file
specifically (see Task 8 Step 1 for the concrete case this avoids).

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


def cache_read_json(path: str) -> dict | None:
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
    Pure function — the caller (this module's CLI entrypoint) decides
    whether/where to persist this via cache_write_json."""
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
        result = rs.resolve_reviewers(self.config, quota={}, source_vendor="anthropic",
                                       cross_ai=False)
        self.assertEqual(result, [rs.NO_CONFIG_FALLBACK])

    def test_no_config_at_all_falls_back_to_session_default(self):
        config = {"policy": {"mode": "single", "ladder": []}, "reviewers": []}
        result = rs.resolve_reviewers(config, quota={}, source_vendor="anthropic",
                                       cross_ai=True)
        self.assertEqual(result, [rs.NO_CONFIG_FALLBACK])

    def test_single_mode_skips_same_vendor_as_source(self):
        # single mode's whole point is an independent perspective, so the two
        # same-vendor-as-source (anthropic) ladder entries are skipped even
        # though they're earlier in the ladder
        result = rs.resolve_reviewers(self.config, quota={}, source_vendor="anthropic",
                                       cross_ai=True)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].key, "codex-gpt")

    def test_single_mode_falls_through_tiers_when_flagship_lacks_quota(self):
        quota = {"codex-gpt": {"available": False}}
        result = rs.resolve_reviewers(self.config, quota=quota, source_vendor="anthropic",
                                       cross_ai=True)
        # only same-vendor entries left with quota -> the vendor-skip fallback picks
        # the ladder's best surviving entry, which is claude-opus (tier-aware: tried
        # before claude-sonnet because it is earlier in the ladder)
        self.assertEqual(result[0].key, "claude-opus")

    def test_double_mode_primary_is_best_native_entry_tier_aware(self):
        config = dict(self.config)
        config["policy"] = {"mode": "double", "ladder": self.config["policy"]["ladder"]}
        result = rs.resolve_reviewers(config, quota={}, source_vendor="anthropic", cross_ai=True)
        self.assertEqual(len(result), 2)
        # best NATIVE entry (guaranteed baseline), tier-aware
        self.assertEqual(result[0].key, "claude-opus")
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
        # regression for the design spec's "double mode always runs a
        # native baseline, guaranteed" guarantee
        # (docs/superpowers/specs/2026-08-27-review-spec-cross-ai-design.md
        # §3): an external entry ranked ABOVE every native entry in the
        # ladder must never become
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

    def test_double_mode_baseline_falls_back_to_default_when_no_native_entry(self):
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

    def test_double_mode_secondary_dropped_when_no_native_and_only_source_vendor(self):
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

Add `from typing import NamedTuple` to the top import block (`ResolvedReviewer`
below needs it; every `X | None` return type in this module, including
`cache_read_json`'s from Task 3, uses PEP 604 union syntax, no `typing`
import needed for those).

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
    cli: str | None
    command: str | None
    extra: dict


NO_CONFIG_FALLBACK = ResolvedReviewer(key="session-default", model="", vendor="",
                                       cli=None, command=None, extra={})

_KNOWN_REVIEWER_FIELDS = {"key", "model", "vendor", "cli", "command"}


def _reviewer_by_key(reviewers: list, key: str) -> dict | None:
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
                         allow_same_vendor_fallback: bool = True) -> ResolvedReviewer | None:
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
        if entry is None or not _has_quota(quota, key):
            continue
        if skip_vendor and entry.get("vendor") == skip_vendor:
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
    """The full policy decision, including double mode's
    native-baseline guarantee. Returns 1 or 2 ResolvedReviewer entries;
    dispatch mechanics are the caller's concern (review-spec/SKILL.md's
    Step 1), this only decides WHO.

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
        secondary = resolve_ladder_pick(
            reviewers, ladder, skip_vendor=secondary_skip_vendor, quota=quota,
            allow_same_vendor_fallback=False,
        )
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

**Cost bound**: this probe only ever answers a boolean — `available` —
from a real (if trivial) call to each CLI; it does **not** capture
remaining context-window headroom, matching design §6's `quota.json`
shape exactly (a boolean `available` plus `checked_at`, no context-window
field) and §10's edge case ("has quota but the window can't fit the
document"), which the design itself already marks "not implemented by
v1" for the same reason: no CLI profile (Task 9) has a confirmed
mechanism for context-window introspection today (every profile marks it
"unconfirmed syntax — research during implementation"). On cost: each
ladder entry is charged for **at most one** trivial
probe call per `QUOTA_TTL_SECONDS` (1 hour) — `refresh_quota_cache` skips
any entry whose cached `checked_at` is still fresh, regardless of how many
`/review-spec` invocations happen inside that hour.

**Files:**
- Modify: `skills/review-spec/review-spec.py`
- Test: `tests/test_review_spec.py`

**Interfaces:**
- Consumes: `ResolvedReviewer`/`_reviewer_by_key`/`_to_resolved` (Task 5).
  `refresh_quota_cache` itself does no cache I/O — it takes `existing`/
  `ttl_seconds` as plain parameters; Task 8's `probe-quota` subcommand is
  what wires it to `cache_read_json`/`cache_write_json`/`QUOTA_TTL_SECONDS`
  (Task 3).
- Produces: `render_reviewer_command(resolved: ResolvedReviewer, prompt: str) -> str`,
  `probe_reviewer_quota(resolved: ResolvedReviewer, run_fn=subprocess.run) -> dict`,
  `refresh_quota_cache(config: dict, ladder_keys: list, existing: dict, ttl_seconds: int, run_fn=subprocess.run) -> dict`.
  `render_reviewer_command` is also consumed by Task 11's Step 3 (real
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
        cmd = "codex exec -m {model} -c service_tier='\"{service_tier}\"' {prompt}"
        resolved = rs.ResolvedReviewer(key="codex-gpt", model="gpt-5.2", vendor="openai",
                                        cli="codex", command=cmd,
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
                                        cli="codex",
                                        command="codex -m {model} {unknown_field} {prompt}",
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
    references it. Shared by probe_reviewer_quota (below) and
    review-spec/SKILL.md's real dispatch step (via the `render-command`
    CLI subcommand), so probing and dispatching can never drift apart.

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
        raise ValueError(
            f"reviewer {resolved.key!r} has cli={resolved.cli!r} set but no command template"
        )
    try:
        return resolved.command.format(
            model=resolved.model, prompt=shlex.quote(prompt), **resolved.extra
        )
    except (KeyError, IndexError, ValueError, TypeError) as exc:
        raise ValueError(
            f"reviewer {resolved.key!r} has a malformed command template: {exc}"
        ) from exc


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
        # ### LOW heading (review-spec-checklist's LOW/Tooling-Catchable tier);
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
    output template). Used by the merge-reports CLI subcommand to
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
    emit it (review-spec-checklist's Plan checklist defines a LOW/Tooling-
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
    the merge-reports CLI subcommand already filters those out (via
    report_has_status) before this function ever runs. Deliberately
    drops each source report's own
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
    lines.append(
        "### Status: Issues Found — fix and re-invoke" if any_issues else "### Status: Approved"
    )
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
- Modify: `.pre-commit-config.yaml` (add `tests.test_review_spec` to the
  `unittest` hook's entry, so this new suite gates commits like every
  other core suite — without this it only runs under `make test`, never
  under `pre-commit`/`make validate`)
- Test: `tests/test_review_spec.py`

**Interfaces:**
- Consumes: every function from Tasks 2–7.
- Produces: a `main(argv: list) -> int` function and `if __name__ ==
  "__main__": sys.exit(main(sys.argv[1:]))`, with subcommands
  `detect-runtimes` (with `--save <path>` and `--if-stale <path>`),
  `cache-path` (`--kind runtimes|quota` — the XDG-aware path Task 11
  Step 2 point 0 and Task 10 Step 0 both resolve `RUNTIMES_JSON`/
  `QUOTA_JSON` through, rather than hardcoding
  `~/.cache/ai-kit/review-spec/...` literally), `probe-quota`,
  `resolve-reviewers`, `merge-reports` (fails closed — see "Bug fixed
  here" below — via `report_has_status`, Task 7), `render-toml`
  (`--json-config`, `--out <path>`), `render-command` (the orchestrator's
  only way to reach Task 6's `render_reviewer_command` from a `Bash`
  dispatch, since it's Python — see Task 11 Step 3).
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
            code = rs.main(
                ["detect-runtimes"], which_fn=lambda n: None, run_fn=lambda *a, **k: None
            )
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
                code = rs.main(["resolve-reviewers", "--cwd", cwd, "--quota-path", quota_path,
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
            fake_run = mock.Mock(
                return_value=subprocess.CompletedProcess(
                    args=[], returncode=0, stdout="ok", stderr=""
                )
            )
            with mock.patch.object(rs.os, "environ", env):
                code = rs.main(
                    ["probe-quota", "--cwd", cwd, "--quota-path", quota_path], run_fn=fake_run
                )
            self.assertEqual(code, 0)
            written = rs.cache_read_json(quota_path)
            self.assertTrue(written["codex-gpt"]["available"])
            fake_run.assert_called()  # never shells out to a real "echo ok"

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
    p_detect.add_argument(
        "--save", default=None, help="write the snapshot to this path via cache_write_json"
    )
    p_detect.add_argument(
        "--if-stale", default=None, metavar="PATH",
        help=(
            "skip detection entirely (print {} and exit 0) when PATH exists "
            "and is fresher than RUNTIMES_TTL_SECONDS; else detect and --save to PATH"
        ),
    )

    p_quota = sub.add_parser("probe-quota")
    p_quota.add_argument("--cwd", required=True)
    p_quota.add_argument("--quota-path", required=True)

    p_resolve = sub.add_parser("resolve-reviewers")
    p_resolve.add_argument("--cwd", required=True)
    p_resolve.add_argument("--quota-path", required=True)
    p_resolve.add_argument("--source-vendor", default="")
    p_resolve.add_argument("--cross-ai", action="store_true")

    p_merge = sub.add_parser("merge-reports")
    p_merge.add_argument("--doc-paths", required=True)
    p_merge.add_argument("reports", nargs="+", help="key=path/to/report.md")

    p_toml = sub.add_parser("render-toml")
    p_toml.add_argument(
        "--json-config", required=True, help="path to a JSON file shaped like the TOML config"
    )
    p_toml.add_argument(
        "--out", default=None,
        help=(
            "write the rendered TOML to this path via cfg_write_toml (creating parent dirs) "
            "instead of only printing it"
        ),
    )

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
        quota = cache_read_json(args.quota_path) or {}
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
            # surface (its own long-standing rule), so a failed/unreadable
            # external reviewer can never silently merge into a false
            # "### Status: Approved". No new orchestrator special-case needed.
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
            # convention as merge-reports: review-spec/SKILL.md's existing
            # "No Status line -> Surface failure" rule catches this
            # without any new special-casing at the dispatch step.
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

- [ ] **Step 6: Add the new test module to the pre-commit `unittest` hook**

In `.pre-commit-config.yaml`, change the `unittest` hook's `entry`:

```yaml
      - id: unittest
        name: unittest (core)
        entry: python3 -m unittest tests.test_status_line tests.test_setup tests.test_external_segments tests.test_statusline_doctor tests.test_arch
```

to:

```yaml
      - id: unittest
        name: unittest (core)
        entry: python3 -m unittest tests.test_status_line tests.test_setup tests.test_external_segments tests.test_statusline_doctor tests.test_arch tests.test_review_spec
```

`tests/test_review_spec.py` uses only `unittest`/`stdlib` (this plan's own
Global Constraints — stdlib-only, zero new external dependencies —
carries through to its tests too), so it belongs in the bare
`python3` `unittest` hook, not the `uv run`-gated `unittest-wizard` hook —
matching how `skills/review-spec/review-spec.py` itself runs on bare
system `python3` (Task 8's own Interfaces), not the `uv`-managed dev venv.

- [ ] **Step 7: Extend the ruff and py-compile hooks to cover `skills/review-spec/review-spec.py`**

`skills/review-spec/review-spec.py` is a real ~500-line module, but
`.pre-commit-config.yaml`'s `ruff` hook is scoped `^(tools|tests)/.*\.py$`
and its `py-compile` hook `^tools/(status-line|statusline-doctor|setup)\.py$`
— neither covers a file under `skills/`. Extend both `files:` patterns to
also match it:

```yaml
      - id: ruff
        name: ruff
        entry: uv run ruff check
        language: system
        # Scoped to the refactor's modules + tests. skills/ joins the gate later
        # (the "enforce more after the refactor" expansion).
        files: ^(tools|tests)/.*\.py$
        require_serial: true
```

to (widen the existing `(tools|tests)/.*` alternative, add the new file
as a second alternative — **do not drop the trailing `/.*`**, or every
existing file under `tools/`/`tests/` silently stops being linted):

```yaml
      - id: ruff
        name: ruff
        entry: uv run ruff check
        language: system
        # Scoped to the refactor's modules + tests, plus review-spec.py.
        # The rest of skills/ joins the gate later (the "enforce more
        # after the refactor" expansion).
        files: ^((tools|tests)/.*|skills/review-spec/review-spec)\.py$
        require_serial: true
```

and:

```yaml
      - id: py-compile
        name: py-compile
        entry: python3 -m py_compile
        language: system
        files: ^tools/(status-line|statusline-doctor|setup)\.py$
```

to:

```yaml
      - id: py-compile
        name: py-compile
        entry: python3 -m py_compile
        language: system
        files: ^(tools/(status-line|statusline-doctor|setup)|skills/review-spec/review-spec)\.py$
```

Before running ruff, reorder the top import block into the following
(this is the accumulated result of every earlier task's "add import X"
instruction — Task 2's `os`, Task 3's `json`/`time`, Task 4's
`shutil`/`subprocess`, Task 5's `NamedTuple`, Task 6's `shlex`, Task 7's
`re`, Task 8's `sys` — collected here once and sorted per `I001`):

```python
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import time

try:
    import tomllib as _tomllib_impl
    tomllib = _tomllib_impl
except ModuleNotFoundError:        # Python < 3.11 — degrade to env-only config.
    tomllib = None  # type: ignore[assignment]  # stdlib boundary: optional module absent on <3.11

from typing import NamedTuple
```

Run `uv run ruff check skills/review-spec/review-spec.py` and fix
anything else it flags. Two things it will flag beyond import order:
`E501` (line too long) on the module's few lines that run past 100
chars — reflow each to fit, same as any other `E501` fix in this plan —
and the module was otherwise written against this repo's existing `E`
conventions throughout this plan, so beyond those two categories this
should be a no-op. **Deliberately left out of scope**: `pylint`
(`.pre-commit-config.yaml`) and `pyright`/`vulture`
(`pyproject.toml`'s `[tool.pyright] include` / `[tool.vulture] paths`) —
those enforce stricter design thresholds tuned specifically for the
three existing `tools/*.py` files (per this repo's own
`.pre-commit-config.yaml` header: "Enforcement is intentionally LENIENT
during the render refactor... test hook expands to the full suite" —
this plan follows that same phased-expansion precedent rather than
retroactively tuning three more tools' configs for a brand-new module in
the same commit). A future task can extend those once `review-spec.py`
has been live long enough to know what those tools would actually flag.

- [ ] **Step 8: Commit**

```bash
git add skills/review-spec/review-spec.py tests/test_review_spec.py Makefile .pre-commit-config.yaml
git commit -m "feat(review-spec): add CLI entrypoint (detect-runtimes, cache-path, probe-quota, resolve-reviewers, merge-reports, render-toml, render-command); wire cfg_resolve; register with make test and pre-commit"
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
- `gemini`: **partial** — its template adds `--sandbox` (the existing
  `gemini` skill's own flag list documents only "`-s, --sandbox` — Run in
  sandbox mode for isolation"; it does not state that writes are confined
  to an ephemeral container or that they never reach the real working
  tree — that stronger characterization is unverified, consistent with
  this profile's own `status: stub`), combined with `--approval-mode
  yolo` (required for non-interactive dispatch — `default` hangs, per
  that skill).
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

`{model}`/`{prompt}` above are the literal `command`-template
placeholders every reviewer entry's `command` field can reference —
written bare, never wrapped in extra quotes.
`render_reviewer_command` (in `review-spec.py`) applies `shlex.quote` to
`{prompt}` itself before substitution, so a template that adds its own
quotes around `{prompt}` ends up double-quoted. Copy this shape directly
into a `command` field.

Quota/context-window introspection: unconfirmed syntax — research
whether a dedicated Claude usage
subcommand exists; otherwise rely on the same "low-effort call, detect a
usage-limit error" mechanism confirmed for `codex` (`codex.md`, this same
`cli-profiles/` directory).
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
  -c model_reasoning_effort='"{effort}"' \
  -c service_tier='"{service_tier}"' \
  {prompt}
```

`{model}`/`{prompt}` above are the literal config `command` template
placeholders — bare, unquoted (`render_reviewer_command` already
`shlex.quote`s `{prompt}`). `{effort}`/`{service_tier}` are also literal
`command`-template placeholders, but filled from the reviewer entry's own
`extra` table (e.g. `effort = "high"`, `service_tier = "fast"` in
`review-spec.toml`), not from `{model}`/`{prompt}` — `render_reviewer_command`
fills every placeholder the template references via
`resolved.command.format(model=..., prompt=..., **resolved.extra)`, so an
entry that omits `effort`/`service_tier` from its `extra` table and still
references them here fails to render (a config error, surfaced at
dispatch — see `review-spec/SKILL.md`'s reviewer dispatch step). **Do not
append `2>/dev/null`** —
`probe_reviewer_quota` classifies availability from
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
template placeholders, unquoted; `{prompt}` is `shlex.quote`d by
`render_reviewer_command` before substitution, so never wrap it in your
own quotes here.)

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
`--output-format json`). **Never use `--output-format json` or
`--json-schema` here** — `review-spec.py`'s report parsing
(`report_has_status`/`parse_findings`) expects the reviewer output
template's raw markdown (`### Status:`, `### <SEVERITY>` headings,
`- **title** — Location: ...` bullets) as plain text on stdout, not JSON;
a JSON-wrapped response parses as zero findings and can bury the
`### Status:` line inside an escaped string, silently degrading this
reviewer. Omit `--output-format` entirely (its default is plain text) or
pass `--output-format text` explicitly:

```bash
grok -m {model} --output-format text {prompt}
```

(`{model}`/`{prompt}` are bare config `command` template placeholders,
unquoted; `{prompt}` is `shlex.quote`d by `render_reviewer_command`
before substitution, so never wrap it in your own quotes here.)

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
auth/version (possibly a quota source — unconfirmed). **Use
`--output-format text` (or omit the flag), never `json`**:
`review-spec.py`'s report parsing expects the reviewer output template's
raw markdown on stdout, not a JSON wrapper.

```bash
cursor-agent -p {prompt} --output-format text --model {model}
```

(`{model}`/`{prompt}` are bare config `command` template placeholders,
unquoted; `{prompt}` is `shlex.quote`d by `render_reviewer_command`
before substitution, so never wrap it in your own quotes here.)

Not yet verified against a real installation. Verify all of the above with
`cursor-agent --help` before marking this profile `status: confirmed`.
````

- [ ] **Step 6: Write `skills/review-spec/references/cli-profiles/gemini.md`**

````markdown
---
id: gemini
display_name: Gemini CLI
status: stub (carried over from the existing `gemini` skill's documented flags — not installed on the reference machine)
read_only: "partial (--sandbox per the gemini skill's own flag list, 'run in sandbox mode for isolation' — the container/no-write-to-real-tree characterization is unverified)"
detect: "which gemini"
last_verified: 2026-08-27
---

# gemini — reviewer profile (STUB — unverified live on this machine)

Per the existing `gemini` skill (`~/.claude/skills/gemini/SKILL.md`):
model via `-m/--model <MODEL>`; **background/non-interactive runs require
`--approval-mode yolo`** (the `default` approval mode hangs indefinitely in
a non-interactive shell — do not use it here); that skill also documents
`-s`/`--sandbox` as "run in sandbox mode for isolation" (no further detail
on what's isolated) — include it always here regardless, since `yolo`
alone grants unrestricted write access to whatever it runs against and
`--sandbox` is the only mitigation this profile can point to; confirm its
actual isolation scope live before marking this profile `status:
confirmed`.

```bash
gemini -m {model} --sandbox --approval-mode yolo {prompt}
```

(`{model}`/`{prompt}` are bare config `command` template placeholders,
unquoted; `{prompt}` is `shlex.quote`d by `render_reviewer_command`
before substitution, so never wrap it in your own quotes here.)

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
- Modify: `README.md` (add a Contents table row for the new skill)
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
see `review-spec/SKILL.md`'s Step 0.7 point 0 for why).
Resolve them the identical way `review-spec/SKILL.md` itself resolves
these same two paths (its own Step 0.7 point 0) — same three candidates,
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
if [ -f "$TOOLS_PY" ]; then
  RUNTIMES_JSON="$(python3 "$TOOLS_PY" cache-path --kind runtimes)"
fi
printf '%s\n' "$TOOLS_PY" "$CLI_PROFILES_DIR" "$RUNTIMES_JSON"
```

(The third candidate is `review-spec-config`'s own sibling — matching
`SEEDS_DIR`'s own third candidate — since this skill's directory and
`review-spec`'s are installed alongside each other in every shape:
plugin, `~/.claude/skills`, or a direct dev checkout. `cache-path`
resolves the `${XDG_CACHE_HOME:-$HOME/.cache}`-aware path through
`review-spec.py`'s own `cache_runtimes_path` — the same call
`review-spec/SKILL.md` itself uses
— so both skills always agree on where this file lives.)

**Resolve this whole block once, in one `Bash` call, and record
`TOOLS_PY`/`CLI_PROFILES_DIR`/`RUNTIMES_JSON` from its `printf` output as
literal absolute paths — not shell environment variables.** Every `Bash`
tool call in this harness starts a fresh shell, so a variable assigned in
one call is gone by the next; every `$TOOLS_PY`/`$CLI_PROFILES_DIR`/
`$RUNTIMES_JSON` reference in Steps 1–3 below means "the literal path
captured here", substituted directly, exactly the way `review-spec/SKILL.md`'s
own `TOOLS_PY`/`RUN_TMP_DIR` work (its own Step 0.7 points 0/1) — this
skill has its own separate `AskUserQuestion` interaction (Step 2) between
this resolution and Step 3's write, guaranteeing at least one call
boundary in between. If `TOOLS_PY` does not exist at the resolved path,
stop and report: "review-spec's own `review-spec.py` module is missing —
this skill configures cross-AI review for `review-spec`, which must
already be installed."

### Step 1 — Detect

```bash
python3 "$TOOLS_PY" detect-runtimes
```

Parse the printed JSON: for each CLI marked `"installed": true`, note its
path; for `opencode`, note its `models` list.

**If `--check-only` was passed**: report which CLIs are installed. To
also report which already have a `review-spec.toml` reviewer entry,
`Read` the config file directly — `./.aikit/review-spec.toml` if
`--local` was passed, else `~/.config/ai-kit/review-spec.toml` (the same
local/global locations `review-spec` itself resolves) — if it exists,
and note each `[[reviewers]]`
entry's `key`/`cli`. (This is a raw read for reporting only, not
`cfg_resolve`'s local/global merge — `--check-only` is describing what's
on disk, not resolving an effective policy.) If the config has any
`[[reviewers]]` entries, also report **quota availability** — the actual
"standalone availability check" this flag exists to provide — by probing
into a throwaway path that is never persisted anywhere real. This skill
has no `CODEBASE_ROOT` variable of its own (that is a
`review-spec/SKILL.md`-only concept, resolved in that skill's own Step
0.1) — `--cwd` here is just this skill's own current working directory,
the same directory whose `./.aikit/review-spec.toml` Step 0/1 already
read from:
```bash
python3 "$TOOLS_PY" probe-quota --cwd "$(pwd)" --quota-path "$(mktemp)"
```
`probe-quota` has no `--local` flag — internally it always runs
`cfg_resolve`'s local+global merge, so its printed JSON may include keys
from the level the raw read above didn't look at (e.g. a global entry
when `--local` was passed). Report each `key`'s `available` boolean only
for keys that also appeared in the raw-read listing above — drop any
extra key the merge surfaced — so the two parts of this report describe
the same set of reviewers instead of two different ones. This still
makes live probe calls to each configured CLI (the probe itself is a
real trivial invocation, same as at dispatch time), but "no writes" here
means no write to the real `quota.json`/`review-spec.toml` locations —
the temp path this command wrote to is discarded, never reused. Then
stop here — do not persist the runtimes snapshot and do not write
anything else to a real cache/config location, matching this skill's own
`--check-only` contract (frontmatter `description:` above).

**Otherwise**, persist the snapshot before continuing to Step 2:
```bash
python3 "$TOOLS_PY" detect-runtimes --save "$RUNTIMES_JSON"
```
(re-running detection here is cheap and keeps this step's logic linear —
`--save` persists via `cache_write_json`, so `review-spec` doesn't
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
permissions against your working tree." — inform, don't block; the user
is choosing to accept that CLI's default risk.

**Also ask, explicitly — do not skip this**: whether to register one or
more **native** (`cli`-omitted) reviewer entries — e.g. the current
session's own tier, or another Claude tier reachable without an external
CLI. This is not optional to ask: `policy.mode = "double"`'s guaranteed
baseline walks `policy.ladder` restricted to native entries only
(`review-spec.py`'s `_native_ladder` helper), so a config with zero native `[[reviewers]]`
entries can never seat a real native baseline — it always degrades to
`NO_CONFIG_FALLBACK` — silently defeating the goal of preferring the
strongest available Claude tier for anyone who only answered the
per-CLI questions above. For each native entry the user wants, `model`
must be one of the four `Agent`-tool aliases (`sonnet`/`opus`/`haiku`/
`fable`), never a full model id like `"opus-5"`; ask the user to pick one
of those four rather than typing a version string.

Then ask: `policy.mode` (`single` or `double`) and the `policy.ladder`
order (default to the order the user answered the per-CLI and
native-entry questions in, combined, but let them reorder). If `--local`
was passed, also ask whether this
local config should be `local-only` or the default `global-merge` — set
the JSON config's top-level `strategy` key to `"local-only"` if so
(`cfg_render_toml` renders it as a bare `strategy = "..."` line at the
top of the file); omit the key entirely for the default (global
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

- [ ] **Step 2: Register the new skill in `README.md`'s Contents table**

`README.md`'s Contents table (verified live, lines 26-34) is a complete
registry of every directory under `skills/` — Task 1 Step 6 already
updates the two renamed rows, but adds no row for this new skill. Add,
after the `review-spec` row (line 34):

```markdown
| [`review-spec-config`](skills/review-spec-config/SKILL.md) | skill | Interactive setup wizard for `review-spec`'s cross-AI reviewer config — detects installed CLIs/models, asks which to configure, writes `review-spec.toml`. |
```

- [ ] **Step 3: Commit**

```bash
git add skills/review-spec-config/SKILL.md README.md
git commit -m "feat(review-spec-config): add interactive cross-AI reviewer setup skill"
```

---

### Task 11: Orchestrator integration — `review-spec/SKILL.md`

**Files:**
- Modify: `skills/review-spec/SKILL.md`
- Test: none (orchestration prose — validated per spec §11 via manual dry
  run, listed in this task's steps)

**Interfaces:**
- Consumes: `skills/review-spec/review-spec.py`'s `cache-path`,
  `detect-runtimes`, `probe-quota`, `resolve-reviewers`, `render-command`,
  and `merge-reports` subcommands (Task 8), the renamed skills (Task 1).

- [ ] **Step 1: Update the frontmatter `description:`, then add
  `--cross-ai`/`--no-cross-ai`/`--source-vendor` to the Inputs section**

`skills/review-spec/SKILL.md`'s frontmatter `description:` (line 3, after
Task 1 Step 3's name substitution) still describes the orchestrator as
dispatching a single fixed reviewer, with no mention of the new
cross-AI/configurable-reviewer behavior this task adds. Insert one clause
after "Orchestrates a reviewer subagent (`review-spec-checklist`)":
", optionally dispatching one or two reviewers per `review-spec.toml`
(native and/or external CLI, config-driven) via `--cross-ai`/
`--no-cross-ai`". This keeps the description accurate for the trigger
surface an agent sees before ever reading the skill body.

In `skills/review-spec/SKILL.md`'s existing "## Inputs" section, extend
the "Document path(s)" bullet to also parse three optional flags from the
same invocation-arguments string (all three, unlike doc paths, have
defaults — never block on their absence):

```markdown
- **Flags (optional, parsed from the same invocation arguments):**
  `--cross-ai` (default) or `--no-cross-ai` — whether Step 0.7 attempts
  cross-AI reviewer resolution at all. `--source-vendor=<vendor>` (default
  `anthropic`) — the document's authoring vendor, used by Step 0.7's
  ladder walk to prefer an independent perspective. The default is meant
  to mean "the current session's own vendor"; `anthropic` is that
  default's concrete value here specifically because this orchestrator
  has no runtime introspection API telling it what vendor its own model
  actually is — it can only assume the overwhelmingly common case (a
  native Claude Code session). A session pointed at a compatible
  third-party endpoint would make this default wrong, which is exactly
  the escape hatch `--source-vendor` itself exists for — pass the real
  vendor explicitly in that case. This is a
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
   that placement isn't reachable from an installed skill, since
   `tools/setup.py`'s symlinks only cover `agents/commands/skills`, per
   its `CATEGORIES`). Because it's inside `review-spec`'s own skill
   directory, it resolves the same way `SEEDS_DIR` (in the `## Constants`
   section, below this Step 0.7 insertion point) does (three
   candidates: `CLAUDE_PLUGIN_ROOT`/`~/.claude/skills`/
   sibling-of-this-file) — this snippet is **self-contained** and does
   not read any variable assigned elsewhere; it computes its own
   directory inline via `$(dirname ...)`. (`SEEDS_DIR`'s own block below
   assigns `SKILL_DIR="$(dirname "<path to this SKILL.md>")"` immediately
   before its own `for` loop, so its third candidate resolves the same
   way this snippet's does.):
   ```bash
   for d in "${CLAUDE_PLUGIN_ROOT:+$CLAUDE_PLUGIN_ROOT/skills/review-spec}" \
            "$HOME/.claude/skills/review-spec" \
            "$(dirname "<absolute path to THIS SKILL.md>")"; do
     [ -d "$d" ] && { REVIEW_SPEC_SKILL_DIR="$d"; break; }
   done
   TOOLS_PY="$REVIEW_SPEC_SKILL_DIR/review-spec.py"
   CHECKLIST_SKILL_MD="$(dirname "$REVIEW_SPEC_SKILL_DIR")/review-spec-checklist/SKILL.md"
   if [ -f "$TOOLS_PY" ]; then
     RUNTIMES_JSON="$(python3 "$TOOLS_PY" cache-path --kind runtimes)"
     QUOTA_JSON="$(python3 "$TOOLS_PY" cache-path --kind quota)"
   fi
   printf '%s\n' "$TOOLS_PY" "$CHECKLIST_SKILL_MD" "$RUNTIMES_JSON" "$QUOTA_JSON"
   ```
   `CHECKLIST_SKILL_MD` is the path Step 1's external-CLI dispatch tells
   the external reviewer to `Read` — `review-spec-checklist` (the
   reviewer skill) is always installed as
   `review-spec`'s own sibling, since both live under the same `skills/`
   tree in every installed shape (plugin, `~/.claude/skills`, or a dev
   checkout), so deriving it from `$REVIEW_SPEC_SKILL_DIR`'s own parent
   needs no separate three-candidate search. `cache-path`
   resolves `RUNTIMES_JSON`/`QUOTA_JSON` through the module's own
   `cache_runtimes_path`/`cache_quota_path` — the
   `${XDG_CACHE_HOME:-$HOME/.cache}/ai-kit/review-spec/...` formula lives
   in exactly one place, not duplicated as a bash literal here.
   Resolve this whole block once, in one `Bash` call, and — exactly like
   `RUN_TMP_DIR` below — record `TOOLS_PY`/`CHECKLIST_SKILL_MD`/
   `RUNTIMES_JSON`/`QUOTA_JSON` from the trailing `printf`'s stdout (four
   lines, in that order) as literal absolute paths substituted into every
   later command and prose reference; they are **not** shell environment
   variables that survive across separate `Bash` tool calls. If
   `TOOLS_PY` does not exist at the resolved path, treat this
   exactly like `--no-cross-ai` (point 2 below) — cross-AI support isn't
   installed, never block the review over it. If `TOOLS_PY` exists but
   `CHECKLIST_SKILL_MD` does not (a broken/partial install —
   `review-spec-checklist` missing while `review-spec` itself is
   present), still proceed with native dispatch (`cli` absent entries
   need no checklist path), but skip any reviewer entry whose `cli` is
   set: an external CLI can't be told to `Read` a file that doesn't
   exist, so treat that entry the way a config error is treated —
   dropped from `REVIEWER_LIST`, never dispatched, and this iteration
   surfaces via whatever entries remain (or `NO_CONFIG_FALLBACK` if none
   do).
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
   null, "command": null, "extra": {}}]` — `review-spec.py`'s
   `NO_CONFIG_FALLBACK` constant's exact shape. **Do not run
   `resolve-reviewers`, `probe-quota`, or
   `detect-runtimes`, and do not write `$RUN_TMP_DIR/reviewers.json`** —
   points 3–5 below are entirely skipped, not just their side effects;
   this is the "skip it entirely, minimal overhead" case the flag exists
   for. Because this entry's `cli` is always `null`, Step 1's dispatch
   never needs `reviewers.json` for it either (only the external branch
   reads that file), so nothing downstream is left dangling. Go directly
   to Step 1.
3. **Required — check before the call below, not optionally**: the
   `--if-stale` call immediately after this destroys the evidence a
   missing-file check would find (it creates the file), so this order is
   fixed — check first, save second:
   ```bash
   [ -f "$RUNTIMES_JSON" ] || echo "no-runtimes-snapshot-yet"
   ```
   Then refresh the runtimes snapshot if it's missing or older than
   `RUNTIMES_TTL_SECONDS` (~30 days — CLI/model presence rarely changes):
   ```bash
   python3 "$TOOLS_PY" detect-runtimes --if-stale "$RUNTIMES_JSON"
   ```
   `--if-stale` checks `cache_is_stale` itself and no-ops
   (prints `{}`, doesn't touch the file) when the existing snapshot is
   still fresh; when missing or stale it detects and saves in the same
   call, so this is always safe to run. If the check above printed
   `no-runtimes-snapshot-yet` (this was the first-ever save), print one
   line — "No cross-AI config saved yet — run `review-spec-config` so
   this doesn't repeat every invocation." — then continue to step 4
   regardless; do NOT skip reviewer resolution (there's usually no
   `review-spec.toml` yet either, so `resolve-reviewers` in step 5
   degrades to `NO_CONFIG_FALLBACK` on its own — no special-casing needed
   here beyond the detection call and the hint).
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
   above — so `--cross-ai` is always passed here, never conditionally.
   (Do not split this command across a trailing `\` followed by an
   inline `#` comment — that escapes the *space* before the comment, not
   the newline, so the redirect below silently becomes a separate command
   that truncates the file.):
   ```bash
   python3 "$TOOLS_PY" resolve-reviewers \
     --cwd <CODEBASE_ROOT> \
     --quota-path "$QUOTA_JSON" \
     --source-vendor <SOURCE_VENDOR from the "## Inputs" section's flag parsing> \
     --cross-ai \
     > "$RUN_TMP_DIR/reviewers.json"
   ```
   `resolve-reviewers` itself calls `cfg_resolve(cwd, env)`,
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
section's opening — everything from that heading through the existing
"Use the `Agent` tool with these exact parameters:" bullet list —
**stopping before, and NOT including**, the lead-in sentence "Reviewer
prompt template — use VERBATIM, substitute only `<DOC_PATHS>`, ..."
(line 263 in the file as it reads before this task's own Steps 1-2
touch it — those steps insert lines above this point, so re-grep for the
quoted lead-in sentence rather than trusting the line number by the time
you reach this step; the quoted text is the real anchor) — with:

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
    `"opus-5"`); `review-spec-config` is responsible for writing
    exactly one of these four strings for every native reviewer entry, so
    surface anything else as a config error rather than passing it through.
  - `description`: `review-spec iter N reviewer (<key>)`
  - `prompt`: the template below, invoking the `review-spec-checklist` skill
  - After the `Agent` tool returns its report text, write it verbatim to
    `$RUN_TMP_DIR/iter<N>-<key>.md` via the `Write` tool (mirroring the
    external branch below, which redirects `Bash` stdout to the same
    path). Step 1.5's merge reads both reviewers' reports from files
    unconditionally — a native reviewer's report must land on disk exactly
    like an external one's, or `merge-reports` has no file to
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
     ARCHETYPE-ceiling clauses verbatim — see the native reviewer prompt
     template later in this same Step 1 — so an external reviewer works
     from the exact same contract a native one does, not a thinner one.)
  2. Fill the entry's `command` template via the `render-command`
     subcommand, which calls `render_reviewer_command`
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
     `{prompt}` already shell-escaped, per `render_reviewer_command`'s own
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

````

The lead-in sentence ("Reviewer prompt template — use VERBATIM...", line
263 pre-Task-11 — same re-grep caveat as above) and the fenced reviewer
prompt template that follows it in `skills/review-spec/SKILL.md` (for the native case)
both stay unchanged, exactly as they read today — only the section's
opening (replaced above) changes.

- [ ] **Step 4: Add Step 1.5 after the new Step 1**

(Four backticks below — this insertion contains a nested triple-backtick
`bash` fence.)

````markdown
### Step 1.5 — Merge reviewer reports, then bind `EFFECTIVE_REPORT_PATH` (runs every iteration — only the merge call itself is conditional)

**This whole step always runs, in both the 1- and 2-reviewer cases** —
only the `merge-reports` `Bash` call below is conditional on
`REVIEWER_LIST` having 2 entries. Do not skip this step for a
single-reviewer iteration: `EFFECTIVE_REPORT_PATH` is bound here either
way, and Step 2/3a/3b below have no other source for it.

When `REVIEWER_LIST` has 2 entries, run:

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
`EFFECTIVE_REPORT_PATH` directly, unchanged from today's behavior. If
`EFFECTIVE_REPORT_PATH` does not exist on disk at all — the single-mode
case of Step 1's "render-command exits nonzero" dispatch failure, which
deliberately leaves that path unwritten — treat it exactly like a
report that lacks a `### Status:` line: Step 2's existing "No Status
line -> Surface failure" rule applies unchanged, there is no separate
"missing file" case to handle.
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
path). Verified live against the file as it read before this task's own
Steps 1-2 inserted lines above these locations — by the time you reach
this step those line numbers have shifted, so use the `grep` above and
the quoted text below to relocate each one; the numbers are given only
as a cross-check, not the primary way to find them:
- **Line 323** (Step 3): `Save the reviewer's report to a temp file
  (\`/tmp/review-spec-report-iter<N>.md\`) so downstream subagents/skills
  can \`Read\` it.` → `The reviewer's report is already at
  \`EFFECTIVE_REPORT_PATH\` (Step 1.5) — no separate save needed here.`
- **Every `<REPORT_TEMP_PATH>` placeholder that reads this saved report**
  — since Step 3's own save is being removed by the bullet above,
  `<REPORT_TEMP_PATH>` is no longer bound by anything. Verified live,
  there are exactly four occurrences, at four different roles:
  - **Line 360** — Step 3a's (generic fixer) prompt-template Inputs list:
    `Review report: <REPORT_TEMP_PATH>`.
  - **Line 383** — Step 3b-skill's (native-revise) `prompt` substitution
    list: `` substitute `<SKILL_NAME>` ..., `<DOC_PATHS>`,
    `<REPORT_TEMP_PATH>`, `<CODEBASE_ROOT>` ``.
  - **Line 392** — Step 3b-skill's own Inputs list inside that same
    prompt: `Review report (the findings to resolve): <REPORT_TEMP_PATH>`.
  - **Line 430** — Step 3b-cmd's (slash command / backing skill route)
    trailing note when invoking without a `{report_path}` placeholder:
    `` (findings: <REPORT_TEMP_PATH>) ``.

  Rename every one of these four occurrences to `<EFFECTIVE_REPORT_PATH>`,
  bound to the value Step 1.5 (Task 11 Step 4) established — one name for
  the same path throughout the whole skill, not two.
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
missing assignment on its own line, **immediately before** the
`for d in ...` line — NOT inside the loop body, where it would execute
after the candidate list is already expanded and leave `$SKILL_DIR`
empty in the third candidate, reproducing the exact bug this fixes:
```bash
SKILL_DIR="$(dirname "<absolute path to THIS SKILL.md>")"
for d in "${CLAUDE_PLUGIN_ROOT:+$CLAUDE_PLUGIN_ROOT/skills/review-spec-checklist/references/frameworks}" \
```
(the `for d in ...` line itself is already being rewritten by Task 1 Step
3 to the new `review-spec-checklist` name — this just adds the missing
`SKILL_DIR=` line immediately before it, in the same block). This bug
predates this plan, but the new `TOOLS_PY`/`CHECKLIST_SKILL_MD`
resolution (this task's Step 2, point 0, above) is modeled directly on
this exact block, so fixing it here keeps both resolutions genuinely
consistent instead of one working and the other's precedent silently
broken.

Also replace line 153, `**Subagent model for both:** \`sonnet\` (Haiku
misses subtle defects; Opus burns tokens for no extra review-quality
signal)`, with `**Fixer subagent model:** \`sonnet\` (Haiku misses subtle
defects; Opus burns tokens for no extra fix-quality signal — the fixer
stays Claude-only and sonnet-pinned; who edits the document under review
is out of scope for this skill). The reviewer's model is no longer a
Constant at all — it comes from `REVIEWER_LIST` (this skill's own
`Step 0.7`, points 2/5/6), set per-entry.`. (This task's own Step
numbering is separate from `review-spec/SKILL.md`'s internal
`Step 0.7`/`Step N` numbering — the parenthetical above refers to the
latter.) **Verified
live: this line is never touched by any other step in this task**, and
left as-is it directly contradicts Step 3's dispatch rule (the entry's
`model`, omitted only when empty) — two readings of the same skill with
opposite outcomes, and a literal reintroduction of the exact
hardcoded-model anti-pattern this whole plan exists to remove.

- [ ] **Step 8: Update the loop diagram for 1–2 reviewer dispatches and the merge step**

`skills/review-spec/SKILL.md`'s ` ```dot ` loop diagram (the `digraph
review_spec { ... }` block, lines 194–252 — inside the `## Loop` section,
which follows `## Constants` and `## NEVER`, and sits immediately above
`### Step 1 — Dispatch reviewer (every iteration)`)
still names a single `"Dispatch reviewer subagent (fresh)"` node feeding
straight into `"Parse Status line"` — a single-reviewer flow. After Steps
2–5 above, the real flow is 1 or 2 dispatches, then `Step 1.5` (runs every
iteration; only its `merge-reports` call is conditional on 2 reviewers)
binding `EFFECTIVE_REPORT_PATH` — leaving the diagram as-is would ship a
skill whose diagram contradicts its own prose.

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


### Adversarial review history (condensed)

Before execution, this plan and its design spec were reviewed through 17
rounds of adversarial review: an initial pass via an external CLI
(`opencode run -m opencode-go/kimi-k3`), then 16 sequential clean-context
Opus 5 subagent reviews, each one fixing every finding from the prior
round and re-verifying the whole document fresh against the live repo
before the next round dispatched. All findings across all 17 rounds were
fixed and confirmed; per `reviewing-specs`' own re-review convention
("don't carry previously-flagged, now-fixed issues forward"), the
round-by-round finding tables have been condensed here rather than kept
in full — no unresolved issue remains from this history.

Recurring defect classes worth knowing if extending this plan further:

- **Plan-internal references leaking into shipped content.** This plan's
  own "Task N"/"Step M" numbering and cross-references to the design
  spec's `§N` sections repeatedly leaked into text that ships verbatim as
  `skills/review-spec-config/SKILL.md`, `skills/review-spec/SKILL.md`, the
  CLI profile docs, or `skills/review-spec/review-spec.py` itself — none
  resolvable by an agent reading the *installed* artifact. Any future
  edit to a 4-backtick "insert this" block or a `review-spec.py`-destined
  Python block should be checked for this before being trusted.
- **Stale directional claims** ("above"/"below", wrong line numbers,
  wrong `§N`) about where something lives relative to something else —
  always verify against the live file, never assume a prior round's fix
  moved things where a new edit's prose assumes.
- **Step-numbering conflation** between this plan's own `Task N Step M`
  scheme and `review-spec/SKILL.md`'s internal `Step 0.7 point N` scheme.
- **Shell-snippet execution order vs documented guards** — a prose
  paragraph describing a guard ("if X doesn't exist, degrade gracefully")
  doesn't make it true unless the actual shipped `bash` block places the
  guard before the command it protects.
- **Files/Interfaces blocks drifting from what a task's own Steps
  actually do** — verify each task's declared file list and
  Consumes/Produces against its Steps before trusting either.

A subsequent review round should confirm this document reaches Approved
before execution begins.

**Round 17** (a seventeenth clean-context Opus 5 subagent) found 8 more
issues after this history was condensed above: a CRITICAL — the plan's
own Tech Stack paragraph repeated the "zero external dependencies" false
premise the design's equivalent claim had just been fixed to scope to
the runtime, in only one of the two places it appeared — plus a HIGH
(`--check-only` was documented, both in the design and the plan, as
reporting "availability" but never actually probed quota, the one thing
"availability" means per the design's own §6 definition) and 6 MEDIUM
(Task 11's and Task 6's Interfaces blocks didn't match their own Steps;
Task 11 Step 3's replacement-boundary instruction was ambiguous about
whether it included or excluded the SKILL.md line right before the
reviewer prompt template; a test comment had a bare `§3` reference with
no named document; the new `review-spec.py` module had no lint/compile
gate and neither document said so; `review-spec/SKILL.md`'s frontmatter
`description:` was never updated to mention the new cross-AI behavior;
and this Self-review notes section itself, at ~390 lines of resolved
history, was flagged as worth condensing — which prompted collapsing it
into the summary above). All 8 fixed: the Tech Stack line now scopes the
same way the Global Constraints already did; `--check-only` now probes
quota into a throwaway path and reports `available` per entry, with
matching design §6/§7 wording; both Interfaces blocks corrected to match
their Steps; the Step 3 boundary instruction now names the exact line
(263) it stops before, and explicitly preserves it and the fenced
template after it, unchanged; the test comment now names the design
spec's file path; a new Task 8 step extends `ruff`/`py-compile` to cover
`skills/review-spec/review-spec.py`, with `pylint`/`pyright`/`vulture`
explicitly deferred and why; and Task 11 Step 1 now updates the
frontmatter `description:` alongside the Inputs-section flags.

An eighteenth review round should confirm this document reaches Approved
before execution begins.

**Round 18** (an eighteenth clean-context Opus 5 subagent) found 2
CRITICAL, 4 HIGH, 5 MEDIUM, and 1 cross-document issue — the largest set
yet, several introduced by round 17's own fixes. CRITICAL: the new Task
8 ruff-scope regex dropped the `/.*` wildcard, which would have silently
un-scoped all of `tools/`/`tests/` from linting; and `review-spec-config`'s
new `--check-only` quota probe called `--cwd <CODEBASE_ROOT>`, a variable
that skill never defines (it's `review-spec/SKILL.md`-only). HIGH: the
"near-no-op" ruff claim was false (10 real `E501` lines across the
module, plus an unstated final import order); `--quota-path` and
`--quota` named the same flag differently on two subcommands; Task 11's
line-number anchors (e.g. "line 263") go stale once that task's own
earlier steps insert lines above them; and shipped SKILL.md replacement
text in two places referenced this plan's own "design §1" / "(Task 11
Step 6)", unresolvable from the installed file. MEDIUM: the same
`--quota-path`/`--quota` mismatch on `resolve-reviewers`; `--check-only`'s
reported reviewer set (raw file read) could diverge from its probed set
(`cfg_resolve`'s merge); design §11 promised an eval doc for
`review-spec-config` that Task 10 never creates; no documented behavior
when `render-command` fails in single-mode (report file never written);
and Step 0.7's first-run-hint precondition check was phrased as optional
when it must run unconditionally, before `--if-stale` destroys the
missing-file evidence. Cross-document: the mermaid-audit/markdown-to-pdf
skill-local-Python precedent was duplicated at length in both documents.
All 12 fixed: the ruff regex restored to `^((tools|tests)/.*|skills/review-spec/review-spec)\.py$`;
the quota probe now uses `--cwd "$(pwd)"` with an explanatory note, and
its reported set is filtered to the raw-read keys; Task 8 Step 7 now
states the definitive final sorted import block and requires an `E501`
pass, and every over-100-char line in every `review-spec.py`-destined
code block was reflowed; both subcommands now share `--quota-path`;
Task 11's stale line numbers are now explicitly flagged as pre-Task-11,
re-grep-before-trusting, with the actual `grep`/quoted-text anchors
already primary; both leaked self-references were replaced with
self-contained text; design §11 now excludes `review-spec-config` from
the eval-doc claim and adds a manual-dry-run bullet for it instead; a
missing `EFFECTIVE_REPORT_PATH` file is now explicitly documented as
falling through to the existing "No Status line" rule; the first-run
hint check is now unconditional and ordered before the destructive
`--if-stale` call; and the duplicated precedent argument now lives once
in the plan's Architecture section, cited from the design.

A nineteenth review round should confirm this document reaches Approved
before execution begins.
