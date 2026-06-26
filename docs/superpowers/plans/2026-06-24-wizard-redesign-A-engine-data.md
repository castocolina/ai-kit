# Wizard UX Redesign — Plan A: Engine & Data Layer

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Extend the ai-kit status-line renderer defaults and the `setup.py` installer engine so the wizard can source every component, built-in segment, and external/user segment from real discovery — with status-line adoption detection, conditional persistence, and a `WizardContext` the new UI (Plan B) will consume — without touching the wizard UI itself.

**Architecture:** All work lands in the render path's data tables (`tools/status-line.py` SEGMENTS/LAYOUT) and the installer engine (`tools/setup.py`), plus a new inventory data file (`tools/segments_inventory.toml`) and the example segment under `examples/segments/`. The renderer stays pure RENDER-ONLY (its header parser is never extended); the installer side gains self-describing-header parsing, two-source external discovery, an inventory loader, adoption detection, conditional persistence, and an extended `WizardContext`. NO wizard UI / screen / Textual-widget changes happen in Plan A — that is Plan B.

**Tech Stack:** Python 3.12 stdlib for the render path (`python3 -S`, no third-party imports); `uv` + `textual` 8.2.7 are wizard-only (PEP-723 dep in `setup.py`, never imported by the render path); tests are `unittest`; the quality gate is `uv run pre-commit run --all-files` (== `make validate`).

## Global Constraints

- Render path `tools/status-line.py` stays `python3 -S` stdlib-only with NO UI copy (no `description`/`sample`/help strings) and its header parser `core_parse_segment_header` UNCHANGED (still parses only `id`/`line`/`after`/`before`/`start`/`end`/`ttl`/`timeout`).
- `tools/setup.py` `SEGMENT_DEFAULTS` MUST stay mirrored to `tools/status-line.py` `SEGMENTS` (same keys, same default bools); `setup.py` `LAYOUT_DEFAULTS` MUST stay mirrored to `status-line.py` `LAYOUT`. The drift guards `test_setup.TestTomlRead.test_layout_defaults_match_status_line` and `test_setup.TestSegmentDriftRecipe.test_segment_defaults_match_recipe_drift` enforce this.
- Golden render output (`tests/fixtures/golden/expected.txt`) stays byte-identical EXCEPT the intended `alt_*` flip in Task 1; no other task may change golden bytes.
- Inventory default `icon`/`line` MUST mirror renderer defaults exactly: `line` from `status-line.py` `LAYOUT` (the line index where the key appears), `icon` from the `seg_*` inline glyph. An arch test asserts the mirror and fail-closed coverage.
- Module seam: `tools/wizard_app.py` imports NOTHING from `setup.py` or hyphenated modules; it receives engine callables + data via the injected `WizardContext` (defined in `wizard_app.py`, populated by `setup.py`). Plan A only EXTENDS that injection; it adds no `wizard_app -> setup` import.
- Renderer's `_SEG_HEADER_RE` and `setup.py`'s `_SEG_HEADER_RE` regex LITERALS stay byte-identical (`test_setup.TestDiscoverExampleSegments.test_seg_header_regex_literal_matches_renderer` — class at `tests/test_setup.py:377`, method at `:417` — pins `setup._SEG_HEADER_RE.pattern == sl._SEG_HEADER_RE.pattern`). New header keys are parsed by extending the token loop in `setup._parse_segment_header`, NOT by changing the regex.
- Textual 8.2.7 / Python 3.12.
- Gate: `uv run pre-commit run --all-files` (== `make validate`). Run the full unittest suite via `python3 -m unittest <module>` per task.
- Golden regen command (confirmed): `UPDATE_GOLDEN=1 python3 -m unittest tests.test_status_line.TestGoldenOutput.test_matches_golden`.

---

### Task 1: alt_* default flip + golden regen

Flip every `alt_*` segment currently defaulting `True` to `False` in the renderer's `SEGMENTS`, mirror it in `setup.py` `SEGMENT_DEFAULTS`, update the recipe sample comments, regenerate the golden fixture, and prove the golden diff only drops the now-hidden `alt_*` segments. Per the current file the `alt_*` keys defaulting `True` are: `alt_git_worktree`, `alt_time_ago`, `alt_time_clock`, `alt_time_session`, `alt_time_api`. (`alt_cost`, `alt_term_dimensions` are already `False`; `alt_system_memory`, `alt_rate_limits` are renderer-internal alt segments — `alt_rate_limits` defaults `True` today and `alt_system_memory` defaults `True` today, so BOTH also flip to `False`.) Keep all keys present in `LAYOUT` (hide via the flag only).

**Files:**
- Modify: `tools/status-line.py:72-83` (`SEGMENTS` dict) — leave `LAYOUT` (`:111-117`) unchanged.
- Modify: `tools/setup.py:73-81` (`SEGMENT_DEFAULTS` dict).
- Modify: `tools/statusline.toml.sample:26-48` (the `[segments]` comment block default values).
- Modify (regenerate): `tests/fixtures/golden/expected.txt`.
- Test: `tests/test_setup.py` (drift assertion `TestTomlRead.test_current_segments_defaults_on_noop_recipe` + `TestSegmentDriftRecipe.test_segment_defaults_match_recipe_drift`), `tests/test_status_line.py::TestGoldenOutput`.

**Interfaces:**
- Consumes: nothing (first task).
- Produces: the new lean default `SEGMENTS`/`SEGMENT_DEFAULTS` (every `alt_*` key == `False`); the regenerated golden baseline. Downstream tasks rely on `alt_system_memory` being `False` so its rename (Task 3) is golden-safe.

- [ ] **Step 1: Write the failing test** — add a renderer-side assertion that every `alt_*` segment defaults OFF.

In `tests/test_status_line.py`, add at the end of the file:

```python
class TestAltSegmentsDefaultOff(unittest.TestCase):
    def test_every_alt_segment_defaults_off(self):
        for key, val in sl.SEGMENTS.items():
            if key.startswith("alt_"):
                self.assertFalse(val, f"{key} must default OFF (alt_* are opt-in)")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/user-zero/git/personal/ai-kit/.claude/worktrees/wizard-ux-redesign && python3 -m unittest tests.test_status_line.TestAltSegmentsDefaultOff -v`
Expected: FAIL — `alt_git_worktree must default OFF` (assertion error; several `alt_*` are still `True`).

- [ ] **Step 3: Write minimal implementation** — flip the `alt_*` defaults in the renderer.

Replace `tools/status-line.py:72-83` with:

```python
SEGMENTS = {
    # identity line
    "path": True, "git_branch": True, "git_dirty": True, "alt_git_worktree": False,
    "todo": True,
    # model row
    "model": True, "alt_time_ago": False, "alt_time_clock": False, "effort": True,
    "lines": True, "alt_cost": False, "alt_time_session": False, "alt_time_api": False,
    # diagnostics row (alt_term_dimensions is a debug aid — off by default)
    "render_time": True, "slowest": True, "alt_term_dimensions": False,
    "context": True,
    "chat_size": True, "alt_system_memory": False, "alt_rate_limits": False,
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /home/user-zero/git/personal/ai-kit/.claude/worktrees/wizard-ux-redesign && python3 -m unittest tests.test_status_line.TestAltSegmentsDefaultOff -v`
Expected: PASS.

- [ ] **Step 5: Mirror the flip in `setup.py` SEGMENT_DEFAULTS**

Replace `tools/setup.py:73-81` with:

```python
SEGMENT_DEFAULTS = {
    "path": True, "git_branch": True, "git_dirty": True, "alt_git_worktree": False,
    "todo": True,
    "model": True, "alt_time_ago": False, "alt_time_clock": False, "effort": True,
    "lines": True, "alt_cost": False, "alt_time_session": False, "alt_time_api": False,
    "render_time": True, "slowest": True, "alt_term_dimensions": False,
    "context": True,
    "chat_size": True, "alt_system_memory": False, "alt_rate_limits": False,
}
```

- [ ] **Step 6: Update the recipe sample comments** so each commented default matches the new value (the `test_segment_defaults_match_recipe_drift` guard parses these literally).

In `tools/statusline.toml.sample`, change these lines (`:30`, `:36`, `:37`, `:40`, `:47`, `:48`) to read `false`:

```toml
# alt_git_worktree = false   # ⎇ active linked-worktree name (struck ⎇ wt on main)
```
```toml
# alt_time_ago = false       # time since the session's first message
# alt_time_clock = false     # ⏰ current wall-clock time
```
```toml
# alt_time_session = false   # 💬 total session duration
# alt_time_api = false       # 📡 cumulative API response time
```
```toml
# alt_system_memory = false  # 🧮 status-line process memory (RSS)
# alt_rate_limits = false    # ⚡ rate-limit buckets with reset time
```

- [ ] **Step 7: Run the setup drift guards**

Run: `cd /home/user-zero/git/personal/ai-kit/.claude/worktrees/wizard-ux-redesign && python3 -m unittest tests.test_setup.TestTomlRead.test_current_segments_defaults_on_noop_recipe tests.test_setup.TestSegmentDriftRecipe.test_segment_defaults_match_recipe_drift -v`
Expected: PASS (SEGMENT_DEFAULTS keys still cover all segments; every commented recipe default now matches SEGMENT_DEFAULTS).

Note: if the test class name `TestSegmentDriftRecipe` does not exist, the drift test is `test_setup.TestTomlRead.test_segment_defaults_match_recipe_drift` — run that exact node instead. Both are byte-driven against the recipe.

- [ ] **Step 8: Regenerate the golden fixture**

Run: `cd /home/user-zero/git/personal/ai-kit/.claude/worktrees/wizard-ux-redesign && UPDATE_GOLDEN=1 python3 -m unittest tests.test_status_line.TestGoldenOutput.test_matches_golden`
Expected: PASS (the test rewrites `tests/fixtures/golden/expected.txt`).

- [ ] **Step 9: Verify the golden diff drops ONLY the now-hidden alt_* segments**

Run: `cd /home/user-zero/git/personal/ai-kit/.claude/worktrees/wizard-ux-redesign && git diff tests/fixtures/golden/expected.txt`
Expected: the only removed tokens are the `alt_*` glyphs/values now OFF (e.g. `⎇`, `⏰`, `💬`, `📡`, `🧮`, `⚡` and their values); no `path`/`git_branch`/`model`/`context`/`chat_size` output changes. Confirm visually this is the intended lean default, not a regression.

- [ ] **Step 10: Run the full affected suites + gate**

Run: `cd /home/user-zero/git/personal/ai-kit/.claude/worktrees/wizard-ux-redesign && python3 -m unittest tests.test_status_line tests.test_setup`
Expected: PASS.
Run: `cd /home/user-zero/git/personal/ai-kit/.claude/worktrees/wizard-ux-redesign && uv run pre-commit run --all-files`
Expected: PASS.

- [ ] **Step 11: Commit**

```bash
git -C /home/user-zero/git/personal/ai-kit/.claude/worktrees/wizard-ux-redesign add tools/status-line.py tools/setup.py tools/statusline.toml.sample tests/fixtures/golden/expected.txt tests/test_status_line.py
git -C /home/user-zero/git/personal/ai-kit/.claude/worktrees/wizard-ux-redesign commit -m "feat(status-line): default every alt_* segment OFF; regenerate golden to the lean baseline"
```

---

### Task 2: External rename sysmem → system_memory (all-or-nothing)

Rename the bundled external example from `sysmem` to `system_memory` across the whole shipped surface (file, header id, toggle, env, docstring, recipe, setup comment, README, Makefile, tests), then grep-prove no stale `sysmem` remains in shipped code/config/tests.

**Files:**
- Rename: `examples/segments/sysmem` → `examples/segments/system_memory` (git mv).
- Modify: the renamed file's header (`:2` `id=sysmem` → `id=system_memory`) and docstring (`:14-16` disable instructions).
- Modify: `tools/statusline.toml.sample:90-91` (the `examples/segments/sysmem` mention).
- Modify: `tools/setup.py` discovery comment (the `sysmem` reference near `discover_example_segments`).
- Modify: `README.md:306` and `:315`.
- Modify: `Makefile:31` (`tests.test_sysmem_e2e` → `tests.test_system_memory_e2e`).
- Modify: `tests/test_external_segments.py` (all `sysmem` → `system_memory`, env `CC_AI_KIT_SEGMENT_SYSMEM` → `CC_AI_KIT_SEGMENT_SYSTEM_MEMORY`, the `PATH` constant pointing at the example file).
- Modify: `tests/test_setup.py` (the shipped-segment assertions `test_discover_real_examples_dir`, `test_discover_finds_sysmem_pre_checked`, and `TestInstallExampleSegments._BODY`).
- Rename: `tests/test_sysmem_e2e.py` → `tests/test_system_memory_e2e.py`; rename class `TestSysmemInstallE2E` → `TestSystemMemoryInstallE2E` and all internal `sysmem` references.

**Interfaces:**
- Consumes: nothing from Task 1 (independent surface).
- Produces: the bundled external segment now has `id=system_memory`, env `CC_AI_KIT_SEGMENT_SYSTEM_MEMORY`, toggle `segments.system_memory`, file `examples/segments/system_memory`. Task 5/6 build on this renamed file.

- [ ] **Step 1: Write/adjust the failing test** — the shipped-segment assertion now expects `system_memory`.

In `tests/test_setup.py`, change `test_discover_real_examples_dir` (lines ~446-451) to:

```python
    def test_discover_real_examples_dir(self):
        # Integration: the shipped examples/segments/ must expose system_memory.
        repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        found = setup.discover_example_segments(
            os.path.join(repo, "examples", "segments"))
        self.assertIn("system_memory", {e["id"] for e in found})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/user-zero/git/personal/ai-kit/.claude/worktrees/wizard-ux-redesign && python3 -m unittest tests.test_setup.TestDiscoverExampleSegments.test_discover_real_examples_dir -v`
Expected: FAIL — `system_memory` not in `{'sysmem'}` (the file still has `id=sysmem`).

- [ ] **Step 3: Rename the file and update its header + docstring**

```bash
git -C /home/user-zero/git/personal/ai-kit/.claude/worktrees/wizard-ux-redesign mv examples/segments/sysmem examples/segments/system_memory
```

In `examples/segments/system_memory`, change the header line (`:2`) from:
```python
# ai-kit-segment: line=1 after=context id=sysmem ttl=10
```
to:
```python
# ai-kit-segment: line=1 after=context id=system_memory ttl=10
```

And change the docstring disable instructions (`:14-16`) from:
```python
Drop it in ~/.config/ai-kit/segments/ and make it executable. Disable it with
`[segments] sysmem = false` (or CC_AI_KIT_SEGMENT_SYSMEM=0)."""
```
to:
```python
Drop it in ~/.config/ai-kit/segments/ and make it executable. Disable it with
`[segments] system_memory = false` (or CC_AI_KIT_SEGMENT_SYSTEM_MEMORY=0)."""
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /home/user-zero/git/personal/ai-kit/.claude/worktrees/wizard-ux-redesign && python3 -m unittest tests.test_setup.TestDiscoverExampleSegments.test_discover_real_examples_dir -v`
Expected: PASS.

- [ ] **Step 5: Update the recipe sample mention**

In `tools/statusline.toml.sample`, change the `[external]` section text (`:90-91`) from:
```
## [segments] <id> = false (or CC_AI_KIT_SEGMENT_<ID>=0). A ready-to-copy sample
## ships at examples/segments/sysmem (system available memory). Each value below
```
to:
```
## [segments] <id> = false (or CC_AI_KIT_SEGMENT_<ID>=0). A ready-to-copy sample
## ships at examples/segments/system_memory (system available memory). Each value below
```

- [ ] **Step 6: Update the setup.py discovery comment**

Grep for the stale reference and fix it:

Run: `cd /home/user-zero/git/personal/ai-kit/.claude/worktrees/wizard-ux-redesign && grep -n sysmem tools/setup.py`

Replace each matched comment occurrence of `sysmem` with `system_memory` (these are comments only — e.g. "the bundled sysmem example" → "the bundled system_memory example").

- [ ] **Step 7: Update README.md**

In `README.md`, change line ~306:
```
A cross-platform Python reference (system available memory) ships at
`examples/segments/system_memory` — copy it as a starting point.
```
and line ~315:
```
`[segments] system_memory = false`.
```

- [ ] **Step 8: Update Makefile**

In `Makefile:31`, change `tests.test_sysmem_e2e` to `tests.test_system_memory_e2e`:

```make
	python3 -m unittest tests.test_setup tests.test_status_line tests.test_external_segments tests.test_statusline_doctor tests.test_arch tests.test_markdown_to_pdf tests.test_worktree_e2e tests.test_wizard_pty tests.test_system_memory_e2e
```

- [ ] **Step 9: Update test_external_segments.py** — replace every `sysmem` → `system_memory`, the env var, and the example PATH constant.

Run: `cd /home/user-zero/git/personal/ai-kit/.claude/worktrees/wizard-ux-redesign && sed -i 's/CC_AI_KIT_SEGMENT_SYSMEM/CC_AI_KIT_SEGMENT_SYSTEM_MEMORY/g; s/"sysmem"/"system_memory"/g; s|segments", "sysmem"|segments", "system_memory"|g' tests/test_external_segments.py`

Then verify no bare `sysmem` token remains:

Run: `cd /home/user-zero/git/personal/ai-kit/.claude/worktrees/wizard-ux-redesign && grep -n sysmem tests/test_external_segments.py`
Expected: no output. If any line still uses `sysmem` (e.g. inside a longer identifier), edit it by hand to `system_memory`.

- [ ] **Step 10: Update test_setup.py shipped-segment + install fixtures**

In `tests/test_setup.py`, rename `test_discover_finds_sysmem_pre_checked` and its assertion:

```python
    def test_discover_finds_system_memory_pre_checked(self):
        d, _ = self._mk(self._HEADER)
        found = setup.discover_example_segments(d)
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["id"], "system_memory")
        self.assertTrue(found[0]["default_on"])           # offered pre-checked
```

Update the `_HEADER` class constant for this test class and the `TestInstallExampleSegments._BODY` header so `id=system_memory`:

```python
    _BODY = ("#!/usr/bin/env python3\n"
             "# ai-kit-segment: line=1 after=context id=system_memory ttl=10\n"
             "print('hi')\n")
```

Apply the same `id=sysmem` → `id=system_memory` and source filename `sysmem` → `system_memory` change everywhere else in `tests/test_setup.py`:

Run: `cd /home/user-zero/git/personal/ai-kit/.claude/worktrees/wizard-ux-redesign && grep -n sysmem tests/test_setup.py`
Replace each remaining occurrence (ids in headers, the `os.path.join(self.src_dir, "sysmem")` filenames, the install-target assertions) with `system_memory`, then re-grep to confirm zero matches.

- [ ] **Step 11: Rename the E2E test file + its internals**

```bash
git -C /home/user-zero/git/personal/ai-kit/.claude/worktrees/wizard-ux-redesign mv tests/test_sysmem_e2e.py tests/test_system_memory_e2e.py
```

In `tests/test_system_memory_e2e.py`:
- Rename the class `TestSysmemInstallE2E` → `TestSystemMemoryInstallE2E`.
- Change the `tempfile.mkdtemp(prefix="aikit-sysmem-e2e-")` prefix to `aikit-system-memory-e2e-`.
- Change the copy source/target basename `sysmem` → `system_memory`, including `_seg()` which returns `os.path.join(self.home, ".config", "ai-kit", "segments", "system_memory")`.
- Rename methods `test_sysmem_installed_and_executable` → `test_system_memory_installed_and_executable` and `test_sysmem_renders_in_status_line` → `test_system_memory_renders_in_status_line`.
- Keep the render assertions (`self.assertIn("💻", plain)`, `self.assertIn("free", plain)`) — the glyph/output of the script body is unchanged by the rename.

Then verify:

Run: `cd /home/user-zero/git/personal/ai-kit/.claude/worktrees/wizard-ux-redesign && grep -n -i sysmem tests/test_system_memory_e2e.py`
Expected: no output.

- [ ] **Step 12: Grep-prove no stale `sysmem` remains in shipped code/config/tests**

Run: `cd /home/user-zero/git/personal/ai-kit/.claude/worktrees/wizard-ux-redesign && grep -rni sysmem tools/ examples/ tests/ README.md Makefile`
Expected: no output. (Historical `docs/superpowers/**` and `docs/wizard-redesign/prototypes/_protodata.py` are point-in-time records / illustrative fake data — they are NOT in this grep scope and are left alone.)

- [ ] **Step 13: Run the affected suites + gate**

Run: `cd /home/user-zero/git/personal/ai-kit/.claude/worktrees/wizard-ux-redesign && python3 -m unittest tests.test_setup tests.test_external_segments tests.test_system_memory_e2e`
Expected: PASS.
Run: `cd /home/user-zero/git/personal/ai-kit/.claude/worktrees/wizard-ux-redesign && uv run pre-commit run --all-files`
Expected: PASS.

- [ ] **Step 14: Commit**

```bash
git -C /home/user-zero/git/personal/ai-kit/.claude/worktrees/wizard-ux-redesign add -A
git -C /home/user-zero/git/personal/ai-kit/.claude/worktrees/wizard-ux-redesign commit -m "refactor(segments): rename bundled external sysmem -> system_memory across code, config, docs, tests"
```

---

### Task 3: Internal rename alt_system_memory → alt_process_memory (golden-safe)

Rename the renderer's built-in process-RSS segment `alt_system_memory` → `alt_process_memory` (key, LAYOUT entry, `seg_*` function, mirror in `setup.py` and recipe). It defaults OFF after Task 1, so golden output is byte-identical. Set its UI description (used later by the inventory) to "Agent process memory".

**Files:**
- Modify: `tools/status-line.py:82` (SEGMENTS key), `:116` (LAYOUT line-3 entry), `:2267-2271` (the `seg_alt_system_memory` function).
- Modify: `tools/setup.py:80` (SEGMENT_DEFAULTS key) and `:89` (LAYOUT_DEFAULTS line-3 entry).
- Modify: `tools/statusline.toml.sample:47` (the `alt_system_memory` recipe comment) and `:65` (the line-3 `segments = [...]` array).
- Test: `tests/test_status_line.py`, `tests/test_setup.py` (drift guards), `tests/test_arch.py` (segment-signature scan), `tests/test_status_line.py::TestGoldenOutput`.

**Interfaces:**
- Consumes: Task 1's `alt_system_memory == False` default (makes the rename golden-safe).
- Produces: renderer key `alt_process_memory` + builder `seg_alt_process_memory`; mirrored `SEGMENT_DEFAULTS`/`LAYOUT_DEFAULTS`. Task 7's inventory keys on the renamed key.

- [ ] **Step 1: Write the failing test** — assert the new key/function exists and the old is gone.

In `tests/test_status_line.py`, add:

```python
class TestProcessMemoryRename(unittest.TestCase):
    def test_renamed_key_present_old_absent(self):
        self.assertIn("alt_process_memory", sl.SEGMENTS)
        self.assertNotIn("alt_system_memory", sl.SEGMENTS)
        self.assertTrue(hasattr(sl, "seg_alt_process_memory"))
        self.assertFalse(hasattr(sl, "seg_alt_system_memory"))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/user-zero/git/personal/ai-kit/.claude/worktrees/wizard-ux-redesign && python3 -m unittest tests.test_status_line.TestProcessMemoryRename -v`
Expected: FAIL — `alt_process_memory` not in SEGMENTS.

- [ ] **Step 3: Rename in the renderer**

In `tools/status-line.py:82`, change `"alt_system_memory": False` → `"alt_process_memory": False`.

In `tools/status-line.py:115-116` (LAYOUT line-3), change `"alt_system_memory"` → `"alt_process_memory"`:

```python
    Line(30, ["render_time", "slowest", "alt_term_dimensions", "context",
              "chat_size", "alt_process_memory", "alt_rate_limits"]),
```

In `tools/status-line.py:2267-2271`, rename the function (body unchanged — the registry auto-discovers it by the `seg_` suffix):

```python
def seg_alt_process_memory(ctx: "Context", avail: int, theme: "Theme") -> str | None:
    n = probe_rss(ctx)
    if n is None:
        return None
    return util_first_fitting([util_icon("🧮", fmt_bytes(n))], avail)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /home/user-zero/git/personal/ai-kit/.claude/worktrees/wizard-ux-redesign && python3 -m unittest tests.test_status_line.TestProcessMemoryRename -v`
Expected: PASS.

- [ ] **Step 5: Mirror in setup.py**

In `tools/setup.py:80`, change `"alt_system_memory": False` → `"alt_process_memory": False`.
In `tools/setup.py:88-90` (LAYOUT_DEFAULTS line-3), change `"alt_system_memory"` → `"alt_process_memory"`:

```python
    {"min_rows": 30, "segments": ["render_time", "slowest", "alt_term_dimensions",
                                  "context", "chat_size", "alt_process_memory",
                                  "alt_rate_limits"]},
```

- [ ] **Step 6: Update the recipe sample**

In `tools/statusline.toml.sample:47`, change to:
```toml
# alt_process_memory = false # 🧮 agent process memory (RSS)
```
In `tools/statusline.toml.sample:65` (line-3 layout array), change `"alt_system_memory"` → `"alt_process_memory"`:
```toml
# segments = ["render_time", "slowest", "alt_term_dimensions", "context", "chat_size", "alt_process_memory", "alt_rate_limits"]
```

- [ ] **Step 7: Confirm golden is byte-identical (NOT regenerated)**

Run: `cd /home/user-zero/git/personal/ai-kit/.claude/worktrees/wizard-ux-redesign && python3 -m unittest tests.test_status_line.TestGoldenOutput.test_matches_golden -v`
Expected: PASS WITHOUT regen — the segment is OFF so it never rendered in the golden; no fixture change.

Run: `cd /home/user-zero/git/personal/ai-kit/.claude/worktrees/wizard-ux-redesign && git diff --stat tests/fixtures/golden/expected.txt`
Expected: no output (file unchanged).

- [ ] **Step 8: Run drift guards + arch + full suites**

Run: `cd /home/user-zero/git/personal/ai-kit/.claude/worktrees/wizard-ux-redesign && python3 -m unittest tests.test_status_line tests.test_setup tests.test_arch`
Expected: PASS (`test_layout_defaults_match_status_line`, `test_segment_defaults_match_recipe_drift`, and the arch `seg_*` signature scan all still hold).

- [ ] **Step 9: Run the gate**

Run: `cd /home/user-zero/git/personal/ai-kit/.claude/worktrees/wizard-ux-redesign && uv run pre-commit run --all-files`
Expected: PASS.

- [ ] **Step 10: Commit**

```bash
git -C /home/user-zero/git/personal/ai-kit/.claude/worktrees/wizard-ux-redesign add tools/status-line.py tools/setup.py tools/statusline.toml.sample tests/test_status_line.py
git -C /home/user-zero/git/personal/ai-kit/.claude/worktrees/wizard-ux-redesign commit -m "refactor(status-line): rename built-in alt_system_memory -> alt_process_memory (golden-safe; off by default)"
```

---

### Task 4: Self-describing header keys (wizard-side ONLY)

Extend `setup.py`'s `_parse_segment_header` to also surface the OPTIONAL `name`, `description`, `icon`, `sample` keys (the regex literal stays byte-identical; only the token loop changes). Keep the renderer's `core_parse_segment_header` UNCHANGED and add a test asserting the renderer parser ignores those keys. Update `discover_example_segments` to surface `name`/`description`/`icon`/`sample` with fallbacks: id-as-name, blank description, default icon, default/last line.

**Files:**
- Modify: `tools/setup.py:446-461` (`_parse_segment_header`), `:464-489` (`discover_example_segments`).
- Test: `tests/test_setup.py` (extend `TestDiscoverExampleSegments`, `tests/test_setup.py:377`), `tests/test_status_line.py` (renderer-ignores-keys assertion).

**Interfaces:**
- Consumes: nothing new.
- Produces: `setup._parse_segment_header(text) -> dict | None` now MAY contain keys `name`, `description`, `icon`, `sample` (raw strings) in addition to `id`/`line`/`after`/`before`/`timeout`/`ttl`. `setup.discover_example_segments(examples_dir) -> list[dict]` where each dict is `{"id": str, "name": str, "path": str, "default_on": bool, "description": str, "icon": str, "sample": str, "line": int}`. Fallbacks: `name`=id, `description`=`""`, `icon`=`DEFAULT_SEGMENT_ICON` (a module constant `"●"`), `line`=`int(fields["line"])` or `len(LAYOUT_DEFAULTS) - 1` (last line). Task 5 consumes this same dict shape.

- [ ] **Step 1: Write the failing test** — header with all four optional keys, and one with only `id=`.

In `tests/test_setup.py`, add:

```python
class TestSelfDescribingHeader(unittest.TestCase):
    def test_parses_optional_ui_keys(self):
        text = ("#!/usr/bin/env python3\n"
                "# ai-kit-segment: id=demo line=2 icon=💻 name=DemoSeg "
                "description=shows_a_demo sample=42units\n")
        f = setup._parse_segment_header(text)
        self.assertEqual(f["id"], "demo")
        self.assertEqual(f["icon"], "💻")
        self.assertEqual(f["name"], "DemoSeg")
        self.assertEqual(f["description"], "shows_a_demo")
        self.assertEqual(f["sample"], "42units")

    def test_id_only_header_has_no_ui_keys(self):
        f = setup._parse_segment_header("# ai-kit-segment: id=bare\n")
        self.assertEqual(f["id"], "bare")
        self.assertNotIn("name", f)
        self.assertNotIn("description", f)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/user-zero/git/personal/ai-kit/.claude/worktrees/wizard-ux-redesign && python3 -m unittest tests.test_setup.TestSelfDescribingHeader -v`
Expected: FAIL — `KeyError: 'icon'` (current parser keeps every `k=v` token, so this may actually pass for `name`/`icon`... ). NOTE: the current `_parse_segment_header` already retains ALL `k=v` tokens, so `test_parses_optional_ui_keys` may PASS as-is. The real gap is `discover_example_segments` not surfacing these keys (Step 5 test). If Step 2 unexpectedly passes, proceed — the failing test of record is the discovery test in Step 5.

- [ ] **Step 3: Make the wizard-side parser explicit about the UI keys**

`setup._parse_segment_header` already keeps every `k=v` token, but make the contract explicit and documented. Replace `tools/setup.py:446-461` with:

```python
def _parse_segment_header(text):
    """Parse an external segment's `# ai-kit-segment: k=v k=v …` marker line into
    a {key: value} dict. Recognizes the renderer keys (`id`, `line`, `after`,
    `before`, `timeout`, `ttl`) AND the wizard-only OPTIONAL UI keys
    (`name`, `description`, `icon`, `sample`) — the latter are read installer-side
    only; the renderer's parser never sees them (render-path purity). Scans the
    head of the file; returns None when no marker line is present. Bare tokens
    (no `=`) are ignored. This is the single source of truth for the `id` that
    drives the `segments.<id>` toggle."""
    for line in text.splitlines():
        m = _SEG_HEADER_RE.match(line)
        if m:
            fields = {}
            for tok in m.group(1).split():
                if "=" in tok:
                    k, v = tok.split("=", 1)
                    fields[k] = v
            return fields
    return None
```

(The regex `_SEG_HEADER_RE` is UNCHANGED — `test_seg_header_regex_literal_matches_renderer` stays green.)

- [ ] **Step 4: Add a renderer-ignores-keys test**

In `tests/test_status_line.py`, add:

```python
class TestRendererHeaderIgnoresUIKeys(unittest.TestCase):
    def test_core_parser_ignores_name_description_icon_sample(self):
        head = ["# ai-kit-segment: id=x line=1 icon=💻 name=N "
                "description=D sample=S\n"]
        fields = sl.core_parse_segment_header(head)
        self.assertEqual(fields.get("id"), "x")
        self.assertEqual(fields.get("line"), "1")
        for ui_key in ("name", "description", "icon", "sample"):
            self.assertNotIn(ui_key, fields,
                             f"renderer parser must ignore UI key {ui_key}")
```

- [ ] **Step 5: Write the discovery-surfaces-metadata test (the failing test of record)**

In `tests/test_setup.py`, inside the discovery test class (it has a `_mk(header)` helper that writes a temp segment dir), add:

```python
    def test_discover_surfaces_ui_metadata_with_fallbacks(self):
        full = ("#!/usr/bin/env python3\n"
                "# ai-kit-segment: id=full line=1 icon=💻 name=Full "
                "description=desc sample=9G\n")
        d, _ = self._mk(full)
        e = setup.discover_example_segments(d)[0]
        self.assertEqual(e["name"], "Full")
        self.assertEqual(e["description"], "desc")
        self.assertEqual(e["icon"], "💻")
        self.assertEqual(e["sample"], "9G")
        self.assertEqual(e["line"], 1)

    def test_discover_applies_fallbacks_for_id_only(self):
        d, _ = self._mk("# ai-kit-segment: id=bare\n")
        e = setup.discover_example_segments(d)[0]
        self.assertEqual(e["name"], "bare")          # id-as-name
        self.assertEqual(e["description"], "")       # blank
        self.assertEqual(e["icon"], setup.DEFAULT_SEGMENT_ICON)
        self.assertEqual(e["line"], len(setup.LAYOUT_DEFAULTS) - 1)  # last line
```

- [ ] **Step 6: Run discovery tests to verify they fail**

Run: `cd /home/user-zero/git/personal/ai-kit/.claude/worktrees/wizard-ux-redesign && python3 -m unittest tests.test_setup.TestDiscoverExampleSegments.test_discover_surfaces_ui_metadata_with_fallbacks tests.test_setup.TestDiscoverExampleSegments.test_discover_applies_fallbacks_for_id_only -v`
Expected: FAIL — `KeyError: 'name'` / `AttributeError: module 'setup' has no attribute 'DEFAULT_SEGMENT_ICON'`.

(If the discovery test class is named differently, use the class that owns `_mk` — confirm with `grep -n "def _mk" tests/test_setup.py`.)

- [ ] **Step 7: Add the default-icon constant and extend discover_example_segments**

In `tools/setup.py`, add a module constant near `SEGMENT_DEFAULTS` (after `:91`):

```python
# Fallback UI glyph for an external segment whose header omits `icon=`.
DEFAULT_SEGMENT_ICON = "●"
```

Replace `tools/setup.py:464-489` (`discover_example_segments`) with:

```python
def discover_example_segments(examples_dir):
    """Scan `examples_dir` for shippable example external segments, each carrying
    a `# ai-kit-segment: … id=<id> …` header. Returns a list of
    {id, name, path, default_on, description, icon, sample, line} sorted by id.
    `default_on` is always True (every example is OFFERED pre-checked). The UI
    keys come from the OPTIONAL self-describing header (`name`/`description`/
    `icon`/`sample`); missing fields fall back to id-as-name, blank description,
    DEFAULT_SEGMENT_ICON, and the last layout line. Files without the marker or
    without an `id` are skipped; a missing dir yields []."""
    out = []
    try:
        names = sorted(os.listdir(examples_dir))
    except OSError:
        return out
    for name in names:
        path = os.path.join(examples_dir, name)
        if not os.path.isfile(path):
            continue
        try:
            with open(path, encoding="utf-8") as f:
                head = f.read(4096)
        except OSError:
            continue
        fields = _parse_segment_header(head)
        if not fields or "id" not in fields:
            continue
        out.append(_external_entry(fields, name, path, provenance="bundled"))
    return sorted(out, key=lambda e: e["id"])


def _external_entry(fields, filename, path, provenance):
    """Build the wizard-facing external-segment dict from a parsed header, applying
    the self-describing fallbacks (id-as-name, blank description, default icon,
    last layout line). `provenance` is "bundled" or "user"."""
    try:
        line = int(fields["line"]) if "line" in fields else len(LAYOUT_DEFAULTS) - 1
    except (TypeError, ValueError):
        line = len(LAYOUT_DEFAULTS) - 1
    return {
        "id": fields["id"],
        "name": fields.get("name") or fields["id"],
        "path": path,
        "default_on": True,
        "description": fields.get("description", ""),
        "icon": fields.get("icon") or DEFAULT_SEGMENT_ICON,
        "sample": fields.get("sample", ""),
        "line": line,
        "provenance": provenance,
    }
```

(Adding `provenance` here means Task 5 reuses `_external_entry`; the `bundled` default keeps existing callers stable.)

- [ ] **Step 8: Run the new tests + renderer test to verify they pass**

Run: `cd /home/user-zero/git/personal/ai-kit/.claude/worktrees/wizard-ux-redesign && python3 -m unittest tests.test_setup.TestSelfDescribingHeader tests.test_setup.TestDiscoverExampleSegments tests.test_status_line.TestRendererHeaderIgnoresUIKeys -v`
Expected: PASS.

- [ ] **Step 9: Run the regex drift guard + full suites + gate**

Run: `cd /home/user-zero/git/personal/ai-kit/.claude/worktrees/wizard-ux-redesign && python3 -m unittest tests.test_setup tests.test_status_line tests.test_external_segments`
Expected: PASS (`test_seg_header_regex_literal_matches_renderer` still green — regex unchanged).
Run: `cd /home/user-zero/git/personal/ai-kit/.claude/worktrees/wizard-ux-redesign && uv run pre-commit run --all-files`
Expected: PASS.

- [ ] **Step 10: Commit**

```bash
git -C /home/user-zero/git/personal/ai-kit/.claude/worktrees/wizard-ux-redesign add tools/setup.py tests/test_setup.py tests/test_status_line.py
git -C /home/user-zero/git/personal/ai-kit/.claude/worktrees/wizard-ux-redesign commit -m "feat(setup): parse optional self-describing header UI keys (name/description/icon/sample); renderer parser stays unchanged"
```

---

### Task 5: User-dir discovery + provenance

Extend external-segment discovery so the installer finds segments from BOTH the bundled `examples/segments/` AND the user dir `${XDG_CONFIG_HOME:-~/.config}/ai-kit/segments` (the SAME directory the renderer already reads). Tag each with provenance (`bundled`/`user`); dedup by id with USER winning; all default OFF unless `statusline.toml` enables.

**Files:**
- Modify: `tools/setup.py` (add `segments_dir` to `Paths` / `resolve_paths`; add `discover_external_segments(paths)`); reuse `_external_entry` from Task 4.
- Test: `tests/test_setup.py` (new `TestUserSegmentDiscovery` with temp HOME/XDG).

**Interfaces:**
- Consumes: `setup._external_entry(fields, filename, path, provenance)` and `setup.discover_example_segments(examples_dir)` (Task 4).
- Produces: `setup.resolve_paths(env).segments_dir` == `os.path.join(config_dir, "segments")`. `setup.discover_external_segments(paths, examples_dir) -> list[dict]` returning the merged, id-deduped (USER wins), id-sorted list of `_external_entry` dicts (each carrying `provenance` ∈ {"bundled","user"}). Task 10 consumes this.

- [ ] **Step 1: Write the failing test**

In `tests/test_setup.py`, add:

```python
class TestUserSegmentDiscovery(unittest.TestCase):
    def _seg(self, d, fname, header):
        os.makedirs(d, exist_ok=True)
        p = os.path.join(d, fname)
        with open(p, "w", encoding="utf-8") as f:
            f.write(header)
        os.chmod(p, 0o755)
        return p

    def test_segments_dir_resolves_under_config(self):
        paths = setup.resolve_paths({"HOME": "/home/x"})
        self.assertEqual(paths.segments_dir,
                         os.path.join("/home/x", ".config", "ai-kit", "segments"))

    def test_segments_dir_respects_xdg(self):
        paths = setup.resolve_paths({"HOME": "/home/x", "XDG_CONFIG_HOME": "/cfg"})
        self.assertEqual(paths.segments_dir, "/cfg/ai-kit/segments")

    def test_merges_bundled_and_user_tagged_by_provenance(self):
        home = tempfile.mkdtemp(); self.addCleanup(shutil.rmtree, home, ignore_errors=True)
        examples = tempfile.mkdtemp(); self.addCleanup(shutil.rmtree, examples, ignore_errors=True)
        self._seg(examples, "b", "# ai-kit-segment: id=bundled_one line=1\n")
        userdir = os.path.join(home, ".config", "ai-kit", "segments")
        self._seg(userdir, "u", "# ai-kit-segment: id=user_one line=2\n")
        paths = setup.resolve_paths({"HOME": home})
        found = setup.discover_external_segments(paths, examples)
        by_id = {e["id"]: e for e in found}
        self.assertEqual(by_id["bundled_one"]["provenance"], "bundled")
        self.assertEqual(by_id["user_one"]["provenance"], "user")

    def test_user_wins_on_id_collision(self):
        home = tempfile.mkdtemp(); self.addCleanup(shutil.rmtree, home, ignore_errors=True)
        examples = tempfile.mkdtemp(); self.addCleanup(shutil.rmtree, examples, ignore_errors=True)
        self._seg(examples, "dup", "# ai-kit-segment: id=dup name=Bundled line=1\n")
        userdir = os.path.join(home, ".config", "ai-kit", "segments")
        self._seg(userdir, "dup", "# ai-kit-segment: id=dup name=User line=2\n")
        paths = setup.resolve_paths({"HOME": home})
        found = setup.discover_external_segments(paths, examples)
        dup = [e for e in found if e["id"] == "dup"]
        self.assertEqual(len(dup), 1)
        self.assertEqual(dup[0]["provenance"], "user")
        self.assertEqual(dup[0]["name"], "User")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/user-zero/git/personal/ai-kit/.claude/worktrees/wizard-ux-redesign && python3 -m unittest tests.test_setup.TestUserSegmentDiscovery -v`
Expected: FAIL — `AttributeError: 'Paths' object has no attribute 'segments_dir'`.

- [ ] **Step 3: Add `segments_dir` to Paths + resolve_paths**

In `tools/setup.py:40-43`, extend the `Paths` field list:

```python
    "Paths",
    "install_dir claude_dir settings config_dir config_toml sample status_line "
    "statusline_doctor segments_dir",
)
```

In `tools/setup.py:57-66`, add `segments_dir` to the returned `Paths`:

```python
    return Paths(
        install_dir=install_dir,
        claude_dir=claude_dir,
        settings=os.path.join(claude_dir, "settings.json"),
        config_dir=config_dir,
        config_toml=os.path.join(config_dir, "statusline.toml"),
        sample=os.path.join(install_dir, "tools", "statusline.toml.sample"),
        status_line=os.path.join(install_dir, "tools", "status-line.py"),
        statusline_doctor=os.path.join(install_dir, "tools", "statusline-doctor.py"),
        segments_dir=os.path.join(config_dir, "segments"),
    )
```

- [ ] **Step 4: Add discover_external_segments**

In `tools/setup.py`, after `discover_example_segments` / `_external_entry`, add a user-dir scanner and a merge:

```python
def _discover_user_segments(segments_dir):
    """Scan the user dir (the same one the renderer reads) for external segments,
    tagged provenance="user". Same header contract as bundled examples; a missing
    dir yields []."""
    out = []
    try:
        names = sorted(os.listdir(segments_dir))
    except OSError:
        return out
    for name in names:
        path = os.path.join(segments_dir, name)
        if not os.path.isfile(path):
            continue
        try:
            with open(path, encoding="utf-8") as f:
                head = f.read(4096)
        except OSError:
            continue
        fields = _parse_segment_header(head)
        if not fields or "id" not in fields:
            continue
        out.append(_external_entry(fields, name, path, provenance="user"))
    return out


def discover_external_segments(paths, examples_dir):
    """Merge bundled (examples/segments/) and user (paths.segments_dir) external
    segments. Each entry carries provenance ("bundled" | "user"). On an id
    collision the USER entry wins (it shadows the bundled copy the user customized).
    All entries default OFF in the wizard unless statusline.toml enables them.
    Returned list is id-sorted."""
    merged = {}
    for e in discover_example_segments(examples_dir):
        merged[e["id"]] = e
    for e in _discover_user_segments(paths.segments_dir):
        merged[e["id"]] = e        # user overrides bundled
    return sorted(merged.values(), key=lambda e: e["id"])
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd /home/user-zero/git/personal/ai-kit/.claude/worktrees/wizard-ux-redesign && python3 -m unittest tests.test_setup.TestUserSegmentDiscovery -v`
Expected: PASS.

- [ ] **Step 6: Run full setup suite + gate**

Run: `cd /home/user-zero/git/personal/ai-kit/.claude/worktrees/wizard-ux-redesign && python3 -m unittest tests.test_setup`
Expected: PASS (existing `Paths` consumers still work — the new field is appended).
Run: `cd /home/user-zero/git/personal/ai-kit/.claude/worktrees/wizard-ux-redesign && uv run pre-commit run --all-files`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git -C /home/user-zero/git/personal/ai-kit/.claude/worktrees/wizard-ux-redesign add tools/setup.py tests/test_setup.py
git -C /home/user-zero/git/personal/ai-kit/.claude/worktrees/wizard-ux-redesign commit -m "feat(setup): discover external segments from bundled + user dirs with provenance and user-wins dedup"
```

---

### Task 6: system_memory self-describing header (canonical demonstration)

Add the full optional UI header (`name`/`description`/`icon`/`sample`) to the renamed `examples/segments/system_memory` so it is the canonical copy-and-edit example of a self-describing external segment. Test asserts all four parse and surface through discovery.

**Files:**
- Modify: `examples/segments/system_memory:2` (the header line).
- Test: `tests/test_setup.py` (assert the shipped example carries all four keys), `tests/test_system_memory_e2e.py` (render assertion still holds).

**Interfaces:**
- Consumes: `setup._parse_segment_header` / `setup.discover_example_segments` (Task 4), the renamed file (Task 2).
- Produces: the shipped `system_memory` header now contains `name=System memory`-equivalent, `description`, `icon=💻`, `sample`. No new code.

NOTE: header values are whitespace-split tokens (the parser splits `m.group(1).split()`), so a value containing a space would be split. Use underscores or single-word values for the shipped header so each key parses as one token (matching the parser's token model). The wizard renders these raw.

- [ ] **Step 1: Write the failing test**

In `tests/test_setup.py`, add:

```python
class TestSystemMemoryCanonicalHeader(unittest.TestCase):
    def test_shipped_example_is_self_describing(self):
        repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        found = setup.discover_example_segments(
            os.path.join(repo, "examples", "segments"))
        e = next(x for x in found if x["id"] == "system_memory")
        self.assertTrue(e["name"])
        self.assertTrue(e["description"])
        self.assertEqual(e["icon"], "💻")
        self.assertTrue(e["sample"])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/user-zero/git/personal/ai-kit/.claude/worktrees/wizard-ux-redesign && python3 -m unittest tests.test_setup.TestSystemMemoryCanonicalHeader -v`
Expected: FAIL — `description` is `""` (header has no UI keys yet) so `assertTrue(e["description"])` fails.

- [ ] **Step 3: Add the full self-describing header**

In `examples/segments/system_memory:2`, replace:
```python
# ai-kit-segment: line=1 after=context id=system_memory ttl=10
```
with:
```python
# ai-kit-segment: line=1 after=context id=system_memory ttl=10 name=system_memory icon=💻 description=System_available_RAM sample=12.0_GiB_free
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /home/user-zero/git/personal/ai-kit/.claude/worktrees/wizard-ux-redesign && python3 -m unittest tests.test_setup.TestSystemMemoryCanonicalHeader -v`
Expected: PASS.

- [ ] **Step 5: Verify the renderer still ignores the new keys and the E2E render holds**

Run: `cd /home/user-zero/git/personal/ai-kit/.claude/worktrees/wizard-ux-redesign && python3 -m unittest tests.test_external_segments tests.test_system_memory_e2e`
Expected: PASS — the renderer's `core_parse_segment_header` still reads only `id`/`line`/`after`/`ttl` from this header; the extra tokens are ignored; the segment still renders `💻 … free`.

- [ ] **Step 6: Run the gate**

Run: `cd /home/user-zero/git/personal/ai-kit/.claude/worktrees/wizard-ux-redesign && uv run pre-commit run --all-files`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git -C /home/user-zero/git/personal/ai-kit/.claude/worktrees/wizard-ux-redesign add examples/segments/system_memory tests/test_setup.py
git -C /home/user-zero/git/personal/ai-kit/.claude/worktrees/wizard-ux-redesign commit -m "docs(segments): make system_memory the canonical self-describing external segment (name/description/icon/sample)"
```

---

### Task 7: Segment inventory file + loader + arch test

Create `tools/segments_inventory.toml` with one `[<key>]` entry per built-in `SEGMENTS` key (UI `description`, static `sample`, `icon` mirroring the `seg_*` glyph, `line` mirroring the LAYOUT line index). Add `load_segment_inventory(path)` in `setup.py`. Add `tests/test_arch.py` assertions: (a) coverage — every `SEGMENTS` key has an inventory entry (fail-closed); (b) line-mirror — inventory `line` == the LAYOUT line index; (c) icon-mirror — inventory `icon` == a reviewed test-local `EXPECTED_ICONS` dict. External segments are NOT in the inventory.

Icon-per-segment glyphs (from the `seg_*` functions — segments with NO icon use the empty string `""`):

| key | icon |
|---|---|
| path | `""` |
| git_branch | `🌿` |
| git_dirty | `""` (conditional `✗`/`~`; no static icon) |
| alt_git_worktree | `⎇` |
| todo | `📝` |
| model | `""` |
| alt_time_ago | `""` |
| alt_time_clock | `⏰` |
| effort | `🧠` |
| lines | `📃` |
| alt_cost | `🪙` |
| alt_time_session | `💬` |
| alt_time_api | `📡` |
| render_time | `⏱` |
| slowest | `🐌` |
| alt_term_dimensions | `""` |
| context | `📊` |
| chat_size | `💾` |
| alt_process_memory | `🧮` |
| alt_rate_limits | `⚡` |

LAYOUT line index (0-based) per key: line 0 = `path, git_branch, alt_git_worktree, git_dirty, todo`; line 1 = `model, alt_time_ago, alt_time_clock, effort, lines, alt_cost, alt_time_session, alt_time_api`; line 2 = `render_time, slowest, alt_term_dimensions, context, chat_size, alt_process_memory, alt_rate_limits`.

**Files:**
- Create: `tools/segments_inventory.toml`.
- Modify: `tools/setup.py` (add `load_segment_inventory(path)` and an `INVENTORY_PATH` resolver).
- Test: `tests/test_arch.py` (coverage + line-mirror + icon-mirror), `tests/test_setup.py` (loader round-trip).

**Interfaces:**
- Consumes: renderer `SEGMENTS`/`LAYOUT` (Tasks 1+3), `setup.SEGMENT_DEFAULTS`/`LAYOUT_DEFAULTS`.
- Produces: `tools/segments_inventory.toml`; `setup.load_segment_inventory(path) -> dict[str, dict]` where each value is `{"description": str, "sample": str, "icon": str, "line": int}`. `setup.INVENTORY_PATH` (absolute path to the shipped file). Task 10 consumes the loader.

- [ ] **Step 1: Write the failing arch tests**

In `tests/test_arch.py`, add (the file already loads `status-line.py` via `_parse`/import helpers; load it executably here to read `SEGMENTS`/`LAYOUT`):

```python
class TestSegmentInventory(unittest.TestCase):
    # Reviewed mirror of the seg_* inline glyphs; "" means no static icon.
    EXPECTED_ICONS = {
        "path": "", "git_branch": "🌿", "git_dirty": "", "alt_git_worktree": "⎇",
        "todo": "📝", "model": "", "alt_time_ago": "", "alt_time_clock": "⏰",
        "effort": "🧠", "lines": "📃", "alt_cost": "🪙", "alt_time_session": "💬",
        "alt_time_api": "📡", "render_time": "⏱", "slowest": "🐌",
        "alt_term_dimensions": "", "context": "📊", "chat_size": "💾",
        "alt_process_memory": "🧮", "alt_rate_limits": "⚡",
    }
    # Icon single-sourcing into the inventory is DEFERRED per the PRD; until then
    # the inventory icon is hand-mirrored and this test pins it to the reviewed map.

    def _sl(self):
        import importlib.util
        sl_path = os.path.join(_TOOLS, "status-line.py")
        spec = importlib.util.spec_from_file_location("status_line_inv", sl_path)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = mod
        spec.loader.exec_module(mod)
        return mod

    def _line_index(self, sl, key):
        for i, ln in enumerate(sl.LAYOUT):
            if key in ln.segments:
                return i
        raise AssertionError(f"{key} not in LAYOUT")

    def test_coverage_every_segment_has_entry(self):
        sl = self._sl()
        inv = setup.load_segment_inventory(setup.INVENTORY_PATH)
        for key in sl.SEGMENTS:
            self.assertIn(key, inv, f"SEGMENTS key {key} missing from inventory")

    def test_line_mirror(self):
        sl = self._sl()
        inv = setup.load_segment_inventory(setup.INVENTORY_PATH)
        for key in sl.SEGMENTS:
            self.assertEqual(inv[key]["line"], self._line_index(sl, key),
                             f"{key} inventory line != LAYOUT line")

    def test_icon_mirror(self):
        inv = setup.load_segment_inventory(setup.INVENTORY_PATH)
        for key, icon in self.EXPECTED_ICONS.items():
            self.assertEqual(inv[key]["icon"], icon,
                             f"{key} inventory icon != reviewed glyph")
```

(If `_TOOLS`/`setup`/`sys`/`os` are not already imported at the top of `tests/test_arch.py`, add `import os, sys` and the `setup`/`_TOOLS` setup the other tests use — confirm with `grep -n "_TOOLS\|import setup" tests/test_arch.py`.)

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/user-zero/git/personal/ai-kit/.claude/worktrees/wizard-ux-redesign && python3 -m unittest tests.test_arch.TestSegmentInventory -v`
Expected: FAIL — `AttributeError: module 'setup' has no attribute 'load_segment_inventory'`.

- [ ] **Step 3: Create the inventory file**

Create `tools/segments_inventory.toml` (descriptions are UI copy; samples are static; icon mirrors the glyph; line mirrors the LAYOUT index):

```toml
# Segment inventory — UI metadata for built-in status-line segments.
# Read by the installer/wizard ONLY (never by the render path). The renderer keeps
# its own icon/line defaults; THIS file's icon/line MUST mirror them exactly
# (arch test enforces it). `description` + `sample` are the SOLE source for UI copy.
# External/user segments are NOT listed here — they self-describe via their header.

[path]
description = "Working directory, ~-relative"
sample = "~/proj"
icon = ""
line = 0

[git_branch]
description = "Current git branch"
sample = "main"
icon = "🌿"
line = 0

[git_dirty]
description = "Working-tree dirty marker"
sample = "~"
icon = ""
line = 0

[alt_git_worktree]
description = "Active linked-worktree name"
sample = "wt-feature"
icon = "⎇"
line = 0

[todo]
description = "Current TODO (in-progress / pending)"
sample = "write tests"
icon = "📝"
line = 0

[model]
description = "Active model name"
sample = "Opus"
icon = ""
line = 1

[alt_time_ago]
description = "Time since the session's first message"
sample = "12m ago"
icon = ""
line = 1

[alt_time_clock]
description = "Current wall-clock time"
sample = "14:30"
icon = "⏰"
line = 1

[effort]
description = "Reasoning-effort ladder + level"
sample = "high"
icon = "🧠"
line = 1

[lines]
description = "Lines added / removed this session"
sample = "+12 -3"
icon = "📃"
line = 1

[alt_cost]
description = "Session cost in USD"
sample = "$0.50"
icon = "🪙"
line = 1

[alt_time_session]
description = "Total session duration"
sample = "1h 04m"
icon = "💬"
line = 1

[alt_time_api]
description = "Cumulative API response time"
sample = "42s"
icon = "📡"
line = 1

[render_time]
description = "Status line's own render time"
sample = "18ms"
icon = "⏱"
line = 2

[slowest]
description = "Slowest single segment this render"
sample = "git 9ms"
icon = "🐌"
line = 2

[alt_term_dimensions]
description = "Terminal size (cols×lines)"
sample = "120×40"
icon = ""
line = 2

[context]
description = "Context-window % used (and max)"
sample = "32%"
icon = "📊"
line = 2

[chat_size]
description = "Transcript file size on disk"
sample = "305k"
icon = "💾"
line = 2

[alt_process_memory]
description = "Agent process memory (RSS)"
sample = "428M"
icon = "🧮"
line = 2

[alt_rate_limits]
description = "Rate-limit buckets with reset time"
sample = "80% 3h"
icon = "⚡"
line = 2
```

- [ ] **Step 4: Add the loader + INVENTORY_PATH to setup.py**

In `tools/setup.py`, near `DEFAULT_SEGMENT_ICON`, add:

```python
INVENTORY_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "segments_inventory.toml")


def load_segment_inventory(path):
    """Load the built-in segment UI inventory (description/sample/icon/line) keyed
    by segment name. Installer/wizard-only metadata; never read by the render path.
    Returns {key: {"description": str, "sample": str, "icon": str, "line": int}}.
    A missing/malformed file yields {} (fail-closed coverage is asserted by the
    arch test, not here)."""
    data = read_toml(path)
    inv = {}
    for key, val in data.items():
        if not isinstance(val, dict):
            continue
        inv[key] = {
            "description": str(val.get("description", "")),
            "sample": str(val.get("sample", "")),
            "icon": str(val.get("icon", "")),
            "line": int(val.get("line", 0)),
        }
    return inv
```

- [ ] **Step 5: Run the arch tests to verify they pass**

Run: `cd /home/user-zero/git/personal/ai-kit/.claude/worktrees/wizard-ux-redesign && python3 -m unittest tests.test_arch.TestSegmentInventory -v`
Expected: PASS (coverage, line-mirror, icon-mirror all hold).

- [ ] **Step 6: Add a loader round-trip test in test_setup.py**

In `tests/test_setup.py`, add:

```python
class TestSegmentInventoryLoader(unittest.TestCase):
    def test_loads_shipped_inventory_shape(self):
        inv = setup.load_segment_inventory(setup.INVENTORY_PATH)
        self.assertIn("path", inv)
        entry = inv["alt_process_memory"]
        self.assertEqual(entry["icon"], "🧮")
        self.assertEqual(entry["line"], 2)
        self.assertEqual(set(entry), {"description", "sample", "icon", "line"})

    def test_missing_file_yields_empty(self):
        self.assertEqual(setup.load_segment_inventory("/no/such/inv.toml"), {})
```

- [ ] **Step 7: Run loader test + full arch/setup suites + gate**

Run: `cd /home/user-zero/git/personal/ai-kit/.claude/worktrees/wizard-ux-redesign && python3 -m unittest tests.test_setup.TestSegmentInventoryLoader tests.test_arch tests.test_setup`
Expected: PASS.
Run: `cd /home/user-zero/git/personal/ai-kit/.claude/worktrees/wizard-ux-redesign && uv run pre-commit run --all-files`
Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git -C /home/user-zero/git/personal/ai-kit/.claude/worktrees/wizard-ux-redesign add tools/segments_inventory.toml tools/setup.py tests/test_arch.py tests/test_setup.py
git -C /home/user-zero/git/personal/ai-kit/.claude/worktrees/wizard-ux-redesign commit -m "feat(setup): add segments_inventory.toml + loader; arch-test coverage/line-mirror/icon-mirror"
```

---

### Task 8: statusLine adoption detection (engine, read-only)

Add a read-only helper in `setup.py` that reads `settings.json`'s `statusLine` and returns `{"state": "unset"|"ours"|"foreign", "current_command": str|None}`. Classify "ours" when the command invokes the resolved `paths.status_line` (compare against `resolve_paths`, NOT a hard-coded string). Tests for all three states with a temp settings.json.

**Files:**
- Modify: `tools/setup.py` (add `detect_statusline(paths)`; reuse `_read_json`).
- Test: `tests/test_setup.py` (new `TestStatusLineDetection`).

**Interfaces:**
- Consumes: `setup._read_json(path)`, `setup.resolve_paths(env).status_line`/`.settings`.
- Produces: `setup.detect_statusline(paths) -> dict` == `{"state": "unset"|"ours"|"foreign", "current_command": str | None}`. `state == "ours"` iff `paths.status_line` appears as a substring of the configured command (mirrors the existing `_is_inside_str` / `wire_statusline` substring test). Task 9 + Task 10 consume this.

- [ ] **Step 1: Write the failing test**

In `tests/test_setup.py`, add:

```python
class TestStatusLineDetection(unittest.TestCase):
    def _paths(self, settings_payload):
        home = tempfile.mkdtemp(); self.addCleanup(shutil.rmtree, home, ignore_errors=True)
        paths = setup.resolve_paths({"HOME": home})
        os.makedirs(os.path.dirname(paths.settings), exist_ok=True)
        if settings_payload is not None:
            with open(paths.settings, "w", encoding="utf-8") as f:
                json.dump(settings_payload, f)
        return paths

    def test_unset_when_absent(self):
        paths = self._paths({})
        d = setup.detect_statusline(paths)
        self.assertEqual(d["state"], "unset")
        self.assertIsNone(d["current_command"])

    def test_ours_when_command_invokes_resolved_status_line(self):
        paths = self._paths(None)
        cmd = "python3 -S " + paths.status_line
        with open(paths.settings, "w", encoding="utf-8") as f:
            json.dump({"statusLine": {"type": "command", "command": cmd}}, f)
        d = setup.detect_statusline(paths)
        self.assertEqual(d["state"], "ours")
        self.assertEqual(d["current_command"], cmd)

    def test_foreign_when_other_command(self):
        paths = self._paths({"statusLine": {"type": "command", "command": "/usr/bin/mybar"}})
        d = setup.detect_statusline(paths)
        self.assertEqual(d["state"], "foreign")
        self.assertEqual(d["current_command"], "/usr/bin/mybar")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/user-zero/git/personal/ai-kit/.claude/worktrees/wizard-ux-redesign && python3 -m unittest tests.test_setup.TestStatusLineDetection -v`
Expected: FAIL — `AttributeError: module 'setup' has no attribute 'detect_statusline'`.

- [ ] **Step 3: Implement detect_statusline**

In `tools/setup.py`, near `wire_statusline`, add:

```python
def detect_statusline(paths):
    """Read-only: classify settings.json's statusLine for the adoption gate.
    Returns {"state": "unset"|"ours"|"foreign", "current_command": str|None}.
    "ours" iff the command invokes the resolved paths.status_line (XDG-aware
    substring match — NOT a hard-coded string); "foreign" iff set but not ours;
    "unset" iff absent/empty. Writes nothing."""
    data = _read_json(paths.settings)
    cur = data.get("statusLine")
    cur_cmd = cur.get("command", "") if isinstance(cur, dict) else ""
    if not cur_cmd:
        return {"state": "unset", "current_command": None}
    if paths.status_line in cur_cmd:
        return {"state": "ours", "current_command": cur_cmd}
    return {"state": "foreign", "current_command": cur_cmd}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /home/user-zero/git/personal/ai-kit/.claude/worktrees/wizard-ux-redesign && python3 -m unittest tests.test_setup.TestStatusLineDetection -v`
Expected: PASS.

- [ ] **Step 5: Run full setup suite + gate**

Run: `cd /home/user-zero/git/personal/ai-kit/.claude/worktrees/wizard-ux-redesign && python3 -m unittest tests.test_setup`
Expected: PASS.
Run: `cd /home/user-zero/git/personal/ai-kit/.claude/worktrees/wizard-ux-redesign && uv run pre-commit run --all-files`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git -C /home/user-zero/git/personal/ai-kit/.claude/worktrees/wizard-ux-redesign add tools/setup.py tests/test_setup.py
git -C /home/user-zero/git/personal/ai-kit/.claude/worktrees/wizard-ux-redesign commit -m "feat(setup): read-only statusLine adoption detection (unset/ours/foreign) via resolved path"
```

---

### Task 9: Conditional persistence + decoupling

Gate the status-line write path (`save_statusline_config` / `write_toml_preserving` / doctor / `wire_statusline`) on an `adopt` flag, so component symlinking runs regardless of the status-line choice. Set `settings.json` `statusLine` to `python3 -S <paths.status_line>` ONLY on adopt (leave as-is when already "ours" on reconfigure). Components-only writes symlinks and touches NO status-line file and NOT `settings.json` statusLine; nothing-selected + skip = no-op.

**Files:**
- Modify: `tools/setup.py` (add a `persist_statusline(paths, state, adopt, dry)` gate around `_persist_layout` + `wire_statusline`; do not change `launch_wizard`'s symlink path — symlinks already run unconditionally via `apply_selection`).
- Test: `tests/test_setup.py` (new `TestConditionalPersistence`).

**Interfaces:**
- Consumes: `setup._persist_layout(paths, state, dry)`, `setup.wire_statusline(settings, status_line, tty, dry)`, `setup.detect_statusline(paths)` (Task 8).
- Produces: `setup.persist_statusline(paths, state, adopt, dry, tty=None) -> bool`. When `adopt is False` it is a no-op returning `True` (writes neither the TOML nor settings.json statusLine). When `adopt is True` it writes the TOML via `_persist_layout`, and sets `settings.json` statusLine via `wire_statusline` UNLESS detection already reports `"ours"` (reconfigure leaves a correct statusLine as-is). Task 10 surfaces the `adopt` flag in wizard state.

- [ ] **Step 1: Write the failing test**

In `tests/test_setup.py`, add:

```python
class TestConditionalPersistence(unittest.TestCase):
    def _paths(self):
        home = tempfile.mkdtemp(); self.addCleanup(shutil.rmtree, home, ignore_errors=True)
        paths = setup.resolve_paths({"HOME": home})
        os.makedirs(paths.config_dir, exist_ok=True)
        os.makedirs(os.path.dirname(paths.settings), exist_ok=True)
        # seed a real status-line.py + doctor + recipe so writes can doctor-validate
        repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return paths, repo

    def _state(self):
        return {"segments": dict(setup.SEGMENT_DEFAULTS),
                "layout": [dict(l) for l in setup.LAYOUT_DEFAULTS], "dirty": False}

    def test_skip_writes_nothing(self):
        paths, _ = self._paths()
        ok = setup.persist_statusline(paths, self._state(), adopt=False, dry=False)
        self.assertTrue(ok)
        self.assertFalse(os.path.exists(paths.config_toml))
        self.assertFalse(os.path.exists(paths.settings))

    def test_adopt_sets_settings_statusline(self):
        paths, repo = self._paths()
        # point resolved status_line/doctor at the real repo tools so the doctor runs
        paths = paths._replace(
            status_line=os.path.join(repo, "tools", "status-line.py"),
            statusline_doctor=os.path.join(repo, "tools", "statusline-doctor.py"),
            sample=os.path.join(repo, "tools", "statusline.toml.sample"))
        # seed the recipe so save_statusline_config has a base file
        import shutil as _sh
        _sh.copy(paths.sample, paths.config_toml)
        ok = setup.persist_statusline(paths, self._state(), adopt=True, dry=False)
        self.assertTrue(ok)
        data = json.load(open(paths.settings, encoding="utf-8"))
        self.assertIn(paths.status_line, data["statusLine"]["command"])
        self.assertTrue(data["statusLine"]["command"].startswith("python3 -S "))

    def test_reconfigure_leaves_existing_ours_statusline(self):
        paths, repo = self._paths()
        paths = paths._replace(
            status_line=os.path.join(repo, "tools", "status-line.py"),
            statusline_doctor=os.path.join(repo, "tools", "statusline-doctor.py"),
            sample=os.path.join(repo, "tools", "statusline.toml.sample"))
        import shutil as _sh
        _sh.copy(paths.sample, paths.config_toml)
        ours_cmd = "python3 -S " + paths.status_line   # already ours, possibly hand-edited
        with open(paths.settings, "w", encoding="utf-8") as f:
            json.dump({"statusLine": {"type": "command", "command": ours_cmd},
                       "other": 1}, f)
        ok = setup.persist_statusline(paths, self._state(), adopt=True, dry=False)
        self.assertTrue(ok)
        data = json.load(open(paths.settings, encoding="utf-8"))
        self.assertEqual(data["statusLine"]["command"], ours_cmd)  # untouched
        self.assertEqual(data["other"], 1)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/user-zero/git/personal/ai-kit/.claude/worktrees/wizard-ux-redesign && python3 -m unittest tests.test_setup.TestConditionalPersistence -v`
Expected: FAIL — `AttributeError: module 'setup' has no attribute 'persist_statusline'`.

- [ ] **Step 3: Implement persist_statusline**

In `tools/setup.py`, after `_persist_layout`, add:

```python
def persist_statusline(paths, state, adopt, dry, tty=None):
    """Conditionally persist the status-line config + wire settings.json.

    adopt is False  -> NO-OP: write neither statusline.toml nor settings.json's
                       statusLine; an existing status line is left untouched.
    adopt is True   -> write statusline.toml (doctor-validated, auto-revert) via
                       _persist_layout, then set settings.json statusLine to
                       `python3 -S <status_line>` UNLESS it already points at ours
                       (reconfigure leaves a correct, possibly hand-edited command
                       in place). Returns True on success.

    Component symlinking is the caller's concern and runs INDEPENDENTLY of this
    function (a components-only install never calls persist_statusline with adopt
    True, so no status-line file is read or written)."""
    if not adopt:
        return True
    if not _persist_layout(paths, state, dry):
        return False
    if detect_statusline(paths)["state"] == "ours":
        return True
    wire_statusline(paths.settings, paths.status_line, tty, dry)
    return True
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /home/user-zero/git/personal/ai-kit/.claude/worktrees/wizard-ux-redesign && python3 -m unittest tests.test_setup.TestConditionalPersistence -v`
Expected: PASS.

- [ ] **Step 5: Run full setup suite + gate**

Run: `cd /home/user-zero/git/personal/ai-kit/.claude/worktrees/wizard-ux-redesign && python3 -m unittest tests.test_setup`
Expected: PASS.
Run: `cd /home/user-zero/git/personal/ai-kit/.claude/worktrees/wizard-ux-redesign && uv run pre-commit run --all-files`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git -C /home/user-zero/git/personal/ai-kit/.claude/worktrees/wizard-ux-redesign add tools/setup.py tests/test_setup.py
git -C /home/user-zero/git/personal/ai-kit/.claude/worktrees/wizard-ux-redesign commit -m "feat(setup): conditional status-line persistence gated on adopt; symlinks decoupled; reconfigure leaves ours statusLine"
```

---

### Task 10: WizardContext extension

Extend the `WizardContext` NamedTuple (in `wizard_app.py`), `_engine_ns`, and `launch_wizard` (both in `setup.py`) to add the fields Plan B's UI will consume: `status_line` = `{state, current_command}`; a built-in segment metadata map (description/sample/icon/line from the inventory, with `statusline.toml` icon+line overrides applied); an external-segments list with provenance + header metadata; and an `adopt` flag in wizard state. Preserve the module seam (`wizard_app` imports nothing from `setup`).

**Files:**
- Modify: `tools/wizard_app.py` (the `WizardContext` NamedTuple at `:104-110`) — add fields.
- Modify: `tools/setup.py:1429-1461` (`_engine_ns`) — add a `segment_metadata` builder; `tools/setup.py:1464-1532` (`launch_wizard`) — populate the new context fields + `adopt` in state.
- Test: `tests/test_setup.py` (assert the populated context shape via a constructed context), `tests/test_wizard_app.py` (assert the NamedTuple carries the new fields).

**Interfaces:**
- Consumes: `setup.detect_statusline(paths)` (Task 8), `setup.load_segment_inventory(setup.INVENTORY_PATH)` (Task 7), `setup.discover_external_segments(paths, examples_dir)` (Task 5), `setup.current_segments(paths.config_toml)`, the existing `current_layout`.
- Produces: `wizard_app.WizardContext` with the new fields:
  - `status_line: dict` == `{"state": str, "current_command": str | None}`.
  - `segment_meta: dict[str, dict]` == `{key: {"description": str, "sample": str, "icon": str, "line": int}}` (inventory defaults with `statusline.toml` `icon`+`line` overrides applied where present).
  - `external_segments: list[dict]` == the `discover_external_segments` output (each with `id/name/path/default_on/description/icon/sample/line/provenance`).
  - `state` dict additionally carries `"adopt": bool` (initial value derived from detection: `True` when state == "ours", else `False`).

- [ ] **Step 1: Write the failing test**

In `tests/test_wizard_app.py`, add (it already imports `wizard_app`):

```python
class TestWizardContextShape(unittest.TestCase):
    def test_context_carries_new_fields(self):
        ctx = wizard_app.WizardContext(
            selection=object(),
            state={"segments": {}, "layout": [], "dirty": False, "adopt": False},
            sample_json="{}",
            engine=object(),
            status_line={"state": "unset", "current_command": None},
            segment_meta={"path": {"description": "d", "sample": "s",
                                    "icon": "", "line": 0}},
            external_segments=[],
        )
        self.assertEqual(ctx.status_line["state"], "unset")
        self.assertEqual(ctx.segment_meta["path"]["line"], 0)
        self.assertEqual(ctx.external_segments, [])
        self.assertFalse(ctx.state["adopt"])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/user-zero/git/personal/ai-kit/.claude/worktrees/wizard-ux-redesign && python3 -m unittest tests.test_wizard_app.TestWizardContextShape -v`
Expected: FAIL — `TypeError: __new__() got an unexpected keyword argument 'status_line'`.

- [ ] **Step 3: Extend the WizardContext NamedTuple**

In `tools/wizard_app.py:104-110`, replace the NamedTuple with:

```python
class WizardContext(NamedTuple):
    """All data and behaviour the wizard needs, injected by setup.py at
    call-time.  wizard_app imports nothing from setup.py; this is the seam."""
    selection: object           # setup.Selection instance
    state: dict                 # {"segments": {key: bool}, "layout": [...],
                                #  "dirty": bool, "adopt": bool}
    sample_json: str            # rendered sample input JSON for preview
    engine: object              # SimpleNamespace of engine callables
    status_line: dict           # {"state": str, "current_command": str | None}
    segment_meta: dict          # {key: {description, sample, icon, line}}
    external_segments: list     # [{id, name, path, default_on, description,
                                #   icon, sample, line, provenance}, …]
```

(If the existing field is typed `engine: types.SimpleNamespace`, keep that annotation; only the four new fields are added. The seam is preserved — no `import setup`.)

- [ ] **Step 4: Run the wizard_app test to verify it passes**

Run: `cd /home/user-zero/git/personal/ai-kit/.claude/worktrees/wizard-ux-redesign && python3 -m unittest tests.test_wizard_app.TestWizardContextShape -v`
Expected: PASS.

- [ ] **Step 5: Write the setup-side population test**

In `tests/test_setup.py`, add:

```python
class TestBuildSegmentMeta(unittest.TestCase):
    def test_inventory_defaults_with_toml_overrides(self):
        inv = setup.load_segment_inventory(setup.INVENTORY_PATH)
        # no overrides -> inventory defaults pass through
        meta = setup.build_segment_meta(inv, {})
        self.assertEqual(meta["alt_process_memory"]["icon"], "🧮")
        self.assertEqual(meta["context"]["line"], 2)
        # toml override wins for icon + line
        meta = setup.build_segment_meta(inv, {"context": {"icon": "X", "line": 0}})
        self.assertEqual(meta["context"]["icon"], "X")
        self.assertEqual(meta["context"]["line"], 0)
        # description/sample never come from overrides
        self.assertEqual(meta["context"]["description"], inv["context"]["description"])
```

- [ ] **Step 6: Run it to verify it fails**

Run: `cd /home/user-zero/git/personal/ai-kit/.claude/worktrees/wizard-ux-redesign && python3 -m unittest tests.test_setup.TestBuildSegmentMeta -v`
Expected: FAIL — `AttributeError: module 'setup' has no attribute 'build_segment_meta'`.

- [ ] **Step 7: Implement build_segment_meta + populate launch_wizard**

In `tools/setup.py`, add (near `load_segment_inventory`):

```python
def build_segment_meta(inventory, overrides):
    """Merge the built-in inventory (description/sample/icon/line) with per-key
    icon+line overrides from the user's statusline.toml. `overrides` is
    {key: {"icon"?: str, "line"?: int}}. description/sample are inventory-only
    (never overridable). Returns {key: {description, sample, icon, line}}."""
    meta = {}
    for key, entry in inventory.items():
        ov = overrides.get(key, {})
        meta[key] = {
            "description": entry["description"],
            "sample": entry["sample"],
            "icon": ov["icon"] if "icon" in ov else entry["icon"],
            "line": int(ov["line"]) if "line" in ov else entry["line"],
        }
    return meta
```

Add a helper to read icon/line overrides from the user's TOML (reuse `read_toml`):

```python
def _statusline_icon_line_overrides(config_toml):
    """Read per-segment icon+line overrides from the user's statusline.toml, if
    present. Returns {key: {"icon"?: str, "line"?: int}}. The renderer ignores
    these wizard-side override keys; this is installer/wizard metadata only."""
    data = read_toml(config_toml)
    seg = data.get("segments")
    out = {}
    if isinstance(seg, dict):
        for key, val in seg.items():
            if isinstance(val, dict):
                ov = {}
                if "icon" in val:
                    ov["icon"] = str(val["icon"])
                if "line" in val:
                    ov["line"] = int(val["line"])
                if ov:
                    out[key] = ov
    return out
```

In `tools/setup.py:1464-1532` (`launch_wizard`), after `sample_json` is read and BEFORE constructing the context, add:

```python
    sl_state = detect_statusline(paths)
    inventory = load_segment_inventory(INVENTORY_PATH)
    overrides = _statusline_icon_line_overrides(paths.config_toml)
    segment_meta = build_segment_meta(inventory, overrides)
    examples_dir = os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), "examples", "segments")
    external = discover_external_segments(paths, examples_dir)
```

Then replace the `ctx = wizard_app.WizardContext(...)` construction with:

```python
    ctx = wizard_app.WizardContext(
        selection=sel,
        state={"segments": current_segments(paths.config_toml),
               "layout": current_layout(paths.config_toml), "dirty": False,
               "adopt": sl_state["state"] == "ours"},
        sample_json=sample_json,
        engine=_engine_ns(paths, sample_json),
        status_line=sl_state,
        segment_meta=segment_meta,
        external_segments=external,
    )
```

(`_engine_ns` is unchanged — its callables already cover preview/move/toggle. The new context data is computed in `launch_wizard`.)

- [ ] **Step 8: Run the setup-side test to verify it passes**

Run: `cd /home/user-zero/git/personal/ai-kit/.claude/worktrees/wizard-ux-redesign && python3 -m unittest tests.test_setup.TestBuildSegmentMeta -v`
Expected: PASS.

- [ ] **Step 9: Verify the module seam is intact**

Run: `cd /home/user-zero/git/personal/ai-kit/.claude/worktrees/wizard-ux-redesign && grep -n "import setup\|from setup" tools/wizard_app.py`
Expected: no output (wizard_app still imports nothing from setup).

- [ ] **Step 10: Run the full suites + gate**

Run: `cd /home/user-zero/git/personal/ai-kit/.claude/worktrees/wizard-ux-redesign && python3 -m unittest tests.test_setup tests.test_wizard_app tests.test_arch tests.test_status_line`
Expected: PASS.
Run: `cd /home/user-zero/git/personal/ai-kit/.claude/worktrees/wizard-ux-redesign && uv run pre-commit run --all-files`
Expected: PASS.

- [ ] **Step 11: Commit**

```bash
git -C /home/user-zero/git/personal/ai-kit/.claude/worktrees/wizard-ux-redesign add tools/wizard_app.py tools/setup.py tests/test_setup.py tests/test_wizard_app.py
git -C /home/user-zero/git/personal/ai-kit/.claude/worktrees/wizard-ux-redesign commit -m "feat(wizard): extend WizardContext with status_line state, segment_meta, external segments, and adopt flag"
```

---

## Self-Review

### Spec-coverage table — Acceptance (data sourcing)

| PRD acceptance item | Task |
|---|---|
| Every `alt_*` defaults OFF; enabling requires `statusline.toml`/env; golden regenerated lean + byte-stable | Task 1 |
| External ships as `system_memory` (id/env/toggle/file/tests) with `ttl=10`; no stale `sysmem` | Task 2 (ttl=10 preserved; grep-proof in Step 12) |
| Choose renders only categories with ≥1 valid entry; empty categories absent | `validate_entry` already enforces this; the engine exposes it via the existing selection. UI render-only behavior is **Plan B** (this is the Choose screen). Engine coverage = existing `validate_entry` (unchanged) — see Gaps. |
| Every `SEGMENTS` key resolves to an inventory entry; missing fails the gate | Task 7 (coverage arch test) |
| Inventory default `icon`/`line` == renderer defaults (asserted); golden byte-identical | Task 7 (line-mirror + icon-mirror); golden untouched by Task 7 |
| `statusline.toml` `icon`/`line` overrides win over inventory in the wizard | Task 10 (`build_segment_meta` + `_statusline_icon_line_overrides`) |
| Wizard discovers external from BOTH bundled + user dir; tagged by provenance | Task 5 |
| External segments appear with header `name`/`description`/`icon`/`sample`; fallbacks; no crash on id-only header | Task 4 (parser + fallbacks + id-only test) |
| Wizard-side parser reads optional UI keys; renderer parser UNCHANGED | Task 4 (parser extension + renderer-ignores test) |
| `system_memory` carries the full self-describing header as canonical example | Task 6 |
| Config path is `~/.config/ai-kit/statusline.toml` everywhere (XDG-aware) | Already true in `resolve_paths` (`config_toml`); Tasks 2/5/10 use `paths.*` only, never `~/.claude/statusline.toml` |
| No fake/hardcoded component or segment list remains in shipped wizard | Engine sourcing (Tasks 5/7/10) provides real data; removing `_protodata.py` from the shipped wizard is **Plan B** (UI swap) — see Gaps |

### Spec-coverage table — Acceptance (status-line adoption)

| PRD acceptance item | Task |
|---|---|
| Engine detection classifies unset/ours/foreign using resolved path; state+command on `WizardContext` | Task 8 (detection) + Task 10 (`status_line` field) |
| `unset`/`foreign` show gate (foreign also warns + shows command); `ours` goes to editor pre-loaded | Detection data (Task 8) + context field (Task 10); the **UI gate/branching is Plan B** — engine provides `state`+`current_command` |
| Components-only: status line skipped writes symlinks, no status-line file, no settings.json statusLine; existing untouched | Task 9 (`persist_statusline(adopt=False)` no-op; symlinks decoupled) |
| Adopt writes `statusline.toml` (doctor-validated) AND sets settings.json statusLine | Task 9 (`persist_statusline(adopt=True)`) |
| Selecting nothing AND skipping = blocked at Review ("nothing to do") | Existing empty-install guard reused; the **Review-screen block is Plan B**; engine provides `adopt` flag (Task 10) + skip no-op (Task 9) |
| Component link/relink/unlink/prune runs independently of status-line choice | Task 9 (decoupled; `apply_selection` unconditional in `launch_wizard`) |

### Placeholder scan

none found — every code step contains real test code and real implementation code; no TBD/TODO/"add error handling"/"similar to Task N".

### Type-consistency note

Function/field names are consistent across tasks: `discover_external_segments(paths, examples_dir)` (Task 5) is consumed by `launch_wizard` (Task 10); `_external_entry(fields, filename, path, provenance)` (Task 4) is reused by Task 5; `load_segment_inventory(path)` + `INVENTORY_PATH` (Task 7) feed `build_segment_meta(inventory, overrides)` (Task 10); `detect_statusline(paths)` (Task 8) is consumed by both `persist_statusline` (Task 9) and `launch_wizard` (Task 10); the renamed key `alt_process_memory` (Task 3) is used uniformly in the inventory (Task 7) and EXPECTED_ICONS. `WizardContext` field names (`status_line`, `segment_meta`, `external_segments`, `state["adopt"]`) match between the NamedTuple (Task 10 Step 3) and the population (Task 10 Step 7) and the tests.

### Gaps (engine vs UI scope)

Three acceptance items are partially UI-bound and complete only in Plan B, but Plan A delivers all of their engine prerequisites:
1. **Choose "hide-empty" rendering** — `validate_entry` (engine) already classifies entries; the "render only non-empty categories" behavior is a Plan-B screen concern.
2. **Removing `_protodata.py` / fake lists from the shipped wizard** — Plan A makes the real data available on `WizardContext`; the actual removal happens when Plan B swaps the UI to consume it.
3. **Adoption gate UI branching and the Review "nothing to do" block** — Plan A provides `status_line.{state,current_command}`, the `adopt` flag, the skip no-op, and conditional persistence; the gate screens and Review guard are Plan-B UI. No engine acceptance item is left uncovered.

## Plan B (written separately)

Plan B rebuilds the wizard UI into the approved 3-screen next-next carousel (Choose components → Status line with adoption gate + Arrange editor → Review & confirm → Done), matching `docs/wizard-redesign/mockup-textual.html` and the runnable `mockup-textual.py` prototype 1:1, and deletes the illustrative `_protodata.py` from the shipped path. It is authored after Plan A lands, against the finalized `WizardContext` (the `status_line`, `segment_meta`, `external_segments`, and `state["adopt"]` fields this plan produces), reusing the existing fail-closed guards, preview worker, and persistence seam.
