---
name: ai-kit-gsd-spec-discuss
description: "Chains GSD /gsd-spec-phase --auto then assumptions-mode /gsd-discuss-phase over a range of phases (SPEC.md, then CONTEXT.md + DISCUSSION-LOG.md, committed per phase), settling gray areas through the `jev-fast-decision` client's decision ladder (local first, then consented remotes in table order, then own reasoning) with logged decisions, a deferred ledger, cross-phase amendments and a best-over-easy design rule (simplest-that-keeps-user-quality under workflow.mvp_mode). Use when asked to spec and discuss several GSD phases unattended or in one run (\"spec/discuss phases 17-24\", \"run spec-phase and discuss-phase for every undiscussed phase\", \"--analyze --all --batch --assumptions\"), or to use jev / Laya / TypeSafe / System One for GSD planning decisions. Works with no decision backend installed. Not for plan-phase or execute-phase."
---

# ai-kit-gsd-spec-discuss

Takes phases N..M through **spec** (the WHAT, `NN-SPEC.md`) then **assumptions-mode discuss**
(the HOW, `NN-CONTEXT.md` + `NN-DISCUSSION-LOG.md`), one phase at a time, deciding gray areas
yourself with advisory help. It never plans or executes.

**The mindset:** you are the decider. Laya and TypeSafe are cheap typed screens, not verdicts.
Your own reasoning against verified evidence is the last rung and the most important one:
Laya is often low-confidence, and sometimes confidently wrong. Stop the run only for a decision
that blocks other decisions *and* that nothing settles with high confidence; everything else is
decided provisionally and shown at the end.

## 0. Set up once per run

1. **Resolve this skill's scripts dir** (`S`) once, and use the printed literal path:
   ```bash
   for d in "$(dirname "<absolute path of THIS SKILL.md>")" "$HOME/.claude/skills" "$HOME/.agents/skills" \
            "${XDG_CONFIG_HOME:-$HOME/.config}/opencode/skills" "$HOME/.cursor/skills" "$HOME/.pi/agent/skills"; do
     for c in "$d/scripts" "$d/ai-kit-gsd-spec-discuss/scripts"; do
       [ -f "$c/decide.py" ] && { printf '%s\n' "$c"; break 2; }; done; done
   ```
2. **Resolve `gsd_run`** with gsd-core's standard resolver (`references/gsd-run-resolver.md`
   inside the gsd-core install; it finds the repo's own `.claude/gsd-core/bin/gsd-tools.cjs`
   before any user-level install).
   The workflows dir is `<dir of gsd-tools.cjs>/../workflows/`. No gsd-core → stop with the
   resolver's own install hint.
3. **Detect backends:** `python3 "$S/decide.py" detect` — the shared `jev-fast-decision`
   client's probe table, one entry per table backend (`laya`, `typesafe`, `opencode`), labels
   only (key *source*, never the key). Laya's URL comes from `JEV_LAYA_URL`, `AI_KIT_LAYA_URL`
   or a loopback `JEV_API_URL`, default `http://127.0.0.1:8010`, probed via `/health` (not
   bare TCP). Keys the client reads: TypeSafe `TYPESAFE_API_KEY` or
   `${XDG_STATE_HOME:-~/.local/state}/typesafe/api_key`; OpenCode Zen `OPENCODE_ZEN_API_KEY` or
   `opencode-zen.key` in `~/.pi/agent/keys.json`. A status `no_client` (no client found) or
   `incompatible_client` (the client beside the skill predates the shared one) means own
   reasoning only, until the owner runs `python3 tools/setup.py install --headless --skills
   jev-fast-decision --replace-existing`.
4. **Pick the range.** Explicit `--from N --to M` or a list wins. Otherwise:
   `gsd_run query roadmap analyze > <tmp>.json` then
   `python3 "$S/phase_range.py" --roadmap <tmp>.json` — proposes phases with no CONTEXT or a
   SPEC newer than its CONTEXT (git commit time), each with its reason. A "SPEC newer" reason
   can be a false positive: a later phase's dated cross-phase amendment also touches the SPEC.
   Check `git log -1 -- <SPEC>`; if that commit only appended an amendment the CONTEXT already
   reflects, drop the phase from the proposal and say why.
5. **Ask exactly one question**, only when needed: confirm or trim the proposed range, and —
   if a remote backend's `detect` entry has `status: consent_required_for_remote` (a keyed
   remote this session has not allowed; a keyless one reads `missing_api_key`) — ask for consent
   in the same question, naming each backend and its host, "summaries only, never code or
   secrets", and the revoke command (`python3 "$S/decide.py" consent revoke <backend>`). On yes: `python3 "$S/decide.py" consent grant <backend>`
   (`consent grant typesafe` still works; the client keeps the record, same once-per-user
   rule). Consent on file asks nothing. After a ladder call, announce a `consent_used` entry only
   when that backend's column is non-null: "using <backend> (consent recorded <date>)" (the
   list names every remote with consent on file, called or not).
6. **Read the quality rule:** `gsd_run query phase.mvp-mode <N>` per phase (`active` true →
   MVP branch), falling back to `gsd_run query config-get workflow.mvp_mode --default false
   --raw`. Bare `config-get` exits "Key not found" when the key is unset.

**MANDATORY — read `references/decision-table.md` before the first ladder call.**

## 1. Per phase: spec

Read and execute `<workflows>/spec-phase.md` end-to-end with arguments `N --auto` (read the
file; do not delegate to another skill — skill-to-skill calls are unreliable on some hosts).

- An existing SPEC is reused, as the workflow does.
- **Live-verify before you write a claim**: installed versions, real config keys, real CLI
  output in a scratch dir. A SPEC sentence from memory is a defect.
- Where the workflow says "select the recommended default", run the open items through the
  ladder (§3) and log them in the Interview Log (format: `references/log-formats.md`).
- **Edge Coverage is engine output, never hand-written.** Write the requirements, then
  `python3 "$S/edge_floor.py" floor <SPEC>`; resolve each floor row (✅ covered / 🧪 backstop),
  mark any row you add with `(added …)` in the Resolution cell, and leave every `unclassified`
  row `⚠ UNRESOLVED`. Gate with `python3 "$S/edge_floor.py" check <SPEC>` (exit 1 = drift).
  Amending a requirement's text later changes its floor: re-run `check` after every amendment.
  Exit 2 means node or the engine is missing — fail closed: stop the spec step for this phase
  (the workflow itself cannot compute the floor either), never write the table by hand.
- The workflow commits the SPEC itself.

## 2. Per phase: discuss (assumptions mode)

Read and execute `<workflows>/discuss-phase-assumptions.md` with argument `N` — **never** pass
`--assumptions` (routes to `list-phase-assumptions.md`, which writes no files) and **never**
pass `--auto` (it chains into plan-phase and auto-accepts Unclear items). Skip the workflow's
`auto_advance` step regardless of config; automatic mode can dispatch plan-phase there without
changing the user's settings. Encode the user's `--analyze --all --batch` intent yourself: every
analyzer area in one pass; 2–3 alternatives
per Likely/Unclear item with best and easy marked; all the phase's questions in one ladder run (the client still sends Laya one item per call).

Pre-answer the workflow's prompts by rule:
- existing CONTEXT → "Update it" (in place, additively — locked decisions stay verbatim);
- existing plans → "Continue and replan after";
- todos → fold those scoring ≥ 0.4;
- assumptions → "Yes, proceed" only after every Unclear item went through the ladder.

**Spawn the analyzer** (`gsd-assumptions-analyzer`) through the host's subagent mechanism when
`init phase-op` reports it installed (in Claude Code: the Agent tool, background). Omit `model`
when it resolves to `inherit` or empty. No subagent support → run the brief inline and say so
in the DISCUSSION-LOG.

**MANDATORY — read `references/analyzer-brief.md` before spawning; fill every placeholder.**
The analyzer returns "Jev question" lines; it never calls jev itself (consent, the ladder
and the answer log belong to the shared client).

Then: ladder (§3) → write CONTEXT + DISCUSSION-LOG (**MANDATORY — read
`references/log-formats.md` first**) → one commit:
`gsd_run query commit "docs(NN): ..." --files <CONTEXT> <LOG> <every cross-phase amended file>`.
After the range (or batched): `gsd_run query state.record-session --stopped-at "..."
--resume-file <last CONTEXT>` and a separate `docs(state)` commit of `.planning/STATE.md`.

## 3. The ladder

```bash
python3 "$S/decide.py" ladder < items.json        # {"items": [...]}
python3 "$S/decide.py" ladder --second-opinion < contested.json
```

Item shape (`choice`, `noul` or `score`), summaries only:
`{"id": "B07_segments", "type": "choice", "instructions": "<standalone question>",
"context": "<the facts it turns on, non-empty>", "criteria": {"a": "neutral description",
"b": "neutral description"}}`. A `choice` item needs `criteria` with two or more options; a
`noul` item takes no `criteria` or exactly `{"true": "...", "false": "..."}`; a `score` item's
`criteria` is a list of 2-10 levels. Malformed or code-bearing items are rejected
alone (`invalid_input` + reason) — fix and resubmit. A repeated `id` is rejected alone
(`duplicate_id`); an `id` starting with `#` is `reserved_id` (that prefix keys rejections).

The ladder is **one client call per run**: decide.py validates the items and maps the
client's per-item rung trail onto one column per table backend, each
`{choice, top, fallback, model}`, `{error}` or null = not called, plus `decided_by` (the
last confident rung, else `own_reasoning`); each column's `top` is its winning probability. The client
runs the local backend one item per call; `fallback` follows each row's own threshold, and
is also forced when one request's state exceeds the row's size cap (Laya 2,000 characters,
TypeSafe and OpenCode Zen 8,000; TypeSafe sends every pending item in one request). Keep each
item's text short; `fallback: true` with a `top` above the threshold is that size flag:
shorten the item and re-ask instead of logging it as low confidence.

- Describe options **neutrally**. Labelling one "best" or "easy" just echoes your framing back.
- A high local answer contradicting verified evidence or a locked decision gets
  `--second-opinion` before you override it (the client skips the local rung; the first consented
  remote answers, a later one only on an error). The remote rung sided with the evidence every time here (17 K01/K08, 18.1
  T2, 23 B10/B12, 24 C13).
- Laya is not deterministic: the same item scored 0.74 then 0.67 (fb) on two runs. Never treat
  a single Laya number as stable.
- Every answering column low (`fallback: true`, the client's `needs_fallback`) or errored → **own reasoning** against the SPEC, earlier CONTEXT
  files and the live facts. Log it, and ledger it when it blocks nothing.

## 4. Ledger and stop rule

Keep the ledger in a run file under the system temp dir (`tempfile.gettempdir()`), appended as
you go, and mark each ledgered row in the committed DISCUSSION-LOG ("own reasoning … ledger").
"Blocking" = another decision **in this run** depends on it; an item that only blocks later
planning is ledgered with `Blocks: <what>`. User-owned preconditions (land or shelve a branch)
go on the ledger. A low-confidence item that contradicts a **user-locked** decision is decided
provisionally and flagged "needs confirmation" — never a silent override.

Stop only for blocking × unresolved; show that question **with** the ledger. Otherwise print
the ledger at the end. Full matrix: `references/decision-table.md`.

## 5. Quality rule (goes into every brief)

- `mvp-mode` inactive: **the best design wins over the smallest diff.**
- `mvp-mode` active: the simpler design wins, as long as it does not lower what reaches the
  product's user.
- Ponytail-style "least code" findings decide *how* code is written, never *which* design wins.

## 6. Live facts and cross-phase amendments

A fact found in phase K that contradicts phase J's SPEC/CONTEXT, `REQUIREMENTS.md` or
`ROADMAP.md` amends them **in K's commit**, dated, with the markup in `log-formats.md`. Grep
the other phases for the statement first. A coupling (K's decision constrains J's HOW) is
handed to J's discuss. Examples: `resolve_model_ids: "omit"` found in 19 amended 17 R5/R13 and
18 R13; the pi capability registry found in 22 amended 17 D-22.

## 7. Pacing

Where the host has background subagents with completion notices, start phase K+1's analyzer
while you write phase K's SPEC or CONTEXT when coupling is low; name any coupling in its brief.
Never use a background result before its notification arrives. Elsewhere, run phases strictly
in sequence (flag that gap in the log).

## NEVER

- **NEVER pass `--assumptions` to the discuss command** — it routes to a listing workflow that
  writes nothing; the run looks complete and produces no CONTEXT.
- **NEVER pass `--auto` to discuss** — it auto-advances into plan-phase and accepts the
  analyzer's default for Unclear items, bypassing the ladder and the log.
- **NEVER hand-batch items into one Laya question** — one item's context changes another's answer.
- **NEVER treat a Laya, TypeSafe or OpenCode Zen answer as the decision** — log it as advisory; the decision
  column is yours, with its reason.
- **NEVER send code, diffs, file contents, config values or secrets** — summaries only;
  `decide.py` rejects fences and key shapes, but it is defense in depth, not a guarantee.
- **NEVER flip `workflow.discuss_mode` to get assumptions mode** — plan-phase and progress read
  it too, and a crash leaves it flipped.
- **NEVER regenerate an existing CONTEXT wholesale** — user-locked decisions from an earlier
  interactive discuss are lost silently; amend in place.
- **NEVER hand-write the Edge Coverage floor** — the engine's floor depends on the exact
  requirement text; prose-derived rows drift (this milestone's 16.1–19 SPECs did).
- **NEVER print or log a key** — check keys by name; `decide.py detect` shows source labels.

## Host gaps (flagged, not hidden)

- Subagent spawn and background completion notices are host features. Without them the brief
  runs inline (more context used) and pacing (§7) does not apply.
- `init phase-op` reports `agents_installed` / `missing_agents` / `agent_runtime`; trust it
  over assumptions about the host.

## References — load only at the trigger

- `references/decision-table.md` — before the first ladder call.
- `references/analyzer-brief.md` — before spawning (or running inline) the analyzer.
- `references/log-formats.md` — before writing a SPEC Interview Log, CONTEXT, DISCUSSION-LOG,
  an amendment, or the ledger.
- `references/worked-examples.md` — only when a case is unclear: an override, a second
  opinion, a both-low item, an out-of-scope fix.

Do NOT load the references for a phase whose SPEC and CONTEXT are already current
(`phase_range.py` gives no reason for it) — skip the phase instead.
