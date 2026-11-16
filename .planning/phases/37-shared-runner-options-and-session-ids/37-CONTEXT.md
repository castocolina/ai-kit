# Phase 37: Shared runner options and session ids - Context

**Gathered:** 2026-11-16 (interactive path, no owner question needed, jev screening, after 37-SPEC.md); updated 2026-11-16 (re-run 2, herdr hosting, interactive path, jev screening, after the 37-SPEC.md R12 amendment)
**Status:** Ready for planning (after Phase 36 lands: this phase reads its per-lane `effort`, `lane_escalation` and `no_formula` route, and deletes the transitional Python pieces it left)

<domain>
## Phase Boundary

The runner is the one place that knows how each external CLI takes a model, an effort, a context label, a session id and
a permission mode. A call names those settings with plain flags (a GSD hook string can carry them), the runner applies
what it has a form for, prints every other setting as ignored or unknown with a reason from a closed list, and prints the
session id it used so a later round resumes it. No seed table refuses a lane: an unknown runtime runs from a declared argv
file, an unusual model id passes with an advisory, any effort token goes to the host, and the Python layer reads the
runner's own `--describe` instead of mirroring its tables. A unit test renders the template and compares it with the copy.
</domain>

<spec_lock>
## Requirements (locked via SPEC.md)

**11 requirements are locked.** See `37-SPEC.md` for full requirements, boundaries, and acceptance criteria.

Downstream agents MUST read `37-SPEC.md` before planning or implementing. Requirements are not duplicated here.

**Refined 2026-11-16 (re-run 2, D-22 to D-29):** 12 requirements are locked; R12 (optional herdr hosting of a lane, RUN-12) is the
new one, in scope for this phase's runner. Out of scope beside the earlier list: an interactive agent TUI, a TUI app, an e2e run and
pane reuse across calls (Phase 42 and calling skills), the run lock and the sweep of leftover tabs (Phase 38).

**In scope:** the call vocabulary (R1); the settings report (R2); effort forms in the runner (R3); unknown runtimes and the
argv file (R4); the model id floor (R5); claude's execute formula (R6); session ids (R7); the sync test (R8); `--describe`
and removing the Python mirrors (R9); escalation flags carried (R10); skill text, docs, the runner example cleanup and the
judge bar (R11).

**Out of scope:** idle watchdog, run lock, tree baseline, plan-versus-commits, the Phase 25 cleanup and the self-test move
(38); error classes and retry policy (38.1); capability blocks and prompt-size refusal (39); lane switching, resilient review
and routing custom lanes through the runner (40); the adapter's resume and stop paths and its use of session ids (41); jev
choosing effort by task (42).
</spec_lock>

<decisions>
## Implementation Decisions

### The call and the forms (SPEC R1, R3, R10)

- **D-01: The runner owns every effort form; Python only passes the flag.** The runner composes claude `--effort`, copilot
  `--reasoning-effort`, codex `-c model_reasoning_effort=`, pi `--thinking`, cursor `[effort=..]` (merged into the id's own
  bracket) and opencode `#variant` from one `--effort`. Two facts decide it: a GSD hook string is word-split with no shell
  and a cursor bracket is a glob class there, and a hook has no Python layer at all, so a Python-only form cannot serve GSD
  cross-AI. The previews (`build-model-id`, Phase 36's wizard preview, `build-command`) read the runner's `--print-argv`.
  `build_reviewer_model_id` and `build_cursor_agent_model_id` are deleted with their tests once the subcommand reads the
  runner. **Amends 36 D-05** (its Python forms are transitional: Phase 36 executes first and needs them for its probe call,
  this phase removes them; the amendment is made in 36-CONTEXT). **Own reasoning** (jev low both rungs: laya
  runner_owns_forms 0.38, typesafe runner_owns_forms 0.60). Ledger. **Needs owner awareness** (a cross-phase amendment).
- **D-02: `--role` is the documented name, `--mode` stays an alias.** Values `review` and `execute` map to `review` and
  `exec`; a disagreement is a usage error. Old hook strings and rendered copies keep working. **Own reasoning** (jev low:
  laya keep_mode_only 0.44, typesafe role_flag_mode_alias 0.76). Ledger.
- **D-04: No provider flag.** The provider is the id prefix of pi and opencode ids and shows as the `provider` setting
  (`applied`, from the id); codex, cursor, claude and copilot ids carry none, so it is `unknown` with `no_provider_form`.
  **Own reasoning** (jev low: laya provider_flag 0.63, typesafe derive_and_report 0.57). Ledger.
- **D-07: A level is a token, not a member of a set.** Shape `^[a-z][a-z0-9_-]{0,15}$`; `CODEX_EFFORTS` and `PI_THINKING` go.
  A host that rejects a level fails the call by the existing classification (an unclassified rejection is a `crash` with the
  host's first line, redacted). The levels offered to the owner are Phase 35's catalog and Phase 36's wizard's job.
  `CONFIG.effort.<runtime>` (the plan-baked default, today pi and codex only) works for every runtime and sits beneath the
  call. **Own reasoning** (jev low: laya catalog_check 0.67, typesafe shape_only 0.58): a catalog read would put the catalog
  into a standalone rendered script. Ledger.
- **D-08: Escalation flags are carried, reported `recorded_only` and echoed as `escalate=`; the runner never acts on them.**
  jev carry_and_report choice 0.98. Phase 40 reads them for lane switching.
- **D-15: `--context <label>`** (`^[a-z0-9][a-z0-9._-]{0,15}$`, for example `1m`) is a named setting, applied only where a form
  exists: cursor's bracket `context=` key (cursor's own help example). Every other runtime reports `ignored` with `no_form`
  (claude's `[1m]` model suffix and codex's window key are unverified forms: `unverified_form`, not fed). The window check of
  Phase 39 is a prompt-size check, a different thing.

### The report and the status line (SPEC R2)

- **D-11: Rows carry data; one pure planner builds argv and the report.** Each `RUNTIMES` row gains fields for its effort form,
  its session style (`chosen` or `minted`), its resume formula and a `source` label (verified with date and the help line, or
  unverified); a pure `planSettings(row, role, call)` returns the argv additions and the `{name, value, state, reason}` list.
  `main`, `--print-argv` and `--describe` all read it, and the formulas stay as they are. Python never mirrors a field.
  **Own reasoning** (jev low: laya branches_in_main 0.39, typesafe row_fields_one_planner 0.78). Ledger.
- **D-12: The status line gets one new group, after `attempts= cycles=` and before `retry_after_s=`.** The group is
  `session=<id|-> applied=<list|-> ignored=<list|-> unknown=<list|-> escalate=<list|->`. Callers read by key, so nothing that
  parses today moves; the self-test's `STATUS_HEAD_RE`, the two sample lines in `skills/ai-kit-cross-ai/SKILL.md` and
  `launch-and-wait.md` (lines taken from real self-test output), and any doc-contract test that compares them are refreshed.
  The one-last-line rule is unchanged. **Own reasoning** (jev low: laya append_last 0.48, typesafe group_after_cycles 0.56):
  the group is always present like `attempts` and `cycles`, while `retry_after_s` and `upstream` are conditional tails. Ledger.
- **D-14: The setting reasons are a closed list owned by the runner.** `no_form`, `id_carries`, `unverified_form`,
  `mode_forbids`, `no_slot`, `recorded_only`, `no_provider_form`; `--describe` prints the list, and one locking test compares
  the runner source, `--describe` and the SKILL.md table. States: `applied`, `ignored`, `unknown`. **Own reasoning** (GSD's
  closed-list-with-lock idea, adopted by the owner's directive). The setting lines go to stderr before the spawn, redacted
  with the runner's existing `redactSecrets`.
  - **Refined 2026-11-16 (re-run 2, D-28):** the list gains `no_herdr` and `host_failed`, and the names gain `host`. The same one
    locking test covers them (the stack's other additions to this list, such as Phase 38.1's `bad_value`, are counted by that test too).

### Gates become facts (SPEC R4, R5, R6, R9)

- **D-05: An unknown runtime runs from `--argv-file`; without one it gets a named refusal.** The file is a JSON array of argv
  strings with `{model}`, `{effort}` and `{session}` as the only placeholders and the prompt on stdin (a prompt on argv shows
  in the process table; the Python launcher's `{prompt}` template cannot move here). It is read once at start, strict UTF-8,
  size-capped, path inside the cwd tree. The runner never reads a lane's command from `config.toml`: the caller (a skill, a
  rendered hook) writes the file, and `config-trust/` stays the Python launcher's gate. The Python custom launcher
  (`run_custom_command`) is unchanged; routing custom lanes through the runner, so they get the status line and tree check, is a
  Phase 40 handoff. **jev overridden** (both low answers, refuse_always 0.43 and 0.72) because the owner directive says a runtime
  missing from the table and a custom command lane can still serve review or execute. **Own reasoning.** Ledger. **Needs owner
  awareness** (a new command-running surface in the runner; same trust as a GSD hook string, which is also an arbitrary command).
- **D-06: One universal model id floor; per-runtime shapes advise.** The floor is non-empty, no leading dash, no whitespace,
  no control or shell character (the existing ASCII charset, which already holds for every row). The advisory line names the
  seed shape and its source label. A successful live listing that lacks the id still ends `bad_model`. jev floor_plus_advisory
  choice 0.95 (laya drop_all low 0.69). Python's `_MODEL_ID_SRC` and `model_id_ok` are deleted; `project_runner_command` keeps
  `HOOK_TOKEN_RE` only (hook-string safety, a different concern).
- **D-09: claude gets an execute and a resume formula now, labeled unverified.** Full permissions like every other execute
  runtime; the permission flag (`--permission-mode bypassPermissions` or `--dangerously-skip-permissions`) is picked by the
  planning spike below. The review formula stays byte-equal. The runner prints the unverified note on each execute call and the
  row keeps `errorsUnverified` until the probe record exists. jev add_formula_unverified_label choice 0.89 (typesafe; laya low
  0.51 agrees). **Needs owner awareness** (a claude subprocess then runs unsandboxed, as the others do).
- **D-10: `--describe` is the one source Python reads, keyed by the template's content hash.** It prints rows (sorted by runtime
  id) with formulas present (exec, review, resume), listing command, session style, effort form, each with its source label, plus
  the reason list. Runtime detection runs it once and stores it in the runtimes snapshot with the template's sha256; the fact is
  refreshed when the hash differs as well as with the snapshot's age (a reinstall changes formulas within the 30-day age).
  Routing stays a pure function reading the stored fact; an absent or stale fact never refuses (the runner refuses at run time
  with its own named reason). `exec_formula`, its drift test, `unknown_runtime`, `no_inventory` (becomes `unverified`) and the
  `SUPPORTED_EXECUTE_CLIS` seed derivation go. jev key_by_template_hash choice 0.99 (laya age_only low 0.60).

### Sessions (SPEC R7)

- **D-03: One `--session-id`; the row says how its host takes ids.** `chosen` rows (pi, copilot: one create-or-continue flag per
  their own help) use the caller's id or a generated UUID; `minted` rows (cursor, codex, claude, and opencode) print the id the
  host created and continue it with the row's resume formula. A rejected id is a failed call with the host's first line, never a
  silent fresh session; a role that has no resume form (codex review and sandboxed codex execute) starts fresh, prints the new
  id and reports `ignored mode_forbids`. An explicit id beats the quota record's `last_sid`. Reviewers start fresh unless a
  skill passes an id; executors opt in; the adoption is Phases 40 and 41. **Own reasoning** (jev low: laya resume_only_printed
  0.42, typesafe one_flag_row_decides 0.79). Ledger. opencode is `minted` until a live probe shows arbitrary ids are accepted
  (jev minted_until_probe choice 0.96; its help says create-if-missing but the id shape is unverified).
  - **Refined 2026-11-16 (re-run 2, live):** a headless `opencode run -s ses_<16 letters or digits>` accepted a caller-chosen id and the TUI
    attached to that session; other id shapes are unverified. The row stays `minted` until the planning spike (D-17) records the shape rule
    and the label, so no behavior changes; the spike now has the cheaper question "which id shapes does the host accept".
- **D-17: A spike comes first, at execute start.** Theory (the hosts' help) says `--session-id` and `--resume` continue a session;
  the spike proves it with one cheap call per primary host (claude, opencode, pi; codex, cursor and copilot stay fake-only and
  labeled unverified, because claude, opencode and pi are the primary hosts since 2026-10-18) in a scratch repository, and picks claude's permission flag. Findings go to
  `tmp/` and into the rows' source labels. herdr may drive a host for it where `HERDR_ENV=1` and the CLI exist; the fake-CLI
  tests do not depend on it. **Own reasoning.** Ledger.

### Tests, sync, docs (SPEC R8, R11)

- **D-13: Tests are split by cost.** Argv and describe checks are table-driven Python unit tests through `--print-argv` and
  `--describe`; spawn-level behavior (settings lines, two-call resume, the argv-file lane, the claude fake, `escalate=`) are new
  built-in self-test cases using the existing fakes, whose shard times are re-recorded (`tests/cross_ai_selftest.py
  --record-times`); the sync test is Python. jev split_by_cost choice 0.93 (laya all_selftest low 0.36).
- **D-18: The sync test renders through `ensure_runner` into a scratch project.** It asserts `pristine`, equal version, equal
  bytes outside the config block, then equal `--print-argv` output for a matrix (each runtime and role, plus effort, session and
  argv-file cases) from the template and the copy, plus a one-byte mutation that must fail. `tools/check_dogfood.py` stays the
  live-copy check; it is the only reader of `.planning/`. The live `.planning/scripts/cross-ai.mjs` is re-rendered by the
  installer after the template changes (a plan task, then `make check-dogfood`).
- **D-19: Runner-file hardcoding cleanup is limited to the code this phase rewrites.** The `RUNTIMES` rows, `parseArgs`, `main`,
  the classifier region outside the self-test: example names carry the `model-example:` marker or become placeholders, decision
  lists go (D-06, D-07). The self-test harness and its entries stay in Phase 38's baseline. `llama`/`qwen3` in the id-grammar
  comments are reworded.
- **D-16: Skills and docs.** `ai-kit-cross-ai/SKILL.md` is the one SKILL.md that changes and meets the judge bar here (new section
  for the vocabulary, the report and sessions; evals in the new shape; a trailing provenance section). `cross-ai-dispatch.md`,
  curated-config `runner.md`, `docs/` and the READMEs follow. **Own reasoning.** If another SKILL.md changes during execution it
  joins the judge loop.
- **D-20: jev and herdr are conditional ~~and never in the runner~~ *(superseded 2026-11-16, D-22: jev is never in the runner; herdr is in the runner only as one optional hosting transport)*.** The runner is stdlib Node rendered into projects and calls
  ~~neither~~ *(superseded 2026-11-16, D-22: never jev, and herdr only through the transport of R12)*. Callers: jev may size or classify (Phase 42 owns effort by task); herdr may watch a long lane or drive a host for
  UAT, but a Python-dispatched lane stays supervised by `runner_dispatch` (its process-group backstop would not cover a pane's
  process). Each has a tested absent behavior; the fake-CLI path is the default.
  - **Refined 2026-11-16 (re-run 2, D-22):** the process-group worry is real and is met inside the transport: a hosted lane has no
    process group of the runner, so the runner closes its own tab by id (which ended the child live) and records the id for Phase 38's
    sweep. A caller that drives herdr by hand for UAT, a long lane watch or an interactive agent is unchanged and stays the caller's.
- **D-21: Todo folding.** The 2026-10-29 lane-TOML todo's items 1-4 were folded in Phase 36; its items 5-6 belong to Phase 42. The
  error-class todos (Claude stdout limit, unrecorded error bodies) are Phase 38.1. Nothing else folds here.

### Added 2026-11-16 (re-run 2, herdr hosting, after the R12 amendment)

- **D-22: Hosting is one optional transport inside the runner, next to the direct spawn; it reconciles D-20, 36 D-14 and D-19, and
  38 D-16.** The runner's one spawn seam is `runChild` (cross-ai.mjs `runChild`: detached child, piped output, process-group kill,
  capture caps, a result of `code`, `signal`, `timedOut`, `stdout`, `stderr`); the hosted transport returns the same result, so
  classification, retries, session parsing, the settings report and the status line stay one code path. Chosen over a Python caller
  helper and over a sibling script for three facts: a GSD hook string has no Python layer (the argument of D-01), the lane's output and
  exit code are needed inside the runner to classify and to print `session=`, and a wrapper outside the runner would hide the lane's
  process from the runner's own supervision. The runner calls `herdr` through the same `node:child_process` layer with three
  commands only: `tab create`, `pane run`, `tab close`. Reconciled statements: 37 D-20 (superseded above), 36 D-14 and D-19 (the wizard's
  questions stay the owner's; a probe call the wizard makes through the runner is hosted by the same rule, with the same result and
  the same written file), 38 D-16 (its "never inside the runner" is amended in 38's commit: the runner hosts, never reads herdr as a
  signal). jev typesafe inside_runner_transport choice 0.89 (laya none_of_these low 0.51), consistent with the evidence.
- **D-23: `--host auto|none`, runner default `none`; the builders emit `auto`; `AIKIT_HOST` and the flag's `none` switch it off; no
  config key.** The trigger is availability, never the lane: a hosted lane runs the same command line, so a free or limited lane gets
  nothing from a lane-specific rule (36 D-19's open question, settled: availability only). The runner's own default stays `none` so an
  old hook string or rendered copy runs as before (D-02's compatibility rule); ai-kit's Python layer and the hook builder emit `--host auto`
  through `runner_flags` and the builder, so every ai-kit call hosts when herdr is there. Switch-off: `--host none` or `AIKIT_HOST=none`
  (read when the flag is absent or says `auto`; `none` from either source wins); a shell profile makes it persistent. The envelope of
  36 D-19 holds: the written config is identical with and without herdr, because hosting is a runtime fact and a per-run choice.
  **Own reasoning** (jev laya none_of_these 0.83, a confident answer with no option; second opinion typesafe config_key low 0.67): a
  config key would make the owner's per-project switch possible but needs the Phase 36 writer and validator to change and breaks the
  "one fact, no key" rule of 36 D-19; `AIKIT_HOST` is settable per project with any env loader. Ledger. **Needs owner confirmation** (the
  config-key alternative is real: choose it if a per-project switch in `.aikit/config.toml` matters more than an unchanged 36 writer).
  The trigger half: jev typesafe availability_with_flag choice 0.89 (laya always_when_available low 0.39).
- **D-24: A hosted lane is the headless command run by a launcher; the result channel is files, with `rc` as the only verdict.**
  Live (SPEC added facts): a pane has no exit code; `agent prompt --wait` returns only a lifecycle state and no reply, and its
  `blocked` is ambiguous; a literal `wait-output` match hit the typed line; a launcher run as `sh <path>` with redirected streams and an
  exit file returned the exact code, both streams and the stdin prompt. So the runner writes the run directory (`launch.sh`, `env`,
  `prompt`, `out`, `err`, `pid`, `rc`), opens the tab, types `sh <path>`, polls the three files at a short interval into the existing
  capture buffers, and treats `rc` (renamed into place after the lane exits and its streams close) as the exit code. `herdr pane
  wait-output` is not used: polling files is the truth and needs no screen text (ponytail: one fewer herdr command and no regex on a
  shared screen). A launcher gone with no `rc` ends the lane as killed by a signal through the existing branch. The pane shows a
  header and, after the lane, one `AIKIT-HOST-DONE <token> rc=<n>` line for a human; nothing reads it. **Own reasoning, jev overridden**
  (laya forced; typesafe screen_scrape_marker low 0.63, contradicted by the live check). Ledger.
- **D-25: The lane's environment travels in a 0600 file inside a 0700 per-run directory, sourced by the launcher and removed with the
  directory.** The pane's shell inherits herdr's server environment, not the runner's, and the lane's environment holds API keys and
  the test-isolation variables (`AI_KIT_REFUSE_REAL_HOME`, `HOME`, `XDG_*`); `tab create --env` puts values on a command line that
  shows in the process table (the same exposure a key on argv has anywhere). The directory sits under the state home beside the quota
  cycle records (`<state home>/ai-kit/spec/host/<run token>/`, created with the `mkdir` mode and `fs.writeFileSync` mode, so the same
  `HOME` rule keeps a scratch HOME away from the real one). **Own reasoning, jev overridden** (laya none_of_these low 0.56; typesafe
  tab_env_arguments low 0.65). Ledger. **Needs owner awareness**: a key now touches disk for the length of a hosted lane (headless
  keeps it in memory), in a private file that is removed; the alternative is no hosting for lanes that need keys.
- **D-26: Ownership, closing and failure.** One tab per lane call (never reused; `--no-focus`, `--cwd` the lane's cwd, label
  `aikit:<role>:<runtime>:<run token>`), its id read from the `tab create` JSON, and only that id is ever closed or typed into. The tab
  closes on finish, deadline, signal and spawn error; `tab close` was live-verified to end an `sh` launcher and its `sleep` child (a
  grandchild that detaches is unverified, so the lane's own kill path also signals the launcher pid). The run directory is removed after
  the close. The tab id is also written to the run directory before the launcher is typed so a runner killed hard leaves a record that
  Phase 38's sweep (and Phase 42's) can read: 37 writes the record and closes by id, 38 owns the lock between two runs, the sweep of
  stale records and any naming change (its D-16 amendment). A `tab create` or `pane run` that fails before the launcher is typed gives
  `host` `ignored` with `host_failed` and one headless run; a failure after typing never reruns the lane (an execute lane would run twice).
- **D-27: An interactive agent TUI, a TUI app, an e2e run and pane reuse are not runner transports.** Live: opencode's TUI has no
  `--model` flag, the reply is only on screen, `blocked` means a recognized dialog or an unexplained state, and the structured error
  events the headless command prints (for example the free-limit event) are not visible in the TUI, so the runner could neither apply
  the settings of D-01 nor classify. Phase 42 already plans the per-lane transport chooser (subprocess, resumed session, herdr pane) with a
  result file and a leftover sweep for exactly this; the owner's examples of a TUI app and an e2e run are calling-skill work (UAT, 38.1
  fixture captures), not lanes. What this phase hands over is the protocol (label prefix, run directory layout, the rule that `rc` or a
  result file is the verdict) so that one helper serves 42 and the skills; a fixture test in this phase pins the protocol's file names and
  label grammar so the two implementations cannot drift. jev typesafe caller_transport_later_phase choice 0.98 (laya low 0.43).
- **D-28: Composition with the rest of the phase.** The hosted lane's argv is exactly the headless argv (`--print-argv` prints one list
  for both; the transport is not part of the formula), so settings, effort and context forms, `--argv-file` lanes, session ids (D-03;
  a minted id is parsed from the captured `out` as today, a chosen id is the caller's) and the `AIKIT-XAI` line behave the same; the
  status line (D-12) is unchanged and `host` rides the existing `applied=` and `ignored=` lists. New setting name `host`: `--host auto`
  with herdr available is `applied` (value `herdr`), `--host none` or `AIKIT_HOST=none` is `applied` (value `none`), an `auto` call without
  herdr is `ignored` with `no_herdr`, a failed start is `ignored` with `host_failed`; a call that names no host and has no env value
  reports nothing (the rule for unnamed settings). `--print-argv` and `--describe` report availability from the environment and PATH
  without calling herdr; `--describe` lists the two new reasons. A line `cross-ai: host herdr tab=<id> label=<label>` goes to stderr
  before the lane starts. The runner tests use a fake `herdr` on PATH that replays the JSON shapes recorded live (a test for a
  host-less run needs none: no `HERDR_ENV`); the module baseline already removes host signals, so a test that wants hosting sets
  `HERDR_ENV=1` itself, and a real herdr is called only by the recorded spike under `tmp/`. **Own reasoning.**
- **D-29: A free lane's limit and the runner.** Live today: a free opencode lane returned `provider.free-limit` with a 429 status and
  `retryAfterMs` of about 6 h 44 min in a headless JSON event, and the TUI hid it. The runner treats a free lane like any other and
  hosting changes nothing for it; the classification (a quota-class stop that does not wait inside the 4-hour tier, with the reset time as
  a display field) is Phase 38.1's, the switch to the fallback lane Phase 40's (reading `lane_usage_limit` and `lane_fallback` of
  Phase 36). This phase records the captured wording as a fixture source for 38.1 (the body contains no key) and adds no class.

### Handoffs to later phases

- **Phase 36** (executes first): writes Python effort composition and the `exec_formula` mirror, `no_formula` route and drift
  test as transitional code; if the executed shapes differ, this phase's plan adapts and records it.
- **Phase 38**: the self-test move must carry `STATUS_HEAD_RE`, the new self-test cases and the sample lines; the id-grammar gate and
  the closed effort sets are already gone, so its baseline cleaning covers the self-test entries only; the watchdog and lock
  reuse the planner for their report lines.
- **Phase 38.1**: its error classes use their own closed list; a `rejected` effort line adopts it; the status line grows after
  this group.
- **Phase 39**: the capability block reads the final argv from `--print-argv`; the window check is unrelated to `--context`.
- **Phase 40**: reads `escalate=` for lane switching, passes session ids between review rounds where it wants continuity, and
  routes custom lanes through `--argv-file` (so they get the status line and tree check).
- **Phase 41**: executors resume fix rounds with the printed `session=`; the `no_formula` route is already gone.
- *Added 2026-11-16 (re-run 2):* **Phase 36**: no hosting key is needed (D-23), so 36 D-19's conditional amendment is closed by a
  one-line note there; a probe call the wizard makes through the runner inherits `--host auto` from `runner_flags`. **Phase 38**:
  amends its D-16 in its own commit (the runner may host and close what it opened; herdr is still never a liveness or verdict
  signal); owns the lock between two runs, the sweep of stale `host/<token>/` records and tab ids, any naming change, and the idle
  clock reading the files of a hosted lane (growth of `out` or `err`, plus the tree and commit reset for execute lanes); the runner
  records and closes by id (D-26). **Phase 38.1**: the free-limit event captured today is a fixture source (`provider.free-limit`,
  429, `retryAfterMs`) and its note that no free lane reached its limit is out of date; classes and waits stay its call (D-29).
  **Phase 40**: reads `lane_usage_limit` and `lane_fallback` for a free lane's stop; a hosted lane's result is the same status line.
  **Phase 41**: executor lanes run hosted by default through the builder; the fix-round resume uses `session=` as before.
  **Phase 42**: owns the interactive-agent, TUI-app and e2e transports and the per-plan pane reuse; it reads this phase's protocol
  (label grammar, run directory files, `rc` as the verdict) rather than inventing a second one (D-27).

### Open questions for the phase researcher

- Does a second call actually continue the session on each primary host (the spike), and does opencode accept a caller-chosen id?
- Which claude permission flag works under `-p` here, and does `-p` refuse `bypassPermissions` in any setting (a help fragment
  hints it can)?
- Do cursor's bracket keys `effort` and `context` apply to every model it lists (only the help example shows them)?
- Which self-test cases take real time (the shard recorder decides their kind)?
- Whether GSD's `run-with-timeout` keeps the one-last-line rule with the longer status line (line length, no truncation).
- *Added 2026-11-16 (re-run 2):* whether `tab close` also ends a grandchild that detaches from the launcher's process tree (only an
  `sh` plus `sleep` child was tested); how fast the poll interval can be before the files cost CPU on a long lane; whether `pane run`
  of a short `sh <path>` line is safe in every interactive shell an owner may use (zsh was tested; fish and nushell are unverified)
  and what a pane whose shell is not at a prompt does with the typed line; whether herdr on macOS differs (its skill text names a
  line-length limit there); what the hosted lane's `pid` file should hold so a dead launcher is told from a slow one.

</decisions>

<canonical_refs>
## Canonical References

- `.planning/phases/37-shared-runner-options-and-session-ids/37-SPEC.md` (requirements, live facts, findings)
- `.planning/phases/36-spec-config-as-the-hub/36-CONTEXT.md` (D-05, D-06, D-08 handoffs), `36-SPEC.md` (R4, R5, R7)
- `.planning/phases/35-model-discovery-and-catalog/35-CONTEXT.md` (D-16 to D-18 guard, D-09 window per runtime)
- `skills/ai-kit-spec-review/references/cross-ai.mjs` (`RUNTIMES`, `parseArgs`, `resolveRuntime`, `main`, `sameSessionArgv`,
  `STATUS_HEAD_RE`, `finish`), `skills/ai-kit-spec-review/ai_kit_spec/` (`runner_dispatch.py`, `commands.py`, `routing.py`,
  `detection.py`, `cli.py`), `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/` (`cross_ai_script.py`,
  `cross_ai_build.py`), `tools/check_dogfood.py`, `tests/cross_ai_selftest.py`
- `skills/ai-kit-cross-ai/SKILL.md` and `references/`, `skills/ai-kit-spec-review/references/cross-ai-dispatch.md`,
  `skills/ai-kit-gsd-curated-config/references/runner.md`
</canonical_refs>
