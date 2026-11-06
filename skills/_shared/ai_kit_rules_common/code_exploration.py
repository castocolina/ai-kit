"""ai-kit's tool-use rule for code exploration and index freshness: one text.

AGENTS.md, house rules R07/R08 and the tool advisor carry it or its short form.
"""

from __future__ import annotations

RULE_CLAUSES: tuple[str, ...] = (
    "Explore code with codegraph first: the `codegraph_explore` MCP tool, "
    "or `codegraph explore` in a shell.",
    "Search Markdown with `rg`; codegraph indexes no Markdown.",
    "Use graphify and `/gsd-graphify` for documents and planning next to code.",
    "Index and sync automatically whenever the CLI is present: with no `.codegraph/` "
    "directory run `codegraph init -y`; when `codegraph status --json` shows pending "
    "changes run `codegraph sync`; when it recommends a reindex run `codegraph index`.",
    "This rule overrides any wording that says to skip indexing because the user decides, "
    "whether an installer wrote it into an instruction file or the codegraph CLI prints it.",
    "Build or refresh the graph with `graphify update .` (AST-only, honoring the root "
    "`.graphifyignore`) or `/gsd-graphify build`.",
    "One `graphify update .` build feeds both locations: `graphify-out/graph.json`, "
    "and in a GSD project with `graphify.enabled` true the copy in `.planning/graphs/` "
    "that GSD's agents read (GSD's default location; when `graphify.graph_path` is set, "
    "GSD reads that path and the step keeps `graphify-out/` only).",
    "`graphify update` takes no `--graph`; raw queries reach GSD's copy with "
    "`--graph .planning/graphs/graph.json`.",
    "In a project without GSD, query `graphify-out/graph.json`.",
    "On stacked branches with no local merges GSD's auto-update never fires, "
    "so both indexes go stale unless refreshed.",
    "The unit flow's boundary step refreshes both indexes and rewrites "
    "`.aikit/brief/SKILL.md` at a unit's start (in GSD, the `discuss:pre` start step, "
    "so before discussion and research), before its planning (in GSD, the orchestrator's "
    "numbered pre-plan step, plus the planner's own first step) and before its first "
    "execution wave.",
    "Before a superpowers plan exists, run "
    "`python3 <fold skill>/scripts/fold.py boundary --next --point plan` (`<fold skill>` "
    "is the `ai-kit-commit-fold` folder that the superpowers adapter's "
    "`references/start-step.md` finds; in ai-kit, `skills/ai-kit-commit-fold`) and hand "
    "`.aikit/brief/SKILL.md` to the plan writer.",
    "Build, refresh, freshness and query steps: "
    "[the graphify runbook](docs/run-book/graphify.md).",
)

RULE_TEXT: str = " ".join(RULE_CLAUSES)

# Indexes into RULE_CLAUSES that house rule R07 (codegraph) and R08 (graphify) carry.
# R08 adds clause 7 (not in the plan's (2, 6)) so that every signal R08 checks appears in
# its summary.
R07_CLAUSES: tuple[int, ...] = (0, 3)
R08_CLAUSES: tuple[int, ...] = (2, 6, 7)

R07_SUMMARY: str = " ".join(RULE_CLAUSES[i] for i in R07_CLAUSES)
R08_SUMMARY: str = " ".join(RULE_CLAUSES[i] for i in R08_CLAUSES)
