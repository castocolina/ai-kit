---
name: ai-kit-project-rules-arch
description: Use when a target repo's `arch-test`-shaped Makefile target needs auditing -- whether it exists, whether it is chained into `test` so it actually runs, and (where the backing test file is discoverable) whether that file is AST-only rather than importing or executing the module it architecturally checks -- or when asked "is my architecture-fitness test wired into test", "does my arch-test target actually run", or "does my architecture test file import what it should only parse". Detects and reports only; never edits the target repo.
---

# ai-kit-project-rules-arch

## Scope

This skill DETECTS AND REPORTS gaps in a repo's architecture-fitness Makefile WIRING only. It
never edits the target repo's Makefile, test files, or any other file -- applying a fix is a
decision for whoever invoked this skill.

Three neighbouring boundaries, named here so a reader files the right question in the right
place:

- General Makefile target SHAPE -- the `validate-<category>` alias chain, required static
  targets, the recipe-length cap, Docker build-before-up, the shellcheck threshold -- is the
  `ai-kit-project-rules-makefile` sibling skill's domain, not this one's. This skill reads the
  Makefile only to find and evaluate one arch-test-shaped target; it never judges the
  Makefile's overall shape.
- Pre-commit configuration and Makefile/pre-commit-hook parity belong to the
  `ai-kit-project-rules-precommit` sibling skill, not this one.
- Auditing an AGENTS.md/CLAUDE.md-style agent-instruction file is the fourth sibling skill's
  domain. That skill also carries its own agent-instruction-file remediation hand-off
  mechanism, which this skill does not have and does not replicate.

What this skill checks, in order: does an arch-test-SHAPED target exist in the Makefile (a
target named, for example, `arch-test`, `arch`, `arch-check`, or `architecture-test` -- a
shape RULE, not a single literal name); is that target actually reached when `test` runs (any
of three mechanisms counts -- a direct prerequisite of `test`, a transitive prerequisite
reachable through `test`'s own prerequisite graph, or a target `test`'s own recipe invokes by
name); and -- where the backing test file behind that target is discoverable -- does that file
PARSE the module it architecturally checks rather than import or execute it.

## Resolve the entrypoint

Resolve once per invocation, in one Bash call, and record the printed path as a literal
absolute path:

```bash
for d in "${CLAUDE_PLUGIN_ROOT:+$CLAUDE_PLUGIN_ROOT/skills/ai-kit-project-rules-arch}" \
         "$HOME/.claude/skills/ai-kit-project-rules-arch" \
         "${XDG_CONFIG_HOME:-$HOME/.config}/opencode/skills/ai-kit-project-rules-arch" \
         "$HOME/.agents/skills/ai-kit-project-rules-arch" \
         "$(dirname "<absolute path to THIS SKILL.md>")"; do
  [ -f "$d/ai-kit-project-rules-arch.py" ] && { printf '%s\n' "$d/ai-kit-project-rules-arch.py"; break; }
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

`check` returns a single key: `{"arch": [...]}` -- every finding this skill emits, sorted by
criticality. The checker modules (`arch_checker.py`, `ast_only.py`, `canonical_tools.py`) are
the source of truth for what each finding's fields mean; this document does not restate every
finding kind's full field list.

`remediate` runs `check` internally and returns the shared builder's two-key payload:
`{"remediate": [...ordered, most-critical-first...], "blocked": [...]}`. Every `remediate`
entry carries `auto_apply`. `auto_apply` is `True` UNLESS the underlying finding carries
`advisory: True` (the AST-only not-verifiable advisories do -- see Limits below), in which case
it arrives `False` -- an advisory entry is a suggestion to consider, never an edit to apply.
This skill's findings never populate `blocked`: nothing it emits carries `needs_research`,
because its baseline knowledge is entirely hardcoded (see below).

This skill has exactly two subcommands, `check` and `remediate` -- unlike the Phase 10
(`ai-kit-project-rules-makefile`) and Phase 11 (`ai-kit-project-rules-precommit`) siblings,
there is no `classify` subcommand and no `cache-update` subcommand, and no research step or
cache-staleness mechanism behind either of the two subcommands that do exist. A reader coming
from either sibling skill should expect that difference rather than discover it by a failed
invocation: an architecture-fitness tool choice per ecosystem is stable in a way a linter
roster is not, so this skill's knowledge does not go stale the way a per-stack tooling cache
would.

Three finding categories, because a reader needs them to interpret a report: `arch-test-target`
(the shape rule found no target at all), `arch-test-chaining` (a shaped target exists but
`test` never reaches it), and `arch-test-ast-only` (the backing test file either could not be
verified as AST-only, or was verified and found to import/execute the module it checks).

Trimmed worked example, contrasting an auto-applying entry against an advisory one:

```json
{
  "remediate": [
    {"kind": "arch", "id": "arch-test-chaining", "issue": "arch_test_not_chained",
     "criticality": 2, "summary": "...", "auto_apply": true},
    {"kind": "arch", "id": "arch-test-ast-only", "issue": "ast_only_not_verifiable",
     "criticality": 4, "summary": "...", "auto_apply": false}
  ],
  "blocked": []
}
```

## Hardcoded Baseline Knowledge

This skill's knowledge is entirely hardcoded -- no research is needed to apply it, and there is
no per-stack cache to keep current. The canonical architecture-fitness tool per stack, with the
one-line reason for each:

- **Python -> import-linter** -- static, AST-only via Grimp, safe against untrusted
  target-repo code, and config-DSL "contracts" that express layering rules declaratively.
- **Node/TS -> dependency-cruiser** -- the broadest static rule surface (circular
  dependencies, path-based layering, orphan detection) with no build or type-system
  dependency.
- **Java -> ArchUnit** -- runs as ordinary JUnit tests in the normal test suite rather than
  as a side lint pass, the most consistently recommended pattern across sources surveyed,
  since a failing named test is a stronger CI signal than a side lint-pass failure.
- **Rust / Go -- known gap.** No equally canonical, dedicated architecture-fitness tool
  surfaced in research for either ecosystem, and this skill declines to assert a false
  canonical choice for them rather than inventing one.

## Limits

Three places this skill knows less than it might appear to -- stated here rather than left to
be discovered, in one scannable section, per the design spec's anti-patterns-live-in-one-place
lesson.

**1. The AST-only check is Python-only and statically scoped.** It reads one file, follows one
level of local name resolution, and sees no cross-module dataflow and no computed/dynamic
module names. Where it cannot see, it emits one of four PINNED advisory reasons rather than a
guess or a silent skip -- a caller branches on these exact `reason` token strings, so a
paraphrase here would document a surface the code does not emit:
  - `not_discoverable` -- the arch-test target's own Makefile recipe formed a file-shaped
    candidate, but it did not resolve to an existing regular file inside the repo root.
  - `not_python` -- the backing file the recipe names is not a `.py` file, so this skill's
    ast-based check does not apply to it.
  - `unparseable` -- the backing file is a `.py` file that Python's own `ast.parse` refused to
    parse (a syntax error).
  - `no_parse_call` -- the backing file parsed, but contains no call reaching `ast.parse`
    (directly, or through a helper function), so this skill could not identify what it
    architecturally checks.

**2. The canonical-tool baseline is hardcoded with no staleness mechanism.** For Rust and Go it
states a known gap rather than naming a tool, because no equally canonical dedicated tool
surfaced for those ecosystems, and asserting one would be a confident wrong answer.

**3. This skill checks the FORM of architecture-fitness wiring only.** It does NOT enforce
dependency-direction or layering-boundary rules, and it does not analyse the target repo's own
import graph. That fuller ambition is an explicitly-flagged known gap recorded in this
project's roadmap backlog, deliberately out of this skill's scope rather than unfinished work.
A user who reads a clean report from this skill has learned that the wiring is present, not
that the architecture is sound.

## Anti-patterns (NEVER)

- **NEVER hardcode a host-specific absolute path** when resolving this skill's own entrypoint
  -- always walk the host-neutral candidate list above; a hardcoded path breaks on every host
  but the one it was written for.
- **NEVER treat a `remediate` entry with `advisory: true` as safe to auto-apply.** It arrives
  with `auto_apply: false` and must stay a suggestion to consider, never an automatic edit.
- **NEVER read the four not-verifiable `reason` tokens as interchangeable or paraphrase them.**
  They are a pinned, closed vocabulary a caller branches on; inventing a fifth or renaming one
  documents a surface the code does not emit.
- **NEVER assert a canonical tool for Rust or Go.** The known-gap statement exists precisely
  because no equally canonical, dedicated tool surfaced in research for either ecosystem.
- **NEVER read a clean report from this skill as proof the architecture is sound.** It proves
  only that the form of the wiring is present -- see Limits #3.
- **NEVER edit the target repo's Makefile, test files, or any other file from this skill.** The
  family's report-only boundary holds even when a finding's `auto_apply` is `true` --
  "auto-apply" means "safe for the caller to apply automatically," not "this skill applies it."

## Reporting rule

Findings and remediation results are reported INLINE in the conversation only. This skill never
writes a persisted report file into the target repo.
