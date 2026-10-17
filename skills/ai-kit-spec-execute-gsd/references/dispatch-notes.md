# Dispatch notes: rationale and history

Background material for `SKILL.md` Step 2. Not needed to execute the workflow — read only if
you need to understand *why* a step is written the way it is.

## Why no manual quoting around `workflow.cross_ai_command`'s values

`SKILL.md` Step 2 stores the hook string with NO manual quoting around its tokens. This is
deliberate, not an oversight:

GSD's own `cross_ai_delegation` step expands `workflow.cross_ai_command`'s stored value as a bare
`${CROSS_AI_CMD}` (word-split by whitespace only, never re-parsed as shell syntax, no `eval`),
so only word splitting and globbing apply to it. A quote character embedded in the stored string
is NOT a quoting boundary at that point — it is just another literal character stuck onto
whichever word it falls inside.

The hook therefore carries only tokens from an allowlist (letters, digits and `._:/@+=,#-`, plus
one bracket suffix on a cursor model id). A model id or any other token outside that allowlist
never becomes a hook: the adapter returns `fallback_notice` with reason `unsafe_hook_token`
instead of writing a broken string. One accepted limitation remains: GSD expands the value
unquoted, so a cursor bracket id such as `model[effort=high]` is a glob class and changes if a
file with a matching name exists in the project root.

## Codex confinement

The hook passes `--codex-sandbox workspace-write` for a codex executor, the same confinement the
old direct-dispatch path used. The runner then uses `--sandbox workspace-write` instead of the
bypass, so writes stay inside the project directory plus `/tmp` and `$TMPDIR`, which
workspace-write always allows. Whether GSD's own git commits succeed under `workspace-write` is
unverified: `.git` writability under it has not been confirmed. Every other exec target runs with
full permissions and gets only the soft-confinement sentence in the guidance file, which is
guidance, not a boundary. `claude` is review-only and never a hook target. pi exec uses the
runner's pi formula, verified by its hermetic self-test only; live verification is Phase 22.

## History: the guidance file supersedes the old guidance-append step

`RESULT_MODE = "cross_ai_hook"` needs no separate guidance-append step in Step 3 anymore.
(Superseded by Step 2's tracked guidance file.)

Earlier, Step 3 appended cross-AI dispatch reinforcement guidance directly to
`$PHASE_PROMPT_FILE`, relying on GSD's own `cross_ai_delegation` step to carry that content
through into the prompt it pipes to the external CLI. That worked in live testing, but rested on
an assumption worth naming: GSD's own recipe extracts specific `<objective>`/`<tasks>` sections
from the plan file to build its `$TASK_PROMPT`, not necessarily the whole file verbatim — so an
appended block could in principle land outside what GSD actually extracts.

A later Step 2 composed that guidance inside a `dispatch-execute` wrapper at the moment of the
subprocess call. The hook now names the project's own supervised runner instead. Step 2 renders or
upgrades that runner and the guidance file through curated-config `ensure-runner`; a user-edited
runner is never
overwritten and gets a `.new` file plus the printed notes. The guidance (reinforcement with GSD's
SUMMARY.md format block, tooling guidance, and the soft-confinement sentence for every runtime
except codex) lands in `.planning/scripts/cross-ai-guidance.md`, which the hook places before the
prompt with the runner's own preamble off, so nothing is said twice. The hook stays unquoted: GSD
expands the stored value by word splitting and pathname expansion, so a quote character would be
a literal, not a quoting boundary.

A custom entry (a `command` and no `runtime`) is the one exception to "every subprocess runs
through the runner": the fixed-argv custom launcher runs it on the same supervision core, and only
as a reviewer. Exec mode routes it `review_only`, so it never becomes a GSD hook.

The underlying guidance functions still live in `ai_kit_spec.dispatch_guidance`
(framework-agnostic, shared with any future `ai-kit-spec-execute-<other-framework>` adapter) and
`ai_kit_spec_gsd.cross_ai_guidance` (GSD's own real SUMMARY.md shape) — only WHERE they get
composed changed, not what they say or that they stay out of GSD's own workflow/skill files
entirely.
