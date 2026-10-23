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
