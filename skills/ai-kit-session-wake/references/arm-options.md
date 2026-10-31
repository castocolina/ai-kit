# `arm` options

Load this when passing `--pid`, `--permission-mode` or `--only-if-armed`, or when `arm` refuses
with `pass --pid`. Do NOT load it for a plain `arm` (`--ref` included; SKILL.md covers it),
`status`, `done` or `disarm`.

- `--ref "<state file>"`, once per state file this run owns (for example a cross-AI
  resumable-state file), so the resumed session reads them.
- `--pid <host pid>`: on pi, opencode and codex (and on claude when `CLAUDE_PID` is unset) the
  shim finds the host process by an ancestor scan; when that finds nothing, `arm` refuses with
  `pass --pid`. Pass only the pid the host itself reports.
- `--permission-mode` is claude-only: it overrides the permission mode the claude resume replays
  (by default copied from the claude host command line: `bypassPermissions`, another explicit
  mode, `default`, or `unknown`; the resume adds no mode flag for `default` or `unknown`, and a
  claude resume always runs with `--permission-prompts none`). Do not pass it on pi, opencode or
  codex: `arm` prints `(not applied: no verified permission flag for <host>)` and the resume
  omits the flag.
- `--only-if-armed` refreshes an existing wake only; with none it prints `not armed; nothing
  refreshed` and exits 0.
