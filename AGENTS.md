# ai-kit Agent Instructions

`ai-kit` is uz's personal collection of Agent Skills (agentskills.io
standard) and a one-line installer, portable across Claude Code, opencode,
Codex CLI, Cursor, and other conformant hosts. This is a solo-dev project.

## Required Start

1. For milestone work, read `.planning/PROJECT.md`, `.planning/STATE.md`,
   `.planning/ROADMAP.md`, and the active phase's `NN-CONTEXT.md` before
   planning or implementation.
2. Use a GSD workflow before repository edits: `/gsd-discuss-phase` →
   `/gsd-plan-phase` → `/gsd-execute-phase` for milestone-scale work;
   `/gsd-quick` or `/gsd-debug` for small, well-scoped out-of-plan work.
3. Live-verify claims against the actually-installed tools/config on this
   machine before trusting a PRD's, REQUIREMENTS.md's, or a doc's wording at
   face value (`.planning/PROJECT.md`'s core value: never claim more
   certainty than verified).

## Non-Negotiable Rules

- **English only, always**: write all documentation, planning artifacts,
  commit messages, code comments, and any other written project artifact in
  English, regardless of what language the conversation with uz happens to
  be in. Never mix languages within a single document or file (no
  "Spanglish"). Translate quoted non-English input faithfully into English
  rather than leaving it verbatim. Conversing with uz in another language is
  fine — everything written to a file must be English.
- Runtime code (`tools/status-line.py`, `tools/statusline-doctor.py`,
  `tools/setup.py`'s non-wizard paths) stays **stdlib-only** — no
  third-party imports, ever. `uv`/`textual`-class dependencies are dev- or
  wizard-only, reached only through the guard + re-exec + fail-closed
  pattern (`ensure_rich_runtime()`/`_textual_importable()` in
  `tools/setup.py`) — never a silent runtime import.
- Every write to a runtime's config file (opencode.jsonc, Codex TOML, Claude
  JSON, ai-kit's own `settings.json` wiring) is atomic (`tempfile.mkstemp()`
  + `os.replace()`), reusing `_read_json()`/`_write_json()`. JSONC surgical
  edits preserve every other byte untouched — comments, formatting,
  unrelated entries.
- No diagnostic, detection, or catalog result is presented with more
  certainty than its actual sourcing — reverse-engineered formats,
  informational-only settings, and inferred classifications are visibly
  flagged, never shown at the same confidence as officially documented
  behavior.
- Any new or materially updated `SKILL.md` passes the `skill-judge` review
  loop (no remaining Critical/Important finding, or score ≥ 96/120, no
  regression vs. baseline) before being marked complete.
- Commit one coherent, buildable logical change with its tests and
  documentation together. Let pre-commit hooks run; never use `--no-verify`.
- Preserve unrelated dirty or untracked work. Never `git reset --hard`,
  `git clean -f`, `git checkout .`/`git restore .` without uz's explicit
  confirmation.

## Architecture

- `detect_installed_clis()` (binary-on-PATH) and `detect_current_runtime()`
  (which CLI hosts *this* process) are deliberately different questions —
  never conflate them. `KNOWN_CLIS` in
  `skills/ai-kit-spec-review/ai_kit_spec/detection.py` is the single source
  of truth for which CLIs ai-kit knows about.
- A model-catalog entry with `cli: None` means "native" (host-agnostic
  wording — never Claude/opus-specific). `native_runtime` is only ever set
  on entries with `cli: None`.
  > **Amended 2026-09-09** (Phase 1.2 plan 01.2-02): `cli: None`/`cli`-omitted
  > semantics actually live in `review-spec.toml`'s native `[[reviewers]]`
  > entries (and the candidate dicts `quota.py` builds from them) — not in
  > `model_catalog.py`, whose catalog entries never carry a `cli` key at all.
  > `native_runtime` schema validation exists in both files: `config_io.py`
  > is the functionally-reachable path (native review-spec.toml entries),
  > `model_catalog.py`'s is forward-compatible-only (no live producer sets a
  > `cli` key there today). Both reject `native_runtime` co-present with a
  > non-null `cli` on the same entry.
- `tools/status-line.py` is organized into banner-delimited blocks
  (`# ═══ N. <ROLE> — ...`) with a role-prefix convention on top-level
  functions (`cfg_`/`probe_`/`fmt_`/`util_`/`core_`/`seg_`, plus the
  unprefixed `main`/`safe_render` SHELL entrypoints). `tests/test_arch.py`
  enforces these invariants via AST parsing — extend it, don't bypass it,
  when adding top-level functions to that module.
- Skills under `skills/` follow the Agent Skills open standard so they work
  unmodified across hosts — don't write one against Claude-Code-specific
  behavior unless there's genuinely no portable equivalent; flag the gap
  explicitly instead of silently degrading.
- Before reusing the `ensure_rich_runtime()` guard pattern for a new
  interactive feature, confirm its fail-closed path is exercised by more
  than a mock — a prior investigation found it lacks a genuinely-clean-
  container e2e test.

## Tools and Stack

- Dev/lint env is `uv`-managed, pinned via `uv.lock`
  (`pyproject.toml`'s `dev` group): `ruff~=0.14` (target `py312`,
  line-length 100, `select = [E, F, W, I, UP, B, SIM, RUF]` — the `RUF00x`
  ambiguous-unicode rules are ignored globally since the status line is
  intentionally unicode-rich UI), `pylint~=4.0` (`max-args=5`,
  `max-locals=15`, `max-branches=12`, `max-returns=6`, `max-statements=50`),
  `pyright~=1.1` (`basic` mode), `vulture~=2.14` (`min_confidence=80`),
  `pre-commit~=4.4`, `textual>=8.0,<9.0` (dev/wizard-only).
- `tools/install.sh` and `tests/test_install.sh` are checked with
  `shellcheck` — fix findings, don't suppress without a documented reason.
- Don't add a new dev dependency without checking whether an existing
  stdlib-only or already-approved approach covers the need (e.g. the
  hand-rolled-JSONC-scanner precedent over a JSONC-parser dependency).

## Testing

- `make test` — `python3 -m unittest tests.test_setup tests.test_status_line
  tests.test_external_segments tests.test_statusline_doctor tests.test_arch
  tests.test_markdown_to_pdf tests.test_worktree_e2e tests.test_wizard_pty
  tests.test_system_memory_e2e tests.test_ai_kit_spec
  tests.test_ai_kit_spec_gsd`, then `bash tests/test_install.sh`. Run this
  before considering work done — the Python suite alone doesn't cover
  installer behavior (fetch, symlink, wiring).
- `make lint` — shellcheck + `py_compile`. `make validate` — the same
  pre-commit hooks that gate commits, run across all files.
- `tests/*` gets a lighter ruff bar than runtime code (idiomatic test
  patterns are fine there even where they'd fail elsewhere).
- `tests/test_arch.py` is a structural-fitness test (parses source with
  `ast`, no import/execution). Its `TestArchNonVacuity` class proves each
  rule actually catches the violation it claims to — don't add a structural
  rule without a non-vacuity counterpart.
- Never use uz's real config files (`~/.claude/settings.json`,
  `~/.cursor/...`, `~/.config/opencode/...`) as a test fixture — use
  temporary directories and synthetic content.
- For UI/wizard changes, actually run `tools/wizard_app.py` under `uv run`
  before reporting done — type checking and unit tests verify code
  correctness, not feature correctness.
- **Deferred**: a real architecture-layer test suite (dependency-direction
  rules, layering boundaries across the whole `tools/`/`skills/` tree, not
  just the single-file banner/role-prefix checks `test_arch.py` currently
  does) is not built yet — see `.planning/ROADMAP.md` §Backlog, Phase 999.3.

## Code Exploration

This repo is CodeGraph-indexed (`.codegraph/`). Use the `codegraph_explore`
MCP tool before any Grep/Read loop ("how does X work," "where is X
defined," "what calls X"). Fall back to `rg` + Read only if CodeGraph is
unavailable or insufficient.

## Workflow

- When a live-verified fact contradicts `REQUIREMENTS.md`/`ROADMAP.md`
  wording, amend those files formally (not just the phase's own
  `CONTEXT.md`) — downstream researcher/planner agents trust them as the
  source of truth for phase boundaries.
- Genuinely unresolved factual questions get routed to the
  `gsd-phase-researcher` as explicit open questions, never answered by
  invented/guessed content.
- A proposal outside a phase's literal requirement scope gets a real
  feasibility check against the already-confirmed architecture before being
  deferred — don't reflexively push it to the backlog.
- An idea that's genuinely out of scope goes to the GSD backlog
  (`.planning/ROADMAP.md` §Backlog) with a real goal statement, not silently
  dropped.
- Review `git status`/`git diff` after a broad `git add` before committing;
  double-check file contents (not just filenames) for anything that might
  be a secret.

## Commands

- `make dev` — provision the uv-managed dev/lint env + pre-commit hooks
- `make test` — full unittest suite + `tests/test_install.sh`
- `make lint` — shellcheck + `py_compile`
- `make validate` — the same pre-commit hooks that gate commits, all files
- `make doctor` / `make check` — installer diagnostics
