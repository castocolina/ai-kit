# The pair test call (spec-config Step 2.5)

Read this before the first write-risk question or `check-reviewer` test call of a run (SKILL.md Step 2.5; `wizard-flow.md` steps 5 and 6 send every chosen lane there). `$TOOLS_PY` is the literal path SKILL.md Step 0 printed and `<catalog>` the path Step 1.5 printed.

## Write risk

When the runtime's profile (read at Step 2.4) has `read_only: unconfirmed`, the test runs that CLI from a private temporary directory, not from the working tree, but with its normal write permissions, so nothing stops it from writing to other paths you can write, your files included. The question, asked with "skip the test" first/default: "Note: `<id>` has no confirmed read-only invocation — its test call starts in a private temporary directory but runs with the CLI's normal write permissions, and every later run uses them against your working tree. Run the one test call now, or skip the test?" A runtime with no profile file is treated the same way, because nothing confirms a read-only invocation for it.

## Why the call is needed

The runner does not refuse an unusual id shape: it prints a shape note and still runs it; it refuses an id only when the runtime's live model listing succeeds and lacks it (`bad_model`), and the CLI itself may reject an id. Step 2.5's live test is the check that the chosen id works.

## Arguments and the usability record

Leave `--vendor` out for a lane saved without a vendor. Pass `--catalog-path <catalog>` to `check-reviewer` so the result can be recorded as the pair's usability: the printed `usability` object says whether it was (`recorded`, with a `problem` when not, for example a pair the catalog does not list; no `usability` object means nothing was recorded), so report a catalog update only when `recorded` is true; a custom entry has no runtime, so its test records nothing. `--extra-json` carries the lane's other knobs (`service_tier`, `cursor_mode`, a custom entry's template fields), never `effort`: the command refuses an effort together with `--catalog-path`, so this call tests the pair without its chosen effort, and the effort level gets its own call (`wizard-flow.md` step 5).

## A custom entry

A custom entry (no `runtime`) is tested the same way with `--command '<template>'` instead of `--runtime`.

## What the call prints

This makes one real call through the runner or the custom launcher (the same mechanism `probe-quota` uses later) and prints `{"available": bool, "detail": "..."}`. When `available` is `false`, the `detail` message is the CLI's own real error text — e.g. a bad model id, an auth problem, or a plan/entitlement gate like `cursor`'s Free-plan restriction — which is why SKILL.md Step 2.5 shows it verbatim before asking whether to keep the entry.
