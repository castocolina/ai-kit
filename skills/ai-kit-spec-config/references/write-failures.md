# When the write is not clean (spec-config Step 4)

Read this only when Step 3 printed anything but `render-toml exit 0`, or when
`$SCRATCH/render-toml-stderr.txt` holds a `WARNING:` line after exit 0. Then go back to SKILL.md
Step 4 for the orders, `config-status` and trust.

## Nonzero exit

**First, check the printed exit status**, before any other report line. Anything but `render-toml exit 0` means the
write is not confirmed (a rejected config can end in a traceback, with no `WARNING:` line;
a `refusing to replace` line means nothing was written (render-toml checks the target before it migrates or writes anything); a `migrated ... to ...` line on stderr means the old roster moved into the target just before the write; a failure after the write,
such as printing stdout, can leave the target already replaced): show
`$SCRATCH/render-toml-stderr.txt` verbatim, `Read` the target and report "Config write NOT
confirmed" with what the target now holds and the `$SCRATCH` path, list any Step 1.6 role
writes (they stand on their own), keep `$SCRATCH` for inspection and stop — never offer trust
after a nonzero exit.

One exception to that stop: when every stderr line is a `render-toml: <key>: effort ...` refusal (a level outside the model's list, or one the runner cannot pass), nothing was written; ask each named lane's effort again, then re-run Step 3. An `is not in the model's list (...)` line names the levels to offer; a `cannot be passed` line names none, so offer the levels Step 2 offered for that model without the refused one. Offer no effort as a choice in both cases. A changed or removed effort drops that lane's `effort_source`, which covered only the tested level.

## WARNING lines after exit 0

**On exit 0, check `$SCRATCH/render-toml-stderr.txt` for any `WARNING:`-prefixed
line.** If one or more are present, the write still succeeded but
`render-toml` left out every item named after `NOT written:` — a rejected lane entry, or an
order key or policy value it rejected — never report a plain success in this case. Name each
item as printed (a dropped order key is not a dropped lane). Surface it clearly, e.g.:
```
Config written to: `<target path>` — but with warnings:
  WARNING: 1 issue(s) found and NOT written: <item detail>
Each item named after NOT written: is not in the file. Review them and re-run if this wasn't intended.
```
