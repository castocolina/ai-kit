# Cursor Agent statusline POC Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prove that `cursor-agent` can render a useful local status line (path/git/worktree/process RSS/system free RAM + model/context + included quota auto/API/total + on-demand ceiling + reset date) without implementing the multi-host backlog refactor.

**Architecture:** One stdlib-only script `tools/cursor-status-line-poc.py` that deliberately duplicates a lean subset of `tools/status-line.py` (SEGMENTS/LAYOUT/TOML, color ramps, packer, timing segments) and adds a Cursor-only quota fetch. No imports from the Claude status-line module. No setup/wizard/doctor changes. Findings feed later milestone work (Phase 999.4 design), but this POC ships and dies on its own branch.

**Tech Stack:** Python 3 stdlib (`json`, `tomllib`, `urllib.request`, `os`, `time`, `tempfile`), Cursor CLI stdin payload, read-only auth via Task 4 `resolve_auth_path` (ordered `is_file()` list: `$CURSOR_CONFIG_DIR/auth.json` → `$XDG_CONFIG_HOME/cursor/auth.json` → `~/.config/cursor/auth.json` → `~/.cursor/auth.json`), optional TOML at `~/.config/ai-kit/cursor-statusline-poc.toml`.

## Global Constraints

- Runtime: stdlib-only; run under `python3 -S`.
- Base worktree: this branch (`poc/cursor-statusline`); never checkout away from `main` in the primary workdir.
- Do not modify `tools/status-line.py`, `tools/setup.py`, wizard, doctor, or Claude wiring.
- Do not implement host-split / `common_*` / `claude_*` from `.planning/specs/2026-10-10-host-split-statusline-design.md`.
- Auth token: read-only; never log, print, cache, or pass on argv.
- Quota API is undocumented: show a dim `≈` on quota segments. On fetch failure:
  if a prior **good** cache exists, keep showing those numbers with `(stale)`;
  if there is no prior good cache, hide quota segments. Local segments always
  still render.
- Endpoint: HTTPS only; honor `CURSOR_API_ENDPOINT` if set, else `https://api2.cursor.sh`; do not follow redirects to a different host.
- Edits to the user's real Cursor `cli-config.json` (Task 3 POC
  `is_file()` fallthrough — wider than `setup.py`'s exclusive
  `CURSOR_CONFIG_DIR`/`~/.cursor`) require uz's explicit OK, atomic backup,
  and verified restore.
- Scratch and captured payloads live under `./tmp/` (gitignored).
- English-only in files, comments, commits, and findings docs.

## Relation to backlog 999.4

This POC does **not** close Phase 999.4. It produces evidence (real payload, quota JSON shape, latency, segment usefulness) that discuss/plan can consume. Duplicate code is intentional (ponytail: prove first, extract later).

## File map

| Path | Role |
|---|---|
| Create: `tools/cursor-status-line-poc.py` | Entire POC: defaults, cfg, probes, fmt/util subset, segments, quota fetch, shell |
| Create: `tools/cursor-statusline-poc.toml.sample` | Commented recipe mirroring Claude sample style |
| Create: `tests/test_cursor_status_line_poc.py` | Synthetic payload + fake HTTP + local probes (temp dirs only) |
| Required after Task 6 live pass: `$WORKTREE/tmp/cursor-statusline-poc-FINDINGS.md` | Live findings (gitignored; not committed) |
| Do not touch: `tools/status-line.py`, setup, wizard, doctor |

## Default layout (POC)

```
Line 0 (min_rows=0):  path, git_branch, alt_git_worktree, git_dirty
Line 1 (min_rows=0):  model_compact
Line 2 (min_rows=0):  included_total, included_auto, included_api, reset, on_demand
Line 3 (min_rows=0):  process_memory, system_memory, render_time, slowest
```

**`min_rows` policy (POC):** every line uses `min_rows=0`. Do **not** probe
terminal height and do **not** skip rows. (Claude's height gating is out of
scope; success criteria assume all four lines can render.)

### Segments

**Local (no Cursor backend / no Dashboard API):**

| id | Default | Source |
|---|---|---|
| `path` | on | **POC simplification (not Claude's `seg_path`):** show `os.path.basename(workspace.current_dir)`. Claude's real `seg_path` prefers git `root_name` / `util_display_dir` — out of scope for the POC. |
| `git_branch` | on | Shared git snapshot (one probe) |
| `alt_git_worktree` | **on** (unlike Claude default off) | Linked-worktree name or struck marker on main |
| `git_dirty` | on | Dirty marker from same snapshot |
| `process_memory` | on | RSS of host process: walk ancestors for `cursor-agent` / `agent` / basename match; fall back to self RSS if none found (unlike Claude's `claude`-only walk) |
| `system_memory` | on | Available RAM: adapt `examples/segments/system_memory` (`MemAvailable` / `vm_stat`) **in-process**, not as external drop-in |
| `render_time` | on | Whole-script wall time; color bands copy Claude `_RAMP_DEFAULTS["render_time"]` (**50 ms / 150 ms**) |
| `slowest` | on | Slowest non-meta segment name + ms; bands copy Claude `_RAMP_DEFAULTS["slowest"]` (**15 ms / 40 ms**). Meta segments `render_time`/`slowest` are timed in a **second pass** after other `seg_*` (Claude `_SLOWEST_META` pattern) so they do not win "slowest" of themselves |

**From statusLine payload (no network):**

| id | Default | Source |
|---|---|---|
| `model_compact` | on | Binding text: `{display_name}` then, when `context_window_size` is a positive int, `· {fmt_tokens(size)}` (Claude `fmt_tokens`: `200000`→`200K`); then, when `param_summary` is a non-empty string, `· {param_summary}` verbatim; then, when `used_percentage` is a number, `· {int(pct)}%` (omit `%` when null/absent — never show `0`/`None`); when `max_mode` is true, append `· max` (exact marker string); width from `render_width_chars` when a positive int, else no width trim in POC |

**From Dashboard API (network, cached):**

| id | Default | Source |
|---|---|---|
| `included_total` | on | Text: `inc {int(total_pct)}%` + pace-gap color on the `%` via `util_gap_color(abs(gap), theme)`; hide if `total_pct` is `None` |
| `included_auto` | on | Text: `auto {int(auto_pct)}%` (same gap color); hide if `auto_pct` is `None` |
| `included_api` | on | Text: `api {int(api_pct)}%` (same gap color); hide if `api_pct` is `None` |
| `reset` | on | Text: `↺ {YYYY-MM-DD} ({n}d)` from `cycle_end_ms` in **UTC** (`datetime.fromtimestamp(ms/1000, tz=timezone.utc).date()`); `n = max(0, ceil((end_ms - now_ms) / 86400000))`; hide if `cycle_end_ms` missing/0 |
| `on_demand` | on | `disabled` → `od off`; `fixed` → `od $used/$ceiling` (1 decimal used); `unlimited` → `od $used no cap`; hide if `unavailable`; highlight when included ≥ 100% and on-demand used > 0 |

All quota segments append dim `≈` as `{_DIM}≈{RESET}` where `_DIM = "\033[90m"` and `RESET = "\033[0m"` (same constants as Claude `tools/status-line.py`). Stale cache appends `(stale)`.

## Config

Path: `${XDG_CONFIG_HOME:-$HOME/.config}/ai-kit/cursor-statusline-poc.toml`  
Env override: `AI_KIT_CURSOR_POC_CONFIG_FILE` (POC-only; do not use `CC_AI_KIT_*`).

Same merge semantics as Claude: `[segments]` merges; `[[line]]` is all-or-nothing if any `[[line]]` is present.

---

### Task 1: Scaffold + payload render

**Files:**
- Create: `tools/cursor-status-line-poc.py`
- Create: `tests/test_cursor_status_line_poc.py`
- Create: `tools/cursor-statusline-poc.toml.sample` (stub header only)

**Interfaces:**
- Produces: `main(argv: list[str] | None = None, stdin: BinaryIO | None = None, env: dict | None = None) -> int`; `safe_render(raw: bytes, env, *, now: float | int | None = None) -> str` (never raises); `render_for_test(payload, env, *, now=None) -> str`; `render_from_raw(raw, env, *, dump_payload_path=None, now=None) -> str`; `SEGMENTS`, `LAYOUT`; `load_config(env) -> Config`; `default_theme() -> Theme` where `Theme` is a small class/NamedTuple with method `c(name: str) -> str` returning an SGR prefix (enough for gap/memory colors — same call shape as Claude `theme.c(...)`); every `seg_*(ctx, avail: int, theme: Theme) -> str | None`
- **Context type (binding from Task 1):** `types.SimpleNamespace` only (attribute access). Build it in `build_context(payload, env, *, now=None)`. Never a plain dict for `ctx`.
- Consumes: Cursor-shaped stdin (synthetic in tests); optional TOML via `AI_KIT_CURSOR_POC_CONFIG_FILE` or `${XDG_CONFIG_HOME:-$HOME/.config}/ai-kit/cursor-statusline-poc.toml`

- [ ] **Step 1: Write the failing test**

```python
import io, json, os, tempfile, types, unittest
from pathlib import Path

# Load hyphenated module by path
import importlib.util
POC = Path(__file__).resolve().parents[1] / "tools" / "cursor-status-line-poc.py"

def load_poc():
    spec = importlib.util.spec_from_file_location("cursor_status_line_poc", POC)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

class TestPayloadRender(unittest.TestCase):
    def test_model_and_path_from_payload(self):
        mod = load_poc()
        payload = {
            "session_id": "t",
            "model": {"id": "x", "display_name": "GPT POC", "param_summary": "High"},
            "workspace": {"current_dir": "/tmp/poc-proj"},
            "context_window": {
                "used_percentage": 34.5,
                "context_window_size": 200000,
            },
            "render_width_chars": 100,
        }
        with tempfile.TemporaryDirectory() as td:
            env = {"HOME": td, "XDG_CONFIG_HOME": td, "XDG_CACHE_HOME": td}
            out = mod.render_for_test(payload, env)
        self.assertIn("GPT POC", out)
        self.assertIn("34", out)
        self.assertIn("poc-proj", out)
        self.assertIn("200K", out)  # fmt_tokens(200000)
        self.assertIn("High", out)  # param_summary verbatim

    def test_null_context_pct_omits_percent(self):
        mod = load_poc()
        payload = {
            "model": {"display_name": "M"},
            "workspace": {"current_dir": "/tmp/x"},
            "context_window": {"used_percentage": None, "context_window_size": 1000},
        }
        with tempfile.TemporaryDirectory() as td:
            out = mod.render_for_test(payload, {"HOME": td, "XDG_CONFIG_HOME": td, "XDG_CACHE_HOME": td})
        self.assertIn("M", out)
        self.assertNotIn("None", out)
        self.assertNotRegex(out, r"\b0%\b")

    def test_max_mode_marker(self):
        mod = load_poc()
        payload = {
            "model": {"display_name": "M", "max_mode": True},
            "workspace": {"current_dir": "/tmp/x"},
            "context_window": {"used_percentage": 1, "context_window_size": 1000},
        }
        with tempfile.TemporaryDirectory() as td:
            out = mod.render_for_test(payload, {"HOME": td, "XDG_CONFIG_HOME": td, "XDG_CACHE_HOME": td})
        self.assertIn("· max", out)

    def test_toml_segments_merge_and_line_replace(self):
        mod = load_poc()
        with tempfile.TemporaryDirectory() as td:
            cfg = Path(td) / "ai-kit" / "cursor-statusline-poc.toml"
            cfg.parent.mkdir(parents=True)
            cfg.write_text(
                '[segments]\npath = false\n\n[[line]]\nmin_rows = 0\nsegments = ["model_compact"]\n',
                encoding="utf-8",
            )
            env = {"HOME": td, "XDG_CONFIG_HOME": td, "XDG_CACHE_HOME": td}
            c = mod.load_config(env)
            self.assertFalse(c.segments["path"])
            self.assertEqual(c.layout, [(0, ["model_compact"])])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `WORKTREE="$(git rev-parse --show-toplevel)" && cd "$WORKTREE" && python3 -m unittest tests.test_cursor_status_line_poc.TestPayloadRender -v`  
Expected: FAIL (module missing or `render_for_test` undefined)

- [ ] **Step 3: Write minimal implementation (no dump yet)**

Implement in `tools/cursor-status-line-poc.py`:
- Module docstring: "Cursor Agent statusline POC — not production; duplicates lean status-line patterns."
- `SEGMENTS` / `LAYOUT` as in the segment tables (**all keys default `True`**). For every LAYOUT id, define `seg_*` immediately — unimplemented ones return `None` (hide) so the packer never KeyErrors. Task 2 replaces local probe stubs; Task 5 replaces quota `seg_*` stubs (Task 4 only implements `fetch_quota` / normalize / cache — not segments).
- Parse stdin JSON; `build_context(...)` → `SimpleNamespace` with at least `work_dir`, `model_name`, `param_summary`, `max_mode` (bool from `model.max_mode`, default `False`), `context_pct` (float|None), `context_max`, `cols`, `config`, `theme`, and later quota fields.
- Every segment is `seg_x(ctx, avail, theme) -> str | None` from day one.
- **Width helpers (Task 1 deliverables):** copy/adapt `util_char_width` + `util_visible_width` from Claude (ANSI-stripped, emoji-aware). Packer and any `util_first_fitting` use these — never raw `len()` for column budgets.
- **Packer / two-pass render (Task 1 scaffold; Task 2 fills timing):**
  1. `ctx.cols` = positive `render_width_chars` else POC default `80`; `ctx.t_start = time.perf_counter_ns()` at render start; `ctx.slowest = None`; `SEP = " | "`.
  2. **Pass A (non-meta):** for each LAYOUT line, shrinking `avail` from `ctx.cols`; for each enabled key **not** in `_SLOWEST_META = frozenset({"render_time", "slowest"})`, time the builder, on success store text in `built[(line_i, key)]` and crown `ctx.slowest = (key, ns)` when slower (never crown meta). **POC exception policy (binding, not Claude):** on builder exception store nothing and continue — do **not** emit Claude's `⚠key` warning marker.
  3. **Pass B (meta):** build `render_time` / `slowest` **once** into `meta_built: dict[str, str]` with full `ctx.cols` budget from settled `ctx.t_start` / `ctx.slowest` (Claude `core_build_meta`).
  4. **Assemble (Claude Phase C shape):** for each LAYOUT row, `line_built = {k: v for (i,k), v in built.items() if i == line_i}`; then `line_built.update(meta_built)` so meta strings land at their **LAYOUT positions** on that row (not forced last, not extra rows); re-fit left→right with known `util_visible_width` + `SEP`; omit empty rows; **ignore `min_rows`**. Join rows with `"\n"`. `safe_render` / `render_for_test` / `render_from_raw` return that string.
- `load_config(env)`: if config file missing, return defaults. If present: merge `[segments]` over defaults; if any `[[line]]` present, replace layout entirely with those lines (all-or-nothing). Honor `AI_KIT_CURSOR_POC_CONFIG_FILE` when set.
- `default_theme()`: `Theme` with `.c(name)` for at least `GREY`, `CYAN`, `GREEN`, `YELLOW`, `ORANGE`, `RED`, `BLUE`, `WHITE` (copy Claude `_PALETTE_DEFAULTS` values), **and** `theme.ramps` containing only bands that exist in Claude `_RAMP_DEFAULTS` and that the POC uses: `render_time` and `slowest`. Resolve thresholds to **nanoseconds** before `util_pick_color` (Claude: `util_parse_threshold` + `core_resolve_ramp` → e.g. `50ms`→`5e7`, `150ms`→`1.5e8`, `15ms`→`1.5e7`, `40ms`→`4e7`, colors as SGR escapes). **Gap coloring is separate:** copy Claude `util_gap_color` hardcoded inclusive bands (`<=5` GREEN, `<11` YELLOW, `<=15` ORANGE, else RED) — `_RAMP_DEFAULTS` has **no** `gap` key; do not invent one.
- **Time units (binding):** `now` / `fetched_at` are **epoch seconds** (float/int) for cache TTL. Billing cycle fields and `billing_pace_gap` / `context_from_quota(..., now_ms=)` use **epoch milliseconds**. Prefer a single `now = time.time()` default in render helpers; Task 5 converts `now_ms = int(now * 1000)` when it wires `context_from_quota`.
- `render_for_test(payload, env, *, now=None) -> str` — **no** dump parameter.
- `safe_render(raw, env, *, now=None) -> str`: never raises; bad or empty JSON → return `""` (binding). **Ownership (B):** Task 1 defines a stub `fetch_quota(...)` (hide-shaped empty quota) but **does not call it** from `safe_render` / `render_for_test` / `render_from_raw` — Task 1 render is local+payload segments only. Task 4 replaces the stub body. **Task 5 alone** adds the `fetch_quota` call + `context_from_quota` merge + try/except hide-on-error (see Task 5 Interfaces).
- **Host failure contract (POC binding):** `main` always returns `0`, including when stdout is empty. Cursor's keep-previous behavior requires non-zero exit + empty stdout; this POC **accepts blanking** the statusline on bad/empty JSON rather than preserving the prior line. Do not return non-zero from `main`.
- `main(argv=None, stdin=None, env=None) -> int`: read stdin bytes, print `safe_render` result, return 0 even on parse errors. (**Dump flag is Step 4 — not here.**)

- [ ] **Step 4: Add failing dump tests first, then implement dump until green**

Dump ownership: `render_from_raw` + `main --dump-payload` only.

```python
class TestDumpPayload(unittest.TestCase):
    def test_dump_payload_writes_exact_raw_bytes(self):
        mod = load_poc()
        raw = b'{"model":{"display_name":"D"},"workspace":{"current_dir":"/tmp/x"},'
        raw += b'"context_window":{"used_percentage":1,"context_window_size":1000}}\n'
        with tempfile.TemporaryDirectory() as td:
            dump = Path(td) / "out" / "payload.json"
            env = {"HOME": td, "XDG_CONFIG_HOME": td, "XDG_CACHE_HOME": td}
            mod.render_from_raw(raw, env, dump_payload_path=str(dump))
            self.assertEqual(dump.read_bytes(), raw)

    def test_main_dump_payload_argv(self):
        mod = load_poc()
        raw = b'{"model":{"display_name":"D"},"workspace":{"current_dir":"/tmp/x"},'
        raw += b'"context_window":{"used_percentage":1,"context_window_size":1000}}\n'
        with tempfile.TemporaryDirectory() as td:
            dump = Path(td) / "p.json"
            env = {"HOME": td, "XDG_CONFIG_HOME": td, "XDG_CACHE_HOME": td}
            rc = mod.main(
                argv=["cursor-status-line-poc.py", "--dump-payload", str(dump)],
                stdin=io.BytesIO(raw),
                env=env,
            )
            self.assertEqual(rc, 0)
            self.assertEqual(dump.read_bytes(), raw)

    def test_main_never_raises_on_bad_stdin(self):
        mod = load_poc()
        with tempfile.TemporaryDirectory() as td:
            env = {"HOME": td, "XDG_CONFIG_HOME": td, "XDG_CACHE_HOME": td}
            rc = mod.main(argv=["poc"], stdin=io.BytesIO(b"not-json"), env=env)
            self.assertEqual(rc, 0)
            rc2 = mod.main(argv=["poc"], stdin=io.BytesIO(b""), env=env)
            self.assertEqual(rc2, 0)

    def test_python_s_import(self):
        import subprocess, sys
        with tempfile.TemporaryDirectory() as td:
            env = {
                "HOME": td, "XDG_CONFIG_HOME": td, "XDG_CACHE_HOME": td,
                "PATH": os.environ.get("PATH", ""),
                "LANG": os.environ.get("LANG", "C.UTF-8"),
            }
            # Isolated env: no real auth.json / CURSOR_* so fetch_quota cannot
            # touch uz credentials or POST to api2.cursor.sh under unittest.
            r = subprocess.run(
                [sys.executable, "-S", str(POC)],
                input=b"{}",
                capture_output=True,
                env=env,
            )
        self.assertNotIn(b"ImportError", r.stderr)
        self.assertNotIn(b"ModuleNotFoundError", r.stderr)
```

Implement dump after these tests fail: `--dump-payload PATH` on `main` / `render_from_raw` creates parent dirs (`Path(path).parent.mkdir(parents=True, exist_ok=True)`), writes exact stdin bytes via mkstemp+`os.replace`, then renders.

- [ ] **Step 5: Run tests to verify they pass**

```bash
WORKTREE="$(git rev-parse --show-toplevel)" && cd "$WORKTREE"
python3 -m unittest tests.test_cursor_status_line_poc.TestPayloadRender tests.test_cursor_status_line_poc.TestDumpPayload -v
```

Expected: PASS (`render_from_raw` and `main(--dump-payload)` preserve exact bytes)

```bash
WORKTREE="$(git rev-parse --show-toplevel)" && cd "$WORKTREE"
mkdir -p tmp
printf '%s' '{"model":{"display_name":"S","param_summary":"High","max_mode":true},"workspace":{"current_dir":"/tmp/x"},"context_window":{"used_percentage":1,"context_window_size":1000}}' \
  | python3 -S tools/cursor-status-line-poc.py >tmp/poc-s.out
test -s tmp/poc-s.out
rg -q High tmp/poc-s.out
```

Expected: exit 0, non-empty stdout under `$WORKTREE/tmp/` including `param_summary` and `· max` (stdlib-only under `-S`).

- [ ] **Step 6: Register the test module in gates, then commit**

Add `tests.test_cursor_status_line_poc` next to the other unittest modules in:
- `Makefile` target `test-unit` (the `python3 -m unittest …` list)
- `.pre-commit-config.yaml` `unittest` hook `entry` / `args` list (same pattern as `tests.test_status_line`)

```bash
git add tools/cursor-status-line-poc.py tools/cursor-statusline-poc.toml.sample \
  tests/test_cursor_status_line_poc.py Makefile .pre-commit-config.yaml
git commit -m "$(cat <<'EOF'
poc: cursor statusline stub from stdin payload

Prove model/context/path render under python3 -S without touching the Claude status-line.
EOF
)"
```

---

### Task 2: Local segments — git, worktree, process RSS, system RAM

**Files:**
- Modify: `tools/cursor-status-line-poc.py`
- Modify: `tests/test_cursor_status_line_poc.py`
- Modify: `tools/cursor-statusline-poc.toml.sample`

**Interfaces:**
- Produces: `probe_git_snapshot(work_dir) -> dict` with keys `in_repo: bool`, `branch: str`, `dirty: str` where dirty is one of `"clean"|"modified"|"untracked"` (same three-state strings Claude uses; **not** a bool), `is_worktree: bool`, `wt_name: str` (**POC uses a plain dict**, not Claude's `GitSnapshot` NamedTuple). **`probe_git_for(ctx)`** memoizes one snapshot per render on `ctx` (Claude pattern: store under `ctx._git` / `_memo`); `seg_git_branch` / `seg_git_dirty` / `seg_alt_git_worktree` call **only** `probe_git_for(ctx)`, never bare `probe_git_snapshot` — guarantees one probe per render for `slowest` timing. Unit tests that patch `probe_git_snapshot` still work because `probe_git_for` calls it. `probe_process_rss_bytes() -> int` (always an int: host match or **self RSS fallback** — never `None`). `probe_system_available_bytes() -> int | None`. Segments: `git_branch`, `git_dirty`, `alt_git_worktree`, `process_memory`, `system_memory`, `seg_render_time`, `seg_slowest` (second-pass meta).
- Consumes: Task 1 context + `workspace.current_dir`

- [ ] **Step 1: Write the failing tests**

```python
class TestLocalProbes(unittest.TestCase):
    def test_system_available_bytes_positive_on_linux(self):
        mod = load_poc()
        n = mod.probe_system_available_bytes()
        if os.path.exists("/proc/meminfo"):
            self.assertIsNotNone(n)
            self.assertGreater(n, 0)

    def test_process_rss_returns_int(self):
        if not Path("/proc").is_dir():
            self.skipTest("Linux /proc required for POC RSS probe")
        mod = load_poc()
        n = mod.probe_process_rss_bytes()
        self.assertIsInstance(n, int)
        self.assertGreater(n, 0)

    def test_git_branch_in_repo(self):
        mod = load_poc()
        root = str(Path(__file__).resolve().parents[1])
        snap = mod.probe_git_snapshot(root)
        self.assertIsInstance(snap, dict)
        self.assertTrue(snap["in_repo"])
        self.assertIn(snap["dirty"], ("clean", "modified", "untracked"))
        self.assertTrue(snap["branch"] or snap["is_worktree"])

    def test_worktree_struck_on_main_checkout(self):
        mod = load_poc()
        theme = mod.default_theme()
        ctx = types.SimpleNamespace(work_dir="/tmp/x", home="/tmp")
        # Patch probe to a main-checkout snapshot (in_repo, not linked worktree).
        mod.probe_git_snapshot = lambda _wd: {
            "in_repo": True, "branch": "main", "dirty": "clean",
            "is_worktree": False, "wt_name": "",
        }
        s = mod.seg_alt_git_worktree(ctx, 80, theme)
        self.assertIsNotNone(s)
        self.assertIn("⎇", s)
        self.assertIn("\033[9m", s)  # struck
        self.assertIn(theme.c("GREY"), s)

    def test_worktree_cyan_on_linked(self):
        mod = load_poc()
        theme = mod.default_theme()
        ctx = types.SimpleNamespace(work_dir="/tmp/x", home="/tmp")
        mod.probe_git_snapshot = lambda _wd: {
            "in_repo": True, "branch": "feat", "dirty": "clean",
            "is_worktree": True, "wt_name": "poc-wt",
        }
        s = mod.seg_alt_git_worktree(ctx, 80, theme)
        self.assertIsNotNone(s)
        self.assertIn("poc-wt", s)
        self.assertIn(theme.c("CYAN"), s)
        self.assertNotIn("\033[9m", s)

    def test_process_memory_fmt_shape(self):
        mod = load_poc()
        theme = mod.default_theme()
        ctx = types.SimpleNamespace()
        mod.probe_process_rss_bytes = lambda: 85 * 1024 * 1024
        s = mod.seg_process_memory(ctx, 80, theme)
        self.assertIsNotNone(s)
        self.assertIn("🧮", s)
        self.assertRegex(s, r"\d+(\.\d)?MB")  # fmt_bytes, no space before unit

    def test_system_memory_long_form(self):
        mod = load_poc()
        theme = mod.default_theme()
        ctx = types.SimpleNamespace()
        mod.probe_system_available_bytes = lambda: int(5.5 * 1024**3)
        s = mod.seg_system_memory(ctx, 80, theme)
        self.assertIsNotNone(s)
        self.assertIn("GiB free", s)

    def test_slowest_skips_meta_second_pass(self):
        mod = load_poc()
        # After a full render, slowest must not name render_time/slowest themselves.
        payload = {
            "model": {"display_name": "M"},
            "workspace": {"current_dir": str(Path(__file__).resolve().parents[1])},
            "context_window": {"used_percentage": 1, "context_window_size": 1000},
            "render_width_chars": 200,
        }
        with tempfile.TemporaryDirectory() as td:
            out = mod.render_for_test(
                payload, {"HOME": td, "XDG_CONFIG_HOME": td, "XDG_CACHE_HOME": td})
        # Meta segments exist in LAYOUT; if slowest appears it must not be self-referential.
        if "🐌" in out:
            self.assertNotRegex(out, r"🐌\s*(render_time|slowest)\b")

    def test_git_probe_once_per_render(self):
        mod = load_poc()
        n = {"calls": 0}
        real = mod.probe_git_snapshot
        def counted(wd):
            n["calls"] += 1
            return real(wd)
        mod.probe_git_snapshot = counted
        payload = {
            "model": {"display_name": "M"},
            "workspace": {"current_dir": str(Path(__file__).resolve().parents[1])},
            "context_window": {"used_percentage": 1, "context_window_size": 1000},
            "render_width_chars": 200,
        }
        with tempfile.TemporaryDirectory() as td:
            mod.render_for_test(
                payload, {"HOME": td, "XDG_CONFIG_HOME": td, "XDG_CACHE_HOME": td})
        self.assertEqual(n["calls"], 1)  # probe_git_for memo across branch/dirty/worktree
```

Real-filesystem linked worktree creation is still Task 2 smoke / Task 6 live only; the cyan path is unit-covered via the synthetic snapshot above.

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m unittest tests.test_cursor_status_line_poc.TestLocalProbes -v`  
Expected: FAIL (probes missing)

- [ ] **Step 3: Implement probes + segments**

Copy/adapt patterns from `tools/status-line.py` and `examples/segments/system_memory`:
- One git rev-parse snapshot via `probe_git_snapshot`; expose through `probe_git_for(ctx)` so all three git segments share one call per render. Dirty is `"clean"|"modified"|"untracked"`; `git_dirty` renders a glyph only when dirty ≠ `"clean"` (do not invent a bool API).
- **`alt_git_worktree` (binding, match Claude `seg_alt_git_worktree`):** hide when not `in_repo`; on main checkout (`is_worktree` false) show dim struck `{GREY}\033[9m⎇ wt{RESET}`; on linked worktree show `{CYAN}⎇ {wt_name}{RESET}` (name via `util_two_state_cap` 30/20).
- `process_memory`: **Linux POC** — walk `/proc/self` → parent chain; match comm in `{"cursor-agent", "agent"}` or containing `cursor-agent`; else self RSS. Always returns `int` when `/proc` exists; if `/proc` is absent, return self RSS via Claude-style `ps` fallback or `1` as last resort so the type contract holds. Gate `test_process_rss_returns_int` with `if not Path("/proc").is_dir(): self.skipTest("Linux /proc required")` when only `/proc` path is implemented. Format with Claude's `util_icon` + `fmt_bytes` (`KB`/`MB`/`GB`, no space before the unit — e.g. `🧮 85MB`, **not** `MiB` or `85 MB`).
- `system_memory`: read available bytes the same way as `examples/segments/system_memory` (`MemAvailable` / `vm_stat`). **Text shape (binding, match the example exactly):** long `💻 {gib:.1f} GiB free`; medium `💻 {gib:.1f}G`; short `💻{gib:.0f}G` (icon kept). **Color policy:** absolute thresholds from the example (green if free ≥ 4 GiB, yellow if ≥ 1 GiB, else red).
- Enable all local segments in default `SEGMENTS`; document in sample TOML.
- Implement `seg_render_time` / `seg_slowest` against Task 1’s two-pass packer: `render_time` colors `perf_counter_ns() - ctx.t_start` via `util_pick_color(..., theme.ramps["render_time"])`; `slowest` reads `ctx.slowest` `(name, ns)` and colors ns via `theme.ramps["slowest"]`. Format durations with a copied `fmt_duration`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m unittest tests.test_cursor_status_line_poc.TestLocalProbes -v`  
Expected: PASS

- [ ] **Step 5: Manual smoke**

```bash
WORKTREE="$(git rev-parse --show-toplevel)" && cd "$WORKTREE"
echo '{"model":{"display_name":"X"},"workspace":{"current_dir":"'"$PWD"'"},"context_window":{"used_percentage":10,"context_window_size":100000},"render_width_chars":120}' \
  | python3 -S tools/cursor-status-line-poc.py
```

Expected: multi-line output including path/branch and memory segments (no crash).

- [ ] **Step 6: Commit**

```bash
git add tools/cursor-status-line-poc.py tools/cursor-statusline-poc.toml.sample tests/test_cursor_status_line_poc.py
git commit -m "$(cat <<'EOF'
poc: local git/worktree/memory segments for cursor statusline

Copy lean probes so the POC shows host-local context without Dashboard calls.
EOF
)"
```

---

### Task 3: Capture a real Cursor statusLine payload

**Files:**
- None in repo (writes only under `$WORKTREE/tmp/`, gitignored)
- Temporarily edits the resolved Cursor `cli-config.json` with uz approval
- Requires Task 1's `--dump-payload` already implemented and tested

**Interfaces:**
- Produces: `$WORKTREE/tmp/cursor-payload.json`, `$WORKTREE/tmp/cli-config.json.bak`
- Consumes: live `cursor-agent` session; Task 1 CLI

**Path rules:** Every command below starts with
`WORKTREE="$(git rev-parse --show-toplevel)"` and `cd "$WORKTREE"`. Never use
bare relative `tmp/` without that `cd`.

**`cli-config.json` resolution (POC ordered `is_file()` fallthrough — intentional, not a copy of `setup.py`):**

`tools/setup.py` `resolve_paths` sets `cursor_dir` exclusively as `CURSOR_CONFIG_DIR` or `~/.cursor` (no XDG leg, no `is_file()` fallthrough). This POC **widens** discovery so live wire still finds the file when only `~/.cursor/cli-config.json` exists under a set `XDG_CONFIG_HOME` (design §2 verified location):

```python
def resolve_cli_config_path(env=os.environ) -> Path:
    home = Path(env.get("HOME") or Path.home())
    cands: list[Path] = []
    if env.get("CURSOR_CONFIG_DIR"):
        cands.append(Path(env["CURSOR_CONFIG_DIR"]) / "cli-config.json")
    if env.get("XDG_CONFIG_HOME"):
        cands.append(Path(env["XDG_CONFIG_HOME"]) / "cursor" / "cli-config.json")
    cands.append(home / ".cursor" / "cli-config.json")  # design §2 verified
    cands.append(home / ".config" / "cursor" / "cli-config.json")
    for p in cands:
        if p.is_file():
            return p
    raise SystemExit(
        "refuse: no cli-config.json among: " + ", ".join(str(p) for p in cands)
    )
```

If none exist, **refuse** via `SystemExit` (same as the Step 2–3 scripts — one binding). Do not create a new cli-config. Print every candidate so uz can set `CURSOR_CONFIG_DIR` or confirm the right file. Get uz confirmation before editing.

- [ ] **Step 1: Get uz approval** to backup and temporarily set `statusLine` on the resolved path.

- [ ] **Step 2: Atomic backup** (from `$WORKTREE`)

```bash
cd "$WORKTREE"
python3 - <<'PY'
import os
from pathlib import Path

def resolve_cli_config_path(env=os.environ) -> Path:
    home = Path(env.get("HOME") or Path.home())
    cands = []
    if env.get("CURSOR_CONFIG_DIR"):
        cands.append(Path(env["CURSOR_CONFIG_DIR"]) / "cli-config.json")
    if env.get("XDG_CONFIG_HOME"):
        cands.append(Path(env["XDG_CONFIG_HOME"]) / "cursor" / "cli-config.json")
    cands += [home / ".cursor" / "cli-config.json",
              home / ".config" / "cursor" / "cli-config.json"]
    for p in cands:
        if p.is_file():
            return p
    raise SystemExit("refuse: no cli-config among: " + ", ".join(map(str, cands)))

p = resolve_cli_config_path()
raw = p.read_bytes()
Path("tmp").mkdir(parents=True, exist_ok=True)
Path("tmp/cli-config.path.txt").write_text(str(p.resolve()) + "\n", encoding="utf-8")
bak = Path("tmp/cli-config.json.bak")
bak.write_bytes(raw)
print("chose", p)
print("backed up", len(raw), "bytes to", bak.resolve())
PY
```

- [ ] **Step 3: Atomic wire of `statusLine`**

```bash
cd "$WORKTREE"
python3 - <<'PY'
import json, os, shlex, tempfile
from pathlib import Path

def resolve_cli_config_path(env=os.environ) -> Path:
    home = Path(env.get("HOME") or Path.home())
    cands = []
    if env.get("CURSOR_CONFIG_DIR"):
        cands.append(Path(env["CURSOR_CONFIG_DIR"]) / "cli-config.json")
    if env.get("XDG_CONFIG_HOME"):
        cands.append(Path(env["XDG_CONFIG_HOME"]) / "cursor" / "cli-config.json")
    cands += [home / ".cursor" / "cli-config.json",
              home / ".config" / "cursor" / "cli-config.json"]
    for p in cands:
        if p.is_file():
            return p
    raise SystemExit("refuse: no cli-config among: " + ", ".join(map(str, cands)))

wt = Path.cwd().resolve()
p = resolve_cli_config_path()
data = json.loads(p.read_text(encoding="utf-8"))
if not isinstance(data, dict):
    raise SystemExit("refuse: cli-config is not a JSON object")
script = wt / "tools" / "cursor-status-line-poc.py"
dump = wt / "tmp" / "cursor-payload.json"
cmd = (
    "python3 -S "
    + shlex.quote(str(script))
    + " --dump-payload "
    + shlex.quote(str(dump))
)
data["statusLine"] = {
    "type": "command",
    "command": cmd,
    "updateIntervalMs": 3000,
    "timeoutMs": 10000,
}
text = json.dumps(data, indent=2) + "\n"
fd, tmp = tempfile.mkstemp(dir=str(p.parent), prefix=".cli-config.", suffix=".tmp")
try:
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(tmp, p)
finally:
    if os.path.exists(tmp):
        os.unlink(tmp)
# verify
assert json.loads(p.read_text())["statusLine"]["command"] == cmd
print("wired", p)
print("NOTE: on any failure after this point, run Task 3 Step 5 restore immediately")
PY
```

**Restore-on-failure (binding):** After Step 3 succeeds, if Step 4 fails, the agent aborts, or uz cancels — run Step 5 restore before doing anything else (treat Steps 3–5 as try/finally). Do not leave a wired dump command overnight unless uz explicitly asks to keep it.

POC choice for kill/timeout window (binding, must match Task 4):

```json
"statusLine": {
  "type": "command",
  "command": "…",
  "updateIntervalMs": 3000,
  "timeoutMs": 10000
}
```

Fetch is **sequential, 800 ms per call, up to ~2.4 s** wall on a cold miss (three methods). Raising `updateIntervalMs` to 3000 and `timeoutMs` to 10000 makes a successful cold fetch the expected path during POC live wire. Still serve last-good / hide quota if killed; do **not** claim the POC works at the CLI defaults (300 / 2000).

- [ ] **Step 4: Run `cursor-agent` one turn; confirm `$WORKTREE/tmp/cursor-payload.json` exists and is valid JSON.**

- [ ] **Step 5: Atomic restore from backup + verify**

Restore **only** to the path recorded in `tmp/cli-config.path.txt` (written in Step 2). Refuse if that file or the backup is missing.

```bash
cd "$WORKTREE"
python3 - <<'PY'
import os, tempfile
from pathlib import Path
meta, bak = Path("tmp/cli-config.path.txt"), Path("tmp/cli-config.json.bak")
if not meta.is_file() or not bak.is_file():
    raise SystemExit("refuse: missing tmp/cli-config.path.txt or .bak")
p = Path(meta.read_text(encoding="utf-8").strip())
raw = bak.read_bytes()
fd, tmp = tempfile.mkstemp(dir=str(p.parent), prefix=".cli-config.", suffix=".tmp")
try:
    with os.fdopen(fd, "wb") as f:
        f.write(raw)
    os.replace(tmp, p)
finally:
    if os.path.exists(tmp):
        os.unlink(tmp)
assert p.read_bytes() == raw
print("restored", p, "bytes", len(raw))
PY
```

- [ ] **Step 6: Diff payload against Task 1 bindings, amend if needed, then record notes**

```bash
WORKTREE="$(git rev-parse --show-toplevel)" && cd "$WORKTREE"
python3 - <<'PY'
import json
from pathlib import Path
p = Path("tmp/cursor-payload.json")
raw = json.loads(p.read_text(encoding="utf-8"))
required = [
    ("model.display_name", lambda d: isinstance((d.get("model") or {}).get("display_name"), str)),
    ("workspace.current_dir", lambda d: isinstance((d.get("workspace") or {}).get("current_dir"), str)),
    ("context_window", lambda d: isinstance(d.get("context_window"), dict)),
]
def dig(d, path):
    cur = d
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur
optional = ["model.param_summary", "model.max_mode", "context_window.used_percentage",
            "context_window.context_window_size", "render_width_chars"]
miss = [name for name, ok in required if not ok(raw)]
if miss:
    raise SystemExit(f"AMEND Task 1 bindings before Task 4+: missing/wrong {miss}")
present = [k for k in optional if dig(raw, k) is not None]
print("payload ok for Task 1 bindings; optional present:", present)
PY
```

If the gate fails: amend Task 1 field paths / tests / `model_compact` bindings in this plan and re-run Task 1 tests before continuing to Task 4. Record notes in `$WORKTREE/tmp/cursor-statusline-poc-FINDINGS.md`: which optional fields were present (`param_summary`, `max_mode`, null context %).

No commit of payload or backup files.

---

### Task 4: Quota fetch + disk cache

**Files:**
- Modify: `tools/cursor-status-line-poc.py`
- Modify: `tests/test_cursor_status_line_poc.py`

**Interfaces:**
- Produces: **`fetch_quota(env, *, now: float | int, urlopen=...) -> QuotaDict`** — Task 4 **owns and replaces** the Task 1 stub with the real body (normalize + cache + POSTs). Task 5 only calls it from render. Also produces (required by tests): `resolve_auth_path`, `normalize_quota_responses`, `quota_cache_path`, `write_quota_cache`, `quota_endpoint_url`, `redirect_allowed`, `QuotaRedirectHandler`. Algorithm (binding):
  1. Read disk cache if present.
  2. If cache has **no** `error` and `now - fetched_at < 120` → return it with `stale=False` (no POST).
  3. If cache has `error` and `now - fetched_at < 600` → return the cached dict with `stale=True` (no POST). If that cache also still has usable `total_pct` / on_demand from a prior good fetch, segments show `(stale)`; if it is error-only (no prior good fields), normalize to hide (pcts `None`, on_demand `unavailable`).
  4. Resolve token via `resolve_auth_path` + read `accessToken`. If missing/unreadable/incomplete → **do not POST**; return last-good+`stale=True` if usable fields exist, else hide-shape.
  5. Else POST three methods. On success: write good cache (`error` absent), return `stale=False`. On failure (including `quota_endpoint_url` `ValueError`): write negative cache = `{**last_good_fields_if_any, "error": str, "fetched_at": now}` and return that dict with `stale=True` (or hide-shape if no last-good). Never raise out of `fetch_quota`.
- `QuotaDict` keys: `cycle_start_ms`, `cycle_end_ms`, `total_pct`, `auto_pct`, `api_pct`, `on_demand` (`kind`, `used_dollars`, `ceiling_dollars`|None), `fetched_at`, `stale`, `error`
- Consumes: `accessToken` via `resolve_auth_path(env)` (same ordered list as Step 3 Auth path); Dashboard Connect-RPC JSON

- [ ] **Step 1: Write failing tests** with concrete fixtures (no ellipses). Units: period spend fields in **cents** (divide by 100 for dollars); `GetHardLimit.hard_limit` in **dollars**.

```python
# Synthetic Connect-JSON-shaped dicts (field names as returned after JSON decode).
PERIOD_FIXED = {
    "billingCycleStart": "1700000000000",
    "billingCycleEnd": "1702592000000",
    "planUsage": {
        "totalPercentUsed": 42.0,
        "autoPercentUsed": 10.0,
        "apiPercentUsed": 32.0,
        "includedSpend": 840,
        "limit": 2000,
    },
    "spendLimitUsage": {
        "individualUsed": 150,       # cents
        "individualLimit": 2000,     # cents
        "limitType": "user",
    },
}
HARD_FIXED = {"hardLimit": 20, "noUsageBasedAllowed": False}  # dollars
HARD_UNLIMITED = {"hardLimit": 2147483647, "noUsageBasedAllowed": False}
HARD_DISABLED = {"hardLimit": 0, "noUsageBasedAllowed": True}
HARD_ZERO_ENABLED = {"hardLimit": 0, "noUsageBasedAllowed": False}  # fall-through → disabled
PLAN = {"planInfo": {"planName": "Pro", "billingCycleEnd": "1702592000000"}}

class TestQuotaFetch(unittest.TestCase):
    def test_normalize_fixed(self):
        mod = load_poc()
        q = mod.normalize_quota_responses(PERIOD_FIXED, HARD_FIXED, PLAN)
        self.assertEqual(q["total_pct"], 42.0)
        self.assertEqual(q["auto_pct"], 10.0)
        self.assertEqual(q["api_pct"], 32.0)
        self.assertEqual(q["on_demand"]["kind"], "fixed")
        self.assertEqual(q["on_demand"]["used_dollars"], 1.5)
        self.assertEqual(q["on_demand"]["ceiling_dollars"], 20.0)
        self.assertEqual(q["cycle_end_ms"], 1702592000000)

    def test_normalize_unlimited_and_disabled(self):
        mod = load_poc()
        u = mod.normalize_quota_responses(PERIOD_FIXED, HARD_UNLIMITED, PLAN)
        self.assertEqual(u["on_demand"]["kind"], "unlimited")
        self.assertEqual(u["on_demand"]["used_dollars"], 1.5)  # individualUsed 150¢
        self.assertIsNone(u["on_demand"].get("ceiling_dollars"))
        d = mod.normalize_quota_responses(PERIOD_FIXED, HARD_DISABLED, PLAN)
        self.assertEqual(d["on_demand"]["kind"], "disabled")
        z = mod.normalize_quota_responses(PERIOD_FIXED, HARD_ZERO_ENABLED, PLAN)
        self.assertEqual(z["on_demand"]["kind"], "disabled")  # hardLimit==0 ⇒ disabled

    def test_normalize_unavailable_without_plan_usage(self):
        mod = load_poc()
        q = mod.normalize_quota_responses({"billingCycleStart": "0", "billingCycleEnd": "0"}, HARD_FIXED, PLAN)
        self.assertEqual(q["on_demand"]["kind"], "unavailable")

    def test_cache_does_not_store_token(self):
        mod = load_poc()
        with tempfile.TemporaryDirectory() as td:
            env = {"HOME": td, "XDG_CACHE_HOME": td}
            mod.write_quota_cache(env, {"total_pct": 10, "fetched_at": 1, "on_demand": {"kind": "disabled"}})
            text = Path(td, "ai-kit", "cursor-statusline-poc", "usage.json").read_text(encoding="utf-8")
            self.assertNotIn("accessToken", text)
            self.assertNotIn("eyJ", text)

    def test_cache_path_defaults_without_xdg_cache_home(self):
        mod = load_poc()
        with tempfile.TemporaryDirectory() as td:
            env = {"HOME": td}  # no XDG_CACHE_HOME
            p = mod.quota_cache_path(env)
            self.assertEqual(p, Path(td) / ".cache" / "ai-kit" / "cursor-statusline-poc" / "usage.json")

    def test_rejects_non_https_endpoint(self):
        mod = load_poc()
        with self.assertRaises(ValueError):
            mod.quota_endpoint_url({"CURSOR_API_ENDPOINT": "http://evil.example"})

    def test_rejects_cross_host_redirect(self):
        mod = load_poc()
        self.assertFalse(mod.redirect_allowed(
            "https://api2.cursor.sh/x", "https://evil.example/x"))
        self.assertTrue(mod.redirect_allowed(
            "https://api2.cursor.sh/a", "https://api2.cursor.sh/b"))

    def test_default_opener_refuses_cross_host_redirect(self):
        # Production opener/handler uses redirect_allowed (not only the helper unit).
        import urllib.error, urllib.request
        mod = load_poc()
        self.assertTrue(issubclass(mod.QuotaRedirectHandler, urllib.request.HTTPRedirectHandler))
        handler = mod.QuotaRedirectHandler()
        req = urllib.request.Request(
            "https://api2.cursor.sh/aiserver.v1.DashboardService/GetHardLimit",
            data=b"{}",
            headers={"Authorization": "Bearer tok"},
            method="POST",
        )
        refused = False
        try:
            out = handler.redirect_request(
                req, None, 302, "Found", {}, "https://evil.example/x")
            refused = out is None
        except (urllib.error.HTTPError, ValueError, OSError):
            refused = True
        self.assertTrue(refused, "cross-host redirect must be refused by QuotaRedirectHandler")

    def test_fetch_quota_posts_three_methods(self):
        mod = load_poc()
        calls = []
        def fake_urlopen(req, timeout=None):
            calls.append((req.full_url, req.get_header("Authorization"), req.data, timeout))
            # Minimal Connect-JSON success bodies (one per URL path).
            class R:
                def __enter__(self): return self
                def __exit__(self, *a): return False
                def read(self):
                    if "GetCurrentPeriodUsage" in req.full_url:
                        return json.dumps(PERIOD_FIXED).encode()
                    if "GetHardLimit" in req.full_url:
                        return json.dumps(HARD_FIXED).encode()
                    return json.dumps(PLAN).encode()
            return R()
        with tempfile.TemporaryDirectory() as td:
            auth = Path(td) / "cursor" / "auth.json"
            auth.parent.mkdir(parents=True)
            auth.write_text('{"accessToken":"tok-test","refreshToken":"r"}', encoding="utf-8")
            env = {"HOME": td, "XDG_CONFIG_HOME": td, "XDG_CACHE_HOME": td}
            q = mod.fetch_quota(env, urlopen=fake_urlopen, now=1_700_100_000)
        self.assertEqual(len(calls), 3)
        self.assertTrue(all(u.startswith("https://api2.cursor.sh/") for u, *_ in calls))
        self.assertTrue(all(a == "Bearer tok-test" for _, a, *_ in calls))
        self.assertTrue(all(t == 0.8 for *_, t in calls))
        self.assertEqual(q["on_demand"]["kind"], "fixed")
```

- [ ] **Step 2: Run tests — expect FAIL**

Run: `python3 -m unittest tests.test_cursor_status_line_poc.TestQuotaFetch -v`  
Expected: FAIL

- [ ] **Step 3: Implement**

**Auth path (`resolve_auth_path(env)` — authoritative ordered `is_file()` fallthrough):**

Build the candidate list in order (include env legs only when set; always include the two home defaults), then return the **first** path that `is_file()`:

1. `$CURSOR_CONFIG_DIR/auth.json` — only if `CURSOR_CONFIG_DIR` is set  
2. `$XDG_CONFIG_HOME/cursor/auth.json` — only if `XDG_CONFIG_HOME` is set  
3. `~/.config/cursor/auth.json` — always  
4. `~/.cursor/auth.json` — always  

Not an exclusive `else` cascade: if `XDG_CONFIG_HOME` is set but that path is missing, keep falling through to `~/.config/cursor/auth.json` and `~/.cursor/auth.json`.

**Missing / unreadable / incomplete auth (binding):**
- No candidate `is_file()`, or chosen file is unreadable / not JSON / lacks a non-empty string `accessToken` → **skip network only**. Still run algorithm steps 1–3: serve a usable fresh or last-good cache when present. Hide-shaped quota (pcts `None`, on_demand `unavailable`) only when there is **no** usable cache. Never log, print, or cache token material. Do not refresh tokens.

**Wire contract (Connect-RPC JSON over HTTPS):**

- Base: `quota_endpoint_url(env)` → default `https://api2.cursor.sh`; if `CURSOR_API_ENDPOINT` set, require `https://` or raise `ValueError`. Callers: `fetch_quota` catches that `ValueError` (and other fetch/IO errors), writes/returns hide or last-good+stale, and **must not** propagate to `safe_render`.
- For each method `M` in (`GetCurrentPeriodUsage`, `GetHardLimit`, `GetPlanInfo`):

```
POST {base}/aiserver.v1.DashboardService/{M}
Headers:
  Authorization: Bearer <accessToken>
  Content-Type: application/json
  Connect-Protocol-Version: 1
Body: {}
```

(POC body is empty object `{}` for all three — matches the CLI's empty-request pattern observed in the bundle. If live Task 6 shows a required field, amend FINDINGS and the body; do not invent fields here.)

- **Redirects (binding integration):** build a custom `urllib.request.HTTPRedirectHandler` subclass whose `redirect_request` calls `redirect_allowed(old.get_full_url(), newurl)` and raises `urllib.error.HTTPError` (or returns `None` to refuse) when false; install via `urllib.request.build_opener(handler)` and pass `opener.open` as the injectable `urlopen` default. Never copy `Authorization` onto a cross-host redirect (handler refusal is the control). Unit tests may inject a fake `urlopen`; production path must use this opener.
- **Timeout (binding):** 800 ms (`timeout=0.8`) **per** call, sequential; worst-case cold wall ≈ 2.4 s. On first failure/timeout stop remaining calls, write negative cache, return last-good or empty quota.
- **POC kill-window choice (explicit):** live wire uses `updateIntervalMs: 3000` and `timeoutMs: 10000` (Task 3). Comment: `shortcut: sync sequential fetch; no single-flight; live wire raises interval/timeout`.
- Cache path: `${XDG_CACHE_HOME:-$HOME/.cache}/ai-kit/cursor-statusline-poc/usage.json` mode 0600, atomic replace.
- TTL fresh 120 s; negative cache 600 s on 401/network error.
- **JSON key map (inferred until Task 6 confirms; try camelCase first, then snake_case):**

| Logical field | Try keys in order |
|---|---|
| cycle start | `billingCycleStart`, `billing_cycle_start` |
| cycle end | `billingCycleEnd`, `billing_cycle_end` |
| plan usage obj | `planUsage`, `plan_usage` |
| total % | `totalPercentUsed`, `total_percent_used` |
| auto % | `autoPercentUsed`, `auto_percent_used` |
| api % | `apiPercentUsed`, `api_percent_used` |
| included spend | `includedSpend`, `included_spend` |
| included limit | `limit` |
| spend limit obj | `spendLimitUsage`, `spend_limit_usage` |
| individual used¢ | `individualUsed`, `individual_used` |
| hard limit $ | `hardLimit`, `hard_limit` |
| no usage based | `noUsageBasedAllowed`, `no_usage_based_allowed` |
| planInfo | `planInfo`, `plan_info` |

- **Percent extraction:** `total_pct = totalPercentUsed` if present and numeric; else if `limit > 0`: `100 * includedSpend / limit`; else `None`. `auto_pct` / `api_pct` = their fields if numeric else `None` (segment hides).
- **Cycle dates:** prefer Period's start/end; if Period end missing/0, use `planInfo.billingCycleEnd` / `billing_cycle_end`. Coerce with `int(...)`. If still missing, pace-gap returns `None` (segments still show % without gap color).
- On-demand classification (POC contract, exhaustive):
  1. missing `planUsage` → kind `unavailable` (included pcts `None`)
  2. else if `noUsageBasedAllowed` is true → `disabled`
  3. else if `hardLimit >= 2147483647` → `unlimited` (`used_dollars=individualUsed/100` or 0; no ceiling)
  4. else if `hardLimit > 0` → `fixed` (`ceiling_dollars=hardLimit`, `used_dollars=individualUsed/100` or 0)
  5. else (`hardLimit <= 0`) → `disabled`

Also add these failing tests (exact code):

```python
    def test_total_pct_from_spend_over_limit(self):
        mod = load_poc()
        period = {
            "billingCycleStart": "1", "billingCycleEnd": "2",
            "planUsage": {"includedSpend": 50, "limit": 200},  # no totalPercentUsed
        }
        q = mod.normalize_quota_responses(period, HARD_DISABLED, PLAN)
        self.assertEqual(q["total_pct"], 25.0)

    def test_total_pct_none_when_limit_zero(self):
        mod = load_poc()
        period = {
            "billingCycleStart": "1", "billingCycleEnd": "2",
            "planUsage": {"includedSpend": 50, "limit": 0},
        }
        q = mod.normalize_quota_responses(period, HARD_DISABLED, PLAN)
        self.assertIsNone(q["total_pct"])

    def test_cycle_end_falls_back_to_planinfo(self):
        mod = load_poc()
        period = {"billingCycleStart": "10", "planUsage": {"totalPercentUsed": 1}}
        q = mod.normalize_quota_responses(period, HARD_DISABLED, PLAN)
        self.assertEqual(q["cycle_end_ms"], 1702592000000)

    def test_missing_auth_no_network_hides_quota(self):
        mod = load_poc()
        calls = []
        def no(req, timeout=None):
            calls.append(1)
            raise AssertionError("no network without auth")
        with tempfile.TemporaryDirectory() as td:
            env = {"HOME": td, "XDG_CONFIG_HOME": td, "XDG_CACHE_HOME": td}
            q = mod.fetch_quota(env, now=1, urlopen=no)
            self.assertEqual(calls, [])
            self.assertTrue(q["on_demand"]["kind"] == "unavailable" or q.get("total_pct") is None)

    def test_missing_auth_still_serves_fresh_cache(self):
        mod = load_poc()
        calls = []
        def no(req, timeout=None):
            calls.append(1)
            raise AssertionError("no network without auth")
        with tempfile.TemporaryDirectory() as td:
            env = {"HOME": td, "XDG_CONFIG_HOME": td, "XDG_CACHE_HOME": td}
            mod.write_quota_cache(env, {
                "total_pct": 42, "fetched_at": 1000, "stale": False,
                "on_demand": {"kind": "disabled"}, "cycle_start_ms": 0, "cycle_end_ms": 1,
            })
            q = mod.fetch_quota(env, now=1030, urlopen=no)  # within 120s fresh TTL
            self.assertEqual(calls, [])
            self.assertEqual(q["total_pct"], 42)
            self.assertFalse(q.get("stale"))

    def test_malformed_auth_skips_network(self):
        mod = load_poc()
        calls = []
        def no(req, timeout=None):
            calls.append(1)
            raise AssertionError("no network on bad auth")
        with tempfile.TemporaryDirectory() as td:
            auth = Path(td) / "cursor" / "auth.json"
            auth.parent.mkdir(parents=True)
            auth.write_text("{not-json", encoding="utf-8")
            env = {"HOME": td, "XDG_CONFIG_HOME": td, "XDG_CACHE_HOME": td}
            q = mod.fetch_quota(env, now=1, urlopen=no)
            self.assertEqual(calls, [])
            self.assertTrue(q["on_demand"]["kind"] == "unavailable" or q.get("total_pct") is None)

    def test_auth_missing_token_skips_network(self):
        mod = load_poc()
        calls = []
        def no(req, timeout=None):
            calls.append(1)
            raise AssertionError("no network without token")
        with tempfile.TemporaryDirectory() as td:
            auth = Path(td) / "cursor" / "auth.json"
            auth.parent.mkdir(parents=True)
            auth.write_text('{"refreshToken":"x"}', encoding="utf-8")
            env = {"HOME": td, "XDG_CONFIG_HOME": td, "XDG_CACHE_HOME": td}
            q = mod.fetch_quota(env, now=1, urlopen=no)
            self.assertEqual(calls, [])
            self.assertTrue(q["on_demand"]["kind"] == "unavailable" or q.get("total_pct") is None)

    def test_auth_fallthrough_when_xdg_missing_file(self):
        mod = load_poc()
        with tempfile.TemporaryDirectory() as td:
            xdg = Path(td) / "xdg"
            home = Path(td) / "home"
            xdg.mkdir(); home.mkdir()
            auth = home / ".config" / "cursor" / "auth.json"
            auth.parent.mkdir(parents=True)
            auth.write_text('{"accessToken":"t"}', encoding="utf-8")
            env = {"HOME": str(home), "XDG_CONFIG_HOME": str(xdg)}
            self.assertEqual(mod.resolve_auth_path(env), auth)
```

Also add failure/TTL tests in `TestQuotaFetch`:

```python
    def test_fetch_timeout_writes_negative_cache_and_stops(self):
        mod = load_poc()
        n = {"calls": 0}
        def boom(req, timeout=None):
            n["calls"] += 1
            raise TimeoutError("slow")
        with tempfile.TemporaryDirectory() as td:
            auth = Path(td) / "cursor" / "auth.json"
            auth.parent.mkdir(parents=True)
            auth.write_text('{"accessToken":"t"}', encoding="utf-8")
            env = {"HOME": td, "XDG_CONFIG_HOME": td, "XDG_CACHE_HOME": td}
            # Seed a prior good cache past the 120s fresh TTL so step 4 runs.
            # now(1000) - fetched_at(800) = 200 >= 120 → must POST (not step 2).
            mod.write_quota_cache(env, {
                "total_pct": 11, "fetched_at": 800, "stale": False,
                "on_demand": {"kind": "disabled"}, "cycle_start_ms": 0, "cycle_end_ms": 1,
            })
            q = mod.fetch_quota(env, urlopen=boom, now=1000)
            self.assertEqual(n["calls"], 1)  # early abort after first method
            self.assertTrue(mod.quota_cache_path(env).is_file())
            self.assertTrue(q.get("error"))
            self.assertTrue(q.get("stale"))
            self.assertEqual(q["total_pct"], 11)  # last-good kept
            # Within 600s negative TTL: no more POSTs
            n["calls"] = 0
            q2 = mod.fetch_quota(env, urlopen=boom, now=1100)
            self.assertEqual(n["calls"], 0)
            self.assertTrue(q2.get("stale"))
            self.assertEqual(q2["total_pct"], 11)

    def test_fresh_cache_skips_network(self):
        mod = load_poc()
        with tempfile.TemporaryDirectory() as td:
            env = {"HOME": td, "XDG_CACHE_HOME": td, "XDG_CONFIG_HOME": td}
            mod.write_quota_cache(env, {
                "total_pct": 7, "fetched_at": 1000, "stale": False,
                "on_demand": {"kind": "disabled"}, "cycle_start_ms": 0, "cycle_end_ms": 1,
            })
            calls = []
            def no(req, timeout=None):
                calls.append(1)
                raise AssertionError("network should not run")
            # Same entrypoint the render path calls:
            q = mod.fetch_quota(env, now=1000 + 30, urlopen=no)  # within 120s
            self.assertEqual(q["total_pct"], 7)
            self.assertEqual(calls, [])

    def test_error_only_negative_cache_hides(self):
        mod = load_poc()
        calls = []
        def no(req, timeout=None):
            calls.append(1)
            raise AssertionError("no network inside negative TTL")
        with tempfile.TemporaryDirectory() as td:
            env = {"HOME": td, "XDG_CACHE_HOME": td, "XDG_CONFIG_HOME": td}
            mod.write_quota_cache(env, {
                "error": "timeout", "fetched_at": 1000, "stale": True,
                # no usable total_pct / on_demand from a prior good fetch
            })
            q = mod.fetch_quota(env, now=1100, urlopen=no)  # within 600s
            self.assertEqual(calls, [])
            self.assertIsNone(q.get("total_pct"))
            self.assertEqual(q["on_demand"]["kind"], "unavailable")
```

- [ ] **Step 4: Tests PASS**

Run: `python3 -m unittest tests.test_cursor_status_line_poc.TestQuotaFetch -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tools/cursor-status-line-poc.py tests/test_cursor_status_line_poc.py
git commit -m "$(cat <<'EOF'
poc: cursor Dashboard quota fetch and disk cache

Normalize included/auto/api/on-demand fields with token-free cache for the statusline POC.
EOF
)"
```

---

### Task 5: Quota segments + TOML recipe

**Files:**
- Modify: `tools/cursor-status-line-poc.py`
- Modify: `tools/cursor-statusline-poc.toml.sample`
- Modify: `tests/test_cursor_status_line_poc.py`

**Interfaces:**
- Produces: `seg_included_total`, `seg_included_auto`, `seg_included_api`, `seg_reset`, `seg_on_demand`; `context_from_quota(quota: dict, *, now_ms: int) -> SimpleNamespace` carrying quota fields, `now_ms`, and **`on_demand_hot: bool` set here** (`True` iff `total_pct >= 100` and on-demand `used_dollars > 0`); reuses Task 1 `default_theme()`
- **Render wiring (Task 5 owns this exclusively — ownership B):** Task 1 left `safe_render` / `render_for_test` / `render_from_raw` **without** any `fetch_quota` call. Task 5 adds the call, then **`vars(context_from_quota(...)).items()` copied onto the existing `build_context(...)` `SimpleNamespace`** (update in place — never replace the whole ctx). Wrap the fetch in try/except so endpoint `ValueError` / IO / unexpected errors leave quota fields unset/hide and still return local/payload segments (`safe_render` never raises). Task 4 owns the `fetch_quota` implementation; Task 5 does not re-implement fetch.
- Consumes: `QuotaDict` from Task 4

- [ ] **Step 1: Failing tests** for on-demand kinds, hiding missing auto/api, `≈`, stale, reset, highlight, pace-gap, **and** render-level fetch wiring.

```python
class TestQuotaSegments(unittest.TestCase):
    def test_on_demand_fixed_shows_ceiling(self):
        mod = load_poc()
        ctx = mod.context_from_quota(
            {"on_demand": {"kind": "fixed", "used_dollars": 1.5, "ceiling_dollars": 20.0},
             "total_pct": 100, "stale": False, "cycle_start_ms": 0, "cycle_end_ms": 10},
            now_ms=5,
        )
        s = mod.seg_on_demand(ctx, 80, mod.default_theme())
        self.assertIsNotNone(s)
        self.assertIn("1.5", s)
        self.assertIn("20", s)
        self.assertIn("≈", s)

    def test_on_demand_disabled_unlimited_unavailable(self):
        mod = load_poc()
        theme = mod.default_theme()
        d = mod.context_from_quota(
            {"on_demand": {"kind": "disabled"}, "total_pct": 10, "stale": False,
             "cycle_start_ms": 0, "cycle_end_ms": 10}, now_ms=5)
        self.assertIn("off", mod.seg_on_demand(d, 80, theme).lower())
        u = mod.context_from_quota(
            {"on_demand": {"kind": "unlimited", "used_dollars": 3.0}, "total_pct": 10,
             "stale": False, "cycle_start_ms": 0, "cycle_end_ms": 10}, now_ms=5)
        su = mod.seg_on_demand(u, 80, theme)
        self.assertIn("3", su)
        self.assertRegex(su.lower(), r"no cap|unlimited")
        x = mod.context_from_quota(
            {"on_demand": {"kind": "unavailable"}, "total_pct": None, "stale": False,
             "cycle_start_ms": 0, "cycle_end_ms": 10}, now_ms=5)
        self.assertIsNone(mod.seg_on_demand(x, 80, theme))

    def test_included_templates(self):
        mod = load_poc()
        theme = mod.default_theme()
        ctx = mod.context_from_quota(
            {"total_pct": 42, "auto_pct": 10, "api_pct": 32, "stale": False,
             "on_demand": {"kind": "disabled"}, "cycle_start_ms": 0, "cycle_end_ms": 100},
            now_ms=50,
        )
        self.assertIn("inc 42%", mod.seg_included_total(ctx, 80, theme))
        self.assertIn("auto 10%", mod.seg_included_auto(ctx, 80, theme))
        self.assertIn("api 32%", mod.seg_included_api(ctx, 80, theme))

    def test_auto_hidden_when_absent(self):
        mod = load_poc()
        ctx = mod.context_from_quota(
            {"total_pct": 10, "auto_pct": None, "on_demand": {"kind": "disabled"}, "stale": False,
             "cycle_start_ms": 0, "cycle_end_ms": 10},
            now_ms=5,
        )
        self.assertIsNone(mod.seg_included_auto(ctx, 80, mod.default_theme()))

    def test_stale_marker_and_reset_days(self):
        mod = load_poc()
        ctx = mod.context_from_quota(
            {"total_pct": 10, "on_demand": {"kind": "disabled"}, "stale": True,
             "cycle_start_ms": 0, "cycle_end_ms": 86_400_000},
            now_ms=0,
        )
        t = mod.seg_included_total(ctx, 80, mod.default_theme())
        self.assertIn("stale", t.lower())
        r = mod.seg_reset(ctx, 80, mod.default_theme())
        self.assertIsNotNone(r)
        self.assertIn("↺", r)
        self.assertIn("1d", r)

    def test_pace_gap_formula(self):
        mod = load_poc()
        # elapsed 50% of window, used 80% → gap +30
        self.assertEqual(mod.billing_pace_gap(80.0, start_ms=0, end_ms=100, now_ms=50), 30.0)

    def test_gap_color_bands(self):
        mod = load_poc()
        theme = mod.default_theme()
        self.assertEqual(mod.util_gap_color(5.0, theme), theme.c("GREEN"))
        self.assertEqual(mod.util_gap_color(10.0, theme), theme.c("YELLOW"))
        self.assertEqual(mod.util_gap_color(15.0, theme), theme.c("ORANGE"))
        self.assertEqual(mod.util_gap_color(16.0, theme), theme.c("RED"))

    def test_on_demand_highlight_when_included_exhausted(self):
        mod = load_poc()
        ctx = mod.context_from_quota(
            {"total_pct": 100, "on_demand": {"kind": "fixed", "used_dollars": 0.5, "ceiling_dollars": 20},
             "stale": False, "cycle_start_ms": 0, "cycle_end_ms": 10},
            now_ms=5,
        )
        s = mod.seg_on_demand(ctx, 80, mod.default_theme())
        self.assertTrue(ctx.on_demand_hot)
        self.assertIn("\x1b[1;31m", s)  # bold red — binding highlight

    def test_render_includes_quota_from_fetch(self):
        # Proves Task 5 wiring: render_for_test → fetch_quota → context_from_quota.
        mod = load_poc()
        payload = {
            "model": {"display_name": "M"},
            "workspace": {"current_dir": "/tmp/x"},
            "context_window": {"used_percentage": 10, "context_window_size": 1000},
        }
        with tempfile.TemporaryDirectory() as td:
            env = {"HOME": td, "XDG_CONFIG_HOME": td, "XDG_CACHE_HOME": td}
            mod.write_quota_cache(env, {
                "total_pct": 42, "auto_pct": None, "api_pct": None,
                "on_demand": {"kind": "disabled"}, "stale": False,
                "fetched_at": 1, "cycle_start_ms": 0, "cycle_end_ms": 10_000,
            })
            out = mod.render_for_test(payload, env, now=50)
        self.assertIn("M", out)  # payload segment still present after merge
        self.assertIn("inc 42%", out)
        self.assertIn("≈", out)

    def test_render_hides_quota_when_fetch_raises(self):
        mod = load_poc()
        payload = {
            "model": {"display_name": "M"},
            "workspace": {"current_dir": "/tmp/x"},
            "context_window": {"used_percentage": 10, "context_window_size": 1000},
        }
        with tempfile.TemporaryDirectory() as td:
            env = {"HOME": td, "XDG_CONFIG_HOME": td, "XDG_CACHE_HOME": td}
            def boom(*a, **k):
                raise RuntimeError("quota down")
            mod.fetch_quota = boom
            out = mod.render_for_test(payload, env, now=50)
        self.assertIn("M", out)  # local/payload still render
        self.assertNotIn("inc ", out)
        self.assertNotIn("≈", out)
```

- [ ] **Step 2: Run — expect FAIL**

Run: `python3 -m unittest tests.test_cursor_status_line_poc.TestQuotaSegments -v`  
Expected: FAIL (including `test_render_includes_quota_from_fetch`)

- [ ] **Step 3: Implement segments + render wiring**

**Display templates (binding):**
- `included_total`: `inc {int(total_pct)}%` (hide if `total_pct` is `None`)
- `included_auto`: `auto {int(auto_pct)}%` (hide if `None`)
- `included_api`: `api {int(api_pct)}%` (hide if `None`)
- `reset`: `↺ {YYYY-MM-DD} ({n}d)` in **UTC** via `datetime.fromtimestamp(cycle_end_ms/1000, tz=timezone.utc)`; `n = max(0, math.ceil((cycle_end_ms - now_ms) / 86_400_000))`; hide if `cycle_end_ms` missing/0
- `on_demand`: `od off` / `od $1.5/$20` / `od $3.0 no cap` / hide `unavailable`

**Pace-gap (binding):**
`billing_pace_gap(used_pct, start_ms, end_ms, now_ms) = used_pct - elapsed_pct`
where `elapsed_pct = 100 * (now_ms - start_ms) / (end_ms - start_ms)` clamped to `[0, 100]`; return `None` if `end_ms <= start_ms`.
**Color bands:** copy Claude `util_gap_color(abs(gap), theme)` exactly (`<=5` GREEN / `<11` YELLOW / `<=15` ORANGE / else RED via `theme.c`). Apply to `included_*` segments.
**On-demand `fixed` ramp:** color by `used_dollars/ceiling_dollars` (0–100%): green <50, yellow <80, red ≥80 (absolute ratio, not pace).
Append dim `≈` on all quota segments as `{_DIM}≈{RESET}` (`_DIM="\033[90m"`, `RESET="\033[0m"`); append `(stale)` when `stale`.
When `billing_pace_gap` is `None`, included `%` uses uncolored text (no gap SGR) — still show the number.
Highlight when `ctx.on_demand_hot` (set by `context_from_quota`, not by the segment): wrap the on-demand segment body in bold red SGR `\x1b[1;31m…\x1b[0m`.

**Render wiring (do in this step, not later):** `safe_render` / `render_for_test` / `render_from_raw` call `fetch_quota` + merge `context_from_quota` under try/except as in Interfaces.

- [ ] **Step 4: Complete sample TOML** documenting every segment default and the four `[[line]]` blocks.

- [ ] **Step 5: Tests PASS**

Run: `python3 -m unittest tests.test_cursor_status_line_poc.TestQuotaSegments -v`  
Expected: PASS (including `test_render_includes_quota_from_fetch`)

Also: `python3 -m unittest tests.test_cursor_status_line_poc -v` for the full module.

- [ ] **Step 6: Commit**

```bash
git add tools/cursor-status-line-poc.py tools/cursor-statusline-poc.toml.sample tests/test_cursor_status_line_poc.py
git commit -m "$(cat <<'EOF'
poc: included/auto/api/reset/on-demand statusline segments

Render Cursor plan usage with inferred-API markers and a complete TOC sample.
EOF
)"
```

---

### Task 6: Live wire + findings wrap-up

**Files:**
- Write: `$WORKTREE/tmp/cursor-statusline-poc-FINDINGS.md` (gitignored)
- Temporarily edits resolved `cli-config.json` (same resolver as Task 3)
- Optionally amend REVIEW notes under `.planning/specs/` only if uz asks to promote findings into the backlog assets

**Interfaces:**
- Consumes: live `cursor-agent` + Tasks 1–5 script (no `--dump-payload`)

**Restore-on-failure:** same as Task 3 — after wire, any abort/failure runs restore first.

- [ ] **Step 1: Ask uz OK** to wire POC as `statusLine.command` (backup/restore again).

- [ ] **Step 2: Backup + atomic wire** (copy Task 3 Steps 2–3 with these changes: command has **no** `--dump-payload`; still set `updateIntervalMs: 3000`, `timeoutMs: 10000`; still write `tmp/cli-config.path.txt` + `.bak`; use `shlex.quote` on the script path).

```bash
WORKTREE="$(git rev-parse --show-toplevel)"
cd "$WORKTREE"
# Reuse Task 3 Step 2 backup snippet verbatim, then:
python3 - <<'PY'
import json, os, shlex, tempfile
from pathlib import Path

def resolve_cli_config_path(env=os.environ) -> Path:
    home = Path(env.get("HOME") or Path.home())
    cands = []
    if env.get("CURSOR_CONFIG_DIR"):
        cands.append(Path(env["CURSOR_CONFIG_DIR"]) / "cli-config.json")
    if env.get("XDG_CONFIG_HOME"):
        cands.append(Path(env["XDG_CONFIG_HOME"]) / "cursor" / "cli-config.json")
    cands += [home / ".cursor" / "cli-config.json",
              home / ".config" / "cursor" / "cli-config.json"]
    for p in cands:
        if p.is_file():
            return p
    raise SystemExit("refuse: no cli-config among: " + ", ".join(map(str, cands)))

wt = Path.cwd().resolve()
p = resolve_cli_config_path()
data = json.loads(p.read_text(encoding="utf-8"))
cmd = "python3 -S " + shlex.quote(str(wt / "tools" / "cursor-status-line-poc.py"))
data["statusLine"] = {
    "type": "command",
    "command": cmd,
    "updateIntervalMs": 3000,
    "timeoutMs": 10000,
}
text = json.dumps(data, indent=2) + "\n"
fd, tmp = tempfile.mkstemp(dir=str(p.parent), prefix=".cli-config.", suffix=".tmp")
try:
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(tmp, p)
finally:
    if os.path.exists(tmp):
        os.unlink(tmp)
assert json.loads(p.read_text())["statusLine"]["command"] == cmd
print("wired", p)
PY
```

- [ ] **Step 3: Live pass/fail checklist** (several minutes of use). **Must observe all of:**
  1. path + branch visible; struck `⎇ wt` on main checkout **or** cyan `⎇ {name}` in a linked worktree
  2. process RSS **and** system free RAM visible
  3. `model_compact`: model name + context size + `%` when known; `param_summary` if present; `· max` when `max_mode` is true
  4. included total with `≈` when quota loaded
  5. on-demand: `off` / `$used/$cap` / unlimited as appropriate for this account
  6. reset date or days remaining when cycle end is known
  7. no Python traceback in the agent UI from the statusline command  
  Optional notes: kill/cancel feel, whether auto/api populate.  
  If any of 1–7 fails, run Step 5 restore immediately.

- [ ] **Step 4: Measure cold-fetch wall time, then write findings**

```bash
WORKTREE="$(git rev-parse --show-toplevel)" && cd "$WORKTREE"
# Force cache miss (delete POC cache only under XDG_CACHE_HOME default), time one render.
python3 - <<'PY'
import os, time, tempfile
from pathlib import Path
import importlib.util
POC = Path("tools/cursor-status-line-poc.py")
spec = importlib.util.spec_from_file_location("poc", POC)
mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
# Use real HOME so auth resolves; still only read-only token.
env = dict(os.environ)
cache = mod.quota_cache_path(env)
if cache.is_file():
    cache.unlink()
payload = {"model":{"display_name":"T"},"workspace":{"current_dir":str(Path.cwd())},
           "context_window":{"used_percentage":1,"context_window_size":1000}}
t0 = time.perf_counter()
out = mod.render_for_test(payload, env)
ms = (time.perf_counter() - t0) * 1000
Path("tmp").mkdir(exist_ok=True)
findings = Path("tmp/cursor-statusline-poc-FINDINGS.md")
block = (f"\n## Latency\n- cold_fetch_wall_ms: {ms:.0f}\n"
         f"- stdout_nonempty: {bool(out.strip())}\n\n")
if findings.is_file():
    findings.write_text(findings.read_text(encoding="utf-8") + block, encoding="utf-8")
else:
    findings.write_text("# Cursor statusline POC findings\n" + block, encoding="utf-8")
print(f"cold_fetch_wall_ms={ms:.0f}")
PY
```

**Never truncate** Task 3 notes already in that file — only append. Then append further sections: payload vs skill schema; auth path that worked; RPC encoding/headers; units (cents vs dollars); camelCase vs snake_case confirmation; **sync vs background recommendation grounded in the measured `cold_fetch_wall_ms` and live kill/cancel feel under `updateIntervalMs: 3000`**; any API fields that were null.

- [ ] **Step 5: Restore** using Task 3 Step 5 verbatim (unless uz asks to keep the POC wired).

- [ ] **Step 6: Run unit tests once more**

```bash
WORKTREE="$(git rev-parse --show-toplevel)"
cd "$WORKTREE"
python3 -m unittest tests.test_cursor_status_line_poc -v
```

Expected: PASS. No commit of `./tmp/` secrets/payloads.

---

## Success criteria

POC succeeds when a real `cursor-agent` session shows:

1. path + branch (+ struck `⎇ wt` on main or linked-worktree glyph)  
2. process RSS + system free RAM  
3. model_compact (model · context · param_summary · % · `max` when set)  
4. included total (and auto/API if API sends them)  
5. on-demand state with ceiling when fixed  
6. reset date/days from API window  
7. script never crashes the host; quota failures only hide quota segments; bad JSON blanks the line (exit 0)  

## Self-review notes (author)

- Spec coverage: local segments requested (path/branch/worktree/process/system memory) are Task 2; quota/model are Tasks 1/4/5; live proof Task 3/6. Backlog refactor explicitly out of scope.  
- No TBD placeholders in task steps.  
- `process_memory` must not reuse Claude's `claude`-only ancestor filter.
