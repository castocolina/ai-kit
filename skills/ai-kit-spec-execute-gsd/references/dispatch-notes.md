# Dispatch notes: rationale and history

Background material for `SKILL.md` Step 2. Not needed to execute the workflow — read only if
you need to understand *why* a step is written the way it is.

## Why no manual quoting around `workflow.cross_ai_command`'s values

`SKILL.md` Step 2's `WRAPPER_COMMAND` line builds the stored `cross_ai_command` string with NO
manual quoting around `$TOOLS_PY`/`$RESULT_CLI`/`$RESULT_MODEL`/`$CWD`/`$FORMAT_BLOCK_PATH`. This
is deliberate, not an oversight:

GSD's own `cross_ai_delegation` step expands `workflow.cross_ai_command`'s stored value as a bare
`${CROSS_AI_CMD}` (word-split by whitespace only, never re-parsed as shell syntax, no `eval`). A
quote character embedded in the stored string is NOT a quoting boundary at that point — it is just
another literal character stuck onto whichever word it falls inside, so `--cli \"$RESULT_CLI\"`
would hand `dispatch-execute` the literal 8-character argument `'"codex"'` (quotes included)
instead of the bare 5-character `codex` it needs.

This means values with actual whitespace cannot be passed safely through this hook at all — a
real, structural limitation of GSD's own naive `${CROSS_AI_CMD}` expansion (not something this
adapter can fix without editing GSD's own workflow prose), same as it already was for the raw
external-CLI command string this replaces.

## History: Step 2's wrapper supersedes the old guidance-append step

`RESULT_MODE = "cross_ai_hook"` needs no separate guidance-append step in Step 3 anymore.
(Superseded 2026-08-30 by Step 2's direct-dispatch wrapper.)

Earlier, Step 3 appended cross-AI dispatch reinforcement guidance directly to
`$PHASE_PROMPT_FILE`, relying on GSD's own `cross_ai_delegation` step to carry that content
through into the prompt it pipes to the external CLI. That worked in live testing, but rested on
an assumption worth naming: GSD's own recipe extracts specific `<objective>`/`<tasks>` sections
from the plan file to build its `$TASK_PROMPT`, not necessarily the whole file verbatim — so an
appended block could in principle land outside what GSD actually extracts.

Step 2's wrapper command sidesteps this: `dispatch-execute`'s own `--format-block-file` composes
the SAME reinforcement guidance (model-selection override, incremental progress, honest failure
reporting, and GSD's own real SUMMARY.md shape) directly INTO the dispatch itself, at the moment
of the real subprocess call — guaranteed to reach the dispatched CLI regardless of what GSD's own
extraction includes.

The underlying guidance functions still live in `ai_kit_spec.dispatch_guidance`
(framework-agnostic, shared with any future `ai-kit-spec-execute-<other-framework>` adapter) and
`ai_kit_spec_gsd.cross_ai_guidance` (GSD's own real SUMMARY.md shape) — only WHERE they get
composed changed, not what they say or that they stay out of GSD's own workflow/skill files
entirely.
