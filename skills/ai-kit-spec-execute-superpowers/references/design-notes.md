# Design notes: why the SKILL.md rules are shaped this way

Background for `SKILL.md`. Nothing here is a step to run; read it when a rule looks arbitrary and
you are tempted to bend it.

## Why `superpowers:executing-plans` is out of scope

Its own SKILL.md runs every task in the controller's session ("Follow each step exactly", no
`Agent`-tool dispatch), so there is no dispatch point to inject a resolution into.

## Why the Step 0 resolution has git-toplevel and cwd candidates

A dev or worktree checkout has no plugin root and is not under `~/.claude/skills`. Searching the
real git toplevel and then the cwd keeps every candidate an executable check, so the agent never
has to substitute a path by hand.

## Why mode is checked before `key`/`runtime`

The `quota_exhausted` shape (`mode`, `task_type`, `tried`, `reasons`, `all_auth_failures`,
`any_quota_recoverable`) and the `no_candidate` shape (`mode`, `task_type`, `detail`,
`ladder_keys`) carry no `key`/`runtime`. Reading `["key"]` first raised `KeyError` on exactly the
cases Step 2 exists to handle.

`native` and `external_cli` are the two dispatch modes of one routing decision, never stored
fields. `native` means this host runs the pair itself (today only Claude Code selects a model per
call; every other host runs only its session default natively). `external_cli` means a subprocess
through the supervised runner, including a route of `unverified`: the model list was unavailable,
so neither side checks the model before the CLI runs. A custom entry (a `command` and no
`runtime`) is the one exception to that runner path, and only in review: exec mode never runs
it (`purpose = "execute"` makes `resolve-injection` exit 2; otherwise it is skipped as
`review_only`). In review the fixed-argv custom launcher runs it on the same
supervision core.

## Why `$INJECTION_KEY`, never `$INJECTION_RUNTIME`, goes into exclusions

`$INJECTION_KEY` is the ladder key (`codex/terra`). `$INJECTION_RUNTIME` is the runtime id
(`codex`), which matches no ladder key, so excluding it excludes nothing and the ladder retries the
same exhausted candidate forever.

## Why the permanent-failure stop is this adapter's own call

`subagent-driven-development`'s "Rulings, not stalls" section lists four stop-and-ask conditions:
an irreversible or destructive operation, a security-sensitive action, a side effect outside the
worktree, or a plan so broken every path forward is a guess. None of the typed failure reasons is
literally one of those. The adapter stops anyway because no configured candidate is usable for this task
in a way an hourly wake can fix (a `"capacity"` failure may still clear by itself): no ruling it could make (another candidate) changes that, and the fix
(credentials, a config template, an investigation) is outside the session. That is the same shape
as the fourth condition, so the stop is consistent with that skill's intent without claiming
membership in its list. The same reasoning covers `no_candidate`.

## Report file: why `write` once, then `append`

A fix-loop round's `dispatch-task` call once overwrote the implementer's report and every earlier
round's evidence. Two separate controls close this:

- `--report-mode` governs only `dispatch-task`'s stdout fallback, used when the CLI did not write
  the report itself. `dispatch-task` compares the file before and after the call and never
  overwrites a file the CLI wrote; a fallback write carries a leading marker line.
- The prompt text governs what a compliant CLI does to the file. A round-2 prompt that only says
  "write your report to `$REPORT_FILE`" makes the CLI overwrite round 1, so every prompt after the
  first must say APPEND.

The initial mode comes from `[ -s "$REPORT_FILE" ]` because a resumed task may already have a
partial report on disk.

## Why the status comes from `stdout`, never the report file

The implementer contract is: detailed evidence in the report file, a short status reply returned
separately. That reply is `$DISPATCH_RESULT_JSON["stdout"]`. The report is free-form prose, and
`dispatch-task` never inspects it when the CLI wrote it, so scanning it for a status word misfires
whenever the prose mentions one in passing. In the extraction regex, the longer words come before
`DONE` so the alternation cannot stop at the `DONE` prefix, and `tail -1` takes the final status
when the reply echoes the allowed-values list first. `rg` is used because tool detection already
confirms it on every supported environment.

## Why exec confinement differs by runtime

Codex runs under `--codex-sandbox workspace-write`, so its writes stay inside the target dir plus
`/tmp` and `$TMPDIR`, which workspace-write always allows; whether `.git` is writable under that
sandbox is unverified. Every other exec target runs with full permissions and gets only the
soft-confinement sentence, which is guidance, not a boundary. `claude` is review-only and never an
exec target. pi exec uses the runner's pi formula, verified by its hermetic self-test only until
Phase 22.

## Why `--timeout 900` is a fixed constant

`ai-kit-spec-config` can write a per-entry `timeout_tiers`, but `assemble_candidates` does not
carry it onto a candidate dict, and nothing like `ai_kit_spec.config_io.resolve_timeout_tiers` is
wired into this adapter. Honoring it would mean threading a per-candidate timeout through
`resolve-injection`'s JSON, `dispatch-task`'s arguments and the Step 3 call. That per-entry
override exists for review dispatch; this adapter's execute budget is a separate axis. Add the
plumbing explicitly if a known-slow execute candidate needs more time; do not assume it works.

## Why a mid-dispatch `"quota"` failure is recorded with its reason

Folding the key straight into `$EXCLUDED_KEYS_JSON` with no reason makes a temporary exclusion
look permanent once resumable state is persisted, so the candidate never comes back after quota
recovers. Recording it in `$WAVE_TRIED_JSON`/`$WAVE_REASONS_JSON` lets `resume-exclusions` drop it
on resume. Within the same wave the exclusion is immediate, so the candidate is not retried a
moment later.

When the exclusions cover every candidate (a one-entry ladder tried once, or several failures in a
row), `resolve-injection` reports a controlled `quota_exhausted` result and recovers the known
reasons from `--excluded-reasons-json`. An older version raised `ValueError` here, mistaking
"every candidate excluded" for "nothing configured".

## Why `$FIX_ROUND` increments before the escalation check

Round 4's own dispatch is the first one where `$FIX_ROUND` reads `4`, and that is when capability
escalation must first apply. Incrementing after the check would delay escalation by one round. A
same-round quota retry is not a new round and does not increment.
