# Color & shape — good vs. flagged

Runnable fixtures in this dir. Bad ones trip a rule in
`scripts/mermaid_style.py`; the good one is clean.

## C1 — flat default gray (`bad-no-style.mmd`)

Seven nodes, no `classDef`: everything is the same gray, nothing reads as the
hot path or a data store. Fix: apply palette A from `references/palettes.md` by role.

## C3 — garish (`bad-garish.mmd`)

Seven saturated fills — color stops meaning anything. Fix: collapse to ≤6 sober
semantic classes.

## S1 — decision drawn as a rectangle (`bad-decision-rect.mmd`)

`A[Validate input]` has two labeled out-edges (`valid`/`invalid`) — that's a
decision and should be a diamond `A{Validate input}`.

## Good (`good-palette.mmd`)

Stadium start, rect services grouped by one accent class, cylinder data store —
color and shape both carry role. Passes all C/S gates.
