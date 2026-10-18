# Runner details (template 5)

Read when a runner upgrade, a `.new` merge, `ensure-runner`, the template flags, the live
timeout, or hand-edited CONFIG `extraArgs` comes up. SKILL.md's "Cross-AI execution" section
keeps the permission facts; this file never weakens them.

The hook's runtime id for Cursor is `cursor` (its binaries are `cursor-agent` and a bare `agent`
only when that binary's real path has the basename `cursor-agent`). For the guarded bare `agent`,
the runner scans every PATH entry and accepts the first whose real path has basename
`cursor-agent`, so another CLI's `agent` earlier on PATH does not hide Cursor.

## Template flags

The template understands three flags (since template 3). Whether a run gets them depends on who
builds the argv (see SKILL.md): v2's bare hook passes none of them. Template 4 also runs every
opencode target as `opencode run --standalone` (accepted by opencode v2.0.31; running on a
private server rather than the user's shared opencode service is the flag's stated purpose, not
observed beyond the absence of a port conflict); the `opencode models` check before each run is
read-only and still reaches that shared service.

- `--outer-timeout <s>` replaces the GSD config lookup and the CONFIG cap as the outer deadline.
  The review lane passes it; the GSD hook does not, so the live timeout lookup below applies.
- `--prepend-file <path>` puts that file, minus its leading `<!-- … -->` stamp lines, before
  the prompt. `ai-kit-spec-execute-gsd`'s hook passes the guidance file
  (`.planning/scripts/cross-ai-guidance.md`) this way, with `--no-preamble` keeping the
  runner's own preamble off, so nothing is said twice.
- `--codex-sandbox workspace-write` confines a codex exec target: writes stay inside the project
  dir plus `/tmp` and `$TMPDIR`, which workspace-write always allows. Whether `.git` is writable
  under it is unverified. Without the flag, codex exec runs with
  `--dangerously-bypass-approvals-and-sandbox`; every other exec target always runs with full
  permissions (no sandbox, no ask mode), and any guidance it receives is prose, not a boundary.

## Runner upgrade

`ensure-runner` renders or upgrades the project runner and, with `--guidance-file`, the guidance
file. It never overwrites a user-edited runner, and readiness
comes from the JSON it prints (`ready`, `runner`, `notes`), not from whether a `.new` file
exists. A user-edited runner already on the current template is kept as-is and reported ready,
with no `.new` file. An edited runner on an older template gets a `.new` file plus the printed
notes; it stays ready from template 3 on (the readiness floor: the first template with the hook's
flags), while an edited template-1/2 or foreign runner is not ready until `.new` is merged by hand. v1
`apply-execution` writes the runner command (`node .planning/scripts/cross-ai.mjs …`) only when
that render is ready.

**Live timeout:** the runner reads `workflow.cross_ai_timeout` the way gsd-core's
`config-get` does: `.planning/[$GSD_PROJECT/][workstreams/$GSD_WORKSTREAM/]config.json`, then the
root `.planning/config.json` only when a workstream lacks the key; no valid value means 300 s. It
uses the smaller of that value and the timeout baked in at apply.

**Opt-in skills and MCP servers:** hand-edit the generated script's CONFIG `extraArgs` per
target. The next apply then writes `cross-ai.mjs.new` instead of overwriting the live runner.

**`.new` is not active:** the live runner keeps its old CONFIG and apply reports
`script.active: false`. Merge `.new` by hand (keep customizations), check the **active**
runner (the runner resolves its config from its cwd, so run it inside the target), then
delete `.new`:

```bash
cd <target> && node .planning/scripts/cross-ai.mjs --print-argv
```

