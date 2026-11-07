---
phase: quick-261106-tdq
plan: 01
subsystem: setup wizard
status: complete
tags: [wizard, choose, header]
key-files:
  modified:
    - tools/wizard_app.py
    - tests/wizard_fixtures.py
    - tests/test_wizard_app_1.py
    - tests/test_wizard_app_2.py
    - tests/test_wizard_pty.py
    - tests/test_system_memory_e2e.py
    - README.md
commits: [2acf64f]
---

# Quick task 261106-tdq summary

- **One card per kind (2acf64f):** Choose has no tab bar; each kind with items is its own screen,
  titled `Choose <kind> to install`, border `<kind> on/total`. Enter goes to the next card, the last
  card's Enter goes to Arrange (Review with no host); Esc goes back a card (no-op on the first), and
  Esc from Arrange's first host or from a host-less Review lands on the last card. ←→ no longer act
  on Choose. FOOTERS/HELP/SUBS for Choose drop ←→ and gain Esc.
- **Header:** `Step i of N` with N pips, N = cards (at least 1) + Arrange when a host is detected +
  Review. This checkout with a host: `Step 1 of 5` (skills), 2 (agents), 3 (hooks), 4 (every host
  pane), 5 (Review); Done shows 5 green pips.
- **Tests:** the card walk, Esc back, Esc from Arrange and from host-less Review to the last card,
  the 5-step and 4-step (no host) counts, Done pips. `make_ctx` keeps one kind so one Enter leaves
  Choose; PTY tests walk the cards from the header count.

Verification: `make test-unit` 100/100 + 1/1, `make test-integration` 8/8,
`tests.test_wizard_pty` + `tests.test_system_memory_e2e` 18 OK; snapshots
`tmp/wizard-fixes/quick-ui/task1-*.txt` from the real app (scratch HOME, both hosts).
