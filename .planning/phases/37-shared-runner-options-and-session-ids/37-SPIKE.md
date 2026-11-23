# Phase 37 spike record (D-17)

help-refresh: recorded 2026-11-21
real-home probes: not run (no ledger consent line)

## Host versions

| host | version | `--version` text | date |
|------|---------|------------------|------|
| claude | 2.1.330 | 2.1.330 (Claude Code) | 2026-11-21 |
| codex | 0.170.0 | codex-cli 0.170.0 | 2026-11-21 |
| copilot | 1.0.112 | GitHub Copilot CLI 1.0.112. | 2026-11-21 |
| cursor | 2026.11.13 | 2026.11.13-eacade1 | 2026-11-21 |
| opencode | 2.3.2 | opencode v2.3.2 | 2026-11-21 |
| pi | 1.5.2 | 1.5.2 | 2026-11-21 |

All help and version captures ran with no model call, in the scrubbed scratch environment of `tools/record_cli_help.py` `child_env` (scratch HOME and XDG dirs, `OPENCODE_*` removed, scratch HOME as cwd) with the host signal variables and every `CLAUDE_`, `CODEX_`, `COPILOT_`, `CURSOR_` and `PI_` variable removed. All sixteen captures exited 0 and are non-empty UTF-8.

## Questions

### Q1 pi session resume

- command shape: not probed (no ledger consent line)
- host version and date: not probed (no ledger consent line)
- observed: not probed (no ledger consent line)
- verdict: not probed (no ledger consent line)

### Q2 opencode session resume and id shapes

- command shape: not probed (no ledger consent line)
- host version and date: not probed (no ledger consent line)
- observed: not probed (no ledger consent line)
- verdict: not probed (no ledger consent line)

### Q3 claude resume, permission flag and error channel

- command shape: not probed (no ledger consent line)
- host version and date: not probed (no ledger consent line)
- observed: not probed (no ledger consent line)
- verdict: not probed (no ledger consent line)

### Q4 claude `/<name>` skill form

- command shape: not probed (no ledger consent line)
- host version and date: not probed (no ledger consent line)
- observed: not probed (no ledger consent line)
- verdict: not probed (no ledger consent line)

### Q5 copilot `--add-dir` skill form

- command shape: not probed (no ledger consent line)
- host version and date: not probed (no ledger consent line)
- observed: not probed (no ledger consent line)
- verdict: not probed (no ledger consent line)

### Q6 codex `model_context_window` key

- command shape: `codex -c model_context_window=<value> debug models` with an empty scratch CODEX_HOME, once with `abc` and once with `128000`, no model call
- host version and date: codex 0.170.0, 2026-11-21
- observed: `abc` exits 1 with `invalid type: string "abc", expected i64 in model_context_window`; `128000` exits 0 and lists the model catalog JSON
- verdict: verified (the key is parsed as an integer, a wrong type names the key)

### Q7 help refresh of the six hosts

- command shape: `<host> --version`, `<host> --help`, plus `codex exec --help`, `codex exec resume --help`, `opencode run --help`, `copilot skill --help`
- host version and date: see Host versions, 2026-11-21
- observed: all sixteen captures exit 0 and are non-empty; no host is incomplete
- verdict: recorded for claude, codex, copilot, cursor, opencode and pi

### Q8 cursor model listing

- command shape: not probed (no ledger consent line)
- host version and date: not probed (no ledger consent line)
- observed: not probed (no ledger consent line)
- verdict: not probed (no ledger consent line)

### Q9 herdr hosting round trip

- command shape: `herdr tab create --label <label> --no-focus --cwd <dir>`, `herdr pane run <pane> "sh <launch.sh>"` (the script writes its pid, runs `sh -c 'echo out-line; echo err-line >&2; exit 7'` with stdout and stderr to files, then renames `rc.tmp` to `rc`), `herdr tab close <tab id>`; no model call
- host version and date: herdr 0.9.5, 2026-11-21
- observed: tab and root pane ids read from the create JSON; the script finished within 1 s with rc 7; out held `out-line`, err held `err-line`; the tab closed with `ok` (close rc 0)
- verdict: verified (a herdr-hosted command keeps its exit code and both streams through files; the tab is closed by its recorded id)

### opencode id-shape matrix

not probed (no ledger consent line); style stays `minted`, idShape `none`.

### claude execute output channel (0b-11)

not probed (no ledger consent line); the output channel stays `not observed`, and a usage-limit body was not observed either.

## Label flips

- pi.forms.session.label -> unverified, not probed (no ledger consent line)
- opencode.forms.session.label -> unverified, not probed (no ledger consent line)
- opencode.forms.session.style -> minted, not probed (no ledger consent line)
- opencode.forms.session.idShape -> none, not probed (no ledger consent line)
- claude.forms.session.label -> unverified, not probed (no ledger consent line)
- claude.exec.permission -> --permission-mode bypassPermissions, not probed (no ledger consent line; 0c default)
- claude.exec.probe_record -> null, not probed (no ledger consent line)
- claude.exec.output_channel -> not observed, not probed (no ledger consent line)
- claude.forms.skills.name.state -> unverified, not probed (no ledger consent line)
- copilot.forms.skills.path.state -> unverified, not probed (no ledger consent line)
- codex.forms.context.key -> verified, codex 0.170.0 config parse 2026-11-21: invalid type: string "abc", expected i64

## Open (not probed by design)

- whether an unattended cursor execute lane blocks without `--approve-mcps` (Phase 39)
- whether claude plan mode and copilot's review profile still run the given MCP servers' tools (Phase 39)
- which server wins on a copilot name collision (Phase 39)

## Real config audit

Detection after the fact, not proof of no change: under consent the hosts ran with full permissions.

No consent line was present, so no host ran against the real HOME; the audit window (marker written before the first host call) still covers the whole orchestrating session. Output of the read-only audit over the host config directories (including `~/.copilot`):

```
noise .claude/backups: 2 files newer than marker
noise .claude/projects: 6 files newer than marker
noise .claude/sessions: 1 files newer than marker
noise .claude/shell-snapshots: 1 files newer than marker
CHANGED ~/.claude/history.jsonl
CHANGED ~/.claude/plugins/store/cc-plugin-you-should-know_builtin-19776595df2c.json
flagged=2
```

Both CHANGED files belong to the running orchestrating Claude session (prompt history and a plugin state store); the spike's own host calls all ran with a scratch HOME and only printed help or version text. Nothing listed was removed, moved or edited.

## Cleanup

- leftovers: none (two runs of the process-group check; every recorded group is gone)
- herdr tabs: one tab created for Q9 and closed by its recorded id; the tab list afterwards holds no spike tab
- removed paths: scratch HOME, scratch CODEX_HOME and the Q9 folder under the spike folder; no probe repositories were created
- out/help kept for 37-02, raw output removed
