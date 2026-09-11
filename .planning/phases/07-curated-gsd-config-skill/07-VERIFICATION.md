---
phase: 07-curated-gsd-config-skill
verified: 2026-09-11T00:00:00Z
verifier: independent goal-backward verification (fresh review, not the original code-reviewer)
status: passed
score: 6/6 review findings (CR-01, CR-02, WR-01, WR-02, WR-03, WR-04) fixed and re-verified; all subcommands exercised live and match locked decisions
covered_files:
  - ".planning/phases/07-curated-gsd-config-skill/07-CONTEXT.md"
  - ".planning/phases/07-curated-gsd-config-skill/07-01-PLAN.md"
  - ".planning/phases/07-curated-gsd-config-skill/07-02-PLAN.md"
  - ".planning/phases/07-curated-gsd-config-skill/07-03-PLAN.md"
  - ".planning/phases/07-curated-gsd-config-skill/07-04-PLAN.md"
  - ".planning/phases/07-curated-gsd-config-skill/07-REVIEW.md"
  - ".planning/phases/07-curated-gsd-config-skill/07-REVIEWS.md"
  - "skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cli.py"
  - "skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/preference_match.py"
  - "skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cross_ai_build.py"
  - "skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/frontend_detect.py"
  - "tests/test_ai_kit_gsd_curated_config.py"
test_results:
  unittest_module: "94 tests, OK"
  make_test: pass
  make_lint: pass
  ruff: "0 findings"
  pyright: "0 errors, 0 warnings, 0 informations"
---

# Phase 7 Verification: Curated GSD Config Skill

## Verdict: PASSED

Independently re-verified (not trusting the fix summary) against the live
code in `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/`, the
phase's own locked decisions in `07-CONTEXT.md` (D-01 through D-10) and the
four `07-0N-PLAN.md` files, and by running the actual test/lint/type-check
tooling myself. All 6 previously-reported review findings are genuinely
fixed in the current code. All required commands pass. Registration is
complete and consistent under the renamed `ai-kit-gsd-curated-config` name.
No new gaps found.

## 1. Fix verification (read live code, not the commit message)

All six fixes were confirmed present by reading the actual current file
contents (not just `git show`):

- **CR-01** (import-time crash on missing `ai_kit_spec`): both
  `preference_match.py:30-38` and `cross_ai_build.py:28-36` now wrap the
  `from ai_kit_spec...` import in `try/except ImportError`, with a local
  regex-based `_hint_matches` fallback in the former and a `None` sentinel
  (`build_execute_command = None`) in the latter that
  `build_execution_command` checks (`cross_ai_build.py:54-55`) before ever
  calling it. Importing `cli.py` (which imports both modules at top level)
  no longer depends on the sibling skill being resolvable.
- **CR-02** (`apply-execution --cli` without `--model` wrote literal
  `"None"`): `cli.py:179-189` now has an explicit
  `elif not args.model: degraded_reason = "no_model"` branch before the
  `cross_ai_build.build_execution_command` call, so a partial invocation
  never reaches `str.format(model=None)`. Live-reproduced: `apply-execution
  --cli opencode` (no `--model`) now returns
  `{"cross_ai_command_written": false, "degraded_reason": "no_model"}`
  instead of a fabricated command.
- **WR-01** (bare `KeyError` on unrecognized `apply-review --cli`):
  `cli.py:238-245` now uses `CLI_TO_REVIEWER_SLUG.get(args.cli)` and prints a
  clean stderr message + `return 2` when the slug is `None`. Live-reproduced:
  `apply-review --cli bogus --model foo` now prints
  `unrecognized --cli 'bogus' (expected one of [...])` and exits 2, no
  traceback.
- **WR-02** (`ValueError` on non-dict `package.json` deps):
  `frontend_detect.py:50-55` now guards both `dependencies` and
  `devDependencies` with `isinstance(..., dict)` before `dict.update()`,
  restoring the module's documented "never raises" contract.
- **WR-03** (reviewer-list merge exploding a bare string):
  `cli.py:249` now reads
  `reviewers = list(existing) if isinstance(existing, list) else []`,
  closing the `list("opencode") -> ['o','p',...]` corruption path.
- **WR-04** (missing test coverage): `tests/test_ai_kit_gsd_curated_config.py`
  now has `test_partial_candidate...` (line ~851, asserts `no_model`) and
  `test_unimplemented_builder_degrades_to_no_builder` (line 854, asserts
  `no_builder`) — the previously-untested corners of the
  `--cli`/`--model` presence matrix are covered.

All six fixes match both the review's prescribed remedy and the commit
messages in `b9cf7ba` and `a8f77be`. No fix was cosmetic or partial.

## 2. Goal-backward check against 07-CONTEXT.md / plans

Ran the actual CLI end-to-end against a scratch `.planning/` directory
(not just unit tests) to confirm the phase's stated behavior is real, not
just internally self-consistent:

- `ensure-project` creates `.planning/config.json` via gsd-tools'
  `config-new-project` (confirmed: file appears with GSD's own full default
  key set, including things this skill never touches, e.g. `intel`,
  `graphify`, `branching_strategy` — proving D-09's merge-mode design: only
  the curated keys are touched, everything else is gsd-core's own default,
  not hand-authored JSON).
- `apply-profile --profile balanced` writes `model_profile: "balanced"`
  through `config-set` (D-01 confirmed — no direct file write).
- `apply-critical-agents` wrote `heavy_agents_written: 18` unconditional +
  swept agents, and the resulting config shows
  `model_overrides.gsd-code-reviewer: "opus"` +
  `effort.agent_overrides.gsd-code-reviewer: "high"` (the user's named
  top-up per D-03) and `model_overrides.gsd-executor: "haiku"` (the
  unconditional floor per D-03's last bullet) — both live-derived from the
  installed gsd-core, matching the design, not a hardcoded snapshot (the
  module docstrings and `gsd_catalog.py` query the installed
  `model-catalog.cjs` at runtime, verified by reading `gsd_catalog.py`).
- `apply-claude-md-path --path ./AGENTS.md` correctly writes
  `claude_md_path` to the given value (D-06's detection helper is exercised
  separately via `detect-claude-md-path`).
- `apply-workflow-defaults --ui-phase false --ui-review false` writes a
  27-key bundle (D-07), matching the count the review previously verified
  byte-for-value against this repo's own `.planning/config.json`.
- `detect-frontend` runs without a project-specific package.json/README and
  correctly reports `frontend_present: false` (D-08), never raising.
- `apply-execution` without `--cli`/`--model` degrades cleanly
  (`no_candidate`); with `--cli` only, degrades cleanly (`no_model`, the
  CR-02 fix); a pre-existing `workflow.cross_ai_command` value observed in
  the scratch config came from gsd-core's own `config-new-project` template
  default (verified: present immediately after `ensure-project`, before any
  `apply-execution` call), not written by this skill — no D-05 violation.
- `apply-review` with an unrecognized `--cli` fails cleanly with exit 2 and
  a documented message (WR-01 fix), never a raw traceback.

All subcommands promised across `07-CONTEXT.md` and the four plan files are
present in `--help` output
(`ensure-project, apply-profile, apply-critical-agents,
detect-execution-candidate, detect-review-candidate, apply-execution,
apply-review, detect-claude-md-path, detect-frontend, apply-claude-md-path,
apply-workflow-defaults`) and each one was exercised directly, not merely
inferred from source reading.

## 3. Test / lint / type-check results (run live, not assumed)

- `python3 -m unittest tests.test_ai_kit_gsd_curated_config -v` — **94 tests,
  OK** (up from the review's reported 87 — the +7 are the CR-01/CR-02/WR-01
  through WR-04 regression tests added across the two fix commits).
- `make test` — full repo suite (all modules, including
  `tests.test_ai_kit_gsd_curated_config` and `tests/test_install.sh`) —
  **passes clean**, `.planning/config.json` of this repo provably untouched
  by the run (confirmed by `TestRealIntegration.test_this_repos_own_config_is_never_touched`).
- `make lint` — shellcheck + `py_compile` over all registered paths
  including `skills/ai-kit-gsd-curated-config/**/*.py` — **passes clean**.
- `uv run ruff check skills/ai-kit-gsd-curated-config/
  tests/test_ai_kit_gsd_curated_config.py` — **`[]`, 0 findings**.
- `uv run pyright skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/`
  — **0 errors, 0 warnings, 0 informations**.

## 4. Registration completeness

Checked every registration surface for the renamed
`ai-kit-gsd-curated-config` name and searched the whole repo (excluding
`.planning/`, which legitimately retains historical references to the old
`ai-kit-gsd-config` name in prior summaries/state notes) for leftovers:

- `Makefile` — `test:` target includes
  `tests.test_ai_kit_gsd_curated_config`; `lint:` target's `py_compile`
  line includes
  `skills/ai-kit-gsd-curated-config/ai-kit-gsd-curated-config.py
  skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/*.py`.
- `.pre-commit-config.yaml` — both the ruff hook and the pyright hook's
  `files:` regex include `skills/ai-kit-gsd-curated-config/.*`.
- `pyproject.toml` — `[tool.pyright]`/`[tool.vulture]` `paths`/`include`
  lists both contain `skills/ai-kit-gsd-curated-config`.
- `README.md` — has a row for `ai-kit-gsd-curated-config` linking to its
  `SKILL.md`, describing the curated one-question flow accurately.
- Repo-wide grep for `ai_kit_gsd_config\b` / `ai-kit-gsd-config\b` outside
  `.planning/` returns **zero matches** — no leftover old-name references
  in any `.py`, `.md`, `.toml`, `.yaml`, or `Makefile` file.

No gaps found in registration.

## Conclusion

All 6 previously-reported CRITICAL/WARNING findings are genuinely fixed in
the live code, the phase's stated goal and success criteria are actually
achieved by exercising the CLI directly (not just reading source or trusting
tests), the full tooling chain (unittest, make test, make lint, ruff,
pyright) passes with zero findings, and registration under the renamed
skill name is complete with no old-name leftovers outside historical
planning docs. **Status: passed.**
