---
status: resolved
trigger: "In the setup wizard I can't turn the status line off. I see an on|off toggle; for Cursor it shows more options, but in neither host did turning it off work."
created: 2026-11-06
updated: 2026-11-06
---

# Debug: wizard cannot turn the status line off

## Symptoms

- expected: turning the toggle off (an ai-kit line) or choosing remove (a foreign line) removes the statusLine from the host config.
- actual: the line stayed after the wizard; Claude showed on|off, Cursor showed more options (the extra-spend alert row of an "ours" Cursor pane).
- errors: none reported.
- timeline: after phases 30.1 to 31 (band toggle and foreign choices shipped in 30.1).
- repro: run the wizard, press o on a host pane, confirm Review.
- owner addition: before 30.1, an unset or foreign line got a "do you want to set it?" question; now an unset Cursor neither asked nor showed a clear off note.

## Current Focus

- hypothesis: resolved (see Resolution).
- next_action: none.

## Evidence

- timestamp: 2026-11-06. Repro harness `tmp/wizard-fixes/debug/repro.py` and `repro2.py` drive the real `WizardApp` with setup's real `_build_wizard_context`, `_make_wizard_commit` and `_prepare_foreign` in a scratch HOME (AI_KIT_REFUSE_REAL_HOME=1), one host and both hosts at once. Start states: unset, ours (installed entry), alias (symlinked spelling of the kit), other install (same script in another dir), foreign (`my-line.sh`), legacy (`status-line.py`).
- timestamp: 2026-11-06. Off on ours and alias removes the line on both hosts and Done reports it; the realpath compare in `tools/command_ownership.py:62` already covers the /home vs /var/home alias.
- timestamp: 2026-11-06. Claude foreign remove (foreign, other install, legacy) FAILS every time: Done shows "claude config changed after the backup you confirmed". Cause: `_make_wizard_commit` ran `_commit_components` first; its hook rows rewrite `~/.claude/settings.json` (default-on hooks), so `_same_bytes(settings, foreign_backup)` in `_commit_host_statusline` no longer holds. Cursor is unaffected (hooks live in hooks.json).
- timestamp: 2026-11-06. Legacy entry: `detect_statusline` called it foreign while `wire_statusline` and `unwire_statusline` called it ours (two rules for one question).
- timestamp: 2026-11-06. `unwire_statusline`/`unwire_statusline_cursor` return True without writing when their ours-check fails, and the wizard commit never re-read the file, so a skipped write would have shown success on Done.
- timestamp: 2026-11-06. History: the pre-30.1 pane had an inline adoption gate (`_adoption_gate_markup`, commit 232b178 and earlier): unset asked "Wire your <host> status line? Y / Enter = set it up, n = skip"; foreign warned "Existing <host> status line detected / Current: <cmd> / Replace it with ai-kit? y = replace, N / Enter = keep mine"; ours skipped it. Not a modal. 30.1 (27b7204) replaced it with the band toggle and notes, dropping the foreign warning with the current command and the unset "not set" wording.
- timestamp: 2026-11-06. Cursor CLI bundle (installed 2026.10.22, `FileBasedConfigProvider.transform`) re-reads cli-config.json before each write, so a running Cursor session does not write the removed statusLine back.

## Eliminated

- hypothesis: a /home vs /var/home alias makes detect say ours and unwire skip. Both use the same realpath compare; reproduced as working.
- hypothesis: the checkout renderer path vs an installed entry splits detect and unwire. Both decide against the same resolved entry; a line from another install is foreign in both, and remove works on Cursor.
- hypothesis: a running Cursor CLI rewrites the removed statusLine back. Its config writer re-reads the file first.

## Resolution

- root_cause: (1) the wizard commit wrote the hook rows into Claude's settings.json before the status-line step, breaking the backup binding, so every confirmed Claude foreign remove or replace was refused; (2) detection and wire/unwire used different "is ai-kit's" rules for the legacy entry; (3) no re-read after a status-line write, so a skipped write could show success; (4) the 30.1 pane lost the old gate's foreign warning and the unset "not set" wording.
- fix: status lines commit before components and hooks (`tools/setup.py` `_make_wizard_commit`); one Claude predicate `_claude_statusline_is_ours(value, status_line)` (entry or legacy beside it) used by detect, wire and unwire; `_verify_host_statusline` re-reads the host after every non-dry status-line action and fails the host with a reason on Done; the pane notes now say "no status line is set" for unset and warn "⚠ <host> already has another status line: <cmd>" for foreign.
- verification: `tests/test_statusline_toggle.py` (off for every start state on both hosts through the whole commit, no-op removal and no-op write reported); `tests/test_wizard_hostpane.py` (notes); repro before/after in `tmp/wizard-fixes/debug/repro-before.json` and `repro-after.json`; TUI text snapshots in `tmp/wizard-fixes/debug/*.txt`.
- not reproduced: the owner's exact Claude and Cursor "ours" off failure. In scratch HOMEs, ours and alias lines turn off on both hosts. If it recurs, Done now names the host and the line still present.
- files_changed: tools/setup.py, tools/wizard_app.py, tests/test_statusline_toggle.py, tests/test_wizard_hostpane.py, README.md
