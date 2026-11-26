# Phase 40: Resilient review sized by jev - Research

**Researched:** 2026-11-25
**Domain:** `skills/ai-kit-spec-review/` (stdlib Python package `ai_kit_spec`, markdown skill, `cross-ai.mjs` runner), jev advisory client, skill-judge loop
**Confidence:** HIGH for in-repo facts (all read at HEAD this session); MEDIUM for the proposed trigger rules and names (design proposals, `[ASSUMED]`)

<user_constraints>
## User Constraints (from CONTEXT.md and SPEC.md)

SPEC R1-R8 and CONTEXT D-01..D-10 are locked (not repeated here; read `40-SPEC.md` and `40-CONTEXT.md`). Claude's discretion: module and
function names, the review-level reason names, the exact deterministic trigger rules, the per-ping timeout default (configurable, with a
test seam). Deferred (out of scope): switching an unflagged lane on transient, bad_model or crash classes; execute-side switching
(Phases 41, 42). Everything about the blocked-until record and the free-lane pool is **PROVISIONAL (needs owner confirmation)**.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| REV-01 | Flagged lane switches at once on quota; blocked pool skipped | Q1, Q2: `lane_fallback`, `--blocked-status`, `--pool` gap in `RunnerSpec` |
| REV-02 | jev classifies reviewer-fixer disagreements | Q7: `ask_items`, sentinel precedent |
| REV-06 | jev sizes review on top of deterministic signals | Q7, Q8 |
| REV-07 | Ping per round, closed reason list, partial report | Q3, Q4, Q5, Q6 |
| REV-08 | Superpowers plan without fold step gets HIGH finding | Q9 |
| JDG-04 | Changed SKILL.md meets judge bar | Q10, Q12 |
</phase_requirements>

## Summary

The review loop is driven by the host agent reading `skills/ai-kit-spec-review/SKILL.md` and calling `ai-kit-spec.py` subcommands. Today
Step 0.7 runs `probe-quota` then `resolve-reviewers` (writes `$RUN_TMP_DIR/reviewers.json`), Step 1 dispatches each entry (native via
the host agent tool, subprocess via `dispatch-reviewer`), Step 1.5 runs `merge-reports`, and Step 5 is **prose in SKILL.md** (the
"Approved" wording is not produced by code). **Confirmed:** every new behaviour (ping, flagged switch, round log, partial report, jev
classify, jev size, fold check) must be a new CLI subcommand reachable from SKILL.md steps, because the host agent cannot call Python
functions. New subcommands go into **new modules** that export `register_parsers(sub)` and `COMMANDS` (precedent: `skill_classify.py`),
not into `cli.py` (1481 lines). [VERIFIED: skills/ai-kit-spec-review/ai_kit_spec/cli.py:499-512,1432-1463]

Three corrections to the SPEC/CONTEXT live facts: (1) `evals.json` holds **15** evals, not 14 (REJUDGE.md also says 15 evals);
(2) **`merge-reports` currently fails the whole merge when any lane fails** (`cli.py:992-997`: prints `### Status: Failure — <lanes>`
and exits 1), and four tests pin it (`tests/test_ai_kit_spec.py:3660-3715`, `4452-4478`) — R4 "one lane's failure never cancels
another lane's result" therefore **changes existing behaviour and existing tests**, it is not additive; (3) the Python dispatch never
passes `--pool`: `RunnerSpec` has no `pool` field (`runner_dispatch.py:69-89`, `_SETTING_FLAGS` at 210-217), so D-04's pool pass-through
needs a `RunnerSpec` field plus a flag row.

**Primary recommendation:** build five small stdlib modules (lane ping, lane switch, round log + partial report, jev adapters, fold
check) each with a `register_parsers`/`COMMANDS` pair, extend `REASONS` with four keys (`replaced`, `never_resolved`, `no_lane_left`,
`ping_timeout`), add `pool` to `RunnerSpec`, relax `merge-reports` to merge the surviving lanes with a partial marker, and put the
documented reason table in a new `references/lane-failure.md` that a lock test compares to `REASONS`.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Ping, switch, sizing, classify, fold check, partial report logic | Python CLI (`ai_kit_spec` modules) | SKILL.md steps call them | Deterministic and fake-lane testable; host agent only orchestrates |
| Blocked-until record read | Runner (`cross-ai.mjs --blocked-status`) | Python wrapper (spawn, parse one line) | The runner owns the validated reader and writer; a Python re-parse would be a second reader |
| Review log (per-round lane records) | `$RUN_TMP_DIR` JSON file written by CLI | SKILL.md Step 5 reads it | No log exists today (only the optional `loop.log`, SKILL.md:204) |
| Reason list | `error_classifier.REASONS` | `references/lane-failure.md` documents it; lock test compares | One list, D-01 |
| jev calls | `jev_names.ask_items` (existing client) | New adapter module | Never a new backend (SPEC out of scope) |

## Standard Stack

### Core (all in-repo, stdlib only)
| Component | Location | Purpose |
|-----------|----------|---------|
| `probe_reviewer_quota`, `ProbeSeams` | `ai_kit_spec/quota.py:208-287` | the ping |
| `lane_usage_limit`, `lane_fallback`, `selectable_lanes` | `ai_kit_spec/lane_settings.py:103,150,139` | flag reader, fallback rule |
| `jev_names.ask_items`, `find_jev` | `ai_kit_spec/jev_names.py:140,63` | jev call, presence |
| `run_in_own_group` / `bounded_run` | `ai_kit_spec/detection.py:955,980` | spawn the runner status read without a new `start_new_session` literal |
| `concurrent.futures.ThreadPoolExecutor` | stdlib; precedents `tools/run_unittest_parallel.py:84,935`, `tools/cursor_quota.py:624-657` | concurrent pings |

No external package is installed by this phase, so there is no Package Legitimacy Audit (nothing to verify). [VERIFIED: no new dependency in SPEC Constraints]

## Q1. Blocked-until record: runner flags, locations, Python call shape (PROVISIONAL)

- **Flag grammar.** `--pool <p>` is validated by `BLOCKED_POOL_RE` and a bad value throws `--pool must look like <provider>:free`:
  `cross-ai.mjs:6721`. The regex, verbatim: `const BLOCKED_POOL_RE = /^[A-Za-z0-9._-]{1,64}:[a-z]{1,16}$/;`
  (`cross-ai.mjs:4043`). It equals `lane_settings.POOL_RX` (`lane_settings.py:16`: `POOL_RX = re.compile(r"[A-Za-z0-9._-]{1,64}:[a-z]{1,16}")`),
  pinned by `tests/test_runner_describe.py:239-245`. A lane's stored `pool` value is already the full key (`_problems`, `lane_settings.py:52-54`:
  "'pool' must look like '<provider>:free'"), so pass `lane["pool"]` verbatim. [VERIFIED]
- **`--blocked-status <pool>` output and exits.** `main` prints exactly one stdout line and exits 0
  (`cross-ai.mjs:7000`: `process.stdout.write(\`${blockedStatusLine(o.blockedStatus)}\n\`)` then `reportAndFinish('ok', ... exit: 0 ...)`),
  and the runner also prints its own `AIKIT-XAI status=ok ...` trailer on **stderr**. Line format (`cross-ai.mjs:4140-4143`):
  `blocked_until=${rec ? blockedIso(rec.untilS) : '-'} failures=${rec ? rec.failures : 0}` where the time is `YYYY-MM-DDTHH:MM:SSZ`.
  A missing OR malformed record (bad JSON, wrong pool, bad time, failures < 1, unknown basis, > 4096 bytes, not a regular file) reads
  `blocked_until=- failures=0` with exit 0 (`readBlocked`, `cross-ai.mjs:4072-4082`; selftest `blocked-status-none` and
  `malformed status` at `cross-ai-selftest.mjs:1119,3320`). A bad pool string exits **2** with `AIKIT-XAI status=usage` and stderr
  `cross-ai: --blocked-status must look like <provider>:free` (`cross-ai-selftest.mjs:3340-3341`). Combining with `--blocked-clear`,
  `--print-argv`, `--classify-only`, `--sweep`, `--describe` or `--self-test` exits 2 (`cross-ai.mjs:6782`). It spawns no host
  (`subprocess-quota-policy.md:185`). [VERIFIED]
- **Record location.** `${XDG_STATE_HOME:-$HOME/.local/state}/ai-kit/spec/blocked/<encodeURIComponent(pool)>.json`
  (`stateHome` `cross-ai.mjs:3985-3989`, `blockedFilePath` 4069). `child_env` forwards the caller env minus host-signal vars
  (`runner_dispatch.py:161-171`), so `XDG_STATE_HOME` and `HOME` reach the child. Test fixture precedent with a scratch state home:
  `tests/test_runner_describe.py:247-266`.
- **Which runner file Python spawns.** Product code spawns the **package template** `skills/ai-kit-spec-review/references/cross-ai.mjs`
  through `resolve_cross_ai_template_path()` (`tooling_guidance.py:36-40`), via `RunnerSeams.runner_path_fn` (`runner_dispatch.py:301`).
  `.planning/scripts/cross-ai.mjs` exists in this repo (the project's rendered copy) but `PROJECT_RUNNER_PATH`
  (`runner_dispatch.py:33`) is used only to build the GSD hook token list (`runner_dispatch.py:203`). Both read the same state dir, so
  use the template path. **No Python caller of `--blocked-status` exists** (rg found none in `ai_kit_spec`); only tests spawn it.
- **Spawn precedent to copy.** `print_argv_lines` (`runner_dispatch.py:306-328`): `bounded_run(run_fn)`, `which_fn("node")`,
  `runner_path_fn()`, `run_fn([node, template, ...], stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=..., cwd=..., env=child_env(env=...), check=False)`,
  catching `(OSError, subprocess.SubprocessError)`, returning `None` on any failure. Using `bounded_run`/`run_in_own_group` means no new
  `start_new_session=True` literal, which `tests/test_arch.py:2125-2173` (rule 11) forbids outside an allowlist.
- **Proposed call shape** (`[ASSUMED]` names):
  `blocked_until(pool: str, now: datetime, seams: RunnerSeams | None = None, run_fn=run_in_own_group) -> datetime | None`.
  Returns `None` on: no node, no template, spawn error, non-zero exit, any stdout that does not match
  `^blocked_until=(-|\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z) failures=\d+$`, or `-`. A lane is skipped only while `now < blocked_until`
  (a record equal to now counts as passed: SPEC edge "boundary R1"). Only called for a lane with `usage_limited` true **and** a `pool`
  (D-05). Parse with `datetime.strptime(..., "%Y-%m-%dT%H:%M:%SZ")`.
- **`--pool` pass-through gap.** `RunnerSpec` fields `runtime ... mcp_config` have no `pool`; `runner_flags` emits no `--pool`. Add
  `pool: str | None = None` as the **last** field, read `knobs.get("pool")` in `spec_with_effort` (`runner_dispatch.py:96-111`), and
  append the flag **after** the existing flags (the file's own byte-equal rule, `runner_dispatch.py:238`) so `tests/test_runner_flags.py`
  and the argv goldens stay green. Because `resolve_reviewers` puts every non-core lane field into `ResolvedReviewer.extra`
  (`quota.py:42-52`, `_KNOWN_REVIEWER_FIELDS = {"key", "model", "vendor", "runtime", "command"}` at `config_io.py:21`), `pool` and
  `usage_limited` already arrive in `reviewers.json` entries under `extra` and flow into `review_spec(..., extra)` (`reviewer_dispatch.py:108`).
  Pass `--pool` for the **ping too** (same `review_spec` path), otherwise an ok ping does not clear the record.
- **Runner reads vs product code reads (pitfall).** The runner "never refuses or switches a lane because of" a record
  (`subprocess-quota-policy.md:185`): skipping at selection is purely spec-review's job.

## Q2. `lane_usage_limit`, `lane_fallback`, the lanes table and "a chosen lane"

Verbatim signatures and returns [VERIFIED: skills/ai-kit-spec-review/ai_kit_spec/lane_settings.py]:
```
class UsageLimit(NamedTuple):            # :82
    limited: bool
    note: str
def lane_usage_limit(entry: dict) -> UsageLimit:                       # :103
def lane_fallback(role_lanes: list, key: str) -> str | None:            # :150  "first different, unflagged, different-pool lane in order"
def selectable_lanes(role: str, role_lanes, order) -> list:             # :139  review: ordered lanes only
```
- `lane_usage_limit(entry)` takes ONE lane dict; reads `entry["usage_limited"]` (must be a bool or raises `LaneSettingError`, a
  `ValueError`) and `usage_limit_note`. A reviewers.json entry keeps the flag under `extra`, so call it on the **config lane**
  (`config["review"][i]`) or on `entry["extra"]`.
- `lane_fallback(role_lanes, key)`: `role_lanes` is a **list of lane dicts** (`_keyed`: dicts with a str `key`, first occurrence wins,
  malformed skipped); returns the first lane in LIST order that is not the base, not `usage_limited is True`, and not the same non-empty
  `pool` as the base; `None` when the key is unknown or no lane qualifies. **Pitfall:** the list order is the table order, not the
  review order. Pass `selectable_lanes("review", config["review"], config["orders"]["review"])` (ordered review lanes only, the
  same call `fallback_warnings` makes at `lane_settings.py:179-181`) so a fallback never lands on a lane the owner left out of the
  review order. `lane_fallback` has no filter for a blocked pool or an already-failed lane: the new module must iterate (call it with a
  list from which failed or blocked lanes were removed) to honor "skips a lane whose pool is still blocked".
- **Where config lives at runtime.** `cfg_resolve(cwd, env)` returns a dict with `"review"` (list of lane dicts with `key`, `runtime`,
  `model`, optional `usage_limited`, `pool`, `effort`...), `"execute"`, `"orders"` (`{"review": [keys], "execute": [keys]}`), `"policy"`
  and the flat `"reviewers"` (`config_io.py:424-445`, `815`). `role_orders.role_order(config, "review")` returns the key list
  (`role_orders.py:85-89`). `resolve_reviewers(config, quota, source_vendor, cross_ai)` (`quota.py:122-193`) picks 1 or 2
  `ResolvedReviewer` (single/double by `policy.mode`), falling back to `NO_CONFIG_FALLBACK` (`session-default`, `quota.py:25`).
  `routing.route_all(entries, ctx)` (`routing.py:353`) maps `key -> route`; routes in `routing.SKIP_ROUTES` never dispatch.
  `dispatch_reviewer(ReviewerDispatchSpec, ReviewerSeams)` (`reviewer_dispatch.py:86`) runs ONE reviewer entry and returns
  `{stdout, returncode, timed_out, reason, status, argv}` (`_result_dict`, `reviewer_dispatch.py:61-65`).
- **"A chosen lane" during a review** is one entry of `reviewers.json` (a `ResolvedReviewer._asdict()` plus `route`, `cli.py:968-973`),
  addressed by its `--index` and `key`. The switch module's input should be (config, role order, failed key, result `reason`);
  its output a replacement lane **key** or `None` (D-04). A switched round re-resolves the replacement entry by key from `config["review"]`
  through `quota.to_resolved` + `routing` (so the replacement gets its own route, and its own `extra`/pool).

## Q3. Ping: probe, cache, CLI wiring, timeout and clock seams, concurrency

- `probe_reviewer_quota(resolved: ResolvedReviewer, seams: ProbeSeams | None = None) -> dict` (`quota.py:271`). Native entry (no runtime, no command)
  returns `{"available": True, "checked_at": time.time(), "reason": None, "detail": "", "answered": False}` without running anything.
  Otherwise one 30 s review through the runner/launcher; entry shape on failure
  `{"available": False, "checked_at": <time.time()>, "reason": <runner reason>, "detail": <stderr tail <=300>, "answered": False}`;
  on success `{"available": True, ..., "reason": None, "detail": "", "answered": bool(stdout)}` (`_probe_entry`, `quota.py:217-223`);
  a template render `ValueError` gives reason `"configuration"` (`quota.py:284-286`).
- `class ProbeSeams(NamedTuple)`: `runner_fn=run_runner`, `custom_fn=run_custom_command`, `env_fn`, `print_fn=None` (`quota.py:208-214`);
  `CliDeps.probe_seams()` builds it positionally (`cli.py:188-190`), so a **trailing** new field is backward compatible.
- **TTL and cache.** `QUOTA_TTL_SECONDS = 3600` (`quota.py:23`); cache file `os.path.join(cache_base(env), "quota.json")` (`cache_quota_path`, `quota.py:31-32`),
  read/written by `_cmd_probe_quota` with `cache_read_json`/`cache_write_json` (`cli.py:927-933`). `refresh_quota_cache(config, ladder_keys, existing, ttl_seconds, seams)`
  re-probes only missing or `now - checked_at >= ttl` entries and looks lanes up in `config.get("reviewers", [])` (`quota.py:290-307`).
- **No clock seam and a fixed 30 s probe.** `probe_reviewer_quota` and `refresh_quota_cache` call `time.time()` directly, and
  `_probe_call` hard-codes `review_spec(..., 30, ...)` (`quota.py:253`). For the ping: (a) the per-ping timeout rides the existing seam by
  wrapping `ProbeSeams.runner_fn` so it replaces `spec.timeout_s` (`spec._replace(timeout_s=...)`), or add a trailing `timeout_s` field to
  `ProbeSeams` (cleaner; default 30 keeps today's behaviour); (b) the clock: the ping module takes `now_fn`/`sleep_fn`, decides
  "stale" itself (`now - checked_at < QUOTA_TTL_SECONDS` = fresh, "TTL minus one second is not pinged, plus one second is": SPEC edge R2
  precision) and overwrites `checked_at` with `now_fn()` in the entry it stores, so no edit to `quota.py` clocks is needed.
- **Thread-pool caveat.** `future.result(timeout=)` cannot stop a hung thread; the real bound is the runner's own timeout (the probe's
  process group is killed on its deadline, `run_runner` `deadline` at `runner_dispatch.py:660`). Record a wall-clock overrun as
  reason `ping_timeout` and treat the lane as blocked, as the SPEC's boundary edge says. Tests: the fake probe sleeps through
  an injected `sleep_fn`/real 2 s only for the "2 lanes x 2 s under 3.5 s" assertion; every other test uses an instant fake.
- **Existing `probe-quota` wiring.** Parser `cli.py:285-301` (`--cwd --quota-path --role --no-save-runtimes --no-migrate`);
  handler `_cmd_probe_quota` (`cli.py:922-934`): `cfg_resolve` -> `_probe_lanes(config, role)` -> `_route_reviewers` ->
  `routing.probe_keys` (skips non-probe routes) -> `refresh_quota_cache` -> write cache -> print JSON dict `{key: entry}`.
  SKILL.md:177-195 (Step 0.7) describes it as a sequential walk once per invocation; `references/cross-ai-dispatch.md:144-163`
  holds the verbatim bash.
- **Concurrency precedent exists:** `ThreadPoolExecutor` with `as_completed` in `tools/run_unittest_parallel.py:84,935` and an injectable
  `runtime("concurrent.futures")` in `tools/cursor_quota.py:624-657` (tools/ code; no use inside `skills/`). Use stdlib
  `concurrent.futures` in the new module. Match results to lanes by **key** (futures complete out of order), pass `max_workers=len(unique keys)`,
  and de-duplicate identical keys (SPEC edge: "same key pinged once").
- **What the ping returns:** per lane key `{"status": "ok"|"blocked"|"fresh"|"skipped", "reason": <REASONS member|None>, "checked_at": ...}`;
  the CLI prints JSON, exit 0 when at least one lane survives, exit 3 (or similar, plan-time) with reason `no_lane_left` when none does,
  so SKILL.md can stop without dispatching.

## Q4. `REASONS` and every reader/pin (D-01)

Verbatim [VERIFIED: skills/ai-kit-spec-review/ai_kit_spec/error_classifier.py:16-26]:
```
REASONS = (
    "quota",  "auth",  "timeout",  "configuration",  "dispatch_unavailable",
    "real_error",  "capacity",  "billing_or_access",  "git_timeout",
)
```
(one per line with comments in the file; the lock test below names the same nine.)

**Readers and pins (complete list found by `rg REASONS`):**
| Where | What it does | Effect of adding keys |
|-------|--------------|-----------------------|
| `tests/test_ai_kit_spec.py:3483-3490` | `test_reason_vocabulary_is_closed`: `assertEqual(set(REASONS), {nine keys})` | **must be extended in the same commit** |
| `tests/test_ai_kit_spec_runtimes_table.py:774-780` | `test_map_values_are_none_or_known_reasons`: every `STATUS_TO_REASON` value is in `set(REASONS)` | stays green |
| `tests/test_quota_policy_text.py:28,152-153` | `CLASSIFIER` path read only for `wake_lines(...) == []` (no fixed-interval wake wording) | new comments in `error_classifier.py` must not contain `hourly`/`every hour`/`recurring` |
| `ai_kit_spec_superpowers/dispatch_injection.py:100-114` | docstring names the reasons; behaviour reads only `"quota"` and `"auth"` (`reasons_summary`, lines ~85-91) | no code reads `REASONS`; the review-level keys never reach execute |
| `skills/ai-kit-spec-execute-superpowers/references/resolution-stops.md:31-36` | prose list of reasons | not pinned by a test; leave unchanged (review-only keys), optional |
| `error_classifier.py` itself (`STATUS_TO_REASON`, `_EXIT_FALLBACK`, `classify_error`, `reason_for_status`) | values are `None` or members | unchanged |
| `ai_kit_spec/effort_probe.py:15` `REJECTING_REASONS = ("real_error", "configuration")` | independent tuple | unchanged |

`tests/test_prompt_guard.py`/`test_cross_ai_docs_text.py:250` read `REFUSAL_REASONS` (a different tuple); `fold_engine.REASONS` is another
skill's frozenset: both unrelated, do not touch. There is **no documented reason table** today; SPEC R3's "documented list" must be created.

**Review-level reasons NOT covered by the nine:**
- *Ping timeout* (wall-clock overrun of the ping deadline): the runner's own timeout already maps to `timeout`; the **ping deadline overrun**
  is a distinct fact the SPEC wants recorded -> add `ping_timeout`.
- *Missing runtime* (no node/runner, binary absent): already `dispatch_unavailable` (`STATUS_TO_REASON["not_installed"]`, `error_classifier.py:50`;
  runner-missing line in `runner_dispatch.py:59`) -> **reuse**, no new key.
- *No lane left*, *replaced*, *never resolved* (pending hard-tier lane or timeout with no report): no key -> add `no_lane_left`, `replaced`, `never_resolved`.
- *Default reason for an unclassifiable failure*: already `real_error` (`classify_error` returns `... or "real_error"`, `error_classifier.py:125`;
  `reason_for_status` returns `_EXIT_FALLBACK.get(returncode, "real_error")`, line 135; `entry_reason` legacy default line 205) -> **reuse**; the
  SPEC "empty" edge asserts a failure never records an empty/None reason.

**Proposed final names (fit the snake_case style, comment-per-key):** `replaced`, `never_resolved`, `no_lane_left`, `ping_timeout`
-> 13 keys. `[ASSUMED]` naming; CONTEXT leaves names to plan time.

**Files a key addition must touch, in one commit:** (1) `ai_kit_spec/error_classifier.py` (tuple, header comment "nine"->"thirteen" if present);
(2) `tests/test_ai_kit_spec.py:3483` expected set; (3) new `skills/ai-kit-spec-review/references/lane-failure.md` reason table;
(4) a new lock test that parses that table (first-column backticked keys, same regex style as `tests/test_cross_ai_settings_text.py:60`
`re.findall(r"^\| \`([a-z_]+)\` \|", ...)`) and compares to `set(REASONS)`, with a non-vacuity case (seed an extra key in a copy of the text and see it
differ, pattern at `test_cross_ai_settings_text.py:222-227`). No other test needs a change. Lane-failure.md must obey
`tests/test_skill_text_history.py` (see Pitfall 4).

## Q5. Report: `merge-reports`, "Approved", the log

- **`merge-reports` today.** `_cmd_merge_reports` (`cli.py:976-1001`): for each `key=path` it reads the file, classifies via
  `report_status`; **any** lane with no readable file / no `### Status:` / status `failure` goes into `failing`; if `failing`, it prints
  `### Status: Failure — <keys>` and **returns 1** with no merge (`cli.py:992-997`). Otherwise `merge_findings` + `render_merged_report`
  (`review_reports.py:72-145`): header `## Review: <doc paths>`, `### Document Type`, `cross-ai merged`, severity sections, then
  `### Status: Issues Found — fix and re-invoke` or `### Status: Approved`. Reviewer-report finding bullets must match
  `_BULLET_RE` = `^- \*\*(.+?)\*\* — Location: (.+?)\. Required: (.+?)\. Why: (.+?)\.\s*$` (`review_reports.py:11-13`), under bare headings
  `### CRITICAL|HIGH|MEDIUM|LOW|Cross-Document Consistency`. Tests pinning the fail-closed merge: `tests/test_ai_kit_spec.py:3660-3715`
  (single/both lanes failing -> `Failure — a`, `Failure — a, b`) and `4452-4478`; `report_status` unit tests at `3625,3639`.
  **R4 requires the merge to keep the surviving lane** (partial), so these tests change: a one-lane failure now merges the other lane and
  marks the report partial; **both lanes failed still yields `### Status: Failure`** (nothing judged -> "not reviewed", never Approved).
- **Where "Approved" is produced.** `merge-reports` emits `### Status: Approved` (`review_reports.py:143`) for the 2-lane case; for one lane the
  raw reviewer report is `EFFECTIVE_REPORT_PATH` (SKILL.md:440-445). The user-facing strings ("Approved on first review...", the Step 5 table
  at SKILL.md:508-519) and the pending-lane rule ("an approval while a lane is pending surfaces as that row, never as Approved", SKILL.md:523-524)
  are **prose the host agent follows**; no code renders them. To be testable with fake lanes, the partial status must come from code.
- **Review log.** None exists. SKILL.md:204 mentions an optional, debug-only `$RUN_TMP_DIR/loop.log`; there is no per-round lane record.
  **Create** `$RUN_TMP_DIR/lanes.json` (name `[ASSUMED]`), written atomically (`tempfile.mkstemp()` + `os.replace()`, AGENTS.md rule; reuse
  `_atomic_write_json` from the config helpers) with per round: `{round, lanes: {key: {state: judged|replaced|failed|never_resolved|pending,
  reason, replaced_by, checked_at, size_reason}}}`.
- **Proposed shape.** New module `review_log.py` (record + `partial_status(log) -> "clean"|"partial"|"not_reviewed"`, `judged_line(roster_order, log)`),
  and `merge-reports` gains `--lane-log <path>` (optional; absent keeps the old call valid) so it prints, after the Status line, a header line
  `Judged by: <keys in roster order>; not judged: <key> (<reason>)...` and `### Status: Approved (partial)` when the merged findings are
  clean but the log is partial. `_status_value` (`review_reports.py:22-28`) must keep treating `Approved (partial)` as `approved`
  (it uses `startswith("approved")`, so it already does). Step 5 text then quotes the line; SKILL.md says "Approved (partial)" only in a table row.
  Pin wording in a doc-contract test (SPEC R4).
- Fixer interplay: `apply-findings.md` and the fixer treat `### Status: Approved` by prefix elsewhere? Check at plan time that no regex in
  `references/` or in tests requires the exact line `### Status: Approved` for the merged report (`rg "Status: Approved"` over tests before choosing the suffix form).

## Q6. "Judge round": what it is here

"Judge round" in this repo is a round of the **skill-judge loop**: `tools/judge_loop.py` (subcommands `prompt`, `ingest`, `check`, `report`,
`pool`, `count`; `build_parser`, `tools/judge_loop.py:1974-2020`) with its own lane probe (`prompt --probe` writes probe prompts, `pool`
calls `choose_pool`/`probe_result`, `tools/judge_loop.py:337-360,1501-1552`) and scratch drivers in `tmp/judge-<loop>/lanes.py`
driven by an orchestrator plan (see 39.2-09-PLAN.md Task 1 steps 5-6: probes, `lanes.py pool`, `assign`, `launch`). Judge lanes are **not**
spec-review review lanes and `judge_loop.py` never imports `ai_kit_spec`. There is no spec-review code path named "judge round".
So the only shared entry point a judge round can reuse is the **new ping CLI subcommand** (e.g. `ai-kit-spec.py ping-lanes ...`) named in the judge
plan's probe step; the plan must say how a judge lane list is handed to it (it takes `--keys`/the config `review` lane keys; judge-only
referee lanes that are not in the owner's `[lanes]` cannot be pinged by it).
**Open question O1** (below). Recommendation: implement REV-07's "judge round" clause as: the ping subcommand accepts an explicit
`--reviewers-json` (the same file a review round uses) and the judge orchestration plan calls it before each round; do not modify `judge_loop.py`
(it has its own pool probe, SPEC lists the judge loop as a process over files).

## Q7. jev: `ask_items`, detection, fakes, precedents

- `ask_items(entry: str, items: list, env, run=subprocess.run, strict=False) -> dict` (`jev_names.py:140`): returns `{item_id: (choice|None, top|None, reason)}`;
  `reason` is `""` (answer), `"low"` (`needs_fallback`, `forced` or `fallback` true, `_column_answer` `jev_names.py:130-131`), `"no answer"`, `"timeout"`,
  `"old"` (exit 2 `invalid choice`), or `"failed"` (`strict=True` and non-zero exit). Items need `id`, `type: "choice"`, `instructions`, `context`,
  `criteria: {class: description}`; the answer's `choice` must be a criteria key. Batches are capped at `BATCH_CHARS = 7000` (`jev_names.py:33,106-118`). There is
  **no confidence threshold** inside `ask_items`: `top` is returned raw, so "low confidence" = the `reason == "low"` or a caller threshold
  (precedent `lane_order.STABLE_TOP = 0.80`, `lane_order.py:14,93-98`). Adopt `STABLE_TOP`-style: confident = `reason == ""` and `top >= 0.80`; anything else is the sentinel.
- **Presence:** `jev_names.find_jev(env, own_root=None) -> path|None` (first existing `jev-fast-decision/scripts/jev_review.py` across the skills roots,
  `jev_names.py:11-69`). `None` = absent (`skill_classify.classify` returns `"jev": "absent"` and no proposals, `skill_classify.py:121-124`).
- **Sentinel on no answer:** `lane_order._judged` returns `NEUTRAL_LEVEL, None, None, "scorer", <reason text>` and `rank` catches `_JUDGE_ERRORS`
  (a tuple of specific exceptions, `lane_order.py:26-27`) instead of `except Exception` (rule 9). Copy: the new adapter returns a small
  `NamedTuple` `(klass|None, confidence|None, reason)` per finding and the caller takes today's path when `klass is None`.
- **How tests fake jev:** pass `run=` (a fake `subprocess.run`) and a fake env; payload-recording precedent `tests/test_catalog_jev_names.py:43-45`
  (reads the recorded JSON, asserts `payload["items"][0]["context"]`) and `:133-146` (collects the `input` of each call, asserts sizes). That test pair is the one to
  copy for "only summaries go to jev": record every `input`, then assert no item contains the document text, a path from the repo, or a finding body beyond a
  bounded summary. `tests/test_jev_config_parity.py` and `test_arch.py` `LOOKUP_COPIES` (rule at `test_arch.py:2472-2494`) bind the *copy* of the jev client in
  `jev_names.py`; a new module must **import** `jev_names`, never copy the client.
- **Items to build:** `classify_disagreements`: one item per finding, criteria `owner_decision`/`mechanical`/`reviewer_wrong` (each with a one-line
  description), context = severity word + title + the fixer's stated reason, each `jev_names._clean`-style printable-ASCII-bounded, plus the
  `secret_shapes.redact` step `skill_classify.role_item` uses (`skill_classify.py:86-100`). `size_review`: one `choice` item with criteria
  `one`/`two` (lane count) and a second for the reviewer key from the roster only.
- **Hard rules to encode:** a CRITICAL/HIGH finding is never routed `mechanical`/`reviewer_wrong` (route table in code, tested); a pick outside the roster is discarded;
  jev absent/error/low -> sentinel.

## Q8. Deterministic signals and sizing inputs (D-07)

- **No reusable signal module.** `tests/test_ai_kit_spec_goal_prompt_signals.py` tests `gp_e2e.py` (e2e-evidence signals, header line 1), not security/data/irreversible
  detection; `rg` finds no such matcher in `skills/`. The only deterministic-trigger precedent is `tools/judge_loop.py:deterministic_count` (`1650-1662`): "two
  when one applies, else one", reasons returned as strings. Mirror its shape: `signals(...) -> (floor_lanes:int, reasons:list[str])`.
- **Inputs available at Step 0.7 -> 1.** SKILL.md variables: `DOC_PATHS` (the document paths, saved on disk by Step 0), `ARCHETYPE` (one or more of `intent|requirements|design|plan`),
  `FRAMEWORK_PROFILE_PATH` (profile file or `none`), `GROUNDING_DOCS`, `CODEBASE_ROOT`, `REVIEWER_LIST` (SKILL.md:100-114,144-153,161). The signal function therefore takes
  the document **text** read from `DOC_PATHS` (the script reads the file itself; nothing but the verdict goes to jev) plus the path list.
- **Computable from a superpowers plan** (verified format, e.g. `docs/superpowers/plans/2026-08-31-ai-kit-spec-dispatch-hardening.md:69-72,297-302`): task count
  = `^### Task \d+` headings (checklist plan archetype uses `### Task N`, `ai-kit-spec-review-checklist/SKILL.md:87`); files touched = unique paths in `**Files:**` bullets
  `^- (Create|Modify|Test|Delete): \`path\``; checkboxes `- [ ]` count as steps; category = archetype + framework id (`superpowers`, `gsd`...). GSD plans use `<task>`/`<files>` tags
  (`39.2-10-PLAN.md:76-78`). Complexity = a bucket from task count and file count (no model call).
- **Proposed trigger rules (`[ASSUMED]`, to be fixed at plan time with held-out fixtures; keyword regexes are case-insensitive and word-bounded, applied to headings, `Files:` paths and task text):**
  - `security`: path segments or words matching `\b(auth|authn|authz|oauth|jwt|session|csrf|xss|crypto|encrypt|decrypt|secret|credential|token|password|permission|acl|sandbox|trust)\b`
    in a changed path or task title; or the words `security`, `vulnerab`, `injection`.
  - `data`: `\b(database|schema|migration|migrate|sql|table|index|backfill|pii|gdpr|retention|persist|datastore|dump|restore)\b`, or a path under `migrations/`, `*.sql`.
  - `irreversible`: `\b(drop|delete all|truncate|rm -rf|force[- ]push|reset --hard|purge|wipe|destroy|irreversib|publish|release|deploy|rotate key)\b`.
  Any one hit -> floor of two lanes; the reason string names the signal and the matched token only (a summary, never the surrounding text). Boundaries: an empty plan hits none; a trigger inside a fenced
  example is still a hit (fail toward two lanes, the safe direction).
- **jev sizing inputs (summaries):** files touched (count), task count, complexity bucket, category (framework + archetype), the signal outcome, and the
  roster order as a key list. Payload is numbers and words only. "jev picks the reviewer from the owner's order" = jev chooses among roster keys already in `config["orders"]["review"]`;
  anything else is discarded (SPEC R6).
- **Where sizing plugs in:** between `resolve-reviewers` (which already yields 1 or 2 by `policy.mode`) and writing `reviewers.json`: a `size-review` subcommand reads the config, the doc, and
  prints the decided key list plus a log reason; the log reason goes into `lanes.json`. With no jev or a low answer the output equals today's `resolve_reviewers` result (**no behaviour change**, SPEC prohibition).

## Q9. Fold step (D-08)

- **Documented wording in `ai-kit-spec-execute-superpowers`** [VERIFIED: skills/ai-kit-spec-execute-superpowers/SKILL.md:108]: "If the plan's last `### Task` does not name `ai-kit-commit-fold`, add a final todo `Fold the plan's commits (ai-kit-commit-fold)` to subagent-driven-development's task list; never edit the plan file." Step 5 (SKILL.md:288-290) and `references/fold-step.md` run `fold.py checkpoint ... --final` then `fold.py ready`. The evals quote the todo
  name (`evals/evals.json:56,61`). So the testable rule: **the plan's last `### Task` section names `ai-kit-commit-fold`** (the adapter's own condition). The fixer's added step uses the
  todo wording "Fold the plan's commits (ai-kit-commit-fold)".
- **Encoding edge (SPEC R7):** recognize case-insensitively in a heading or a checkbox of the last task. Implementation: split the plan at `^### Task `, take the last section, regex
  `ai-kit-commit-fold` (case-insensitive) or `fold the plan'?s commits`; an empty plan (no `### Task`) yields no fold finding.
- **Detection of a superpowers plan.** Framework profile `superpowers` (`ai-kit-spec-review-checklist/references/frameworks/superpowers.md:2,14`) maps
  `docs/superpowers/plans/*.md` to archetype `plan`. The orchestrator already resolves both in Step 0.5 (SKILL.md:100-114) as `FRAMEWORK_PROFILE_PATH` and `ARCHETYPE`. The check takes `--framework-id superpowers`
  (profile id, `[ASSUMED]` flag name) and `--archetype plan` plus the doc path; any other combination prints nothing (never flags a non-superpowers plan; a fused design doc never).
- **Cleanest hook:** a deterministic subcommand `check-fold-step --doc <path> --framework <id> --archetype <a>` that prints either nothing (exit 0) or one finding bullet in the
  reviewer shape that `parse_findings` already parses (`review_reports._BULLET_RE`):
  `- **Plan has no fold step** — Location: last ### Task. Required: the plan's last ### Task names ai-kit-commit-fold (a final task "Fold the plan's commits (ai-kit-commit-fold)"). Why: ... .`
  under a `### HIGH` heading. SKILL.md then adds one step between reviewer dispatch and Step 1.5: write the output to `$RUN_TMP_DIR/iter<N>-fold.md` as a synthetic report
  (`### HIGH` + bullet + `### Status: Issues Found — fix and re-invoke`) and pass it to `merge-reports` as an extra `fold=<path>` key, so the finding merges with the same dedup and
  rendering, with the fixer treating it like any HIGH (fixer rule: addresses every CRITICAL/HIGH, `ai-kit-spec-review-fixer/SKILL.md:48`). No new fixer behaviour is needed; the fixer
  "adds the step" because the Required line names the outcome. A with-step plan prints nothing and merge sees no `fold` key.
- **Cross-skill rule.** `tests/test_arch.py:2459-2469` (`test_no_cross_skill_reach_outside_the_allowlist`, frozen allowlist at 2469) forbids spec-review code from reaching into another skill's
  files, so the wording is a **constant in the check module**, pinned against `ai-kit-spec-execute-superpowers/SKILL.md` by a **test** (tests may read both). Spec-review gets no import of the adapter.

## Q10. Evals and tests

- **Shape.** `evals.json` top-level `skill_name` and `evals` list; each eval has exactly `{"id","prompt","expected_output","files","assertions"}` (`tests/test_skill_evals_shape.py:19,46`);
  id regex `^(casual|precise|edge)-[a-z0-9-]+$` (line 17); at least 5 evals, at least one of each prefix; `assertions` >= 2 strings of >= 20 characters; `files` each under `evals/files/`
  and existing, and **every file under `evals/files/` must be named by some eval**; no machine path (`MACHINE_PATH_RE` line 16). Counts today: `ai-kit-spec-review` 15, `-fixer` 7,
  `-checklist` 9 (`rg -c '"id":'`; REJUDGE.md rows 104,111,112 agree). Last two review evals: `edge-refused-lane-exit-65`, `edge-edit-lens-pass-owner-started` (`evals.json:143,153`).
  New evals (SPEC R8): flagged-lane switch, blocked lane replaced by a ping, partial report, jev-classified disagreement; use fixtures from `evals/files/active/project/...` (existing pattern,
  `evals.json:146,156`). The refused-lane eval already asserts "never re-dispatches the lane" (`evals.json:149`): re-read it so the narrowed rule does not contradict it (a refusal is still never switched).
- **Modules that cover spec-review today** (units run under system python3 via the `unit` group unless in `UNIT_UV_MODULES`/`INTEGRATION_MODULES`/`ARCH_MODULES`/`E2E_MODULES`, `tools/run_unittest_parallel.py:92-117,233-237`):
  `tests/test_ai_kit_spec.py` (REASONS, merge-reports, probe, CLI), `test_ai_kit_spec_routing.py`, `test_ai_kit_spec_runner_dispatch.py`, `test_ai_kit_spec_runtimes_table.py`, `test_role_orders.py`,
  `test_lane_settings.py`, `test_lane_order.py`, `test_catalog_jev_names.py`, `test_quota_policy_text.py`, `test_cross_ai_docs_text.py`, `test_cross_ai_skill_text.py`, `test_runner_describe.py`,
  `test_runner_flags.py`, `test_ai_kit_spec_review_checklist.py`, `test_ai_kit_spec_review_fixer.py`, `test_skill_evals_shape.py`, `test_skill_text_history.py`, `test_arch.py` and `test_arch_hardcoded_models.py` (arch group),
  `test_check_dogfood.py`. New `tests/test_*.py` modules join the `unit` group automatically (AGENTS.md); `tests/test_gate_scope.py` enforces it.
- **E2E modules exercising spec-review (must stay green):** `tests.test_ai_kit_spec_e2e` (recorded 3 s, `E2E_RECORDED_SECS`), `tests.test_cross_ai_runner_e2e` (18 s),
  and the `tests.test_cross_ai_selftest_{logic,runtime}_*_e2e` shards (the runner template; **do not edit `cross-ai.mjs`**: SPEC puts the runner out of scope), plus curated-config e2e
  modules that import `ai_kit_spec` (`test_curated_config_e2e`, `test_curated_config_apply_e2e`) (`rg -l ai_kit_spec tests/test_*e2e*.py`).
  A new `*_e2e` module needs an `E2E_MODULES` entry and a recorded seconds value; avoid adding one: keep new tests unit-level with fake lanes. Spawning `node` for the blocked-status wrapper
  can be covered by a unit test that fakes `run_fn`, plus one real-node case guarded by `skipTest` like `tests/test_runner_describe.py:247-249`.

## Q11. Constraints binding new modules

| Rule | Source | Consequence |
|------|--------|-------------|
| Stdlib only in runtime code | AGENTS.md | no new third-party import; jev only via `jev_names` |
| Rule 8: no `shell=True` in the spec family | `tests/test_arch.py:2267-2283` | argv lists only |
| Rule 9: broad `except` only in `_BROAD_EXCEPT_BACKSTOPS` | `test_arch.py:2040-2090,2419-2434` | catch specific tuples (`lane_order._JUDGE_ERRORS` precedent, `lane_order.py:26`); adding a backstop is a frozen-list edit, avoid |
| Rule 11: `start_new_session=True` only in an allowlist | `test_arch.py:2125-2173` | spawn the status read through `bounded_run`/`run_in_own_group` (`detection.py:955,980`); no new literal |
| Rule 12 (tests): `if __name__ == "__main__"` last statement | `test_arch.py:2372-2382` | every new test module ends with the guard |
| Host-CLI literal rule (tests) | `test_arch.py:2405-2417` | no test names a host CLI as the spawned program; use `tests/host_fakes.py` |
| No test reads `.planning/` | `test_arch.py:2384-2402` | fixtures under `tests/fixtures/` or temp dirs |
| Hardcoded-model guard + baseline | `tests/test_arch_hardcoded_models.py` (`BASELINE = tests/fixtures/no_hardcoded_models_baseline.json`, schema 2, only shrinks; `MARKER = "model-example:"`) | new code, tests, docs and evals use placeholder names like `fake/placeholder-model-1` (pattern at `test_runner_describe.py:272`); no `provider/model` literal that scans as a real model; never add a baseline entry |
| Cross-skill reach frozen | `test_arch.py:2459-2469` | spec-review imports nothing from another skill |
| Lookup copies | `test_arch.py:2472-2494` | import `jev_names`; never copy the client |
| Skill text history | `tests/test_skill_text_history.py:82-122` | `SKILL.md` main flow and every shipped `.md` outside `evals/` (so `references/lane-failure.md`): no ISO dates, no "as of", no phase folder/file names, no backlog ids, no `D-NN` ids, no `router-env/` or `referee-` names, no tool versions in prose outside a constraint/code span; provenance goes in a trailing `## Evidence` section (dates allowed there only) |
| Python names no planning file | `test_skill_text_history.py` (class around line 509-575) | no `.planning/...` path or phase folder in docstrings/comments of new modules |
| pylint caps | AGENTS.md: `max-args=5`, `max-locals=15`, `max-branches=12`, `max-returns=6`, `max-statements=50` | pass a small `NamedTuple` (e.g. `PingSeams`, `SwitchInput`) rather than 6+ args; split `_cmd_*` handlers |
| Atomic writes | AGENTS.md | round log via `tempfile.mkstemp()` + `os.replace()` |
| `vulture` min_confidence 80, `pyright` basic | AGENTS.md | no unused new function; every new public function has a caller or test (tests count for vulture only if scanned: `tests/` is in vulture scope per AGENTS.md) |
| Evals/docs: no machine absolute path | SPEC Constraints, `MACHINE_PATH_RE` | repo-relative paths only |

**Which module may hold which literal.** Reason strings live only in `error_classifier.py` (`REASONS`); other modules `import` the tuple and never retype a reason string
except through a constant derived from it (keeps the lock test the one place). The pool regex stays in `lane_settings.POOL_RX` (new code imports it; do not copy). The `--blocked-status`
flag string lives in exactly one new wrapper (`blocked_pool.py`, `[ASSUMED]` name) since the runner template is the other holder (`test_runner_describe.py:227,311` pins the flag lists).
`cli.py` is 1481 lines; **register new commands via new modules' `register_parsers(sub)` and `COMMANDS` dict** (call sites `cli.py:506-512`, `1456-1462`), two added lines per module in `cli.py`.

## Q12. Judge loop

- **Tool:** `tools/judge_loop.py` subcommands `prompt` (`--loop --round --judge --skill --out`, or `--probe`), `ingest`, `check` (`--gate`, `--skills`, `--require-current`), `report`, `pool`, `count`
  (module docstring lines 1-20; parser lines 1974-2020; `ROUND_CAP = 3` line 684). Records under `.planning/judge/`: `inputs.json` (roster `skills` / `excluded`), `loops/<loop>.json`
  (pool, probes, counts), `verdicts/<loop>/<skill>/r<N>/<judge slug>.json` (+ `fixes.md` after a no-rejudge fix), `refutations/<loop>.json`, regenerated `REJUDGE.md`, `facts.json`
  (`39.2-09-PLAN.md:7-12,143`). `make check-dogfood` validates them (`tools/check_dogfood.py`, AGENTS.md).
- **Baseline grades (from `.planning/judge/REJUDGE.md`):**
  | Skill | Last loop / round | Lowest percent | Grade | Bar line |
  |---|---|---|---|---|
  | `ai-kit-spec-review` | loop 39, round 3 (rounds 3) | 82.4 | B | "met: grade B or better; lowest percent 82.4, loop 36 base 83.2" (REJUDGE.md:34) |
  | `ai-kit-spec-review-fixer` | loop 32.1, round 1 | 81.6 | B | "met: no critical or high finding; lowest percent 81.6, loop 32 base 75.2" (:27) |
  | `ai-kit-spec-review-checklist` | loop 39.1, round 1 | 88.8 | B | "met: grade B or better" (:35) |
  Regression limit: compared at `REGRESSION_TENTHS` (`judge_loop.py:1631`) against the prior loop's lowest percent. A new loop id (e.g. `40`) for the three skills; the checklist and fixer
  must be judged only if their SKILL.md changes materially (SPEC R8 names them; the fixer rule line 48 and checklist output shape may need only an eval/test change: decide at plan time and record).
- **Plan shape to reuse.** `39.2-09-PLAN.md` (judge plan; orchestrator action, `autonomous: false`, `cross_ai: false`): front-matter with `requirements: [..., JDG-04]`, a two-task body (Task 1 `checkpoint:human-action`: copy the previous loop's scratch drivers from `tmp/judge-39.x/` with the loop id replaced,
  allowlist + collision scan, judged-set-from-git, probes, `lanes.py pool`/`count`/`assign`/`launch`, frozen tree until `check.py` and audits end, three lanes per skill (two pool judges + referee-three advisory with the owner's Opus-high substitute on failure);
  Task 2 `auto`: `publish.py`, `report.sh`, `check.py`, `bar_table.py`, `decide.py` per skill -> `record|fix|next-round|owner-round-3`; fix rule: <= 3 critical+important+high findings -> one fix commit with `verdicts/<loop>/<skill>/r<N>/fixes.md`, no re-judge; closing `closing.sh`), executor shell rules verbatim, threat model T-xx-13..15.
  `39.2-10-PLAN.md` (closing plan): Task 1 installed-layout scratch check, Task 2 suites once each under `tmp/run-2026-11-23/orch-guard.py` (`make test`, `make e2e-docker`, `make check-dogfood`, installer dry run, `AI_KIT_TEST_REPORT_DIR` per-module reports + `evidence.py`), Task 3 ROADMAP tick last; orchestrator steps: `judge_loop.py check .planning/judge --skills ... --require-current`, then the link-only live install check. Plan 40's judge plan should be written from 39.2-09 (loop id `40`) and the closing plan from 39.2-10; both **depend on the scratch drivers under `tmp/judge-39.2/` being present** (untracked): if missing the 39.2 plan says stop with an owner question.
- AGENTS.md judge rules to restate in the plans: <= 3 rounds per skill; <= 3 critical/important/high findings -> fix without re-review, fix commit recorded beside the round; disputed finding refuted only by a recorded run; digest stale by design until next loop; SKILL.md describes behaviour, provenance in a trailing section (`## Evidence`).

## Architecture Patterns

### System Architecture Diagram

```
Step 0.5/0.6 (DOC_PATHS, ARCHETYPE, FRAMEWORK_PROFILE_PATH)
   |
Step 0.7  config-status -> probe-quota (cache) -> resolve-reviewers --> [size-review: signals -> floor 2 | jev -> 1|2 | none -> today's count]
   |                                                                     writes reviewers.json + lanes.json (round 0: size_reason)
   v
ping-lanes (before round 1; later only failed/stale lanes)   --blocked-status per flagged pooled lane (node cross-ai.mjs, 1 line)
   |  concurrent probes by key (ThreadPoolExecutor, per-ping timeout) -> reason from REASONS
   |  blocked lane -> lane_switch (same selection as R1: lane_fallback over ordered review lanes minus blocked/failed)
   |  none left -> stop: reason no_lane_left, no dispatch
   v
Step 1 dispatch each lane (native | dispatch-reviewer with --pool for flagged lane)
   |  flagged lane + reason quota after dispatch -> lane_switch -> re-dispatch replacement this round
   |  any other failure -> lane stays failed (reason), owner decides
   v
check-fold-step (superpowers plan only) -> synthetic HIGH report "fold=<path>"
   v
Step 1.5 merge-reports --lane-log lanes.json  (survivors merge; both failed -> Failure/not reviewed)
   v
Step 2/3/4 (fixer) -> disagreements (escalate | skip | cap-open) -> classify-disagreements (jev; CRIT/HIGH never closed)
   v
Step 5 surface: "Judged by: ...", "Approved (partial)" | "not reviewed" | today's rows
```

### Recommended structure (new modules in `skills/ai-kit-spec-review/ai_kit_spec/`; names `[ASSUMED]`)
```
lane_ping.py       # ping_lanes(...), PingSeams, ping CLI (register_parsers/COMMANDS)
lane_switch.py     # next_lane(...), blocked_until(...) wrapper (or blocked_pool.py), switch CLI
review_log.py      # round log read/write, partial_status, judged_line
jev_review.py      # classify_disagreements, size_review, sentinel (builds on jev_names.ask_items)
review_signals.py  # signals(text, paths) -> (floor, reasons)
fold_check.py      # fold-step check + one finding line; constant wording
references/lane-failure.md   # ping, flagged switch, partial status, reason table, jev classes (D-09)
```

### Anti-patterns
- A second reason list or a retyped reason string; a Python parse of the blocked record JSON (a second reader); sending code, diffs or finding bodies to jev;
  copying the jev client; passing a lane to `lane_fallback` as the whole config table instead of the ordered review list; printing "Approved" from prose only.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead |
|---------|-------------|-------------|
| Fallback choice | a new next-lane rule | `lane_settings.lane_fallback` over `selectable_lanes` |
| Blocked record read | JSON parser for the state file | `cross-ai.mjs --blocked-status` |
| Ping | a new probe | `probe_reviewer_quota` |
| jev call/batching/parsing | subprocess + JSON handling | `jev_names.ask_items` (+ `find_jev`) |
| Atomic JSON write | open/write | the existing `_atomic_write_json`-style helper (tempfile + `os.replace`) |
| Finding merge | a second merger | `review_reports.merge_findings/render_merged_report` |
| Process-group kill | `start_new_session=True` | `detection.bounded_run`/`run_in_own_group` |

## Common Pitfalls

1. **`merge-reports` fail-closed tests.** `tests/test_ai_kit_spec.py:3660-3715,4452-4478` assert today's whole-merge failure; update them in the same commit as the partial merge, keep a both-lanes-failed case.
2. **`lane_fallback` order trap** (Q2): wrong input list means a fallback outside the review order; also it knows nothing about blocked pools or already-failed lanes.
3. **`--pool` not wired** (Q1): without a `RunnerSpec.pool` field a flagged lane's ok run never clears the record; and a ping that omits it does not either.
4. **Skill-text history test** (Q11): `references/lane-failure.md` and SKILL.md edits must contain no `D-0x`, phase names, dates (outside `## Evidence`), `referee-` or `router-env/`. The existing SKILL.md `## Evidence` section (line 555) already holds dates: keep new provenance there.
5. **Pending hard-tier lane vs partial.** A hard-tier pending lane (SKILL.md:459, 523) is a `never_resolved`/pending state: the partial header must still print the hard-tier row first (the Step 2 table checks pending first).
6. **Cache TTL semantic.** `refresh_quota_cache` re-probes `>= ttl`; the SPEC edge says TTL minus 1 s fresh, TTL plus 1 s stale; implement `<` ttl = fresh, and unit test both sides with the fake clock.
7. **Native lanes are never pinged** (`probe_reviewer_quota` native short circuit); a native lane always counts "available", so "no lane left" can only arise with all external lanes blocked and no native entry in the order.
8. **`SKILL.md` is 560 lines** (CONTEXT D-09); additions must be short pointers into `references/lane-failure.md` to keep progressive disclosure and the judge grade.
9. **Evals `files` rule:** any new fixture under `evals/files/` must be named by an eval or `test_skill_evals_shape` fails.
10. **Tripwire isolation:** tests that exercise the wrapper must fake `run_fn`; the real-node case must set a scratch `XDG_STATE_HOME` and `AI_KIT_REFUSE_REAL_HOME=1` (pattern at `test_runner_describe.py:260-264`).

## Code Examples

Spawn-and-parse wrapper skeleton (pattern of `print_argv_lines`, `runner_dispatch.py:306-328`; `[ASSUMED]` names):
```python
_STATUS_RE = re.compile(r"^blocked_until=(-|\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z) failures=\d+$")

def blocked_until(pool, seams=None, run_fn=run_in_own_group):
    run_fn = bounded_run(run_fn)
    active = seams or RunnerSeams()
    node, template = active.which_fn("node"), active.runner_path_fn()
    if not node or not template:
        return None
    try:
        proc = run_fn([node, template, "--blocked-status", pool], stdin=subprocess.DEVNULL,
                      capture_output=True, text=True, timeout=30, check=False,
                      env=child_env(env=active.env_fn()))
    except (OSError, subprocess.SubprocessError):
        return None
    match = _STATUS_RE.match((proc.stdout or "").strip()) if proc.returncode == 0 else None
    if not match or match.group(1) == "-":
        return None
    return datetime.strptime(match.group(1), "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
```
Concurrent ping by key (`concurrent.futures`, stdlib):
```python
with ThreadPoolExecutor(max_workers=len(keys)) as pool:
    futures = {pool.submit(probe, lane): key for key, lane in unique_lanes.items()}
    for future, key in futures.items():   # results matched by key, not by completion order
        try:
            entries[key] = future.result(timeout=deadline_s)
        except TimeoutError:               # concurrent.futures.TimeoutError
            entries[key] = {"available": False, "reason": "ping_timeout", "checked_at": now_fn(), "detail": ""}
```
Reason list lock test shape: parse `references/lane-failure.md` table keys and `assertEqual(set(REASONS), keys)`; non-vacuity: `keys | {"zzz_new"} != set(REASONS)`.

## State of the Art

| Old | New (this phase) |
|-----|------------------|
| SKILL.md hard rule line 540: "Never re-dispatch a failed subprocess lane to another CLI, provider, model or the native session." (blanket) | "an unflagged lane never switches", flagged-lane exception named; lines 398 ("never switch lanes after a refusal") and 419 ("Never switch harness, provider or model", pinned by `tests/test_quota_policy_text.py:104` regex and `test_cross_ai_skill_text.py:250`) must keep their pinned text: **narrow line 540 only**, keep 419's pinned sentence verbatim or update both tests; a refusal (exit 65) is still never switched |
| One sequential probe walk per invocation | Concurrent ping before round 1; failed/stale lanes only afterwards |
| `merge-reports` fails on any lane failure | survivors merge, partial marker |

## Runtime State Inventory

Not a rename/refactor phase, but one state surface is touched: `${XDG_STATE_HOME:-~/.local/state}/ai-kit/spec/blocked/` records are **read only** (never written by this phase); `quota.json` cache (`cache_quota_path`) is written by the existing probe path only. New files live under `$RUN_TMP_DIR` (per-review temp dir, kept unless Approved, SKILL.md:549-553). None of the categories needs data migration.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Four new reason keys named `replaced`, `never_resolved`, `no_lane_left`, `ping_timeout` | Q4 | Names differ at plan time; any name works if lock test + doc table move together |
| A2 | Proposed regex triggers for security/data/irreversible | Q8 | Over/under-triggering; held-out fixtures at plan time decide (CONTEXT D-07) |
| A3 | Module and CLI subcommand names (`ping-lanes`, `check-fold-step`, `size-review`, `classify-disagreements`, `lanes.json`) | Q3-Q9 | Cosmetic; SKILL.md and tests move together |
| A4 | jev confidence threshold 0.80 (`lane_order.STABLE_TOP` precedent) for "confident" | Q7 | Owner may want a different bar; reversible, one constant |
| A5 | `Approved (partial)` suffix form does not break parsers/tests that look for `### Status: Approved` exactly | Q5 | Check by `rg "Status: Approved"` in tests and references at plan time before fixing the form |
| A6 | Judge-lane pings reuse the review ping command; judge-only referee lanes are not in the owner's `[lanes]` | Q6 | The "judge round" clause could need a judge-specific adapter; see O1 |
| A7 | Fold check keyed to the profile id `superpowers` plus archetype `plan` | Q9 | A non-profile-detected superpowers plan would be missed; the orchestrator already resolves the profile |

## Open Questions

1. **O1: What exactly is the "judge round" a ping must precede?**
   - Known: the judge loop is `tools/judge_loop.py` with scratch drivers; it has its own probe and never imports `ai_kit_spec` (Q6).
   - Unclear: whether REV-07's "before a judge round" means the skill-judge loop's lanes (not spec-review lanes) or a spec-review round that follows a fixer edit.
   - Recommendation: implement the ping as a subcommand with `--reviewers-json`; name it in the phase's judge plan as the pre-round probe, and record the clause as satisfied for review rounds (fixer-pass rounds) with the judge-loop use documented as an orchestrator step. Owner confirmation advised (PROVISIONAL-adjacent).
2. **O2: The partial header and its merge with `Failure`.** When both lanes fail the merge must not print `Approved`; confirm the plan-time choice: both failed -> `### Status: Failure — <lanes>` as today (exit 1) with "not reviewed" in the Step 5 line.
3. **O3: `--pool` for pings and for flagged-lane dispatch only, or for every lane with a pool?** D-04 says flagged lanes; the runner's pool key can also derive from a pooled catalog row (`blockedPoolKey`, `cross-ai.mjs:4061-4068`). Recommendation: pass the lane's own `pool` field whenever it has one (flagged or not), since the clear-on-ok rule depends on it; confirm the owner is fine with pooled-but-unflagged lanes clearing records.
4. **O4: Per-ping timeout default.** The probe's own limit is 30 s (`quota.py:253`). Recommendation: default `PING_TIMEOUT_S = 30` configurable in the subcommand and seam; three lanes concurrent cost at most 30 s.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `node` | `--blocked-status` read, runner | not probed here (read-only research) | tested floor Node 24 per SKILL.md:228-229 | missing node -> blocked read returns none, lane never blocked (D-05) |
| jev client (`jev-fast-decision`) | classify, size | not probed | - | absent -> today's path (all jev paths) |
| `uv`, `pre-commit`, `shellcheck` | `make test`, hooks | not probed | pinned by `uv.lock` | n/a |

Step 2.6 note: no external service is needed; everything runs on stdlib with fakes.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | `unittest` through `tools/run_unittest_parallel.py` (one subprocess per module; groups `unit`, `unit-uv`, `integration`, `e2e`, `arch`) |
| Config file | none (groups are sets in `tools/run_unittest_parallel.py`) |
| Quick run command | `python3 tools/run_unittest_parallel.py tests.<module> [tests.<module> ...]` |
| Full suite command | `make test` (unit, integration, e2e incl. `bash tests/test_install.sh`, arch) |

### Phase Requirements -> Test Map (new modules named `[ASSUMED]`; one new unit module per slice)
| Req | Behavior | Test type | Automated command | File exists? |
|-----|----------|-----------|-------------------|-------------|
| REV-07 R3 | reason list lock + doc table == `REASONS`, non-vacuity | unit | `python3 tools/run_unittest_parallel.py tests.test_ai_kit_spec tests.test_ai_kit_spec_runtimes_table tests.test_lane_failure_text` | extend `test_ai_kit_spec.py:3483`; new `test_lane_failure_text.py` Wave 0 |
| REV-07 R2 | concurrent ping, replacement by key, stale/fresh at TTL+-1 s, no lane left, dedup, ping_timeout | unit (fake probe, fake clock) | `python3 tools/run_unittest_parallel.py tests.test_lane_ping` | Wave 0 |
| REV-07 R4 | partial report, judged-lanes line in roster order, not reviewed, survivors merge, all-clean not partial | unit | `python3 tools/run_unittest_parallel.py tests.test_review_log tests.test_ai_kit_spec` | Wave 0 (+ edit merge-reports tests) |
| REV-01 R1 | flagged+quota switches; unflagged/transient/crash do not; blocked pool skipped, equal time passes, once after; adjacency/ordering/empty | unit | `python3 tools/run_unittest_parallel.py tests.test_lane_switch tests.test_lane_settings tests.test_role_orders tests.test_ai_kit_spec_runner_dispatch tests.test_runner_flags` | Wave 0 |
| REV-01 `--blocked-status` | wrapper parse, no-node, malformed, bad exit; one real-node case | unit (+skip if no node) | `python3 tools/run_unittest_parallel.py tests.test_lane_switch tests.test_runner_describe` | Wave 0 |
| REV-01 doc | narrowed hard rule pinned; old blanket wording fails | unit (doc contract) | `python3 tools/run_unittest_parallel.py tests.test_lane_failure_text tests.test_quota_policy_text tests.test_cross_ai_skill_text` | Wave 0 |
| REV-02 R5 | classes route as written, low -> owner, CRITICAL stays, no jev, empty -> no call, payload recorded | unit (fake `run`) | `python3 tools/run_unittest_parallel.py tests.test_jev_review tests.test_catalog_jev_names` | Wave 0 |
| REV-06 R6 | signals at each trigger and none; jev one lane; outside roster discarded; no jev same count | unit | `python3 tools/run_unittest_parallel.py tests.test_review_signals tests.test_jev_review` | Wave 0 |
| REV-08 R7 | fixture pair (with/without step), non-superpowers never, empty, case/checkbox | unit | `python3 tools/run_unittest_parallel.py tests.test_fold_check` | Wave 0 (+ wording pin vs adapter SKILL.md) |
| JDG-04 R8 | evals shape, text history, frontmatter, dogfood | unit | `python3 tools/run_unittest_parallel.py tests.test_skill_evals_shape tests.test_skill_text_history tests.test_skill_frontmatter tests.test_ai_kit_spec_review_checklist tests.test_ai_kit_spec_review_fixer tests.test_check_dogfood` ; `make check-dogfood` | exists |
| Arch | rules 8, 9, 11, cross-skill reach, hardcoded models | arch | `python3 tools/run_unittest_parallel.py tests.test_arch tests.test_arch_hardcoded_models` | exists |
| E2E keep green | spec-review CLI and runner | e2e | `python3 tools/run_unittest_parallel.py tests.test_ai_kit_spec_e2e tests.test_cross_ai_runner_e2e` | exists |

### Sampling Rate
- Per task commit: the module(s) of that slice (the commit-stage `staged-tests` hook runs the covering modules).
- Per wave merge: `python3 tools/run_unittest_parallel.py --group unit` plus `--group arch`.
- Phase gate: `make test` and `make check-dogfood` green before verify.

### Wave 0 Gaps
- [ ] `tests/test_lane_ping.py`, `tests/test_lane_switch.py`, `tests/test_review_log.py`, `tests/test_jev_review.py`, `tests/test_review_signals.py`, `tests/test_fold_check.py`, `tests/test_lane_failure_text.py` (new, join the `unit` group automatically; each ends with the main guard, rule 12)
- [ ] Fixtures: fake lane tables (placeholder model names), a superpowers plan pair under `tests/fixtures/`, held-out signal fixtures
- [ ] Update `tests/test_ai_kit_spec.py:3483-3490` and the merge-reports tests (`3660-3715`, `4452-4478`) in the same commits as the code
- [ ] Arch: extend only by adding rules with non-vacuity counterparts if any new structural rule is added (AGENTS.md); no baseline edits

## Security Domain

| ASVS Category | Applies | Standard Control |
|---------------|---------|------------------|
| V2 Authentication | no | - |
| V4 Access Control | no | lane switches stay inside the owner's roster (tested) |
| V5 Input Validation | yes | pool string validated by `POOL_RX` before argv; blocked-status stdout matched by anchored regex; lane keys opaque strings; jev answers accepted only when in `criteria` |
| V6 Cryptography | no | - |
| V7/V9 data protection | yes | summaries only to jev; run `secret_shapes.redact` on every text field; no code, diff, file content, config values or secrets in payload (recorded-payload test) |

| Threat | STRIDE | Mitigation |
|--------|--------|------------|
| Hostile reviewer text steering a jev item | Tampering | bounded printable-ASCII summaries (`jev_names._clean` pattern), criteria keys only |
| Prompt text leaking via status stderr | Info disclosure | quote only evidence lines per existing Step 1 rules; never pass document bodies to jev |
| Switch to a lane outside the roster | Elevation | selection only from `selectable_lanes("review", ...)`; tested |
| Shell injection through pool/key | Tampering | argv lists, `POOL_RX` fullmatch, rule 8 |
| Runaway ping threads | DoS | per-ping timeout, runner kills its group at its deadline |

## Sources

### Primary (HIGH: files read this session)
- `skills/ai-kit-spec-review/{SKILL.md,ai_kit_spec/{lane_settings,error_classifier,quota,runner_dispatch,reviewer_dispatch,review_reports,jev_names,lane_order,skill_classify,role_orders,cli,config_io,detection,tooling_guidance}.py,references/cross-ai.mjs,evals/evals.json}`
- `skills/ai-kit-spec-review-checklist/SKILL.md`, `.../frameworks/superpowers.md`; `skills/ai-kit-spec-execute-superpowers/SKILL.md:108,288-290`, `references/fold-step.md`, `references/resolution-stops.md`
- `tests/{test_arch,test_ai_kit_spec,test_ai_kit_spec_runtimes_table,test_quota_policy_text,test_skill_evals_shape,test_skill_text_history,test_runner_describe}.py`, `tools/{judge_loop,run_unittest_parallel}.py`
- `.planning/judge/REJUDGE.md`; `.planning/phases/39.2-*/39.2-09-PLAN.md`, `39.2-10-PLAN.md`; `.planning/ROADMAP.md:1061-1078`; `.planning/REQUIREMENTS.md:308-318`; 29-CONTEXT D-03

### Secondary / Tertiary
- None (no web search needed; no network used).

## Project Constraints (from CLAUDE.md and AGENTS.md)

English only in every artifact; runtime code stdlib-only; atomic config writes (`tempfile.mkstemp()` + `os.replace()`); results never shown with more certainty than their sourcing (mark PROVISIONAL items);
SKILL.md changes pass the `skill-judge` loop (<= 3 rounds, <= 3 findings fixed without re-review); no machine absolute path in skill text, tests or fixtures; one logical, buildable commit with tests and docs;
`make test` before done; explore with codebase-memory-mcp then `rg`; new dev dependencies need a check against stdlib; never use real config files as fixtures; leave no scratch files outside `tmp/`; local shell rules
(one simple command per call, no `cd`, no heredocs, no command substitution, scripts in `tmp/`) bind every executor and must be passed word for word to subagents.

## Metadata

**Confidence breakdown:** standard stack HIGH (all in-repo, read this session); architecture HIGH (CLI/SKILL.md flow confirmed); pitfalls HIGH (found in code and tests); jev thresholds, trigger regexes and names MEDIUM/`[ASSUMED]`.
**Research date:** 2026-11-25 · **Valid until:** until `skills/ai-kit-spec-review/` changes (re-read `merge-reports`, `REASONS` and `runner_dispatch.py` before planning).
