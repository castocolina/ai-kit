# 37-01 Summary: live spike (D-17)

Status: complete. Commit b6f4e8f (`docs(37-01): live spike record for runner session, permission and skill forms`) names only `37-SPIKE.md`.

## What ran

- Task 1: marker, then the help and version refresh of claude, codex, copilot, cursor-agent, opencode and pi (sixteen captures, `codex exec --help`, `codex exec resume --help`, `opencode run --help`, `copilot skill --help` included) in the scrubbed scratch environment, no model call. All sixteen exited 0 and are non-empty. Codex key probe with an empty scratch CODEX_HOME.
- Task 2: the anchored consent regex was run against `tmp/run-2026-11-19/ledger.md` and matched 0 lines (orchestrator decision: no consent line written). Q1-Q5 and Q8 recorded `not probed (no ledger consent line)`, defaults kept. Q9 ran (`HERDR_ENV=1`, herdr 0.9.5 on PATH).
- Task 3: leftovers check (twice), herdr tab list, real-config audit, help handoff, scratch removal, doc check, commit.

## Evidence

- help-refresh: recorded 2026-11-21 (no `not recorded` line). Versions: claude 2.1.330, codex 0.170.0, copilot 1.0.112, cursor-agent 2026.11.13, opencode 2.3.2, pi 1.5.2.
- Codex key: `model_context_window=abc` exits 1 with `invalid type: string "abc", expected i64`; `128000` exits 0. Verdict verified.
- Q9: a herdr-hosted `sh -c 'echo out-line; echo err-line >&2; exit 7'` finished in 1 s, rc 7, both streams in files; tab `close` returned ok. Tab id recorded in `tabs.txt` before use; the later tab list holds no spike tab.
- real-home probes: not run (no ledger consent line).
- Audit: `flagged=2` (`~/.claude/history.jsonl`, one `~/.claude/plugins/store/cc-plugin-you-should-know_builtin-*.json`); both belong to the running orchestrating session, since the marker window covers the whole run. No spike host call touched the real HOME. Nothing removed.
- Leftovers: `leftovers: none` on both runs. `out/` is mode 700 and holds only `out/help/` (16 files); 19 raw files removed. Scratch HOME, CODEX_HOME and `q9/` removed; no probe repositories were created. `marker`, scripts, `pgids.txt`, `tabs.txt` kept under `tmp/run-2026-11-19/p37-spike/`.

## Label flips (all in 37-SPIKE.md)

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

## Deviations

- Task 2 ran the no-consent branch by orchestrator decision; Q1-Q5 and Q8 are open for a later consented spike (labels stay unverified, claude.exec.permission stays the 0c default, claude's error channel not observed).
- Task 1's first 37-SPIKE.md draft was filled in one pass together with Task 2's Q9 and no-consent text (same final content, one write order change). `doc_check.py` printed `spike doc: ok` before and after.
- Q9 script created `launch.sh` and `q9/` under the spike folder (plan-specified), removed afterwards.
