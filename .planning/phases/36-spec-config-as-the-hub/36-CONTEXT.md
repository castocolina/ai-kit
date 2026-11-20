# Phase 36: spec-config as the hub - Context

**Gathered:** 2026-11-16 (interactive path, no owner question needed, jev screening, after 36-SPEC.md); updated 2026-11-16 (re-run 2, herdr hosting and free models, interactive path, jev screening, after the 36-SPEC.md R12 amendment); updated 2026-11-16 (free-lane pool study and data use, owner directive, accepted by the owner the same day); updated 2026-11-20 (plan time: D-20 to D-23 copied from ROADMAP and REQUIREMENTS, and the plan-time decisions record)
**Status:** Ready for planning (after Phase 35 lands: this phase reads its classified catalog, usability records, per-(runtime, model) efforts and hardcoding guard)

<domain>
## Phase Boundary

Every skill that reads lanes (the review skill and the execute adapter) checks for config through one read-only command
and chains spec-config with one ask. The written config keeps reviewers and executors apart: a priority order per role,
an effort per lane in the runtime's own form where it is known to be accepted, and escalation flags that stay off unless
the owner says yes. spec-config proposes a review set and a coding set from the Phase 35 catalog (jev scores, the owner
picks), no runtime-table flag refuses a lane, a verified migration leaves no backup by default, and a referee rule joins
Phase 35's guard.
</domain>

<spec_lock>
## Requirements (locked via SPEC.md)

**11 requirements are locked.** See `36-SPEC.md` for full requirements, boundaries, and acceptance criteria.

Downstream agents MUST read `36-SPEC.md` before planning or implementing. Requirements are not duplicated here.

**Refined 2026-11-16 (re-run 2, D-15 to D-19):** 12 requirements are locked; R12 (free models selectable, a usage-limited
flag and an alternative lane) is added, and R1 to R11 are unchanged.

**Refined 2026-11-20 (plan time, D-20 to D-23, first drafted 2026-11-16 from the free-lane pool study):**
13 requirements are locked; R13 (a free model's data-use note and the owner's confirmation, HUB-10) is added, R12 gains
clause (g) (each zero-price lane's pool and the different-pool fallback), and R7's acceptance names a placeholder CLI
instead of grok (grok is not a target in this phase).

**In scope:** the no-config check and chain (R1, R2); per-role orders (R3); effort per lane (R4); escalation flags (R5);
the proposal command and wizard flow (R6); removing seed-flag refusals (R7); the referee rule (R8); the migration backup
default (R9); the headless stop (R10); skill text, docs and the judge bar (R11).

**Out of scope:** any run reading the escalation flags (Phases 37, 40, 41); the runner's effort flags for claude and
copilot, its closed effort sets, `unknown_runtime`, `no_inventory`, `exec: null`, the `modelId` gate (Phase 37); the
adapter's resume and stop paths and session-model fallback (Phase 41); jev choosing executors (Phase 42); the catalog (35).
</spec_lock>

<decisions>
## Implementation Decisions

### Layout (SPEC R1, R5, R6, R4)

- **D-01: One small new module per concern, each with its own tests; `cli.py` only wires subcommands.** Modules (names are
  the plan's to fix): config status (R1), lane proposal (R6: pool, ranking seam, jev seam), lane settings (R4's effort
  forms and level validation, R5's `lane_escalation` reader). `cli.py` (about 1,000 lines), `config_io.py` (959) and
  `runner_dispatch.py` (663) are near the pylint caps, and Phase 35 D-01 set the same pattern. **Own reasoning** (jev
  low both rungs: laya skill_prose_only 0.55, typesafe new_module_and_command 0.58): the proposal must be unit-testable
  with a fake jev, which skill prose cannot be. Ledger.

### The chain (SPEC R1, R2, R10)

- **D-02: `config-status` is the one check; the skills hold a short numbered block.** The command lives beside
  `check-providers` in `cli.py`, reuses `cfg_load_layers`, the trust reader and the pending-migration read
  (`config_io.py`), and prints `active`, `pending` or `none` with the paths checked (exit 0; a malformed file is a named
  error, exit 2). A roster counts when a layer holds at least one lane; a session-default lane counts, so a user who chose
  session-only is not asked again. On `none` the skill asks once through the host's question tool or numbered plain text:
  run setup now / run once on the session model / stop; an empty or unknown answer is `stop`. A host with no way to ask
  prints the notice and runs on the session default for this run (nothing written), shown in the surface message. The
  review skill's old missing-snapshot hint is replaced. jev chain_mode choice 0.87 (laya: ask_then_chain). Trigger:
  **Own reasoning** (jev low both rungs: laya no_file 0.41, typesafe no_roster_either_layer 0.55): the roster is the fact
  a lane run needs, a file's existence and the runtimes snapshot are different facts. Ledger.
- **D-03: The check is wired in the review skill's Step 0.7 and the adapter's first step; the router is unchanged.**
  `ai-kit-spec-execute` never reads lanes (it hands off to GSD or the adapter). The adapter's block is the only edit to
  its SKILL.md in this phase; Phase 41 keeps it and owns the resume and stop paths. jev adapter_wiring choice 0.77. The
  amendment to EXE-01 and Phase 41 criterion 1 is made in this commit.
  - **Refined 2026-11-20 (plan time):** the EXE-01 and Phase 41 criterion 1 amendment named above already exists
    (REQUIREMENTS.md EXE-01 and ROADMAP.md Phase 41 criterion 1, both amended 2026-11-16 citing 36 D-03); this phase writes
    nothing further there.

### The config shape (SPEC R3, R4, R5)

- **D-04: Per-role orders are `[lanes.policy.review]` and `[lanes.policy.execute]` with a `ladder` each.** `mode` and
  `timeout_tiers` stay in `[lanes.policy]`; a legacy shared `ladder` loads as each role's order filtered to that role's
  lanes with a note, and is rewritten on the next write; a dangling key is dropped with the existing warning. Policies
  merge shallowly today (`{**DEFAULT_POLICY, **user, **project}`), so a role table from the project layer replaces the
  user's whole role table: project over user per role. The writer keeps writing `purpose` on each lane for the readers
  that still filter by it (`quota.py`, `execute_selection.py`) until Phases 37 and 41 retire it. Readers change: the
  review path reads the review order, the adapter's `top_n_keys` the execute order, `probe-quota` probes the keys of both.
  **jev overridden** (array_order 0.71 from laya: the order of a lane array has no meaning across two merged layers, and the
  ordered list names keys from both). A second request with the merge fact stated: policy_subtables, typesafe low 0.71.
  **Own reasoning.** Ledger.
- **D-05: One flat `effort` key on any lane; the runtime's form is decided in one place at argv build.** Forms in
  `runner_dispatch.py`, reused by the preview (`build-command`), the probe (`review_spec`) and the dispatch: codex
  `--codex-effort`; pi `:level`, cursor `[effort=...]` and opencode `#variant` composed onto the bare stored model id (a
  stored id that already carries one keeps working and is read as that effort, per Phase 35 D-04). The offered levels come
  from, in order: the Phase 35 catalog's `efforts` for (runtime, model); the runtimes snapshot's `reasoning_modes`; else
  unknown. Unknown support is learned by one probe: `check-reviewer` gets `--effort` (it already takes `--extra-json`),
  the call that answers stores the effort labelled `accepted by a call on <date>`, a rejection stores nothing and shows the
  host's first error line (control characters removed, key shapes redacted by `secret_shapes.py`). A listed level the
  runner's closed set rejects is not offered and is named (codex lists levels beyond the runner's `xhigh`). *(amended 2026-11-16, 37 D-01, D-07: the forms in `runner_dispatch.py` and the
  Python composers are transitional, and the runner's closed level sets go; Phase 37 moves every runtime's effort form into the
  runner behind one `--effort` flag, so previews read the runner's `--print-argv`, and deletes the Python composers; Phase 36
  still builds them first because its probe call needs them)* For claude and
  copilot the wizard does not ask (jev effort_offer choice 0.82), says why in one line and writes none. Per-runtime keys
  versus one key: **Own reasoning** (jev low: typesafe per_runtime_keys 0.65, laya inside_model_id 0.43): `effort` already
  is the generic knob read by `review_spec` and `build-command`, and a second spelling per runtime would multiply the
  validator. The probe: jev effort_unknown choice 0.93 on the second request, first request refuse 0.82 contradicted the
  owner directive that unknowns are learned live (**jev overridden**, SPEC log). Ledger for the key.
- **D-06: Escalation is two flat booleans on a lane, read through one function.** `escalate_runtime` and `escalate_model`,
  absent means false, written only when true, non-boolean refused with the key named; the targets are other lanes of the
  same role in the declared order (runtime: the next lane of a different runtime; model: the next lane of the same runtime),
  never an unlisted model (jev escalation_target choice 0.84; flat keys choice 1.00). `lane_escalation(entry)` is the one
  reader for Phases 37, 40 and 41. The wizard asks only for a role with two or more lanes, default no, and states "stored,
  no run reads it yet" the way `strength` is stated today (informational flags are labelled, never shown at the confidence
  of an enforced setting). No ranking, proposal or default sets a flag, pinned by a test.

### The proposal and the wizard flow (SPEC R6)

- **D-07: `propose-lanes --purpose review|execute` is read-only and deterministic first.** Pool from the Phase 35 catalog:
  usability not `rejected`, not stale, not `unmatched`, class `flagship` for review and `coding` or `fast` for execute;
  unknown tier or class is kept and shown below the known ones; "show more" first lengthens the list (default 5 per purpose),
  then widens the pool to every non-router class with its class label. Deterministic order: the existing
  `score_candidates` with the `review` or `execution` weights from `ranking-weights.toml` (execution already weights price).
  jev: one score per candidate for fit to the purpose, from labelled facts (tier, class, cost band, strengths, effort
  levels; no names, config values or keys; an index maps answers back), one jev request per proposal; the scores give
  the order, the scorer breaks ties and stands in when jev gives a low answer, an error or no answer; each row names who
  ranked it. **jev overridden** (one_choice_best: laya 0.84, second opinion typesafe low 0.79): HUB-07 says jev ranks the
  candidates, and one best pick plus the scorer's order is not a ranking; own reasoning decides score_each. The run-to-run
  variance of jev scores (one real item scored 0.74 then 0.67) is a researcher question: a stability margin or a cache per
  catalog version. Ledger. `router-env/<x>` aliases come in their own group labelled `assumed: router-env alias naming`
  (purpose guessed by the existing name heuristic, labelled assumed), outside the ranking and outside jev. Flow (owner items
  2 to 4): preferred runtimes per purpose first; then the shortlist per purpose, one confirmation per set; then per
  chosen lane its effort (D-05), then each role's order (default the ranking order, echoed as a numbered list), then
  escalation (D-06); then write only the chosen lanes. The old Step 2.2 catalog-per-runtime and heuristic-confirm loop moves
  into Phase 35's catalog step; Step 2.6's `strength` stays an informational ask.

### Refusals, migration, guard (SPEC R7, R8, R9)

- **D-08: No seed flag refuses a lane; the one fact left is the runner's formula.** The `review_only` field goes. A
  Python field `exec_formula` mirrors the runner's per-runtime `exec` entry with a source label, and a test asks the runner
  offline (`--print-argv`) for every runtime and fails on drift (jev exec_formula_source choice 0.81 over asking the runner
  at each routing decision, which would spawn node in a pure function; laya ask_runner_each_time low 0.56). The route is
  `no_formula` (mode and runtime named) in place of `review_only` in `routing.py`, `SKIP_ROUTES`, `dispatch_injection.py`'s
  route list, the skill texts that name `review_only`, `SUPPORTED_EXECUTE_CLIS` (derived from rows with a formula),
  `execute_cli_error` (names the formula fact) and `execute_selection.py`. A seed advice string (for claude: usually the main
  agent here, unverified) is shown by the wizard and the preview, never used by a branch. `config_io.py`'s save error for a
  runtime outside the table says "store a custom `command` lane" instead of printing the table. `unknown_runtime` and
  `no_inventory` mirror the runner's own gate and go with Phase 37. Phase 37 deletes `exec_formula` and its drift test once
  the runner learns each formula. *(amended 2026-11-16, 37 D-10: Python then reads the runner's `--describe` fact, recorded in the
  runtimes snapshot and keyed by the template hash; `no_formula` stays only as the name of that recorded fact, `unknown_runtime`
  and `no_inventory` stop refusing at routing)* On a Claude Code host the aliases still run natively.
- **D-09: The referee rule is a rule inside Phase 35's guard.** Same scanner, baseline and non-vacuity convention (jev
  referee_rule_home choice 0.82). Outside tests, `.planning/`, `.aikit/` and the owner's config files, an unmarked
  `router-env/<x>` literal in a skill, rail template, default or doc fails; a marked example passes; in tests it stays
  allowed for pi and opencode. The project's tracked GSD config and the owner's `.aikit/config.toml` hold the owner's own
  lanes and are not scanned. The baseline gains today's violators (live: the curated-config evals, the goal-prompt eval
  config, the runner's two literals, the docs plans), each naming the phase that cleans it; this phase cleans every file it
  rewrites. The existing `test_skill_text_history.py` rule stays.
- **D-10: A verified migration deletes the old roster file by default; keeping a backup is opt-in.** The step (4)
  comparison still gates it, the rename guard on a changed old file still applies (a changed file is left in place with
  the existing error). The opt-in must be reachable before any implicit migration, because `probe-quota`,
  `resolve-reviewers` and `trust-local` migrate on read: the plan picks an environment switch read in `config_migrate.py`
  only, plus `--keep-backup` on `render-toml` (open question). The runner's `cross-ai.json.migrated` is not changed here.
  **Own reasoning** (jev low both rungs: laya keep_renamed 0.43, typesafe delete_after_verify 0.68), following the owner's
  2026-11-16 words "never needed a backup". It supersedes the draft-origin step (6) of 33 D-12 (amended there). **Needs
  owner confirmation** (a deleted file is not recoverable). Ledger.
- **D-11: spec-config's headless stop.** When it has no way to ask, it stops after Step 1's detection and prints the pending
  decisions (installed runtimes, listing counts, the questions it would ask), writes nothing, and says a person must run it
  (the `--check-only` pattern). R2's no-way-to-ask exit relies on it.

### Skills, docs, todos

- **D-12: Three SKILL.md files meet the judge bar:** `ai-kit-spec-config` (Steps 1 to 4 rewritten: detection stops for the
  headless case, one question per role, the effort and escalation questions, the migration line), `ai-kit-spec-review` (Step
  0.7 block, `no_formula` wording) and `ai-kit-spec-execute-superpowers` (first-step block, `no_formula` wording). Doc-contract
  tests pin each block; `docs/config/design.md`, `config-file.md` and the READMEs follow (the config design record has its
  own fitness test). A judge loop applies per AGENTS.md; History stays in a trailing section.
  - **Refined 2026-11-16 (re-run 2, D-15 to D-18):** `ai-kit-spec-config`'s question flow also holds the zero-price group, the
    usage-limit question for a chosen zero-price lane and the alternative-lane step; `config-file.md` and the design record name
    `usage_limited` and `usage_limit_note`; the wizard says "stored, read only by the lane-switching phase".
- **D-13: Todo folding.** From the 2026-11-16 wizard todo: items 2, 3, 4 and 5 and the headless note fold into this phase
  (R6, R3, R9, R10). The 2026-10-29 lane-TOML todo folds items 1 to 4 (effort per model, role stated by the caller as the file
  shape, runtime and model escalation flags); its items 5 and 6 (jev classifies the input prompt and the result) belong to
  Phase 42 (EXE-03 picks effort by task; criterion 5 classifies results). The other matched todos concern other skills.
- **D-14: jev and herdr are conditional.** jev is used only for the proposal's scores and only when present (probed at
  runtime, summaries only, advisory); the no-jev order is tested. herdr is not used: the wizard needs the owner at every step,
  and nothing here watches a long lane.
  - **Refined 2026-11-16 (re-run 2, D-19):** the sentence stands for the wizard's own questions, which are always asked of the
    owner in the owner's session, never in a pane or by another agent. The owner's herdr hosting directive concerns the runner
    (Phases 37 and 38) and changes nothing the wizard asks or writes: a call the wizard makes through the runner (the effort
    probe, the test call before saving) may be hosted in a pane when herdr is available, with the same result and the same
    file. "herdr is not used" no longer means the phase is blind to it: the output with and without herdr is pinned identical.

### Added 2026-11-16 (re-run 2, herdr hosting and free models, after the R12 amendment)

- **D-15: Only the owner can say a lane is usage-limited; a zero price only triggers the question.** Live (SPEC Background):
  a host's own listing and models.dev state a price of zero for free models, and no source a program can read states a daily
  or other limit; a zero price also appears on subscription plans, gateways and local runtimes, a free model may have no
  marker in its id, and one display name says `Unlimited`. So nothing is inferred from a price, a name or a shipped list (a
  table never decides, and only `router-env/<x>` names may be hardcoded). For each chosen zero-price lane the wizard asks:
  yes (optional one-line note) / no / not sure; only yes writes the flag. The price comes from the catalog's cost fact with its
  source and date (Phase 35); for hosts whose listing has no price (pi, cursor, and codex, claude and copilot checked here
  only as far as their listings go) the source is models.dev through Phase 35's matching, so a model models.dev does not
  match shows price unknown and gets no question. jev owner_declares choice 0.88 (consistent with the evidence).
- **D-16: A flat boolean `usage_limited` on the lane, an optional display note, and one reader; the fallback is derived from
  the role's order.** `usage_limited = true` (written only when true, TOML boolean, non-boolean refused with the key named,
  valid on a lane of either role) and `usage_limit_note` (one line, control characters removed, length capped, display only,
  never parsed, never sent to jev). The fallback rule: a flagged lane's fallback is the first lane of the same role, in that
  role's `ladder` order, that is not itself flagged (no explicit fallback key: the order already is the owner's preference,
  and a key naming a lane could dangle). `lane_usage_limit(entry)` and `lane_fallback(role_lanes, key)` live in the lane-settings
  module beside `lane_escalation` (D-01, D-06), the one place consumers read them. The flag is the owner's opt-in that a quota
  stop on this lane may move to the next lane: it does not conflict with the owner rule "never switch harness, provider or model
  on failure", which applies to a lane the owner did not flag. No run reads the flag in this phase; the wizard says "stored, read
  only by the lane-switching phase" the way `strength` and the escalation flags are stated (informational flags are labelled).
  jev flat_flag_plus_order choice 0.95 (consistent with the evidence).
- **D-17: A role whose only lanes are flagged gets an alternative proposed, an explicit none is allowed and warned, nothing
  refuses.** The wizard proposes the best-ranked unflagged candidate of that purpose (the ranking of D-07); the role is written
  after the owner adds one or says there is none; the explicit none prints a warning on every preview and the reader prints it
  for a hand-written file. Refusing would take away a deliberate single free lane and break the "the owner decides" rule of this
  phase, and no check at all would break the directive that an alternative must exist. **Own reasoning** (jev
  ask_then_allow_explicit_none low 0.67, the same option): the choice follows the directive and the owner-decides rule. Ledger.
- **D-18: Zero-price models get their own group in the proposal, from the same ranking.** After the ranked list each purpose
  shows a group `zero price` of up to 5 rows from the same pool (D-07's filters: usability, stale, unmatched, class), ordered by
  the same scores and labelled by the same ranker; each row shows `price: zero` with its source and date, and a local
  model reads `zero price (local or hosted not known)` unless the source says which. It reuses D-07's `score_candidates` and the
  single jev request (the group is a filter of the scored pool, not a second ranker); `router-env/<x>` aliases keep their group.
  **jev overridden** (plain_ranking_only 0.89: with the review ranking by quality and a top 5, the owner's wish to select a
  free model would often show nothing); second request with the wish stated: own_group_same_ranking, low 0.62. **Own
  reasoning.** Ledger.
- **D-19: herdr hosting does not change that the wizard asks the owner, and the config has no hosting key.** Reconciles 36 D-14
  (Refined there). The wizard's questions are asked in the owner's session only. A call the wizard makes through the runner may
  be hosted in a herdr pane when the runner (Phase 37) decides to; the pane's result channel, ownership and cleanup of what the
  runner opened, naming, `--no-focus` and the one-run-per-pane lock are Phases 37 and 38 (their locked 37 D-20 and 38 D-16
  statements are amended in those phases' own commits, not here). No config key records hosting (availability is a runtime
  fact: `HERDR_ENV=1` and the `herdr` CLI), so the written file is identical with and without herdr, pinned by a test with a fake
  herdr signal that also checks the wizard opens no pane. jev no_key_runner_decides choice 0.94 (consistent with the evidence).
  Open for Phase 37: whether the runner's trigger for hosting reads the lane (a free lane the owner selected) or only
  availability, and whether the owner can switch hosting off; if a config key turns out to be needed, it is a 37 requirement
  that this phase's writer and validator then carry (a one-line amendment here).
  *(amended 2026-11-16, 37 D-23: settled in Phase 37. The trigger is availability, never the lane; the owner switches hosting off with
  `--host none` or the environment variable `AIKIT_HOST=none`; no config key is needed, so this phase's writer and validator carry nothing
  new. The wizard's probe calls inherit `--host auto` from `runner_flags` and the written file stays identical.)*

### Added 2026-11-20 (plan time; copied from ROADMAP Phase 36 criteria 8 and 9 and REQUIREMENTS HUB-05 and HUB-10)

- **Plan-time decisions record:** section 0 ("Cross-area contract") of `36-RESEARCH.md` holds the decisions made at plan
  time (the plan map, the cross-cutting decisions and the standing rules); where it differs from parts A to D of that file
  it wins, and the plans cite it.
- **Source of D-20 to D-23 (first drafted 2026-11-16 from the free-lane pool study, owner directive):**
  `.planning/research/2026-11-16-opencode-free-models.md` (read 2026-11-16). Its labels: the free models appear to share
  one pool per account or network (reported by users, scope unresolved, maintainers say the limit is decided by the hosted
  service); the data-use exceptions per model come from the vendor's own docs page (verified, read 2026-11-16); only four
  of the listed free models are zero-retention, so project code may go to a third party; no machine-readable data-use
  field was found in the catalog (open question 5 there, unchecked).
- **D-20: A flagged lane records its pool (accepted by the owner on 2026-11-16, `.planning/docs/OWNER-DECISIONS-2026-11-16.md`; the shared pool itself is reported by users, not confirmed
  by a maintainer).** REQUIREMENTS HUB-05 (amended
  2026-11-16, free-lane pool study): "a flagged lane also records its pool (provider plus tier, for example the one pool that
  the free models of a provider appear to share)". ROADMAP Phase 36 criterion 8: "the flag is written with the lane's pool
  (provider plus free tier)". Source: `.planning/research/2026-11-16-opencode-free-models.md`, where the shared pool is
  reported by users and not confirmed by a maintainer.
  - **Refined 2026-11-20 (plan time, `36-RESEARCH.md` section 0 item 2):** the lane key is `pool` with the value
    `<provider>:free` (shape `^[A-Za-z0-9._-]{1,64}:[a-z]{1,16}$`; the tier is always `free` in this phase). It is derived
    from a zero price and written by the wizard on every chosen lane whose price is zero, flagged or not (so a fallback can
    compare pools), is valid on any lane, is labelled reported, and never sets `usage_limited`, which stays the owner's yes
    only (D-15). `propose-lanes` prints the same string as each row's `pool_key`. The string is a provider-level stand-in,
    because the real scope of the pool (account, IP, session) is not documented. It amends D-16: the flag stays flat and a
    second flat key joins the lane. The 2026-11-16 draft's `usage_pool` key in `<provider>/<tier>` form, written only with
    the owner's yes, is replaced by this plan-time form.
- **D-21: A flagged lane's fallback comes from a different pool (accepted by the owner on 2026-11-16, `.planning/docs/OWNER-DECISIONS-2026-11-16.md`).** REQUIREMENTS
  HUB-05: "the fallback is the first lane of the role that is neither flagged nor in the same pool". ROADMAP criterion 8: "a
  flagged lane's fallback is the first lane of the role that is neither flagged nor in the same pool". This replaces D-16's
  fallback sentence ("the first lane of the same role ... that is not itself flagged").
  - **Refined 2026-11-20 (plan time, `36-RESEARCH.md` section 0 item 3):** `lane_fallback(role_lanes, key)`, with
    `role_lanes` already in the role's order, skips `key` itself, every flagged lane and every lane whose non-empty `pool`
    equals the key lane's non-empty `pool`, and returns the first key left, else `None` (a lane without `pool` shares no
    pool, so only an equal string counts as shared). Reason: free models of one provider appear to draw on one pool, so an
    unflagged sibling would fail the same way. The alternative proposed by D-17 skips candidates of the flagged pool
    (`propose-lanes --avoid-pool`).
- **D-22: The wizard warns that the free models of one provider share one pool (accepted by the owner on 2026-11-16, `.planning/docs/OWNER-DECISIONS-2026-11-16.md`; the shared pool
  itself stays reported-grade).**
  REQUIREMENTS HUB-05: "the wizard warns that other free models of the same provider share the pool". ROADMAP criterion 8:
  "the wizard warns that other free models of the same provider share one pool". The warning says the shared pool is
  reported by users and not confirmed by the vendor: reported for opencode's free models, unverified for any other
  provider, and never presented as verified.
- **D-23: A free model's data-use note and the owner's confirmation (HUB-10; accepted by the owner on 2026-11-16, `.planning/docs/OWNER-DECISIONS-2026-11-16.md`, with the closed value list
  and the decline path as recorded here).** REQUIREMENTS HUB-10: "When the owner selects a free (zero-price) model that is
  not known to be local, spec-config shows the model's data-use note before anything else about the lane: `zero_retention`,
  `may_be_kept_or_trained` or `unknown`, with a display line, its source, the date it was read and a label (`verified` only
  for the vendor's own documentation page read in that run, else `reported`); an unreadable or silent source shows `unknown`
  and never defaults to a safe value, and no shipped list decides. It states that a review or execute lane sends project
  content to that vendor and asks the owner to confirm; a yes records the note and the confirmation beside the lane, a no or
  a skip writes no lane." ROADMAP Phase 36 criterion 9 states the same and adds that the research note lists only four free
  models as zero-retention, so project code may reach a third party.
  - **Refined 2026-11-20 (plan time, `36-RESEARCH.md` section 0 item 4, record contract corrected in plan review):** the
    record is flat keys on the lane: five always, `data_use` (`zero_retention`, `may_be_kept_or_trained` or `unknown`),
    `data_use_line` (one display line, at most 200 characters, control characters removed, key shapes redacted),
    `data_use_source` (an `https://` page of at most 300 characters, or `none`), `data_use_read` (`YYYY-MM-DD`) and
    `data_use_confirmed` (only `true` is storable), plus `data_use_label` (`verified` or `reported`) exactly when
    `data_use` is not `unknown`; a lane holds that whole record or no data-use key. There is no data-use
    CLI command: the wizard composes the keys and `render-toml` validates them. In this phase the proposal cannot tell
    local from hosted (every zero-price row reads `zero price (local or hosted not known)`), so the note is shown for every
    chosen zero-price lane. The vendor page is HTML and no program scrapes it: the calling skill reads it per model (a
    model the page does not name is `unknown`, a model listed twice takes the stricter statement) and the owner's own
    statement counts as `reported`. A no or a skip writes no lane and the owner may pick another candidate; `unknown`
    needs the same explicit yes. Owner-accepted 2026-11-16: the decline path (no lane written) and the closed value list;
    the rejected alternative was a lane written but marked unconfirmed, which would let an unconfirmed lane run later.

### Handoffs to later phases

- *Added 2026-11-16 (free-lane pool study):* **Phase 38.1**: R11 keys its blocked-until record by the same pool string
  (38.1 D-23). 38.1 D-23 still names the 2026-11-16 draft form `<provider>/<tier>`; the lane key is now `pool` with the
  value `<provider>:free` (D-20, refined 2026-11-20), so Phase 38.1 adopts that string in its own amendment. **Phases 40 and 41**: read `lane_fallback` (now different-pool) and the record (new EXE-09). **Phase 35**: the optional
  web source is how a vendor page is read; a catalog field for data use, if models.dev gains one, replaces the page read.
- **Phase 35**: this phase reads its per-(runtime, model) `efforts`, usability record, tiers and classes, and adds a rule to its
  guard; if the executed shapes differ, the plan adapts and records it.
- **Phase 37**: owns the runner side: claude and copilot effort flags, closed effort sets, the `exec: null` formula for claude,
  deleting `exec_formula` and the `no_formula` route, `unknown_runtime`, `no_inventory`, and reading the escalation flags
  through `lane_escalation`.
- **Phase 40**: lane switching reads the escalation flags. **Phase 41**: keeps the adapter's no-config block and decides whether
  `escalate_model` gates rounds 4 and 5 (today they run for everyone). **Phase 42**: jev picks the effort by task.
- **Phase 38.1**: the `rejected` effort line holds the first error line today and adopts the closed reason list later.
- *Added 2026-11-16 (re-run 2):* **Phase 35**: the catalog keeps the raw zero-price fact (input and output both zero) with its
  source (the host's own listing or models.dev) and date beside the `free_or_local` band, and says local versus hosted where a
  source does; if the executed catalog holds only the band, this phase's plan reads the price from the source records and records
  the difference. **Phase 37**: owns the runner's herdr hosting (D-19 open points) and may need the writer to carry a hosting key
  if it decides one. **Phase 38**: owns ownership, cleanup and lock of what the runner opens. **Phase 38.1**: a quota stop on a
  flagged lane is a quota-class stop that does not wait (a daily cap does not clear inside the hard tier's 4 hours, and a direct
  lane already stops at once per 38.1 D-12); how a host's message for a free lane's cap is worded is not captured (no free lane
  has reached its limit on this machine), so any such row stays unverified until captured. **Phase 40**: reads
  `lane_usage_limit` and `lane_fallback`: a quota stop on a flagged lane switches to the fallback lane at once, a lane without the
  flag never switches on its own; which other classes justify a switch is 40's call (38.1). **Phase 41**: executors read the same
  fallback rule when an execute lane hits its cap (its call).

### Open questions for the phase researcher

- The run-to-run variance of jev scores and the stability rule for the proposal order (D-07).
- The mechanism for the migration backup opt-in that works before any implicit migration (D-10).
- How the Phase 35 catalog names classes and efforts once executed, so the pool and the level source match it (D-05, D-07).
- Whether `probe-quota` should probe the union of both orders or only the roles in use (D-04).
- *Added 2026-11-16 (re-run 2):* whether the catalog's cost record separates local from hosted zero-price models (D-18); how
  `probe-quota` treats a flagged lane (its probe spends part of a limited allowance, D-16).

</decisions>

<canonical_refs>
## Canonical References

- `.planning/phases/36-spec-config-as-the-hub/36-SPEC.md` (requirements, live facts, findings)
- `.planning/phases/35-model-discovery-and-catalog/35-SPEC.md`, `35-CONTEXT.md` (catalog fields, guard D-16 to D-18)
- `.planning/phases/33-one-config-design/33-CONTEXT.md` (D-03 tables, D-11 trust, D-12 migration, D-22 reader, D-24 roles),
  `docs/config/design.md`
- `.planning/todos/pending/2026-11-16-spec-config-wizard-owner-observations.md`,
  `.planning/todos/pending/2026-10-29-unify-review-execute-lane-toml-effort-escalation-and-jev-classification.md`,
  `.planning/research/2026-11-16-opencode-free-models.md` *(added 2026-11-16: source of D-20 to D-23)*
- `skills/ai-kit-spec-review/ai_kit_spec/` (`config_io.py`, `config_migrate.py`, `quota.py`, `routing.py`, `commands.py`, `cli.py`,
  `runner_dispatch.py`, `execute_selection.py`, `model_ranker.py`, `toml_splice.py`), `references/cross-ai-dispatch.md`,
  `references/ranking-weights.toml`
- `skills/ai-kit-spec-config/SKILL.md`, `skills/ai-kit-spec-review/SKILL.md`, `skills/ai-kit-spec-execute-superpowers/SKILL.md`
</canonical_refs>
