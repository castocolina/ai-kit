---
name: ai-kit-usage-metrics
description: Run the local capture-refine-dashboard pipeline over Claude Code, opencode, Codex, Cursor, and rtk session logs, then open the static HTML usage-metrics dashboard. Use when the user asks about "usage metrics", "usage dashboard", "how do I use my AI CLIs", command history across Claude Code / opencode / rtk / Codex / Cursor, grep-family invocations grouped by session, or wants a filterable/sortable static HTML view of captured shell commands. Does not export or import data; never a hosted-database Artifact.
---

# ai-kit-usage-metrics

Thin wrapper around `ai-kit-usage-metrics.py`. Invoke the CLI; do not
re-implement capture, refine, classify, or dashboard generation in prose.

## Scope

Runs the local capture -> refine -> dashboard pipeline against Claude Code,
opencode, Codex, and Cursor session logs plus `rtk`'s own local stores,
entirely on this machine. There is no export/import step and no
browser-sandboxed Artifact mechanism. Session data never leaves the machine.

Raw sources (5):

- Claude Code `${CLAUDE_CONFIG_DIR:-$HOME/.claude}/projects/*/*.jsonl`
- opencode `${XDG_DATA_HOME:-$HOME/.local/share}/opencode/opencode.db`
  (session / message / part) plus `storage/**/*.json`
- rtk `${XDG_DATA_HOME:-$HOME/.local/share}/rtk/history.db` (commands +
  parse_failures) and `rtk/tee/*.log`
- Codex `${CODEX_HOME:-$HOME/.codex}/sessions/**/rollout-*.jsonl`
- Cursor `${CURSOR_CONFIG_DIR:-$HOME/.cursor}/projects/*/agent-transcripts/*/*.jsonl`
  only. Every Cursor envelope is flagged `source_confidence="low"`
  (community-reverse-engineered format, no official docs). Cursor's
  `store.db` is out of scope: live-verified opaque undocumented BLOB rows,
  never opened by this pipeline.

Outputs live under
`${XDG_DATA_HOME:-$HOME/.local/share}/ai-kit/usage-metrics/`
(`raw/*.jsonl`, `refined/refined.db`, `dashboard.html`). The default
dashboard path is
`~/.local/share/ai-kit/usage-metrics/dashboard.html`, opened via `file://`.

Never read or write the operator's real config to "just see real data"
during development; tests and verification use scratch `XDG_DATA_HOME` /
`CLAUDE_CONFIG_DIR` / `CODEX_HOME` / `CURSOR_CONFIG_DIR` trees.

Scheduling (cron / systemd timer) is out of this milestone. Invocation is
manual only (D-07). The gap is tracked as Backlog 999.2
("Cron/scheduling automation for usage-metrics daily ingestion").

## Resolve the entrypoint

Resolve once per invocation, in one Bash call, and record the printed path as
a **literal absolute path**.

```bash
for d in "${CLAUDE_PLUGIN_ROOT:+$CLAUDE_PLUGIN_ROOT/skills/ai-kit-usage-metrics}" \
         "$HOME/.claude/skills/ai-kit-usage-metrics" \
         "${XDG_CONFIG_HOME:-$HOME/.config}/opencode/skills/ai-kit-usage-metrics" \
         "$HOME/.agents/skills/ai-kit-usage-metrics" \
         "$(dirname "<absolute path to THIS SKILL.md>")"; do
  [ -f "$d/ai-kit-usage-metrics.py" ] && { printf '%s\n' "$d/ai-kit-usage-metrics.py"; break; }
done
```

If no candidate exists, stop and report that the skill is not installed.
Substitute the directory containing this SKILL.md for the fifth candidate
(used when the skill is invoked from a checkout).

## Subcommands

- `capture` — lossless raw JSONL ingest for each registered source
- `refine` — normalize captured records into `refined.db`
- `dashboard` — regenerate static `dashboard.html` from the refined DB
- `classify` — optional pattern-mining pass over opaque rows (never part of `run`)
- `run` — `capture` then `refine` then `dashboard`

```bash
python3 "$TOOLS_PY" run
```

`$TOOLS_PY` is the literal absolute path recorded from the resolution block.
The pipeline never sends data off-machine.

Partial runs use the same entrypoint with `capture`, `refine`, or
`dashboard`. Regenerating the dashboard never rereads `raw/*.jsonl`; it
queries `refined.db` only.

## Refined schema

`refined_commands` columns, verbatim from `refined_store.py`:

- `id` — SQLite primary key
- `raw_ref` — pointer back to the originating raw envelope
- `runtime` — source runtime (`claude` / `opencode` / `codex` / `cursor` / `rtk`)
- `session_id` — session the command belonged to
- `turn_id` — turn whose token/price figures this step inherits
- `date` — `YYYY-MM-DD` taken from `timestamp`
- `timestamp` — original event time when known
- `model` — model that served the turn
- `command_text` — literal command (or opaque script body)
- `family` — mechanical family tag (`rg` -> `grep`), empty when unknown
- `command_shape` — `simple` / `control_flow_script` / `unclassified`
- `step_index` — 0-based index of this step inside the decomposed command
- `step_count` — number of steps the original command produced
- `operator` — trailing operator that joined this step to the next (`&&`, `;`, `|`)
- `execution_certain` — `False` for an `&&`-gated step that may not have run
- `resolved_cwd` — working directory after cwd-resolution
- `source_confidence` — capture confidence (`high`, or `low` for Cursor)
- `tokens_input` — turn-level input tokens, duplicated onto every step of the turn
- `tokens_output` — turn-level output tokens, duplicated the same way
- `price` — estimated USD cost for the turn, duplicated the same way
- `price_confidence` — how the price was derived (`unknown` / `not_applicable` / catalog)
- `rtk_input_tokens` — rtk history.db input tokens, rtk rows only
- `rtk_output_tokens` — rtk history.db output tokens, rtk rows only
- `rtk_saved_tokens` — rtk-reported saved tokens, rtk rows only
- `rtk_savings_pct` — rtk-reported savings percent, rtk rows only
- `rtk_rewrote` — whether rtk rewrote the command, rtk rows only
- `inferred_family` — LOW-confidence family from `classify`, never overwrites `family`
- `inferred_confidence` — confidence of `inferred_family` (`LOW` when set)
- `exec_duration_ms` — execution duration when the source reports one

Token/price figures on a compound command are turn-level values duplicated
onto every step sharing `(session_id, turn_id)`. Session totals must
dedup on that pair before summing; invocation counts still count every
matching row.

## `command_shape` limitation

`control_flow_script` is a recognized `if` / `for` / `while` / `case` /
`until` / `select` block, captured as one opaque entry, never decomposed
into fabricated sub-commands.

`unclassified` is a segment the decomposer's quote-aware scanner could
not structurally close (unterminated quote or unsupported shape),
distinct from a recognized-but-opaque script block.

Both buckets are the intended seed for the classification refinement
pass, not permanent dead ends.

## Cursor caveat

Cursor capture is explicitly low-confidence. Every envelope carries
`source_confidence="low"` because the agent-transcripts JSONL format is
community-reverse-engineered, not officially documented. The dashboard
renders that value in its own column; do not present a Cursor row with
the same certainty as a Claude Code or opencode row.

`store.db` is excluded: it holds opaque undocumented BLOB rows (`blobs`
table, `meta` table empty). Support for it is additive future work if
the format is ever documented.

## Classification refinement loop

The `classify` subcommand exists and is tested against synthetic fixtures
reproducing the PRD's own for-loop example. It is NEVER run automatically
by `run`. `run` stays exactly three steps: `capture` -> `refine` ->
`dashboard`.

The PRD's own intended trigger is "after the first real end-to-end runs
of the capture->refine pipeline against actual historical session
logs... not on a fixed schedule, and not before real data exists to
mine". Invoking `classify` for real, against a user's own accumulated
history, is a separate, later, user-initiated action, not something this
phase's own automated delivery performs on the user's behalf.

`DEFAULT_MIN_OCCURRENCES` (currently `2` in `classify_loop.py`) is a
documented placeholder, not a researched constant. The PRD's own framing
is "exact threshold TBD once real data volume is known". A future tuning
pass should change that constant once real volume is known; do not treat
`2` as a measured optimum.

`classify` updates SQLite only — it does NOT regenerate `dashboard.html`.
Seeing updated `inferred_family`/`inferred_confidence` values in the
dashboard after a `classify` run requires a subsequent, separate
`dashboard` subcommand invocation. The exact two-step sequence is:

```
ai-kit-usage-metrics.py classify
ai-kit-usage-metrics.py dashboard
```

An `inferred_family` value is a LOW-confidence annotation on matching
`control_flow_script`/`unclassified` rows. It never overwrites the row's
own `family` or `command_shape` columns, which stay exactly as the
mechanical decomposer originally set them. Ambiguous groups (two or more
equally plausible curated-tool tokens in the sample body) are left
unclassified rather than guessed.

## Dashboard

`dashboard` embeds the refined rows as JSON in a static HTML file and
opens with no server. Filters and sorts cover the 5 MVP axes (date,
model, family + command-text substring, tokens, price) plus a group-by-
session toggle. A row with empty `family` but set `inferred_family`
renders as `{inferred_family} (inferred, {inferred_confidence})`. A row
with `execution_certain=False` renders a `(conditional)` marker.

The "current month" date preset is computed in the browser from
`new Date()` when the file is opened, so the same HTML answers that
preset differently depending on when it is opened. Every other embedded
value is fixed at generation time.

## NEVER

- Never re-implement capture, refine, classify, or dashboard generation
  in prose — the CLI owns quoting, atomic writes, and schema details a
  paraphrase will drift from.
- Never present `inferred_family` with the same certainty as mechanical
  `family`, or a Cursor `source_confidence="low"` row as a confirmed
  invocation — both are flagged inferences, not decomposer facts.
- Never treat an `execution_certain=False` (`&&`-gated) step as a
  confirmed run — a preceding `&&` may have short-circuited it.
- Never sum `tokens_input` / `tokens_output` / `price` per session
  without deduping on `(session_id, turn_id)` first — those figures are
  duplicated onto every step of a compound command.
- Never open Cursor `store.db` — it is opaque undocumented BLOBs, not a
  session log.
- Never send session data off-machine or wire a hosted-database
  capability to it — the dashboard is a local `file://` HTML file.
- Never run `classify` as part of `run`, and never claim `classify`
  refreshed the dashboard without a following `dashboard` invocation —
  `classify` writes SQLite only.
- Never read the operator's real `~/.claude` / `~/.codex` / `~/.cursor`
  trees to "just see real data" during development — use scratch env
  overrides.
- Never invent a cron/timer for this pipeline this milestone — that is
  Backlog 999.2.
