# Execute result checks

The detail behind the execute result checks in the ai-kit-cross-ai skill: which tasks count,
the finding codes in print order, and which result wins. Section numbers refer to
[`../SKILL.md`](../SKILL.md).

After a spawned execute run the runner checks the result against the prompt's plan and the commits since the run's baseline. Planned tasks are the prompt's `<task>` blocks whose type is absent or not a checkpoint type, each with its `<name>` and `<files>`; a task is covered when a commit since the baseline touched one of its files (a trailing `/` covers a directory), and a task with no files, or only glob patterns, is unchecked. Each finding prints one `cross-ai: finding reason=<code> detail=<text>` line before the status line (values redacted, control characters removed, at most 10 paths or phrases, then `(+N more)`), in this order:

| # | Finding | Result | Meaning |
|---|---|---|---|
| 1. | `no_commit` | partial | exit 0 with an answer and planned tasks, but no commit since the baseline |
| 2. | `task_uncovered` | partial | a checkable task has no covering commit, or the `--plan-id` commit count is short; the missing task names are printed |
| 3. | `admits_skipped` | partial | the answer holds an admission phrase outside fenced and inline code; the phrase is printed |
| 4. | `forbidden_path` | contract_violation | a forbidden path changed (committed or not) and the prompt's `<files>` does not name it |
| 5. | `no_tree_change` | info | the lane printed output but changed nothing in the checkout for the idle time |
| 6. | `outside_plan_files` | info | paths changed outside the prompt's `<files>`, counted |
| 7. | `uncommitted_edits` | info | the end tree differs from HEAD in paths that were clean at the baseline |
| 8. | `baseline_replaced` | info | the stored baseline was replaced; the reason is printed |
| 9. | `coverage_unchecked` | info | tasks the runner could not check |

`contract_violation` wins over `partial`, and `no_change` (a clean tree) wins over both. `partial` (exit 1) writes no answer to stdout, so GSD cannot record it as a summary. An execute run that ends with another status still prints its findings: they are the missing list for the resume. Files the owner left dirty and never touched are never the lane's. A lane hosted in a herdr tab is checked by the same rules on the same inputs.

## Baked defaults

Their baked defaults sit beneath the call: `CONFIG.idleTimeoutS` (shipped as 0; 0 or absent is off), and two seed lists in the runner that an optional CONFIG key replaces: `CONFIG.forbiddenPaths` (seed `.planning/STATE.md`, `.planning/ROADMAP.md` and `.planning/REQUIREMENTS.md`, the files GSD's orchestrator owns) and `CONFIG.admissionPhrases` (a short seed of lowercase phrases, labeled judged). Neither key is in the shipped CONFIG; a value that is not a list of strings prints `cross-ai: note: CONFIG.<key> is not a list of strings; the seed list is used`. A seed never decides which runtime or model runs; the owner replaces it in CONFIG, and every match is printed.

## Evidence

- The admission phrases are a judged seed from earlier execute reports that admitted skipped work; their recall is unverified.
- The forbidden-path default is the set of planning files GSD's orchestrator owns and writes itself.
