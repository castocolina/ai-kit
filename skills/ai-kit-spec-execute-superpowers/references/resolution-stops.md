# Steps 2 and 3 reference: owner stops

MANDATORY read when `resolve-injection` exits non-zero, prints the untrusted-config line, or
returns `$INJECTION_MODE` `no_candidate` or `quota_exhausted` (`SKILL.md` Step 2), when a rounds 4–5
re-resolution stops (`escalation.md`), and before acting on any dispatch outcome other than `ok`
(`dispatch-external-cli.md`, Classify) or on a failed native dispatch,
and when the code review step stops at its cap (`code-review.md`). Do NOT load it when the result
is `native` or `external_cli` with a clean stderr and the dispatch classified `ok`. Every `$VAR` is
restored by the scalar loader (`SKILL.md`, Step 0).

## Owner stop

**Session-model fallback first.** When the owner turned on `session_fallback` in `[lanes.policy.execute]`, a plain Step 2 `resolve-injection` (fix round below 4, no escalation keys) does not return `quota_exhausted` (every configured lane unavailable, blocked or out of quota): it prints a `native` injection with `"fallback": "session"` (its `model` is jev's confident haiku-or-sonnet pick on a Claude Code host, otherwise empty, which means the session model) and stderr `ai-kit-spec: no execute lane is available; this task runs on the session model (<note>)`. Dispatch it through Step 3's native branch with its session-fallback exception. With the flag off, stderr says `run ai-kit-spec-config to add one or to turn on the session-model fallback`: put that line in the stop report. A `no_candidate` result (task narrowing left no configured lane) is never replaced by the session model: it stays the curation-gap stop below, flag on or off.

Every stop-versus-continue decision of Steps 2 and 3 is listed here once; the other files hold only the
mechanics (state writes, the wait and schedule blocks) and link here. When `WAKE_OWNED=1`, every stop
below ends with the close block of `session-wake.md` ("Close the session wake"); the one-shot wait of
`quota_cycle` is not a stop.

### Exit codes and the untrusted-config line

**If the block prints `resolve-injection exit 2`**: a malformed `config.toml` (or an old roster that fails to migrate), or an
entry with `purpose = "execute"` that can never execute (a custom `command` entry or a runtime outside the table;
a `claude` pair is not refused here, it takes the route the shim returns). STOP and relay its stderr verbatim; any other non-zero
exit stops the same way.

**If its stderr prints `ai-kit-spec: ignoring untrusted project-local config <path>; review its
commands with ...`** (match on the whole `ai-kit-spec: ignoring untrusted project-local config` prefix), this resolution used the global
config only. Ask **once per run**: relay the line verbatim, tell the owner that the preview records no
trust but first migrates a pending old roster into `config.toml` (retiring the old file), then show
`python3 "$TOOLS_PY" trust-local --cwd "$CWD" --show` (one JSON line per local reviewer with the
argv it would run, the prompt shown as `<prompt>`), and ask whether to trust it.
On yes, run `python3 "$TOOLS_PY" trust-local --cwd "$CWD"` and re-run this step's
`resolve-injection` before dispatching. On no, continue on the global-only result and do not ask
again this run, though the line repeats on every later resolution. Never trust unasked.

### `no_candidate` and `quota_exhausted`

- **`no_candidate`** — nothing configured for this task survives affinity/context narrowing (read
  `detail`, e.g. every `context_limit` is below the task's `required_context`). A curation gap, not
  quota. STOP this wave and report `detail`. Nothing is scheduled.
- **`quota_exhausted`** — read `any_quota_recoverable`
  (`python3 -c 'import json,sys; print(json.loads(sys.argv[1])["any_quota_recoverable"])' "$(cat "$RUN_DIR/INJECTION_JSON.json")"`).
  It, not `all_auth_failures`, is the gate. `reasons` holds `"quota"`, `"auth"`,
  `"billing_or_access"`, `"capacity"`, `"git_timeout"`, `"timeout"`, `"configuration"`,
  `"dispatch_unavailable"`, `"real_error"`, `"no_usable_dispatch"` (a prior wave's permanent
  failure), or a skip-route name (`"bad_model"`, `"no_formula"`, `"not_installed"`,
  `"no_inventory"`, `"unknown_runtime"`, `"no_model"`; never picked). Only `"quota"` is worth
  waiting for.
  - **`any_quota_recoverable == False`** — no candidate is eligible for automatic quota recovery
    (only `"quota"` is). Some reasons may clear on their own (`"capacity"`), others need a fix first
    (credentials, configuration). STOP this wave and tell the user which key needs what fix, read
    off `reasons`: `"auth"` needs login or entitlement, `"billing_or_access"` credits or model
    access, `"configuration"` a fixed model id, prompt or flag (the runner refused it), `"capacity"`
    a later re-invoke (this stop writes no resumable-state file, so a key not already saved as
    permanent is tried again; the scalars persist), `"git_timeout"` a look at the repo (the work-tree
    check timed out, not the CLI), `"timeout"`/`"dispatch_unavailable"` an investigation of the CLI,
    `"real_error"` its own diagnosis (pinned state: dispatch-external-cli.md). Nothing is scheduled. This
    stop is the adapter's own call, not one of subagent-driven-development's four stop-and-ask conditions
    (`references/design-notes.md`).
  - **`any_quota_recoverable == True`** — at least one candidate is quota-exhausted, which is
    time-bound. Write resumable state, then STOP this wave and report the reasons per key and the
    state path; the owner re-invokes to resume. Nothing is scheduled. Only `"quota"` keys come back:
    every other co-tried key, `"capacity"` included, is saved as a permanent exclusion. **MANDATORY: read
    `references/state-management.md`'s "Resumable state" sections first** — they give the exact bash
    for merging `tried`/`reasons` into the wave sets, computing `$RESUME_EXCLUDED_KEYS_JSON` with the
    `resume-exclusions` subcommand (never inline set arithmetic), the `STATE_JSON` passed to
    `write-resumable-state`.

### Rounds 4–5 re-resolution

- **Empty or unknown anchor** — An empty anchor, or one missing from `ladder_keys` or from the live execute roster, dispatches nothing: `$ESCALATION_ANCHOR_KEY` empty (an old state file) or missing from `ladder_keys` (the config changed) leaves no order to bump along, so no pick is a verified bump. Do not re-run `resolve-injection` for this round; STOP and ask the owner to name a candidate from `ladder_keys` they judge more capable than the stuck implementer, or to stop (the owner-pick mechanics: `escalation.md`, "An empty or unknown anchor never dispatches").
- **`any_quota_recoverable == True`** — a more-capable candidate is only temporarily out of quota. Run the recoverable branch of the subsection above; its state write carries this round's `$FIX_ROUND`, `$LAST_DISPATCHED_KEY` and `$ESCALATION_ANCHOR_KEY`. Never dispatch a same-or-weaker candidate as a substitute.
- **`False`, or `no_candidate`** — no more-capable candidate is eligible for automatic quota
  recovery (the `False` branch above: this stop writes no resumable-state file; the round and anchor scalars persist, so the re-invoke keeps the floor). Do not fall through to a same-or-weaker one. Nothing is scheduled. STOP and
  tell the user that rounds 4–5 cannot honor the capability bump with the current ladder, reading
  `reasons`/`detail` for which candidates failed and why. When the pool was narrowed only by the
  floor (the stuck key is top-ranked), `reasons`/`detail` are empty by design: name the keys in
  `$ESCALATION_EXCLUDE_JSON` instead. For a native stuck dispatch on a non-Claude host, also say
  how to unblock it: put a more capable routable pair above `$ESCALATION_ANCHOR_KEY` in
  `[lanes.policy.execute]` ladder, then resume. Switching this session's model does not help: the session default
  keeps its ladder key, which the floor still excludes. This stop is the adapter's own
  call, not one of subagent-driven-development's four stop-and-ask conditions.
- **An unavailable kept lane** — when the gate printed `escalate` false (reason `off` or `no-target`), the round stays on the anchor's own lane, so a re-resolution that reports `quota_exhausted` or `no_candidate` means that lane is unavailable, not that a bump failed: stop as the `no_candidate` and `quota_exhausted` subsection above says for that result (its recoverable branch when `any_quota_recoverable` is true) and tell the owner the stuck task's own lane is unavailable and its escalation flags allow no move. The `any_quota_recoverable == True` and `False` bullets above apply only when the gate printed `escalate` true.
- **A re-resolved key the gate did not allow** — at the automatic round, `$INJECTION_KEY` is missing from `$RUN_DIR/ESCALATION_ALLOWED_JSON.json`: dispatch nothing; STOP and tell the owner which key the re-resolution returned and which keys the gate allowed.

### Dispatch-time stops

- **`"ok"`** — not a stop; Classify continues (`dispatch-external-cli.md`).
- **Quota outcome on a lane the owner flagged `usage_limited`** (class "quota_cycle" or "quota", every RETURNCODE 69 and a bare 75): the **Flagged switch** step of [dispatch-external-cli.md](dispatch-external-cli.md) runs first (at fix round 4 or 5 it moves only to a lane the escalation gate allowed); a dispatched switch is not a stop. Only when it records `SWITCHED=0` do the items below decide.
- **`"quota_cycle"`** — Only a classified `"quota_cycle"` (exit 75 with whole-number `retry_after_s` and `cycle` in `$CLASSIFICATION`) gets the one-shot wait and re-dispatch of the same task, lane and model (a hint such as `600s` classifies `real_error` and never reaches this branch); the re-arm and schedule blocks are `dispatch-external-cli.md`'s **Schedule-or-stop**.
- **`"quota"`** — an owner stop: schedule nothing and re-arm nothing. Every `RETURNCODE` 69 (`stopped=hard-waits`, `stopped=cap`, or a `cross-ai: lane stopped=` refusal) is an owner stop after relaying the evidence, including that line's state path, whose deletion is the owner's reset. A runner `RETURNCODE` 69 or 75 whose status is `transient` or `quota` with no token or only one of the two (neither malformed) is classified `quota` but is an owner stop: relay, write pinned state, schedule nothing. In short, every `RETURNCODE` 69 stops; a bare 75 and any other quota class are owner stops, and so is `reason == "quota"` at any other `RETURNCODE` (no re-resolve: NEVER index).
- **`"real_error"`** — stop for the owner with the pinned state written (the relay and fold block: `dispatch-external-cli.md`, `"real_error"`).
- For every owner stop above, report `$RESUME_STATE_PATH`: an owner re-invoke re-dispatches the pinned injection ([`state-management.md#pinned-resume`](state-management.md#pinned-resume)), or runs the "Owner-named replacement pair" recipe in `state-management.md` for a pair the owner names.
- A failed native dispatch (for example an `Agent` model error) is subagent-driven-development's own (NEVER index); stop for the owner when that skill has no route.

### Code review cap stop

- **Round 3 still has a CRITICAL or HIGH finding open** (`code-review-verdict` exit 3, `state.json` reads `cap_stop`): show the last merged report and the verdict's `blocking` list verbatim, name the round log, and stop; the fold step does not run. A re-invoke runs no further review: it asks the owner to accept the open findings (recorded as `owner_accepted` at the head of the report shown, then the fold runs) or to stop. When HEAD's tree moved after the cap stop or after the owner's accept (the owner fixed the finding by hand), the start block prints `CODE_REVIEW_NEXT=cap_stop_moved <R>` and the owner is asked to review the new head (a fresh state and a new 3-round budget) or to stop; `code-review.md`, "Review the new head", holds the block.
