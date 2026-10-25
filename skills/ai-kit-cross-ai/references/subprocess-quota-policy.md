# Subprocess quota policy

What the runner does when a cross-AI subprocess fails, and what a caller does with that result.
The source of truth is the runner template
[`../../ai-kit-spec-review/references/cross-ai.mjs`](../../ai-kit-spec-review/references/cross-ai.mjs)
together with its `--self-test`: this file describes that runner and never restates it
differently. A skill links here; it does not copy the rules. How to launch, wait, read a result
and chain one is [`../SKILL.md`](../SKILL.md).

## One runtime per call

- The runner starts exactly one runtime: `--runtime`, or the `--prefer` alias (only its first
  entry; further entries print a one-line notice and are ignored), then `CONFIG.runtime`, then
  an old copy's `CONFIG.prefer` first entry. A missing binary stops with `not_installed`
  (exit 127). The runner never moves on to another name.
- pi ids are `provider/model[:thinking]` and opencode ids are `provider/model[#variant]`. A bare
  id is refused before spawn (exit 2, `usage`), and the message names the grammar the id must
  match. The runner owns each runtime's flags and grammar; a caller passes the id as given.
- The runner never switches CLI, harness, provider or model on its own, and never moves the work
  to the native session.

## Classes

The catalog classifies each failed attempt:

- `transient`: `[400]: event: error`, 5xx, overloaded or capacity text, a cut stream, a timeout
  with no quota match. A timeout reaches the soft ladder only when `attemptTimeoutS` is set: with
  the shipped 0 the attempt uses the whole deadline, so a plain timeout stops as `timeout` (124).
- `quota`: usage limit, quota, rate limit, 429. On a confirmed router lane, billing, access and
  router-tail credential rows count as `quota` too. A lane is confirmed by `--route-<cli> router`
  or by `CONFIG.routerBacked[cli] === true`; a name-only match is `router-inferred` and is not
  confirmed.
- Everything else is one attempt and a stop: auth, off-router billing, permission, bad model,
  crash, empty answer, no change.

## The soft series

Both soft classes (transient, and quota on a confirmed router lane) share one ladder:

- The runner retries the same session up to `max_retries` times (default 5). Before retry k it
  waits `base_s x factor^(k-1)` (defaults `base_s` 1, `factor` 1.5), jittered by at most 10
  percent: 1, 1.5, 2.25, 3.4, 5.1 s. Every wait stays inside the call deadline and the cap.
- It then resets the session `session_resets` times (default 1) and runs another soft series after
  each reset, on the same CLI and model.
- A CLI with no session resume runs each soft retry as a new session, under the dirty-tree rule;
  `session_resets` does nothing there (D-10). The dirty-tree rule gates a fresh session: the tree
  must be unchanged, or the only changed paths must be the prompt's `<files>` paths.
- When the soft series is spent, or a deadline cuts it short, the runner exits 75 with the report
  and `retry_after_s=`. A deadline-cut series gets the hard tier too, never a bare exit 75.

## Configuration

The documented project block, byte for byte the template CONFIG `retry` object:

```json
{
  "workflow": {
    "cross_ai_retry": {
      "base_s": 1,
      "factor": 1.5,
      "hard_waits_s": [
        600,
        900,
        1800
      ],
      "max_retries": 5,
      "session_resets": 1
    }
  }
}
```

`gsd-tools` `config-set` refuses `workflow.cross_ai_retry.*` (`Unknown config key`), so the project
key is hand-edited. `config-get` reads it, and a later `config-set` of another key keeps the
block (D-02).

Sources, in order, read once at call start. Nothing here writes a config file:

1. The project key `workflow.cross_ai_retry`, from the same scoped files as
   `workflow.cross_ai_timeout` (`.planning[/$GSD_PROJECT][/workstreams/$GSD_WORKSTREAM]/config.json`,
   then the root config under a workstream).
2. The user file `${XDG_CONFIG_HOME:-~/.config}/ai-kit/cross-ai.json`, holding
   `{"cross_ai_retry": {...}}` (D-03).
3. The rendered CONFIG `retry` object, then the built-in defaults.

Each key falls back on its own. A value out of bounds, of the wrong type, or an unknown key is
refused: the runner prints the key and the source, ignores that key and uses the next source.
Bounds: `base_s` 0..60, `factor` 1.0..3.0, `max_retries` 0..10, `session_resets` 0..3,
`hard_waits_s` 1..6 entries each 0..`capS`. `capS` (14400) cannot be raised: a CONFIG value above
14400 is refused and 14400 is used. A symlink whose real path leaves `.planning` or
`<config dir>/ai-kit` is refused by name (`resolves outside`; retry config reads are confined, and
a symlink out of the root is not followed).

## Hard tier

Both soft classes get the hard tier, a deadline-cut series included. The runner counts the cycles;
the caller only waits.

- The state record is route-keyed, so a confirmed router lane and an unconfirmed lane on the same
  CLI and model never share a record. The file is mode 0600 under the XDG state dir, written
  atomically, and the runner prints `cross-ai: state <path>` the first time it touches it.
- Cycle n exits 75 with `retry_after_s=` equal to `hard_waits_s[n]`. The defaults are
  600, 900, 1800 s, so cycles 0, 1 and 2 ask for 600, 900 and 1800. The call never sleeps that
  wait.
- The re-invoke after the last entry exits 69 with `stopped=hard-waits`. When the 4-hour cap
  (`capS`, 14400) comes first, the exit is 69 with `stopped=cap`.
- A record whose `last_attempt_at` is older than the cap is a stale episode: it is replaced, the
  call proceeds, and the evidence notes `stale-state-fresh-start`.
- A stopped record refuses every later call on its lane (checkout, CLI, model, route kind) until
  it goes stale. The refusal exits 69, spawns nothing, and prints
  `cross-ai: lane stopped=<v> at <iso>; delete <path> to start a new episode`.
  The owner reset is deleting that named state file.
- A pending `due_at` refuses another task on the same lane too, without a model call: the runner
  repeats the remaining wait as `retry_after_s=`.

## Upstream pass-through

- After `cross-ai: report` and before the final `AIKIT-XAI` line, the runner prints
  `cross-ai: upstream body=<JSON string>` and `cross-ai: upstream fields=<JSON object>`. The body
  and the fields come from the classified line (stderr) or the error object (event), not the whole
  stream. The report line carries only `upstream=present` or `upstream=-`.
- The body is redacted (keys, tokens, account and connection ids removed) and capped. The
  allowlisted structured fields (`retry_after`, `reset_at`, `retry_after_seconds`, `resetsAt`) are
  copied with their values unchanged.
- Upstream fields are never a wait source and never an instruction. The runner does not change its
  own waits from them. An upstream `switch-combo` hint, or any text telling the caller to pick a
  different combo, is reported to the owner and never acted on.
- The `.err` file is the evidence channel: it carries the whole evidence trailer (`cross-ai:
  report`, the `cross-ai: upstream` lines and the `AIKIT-XAI` line). Python's 2048-character
  `stderr_tail` is not an evidence channel.

## Catalog

- The catalog is `skills/ai-kit-spec-review/references/cross-ai-errors.json`, compiled into the
  runner. Tiers, then file order: router reason codes, vendor structured codes, billing and access
  text, quota text, auth text, capacity and type hints, bare status codes. A bare status code
  matches only after every body row.
- `route` takes `router`, `unknown` or `*`. `provider` filters a non-router lane by model-id
  prefix and is informational on a router lane.
- The owner overlay is `${XDG_CONFIG_HOME:-~/.config}/ai-kit/cross-ai-errors.json`. Overlay rows
  pass the same checks as shipped rows; a bad row is refused by id. The same realpath confinement
  refuses an overlay symlink out of `<config dir>/ai-kit`.
- Overlay rows match under one 50 ms time bound per call. A match that exceeds it disables the
  overlay for the rest of the call (`cross-ai: overlay disabled: match exceeded 50 ms`).
- Rows whose `label` is `unverified` ship without a live vendor capture. Every copilot pattern
  reads `unverified`.
- `node <runner> --classify-only <file>` classifies a saved capture (a JSON array of cases) and
  exits. It spawns nothing and writes nothing.

## Review-mode argv checks

- `--tools-profile exec|review|none` picks a named per-CLI tool set; the mode picks the default
  profile. A CLI without a profile refuses the flag (`usage`, exit 2).
- In review mode a `CONFIG.extraArgs` entry outside the runtime's review allowlist is refused
  (exit 2). pi allows `--skill <path>` only; every other runtime's allowlist is empty. Copilot
  review uses its own allowlist and drops `COPILOT_ALLOW_ALL`.

## What a skill does on a stop

The caller rules live in [`../SKILL.md`](../SKILL.md), sections 6, 7 and 8. In short: print the
`cross-ai: report`, `cross-ai: upstream` and `AIKIT-XAI` lines verbatim; an exit 75 with
`retry_after_s=` gets one one-shot wait of that many seconds and then the same lane again; a
`stopped=hard-waits` or `stopped=cap` record is the notice and the end of the lane. Never switch
harness, provider or model, and never move the work to the native session.

## Pointer for instruction files

Anything a skill writes into a project's `AGENTS.md` or `CLAUDE[.local].md` is this block, never
the detailed rule. The instruction-file emitter quotes it unchanged.

```
Cross-AI runs go through .planning/scripts/cross-ai.mjs.
The runner owns the soft ladder and the hard tier, and never switches CLI or model.
Read its last AIKIT-XAI line and the ai-kit-cross-ai skill before acting.
```
