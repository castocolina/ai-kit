---
spike: 002
idea: session-self-resume
name: claude-resume-while-alive
type: standard
validates: "Given a session whose process is still running, when a timer-fired claude -p --resume <id> starts, then it is refused, queued or forks"
verdict: VALIDATED
related: [001]
tags: [claude-code, concurrency, resume]
---

# Spike 002: resume while the original process is alive

## What This Validates
Given a throwaway session busy for about 40 s in one `claude -p --resume` process, when a
transient timer fires a second `claude -p --resume <id>` 10 s in, then we see whether the second
run is refused, waits, or runs concurrently, and what the transcript keeps.

## How to Run
`bash .planning/spikes/002-claude-resume-while-alive/run.sh <log dir>`

## Investigation Trail
- The busy run (a background shell `sleep 40`) took 48 s and replied `BUSY-DONE`.
- The timer-fired resume started 11 s in, ran concurrently, finished in 4 s with `PERSIMMON`,
  exit 0, the same session id: no lock, no refusal, no warning.
- A final resume asked for every reply in the conversation and listed `OK`, the busy run's lines
  and `BUSY-DONE`, but **not** `PERSIMMON`: the concurrent run's turn is missing from the history
  the session keeps. The still-running process wins; the concurrent turn is silently lost.
- `--bg --resume <id>` exists ("continues that session in the background"); not measured here.

## Results
VALIDATED (hazard confirmed): Claude Code does not guard a session against a concurrent
`--resume`. A wake that fires while the original process lives does run, and its work is lost
from the session. The liveness check before a resume (D-08, D-10 step 4) is load-bearing, not
optional.
