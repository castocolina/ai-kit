---
phase: "25"
cycle: 1
reviewers: ["opencode router-env/my-referee-one", "opencode router-env/my-referee-two", "claude opus (claude -p, plan mode)", "opencode router-env/my-plan-review (ponytail)"]
---

# Phase 25 plan reviews, cycle 1

## referee-one (verbatim)

## Summary

The plans follow the owner’s later decision in the main design: one CLI per runner call, a runner-owned retry ladder, and no automatic cross-CLI fallback. The runner plans are serialized, and wave 8’s Python and skill work has no declared file overlap. **They are not ready for unattended execution yet.** The largest gaps are timeout handling, quota-cycle bounds, secret-bearing stderr, and an automatic model-change path left in the superpowers skill.

This was a read-only review of the plans and local source. I checked the `<automated>` blocks with `bash -n`; that establishes shell syntax only, not that their assertions will pass. I ran no suite, AI CLI, network call, or vendor probe.

### 25-01

**Strengths:** Removes the runner’s `tryNextCli` loop and tests that failures do not spawn a second CLI.

**Concerns:**
- **HIGH — `25-01-PLAN.md:225–240`, Task 1:** The proposed `reviewOnly = cands.find(...)` still examines *every* menu entry before selecting the first. An exec request for `--prefer pi,claude` can be rejected because `claude` is review-only, even though only pi was chosen. This conflicts with the locked **Owner decision** that the remaining entries are only a menu. Validate the selected entry alone; add that combination to the matrix.

### 25-02

**Strengths:** One labelled pattern table, structured-event fixtures, and an answer-text exclusion test address the classifier’s principal risks.

**Concerns:**
- **HIGH — `25-02-PLAN.md:293–298`, Task 1:** The sentinel key is written literally into the plan and is to be copied into the fake. The request requires synthetic sentinels to be assembled at run time, not stored as literals. More importantly, the current `runOnce` relays child stderr through `log(d.toString('utf8'))` (`cross-ai.mjs:828–843`); checking only composed `cross-ai:` and `AIKIT-XAI` lines does **not** establish “no key in any runner log.” Build the sentinel at test run time and test the complete captured evidence stream, or explicitly distinguish unavoidable raw child stderr from safe composed evidence.
- **MEDIUM — `25-02-PLAN.md:14–18,224–379`:** The estimated 120,000-token, low-confidence two-task plan combines the table, extraction, integration, many fixtures, and a mutation test in one 3,600-second unattended run. Split the fixture expansion from the matcher/integration work, with a green self-test at each boundary.

### 25-03

**Strengths:** A no-spawn classify mode and a parity test give Python a way to exercise the shipped Node matcher without duplicating it.

**Concerns:**
- **HIGH — `25-03-PLAN.md:263`, Task 1 acceptance:** The single-quoted shell `printf` does not preserve the intended JSON escapes. It produces `..."stderr":"429: {"type":"insufficient_quota"}"...`, which `json.loads` rejects. I reproduced the resulting bytes locally. Use a quoted here-document or generate the fixture with `json.dumps`.
- **MEDIUM — `25-03-PLAN.md:283–292`, Task 2:** The test specifies **seven** cases but asserts six output lines. Count them consistently and pin the expected names as well as the count.

### 25-04

**Strengths:** Terminal-only live killing, a timeout-with-partial-output case, answer-only negatives, and process reaping are well targeted.

**Concerns:**
- **MEDIUM — `25-04-PLAN.md:220–235`, Task 1:** The proposed post-hoc path uses the captured stderr tail and stdout events. A terminal line followed by more than 64 KiB of stderr is tested live, but a terminal *partial line* followed by a timeout and enough further output can disappear from the tail before post-hoc classification. Preserve the first matched signal across both live and post-hoc paths, and add a timeout/flood case.

### 25-05

**Strengths:** The call-count and session-ID cases pin 3 same-session retries plus 3 fresh sessions on the same CLI/model. The plan also protects review-mode permissions.

**Concerns:**
- **HIGH — `25-05-PLAN.md:249–269`, Task 1:** The owner’s transient list explicitly includes **timeout**, but this action maps only a classified `transient` row into `ladderNext`. Current `runCli` returns immediately on `r.timedOut` (`cross-ai.mjs:869–870`), and `main` finishes `timeout` (`:3004–3005`). Put child timeouts through the same bounded transient decision when the outer deadline permits; test a timed-out first attempt followed by success and by exhausted rungs. This contradicts the locked **Owner decision** if left as written.
- **MEDIUM — `25-05-PLAN.md:315–333`, Task 2:** `promptFiles` treats any `<files>` block in the prompt as authority to start a new full-permission session over edits. The real GSD prompt includes plan text, but this plan has not established that those blocks always identify the current task’s allowed paths. Bind the check to the dispatched task’s files, and test a changed path named only in another task’s `<files>` block.
- **MEDIUM — `25-05-PLAN.md:18–22,239–381`:** This low-confidence, 120,000-token plan includes the retry rewrite, dirty-tree policy, Python mappings, and several fake-CLI families. Separate the core ladder from the dirty-tree widening so each unattended run has a smaller, independently green deliverable.

### 25-06

**Strengths:** The plan specifies attempt evidence, off-router and auth stops, boundary cases, and a template-version pin.

**Concerns:**
- **HIGH — `25-06-PLAN.md:250–276`, Task 1:** The 4-hour check guards entry into a **next** cycle, not every attempt within that cycle. A cycle admitted exactly at the cap can run further attempts after it. Bound each wait and child attempt by the remaining quota cap as well as the runner deadline; test a cap reached mid-cycle. This contradicts the locked **Rule adjustment** and its “never loops forever” bound.
- **HIGH — `25-06-PLAN.md:153–162,250–276`, Task 1:** The proposed 600-second cooldown happens **inside one runner call**. The checked-in GSD cross-AI step defaults to `run-with-timeout` 300 seconds (`elaboration.md:74,96–100`), and the runner’s live timeout lookup also defaults to 300 (`cross-ai.mjs:436–472`). With that configuration the default cooldown cannot finish, despite the plan claiming router cycles will run. Specify how the orchestrator supplies a sufficient deadline, or report that no next cycle fits; test the default GSD configuration. Do not claim the 600-second cycle works on every rendered path.
- **HIGH — `25-06-PLAN.md:298–312`, Task 2:** The second sentinel again embeds a literal key in the plan. Its seven-attempt scan checks only prefixed lines, while the current runner relays raw child stderr. Use a runtime-built sentinel and assert exactly what output is safe; do not claim the entire log is secret-free from the proposed assertion.
- **MEDIUM — `25-06-PLAN.md:161–162,263–275`, Task 1:** Self-test copies set both cooldown and backoff to zero while allowing a second cycle. If a fake never recovers, elapsed wall time alone permits rapid repeated full cycles until the cap or deadline. Give tests an explicit small cycle bound or fake clock; pin exhaustion without real sleep or an unbounded process storm.
- **MEDIUM — `25-06-PLAN.md:18–22,241–359`:** Three substantial tasks, five files, a runner state machine, evidence changes, and a version bump are estimated at 120,000 tokens with low confidence. Move the version/pin work into a small sequential run, preserving the immediate 25-07 re-render barrier.

### 25-07

**Strengths:** Re-rendering the live dogfood supervisor is orchestrator-only and sequenced immediately after the template bump. The pristine-versus-edited check protects user changes.

**Concerns:**
- **MEDIUM — `25-07-PLAN.md:167–179`, Task 1:** The prose requires the rendered body outside CONFIG to equal the template and requires preservation of `models`, `outerTimeoutS`, and `routerBacked`. The automated check proves only pristine stamping, first preference, and presence of new keys. Add a comparison of the non-CONFIG body and those preserved CONFIG fields to the automated check before claiming either property.

### 25-08

**Strengths:** A seam keeps unit tests off the real catalog cache, and a real-runner e2e is planned for the confirmed route flag.

**Concerns:**
- **MEDIUM — `25-08-PLAN.md:226–239`, Task 1:** Catalog lookup requires an exact runtime `model_id` match. Existing routing strips cursor bracket, opencode `#variant`, and pi thinking suffixes before lookup (`routing.py:123–128`). A confirmed `fallback_quota: false` for the base model could therefore be missed for its selected variant, letting the runner infer `router-inferred` and retry quota against the user’s correction. Reuse `strip_model_suffix` for matching and test a confirmed false value with a variant.

### 25-09

**Strengths:** Removes the hourly subprocess wake, retains resumable-state data, and adds a shared policy reference and text tests.

**Concerns:**
- **HIGH — `25-09-PLAN.md:310–326`, Task 2:** It stops superpowers’ `"quota"` branch, but leaves `"real_error"` to the existing `BLOCKED` fix loop, including a **capability-escalated candidate** (`SKILL.md:310–312,331–340`). After a failed external run, that can automatically change model/provider; the new stop sentence and text test cover only quota. This contradicts the locked **Owner decision**. Separate task-review fix rounds after successful work from dispatch-failure handling, and stop for owner choice on every failed external dispatch.
- **MEDIUM — `25-09-PLAN.md:34–37,158–168`, Tasks 1–2:** Keeping automatic pre-dispatch candidate choice and rounds 4–5 escalation is labelled assumption A1, with owner confirmation deferred to C7 in 25-10. Since the owner says the catalog is a menu used when they name a lane, do not present A1 as settled policy before that confirmation; state the narrow existing pre-dispatch behavior and make any post-failure choice owner-controlled.

### 25-10

**Strengths:** Updates the review and curated-config surfaces, and treats live vendor observations as owner-only, unverified work.

**Concerns:**
- **MEDIUM — `25-10-PLAN.md:263–280`, Task 2:** “Every document” and “every rendered runner” following template 7 overstate upgrade behavior. `plan_runner_upgrade` keeps a pristine *current* runner and writes `.new` rather than replacing an edited older runner (`cross_ai_script.py:242–265`); `runner.md:36–46` also describes edited older runners that can remain ready. Explain that only newly rendered or successfully upgraded active copies have the ladder, and tell the user to inspect the active header rather than a `.new` file.

### 25-11

**Strengths:** Reserves skill-judge calls and final gates for the orchestrator, records owner-only facts as pending, and plans formal amendments to older decisions.

**Concerns:**
- **MEDIUM — `25-11-PLAN.md:193–217`, Task 1:** The automated check establishes that eight report files are nonempty and four skill names appear in the verdict document; it does not establish a PASS score, absence of critical/important findings, or no regression. Parse and check the recorded verdict and baseline comparison before claiming the `AGENTS.md` judge rule was met. A `BLOCKED` judge must leave the phase blocked, not satisfy the acceptance claim.
- **MEDIUM — `25-11-PLAN.md:257–277`, Task 3:** The gate command allows **5,400 seconds per command** and runs six commands sequentially. That is appropriate only for an orchestrator close-out, not a 3,600-second cross-AI run; retain the orchestrator-only guard and do not dispatch this plan to the unattended executor. Its `grep '## Phase status'` also does not prove the stated `human_needed` or C1–C7 results; check those explicitly.

## Overall Risk

**High until corrected.** The sequential template waves and no-second-CLI tests are a sound base, but the written implementation can still stop on a transient timeout without retrying, pass the quota cap during an admitted cycle, fail to fit a cooldown under GSD’s default timeout, and switch models after a superpowers dispatch failure. Fix those contract gaps and the concrete failing checks before unattended execution. The 25-08 and 25-09 wave-8 file sets do not overlap; the runner edits remain sequential.

Not checked: I did not run the plans, tests, skill judges, vendor CLIs, or live captures. No file or git state was changed.

CYCLE_SUMMARY: current_high=7 current_actionable=10

## referee-two (verbatim)

# Phase 25 Cross-AI Plan Review

## Summary

Reviewed all 11 plans against `25-SPEC.md`/`25-CONTEXT.md` (owner decision, Placement, Rule adjustment sections binding), `25-RESEARCH.md`, `25-VALIDATION.md`, `AGENTS.md`, and the actual code (template + dogfood runner, `ai_kit_spec` modules, curated-config package, tests, docs).

Verification depth: the worktree is at the phase base (`b99f3e5`, clean, plans unexecuted). I verified the template's `STATUS_TABLE`/`finish`/`tryNextCli`/`main`/`PATTERNS`/`classify`/`runCli`/`retryArgv`/`treeState`/`runOnce`/`runChild`/`RUNTIMES.*.resume`/self-test harness against every plan claim; the Python side (`parse_status_line`, `_trailer_counts`, `RunnerSpec`/`RunnerSeams`/`runner_flags`/`build_runner_argv`/`run_runner`, `error_classifier`, `model_heuristics._ROUTER_NAME_HINTS`, `model_catalog`, `cross_ai_script`, `TEMPLATE_VERSION`); `tools/run_unittest_parallel.py` (bare module args, exact `N/N modules passed` line); the dogfood runner (pristine template 6, CONFIG exactly as 25-07 claims); all doc/test baselines the gates grep for; and `make e2e-docker`.

Headline: **no HIGH findings**. The plans are unusually well-calibrated — every baseline count I checked (25-01's removed-literal counts, 25-06's 8 `template=6` hits, 25-09's CronCreate/hourly counts incl. the combined `dispatch_injection` 8-line figure, the ROADMAP stale phrase, the e2e `fake/capacity` `[600]` tier) is exact against HEAD. The owner's ladder is faithfully carried: no plan keeps or reintroduces cross-CLI fallback or a harness/provider/model switch; no test sleeps past ~1 s (`writeCopy` already defaults `backoffS: [0, 0]`); every verify command is runnable as written. The concerns below are hardening, not correctness blockers — two shared safety nits (sentinel literals written into plan files), one sizing risk, and small precision gaps.

### 25-01

**Strengths**
- Baseline calibration is exact: `tryNextCli` 2, `trying the next CLI` 3, `retry-later` 9, `action=fallback` 12, `action: 'fallback'` 8, `action: '...'` rows 20, `routerBacked[fields.cli]` 1, `"retries"` 1 — all verified against the template, so the gates genuinely fail on the unchanged tree and pass after.
- The single-CLI rewrite maps 1:1 to real code: `main`'s candidate loop with `continue` paths and `last`/`sawModel` bookkeeping, `STATUS_TABLE` actions, the demotion line in `finish()` (cross-ai.mjs:219), and the `--print-argv` loop that walks every entry — all verified.
- The "don't edit Python here" claim is proven: no Python code consumes `action=` (`parse_status_line` keeps tokens unused; `_trailer_counts` reads only exit/cli/model; the e2e test contains zero `action=` assertions).
- All 10 referenced self-test cases exist; every FAKE_MODE the matrix uses (`crash`, `quota`, `billing`, `auth`, `perm`, `empty`, `nochange`, `hang`, `review-edit`) exists; `not-installed-codex`/`bin-nocodex` provides the exact symlink pattern for `not-installed-first`.

**Concerns**
- LOW (Task 1, cross-ai.mjs:211/215): `finish()` computes `action = fields.action ?? row.action` and the router-billing rule writes `action = 'retry-later'`. The plan text covers the STATUS_TABLE field and the demotion line but not these two action writes; leaving `fields.action` live would let a future caller reintroduce a non-`stop` action invisibly. Fix: add one clause "finish ignores any `fields.action` override and always prints `action=stop`" (the router rule keeps only its exit-75 half until 25-02).

### 25-02

**Strengths**
- Carries the amended D-03/D-04 exactly: tier order (vendor codes → billing/access text → quota/rate-limit → auth/permission/bad-model → capacity/transient → `provider.*` hints → bare codes), both opencode event shapes, `provider.auth`-is-only-a-hint, `\b`-anchored codes, `spending[ -]limit`, U+2019 normalization, and the unverified-label policy with every research-flagged row explicitly listed as `unverified`.
- The status-line ripple is handled deliberately: every existing case regex ends `action=stop$` (verified, e.g. cross-ai.mjs:1681), and Task 1's `statusLineOk` truncation-before-regex plus tail-object is exactly the right fix; new tokens are space-free so `parse_status_line`/`_trailer_counts` are unaffected.
- The verify's Python parse of the `// <patterns>` JSON block is enforceable (markers verified present at 116/126); the mutation and idempotency pure cases give real non-vacuity; the fixture list maps 1:1 to RESEARCH §2 including the `kimi-429-router` and `[400]: event: error` rulings.

**Concerns**
- MEDIUM (Task 1 action text, and 25-06 Task 2): the sentinel key `<redacted-synthetic-key>` is written as a literal in the plan file. Synthetic sentinels must be composed at run time — a committed `sk-`-shaped literal in planning docs trips secret scanners and invites copy-paste. Fix: instruct the fake to build it at run time (e.g. `'sk-aikit-' + 'SENTINEL-' + Date.now().toString(36)`), keep only the harmless `sk-aikit-` prefix in the plan text, and have the check scan for the composed value.
- LOW (Task 1): this is the largest single-commit template edit of the phase (table + matcher + extractors + status tail + 4 fakes + 3 cases) at `confidence: low`; a single 3600 s unattended pass may not land it. Mitigation already exists (per-task commits, orchestrator re-dispatch under the ladder); consider naming the task's own smoke order (`--classify-only` subset first) explicitly.

### 25-03

**Strengths**
- `ROUTER_HINTS` parity is against the real tuple (`("router", "-env", "local-llm")` — verified identical to `model_heuristics._ROUTER_NAME_HINTS`), the `--model-<cli>` `slice(8)` precedent exists, and the doctored-template non-vacuity mirrors the existing `TestStatusMapDrift` pattern (verified).
- Verify commands are exactly runnable: bare module args to `run_unittest_parallel.py` are supported (`modules = argv` when no `--group`), the `1/1`/`2/2 modules passed` strings are the tool's literal output, and the e2e module is correctly run under `uv run`.
- Good test triads: `route-config` / `route-flag-wins` / `route-heuristic` / `route-flag-bad` pin the precedence chain, and `classify-only-fixtures` prevents shipped-mode vs in-process drift.

**Concerns**
- None found above nit level. (Verified: the dogfood's `router-env/my-coding` really does resolve `router-inferred` via the "router" hint once 25-07 lands, and `--route-pi unknown` correctly overrides a true `CONFIG.routerBacked` — the enum design is coherent end to end.)

### 25-04

**Strengths**
- Interfaces match the code exactly: `runOnce`'s chunk callbacks and 64 KiB `errTail` (cross-ai.mjs:828-843), `runChild`'s `finalize(reason)` kill sequence, `KILL_GRACE_MS = 2000` (1500 ms grace fits), `STICKY_FAKE`/`deadCheck`, and the codex fake's existing `fake-ok-codex`/`fake-retry-codex` listing.
- Ruling Q1 (bare `error` never kills; only `turn.failed` with limit text) is pinned in both directions, and the `limit-partial` (no trailing newline) → post-hoc-only case is a genuinely clever split of live vs after-the-fact paths. The honest value note from RESEARCH §3.2 is carried forward.

**Concerns**
- LOW (Task 1, case `live-limit-kill`): the case asserts `ctx.elapsedMs < 15000`, but the harness's `ctx` today is `{tmp, repo, home, calls, pidFile, copy, env}` — no elapsed field. Fix: either add the field in the same task or (cheaper) parse `elapsed=<n>s` from the already-asserted `AIKIT-XAI` line.

### 25-05

**Strengths**
- The rung-1 availability matrix matches the verified `RUNTIMES.*.resume` formulas byte for byte (codex exec `resume` + bypass, codex review no-resume, pi same-sid, opencode `--session`, cursor `--resume`, claude null), and `canResume` correctly excludes sandboxed codex exec.
- The e2e tier change is exactly right: the current review row is `("fake/capacity", "capacity", "capacity", [600])` (tests/test_cross_ai_runner_e2e.py:425) — `[30]` makes the 60 s work guard stop after one attempt instead of really sleeping 30+60 s; `writeCopy`'s `backoffS: [0, 0]` default (cross-ai.mjs:996) keeps the new 7-call ladder cases fast.
- `STATUS_TO_REASON["transient"]` is required by the same commit as the template rename — `TestStatusMapDrift` (verified) enforces it, and the plan knows it.

**Concerns**
- MEDIUM (Task 1): the broadest cross-file single commit of the phase — template CONFIG/ladder rewrite, both argv helpers, 10 case updates, `error_classifier.py`, and 3 test modules including e2e rows — at 120k-token estimate, low confidence, one 3600 s pass. Fix: split Task 1's Python/e2e updates into the commit that follows the template commit (the orchestrator barrier re-runs gates either way), or accept and note the re-dispatch path explicitly.
- LOW (Task 1): rung-1 review resume deliberately replaces the in-code "review retry is a fresh run" rule (cross-ai.mjs:482-484) — sound and threat-modeled (T-25-12, mid-run check kept), but it's an interpretation of the owner ladder, not a quoted ruling. Fix: rewrite that comment in the same commit and add the interpretation to 25-10's C7 owner-confirmation list.

### 25-06

**Strengths**
- Cap/cooldown semantics implement the Rule adjustment faithfully with clamps and pure boundary cases; `writeCopy` defaults (`cooldownS: 0`, `capS: 0`) guarantee no real waits, and only `router-quota-second-cycle` raises `capS` (recovered fake, 9 calls, one cycle) — verified sleep-free by construction.
- Version rails check out: template line 2 is `template=6 sha256=UNSTAMPED`, `cross_ai.TEMPLATE_VERSION = 6`, the docstring/header say `(template v6)`, `_READY_TEMPLATE` is a floor of 3 (not the shipped version), and the 8 `template=6` literals across the two curated-config test modules is the exact baseline. Computing the literals from `template_version(<shipped>)` so the next bump needs no test edit is the right maintenance fix.
- `_upgrade_config` (verified: `{**template, **kept}`) means the re-rendered dogfood gains the new knobs while keeping its stray `retries: 2` — exactly what 25-10 documents.

**Concerns**
- MEDIUM (Task 2): sentinel literal `<redacted-synthetic-key>` again — same run-time-composition fix as 25-02.
- LOW (Task 1): cycles are bounded only by wall-clock cap + deadline; with `cooldownS: 0` and `capS > 0`, a never-recovering fake would spin 7-attempt cycles until the deadline. No written case triggers it, but a one-line clamp (e.g. max `ceil(capS / max(cooldownS, 60))` cycles, or cap total attempts) or a pure case pinning it would close the hole for future case writers.

### 25-07

**Strengths**
- Every precondition verified live: the dogfood is a pristine stamped template 6 (sha256 recomputes true), tracked in git, with CONFIG exactly as claimed (`prefer` pi/cursor/opencode, per-CLI models, `outerTimeoutS: 1800`, `routerBacked: {}`); `plan_runner_upgrade` will produce `change` (pristine + older → in-place, CONFIG kept); the curated package imports standalone for the verify's `PYTHONPATH` one-liner (empty `__init__`, stdlib-only modules).
- Orchestrator-only guard, the refuse-if-edited `.new` stop, and the no-dispatch-in-flight prohibition are all the right protections for replacing the live supervisor.

**Concerns**
- None above nit level. (The `--print-argv` "a run uses pi only" line it checks is added by 25-01 as planned.)

### 25-08

**Strengths**
- The seams are real and correctly named: `RunnerSpec` is a NamedTuple with all-defaulted tail fields (adding `route` last is safe), `RunnerSeams` matches the plan's field list exactly, `runner_flags`/`project_runner_command` verified unchanged so the GSD hook never carries `--route-`, and `run_runner`'s check-then-build order gives the exact insertion point.
- Catalog plumbing verified: `cache_catalog_path` → `<cache_base>/model-catalog.json` (matches the scratch `XDG_CACHE_HOME` layout), `split_catalog_meta` skips `_meta`, `heuristic_confirmed`/`fallback_quota` are real fields; the confirmed-only rule keeps heuristics visibly labelled (AGENTS.md sourcing rule).

**Concerns**
- None above nit level. The `RunnerSeams(` audit instruction is backed by reality (15 sites across 4 test modules — 1/3/6/5 — matching the plan's "known" two plus the rg sweep).

### 25-09

**Strengths**
- Every text baseline verified exact: CronCreate 4/6/2 and hourly 2/2/2/1/1 across the five skill files, the combined 8-line figure for `dispatch_injection.py`, 1 in `error_classifier.py`, and the `Retry Step 3 with the new injection` sentence (1 hit). Section anchors exist ("Host-specific steps":33, "Resumable state: writing it and scheduling the wake":61).
- The pointer block implements the Placement correction literally (3-4 lines, ≤100 chars, names `.planning/scripts/cross-ai.mjs`); the text test has real non-vacuity; `gen_test_groups.py` + staged Makefile/`.pre-commit-config.yaml` keeps `test_gate_scope` green.

**Concerns**
- LOW (Task 3): rewording the wake words in `tests/test_ai_kit_spec_superpowers.py` (13 lines today) is instructed but unenforced by any gate, and tests aren't scanned. Acceptable (tests aren't instructions), but have the SUMMARY list the remaining lines so the residue is a recorded decision, not drift.

### 25-10

**Strengths**
- All stale-text targets verified present exactly once (the prefer-order fallback sentence at SKILL.md:192, `template 6` in SKILL.md:202 and runner.md:1, `template-6` in README:45), so the gates are calibrated and will genuinely fire on the baseline.
- The owner-capture kit verify is a real parser (7 C1–C7 rows, exact `not run (owner)` suffixes, `--classify-only` and `<redacted>` required), and the safety prose (redact first, raw captures under `tmp/`, secret scan, executor never runs captures) satisfies the no-key-in-evidence prohibition.

**Concerns**
- None above nit level.

### 25-11

**Strengths**
- The ROADMAP gate phrase `10-minute / 4-hour wait-and-resume for cross-AI children` exists verbatim (ROADMAP.md:81, 1 hit) — the gate is calibrated, not vacuous; the three upstream CONTEXT files and their D-27/D-12/D-13 anchors exist; the judge precedent (23-18-PLAN.md) and `make e2e-docker` exist; the pass rule matches AGENTS.md's skill-judge rule, and `BLOCKED` (never a guessed pass) is the right terminal state for a failed judge lane.
- The edge-ledger (kept/adapted/superseded per criterion) is the correct formal record of the owner decision's supersessions.

**Concerns**
- LOW (Task 1): the automated verify checks report existence + skill names, not verdicts — PASS-rule enforcement lives only in `orchestrator_verify`/acceptance criteria. Since `UNRESOLVED`/`BLOCKED` are legitimate outcomes, this is defensible; adding `grep -c PASS` per skill to the barrier (already prose) would make it mechanical.

## Overall Risk

**Low-to-medium; no blocking findings.** The binding scope (owner decision + Placement + Rule adjustment) is implemented coherently across the chain: 25-01 removes the fallback, 25-05/25-06 build the 3+3/router-cycle ladder on one lane with same CLI+model, the skills stop and relay evidence, and everything the owner decision superseded (state file, waits, reset parsing, direct prefixes, pending merge, done-work list) is explicitly not built and gets recorded by 25-11. Ordering is sound (strict template chain 01→06, orchestrator-only 07 between the bump and the remaining dispatches, 25-10 after both wave-8 plans with zero file overlap between 25-08 and 25-09, 25-11 last). Sizing is plausible for 3600 s per plan thanks to per-task commits and `writeCopy`'s zero backoffs. The two shared safety nits (sentinel literals in plan text) and the 25-05 breadth are the only items I would fix before dispatch; everything else is polish.

CYCLE_SUMMARY: current_high=0 current_actionable=11

## claude-opus (verbatim)

## Summary

The 11 plans follow the binding owner sections: one CLI per call, a 3 + 3 transient ladder, router quota cycles under a 4-hour cap, auth stops, evidence lines, and the ladder in the runner template with a 3-4 line pointer. Every self-test case and fake mode they name exists in template 6, and the counts and test names they cite are correct. Five problems stop the plans as written:

- Until 25-07, the runner that supervises this phase's own runs still falls back to other CLIs.
- Each delegated plan really gets 1800 s, not the 3600 s the plans assume.
- Three runner plans break unit tests or golden files that are not in their `files_modified` or their verify steps.
- 25-11 uses a judge set the owner replaced on 2026-10-24.
- GSD's cross-AI step only sends `<objective>` and `<tasks>`, so the plans' `<interfaces>` and frontmatter never reach the executor.

### 25-01
**Strengths**
- Removes `tryNextCli` and every `continue` path. The removed-literal gate's baselines are correct (`tryNextCli` 2, `trying the next CLI` 3, `retry-later` 9, `action=fallback` 12).
- The no-second-CLI matrix covers every outcome class, from both `--prefer` and `CONFIG.prefer`.
- No Python test reads `action=`, so "do not edit Python tests" holds.

**Concerns**
- HIGH (run rule 1; affects 25-01..25-06): the live supervisor is template 6, with `cross_ai_command` = `node .planning/scripts/cross-ai.mjs` (no flags) and dogfood `prefer: [pi, cursor, opencode]` (`cursor: auto`, `opencode: router-env/my-coding`).
  - So a pi crash, auth, billing, bad_model or no_change on a clean tree falls back to cursor, then opencode, at full permissions.
  - That is exactly the automatic fallback the owner removed, active during this phase's own runs.
  - **Fix:** before dispatching 25-01, the orchestrator sets the hook to `... cross-ai.mjs --prefer pi` (template 6 honors it) and puts it back after 25-07.
- MEDIUM (Task 1, "keep the router billing exit-75 rule as it is"): that rule sets `action = 'retry-later'` (template:214-216), but the gate requires `retry-later` to be absent. **Fix:** say "keep only `exit = 75`".
- LOW (Task 1 acceptance, count 0): `finish`'s fallback row `{ exit: 1, action: 'stop' }` (template:210) also counts. **Fix:** name it explicitly.
- LOW (Task 2, `no-second-cli-hang`): the `hang` fake is sticky and spawns `gc`, but the generated case has no `deadCheck(ctx, ['pi','gc'])`. **Fix:** add it.

### 25-02
**Strengths**
- The table order follows D-03 as amended (an opencode `provider.*` type is only a hint).
- Fixtures are thorough: U+2019 apostrophe, `spending[ -]limit`, `4021`, answer-only cases, and an order-mutation test.
- Log lines the runner writes carry a rule id, never provider text.

**Concerns**
- HIGH (Task 1, "Only the template changes"): `tests/test_ai_kit_spec.py:11864-11884` (`test_patterns_block`) parses `PATTERNS` as a dict with 7 pinned keys. A JSON array fails it, so the barrier `make test` goes red. **Fix:** add the file to `files_modified`, rewrite the test for the row schema, and verify `tests.test_ai_kit_spec`.
- HIGH (run rule 1, "3600 s per plan"; affects every delegated plan):
  - `.planning/config.json` has `cross_ai_timeout: 1800`, and the dogfood `outerTimeoutS: 1800` caps the deadline through `Math.min` (template:466-468). Executors get about 1770 s; 25-07 itself says "the 1800 s window".
  - 25-02 (about 60 rows, extractors, matcher and status tail, then about 60 fixtures) won't fit reliably, nor will 25-05 and 25-06 (3 tasks each, e2e runs up to 900 s).
  - **Fix:** raise `cross_ai_timeout` to 3600 and add `--outer-timeout 3600` to the hook, or split 25-02 and trim the verifies.
- MEDIUM (lines 295-297; also 25-06 Task 2): `<redacted-synthetic-key>` is written as a literal in the plan and in the shipped template. **Fix:** build it at run time (for example `['sk','aikit','SENTINEL',process.pid].join('-')`), pass it to the fake through an env var, and scan for that value.
- MEDIUM (Task 2, `xai-spending-hyphen` "verbatim"): the recorded xai text says `need a Grok subscription`, and `tests/test_ai_kit_spec.py:11841-11855` fails on any `grok` outside `scrubEnv`. **Fix:** fixture only the `spending-limit` / `run out of credits` part.

### 25-03
**Strengths**
- The route value is an enum, and the `router-inferred` label is visibly flagged.
- `--classify-only` is pure.
- A parity test with a non-vacuity case pins `ROUTER_HINTS` (`model_heuristics.py:9` matches).
- The e2e tests run under uv.

**Concerns**
- LOW (Task 2): it lists seven `TestClassifyOnly` cases but asserts "six JSON lines". **Fix:** say seven.

### 25-04
**Strengths**
- Live kill reuses `currentFinalize`.
- The signal is recorded at first sight (flood case).
- Ruling Q1 is pinned both ways.
- `deadCheck` is required for long-running cases.

**Concerns**
- MEDIUM (Task 1 with 25-02's `terminal` flag): the bare-code rows (`\b429\b`, `\b40[13]\b`, `\b402\b`) and `rate.?limit` are terminal. So a CLI's own `Retrying after 429` notice kills the child, against D-09; `retry-notice-no-kill` only covers a 503 notice. **Fix:** set `terminal:false` on those rows and add `retry-notice-429-no-kill`.
- MEDIUM (Task 1, re-labelling a timeout after the fact): a timeout matched by a transient or capacity row becomes `transient` exit 75. `run_runner_tiers` (`runner_dispatch.py:552-564`) only moves to the next timeout tier on `timeout`/124, so a slow reviewer that printed one retry line loses its next tier. **Fix:** only terminal rows re-label a timeout; add a case.

### 25-05
**Strengths**
- `ladderNext` is pure and clamped.
- Which CLIs can continue a session is pinned per CLI (codex review, sandboxed codex, cursor without an id).
- The dirty-tree rule uses `git diff-tree` on the stored write-tree.
- The e2e timing guard avoids real sleeps.

**Concerns**
- HIGH (Task 1, drop `retries` and add the rung keys): `tests/test_ai_kit_spec.py:11804-11837` (`test_header_and_config_contract`) pins the exact CONFIG dict, including `retries: 2`, and requires `sort_keys` order. **Fix:** add the file to `files_modified`, update the expected dict, insert the new keys in sorted order, and verify `tests.test_ai_kit_spec`.
- MEDIUM (rung 1): QTA-03 and the owner list `timeout` as transient. The plan only retries provider-timeout text and silently ends a runner-deadline `timeout` at once. **Fix:** state it, add a pure case, and add it to C7.
- MEDIUM (Task 3, "budget 120 s"): the Python e2e tests cap the full self-test at 180 s (`tests/test_cross_ai_runner_e2e.py:225`, `:315`) under `make test` parallel load, and this phase roughly doubles the cases. **Fix:** time it under `make e2e-test` and raise both caps if needed.
- LOW (Task 1, `$FAKE_SIDS`): no location is given; inside the repo it dirties the tree and rung 2 stops. **Fix:** put it beside `FAKE_CALLS`.

### 25-06
**Strengths**
- The cap boundary is checked as pure cases (exactly at the cap, and 60 s past it).
- Values are clamped, and self-test copies use cooldown 0.
- The evidence lines carry no child text.
- Version pins become computed values.

**Concerns**
- HIGH (Task 3, the version bump): two sets of pins outside the plan break.
  - `tests/test_ai_kit_spec.py:11815` asserts `"6"`; the plan's `template=6` grep misses it, and its CONFIG pin also lacks `cooldownS`/`capS`.
  - Seven goldens in `tests/fixtures/curated_config_v2/golden/*.json` pin `"version": 6`.
  - **Fix:** add these files, regenerate the goldens with `UPDATE_GOLDEN=1`, rerun them without it, and verify both modules.
- MEDIUM (prohibition "no key in any log", marked resolved): the runner passes the child's raw stderr straight through (`log(d)`, template:840) into GSD's error log, and `sentinel-evidence` only scans `cross-ai:`/`AIKIT-XAI` lines. **Fix:** redact key-shaped tokens there, or mark the prohibition "adapted: runner-written lines only" in the policy reference and the SPEC mapping.
- MEDIUM (D-08 router-tail rows): `credential gate`, `requires an opencode api key`, `model access is disabled` and the `[401]` MonthlyLimitError are retried as quota on router lanes.
  - The owner's step 3 names 401/403 as stop. Locked D-08 conflicts with the later owner decision, which wins, and C7 doesn't ask about it.
  - **Fix:** add a C7 item, or stop on these until the owner confirms.
- LOW: the sentinel literal again; same fix as 25-02.
- LOW: with `cooldownS: 0` and `backoffS: [0]`, a user config hammers the router until the deadline. **Fix:** cap the number of cycles, or set a floor outside self-test copies.

### 25-07
**Strengths**
- Uses the shipped `ensure-runner`; I checked that a pristine older runner gets `change` and keeps its CONFIG.
- The dogfood runner is `pristine` today.
- Proves the rendered copy passes its self-test.
- Commits a single file.

**Concerns**
- MEDIUM (`cross_ai: true` on orchestrator plans, also 25-11):
  - GSD's step 2.5 sends every cross_ai plan to the runner (`elaboration.md:67-68`). It runs them sequentially before any wave, ignoring `depends_on` (`:82`).
  - The guard line then ends `no_change` exit 1 and triggers retry/skip/abort; under template 6 it also falls through to cursor and opencode.
  - **Fix:** document that the run uses a custom per-plan loop, or set `cross_ai: false` and split the run at 25-07.
- LOW: the "body equals the template's" check must exclude line 2 (stamped vs `UNSTAMPED`).
- LOW: nothing checks the real-config mtimes after delegated runs (owner memory "executor real-home guard"). **Fix:** add that check to the barrier.

### 25-08
**Strengths**
- Only a user-confirmed `fallback_quota` becomes a flag.
- `_meta` is skipped and nothing is written.
- The GSD hook command (`project_runner_command`) is unchanged.
- The e2e test's cache is hermetic through `runner_env`'s scratch `HOME`.

**Concerns**
- LOW (Task 2 audit): `rg "RunnerSeams\("` misses the default seams built inside `ReviewerSeams()`/`ExecuteSeams()` (`reviewer_dispatch.py:31`, `execute_dispatch.py:52`). **Fix:** also audit those call sites.

### 25-09
**Strengths**
- One canonical reference with the 3-4 line pointer.
- The wake baselines are correct (4/2, 6/2, 8, 1).
- Text tests with non-vacuity cases; behavior unchanged.
- A1 is routed to C7.

**Concerns**
- None new.

### 25-10
**Strengths**
- Removes the stale prefer-order text, with pinned baselines.
- The owner kit has redaction rules, and every result row reads `not run (owner)`.

**Concerns**
- MEDIUM (Task 2 read_first "sections named in `<interfaces>`"; applies to every delegated plan):
  - GSD's prompt holds `<objective>` and `<tasks>` only (`elaboration.md:84-85`).
  - So `<interfaces>` and the frontmatter `files_modified` (needed by the "stage only `files_modified`" rule) never reach pi.
  - **Fix:** start each `<objective>` with "read `25-NN-PLAN.md` in full first".

### 25-11
**Strengths**
- Formal amendments are planned; all target paths exist, and the stale ROADMAP line is at 81.
- A blocked judge lane is recorded as `BLOCKED`, never a guessed pass.
- The phase-tip gates include `e2e-docker`.

**Concerns**
- HIGH (Task 1, run rule 2): the owner changed the judge set on 2026-10-24 (owner memory and the commit 9278476 config change). It is now native Opus plus opencode `router-env/my-referee-one` plus `router-env/my-referee-two`; `my-plan-review` stays only for plan and code reviews. **Fix:** switch to the two referee lanes, go from 8 to 12 report files, and update the verify loop.
- LOW: 25-VALIDATION's quick-run command for the e2e module should be `uv run python ...`, as the Makefile runs it. **Fix:** amend it in Task 2.

## Overall Risk

HIGH as written. The ladder design is sound and faithful to the owner sections. Two kinds of problem stop it:

- **Execution environment, fix before 25-01 is dispatched:** template 6 can still fall back to cursor or opencode, and each plan really gets 1800 s.
- **Unlisted test pins, which fail at the barriers after the executor reports green:** `test_ai_kit_spec.py` (PATTERNS, CONFIG, version) and the seven golden files.

Fixing those and the judge set is mechanical: config flags, plus `files_modified` and verify additions. After that the risk drops to MEDIUM, mostly the unverified cursor and claude rows and live-kill tuning.

Not checked: I didn't run any self-test or `make` target (read-only review). Whether the orchestrator drives plans through `/gsd-execute-phase` or its own loop is not stated in the plans. The full review is also saved to `<home>/.claude/plans/you-are-a-senior-luminous-pebble.md`.

CYCLE_SUMMARY: current_high=6 current_actionable=21

## ponytail (verbatim)

What the plans aim to do: replace automatic cross-CLI fallback with the owner’s one-lane failure ladder, classify limits from child errors, and carry that policy through the rendered runner and skills. The latest owner decisions in `25-SPEC.md:221-256` and `25-CONTEXT.md:285-320` override the earlier wait-and-resume design; I have not treated those superseded features as missing.

1. **HIGH — A classified timeout can still become an ordinary timeout** (`25-04` Task 1; `25-06` Task 1). The plan gives a timed-out attempt its matched quota status but keeps `timedOut: true`. The existing `main` checks `r.timedOut` first and emits `status=timeout` (`cross-ai.mjs:3004-3005`). Have `main` prefer the classified status, while retaining timeout in the attempt evidence; test through `main`, not only the matcher. **Saving:** one classification path instead of adding a result that the caller discards; avoids a broken acceptance case.

2. **HIGH — The proposed four-hour cycle cannot run under the current call deadline** (`25-06` Task 1; `25-07` Task 1). The template and dogfood CONFIG use `outerTimeoutS: 1800`; Python dispatch sets its own timeout, and the GSD cross-AI step defaults to 300 seconds. An in-process 600-second cooldown cannot deliver repeated cycles under those bounds, regardless of a `capS: 14400` clamp. Keep the required 3+3 attempts and hard cap, but settle where later cycles run and how their first-failure time survives calls **before** implementing cooldown. Do not describe the present in-call design as a working four-hour policy. **Saving:** the planned in-call cycle machinery and misleading boundary tests until there is a viable orchestration contract.

3. **HIGH — The secret test protects only composed lines, not the log** (`25-02` Task 1; `25-06` Task 2). `runOnce` currently relays raw child stderr with `log(d.toString('utf8'))` (`cross-ai.mjs:840`). Both sentinel cases explicitly ignore that line and scan only lines beginning `cross-ai:` or `AIKIT-XAI`. The SPEC prohibits a key or token in **any** log (`25-SPEC.md:118,191`). Keep the evidence lines, but redact or suppress sensitive raw error output before relay and assert the sentinel is absent from the **entire** captured log. **Saving:** two partial sentinel checks replaced by one test of the actual boundary; this is a necessary safety addition, not a feature cut.

4. **HIGH — An inferred route controls costly retries** (`25-03` Task 1; `25-07` Task 1). Matching `router`, `-env`, or `local-llm` anywhere in a model ID makes `router-inferred` behave as a confirmed router lane. In the dogfood copy, `routerBacked` is empty, so this inference alone enables quota cycles. Keep the visibly labelled hint for diagnosis, but require an explicit `routerBacked` value or confirmed `--route-<cli>` for automatic quota cycling; set the dogfood lane explicitly if the owner confirms it. **Saving:** the cross-language `ROUTER_HINTS` parity machinery in `25-03` Task 2 and an unsafe retry branch.

5. **MEDIUM — Route lookup is over-layered and underspecified for malformed entries** (`25-08` Tasks 1–2). The proposal adds `resolve_route`, `RunnerSpec.route`, `RunnerSeams.route_fn`, and test stubs solely to pass one confirmed boolean. Yet the proposed “first entry” lookup calls `.get` through catalog entries without first establishing that each entry and its `runtimes` value are dictionaries; malformed JSON objects are promised to yield no flag, not an exception. Keep the confirmed-value check, use the existing `cache_read_json` and `split_catalog_meta`, validate each traversed shape, and pass the resulting literal at the existing argv-building seam. **Saving:** roughly one seam and its spawn-path test-stub sweep; keep one malformed-entry regression test.

6. **MEDIUM — The classify-only fixtures largely test their own matcher twice** (`25-02` Task 2; `25-03` Tasks 1–2). `CLASSIFY_CASES` first calls `classifyStop` directly, then `classify-only-fixtures` sends those same cases through the runner’s new `--classify-only`, which calls the same matcher. Keep the observed-message fixtures and the required owner-facing mode, but use one fixture table with a small black-box check of the CLI’s parsing, output, and no-spawn behavior. Keep separate fake-child tests for live detection and answer-text exclusion. **Saving:** one generated self-test layer and most of `25-03`’s repeated Python fixture assertions; no loss of real-flow coverage.

7. **MEDIUM — Several new retry knobs are flexibility the owner did not request** (`25-05` Task 1; `25-06` Task 1). `sameSessionRetries`, `newSessionRetries`, `cooldownS`, and `capS`, their clamps, and old-`retries` upgrade handling create more states than the fixed owner rule of 3+3, ten minutes, and four hours needs. Keep existing `backoffS` and the hard safety ceiling; make the new counts and cooldown policy constants unless a real caller needs to configure them. **Saving:** four CONFIG fields, clamp branches, upgrade assertions, and their pure tests. This does **not** remove the ladder or its cap.

8. **MEDIUM — Some planned tests prove a test artifact, not behavior** (`25-01` Task 2; `25-05` Task 3; `25-09` Task 1). Thirteen near-identical no-second-CLI cases cover a decision made once in `main`; a reversed-table mutation and a deliberately wrong pure-ladder expectation prove that test code can fail; the policy text test proves particular words are absent, not that a skill stops. Retain a first-choice success, failure, missing-first case, route-sensitive classifier cases, and a real failed-dispatch skill test. **Saving:** approximately a dozen generated cases and the mutation/non-vacuity scaffolding, while preserving trust-boundary and behavior checks.

9. **LOW — Eleven plan boundaries cause avoidable handoffs and repeated gates** (`25-01`–`25-11`). Merge `25-02`+`25-03` (table, route, fixtures, classify-only), `25-05`+`25-06` (one ladder and its evidence), and `25-09`+`25-10` (skill and documentation policy). Fold `25-01` into the ladder work if the executor can still leave each commit buildable. **Keep `25-07` separate and orchestrator-only:** it replaces the live dogfood supervisor between dispatches. Keep `25-11` as the final judge/amendment/gate. **Saving:** roughly three plan handoffs, summaries, and repeated project-wide gate rounds; retain the final `make test`, `make validate`, and clean-room run.

**Not checked:** no tests, AI CLIs, network calls, credentials, or real home configuration were used. Estimates are planning savings, not measured line counts; the timeout/cycle contract needs resolution before execution.

PONYTAIL high=4 medium=4 low=1


# Cycle 2 (2026-10-24)

Reviewers: my-referee-one, my-referee-two, claude-opus (the my-plan-review ponytail lane was dropped mid-cycle at the owner request: three reviewers only).

## referee-one, cycle 2 (verbatim)

## Summary

The cycle-1 edits resolve several concrete problems: the plans now include the pattern and CONFIG test pins, classify a quota-bearing timeout before treating it as an ordinary timeout, stop superpowers after a failed external dispatch, and use the corrected judge set. **The plans are not ready for unattended execution.** The cross-call quota ruling is not carried consistently into the caller, state handling, tests, and documentation. A read-only syntax check also found that 25-07’s main verification command cannot run as written.

I reviewed the plans and local source without running a test suite, AI CLI, vendor call, or network request. I assumed the stated one-hour unattended dispatch target, while checking it against the currently configured deadline.

### 25-01

**Strengths:** The first-entry-only rewrite and no-second-CLI matrix target the existing fallback loop. Task 1 now checks the selected entry, rather than rejecting an exec request because of a later menu entry.

**Concerns:**
- **HIGH — Task 2, lines 293–299:** `review-only-first-refused` selects `cursor`, but the runner defines a Cursor **exec** formula. `review-only-later-ignored` similarly treats `opencode` as review-only when its model is absent; absence of a model does not make its runtime review-only. These cases cannot prove the stated rule and the first has the wrong expected outcome. Use `claude` as the review-only entry; test a missing model separately.
- **HIGH — run rule 1, lines 101–107; Task 1:** Before 25-07, the active `.planning/scripts/cross-ai.mjs` is still template 6 with `prefer: [pi, cursor, opencode]` and a fallback loop. Dispatching 25-01 through 25-06 with the configured bare hook can still switch CLI after a pi failure. This **contradicts the locked Owner decision** during the phase’s own execution. Pin the active hook to the owner-selected pi lane before the first dispatch, or otherwise prevent its fallback, and verify the effective command before delegating.
- **MEDIUM — lines 101–105, 135–144:** The plans promise 3600 seconds per dispatch, but `.planning/config.json` sets `cross_ai_timeout: 1800`, and the active runner also caps its default outer deadline at 1800. A green commit boundary does not give a 120k-token plan another uninterrupted hour. Set and verify the intended effective deadline, or split the large delegated runs to fit the current one.
- **MEDIUM — lines 81–83, 214–225:** The execution rule relies on `files_modified`, but GSD’s cross-AI prompt includes `<objective>` and `<tasks>`, not frontmatter. The documented custom orchestrator loop does not specify that it sends the full plan either. Tell the executor in `<objective>` to read its complete plan before editing or staging, and verify that instruction reaches it.

### 25-02

**Strengths:** Task 1 now updates `test_patterns_block`, builds sentinel values at run time, and proposes a full-log check. The pattern order and non-terminal retry-notice rows have explicit fixtures.

**Concerns:**
- **MEDIUM — Task 1, lines 295–311:** Redacting each stderr **chunk** before `log(...)` is insufficient when a key-shaped token is split across two chunks. The raw tail is retained for classification, but the first chunk may already have been relayed. Redact across chunk boundaries—or relay complete bounded lines with a retained partial buffer—and add a fake that splits the runtime-built sentinel mid-token. This is needed before claiming the whole log is secret-free.
- **MEDIUM — estimate and Task 1, lines 16–19, 238–325:** The low-confidence 120k-token plan still puts table construction, extractors, integration, redaction, status changes, and existing test-pin repair into one large task under the effective 1800-second dispatch deadline. Split it into independently green tasks or establish a longer verified deadline before unattended dispatch.

### 25-03

**Strengths:** The malformed JSON acceptance fixture is now a quoted heredoc, and Task 2 consistently expects seven lines. `router-inferred` is expressly diagnostic rather than authorization for quota cycles.

**Concerns:** None found beyond the shared execution-deadline and full-plan-prompt concerns above.

### 25-04

**Strengths:** The task body now gives a classified terminal timeout precedence in `main` and preserves ordinary timeout handling for transient/capacity notices. The live-kill and answer-only negative cases are useful.

**Concerns:**
- **HIGH — Task 1, lines 225–239; Task 2, lines 286–291:** `post-hoc-timeout-flood` is claimed to preserve an **unterminated** early quota line followed by more than 64 KiB of stderr. The proposed partial-line buffer “keep[s] the tail,” and the existing stderr capture also keeps only the tail; without a newline, both can discard that early phrase before the timeout. Neither `liveHit` nor the later post-hoc pass can recover it. Record a terminal match incrementally before trimming, or retain a bounded first candidate until it is resolved; make the flood test exceed the buffer cap.

### 25-05

**Strengths:** The revised task sends quota-free child timeouts into the transient ladder when budget remains, updates the exact CONFIG pin, and specifies session IDs and dirty-tree checks for both rungs.

**Concerns:**
- **MEDIUM — Task 1, lines 262–266; Task 3, lines 364–382:** A pure `ladderNext(timeout, …)` case does not prove the real `runCli` → `main` timeout path takes another attempt. Add a short-deadline fake whose first child times out while enough outer budget remains, then succeeds on the next attempt; also pin the no-budget stop. Keep both runs fast with short fake timeouts and zero test backoff.

### 25-06

**Strengths:** Moving the 600-second cooldown **between** runner calls addresses the cycle-1 conflict with GSD’s 300-second default. The task bodies now include the header/CONFIG pin and golden-file updates, runtime-built sentinel, and confirmed-route requirement.

**Concerns:**
- **HIGH — Task 1, lines 275–299:** `pure-ladder-cap-boundary` expects `stop/cap` at 13,860,000 ms, but the specified predicate `nowMs + 60000 <= firstQuotaMs + capMs` still permits it: 13,920,000 ≤ 14,400,000. The check for **another** cycle must include the 600,000 ms cooldown as well as work time. Distinguish permission to finish this cycle from permission to advertise the next, and correct both boundary expectations.
- **HIGH — Task 1, lines 284–292:** The state holds `first_seen` and `cycle` but not a captured session ID, yet re-entry is instructed to continue rung 1 “on the last captured session.” `runCli` currently creates a fresh `ctx.sid` each invocation. The second invocation therefore cannot resume that session as specified. Persist the session reference safely or explicitly start the new invocation with a new-session rung; pin its session IDs across two real runner invocations.
- **HIGH — Task 1, lines 284–290:** A state path keyed only by worktree, CLI, and model combines unrelated tasks using the same lane. Task B can inherit Task A’s first-failure time and hit its four-hour cap immediately. Include a stable task identity in the key, with a defined GSD prompt source, and test two tasks on one lane independently.
- **HIGH — Task 1, lines 280–310:** `retry_after_s` is advice, but the re-entry path specifies only a four-hour expiry check; it does not reject a call **before** the cooldown ends. An impatient caller, or tests using `cooldownS: 0`, can run full 3+3 cycles repeatedly without the required several-minute pause. Persist a due time and refuse early re-entry without spawning a child; test early, due, and expired calls with an injected clock. This contradicts the locked **Rule adjustment**’s bounded cooldown.
- **MEDIUM — Task 3, lines 368–400:** Its acceptance criterion says `git show --stat HEAD` lists “all five files,” although Task 3 also changes `tests/test_ai_kit_spec.py` and the seven golden fixtures. Name the full expected file set so the commit-content check does not overlook those pins.

### 25-07

**Strengths:** Re-rendering is orchestrator-only and follows the template bump. The task checks the active copy rather than accepting a `.new` file as installed.

**Concerns:**
- **HIGH — Task 1 `<automated>`, line 195:** The Python `cut=lambda` expression is syntactically invalid, and its quoting also leaves the surrounding shell command unterminated. A read-only `bash -n` check rejected this block; parsing its `python3 -c` payload also raised `SyntaxError`. Replace the inline expression with a small, valid check and syntax-check both layers before relying on this barrier.
- **HIGH — must-haves, lines 21–24; Task 1, lines 184–188:** The retained dogfood CONFIG has `routerBacked: {}`. Its pi model can therefore resolve only to `router-inferred`; 25-03 and 25-06 explicitly prohibit quota cycles on that route. The assertion that this dogfood lane cycles on quota, and that the later delegated runs use that policy, **contradicts the locked cycle-1 confirmed-route ruling**. Obtain and set a confirmed route for the selected model, or report that its quota stops without cycles and change the test and claim.
- **MEDIUM — Task 1, lines 177–195:** The check compares `models`, `outerTimeoutS`, and `routerBacked`, but not the preserved `prefer` value it also claims to protect. Compare `prefer` with `before.json` as well.

### 25-08

**Strengths:** The plan now normalizes model variants before catalog lookup and covers malformed top-level entries. Its Python route seam is placed on the real runner dispatch path.

**Concerns:**
- **MEDIUM — Task 1, lines 221–244:** The promised “malformed entry yields no flag” behavior still indexes `runtimes[runtime]["model_id"]` without requiring that runtime row to be a dictionary. For `{"runtimes":{"pi":null}}`, route resolution raises instead of dispatching without a flag. Validate that nested row and add this case to the malformed-catalog test.

### 25-09

**Strengths:** The superpowers `"real_error"` branch now stops rather than offering a capability-escalated candidate. The policy pointer is short, and pre-dispatch selection is marked as awaiting owner confirmation.

**Concerns:**
- **HIGH — must-haves, lines 31–37; Tasks 1–2, lines 255–280 and 311–335:** The skills are instructed to schedule **no** wake, stop the wave, and wait for the owner to re-invoke. But the binding cycle-1 ruling says the **caller waits and re-invokes** a router-quota result, through an orchestrator one-shot wake or execute-skill loop. As written, the first exit 75 can strand a pending cycle indefinitely, so the cross-call policy in 25-06 is not delivered. This conflicts with that locked ruling. Define which caller consumes `retry_after_s`, how it observes the state’s due time and cap, and how it re-invokes without changing lane; keep auth and off-router stops owner-controlled.

### 25-10

**Strengths:** The active-runner-versus-`.new` documentation now reflects `plan_runner_upgrade`, and live vendor captures remain owner-only and unverified.

**Concerns:**
- **HIGH — Task 3 C7, lines 322–327:** C7 asks the owner to confirm that cooldown cycles “stay inside one runner call (A4).” The binding cycle-1 ruling and 25-06 Task 1 explicitly put them **across** calls. Remove or correct that question; an owner answer to the wrong premise could reverse the settled placement.
- **MEDIUM — Task 2, lines 263–286:** The requested failure-ladder documentation describes route sources but does not require saying that `router-inferred` **cannot** authorize quota cycles. Say this explicitly beside `router_backed`/`--route-<cli>` so readers do not infer the wrong behavior from a diagnostic route label.

### 25-11

**Strengths:** The judge set is corrected to Opus plus two named referee lanes. The close-out is guarded as orchestrator-only, and the phase-status check now inspects `human_needed` and all C1–C7 rows.

**Concerns:**
- **MEDIUM — Task 1 `<automated>`, line 228:** The parser accepts `Verdict: PASS` without parsing a score, findings, or the no-regression comparison it claims to establish. Nonempty reports and a self-declared PASS are not proof of the AGENTS.md rule. Parse those recorded values against each skill’s base score, or label the verify as a format check and make a separate enforceable verdict gate.
- **MEDIUM — edge ledger, lines 43–45; Task 2, lines 247–255:** The planned SPEC amendment says R5 concurrency/idempotency is superseded because there is “no state file.” 25-06 now introduces a cross-call cycle state file. Correct the mapping and cover its task isolation, atomicity, and early re-entry behavior rather than formally declaring those edges absent.

## Overall Risk

**High.** The main design no longer proposes automatic fallback in the new template, but the *active* template-6 supervisor can still do it before 25-07. More importantly, the revised quota-cycle plan lacks a dependable caller, due-time enforcement, task isolation, and cross-call session continuity. Fix those contracts and the 25-07 command before unattended runs. The runner-template edits remain sequential; the declared 25-08 and 25-09 file sets have no same-wave overlap.

Not checked: I did not execute any plan, suite, skill judge, vendor CLI, or live capture. My command check was limited to read-only shell/Python syntax parsing; it does not establish that other verification assertions will pass.

CYCLE_SUMMARY: current_high=11 current_actionable=11

## referee-two, cycle 2 (verbatim)

All plans read; baselines verified against the actual tree (template 6 literals, `ctx.elapsedMs` at cross-ai.mjs:1432, `test_header_and_config_contract` pinning `"6"` + `retries: 2`, 7 goldens, 8 `template=6` test literals, `fake/capacity` rows `[600]`/`30`, the two 180 s e2e caps, CronCreate/hourly counts 4/6/2 + 1/1, `dispatch_injection` 8 + `error_classifier` 1, `"Retry Step 3 with the new injection"` 1, capability-escalated wording 1, curated SKILL.md:192 prefer-order sentence, runner.md title, README:45, ROADMAP:81, dogfood pristine template 6, `cross_ai_timeout: 1800`, `strip_model_suffix` routing.py:123, `_ROUTER_NAME_HINTS`, default `RunnerSeams()` in Reviewer/ExecuteSeams, `split_header` 3-tuple, `pids_with_cwd_under`, `make e2e-docker`).

## Summary

Cycle 1 was absorbed seriously: every cycle-1 HIGH I re-checked (menu selection, sentinel handling, timeout-as-transient-rung, cross-call quota cycles, version pins, judge set) is genuinely resolved in the task bodies, and the ruling text is carried into must-haves and verify steps. Baseline calibration is still exact against HEAD. Two new blocking problems, both inside 25-06 Task 1, where the pinned pure-case numbers and the pinned status token contradict the plan's own stated rules — the self-test cannot pass as written. Everything else is LOW polish.

### 25-01

**Strengths:** Removed-literal baselines exact (2/3/9/12/8/20/1); menu-selection fix (`cands.find` → `cands[0]`, template line 2885 confirmed) pinned by two cases; the implicit `{exit:1}` fallback row and the exit-75-half-only router rule both named; `deadCheck(ctx, ['pi','gc'])` for the sticky hang fake.

**Concerns:** none new.

### 25-02

**Strengths:** Sentinel now runtime-built via env var with a whole-log scan plus stderr redaction in `runOnce`; `test_patterns_block` rewrite joined to `files_modified` with the module in the verify; xai fixture bounded to the `spending-limit` wording (the `grok` prohibition is real); smoke order paces the oversized task.

**Concerns:** none new.

### 25-03

**Strengths:** Heredoc fixture (the printf bug is really fixed); seven/seven case count; `router-inferred` demoted to advisory with cycles requiring a confirmed route — the binding ruling is written into `routeOf`'s contract, not just prose.

**Concerns:** none new.

### 25-04

**Strengths:** Timeout-ordering fix at both seams (`runCli` early return, `main`'s `timedOut`-first finish) with `post-hoc-timeout-transient-stays` protecting `run_runner_tiers`; partial-line + flood cases cover the tail-loss hole; `ctx.elapsedMs` rejection was correct (line 1432).

**Concerns:** none new.

### 25-05

**Strengths:** Timeout enters the ladder; CONFIG-contract test updated in the same commit with the module verified (pin confirmed at tests/test_ai_kit_spec.py:11804-11837); e2e `[30]` tier and the two 180 s caps (lines 225/316) both real and handled.

**Concerns:**
- LOW (Task 2, `promptFiles`): referee-one's cycle-1 MEDIUM (bind `<files>` to the dispatched task, test a path named only in another task's block) is in neither the ledger nor the task; the union-of-all-blocks rule is defensible only because the GSD prompt carries the whole plan (assumption A6, unverified). Add the cross-task negative case or record the acceptance of the union under A6 explicitly.

### 25-06

**Strengths:** Cross-call cycle design matches the binding ruling exactly (exit 75 + `retry_after_s`/`cycle`, 0600 XDG state file, past-cap exit 69, no in-call sleep); every rung cap-bounded; sentinel via env var with full-log scan; all version pins (spec test literal `"6"` at 11815, 7 goldens, 8 curated-test literals) computed or regenerated in the same commit.

**Concerns:**
- HIGH (Task 1, `pure-ladder-cap-boundary`): the stated rule (`nowMs + 60000 <= firstQuotaMs + capMs`, and the same bound in the must-have) makes **both** pinned values pass: 13 860 000 + 60 000 = 13 870 000 ≤ 14 400 000, so `nowMs = 13860000` would return `cooldown`, not `stop`/`cap` — the case fails as written. The values pin a different rule: `nowMs + cooldownMs <= firstQuotaMs + capMs` (13 800 000 + 600 000 = 14 400 000 exactly → inside; 13 860 000 → outside), which also matches "exactly at the cap is inside". Fix: state the cooldown-admission rule as `nowMs + cooldownMs <= firstQuotaMs + capMs` (keep the +60 s rung rule for attempts), or change the second fixture value to ≥ 14 340 001 under the prose rule.
- HIGH (Task 1, `router-quota-one-cycle` vs the writeCopy rule): the case expects the status line to end `retry_after_s=600 cycle=0`, but this plan's own objective says self-test copies default `cooldownS: 0` and "never `cooldownS` above 0" — so the copy would print `retry_after_s=0` and the case fails. Fix: expect `retry_after_s=0` in self-test copies and pin the 600 default only through the CONFIG-contract test (which Task 3 already does), or let this one case override `cooldownS: 600` and drop the "never above 0" clause.
- LOW (frontmatter prohibitions, 25-06-PLAN.md:63-68): the "MUST NOT write a key or token" prohibition appears twice, the second copy carrying the old weaker verification ("scans every `cross-ai:` and `AIKIT-XAI` line"). Delete the duplicate so an executor can't implement the weaker one.

### 25-07

**Strengths:** The body/CONFIG comparison is real and correctly excludes line 2 (`split_header` returns the 3-tuple the verify unpacks); refuse-if-edited stop; mtime baseline stat-only; orchestrator-loop documentation resolves the step-2.5 hazard.

**Concerns:**
- LOW (orchestrator_verify / Task 1 verify): the check proves `prefer[0] == "pi"` but not that the whole `prefer` order equals `before.json` (only `models`/`outerTimeoutS`/`routerBacked` are compared). Add `prefer` to the compared keys, or soften the claim to what is checked.

### 25-08

**Strengths:** Variant normalization via the real `strip_model_suffix`; malformed-entry guards; `ReviewerSeams()`/`ExecuteSeams()` default-construction sites included in the audit (verified at reviewer_dispatch.py:31, execute_dispatch.py:52); GSD hook string provably unchanged.

**Concerns:** none new.

### 25-09

**Strengths:** All text baselines exact (Cron 4/6/2, hourly 2/2/1/1, 8 + 1 Python lines); the capability-escalated option really leaves the `"real_error"` branch (wording confirmed present today); A1 demoted to pending-owner, not settled policy; Makefile/`.pre-commit-config.yaml` staged for the new test module.

**Concerns:** none new.

### 25-10

**Strengths:** Stale-text targets verified present exactly once (SKILL.md:192, `template 6` titles, README:45 `template-6`); upgrade-behavior wording now matches `plan_runner_upgrade` reality; the owner kit's parser check is a real assertion over the seven C1–C7 rows.

**Concerns:** none new.

### 25-11

**Strengths:** Judge set corrected everywhere with twelve reports; machine-checkable verdict lines with BLOCKED never satisfying acceptance; Task 3's 5400 s budgets explicitly guarded as orchestrator time; ROADMAP gate phrase verified at line 81.

**Concerns:**
- LOW (Task 1, files_modified): "fix every CRITICAL and IMPORTANT finding with a scoped edit" can require touching a `references/*.md` file, but only the four SKILL.md paths are in `files_modified` while the executor rule says "stage only files_modified paths". Add the touched skills' `references/` directories (or a sentence authorizing scoped reference edits) so a legitimate judge fix doesn't deadlock the staging rule.

## Overall Risk

**Medium — two concrete blockers, both in 25-06 Task 1, both one-line fixes.** The chain 01→05 and 07→11 is verified against the tree down to line numbers and counts; nothing keeps or reintroduces a cross-CLI fallback, harness/provider/model switch, an unbounded loop, or a real sleep; sentinel hygiene and real-home guards are in place. Fix the two 25-06 contradictions (cooldown-admission rule vs its pinned boundary values; `retry_after_s=600` vs the `cooldownS: 0` self-test rule) before dispatching wave 6; the four LOWs can ride along in the same edit pass.

Not checked: I ran no self-test, make target, AI CLI, or network call (read-only review); 25-RESEARCH.md/25-VALIDATION.md were read for cross-reference only where plans cite them verbatim.

CYCLE_SUMMARY: current_high=2 current_actionable=4

## claude-opus, cycle 2 (verbatim)

## Summary

Most cycle-1 HIGHs are fixed in the task bodies: the menu-selection intent, the router-billing `retry-later` write, the `test_patterns_block`, CONFIG and version pins, the goldens, the e2e caps, the per-rung cap bound, the cross-call cooldown, the judge set in 25-11, the superpowers `real_error` escalation, and the printf escapes.

Eight HIGH problems remain or are new:

- **Two cycle-1 opus HIGHs were never handled.** Until 25-07 the live supervisor is still template 6 with automatic fallback. Each delegated run really gets about 1770 s, not 3600 s.
- **25-01** builds its review-only cases on a false premise.
- **25-05**'s "timeout is a transient rung" can never fire.
- **25-06**'s router cases contradict its own `writeCopy` defaults. Its cycle state file is never cleared.
- **25-07**'s verify is a Python syntax error.
- **25-09/25-10** leave nobody to act on `retry_after_s`. That contradicts the binding ruling.

What I checked: template 6, the dogfood runner, `.planning/config.json`, `runner_dispatch`/`routing` imports, the e2e helpers, the golden pins and the unittest runner groups, all read-only. I parsed the 25-07 verify snippet with `ast.parse`. I ran no suite, CLI or network call.

### 25-01
**Strengths**
- `cands[0]`-only selection, the `finish` `action=stop` rule, and the explicit `{ exit: 1 }` row match the template (`finish`, `STATUS_TABLE`, `reviewOnly` at cross-ai.mjs:2885).
- The `deadCheck(ctx, ['pi','gc'])` fix for `hang` is right.

**Concerns**
- **HIGH** (25-01-PLAN.md:293-299, Task 2): the review-only cases misread the code.
  - Only claude is review-only (`RUNTIMES.claude.exec: null`, cross-ai.mjs:326). A missing `--model-opencode` does not make opencode review-only, so `review-only-later-ignored` tests nothing.
  - `review-only-first-refused` (`--prefer cursor,pi`) will run cursor, because cursor has an exec formula. That case fails.
  - The existing case `claude-exec-late-usage` (IN-09, cross-ai.mjs:2252-2258) asserts the opposite of the menu ruling: a late claude refuses the exec run. The plan never updates it, so Task 1's full self-test goes red. This contradicts the binding menu-selection ruling.
  - Fix: use `--prefer pi,claude` for the later-ignored case (pi runs, no refusal line) and `--prefer claude,pi` for the refused case. Rename and invert `claude-exec-late-usage` in Task 1.
- **HIGH** (run rule 1, 25-01-PLAN.md:102-107; affects 25-01..25-06; cycle-1 opus HIGH, still unresolved):
  - `.planning/config.json:46` is `node .planning/scripts/cross-ai.mjs` with no `--prefer`. The dogfood has `prefer: [pi, cursor, opencode]`.
  - So template 6 still falls back to cursor or opencode, at full permissions, whenever pi fails on a clean tree. That is the automatic fallback the owner decision removed.
  - Fix: before 25-01, the orchestrator sets the hook to `... cross-ai.mjs --prefer pi`; restore it after 25-07. Record this in each run rule.
- **HIGH** (run rule 1, every delegated plan; cycle-1 opus HIGH, deferred as "orchestrator-level" in 25-02's ledger, never done):
  - `cross_ai_timeout: 1800` plus `outerTimeoutS: 1800` caps `resolveDeadline` (cross-ai.mjs:464-469) at about 1770 s inner. The plans still say 3600 s.
  - 25-06 Task 3's verify alone allows 300 + 600 + 300 + 900 = 2100 s.
  - Fix: raise `cross_ai_timeout` to 3600 and add `--outer-timeout 3600` to the hook. Also add a re-dispatch rule: skip a task whose `feat/test(25-NN)` commit already exists.
- **LOW** (Task 2 verify and acceptance): the targeted case list omits the two new review-only cases, and "thirteen" should be fifteen.
- **LOW** (run rules, all plans): the text is not identical across plans. In 25-01..25-06, rule 2 still names `router-env/my-plan-review` as a judge, and the "own loop, never step 2.5" sentence appears only in 25-07 onwards. Sync the text.

### 25-02
**Strengths**
- The row schema, the D-03 tier order and `terminal:false` on bare codes and rate-limit rows are right.
- `test_patterns_block` joins `files_modified`.
- The xai fixture is limited to the `spending-limit` wording, so no `grok` literal enters the template.

**Concerns**
- **MEDIUM** (25-02-PLAN.md:295-298): the redactor is not specified.
  - The plan says "the key-shaped-token pattern from the scrub rules", but no such pattern exists. `scrubEnv` is a list of env-var names (cross-ai.mjs:77). The executor will invent a regex.
  - Redacting per chunk (`onStderr`, cross-ai.mjs:840) leaks both halves of a token split across two chunks.
  - The only sentinel shape is `sk-aikit-…`, so a redactor written for that shape passes its own test.
  - Fix: name the regex set (`sk-`/`rk-`-style tokens, `Bearer \S+`, `(api[_-]?key|token|secret)\s*[:=]\s*\S+`). Redact per complete line (25-04 adds the splitter; flush the partial line at exit). Add a split-chunk case and a second sentinel shape.
- **MEDIUM** (Task 1 and Task 2 `<automated>`, lines 318 and 391): the shell is fragile. `…&& node … > t2b.log; grep -qx 'self-test ok' t2b.log` evaluates the last grep even when the earlier chain failed. A stale log from a previous attempt then passes. The same pattern is in 25-01 T2, 25-03 T1/T2, 25-04 T2, 25-05 T1/T3, 25-06 T3, 25-07 T1, 25-08 T1/T2 and 25-11 T1. Fix: `rm -f` the logs first and join every step with `&&` (or `set -e`).
- **LOW** (lines 146-147): "Only the template changes" contradicts `files_modified`, which includes `tests/test_ai_kit_spec.py`. Reword.

### 25-03
**Strengths**
- The heredoc fixture is valid JSON with escapes preserved.
- `routeOf` precedence and the enum flag are right.
- The parity test runs against the real `_ROUTER_NAME_HINTS`, and the seven-case count is consistent.

**Concerns**
- **MEDIUM** (lines 235-237, 258-259): this contradicts the binding ruling "a name-only heuristic is advisory only … stops and reports like a direct route".
  - The `route-heuristic` case expects a 402 on `router-inferred` to read `status=quota exit=75`, because "the router lane for classification stays a route starting with `router`".
  - So a heuristic turns billing into a recoverable quota (`any_quota_recoverable`) in Python.
  - Fix: apply `routerClass` only on a confirmed route. An inferred route keeps the base class (`billing`, exit 69) and still prints `route=router-inferred`.

### 25-04
**Strengths**
- Classified status now wins over `timedOut`, and only terminal rows re-label a timeout. `retry-notice-429-no-kill` is added.
- `ctx.elapsedMs` really exists (cross-ai.mjs:1432); the cycle-1 rejection was correct.

**Concerns**
- **MEDIUM** (Task 2, `post-hoc-timeout-flood` and `post-hoc-timeout-transient-stays`; referee-one's cycle-1 MEDIUM is only nominally resolved):
  - The flood's `x\n` lines complete the partial `quota exceeded` line, so the case becomes a live kill and never exercises the post-hoc path.
  - With a newline-free flood, the tail-keeping 64 KiB buffer drops the head, so the signal is lost for real.
  - `post-hoc-timeout-transient-stays` passes even when its signal is lost, so it proves nothing.
  - Fix: match the partial buffer before trimming it and record `liveHit` then. Use a newline-free flood for the flood case, and no flood for the transient-stays case.

### 25-05
**Strengths**
- The 3 + 3 rung logic, `canResume` exclusions, `ctx.sids` outside the repo, the CONFIG pin update and the e2e `[30]` tier are right. I checked that the exec `fake/capacity` row is 30 s.

**Concerns**
- **HIGH** (lines 261-266; cycle-1 referee-one HIGH not truly resolved; contradicts the owner decision's rung 1, which names timeout):
  - A child's timer is `budgetMs(…, runDeadline)` (cross-ai.mjs:837, 2934). A child timeout therefore means the whole call deadline is spent.
  - `ladderNext` then always returns `stop`/`deadline`, so "a quota-free timeout is a transient rung when the deadline admits one" can never happen. `pure-ladder-timeout` is pure and cannot show this.
  - Fix: add a per-attempt budget, for example `attemptTimeoutS`, clamped below the remaining deadline minus a reserve for rungs. Add a black-box case where call 1 hangs, call 2 answers, and the status is `ok` with 2 calls. Otherwise state plainly that a call-deadline timeout is terminal and add that reading to C7.
- **LOW** (Task 1 `<files>`, orchestrator_verify): `tests/test_ai_kit_spec.py` is edited but missing from `<files>` and from the porcelain list.
- **LOW**: referee-one's cycle-1 MEDIUM on `promptFiles` (any `<files>` block in the prompt) was neither applied nor rejected. Record the decision; the plan-level union matches the ruling's `files_modified` scope.

### 25-06
**Strengths**
- The cross-call design follows the ruling: exit 75 with `retry_after_s`/`cycle`, `first_seen` in the state file, exit 69 past the cap.
- Rungs are bounded by the remaining cap. Only a confirmed route gets cycles.
- The pins in `tests/test_ai_kit_spec.py` and the seven goldens are covered, and both are real (7 files carry `"version": 6`).

**Concerns**
- **HIGH** (lines 176-178, 275-278, 301-310): the verify cannot pass as written.
  - `writeCopy` defaults `capS: 0`, and every rung needs `nowMs + 60000 <= firstQuotaMs + capMs`. So every router-lane case on defaults stops after one call with `stopped=cap`.
  - Yet `router-quota-one-cycle` ("defaults") expects 7 calls. `billing-router`, `billing-403-router` and `sentinel-evidence` expect 7 calls, and `dirty-billing-router` expects 4.
  - `retry_after_s=600` is impossible under the copy's `cooldownS: 0`.
  - Fix: since the cooldown is no longer slept inside a call, default the copies to `capS: 14400, cooldownS: 0` and assert `retry_after_s=<copy cooldownS>`. Alternatively set `capS` explicitly in every router case.
- **HIGH** (lines 284-292): the state file is never cleared. Nothing removes it on `ok` or on a non-quota outcome.
  - After 4 hours, the lane's next quota failure reads the stale `first_seen` and exits 69 `stopped=cap`, skipping the 3 + 3 rungs forever until someone deletes the file by hand. This breaks the Rule adjustment.
  - Fix: delete the file on any non-quota outcome. Treat a file older than `capS` at the first failure of a new run as a fresh start, and add a case for it.
- **MEDIUM** (lines 300-307): `router-quota-second-cycle` is inconsistent.
  - `quota-until-9` fails calls 1-8, but the case expects an answer on call 8.
  - `attempts=8` needs a cumulative attempt count, which the state file does not store.
  - The objective says "pre-seed a state file", the task says "two invocations", and the harness runs one invocation per case.
  - Fix: name the mode `quota-until-8`, persist `attempts`, and pick one mechanism.
- **LOW** (prohibitions): a duplicate entry still says the sentinel test "scans every `cross-ai:` and `AIKIT-XAI` line", which is the superseded claim. Delete it.
- **LOW** (Task 3): `<files>` and "lists all five files" omit `tests/test_ai_kit_spec.py` and the goldens. The porcelain list omits them too.
- **LOW**: Node has no mkstemp. Specify `fs.openSync(tmp, 'wx', 0o600)` plus `renameSync`, with the directory at 0700. Two concurrent runs on one lane race on the lane+model key.

### 25-07
**Strengths**
- Orchestrator-only, refuses an edited dogfood, and compares the body with line 2 excluded. The CONFIG key comparison was added.

**Concerns**
- **HIGH** (Task 1 `<automated>`): the Python one-liner does not parse. `rest[rest.find(b"// </config>"):)(*s.split_header(x)` mixes a `[` with a `)`; `ast.parse` raises `SyntaxError: closing parenthesis ')' does not match opening parenthesis '['`. The rail-7 barrier can never go green. Fix: write it as a here-doc script under `tmp/p25/07/`, as the action itself suggests.
- **MEDIUM** (must-haves, lines 22-23): two truths contradict the rulings.
  - "router-inferred … cycles instead of stopping" contradicts "only a confirmed route gets router-quota cycles".
  - "600 s cooldown inside the 1800 s window" contradicts "quota cycles span runner calls".
  - Fix: rewrite both. Then either have the orchestrator set `routerBacked: {pi: true}` once the owner confirms, or state that the dogfood stops and reports.
- **MEDIUM** (lines 94-98, 213): the real-home mtime check starts too late and covers too little.
  - The baseline is taken at 25-07, after six delegated runs, and covers only two paths.
  - Task 2 says "from Task 1", but Task 1's action never records it.
  - Fix: take the baseline before 25-01, include `~/.pi`, `~/.codex` and `~/.cursor` config paths (stat only), and put it in an explicit step.

### 25-08
**Strengths**
- `strip_model_suffix` normalization and malformed-entry handling are in.
- No import cycle: `routing.py` imports only `cache`, `detection` and `model_catalog`.
- `runner_env` gives a scratch `HOME`, so the e2e test's cycle state file stays hermetic.

**Concerns**
- **MEDIUM** (all orchestrator_verify barriers, e.g. 25-08-PLAN.md:16): the barriers chain with `;`. The overall exit is only the last `test -z` or `diff`, so a red `make test` or `make validate` never fails the barrier, and "BARRIER green" overstates what was verified. Fix: `set -e`, or `&&` throughout.
- **MEDIUM** (wave 8, with 25-09): both plans go to pi in the same worktree. If they are dispatched concurrently, each runner's tree snapshot sees the other's edits: tree turns dirty, rung 2 stops on dirty-tree, no_change is misattributed, and `make test` runs over half-edited files. Fix: state that wave-8 dispatches run one after the other.

### 25-09
**Strengths**
- The `real_error` capability escalation is removed and pinned. A1 is labelled pending, and the 3-4 line pointer follows Placement.

**Concerns**
- **HIGH** (lines 62-63, 191-192, 282-287; also 25-10 Task 1): this contradicts the binding cycle-1 ruling ("the caller waits — the orchestrator's one-shot wake or the execute skill's loop — and re-invokes") and the Rule adjustment ("wait several minutes before trying again").
  - Both execute skills STOP on exit 75, and "no run schedules anything".
  - The text test bans `CronCreate`, which is the one-shot wake the ruling names.
  - The GSD skill forbids only retrying auth, billing or bad_model, so an agent may retry a quota stop at once without the 600 s wait.
  - `<interfaces>` describes the superseded in-call cooldown, so the policy reference would document the wrong model.
  - Result: nothing ever drives cycle 2.
  - Fix: document the `retry_after_s`/`cycle=`/state-file/exit-69 contract, and allow exactly one one-shot wake at `retry_after_s` for a confirmed-router exit 75. Ban only recurring or hourly wakes. Or get the owner to amend the ruling.

### 25-10
**Strengths**
- The upgrade-behavior wording is now precise (`.new` file, line-2 header).
- The stale-text baselines are calibrated, and the kit parser is real.

**Concerns**
- **MEDIUM** (Task 3, C7): C7 is stale and incomplete.
  - "cooldown cycles stay inside one runner call (A4)" contradicts the ruling and 25-06's amended A4.
  - C7 also lacks items other ledgers say were sent to it: D-08 router-tail `[401]`/credential rows against the owner's step 3 (25-06 A2), the timeout "deadline permits" reading (25-05), and the review-mode rung-1 resume interpretation.
  - Fix: rewrite A4 and add the three items.
- **LOW** (Task 3 secret scan): `rg -n -i 'sk-|token|key' tmp/` prints any key it finds. Use `rg -l`.

### 25-11
**Strengths**
- The judge set is updated to Opus + `my-referee-one` + `my-referee-two`, with twelve report files.
- Verdicts are parsed, `BLOCKED` stays blocked, and the gates are orchestrator-only. The upstream CONTEXT paths exist.

**Concerns**
- **LOW** (must-haves edge ledger): "R5 concurrency and idempotency (no state file)" is marked superseded, but 25-06 now ships a state file. Reclassify it as adapted to 25-06 (atomic write, lane key).

## Overall Risk

**HIGH as written.** The ladder design follows the owner sections, but four of the HIGHs block execution outright: 25-01's review-only cases, 25-06's cap defaults, 25-07's syntax error, and the 1800 s window. Two contradict binding rulings: the template-6 fallback still active during 25-01..25-06, and the missing `retry_after_s` consumer in 25-09/25-10. 25-05's timeout rung and 25-06's state-file lifecycle would ship behavior that only looks implemented.

The fixes are mechanical:
- set the hook flags (`--prefer pi`, `--outer-timeout 3600`);
- correct the case premises and the `writeCopy` defaults;
- add a per-attempt timeout and state-file cleanup;
- rewrite the verify one-liner;
- choose who waits on `retry_after_s`.

After that the risk drops to MEDIUM, mostly the unverified cursor and claude rows and the redactor's coverage.

I did not run any self-test, `make` target or judge, and did not open the 25-RESEARCH section 2 evidence row by row. So the per-fixture expected classes (for example `opencode-requires-key` → auth) are checked against the plan's own table order, not the raw captures.

CYCLE_SUMMARY: current_high=8 current_actionable=18


# Cycle 3 (2026-10-24, final)

## referee-one, cycle 3 (verbatim)

## Summary

The plans are substantially improved, but **not ready for unattended execution**. Most earlier HIGHs have real task-body fixes: the initial supervisor is pinned to one CLI, dispatch deadlines are raised, review-only cases use Claude, inferred routes no longer authorize quota recovery, session IDs persist, and the judge checks recompute the pass rule.

Remaining blockers concern timeout tests, quota-cap enforcement and state lifecycle, the dogfood verification command, and contradictory caller instructions.

I read all 11 plans, both review cycles, the binding owner sections, research and validation documents, and the relevant local implementation. All **27 actual task `<automated>` blocks pass `bash -n`**; the two Python heredoc bodies parse. Those syntax checks do not establish that their assertions pass. The findings below identify behavioral contradictions separately.

Paths below are relative to `.planning/phases/25-quota-aware-cross-ai-subprocess-supervision/` unless otherwise stated.

### 25-01

**Strengths**

- Task 1 now inverts `claude-exec-late-usage`, not merely the newly added cases.
- Initial dispatch setup expressly pins template 6 to pi and supplies the longer outer deadline.
- The no-second-CLI matrix checks actual fake call logs and reaps the sticky hang fake.

**Concerns**

- **MEDIUM — `25-01-PLAN.md:12`, shared with 25-02 through 25-06 and 25-10:** The orchestrator barriers still separate gate assertions with `;`. A failed `make test` or `make validate` can be followed by a successful clean-tree check, making the overall command succeed. This earlier concern remains unresolved in these bodies. **Fix:** make every failed gate terminate the barrier explicitly, or use one fail-fast `&&` chain. Apply the repair to all affected barriers rather than only 25-08/25-09.

### 25-02

**Strengths**

- The exact pattern-schema test is updated alongside the implementation.
- Runtime-built sentinels, split-token coverage, and full-log scanning address the previous secret-test weaknesses.
- Structured event extraction and answer-text negatives exercise the correct trust boundary.

**Concerns**

- **MEDIUM — `25-02-PLAN.md:342`, Task 1 acceptance:** Its required smoke run names `pure-classify-edge-empty`, `pure-classify-codex-usage-limit-clock`, and `pure-classify-opencode-monthly-limit-router`, but Task 2 creates `CLASSIFY_CASES` and pure-case support at lines 362–365. At Task 1’s checkpoint these names are unknown. **Fix:** use existing cases plus the sentinel for Task 1’s smoke check, or move the minimal pure harness and those three fixtures into Task 1.

- **MEDIUM — `25-02-PLAN.md:305–313`; `25-04-PLAN.md:232–240`:** The redaction relay buffers complete stderr lines without a size bound; 25-04 then plans another splitter with a separate 64 KiB bound. A newline-free child can grow the relay buffer indefinitely, even when the detector stays bounded. This is also duplicated stream-processing logic. **Fix:** share one bounded splitter between detection and relay, preserving the pre-trim classifier match and suppressing or safely redacting overlong lines. Add one overlong-line sentinel case.

### 25-03

**Strengths**

- The quoted heredoc fixes the earlier JSON-escaping failure.
- Seven fixtures consistently produce seven expected lines.
- Confirmed-route classification is distinguished from diagnostic `router-inferred`, including the expected billing exit.

**Concerns**

None beyond the shared barrier issue recorded under 25-01. I would not reopen the already-adjudicated router-hint parity design in this final cycle.

### 25-04

**Strengths**

- The pre-trim partial-buffer match genuinely addresses the earlier newline-free flood loss.
- The transient-timeout negative now keeps its signal intact instead of passing because the signal disappeared.
- Codex’s recovered bare error and terminal `turn.failed` are tested separately.

**Concerns**

- **HIGH — `25-04-PLAN.md:250–252`, combined with `25-02-PLAN.md:254–255`:** Only terminal rows may reclassify a timeout, while bare 429 and rate-limit wording are deliberately non-terminal. A child that prints `429 Too Many Requests` and then hangs therefore becomes an ordinary timeout and enters the transient ladder, even though it emitted a rate-limit signal. This **contradicts the locked cycle-1 timeout ruling**: a timeout with a quota/rate-limit signal must retain that classification. **Fix:** separate eligibility for *live killing* from eligibility for *post-hoc classification*. Keep retry notices non-killing, but classify a failed/timed-out attempt from its captured quota evidence. Add a bare-429-then-timeout case through `main`.

### 25-05

**Strengths**

- The plan now introduces an actual per-attempt deadline rather than relying on a pure ladder test.
- Session-ID and input assertions verify the 3+3 sequence without changing CLI or model.
- The plan-level `<files>` union is now an explicit recorded decision, rather than an unanswered earlier finding.

**Concerns**

- **HIGH — `25-05-PLAN.md:269,279–299`, Task 1:** `ladder-timeout-then-ok` cannot pass as specified. It gives the whole call `--timeout 60`, requires a first attempt lasting 10 seconds, and admits another rung only when at least 60 seconds of work remain. After the first attempt, fewer than 50 seconds remain. Moreover, subtracting the required 60-second reserve from the initial 60-second budget leaves no attempt budget. **Fix:** give this case more than 70 seconds of call budget, plus cleanup slack; its actual runtime can still be about 10 seconds. Define the no-budget case with a concrete shorter call deadline that cannot admit a second rung.

- **MEDIUM — `25-05-PLAN.md:259–261,318–320`:** The implementation adds `attemptTimeoutS: 240`, but the exact CONFIG-test update lists only the two retry-count keys. The current `test_header_and_config_contract` compares the entire dictionary (`tests/test_ai_kit_spec.py:11822–11837`), so following the listed update leaves it red. **Fix:** explicitly add `attemptTimeoutS: 240` to the expected dictionary in this same task.

### 25-06

**Strengths**

- Cooldown now spans calls, and tests no longer require a 600-second sleep.
- Persisted session IDs and cumulative attempts make the second invocation test meaningful.
- Boundary arithmetic, self-test CONFIG defaults, runtime sentinels, and version/golden updates are substantially corrected.

**Concerns**

- **HIGH — `25-06-PLAN.md:285–288,312–313`:** Requiring 60 seconds of cap headroom before a rung does not bound the child’s duration. With 90 seconds left before the quota cap, the predicate admits a child whose configured attempt timeout is 240 seconds. The task asserts that attempts are bounded by the remaining cap but does not wire that bound into the child timer. This leaves the earlier cap HIGH unresolved and **contradicts the locked four-hour limit**. **Fix:** clamp every quota attempt and backoff to the absolute quota deadline as well as the call deadline. Add a black-box case admitted shortly before expiry that is stopped at the cap.

- **HIGH — `25-06-PLAN.md:301–311,338–340`:** Expired-state handling still has two incompatible outcomes. Re-entry must read an expired file and exit 69 before spawning, but `stale-state-fresh-start` seeds an expired file and expects seven calls after automatically resetting it. No flag or other discriminator distinguishes a continuation from a fresh run. **Fix:** make ordinary re-entry fail closed at expiry. Define a separate explicit fresh-start/reset operation if needed, and test both paths. Do not let ordinary caller retries silently restart the four-hour window.

- **HIGH — `25-06-PLAN.md:296–307`:** Keeping the quota budget lane/model-keyed follows the binding ruling, but automatically resuming its `last_sid` also joins unrelated tasks. Task B on the same worktree/lane/model can resume Task A’s session with only `RESUME_MSG`; B’s prompt is then not delivered. **Fix:** keep the lane/model cap key unchanged, but attach a task/objective identity to the resumable session reference. Resume only when that identity matches; otherwise start a fresh permitted session with B’s original prompt. This does **not** require the previously rejected task-keyed quota budget.

### 25-07

**Strengths**

- The comparison script is now valid Python, and the full preference list is checked.
- The dogfood claim correctly says an unconfirmed route gets no quota cycles.
- Re-rendering remains orchestrator-only and refuses an edited active runner.

**Concerns**

- **HIGH — `25-07-PLAN.md:200–221`, Task 1 verification:** The header regex ends in `[$]`, which matches a literal dollar sign, not end-of-line. A correctly stamped runner fails it; I checked this predicate against a synthetic valid header. Also, the command after the heredoc starts independently, so a previously created `check_dogfood.py` can still run after the preceding chain fails and mask that failure. **Fix:** use `$` as the anchor, remove the old check script before verification, and make the post-heredoc execution conditional on successful completion of the preceding checks. The Python syntax HIGH is resolved; this verification HIGH is not.

### 25-08

**Strengths**

- Variant normalization reuses `strip_model_suffix`.
- Nested malformed runtime rows are now explicitly guarded.
- The route test runs the actual runner with a synthetic catalog, rather than merely asserting a mock’s argv.

**Concerns**

- **HIGH — Task 1 and the “same policy” claim at `25-08-PLAN.md:25–28`:** Confirmed-route enforcement covers Python dispatch, but not all rendered-runner producers. Current curated-config `plan_edit._plan_set_script_model` sets `router_backed` from `bool(row["is_router"])` (`skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/plan_edit.py:213–217`), and rendering copies that directly into `CONFIG.routerBacked`. It does not require confirmed `fallback_quota`. A heuristic router row—or a confirmed `fallback_quota: false` row—can therefore become an authoritative router route in a rendered copy. This **contradicts locked D-05 and the confirmed-route ruling**. **Fix:** include the curated-config producer in scope and derive this authorization from the confirmed quota field; test `plan-set` → render with inferred-router and confirmed-false cases.

- **MEDIUM — `25-08-PLAN.md:5–6`; `25-09-PLAN.md:5–6`:** Both plans remain in wave 8 with only 25-07 as a dependency. The shared rules serialize template edits, not these two dispatches. Even with no declared file overlap, concurrent full-permission runs in the same worktree contaminate each other’s tree snapshots and dirty-tree decisions. The earlier concurrency concern is still unhandled. **Fix:** explicitly serialize these dispatches, preferably with a dependency between them.

### 25-09

**Strengths**

- The failed-dispatch capability escalation is removed from the superpowers branch.
- The new caller paragraph recognizes the cross-call quota contract.
- The instruction-file pointer remains short and points to the runner.

**Concerns**

- **HIGH — `25-09-PLAN.md:268–269,279–289,322–335`:** The new caller exception is appended to contradictory instructions that still say “never schedule a wake,” “nothing is scheduled,” and that the owner re-invokes. The canonical reference itself is instructed to prohibit every wake. An executor following those sentences can still strand the first quota cycle. This earlier HIGH is only partially resolved and **contradicts the locked cross-call caller ruling**. **Fix:** replace the absolute bans throughout the objective, canonical reference, NEVER list, and branches with one consistent rule: only a confirmed-router exit 75 carrying the cycle tokens gets the same-lane delayed re-entry; other stops remain owner-controlled.

- **HIGH — `25-09-PLAN.md:289–296,354–355`:** The prescribed checks cannot pass the prescribed text. Task 1 requires the sentence “never a recurring or hourly job,” while `wake_lines` and its shell gate reject either word anywhere. Task 2 explicitly adds `CronCreate`, while its verification rejects every `CronCreate` occurrence. **Fix:** keep the existing negative-wording checks only if the prose avoids those words; otherwise test forbidden scheduling instructions rather than every mention. Update Task 2’s gate to accept the same one-shot `retry_after_s` exception as Task 1.

### 25-10

**Strengths**

- C7 now describes cross-call cooldown and includes the previously omitted owner interpretations.
- The capture-kit scan lists filenames instead of printing potential secrets.
- The docs explicitly distinguish inferred routes from quota-cycle authorization.

**Concerns**

- **HIGH — `25-10-PLAN.md:231–242`, Task 1:** Review lanes still have no consumer for exit 75’s `retry_after_s`/`cycle` contract. The task says a persistently failing lane is merged as failed, but does not instruct the review orchestrator to schedule and re-invoke that same confirmed-router lane. The execute-skill fix in 25-09 does not cover this caller. This **contradicts the locked caller ruling** for router quota cycles. **Fix:** add the same bounded same-lane continuation contract to the review caller, with a small instruction check for the cycle-token branch; ordinary terminal failures can still merge as failed.

### 25-11

**Strengths**

- The correct three-judge set is used throughout.
- The verdict script now recomputes the pass/no-regression rule from recorded numbers.
- Scoped reference fixes are authorized, and final long-running gates remain orchestrator-only.

**Concerns**

- **LOW — `25-11-PLAN.md:46,286–288`:** The formal acceptance amendment still promises a “task-keyed lane key,” while 25-06 explicitly retains a lane/model-keyed quota budget under the binding ruling. This would commit a false description of the implemented state scope. **Fix:** describe the lane/model budget accurately, and distinguish any task-bound session-continuation guard from that budget key.

## Overall Risk

**High until the listed blockers are corrected.** The remaining issues are concentrated: an impossible timeout fixture, incomplete absolute cap enforcement, ambiguous expired-state handling, cross-task session reuse, a broken dogfood predicate, and inconsistent callers/checks for delayed quota cycles.

The strict template chain and orchestrator-only re-render boundary are sound. I found no reason to repeat the already-adjudicated proposals to merge the large runner plans or remove their CONFIG seams; doing so now would add churn without resolving these concrete failures.

Not checked: no plans, suites, AI CLIs, judges, vendor calls, or network requests were executed; no files or git state changed, and no prohibited credential or real-home configuration files were read. Live CLI behavior remains unverified where the plans label it so.

CYCLE_SUMMARY: current_high=10 current_actionable=6

## referee-two, cycle 3 (verbatim)

# Phase 25 plan review — cycle 3 (final)

## Summary

I re-read all 11 plans, the binding sections of 25-SPEC.md/25-CONTEXT.md (Owner decision, Placement, Rule adjustment, cycle-1 orchestrator rulings), both prior review cycles, and verified the plans' load-bearing claims against the tree: template-6 baselines (`tryNextCli` 2, `trying the next CLI` 3, `retry-later` 9, `action=fallback` 12, `action: '…'` rows 20 — all exact), `finish`/`STATUS_TABLE`/`writeCopy` (`backoffS: [0,0]`, `retries: 2`), `RUNTIMES.claude.exec: null` (line 326), `claude-exec-late-usage` (2253), `reviewOnly = cands.find` (2885), `ctx.elapsedMs` (1432), `test_header_and_config_contract` (11804, **exact-dict** `assertEqual`), `test_patterns_block` (11864), the 7 goldens pinning `"version": 6`, the 8 `template=6` test literals, e2e `fake/capacity` rows (`[600]` review / `30` exec) and both 180 s caps (225/316), `RunnerSpec`/`RunnerSeams`/`runner_flags`/`build_runner_argv`, `strip_model_suffix` (routing.py:123), `_ROUTER_NAME_HINTS` (model_heuristics.py:9), `split_header`/`script_state`/`template_version`/`plan_runner_upgrade`/`TEMPLATE_VERSION = 6`, `TestGoldenPlans`/`UPDATE_GOLDEN`, the dogfood (pristine template 6, `prefer: [pi, cursor, opencode]`, `outerTimeoutS: 1800`, `routerBacked: {}`), `.planning/config.json` (`cross_ai_timeout: 1800`), and every 25-09/25-10/25-11 text baseline (CronCreate 4/6/2, hourly 2/2/2/1/1, capability-escalated wording, `Retry Step 3…`, curated SKILL.md:192, runner.md:1, README:45, ROADMAP:81).

Every cycle-1 and cycle-2 HIGH I re-checked is genuinely resolved in the task bodies: menu selection (`cands[0]`), sentinel keys built at run time with full-log scans and named redactor patterns, timeout-as-transient-rung with a real per-attempt budget, cross-call quota cycles with `due_at` refusal, state-file cleanup, confirmed-route-only cycles, the 25-07 heredoc verify, the judge set, the `writeCopy` cap defaults, the cap-boundary arithmetic (13.8M+0.6M = 14.4M exactly → inside), and the caller contract for `retry_after_s`. No plan keeps or reintroduces a cross-CLI fallback, a harness/provider/model switch, an unbounded loop, or a real sleep. Two new blocking contradictions remain, both in **25-09**, where prescribed prose trips the plan's own gates.

### 25-01

**Strengths:** Baselines exact against HEAD (verified); the review-only premise is now correct (only `claude` has `exec: null`, line 326) and `claude-exec-late-usage` is renamed/inverted in Task 1; `deadCheck(ctx, ['pi','gc'])`, the implicit `{exit:1}` row, and the exit-75-half-only router rule are all in the task body; the run-rule hook pin (`--prefer pi --outer-timeout 3600`, template 6 honors both flags — verified in the header) closes the live-fallback hole.

**Concerns:**
- **MEDIUM (orchestrator_verify, line 12):** the barrier chains its steps with `;` — a red `make test`/`make validate` still ends with the porcelain `test -z`, so the barrier exits 0 (same defect cycle 2 fixed in 25-08/25-09). Fix: the `e=$?; test "$e" -eq 0 && …` shape of 25-08. Applies to 25-01..25-06 and 25-10 (counted once here).

### 25-02

**Strengths:** Row schema, D-03 tier order with `terminal:false` on bare codes, both opencode event shapes, named redactor patterns with line-buffered relay and split-chunk + Bearer sentinels, `test_patterns_block` rewrite joined to `files_modified` with the module in the verify, xai fixture bounded away from the `grok` prohibition (the test is real at 11841-11855), smoke order for the oversized task.

**Concerns:**
- **MEDIUM (orchestrator_verify, line 13):** `;`-chained barrier (see 25-01); same fix.

### 25-03

**Strengths:** Confirmed-route ruling written into `routeOf`'s contract (inferred keeps base class, `route-heuristic` now expects `billing`/69); heredoc acceptance fixture; seven/seven count; parity test against the real `_ROUTER_NAME_HINTS`.

**Concerns:**
- **MEDIUM (orchestrator_verify, line 14):** `;`-chained barrier (see 25-01).
- **LOW (Task 2, ponytail):** `TestClassifyOnly`'s seven handpicked cases re-drive inputs the runner's own `classify-only-fixtures` case already drives through the same shipped matcher — cross-harness pinning of the CLI parsing is the only new value. Defensible; if trimming, keep the answer-only and `4021` cases only.

### 25-04

**Strengths:** Timeout-ordering fixed at both seams with `post-hoc-timeout-transient-stays` protecting `run_runner_tiers`; pre-trim partial-buffer match preserves an unterminated signal against a newline-free flood; `retry-notice-429-no-kill`; `ctx.elapsedMs` premise verified (line 1432).

**Concerns:**
- **MEDIUM (must-have truth 7; Task 1 `post-hoc-timeout-quota`, Task 2 `post-hoc-timeout-flood`):** under the plan's own pre-trim-match design, an unterminated `quota exceeded` records `liveHit` on the first chunk and the 1500 ms grace kills the child — neither case reaches its `--timeout 3` deadline, so both are live-kill cases despite their names, and the positive post-hoc path (timeout, `liveHit` unset, captured text re-labels the timeout) is pinned only in the negative direction. The only genuinely post-hoc positive scenario (a codex bare `error` carrying limit text, non-terminal live, then hang → timeout → quota) has no case. Fix: rename/expect the live-kill semantics, add the bare-error-then-hang case, and have 25-11's acceptance mapping note that "times out after printing one" is now adapted (the child is stopped at the grace, never the deadline).
- **MEDIUM (orchestrator_verify, line 12):** `;`-chained barrier (see 25-01).

### 25-05

**Strengths:** `attemptTimeoutS` makes the timeout rung real and both black-box cases (`ladder-timeout-then-ok`, `-no-budget`) are correctly designed; the CONFIG pin, e2e `[30]` review tier and the two 180 s caps (verified at 225/316) are all in Task 1; `promptFiles` union recorded under A6; `ctx.sids` outside the repo.

**Concerns:**
- **MEDIUM (Task 1, Python bullet; also 25-06 Task 3 and 25-10 Task 2):** the CONFIG change adds `attemptTimeoutS: 240`, but the `test_header_and_config_contract` update names only `newSessionRetries`/`sameSessionRetries` — and the test is an exact-dict `assertEqual` (tests/test_ai_kit_spec.py:11822-11834). The verify (`3/3 modules passed`) goes red, and the wrong reconciliation (dropping the template key instead of adding it to the expected dict) still passes every self-test case, silently losing the documented knob. Fix: name `attemptTimeoutS: 240` in the expected-dict updates in 25-05 Task 1 and 25-06 Task 3, and in 25-10's runner.md knob list.
- **MEDIUM (orchestrator_verify, line 17):** `;`-chained barrier (see 25-01).

### 25-06

**Strengths:** Cross-call cycle design matches the ruling end to end (exit 75 + `retry_after_s`/`cycle`, 0600 atomic state file with `due_at` refusal, cleanup on non-quota, stale-file fresh start, persisted `last_sid`); cap-boundary arithmetic now consistent with the stated rule; `writeCopy` defaults corrected (`capS: 14400, cooldownS: 0`); all version pins (spec literal, 8 curated-test literals, 7 goldens) covered in one commit with computed values.

**Concerns:**
- **MEDIUM (orchestrator_verify, line 19):** `;`-chained barrier (see 25-01).
- **LOW (Task 1, state file path):** the fallback when `XDG_STATE_HOME` is unset is unspecified — name it (`<home>/.local/state` per XDG) so hermetic scratch-HOME e2e runs provably never touch the real home.

### 25-07

**Strengths:** The verify is now a valid heredoc script comparing the non-CONFIG body (line 2 excluded) and all four preserved CONFIG keys including `prefer`; refuse-if-edited stop; the confirmed-route truth and cross-call cooldown truth are corrected; the real-home mtime baseline is correctly hoisted to before 25-01 and excluded from `rm -rf tmp/p25/07`.

**Concerns:**
- None above nit level.

### 25-08

**Strengths:** Barrier fixed (`&&` + tested exit codes, stat-only baseline re-statted from its own path list); `runtimes[<runtime>]`-is-a-dict guard; `strip_model_suffix` variant normalization; the default-seam construction sites (`ReviewerSeams()`/`ExecuteSeams()`) included in the audit.

**Concerns:**
- **MEDIUM (frontmatter `wave: 8`, with 25-09; unresolved cycle-2 opus concern):** both wave-8 plans are autonomous, delegated to pi in the same worktree, and run rule 1 only serializes *template* plans. Concurrent dispatch means each runner snapshot sees the other's edits (dirty-tree stops, misattributed `no_change`, gates over half-edited files). Fix: one sentence in either plan's run rules — wave-8 dispatches run one after the other.

### 25-09

**Strengths:** The caller contract (one one-shot `CronCreate` at `retry_after_s`, same lane, bounded by the 4-hour cap) resolves the stranded-cycle HIGH and matches the ruling; the `real_error` capability-escalation option is removed and pinned; A1 is pending-owner, not settled.

**Concerns:**
- **HIGH (Task 2 `<automated>`, line 354, vs Task 2 action lines 331-335 and Task 3 line 386):** the verify runs `rg -n -i 'CronCreate|\bhourly\b' …superpowers/SKILL.md …references` and fails on *any* hit, but Task 2's own action adds the caller-contract sentence containing the literal `CronCreate`, and Task 3's text test expects `CronCreate` occurrences filtered by `one-shot`/`retry_after_s`. The verify cannot pass as written. Fix: use Task 1's shape — `rg -n -i 'CronCreate' … | grep -v 'one-shot'` — plus the hourly-only ban.
- **HIGH (Task 1 action lines 288-289 and Task 2 lines 331-335, vs Task 1 verify line 303, Task 2 verify line 354, the text test's `wake_lines`, and the orchestrator_verify line 23):** the prescribed sentence "never a recurring or hourly job" contains both banned words, so `wake_lines` flags it, both task rg checks print `wake left`, and the frontmatter barrier's `\bhourly\b|every hour|recurring` scan fails — the mandated wording trips every anti-wake gate. Fix: reword the disclaimer without the banned literals (e.g. "never a repeated or fixed-interval job"), or make `wake_lines` ignore lines carrying `one-shot` and `retry_after_s` (as `cron_lines` already does).
- **MEDIUM (wave 8):** see 25-08 — this plan is the other half of the sequencing gap.

### 25-10

**Strengths:** All stale-text baselines verified present exactly once; upgrade-behavior wording matches `plan_runner_upgrade` reality; the `router-inferred`-cannot-authorize-cycles sentence is explicit; C7 now carries the cross-call premise plus the three routed items; the kit's secret scan is `rg -l`.

**Concerns:**
- **MEDIUM (orchestrator_verify, line 18):** `;`-chained barrier (see 25-01) — 25-10 kept the old form while 25-08/25-09 were fixed.
- **LOW (Task 2, `## Failure ladder` knob list):** omits `attemptTimeoutS` (same root as the 25-05 pin gap); add it with its 10..1800 clamp.

### 25-11

**Strengths:** Judge set and twelve reports correct; verdicts are machine-checkable and recomputed from recorded numbers; R5 concurrency/idempotency correctly reclassified as adapted to 25-06's state file; 5400 s budgets explicitly orchestrator-time; a scoped `references/` fix is authorized without breaking the staging rule.

**Concerns:**
- **MEDIUM (Task 1 verify, check_verdicts.py lines ~254-259 vs `<fails_when>` line 263):** the script asserts `ok = v == "PASS" and rule and s >= n` for every skill, so a legitimate `BLOCKED`/`UNRESOLVED` verdict fails the barrier — directly contradicting the fails_when prose ("satisfies this check but leaves the phase blocked"). Fix: enforce the pass rule only when the verdict claims PASS (`assert v != "PASS" or (rule and s >= n)`) and let the acceptance criteria handle the blocked terminal state.
- **LOW (Task 2):** 25-CONTEXT D-21 promised a `billing_or_access` reason (amending 18.1 D-12's `billing → auth`); the owner decision superseded it, but no amendment note records that — 18.1 D-12's note covers `transient`/`capacity` only. Add one line to the SPEC acceptance mapping or the 18.1 note.

## Overall Risk

**Medium — dispatchable after two one-edit fixes in 25-09.** The owner's ladder is carried faithfully and verifiably end to end: 25-01 removes the fallback (baselines exact), 25-02..25-04 build labelled classification and live/post-hoc detection, 25-05/25-06 implement 3+3 rungs and cross-call router cycles under a real 4-hour cap with evidence lines, 25-07/25-08 propagate it, the skills stop and relay evidence, and 25-11 judges and amends. Every earlier HIGH is genuinely resolved in task bodies, not just ledgers. The remaining blockers are self-inflicted text-gate contradictions in 25-09 (its own prescribed sentences trip its own bans), plus hygiene: the `;`-chained barriers in six plans would let a red gate pass the orchestrator check, and wave-8 dispatch needs an explicit sequence. Ponytail-wise the structure is heavier than minimal (25-02+25-03 and 25-05+25-06 could be one plan each), but that was raised in cycle 1 and rejected for per-plan green commit boundaries — accepted, not re-litigated.

Not checked: I ran no self-test, make target, AI CLI, judge, or network call (read-only); 25-RESEARCH §2 fixture expectations were checked against the plans' own table order, not the raw captures.

CYCLE_SUMMARY: current_high=2 current_actionable=8

## claude-opus, cycle 3 (verbatim)

# Phase 25 plan review — cycle 3 (final), claude-opus

## Summary

Most of the cycle-2 HIGHs are resolved in the task bodies, not only in the ledgers. These are fixed:
- 25-01: the review-only cases now use `claude`, `claude-exec-late-usage` is inverted, and the hook is pinned (`--prefer pi --outer-timeout 3600`).
- 25-03: an inferred route keeps the base class.
- 25-04: the partial buffer is matched before it is trimmed.
- 25-06: the boundary rule includes the cooldown, `writeCopy` defaults to `capS: 14400, cooldownS: 0`, and `last_sid` is persisted. A due-time refusal is in, the state file is cleaned up and a stale file is reset. The lane+model key is kept per the ruling.
- 25-07: the check is now a heredoc script and the dogfood route claims are corrected.
- 25-10: C7 is rewritten.

Two cycle-2 fixes added new defects, and a third verify can never pass:
- **25-05's per-attempt timeout breaks real runs and its own cases.** The default `attemptTimeoutS: 240` would kill every real exec attempt after 4 minutes, and 25-07 carries that default into the live dogfood. The "remaining deadline minus 60 s" formula also cannot pass `ladder-timeout-then-ok` at `--timeout 60`.
- **25-09's caller contract conflicts with its own text gates.** The added one-shot `CronCreate` / "never a recurring or hourly job" text trips the plan's own bans on `CronCreate`, `hourly` and `recurring`.
- **25-07's header check can never match.** `grep -E '...{64}[$]'` needs a literal `$` character. I confirmed this locally.

What I checked, all read-only:
- template 6 (`STATUS_TABLE`, `finish`, `runOnce`, `runCli`, `resolveDeadline`, `budgetMs`, `hermeticEnv`, `writeCopy`, the production `backoffS` [30, 60], `GSD_DEFAULT_TIMEOUT_S` 300);
- the dogfood line 2 and `.planning/config.json`;
- `cross_ai_script` (`split_header`, `script_state`, `_upgrade_config`);
- `run_runner_tiers` and its caller in `cli.py`;
- the runner groups and the unittest CLI, `test_patterns_block` and `TestStatusMapDrift`;
- `_ROUTER_NAME_HINTS`, `strip_model_suffix`, and the golden `UPDATE_GOLDEN` path.

I ran no self-test, `make` target, AI CLI or network call.

### 25-01
**Strengths**
- `cands[0]`-only selection and the refusal limited to the first entry match the menu ruling. `claude` (`exec: null`, template line 326) is the correct review-only entry.
- `claude-exec-late-usage` is now inverted, so the full self-test can go green. The verify joins steps with `&&` and removes logs first.

**Concerns**
- MEDIUM (orchestrator_verify, line 12; the same barrier text is in 25-02..25-06 and 25-10): the barrier still chains `grep -qx 'exit=0' t.log; timeout 3000 make validate ...; ...; test -z ...` with `;`. Its exit status is only the last `test -z`, so a red `make test` or `make validate` never fails it. The cycle-2 opus MEDIUM was fixed only in 25-08 and 25-09. **Fix:** copy 25-08's form (`e=$?; ...; test "$e" -eq 0 && ...`) into all seven barriers.
- LOW (Task 2, line 307, vs Task 1, line 259): `review-only-later-ignored` (exec, `--prefer pi,claude`, pi answers, no refusal line) repeats `review-only-later-menu-ok` exactly. **Fix:** drop one and update the verify list and the count of "fifteen".
- LOW (run rule 1, lines 107-112): the hook pin and the `cross_ai_timeout` raise are prose only, and nothing checks the effective command before the first dispatch. **Fix:** add an orchestrator pre-dispatch check that `.planning/config.json` holds `--prefer pi --outer-timeout 3600` and `cross_ai_timeout: 3600`.

### 25-02
**Strengths**
- The row schema and the D-03 order are right. The bare-code and rate-limit rows are `terminal: false`, and `test_patterns_block` is rewritten in the same commit.
- The redactor's pattern set is named, it works per complete line with a flush at exit, and two sentinel shapes plus `sentinelsplit` are tested.

**Concerns**
- LOW (Task 1 acceptance, line 342): the smoke order names `pure-classify-*` cases that only Task 2 creates. In Task 1 the self-test exits 2 with `unknown case`. **Fix:** in Task 1 use `quota,billing-router,sentinel-failed-line`, and move the `pure-classify-*` smoke to Task 2.
- LOW (line 322; the same wording is in 25-06 Task 2): "the fake pi mode … builds its key at run time (`'sk-aikit-SENTINEL-' + process.pid` …)". The fake's pid is not the checker's pid, so if the fake builds the key, the check cannot rebuild it. **Fix:** say the case (the parent) builds the key, passes it through the env, and checks for that same value; the fake only reads the env var.
- LOW ("One line comment above the block"): `test_patterns_block` requires `const PATTERNS = ` straight after `// <patterns>\n`. **Fix:** say the comment goes above the marker.

### 25-03
**Strengths**
- `routeOf` precedence is flag, then CONFIG boolean, then heuristic. `routerClass` applies only on a confirmed lane, which follows the ruling.
- The quoted heredoc fixture is valid JSON. The e2e module runs under uv and the unit module under python3, as the runner groups require.

**Concerns**
- LOW (ponytail; Task 2 `TestRouterHintParity` plus the doctored-template test): `router-inferred` now changes no behavior. It is a label only, with no cycles and no `routerClass`. A cross-language parity test with its own non-vacuity case is a lot of machinery for a diagnostic label. **Fix (optional):** keep the one equality test and drop the doctored variant.

### 25-04
**Strengths**
- The partial buffer is matched before it is trimmed, and `post-hoc-timeout-flood` floods without newlines. `post-hoc-timeout-transient-stays` has no flood, so it now proves the re-label rule. Classified status wins over `timedOut`.

**Concerns**
- MEDIUM (ponytail plus a stale interface, line 171 and Task 1): 25-02 already adds a per-stream partial-line buffer for redaction. 25-04's `<interfaces>` still says "`runOnce` relays stderr chunks", and Task 1 adds a second splitter with its own 64 KiB cap. Two buffers per stream can drift apart in flush and cap behavior. **Fix:** update the interface and hook the watcher into 25-02's splitter (one buffer, one cap, one flush), adding the pre-trim match there.

### 25-05
**Strengths**
- The 3 + 3 rungs and the `canResume` exclusions are right. The sids file sits outside the repo, `transient` maps to `capacity`, and the CONFIG pin update is in the same commit.

**Concerns**
- **HIGH** (line 260 and the must-have truth; this also hits 25-07): `attemptTimeoutS` defaults to 240 s. Every exec attempt, including real plan executions that run 20-50 minutes, would be killed after 4 minutes. The ladder then resumes it (rung 1) up to 3 times. Rung 2 needs a clean tree or only `<files>` paths changed, so it will usually stop with `why=dirty-tree`. 25-07's `_upgrade_config` merges new template keys at their defaults, so 25-08, 25-09, 25-10 and every upgraded user runner inherit this cap. 25-07 does not even check the key. **Fix:** default `attemptTimeoutS: 0`, meaning no per-attempt cap, so the child timer is the remaining deadline as today. Self-test copies set it explicitly. Document that a call-deadline timeout is terminal unless the owner sets the knob, and add that reading to C7. Make 25-07 assert the dogfood value.
- **HIGH** (lines 296-300, line 164, and the "remaining deadline minus a 60 s reserve" formula): the cases cannot pass as written, under either reading of the formula.
  - **Read literally,** the timer is zero or negative for every short `--timeout` case: `hang` and `no-second-cli-hang` (2 s), `post-hoc-timeout-*` (3 s), the e2e review tier `[30]`, and `ladder-timeout-then-ok` itself (60 s). The child would be killed before it prints anything.
  - **Read as `min(knob, remaining)`,** `ladder-timeout-then-ok` (`--timeout 60`, knob 10) times out at about 12 s. Then `ladderNext`'s `now + wait + 60 s` guard returns `stop`/`deadline`, so the expected 2 calls ending `ok` never happen.

  **Fix:** set the timer to `min(attemptTimeoutS, remaining)`, with the reserve used only for rung admission. Run `ladder-timeout-then-ok` with `--timeout` of at least 90.
- MEDIUM (contradicts the owner's "out of rungs: stop and report"; `runner_dispatch.py:552`, used by `cli.py:126`): an exhausted timeout ladder still ends exit 124. `run_runner_tiers` then calls the runner again for each tier, and each call runs its own 3 + 3, so a lane gets tiers × 7 attempts. **Fix:** end an exhausted timeout ladder `transient`/75 on template 7, or have 25-08 stop the tier loop when `attempts=` is present. Add a test.
- LOW (ponytail): `ladder-timeout-no-budget` repeats `hang`. **Fix:** reuse `hang`. Also note in the SUMMARY that `hangonce` adds about 12 s of real time to the self-test budget.

### 25-06
**Strengths**
- Cycles span calls, with refusal before `due_at`. The cap check is `now + cooldown <= first + cap` and the rung check is `now + 60 s <= first + cap`.
- `last_sid` is persisted, a stale file restarts the cycle, and the state file is written atomically with `wx`, 0600 and 0700.
- The pins, the goldens (seven at `"version": 6`) and the `template=6` gate all match HEAD.

**Concerns**
- MEDIUM (line 308 and the GSD default path): two problems with when the state file is deleted.
  - **Production timing.** The file is deleted on a transient, dirty-tree or deadline stop. With production `backoffS` [30, 60] and the GSD default (270 s inner deadline), a router quota run fits only about 4 attempts and ends `stopped=deadline`. It never reaches `cooldown`, prints no `retry_after_s`, and deletes the state. So no cycle or cap accounting ever starts on the default GSD path.
  - **Flapping.** Alternating quota and transient runs reset `first_seen` each time, so the 4-hour bound is never reached.

  **Fix:** treat a quota-class `deadline` stop as the end of a cycle (write the state, emit `retry_after_s`). Delete only on `ok` and on auth, billing and bad_model stops. Add a case for that.
- MEDIUM (sizing; Task 1): one task holds the quota branch, the state-file format and atomic I/O, due-time refusal, stale handling, `last_sid`, the deletion lifecycle and 12 cases. The re-dispatch skip rule works per commit. **Fix:** split into 1a (in-call quota rungs and pure cases) and 1b (the cross-call state file with its black-box cases), each with its own commit.
- LOW (line 295): "`n` is the completed cycle count", yet the first exit after one cycle expects `cycle=0`. **Fix:** define the two tokens precisely and reuse the same words in 25-09.
- LOW (ponytail; line 342): `inferred-quota-no-cycle` (billing exit 69) repeats 25-03's `route-heuristic`. It misses the ruling's real path: an inferred-route quota stops after one call with no state file. **Fix:** add a `router-env-quota` fake mode and expect `quota exit=75`, 1 call, no state file.

### 25-07
**Strengths**
- The plan is orchestrator-only and refuses an edited dogfood. The heredoc check compares the body without line 2 and all four kept CONFIG keys. The route claims now follow the ruling.

**Concerns**
- **HIGH** (Task 1 `<automated>`, line 200): in `grep -qE 'template=7 sha256=[0-9a-f]{64}[$]'`, the `[$]` is a literal dollar sign. The dogfood's line 2 ends at the hash, so the check can never pass; I reproduced NOMATCH, while a plain `$` gives MATCH. **Fix:** use `...{64}$'`.
- MEDIUM (run rule 1, "both are restored after 25-07"): restoring `cross_ai_timeout` 1800 and dropping `--outer-timeout 3600` puts 25-08, 25-09 and 25-10 back on about 1770 s. That contradicts the rule's own "3600 s per plan". **Fix:** restore only after 25-10's barrier. `--prefer pi` can go after 25-07.
- LOW: the check script does not assert `attemptTimeoutS` or record the leftover `retries` key. **Fix:** add both.

### 25-08
**Strengths**
- `resolve_route` passes a flag only for a confirmed boolean, uses `strip_model_suffix`, and handles malformed entries. The `route_fn` seam is right and there is no import cycle. The barrier now really fails on a red gate and checks real-home mtimes.

**Concerns**
- MEDIUM (verify lines 250 and 287): a stale log can make either verify pass. The steps are chained `…; grep … && next > log; grep …` with no `rm -f` first, and the pyright log is appended to with `>>`.
  - In Task 1, a failed unit run skips pyright, and an old `exit=0` line in the log still matches.
  - In Task 2, a failed e2e run skips the unit run, and a stale `u2.log` passes.

  **Fix:** `rm -f` the logs first and join every step with `&&`.
- MEDIUM (wave 8 shared with 25-09; the cycle-2 MEDIUM was not handled): both plans dispatch to pi in one worktree. If they run at the same time, each sees the other's edits as a dirty tree, `make test` runs over half-edited files, and they share one lane state file. **Fix:** state in run rule 1 that every delegated plan runs one after another.

### 25-09
**Strengths**
- The one-shot `retry_after_s` contract now exists, and auth, off-router and cap stops stay owner-controlled. The `real_error` escalation is removed and pinned. The pointer has 3-4 lines and follows Placement.

**Concerns**
- **HIGH** (the cycle-2 fix conflicts with the plan's own gates; this is the ruled caller contract): the verifies cannot pass if the action is followed.
  - Task 1 writes "never a recurring or hourly job" (line 289) into the GSD SKILL.md. Task 1's verify (line 303), `wake_lines` and the barrier fail on that text.
  - Task 2 writes the one-shot `CronCreate` contract into the superpowers SKILL.md. Task 2's verify (line 354) fails on any `CronCreate` there.
  - "This plan" (line 165) bans the literal `CronCreate` everywhere the text test scans.

  **Fix:**
  - Phrase the contract without the banned words.
  - Use the `cron_lines` rule in Task 2's verify: every `CronCreate` line carries `one-shot` and `retry_after_s`.
  - Narrow the plan-level ban to the two Python modules.
- MEDIUM (the canonical reference contradicts the ruling): it says a skill should "never schedule a wake" (line 268), the objective says "no wake of any kind" (line 71), and `<interfaces>` calls the state file "task-keyed" (line 193), while 25-06 keys it by lane and model. Phase 26 will quote this reference. **Fix:** document the one-shot re-invoke and the lane+model key.
- MEDIUM (portability and unverified behavior; Agent Skills rule; D-16): the contract names only `CronCreate`. Other hosts are not covered, and it is still open whether a wake fires while GSD's retry/skip/abort prompt is pending. **Fix:** add "other hosts: print `retry_after_s`, the state path and the re-invoke command (unverified)". Mark firing during a pending GSD prompt as unverified and add it to C7.

### 25-10
**Strengths**
- C7 now states the cross-call contract and the three routed items. The upgrade wording matches `plan_runner_upgrade`. `rg -l` is used for the secret scan.

**Concerns**
- MEDIUM (orchestrator_verify): the barrier is still chained with `;`. It also lacks the real-home mtime comparison that 25-07 promises at this barrier. **Fix:** use 25-08's form, including the `stat | diff` step.
- LOW (lines 276 and 402): "like a direct route" names a route kind that is never built. **Fix:** say "like an unknown route". `runner.md` also omits `attemptTimeoutS`.
- LOW (C7): C7 does not ask the owner about two things: the one-shot `CronCreate` consumer, and review lanes not re-invoking on `retry_after_s`. **Fix:** add both.

### 25-11
**Strengths**
- The judge set is right with 12 reports, verdicts are recomputed from recorded numbers, `BLOCKED` stays blocked, and the gates are orchestrator-only.

**Concerns**
- LOW (`fails_when`, line 263): it says an `UNRESOLVED` or `BLOCKED` verdict "satisfies this check", but the script asserts `PASS`. **Fix:** reword it, and delete the duplicated judge-lane paragraph (lines 219 and 228).
- LOW: the edge ledger says "task-keyed lane key", which conflicts with 25-06. `25-VALIDATION.md:81-82` still lists R5 concurrency and idempotency as superseded and says "no skill wake". **Fix:** align both with 25-06 and 25-09.

## Overall Risk

**HIGH as written, but every fix is mechanical.** Two HIGHs block execution outright: 25-07's `[$]` regex and 25-09's self-contradicting gates. 25-05's `ladder-timeout-*` cases cannot pass under either reading of the timer formula. The serious product risk is 25-05's `attemptTimeoutS: 240` default. Through 25-07's config merge it would cut every real exec attempt at 4 minutes, including this phase's own later runs.

No plan reintroduces a CLI fallback or a harness, provider or model switch. No test calls a real vendor or writes the real home. Sentinels are built at run time. Two places still loop past the owner's caps: the Python tier loop multiplies the 3 + 3 rungs, and deleting the state on transient or deadline stops resets the 4-hour clock. On the default GSD 300 s path, router-quota cycles never start.

The fixes:
- default `attemptTimeoutS` to 0 and use `min(knob, remaining)`;
- remove the brackets from `[$]`;
- reconcile 25-09's bans with its contract;
- `&&`-chain the seven barriers;
- keep the cycle state on quota-class deadline stops.

After those, risk drops to MEDIUM.

CYCLE_SUMMARY: current_high=4 current_actionable=25

---
I did not check RESEARCH §2's raw captures against each fixture's expected class, and I ran no self-test, so the timing arithmetic (about 4 attempts in 270 s, about 12 s for `hangonce`) is derived from the code, not measured. The review is also saved to `<home>/.claude/plans/you-are-a-senior-async-brook.md`.


## Escalation at the cycle cap

jev ladder: Laya B (fallback 0.52), TypeSafe A (0.97, decided). The orchestrator rules on the remaining HIGHs (25-CONTEXT.md "Cycle-3 rulings"), a cross-AI amend run applies every cycle-3 fix, and the orchestrator verifies the HIGHs line by line before execution.
