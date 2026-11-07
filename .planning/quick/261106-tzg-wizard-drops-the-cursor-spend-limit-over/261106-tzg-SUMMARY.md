---
phase: quick-261106-tzg
plan: 01
subsystem: setup wizard, Cursor status line
status: complete
tags: [wizard, cursor, alert]
key-files:
  modified:
    - tools/wizard_app.py
    - tools/cursor_host.py
    - tools/cursor_quota.py
    - tools/common_types.py
    - tools/common_config.py
    - tools/statusline-doctor.py
    - tools/setup.py
    - tools/cursor-statusline.toml.sample
    - README.md
    - tests/test_wizard_hostpane.py
    - tests/test_wizard_app_1.py
    - tests/test_cursor_quota.py
    - tests/test_cursor_status_line.py
    - tests/test_statusline_doctor.py
    - tests/test_setup.py
commits: [8e23e75]
---

# Quick task 261106-tzg summary

- **Wizard (8e23e75):** the Cursor alert row is `Extra-spend alert [on/off]  Cursor spend limit: $20.00
  (from Cursor, read 2m ago; inferred ≈)`, or `Cursor spend limit: unknown (not read from Cursor yet;
  no ai-kit quota cache)`. `e`, `#alert-usd`, `#alert-msg`, the hint/refusal texts and the Input key
  guard are gone; HELP, the sub-line, README and Review name no override.
- **Setting gone:** `HOST_SCALARS["cursor"]` is `{"extra_alert": True}`; `core_extra_alert` always uses
  the Cursor limit; the doctor's alert line and `cursor_limit_text` drop the override wording;
  `AI_KIT_CURSOR_EXTRA_ALERT_USD` is no longer read.
- **Older configs:** `ConfigSpec.retired_host_keys` lists `extra_alert_usd` for Cursor. The binder
  skips it silently, the doctor's `--check` accepts it (rejecting it would make setup reset the whole
  file to `.bak`), and `save_statusline_config` removes its live and commented lines from the
  `[cursor]` table on the next atomic write (`setup.drop_host_keys`), every other byte kept.
- Also fixed: bd44cef's resize timer could re-draw the help line after teardown (intermittent
  `NoMatches` in `test_wizard_app_3`); `_render_sub` now skips a missing sub-line.

Verification: affected modules under uv OK (cursor quota/status line, doctor, setup, wizard 1/2/3,
host pane, arch); ruff, pylint 10.00 and pyright clean on the changed files; commit hook 51/51
modules. Snapshots `tmp/wizard-fixes/quick-data/task3-arrange-cursor-{24,40}rows.txt` (limit from
a synthetic quota cache) and `task3-nocache-arrange-cursor-40rows.txt` (unknown).
