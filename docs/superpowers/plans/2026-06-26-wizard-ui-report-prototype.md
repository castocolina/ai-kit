# Wizard UI Re-port to Prototype — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the divergent `tools/wizard_app.py` view layer with a faithful re-port of `docs/wizard-redesign/prototypes/mockup-textual.py`, wired to real installer data, so the shipped wizard looks and behaves exactly like the locked prototype.

**Architecture:** The prototype is the binding UI contract. Port its single-`WizardApp` structure (one `compose()` laying out bordered panels per area; `_render()` toggles `.display` per step) into `tools/wizard_app.py`, **swapping `_protodata` for the injected `WizardContext`**. The view owns two lists per the prototype — `self.lines` (3 lanes, ON segments only) and `self.tray` (OFF segments) — so a segment is in exactly one place and the lane/tray duplication of the current build is structurally impossible. `setup.py` is **modified only** to add `_read_component_desc` and populate `component_meta` in `WizardContext` (Task 1); its seam (`_build_wizard_context`, `_engine_ns`, `run_wizard` entry, `WizardResult`) is otherwise untouched, and the view simply stops calling `ctx.engine.*` (those functions remain referenced inside `_engine_ns`, so no dead code is introduced). On confirm the view serializes `lines`/`tray` back into `state["segments"]` + `state["layout"]` in the exact shape `_persist_layout` already consumes.

**Tech Stack:** Python 3.12, Textual 8.2.7 (wizard-only, via `uv`), `unittest`. Render path (`tools/status-line.py`) is untouched and stays `python3 -S` stdlib-only.

## Global Constraints

- **`docs/wizard-redesign/prototypes/mockup-textual.py` is NORMATIVE, not illustrative.** Port it; do **not** re-architect. The shipped wizard MUST reproduce the prototype's widget tree: a `#headerbar` (title + step pips), a `#bodywrap` containing the per-step panels, and a `#footerbar` (keys + quit). **Arrange MUST have three SEPARATE bordered lane panels** (`#lane0`, `#lane1`, `#lane2`), a `#focchip` panel, a `#tray` panel, and a `#preview` panel — never one collapsed container.
- **Two-list model (view-owned):** `self.lines: list[list[str]]` (length 3, ON segments per lane) and `self.tray: list[str]` (OFF segments). A segment appears in `lines` XOR `tray` — **never both**. There is no "not in layout" group rendered to the user.
- **Every chip carries its icon.** Chip label is `"{icon} {seg}"` (built-in icon from `ctx.segment_meta[seg]["icon"]`; external icon from the external entry, falling back to `●`).
- **Choose (step 0) shows COMPONENTS ONLY.** No segment rows, no external rows on the Choose screen. Externals are status-line segments → they live on Arrange (step 1) only.
- **`Tab` on Choose is a no-op** (the focus stays on Choose; `Tab`/`⇧Tab` cycle chip focus on Arrange only, matching the prototype and the footer/help text).
- **Preview is the styled MOCK** built from `ctx.segment_meta[seg]["sample"]` + icon (and external `sample`), laid out per-lane as `{icon} {sample} | {icon} {sample}` with a `N on · M off` footer. Do **not** shell out to `status-line.py` for the preview (segments like git branch/worktree/memory read the live environment, which is empty/broken when the installer runs outside a git repo or before any Claude context exists). *This constraint supersedes the PRD's prior live-preview binding invariant per the 2026-06-26 product decision; `docs/prds/wizard-ux-redesign-v1.0-prd.md` Binding Invariants has been amended accordingly.*
- **External distinction (net-new vs prototype):** external chips are visually marked — prefixed with `◆ ` and colored `CYAN` (active) so the user can tell an external segment from a built-in one at a glance. The detail/`#focchip` panel shows `external · <provenance>` for externals.
- **Full 4-step flow:** Choose → Arrange → Review → Done (the prototype's `STEP_CHOOSE/ARRANGE/REVIEW/DONE`). Review and Done both use the prototype's bordered-panel design. The real install runs on confirm; the user lands on Done.
- **Adoption gate (Plan-B, not in prototype) is preserved on Arrange entry:** `status_line["state"]=="ours"` → adopt silently (skip gate); `"unset"` → "Wire status line? [Y/n]" (Enter = Yes); `"foreign"` → show current command + "Replace with ai-kit? [y/N]" (Enter = No). The answer sets `self.state["adopt"]`.
- **`setup.py` is modified ONLY to supply real component descriptions (Task 1 only).** All other changes are in `tools/wizard_app.py` and the test files. The seam contract — `WizardContext` fields, `WizardResult(selection, state)`, `run_wizard(ctx)`, the terminal-size guard, `WizardCrash`, `on_exception` — is preserved exactly.
- **Components (`ctx.selection`) and segments (`state["segments"]`) are SEPARATE namespaces.** Choose mutates `ctx.selection` only. Arrange mutates `lines`/`tray` only. The old `_sync_selection_to_state` (which polluted `state["segments"]` with component names) MUST NOT be reintroduced.
- **Gate:** `uv run pre-commit run --all-files` (== `make validate`) must pass. Wizard unit/PTY tests run via `uv run python -m unittest tests.test_wizard_app tests.test_wizard_pty`. Render-path purity, module seam (wizard_app imports nothing from setup.py), and stdlib-only render path are unchanged.
- **Output language: English** for all code, comments, commit messages, and reports.

---

## File Structure

| File | Responsibility | Change |
|---|---|---|
| `tools/wizard_app.py` | The entire wizard view, ported from the prototype, wired to `WizardContext`. Single `WizardApp`; view-owned `lines`/`tray`; mock preview; adoption gate; external distinction; confirm → `_serialize_state` → `WizardResult`. | **Rewrite** |
| `tests/test_wizard_app.py` | Unit/`run_test` coverage of the new view: structure (the anti-divergence **structural gate test**), Choose, Arrange (move/toggle/gate/external), Review writeback, Done, header/footer/help. | **Rewrite** |
| `tests/test_wizard_pty.py` | End-to-end PTY drive of the new 4-step flow (Choose → Arrange → Review → Done) + curl-bash path. | **Rewrite** |
| `docs/wizard-redesign/prototypes/mockup-textual.py` | The binding reference. | **Read-only** (source of truth) |
| `tools/setup.py` | The seam + engine. Adds `_read_component_desc` + `component_meta`. | **Modified** (Task 1 only) |
| `tests/test_setup.py` | Unit tests for `_read_component_desc` + context shape. | **Modified** (Task 1 only) |

---

## Reference: the injected `WizardContext` (read once before Task 1)

The view consumes exactly these (defined in `tools/wizard_app.py`, populated by `setup.py._build_wizard_context`):

```python
class WizardContext(NamedTuple):
    selection: object        # setup.Selection: .items=[[cat,name,on],...], .cursor,
                             #   .toggle_cursor(), .set_category(cat,bool), .set_all(bool),
                             #   .move_cursor(delta), .enabled_map(), .category_sets(cats)
    state: dict              # {"segments": {key: bool},          # built-ins + externals
                             #  "layout": [{"min_rows": int, "segments": [str]}],
                             #  "dirty": bool, "adopt": bool, "_initial_enabled": {(cat,name): bool}}
    sample_json: str         # unused by the new view (kept for seam stability)
    engine: object           # unused by the new view (kept; functions stay referenced in setup.py)
    status_line: dict        # {"state": "ours"|"unset"|"foreign", "current_command": str|None}
    segment_meta: dict       # {key: {"description": str, "sample": str, "icon": str, "line": int}}
    external_segments: list  # [{"id","filename","name","path","default_on","description",
                             #   "icon","sample","line","provenance"}]  provenance: "bundled"|"user"
    component_meta: dict     # {name: description} across all CATEGORIES (Task 1)
```

Facts the implementer must rely on (verified against `tools/setup.py`):
- `segment_meta[seg]["line"]` is **0-based** (0=identity, 1=model, 2=diagnostics) and matches the layout row index.
- Initial `state["layout"]` rows carry `min_rows` `0`, `20`, `30` in order.
- Externals are **not** present in `state["layout"]`; they appear only as keys in `state["segments"]` (default OFF).
- `WizardResult(selection, state)` is consumed by `launch_wizard`: `result.selection` (components, cast to `Selection`) and `result.state` (`["adopt"]`, `["segments"]`, `["layout"]`) → `persist_statusline`/`_persist_layout`. So the serialized `state` MUST keep every key currently in `state["segments"]` (built-ins **and** externals).

---

## Task 1: Wire real component descriptions into `WizardContext`

The Choose screen's description column is permanently blank: `_component_desc` looks up component names in `ctx.segment_meta`, which is keyed by SEGMENT ID (e.g. `git_branch`), not component name (e.g. `ui-ux-designer`). This task adds `_read_component_desc(abspath)` (stdlib-only, no PyYAML — simple line scanning), threads it through a new `component_meta: dict` field on `WizardContext`, and fixes `_component_desc` to consume it.

**Files:**
- Modify: `tools/setup.py` (insert `_read_component_desc` before `validate_entry`; build `component_meta`; add to `WizardContext(...)` constructor call)
- Modify: `tools/wizard_app.py` (add `component_meta: dict` as 8th field on `WizardContext`)
- Modify: `tests/test_setup.py` (append `TestReadComponentDesc` + `TestComponentMetaInContext`)

**Interfaces:**
- Produces: `WizardContext.component_meta: dict` — `{name: description}` over all `CATEGORIES`.
- `_read_component_desc(abspath: str) -> str` — module-level helper (called from `_build_wizard_context`).

- [ ] **Step 1: Write failing tests in `tests/test_setup.py`**

Append two test classes after the last `class Test...` in `tests/test_setup.py`:

```python
@unittest.skipUnless(HAVE_TEXTUAL, "textual not installed (run under uv)")
class TestReadComponentDesc(unittest.TestCase):
    """_read_component_desc parses description: from YAML frontmatter."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _make_file(self, relpath, content):
        p = os.path.join(self.tmp, relpath)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(content)
        return p

    def test_reads_description_from_md_file(self):
        p = self._make_file("my-cmd.md",
                            "---\nname: my-cmd\ndescription: Does the thing\n---\n")
        self.assertEqual(setup._read_component_desc(p), "Does the thing")

    def test_reads_description_from_skill_directory(self):
        self._make_file("my-skill/SKILL.md",
                        "---\nname: my-skill\ndescription: Skill description here\n---\n")
        skill_dir = os.path.join(self.tmp, "my-skill")
        self.assertEqual(setup._read_component_desc(skill_dir), "Skill description here")

    def test_returns_empty_string_when_no_frontmatter(self):
        p = self._make_file("bare.md", "# Just a heading\nNo frontmatter here.\n")
        self.assertEqual(setup._read_component_desc(p), "")

    def test_returns_empty_string_when_file_missing(self):
        self.assertEqual(
            setup._read_component_desc(os.path.join(self.tmp, "nonexistent.md")), "")

@unittest.skipUnless(HAVE_TEXTUAL, "textual not installed (run under uv)")
class TestComponentMetaInContext(unittest.TestCase):
    """_build_wizard_context populates component_meta from real frontmatter."""

    def _ctx(self):
        wa = _import_wizard_app()
        home = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, home, ignore_errors=True)
        repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        env = {"HOME": home, "AI_KIT_DIR": repo}
        paths = setup.resolve_paths(env)
        entries = setup.enumerate_entries(paths.install_dir)
        installed = {cat: set() for cat in setup.CATEGORIES}
        return setup._build_wizard_context(paths, entries, installed, "{}", wa)

    def test_component_meta_is_dict(self):
        ctx = self._ctx()
        self.assertIsInstance(ctx.component_meta, dict)

    def test_component_meta_keys_match_selection_names(self):
        ctx = self._ctx()
        sel_names = {name for _, name, _ in ctx.selection.items}
        for name in sel_names:
            self.assertIn(name, ctx.component_meta,
                          f"component {name!r} missing from component_meta")

    def test_component_meta_values_are_strings(self):
        ctx = self._ctx()
        for name, desc in ctx.component_meta.items():
            self.assertIsInstance(desc, str,
                                  f"component_meta[{name!r}] must be str, got {type(desc)}")
```

- [ ] **Step 2: Run the new tests to confirm they fail**

```bash
uv run python -m unittest tests.test_setup.TestReadComponentDesc tests.test_setup.TestComponentMetaInContext -v
```
Expected: FAIL with `AttributeError: module 'setup' has no attribute '_read_component_desc'`.

- [ ] **Step 3: Add `_read_component_desc` to `tools/setup.py`**

Insert before `def validate_entry` (search that anchor):

```python
def _read_component_desc(abspath: str) -> str:
    """Return the ``description:`` value from YAML frontmatter of a component.

    For skills ``abspath`` is a directory — the frontmatter lives in
    ``{abspath}/SKILL.md``.  For commands and agents it is the ``.md`` file
    directly.  Returns an empty string if the file is absent, unreadable, or
    has no frontmatter block.
    """
    if os.path.isdir(abspath):
        candidate = os.path.join(abspath, "SKILL.md")
    else:
        candidate = abspath
    try:
        with open(candidate, encoding="utf-8") as fh:
            lines = fh.readlines()
    except OSError:
        return ""
    if not lines or lines[0].rstrip() != "---":
        return ""
    for line in lines[1:]:
        if line.rstrip() == "---":
            break
        if line.startswith("description:"):
            return line[len("description:"):].strip()
    return ""
```

- [ ] **Step 4: Add `component_meta: dict` to `WizardContext` in `tools/wizard_app.py`**

Find the `WizardContext` NamedTuple definition. Add `component_meta: dict` as the 8th (last) field:

```python
class WizardContext(NamedTuple):
    selection: object
    state: dict
    sample_json: str
    engine: object
    status_line: dict
    segment_meta: dict
    external_segments: list
    component_meta: dict          # {name: description} across all CATEGORIES
```

- [ ] **Step 5: Build `component_meta` in `_build_wizard_context` in `tools/setup.py`**

Add just before the `return wizard_app_mod.WizardContext(...)` call:

```python
    component_meta = {
        name: _read_component_desc(abspath)
        for cat in CATEGORIES
        for name, abspath in entries[cat]
    }

    return wizard_app_mod.WizardContext(
        selection=sel,
        state={"segments": segments,
               "layout": current_layout(paths.config_toml), "dirty": False,
               "adopt": sl_state["state"] == "ours",
               "_initial_enabled": initial_enabled},
        sample_json=sample_json,
        engine=_engine_ns(paths, sample_json),
        status_line=sl_state,
        segment_meta=segment_meta,
        external_segments=external,
        component_meta=component_meta,
    )
```

- [ ] **Step 6: Run the tests — they must now pass**

```bash
uv run python -m unittest tests.test_setup.TestReadComponentDesc tests.test_setup.TestComponentMetaInContext -v
```
Expected: 7 tests PASS.

- [ ] **Step 7: Run the full gate**

```bash
uv run pre-commit run --all-files
```
Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add tools/setup.py tools/wizard_app.py tests/test_setup.py
git commit -m "feat(wizard): add _read_component_desc + WizardContext.component_meta (real component descriptions from frontmatter)"
```

---

## Task 2: Re-port the wizard view + rewrite `test_wizard_app.py`

This is one atomic deliverable: a working, prototype-faithful 4-step wizard on real data. It is large because `tools/wizard_app.py` and `tests/test_wizard_app.py` are a single cohesive unit — a half-ported file cannot keep the gate green. Steps are bite-sized; the deliverable is the whole file.

**Files:**
- Rewrite: `tools/wizard_app.py`
- Rewrite: `tests/test_wizard_app.py`
- Read (verbatim source): `docs/wizard-redesign/prototypes/mockup-textual.py`

**Interfaces:**
- Consumes: `WizardContext` (above), `Selection` API (above).
- Produces (for `setup.py.launch_wizard`, unchanged): `run_wizard(ctx) -> WizardResult | None`; `WizardResult(selection, state)`; `WizardContext`/`WizardCrash` exported names.

### Porting rules (apply throughout)

When a method is **identical** to the prototype, copy it verbatim from `mockup-textual.py` and apply these substitutions; do not invent new structure:

| Prototype (`_protodata` / `self.picks`) | Real view (from `ctx`) |
|---|---|
| `D.ICON[seg]` | `self._icon(seg)` |
| `D.SAMPLE[seg]` | `self._sample(seg)` |
| `SEG_DESC.get(seg,'')` | `self._desc(seg)` |
| `D.LAYOUT` / `D.DEFAULT_ON` / `D.ALL_SEGMENTS` | derived from `ctx.state` (see `_build_lists_from_state`) |
| `self.picks` (categories/names) | `ctx.selection` (`.items`, `.cursor`) |
| `ITEM_DESC.get(name,'')` | `self._component_desc(cat, name)` |

Keep verbatim from the prototype (no substitution): `FG/DIM/LINE/ACCENT/GREEN/WARN/PINK/CYAN/KEYCAP`, `STEP_*`, `LANE_GATE`, `FOOTERS`, `QUIT_KEY`, `HELP`, `TITLES`, `SUBS`, `_pad`, the full `CSS` string, `compose()`, `_render`, `_render_header`, `_cap`, `_render_footer`, `_render_help`, `_render_choose` (with the selection substitution), `_render_arrange`, `_render_review`, `_render_done`, `_chip` (extended for externals — see Step 9), `_preview` (with icon/sample substitution), `on_key` and the four `_key_*` handlers, `_move_chip_v`, `_toggle_chip`, `_cycle_focus`, `_clamp_focus`, `_zones`.

### Steps

- [ ] **Step 1: Snapshot the current behavior, then start the rewrite from the prototype**

Copy `docs/wizard-redesign/prototypes/mockup-textual.py` into `tools/wizard_app.py` as the starting skeleton. Then strip the prototype's `__main__`, `_selftest`, and the `import _protodata as D` line; keep the module docstring but replace it with a one-paragraph description of the seam (imports nothing from setup.py; all data via `WizardContext`).

- [ ] **Step 2: Re-declare the seam types and entry point (preserve the contract)**

Keep these EXACTLY as in the current `tools/wizard_app.py` (copy them in): `WizardResult`, `WizardContext` (the 8-field NamedTuple above), `WizardCrash`, `_MIN_TERMINAL_COLS=40`, `_MIN_TERMINAL_ROWS=10`, and `run_wizard(ctx)` (terminal-size guard → `WizardApp(ctx).run()` → re-raise `app._exception` as `WizardCrash`). Add `on_exception(self, exception)` to `WizardApp` (store in `self._exception`, then `self.exit()`).

- [ ] **Step 3: Wire `WizardApp.__init__` to ctx + build the model**

Replace the prototype's `__init__` with:

```python
def __init__(self, ctx: WizardContext) -> None:
    super().__init__()
    self.ctx = ctx
    self.sel = ctx.selection
    self.meta = ctx.segment_meta
    self.ext_by_id = {e["id"]: e for e in ctx.external_segments}
    self.state = dict(ctx.state)            # adopt, _initial_enabled, dirty, segments, layout
    self.result: WizardResult | None = None
    self._exception: BaseException | None = None
    self.step = STEP_CHOOSE
    self.help_open = False
    # adoption gate: 'ours' adopts silently; otherwise the gate is shown on Arrange entry
    self.gate_done = ctx.status_line.get("state") == "ours"
    if self.gate_done:
        self.state["adopt"] = True
    # min_rows per lane, captured from the initial layout (fallback 0/20/30)
    rows = [r.get("min_rows", 0) for r in self.state["layout"]]
    self._min_rows = (rows + [0, 20, 30])[:3]
    # home line (0-based) per segment: built-ins from inventory; externals → last lane
    self.home_line = {k: min(max(int(m.get("line", 0)), 0), 2)
                      for k, m in self.meta.items()}
    for e in ctx.external_segments:
        self.home_line[e["id"]] = 2
    self._build_lists_from_state()
    # immutable snapshot for 'r' reset
    self._initial_lines = [list(x) for x in self.lines]
    self._initial_tray = list(self.tray)
```

- [ ] **Step 4: Implement `_build_lists_from_state` (the two-list model)**

```python
def _build_lists_from_state(self) -> None:
    segs = self.state["segments"]
    self.lines = [[], [], []]
    placed = set()
    for i, row in enumerate(self.state["layout"][:3]):
        for seg in row["segments"]:
            if segs.get(seg) and seg not in placed:
                self.lines[i].append(seg)
                placed.add(seg)
    # ON segments not in any layout row (e.g. an enabled external): home line
    for seg, on in segs.items():
        if on and seg not in placed:
            self.lines[self.home_line.get(seg, 2)].append(seg)
            placed.add(seg)
    # tray = every OFF segment, in stable state-key order (built-ins then externals)
    self.tray = [seg for seg in segs if not segs.get(seg)]
    self.focus_zp = (0, 0)
```

- [ ] **Step 5: Implement the metadata accessors**

```python
def _icon(self, seg: str) -> str:
    if seg in self.ext_by_id:
        return self.ext_by_id[seg].get("icon") or "●"
    return self.meta.get(seg, {}).get("icon", "")

def _sample(self, seg: str) -> str:
    if seg in self.ext_by_id:
        return self.ext_by_id[seg].get("sample", "")
    return self.meta.get(seg, {}).get("sample", "")

def _desc(self, seg: str) -> str:
    if seg in self.ext_by_id:
        return self.ext_by_id[seg].get("description", "")
    return self.meta.get(seg, {}).get("description", "")

def _component_desc(self, cat: str, name: str) -> str:
    return self.ctx.component_meta.get(name, "")  # populated by Task 1's _read_component_desc
```

- [ ] **Step 6: Port the chrome verbatim (header/footer/help/compose/_render)**

Copy from the prototype, unchanged: the `CSS` string, `compose()`, `on_mount`, `_render`, `_render_header`, `_cap`, `_render_footer`, `_render_help`, `_pad`. These already produce `#headerbar`/`#bodywrap`/`#footerbar`, the per-step `.display` toggling, the step pips (`range(3)`), and the `Step N of 3` label. No substitution needed.

- [ ] **Step 7: Port the Choose screen onto `ctx.selection` (components only)**

Replace `_render_choose` to read `self.sel.items` (list of `[cat, name, on]`) and `self.sel.cursor` instead of `self.picks`. Keep the prototype's exact visual structure (cyan `▌ CAT  N/M on  · a all · n none` headers, `◉/◯` glyph, pink `▌` focus gutter, `_pad(name, 30)` + `self._component_desc(cat, name)`). Build category groups in first-appearance order over `self.sel.items`. Render the count line `N of M components selected`. **Do not render any external/segment rows here.**

Replace `_key_choose` to drive `self.sel`:

```python
def _key_choose(self, event) -> bool:
    ch, k = event.character, event.key
    n = len(self.sel.items)
    if not n:
        return k == "enter" and self._goto(STEP_ARRANGE)
    if k == "up":
        self.sel.cursor = (self.sel.cursor - 1) % n
    elif k == "down":
        self.sel.cursor = (self.sel.cursor + 1) % n
    elif k == "space":
        self.sel.toggle_cursor()
    elif ch in ("a", "n"):
        self.sel.set_category(self.sel.items[self.sel.cursor][0], ch == "a")
    elif ch in ("A", "N"):
        self.sel.set_all(ch == "A")
    elif k == "enter":
        return self._goto(STEP_ARRANGE)
    elif k == "tab":
        return True   # consume — Tab is a no-op on Choose (never advances)
    else:
        return False
    return True
```

Add `_goto`:

```python
def _goto(self, step: int) -> bool:
    self.step = step
    return True
```

- [ ] **Step 8: Port the Arrange board + adoption gate**

Port `_render_arrange`, `_chip`, `_preview`, `_clamp_focus`, `_zones`, `_key_arrange`, `_move_chip_v`, `_toggle_chip`, `_cycle_focus`, and `_reset_layout` from the prototype, with substitutions per the porting table. **`_reset_layout` restores the launch snapshot** (not engine defaults):

```python
def _reset_layout(self) -> None:
    self.lines = [list(x) for x in self._initial_lines]
    self.tray = list(self._initial_tray)
    self.focus_zp = (0, 0)
```

Adoption gate — render it ABOVE the lanes when `not self.gate_done`, and short-circuit Arrange keys until answered. In `_render_arrange`, before drawing lanes:

```python
if not self.gate_done:
    sl = self.ctx.status_line
    if sl.get("state") == "foreign":
        cmd = sl.get("current_command") or "(unknown)"
        gate = (f"[{WARN}]Existing status line detected.[/]\n"
                f"[{DIM}]Current:[/] {cmd}\n\nReplace with ai-kit?  [y/N]")
    else:
        gate = "Wire your status line?  [Y/n]"
    self.query_one("#lane0", Static).update(gate)
    for wid in ("#lane1", "#lane2", "#focchip", "#tray", "#preview"):
        self.query_one(wid, Static).update("")
    return
```

In `_key_arrange`, handle the gate first:

```python
if not self.gate_done:
    ch, k = event.character, event.key
    if ch == "y":
        self.state["adopt"] = True; self.gate_done = True
    elif ch == "n":
        self.state["adopt"] = False; self.gate_done = True
    elif k == "enter":
        self.state["adopt"] = self.ctx.status_line.get("state") != "foreign"
        self.gate_done = True
    elif k == "escape":
        self.state["adopt"] = False; self.gate_done = True
    else:
        return False
    return True
```

(After the gate, the rest of `_key_arrange` — arrows/space/tab/r/enter/esc — runs as ported. `enter` advances to Review; `escape` returns to Choose.)

- [ ] **Step 9: External distinction in `_chip` (the net-new requirement)**

```python
def _chip(self, seg: str, focused: bool, parked: bool) -> str:
    is_ext = seg in self.ext_by_id
    label = f"{self._icon(seg)} {seg}"
    if is_ext:
        label = f"◆ {label}"             # external marker
    if focused:
        return (f"[{PINK}]\\[>[/][bold #ffffff on #1b1016]{label}[/]"
                f"[{PINK}]<][/]")
    col = CYAN if is_ext else (DIM if parked else FG)
    return f"[{col} on #0d1117] {label} [/]"
```

In `_render_arrange`'s `#focchip` body, append provenance for externals:

```python
state = "off · in tray" if fz == 3 else f"on · Line {fz + 1}"
prov = (f"  [{CYAN}]external · {self.ext_by_id[seg].get('provenance','')}[/]"
        if seg in self.ext_by_id else "")
self.query_one("#focchip", Static).update(
    f"[#f0f6fc]{self._icon(seg)} [bold]{seg}[/][/]{prov}\n"
    f"[{DIM}]{self._desc(seg)}[/]\n[{DIM}]{state}[/]")
```

- [ ] **Step 10: Port Review + Done, and wire confirm → `_serialize_state` → `WizardResult`**

Port `_render_review` and `_render_done` from the prototype (substituting icon/sample for the preview). In `_render_review`'s "components to install" panel, read `self.sel.items` (enabled names per category). In the `what happens on confirm` panel, reflect the real plan using `self.state["adopt"]`:

```python
adopt = self.state.get("adopt", False)
sl_line = ("Writes ~/.config/ai-kit/statusline.toml + wires settings.json"
           if adopt else "Status line left unchanged (components only)")
```

Replace `_key_review` so `enter` commits and advances to Done:

```python
def _key_review(self, event) -> bool:
    if event.key == "enter":
        if not self._has_net_change():
            self.query_one("#cta", Static).update(
                f"[{WARN}]Nothing to write — Esc to go back, q to quit[/]")
            return True
        self.result = WizardResult(self.sel, self._serialize_state())
        self.step = STEP_DONE
        return True
    if event.key == "escape":
        self.step = STEP_ARRANGE
        return True
    return False
```

Add `_has_net_change` (components changed vs `_initial_enabled`, OR adopt True):

```python
def _has_net_change(self) -> bool:
    initial = self.state.get("_initial_enabled", {})
    current = {(c, n): on for c, n, on in self.sel.items}
    return current != initial or self.state.get("adopt", False)
```

Add `_serialize_state` (built-in rows only; externals persist as toggles; keep every existing segment key):

```python
def _serialize_state(self) -> dict:
    st = dict(self.state)
    on = set()
    for ln in self.lines:
        on.update(ln)
    segs = {k: (k in on) for k in self.state["segments"]}
    st["segments"] = segs
    builtin = set(self.meta)
    layout = []
    for i in range(3):
        on_row = [s for s in self.lines[i] if s in builtin]
        off_home = [s for s in self.tray
                    if s in builtin and self.home_line.get(s, 2) == i]
        layout.append({"min_rows": self._min_rows[i], "segments": on_row + off_home})
    st["layout"] = layout
    st["adopt"] = self.state.get("adopt", False)
    st["dirty"] = True
    return st
```

Port `_key_done`: `enter` → `self.exit()` (result already set). `q`/`escape` from Done are no-ops except `q` (global quit). Global `q` (handled in `on_key`, as in the prototype) leaves `self.result` as-is; if the user `q`s before Review-confirm, `result` is `None` (clean abort) — matches `launch_wizard`'s abort path.

- [ ] **Step 11: Write the STRUCTURAL GATE TEST first (anti-divergence contract)**

In `tests/test_wizard_app.py`, write this test (it encodes the Global Constraints as machine checks):

```python
import unittest
from textual.widgets import Static
from tools import wizard_app as wa
from tests.wizard_fixtures import make_ctx   # Step 12 helper

class TestStructuralFidelity(unittest.IsolatedAsyncioTestCase):
    async def test_arrange_has_three_separate_lane_panels(self):
        app = wa.WizardApp(make_ctx())
        async with app.run_test() as pilot:
            app.step = wa.STEP_ARRANGE
            app.gate_done = True
            app._render()
            await pilot.pause()
            for wid in ("#lane0", "#lane1", "#lane2", "#focchip", "#tray", "#preview"):
                self.assertEqual(len(app.query(wid)), 1, f"missing {wid}")

    async def test_off_segment_never_appears_in_a_lane(self):
        app = wa.WizardApp(make_ctx())
        async with app.run_test() as pilot:
            app.step = wa.STEP_ARRANGE
            app.gate_done = True
            app._render()
            await pilot.pause()
            lane_text = " ".join(
                str(app.query_one(f"#lane{i}", Static).content) for i in range(3))
            for seg in app.tray:
                self.assertNotIn(seg, lane_text,
                                 f"OFF segment {seg!r} leaked into a lane")

    async def test_every_lane_chip_carries_its_icon(self):
        ctx = make_ctx()
        app = wa.WizardApp(ctx)
        async with app.run_test() as pilot:
            app.step = wa.STEP_ARRANGE
            app.gate_done = True
            app._render()
            await pilot.pause()
            lane_text = " ".join(
                str(app.query_one(f"#lane{i}", Static).content) for i in range(3))
            for i in range(3):
                for seg in app.lines[i]:
                    icon = app._icon(seg)
                    if icon:
                        self.assertIn(icon, lane_text, f"{seg} missing icon")

    async def test_choose_shows_no_segments_or_externals(self):
        app = wa.WizardApp(make_ctx(with_external=True))
        async with app.run_test() as pilot:
            await pilot.pause()
            box = str(app.query_one("#picksbox", Static).content)
            for seg in app.state["segments"]:
                self.assertNotIn(seg, box, f"segment {seg!r} leaked onto Choose")
```

The correct accessor in Textual 8.2.7 is `str(widget.content)` on a `Static` or `Label` — confirmed against `tests/test_wizard_app.py` (lines 295, 374-375). Use this form consistently throughout; do **not** use `.render()`.

- [ ] **Step 12: Add the test fixture builder `tests/wizard_fixtures.py`**

Create a helper that builds a realistic `WizardContext` without importing the Textual app's data from setup (it may import `tools.setup` to reuse `Selection`, `load_segment_inventory`, `build_segment_meta`, `LAYOUT_DEFAULTS`, `SEGMENT_DEFAULTS`, `INVENTORY_PATH`):

```python
from tools import setup
from tools import wizard_app as wa

def make_ctx(with_external=False, sl_state="unset"):
    inv = setup.load_segment_inventory(setup.INVENTORY_PATH)
    meta = setup.build_segment_meta(inv, {})
    sel = setup.Selection([
        ("agents", "ui-ux-designer", True),
        ("agents", "code-reviewer", False),
        ("commands", "code-review", True),
        ("skills", "brainstorming", True),
    ])
    segments = dict(setup.SEGMENT_DEFAULTS)
    external = []
    if with_external:
        external = [{"id": "system_memory", "filename": "system_memory",
                     "name": "System memory", "path": "/dev/null",
                     "default_on": False, "description": "System available RAM",
                     "icon": "💻", "sample": "12.0 GiB free", "line": 1,
                     "provenance": "bundled"}]
        segments["system_memory"] = False
    layout = [{"min_rows": r["min_rows"], "segments": list(r["segments"])}
              for r in setup.LAYOUT_DEFAULTS]
    initial = {(c, n): False for c, n, _ in sel.items}
    return wa.WizardContext(
        selection=sel,
        state={"segments": segments, "layout": layout, "dirty": False,
               "adopt": sl_state == "ours", "_initial_enabled": initial},
        sample_json="{}", engine=None,
        status_line={"state": sl_state, "current_command": None},
        segment_meta=meta, external_segments=external,
        component_meta={name: "" for _, name, _ in sel.items})
```

- [ ] **Step 13: Run the structural gate test — it must PASS**

Run: `uv run python -m unittest tests.test_wizard_app.TestStructuralFidelity -v`
Expected: 4 tests PASS. If any fail, the port violates a Global Constraint — fix the view, not the test.

- [ ] **Step 14: Add behavior tests for Choose, Arrange, gate, external, writeback, Done**

Write `run_test`-driven tests (use `make_ctx`, drive with `pilot.press(...)`, assert on `app` state):
- Choose: `down`/`up` wrap the cursor; `space` toggles `sel.items[cursor][2]`; `a`/`n` set the cursor's category; `A`/`N` set all; `tab` does NOT change `app.step`; `enter` sets `app.step == STEP_ARRANGE`.
- Arrange gate: with `sl_state="unset"`, `enter` sets `app.state["adopt"] is True` and `app.gate_done`; with `sl_state="foreign"`, `enter` sets `adopt is False`; `y`/`n` force True/False; `sl_state="ours"` → `gate_done` already True at init, `adopt True`.
- Arrange moves: after `gate_done`, `space` on a lane chip moves it to `app.tray` and OFF; `space` on a tray chip re-activates it onto its home line; `left`/`right` reorder within a lane; `up` from Line 1 sends a chip to the tray.
- External: with `with_external=True`, the tray initially contains `"system_memory"`; toggling it on places it on a lane and `_serialize_state()["segments"]["system_memory"] is True`; the chip text contains `◆`.
- Writeback: after toggling a built-in off, `_serialize_state()["segments"][seg] is False` and `seg` is NOT in any `layout` row's ON portion but the layout still lists it (off-home placement); every original segment key is still present in serialized `segments`.
- Review/Done: from Arrange, `enter` → Review (`app.step == STEP_REVIEW`); on Review `enter` with a net change sets `app.result` (a `WizardResult`) and `app.step == STEP_DONE`; `app.result.state["adopt"]` matches the gate answer; `q` before confirm leaves `app.result is None`; on Review `enter` when `_has_net_change()` is False, `app.step` stays `STEP_REVIEW` and `str(app.query_one("#cta", Static).content)` contains `"Nothing to write"`.
- Header/footer: `_render_header` shows 3 pips; `STEP_DONE` shows all green; footer for each step matches `FOOTERS[step]`.

- [ ] **Step 15: Run the full wizard unit suite**

Run: `uv run python -m unittest tests.test_wizard_app -v`
Expected: all PASS.

- [ ] **Step 16: Run the gate (lint + type + dead-code)**

Run: `uv run pre-commit run --all-files`
Expected: PASS (ruff/pylint/pyright/vulture/shellcheck/py-compile/unittest hooks green). If `vulture` flags any new helper, it is genuinely unused — remove it. Confirm `tools/setup.py` shows only the Task 1 diff (no further changes introduced by this task): `git diff HEAD~1 --stat tools/setup.py` should show exactly the `_read_component_desc` + `component_meta` lines committed in Task 1, and `git diff --stat tools/setup.py` (unstaged) is empty.

- [ ] **Step 17: Commit**

```bash
git add tools/wizard_app.py tests/test_wizard_app.py tests/wizard_fixtures.py
git commit -m "feat(wizard): re-port view to the locked prototype (3 lane panels, mock preview, external distinction, view-owned lines/tray, component_meta-backed descriptions)"
```

Note: `tests/test_setup.py` and the `tools/setup.py` changes were committed in Task 1 — do not re-stage them here.

---

## Task 3: Rewrite `tests/test_wizard_pty.py` for the new 4-step flow

The current PTY suite drives the old multi-widget flow (it asserts `OFF-TRAY:`, `#board-lanes`, etc.). Rewrite it to drive the ported flow end-to-end over a real PTY.

**Files:**
- Rewrite: `tests/test_wizard_pty.py`

**Interfaces:**
- Consumes: `run_wizard`/`WizardApp` over a PTY (the existing harness in the current file — keep the PTY spawn/escape-stripping helpers; only the assertions and key sequences change).

- [ ] **Step 1: Keep the PTY harness, retarget the assertions**

Reuse the file's existing PTY spawn helper and ANSI-stripping. Replace each phase's key sequence + assertions with the new flow:
- **Choose visible:** spawn, assert the screen contains `ai-kit install wizard` and `select components` and `components selected`; assert it does NOT contain any segment id (e.g. `render_time`).
- **Choose → Arrange:** press `enter`; assert the answered/gated Arrange screen renders `Line 1`/`Line 2`/`Line 3` border titles and `live preview`.
- **Gate:** with a clean `$HOME` (unset state), assert the gate text `Wire your status line?` appears before `enter`; after `enter`, the lanes render.
- **Arrange → Review:** press `enter`; assert `components to install` and `status line` and `Install ai-kit`.
- **Review → Done:** press `enter`; assert the Done art and `next` panel.
- **Abort:** press `q` at Choose; assert clean exit, no config written under the temp `$HOME`.

- [ ] **Step 2: Keep the curl-bash E2E**

Retain the existing curl-bash invocation test (`open_tty` + stdin redirect path); update only its expected on-screen strings to the new flow's first screen (`select components`).

- [ ] **Step 3: Run the PTY suite**

Run: `uv run python -m unittest tests.test_wizard_pty -v`
Expected: all PASS. (PTY tests are slow; allow the suite its normal runtime.)

- [ ] **Step 4: Commit**

```bash
git add tests/test_wizard_pty.py
git commit -m "test(wizard): rewrite PTY E2E for the ported 4-step flow"
```

---

## Task 4: Copy/help parity + final full-gate sweep + manual smoke

**Files:**
- Modify (if needed): `tools/wizard_app.py` (copy strings only)

**Interfaces:** none new.

- [ ] **Step 1: Verify copy parity against the prototype**

Diff the user-facing strings against `mockup-textual.py`: `TITLES`, `SUBS`, `FOOTERS`, `HELP`, the panel border titles (`select components`, `Line N`, `focused chip`, `OFF — disabled  (Space activates → its home line)`, `live preview  (full width — like the real status line)`, `components to install`, `status line`, `what happens on confirm`, `next`). They must match the prototype verbatim (the prototype's `SUBS[STEP_DONE]` is still built dynamically with run counts — keep that). Fix any drift in `tools/wizard_app.py`.

- [ ] **Step 2: Confirm Help text matches actual key behavior**

Verify `HELP[STEP_ARRANGE]` says `Tab / ⇧Tab  Focus the next / previous chip` and that the implementation binds Tab/⇧Tab to `_cycle_focus` (chip focus), not panel cycling. They must agree (this was a defect in the shipped build).

- [ ] **Step 3: Full gate**

Run: `uv run pre-commit run --all-files`
Expected: PASS. Confirm no new changes to `tools/setup.py` were introduced since Task 1: `git diff --stat tools/setup.py` (unstaged) is empty.

- [ ] **Step 4: Manual smoke (record results in the task report)**

Run the wizard against a throwaway HOME and walk all four screens:

```bash
HOME=$(mktemp -d) XDG_CONFIG_HOME=$(mktemp -d) uv run tools/setup.py install
```

Check, eyeballing against the prototype screenshots: (a) Choose has no external/segment rows and Tab does nothing; (b) Arrange shows three distinct bordered lanes, chips have icons, the external `system_memory` shows `◆` and a CYAN tint and appears in exactly one place; (c) the preview shows `icon sample | icon sample` per lane with `N on · M off`; (d) Review shows four panels + the green install CTA; (e) Done shows the ASCII art. Abort with `q` and confirm nothing was written under the temp HOME.

- [ ] **Step 5: Commit (if any copy fixes were made)**

```bash
git add tools/wizard_app.py
git commit -m "polish(wizard): copy + help-text parity with the prototype"
```

---

## Task 5 (OPTIONAL — defer unless requested): slim the unused engine seam

After Task 1 the view no longer calls `ctx.engine.*`, `ctx.sample_json`, or the live `render_preview`. They remain in `setup.py` (still referenced inside `_engine_ns`, so not dead) but are now unused by the view — an injected-but-ignored dependency. **Do not do this as part of the fix.** If the user later wants the seam tightened: drop `engine`/`sample_json` from `WizardContext`, delete `_engine_ns` and the pure functions it bundled (`_wizard_groups`, `off_tray`, `layout_move`, `layout_toggle`, `_apply_wizard_command`, `_wizard_order`, `render_preview`, and `patch_layout` if then unused), update `_build_wizard_context`, and fix `tests/test_setup.py` accordingly — guided by `vulture`. This is a separate, reviewable cleanup with its own test impact; keep it out of the UI fix to bound risk.

---

## Self-Review

**1. Spec/constraint coverage:**
- Real component descriptions in Choose → Task 1 (`_read_component_desc` + `component_meta: dict` 8th field on `WizardContext`). ✓
- Three separate lane panels → Task 2 Steps 6/8 + structural gate test (Step 11). ✓
- Chips carry icons → Task 2 Steps 5/9 + structural test. ✓
- OFF ∉ lanes (no duplication) → two-list model (Task 2 Step 4) + structural test. ✓
- Choose components-only, Tab no-op → Task 2 Step 7 + structural test + PTY. ✓
- Mock preview → Task 2 Step 8 `_preview`. ✓ (mock-preview constraint supersedes PRD live-preview invariant per 2026-06-26 decision, cited in Global Constraints and PRD.)
- External distinction → Task 2 Step 9 + behavior test. ✓
- 4-step flow incl. Done → Task 2 Steps 6/10. ✓
- Adoption gate preserved → Task 2 Step 8 + behavior test. ✓
- No-op Review feedback → Task 2 Step 10 (`#cta` WARN update) + behavior test (Step 14). ✓
- `setup.py` bounded to Task 1 only → Task 2 Step 16 and Task 4 Step 3 both confirm no further unstaged diff on `tools/setup.py`. ✓
- Components/segments namespaces separate (no `_sync_selection_to_state`) → Task 2 Step 7 (Choose mutates `sel` only), Step 10 (`_serialize_state` builds segments from lines/tray). ✓
- Writeback shape consumed by `_persist_layout` → Task 2 Step 10 `_serialize_state` (keeps all segment keys; built-in-only layout rows; min_rows preserved). ✓

**2. Placeholder scan:** No "TBD"/"handle appropriately"; every code step shows complete code or a verbatim-port instruction with explicit substitutions. The `Static` accessor is specified precisely as `str(widget.content)` (Textual 8.2.7, confirmed against existing test suite) — no deferred decisions. ✓

**3. Type/name consistency:** `self.lines`/`self.tray`/`self.home_line`/`self._min_rows`/`self.sel`/`self.meta`/`self.ext_by_id`/`self.state`/`self.step`/`self.gate_done` are used consistently across Task 2 Steps 3–10. `_goto`, `_build_lists_from_state`, `_icon`/`_sample`/`_desc`/`_component_desc`, `_serialize_state`, `_has_net_change`, `_reset_layout`, `make_ctx` are each defined where first referenced. `_component_desc` uses `self.ctx.component_meta.get(name, "")` — consistent with the 8th field added in Task 1. `WizardResult(selection, state)` and `WizardContext`'s 8 fields match `setup.py` (after Task 1). `make_ctx` passes `component_meta={name: "" for _, name, _ in sel.items}` as the 8th positional argument. ✓
