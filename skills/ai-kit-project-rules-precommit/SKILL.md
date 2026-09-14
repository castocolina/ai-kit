---
name: ai-kit-project-rules-precommit
description: Use when a target repo's `.pre-commit-config.yaml` needs checking against its Makefile for parity (every hook id <-> a matching single-tool target, both directions), when detected pre-commit tooling needs classifying into the six-category taxonomy (Formatting/Type-checking/Linting/Security/Duplicate-code/Dead-code), when a config might be an uncurated "enable-everything" ruleset (ruff `select = ["ALL"]`, an unpinned PMD wildcard, golangci-lint's full linter list, an ESLint all-plugins preset), when Duplicate-code or Dead-code category tooling might be completely absent, or when asked "does my pre-commit config match my Makefile", "is this tool redundant with that one", "why is ruff flagged for type safety", or "is my golangci-lint config duplicating staticcheck". Detects and reports only; never edits the target repo.
---

# ai-kit-project-rules-precommit

## Scope

This skill DETECTS AND REPORTS pre-commit-configuration and Makefile<->pre-commit parity gaps
only. It never edits the target repo's `.pre-commit-config.yaml`, Makefile, or any other file --
applying a fix is a decision for whoever invoked this skill.

Two neighbouring boundaries, named here so a reader files the right question in the right place:

- Makefile target SHAPE itself -- the `validate-<category>` alias chain, required static
  targets, the recipe-length cap, Docker build-before-up, the shellcheck threshold -- is the
  `ai-kit-project-rules-makefile` sibling skill's domain, not this one's. This skill reads the
  Makefile only to compare its targets against `.pre-commit-config.yaml`'s hooks; it never
  judges whether the Makefile itself is well-formed.
- Auditing an AGENTS.md/CLAUDE.md-style agent-instruction file is the `ai-kit-project-rules-
  agents` sibling skill's domain. That skill also carries its own agent-instruction-file
  remediation hand-off mechanism, which this skill does not have and does not replicate.

**The deliberate overlap, stated plainly:** a pre-commit hook with no matching Makefile target
produces a finding from THIS skill (`precommit-parity`/`hook_without_target`) AND a different
finding from the Makefile sibling (its own target-presence check unions hook ids into its
required-target set), on purpose -- the two answer different questions and recommend different
things. The sibling's finding says "add this target" (Makefile-completeness); this skill's
finding says "the two files disagree about the tool set" (parity). Neither suppresses the other,
neither reaches into the other to deduplicate. A reader who meets both reports about the same
hook and does not find this sentence will file a duplicate-findings bug against a designed
behavior.

## Resolve the entrypoint

Resolve once per invocation, in one Bash call, and record the printed path as a literal
absolute path:

```bash
for d in "${CLAUDE_PLUGIN_ROOT:+$CLAUDE_PLUGIN_ROOT/skills/ai-kit-project-rules-precommit}" \
         "$HOME/.claude/skills/ai-kit-project-rules-precommit" \
         "${XDG_CONFIG_HOME:-$HOME/.config}/opencode/skills/ai-kit-project-rules-precommit" \
         "$HOME/.agents/skills/ai-kit-project-rules-precommit" \
         "$(dirname "<absolute path to THIS SKILL.md>")"; do
  [ -f "$d/ai-kit-project-rules-precommit.py" ] && { printf '%s\n' "$d/ai-kit-project-rules-precommit.py"; break; }
done
```

If no candidate exists, stop and report that the skill is not installed. The fifth candidate
covers a from-checkout invocation -- substitute the directory actually containing this
`SKILL.md`.

Only the `$HOME/.claude/skills/...` symlink install (`tools/setup.py`) and a direct git checkout
can actually import this skill: those layouts keep `skills/_shared/` beside the skill package.
The other three candidates (`$CLAUDE_PLUGIN_ROOT`, opencode's skills dir, `~/.agents/skills`)
raise `ImportError` at import time by design -- they are copy-installs that do not carry
`skills/_shared/`. A successful path lookup is not proof the import will succeed; prefer the
symlink or a checkout.

## Run the check

```bash
python3 "$ENTRYPOINT" check <repo_root>
python3 "$ENTRYPOINT" remediate <repo_root>
python3 "$ENTRYPOINT" classify <repo_root>
```

`check` returns a single key: `{"precommit": [...]}` -- every finding this skill emits, sorted
by criticality. The checker modules (`parity_checker.py`, `taxonomy_checker.py`,
`enable_everything.py`, `ruff_checks.py`, `pair_checks.py`, and the shared
`ai_kit_rules_common.precommit_parse.check_precommit_prepush_split`) are the source of truth for
what each finding's fields mean; this document does not restate every finding kind's full field
list.

`remediate` runs `check` internally and returns the shared builder's two-key payload:
`{"remediate": [...ordered, most-critical-first...], "blocked": [...]}`. Every `remediate` entry
carries `auto_apply`. `auto_apply` is `True` UNLESS the underlying finding carries
`advisory: True` (the tool-pair findings and the statically-unreadable-config finding both do),
in which case it arrives `False` -- an advisory entry is a suggestion to consider, never an edit
to apply. A `blocked` entry means the finding needs a tooling-category recommendation this
skill's cache doesn't have yet (see Research Step).

`classify` returns `{"taxonomy": {category: [hook, ...] for each of the six categories},
"out_of_taxonomy": [hook, ...], "unclassified": [hook, ...]}` -- every declared pre-commit hook
appears in EXACTLY one of those three outcomes, never zero and never more than one.

Trimmed worked example, contrasting an auto-applying entry against an advisory one:

```json
{
  "remediate": [
    {"kind": "precommit", "id": "shellcheck", "issue": "hook_without_target",
     "criticality": 2, "summary": "...", "auto_apply": true},
    {"kind": "precommit", "id": ["cargo-audit", "cargo-deny"], "issue": "confirmed_redundant_pair",
     "criticality": 3, "summary": "...", "auto_apply": false}
  ],
  "blocked": []
}
```

`cache-update` also accepts one additional, TEST-ONLY flag not documented here: naming it would
invite a caller to write outside this skill's own cache namespace, so this document deliberately
omits it.

## Hardcoded Baseline Knowledge

Facts here do not go stale -- no research is needed to apply them.

**The six-category taxonomy** (the exact identifier strings every classification and finding
uses): `formatting`, `type-checking`, `linting`, `security`, `duplicate-code`, `dead-code`.

**The enable-everything heuristic.** An uncurated "enable everything" ruleset -- ruff
`select = ["ALL"]`, an unpinned PMD ruleset wildcard, an ESLint config extending an "all-plugins"
preset, golangci-lint's full available-linter list with no curation -- is flagged. Every
researched ecosystem's own docs independently discourage this pattern in favor of a maintained
preset plus explicit, reviewed extension.

**The two-most-commonly-skipped-categories heuristic.** Complete absence of Duplicate-code or
Dead-code category tooling is flagged, because research confirms these are the two categories
most commonly skipped entirely across every ecosystem surveyed -- unlike a missing formatter or
linter, their absence is easy to miss precisely because nothing else in a typical pipeline
notices it.

**The confirmed pairs table's existence and role.** A shared, ten-row table
(`REDUNDANT_VS_COMPLEMENTARY_PAIRS`) records, per ecosystem, which cross-tool pairs in the same
category are genuinely redundant, superseded, complementary, or merely overlapping (the closed
four-value relationship vocabulary). This skill's pair checks evaluate every detected pair
against this table -- never a same-category-implies-redundant heuristic -- so a fast/narrow tool
paired with a slow/wide one for a genuinely different failure class (e.g. `cargo-machete` and
`cargo-udeps`) is never flagged as duplication.

## Research Step

This step fires only when a per-stack cache entry is cold (never populated) or stale (older than
this skill's cache staleness window -- check the shared cache engine's own constant for the
exact threshold rather than assuming any particular figure, since that number has changed
before). It is a step of THIS skill's own flow, not appendix material for another skill.

On a host that provides a subagent/Task-dispatch primitive, dispatch one independent research
sub-task per distinct stack a `blocked` entry names; on a host with no such primitive, perform
the research directly in the current conversation instead of assuming one exists.

Each research sub-task is asked, for its ONE stack, for CURRENT (not training-data-stale)
concrete tool recommendations covering all six taxonomy categories -- never for the parity
direction or the pre-commit-vs-pre-push stage split, both of which are structural facts this
skill reads directly from the target repo's own Makefile/`.pre-commit-config.yaml`, never a
research question. Every value must be formatted `"<tool + invocation> (source: <url or concrete
rationale the research sub-task actually consulted>)"` -- a bare tool-name guess with no stated
evidence is not acceptable, and `cache-update` rejects it. Example findings object:

```json
{"formatting": "ruff format (source: https://docs.astral.sh/ruff/formatter/)",
 "dead-code": "vulture (source: https://github.com/jendrikseipp/vulture)"}
```

Write the findings to a scratch JSON file under `./tmp/` (this repo's own convention, applied to
whichever repo is running the check), then call:

```bash
python3 "$ENTRYPOINT" cache-update <stack> <path-to-that-file>
```

`cache-update` validates the JSON against the full tooling-key list (the six taxonomy category
names), non-empty-string-ness, and the `(source: ...)` provenance requirement before writing --
rejecting anything else with a one-line error and writing nothing.

## Deciding whether to research now or defer

The research step's one branch point -- research now, or defer to the next invocation -- carries
explicit decision criteria rather than a bare choose-one:

- **Research now** when the `blocked` list names few distinct stacks (1-2) and the invocation is
  already mid-flow on this repo -- the research cost is small, and deferring just means paying it
  next invocation anyway.
- **Defer** when `blocked` spans many stacks, the invocation explicitly wants a fast pass focused
  on what's already resolvable, or this invocation is itself time-boxed (e.g. part of a larger
  orchestrated run budgeting one skill call per target).
- **When genuinely unsure, ask the user** which they'd prefer rather than guessing -- the cost of
  researching the wrong priority first is a wasted sub-task dispatch.

## Limits

Three places this skill knows less than it might appear to -- stated here rather than left to be
discovered, in one scannable section, per the design spec's anti-patterns-live-in-one-place
lesson.

**1. Classification confidence.** Every classified hook carries a confidence level: `baseline`
(matched the shared catalog's tool index -- a researched, cited entry), `cache` (matched this
skill's own per-stack research cache, populated by the Research Step above), or `inferred`
(matched a small, explicitly-cited ambiguous-tool-name convention, e.g. bare `ruff` defaulting to
`linting` because upstream `ruff-pre-commit`'s linter hook id is the bare name while the
formatter's is suffixed `ruff-format`). A tool the skill cannot place in any of those three ways
is never guessed into a category -- it is reported as `unclassified_tool`, needing research,
rather than assigned a confidence it does not have.

**2. The presumed-complementary default.** A tool pair sharing a category with no row in the
confirmed pairs table is presumed complementary and never flagged, because flagging an
unresearched pair as redundant would claim confidence this skill does not have. Of the ten
researched pairs-table rows, nine are evaluable against a target repo's declared hooks directly.
The tenth pairs a rule FAMILY (ruff's `S` rule selector) against a tool (`bandit`) -- a
configuration-family relationship, not two hooks a repo runs side by side -- which generic
hook-pair evaluation cannot reach. So this skill evaluates nine of the ten rows and says nine,
rather than silently treating the tenth as covered.

**3. One configuration format cannot be read statically at all.** A JavaScript-module ESLint
flat config (`eslint.config.js`/`.mjs`/`.cjs`) is a program, not data -- this skill reads
configuration statically only, so the enable-everything check cannot be applied to it. Rather
than a silent skip, this emits an explicit advisory finding (`check-limitation` /
`config_not_statically_readable`) recommending a manual review, which reaches `remediate` with
`auto_apply: False` -- the honest answer is a visible advisory, not a quiet absence of a finding
that looks identical to "nothing wrong here."

## Anti-patterns (NEVER)

- **NEVER hardcode a host-specific absolute path** when resolving this skill's own entrypoint --
  always walk the host-neutral candidate list above; a hardcoded path breaks on every host but
  the one it was written for.
- **NEVER flag a same-category tool pair as redundant just because it shares a category.** Only
  the confirmed pairs table's own `redundant`/`supersession` rows produce a finding (see Limits
  #2 above) -- a same-category-implies-redundant shortcut would flag deliberate complementary
  layering (e.g. `cargo-machete` + `cargo-udeps`) as duplication.
- **NEVER index a bare tool name into the shared catalog when the researched cell is a distinct,
  longer string.** Bare `pylint` is not the same catalog entry as Python's duplicate-code cell
  `"pylint R0801"`: indexing the bare name would misclassify a `pylint` hook already satisfying a
  different category AND would suppress the Duplicate-code absence finding for a repo that has
  no real duplicate-code tooling wired -- trading one missing parity finding for a wrong
  classification and a wrong absence answer.
- **NEVER accept a bare tool-name guess with no `(source: ...)`** in a research finding --
  `cache-update` rejects it, and an unsourced recommendation is exactly the claim this project's
  live-verification rule forbids.
- **NEVER treat a `remediate` entry with `advisory: true` (tool-pair or check-limitation
  findings) as safe to auto-apply.** It arrives with `auto_apply: false` and must stay a
  suggestion to consider, never an automatic edit.
- **NEVER edit the target repo's `.pre-commit-config.yaml`, Makefile, or any other file from this
  skill.** The family's report-only boundary holds even when a finding's `auto_apply` is `true`
  -- "auto-apply" means "safe for the caller to apply automatically," not "this skill applies
  it."
- **NEVER read a stale cache entry as a current recommendation.** The staleness gate exists
  because concrete tool names drift; a stale entry must be re-researched, not reused silently.

## Reporting rule

Findings and remediation results are reported INLINE in the conversation only. This skill never
writes a persisted report file into the target repo.
