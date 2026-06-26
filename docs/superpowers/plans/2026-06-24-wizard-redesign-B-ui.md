---
id: 2026-06-24-wizard-redesign-B-ui
title: "Plan B — Wizard UI Rebuild (Textual 8.2.7)"
phase: wizard-ux-redesign
plan_type: implementation
created: 2026-06-24
status: ready
prd: docs/prds/wizard-ux-redesign-v1.0-prd.md
prototype: docs/wizard-redesign/prototypes/mockup-textual.py
worktree: .claude/worktrees/wizard-ux-redesign
---

# Plan B — Wizard UI Rebuild (Textual 8.2.7)

## Global Constraints

These constraints apply to every task in this plan. No task may violate them.

1. **Render-path purity.** `tools/status-line.py` is NEVER modified. It stays
   `python3 -S` stdlib-only. Any import of or modification to `status-line.py`
   is a hard blocker.

2. **Module seam.** `tools/wizard_app.py` imports NOTHING from `tools/setup.py`.
   The AST seam test in `tests/test_wizard_app.py::TestModuleSeam` must remain
   green. All engine callables reach `wizard_app` via `WizardContext.engine`
   (a `SimpleNamespace` built in `setup._engine_ns`).

3. **No `_protodata.py` in shipped code.** `docs/wizard-redesign/prototypes/_protodata.py`
   is prototype-only fake data and must NEVER be imported — directly or
   transitively — by `wizard_app.py`, `setup.py`, or any test that exercises
   the shipped path.

4. **Single-path fail-closed.** Missing tty / uv / textual / terminal too small /
   unhandled crash all exit non-zero to stderr. Clean `q` / `Esc` exits 0 with
   config intact. There is no plain-menu fallback.

5. **Writes on Install only via `persist_statusline`.** The only write path is
   `setup.persist_statusline(paths, state, adopt, dry, tty)`. `wizard_app.py`
   writes nothing to disk; it only returns a `WizardResult`.

6. **Live preview = real renderer.** Preview shells to `python3 -S status-line.py`
   via `engine.render_preview`. Debounced 100 ms, decorated
   `@work(thread=True, exclusive=True, exit_on_error=False)`, epoch-guarded to
   discard stale results. Env var `CC_AI_KIT_CONFIG_FILE` points to a temp TOML.

7. **Textual 8.2.7 API.** Use `border_title` / `border_subtitle` widget
   attributes, not CSS. Padding values are 1, 2, or 4 — never 3.
   `ENABLE_COMMAND_PALETTE = False` at App level.

8. **Navigation model.** `Esc` = Back (one step), `q` = Quit (abort entire
   wizard, exit 0), `?` = help modal. Footer key-bar rendered per-step from
   `FOOTERS` tuples. Push `SummaryScreen` to confirm; single-screen swappable
   body otherwise (avoids Enter double-fire from screen push).

9. **Gate.** `uv run pre-commit run --all-files`. All tasks must land green.

10. **Wizard test hook.** `uv run python -m unittest tests.test_wizard_app
    tests.test_wizard_pty`. Both suites must be green before a task is
    complete.

11. **Mockup parity.** The shipped UI must match `mockup-textual.py` 1:1 for all
    visual behaviors: color palette, `_chip()` shape, `_render_header()` pips,
    `_cap()` keycap style, `_render_footer()` sep and right-pushed Quit, FOOTERS
    content, TITLES, SUBS, `_move_chip_v()` vertical navigation map,
    `_toggle_chip()` home-line placement, `_cycle_focus()` panel rotation.

---

## Task 0 — Quoted-value header parsing + self-describing polish

**Goal:** Extend the wizard-side segment-header parser (`_parse_segment_header`
in `tools/setup.py`) to support **quoted values** so multi-word strings can
contain real spaces and punctuation without underscore escaping:

```
# ai-kit-segment: id=system_memory name="System memory" description="System available RAM" sample="12.0 GiB free" icon=💻 line=1 after=context ttl=10
```

Three minor polish items ship in the same commit (Minor M-3/M-4/M-5 from the
PRD data-sourcing section).

**Files changed:**
- `tools/setup.py` — `_parse_segment_header` token loop (quote-aware splitter);
  `discover_example_segments` and `discover_external_segments` docstrings
  (M-3: list all returned keys including `filename` and `provenance`)
- `examples/segments/system_memory` — header updated to quoted real-space values
- `tests/test_setup.py` — new quoted-value tests; `TestSelectExamples._ex`
  comment (M-4); integration test that `discover` surfaces the real-space description
- `tools/statusline.toml.sample` — document external-segment header grammar
  incl. optional quoting convention (M-5)

**Constraints (hard):**
- `_SEG_HEADER_RE = re.compile(r"^#\s*ai-kit-segment:\s*(.*?)\s*$")` — the
  pattern string is NOT modified. The regex-literal drift guard
  `tests.test_setup.TestDiscoverExampleSegments.test_seg_header_regex_literal_matches_renderer`
  must stay green.
- `tools/status-line.py` `core_parse_segment_header` — NOT touched (render-path
  purity). The renderer never sees wizard-only UI keys; that is by design.

**Implementation approach:**

The existing token loop in `_parse_segment_header`:

```python
for tok in m.group(1).split():
    if "=" in tok:
        k, v = tok.split("=", 1)
        fields[k] = v
```

Replace `m.group(1).split()` with a `shlex`-based quote-aware splitter.
`shlex.split` handles `name="System memory"` → `['name=System memory']` in
`posix=True` mode. Split each token on the FIRST `=` only:

```python
import shlex

# … inside _parse_segment_header, replacing the split() line:
try:
    tokens = shlex.split(m.group(1), posix=True)
except ValueError:
    tokens = m.group(1).split()   # malformed quotes → graceful fallback
for tok in tokens:
    if "=" in tok:
        k, v = tok.split("=", 1)
        fields[k] = v
```

Behavior is byte-identical for unquoted tokens (`id=system_memory` → `{"id":
"system_memory"}`). The regex is not touched; only the content extracted by
`m.group(1)` is re-tokenized.

**Exact work — TDD steps:**

**Step 1 — Failing tests (run RED before any implementation).**

Add to `tests/test_setup.py` inside `TestDiscoverExampleSegments`:

```python
def test_parse_quoted_values(self):
    """T0.1: quoted values with spaces parse to the full phrase."""
    hdr = ('# ai-kit-segment: id=system_memory name="System memory" '
           'description="System available RAM" sample="12.0 GiB free" '
           'icon=💻 line=1 after=context ttl=10\n')
    fields = setup._parse_segment_header(hdr)
    self.assertEqual(fields["name"], "System memory")
    self.assertEqual(fields["description"], "System available RAM")
    self.assertEqual(fields["sample"], "12.0 GiB free")
    # Unquoted tokens still parse correctly
    self.assertEqual(fields["id"], "system_memory")
    self.assertEqual(fields["line"], "1")
    self.assertEqual(fields["ttl"], "10")

def test_parse_quoted_value_with_apostrophe(self):
    """T0.2: values with apostrophe/punctuation inside double quotes."""
    hdr = "# ai-kit-segment: id=x description=\"don't panic\" sample=ok\n"
    fields = setup._parse_segment_header(hdr)
    self.assertEqual(fields["description"], "don't panic")
    self.assertEqual(fields["sample"], "ok")

def test_parse_id_only_header_unchanged(self):
    """T0.3: bare id-only header still parses (regression guard)."""
    hdr = "# ai-kit-segment: id=foo\n"
    fields = setup._parse_segment_header(hdr)
    self.assertEqual(fields, {"id": "foo"})
```

Run: `uv run python -m unittest tests.test_setup.TestDiscoverExampleSegments.test_parse_quoted_values tests.test_setup.TestDiscoverExampleSegments.test_parse_quoted_value_with_apostrophe` → **RED** (current `.split()` truncates at the space inside quotes).

**Step 2 — Implement the quote-aware splitter.**

Edit `tools/setup.py`: add `import shlex` to the stdlib imports block at the
top of the file. Then replace the token loop inside `_parse_segment_header`
(lines ~542–546) with the `shlex.split` version shown above.

**Step 3 — Run GREEN.**

```
uv run python -m unittest tests.test_setup.TestDiscoverExampleSegments
```

All `TestDiscoverExampleSegments` tests must pass including the unchanged
`test_seg_header_regex_literal_matches_renderer` drift guard.

**Step 4 — Update `examples/segments/system_memory` header.**

Replace the current header line (which uses underscore-escaped values):

```
# ai-kit-segment: line=1 after=context id=system_memory ttl=10 name=system_memory icon=💻 description=System_available_RAM sample=12.0_GiB_free
```

with the real-space quoted form:

```
# ai-kit-segment: id=system_memory name="System memory" description="System available RAM" sample="12.0 GiB free" icon=💻 line=1 after=context ttl=10
```

**Step 5 — Add integration test asserting real-space description surfaces.**

Add to `TestDiscoverExampleSegments`:

```python
def test_discover_real_examples_surfaces_quoted_description(self):
    """T0.5: shipped system_memory header uses quoted values; discover returns
    the real-space strings (not underscore-escaped)."""
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    found = setup.discover_example_segments(
        os.path.join(repo, "examples", "segments"))
    sm = next((e for e in found if e["id"] == "system_memory"), None)
    self.assertIsNotNone(sm, "system_memory not found in examples/segments/")
    self.assertEqual(sm["name"], "System memory")
    self.assertEqual(sm["description"], "System available RAM")
    self.assertEqual(sm["sample"], "12.0 GiB free")
```

Run: `uv run python -m unittest tests.test_setup.TestDiscoverExampleSegments.test_discover_real_examples_surfaces_quoted_description` → **GREEN**.

**Step 6 — Apply three doc-sweep edits (M-3, M-4, M-5).**

*M-3:* In `tools/setup.py`, update the `discover_example_segments` docstring
to list ALL returned keys:

```python
def discover_example_segments(examples_dir):
    """Scan `examples_dir` for shippable example external segments, each carrying
    a `# ai-kit-segment: … id=<id> …` header. Returns a list of
    {id, filename, name, path, default_on, description, icon, sample, line}
    sorted by id. `filename` is the real filesystem filename (used as the
    install-destination by install_example_segments). `default_on` is always
    True (every example is OFFERED pre-checked). The UI keys come from the
    OPTIONAL self-describing header (`name`/`description`/`icon`/`sample`);
    missing fields fall back to id-as-name, blank description,
    DEFAULT_SEGMENT_ICON, and the last layout line. Files without the marker or
    without an `id` are skipped; a missing dir yields []."""
```

Update the `discover_external_segments` docstring likewise:

```python
def discover_external_segments(paths, examples_dir):
    """Merge bundled (examples/segments/) and user (paths.segments_dir) external
    segments. Each entry carries {id, filename, name, path, default_on,
    description, icon, sample, line, provenance} where provenance is
    "bundled" | "user". On an id collision the USER entry wins (it shadows
    the bundled copy the user customized). All entries default OFF in the wizard
    unless statusline.toml enables them. `filename` is preserved from the
    winning entry and drives the install-destination in install_example_segments.
    Returned list is id-sorted."""
```

*M-4:* In `tests/test_setup.py`, add a comment to `TestSelectExamples._ex`
clarifying that it is selection-only and intentionally omits `filename`:

```python
def _ex(self, *ids):
    # Minimal dict for selection-only tests. Intentionally omits `filename`,
    # `description`, `icon`, `sample`, `line`, and `provenance` — those fields
    # are not consulted by select_examples / resolve_example_selection.
    return [{"id": i, "name": i, "path": f"/x/{i}", "default_on": True}
            for i in ids]
```

*M-5:* In `tools/statusline.toml.sample`, locate the external-segment header
grammar documentation block (search for `ai-kit-segment:` in the file). Add a
note about quoting after the existing grammar line:

```toml
# Header grammar:  # ai-kit-segment: id=<id> [key=value …]
# Values with spaces or punctuation can be double-quoted:
#   # ai-kit-segment: id=system_memory name="System memory" description="System available RAM"
# Unquoted values must not contain whitespace.
```

**Step 7 — Run focused tests + full gate.**

```
uv run python -m unittest tests.test_setup.TestDiscoverExampleSegments
uv run python -m unittest tests.test_setup
uv run pre-commit run --all-files
```

All must be green.

**Step 8 — Commit.**

```
git -C <worktree> commit -m "feat(setup): quoted values in self-describing segment headers + doc polish"
```

**Acceptance criteria:**
- `test_parse_quoted_values` and `test_parse_quoted_value_with_apostrophe` green.
- `test_seg_header_regex_literal_matches_renderer` (drift guard) still green.
- `test_discover_real_examples_surfaces_quoted_description` green.
- `examples/segments/system_memory` header uses real-space quoted values.
- `_SEG_HEADER_RE` pattern string unchanged.
- `tools/status-line.py` not touched.
- Gate green.

**Definition of done:** gate green; all `TestDiscoverExampleSegments` tests
green; drift guard green; seam test green; render path untouched.

---

## Task 1 — Color palette, CSS, and App scaffold

**Goal:** Establish the App class, global CSS, color constants, ENABLE_COMMAND_PALETTE=False,
step constants, and LANE_GATE — the shared foundation every subsequent task builds on.
No interactive behavior yet; the app must mount and exit cleanly.

**Files changed:** `tools/wizard_app.py`

**Exact work:**

Define module-level color constants (copy verbatim from mockup, which is the
canonical source):

```python
FG      = "#c9d1d9"
DIM     = "#6e7681"
LINE    = "#30363d"
ACCENT  = "#58a6ff"
GREEN   = "#3fb950"
WARN    = "#d29922"
PINK    = "#db61a2"
CYAN    = "#39c5cf"
KEYCAP  = "#21262d"
```

Define step constants and lane gate:

```python
STEP_CHOOSE  = 0
STEP_ARRANGE = 1
STEP_REVIEW  = 2
STEP_DONE    = 3

LANE_GATE = {1: 20, 2: 30}   # 0-based line index → min terminal rows required
```

Define TITLES, SUBS (subtitle per step), FOOTERS (key-bar tuples per step),
and QUIT_KEY — matching mockup exactly:

```python
TITLES = [
    "Choose what to install",
    "Arrange your status line",
    "Review & confirm",
    "✓ ai-kit is installed",
]

SUBS = [
    "Toggle skills, agents and commands",
    "Drag segments across lines",
    "Check your selections before writing",
    "Run the doctor to verify your setup",
]

# Each tuple: (label, key, is_primary)
# FOOTERS[STEP_CHOOSE]: a/n = per-category; A/N = global all/none (not shown in
#   the footer bar — global all/none is footer-omitted for space, full key
#   legend including A/N lives in HELP[STEP_CHOOSE] below, rendered by the
#   Help modal in Task 8).
# FOOTERS[STEP_ARRANGE]: r = reset layout to LAYOUT_DEFAULTS; shift+tab = reverse
#   panel cycle.
FOOTERS = [
    [("Continue", "enter", True), ("Toggle", "space", False),
     ("Move", "↑↓", False), ("Category", "a/n", False), ("Help", "?", False)],
    [("Continue", "enter", True), ("Back", "esc", False), ("Move", "←→", False),
     ("Line", "↑↓", False), ("On/off", "space", False), ("Reset", "r", False),
     ("Help", "?", False)],
    [("Install", "enter", True), ("Back", "esc", False), ("Help", "?", False)],
    [("Finish & exit", "enter", True)],
]

QUIT_KEY = ("Quit", "q")
```

Define `HELP`, the per-step key legend rendered by the Help modal (Task 8).
This is the single source of truth for help content; it is richer than
`FOOTERS` (which is footer-bar space-constrained) — it spells out the a/n
vs A/N distinction and the off-tray semantics that the footer omits.
Matches `docs/wizard-redesign/prototypes/mockup-textual.py` `HELP` dict,
adapted to this plan's exact key bindings (`Tab`/`shift+tab` for chip focus,
`r` for layout reset):

```python
# Each tuple: (key, description)
HELP = {
    STEP_CHOOSE: [
        ("↑ ↓", "Move the highlight between components"),
        ("Space", "Install / skip the highlighted component"),
        ("a / n", "Select all / none in the current category"),
        ("A / N", "Select all / none across every category"),
        ("Enter", "Continue to Arrange"),
        ("q", "Quit the installer"),
    ],
    STEP_ARRANGE: [
        ("← →", "Reorder the focused chip within its line"),
        ("↑ ↓", "Move the chip across lines (↑ off Line 1 → OFF tray)"),
        ("Space", "Turn the focused segment on/off (off → tray)"),
        ("Tab / ⇧Tab", "Focus the next / previous chip"),
        ("r", "Reset the layout to defaults"),
        ("Enter", "Continue to Review"),
        ("Esc", "Back to Choose"),
        ("q", "Quit the installer"),
    ],
    STEP_REVIEW: [
        ("Enter", "Install / write the config"),
        ("Esc", "Back to Arrange"),
        ("q", "Quit the installer"),
    ],
    STEP_DONE: [
        ("Enter", "Finish and exit"),
        ("q", "Quit"),
    ],
}
```

Define `WizardResult`, `WizardContext`, and `WizardCrash` (NamedTuples and
Exception subclass). These are the stable public types; downstream tasks extend
behavior, not signatures:

```python
class WizardResult(NamedTuple):
    selection: object        # typed as Selection in setup.py cast
    state: dict

class WizardContext(NamedTuple):
    selection: object
    state: dict
    sample_json: str
    engine: object           # SimpleNamespace with render_preview/groups/order/
                             # layout_move/layout_toggle/off_tray/apply_command
    status_line: dict        # {"state": "unset"|"ours"|"foreign", "current_command": str|None}
    segment_meta: dict       # {key: {description, sample, icon, line}}
    external_segments: list  # [{id, name, path, description, icon, sample, line, provenance, ...}]

class WizardCrash(Exception):
    """Raised by run_wizard when an unhandled exception escapes the app."""
```

Define `WizardApp(App)` skeleton with:
- `ENABLE_COMMAND_PALETTE = False`
- `CSS` string matching mockup (full `.wizard-*` ruleset; padding 1/2/4 only)
- `__init__(self, ctx: WizardContext)` storing `self._ctx = ctx` and
  `self._exception: BaseException | None = None`
- `on_mount` that installs exception handler and displays the first step body
- Keybinding: `q` → `action_quit`, `escape` → `action_back`, `?` → `action_help`

Define `run_wizard(ctx: WizardContext) -> WizardResult | None`:
- Checks `shutil.get_terminal_size()` against minimum (40 cols × 10 rows);
  if too small, raises `WizardCrash("terminal too small: …")`
- Runs `WizardApp(ctx).run()` synchronously
- Re-raises `app._exception` as `WizardCrash` if set
- Returns `app._result` (a `WizardResult`) or `None` on abort

**Acceptance test (unit):** `TestWizardApp.test_boot` mounts the app and
asserts it does not crash. `TestCrashSafety.test_small_terminal` passes a
mock terminal size of 10×5 and asserts `WizardCrash` is raised. Both must
pass with `uv run python -m unittest tests.test_wizard_app`.

**Definition of done:** gate green; `test_wizard_app` green; no import of
`_protodata` or `setup`; seam test green.

---

## Task 2 — Header, footer, and step-pip rendering helpers

**Goal:** Implement the pure rendering helpers (`_render_header`, `_render_footer`,
`_cap`, `_chip`) and wire them into a `Header` widget and `Footer` widget used
by every step body. These functions have no side effects; they are tested in
isolation.

**Files changed:** `tools/wizard_app.py`

**Exact work:**

Implement `_render_header(step: int, total: int = 4) -> str` — returns a Rich
markup string. Filled pips (steps up to and including `step`) use
`[{ACCENT}]●[/]`; unfilled use `[{LINE}]○[/]`; the Done step pip
uses `[{GREEN}]●[/]`. Pips are joined with a single space.

```python
def _render_header(step: int, total: int = 4) -> str:
    pips = []
    for i in range(total):
        if i < step:
            pips.append(f"[{ACCENT}]●[/]")   # filled — past step
        elif i == step and step == STEP_DONE:
            pips.append(f"[{GREEN}]●[/]")     # done
        elif i == step:
            pips.append(f"[{ACCENT}]●[/]")    # current
        else:
            pips.append(f"[{LINE}]○[/]")      # future
    return " ".join(pips)
```

Implement `_cap(label: str, primary: bool = True) -> str` — returns Rich
markup for a keycap. Primary: `[#cae3ff on #10325c] {label} [/]`. Secondary:
`[#e6edf3 on {KEYCAP}] {label} [/]`. Both include one leading and one
trailing space inside the markup brackets.

Implement `_render_footer(keys: list[tuple[str,str,bool]], width: int) -> str`
— builds the footer bar. `QUIT_KEY` is always appended right-aligned (pushed
right with a Rich `[right][/right]` or equivalent pad). Each key entry is
`_cap(key, primary) + " " + label`. Entries separated by
`f"   [{LINE}]│[/]   "` (3 spaces, pipe glyph, 3 spaces).

Implement `_chip(label: str, focused: bool, parked: bool = False) -> str` —
returns Rich markup for a segment chip. Focused:
`[{PINK}][[/][bold #ffffff on #1b1016]{label}[/][{PINK}]][/]` with `[>` and
`<]` brackets (i.e., `[PINK]\[>[/][bold #ffffff on #1b1016]{label}[/][PINK]<\][/]`
producing the `[>label<]` visual). Unfocused: `[col on #0d1117] {label} [/]`
where `col = DIM` if `parked` else `FG`.

Define `WizardHeader(Static)` and `WizardFooter(Static)` widgets — each
accepts the step int in `__init__`, sets `self._step` and calls
`self.update(…)` from `on_mount` to render the correct pip / key bar.
`WizardFooter` must also accept a `keys` override to allow step-specific
key bars (including the Quit key pushed right).

**Acceptance test (unit):** Add assertions in `TestWizardApp` (or a dedicated
`TestRenderers` class) that verify:
- `_render_header(0)` contains exactly one `ACCENT` pip and three `LINE` pips
- `_render_header(STEP_DONE)` contains at least one `GREEN` pip
- `_chip("path", focused=True)` contains `[>path<]`
- `_chip("model", focused=False)` contains `[model]`
- `_cap("enter", primary=True)` contains `#10325c` background

These tests must pass with `uv run python -m unittest tests.test_wizard_app`.

**Definition of done:** gate green; helper unit tests green; seam test green.

---

## Task 3 — Picks screen (_PicksScreen)

**Goal:** Implement `_PicksScreen` — the "Choose what to install" step body
(STEP_CHOOSE). Segments displayed grouped by category in layout-line order
via `engine.groups`. Toggle with Space, select all/none within the focused
category with `a`/`n`, select all/none globally with `A`/`N`. Glyph `◉` = on,
`◯` = off. Cursor navigation with Up/Down arrows. Enter advances to STEP_ARRANGE.

**Files changed:** `tools/wizard_app.py`, `tools/setup.py`

**Exact work:**

**setup.py — add `Selection.set_category()`:**

`Selection` in `setup.py` has no per-category set method. Add it:

```python
def set_category(self, cat: str, value: bool) -> None:
    """Set all items in `cat` to `value`."""
    for it in self.items:
        if it[0] == cat:
            it[2] = bool(value)
```

This must be added to the `Selection` class (after `set_all`). No other
`Selection` changes; the existing `set_all(value)` remains for the global A/N
bindings.

**wizard_app.py — `_PicksScreen` class:**

`_PicksScreen` is a `Widget` (not a `Screen`). Concrete transition: change
`class _PicksScreen(Screen)` → `class _PicksScreen(Widget)` and remove any
`pop_screen`/`push_screen` calls inside it. Step transitions happen via
`AdvanceStep` messages posted to the parent `WizardApp` (see Task 8), which
body-swaps the active widget. This avoids the Enter double-fire bug inherent
in pushed Screens.

`_PicksScreen` holds a reference to `WizardContext` and renders a scrollable
list of grouped segment entries.

State it manages: `self._selection` (a reference to `ctx.selection`; the
`Selection` object is mutated in-place via `.toggle()`, `.set_all()`,
`.set_category()`, `.move_cursor()`). The widget re-renders on every state
mutation via `self.refresh()`.

`self._cur_cat: str` — the category of the currently focused row (used by
`a`/`n` to know which category to act on). Updated whenever the cursor moves
to a row belonging to a different category.

Key bindings (bound in `_PicksScreen.BINDINGS` or via `on_key`):
- `space` → `ctx.selection.toggle_cursor()` then `_sync_selection_to_state()`,
  `refresh()`
- `a` → `ctx.selection.set_category(self._cur_cat, True)` then
  `_sync_selection_to_state()`, `refresh()` — **per-category** all-on
- `n` → `ctx.selection.set_category(self._cur_cat, False)` then
  `_sync_selection_to_state()`, `refresh()` — **per-category** all-off
- `A` → `ctx.selection.set_all(True)` then `_sync_selection_to_state()`,
  `refresh()` — **global** all-on
- `N` → `ctx.selection.set_all(False)` then `_sync_selection_to_state()`,
  `refresh()` — **global** all-off
- `up` → `ctx.selection.move_cursor(-1)` then update `_cur_cat`, `refresh()`
- `down` → `ctx.selection.move_cursor(1)` then update `_cur_cat`, `refresh()`
- `enter` → post `AdvanceStep(STEP_ARRANGE)` message to parent App

Rendering (via `render()` or composing `Label` children):
- For each group from `engine.groups(ctx.state)`, render the group label in
  `[{DIM}]` markup as a section header with a **per-category count**:
  ```
  [{DIM}]─── {category_label}  [{GREEN}]{on}[/]/{total} on ───[/]
  ```
  where `on = sum(1 for it in ctx.selection.items if it[0]==cat and it[2])`
  and `total = sum(1 for it in ctx.selection.items if it[0]==cat)`.
- For each segment key in the group, render one row:
  `"  {glyph} {icon} {name}  {description}"` where
  - `glyph = "[{GREEN}]●[/]"` if enabled else `"[{DIM}]○[/]"`
  - `icon` = `ctx.segment_meta[key]["icon"]` (empty string if absent)
  - `description` = `ctx.segment_meta[key]["description"]` (empty string if absent)
  - The cursor row is highlighted: `[on {LINE}]…[/]`
- A **total count** line at the bottom of the widget (rendered as a `Static`
  with `id="picks-count"`):
  ```
  [{GREEN}]{sel_n}[/] of {total_n} components selected
  ```
  where `sel_n = sum(1 for _, _, on in ctx.selection.items if on)` and
  `total_n = len(ctx.selection.items)`. Updated on every `refresh()`.
- Both the per-category count and the total count must update immediately
  after every `space`/`a`/`n`/`A`/`N` key event.

External segments (from `ctx.external_segments`) are appended as their own
group labeled `"external"` after the built-in groups. Each external entry
uses the same glyph/icon/description fields from `ctx.external_segments[i]`.

The `Selection` object's `.items` list is the source of truth for enabled
state; `engine.groups(ctx.state)` provides the display order. The picks
widget must keep `ctx.state["segments"]` in sync with `selection.enabled_map()`
after every toggle so the live preview (Task 6) sees up-to-date state.
Use a helper `_sync_selection_to_state()` that calls
`ctx.state["segments"].update(ctx.selection.enabled_map())`.

**Acceptance tests (unit):**
- `TestInstallPicks.test_space_toggle_changes_glyph` — mount app, query the
  picks widget, send `space`, assert glyph flipped from `◉` to `◯`.
- `TestInstallPicks.test_a_selects_category_only` — with cursor in category
  "skills" that has 2/5 on, send `a`, assert all skills-category glyphs are
  `◉` but other category glyphs are unchanged (per-category, not global).
- `TestInstallPicks.test_n_deselects_category_only` — with all on, send `n`,
  assert only the focused category is all-`◯`; other categories unchanged.
- `TestInstallPicks.test_A_selects_all_global` — send `A`, assert ALL glyphs
  across all categories are `◉`.
- `TestInstallPicks.test_N_deselects_all_global` — send `N`, assert ALL
  glyphs across all categories are `◯`.
- `TestInstallPicks.test_per_category_count_renders` — mount, assert the
  category header line contains `/{total} on` text.
- `TestInstallPicks.test_total_count_renders` — assert `#picks-count` widget
  contains `"of {total_n} components selected"`.
- `TestInstallPicks.test_glyph_shape` — assert focused row uses `◉`/`◯`
  (shape-based, color-independent).

All must pass with `app.run_test()` pilot. Use `IsolatedAsyncioTestCase`.

**Definition of done:** gate green; all `TestInstallPicks` tests green; seam
test green; no `_protodata` import.

---

## Task 4 — Layout board panels (LayoutBoard)

**Goal:** Implement `LayoutBoard` — the "Arrange your status line" step body
(STEP_ARRANGE). Four bordered panels: (1) active line lanes, (2) focused-chip
detail, (3) Off tray, (4) live preview placeholder (wired in Task 6).
Left/right arrows reorder within a lane; up/down arrows move cross-line
(including to/from Off tray — no-op when focused chip is in the tray);
Space toggles chip on/off; `r` resets layout to defaults; `Tab`/`Shift+Tab`
cycle panel focus forward/backward.

**Files changed:** `tools/wizard_app.py`

**Exact work:**

**Concrete class transition:** change `class LayoutBoard(Screen)` →
`class LayoutBoard(Widget)`. Remove any `pop_screen`/`push_screen` calls inside
it. Step transitions happen via `AdvanceStep` messages posted to the parent
`WizardApp`, which body-swaps the active widget (see Task 8). This avoids the
Enter double-fire bug inherent in pushed Screens.

**Step-2 adoption gate (shown BEFORE the Arrange editor, at the start of
STEP_ARRANGE):** Per the PRD, Step 2 opens with an adoption gate:
- `ctx.status_line["state"] == "ours"`: gate is skipped; load the board
  pre-populated from the saved arrangement. `ctx.state["adopt"]` remains True.
- `ctx.status_line["state"] == "unset"`: prompt "Wire status line? [Y/n]"
  (default Yes). Selecting Y sets `ctx.state["adopt"] = True`; selecting N
  (or Skip) sets `ctx.state["adopt"] = False` and shows a one-line
  confirmation "No status-line writes — component install only." before
  proceeding to the Arrange editor.
- `ctx.status_line["state"] == "foreign"`: prompt "Existing status line
  detected. Replace with ai-kit? [y/N]" (default No). Show
  `ctx.status_line["current_command"]` in the prompt so the user sees what
  would be replaced. Y sets `ctx.state["adopt"] = True`; N/Keep sets
  `ctx.state["adopt"] = False` and shows the one-line confirmation.

The gate is rendered as a focusable prompt above the board panels when
`LayoutBoard` first mounts. After the user makes a choice, the prompt is
replaced by the four-panel Arrange editor. Implementation: use a simple
`_gate_done: bool` flag; when False, render the gate prompt (a
`GatePrompt(Widget)` child); when True, render the four board panels. A key
handler (`y`/`n`/`enter`/`esc` on the gate) sets `_gate_done = True` and
triggers `self.refresh()`.

`LayoutBoard` is a `Widget` composed into the app's content area. It manages:
- `self._focused_seg: str` — the currently focused chip key
- `self._focus_panel: int` — which panel is focused (0=lanes, 1=detail,
  2=tray, 3=preview); cycles with Tab/Shift+Tab
- `self._preview_epoch: int = 0` — incremented each `_schedule_preview` call;
  starts at 1 after `on_mount` fires the first preview
- `self._gate_done: bool` — True once the adoption-gate prompt has been
  answered; only then are the four board panels shown

**Widget tree (DOM) for the Arrange editor (once `_gate_done = True`):**

```
LayoutBoard (Widget, id="step-arrange")
├── Static (id="board-lanes")          # lane panel — horizontal chip rows
├── Static (id="board-detail")         # detail panel — focused chip metadata
├── Static (id="board-tray")           # off-tray panel — parked chips
├── Static (id="board-preview")        # preview panel (Task 6)
└── Label  (id="board-label", classes="sr-only")  # TEST-ONLY — not visible
```

`#board-label` is a **hidden test-helper** `Label` (`classes="sr-only"`,
CSS: `display: none`) updated on every `refresh()`. It contains the full lane
panel text as a plain string. Unit tests use `query_one("#board-label", Label)`
to assert chip shape without parsing Rich markup from the visible panels:

```python
lbl = board.query_one("#board-label", Label)
text = str(lbl.content)
assert "[>path<]" in text   # focused chip
assert "[model]" in text    # unfocused chip
```

`#board-label` is a sibling of the four visible panels, NOT nested inside any
of them. It is never rendered visibly. There is no `#board-label` in the
prototype's widget tree (the prototype pre-dates this test-helper design) — it
is introduced purely for PTY/unit-test assertions.

Four sub-panels rendered as bordered `Static` widgets (each set via
`.update(…)` on every `refresh()`):

1. **Lane panel** (`#board-lanes`): renders each layout line as a horizontal
   row of `_chip(seg, focused=(seg==self._focused_seg))` chips, one row per
   `ctx.state["layout"]` entry. Row header = `_ROW_LABELS` from setup:
   `{0: "identity line", 20: "model line", 30: "diagnostics line"}`, keyed by
   `row["min_rows"]`. `border_title = "Lines"`.

2. **Detail panel** (`#board-detail`): shows `segment_meta` for the focused
   chip — description, sample value, icon — formatted in Rich markup.
   `border_title = "Detail"`. `border_subtitle` = provenance tag if external.

3. **Off-tray panel** (`#board-tray`): renders chips from
   `engine.off_tray(ctx.state)` as `_chip(seg, focused=False, parked=True)`.
   Renders the literal text `"OFF-TRAY:"` as section header (used by PTY
   tests as a render marker). `border_title = "Off Tray"`.

4. **Preview panel** (`#board-preview`): placeholder `Static` widget wired to
   display preview output (Task 6). `border_title = "Preview"`.

Key bindings (all active only when `_gate_done = True`):
- `left` → if focused chip is in the Off Tray (i.e., in `engine.off_tray(ctx.state)`),
  this is a **no-op** (left/right do not apply to tray chips); otherwise call
  `engine.layout_move(ctx.state, focused_seg, "left")` → update `ctx.state`,
  `_schedule_preview()`, `refresh()`
- `right` → same no-op guard as `left`; otherwise
  `engine.layout_move(ctx.state, focused_seg, "right")`
- `up` → `engine.layout_move(ctx.state, focused_seg, "up")` → update,
  `_schedule_preview()`, `refresh()`. When the focused chip is in the Off
  Tray, `engine.layout_move` already returns the state unchanged (tray maps
  to None in up_map); callers need not guard separately — just call and apply
  the returned state.
- `down` → same as `up` — engine handles the tray-is-None guard.
- `space` → `engine.layout_toggle(ctx.state, focused_seg)` → update,
  `_schedule_preview()`, `refresh()`; after toggle, if the chip moved to tray,
  advance `_focused_seg` to the next chip in lane order; if moved from tray
  to lane, keep it focused.
- `tab` → cycle `_focus_panel` forward: `(self._focus_panel + 1) % 4`
- `shift+tab` → cycle `_focus_panel` backward: `(self._focus_panel - 1) % 4`
- `r` → reset layout to LAYOUT_DEFAULTS:
  ```python
  import copy
  ctx.state["layout"] = copy.deepcopy(LAYOUT_DEFAULTS)
  self._focused_seg = ctx.state["layout"][0]["segments"][0]
  self._schedule_preview()
  self.refresh()
  ```
  `LAYOUT_DEFAULTS` must be imported/accessible in `wizard_app.py` via
  `ctx.engine` (e.g., `ctx.engine.layout_defaults()` returns a fresh deep
  copy) OR defined as a module-level constant matching `setup.LAYOUT_DEFAULTS`.
  Either approach is acceptable; document the chosen one in the implementation.
- `enter` → post `AdvanceStep(STEP_REVIEW)` message to parent App (only when
  `_gate_done = True`)

**Off-tray move-key no-op specification:**
- `left`/`right` bindings check `focused_seg in engine.off_tray(ctx.state)`;
  if True, return immediately without calling `engine.layout_move`.
- `up`/`down` delegate to the engine, which uses up_map/down_map where the
  tray zone (3) maps to None — the engine returns the state unchanged. No
  extra guard needed in the widget for vertical moves.

`_toggle_chip()` off→on placement: `engine.layout_toggle` already places chips
on `layout[0]["segments"]` (home line = first line). Callers do not replicate
this logic.

`on_mount` must fire `_schedule_preview()` (Task 6 hook — safe to stub as
`pass` in Task 4; wired in Task 6). After mount, `_preview_epoch == 1`.

**Acceptance tests (unit):**
- `TestLayoutBoard.test_arrow_moves_focused_chip` — mount board, send `right`,
  assert focused chip moved one position right in lane 0.
- `TestLayoutBoard.test_up_cross_line` — with a chip on line 1, send `up`,
  assert chip is now in line 0.
- `TestLayoutBoard.test_space_to_tray` — send `space`, assert chip appears in
  `engine.off_tray(ctx.state)`.
- `TestLayoutBoard.test_focus_glyph` — assert `#board-label` contains
  `[>path<]` for the focused chip and `[model]` (no brackets) for unfocused.
- `TestLayoutBoard.test_r_resets_layout` — seed a non-default layout, send
  `r`, assert `ctx.state["layout"]` equals `LAYOUT_DEFAULTS`.
- `TestLayoutBoard.test_shift_tab_reverses_panel_cycle` — send `tab` then
  `shift+tab`, assert `_focus_panel` returns to its original value.
- `TestLayoutBoard.test_left_right_noop_in_tray` — move a chip to tray, send
  `left`, assert `ctx.state["layout"]` is unchanged (engine not called with
  "left").

Use `_fake_ctx_layout()` helper from the existing test file (which uses real
`setup` engine functions). All must pass with `app.run_test()` pilot.

**Definition of done:** gate green; all `TestLayoutBoard` tests green; seam
test green; `_preview_epoch == 1` after mount; adoption gate prompt fires for
"unset" and "foreign" status_line states.

---

## Task 5 — Review screen (SummaryScreen)

**Goal:** Implement `SummaryScreen` (a `Screen` subclass — it IS a pushed
screen, the final confirm step) showing the "Review & confirm" summary and the
`EmptyConfirmModal`. Wire Enter to commit the result and pop back to the app.
The adoption gate has already been handled in Task 4 (STEP_ARRANGE opening);
`SummaryScreen` is Review-only.

**Files changed:** `tools/wizard_app.py`

**Exact work:**

`SummaryScreen(Screen)` — a modal-style screen pushed via `app.push_screen`.
On mount it calls `_build_summary_text(ctx)` and renders the result in a
scrollable `Static`. The summary text includes:
- A "Skills / Agents / Commands" section listing enabled picks, grouped by
  category, from `ctx.selection.enabled_map()`.
- A "Status line" section showing the current `ctx.status_line["state"]` and
  the planned action (adopt / skip), derived from `ctx.state["adopt"]` which
  was already set by the Task 4 adoption gate.
- A layout preview: for each layout line, the enabled segments in line order.

**Nothing-to-do guard:** Before committing, check whether the wizard would
make any net change. The guard blocks `enter` (shows `EmptyConfirmModal` with
a different message) when ALL of:
  1. No net component change: the CURRENT selection's enabled map equals the
     snapshot taken at wizard launch. The snapshot is written by
     `setup.launch_wizard` into `state["_initial_enabled"]` (see Task 9 —
     `launch_wizard` builds it from `sel.items` right after constructing
     `sel = Selection(...)`, BEFORE handing `state` to `WizardContext`).
     Both sides of the comparison MUST use the identical key shape: a
     `{(category, name): on}` dict built from `Selection.items` (a list of
     `[category, name, on]` entries) — NOT `Selection.enabled_map()`, whose
     `{name: on}` shape collapses same-named items across categories and
     would make the comparison meaningless.
  2. Status line is skipped: `ctx.state["adopt"] == False`.

Implementation:

```python
def _has_net_change(self, ctx: WizardContext) -> bool:
    """True if the wizard would produce any write."""
    initial = ctx.state.get("_initial_enabled", {})
    current = {(cat, name): on for cat, name, on in ctx.selection.items}
    component_changed = current != initial
    adopt = ctx.state.get("adopt", False)
    return component_changed or adopt
```

`EmptyConfirmModal(ModalScreen)` — a modal pushed when `_has_net_change`
returns False (nothing to do) OR when selection is empty. It renders an
appropriate warning:
- If empty picks and no externals: "Nothing selected — confirm abort?"
- If no net change and adopt=False: "No changes — nothing to write. Confirm exit?"

Two options in both cases: "Continue editing" (Esc) or "Confirm" (Enter).
On "Confirm" it posts `ConfirmEmpty` message to parent.

Key bindings on `SummaryScreen`:
- `enter` → call `_has_net_change(ctx)`; if False, push `EmptyConfirmModal`;
  if selection is empty and no external segments enabled, also push
  `EmptyConfirmModal`; otherwise commit result: set `app._result =
  WizardResult(selection=ctx.selection, state=ctx.state)` and call
  `app.exit()`.
- `escape` → pop screen (back to STEP_ARRANGE).
- `q` → abort: set `app._result = None` and call `app.exit()`.

**Acceptance tests (unit):**
- `TestConfirm.test_enter_shows_summary` — push SummaryScreen, verify "Install
  Summary" text renders.
- `TestConfirm.test_enter_commits_result` — push SummaryScreen with non-empty
  selection and `adopt=True`, send Enter, assert `app._result` is a `WizardResult`.
- `TestConfirm.test_escape_pops_to_arrange` — push SummaryScreen, send Esc,
  assert app is back at STEP_ARRANGE (or the board is visible).
- `TestConfirm.test_empty_selection_shows_modal` — push SummaryScreen with
  all picks disabled, send Enter, assert `EmptyConfirmModal` is on screen.
- `TestConfirm.test_no_net_change_shows_modal` — seed `state["_initial_enabled"]`
  with `{(cat, name): on for cat, name, on in selection.items}` taken from the
  same `selection` passed to the context (no change applied after the seed),
  push SummaryScreen with `adopt=False`, send Enter, assert `EmptyConfirmModal`
  is on screen.
- `TestConfirm.test_component_change_bypasses_guard` — seed
  `state["_initial_enabled"]` the same way, then flip one item's `on` flag on
  `selection.items` (so `current != initial`), push SummaryScreen with
  `adopt=False`, send Enter, assert `app._result` is committed (no modal).

All must pass with `app.run_test()` pilot.

**Definition of done:** gate green; all `TestConfirm` tests green; seam test
green; adoption gate is NOT in SummaryScreen (handled by Task 4); nothing-to-do
guard covers both no-net-change AND adopt=False together.

---

## Task 6 — Live preview worker (epoch-guarded, debounced)

**Goal:** Wire the preview panel in `LayoutBoard` to call
`engine.render_preview(segments, layout)` in a background thread, debounced
100 ms, epoch-guarded to discard stale results. The preview displays the real
renderer output (or an "unavailable" sentinel on failure) in `#board-preview`.

**Files changed:** `tools/wizard_app.py`

**Exact work:**

Add `_PREVIEW_DEBOUNCE_SECS: float = 0.1` at module level.

In `LayoutBoard`, add:
- `self._preview_epoch: int = 0` (initialized to 0 in `__init__`; set to 1
  by `on_mount` via first `_schedule_preview()` call).

`_schedule_preview(self) -> None`:
```python
def _schedule_preview(self) -> None:
    self._preview_epoch += 1
    epoch = self._preview_epoch
    self.set_timer(_PREVIEW_DEBOUNCE_SECS, lambda: self._run_preview(epoch))
```

`_run_preview` is decorated `@work(thread=True, exclusive=True, exit_on_error=False)`:
```python
@work(thread=True, exclusive=True, exit_on_error=False)
def _run_preview(self, epoch: int) -> None:
    if epoch != self._preview_epoch:
        return                       # stale — discard
    segments = {
        k: bool(v) for k, v in self._ctx.state["segments"].items()
    }
    layout = self._ctx.state["layout"]
    try:
        text = self._ctx.engine.render_preview(segments, layout=layout)
    except Exception:  # noqa: BLE001
        text = "— preview unavailable —"
    if epoch == self._preview_epoch:
        self.call_from_thread(self._update_preview, text)
```

`_update_preview(self, text: str) -> None`:
```python
def _update_preview(self, text: str) -> None:
    preview = self.query_one("#board-preview", Static)
    preview.update(text or "— preview unavailable —")
```

**Full call chain:** The only call sites for `_run_preview` are the timer
lambdas created by `_schedule_preview`. No other code calls `_run_preview`
directly. The chain is:

```
_schedule_preview()
  → self._preview_epoch += 1
  → epoch = self._preview_epoch          # snapshot the current epoch value
  → self.set_timer(0.1, lambda: self._run_preview(epoch))
      → [timer fires after 100ms] → _run_preview(epoch)
          → if epoch != self._preview_epoch: return  # stale guard
          → engine.render_preview(segments, layout=layout)   # @work thread
          → self.call_from_thread(self._update_preview, text)
              → _update_preview(text)
                  → self.query_one("#board-preview", Static).update(text)
```

Call `_schedule_preview()` from:
- `on_mount` (first preview after board mounts; sets epoch to 1)
- After every `left`/`right`/`up`/`down` move
- After every `space` toggle
- After `r` reset

The `CC_AI_KIT_CONFIG_FILE` environment variable: `engine.render_preview` in
`setup._engine_ns` already handles writing the temp TOML and passing it to
`status-line.py` via environment — `wizard_app.py` does NOT set env vars or
manage temp files directly.

**Acceptance tests (unit):**
- `TestPreview.test_preview_widget_exists` — mount board, assert
  `#board-preview` widget is present.
- `TestPreview.test_toggle_updates_preview` — send `space`, assert
  `_schedule_preview` was called (check `_preview_epoch` incremented).
- `TestPreview.test_unavailable_sentinel` — mock `engine.render_preview` to
  raise `RuntimeError`, fire preview, assert widget text contains "unavailable".
- `TestPreview.test_epoch_guard` — send three rapid moves, assert
  `_preview_epoch == 4` (1 from mount + 3 moves); assert only the final
  preview result is applied (stale calls do not update widget).

All must pass with `app.run_test()` pilot using `IsolatedAsyncioTestCase`.

**Definition of done:** gate green; all `TestPreview` tests green; `_preview_epoch == 1`
after mount; seam test green.

---

## Task 7 — Fail-closed guards (tty, uv, textual, terminal size, crash handler)

**Goal:** Implement and harden all fail-closed guards: tty check in
`run_wizard`, terminal-size check, unhandled-exception handler that sets
`app._exception` and exits the app, and the `WizardCrash` propagation in
`run_wizard`. Verify the no-tty PTY E2E path.

**Files changed:** `tools/wizard_app.py` (crash handler); `tools/setup.py`
(ensure_rich_runtime, require_tty — review only; no change needed if already
correct); `tests/test_wizard_app.py` (crash safety tests); `tests/test_wizard_pty.py`
(Phase-1 E2E tests must remain green).

**Exact work:**

`run_wizard(ctx)` must:
1. Check `shutil.get_terminal_size()` — if `cols < 40 or rows < 10`, raise
   `WizardCrash(f"terminal too small: {cols}x{rows} (need 40x10)")`.
2. Instantiate `WizardApp(ctx)` and call `.run()` synchronously.
3. If `app._exception is not None`, raise `WizardCrash(str(app._exception))`
   (wraps any unhandled exception from inside the Textual run loop).
4. Return `app._result` (`WizardResult` or `None`).

`WizardApp.on_exception(exception: BaseException) -> None` (Textual lifecycle
hook — called by the framework on any unhandled exception during the run loop):
```python
def on_exception(self, exception: BaseException) -> None:
    self._exception = exception
    self.exit()
```

This ensures exceptions from workers or event handlers do not silently swallow
into Textual's log.

The `require_tty` / `open_tty` / `ensure_rich_runtime` guards live in
`setup.py` and are already implemented. Do NOT duplicate them in `wizard_app.py`.
Task 7 only verifies that `wizard_app.py`'s own exception contract is correct.

LANE_GATE enforcement (terminal-rows gate for layout lines): The LayoutBoard
renders LANE_GATE keys as visual hints (grayed-out row header with "needs N
rows") but does NOT suppress segments — the renderer itself handles row gating.
This means Task 7 does not add row-gating logic to the board; it documents
this as a known non-enforcement (the gate is cosmetic / informational).

**Acceptance tests (unit):**
- `TestCrashSafety.test_exception_raises_wizard_crash` — mock Textual run to
  raise `RuntimeError("boom")`; assert `run_wizard` raises `WizardCrash`.
- `TestCrashSafety.test_small_terminal` — monkeypatch `shutil.get_terminal_size`
  to return `(10, 5)`; assert `run_wizard` raises `WizardCrash` with "too small"
  in the message.

PTY E2E (must remain green):
- `TestPhase1E2E.test_no_tty_exits_nonzero_with_reason` — spawn without a tty,
  assert exit non-zero and "terminal" in output.
- `TestPhase1E2E.test_interactive_under_pty_runs_to_completion` — spawn under
  PTY, drive `q`, assert "summary:" in output and exit 0.

Run with: `uv run python -m unittest tests.test_wizard_app tests.test_wizard_pty`

**Definition of done:** gate green; crash safety tests green; PTY Phase-1
E2E tests green; seam test green.

---

## Task 8 — Keyboard navigation contract (Esc=Back, q=Quit, ?=Help)

**Goal:** Wire the full keyboard contract: `Esc` navigates back one step (from
Arrange → Choose, from Summary → Arrange; from Choose → abort/quit); `q`
aborts the wizard at any step (exit 0, config intact); `?` shows a help modal
with the current step's key legend. Footer key-bar updates per step.

**Files changed:** `tools/wizard_app.py`

**Exact work:**

`WizardApp.action_back(self) -> None`:
- On `STEP_CHOOSE`: equivalent to Quit (abort; `self._result = None; self.exit()`).
- On `STEP_ARRANGE`: swap body back to `_PicksScreen` and update step to
  `STEP_CHOOSE`.
- On `STEP_REVIEW` (`SummaryScreen` pushed): pop the screen
  (`self.pop_screen()`), returning to the board.
- On `STEP_DONE`: no-op (wizard already finished).

`WizardApp.action_quit(self) -> None`:
- At any step: `self._result = None; self.exit()`.
- Exit code 0 (Textual's default for `self.exit()` without an error).

`WizardApp.action_help(self) -> None`:
- Pushes a `HelpModal(ModalScreen)` that renders the current step's `HELP`
  entry (defined in Task 1) as a formatted key legend. `Esc` or `q` dismisses
  the modal (calls `self.dismiss()`).

`HelpModal(ModalScreen)`:
- Receives `step: int` in `__init__`.
- Renders `HELP[step]` as a two-column table: key column | description
  column. `HELP` (not `FOOTERS`) is the source here because it carries the
  full key legend, including bindings the footer omits for space (e.g.
  `STEP_CHOOSE`'s `A/N` global all/none, `STEP_ARRANGE`'s off-tray semantics
  on `↑`).
- `BINDINGS = [("escape", "dismiss"), ("q", "dismiss"), ("?", "dismiss")]`

Footer update: after each step transition, call `self.query_one(WizardFooter).update_step(new_step)`.
`WizardFooter.update_step(step: int)` re-renders the footer bar using
`FOOTERS[step]`.

Step-transition message: define `AdvanceStep(Message)` with `step: int` field.
`WizardApp.on_advance_step(msg: AdvanceStep)` swaps the body widget to the
appropriate step body (or pushes `SummaryScreen` for STEP_REVIEW), then
updates the header and footer.

**Acceptance tests (unit):**
- `TestWizardApp.test_abort_via_q` — mount app, send `q`, assert `app._result is None`
  and app exited with code 0.
- `TestWizardApp.test_abort_via_escape` — mount at STEP_CHOOSE, send `Esc`,
  assert app aborted (equivalent to Quit from first step).
- Add a `test_esc_from_arrange_goes_to_choose` — mount app, advance to
  STEP_ARRANGE, send `Esc`, assert current step body is `_PicksScreen`.
- Add a `test_help_modal_appears` — send `?`, assert a `HelpModal` is mounted.
- Add a `test_help_modal_renders_help_dict` — mount `HelpModal(STEP_CHOOSE)`,
  assert the rendered text contains the `A/N` global all/none row from
  `HELP[STEP_CHOOSE]` (content that `FOOTERS[STEP_CHOOSE]` does not carry),
  proving `HelpModal` reads `HELP`, not `FOOTERS`.

All must pass with `app.run_test()` pilot.

**Definition of done:** gate green; navigation tests green; `q` always exits 0
with `_result = None`; seam test green.

---

## Task 9 — WizardContext population and segment-meta sourcing

**Goal:** Verify end-to-end that `WizardContext` is populated correctly in
`setup.launch_wizard` — specifically that `status_line`, `segment_meta`, and
`external_segments` are built from real sources (not defaults or fakes), and
that `TestWizardContextShape` assertions pass. This task ALSO adds the one
concrete code change `launch_wizard` is still missing: capturing the initial
component-selection snapshot into `state["_initial_enabled"]` so Task 5's
`_has_net_change` guard has a real baseline to compare against (today nothing
writes that key, so the guard always falls back to `{}`).

**Files changed:** `tools/setup.py` (`launch_wizard` — add the
`_initial_enabled` snapshot line; otherwise read-only verification, only fix
further if `TestWizardContextShape` fails due to a setup bug);
`tests/test_wizard_app.py` (may need helper fixes or additional assertions).

**Exact work:**

In `launch_wizard` (`tools/setup.py`), immediately after constructing
`sel = Selection(...)` (~line 1708) and before building the `state` dict
passed to `WizardContext`, snapshot the initial enabled state of every
`(category, name)` item using the SAME key shape `_has_net_change` (Task 5)
will compare against:

```python
sel = Selection(
    (cat, name, name in default[cat])
    for cat in CATEGORIES
    for name, _ in entries[cat]
)
initial_enabled = {(cat, name): on for cat, name, on in sel.items}
```

Then add the key to the `state` dict literal passed into `WizardContext`:

```python
ctx = wizard_app.WizardContext(
    selection=sel,
    state={"segments": segments,
           "layout": current_layout(paths.config_toml), "dirty": False,
           "adopt": sl_state["state"] == "ours",
           "_initial_enabled": initial_enabled},
    ...
)
```

This is the ONLY write site for `state["_initial_enabled"]` — it is written
once, here, at construction time, and read once, in Task 5's
`_has_net_change`. Both sides use `{(cat, name): on}` built from
`Selection.items` (`[category, name, on]` entries), so the comparison in
Task 5 is meaningful — not a vacuous `{} == {}` fallback.

Confirm that `WizardContext` as constructed in `launch_wizard` satisfies the
field contract `TestWizardContextShape` asserts:

```
ctx.status_line  == {"state": "unset"|"ours"|"foreign", "current_command": str|None}
ctx.segment_meta == {key: {"description": str, "sample": str, "icon": str, "line": int}}
ctx.external_segments == [{"id": str, "name": str, "path": str, "description": str,
                           "icon": str, "sample": str, "line": int, "provenance": str, ...}]
ctx.state["adopt"]  # bool — True iff status_line["state"] == "ours"
ctx.state["_initial_enabled"]  # {(category, name): bool} — snapshot of sel.items
                                # at construction time; see above.
```

From reading `launch_wizard` (lines 1675–1772 of `setup.py`):
- `sl_state = detect_statusline(paths)` — provides `status_line`
- `segment_meta = build_segment_meta(inventory, overrides)` — built from
  `load_segment_inventory(INVENTORY_PATH)` + `_statusline_icon_line_overrides`
- `external = discover_external_segments(paths, examples_dir)` — provides
  `external_segments`
- `ctx.state["adopt"] = sl_state["state"] == "ours"` — correct initial adopt flag

`TestWizardContextShape` in `test_wizard_app.py` verifies these shapes. If any
assertion fails, the fix is in `setup.launch_wizard` or the test helper
`_fake_ctx()`, not in `wizard_app.py`.

The `adopt` flag in `ctx.state`: `launch_wizard` sets it as
`"adopt": sl_state["state"] == "ours"`. On a fresh install where detect returns
`"unset"`, `adopt` starts `False`. On reconfigure where the status line is
already ours, it starts `True`. `SummaryScreen` (Task 5) may flip `adopt` to
`True` via the adoption-gate prompt.

Externals default-off contract: `launch_wizard` uses
`_external_enabled_in_toml(paths.config_toml, e["id"])` — NOT `e["default_on"]`
— so externals are never pre-checked based on metadata alone. This is the
Task 10 constraint enforced by setup; wizard_app.py need not re-enforce it.

**Acceptance tests (unit):**
- `TestWizardContextShape.test_status_line_field_shape` — passes.
- `TestWizardContextShape.test_segment_meta_field_shape` — passes.
- `TestWizardContextShape.test_external_segments_field_shape` — passes.
- `TestWizardContextShape.test_adopt_flag_initial_value` — passes.
- `TestWizardContextShape.test_initial_enabled_snapshot` — calls
  `launch_wizard`'s context-construction path (or the equivalent test helper
  that builds a real `Selection` + calls into the same snapshot logic) and
  asserts `ctx.state["_initial_enabled"] == {(cat, name): on for cat, name, on
  in ctx.selection.items}` — i.e. the snapshot taken at construction time
  equals the selection's enabled state at that same moment.

Run with: `uv run python -m unittest tests.test_wizard_app`

**Definition of done:** gate green; all `TestWizardContextShape` tests green
including `test_initial_enabled_snapshot`; seam test green; the only
`wizard_app.py`-adjacent change in this task is the `setup.py` snapshot line
above — `wizard_app.py` itself is unchanged (the read site lives in Task 5).

---

## Task 10 — PTY E2E Phase-2/3 and curl-bash path

**Goal:** Ensure all PTY E2E test classes pass end-to-end: Phase-2
(confirm → symlinks created), Phase-3 (arrange → TOML reflects; reconfigure
pre-loads), and curl-bash (piped stdin + PTY ctty). These tests exercise the
full `setup.py → wizard_app.py → persist_statusline` pipeline. Identify and
fix any integration gaps exposed by the E2E tests.

**Files changed:** `tests/test_wizard_pty.py` (add/fix test helpers if needed);
`tools/setup.py` (fix integration gaps only); `tools/wizard_app.py` (fix
integration gaps only).

**Exact work:**

The E2E tests in `test_wizard_pty.py` already exist (Phase-1/2/3 and
curl-bash). Task 10 runs them and resolves any failures caused by Plan-B UI
changes.

Known integration contracts verified by the PTY tests:

1. **Phase-2** (`TestPhase2E2E.test_pick_skill_and_confirm_creates_symlink`):
   - Picks screen renders `◉` glyph (UTF-8 `\xe2\x97\x89`).
   - Enter on picks advances to SummaryScreen (renders "Install Summary").
   - Enter on SummaryScreen calls `apply_selection` → symlinks created.
   - Assert: `<cfg>/skills/applying-review-feedback` symlink exists.

2. **Phase-3 Scenario 1** (`TestPhase3E2E.test_arrange_confirm_skips_statusline_when_not_adopted`):
   - Tab from picks advances to LayoutBoard (renders "identity line:").
   - Space toggles "path" chip to Off tray (renders "OFF-TRAY:").
   - Enter from board → SummaryScreen → Enter → confirm.
   - Assert: NO `statusline.toml` written (adopt=False, status_line="unset").
   - Assert: `settings.json` has NO `statusLine` key.
   - Assert: skill symlinks ARE created (component install is independent of adopt).

3. **Phase-3 Scenario 2** (`TestPhase3E2E.test_reconfigure_preloads_saved_arrangement`):
   - Pre-seed `statusline.toml` with `path = false`.
   - Spawn `reconfigure`, tab to board, assert "OFF-TRAY:" in output.
   - Assert `path` chip appears as `(path)` or `[>path<]` in tray.

4. **curl-bash** (`TestCurlBashE2E.test_piped_stdin_wizard_still_driven_via_dev_tty`):
   - Spawn with piped stdin (`spawn_pty_piped_stdin`); ctty = PTY.
   - Wizard renders (ANSI / `◉` / "summary:" in output).
   - `q` via PTY master exits 0.

If Phase-3 tests fail because the LayoutBoard does not render `"identity line:"`
or `"OFF-TRAY:"` as literal text in the terminal output, add those as explicit
label texts in the board rendering (they are currently the `_ROW_LABELS` entry
and the Off-tray section header — ensure they render as plain text, not only
as Rich markup that might be stripped by PTY capture).

The `spawn_pty` / `spawn_pty_piped_stdin` / `drive_until` / `_drain` helpers
in `test_wizard_pty.py` are already implemented. No changes to these helpers
unless a Phase-1 test regresses.

**Acceptance tests (PTY E2E):**
All four PTY test classes must pass:
- `TestPhase1E2E` (2 tests)
- `TestPhase2E2E` (1 test)
- `TestPhase3E2E` (2 tests)
- `TestCurlBashE2E` (1 test)

Run with: `uv run python -m unittest tests.test_wizard_pty`

Gate must also be green: `uv run pre-commit run --all-files`

**Definition of done:** gate green; all PTY E2E tests green; unit tests green;
seam test green; `_protodata` never imported; render path untouched.

---

## Task 11 — Reconcile legacy example-segment install path (I-1)

**Goal (I-1):** After the wizard returns, `cmd_install` currently runs a
SEPARATE legacy `discover_example_segments` (bundled-only) +
`select_examples` (which RE-PROMPTS at the terminal in interactive mode) +
`install_example_segments` — ignoring the wizard's own external-segment
decisions stored in `result.state["segments"]` and causing a DOUBLE-PROMPT for
interactive installs. Reconcile so the interactive (wizard) path drives
external-segment install from `result.state` (no second prompt), while the
NONINTERACTIVE `--examples` flag path keeps using `select_examples`.

**Current code in `cmd_install` (tools/setup.py ~lines 1799–1812):**

```python
# A: choose what to install + segment layout via Textual wizard (Task 2.1+).
launch_wizard(paths, entries, installed, tty, dry, counts)

# Example external segments (system_memory, …): offer pre-checked when interactive,
# else governed by --examples (default ON). Copy+chmod+enable; default-ON
# means the copied provider renders without an explicit toggle write.
examples = discover_example_segments(
    os.path.join(paths.install_dir, "examples", "segments"))
if examples:
    chosen = select_examples(examples, examples_flag, tty)
    if chosen and not dry:
        ids = install_example_segments(chosen, paths.config_dir)
        print(f"examples: installed {len(ids)} external segment(s): "
              f"{', '.join(ids)}")
```

**Problem:** `launch_wizard` returns `None` (abort/Esc) or implicitly after
applying the wizard result. The `result` is consumed inside `launch_wizard`
and never surfaced back to `cmd_install`, so `cmd_install` cannot inspect the
wizard's `result.state["segments"]` decisions. The legacy block then calls
`select_examples` unconditionally — which for an interactive run (tty present,
`examples_flag=None`) returns `list(examples)` (ALL examples), overriding any
wizard deselections.

**Files changed:**
- `tools/setup.py` — `launch_wizard` signature (return the `result` so
  `cmd_install` can read `result.state`); `cmd_install` post-wizard block
  (branch on whether the wizard ran and returned a result)
- `tests/test_setup.py` — new tests for the double-prompt fix
- `tests/test_wizard_pty.py` — update any assertion that relied on the legacy
  select_examples prompt appearing after the wizard (if present)

**Implementation approach:**

The cleanest fix with minimal blast-radius:

1. Make `launch_wizard` return its `result` (`WizardResult | None`) so
   `cmd_install` can inspect `result.state["segments"]`.

2. In `cmd_install`, capture the return value of `launch_wizard`:

```python
result = launch_wizard(paths, entries, installed, tty, dry, counts)
```

3. After the wizard call, branch on whether the wizard ran interactively
   (result is not None — it ran and the user confirmed) vs. the noninteractive
   `--examples` path:

```python
examples = discover_example_segments(
    os.path.join(paths.install_dir, "examples", "segments"))
if examples:
    if result is not None:
        # Interactive path: wizard already captured external-segment decisions
        # in result.state["segments"]. Drive install from those toggles —
        # no second prompt.
        seg_state = result.state["segments"]
        chosen = [e for e in examples if seg_state.get(e["id"], False)]
    else:
        # Noninteractive / --examples flag path: wizard did not run (abort) or
        # examples_flag governs. Fall back to select_examples.
        chosen = select_examples(examples, examples_flag, tty)
    if chosen and not dry:
        ids = install_example_segments(chosen, paths.config_dir)
        print(f"examples: installed {len(ids)} external segment(s): "
              f"{', '.join(ids)}")
```

4. Update `launch_wizard` to `return result` at the end:

```python
    # … existing apply_selection + persist_statusline code …
    return result   # propagate wizard result to cmd_install (I-1)
```

And at the abort path: the existing `if result is None: return` must become
`if result is None: return None` (semantically identical; explicit for clarity).

**Exact work — TDD steps:**

**Step 1 — Read and confirm current code.**

Before writing tests, read `tools/setup.py` around `launch_wizard` (return
value) and the `cmd_install` post-wizard block (~lines 1799–1812) to confirm
exact line numbers and variable names match what is described here.

**Step 2 — Failing tests.**

Add to `tests/test_setup.py` (new class `TestCmdInstallExternalReconcile`).
The new test class requires the following imports, which may not all be present
at the top of `test_setup.py` — add any that are missing:

```python
import os
import types
import unittest
from unittest import mock

from tools import setup
```

`unittest` and `mock` are already used in `test_setup.py` (`unittest.TestCase`,
`mock.patch`). `os` is used for `os.environ.copy()` in the test body. `types`
is used for `types.SimpleNamespace` in `_fake_result`. Confirm these are present
in the file's import block before adding the class; do not duplicate imports.

```python
class TestCmdInstallExternalReconcile(unittest.TestCase):
    """I-1: wizard result drives external-segment install; no double-prompt."""

    def _fake_result(self, seg_state):
        """Build a minimal WizardResult-shaped object (NamedTuple) with the
        given segments state dict."""
        from tools import setup as s
        # wizard_app.WizardResult is a NamedTuple(selection, state)
        # We import it lazily to avoid the seam (wizard_app not loadable
        # without uv; use a SimpleNamespace stand-in for the test).
        import types
        return types.SimpleNamespace(
            selection=None,
            state={"segments": seg_state, "layout": [], "dirty": False, "adopt": False}
        )

    @mock.patch.object(setup, "install_example_segments", return_value=["system_memory"])
    @mock.patch.object(setup, "select_examples")
    @mock.patch.object(setup, "discover_example_segments")
    def test_interactive_install_uses_wizard_state_not_select_examples(
        self, mock_discover, mock_select, mock_install
    ):
        """When wizard returned a result, install_example_segments is called
        with exactly the wizard-enabled segments; select_examples is NOT called."""
        mock_discover.return_value = [
            {"id": "system_memory", "name": "System memory",
             "path": "/fake/system_memory", "filename": "system_memory",
             "default_on": True, "description": "", "icon": "💻",
             "sample": "", "line": 0, "provenance": "bundled"},
        ]
        # Simulate wizard: user ENABLED system_memory.
        fake_result = self._fake_result({"system_memory": True})

        # Invoke just the post-wizard example block logic. We call it via
        # cmd_install with launch_wizard mocked to return our fake result.
        with mock.patch.object(setup, "launch_wizard", return_value=fake_result), \
             mock.patch.object(setup, "resolve_paths", return_value=mock.MagicMock(
                 install_dir="/fake", config_dir="/fake/cfg",
                 claude_dir="/fake/.claude")), \
             mock.patch.object(setup, "enumerate_entries", return_value={
                 "agents": [], "commands": [], "skills": []}), \
             mock.patch.object(setup, "new_counts", return_value={}), \
             mock.patch.object(setup, "prune_stale"), \
             mock.patch.object(setup, "adopt_predecessor_links"), \
             mock.patch.object(setup, "installed_links", return_value={}), \
             mock.patch("builtins.print"):
            setup.cmd_install(os.environ.copy(), tty=mock.MagicMock(isatty=lambda: True),
                              dry=False, examples_flag=None)

        # select_examples must NOT have been called (no double-prompt).
        mock_select.assert_not_called()
        # install_example_segments IS called with the wizard-enabled segment.
        mock_install.assert_called_once()
        chosen_arg = mock_install.call_args[0][0]
        self.assertEqual([e["id"] for e in chosen_arg], ["system_memory"])

    @mock.patch.object(setup, "install_example_segments", return_value=[])
    @mock.patch.object(setup, "select_examples", return_value=[])
    @mock.patch.object(setup, "discover_example_segments")
    def test_noninteractive_flag_path_still_uses_select_examples(
        self, mock_discover, mock_select, mock_install
    ):
        """When wizard aborted (result=None), select_examples governs."""
        mock_discover.return_value = [
            {"id": "system_memory", "name": "System memory",
             "path": "/fake/system_memory", "filename": "system_memory",
             "default_on": True, "description": "", "icon": "💻",
             "sample": "", "line": 0, "provenance": "bundled"},
        ]
        with mock.patch.object(setup, "launch_wizard", return_value=None), \
             mock.patch.object(setup, "resolve_paths", return_value=mock.MagicMock(
                 install_dir="/fake", config_dir="/fake/cfg",
                 claude_dir="/fake/.claude")), \
             mock.patch.object(setup, "enumerate_entries", return_value={
                 "agents": [], "commands": [], "skills": []}), \
             mock.patch.object(setup, "new_counts", return_value={}), \
             mock.patch.object(setup, "prune_stale"), \
             mock.patch.object(setup, "adopt_predecessor_links"), \
             mock.patch.object(setup, "installed_links", return_value={}), \
             mock.patch("builtins.print"):
            setup.cmd_install(os.environ.copy(), tty=mock.MagicMock(isatty=lambda: True),
                              dry=False, examples_flag="none")

        # select_examples IS called for the noninteractive/flag path.
        mock_select.assert_called_once()
```

Run: `uv run python -m unittest tests.test_setup.TestCmdInstallExternalReconcile` → **RED** (currently `launch_wizard` returns `None` and `cmd_install` always calls `select_examples`).

**Step 3 — Implement the fix.**

Edit `tools/setup.py`:

a. In `launch_wizard`, change the abort early-return from `return` to
   `return None` (no behavioral change, just explicit) and add `return result`
   at the very end of the function (after the `persist_statusline` call).

b. In `cmd_install`, capture the return:

```python
result = launch_wizard(paths, entries, installed, tty, dry, counts)
```

c. Replace the post-wizard example block with the branched version shown in
   the Implementation approach above.

**Step 4 — Run GREEN.**

```
uv run python -m unittest tests.test_setup.TestCmdInstallExternalReconcile
uv run python -m unittest tests.test_setup
```

**Step 5 — Check test_wizard_pty.py for assertions to update.**

Scan `tests/test_wizard_pty.py` for any assertion that `select_examples` is
called or that a second prompt appears after the wizard in the interactive E2E
flow. If found, update the assertion to match the new behavior (no second
prompt). Run:

```
uv run python -m unittest tests.test_wizard_pty
```

All PTY E2E tests must remain green.

**Step 6 — Run full gate.**

```
uv run pre-commit run --all-files
```

Gate must be green.

**Step 7 — Commit.**

```
git -C <worktree> commit -m "fix(setup): interactive install uses wizard external selection (no double-prompt)"
```

**Acceptance criteria:**
- `test_interactive_install_uses_wizard_state_not_select_examples` green:
  `select_examples` is NOT called when wizard returned a result.
- `test_noninteractive_flag_path_still_uses_select_examples` green:
  `select_examples` IS called when wizard aborted (result=None).
- All existing PTY E2E tests remain green.
- `launch_wizard` returns `WizardResult | None` to its caller.
- Gate green.

**Definition of done:** gate green; `TestCmdInstallExternalReconcile` tests
green; all PTY E2E tests green; unit tests green; seam test green; render path
untouched.

---

## Self-Review

### Spec-coverage table

| PRD FR / Prototype behavior | Task(s) | Status |
|---|---|---|
| M-1 Quoted-value header parsing (shlex; `_SEG_HEADER_RE` unchanged) | T0 | Covered |
| M-2 system_memory header → real-space quoted values | T0 | Covered |
| M-3 discover_example_segments / discover_external_segments docstrings list all keys incl. filename + provenance | T0 | Covered |
| M-4 TestSelectExamples._ex comment: selection-only, intentionally omits filename | T0 | Covered |
| M-5 statusline.toml.sample documents external-segment header grammar + quoting | T0 | Covered |
| I-1 Interactive install drives external segments from wizard result (no double-prompt) | T11 | Covered |
| I-1 Noninteractive --examples flag path unchanged (select_examples still governs) | T11 | Covered |
| FR-U.1 Single-screen swappable body (avoid Enter double-fire) | T1, T3, T4, T8 | Covered |
| FR-U.2 WizardContext DI seam (engine, selection, status_line, segment_meta, external_segments) | T1, T9 | Covered |
| FR-U.3 STEP_CHOOSE picks screen (groups, glyph, toggle, cursor) | T3 | Covered |
| FR-U.3a a/n = per-category all/none (set_category); A/N = global set_all | T3 | Covered |
| FR-U.3b Live counts: per-category N/M on in group header + total X of Y in #picks-count | T3 | Covered |
| FR-U.4 STEP_ARRANGE layout board (4 panels, chip focus, left/right/up/down, space) | T4 | Covered |
| FR-U.4a Adoption gate in Step-2 body (unset→Adopt/Skip; foreign→Replace/Keep; ours→straight in) | T4 | Covered |
| FR-U.4b r reset → LAYOUT_DEFAULTS + preview refresh | T4 | Covered |
| FR-U.4c shift+tab reverse panel cycle (panel-1)%4 | T4 | Covered |
| FR-U.4d Off-tray left/right no-op; up/down engine-delegated (tray=None in up_map/down_map) | T4 | Covered |
| FR-U.5 Live preview (real renderer, debounced 100ms, @work thread, epoch guard) | T6 | Covered |
| FR-U.6 STEP_REVIEW SummaryScreen (Review-only; EmptyConfirmModal; confirm) | T5 | Covered |
| FR-U.6a Nothing-to-do guard: blocks confirm when no net component change AND adopt=False | T5, T9 | Covered |
| FR-U.7 Esc=Back, q=Quit, ?=Help per-step (HELP dict content rendered by HelpModal) | T1, T8 | Covered |
| FR-U.8 Footer key-bar per step from FOOTERS tuples | T1, T2, T8 | Covered |
| FR-U.9 Color palette (FG/DIM/LINE/ACCENT/GREEN/WARN/PINK/CYAN/KEYCAP) | T1 | Covered |
| FR-U.10 _chip() shape (focused [>…<] PINK, unfocused plain, parked DIM) | T2 | Covered |
| FR-U.11 _render_header() pips (ACCENT filled, LINE unfilled, GREEN done) | T2 | Covered |
| FR-U.12 _cap() keycap style (primary blue-on-dark, secondary gray-on-keycap) | T2 | Covered |
| FR-U.13 _render_footer() sep + right-pushed Quit | T2 | Covered |
| FR-U.14 ENABLE_COMMAND_PALETTE = False | T1 | Covered |
| FR-U.15 Textual 8.2.7 API (border_title/border_subtitle attrs, padding 1/2/4) | T1–T4 | Covered |
| FR-U.16 _move_chip_v() vertical nav (engine.layout_move) | T4 | Covered |
| FR-U.17 _toggle_chip() home-line placement (engine.layout_toggle → layout[0]) | T4 | Covered |
| FR-U.18 _cycle_focus() panel rotation (Tab: +1 mod 4; Shift+Tab: -1 mod 4) | T4 | Covered |
| FR-W.1 Fail-closed: no tty → stderr + exit non-zero | T7 | Covered |
| FR-W.2 Fail-closed: terminal too small → WizardCrash | T7 | Covered |
| FR-W.3 Fail-closed: unhandled crash → WizardCrash via on_exception | T7 | Covered |
| FR-W.4 Clean q/Esc → exit 0, config intact | T7, T8 | Covered |
| FR-W.5 writes-on-Install-only via persist_statusline (adopt-gated) | T5, T10 | Covered |
| FR-W.6 Module seam (wizard_app imports nothing from setup) | T1, T9 | Covered |
| FR-W.7 No _protodata in shipped path | T0–T11 (global constraint) | Covered |
| FR-W.8 Render path tools/status-line.py untouched | T0–T11 (global constraint) | Covered |
| FR-D.1 WizardContext.status_line shape | T9 | Covered |
| FR-D.2 WizardContext.segment_meta shape (description/sample/icon/line) | T9 | Covered |
| FR-D.3 WizardContext.external_segments shape (id/name/path/provenance/…) | T9 | Covered |
| FR-D.4 External segments default-off via TOML, not default_on metadata | T9, T10 | Covered |
| FR-D.5 SEGMENT_DEFAULTS 20 segments | T3, T9 | Covered |
| FR-D.6 LAYOUT_DEFAULTS 3 lines (min_rows 0/20/30) | T4, T9 | Covered |
| FR-D.7 LANE_GATE cosmetic hints only (renderer enforces row-gating) | T4, T7 | Covered |
| E2E C.2 #3 Interactive PTY runs to completion | T7, T10 | Covered |
| E2E C.2 #4 No-tty exits non-zero + "terminal" message | T7, T10 | Covered |
| E2E C.2 #1 partial Phase-2 confirm → symlinks created | T10 | Covered |
| E2E Addendum C Phase-3 arrange → TOML + doctor; reconfigure preloads | T10 | Covered |
| E2E curl-bash piped stdin via /dev/tty | T10 | Covered |

### Placeholder scan

No placeholders, stubs, or `TODO` / `FIXME` / `pass` are present in the task
descriptions above. All function signatures, data shapes, and code patterns are
complete and verbatim-ready. Task 4's `on_mount` `_schedule_preview()` stub is
explicitly noted as "safe to leave as `pass` until Task 6 wires it" — this is
an intentional cross-task dependency, not a placeholder; the stub is replaced
in Task 6.

### Type and interface consistency note

- `WizardContext` is a `NamedTuple` with 7 fields; field order matches
  `tests/test_wizard_app.py::TestWizardContextShape` and `setup.launch_wizard`
  exactly.
- `engine` is `types.SimpleNamespace` with callables:
  `render_preview(segments, layout=None)`, `apply_command(state, cmd)`,
  `groups(state)`, `order(state)`, `layout_move(state, seg, direction)`,
  `layout_toggle(state, seg)`, `off_tray(state)`. All return contracts are
  consistent between `setup._engine_ns` and the unit test's `_fake_ctx_layout`.
- `Selection.toggle_cursor()` is called (not `toggle(cursor_index)`) from the
  picks screen — matches the `Selection` API read from `setup.py`.
- `_preview_epoch` starts at 0 in `__init__` and becomes 1 after `on_mount`
  fires the first `_schedule_preview()` — consistent with `TestPreview`
  assertion `initial_epoch == 1`.
- `layout_move` and `layout_toggle` return `(new_state, err | None)`. Callers
  in Tasks 4 and 6 must unpack: `new_state, _err = engine.layout_move(…)` and
  update `ctx.state` from `new_state` (replacing the dict reference, since
  these functions deep-copy).
- `_chip()` focused markup uses `\[>` (escaped bracket) to produce the literal
  `[>` in terminal output — consistent with the PTY test assertion
  `"[>path<]" in all_output`.
