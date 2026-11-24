# Trusting a local roster (spec-config Step 4)

Read this only when SKILL.md Step 4 found a command-bearing entry in a local write, or when
`probe-quota` printed `ignoring untrusted project-local config` outside `--check-only`. Until the
file is trusted, its whole project `[lanes]` table stays inactive for cross-AI review.
`<project root>` is the parent of `.aikit/`, never `.aikit/` itself (that looks for
`.aikit/.aikit/config.toml` and exits 1). Go through the steps in order; each one gates the next.

1. **Pending old roster.** `--show` records no new consent, but it is not a pure read: like every
   `trust-local` call it first migrates a pending old `review-spec.toml`, which can carry that
   roster's existing trust record into the new store, and its merged preview can migrate a pending
   old roster in the user config folder too. When an old roster is pending in either place, say so
   before running it. When that roster lies outside the target the owner approved at Step 2.1 (a
   pending global roster after a local write, for example), run neither `trust-local` form: the
   file stays written but untrusted; say that `--show` would migrate that roster and give the owner
   the command to run once the owner agrees to that migration. Stop here.
2. **Preview.** Run `python3 "$TOOLS_PY" trust-local --cwd <project root> --show`. It prints one
   JSON line per project entry that runs as a subprocess (an entry with a `runtime` or a `command`,
   so more entries than the command-bearing ones): `{"key", "argv", "trusted", "path"}`, where
   `argv` is the argument list a review dispatch would run (already merged with the global config
   per `strategy`) with the prompt shown as the literal `<prompt>` placeholder, or
   `{"key", "error"}` for an entry that would be refused.
3. **Match every command-bearing entry.** The preview walks the flattened entry view and renders
   the review invocation: an execute entry that shares a key with a review entry can be missing,
   and a table-runtime execute entry is shown with its review argv. Compare the lines with the
   file's command-bearing entries in both roles. A `{"key", "error"}` line, and a line that renders
   a key's review argv for an execute entry of that key, count as no line for that entry.
4. **Show what the preview does not render.** For any entry without its own line, show the whole
   entry from the file, every field (its fields fill the command's placeholders), and say the
   preview does not render it. An entry with no `command` of its own fills a user-config command's
   placeholders: show that user entry, every field, beside the project entry, naming its role and key. When no such user entry can be
   shown, leave the file untrusted, name the role and key that could not be shown, and stop.
5. **Ask.** Only once every command-bearing entry has been shown, show those lines and ask whether
   to trust the file. Without an explicit yes, run no trusting call. When an entry was shown at
   step 4 instead of its own preview line, put "leave it untrusted" first, as the default, and say
   that its argv was not rendered, so only step 7's field check below covers it.
6. **Trust.** Run `python3 "$TOOLS_PY" trust-local --cwd <project root>`. It prints one JSON line
   per entry for the bytes it trusts, then `trusted <path> sha256=<digest>` (or `nothing to trust:`
   for a file with no command-bearing entry).
7. **Confirm the trusted bytes are the approved ones.** Parse each JSON line of steps 2 and 6 and
   compare them by their shared fields only: `key` with `argv`, or `key` with `error`. The trusting
   call omits `--show`'s `trusted` and `path` fields, and the final `trusted ...` line is a status
   line, not an entry; neither counts as a difference. When an entry differs, is added or is
   missing (the file changed in between), run `trust-local --cwd <project root> --revoke` at once,
   show the new lines and go back to step 3. For an entry shown at step 4 instead of a preview line,
   read the file (and the user config, for an inherited command) again after the trusting call and
   check that every field of each entry shown at step 4 is unchanged since it was shown; on any
   difference, revoke at once and go back to step 3 the same way. The trust digest is the file's
   command-bearing entries with every field (`trust.command_lanes_bytes`), so unchanged entries mean
   the trusted bytes are the approved ones; an inherited user command is outside the digest (the
   user layer needs no trust), and re-checking it only confirms the argv the owner saw. Limit: a change made and undone while the trusting call runs is not
   seen by reads before and after it.

Trust covers the file's command-bearing lane entries: editing another table, comments or spacing
keeps it; changing a command-bearing entry needs a new trust; a file with no command-bearing entry
needs none. `trust-local --cwd <project root> --revoke` withdraws it, and still works after the
file was deleted or moved. After a trust that `probe-quota` asked for, re-run `probe-quota` before
treating its output as authoritative for that project's local entries.
