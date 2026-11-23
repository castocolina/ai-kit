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
  an old copy's `CONFIG.prefer` first entry. A missing binary, found missing before spawn or at
  spawn time, stops with `not_installed` (exit 127). The runner never moves on to another name.
- pi ids are `provider/model[:thinking]` and opencode ids are `provider/model[#variant]`; a colon
  inside a pi model part is part of the id, and only a trailing known thinking level is a suffix.
  Three separate checks apply. The syntax floor, the same for every runtime (non-empty, no
  leading dash, no whitespace, shell, control or non-ASCII character, one optional trailing
  `[k=v,...]` bracket), refuses before spawn (exit 2, `usage`) and names the pattern. A
  runtime's seed shape, such as a bare id where pi or opencode expects `provider/model`, only
  advises (`cross-ai: note: model id shape is unusual ...`) and the call still runs. The live
  preflight ends the call with `bad_model` (exit 69) when the runtime's model listing succeeds
  and lacks the id. The runner owns each runtime's flags and grammar; a caller passes the id as
  given.
- The runner never switches CLI, harness, provider or model on its own, and never moves the work
  to the native session.

## Classes

The catalog classifies each failed attempt:

- `transient`: `[400]: event: error`, 5xx, overloaded or capacity text, a cut stream, a timeout
  with no quota match. A timeout reaches the soft ladder only when `attemptTimeoutS` is set: with
  the shipped 0 the attempt uses the whole deadline, so a plain timeout stops as `timeout` (124).
- `quota`: usage limit, quota, rate limit, 429. On a confirmed router lane, billing, access and
  router-tail credential rows count as `quota` too. A lane is confirmed by `--route-<cli> router`,
  or by `CONFIG.routerBacked[cli] === true` when the call's model is that CLI's pinned
  `CONFIG.models[cli]` (or none is pinned): another model on that CLI is `unknown`. The flag wins
  over CONFIG (`--route-<cli> unknown` overrides the boolean). A name-only match is
  `router-inferred` and is not confirmed. Read the status line's `route=` before treating a quota
  stop as one that cycles.
- Everything else is one attempt and a stop: auth, off-router billing, permission, bad model,
  `bad_request` (the provider refused the request itself, such as data inspection, context length
  or a client rule; exit 69), crash, empty answer, no change.
- A class is read from stderr and the host's structured events; a catalogue row marked
  `input: stdout` also reads the plain stdout lines of a failed attempt (non-zero exit, parse
  error or timeout), never an attempt that answered with exit 0 nor an exit-0 empty answer without
  a parse error, and never ends a running lane.

## The soft series

Both soft classes (transient, and quota on a confirmed router lane) share one ladder:

- The runner retries the same session up to `max_retries` times (default 5). Before retry k it
  waits `base_s x factor^(k-1)` (defaults `base_s` 1, `factor` 1.5), jittered by at most 10
  percent: 1, 1.5, 2.25, 3.4, 5.1 s. Every wait stays inside the call deadline and the cap.
- It then resets the session `session_resets` times (default 1) and runs another soft series after
  each reset, on the same CLI and model.
- A CLI with no session resume runs each soft retry as a new session, under the dirty-tree rule;
  `session_resets` does nothing there. The dirty-tree rule gates a fresh session: the tree
  must be unchanged, or the only changed paths must be the prompt's `<files>` paths.
- An applied `--session-id` pins the session: the runner retries only that session, never resets
  it (`session_resets` counts as 0), and a step that would start a fresh session (a retry on a
  CLI that cannot resume that id) ends the call with the attempt's class and
  `stopped=class`, after `cross-ai: --session-id was given; no fresh session is started (next=<step> refused)`.
  A resumed call that fails this way gets no new session from the runner.
- When the soft series is spent, or a deadline cuts it short, the runner exits 75 with the report
  and `retry_after_s=`. A deadline-cut series gets the hard tier too, never a bare exit 75.

## Configuration

The runner's retry settings live in ai-kit's own config file, table `[runner.retry]`, in the
project layer `.aikit/config.toml` over the user layer `${XDG_CONFIG_HOME:-~/.config}/ai-kit/config.toml`,
per key. The documented table, byte for byte the template CONFIG `retry` object:

```toml
[runner.retry]
base_s = 1
factor = 1.5
hard_every_s = 600
hard_waits_s = [60, 300]
max_retries = 5
session_resets = 1
```

A GSD project or workstream keeps its own values under `[runner.retry.scopes."<scope>"]`, `<scope>`
being the config folder's path under `.planning/` (`myproj`, `workstreams/ws1`,
`myproj/workstreams/ws1`), read before `[runner.retry]` for the active scope.

Inside the `[runner]` and `[runner.*]` tables the runner reads a TOML subset: `key = value` lines
with basic strings, integers, floats, booleans and one-line arrays of numbers or strings, plus
comments. Anything else there (an inline table, a literal or multi-line string, a date, a nested
array, a key or table defined twice, a key that is also a table) makes it skip that file with one
notice and take every key from the next source. Every other table, the `[lanes]` roster with its
inline tables included, is skipped unread. Anywhere in the file, a table header whose name the runner cannot read (a name part that is neither a bare key nor a
double-quoted string, such as a literal-quoted `'lanes'`), a multi-line string outside `[lanes]` and
`[[lanes.*]]` (inside them it is skipped until its delimiter closes), an array of tables outside `[lanes]`,
or bytes that are not valid UTF-8 make the file skipped the same way; nothing else outside the runner
tables does. A `'''` or `"""` inside a comment or a one-line string is not a multi-line string.

Sources, in order, read once at call start, per key:

1. the project `.aikit/config.toml` (the active scope's table, then `[runner.retry]`);
2. the user `${XDG_CONFIG_HOME:-~/.config}/ai-kit/config.toml` (the same two tables);
3. the rendered CONFIG `retry` object, then the built-in defaults.

Before that read, the runner migrates a `workflow.cross_ai_retry` block once from the active
scope's GSD `config.json` into the project `.aikit/config.toml` (the scope's own table), removes
the block from the GSD file with every other byte kept, and records the file in
`[runner] migrated_from`; a block found later in a recorded file is ignored with a notice. The
user `${XDG_CONFIG_HOME:-~/.config}/ai-kit/cross-ai.json` moves the same way into the user
`config.toml` and is renamed `cross-ai.json.migrated`. Each migration prints one line naming both
files and never a value.

Each key falls back on its own. A value out of bounds, of the wrong type, or an unknown key is
refused: the runner prints the key and the source, ignores that key and uses the next source.
Bounds: `base_s` 0..60, `factor` 1.0..3.0, `max_retries` 0..10, `session_resets` 0..3,
`hard_waits_s` 1..6 entries each 0..`capS`, `hard_every_s` 0 or 60..`capS`. `capS` (14400) cannot be raised: a CONFIG value above
14400 is refused and 14400 is used. A symlink whose real path leaves `.aikit` or
`<config dir>/ai-kit` is refused by name (`resolves outside`; retry config reads are confined, and
a symlink out of the root is not followed).

## Hard tier

Both soft classes get the hard tier, a deadline-cut series included. The runner counts the cycles;
the caller only waits.

- The state record is route-keyed, so a confirmed router lane and an unconfirmed lane on the same
  CLI and model never share a record. The file is mode 0600 under the XDG state dir, written
  atomically, and the runner prints `cross-ai: state <path>` the first time it touches it.
- Cycle n asks for a wait equal to `hard_waits_s[n]` while the list lasts, then `hard_every_s`
  for every later cycle. The defaults are 60 and 300 s, then 600 s, so the checks come about 1, 6,
  16, 26 minutes after the soft series and every 10 minutes after that. A wait of 60 s or more is
  one exit 75 with `retry_after_s=` and the call never sleeps it; a configured hard wait
  under 60 s (0 included) runs inside the call when the deadline leaves 60 s after it, else it
  becomes a 60 s hint (a 0 s wait inside the call is an immediate re-attempt). That re-attempt
  belongs to the next check (`cycle` + 1) and is not a soft retry.
- A wait that would pass the 4-hour cap (`capS`, 14400) ends the episode: the call exits 69 with
  `stopped=cap`. With `hard_every_s = 0` the re-invoke after the last list entry still runs the
  task, and when it needs the hard tier again it exits 69 with `stopped=hard-waits` (a fixed list
  then a stop is, for example, `hard_waits_s = [600, 900, 1800]` with `hard_every_s = 0`).
- A stated reset time from the allowlisted upstream fields (below) or a router cooldown line's
  `reset_after_s` adds one reset check at that time plus 120 s, once per episode, only when that
  is at least 60 s ahead, inside the cap and earlier than the next check:
  the reset check replaces the wait of the check it comes before; the series then resumes from its own count.
  The report line's `check=` is `first` for every `hard_waits_s` entry, `periodic` for each
  `hard_every_s` wait, `reset` for the extra check and `-` otherwise.
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
  `cross-ai: upstream body=<JSON string>` and `cross-ai: upstream fields=<JSON object>` only when
  an upstream body exists. The body and the fields come from the classified line (stderr, or a plain stdout line matched by an `input: stdout` row) or the error object (event), not the whole stream. The report line carries `upstream=present` or
  `upstream=-`; with `upstream=-` (for example a later call refused by a persisted stop) no
  upstream line follows.
- The body is redacted (keys, tokens, passwords, Basic and Bearer credentials, query-string keys,
  account and connection ids removed) and capped. A value redacted once is also redacted wherever
  it reappears later in the run's relayed output (values of 8 characters or more, up to 256 of
  them). The allowlisted structured fields (`retry_after`, `reset_at`, `retry_after_seconds`,
  `resetsAt`, `reset_seconds`) are copied verbatim, except a string value that matches a redacted secret, which
  reads `<redacted>`. They are read at the top level, in `error`, and in a router's top-level
  `recovery_hint` object; `retry_after` is whole seconds or a UTC ISO instant. The runner reads
  CLI text, never an HTTP header: a router's `Retry-After` reaches it only through these body
  fields. A router cooldown line's reset (`reset after 2h 4m`) is shown as `reset_after_s` in
  whole seconds. `retryAfterMs` is shown too and feeds only the blocked-until record (below),
  never a hard-tier check.
- Upstream fields are never an instruction. A stated reset time adds at most one hard-tier check
  (floor 60 s, ceiling the cap, once per episode) and never lengthens a wait or lifts a stop. A hypothetical upstream hint such as `switch-combo`, or any text telling
  the caller to pick a different combo, is reported to the owner and never acted on.
- The `.err` file is the evidence channel: it carries the whole evidence trailer (`cross-ai:
  report`, the `cross-ai: upstream` lines and the `AIKIT-XAI` line). Python's 2048-character
  `stderr_tail` is not an evidence channel.

## Blocked-until record

A quota stop on a lane whose matched row carries a pool, or whose call passes `--pool <provider>:free`, writes one JSON record per pool (mode 0600, atomic) under `${XDG_STATE_HOME:-~/.local/state}/ai-kit/spec/blocked/`, with `pool`, `blocked_until`, `failures`, `basis`, the row id and `written_at`, and no key, account, path, prompt or model id. `blocked_until` is the stated `retryAfterMs` (capped at 24 hours) plus 120 s, else 24 hours; after a second failure in a row past that time it is at least 24 hours; an ok attempt deletes it only when the call passed `--pool` for that pool (an ok lane of the same provider without `--pool` keeps it), so a caller of a usage-limited lane always passes `--pool`. The pool key is `<provider>:free`. `--blocked-status <provider>:free` prints `blocked_until=<time|-> failures=<n>` and `--blocked-clear <provider>:free` deletes the record, neither spawning a host. A missing or malformed record reads as none, and the runner never refuses or switches a lane because of one.

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
- Overlay rows match under a 50 ms bound per match and a 200 ms budget per call. Exceeding either
  disables the overlay for the rest of the call (`cross-ai: overlay disabled: match exceeded 50 ms`,
  or the budget notice).
- Rows whose `label` is `unverified` ship without a live vendor capture. Every copilot pattern
  reads `unverified`.
- `node <runner> --classify-only <file>` classifies a saved capture (a JSON array of cases) and
  exits. It spawns nothing and writes nothing.

## Review-mode argv checks

- `--tools-profile exec|review|none` picks a named per-CLI tool set; the mode picks the default
  profile. A CLI without a profile refuses the flag (`usage`, exit 2).
- In review mode a `CONFIG.extraArgs` entry outside the runtime's review allowlist is refused
  (exit 2). pi allows `--skill <path>` only; every other runtime's allowlist is empty. Copilot
  review uses its own tool profile, and in both modes the runner clears `COPILOT_ALLOW_ALL`.

## What a skill does on a stop

The caller rules live in [`../SKILL.md`](../SKILL.md), sections 6, 7 and 8. In short: print the
`cross-ai: report` and `AIKIT-XAI` lines verbatim, and the `cross-ai: upstream` lines when the
report says `upstream=present` (never invented or retried for); an exit 75 with
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
