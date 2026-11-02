DIGEST a4b2dbc04b1e3984
TREE e66c5517ddd061ac498331ff8134815b4e616d5c

# Skill evaluation: `jev-fast-decision`

Read-only static review of `SKILL.md`, `reference.md`, all three backend notes, the named client, and the supporting evaluation files. No files changed or scripts executed. External API behavior was not live-verified; the findings below concern observable inconsistencies within the reviewed files.

## Activation picks

These choices were recorded **before opening any skill body**, using only the `name` and `description` fields of all 22 listed skills.

Fixture: `.planning/phases/21.1-atomic-reusable-decision-system-skills/skill-judge/activation.jsonl`.

| Line | Single pick | Reason |
|---|---|---|
| 1 | `jev-fast-decision` | Yes/no screening of supplied findings and evidence. |
| 2 | `jev-fast-decision` | Bounded choice among named titles. |
| 3 | `jev-fast-decision` | Rubric scoring of supplied report text. |
| 4 | `jev-fast-decision` | Yes/no screening of supplied grep hits. |
| 5 | none | Code and test edits are explicitly excluded. |
| 6 | none | Call-chain investigation requires a full reasoning pass. |
| 7 | none | Command execution and repairs are not advisory judgments. |
| 8 | none | Multi-step migration planning and implementation are outside the description. |
| 9 | none | In-app TypeSafe integration is excluded; `typesafe-ai` is not among the listed frontmatter names. |
| 10 | none | Product-feature brainstorming is not a bounded typed judgment. |
| 11 | none | Application-code TypeSafe integration is explicitly excluded. |
| 12 | none | Building an in-app ranker and backend integration is explicitly excluded. |

All four expected positive cases selected `jev-fast-decision`; none of the other eight selected it.

## Part 1 — Dimensions

D1 18/20 — 90.0%. Strong knowledge delta: consent semantics, state contamination, capability provenance and truncation guards. Trim repeated warnings.
D2 13/15 — 86.7%. Good advisory-versus-verification mindset and probe-first workflow. Reconcile the documented escalation procedure with implementation.
D3 14/15 — 93.3%. Specific anti-patterns address concrete consent and batching failures, with supporting rationale in backend notes. Some warnings repeat.
D4 15/15 — 100%. Valid frontmatter, precise WHAT/WHEN/keywords, explicit exclusions, and successful activation separation.
D5 13/15 — 86.7%. Compact body with explicit backend/reference loading triggers. Make unsupported-feature web reading conditional rather than universally required.
D6 13/15 — 86.7%. Appropriate constraints around transport, consent and backend selection, while retaining agent judgment. Explicitly assign responsibility for failed or missing item results.
D7 9/10 — 90.0%. Clear Navigation/Tool hybrid: backend selection, invocation, interpretation and safeguards. Conditional reading guidance would sharpen the navigation pattern.
D8 9/15 — 60.0%. Below floor 12. Improvement: repair and test default Zen routing, reconcile free-to-paid behavior, and add an explicit per-item error/missing-answer recipe.

## Findings

### Important

1. **Default Zen request URL contradicts the backend instructions.**  
   `skills/jev-fast-decision/backends/opencode.md:9–13` identifies `/zen/v1/systemone` as the default System One path. However, `skills/jev-fast-decision/scripts/jev_review.py:740–741` returns `https://opencode.ai/zen/v1`, and `:1385` posts directly to that URL without appending `/systemone`. Thus the default invocation does not address the documented endpoint. Resolve the discrepancy and test the actual default POST path, not only an overridden fixture URL.

2. **Documented free-to-paid transitions differ materially from the client.**  
   `skills/jev-fast-decision/backends/opencode.md:21–24` promises transition to the paid ID on 5xx, network failure, or a specific “Model is unavailable” 400, without retrying the free ID. In contrast, `skills/jev-fast-decision/scripts/jev_review.py:777–794` retries 5xx, escalates network failures, and treats every 400 as a caller error; the error body is discarded without inspecting that message. `:1443–1450` retries the same model and then escalates rather than selecting the next model. Establish the verified policy, then align implementation, notes and tests.

3. **The result recipe omits partial failures under `status: ok`.**  
   `skills/jev-fast-decision/SKILL.md:38–40` directs the agent to process `answers`, but gives no action for `errors` or requested IDs absent from `answers`. `skills/jev-fast-decision/reference.md:24` mentions item-level failures without supplying that recipe. The client explicitly permits an `ok` result containing both answers and errors (`skills/jev-fast-decision/scripts/jev_review.py:1704–1720`), also demonstrated by `tests/test_jev_fast_decision.py:752–767`. Require reconciling every requested ID and independently reasoning about failed/missing items, or explicitly repairing and retrying them.

### Minor

1. **Repeated safeguards consume avoidable body tokens.**  
   `skills/jev-fast-decision/SKILL.md:45–59` repeats consent, batching and fallback warnings across NEVER, Red Flags and Common Mistakes. Preserve the concrete rationalization triggers, but consolidate duplicated instructions.

2. **Required reading includes unsupported functionality unconditionally.**  
   `skills/jev-fast-decision/SKILL.md:61–66` requires image and broader release documentation even though the client cannot build image or box requests. Make those links conditional on feature inquiries; retain essential primitive and interpretation guidance.

### Special check — `needs_fallback`

**Present**, at `skills/jev-fast-decision/SKILL.md:38`:

> `needs_fallback: true` → **you decide that item with your own reasoning**; else advisory input.

CURRENT 104/120
CRITICAL 0
IMPORTANT 3
FLOORS fail
ACTIVATION ok
CITE_PROBE skills/jev-fast-decision/SKILL.md:12
> From this skill's directory, run `python3 -B scripts/jev_review.py --probe` before the first call of a session; read `backends/<selected>.md` before the first call with that backend.
CITE_BACKEND skills/jev-fast-decision/SKILL.md:12
> From this skill's directory, run `python3 -B scripts/jev_review.py --probe` before the first call of a session; read `backends/<selected>.md` before the first call with that backend.
VERDICT fail

DIGEST 587d8e67ccf3cb82
TREE ee1c913dd4478e903914716f04660c66795043a7

# Skill evaluation: `jev-fast-decision`

Static, read-only review of `SKILL.md`, `reference.md`, all three backend notes, both bundled scripts, the evaluation cases, and the cited evaluation results. The large client script was read in chunks. No files were edited or scripts executed. The four linked external documents could not be fetched with the supplied tools.

**Pattern:** Navigation/Tool hybrid. **Estimated Expert:Activation:Redundant ratio:** 80:15:5.

## Part 1 — Dimensions

D1 18/20 — 90% — Strong knowledge delta: backend-specific contamination, truncation guards, confidence interpretation and consent boundaries. Consolidate repeated consent and batching reminders in `skills/jev-fast-decision/SKILL.md:45–57`.

D2 14/15 — 93.3% — The probe → backend notes → call → per-item interpretation sequence transfers useful domain procedures. Improve the executable request example identified below.

D3 14/15 — 93.3% — Specific NEVER rules address real failure modes, with supporting explanations in the backend notes. Align the example’s “your grep output” placeholder with the prohibition on sending raw sources.

D4 15/15 — 100% — Valid frontmatter with a matching name, explicit capabilities, searchable primitive/backend names and clear exclusions. All activation cases satisfy the requested routing rule.

D5 13/15 — 86.7% — Compact body with explicit backend and reference-loading triggers. The unconditional external “Required reading” list weakens otherwise effective conditional disclosure.

D6 14/15 — 93.3% — Appropriate constraints on consent, explicit backend overrides, batching and advisory interpretation. Correct the contradictory calibration claim so agents do not overestimate the retained threshold.

D7 9/10 — 90% — Effective Navigation/Tool combination: small routing body, precise client invocation and backend-specific resources. Make external reading scenario-dependent to complete the navigation pattern.

D8 11/15 — 73.3% — Common paths and fallback instructions are clear, but HTTP-error handling can exceed the documented whole-run deadline. **Below floor:** meet the rubric’s comprehensive edge-case/error-handling standard by keeping the watchdog active during error-body draining, passing the remaining deadline through that path, and adding slow-dripping 4xx/503 response tests.

## Findings

### Important — HTTP error-body reads escape the whole-run deadline

**Files:** `skills/jev-fast-decision/scripts/jev_review.py:226`, `:1319–1322`, `:1387`, `:1436`.

When `opener.open()` raises `HTTPError`, `_exchange()` exits and cancels its watchdog. Classification subsequently calls `_error_body()`, which invokes `_read_body()` without a deadline.

A server returning an error body slowly enough to avoid individual socket timeouts can therefore keep the client reading beyond `GSD_PATH_JEV_DEADLINE_SECONDS`. This contradicts the whole-run bound documented at `skills/jev-fast-decision/reference.md:71`.

**Improvement:** keep deadline enforcement active through error-body processing, or close unread error bodies when their contents are unnecessary. Cover slow-dripping error bodies, including chunk framing, with deadline tests.

### Minor — Retained default is described as successfully calibrated

**File:** `skills/jev-fast-decision/backends/laya.md:37–38`, contrasted with `:61–65`.

The earlier statement says `min_confidence` “is calibrated from the live 32-case eval,” but the evaluation section reports that calibration proposed `null` and the conservative `0.7` default stayed unchanged.

**Improvement:** describe it consistently as a retained conservative default; explicitly state that the evaluation found no qualifying calibrated threshold.

### Minor — Call example requires unstated preparation and safer evidence wording

**File:** `skills/jev-fast-decision/SKILL.md:25–28`.

The shell example contains an unquoted `<port>` placeholder and a literal `"<git rev-parse HEAD>"` inside a quoted heredoc. It therefore requires manual substitution before execution. “Your grep output” also invites raw-source inclusion despite the prohibition at line 47.

**Improvement:** clearly label the block as a template or provide executable variable preparation and JSON construction. Show value-free, sanitized evidence.

### Minor — External reading is unconditional

**File:** `skills/jev-fast-decision/SKILL.md:59–64`.

Every invocation apparently requires four external documents, including image documentation even though this client has no image builder.

**Improvement:** retain essential safety guidance locally and attach explicit loading conditions to version, image and confidence documentation.

## Special check — `needs_fallback`

**Present:** `skills/jev-fast-decision/SKILL.md:38`:

> `needs_fallback: true` → **you decide that item with your own reasoning**

This is an actionable body recipe, not merely a field definition.

## Part 2 — Activation

These picks were recorded before opening any skill body, using only the enumerated frontmatter fields. `typesafe-ai` was not among the 22 available skill names.

| Line | Single skill selected | Reason |
|---|---|---|
| 1 | `jev-fast-decision` | Supplied-evidence yes/no triage matches typed judgment. |
| 2 | `jev-fast-decision` | Selecting one named title matches `choice`. |
| 3 | `jev-fast-decision` | Applying a severity rubric matches `score`. |
| 4 | `jev-fast-decision` | Screening supplied hits matches yes/no evidence screening. |
| 5 | none | Script and test editing is explicitly excluded. |
| 6 | none | Call-chain investigation is not a bounded typed judgment. |
| 7 | none | Running checks and fixing failures is implementation work. |
| 8 | none | Planning and implementing a migration exceeds advisory judgment. |
| 9 | none | Application integration is excluded; `typesafe-ai` is unavailable. |
| 10 | none | Product-primitive ideation is outside scope; `typesafe-ai` is unavailable. |
| 11 | none | Application-code integration is excluded; `typesafe-ai` is unavailable. |
| 12 | none | Building a product-facing backend feature is excluded; `typesafe-ai` is unavailable. |

All four expected-positive cases select `jev-fast-decision`; none of the eight negative cases selects it. The overall verdict fails because D8 is below its floor.

CURRENT 108/120
CRITICAL 0
IMPORTANT 1
FLOORS fail
ACTIVATION ok
CITE_PROBE skills/jev-fast-decision/SKILL.md:12
> From this skill's directory, run `python3 -B scripts/jev_review.py --probe` before the first call of a session; read `backends/<selected>.md` before the first call with that backend.

CITE_BACKEND skills/jev-fast-decision/SKILL.md:12
> From this skill's directory, run `python3 -B scripts/jev_review.py --probe` before the first call of a session; read `backends/<selected>.md` before the first call with that backend.

VERDICT fail
DIGEST 587d8e67ccf3cb82
TREE ee1c913dd4478e903914716f04660c66795043a7

# Skill evaluation: `jev-fast-decision`

Static, read-only review of `SKILL.md`, `reference.md`, all three backend notes, both bundled scripts, the evaluation cases, and the cited evaluation results. The large client script was read in chunks. No files were edited or scripts executed. The four linked external documents could not be fetched with the supplied tools.

**Pattern:** Navigation/Tool hybrid. **Estimated Expert:Activation:Redundant ratio:** 80:15:5.

## Part 1 — Dimensions

D1 18/20 — 90% — Strong knowledge delta: backend-specific contamination, truncation guards, confidence interpretation and consent boundaries. Consolidate repeated consent and batching reminders in `skills/jev-fast-decision/SKILL.md:45–57`.

D2 14/15 — 93.3% — The probe → backend notes → call → per-item interpretation sequence transfers useful domain procedures. Improve the executable request example identified below.

D3 14/15 — 93.3% — Specific NEVER rules address real failure modes, with supporting explanations in the backend notes. Align the example’s “your grep output” placeholder with the prohibition on sending raw sources.

D4 15/15 — 100% — Valid frontmatter with a matching name, explicit capabilities, searchable primitive/backend names and clear exclusions. All activation cases satisfy the requested routing rule.

D5 13/15 — 86.7% — Compact body with explicit backend and reference-loading triggers. The unconditional external “Required reading” list weakens otherwise effective conditional disclosure.

D6 14/15 — 93.3% — Appropriate constraints on consent, explicit backend overrides, batching and advisory interpretation. Correct the contradictory calibration claim so agents do not overestimate the retained threshold.

D7 9/10 — 90% — Effective Navigation/Tool combination: small routing body, precise client invocation and backend-specific resources. Make external reading scenario-dependent to complete the navigation pattern.

D8 11/15 — 73.3% — Common paths and fallback instructions are clear, but HTTP-error handling can exceed the documented whole-run deadline. **Below floor:** meet the rubric’s comprehensive edge-case/error-handling standard by keeping the watchdog active during error-body draining, passing the remaining deadline through that path, and adding slow-dripping 4xx/503 response tests.

## Findings

### Important — HTTP error-body reads escape the whole-run deadline

**Files:** `skills/jev-fast-decision/scripts/jev_review.py:226`, `:1319–1322`, `:1387`, `:1436`.

When `opener.open()` raises `HTTPError`, `_exchange()` exits and cancels its watchdog. Classification subsequently calls `_error_body()`, which invokes `_read_body()` without a deadline.

A server returning an error body slowly enough to avoid individual socket timeouts can therefore keep the client reading beyond `GSD_PATH_JEV_DEADLINE_SECONDS`. This contradicts the whole-run bound documented at `skills/jev-fast-decision/reference.md:71`.

**Improvement:** keep deadline enforcement active through error-body processing, or close unread error bodies when their contents are unnecessary. Cover slow-dripping error bodies, including chunk framing, with deadline tests.

### Minor — Retained default is described as successfully calibrated

**File:** `skills/jev-fast-decision/backends/laya.md:37–38`, contrasted with `:61–65`.

The earlier statement says `min_confidence` “is calibrated from the live 32-case eval,” but the evaluation section reports that calibration proposed `null` and the conservative `0.7` default stayed unchanged.

**Improvement:** describe it consistently as a retained conservative default; explicitly state that the evaluation found no qualifying calibrated threshold.

### Minor — Call example requires unstated preparation and safer evidence wording

**File:** `skills/jev-fast-decision/SKILL.md:25–28`.

The shell example contains an unquoted `<port>` placeholder and a literal `"<git rev-parse HEAD>"` inside a quoted heredoc. It therefore requires manual substitution before execution. “Your grep output” also invites raw-source inclusion despite the prohibition at line 47.

**Improvement:** clearly label the block as a template or provide executable variable preparation and JSON construction. Show value-free, sanitized evidence.

### Minor — External reading is unconditional

**File:** `skills/jev-fast-decision/SKILL.md:59–64`.

Every invocation apparently requires four external documents, including image documentation even though this client has no image builder.

**Improvement:** retain essential safety guidance locally and attach explicit loading conditions to version, image and confidence documentation.

## Special check — `needs_fallback`

**Present:** `skills/jev-fast-decision/SKILL.md:38`:

> `needs_fallback: true` → **you decide that item with your own reasoning**

This is an actionable body recipe, not merely a field definition.

## Part 2 — Activation

These picks were recorded before opening any skill body, using only the enumerated frontmatter fields. `typesafe-ai` was not among the 22 available skill names.

| Line | Single skill selected | Reason |
|---|---|---|
| 1 | `jev-fast-decision` | Supplied-evidence yes/no triage matches typed judgment. |
| 2 | `jev-fast-decision` | Selecting one named title matches `choice`. |
| 3 | `jev-fast-decision` | Applying a severity rubric matches `score`. |
| 4 | `jev-fast-decision` | Screening supplied hits matches yes/no evidence screening. |
| 5 | none | Script and test editing is explicitly excluded. |
| 6 | none | Call-chain investigation is not a bounded typed judgment. |
| 7 | none | Running checks and fixing failures is implementation work. |
| 8 | none | Planning and implementing a migration exceeds advisory judgment. |
| 9 | none | Application integration is excluded; `typesafe-ai` is unavailable. |
| 10 | none | Product-primitive ideation is outside scope; `typesafe-ai` is unavailable. |
| 11 | none | Application-code integration is excluded; `typesafe-ai` is unavailable. |
| 12 | none | Building a product-facing backend feature is excluded; `typesafe-ai` is unavailable. |

All four expected-positive cases select `jev-fast-decision`; none of the eight negative cases selects it. The overall verdict fails because D8 is below its floor.

CURRENT 108/120
CRITICAL 0
IMPORTANT 1
FLOORS fail
ACTIVATION ok
CITE_PROBE skills/jev-fast-decision/SKILL.md:12
> From this skill's directory, run `python3 -B scripts/jev_review.py --probe` before the first call of a session; read `backends/<selected>.md` before the first call with that backend.

CITE_BACKEND skills/jev-fast-decision/SKILL.md:12
> From this skill's directory, run `python3 -B scripts/jev_review.py --probe` before the first call of a session; read `backends/<selected>.md` before the first call with that backend.

VERDICT fail
DIGEST b3a28ffca7b8ff2b
TREE a4daa7035c4a8c812035d6d4f5eb34db73885bcf

# Skill evaluation: `jev-fast-decision`

Read the complete rubric, all eight bundled skill files, and the linked local evaluation results. This is a read-only, static assessment: no scripts were executed, external URLs were not fetched, and committed-tree status was not independently verified.

## Part 1 — Dimensions

D1 18/20 — 90%
D2 14/15 — 93.3%
D3 14/15 — 93.3%
D4 15/15 — 100%
D5 13/15 — 86.7%
D6 13/15 — 86.7%
D7 9/10 — 90%
D8 11/15 — 73.3% — Below floor: make error handling and fallback paths work as documented, keep HTTP-error body reads within the total deadline, and reconcile status/attempt guidance with actual client output.

**Assessment:** An expert-heavy Navigation/Tool hybrid with effective activation metadata, concrete consent safeguards, measured batching pitfalls, and explicit advisory-only interpretation. The main weakness is practical reliability: two client error paths contradict the documented operating contract.

### Critical findings

None. The required `needs_fallback` recipe exists.

### Important findings

1. **HTTP-error body reads escape the total deadline.**  
   **Files:** `skills/jev-fast-decision/scripts/jev_review.py:226`, `:1319–1323`, `:1436`; documented promise at `skills/jev-fast-decision/reference.md:71`.  
   When `opener.open()` raises an HTTP error, `_exchange()` cancels its watchdog before classification. The classifier subsequently calls `_error_body()`, which invokes `_read_body()` without a deadline. A slowly trickling error response can therefore outlast the advertised whole-run bound. Keep error-body processing inside the deadline/watchdog scope and cover a trickling non-200 response with a regression test.

2. **TypeSafe 402 does not escalate as documented.**  
   **Files:** `skills/jev-fast-decision/backends/typesafe.md:39`; implementation at `skills/jev-fast-decision/scripts/jev_review.py:727–728`, `:1437–1451`, `:1738–1739`.  
   TypeSafe classifies 402 as `next_model`, but its row has only one model. When no next model exists, `_post()` returns the unchanged `next_model` action; `_fold_rung()` treats every action other than `escalate` as final. Thus an auto-mode item stops instead of reaching an otherwise usable, consented OpenCode rung. Implement the documented exhausted-model escalation while preserving OpenCode’s separately documented paid-budget stop.

### Minor findings

1. **OpenCode attempt provenance is incomplete or mislabeled.**  
   **Files:** `skills/jev-fast-decision/backends/opencode.md:29–30`; `skills/jev-fast-decision/scripts/jev_review.py:1437–1442`, `:1498–1502`, `:1534`.  
   The notes promise an `attempts` entry for the free-model failure. A successful free-to-paid transition records none; a terminal paid failure is labeled using `_request_model(row)`’s default first model. Record each failed attempt with the actual attempted model.

2. **The reference gives the wrong explicit-remote consent reason.**  
   **File:** `skills/jev-fast-decision/reference.md:48`.  
   It lists `backend_unavailable:<name>:consent_required_for_remote`, whereas the client emits `backend_unavailable:<name>:consent_required`. The body’s recipe at `skills/jev-fast-decision/SKILL.md:39` is correct; align the reference.

3. **Progressive disclosure omits the `noul` request shape.**  
   **File:** `skills/jev-fast-decision/SKILL.md:66`.  
   Mandatory reference loading covers `choice`, `score`, and receipts, but not `noul`; the body contains no `noul` example. Its wrapper schema lives at `skills/jev-fast-decision/reference.md:17`. Include `noul` in the loading trigger or provide a minimal example.

4. **“Other 4xx” descriptions overstate the implemented caller-error classification.**  
   **Files:** `skills/jev-fast-decision/backends/typesafe.md:40`, `skills/jev-fast-decision/backends/opencode.md:25`.  
   The code uses narrower caller-error sets: TypeSafe 429 and OpenCode 404, for example, escalate rather than becoming the documented final caller errors (`scripts/jev_review.py:729–731`, `:792–794`). Document the actual sets or reconcile implementation and tests.

### Required fallback recipe

**Confirmed — `skills/jev-fast-decision/SKILL.md:38`:**

> `needs_fallback: true` → **you decide that item with your own reasoning**

The same line explicitly requires independent decisions for errors and missing IDs.

## Part 2 — Activation

These picks were made before opening any skill body, using only the `name` and `description` fields of all 22 listed skills. The fixture was located at `.planning/phases/21.1-atomic-reusable-decision-system-skills/skill-judge/activation.jsonl`.

| Line | Single selection | Frontmatter-only reasoning |
|---|---|---|
| 1 | `jev-fast-decision` | Per-finding yes/no screening over supplied evidence. |
| 2 | `jev-fast-decision` | One selection among named options matches `choice`. |
| 3 | `jev-fast-decision` | Bounded rubric judgment matches `score`. |
| 4 | `jev-fast-decision` | Per-hit false-positive screening matches typed judgment. |
| 5 | none | Editing code and tests is explicitly excluded; no other description matches. |
| 6 | none | Call-chain investigation is not supplied-evidence screening. |
| 7 | none | Running checks and implementing fixes is not advisory judgment. |
| 8 | none | Planning and implementing a migration is outside scope. |
| 9 | none | In-app TypeSafe integration is excluded; no `typesafe-ai` frontmatter is present. |
| 10 | none | Product-feature brainstorming is not typed screening; no `typesafe-ai` frontmatter is present. |
| 11 | none | Application-level integration is excluded; no `typesafe-ai` frontmatter is present. |
| 12 | none | Building an in-app ranker and backend integration is excluded; no `typesafe-ai` frontmatter is present. |

All four expected positive cases select `jev-fast-decision`; none of the eight negative cases selects it. This satisfies the specified activation pass rule.

CURRENT 107/120  
CRITICAL 0  
IMPORTANT 2  
FLOORS fail  
ACTIVATION ok  
CITE_PROBE skills/jev-fast-decision/SKILL.md:12
> From this skill's directory, run `python3 -B scripts/jev_review.py --probe` before the first call of a session; read `backends/<selected>.md` before the first call with that backend.

CITE_BACKEND skills/jev-fast-decision/SKILL.md:12
> From this skill's directory, run `python3 -B scripts/jev_review.py --probe` before the first call of a session; read `backends/<selected>.md` before the first call with that backend.

VERDICT fail

