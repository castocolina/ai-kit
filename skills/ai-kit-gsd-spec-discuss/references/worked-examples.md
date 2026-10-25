# Worked examples (1–5 from the ai-kit v1.3 run, 2026-10-14; 6 illustrative)

Load only when a case is unclear. Each shows what the models said, what the evidence said, and
what was logged.

## 1. A confident Laya answer overridden, confirmed by a second opinion

Phase 17, K08: "Which model pairs form the price-ceiling sample?"
- Laya `every_pair 0.91` (high).
- Evidence: effort variants of one model repeat one price, so "every pair" weights a single
  model several times and skews the percentile.
- `--second-opinion`: TypeSafe `families 1.00`.
- Logged: `| K08 ceiling sample | every_pair 0.91 | families 1.00 (second opinion) | **Laya
  overridden:** effort variants repeat one price and would skew the percentile (D-16) |`.

## 2. A near-tie second opinion that still loses to the evidence

Phase 18.1, T2: "Delete the Claude subprocess inventory?"
- Laya `delete_all 0.75`; TypeSafe second opinion `keep_for_review 0.74`.
- The models are effectively split, and the 0.74 second opinion is below TypeSafe's threshold
  (`fb`) — no high remote answer, so decision-table row 3 ends in own reasoning. Evidence
  decides: Phase 18 R2 fills `review.models.claude` on codex/opencode hosts from that
  inventory.
- Logged: `| T2 inventory | delete_all 0.75 | keep_for_review 0.74 (fb, second opinion) |
  **Own reasoning:** no high remote answer; R2 fills review.models.claude from it (D-19,
  ledger) |`.

## 3. Both low → own reasoning, ledgered, flagged for the user

Phase 24, C08: consent model for remote calls.
- Laya `session_only 0.65 (fb)`; TypeSafe `user_level_persistent 0.60 (fb)`.
- The SPEC's "consent recorded once" is a user-locked decision; the companion jev skill says
  "confirm before the first call each session". Two documents disagree, so no model settles it.
- Decided provisionally (persistent per-user record, announced every run, revocable). Because
  the provisional answer would change that user-locked decision, it is flagged
  `needs confirmation` — the only rule that flags — and ledgered; not a stop, because nothing
  else in the run depended on it. (An answer that agreed with the locked decision would not be
  flagged; decision-table row 1.)

## 4. A confident out-of-scope recommendation

Phase 23, B12: the status line needs Cursor's config dir; hooks use the same variable but the
CLI reads hooks from a fixed path.
- Laya `fix_both 0.97`; TypeSafe second opinion `separate_resolver 0.99`.
- Feasibility check: the hooks fix is small but changes Phase 21's gate and is outside the
  phase's requirements.
- Decided: separate resolver now; the hooks mismatch filed as backlog `999.2` with a goal.

## 5. A live fact amends earlier phases

Phase 19 (spec): `config-new-project` copies `~/.gsd/defaults.json`, including
`resolve_model_ids: "omit"`; with it, `resolve-model` returns `model: ""` on claude.
- No model was asked; it was a scratch-dir experiment.
- Same commit amended 17-SPEC R5/R13, 18-SPEC R13 and added 17 D-21.

## 6. A forced column (illustrative ids)

The ids and options are illustrative, not from a real run.

- **Forced local, high remote.** Item X01: Laya `option_a 0.91 (forced)`, TypeSafe
  `option_b 0.94`. `decided_by` is TypeSafe, so row 4 applies: take `option_b` unless it
  contradicts the evidence; Laya's forced answer is logged beside it as advisory.
- **Forced local, no high remote.** Item X02: Laya `option_a 0.91 (forced)`, TypeSafe
  `option_b 0.62 (fb)`. `decided_by` is `own_reasoning` (row 5): reason against the evidence;
  the forced answer is one input, not the decision. Ledger it when it blocks nothing.
