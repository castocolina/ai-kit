# FR-R.0 — Lint ruleset & triage (report-only spike)

> Baseline captured 2026-06-21 against `refactor/status-line-render`, report-only.
> Tools run via `uvx` (ruff, pylint, vulture) + system `pyright` 1.1.410.
> This document is the source of truth for `pyproject.toml` (Task 1.4) and for which
> findings are fixed in Phase 1 (`fix-now`), erased by the restructure (`fixed-by-refactor`),
> or suppressed with justification (`legitimately-suppress`).

## Baseline counts

| Tool | status-line.py | setup.py | tests/ |
|---|---|---|---|
| ruff | 0 | 1 (F541) | 26 |
| pylint | (part of 132 across both modules) | | n/a (not linted by pylint) |
| pyright | 0 | 4 | n/a |
| vulture | 0 | 4 | n/a |

Decisions reflect the maintainer's guidance: the single-file length is justified (segments will
externalize later, shrinking it); the uniform `(data, avail, theme)` builder contract makes some
args legitimately unused; exception handling should be **specific** except at the never-blank
isolation boundaries, which stay wide; docstrings are required only where they add signal; tests
are held to a lighter, permissive bar; **local imports are not allowed in `status-line.py`**.

## Enforced ruleset (→ `pyproject.toml`)

```toml
[tool.ruff]
target-version = "py312"
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "W", "I", "UP", "B", "SIM", "RUF"]
ignore = []

[tool.ruff.lint.per-file-ignores]
# Tests held to a lighter, permissive bar (idiomatic test patterns):
#   E741 ambiguous loop var `l`, E731 lambda-assign, E402 imports after sys.path setup.
"tests/*" = ["E741", "E731", "E402"]

[tool.pylint.main]
py-version = "3.12"
# Docstrings required only where they add signal: builders (seg_*), private helpers (_*),
# and tests are self-documenting via the segment contract / test name.
no-docstring-rgx = "^(_|seg_|test_)"

[tool.pylint.basic]
# `bar` is a domain term here (context / effort progress bar), not a placeholder name.
bad-names = ["foo", "baz", "toto", "tutu", "tata"]
# Conditional stdlib import aliases that read as module-level constants.
good-names = ["tomllib"]

[tool.pylint.design]
max-args = 8                 # safe_build/render thread the builder context explicitly
max-positional-arguments = 8
max-locals = 20

[tool.pylint."messages control"]
disable = [
  "too-many-lines",          # deliberate single-file drop-in script; shrinks as segments
                             # externalize (E4c direction). Re-evaluate after externalization.
  "unused-argument",         # uniform segment-builder contract (data, avail, theme): not every
                             # builder reads all three; renaming would break the contract.
  "duplicate-code",          # cross-occurrence false positives on small idiomatic blocks.
  "fixme",                   # TODO/NOTE markers are allowed in-tree.
  "too-few-public-methods",  # data carriers (e.g. _RenderData dict subclass) are not APIs.
]

[tool.vulture]
min_confidence = 80
paths = ["tools/status-line.py", "tools/setup.py"]
# whitelist signal-handler / context-manager params required by their signature
ignore_names = ["signum", "frame"]

[tool.pyright]
include = ["tools/status-line.py", "tools/setup.py"]
pythonVersion = "3.12"
typeCheckingMode = "basic"
```

`broad-exception-caught` is intentionally **not** in the disable list — it is handled per-occurrence
(see triage). `invalid-name` for the hyphenated module name (`status-line.py` is the installed script
name, unrenamable) is suppressed with a single file-header `# pylint: disable=invalid-name` note on
line 1, justified in-file.

## Triaged finding inventory

### `fix-now` — structure-independent, fixed in Phase 1 (Task 1.5)

| Tool | Rule | Count | Where | Action |
|---|---|---:|---|---|
| ruff | F541 | 1 | setup.py:1566 | drop stray `f` prefix |
| pylint | consider-using-f-string | 19 | both modules | convert `%`/`.format` to f-strings |
| pylint | unspecified-encoding | 13 | both modules | add `encoding="utf-8"` to `open()` |
| pylint | subprocess-run-check | 7 | both modules | add explicit `check=False` (intent: probes never raise) |
| pylint | disallowed-name `bar` | 3 | status-line.py:774,1013,1080 | resolved by `bad-names` config (domain term) |
| pylint | invalid-name `tomllib` | 1 | status-line.py:24 | resolved by `good-names` config |
| pylint | invalid-name module | 1 | status-line.py:1 | file-header `# pylint: disable=invalid-name` + comment |
| pylint | invalid-name `raw_mode` | 1 | setup.py:1417 | rename class → `RawMode` (PascalCase) |
| pylint | inconsistent-return-statements | 1 | status-line.py:853 | make all branches return / none |
| pylint | superfluous-parens | 2 | both | remove |
| pylint | line-too-long | 2 | both | wrap to ≤100 |
| pylint | import-outside-toplevel | 2 | setup.py:1059(`copy`),1336(`select`) | move to module top (both stdlib) |
| pylint | f-string-without-interpolation | 1 | setup.py | drop `f` prefix (same as ruff F541) |
| pyright | reportOptionalMemberAccess / reportArgumentType | 4 | setup.py:1443,1463 (termios/tty) | guard the optional module / annotate so `termios`/`tty` are non-None on the tty path |
| vulture | unused variable `exc` | 1 | setup.py:1449 | remove or use in the except |
| vulture | unused variable `reconfigure` | 1 | setup.py:1576 | remove dead binding |
| vulture | `signum`,`frame` | 2 | setup.py:1473 | signal-handler signature → `ignore_names` config |

### `broad-exception-caught` (9) — handled per-occurrence (not globally disabled)

| Where | Disposition |
|---|---|
| status-line.py:1586 (`safe_build`) | KEEP wide — per-segment isolation (never-blank). Inline `# pylint: disable=broad-exception-caught` + existing `# noqa: BLE001`. |
| status-line.py:2068 (`safe_render`) | KEEP wide — whole-render backstop. Inline disable + comment. |
| status-line.py:1215, 2013 | Narrow to the specific exception(s) the block actually guards (cache/probe I/O → `OSError`/`ValueError`); inline disable only if a genuine catch-all is required. |
| setup.py:550,881,1208,1464,1469 | Narrow where the failure mode is known (file/JSON I/O, termios); keep wide only at true UX-degradation boundaries with an inline disable + reason. |

### `fixed-by-refactor` — deferred to the Phase 2 zero-sweep (Task 2.6), NOT fixed/suppressed in Phase 1

| Rule | Count | Where | Why it disappears |
|---|---:|---|---|
| too-many-locals | 7 | incl. `build_data`, `pack_line`, `render` | the lazy `_RenderData` split + two-pass restructure cut local counts |
| too-many-branches | 4 | `build_data`, `pack_line` | data-gathering moves into builders; branch nests collapse |
| too-many-return-statements | 1 | (restructured fn) | simplified control flow |
| too-many-arguments / too-many-positional-arguments | up to 12 | `safe_build`/`pack_line`/`render` | relaxed by `max-args=8`; remainder reduced by the restructure. Any residual gets a justified inline disable in 2.6. |

> If a `fixed-by-refactor` row still reports after Phase 2, fix it then — or, only if genuinely
> irreducible, add a justified inline disable and record it as `legitimately-suppress` here.

### `legitimately-suppress` (config-level, justified above)

- `too-many-lines` — single-file drop-in; will shrink as segments externalize.
- `unused-argument` — uniform builder contract.
- `duplicate-code`, `fixme`, `too-few-public-methods` — see config comments.
- tests `E741`/`E731`/`E402` — permissive test bar (per-file-ignore).
- vulture `signum`/`frame` — required handler signature.
- `missing-function-docstring` on `seg_*`/`_*`/`test_*` — self-documenting (via `no-docstring-rgx`); public non-builder functions still require docstrings (the remaining handful are added in 1.5).
