# Confirming the write (spec-config Step 4)

Read this at SKILL.md Step 4, after its exit-status check, for the wording and order of what it prints. `$SCRATCH` is the run's scratch folder and `<target path>` the target Step 2.1 announced.

## Confirmation and orders

Only when the captured file has no `WARNING:` lines, print a plain summary confirming the write, always including the exact absolute path (repeat it even though Step 2 already announced it — this is the confirmation that the write actually happened, not just the plan to do it): "Config written to: `<target path>`." Then, either way, the resolved `policy.mode` and **each role's priority order** as its own explicit numbered list, read from the `ladder` line of `[lanes.policy.review]` and of `[lanes.policy.execute]` in `$SCRATCH/rendered.toml` (what was actually written, which omits any rejected entry), never re-typed from Step 2's confirmed lists — e.g.:

```
Review order:
  1. review-primary
  2. session-fallback
Execute order:
  1. execute-primary
```

never summarized in a sentence, so the owner sees each fallback sequence without opening the file. If an order differs from the one confirmed at Step 2.2, name the missing keys; a role with no lane has no order.

## Other lines

Show every other stderr line (a migration line, a usage-limited role warning, a legacy-order note) as printed. Name every entry saved untested at Step 2.5 ("untested: `<key>` — its availability is unverified") and every entry saved without a vendor at Step 2.3 ("vendor unknown: `<key>` — the cross-vendor filter cannot exclude it").

## Capability lines

The `capability` lines `config-status` prints show that project's effective roster (project over user, per `strategy`), not only the file just written: label them so, and after a global write say when a `local-only` project file hides the saved lanes there.
