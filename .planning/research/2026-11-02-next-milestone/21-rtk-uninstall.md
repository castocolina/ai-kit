# Removing rtk from this machine

Research date: 2026-11-02. Nothing was uninstalled or changed. The script
`21-rtk-uninstall.sh` sits next to this file and has not been run on the real home directory.
I tested it only in a throwaway fake home directory.

## Which rtk this is

- Project: rtk-ai/rtk ("Rust Token Killer"), Apache-2.0, homepage https://www.rtk-ai.app/.
  `rtk --help` matches it (`init`, `gain`, `hook`, `rewrite`, `telemetry`). It is not the
  unrelated "Rust Type Kit" crate on crates.io.
- This machine has **two copies**:
  - `~/.local/bin/rtk`, version 0.44.1, dated Jul 28. This is the bare binary that the upstream
    `install.sh` places in `${RTK_INSTALL_DIR:-~/.local/bin}`. No package manager owns it. It
    comes first on PATH, and PATH lists `~/.local/bin` twice, so `type -a` shows it twice.
  - The Homebrew formula `rtk` 0.49.0, installed Sep 15 16:58 (`brew info rtk` says
    "Installed (on request)"). Homebrew reports that the `~/.local/bin` copy hides it. The
    install time matches the time `~/.codex/RTK.md` was written, which points to the
    tools-installer brew fallback plus its rtk registration hook.
- No cargo copy exists (no `~/.cargo/bin/rtk`).

## How the project says to uninstall

From the official installation page (rtk-ai.app/docs/getting-started/installation) and the
repo's INSTALL.md:

- `rtk init -g --uninstall` removes the Claude Code wiring: the `rtk hook claude` entry in
  `settings.json`, the legacy `~/.claude/hooks/rtk-rewrite.sh`, `~/.claude/RTK.md` and the
  `@RTK.md` line in `~/.claude/CLAUDE.md`. After that, restart Claude Code.
- Each host is uninstalled separately with the same flag: `--codex`, `--opencode`, `--gemini`,
  `--copilot` and `--agent cursor|windsurf|cline|kilocode|antigravity|kimi|pi|hermes|droid`,
  each with `--uninstall` (`rtk init --help`). There is no single command that removes
  everything. ai-kit's old `tools/context_tools_scripts/rtk.sh` (commit 7e2a088, later deleted)
  ran the whole list for the same reason. It also noted rtk issue #1014: `--uninstall` can
  leave data-dir artifacts behind.
- To remove the binary, use the command for how it was installed: `brew uninstall rtk`,
  `cargo uninstall rtk`, or just delete the file for an `install.sh` install. The upstream
  `install.sh` writes only the binary. It does not touch shell rc files, PATH or config.
- Telemetry: `rtk telemetry forget` turns telemetry off and deletes the device salt, the ping
  marker and the local tracking database. It then sends an erasure request to rtk-ai's server.
  If the server is unreachable, you erase by email (contact@rtk-ai.app plus the device hash).
  Source: docs/TELEMETRY.md in the repo. That doc calls the database both `tracking.db` and
  `history.db`. This machine has `history.db`.

## Where rtk writes (from the docs and the `init --help` list)

- Its own directories: `~/.config/rtk/` (config.toml, filters.toml, pipeline.toml),
  `~/.local/share/rtk/` (history.db, tee/, .device_salt, ping and warning markers). In project
  folders it may also write `./.rtk/filters.toml` and a block in `./CLAUDE.md`.
- Claude Code: `~/.claude/settings.json` hook (`rtk hook claude`), `~/.claude/RTK.md`, the
  `@RTK.md` line in `~/.claude/CLAUDE.md`, a `settings.json.bak`, and the legacy
  `~/.claude/hooks/rtk-rewrite.sh`.
- Codex: `~/.codex/RTK.md` plus an `@…/RTK.md` line in `~/.codex/AGENTS.md`.
- opencode: a TypeScript plugin `~/.config/opencode/plugins/rtk.ts`.
- Cursor: `~/.cursor/hooks.json`. Gemini: a BeforeTool hook in `~/.gemini/settings.json`.
  Copilot: a PreToolUse hook. pi: a TypeScript extension. Antigravity:
  `~/.gemini/config/plugins/rtk/`. Hermes: `~/.hermes/plugins/rtk-rewrite/`. Droid:
  `~/.factory/hooks.json`.
- Shell rc files and completions: the docs mention none.

## What is on this machine now (read-only scan)

Traces found:

- `~/.local/bin/rtk` (0.44.1, a bare binary).
- `/home/linuxbrew/.linuxbrew/bin/rtk` → `Cellar/rtk/0.49.0` (Homebrew).
- `~/.config/rtk/config.toml`, `~/.config/rtk/filters.toml`.
- `~/.local/share/rtk/`: `history.db` (about 69 MB), `tee/` (20 logs), `.device_salt`,
  `.telemetry_last_ping`, `.hook_warn_last`. The two markers were touched today at 11:16, so
  something still calls rtk.
- Telemetry is **on**: `rtk telemetry status` shows consent yes since 2026-07-25.
- Codex:
  - `~/.codex/RTK.md` exists. It tells the agent to put `rtk` in front of every shell command.
  - `~/.codex/AGENTS.md` line 1: `@/home/bazzite/.codex/RTK.md`
  - `~/.codex/rules/default.rules` lines 5-6: `prefix_rule(pattern=["rtk", "uv", "run", "pytest"], decision="allow")`
    and the same rule for `pyright`.
- The ai-kit project's `.claude/settings.local.json` (gitignored) lines 5-6, permission allow
  entries `"Bash(rtk git *)"` and `"Bash(rtk grep *)"`.
- Homebrew download cache: `~/.cache/Homebrew/downloads/*rtk-0.49.0*`,
  `~/.cache/Homebrew/rtk--0.49.0`, `~/.cache/Homebrew/rtk_bottle_manifest--0.49.0`, and the
  formula API cache `~/.cache/Homebrew/api/formula/rtk.json`. The script leaves that last one
  alone because brew manages it.

Checked and clean, with no rtk entries:

- Claude Code: `~/.claude/settings.json` (hooks are ai-kit, herdr and codegraph only),
  `~/.claude/CLAUDE.md`. There is no `~/.claude/settings.local.json`, `~/.claude/RTK.md` or
  `~/.claude/hooks/rtk-rewrite.sh`. `rtk init --show` agrees for both versions:
  "Hook: not found", "OpenCode: plugin not found", "Cursor hook: not found".
- opencode: `~/.config/opencode/opencode.jsonc`. The only file in
  `~/.config/opencode/plugins/` is `herdr-agent-state.js`.
- Other hosts: `~/.cursor/hooks.json`, `~/.codex/config.toml`, `~/.codex/hooks.json`,
  `~/.pi/agent/settings.json`, and `~/.pi/agent/extensions/` (ai-kit symlinks plus `subagent`).
- More hosts: `~/.copilot/config.json`, `~/.gemini/settings.json`, `~/.gemini/GEMINI.md`, and
  `/var/home/bazzite/.agents/AGENTS-TOOLING.md`.
- Shell setup: `~/.bashrc`, `~/.bash_profile`, `~/.profile`, `~/.zshrc`, `~/.zprofile`, fish
  config and conf.d have no rtk lines. No completion files exist.

Other mentions, not rtk files:

- `~/.cache/pylint/ai_kit_usage_metrics.capture_rtk_1.stats` is a pylint cache from ai-kit.
- The memory note `feedback_no_rtk.md` records that rtk was dropped.

## The script (`21-rtk-uninstall.sh`)

What it does, in order (`set -euo pipefail`, safe to run more than once):

1. It finds a working rtk binary: the brew copy first because it is newer, then
   `~/.local/bin`, then cargo.
2. It backs up rtk's directories and every host file it might touch to
   `~/.local/state/rtk-uninstall-backup/<time>-<pid>/`. The backup includes history.db.
3. It runs rtk's own `rtk init -g <host> --uninstall` **only for hosts with a trace**, from an
   empty temporary directory with input closed. On this machine that means `--codex` only, so
   rtk never rewrites `~/.claude/settings.json` for nothing.
4. It runs `rtk telemetry forget`, which asks the server to erase your data. Skip it with
   `RTK_SKIP_TELEMETRY_FORGET=1`.
5. A Python sweep removes whatever is left, only the rtk parts:
   - It reads the JSON files, removes hook objects whose command calls rtk and any `Bash(rtk …)`
     allow entries, and writes the result through a temporary file plus `os.replace()`. It
     writes a file only if something changed.
   - It also removes the Codex `@…RTK.md` line and the `prefix_rule(pattern=["rtk", …])` lines.
   - Leftover `RTK.md`/`rtk.ts` files are deleted.
6. It runs `brew uninstall --formula rtk`. If a cargo copy existed it would run
   `cargo uninstall rtk`. It backs up and deletes `~/.local/bin/rtk`, but only after
   `--version` confirms the file really is rtk.
7. It deletes `~/.config/rtk`, `~/.local/share/rtk`, `~/.cache/rtk` and `~/.local/state/rtk`,
   plus the Homebrew bottle cache files.
8. It **prints** any shell rc lines that mention rtk for you to remove by hand. Today there are
   none.
9. It runs `hash -r` and checks that `command -v rtk` prints nothing. If not, it exits 1.

`RTK_DRY_RUN=1` prints every step without changing anything. Run that first.

Checks done: `bash -n` and shellcheck are clean. In a fake home directory with a stand-in rtk
binary, the dry run changed nothing. The real run removed only the rtk hook objects and
permissions and kept the ai-kit and other hooks plus unrelated keys. A second run reported
everything clean and exited 0.

What it does on this machine:

- It edits these files: `~/.codex/AGENTS.md` (drops one line), `~/.codex/rules/default.rules`
  (drops two lines) and the ai-kit `.claude/settings.local.json` (drops two permissions).
- `json.dumps(indent=2)` rewrites the whole settings.local.json file. Its content stays the
  same, but any non-standard spacing would change.

## Follow-ups for the next milestone (not edited)

ai-kit. The hooks themselves are clean:

- The tool advisor, reminder and session-start hooks contain no rtk.
  `tests/test_tool_substitution_hook.py::test_no_hook_file_mentions_the_rewrite_tool` already
  fails the build if any file under `tools/hooks/` mentions rtk.
- The wired hooks (Claude settings, Cursor `sessionStart`, pi extension symlinks) do not depend
  on rtk.

What still mentions rtk:

- **Docs:**
  - `AGENTS.md` line 118 ("Tools and Stack") lists `rtk` as shell tooling.
  - `.claude/cli-environment.md` (gitignored, local only) has a whole "rtk" section.
  - `README.md` lines 51, 646 and 653 mention it (usage-metrics sources, the "rtk substitutions"
    briefing wording, and the doctor's rtk Cursor check).
  - `.planning/PROJECT.md` line 75 and `MILESTONES.md` line 95 are history and can stay.
- **Config doctor:**
  - `tools/config_doctor_checks.py` has the check `rtk-cursor-integration`, whose recommended
    action is `rtk init -g --agent cursor`. It will tell the owner to reinstall rtk.
  - `tools/config_doctor_readers.py` parses `rtk init --show` output.
  - Tests: `tests/test_config_doctor.py`, `tests/test_config_doctor_pty.py`.
- **Agents-file rules checker:**
  - `skills/ai-kit-project-rules-agents/ai_kit_project_rules_agents/rules.py` lines 109-114
    holds a house rule: "when rtk is present, tell agents to prefix `rtk`".
  - `skills/_shared/ai_kit_rules_common/tool_presence.py` line 33 detects rtk.
  - Also affected: the skill's SKILL.md lines 66-67, `tests/test_ai_kit_project_rules_agents.py`
    and `tests/test_ai_kit_rules_common.py`.
  - Once rtk is gone the rule never fires. Decide whether to delete it so it cannot come back.
- **Usage-metrics skill:**
  - `skills/ai-kit-usage-metrics/` (capture_rtk.py, paths.py, cli.py, refiner.py, dashboard.py,
    SKILL.md) and `tests/test_ai_kit_usage_metrics.py` read `~/.local/share/rtk/history.db` and
    `tee/`.
  - After removal that source is empty. Rows already captured into ai-kit's own store should
    remain, but I have not verified this.
  - Decide whether to keep the rtk source as optional, or remove it. The backup of history.db
    can be imported once if wanted.
- Pending todo `.planning/todos/pending/2026-10-18-visible-tool-advisory-hooks-pre-and-post-tool-use.md`
  already says "drop the rtk parse". `NEXT-MILESTONE-INPUTS.md` lines 747-775 already record
  that rtk is dropped and that `cli-environment.md` is stale.

tools-installer (`/var/home/bazzite/git/personal/tools-installer`). **It would reinstall rtk:**

- `installer/registry.toml` has a `[[tool]] id = "rtk"` entry, P1, ai tier, with three
  `github_release` methods plus a `brew` fallback.
- `recommends = ["codegraph", "graphify", "rtk"]` appears on the claude, opencode, codex and
  cursor-agent entries (lines 1436, 1476, 1501, 1556), so installing any of those hosts offers
  rtk again.
- `postinstall = "rtk-register"`: `installer/postinstall.py` `_rtk_register` / `_RTK_HOST_ARGS`
  runs `rtk init -g --auto-patch` for claude, `--opencode`, `--codex` and `--agent cursor`, which
  re-wires every host. It is also listed in `installer/model.py` `POSTINSTALL_HOOK_NAMES`.
- `.planning/ROADMAP.md` line 344 and `REQUIREMENTS.md` (CONF-01) plan rtk
  register/unregister work.
- Local state: no receipt for rtk under `~/.local/state/tools-installer/receipts/`. Only
  `versions.json` caches rtk (brew inventory 0.49.0, latest v0.51.0). After uninstalling, a
  "missing P1 tool" view may offer rtk again.
- Follow-up: remove rtk from the catalog or mark it as not wanted, drop it from the hosts'
  `recommends`, and drop `rtk-register`. Per the ai-kit/tools-installer scope split, that work
  belongs in tools-installer.

## Not checked

- I did not run `rtk init --uninstall --dry-run`, so I have not seen what rtk itself would write.
- Whether `rtk telemetry forget` prompts or succeeds without input is unverified (input is
  closed, and a failure only prints a warning).
- I did not find what touched `~/.local/share/rtk` at 11:16 today.
- Server-side erasure cannot be checked from here.

Sources:
- https://github.com/rtk-ai/rtk
- https://raw.githubusercontent.com/rtk-ai/rtk/develop/INSTALL.md
- https://www.rtk-ai.app/docs/getting-started/installation/
- https://raw.githubusercontent.com/rtk-ai/rtk/master/install.sh
- https://raw.githubusercontent.com/rtk-ai/rtk/develop/docs/TELEMETRY.md
