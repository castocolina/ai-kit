# Subprocess quota policy

What a skill does when a cross-AI subprocess hits a limit. The source of truth is
`references/cross-ai.mjs` (this directory) together with its `--self-test`: this file describes
that ladder and never restates it differently. A skill links here; it does not copy the rules.

## One CLI per call

- The runner starts the first named entry of `--prefer` or `CONFIG.prefer`. The rest of the
  list is the owner's menu, used only when the owner names one. A missing first entry stops
  with `not_installed` (exit 127); the runner does not move on to the next name.
- The runner never switches CLI, harness, provider or model on its own, and never moves the work
  to the native session.

## Classes

The pattern table in the runner classifies each failed attempt:

- `transient`: `[400]: event: error`, 5xx, overloaded or capacity text, a cut stream, a timeout
  with no quota match. A timeout reaches a rung only when `attemptTimeoutS` is set: with the
  shipped 0 the attempt uses the whole deadline, so a plain timeout stops as `timeout` (124).
- `quota`: usage limit, quota, rate limit, 429. On a confirmed router lane, billing, access and
  router-tail credential rows count as `quota` too.
- Everything else stops: auth, off-router billing, permission, bad model, crash, empty answer,
  no change.

## Rungs

- Rung 1: up to `sameSessionRetries` (3) retries in the same session, where the CLI can continue
  a session. When it cannot, rung 1 is unavailable and the runner goes straight to rung 2.
- Rung 2: up to `newSessionRetries` (3) new sessions, same CLI and same model. A router pins a
  session to one combo member; a new session lets the combo choose again.
- The dirty-tree rule gates rung 2. The tree must be unchanged, or the only changed paths must be
  the prompt's `<files>` paths. Any other dirty path stops the ladder.

## Router quota cycles

- Only a confirmed router lane gets cycles. A lane is confirmed by `--route-<cli> router` or by
  `CONFIG.routerBacked[cli] === true`. A name-only match (`router`, `-env`, `local-llm`) is
  reported as `router-inferred` and is advisory: it gets no cycles and stops like a direct route.
- After rung 2 the runner exits 75 with `retry_after_s=` (`cooldownS`, 600) and `cycle=<n>`. The
  caller waits that long and re-invokes the same lane.
- A cross-call state file (mode 0600, XDG state dir, atomic write) stores `first_seen`,
  `last_attempt_at` and the cycle. Its key is the checkout, the lane and the model: the quota
  budget is not task-keyed. The session id to resume lives in that same file, and the runner reuses it only
  when the file's task digest matches this prompt (the `<objective>` text, or the whole prompt
  when there is none). It is never reused for a different task on the same lane, and there is
  no second store.
- A new cycle starts while `now + cooldown <= first quota failure + capS` (14400, the 4-hour
  cap). Past the cap the runner exits 69 and stops for good.
- A re-entry before the state file's due time is refused without a model call (the runner's
  preflight may still list the CLI's models). A file whose
  `last_attempt_at` is older than the cap is a stale episode: it is replaced, the call proceeds,
  and the evidence notes `stale-state-fresh-start`.

## Stops that end the ladder

- Auth (401/403 that is not a router-tail credential row), off-router billing or access, a bad
  model, permission, a crash, an empty answer and a no-change result stop immediately. So does a
  quota stop off a confirmed router lane (direct or `router-inferred`): a bare exit 75 with no
  `retry_after_s=`. None of them enters a rung or a cycle.

## Evidence

- One `cross-ai: attempt ...` line per failed attempt.
- One `cross-ai: report status= lane= route= attempts= cycles= first_failure= last_failure=
  stopped=` line on a stop.
- The last stderr line is `AIKIT-XAI status=... action=stop route= rule= pattern= attempts=
  cycles=`, plus `retry_after_s=` and `cycle=` on a router-quota exit 75.

## CONFIG knobs and clamps

- `prefer`: the menu; the first named entry runs, and a missing one stops with `not_installed`
  (exit 127).
- `sameSessionRetries`, `newSessionRetries`: counts clamped to 0..3.
- `backoffS`: the short backoff between rungs inside one call. The call never sleeps the cooldown.
- `cooldownS`: seconds the caller waits between cycles (default 600), clamped to `0..capS`.
- `capS`: the cap in seconds (default 14400), clamped to `0..14400`.
- `routerBacked`: per-CLI confirmed route (`true` router, `false` unknown); with a pinned
  `models[cli]`, `true` covers only that model. `--route-<cli>` wins.
- `attemptTimeoutS`: `0` (none) or clamped to `10..1800`.

## What a skill does on a stop

- Print the runner's `AIKIT-XAI` line and its `cross-ai: report` line verbatim, before acting.
- Stop. Never re-dispatch the task to another candidate, harness, provider or model, and never
  move the work to the native session.
- Write resumable state where the skill already writes it, and let the owner choose.
- Caller contract, the only delayed re-entry: a confirmed-router exit 75 carrying `retry_after_s=`
  and `cycle=` gets exactly one one-shot `CronCreate` at `retry_after_s`, re-invoking the same
  lane (same CLI and model), until a stop past the 4-hour cap (exit 69). Never a repeated or
  fixed-interval job. An off-router quota stop also exits 75, without `retry_after_s=`, and it is
  not this case. Every other stop (exit 69, auth, off-router billing or access, bad model) is
  owner-controlled: nothing is scheduled, and the owner re-invokes.
- Other hosts have no `CronCreate`. They print `retry_after_s`, the state path and the re-invoke
  command, and the owner runs it. Whether that printed re-invoke is picked up is unverified.
- Unverified: whether a one-shot wake fires while GSD's retry/skip/abort prompt is pending.

## Checking a capture

- `node references/cross-ai.mjs --classify-only <file>` classifies a saved capture and exits. The
  file is a JSON array of cases. It spawns nothing and writes nothing.
- Rows whose `label` is `unverified` ship without a live vendor capture. Their ids:
  `vendor-monthly-limit`, `text-insufficient-funds`, `text-model-access-disabled`,
  `text-named-models`, `text-free-plan-auto`, `vendor-go-usage`, `cursor-action-usage-limit`,
  `pi-chatgpt-usage-limit`, `claude-hit-your-limit`, `text-hit-your-limit`, `claude-overloaded`.
  The owner's capture kit stages each as not run; that kit is not part of this skill.

## Pointer for instruction files

Anything a skill writes into a project's `AGENTS.md` or `CLAUDE[.local].md` is this block, never
the detailed rule. The instruction-file emitter quotes it unchanged.

```
Cross-AI runs: send every external CLI run through .planning/scripts/cross-ai.mjs.
The runner owns the failure ladder (same-session retries, new sessions, router quota
cooldown, 4-hour cap) and never switches CLI, provider or model; read its last AIKIT-XAI line.
On a stop, give the owner its cross-ai: report line; never retry auth or pick another CLI.
```
