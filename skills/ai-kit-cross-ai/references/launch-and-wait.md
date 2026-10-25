# Launch and wait

Per-host patterns for section 2 and section 3 of [`../SKILL.md`](../SKILL.md). The runner command
is the same everywhere; only the background primitive differs. A host without one uses the
foreground wait below.

Record the PID the launch prints, and kill a lane by that PID only. Each parallel lane gets its
own status file and its own PID. Never edit the tree while a review lane runs.

The examples below are copied from hermetic runner runs against a fake CLI.

## Claude Code

Claude Code's background Bash runs the lane and posts a completion notice. Launch it in the
background, keep the recorded PID, and read the status only after the notice arrives.

```bash
node .planning/scripts/cross-ai.mjs --runtime pi --model "$MODEL" --mode exec \
  < prompt.md > lane.out 2> lane.err &
echo $! > lane.pid
```

When the completion notice arrives, read `lane.err`. Its last line is the status, for example:

```
AIKIT-XAI status=ok cli=- model=- exit=0 cli_rc=- elapsed=0s out=0 tree=clean action=stop route=unknown rule=- pattern=none attempts=0 cycles=0
```

A stop carries the report line before it:

```
cross-ai: report status=auth lane=pi/fake/auth route=unknown attempts=1 cycles=0 first_failure=2026-10-25T17:26:29.839Z last_failure=2026-10-25T17:26:29.855Z due_at=- stopped=class upstream=present
```

On an exit 75 with `retry_after_s=`, schedule one one-shot `CronCreate` at `retry_after_s` and
re-invoke the same lane. No other wake exists.

## pi

unverified. pi's help shows no notification or one-shot scheduling feature, so pi uses the
foreground wait: the command blocks, and its PID file records the lane.

```bash
node .planning/scripts/cross-ai.mjs --runtime pi --model "$MODEL" --mode exec \
  < prompt.md > lane.out 2> lane.err &
echo $! > lane.pid
wait "$(cat lane.pid)"
```

Then read `lane.err` the same way. Print `retry_after_s`, the state path and the re-invoke
command; do not schedule anything.

## opencode

unverified. opencode's help shows no notification or one-shot scheduling feature, so opencode
uses the same foreground wait, with `--runtime opencode` and its own PID file.

```bash
node .planning/scripts/cross-ai.mjs --runtime opencode --model "$MODEL" --mode exec \
  < prompt.md > lane.out 2> lane.err &
echo $! > lane.pid
wait "$(cat lane.pid)"
```

## cursor

unverified. No background primitive is documented for cursor, so cursor uses the foreground wait
with `--runtime cursor` and its own PID file.

```bash
node .planning/scripts/cross-ai.mjs --runtime cursor --model "$MODEL" --mode exec \
  < prompt.md > lane.out 2> lane.err &
echo $! > lane.pid
wait "$(cat lane.pid)"
```

## codex

unverified. No background primitive is documented for codex, so codex uses the foreground wait
with `--runtime codex` and its own PID file.

```bash
node .planning/scripts/cross-ai.mjs --runtime codex --model "$MODEL" --mode exec \
  < prompt.md > lane.out 2> lane.err &
echo $! > lane.pid
wait "$(cat lane.pid)"
```

## copilot

unverified. No background primitive is documented for copilot, so copilot uses the foreground
wait with `--runtime copilot` and its own PID file. Copilot takes the prompt on argv, which the
runner passes for it; the prompt is then visible in the process table.

```bash
node .planning/scripts/cross-ai.mjs --runtime copilot --model "$MODEL" --mode exec \
  < prompt.md > lane.out 2> lane.err &
echo $! > lane.pid
wait "$(cat lane.pid)"
```

## A host without a background primitive

unverified. A host not listed above gets the foreground wait: start the runner, record its PID,
and `wait` on that PID. Read `lane.err` afterwards. Print `retry_after_s`, the state path and the
re-invoke command instead of scheduling a wake.

```bash
node .planning/scripts/cross-ai.mjs --runtime "$RUNTIME" --model "$MODEL" --mode exec \
  < prompt.md > lane.out 2> lane.err &
echo $! > lane.pid
wait "$(cat lane.pid)"
```
