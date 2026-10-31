# `arm` exit 2: which kind, which action

MANDATORY when `arm` exits 2. Do NOT load it for exit 0 or 3, or for `status`, `done` or `disarm`.

Relay the stderr line first. Then match it to one row; the action column is the only follow-up,
and it is one of: continue the run, run `status`, run `disarm` (plus one re-`arm` after an invalid
state). The run goes on in every
case (never fail the run on the wake).

| stderr contains | kind | wake state afterwards | action |
|---|---|---|---|
| `systemctl daemon-reload failed`, `restart ... failed` or `enable --now ... failed`, with `previous wake restored` | timer step failed on a refresh | the old wake is unchanged | continue |
| the same, with `rollback failed: ...` on a refresh | timer step failed on a refresh | uncertain (state, units or timer may differ from before) | `status` |
| the same, nothing after the failure, on a first arm | timer step failed on a first arm | rolled back, no wake | continue |
| the same, with `rollback failed: ...` on a first arm | timer step failed on a first arm | files deleted, but the timer may still be enabled or running in systemd, or the daemon state stale | `disarm` |
| `invalid state (...); run disarm first` | recorded state unreadable or mismatched | no usable wake | `disarm`, then `arm` once |
| anything else (no session id, cross-AI child, `pass --pid` or a wrong `--pid`, unknown host, session not found, host CLI or interpreter not usable, invalid `--permission-mode`, sibling `ai-kit-spec-review` missing) | refused before any write | none armed | continue; retry only with a value the host or owner gave |

A first arm has no wake recorded yet, so a failed one deletes every file it wrote. A refresh
replaces an existing wake, so a failed one restores the previous state and units and deletes
nothing.

`done` and `disarm` also exit 2 when no session id can be resolved or the host is unknown (for
example on pi without `--session-id`); relay it and continue.
