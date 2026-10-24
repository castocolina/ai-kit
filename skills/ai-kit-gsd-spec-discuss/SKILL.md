---
name: ai-kit-gsd-spec-discuss
description: "Chains GSD /gsd-spec-phase then /gsd-discuss-phase over a range of phases (SPEC.md, then CONTEXT.md + DISCUSSION-LOG.md, one commit per phase), settling gray areas through the `jev-fast-decision` client's decision ladder with logged decisions, a deferred ledger, cross-phase amendments and a best-over-easy design rule. Two run modes, picked once: auto (spec `--auto`, discuss in assumptions mode) or interactive (discuss-phase with the user answering). Use when asked to spec and discuss several GSD phases unattended or in one run (\"spec/discuss phases 17-24\", \"run spec-phase and discuss-phase for every undiscussed phase\", \"--analyze --all --batch --assumptions\"), or to use jev / Laya / TypeSafe / System One for GSD planning decisions. Works with no decision backend installed. Not for plan-phase or execute-phase."
---

# ai-kit-gsd-spec-discuss

Takes phases N..M through **spec** (the WHAT, `NN-SPEC.md`) then **discuss**
(the HOW, `NN-CONTEXT.md` + `NN-DISCUSSION-LOG.md`), one phase at a time, deciding gray areas
yourself with advisory help. It never plans or executes. Backend order on the ladder: the local backend first, then
consented remotes in the client's table order, then your own reasoning (§3). Two run modes,
picked once in §0:
**auto** (spec `--auto`, discuss assumptions-mode) and **interactive** (spec without `--auto`,
discuss in its standard discuss mode with the user answering).

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
   If it prints nothing, **stop the run** (fail closed, like `edge_floor` exit 2).
2. **Resolve `gsd_run`** with gsd-core's standard resolver (`references/gsd-run-resolver.md`
   inside the gsd-core install; it finds the repo's own `.claude/gsd-core/bin/gsd-tools.cjs`
   before any user-level install).
   The workflows dir is `<dir of gsd-tools.cjs>/../workflows/`. No gsd-core → stop with the
   resolver's own install hint. The `gsd_run` alias survives across shell calls only on hosts
   with `CLAUDE_ENV_FILE`; elsewhere, print the resolved gsd-tools path here and use that
   literal path in later calls, like `S`.
3. **Detect backends:** `python3 "$S/decide.py" detect` — the shared `jev-fast-decision`
   client's probe table (one entry per backend: `laya`, `typesafe`, `opencode`), labels
   only (key *source*, never the key). Key names, file modes and endpoint precedence are in
   the client's `reference.md` (Environment) and `backends/`. A status `no_client` (no client
   found) or `incompatible_client` (the client beside the skill predates the shared one)
   means own reasoning only, until the owner runs `python3 tools/setup.py install --headless
   --skills jev-fast-decision --replace-existing` from the ai-kit checkout.
   Then check the agents' skill wiring, one portable loop (gsd-core exits 0 and only drops a
   skipped entry from that agent's prompt, so report every line verbatim with its cause):
   ```bash
   for a in gsd-assumptions-analyzer gsd-advisor-researcher; do
     gsd_run query agent-skills "$a" 2>&1 >/dev/null | grep -F '[agent-skills] WARNING'
   done
   ```
   - "failed path check (symlink escape?)": the skill's real path is outside the host's global
     skills dir and no `agent_skills_security.trusted_global_roots` entry covers it;
   - "not found": nothing is at that path.

   The fix is to re-run `ai-kit-gsd-curated-config`, which wires only references gsd-core
   resolves (a project copy such as `skills/<name>`, or a trusted ai-kit install). This skill
   never edits config itself; the run continues without that skill.
4. **Pick the range.** Explicit `--from N --to M` or a list wins and is passed through to
   `phase_range.py` (`--from N --to M`, or `--list a,b`). Otherwise:
   `gsd_run query roadmap analyze > <tmp>.json` then
   `python3 "$S/phase_range.py" --roadmap <tmp>.json` — proposes phases with no CONTEXT or a
   SPEC newer than its CONTEXT (git commit time), each with its reason. A "SPEC newer" reason
   can be a false positive: a later phase's dated cross-phase amendment also touches the SPEC.
   Check `git log -1 -- <SPEC>`; if that commit only appended an amendment the CONTEXT already
   reflects, drop the phase from the proposal and say why.
5. **Ask one question about the range**, only when needed (the run-mode ask in step 7 is
   separate): confirm or trim the proposed range, and —
   if a remote backend's `detect` entry has `status: consent_required_for_remote` (a keyed
   remote this session has not allowed; a keyless one reads `missing_api_key`) — ask for consent
   in the same question, naming each backend and its host, "summaries only, never code or
   secrets", and the revoke command (`python3 "$S/decide.py" consent revoke <backend>`). On
   yes: `python3 "$S/decide.py" consent grant <backend>`. Consent on file asks nothing. After
   a ladder call, announce `consent_used` only for backends whose column is non-null
   ("using <backend> (consent recorded <date>)").
6. **Read MVP mode once, per phase:** `gsd_run query phase.mvp-mode <N>` (`active` true →
   MVP branch). This one query is the single source for both the quality rule (§5) and the
   run-mode recommendation in step 7 — do not read `workflow.mvp_mode` a second way. If the
   per-phase query errors (an unresolvable phase), fall back to `gsd_run query config-get
   workflow.mvp_mode --default false --raw`. Bare `config-get` exits "Key not found" when
   the key is unset.
7. **Pick the run mode** (§1–§2). With the skill's `--auto` flag: auto path. Without it:
   read the project mode — `gsd_run query config-get mode`; a "Key not found" exit means the
   default (`interactive`) — then **ask the user once**: recommend the **auto path** when
   `mode` is `yolo` or the phase's `mvp-mode` is active (step 6's value, first phase of the
   range), the **interactive path** otherwise (interactive = spec-phase without `--auto`,
   discuss-phase in its standard discuss mode with the user answering). Never flip config
   keys to pick a path.

**MANDATORY — read `references/decision-table.md` before the first ladder call.**

## 1. Per phase: spec

Read and execute `<workflows>/spec-phase.md` end-to-end with arguments `N --auto` (auto path)
or plain `N` (interactive path) (read the
file; do not delegate to another skill — skill-to-skill calls are unreliable on some hosts).

- An existing SPEC is reused, as the workflow does.
- **Live-verify before you write a claim**: installed versions, real config keys, real CLI
  output in a scratch dir. A SPEC sentence from memory is a defect.
- Where the workflow says "select the recommended default", run the open items through the
  ladder (§3) and log them in the Interview Log (**MANDATORY — read
  `references/log-formats.md` before writing it**).
- **Edge Coverage is engine output, never hand-written.** Write the requirements, then
  `python3 "$S/edge_floor.py" floor <SPEC>`; resolve each floor row (✅ covered / 🧪 backstop),
  mark any row you add with `(added …)` in the Resolution cell, and leave every `unclassified`
  row `⚠ UNRESOLVED`. Gate with `python3 "$S/edge_floor.py" check <SPEC>` (exit 1 = drift).
  Amending a requirement's text later changes its floor: re-run `check` after every amendment.
  Exit 2 means node or the engine is missing — fail closed: stop the spec step for this
  phase, never write the table by hand.
- The workflow commits the SPEC itself.

## 2. Per phase: discuss

The **auto path** runs assumptions mode: read and execute `<workflows>/discuss-phase-assumptions.md`
with argument `N` — **never** pass `--assumptions` (routes to `list-phase-assumptions.md`, which
writes no files) and **never** pass `--auto` (it chains into plan-phase and auto-accepts Unclear
items). The **interactive path** runs `<workflows>/discuss-phase.md` instead, with the user
answering its prompts.

**Rules that hold in both paths:**
- Skip the workflow's `auto_advance` step regardless of config — the skill never plans or
  executes, and automatic mode can dispatch plan-phase there without changing the user's
  settings.
- One commit per phase: write CONTEXT + DISCUSSION-LOG (**MANDATORY — read
  `references/log-formats.md` first**), then
  `gsd_run query commit "docs(NN): ..." --files <CONTEXT> <LOG> <every cross-phase amended
  file>`. This commit **replaces** the workflow's `git_commit` step (skip it), and the single
  end-of-range `state.record-session` **replaces** its per-phase `update_state` step (skip per
  phase, like `auto_advance`) — never commit or update STATE.md twice per phase.
- The ladder and analyzer per path: in the interactive path the user answers the workflow's
  prompts, and the ladder only screens the items the user asks it to screen (§3); in the auto
  path the ladder runs on every open item, per the rules below.

**Auto path only** — encode the user's `--analyze --all --batch` intent yourself:
every analyzer area in one pass; 2–3 alternatives per Likely/Unclear item with best and easy
marked; all the phase's questions in one ladder run (the client still sends Laya one item per
call). Pre-answer the workflow's prompts by rule (in the interactive path these are only the
recommended defaults you offer the user):
- existing CONTEXT → "Update it" (in place, additively — locked decisions stay verbatim);
- existing plans → "Continue and replan after";
- todos → fold those scoring ≥ 0.4 (gsd-core's workflow constant for a todo worth folding);
- assumptions → "Yes, proceed" only after every Unclear item went through the ladder.

**Spawn the analyzer** (`gsd-assumptions-analyzer`) through the host's subagent mechanism when
`init.phase-op` reports it installed; its output also carries the resolved analyzer model
value — omit `model` when that is `inherit` or empty. No subagent support → run the brief
inline and say so in the DISCUSSION-LOG.

**MANDATORY — read `references/analyzer-brief.md` before spawning; fill every placeholder.**
The analyzer returns "Jev question" lines; it never calls jev, even when `jev-fast-decision`
is wired into it (SKL-04). The ladder, consent and the answer log belong to the orchestrator
(this skill), through the shared client. In the interactive path the analyzer runs
only when the user asks for it; otherwise its prompts come straight from the user.

After the range: `gsd_run query state.record-session --stopped-at "..."
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
alone (`invalid_input` + reason) — fix and resubmit. A repeated `id` is `duplicate_id`; an
`id` starting with `#` is `reserved_id` (that prefix keys rejections).

The ladder is **one client call per step that has open items** (spec and discuss ladder
separately, §1–§2), plus an optional `--second-opinion` run for contested items: decide.py
validates the items and maps the
client's per-item rung trail onto one column per table backend, each
`{choice, top, fallback, model}`, `{error}` or null = not called, plus `decided_by` (the
last confident rung, else `own_reasoning`); each column's `top` is its winning probability.
What a forced `fallback: true` column does in "Which answer wins", and when a high local
answer gets `--second-opinion`, is defined once in `references/decision-table.md` — follow it
there.
A detect row with `key_check: unverified` is reachable, not a proven key.

- Describe options **neutrally**. Labelling one "best" or "easy" just echoes your framing back.
- A high local answer contradicting verified evidence or a locked decision gets
  `--second-opinion` (decision-table row 3; worked cases in `references/worked-examples.md`).
- Laya is not deterministic (one real run: the same item scored 0.74 then 0.67 (fb)); never
  treat a single Laya number as stable.
- Every answering column low (`fallback: true`, the client's `needs_fallback`) or errored → **own reasoning** against the SPEC, earlier CONTEXT
  files and the live facts. Log it, and ledger it when it blocks nothing.

## 4. Ledger and stop rule

Keep the ledger in a run file under the system temp dir (`tempfile.gettempdir()`), appended as
you go, and mark each ledgered row in the committed DISCUSSION-LOG ("own reasoning … ledger").
"Blocking" = another decision **in this run** depends on it; an item that only blocks later
planning is ledgered with `Blocks: <what>`. User-owned preconditions (land or shelve a branch)
go on the ledger. An item that would change or contradict a **user-locked** decision is
decided provisionally and flagged "needs confirmation" — never a silent override; an answer
that agrees with the locked decision is not flagged (decision-table row 1, same rule). The ledger is a
temp file; after a context reset, resumption relies on the "own reasoning … ledger" marks in
the committed DISCUSSION-LOGs.

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
handed to J's discuss. Example pattern: a config default discovered in a later phase's spec
amends the earlier phases whose requirements assumed the opposite.

## 7. Pacing

A phase's analyzer must never start before that phase's spec step has finished: its Locked WHAT
input is this phase's committed SPEC, so the SPEC must exist and be current first. Where the
host has background subagents with completion notices, start phase K's analyzer while you write
phase K's CONTEXT (its SPEC already committed) when coupling is low; name any coupling in its
brief. Never use a background result before its notification arrives. Elsewhere, run phases
strictly in sequence (flag that gap in the log).

## NEVER

- **NEVER pass `--assumptions` to the discuss command** — it routes to a listing workflow that
  writes nothing; the run looks complete and produces no CONTEXT.
- **NEVER pass `--auto` to discuss in assumptions mode** — it auto-advances into plan-phase
  and accepts the analyzer's default for Unclear items, bypassing the ladder and the log
  (the interactive path runs standard discuss mode instead).
- **NEVER hand-batch items into one Laya question** — one item's context changes another's answer.
- **NEVER treat a Laya, TypeSafe or OpenCode Zen answer as the decision** — log it as
  advisory; the decision column is yours, with its reason.
- **NEVER send code, diffs, file contents, config values or secrets** — summaries only;
  `decide.py` rejects fences and key shapes, but it is defense in depth, not a guarantee.
- **NEVER flip `workflow.discuss_mode`, `mode` or `workflow.mvp_mode` to pick a run path or
  get assumptions mode** — plan-phase and progress read them too, and a crash leaves them
  flipped.
- **NEVER regenerate an existing CONTEXT wholesale** — user-locked decisions from an earlier
  interactive discuss are lost silently; amend in place.
- **NEVER hand-write the Edge Coverage floor** — the engine's floor depends on the exact
  requirement text; prose-derived rows drift from the engine's output.
- **NEVER print or log a key** — check keys by name; `decide.py detect` shows source labels.

## Host gaps (flagged, not hidden)

- Subagent spawn and background completion notices are host features. Without them the brief
  runs inline (more context used) and pacing (§7) does not apply.
- `init.phase-op` reports `agents_installed` / `missing_agents` / `agent_runtime`; trust it
  over assumptions about the host.

## References — load only at the trigger

- `references/decision-table.md` — before the first ladder call.
- `references/analyzer-brief.md` — before spawning (or running inline) the analyzer.
- `references/log-formats.md` — before writing a SPEC Interview Log, CONTEXT, DISCUSSION-LOG,
  an amendment, or the ledger.
- `references/worked-examples.md` — only when a case is unclear: an override, a second
  opinion, a both-low item, an out-of-scope fix.

Do NOT load the references for a phase the automatic proposal skipped because its SPEC
and CONTEXT are already current. An explicit range or list still runs that phase.
