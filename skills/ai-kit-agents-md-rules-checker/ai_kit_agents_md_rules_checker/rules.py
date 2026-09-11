"""ai-kit's 17-rule house ruleset as structured data (D-06).

Each entry is a plain dict with keys: id, category, criticality, condition,
signals, summary. `signals` drives Task 2's keyword heuristic and comes in
three shapes:

  - FLAT: a tuple of lowercase phrase strings (most rules).
  - PLAIN GROUPS (R04 only): a tuple of tuples-of-phrases, where each inner
    tuple is one independently-required clause.
  - TOOL-SCOPED GROUPS (R06 only): a tuple of `(tool_name, phrases)` 2-tuples,
    where a group is only required when that tool is actually installed.

`summary` is this plan's own concise paraphrase of the source todo's rule
text (D-01) -- never a verbatim block-quote.
"""

from __future__ import annotations

CONDITION_ALWAYS = "always"


def condition_tool_presence(name: str) -> str:
    return f"tool-presence:{name}"


CRITICALITY_CRITICAL = 1
CRITICALITY_HIGH = 2
CRITICALITY_MEDIUM = 3

RULES: tuple[dict, ...] = (
    {
        "id": "R01",
        "category": "workflow",
        "criticality": CRITICALITY_CRITICAL,
        "condition": CONDITION_ALWAYS,
        "signals": ("english only", "english-only", "non-negotiable"),
        "summary": (
            "All written project artifacts (docs, commits, comments, "
            "planning files) are English-only, regardless of the "
            "conversation's language."
        ),
    },
    {
        "id": "R02",
        "category": "makefile",
        "criticality": CRITICALITY_CRITICAL,
        "condition": CONDITION_ALWAYS,
        # These three signals check ONLY R02's separate prose clause; the
        # Makefile SHAPE half of R02 is read from the real Makefile by
        # makefile_checker.py, never from AGENTS.md prose.
        "signals": ("--no-verify", "skip pre-commit checks", "red-green"),
        "summary": (
            "Agents must not skip pre-commit checks, except for the "
            "sanctioned TDD red-to-green bypass of intentionally "
            "committing a failing test before turning it green."
        ),
    },
    {
        "id": "R03",
        "category": "workflow",
        "criticality": CRITICALITY_HIGH,
        "condition": CONDITION_ALWAYS,
        "signals": ("one coherent", "compaction", "logical commit"),
        "summary": (
            "The compaction unit is the plan: fold related work into as "
            "few logically-grouped commits as possible before closing out "
            "a plan, rather than leaving commit sprawl."
        ),
    },
    {
        "id": "R04",
        "category": "workflow",
        "criticality": CRITICALITY_HIGH,
        "condition": condition_tool_presence("gsd"),
        "signals": (
            ("cross-ai review", "plan-review convergence", "cross-ai plan-review"),
            ("cross-ai execution", "cheap-model execution", "cheap model"),
            ("path-agnostic", "path agnostic"),
        ),
        "summary": (
            "Every plan must enable cross-AI plan-review, cross-AI "
            "cheap-model execution, and generate path-agnostic (PATH-"
            "resolved, never machine-specific absolute) commands."
        ),
    },
    {
        "id": "R05",
        "category": "workflow",
        "criticality": CRITICALITY_MEDIUM,
        "condition": condition_tool_presence("rtk"),
        "signals": ("rtk", "token killer", "tool substitution"),
        "summary": (
            "When rtk (Rust Token Killer CLI proxy) is present, agents "
            "should be told how its hook-based command rewriting (e.g. "
            "`git status` -> `rtk git status`) works."
        ),
    },
    {
        "id": "R06",
        "category": "workflow",
        "criticality": CRITICALITY_MEDIUM,
        "condition": condition_tool_presence("modern-cli"),
        "signals": (
            ("rg", ("rg", "ripgrep")),
            ("bat", ("bat", "batcat")),
            ("sd", ("sd", "stream editor", "sed replacement")),
            ("fd", ("fd", "fd-find")),
            ("eza", ("eza", "exa")),
        ),
        "summary": (
            "When modern CLI tools (rg, bat, sd, fd, eza) are present, "
            "agents should be told to prefer them over their legacy "
            "counterparts, with a short usage hint for each installed tool."
        ),
    },
    {
        "id": "R07",
        "category": "workflow",
        "criticality": CRITICALITY_MEDIUM,
        "condition": condition_tool_presence("codegraph"),
        "signals": ("codegraph", "codegraph_explore", ".codegraph"),
        "summary": (
            "When `.codegraph/` is present, prefer the codegraph_explore "
            "MCP tool over ad hoc Read/Grep for codebase exploration."
        ),
    },
    {
        "id": "R08",
        "category": "workflow",
        "criticality": CRITICALITY_MEDIUM,
        "condition": condition_tool_presence("graphify"),
        "signals": ("graphify", "graph.json", "graphify-out"),
        "summary": (
            "When graphify is present, agents should use it for doc-aware "
            "indexing and trigger re-indexing proactively rather than "
            "relying solely on its hook."
        ),
    },
    {
        "id": "R09",
        "category": "workflow",
        "criticality": CRITICALITY_HIGH,
        "condition": CONDITION_ALWAYS,
        "signals": ("orphan", "orphaned process", "kill"),
        "summary": (
            "Any agent-spawned ephemeral process or window used for e2e "
            "verification must be killed/stopped when done -- no orphaned "
            "processes left alive."
        ),
    },
    {
        "id": "R10",
        "category": "workflow",
        "criticality": CRITICALITY_MEDIUM,
        "condition": CONDITION_ALWAYS,
        "signals": ("./tmp/", "tmp/", "ephemeral"),
        "summary": (
            "Ephemeral scratch files/scripts with no lasting project value "
            "belong under `./tmp/` (gitignored), not scattered through the "
            "repo."
        ),
    },
    {
        "id": "R11",
        "category": "workflow",
        "criticality": CRITICALITY_HIGH,
        "condition": CONDITION_ALWAYS,
        "signals": ("readme", "docs currency", "nested docs"),
        "summary": (
            "README and other nested docs (submodule READMEs, diagrams, "
            "docstrings) must be kept current after any significant "
            "feature change."
        ),
    },
    {
        "id": "R12",
        "category": "workflow",
        "criticality": CRITICALITY_CRITICAL,
        "condition": CONDITION_ALWAYS,
        "signals": ("no absolute path", "absolute path", "relative path"),
        "summary": (
            "Project assets, source, and tests never hardcode absolute "
            "filesystem paths; use relative or repo-root-relative "
            "resolution."
        ),
    },
    {
        "id": "R13",
        "category": "workflow",
        "criticality": CRITICALITY_CRITICAL,
        "condition": CONDITION_ALWAYS,
        "signals": ("no excuse", "deflection", "not my fault"),
        "summary": (
            "No excuse-driven deflection on a failing test or bug -- "
            "agents must address it, never blame something else or defer "
            "it as a scope change."
        ),
    },
    {
        "id": "R14",
        "category": "workflow",
        "criticality": CRITICALITY_HIGH,
        "condition": CONDITION_ALWAYS,
        "signals": ("stale knowledge", "gray-area", "verify before trusting"),
        "summary": (
            "On gray-area or genuinely new topics, verify against current "
            "resources instead of trusting potentially-stale training "
            "data."
        ),
    },
    {
        "id": "R15",
        "category": "workflow",
        "criticality": CRITICALITY_HIGH,
        "condition": CONDITION_ALWAYS,
        "signals": ("theory", "hypothesis", "spike"),
        "summary": (
            "For new/unfamiliar territory, follow theory -> hypothesis -> "
            "spike before any plan is written, rather than planning on "
            "untested assumptions."
        ),
    },
    {
        "id": "R16",
        "category": "workflow",
        "criticality": CRITICALITY_HIGH,
        "condition": CONDITION_ALWAYS,
        "signals": ("uncommitted", "working area", "untracked"),
        "summary": (
            "Before closing a plan, the working area must have no "
            "uncommitted files left dangling -- fold, ignore, or ask, but "
            "never leave it unexplained."
        ),
    },
    {
        "id": "R17",
        "category": "workflow",
        "criticality": CRITICALITY_MEDIUM,
        "condition": CONDITION_ALWAYS,
        "signals": ("concise", "no excess documentation", "narrative"),
        "summary": (
            "Documentation should be concise, stating what was done and "
            "why -- skip narrating abandoned alternatives unless the "
            "rejection itself carries a load-bearing lesson."
        ),
    },
)
