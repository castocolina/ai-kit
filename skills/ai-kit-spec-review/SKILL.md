---
name: ai-kit-spec-review
description: Use when a design, spec, requirements, or plan document needs review-and-fix before the next step. Framework-aware across superpowers, GSD, OpenSpec, Spec Kit, Kiro, BMAD, and generic docs — orchestrates a reviewer and routes fixes via the appropriate handler (native framework skill, slash command, or direct-edit fixer), with optional cross-AI reviewer dispatch via `--cross-ai`/`--no-cross-ai`. Respects worktrees, scopes to lifecycle stage, loops until approved or iteration cap. Triggered by "ai-kit-spec-review", "review my spec/plan", naming one of these frameworks alongside a spec/plan/design review, or passing document path(s).
---

## Your Task

You are the orchestrator running as the `ai-kit-spec-review` skill (invocable via `/ai-kit-spec-review`, by asking to review a spec/plan, or programmatically). You were given one or more document paths. Your job: drive a review-and-fix loop using clean-context subagents (a reviewer, and a rewrite handler chosen by framework), surface the outcome to the user, and never edit the document yourself.

## Inputs

- **Document path(s):** taken from the user's invocation arguments. If absent (e.g. "review my specs"), ask the user for absolute paths and wait — you may list the candidate documents you can see to make the answer easy, but review nothing until the user names the paths.
- **Codebase root:** the worktree that contains the document — resolved in Step 0.1, **not** assumed to be your CWD. With worktrees, the spec/plan and the code it grounds against live in a checkout that is often *not* where you were invoked.
- **Flags (optional, parsed from the same invocation arguments):**
  `--cross-ai` (default) or `--no-cross-ai` — whether Step 0.7 attempts
  cross-AI reviewer resolution at all. `--source-vendor=<vendor>` (default
  `anthropic`) — the document's authoring vendor, used by Step 0.7's ladder
  walk to prefer an independent perspective. Defaults to `anthropic` because
  the orchestrator has no way to introspect its own model's vendor; pass the
  real vendor explicitly when this host's model comes from another vendor.
  A Claude Code session is one example of an `anthropic` author, not the
  rule. This is a **vendor** (`anthropic`, `openai`, `xai`, ...) matching the
  `vendor` field in `review-spec.toml` reviewer entries, not a model id.

## Step 0 — Persist before dispatch (ALWAYS)

Before any subagent dispatch, every document under review **must exist on disk** at a stable path. Subagents run in isolated contexts and read inputs via the `Read` tool; an in-memory document does not survive the dispatch boundary, and the next iteration would re-read the unfixed file and contradict itself.

| Caller state | Action |
|---|---|
| User passed real file path(s) that exist on disk | Continue to Step 1. |
| Doc was just produced in this session by `brainstorming` / `writing-plans` and SAVED to a path | Confirm the file exists on disk via a `Read` call before Step 1. Do not assume. |
| Doc only exists in chat (in-memory, not yet persisted) | STOP. Tell the user: "The document is not on disk. To run `/ai-kit-spec-review` I need to persist it first to a stable path." Offer a default location appropriate to the framework in use (superpowers → `docs/superpowers/specs/YYYY-MM-DD-<topic>-design.md` or `.../plans/YYYY-MM-DD-<feature>.md`; Spec Kit → `specs/<NNN>-<feature>/spec.md` or `plan.md`; OpenSpec → `openspec/changes/<id>/proposal.md` or `tasks.md`; otherwise ask). After the user confirms, write the document verbatim to the chosen path, then continue. |
| Path was given but file does not exist | STOP. Surface a Failure: `Path does not exist: <path>. Persist the document first.` |

Do not paraphrase the document into the subagent prompt as a workaround — that defeats the clean-context guarantee. The subagent must `Read` the file from disk.

## Step 0.1 — Resolve the codebase root (worktree-aware)

Plans and designs are routinely written/executed in an **isolated worktree** (superpowers
`using-git-worktrees` puts them under `.worktrees/<name>/`, `worktrees/`, or a sibling `../<name>/`),
while you may have been invoked from the main checkout. A clean-context subagent has no way to know
this — if you hand it the wrong root, its codebase-grounding checks read the *main* branch's files
instead of the worktree's, producing phantom "X doesn't exist / contradicts the code" findings (or
silently passing real ones). The root **must be the worktree that owns the document**, derived from
the document's own location:

1. **Derive from the doc, not CWD.** For the first document path, take its directory and run
   `git -C "<doc-dir>" rev-parse --show-toplevel`. That toplevel is the authoritative codebase root —
   it resolves to whichever worktree the file physically lives in. Use it as `<CODEBASE_ROOT>`.
2. **If that fails or feels ambiguous** (doc outside any repo, multiple docs in different roots, or
   you're unsure which checkout is "live"), run `git -C "<doc-dir>" worktree list` and inspect the
   output: each line is `<path>  <sha>  [<branch>]`. Match the document's path prefix to a worktree
   `<path>`; that path is the root. If several docs map to *different* worktrees, that's a red flag —
   stop and ask the user which checkout to ground against (do not silently pick one).
3. **Pass the resolved worktree root** as `<CODEBASE_ROOT>` to **both** the reviewer and the fixer.
   Never default to your CWD or the main repo root when the document lives in a worktree.

**The plan's declared paths win — do not normalize them to convention.** A plan may
deliberately declare a worktree/target outside the ambient convention (e.g. a cross-repo
execution that creates `../.worktrees/target-repo/<wt>` even though `CLAUDE.md` /
`CLAUDE.local.md` recommend `.claude/worktrees/`). For *this* review, authority runs:
**(1) the explicit paths in the plan/spec under review → (2) `CLAUDE.local.md` → `CLAUDE.md`
→ (3) Claude's default recommendation.** The reviewer grounds against the paths the plan
declares, AS DECLARED; it must not flag them merely for diverging from convention, and must
not "correct" them toward `.claude/worktrees`. Carry this precedence into the reviewer prompt.

**Cross-repo plans have more than one root.** If the document references files in a second
repo/worktree (a target repo it acts on), don't force a single `--show-toplevel`. Capture each
**declared** root from the plan, label which references belong to which root, and pass the set
so the reviewer grounds each claim against the right checkout instead of chasing references
across both. If the roots are unclear, run `git worktree list` in each repo and ask once.

Record the result as `CODEBASE_ROOT` (one root, or a labeled set for cross-repo plans).

## Step 0.5 — Detect framework, resolve its profile, classify archetype

Before classifying, ask yourself: what stage-shaped artifact is this, really — an early why/what (intent), a testable requirement, a design, or a sequenced plan? Archetype is a ceiling on what the reviewer is allowed to demand; guessing "plan" for what is actually an intent doc invites findings the document was never meant to satisfy.

The reviewer/fixer are clean-context subagents — give them the framework's rules as a **file
path**, not prose. You (orchestrator, in the user's session, with web access) do the detection
and any research; they just `Read` the profile. Three sub-steps:

First resolve `SEEDS_DIR` and `CACHE_DIR` to absolute paths (see Constants) — every profile path
below and the `FRAMEWORK_PROFILE_PATH` you pass to subagents must be absolute, never a bare
relative `references/frameworks/…`.

**A. Detect the framework.** Match the document path + nearby project markers against the
`detection_signals` of the known profiles (bundled seeds in `SEEDS_DIR`). Conversation signal
wins: if the user just used a framework's skill (superpowers `brainstorming`/`writing-plans` →
`superpowers`), use it. If markers are ambiguous, ask once.

**B. Resolve the profile** (an **absolute** path on disk), in order:
1. `CACHE_DIR/<id>.md` if it exists and isn't stale → use it.
2. else the bundled seed `SEEDS_DIR/<id>.md` → use it.
3. else **unknown framework** → research it (web: official repo/docs), write a new profile to
   `CACHE_DIR/<id>.md` following `SEEDS_DIR/SCHEMA.md` (frontmatter + conventions), set
   `last_updated` to today, then use it. Tell the user one line: "Learned framework `<id>`;
   cached its profile."

Staleness: a cached profile for a known-to-drift framework (`bmad`, `gsd`) older than ~180 days
is a refresh candidate — you may re-research and rewrite the **cache** copy (bump
`last_updated`). Never overwrite a bundled seed in place. Record the resolved path as
`FRAMEWORK_PROFILE_PATH` (or `none` if you genuinely can't resolve a framework, e.g. generic
`docs/rfcs/` — the reviewer then uses generic checklists).

**C. Classify the archetype** from the resolved profile's `doc_types` (glob → archetype).
Conversation signal still wins (`brainstorming` → a fused `intent+requirements+design` design
doc; `writing-plans` → `plan`). A `fused` doc yields several archetypes — pass them all. If the
path matches no `doc_types` glob, fall back to content shape (see the reviewer skill's archetype
table) or ask. Record as `ARCHETYPE` (one or more of: `intent`, `requirements`, `design`, `plan`).

**Low-confidence detection → generic.** If the framework stays ambiguous and the user cannot
disambiguate, set `FRAMEWORK_PROFILE_PATH = none` and route every archetype through the generic
`ai-kit-spec-review-fixer` fixer (Step 3a). State this in the final Surface message ("Framework
ambiguous — used the generic fixer.") so routing stays transparent.

Pass both `FRAMEWORK_PROFILE_PATH` and `ARCHETYPE` to the reviewer and fixer below.

## Step 0.6 — Scope the review to the project's lifecycle stage

Frameworks have stages (GSD: context/discussion → requirements → roadmap → research → plan →
status; OpenSpec: proposal → design → specs → tasks; superpowers: design → plan). Reviewing an
early-stage document as if it were a finished plan is the most common failure — e.g. invoked in
GSD with only `PROJECT.md`/CONTEXT present, the reviewer demands tasks and exact files that the
*intent* stage does not have yet. Don't. Resolve scope before dispatch:

1. **See what exists.** Glob the profile's `doc_types` against the project root. The
   furthest-along present archetype (per the profile's `lifecycle_order`) is the **current
   stage**.
2. **Review each existing document at its own archetype** — the `ARCHETYPE` from Step 0.5 is
   per-document and is the ceiling. Never escalate an upstream doc to a downstream checklist:
   a bare `intent`/CONTEXT is judged on why/what clarity and scope, **not** on missing tasks,
   files, or interfaces. (The reviewer skill enforces this too; set the right `ARCHETYPE` so it
   never has to guess.)
3. **Missing required prerequisites are gaps, not defects.** A `required: true` doc-type absent
   at or before the current stage → note it to the user as a prerequisite to produce next, not
   as a finding inside an existing document.
4. **Insufficient-info guard.** If the user asked to review an artifact a later stage hasn't
   produced (e.g. "review the plan" but only `intent` exists), STOP and surface:
   `Only <existing docs> exist; the project is at the <stage> stage. There is no <requested
   archetype> to review yet. I can review <existing> as <archetype>, or wait until <next
   stage> is produced.` Do not invent a deeper review or ask for downstream detail.

Review exactly the path(s) the user named (Inputs) at their archetypes — do not pull in
downstream scope — and list any prerequisite gaps.

5. **Supply complementary grounding to the reviewer.** A document under review is usually
   derived from upstream context the reviewer should read but NOT review. When reviewing a
   `plan` (or `design`), gather the framework's sibling context/research for that same unit of
   work and pass them as `GROUNDING_DOCS` (Step 1): for GSD, the phase's `NN-CONTEXT.md`
   (intent) and `NN-RESEARCH.md` (research) — plus `NN-PATTERNS.md`/`NN-UI-SPEC.md` if present —
   from the same `.planning/phases/<phase>/` dir; for superpowers, the sibling `*-design.md` for
   a plan. The reviewer grounds the document against these to catch drift (plan contradicts its
   own intent/research) but emits **no findings about the grounding docs themselves**. Context/
   state archetypes (`state`, discussion logs, verification, summaries) are grounding-only, never
   reviewed. If no sibling context exists, pass `none`.

## Step 0.7 — Resolve the reviewer list (cross-AI)

Runs once per invocation, after Step 0.6. Before walking the cross-AI ladder, ask yourself: is cross-AI support actually installed and requested here, or does this invocation degrade cleanly to the session default (`--no-cross-ai`, or `ai-kit-spec.py` simply not present)? Answering that first avoids resolving quota/runtime state nobody asked for.

**MANDATORY — READ ENTIRE FILE, on every run**: Before running any command below, read [`references/cross-ai-dispatch.md`](references/cross-ai-dispatch.md) completely — it has the exact VERBATIM bash snippets, resolution order, and fail-closed rules for resolving `TOOLS_PY`, `CHECKLIST_SKILL_MD`, `RUNTIMES_JSON`, `QUOTA_JSON`, `SHARED_TOOLING_PATH`, `TOOL_AVAILABILITY_JSON`, `RUN_TMP_DIR`, and ultimately `REVIEWER_LIST`. Do not attempt to reconstruct these from memory. `--no-cross-ai` does not skip it: points 0–2 (paths, tooling facts, `RUN_TMP_DIR`, the session-default list) are what Step 1's native dispatch substitutes and writes into; the flag skips only points 3–6.

Once resolved, `REVIEWER_LIST`, `RUN_TMP_DIR`, `TOOLS_PY`, `CHECKLIST_SKILL_MD`, `SHARED_TOOLING_PATH`, and `TOOL_AVAILABILITY_JSON` are consumed by Step 1 below exactly as named.

When `probe-quota` or `resolve-reviewers` prints `ignoring untrusted project-local config`
(on stderr), a project-local `.aikit/review-spec.toml` is present but not trusted yet — show
the user `python3 "$TOOLS_PY" trust-local --cwd <CODEBASE_ROOT> --show` (writes nothing; one JSON
line per local reviewer with the argv dispatch would run, merged with the global config, the
prompt shown as `<prompt>`), ask whether to trust it, and run
`python3 "$TOOLS_PY" trust-local --cwd <CODEBASE_ROOT>` only after an explicit yes, then re-run
the reference's points 4–5. Never trust on the user's behalf. `--revoke` withdraws trust, even
after the file was deleted.

## Constants

- **Reviewer skill:** `ai-kit-spec-review-checklist`
- **Fixer skill:** `ai-kit-spec-review-fixer`
- **Dispatch for both:** fresh-context delegation (Step 1) — on Claude Code the `Agent` tool with `subagent_type: general-purpose`.
- **Fixer model:** `sonnet` on Claude Code (Haiku misses subtle defects; Opus burns tokens for no extra fix-quality signal). Another host runs the fixer on its session default — say so in the Surface message rather than implying a sonnet fix. The reviewer's model is not a Constant at all — it comes from `REVIEWER_LIST` (Step 0.7, points 2/5/6), set per-entry.
- **Iteration cap:** 3 (configurable per invocation if user requests)
- **Loop state file (optional):** `$RUN_TMP_DIR/loop.log` — append iter# + status line each round, for debugging only.
- **Framework profile seeds dir** (`SEEDS_DIR`) — resolve once to an **absolute** path. As a skill
  you are not guaranteed a `CLAUDE_PLUGIN_ROOT`; take the **first existing** of, in order (the
  sibling first, so the profiles match the skill you loaded, not an older install elsewhere):
  1. the sibling of this skill: `<dir-of-this-SKILL.md>/../ai-kit-spec-review-checklist/references/frameworks/`
  2. `${CLAUDE_PLUGIN_ROOT}/skills/ai-kit-spec-review-checklist/references/frameworks/` (when set)
  3. `~/.claude/skills/ai-kit-spec-review-checklist/references/frameworks/` (symlinked install — what `tools/install.sh` creates)

  ```bash
  # SKILL_DIR = the directory containing this SKILL.md (the ai-kit-spec-review skill)
  SKILL_DIR="$(dirname "<absolute path to THIS SKILL.md>")"
  for d in "$SKILL_DIR/../ai-kit-spec-review-checklist/references/frameworks" \
           "${CLAUDE_PLUGIN_ROOT:+$CLAUDE_PLUGIN_ROOT/skills/ai-kit-spec-review-checklist/references/frameworks}" \
           "$HOME/.claude/skills/ai-kit-spec-review-checklist/references/frameworks"; do
    [ -d "$d" ] && { SEEDS_DIR="$d"; break; }
  done
  ```
  If none of the three fallbacks resolves to an existing directory, STOP and surface to the user: `The ai-kit-spec-review-checklist skill is not installed (no framework profiles found). Install ai-kit and re-invoke.` — do not invent a path or proceed.

  It holds the curated seed profiles `<id>.md` and `SCHEMA.md`. **Never reference these as a bare
  relative `references/frameworks/…`** — your CWD is the user's repo (often a worktree), not the kit.
- **Framework profile cache** (`CACHE_DIR`): `~/.claude/cache/framework-profiles/*.md` (absolute,
  user-global) — learned/refreshed profiles the orchestrator writes for frameworks not covered by a
  seed. Create the dir on first write.
- **Runner:** subprocess dispatch needs Node 24 (GSD's declared floor); older versions untested.
  Without Node, subprocess entries are skipped as `dispatch_unavailable`
  (the stderr line starts `ai-kit-spec: subprocess dispatch needs Node`) and the session
  default still runs.
- **`claude` is review-only:** the runtime table flags it review-only, so it is a review target
  and never an execution CLI. Routing skips an exec-mode `claude` candidate unless it is a
  Claude Code alias on a Claude Code host (that one runs natively).

## NEVER (hard landmines)

These are the failures that have actually bitten this loop; violating any one silently corrupts
the review. Two that deserve a callout before you're even inside the loop:

- **NEVER dispatch any subagent before every document under review is saved on disk** (Step 0). Subagents read via `Read`; an in-memory doc does not survive the dispatch boundary.
- **NEVER run the generic fixer before `EFFECTIVE_REPORT_PATH` exists on disk** (Step 1.5). The fixer has nothing to `Read` otherwise.

The `## Hard rules for the orchestrator` table near the end carries the full list (these two plus
paraphrasing-into-prompts, defaulting `CODEBASE_ROOT` to CWD, editing the document yourself, and
reusing a subagent across iterations) with reasons for each.

## Loop

Run this loop. Each iteration is one reviewer dispatch followed by (conditionally) one fixer dispatch. Steps 1-5 below fully specify the branching; if you want a visual companion for tracing how the four Step 3 routes rejoin the loop, see [`references/loop-diagram.md`](references/loop-diagram.md) (optional — not required to execute the loop correctly).

### Step 1 — Dispatch reviewer(s) (every iteration)

A reviewer or executor is a (runtime, model) pair. Each call runs it natively when its runtime is the current host and the host can select that model; otherwise it runs as a subprocess through the supervised runner. An entry with neither a runtime nor a model is the session default, which the host always runs natively. Today only Claude Code selects a model per call (its sonnet, opus, haiku and fable aliases); every other host runs only its session default natively.

`resolve-reviewers` adds a per-call `route` and never stores it. A skip (`bad_model`,
`no_inventory`, `not_installed`, `unknown_runtime`, `no_model`, `review_only`) never reaches
`REVIEWER_LIST`: stderr prints `ai-kit-spec: skipping reviewer <key>: route <route>`. The routes
that do dispatch are `native`, `subprocess`, `unverified` and `custom`.

**Fresh-context delegation** (the native route here, and every fixer in Step 3). It needs a host
tool that starts a new agent with an empty context, given only a prompt, and returns its final
text. On Claude Code that is the `Agent` tool (`subagent_type: general-purpose`, `model` as
below). On another host it is that host's own subagent/task tool, with no model field: it runs
the session default. **If the host has no such tool, never review or fix inline in this
conversation** — this context holds the author's intent, exactly the contamination the loop
exists to prevent. Drop the native entry instead; if a subprocess entry remains in
`REVIEWER_LIST`, run it alone (single mode) and say so in the Surface message; otherwise STOP:
`This host cannot start a clean-context reviewer. Register a subprocess reviewer with
ai-kit-spec-config, or run /ai-kit-spec-review on a host with subagents.` No ai-kit command
detects this capability: it is your own knowledge of the host's tools, a portability gap stated
here rather than papered over.

**MANDATORY — READ ENTIRE FILE** before writing either reviewer prompt:
[`references/reviewer-prompts.md`](references/reviewer-prompts.md) holds both VERBATIM templates.

For each entry in `REVIEWER_LIST`:

- **`route` is `native`** (this host runs the pair itself), through fresh-context delegation with
  the native template. On every host except Claude Code that is only the session default, so
  give no model and let the host use its current session. Claude Code is the one labelled case
  of per-call selection: its `Agent` tool takes one of the four aliases and nothing else.
  - `model`: the entry's alias when the host is Claude Code, **omitted entirely when
    `model == ""`** (the `NO_CONFIG_FALLBACK`/session-default case — never substitute a
    hardcoded name; an empty `model` means "let the host use its session"). A non-empty
    `model` on any other host is a config error. On Claude Code it must be one of
    `sonnet`/`opus`/`haiku`/`fable` (not a full model id like `"opus-5"`);
    `ai-kit-spec-config` writes exactly that shape, so surface anything else as a config
    error rather than passing it through.
  - `description` (where the tool takes one): `ai-kit-spec-review iter N reviewer (<key>)`
  - After the delegated agent returns its report text, write it verbatim to
    `$RUN_TMP_DIR/iter<N>-<key>.md` with the host's file-write tool. Step 1.5's merge reads
    every reviewer's report from a file, so a native report must land on disk exactly like a
    subprocess one, or `merge-reports` has no file to open in `double` mode.

- **`route` is `subprocess`, `unverified` or `custom`** (`dispatch-reviewer`):
  a `subprocess` or `unverified` entry names a table runtime and runs through the supervised
  runner (`node` plus the runner template), which builds the argv from `runtime` and `model`.
  A `custom` entry has a `command` and no `runtime`; the fixed-argv launcher (same supervision
  core, no shell) runs that command, and its stderr is classified for quota, auth and
  configuration. `unverified` means the runtime's model list was unavailable after one
  refresh: neither ai-kit nor the runner checks the model before the CLI runs. The runner has
  no `unverified` status — that word is only this route — and stderr prints
  `ai-kit-spec: dispatching reviewer <key> unverified: ...`.
  1. Write the subprocess prompt from `references/reviewer-prompts.md` to
     `$RUN_TMP_DIR/iter<N>-<key>-prompt.txt`.
  2. Resolve this entry's timeout tiers via the `resolve-timeout-tiers` subcommand (the entry's
     own flat `timeout_tiers` key if `$RUN_TMP_DIR/reviewers.json`'s entry at this index has
     one, else the config's own `policy.timeout_tiers`):
     ```bash
     TIMEOUT_TIERS="$(python3 "$TOOLS_PY" resolve-timeout-tiers --cwd <CODEBASE_ROOT> \
       --reviewers-json "$RUN_TMP_DIR/reviewers.json" --index <0 for primary, 1 for secondary>)"
     ```
  3. Dispatch via `dispatch-reviewer` — **one** call, no separate render step, instead of a
     hand-built `nohup`/redirect pipeline. One tested Python path composes the prompt and runs
     the entry (a table runtime through the runner, a custom entry through the launcher); never
     assemble that argv in the shell:
     ```bash
     python3 "$TOOLS_PY" dispatch-reviewer --cwd <CODEBASE_ROOT> \
       --reviewers-json "$RUN_TMP_DIR/reviewers.json" \
       --index <0 for the primary/single reviewer, 1 for the secondary> \
       --prompt-file "$RUN_TMP_DIR/iter<N>-<key>-prompt.txt" \
       --timeout-tiers "$TIMEOUT_TIERS" \
       --tool-availability-json "$TOOL_AVAILABILITY_JSON" \
       --stdout-only \
       > "$RUN_TMP_DIR/iter<N>-<key>.md"; echo "$?" > "$RUN_TMP_DIR/iter<N>-<key>.exit"
     ```
     `--cwd` runs the reviewer, and the runner's read-only tree check, in the document's
     worktree rather than this session's cwd (for a labeled set, the root of `<DOC_PATHS>`'s
     first entry).
     **Two hard rules, no exceptions:** (1) do not render the command yourself and pass it back
     in — hand `dispatch-reviewer` the reviewer entry and let it render internally; and (2) run
     this backgrounded or with an explicit near-cap shell timeout, never the tool default (the
     tiers are cumulative and can reach 60 minutes of wall time). **The dispatch is finished
     only when `iter<N>-<key>.exit` exists** — never because the report file stopped growing
     (the `>` redirect creates it at once, and it can sit unchanged while the CLI works). Read
     the exit code from that file: nonzero leaves this reviewer's slot undispatched — delete
     `$RUN_TMP_DIR/iter<N>-<key>.md` so Step 1.5's fail-closed `### Status:` handling applies
     unchanged. Never move on to Step 1.5 while a dispatch is still running; if you must abandon
     one, stop that process first. **MANDATORY before deviating from either rule**: read
     [`references/cross-ai-dispatch.md`](references/cross-ai-dispatch.md)'s
     [Step 1 subprocess dispatch](references/cross-ai-dispatch.md#step-1-subprocess-dispatch--full-rationale-for-dispatch-reviewer)
     section for the full rationale — it explains the injection/escaping hazard rule (1)
     prevents and the tier-math behind rule (2).

### Step 1.5 — Merge reviewer reports, then bind `EFFECTIVE_REPORT_PATH` (runs every iteration — only the merge call itself is conditional)

**This whole step always runs, in both the 1- and 2-reviewer cases** —
only the `merge-reports` `Bash` call below is conditional on
`REVIEWER_LIST` having 2 entries. Do not skip this step for a
single-reviewer iteration: `EFFECTIVE_REPORT_PATH` is bound here either
way, and Step 2/3a/3b below have no other source for it.

When `REVIEWER_LIST` has 2 entries, run:

```bash
python3 "$TOOLS_PY" merge-reports --doc-paths "<DOC_PATHS>" \
  "<key1>=$RUN_TMP_DIR/iter<N>-<key1>.md" \
  "<key2>=$RUN_TMP_DIR/iter<N>-<key2>.md" \
  > "$RUN_TMP_DIR/iter<N>-merged.md"
```

`merge-reports` exits non-zero and prints `### Status: Failure — <lanes>` when any lane
failed or produced no readable report (missing file, no `### Status:` line, or a lane whose
status is `### Status: Failure — …`). The redirect above still captures that line in
`$RUN_TMP_DIR/iter<N>-merged.md`. Do not treat the nonzero exit as a separate failure mode —
bind `EFFECTIVE_REPORT_PATH` to that merged file and go straight to Step 2 with the Failure
line it contains.

Record `EFFECTIVE_REPORT_PATH`: `$RUN_TMP_DIR/iter<N>-merged.md` when
`REVIEWER_LIST` had 2 entries, else `$RUN_TMP_DIR/iter<N>-<key>.md` (the
single reviewer's own raw report) when it had 1. **Every later step reads
`EFFECTIVE_REPORT_PATH` and only that name** — there is exactly one
report artifact per iteration from Step 1.5 onward, never three or four
different invented filenames for the same underlying thing. The merged
report becomes the input to Step 2 (parse `### Status:`) exactly as a
single reviewer's report would — the merge already reproduces that line
(`Approved` when no findings survived the merge, `Issues Found — fix and
re-invoke` when they did, or `Failure — <lanes>` when a lane could not be
merged). When `REVIEWER_LIST` has only 1 entry, skip the
merge call — that entry's raw report (or the host tool's output,
written to the same `iter<N>-<key>.md` path per Step 1) is
`EFFECTIVE_REPORT_PATH` directly, unchanged from today's behavior. If
`EFFECTIVE_REPORT_PATH` does not exist on disk at all — the single-mode
case of Step 1's "dispatch-reviewer exits nonzero" dispatch failure, which
deliberately leaves that path unwritten — treat it exactly like a
report that lacks a `### Status:` line: Step 2's existing "No Status
line -> Surface failure" rule applies unchanged, there is no separate
"missing file" case to handle.

### Step 2 — Parse reviewer Status

Read `EFFECTIVE_REPORT_PATH` (Step 1.5) from disk; locate the line beginning `### Status:` in it.

| Status | Action |
|---|---|
| `### Status: Approved` | Loop ends. Go to Surface (success). |
| `### Status: Issues Found — fix and re-invoke` | Continue to Step 3 if iter < cap, else go to Surface (cap reached). |
| `### Status: Failure — <reason>` | Loop ends. Surface failure with the reason verbatim (in double mode it names the failed lanes). Never treat as Approved. |
| Any other text on the Status line | Treat as Issues Found (be conservative); log the anomaly. |
| No Status line | Loop ends. Surface failure: "Reviewer did not emit a Status line." |

### Step 3 — Apply findings (when Issues Found, iter < cap)

Resolve a revise route per flagged archetype and dispatch to one of four handlers: 3a (generic fixer for direct edits), 3b-skill (native framework skill), 3b-cmd (slash command), or 3b-surface (hand off to user). Run 3c validation after successful native revise if the route requires it. Before dispatching, ask: which handler does this archetype's `revise_protocol.routes` actually specify — direct edit, a native skill, a slash command, or surface-only?

**MANDATORY — READ ENTIRE FILE**: Before dispatching to any of the four handlers below, read [`references/apply-findings.md`](references/apply-findings.md) completely — it has the exact VERBATIM prompt templates, parsing tables, and sequencing rules for all four routes. Do not attempt to reconstruct these from memory.

Dispatch per the route's `invoke`:

| `invoke` | Handler |
|---|---|
| (direct edit / archetype not covered) | **Step 3a** — generic `ai-kit-spec-review-fixer` fixer |
| `skill:<name>` | **Step 3b-skill** — hybrid native-skill revise; surface if it stalls |
| `slash_command` | **Step 3b-cmd** — invoke it if the command/backing skill is installed this session (e.g. global GSD), else surface |
| `surface` | **Step 3b-surface** — always hand the user the pre-filled command, then stop |

### Step 4 — Parse fixer Status

*(Reached only from Step 3a — the generic direct-edit fixer. The native-revise paths 3b-skill / 3b-cmd parse their own status inline and do not pass through here.)*

Before treating `No Edits` as equivalent to `Escalation Required`, notice the table below already
does — both end the loop and go to Surface. The distinction that matters is not to the loop but
to the user reading Step 5's message: "fixer looked and genuinely found nothing fixable" reads
very differently from "fixer tried and gave up," so carry the fixer's own stated reason into the
Surface message rather than collapsing both to a generic "escalation."

Locate the `### Status:` line in the fixer's Fix Summary.

| Status | Action |
|---|---|
| `### Status: Edits Applied` | Increment iter. Go back to Step 1 (re-review with fresh reviewer). |
| `### Status: Escalation Required` | Loop ends. Go to Surface (escalation). |
| `### Status: No Edits` | Loop ends. Go to Surface (escalation — fixer made no progress). |
| No Status line | Loop ends. Surface failure: "Fixer did not emit a Status line." |

### Step 5 — Surface to user

Before writing the message, ask: does the user need to *decide* something here, or just be
*informed*? Cap-reached and escalation outcomes need a decision, so they earn the full report;
a clean approval needs only a one-line confirmation. Over-pasting a report nobody has to act on
buries the signal as much as under-informing does.

Emit one short message in the user's terminal. Do NOT paste full reports unless the user is at cap or escalation.

| Outcome | Message shape |
|---|---|
| Approved on iter 1 | `Approved on first review. <DOC_PATHS> ready for next step.` |
| Approved after N iters | `Approved after N iteration(s). Doc edited and re-reviewed clean.` |
| Cap reached | `Hit iteration cap (N). Last review still has issues. Final report:\n\n<paste full last reviewer report>\n\nDecide manually.` |
| Escalation Required | `Fixer escalated on iter N. Reason: <fixer's escalation message>. Decide manually.` |
| Native revise handed off | `Findings ready. This <archetype> is owned by <framework>'s planner — run: <pre-filled command>  (findings: <report path>), then re-run /ai-kit-spec-review.` |
| Insufficient info (stage gap) | `Only <existing docs> exist; project is at the <stage> stage. No <requested archetype> to review yet. Reviewed <existing> as <archetype>; produce <next stage> before reviewing it.` |
| Validator blocked (Step 3c) | `Regenerated <archetype> was rejected by <validator> — <reasons>. Findings: <report path>. Fix manually and re-run /ai-kit-spec-review.` |
| Failure | `<failure mode message>. Last available output: <quote brief>.` |

After surfacing, the orchestrator's job is done. Do NOT continue to "next steps" — the user decides whether to invoke `writing-plans`, edit manually, or re-invoke `/ai-kit-spec-review` after their own edits.

## Hard rules for the orchestrator

| Rule | Reason |
|---|---|
| Never edit the document yourself. | Orchestrator is dispatch + parse, not author or fixer. |
| Resolve `CODEBASE_ROOT` from the document's own worktree (Step 0.1), never from your CWD. Use `git worktree list` when unsure. | Grounding the review against the wrong checkout (main vs. the worktree the doc lives in) yields phantom findings and misses real ones. |
| Never include conversation/intent/document-content in subagent prompts. | Subagents must form their own reading from disk. |
| Always dispatch a NEW subagent each iteration. Do not reuse. | Reuse contaminates context with prior round's findings. |
| Reviewer and fixer are separate subagents, never the same. | Fixer must edit; reviewer must not. Separation = audit integrity. |
| Stop at the iteration cap. | Avoid infinite review↔fix loops on irreconcilable disagreement. |
| If reviewer and fixer disagree on a finding's severity across iterations, surface to user. | Orchestrator does not arbitrate. |

## Routing table — who rewrites what

Routing is data-driven from each profile's `revise_protocol.routes` — that profile is always the
authoritative source; consult it, not a cached mental table, whenever routing is in doubt. For a
convenience snapshot of the seed profiles' routes (FR-1.5), see
[`references/routing-table.md`](references/routing-table.md) — useful for a quick sanity check,
but it may lag a profile that's since been edited.

## Cleanup

**Remove `$RUN_TMP_DIR` (`rm -rf "$RUN_TMP_DIR"`) only when the Surface outcome is `Approved`.**
Every other outcome (cap reached, escalation, insufficient info, failure) keeps it: a review
often spans several invocations (a cap handed back, an out-of-band fix, a fresh re-check), and
deleting the reports when one round merely ends once destroyed the only evidence of a still-open
review. The labelled directory name (Step 0.7 point 1) says which repo, branch and document each
kept directory belongs to; remove a stale one by hand once that review is approved or abandoned.
