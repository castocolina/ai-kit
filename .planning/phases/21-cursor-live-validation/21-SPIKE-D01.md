# Phase 21 — D-01 spike: does the cursor CLI load user-level subagents?

**Date:** 2026-10-18 · **cursor-agent:** 2026.10.14-941492e · **Run by:** orchestrator (headless)

## Setup

- Scratch HOME with `CURSOR_CONFIG_DIR=<scratch>/home/.cursor` and `XDG_CONFIG_HOME=<scratch>/home/.config`; env built with `env -i` (PATH, HOME, the two config vars, TERM only).
- The login is a symlink `<scratch>/home/.config/cursor/auth.json -> <home>/.config/cursor/auth.json`; its contents were never read. Nothing was written under the real `~/.cursor`.
- `composer-worker.md` (`model: composer-2.5`, unquoted single-line scalars, non-empty body) lives in a scratch source dir and is linked per file.
- Parent: `cursor-agent -p --trust --model composer-2.5 --output-format stream-json --workspace <scratch>/ws "<delegate to composer-worker; reply PONG>"`.

## Results

1. **User level** (`<scratch>/home/.cursor/agents/composer-worker.md`, symlink): not loaded. The Task call
   was rejected: `subagent_type: Invalid option: expected one of "generalPurpose"|"explore"|"cursor-guide"|"ci-investigator"|"bugbot"|"security-review"|"best-of-n-runner"`. The parent answered NO-SUCH-AGENT.
2. **Project level** (`<scratch>/ws/.cursor/agents/composer-worker.md`, a symlink to a file outside the
   workspace): loaded. The Task call carried `"subagentType": {"custom": {"name": "composer-worker"}}, "model": "composer-2.5"`, and the subagent returned `PONG`.
3. **Static check** of the 2026.10.14 bundle (`index.js`, `computeAgentsDirs()`): the dirs are
   `join(resolve(workspacePath), ".cursor", "agents")`, plus `.claude/agents` and `.grok/agents` under
   the same workspace root when third-party extensibility is on. No home-directory root, same as
   2026.10.01.
4. `cursor-agent models` under the scratch HOME exited 0 (269 lines, 79 `-fast` ids; `composer-2.5`
   and `grok-4.7-medium` present, each with a `-fast` twin). The CLI wrote its own
   `<scratch>/home/.cursor/cli-config.json`.
5. Process proof: the `models` call left a detached `index.js worker-server` (parent PID 1, HOME =
   the scratch home). It was killed by PID after checking its environment; no cursor process with
   the scratch HOME remains.

## Consequence (D-01, locked)

The CLI ignores `~/.cursor/agents`. Per D-01 the AGT-01 target becomes project-level
`.cursor/agents` through a decimal phase, with SPEC R6/R7, ROADMAP SC4 and AGT-01 amended formally.
The Background claim "Cursor also reads `~/.claude/agents`" does not hold for the CLI either: it reads
`<workspace>/.claude/agents`.
