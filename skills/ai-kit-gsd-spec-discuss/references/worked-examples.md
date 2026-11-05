# Worked examples (1–5 from the ai-kit v1.3 run, 2026-10-14; 6 illustrative)

Load only when a case is unclear. Each shows what jev said, what the evidence said, and
what was logged.

## 1. A confident jev answer overridden, confirmed by a second opinion

Phase 17, K08: "Which model pairs form the price-ceiling sample?"
- jev answered `every_pair 0.91` (confident).
- Evidence: effort variants of one model repeat one price, so "every pair" weights a single
  model several times and skews the percentile.
- Second opinion: `families 1.00`.
- Logged: `| K08 ceiling sample | every_pair 0.91; second opinion families 1.00 | **jev
  overridden:** effort variants repeat one price and would skew the percentile (D-16) |`.

## 2. A near-tie second opinion that still loses to the evidence

Phase 18.1, T2: "Delete the Claude subprocess inventory?"
- jev answered `delete_all 0.75`; the second opinion `keep_for_review` came back low (0.74).
- The answers are effectively split, and a low second opinion is no confident second opinion,
  so row 3 ends in own reasoning. Evidence decides: Phase 18 R2 fills `review.models.claude` on
  codex/opencode hosts from that inventory.
- Logged: `| T2 inventory | delete_all 0.75; second opinion keep_for_review low 0.74 |
  **Own reasoning:** no confident second opinion; R2 fills review.models.claude from it (D-19,
  ledger) |`.

## 3. Both low → own reasoning, ledgered, flagged for the user

Phase 24, C08: how a remote call is approved.
- jev answered `session_only 0.65` (low); the second opinion `user_level_persistent 0.60` (low).
- The SPEC's "recorded once" approval is a user-locked decision; the jev-fast-decision skill
  says to confirm before the first call each session. Two documents disagree, so no answer
  settles it.
- Decided provisionally (persistent per-user record, announced every run, revocable). Because
  the provisional answer would change that user-locked decision, it is flagged
  `needs confirmation` — the only rule that flags — and ledgered; not a stop, because nothing
  else in the run depended on it. (An answer that agreed with the locked decision would not be
  flagged; decision-table row 1.)

## 4. A confident out-of-scope recommendation

Phase 23, B12: the status line needs Cursor's config dir; hooks use the same variable but the
CLI reads hooks from a fixed path.
- jev answered `fix_both 0.97`; the second opinion `separate_resolver 0.99`.
- Feasibility check: the hooks fix is small but changes Phase 21's gate and is outside the
  phase's requirements.
- Decided: separate resolver now; the hooks mismatch filed as backlog `999.2` with a goal.

## 5. A live fact amends earlier phases

Phase 19 (spec): `config-new-project` copies `~/.gsd/defaults.json`, including
`resolve_model_ids: "omit"`; with it, `resolve-model` returns `model: ""` on claude.
- No model was asked; it was a scratch-dir experiment.
- Same commit amended 17-SPEC R5/R13, 18-SPEC R13 and added 17 D-21.

## 6. A low answer (illustrative ids)

The ids and options are illustrative, not from a real run.

- **Low answer, no second opinion needed.** Item X02: jev answered `option_b 0.62` with
  `needs_fallback` true. Row 4 applies: reason against the evidence; the low answer is one
  input, not the decision. Ledger it when it blocks nothing.
