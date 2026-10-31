# Reset time and the StopFailure hook

Load this when the host reports a usage-limit reset time or when asked about the hook. Do NOT
load it for `status`, `done` or `disarm`.

## Reset time

When the host reports a usage-limit reset time, pass it so the first wake lands after the reset:

- `--reset-text "<the host's limit line>"`: parsed into a reset time, inferred from the host's
  wording.
- `--reset-at <epoch or ISO 8601 with Z or an offset>`: a reset time you already read from the
  host.

Both are recorded as inferred (`reset: <time> (inferred)`), never as stated by the host; the wake
lands 60 s after the reset.

## Opt-in StopFailure hook

The `session-wake` StopFailure hook (Claude Code, `rate_limit`) passes the host's reset text to
`arm --only-if-armed`, so it refreshes a wake that is already armed and never arms one. It is
opt-in through the ai-kit installer's hook selection, experimental, and its payload is unverified.
