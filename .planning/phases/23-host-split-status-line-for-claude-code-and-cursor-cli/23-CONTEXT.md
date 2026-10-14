# Phase 23: Host-split status line for Claude Code and Cursor CLI - Context

**Gathered:** 2026-10-14 (assumptions mode, `--analyze --all --batch`, jev screening, best over easy)
**Status:** Ready for planning (Parts A and C wait on the plan1 decision; Part B waits on the R5 spike)

<domain>
## Phase Boundary

Split `tools/status-line.py` into host-neutral and per-host modules with a byte-identical Claude
render (Part A), ship a Cursor CLI status line with the shared 5/10/15 gauge and inferred
Dashboard quota (Part B), and make setup and the wizard multi-host (Part C). The WHAT is locked
in `23-SPEC.md` (R1–R12, amended 2026-10-14). This file locks the HOW, including the reviewed
design's open findings R3-1..R3-6.
</domain>

<decisions>
## Implementation Decisions

### Part A — audit, layout, oracle
- **D-01: The audit table has 182 rows:** 134 functions, 7 classes and 41 module-level
  assignments, with the 141 def/class rows as a subtotal (SPEC R1 amended).
  - Columns: name, kind, target module, host-neutral y/n, reason, fate (reused, generalized,
    deleted, split). Machine-readable, enumerated by `ast` on the base commit's blob; a script
    fails when the row count differs from the AST count.
  - Two passes: a reviewed reason per row, plus a call-graph taint cross-check (29 direct seeds,
    9 by propagation). A row disagreeing with the taint result carries a written explanation.
    The token grep misses data-source taint (`probe_transcript_bytes`, `util_iter_tool_uses`,
    `util_pick_from_tasks`) and over-flags `cfg_load_config*` (only the `CC_AI_KIT_` literals),
    whose fate is "generalized".
  - The same file is the test-migration rewrite map and a post-split conformance check (every
    non-deleted row exists in its target module).
  - **Laya overridden** (defs_only 0.81): the assignments carry the real host decisions
    (`SEGMENTS`, `LAYOUT`, `PINNED`, `_EFFORT_DEFAULTS`, the mixed `_RAMP_DEFAULTS`), and
    `tests/test_arch.py:133` already counts assignments. TypeSafe second opinion
    with_assignments 0.75.
- **D-02: The layout follows the owner-reviewed role split** (`.planning/specs/
  2026-10-10-host-split-statusline-design.md` §4): `common_config/fmt/probe/render/segments`,
  `claude_payload/probes/segments/host`, `cursor_payload/quota/segments/host`, thin entries,
  plus one types/defaults leaf. The ROADMAP's four names are shorthand (amended).
  - The one upward edge, `cfg_load_config_verbose` → `core_discover_external`, moves external
    discovery to the config side. Config functions take primitives (prefix, defaults, filename),
    not `HOST`, which breaks the design's `common_render`/`common_config` cycle.
  - Annotation-only references (`Theme`, `Context`) use `TYPE_CHECKING` imports.
  - The `globals()` registry (`core_discover_builders`, the `BUILDERS` snapshot,
    `core_safe_build`/`core_builders_for` defaults) becomes discovery over named modules with a
    duplicate-id startup error.
  - **Own reasoning** (Laya role_split 0.47 fb, TypeSafe hybrid 0.62 fb): the owner decision
    fixes `claude_host.py`/`cursor_host.py`, and role modules make import direction
    machine-checkable — the repo's first real layering rule (999.3). Ledger.
- **D-03: `Context` keeps only neutral fields plus a typed `ctx.host`.**
  - Neutral: `work_dir`, `home`, `clock`, `cols`, `lines`, `dim_assumed`, `t_start`,
    `model_name`, `model_id`, `context_pct`, `context_max`. The context fields are `int | None`:
    Claude's payload builder keeps the `or 0` coalescing (`:1826-1827`), Cursor passes `None`.
  - `HOST` gains `pinned`, `right_margin`, a doctor-command suffix (Claude stays exactly
    `--doctor`), the env prefix and the three provider-namespace fields (D-18).
  - Cursor's `render_width_chars` is already `columns - 4` (bundle), so Claude's `RIGHT_MARGIN`
    is not applied again; the spike confirms the Cursor margin. Design §5.1 is amended.
  - `setup.py` imports host modules lazily (uninstall must not depend on renderer import health).
  - The `_data()` fixture helper (`tests/test_status_line.py:55-99`) changes with it.
- **D-04: Arch rules and references.**
  - Rule 1 becomes "only `*_host.py` contains a host env-prefix literal".
  - New rules, each with a `TestArchNonVacuity` twin: common never imports a host; claude and
    cursor never import each other; only entries, setup, wizard and doctor import `*_host`;
    segment ids are unique; `cursor_quota` imports networking only inside functions
    (`import urllib.request` costs 18 ms against a 41.5 ms p50 render).
  - The R3 reference check is the anchored `rg -P '(?<![\w-])(status-line\.py|statusline\.toml)'`
    with a history allowlist (SPEC R3 amended). References to update: `AGENTS.md:29,90`,
    `pyproject.toml:88,94`, `Makefile:70`, `.pre-commit-config.yaml:27,50,56`, README (11),
    `tools/install.sh:183`, `tests/test_install.sh:47`, `tools/statusline-doctor.py:36-51`, the
    `setup.py:83-110` defaults and their drift tests.
  - `docs/architecture/status-line-pipeline.md` is deleted; the dependency diagram lives in
    module docstrings plus the arch rules.
  - `tools/segments_inventory.toml` gains a per-host `line` (mirrored by `TestSegmentInventory`).
- **D-05: Oracle first, then a pure move.**
  - A pre-split commit adds golden renders with every segment on (payloads with `rate_limits`,
    `cost`, `effort`, `todo`, `lines`), an entry-level subprocess render, and a strict-provider
    capture (stdin bytes, env keys, cache path) for R10.
  - The split is a pure move. Behavior changes (gauge generalization, `HOST.env_prefix`, git
    timeouts, the bad-TOML fix) ride in later commits.
  - "No assertion changed" is checked mechanically after rewriting `sl.X` qualifiers via the
    audit map: only loaders, fixture helpers and `mock.patch.object` targets may differ. No
    compatibility facade (patching it would patch the wrong module).
  - Laya oracle_then_move 0.68 (fb), TypeSafe 0.99.

### Part B — gauge, quota, Cursor segments
- **D-06: One shared `context` segment over a nullable percent,** hidden when Cursor sends null;
  `model` and `path` are one common implementation each. Laya cursor_folded 0.53 (fb),
  TypeSafe shared_nullable 0.99.
- **D-07: The gauge splits into a pure `util_window_gap(pct, start, end, now) -> float | None`**
  and a Claude adapter (`start = reset - util_rate_window_seconds(key)`). `util_gap_color` and
  `util_gap_sign` are unchanged. Elapsed outside [0, 100] stays `None` (white, no sign); the
  POC's clamping is dropped. The sign stays gated to the wide tier on both hosts.
- **D-08: Four Cursor segments, no scalar toggles** (R3-6): `cursor_included`
  (`total_percent_used`), `cursor_api` (`api_percent_used`), `cursor_extra` (used/ceiling
  against cycle elapsed), and a separate `cursor_reset` in local time. Included, extra and reset
  default on; **API defaults off**. No auto-only segment. Extra kinds: `fixed` shows
  `$used/$ceiling` with the gauge, `unlimited` shows `$used` with no ramp, `disabled` is dim,
  `unavailable` is hidden. All carry `≈`; stale data carries a stale marker. Design §5.2's
  on-demand ramp is superseded by the ROADMAP gauge. Laya four_api_off 0.45 (fb), TypeSafe 0.95.
- **D-09: Each segment declares its own window** (SPEC R4 amended): included and API use the
  included-usage period (MONTHLY or UNSPECIFIED → billing cycle; WEEKLY →
  `(included_usage_resets_at - 7d, included_usage_resets_at)`), extra uses the billing cycle,
  and an underivable window renders neutral. Inferred from bundle descriptors; the spike records
  the real `included_usage_period`. Laya billing_cycle_all 0.63 (fb), TypeSafe 0.91.
- **D-10: Normalization follows the shipped client's `/usage` logic** (R3-2,
  `./src/usage/usage-data.ts` in the bundle), validated by spike fixtures, with recorded
  deviations.
  - Spend fields are int32 cents; `hard_limit` is dollars and `>= 2147483647` means unlimited;
    `billing_cycle_*` are epoch ms, possibly strings. Accept int, float or numeric string;
    reject bool, NaN and negatives (the POC turns `True` into 1.0).
  - Proto3 absence means 0 only for non-optional fields; `*_percent_used` are optional.
  - On-demand kind as first-party `u()`, including `limit_type == "team"`
    (`individual_limit`, then hard limit, then `pooled_limit > 0`). A failed or absent
    `GetHardLimit` is `unavailable`, never `disabled`.
  - `GetCurrentPeriodUsage` is required; `GetHardLimit`/`GetPlanInfo` failures hide only extra
    and the window metadata. The three calls run concurrently, each with its own timeout.
- **D-11: A missing percent is derived from spend/limit when both exist and limit > 0;
  otherwise the segment hides** — never the client's `?? 0`. **Own reasoning** (Laya
  show_zero 0.48 fb, TypeSafe derive_else_hide 0.49 fb): showing 0% claims more certainty than
  the data has (core value). Ledger.
- **D-12: The POC is reference only.** Shape reused: `_pick` camel/snake lookup, the atomic 0600
  token-free cache write, the `≈ (stale)` suffix. Not carried: the blocking `fetch_quota`, the
  scheme-only endpoint check, `resolve_auth_path`, the UTC reset and 50/80 ramp, `main()`
  bypassing `safe_render`. Keep a redacted copy of the POC's real payload before the POC
  worktree is deleted, and delete its `tmp/cli-config.json.bak` (0644, contains `authInfo`).

### Part B — fetch, spike, credentials, cache
- **D-13: Working presumption: cache-only render plus a single-flight detached refresher**
  (`python3 -S cursor_quota.py --refresh`, `start_new_session=True`, `close_fds=True`, stdio on
  DEVNULL). The CLI debounces runs (≥ 300 ms), aborts the previous child on each new run and
  waits for its `close` event, so a refresher holding the pipe would block the line. The spike's
  p50/p95 confirms or overturns this; an inline fetch needs the `shortcut:` comment and the
  kill-by-next-update test. Non-default `updateIntervalMs`/`timeoutMs` are rejected. Laya
  raise_knobs 0.48 (fb), TypeSafe cache_plus_refresher 0.94.
- **D-14: The spike captures the payload under a scratch `CURSOR_CONFIG_DIR`** holding a copy of
  `cli-config.json` plus `statusLine` (SPEC R5 amended). `auth.json` resolves independently, so
  the agent stays logged in. Fallback if that fails: a 0600 backup outside the repo, a key-level
  atomic revert of `statusLine` only, then delete the backup. Approval is still needed (real
  token, quota). **Laya overridden** (edit_real_file 0.72): the CLI rewrites the file during
  use. TypeSafe second opinion scratch_config_dir 0.98.
- **D-15: Transport and credentials** (R3-4).
  - A pure `validate_endpoint()`: https only, `urllib.parse` hostname lowercased, no userinfo,
    port 443, hostname `cursor.sh` or ending in `.cursor.sh`, validated before the token read.
  - **Every redirect is refused** (`redirect_request` returns `None`) and reported as a network
    error. Live experiment: stock urllib forwards `Authorization` cross-origin on 301/302 and
    turns the POST into a bodiless GET. SPEC edge row amended. Laya refuse_all 0.50 (fb),
    TypeSafe 0.72.
  - The auth path mirrors the CLI's `getAuthFilePath`: Linux
    `${XDG_CONFIG_HOME:-~/.config}/cursor/auth.json`, darwin `~/.cursor/auth.json`, independent
    of `CURSOR_CONFIG_DIR`. Read-only; a parse error is a transient `network_error`; 401/403 is
    `auth_expired`. The token never appears on argv, in env, logs or the cache. Default TLS
    verification.
  - Test seams: unit tests for the validator, a loopback fake server for the redirect handler,
    an injectable `urlopen`.
- **D-16: Cache and states** (R9): `<cache_base>/cursor/usage.json`, 0600, mkstemp +
  `os.replace`, holding `{data, data_fetched_at, last_attempt_at, last_error, last_error_kind}`.
  `QuotaResult.state` is a pure function of (cache, now): fresh 120 s, then stale; hidden on
  401/403 or past `cycle_end`; a network error shows the last good data as stale; negative TTL
  600 s from `last_attempt_at`. The lock is `O_EXCL` with pid and start time, expiring after
  the hard timeout plus a margin.
- **D-17: Shared-shell robustness fixes, post-split commits.** `probe_git_worktree_info`
  (`:760`) and `probe_git_snapshot` (`:831`) get a `timeout` and catch `TimeoutExpired` (test:
  a fake slow `git` on `PATH`). `cfg_load_config` moves inside `safe_render`'s try, so a bad
  TOML (`min_rows = "x"` raises at `:503` today, on Claude too) renders an error segment on
  both hosts.

### Part B/C — providers, config files, Cursor dir
- **D-18: Cursor external providers get their own namespace** (R3-3): default dir
  `~/.config/ai-kit/segments-cursor`, env `AI_KIT_CURSOR_SEGMENT_*`, cache `segments-cursor`.
  Claude's payload, env and cache are untouched. The wizard's `discover_external_segments`
  becomes per host; `examples/segments/system_memory` is offered to both. Tests: the pre-split
  strict-provider capture compared post-split, and Claude never scans the Cursor dir. Laya
  separate_namespace 0.34 (fb), TypeSafe 0.88.
- **D-19: One create-if-absent helper** (R3-5): mkstemp in the destination dir, write and fsync,
  `os.link(tmp, dest)`, unlink tmp; `FileExistsError` leaves the winner; any other `OSError`
  falls back to `O_CREAT|O_EXCL` with unlink on failure. Used by `copy_recipe_if_absent`
  (`setup.py:1760-1773`), `_recover_incompatible_config` (`:2237-2240`) and the
  `statusline.toml` → `claude-statusline.toml` migration (link + unlink; both present warns).
  `write_toml_preserving` stays `os.replace` and takes the host's doctor invocation and prefix.
  Experiment: 16 concurrent processes, exactly 1 winner, no leftover tmp files.
- **D-20: Config env is host-derived.** Cursor uses `AI_KIT_CURSOR_CONFIG_FILE`,
  `…_SEGMENT_<KEY>`, `…_GIT_CACHE_TTL`, `…_EXTERNAL_DIR`, `…_EXTERNAL_CACHE_TTL`; the hard-coded
  `CC_AI_KIT_*` in `setup.py:256,269,476` and the doctor's `_ENV_HELP` come from `HOST`.
- **D-21: A separate `Paths.cursor_config_dir`** (and `cursor_cli_config`), resolved like the CLI:
  non-blank `CURSOR_CONFIG_DIR`, then non-blank `$XDG_CONFIG_HOME/cursor`, then `~/.cursor`
  (no platform gate in the bundle). `cursor_dir` (hooks) is left alone; the hooks mismatch is
  backlog 999.2. `config_doctor_checks.py:68-93` already implements the resolver. **Laya
  overridden** (fix_both 0.97): hooks are outside this phase and fixing them changes Phase 21's
  gate; the feasibility check is recorded in 999.2. TypeSafe second opinion separate_resolver
  0.99.

### Part C — setup and wizard
- **D-22: One wizard app with a host-keyed seam** (R3-1). `WizardContext` gains
  `hosts: tuple[HostView, ...]` (detected hosts, Claude then Cursor), each with id, label,
  config and wiring strings, `state`, a live `status_line()`, `segment_meta`,
  `external_segments`, `sample_json` and an engine. Flow: Choose → gate + Arrange per host →
  one Review listing per-host writes → Done. `WizardResult.state` becomes `{host: state}`;
  `commit(selection, states)` returns the component outcome plus per-host `{ok, adopt, log}`.
  One host's doctor rejection never blocks the other; a declined host is untouched.
  Hard-coded Claude strings (`wizard_app.py:598-606,640`) become host-labelled; `wizard_app`
  imports nothing from `setup.py` or host modules. A two-host PTY test is required. Laya
  headless_only 0.51 (fb, ruled out by the owner), TypeSafe host_keyed_one_app 0.95.
- **D-23: Per-host detect/wire/unwire share the unset/ours/foreign classification and the atomic
  primitives** (`_read_json_checked`, `_atomic_write_json`).
  - Cursor shape: an object with `type == "command"` and a non-empty string `command` (bundle
    schema; optional `padding`, `updateIntervalMs`, `timeoutMs`). A bare string is invalid for
    Cursor; any other shape is refused. No extra keys; an "ours" refresh preserves sibling
    timing keys; no non-default knobs are written.
  - The command is argv-split by the CLI (`string-argv`, `shell:false`): no shell features, and
    an install path with spaces is quoted.
  - Write ordering: re-read and re-classify immediately before the atomic replace (the CLI
    rewrites the file).
  - Headless `--with-statusline` becomes `nargs="?"`; the bare flag wires every detected host
    (a behavior change called out in the README); an unknown or undetected name errors before
    any write; Claude is wired before Cursor; a foreign entry is never overwritten headless.
  - `cmd_uninstall` becomes per host; the doctor gets `--host` (default claude).
- **D-24: The wizard preview runs the real Cursor entry against a synthetic fresh quota cache in
  a temporary `XDG_CACHE_HOME`** — no network, no token, segments show `≈`. `cursor_quota`
  exposes the cache schema (e.g. `synthetic_cache()`) without importing networking. A Cursor
  sample payload sits beside the Claude one. **Own reasoning** (Laya static_samples 0.35 fb,
  TypeSafe static_samples 0.66 fb): static samples cannot show the gauge colors the feature
  exists for, and the env-only cache is not a production test hook. Ledger.

### Claude's Discretion
- File names of the audit table and scripts; the exact `HostView` field names; refresher lock
  margin; the stale-marker glyph.
</decisions>

<canonical_refs>
## Canonical References

- `.planning/phases/23-host-split-status-line-for-claude-code-and-cursor-cli/23-SPEC.md` (amended R1, R3, R4, R5, R8 edge)
- `.planning/specs/2026-10-10-host-split-statusline-design.md` and `-REVIEW.md` (R3-1..R3-6 resolved here: R3-1 D-22, R3-2 D-10, R3-3 D-18, R3-4 D-15, R3-5 D-19, R3-6 D-08)
- `.planning/research/2026-10-13-audit/13-statusline-review.md`, `13b-statusline-proposal-corrected.md`
- `tools/status-line.py` (`:72-123` registry/layout, `:503`, `:565-615`, `:760`, `:831`, `:1493-1533`, `:1677-1715`, `:1826-1833`, `:1943-2140`, `:2056-2078`, `:2499-2546`)
- `tools/setup.py` (`:51-110`, `:232-283`, `:455-513`, `:734-748`, `:1409-1454`, `:1627`, `:1760-1773`, `:2237-2240`, `:2413-2560`, `:2752-2769`, `:2913-2927`, `:3122`), `tools/wizard_app.py:39,101-126,208,236,598-640`
- `tests/test_arch.py:46,133,197,377-381,590-640`, `tests/test_status_line.py:55-99,2737-2753`, `tests/fixtures/golden/inputs.json`
- Cursor bundle 2026.10.01 (read-only): `./src/hooks/use-status-line.ts`, `./src/usage/usage-data.ts`, `../cursor-config/dist/paths.js`, `190.index.js` (hooks path)
</canonical_refs>

<code_context>
## Existing Code Insights

- `tools/hooks/detect.py` + `claude_session_start.py`/`cursor_session_start.py` is the per-host-files precedent.
- `config_doctor_checks.py:68-93` already resolves Cursor's `cli-config.json` three-step precedence.
- `tests/wizard_fixtures.py:34` is `WizardContext`'s single test construction site.
- `render_preview` (`setup.py:232-283`) shells the real script with sample JSON; `_sample_input_path` (`:2293`) reads a test fixture at runtime.
</code_context>

<specifics>
## Specific Ideas

- **Precondition owned by uz:** land or shelve `worktree-context-tools-manager-plan1`. It rewrites the same `setup.py`/`wizard_app.py` seams, and Part A's migration code edits `setup.py` too, so it blocks Part A and Part C planning.
- Spike-only facts (R5): the real payload on a parameterized model (`param_summary` stays conditional); real Dashboard responses (optional fields on Pro, `total_percent_used` vs auto/API, `included_usage_period`, `on_demand_spend_disabled_by_organization`, units); concurrent vs sequential p50/p95 and cadence during streaming; whether a `/dev/tty` size probe works under the CLI's piped spawn and the right Cursor margin; token lifetime and whether the CLI rewrites `auth.json` while a refresher reads it.
- Re-check the `statusLine` schema, update/kill semantics and config-dir resolver against current Cursor docs at spike time (the docs say the XDG leg is Linux/BSD only; the bundle has no gate).
- `os.link` fallback on FAT and some FUSE/NFS is covered by failure injection.
</specifics>

<deferred>
## Deferred Ideas

- The Cursor hooks path mismatch: backlog 999.2.
- An auto-only Cursor segment and the design's scalar toggles (D-08).
</deferred>

---

*Phase: 23-host-split-status-line-for-claude-code-and-cursor-cli*
*Context gathered: 2026-10-14*
