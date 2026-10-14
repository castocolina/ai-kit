# Analyzer brief template

Read before spawning `gsd-assumptions-analyzer` (or running the analysis inline). Start from the
spawn prompt in `discuss-phase-assumptions.md` (its `deep_codebase_analysis` step) and add the
blocks below. Fill every `<...>`; delete a block only where its condition says so.

```text
Phase <N>: <name>. Goal: <ROADMAP goal>.

Locked WHAT: <path to NN-SPEC.md>. Read it first; do not re-decide its requirements. If a live
fact contradicts it, report the contradiction with evidence instead of working around it.

Locked HOW (keep verbatim; only propose dated amendments): <list of D-ids and one-line
summaries from the existing NN-CONTEXT.md, or "none">.

Earlier phases' decisions that constrain this one: <D-ids from prior CONTEXT files>.

Quality rule: <mvp inactive: "The best design wins over the smallest diff; least-code findings
decide how code is written, not which design wins." | mvp active: "Prefer the simpler design as
long as it does not lower what reaches the product's user.">

Live-verify claims: installed versions, real config keys, real CLI output — in a scratch dir
under <tmp path>, never in the user's real config dirs. Never print a secret or key value.

<CODEGRAPH BLOCK — include only when `command -v codegraph` succeeds>
CodeGraph is available. Before exploring code, run `codegraph sync <repo or worktree path>`
(or `codegraph init <path>` when `.codegraph/` is missing), then use `codegraph explore
"<symbols or question>"` or the `codegraph_explore` MCP tool before grep/read loops. In a git
worktree the index may belong to the main checkout (another branch): index the worktree first,
or treat results as hints and re-read the worktree files.
</CODEGRAPH BLOCK>

<COUPLING BLOCK — include only when this analyzer runs in the background beside other work>
This runs while phase <K> is being written. Known coupling: <what K decides that may affect
this phase, or "none known">. Report any dependency on phase <K>'s open items explicitly.
</COUPLING BLOCK>

Output, per area: the standard Assumption / Why this way / If wrong / Confidence fields, plus
for every Likely or Unclear item:
- Alternatives: 2–3, with the best one and the easy one marked;
- Jev question: one standalone, summary-only question with neutral option descriptions and a
  non-empty context line (no code, no file contents, no secrets).
Do NOT call jev, Laya or TypeSafe yourself. End with "Needs External Research" (open factual
questions only, never guesses) and one line on what you skipped.
```

Why each block exists:
- **Locked WHAT/HOW** — the assumptions workflow loads neither the SPEC nor this phase's own
  CONTEXT; without them the analyzer re-litigates settled scope.
- **Quality rule** — analyzers default to the smallest diff.
- **CodeGraph** — a worktree's index can silently describe another branch.
- **No jev** — remote calls would bypass consent, the one-item Laya rule and the log.
