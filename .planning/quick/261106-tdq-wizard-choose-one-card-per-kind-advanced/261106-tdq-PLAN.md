---
phase: quick-261106-tdq
plan: 01
type: quick
autonomous: true
---

# Quick task 261106-tdq: one Choose card per component kind

Owner request 2026-11-06 (translated): no single card for skills, agents and hooks; one card each,
advanced with Enter, so the header reads "Step x of 5", not "of 3". Executed inline, as 261106-n8k was.

<objective>
`tools/wizard_app.py` Choose shows one card per present kind (KINDS order, empty kinds skipped), each
its own screen titled "Choose <kind> to install" with the border `<kind> on/total`; the tab bar and
the ←→ kind switch are gone. Enter goes to the next card, the last card's Enter goes to Arrange
(`_enter_arrange`, Review with zero hosts); Esc goes to the previous card (no-op on the first); Esc
from Arrange's first host (or from Review with zero hosts) lands on the last card. The header reads
"Step i of N" with N pips: N = cards (at least 1) + 1 for Arrange when a host is detected + 1 for
Review; Done keeps "Done" with N green pips.
</objective>

<tasks>
1. View: drop `#kind-tabs`, per-kind title, `_step_kind` (no wrap) for Enter/Esc, `_back_to_choose`
   for the two Esc paths into Choose, `_header_step` for i/N; FOOTERS/HELP/SUBS for Choose lose ←→
   and gain Esc.
2. Tests: the Choose card walk, Esc back, Esc from Arrange to the last card, the header count with
   three kinds and a host (5) and with zero hosts (4), Done pips; the shared `make_ctx` fixture keeps
   one kind so one Enter still leaves Choose. PTY tests walk the cards by the header count.
3. Docs: README and the wizard docs that describe the Choose tabs.
</tasks>

<verify>
`make test-unit`, `make test-integration`, `python3 -m unittest tests.test_wizard_pty` (under uv),
snapshots under `tmp/wizard-fixes/quick-ui/`, one `make test` at the end of both quick tasks.
</verify>
