---
phase: quick-261106-tox
plan: 01
subsystem: setup wizard
status: complete
tags: [wizard, help, keys]
key-files:
  modified:
    - tools/wizard_app.py
    - tests/test_wizard_app_1.py
    - tests/test_wizard_hostpane.py
    - tests/test_system_memory_e2e.py
    - README.md
commits: [bd44cef]
---

# Quick task 261106-tox summary

- **One key table (bd44cef):** `HELP` rows are `KeyRow(keys, help, short, group, host)`; the `?` panel
  and the sub-line under each title both read `_key_rows(step)`, and `SUBS` is gone. Arrange's
  sub-line now lists `o`, Tab/⇧Tab, `r`, Enter, Esc, `?`, `q`; every FOOTERS cap is a HELP key.
- **Parity:** Claude's and Cursor's panes show identical help; Cursor's `x` and `e` are named with the
  host ("x Cursor extra-spend alert on/off", "e Cursor alert override") and listed whenever Cursor is
  detected; a Claude-only install shows no Cursor key. `g` shows only with the global-rules item, `d`
  only with a doctor. `e` stays (a later quick task removes it).
- **Height:** from `TALL_HELP_ROWS` (= `LANE_GATE[2]`, 30 rows) the help is the lead line plus one
  group per line (navigation / edit / status line / continue); below it, one wrapped line; a resize
  re-draws it.
- Also fixed a pyright optional access in 2acf64f's system-memory e2e walk.

Verification: affected wizard modules and PTY/e2e OK, pyright clean on the changed files, `make
vulture` passed; final `make test` exit 0 (unit 100/100, unit-uv 1/1, integration 8/8, e2e 25/25,
install 48/0, arch 1/1); snapshots
`tmp/wizard-fixes/quick-ui/task2-*.txt` (24 and 40 rows).
