# Installer Registry UX Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restore a sorted, audience-tagged tool list with a graded severity model and a per-tool enable/disable flag, and stop GSD from nagging by detecting its state from the file it already writes.

**Architecture:** Extend the declarative `Tool` model with four new fields plus a `[tool.state]` block; add a `sort_tools()` helper and a six-state `status()` with a `severity()` bucketer in the engine; update `setup.py` tables to show `Pri / For / What it does` and route only "loud" states into the ACTIONS panel. All behaviour stays driven by `registry.toml` — no hardcoded tool data.

**Tech Stack:** Python 3.11+ (stdlib `tomllib`, `json`), `rich` (degrades to plain print), bare `unittest` (no pytest).

**Reference spec:** `docs/superpowers/specs/2026-06-07-installer-registry-ux-design.md`

**Test command (whole suite):** `python3 -m unittest discover -s tests -p 'test_*.py'`
**Single test:** `python3 -m unittest tests.test_setup.ClassName.test_name -v`

**Constraints:** npm/pip banned (volta/pnpm/uv only). English source/docs. Do NOT push or force-push (no permission). Commit locally only.

---

### Task 1: Schema — new fields on the `Tool` model + loader

**Files:**
- Modify: `tools/installer/model.py`
- Test: `tests/test_setup.py` (class `ModelTests`)

- [ ] **Step 1: Write the failing tests**

Add to `class ModelTests` in `tests/test_setup.py`:

```python
    def test_new_fields_default(self):
        t = mdl.Tool(id="rg", name="ripgrep", kind="pkg", category="search")
        self.assertTrue(t.enabled)            # enabled by default
        self.assertEqual(t.audience, "both")
        self.assertEqual(t.desc, "")
        self.assertEqual(t.pin, "")
        self.assertEqual(t.state_file, "")

    def test_loader_parses_state_block_and_flags(self):
        import tempfile, pathlib
        toml = (
            '[[tool]]\n'
            'id="gsd"\nname="GSD Core"\nkind="launcher"\ncategory="ai"\npriority="P1"\n'
            'cmd="npx"\nenabled=false\naudience="ai"\ndesc="Spec-driven phases"\n'
            '[tool.state]\n'
            'file="~/.cache/gsd/x.json"\ninstalled_key="installed"\n'
            'latest_key="latest"\nupdate_key="update_available"\n'
        )
        p = pathlib.Path(tempfile.mkdtemp()) / "r.toml"
        p.write_text(toml)
        t = mdl.load_tools(p)[0]
        self.assertFalse(t.enabled)
        self.assertEqual(t.audience, "ai")
        self.assertEqual(t.desc, "Spec-driven phases")
        self.assertEqual(t.state_file, "~/.cache/gsd/x.json")
        self.assertEqual(t.state_installed_key, "installed")
        self.assertEqual(t.state_update_key, "update_available")
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m unittest tests.test_setup.ModelTests -v`
Expected: FAIL — `AttributeError: 'Tool' object has no attribute 'enabled'`.

- [ ] **Step 3: Add the fields to the dataclass**

In `tools/installer/model.py`, inside `@dataclass class Tool`, add after the `setup` field (around line 53):

```python
    # enable / audience / description / pin
    enabled: bool = True
    audience: str = "both"                          # ai | human | both ("classifier")
    desc: str = ""                                  # one-line "what it does" (notes stays impl detail)
    pin: str = ""                                   # held version; presence suppresses the update state
    # launcher state-file detection ([tool.state])
    state_file: str = ""
    state_installed_key: str = ""
    state_latest_key: str = ""
    state_update_key: str = ""
```

- [ ] **Step 4: Parse them in `load_tools`**

In `tools/installer/model.py`, inside the `for row in data.get("tool", []):` loop, add after `ver = row.get("version", {})`:

```python
        state = row.get("state", {})
```

Then add these keyword args to the `Tool(...)` constructor call (after `version_re=...`):

```python
            enabled=bool(row.get("enabled", True)),
            audience=row.get("audience", "both"),
            desc=row.get("desc", ""),
            pin=row.get("pin", ""),
            state_file=state.get("file", ""),
            state_installed_key=state.get("installed_key", ""),
            state_latest_key=state.get("latest_key", ""),
            state_update_key=state.get("update_key", ""),
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `python3 -m unittest tests.test_setup.ModelTests -v`
Expected: PASS (all `ModelTests`).

- [ ] **Step 6: Commit**

```bash
git add tools/installer/model.py tests/test_setup.py
git commit -m "feat(installer): add enabled/audience/desc/pin + [tool.state] to Tool model"
```

---

### Task 2: `sort_tools()` — priority → category → name

**Files:**
- Modify: `tools/installer/model.py`
- Test: `tests/test_setup.py` (new class `SortToolsTests`)

- [ ] **Step 1: Write the failing test**

Add to `tests/test_setup.py` (before `if __name__`):

```python
class SortToolsTests(unittest.TestCase):
    def _t(self, id, pri, cat, name=None):
        return mdl.Tool(id=id, name=name or id, kind="pkg", category=cat, priority=pri)

    def test_sorts_priority_then_category_then_name(self):
        tools = [
            self._t("z", "P3", "system"),
            self._t("a", "P0", "search"),
            self._t("yq", "P0", "data", name="yq"),
            self._t("jq", "P0", "data", name="jq"),
            self._t("eza", "P1", "nav"),
        ]
        out = [t.id for t in mdl.sort_tools(tools)]
        # P0 first; within P0, data(jq,yq) before search(a); names A->Z within category
        self.assertEqual(out, ["jq", "yq", "a", "eza", "z"])

    def test_unknown_priority_sorts_last(self):
        tools = [self._t("known", "P1", "x"), self._t("weird", "PX", "x")]
        out = [t.id for t in mdl.sort_tools(tools)]
        self.assertEqual(out, ["known", "weird"])
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3 -m unittest tests.test_setup.SortToolsTests -v`
Expected: FAIL — `AttributeError: module 'model' has no attribute 'sort_tools'`.

- [ ] **Step 3: Implement `sort_tools`**

In `tools/installer/model.py`, add after the `categories()` function:

```python
_PRIORITY_RANK = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}


def sort_tools(tools: list[Tool]) -> list[Tool]:
    """Stable sort: priority P0→P3, then category A→Z, then tool name A→Z."""
    return sorted(
        tools,
        key=lambda t: (_PRIORITY_RANK.get(t.priority, 99), t.category.lower(), t.name.lower()),
    )
```

- [ ] **Step 4: Run to verify it passes**

Run: `python3 -m unittest tests.test_setup.SortToolsTests -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tools/installer/model.py tests/test_setup.py
git commit -m "feat(installer): sort_tools by priority, category, name"
```

---

### Task 3: `status()` rewrite — six canonical states + state-file detection

**Files:**
- Modify: `tools/installer/engine.py`
- Test: `tests/test_setup.py` (class `EngineStatusTests` — update + add)

- [ ] **Step 1: Rewrite the existing status tests and add new ones**

In `tests/test_setup.py`, REPLACE `test_installed_binary`, `test_launcher_unwired_when_marker_absent`, and `test_npx_launcher_unknown` inside `class EngineStatusTests` with:

```python
    def test_installed_binary_is_current(self):
        n = self._bin("fakeok", 'echo 1.2.3\nexit 0\n')
        t = mdl.Tool(id=n, name="x", kind="curl", category="extras")
        self.assertEqual(eng.status(t, "debian"), "current")

    def test_disabled_short_circuits(self):
        # disabled wins even for an installed binary; no subprocess needed
        t = mdl.Tool(id="anything", name="x", kind="pkg", category="extras", enabled=False)
        self.assertEqual(eng.status(t, "debian"), "disabled")

    def test_launcher_needs_wiring_when_marker_absent(self):
        t = mdl.Tool(id="x", name="x", kind="launcher", category="ai", cmd="sh",
                     wired_marker="/nonexistent/marker")
        self.assertEqual(eng.status(t, "debian"), "needs_wiring")

    def _state_launcher(self, payload):
        import json, tempfile, pathlib
        d = tempfile.mkdtemp(); self.addCleanup(__import__("shutil").rmtree, d)
        f = pathlib.Path(d) / "state.json"; f.write_text(json.dumps(payload))
        return mdl.Tool(id="gsd", name="gsd", kind="launcher", category="ai", cmd="npx",
                        state_file=str(f), state_installed_key="installed",
                        state_latest_key="latest", state_update_key="update_available")

    def test_launcher_state_current(self):
        t = self._state_launcher({"installed": "1.3.1", "latest": "1.3.1", "update_available": False})
        self.assertEqual(eng.status(t, "debian"), "current")

    def test_launcher_state_update_available(self):
        t = self._state_launcher({"installed": "1.3.0", "latest": "1.3.1", "update_available": True})
        self.assertEqual(eng.status(t, "debian"), "update")

    def test_launcher_state_pinned_suppresses_update(self):
        t = self._state_launcher({"installed": "1.3.0", "latest": "1.3.1", "update_available": True})
        t.pin = "1.3.0"
        self.assertEqual(eng.status(t, "debian"), "pinned")

    def test_launcher_missing_when_state_file_absent(self):
        t = mdl.Tool(id="gsd", name="gsd", kind="launcher", category="ai", cmd="npx",
                     state_file="/nonexistent/gsd-state.json", state_installed_key="installed")
        self.assertEqual(eng.status(t, "debian"), "missing")
```

- [ ] **Step 2: Run to verify they fail**

Run: `python3 -m unittest tests.test_setup.EngineStatusTests -v`
Expected: FAIL — `current`/`disabled`/`needs_wiring`/state tests fail against the old `installed`/`unwired`/`unknown` strings.

- [ ] **Step 3: Rewrite `status()` and add helpers**

In `tools/installer/engine.py`, add `import json` near the top imports. Then REPLACE the entire `status()` function (the current `def status(tool, os_name) -> str:` block) with:

```python
# severity buckets for the canonical states
STATE_LOUD = {"missing", "needs_wiring", "alias_needed"}     # demand action (ACTIONS NEEDED)
STATE_CALM = {"update"}                                      # FYI (Updates available)
STATE_SILENT = {"current", "pinned", "disabled"}            # nothing to show


def severity(state: str) -> str:
    """Map a status state to its display bucket: 'loud' | 'calm' | 'silent'."""
    if state in STATE_LOUD:
        return "loud"
    if state in STATE_CALM:
        return "calm"
    return "silent"


def _read_state_file(tool: Tool) -> dict | None:
    """Parse a launcher's declared JSON state file; None if absent/unreadable."""
    if not tool.state_file:
        return None
    p = Path(tool.state_file).expanduser()
    try:
        return json.loads(p.read_text())
    except (OSError, ValueError):
        return None


def _launcher_status(tool: Tool) -> str:
    if tool.state_file:
        data = _read_state_file(tool)
        if data is None:
            return "missing"                       # declared a state file, it's absent → not installed
        installed = data.get(tool.state_installed_key) if tool.state_installed_key else True
        if not installed:
            return "missing"
        if tool.pin:
            return "pinned"
        if tool.state_update_key and data.get(tool.state_update_key):
            return "update"
        return "current"
    if not shutil.which(tool.cmd):
        return "missing"
    if tool.wired_marker and not Path(tool.wired_marker).expanduser().exists():
        return "needs_wiring"
    return "current"


def status(tool: Tool, os_name: str) -> str:
    """Canonical state: missing|needs_wiring|alias_needed|update|pinned|current|disabled."""
    if not tool.enabled:
        return "disabled"
    if tool.kind == "marketplace":
        from register import marketplace_enabled
        return "current" if marketplace_enabled(tool) else "missing"
    if tool.kind == "launcher":
        return _launcher_status(tool)
    st = check(tool, os_name)[0]                    # "installed" | "alias_needed" | "missing"
    return "current" if st == "installed" else st
```

- [ ] **Step 4: Run to verify they pass**

Run: `python3 -m unittest tests.test_setup.EngineStatusTests -v`
Expected: PASS (all `EngineStatusTests`).

- [ ] **Step 5: Commit**

```bash
git add tools/installer/engine.py tests/test_setup.py
git commit -m "feat(installer): six-state status() with [tool.state] detection + severity buckets"
```

---

### Task 4: dependency-override warning for disabled deps

**Files:**
- Modify: `tools/installer/engine.py`
- Test: `tests/test_setup.py` (class `EngineOrderTests`)

- [ ] **Step 1: Write the failing test**

Add to `class EngineOrderTests` in `tests/test_setup.py`:

```python
    def test_required_but_disabled_is_reported(self):
        enabled_tool = mdl.Tool(id="needsX", name="needsX", kind="pkg", category="x",
                                requires=["X"])
        disabled_dep = mdl.Tool(id="X", name="X", kind="pkg", category="x", enabled=False)
        catalogue = [enabled_tool, disabled_dep]
        dragged = eng.with_required([enabled_tool], catalogue, lambda t: False)
        # the disabled dep is still dragged in (dependency wins)...
        self.assertIn("X", {t.id for t in dragged})
        # ...and flagged so the caller can warn
        flagged = eng.required_but_disabled([enabled_tool], dragged)
        self.assertEqual([t.id for t in flagged], ["X"])
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3 -m unittest tests.test_setup.EngineOrderTests.test_required_but_disabled_is_reported -v`
Expected: FAIL — `module 'engine' has no attribute 'required_but_disabled'`.

- [ ] **Step 3: Implement `required_but_disabled`**

In `tools/installer/engine.py`, add after the `with_required(...)` function:

```python
def required_but_disabled(selected: list[Tool], dragged: list[Tool]) -> list[Tool]:
    """Dragged-in dependencies that are disabled (caller should warn — dependency wins)."""
    sel_ids = {t.id for t in selected}
    return [t for t in dragged if not t.enabled and t.id not in sel_ids]
```

(`with_required` already drags deps by `requires` regardless of `enabled`, so no change there.)

- [ ] **Step 4: Run to verify it passes**

Run: `python3 -m unittest tests.test_setup.EngineOrderTests -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tools/installer/engine.py tests/test_setup.py
git commit -m "feat(installer): flag disabled deps dragged in by enabled tools"
```

---

### Task 5: wizard tables — Pri/For/What columns, sort, severity routing

**Files:**
- Modify: `tools/setup.py`
- Test: `tests/test_setup.py` (new class `WizardRenderTests`)

This task wires the new model/engine into the display. Rich tables aren't unit-tested directly; we test the pure routing the tables rely on (severity + actionable filtering) and smoke-render the tables.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_setup.py`:

```python
class WizardRenderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import importlib
        cls.wiz = importlib.import_module("setup")
        cls.tools = mdl.load_tools(MANIFEST_NEW)

    def test_actionable_excludes_disabled_and_current(self):
        # actionable = LOUD states only; disabled/current/update never block
        states = {
            "a": "missing", "b": "needs_wiring", "c": "current",
            "d": "disabled", "e": "update", "f": "pinned",
        }
        loud = [k for k, s in states.items() if eng.severity(s) == "loud"]
        self.assertEqual(sorted(loud), ["a", "b"])

    def test_audit_table_renders_sorted_without_error(self):
        # smoke: building the table must not raise and must touch every tool
        out = self.wiz.audit_table(mdl.sort_tools(self.tools[:5]), "debian")
        self.assertIsInstance(out, list)   # returns actionable list

    def test_for_label_maps_audience(self):
        self.assertEqual(self.wiz.for_label("ai"), "AI")
        self.assertEqual(self.wiz.for_label("human"), "you")
        self.assertEqual(self.wiz.for_label("both"), "both")
```

- [ ] **Step 2: Run to verify they fail**

Run: `python3 -m unittest tests.test_setup.WizardRenderTests -v`
Expected: FAIL — `module 'setup' has no attribute 'for_label'`.

- [ ] **Step 3: Add `for_label` and the status-accent map; rewrite the two tables**

In `tools/setup.py`, add near the top (after `AI_CATEGORIES`):

```python
AUDIENCE_LABEL = {"ai": "AI", "human": "you", "both": "both"}
STATUS_ACCENT = {
    "missing":      "[red]✗ missing[/red]",
    "needs_wiring": "[yellow]● needs wiring[/yellow]",
    "alias_needed": "[yellow]● alias needed[/yellow]",
    "update":       "[cyan]↑ update[/cyan]",
    "pinned":       "[blue]◆ pinned[/blue]",
    "current":      "[green]✓ current[/green]",
    "disabled":     "[dim]· disabled[/dim]",
}


def for_label(audience: str) -> str:
    return AUDIENCE_LABEL.get(audience, audience)
```

REPLACE `audit_table` with:

```python
def audit_table(tools: list[mdl.Tool], os_name: str) -> list[mdl.Tool]:
    """Render a sorted status table; return the actionable (LOUD-state) tools."""
    from rich.table import Table
    table = Table(show_header=True, header_style="bold cyan")
    for col in ("Pri", "Tool", "For", "What it does", "Status"):
        table.add_column(col)
    actionable = []
    for t in mdl.sort_tools(tools):
        st = eng.status(t, os_name)
        if eng.severity(st) == "loud":
            actionable.append(t)
        row_style = "dim" if st == "disabled" else None
        table.add_row(t.priority, t.name, for_label(t.audience), t.desc or t.notes,
                      STATUS_ACCENT.get(st, st), style=row_style)
    console.print(table)
    return actionable
```

REPLACE `audit_ai_table` with:

```python
def audit_ai_table(tools: list[mdl.Tool], os_name: str) -> None:
    from rich.table import Table
    table = Table(title="AI toolkits", show_header=True, header_style="bold cyan")
    for col in ("#", "Toolkit", "For", "Kind", "What it does", "Status"):
        table.add_column(col)
    for i, t in enumerate(mdl.sort_tools(tools), 1):
        st = eng.status(t, os_name)
        row_style = "dim" if st == "disabled" else None
        table.add_row(str(i), t.name, for_label(t.audience), t.kind,
                      t.desc or t.notes, STATUS_ACCENT.get(st, st), style=row_style)
    console.print(table)
```

- [ ] **Step 4: Run to verify they pass**

Run: `python3 -m unittest tests.test_setup.WizardRenderTests -v`
Expected: PASS.

- [ ] **Step 5: Route only LOUD states into the ACTIONS panel; add an Updates line**

In `tools/setup.py`, in `run_ai_tools`, REPLACE the `pending = [...]` line and its panel block with:

```python
    pending = [(i, t, ai_action_hint(t, os_name)) for i, t in enumerate(mdl.sort_tools(tools), 1)
               if eng.severity(eng.status(t, os_name)) == "loud"]
    if pending:
        from rich.panel import Panel
        lines = [f"[bold bright_white]{i}[/]) [bold cyan]{t.name}[/]\n"
                 f"     [bold black on bright_yellow] ▶ {hint} [/]" for i, t, hint in pending]
        console.print(Panel("\n".join(lines),
                            title="[bold black on bright_yellow] ACTIONS NEEDED [/]",
                            border_style="bright_yellow", expand=False, padding=(1, 2)))
    updates = [t for t in mdl.sort_tools(tools) if eng.status(t, os_name) == "update"]
    if updates:
        console.print("[cyan]↑ Updates available:[/cyan] "
                      + ", ".join(f"{t.name}" for t in updates)
                      + "  [dim](run menu 6 / their update command)[/dim]")
```

Then update the two selection branches in `run_ai_tools` that reference old states:
- the `select=True` "Enter for all" branch and the `select=False` branch currently filter on `eng.status(...) != "installed"` / `== "missing"` / `in ("unwired", "unknown")`. Change them to use severity:

```python
    if select:
        raw = input("Select toolkits (e.g. 1,3 — Enter for all pending): ").strip().lower()
        ordered = mdl.sort_tools(tools)
        if raw in ("", "a", "all"):
            chosen = [t for t in ordered if eng.severity(eng.status(t, os_name)) == "loud"] or list(ordered)
        else:
            idx = [int(p) for p in raw.replace(" ", "").split(",") if p.isdigit()]
            chosen = [ordered[i - 1] for i in idx if 1 <= i <= len(ordered)]
    else:
        chosen = [t for t in tools if eng.status(t, os_name) == "missing"]
        deferred = [t for t in tools if eng.status(t, os_name) == "needs_wiring"]
        if deferred:
            info("Needs interactive setup — run setup → AI tools to handle: "
                 + ", ".join(t.name for t in deferred))
```

Also in `ai_action_hint`, change the early guard `if st == "installed":` to `if eng.severity(st) != "loud":` and the launcher verb line `verb = "wire" if st == "unwired" else "install"` to `verb = "wire" if st == "needs_wiring" else "install"`.

- [ ] **Step 6: Update `run_cli_tools` and `summary` for the new states**

In `tools/setup.py` `summary`, change the per-tool key line:

```python
        key = "installed" if eng.severity(eng.status(t, os_name)) == "silent" \
            and eng.status(t, os_name) != "disabled" else "missing"
```

Replace with a clearer two-line form:

```python
        st = eng.status(t, os_name)
        if st == "disabled":
            continue                                  # disabled tools aren't "missing"
        key = "installed" if eng.severity(st) == "silent" else "missing"
```

In `run_cli_tools`, after `actionable = audit_table(chosen, os_name)` and the `with_required` drag-in, add the disabled-dependency warning:

```python
    actionable = eng.with_required(actionable, all_tools, installed)
    for dep in eng.required_but_disabled(chosen, actionable):
        warn(f"{dep.name} is disabled but required by a selected tool — installing it anyway.")
```

- [ ] **Step 7: Run the full suite**

Run: `python3 -m unittest discover -s tests -p 'test_*.py'`
Expected: PASS (no references to the removed `"unwired"`/`"unknown"`/`"installed"` state strings remain).

- [ ] **Step 8: Commit**

```bash
git add tools/setup.py tests/test_setup.py
git commit -m "feat(setup): Pri/For/desc columns, sorted tables, severity-routed actions panel"
```

---

### Task 6: registry content — audience + desc on every row, disable pi, GSD state

**Files:**
- Modify: `tools/installer/registry.toml`
- Test: `tests/test_setup.py` (class `UnifiedManifestTests`)

- [ ] **Step 1: Write the failing tests**

Add to `class UnifiedManifestTests` in `tests/test_setup.py`:

```python
    def test_every_row_has_known_audience(self):
        for t in self.tools:
            self.assertIn(t.audience, {"ai", "human", "both"}, f"{t.id}: bad audience {t.audience!r}")

    def test_every_row_has_a_desc(self):
        for t in self.tools:
            self.assertTrue(t.desc, f"{t.id}: missing desc")

    def test_pi_is_disabled_by_default(self):
        pi = next(t for t in self.tools if t.id == "pi")
        self.assertFalse(pi.enabled)

    def test_gsd_has_state_block(self):
        g = next(t for t in self.tools if t.id == "gsd")
        self.assertTrue(g.state_file)
        self.assertEqual(g.state_update_key, "update_available")
```

- [ ] **Step 2: Run to verify they fail**

Run: `python3 -m unittest tests.test_setup.UnifiedManifestTests -v`
Expected: FAIL — desc missing / pi enabled / gsd has no state block.

- [ ] **Step 3: Add `audience` + `desc` to every `[[tool]]` row**

In `tools/installer/registry.toml`, add an `audience` and a `desc` line to each row using this exact mapping (id → audience → desc):

```
rg          ai     Fast recursive search; respects .gitignore automatically
fd          ai     Find files without find's syntax friction
jq          ai     Surgical queries and edits on JSON
yq          ai     Surgical queries and edits on YAML
gh          both   GitHub from the terminal: PRs, issues, releases
uv          both   Fast Python package and venv manager (replaces pip/venv)
volta       both   Version-pinned Node.js toolchain manager
pnpm        both   Fast, disk-efficient Node package manager
node        both   Node.js 22 LTS runtime
mmdc        ai     Render Mermaid diagrams to SVG/PNG for validation
eza         both   ls with tree view and git awareness
tmux        human  Terminal multiplexer: persistent sessions, background tasks
tokei       ai     Instant line/language stats to orient in a repo
ast-grep    ai     Structural (AST) search and rewrite, not textual
codegraph   ai     Code knowledge-graph MCP server for structural queries
pyright     ai     Python language server for type-aware navigation
opencode    both   Terminal AI coding agent (wired by gentle-ai)
pi          both   Pi coding agent (needs Node 22+)
bat         human  Syntax-highlighted cat with a git gutter
delta       human  Rich, readable git diffs
lazygit     human  Terminal UI for git
htop        human  Interactive process viewer
btop        human  Resource monitor with graphs
ncdu        human  Interactive disk-usage explorer
httpie      human  Human-friendly HTTP client
fzf         human  Fuzzy finder for files, history, anything
vim         human  Modal text editor
tree        both   Directory tree listing
ast-bro     ai     AST MCP server for structural code queries
dust        human  Intuitive du: disk usage by directory
sd          both   Simpler sed: intuitive find and replace
hyperfine   both   Statistical command-line benchmarking
tldr        human  Community cheatsheets for CLI commands
gron        ai     Flatten JSON into greppable lines
jless       human  Interactive JSON/YAML viewer
subl        human  Sublime Text launcher (GUI editor)
superpowers     ai    Skill marketplace: brainstorming, TDD, debugging workflows
agent-toolkit   ai    Softaworks skills and commands toolkit for agents
gsd             ai    Spec-driven phase planning and execution for agents
gentle-ai       both  Configurator that wires AI agents into your editors
```

For each row add the two lines, e.g. for `rg`:

```toml
audience = "ai"
desc = "Fast recursive search; respects .gitignore automatically"
```

- [ ] **Step 4: Disable `pi`**

In the `[[tool]]` block with `id = "pi"`, add:

```toml
enabled = false
```

- [ ] **Step 5: Add the `[tool.state]` block to `gsd`**

In the `gsd` `[[tool]]` block, after its `notes = ...` line, append:

```toml
[tool.state]
file = "~/.cache/gsd/gsd-update-check-opengsd-gsd-core.json"
installed_key = "installed"
latest_key = "latest"
update_key = "update_available"
```

(Note: a `[tool.state]` / `[tool.version]` sub-table must come AFTER all of that tool's
plain key/value lines, or `tomllib` will assign later bare keys to the sub-table. Keep
`audience`/`desc`/`enabled` above the `[tool.state]` block.)

- [ ] **Step 6: Run the tests to verify they pass**

Run: `python3 -m unittest tests.test_setup.UnifiedManifestTests -v`
Expected: PASS.

- [ ] **Step 7: Run the full suite**

Run: `python3 -m unittest discover -s tests -p 'test_*.py'`
Expected: PASS (all classes).

- [ ] **Step 8: Commit**

```bash
git add tools/installer/registry.toml tests/test_setup.py
git commit -m "feat(registry): audience+desc on all tools, disable pi, GSD state detection"
```

---

### Task 7: docs — document the new registry fields

**Files:**
- Modify: `docs/ia-helper-tools.md`

- [ ] **Step 1: Update the registry-schema section**

In `docs/ia-helper-tools.md`, find the "Common fields" schema section (near the
`priority = "P2"` example, ~line 554-565) and add documentation for the new fields:

```markdown
- `enabled` (bool, default `true`) — set `false` to keep a tool in the registry but
  hide it from installs. It renders as a dim `· disabled` row. If an enabled tool
  `requires` a disabled one, the dependency wins (it is installed anyway, with a warning).
- `audience` (`ai` | `human` | `both`, default `both`) — who the tool serves; shown as
  the `For` column.
- `desc` (string) — one-line "what it does", shown in the wizard. Keep the longer
  rationale in this document; `notes` stays an implementation detail.
- `pin` (string) — a version you intend to hold. When set, the tool never shows the
  `↑ update` state even if a newer version exists.

**`[tool.state]`** (launcher state-file detection) — for launchers (e.g. GSD) that
write their own status cache instead of exposing a binary version:

| Key | Meaning |
|-----|---------|
| `file` | path to the JSON the tool writes (e.g. `~/.cache/gsd/...json`) |
| `installed_key` | key holding the installed version |
| `latest_key` | key holding the latest version |
| `update_key` | boolean key: an update is available |

With a `[tool.state]` block the wizard reads status from disk — no `npx`/network call.
Absent file → `missing`; `update_key` true (and not `pin`) → `↑ update`; otherwise
`✓ current`.

**Status states & severity:** `✗ missing` (red) and `● needs wiring` (yellow) are
*loud* — they appear in the ACTIONS NEEDED panel. `↑ update` (cyan) is *calm* — a
one-line FYI, never an alarm. `◆ pinned` (blue), `✓ current` (green), and `· disabled`
(dim) are silent. Tools are listed sorted by priority (P0→P3), then category, then name.
```

- [ ] **Step 2: Commit**

```bash
git add docs/ia-helper-tools.md
git commit -m "docs: document enabled/audience/desc/pin and [tool.state]"
```

---

### Task 8: full verification + live smoke

**Files:** none (verification only)

- [ ] **Step 1: Run the whole suite**

Run: `python3 -m unittest discover -s tests -p 'test_*.py'`
Expected: PASS, count ≥ the previous 109 (new tests added).

- [ ] **Step 2: Smoke the CLI audit table**

Run: `printf '2\n\n' | uv run tools/setup.py` (menu 2 → CLI tools → Enter for all categories, then abort at the confirm prompt with Ctrl-C).
Expected: a table with `Pri / Tool / For / What it does / Status`, rows sorted P0→P3 then category then name; `pi` shows as `· disabled` (dim).

- [ ] **Step 3: Smoke the AI panel — GSD no longer nags**

Run: `printf '3\n' | uv run tools/setup.py` (menu 3 → AI tools; abort at the select prompt).
Expected: GSD shows `✓ current` (because `~/.cache/gsd/...json` has `update_available: false`) and is NOT in the ACTIONS NEEDED panel. If `pi` were enabled it would be the only `ai-cli` shown; confirm it's absent/dim.

- [ ] **Step 4: Confirm no banned strings crept in**

Run: `python3 -m unittest tests.test_setup.NoBareNpmTests -v`
Expected: PASS (npm/pip ban still holds).

- [ ] **Step 5: Final commit (if any uncommitted verification fixups)**

```bash
git add -A
git commit -m "test: verify installer registry UX end to end"
```

---

## Self-Review

**Spec coverage:**
- Decision 1 (sort priority→category→name) → Task 2 + applied in Task 5 tables. ✓
- Decision 2 (audience = `For` column) → Task 1 field + Task 5 `for_label`/columns + Task 6 data. ✓
- Decision 3 (six states, 4 severities) → Task 3 `status()`/`severity()` + Task 5 routing. ✓
- Decision 4 (GSD state-file, no npx) → Task 3 `_launcher_status` + Task 6 `[tool.state]`. ✓
- Decision 5 (one-line desc + tag, prose stays in docs) → Task 1 `desc` + Task 6 data + Task 7 docs. ✓
- Decision 6 (`enabled`, default true, dim, excluded) → Task 1 field + Task 3 short-circuit + Task 5 dim/summary + Task 6 disables pi. ✓
- Decision 7 (dependency override + warning) → Task 4 `required_but_disabled` + Task 5 Step 6 warning. ✓
- Decision 8 (`pin` suppresses update) → Task 1 field + Task 3 `_launcher_status` pin branch. ✓

**Placeholder scan:** no TBD/TODO; every code step shows full code. ✓

**Type consistency:** state strings (`missing`, `needs_wiring`, `alias_needed`, `update`,
`pinned`, `current`, `disabled`) are identical across `engine.py`, `setup.py`
`STATUS_ACCENT`, and tests. `for_label`, `sort_tools`, `severity`,
`required_but_disabled`, `_read_state_file`, `_launcher_status` names match between
definition and call sites. `[tool.state]` keys (`file`, `installed_key`, `latest_key`,
`update_key`) map to dataclass fields `state_file`, `state_installed_key`,
`state_latest_key`, `state_update_key` consistently. ✓
