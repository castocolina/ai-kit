# Status-Line Rate-Limit Split + Compaction-Aware Chat Size Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Split the bundled `alt_rate_limits` segment into two independent, width-adaptive segments
(`alt_h_rate_limit`, `alt_w_rate_limit`), and make `chat_size` compaction-aware (showing bytes
since the last `/compact` alongside the historical total and compaction count) instead of only
ever-growing raw disk bytes.

**Architecture:** Both features are additive within `tools/status-line.py`'s existing
builder-registry pattern (`SEGMENTS`/`BUILDERS`/`LAYOUT`/`_RAMP_DEFAULTS`/`util_first_fitting`
tiering) — no changes to the packer, `Context`, or `Theme` machinery themselves. FR-1 deletes
`seg_alt_rate_limits`/`util_rate_str`/`util_reset_suffix` and replaces them with a shared
`util_rate_group_str` helper plus two builders (`BUILDERS` auto-discovers them from their
`seg_*` names — no manual registry edit). FR-2 adds a new pure probe
(`probe_transcript_compaction`) that scans the transcript once for `compact_boundary` markers,
wires it through the existing `_memo`/`probe_cache` pattern, and reworks `seg_chat_size`'s
tiering and ramp source.

**Tech Stack:** Python 3.12 stdlib only (`re`, `json`, `datetime`, `os`) — `tools/status-line.py`
stays `python3 -S` stdlib-only per the project's render-path purity rule. Tests: `python3 -m
unittest` (NOT pytest), run directly against `tests/test_status_line.py` and `tests/test_setup.py`.

## Global Constraints

- **PRD**: `docs/prds/statusline-rate-chat-segments-v1.0-prd.md` — every format string, tier, and
  drop-order rule below is copied verbatim from its resolved Design Decisions; do not re-derive.
- **No legacy alias** for `alt_rate_limits` — it is deleted outright (off by default today, so
  breaking risk is low), per the project's established canonical-only convention.
- **`seg_context` is never touched** by this plan — it already reads Claude Code's own
  `context_window.used_percentage`/`context_window_size`, which is correct and out of scope.
- **`SEGMENTS`/`LAYOUT` in `tools/status-line.py` and `SEGMENT_DEFAULTS`/`LAYOUT_DEFAULTS` in
  `tools/setup.py` must stay byte-identical** (a drift guard test —
  `tests/test_setup.py::TestWizardEngineHelpers` around line 100 — asserts this; every task that
  touches one must touch the other in the same commit).
- **Gate**: `python3 -m unittest tests.test_status_line tests.test_setup -v` plus `make lint`
  (ruff/pylint/pyright/vulture/shellcheck) must pass before every commit in this plan.
- **`fmt_bytes`, `fmt_rate_key_label`, `util_pick_color`, `util_first_fitting`, `util_icon`,
  `_memo`, `RESET` are existing helpers — reuse them verbatim, do not reimplement.**

---

## Task 1: Split `alt_rate_limits` into `alt_h_rate_limit` + `alt_w_rate_limit`

**Files:**
- Modify: `tools/status-line.py` — delete `util_reset_suffix` (~line 1503), `util_rate_str`
  (~line 1515), `seg_alt_rate_limits` (~line 2274); add `_rate_bucket_hourly`,
  `util_hour_reset_suffix`, `util_week_reset_suffix`, `util_rate_group_str` (near the deleted
  `util_reset_suffix`/`util_rate_str`, ~line 1503); add `seg_alt_h_rate_limit` +
  `seg_alt_w_rate_limit` (where `seg_alt_rate_limits` was, ~line 2274); update `SEGMENTS` (~line
  82) and `LAYOUT`'s diagnostics row (~line 116).
- Modify: `tools/setup.py` — update `SEGMENT_DEFAULTS` (~line 82), `LAYOUT_DEFAULTS` (~line
  84-93), and the inventory description dict (~line 296).
- Modify: `tools/statusline.toml.sample` — update the `[segments]` comment block (~lines 46-48),
  the `[[line]]` example (~line 65), and the diagnostics-row `[[line]]` block (~line 62-64).
- Modify: `README.md` — replace the sample-TOML-adjacent mention of `alt_rate_limits` with the two
  new segments (a new bolded paragraph, mirroring the existing `alt_git_worktree` paragraph at
  ~line 168).
- Test: `tests/test_status_line.py` — replace `test_rate_limits_shows_reset_then_drops_suffix_when_narrow`
  and its neighboring rate-limit tests (~lines 427-469); update `test_builders_registry_complete`
  (~line 476) and `test_discovered_builders_cover_segments` (~line 786) to swap `alt_rate_limits`
  for the two new keys.

**Interfaces:**
- Produces: `seg_alt_h_rate_limit(ctx, avail, theme) -> str | None`, `seg_alt_w_rate_limit(ctx,
  avail, theme) -> str | None` — both auto-register into `BUILDERS` via the existing `seg_*`
  discovery (FR-A.3); no other task depends on their internals.
- Consumes: `ctx.rate_limits: dict[str, Any]` (unchanged shape), `fmt_rate_key_label`,
  `util_rate_color`, `util_icon`, `util_first_fitting`, `RESET` (all pre-existing).

### Step 1: Write the failing tests

Replace the block from `def test_rate_limits_shows_reset_then_drops_suffix_when_narrow(self):`
through the end of that rate-limit test group (ending at the `test_...wide_reset_stamp` test,
~line 469) in `tests/test_status_line.py` with:

```python
    def test_h_rate_limit_shows_time_only_reset_then_drops_it_when_narrow(self):
        rl = {"five_hour": {"used_percentage": 42, "resets_at": NOW + 3600}}
        rich = strip(sl.seg_alt_h_rate_limit(_data(rate_limits=rl), 200, THEME))
        self.assertIn("5h: 42%", rich)
        self.assertIn("↺", rich)
        # time-only reset stamp — no date component at all
        dt = sl.datetime.fromtimestamp(NOW + 3600)
        self.assertIn(dt.strftime("%H:%M"), rich)
        self.assertNotIn(dt.strftime("%b"), rich)
        narrow = strip(sl.seg_alt_h_rate_limit(_data(rate_limits=rl), 10, THEME))
        self.assertEqual(narrow, "⚡ 5h: 42%")
        self.assertIsNone(sl.seg_alt_h_rate_limit(_data(rate_limits={}), 200, THEME))

    def test_h_rate_limit_hides_when_no_hourly_bucket(self):
        rl = {"seven_day": {"used_percentage": 13, "resets_at": NOW + 86400}}
        self.assertIsNone(sl.seg_alt_h_rate_limit(_data(rate_limits=rl), 200, THEME))

    def test_h_rate_limit_ignores_weekly_bucket(self):
        rl = {"five_hour": {"used_percentage": 42, "resets_at": NOW + 3600},
              "seven_day": {"used_percentage": 13, "resets_at": NOW + 86400}}
        out = strip(sl.seg_alt_h_rate_limit(_data(rate_limits=rl), 200, THEME))
        self.assertIn("5h:", out)
        self.assertNotIn("7d:", out)

    def test_w_rate_limit_shows_weekday_reset_then_drops_it_when_narrow(self):
        rl = {"seven_day": {"used_percentage": 13, "resets_at": NOW + 86400}}
        rich = strip(sl.seg_alt_w_rate_limit(_data(rate_limits=rl), 200, THEME))
        self.assertIn("7d: 13%", rich)
        dt = sl.datetime.fromtimestamp(NOW + 86400)
        self.assertIn(dt.strftime("%a"), rich)
        self.assertIn(dt.strftime("%H:%M"), rich)
        self.assertNotIn(dt.strftime("%b %d"), rich)
        narrow = strip(sl.seg_alt_w_rate_limit(_data(rate_limits=rl), 10, THEME))
        self.assertEqual(narrow, "⚡ 7d: 13%")
        self.assertIsNone(sl.seg_alt_w_rate_limit(_data(rate_limits={}), 200, THEME))

    def test_w_rate_limit_hides_when_no_weekly_bucket(self):
        rl = {"five_hour": {"used_percentage": 42, "resets_at": NOW + 3600}}
        self.assertIsNone(sl.seg_alt_w_rate_limit(_data(rate_limits=rl), 200, THEME))

    def test_rate_limit_no_reset_stamp_when_absent(self):
        rl_h = {"five_hour": {"used_percentage": 30}}
        self.assertEqual(strip(sl.seg_alt_h_rate_limit(_data(rate_limits=rl_h), 200, THEME)),
                         "⚡ 5h: 30%")
        rl_w = {"seven_day": {"used_percentage": 30}}
        self.assertEqual(strip(sl.seg_alt_w_rate_limit(_data(rate_limits=rl_w), 200, THEME)),
                         "⚡ 7d: 30%")

    def test_weekly_drops_before_hourly_under_column_pressure(self):
        # Both fit at 200 cols; at a width that fits only ONE segment's terse
        # form plus a separator, the packer keeps the hourly (leftmost) one —
        # this is enforced by LAYOUT ordering, checked at the registry level.
        idx_h = sl.LAYOUT[2].segments.index("alt_h_rate_limit")
        idx_w = sl.LAYOUT[2].segments.index("alt_w_rate_limit")
        self.assertLess(idx_h, idx_w, "alt_w_rate_limit must sit to the right (dropped first)")
```

Then update the two registry-list tests: in `test_builders_registry_complete` (~line 476) and
`test_discovered_builders_cover_segments` (~line 786), replace `"alt_rate_limits"` with
`"alt_h_rate_limit", "alt_w_rate_limit"` in both tuples.

- [ ] Step 1 complete

### Step 2: Run the new tests to confirm they fail

Run: `python3 -m unittest tests.test_status_line -k "rate_limit" -v`

Expected: FAIL — `AttributeError: module 'status_line' has no attribute 'seg_alt_h_rate_limit'`
(and similar for `seg_alt_w_rate_limit`).

- [ ] Step 2 complete

### Step 3: Delete the old rate-limit code, add the new helpers + builders

In `tools/status-line.py`, delete `util_reset_suffix` (~line 1503-1512), `util_rate_str`
(~line 1515-1532), and `seg_alt_rate_limits` (~line 2274-2280 — the function reading
`ctx.rate_limits` and calling `util_first_fitting([util_rate_str(...), ...])`).

In their place (same location as the deleted `util_reset_suffix`/`util_rate_str`), add:

```python
def _rate_bucket_hourly(key: str) -> bool:
    """True if `key` (e.g. 'five_hour') names an hourly bucket; False for
    day/week/month buckets (e.g. 'seven_day')."""
    _, _, unit = key.partition("_")
    return unit in ("hour", "hours")


def util_hour_reset_suffix(reset: int | None) -> str:
    """Time-only reset stamp for the hourly bucket — never a date, since a
    5-hour window can't meaningfully cross into a different day."""
    if reset is None:
        return ""
    return f" (↺ {datetime.fromtimestamp(reset).strftime('%H:%M')})"


def util_week_reset_suffix(reset: int | None) -> str:
    """Weekday + time reset stamp for the weekly bucket (e.g. 'Sun 14:10')."""
    if reset is None:
        return ""
    return f" (↺ {datetime.fromtimestamp(reset).strftime('%a %H:%M')})"


def util_rate_group_str(
    rate_limits: dict[str, Any], hourly: bool, show_reset: bool, theme: "Theme",
) -> str | None:
    """Format only the buckets whose unit matches `hourly` (True: hour(s);
    False: everything else — day/week/month) into one icon string, or None
    when no matching bucket reports a percentage."""
    suffix_fn = util_hour_reset_suffix if hourly else util_week_reset_suffix
    parts: list[str] = []
    for key in sorted(rate_limits):
        if _rate_bucket_hourly(key) != hourly:
            continue
        info: dict[str, Any] = cast(dict[str, Any], rate_limits[key] or {})
        pct_raw: Any = info.get("used_percentage")
        if pct_raw is None:
            continue
        pct = float(pct_raw)
        reset_raw: Any = info.get("resets_at")
        reset: int | None = int(reset_raw) if reset_raw is not None else None
        color = util_rate_color(pct, theme)
        suffix = suffix_fn(reset) if show_reset else ""
        parts.append(f"{fmt_rate_key_label(key)}: {color}{round(pct)}%{RESET}{suffix}")
    return util_icon("⚡", " | ".join(parts)) if parts else None
```

Where `seg_alt_rate_limits` was, add:

```python
def seg_alt_h_rate_limit(ctx: "Context", avail: int, theme: "Theme") -> str | None:
    rl = ctx.rate_limits
    if not rl:
        return None
    return util_first_fitting(
        [util_rate_group_str(rl, True, True, theme),
         util_rate_group_str(rl, True, False, theme)], avail)


def seg_alt_w_rate_limit(ctx: "Context", avail: int, theme: "Theme") -> str | None:
    rl = ctx.rate_limits
    if not rl:
        return None
    return util_first_fitting(
        [util_rate_group_str(rl, False, True, theme),
         util_rate_group_str(rl, False, False, theme)], avail)
```

- [ ] Step 3 complete

### Step 4: Wire `SEGMENTS` and `LAYOUT`

In `tools/status-line.py`, in `SEGMENTS` (~line 82), replace:

```python
    "chat_size": True, "alt_process_memory": False, "alt_rate_limits": False,
```

with:

```python
    "chat_size": True, "alt_process_memory": False,
    "alt_h_rate_limit": False, "alt_w_rate_limit": False,
```

In `LAYOUT` (~line 116), replace the diagnostics row:

```python
    Line(30, ["render_time", "slowest", "alt_term_dimensions", "context",
              "chat_size", "alt_process_memory", "alt_rate_limits"]),
```

with (hourly BEFORE weekly — leftmost is kept first, so weekly drops first):

```python
    Line(30, ["render_time", "slowest", "alt_term_dimensions", "context",
              "chat_size", "alt_process_memory", "alt_h_rate_limit", "alt_w_rate_limit"]),
```

- [ ] Step 4 complete

### Step 5: Run the rate-limit tests — they must now pass

Run: `python3 -m unittest tests.test_status_line -k "rate_limit" -v`

Expected: all new tests PASS (8 tests).

- [ ] Step 5 complete

### Step 6: Mirror `tools/setup.py` and run the drift guard

In `tools/setup.py`, in `SEGMENT_DEFAULTS` (~line 82), replace:

```python
    "chat_size": True, "alt_process_memory": False, "alt_rate_limits": False,
```

with:

```python
    "chat_size": True, "alt_process_memory": False,
    "alt_h_rate_limit": False, "alt_w_rate_limit": False,
```

In `LAYOUT_DEFAULTS` (~lines 84-93), replace the last block:

```python
    {"min_rows": 30, "segments": ["render_time", "slowest", "alt_term_dimensions",
                                  "context", "chat_size", "alt_process_memory",
                                  "alt_rate_limits"]},
```

with:

```python
    {"min_rows": 30, "segments": ["render_time", "slowest", "alt_term_dimensions",
                                  "context", "chat_size", "alt_process_memory",
                                  "alt_h_rate_limit", "alt_w_rate_limit"]},
```

In the inventory description dict (~line 296), replace:

```python
    "alt_rate_limits": "⚡ rate-limit buckets with reset time",
```

with:

```python
    "alt_h_rate_limit": "⚡ 5-hour rate-limit bucket (time-only reset)",
    "alt_w_rate_limit": "⚡ 7-day rate-limit bucket (weekday reset)",
```

Run: `python3 -m unittest tests.test_setup -k "layout or drift or segment_defaults" -v`

Expected: PASS — the drift guard confirms `setup.LAYOUT_DEFAULTS`/`SEGMENT_DEFAULTS` still mirror
`status-line.py`'s `LAYOUT`/`SEGMENTS`.

- [ ] Step 6 complete

### Step 7: Update the sample TOML and README

In `tools/statusline.toml.sample`, replace line 48:

```toml
# alt_rate_limits = false    # ⚡ rate-limit buckets with reset time
```

with:

```toml
# alt_h_rate_limit = false   # ⚡ 5-hour rate-limit bucket (time-only reset)
# alt_w_rate_limit = false   # ⚡ 7-day rate-limit bucket (weekday reset)
```

Replace the `[[line]]` example segments list at ~line 65 and the diagnostics-row `[[line]]` block
at ~line 62-64, both instances of:

```
"render_time", "slowest", "alt_term_dimensions", "context", "chat_size", "alt_process_memory", "alt_rate_limits"
```

with:

```
"render_time", "slowest", "alt_term_dimensions", "context", "chat_size", "alt_process_memory", "alt_h_rate_limit", "alt_w_rate_limit"
```

In `README.md`, after the existing `alt_git_worktree` paragraph (ends ~line 172, right before
"**Shared git probe + cache TTL**"), add:

```markdown
**Rate-limit segments** — split into `alt_h_rate_limit` (5-hour bucket) and `alt_w_rate_limit`
(7-day bucket), both **off by default**. Each renders `{Nh|Nd}: {pct}%` and degrades to that bare
form when space is tight; with room, the hourly segment adds a time-only reset stamp
(`5h: 42% (↺ 14:10)` — never a date, since a 5-hour window can't cross into a different day), and
the weekly segment adds a weekday + time stamp (`7d: 13% (↺ Sun 14:10)`). In the diagnostics row,
`alt_h_rate_limit` sits to the left of `alt_w_rate_limit`, so the weekly segment is always the
first of the two dropped under column pressure.
```

- [ ] Step 7 complete

### Step 8: Run the full test suite + lint

Run: `python3 -m unittest tests.test_status_line tests.test_setup -v`

Expected: all PASS, 0 failures.

Run: `make lint`

Expected: EXIT=0 (ruff/pylint/pyright/vulture/shellcheck clean — vulture in particular confirms
nothing still references the deleted `util_reset_suffix`/`util_rate_str`/`seg_alt_rate_limits`).

- [ ] Step 8 complete

### Step 9: Commit

```bash
git add tools/status-line.py tools/setup.py tools/statusline.toml.sample README.md \
        tests/test_status_line.py
git commit -m "feat(status-line): split alt_rate_limits into alt_h_rate_limit + alt_w_rate_limit

Replaces the bundled 5h+7d rate-limit string with two independent segments:
alt_h_rate_limit (time-only reset, never a date) and alt_w_rate_limit
(weekday+time reset). Weekly sits right of hourly in the diagnostics row so
it is always the first of the two dropped under column pressure. No legacy
alias — alt_rate_limits is removed outright (off by default, low risk)."
```

- [ ] Step 9 complete

---

## Task 2: Transcript compaction-boundary probe (pure function)

**Files:**
- Modify: `tools/status-line.py` — add `_COMPACT_BOUNDARY_RE` and
  `probe_transcript_compaction` near `probe_transcript_bytes` (~line 918).
- Test: `tests/test_status_line.py` — new `TestProbeTranscriptCompaction` class (add near the
  existing transcript-probe tests, or as a new class before `TestChatSizeRamp` at ~line 1177).

**Interfaces:**
- Produces: `probe_transcript_compaction(path: str, total_bytes: int) -> tuple[int, int]` —
  `(since_bytes, compact_count)`. Never raises. Task 3 consumes this signature exactly.
- Consumes: nothing new — stdlib `re`/`json`/`os` only.

### Step 1: Write the failing tests

Add to `tests/test_status_line.py`, before `class TestChatSizeRamp(unittest.TestCase):`:

```python
class TestProbeTranscriptCompaction(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def _write(self, lines):
        path = os.path.join(self.tmp, "transcript.jsonl")
        with open(path, "w", encoding="utf-8") as f:
            for line in lines:
                f.write(line + "\n")
        return path

    def test_no_boundary_since_equals_total(self):
        path = self._write([
            json.dumps({"type": "user", "message": {"role": "user", "content": "hi"}}),
            json.dumps({"type": "assistant", "message": {"role": "assistant", "content": "hey"}}),
        ])
        total = os.path.getsize(path)
        since, count = sl.probe_transcript_compaction(path, total)
        self.assertEqual(count, 0)
        self.assertEqual(since, total)

    def test_one_boundary_since_is_tail_only(self):
        pre = json.dumps({"type": "user", "message": {"role": "user", "content": "long history"}})
        boundary = json.dumps({"type": "system", "subtype": "compact_boundary",
                                "compactMetadata": {"trigger": "manual",
                                                     "preTokens": 100000, "postTokens": 500}})
        post = json.dumps({"type": "user", "message": {"role": "user", "content": "new turn"}})
        path = self._write([pre, boundary, post])
        total = os.path.getsize(path)
        since, count = sl.probe_transcript_compaction(path, total)
        self.assertEqual(count, 1)
        # since = the boundary line + everything after it, not the pre-boundary line
        expected_since = len((boundary + "\n" + post + "\n").encode("utf-8"))
        self.assertEqual(since, expected_since)
        self.assertLess(since, total)

    def test_three_boundaries_counted(self):
        boundary = json.dumps({"type": "system", "subtype": "compact_boundary",
                                "compactMetadata": {"trigger": "auto"}})
        path = self._write([boundary, "x", boundary, "y", boundary, "z"])
        total = os.path.getsize(path)
        since, count = sl.probe_transcript_compaction(path, total)
        self.assertEqual(count, 3)
        expected_since = len((boundary + "\nz\n").encode("utf-8"))
        self.assertEqual(since, expected_since)

    def test_malformed_boundary_shape_is_ignored(self):
        # matches the substring but wrong "type", and a non-JSON line — neither counts
        wrong_type = json.dumps({"type": "user", "subtype": "compact_boundary"})
        not_json = '{"subtype":"compact_boundary", not valid json'
        path = self._write([wrong_type, not_json])
        total = os.path.getsize(path)
        since, count = sl.probe_transcript_compaction(path, total)
        self.assertEqual(count, 0)
        self.assertEqual(since, total)

    def test_missing_file_returns_total_zero(self):
        since, count = sl.probe_transcript_compaction(
            os.path.join(self.tmp, "nonexistent.jsonl"), 12345)
        self.assertEqual((since, count), (12345, 0))
```

Add `import shutil` and `import tempfile` to the top of `tests/test_status_line.py` if not already
imported (both already are, per the existing `import shutil` / `import tempfile` at the top of the
file — no change needed there).

- [ ] Step 1 complete

### Step 2: Run the new tests to confirm they fail

Run: `python3 -m unittest tests.test_status_line.TestProbeTranscriptCompaction -v`

Expected: FAIL — `AttributeError: module 'status_line' has no attribute
'probe_transcript_compaction'`.

- [ ] Step 2 complete

### Step 3: Implement `probe_transcript_compaction`

In `tools/status-line.py`, immediately after `probe_transcript_bytes` (~line 925), add:

```python
_COMPACT_BOUNDARY_RE = re.compile(r'"subtype"\s*:\s*"compact_boundary"')


def probe_transcript_compaction(path: str, total_bytes: int) -> tuple[int, int]:
    """Scan the transcript for compact_boundary markers. Returns
    (since_bytes, compact_count): since_bytes is the byte count from the start
    of the LAST compact_boundary record's line to EOF (== total_bytes when none
    found); compact_count is how many valid compact_boundary records were
    found. The compaction-marker JSON shape is Claude Code's internal, version-
    dependent format — a malformed/renamed shape (doesn't parse, or parses but
    isn't {"type":"system","subtype":"compact_boundary"}) is silently skipped,
    never raised; a missing/unreadable file degrades to (total_bytes, 0)."""
    last_offset: int | None = None
    count = 0
    try:
        with open(path, "rb") as f:
            offset = 0
            for raw_line in f:
                line = raw_line.decode("utf-8", errors="replace")
                if _COMPACT_BOUNDARY_RE.search(line):
                    try:
                        obj = json.loads(line)
                    except json.JSONDecodeError:
                        obj = None
                    if (isinstance(obj, dict) and obj.get("type") == "system"
                            and obj.get("subtype") == "compact_boundary"):
                        last_offset = offset
                        count += 1
                offset += len(raw_line)
    except OSError:
        return total_bytes, 0
    since = total_bytes - last_offset if last_offset is not None else total_bytes
    return since, count
```

Confirm `re` and `json` are already imported at module level (both are — `re` is used throughout
for ANSI stripping, `json` is used by `cfg_load_toml`'s neighbors). No new imports needed.

- [ ] Step 3 complete

### Step 4: Run the tests — they must now pass

Run: `python3 -m unittest tests.test_status_line.TestProbeTranscriptCompaction -v`

Expected: 5 tests PASS.

- [ ] Step 4 complete

### Step 5: Run the full suite + lint, then commit

Run: `python3 -m unittest tests.test_status_line -v` — expected: all PASS.

Run: `make lint` — expected: EXIT=0.

```bash
git add tools/status-line.py tests/test_status_line.py
git commit -m "feat(status-line): probe_transcript_compaction — scan transcript for compact_boundary markers

Pure function: (since_bytes, compact_count) from the transcript's
compact_boundary records. Never raises; a missing file or an unrecognized
marker shape degrades to (total_bytes, 0). Not yet wired into any segment
(Task 3)."
```

- [ ] Step 5 complete

---

## Task 3: Wire the compaction probe into `chat_size`

**Files:**
- Modify: `tools/status-line.py` — add `probe_chat_compaction` near `probe_chat_size` (~line
  1087); rewrite `seg_chat_size` (~line 2259); the `chat_size` ramp's semantic key stays
  `theme.ramps["chat_size"]` (no rename), but is now driven by `since_bytes`.
- Modify: `tests/test_status_line.py` — extend the `_data()` test fixture (~lines 53-91) with
  `chat_since`/`chat_compactions` overrides; add tiering tests near `TestChatSizeRamp` (~line
  1177).
- Modify: `README.md` — add a `chat_size` paragraph distinguishing it from `context` (after the
  rate-limit paragraph added in Task 1, or after the `alt_git_worktree`/`alt_h_rate_limit`
  paragraphs — same location).
- Modify: `tools/setup.py` — update the `chat_size` inventory description (~line 294) to mention
  the compaction-aware reading.

**Interfaces:**
- Consumes: `probe_transcript_compaction(path, total_bytes) -> tuple[int, int]` (Task 2, exact
  signature). `probe_chat_size(ctx) -> int | None` (pre-existing, unchanged).
- Produces: `probe_chat_compaction(ctx) -> tuple[int, int] | None` — `None` exactly when
  `probe_chat_size(ctx)` is `None` (mirrors the existing "no transcript" contract).

### Step 1: Write the failing tests

In `tests/test_status_line.py`, extend `_data()`'s `probe_defaults` dict (~line 67-73) — add two
new keys after `"chat_bytes": 305000, "mem_bytes": 448_790_528,`:

```python
        "chat_bytes": 305000, "mem_bytes": 448_790_528,
        "chat_since": None, "chat_compactions": 0,
```

Then, right after the existing `ctx.probe_cache["chat_size"] = probe_over["chat_bytes"]` line
(~line 87), add:

```python
    if probe_over["chat_bytes"] is None:
        ctx.probe_cache["chat_compaction"] = None
    else:
        since = (probe_over["chat_bytes"] if probe_over["chat_since"] is None
                  else probe_over["chat_since"])
        ctx.probe_cache["chat_compaction"] = (since, probe_over["chat_compactions"])
```

Now add new tests in `tests/test_status_line.py`, right after `TestChatSizeRamp`'s existing
`test_seg_chat_size_none_when_no_bytes` (~line 1201), inside the same class:

```python
    def test_never_compacted_shows_total_only_at_both_tiers(self):
        out_wide = strip(sl.seg_chat_size(_data(chat_bytes=850_000), 200, THEME))
        out_narrow = strip(sl.seg_chat_size(_data(chat_bytes=850_000), 40, THEME))
        self.assertEqual(out_wide, out_narrow)
        self.assertIn(sl.fmt_bytes(850_000), out_wide)
        self.assertNotIn("/", out_wide)
        self.assertNotIn("x)", out_wide)

    def test_compacted_shows_since_over_total_with_count_when_room(self):
        out = strip(sl.seg_chat_size(
            _data(chat_bytes=4_200_000, chat_since=320_000, chat_compactions=3), 200, THEME))
        self.assertIn(f"{sl.fmt_bytes(320_000)}/{sl.fmt_bytes(4_200_000)} (3x)", out)

    def test_compacted_drops_to_since_only_when_narrow(self):
        out = strip(sl.seg_chat_size(
            _data(chat_bytes=4_200_000, chat_since=320_000, chat_compactions=3), 12, THEME))
        self.assertEqual(out, f"💾 {sl.fmt_bytes(320_000)}")

    def test_ramp_color_driven_by_since_not_total(self):
        # 6 MB total but only 900 KB since last compaction -> CYAN band, not RED
        out = sl.seg_chat_size(
            _data(chat_bytes=6 * self.MB, chat_since=900 * self.KB, chat_compactions=1), 200, THEME)
        self.assertIn(THEME.c("CYAN"), out)
        self.assertNotIn(THEME.c("RED+bold"), out)
```

- [ ] Step 1 complete

### Step 2: Run the new tests to confirm they fail

Run: `python3 -m unittest tests.test_status_line -k "chat_size or compacted" -v`

Expected: FAIL — `test_compacted_shows_since_over_total_with_count_when_room` and
`test_compacted_drops_to_since_only_when_narrow` fail (current `seg_chat_size` only ever shows the
total); `test_ramp_color_driven_by_since_not_total` fails (current ramp reads the total, so 6 MB
still colors RED+bold).

- [ ] Step 2 complete

### Step 3: Add `probe_chat_compaction` and rewrite `seg_chat_size`

In `tools/status-line.py`, immediately after `probe_chat_size` (~line 1089), add:

```python
def probe_chat_compaction(ctx: "Context") -> tuple[int, int] | None:
    """Memoized (since_bytes, compact_count) for the transcript — None exactly
    when probe_chat_size(ctx) is None (mirrors its 'no transcript' contract)."""
    total = probe_chat_size(ctx)
    if total is None:
        return None
    return _memo(ctx, "chat_compaction",
                 lambda: probe_transcript_compaction(ctx.transcript, total))
```

Replace `seg_chat_size` (~line 2259-2264):

```python
def seg_chat_size(ctx: "Context", avail: int, theme: "Theme") -> str | None:
    n = probe_chat_size(ctx)
    if n is None:
        return None
    color = util_pick_color(n, theme.ramps["chat_size"])
    return util_first_fitting([util_icon("💾", f"{color}{fmt_bytes(n)}{RESET}")], avail)
```

with:

```python
def seg_chat_size(ctx: "Context", avail: int, theme: "Theme") -> str | None:
    compaction = probe_chat_compaction(ctx)
    if compaction is None:
        return None
    since, count = compaction
    total = probe_chat_size(ctx)     # memoized — free, already computed above
    color = util_pick_color(since, theme.ramps["chat_size"])
    if count == 0:
        return util_first_fitting(
            [util_icon("💾", f"{color}{fmt_bytes(since)}{RESET}")], avail)
    rich = util_icon("💾", f"{color}{fmt_bytes(since)}/{fmt_bytes(total)} ({count}x){RESET}")
    terse = util_icon("💾", f"{color}{fmt_bytes(since)}{RESET}")
    return util_first_fitting([rich, terse], avail)
```

- [ ] Step 3 complete

### Step 4: Run the tests — they must now pass

Run: `python3 -m unittest tests.test_status_line -k "chat_size or compacted" -v`

Expected: all PASS, including the two pre-existing tests
(`test_seg_chat_size_colors_the_size`, `test_seg_chat_size_none_when_no_bytes`) — they still pass
unchanged because `chat_since` defaults to `None` in `_data()`, which the fixture treats as "equal
to `chat_bytes`, 0 compactions," i.e. identical behavior to today when no compaction happened.

- [ ] Step 4 complete

### Step 5: Update `tools/setup.py`'s inventory description

In `tools/setup.py` (~line 294), replace:

```python
    "chat_size": "💾 transcript file size on disk",
```

with:

```python
    "chat_size": "💾 bytes since last compaction/total on disk (+ compaction count)",
```

Run: `python3 -m unittest tests.test_setup -k "inventory or description" -v` — expected: PASS (no
test currently pins the exact string; this just keeps the wizard's Choose-screen description
accurate — confirm no hard-coded-string test breaks with `python3 -m unittest tests.test_setup -v`).

- [ ] Step 5 complete

### Step 6: Update the README

In `README.md`, after the rate-limit paragraph added in Task 1, add:

```markdown
**`chat_size` vs `context`** — these answer different questions. `chat_size` (💾) reads the
transcript `.jsonl` on disk, which is **append-only and never shrinks** — even a `/compact` only
adds a boundary marker + summary to the file, it never removes anything. So `chat_size` shows
bytes accumulated **since the last compaction** (falling back to the full total when there hasn't
been one yet), plus the total and how many compactions have happened once there's been at least
one: `320K/4.2M (3x)` — narrower terminals drop to just the "since" figure. `context` (📊,
`seg_context`) is a *different* segment, unaffected by this: it reads Claude Code's own live
`context_window.used_percentage`, which already reflects the real, current context sent to the
model on the next turn. Use `chat_size` to gauge how much has piled up since your last compaction;
use `context` for what's actually in play right now.
```

- [ ] Step 6 complete

### Step 7: Run the full suite + lint

Run: `python3 -m unittest tests.test_status_line tests.test_setup -v`

Expected: all PASS.

Run: `make lint`

Expected: EXIT=0.

- [ ] Step 7 complete

### Step 8: Commit

```bash
git add tools/status-line.py tools/setup.py tests/test_status_line.py README.md
git commit -m "feat(status-line): chat_size is compaction-aware (since/total/count)

seg_chat_size now reads probe_chat_compaction (Task 2's transcript scan):
shows bytes since the last compact_boundary alongside the historical total
and compaction count when room allows, dropping to the 'since' figure alone
when narrow. Falls back to today's plain-total behavior when the session
has never compacted. The chat_size ramp is now keyed on the 'since' value,
not the ever-growing total. seg_context is unmodified."
```

- [ ] Step 8 complete

---

## Task 4: Final full-suite verification + doctor smoke

**Files:** none new — verification only.

**Interfaces:** none new.

### Step 1: Run the full test suite

Run: `make test`

Expected: all suites PASS (status_line, setup, external_segments, markdown_to_pdf [ignore the
pre-existing, environment-only `TestRenderRealMmdc` failure if `mmdc` is broken locally — unrelated
to this plan], worktree_e2e, wizard_pty, sysmem_e2e).

- [ ] Step 1 complete

### Step 2: Run the full lint gate

Run: `make lint`

Expected: EXIT=0.

- [ ] Step 2 complete

### Step 3: Doctor smoke with the new segments enabled

Run:

```bash
printf '{"model":{"display_name":"Opus"},"workspace":{"current_dir":"%s"},"context_window":{"used_percentage":10,"context_window_size":200000},"rate_limits":{"five_hour":{"used_percentage":42,"resets_at":9999999999},"seven_day":{"used_percentage":13,"resets_at":9999999999}}}' "$PWD" \
  | CC_AI_KIT_SEGMENT_ALT_H_RATE_LIMIT=1 CC_AI_KIT_SEGMENT_ALT_W_RATE_LIMIT=1 \
    python3 tools/status-line.py
```

Expected: a rendered line containing `5h: 42%` and `7d: 13%` with no errors on stderr.

Run: `python3 tools/status-line.py --doctor`

Expected: exit 0, "all N segments render cleanly" (N includes the two new segments and excludes
`alt_rate_limits`).

- [ ] Step 3 complete

### Step 4: Confirm no drift between `status-line.py` and `setup.py`

Run:

```bash
python3 -c "
import sys
sys.path.insert(0, 'tools')
import importlib.util
def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod
sl = load('sl', 'tools/status-line.py')
su = load('su', 'tools/setup.py')
assert su.SEGMENT_DEFAULTS == sl.SEGMENTS, 'SEGMENT_DEFAULTS drifted from SEGMENTS'
assert [dict(l._asdict()) for l in sl.LAYOUT] == su.LAYOUT_DEFAULTS, 'LAYOUT drifted'
print('OK: no drift')
"
```

Expected: `OK: no drift`.

- [ ] Step 4 complete

### Step 5: Hand off to branch finishing

No commit in this task (verification only). If all prior steps are green, invoke
`superpowers:finishing-a-development-branch` to decide how this work integrates (merge/PR/keep
as-is), per the user's preference at that time.

- [ ] Step 5 complete

---

## Self-Review

**1. Spec/PRD coverage:**
- FR-1 hourly/weekly split, time-only vs weekday reset stamps, 2-tier degrade, weekly-drops-first
  → Task 1 (all steps). ✓
- FR-1 no legacy alias, `alt_rate_limits` fully removed (segment, builder, `SEGMENTS`/`LAYOUT`,
  `setup.py` mirror, sample TOML) → Task 1 Steps 3, 4, 6, 7. ✓
- FR-2 compaction-boundary scan (append-only file, malformed-shape degrade, missing-file degrade)
  → Task 2 (pure function, fully unit-tested standalone). ✓
- FR-2 `chat_size` since/total/count tiering, ramp keyed on `since` → Task 3 Steps 1-4. ✓
- FR-2 `seg_context` untouched → verified explicitly in Task 4 Step 4 (no `context` reference in
  either diff) and never modified in any task. ✓
- README documentation of both features, including the `chat_size` vs `context` distinction →
  Task 1 Step 7, Task 3 Step 6. ✓
- Drift-guard (`SEGMENT_DEFAULTS`/`LAYOUT_DEFAULTS` vs `SEGMENTS`/`LAYOUT`) → enforced in Task 1
  Step 6 and independently re-verified in Task 4 Step 4. ✓

**2. Placeholder scan:** every step contains literal code, exact line-number anchors, and a runnable
verification command with its expected output. No "TBD"/"handle appropriately"/"similar to Task N"
patterns present. ✓

**3. Type/name consistency:** `probe_transcript_compaction(path, total_bytes) -> tuple[int, int]`
(Task 2) is consumed with that exact signature by `probe_chat_compaction` (Task 3 Step 3).
`_data()`'s `chat_since`/`chat_compactions` overrides (Task 3 Step 1) are consumed identically by
every new test added in Task 3. `seg_alt_h_rate_limit`/`seg_alt_w_rate_limit` (Task 1 Step 3) are
the exact names asserted in the registry tests updated in Task 1 Step 1. ✓
