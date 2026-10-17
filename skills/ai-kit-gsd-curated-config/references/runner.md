# Runner details (template 3)

Read when a runner upgrade, a `.new` merge, `ensure-runner`, the template flags, the live
timeout, or hand-edited CONFIG `extraArgs` comes up. SKILL.md's "Cross-AI execution" section
keeps the permission facts; this file never weakens them.

The hook's runtime id for Cursor is `cursor` (its binaries are `cursor-agent` and a bare `agent`
only when that binary's real path has the basename `cursor-agent`).

## Template flags

Template 3 understands three flags. Whether a run gets them depends on who builds the argv (see
SKILL.md): v2's bare hook passes none of them.

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
with no `.new` file. An edited runner on an older or foreign template gets a `.new` file plus the
printed notes and is not ready until that file is merged by hand. v1
`apply-execution` writes the runner command (`node .planning/scripts/cross-ai.mjs …`) only when
that render is ready.

**Live timeout:** the runner reads `workflow.cross_ai_timeout` from `.planning/config.json`,
or from `.planning/workstreams/$GSD_WORKSTREAM/config.json` when `GSD_WORKSTREAM` is set, and
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

