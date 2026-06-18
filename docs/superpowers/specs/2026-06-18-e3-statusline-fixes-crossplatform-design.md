# E3 — Status-Line Bug Fixes + Cross-Platform Clarity · Design

**Status:** approved (brainstorming) — ready for `writing-plans`
**Date:** 2026-06-18
**Scope:** `tools/status-line.py` (+ `tests/test_status_line.py`), one subsystem, one plan.
**Supersedes roadmap note:** the index's "E4 first" sequencing was a PRD mistake — **E3
precedes E4**. We fix the status-line issues now; E4 (the config wizard) later makes the
constants introduced here user-overridable. Correcting the index is part of this work.

## Goal

Fix seven reported status-line defects and make the script genuinely **cross-platform
and clear** — so it renders correctly on macOS and Linux/wezterm, and the two
platform-specific spots read as obviously cross-platform rather than silently
Linux-only.

## Guiding approach

Every fix is a **module-level constant / ramp at a single named lookup point**, mirroring
the file's existing `CONTEXT_RAMP` + `pick_color` idiom. E4's wizard later swaps each
constant's *source* to config with no rework here. Rejected alternatives: a palette-
resolution layer now (YAGNI before E4); inline ad-hoc coloring (un-wireable later).

TDD throughout: each fix lands test-first in `tests/test_status_line.py`.

**Out of scope (deferred to E4):** making any of these colors/thresholds user-overridable
via TOML/env, segment toggles, the wizard. E3 ships correct hardcoded defaults; E4 wires
them to config.

---

## Fix clusters

### 1 · Blue that reads blue (FR-3.3)

`BLUE = "\033[1;34m"` (bold ANSI-blue) renders purple on many terminals. Replace with
256-color true blue **`BLUE = "\033[38;5;33m"`**. Used by `seg_path`, the `CONTEXT_RAMP`
20% band, and effort `medium` — all benefit. Add a distinct **`LIGHTBLUE =
"\033[38;5;75m"`** (cornflower) for the chat-size ramp's band 3.

### 2 · chat-size colored ramp (FR-3.7)

`seg_chat_size` is uncolored today. Add a byte-keyed ramp reusing `pick_color`, and color
`💾 {size}` the way `seg_context` colors its percent. The ramp mirrors the context bar's
8-color progression, with the top two bands pinned to the user's thresholds:

```python
# (ceil_bytes, color) — first ceil the size is strictly below wins
MB = 1024 * 1024
CHAT_SIZE_RAMP = [
    (512 * 1024, WHITE),
    (1 * MB,     CYAN),
    (2 * MB,     LIGHTBLUE),
    (3 * MB,     GREEN),
    (4 * MB,     YELLOW),
    (5 * MB,     ORANGE),
    (10 * MB,    RED),       # >= 5 MB  -> red + bold
    (INF,        MAGENTA),   # >= 10 MB -> purple
]
```

`RED`/`MAGENTA` are already bold in the palette. Ramp shape follows the same
"first ceil the value is below wins" rule as `CONTEXT_RAMP` (so *exactly* 5 MB → red,
*exactly* 10 MB → purple).

### 3 · effort = auto (FR-3.1 detect + FR-3.2 render)

**Detect (FR-3.1).** Today `build_data` reads `raw["effort"]["level"]` /
`CLAUDE_EFFORT`; `auto` is reported as `high`. Working hypothesis: the field literally
carries `"auto"` in one of those, but Claude Code may instead send the *resolved* level.
**This is the one piece that needs a real sample** — at implementation time, capture one
status-line JSON while effort is `auto` and key the detection off whatever marker it
actually exposes. The detection lives at the single `effort = …` assignment.

**Render (FR-3.2).** `auto` currently shows static green. Replace with a **per-letter
rainbow**: the word `auto` *and* the 5 ladder bars `▁▃▄▆█` each cycle through
**CYAN → GREEN → YELLOW → ORANGE → MAGENTA → BLUE**. A new helper
`_rainbow(text, cycle)` colors each visible character by cycling the palette; the
`_EFFORT_BARS["auto"]` entry is generated through it rather than a static string. The
fixed per-effort colors for the other levels are unchanged.

### 4 · memory segment — wezterm bug + macOS (FR-3.4 + FR-3.5)

`proc_rss_bytes()` walks the parent chain for a process named `claude`; today, if it
never matches, it falls through and reports *whatever pid it ended on* — a tiny process,
the wezterm `<10mb` bug.

- **FR-3.4:** return RSS **only when a `claude` process was actually matched** in the
  parent walk; otherwise return `None` (the segment hides — correct, honest absence)
  instead of reporting the last pid the walk landed on. (`claude` is 6 chars, so Linux
  `comm` truncation isn't a factor; exact match stays.) The parent-walk depth/limit is
  reviewed in cluster 6's simplify pass.
- **FR-3.5:** macOS has no `/proc`. Add a fallback that walks the parent chain via
  `ps -o ppid= -p <pid>` and reads RSS via `ps -o rss= -p <pid>` (KB → bytes), matching
  `claude` by the command name (`ps -o comm= -p <pid>`), same "only return on match" rule.

### 5 · terminal dimensions — macOS fallback (FR-3.6)

`terminal_size()` resolves `STATUSLINE_* → COLUMNS/LINES → stty size (/dev/tty)`, then
assumes `200×40`. `stty` works on macOS, but add a final **`tput cols` / `tput lines`**
(run against `/dev/tty`) fallback before the assumed default, so a host where `stty size`
is unavailable still gets real dimensions.

### 6 · Cross-platform clarity pass (the umbrella goal)

The script has **no platform awareness** — it silently assumes Linux in exactly the two
spots above. Make the cross-platform intent explicit and the code clear:

- Keep the **two** platform-specific concerns — *process RSS* and *terminal size* — each
  in **one clearly-named helper** with explicit, commented Linux-vs-macOS branches and a
  documented, ordered fallback chain (so a reader sees "Linux: /proc; macOS: ps; else
  None" at a glance).
- Apply **`/simplify`** and **`/reduce-entropy`** to those helpers during implementation
  to remove incidental complexity (e.g. the bare `for _ in range(4)` parent-walk, the
  nested try/except ladder) and surface the platform structure. **Do not** refactor the
  already-portable code (`git_info`, packing, builders) — stay focused.
- No new dependency on `sys.platform` string-matching where a capability probe is clearer
  (prefer "is `/proc` present?" over "is this Linux?"), so an unrecognized Unix still
  works via the probe + fallback chain.

Net effect: the same behavior on Linux, correct behavior on macOS, and a platform layer
the next reader (or agent) understands immediately.

---

## Index correction

In `docs/prds/000-ai-kit-overhaul-requirements.md`: remove the "**E4 first**" guidance
from the suggested sequence and the E3/E4 dependency lines; note E3 ships standalone and
E4 later makes its colors/thresholds configurable.

## Testing strategy

Extend `tests/test_status_line.py`:

- **chat-size ramp:** one assertion per band, including the exact boundaries 5 MB → red
  and 10 MB → purple (off-by-one guard on the `<`-ceil rule).
- **blue:** assert `seg_path` / context-20% emit `38;5;33`, not `1;34`.
- **effort=auto:** detection maps the sample's marker to `auto`; `seg_effort` output
  contains the rainbow cycle across the word and bars (assert the per-letter SGR sequence,
  not a static green).
- **memory:** `proc_rss_bytes` returns `None` when no `claude` ancestor exists (regression
  for the wezterm bug); Linux `/proc` path still works; macOS `ps` fallback returns bytes
  (monkeypatch `subprocess`/`os.path.exists("/proc")`).
- **dims:** `tput` fallback returns real cols/lines when `stty` is stubbed to fail
  (monkeypatch `subprocess`).
- Platform branches are exercised by faking the capability probe, so both OS paths run in
  CI on Linux.

## Open items

- **effort=auto JSON sample** — needed before implementing cluster 3's *detection* (the
  *rendering* can be built and tested independently of the sample).

## Deliverables

- `tools/status-line.py` — clusters 1–6.
- `tests/test_status_line.py` — coverage above.
- `docs/prds/000-ai-kit-overhaul-requirements.md` — index correction; mark E3 progress.
