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
cost   = true     # show the 🪙 cost segment (off by default)
memory = false    # hide the 🧮 process-memory segment
```

…or per-session via env (wins over the file):

```sh
CC_AI_KIT_SEGMENT_COST=1     # 1 true t y yes on  /  0 false f n no off
```

**Reorder / move rows** — uncomment **all** `[[line]]` blocks and edit (layout
is all-or-nothing; a partial layout would silently drop segments):

```toml
[[line]]
min_rows = 0
segments = ["path", "branch", "dirty", "todo"]
```

**Fix a color** (e.g. a blue that reads purple) with raw ANSI SGR params:

```toml
[palette]
BLUE = "38;5;33"
```

**Inspect & validate:**

```sh
python3 tools/status-line.py --print-config   # resolved config as JSON
python3 tools/status-line.py --check          # validate the config file
python3 tools/status-line.py --help           # full env-var list
```

Environment variables: `CC_AI_KIT_CONFIG` (config path),
`CC_AI_KIT_SEGMENT_<KEY>` (per-segment toggle). Requires Python 3.11+ for the
TOML file; on older Python the file is ignored and only env toggles apply.

### Flags & overrides

```bash
install.sh --dry-run     # show what would change, mutate nothing
install.sh --uninstall   # remove every ai-kit symlink + statusLine (keeps the install dir)
```

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

## Compatibility notes

- All `SKILL.md` files use the base [Agent Skills](https://agentskills.io/specification) frontmatter (`name`, `description`). No Claude-only fields, so the skills run unmodified on every conformant tool.
- The `cst-refactor` skill resolves its bundled `codemod_template.py` via `${CLAUDE_PLUGIN_ROOT}`. On non-Claude tools, substitute the path to wherever this repo is cloned.

## License

MIT.
