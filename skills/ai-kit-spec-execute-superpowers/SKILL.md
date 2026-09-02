---
name: ai-kit-spec-execute-superpowers
description: Resolves the best available, live-quota-checked model/CLI for each task in a superpowers-generated implementation plan, then delegates actual execution to superpowers:subagent-driven-development, injecting the resolved model/CLI at its implementer-dispatch point without bypassing that harness's TDD enforcement, agent-identity/resume, task review, fix-loop, or final-review pattern. Use when ai-kit-spec-execute detects a superpowers-generated plan (docs/superpowers/plans/*.md) being run under subagent-driven-development and needs to resolve a model/CLI for it; not for superpowers:executing-plans, which executes every task inline with no subagent-dispatch point to inject into.
---

# ai-kit-spec-execute-superpowers

**This skill never dispatches a task itself.** It resolves WHICH model/CLI a task should use, then
hands that resolution to `superpowers:subagent-driven-development` as an explicit input at its one
documented dispatch point — that skill keeps full ownership of TDD enforcement, fresh-subagent-
per-task, agent-identity/resume, task review, fix loops, and the final whole-branch review.
Delegating to it (rather than bypassing it) is deliberate: it carries pattern/TDD knowledge this
skill does not duplicate. **`superpowers:executing-plans` is out of scope** — confirmed from its
own SKILL.md, it runs every task directly in the controller's own session ("Follow each step
exactly", no `Agent`-tool dispatch anywhere), so there is no dispatch point here to inject a
resolution into.

## NEVER (index of scattered CRITICAL/HIGH findings)

Every item below is a recurrence guard for a bug this skill's history already produced once. Each
has a full inline callout at its point of use — this is a pointer index, not a replacement for them:

- **Never** persist `$EXCLUDED_KEYS_JSON` wholesale as `excluded_keys` — it is a working union of a
  permanent set and a same-wave set; doing so makes a temporary `"quota"` exclusion indistinguishable
  from a permanent one (Step 2; full mechanics in `references/state-management.md`).
- **Never** call `resolve-injection` with `--exclude-keys-json` alone, omitting
  `--excluded-reasons-json` — omitting it silently relabels every prior-wave permanent reason as
  `"no_usable_dispatch"` (Step 2; `references/state-management.md`).
- **Never** read `.["key"]`/`.["cli"]` off an injection result before checking `$INJECTION_MODE` —
  `quota_exhausted` and `no_candidate` carry neither field (Step 2).
- **Never** fold `$ESCALATION_EXCLUDE_JSON` into `$EXCLUDED_KEYS_JSON` — it marks healthy,
  never-tried candidates excluded only to enforce a capability floor, not failures (Step 3;
  `references/escalation.md`).
- **Never** let a fix-loop round's `dispatch-task` call overwrite `$REPORT_FILE` — `REPORT_MODE`
  must be `write` exactly once per task, `append` for every call after that (Step 3).
- **Never** parse the implementer's status (`DONE`/`DONE_WITH_CONCERNS`/`NEEDS_CONTEXT`/`BLOCKED`)
  out of `$REPORT_FILE`'s free-form content — read it from `$DISPATCH_RESULT_JSON["stdout"]` only
  (Step 3).
- **Never** schedule `CronCreate` when `any_quota_recoverable == False` or on `no_candidate` — no
  wait fixes a permanent failure; STOP and report instead (Step 2, Step 3).

## Step 0: Resolve the shim path

Same pattern `ai-kit-spec-execute-gsd/SKILL.md` uses for its own shim — take the FIRST existing of,
in order, in the same `Bash` call. Every branch is a real, executable check — HIGH finding: no
branch here is an instruction for the reading agent to manually substitute a path; a git-checkout
(this repo cloned or worktree-added, not plugin- or user-globally-installed) is resolved by
searching from the real git toplevel and, failing that, from the current working directory —
covering every supported installation shape (plugin install, user-global install, dev/worktree
checkout) with plain, portable shell:

```bash
for d in "${CLAUDE_PLUGIN_ROOT:+$CLAUDE_PLUGIN_ROOT/skills/ai-kit-spec-execute-superpowers}" \
         "$HOME/.claude/skills/ai-kit-spec-execute-superpowers" \
         "$(git rev-parse --show-toplevel 2>/dev/null)/skills/ai-kit-spec-execute-superpowers" \
         "$(pwd)/skills/ai-kit-spec-execute-superpowers"; do
  [ -n "$d" ] && [ -d "$d" ] && { SKILL_DIR="$d"; break; }
done
if [ -z "$SKILL_DIR" ]; then
  printf 'ERROR: could not resolve skills/ai-kit-spec-execute-superpowers under any known '
  printf 'installation shape (CLAUDE_PLUGIN_ROOT, ~/.claude/skills, git toplevel, or cwd) -- '
  printf 'STOP and tell the user rather than guessing a path.\n'
  exit 1
fi
SHIM="$SKILL_DIR/ai-kit-spec-superpowers.py"
for d in "${CLAUDE_PLUGIN_ROOT:+$CLAUDE_PLUGIN_ROOT/skills/ai-kit-spec-review}" \
         "$HOME/.claude/skills/ai-kit-spec-review" \
         "$(dirname "$SKILL_DIR")/ai-kit-spec-review"; do
  [ -d "$d" ] && { REVIEW_SKILL_DIR="$d"; break; }
done
if [ -z "$REVIEW_SKILL_DIR" ]; then
  printf 'ERROR: could not resolve skills/ai-kit-spec-review under any known installation shape '
  printf '(CLAUDE_PLUGIN_ROOT, ~/.claude/skills, or alongside this skill'\''s own resolved '
  printf 'directory) -- STOP and tell the user rather than guessing a path.\n'
  exit 1
fi
TOOLS_PY="$REVIEW_SKILL_DIR/ai-kit-spec.py"
printf 'SHIM=%s\nTOOLS_PY=%s\n' "$SHIM" "$TOOLS_PY"
```

**Record both printed lines as this wave's own literal values.** Every later `python3 $SHIM
<subcommand> ...` invocation uses this resolved `$SHIM` path. `$TOOLS_PY` resolves
`ai-kit-spec-review`'s own shim for its `cache-path --kind quota` subcommand.

**Every separate `Bash` tool call starts a fresh shell** — a variable set in one call is gone by
the next. Every `$VAR` below denotes the literal value most recently captured for it via `printf`,
re-substituted verbatim into every later command.

## Step 1: Load the plan under subagent-driven-development, unmodified

Follow that skill's own Setup exactly as written (workspace, ledger, plan read, pre-flight scan).
This adapter changes nothing about Setup — it only participates at "1. Dispatch the implementer".

`$CWD`, `$PLAN_FILE`, `$TASK_N`, and `$BRIEF_FILE` below are values that skill's own process
already holds at the point it dispatches each task's implementer — this adapter reads them, it
never invents or infers them.

## Step 2: Before each task's implementer dispatch — resolve the injection

**Before touching any exclusion-set variable, ask yourself:** is this a permanent exclusion
(auth/config/real error) or a same-wave-only one (quota)? What breaks for the user if this
candidate's exclusion reason is silently dropped or mislabeled on the next resume — does a
permanently-broken candidate get retried forever, or a temporarily-exhausted one get locked out
even after quota recovers? Getting this wrong doesn't crash loudly; it recurs silently, wave after
wave.

`$FIX_ROUND` and `$EXCLUDED_KEYS_JSON` are this task's own wave state, carried across every
`Bash` call for its lifetime (re-`printf`'d and re-substituted each time, per Step 0's own
convention). The full bookkeeping is a three-set split (`$PRIOR_EXCLUDED_KEYS_JSON`/
`$PRIOR_REASONS_JSON` for permanent exclusions carried across resumes, `$WAVE_TRIED_JSON`/
`$WAVE_REASONS_JSON` for this-wave-only failures, and the derived `$EXCLUDED_KEYS_JSON`/
`$EXCLUDED_REASONS_JSON` unions actually passed to `resolve-injection`) plus the resumable-state
JSON written when quota is recoverable.

**MANDATORY: before writing to, or reading, `$EXCLUDED_KEYS_JSON`, `$EXCLUDED_REASONS_JSON`, any
of the `$PRIOR_*`/`$WAVE_*` variables, or the resumable-state file, read
`references/state-management.md` in full.** It defines every variable's exact provenance, the
initial/resume values, why both `$PRIOR_REASONS_JSON` and `$WAVE_REASONS_JSON` must be merged into
`--excluded-reasons-json`, and the complete resumable-state write/read-back bash. Skipping it
reproduces a bug this skill's history already had once (a same-wave `"quota"` exclusion becoming
indistinguishable from a permanent one after a resume).

Immediately after that skill's own `scripts/task-brief PLAN_FILE N` produces the task's brief file
(`$BRIEF_FILE`), and before composing the dispatch:

```bash
QUOTA_PATH="$(python3 "$TOOLS_PY" cache-path --kind quota)"
EXCLUDED_REASONS_JSON="$(python3 -c 'import json,sys; a=json.loads(sys.argv[1]); a.update(json.loads(sys.argv[2])); print(json.dumps(a))' \
  "$PRIOR_REASONS_JSON" "$WAVE_REASONS_JSON")"
INJECTION_JSON="$(python3 "$SHIM" resolve-injection --cwd "$CWD" --task-file "$BRIEF_FILE" \
  --quota-path "$QUOTA_PATH" --exclude-keys-json "$EXCLUDED_KEYS_JSON" \
  --excluded-reasons-json "$EXCLUDED_REASONS_JSON")"
INJECTION_MODE="$(python3 -c 'import json,sys; print(json.loads(sys.argv[1])["mode"])' "$INJECTION_JSON")"
printf 'INJECTION_JSON=%s\nINJECTION_MODE=%s\n' "$INJECTION_JSON" "$INJECTION_MODE"
```

**`--excluded-reasons-json "$EXCLUDED_REASONS_JSON"` carries the FULL accumulated reasons
alongside the excluded keys, not just the keys** — the merge of `$PRIOR_REASONS_JSON` and
`$WAVE_REASONS_JSON`, never `$WAVE_REASONS_JSON` alone. Full rationale (two distinct bugs this
prevents) is in `references/state-management.md` — read it if this call's shape is ever in doubt.

**Record both printed lines, then branch on `$INJECTION_MODE` BEFORE reading any other field —
CRITICAL finding (recurrence guard): the `quota_exhausted` shape (`mode`, `task_type`, `tried`,
`reasons`, `all_auth_failures`, `any_quota_recoverable`) carries no `key`/`cli` at all** (Task 3's
`resolve-injection` `except QuotaExhaustedError` branch never writes one — there is no resolved
candidate to name), **and neither does the `"no_candidate"` mode (`mode`, `task_type`, `detail`,
`ladder_keys` — HIGH finding, Task 3's `except ValueError` branch)**. Unconditionally reading
`.["key"]` here, before checking `$INJECTION_MODE`, raised an uncaught `KeyError` on every genuine
quota-exhausted OR no-candidate resolution — exactly the cases this step exists to handle. Only
once `$INJECTION_MODE` is confirmed to be `native_claude` or `external_cli` (the "Otherwise" branch
below) does this SKILL.md read `key`/`cli`:

```bash
if [ "$INJECTION_MODE" != "quota_exhausted" ] && [ "$INJECTION_MODE" != "no_candidate" ]; then
  INJECTION_KEY="$(python3 -c 'import json,sys; print(json.loads(sys.argv[1])["key"])' "$INJECTION_JSON")"
  INJECTION_CLI="$(python3 -c 'import json,sys; print(json.loads(sys.argv[1]).get("cli") or "")' "$INJECTION_JSON")"
  printf 'INJECTION_KEY=%s\nINJECTION_CLI=%s\n' "$INJECTION_KEY" "$INJECTION_CLI"
fi
```

**If `INJECTION_MODE == "no_candidate"`** (HIGH finding) — a genuine curation gap: nothing
configured for this task can survive affinity/context narrowing at all (read `detail` in
`$INJECTION_JSON` for exactly why, e.g. every candidate's `context_limit` is below this task's
estimated `required_context`). This is not a quota-availability problem, so do **not** schedule
`CronCreate` — waiting an hour changes nothing here. STOP this wave and report `detail` to the
user, plainly, justified on this adapter's own terms exactly as the `any_quota_recoverable ==
False` branch below is (no ruling this adapter could make — trying a different already-configured
candidate — changes an outcome where none of them can run this task at all).

**Record `$INJECTION_KEY`/`$INJECTION_CLI` when this second block ran.** `$INJECTION_KEY` is this
exact candidate's own ladder key (e.g. `codex/terra`) — HIGH finding: distinct from
`$INJECTION_CLI`, which only carries the bare CLI name (e.g. `codex`) and is never itself a valid
`--exclude-keys-json` entry; using the wrong one there would silently fail to exclude anything and
let the ladder retry the same exhausted candidate indefinitely (see Step 3's mid-dispatch
`"quota"` branch below).

If `INJECTION_MODE == "quota_exhausted"`, read `any_quota_recoverable` from `$INJECTION_JSON`
(`python3 -c 'import json,sys; print(json.loads(sys.argv[1])["any_quota_recoverable"])' "$INJECTION_JSON"`)
and branch — HIGH finding: `any_quota_recoverable`, not `all_auth_failures`, is the real gate here.
`reasons` now carries seven typed values (`"quota"`, `"auth"`, `"timeout"`, `"configuration"`,
`"dispatch_unavailable"`, `"real_error"`, `"no_usable_dispatch"`) — only `"quota"` is ever worth an
hourly wait; every other reason is a real, permanent problem for that candidate regardless of
whether every OTHER candidate also failed for a different reason:

- **`any_quota_recoverable == False`** — every excluded candidate failed for a reason waiting never
  fixes (read `reasons` in `$INJECTION_JSON` for exactly which — e.g. `"auth"` needs login/
  entitlement, `"configuration"` needs a fixed `command` template, `"timeout"`/
  `"dispatch_unavailable"` needs the CLI itself investigated, `"real_error"` needs its own
  diagnosis). Do **not** schedule `CronCreate` — it would fire forever and never accomplish
  anything. STOP this wave and report to the user, plainly, which candidate key(s) need what fix,
  read straight off `reasons`. **This is not, verbatim, one of `subagent-driven-development`'s own
  four stop-and-ask conditions** (an irreversible/destructive operation, a security-sensitive
  action, a side effect outside this worktree, or a plan so broken every path forward is a guess —
  that skill's own "Rulings, not stalls" section) — none of the seven typed reasons above is any of
  those four. It is justified on this adapter's own terms instead: every configured candidate for
  this task is permanently unusable, and no ruling this adapter could make (picking a different
  candidate) changes that outcome — there is no path forward to rule past, only a real,
  human-actionable fix (credentials, a config template, an investigation) outside this session's
  reach. That is functionally the same shape as "a plan so broken every path forward is a guess,"
  so this adapter stops and asks on its own explicit authority, consistent with that skill's intent
  rather than claiming membership in its literal list.
- **`any_quota_recoverable == True`** — at least one candidate is a genuine, time-bound quota
  exhaustion, discovered before dispatch. Write resumable state and schedule an hourly
  `CronCreate` wake, then STOP this wave (do not dispatch this task).

  **MANDATORY: before writing the resumable-state JSON or scheduling `CronCreate`, read
  `references/state-management.md`'s "Resumable state" sections in full.** They give the exact
  bash — merging this call's `tried`/`reasons` into `$WAVE_TRIED_JSON`/`$WAVE_REASONS_JSON`,
  computing `$RESUME_EXCLUDED_KEYS_JSON` via the tested `resume-exclusions` subcommand (never
  inline set arithmetic), and the `STATE_JSON` shape passed to `write-resumable-state` — plus the
  read-back rules for a later resume (which variables restore into `$PRIOR_*` vs. get reset).
  Skipping this step and improvising the JSON risks silently losing a candidate's real failure
  reason or making a temporary quota exclusion look permanent.

  Schedule `CronCreate`: hourly interval, prompt `"re-check quota via probe-quota and, once
  restored, resume ai-kit-spec-execute-superpowers from $RESUME_STATE_PATH"`. `CronCreate` jobs are
  session-scoped (design spec §10) — they vanish if the session exits, only fire while the session
  is idle, and recurring jobs auto-expire after 7 days; tell the user this explicitly.

Otherwise, `$INJECTION_JSON` carries `mode`, `key`, `model`, `ladder_keys`, and (for
`external_cli`) `cli`, `effort`, `service_tier`. Proceed to Step 3.

## Step 3: Dispatch the implementer — apply the injection

**`mode == "native_claude"`:** unchanged from `subagent-driven-development`'s own process. Pass
`model` as the `Agent` tool's own `model` parameter, dispatch exactly as documented, and record
the returned agent identity — fix-loop rounds 1–3 resume this SAME live agent, exactly as that
skill's own "1. Dispatch the implementer" step already specifies. Nothing else about this mode
changes.

**`mode == "external_cli"`:** there is no live subagent to hold an identity for — a dispatched CLI
process exits when it finishes. `subagent-driven-development`'s own text already defines the
fallback for exactly this case ("If your harness cannot send another message to a live subagent,
dispatch a fresh implementer carrying the brief path, the report-file path, and the findings — the
report file is the persistent memory either way"). Every `external_cli` dispatch — the first
attempt AND every fix-loop round — uses that fallback path:

**Artifact paths — HIGH finding (recurrence guard): these are exact, plan-scoped, and created by a
real command, never left for the executing agent to improvise.** Derive all three from `$BRIEF_FILE`
(`subagent-driven-development`'s own `scripts/task-brief` already named it `…/task-N-brief.md`), and
create the scratch subdirectory they live in, once, before the first use:

```bash
TASK_STATE_DIR="$(dirname "$BRIEF_FILE")/.ai-kit-spec-execute-superpowers"
mkdir -p "$TASK_STATE_DIR"
PROMPT_FILE="$TASK_STATE_DIR/task-${TASK_N}-prompt.txt"
FORMAT_BLOCK_FILE="$TASK_STATE_DIR/task-${TASK_N}-format-block.md"
REPORT_FILE="${BRIEF_FILE%-brief.md}-report.md"
printf 'PROMPT_FILE=%s\nFORMAT_BLOCK_FILE=%s\nREPORT_FILE=%s\n' \
  "$PROMPT_FILE" "$FORMAT_BLOCK_FILE" "$REPORT_FILE"
```

`$REPORT_FILE` sits alongside `$BRIEF_FILE` itself (`…/task-N-brief.md` → `…/task-N-report.md`,
substituting the suffix), matching `subagent-driven-development`'s own naming convention exactly —
this is the SAME path that skill's own task review / re-review / ledger already expect to find the
task's report at, so no extra wiring is needed for later steps to pick it up. `$PROMPT_FILE`/
`$FORMAT_BLOCK_FILE` are pure scratch — this adapter's own working files, never read by
`subagent-driven-development` itself — so they live in a dedicated, clearly-named subdirectory next
to the brief rather than cluttering the task's own directory.

**`$REPORT_MODE`: `write` exactly once per task, `append` for every dispatch-task call after
that — CRITICAL finding.** Determine the INITIAL value the moment `$REPORT_FILE`'s path is known
(above), for BOTH a brand-new task and a resumed one — never assume `write` unconditionally, since
a resumed task may already have a partial report on disk from before the resume:

```bash
if [ -s "$REPORT_FILE" ]; then REPORT_MODE=append; else REPORT_MODE=write; fi
printf 'REPORT_MODE=%s\n' "$REPORT_MODE"
```

(`-s` is true when the file exists AND is non-empty — a brand-new task's report file does not exist
yet, so this correctly starts it at `write`; a resumed task whose report already has content from an
earlier round correctly continues at `append`, never re-triggering the CRITICAL finding this rule
exists to prevent.) Immediately after EVERY `dispatch-task` call returns from here on — success or
failure, whether or not this specific attempt's own output turns out to be a genuine implementer
report — set `REPORT_MODE=append` and never set it back to `write` for the rest of this task's
lifetime (mid-round quota-escalation retries below, and every later fix-loop round alike). This
guarantees `$REPORT_FILE` is a complete, ordered history that a `write` call can never silently
destroy — the exact failure mode the CRITICAL finding named (a fix-loop round's `dispatch-task` call
was overwriting the implementer's own report, and any earlier rounds' evidence, instead of appending
to it).

1. Compose the SAME dispatch prompt `subagent-driven-development`'s own implementer-prompt.md
   template calls for (brief path, context, report-file path, the "you do not dispatch subagents"
   contract) — write it to `$PROMPT_FILE` (path defined above). **The composed prompt must
   explicitly instruct the dispatched CLI to write its own detailed report directly to
   `$REPORT_FILE`** (it has write access to `$CWD`, being an execute-mode dispatch) **and return
   only a short status line separately** — this IS implementer-prompt.md's own real contract
   (detailed evidence to the report file, a short status separately, CRITICAL finding, recurrence
   guard): `dispatch-task` (Task 3) only falls back to capturing stdout as the report when the CLI
   provably didn't write to that path itself. **On the FIRST dispatch of a task, the prompt text
   instructs the CLI to WRITE `$REPORT_FILE`; on every dispatch after the first — every fix-loop
   round — the prompt text itself must instead instruct the CLI to APPEND its report to the END of
   `$REPORT_FILE`, never overwrite it (HIGH finding, distinct from `dispatch-task`'s own
   `--report-mode` flag).** `--report-mode append` only governs `dispatch-task`'s own
   stdout-fallback path — the case where the dispatched CLI did NOT write its own report — and
   deliberately never touches a file the CLI wrote to directly (Task 3). When the CLI DOES follow
   the prompt's instruction and writes its own report, `--report-mode` has no say over what the CLI
   itself does to that file; a prompt that told a round-2 CLI only "write your report to
   `$REPORT_FILE`" would have a fully compliant CLI overwrite round 1's evidence — the same failure
   `--report-mode` was built to close, relocated into the prompt text. Match
   `subagent-driven-development`'s own "every round... appends its fix report to the same report
   file" contract exactly: word the fix-loop-round instruction as "APPEND your detailed report to
   the end of `$REPORT_FILE` — do not overwrite its existing contents from earlier rounds." On a
   fix-loop round, also append the open findings verbatim to this same prompt, per that skill's own
   "Rounds 1–3 — resume" fallback text quoted above. Rounds 4–5 use the capability-escalation rule
   defined after the classification step below (never a plain ladder-exclusion walk, which cannot
   guarantee the required capability bump). **Increment `$FIX_ROUND` by one at the start of every
   fix-loop round, BEFORE evaluating the Rounds 4–5 `$FIX_ROUND >= 4` capability-escalation check
   below and before composing that round's prompt** (never for a same-round quota-escalation retry,
   which is not a new round) — this fixes the ordering ambiguity between the increment and the
   check (HIGH finding): round 4's own dispatch is the one where `$FIX_ROUND` first reads `4`, and
   that is exactly when capability escalation must first apply.
2. Write the implementer report-file's own required status contract (`DONE` /
   `DONE_WITH_CONCERNS` / `NEEDS_CONTEXT` / `BLOCKED`, per implementer-prompt.md's own "After
   Review Findings" section) to `$FORMAT_BLOCK_FILE` — this becomes `dispatch_execute`'s
   `format_block`, reinforcing that the dispatched CLI's own final output must match it.
3. Dispatch for real — `dispatch-task` already computes and applies tooling guidance internally
   (Task 3), so there is no separate tooling-preparation call to make first. **MEDIUM finding:
   `--timeout 900` is a fixed constant, deliberately — this adapter does not read a resolved
   candidate's own per-entry `timeout_tiers` override.** `timeout_tiers` (Global Constraints,
   optional-fields paragraph) is a real field `ai-kit-spec-config` writes, but nothing in
   `assemble_candidates` (Task 2) carries it onto a candidate dict, and no equivalent of
   `ai_kit_spec.config_io.resolve_timeout_tiers` is wired in here — propagating it would mean
   plumbing a per-candidate timeout through `resolve-injection`'s JSON, `dispatch-task`'s own
   arguments, and this call, which this plan treats as out of scope rather than a silent gap: a
   known-slow entry's `timeout_tiers` override exists for the GSD adapter's own review-dispatch
   timeout tiers (fix-round pressure that genuinely varies by round), a different axis than this
   adapter's fixed execute-mode heartbeat/timeout budget. A future revision that wants a
   known-slow execute candidate to get a longer budget here should add that plumbing explicitly
   rather than have it silently assumed to already work:

```bash
DISPATCH_RESULT_JSON="$(python3 "$SHIM" dispatch-task --injection-json "$INJECTION_JSON" \
  --prompt-file "$PROMPT_FILE" --target-dir "$CWD" --heartbeat-interval 60 --timeout 900 \
  --format-block-file "$FORMAT_BLOCK_FILE" --report-file "$REPORT_FILE" \
  --report-mode "$REPORT_MODE")"
printf 'DISPATCH_RESULT_JSON=%s\n' "$DISPATCH_RESULT_JSON"
```

Immediately after this call returns (per the rule above): `REPORT_MODE=append`.

`$REPORT_FILE` is named exactly as `subagent-driven-development`'s own convention requires (brief
`…/task-N-brief.md` → report `…/task-N-report.md`). **`dispatch-task` never overwrites an
implementer-authored report with captured stdout (CRITICAL finding, recurrence guard)**: when the
dispatched CLI followed point 1's instruction and wrote its own detailed report directly to
`$REPORT_FILE`, that on-disk content is left completely untouched — `dispatch-task` detects this
by comparing the file's content before and after the dispatch call. Only when the file is provably
unchanged (the CLI never wrote to it) does `dispatch-task` fall back to writing/appending the
captured stdout, with a leading marker line so a fallback is never mistaken for a genuine
implementer report. Either way, every later step (task review, fix loop) reads `$REPORT_FILE`
exactly as it would read a native subagent's own report, its history intact across every round.

4. Classify the outcome before treating it as the implementer's report:

```bash
CLASSIFICATION="$(python3 "$SHIM" classify-dispatch-failure --dispatch-result-json "$DISPATCH_RESULT_JSON")"
```

- `"ok"` — proceed exactly as `subagent-driven-development`'s own "2. Handle the report" step
  describes, but **read the short status line from `$DISPATCH_RESULT_JSON`'s own `stdout` field,
  never from `$REPORT_FILE`'s content — CRITICAL finding (status-channel mismatch).** The prompt
  composed in point 1 above instructs the dispatched CLI to write its DETAILED evidence directly to
  `$REPORT_FILE` and return only the short `DONE`/`DONE_WITH_CONCERNS`/`NEEDS_CONTEXT`/`BLOCKED`
  contract SEPARATELY (implementer-prompt.md's own real contract, quoted above) — that separate
  reply is exactly `$DISPATCH_RESULT_JSON["stdout"]`, the captured subprocess output, not the report
  file. `$REPORT_FILE` is free-form detailed evidence with no guaranteed status-line position or
  format (and, per `dispatch-task`'s CLI-writes-its-own-report path, `dispatch-task` never even
  inspects its content) — parsing a status keyword out of it is unreliable at best and silently
  wrong whenever the implementer's prose happens to mention one of the four words in passing.
  Extract it with:

```bash
STATUS_LINE="$(python3 -c 'import json,sys; print(json.loads(sys.argv[1])["stdout"])' "$DISPATCH_RESULT_JSON")"
STATUS="$(printf '%s\n' "$STATUS_LINE" | rg -o '\b(DONE_WITH_CONCERNS|NEEDS_CONTEXT|BLOCKED|DONE)\b' | tail -1)"
```

  (MEDIUM finding: `rg -o`, not `grep -oE` — `TOOL_AVAILABILITY` already confirms `rg: true` for
  every supported environment this plan targets, and `rg`'s default regex engine is already
  extended/Perl-compatible-enough for this alternation with no `-E`-equivalent flag needed.
  `DONE_WITH_CONCERNS`/`NEEDS_CONTEXT`/`BLOCKED` are matched before the bare `DONE` alternative so
  the alternation cannot short-circuit on the `DONE` prefix of a longer status word; `tail
  -1` takes the dispatched CLI's own FINAL status line if its reply echoes the format-block's
  allowed-values list before stating its actual status.) If `$STATUS` is empty — the dispatched CLI
  never emitted a recognizable status word in `stdout` — treat this exactly like `BLOCKED`
  (`subagent-driven-development`'s own stop-and-ask path) rather than guessing; do not fall back to
  scanning `$REPORT_FILE` for one.
- `"quota"` — this specific candidate went quota-exhausted mid-dispatch (not discovered ahead of
  time in Step 2, but a real, late signal — design spec §12). **CRITICAL finding (recurrence
  guard): record this as a wave-tried key WITH its `"quota"` reason — never fold it into
  `$EXCLUDED_KEYS_JSON` directly with no reason attached**, or a later resumable-state persist
  (Step 2) would have no way to tell this temporary, mid-dispatch exclusion apart from a genuinely
  permanent one, and it would never become eligible again after a resume — the exact bug a prior
  revision's fix (the `resume-exclusions` subcommand itself) was meant to close, recurring one
  layer up:

```bash
WAVE_TRIED_JSON="$(python3 -c 'import json,sys; print(json.dumps(sorted(set(json.loads(sys.argv[1])) | {sys.argv[2]})))' \
  "$WAVE_TRIED_JSON" "$INJECTION_KEY")"
WAVE_REASONS_JSON="$(python3 -c 'import json,sys; d=json.loads(sys.argv[1]); d[sys.argv[2]]="quota"; print(json.dumps(d))' \
  "$WAVE_REASONS_JSON" "$INJECTION_KEY")"
EXCLUDED_KEYS_JSON="$(python3 -c 'import json,sys; print(json.dumps(sorted(set(json.loads(sys.argv[1])) | set(json.loads(sys.argv[2])))))' \
  "$PRIOR_EXCLUDED_KEYS_JSON" "$WAVE_TRIED_JSON")"
```

  (`$INJECTION_KEY` is this exact candidate's own ladder key, e.g. `codex/terra` — HIGH finding:
  never `$INJECTION_CLI`, which only carries the bare CLI name, e.g. `codex`, and would silently
  exclude nothing, letting the ladder retry the same exhausted candidate indefinitely.) Re-run Step
  2's `resolve-injection` with the recomputed `--exclude-keys-json "$EXCLUDED_KEYS_JSON"` — this
  reuses the SAME invocation shape, including `--excluded-reasons-json "$EXCLUDED_REASONS_JSON"`
  (recomputed the same way as Step 2's own — the merge of `$PRIOR_REASONS_JSON` with the
  now-updated `$WAVE_REASONS_JSON`, so this candidate's freshly-recorded `"quota"` reason above is
  included alongside every earlier-wave permanent reason), **and,
  when this mid-dispatch quota failure happened on a Rounds 4–5 capability-escalated candidate
  (`$ESCALATION_EXCLUDE_JSON` is non-empty this round), also `--escalation-excluded-keys-json
  "$ESCALATION_EXCLUDE_JSON"` — otherwise this retry would silently drop the capability floor that
  round established and could hand back a same-or-weaker candidate the Rounds 4–5 rule below already
  ruled out** — which now already carries this exact candidate's own freshly-recorded `"quota"`
  reason (updated above) — and retry Step 3 with the newly-resolved injection — never re-dispatch the
  same candidate blind. Excluding it from `$EXCLUDED_KEYS_JSON` (the live resolve-injection input) is
  intentionally immediate and unconditional within this SAME wave — a candidate that just failed mid-dispatch
  should not be retried again a moment later — but its `"quota"` reason travels with it in
  `$WAVE_REASONS_JSON`, so if this wave later needs to persist resumable state, `resume-exclusions`
  still drops it and it is eligible again on resume, exactly like a candidate Step 2 itself caught as
  quota-exhausted ahead of time. **CRITICAL finding (recurrence guard): even if this wave's
  `EXCLUDED_KEYS_JSON` now covers every configured candidate — a single-candidate ladder tried once,
  or several exclusions in a row covering the whole roster — `resolve-injection` no longer crashes**
  (a prior revision's `build_dispatch_injection` raised an uncaught `ValueError` in exactly this
  case, mistaking "every candidate already excluded" for "nothing configured at all"); it reports a
  controlled `quota_exhausted` result instead, using `--excluded-reasons-json` to recover every
  already-known reason. If re-resolution itself now reports `quota_exhausted`, follow Step 2's own
  `any_quota_recoverable`/resumable-state/`CronCreate` branch (which merges this call's own
  `tried`/`reasons` into `$WAVE_TRIED_JSON`/`$WAVE_REASONS_JSON` too, so nothing discovered here is
  lost).
- `"real_error"` — never silently retried (design spec §12's explicit rule). Treat exactly as
  `subagent-driven-development`'s own `BLOCKED` handling: assess the blocker (more context and
  retry, a capability-escalated candidate per the Rounds 4–5 rule below, break the task down, or
  rule on a plan defect) — never force the same candidate to retry unchanged.

**Rounds 4–5 capability escalation (`mode == "external_cli"` only).** Applied at the START of point
1 above, immediately AFTER that round's `$FIX_ROUND` increment (never before it — the check reads
the POST-increment value) and BEFORE composing that round's prompt, whenever `$FIX_ROUND >= 4`
(`subagent-driven-development`'s own fix-loop, unmodified per Step 4, has re-entered this dispatch
point for the 4th or 5th time on this task) AND the mode in play is `external_cli` (a
`native_claude` fix-loop round is unchanged — see that mode's own paragraph above; its round 4/5
model-tier bump is that skill's own `Agent`-tool dispatch judgment, with no ladder involved).
`subagent-driven-development` requires rounds 4–5 to "dispatch a fresh implementer on a MORE
CAPABLE model" — a genuine capability bump, not merely a different candidate. Naively excluding
the stuck candidate's key and letting `resolve-injection` re-walk the ladder does NOT guarantee
this: the next surviving candidate could easily be LESS capable than the one that got stuck.

**MANDATORY: before computing `$ESCALATION_EXCLUDE_JSON` or re-running `resolve-injection` with
`--escalation-excluded-keys-json`, read `references/escalation.md` in full.** It defines the
ladder-position capability-tier proxy this adapter uses (no dedicated capability-tier field exists
in config today), the exact `ESCALATION_EXCLUDE_JSON` computation (including the `{stuck}`-union
and `len(ladder)`-fallback edge cases), why `$ESCALATION_EXCLUDE_JSON` is passed only via
`--escalation-excluded-keys-json` and never folded into `$EXCLUDED_KEYS_JSON`, and how to branch
if the re-resolution itself reports `quota_exhausted` or `no_candidate` (mirrors Step 2's
`any_quota_recoverable` branch, with one MEDIUM-finding wrinkle: an escalation-only exclusion
produces empty `reasons`/`detail`, so report the excluded ladder keys by name instead). Skipping
this reference risks a round 5 that silently regresses to a same-or-weaker candidate round 4
already ruled out.

## Step 4: Task review, fix loop, final review — unaffected

Whichever mode Step 3 used, `subagent-driven-development`'s own "3. Review the task" and "4. The
fix loop" proceed completely unmodified from here: `scripts/review-package`, the task reviewer
dispatch, the fix-loop round structure (1–5), and the final whole-branch review all operate on
`$REPORT_FILE` and the real commits the dispatch produced, with zero awareness of which mode
produced them. This skill's own scope ends at Step 3 — it never touches review, fix-loop
adjudication, or the ledger directly.
