---
phase: 05-usage-metrics-dashboard
plan: 01
subsystem: usage-metrics
tags: [usage-metrics, tracer, claude-code, jsonl, sqlite, static-html]

requires: []
provides:
  - "stdlib-only skills/ai-kit-usage-metrics package: lossless Claude Code JSONL capture, simple-command refined SQLite, static HTML dashboard"
  - "CaptureResult contract (records/cursor/stats) and CAPTURE_SOURCES registry seeded with claude"
  - "refined_commands schema at full Round-1 column set with UNIQUE(raw_ref, step_index) UPSERT"
  - "tests.test_ai_kit_usage_metrics wired into make test, pre-commit, py-compile, and pyright"
affects: [05-usage-metrics-dashboard]

actuals:
  tokens: 90000
  tasks: 2
  commits: 4

tech-stack:
  added: []
  patterns:
    - "Three-layer pipeline: raw JSONL per source -> refined SQLite -> pipeline-regenerated static HTML (D-01/D-02/D-04)"
    - "CaptureResult dataclass as the one return shape every later capture module implements"
    - "raw_ref-keyed append dedup plus ON CONFLICT UPSERT for crash-safe idempotency without file locks"
    - "Atomic writes with existed=os.path.isfile(target) pre-check: new files 0600, dirs 0700 regardless of umask"

key-files:
  created:
    - skills/ai-kit-usage-metrics/SKILL.md
    - skills/ai-kit-usage-metrics/ai-kit-usage-metrics.py
    - skills/ai-kit-usage-metrics/ai_kit_usage_metrics/__init__.py
    - skills/ai-kit-usage-metrics/ai_kit_usage_metrics/paths.py
    - skills/ai-kit-usage-metrics/ai_kit_usage_metrics/raw_store.py
    - skills/ai-kit-usage-metrics/ai_kit_usage_metrics/refined_store.py
    - skills/ai-kit-usage-metrics/ai_kit_usage_metrics/capture_claude.py
    - skills/ai-kit-usage-metrics/ai_kit_usage_metrics/family.py
    - skills/ai-kit-usage-metrics/ai_kit_usage_metrics/pricing.py
    - skills/ai-kit-usage-metrics/ai_kit_usage_metrics/refiner.py
    - skills/ai-kit-usage-metrics/ai_kit_usage_metrics/dashboard.py
    - skills/ai-kit-usage-metrics/ai_kit_usage_metrics/cli.py
    - tests/test_ai_kit_usage_metrics.py
    - .planning/phases/05-usage-metrics-dashboard/05-01-SUMMARY.md
  modified:
    - Makefile
    - .pre-commit-config.yaml
    - pyproject.toml

key-decisions:
  - "Atomic-write mode preservation ports config_doctor_appliers._atomic_write_text's existed=os.path.isfile pre-check, not an exception wrap around write_preserving_mode's unconditional os.stat."
  - "Sibling skill patterns (config_paths, atomic_write, CLI wrapper) are ported with source citations, never imported — the verify grep forbids the identifier ai_kit_opencode_providers even in comments."
  - "refine this wave reads only raw/claude.jsonl (Wave-1 single-source scope); 05-04 Task 3 replaces that call site with refine_all."

patterns-established:
  - "Every path function takes an explicit env: dict and never reads os.environ — tests construct a fully scratch hermetic environment."
  - "Gate registration is asserted by tests that parse Makefile / pre-commit / pyproject as text, not assumed."
  - "CAPTURE_SOURCES is a dict of {source_name: capture_fn}; later waves ADD an entry rather than inventing a parallel dispatch mechanism."

requirements-completed: []

coverage:
  - id: D-01
    description: "Single-script run pipeline: capture then refine then dashboard against a scratch Claude Code session JSONL"
    requirement: REQ-usage-metrics-dashboard-ui
    verification:
      - kind: unit
        ref: "tests.test_ai_kit_usage_metrics.TestEndToEnd.test_run_end_to_end_produces_raw_refined_and_dashboard"
        status: pass
    human_judgment: false
  - id: D-02
    description: "Lossless raw capture: malformed and queue-operation lines keep raw_ref and verbatim raw_text; payload is None only for malformed"
    requirement: REQ-usage-metrics-raw-capture
    verification:
      - kind: unit
        ref: "tests.test_ai_kit_usage_metrics.TestCapture.test_simple_bash_and_lossless_queue_operation_and_malformed"
        status: pass
    human_judgment: false
  - id: D-04
    description: "Store layout honors XDG_DATA_HOME; never a hardcoded ~/.local/share string"
    requirement: REQ-usage-metrics-raw-capture
    verification:
      - kind: unit
        ref: "tests.test_ai_kit_usage_metrics.TestPaths.test_usage_metrics_base_honors_xdg_data_home"
        status: pass
    human_judgment: false
  - id: D-07
    description: "Second run against the same fixture does not duplicate raw lines or refined rows (raw_ref dedup + UPSERT)"
    requirement: REQ-usage-metrics-refinement-pipeline
    verification:
      - kind: unit
        ref: "tests.test_ai_kit_usage_metrics.TestEndToEnd.test_run_end_to_end_produces_raw_refined_and_dashboard"
        status: pass
    human_judgment: false

completed: 2026-09-10
status: complete
---

# Phase 5 Plan 01: Usage Metrics Dashboard Tracer Summary

**One Claude Code Bash command travels from a scratch session JSONL through lossless raw capture and a simple-command refined SQLite schema into an embedded static HTML dashboard.**

## Performance

- **Tasks:** 2
- **Files created:** 13 (plus this SUMMARY)
- **Files modified:** 3
- **Commits:** 4

## Accomplishments

- `skills/ai-kit-usage-metrics/` mirrors the opencode-providers skill shape: thin `ai-kit-usage-metrics.py` wrapper plus `ai_kit_usage_metrics/` package. Wave-1 Scope in `SKILL.md` is honest (Claude Code only, simple commands only).
- `capture_claude.capture` glob-walks `CLAUDE_CONFIG_DIR/projects/*/*.jsonl`, resumes from cursor line counts, and emits one 8-key envelope per new line including `queue-operation` (`recognized_no_data`, payload is the parsed dict) and invalid JSON (`malformed`, payload is None). Missing projects dir is zero records, not an error. A non-UTF-8 file is skipped and listed in `stats["unreadable_files"]`.
- `raw_store.append_records` de-duplicates on the target file's own `raw_ref` values before rewriting atomically. `refined_store.insert_commands` UPSERTs on `UNIQUE(raw_ref, step_index)` and excludes `inferred_family`/`inferred_confidence` from `DO UPDATE SET`.
- `refiner.refine_simple_commands` emits rows only for Bash `tool_use` envelopes whose `input.command` contains none of `&`, `;`, `|`. Missing `input.command` is a refiner skip, not a capture concern.
- `dashboard.generate` embeds refined rows as JSON inside `<script type="application/json" id="usage-metrics-data">` with every `</script` sequence escaped to `<\/script`, then renders a sortable/filterable table over `date, model, family, tokens_input, tokens_output, price`.
- Directories created mode `0700` and files mode `0600` regardless of umask, verified under `os.umask(0o000)`.

## Task Commits

1. **Task 1: End-to-end tracer** — `f4e49de` (feat)
2. **Task 2: Error-path tests + quality-gate registration** — `e8c84e7` (feat)
3. **Gap closure: pyright `_Environ` vs `dict` after joining pyright include** — `7c337c8` (fix)

## Files Created/Modified

- `skills/ai-kit-usage-metrics/` — skill package (wrapper, SKILL.md, 10 modules)
- `tests/test_ai_kit_usage_metrics.py` — 20 tests covering paths, capture, raw/refined stores, refiner, pricing, dashboard, permissions, e2e, and gate registration
- `Makefile` — `tests.test_ai_kit_usage_metrics` on `test:`; package paths on `lint:` py_compile
- `.pre-commit-config.yaml` — ruff and py-compile `files:` regexes; unittest (core) entry
- `pyproject.toml` — `"skills/ai-kit-usage-metrics"` on `[tool.pyright] include` (directory entry; pylint/vulture not widened)

## Decisions Made

None beyond the plan. Followed D-01/D-02/D-04/D-07, the Round-1 CaptureResult contract, the Round-3 atomic-write pre-check, and Phase 4's gate-registration-by-executed-assertion precedent.

## Deviations from Plan

- Atomic-write / path-resolution citations name the hyphenated skill directory (`skills/ai-kit-opencode-providers`) rather than the underscore package path. The plan's verify grep treats `ai_kit_opencode_providers` as a forbidden import, so the citation was worded to keep that grep clean while still attributing the port. The helpers are copied, not imported.
- `main()` copies `os.environ` into a plain `dict` (`resolved: dict = dict(os.environ) if env is None else env`) so pyright accepts the `env: dict` parameter after the package joined `[tool.pyright] include`. Behavior is unchanged; tests already pass an explicit scratch dict.

**Total deviations:** 2
**Impact on plan:** None. Layering, attribution, and type-check cleanliness all hold.

## Issues Encountered

After Task 2 registered the package in pyright include, `uv run pyright skills/ai-kit-usage-metrics` reported 6 `reportArgumentType` errors: `_Environ[str]` is not assignable to `dict`. Fixed in `7c337c8` by copying `os.environ` into a dict at the CLI boundary. Tests were already green; this was a type-checker gap, not a runtime bug.

## User Setup Required

None. Wave 2 (05-02) adds opencode + rtk capture sources to the same `CAPTURE_SOURCES` dict. A real `run` against this machine's `~/.claude/projects/` is a later, user-initiated action — never part of this plan's automated verification (ONESHOT-RULES: every session-data read used a scratch `CLAUDE_CONFIG_DIR`).

## Next Phase Readiness

Ready for 05-02 (opencode + rtk capture). ROADMAP Phase 5 success criteria SC-1/SC-2/SC-3 are true for this plan's tracer scope: one simple Claude Code Bash command is captured losslessly, refined into exactly one `refined_commands` row, and embedded in a locally regenerated `dashboard.html`. Compound commands, additional runtimes, the command decomposer, and the full 5-axis UI remain later waves.

## Verification (captured)

```
$ python3 -m unittest tests.test_ai_kit_usage_metrics -v
Ran 20 tests in 0.006s
OK

$ grep -rn "ai_kit_opencode_providers" skills/ai-kit-usage-metrics/ai_kit_usage_metrics/
# no matches (exit 1 — the passing outcome)

$ grep -c "ON CONFLICT" skills/ai-kit-usage-metrics/ai_kit_usage_metrics/refined_store.py
1

$ python3 -m py_compile skills/ai-kit-usage-metrics/ai-kit-usage-metrics.py skills/ai-kit-usage-metrics/ai_kit_usage_metrics/*.py
# exit 0

$ make lint
shellcheck tools/install.sh tests/test_install.sh
python3 -m py_compile tools/setup.py tools/status-line.py tools/statusline-doctor.py tools/hooks/*.py tools/config_doctor_*.py skills/ai-kit-usage-metrics/ai-kit-usage-metrics.py skills/ai-kit-usage-metrics/ai_kit_usage_metrics/*.py

$ uv run pyright skills/ai-kit-usage-metrics
0 errors, 0 warnings, 0 informations

$ python3 skills/ai-kit-usage-metrics/ai-kit-usage-metrics.py run
# against a scratch CLAUDE_CONFIG_DIR / XDG_DATA_HOME (never ~/.claude)
# first run exit=0; second run exit=0
# raw/claude.jsonl: 4 lines (ok, ok, recognized_no_data, malformed)
# refined/refined.db: 1 row ('ls -la', 'ls', 'simple', 'claude-opus-4-7', '2026-09-10', 0, 1)
# dashboard.html embeds that row; dirs 0700, files 0600
# second run: raw line count still 4, refined row count still 1
```

## Self-Check: PASSED

- [x] Scratch `run` produces raw JSONL (every line including malformed/queue-operation with its own raw_ref/raw_text), one refined_commands row for the simple Bash command, and dashboard.html embedding that row
- [x] Store layout honors `XDG_DATA_HOME` (`${XDG_DATA_HOME}/ai-kit/usage-metrics/{raw,refined}/`)
- [x] Malformed line is captured losslessly (`parse_status="malformed"`, `payload=None`); queue-operation is `recognized_no_data` with parsed payload
- [x] Second `run` against the same fixture does not duplicate raw lines or refined rows (raw_ref dedup + UPSERT)
- [x] Dashboard HTML escapes `</script` inside the embedded JSON payload
- [x] SQLite writes use `?` placeholders; `ON CONFLICT` UPSERT excludes inferred_family/inferred_confidence
- [x] Directories mode 0700 and files mode 0600 under a permissive umask
- [x] Every capture function returns CaptureResult with records/cursor/stats
- [x] Package is import-clean of `ai_kit_opencode_providers`
- [x] `tests.test_ai_kit_usage_metrics` is in Makefile, pre-commit, and pyright (20 tests, 0 failures)
- [x] Production commits exist (`f4e49de`, `e8c84e7`, `7c337c8`)

---
*Phase: 05-usage-metrics-dashboard*
*Completed: 2026-09-10*
