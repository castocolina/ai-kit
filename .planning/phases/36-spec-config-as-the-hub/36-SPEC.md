# Phase 36: spec-config as the hub — Specification

**Created:** 2026-11-16
**Ambiguity score:** 0.15 (gate: ≤ 0.20)
**Requirements:** 11 locked *(amended 2026-11-16, re-run 2, 36 D-15 to D-19: 12 locked; R12 added for free models and usage-limited lanes; R1 to R11 unchanged)* *(amended 2026-11-16, free-lane pool study, 36 D-20 to D-23: R12 gains items g to i; 13 locked, R13 added for a free model's data-use note and confirmation; both PROVISIONAL)*

## Goal

Every `ai-kit-spec-*` skill that reads lanes reaches its config through spec-config: with no lanes configured it offers
the setup, with spec-config missing it fails naming the fix, and `--no-cross-ai` still runs on the session model. The
written config keeps reviewers and executors apart, each with its own priority order, an effort per lane passed only
where it is known to be accepted and in the runtime's own form, and escalation flags that stay off unless the owner
turns them on. spec-config proposes a review set and a coding set from the classified catalog (jev ranks, the owner
picks), and no runtime-table flag refuses a lane any more.

## Background

Requirements HUB-01, HUB-05, HUB-07 (REQUIREMENTS.md "spec-config as the hub"), the 2026-11-16 owner observations
(`.planning/todos/pending/2026-11-16-spec-config-wizard-owner-observations.md`, items 2 to 5 and the headless note), the
2026-10-29 lane-TOML todo, and the 2026-11-16 amendments (a runtime table never decides; Phase 35's hardcoding guard).
Phase 33 fixed the file shape (`[[lanes.review]]`, `[[lanes.execute]]`, `[lanes.policy]`, layered reader, splicing writer,
trust) and left per-role orders, effort and escalation here (33 D-24). Phase 35 delivers the classified catalog (tier,
class, cost band, strengths, usability, context per runtime) that the proposal reads, and the guard this phase extends.

**The owner's decisions (highest priority):**

- Catalog first, then a short choice per purpose (2026-11-14, 2026-11-16 todo): ask which runtimes the owner prefers for
  review and which for execute, show the ranked models for each purpose with the best fit first, few steps. Review
  favours semi-frontier models; execute favours cheap, fast, coding-capable models (the owner's own list includes Claude's
  short aliases, so Claude is a normal execute choice). Nothing is labelled review by default in the catalog.
- Review and execute are separate in every question and in the file; the file holds only what was chosen (the observed
  run wrote 19 lane entries and one mixed 18-key order for about 5 chosen models).
- `router-env/<x>` aliases are assumed, not asked: router, fallback quota, no per-model question, label
  `assumed: router-env alias naming` (35 D-15); they appear in their own group in the proposal.
- Escalation is opt-in per lane and off by default (2026-10-29 todo, owner rule "never switch harness, provider or model on
  failure" on its own).
- A runtime table is seed data and examples only; a row never blocks a lane; a setting a runtime cannot take is reported
  as ignored with the reason, never fed to it and never dropped silently; unknown means shown unknown until learned
  live (2026-11-16 directive).
- Only `router-env/<x>` model names may be hardcoded, and the hardcoded-referee test is the same guard family as Phase
  35's, not a second mechanism (HUB-09, 35 D-16 to D-18).
- The migration backup was never needed (2026-11-16 observation): see R9.
- *Added 2026-11-16 (re-run 2, owner directive "herdr hosting and free models"):* the owner wants to SELECT free models (for
  example an opencode free model, which often has a daily usage limit) in spec-config, with the config recording that the
  lane is usage-limited so that an alternative lane exists and the order of lanes can fall back to it: see R12. Where herdr
  is available at runtime the review and execute runner may always host a lane in a pane and close what it opened (a
  runner and run-safety matter, Phases 37 and 38); hosting never changes that the wizard asks the owner (D-19).

**Live facts checked for this spec (2026-11-16, this machine; claude 2.1.325, opencode 2.3.0, pi 1.5.2, cursor-agent
2026.11.13, codex 0.169.0, copilot 1.0.112, grok 1.0.52):**

- Effort forms in each host's own `--help`: claude `--effort <low|medium|high|xhigh|max>`; codex `-c
  model_reasoning_effort=<x>`; pi `--thinking <off|minimal|low|medium|high|xhigh|max>` or a `:level` suffix on the model;
  cursor-agent a bracket on the model (`[effort=...]`); opencode `provider/model#variant` in `--model`; copilot
  `--reasoning-effort <none|minimal|low|medium|high|xhigh|max>` ("supported levels depend on the model"); grok
  `--reasoning-effort` (alias `--effort`; grok has no runner formula).
- The runtimes snapshot carries per-model effort levels for two hosts only: pi (72 of 89 models) and codex (8 of 8).
  opencode, cursor, claude, copilot and grok carry none (opencode's own `/api/model` `variants` and cursor's names are
  Phase 35's R1 to R4 inputs, not yet read).
- The runner takes effort in three ways today: codex through `--codex-effort` (closed set minimal to xhigh), pi through
  its baked config only (`--thinking`, skipped when the model has a `:level` suffix), cursor and opencode inside the
  model id. It has no effort path for claude or copilot. Codex's own listing shows levels (`max`, `ultra`) that the
  runner's closed set rejects.
- `ai-kit-spec-review` with no config: `resolve-reviewers` degrades to `NO_CONFIG_FALLBACK` (the session default) with no
  message; the only hint ("No cross-AI config saved yet - run `ai-kit-spec-config`") prints when the runtimes snapshot
  file is missing, which is not the same fact as no lanes (`references/cross-ai-dispatch.md` point 3). The execute
  adapter has no no-config check; `ai-kit-spec-execute` never reads lanes.
- One shared ordered list of lane keys (`[lanes.policy] ladder`) serves both roles: the review path filters it by
  `purpose` (`quota.py`), `probe-quota` probes it (`cli.py`), the execute adapter reads it as `top_n_keys`. Policies from
  the two layers merge shallowly (`{**DEFAULT_POLICY, **user, **project}`), so a nested per-role table is replaced as a
  whole by the project layer. TOML cannot nest a table under an array of tables, so a per-role order cannot live inside
  `[[lanes.review]]`.
- Where a table row decides today (this phase owns these): `routing.py` route `review_only` (line 177, and `_route_shape`
  138 for custom entries in exec mode), `commands.py` `SUPPORTED_EXECUTE_CLIS` (66, excludes `review_only` rows),
  `execute_cli_error` (70) used by `dispatch-execute` (`cli.py` 973) and `execute_dispatch.py` (114),
  `execute_selection.py` 103, `config_io.py` 104-105 and `_RUNNER_RUNTIMES` (713, 721). `routing.py` `unknown_runtime`
  (141) and `no_inventory` (156) mirror the runner's own formula gate and go with Phase 37.
- The old roster backup: `config_migrate.py` renames the old file to `*.migrated` after the value check passes
  (`MIGRATED_SUFFIX`, line 16; rename guard line 344); 33 D-12 keeps it.
- `tests/test_skill_text_history.py` already bans `router-env/` and `referee-<x>` pointers in a SKILL.md's main flow
  (`REFEREE_RE`); nothing guards defaults, rails or docs. The project's tracked GSD config (`.planning/config.json`) and
  the owner's `.aikit/config.toml` hold referee aliases as the owner's own lanes.
- Model ids of one host are never printed in this spec (HUB-09 applies to docs).
- *Added 2026-11-16 (re-run 2), how a free model shows (live, this machine; opencode 2.3.0, models.dev fetched the same
  day):* `opencode models` prints bare `provider/model` ids only (no cost, no limit, no flag; its own `--help` has no verbose
  switch); opencode's `GET /api/model` (the private-server helper in `detection.py`) gives every model a `cost` list with
  `input`, `output` and `cache` figures (zero for the free entries), a `status`, an `enabled` flag and `limit` with
  `context`, `input` and `output` token counts, and no field for a daily or other usage limit (the free entries of the
  `opencode` provider also carry a public placeholder key setting, so they need no account; the `opencode-go` provider lists
  its own free entries). models.dev carries `cost.input` and `cost.output` per model (zero for free entries, `cache_read` and
  `cache_write` only sometimes) and `limit.context`, `limit.output` and sometimes `limit.input`; it has no daily-limit or
  quota field in any of its 9,895 model records and 324 provider records. A name ending in `free` is NOT a reliable marker:
  two zero-price entries of the `opencode` provider have no such ending, and one entry's display name says `Unlimited`.
  A zero price is also normal for subscription "plan" providers (19 provider ids contain `plan`), gateways and local
  runtimes (models.dev lists zero-price models under 80 providers), so zero price shows "no per-token price", never "has a limit" and
  never "has none". pi's listing (columns provider, model, context, max-out, thinking, images) and cursor-agent's listing
  carry no price at all; codex's listing and claude and copilot have none checked here: price for those hosts comes only from
  models.dev through Phase 35's matching. The only statement of a cap found is prose on opencode's own models page (read
  through a summarising web fetch, so *web, unverified*): one free model "with a limit of 100 requests per day", other free
  models "free for a limited time", some with data-retention notes. Nothing a program can read states a daily limit, so the
  fact that a lane is usage-limited can only come from the owner (D-15). herdr 0.9.5 is installed here.

## Requirements

1. **One no-config check for every skill that reads lanes (HUB-01)**: a read-only command reports whether lanes exist.
   - Current: no skill asks the fact "are lanes configured?"; the only signal is the runtimes snapshot file, a different fact.
   - Target: `ai-kit-spec.py config-status --cwd <root>` prints one state: `active` (a lane in the project or user
     layer, or a trusted project roster), `pending` (a project roster not yet trusted, or an old `review-spec.toml` not yet
     migrated: these go to the existing trust and migration flows, never to setup) or `none` (no lane in either layer, no old
     roster), with the paths it checked; exit 0 for all three; it writes nothing and migrates nothing; `strategy =
     "local-only"` makes it read the project layer alone, as the reader does.
   - Acceptance: tests with scratch HOME and fixture files cover `none`, `active` from the user layer only, `active` from the
     project layer only, `pending` for an untrusted command-bearing project roster, `pending` for an old roster, a
     `local-only` project with an empty roster beside a full user roster (`none`), and a malformed file (named error, exit 2).

2. **The chain, and its three exits (HUB-01)**: `ai-kit-spec-review` and the execute adapter run R1 at their entry and act on it.
   - Current: no config degrades silently to the session default; the adapter has no check; a missing spec-config is not
     mentioned.
   - Target: on `none`, ask once (`run ai-kit-spec-config now` / `run once on the session model` / `stop`); `run` chains the
     wizard and then continues the original task with the new config; `once` runs on the session default and prints the notice
     in the surface message; `stop` ends. When the host has no way to ask the user, the skill prints the notice naming
     `ai-kit-spec-config` and continues on the session default for this run, nothing written. A registered session-default
     lane counts as a roster (a user who wants session-only runs setup once and is never asked again). With the
     spec-config skill not installed, the skill stops with a message naming the fix (install ai-kit, then
     `ai-kit-spec-config`). `--no-cross-ai` never runs R1, never chains and never reads config. The old
     missing-snapshot hint is replaced by this check. `ai-kit-spec-execute` (the router) never reads lanes and is not
     changed.
   - Acceptance: doc-contract tests pin the entry block and the three answers in both skills; an eval per skill (no config,
     config present, `--no-cross-ai`, spec-config missing, no way to ask); a test shows the fixture project with no config
     reaches the chain and a project with an active roster never does.

3. **Reviewers and executors kept apart, with their own orders (HUB-05)**: each role has its own priority order and the wizard
   asks and writes them separately.
   - Current: one shared `ladder`; the wizard mixes both purposes in its order questions and writes every registered
     candidate.
   - Target: the written file holds `[[lanes.review]]`, `[[lanes.execute]]`, `[lanes.policy]` (mode, timeout tiers) and
     `[lanes.policy.review]` and `[lanes.policy.execute]` with a `ladder` each; the review path reads the review order, the
     execute path the execute order; a legacy shared `ladder` loads as each role's order filtered to that role's lanes with a
     visible note and is rewritten on the next write; a key in the order that names no lane of that role is dropped with a
     warning, as dangling keys are today; only the lanes the owner chose are written, never the catalog; a lane never serves
     both roles (two entries); the wizard asks the order of each role in its own question; project over user applies per
     role table.
   - Acceptance: tests cover write of both orders, read of both, a legacy shared order split by role, a dangling key, a
     role with no lane (no order table written), project-over-user per role, byte preservation of comments and unrelated
     tables through the splicing writer, and that no order is written for a role the owner did not configure.

4. **Effort per lane, in the runtime's own form, only where accepted, never dropped silently (HUB-05)**.
   - Current: a lane's `effort` reaches only codex; pi gets thinking from baked config only; claude and copilot have no path;
     an effort a model cannot take is not detected.
   - Target: a lane may carry `effort` for any runtime. The wizard offers an effort only from the model's known levels
     (listing or catalog, per (runtime, model)); where support is unknown it offers to run the existing test call with the
     effort set and stores it only when the call answers, labelled `accepted by a call on <date>` (a call that answers shows
     acceptance, not effect); a rejected call stores nothing and reports the host's first error line (control characters
     removed, key shapes redacted). The argv form per runtime lives in one function used by the preview, the probe and the
     dispatch: codex `--codex-effort`; pi, cursor and opencode as the model id carries it (`:level`, `[effort=...]`, `#variant`);
     claude `--effort` and copilot `--reasoning-effort` have no runner path yet (Phase 37 adds them): the wizard does not ask
     for an effort on those runtimes, says in one line why, and writes none; a lane written by hand with one prints
     `ignored: the runner has no effort flag for <runtime>` on every preview and dispatch. A level outside the model's own
     list, or one the runner cannot pass today (codex's listing shows levels the runner's closed set rejects), is not offered,
     and is refused at write with the list and the reason named; a stored effort the runtime cannot take at run time prints
     `ignored: <reason>`.
   - Acceptance: tests with fake hosts cover each form's argv (codex, pi, cursor, opencode), the two no-path runtimes (no
     question, a hand-written effort printing its reason), a level outside a listed set refused, a listed level the runner
     rejects not offered, unknown support probed and accepted, probed and rejected, a lane with no effort (nothing passed,
     nothing printed), and that no path drops a set effort without a line.

5. **Escalation flags, off unless the owner turns them on (HUB-05)**.
   - Current: no flag exists; the execute adapter escalates capability in fix rounds 4 and 5 with no owner opt-in
     (`references/escalation.md`).
   - Target: a lane may carry `escalate_runtime` and `escalate_model` (booleans; absent means false; written only when
     true); the targets are other lanes already configured in the same role, in the declared order: runtime escalation
     steps to the next lane of a different runtime, model escalation to the next lane of the same runtime; never to a model
     that is not a configured lane. The wizard asks only when a role holds two or more lanes, default no, and says the flag
     is informational until a run reads it (as `strength` is today); a reader function `lane_escalation(entry)` is the one
     place consumers read the flags. No ranking, proposal or default ever sets a flag. Consumers are Phase 37 (the runner
     call), 40 (lane switching) and 41 (the adapter's rounds 4 and 5); none reads it here.
   - Acceptance: tests cover a lane with no flag (false), both flags true, a non-boolean refused with the key named, no
     flag written by the wizard on a "no" or a skip, `lane_escalation` on a layered merge, and a test that fails when a
     writer, ranking or default path sets a flag.

6. **Proposal of a review set and a coding set; jev ranks, the owner picks (HUB-07)**.
   - Current: Step 2.2 builds a ranked list per runtime from `fetch-model-catalog` and asks for each candidate; the older
     wording says flagship for review, coding for execute by default.
   - Target: `ai-kit-spec.py propose-lanes --purpose review|execute` reads the Phase 35 catalog and prints a ranked
     shortlist for that purpose, read-only. Pool: entries whose usability is not `rejected`, that are not stale or
     unmatched, in the classes that fit the purpose (review: flagship; execute: coding and fast), with unknown tier or class
     kept and shown as unknown below the known ones. Order: with jev available, jev scores each candidate once for its fit to
     the purpose from labelled facts only (tier, class, cost band, strengths, effort levels; never configuration or keys)
     and the scores give the order; a low answer, an error or no jev
     gives the deterministic order of the existing purpose-weighted scorer plus cost for execute; each row names who
     ranked it. `router-env/<x>` aliases are listed apart as `assumed: router-env alias naming` (the purpose guessed by the
     existing name heuristic, labelled assumed). The owner picks from the list (the default view shows 5 per purpose,
     with "show more"); nothing is written before each of the two sets is confirmed; nothing is labelled review or execute in
     the catalog. The first wizard question is the preferred runtimes per purpose; the shortlist is limited to them.
   - Acceptance: tests with a fixture catalog cover a review pool and an execute pool, a rejected or stale entry out, an
     unknown-tier entry shown last as unknown, jev confident, low and absent (fake jev, the order's source named), an
     owner alias group, a runtime filter, and that no catalog value changes when a proposal runs.

7. **No runtime-table flag refuses a lane (owner directive 2026-11-16)**.
   - Current: see the live facts: `review_only` refuses in routing, `SUPPORTED_EXECUTE_CLIS`, `execute_cli_error`
     (`dispatch-execute`, `execute_dispatch.py`) and `execute_selection.py`; save-time validation names the table as the
     allowed set.
   - Target: no refusal cites a seed flag. The `review_only` field becomes advice text shown by the wizard and the
     preview, labelled with its source and unverified. Refusals left are facts with a named reason: the runner has no
     formula for the mode (route `no_formula`, replacing `review_only`, naming mode and runtime; Phase 37 removes it by
     teaching the runner), the binary is not installed, a model absent from a successful listing, a rejected probe. A
     runtime outside the table is stored only as a custom `command` lane, and the save error says exactly that instead of
     printing the table. On a Claude Code host, the aliases still run natively as before.
   - Acceptance: tests cover claude as an explicit execute lane on a non-Claude host (accepted by config and selection,
     route `no_formula` with its reason, not `review_only`), on a Claude host (native), `dispatch-execute` for it no longer
     exiting 2 on the flag, an unknown runtime without a command (the new message), grok as a custom command lane, and a
     grep-style test that no refusal path reads the `review_only` field.

8. **The hardcoded-referee test, one guard (HUB-07, HUB-09)**.
   - Current: only SKILL.md main flow is checked for `router-env/` and referee pointers (`tests/test_skill_text_history.py`);
     Phase 35 adds the position-based guard with a shrinking baseline.
   - Target: a rule in Phase 35's guard module (the same scanner, baseline file and non-vacuity convention, no second
     mechanism): outside tests, `.planning/`, `.aikit/` and the owner's own config files, an unmarked `router-env/<x>`
     literal in a skill, rail template, default or doc fails (a lane alias is the owner's config, so a shipped file may
     show one only as a marked example); in tests a `router-env/<x>` expected value stays allowed for pi and opencode. The
     baseline gains the files that violate today, each naming the phase that cleans it; this phase cleans every file it
     rewrites.
   - Acceptance: planted fixtures show an unmarked alias in a default failing, in a SKILL.md failing, a marked example
     passing, a test file using it for pi passing, a new violating file failing, and a cleaned file failing until its
     baseline entry is removed.

9. **No backup file after a verified migration (owner observation 2026-11-16, amends 33 D-12; needs confirmation)**.
   - Current: the old roster is renamed to `review-spec.toml.migrated` and stays.
   - Target: after the existing value check passes, the old file is deleted by default; `--keep-backup` (and the
     wizard's migration line saying so) keeps the `*.migrated` rename; a failed check deletes and renames nothing; the
     rename guard on a changed old file still applies.
   - Acceptance: tests cover a passing migration leaving no old file, `--keep-backup` leaving the rename, a failed value
     check leaving the old file untouched, and an old file changed during the run left in place with the existing error.

10. **spec-config in a context that cannot ask (owner observation 2026-11-16)**.
    - Current: a run from a subagent hit Step 2, which needs the user, and hand-edited files instead.
    - Target: when spec-config cannot ask (no structured-question tool and no plain conversation), it stops after detection
      and prints the pending decisions (installed runtimes, listing counts, the questions it would ask), writes nothing, and
      says that a person must run it; R2's "no way to ask" exit relies on this.
    - Acceptance: a doc-contract test pins the stop; an eval runs the skill with no way to ask and expects no write and the
      pending-decisions block.

11. **Skill text, docs and the judge bar (JDG-04)**: `ai-kit-spec-config`, `ai-kit-spec-review` and
    `ai-kit-spec-execute-superpowers` describe the new flow and meet the judge bar; READMEs and nested docs match.
    - Current: spec-config Steps 2.1 to 2.8 describe the mixed purpose flow and the replace-and-migrate backup wording; the
      other two skills have no chain.
    - Target: Step 1 and Steps 2.x follow R3, R4, R5, R6 and R10; the review skill's Step 0.7 and the adapter's first step
      hold R2's block; the migration line follows R9; READMEs and the config docs name the new commands (`config-status`,
      `propose-lanes`, `--keep-backup`); evals use the new shape.
    - Acceptance: the `skill-judge` loop for each of the three skills ends with no critical or high finding or a grade of B
      or better and no regression beyond variation (recorded in 36-VERIFICATION.md); doc-contract tests pin the new steps;
      `make test` passes.

12. **Free models are selectable, and a usage-limited lane has an alternative (owner directive 2026-11-16, re-run 2; HUB-05,
    HUB-07)**.
    - Current: nothing in the proposal marks a price source or lets the owner reach a zero-price model on purpose; no config
      key says a lane is usage-limited; no check asks for an alternative; no machine-readable source states a daily limit
      (see the live facts).
    - Target: (a) a proposal row shows `price: zero` with its source and date when the Phase 35 catalog holds a price of zero
      from the host's own listing (opencode `/api/model`) or models.dev (`input` and `output` both zero), never from the
      wording of a model id; after the ranked list each purpose shows a separate group `zero price` of up to 5 rows from the
      same pool, ordered by the same scores (jev or the deterministic scorer, one request, the same ranker label), so the
      owner can reach one without scrolling; local models share the band and are labelled `zero price (local or hosted not
      known)` unless the source says which; `router-env/<x>` aliases stay in their own group. (b) The owner picks a zero-price
      model like any candidate; for each chosen zero-price lane the wizard asks once whether it is usage-limited (daily or
      other cap): yes (with an optional one-line note) / no / not sure; only a yes writes `usage_limited = true` (a flat
      boolean on the lane in either role, written only when true) and the optional `usage_limit_note` (display text, never
      parsed, never sent to jev); no / not sure and a skipped question write nothing; no price, name or table ever sets the
      flag. The wizard asks only for zero-price lanes; any other lane carries the flag only when the file is edited by hand,
      and the validator accepts it on any lane. (c) The alternative: when a role holds a usage-limited lane and no lane without the flag,
      the wizard proposes the best-ranked unflagged candidate of that purpose and writes the role only after the owner adds
      one or says explicitly that there is none; the explicit none is written the same way and prints a visible warning on every
      preview; the reader prints the same warning for a hand-written file; nothing refuses. The wizard states the fallback
      rule in one line: a flagged lane's fallback is the first lane of the same role, in that role's order, that is not itself
      flagged. (d) `lane_usage_limit(entry)` (flag, note; a non-boolean flag is refused with the key named) and
      `lane_fallback(role_lanes, key)` (the first unflagged lane in the role's order, or none) are the one place consumers read
      the facts, beside `lane_escalation`; no run reads them in this phase (Phase 40 reads them to switch lane, 38.1's classes
      decide when). (e) The existing test call before saving runs for a free lane too; the wizard says in one line that the
      call spends part of its allowance. (f) With herdr available at runtime the runner may host that call or any lane in a
      pane (Phases 37 and 38 own it); the wizard's questions are always asked of the owner in the owner's session, never in a
      pane or by another agent, so the flow, the written file and every acceptance check are identical with and without herdr.
    - Acceptance: tests with a fixture catalog (invented placeholder ids; `router-env/<x>` only for the alias group) cover a
      zero-price entry from the host listing and one from models.dev showing their source, a zero-price entry whose id has no
      `free` wording shown in the group, an id with `free` wording and a nonzero price not shown in it, the group's size cap and
      its order from the same scores (jev confident, low and absent), the flag written only on a yes (no / not sure / skip write
      nothing, no inference from price or name), the optional note stored and never present in the jev item, a role with only
      flagged lanes (proposal, explicit none with the warning, reader warning for a hand-written file), `lane_usage_limit` on a
      layered merge and a non-boolean refused, `lane_fallback` order (first unflagged in the role's order, none), a byte-
      preserving write through the splicing writer, and that the same session with and without a herdr signal in the
      environment gives byte-identical output (fake herdr, no pane opened by the wizard).
    - *Amended 2026-11-16 (free-lane pool study, 36 D-20 to D-22; PROVISIONAL, needs owner confirmation):* (g) a yes also writes
      `usage_pool`, one line `<provider>/<tier>` (the provider prefix of the model id as the host lists it, and `free` as the
      tier); the wizard proposes it and the owner may edit it, and a hand-written flagged lane may omit it. (h) The fallback of (c)
      and (d) becomes the first lane of the same role, in the role's order, that is neither flagged nor in the same pool as the
      flagged lane (a lane with no `usage_pool` counts as a pool of its own, so only an equal string means the same pool);
      `lane_fallback` returns none when every remaining lane is flagged or shares the pool, and the alternative proposed in (c)
      skips candidates of the flagged pool. (i) The wizard states the rule in its one line and warns, when the owner picks or is
      offered a second lane of the same provider as the alternative, that other free models of that provider appear to share one
      pool and so are not an alternative (reported by users for opencode's free models, scope unresolved; unverified for any other
      provider). Evidence: `.planning/research/2026-11-16-opencode-free-models.md`. Acceptance additions: the pool string written
      with a yes and with nothing else, an edited string kept byte for byte, `lane_fallback` skipping an unflagged lane of the same
      pool and taking a lane of another pool, a missing `usage_pool` comparing as its own pool, the same-provider warning shown
      and the different-provider case silent, a non-string `usage_pool` refused with the key named, a byte-preserving write with
      the new key, and one shared fixture with Phase 38.1 R11 that the recorded string equals the runner's pool key for the same
      lane.

13. **A free model's data use is shown, recorded and confirmed before project content may go to it (owner directive 2026-11-16;
    HUB-10)**. *(added 2026-11-16, free-lane pool study; PROVISIONAL, needs owner confirmation: the decline path and the closed
    value list)*
    - Current: nothing tells the owner what a free model's vendor does with the prompts. The research note
      (`.planning/research/2026-11-16-opencode-free-models.md`, section 2, read 2026-11-16) reads the vendor's docs: most free models
      carry exceptions to the zero-retention rule (the prompt may be kept, used to improve the model, or sent to a trial endpoint
      that logs it), only four of the listed free models are zero-retention, and a review or execute lane sends repository diffs,
      plans and code to the vendor. No machine-readable field for it was found in the catalog (open question 5 of the note).
    - Target: (a) when the owner selects a zero-price model (the group of R12) whose source does not say it is local, the wizard
      shows its data-use note before asking anything else about the lane: one of `zero_retention`, `may_be_kept_or_trained` or
      `unknown`, with a one-line display text, its source and the date it was read, and a label `verified` (the vendor's own
      documentation page read by the wizard in this run, through Phase 35's optional web source) or `reported` (any other source,
      including the owner's own statement); no readable source gives `unknown`, shown as unknown and never defaulted to a safe
      value, and no shipped list of models or vendors decides it (a table is seed data and examples only). (b) The wizard states
      in one line that a review or execute lane sends project content (diffs, plans, code) to that vendor, and asks the owner to
      confirm sending it to this lane: yes writes `data_use` (the value), `data_use_source` (one line: label, source name and
      date; control characters removed, length capped, display only, never parsed) and `data_use_confirmed = true` beside the
      lane; no or a skipped question writes no lane (the owner picks another candidate), and `unknown` needs the same explicit
      yes. (c) The validator accepts the three keys on any lane, refuses a value outside the list or a non-boolean confirmation
      with the key named, and a hand-written lane without them is read as unconfirmed with a one-line notice (nothing refuses).
      (d) The facts are shown in the preview and `config-status` prints them; no data-use text is sent to jev.
    - Acceptance: fixtures with invented placeholder ids and a recorded vendor-page excerpt (read date in its header) cover a
      zero-retention page, an exception page, a page with no statement (shown `unknown`) and an unreachable source (shown
      `unknown`, never `zero_retention`); the note shown before the confirmation question; a yes writing the three keys and a no
      or skip writing no lane; a local source skipping the question; an out-of-list value and a non-boolean confirmation refused
      with the key named; a hand-written lane read as unconfirmed with the notice; a byte-preserving write; the label `verified`
      only for a page read in the run; and the item text sent to jev holding no data-use text.

## Boundaries

**In scope:**
- The config-status command and the chain (R1, R2), per-role orders (R3), effort per lane and its forms (R4), escalation
  flags and the reader (R5), the proposal command and the wizard flow (R6), removing the seed-flag refusals (R7), the
  referee rule in Phase 35's guard (R8), the migration backup default (R9), the headless stop (R10), skill text and docs
  (R11). *(amended 2026-11-16, re-run 2, D-15 to D-19: also free-model selection, the usage-limited flag, the alternative-lane
  rule and its reader (R12).)* *(amended 2026-11-16, free-lane pool study, D-20 to D-23: also the pool recorded with the flag and the
  different-pool fallback (R12 g to i) and the data-use note and confirmation (R13).)*

**Out of scope:**
- Making any run read the escalation flags (Phases 37, 40, 41); the runner's effort flags for claude and copilot, its
  closed effort sets, `unknown_runtime`, `no_inventory`, `exec: null`, and the `modelId` gate (Phase 37, with Phase 38.1
  for classes).
- The execute adapter's resume path, owner stop path, session-model fallback and brief changes (Phase 41), jev choosing the
  executor (Phase 42).
- The catalog itself (Phase 35) and cleaning baseline files this phase does not rewrite.
- Prompt-size refusal and capability blocks (Phase 39), resilient review (Phase 40).
- *Added 2026-11-16 (re-run 2):* making any run read `usage_limited` or switch to the fallback lane, how a host's quota
  message from a free lane is classified, and what a quota stop on a flagged lane waits for (Phases 38.1 and 40); the
  runner's hosting of a lane or call in a herdr pane, the pane's result channel, and ownership, cleanup, naming and the
  lock of what the runner opens (Phases 37 and 38); a shipped list of known free or limited models (never: a table does not
  decide, D-15); the catalog's own price fields (Phase 35).

## Constraints

- Runtime code stays stdlib-only; new subcommands go through `ai-kit-spec.py` and its factory pattern.
- Every config write is atomic through the splicing writer; byte-preserving; the writer rejects what the validator rejects.
- jev is used only when present at runtime (probed); every path has a tested no-jev behavior; jev sees labelled summaries
  only, never configuration values, keys or paths.
- Tests run in a scratch HOME with `AI_KIT_REFUSE_REAL_HOME=1`, read no `.planning/` path and no real host config; fake
  hosts only.
- English only; no machine-specific absolute path and no provider or model name other than `router-env/<x>` in code,
  defaults, rails, skills, docs or tests (tests for pi and opencode only).
- A SKILL.md describes behaviour; provenance and version history live in a trailing section.

## Acceptance Criteria

- [ ] `config-status` prints `active`, `pending` or `none` per the fixtures and writes nothing (R1).
- [ ] The review skill and the adapter chain spec-config on `none`, fail naming the fix when it is missing, and never touch
      config under `--no-cross-ai` (R2).
- [ ] The written file holds a separate order per role and only the chosen lanes; a legacy shared order splits by role (R3).
- [ ] An effort is offered from known levels or a probe, passed in the runtime's form, and ignored-with-reason where the
      runner has no path; none is dropped silently (R4).
- [ ] Escalation flags exist, default false, are written only on an explicit yes, and no path turns one on (R5).
- [ ] `propose-lanes` ranks per purpose with the ranker's source named, lists owner aliases apart, and writes nothing (R6).
- [ ] No refusal path reads `review_only`; refusals name a fact (R7).
- [ ] The referee rule fails an unmarked alias in a skill, rail, default or doc, through Phase 35's guard (R8).
- [ ] A verified migration leaves no backup unless `--keep-backup` (R9).
- [ ] spec-config without a way to ask prints pending decisions and writes nothing (R10).
- [ ] The three skills meet the judge bar; docs updated; `make test` passes (R11).
- [ ] *(added 2026-11-16, re-run 2)* A zero-price model is reachable in its own group with its price source, the owner's
      yes writes `usage_limited` and nothing else does, a role holding only flagged lanes proposes an alternative or prints an
      explicit-none warning, and the wizard's output is identical with and without herdr (R12).
- [ ] *(added 2026-11-16, free-lane pool study, PROVISIONAL)* A yes records the lane's pool, the fallback is a lane of a different
      pool, and the wizard warns that other free models of the same provider share the pool (R12 g to i).
- [ ] *(added 2026-11-16, free-lane pool study, PROVISIONAL)* A selected free model's data-use note is shown with its source, read
      date and label (unknown shown as unknown), recorded beside the lane only with the owner's explicit confirmation to send
      project content to it, and a no writes no lane (R13).

## Edge Coverage

**Coverage:** 46/46 applicable edges resolved · 0 unresolved (46 engine rows from `edge_floor.py floor`; 7 added for R12 on 2026-11-16, re-run 2; 7 more for R13 on 2026-11-16, 53 engine rows in all)

| Category | Requirement | Status | Resolution / Reason |
|----------|-------------|--------|---------------------|
| adjacency | R1 | ✅ covered | Both layers active: one `active` state listing both paths, project first |
| empty | R1 | ✅ covered | An empty `[lanes]` table or empty arrays is `none`; the file's path is named |
| ordering | R1 | ✅ covered | Checked paths are printed in a fixed order: project, then user |
| concurrency | R1 | ✅ covered | Read-only, no lock; a file replaced mid-read gives the old or the new state (writes are atomic) |
| empty | R2 | ✅ covered | An empty or unrecognised answer to the ask means `stop`; there is no default yes |
| encoding | R2 | 🧪 backstop | Answers are numbered options, never free text; the notice is ASCII |
| adjacency | R3 | ✅ covered | A key under both roles stays two entries; each role's order names its own lanes |
| empty | R3 | ✅ covered | A role with no lane gets no order table, and an old one is removed on write |
| encoding | R3 | 🧪 backstop | Order entries are existing lane keys compared as exact strings (the writer's key rules) |
| ordering | R3 | ✅ covered | Order is the written list order; a duplicate key keeps its first place |
| concurrency | R3 | 🧪 backstop | Atomic publish through the splicing writer; the last writer wins |
| adjacency | R4 | ✅ covered | The first and last level of a model's list are accepted, one outside is refused; levels match as whole tokens (`high` is not `xhigh`) |
| empty | R4 | ✅ covered | No effort: nothing passed and nothing printed; an empty string is a named error |
| encoding | R4 | ✅ covered | Levels are ASCII lowercase; a host error line has control characters removed and key shapes redacted before it is stored |
| ordering | R4 | 🧪 backstop | Levels are shown in the host's own order; nothing depends on a sort |
| adjacency | R5 | ✅ covered | A role with one lane has no target: the wizard does not ask and `lane_escalation` reports no target |
| empty | R5 | ✅ covered | No flag key means both false; a false value is never written |
| ordering | R5 | ✅ covered | Targets follow the role's declared order; two lanes of one runtime step in that order |
| adjacency | R6 | ✅ covered | One model on two runtimes is two rows, one per runtime; equal scores tie-break by id for display only |
| empty | R6 | ✅ covered | An empty pool prints "no candidates for this purpose" and the owner may name a model; an empty catalog stops and names the catalog step |
| encoding | R6 | 🧪 backstop | Names are shown as stored; jev gets labelled facts and ids that pass the model-id pattern |
| ordering | R6 | ✅ covered | The deterministic scorer is stable; ties break by id; each row names who ranked it |
| concurrency | R6 | 🧪 backstop | The proposal is read-only |
| adjacency | R7 | ✅ covered | A runtime outside the table with a `command` is custom, never unknown; ids compare exactly |
| empty | R7 | ✅ covered | A runtime with no model keeps its `no_model` route (a fact about the entry) |
| encoding | R7 | 🧪 backstop | Runtime ids are exact, case-sensitive matches, as today |
| ordering | R7 | 🧪 backstop | The route decision order in `routing.py` is kept; `no_formula` takes `review_only`'s place |
| idempotency | R7 | ✅ covered | Validation and routing are pure; a second run gives the same route and message |
| concurrency | R7 | 🧪 backstop | Pure functions with no shared state |
| adjacency | R8 | ✅ covered | A marked example covers only its own region; a literal beside it still fails |
| empty | R8 | ✅ covered | An empty baseline passes when nothing violates |
| ordering | R8 | ✅ covered | The baseline stays sorted and duplicate-free (Phase 35's rule) |
| concurrency | R8 | 🧪 backstop | The scan is read-only |
| concurrency | R9 | ✅ covered | The old file is deleted only while its bytes equal the snapshot taken at read; a change during the run leaves it in place |
| concurrency | R10 | 🧪 backstop | It writes nothing, so parallel runs cannot conflict |
| adjacency | R11 | 🧪 backstop | Plain Markdown and test text |
| empty | R11 | ✅ covered | A skill with no evals fails the judge bar |
| encoding | R11 | 🧪 backstop | Plain Markdown |
| ordering | R11 | 🧪 backstop | Step order is pinned by the doc-contract tests |
| boundary | R12 | ✅ covered | The zero-price group holds at most 5 rows; a sixth reaches the owner only through "show more"; a price counts as zero only when `input` and `output` are both zero (one zero and one positive is not zero price) *(added 2026-11-16, re-run 2, D-18)* |
| adjacency | R12 | ✅ covered | One model offered by a free provider and a paid one is two rows with their own price; the flag belongs to one lane and a free and a paid lane of the same model never share it *(added 2026-11-16, re-run 2, D-16)* |
| empty | R12 | ✅ covered | No zero-price entry: the group is not printed; a missing price is unknown, never zero; no note means no `usage_limit_note` key; not sure and skip write nothing *(added 2026-11-16, re-run 2, D-15)* |
| encoding | R12 | ✅ covered | The note is one line, control characters removed, length capped, stored as typed, never parsed and never sent to jev; the flag is a TOML boolean compared exactly *(added 2026-11-16, re-run 2, D-16)* |
| ordering | R12 | ✅ covered | The group follows the ranking order, ties by id for display only; `lane_fallback` follows the role's written order and a duplicate key keeps its first place *(added 2026-11-16, re-run 2, D-16, D-18)* |
| precision | R12 | ✅ covered | Zero is exact: any positive figure, however small, is not zero price; the source's figure is shown as stored with no rounding *(added 2026-11-16, re-run 2, D-18)* |
| concurrency | R12 | 🧪 backstop | The proposal is read-only; the write is atomic through the splicing writer and the last writer wins; a pane the runner hosts is outside this phase *(added 2026-11-16, re-run 2, D-16, D-19)* |
| adjacency | R13 | ✅ covered | One model offered by a vendor page that lists it twice (a free and a contributor form) shows the stricter of the two statements; a lane flagged usage-limited and a lane confirmed for data use are independent keys *(added 2026-11-16, D-23)* |
| boundary | R13 | ✅ covered | A page that states zero retention for some models and an exception for others is read per model; a model the page does not name is `unknown`, not the page's general rule *(added 2026-11-16, D-23)* |
| concurrency | R13 | 🧪 backstop | The note is read once per run and the write is atomic through the splicing writer with the last writer winning *(added 2026-11-16, D-23)* |
| empty | R13 | ✅ covered | No source, an empty page or an unreachable one gives `unknown`; no source line means no `data_use_source` key; a skipped question writes no lane *(added 2026-11-16, D-23)* |
| encoding | R13 | ✅ covered | The source line is one line with control characters removed and a capped length; the three values are compared exactly and the confirmation is a TOML boolean *(added 2026-11-16, D-23)* |
| ordering | R13 | ✅ covered | The note is shown before the confirmation question and before the usage-limited question of R12, so the owner sees the data use first *(added 2026-11-16, D-23)* |
| precision | R13 | ✅ covered | The read date is a calendar date, and a note older than the run's own read is never shown as verified *(added 2026-11-16, D-23)* |

## Prohibitions (must-NOT)

**Coverage:** 11/11 applicable prohibitions resolved · 0 unresolved *(amended 2026-11-16, re-run 2: 3 rows added for R12; amended 2026-11-16, free-lane pool study: 2 more rows, 13/13; 2 more rows for R13, 15/15)*

| Prohibition (must-NOT statement) | Requirement | Status | Verification / Reason |
|----------------------------------|-------------|--------|------------------------|
| MUST NOT chain, migrate or read config under `--no-cross-ai`, and MUST NOT let `config-status` write or migrate anything | R1, R2 | resolved | verification: test — the flag case and the scratch-HOME no-write check |
| MUST NOT turn an escalation flag on from a ranking, a proposal, a default or a skipped question | R5, R6 | resolved | verification: test — the writer, ranking and default paths never set a flag |
| MUST NOT drop a set effort without a printed reason, and MUST NOT pass an effort a listed model does not take | R4 | resolved | verification: test — the ignored-with-reason lines and the refused level |
| MUST NOT let jev's ranking stand as the owner's pick, write a lane before the owner confirms each set, or label a catalog entry review or execute | R6 | resolved | verification: test — the catalog is unchanged by a proposal and nothing is written before confirmation |
| MUST NOT send configuration values, keys or paths to jev | R6 | resolved | verification: test — the item text holds labelled facts only |
| MUST NOT refuse a lane from a seed flag alone | R7 | resolved | verification: test — the route tests and the no-reader check on `review_only` |
| MUST NOT delete the old roster before the value check passes | R9 | resolved | verification: test — the failed-check and changed-file cases |
| MUST NOT write the real user config or call a real host or network in tests | R1-R10 | resolved | verification: test — the module tripwire and `AI_KIT_REFUSE_REAL_HOME` |
| MUST NOT set `usage_limited` from a price, a model id's wording, a shipped list or a skipped, "no" or "not sure" answer, and MUST NOT send the note to jev | R12 | resolved | verification: test — the writer writes the flag only on a yes; the jev item text is checked for the note *(added 2026-11-16, re-run 2)* |
| MUST NOT refuse or reorder a role because its only lanes are usage-limited, and MUST NOT make a run switch lane from the flag in this phase | R12 | resolved | verification: test — the explicit-none write succeeds with its warning; no run path reads `lane_usage_limit` *(added 2026-11-16, re-run 2)* |
| MUST NOT ask the owner's wizard questions in a herdr pane or of another agent, and MUST NOT make the written file or the questions differ with herdr present | R12 | resolved | verification: test — the same session with and without a fake herdr signal gives identical output and opens no pane *(added 2026-11-16, re-run 2)* |
| MUST NOT return a lane of the flagged lane's own pool as its fallback, and MUST NOT write `usage_pool` without a yes or infer it from a price or a name beyond the proposed provider prefix the owner can edit | R12 | resolved | verification: test — `lane_fallback` and writer cases with a same-pool unflagged lane and with no, not-sure and skipped answers *(added 2026-11-16, free-lane pool study)* |
| MUST NOT present the shared-pool warning as verified for any provider: it is reported for opencode's free models and unverified elsewhere | R12 | resolved | verification: test — the warning text carries its label and the wizard prints no warning for a different provider *(added 2026-11-16, free-lane pool study)* |
| MUST NOT default an unknown data use to a safe value, label a note `verified` unless the vendor page was read in this run, decide it from a shipped list, or send data-use text to jev *(added 2026-11-16)* | R13 | resolved | verification: test — the unreachable-source and no-statement fixtures give `unknown`, the label check, and the jev item text *(added 2026-11-16, D-23)* |
| MUST NOT write `data_use_confirmed = true` without the owner's explicit yes, and MUST NOT write a free lane the owner declined or skipped *(added 2026-11-16)* | R13 | resolved | verification: test — the writer cases for yes, no, skip and unknown *(added 2026-11-16, D-23)* |

## Ambiguity Report

| Dimension          | Score | Min  | Status | Notes |
|--------------------|-------|------|--------|-------|
| Goal Clarity       | 0.88  | 0.75 | ✓      | Roadmap goal, three requirements, owner observations and directives |
| Boundary Clarity   | 0.84  | 0.70 | ✓      | Runner, adapter and consumers fenced to Phases 37, 40, 41 |
| Constraint Clarity | 0.82  | 0.65 | ✓      | stdlib-only, jev optional, byte-preserving writes, guard reuse |
| Acceptance Criteria| 0.82  | 0.70 | ✓      | Eleven checks tied to tests, evals or records |
| **Ambiguity**      | 0.15  | ≤0.20| ✓      | 1 − (0.35×0.88 + 0.25×0.84 + 0.20×0.82 + 0.20×0.82) |

## Interview Log

Interactive path, one round in the phase subagent; no owner question was unclear enough to relay (the owner answers only
unclear gray areas, 2026-11-16 run mode). The open items went through jev (one advisory answer per item; a low answer is
decided by own reasoning). Summaries only, advisory. Rule: `mvp-mode` inactive, so the best design wins over the smallest
diff.

| Round | Perspective | Question summary | jev (advisory) | Decision locked |
|-------|-------------|------------------|----------------|-----------------|
| 1 | Researcher | How does each host take an effort, and where is support known per model? | none; live `--help` and the runtimes snapshot | Facts in Background; support is per-model known for pi and codex only (R4) |
| 1 | Failure Analyst | Which fact means "no config"? | laya no_file low 0.41; typesafe no_roster_either_layer low 0.55 | **Own reasoning:** no lane in either layer and no old roster; `pending` goes to trust and migration (R1, ledger) |
| 1 | Simplifier | What does a skill do on no config? | ask_then_chain, choice 0.87 | Ask once, then chain; no way to ask: notice and session default (R2) |
| 1 | Boundary Keeper | Where is the adapter's entry check wired? | all_now, choice 0.77 | Review skill and adapter now; the router is unchanged; Phase 41 keeps the block (R2, amendment to EXE-01) |
| 1 | Simplifier | Where do per-role orders live? | laya array_order 0.71, contradicted by the layer-merge evidence; second request with the merge fact: policy_subtables, typesafe low 0.71 | **jev overridden** (first answer); **Own reasoning:** `[lanes.policy.review]` and `[lanes.policy.execute]` (R3, ledger) |
| 1 | Failure Analyst | An effort whose support is unknown? | refuse, typesafe 0.82 (laya pass_flagged low 0.40); asked again with the probe fact stated: probe_then_decide, typesafe 0.93 | **jev overridden** (first answer contradicts the owner directive that unknowns are learned live): one probe call with the effort (R4) |
| 1 | Boundary Keeper | What happens to the `review_only` refusals? | remove_refusal, typesafe 0.86 (laya keep_refusal low 0.41) | No refusal reads the flag; a missing runner formula refuses with its own reason (R7) |
| 1 | Boundary Keeper | Which lanes may an escalation flag step to? | configured_lanes_same_role, typesafe 0.84 | Configured lanes of the same role, in order (R5) |
| 1 | Failure Analyst | Default after a verified migration? | laya keep_renamed low 0.43; typesafe delete_after_verify low 0.68 | **Own reasoning:** delete by default, `--keep-backup` keeps it; follows the owner's words, needs confirmation (R9, ledger) |
| 1 | Simplifier | What does the referee test add to the Phase 35 guard? | none | A rule in the same guard: an unmarked `router-env/<x>` in a skill, rail, default or doc fails (R8) |
| 1 | Researcher | What do the owner's 2026-11-16 items 2 to 5 and the headless note add? | none | Short choice per purpose (R6), separate orders and only chosen lanes (R3), no backup (R9), headless stop (R10) |

*Added 2026-11-16, re-run 2 (herdr hosting and free models; interactive path, one round in the phase subagent; no owner
question unclear enough to relay; typesafe answered, laya gave no answer in this run; summaries only, advisory).*

| Round | Perspective | Question summary | jev (advisory) | Decision locked |
|-------|-------------|------------------|----------------|-----------------|
| 2 | Researcher | How does a free model show in the hosts and the catalog, and does anything state a daily limit? | none; live `opencode models`, `/api/model`, models.dev, the other hosts' listings | Facts in Background: zero price only, no limit field anywhere; only the owner can say a lane is usage-limited (R12) |
| 2 | Failure Analyst | Where does "usage-limited" come from? | owner_declares, choice 0.88 | The owner states it; a zero price only triggers the question (R12 b, D-15) |
| 2 | Boundary Keeper | How is it recorded so a run can fall back? | flat_flag_plus_order, choice 0.95 | Flat boolean plus display note on the lane; fallback is the first unflagged lane in the role's order (R12 b, d, D-16) |
| 2 | Failure Analyst | What if a role holds only flagged lanes? | ask_then_allow_explicit_none, typesafe low 0.67 | **Own reasoning:** propose an alternative; an explicit none is allowed and warned, never refused (R12 c, D-17) |
| 2 | Simplifier | How do free models reach the owner in the shortlist? | plain_ranking_only, typesafe 0.89; asked again with the owner's wish stated: own_group_same_ranking, typesafe low 0.62 | **jev overridden** (first answer contradicts the directive that the owner can select free models): a separate group from the same ranking; **Own reasoning** (R12 a, D-18) |
| 2 | Boundary Keeper | Does the config need a herdr hosting key? | no_key_runner_decides, choice 0.94 | No key; the runner decides at run time; the wizard's questions stay with the owner (R12 f, D-19) |
| 3 | Failure Analyst | May project content go to a free model whose vendor keeps or trains on prompts? *(added 2026-11-16, free-lane pool study)* | classified by the orchestrator through jev (not re-run in this pass) | **Owner directive 2026-11-16, PROVISIONAL:** show the data-use note with source and label, record it beside the lane and ask the owner to confirm; unknown stays unknown; a no writes no lane (R13, D-23) |
| 3 | Failure Analyst | Is another free model of the same provider a fallback for a usage-limit stop? *(added 2026-11-16, free-lane pool study)* | none | **Owner directive 2026-11-16, PROVISIONAL:** no; the fallback must come from a different pool, the pool is recorded with the flag and the wizard warns about the shared pool (R12 g to i, D-20 to D-22) |

---

*Phase: 36-spec-config-as-the-hub*
*Spec created: 2026-11-16*
