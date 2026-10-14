# Worked examples (from the ai-kit v1.3 run, 2026-10-14)

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

Lesson: a high Laya number is not evidence. The override needs the second opinion *and* the
reason written down.

## 2. A near-tie second opinion that still loses to the evidence

Phase 18.1, T2: "Delete the Claude subprocess inventory?"
- Laya `delete_all 0.75`; TypeSafe second opinion `keep_for_review 0.74`.
- The models are effectively split. Evidence decides: Phase 18 R2 fills `review.models.claude`
  on codex/opencode hosts from that inventory.
- Logged as **Laya overridden** with that reason.

Lesson: when the models tie, do not average them — the evidence breaks the tie, and the log
says which fact did.

## 3. Both low → own reasoning, ledgered, flagged for the user

Phase 24, C08: consent model for remote calls.
- Laya `session_only 0.65 (fb)`; TypeSafe `user_level_persistent 0.60 (fb)`.
- The SPEC wants consent "recorded once"; the companion jev skill says "confirm before the first
  call each session". Two documents disagree, so no model settles it.
- Decided provisionally (persistent per-user record, announced every run, revocable), flagged
  `needs confirmation`, ledgered — not a stop, because nothing else in the run depended on it.

Lesson: a genuine policy conflict between documents is the user's call; record the provisional
choice and keep going unless it blocks.

## 4. A confident out-of-scope recommendation

Phase 23, B12: the status line needs Cursor's config dir; hooks use the same variable but the
CLI reads hooks from a fixed path.
- Laya `fix_both 0.97`; TypeSafe second opinion `separate_resolver 0.99`.
- Feasibility check: the hooks fix is small but changes Phase 21's gate and is outside the
  phase's requirements.
- Decided: separate resolver now; the hooks mismatch filed as backlog `999.2` with a goal.

Lesson: "fix it now" is checked for feasibility, not reflexively deferred — and a deferral gets
a real backlog entry, not a note.

## 5. A live fact amends earlier phases

Phase 19 (spec): `config-new-project` copies `~/.gsd/defaults.json`, including
`resolve_model_ids: "omit"`; with it, `resolve-model` returns `model: ""` on claude.
- No model was asked; it was a scratch-dir experiment.
- Same commit amended 17-SPEC R5/R13, 18-SPEC R13 and added 17 D-21.

Lesson: the ladder is for judgment calls. Facts come from experiments, and they flow backwards
into every phase that stated the opposite.
