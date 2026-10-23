# Log formats

Read before writing a SPEC Interview Log, a CONTEXT, a DISCUSSION-LOG, an amendment or the
ledger. All artifacts in English.

## Cell format for a backend answer

- `choice 0.NN` — winning probability `top`, high.
- `choice 0.NN (fb)` — `fallback` true (below the threshold).
- `choice 0.NN (second opinion)` — from `--second-opinion`.
- `–` — not called (an earlier rung was high, or the backend was unavailable).
- `error: <code>` — the call failed; say what you did instead.

## SPEC Interview Log

```markdown
## Interview Log

`--auto`, one round. The open items went through the decision ladder (the local backend
first; `needs_fallback` items batched to the consented remotes in table order). Summaries
only, advisory. Rule: <quality rule branch>.

| Round | Perspective | Question summary | <backend> (advisory) | <backend> (advisory) | Decision locked |
|-------|-------------|------------------|-----------------|---------------------|-----------------|
| 1 | Simplifier | The skill's name? | ai-kit-gsd-phase-prep 0.46 (fb) | ai-kit-gsd-spec-discuss 0.89 | `ai-kit-gsd-spec-discuss` (R1) |
| 1 | Boundary Keeper | Delete the Claude subprocess inventory? | delete_all 0.75 | keep_for_review 0.74 (second opinion) | **Laya overridden:** Phase 18 R2 fills `review.models.claude` from it (R8) |
```

Drop a backend column only when that backend was never available for the whole run, and say so
in the intro line.

## CONTEXT decision entry

```markdown
- **D-14: The spike captures the payload under a scratch `CURSOR_CONFIG_DIR`** (SPEC R5
  amended).
  - <evidence, file:line, live check>
  - **Laya overridden** (edit_real_file 0.72): the CLI rewrites the file during use. TypeSafe
    second opinion scratch_config_dir 0.98.
```

The attribution comes last: one `<backend> <choice> 0.NN[ (fb)]` per answering backend, or
`**Own reasoning** (<backend> … , <backend> …): <why>. Ledger.`

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
# Phase NN: <name> - Discussion Log (Assumptions Mode)

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the analysis.

**Date:** YYYY-MM-DD
**Phase:** NN-slug
**Mode:** assumptions (`--analyze --all --batch`), decision ladder, <quality rule>, CodeGraph
**Areas analyzed:** <areas>

## Assumptions Presented

The analyzer was `gsd-assumptions-analyzer` (<model>), with <N> tool calls. <what it ran live,
what it did not>.

| Assumption | Confidence | Evidence |
|---|---|---|

## jev screening

One local call per item; `needs_fallback` items batched to the consented remotes in table
order. Summaries only.

| Item | <backend> | <backend> | Outcome |
|---|---|---|---|
| B10 spike capture | edit_real_file 0.72 | scratch_config_dir 0.98 (second opinion) | **Laya overridden**: D-14 |
| B14 preview | static_samples 0.35 (fb) | static_samples 0.66 (fb) | **Own reasoning:** synthetic cache (D-24, ledger) |

## Live facts that changed the plan
## Corrections Made
## External Research
```

The Outcome column always names the D-id. "Own reasoning" rows always say why, and whether they
are ledgered. The jev section heading stays "jev screening" even with no backend; then every
row reads `– | – | **Own reasoning:** …`.

## DISCUSSION-LOG (existing)

Append, never rewrite:

```markdown
# Update 2026-10-14 (assumptions mode)

**Input:** `NN-SPEC.md` (committed in `<sha>`) and the <date> CONTEXT (D-01..D-06 kept).
```

followed by the same sections as a new log.
