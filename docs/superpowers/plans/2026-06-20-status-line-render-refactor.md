# Status-line Render Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restructure `tools/status-line.py` into one legible measured render pass with a truthful `slowest` diagnostic, normalize icon→text spacing, and add a `make validate` + pre-commit static-analysis gate — without changing the output a correct config produces (except the truthful `slowest` and the corrected icon spacing).

**Architecture:** Three coupled changes. (1) **Icon spacing (FR-R.5):** a single `_icon(glyph, text)` helper every iconed segment routes through, plus a `char_width` fix so variation selectors are zero-width — so VS16 can force narrow-rendering glyphs (`⏱ ⏸ ⚡`) to wide presentation and a one-space gap is always one clean column. (2) **Static-analysis gate (FR-R.0/R.4):** a report-only ruleset/triage spike first, then `make validate` (ruff + pylint + pyright + vulture via `uvx`/`pyright`) and a pinned `.pre-commit-config.yaml`, with fix-to-clean split so structural violations are erased by the restructure rather than suppressed. (3) **Measured-pass restructure (FR-R.1/2/3):** replace the eager `build_data` phase with a lazy-memoized `_RenderData` map so each expensive probe's cost is captured inside the measured build of the first segment that reads it (de-share + cache = "option A"), a single max-tracking helper, and a two-pass render that places `render_time`/`slowest` at their layout positions (dropping the "slowest last on line" workaround).

**Tech Stack:** Python 3.12 stdlib only at runtime (no new runtime deps). Tests: `unittest` (run via `python3 -m unittest`). Dev tooling run through `uvx` (uv is installed; ruff/pylint/vulture/pre-commit are *not* installed system-wide and must not pollute the runtime). `pyright` is installed system-wide (1.1.410).

**Source of truth:** PRD `docs/prds/status-line-render-refactor-v1.0-prd.md` (v1.1). Line numbers below were re-anchored against the live file on 2026-06-20; re-confirm with `grep -n` before editing, since earlier tasks shift later line numbers.

---

## File Structure

**Modified:**
- `tools/status-line.py` — the segment builders, `char_width`, `build_data`→`_RenderData`, `pack_line`/`render`, `LAYOUT`. The one runtime module under refactor.
- `tools/setup.py` — only the fix-to-clean type-hint/lint cleanup (FR-R.4); no behavioral change.
- `Makefile` — add the `validate` target; document next to `test`/`lint`.
- `tests/test_status_line.py` — new tests (icon spacing, VS16 width, golden output, truthful `slowest`, one-git-subprocess). Matches existing idioms: `sl = load_module()`, `THEME`, `strip()`, `_data(**over)`.
- `README.md` — document `make validate` / pre-commit alongside `make test` / `make lint`.

**Created:**
- `pyproject.toml` — ruff + pylint + vulture + pyright config (the enforced ruleset from FR-R.0). Dev-only config; does not make the runtime non-stdlib.
- `.pre-commit-config.yaml` — pinned hooks running the same set + existing `shellcheck`/`py_compile`.
- `docs/refactor/lint-ruleset-and-triage.md` — FR-R.0 deliverable: the enforced ruleset (with a justification per ignore/disable) and the triaged finding inventory.
- `tests/fixtures/golden/` — committed golden snapshot inputs + expected outputs for the render.

---

## Phase 0 — Ruleset & triage spike (FR-R.0)

> No production-code edits in this phase. Output is a reviewed document. This prevents fix-to-clean from manufacturing `# noqa`/`# pylint: disable` carpets on code the restructure deletes.

### Task 0.1: Run the four tools report-only and capture raw output

**Files:**
- Create: `docs/refactor/lint-ruleset-and-triage.md`

- [ ] **Step 1: Run each tool report-only over the two modules + tests**

Run (record each tool's full output; none of these change files):

```bash
cd /home/user-zero/git/personal/ai-kit
uvx ruff check tools/status-line.py tools/setup.py tests/ 2>&1 | tee /tmp/ruff.txt
uvx pylint tools/status-line.py tools/setup.py 2>&1 | tee /tmp/pylint.txt
pyright tools/status-line.py tools/setup.py 2>&1 | tee /tmp/pyright.txt
uvx vulture tools/status-line.py tools/setup.py 2>&1 | tee /tmp/vulture.txt
```

Expected: each prints findings (non-zero counts are expected — this is the baseline). `uvx` downloads the tool into an ephemeral env on first run; that is fine and leaves the runtime stdlib-only.

- [ ] **Step 2: Write the deliverable doc**

Create `docs/refactor/lint-ruleset-and-triage.md` with two sections:

1. **Enforced ruleset.** For each tool, the rules ON and a one-line justification for every `ignore`/`disable`. Sensible defaults: ruff `E,F,W,I,UP,B,SIM,RUF`; pylint default minus only what is justified (e.g. `missing-module-docstring` if the file uses banner comments instead — justify it); pyright `basic`; vulture `--min-confidence 80`. Document any rule turned off and *why* (one line each — no blanket disables).
2. **Triaged finding inventory.** A table: `tool | code | location | tag`, where `tag ∈ {fix-now, fixed-by-refactor, legitimately-suppress}`. `fix-now` = structure-independent (type hints, imports, naming, genuinely dead code). `fixed-by-refactor` = artifact of `pack_line`/`build_data` structure that FR-R.1/2/3 deletes (e.g. `too-many-locals`, `too-many-branches`, vulture "unused" on the shared-probe split). `legitimately-suppress` = a short, justified list, each with a reason.

- [ ] **Step 3: Commit**

```bash
git add docs/refactor/lint-ruleset-and-triage.md
git commit -m "docs(refactor): FR-R.0 lint ruleset + triaged finding inventory"
```

**Deliverable:** reviewed ruleset + inventory. The `fixed-by-refactor` rows are the list of violations Phase 1 must NOT fix or suppress — they are deferred to the Phase 2 zero-sweep.

---

## Phase 1 — Validation gate + icon spacing (FR-R.4-partial + FR-R.5)

> FR-R.5 lands here so the Phase 2 golden snapshot captures already-corrected output. Only structure-independent lint fixes happen here.

### Task 1.1: `char_width` treats variation selectors as zero-width

**Files:**
- Modify: `tools/status-line.py` (`char_width`, ~line 602)
- Test: `tests/test_status_line.py` (add to `TestVisibleWidth`, ~line 134)

- [ ] **Step 1: Write the failing test**

Add to `class TestVisibleWidth`:

```python
    def test_variation_selector_is_zero_width(self):
        self.assertEqual(sl.char_width("️"), 0)  # VS16 emoji presentation
        self.assertEqual(sl.char_width("︎"), 0)  # VS15 text presentation

    def test_glyph_plus_vs16_measures_as_two(self):
        # ⏸ (modeled wide) + VS16 must stay 2 cells, not inflate to 3.
        self.assertEqual(sl.visible_width("⏸️ x"), 4)  # 2 + 0 + 1(space) + 1(x)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_status_line.TestVisibleWidth.test_variation_selector_is_zero_width -v`
Expected: FAIL — `char_width("️")` currently returns 1.

- [ ] **Step 3: Implement the fix**

In `char_width`, add the variation-selector range immediately after the combining check:

```python
def char_width(ch):
    """Display cells for one char: 0 (combining/zero-width), 1, or 2 (wide)."""
    if unicodedata.combining(ch):
        return 0
    o = ord(ch)
    if 0xFE00 <= o <= 0xFE0F:                         # variation selectors render in-place
        return 0
    if o >= 0x1F300:                                  # emoji / pictographs (SMP)
        return 2
    if o in _WIDE_BMP:
        return 2
    if unicodedata.east_asian_width(ch) in ("W", "F"):
        return 2
    return 1
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m unittest tests.test_status_line.TestVisibleWidth -v`
Expected: PASS (all width tests, including the two new ones).

- [ ] **Step 5: Commit**

```bash
git add tools/status-line.py tests/test_status_line.py
git commit -m "fix(status-line): count variation selectors U+FE00..FE0F as zero-width"
```

### Task 1.2: `_icon` helper + VS16 force-wide set

**Files:**
- Modify: `tools/status-line.py` (add helper near `_first_fitting`, ~line 621; `_WIDE_BMP` is at ~line 599)
- Test: `tests/test_status_line.py` (new `class TestIconHelper`)

- [ ] **Step 1: Write the failing test**

Add a new test class (after `TestFirstFitting`):

```python
class TestIconHelper(unittest.TestCase):
    def test_wide_emoji_gets_single_space(self):
        self.assertEqual(sl._icon("\U0001F4C3", "x"), "\U0001F4C3 x")  # 📃 x

    def test_narrow_rendering_glyph_gets_vs16(self):
        # ⏱ ⏸ ⚡ are modeled wide but render narrow bare -> force emoji presentation.
        self.assertEqual(sl._icon("⏱", "x"), "⏱️ x")  # ⏱️ x
        self.assertEqual(sl._icon("⏸", "x"), "⏸️ x")  # ⏸️ x
        self.assertEqual(sl._icon("⚡", "x"), "⚡️ x")  # ⚡️ x

    def test_already_wide_bmp_alarm_clock_no_vs16(self):
        self.assertEqual(sl._icon("⏰", "x"), "⏰ x")  # ⏰ is EAW=W already

    def test_icon_width_is_two_plus_space_plus_text(self):
        self.assertEqual(sl.visible_width(sl._icon("⏸", "12:00")), 8)  # 2+1+5
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_status_line.TestIconHelper -v`
Expected: FAIL — `sl._icon` does not exist (`AttributeError`).

- [ ] **Step 3: Implement the helper**

Add immediately after `_first_fitting` (and document the set next to `_WIDE_BMP`):

```python
# Glyphs we model as wide (_WIDE_BMP) but that render NARROW bare on many
# terminals. Forcing VS16 (emoji presentation) makes them render wide everywhere
# so the single-space _icon gap is always one clean column. ⏰ (U+23F0) is
# already EAW=W, so it is intentionally absent.
_ICON_VS16 = {"⏱", "⏸", "⚡"}  # ⏱ ⏸ ⚡


def _icon(glyph, text):
    """Render `glyph` + exactly one space + `text` — the one place icon→text
    spacing is decided. Narrow-rendering glyphs get VS16 so the gap is one
    visible column regardless of terminal emoji handling."""
    g = f"{glyph}️" if glyph in _ICON_VS16 else glyph
    return f"{g} {text}"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m unittest tests.test_status_line.TestIconHelper -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tools/status-line.py tests/test_status_line.py
git commit -m "feat(status-line): add _icon helper + VS16 force-wide set (no callers yet)"
```

### Task 1.3: Route every iconed segment through `_icon` (fixes the five collapsers)

**Files:**
- Modify: `tools/status-line.py` — `seg_clock` (~1003), `seg_lines` (~1028), `seg_cost` (~1034), `seg_total_time` (~1038), `seg_api_time` (~1042), `seg_todo` (~972), `seg_effort` (~1007), `seg_render_time` (~1047), `seg_slowest` (~1056), `seg_context` (~1071), `seg_chat_size` (~1086), `seg_memory` (~1094), `seg_rate_limits` `_rate_str` (~1129)
- Test: `tests/test_status_line.py` (new `class TestNoCollapsedIcons`)

- [ ] **Step 1: Write the failing test**

```python
class TestNoCollapsedIcons(unittest.TestCase):
    # The five segments that previously glued the glyph to the value.
    def test_collapsers_have_a_space_after_the_icon(self):
        cases = {
            "⏰": sl.seg_clock(_data(), 80, THEME),                 # ⏰
            "\U0001F4C3": sl.seg_lines(_data(), 80, THEME),            # 📃
            "\U0001FA99": sl.seg_cost(_data(cost=0.5), 80, THEME),     # 🪙
            "\U0001F4AC": sl.seg_total_time(_data(), 80, THEME),       # 💬
            "\U0001F4E1": sl.seg_api_time(_data(), 80, THEME),         # 📡
        }
        for glyph, out in cases.items():
            plain = strip(out)
            self.assertTrue(plain.startswith(glyph), plain)
            after = plain[len(glyph):]
            self.assertTrue(after.startswith(" "), f"icon collapsed: {plain!r}")

    def test_no_segment_emits_glyph_then_nonspace(self):
        # Property check across the iconed builders at a wide budget.
        builders = [sl.seg_clock, sl.seg_lines, lambda d, a, t: sl.seg_cost(_data(cost=0.5), a, t),
                    sl.seg_total_time, sl.seg_api_time, sl.seg_render_time,
                    lambda d, a, t: sl.seg_context(_data(), a, t),
                    sl.seg_chat_size, sl.seg_memory]
        for b in builders:
            out = b(_data(t_start=sl.time.perf_counter_ns()), 120, THEME)
            if not out:
                continue
            plain = strip(out)
            for i, ch in enumerate(plain[:-1]):
                # An icon (wide glyph) must be followed by a space or VS16 — never
                # glued to text. Skip bar/box cells, which are legitimately wide.
                if sl.char_width(ch) == 2 and ch not in "█▌░":
                    nxt = plain[i + 1]
                    self.assertIn(nxt, (" ", "️"), f"{plain!r} collapses at {i}")
```

> Note: the property test skips bar/box-drawing cells (`█▌░`) which are legitimately wide-but-not-icons. Keep the explicit five-collapser test as the primary guard; the property test is a backstop.

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_status_line.TestNoCollapsedIcons -v`
Expected: FAIL — the five collapsers emit e.g. `"⏰14:30"` (no space).

- [ ] **Step 3: Edit each builder to use `_icon`**

The five collapsers:

```python
def seg_clock(data, avail, theme):
    return _first_fitting([_icon("⏰", data['clock'])], avail)

def seg_lines(data, avail, theme):
    body = (f"{BG_LIGHTGRAY}{theme.c('GREEN')}+{fmt_number(data['added'])}{RESET}"
            f"/{BG_LIGHTGRAY}{theme.c('RED')}-{fmt_number(data['removed'])}{RESET}")
    return _first_fitting([_icon("📃", body)], avail)

def seg_cost(data, avail, theme):
    return _first_fitting([_icon("🪙", f"${float(data['cost']):.3f}")], avail)

def seg_total_time(data, avail, theme):
    return _first_fitting([_icon("💬", fmt_time_ms(data['total_ms']))], avail)

def seg_api_time(data, avail, theme):
    return _first_fitting([_icon("📡", fmt_time_ms(data['api_ms']))], avail)
```

The already-spaced builders — convert their icon prefix to `_icon` so no spacing literal remains (output is byte-identical for SMP glyphs; `render_time`/`rate_limits`/`todo`-pending gain VS16, which is the intended FR-R.5 change):

```python
# seg_todo: replace the literal "📝 "/"⏸  " forms
    if state == "in_progress":
        return _icon("📝", f"{theme.c('YELLOW')}{text}{RESET}")
    if state == "pending":
        return _icon("⏸", f"{theme.c('GREY')}{text}{RESET}")

# seg_effort: bars = f"🧠 {bar}{RESET}"  ->
    bars = _icon("🧠", f"{bar}{RESET}")

# seg_render_time: f"⏱ {color}{fmt_duration(elapsed)}{RESET}"  ->
    return _first_fitting([_icon("⏱", f"{color}{fmt_duration(elapsed)}{RESET}")], avail)

# seg_slowest: keep 🐌 (SMP, unaffected) but route for consistency
    return _first_fitting([_icon("🐌", f"{name} {dur}"), _icon("🐌", dur)], avail)

# seg_context: f"📊 {bar} {color}{pct}%{RESET}"  -> _icon("📊", f"{bar} {color}{pct}%{RESET}")
#   apply to pct_only, mid, full forms (the "📊 " prefix becomes _icon("📊", ...))

# seg_chat_size: _first_fitting([_icon("💾", f"{color}{fmt_bytes(n)}{RESET}")], avail)
# seg_memory:    _first_fitting([_icon("🧮", fmt_bytes(n))], avail)
# _rate_str last line: return _icon("⚡", " | ".join(parts)) if parts else None
```

> The pending-todo `limit`/icon budgeting (`avail - 4`) is unchanged — `⏸️` is still 2 cells (Task 1.1 guarantees VS16 is zero-width), so the room-for-icon math holds.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m unittest tests.test_status_line.TestNoCollapsedIcons tests.test_status_line.TestCooperativeBuilders -v`
Expected: PASS. Then full module: `python3 -m unittest tests.test_status_line -v` — any failures here are existing tests asserting old glued/double-space output; update those expected strings to the corrected form (this is the intended FR-R.5 change, not a regression).

- [ ] **Step 5: Commit**

```bash
git add tools/status-line.py tests/test_status_line.py
git commit -m "fix(status-line): route all iconed segments through _icon — no collapsed icons (FR-R.5)"
```

### Task 1.4: Add `pyproject.toml` ruleset + `make validate` target

**Files:**
- Create: `pyproject.toml`
- Modify: `Makefile` (add `validate`, extend `.PHONY`)

- [ ] **Step 1: Write `pyproject.toml`** using the FR-R.0 ruleset

```toml
[tool.ruff]
target-version = "py312"
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "W", "I", "UP", "B", "SIM", "RUF"]
# Justify every ignore here (carried from docs/refactor/lint-ruleset-and-triage.md):
ignore = []

[tool.pylint.main]
py-version = "3.12"

[tool.pylint."messages control"]
# Each disable MUST have a one-line justification (see the FR-R.0 doc).
disable = []

[tool.vulture]
min_confidence = 80
paths = ["tools/status-line.py", "tools/setup.py"]

[tool.pyright]
include = ["tools/status-line.py", "tools/setup.py"]
pythonVersion = "3.12"
typeCheckingMode = "basic"
```

> Fill `ignore`/`disable` with exactly the entries the FR-R.0 doc justified — no blanket disables.

- [ ] **Step 2: Add the `validate` target to the Makefile**

```makefile
.PHONY: install reconfigure uninstall doctor check test lint validate

validate:
	uvx ruff check tools/ tests/
	uvx pylint tools/status-line.py tools/setup.py
	pyright tools/status-line.py tools/setup.py
	uvx vulture
```

> `uvx vulture` reads `paths` from `[tool.vulture]`. Keep `pyright` as the installed binary (already present); the other three run via `uvx` so the runtime stays stdlib-only.

- [ ] **Step 3: Run the gate (expect deferred-only failures)**

Run: `make validate`
Expected: the only remaining findings are the `fixed-by-refactor` rows from the FR-R.0 inventory. If a `fix-now` finding appears, it belongs to Task 1.5.

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml Makefile
git commit -m "build(validate): add make validate (ruff+pylint+pyright+vulture) with FR-R.0 ruleset"
```

### Task 1.5: Apply structure-independent fixes + type hints (Phase-1 half of fix-to-clean)

**Files:**
- Modify: `tools/status-line.py`, `tools/setup.py`

- [ ] **Step 1: Apply only the `fix-now` rows** from `docs/refactor/lint-ruleset-and-triage.md`

Fix type hints (function signatures + returns on touched/public functions), import ordering (ruff `I`), naming, and genuinely-dead code vulture flags as `fix-now`. Do **not** touch any `fixed-by-refactor` row (those disappear in Phase 2). Do **not** add `# noqa`/`# pylint: disable` for a `fixed-by-refactor` row.

- [ ] **Step 2: Verify the gate is green except the deferred rows**

Run: `make validate`
Expected: zero `fix-now` findings remain; only `fixed-by-refactor` rows (if any tool reports them) are left. Run `python3 -m unittest tests.test_status_line` — Expected: PASS (type hints/imports don't change behavior).

- [ ] **Step 3: Commit**

```bash
git add tools/status-line.py tools/setup.py
git commit -m "refactor(status-line,setup): structure-independent lint fixes + type hints (FR-R.4 phase 1)"
```

### Task 1.6: Pinned `.pre-commit-config.yaml`

**Files:**
- Create: `.pre-commit-config.yaml`

- [ ] **Step 1: Write the config** (pin every version)

```yaml
# Dev-only. Runtime stays stdlib-only. Versions pinned per FR-R.4 risk note.
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.8.4
    hooks:
      - id: ruff
  - repo: https://github.com/pylint-dev/pylint
    rev: v3.3.3
    hooks:
      - id: pylint
        files: ^tools/(status-line\.py|setup\.py)$
  - repo: https://github.com/RobertCraigie/pyright-python
    rev: v1.1.410
    hooks:
      - id: pyright
        files: ^tools/(status-line\.py|setup\.py)$
  - repo: https://github.com/jendrikseipp/vulture
    rev: v2.14
    hooks:
      - id: vulture
  - repo: local
    hooks:
      - id: shellcheck
        name: shellcheck
        entry: shellcheck
        language: system
        files: \.(sh)$
      - id: py-compile
        name: py_compile
        entry: python3 -m py_compile
        language: system
        files: ^tools/(status-line\.py|setup\.py)$
```

> Confirm the latest stable `rev` for each at implementation time and pin to it; the values above are placeholders to replace with the resolved versions.

- [ ] **Step 2: Verify it runs**

Run: `uvx pre-commit run --all-files`
Expected: the same result as `make validate` (deferred-only findings) plus shellcheck/py_compile green.

- [ ] **Step 3: Commit**

```bash
git add .pre-commit-config.yaml
git commit -m "build(pre-commit): pinned ruff/pylint/pyright/vulture + shellcheck/py_compile"
```

---

## Phase 2 — Measured-pass restructure + final cleanup (FR-R.1 + FR-R.2 + FR-R.3 + FR-R.4-final)

> The golden-output test lands first and snapshots the **already icon-corrected** output. Intentional output changes in this phase (the truthful `slowest` numbers and `slowest` moving next to `render_time`) regenerate the snapshot — the reviewer confirms the diff shows *only* the intended change.

### Task 2.1: Golden-output snapshot test (the safety net)

**Files:**
- Create: `tests/fixtures/golden/inputs.json` (a list of representative raw status-line inputs)
- Create: `tests/fixtures/golden/expected.txt` (generated)
- Test: `tests/test_status_line.py` (new `class TestGoldenOutput`)

- [ ] **Step 1: Write the golden inputs**

Create `tests/fixtures/golden/inputs.json` — a JSON list of `{name, raw, cols, lines}` cases covering: a typical wide terminal (cols 200, lines 50), a narrow terminal (cols 60), a fresh `/clear` session (null cost/context fields), and a non-repo dir. Use deterministic values (no clock/time-dependent fields that vary per run — patch `time.strftime`/`time.time` in the test).

- [ ] **Step 2: Write the test that renders each case and compares to expected.txt**

```python
class TestGoldenOutput(unittest.TestCase):
    GOLDEN = os.path.join(os.path.dirname(__file__), "fixtures", "golden")

    def _render_all(self):
        with open(os.path.join(self.GOLDEN, "inputs.json")) as f:
            cases = json.load(f)
        cfg = sl.default_config()
        theme = sl.build_theme(cfg)
        blocks = []
        with mock.patch.object(sl.time, "strftime", return_value="14:30"), \
             mock.patch.object(sl.time, "time", return_value=NOW):
            for c in cases:
                data, _, _ = sl.build_data(c["raw"], {"HOME": "/home/u"},
                                           cfg.segments, t_start=None)
                data["cols"], data["lines"] = c["cols"], c["lines"]
                lines = sl.render(data, c["cols"], c["lines"], cfg, theme)
                blocks.append(f"### {c['name']}\n" + "\n".join(lines))
        return "\n\n".join(blocks) + "\n"

    def test_matches_golden(self):
        expected_path = os.path.join(self.GOLDEN, "expected.txt")
        actual = self._render_all()
        if os.environ.get("UPDATE_GOLDEN"):
            with open(expected_path, "w") as f:
                f.write(actual)
        with open(expected_path) as f:
            self.assertEqual(actual, f.read())
```

> `t_start=None` makes `seg_render_time` self-omit, keeping the snapshot deterministic. `seg_slowest` reads `data["slowest"]`, which is unset here → it self-omits too. So the golden guards the *non-meta* segments exactly, which is its job.

- [ ] **Step 3: Generate the snapshot and verify it passes**

Run: `UPDATE_GOLDEN=1 python3 -m unittest tests.test_status_line.TestGoldenOutput`
then `python3 -m unittest tests.test_status_line.TestGoldenOutput -v`
Expected: PASS. Inspect `expected.txt` by eye — every iconed segment shows a clean icon→text gap (FR-R.5 confirmed in the snapshot).

- [ ] **Step 4: Commit**

```bash
git add tests/fixtures/golden tests/test_status_line.py
git commit -m "test(status-line): golden-output snapshot (post-FR-R.5 baseline) for the restructure"
```

### Task 2.2: Introduce `_RenderData` (lazy-memoized) — keep output identical

**Files:**
- Modify: `tools/status-line.py` (`build_data`, ~1766; add `_RenderData` class above it)
- Test: `tests/test_status_line.py` (new `class TestRenderDataLazy`)

- [ ] **Step 1: Write the failing tests**

```python
class TestRenderDataLazy(unittest.TestCase):
    def test_git_probe_runs_once_per_render(self):
        raw = {"workspace": {"current_dir": "/repo"}, "session_id": "s"}
        cfg = sl.default_config()  # branch+dirty+worktree all on
        theme = sl.build_theme(cfg)
        with mock.patch.object(sl.subprocess, "run") as run:
            run.return_value = mock.Mock(stdout="## main\n M f\n")
            with mock.patch.object(sl, "_worktree_info_cached", return_value=(True, False, "")):
                data, cols, lines = sl.build_data(raw, {"HOME": "/h"}, cfg.segments)
                sl.render(data, cols, lines, cfg, theme)
        git_calls = [c for c in run.call_args_list if c.args and c.args[0][:2] == ["git", "-C"]]
        self.assertEqual(len(git_calls), 1, "git status must run exactly once per render")

    def test_disabled_git_segments_skip_the_probe(self):
        raw = {"workspace": {"current_dir": "/repo"}}
        cfg = sl.default_config()
        cfg.segments.update(branch=False, dirty=False, worktree=False)
        theme = sl.build_theme(cfg)
        with mock.patch.object(sl.subprocess, "run") as run:
            data, cols, lines = sl.build_data(raw, {"HOME": "/h"}, cfg.segments)
            sl.render(data, cols, lines, cfg, theme)
        git_calls = [c for c in run.call_args_list if c.args and c.args[0][:2] == ["git", "-C"]]
        self.assertEqual(git_calls, [], "no git segment enabled => no git subprocess")
```

- [ ] **Step 2: Run to verify they fail (or pass trivially) and pin behavior**

Run: `python3 -m unittest tests.test_status_line.TestRenderDataLazy -v`
Expected: the first may already pass (build_data calls git once today); keep it as a regression lock for the refactor. The disabled-segments test pins the "disabled costs nothing" invariant.

- [ ] **Step 3: Implement `_RenderData` and convert `build_data`**

Add the class above `build_data`:

```python
class _RenderData(dict):
    """Builder-facing data map. Cheap fields are eager; expensive probes (git,
    transcript/todo parse, RSS, ago, effort-auto) are computed lazily on first
    read and memoized into the dict — so the cost lands inside the *measured
    build* of the first segment that reads it (FR-R.2 option A), and later
    readers get a free hit. A disabled segment never builds, so its probe never
    runs: laziness IS the compute gate for single-consumer probes."""

    def __init__(self, eager, lazy):
        super().__init__(eager)
        self._lazy = dict(lazy)            # {key: thunk}; thunk fills key(s) into self

    def _ensure(self, key):
        if key not in self and key in self._lazy:
            self._lazy.pop(key)()          # run once; thunk does self.update(...)

    def __missing__(self, key):
        if key in self._lazy:
            self._ensure(key)
            return super().get(key)
        raise KeyError(key)

    def get(self, key, default=None):
        self._ensure(key)
        return super().get(key, default)
```

Rewrite `build_data` to split eager vs lazy. The git thunk keeps the per-probe sub-gating via the `segments` closure (so `dirty` off still skips the untracked walk); single-consumer probes drop their `want()` checks (laziness gates them):

```python
def build_data(raw, env, segments=None, t_start=None, git_ttl=_GIT_CACHE_TTL):
    model = raw.get("model") or {}
    cost = raw.get("cost") or {}
    ctx = raw.get("context_window") or {}
    workspace = raw.get("workspace") or {}
    work_dir = os.path.abspath(workspace.get("current_dir") or ".")
    transcript = raw.get("transcript_path") or ""
    home = env.get("HOME", "")
    session = raw.get("session_id") or (
        os.path.splitext(os.path.basename(transcript))[0] if transcript else "")
    claude_dir = env.get("CLAUDE_CONFIG_DIR") or os.path.join(home, ".claude")
    cols, lines, assumed = terminal_size(env)

    def want(key):
        return segments is None or segments.get(key, False)

    eager = {
        "raw": raw,
        "model_name": model.get("display_name", ""),
        "model_id": model.get("id", "unknown"),
        "effort": resolve_effort(raw, env),
        "work_dir": work_dir, "home": home,
        "clock": time.strftime("%H:%M"),
        "added": cost.get("total_lines_added") or 0,
        "removed": cost.get("total_lines_removed") or 0,
        "cost": cost.get("total_cost_usd") or 0,
        "total_ms": cost.get("total_duration_ms") or 0,
        "api_ms": cost.get("total_api_duration_ms") or 0,
        "context_pct": int(ctx.get("used_percentage") or 0),
        "context_max": ctx.get("context_window_size") or 0,
        "rate_limits": raw.get("rate_limits") or {},
        "dim_assumed": assumed, "cols": cols, "lines": lines, "t_start": t_start,
    }

    def _git():
        snap = git_snapshot(work_dir, untracked=want("dirty"),
                            want_worktree=want("worktree"), ttl=git_ttl, env=env)
        data.update(branch=snap.branch, dirty=snap.dirty, is_worktree=snap.is_worktree,
                    wt_name=snap.wt_name, in_repo=snap.in_repo)

    def _ago():
        ok = transcript and os.path.isfile(transcript)
        data["ago"] = fmt_ago(int(time.time()) - int(os.path.getmtime(transcript))) if ok else ""

    def _effort_auto():
        data["effort_auto"] = effort_setting_is_auto(work_dir, home)

    def _todo():
        st, tx = current_todo(transcript, session, claude_dir)
        data.update(todo_state=st, todo_text=tx)

    def _chat():
        data["chat_bytes"] = transcript_bytes(transcript)

    def _mem():
        data["mem_bytes"] = proc_rss_bytes()

    lazy = {
        "branch": _git, "dirty": _git, "is_worktree": _git, "wt_name": _git, "in_repo": _git,
        "ago": _ago, "effort_auto": _effort_auto,
        "todo_state": _todo, "todo_text": _todo,
        "chat_bytes": _chat, "mem_bytes": _mem,
    }
    data = _RenderData(eager, lazy)
    return data, cols, lines
```

> Two `_git` keys share one thunk; `_ensure` pops the *requested* key's thunk and runs it — the thunk fills all five git keys, so the other four are now present and never re-trigger. Same for `_todo`. (The other thunk entries for `_git`/`_todo` remain in `_lazy` but are dead once the keys exist, since `_ensure` checks `key not in self` first.)

- [ ] **Step 4: Run the lazy tests + golden + full suite**

Run: `python3 -m unittest tests.test_status_line.TestRenderDataLazy tests.test_status_line.TestGoldenOutput -v`
Expected: PASS — golden unchanged (field names + values identical; only *when* they're computed moved).
Run: `python3 -m unittest tests.test_status_line` — Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tools/status-line.py tests/test_status_line.py
git commit -m "refactor(status-line): lazy-memoized _RenderData — probes run in the segment that reads them (FR-R.2)"
```

### Task 2.3: Single max-tracking helper + measured pass

**Files:**
- Modify: `tools/status-line.py` (`pack_line` ~1594; add `_crown_slowest` helper)
- Test: `tests/test_status_line.py` (`class TestSlowestTruthful`)

- [ ] **Step 1: Write the failing test (truthful slowest = same order of magnitude as render_time)**

```python
class TestSlowestTruthful(unittest.TestCase):
    def test_slowest_captures_probe_cost_not_microseconds(self):
        raw = {"workspace": {"current_dir": "/repo"}, "session_id": "s"}
        cfg = sl.default_config()
        theme = sl.build_theme(cfg)

        def slow_git(*a, **k):              # simulate a 20ms git status
            sl.time.sleep(0.02)
            return mock.Mock(stdout="## main\n M f\n")

        with mock.patch.object(sl.subprocess, "run", side_effect=slow_git), \
             mock.patch.object(sl, "_worktree_info_cached", return_value=(True, False, "")):
            data, cols, lines = sl.build_data(raw, {"HOME": "/h"}, cfg.segments)
            sl.render(data, cols, lines, cfg, theme)
        name, ns = data["slowest"]
        self.assertIn(name, ("branch", "dirty", "worktree"))   # a real git consumer
        self.assertGreater(ns, 1_000_000)                      # >1ms, not µs
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3 -m unittest tests.test_status_line.TestSlowestTruthful -v`
Expected: FAIL today — the git cost lives in `build_data` (untimed); `slowest` only times the formatting bracket (µs). After Task 2.2 the cost moved into the build, but the *timing bracket* still needs to wrap it (this task).

- [ ] **Step 3: Add `_crown_slowest` and ensure the timing bracket wraps the lazy probe**

```python
def _crown_slowest(data, key, ns, failed):
    """Record the slowest non-meta, non-crashed segment build this render. The
    single place the running max is tracked (FR-R.1). Meta-segments report the
    whole render, never a single builder, so they can't be the culprit."""
    if key in _SLOWEST_META or key in failed:
        return
    cur = data.get("slowest")
    if cur is None or ns > cur[1]:
        data["slowest"] = (key, ns)
```

In `pack_line`, the existing `t0`/`ns` bracket already wraps `safe_build`; because `safe_build` now triggers the lazy probe (the builder reads `data["branch"]` inside the call), the probe cost is captured. Replace the inline max-tracking block with the helper, and **always time** (drop the `track_slow` short-circuit — timing two `perf_counter_ns` reads is negligible and `slowest` is on by default; this removes a per-segment special case per FR-R.1):

```python
    for key in keys:
        if not cfg.segments.get(key, False):
            continue
        sep = sep_w if kept else 0
        avail = budget - used - sep
        t0 = time.perf_counter_ns()
        s = safe_build(key, data, max(avail, 0), theme, failed, builders)
        ns = time.perf_counter_ns() - t0
        if not s:
            continue
        if key in PINNED or visible_width(s) <= avail:
            kept.append(s)
            used += visible_width(s) + sep
            _crown_slowest(data, key, ns, failed)
```

- [ ] **Step 4: Run the test + golden + full suite**

Run: `python3 -m unittest tests.test_status_line.TestSlowestTruthful tests.test_status_line.TestGoldenOutput -v`
Expected: truthful-slowest PASS; golden still PASS (slowest/render_time self-omit in the golden harness).
Run: `python3 -m unittest tests.test_status_line` — Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tools/status-line.py tests/test_status_line.py
git commit -m "refactor(status-line): single _crown_slowest helper; truthful slowest captures probe cost (FR-R.1/R.2)"
```

### Task 2.4: Two-pass render; place `render_time`/`slowest` at their layout positions

**Files:**
- Modify: `tools/status-line.py` (`render` ~1653, `pack_line` ~1594, `LAYOUT` ~58)
- Test: `tests/test_status_line.py` (`class TestTwoPassLayout`)

- [ ] **Step 1: Write the failing test**

```python
class TestTwoPassLayout(unittest.TestCase):
    def test_slowest_renders_adjacent_to_render_time(self):
        raw = {"workspace": {"current_dir": "/repo"}, "session_id": "s",
               "cost": {"total_cost_usd": 0.5}}
        cfg = sl.default_config()
        theme = sl.build_theme(cfg)
        with mock.patch.object(sl.subprocess, "run",
                               return_value=mock.Mock(stdout="## main\n M f\n")), \
             mock.patch.object(sl, "_worktree_info_cached", return_value=(True, False, "")):
            data, cols, lines = sl.build_data(raw, {"HOME": "/h"}, cfg.segments,
                                              t_start=sl.time.perf_counter_ns())
            out = sl.render(data, 200, 50, cfg, theme)
        diag = next(strip(l) for l in out if "⏱" in strip(l))   # the diagnostics row
        # ⏱ render_time then 🐌 slowest are neighbors (only SEP between them).
        i = diag.index("⏱")
        j = diag.index("🐌")
        between = diag[i:j]
        self.assertNotIn("📊", between)  # no context segment wedged between them
        self.assertLess(j - i, 20)       # adjacent, separated only by SEP + value
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3 -m unittest tests.test_status_line.TestTwoPassLayout -v`
Expected: FAIL — today `slowest` is forced last on line 3, far from `render_time`.

- [ ] **Step 3: Move `slowest` next to `render_time` in `LAYOUT`**

```python
LAYOUT = [
    Line(0,  ["path", "branch", "worktree", "dirty", "todo"]),
    Line(20, ["model", "time_ago", "clock", "effort", "lines",
              "cost", "total_time", "api_time"]),
    Line(30, ["render_time", "slowest", "dimensions", "context",
              "chat_size", "memory", "rate_limits"]),
]
```

- [ ] **Step 4: Restructure `render` into two passes**

The meta segments need totals known only after every non-meta build. Build non-meta in pass 1 (recording each line's kept strings keyed by layout index), then build meta in pass 2 with the budget left on their line, and splice them in at their layout position:

```python
def render(data, cols, lines, cfg=None, theme=None):
    cfg = cfg or default_config()
    theme = theme or build_theme(cfg)
    builders = _builders_for(cfg)
    failed = set()
    out = []
    for ln in cfg.layout:
        if lines < ln.min_rows:
            continue
        packed = pack_line(ln.segments, data, cols, cfg, theme, failed, builders)
        if packed:
            out.append(packed)
    diag = diagnostic_line(failed)
    if diag:
        out.append(diag)
    return out
```

and fold the two passes into `pack_line` itself, since the meta dependency is per-line. `pack_line` builds non-meta first (timed, crowning slowest), then builds meta (`render_time` reads `t_start`; `slowest` reads `data["slowest"]` now populated), then assembles in original `keys` order, fitting left→right with all strings known:

```python
def pack_line(keys, data, cols, cfg=None, theme=None, failed=None, builders=None):
    cfg = cfg or default_config()
    theme = theme or build_theme(cfg)
    failed = failed if failed is not None else set()
    builders = builders if builders is not None else _builders_for(cfg)
    budget = cols - RIGHT_MARGIN
    sep_w = visible_width(SEP)

    enabled = [k for k in keys if cfg.segments.get(k, False)]
    built = {}
    # Pass 1: build + time every non-meta enabled segment (crowns slowest via
    # the lazy probes inside safe_build).
    used_est = 0
    for key in enabled:
        if key in _SLOWEST_META:
            continue
        sep = sep_w if used_est else 0
        avail = max(budget - used_est - sep, 0)
        t0 = time.perf_counter_ns()
        s = safe_build(key, data, avail, theme, failed, builders)
        ns = time.perf_counter_ns() - t0
        if not s:
            continue
        if key in PINNED or visible_width(s) <= avail:
            built[key] = s
            used_est += visible_width(s) + sep
            _crown_slowest(data, key, ns, failed)
    # Pass 2: build the meta segments now that timings/max are known.
    for key in enabled:
        if key in _SLOWEST_META:
            s = safe_build(key, data, budget, theme, failed, builders)
            if s:
                built[key] = s
    # Assemble in layout order, fitting left->right with everything known.
    kept, used = [], 0
    for key in enabled:
        s = built.get(key)
        if not s:
            continue
        sep = sep_w if kept else 0
        if key in PINNED or used + sep + visible_width(s) <= budget:
            kept.append(s)
            used += visible_width(s) + sep
    return SEP.join(kept)
```

> This removes the "slowest must be last" workaround: `slowest` is built in pass 2 regardless of its layout position, then placed where `LAYOUT` puts it. `render_time` reading `t_start` and `slowest` reading `data["slowest"]` both work because pass 1 finished first. Remove the now-stale `track_slow`/"slowest last" comments from the old `pack_line`.

- [ ] **Step 5: Run the layout test, regenerate golden, review the diff**

Run: `python3 -m unittest tests.test_status_line.TestTwoPassLayout -v` — Expected: PASS.
Run: `python3 -m unittest tests.test_status_line.TestGoldenOutput` — Expected: FAIL if any non-meta ordering shifted; the golden harness omits meta, so a non-meta diff means an unintended change — investigate before regenerating. If the only failures are meta-related (they shouldn't appear in the harness), regenerate: `UPDATE_GOLDEN=1 python3 -m unittest tests.test_status_line.TestGoldenOutput`, then `git diff tests/fixtures/golden/expected.txt` and confirm the diff is empty or only intended.
Run: `python3 -m unittest tests.test_status_line` — Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add tools/status-line.py tests/test_status_line.py tests/fixtures/golden
git commit -m "refactor(status-line): two-pass pack; slowest adjacent to render_time, drop last-on-line workaround (FR-R.3)"
```

### Task 2.5: Document the contract in-file + `/simplify` + `/reducing-entropy`

**Files:**
- Modify: `tools/status-line.py` (the HOW TO CUSTOMIZE banner ~1673; add a short "render contract" note)

- [ ] **Step 1: Add an in-file contract note** above the builders or near `render`, documenting: built-in + external segments share one `name->builder` map (`_builders_for`) and one gate (`cfg.segments.get(name, False)`); `safe_build` is the single guarded entry (sets `failed`, preserves never-blank); the measured pass times every non-meta build and `_crown_slowest` tracks the max; `render_time`/`slowest` are the only meta segments, built in pass 2.

- [ ] **Step 2: Run `/simplify` then `/reducing-entropy`** over the changed regions; accept only changes that keep the golden + full suite green.

- [ ] **Step 3: Verify**

Run: `python3 -m unittest tests.test_status_line` — Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add tools/status-line.py
git commit -m "docs(status-line): document the render contract in-file; simplify the measured pass"
```

### Task 2.6: Final fix-to-clean zero-sweep (FR-R.4-final)

**Files:**
- Modify: `tools/status-line.py`, `tools/setup.py`, `pyproject.toml` (only if a `legitimately-suppress` entry is now needed), `docs/refactor/lint-ruleset-and-triage.md` (mark resolved rows)

- [ ] **Step 1: Run the gate and confirm the `fixed-by-refactor` rows are gone**

Run: `make validate`
Expected: the structural violations from the FR-R.0 inventory (`too-many-locals`/`too-many-branches`/shared-probe vulture flags) are **absent** — erased by the restructure, not suppressed. Any residual finding must be either fixed now or added to `[tool.*]` ignore/disable *with a justification* (and recorded as `legitimately-suppress` in the FR-R.0 doc). The suppression list stays short.

- [ ] **Step 2: Fill any remaining type hints on the new functions** (`_icon`, `_crown_slowest`, `_RenderData`, the rewritten `build_data`/`pack_line`/`render`).

- [ ] **Step 3: Verify the whole gate + tests are green**

Run: `make validate && python3 -m unittest tests.test_status_line`
Expected: both fully green (zero violations).

- [ ] **Step 4: Commit**

```bash
git add tools/status-line.py tools/setup.py pyproject.toml docs/refactor/lint-ruleset-and-triage.md
git commit -m "refactor(status-line,setup): final fix-to-clean zero-sweep on the restructured code (FR-R.4)"
```

---

## Phase 3 — Verify

### Task 3.1: Full sweep + docs

**Files:**
- Modify: `README.md` (document `make validate` / pre-commit next to `make test` / `make lint`)

- [ ] **Step 1: Document the gate in README** alongside the existing `make test`/`make lint` section: what `make validate` runs, that it's dev-only (runtime stays stdlib-only), and how to enable pre-commit (`uvx pre-commit install`).

- [ ] **Step 2: Run the complete verification sweep**

```bash
make test
make lint
make validate
make doctor                                   # exit 0
echo '{}' | python3 tools/status-line.py      # never-blank: prints at least one line
```

Expected: `make test`/`lint`/`validate` green; `make doctor` exits 0; the empty-input render prints a non-empty bar (never-blank invariant holds).

- [ ] **Step 3: Confirm the FR-R.2 acceptance with a real render**

```bash
# In a git repo with changes, render with diagnostics on and eyeball that
# slowest names a real segment with a ms-scale (not µs) duration next to render_time.
printf '{"workspace":{"current_dir":"%s"},"session_id":"x"}' "$PWD" | python3 tools/status-line.py
```

Expected: `🐌 <segment> <ms>` sits next to `⏱ <ms>`, same order of magnitude.

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs(readme): document make validate + pre-commit alongside make test/lint"
```

- [ ] **Step 5: Fresh holistic review** (E7-loop discipline): re-read the full diff for any HIGH/CRITICAL issue; confirm the contract note matches the code; confirm the suppression list is short and each entry justified.

**Deliverable:** branch ready to finish — truthful `slowest`, corrected icon spacing, green `make validate`/`test`/`lint`, golden test green, never-blank holds.

---

## Self-Review

**Spec coverage (PRD v1.1 → task):**
- FR-R.0 (ruleset & triage spike) → Task 0.1
- FR-R.1 (one contract, one measured pass, single max helper) → Tasks 2.3, 2.5
- FR-R.2 (truthful slowest via de-share + cache; one git subprocess) → Tasks 2.2, 2.3 (+ test in 2.2/2.3)
- FR-R.3 (two-pass, slowest adjacent to render_time, drop last-on-line) → Task 2.4
- FR-R.4 (make validate + pre-commit + fix-to-clean split + type hints) → Tasks 1.4, 1.5, 1.6, 2.6
- FR-R.5 (icon spacing: char_width VS16 + _icon helper + route all segments) → Tasks 1.1, 1.2, 1.3
- Golden-output test → Task 2.1; README docs → Task 3.1; full sweep → Task 3.1

**Known design notes (not gaps):**
- The golden harness intentionally renders with `t_start=None`/no `slowest`, so meta segments self-omit and the snapshot guards only non-meta output (its stated purpose). Meta layout (FR-R.3) is verified by `TestTwoPassLayout`, not the golden.
- Two-pass packing builds non-meta with budget that doesn't yet account for meta width; at very narrow widths the leftmost-priority packing may drop a trailing segment differently than the old code. This is within the "best-fit, leftmost survive" contract and is covered by the narrow-terminal golden case — review that case's diff when regenerating.
- `uvx`-run tools require network on first fetch; if the implementation environment is offline, pre-fetch with `uv tool install ruff pylint vulture pre-commit` before Phase 0/1.
