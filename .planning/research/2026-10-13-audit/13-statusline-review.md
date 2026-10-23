# 13 — Status-line review: Cursor POC, host-split spec, Claude v1.3 tip

Date: 2026-10-13. Method: `ponytail:ponytail-review` + `ponytail:ponytail-audit`
(order: correct, safe, holds under load, tested, fast, lean), plus the
architecture rules the repo enforces (`tests/test_arch.py` banners and role
prefixes, `common_*`/`claude_*`/`cursor_*` boundaries, pure versus IO).

Read-only. The only writes were this report and throwaway probes in
`scratchpad/probe13/`, including a `git clone --shared` used to dry-run the
cherry-pick and the later merge. No repo, ref or config was changed.

## What these three things are

- **Cursor POC** (`poc/cursor-statusline`, `tools/cursor-status-line-poc.py`,
  1347 lines, plus 52 unit tests). It is one file that reads Cursor's
  `statusLine` stdin payload. It renders three rows that look like Claude's,
  and it fetches included-quota and on-demand data from Cursor's private
  Dashboard Connect-RPC API, with a disk cache.
- **Host-split spec** (`spec/host-split-statusline`, 542 lines, plus a REVIEW
  with R3-1..R3-6 open). It plans to split `status-line.py` into 5 `common_*`
  modules, 4 `claude_*` modules, 4 `cursor_*` modules and 2 entries, in three
  phases: A split, B Cursor host, C multi-host setup and wizard.
- **Claude `status-line.py` at the v1.3 tip** (2618 lines). The 5 gap commits
  `d23749b..52def0f` replace pace-ratio coloring with absolute
  usage-versus-time gap coloring plus a `+`/`-` sign.

**Assumed load:** one developer, with 1 to 3 concurrent agent sessions per
host. Claude renders on every update. Cursor renders on updates debounced at
`updateIntervalMs` (default 300 ms). A new update **kills the render that is
still running** (spec §2, documented in Cursor's bundled `statusline` skill),
and `timeoutMs` defaults to 2000.

**Test runs (read-only):**
- The POC suite: `Ran 52 tests … OK` (0.1 s).
- On the v1.3 tip: `tests.test_status_line tests.test_arch` gives `Ran 326 tests … OK`.
- The same suite after a scratch cherry-pick of the 5 gap commits onto `main`: `Ran 326 … OK`.
- ruff: 6 errors on `status-line.py` (unchanged since research 03) and 10 on the POC plus its test.

---

## 1. Findings, ranked

Numbering runs across all groups. Tags: **[POC]**, **[SPEC]**, **[CLAUDE]**.

### Must fix (before anything Cursor reaches `main`)

1. **[POC] The quota fetch blocks the render, so Cursor's kill-on-update stops it from ever finishing during a turn** (`tools/cursor-status-line-poc.py:532-610`, `:1276`)
   - **What this is:** On a stale cache, every render sends 3 sequential HTTPS POSTs, each with a 0.8 s timeout, before it prints. The cache is written only after all three return, or in the `except` branch.
   - **Problem:** The spike measured a cold fetch at **1921 ms** (`poc tmp/cursor-statusline-poc-FINDINGS.md`, "cold_fetch_wall_ms: 1921"). Cursor kills the running render when the next update arrives, after as little as 300 ms. The kill is a SIGTERM, which ends Python without running `finally` or `except`. So no cache is written, positive or negative.
     - **Concrete case:** During an active agent turn, every update starts a new TLS connection to `api2.cursor.sh`, which is about 3 per second per session, and kills it before any request completes. The quota stays stale or absent until the session goes idle.
     - Even when idle, the worst case of 3 × 0.8 s plus connect is longer than the 2000 ms default `timeoutMs`.
     - The POC only "worked" because the live wiring raised `updateIntervalMs`/`timeoutMs` to 3000/10000 (FINDINGS, "as wired"). The code even says so: `# shortcut: sync sequential fetch; no single-flight; live wire raises interval/timeout` (`:539`).
     - That shortcut's limit is crossed at the expected load, with default Cursor settings.
   - **Fix:** The render reads the cache only. When the data is stale, it takes an `O_EXCL` lock file and spawns one detached refresher: `subprocess.Popen([sys.executable, "-S", entry, "--refresh-quota"], start_new_session=True, stdin/stdout/stderr=DEVNULL)`.
     - The refresher fetches, writes the cache atomically (good result or negative), and unlinks the lock in `finally`.
     - A lock older than about 20 s counts as dead.
     - About 40 lines in all. Section 3 gives the shape.
     - `DEVNULL` is mandatory. A child that inherits stdout keeps Cursor's pipe open.
   - **If we skip it:** Quota numbers lag whole turns, the private API gets hammered, and the status line depends on non-default Cursor settings that setup will not write.

2. **[POC] Old data is shown forever as "(stale)", including after auth expiry and after the billing cycle resets** (`:591-602`, `:524-529`)
   - **What this is:** On any fetch error, the POC merges the last good values into a negative entry and sets `fetched_at = now`.
   - **Problem:** This loses the age of the real data, so staleness has no bound. A 401 or 403 is handled the same way as a network blip, but the spec says auth-expired means hide (§5.3).
     - **Verified with a probe:** I seeded a last-good entry from a cycle that ended 30 days earlier, at 97% used and $12/$20 on-demand. Then I made every fetch return `HTTP Error 401`. At t+0, t+700 s and t+1400 s the POC returned `total 97.0 stale True`, and `fetched_at` age was `0.0` every time.
     - A user whose token expired, or who is offline across the cycle reset, sees last month's 97% and a red on-demand warning.
   - **Fix:** Store `data_fetched_at` (only set on success) apart from `last_attempt_at` and `last_error`.
     - Hide the quota segments when `last_error` is 401/403 or when `now_ms > cycle_end_ms`.
     - Otherwise show the data as stale. This is the `QuotaResult.state` the spec already defines.
   - **If we skip it:** The line shows wrong money numbers with only a dim "(stale)".

3. **[POC] Included % is colored by the old absolute 50/80 ramp, not by the gap rule both the spec and the POC plan require. The gap helpers are dead code** (`:1077-1080`, `:1032-1042`, `:185-192`)
   - **What this is:** `_included_body` colors with `theme.ramps["rate"]`.
   - **Problem:** The plan line 82 says `inc N%` gets "pace-gap color … via `util_gap_color(abs(gap))`", and spec §5.2 says the same. `billing_pace_gap` and `util_gap_color` have tests (`tests/test_cursor_status_line_poc.py:819-831`) but no caller in the render.
     - **Concrete case:** 85% used with 90% of the cycle elapsed. The POC paints RED (≥80). The rule the Claude line now uses (|−5| ≤ 5) paints GREEN. Two status lines on one desk would disagree about what the colors mean.
   - **Fix:** Generalize Claude's `util_rate_gap` (`status-line.py:1492`) into a pure `util_window_gap(pct, start, end, now) -> float | None`. Claude calls it with `start = reset - window_seconds`, and Cursor calls it with the billing cycle.
     - Delete the POC's `billing_pace_gap`, which differs anyway: it clamps where Claude returns None, and Claude's choice is the correct one for a stale cycle.
   - **If we skip it:** A user-visible contradiction, plus two copies of the gap math.

4. **[POC] About 620 of its 1347 lines are copies of `status-line.py`, outside every architecture rule** (whole file)
   - **What this is:** The POC re-implements about 27 helpers that already exist on the v1.3 tip:
     - `util_char_width:1341`, `util_visible_width:1357`, `util_pick_color:1324`, `util_gap_color:1512`, `util_first_fitting:1362`, `util_icon:1388`, `util_trunc_cols:1628`, `util_two_state_cap:1373`, `util_display_dir:1606`;
     - `fmt_tokens/bytes/duration:1201-1240`;
     - `util_branch_from_porcelain:1535`, `util_dirty_mark:1619`, `probe_git_snapshot:831`;
     - the 6 proc/ps readers `:871-925`;
     - `core_safe_build:2130`, `core_crown_slowest:2150`, the packer `core_render:2253`;
     - `seg_path/git_branch/git_dirty/alt_git_worktree/render_time/slowest/context`.

     It has no banner blocks. Its role prefixes are missing or wrong (`build_context`, `fetch_quota`, `load_config`, `_safe_build`, `render_for_test` on the production path). `tests/test_arch.py:374` parses only `status-line.py`.
   - **Problem:** Every fix to width math, packing or git now has to be made twice. The POC's `seg_path` already differs from Claude's: it ignores the git `root_name`.
   - **Fix:** This is what 999.4 exists to do. Promote by extraction, never by merging the branch. The branch also carries all 343 v1.3 commits, because it was cut from the v1.3 tip.
   - **If we skip it:** Two status lines that drift apart.

5. **[CLAUDE] The gap coloring is about to go live without ever being approved** (`docs/superpowers/specs/2026-10-09-statusline-quota-window-gap-design.md:4`, "Status: draft, awaiting user review")
   - **What this is:** The code is correct and tested. I confirmed the 326 tests, and research 01/02 confirmed it too. It reverses Phase 8.1 on purpose: low usage late in a window is now RED. It also shows `-50%` to mean "50% used, burning ahead of the clock".
   - **Problem:** `~/.claude/settings.json` runs the **main checkout** (research 02 §4). So the moment the commits land on `main`, they render on every prompt. That includes the inverted sign, which a reader can take for negative usage. `PROJECT.md:199` ("burn pace … ✓ Good") and the v1.2 REQ still describe the old formula, and the spec header still says draft.
   - **Fix:** The user looks at one rich render and one narrow render and approves the sign meaning. Then, in the same push: flip the spec header to accepted, add one PROJECT.md Key-Decision row ("gap coloring supersedes burn pace, 2026-10-09"), and add a one-line REQ amendment.
   - **If we skip it:** An unreviewed visual change becomes the user's live status line, and planning keeps contradicting the code.

6. **[SPEC] Four of the six open review findings disappear if scope is cut, and the rest have small known fixes. The spec has also not absorbed what the spike learned** (`…-REVIEW.md:17-49`, spec §2, §5.2)
   - **What this is:** R3-1..R3-6 are marked MUST-resolve before execution.
   - **Problem:** The spec's §2 facts are now partly wrong. The real payload (`poc tmp/cursor-payload.json`) has **no `param_summary` and no `max_mode`** (`model = {id: "default", display_name: "Auto"}`), and no `worktree` or `vim`. The spec's own rule (§5.2) says that in this case the "effort" wording must be dropped. The spike also settled these points, which §2 still lists as "inferred":
     - the Connect-JSON request is an empty `{}` body with camelCase responses;
     - period values are in cents and `hardLimit` is in dollars;
     - the cold fetch takes 1921 ms.
   - **Fix:** Section 2 below gives resolutions. Amend §2 and §5.2 with the spike facts, and change the "Base branch" line (spec:11) to `main` once finding 5 lands.
   - **If we skip it:** discuss-phase re-derives facts that already exist, and plans on a wrong payload.

### Should fix

7. **[CLAUDE, shared after the split] `git` runs with no timeout on every render** (`tools/status-line.py:779` rev-parse, `:848` status)
   - **What this is:** The git probe behind three segments.
   - **Problem:** On a stalled mount (NFS, sshfs) or a huge repo, `subprocess.run` waits forever. Each update then leaves another hung Python behind.
     - Once this becomes `common_probe` code, Cursor kills the render at 300 ms anyway, so a slow `git status` blanks every Cursor render.
     - The POC added `timeout=2` (`:653`, `:669`). The Claude original never had one.
   - **Fix:** Add `timeout=1` to both calls and catch `subprocess.TimeoutExpired`, so the git segments hide. Two lines plus one test with a fake slow `git` on `PATH`.
   - **If we skip it:** Process pile-up on one bad directory.

8. **[POC] The reset date is computed in UTC, so the user (UTC−3) sees the wrong day near midnight** (`:1121`)
   - **Problem:** **Verified:** with `TZ=America/Santiago` and a cycle ending at 2026-10-31 23:00 local, the POC prints `↺ 2026-11-01 (1d)`. The FINDINGS even record "reset date/days: PASS (UTC cycle end)".
   - **Fix:** `datetime.fromtimestamp(end_ms / 1000).date()`, which uses local time. Claude's reset suffix is already local.
   - **If we skip it:** An off-by-one day on the reset segment for anyone not on UTC.

9. **[POC] `main()` bypasses `safe_render`, so a bad TOML value crashes the render** (`:1340`, `:306`)
   - **Problem:** **Verified:** `min_rows = "x"` makes `main` raise `ValueError` (traceback, exit 1). Cursor then keeps the previous line silently, so the user sees a frozen bar with no hint. `safe_render` (`:1314`) exists but nothing calls it (0 test or source callers).
   - **Fix:** This goes away with reuse. The common `safe_render` prints the Claude-style "⚠ status-line error — run the doctor" line (`status-line.py:2518-2533`).

10. **[POC/SPEC R3-4] Any `https://` host in `CURSOR_API_ENDPOINT` receives the bearer token** (`:418-422`)
    - **What this is:** The scheme check and the same-host-only redirect handler (`:425-445`, tested at `:431-463`) are correct and needed. urllib does copy `Authorization` across redirects.
    - **Problem:** The endpoint host itself is not checked. **Concrete case:** a project `.envrc` (direnv) sets `CURSOR_API_ENDPOINT=https://collector.example`. The next render, in that directory, sends the user's Cursor token there.
    - **Fix:** Send the token only when `urlparse(base).hostname` is `api2.cursor.sh` or ends with `.cursor.sh`. Otherwise use state `network_error` with the diagnostic "endpoint not allowed". About 2 lines and 1 test.

11. **[POC/SPEC R3-2] The quota normalization is tested only against made-up shapes, and Connect-JSON leaves out zero values** (`:448-514`)
    - **Problem:** In proto3 JSON, non-optional fields equal to 0 or false are **omitted**. **Concrete case:** at the start of a cycle with `totalPercentUsed` unset and `includedSpend` = 0 (so omitted), `total` becomes `None` and the included segment hides instead of showing `0%`.
      - The same rule means a missing `hardLimit` reads as 0, and the POC then says "od off" (`:504-505`). That is a claim, not a hide.
      - The spike confirmed the shapes ("camelCase fields present"), but it saved no response.
    - **Fix:**
      - Re-run the spike's fetch once and save **redacted** responses as `tests/fixtures/cursor_dashboard_*.json`.
      - Then write the mapping rule into the spec: an absent non-optional number means 0, and an absent optional percentage means "derive from spend/limit".
      - Treat a missing `hardLimit` together with a false `noUsageBasedAllowed` as `unavailable` (hide), never `disabled`.
      - Pin each case with a fixture test.

12. **[POC] `fetch_quota` does five jobs in one function** (`:532-610`)
    - **Problem:** Cache-freshness policy, auth read, transport, normalization and persistence are tangled, which is why bugs 1 and 2 live in branch soup. Only `normalize_quota_responses` is pure.
    - **Fix:** This is part of the fix for 1:
      - pure `quota_view(cache_dict, now) -> QuotaResult` plus a `needs_refresh` flag;
      - IO `refresh(env)`: auth, POSTs, `normalize`, atomic write;
      - `spawn_refresh()`: the lock plus `Popen`.

      The render touches only the first.

13. **[CLAUDE] Lint debt and a stale architecture doc, which Phase A will touch line by line anyway**
    - ruff reports 6 on `tools/status-line.py` (`:788` SIM108, E501 at `:798,:859,:2292,:2295,:2297`), and pylint reports 6 (research 03 C3). So `make validate` is red, and spec §7's close-out ("`make validate` green") cannot pass without fixing them.
    - `docs/architecture/status-line-pipeline.md` names 7 functions that do not exist (research 03 finding 13).
    - **Fix:** Phase A fixes the lint as it moves code, and deletes that doc. `test_arch.py`'s banners are the enforced truth.

### Nice to have

14. **[POC] Every render pays a 22 ms `urllib.request` import** (`:16-18`). Measured with `python3 -S -X importtime`: 22256 µs cumulative, about the same as the whole bare interpreter start. With the background refresher, import it inside `refresh()` only. The render path then never loads ssl or http.
15. **[POC] On macOS, the RSS walk can spawn up to 36 `ps` processes per render** (`:800-819`: 12 ancestors × comm + cmdline + ppid). One `ps -o ppid=,rss=,command= -p <pid>` per ancestor cuts that to a third. Linux (/proc) is unaffected.
16. **[POC] `seg_on_demand` hardcodes `"\x1b[1;31m"`** (`:1150`) instead of the theme's bold red. Use `theme.c(...)` like every other segment.
17. **[CLAUDE+POC] Give the parse-compat-only `rate` ramp a real job.** `_RAMP_DEFAULTS["rate"]` (`status-line.py:172`) has had no consumer since the gap commits. The POC's on-demand `$used/$ceiling` coloring uses the same 50/80 ramp (`:1142`), which is the right scale for "closer to the ceiling is hotter". Wire `cursor_on_demand` to it, and the dead default becomes live config.
18. **[POC] The tests print renders to stdout** (the suite shows raw ANSI lines between results). Capture stdout in `test_main_*`.
19. **[POC] `tmp/cli-config.json.bak` (mode 0644) is a full copy of the user's Cursor config**, left in the POC worktree. It is gitignored. Delete it when the worktree is removed. Before that, keep a **redacted** copy of `tmp/cursor-payload.json` as the Phase B payload fixture: strip `session_id`, `transcript_path` and the dirs.

Two smaller items were left out: the `del now` placeholder in `build_context`, and the 6 RUF100 unused-noqa notes.

**Verdict:** The Claude gap commits are ready for `main` once the user approves the sign meaning and the planning is updated (finding 5). The Cursor POC did its job as evidence, but it must not be promoted as code. Fix 1-4 by extraction through the host split, and resolve the spec scope (6) first.

**Lean:**
- The POC: −620 lines through reuse, plus −2 dead helpers.
- The spec: 13 new modules become 6, and two review findings (R3-3, R3-6) drop out.

**Not checked:**
- Real Cursor kill behavior under load. I relied on the documented AbortController and SIGTERM semantics, not a live run.
- macOS.
- Whether Claude Code itself times out a hung status-line command.

---

## 2. Must fix before promotion, versus what can wait

### Before any Cursor code lands on `main`

- **Finding 1:** a cache-only render plus a single-flight detached refresher.
- **Finding 2:** separate the data age from the attempt age, and hide on auth-expired or after the cycle end.
- **Finding 3:** one shared `util_window_gap` for both hosts.
- **Finding 4:** extraction through the split. The POC file is deleted, not merged.
- **Finding 10:** the endpoint host allowlist, because it guards a credential.
- **Finding 11:** redacted real-response fixtures and the absent-equals-zero rule.
- **Spec resolutions for R3-1..R3-6** (finding 6), proposed here at the smallest scope:
  - **R3-1 (wizard multi-host):** keep the owner decision, but **sequence it last**. Split Phase C into:
    - C1: headless `--with-statusline[=claude,cursor]` plus `detect/wire/unwire_statusline(paths, host)`;
    - C2: the wizard's per-host gate and Arrange.

    C2 waits for the context-tools-manager decision (Section 4). Cursor is then usable on `main` after C1.
  - **R3-2 (normalization):** finding 11's rule plus fixtures. The POC's `normalize_quota_responses` is otherwise the right mapping (verified units: cents to dollars for period spend, dollars for `hardLimit`, `>= 2147483647` means unlimited).
  - **R3-3 (external providers versus Claude):** **cut external segments from the Cursor first cut.** Claude's provider input, env and cache namespace then stay byte-identical by construction, and no `segment.host`, `AI_KIT_SEGMENT_HOST` or `external_cache_subdir` is needed. Keep one regression test: a strict provider sees the exact pre-split stdin.
  - **R3-4 (credential transport):** already met by the POC (https-only, same-host redirects, tested), plus finding 10's host allowlist.
  - **R3-5 (create-if-absent):** write the temp file, then `os.link(tmp, dest)`. `FileExistsError` means "leave the existing file alone". Then unlink the temp file. That is 3 lines, shared by both host TOMLs. The **spike half is closed**: the spike is over, and `~/.cursor/cli-config.json` has no `statusLine` key (checked 2026-10-13).
  - **R3-6 (toggles):** **no toggles.** `included_auto`, `included_api` and `reset` are already separate segments in the registry (POC `:74-90`), so `[segments]` *is* the toggle. Defaults: `included_total`, `reset` and `on_demand` on; `included_auto` and `included_api` off, because they are width-hungry and only interesting when Auto and API diverge.

### Can wait (fold into Phase A or B tasks, without blocking promotion)

- Finding 7: the git timeout. Do it in Phase A, since the probe becomes shared.
- Findings 8 and 9: the reset date in local time, and the crash path. Both are fixed by construction in Phase B.
- Finding 12: the refactor shape, which comes with finding 1.
- Finding 13: lint and the stale doc, in Phase A.
- Findings 14-19.

---

## 3. Target architecture: the smallest viable host split

**Principle.** Follow the precedent the repo already has, not a new one. `tools/hooks/` has one host-neutral module (`detect.py`) plus one module per host (`claude_session_start.py`, `cursor_session_start.py`). Inside a module, the banner blocks (`DEFAULTS`/`cfg_`/`probe_`/`fmt_`/`util_`/`core_`/`seg_`/`SHELL`) already separate roles, and `test_arch.py` enforces them. Splitting roles into separate *files* adds import edges and no testability: every function is already importable.

So there are **6 files, not 13**.

- **`tools/common_statusline.py`** holds everything that is host-neutral, from `status-line.py`, with the same banners:
  - **DEFAULTS:** palette, ramps (including `rate`, now used by Cursor's on-demand ramp) and the neutral segment and layout data.
  - **`cfg_`:** TOML, env binding and the cache base. The env prefix comes from `HOST.env_prefix`, so `CC_AI_KIT_*` stays Claude-only.
  - **`probe_`:**
    - terminal size;
    - the git snapshot, with a timeout (finding 7);
    - the generic proc/ps readers;
    - one `probe_ancestor_rss(match: Callable[[str|None, str|None], bool])`. It replaces both `probe_rss_bytes` (Claude, `status-line.py:927`) and the POC's `probe_process_rss_bytes`, which differ only in their matcher.
  - **`fmt_`, `util_`:** including `util_window_gap(pct, start, end, now)`, `util_gap_color` and `util_gap_sign`.
  - **`core_`:**
    - `Context`, with neutral fields plus `host: Any`. Generic code never reads `host`, and an arch rule enforces that;
    - `Theme`;
    - the registry, which merges neutral and host segments and raises at startup on a duplicate id;
    - the packer;
    - `core_render`;
    - `safe_render(host)`.
  - **`seg_`:** the neutral segments (path, git_branch, git_dirty, alt_git_worktree, render_time, slowest, alt_term_dimensions, alt_time_clock, context, and the new `system_memory` if it is wanted on both hosts).
- **`tools/claude_statusline.py`** holds the Claude `HOST`:
  - the payload adapter: cost, lines, durations, `rate_limits`, `claude_dir`;
  - the Claude probes: effort setting, todo, tasks, transcript and compaction, plus the `claude` RSS matcher;
  - the Claude segments.
- **`tools/cursor_statusline.py`** holds the Cursor `HOST`:
  - the payload adapter: `render_width_chars` wins, then the terminal probe;
  - `used_percentage: null` means the segment is absent;
  - the cmdline RSS matcher (`cursor-agent`/`agent`; Node's comm is `MainThread`);
  - the Cursor segments: `cursor_model` (no effort wording, see finding 6), `included_total`, `included_auto`, `included_api`, `reset` and `on_demand`, each with the `≈` inferred marker.
- **`tools/cursor_quota.py`** is the **only** code that touches the network or a credential. It is stdlib only, imports nothing from the hosts, and is reviewed in `/gsd-secure-phase`. It has four parts:
  - `normalize(period, hard, plan) -> dict` is **pure** and fixture-tested.
  - `view(cache: dict | None, now: float) -> QuotaResult` is **pure**: freshness, stale, auth-expired, past-cycle-end and absent states, plus a `needs_refresh` flag.
  - `spawn_refresh(cache_dir, entry)` makes the lock: `os.open(lock, O_CREAT|O_EXCL|O_WRONLY, 0o600)`. On `FileExistsError` it steals the lock only when its mtime is more than 20 s old, and otherwise returns. It then runs `Popen([sys.executable, "-S", entry, "--refresh-quota"], start_new_session=True, stdin/stdout/stderr=DEVNULL, close_fds=True)`. Nothing goes on argv but the flag; the token is never on argv.
  - `refresh(env)` runs in the detached child. It lazy-imports `urllib.request`, reads `accessToken` read-only, checks the endpoint allowlist, and makes 3 POSTs with a 5 s timeout each, because no render budget applies now. It writes `{data, data_fetched_at, last_attempt_at, last_error}` with `mkstemp` and `os.replace` at mode 0600, and unlinks the lock in `finally`.
  - The retry cadence is `FRESH_TTL=120` s after a success and `NEG_TTL=600` s after an error, both measured from `last_attempt_at`.
- **`tools/claude-status-line.py`** and **`tools/cursor-status-line.py`** are 3-line entries: a realpath `sys.path` insert (the hooks precedent), then `common_statusline.safe_render(HOST)`. The Cursor entry also dispatches `--refresh-quota` to `cursor_quota.refresh`.

**`HOST` (a NamedTuple in `common_statusline`)** has 7 fields: `name`, `env_prefix`, `config_filename`, `build_context`, `segments`, `default_segments` and `default_layout`. There is no `external_cache_subdir`, because the Cursor externals were cut (R3-3).

**Dependency rules (added to `test_arch.py`, each with a `TestArchNonVacuity` twin):**
- `common_statusline` imports no `claude_*` or `cursor_*` module.
- `claude_*` and `cursor_*` never import each other.
- `cursor_quota` imports only the stdlib.
- Only the entries, `setup.py`, the wizard and the doctor import a host module.

The banner and role-prefix rules become a loop over the 4 importable modules. `segments_inventory.toml` gains a `host` field.

**Setup:** `setup.py` imports `common_statusline` for the defaults and `_SEG_HEADER_RE`. That deletes the copies at `setup.py:83` and `:616-621`. The doctor drops its `importlib` shim (`statusline-doctor.py:43`).

**What stays as the spec says:** the owner decisions, the `QuotaResult` contract, per-host TOMLs, `AI_KIT_CURSOR_*` env vars, the doctor's `--host` flag, atomic writes, and semantic JSON preservation.

**What this skips:**
- 7 extra role-split modules;
- the Cursor external segments;
- the toggles;
- a synchronous-fetch option. The spike already answered it: 1921 ms is far above the 300 ms kill.

---

## 4. The path to `main`

### State verified today

- `main` (`de7dcbb`) is the v1.3 merge base `de2139c` plus 4 commits, all of them docs and todos.
- v1.3 (`gsd/v1.3-curated-config-v2`, tip `0acbd06`) has 343 commits. Phase 16 is not closed, and Phases 17-22 have not been executed (research 02).
- The 5 gap commits touch only `tools/status-line.py`, `tests/test_status_line.py`, `tools/statusline.toml.sample`, `README.md` and two `docs/superpowers/` files. No other v1.3 commit touches the status-line files.
- `poc/cursor-statusline` and `spec/host-split-statusline` were both cut from the v1.3 tip `2b4b45b`, so merging either branch would drag in all of v1.3.
- **Dry run in a scratch `--shared` clone:**
  - `git cherry-pick d23749b^..52def0f` onto `main` applies cleanly, and the suite runs `Ran 326 tests … OK`.
  - A later merge of v1.3 into that result conflicts **only in `.planning/ROADMAP.md`**: the 999.4 id collision. The status-line files merge cleanly, because the changes are identical.
- The 999.4 collision: on `main` and the spec branch, 999.4 is the host split. On v1.3 (`ROADMAP.md:332`), 999.4 is "Ponytail as a first-class recommended skill set". The ponytail id is referenced nowhere else on v1.3, so renaming it is a one-heading change.
- **Context-tools-manager** (`worktree-context-tools-manager-plan1`):
  - 21 commits, merge base `20f14a3` (2026-07-28), which is **529 commits behind `main`**;
  - `main` has since changed `tools/setup.py` by about 1054 lines and `wizard_app.py` by 105;
  - it rewrites `_build_wizard_context` and `cmd_install`, exactly the seams Phase C changes;
  - v1.3 touches neither file.

### Recommended order

1. **Now, docs only, on `main`:**
   - copy `.planning/specs/2026-10-10-host-split-statusline-design{,-REVIEW}.md` from `spec/host-split-statusline` (a file checkout, not a merge);
   - apply the 999.4 and todo replacement text from Section 5;
   - add a note to the REVIEW that records the resolutions proposed in Section 2.
2. **The user approves the gap rendering** (finding 5). Then **cherry-pick `d23749b^..52def0f` onto `main`**, plus one doc commit: spec status set to accepted, a PROJECT.md decision row, and a REQ amendment line.
   - **Why cherry-pick, not merge:** a merge would bring 338 unrelated, unfinished milestone commits into `main` just to get 5 self-contained ones.
   - The cherry-picked commits become duplicates that git resolves cleanly when v1.3 merges at milestone close (verified).
   - It goes live at once, because the settings run the main checkout.
3. **On the v1.3 branch, renumber the ponytail backlog item 999.4 to 999.5** (one heading). Main's todo, the spec, the REVIEW and the POC plan all already use 999.4 for the host split. The v1.3 merge then has no id fight, just one ROADMAP hunk to keep both.
4. **Decide the context-tools-manager's fate before Phase A** (decision D6 below). Phase A edits `setup.py` and `wizard_app.py` for the rename and imports. C2 rewrites the same wizard-context code the worktree rewrites. Rebasing a 529-commit-stale branch after the split would be worse than doing it before.
5. **Promote 999.4** with `/gsd-review-backlog`, then discuss-phase (folding in this report and the spike facts), then plan-phase, **on a worktree from `main`**. With step 2 done, `main` holds the latest `status-line.py`, so the spec's "Base branch: v1.3" line changes to `main`. Ship in this order:
   - **A:** the split, a byte-identical Claude render, the lint, the git timeout, and deleting the stale doc;
   - **B:** the Cursor host plus `cursor_quota`, with real redacted fixtures;
   - **C1:** headless multi-host wiring. Both status lines are usable on `main` here;
   - **C2:** the wizard multi-host flow.
6. **After B lands:** keep the redacted payload and response fixtures, then remove the POC worktree and branch, including `tmp/cli-config.json.bak`. The spec branch can go once its files are on `main`.
7. **v1.3 merges into `main` at its own milestone close**, independent of 999.4. The only expected conflict is the ROADMAP backlog hunk.

### Decisions the user must make

- **D1:** Approve the gap coloring as final, including that `-` means "ahead of the clock" and that low usage late in a window is RED. If yes, the cherry-pick happens now; if no, revise the spec first.
- **D2:** Cherry-pick the 5 commits to `main` now (recommended), or wait for the full v1.3 merge. Waiting means `main`, which is what the user actually runs, keeps the superseded pace ratio for the rest of v1.3.
- **D3:** Renumber ponytail to 999.5 (recommended; 1 reference), or host-split to 999.5 (about 14 references across main, the spec and the POC).
- **D4:** Module shape: 6 files (recommended), or the spec's 13.
- **D5:** Cut Cursor external segments from the first cut (recommended; closes R3-3), or build host-tagged providers now.
- **D6:** Context-tools-manager: rebase it onto `main` and land it before 999.4 Phase A, or shelve it. Either way, decide before Phase A.
- **D7:** Split Phase C into C1 (headless) and C2 (wizard), so Cursor is usable before the wizard work (recommended).
- **D8:** Cursor defaults: `included_auto` and `included_api` off (recommended), and no toggles (R3-6).
- **D9 (optional, reopens an owner decision):** The hard rename `status-line.py` → `claude-status-line.py` costs 62 references outside `.planning/`, `.claude/` and `docs/`, the §6.2 migration code, and an accepted broken-line window. Keeping `status-line.py` as the Claude entry would delete all of that. The decision is recorded as final. I list the cost only so the user can choose with it in view.

---

## 5. Ready-to-apply replacement text

### 5a. `.planning/ROADMAP.md` §Backlog: replace the whole "Phase 999.4" section (from its `###` heading to the `---` before the next section) with:

```markdown
### Phase 999.4: Host-split status line for Claude Code and Cursor CLI (BACKLOG)

**Goal:** [Captured for future planning] Ship a Cursor CLI status line next to
the Claude Code one, both on `main`, by splitting `tools/status-line.py` into
one host-neutral `common_statusline.py` plus one module per host
(`claude_statusline.py`, `cursor_statusline.py`) and an isolated
`cursor_quota.py` (the only network/credential code), with thin
`claude-status-line.py` / `cursor-status-line.py` entries. The Cursor line
shows model + context, included quota colored by the same usage-vs-time gap
rule as Claude's quota windows, billing-cycle reset, and on-demand spend
against its ceiling. Quota comes from Cursor's undocumented Dashboard API,
always marked inferred (`≈`), fetched by a detached single-flight background
refresher (never inside the render). `setup.py` wires each detected host
headless first; the wizard's per-host flow comes last.

**Depends on (before promotion):**

- The 5 quota-gap commits `d23749b..52def0f` cherry-picked onto `main` after
  the user approves the gap rendering, with the gap spec marked accepted and
  PROJECT.md/REQ amended (research 13 finding 5). After that the base branch
  for this phase is `main`, not `gsd/v1.3-curated-config-v2`.
- A decision on `worktree-context-tools-manager-plan1` (21 commits, 529
  behind `main`, rewrites `_build_wizard_context`/`cmd_install`): rebase and
  land, or shelve, before Phase A.
- v1.3's own backlog item "999.4 Ponytail …" renumbered to 999.5 on the v1.3
  branch, so the milestone merge has no id collision.

**Linked assets:**

- Design spec + review: `.planning/specs/2026-10-10-host-split-statusline-design.md`
  and `…-REVIEW.md` (copied from branch `spec/host-split-statusline`; single
  source of truth once on `main`). Owner decisions in the REVIEW are final.
- Review of POC + spec + Claude tip: session research note
  `13-statusline-review.md` (findings 1–19, proposed R3 resolutions, target
  architecture). Fold its content into this phase's CONTEXT.md.
- External: Cursor `cli-config.json` location and env overrides
  (`CURSOR_CONFIG_DIR`, `XDG_CONFIG_HOME/cursor`):
  <https://cursor.com/docs/cli/reference/configuration>. Claude Code status
  line reference: <https://code.claude.com/docs/en/statusline>. Cursor's
  `statusLine` schema is documented only in the CLI's bundled `statusline`
  skill.

**Spike / POC evidence (branch `poc/cursor-statusline`; evidence only, never merge — it is cut from the v1.3 tip):**

- Real payload captured (cursor-agent 2026.10.01): `model` has only `id` and
  `display_name` (no `param_summary`, no `max_mode`) → drop all "effort"
  wording for Cursor; no `worktree`/`vim`; `render_width_chars` present;
  `used_percentage` is a float.
- Dashboard Connect-JSON: POST `{}` to
  `aiserver.v1.DashboardService/{GetCurrentPeriodUsage,GetHardLimit,GetPlanInfo}`,
  camelCase responses, period spend in cents, `hardLimit` in dollars.
  Cold fetch of all three: 1921 ms — far above Cursor's 300 ms
  kill-on-next-update, so the fetch must be background + single-flight.
- Process RSS must match `cursor-agent`/`agent` via cmdline (Node's `comm` is
  `MainThread`); never report the script's own RSS.
- Live `cli-config.json` wiring was restored; `statusLine` absent as of
  2026-10-13.

**Must fix when extracting (do not port the POC as-is):**

1. Render reads cache only; one detached refresher behind an `O_EXCL` lock
   (`start_new_session=True`, stdio to DEVNULL); lazy `urllib` import.
2. Cache keeps `data_fetched_at` separate from `last_attempt_at`/`last_error`;
   hide on 401/403 and after `cycle_end`; never show old data as merely stale.
3. Included % uses one shared `util_window_gap(pct, start, end, now)` (Claude
   and Cursor), not the old 50/80 ramp.
4. Reuse the ~620 duplicated lines from `common_statusline.py`; full banner +
   role-prefix compliance under `tests/test_arch.py`.
5. `CURSOR_API_ENDPOINT` host allowlist (`*.cursor.sh`), https-only,
   same-host redirects (already in the POC).
6. Redacted real Dashboard responses as fixtures; absent non-optional
   Connect-JSON numbers mean 0.

**Proposed R3 resolutions (confirm in discuss-phase):** R3-1 wizard last
(Phase C2); R3-2 fixtures + absent=0 rule; R3-3 no Cursor external segments
in the first cut; R3-4 as item 5; R3-5 `os.link` create-if-absent (spike half
closed); R3-6 no toggles — segments are the toggles, `included_auto`/`api`
off by default.

**Phases (each shippable):** A split (byte-identical Claude render, ruff/pylint
debt cleared, `git` timeout, delete stale
`docs/architecture/status-line-pipeline.md`) → B Cursor host + quota →
C1 headless `--with-statusline[=claude,cursor]` + per-host
detect/wire/unwire → C2 wizard per-host gate + Arrange.

**Requirements:** TBD
**Plans:** 0 plans

Plans:

- [ ] TBD (promote with /gsd-review-backlog when ready)
```

### 5b. `.planning/todos/pending/2026-10-12-promote-cursor-statusline-poc-into-999-4.md`: full replacement

```markdown
---
created: 2026-10-12T12:50:00.000Z
updated: 2026-10-13T00:00:00.000Z
title: Promote Cursor statusline POC spike into Phase 999.4 discuss/plan
area: statusline
severity: major
files:
  - .planning/ROADMAP.md
  - .planning/specs/2026-10-10-host-split-statusline-design.md
  - .planning/specs/2026-10-10-host-split-statusline-design-REVIEW.md
  - tools/status-line.py
  - .claude/worktrees/poc-cursor-statusline/
  - .claude/worktrees/context-tools-manager-plan1/
---

## Problem

Both status lines must end up on `main`. Today `main` ships only the Claude
`tools/status-line.py`, and not even its latest version: the 5 quota-gap
commits `d23749b..52def0f` live only on `gsd/v1.3-curated-config-v2`, while
`~/.claude/settings.json` runs the main checkout. The Cursor line exists only
as a throwaway POC (`poc/cursor-statusline`) that proved the payload, the
Dashboard quota RPC, layout and RSS matching, but cannot be promoted as code:
it blocks the render on a 1.9 s fetch that Cursor kills after 300 ms, shows
old quota forever as "stale", colors included % with the wrong rule, and
duplicates ~620 lines of `status-line.py` outside the architecture tests
(research 13, findings 1–4).

## Solution

1. Docs on `main`: copy the host-split spec + REVIEW from
   `spec/host-split-statusline` into `.planning/specs/`; amend spec §2/§5.2
   with the spike facts (no `param_summary`/`max_mode` → no "effort" wording;
   Connect-JSON `{}` body, camelCase, cents vs dollars; 1921 ms cold fetch);
   set its base branch to `main`.
2. After the user approves the gap rendering: cherry-pick `d23749b^..52def0f`
   onto `main` (dry-run verified clean, 326 tests OK) plus one doc commit (gap
   spec → accepted, PROJECT.md decision row, REQ amendment).
3. On the v1.3 branch, renumber its "999.4 Ponytail …" backlog item to 999.5.
4. Decide `worktree-context-tools-manager-plan1` (rebase+land or shelve)
   before Phase A — it rewrites the same `setup.py`/`wizard_app.py` seams.
5. `/gsd-review-backlog` → `/gsd-discuss-phase 999.4` (fold research 13 and
   the proposed R3-1..R3-6 resolutions into CONTEXT.md) → `/gsd-plan-phase`,
   on a worktree from `main`. Ship A split → B Cursor host → C1 headless
   wiring → C2 wizard.
6. Before deleting the POC worktree: keep a redacted `cursor-payload.json`
   and redacted Dashboard responses as test fixtures; delete
   `tmp/cli-config.json.bak`.

Do **not** merge `poc/cursor-statusline` or `spec/host-split-statusline`:
both are cut from the v1.3 tip and would drag 343 commits into `main`.
Keep `~/.cursor/cli-config.json` `statusLine` unset until C1 ships.

## Acceptance

- [ ] Gap coloring approved and on `main`; gap spec no longer "draft";
      PROJECT.md/REQ record that it supersedes burn pace
- [ ] Spec + REVIEW on `main` `.planning/specs/`, amended with spike facts
- [ ] Backlog id collision resolved (ponytail → 999.5 on v1.3)
- [ ] Context-tools-manager worktree decided before Phase A starts
- [ ] 999.4 promoted with plans that cite the spec, REVIEW and research 13,
      and record a decision for each R3-1..R3-6
- [ ] Phase B quota code: cache-only render, single-flight background
      refresh, auth-expired/past-cycle hide, endpoint allowlist, fixture
      tests from real redacted responses
- [ ] Both `claude-status-line.py` and `cursor-status-line.py` on `main`,
      `make test` and `make validate` green, Cursor wired via
      `--with-statusline=cursor`
- [ ] No lingering live wire of `cursor-status-line-poc.py`; POC worktree
      removed after fixtures are kept (`statusLine` absent as of 2026-10-13)
```
