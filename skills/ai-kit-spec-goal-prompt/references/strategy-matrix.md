# Strategy matrix

How the script picks one to three strategies, row by row, and how it drops a request.

Load when: before overriding or explaining a strategy (SKILL.md §2), or when detect's
`strategies` or `dropped` look surprising.

## How the selector works

- Inputs: the scope kind (`opengsd`, `gsd-unproven`, `superpowers`, `both`, `none`), the user's
  request (`goal`, `loop`, `autonomous` or none), the primitive table, and two derived flags.
- Derived, never asked: `must_outlive` is true when the work has more than one phase or plan.
  `provable` is true when an e2e command exists and there are no mockups.
- A row fires when its scope, request, needs, outlive and provable columns all match; a column set
  to `None` matches anything. A `needs` column means a primitive of that kind is not `absent`.
- One strategy per id: the lower rank wins, and on equal rank the earlier row wins. The result is
  ordered by rank, then by row order, capped at three. Exactly one is recommended.
- If no row fires, the fallback row M09 fires.
- A requested goal or loop whose primitive is missing goes to `dropped`. It is never emitted.
- A scope with an open question (`scope.ask`) has no strategies until the question is answered.

## Rows

- M01: OpenGSD scope, no request or an `autonomous` request. Strategy `autonomous`, rank 1, the
  `/gsd-autonomous` line with `--from`, `--to` or `--only`, and `--converge`.
- M02: OpenGSD scope, user asked for `goal`. Strategy `goal`, rank 1; needs a goal primitive.
- M03: OpenGSD scope, user asked for `loop`. Strategy `loop`, rank 1; needs a loop primitive.
- M02b: OpenGSD scope, user asked for `goal` or `loop`. Strategy `autonomous`, rank 2, listed
  behind the request.
- M04: a non-OpenGSD scope (superpowers, gsd-unproven or none), needs a goal primitive, provable.
  Strategy `goal`, rank 1.
- M05: as M04, not provable (mockups, or no e2e). Strategy `goal`, rank 2; the condition needs a
  human check.
- M06: a non-OpenGSD scope, needs a loop primitive, must outlive the session, not provable.
  Strategy `loop`, rank 1.
- M07: as M06, provable. Strategy `loop`, rank 2.
- M08: scope `gsd-unproven` only. Strategy `autonomous`, rank 3, labelled `unverified`: whether
  the workflow exists on that install is unverified.
- M09: fallback, used only when no other row fires. Strategy `plain`, rank 9. The plain prompt
  relies on an OS-timer wake, which is flagged unverified.
- M11g: a non-OpenGSD scope, user asked for `goal`. Strategy `goal`, rank 0.
- M11l: a non-OpenGSD scope, user asked for `loop`. Strategy `loop`, rank 0.

## Why an OpenGSD scope gets only `autonomous`

M01 fires for every OpenGSD scope with no request, and its strategy is `autonomous`. The goal and
loop rows fire only when the user asked for them. So an OpenGSD run with no request has one
strategy. Its first line carries only the flags, because the workflow greps all of its arguments.

## Superpowers scope

- A user request for `autonomous` on a superpowers scope has no row. It is dropped with the reason
  `/gsd-autonomous needs a GSD phases work set on this scope`.
- `goal` on a superpowers scope uses M04, M05 or M11g, depending on provability and the request.
- `loop` uses M06, M07 or M11l, depending on whether the work outlives the session and on
  provability.

## Inline and pointer form of a `/goal` block

Only the `goal` strategy has two forms; loop, autonomous and plain blocks never change.

- Inline: the whole condition is on the `/goal` line. The renderer refuses an inline condition
  over `GOAL_BUDGET` (1,800 characters) and over `GOAL_CAP` (4,000 code points).
- Pointer: the `/goal` line is `/goal read document` + the file's own repository-relative path
  (the final unique path from `choose_path`) + `at section` + `Full goal` + `and finish only when
  that section's DONE WHEN conditions hold`. The condition moves, unchanged, to a `## Full goal`
  section at the bottom of the file, wrapped at about 100 columns with no per-line cap. The
  1,800 and 4,000 refusals do not apply to it. The `## Rails` line caps still do.
- `goal_style` in the answers picks the form: `auto` (default) uses the pointer when the inline
  condition is longer than `GOAL_POINTER_THRESHOLD` (1,000 characters: below the 1,800 budget, and above the fixed text of about 300
  characters plus the scope clause cut at 600, so only a long objective crosses it); `inline` and
  `pointer` force one.
- Render prints `goal_form` (`inline`, `pointer` or `null` when no `/goal` block exists) and, in the
  pointer form, `full_chars` in the `conditions` entry and a warning that the host's behaviour is
  unverified.

## The loop block

Only a `loop` strategy whose primitive is the `/loop` row is typed as `/loop 30m ...`; its label is
that row's own availability. A schedule or wake tool (`CronCreate one-shot`, `CronCreate recurring`,
`ScheduleWakeup`) renders a plain paragraph that names the tool as the QUOTA A wake, never an
interval loop. An OS timer or no primitive renders the plain paragraph.

## A long objective

The OBJECTIVE rule line holds at most one 200-character line. When the user's `objective` is
longer, the line is cut with `...` and ends with `(full text: <path> section Full objective)`,
where `<path>` is the file's final unique path. The file then ends with a `## Full objective`
section (before `## Full goal`) that holds the whole objective, wrapped at about 100 columns
with no line cap. Render prints `full_objective` as `true` in that case. A cut scope clause
(many plan titles) does not add the section: the titles are in the plan files.

## Unverified

- Original GSD (`gsd-unproven`): `/gsd-autonomous` may not exist on that install. M08 offers it
  last, labelled `unverified`.
- Whether the host follows `/goal read document ... at section ...` (the pointer form). No live
  run has shown it. Render prints a warning for it each time and the paste text stays valid
  without it: the pointer names the file and the section.
- Whether a multi-line `/gsd-autonomous` paste is parsed by its flags as intended. That the paste
  arrives whole is observed (see evidence.md); the flag parse is simulated from the workflow's own grep.
- The `native_execution` answer: its wording effect is coded for OpenGSD cross-AI and not checked
  in a live run.
