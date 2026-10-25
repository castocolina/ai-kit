# Launch and wait

Per-host patterns for section 2 and section 3 of [`../SKILL.md`](../SKILL.md). Each section below
is named for the host the caller runs in, never for the target runtime: every example passes the
owner's `$RUNTIME` and `$MODEL` unchanged. Pick the pattern by what the host can do: a host whose
background primitive posts a completion notice uses it; any other host uses the foreground wait.

Every lane writes into its own scratch directory, per section 2 of [`../SKILL.md`](../SKILL.md)
(`mktemp -d`, or a directory git ignores as a whole). A lane's files are:
- `lane.out`: the answer (stdout);
- `lane.err`: the evidence (stderr), whose last line is the `AIKIT-XAI` status line;
- `lane.rc`: the exit code, written by the launch itself.

The exit code is also the `exit=` field of that last line. Stop a lane only through its own
launch: its background task, or the foreground command you started.

The report line below is copied from a hermetic runner run against a fake CLI; the ok line shows
the shape of a finished exec lane, with illustrative values.

## Claude Code

Claude Code's background Bash runs one command and posts a completion notice when that command
exits. Make the runner itself that command: no trailing `&`, or the shell exits at once and the
notice fires while the lane still runs. Read the lane's files only after the notice arrives.

```bash
L="$(mktemp -d)"; printf 'lane dir: %s\n' "$L"
node .planning/scripts/cross-ai.mjs --runtime "$RUNTIME" --model "$MODEL" --mode exec \
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
re-invoke the same lane, per section 6 of [`../SKILL.md`](../SKILL.md). When that tool is not
callable in the session, use the print-and-stop path of that section.

## pi

unverified. pi's help shows no notification or one-shot scheduling feature, so a pi host uses the
foreground wait below. Print `retry_after_s`, the state path and the re-invoke command; do not
schedule anything.

## opencode

unverified. opencode's help shows no notification or one-shot scheduling feature, so an opencode
host uses the foreground wait below.

## cursor

unverified. No background primitive is documented for cursor, so a cursor host uses the
foreground wait below.

## codex

unverified. No background primitive is documented for codex, so a codex host uses the foreground
wait below.

## copilot

unverified. No background primitive is documented for copilot, so a copilot host uses the
foreground wait below.

## A host without a background primitive

unverified. Any host above but Claude Code, and any host not listed, gets the foreground wait:
run the runner as a plain command, which blocks until the lane exits, and record its exit code.
Then read `lane.rc` and `lane.err`. Print `retry_after_s`, the state path and the re-invoke
command instead of scheduling a wake.

```bash
L="$(mktemp -d)"; printf 'lane dir: %s\n' "$L"
node .planning/scripts/cross-ai.mjs --runtime "$RUNTIME" --model "$MODEL" --mode exec \
  < prompt.md > "$L/lane.out" 2> "$L/lane.err"; echo $? > "$L/lane.rc"
```
