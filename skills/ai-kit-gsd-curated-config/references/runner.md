# Runner details (template 8)

Read when a runner upgrade, a `.new` merge, `ensure-runner`, the template flags, the live
timeout, hand-edited CONFIG `extraArgs`, or a dispatch whose `AIKIT-XAI` line shows a
`status=` other than `ok` comes up. Every status line carries `action=stop`, a clean exit 0
included, so `action=stop` alone is not a trigger. Do NOT load for the stock v2 flow otherwise.
SKILL.md's "Cross-AI execution" section
keeps the permission facts; this file never weakens them.

The hook's runtime id for Cursor is `cursor` (its binaries are `cursor-agent` and a bare `agent`
only when that binary's real path has the basename `cursor-agent`). For the guarded bare `agent`,
the runner scans every PATH entry and accepts the first whose real path has basename
`cursor-agent`, so another CLI's `agent` earlier on PATH does not hide Cursor. An empty PATH
entry is the cwd, so with one a checkout can supply its own `agent -> .../cursor-agent`; avoid
empty PATH entries when running the runner in an untrusted checkout.

## Template flags

Three hook-control flags matter here (since template 3; the runner has others, such as `--no-preamble`
and `--print-argv`, used below). Whether a run gets them depends on who
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

## Failure ladder

The soft retry series and one session reset plus second soft series run inside a call, configured by
`workflow.cross_ai_retry` in the project config or by `{"cross_ai_retry": {...}}` in
`${XDG_CONFIG_HOME:-~/.config}/ai-kit/cross-ai.json`; hand-edit these sources because
`config-set` refuses the project key. Tune neither in CONFIG: edits only receive `.new` upgrades.
The caller owns the hard waits and notice. CONFIG retains `capS` (at most 14400),
`attemptTimeoutS`, `routerBacked` and `runtime`. For caller actions on any non-ok status, see
[`../../ai-kit-cross-ai/SKILL.md`](../../ai-kit-cross-ai/SKILL.md).

## Runner upgrade

`plan_runner_upgrade` upgrades a pristine older runner in place and keeps its CONFIG; a pristine
current-template runner takes a same-version body fix the same way and is otherwise kept
byte for byte; an edited runner is never replaced — a `.new` file is
written for the owner to merge (`ensure-runner` reports `runner: "new-as-.new"` and `ready:
false` below template 8; v2 `apply` reports `script.active: false`).
So only a newly rendered or successfully upgraded active copy carries the ladder, and the way to
see what a project actually runs is the active runner's line-2 `template=<n>` header, never the
`.new` file.

`ensure-runner` renders or upgrades the project runner and, with `--guidance-file`, the guidance
file. It never overwrites a user-edited runner, and readiness
comes from the JSON it prints (`ready`, `runner`, `notes`), not from whether a `.new` file
exists. A user-edited runner already on the current template is kept as-is and reported ready,
with no `.new` file. An edited runner on an older template gets a `.new` file plus the printed
notes. The readiness floor is template 8, the first with `--runtime` and retry config. Template 7 has
neither. A hook built with `--runtime` against a project's template-7 copy fails with `unknown
argument` (exit 2) until `ensure-runner` re-renders it: a pristine copy upgrades in place, while an
edited one gets `.new`. Templates 3-6 can still fall back to another CLI. A foreign runner is
never ready. v1
`apply-execution` writes the runner command (`node .planning/scripts/cross-ai.mjs …`) only when
that render is ready.

**Live timeout:** the runner reads `workflow.cross_ai_timeout` the way gsd-core's
`config-get` does: `.planning/[$GSD_PROJECT/][workstreams/$GSD_WORKSTREAM/]config.json`, then the
root `.planning/config.json` only when a workstream lacks the key; no valid value means 300 s. It
uses the smaller of that value and the timeout baked in at apply.

**Opt-in skills and MCP servers:** hand-edit the generated script's CONFIG `extraArgs` per
target. The next apply then writes `cross-ai.mjs.new` instead of overwriting the live runner.
Review mode refuses (exit 2) any `extraArgs` entry outside the runtime's review allowlist
(pi `--skill <path>` only), so extras for exec lanes cannot also run review lanes on that runtime.

**`.new` is not active:** the live runner keeps its old CONFIG and apply reports
`script.active: false`. Merge `.new` by hand (keep customizations), check the **active**
runner (the runner resolves its config from its cwd, so run it inside the target), then
delete `.new`:

```bash
cd <target> && node .planning/scripts/cross-ai.mjs --print-argv
```

