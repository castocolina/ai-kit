# In-session skill-judge: jev-fast-decision

Judge: native skill-judge (Claude Opus 5.5, a fresh in-session subagent run by the orchestrator, read-only).

## Run 1

DIGEST 9751612c69f865e4
TREE e06c4151656991569018407b29bd3a2d092b3eec

# Skill evaluation: jev-fast-decision

The skill passes. It scores 104/120, no dimension is under its floor, the `needs_fallback` recipe is there, all 12 activation picks hold, and both cite lines exist. Two Important findings remain: a wrong consent host in the TypeSafe backend note, and a description with no "not for" boundary.

## PART 2 — Activation picks (made before opening any skill body)

I made these picks from the frontmatter `name`/`description` of each `skills/*/SKILL.md` file only. `typesafe-ai` has no `SKILL.md` under `skills/`, so lines that expect it get "none" from this list. The pass rule only needs them not to pick jev-fast-decision.

1. **jev-fast-decision**: a yes/no triage per finding, with the evidence supplied and no edits. This matches "yes/no (noul)… screening evidence against a criterion".
2. **jev-fast-decision**: picks among named options, which is "choice".
3. **jev-fast-decision**: a rubric score from 0 to 3 on supplied text, which is "score".
4. **jev-fast-decision**: a yes/no screen of grep hits that are already in hand.
5. **none**: it edits a script and its tests. That is code work, not a typed judgment.
6. **none**: a multi-step trace of a call chain needs full reasoning.
7. **none**: it runs commands and fixes failures.
8. **none**: a multi-step plan plus code changes.
9. **none** (typesafe-ai intent): it builds a product feature that calls Jev for end users. That is not the agent's own advisory judgment.
10. **none** (typesafe-ai intent): product brainstorming about System One as a primitive.
11. **none** (typesafe-ai intent): application code calls a typed judgment. This is integration work.
12. **none** (typesafe-ai intent): an in-app ranker plus a backend API call is product integration. It is the riskiest line, because "Jev" and the severity scoring overlap the description's keywords.

## PART 1 — Dimensions

- Structure: `SKILL.md` is 68 lines, and the body is 488 words.
- Pattern: Tool.
- Knowledge ratio, roughly: Expert 75, Activation 15, Redundant 10.

**D1 18/20 (90%).** The knowledge is dense and new to the model: the consent rules, the measured Laya state-bleed (0.46 → 0.86), `top` versus uncalibrated `confidence`, the 2000-character guard, and how the free/paid tiers fall through. It loses points for the three repeated consent/batching sections and the unconditional external links.

**D2 13/15 (87%).** The procedures are domain-specific: probe first, read the backend note, then grant consent. The thinking frame is present: advisory not verdict, value-free question text, investigate a confident `unsupported`. Missing is a short "before asking Jev, check that the question is self-contained and typed" frame in `SKILL.md`. It only exists in `reference.md:20`.

**D3 13/15 (87%).** The NEVER list is specific and gives reasons. The Red Flags quote real baseline rationalizations verbatim. The same points appear across NEVER, Red Flags and Common Mistakes, which wastes tokens.

**D4 13/15 (87%).** The frontmatter is valid and covers what the skill does, when to use it, and keywords (noul/choice/score, Laya, TypeSafe, OpenCode Zen). There is no negative boundary against product integration or code/command tasks.

**D5 12/15 (80%).** The load triggers sit inside the workflow:
- `backends/<selected>.md` before the first call with that backend.
- `reference.md` for "any other status" and before interpreting `score` or a receipt.

There is no "Do NOT load" guidance. The "Required reading" external links have no trigger condition.

**D6 14/15 (93%).** Freedom is low where it should be (consent, off-machine sends, Laya batching) and medium for interpreting answers. The example pins an explicit backend, which pulls against the auto-ladder default.

**D7 9/10 (90%).** A compact Tool pattern: decision table, call example, result recipe, status table in the reference.

**D8 12/15 (80%).** There is a status table, error tables for each backend, and the `needs_fallback` recipe. But the call example fails validation if copied as written. The script path is only resolved relative to the skill root in `reference.md`. `--skip-local` is undocumented.

**Special check:** the `needs_fallback` recipe is present at `skills/jev-fast-decision/SKILL.md:38`: "`needs_fallback: true` → **you decide that item with your own reasoning**".

### Findings

**Critical:** none.

**Important (2):**
1. `skills/jev-fast-decision/backends/typesafe.md:44` reads "Questions go to `api.typesafe.ai`". The actual endpoint is `api.typesafe.dev` (`typesafe.md:9`, `scripts/jev_review.py:684`). The grant note prints the endpoint's own hostname (`jev_review.py:1087`). The doc's consent and retention text names the wrong host, which matters in a privacy-critical file.
2. `skills/jev-fast-decision/SKILL.md:3`: the description has no "not for" clause. It does not exclude product or application integration of TypeSafe/Jev (the typesafe-ai lane) or tasks that edit code or run commands. Because both "TypeSafe" and Jev-style scoring appear in it, activation lines 9 to 12 depend on inference.

**Minor:**
1. `SKILL.md:27`: `"reviewed_head": "0*40hex"` fails the `[0-9a-f]{40}` fullmatch (`jev_review.py:344`) if copied literally, giving `invalid_input`. Nothing says what to pass when no revision is being reviewed.
2. `SKILL.md:12` and `SKILL.md:26`: `scripts/jev_review.py` reads as relative to the current directory. Resolving it from the skill root is only stated in `reference.md:3`. The full `consent grant` command line (`SKILL.md:20`) is not shown.
3. `SKILL.md:25`: the example pins `JEV_BACKEND=laya`, which never falls back, plus a placeholder port. The default `127.0.0.1:8010` (`backends/laya.md:9`) makes the override unnecessary, and it models skipping the auto ladder.
4. `SKILL.md:61-66`: "Required reading" lists 4 external URLs with no condition, so it reads as a mandatory fetch on every use.
5. `SKILL.md:43-59`: NEVER, Red Flags and Common Mistakes repeat the consent and Laya-batching points three times.
6. `jev_review.py:1905`: the `--skip-local` flag is not documented in `SKILL.md` or `reference.md`.

**End lines:**

```
D1 18/20
D2 13/15
D3 13/15
D4 13/15
D5 12/15
D6 14/15
D7 9/10
D8 12/15
CURRENT 104/120
CRITICAL 0
IMPORTANT 2
FLOORS ok
ACTIVATION ok
CITE_PROBE skills/jev-fast-decision/SKILL.md:12 — "Run `python3 -B scripts/jev_review.py --probe` before the first call of a session; read `backends/<selected>.md` before the first call with that backend."
CITE_BACKEND skills/jev-fast-decision/SKILL.md:12 — "Run `python3 -B scripts/jev_review.py --probe` before the first call of a session; read `backends/<selected>.md` before the first call with that backend."
VERDICT pass
```

Both cite lines point to the same line, because line 12 carries both instructions. D5 and D8 sit exactly on their floors (12/15), so the next small edit to those areas could tip them under.

I did not read all of `scripts/jev_review.py`. It is 85 KB, so I only checked the lines behind specific claims, and I did not open `scripts/eval_cases.py` or `evals/cases.jsonl`. No files were modified.

## Run 2 (after fix round 1: 6da2270, 9211018)

DIGEST bd79203f9d0b47cc
TREE ea330a0a25a1130f20a3fed2aeedfe21917504fc

Activation picks (made before I opened any skill body)

Pool: the `name`/`description` frontmatter of all 22 `skills/*/SKILL.md`. There is no `typesafe-ai` under `skills/`. Its only presence in the pool is the jev-fast-decision description's exclusion "Not for building TypeSafe into an app (typesafe-ai)".

1. Triage findings F1/F2 yes/no, evidence inline, no edits: **jev-fast-decision**. It is a yes/no (noul) screen of evidence against a criterion.
2. Pick one of three named titles: **jev-fast-decision**. It is a choice among named options.
3. Score a bug report from 0 to 3, text inline: **jev-fast-decision**. It is a rubric score.
4. Grep hits, false positive yes/no, no code changes: **jev-fast-decision**. It is a noul screen on evidence supplied in the message.
5. Edit check-setup.sh and update tests: **none**. It is code editing, which the jev description excludes, and no other skill fits.
6. Trace why `make start` fails and walk the call chain: **none**. It is code investigation, not a typed judgment on supplied state.
7. Run `make check-server` and fix failures: **none**. It means running commands and editing.
8. Plan and implement the JEV_API_URL migration: **none**. It is multi-step implementation, not a typed judgment, and there is no existing plan for ai-kit-spec-execute to route.
9. Support-ticket router in a web app that calls TypeSafe Jev: **none in pool (typesafe-ai)**. This is building TypeSafe into an app, which the jev description excludes.
10. Brainstorm product features on System One: **none in pool (typesafe-ai)**. The product uses TypeSafe as a primitive, not the agent using Jev.
11. Replace prompt-and-parse in the checkout service with a TypeSafe typed judgment: **none in pool (typesafe-ai)**. It is application code calling TypeSafe.
12. In-app severity ranker with Jev, API call from the backend: **none in pool (typesafe-ai)**. It is an in-product integration.

Pass rule: lines 1–4 pick jev-fast-decision, and lines 5–12 do not.

---

# Skill Evaluation Report: jev-fast-decision

- **Files read:** `SKILL.md` (68 lines, 494 body words, under the 500-word cap from D-22), `reference.md` (133 lines), `backends/laya.md`, `backends/typesafe.md` and `backends/opencode.md`.
- **Spot-checked:** `scripts/jev_review.py` (parser, `request_body`, `_build_choice`/`_build_noul`, `_row_probe`, `probe_report`) and `scripts/eval_cases.py` (`--calibrate`).
- **Pattern:** Tool skill, short, with navigation to per-backend notes.
- **Knowledge ratio (E:A:R):** about 80:12:8.

**Things confirmed in the code:**
- `--probe` returns a `selected` field.
- Remote rows are never dialed without consent, not even for a probe (`_row_probe`, jev_review.py:1113-1118).
- `needs_fallback` is "forced or `top` < threshold" (jev_review.py:1474).
- The `consent grant|revoke|show` subcommand exists.
- The User-Agent behaviour matches `backends/opencode.md`.

**needs_fallback special check:** present. SKILL.md:38 says: "`needs_fallback: true` → **you decide that item with your own reasoning**; else advisory input." Common Mistakes at SKILL.md:59 reinforces it.

## Dimensions

D1 17/20 — 85%. Nearly every line is project-specific: the backend ladder, the consent semantics, the measured Laya state-bleed (0.46→0.86), the 2000-character guard, and the value-free question text. The deduction is for repetition: the consent rule and the Laya batching rule each appear three times, in NEVER (SKILL.md:46, :49), Red Flags (:53) and Common Mistakes (:57-58).

D2 12/15 — 80%. The procedure is domain-specific: probe, read the backend note, call, read the result recipe. It carries real thinking cues: advisory-only, "criteria name concrete signals" (:34), and summarising a hunk as the pattern rather than the value (:41). The deeper framing, "the model sees only `state`, not the conversation" and "a question with nothing to judge against still gets a confident-looking, meaningless answer", sits only in reference.md:20, not in the body.

D3 13/15 — 87%. The NEVER list (:45-49) is specific. It is backed by verbatim baseline rationalizations (reference.md:129-133) and a measured state-bleed reason (backends/laya.md:20-24). In the body, the "why" for :47-48 is implied rather than stated.

D4 14/15 — 93%. The name is valid. The description says WHAT (noul, choice, score, screening evidence), WHEN ("Use when a fast, cheap typed judgment beats a full reasoning pass") and has keywords (Laya, TypeSafe, OpenCode Zen, System One). Its exclusions route correctly, as the activation picks show. Small loss: it spends words on body-level semantics ("needs_fallback means…") instead of concrete trigger phrases such as "triage findings", "false positive", "rate severity" or "pick one".

D5 12/15 — 80%. It is well layered and the triggers are conditional: `backends/<selected>.md` (:12), the status table in reference.md (:40), and reference.md before `score`/receipts (:68). It loses points for three reasons:
- No "Do NOT load" guidance.
- No trigger to read reference.md before building a `choice` or `noul` item.
- "Required reading" (:61-66) lists four external URLs with no condition for when to read them.

D6 13/15 — 87%. Low freedom where it is fragile (consent, off-machine sends, the exact client script) and medium freedom for interpreting answers. The only call example pins `JEV_BACKEND=laya` (:25), and an explicit backend never falls back (:20). An agent whose probe selected `typesafe` gets no matching activation line in that backend note.

D7 8/10 — 80%. It is a clear, compact Tool pattern with routing to the per-backend notes. Minor drift: Red Flags and Common Mistakes are near-duplicate sections, and reference.md mixes runtime lookup tables with host-installation notes (`## Hosts`) the calling agent does not need.

D8 12/15 — 80%. It handles the common case clearly: a status → action table, the consent ask/retry loop, the `needs_fallback` recipe, and Laya error handling. The gaps are listed under Important and Minor below.

## Findings

**Critical**
- None.

**Important**
- **The choice item shape is missing from the body** (`skills/jev-fast-decision/SKILL.md:27-30`, with `:68` triggering reference.md only for `score`/receipts).
  - "Picking among named options (choice)" is one of the three headline uses.
  - The body's only example of an explicit `criteria` is a list (score).
  - `_build_choice` (jev_review.py:289-291) rejects anything but a map of at least 2 entries, returning `invalid_input`. An agent copying the example's shape for a choice item will fail.
  - Fix: add a one-line choice example, or make the reference.md trigger at :68 cover building `choice`/`noul` items.

**Minor**
- **`reviewed_head` outside a git repo** (`SKILL.md:27`, `reference.md:8`). The client requires exactly 40 lowercase hex characters (jev_review.py:344). Nothing says what to send outside a git repo, or that sending the placeholder literally gets `invalid_input`.
- **Untriggered "Required reading"** (`SKILL.md:61-66`). Four external URLs are labelled required but have no condition for when to read them. That risks an unneeded web fetch on every call, or the list being ignored entirely.
- **Triple statement** (`SKILL.md:46`, `:53`, `:57-59`). The consent and Laya batching rules repeat across NEVER, Red Flags and Common Mistakes, which wastes tokens.
- **Example pins laya** (`SKILL.md:25`). The only call example sets `JEV_BACKEND=laya`. Copying it after the probe selected a remote backend pins the wrong backend, and `backends/typesafe.md` and `backends/opencode.md` give no activation line.
- **`--skip-local` undocumented** (`jev_review.py:1906`). The "second opinion, no local run" flag appears in neither SKILL.md nor reference.md.
- **Runtime-irrelevant content** (`reference.md:120-125`). The `## Hosts` section covers installation, not calling the skill.

## End lines

D1 17/20
D2 12/15
D3 13/15
D4 14/15
D5 12/15
D6 13/15
D7 8/10
D8 12/15
CURRENT 101/120
CRITICAL 0
IMPORTANT 1
FLOORS ok
ACTIVATION ok
CITE_PROBE skills/jev-fast-decision/SKILL.md:12
> From this skill's directory, run `python3 -B scripts/jev_review.py --probe` before the first call of a session; read `backends/<selected>.md` before the first call with that backend.
CITE_BACKEND skills/jev-fast-decision/SKILL.md:12
> From this skill's directory, run `python3 -B scripts/jev_review.py --probe` before the first call of a session; read `backends/<selected>.md` before the first call with that backend.
VERDICT pass

---

Notes:
- **What I did not check:** I made no live probe or run of the client, so the backend figures are taken from the docs as written. I did not open `evals/cases.jsonl` and spot-checked `eval_cases.py` only for `--calibrate`. I did not read the earlier in-session judge report, to keep this evaluation independent.
- **Risks:**
  - D5 and D8 sit exactly at their floor of 12, so a stricter judge could fail the skill on the choice-shape gap alone.
  - One skill file is out of date: the `jev-fast-decision` description installed for this session's Skill tool differs from the one in this tree.

## Run 3 (after fix round 2: 39d61eb; final, fix cap 2 of 2 used)

DIGEST a4b2dbc04b1e3984
TREE e66c5517ddd061ac498331ff8134815b4e616d5c

# skill-judge report: jev-fast-decision (fresh, independent, current tree)

I followed the prompt order. I made the activation picks using only the `skills/*/SKILL.md` frontmatter. After that I opened `skills/jev-fast-decision/SKILL.md` (68 lines, 576 words), `reference.md`, `backends/{laya,typesafe,opencode}.md`, and the CLI surface of `scripts/jev_review.py`, and checked the body's example against the client's validators. I did not read the earlier in-session reports.

## PART 2: Activation picks (frontmatter only, done first)

1. jev-fast-decision. It asks for a yes/no triage on evidence that is already supplied, with no edits. That matches "yes/no (noul)… screening evidence".
2. jev-fast-decision. It asks to pick one of three named options. That is the `choice` shape.
3. jev-fast-decision. It asks for a 0–3 rubric score on text in the prompt, with no investigation. That is the `score` shape.
4. jev-fast-decision. It asks for a yes/no false-positive call on grep hits it already has, with no code changes.
5. none. It edits a script and tests, and the description says "Not for… editing code".
6. none. It needs a multi-step call-chain trace, not a typed judgment.
7. none. It runs a command and fixes failures. That is action, not judgment.
8. none. It is multi-step planning plus code change. No skill under `skills/` fits.
9. none. typesafe-ai is not under `skills/`. The jev description excludes "building TypeSafe into an app (typesafe-ai)".
10. none. This is product ideation on TypeSafe as an app primitive, which the same exclusion points to typesafe-ai.
11. none. It puts TypeSafe into application code, which is the excluded app-integration case.
12. none. It is an in-app Jev feature with a backend API call, so the exclusion points it to typesafe-ai.

The pass rule holds. All 4 `expect jev-fast-decision` lines pick it, and none of the 8 `expect none` or `expect typesafe-ai` lines do.

Cite lines:
- `CITE_PROBE skills/jev-fast-decision/SKILL.md:12` with the line: "From this skill's directory, run `python3 -B scripts/jev_review.py --probe` before the first call of a session; read `backends/<selected>.md` before the first call with that backend."
- `CITE_BACKEND skills/jev-fast-decision/SKILL.md:12` (same line as above): "...read `backends/<selected>.md` before the first call with that backend."

## PART 1: Dimensions

D1 17/20 (85%). Mostly expert knowledge that Claude would not have:
- the measured state-bleed figure (0.46 to 0.86)
- the consent rules, including the "the key is set is not consent" rationalizations
- the rule to send value-free question text instead of raw hunks
- the TypeSafe and Zen routes being separate
- `needs_fallback` semantics.

Points lost for the Red Flags and Common Mistakes sections repeating the NEVER list.

D2 13/15 (87%). The thinking framing is good: answers are advisory only, and a low or `unsupported` answer means "investigate yourself". The domain procedures are ones Claude would not know: probe first, read the selected backend's file, then the consent grant-or-export-and-retry loop. There is no explicit "before you send, ask..." framework for when Jev beats your own reasoning.

D3 13/15 (87%). The NEVER list is specific. Most lines carry their reason, and the consent rationalizations are taken word for word from RED baseline runs. Line 47 (raw sources and secrets) gives no reason beyond the obvious.

D4 14/15 (93%). The frontmatter is valid. The description covers WHAT, WHEN, keywords, and exclusions, and all 12 activation lines pass. It lacks the "batch" and "triage findings" trigger words, even though batching is a supported use.

D5 12/15 (80%). The backend trigger is built into step one (line 12). There are conditional pointers to `reference.md` at lines 40, 53 and 68. Points lost:
- the "Required reading" block has no load condition
- the `reference.md` trigger sits at the end of the file, not in "Call it"
- there is no "Do NOT load" guidance.

D6 14/15 (93%). Freedom is low where mistakes are costly: consent, the exact command line, environment variables, never batching Laya calls. It is medium where judgment is needed: question wording, how to summarize a hunk.

D7 9/10 (90%). A compact Tool/Navigation hybrid with a routing table, one working example, a status recipe, and the NEVER list.

D8 13/15 (87%). I checked the example against the validators: the shorthand item, the score item with a 2–10 level list, the required `reviewed_head` and the `GSD_PATH_JEV=1` kill switch all pass. Status handling and the consent loop are covered. Gaps: the `noul` shape has no example and is not in the line 68 trigger, the consent command is not shown in full, and `--skip-local` is undocumented.

Special check: the `needs_fallback` recipe is present at line 38: "`needs_fallback: true` → **you decide that item with your own reasoning**". It is also backed by line 59.

### Findings

Critical: none.

Important (1):
- `skills/jev-fast-decision/SKILL.md:61-66`: the "Required reading" heading lists 4 external web pages with no condition for when to read them. Taken literally, an agent fetches 4 pages before any call, which defeats the "fast, cheap" purpose. Make each link conditional (for example, "only when an item needs images or box"), or move them to `reference.md`.

Minor:
- `skills/jev-fast-decision/SKILL.md:68`: the `reference.md` loading trigger comes last, after the external links, not in "Call it". It also leaves out `noul`, the most common yes/no type, and the body has no `noul` example.
- `skills/jev-fast-decision/SKILL.md:20`: it says `consent grant <backend>` without the full command, `python3 -B scripts/jev_review.py consent grant <backend>`.
- `skills/jev-fast-decision/SKILL.md:51-59`: Red Flags and Common Mistakes repeat NEVER lines 46 and 49.
- `skills/jev-fast-decision/scripts/jev_review.py:1906`: the `--skip-local` flag (remote second opinion only) is not documented in SKILL.md or `reference.md`.
- The skill has no "Do NOT load" guidance, for example "skip the other backends' notes" or "skip the capability matrix for plain choice or noul".

D1 17/20
D2 13/15
D3 13/15
D4 14/15
D5 12/15
D6 14/15
D7 9/10
D8 13/15
CURRENT 105/120
CRITICAL 0
IMPORTANT 1
FLOORS ok
ACTIVATION ok
CITE_PROBE skills/jev-fast-decision/SKILL.md:12
CITE_BACKEND skills/jev-fast-decision/SKILL.md:12
VERDICT pass

Open after the 2-round fix cap (owner review / 21.1 code review): Important — SKILL.md 'Required reading' lists 4 external links with no load condition; Minors as listed.

## Run 4 (final-tree check after 5af9c01 and a907c41; fresh opus subagent)

An earlier final-tree check on the c4849be tree scored 106/120, 0 Critical, 0 Important, pass;
its one actionable Minor (the Zen default POST target had no `/systemone` path) was fixed in
5af9c01 and its full text was not kept.

DIGEST 9ad03a73e9daeb6e
TREE a0f85261f43470d5053507d0d6d00898a5aa7aa0

Activation picks first, from the frontmatter only (the body was opened in a tool call before
the picks were written; no pick depends on it): lines 1-4 pick jev-fast-decision, lines 5-12
pick none. Pass rule holds. `needs_fallback` recipe present at SKILL.md:38.

Findings verified by the orchestrator against `scripts/jev_review.py` and fixed in 3701297:
- Important 1: `backends/typesafe.md` said a 402 escalates; with one model id `_post` returns
  `next_model` and `_fold_rung` makes it final (`http_402`).
- Important 2: `backends/opencode.md` / `reference.md` said a `JEV_OPENCODE_MODEL` pin covers
  both ids; a pin sends one id and turns off free-to-paid.
- Important 3: the opencode row refuses `score` (cell `unverified`); with `JEV_BACKEND=opencode`
  one score item stops the request with `unsupported_feature`. Undocumented.
- Important 4: the attempts entry always named the first model id (code bug, fixed with tests)
  and the note implied a recovered free 429 leaves an entry.
Minors (13) left for the owner: 4xx wording in both backend notes, Laya 401/403 token in
reference.md, the example's `JEV_BACKEND=laya`, the TypeSafe key-file source in the table,
`reviewed_head` format, laya.md threshold sentence, the choice trigger, `remote_available` on
`ok`, `consent_required_for_remote` scope, opencode batch cell, a `jev-latest` comment, the
Required-reading links.

D1 17/20
D2 12/15
D3 13/15
D4 14/15
D5 13/15
D6 13/15
D7 8/10
D8 12/15
CURRENT 102/120
CRITICAL 0
IMPORTANT 4
FLOORS ok
ACTIVATION ok
CITE_PROBE skills/jev-fast-decision/SKILL.md:12
CITE_BACKEND skills/jev-fast-decision/SKILL.md:12
VERDICT pass

## Run 5 (final tree after the code-review fixes 1b7798b..3a3ffa8; fresh opus subagent)

DIGEST 9ad03a73e9daeb6e
TREE 03be1443594e25d0a2d1f5f8d2180ed960ce7e1b

Activation picks made from frontmatter only, before any body: lines 1-4 pick
jev-fast-decision, lines 5-12 pick none. Pass rule holds. `needs_fallback` recipe present at
SKILL.md:38. Every claim in SKILL.md, reference.md and backends/*.md checked against
`scripts/jev_review.py`; the run-4 Important items are no longer reported.

Open for the owner (not fixed: the gate passes on score and the fix cap is spent):
- Important I1: the SKILL.md:25 example pins `JEV_BACKEND=laya`, so a copied call never reaches
  a consented remote or the auto-mode consent ask; use the probe's selected row instead.
- Minors: 4xx caller-error wording in both backend notes; Laya 401/403 token in reference.md;
  laya.md lines 32 and 37-38; the five TypeSafe key sources not named in the SKILL.md table;
  Required-reading links without a trigger; repeated Red Flags / Common Mistakes text; the
  reference trigger's placement; `remote_available` on `ok` and `--skip-local` undocumented;
  the `_opencode_url` docstring vs the probe's "documented" label.

D1 18/20
D2 13/15
D3 13/15
D4 14/15
D5 13/15
D6 13/15
D7 8/10
D8 13/15
CURRENT 105/120
CRITICAL 0
IMPORTANT 1
FLOORS ok
ACTIVATION ok
CITE_PROBE skills/jev-fast-decision/SKILL.md:12
CITE_BACKEND skills/jev-fast-decision/SKILL.md:12
VERDICT pass

## Run 6 (final tree 07a1efc; one clean-context native Opus subagent — owner judge set 2026-10-23)

DIGEST 8539e9d42a797883
TREE 4e0b112816d8f3cd409dcc8866a68b099e8b7999

Activation picks from frontmatter only, before any body: lines 1-4 pick jev-fast-decision,
lines 5-12 pick none. Pass rule holds. `needs_fallback` recipe present at SKILL.md:38. The
run-5 Important (laya pin) is resolved.

Open for the owner (not fixed, to keep the judged tree final; gate passes on score):
- Important I1: the canonical example sends `"evidence": "your grep output"` while NEVER
  (SKILL.md:47) bans raw sources without saying whether it covers local Laya; scope the rule to
  off-machine rows or make the example a value-free summary.
- Minors: 4xx caller-error wording in both backend notes (and the `_opencode` docstring); Laya
  401/403 token in reference.md; laya.md:37-38 fragment; `--calibrate` belongs to
  eval_cases.py; Required-reading links without a trigger; Red Flags / Common Mistakes repeat
  NEVER; the TypeSafe key sources in the SKILL.md table; `remote_available` on `ok`;
  `--skip-local` undocumented. D2, D5 and D8 sit at their floor of 12.

D1 17/20
D2 12/15
D3 13/15
D4 14/15
D5 12/15
D6 14/15
D7 9/10
D8 12/15
CURRENT 103/120
CRITICAL 0
IMPORTANT 1
FLOORS ok
ACTIVATION ok
CITE_PROBE skills/jev-fast-decision/SKILL.md:12
CITE_BACKEND skills/jev-fast-decision/SKILL.md:12
VERDICT pass

## Run 7 (final tree e34499e; one clean-context native Opus subagent; final round, no further fixes)

DIGEST 4e0a4fcbf5ef4634
TREE 675622459707a4131f602cdae8d17ba668def16d

Activation picks from frontmatter only: lines 1-4 pick jev-fast-decision, 5-8 none, 9-12
typesafe-ai (host-installed). Pass rule holds. `needs_fallback` recipe present at SKILL.md:38;
the example payload validated in-process against `request_body`. The run-6 Important (raw
evidence in the example) is resolved.

Open for the owner:
- Important I1: SKILL.md:20/:39 show only `JEV_ALLOW_REMOTE=1`, which opens every remote; a
  TypeSafe-only yes exported as `=1` lets an escalated item reach OpenCode Zen without consent.
  Say: export the approved backends as a comma list, `1` only when every remote was approved,
  or use `consent grant <backend>`.
- Minors: 4xx caller-error wording (both notes, `_opencode_classify` docstring); Laya 401/403
  token; `answer_confidence` vs `confidence`; `consent_used` lists uncalled remotes;
  `remote_available` on `ok`; read every candidate's backend note; noul shape trigger;
  Required-reading links; laya.md:37-38 fragment; Red Flags repetition; loopback-http exception.

D1 18/20
D2 13/15
D3 13/15
D4 14/15
D5 12/15
D6 13/15
D7 9/10
D8 12/15
CURRENT 104/120
CRITICAL 0
IMPORTANT 1
FLOORS ok
ACTIVATION ok
CITE_PROBE skills/jev-fast-decision/SKILL.md:12
CITE_BACKEND skills/jev-fast-decision/SKILL.md:12
VERDICT pass

## Run 8 (final tree beb51f7; one clean-context native Opus subagent; LAST round)

DIGEST 8d3911535ab993ef
TREE c003aa42896ab240f1dcff2a3ece6e4070b9ba99

Activation picks from frontmatter only: lines 1-4 pick jev-fast-decision, 5-8 none, 9-12
typesafe-ai. Pass rule holds. `needs_fallback` recipe present at SKILL.md:38; the example
payload passes `request_body` validation. No Important finding: the run-7 consent-scope item is
resolved.

Minors left for the owner: Laya 401/403 and other 4xx tokens; TypeSafe and Zen caller-error
code lists; the remote 8,000-character state cap is undocumented in this skill; the
`reviewed_head` placeholder and running from the skill directory; key sources in the table;
the choice qualifier; Required-reading links; `retry explicitly`; laya.md:37-38 fragment;
"deprecated" vs ignored env vars; 0600 vs no group/other bits; `--skip-local`,
`remote_available` and the full `consent grant` line undocumented; `consent_used` lists
uncalled remotes; score `level` is a string key.

D1 18/20
D2 13/15
D3 13/15
D4 14/15
D5 13/15
D6 14/15
D7 9/10
D8 13/15
CURRENT 107/120
CRITICAL 0
IMPORTANT 0
FLOORS ok
ACTIVATION ok
CITE_PROBE skills/jev-fast-decision/SKILL.md:12
CITE_BACKEND skills/jev-fast-decision/SKILL.md:12
VERDICT pass
