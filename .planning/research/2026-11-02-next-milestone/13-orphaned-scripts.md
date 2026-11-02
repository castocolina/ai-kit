# Orphaned and half-orphaned scripts (research for the next milestone)

Date: 2026-11-02. Read-only scan of the main checkout at commit 27337d5.

## How the scan worked

- `13_scan_refs.py`: lists every tracked `.py/.sh/.mjs/.js/.cjs/.ts` file under `skills/`,
  `tools/` and `.planning/` (archived phase folders under `.planning/milestones/` excluded, test
  files excluded). For each one it collects every tracked file that names it (basename, or module
  stem for Python), and sorts the hits into: sibling code, other code, wiring (Makefile,
  installer, pre-commit, CI, plugin), skill docs, tests, planning, archive, other docs.
  Output: `13_scan.out`.
- `13_pkg_imports.py`: a stricter import check for every module inside a skill Python package
  (relative imports, package-qualified imports, multi-line `from . import (...)`). Output:
  `13_pkg.out`.
- `13_tools_refs.sh`: an `rg --hidden` check for `tools/` and `skills/*/scripts/` files, excluding
  tests and planning. Output: `13_tools.out`.
- Spot checks by hand for dynamic loading. The repo loads many modules by string, so a plain
  import graph undercounts usage: `tools/setup.py` uses `_sibling("config_doctor_app")` and
  similar calls, the hooks use `importlib.import_module("detect")`, curated-config uses
  `gsd_catalog.load_ai_kit_spec_module("model_ranker")`, and status-line segments are dispatched
  by their `seg_*` names.

Result: 266 files in scope. 242 have a live caller. Nothing in `tools/` or any skill package is
fully orphaned. The real orphans are in `.planning/`, and a few live files are referenced only by
their own test or only by planning docs.

## Fully orphaned (nobody invokes them)

### `.planning/docs/system-one-decision-skill/scratchpad/` (whole folder)

- What it is: leftover scratch from writing the `jev-fast-decision` skill. It holds 82 tracked
  files, around 20 of them scripts:
  - `build.py`: patched `jb/scripts/jev_review.py` with text snippets during authoring.
  - `v3/blk9.py` … `v3/blk13.py`, `v3/t4.py`, `v3/eof_test.py`: test snippets that were pasted
    into the skill's tests.
  - `lint/t2.py`, `lint/t3.py`, `lint/t_snips.py`: lint trials.
  - `sx/mod.py`, `sx/test_sx.py`: a subprocess smoke stub.
  - `v3/step4.sh`: a calibration step. It writes into `~/.claude/skills/jev-fast-decision/notes/`
    on the real home directory.
  - Three old copies of the skill: `jb/`, `v3/skill/`, `v3/skill.pre-calibrate/`, each with
    `scripts/jev_review.py`, `scripts/eval_cases.py` and `tests/test_jev_review.py`. All three
    differ heavily from the live `skills/jev-fast-decision/scripts/` (diffs of about 2,150 lines
    for `jev_review.py` and about 195 lines for `eval_cases.py`), so they are stale and not
    mirrors.
- Who references it: no code, test, installer, Makefile or SKILL.md. Only planning text names
  the folder: `.planning/STATE.md`, three pending todos, the 2026-10-13 audit notes, the
  onboarding summary, and the v1.3 archive.
- Suggested fate: delete the `scratchpad/` subtree (git history keeps it). Keep the folder's
  `PLAN.md` and `review-history/` as research if the decision log still matters. Repoint or drop
  the three pending todos that still name the folder.

## Half-orphans: referenced only by their own test

### `skills/ai-kit-spec-review/ai_kit_spec/cross_ai_catalog.py`

- What it does: compiles `references/cross-ai-errors.json` into the `// <patterns>` block of the
  `references/cross-ai.mjs` template. It has a `main()` with a check mode.
- Who references it: only `tests/test_cross_ai_catalog.py` (a drift test: the rendered block
  must match the template) and the archived phase 25.1 plans. No SKILL.md, reference doc or
  Makefile target tells a maintainer to run it after editing the error catalog.
- Suggested fate: keep, and adopt it into the maintainer workflow. Either add a Makefile target
  that regenerates the block (and a check target), or add one line to
  `skills/ai-kit-spec-review/references/cross-ai-dispatch.md` naming the regenerate command.

### `skills/jev-fast-decision/scripts/eval_cases.py`

- What it does: runs the 32 labelled cases in `evals/cases.jsonl` through `screen()`, records
  results, and with `--calibrate` rewrites each backend's `min_confidence` in `jev_review.py`.
- Who references it: only `tests/test_jev_fast_decision.py`, planning docs, and the v1.3 archive.
  `SKILL.md` and `reference.md` never mention it.
- Suggested fate: keep, and adopt it into `jev-fast-decision`. Add a short "re-calibrate"
  section to `reference.md` that names the command and its `--record` / `--calibrate` flags.
  This replaces the orphaned `scratchpad/v3/step4.sh`, which did the same job by hand.

## Half-orphans: referenced only by planning docs

### `.planning/spikes/001-claude-timer-resume/run.sh`, `002-claude-resume-while-alive/run.sh`, `003-pi-opencode-timer-resume/run.sh`

- What they do: spike experiments on resuming a CLI session from a timer (Claude, then pi and
  opencode).
- Who references them: the spike READMEs, `.planning/spikes/MANIFEST.md`, the 2026-10-13 audit
  note `15-pi-live-tests.md`, and the archived phase 01.1 docs.
- Suggested fate: keep as research. Their findings already shipped in
  `skills/ai-kit-session-wake/`. Do not adopt them as runtime code.

### `.planning/spikes/004-cron-and-limit-evidence/mine_transcript.py`

- What it does: lists cron-prompt deliveries and usage-limit replies from a Claude transcript.
- Who references it: only its spike README.
- Suggested fate: keep as research. If session-wake ever needs a "show me the evidence" debug
  command, fold it into `ai_kit_session_wake` next to `reset_parse.py`. Otherwise leave it.

## Duplicated copies

### The three `cross-ai.mjs` files

- `skills/ai-kit-spec-review/references/cross-ai.mjs` (10,424 lines, template 8, stamp
  `UNSTAMPED`, empty config block). This is the template. `tooling_guidance.py`,
  `cross_ai_catalog.py` and curated-config's `cross_ai_script.py` / `ensure-runner` load it, and
  the curated-config and spec-review skill docs name it. It is live.
- `.planning/scripts/cross-ai.mjs` (10,443 lines, template 8, stamped). This is this repo's own
  render of that template, wired by `.planning/config.json`
  (`cross_ai_command: node .planning/scripts/cross-ai.mjs`) and named by `ROADMAP.md`. It is
  live. Its diff against the template is 27 lines, all in the stamp and the baked config block
  (models, retries, backoff, routerBacked). The body has not drifted. These two files are a
  template and its render, not stale twins. Nothing in the test suite checks that this repo's own
  render still matches the template; only `ensure-runner` does, when someone runs it.
- `.planning/research/2026-10-13-audit/cross-ai.mjs` (477 lines, template 1). This is the first
  prototype, from commit 344773b. Its header still says `node .planning/cross-ai.mjs`, an
  outdated path. Nobody runs it. Only the audit notes and the v1.3 archive name it.
  - Suggested fate: delete it, or keep it as research with a one-line README note saying it is
    the superseded prototype. It must not be mistaken for a runnable runner.
- Suggested follow-up for the live pair: a cheap check (a Makefile target, or a test that skips
  outside this repo) that this repo's render matches the template body. That makes drift
  visible before a GSD run.

### Helpers copied out of `skills/ai-kit-opencode-providers/`

- The skill itself is live as a user-invocable skill: `SKILL.md` names
  `ai-kit-opencode-providers.py`, and it is installed on this machine. No other skill or tool
  imports it.
- `ai_kit_opencode_providers/jsonc_edit.py` (513 lines; JSONC classify, strip comments, strip
  trailing commas, provider walk and removal) was ported verbatim twice:
  - `tools/config_doctor_readers.py` (`_classify`, `strip_jsonc_comments`,
    `strip_trailing_commas`, each docstring says "Ported from the jsonc_edit module").
  - `tools/config_doctor_appliers.py` (a second `_classify` plus the surgical walk,
    "ported VERBATIM").
  So there are three copies of the JSONC classifier, two of them inside `tools/` alone.
- `ai_kit_opencode_providers/atomic_write.py` (`write_preserving_mode`) was adapted into
  `tools/setup.py` (`_atomic_write_json`, "Adapted from …atomic_write.py"),
  `tools/config_doctor_appliers.py` (`atomic_write_json`, `atomic_write_text`), and
  `skills/ai-kit-usage-metrics/ai_kit_usage_metrics/raw_store.py` plus `dashboard.py` (two
  `_atomic_write_text`, the dashboard one ported from the config-doctor appliers). Smaller
  private `_atomic_write` copies also live in `tools/gen_test_groups.py`,
  `skills/ai-kit-session-wake/ai_kit_session_wake/state.py` and
  `skills/jev-fast-decision/scripts/eval_cases.py`.
- `config_paths.py` overlaps with `config_doctor_checks.resolve_runtime_config_paths()`.
  `cross_reference.py` (finds review-spec and catalog references to a provider) has no copy.
- Suggested fate: merge. Inside `tools/`, keep one JSONC scanner and one atomic writer: make
  `config_doctor_appliers.py` import the classifier from `config_doctor_readers.py` instead of
  holding a second copy. Across skills, either accept the copies (skills install one at a time,
  and each must stay standalone), or move the scanner and writer into `skills/_shared/` the way
  `ai_kit_rules_common` already serves the rules family. Then the opencode-providers skill becomes
  either a thin user of that shared module or a "list/remove" subcommand of the config doctor.
  The AGENTS.md rule names `_read_json_checked()` / `_atomic_write_json()` as the house writer,
  so the copies already diverge from that rule's intent.

### Thin shims in the rules skills (live, by design)

- Each of the six `ai-kit-project-rules-*/…/remediation.py` files is 12 lines that re-export
  `ai_kit_rules_common.remediation.build_remediation`. `ai-kit-project-rules-agents/…/tool_presence.py`
  re-exports the shared `tool_presence`, and the makefile and precommit packages each hold
  `stack_cache.py` and `tooling_payload.py` namespace bindings over the shared engine.
- Who references them: each package's own `cli.py` imports them, and so do the tests. They are
  not orphaned.
- Suggested fate: optional cleanup. The `remediation.py` and `tool_presence.py` shims exist only
  "so existing imports keep working". Importing the shared module directly in each `cli.py`
  would delete 7 files. Low value; mention only if the milestone already touches the rules
  family.

## Live, no action (checked because the name scan looked thin)

- `tools/command_ownership.py`, `tools/config_doctor_app.py`, `tools/config_doctor_checks.py`,
  `tools/config_doctor_readers.py`: loaded by `tools/setup.py` through `_sibling("…")`.
- `tools/hooks/detect.py`: loaded by `importlib.import_module("detect")` in
  `claude_session_start.py`, `cursor_session_start.py` and `advisor_core.py`.
- `skills/ai-kit-spec-review/ai_kit_spec/model_ranker.py`: loaded by curated-config's
  `catalog_adapter.py` through `load_ai_kit_spec_module("model_ranker")`, and documented in
  `ai-kit-spec-config/references/cli-model-selection.md`.
- `skills/mermaid-audit/evals/score_consensus.py`: named by `evals/judge-protocol.md`. It is an
  eval tool, not runtime code.
- Every skill's top-level entry script is named in its own `SKILL.md`. Every module inside a
  skill package has an in-package importer except the two test-only ones above.

## Side finding: three skills are not installed on this machine

`ai-kit-cross-ai`, `ai-kit-session-wake` and `ai-kit-spec-goal-prompt` have no link under
`~/.claude/skills/`, `~/.agents/skills/`, pi or opencode. `~/.claude/settings.json` has no
`claude_session_wake` hook entry. They were last changed today (c104c5f). The code that installs
them is live in `tools/setup.py`, so they are not orphans; the machine's install is behind
`main`. Re-running the installer should fix it. That was not run here (read-only task).

## Dead code count (vulture)

- `uv run --frozen vulture` with the project config (`min_confidence = 80`): 0 findings.
- At `--min-confidence 60` (flag only, config unchanged): 100 findings, 55 of them outside
  `tests/`: 20 unused methods, 18 attributes, 10 variables, 7 functions. Most are framework
  callbacks (Textual `on_mount`/`on_key`/`action_*`, urllib `redirect_request`/`http_open`) or
  segments dispatched by name, which are false positives. These are really dead (each name
  appears only at its own definition):
  - `tools/setup.py`: `_visible_len`, `_trunc_visible`, `_env_truthy` (and probably
    `_term_dimensions`: one call site, not traced).
  - `tools/wizard_app.py`: `_goto`, `_review_from_board`, `_all_hosts_gate_done`.
  - `skills/ai-kit-spec-execute-gsd/ai_kit_spec_gsd/gsd_config.py`: `resolve_model_profile`.
  - Suggested fate: delete them in a small cleanup.

## Suggested milestone scope, smallest first

1. Delete `.planning/docs/system-one-decision-skill/scratchpad/` and the 2026-10-13 prototype
   `cross-ai.mjs`, or mark the prototype as research.
2. Document `eval_cases.py` in `jev-fast-decision/reference.md`, and add a Makefile target or a
   doc line for `cross_ai_catalog.py`.
3. Add a check that this repo's `.planning/scripts/cross-ai.mjs` body still matches the template.
4. Within `tools/`: one JSONC classifier and one atomic writer. Across skills: decide between a
   shared module in `skills/_shared/` and accepting the copies, and decide whether the
   opencode-providers skill folds into the config doctor.
5. Delete the 7 dead private functions that vulture finds at 60% confidence.

Not checked: whether each dynamically loaded name actually resolves at runtime (I trusted the
string matches); whether `.claude-plugin/plugin.json` or the host settings files should list the
three uninstalled skills; the bodies of the `review-history/` files.
