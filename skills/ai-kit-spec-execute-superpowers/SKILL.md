---
name: ai-kit-spec-execute-superpowers
description: Resolves the best available, live-quota-checked model/CLI for each task in a superpowers-generated implementation plan, then delegates actual execution to superpowers:subagent-driven-development, injecting the resolved model/CLI at its implementer-dispatch point without bypassing that harness's TDD enforcement, agent-identity/resume, task review, fix-loop, or final-review pattern. Not for superpowers:executing-plans -- that skill executes every task inline with no subagent-dispatch point to inject into. Use when ai-kit-spec-execute detects a superpowers-generated plan (docs/superpowers/plans/*.md) being run under subagent-driven-development and needs to resolve a model/CLI for it.
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

`$FIX_ROUND` and `$EXCLUDED_KEYS_JSON` are this task's own wave state, carried across every
`Bash` call for its lifetime (re-`printf`'d and re-substituted each time, per Step 0's own
convention) — HIGH finding: resumable state must capture the complete excluded-candidate set and
which fix round a resume lands on, not just the ladder position at the moment of exhaustion.

**CRITICAL finding (recurrence guard): `$EXCLUDED_KEYS_JSON` is a working union of TWO
differently-provenanced sets — never persist it wholesale as `excluded_keys`, or a same-wave
`"quota"` exclusion becomes indistinguishable from a genuinely permanent one and is never
eligible again after a resume, exactly the bug `resume-exclusions` (Task 3) was built to
prevent.** Track the two sets separately for the task's whole lifetime:

- `$PRIOR_EXCLUDED_KEYS_JSON` — the genuinely permanent exclusion set this task resumed with (or
  `'[]'` for a brand-new task). This is `compute_resume_exclusions`' own OUTPUT from a previous
  wave, already reason-filtered — every key in it stayed excluded because its reason was
  something other than `"quota"`. Never add to this set directly; it only changes across a
  resume (below).
- `$PRIOR_REASONS_JSON` — the `{key: reason}` map for every key in `$PRIOR_EXCLUDED_KEYS_JSON`,
  restored alongside it from the SAME persisted `$RESUME_STATE_PATH` (`STATE_JSON` already writes
  this wave's own `reasons` field — Step 2's resumable-state block below — so restoring it costs
  nothing new to persist). `'{}'` for a brand-new task. **Important finding, recurrence guard:
  without this, a resumed wave that later hits `quota_exhausted` again has no way to recover WHY
  an old permanent exclusion failed — `cli.py`'s own `_emit_quota_exhausted` falls back every
  excluded key missing from `--excluded-reasons-json` to the generic `"no_usable_dispatch"`,
  silently replacing a real `"auth"` or `"configuration"` reason with a meaningless one in the
  user-facing report Step 2 instructs reading.** Never add to this set directly; it only changes
  across a resume (below).
- `$WAVE_TRIED_JSON` / `$WAVE_REASONS_JSON` — every candidate key tried and rejected DURING THIS
  LIVE WAVE (both a `resolve-injection` call's own `tried`/`reasons` when it reports
  `quota_exhausted`, and a mid-dispatch `"quota"` failure caught in Step 3), paired with the
  reason each one failed for. Reset to `'[]'`/`'{}'` at the very first dispatch of a NEW task AND
  on every resume (a resume already folded any earlier wave's non-quota reasons into
  `$PRIOR_EXCLUDED_KEYS_JSON`/`$PRIOR_REASONS_JSON` via `resume-exclusions`, so the new wave starts
  with a clean slate and re-discovers THIS wave's own reasons fresh rather than replaying stale
  ones — `$PRIOR_REASONS_JSON` is a separate, never-reset channel for the OLD wave's reasons,
  merged back in only at the point of calling `resolve-injection`, below).
- `$EXCLUDED_KEYS_JSON` — recomputed as the UNION of `$PRIOR_EXCLUDED_KEYS_JSON` and
  `$WAVE_TRIED_JSON` every time either input changes; this is the ONLY one ever passed to
  `resolve-injection --exclude-keys-json`. Because it is a derived value, never persist
  it directly either — always recompute it, and always persist `$PRIOR_EXCLUDED_KEYS_JSON` /
  `$WAVE_TRIED_JSON` / `$WAVE_REASONS_JSON` (or their `resume-exclusions` output) instead. **This is
  a two-set union, never three** — Step 3's Rounds 4–5 capability-escalation rule (below) tracks a
  THIRD, unrelated set, `$ESCALATION_EXCLUDE_JSON` (healthy, never-attempted candidates excluded
  purely to enforce that round's capability floor, never a failure), and passes it to
  `resolve-injection` through its own separate `--escalation-excluded-keys-json` argument — it never
  joins this union and `$EXCLUDED_KEYS_JSON` is never reassigned to include it.
- `$EXCLUDED_REASONS_JSON` — recomputed the same way, as the MERGE of `$PRIOR_REASONS_JSON` and
  `$WAVE_REASONS_JSON` (`$WAVE_REASONS_JSON` wins on key collision, being the freshest information)
  every time either input changes; this is the ONLY one ever passed to `resolve-injection
  --excluded-reasons-json`. Like `$EXCLUDED_KEYS_JSON`, never persist it directly — recompute it at
  the point of each `resolve-injection` call from its two real inputs instead.

At the very first dispatch of a NEW task: `FIX_ROUND=0`, `PRIOR_EXCLUDED_KEYS_JSON='[]'`,
`PRIOR_REASONS_JSON='{}'`, `WAVE_TRIED_JSON='[]'`, `WAVE_REASONS_JSON='{}'`, and
`EXCLUDED_KEYS_JSON='[]'`. Resuming from a persisted `$RESUME_STATE_PATH` (below): read `fix_round`
into `$FIX_ROUND`, the persisted `excluded_keys` into `$PRIOR_EXCLUDED_KEYS_JSON`, and the persisted
`reasons` into `$PRIOR_REASONS_JSON` (these are already permanent — `resume-exclusions` dropped
every quota-only key, and `reasons` carries the real reason for every key that survived that drop,
before persisting them); reset `$WAVE_TRIED_JSON='[]'` and `$WAVE_REASONS_JSON='{}'` for the fresh
wave; set `EXCLUDED_KEYS_JSON="$PRIOR_EXCLUDED_KEYS_JSON"`.

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

**`--excluded-reasons-json "$EXCLUDED_REASONS_JSON"` — CRITICAL finding, recurrence guard.** Every
`resolve-injection` call in this SKILL.md passes the FULL accumulated reasons alongside its
excluded keys, not just the keys — this means merging `$PRIOR_REASONS_JSON` (restored on resume,
covering keys excluded in an EARLIER wave) with `$WAVE_REASONS_JSON` (discovered so far THIS wave),
never `$WAVE_REASONS_JSON` alone. Two distinct bugs this closes: (1) without `$WAVE_REASONS_JSON`
at all, a re-resolution call whose `--exclude-keys-json` already covers every configured candidate
for this task would have no way to report a real `quota_exhausted` outcome (its own ladder walk
never starts, so it discovers no reasons of its own), and a re-resolution call that DOES find a
fresh `quota_exhausted` result would lose every earlier-excluded candidate's own reason from
`any_quota_recoverable`'s computation; (2) without also merging in `$PRIOR_REASONS_JSON` on a
resumed wave, every key in `$PRIOR_EXCLUDED_KEYS_JSON` is present in `--exclude-keys-json` but
absent from `--excluded-reasons-json` — `cli.py`'s own `_emit_quota_exhausted` then falls each one
back to the generic `"no_usable_dispatch"` (`cli.py`'s own `merged_reasons.setdefault(key,
"no_usable_dispatch")`), silently discarding a real `"auth"`/`"configuration"`/etc. reason a PRIOR
wave already discovered and persisted for exactly this purpose.

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
  `CronCreate` wake, then STOP this wave (do not dispatch this task):

```bash
PROJECT_KEY="$(python3 -c "import hashlib,sys; print(hashlib.sha256(sys.argv[1].encode()).hexdigest()[:12])" "$CWD")"
RESUME_STATE_PATH="$(dirname "$QUOTA_PATH")/superpowers-resume-${PROJECT_KEY}-task-${TASK_N}.json"
# CRITICAL finding (recurrence guard, second layer): fold THIS resolve-injection call's own
# tried/reasons into the wave-accumulated sets BEFORE computing what to persist. Without this
# merge, a candidate excluded earlier in the SAME wave purely because of Step 3's mid-dispatch
# "quota" branch (below) would never have its reason recorded here at all -- persisting it would
# either drop it silently (wrong: it really was tried and failed, the harness should know) or, if
# folded in unlabeled via $EXCLUDED_KEYS_JSON directly, get treated as permanent regardless of its
# real (temporary) reason. Merging into $WAVE_TRIED_JSON/$WAVE_REASONS_JSON keeps every wave-tried
# key's real reason attached no matter which step (Step 2 or Step 3) discovered it.
WAVE_TRIED_JSON="$(python3 -c 'import json,sys; print(json.dumps(sorted(set(json.loads(sys.argv[1])) | set(json.loads(sys.argv[2])["tried"]))))' \
  "$WAVE_TRIED_JSON" "$INJECTION_JSON")"
WAVE_REASONS_JSON="$(python3 -c 'import json,sys; a=json.loads(sys.argv[1]); a.update(json.loads(sys.argv[2])["reasons"]); print(json.dumps(a))' \
  "$WAVE_REASONS_JSON" "$INJECTION_JSON")"
# CRITICAL finding (recurrence guard): compute the PERSISTED exclusion set via the tested
# resume-exclusions subcommand, never inline, untested set arithmetic -- a "quota" reason is
# deliberately dropped so the candidate is eligible again once quota genuinely recovers; only
# permanent reasons (auth/timeout/configuration/dispatch_unavailable/no_usable_dispatch/
# real_error) are carried forward into the persisted excluded_keys set. `--prior-excluded-keys-json`
# is `$PRIOR_EXCLUDED_KEYS_JSON` (the genuinely permanent set this wave started with) -- NEVER
# `$EXCLUDED_KEYS_JSON`, which is a derived union and would re-feed already-permanent keys back in
# as if they were freshly-tried (harmless) but, worse, would offer no way to tell a same-wave
# "quota" entry apart from a permanent one, since $EXCLUDED_KEYS_JSON carries no reasons at all.
RESUME_EXCLUDED_KEYS_JSON="$(python3 "$SHIM" resume-exclusions --tried-json "$WAVE_TRIED_JSON" \
  --reasons-json "$WAVE_REASONS_JSON" --prior-excluded-keys-json "$PRIOR_EXCLUDED_KEYS_JSON")"
# Important finding, recurrence guard: the persisted "reasons" field must carry PRIOR_REASONS_JSON
# merged with WAVE_REASONS_JSON, never WAVE_REASONS_JSON alone -- compute_resume_exclusions (above)
# returns ONLY keys, not reasons, so a key carried forward unchanged from $PRIOR_EXCLUDED_KEYS_JSON
# (permanent from an EARLIER wave, never re-tried this wave) would otherwise have no entry in the
# freshly-written "reasons" field at all. Persisting WAVE_REASONS_JSON alone works for a task's
# FIRST resume (the reader falls back to "no_usable_dispatch" harmlessly, since $PRIOR_REASONS_JSON
# was still '{}' then) but silently loses real reasons on every resume AFTER the first, once
# $PRIOR_REASONS_JSON itself is non-empty and needs to be carried forward in what gets persisted.
PERSIST_REASONS_JSON="$(python3 -c 'import json,sys; a=json.loads(sys.argv[1]); a.update(json.loads(sys.argv[2])); print(json.dumps(a))' \
  "$PRIOR_REASONS_JSON" "$WAVE_REASONS_JSON")"
STATE_JSON="$(python3 -c '
import json, sys
print(json.dumps({"framework": "superpowers", "plan_path": sys.argv[1], "task_index": sys.argv[2],
                   "fix_round": int(sys.argv[3]), "excluded_keys": json.loads(sys.argv[4]),
                   "tried": json.loads(sys.argv[5]), "reasons": json.loads(sys.argv[6])}))' \
  "$PLAN_FILE" "$TASK_N" "$FIX_ROUND" "$RESUME_EXCLUDED_KEYS_JSON" "$WAVE_TRIED_JSON" "$PERSIST_REASONS_JSON")"
python3 "$SHIM" write-resumable-state --path "$RESUME_STATE_PATH" --state-json "$STATE_JSON"
```

Schedule `CronCreate`: hourly interval, prompt `"re-check quota via probe-quota and, once
restored, resume ai-kit-spec-execute-superpowers from $RESUME_STATE_PATH"`. `CronCreate` jobs are
session-scoped (design spec §10) — they vanish if the session exits, only fire while the session
is idle, and recurring jobs auto-expire after 7 days; tell the user this explicitly. **On resume**,
read `fix_round` back into `$FIX_ROUND`, `excluded_keys` back into `$PRIOR_EXCLUDED_KEYS_JSON`, and
`reasons` back into `$PRIOR_REASONS_JSON` (never directly into `$EXCLUDED_KEYS_JSON`/
`$WAVE_REASONS_JSON` — see Step 0's state-variable split above; `reasons` here is already the
merged `$PERSIST_REASONS_JSON` this same block just wrote, so restoring it recovers every
permanently-excluded key's real reason, including one from a wave BEFORE the one that most
recently persisted — Important finding, recurrence guard: without restoring this, a resumed wave
that later hits `quota_exhausted` again would have no way to recover WHY an old permanent exclusion
failed, and `cli.py`'s own `_emit_quota_exhausted` would silently relabel it `"no_usable_dispatch"`
in the user-facing report), reset `$WAVE_TRIED_JSON='[]'`/`$WAVE_REASONS_JSON='{}'` for the fresh
wave, and recompute `EXCLUDED_KEYS_JSON="$PRIOR_EXCLUDED_KEYS_JSON"` before re-entering this Step —
CRITICAL finding (recurrence guard): the persisted `excluded_keys` set contains ONLY permanent
exclusions (`compute_resume_exclusions` already dropped every merely-`"quota"`-reason key, including
one discovered mid-dispatch in Step 3), so a candidate that was genuinely quota-exhausted at persist
time — whether discovered here in Step 2 or mid-dispatch in Step 3 — is automatically eligible
again here — the very next `resolve-injection` call always refreshes quota fresh, giving it a real
chance to have recovered, rather than being permanently locked out by its own earlier exhaustion
event. The walk continues exactly where it left off otherwise: never re-trying an
already-permanently-excluded candidate and never losing which fix round the task was on.

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

**Rounds 4–5 capability escalation (`mode == "external_cli"` only) — CRITICAL finding.** Applied at
the START of point 1 above, immediately AFTER that round's `$FIX_ROUND` increment (never before it
— see point 1's ordering rule above; the check reads the POST-increment value) and BEFORE composing
that round's prompt, whenever `$FIX_ROUND >= 4` (i.e. `subagent-driven-development`'s own fix-loop,
unmodified per Step 4 below, has re-entered this dispatch point for the 4th or 5th time on this
task) AND the mode in play is `external_cli` (a
`native_claude` fix-loop round is unchanged — see that mode's own paragraph above; its round 4/5
model-tier bump is that skill's own `Agent`-tool dispatch judgment, made fresh each round exactly as
`subagent-driven-development`'s own Model Selection section already specifies, with no ladder
involved). `subagent-driven-development`'s own Model Selection section requires rounds 4–5 to
"dispatch a fresh implementer on a MORE CAPABLE model" — a genuine capability bump, not merely a
different one.
Naively excluding the stuck candidate's key and letting `resolve-injection` re-walk the ladder does
NOT guarantee this: the next surviving candidate by quota/affinity/context ranking could easily be
LESS capable than the one that got stuck. Today's config schema has no dedicated capability-tier
field (Global Constraints — `strength` is free text, not yet consumed by any resolution logic), so
this adapter uses the ladder's own established preference ordering (`policy.ladder`, authored
most-preferred-first — the same convention the GSD adapter's ladder walk already relies on, and the
same ordering `resolve-injection` already walks best-first) as the capability-tier proxy: only a
candidate ranked STRICTLY ABOVE the stuck candidate's own ladder position — never at the SAME
position, and never the stuck candidate itself — counts as a real capability bump. `resolve-
injection`'s JSON output (every mode, including `quota_exhausted`) now carries `ladder_keys` — the
full ranked candidate-key list `assemble_candidates` produced, BEFORE any `--exclude-keys-json`
filtering (Task 3, CRITICAL finding fix) — precisely so this computation is possible from data this
SKILL.md already has:

```bash
LADDER_KEYS_JSON="$(python3 -c 'import json,sys; print(json.dumps(json.loads(sys.argv[1])["ladder_keys"]))' "$INJECTION_JSON")"
ESCALATION_EXCLUDE_JSON="$(python3 -c '
import json, sys
ladder = json.loads(sys.argv[1]); stuck = sys.argv[2]
idx = ladder.index(stuck) if stuck in ladder else len(ladder)
print(json.dumps(sorted(set(ladder[idx:]) | {stuck})))
' "$LADDER_KEYS_JSON" "$INJECTION_KEY")"
```

**CRITICAL finding (incomplete ladder, recurrence guard): `{stuck}` is unioned in explicitly, and
the not-found fallback is `len(ladder)` (exclude nothing extra), never `0` (exclude the WHOLE
ladder).** `$LADDER_KEYS_JSON` now comes from `compute_ladder_keys` (Task 2/3, CRITICAL finding
fix) — the full narrowed+ranked candidate set, not merely `policy.ladder`'s configured keys — so
`stuck` (`$INJECTION_KEY`) is expected to appear in it whenever the same task/config produced both.
But relying on that alone is fragile — a prior revision's `idx = ... if stuck in ladder else 0`
fallback had a real bug even independent of `ladder_keys`' own completeness: when `stuck` is absent
from `ladder`, `ladder[idx:]` excludes ladder MEMBERS only, and `stuck` itself, never being a member,
was never added to the exclude set at all — leaving the very candidate this round is escalating away
from immediately eligible for reselection. Explicitly unioning `{stuck}` closes that regardless of
whether `stuck` is found in `ladder`, and `len(ladder)` (rather than `0`) as the not-found fallback
avoids the OPPOSITE overcorrection — excluding the entire ladder when the index is unknown, which
would have blocked every real candidate, not just same-or-weaker ones.

**CRITICAL finding (recurrence guard): `$ESCALATION_EXCLUDE_JSON` is passed ONLY via the new,
separate `--escalation-excluded-keys-json` argument, NEVER folded into `$EXCLUDED_KEYS_JSON` or
assigned back into it.** `$EXCLUDED_KEYS_JSON` keeps exactly the meaning Step 2 defines for it —
the recomputed union of `$PRIOR_EXCLUDED_KEYS_JSON` and `$WAVE_TRIED_JSON`, the ONLY value ever
passed as `--exclude-keys-json` — for this task's entire lifetime, with no third exception carved
out here. `$ESCALATION_EXCLUDE_JSON` is a different kind of thing: every key in it is a healthy,
never-attempted candidate excluded purely to enforce this round's capability floor, not a candidate
that was tried and failed — folding it into `$EXCLUDED_KEYS_JSON` (a prior revision did exactly
this) would make the very next union recompute (Step 3's own mid-dispatch `"quota"` branch above,
or a resume re-entering Step 2) silently drop those keys again, since neither
`$PRIOR_EXCLUDED_KEYS_JSON` nor `$WAVE_TRIED_JSON` ever recorded them — letting a later resolution
re-select a same-or-weaker candidate this round explicitly ruled out. Re-run `resolve-injection`
with the SAME `--exclude-keys-json "$EXCLUDED_KEYS_JSON"` and `--excluded-reasons-json
"$EXCLUDED_REASONS_JSON"` this round already had, adding `--escalation-excluded-keys-json
"$ESCALATION_EXCLUDE_JSON"` (same call shape as Step 2's own `resolve-injection` invocation above,
plus this one extra argument) — this excludes every genuinely-tried-and-failed candidate exactly as
before, AND every candidate ranked at-or-below the stuck one — i.e. same-or-weaker — never just the
stuck one alone. If it resolves to a real candidate (`native_claude`/`external_cli`), that IS the
capability-bumped implementer for this round: proceed with the new injection WITHOUT reassigning
`$EXCLUDED_KEYS_JSON`, framing the dispatch exactly as `subagent-driven-development`'s own text
requires: "A prior implementer attempted this task [N] times; you own it now. Read the report file
for what was tried." **`$ESCALATION_EXCLUDE_JSON` needs no persistence across rounds or resumes to
guarantee round 5 never regresses to a same-or-weaker candidate already ruled out in round 4**: it
is recomputed from scratch every time this check fires, purely from `$LADDER_KEYS_JSON` (stable for
this task) and THAT round's own freshly-resolved `$INJECTION_KEY` — and `$INJECTION_KEY` for round 5
can only be a candidate this same rule already proved was ranked strictly above round 4's stuck
candidate (or round 4's escalation-bumped candidate itself, if it later failed and became round 5's
own stuck candidate) — so round 5's `idx` is never worse than round 4's, and round 5's freshly
recomputed `ladder[idx:]` is automatically at least as restrictive. A resume behaves the same way:
Step 2 resolves fresh from `$PRIOR_EXCLUDED_KEYS_JSON` alone (no escalation floor), and if
`$FIX_ROUND >= 4` still holds, this check re-fires against whatever `$INJECTION_KEY` Step 2 just
landed on, re-deriving the correct floor before that round's implementer is ever dispatched.

If re-resolution instead reports `quota_exhausted` — **HIGH finding: this must not simply discard
resumable state and the auto-wake.** Read `any_quota_recoverable` from that result exactly as Step
2 does, and branch the same way:

- **`any_quota_recoverable == True`** — at least one of the more-capable candidates is only
  temporarily unavailable. This is genuinely time-bound, so treat it exactly like Step 2's own
  `any_quota_recoverable == True` branch, verbatim: merge this call's own `tried`/`reasons` into
  `$WAVE_TRIED_JSON`/`$WAVE_REASONS_JSON`, compute `$RESUME_EXCLUDED_KEYS_JSON` via
  `resume-exclusions` against `$PRIOR_EXCLUDED_KEYS_JSON`, write `$STATE_JSON` (including this
  round's own current `$FIX_ROUND`, already incremented per point 1's ordering rule below) via
  `write-resumable-state`, and schedule the hourly `CronCreate` wake — THEN stop this wave. Never
  dispatch a same-or-weaker candidate as a substitute just because persistence happened; the
  capability-bump requirement is still unmet this round, resumable exactly as Step 2's own
  quota-exhaustion case is.
- **`any_quota_recoverable == False`, or re-resolution finds no candidate at all** (the
  `no_candidate` mode — defined in Step 2 above, "If `INJECTION_MODE == "no_candidate"`") — no
  ruling or wait fixes this: no genuinely more-capable candidate is
  currently available for reasons waiting never resolves. Do **not** silently fall through to a
  same-or-weaker one, and do **not** schedule a futile `CronCreate` wake. STOP and report to the
  user, plainly, that rounds 4–5 cannot honor the capability-bump requirement with the currently
  configured/available ladder, reading `reasons`/`detail` off the result for exactly which
  candidates and why — justified on this adapter's own terms exactly as Step 2's own
  `any_quota_recoverable == False` branch is (above), not by claiming membership in
  `subagent-driven-development`'s own four stop-and-ask conditions verbatim. **MEDIUM finding: when
  the re-resolution narrowed the pool purely via `--escalation-excluded-keys-json` — the common case,
  where the stuck candidate is top-ranked and everything at-or-below it on the ladder is
  escalation-excluded, with nothing in `--exclude-keys-json` genuinely failed — `reasons`/`detail`
  come back empty by design (escalation-excluded keys never get a reason), so there is nothing to
  read off the result.** In that case, report instead that no candidate ranked above `$INJECTION_KEY`
  on the ladder is available for a fresh (non-escalation) pick — name the excluded keys from
  `$ESCALATION_EXCLUDE_JSON` (the same ladder keys this step passed as
  `--escalation-excluded-keys-json`) explicitly, so the user sees which candidates were excluded and
  why even though the result's own `reasons` map is empty.

## Step 4: Task review, fix loop, final review — unaffected

Whichever mode Step 3 used, `subagent-driven-development`'s own "3. Review the task" and "4. The
fix loop" proceed completely unmodified from here: `scripts/review-package`, the task reviewer
dispatch, the fix-loop round structure (1–5), and the final whole-branch review all operate on
`$REPORT_FILE` and the real commits the dispatch produced, with zero awareness of which mode
produced them. This skill's own scope ends at Step 3 — it never touches review, fix-loop
adjudication, or the ledger directly.
