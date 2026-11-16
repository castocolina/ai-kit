# Phase 33: One config design - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-11-13 (auto draft) · rewritten 2026-11-14 (owner-led)
**Phase:** 33-one-config-design
**Mode:** owner-led rewrite; order of authority: the owner's words of 2026-11-14, then the 2026-11-07 transcript,
then jev (advisory), then the owner on low confidence.

## Why the rewrite

The 2026-11-13 run specced, discussed and planned this phase in one night with no owner review; the 2026-11-07
alignment summary had promised that the config design would be flagged for the owner's confirmation, and it was not.
On 2026-11-14 the owner stopped the run, kept the draft as a draft, and gave the decisions below. The draft's choices
that conflicted (one file per concern, `lanes.toml`, `.aikit/cross-ai.json` as JSON, the GSD-scoped retry) are
replaced; its live facts and the decisions that still hold are carried, marked "(draft D-nn)" in CONTEXT.md.

## The owner's input (2026-11-14, translated)

- Objected to `review-spec.toml` (named after one skill) holding other commands' settings: use a neutral name such as
  `settings.toml` or `config.toml`, or split one file per skill; if it is one file, its entries must be well
  structured.
- The entries are not structured today: spec-config was supposed to catalog every available model (models.dev,
  Artificial Analysis, LM Arena Elo as the alternative), classify them, and then propose the coding and review sets
  for the user to confirm; instead everything said "reviews".
- Asked whether `./.aikit/` or `~/.aikit` should hold a directory with several configs or one with everything.
- `workflow.cross_ai_retry` was never requested; ai-kit must not add things to third-party schemas that can be lost,
  and must run in a project without GSD, so without `.planning/`.

## Decisions

| Question | Options considered | jev (advisory) | Decision |
|----------|--------------------|----------------|----------|
| One file or several | (a) one neutral `config.toml` per layer, a table per concern, state files apart; (b) one file per skill; (c) none | typesafe choice a 0.91; laya low 0.39 a | (a) — D-01; lanes, retry and jev settings are shared by several skills |
| User directory | (a) existing `~/.config/ai-kit` (XDG); (b) new `~/.aikit`; (c) none | typesafe choice a 0.82; laya low 0.46 c | (a) — D-02 |
| Entry structure | role-keyed `[[lanes.review]]` / `[[lanes.execute]]` vs one reviewer list | none (owner's words) | role-keyed lanes, catalog classification left to Phases 35-36 — D-03 |
| Retry home | ai-kit `config.toml` `[runner.retry]` vs `.aikit/cross-ai.json` (draft) vs GSD config | none (owner's words) | `[runner.retry]`; GSD block and user JSON migrated out — D-13 |
| Runner and TOML | TOML-subset reader in the runner vs keep a JSON side file | none; own reasoning | subset reader — one file per layer is the owner's choice; the subset is small and fails closed — D-07 |
| Trust in a shared file | narrow the trust digest to command-bearing lanes vs keep a separate trusted file | none; own reasoning | narrow the digest, reviewed by `/gsd-secure-phase` — D-11 |
| Foreign keys and GSD | allow ai-kit keys in GSD config vs never | none (owner's words) | never; ai-kit runs without `.planning/` — D-17, D-18 |
| The draft's plans | keep and amend vs supersede | none | supersede, archive tag, replan — D-23 |

## Ledger

- Own reasoning, not blocking: D-07 (runner subset reader), D-11 (trust digest). Both go to `/gsd-secure-phase` and
  plan review.
- Owner was told the two jev-settled answers (D-01, D-02) before this rewrite.
