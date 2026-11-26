# Runner details (template 14)

Read when a runner upgrade, a `.new` merge, `ensure-runner`, the template flags, the live
timeout, hand-edited CONFIG `extraArgs`, retry tuning ([runner.retry] in ai-kit's config.toml), or a dispatch
whose `AIKIT-XAI` line shows a
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
  the prompt.
- `--codex-sandbox workspace-write` asks Codex for its `workspace-write` sandbox, not a fixed
  path allowlist: by default it allows writes in the project dir plus `/tmp` and `$TMPDIR`, but
  the owner's Codex config can add writable roots or exclude both temp locations (its
  `sandbox_workspace_write` settings; not verified here). Check the effective writable roots
  before promising a boundary. Whether `.git` is writable under it is unverified. Without the flag, codex exec runs with
  `--dangerously-bypass-approvals-and-sandbox`; every other exec target always runs with full
  permissions (no sandbox, no ask mode), and any guidance it receives is prose, not a boundary.

The call vocabulary (how to read each setting line and status field is [`../../ai-kit-cross-ai/SKILL.md`](../../ai-kit-cross-ai/SKILL.md)); ai-kit's hook builder and Python layer pass `--role`, the lane's settings and `--host auto`:

- `--role execute|review` names the contract; `--mode exec|review` stays an alias, and two values that disagree are a usage error (exit 2).
- `--effort <level>` (any lowercase token; `--codex-effort` stays an alias), `--context <label>`, `--escalate-runtime`, `--escalate-model` and `--session-id <id>`: each named setting prints one `cross-ai: setting` line, `applied`, `ignored` with a reason, or `unknown`, and the status line carries `session=`, `applied=`, `ignored=`, `unknown=` and `escalate=`.
- `--host auto|none`: `auto` runs the lane in a herdr tab when herdr is available; the runner's own default is `none`, and `AIKIT_HOST=none` wins over `auto`. The `host` line reads `applied`, or `ignored` with `no_herdr` or `host_failed`; the run directory `${XDG_STATE_HOME:-~/.local/state}/ai-kit/spec/host/<run token>/` is removed after the lane once herdr confirms the tab close (otherwise only `run.json` is kept for the sweep). A runner killed hard leaves that directory and its tab for the next real run's automatic sweep or `--sweep`, which closes only a tab whose id and complete label match the dead run's record once the runner and the launcher group are both gone; a live group, an unreadable record or unreachable herdr keeps the record.
- `--skill-path <dir>`, `--skill-name <name>` and `--mcp-config <file>` hand a lane skills and MCP servers through the host's own forms only.
- `--argv-file <path>` serves a runtime the runner has no formula for; `--describe` prints the runner's forms, reasons, states, statuses, classes, finding codes and supervision flags as JSON with no model call.
- Supervision flags, not lane settings (no `cross-ai: setting` line): `--idle-timeout <seconds|default>` (the idle watchdog, off unless it or `CONFIG.idleTimeoutS` is set), `--baseline <sha>`, `--plan-id <id>`, `--forbid <path>` (repeatable) and `--sweep` (no spawn, no lock, exit 0), `--pool <provider>:free` (names the pool a quota stop records), `--blocked-status <provider>:free` and `--blocked-clear <provider>:free` (print or delete that pool's blocked-until record; no spawn). A second execute run on one checkout ends `locked` (a bare exit 75, an owner stop); an execute result missing a planned task's commit ends `partial` (exit 1, empty stdout, `cross-ai: finding` lines, the status-line keys `coverage=` and `findings=`).

## Failure ladder

The soft retry series and one session reset plus second soft series run inside a call, configured by
ai-kit's `config.toml` table `[runner.retry]` (the project `.aikit/config.toml` over the user
`${XDG_CONFIG_HOME:-~/.config}/ai-kit/config.toml`, per key; a GSD scope's own values under
`[runner.retry.scopes."<scope>"]`). The owner edits that table; this skill never writes it. The runner
migrates an old `workflow.cross_ai_retry` block and the old user `cross-ai.json` into it once (see the
policy reference). CONFIG also keeps a `retry`
object, the fallback below those two (the built-in defaults come after it, per key; a copy whose CONFIG `retry` predates `hard_every_s` takes that key from the defaults, so an upgraded copy keeps its own `hard_waits_s` list, such as 600, 900, 1800 s, and then checks every 600 s until the cap; set `hard_waits_s = [60, 300]` in `[runner.retry]` for the shipped schedule): do not tune it there, because CONFIG edits only
receive `.new` upgrades. The caller owns the hard waits and notice. CONFIG retains `capS` (at most 14400), `attemptTimeoutS`, `routerBacked`, `runtime` and `idleTimeoutS`; a copy whose CONFIG predates `idleTimeoutS` reads the watchdog as off. `forbiddenPaths` and `admissionPhrases` are optional CONFIG keys, absent from the shipped block: without them the template's seed lists apply, and a value that is not a list of strings keeps the seed with a note. For caller actions on any non-ok
status, see [`../../ai-kit-cross-ai/SKILL.md`](../../ai-kit-cross-ai/SKILL.md).

The hard tier asks for 60 s, then 300 s, then every `hard_every_s` (600 s) until the 4-hour cap, which ends the lane with `stopped=cap`; `hard_every_s = 0` keeps the list-end stop `stopped=hard-waits`. A configured hard wait under 60 s (0 included) runs inside the call when the deadline leaves 60 s after it, else it becomes a 60 s hint. A stated reset time adds one check at that time plus 120 s (floor 60 s, ceiling the cap), named `check=reset` on the report line: the reset check replaces the wait of the check it comes before; the series then resumes from its own count. `bad_request` is an owner stop (exit 69).

## Runner upgrade

`plan_runner_upgrade` upgrades a pristine older runner in place and keeps its CONFIG with two
changes: an old `prefer` becomes `runtime` (its first entry), and a kept `CONFIG.models` id the
new grammar refuses is dropped with a note ending `dropped it, pick a new <runner> model`. Relay
that note: calls on that runner stop with `no_model` until the owner re-picks with `plan-set
script:cross-ai.model.<runner>`, a dry run and an apply. A pristine
current-template runner takes a same-version body fix the same way and is otherwise kept
byte for byte; an edited runner is never replaced — a `.new` file is
written for the owner to merge (`ensure-runner` reports `runner: "new-as-.new"` and `ready:
false` below template 9; v2 `apply` reports `script.active: false`).
So only a newly rendered or successfully upgraded active copy carries the ladder, and the way to
see what a project actually runs is the active runner's line-2 `template=<n>` header, never the
`.new` file.

`ensure-runner` renders or upgrades the project runner. It never overwrites a user-edited runner, and readiness
comes from the JSON it prints (`ready`, `runner`, `notes`), not from whether a `.new` file
exists. A user-edited runner already on the current template is kept as-is and reported ready,
with no `.new` file. An edited runner on an older template gets a `.new` file plus the printed
notes. The shipped template is template 14 (the run lock, the idle watchdog, the execute result checks, `--sweep`, the closed class list with `bad_request`, the periodic hard tier, the blocked-until record, the `--print-argv` capabilities line and the real-home guard for exec lanes inside an ai-kit checkout; no builder emits their flags), so the readiness floor stays template 9, the first that takes the flags ai-kit's builders emit (`--role`, `--host auto` and the lane settings); template 8 added `--runtime` and the retry config. Template 7
has neither `--runtime` nor the configurable retry series; it carries only the fixed
`sameSessionRetries`/`cooldownS` knobs. A hook built with `--runtime` against a project's template-7 copy fails with `unknown
argument` (exit 2) until `ensure-runner` re-renders it: a pristine copy upgrades in place, while an
edited one gets `.new`. Templates 3-6 can still fall back to another CLI. A foreign runner is
never ready. v1
`apply-execution` writes the runner command (`node .planning/scripts/cross-ai.mjs …`) only when
that render is ready.

**Live timeout:** the runner reads `workflow.cross_ai_timeout` the way gsd-core's
`config-get` does: `.planning/[$GSD_PROJECT/][workstreams/$GSD_WORKSTREAM/]config.json`, then the
root `.planning/config.json` only when a workstream lacks the key; no valid value means 300 s. It
uses the smaller of that value and the timeout baked in at apply. The idle watchdog is separate: an idle end is a timed-out attempt inside that deadline, never a second deadline.

**Opt-in skills and MCP servers:** a call passes `--skill-path`, `--skill-name` and `--mcp-config` (above). Hand-editing the generated script's CONFIG `extraArgs` per target still works; the next apply then writes `cross-ai.mjs.new` instead of overwriting the live runner. Review mode refuses (exit 2) any `extraArgs` entry outside the runtime's review allowlist (pi `--skill <path>`), so extras for exec lanes cannot also run review lanes on that runtime. The MCP flags are not allowlist entries: the runner's own formulas turn `--mcp-config <file>` into `--mcp-config <file> --strict-mcp-config` for claude and `--additional-mcp-config @<file>` for copilot, so `CONFIG.extraArgs` cannot add an unreported server to a review lane.

**`.new` is not active:** the live runner keeps its old CONFIG and apply reports
`script.active: false`. Merge `.new` by hand (keep customizations), check the **active**
runner (the runner resolves its config from its cwd, so run it inside the target), and
delete `.new` only when that check passes:

```bash
cd <target> && node .planning/scripts/cross-ai.mjs --print-argv
```

The check passes only when the active runner's line-2 `template=` header names the bundled
template and the printed line names the approved runtime, an installed binary (not `MISSING`),
the approved model and an argv (not `NO MODEL`). `--print-argv` exits 0 in every one of those
cases, so the exit code proves nothing. On any mismatch keep `.new`, dispatch no model and report
the printed line to the owner.

