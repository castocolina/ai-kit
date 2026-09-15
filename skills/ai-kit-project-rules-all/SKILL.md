---
name: ai-kit-project-rules-all
description: Use when a target repo needs a whole-repo "check everything"/"run all the rules checkers" pass, never a single-domain question: this skill subprocess-fans-out to all 6 sibling `ai-kit-project-rules-*` checkers (agents, makefile, precommit, arch, docker, cicd) and merges their `check`/`remediate` findings into one cross-domain, criticality-ordered report, preserving the AGENTS.md-only `/agent-md-refactor` hand-off for `workflow`-kind findings and leaving every other domain's findings inline and report-only. Route a single-domain question (e.g. "does my Makefile have a validate alias", "is my CI duplicating a hook") to that one sibling directly instead of here.
---

# ai-kit-project-rules-all

## Scope

This skill DETECTS AND REPORTS across all 6 sibling domains at once. It never edits the target
repo; never runs any sibling's checker logic itself (it subprocess-invokes each sibling's own real
entry script); and never re-derives a classification a sibling's own `remediate` subcommand already
made -- every `remediate`/`blocked` entry this skill's report carries is exactly what that sibling
produced, unchanged. Per-domain rule logic belongs entirely to the six siblings, never to this
skill:

- `ai-kit-project-rules-agents` -- the AGENTS.md/CLAUDE.md house-ruleset checker (`workflow` kind).
- `ai-kit-project-rules-makefile` -- Makefile target-shape checker (`makefile` kind).
- `ai-kit-project-rules-precommit` -- Makefile-versus-pre-commit-hook parity and tooling-taxonomy
  checker (`precommit` kind).
- `ai-kit-project-rules-arch` -- architecture-fitness-target checker (`arch` kind).
- `ai-kit-project-rules-docker` -- local-dev Docker Compose convention checker (`docker` kind).
- `ai-kit-project-rules-cicd` -- CI-config command-reuse checker (`cicd` kind).

This skill's own original logic is limited to three things: the subprocess fan-out, the per-domain
failure isolation, and the cross-domain criticality merge (including the AGENTS.md hand-off tag).
Nothing else. A question about one domain's own rule shape, tooling taxonomy, or conventions is
that sibling's business, never this skill's.

## Resolve the entrypoint

Resolve once per invocation, in one Bash call, and record the printed path as a literal absolute
path -- the same 5-candidate pattern every sibling's own `SKILL.md` documents:

```bash
for d in "${CLAUDE_PLUGIN_ROOT:+$CLAUDE_PLUGIN_ROOT/skills/ai-kit-project-rules-all}" \
         "$HOME/.claude/skills/ai-kit-project-rules-all" \
         "${XDG_CONFIG_HOME:-$HOME/.config}/opencode/skills/ai-kit-project-rules-all" \
         "$HOME/.agents/skills/ai-kit-project-rules-all" \
         "$(dirname "<absolute path to THIS SKILL.md>")"; do
  [ -f "$d/ai-kit-project-rules-all.py" ] && { printf '%s\n' "$d/ai-kit-project-rules-all.py"; break; }
done
```

If no candidate exists, stop and report that the skill is not installed. The fifth candidate
covers a from-checkout invocation -- substitute the directory actually containing this `SKILL.md`.

That resolves THIS skill's own entrypoint. Internally, once invoked, this skill's `dispatch.py`
performs the identical **entrypoint-resolution** mechanism a SECOND time -- six times over, once
per domain, parameterized by each domain's real skill name
(`ai-kit-project-rules-agents`/`-makefile`/`-precommit`/`-arch`/`-docker`/`-cicd`) -- to locate each
sibling's own `<name>/<name>.py` entry script before subprocess-invoking it. Both resolutions walk
the SAME 5 host-neutral candidates and trust only those; neither ever searches `$PATH`. A sibling
installed somewhere this walk does not know about produces a D-05 failure entry (see Limits below),
never a silent skip.

## Run the check

```bash
python3 "$ENTRYPOINT" check <repo_root>
python3 "$ENTRYPOINT" remediate <repo_root>
```

Both subcommands return the SAME three-key shape: `{"remediate": [...], "blocked": [...], "failed":
[...]}`.

- `remediate` -- every domain's `remediate` entries, concatenated across all 6 domains and then
  globally sorted by `criticality` ascending (never grouped per-domain) -- the **cross-domain**
  criticality merge (SC2).
- `blocked` -- every domain's `blocked` entries (findings a sibling could not classify without
  research), concatenated the same way, also globally sorted.
- `failed` -- one D-05 entry per domain whose subprocess invocation itself failed (non-zero exit,
  timeout, malformed JSON on stdout, or an unresolvable entrypoint): `{"domain": ..., "status":
  "failed", "error": ..., "returncode": ...}`. A domain here never appears in `remediate` or
  `blocked` too -- the two are mutually exclusive per domain.

`check` and `remediate` return byte-identical output (D-04). Every per-finding classification
already happened inside each sibling's own `remediate` subprocess call before this skill ever sees
it (each sibling's `remediate` already runs that sibling's own `check` internally, then its own
`build_remediation()` builder); this skill's only original work is the fan-out, the failure
isolation, and the cross-domain merge described above -- there is no further per-orchestrator
classification step for `remediate` to do that `check` does not already do.

One complete example finding WITH a `hand_off` key (from a real run against a fixture repo whose
AGENTS.md is missing house rules):

```json
{
  "kind": "workflow",
  "id": "R01",
  "status": "missing",
  "criticality": 1,
  "summary": "All written project artifacts (docs, commits, comments, planning files) are English-only, regardless of the conversation's language.",
  "matched_signals": [],
  "auto_apply": true,
  "hand_off": "agent-md-refactor"
}
```

One complete example finding WITHOUT a `hand_off` key, from the same real run (a non-`workflow`
domain):

```json
{
  "kind": "arch",
  "id": "arch-test-target",
  "criticality": 2,
  "summary": "This repo has no arch-test-shaped Makefile target (a target named e.g. 'arch-test', 'arch', 'arch-check', or 'architecture-test'). Add one that runs this repo's architecture-fitness checks, and chain it into 'test' -- as a direct or transitive prerequisite, or by invoking it from 'test''s recipe -- so it actually runs. No language-stack marker file was detected in this repo, so this skill has no per-stack canonical architecture-fitness-tool recommendation to add.",
  "issue": "arch_test_target_missing",
  "auto_apply": true
}
```

`python3 "$ENTRYPOINT" bogus <repo_root>` prints `usage: ai-kit-project-rules-all.py
check|remediate [repo_root]` and exits `0` for a missing/help argument, or `unknown subcommand:
bogus` on stderr and exits `2` for an unrecognized one -- confirmed against the shipped `cli.py`.

## What it checks

All 6 domains at once, merged into one **cross-domain** criticality-ordered report (SC2). A real
`check` run against this repo itself returns 12 `remediate` entries, 3 `blocked`, 0 `failed`,
spanning the `makefile`, `precommit`, and `arch` domains that had findings that day -- sorted as
one list by `criticality`, not grouped by domain. The `hand_off: agent-md-refactor` tag (SC3) is
set on every `remediate` entry whose `kind == "workflow"` (the AGENTS.md domain) and on no other
entry -- see the Hand-off mechanism section below for what a caller does with it.

## Hand-off mechanism (SC3)

For `workflow`-kind entries ONLY (the AGENTS.md domain), this skill's report is the SAME
`hand_off: agent-md-refactor`-tagged payload `ai-kit-project-rules-agents/SKILL.md` itself
documents. That sibling's own "Wrap mechanism" section names the concrete sequence this document
points at BY NAME rather than restating it:

- **Step A** (confirm near-misses first, owned by `ai-kit-project-rules-agents` itself) -- for
  every `workflow` entry with `auto_apply: false`, stop and ask the user to confirm or decline
  individually before `/agent-md-refactor` is invoked at all.
- **Step B** (assemble one ordered list) -- every `auto_apply: true` `workflow` entry plus every
  user-confirmed near-miss, in the same most-critical-first order `remediate` already returned.
- **Step C** (one invocation, named injection point) -- invoke `/agent-md-refactor` against the
  target file EXACTLY ONCE, treating the Step B list's `summary` strings as additional "essential
  content" candidates for that skill's own Phase 2/Phase 3.

This is a documentation cross-reference, never new code: this skill has no CLI or importable path
into `/agent-md-refactor` and does not re-implement Step A/B/C itself -- it only produces the
`hand_off`-tagged `workflow` entries that make Step A/B/C's input possible.

Every OTHER domain's findings (`makefile`, `precommit`, `arch`, `docker`, `cicd`) are inline and
**report-only**, with no auto-apply, no matter how confident a `hand_off`-less entry's `auto_apply`
field reads. `auto_apply: true` on a non-`workflow` entry means it is safe for the CALLER to apply
automatically, never that this skill -- or any of its 6 siblings -- has already applied it.

## Limits

At least 8 places this skill knows less than it might appear to, stated here rather than left to be
discovered, per this family's own lesson that a document stating what it cannot do is more useful
than one implying it can do everything. Each is its own standalone sentence a reader can act on.
This is a floor: an honestly-discovered 9th or later limit is added here, never trimmed back to
force the count to exactly 8.

1. **Dispatch is sequential, with a 30-second per-domain timeout (D-06).** All 6 siblings run one
   at a time, never in parallel, so a full run's worst case is roughly 180 seconds (6 x 30s) even
   when every domain is slow -- accepted in exchange for zero completion-order non-determinism.
2. **There is no cross-run caching.** Every invocation re-runs all 6 siblings' full `check` from
   scratch; this skill never calls a sibling's own caching-refresh subcommand where one exists, so
   two consecutive runs against an unchanged repo pay the same cost twice.
3. **Entrypoint resolution trusts only the same 5 known install-location candidates every sibling's
   own `SKILL.md` documents -- it never searches `$PATH`.** A sibling installed somewhere outside
   those 5 candidates reports a D-05 `failed` entry, not a silent skip -- see "Resolve the
   entrypoint" above for the **entrypoint-resolution** mechanism itself.
4. **`(kind, id, issue)` together, never `id` alone, distinguish two entries anywhere in the
   combined report.** This is the shared builder's own documented meaning, inherited verbatim and
   never re-derived here -- an `id` alone can repeat across domains (e.g. two different domains
   both using an `id` like `format`).
5. **The AGENTS.md hand-off is a documentation cross-reference, never new code.** This skill has no
   CLI and no importable path into `/agent-md-refactor` -- Step A/B/C above belongs entirely to
   `ai-kit-project-rules-agents`.
6. **Same-criticality findings across different domains tie-break by a pinned, fixed-order domain
   sequence: agents, makefile, precommit, arch, docker, cicd.** This **fixed-order** tie-break is
   deterministic but arbitrary -- it is never a claim that one domain's findings are inherently more
   urgent than another's at equal criticality, only that the merge needs a stable order and this is
   the one it uses.
7. **A domain in the `failed` list is never folded into `remediate`/`blocked`, but a caller reading
   only `remediate` and ignoring `failed` can still mistake "couldn't check this domain" for
   "nothing to report" if it does not read the whole payload.** The three lists are mutually
   exclusive per domain, but nothing about the shape forces a caller to read all three.
8. **Zero re-implementation of any sibling's own classification logic anywhere in this skill.**
   Every `remediate`/`blocked` entry in the combined report is exactly what that sibling's own
   `remediate` subcommand already produced -- criticality, `auto_apply`, and every other field
   arrive unchanged from the sibling that emitted them.

`SKILL-SHAPE-OK`-style keyword checks on this section are a DELETION DETECTOR and nothing more:
they confirm a limit's keyword survived, not that the sentence still states something a reader
would act on.

## Anti-patterns (NEVER)

- **NEVER auto-apply anything for a non-`workflow`-kind domain**, whatever its `auto_apply` field
  says -- **report-only** applies to every domain except the AGENTS.md hand-off.
- **NEVER abort the whole run because one sibling crashed or timed out.** One domain's D-05 failure
  entry must never prevent the other 5 domains' real results from being aggregated and reported.
- **NEVER build the cross-domain merge input from anything but the fixed `DOMAIN_ORDER`
  sequence.** Iterating domains in any other order breaks both the dispatch order and the
  **fixed-order** tie-break the aggregator depends on.
- **NEVER re-implement a sibling's own `build_remediation` branching inside this skill.** Every
  classification decision belongs to the sibling that made it; this skill only fans out, isolates
  failures, and merges.
- **NEVER hardcode a host-specific absolute path when resolving this skill's own entrypoint, or any
  sibling's.** Always walk the host-neutral candidate list, both for this skill's own resolution and
  for the internal per-domain **entrypoint-resolution** dispatch.py performs.

## Reporting rule

Findings are reported inline in the conversation; this skill never writes a persisted report file
into the target repo, matching the family-wide pattern.
