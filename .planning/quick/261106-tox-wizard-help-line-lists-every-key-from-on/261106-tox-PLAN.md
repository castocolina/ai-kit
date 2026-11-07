---
phase: quick-261106-tox
plan: 01
type: quick
autonomous: true
---

# Quick task 261106-tox: the wizard's help line lists every key

Owner request 2026-11-06 (translated): `o` belongs in the top help like the other keys; Cursor's help
must match Claude's, never less; the help is one wrapped line, but with enough height it can be shown
better. Executed inline, as 261106-n8k was. The `e` key stays (a later quick task removes it).

<objective>
`tools/wizard_app.py`: the sub-line under each step title is derived from the step's `HELP` rows (one
table: keys, `?` panel text, short text, group, host), so it lists every key the footer and the panel
name, including Arrange's `o`, Tab/⇧Tab, `r`, Esc and Cursor's `x`/`e`. Both host panes show the same
keys; a host-only key is named with its host and listed whenever that host is detected. From
`TALL_HELP_ROWS` (= `LANE_GATE[2]`, 30) rows the help is a lead line plus one group per line
(navigation / edit / status line / continue); below it stays one wrapped line; a resize re-draws it.
</objective>

<tasks>
1. `KeyRow` HELP table, `_key_rows` (host, `g`, `d` filters), `_sub_text`, `_render_sub` on resize;
   SUBS removed; `_render_help` reads the same rows.
2. Tests: every FOOTERS cap and HELP row appears in the sub-line at 24 and 40 rows; Arrange lists
   o/Tab/r/Esc and the Cursor keys by host name; Claude and Cursor panes show identical help; a
   Claude-only install shows no Cursor key; `g` only with the global-rules item; the height switch
   and back on resize.
3. README: Arrange keys gain `x`, `e`, `?`, and a paragraph on the help line.
</tasks>

<verify>
Affected modules, pyright on the changed files, snapshots under `tmp/wizard-fixes/quick-ui/`, one
`make test` at the end.
</verify>
