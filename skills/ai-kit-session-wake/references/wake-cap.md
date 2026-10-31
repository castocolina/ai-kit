# The wake cap and session lock (internals)

Load this only to explain a count, a `gave up` notice or a done/disarm blocking question. Do NOT
load it for a plain `status`, `done` or `disarm`; the operational rule is in SKILL.md.

## Cap

A wake fires hourly and gives up after 24 counted fires (`wakes: n/24` in `status`).

- Every fire at or after the first wake time counts, including a fire that only logs because the
  host is still alive or a resume is already running. The fire is counted before either check.
  A resume may run up to 4 hours.
- A fire before a host-reported reset (the first wake time) is not counted.
- A refresh keeps the count; only `disarm` then `arm` starts a new one.
- The 24th counted fire is the last: it logs or resumes, then the wake removes itself with a
  `gave up` notice (journal and a desktop notice). This is the locked hard stop, so a run that
  may last past about 24 hours must expect it.
- A wake also gives up early, before the cap, when the session is no longer found at fire time.

## Session lock

`arm` takes no session lock. `done` (non-blocking) and `disarm` (blocking) take it, which keeps a
running resume and a removal apart. That is why `disarm` can wait up to a resume's 4 hours and
`done` does not.
