# Session-default entries (spec-config Step 2.7)

Read this at Step 2.7, before the session-default ask. `$TOOLS_PY` is the literal path SKILL.md Step 0
printed; `host` is the value `detect-current-runtime` printed.

## Native or subprocess

A reviewer or executor is a (runtime, model) pair. Each call runs it natively when its runtime is the current host and the host can select that model; otherwise it runs as a subprocess through the supervised runner. An entry with neither a runtime nor a model is the session default, which the host always runs natively. Today only Claude Code selects a model per call (its sonnet, opus, haiku and fable aliases); every other host runs only its session default natively.
Those four are the
`native_selectors` of the claude row of ai-kit's runtime table (`RUNTIMES` in the review skill's
`ai_kit_spec/detection.py`), the only aliases routing runs natively, and not Claude Code's whole
alias list; Step 1's `detect-runtimes` prints them as `aliases` for an installed claude, and that
live list is the authority.

## When the printed host looks wrong

When several CLIs are nested, their environment markers accumulate and `detect-current-runtime`
returns the first marker in a fixed precedence (pi > opencode > cursor > codex > claude); it does not
verify which CLI is the immediate parent. A codex or opencode session started from Claude Code
records that CLI, not claude, but a pi marker left in the environment wins even when another CLI
started later. When the owner says the printed host is not the active one, explain that precedence
and offer a session-default entry without a host-specific alias.

## The entry's shape

- **`host` is `claude`:** the entry is the pair `runtime = "claude"` plus one of the short aliases
  that host defines (shown here as `placeholder-alias-1`), never a full model id such as
  `placeholder-model-1`; ask the owner to pick one of those aliases (the `aliases` list of Step 1's
  `detect-runtimes` output) rather than typing a version string. That pair has a `model`, so it
  carries a `vendor` like any other pair: Step 2.3 with `--runtime claude` prints `anthropic`. It is
  a table-runtime pair, so it also goes through Step 2.5 (the write-risk ask, then
  `check-reviewer --runtime claude`) before it is saved; a declined test saves it untested and
  Step 4 names it.
- **Any other host, or `unknown`:** the entry is the session default (no `runtime`, `model = ""`),
  because only Claude Code's aliases are verified per-call selectable.

## Why it is always offered

It is the only zero-external-dependency option: it needs no extra CLI and no external quota probe
(the session's own quota still applies and is not observable here), so it is useful as a primary pick
or a pure fallback, depending on where the owner places it in its role's order (`wizard-flow.md`
step 9). A host-run entry is never automatically prioritized over a subprocess one: only its
position in its role's order decides priority, and quota or availability failures decide fallback;
for a pure fallback, place it last in that order.
