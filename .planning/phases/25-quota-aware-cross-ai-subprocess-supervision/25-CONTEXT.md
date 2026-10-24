# Phase 25: Quota-aware cross-AI subprocess supervision - Context

**Gathered:** 2026-10-14 (assumptions mode, `--analyze --all --batch`, jev screening, best over easy)
**Status:** Ready for planning

<domain>
## Phase Boundary

When a cross-AI child (pi, opencode, cursor, codex) stops on a usage limit, ai-kit decides
whether waiting will help, by message and by route:
- If it will, ai-kit waits with a bounded, file-driven policy and resumes only the unfinished
  work.
- If it will not, ai-kit reports and moves on.

The WHAT is locked in `25-SPEC.md` (R1–R8, amended 2026-10-14 by this file). This file locks the
HOW. The orchestrating session's own resume and the AGENTS.md rules are Phase 26.

Phase 25 plans against the **contracts** of 16.1, 18 and 18.1, which are specified but not yet
built (D-20). Code that 18.1 R7 deletes is never patched.
</domain>

<decisions>
## Implementation Decisions

### Classification (R1, R2)
- **D-01: The pattern table and matcher live only in the runner.** Python never matches stderr
  itself; it reads the `AIKIT-XAI` status line, which gains `reset_at=` and `pattern=verified|
  unverified`. Python tests drive the shipped runner, through `--self-test` or a classify-only
  mode, over the same fixture file. 18.1 R7 already routes every subprocess through the runner,
  and 18.1 D-13 means no node, no dispatch. 16.1 D-13's `(returncode, stderr, timed_out)`
  classifier is superseded for subprocess output (amended there).
  - **Own reasoning** (Laya python_stamps 0.51 (fb), TypeSafe runner_only 0.56 (fb)): two
    matchers over one table drift (research 18 §4). The runner is the only component on both
    call paths. Ledger.
- **D-02: The table is its own marked JSON block in the runner template**, outside
  `// <config>` and covered by the sha256 header (18 D-26), so a user edit produces a `.new`
  file.
  - **Laya overridden** (in_config 0.75): user-editable classes defeat evidence labels.
    TypeSafe second opinion marked_block 0.93.
- **D-03: Match order: structured error type/code, then per-CLI billing/access text, then quota
  text, then auth text, then bare status codes (`\b401\b`, `\b429\b`).** A test pins the order.
  `ActionRequiredError` alone is not an auth signal. Evidence:
  - router-env's `[401]: Your workspace has reached its monthly spending limit` with
    `type=MonthlyLimitError` (12 live hits);
  - every live cursor `ActionRequiredError` was a usage limit or a plan gate.
  - **Laya overridden** (auth_first 0.80): auth-first makes the router's 401 monthly limit exit
    69, contradicting R2. TypeSafe second opinion specific_first 0.92.
- **D-04: Matched inputs, per CLI:**
  - opencode `type:"error"` stdout events (`error.name`, `error.data.message`,
    `error.data.statusCode`);
  - codex JSONL `error`/`turn.failed`;
  - cursor result `is_error`/`result`;
  - stderr for all.

  The runner never reads codex's private rollout files. `codex_error_info` was seen only there,
  so codex matches on its distinctive text until research shows the field on stdout.
  - **Own reasoning** (Laya read_private_log 0.52 (fb), TypeSafe read_private_log 0.68 (fb)):
    both backends were low. Reading another tool's undocumented on-disk format is fragile, and
    the text is already distinctive. Ledger.
- **D-05: Python resolves the route kind and passes it per candidate (baked into CONFIG at
  render).** The source is the catalog's user-confirmable `fallback_quota`; `infer_fallback_
  quota` is only the default when the field is absent. No route given means `unknown`. R2's
  boundary is amended accordingly. Laya confirmed_field 0.72.
- **D-06: "Direct" is a closed, evidence-labelled prefix list per runtime, in the same table:**
  OpenCode Zen `opencode/`, OpenCode Go `opencode-go/`, and Cursor named API models. Everything
  that is neither router nor listed is `unknown`. Laya non_router_is_direct 0.68 (fb), TypeSafe
  prefix_list 0.78.
- **D-07: On a direct route, known monthly or account-cap wordings are `billing_or_access`.**
  Examples: cursor `You've hit your usage limit … Spend Limit`, Zen `FreeUsageLimitError`, Go
  `GoUsageLimitError`. Other quota text falls back to the unknown-route rule (wait, capped).
  This fills R2's gap for limit text on direct routes. Laya cap_patterns_report 0.41 (fb),
  TypeSafe cap_patterns_report 0.78.
- **D-08: On a router route, errors from the fallback tail are `quota_wait`.** These are
  missing-credential text, `Credential gate blocked`, `all targets were skipped by pre-dispatch
  filters` and the `[401]` MonthlyLimitError. Only auth at the router's own entry point (its
  own key or login) stays `auth`/69. This fills R2's gap for router-tail access text. Laya
  all_but_bad_model 0.81; TypeSafe second opinion tail_waits 0.87 (it keeps entry-point auth
  separate).

### Detection and reset time (R3, R4)
- **D-09: A live kill happens only on a terminal signal:** a structured error event or a table
  pattern marked `terminal`. A short grace period follows, then the process group is killed.
  Retry-notice lines and capacity lines never kill. A terminal signal is recorded the moment it
  is seen, so the 64 KiB stderr tail cannot lose it. opencode and pi retry limits internally
  (`AI_RetryError: Failed after 3 attempts`). Laya first_line 0.66 (fb), TypeSafe terminal_only
  0.99.
- **D-10: opencode and codex stdout is parsed line by line for error events only.** Text and
  agent-message parts are skipped, which keeps answer text out of the matcher. Cursor keeps its
  verified `--output-format json` formula; its live detection is stderr-only, flagged
  unverified, and Phase 21 owns `stream-json`. Laya switch_stream 0.41 (fb), TypeSafe
  keep_verified 0.98.
- **D-11: The runner parses the reset time once and writes an absolute `reset_at`.** The
  observed forms are:
  - codex `try again at 6:30 PM`, read as local time; a time already past means tomorrow;
  - codex `try again at Aug 1st, 2026 3:36 PM`, with an ordinal suffix;
  - claude `resets 9:30pm (America/Santiago)`, where the IANA zone in parentheses is honored.

  `try again later` and `try again in a moment` are not times. Five codex rollouts had resets
  0.6–3.2 h after the event when read as local time; read as UTC they would be in the past.
  Analyzer: Confident.

### Wait, state and resume (R5–R7)
- **D-12: The runner owns the dispatch-level state file.** It writes the file on exit 75 and
  handles the re-check, the cap, the tree compare and the resume prompt. The skills' resume
  files keep only ladder and exclusion data plus a pointer to it. The GSD path has no Python at
  run time, and only the runner computes the tree id (18 D-27).
  - **Laya overridden** (both 0.85): two records for one wait drift, and the GSD path could not
    enforce the cap. TypeSafe second opinion runner_owned 0.72.
- **D-13: State lives in ai-kit's cache directory**
  (`$XDG_CACHE_HOME/ai-kit/spec/waits/<sha(realpath)>/<task>.json`), never in the working
  tree. Writes use mkstemp plus replace, and an exclusive create refuses a second wait for the
  same task. An in-tree file would make every run `tree=dirty` (temp-index `git add -A`).
  - **Laya overridden** (git_dir 0.74): the repository's git dir is removed with its worktree,
    and per-worktree paths break the cache precedent. TypeSafe second opinion user_cache 0.95.
- **D-14: Task key on the GSD path: one pending wait per worktree, confirmed by matching the
  prompt's `<objective>` against the phase's PLAN.md files.** A prompt hash is only a
  tiebreak. Python paths pass their task id. GSD's prompt is rebuilt by the orchestrating model
  each retry (`elaboration.md:84-87`), so its bytes are not stable. Laya caller_id_else_worktree
  0.59 (fb), TypeSafe worktree_plus_objective 0.76.
- **D-15: A re-check is a cheap runner probe** (18.1 D-14's shape, `--mode review --timeout
  30`) that updates `attempts` and `next_check_at`. The real resume runs only after a probe
  passes. Live codex limit hits return in 1.5–4.3 s.
  - **Laya overridden** (full_retry 0.88): each full GSD retry re-enters step 2.5 and burns a
    partial attempt on a limited CLI. TypeSafe second opinion probe_then_resume 0.94.
- **D-16: Scheduling is a chain of one-shot wakes driven by the state file.** Each wake reads
  `next_check_at` and schedules the next; there is never a recurring job. Claude Code's
  `ScheduleWakeup` and `CronCreate` are named. Other hosts stop and print the state path and the
  exact resume step, flagged unverified; Phase 26's survival matrix later fills those rows. Laya
  oneshot_chain 0.46 (fb), TypeSafe oneshot_chain 0.89.
- **D-17: `action=` is the runner's verdict over the candidates it was given.**
  - A one-candidate call (18.1 D-11) emits `retry-later`, and Python's ladder applies R6.
  - A multi-candidate call (the dogfood `prefer` list) applies R6 inside the runner.

  The 4-hour window is per task across CLIs, never per CLI. Laya verdict_per_call 0.39 (fb),
  TypeSafe verdict_per_call 0.95.
- **D-18: The native session is not "another usable candidate" for R6.** This applies to both
  GSD's skip and review's native reviewer. The user can always answer "skip" by hand.
  - **Own reasoning** (Laya native_last 0.79, TypeSafe second opinion native_not_candidate
    0.58 (fb)): cross-AI exists to save the main session's quota, so silently moving the work
    home defeats it. Ledger.
- **D-19: The state file keeps the first attempt's HEAD and tree id and is never re-snapshotted.**
  - "Done work" is the commits since that HEAD plus `git diff --stat` paths.
  - It goes into the prompt only when no session id was captured.
  - Session id sources: pi uses a pre-assigned id; codex `thread.started`; opencode
    `--session` (create-if-absent); cursor `session_id` only in the final result.
  - **Own reasoning** (Laya first_snapshot 0.56 (fb), TypeSafe latest_snapshot 0.49 (fb)): a
    re-snapshot turns the partial edits into the base, so the resume prompt says nothing is
    done. Ledger.

### Skills and contracts (R8)
- **D-20: Plan against contracts.**
  - **Current code** that changes or is removed:
    - `.planning/scripts/cross-ai.mjs` (dogfood runner);
    - the hourly-wake text in `ai-kit-spec-execute-gsd/SKILL.md:75-100`,
      `ai-kit-spec-execute-superpowers/SKILL.md:39,176-217` and its
      `references/state-management.md` and `escalation.md`.
  - **Contracts:**
    - the runner template under `skills/ai-kit-spec-review` (18.1 D-10, 18 D-26);
    - 18 D-27's status line;
    - 18.1 D-11 to D-14;
    - 16.1 D-13 and D-22.

  `quota.py`/`dispatch_injection.py` matchers are not patched (18.1 R7 deletes them).
- **D-21: The closed reason set gains `billing_or_access`** (non-wake, its own advice:
  "add credits or enable the model"). The other mappings:
  - `quota_wait` maps to `quota`, which keeps the `any_quota_recoverable` gate;
  - `capacity` is added, settling 18.1 D-12's planner item.

  18.1 D-12's `billing → auth` is amended. Laya configuration 0.39 (fb), TypeSafe
  new_billing_access 0.99.
- **D-22: `ai-kit-spec-review` gains the policy rather than replacing an hourly wake** (it has
  none today; R8 amended). Review lanes are read-only, so their tree is always clean. A lane
  falls back along its own ladder; when the ladder is exhausted, it waits per R5 while the
  other lanes finish. The merge then marks it `pending` and re-merges when it resolves. Laya
  lane_pending 0.51 (fb), TypeSafe lane_pending 0.94.
- **D-23: One canonical policy reference**, `skills/ai-kit-spec-review/references/
  subprocess-quota-policy.md`. The three skills link to it, and Phase 26's AGENTS.md rule quotes
  it. Laya one_reference 0.43 (fb), TypeSafe one_reference 0.96.
- **D-24: Phase 26 coupling, recorded for its discuss step:**
  - a bare `/gsd-execute-phase` waits only if Phase 26's OpenGSD rule says so;
  - GSD's `/gsd-review` and convergence lanes don't use `cross_ai_command`, so only that rule
    covers them;
  - the state file names its resume step, so a self-resumed session can pick up a pending
    child wait;
  - the claude `resets <time> (<zone>)` parser may be needed from Python by Phase 26. The
    reset-parsing grammar is therefore a fixture file both can test against; the Node parser
    stays canonical.

### Claude's Discretion
- Grace period length, the probe prompt text, the exact JSON schema field names, the fixture file
  layout.
</decisions>

<canonical_refs>
## Canonical References

- `.planning/phases/25-quota-aware-cross-ai-subprocess-supervision/25-SPEC.md` — locked WHAT
- `.planning/phases/18-curated-config-v2-cross-ai-hard-gate/18-CONTEXT.md` — D-26..D-28 runner template, status line, exit classes
- `.planning/phases/18.1-*/18.1-CONTEXT.md` — D-10..D-14 (runner as sole supervisor, status table, fail closed)
- `.planning/phases/16.1-*/16.1-CONTEXT.md` — D-13 classifier (amended), D-22 mkstemp
- `.planning/research/2026-10-13-audit/18-runtime-detection-and-subprocess-supervision.md` — §4.3–4.7
- `.planning/scripts/cross-ai.mjs` — dogfood runner (TRANSIENT/FATAL, RUNTIMES resume argv)
- `~/.claude/gsd-core/workflows/execute-phase/detail/elaboration.md` §2 — GSD cross-AI step (upstream, unchanged)
</canonical_refs>

<code_context>
## Existing Code Insights

- `model_heuristics.infer_fallback_quota()` and the catalog's `fallback_quota`/`heuristic_confirmed`
  (`model_catalog.py:231-260`, `config_io.py:136-138`) feed D-05.
- `dispatch.write_resumable_state` and `cache.cache_write_json`: the latter uses a fixed `.tmp`
  suffix, so D-13 needs 16.1 D-22's mkstemp.
- Installed versions are opencode v2.0.29 and codex-cli 0.162.1. The formula comments still say
  1.18.35 and 0.153.4; the flags still exist.
</code_context>

<specifics>
## Specific Ideas

- Observed messages to fixture: opencode `The usage limit has been reached` (APIError, 429);
  router `[401] … monthly spending limit` (MonthlyLimitError); Zen `Model access is disabled`;
  Go `Insufficient account funds`; pi `FreeTierError` 403; pi on anthropic `Third-party apps now
  draw from your extra usage` (400); cursor usage limit and `Free plans can only use Auto`.
</specifics>

<deferred>
## Deferred Ideas

- Research (route to `gsd-phase-researcher`):
  - Does `codex exec --json` 0.162.1 emit `codex_error_info` on stdout?
  - Where does cursor's `ActionRequiredError` go under `-p --output-format json`, and does
    `stream-json` stream errors?
  - What does pi's stderr show on a limit, and which `--mode json` error event does it emit?
  - Does opencode exit promptly after its final `type:"error"` event?
  - Can `ScheduleWakeup` be called outside `/loop`; does `CronCreate` support a one-shot job;
    does either fire while a GSD choice is pending?
  - How long do router-env tiers take to recover? (uz's estimate is the only source.)
  - Does any limit message carry a reset time other than codex's and claude's?
</deferred>

## Orchestrator rulings on 25-RESEARCH.md (2026-10-24)

Routed through the jev ladder (Laya local) where a design choice was open; factual questions that
need a live vendor run stay unverified rows or owner items. Binding for planning.

- **Drift accepted:** the runner is template 6 at `skills/ai-kit-spec-review/references/cross-ai.mjs`
  (bump to 7, re-render the dogfood copy). The `error_classifier` classes already exist; extend them.
- **D-03 amended:** opencode's own `error.type` is a weak hint only (`provider.auth` wraps billing
  errors). Vendor codes and message text rank above it.
- **D-04 amended:** the opencode matcher accepts both shapes: `error.type`/`error.status`/
  `error.response.body` (2.0.31, probed) and the older `error.name`/`error.data.*`.
- **D-05 amended:** a per-CLI `--route-<cli>` flag carries router-backed status into the Python
  review/execute paths (the unrendered template has no `routerBacked`).
- **D-14 amended:** the first dispatch stores a digest of the plan's `<objective>`; re-entry compares
  it instead of re-parsing PLAN.md.
- **D-19 amended:** "unfinished work" is measured with `git diff-tree` between the stored write-tree
  id and a fresh snapshot (covers untracked files, which `git diff --stat` misses).
- **Q1 codex terminal signal:** only `turn.failed` carrying limit text is terminal; bare `error` /
  `item.completed` error items are recorded, not terminal. Laya A (fallback 0.68); own reasoning
  from the mock probes.
- **Q5 probe timeout:** counts as still limited, one attempt consumed, keep waiting. Laya A (0.84,
  decided).
- **Dirty tree vs R6:** a quota-class stop keeps `retry-later` with a dirty tree when every dirty
  path is inside the plan's `files_modified`; any other class, or a path outside the plan, demotes
  to `stop` as today. The two self-test cases pinning the old demotion are updated with that
  rule. Laya A (fallback 0.70); own reasoning (R6 resumes unfinished work).
- **Q2, Q3, Q4, Q8, Q9 (live-only facts):** cursor's limit channel, exit code and session id; real
  `resets_at` presence; pi's weekly-limit text; router-env recovery times; the cursor `direct`
  prefixes. Each ships as an `unverified` pattern row, or empty for Q9. A missing `resets_at`
  falls back to the locked 10-minute / 4-hour schedule. The owner confirms them in a live kit.
- **Q7 self-wake:** the orchestrating session uses a one-shot `CronCreate` at the reset time
  (documented as supported), not `ScheduleWakeup` (`/loop` only).
- **Transient upstream 400 (added 2026-10-24, evidence from the router owner's logs):** a router
  response whose body is only `event: error` (surfaced by pi as `[400]: event: error`, in=0 out=0,
  seen twice at 13:32 and 13:33 -03 on combo `my-coding` -> `opencode-go/qwen3.8-flash`, then 200s
  again) is a `transient` class: the runner retries the same CLI once (same session id) before
  moving to the next CLI. It is not quota and never waits. Context: the combo pins a session to
  one member (`context_cache_protection=true`), so the router itself does not fall back.
- **Verified pattern (router logs, 2026-10-24):** `kimi-coding` monthly quota exhaustion returns
  HTTP 429 (12:00 and 12:32 -03). A monthly limit never recovers by waiting inside the 4-hour
  window, so the route-aware classifier maps it to stop-and-report unless the route is
  router-backed with other members.


## Owner decision (2026-10-24): External Agent Runs ladder — supersedes the wait-and-resume design

Relayed from the owner (also in llm-env AGENTS.md "External Agent Runs"); binding over every
earlier requirement, decision and ruling in this phase that conflicts with it:
1. Transient (`[400]: event: error`, 5xx, cut stream, timeout): retry up to 3 times in the SAME
   session.
2. Still failing: a NEW session on the same lane (a router pins each session to one combo member;
   a new session lets the combo choose again), up to 3 more attempts.
3. Quota / rate limit / auth (429 monthly limit, 401/403): never retry the same model; stop and
   report.
4. Out of rungs: stop and report with evidence (status, lane/combo, model, times) for the owner.
The harness catalog (cursor, codex, claude, pi, opencode...) is a menu used only when the owner
names one: the runner never switches harness, provider or model on its own, and the automatic
fallback to another CLI is removed. Superseded here: the 10-minute / 4-hour wait-and-resume, any
"move to the next candidate" step, and the earlier ruling's single-retry transient rule (now 3+3).
Kept: the per-CLI pattern table, live and after-the-fact detection, the typed reason, session-id
continuation per CLI (used by rung 1), and the dirty-tree rule (a quota-class stop now ends in
stop-and-report, so the rule only matters for the transient rungs).

**Placement (owner correction, 2026-10-24):** the full ladder lives in the runner template
(`cross-ai.mjs`), implemented and pinned by its self-tests, and travels in every rendered copy
(`ai-kit-gsd-curated-config` `apply-execution` / `ensure-runner` and the `ai-kit-spec-execute*`
skills). Anything a skill writes into a project's AGENTS.md / CLAUDE[.local].md is a concise 3-4
line summary that points at the runner, never the detailed rule (Phase 26's rules emitter
follows this).

**Rule adjustment (owner, 2026-10-24, replaces step 3 "quota = stop without retrying"):** on a
quota or rate-limit error from a router lane, the orchestrator manages the session: it retries the
same lane up to 3 times, then switches session (the combo picks a member again) up to 3 times.
Only if the error persists after those 3 session switches does it report with evidence (status,
combo, model, times) and wait several minutes before trying again or reporting again. It still
never switches harness, provider or model on its own (the CLI catalog is used only when the owner
names one). Orchestrator interpretation, to confirm with the owner: auth errors (401/403) are not
covered by the adjustment and keep stop-and-report. The "several minutes" cooldown defaults to 10
minutes between full cycles and is bounded by this phase's existing 4-hour cap, so a cycle never
loops forever. Detail and tests live in `cross-ai.mjs`; instruction files keep the short pointer.

## Orchestrator rulings on plan-review cycle 1 (2026-10-24)

- **Quota cycles span runner calls (resolves the 4-hour vs call-deadline HIGHs):** inside one call
  the runner runs only the bounded rungs: 3 same-session retries, then 3 new sessions, with short
  injectable backoff. When a router quota or rate limit persists, it prints the evidence report and
  exits 75 with `retry_after_s=600` and `cycle=<n>`. The caller waits (the orchestrator's one-shot
  wake or the execute skill's loop) and re-invokes. A small state file keyed by lane and model,
  under the XDG state dir with 0600 and atomic writes, stores `first_seen` and the cycle count. A
  re-invocation past 4 hours stops for good: it reports and exits 69. No real sleep exceeds the
  remaining call budget.
- **Timeouts are transient rungs:** a timed-out attempt with no quota match enters the transient
  ladder. A timeout that printed a quota or rate-limit signal is classified as that signal and is
  never also treated as a plain timeout.
- **Only a confirmed route gets router-quota cycles:** confirmation comes from `--route-<cli>
  router` or the catalog's user-confirmed `fallback_quota`. A name-only heuristic is advisory
  only: it is reported in the evidence and gets no cycles, so it stops and reports like a direct
  route.
- **Evidence never carries a secret:** the runner stops relaying raw child stderr verbatim. Every
  relayed line passes the secret redactor. The sentinel tests build their keys at run time (no
  literal in plans or tests) and scan the full log, not only the prefixed lines.
- **Existing pins:** plans update `tests/test_ai_kit_spec.py`'s `test_patterns_block` and
  `test_header_and_config_contract`, and the version pins, in the same commit as the change that
  breaks them.
- **Judge set (25-11):** native Opus plus opencode `router-env/my-referee-one` and
  `router-env/my-referee-two`, per the owner's 2026-10-24 change.
- **Menu selection (25-01):** the first installed entry of `--prefer`/`CONFIG.prefer` that suits
  the mode is chosen once. The runner never evaluates later entries after a failure, and a later
  review-only entry never rejects an exec request.

## Cycle-3 rulings (2026-10-24, at the review cap)

- **Attempt timeout:** an exec attempt's timeout is the call's remaining deadline (minus the
  existing reserve), never a short fixed default. A real plan run must not be killed by a
  per-attempt cap. Review mode may keep a shorter attempt cap. Tests use injected short deadlines.
- **Timeout reclassification:** when an attempt ends by timeout, its captured output is
  classified with every row, terminal and non-terminal. A `429` / rate-limit text makes it a
  rate-limit stop, not a transient timeout.
- **Cap headroom:** each child attempt's timeout is
  `min(attempt timeout, quota-cap remaining - reserve)`, so no attempt can run past the 4-hour cap.
- **State reset:** the state file holds `first_seen` and `last_attempt_at`. If `last_attempt_at`
  is older than the 4-hour cap, the file is stale: it is replaced with a fresh episode, the call
  proceeds, and the evidence notes `stale-state-fresh-start`. If the episode is still active and
  past the cap, the call exits 69 before spawning. One rule, one outcome per case.
- **Session resume scope:** the quota budget stays keyed by lane and model. The session id to
  resume is stored per task key (the plan id or the prompt's objective digest) and never reused
  for a different task on the same lane.
- **Confirmed route everywhere:** every producer of a rendered runner command, including
  curated-config `plan_edit` and `apply-execution`, passes `--route-<cli>` only from the
  user-confirmed catalog field. Inferred stays advisory.
- **Mechanical fixes:** anchors use `$`, not `[$]`. The 25-09 gate checks forbid the removed
  wording only where it was removed, and the prescribed sentence and its test agree. Ladder test
  timings use injected clocks with consistent deadline arithmetic (each case's numbers are
  checked by hand in the plan).
