# Phase 16: ai_kit_spec Extensions - Pattern Map

**Mapped:** 2026-09-24
**Files analyzed:** 6 (all existing, no new files)
**Analogs found:** 6 / 6 (this phase is self-analogous — every change extends an existing
in-file convention; the "analog" for each edit is the adjacent code in the same file)

This phase has **no new files**. Every SPEC-01..04 requirement is an additive edit to a module
that already has the exact pattern it needs, elsewhere in the same file. The planner should treat
each row below as "extend this file's own established convention," not "port a pattern from a
different file."

## File Classification

| Modified File | Role | Data Flow | Closest Analog | Match Quality |
|----------------|------|-----------|-----------------|----------------|
| `skills/ai-kit-spec-review/ai_kit_spec/detection.py` | library (detection + subprocess enumeration) | request-response / event-driven (env-signal walk) + streaming (subprocess parse) | itself — `_RUNTIME_ENV_SIGNALS`/`detect_current_runtime` (D-01/D-02/D-03), `detect_opencode_models`/`detect_cursor_agent_models` (D-04/D-05) | exact (in-file precedent) |
| `skills/ai-kit-spec-review/ai_kit_spec/model_catalog.py` | model (schema validation) | CRUD (validate/merge catalog entries) | itself — `_FIELD_TYPES` dict + `validate_catalog_entry` (D-08/D-09); `_VALID_NATIVE_RUNTIME` (pi gap) | exact (in-file precedent) |
| `skills/ai-kit-spec-review/ai_kit_spec/model_ranker.py` | service (pure scoring) | transform (batch) | itself — `DEFAULT_WEIGHTS`/`_is_valid_weights_structure`/`score_candidates` (D-10/D-11) | exact (in-file precedent) |
| `skills/ai-kit-spec-review/ai_kit_spec/cache.py` | utility (JSON cache I/O) | file-I/O | itself — `cache_is_stale`/`cache_read_json` (D-12: caller-side, not touched internally) | exact (unchanged — caller wraps it) |
| `skills/ai-kit-spec-review/ai_kit_spec/cli.py` | controller (argparse command bodies) | request-response | itself — `fetch-model-catalog`'s existing `fetch_meta_path` sidecar / `--if-stale` skip logic (`cli.py:498-540, 716-785`) | exact (in-file precedent) |
| `skills/ai-kit-spec-review/ai_kit_spec/config_io.py` | model (TOML schema validation) | CRUD | itself — `_VALID_NATIVE_RUNTIME` set + `validate_reviewer_fields` (pi gap, orchestrator-resolved) | exact (in-file precedent, mirrors `model_catalog.py`'s duplicate set) |
| `skills/ai-kit-spec-review/references/ranking-weights.toml` | config (data file) | batch (loaded once) | itself — `[review]`/`[execute]`/`[bonuses]` sections (D-10/D-11 add `[planning]`/`[general]`/`[mechanical]`/`[execution]` + `[mechanical.floor]`) | exact (in-file precedent) |

No file in this phase lacks an analog — the "No Analog Found" section is empty by design; this is
a schema/behavior-extension phase, not new-construction.

## Pattern Assignments

### `skills/ai-kit-spec-review/ai_kit_spec/detection.py` (library, D-01/D-02/D-03/D-04/D-05)

**Analog:** itself, current state read this session.

**Current precedence tuple to edit** (`detection.py:27-31`):
```python
_RUNTIME_ENV_SIGNALS = (
    ("claude", "CLAUDECODE"),
    ("opencode", "OPENCODE"),
    ("cursor", "CURSOR_AGENT"),
    ("codex", "CODEX_VERSION"),
)
```
Target shape per D-01 (amended by Phase 20 D-02) / D-02 / D-03 — **two rows for codex** (see
Pitfall 2 in RESEARCH.md: `"X" or "Y"` in a tuple literal is a silent bug, always resolves to the
first literal):
```python
_RUNTIME_ENV_SIGNALS = (
    ("pi", "PI_CODING_AGENT"),
    ("opencode", "OPENCODE"),
    ("cursor", "CURSOR_AGENT"),
    ("codex", "CODEX_THREAD_ID"),
    ("codex", "CODEX_VERSION"),
    ("claude", "CLAUDECODE"),
)
```
The walk loop (`detect_current_runtime`, unchanged control flow) already supports two same-label
rows:
```python
for label, var in _RUNTIME_ENV_SIGNALS:
    if env.get(var):
        return label
return "unknown"
```
Update the docstring's per-signal verification labels (currently lines ~49-65) to add pi
("source-inspected, not live-verified" per D-03) and codex's `CODEX_THREAD_ID`
("observed in real codex session shell snapshots under `~/.codex/sessions`, 20 occurrences" per
D-02) alongside the existing claude/opencode/cursor/codex labels — do not remove the existing
confidence-labeling convention, extend it.

**Subprocess parser convention to copy for `detect_codex_models`** (D-05), from
`detect_opencode_models` (`detection.py`, current file):
```python
def detect_opencode_models(binary: str, run_fn=subprocess.run) -> list:
    try:
        result = run_fn([binary, "models"], capture_output=True, text=True,
                         check=False, timeout=15)
    except (OSError, subprocess.TimeoutExpired):
        return []
    return [ln.strip() for ln in result.stdout.splitlines() if ln.strip()]
```
New `detect_codex_models(binary, run_fn=subprocess.run)` must follow this exact shape: same
`run_fn` injection, same `timeout=15`, same `except (OSError, subprocess.TimeoutExpired): return
[]`, but parses JSON (`codex debug models`) instead of newline-splitting, filters to
`visibility == "list"`, extracts `slug`, and degrades to `[]` on `json.JSONDecodeError` too (see
RESEARCH.md Pattern 2/Code Examples for the full captured-fixture-based implementation).

`KNOWN_CLIS` (`detection.py:13`, `= ("claude", "codex", "opencode", "grok", "cursor-agent")`) is a
**separate** tuple — do NOT add `"pi"` here (Phase 22's concern, per D-06/anti-pattern in
RESEARCH.md).

---

### `skills/ai-kit-spec-review/ai_kit_spec/model_catalog.py` (model, D-08/D-09 + pi gap)

**Analog:** itself.

**`_FIELD_TYPES` extension pattern** (`model_catalog.py:18-31`, add one line matching the
existing bool-field style):
```python
_FIELD_TYPES = {
    ...
    "tool_calling": bool, "native": bool, "reasoning_modes": list, "fast_mode": bool,
    "image_input": bool,  # NEW (D-09) -- optional, absent means unknown, never written False
    ...
}
```
`reasoning_modes: list` already exists at this line and is already validated (`model_catalog.py`
lines ~111-113, D-08 needs zero schema code change there — only a writer elsewhere).

**Pi gap (orchestrator-resolved as in-scope):** `_VALID_NATIVE_RUNTIME` at `model_catalog.py:39`:
```python
_VALID_NATIVE_RUNTIME = {"claude", "opencode", "codex", "cursor", "unknown"}
```
Add `"pi"` to this set. This mirrors the identical duplicate set in `config_io.py` (below) — both
must change together, they are independently defined and do not import from a shared source.

---

### `skills/ai-kit-spec-review/ai_kit_spec/config_io.py` (model, pi gap)

**Analog:** itself, and its sibling `model_catalog.py._VALID_NATIVE_RUNTIME` (same literal set,
duplicated on purpose per current design — RESEARCH.md Pitfall 1).

**Current set to edit** (`config_io.py:97`):
```python
_VALID_NATIVE_RUNTIME = {"claude", "opencode", "codex", "cursor", "unknown"}
```
Add `"pi"`. Validated at `config_io.py:126-129`:
```python
if "native_runtime" in entry and (
        not isinstance(entry["native_runtime"], str)
        or entry["native_runtime"] not in _VALID_NATIVE_RUNTIME):
    return f"{key}: 'native_runtime' must be one of {sorted(_VALID_NATIVE_RUNTIME)}"
```
No other change needed here — the reject-and-report contract already handles the new value once
it is in the set.

---

### `skills/ai-kit-spec-review/ai_kit_spec/model_ranker.py` (service, D-10/D-11)

**Analog:** itself.

**`DEFAULT_WEIGHTS` mirrors `ranking-weights.toml` exactly** (module docstring says so
explicitly, `model_ranker.py:16`). Current two-purpose shape:
```python
DEFAULT_WEIGHTS = {
    "review": {"intelligence_index": 0.30, "coding_index": 0.10, "agentic_index": 0.15,
               "context_window": 0.15, "tool_calling": 0.05, "price": 0.15, "speed": 0.05},
    "execute": {"intelligence_index": 0.15, "coding_index": 0.30, "agentic_index": 0.25,
                "context_window": 0.10, "tool_calling": 0.15, "price": 0.15, "speed": 0.10},
    "bonuses": {"batch_mode": 8, "fallback_quota": 5, "bonus_cap": 15},
}
```
Add `planning`, `general`, `mechanical`, `execution` sibling dicts with the same 7-axis shape
(`_REQUIRED_AXES`), plus keep `"execute"` as an alias (D-10) rather than duplicating data — see
below.

**`_is_valid_weights_structure` hardcoded purpose tuple to make data-driven** (`model_ranker.py`,
current):
```python
def _is_valid_weights_structure(weights) -> bool:
    ...
    for purpose in ("review", "execute"):
        axes = weights.get(purpose)
        if not isinstance(axes, dict) or _REQUIRED_AXES - axes.keys():
            return False
        ...
```
This literal tuple is the ONE spot that must become a module-level `_REQUIRED_PURPOSES` (or
similar) constant. D-10 requires that a weights file with ONLY `review`/`execute` still loads
(missing new purposes fall back to `DEFAULT_WEIGHTS` per-purpose, not a whole-file rejection) —
so the loop must iterate the file's own known purposes, not reject on missing new ones. Structure
this as: validate every purpose PRESENT in the file against `_REQUIRED_AXES`; for any of the 5
canonical purposes ABSENT from the file, `load_ranking_weights` fills in from
`copy.deepcopy(DEFAULT_WEIGHTS[purpose])`.

**Alias lookup (D-10, `_PURPOSE_ALIASES` style, Claude's Discretion default recommended in
RESEARCH.md)** — same "aliases are a lookup concern" philosophy as `model_catalog.canonical_key`:
```python
_PURPOSE_ALIASES = {"execute": "execution"}
```
consulted before the `weights[purpose]` lookup in `score_candidates` (currently a bare dict
lookup, `weights[purpose]`).

**D-11 floor pre-filter** — new logic, no existing analog inside this file (score_candidates
today only ranks, never excludes). Model it as a pre-filter step reading raw
`entry.get("scores", {}).get(axis)` BEFORE `_normalize_minmax`, using `_MISSING_AXIS_DEFAULT`
awareness: a missing axis must fail the floor, never silently pass via the 49.0 default (that
default only applies post-filter, inside the weighted-average scoring itself).

---

### `skills/ai-kit-spec-review/references/ranking-weights.toml` (config data, D-10/D-11)

**Analog:** itself — `[review]`/`[execute]`/`[bonuses]` current sections:
```toml
[review]
intelligence_index = 0.30
coding_index = 0.10
agentic_index = 0.15
context_window = 0.15
tool_calling = 0.05
price = 0.15
speed = 0.05

[execute]
intelligence_index = 0.15
coding_index = 0.30
agentic_index = 0.25
context_window = 0.10
tool_calling = 0.15
price = 0.15
speed = 0.10

[bonuses]
batch_mode = 8
fallback_quota = 5
bonus_cap = 15
```
Add `[planning]`, `[general]`, `[mechanical]`, `[execution]` sections with the same 7 keys
(`intelligence_index`, `coding_index`, `agentic_index`, `context_window`, `tool_calling`, `price`,
`speed`), matching CONTEXT.md's Claude's Discretion guidance (planning = max
intelligence/agentic, low price weight; general = balanced; execution = coding/agentic-heavy,
high price weight; mechanical = price-dominant). Add `[mechanical.floor]` as a new nested table,
e.g.:
```toml
[mechanical.floor]
coding_index = 40
```
(floor value is Claude's Discretion — RESEARCH.md gives no numeric anchor; pick a value clearly
below `_MISSING_AXIS_DEFAULT`'s 49.0 so "missing != passes" is easy to test, and document the
choice in the plan). `review`/`execute` sections stay verbatim (D-10: old names keep working).

---

### `skills/ai-kit-spec-review/ai_kit_spec/cli.py` (controller, D-12)

**Analog:** itself — the existing `fetch-model-catalog` sidecar-freshness pattern
(`cli.py:498-540`, `cli.py:716-785`), specifically the `fetch_meta_path` sidecar file used to
track "was a real fetch attempted" independently of `cache_is_stale`'s mtime check:
```python
fetch_meta_path = args.catalog_path + ".fetch-meta.json"
```
D-12 does **NOT** reuse this sidecar mechanism — `schema_version` staleness must read the
*content* of the cache JSON itself (a `schema_version` top-level key), not add a third sidecar
file (RESEARCH.md "Don't Hand-Roll" table, cache.py row). The OR-not-AND composition is
load-bearing (RESEARCH.md Pitfall 3):
```python
should_refresh = cache_is_stale(path, ttl_seconds) or (
    cached_data is None or cached_data.get("schema_version", 0) < CURRENT_SCHEMA_VERSION
)
```
Wire this into both `detect-runtimes --if-stale` and `fetch-model-catalog --if-stale` command
bodies (`cli.py:716` / `cli.py:727` onward), never inside `cache.py`'s `cache_is_stale` itself
(shared with `quota.py`, must stay schema-agnostic).

**No new `--force` flag** — RESEARCH.md confirms `cli.py:534-540` already documents "run without
`--if-stale`" as the existing force-refresh path; do not add a parallel flag for D-12.

---

## Shared Patterns

### Never-raise / degrade-to-empty-or-default
**Source:** `detection.py`'s `detect_opencode_models`/`detect_cursor_agent_models`,
`model_ranker.py`'s `load_ranking_weights`, `cache.py`'s `cache_read_json`.
**Apply to:** every new function this phase adds (`detect_codex_models`, the D-09 image_input
extraction helpers, the D-11 floor pre-filter). All catch narrow, specific exceptions
(`OSError`, `subprocess.TimeoutExpired`, `json.JSONDecodeError`) and return `[]`/`None`/defaults
— never a bare `except Exception` and never a raise that would crash the caller's whole
`detect-runtimes`/`fetch-model-catalog` invocation over one bad model entry.

### `run_fn`/`which_fn` injection for subprocess/PATH calls
**Source:** `detect_opencode_models(binary, run_fn=subprocess.run)`,
`detect_installed_clis(which_fn=shutil.which)`.
**Apply to:** `detect_codex_models` (D-05) — must accept `run_fn=subprocess.run` as a keyword
default, never call `subprocess.run` directly inline, so tests can inject a fixture-returning
stub.

### Additive-only optional-field schema
**Source:** `model_catalog.py`'s `_FIELD_TYPES` dict + `validate_catalog_entry`'s "a missing
optional field is never a validation failure" contract.
**Apply to:** `image_input` (D-09) and any future field — add to `_FIELD_TYPES` only, never to
`_MANDATORY_CATALOG_FIELDS`, so old cache entries without the field keep loading (SPEC-03) with
zero extra code.

### Confidence/verification labeling in docstrings
**Source:** `detect_current_runtime`'s existing per-signal docstring paragraph
(claude=live-verified, opencode=live-verified, cursor=source-inspected-only,
codex=source-inspected-only).
**Apply to:** the new pi signal (source-inspected, D-03) and `CODEX_THREAD_ID` (observed in
session snapshots, not yet live-verified from a real codex host per D-02) — extend the existing
paragraph, do not replace its structure. This is a project-wide constraint
(`PROJECT.md` confidence labeling, cited in RESEARCH.md `<user_constraints>`).

## No Analog Found

None — every file this phase touches is a modification of existing code with an in-file
precedent for the exact pattern being extended.

## Metadata

**Analog search scope:** `skills/ai-kit-spec-review/ai_kit_spec/` (detection.py, model_catalog.py,
model_ranker.py, cache.py, cli.py, config_io.py), `skills/ai-kit-spec-review/references/
ranking-weights.toml`.
**Files scanned:** 6 Python modules + 1 TOML data file (all read directly this session).
**Pattern extraction date:** 2026-09-24
