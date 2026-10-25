# Launch and wait

Per-host patterns for section 2 and section 3 of [`../SKILL.md`](../SKILL.md). The runner command
is the same everywhere; only the background primitive differs. A host without one uses the
foreground wait below.

Every lane writes its files into its own scratch directory outside the tracked tree (a temp dir,
or a gitignored one such as `tmp/<lane>/`): a file created in the tree while a review lane runs
dirties the tree and stops that review with `contract_violation tree=dirty`. A lane's files are:
- `lane.out`: the answer (stdout);
- `lane.err`: the evidence (stderr), whose last line is the `AIKIT-XAI` status line;
- `lane.rc`: the exit code, written by the launch itself.

The exit code is also the `exit=` field of that last line. Stop a lane only through its own
launch: its background task, or the PID of the foreground command you started.

The report line below is copied from a hermetic runner run against a fake CLI; the ok line shows
the shape of a finished exec lane, with illustrative values.

## Claude Code

Claude Code's background Bash runs one command and posts a completion notice when that command
exits. Make the runner itself that command: no trailing `&`, or the shell exits at once and the
notice fires while the lane still runs. Read the lane's files only after the notice arrives.

```bash
L=tmp/lane-pi; mkdir -p "$L"
node .planning/scripts/cross-ai.mjs --runtime pi --model "$MODEL" --mode exec \
  < prompt.md > "$L/lane.out" 2> "$L/lane.err"; echo $? > "$L/lane.rc"
```

The background task identifies the lane; stop a lane by stopping its task. When the notice
arrives, read `lane.rc`, then the last line of `lane.err`, for example:

```
AIKIT-XAI status=ok cli=pi model=fake/ok exit=0 cli_rc=0 elapsed=1s out=12 tree=clean action=stop route=unknown rule=- pattern=none attempts=1 cycles=0
```

A stop carries the report line before it:

```
cross-ai: report status=auth lane=pi/fake/auth route=unknown attempts=1 cycles=0 first_failure=2026-10-25T17:26:29.839Z last_failure=2026-10-25T17:26:29.855Z due_at=- stopped=class upstream=present
```

On an exit 75 with `retry_after_s=`, schedule one one-shot `CronCreate` at `retry_after_s` and
re-invoke the same lane. No other wake exists.

## pi

unverified. pi's help shows no notification or one-shot scheduling feature, so pi uses the
foreground wait below with `--runtime pi`. Print `retry_after_s`, the state path and the
re-invoke command; do not schedule anything.

## opencode

unverified. opencode's help shows no notification or one-shot scheduling feature, so opencode
uses the foreground wait below with `--runtime opencode`.

## cursor

unverified. No background primitive is documented for cursor, so cursor uses the foreground wait
below with `--runtime cursor`.

## codex

unverified. No background primitive is documented for codex, so codex uses the foreground wait
below with `--runtime codex`.

## copilot

unverified. No background primitive is documented for copilot, so copilot uses the foreground
wait below with `--runtime copilot`. Copilot takes the prompt on argv, which the runner passes
for it; the prompt is then visible in the process table.

## A host without a background primitive

unverified. Any host above but Claude Code, and any host not listed, gets the foreground wait:
run the runner as a plain command, which blocks until the lane exits, and record its exit code.
Then read `lane.rc` and `lane.err`. Print `retry_after_s`, the state path and the re-invoke
command instead of scheduling a wake.

```bash
L=tmp/lane-"$RUNTIME"; mkdir -p "$L"
node .planning/scripts/cross-ai.mjs --runtime "$RUNTIME" --model "$MODEL" --mode exec \
  < prompt.md > "$L/lane.out" 2> "$L/lane.err"; echo $? > "$L/lane.rc"
```
