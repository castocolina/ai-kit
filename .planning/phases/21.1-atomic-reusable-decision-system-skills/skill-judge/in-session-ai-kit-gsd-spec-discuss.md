# In-session skill-judge: ai-kit-gsd-spec-discuss

Judge: native skill-judge (Claude Opus 5.5, a fresh in-session subagent run by the orchestrator, read-only).

## Run 1

DIGEST 84b0f6debfcdd5ce
TREE ea89cf6dbc95baacfa89cf01b2f40cac68b0972a

The skill passes. Under the judge prompt's rule for ai-kit-gsd-spec-discuss, it scores 106/120 with no dimension under its floor. Three Important findings remain, all in set-up steps 2, 3 and 5, and each makes the skill say something the shared client does not do. I worked read-only and made no AI CLI probes; every claim below was checked against the scripts in the worktree.

# Skill Evaluation: ai-kit-gsd-spec-discuss

- **Pattern:** Process. SKILL.md has 209 lines and four references (52, 73, 111 and 62 lines) and three scripts.
- **Knowledge ratio (E:A:R):** about 80:17:3.

## needs_fallback special check: present, not Critical

The recipe is at `skills/ai-kit-gsd-spec-discuss/SKILL.md:136`: "Every answering column low or errored → **own reasoning** against the SPEC, earlier CONTEXT files and the live facts." It works together with SKILL.md:125-127, where `decided_by` falls back to `own_reasoning` and `fallback` follows each backend's threshold.

`decide.py:321` renames the client's `needs_fallback` to `fallback`, so a ladder answer never carries `needs_fallback: true` literally. The recipe's word "low" is tied to `fallback: true` only in `references/decision-table.md:3`, which is logged as a Minor finding below.

## PART 1 — Dimensions

D1 17/20 (85%). Live-learned facts, for example that `--assumptions` routes to a workflow that writes no files (SKILL.md:81-83, 175-178) and that the Edge Coverage floor must come from the engine (SKILL.md:70-76). It loses points because step 3's key sources and step 5's consent trigger are stale. The skill's own rule at SKILL.md:66-67 calls a sentence written from memory a defect.

D2 14/15 (93%). "You are the decider" (SKILL.md:12-16) is a real mindset. The procedures are ones a model would not know: the pre-answered workflow prompts at SKILL.md:87-91, and the instruction to filter "SPEC newer" false positives with `git log` at SKILL.md:43-46.

D3 13/15 (87%). The NEVER list (SKILL.md:173-190) gives a non-obvious reason for every item. Two items are now partly stale: "NEVER batch items to Laya" (SKILL.md:179) is enforced by the client, and SKILL.md:180 does not name the OpenCode Zen backend.

D4 14/15 (93%). The description (SKILL.md:3, about 850 characters, under 1024) covers what it does, when to use it, trigger phrases and exclusions. It is dense, and its first clause reads like an implementation summary.

D5 14/15 (93%). The MANDATORY triggers sit inside the workflow (SKILL.md:58, 98, 102-103), there is a trigger list (SKILL.md:199-206), and SKILL.md:208-209 says when not to load the references.

D6 13/15 (87%). Freedom is low where the work is fragile: the flags, the Edge Coverage engine and fail-closed exit 2 (SKILL.md:70-76). It is medium for judgment calls (decision-table.md). However, the fragile step 5 depends on a literal string that never matches.

D7 9/10 (90%). A clean Process pattern: sections 0 to 7, checkpoints, NEVER, host gaps, references.

D8 12/15 (80%). Error handling is strong: `invalid_input`, `duplicate_id`, `reserved_id`, `incompatible_client` and fail-closed exit 2. The common case has a gap: with Laya up and TypeSafe keyed but not consented, step 5's consent question never fires (Important finding 1). `no_client` is also not handled in step 3.

## Findings

**Critical:** none.

**Important**

1. **Step 5's consent trigger can never match** (`SKILL.md:48`). The step says to ask "if a remote backend's `detect` entry reads `consent_required_for_remote`".
   - An unconsented remote's probe row actually reads `consent_required` (`jev_review.py:1117-1118`, test at `tests/test_jev_fast_decision.py:993`). `decide.py:219` copies that into the entry's `status`.
   - `consent_required_for_remote` only ever appears as the top-level probe status, and only when no candidate is usable at all (`jev_review.py:1166-1175, 1227-1232`).
   - Result: in the usual case (Laya up, a remote keyed but not consented), the consent question is never asked and the remote rungs are silently skipped.
   - Fix: trigger on an entry with `remote: true`, `status: consent_required` and a non-null `key_source`.

2. **Step 3 lists TypeSafe key sources the client does not read** (`SKILL.md:35-36`). The step names `TYPESAFE_API_KEY`, `JEV_API_KEY`, `JEV_API_KEY_FILE` and `JEV_API_KEY=` in `ai-kit/secrets.env`.
   - The shared client reads only `TYPESAFE_API_KEY`, then `$XDG_STATE_HOME/typesafe/api_key` (`jev_review.py:686-693`). It never reads `JEV_API_KEY` or `secrets.env`.
   - These are leftovers from before plan 21.1-03, carried into the rewritten step.
   - Result: a user keyed through `secrets.env` shows up as having no TypeSafe key, and the skill points them at the wrong file.

3. **Step 2's Claude Code path assumes a global GSD install** (`SKILL.md:27-28`). It says "in Claude Code: `node ~/.claude/gsd-core/bin/gsd-tools.cjs`".
   - The resolver it cites checks the repo's own `.claude/gsd-core/bin/gsd-tools.cjs` first (`.claude/gsd-core/references/gsd-run-resolver.md:7`). This machine is project-local only.
   - Result: an agent that takes the shortcut gets "not found".
   - This line was not changed by plan 21.1-03.

**Minor**

1. SKILL.md:85 versus SKILL.md:179: "all the phase's questions in one ladder run" next to "NEVER batch items to Laya" reads as a contradiction. The client already sends Laya one item per call (SKILL.md:127). Reword it as a property of the client, not an action for the agent.
2. SKILL.md:136 versus `references/decision-table.md:3`: the body never says that "low" means `fallback: true`. `references/log-formats.md:20, 84` call it `needs_fallback`, so the agent meets three names for one flag.
3. SKILL.md:37-39 handles `incompatible_client` but not `no_client` (`decide.py:416-418`). The fact that a missing client means own reasoning only is implied by the description, not stated.
4. SKILL.md:31-36 lists no key source for the OpenCode Zen backend (`OPENCODE_ZEN_API_KEY` or a key file, `jev_review.py:745-751`).
5. Two examples log "Laya overridden" from a TypeSafe second opinion of 0.74: `references/log-formats.md:26` and `references/worked-examples.md:21-25`. TypeSafe's threshold is now 0.8 (`jev_review.py:835`), so 0.74 is `fallback` and should show `(fb)`. `references/decision-table.md:22-26` says to override only on a remote answer above threshold. The cell format at log-formats.md:8-10 also does not say how to combine `(fb)` with `(second opinion)`.
6. SKILL.md:180 says "a Laya or TypeSafe answer" but does not mention OpenCode Zen, now a table backend.

## Top 3 improvements

1. Change step 5's trigger to the per-entry `status: consent_required` with `key_source` set (Important 1).
2. Make step 3's key sources match `_typesafe_key` and `_opencode_key`, or just point to `decide.py detect`'s `key_source` labels (Important 2).
3. Replace the hardcoded `~/.claude/gsd-core` hint with "use the resolver; it finds the repo-local install first" (Important 3).

CURRENT 106/120
CRITICAL 0
IMPORTANT 3
FLOORS ok
VERDICT pass

The verdict rule for this skill counts only the score and the floors. The repo's skill-judge loop also accepts a score of 96 or more without regression, so the three Important findings don't block it, but all three are factual mismatches with the client and cheap to fix. I didn't run the scripts or the tests, and I didn't check `gsd-assumptions-analyzer`, the workflow files or edge-probe.cjs beyond what the skill quotes.

## Run 2 (after fix round 1: 9211018)

DIGEST baefb8959dee86da
TREE 73d2713b3b64ae3be2c0084b4be32adb38efb25b

I judged `skills/ai-kit-gsd-spec-discuss/` read-only against the installed rubric: it scores **106/120 and passes**, with one Important finding and no Critical one. That Important finding is a gap in `decide.py`'s input checks that I reproduced. To verify the claims about the client I ran `decide.item_error` and the client's `request_body` in-process: both are pure functions, so nothing touched the network.

# Skill Evaluation Report: ai-kit-gsd-spec-discuss

- **Pattern:** Process (213-line `SKILL.md`, four references, three scripts).
- **Knowledge ratio:** roughly 80% expert, 15% activation, 5% redundant.

## Claims checked against the code (correct unless listed under Findings)

- **Detect output:** `decide.py detect` returns one entry per table backend (`laya`, `typesafe`, `opencode`) and shows labels only, never key values (decide.py:45, 208-221).
- **Detect statuses:** per-backend `consent_required`, keyed by `key_source` `env` or `file`; top-level `consent_required_for_remote` only when no backend is usable. Matches jev_review.py:1117-1118 and 1159-1176.
- **Laya URL:** read from `JEV_LAYA_URL`, `AI_KIT_LAYA_URL`, or a loopback `JEV_API_URL`, with the stated default, probed via `/health` (jev_review.py:50, 561-578, 609-626).
- **Key sources:** TypeSafe and Zen key sources match (jev_review.py:688-695, 744-759).
- **Thresholds:** each backend has its own (0.7, 0.8, 0.75 at jev_review.py:807, 835, 858). `JEV_MIN_CONFIDENCE` is scrubbed from the child environment (decide.py:34, 257-259).
- **Ladder:** Laya gets one item per call (`batch: False`, jev_review.py:805). `--second-opinion` maps to the client's `--skip-local`, which skips Laya entirely (decide.py:389; jev_review.py:1154-1155).
- **Columns:** each column is `{choice, top, fallback, model}`, `{error}` or null. `decided_by` is the last confident rung, else `own_reasoning` (decide.py:311-367).
- **Validation:** `duplicate_id`, `reserved_id`, code fences and secret shapes are rejected (decide.py:115-199).
- **Version check:** `CLIENT_PROTOCOL = 2` is read as text, never imported (decide.py:31, 95-110; jev_review.py:44).
- **Consent:** `consent grant <backend>` goes through to the client's record (decide.py:429-438; jev_review.py:1066-1089).
- **Install hint:** `setup.py install --headless --skills … --replace-existing` exists (tools/setup.py:3434-3458).
- **gsd-core:** the files the skill names exist (`gsd-run-resolver.md`, `spec-phase.md`, `discuss-phase-assumptions.md`, `edge-probe.cjs`). `phase.mvp-mode` is registered (command-aliases.cjs:821). `workflow.mvp_mode` has no schema default, so the "Key not found" claim holds (config.cjs:82-112).
- **Scripts:** `edge_floor.py` exits 1 on drift and 2 when it fails closed; `phase_range.py --roadmap/--from/--to/--list` exist.
- **Special check (`needs_fallback` recipe):** present. SKILL.md:140 reads "Every answering column low (`fallback: true`) or errored → **own reasoning** …". `decide.py` renames the client's `needs_fallback` to `fallback` (decide.py:321), so this line is the recipe for the field the agent actually sees.

## PART 1 — Dimensions

D1 17/20 (85%). Expert content that's hard to get elsewhere: the `--assumptions`/`--auto` routing traps, the false positive where a later amendment makes a SPEC look newer, Laya's nondeterminism, the edge-floor engine requirement, and the loss of locked decisions if a CONTEXT is regenerated. Small deductions: SKILL.md:34-38 restates key paths the client already owns and `detect` already reports.

D2 13/15 (87%). Clear decider mindset (SKILL.md:12-16), a blocking × confidence frame, and GSD procedures an agent wouldn't otherwise know (set-up steps 1-6, §1-§2).

D3 14/15 (93%). The NEVER list (SKILL.md:177-194) is specific and each entry gives its reason: a listing workflow that writes nothing, a flipped `discuss_mode` left behind after a crash, drift from a hand-written floor.

D4 14/15 (93%). Frontmatter is valid. The description (862 chars) covers WHAT, WHEN, quoted trigger phrases and what it is not for. It is slightly implementation-heavy.

D5 14/15 (93%). MANDATORY read triggers sit inside the workflow (SKILL.md:62, 102, 106-107), plus a trigger list and a "Do NOT load" rule (SKILL.md:203-213).

D6 13/15 (87%). Freedom is low where it should be (the edge floor, command flags, the commit shape) and medium for decisions. One deduction: the item-shape contract is under-specified for a fragile step (Important finding below).

D7 9/10 (90%). A clean Process pattern: per-phase stages, checkpoints, references loaded on demand.

D8 12/15 (80%). The decision table, fallbacks, host gaps and worked examples cover the common cases. Deductions are for the Important finding and several inaccurate statements about the client (Minor findings).

CURRENT 106/120 (88%, grade B)

## Findings

**Critical:** none.

**Important (1)**

1. **A choice or score item without `criteria` sinks the whole batch, and the agent can't tell why.**
   - **Where:** skills/ai-kit-gsd-spec-discuss/SKILL.md:119-125, with the root cause at skills/ai-kit-gsd-spec-discuss/scripts/decide.py:134-135.
   - **What happens:**
     - `_criteria_error` returns `None` whenever the `criteria` key is absent, whatever the item type.
     - The client requires `criteria` for `choice` and `score` (jev_review.py:327-329), and on a bad item it rejects the entire request (jev_review.py:1849-1852, 1680-1684).
     - I reproduced it: `{"type":"choice"}` and `{"type":"score"}` without criteria give `decide: None` but `client: invalid_input:<id>`.
     - `decide.py` then keeps only the bare status (decide.py:303-306, 397), so it reports `client_status: "unavailable"` and marks every item `own_reasoning`.
     - The client's `item` field, which names the bad id, is dropped. The agent sees what looks like a backend outage.
   - **What it contradicts:** SKILL.md:123-124 ("rejected alone … fix and resubmit") and decide.py's own docstring (decide.py:130-132, the T-21.1-29 parity claim).
   - **Made worse by:** SKILL.md:120-121, whose shape example shows a one-option choice. `decide.py` rejects that as `choice_needs_two_criteria`.
   - **Fix:** in `decide.py`, reject a missing `criteria` for `choice`/`score` with a reason such as `missing_criteria`, and add a test. In SKILL.md:122, state that a choice item needs two or more criteria and a score item its 2-10 levels.

**Minor (7)**

1. **SKILL.md:128-131:** "plus `decided_by` … and `top`, the winning probability" suggests a `top` field on the item. It doesn't exist; `top` is only inside each column (decide.py:349-367).
2. **SKILL.md:56-57:** "Announce from the output's `consent_used`". Only the ladder output carries `consent_used` (decide.py:393, 403-405). At set-up, the grant date comes from `detect`'s `backends.<name>.consent` (jev_review.py:1188-1189, decide.py:45).
3. **SKILL.md:53:** "the revoke command" is never spelled out. It is `python3 "$S/decide.py" consent revoke <backend>`. The client's grant note names `jev_review.py consent revoke …` (jev_review.py:1087-1088), a path the agent never resolved.
4. **decision-table.md:30-32 has two inaccuracies.**
   - "a usable remote is not consented": an unconsented remote is never usable, since its probe returns `consent_required` (jev_review.py:1117-1118). Also, `remote_available` only appears when the client returned a trail (decide.py:390-394). With no usable rung, it is dropped and `client_status` becomes `consent_required_for_remote`.
   - "no compatible client and `client_status` is set": with no client found, `client_status` is absent (decide.py:385, 399, 406). It is also set for `unavailable` and `disabled`.
   - Either way the outcome is still `own_reasoning`.
5. **decision-table.md:35:** the example error `budget_exceeded` is never emitted. When Zen runs out of models, the column shows `http_402` or `http_429` (jev_review.py:788-789, 1436-1453).
6. **decision-table.md:26 ("each low") and log-formats.md:20, 84 ("batched to the consented remotes"):**
   - A low remote answer is final; the next remote is only tried after an escalate-class error (jev_review.py:1732-1733).
   - OpenCode Zen is `batch: False`, one call per item (jev_review.py:857).
   - decide.py:6 repeats the "one consented remote batch" wording.
7. **SKILL.md:140 vs log-formats.md:20, 84:** the body says `fallback` while the references say the client's `needs_fallback`. A single bridging phrase ("`fallback` = the client's `needs_fallback`") would join them.

CRITICAL 0
IMPORTANT 1
FLOORS ok

VERDICT pass

Not checked: I ran no live calls to the backends, edge-probe or gsd-tools, and did not try the analyzer-spawn path. The Important finding is the one risk worth fixing: a malformed choice or score item quietly turns a whole ladder run into own reasoning, and nothing in the output says why.

## Run 3 (after fix round 2: 39d61eb; final, fix cap 2 of 2 used)

DIGEST 31a3d173dad8380c
TREE 565393265285688d4ff788cca4db1d213615ac43

# Skill Evaluation Report: ai-kit-gsd-spec-discuss

**Summary.** The skill scores 110/120 (grade A) and passes: no dimension is under its floor and there are no Critical findings. It follows the Process pattern: SKILL.md is 214 lines plus 4 references and 3 scripts. I estimate the content mix at about 80% expert, 15% activation and 5% redundant.

I checked every claim the skill makes about the shared client (`skills/jev-fast-decision/scripts/jev_review.py`) and about `decide.py` against the code. I also ran an offline `partition`/`decided_by`/`typed_answer` check with no network. All the main claims hold:
- **Laya URL:** `JEV_LAYA_URL`, `AI_KIT_LAYA_URL` or a loopback `JEV_API_URL`, default 8010, probed via `/health`.
- **Keys:** the TypeSafe and Zen key sources are as stated.
- **Thresholds:** each backend has its own (laya 0.7, typesafe 0.8, opencode 0.75), and `JEV_MIN_CONFIDENCE` is scrubbed from the child.
- **Laya calls:** Laya is non-batch, one item per call.
- **Second opinion:** `--skip-local` makes the client skip the local rung.
- **`decided_by`:** it is the last confident rung, else `own_reasoning`.
- **Probe statuses:** the `consent_required` row status and the top-level `consent_required_for_remote` behave as described.
- **Item rejection:** `duplicate_id`, `reserved_id`, the `#<index>` keys, `missing_criteria`, `bad_criteria` and code fences are rejected as described.
- **Helper scripts:** the `edge_floor.py` exit codes 0/1/2 and the `phase_range.py` reasons and git-time logic match.
- **gsd-core paths:** the resolver doc, the workflows, `--assumptions` routing to `list-phase-assumptions.md`, and `init phase-op`'s agent fields all exist in the project-local `.claude/gsd-core`.

**Special check:** the `needs_fallback` recipe is present at `skills/ai-kit-gsd-spec-discuss/SKILL.md:141-142`: "Every answering column low (`fallback: true`, the client's `needs_fallback`) or errored → **own reasoning** against the SPEC, earlier CONTEXT files and the live facts."

## PART 1 — Dimensions

D1 18/20
90%. Dense expert content: the false-positive "SPEC newer" check, the measured non-determinism of Laya, Edge Coverage as engine output, `config-get` "Key not found", and the cited override cases. Setup steps 3 and 5 are compressed to the point of being hard to parse.

D2 14/15
93%. A strong decider mindset (SKILL.md:12-16) plus GSD-specific procedures (pre-answered prompts, the analyzer spawn, the commit and state sequence).

D3 14/15
93%. Every NEVER item has a non-obvious reason, for example: `--assumptions` writes nothing, `--auto` chains into plan-phase, a `discuss_mode` flip survives a crash, and a hand-written floor drifts. "NEVER print a key" is the only generic one.

D4 14/15
93%. Valid name. The description covers what the skill does, when to use it, trigger phrases and its exclusions. It is long and carries mechanism detail (best-over-easy, `mvp_mode`) that does nothing for triggering.

D5 14/15
93%. MANDATORY load triggers sit inside the workflow steps (SKILL.md:62, 102, 106), each reference has its own trigger, and there is a "Do NOT load" rule (SKILL.md:213).

D6 14/15
93%. Freedom is low where mistakes are costly (exact flags, the engine-only floor, fail closed on exit 2) and high where judgment is needed (evidence decides, the quality rule).

D7 9/10
90%. A clean Process pattern of about 200 lines, with phased steps, checkpoints and references.

D8 13/15
87%. Covers the common paths, errors and fallbacks (`no_client`, `incompatible_client`, exit 2, no subagent support). There is one gap in the decision tree for a realistic case, plus a few inaccuracies in field and code names (see Findings).

## Findings

**Critical:** none.

**Important (1)**
- **No decision-table row for "Laya unreachable, a remote decided"** (`skills/ai-kit-gsd-spec-discuss/references/decision-table.md:27-29`).
  - Row 4 says "The local rung is low or errored and `decided_by` is a remote backend". But when Laya fails its `/health` probe, it never gets a rung in the trail, so `fill_columns` leaves its column `null` (decide.py:360-368).
  - Null is neither low nor errored. So when Laya is down, the most common case, a literal "first matching row decides" walk matches no row.
  - Fix: change row 4 to "low, errored or not called (null)".

**Minor**
1. **`budget_exceeded` is not a real error code** (`references/decision-table.md:35`). The client never produces it; Zen failures come back as `http_402`/`http_429`, `http_5xx`, `unauthorized` or `network_error` (jev_review.py:777-792). Replace the example with `http_429`.
2. **`client_status` is described too narrowly** (`references/decision-table.md:31-32`).
   - It is not only "no compatible client". decide.py:399 also sets it to whatever status the client returns without a trail, for example `consent_required_for_remote` or `unavailable`.
   - With no client found at all, `client_status` is never set; only `client.found: false` is.
   - In the no-trail case `remote_available` is dropped (decide.py:392-399). Routing is still correct, because `decided_by` is `own_reasoning` either way.
3. **The skill says to announce from `consent_used`, but `detect` does not output it** (`SKILL.md:56-57`). Only `ladder` output has it. `detect` rows carry `consent: <date>` and a grant returns `consent`. Name which output to read.
4. **"Remotes in table order" overstates what happens** (`SKILL.md:136-137`, `references/log-formats.md:19-20`, `references/log-formats.md:84-85`).
   - A low remote answer is final (jev_review.py:1732, `_fold_rung`), so OpenCode Zen only sees items that TypeSafe errored on.
   - OpenCode Zen is non-batch, so "batched to the consented remotes" is not accurate for it either.
5. **`noul` answers read differently from their criteria** (`SKILL.md:130-131`). A `noul` column's `choice` is `yes`/`no` (decide.py:329), not the item's `true`/`false` criteria keys. This is not documented for the log cells.
6. **A fix command that only works in this repo** (`SKILL.md:40-41`). The `tools/setup.py install ...` remediation only works from an ai-kit checkout, which is not portable for a skill run in other repos.
7. **The scripts-dir loop ignores config-dir variables that decide.py honors** (`SKILL.md:22-23`). The loop does not check `CLAUDE_CONFIG_DIR`, `CURSOR_CONFIG_DIR` or `PI_CODING_AGENT_DIR`, while decide.py:72-79 does. The first candidate (the skill's own directory) covers the usual case.

## Sections changed by plan 21.1-03
- **Steps 3 and 5:** accurate against the client, but dense. Step 5's parenthetical about `consent_required_for_remote` is hard to parse.
- **§3:** accurate on item shapes and the column mapping.
- **Both references:** they now defer correctly to the client's table order and per-row thresholds. The remaining defects are Important #1 and Minors 1, 2 and 4.

D1 18/20
D2 14/15
D3 14/15
D4 14/15
D5 14/15
D6 14/15
D7 9/10
D8 13/15
CURRENT 110/120
CRITICAL 0
IMPORTANT 1
FLOORS ok
VERDICT pass

Open after the 2-round fix cap (owner review / 21.1 code review): Important — references/decision-table.md row 4 does not cover a null (never-called) Laya column, so with Laya down no row matches; Minors as listed.

## Run 4 (final-tree check after 5af9c01 and a907c41; fresh opus subagent)

An earlier final-tree check (digest 48b97a10614ffc30) scored 110/120, 0 Critical, 1 Important,
pass; the Important (the references said remotes were batched in turn, but a low remote answer
is final) was fixed in a907c41 with the run-3 row-4 item.

DIGEST a9c177e20f6d444f
TREE cb974e6cc8b1e27c11e5832629836f3c2bb09064

The run-3 open Important (decision-table row 4 and a not-called Laya column) and the run-4
Important (a low remote answer is final) are no longer reported. `needs_fallback` recipe present
at SKILL.md:142-143.

Findings verified by the orchestrator and fixed in 3701297:
- Important 1: the client forces `needs_fallback` when one request's state exceeds the row's
  `state_chars_limit` (Laya 2,000, TypeSafe and Zen 8,000); the skill read every `(fb)` as low
  confidence. §3 and `log-formats.md` now name the size flag.
- Minor 2: `consent_used` lists every remote with consent on file; announce only a called one.
Minors left for the owner: row-5 `client_status` wording, the 18.1 T2 example, escalate-class
errors also reaching the remote, which workflow commit/state steps the chain replaces, the
resolver path, the setup.py working directory, decide.py's docstring, `remote_available` dropped
with no trail.

D1 17/20
D2 13/15
D3 14/15
D4 14/15
D5 14/15
D6 13/15
D7 9/10
D8 12/15
CURRENT 106/120
CRITICAL 0
IMPORTANT 1
FLOORS ok
VERDICT pass
