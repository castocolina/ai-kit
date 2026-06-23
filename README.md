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
`status-line.py`. It is **idempotent** — re-run it any time to update.

## Contents

| Name | Type | Use case |
|---|---|---|
| [`reviewing-specs`](skills/reviewing-specs/SKILL.md) | skill | Audit-only reviewer for design/plan documents. Framework-aware (EARS, RFC-2119, Given/When/Then, OpenSpec, Spec Kit, GSD, …). |
| [`applying-review-feedback`](skills/applying-review-feedback/SKILL.md) | skill | Fixer that addresses each finding from a `reviewing-specs` report, in place. |
| [`commit-message`](skills/commit-message/SKILL.md) | skill | Generate a git commit message for staged/working changes, an amend, or a specific commit. |
| [`cst-refactor`](skills/cst-refactor/SKILL.md) | skill | LibCST-based Python codemod helper — multi-file renames and signature changes that survive comments and formatting. |
| [`mermaid-audit`](skills/mermaid-audit/SKILL.md) | skill | Render and review Mermaid diagrams embedded in Markdown — syntax, layout, **color palette, node shapes, and aspect ratio**; emits ready-to-paste `classDef` fixes and ships a consensus eval that checks the rules are reproducible across agents. |
| [`markdown-to-pdf`](skills/markdown-to-pdf/SKILL.md) | skill | Convert a Markdown document with embedded mermaid diagrams into a **PDF** (or a **marp** slide deck) — every ` ```mermaid ` block is auto-rendered with `mmdc` and embedded; auto-selects the best installed backend (Typst/Pandoc, LaTeX, WeasyPrint, Chromium) and never auto-installs. |
| [`review-spec`](skills/review-spec/SKILL.md) | skill | Orchestrates a clean-context review-and-fix loop: `reviewing-specs` to review, then routes the rewrite by framework (superpowers → `brainstorming`/`writing-plans`; GSD → `/gsd-plan-phase --reviews` + `gsd-plan-checker`; else `applying-review-feedback`). Loops until approved. |

## How the installer works

The repo is the source of truth. `tools/install.sh`:

1. **fetch** — clones (or `git pull`s) the repo into `~/.local/share/ai-kit`; falls back to a tarball download when `git` is absent.
2. **verify** — enumerates `skills/`, `commands/`, and `agents/` and validates each entry's shape (skills need a `SKILL.md`; commands/agents need Markdown with frontmatter). Malformed entries are skipped with a warning.
3. **link** — symlinks each valid entry into `~/.claude/<category>/`. Existing real files and symlinks that point outside ai-kit are never touched.
4. **prune** — removes broken symlinks under `~/.claude/` that point into the install dir, so deleting a skill from the repo and re-running cleans up after itself.
5. **statusline** — sets `statusLine` in `~/.claude/settings.json` to the bundled `tools/status-line.py` (a backup is written to `settings.json.bak`).

Adding or removing skills/commands/agents needs no change to the script — entries are discovered dynamically.

### Status-line configuration

The status line works with zero config. To customize it, edit
`~/.config/ai-kit/statusline.toml` (the installer drops a fully-commented
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
`total_time`, `api_time`, `dimensions`, `rate_limits`) **still load** — each is
forwarded to its new key with a one-time deprecation note, in both the TOML and
the `CC_AI_KIT_SEGMENT_<KEY>` env form.

**Diagnostic segments:**

- `render_time` (⏱, **on by default**) — how long `status-line.py` itself took to run, from
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

See `tools/statusline.toml.sample` for the full default palette and ramps.

**Inspect & validate:** the render module `status-line.py` is intentionally silent
— it never writes to stderr. All validation (bad config values, unknown keys,
bad env overrides) is surfaced by `tools/statusline-doctor.py`:

```sh
python3 tools/statusline-doctor.py --print-config   # resolved config as JSON (incl. ramps)
python3 tools/statusline-doctor.py --check          # validate file + env overrides
python3 tools/statusline-doctor.py --doctor         # validate + dry-render every segment
python3 tools/statusline-doctor.py --help           # full env-var list
```

Environment variables: `CC_AI_KIT_CONFIG_FILE` (config path),
`CC_AI_KIT_SEGMENT_<KEY>` (per-segment toggle). Requires Python 3.11+ for the
TOML file; on older Python the file is ignored and only env toggles apply.

### External drop-in segments

Add a status-line segment without editing `status-line.py`: drop an executable
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
`examples/segments/sysmem` — copy it as a starting point.

**The installer offers to set these up for you.** On an interactive `install`,
the wizard discovers every provider under the repo's `examples/segments/`,
presents them **pre-checked** (default-ON), and copies the ones you keep into
your config segments dir (executable, atomic, idempotent — re-running never
duplicates). Headless / scripted runs are governed entirely by a flag and never
prompt: `--examples=all|none|<ids>` (default `all`; `<ids>` is a comma/space list
of segment ids). Disable an installed provider later like any segment:
`[segments] sysmem = false`.

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
install.sh --uninstall          # remove every ai-kit symlink + statusLine (keeps the install dir)
install.sh --examples=all|none|<ids>   # which bundled example segments to install (default: all)
install.sh --branch <name>      # fetch a specific branch  (or --branch=<name>; fork via AI_KIT_REPO)
AIKIT_PLAIN=1 install.sh        # force the plain numbered wizard (skip the arrow-key chip UI)
```

**Try a branch without merging it.** `--branch <name>` is consumed by the bootstrapper (not passed
to the wizard) and overrides which branch is fetched. A fork is selected with the `AI_KIT_REPO` env
var; the default is `castocolina/ai-kit`.

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

**Wizard modes.** The interactive installer auto-selects its UI: on a capable
terminal it shows an **arrow-key chip selector** (↑↓/space/enter), and falls back
to a **plain numbered menu** anywhere else (non-tty, `TERM=dumb`, a small window).
Force the plain menu with `AIKIT_PLAIN=1`. With no terminal at all (CI, piped
input) the wizard never prompts — selections come from flags and defaults, so an
unattended `install` always completes.

Environment overrides: `AI_KIT_DIR`, `AI_KIT_REPO`, `AI_KIT_BRANCH`, `CLAUDE_CONFIG_DIR`.

## Updating

Re-run the install command (or `git -C ~/.local/share/ai-kit pull`). New entries
are linked, removed ones are pruned, and skills re-read on next invocation.

## Other tools

Skill discovery follows the [Agent Skills](https://agentskills.io/specification)
spec — every conformant tool reads the `name`/`description` frontmatter from each
`SKILL.md`. For non-Claude tools, clone this repo into the tool's skills directory:

```bash
git clone https://github.com/castocolina/ai-kit ~/.opencode/skills/ai-kit   # OpenCode
git clone https://github.com/castocolina/ai-kit ~/.gemini/skills/ai-kit     # Gemini CLI
```

`review-spec` is a skill (not a slash command), so it is portable: on any
Agent-Skills-conformant tool its orchestrator logic in
`skills/review-spec/SKILL.md` is discovered and can be followed directly.

## Layout

```
ai-kit/
├── .claude-plugin/plugin.json   # Claude Code manifest (other tools ignore)
├── README.md
├── skills/                      # one directory per skill, each with SKILL.md
├── commands/                    # one Markdown file per slash command
├── tools/
│   ├── install.sh               # the installer above
│   └── status-line.py           # responsive Claude Code status line
└── tests/                       # test_install.sh, test_status_line.py
```

## Development

The shipped tools stay **stdlib-only** — `tools/status-line.py` runs under the
user's own `python3` with no dependencies. The lint/type toolchain below is
**dev-only** and never required at runtime.

```bash
make dev        # uv sync + install pre-commit hooks (sets up the dev env)
make test       # full test suite on system python3 (real runtime fidelity)
make lint       # shellcheck + py_compile (quick static checks)
make validate   # the full quality gate (see below)
```

**The quality gate is pre-commit.** `.pre-commit-config.yaml` is the single
source of truth: `make validate` runs `uv run pre-commit run --all-files`, the
*same* hooks (ruff, pylint, pyright, vulture, shellcheck, py-compile, unittest)
that gate every commit — so the gate and your local checks can never drift. Tool
versions are pinned in `uv.lock`; `make dev` installs the hooks so commits are
gated even if you skip `make validate`. Run it once after cloning:

```bash
make dev        # then commits are automatically gated
```

## Compatibility notes

- All `SKILL.md` files use the base [Agent Skills](https://agentskills.io/specification) frontmatter (`name`, `description`). No Claude-only fields, so the skills run unmodified on every conformant tool.
- The `cst-refactor` skill resolves its bundled `codemod_template.py` via `${CLAUDE_PLUGIN_ROOT}`. On non-Claude tools, substitute the path to wherever this repo is cloned.

## License

MIT.
