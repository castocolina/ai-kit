---
phase: 16-ai-kit-spec-extensions
plan: 02
subsystem: ai_kit_spec
executor: cross-ai (opencode run --model router-env/my-coding)
actuals:
  commits: 2
key-files:
  created:
    []
  modified:
    - skills/ai-kit-spec-config/SKILL.md
    - skills/ai-kit-spec-review/ai_kit_spec/config_io.py
    - skills/ai-kit-spec-review/ai_kit_spec/detection.py
    - skills/ai-kit-spec-review/ai_kit_spec/model_catalog.py
    - tests/test_ai_kit_spec.py
completed: 2026-09-24
---

# Phase 16 Plan 02: Host detection precedence (pi, codex) Summary

## What changed
- `_RUNTIME_ENV_SIGNALS` (skills/ai-kit-spec-review/ai_kit_spec/detection.py:33) is now the exact 6-row tuple in the new global precedence: pi > opencode > cursor > codex > claude. Codex owns two adjacent rows (`CODEX_THREAD_ID`, `CODEX_VERSION`, both label `codex`) per 16 D-02 — never an `or` inside a tuple row. `KNOWN_CLIS` untouched (16 D-06).
- `detect_current_runtime` docstring: kept the three existing contract paragraphs, added the fixed-order sentence (16 D-01, amended by Phase 20 D-02), and replaced the confidence paragraph with six per-signal bullets — pi and `CODEX_THREAD_ID` visibly flagged `source-inspected-only` / `not yet live-verified`; no mention of `OPENCODE_PID` anywhere (pre-existing docstring inaccuracy fixed).
- Closed the `_VALID_NATIVE_RUNTIME`/`"pi"` gap (orchestrator resolution 1; 16-RESEARCH Pitfall 1): `model_catalog.py:39` and `config_io.py:97` both now accept `{"claude","opencode","codex","cursor","pi","unknown"}`, each with a comment noting the deliberate duplication and the Phase 16 provenance of `pi`.
- New tests: `TestPiHostEndToEnd` (4 tests: pi beats outer claude through the real CLI JSON; the `pi` value survives `cfg_render_toml`; both validators accept `native_runtime="pi"`; codex-from-claude reads as codex) and `TestRuntimePrecedenceMatrix` (10 tests: pinned tuple, single-signal labels, E1 step-down order, E3 codex alone/together, E2 empty/`""`/`"unknown"`-is-str, `""` fallthrough, `env=None` via `patch.dict`, `KNOWN_CLIS` scope guard, P1 confidence labels, docstring-names-only-signals-the-tuple-reads). Renamed `test_nested_subprocess_fixed_order_winner_is_claude` → `..._is_opencode`; added `"pi"` to the accepted-values test.
- `skills/ai-kit-spec-config/SKILL.md` Step 2.7: value list now `(\`pi\` / \`opencode\` / \`cursor\` / \`codex\` / \`claude\` / \`unknown\`)` plus the nesting sentence (innermost wins). No other SKILL.md change.
- Deviation found and fixed during execution (see Deviations): the docstring-bullet test originally split `__doc__` on `"\n    - "` per the plan text; on this machine's Python 3.14.7 that never matches — CPython 3.14 dedents docstrings at compile time (`_PyCompile_CleanDoc`, "C implementation of inspect.cleandoc()", verified in upstream v3.14.7 `Python/compile.c:1515-1520` and applied at `codegen.c:888,1351`). The test now runs the docstring through `inspect.cleandoc` first, which normalizes 3.14 (dedented) and ≤3.13 (indented) runtimes to the identical canonical bullet form; the asserted content is unchanged.

## Files
- skills/ai-kit-spec-review/ai_kit_spec/detection.py
- skills/ai-kit-spec-review/ai_kit_spec/model_catalog.py
- skills/ai-kit-spec-review/ai_kit_spec/config_io.py
- tests/test_ai_kit_spec.py
- skills/ai-kit-spec-config/SKILL.md

## Commits
```
81d35b9 test(16-02): pin host precedence matrix and document pi native runtime
6d37160 feat(16-02): detect pi and codex hosts with innermost-CLI precedence
```

## Test results
- Task 1 verify: `python3 -m unittest ...TestPiHostEndToEnd ...TestDetectCurrentRuntime ...TestValidateCatalogEntry ...TestRenderAndWriteToml ...TestMainCli -v` → `Ran 95 tests in 0.070s` / `OK` (exit 0)
- Task 2 verify #1: `python3 -m unittest ...TestRuntimePrecedenceMatrix ...TestPiHostEndToEnd ...TestDetectCurrentRuntime -v` → `Ran 22 tests in 0.008s` / `OK` (exit 0); `TestRuntimePrecedenceMatrix` ran 10 tests, all passing
- Task 2 verify #2 (broad regression): `Ran 941 tests in 5.579s` / `OK` (exit 0)
- Task 2 verify #3: `PATH="$HOME/.local/bin:$PATH" UV_NO_SYNC=1 UV_OFFLINE=1 make test-unit` → exit 1 (`make: *** [Makefile:46: test-unit] Error 1`); its two unittest legs ran the merged suite once per leg: `Ran 2573 tests in 11.598s` / `FAILED (errors=1, skipped=20)` — the single error is the pre-existing, unrelated `test_real_render_produces_image` (below); every other test in both legs passed
- Acceptance one-liners: tuple/set identity asserts exit 0; `test_nested_subprocess_fixed_order_winner_is_opencode` count = 1; both SKILL.md greps = 1; all lines added by this plan ≤100 chars
- No real network fetches and no real CLI binaries were invoked during verification (the failing mmdc test shells out to the machine's own mermaid-cli, which is absent — that is the failure itself)

## Pre-existing failures
- `ERROR: test_real_render_produces_image (tests.test_markdown_to_pdf.TestRenderRealMmdc.test_real_render_produces_image)` (provisional) — verbatim:
  ```
  Traceback (most recent call last):
    File "/var/home/bazzite/git/personal/ai-kit/tests/test_markdown_to_pdf.py", line 78, in test_real_render_produces_image
      out = rm.render_all(md, work, fmt="png")
    File "/var/home/bazzite/git/personal/ai-kit/skills/markdown-to-pdf/scripts/render_mermaid.py", line 86, in render_all
      raise MermaidRenderError(loc, (err or "").strip())
  render_mermaid.MermaidRenderError: mermaid render failed at line 1: node:internal/modules/cjs/loader:1520
    throw err;
    ^
  Error: Cannot find module '/home/bazzite/.local/share/pnpm/global/v11/ca026-19fa5b731c0-0ac52087022f9fc0/node_modules/@mermaid-js/mermaid-cli/src/cli.js'
  ```
  Rationale: the test file (`tests/test_markdown_to_pdf.py`) and the raising module (`skills/markdown-to-pdf/scripts/render_mermaid.py`) are untouched by this plan; the failure is the machine's pnpm-global mermaid-cli store being missing/incomplete (`MODULE_NOT_FOUND` from node itself), not a code regression. Left unmodified per the objective's pre-existing-failure rule; pending 16-06 Task 3's reproduction at the pre-phase base commit.

## Pending orchestrator gates
skill-judge: skills/ai-kit-spec-config/SKILL.md — pending (orchestrator-owned, blocking)

## Decisions honored
- **16 D-01 (as amended by Phase 20 D-02)**: global precedence pi > opencode > cursor > codex > claude, claude checked last; replaced 01.2 D-02's claude-first order in `_RUNTIME_ENV_SIGNALS` and the test that pinned it. Rated costly (reversibility) in the plan — already user-decided in 16-CONTEXT.md, so no checkpoint was raised.
- **16 D-02**: codex signal is `CODEX_THREAD_ID` or `CODEX_VERSION` — two separate tuple rows; `CODEX_SANDBOX` never added; codex bullets keep the "not yet live-verified" label until Phase 20 (EVAL-04).
- **16 D-03**: pi signal is `PI_CODING_AGENT`, labeled `source-inspected-only` (installed `@earendil-works/pi-coding-agent` `dist/config.js`), live validation deferred.
- **16 D-06**: no pi enumeration and no `pi` in `KNOWN_CLIS` — pinned by `test_known_clis_still_excludes_pi`; both belong to Phase 22.
- **Orchestrator resolution 1**: `"pi"` added to BOTH duplicated `_VALID_NATIVE_RUNTIME` sets (model_catalog.py and config_io.py) with mutual-sync comments.
- **AGENTS.md check (16-CONTEXT canonical_refs)**: `grep -n "opencode > \|> claude\|CLAUDECODE" AGENTS.md` printed nothing (exit 1) — AGENTS.md does not describe the old order, so no AGENTS.md edit was made and none was committed.

## Deviations
- One deviation from the plan's test text, forced by verified interpreter behavior: the bullet-split marker `"\n    - "` in `test_docstring_confidence_labels_for_pi_and_codex_thread_id` was replaced by splitting on `"\n- "` after `inspect.cleandoc(doc)`. Investigation trail: the docstring on disk has 4-space-indented bullets (raw bytes verified), but every runtime docstring on this box — including stdlib `textwrap`'s — arrives dedented; traced to CPython 3.14's compile-time docstring dedent (`_PyCompile_CleanDoc`, confirmed in upstream v3.14.7 `Python/compile.c:1515-1520` "C implementation of inspect.cleandoc()" and its call sites `codegen.c:888,1351`; both this machine's interpreters are 3.14.7, while the repo's uv dev env is py312, so the raw `__doc__` shape is interpreter-dependent). `inspect.cleandoc` makes the assertion interpreter-independent; all content assertions are unchanged and pass under both extraction shapes. No other deviations — the plan's steps, verify commands, staged files, and commit messages were followed exactly.

## Cross-AI execution (orchestrator record)

- Executor: `opencode run --model router-env/my-coding` (cross_ai: true), prompt = plan <objective> + <tasks> via stdin.
- Automatic session resumes after transient provider errors: 1.
- Orchestrator verification: re-ran make test-unit independently: 2573 tests, only error = pre-existing mmdc environment test; confirmed _RUNTIME_ENV_SIGNALS order pi > opencode > cursor > codex(THREAD_ID, VERSION) > claude and 'pi' in _VALID_NATIVE_RUNTIME; commits 6d37160, 81d35b9 reviewed.
