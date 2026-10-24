# Phase 25: Quota-aware cross-AI subprocess supervision - Research

**Researched:** 2026-10-24
**Domain:** Node runner template (`cross-ai.mjs`, template 6) pattern matching, wait/resume state machine, Python dispatch glue, three skills
**Confidence:** HIGH on in-repo facts and on the CLI behavior probed locally; MEDIUM on cursor and claude (no probe possible); LOW on router-env recovery times

## Summary

Phase 25 is no longer planned "against contracts": Phases 18 and 18.1 are complete (ROADMAP "Phase 18: ... (completed 2026-10-16)", "Phase 18.1 ... (completed 2026-10-17)"). The runner template exists at `skills/ai-kit-spec-review/references/cross-ai.mjs` (3060 lines, template 6, 115 named self-test cases) and the dogfood `.planning/scripts/cross-ai.mjs` is a rendered copy of it, not a TRANSIENT/FATAL prototype. Phase 25 therefore edits the template (bump to 7), re-renders the dogfood copy, and amends the Python glue that already half-anticipates it (`error_classifier.STATUS_TO_REASON` already maps `quota_wait`, `billing_or_access`, `capacity`).

The most valuable new evidence is a set of **local mock-HTTP probes** of the installed CLIs (no credential, no real model, no paid call): a stdlib Python server returned canned 4xx bodies while codex, pi and opencode ran in a throwaway config dir. It answers four of the seven deferred research questions (codex stdout field, pi stderr/JSON shape, opencode exit behavior, other reset forms) and **contradicts two CONTEXT premises**: opencode 2.0.31 does not emit `error.name`/`error.data.*`, and its structured `error.type` cannot outrank text because `provider.auth` wraps billing 401/403 errors. Cursor cannot be mocked (Connect/protobuf endpoint) and stays unverified.

Everything the planner needs for sizing: six plans, all runner plans strictly sequential (one shared 3000-line file), each 2-3 tasks, no sleeping test anywhere (time comes from back-dated state files and a pure `--classify-only --now` mode).

**Primary recommendation:** Build the matcher and state machine as pure functions inside the template, drive them from one fixture file through `--classify-only`, change `finish()`'s dirty-tree demotion deliberately (R6), and pass the route kind to the runner as a flag (`--route-<cli>`), because Python-dispatched calls run the unrendered template where `CONFIG.routerBacked` is empty.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
D-01..D-24 in `25-CONTEXT.md` `<decisions>` are locked and are **not restated here** (reference by number). Premise drift against HEAD is reported in section 1; none of it reopens a decision, but D-03 (structured type first), D-04 (opencode event shape), D-05 (route baked into CONFIG) and D-19 (`git diff --stat`) each need a refinement the planner must carry (see 1.2).

### Claude's Discretion
- Grace period length, the probe prompt text, the exact JSON schema field names, the fixture file layout.

### Deferred Ideas (OUT OF SCOPE) / routed research questions
Answered in this document: codex `codex_error_info` on stdout (no), opencode exit after final error event (yes, immediately), pi stderr and `--mode json` shape, other reset forms, `CronCreate` one-shot. Still open: cursor channel, `ScheduleWakeup` outside `/loop`, scheduled fire during a pending GSD choice, router-env recovery time (section 6).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| QTA-01 | Per-CLI pattern table, verified/unverified, route-aware classes | Section 2 (table), 1.2 (route flag), Pitfalls 1-5 |
| QTA-02 | Live and post-hoc detection feeding the closed reason and status line | 3.2, Pitfalls 3, 4, 6; `runOnce`/`runChild` seam |
| QTA-03 | 10 min / 4 h wait, resume only unfinished work, policy in runner and three skills | 3.3-3.6, plans 25-03..25-05 |
</phase_requirements>

## Project Constraints (from AGENTS.md)

Runtime code stdlib-only (the runner is one Node file using only `node:` modules; Python side stdlib). State/config writes atomic (`mkstemp` + replace) and JSON writes reuse `cache_write_json`. No diagnostic more certain than its sourcing (hence the `verified|unverified` pattern label). Any new/changed SKILL.md passes skill-judge (>= 96/120, no regression). One logical commit per task with tests+docs; never `--no-verify`. No absolute machine paths in source/tests/plans. `make test` and `make validate` green; new e2e module must be added to `E2E_MODULES` in `tools/run_unittest_parallel.py` (or extend `tests/test_cross_ai_runner_e2e.py`, already listed). Parallelism: never hardcode workers. Amend REQUIREMENTS/ROADMAP formally when a verified fact contradicts them. Update READMEs/nested docs with the feature. English only.

## 1. Drift report: CONTEXT premises vs HEAD

### 1.1 Stale premises (no decision change)

| # | CONTEXT/SPEC premise | HEAD reality | Source |
|---|---|---|---|
| S1 | D-20, `<domain>`: 16.1/18/18.1 contracts "specified but not yet built"; SPEC "Current code: prototype runner has only `TRANSIENT` and `FATAL`" | Built and complete. The template has seven classes and a closed status table. `grep TRANSIENT\|FATAL` in the dogfood copy returns nothing. | [VERIFIED: skills/ai-kit-spec-review/references/cross-ai.mjs:116-148] ROADMAP lines for Phases 18, 18.1 marked `[x]` |
| S2 | D-13/code_context: `cache.cache_write_json` "uses a fixed `.tmp` suffix, so D-13 needs 16.1 D-22's mkstemp" | Already mkstemp: `fd, tmp = tempfile.mkstemp(dir=parent, suffix=".tmp")` then `os.replace` | [VERIFIED: skills/ai-kit-spec-review/ai_kit_spec/cache.py:28-40] |
| S3 | SPEC/D-20: `dispatch.write_resumable_state` | `dispatch.py` is gone (18.1-18). `write-resumable-state` is a CLI subcommand in each skill package backed by `write_resumable_state_fn: ... = cache_write_json` | [VERIFIED: skills/ai-kit-spec-execute-gsd/ai_kit_spec_gsd/cli.py:70,361-363] |
| S4 | D-21 "closed reason set gains `billing_or_access`", "`capacity` is added" | Already in `REASONS` and `STATUS_TO_REASON` (`"quota_wait": "quota"`, `"billing_or_access": "billing_or_access"`, `"capacity": "capacity"`, also a forward `idle_stall` the runner never emits) | [VERIFIED: skills/ai-kit-spec-review/ai_kit_spec/error_classifier.py:16-26,30-55] |
| S5 | code_context: opencode v2.0.29, codex 0.162.1 | Installed now: opencode v2.0.31, codex-cli 0.162.1, pi 1.3.0, cursor-agent 2026.10.22-27dcf5f, claude 2.1.302, node v24.21.0 | [VERIFIED: `--version` runs this session] |
| S6 | canonical_refs: GSD step at `~/.claude/gsd-core/...elaboration.md` | There is no user-level GSD install (project memory, and the path does not exist). Same text lives at `.claude/gsd-core/workflows/execute-phase/detail/elaboration.md`: prompt built from the plan at 84-87, `run-with-timeout "${CROSS_AI_TIMEOUT}"` at 99, retry/skip/abort at 118-120 | [VERIFIED: that file, read this session] |
| S7 | SPEC R6/R7 speak of `tree=clean\|dirty` only | The runner also emits `tree=unknown` (non-git cwd or git failure). Treat `unknown` like `dirty` for R6 (never fall back over unknown edits). | [VERIFIED: cross-ai.mjs:5-8 header comment, `treeLabel` 499-502] |

### 1.2 Premises that need a refinement the planner must carry

1. **Dirty-tree demotion contradicts R6.** `finish()` ends with the line `if ((action === 'fallback' || action === 'retry-later') && tree !== 'clean') action = 'stop';` (cross-ai.mjs:219), and two self-test cases pin the result: `status=quota ... tree=dirty action=stop` (1774) and the router-billing twin (1781). R6 wants "dirty: wait and resume the same CLI's session". Required change: a `quota_wait` with `tree != clean` keeps `action=retry-later` but means "resume same CLI/session only; no fallback" (the Python ladder and the runner's own multi-candidate loop must read `tree` before choosing a fallback). Both self-test regexes and `18 D-27`'s "Neither another CLI nor a later retry may run over edits" comment must be amended in the same commit. `fallback` over a dirty tree stays forbidden.
2. **Route kind cannot be "baked into CONFIG at render" for the Python paths (D-05).** `routerBacked` is a per-CLI boolean fed from the catalog's `is_router` (`plan_edit.py:213` `router = bool(row.get("is_router"))`, `cross_ai.py:84`), and only rendered project runners carry it. `ai-kit-spec-review`/`-execute*` run the **unrendered template** with default `"routerBacked": {}` (`build_runner_argv(spec, runner_path, node)` uses `resolve_cross_ai_template_path`, flags from `runner_flags`, which has no route flag) [VERIFIED: runner_dispatch.py:157-197, cross-ai.mjs:60-91]. Recommendation: add `--route-<cli> router|unknown` (Python passes `router` iff the confirmed `fallback_quota`, per D-05; absent = unknown); the runner upgrades `unknown` to `direct` only through the D-06 prefix list. Flag tokens are `[A-Za-z0-9-]`, so `HOOK_TOKEN_RE` accepts them. For rendered project runners keep a per-model map in CONFIG (`routeKinds: {cli: kind}`) and let the flag win. The curated-config plan schema (`router_backed`, `plan_io.py:799-853`) maps to it without a schema change if `true -> "router"`.
3. **D-04's opencode event shape is wrong for the installed version.** SPEC amendment says `{"type":"error",...,"name":"APIError","data":{"message":...,"statusCode":429}}`. opencode v2.0.31 emits `{"type":"error","sessionID":...,"error":{"type":"provider.quota","message":"The usage limit has been reached","status":429,"response":{"body":"<provider JSON as a string>"}}}` [VERIFIED: local mock probe, section 2.2]. The matcher must read `error.type`/`error.message`/`error.status`/`error.response.body` **and** the older `error.name`/`error.data.*` (the installed range is not pinned). `parseOpencode` today does `JSON.stringify(ev.error||ev).slice(0, 400)` (cross-ai.mjs:370-382), which can truncate before the body; the new matcher must receive fields, not the stringified blob.
4. **D-03's "structured error type/code first" is unsafe for opencode's own `error.type`.** In the probe, `provider.auth` wrapped a 403 spending-limit, a 401 `MonthlyLimitError` and a 403 `Model access is disabled`, while `provider.quota` wrapped a 402 `requires an opencode API key`. A type-first rule would make the router's monthly limit `auth`/69 (exactly what D-03 set out to prevent). Refinement: structured **vendor** codes (`usage_limit_reached`, `insufficient_quota`, `FreeUsageLimitError`, `MonthlyLimitError`, `ModelDisabledError`, `GoUsageLimitError`, found in `error.response.body` or a pi `<status>: {...}` body) are matched as text at the "structured/billing" tier; opencode's `provider.*` type and `status` are only a **weak hint** used after text, before bare codes. Keep D-03's overall order otherwise.
5. **D-19 "done work = `git diff --stat` paths" misses new files.** `git diff --stat` ignores untracked files. The runner already snapshots with a temp index and `git add -A` + `write-tree` (cross-ai.mjs:735-792), so `state.tree` begins with a tree object id that persists in the object DB. Use `git diff-tree -r --name-status <first_tree> <current_tree>` (current tree from a fresh snapshot) plus `git log --format=%h\ %s <first_head>..HEAD`. It covers untracked, modified and deleted paths in path order (SPEC R7 ordering edge). Objects are unreachable but survive default gc grace.
6. **R2 exit semantics for dirty `quota_wait`.** SPEC says `quota_wait` exits 75 with `action=retry-later`; keep it, including dirty. `billing_or_access` stays 69 and its `action` is `fallback` when clean, `stop` when not (unchanged demotion for `fallback`).
7. **Status rename ripple.** `quota` -> `quota_wait` and `billing` -> `billing_or_access` change the status-line values pinned by `STATUS_TABLE` (cross-ai.mjs:140-141), self-test regexes (1727-1781), Python fake status lines (`tests/test_ai_kit_spec_runner_dispatch.py:302-309,772-798` use `status="quota"`) and e2e fakes (`tests/test_cross_ai_runner_e2e.py:422,515`). `STATUS_TO_REASON` already keeps both spellings, so Python tests with a hand-built `quota` line keep passing; the e2e fakes and self-tests must move to the new names.

## 2. Per-CLI quota / limit / billing pattern table

Label legend. **verified** = produced by the installed CLI in a probe this session, or recorded verbatim from a live run in a committed planning document (source cited). **unverified** = reported in CONTEXT/SPEC/memory without a captured artifact on disk, or inferred from vendor source. Probe method (all three CLIs): a stdlib Python HTTP server on localhost answered every POST with a canned status and JSON body; the CLI ran with a throwaway config dir (`CODEX_HOME`, `PI_CODING_AGENT_DIR`, `XDG_*` + `OPENCODE_CONFIG_CONTENT`) and a dummy key. No real config, credential or model was touched. What the probe proves is **how the installed CLI formats and where it prints** a given upstream error; it does not prove the real vendor sends that body.

### 2.1 codex (codex-cli 0.162.1) - stdout JSONL, exit 1, stderr empty

| Pattern (verbatim) | Channel | Class (route unknown) | Label | Evidence |
|---|---|---|---|---|
| `{"type":"error","message":"You’ve hit your usage limit. Upgrade to Pro (https://chatgpt.com/explore/pro), visit https://chatgpt.com/settings/usage to purchase more credits or try again at 2:24 PM."}` followed by `{"type":"turn.failed","error":{"message":"<same>"}}` | stdout events | `quota_wait`, reset parsed | verified (CLI text; upstream body assumed from codex source) | probe, HTTP 429 body `usage_limit_reached` with `resets_at` = now+5400 s on a -03:00 host rendered `2:24 PM` |
| same, no reset in body: `... or try again later.` | stdout | `quota_wait`, no reset | verified | probe |
| dated: `You’ve hit your usage limit. Try again at Dec 31st, 2099 9:00 PM.` | stdout | `quota_wait`, reset parsed (ordinal suffix) | verified | probe (`resets_at` far future) |
| `Quota exceeded. Check your plan and billing details.` (body `insufficient_quota`) | stdout | billing text tier -> `billing_or_access` on direct/unknown, `quota_wait` on router | verified text | probe |
| `unexpected status 402 Payment Required: <body>, url: <url>` | stdout | bare code, `billing_or_access` (route rules) | verified format | probe |
| `Failed to refresh token: ... refresh token was already used` / `refresh_token_reused` 401 | stderr/stdout | `auth` | verified-recorded | `01.2-02-SUMMARY.md` (live), project memory 2026-09-14 |
| `"codex_error_info":"usage_limit_exceeded"` | private rollout only | none | **absent on stdout** | probe: no such key on `exec --json` (answers deferred Q1) |
| `{"type":"item.completed","item":{"type":"error","message":"Model metadata for ... not found..."}}` | stdout | **never a limit** (non-terminal warning item) | verified | probe; the current `codex.parse` only reads top-level `error`/`turn.failed` and must stay that way |

Facts that shape code: the apostrophe is **U+2019** (`You’ve`), not `'`, so the table normalizes `’ -> '` before matching (SPEC fixtures with `'` would pass while the real message fails). The terminal event is `turn.failed`; a plain `error` precedes it. Treat `turn.failed` as the kill/terminal signal and a bare `error` as record-only (a stream-reconnect `error` that does not end the turn is not proven absent: Open Question 1).

### 2.2 opencode (v2.0.31) - stdout events with `--format json`, exit 1, stderr empty

Probe (isolated XDG dirs, `openai` provider `baseURL` pointed at the mock):

| Upstream (mock) | opencode event `error.*` | Time to event | Class to produce |
|---|---|---|---|
| 429 `usage_limit_reached` "The usage limit has been reached" (+`resets_at`/`resets_in_seconds` inside `response.body`) | `type=provider.quota`, `status=429` | 0.5 s | `quota_wait`, reset from body epoch |
| 429 `insufficient_quota` "You exceeded your current quota, please check your plan and billing details." | `provider.quota`, 429 | <1 s | billing text -> route rule |
| 429 `FreeUsageLimitError` "Rate limit exceeded. Please try again later." | `provider.quota`, 429 | <1 s | direct (Zen): known cap wording -> `billing_or_access` (D-07); else `quota_wait` |
| 402 "requires an opencode API key" | `provider.quota`, 402 | <1 s | router tail: `quota_wait` (D-08); direct: `billing_or_access` |
| 401 `MonthlyLimitError` "Your workspace has reached its monthly spending limit" | **`provider.auth`**, 401 | <1 s | router: `quota_wait` (D-08); direct: `billing_or_access` |
| 403 "Error 403: spending limit reached for this team" | **`provider.auth`**, 403 | <1 s | `billing_or_access` (router: `quota_wait`) |
| 403 `ModelDisabledError` "Model access is disabled" | **`provider.auth`**, 403 | <1 s | direct: `billing_or_access`; router tail: `quota_wait` |
| 401 "Incorrect API key provided" | `provider.auth`, 401 | <1 s | `auth` / 69 |
| 429 `rate_limit_exceeded` | `provider.rate-limit`, 429 | **85.9 s** | `quota_wait` (retried silently first) |
| 529 `overloaded_error` | none within 60 s | >60 s | `capacity` only after the CLI gives up (unverified end) |

[VERIFIED: local mock probe 2026-10-24]. Two consequences. (a) Retryable errors produce **no error event and only repeated `step_start` events** (gaps 1.6, 4.2, 8.1, 9.3, 8.9, 12, 10.8, 9.4, 10.8 s), so a 30 s probe or a short `--timeout` ends as `timeout`, not as a limit (Pitfall 5). (b) The process exits at once (exit 1) after the final error event, so a live kill adds nothing for opencode's terminal errors (answers deferred Q4).

Recorded (not re-probed): text-mode `Error: The usage limit has been reached` on `openai/gpt-5.6-sol`, retried 20 min later with the same result [VERIFIED-recorded: `01.1-REVIEWS.md`]; router `Error: Service temporarily unavailable due to resource pressure. Retry shortly.` (capacity) [same file]; xai `APIError 403 personal-team-blocked:spending-limit "You have run out of credits or need a Grok subscription."` 2026-09-14 [VERIFIED-recorded: project memory `project_opencode_xai_billing_block`]. **Note the hyphen: the current `billing` regex `spending limit` would not match `spending-limit`** (use `spending[ -]limit`). Router errors `Chat admission capacity is temporarily unavailable`, `402 requires an opencode API key`, `all targets were skipped by pre-dispatch filters`, `Credential gate blocked opencode-zen/...` [VERIFIED-recorded: `16-HANDOFF.md:118-135`]. Zen `Model access is disabled` 403 (2026-10-14), Go `Insufficient account funds`, router `[401]... MonthlyLimitError` "12 live hits": **unverified** (CONTEXT-reported; the wrapper shape was reproduced, the vendor text was not seen on disk).

### 2.3 pi (1.3.0)

| Pattern | Channel | Class | Label | Evidence |
|---|---|---|---|---|
| `429: {"type":"insufficient_quota","code":"insufficient_quota","message":"You exceeded your current quota, please check your plan and billing details."}` format `<status>: <JSON body>` | **stderr**, exit 1, stdout empty (`-p` text mode, the runner's formula) | text tier | verified | probe |
| `402: {"type":"monthly","message":"x"}` | stderr, exit 1 | bare code | verified format | probe |
| `403: {"type":"FreeTierError",...}` | stderr | billing/access | verified-recorded | `15-pi-live-tests.md` (cited by `18-REVIEW.md:314`) |
| `Warning: No project session found with id '<uuid>'; creating a new session with that id.` | stderr | **never a limit** (first `--session-id` use) | verified | probe |
| `You have hit your ChatGPT usage limit (plus plan). Try again in ~N min.` (relative reset!) | stderr | `quota_wait`, reset = now + N min | **unverified** (read from pi's bundled source, not observed) | [CITED: installed pi bundle `openai-codex-responses` chunk, `friendlyMessage`] |
| `subscription_sharing_usage_limit_exceeded`, `GoUsageLimitError`, `FreeUsageLimitError`, `Monthly usage limit reached`, `available balance`, `out of budget` | stderr | non-retryable limit/billing wording | unverified (pi's own non-retryable list) | [CITED: pi bundle `NON_RETRYABLE_PROVIDER_LIMIT_ERROR_PATTERN`] |
| a `zai-coding-cn/glm-5.3` weekly limit "resets 2026-10-21" | stderr | **currently misclassified `capacity`** (status line shows `status=capacity ... elapsed=146s`) | message text not recorded | `18.1-one-runtime-model/skill-judge/*-pi-glm-5.3-xhigh-postreview.md` line 5-7 |

pi retries a retryable 429 three times internally (4 POSTs, a few seconds) before printing; terminal-limit words (`insufficient_quota`, `billing`, `quota exceeded`) stop its retries [VERIFIED: probe + CITED bundle]. `--mode json` would exit **0** with `stopReason:"error"` and `errorMessage` inside `message_end` events (verified), so do not switch pi to JSON mode for detection. `--session-id <uuid>` reuses the session across processes in the same project/cwd: the second run's request still contained the first prompt [VERIFIED: probe].

### 2.4 cursor (agent 2026.10.22) - unverified channel

| Pattern | Class | Label | Evidence |
|---|---|---|---|
| `ActionRequiredError: You've hit your usage limit` | `quota_wait` (unknown route) / `billing_or_access` when the message carries the account-cap wording (D-07 `Spend Limit`) | verified text, **unverified channel and exit code** | `01.2-02-SUMMARY.md` (live), `01.2-RESEARCH.md` row "Free-plan usage limit exhausted" |
| `ActionRequiredError: Named models unavailable`, `Free plans can only use Auto` | `billing_or_access` (plan gate), not `auth` | unverified | `16.1-RESEARCH.md` pitfall 3; CONTEXT specifics. 16.1 mapped `ActionRequiredError` to `auth`; D-03 says it alone is not an auth signal |
| `Cannot use this model: ...`, `Warning: The provided API key is invalid` | `bad_model`, `auth` | verified (stderr, exit 1) | `16.1-RESEARCH.md:260` live |
| error kinds in the shipped bundle: `RetriableError`, `ActionRequiredError`, `NonRetriableError`, `CancelledError` (message text is server-provided, not in the bundle) | structural hint only | verified | [VERIFIED: bundle `index.js` class declarations] |

Cursor speaks a Connect/protobuf protocol, so it cannot be mocked like the others; and a live run would call the real service. Keep D-10: stderr-only live detection flagged unverified. The `direct` prefix list for cursor named API models has **no evidence on disk**: ship it empty and unverified rather than guess.

### 2.5 claude (2.1.302, review-only, `resume: null`)

`Overloaded ... try again in a moment` (capacity) and `resets 9:30pm (America/Santiago)` are CONTEXT-reported from session logs: **unverified**. The installed binary contains `usage limit reached` inside its own error-pattern list and a `You've hit your limit` line composed by the client [CITED: strings of the installed binary], which fits but does not prove the stdout/stderr form `claude -p` prints. claude is a review lane only, so a wrong class costs a skipped lane, not edits.

### 2.6 Direct-route prefixes (D-06)

`opencode/` (Zen) and `opencode-go/` (Go) are real model-id prefixes [VERIFIED-recorded: `15-pi-live-tests.md` lists `opencode/big-pickle`, `opencode-go/glm-5.3-flash`]. Cursor: none (see above).

### 2.7 Reset-time forms observed (D-11, deferred Q7)

1. codex local clock, no date: `try again at 2:24 PM` (verified, local zone).
2. codex dated with ordinal: `Try again at Dec 31st, 2099 9:00 PM` (verified). Case differs between forms: match case-insensitively.
3. pi relative: `Try again in ~N min.` (cited, unverified).
4. claude: `resets 9:30pm (America/Santiago)` (reported).
5. **structured epoch**: opencode prints the provider body, which for the ChatGPT-subscription path holds `"resets_at": <epoch>` and `"resets_in_seconds"` [VERIFIED for the shape the mock supplied; real body assumed from codex/pi source]. Prefer this over text when present: it is zone-free.
Not times: `try again later`, `try again in a moment`, `Please try again later.`.

## 3. Where things belong in the runner

### 3.1 Table and matcher (R1, R2, D-01..D-03, D-06..D-08)

Replace `PATTERNS` + `classify(stderrText, structuredError)` (cross-ai.mjs:117-125, 389-398) with a second marked block `// <patterns>` already exists for exactly this: keep the markers, change the payload to a JSON document (D-02 asks for a block outside `// <config>`; the existing `<patterns>` markers sit outside it and inside the sha256 header). Proposed rows: `{id, cli|"*", input: "stderr"|"event", match: regex source, class, terminal: bool, label: "verified"|"unverified", evidence: "<doc ref>", scope: ["router"|"direct"|"unknown"]?}`. Order (pinned by a test): structured vendor codes and billing/access text, then quota text, then auth text, then weak hints from `provider.*`/`status`, then bare `\b402\b|\b401\b|\b429\b`.

A pure `classifyStop({cli, model, route, stderr, events, now}) -> {status, rule, pattern, resetAt}` (no I/O, no clock) is the whole matcher. Route is resolved first: flag -> prefix list -> `unknown`. Inputs are decoded UTF-8 with ANSI stripped (`normalize` already strips ANSI) and `’ -> '`.

Per-CLI event extraction (D-04, D-10), tolerant of both shapes:
- opencode: `type:"error"` events only: `error.type`, `error.message`, `error.status`, `error.response.body` (parsed for nested `error.type`/`error.message`/`resets_at`), plus legacy `error.name`/`error.data.message`/`error.data.statusCode`. Skip `text` parts.
- codex: top-level `error` and `turn.failed` only; skip `item.completed` (agent messages and warning items).
- cursor: the final `result` event when `is_error`; otherwise stderr only.
- pi/claude: stderr only.
Never match the answer text (SPEC R4, must-NOT): the answer is `parse().text`, which the matcher never receives.

### 3.2 Live and post-hoc detection (R4, D-09)

`runOnce` (cross-ai.mjs:828-843) already has per-chunk `onStdout`/`onStderr`. Add a line splitter per stream, feed complete lines to the per-CLI extractor, and on the first **terminal** signal record `{rule, class, resetAt}` immediately (so the 64 KiB `errTail` slice at line 840 cannot lose it), then after a short grace call `currentFinalize('limit')` (the closure `runChild` exposes through `currentFinalize`, which does SIGTERM -> grace -> SIGKILL of the process group). A new `reason` value must be added to `finalize` consumers (`'exit'`/`'timeout'`/`'signal'` are the only ones today). Post-hoc: on `r.timedOut` or non-zero exit with no live record, run `classifyStop` over the captured stderr tail and the events collected so far; with no signal a timeout stays `timeout` (SPEC R4 empty edge).

Honest value note for the planner: for the three probed CLIs the child exits by itself within a second of a terminal error, so the live kill matters only for a child that prints a terminal signal and then keeps running (or whose later output is slow). Implement it per R4, test it with a fake that does exactly that, and do not expect to see it fire against real opencode/codex/pi.

### 3.3 Reset parsing (R3, D-11)

One pure `parseReset(text, nowMs, tz)` returning epoch ms or null, in the template (the Node parser is canonical, D-24). Needs: 12-hour `h:mm AM/PM`, ordinal dates `Mon D(st|nd|rd|th), YYYY h:mm AM/PM`, trailing `(IANA zone)` via `Intl.DateTimeFormat` (Node 24 has full ICU; there is no zone-offset helper, so solve the offset by a two-pass `formatToParts` iteration), `in ~N min`, and a structured `resets_at` epoch (seconds) / `resets_in_seconds`. Rules: a clock time already past today -> tomorrow; a reset **exactly** 4 h after `first_seen` is inside the window and 4 h + 1 min is outside (SPEC R3 adjacency); outside -> `action=stop` with `reset_at` printed. Fixtures live in one JSON file consumed by both Node (`--classify-only`) and any Python caller (D-24). Tests set `TZ` on the child process; no sleeping.

### 3.4 State file and who owns it (R5, D-12..D-16)

State belongs to the runner (D-12). Location per D-13: `cache_base(env)/waits/<sha256(realpath(cwd))>/<task>.json`, where `cache_base` is `$XDG_CACHE_HOME or $HOME/.cache` + `ai-kit/spec` (cache.py:11-14); the template must re-implement that 3-line rule (it cannot import Python). Atomic write: `fs.mkdtemp`/`writeFileSync(tmp)` + `renameSync`; first creation with `{flag: 'wx'}` (exclusive) to refuse a second wait for one task. Task key sanitized to `[A-Za-z0-9._-]{1,64}` (path traversal). Fields (discretionary names, required content): `schema`, `cli`, `model`, `mode`, `route`, `session_id`, `session_kind` (`pi-preassigned|codex-thread|opencode-session|cursor-result|none`), `task`, `objective_digest`, `first_seen` (epoch s), `attempts`, `max_attempts` (24), `next_check_at`, `reset_at`, `first_head`, `first_tree`, `candidates_tried`, `status` (`waiting|ready|resolved|expired`). **No message text, no response body, no key**: the provider text may echo a masked key (real OpenAI errors do), so store only class, rule id and parsed reset. A sentinel-key test (SPEC prohibition 4) must scan state, status line and every runner stderr line.

Status line: add `reset_at=<ISO-8601 with offset, no spaces>`, `pattern=verified|unverified|none`, optionally `rule=<id>`. `parse_status_line` splits on whitespace (`runner_dispatch.py:200-207`), so values must contain no spaces; print the state **path** on a separate preceding `cross-ai:` log line, not on the status line (paths may contain spaces). `_trailer_counts` only reads `exit`, `cli`, `model`, so extra tokens are safe.

### 3.5 Wait policy as a state machine (R5, R6, D-15..D-17)

One pure `waitDecision(state, nowMs) -> refuse|probe|resume|expire|none`:
- `now - first_seen >= 4 h` or `attempts >= 24` -> `expire` (stop and report done/not-done). Cap comes from the file, never from memory. A test back-dates `first_seen`; no clock injection needed.
- `now < next_check_at` -> `refuse` (print `status=quota_wait action=retry-later` and the same `next_check_at`; exit 75; no probe, no attempt burned). This makes an early `CronCreate` fire or an impatient GSD "retry" free (the docs say one-shot jobs on `:00`/`:30` can fire up to 90 s early).
- due -> `probe` (D-15: `--mode review` read-only call, prompt text discretionary). Probe passes -> state `ready`, then `resume` in the same invocation when the caller supplied the prompt (the GSD retry path), else print `action=resume` hint and exit 0 for a Python caller that re-dispatches. Probe fails with a limit -> `attempts += 1`, `next_check_at = max(reset_at, now) + ... ` per R3 (first re-check at the reset time if inside the window, then every 600 s). Probe `timeout` (opencode silent retry) -> counts as one attempt and stays `waiting` (Open Question 5).
- Entry: the runner finds a pending state for `(realpath, task)` at start. GSD path: task unknown, so key = worktree and **confirm with `objective_digest`** (SHA-256 of the first `<objective>...</objective>` block of the stdin prompt, stored at first dispatch). Equal -> same task -> the retry GSD re-runs resumes automatically; different -> run normally and leave the state untouched. This implements D-14's intent without parsing PLAN.md files (GSD builds the prompt from the plan's `<objective>`, `elaboration.md:84-87`); flag the delta as an Open Question (6) since D-14 literally says "against the phase's PLAN.md files".

Fallback rule (R6, D-17, D-18): inside one run, on `quota_wait` with `tree=clean` and a next candidate in `--prefer`, continue to it and append the limited CLI to `candidates_tried` for a later re-check; with `tree != clean` (including unknown) stop at once with `action=retry-later`, keep the same CLI. A single-candidate call returns `retry-later` and the Python ladder applies R6 (D-17). The native session is never a candidate (D-18). Today's loop does not fall back on 75 at all (`tryNextCli` requires `action === 'fallback'`, cross-ai.mjs:400-402), so multi-candidate fallback-on-quota is new code.

### 3.6 Resume only unfinished work, per CLI (R7, D-19)

Today `retryArgv` (cross-ai.mjs:480-491) resumes in-process after a *transient* failure; Phase 25 needs it **across processes**, so the session id must be persisted. Mapping, with what was verified:

| CLI | Session id source | Resume argv (existing `RUNTIMES.*.resume`) | Verified this session |
|---|---|---|---|
| pi | pre-assigned `ctx.sid` (`crypto.randomUUID()`), passed as `--session-id`; persist it in state | same argv as the first run (`resume` just re-calls `RUNTIMES.pi[mode]` with the same sid) + `RESUME_MSG` as input | Yes: second process with the same `--session-id` and cwd carried the first prompt in its request; first use prints a stderr `Warning: No project session found...` (benign). Must run from the **same cwd** |
| codex | `thread.started.thread_id` from the first run's stdout | `exec resume [--dangerously-bypass-approvals-and-sandbox] --skip-git-repo-check -m <model> --json -o <file> <thread_id> -` | Yes: `exec resume <id> -` after a failed (limit) turn carried the first prompt. Sandboxed exec (`--codex-sandbox`) deliberately takes a fresh run (`retryArgv` comment "resume's sandbox flag is not verified"): use the done-work prompt there |
| opencode | `sessionID` field present on every event (`parseOpencode`) | `... --session <id>` | Yes: `--session <id>` carried the first prompt; `--session ses_doesnotexist123` is accepted (creates), confirming create-if-absent |
| cursor | `session_id` only in the final `result` event of `--output-format json` | `... --resume <id>` | **No.** On a live-killed or timed-out cursor there is no id, so the done-work prompt path is the normal case. Channel/exit unverified |
| claude | n/a | `resume: null` | review-only; a limit just skips the lane |

When no id was captured (cursor, sandboxed codex, any CLI killed before its first event) the resume prompt is built from the state: original prompt unchanged if the tree is clean (SPEC R7 empty edge) else the original prompt plus a block "Already done: commits <first_head>..HEAD, changed paths (path order)" from `git diff-tree --name-status` (file names and statuses only, never contents; idempotent because it is recomputed from `first_tree`, never appended to itself). `first_head`/`first_tree` are written once and never re-snapshotted (D-19).

## 4. Plan decomposition (cheap cross-AI executor, 2-3 tasks per plan, 3600 s, commit per task)

All runner plans edit one file, so they are **strictly sequential** (`depends_on` chain; no parallel wave touches `cross-ai.mjs`). Every task ends with its fixture/test green and one commit. The Node self-test takes up to 180 s (`TestRunnerTemplate.test_self_test`); tasks run the targeted subset first (`--classify-only`) and the full self-test once per plan.

- **25-01 Pattern table and matcher** (wave 1)
  1. Table JSON block + `classifyStop` pure function + route resolution (flag, prefix list), replacing `PATTERNS`/`classify`; `’`/ANSI normalization; `spending[ -]limit`.
  2. `--classify-only <fixture.json> [--now <epoch>]` mode (reads `{cli, model, route, stderr, events}`, prints one JSON line, no side effects) and `skills/ai-kit-spec-review/references/quota-fixtures.json` seeded with section 2 (every row has `expect.class`, `expect.pattern`); table-order pin test.
  3. `STATUS_TABLE` rename (`quota_wait`, `billing_or_access`), exit/action per R2, `finish()` demotion change (1.2 item 1), status-line `pattern=`/`rule=`; move the pinned self-test regexes (1727-1781) and Python e2e fakes.
- **25-02 Reset time and live/post-hoc detection** (wave 2, after 25-01)
  1. `parseReset` + `reset_at` token + 4 h window rule; reset fixtures (same-day, dated, relative, zoned, none; boundary +/- 1 min).
  2. Line-splitting live watcher in `runOnce`, terminal-signal record, grace + `currentFinalize('limit')`, post-hoc classification on timeout/partial exit.
  3. Self-test fake modes: `limit-mid` (prints a terminal line then keeps running), `limit-then-timeout`, `answer-only-limit` (limit phrase only in answer text), `retry-notice` (never kills); status-line assertions.
- **25-03 State file and wait/resume machine** (wave 3, after 25-02)
  1. State module: path derivation, task-key sanitizing, `wx` exclusive create + tmp/rename, schema, secret-free; sentinel-key test.
  2. `waitDecision` + the re-entry path (objective digest, `refuse`/`probe`/`resume`/`expire`), `--recheck` for Python callers, cap from file.
  3. Resume builder: persisted session ids per CLI, done-work block from `first_tree`, clean-tree original prompt; multi-candidate fallback on clean (R6) and same-CLI stop on dirty/unknown.
- **25-04 Python glue** (wave 4, after 25-03)
  1. `RunnerSpec.route` + `runner_flags` (`--route-<cli>`, `--task`), resolution from catalog `fallback_quota` (default `infer_fallback_quota`, `model_catalog.py:28-43`), unit tests with the existing `RunnerSeams` fakes.
  2. Parse the new status tokens (`reset_at`, `pattern`, `rule`), extend `RunnerResult`/dispatch payloads; ladder rule R6 in `execute_dispatch`/`reviewer_dispatch`/superpowers `dispatch_injection` (the hourly-wake wording at `dispatch_injection.py:117-154,232,405` and its tests `tests/test_ai_kit_spec_superpowers.py:575-784`).
  3. `TEMPLATE_VERSION = 7` (`cross_ai.py:46`), re-render the dogfood `.planning/scripts/cross-ai.mjs` through `ensure-runner`, curated-config `router_backed -> routeKinds` mapping and `runner.md`/`SKILL.md` runner docs.
- **25-05 Skills and policy reference** (wave 5, after 25-04)
  1. `skills/ai-kit-spec-review/references/subprocess-quota-policy.md` (D-23) + `ai-kit-spec-review` SKILL.md lane waiting policy and `pending` merge (D-22).
  2. `ai-kit-spec-execute-gsd` SKILL.md: replace the `CronCreate` hourly block (lines 133-160) with the one-shot chain; `GSD` retry-prompt behavior.
  3. `ai-kit-spec-execute-superpowers` SKILL.md (39,158-183), `references/state-management.md` (63,99-101), `escalation.md` (83); a text test asserting no hourly-wake instruction remains for subprocess limits.
- **25-06 Amendments, skill-judge, full gate** (wave 6, after 25-05)
  1. Formal amendments: `REQUIREMENTS.md` QTA-01 text, `ROADMAP.md` Phase 25 SC2/SC4, 18 D-27, 18.1 D-12, 16.1 D-13, README/rows; `STATE.md` untouched.
  2. `/skill-judge` on the three SKILL.md (one clean-context native Opus judge + opencode router-env judge per project memory), evidence committed.
  3. `make test` and `make validate` green; leave no untracked files; record the deferred cursor/host rows.

## 5. Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | `unittest` (stdlib) driven by `tools/run_unittest_parallel.py`; Node runner `--self-test` (hermetic fake CLIs, 115 named cases today) |
| Config file | `tools/run_unittest_parallel.py` (`E2E_MODULES` already lists `tests.test_cross_ai_runner_e2e`) |
| Quick run command | `node skills/ai-kit-spec-review/references/cross-ai.mjs --classify-only <fixture>` and `python3 -m unittest tests.test_ai_kit_spec_runner_dispatch` |
| Full suite command | `make test` then `make validate` |

### Phase Requirements -> Test Map
| Req | Behavior | Test type | Automated command | File exists |
|-----|----------|-----------|-------------------|-------------|
| QTA-01 / R1 | every Background message is a fixture with expected class; unverified reported in `pattern=`; structured beats text; empty stderr -> `crash`; `\b402\b` vs `4021`; table order pinned | e2e via `--classify-only` over `quota-fixtures.json` | `python3 -m unittest tests.test_cross_ai_runner_e2e.TestQuotaFixtures` | Wave 0 (new class, file exists) |
| QTA-01 / R2 | route x message matrix (router, direct, unknown) incl. billing on router vs direct; exit 75/69 exact | same fixtures, route field | same class | Wave 0 |
| QTA-03 / R3 | reset same-day, dated, relative, zoned, none; +/-1 min at 4 h boundary; past time -> tomorrow (set `TZ`) | e2e `--classify-only --now` | `...TestResetParse` | Wave 0 |
| QTA-02 / R4 | fake prints a terminal line mid-run -> early stop `status=quota_wait`; fake times out after a limit line -> same; limit phrase only in answer -> not a limit; retry-notice line does not kill | self-test cases + e2e | `node ... --self-test` and `...TestLiveDetect` | Wave 0 |
| QTA-03 / R5 | exit 75 -> state file -> re-check still limited (attempts+1, `next_check_at`) -> re-check succeeds; cap from a back-dated `first_seen`; second wait refused (`wx`); resolved state is a no-op | e2e with fake CLI whose behavior flips via a marker file | `...TestWaitState` | Wave 0 |
| QTA-03 / R6 | clean + candidate falls back; dirty (and unknown) waits; at exactly 4 h stops with report | e2e (git temp repo, fake CLIs) | `...TestFallbackOrWait` | Wave 0 |
| QTA-03 / R7 | partial edits -> resume prompt lists paths (incl. untracked); clean -> original unchanged; double resume does not duplicate; fallback never reuses another CLI's sid | e2e capturing the fake CLI's stdin | `...TestResumePrompt` | Wave 0 |
| QTA-03 / R8 | no hourly-wake text for subprocess limits in the three skills; `subprocess-quota-policy.md` linked; skill-judge evidence | unit text test + judge reports | `python3 -m unittest tests.test_quota_policy_text` | Wave 0 |
| Prohibition: no key in outputs | sentinel key in env/body absent from state, status line, stderr | e2e | inside `TestWaitState` | Wave 0 |

### Non-vacuity
Every negative has a paired positive that proves the matcher can fire: the answer-only phrase fixture is paired with the same phrase on stderr (must classify); the "table order pinned" test also asserts a deliberately reversed table changes a fixture's class (mutation check run in-test on a copy); "unverified is reported" is paired with a verified row. Follow the `tests/test_arch.py` `TestArchNonVacuity` precedent.

### Sampling Rate
- Per task commit: `--classify-only` fixtures plus the touched unit module.
- Per plan: runner `--self-test` once.
- Phase gate: `make test` and `make validate` green before `/gsd-verify-work`.

### Wave 0 Gaps
- [ ] `skills/ai-kit-spec-review/references/quota-fixtures.json` (shared Node/Python fixtures; seeded from section 2 verbatim, apostrophe as U+2019 for codex)
- [ ] `--classify-only` mode in the template (no side effects, `--now`)
- [ ] fake-CLI modes: `limit-mid`, `limit-then-timeout`, `answer-only-limit`, `retry-notice`, `flip-after-marker`
- [ ] `tests/test_quota_policy_text.py` (auto-joins the `unit` group)
- No framework install needed (stdlib + existing node).

## Pitfalls

1. **Curly apostrophe.** Real codex text is `You’ve` (U+2019). Fixtures typed with `'` hide a total miss. Normalize and keep one fixture per variant.
2. **Hyphenated wording.** The recorded xai block is `spending-limit`; the current regex needs `spending limit`. Use `spending[ -]limit`; `free ?tier` and `\b402\b` stay.
3. **Non-terminal "error" shapes.** codex `item.completed` with `item.type:"error"` (model-metadata warning) appears on every run; pi prints a session `Warning:`; opencode shows many `step_start` events. None may classify. Only top-level `turn.failed`/`error` (codex), `type:"error"` (opencode), final `result` with `is_error` (cursor) count.
4. **Structured type is a hint, not a verdict** (opencode `provider.auth` wraps billing). Order text above type (1.2 item 4).
5. **opencode retries silently** (~86 s before an error event for a retryable limit, none within 60 s for 529). A 30 s probe or short inner timeout reads `timeout`. Decide the probe's behavior on `timeout` (Open Question 5) before coding the state machine.
6. **64 KiB stderr tail** drops an early terminal line; record at first sight. Also stdout is buffered whole in `runChild` (`outChunks`), so a chatty child is only memory-bounded by its own output.
7. **`parse_status_line` splits on spaces.** New tokens must be space-free; the state path goes on its own log line.
8. **Existing pins.** Self-test regexes at cross-ai.mjs:1727-1781 and Python e2e fakes pin old status names and `tree=dirty action=stop`; they change in the same commit as the code (a stale pin is a false green).
9. **Python-dispatched route.** Without `--route-<cli>`, a router billing error exits 69 in review/execute flows because `routerBacked` is `{}` in the unrendered template. A test must drive the Python path, not only the rendered runner.
10. **Sleeping in tests.** Never wait for 10 minutes or 4 hours. Time inputs: back-dated `first_seen`/`next_check_at` written by the test, `--now` on pure modes, `TZ` env for zone cases, millisecond grace for the live kill. Any `sleep` over a second in a new test is a defect.
11. **Scheduler semantics.** One-shot `CronCreate` is supported ("whether it recurs or fires once") but is session-scoped, 1-minute granularity, can run up to 90 s early on `:00`/`:30` (so schedule off those minutes and let `refuse` absorb an early fire), fires only between turns, and a one-shot whose time passed while the session was not running is not restored on `--resume` [CITED: code.claude.com/docs/en/scheduled-tasks]. Whether it fires while a GSD choice prompt is pending is undocumented. The state file's `next_check_at` is the recovery path (Phase 26 reads it, D-24).
12. **Cross-cwd resume.** pi sessions are keyed by project/cwd; resume must run from the same worktree, which the realpath-keyed state already enforces.
13. **Secrets.** Provider errors can echo a masked key; never persist or print message text in the state file or status line (existing stderr relay of the child's own output is unchanged).
14. **File size.** The template is already ~3060 lines; add pure functions in one contiguous section with their own banner so the self-test and sha header stay reviewable.

## Don't Hand-Roll

| Problem | Don't build | Use instead | Why |
|---|---|---|---|
| Atomic state write | custom lock files | tmp file + `renameSync`; first create with `{flag:'wx'}` | AGENTS.md atomic-write rule; mirrors `cache_write_bytes` |
| Time-zone conversion | a manual offset table | `Intl.DateTimeFormat(..., {timeZone}).formatToParts` | DST-correct, no dependency |
| Process-group kill | new signal logic | existing `killGroup`/`currentFinalize` | already budgeted against `run-with-timeout`'s 3 s SIGKILL |
| Tree comparison | `git status` parsing | existing `treeState` (temp-index `add -A` + `write-tree`) and `git diff-tree` | includes untracked, already hardened |
| Scheduling in the runner | `setTimeout`/sleep for hours | exit 75 at once; host one-shot job | SPEC R5; GSD wraps the call in `run-with-timeout` |
| Regex-per-source drift | a Python copy of the table | read the status line (D-01) | one matcher |

## Runtime State Inventory (status rename)

| Category | Items found | Action |
|---|---|---|
| Stored data | `quota.json` entries carry `reason` (`quota`, `auth`, ...) written by `probe_reviewer_quota`; values unchanged (`quota_wait` maps to `quota`) | none; add `billing_or_access`/`capacity` readers already present |
| Live service config | none | none |
| OS-registered state | session-scoped `CronCreate` hourly wakes from the old skills (vanish with the session) | none; new chain replaces them |
| Secrets/env vars | none (no key stored by design) | sentinel test |
| Build artifacts | rendered project runners in other projects are template 6 (pristine -> upgraded by `ensure-runner`; edited -> `.new` file); the dogfood `.planning/scripts/cross-ai.mjs` is tracked and stamped | re-render dogfood in 25-04; document the `.new` merge in `runner.md` |

## Architectural Responsibility Map

| Capability | Primary | Secondary | Rationale |
|---|---|---|---|
| Pattern table, matcher, reset parse | Node runner (template) | - | only component on both call paths (D-01) |
| Live kill, post-hoc classify | Node runner | - | owns the child process group |
| Wait state, cap, resume prompt | Node runner | - | GSD path has no Python at run time (D-12) |
| Route kind from catalog | Python (`ai_kit_spec`) | runner prefix list | catalog is user-confirmable (D-05) |
| Ladder fallback (single-candidate calls) | Python dispatch | - | D-17 |
| Scheduling the re-check | host orchestrator (Claude Code one-shot jobs) | state file | D-16; other hosts print the resume step, flagged unverified |

## Standard Stack and Package Legitimacy

No external package is installed: Node `node:` built-ins (`child_process`, `fs`, `crypto`, `os`, `path`, `url`, `Intl`) and Python stdlib only. Dev tooling is unchanged (`ruff`, `pylint`, `pyright`, `vulture`, `shellcheck`). Package Legitimacy Audit: **not applicable, no packages**. A new dependency would breach the stdlib-only rule.

## Environment Availability

| Dependency | Required by | Available | Version | Fallback |
|---|---|---|---|---|
| node | runner, all Phase 25 tests | yes | v24.21.0 | tests skip when absent (existing pattern `_real_node_executable`) |
| git | tree compare | yes | system | tests skip when absent |
| codex / opencode / pi / cursor-agent / claude | probes only; tests use fakes | yes | 0.162.1 / 2.0.31 / 1.3.0 / 2026.10.22 / 2.1.302 | none needed; no real model call in any test |

## Security Domain

| ASVS | Applies | Control |
|---|---|---|
| V5 Input validation | yes | task key `[A-Za-z0-9._-]`, route flag enum, fixture JSON parsed not evaluated, regex run on at most 64 KiB, no user regex |
| V7 Error/logging | yes | no key, token, body or message text in state/status/log (sentinel test) |
| V8 Data protection | yes | state under the user cache dir, mode 0600 file / 0700 dir, never in the work tree |
| V12 Files | yes | `wx` create + rename, no follow of a pre-planted symlink (`lstat` the final path) |

Threats: path traversal via task key (Tampering), symlink race on the state path (Tampering), secret echoed by provider text (Information disclosure), unbounded wait loop (DoS; mitigated by file-held 4 h / 24-attempt cap), ReDoS on the table (bounded input, simple alternations, review each regex).

## State of the Art

| Old | Current | Impact |
|---|---|---|
| `TRANSIENT`/`FATAL` regex pair (prototype) | 7 classes + closed `STATUS_TABLE` (template 6) | Phase 25 extends, does not replace |
| opencode `error.name/data` (1.x) | `error.type=provider.*`, `status`, `response.body` (2.0.31) | accept both |
| hourly `CronCreate` in two skills | one-shot chain from `next_check_at`, runner-owned state | R5/R8 |

## Assumptions Log

| # | Claim | Section | Risk if wrong |
|---|-------|---------|---------------|
| A1 | The real ChatGPT/codex backend sends `usage_limit_reached` with `resets_at` in the 429 body (taken from codex/pi source, mocked here) | 2.1, 2.7 | reset parsing falls back to text forms, which are verified |
| A2 | Cursor limit text goes to stderr and exit is non-zero under `-p --output-format json` | 2.4 | live detection misses; post-hoc on stdout `result` still works if A2 is stdout |
| A3 | claude `resets <time> (<zone>)` grammar exactly as CONTEXT reports | 2.5, 2.7 | one fixture wrong; claude lane only |
| A4 | A bare codex `error` event can precede a recoverable reconnect (so only `turn.failed` is terminal) | 2.1 | an early kill if wrong direction; chosen the safe direction |
| A5 | git keeps the unreachable tree objects long enough (default gc grace) for `diff-tree` on `first_tree` | 3.6 | resume prompt falls back to commits-only list |
| A6 | `ScheduleWakeup` usable outside `/loop` | 6 | CronCreate chain used instead (documented, supported) |

## 6. Open Questions

1. **codex reconnect events.** Can a top-level `error` event appear and then be followed by a successful turn (stream retry)? Probe could not produce it. Recommendation: terminal = `turn.failed` only; a bare `error` is recorded, never kills. Confirm on the next real codex failure with a retry.
2. **cursor channel, exit code and `session_id` on a limit** under `-p --output-format json`: not mockable (Connect protocol) and a real run needs the live account. Recommendation: ship stderr-only live detection plus stdout `result.is_error` post-hoc, both flagged unverified; Phase 21 owns the real check (D-10).
3. **Real vendor bodies.** Does the real ChatGPT-subscription 429 carry `resets_at`/`resets_in_seconds` and does opencode print it in `error.response.body` as the mock did? Recommendation: prefer the structured epoch when present, fall back to text forms.
4. **pi weekly-limit text** (`zai-coding-cn`) is currently classified `capacity`; the exact message was not saved. Recommendation: add a fixture the first time a real pi limit message is captured; until then the generic pi non-retryable words (2.3) cover it as unverified.
5. **Probe timeout semantics for opencode.** Retryable limits are silent for ~86 s, longer than D-15's 30 s probe. Options: per-CLI probe timeout (opencode 120 s), or treat a probe `timeout` on a waiting state as "still limited, attempt consumed". Recommendation: the second (no new knob), plus record `probe_timeouts` in state; planner to confirm with the user since it deviates from the literal `--timeout 30`.
6. **D-14 objective match.** Store an `<objective>` digest from the first dispatch instead of parsing PLAN.md files at re-entry. Same intent, less coupling to GSD's file layout; needs a one-line amendment to D-14.
7. **Scheduler unknowns:** `ScheduleWakeup` outside `/loop` (undocumented), and whether a due one-shot fires while a GSD retry/skip/abort choice is pending (docs: fires between turns only). Alternative primitive worth a spike note for Phase 26: a background shell wait with `Monitor`. Recommendation: D-16 as locked (one-shot `CronCreate` chain, off-hour minutes), other hosts print the resume step flagged unverified.
8. **Router-env recovery time.** Only uz's estimate ("minutes to a couple of hours") exists; the 4 h cap encodes it. No data to improve it.
9. **`direct` list for cursor named API models** has no evidence; shipped empty.

## Sources

### Primary (HIGH)
- `skills/ai-kit-spec-review/references/cross-ai.mjs` (template 6): `PATTERNS` 116-126, `STATUS_TABLE` 128-148, `finish` 208-230, `RUNTIMES` 256-340, `classify` 389-398, `retryArgv` 480-491, `runChild` 539-617, `treeState` 735-792, `runOnce` 828-843, `runCli` 853-914, `main` 2861-3060.
- `skills/ai-kit-spec-review/ai_kit_spec/{error_classifier,runner_dispatch,cache,model_heuristics}.py`, `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/{cross_ai,cross_ai_script,plan_edit}.py`, the three SKILL.md files, `.claude/gsd-core/workflows/execute-phase/detail/elaboration.md`.
- Local mock-HTTP probes of codex 0.162.1, pi 1.3.0 and opencode v2.0.31 (scratch under `tmp/`, removed afterwards; recipe in section 2).
- Committed planning evidence: `01.1-REVIEWS.md`, `01.2-02-SUMMARY.md`, `16-HANDOFF.md`, `16.1-RESEARCH.md`, `18-REVIEW.md`, `18.1-*/skill-judge/*pi-glm-5.3*`, `21-SKILL-JUDGE.md`; project memory notes `project_opencode_xai_billing_block`, `project_quota_recovery_by_route`.

### Secondary (MEDIUM)
- code.claude.com/docs/en/scheduled-tasks (one-shot vs recurring, 1-minute granularity, jitter, idle-only firing, resume behavior).
- Installed pi bundle source (friendly usage-limit message, retry lists); installed cursor-agent bundle (error kinds); installed claude binary strings.

### Tertiary (LOW)
- CONTEXT-reported messages with no artifact on disk (router `[401]` MonthlyLimitError "12 live hits", Zen `Model access is disabled`, Go `Insufficient account funds`, claude `resets 9:30pm (America/Santiago)`).

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH, no packages.
- Architecture: HIGH for runner placement (code read end to end around the seams); MEDIUM for the multi-candidate fallback and entry-point re-entry design (new code, no precedent).
- Pitfalls: HIGH for the probed CLIs; MEDIUM for cursor/claude.

**Research date:** 2026-10-24
**Valid until:** 2026-11-07 (opencode and pi change error shapes between minor versions; re-probe before planning if the installed versions move)
