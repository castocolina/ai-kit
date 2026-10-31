---
name: ai-kit-project-rules-all
description: Use when a target repo needs a whole-repo "check everything"/"run all the rules checkers"/"full rules audit"/"audit all repo conventions" pass (agents file, Makefile, pre-commit, arch test, Docker, CI together), never a single-domain question. It subprocess-fans-out to all 6 sibling `ai-kit-project-rules-*` checkers (agents, makefile, precommit, arch, docker, cicd) and merges their `remediate` findings and a separate AGENTS.md broken-link check step into one cross-domain, criticality-ordered report. Route a single-domain question (e.g. "does my Makefile have a validate alias", "is my CI duplicating a hook") to that one sibling directly instead of here.
---

# ai-kit-project-rules-all

## Scope

This skill DETECTS AND REPORTS across all 6 sibling domains at once. Its script never edits the
target repo; the only edit path is the agents sibling's Wrap mechanism for `hand_off` entries, and
only when the user asked to fix or remediate (see "Act on the report"). It subprocess-invokes each
sibling's own real entry script and passes every `remediate`/`blocked` entry through with the
sibling's field values untouched; the one addition is the `hand_off` key `aggregate()` puts on
`workflow`-kind entries. Per-domain rule logic belongs to the siblings, never to this skill:

- `ai-kit-project-rules-agents` -- the AGENTS.md/CLAUDE.md house-ruleset checker (`workflow` kind).
- `ai-kit-project-rules-makefile` -- Makefile target-shape checker (`makefile` kind).
- `ai-kit-project-rules-precommit` -- Makefile-versus-pre-commit-hook parity and tooling-taxonomy
  checker (`precommit` kind).
- `ai-kit-project-rules-arch` -- architecture-fitness-target checker (`arch` kind).
- `ai-kit-project-rules-docker` -- local-dev Docker Compose convention checker (`docker` kind).
- `ai-kit-project-rules-cicd` -- CI-config command-reuse checker (`cicd` kind).

This skill's own logic is the subprocess fan-out, the per-domain failure isolation, and the
cross-domain criticality merge (including the AGENTS.md hand-off tag). A question about one
domain's own rules is that sibling's business.

## Resolve the entrypoint

Resolve once per invocation, in one Bash call, and record the printed path as a literal absolute
path. Set `SKILL_DIR` to the directory that contains this `SKILL.md` (the host's skill base
directory; the one line to edit). An unedited block aborts with a message instead of guessing.
`SKILL_DIR` is tried first so a checkout runs its own copy rather than an installed one that may be
on another branch:

```bash
SKILL_DIR='<directory containing this SKILL.md>'
[ -f "$SKILL_DIR/SKILL.md" ] \
  || { echo "set SKILL_DIR to the directory containing this SKILL.md" >&2; exit 2; }
for d in "$SKILL_DIR" \
         "${CLAUDE_PLUGIN_ROOT:+$CLAUDE_PLUGIN_ROOT/skills/ai-kit-project-rules-all}" \
         "$HOME/.claude/skills/ai-kit-project-rules-all" \
         "${XDG_CONFIG_HOME:-$HOME/.config}/opencode/skills/ai-kit-project-rules-all" \
         "$HOME/.agents/skills/ai-kit-project-rules-all"; do
  [ -f "$d/ai-kit-project-rules-all.py" ] \
    && { printf '%s\n' "$(cd "$d" && pwd -P)/ai-kit-project-rules-all.py"; break; }
done
```

If no candidate exists, stop and report that the skill is not installed.

That resolves THIS skill's own entrypoint. Internally, once invoked, `dispatch.py` resolves each
of the six siblings (`ai-kit-project-rules-agents`/`-makefile`/`-precommit`/`-arch`/`-docker`/
`-cicd`) the same way, checkout first: the sibling next to the running copy of this skill (from
`dispatch.py`'s own real path), then the plugin root, `~/.claude/skills`, the opencode skills
directory and `~/.agents/skills`. It looks for `<name>/<name>.py` and never searches `$PATH`. A sibling
installed somewhere this walk does not know about produces a `failed` entry, never a silent skip.

## Resolve the agents sibling

"Act on the report" steps 2 and 3 use the `ai-kit-project-rules-agents` skill, which can be installed
away from this skill (a split install). Resolve it once, in one Bash call, with the same candidate
walk as above and with the agents sibling's name (the from-checkout sibling next to `SKILL_DIR`
first), and record the printed path as the literal `<AGENTS_ENTRYPOINT>`. Its `SKILL.md` is in the
same directory. Set `SKILL_DIR` exactly as above:

```bash
SKILL_DIR='<directory containing this SKILL.md>'
[ -f "$SKILL_DIR/SKILL.md" ] \
  || { echo "set SKILL_DIR to the directory containing this SKILL.md" >&2; exit 2; }
for d in "$SKILL_DIR/../ai-kit-project-rules-agents" \
         "${CLAUDE_PLUGIN_ROOT:+$CLAUDE_PLUGIN_ROOT/skills/ai-kit-project-rules-agents}" \
         "$HOME/.claude/skills/ai-kit-project-rules-agents" \
         "${XDG_CONFIG_HOME:-$HOME/.config}/opencode/skills/ai-kit-project-rules-agents" \
         "$HOME/.agents/skills/ai-kit-project-rules-agents"; do
  [ -f "$d/ai-kit-project-rules-agents.py" ] \
    && [ -d "$(cd "$d" && pwd -P)/../_shared/ai_kit_rules_common" ] \
    && { printf '%s\n' "$(cd "$d" && pwd -P)/ai-kit-project-rules-agents.py"; break; }
done
```

The second test skips a candidate that cannot import (the agents sibling's own loop applies it): its package needs `skills/_shared/` beside the skill's real (symlink-resolved) directory, which a checkout and a symlink install have and a plain copy-install does not. A plain copy ahead of a working later candidate is skipped, not bound.

If nothing prints, the agents sibling is not installed: steps 2 and 3 cannot run, so say so.

## Run the check

**Trust gate.** When `.planning/` exists, the agents sibling's GSD identity probe can run the
target repo's own gsd-tools (see its "Trust gate"), and this skill captures that sibling's stderr,
so the line naming the probed path never reaches you on success. Unless the user has already said
they trust that repo's code, ask before running. If they decline, or no one can be asked, prefix
the command with `AI_KIT_SKIP_GSD_PROBE=1`; the siblings inherit it, nothing from the repo runs,
and the rules that need the probe (R18/R19) come back as `notices`.

Substitute the recorded path for `<ENTRYPOINT>` and run `check`; `remediate` is an alias with the
same output:

```bash
python3 <ENTRYPOINT> check <repo_root>
```

Give this command a host tool timeout of at least 210 seconds, or run it in the background: the
six siblings run one after another, up to 30 seconds each (180 seconds, plus interpreter startup). A single sibling that overruns its own 30 seconds is not a host kill: it becomes a `failed` entry with `error: timed out after 30s` and the other five domains still return. If the host kills the whole command, no JSON
comes back, so report a whole-run failure with every domain unchecked, never a clean run.

`<repo_root>` defaults to `.`. With no argument or `-h`/`--help` the script prints `usage:
ai-kit-project-rules-all.py check|remediate [repo_root]` and exits `0`; an unknown subcommand
prints `unknown subcommand: <name>` on stderr and exits `2`.

The output has four keys (every classification already happened inside each sibling's own
`remediate`): `{"remediate": [...], "blocked": [...], "failed":
[...], "notices": [...]}`.

- `remediate` -- every domain's `remediate` entries, concatenated across all 6 domains and then
  globally sorted by `criticality` ascending (never grouped per domain): the **cross-domain**
  criticality merge.
- `blocked` -- every domain's `blocked` entries (findings a sibling could not classify without
  research), concatenated the same way, also globally sorted.
- `failed` -- one entry per domain whose subprocess invocation itself failed (unresolvable
  entrypoint, launch error, non-zero exit, timeout, undecodable output, stdout that is not a JSON
  object), normally `{"domain": ..., "status": "failed", "error": ..., "returncode": ...}`; a
  sibling that prints a JSON object without a `remediate` key is passed through with its `domain`
  added. Any object that contains a `remediate` key is merged as a real result, even if it also
  has `status: failed`. A domain here never appears in `remediate` or `blocked` too.
- `notices` -- workflow-only: the agents sibling emits one per workflow finding flagged
  `unverified: true` (a rule whose condition could not be proven; R18/R19 are the probe example),
  as `{kind, id, status, unverified, reason, criticality, summary}`. Structural siblings report
  `notices: []`. They are concatenated in domain order, never re-sorted and never inserted as a
  remediation.

One complete example finding WITH a `hand_off` key (a fixture repo whose AGENTS.md is missing house
rules):

```json
{
  "kind": "workflow",
  "id": "R01",
  "status": "missing",
  "criticality": 1,
  "summary": "All written project artifacts (docs, commits, comments, planning files) are English-only, regardless of the conversation's language.",
  "matched_signals": [],
  "auto_apply": true,
  "signals": ["english only", "english-only", "non-negotiable"],
  "hand_off": "agent-md-refactor"
}
```

One complete example finding WITHOUT a `hand_off` key, from the same run (a non-`workflow`
domain):

```json
{
  "kind": "arch",
  "id": "arch-test-target",
  "criticality": 2,
  "summary": "This repo has no arch-test-shaped Makefile target ... (trimmed)",
  "issue": "arch_test_target_missing",
  "auto_apply": true
}
```

## Act on the report

1. **`failed` and `notices`** -- always report every entry. A failed domain was not checked; a
   notice is a rule whose condition could not be proven. A `failed` entry whose `error` reads
   `entrypoint not found for '<sibling>'` means that sibling is not installed where the walk in
   "Resolve the entrypoint" looks: report the domain as not installed and name those locations.
2. **`hand_off: agent-md-refactor` entries** (`workflow` kind, the AGENTS.md domain) -- on a
   check-only request, report them and offer the hand-off; do not edit. Only when the user asked to
   fix or remediate (or accepts the offer), it is MANDATORY to read the "Wrap mechanism" section of
   the `ai-kit-project-rules-agents` skill (load it by name, or read the `SKILL.md` in the directory
   of `<AGENTS_ENTRYPOINT>`) and follow its Steps A-D. This skill has no CLI or importable path into
   `/agent-md-refactor` and does not restate those steps.
   Do not load the other five siblings' SKILL.md files; their payloads carry what you report.
3. **AGENTS.md broken links** -- the merged report never carries them (see Limits), so always run
   the agents sibling's `check` once more and report its `links` list (empty means none broken).
   `<AGENTS_ENTRYPOINT>` is the literal path recorded from "Resolve the agents sibling" (shell
   variables do not persist between Bash calls, so substitute it):

   ```bash
   AI_KIT_SKIP_GSD_PROBE=1 python3 "<AGENTS_ENTRYPOINT>" check <repo_root>
   ```

   The probe skip is deliberate: link checking never needs the GSD probe, so this run executes
   nothing from the target repo and needs no trust answer. Read only the `links` key from its
   output. If that command cannot run (the agents sibling did not resolve, or it exits non-zero), say
   explicitly that broken links were NOT checked; never leave the report silent on links.
4. **`blocked` entries** -- a structural finding with `needs_research` and no recommendation.
   Today only the makefile and precommit siblings emit those, but any structural kind can. Each
   entry carries `kind`, `id`, `criticality`, `summary` and `stacks` (no `issue`). Report each as
   needing research and route the user to the sibling that owns its `kind` for its research and
   `cache-update` flow. This skill never runs that flow itself.
5. **Every other `remediate` entry** (`makefile`, `precommit`, `arch`, `docker`, `cicd`) is
   **report-only**: present it inline and do not edit the target repo in this flow, whatever its
   `auto_apply` says. `auto_apply` is passed through for that sibling or the user to act on later;
   it never means anything was applied. When the user asks to fix them, invoke the sibling that owns
   that `kind` (a single-domain request), not this skill.

## Limits

1. **Dispatch is sequential, with a 30-second per-domain timeout**, so a full run can take up to
   180 seconds plus interpreter startup. Runs are not cached: every invocation re-runs all 6 siblings and never calls their
   `cache-update` subcommands.
2. **Entrypoint resolution trusts only the 5 known install-location candidates (checkout sibling
   first) -- it never searches `$PATH`.** A sibling installed elsewhere reports a `failed` entry,
   not a silent skip.
3. **`(kind, id, issue)` groups `remediate` findings of one type; it does not identify one
   finding.** An `id` alone can repeat across domains, and two same-type findings on different
   targets share all three keys. `blocked` entries have no `issue`, so `(kind, id)` is all they
   share. Structural entries carry their location fields (`service`, `compose_file`,
   `depends_on`, `ci_file`, `job`, `command`, `hook_id`, ...) and `summary` names the target:
   dedupe only on the full entry, never on those three keys alone.
4. **AGENTS.md broken-link findings are not in the merged output.** The agents sibling reports
   them only from its `check` (`links`), and this skill calls each sibling's `remediate`; "Act on
   the report" step 3 runs that `check` separately.
5. **Same-criticality findings across different domains tie-break by a pinned, fixed-order domain
   sequence: agents, makefile, precommit, arch, docker, cicd.** This is deterministic but
   arbitrary, never a claim that one domain is more urgent at equal criticality.

## Anti-patterns (NEVER)

- **NEVER summarize the run as clean while `failed` or `notices` is non-empty.** An unchecked
  domain or an unproven rule is not a pass. Nor call the audit complete without the AGENTS.md
  `links` result (or an explicit "links not checked").
- **NEVER auto-apply anything for a non-`workflow`-kind domain**, whatever its `auto_apply` field
  says -- **report-only** applies to every domain except the AGENTS.md hand-off.
- **NEVER start the Wrap steps on a check-only request.** They edit AGENTS.md; a "check
  everything" request gets the report and an offer to fix, not a refactor.
- **NEVER act on a `hand_off` entry from this document alone.** Its insertion rules (verbatim
  blocks, signal phrases, the single refactor pass, the re-check) live in the agents sibling's
  Wrap mechanism.
- **NEVER abort the whole run because one sibling crashed or timed out.** One domain's `failed`
  entry must never prevent the other 5 domains' real results from being reported. A host kill of
  the whole command is the opposite case: nothing was checked.
- **NEVER hardcode a host-specific absolute path when resolving this skill's own entrypoint, or any
  sibling's.** Always walk the host-neutral candidate list.

## Reporting rule

Findings are reported inline in the conversation; this skill never writes a persisted report file
into the target repo, matching the family-wide pattern.
