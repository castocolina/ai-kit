# Phase 36: spec-config as the hub - Discussion Log (standard discuss mode (`--analyze --all --batch`) for the interactive path)

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the analysis.

**Date:** 2026-11-16
**Phase:** 36-spec-config-as-the-hub
**Mode:** interactive path: no owner question was unclear enough to relay (the owner answers only unclear gray areas in this
run); every gray area was screened with jev and decided by the decision table; no gsd-assumptions-analyzer run (the owner
did not ask for it; the scouting was done live in the phase subagent), best design over smallest diff
**Areas analyzed:** code layout, the no-config check and chain, per-role orders, effort key and forms, escalation flags,
the proposal and jev ranking, seed-flag refusals, the referee rule, the migration backup, the headless stop, todo folding

## Assumptions Presented

No analyzer ran. The scouting covered each host's effort flag in its own `--help`, the runtimes snapshot's per-model effort
levels, the runner's effort handling, every code path that reads the shared order or a seed flag, the policy merge, the
migration rename, and the three skills' no-config behavior, all live on 2026-11-16 (SPEC Background).

| Assumption | Confidence | Evidence |
|---|---|---|
| A read-only status command can serve both skills without touching the router | Confident | `ai-kit-spec-execute` never reads lanes; the review skill and the adapter each resolve `TOOLS_PY` already |
| Per-role orders fit the existing layered reader and splicing writer | Confident | `toml_splice.set_table` takes a path tuple; policies merge shallowly so a role table is replaced whole per layer |
| Effort support can be learned per model for every host from a listing | Unclear | only pi (72 of 89 models) and codex (8 of 8) carry levels; the rest need a probe or Phase 35's reads |
| The runner can pass an effort to claude and copilot | Unclear | it has no path; Phase 37 owns `cross-ai.mjs` |
| jev scores are stable enough to order a shortlist | Unclear | one real item scored 0.74 then 0.67; a stability rule is a researcher question |

## jev screening

Four requests: spec items (eight), a second request for two of them, discuss items (seven), a second opinion on the ranking
shape. Summaries only.

| Item | jev | Outcome |
|---|---|---|
| no-config trigger | laya low 0.41; typesafe low 0.55 | **Own reasoning:** no lane in either layer (D-02, ledger) |
| chain behavior | ask_then_chain, choice 0.87 | D-02 |
| adapter wiring | all_now, choice 0.77 | D-03 |
| per-role orders | laya array_order 0.71 contradicted the layer-merge evidence; second request typesafe low 0.71 policy_subtables | **jev overridden**: D-04 (own reasoning, ledger) |
| effort with unknown support | typesafe refuse 0.82 (first request); probe_then_decide, choice 0.93 (second request with the probe fact) | **jev overridden** (first answer): D-05 |
| `review_only` refusals | remove_refusal, choice 0.86 | D-08 |
| escalation targets | configured_lanes_same_role, choice 0.84 | D-06 |
| migration default | laya low 0.43; typesafe low 0.68 | **Own reasoning:** D-10, needs confirmation (ledger) |
| code layout | laya low 0.55; typesafe low 0.58 | **Own reasoning:** D-01 (ledger) |
| jev ranking shape | laya one_choice_best 0.84; second opinion typesafe low 0.79 | **jev overridden**: D-07 (score_each, ledger) |
| effort key | laya low 0.43; typesafe low 0.65 | **Own reasoning:** D-05 (ledger) |
| escalation flag home | flat_keys_on_lane, choice 1.00 | D-06 |
| referee rule home | rule_in_same_guard, choice 0.82 | D-09 |
| exec formula source | python_mirror_with_drift_test, choice 0.81 | D-08 |
| effort question for no-path runtimes | skip_question_say_why, choice 0.82 | D-05 |

## Live facts that changed the plan

- claude and copilot have an effort flag in their own help, but the runner has no path for either, so the wizard cannot
  offer them yet (R4, D-05): the roadmap's "effort in the runtime's own form" splits between this phase and Phase 37.
- codex's listing offers effort levels that the runner's closed set rejects, so "known to be accepted" needs the runner's
  side too (R4).
- The no-config hint in the review skill keyed on a missing runtimes snapshot, a different fact from no lanes (R2).
- The shared order is read by three paths and filtered by purpose in one; a per-role table cannot live inside the lane
  arrays and a nested table is replaced whole by the project layer (D-04).
- `review_only` refuses in five places, and the one remaining fact is the runner's own missing formula (R7, D-08).
- The referee pointer rule exists only for SKILL.md main flow (`REFEREE_RE`); rails, defaults and docs are unguarded (R8).

## Corrections Made

- ROADMAP Phase 36 and its requirements gain dated notes (code anchors, criteria 1 to 3, new criteria 4 to 6, the judge bar
  moves to 7); Phase 37 criterion 1 and Phase 41 criterion 1 and EXE-01 carry the handoffs; HUB-05 notes the effort split;
  33 D-12 notes the backup default.
- SPEC R4 was refined after the discuss screening: no question for runtimes with no runner path, and levels the runner
  rejects are not offered.

## External Research

None. No web source was needed; every claim is from the installed hosts' own `--help` and the repository.

# Update 2026-11-16 (re-run 2, herdr hosting and free models; standard discuss mode with the owner answering only unclear items)

**Input:** `36-SPEC.md` (R12 added in this commit) and the 2026-11-16 CONTEXT (D-01..D-14 kept verbatim, D-14 refined, D-15..D-19
added). No analyzer ran; no owner question was unclear enough to relay. Owner directive: select free models in spec-config
with a usage-limited record so an alternative lane exists and the order falls back to it; reconcile 36 D-14.

**Areas analyzed:** where "usage-limited" comes from, its config shape, the alternative-lane rule, free models in the shortlist,
herdr hosting versus the wizard's questions

## Assumptions Presented

| Assumption | Confidence | Evidence |
|---|---|---|
| A free model is recognisable by its id wording | Corrected | two zero-price entries of one provider have no such wording; one display name says `Unlimited` |
| A host or the catalog states a daily limit | Corrected | none does: `opencode models` prints bare ids, `/api/model` and models.dev carry price and token limits only; one vendor page states one cap in prose (web, unverified) |
| A zero price means free with a limit | Corrected | zero price also appears on 19 plan providers, gateways and local runtimes (80 providers in models.dev) |
| The wizard can ask the owner while a runner hosts calls in panes | Confident | the runner hosts calls it makes; the questions stay in the owner's session (D-19) |
| Free lanes need a different run path | Unclear | the runner's hosting trigger and the hard tier for a daily cap belong to Phases 37, 38.1 and 40 |

## jev screening

Two requests: five items, then a second request for one. typesafe answered; laya gave no answer in this run. Summaries only.

| Item | jev | Outcome |
|---|---|---|
| source of the usage-limited fact | owner_declares, choice 0.88 | D-15 |
| config shape and fallback | flat_flag_plus_order, choice 0.95 | D-16 |
| role with only flagged lanes | ask_then_allow_explicit_none, low 0.67 | **Own reasoning:** same option (D-17, ledger) |
| free models in the shortlist | plain_ranking_only 0.89 contradicted the owner's wish to select free models; second request with the wish stated: own_group_same_ranking low 0.62 | **jev overridden**: own reasoning, D-18 (ledger) |
| herdr hosting key | no_key_runner_decides, choice 0.94 | D-19 |

## Live facts that changed the plan

- No program-readable source states a usage limit, so the flag can only be owner-declared (D-15); a name rule would misfire both ways.
- Price reaches the catalog from opencode's own `/api/model` and models.dev only; pi and cursor listings have no price (D-15, Phase 35 handoff).
- The one cap found is prose on a vendor page for one model, read through a summarising fetch: recorded as unverified, never used by code.
- herdr 0.9.5 is installed here; the owner's evidence (an interactive opencode agent in a pane kept context) is a runner design input for Phase 37, not a wizard input.

## Corrections Made

- SPEC gains R12, 7 engine edge rows (46/46), 3 prohibition rows, an acceptance line and two scope notes; CONTEXT D-14 and D-12
  are refined, D-15..D-19 added, handoffs to Phases 35, 37, 38, 38.1, 40 and 41 added.
- ROADMAP Phase 36 gains criterion 8 and Phase 40 criterion 1 a dated note; REQUIREMENTS HUB-05, HUB-07 and REV-01 carry dated notes.

## External Research

One summarising web fetch of opencode's models page (web, unverified): one free model's stated cap, others "for a limited time".
No code or config value left the machine.
