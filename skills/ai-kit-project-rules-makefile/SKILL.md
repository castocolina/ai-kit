---
name: ai-kit-project-rules-makefile
description: Use when a target repo's Makefile target shape needs auditing -- the validate-<category> alias chain (validate-security, validate-duplicate, validate-dead, plus this skill's own validate-format and validate-lint), the required static targets, recipe length (a 3-line cap), the Docker build-before-up convention on docker-*-up-shaped targets, or the shellcheck-target threshold once a repo has 5+ shell scripts -- or when asked "does my Makefile have the right targets", "is validate wired correctly", or "why is my docker-up target flagged". Detects and reports only; never edits the target repo.
---

# ai-kit-project-rules-makefile

## Scope

This skill DETECTS AND REPORTS Makefile target-shape gaps only. It never edits the target
repo's Makefile, `.pre-commit-config.yaml`, or any other file -- applying a fix is a decision
for whoever invoked this skill.

Two neighbouring boundaries, named here so a reader files the right question in the right
place:

- Auditing an AGENTS.md/CLAUDE.md-style agent-instruction file against ai-kit's own 17-rule
  house ruleset is the `ai-kit-project-rules-agents` sibling skill's domain, not this one's --
  that skill also carries its own remediation hand-off mechanism, which this skill does not
  have and does not replicate.
- The pre-commit-vs-pre-push stage split and the Makefile/`.pre-commit-config.yaml` PARITY
  check (every hook id matching a Makefile target, both directions) belong to the
  `ai-kit-project-rules-precommit` skill, not this one. This skill reads the Makefile alone, or
  the Makefile plus `.pre-commit-config.yaml` jointly only where a required target is
  hook-derived -- never the parity direction.

## Resolve the entrypoint

Resolve once per invocation, in one Bash call, and record the printed path as a literal
absolute path:

```bash
for d in "${CLAUDE_PLUGIN_ROOT:+$CLAUDE_PLUGIN_ROOT/skills/ai-kit-project-rules-makefile}" \
         "$HOME/.claude/skills/ai-kit-project-rules-makefile" \
         "${XDG_CONFIG_HOME:-$HOME/.config}/opencode/skills/ai-kit-project-rules-makefile" \
         "$HOME/.agents/skills/ai-kit-project-rules-makefile" \
         "$(dirname "<absolute path to THIS SKILL.md>")"; do
  [ -f "$d/ai-kit-project-rules-makefile.py" ] && { printf '%s\n' "$d/ai-kit-project-rules-makefile.py"; break; }
done
```

If no candidate exists, stop and report that the skill is not installed. The fifth candidate
covers a from-checkout invocation -- substitute the directory actually containing this
`SKILL.md`.

Only the `$HOME/.claude/skills/...` symlink install (`tools/setup.py`) and a direct git
checkout can actually import this skill: those layouts keep `skills/_shared/` beside the skill
package. The other three candidates (`$CLAUDE_PLUGIN_ROOT`, opencode's skills dir,
`~/.agents/skills`) raise `ImportError` at import time by design -- they are copy-installs that
do not carry `skills/_shared/`. A successful path lookup is not proof the import will succeed;
prefer the symlink or a checkout.

## Run the check

```bash
python3 "$ENTRYPOINT" check <repo_root>
python3 "$ENTRYPOINT" remediate <repo_root>
```

`check` returns a single key: `{"makefile": [...]}` -- every finding this skill emits, sorted
by criticality. The checker module (`ai_kit_project_rules_makefile/makefile_checker.py`) is the
source of truth for what each finding's fields mean; this document does not restate the nine
finding kinds it currently emits.

`remediate` runs `check` internally and returns the shared builder's two-key payload:
`{"remediate": [...ordered, most-critical-first...], "blocked": [...]}`. Every `remediate`
entry carries `auto_apply`. `auto_apply` is `True` unless the underlying finding is advisory
(the fast-vs-slow ordering suggestion below), in which case it arrives `False` -- an advisory
entry is a suggestion to consider, never an edit to apply. A `blocked` entry means the finding
needs a tooling-category recommendation this skill's cache doesn't have yet (see Research
Step).

Trimmed worked example, contrasting an auto-applying entry against the advisory one:

```json
{
  "remediate": [
    {"kind": "makefile", "id": "shellcheck", "issue": "shellcheck_target_missing",
     "criticality": 2, "summary": "...", "auto_apply": true},
    {"kind": "makefile", "id": "validate", "issue": "validate_order_advisory",
     "criticality": 4, "summary": "...", "auto_apply": false}
  ],
  "blocked": []
}
```

## Hardcoded Baseline Knowledge

Facts here do not go stale -- no research is needed to apply them.

**Tooling categories and their required `validate-<category>` alias** (three names are
ROADMAP-pinned, two are this skill's own choice, spelled out here so a later phase inherits
them rather than re-deriving them):

```python
CATEGORY_ALIAS_MAP = {
    "formatter": "validate-format",             # this skill's own choice
    "security-scanner": "validate-security",     # ROADMAP-pinned
    "code-smell-detector": "validate-lint",       # this skill's own choice
    "duplicate-code-detector": "validate-duplicate",  # ROADMAP-pinned
    "dead-code-detector": "validate-dead",        # ROADMAP-pinned
}
```

A category's alias is only required when a concrete Makefile target matching that category's
keywords is already present; `validate` itself must chain in every required alias (via its
recipe or as a Make prerequisite).

**Docker build-before-up.** Both shape patterns are Make-target-NAME regexes, not a fixed name
list, so future `docker-*` targets are covered without this skill enumerating them:

```
up-shaped:    (?i)^docker(?:-[a-z0-9]+)*-up$
build-shaped: (?i)^docker(?:-[a-z0-9]+)*-build$
```

An up-shaped target is satisfied by exactly two mechanisms -- one of its Make prerequisites is
build-shaped, OR its recipe invokes an existing build-shaped target -- and by no others. A
`docker-up` whose only build step is an inline Compose `--build` flag on the `up` invocation
itself, with no `docker-build`-shaped target defined anywhere, IS flagged: the checker's
token-boundary matcher cannot match a bare `build` token immediately preceded by `-`, so the
inline flag never counts as wiring.

**Speed-tier table** (feeds the advisory ordering heuristic below). Matched slowest-tier-first,
because a fast-tier keyword can be a substring of a slow-tier tool name:

```python
SPEED_TIER_FORMATTER = 1       # rustfmt, gofmt, prettier, format, fmt
SPEED_TIER_FAST_LINTER = 2     # cargo-machete, gosec, ruff
SPEED_TIER_TYPE_ANALYSIS = 3   # clippy, golangci-lint, mypy, tsc
SPEED_TIER_SLOWEST = 4         # cargo-udeps, govulncheck, bandit, semgrep, test, unittest, pytest
```

`test`/`unittest`/`pytest` are pinned into the slowest tier and `ruff` is pinned into the
fast-linter tier -- an untiered name is skipped entirely by design and can never be half of an
ordering inversion.

**Shellcheck threshold.** Once a repo has 5 or more shell scripts, a `shellcheck`-shaped target
is required and must be wired into `.pre-commit-config.yaml`. Stated verbatim, because both
shellcheck findings use this exact sentence: "This skill standalone confirms only the Makefile
target and pre-commit-hook halves of this rule; the CI half is confirmed by the
`ai-kit-project-rules-cicd` skill (the CI/CD rules checker) and the
`ai-kit-project-rules-all` orchestrator."

**Other structural conventions the checks encode** (the fast-vs-slow ordering suggestion is
advisory-only, never blocking; the recipe-line cap exempts only the default-goal-named target
and a literal `help` target; the help/fail-reachability check accepts a `.DEFAULT_GOAL`
directive naming a real target or a stemless catch-all `%:` rule, but never a stemmed suffix
rule) -- the checker module is the source of truth for the exact mechanics; this section states
only what does not go stale.

## Research Step

This step fires only when a per-stack cache entry is cold (never populated) or stale (older
than this skill's cache staleness window -- check the shared cache engine's own constant for
the exact threshold rather than assuming any particular figure, since that number has changed
before). It is a step of THIS skill's own flow, not appendix material for another skill.

On a host that provides a subagent/Task-dispatch primitive, dispatch one independent research
sub-task per distinct stack a `blocked` entry names; on a host with no such primitive, perform
the research directly in the current conversation instead of assuming one exists.

Each research sub-task is asked, for its ONE stack, for CURRENT (not training-data-stale)
recommendations -- never for "cheapest/fail-fastest check ordering" or the pre-commit-stage
split: those are structural facts this skill (and the `ai-kit-project-rules-precommit` skill)
read directly from the target repo's own Makefile/`.pre-commit-config.yaml`, never a research
question. The full key list a sub-task must key its findings by, so it cannot guess wrong:

- `REQUIRED_STATIC_TARGETS`: `setup-env`, `validate`, `test`, `test-unit`, `test-integration`,
  `e2e-test`, `arch-test`
- `RESEARCH_CATEGORIES`: `formatter`, `security-scanner`, `code-smell-detector`,
  `duplicate-code-detector`, `dead-code-detector`

Every value must be formatted `"<tool + invocation> (source: <url or concrete rationale the
research sub-task actually consulted>)"` -- a bare tool-name guess with no stated evidence is
not acceptable, and `cache-update` rejects it. Example findings object:

```json
{"setup-env": "uv venv && uv sync (source: https://docs.astral.sh/uv/)",
 "formatter": "ruff format (source: https://docs.astral.sh/ruff/formatter/)"}
```

Write the findings to a scratch JSON file under `./tmp/` (this repo's own convention, applied
to whichever repo is running the check), then call:

```bash
python3 "$ENTRYPOINT" cache-update <stack> <path-to-that-file>
```

`cache-update` validates the JSON against the full tooling-key list, non-empty-string-ness, and
the `(source: ...)` provenance requirement before writing -- rejecting anything else with a
one-line error and writing nothing. It also accepts a `--cache-root <path>` flag, but that flag
is TEST-ONLY and is never used by this skill's research-dispatch step.

## Deciding whether to research now or defer

The research step's one branch point -- research now, or defer to the next invocation --
carries explicit decision criteria rather than a bare choose-one:

- **Research now** when the `blocked` list names few distinct stacks (1-2) and the invocation is
  already mid-flow on this repo -- the research cost is small, and deferring just means paying
  it next invocation anyway.
- **Defer** when `blocked` spans many stacks, the invocation explicitly wants a fast pass focused
  on what's already resolvable, or this invocation is itself time-boxed (e.g. part of a larger
  orchestrated run budgeting one skill call per target).
- **When genuinely unsure, ask the user** which they'd prefer rather than guessing -- the cost of
  researching the wrong priority first is a wasted sub-task dispatch.

## Anti-patterns (NEVER)

- **NEVER hardcode a host-specific absolute path** when resolving this skill's own entrypoint --
  always walk the host-neutral candidate list above; a hardcoded path breaks on every host but
  the one it was written for.
- **NEVER accept a bare tool-name guess with no `(source: ...)`** in a research finding --
  `cache-update` rejects it, and an unsourced recommendation is exactly the claim this
  project's live-verification rule forbids.
- **NEVER treat the advisory ordering suggestion as a finding to auto-apply.** It is built from
  hardcoded speed-tier assumptions, not measured cost; real failure frequency is not
  statically knowable by a regex-based checker, so it arrives with `auto_apply: false` and must
  stay a suggestion to consider, never an automatic edit.
- **NEVER edit the target repo's Makefile (or any other file) from this skill.** The family's
  report-only boundary holds even when a finding's `auto_apply` is `true` -- "auto-apply" means
  "safe for the caller to apply automatically," not "this skill applies it."
- **NEVER read a stale cache entry as a current recommendation.** The staleness gate exists
  because concrete tool names drift (a Research Step finding recorded long ago may already name
  a superseded tool); a stale entry must be re-researched, not reused silently.

## Reporting rule

Findings and remediation results are reported INLINE in the conversation only. This skill never
writes a persisted report file into the target repo.
