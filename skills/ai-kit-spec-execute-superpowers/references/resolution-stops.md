# Step 2 reference: resolution stops

MANDATORY read when `resolve-injection` exits non-zero, prints the untrusted-config line, or
returns `$INJECTION_MODE` `no_candidate` or `quota_exhausted` (`SKILL.md` Step 2). Do NOT load it
when the result is `native` or `external_cli` with a clean stderr. Every `$VAR` is restored by the
scalar loader (`SKILL.md`, Step 0).

## Exit codes and the untrusted-config line

**If the block prints `resolve-injection exit 2`**: a malformed `review-spec.toml`, or an
entry with `purpose = "execute"` that can never execute (a custom `command` entry, grok, or a
claude pair that does not run natively). STOP and relay its stderr verbatim; any other non-zero
exit stops the same way.

**If its stderr prints `ai-kit-spec: ignoring untrusted project-local config <path>; review its
commands with ...`** (match on the whole `ai-kit-spec: ignoring untrusted project-local config` prefix), this resolution used the global
config only. Ask **once per run**: relay the line verbatim, show
`python3 "$TOOLS_PY" trust-local --cwd "$CWD" --show` (one JSON line per local reviewer with the
argv it would run, the prompt shown as `<prompt>`; writes nothing), and ask whether to trust it.
On yes, run `python3 "$TOOLS_PY" trust-local --cwd "$CWD"` and re-run this step's
`resolve-injection` before dispatching. On no, continue on the global-only result and do not ask
again this run, though the line repeats on every later resolution. Never trust unasked.

## `no_candidate` and `quota_exhausted`

- **`no_candidate`** — nothing configured for this task survives affinity/context narrowing (read
  `detail`, e.g. every `context_limit` is below the task's `required_context`). A curation gap, not
  quota. STOP this wave and report `detail`. Nothing is scheduled.
- **`quota_exhausted`** — read `any_quota_recoverable`
  (`python3 -c 'import json,sys; print(json.loads(sys.argv[1])["any_quota_recoverable"])' "$(cat "$RUN_DIR/INJECTION_JSON.json")"`).
  It, not `all_auth_failures`, is the gate. `reasons` holds `"quota"`, `"auth"`,
  `"billing_or_access"`, `"capacity"`, `"git_timeout"`, `"timeout"`, `"configuration"`,
  `"dispatch_unavailable"`, `"real_error"`, `"no_usable_dispatch"` (a prior wave's permanent
  failure), or a skip-route name (`"bad_model"`, `"review_only"`, `"not_installed"`,
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
