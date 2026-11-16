---
name: ai-kit-gsd-spec-discuss
description: "Chains GSD /gsd-spec-phase then /gsd-discuss-phase over a range of phases (SPEC.md, then CONTEXT.md + DISCUSSION-LOG.md). Use when asked to spec and discuss several GSD phases unattended or in one run (\"spec/discuss phases 17-24\", \"run spec-phase and discuss-phase for every undiscussed phase\", \"--analyze --all --batch --assumptions\"), or to use jev for GSD planning decisions. Settles gray areas with advisory answers from the `jev-fast-decision` skill, with logged decisions, a deferred ledger, cross-phase amendments and a best-over-easy design rule. Two run modes, picked once: auto or interactive. Works without `jev-fast-decision` installed. Not for plan-phase or execute-phase."
---

# ai-kit-gsd-spec-discuss

Takes phases N..M through **spec** (the WHAT, `NN-SPEC.md`) then **discuss**
(the HOW, `NN-CONTEXT.md` + `NN-DISCUSSION-LOG.md`), one phase at a time, deciding gray areas
yourself with advisory help. It never plans or executes. Gray areas get an advisory answer from the
`jev-fast-decision` skill when it is installed; your own reasoning decides (§3). Two run modes,
picked once in §0:
**auto** (spec `--auto`, discuss assumptions-mode) and **interactive** (spec without `--auto`,
discuss in standard mode with `--analyze --all --batch`, the user answering).

**The mindset:** you are the decider. jev's answers are cheap typed screens, not verdicts.
Your own reasoning against verified evidence is the final word and the most important input:
jev is often low-confidence, and sometimes confidently wrong. Stop the run only for a decision
that blocks other decisions *and* that nothing settles with high confidence; everything else is
decided provisionally and shown at the end.

## 0. Set up once per run

1. **Resolve this skill's scripts dir** (`S`), the fold skill's `FOLD_PY` and the project root
   `REPO` once, and use the printed literals:
   ```bash
   HERE="$(dirname "<absolute path of THIS SKILL.md>")"
   ROOTS=("$(dirname "$HERE")" "${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills" "$HOME/.agents/skills" \
          "${XDG_CONFIG_HOME:-$HOME/.config}/opencode/skills" "${CURSOR_CONFIG_DIR:-$HOME/.cursor}/skills" \
          "${PI_CODING_AGENT_DIR:-$HOME/.pi/agent}/skills")
   for d in "$HERE" "${ROOTS[@]}"; do
     for c in "$d/scripts" "$d/ai-kit-gsd-spec-discuss/scripts"; do
       [ -f "$c/phase_range.py" ] && { printf 'S=%s\n' "$c"; break 2; }; done; done
   FOLD_PY=""; for d in "${ROOTS[@]}"; do
     [ -f "$d/ai-kit-commit-fold/scripts/fold.py" ] && { FOLD_PY="$d/ai-kit-commit-fold/scripts/fold.py"; break; }; done
   GOAL_MD=""; for d in "${ROOTS[@]}"; do
     [ -f "$d/ai-kit-spec-goal-prompt/SKILL.md" ] && { GOAL_MD="$d/ai-kit-spec-goal-prompt/SKILL.md"; break; }; done
   printf 'FOLD_PY=%s\nGOAL_MD=%s\nREPO=%s\n' "$FOLD_PY" "$GOAL_MD" "$(git rev-parse --show-toplevel)"
   ```
   If it prints no `S=` line, **stop the run** (fail closed, like `edge_floor` exit 2). An empty
   `FOLD_PY` means the fold skill is not installed. An empty `GOAL_MD` means
   `ai-kit-spec-goal-prompt` is not installed.
2. **Resolve gsd-core** with its standard resolver (`references/gsd-run-resolver.md` inside
   the gsd-core install; it finds the repo's own `.claude/gsd-core/bin/gsd-tools.cjs` before any
   user-level install). The workflows dir is `<dir of gsd-tools.cjs>/../workflows/`. No
   gsd-core → stop with the resolver's own install hint. Print the resolved command
   (`node <path>/gsd-tools.cjs`, or the `gsd_run` executable itself on the resolver's PATH-shim
   branch) and use that literal in every later call, like `S`: shell variables and the
   `gsd_run` alias survive across calls only on hosts with `CLAUDE_ENV_FILE`. Later steps call
   it "the resolved GSD command". When the user passes `--ws <name>`, append `--ws=<name>` to
   every gsd-tools call (`query …` and `init …`), including the calls inside `spec-phase.md`
   (it does not parse `--ws` itself), and pass `--ws <name>` to the discuss workflows. A
   workstream can also be active without the flag (`GSD_WORKSTREAM` or the session pointer),
   so take the paths from gsd-core, never from a fixed `.planning/`: the first phase's
   `init.phase-op` gives `state_path` and `phase_dir`; pass the parent of `phase_dir` to
   `phase_range.py --phases-root`, and commit the `state_path` file.
3. **Decision help (optional):** ask the `jev-fast-decision` skill and follow its SKILL.md for
   every gray area; it covers how to call it and any approval it needs. Not installed, an
   error, `needs_fallback` or no answer → your own reasoning decides (§3).
4. **Pick the range.** Get the roadmap first, for every case: the resolved GSD command
   `query roadmap analyze > <tmp>.json`. Explicit `--from N --to M` or a list wins:
   `python3 "$S/phase_range.py" --roadmap <tmp>.json --from N --to M` (or `--list a,b`).
   Otherwise `python3 "$S/phase_range.py" --roadmap <tmp>.json` proposes phases with no
   CONTEXT or a SPEC newer than its CONTEXT (git commit time), each with its reason. A "SPEC
   newer" reason can be a false positive: a later phase's dated cross-phase amendment also
   touches the SPEC. Check `git log -1 -- <SPEC>`; if that commit only appended an amendment the CONTEXT already
   reflects, drop the phase from the proposal and say why. A phase the script lists as
   skipped (executed or complete) under an explicit request runs only after the user
   confirms it.
5. **Ask one question about the range**, only when needed (the run-mode ask in step 7 is
   separate): confirm or trim the proposed range.
6. **Read MVP mode once, per phase:** the resolved GSD command `query phase.mvp-mode <N>`
   (`active` true → MVP branch). This one query is the single source for both the quality
   rule (§5) and the run-mode recommendation in step 7 — do not read `workflow.mvp_mode` a
   second way. If the per-phase query errors (an unresolvable phase), fall back to the
   resolved GSD command `query config-get workflow.mvp_mode --default false --raw`. Bare
   `config-get` exits "Key not found" when the key is unset.
7. **Pick the run mode** (§1–§2). With the skill's `--auto` flag: auto path. Without it, derive the recommendation first: read the project mode — the resolved GSD command `query config-get mode`; a "Key not found" exit means the default (`interactive`) — and recommend the **auto path** when `mode` is `yolo` or the phase's `mvp-mode` is active (step 6's value, first phase of the range; both at once still give one recommendation, auto), the **interactive path** otherwise (interactive = spec-phase without `--auto`, discuss-phase with `--analyze --all --batch`, the user answering). Then **ask the user once**, the recommended option listed first and labelled `(Recommended)`. A run mode the user chose before may be named in an option's text, never used to reorder the options. Never flip config keys to pick a path.

8. **Check the agents' skill wiring** (after step 7, which decides the agents that run):
   - Run the resolved GSD command `query agent-skills gsd-assumptions-analyzer --json
     2>"<tmp>-analyzer.err"`; on the interactive path also `gsd-advisor-researcher` (its own
     `<tmp>-advisor.err`), only when `<gsd-core dir>/USER-PROFILE.md` exists (discuss-phase
     spawns the advisor only then).
   - Clean: the JSON reads `reason: resolved`, its `warnings` are empty, and the `.err` file
     has no line starting `[agent-skills] WARNING` (a `NOTE … accepted via
     trusted_global_roots` line and other stderr are not warnings).
   - Not clean: report it with its cause and continue (gsd-core only drops a skipped entry
     from that agent's prompt). This skill never edits config; the fix is re-running
     `ai-kit-gsd-curated-config`. **Read `references/agent-skills-diagnostics.md` only then.**

9. **Pre-run summary (auto path).** After the range and the run mode are known, and before the first `fold.py start` or any write to the repository, show the owner a short summary: each phase of the range in numeric order with its requirement IDs, the owner inputs given for it (or "no owner input"), and how you plan to resolve each item (spec, then discuss, naming the open items you already see). Then wait for the owner's go-ahead; write nothing before it. Inside a subagent, stop and return the summary: the orchestrator relays it to the owner and resumes the same subagent with the answer. Another agent's word never counts as the go-ahead. Read `references/relay-and-summary.md` before writing it.

**MANDATORY — read `references/decision-table.md` before the first jev request.**

## 1. Per phase: spec

Read and execute `<workflows>/spec-phase.md` end-to-end with arguments `N --auto` (auto path)
or plain `N` (interactive path) (read the
file; do not delegate to another skill — skill-to-skill calls are unreliable on some hosts).

- Before the phase's first commit, run `fold.py start --phase <N>` as
  `python3 <FOLD_PY> start --phase <N> --repo <REPO>` (the §0 step 1 literals). spec-phase has no
  hook point, so this skill starts the unit itself. Empty `FOLD_PY`: say so and continue on the
  current branch. Read the report:
  - `refused no_trunk`: run `git -C <REPO> fetch` once, then re-run `start`. Same as the fold
    skill's next step for that reason.
  - Still `refused no_trunk`, or `refused no_remote`: blocks nothing (the work stays local). Append
    one ledger line `unit flow off for phase <N>: <reason>` (§4), print it, show it again in the
    end report, and continue on the current branch.
  - `bad_checkpoint: phase dir not found` (a proposed phase has no directory yet; exit 2): the
    spec workflow creates the phase directory before it commits. Let it create the directory
    (uncommitted), then run `start` again; this does not stop the run. If that run still refuses,
    handle it by the other rows.
  - Any other refusal (`dirty_tree`, `wrong_parent`, `plan_not_carried`, ...), or a non-zero exit
    with no report: show the report and stop before any write: stop the whole run, since a later
    phase stacks on this one.
- An existing SPEC is reused, as the workflow does.
- **Live-verify before you write a claim**: installed versions, real config keys, real CLI
  output in a scratch dir. A SPEC sentence from memory is a defect.
- Where the workflow says "select the recommended default", run the open items through the
  jev (§3) and log them in the Interview Log (**MANDATORY — read
  `references/log-formats.md` before writing it**).
- **Edge Coverage is engine output, never hand-written.** Write the requirements, then
  `python3 "$S/edge_floor.py" floor <SPEC>`; resolve each floor row (✅ covered / 🧪 backstop),
  mark any row you add with `(added …)` in the Resolution cell, and leave every `unclassified`
  row `⚠ UNRESOLVED`. Gate with `python3 "$S/edge_floor.py" check <SPEC>` (exit 1 = drift).
  Amending a requirement's text later changes its floor: re-run `check` after every amendment.
  Exit 2 means node or the engine is missing — fail closed: stop the spec step for this
  phase, never write the table by hand.
- The workflow commits the SPEC itself. When `commit_docs` is false its commit returns
  `skipped`: stop and say so — the discuss step needs a committed SPEC — and never change
  `commit_docs` yourself.

## 2. Per phase: discuss

The **auto path** runs assumptions mode: read and execute `<workflows>/discuss-phase-assumptions.md`
with argument `N` — **never** pass `--assumptions` (routes to `list-phase-assumptions.md`, which
writes no files) and **never** pass `--auto` (it chains into plan-phase and auto-accepts Unclear
items). The **interactive path** runs `<workflows>/discuss-phase.md` instead, with arguments
`N --analyze --all --batch` (every gray area, 2–5 questions per turn) and with the user answering its prompts.

Where the workflow shows a trade-off table before a group, relay it as one header per option with pros and cons bullets, never a table. Start each interactive decision question with one line per named item saying what it is and who uses it (a subcommand, module, file or key the question names).

**Rules that hold in both paths:**
- Skip the workflow's `auto_advance` step regardless of config — the skill never plans or
  executes, and automatic mode can dispatch plan-phase there without changing the user's
  settings.
- One discuss commit per phase (spec-phase's own SPEC commit is the phase's spec-step commit, so a phase has two commits: the SPEC, then this one): write CONTEXT + DISCUSSION-LOG (**MANDATORY — read
  `references/log-formats.md` first**), then
  the resolved GSD command `query commit "docs(NN): ..." --files <CONTEXT> <LOG> <every cross-phase amended
  file>`. This commit **replaces** the workflow's `git_commit` step (skip it), and the single
  end-of-range `state.record-session` **replaces** its per-phase `update_state` step (skip per
  phase, like `auto_advance`) — never commit or update STATE.md twice per phase.
- jev and analyzer per path: in the interactive path the user answers the workflow's
  prompts, and jev only screens the items the user asks it to screen (§3); in the auto
  path jev is asked about every open item, per the rules below.

**Auto path only** — encode the user's `--analyze --all --batch` intent yourself:
every analyzer area in one pass; 2–3 alternatives per Likely/Unclear item with best and easy
marked; all the phase's questions in one jev request (its SKILL.md says how items are sent).
Pre-answer the workflow's prompts by rule (in the interactive path these are only the
recommended defaults you offer the user):
- existing CONTEXT → "Update it" (in place, additively — locked decisions stay verbatim);
- existing plans → "Continue and replan after";
- todos → fold those scoring ≥ 0.4 (gsd-core's workflow constant for a todo worth folding);
- assumptions → "Yes, proceed" only after every Unclear item got a jev answer or your own reasoning.

**Spawn the analyzer** (`gsd-assumptions-analyzer`) through the host's subagent mechanism when
the workflow's init output (`init.discuss-phase-assumptions`, like `init.phase-op`) reports it
installed. Resolve the analyzer model separately, the way
`discuss-phase-assumptions.md` does — `init.phase-op` does not carry it:
the resolved GSD command `query resolve-model gsd-assumptions-analyzer --raw`. Omit `model`
when that value is `inherit` or empty. No subagent support → run the brief inline and say so
in the DISCUSSION-LOG.

**MANDATORY — read `references/analyzer-brief.md` before spawning; fill every placeholder.**
The analyzer returns "Jev question" lines. `gsd-assumptions-analyzer` and
`gsd-advisor-researcher` never call jev, even when `jev-fast-decision` is wired into them.
Asking jev and the log belong to the orchestrator (this skill).
In the interactive path, when discuss-phase spawns `gsd-advisor-researcher`, the orchestrator
adds this one sentence to the advisor's spawn prompt: "Do NOT call jev-fast-decision yourself,
even when it is among your agent skills." In the interactive path the analyzer runs only when
the user asks for it; otherwise the user answers the workflow's prompts directly.

**Interactive relay (one subagent per phase).** On the interactive path a phase may run in its own subagent. The subagent verifies facts, drafts, and spawns the analyzer as a real subagent where the host nests subagents: Claude Code nests (a subagent may spawn subagents, three layers by default); opencode's default nesting depth is one and pi has no built-in subagents, so there the subagent runs the analyzer inline and says so. A subagent cannot ask the user: it stops and returns the owner's questions in batches of 2 to 5 for one phase (recommended option first, trade-offs as one header per option with pros and cons bullets, never a table). The orchestrator asks the owner and resumes the same subagent with the answers (Claude Code: `SendMessage` to the subagent's id or name; opencode documents continuing a child by its `sessionID`, unverified here). Where the host cannot resume a subagent, run the phase inline in the orchestrator and say so; never start a second subagent that re-derives the first one's work. A phase with no owner question runs to its commit without a stop. Read `references/relay-and-summary.md` before the first relay.

After the range: the resolved GSD command `query state.record-session --stopped-at "..."
--resume-file <last CONTEXT>` and a separate `docs(state)` commit of the `state_path` file
(§0 step 2). An early stop (a blocking question, §4, or any other stop after the unit flow started) runs the same `state.record-session` with the stop reason in `--stopped-at` (`--resume-file` only when a CONTEXT was written), with its own `docs(state)` commit, even when no phase was committed. A `start` refusal that stops the run (§1) stops before any write: no `state.record-session` and no commit; show the report and the stop reason instead.

**Hand off to goal-prompt (auto path only).** After the range's `docs(state)` commit, prepare the autonomous-run prompt for the discussed range. Read the SKILL.md at the §0 step 1 `GOAL_MD` literal and follow it (no skill-to-skill call, as in §1). Supply its answers instead of its four questions: the work set is the discussed phases in numeric order, the target host is the current host, `native_execution` comes from this run's decisions (default false), mockups are none, and its optional owner run-rule fields are set only where a source states them. Commit the rendered file in its own `docs` commit, then end the run; stop earlier only on a blocker. Empty `GOAL_MD`: say goal-prompt is not installed and stop. A range in which no phase was discussed prepares no prompt and says so.

## 3. Asking jev

Ask jev with one item per gray area, shaped as jev's SKILL.md documents (a `choice` with neutral
options, a `noul` or a `score`), summaries only. Each step that has open items (spec and discuss
separately, §1–§2) is one jev request. Ask the `jev-fast-decision` skill and follow its SKILL.md;
it covers the item shape, how the request is sent, the answer format and any approval it needs.

- A confident answer is advisory evidence for the row that decides (`references/decision-table.md`),
  logged with its confidence. It is never the decision on its own.
- `needs_fallback`, an error or no answer → **own reasoning** against the SPEC, earlier CONTEXT
  files and the live facts. Log it, and ledger it when it blocks nothing.
- Describe options **neutrally**. Labelling one "best" or "easy" just echoes your framing back.
- A confident answer that contradicts verified evidence or a locked decision gets one second
  opinion (jev's SKILL.md says how; decision-table row 3; worked cases in
  `references/worked-examples.md`).
- jev is not deterministic (the same item can score differently on a re-ask). Never treat a
  single number as stable.

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
host has background subagents with completion notices, start phase K+1's analyzer while you write
phase K's CONTEXT (phase K+1's SPEC already committed) when coupling is low; name any coupling in its
brief. Phase K's own analyzer never runs while phase K's CONTEXT is being written: that CONTEXT is built from its result. Never use a background result before its notification arrives. Elsewhere, run phases
strictly in sequence (flag that gap in the log).

## NEVER

- **NEVER pass `--assumptions` to the discuss command** — it routes to a listing workflow that
  writes nothing; the run looks complete and produces no CONTEXT.
- **NEVER pass `--auto` to discuss in assumptions mode** — it auto-advances into plan-phase
  and accepts the analyzer's default for Unclear items, bypassing jev and the log
  (the interactive path runs standard discuss mode with `--analyze --all --batch` instead).
- **NEVER merge several gray areas into one jev item** — one item's context changes another's answer.
- **NEVER treat a jev answer as the decision** — log it as advisory; the decision is yours,
  with its reason.
- **NEVER send code, diffs, file contents, config values or secrets to jev** — summaries only,
  never a key, config value or file content in a jev item.
- **NEVER flip `workflow.discuss_mode`, `mode` or `workflow.mvp_mode` to pick a run path or
  get assumptions mode** — plan-phase and progress read them too, and a crash leaves them
  flipped.
- **NEVER regenerate an existing CONTEXT wholesale** — user-locked decisions from an earlier
  interactive discuss are lost silently; amend in place.
- **NEVER hand-write the Edge Coverage floor** — the engine's floor depends on the exact
  requirement text; prose-derived rows drift from the engine's output.
- **NEVER print or log a key** — any key check is the `jev-fast-decision` skill's job.

## Host gaps (flagged, not hidden)

- Subagent spawn and background completion notices are host features. Without them the brief
  runs inline (more context used) and pacing (§7) does not apply.
- `init.phase-op` reports `agents_installed` / `missing_agents` / `agent_runtime`; trust it
  over assumptions about the host.

## References — load only at the trigger

- `references/decision-table.md` — before the first jev request.
- `references/analyzer-brief.md` — before spawning (or running inline) the analyzer.
- `references/log-formats.md` — before writing a SPEC Interview Log, CONTEXT, DISCUSSION-LOG,
  an amendment, or the ledger.
- `references/relay-and-summary.md` — before the auto path's pre-run summary or the first interactive relay.
- `references/agent-skills-diagnostics.md` — only when §0 step 8 finds an agent that is not clean.
- `references/worked-examples.md` — only when a case is unclear: an override, a second
  opinion, a both-low item, an out-of-scope fix.

Do NOT load the references for a phase the automatic proposal skipped because its SPEC
and CONTEXT are already current. An explicit range or list still runs that phase.

## Evidence

- One real run scored the same item 0.74, then 0.67.
