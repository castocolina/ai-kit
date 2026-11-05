# Phase 18 Context (synthetic excerpt for an eval)

## Decisions

### Locked (user decided in an interactive discuss, 2026-10-02)

- D-04: A failed send is retried a fixed three times, with exponential backoff capped at
  30 seconds. A change to the attempt count or the cap needs a new discuss round with the user.

### Open for this discuss

- Whether jitter is added to the backoff delay.
