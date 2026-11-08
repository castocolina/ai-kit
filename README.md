# ai-kit

Personal agent skills and slash commands by uz, with a one-line installer that
wires them into Claude Code. The skills follow the [Agent Skills](https://agentskills.io)
open standard, so they also work on any conformant tool (OpenCode, Codex CLI,
Gemini CLI, Cursor, Copilot CLI, Kiro, and others).

## Install

```bash
curl -fsSL https://raw.githubusercontent.com/castocolina/ai-kit/main/tools/install.sh | bash
```

or with `wget`:

```bash
wget -qO- https://raw.githubusercontent.com/castocolina/ai-kit/main/tools/install.sh | bash
```

The installer clones the repo into `~/.local/share/ai-kit`, symlinks every skill,
command, and agent into `~/.claude/`, and points your status line at the bundled
`tools/claude-status-line.py`. It is **idempotent** — re-run it any time to update.

## Contents

| Name | Type | Use case |
|---|---|---|
| [`ai-kit-spec-review-checklist`](skills/ai-kit-spec-review-checklist/SKILL.md) | skill | Audit-only reviewer for design/plan documents. Framework-aware (EARS, RFC-2119, Given/When/Then, OpenSpec, Spec Kit, GSD, …). |
| [`ai-kit-spec-review-fixer`](skills/ai-kit-spec-review-fixer/SKILL.md) | skill | Fixer that addresses each finding from a `ai-kit-spec-review-checklist` report, in place. |
| [`cst-refactor`](skills/cst-refactor/SKILL.md) | skill | LibCST-based Python codemod helper — multi-file renames and signature changes that survive comments and formatting. |
| [`markdown-to-pdf`](skills/markdown-to-pdf/SKILL.md) | skill | Convert a Markdown document with embedded mermaid diagrams into a **PDF** (or a **marp** slide deck) — every ` ```mermaid ` block is auto-rendered with `mmdc` and embedded; auto-selects the best installed backend (Typst/Pandoc, LaTeX, WeasyPrint, Chromium) and never auto-installs. |
| [`ai-kit-cross-ai`](skills/ai-kit-cross-ai/SKILL.md) | skill | Canonical guide to calling, waiting for and chaining the cross-AI runner, with the caller-owned hard tier and never switching harness, provider or model. |
| [`ai-kit-session-wake`](skills/ai-kit-session-wake/SKILL.md) | skill | Arms, checks and disarms a per-session systemd user-timer wake that resumes this exact session id after the orchestrating agent stalls on its own usage limit or its process dies. Not for cross-AI subprocess limits. |
| [`ai-kit-spec-review`](skills/ai-kit-spec-review/SKILL.md) | skill | Review-and-fix loop over (runtime, model) pairs: native when the host can select the model, otherwise the supervised runner (`claude` is review-only). Loops until approved. |
| [`ai-kit-spec-config`](skills/ai-kit-spec-config/SKILL.md) | skill | Wizard for the reviewer config: picks (runtime, model) pairs, writes `review-spec.toml`; a runtime outside the runner table is a trust-gated custom command. |
| [`ai-kit-spec-execute`](skills/ai-kit-spec-execute/SKILL.md) | skill | Router: detects which framework (GSD, superpowers, …) generated a plan/phase, then hands a GSD phase to GSD's own `/gsd-execute-phase` and a superpowers plan to `ai-kit-spec-execute-superpowers`. |
| [`ai-kit-spec-execute-superpowers`](skills/ai-kit-spec-execute-superpowers/SKILL.md) | skill | Resolves a live-quota-checked (runtime, model) pair for each task of a superpowers implementation plan and injects it at `superpowers:subagent-driven-development`'s implementer-dispatch point, leaving that harness's TDD enforcement, review and fix-loop intact and, after the final review, folds the finished plan into one commit per logical feature through `ai-kit-commit-fold` (push and PR stay with ai-kit's unit flow). Not for `superpowers:executing-plans`. |
| [`ai-kit-project-rules-agents`](skills/ai-kit-project-rules-agents/SKILL.md) | skill | Checks an AGENTS.md/CLAUDE.md file against ai-kit's own 19-rule house ruleset, then wraps `/agent-md-refactor` to remediate gaps. |
| [`ai-kit-project-rules-makefile`](skills/ai-kit-project-rules-makefile/SKILL.md) | skill | Checks a target repo's Makefile target shape — validate-<category> alias chain, recipe length, Docker build-before-up, shellcheck threshold. Detects and reports only. |
| [`ai-kit-project-rules-precommit`](skills/ai-kit-project-rules-precommit/SKILL.md) | skill | Checks Makefile↔pre-commit parity (both directions), classifies pre-commit tooling into the 6-category taxonomy, and flags enable-everything configs, missing Duplicate-code/Dead-code tooling, and ruff/golangci-lint anti-patterns. Detects and reports only. |
| [`ai-kit-project-rules-arch`](skills/ai-kit-project-rules-arch/SKILL.md) | skill | Checks that a repo's `arch-test`-shaped Makefile target exists, is chained into `test`, and (where discoverable) is AST-only rather than importing/executing the module it architecturally checks; states the per-stack canonical-tool baseline. Detects and reports only. |
| [`ai-kit-project-rules-docker`](skills/ai-kit-project-rules-docker/SKILL.md) | skill | Checks a target repo's local-dev Docker Compose conventions — the eight-member `docker-*` Makefile target family, the local-dev runbook, healthcheck timing bounds, `depends_on` discipline, and hot-reload bind-mount-plus-override wiring. Detects and reports only. |
| [`ai-kit-project-rules-cicd`](skills/ai-kit-project-rules-cicd/SKILL.md) | skill | Checks that a target repo's CI config (`.github/workflows/*.yml`/`.gitlab-ci.yml`) reuses commands already defined in a Makefile target, pre-commit hook, `package.json` script, or Gradle build task rather than duplicating a tool invocation inline. Detects and reports only. |
| [`ai-kit-project-rules-all`](skills/ai-kit-project-rules-all/SKILL.md) | skill | Runs all 6 `ai-kit-project-rules-*` checkers (agents, makefile, precommit, arch, docker, cicd) against a target repo and merges their findings into one cross-domain, criticality-ordered report, preserving the AGENTS.md-only `/agent-md-refactor` hand-off. Detects and reports only. |
| [`ai-kit-commit-fold`](skills/ai-kit-commit-fold/SKILL.md) | skill | Folds a finished GSD or superpowers plan into one commit per logical feature by one written policy: a tree proof, a local backup tag, a compare-and-swap ref move and a five-line report. A GSD wave-end capability command and a read-only status backstop; the `jev-fast-decision` skill proposes the grouping when installed. The unit flow (`fold.py start`, `checkpoint`, `ready`, restack, hotfix, merge-chain) folds and pushes a unit's branch and opens its PR, only with push consent. |
| [`ai-kit-gsd-curated-config`](skills/ai-kit-gsd-curated-config/SKILL.md) | skill | v2-primary GSD config pipeline: inventory, recommend, plan-set/unset, apply (dry-run + backup), the template-8 cross-ai.mjs runner (`ensure-runner`, one CLI per call with a configurable soft ladder, no automatic fallback), skill wiring, and grouped follow-ups; kept v1 one-question `model_profile` path that writes the runner command; pi not live-validated; cursor validated headless (interactive confirmation pending); config keys written only through gsd-tools (a failed apply restores the backup bytes directly). |
| [`ai-kit-gsd-spec-discuss`](skills/ai-kit-gsd-spec-discuss/SKILL.md) | skill | Chains GSD `/gsd-spec-phase` then `/gsd-discuss-phase` over a phase range in one of two run modes, auto (spec `--auto`, assumptions-mode discuss) or interactive (discuss with `--analyze --all --batch`, the user answering), settling gray areas through an optional local → consented-remote → own-reasoning decision ladder, asked of the shared `jev-fast-decision` skill (advisory; it owns the backends and the consent ask), with decision logs, a deferred ledger, engine-checked Edge Coverage and a best-over-easy (or `mvp_mode`) design rule. Works with no decision backend. |
| [`ai-kit-spec-goal-prompt`](skills/ai-kit-spec-goal-prompt/SKILL.md) | skill | Builds a ready-to-paste `/goal`, `/loop` or `/gsd-autonomous` prompt file (one-shot goal, autonomous run) for GSD phases or superpowers plans, with rails, quota directives and e2e-based done. Detects host primitives (labelled verified or unverified), picks one to three strategies, writes a committable file. Never runs the prompt. |
| [`ai-kit-usage-metrics`](skills/ai-kit-usage-metrics/SKILL.md) | skill | Runs the local capture-refine-dashboard pipeline over Claude Code, opencode, Codex and Cursor session logs, plus previously stored CLI command history, then opens a static, filterable HTML usage-metrics dashboard. Does not export or import data. |
| [`jev-fast-decision`](skills/jev-fast-decision/SKILL.md) | skill | Shared System One client: one backend table (local Laya, TypeSafe), `--probe`, one escalation ladder with a per-item trail, a consent record, an answer log, a dated capability matrix, one entry point for every caller (`ladder`, `detect`, `consent`) and the installed-skill lookup callers copy — advisory only. Linked for claude/opencode and pi; codex is a documented gap (`~/.agents/skills` is shared by other hosts) and cursor is reached through its `~/.claude/skills` compatibility read (cited in `reference.md`, not live-verified). |
| [`ai-kit-judge`](agents/ai-kit-judge.md) | agent | Read-only native judge lane for Claude Code (Opus at xhigh effort, set in its frontmatter; Read, Grep and Glob only): follows the given prompt and replies only with what it asks, such as verdict JSON lines. Linked to `~/.claude/agents/ai-kit-judge.md`. |

## How the installer works

The repo is the source of truth. `tools/install.sh`:

1. **fetch** — clones (or `git pull`s) the repo into `~/.local/share/ai-kit`; falls back to a tarball download when `git` is absent.
2. **verify** — enumerates `skills/`, `commands/`, and `agents/` and validates each entry's shape (skills need a `SKILL.md`; commands/agents need Markdown with frontmatter). Malformed entries are skipped with a warning.
3. **link** — symlinks each valid entry into `~/.claude/<category>/`. Existing real files and symlinks that point outside ai-kit are never touched. The `jev-fast-decision`, `ai-kit-cross-ai`, `ai-kit-session-wake` and `ai-kit-commit-fold` skills are additionally linked into `${PI_CODING_AGENT_DIR:-~/.pi/agent}/skills` for pi, derived from the same selection (opencode reads `~/.claude/skills`; nothing is ever linked under `~/.agents/skills`; codex and cursor have no link — see the skill's reference for their status). A missing pi agent dir is skipped with a message, never created.
4. **prune** — removes broken symlinks under `~/.claude/` that point into the install dir, so deleting a skill from the repo and re-running cleans up after itself.
5. **statusline** — sets `statusLine` in `~/.claude/settings.json` to the bundled `tools/claude-status-line.py` (a backup is written to `settings.json.bak`).

Adding or removing skills/commands/agents needs no change to the script — entries are discovered dynamically. The interactive wizard asks before it touches real content at a link path: if a skill path holds a real directory or a foreign symlink, a confirmation gate (default No) offers to back it up into the same XDG-state backups dir and link the repo copy — the same move the headless `--replace-existing` flag makes, and the backup destination is printed after the wizard exits.

`cursor-agents/` holds ai-kit's own Cursor executor subagents, `composer-worker` and `grok-worker`, each pinned to an explicit non-fast model id. They stay out of `agents/` because that directory links into `~/.claude/agents`, where Claude would load an unrunnable pin. The Cursor CLI reads subagents only from a project's `.cursor/agents`, so automated per-file linking is backlog 999.7. Until then, from a project root link one file by hand: `ln -s <ai-kit checkout>/cursor-agents/composer-worker.md .cursor/agents/` (never link the directory; owner decision 2026-10-18).

### The install wizard

After the repo is fetched, `install.sh` launches `tools/setup.py` — a
full-screen **Textual** wizard with four steps: **Choose** (one card per kind of
component that has items: skills, agents, commands and hooks, walked with Enter),
**Arrange** (one pane per detected status-line host, each with a 2-D layout
board that arranges status-line segments visually instead of hand-editing TOML),
**Review & confirm**, and **✓ ai-kit is installed** (Done). You can also reach it directly:

```bash
uv run tools/setup.py            # interactive install
uv run tools/setup.py reconfigure   # reload your current selection + layout
make install                        # same as install.sh — launches the wizard
```

`reconfigure` pre-loads your current TOML layout so the board reflects reality
before you make changes.

**`uv` and `textual` are wizard-only.** The status-line render path
(`tools/claude-status-line.py`) stays plain `python3 -S` with zero dependencies —
`uv`/`textual` are never required at render time and are never installed into
your system Python. On first launch, if `uv` is missing, the wizard asks
consent and installs it via the official [astral installer](https://astral.sh/uv);
then re-execs itself under `uv run` so PEP-723 inline deps resolve `textual`
into an ephemeral environment.

**Fail-closed / interactive-only.** The wizard requires a real terminal. If
there is no usable TTY, or `uv`/`textual` cannot be obtained, or the terminal
is too small to render the TUI, it prints a clear reason and exits non-zero.
There is no plain-menu fallback, and the wizard itself never falls back to
headless defaults — this is deliberate. A separate, explicit
`setup.py install --headless` exists for CI and containers (see [Headless
install](#headless-install-ci--containers--no-tty) below); it is opt-in per
piece, and a bare run only removes dead ai-kit links, so it is not a "headless defaults" mode.
A clean `Ctrl-C`, `q`, or `esc` abort leaves the original config intact.

The picks screen includes a **HOOKS** group with one row per hook knob:
`session-briefing`, `tool-advisor`, `tool-reminder`, `decision-probe`,
`precompact` and `session-wake`. Defaults set the initial checkboxes. Checked rows are installed;
unchecked rows remove that ai-kit hook from every host where it is installed.
The precompact row wires Claude's `PreCompact` producer and compact
`SessionStart` injector, plus symlinks the pi extension and experimental
opencode plugin when those host directories exist. The review counts hook rows
separately from components.

#### Choose keys

The Choose step shows one card per component kind that has items (skills,
agents, commands, hooks, in that order), one card per screen, titled
`Choose <kind> to install` with the selected count on its border. `enter` goes
to the next kind's card and `esc` back to the previous one; the last card's
`enter` continues to Arrange. The header counts every screen: `Step i of N`,
where N is the number of cards, plus one for Arrange when a status-line host is
detected (all host panes share it), plus one for Review. With skills, agents
and hooks and a host, that is `Step 1 of 5` to `Step 5 of 5`.

The cards list what is in this checkout: every folder under `skills/` with a
`SKILL.md`, and every `.md` file with frontmatter under `agents/` and `commands/`.
Each row shows the frontmatter `name:` (the folder or file name when there is
none) and its `description:`; when the name is not the folder or file name, that
name follows, dimmed, because it is what gets linked.

| Key | Action |
|---|---|
| `↑` / `↓` | Move the highlight inside this kind's card |
| `space` | Install / skip the highlighted component |
| `a` / `n` | Select all / none of this kind |
| `A` / `N` | Select all / none of every kind |
| `enter` | Next kind's card; the last card continues to Arrange |
| `esc` | Back to the previous kind's card (Arrange's `esc` lands on the last card) |
| `?` | Help |
| `q` | Quit the installer, nothing installed |

#### Arrange keys (one pane per host)

Arrange has one pane per detected status-line host, Claude Code first, then the
Cursor CLI. Each pane's band names its host and carries the `o` on/off toggle.
The board shows segments as chips (`[>chip<]` = focused). Active segments sit
on numbered lines; inactive ones drop into an **OFF tray**. Moving a chip up
from Line 1 sends it to the tray; Space on a tray chip brings it back.

| Key | Action |
|---|---|
| `←` / `→` | Reorder the focused chip within its line |
| `↑` / `↓` | Move the chip across lines (↑ off Line 1 goes to the OFF tray) |
| `space` | Turn the focused segment on / off (off goes to the tray) |
| `tab` / `shift+tab` | Focus the next / previous chip |
| `o` | Host status line on / off; another tool's line: keep / remove / customize |
| `x` | Cursor only: extra-spend alert on / off (it fires at your Cursor spend limit, shown beside it) |
| `r` | Reset the layout to defaults |
| `enter` / `esc` | Continue to the next host or Review / back (the first host's `esc` returns to Choose's last card) |
| `?` | Help |
| `q` | Quit the installer |

The help line under each step's title lists every key that acts on that screen,
from the same table as the `?` panel, and the footer shows a subset of it. Both
host panes show the same keys: a key that exists on one host only, such as
Cursor's `x`, is named with that host (`x Cursor extra-spend alert
on/off`) and is listed whenever that host is detected. Below 30 terminal rows
the help is one wrapped line; from 30 rows it shows one group per line
(navigation, edit, status line, continue), and a resize switches between the two.

#### The host toggle `o`

- **ai-kit's own line, or no line yet.** `o` turns the host on or off. Off locks
  the board, and Review removes ai-kit's entry from a host that has one (an
  unset host stays unchanged). The pane says so: `Off: Review removes ai-kit's
  entry; …` or `Off: no status line is set for …`.
- **Another tool's status line (foreign).** The pane warns `⚠ … already has
  another status line: <command>`, starts in *keep*, and `o` cycles three states:
  - **keep current** (the start state): Review leaves the file as it is and
    writes nothing to that host.
  - **remove**: Review backs up the file, then removes the foreign entry. The
    host shows its own default status line.
  - **customize**: the board unlocks, starting from ai-kit's default layout.
    Review backs up the file, then writes ai-kit's status line.

  Remove and customize change the file only after a backup to
  `~/.local/state/ai-kit/backups/<host>/` and a default-No confirmation on
  Review. A JSONC `cli-config.json` is left untouched with a warning.

**Live preview.** Each pane's preview is a real render of the host's sample
payload, titled `preview — <host> (real renderer, sample data)`; Review's status-line box
shows the same render for each host you turn on. When the render is not
available, it falls back to sample text with a note. The sample values are not
your live session's model, context or cost.

#### Review and Done

**Review & confirm** lists the components to install per kind, the global
rules item (toggle it with `g`), and one outcome line per host, such as
`Claude Code: wire ai-kit`, `Cursor CLI: remove ai-kit's`, or
`Cursor CLI: keep its current status line; nothing written`. `enter` installs
and writes the config, `esc` goes back to Arrange. A host you left off and
unset is not written.

**✓ ai-kit is installed** shows one outcome line per host, for example
`Cursor CLI: status line removed`. After each status-line write the wizard
re-reads the host file; when the line is not what Review promised (still there
after a removal, not ai-kit's after a write), Done shows `install incomplete`
with that host's reason instead of success. `d` opens the config doctor (`esc`
returns to Done), and `enter` finishes and exits.

**Per-host status-line files.** Each host has its own config file:
`~/.config/ai-kit/claude-statusline.toml` and
`~/.config/ai-kit/cursor-statusline.toml`. One host's failure never blocks the
other host.

**What the wizard does not cover.** Adding/removing lines and editing
per-segment min-width gates must be done by hand-editing the TOML (see
[Status-line configuration](#status-line-configuration) below for colors,
ramps, and palette). The TOML file remains the authoritative source; the
wizard writes standard TOML that you can continue to edit by hand.

### Status-line configuration

The status line works with zero config. To customize it, edit
`~/.config/ai-kit/claude-statusline.toml` (the installer drops a fully-commented
starter there if you don't have one — as shipped it changes nothing). Settings
resolve **built-in defaults < this file < environment variables**.

**Toggle segments** — in the file:

```toml
[segments]
alt_cost          = true   # show the 🪙 cost segment (off by default)
alt_system_memory = false  # hide the 🧮 process-memory segment
render_time       = false  # ⏱ hide the render-time mark (on by default)
```

Segment keys follow a **domain-family / dispensability** scheme: a `git_` or
`system_` prefix names the domain, and an `alt_` prefix marks a *dispensable*
segment (dropped first when the line is tight). The pre-2026-06 bare names
(`cost`, `memory`, `branch`, `dirty`, `worktree`, `clock`, `time_ago`,
`total_time`, `api_time`, `dimensions`) **still load** — each is
forwarded to its new key with a one-time deprecation note, in both the TOML and
the `CC_AI_KIT_SEGMENT_<KEY>` env form.

**Diagnostic segments:**

- `render_time` (⏱, **on by default**) — how long `claude-status-line.py` itself took to run, from
  process start to render (the cost of its `git`/process/file probes), shown adaptively as
  `ns`/`µs`/`ms`/`s`. This is the *status line's own* wall-clock — distinct from `alt_time_session`
  (💬) and `alt_time_api` (📡), which report Claude's session and API durations from the input JSON.
  Its color is an SLO/SLA signal driven by the `[ramp.render_time]` ramp: green within the
  50 ms SLO, yellow up to the 150 ms SLA, red+bold beyond (all configurable). Set
  `render_time = false` (or `CC_AI_KIT_SEGMENT_RENDER_TIME=0`) to hide it.
- `alt_term_dimensions` (**off by default**) — the terminal size as `cols×rows` (`?` when the size
  had to be assumed). Enable via `[segments]` or `CC_AI_KIT_SEGMENT_ALT_TERM_DIMENSIONS=1`.

…or per-session via env (wins over the file):

```sh
CC_AI_KIT_SEGMENT_ALT_COST=1     # 1 true t y yes on  /  0 false f n no off
```

**Worktree segment** — `alt_git_worktree` (⎇, **on by default**) names the *active*
linked git worktree the session sits in, never a list: `⎇ <name>` (the worktree
directory basename, truncated to 20 columns). On the main checkout it shows a
dimmed, struck-through `⎇ wt` placeholder; outside any git repo it's hidden. The
`git_branch` segment shows only the branch — worktree state lives entirely in this
segment. Toggle it like any other segment (`[segments] alt_git_worktree = false`, or
`CC_AI_KIT_SEGMENT_ALT_GIT_WORKTREE=0`).

**Rate-limit segments** — split into `alt_h_rate_limit` (5-hour bucket) and `alt_w_rate_limit`
(7-day bucket), both **off by default**. Each renders `{Nh|Nd}: {pct}%` and degrades to that bare
form when space is tight; with room, the hourly segment adds a time-only reset stamp
(`5h: 42% (↺ 14:10)` — never a date, since a 5-hour window can't cross into a different day), and
the weekly segment adds a weekday + time stamp (`7d: 13% (↺ Sun 14:10)`). Color is an absolute
pace gap: |used% − elapsed%| in percentage points — ≤5 green, under 11 yellow, ≤15 orange, more
red. In the rich tier the percentage carries a pace sign: `+` when usage is at or behind the
window clock (under pace — `5h: +0%` early in a window), `-` when it burns faster than the clock
(`5h: -60%` with 60% used and only 45% of the clock gone). The dead `[ramp.rate]` band was
removed: nothing read it, and a leftover `[ramp.rate]` block now reports an unknown-ramp
warning. An unreliable window (missing/past `resets_at`, clock skew) paints the
percentage white with no pace sign. In the diagnostics row,
`alt_h_rate_limit` sits to the left of `alt_w_rate_limit`, so the weekly segment is always the
first of the two dropped under column pressure.

**`chat_size` vs `context`** — these answer different questions. `chat_size` (💾) reads the
transcript `.jsonl` on disk, which is **append-only and never shrinks** — even a `/compact` only
adds a boundary marker + summary to the file, it never removes anything. So `chat_size` shows
bytes accumulated **since the last compaction** (falling back to the full total when there hasn't
been one yet), plus the total and how many compactions have happened once there's been at least
one: `313KB/4.1MB (3x)` — narrower terminals drop to just the "since" figure. `context` (📊,
`seg_context`) is a *different* segment, unaffected by this: it reads Claude Code's own live
`context_window.used_percentage`, which already reflects the real, current context sent to the
model on the next turn. Use `chat_size` to gauge how much has piled up since your last compaction;
use `context` for what's actually in play right now.

**Shared git probe + cache TTL** — `git_branch`, `git_dirty`, and `alt_git_worktree`
read from one shared `git` probe (no duplicate querying). `git_dirty` is always read
fresh; the worktree `rev-parse` is cached (default **5 s**) because it rarely changes.
Tune the cache:

```toml
[git]
cache_ttl = 5   # seconds the worktree probe is cached
```

…or per-session: `CC_AI_KIT_GIT_CACHE_TTL=10` (wins over the file). A legacy
`[git] worktree` key (and the old `CC_AI_KIT_GIT_WORKTREE` env) is silently
ignored — worktree display is now the `alt_git_worktree` segment.

**Performance note** — disabling a segment skips its work, not just its
display. On a very large repository, turning off `git_dirty` also skips git's
untracked-file scan (the slow part of `git status`); turning off `alt_git_worktree`
skips the `rev-parse`; turning off `todo` skips the task-state read. The status
line reads task/todo state from Claude's on-disk state, not by re-parsing the
transcript, so it stays fast as sessions grow.

**Reorder / move rows** — uncomment **all** `[[line]]` blocks and edit (layout
is all-or-nothing; a partial layout would silently drop segments):

```toml
[[line]]
min_rows = 0
segments = ["path", "git_branch", "alt_git_worktree", "git_dirty", "todo"]
```

**Recolor segments** — colors are configured in the TOML file only (there is
**no `CC_AI_KIT_*` override** for palette or ramps, unlike the scalar settings
above). A color value is one of:

| Form | Example | Notes |
|---|---|---|
| palette **NAME** | `RED`, `BLUE` | one of the named colors in `[palette]` |
| raw **SGR** params | `38;5;208` | advanced; the part between `ESC[` and `m` |
| **hex** color | `#3399ff` | `#rgb` / `#rrggbb` / `#rrggbbaa` (alpha byte dropped) |

Any form may carry `+bold` / `+dim` / `+italic` / `+underline` modifiers, e.g.
`RED+bold`, `#3399ff+bold`. (Hex needs a truecolor terminal; `italic`/`underline`
rendering is terminal-dependent.)

`[palette]` **MERGES** over the defaults — override only the names you list (e.g.
pick a different blue):

```toml
[palette]
BLUE = "#3399ff"
```

`[ramp.*]` **REPLACES** the whole ramp — you must list every band you want. A
ramp maps a value to a color by ascending threshold (first band the value is
strictly below wins). Threshold keys are percent integers for `context` and
`rate`, `k`/`M`/`G` byte suffixes (1024-based, quoted) for `chat_size`,
`ns`/`µs`/`us`/`ms`/`s` time suffixes (quoted) for `render_time`, and `inf`
for the final catch-all band:

```toml
[ramp.context]
20 = "BLUE"
50 = "RED+bold"
inf = "MAGENTA_DARK+bold"
```

See `tools/claude-statusline.toml.sample` for the full default palette and ramps.

**Inspect & validate:** the render module `claude-status-line.py` is intentionally silent
— it never writes to stderr. All validation (bad config values, unknown keys,
bad env overrides) is surfaced by `tools/statusline-doctor.py`, which diagnoses
one status line at a time via `--host claude|cursor` (default `claude`):

```sh
python3 tools/statusline-doctor.py --print-config   # resolved config as JSON (incl. ramps)
python3 tools/statusline-doctor.py --check          # validate file + env overrides
python3 tools/statusline-doctor.py --doctor         # validate + dry-render every segment
python3 tools/statusline-doctor.py --help           # full env-var list for the selected host
python3 tools/statusline-doctor.py --host cursor --doctor  # diagnose the Cursor CLI line instead
```

Environment variables: `CC_AI_KIT_CONFIG_FILE` (config path),
`CC_AI_KIT_SEGMENT_<KEY>` (per-segment toggle); the Cursor host uses the
`AI_KIT_CURSOR_*` names instead (see `--host cursor --help`). The Cursor
doctor also reports the quota fetch status, always labeled
`inferred — undocumented Cursor API`, and may attempt one foreground quota
refresh — save-time validation and previews never fetch. Requires Python 3.11+
for the TOML file; on older Python the file is ignored and only env toggles apply.

### Cursor CLI status line

ai-kit renders a second, separate status line for the **Cursor CLI** (the
`cursor-agent` host) — its own entry, config and quota source, sharing only the
segment-layout and colour machinery with the Claude line. `tools/setup.py install`
and `install.sh` wire it next to the Claude one (`--with-statusline=cursor` picks
it alone; see [Headless install](#headless-install-ci--containers--no-tty)).

- **What it renders:** working path, git branch + dirty count, model, context
  remaining, and the quota group — included spend, API spend, on-demand/extra and
  the reset time. Layout and colours come from
  `~/.config/ai-kit/cursor-statusline.toml` (override the path with
  `AI_KIT_CURSOR_CONFIG_FILE`, toggle a segment with `AI_KIT_CURSOR_SEGMENT_<KEY>`);
  layout alternates (worktree path, render time, slowest segment, terminal size)
  are off by default. With no file the Cursor line renders ai-kit's defaults,
  and `tools/cursor-statusline.toml.sample` is the starter to copy by hand — or
  adopt the Cursor host in the wizard, which writes and doctor-validates that
  TOML for you. See that sample
  and `python3 tools/statusline-doctor.py --host cursor --help` for the full key
  and env list.
- **Quota is an inference, always marked as one.** Cursor documents no quota API
  for its CLI; the numbers come from ai-kit's own cache of the undocumented Cursor
  **Dashboard** usage endpoint, refreshed by a detached helper — the render path
  only reads that cache and never waits on the network. Every figure therefore
  prints with a leading `≈` and the doctor reports it as
  `inferred — undocumented Cursor API`. `≈*` means the cache is stale: the last
  refresh failed or never ran, so the number shown is the old one. The quota line
  reads, from the sample render (sample data, not a live Cursor run):
  `⚡️ inc: +42% (↺ Nov 23, 17d) ≈ | 🪙 extra: +$2.50/$20.00 ≈`.
- **Extra-spend alert:** `[cursor]` key `extra_alert` (default `true`, env
  `AI_KIT_CURSOR_EXTRA_ALERT`). The alert fires when extra spend reaches your Cursor spend
  limit, read from ai-kit's own Cursor quota cache (an inference from undocumented Cursor
  calls); there is no dollar override. With no limit in the cache there is no alert. An
  `extra_alert_usd` line left by an older ai-kit is ignored and removed on ai-kit's next
  write of the file. In the wizard's Cursor pane, `x` toggles the alert and the limit is
  shown beside it ("Cursor spend limit: $20.00 (from Cursor, …)", or unknown). The doctor's
  `extra-spend alert:` line names the limit source. `alt_process_memory` and `alt_time_ago`
  stay labelled unverified on Cursor until a live run confirms them.
- **Where its config file lives:** `cli-config.json` under the first Cursor
  directory that applies — a non-blank `CURSOR_CONFIG_DIR`, then
  `$XDG_CONFIG_HOME/cursor`, then `~/.cursor`; a blank or whitespace-only override
  falls through exactly like a missing one. Wiring writes the `statusLine` key and
  nothing else: unrelated keys and other top-level entries stay exactly as they
  are, and the fields Cursor owns (`padding`, `updateIntervalMs`, `timeoutMs`) are
  preserved when ai-kit's own entry is refreshed. An existing foreign `statusLine`
  is shown and confirmed away interactively (default No) and refused headless — it
  is never replaced silently, and a concurrent change to the entry between the read
  and the write aborts the write. **Known gap:** a `cli-config.json` that carries JSONC
  *comments* is left completely untouched (a warning names the file and the run
  exits 1) — ai-kit's writer emits plain JSON and would delete those comments, and
  Cursor itself writes plain JSON, so this stays unread rather than rewritten
  lossy. Detection does read through comments, so the reported state is still
  accurate.
- **Unwiring is per host:** `uninstall` removes ai-kit's entry from
  `~/.claude/settings.json` and from `cli-config.json` independently, matching the
  exact script argument rather than a substring, leaving the other host's file and
  both config TOMLs untouched.

### External drop-in segments

Add a status-line segment without editing `claude-status-line.py`: drop an executable
into `~/.config/ai-kit/segments/` (override with `CC_AI_KIT_EXTERNAL_DIR` or
`[external] dir`). It is discovered on the next render, **enabled by default**,
and placed via a header in its first 10 lines:

```
# ai-kit-segment: line=<N> (after=<key>|before=<key>|start|end) [id=<slug>] [timeout=<s>] [ttl=<s>]
```

Defaults: `line` = last row, position = `end`, `id` = filename stem,
`timeout` = 2s, `ttl` = `[external] ttl` (10s).

**Input.** The provider receives the same status JSON Claude passes, augmented
with a `segment` block, on **stdin** — and the key scalars mirrored as env vars
so a shell one-liner needs no JSON parser:

```json
{ "...": "normal status fields",
  "segment": { "id": "aws", "avail_cols": 24, "line": 2, "position": "after:alt_time_clock" } }
```

`AI_KIT_SEGMENT_COLS`, `AI_KIT_SEGMENT_ID`, `AI_KIT_SEGMENT_LINE`,
`AI_KIT_SEGMENT_POSITION`. The provider runs with `cwd` = the workspace directory.

**Output.** Print **one line**. SGR color escapes (`\033[…m`) are kept; any other
control sequence is stripped. Size it to `AI_KIT_SEGMENT_COLS` (long → medium →
short) — or print nothing to omit the segment. The core truncates as a safety net
and never lets an external push out a pinned segment. Output is cached per `id`
for `ttl` seconds (`ttl=0` re-runs every render).

**Worked example — AWS session expiry (`~/.config/ai-kit/segments/aws-session`):**

```bash
#!/bin/sh
# ai-kit-segment: line=2 after=alt_time_clock id=aws-session ttl=30
left=$(your-aws-expiry-command)            # e.g. "4h 44m 12s"
cols=${AI_KIT_SEGMENT_COLS:-80}
if   [ "$cols" -ge 14 ]; then printf '\033[33m🔐 %s\033[0m\n' "$left"
elif [ "$cols" -ge 8  ]; then printf '\033[33m🔐 4h44m\033[0m\n'
elif [ "$cols" -ge 4  ]; then printf '\033[33m🔐4h\033[0m\n'
fi                                          # else: nothing -> dropped
```

A cross-platform Python reference (system available memory) ships at
`examples/segments/system_memory` — copy it as a starting point.

**The installer offers to set these up for you.** On an interactive `install`,
the wizard discovers every provider under the repo's `examples/segments/`,
presents them **pre-checked** (default-ON), and copies the ones you keep into
your config segments dir (executable, atomic, idempotent — re-running never
duplicates). Scripted runs are governed entirely by a flag and never prompt:
`--examples=all|none|<ids>` (`<ids>` is a comma/space list of segment ids). The
default differs by entry point: `install.sh` / `make install` default to `all`,
while `python3 tools/setup.py install --headless` installs **no** example
segments unless you pass `--examples` explicitly — nothing is wired or copied
headlessly unless asked. See "Headless install (CI / containers / no TTY)" below
for the full non-interactive flag set (`--skills`, `--with-statusline`,
`--with-hooks`). Disable an installed provider later like any segment:
`[segments] system_memory = false`.

**Disable** a provider explicitly: `[segments] aws-session = false` (or
`CC_AI_KIT_SEGMENT_AWS_SESSION=0`).

**Trust model.** Providers are arbitrary executables. ai-kit only ever installs
the **bundled examples** shipped in this repo, and only on your explicit opt-in
(the pre-checked offer, or `--examples`); it never fetches or runs remote code.
Anything else is something you place in your own directory. Keep them fast and
single-line. A failing, slow (past `timeout`), or empty provider is simply omitted.

### Flags & overrides

```bash
install.sh --dry-run            # show what would change, mutate nothing
install.sh --uninstall          # remove ai-kit symlinks, statusLine and hook entries (keeps the install dir)
python3 tools/setup.py uninstall --hooks=tool-advisor,precompact  # remove only selected hook rows/links
install.sh --examples=all|none|<ids>   # which bundled example segments to install (default: all)
install.sh --branch <name>      # fetch a specific branch  (or --branch=<name>; fork via AI_KIT_REPO)
install.sh reconfigure          # re-open the wizard pre-loaded with your current selection + layout
```

`--uninstall` unwires each status-line host separately — it removes ai-kit's
`statusLine` from `~/.claude/settings.json` and from the Cursor `cli-config.json`
only when that entry is ai-kit's own (exact script argument, not a substring),
never a foreign one, and never touches the other host's file while doing it. Both
config TOMLs stay in place. It exits 1, naming the file, when a Claude Code or
Cursor settings file could not be read or rewritten, so ai-kit may still be wired
there; fix the file and re-run it.

**Try a branch without merging it.** `--branch <name>` (or `--branch=<name>`, or the
`AI_KIT_BRANCH` env var) is consumed by the bootstrapper (not passed to the wizard) and overrides
which branch is fetched. It applies only when install.sh fetches (piped from curl/wget); run from a
local checkout it is ignored with a note. On an **existing clone** at the install dir, an explicit
branch runs this sequence:

1. `git check-ref-format --branch B` rejects a malformed name.
2. It refuses when the tree is dirty, `git status` fails, or a `.git/index.lock` is left over from
   an interrupted run, naming `git -C <dir> status` to inspect it. It never auto-recovers.
3. It refuses when local `B` has commits that no `origin` branch has (checked before fetching,
   because a `--depth 1` fetch hides older history).
4. `--dry-run` prints the remaining steps and stops here.
5. `git ls-remote --exit-code --heads origin B` refuses a branch that is not on `origin`.
6. `git remote set-branches --add origin B`, skipped when that refspec is already configured.
7. `git fetch --depth 1 origin B`, then `git switch -C B --track origin/B`. If either fails, the
   refspec added in step 6 is removed again.

The default `main` never triggers a switch: with no explicit branch an existing clone runs
`git pull --ff-only origin <current branch>`, and refuses on a detached HEAD. Naming the branch
means a refspec left over from a branch deleted upstream cannot break the update.

`--dry-run` mutates nothing on any path: it prints the planned git commands (the sequence above,
the `pull`, or the clone/tarball command) and runs no fetch, pull, switch, set-branches, clone or
download, including over an earlier tarball (non-git) install. On an existing install it still
hands `--dry-run` to the wizard; on a not-yet-fetched bootstrap it stops before running setup.py.

A fork is selected with the `AI_KIT_REPO` env var (default `castocolina/ai-kit`) for a new clone or
tarball download. An existing clone fetches from its own `origin`, and install.sh prints a note
that `AI_KIT_REPO` is ignored.

One catch: the `install.sh` you pipe must itself be a *flag-aware* version — `--branch` only exists
in `install.sh` from a branch that has it (or from `main` once it's merged there). So to bootstrap a
not-yet-merged branch, fetch its `install.sh` **from that same branch**:

```bash
# install branch feat/x from the canonical repo (its own install.sh understands --branch):
curl -fsSL https://raw.githubusercontent.com/castocolina/ai-kit/feat/x/tools/install.sh \
  | bash -s -- --branch feat/x
# from a fork: pipe the fork's branch install.sh and point the clone at the fork via env:
#   curl -fsSL https://raw.githubusercontent.com/you/ai-kit/feat/x/tools/install.sh \
#     | AI_KIT_REPO=you/ai-kit bash -s -- --branch feat/x
# once --branch is on main, any branch works via the main install.sh:
#   curl -fsSL …/ai-kit/main/tools/install.sh | bash -s -- --branch feat/x
```

Simplest of all, no flag and no gotcha — clone the branch and run the local install (it skips the
fetch and uses the checked-out files directly):

```bash
git clone -b feat/x https://github.com/castocolina/ai-kit && cd ai-kit && make install
```

### Headless install (CI / containers / no TTY)

`python3 tools/setup.py install --headless` skips the interactive wizard
entirely — no TTY, no Textual. Bare `--headless` links and wires nothing; it only removes dead ai-kit links
(links into the kit whose target was removed upstream) in the claude and pi skills roots, one `warn:`
line each. Combine with the flags below to opt into specific pieces — nothing else is touched unless
explicitly requested:

- `--skills all` — link every skill (or `--skills name1,name2` for a subset).
  Additive only: never unlinks a skill already present from a prior run. A
  `jev-fast-decision`, `ai-kit-cross-ai`, `ai-kit-session-wake` and `ai-kit-commit-fold` links are mirrored into the
  pi agent skills dir (`${PI_CODING_AGENT_DIR:-~/.pi/agent}/skills`) when their claude link is made.
- `--replace-existing` — (requires `--headless --skills`) move a real directory
  or foreign symlink standing at one of the named skills' link paths into
  `${XDG_STATE_HOME:-~/.local/state}/ai-kit/backups/<claude|pi>/<name>.bak-<timestamp>/`
  (outside every scanned skills dir) and link the repo copy in its place.
  Without this flag such content is left alone with a warning and the run exits 1.
- `--with-statusline` — wire the ai-kit status line on **every detected host**,
  Claude first and then Cursor (`--with-statusline=claude,cursor` selects hosts
  explicitly). A host is "detected" by its config directory: `~/.claude` (or
  `CLAUDE_CONFIG_DIR`) and the Cursor config dir below. With neither directory
  present the run says there is nothing to wire and still exits 0; ai-kit never
  conjures a `~/.claude/` or a Cursor config dir on a machine that has no such
  host. `--with-statusline=<hosts>` fails before **any** write happens — no
  migration, no backup, no link, no hook, no example, no config file: an unknown
  name (`--with-statusline=bogus`) is a usage error (`2`), a valid name whose
  host isn't installed (`--with-statusline=cursor` with no Cursor dir) prints one
  message and exits `1`. A foreign `statusLine` is never replaced headless — that
  needs the interactive wizard's explicit yes — so such a run exits `1` and leaves
  the file untouched.
- `--with-hooks` — bare form wires every default-on hook knob, including the
  two per-call advisors; this is a behavior change from the briefing-only
  default. Defaults: `session-briefing`, `tool-advisor` and `tool-reminder` on;
  `decision-probe` off; `precompact` follows each host's recorded verdict.
  `--with-hooks=<id[:host],...>` (for example `--with-hooks=tool-advisor`) is
  additive: it only adds the named hooks and never removes existing ones. The six ids are documented here:

  | Id | What it does | Hosts | Default |
  |---|---|---|---|
  | `session-briefing` | Installed-tool briefing to user/model | Claude Code, Cursor | on |
  | `tool-advisor` | Advice for grep/cat/sed/find, large reads, and code searches (Bash, Grep, Glob) in a codegraph-indexed checkout | Claude Code, pi; Cursor gap; opencode gap pending S-OC | on |
  | `tool-reminder` | Output-size reminder with a better installed tool | Claude Code, pi; Cursor gap; opencode gap pending S-OC | on |
  | `decision-probe` | Reports usable decision backends | Claude Code | off |
  | `precompact` | Decision-system pre-summary before compaction | Claude Code, pi, experimental opencode | Per recorded host verdict |
  | `session-wake` | Passes a usage-limit reset to an armed session wake (experimental) | Claude Code | off |

  `python3 tools/setup.py uninstall --hooks=<ids>` removes only those hook
  ids (comma-separated, with optional `:host` selectors). Claude Code settings
  are wired per event; pi extensions and opencode plugins use symlinks. Absent
  hosts are skipped. The pre-summary fails open without blocking compaction.
- `--with-global-rules` — rewrites codegraph's "indexing is the user's decision"
  sentence inside its `<!-- CODEGRAPH_START -->` block in the four global
  instruction files (Claude `CLAUDE.md`, Codex `AGENTS.md`, Gemini `GEMINI.md`,
  opencode `AGENTS.md`). Only that sentence changes; each file is backed up first
  to `${XDG_STATE_HOME:-~/.local/state}/ai-kit/backups/global-rules/`. A bare
  `--headless` never touches these files, and `--dry-run` only previews the change.
  The config doctor row `codegraph-global-sentence` reports which wording each file holds.
- `--examples=all|none|<ids>` — the same pre-existing flag `install.sh` and
  the interactive wizard use for bundled example segments; it works
  identically here, with or without `--headless`.

Example: `python3 tools/setup.py install --headless --skills all --with-statusline --with-hooks --examples all`
(same thing host-by-host: `--with-statusline=claude,cursor`)

Exit codes: `0` success (including "nothing requested" and "that host isn't
installed here"), `1` something you asked for did not happen — a config file
ai-kit refuses to overwrite because it cannot parse it, a foreign `statusLine`
it will not replace without a human saying yes, a skill whose link path is
occupied by a real file or a non-ai-kit symlink, or a failed example-segment
copy. `2` is a usage error (bad flag combination, or the interactive path
finding no TTY). A `1` leaves every other requested step still attempted.

**This does not fetch or update the repo.** `--headless` is a flag to
`tools/setup.py`, which never syncs anything itself — syncing is
`tools/install.sh`'s job, and only in piped/bootstrap mode (`curl ... | bash`).
Running `install.sh` (or `make install`) from an existing local clone, or
invoking `tools/setup.py` directly as above, explicitly skips the fetch. For
a CI/container job that needs the latest kit, fetch or `git pull` the repo
yourself first, then run `tools/setup.py install --headless ...` against it —
or pipe the bootstrapper fresh each time if you want the fetch included:
`curl -fsSL .../install.sh | bash -s -- install --headless --skills all`.

**Wizard modes.** The interactive wizard requires a real terminal and a
sufficiently large window (see [The install wizard](#the-install-wizard) above).
If either is missing, `install.sh`/`make install` exits non-zero with a clear
message — there is no plain-menu fallback inside the wizard itself. For a
fully non-interactive run instead, use `python3 tools/setup.py install
--headless` (see "Headless install (CI / containers / no TTY)" above) — its
flags are the one non-interactive contract: `--examples=all|none|<ids>`
controls which example segments are copied (identically whether or not
`--headless` is also passed — it is a pre-existing top-level flag), and
`--skills`/`--with-statusline`/`--with-hooks` (headless-only) control
everything else the wizard would otherwise ask about interactively.

Environment overrides: `AI_KIT_DIR`, `AI_KIT_REPO`, `AI_KIT_BRANCH`, `CLAUDE_CONFIG_DIR`,
`CURSOR_CONFIG_DIR`.

## Updating

Re-run the install command (or `git -C ~/.local/share/ai-kit pull`). New entries
are linked, removed ones are pruned, and skills re-read on next invocation.

#### Upgrading from the single status-line script

The entry and sample were hard-renamed, with no compatibility shim. After fetching an update
and before setup runs, an existing status line may be blank. Re-run setup or the installer:
the migration rewrites only a recognized Python interpreter command whose exact script argument
is ai-kit's old entry; data arguments, backup suffixes, other scripts and shell commands remain
untouched. It moves the old TOML only when the new TOML is absent. If both TOMLs exist, neither is
changed; merge them by hand.

## Other tools

Skill discovery follows the [Agent Skills](https://agentskills.io/specification)
spec — every conformant tool reads the `name`/`description` frontmatter from each
`SKILL.md`. For non-Claude tools, clone this repo into the tool's skills directory:

```bash
git clone https://github.com/castocolina/ai-kit ~/.opencode/skills/ai-kit   # OpenCode
git clone https://github.com/castocolina/ai-kit ~/.gemini/skills/ai-kit     # Gemini CLI
```

`ai-kit-spec-review` is a skill (not a slash command), so it is portable: on any
Agent-Skills-conformant tool its orchestrator logic in
`skills/ai-kit-spec-review/SKILL.md` is discovered and can be followed directly.

Session-start hooks in [`tools/hooks/`](tools/hooks/README.md) inject a live
briefing of which curated modern CLI tools are actually on PATH. Claude Code
and Cursor are wired. The same directory documents the pre-summary hook, which
uses the local decision backend to classify context before compaction.

`tools/setup.py --config-doctor` opens a read-only Checks Catalog for Claude
Code, opencode, Codex, and Cursor — retention, sandboxing, telemetry, and
permission settings across whichever of those runtimes have a config file on
this machine. A handful of
rows can be applied one at a time, each behind an explicit confirm screen that
shows the literal resulting config for security-relevant settings; there is no
bulk-apply. The same doctor opens from the wizard's Done screen with `d`.

Every runtime-config apply (Claude `settings.json`, `opencode.jsonc`, Codex
`config.toml`) refuses a file it cannot parse, and backs the file up first to
`~/.local/state/ai-kit/backups/<runtime>/<file name>.<UTC timestamp>.bak` (the
newest 10 per file are kept). This is a different name from the skill backups'
`<name>.bak-<timestamp>/` described above. A missing target and a dry run take no backup.
The global-rules applier (`codegraph-global-sentence`) keeps its own backups
under `~/.local/state/ai-kit/backups/global-rules/`.

The row `claude-playwright-mcp-browser` is shown only when the Playwright plugin
is enabled. Its apply sets `env.PLAYWRIGHT_MCP_EXECUTABLE_PATH` to the flatpak
Chrome wrapper. That the variable reaches the MCP process and that the browser
launches headed are inferred, not verified, until the Phase 54 live check.

## Layout

```
ai-kit/
├── .claude-plugin/plugin.json   # Claude Code manifest (other tools ignore)
├── README.md
├── skills/                      # one directory per skill, each with SKILL.md
├── commands/                    # one Markdown file per slash command
├── tools/
│   ├── install.sh               # the installer above
│   ├── claude-status-line.py           # responsive Claude Code status line
│   └── hooks/                   # session-start substitution briefing
└── tests/                       # test_install.sh, test_status_line.py
```

## Development

The shipped tools stay **stdlib-only** — `tools/claude-status-line.py` runs under the
user's own `python3` with no dependencies. The lint/type toolchain below is
**dev-only** and never required at runtime.

```bash
make dev        # uv sync + install pre-commit hooks (sets up the dev env)
make setup-dev  # uv sync, the missing flow tools (pre-commit, gh, gh-stack, codegraph, graphify) and the hooks, each guarded; never upgrades, always exits 0 (dev and setup-env stay strict)
make test       # full suite in parallel, one subprocess per module, through tools/run_unittest_parallel.py (system python3 for the unit group)
make lint       # shellcheck + py-compile hooks (pre-commit, all files)
make validate   # the full quality gate (see below)
make check-dogfood    # live-project check: dogfood runner copy, curated-config guards, JDG-04 citations and judge records (also a pre-push hook)
make test-env-matrix  # six-environment proof, about six make test runs; not part of make test or validate
```

**The quality gate runs at commit and at push.** `.pre-commit-config.yaml` is the
single source of truth: `make validate` runs each of its hooks via the Makefile's
per-tool targets (ruff, pylint, pyright, vulture, shellcheck, py-compile,
unittest, unittest-wizard, check-dogfood). Ruff, py-compile, pyright and vulture
cover every shipped Python file under `tools/`, `skills/` and `tests/`; pylint
covers `tools/` and `skills/`. Tool versions are pinned in `uv.lock`; `make dev`
installs both hook stages so commits and pushes are gated even if you skip
`make validate`. Run it once after cloning:

```bash
make dev        # then commits and pushes are automatically gated
```

**Commits run only the tests that cover the staged files.** A covering e2e module
over the 60 s commit budget is named in the output and runs at push instead. The
full unit and arch suites run when shared test machinery is staged.

**Pushes run the full unit, arch and wizard suites, the live-project check and the
deferred e2e modules.** The deferred modules are only the pushed range's, for a
push of the checked-out branch from its own checkout with no other unpushed local
branch or worktree HEAD outside it; every over-budget one otherwise. The 60 s
target covers the two test hooks alone (their subtotal, measured with
`python3 tools/time_prepush.py`): before this phase they took 183.9 s (2026-11-03),
after it 55.4 s, and 30.7 s after the test-time cuts (2026-11-04). pyright (9.7 s),
vulture (1.9 s), check-dogfood (0.5 s) and deferred-e2e (0.0 s, no push range; no
e2e module is over the commit budget) are recorded beside that subtotal, and the
worst-case whole push (`push-worst`, every pre-push hook timed alone) is 42.7 s.
Tests never call a real host CLI or read `.planning/`.

**Skill judging.** `tools/judge_loop.py` builds skill-judge prompts that embed the installed judge's rubric and spec files (`prompt`, `prompt --probe`), picks the judge pool from probe lanes (`pool`), decides one or two judges per skill from recorded signals plus an advisory jev score (`count`), records each lane's verdict with its status line (`ingest`), and generates and checks the re-judge report in `.planning/judge/` (`report`, `check`; `--gate` also fails an unmet bar or a loop over three rounds, `--require-current` a stale digest). From a skill's second loop on, `count` takes its recorded signals from the skill's previous loop (its lowest valid percent and its worst verdict's critical and high counts) instead of `inputs.json`, and `report` and `check --gate` also fail the bar when a round's lowest percent is more than 7.0 points under the previous loop's lowest percent.

## Compatibility notes

- All `SKILL.md` files use the base [Agent Skills](https://agentskills.io/specification) frontmatter (`name`, `description`). No Claude-only fields, so the skills run unmodified on every conformant tool. A plain (unquoted) `description:` never holds `: ` or ` #`, which a strict YAML parser rejects (the host then shows no description); such a value is quoted or written as a `>-` block, and a test pins it.
- The `cst-refactor` skill ships its template as `codemod_template.py.txt`; `SKILL.md`
  copies it into the project as `tools/codemod_template.py` from the skill's own directory
  on any host (Claude Code: `${CLAUDE_PLUGIN_ROOT}/skills/cst-refactor`).

## License

MIT.
