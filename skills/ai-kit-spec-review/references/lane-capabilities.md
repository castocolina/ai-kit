# Lane capability block, lenses and refusals — full detail

Read this when a lane's capability block, a lens note or a refusal reason must be explained
(an exit 65, a lens that was not sent), or when the owner asks to run the after-approval pass.
SKILL.md keeps the rules the loop acts on: an exit 65 spawns no lane and switches no lane, and
the after-approval pass is owner-started only.

## Lane capability block, lenses and refusals

A subprocess lane is told only what its own final argv allows. `dispatch-reviewer` and
`dispatch-execute` read the lane's runner dry run (`--print-argv`: the `cross-ai: capabilities`
line and the `setting skill=`, `setting mcp=` and `skill-block` lines), resolve tools against the
PATH of the exact child environment, and prepend one block with these sections, in this order:
`LANE`, `ACCESS`, `TOOLS`, `CODE INDEX`, `SKILLS`, `SETTINGS`. An `unknown` fact reads
`unknown: make no assumption`; a lane without a shell is told about no shell tool. An execute lane whose `write` is `full` or `unknown` also gets the no-confinement sentence word for word (never write outside the working directory); a `workspace` or `none` lane gets none. A native lane
gets no tool claims, only its lens names (see SKILL.md Step 1's native route). `capability-block --runtime <id>
--model <id> --role <review|execute> [--files ...]` prints the same block without spawning the
lane. On a claude lane the run-scoped MCP file is passed with `--strict-mcp-config`, so it replaces the host's other MCP servers for that lane. Field values and the code index routes: [`cross-ai-dispatch.md`](cross-ai-dispatch.md#lane-capabilities).

A skill's role comes from `[skills.roles]` (a sort the owner confirmed), then the seed file
`references/skill-roles.json`, else `unsorted`; `skill-table` prints the per-host scan, which runs
on every call.

| Role | Meaning |
|---|---|
| `review_lens` | read-only advice lens, sent to review lanes |
| `edit_lens` | lens that edits files, used only by the after-approval pass |
| `ui_lens` | sent only when a `--files` value is a UI file |
| `code_index` | code index server, enabled for a lane only from a seed launch form found on the child's PATH |
| `decision_helper` | advisory decision helper |
| `host_control` | terminal or host control |
| `skill_judge` | skill reviewer |
| `unsorted` | no seed row and no confirmed sort |

Lenses ride the runner's `--skill-name` and `--skill-path` flags; its `setting skill=` line says the
form used (`path` or `prose`). A lens that is not sent gets one note, and the base prompt is never cut:

| Note | When |
|---|---|
| `built_in_no_file` | a host built-in with no file, for any lane but a native lane of that host |
| `over_window` | it would push the prompt past the lane's window or argv cap; skipped whole |
| `path_rejected` | its path fails the value check, or its body is not strict UTF-8, starts with a byte-order mark, exceeds 65,536 bytes or has no addressable name |
| `not_present` | its `SKILL.md` is empty |
| `host_cannot_load` | the runner reported it `ignored` |

Last before the spawn, the dispatch checks every `--files` value, lens path and run file, and
compares the prompt's estimate (UTF-8 bytes of the block, lens text and prompt divided by 4,
rounded up, labeled estimated; the runner's preamble and the host's own system prompt are not
counted) with the lane's known window (a `[[models.context]]` entry, then the catalog); without `--files` no block is built and nothing is
checked, and stderr says so. A window is
unknown, and never capped, when none is recorded, when the recorded value is not a positive
integer, or when the lane applies a context form whose effect is unverified and no user value
exists. A refusal spawns no lane, writes one JSON record `{"status": "refused", "reason": ...,
"detail": ...}` to stderr and exits 65; Step 1 counts it as that lane's failure. Nothing is
trimmed or rewritten.

| Reason | When |
|---|---|
| `prompt_over_window` | the estimate exceeds the known window (equal passes) |
| `value_control_char` | a value holds a control, bidirectional or zero-width character |
| `path_outside_roots` | a path resolves outside the repository and every scanned skill root (a review document may also lie in its own worktree) |
| `path_unresolvable` | a value is empty, not a string, or cannot be resolved |

After-approval pass: an owner-started command, off unless `[review] edit_lens_pass = true`; the
review loop never starts it and an unattended run never runs it. After an Approved outcome (an `Approved (partial)` one included) the
owner may run `edit-lens-pass --cwd <CODEBASE_ROOT> --files <the approved files>`: it runs the
present `edit_lens` skills on one execute lane whose `write` is `workspace` or `full` (at present only codex lanes report one: `full` for a plain codex lane, `workspace` with `--codex-sandbox workspace-write`; with no such lane it says so and runs nothing), prints the
diff summary and leaves the edits uncommitted until `edit-lens-pass --cwd <CODEBASE_ROOT> --accept`
or `--reject`. A rejection restores only the listed files the pass recorded; a file changed after
the pass is left alone and named, and then the record is kept and the command exits 1. Edits
outside the listed files are neither recorded nor restored: check `git status` before accepting.
