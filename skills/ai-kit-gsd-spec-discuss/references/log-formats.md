# Log formats

Read before writing a SPEC Interview Log, a CONTEXT, a DISCUSSION-LOG, an amendment or the
ledger. All artifacts in English.

## Cell format for a jev answer

- `choice 0.NN` — jev answered confidently (`needs_fallback` false); `0.NN` is its winning
  probability.
- `low 0.NN` — jev answered with `needs_fallback` true: low confidence, advisory only.
- `choice 0.NN (second opinion)` — from a second-opinion request on the same item.
- `none` — jev was not asked this item.
- `not installed` — the `jev-fast-decision` skill is not on this host.
- `error: <code>` — the call failed; say what you did instead.

## SPEC Interview Log

```markdown
## Interview Log

<Run mode and rounds: `--auto`, one round for the auto path; `interactive`, <round count>
rounds otherwise>. The open items went through jev: one advisory answer per item, and
`needs_fallback` items are decided by your own reasoning. Summaries only, advisory. Rule:
<quality rule branch>.

| Round | Perspective | Question summary | jev (advisory) | Decision locked |
|-------|-------------|------------------|----------------|-----------------|
| 1 | Simplifier | The skill's name? | ai-kit-gsd-spec-discuss 0.89 | `ai-kit-gsd-spec-discuss` (R1) |
| 1 | Boundary Keeper | Delete the Claude subprocess inventory? | delete_all 0.75; second opinion keep_for_review low 0.74 | **Own reasoning:** no confident second opinion; Phase 18 R2 fills `review.models.claude` from it (R8) |
```

When jev is not installed, keep the jev column and write `not installed` in it, and say so in
the intro line.

## CONTEXT decision entry

```markdown
- **D-14: The spike captures the payload under a scratch `CURSOR_CONFIG_DIR`** (SPEC R5
  amended).
  - <evidence, file:line, live check>
  - **jev overridden** (edit_real_file 0.72): the CLI rewrites the file during use. Second
    opinion scratch_config_dir 0.98.
```

The attribution comes last: one `choice 0.NN` or `low 0.NN` for the jev answer taken, or
`**Own reasoning** (jev …): <why>. Ledger.`

## Updating an existing CONTEXT (never regenerate)

- Header: `**Gathered:** 2026-09-23 (interactive); updated 2026-10-14 (assumptions mode, after
  20-SPEC.md)`.
- New decisions continue the numbering under `### Added 2026-10-14 (assumptions mode, after
  NN-SPEC.md)`.
- A refined locked decision gets an indented `**Refined 2026-10-14:** …` bullet; its text stays.
- Superseded text: `~~old text~~ *(superseded 2026-10-14, D-NN)*`.

## Cross-phase amendment markup

In the other phase's SPEC/CONTEXT, or in `REQUIREMENTS.md`/`ROADMAP.md`:
`*(amended 2026-10-14, 20 D-08: <one-line fact and its consequence>)*` — appended to the
sentence it corrects, or as an `- *Amended 2026-10-14 (NN D-xx):* …` bullet under a SPEC
requirement. Edge Coverage rows: `~~old resolution~~ *(superseded, D-NN)* new resolution`.

## DISCUSSION-LOG (new)

```markdown
# Phase NN: <name> - Discussion Log (<run mode: Assumptions Mode for the auto path, standard
# discuss mode (`--analyze --all --batch`) for the interactive path>)

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the analysis.

**Date:** YYYY-MM-DD
**Phase:** NN-slug
**Mode:** <run mode — auto path: assumptions (`--analyze --all --batch`); interactive path:
standard discuss mode (`--analyze --all --batch`) with the user>, jev screening, <quality rule> — add
", CodeGraph" only when the brief included the CodeGraph block.
**Areas analyzed:** <areas>

## Assumptions Presented

The analyzer was `gsd-assumptions-analyzer` (<model>), with <N> tool calls. <what it ran live,
what it did not>.

| Assumption | Confidence | Evidence |
|---|---|---|

## jev screening

One jev request per step that has open items; each item gets one advisory answer, and
`needs_fallback` items are decided by your own reasoning. Summaries only.

| Item | jev | Outcome |
|---|---|---|
| B10 spike capture | edit_real_file 0.72; second opinion scratch_config_dir 0.98 | **jev overridden**: D-14 |
| B14 preview | low 0.35 | **Own reasoning:** synthetic cache (D-24, ledger) |

## Live facts that changed the plan
## Corrections Made
## External Research
```

The Outcome column always names the D-id. "Own reasoning" rows always say why, and whether they
are ledgered. The jev section heading stays "jev screening" even when jev is not installed; then
every row reads `not installed` | `**Own reasoning:** …`.

## DISCUSSION-LOG (existing)

Append, never rewrite:

```markdown
# Update 2026-10-14 (assumptions mode)

**Input:** `NN-SPEC.md` (committed in `<sha>`) and the <date> CONTEXT (D-01..D-06 kept).
```

followed by the same sections as a new log.
