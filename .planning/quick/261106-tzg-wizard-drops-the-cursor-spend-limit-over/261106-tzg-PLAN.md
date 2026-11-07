---
phase: quick-261106-tzg
plan: 01
type: quick
autonomous: true
---

# Quick task 261106-tzg: the wizard drops the Cursor spend-limit override

Owner request 2026-11-06 (translated): Cursor's pane still offers a way to set the spend limit,
although it is no longer wanted because the limit is read from Cursor's API. Phase 30.2 already
shows the cap from Cursor in the status line. Executed inline, as 261106-tox was.

<objective>
No dollar override remains anywhere: the wizard's Cursor alert row keeps `x` (on/off) with the
limit read from Cursor beside it ("Cursor spend limit: $X (from Cursor, …)", unknown stays
unknown); `extra_alert_usd` is no longer a setting. The alert threshold is always the Cursor
limit. A stored `extra_alert_usd` (a config from an older ai-kit) is ignored by the renderer,
accepted by the doctor's `--check` (a rejection would make setup reset the whole file to `.bak`)
and dropped on ai-kit's next write of that config, every other byte kept.
</objective>

<tasks>
1. `tools/wizard_app.py`: remove `e`, the `#alert-usd` Input, `#alert-msg`, ALERT_HINT /
   ALERT_BAD_INPUT / ALERT_AMOUNT_RE, `_leave_alert_box`, `_restore_alert_box`,
   `on_input_submitted` and the Input key guard; Review's alert line names the Cursor limit.
2. `cursor_host.HOST_SCALARS` keeps `extra_alert` only; `RETIRED_HOST_KEYS` (new
   `ConfigSpec.retired_host_keys`) lists `extra_alert_usd`, skipped by the config binder and the
   doctor and removed by `setup.drop_host_keys` inside `save_statusline_config` (the one atomic
   write). `cursor_quota.core_extra_alert` drops the override branch; the doctor's alert line and
   `setup.cursor_limit_text` drop the override wording. Sample config and README updated.
3. Tests: a stored override is ignored by the alert rule, the renderer, the binder (TOML and env)
   and `current_host_keys`; the doctor accepts it; the next write drops it (unit and with the real
   doctor); `x` still toggles both ways; help, footers and Review name no `e` or override.
</tasks>

<verify>
Affected modules under uv, ruff/pylint/pyright on the changed files, snapshots under
`tmp/wizard-fixes/quick-data/task3-*`, one `make test` at the end of both quick tasks.
</verify>
